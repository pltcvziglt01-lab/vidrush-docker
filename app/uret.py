#!/usr/bin/env python3
"""Vidrush render orkestrasi (v2 — gorsel/stok/kapak uretimi Python'da).
Girdi: base64 kodlu JSON (argv[1]) ya da JSON dosya yolu:
  { "is_adi": "is_123", "voice": "tr-TR-EmelNeural", "kapak_prompt": "...",
    "sahneler": [ { "n":1, "voiceover":"...", "image_prompt":"...",
                    "source":"stock|ai", "stock_query":"..." } ] }
Yapilanlar (hepsi Python, n8n binary node'lari YOK):
  - source=stock + Pexels anahtari varsa: Pexels videosu indir; yoksa/bulunamazsa AI'a duser
  - source=ai (ya da fallback): OpenAI gpt-image-1-mini ile gorsel uret, base64 -> PNG
  - edge-tts seslendirme (+kelime zamanlari -> altyazi)
  - kapak: OpenAI gpt-image-1.5 (high)
  - Remotion ile 1080p render
Cikti (stdout son satir JSON): {"video":"...", "kapak":"...", "sure":N, "sahne_sayisi":N}
"""
import asyncio
import base64
import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error

import edge_tts

KOK = os.path.dirname(os.path.abspath(__file__))
STUDYO = os.path.join(KOK, "render-studio")
PUBLIC = os.path.join(STUDYO, "public")

TICK = 10_000_000  # 100ns -> saniye
OPENAI_KEY = os.environ.get("OPENAI_KEY", "")
PEXELS_KEY = os.environ.get("PEXELS_KEY", "")


def payload_oku(arg: str) -> dict:
    if os.path.exists(arg):
        with open(arg) as f:
            return json.load(f)
    return json.loads(base64.b64decode(arg))


def indir(url: str, hedef: str, headers=None) -> None:
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=180) as r, open(hedef, "wb") as f:
        while True:
            parca = r.read(1 << 16)
            if not parca:
                break
            f.write(parca)


def openai_gorsel(prompt: str, hedef: str, model="gpt-image-1-mini",
                  boyut="1536x1024", kalite="medium", deneme=3) -> bool:
    """OpenAI gorsel API -> base64 -> PNG dosyasi. Basari: True."""
    govde = json.dumps({"model": model, "prompt": prompt, "size": boyut,
                        "quality": kalite, "n": 1}).encode()
    for d in range(deneme):
        try:
            req = urllib.request.Request(
                "https://api.openai.com/v1/images/generations", data=govde,
                headers={"Authorization": f"Bearer {OPENAI_KEY}",
                         "Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=180) as r:
                d2 = json.loads(r.read())
            b64 = d2["data"][0]["b64_json"]
            with open(hedef, "wb") as f:
                f.write(base64.b64decode(b64))
            return True
        except urllib.error.HTTPError as e:
            govet = e.read().decode(errors="replace")[:200]
            print(f"  openai gorsel hata {e.code}: {govet}", file=sys.stderr)
            if e.code == 429 and d < deneme - 1:
                time.sleep(20)
                continue
            return False
        except Exception as e:
            print(f"  openai gorsel istisna: {e}", file=sys.stderr)
            time.sleep(5)
    return False


def pexels_video(query: str, hedef: str) -> bool:
    """Pexels'ten stok video indir. Anahtar yoksa/bulunamazsa False."""
    if not PEXELS_KEY or PEXELS_KEY.startswith("PEXELS_KEY"):
        return False
    try:
        url = ("https://api.pexels.com/videos/search?orientation=landscape&size=medium"
               "&per_page=5&query=" + urllib.parse.quote(query))
        req = urllib.request.Request(url, headers={"Authorization": PEXELS_KEY})
        with urllib.request.urlopen(req, timeout=60) as r:
            d = json.loads(r.read())
        en_iyi = None
        for v in d.get("videos", []):
            dosyalar = [f for f in v.get("video_files", [])
                        if 1280 <= (f.get("width") or 0) <= 1920 and f.get("link")]
            dosyalar.sort(key=lambda f: f.get("width", 0), reverse=True)
            if dosyalar and (en_iyi is None or (v.get("duration", 0) > en_iyi[0])):
                en_iyi = (v.get("duration", 0), dosyalar[0]["link"])
        if not en_iyi:
            return False
        indir(en_iyi[1], hedef)
        return True
    except Exception as e:
        print(f"  pexels hata: {e}", file=sys.stderr)
        return False


import urllib.parse  # noqa: E402


def _ses_suresi(mp3_yolu: str) -> float:
    """Gercek ses uzunlugu (ffprobe). WordBoundary gelmezse/yanlissa sahne suresi buna gore
    ayarlanir -> anlatim kesilmez."""
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", mp3_yolu],
            capture_output=True, text=True, timeout=30)
        return float((r.stdout or "").strip() or 0)
    except Exception:
        return 0.0


# ═══════════ OpenAI TTS (GERCEK YASLI SES) ═══════════
# Neden gerekli: edge-tts'in 322 sesinin HICBIRI yasli degil (hepsi Friendly/Positive/
# Cheerful etiketli). Perde dusurmek genc sesi KALINLASTIRIR, yaslandirmaz.
# gpt-4o-mini-tts ise "instructions" aliyor -> sesin yasini/tinisini TARIF edebiliyoruz.
# BEDEL: edge-tts kelime zamanlarini (WordBoundary) bedava veriyordu, OpenAI vermiyor.
# Cozum: uretilen mp3'u whisper-1 ile kelime bazli hizala. Whisper de patlarsa
# kelime uzunluguna gore ORANTILI tahmin uret — altyazi kabaca dogru kalir, is olmez.
def _oai_anahtar():
    return os.environ.get("OPENAI_KEY") or os.environ.get("OPENAI_API_KEY") or ""


def _orantili_zaman(metin: str, toplam: float):
    """Whisper yoksa: kelime uzunluguna gore sureyi bol. Kusursuz degil ama altyazi
    tamamen kaymaz ve is olmez."""
    kel = [k for k in (metin or "").split() if k]
    if not kel or toplam <= 0:
        return []
    agirlik = [max(1, len(k)) for k in kel]
    top = sum(agirlik)
    out, t = [], 0.0
    for k, a in zip(kel, agirlik):
        d = toplam * a / top
        out.append({"t0": t, "t1": t + d, "kelime": k})
        t += d
    return out


def _whisper_zamanlari(mp3_yolu: str):
    """whisper-1 ile KELIME bazli zaman damgasi. Hata olursa [] doner (cagiran tahmine duser)."""
    key = _oai_anahtar()
    if not key:
        return []
    try:
        import urllib.request, uuid, json as _json
        sinir = "----bedosaho" + uuid.uuid4().hex
        with open(mp3_yolu, "rb") as f:
            ses_veri = f.read()
        parcalar = []
        for ad, deger in (("model", "whisper-1"), ("response_format", "verbose_json"),
                          ("timestamp_granularities[]", "word")):
            parcalar.append(f"--{sinir}\r\nContent-Disposition: form-data; name=\"{ad}\"\r\n\r\n{deger}\r\n".encode())
        parcalar.append(
            f"--{sinir}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"a.mp3\"\r\n"
            f"Content-Type: audio/mpeg\r\n\r\n".encode() + ses_veri + b"\r\n")
        parcalar.append(f"--{sinir}--\r\n".encode())
        govde = b"".join(parcalar)
        r = urllib.request.Request(
            "https://api.openai.com/v1/audio/transcriptions", data=govde,
            headers={"Authorization": f"Bearer {key}",
                     "Content-Type": f"multipart/form-data; boundary={sinir}"})
        with urllib.request.urlopen(r, timeout=180) as y:
            j = _json.loads(y.read().decode())
        return [{"t0": float(w["start"]), "t1": float(w["end"]), "kelime": w["word"]}
                for w in (j.get("words") or []) if w.get("word")]
    except Exception as e:
        print(f"  whisper hizalama basarisiz (orantili tahmine dusuluyor): {str(e)[:140]}",
              file=sys.stderr)
        return []


async def seslendir_openai(metin: str, mp3_yolu: str, ses: str = "shimmer",
                           talimat: str = "", hiz: float = 0.92):
    key = _oai_anahtar()
    if not key:
        raise RuntimeError("OPENAI_KEY yok — OpenAI sesi kullanilamaz")
    import urllib.request, json as _json
    govde = {"model": "gpt-4o-mini-tts", "voice": ses, "input": metin,
             "response_format": "mp3", "speed": max(0.5, min(1.5, float(hiz)))}
    if talimat:
        govde["instructions"] = talimat
    r = urllib.request.Request(
        "https://api.openai.com/v1/audio/speech", data=_json.dumps(govde).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    veri = await asyncio.to_thread(lambda: urllib.request.urlopen(r, timeout=180).read())
    with open(mp3_yolu, "wb") as f:
        f.write(veri)
    olculen = _ses_suresi(mp3_yolu)
    kelimeler = await asyncio.to_thread(_whisper_zamanlari, mp3_yolu)
    if not kelimeler:
        kelimeler = _orantili_zaman(metin, olculen)
    kuyruk = float(os.environ.get("TTS_KUYRUK", "0.30"))
    sure = max((kelimeler[-1]["t1"] + kuyruk) if kelimeler else 0,
               (olculen + 0.12) if olculen else 0,
               max(2.5, len(metin.split()) * 0.40))
    return kelimeler, sure


def _ai33_anahtar():
    """Ai33.Pro anahtari: env AI33_KEY veya /opt/vidrush/AI33_KEY dosyasi.
    Anahtar GIT'E GIRMEZ — sadece sunucuda durur (docker commit ile kalici)."""
    k = os.environ.get("AI33_KEY", "").strip()
    if not k:
        try:
            with open(os.path.join(os.environ.get("VIDRUSH_KOK", "/opt/vidrush"),
                                   "AI33_KEY")) as f:
                k = f.read().strip()
        except Exception:
            k = ""
    return k


async def seslendir_ai33(metin: str, mp3_yolu: str,
                         voice_id: str = "elevenlabs_21m00Tcm4TlvDq8ikWAM", hiz: float = 1.0):
    """Ai33.Pro — tek anahtarla premium TTS (ElevenLabs/MiniMax/FishAudio...). Asenkron API:
    POST -> task_id -> poll -> mp3 + KELIME BAZLI transkript (altyazi senkronu buradan gelir).
    Kisa cumle ~35 kredi. voice_id saglayici onekli: elevenlabs_XXX, minimax_XXX..."""
    key = _ai33_anahtar()
    if not key:
        raise RuntimeError("AI33_KEY yok — premium ses kullanilamaz")
    import requests

    def _basla():
        r = requests.post("https://api.ai33.pro/v3/text-to-speech",
                          headers={"xi-api-key": key},
                          data={"text": metin, "voice_id": voice_id,
                                "speed": str(max(0.5, min(1.5, float(hiz)))),
                                "with_transcript": "true"},
                          timeout=60)
        r.raise_for_status()
        j = r.json()
        if not j.get("success") or not j.get("task_id"):
            raise RuntimeError(f"ai33 baslatilamadi: {str(j)[:150]}")
        return j["task_id"]

    def _bekle(tid):
        bas = time.time()
        while time.time() - bas < 240:
            time.sleep(3)
            try:
                j = requests.get(f"https://api.ai33.pro/v3/task/{tid}",
                                 headers={"xi-api-key": key}, timeout=30).json()
            except Exception:
                continue
            if not j.get("success"):
                continue   # server_busy vb. gecici durumlar -> tekrar dene
            d = j.get("data", {})
            if d.get("status") == "done":
                return d.get("metadata", {})
            if d.get("status") in ("failed", "error", "cancelled"):
                raise RuntimeError(f"ai33 task basarisiz: {str(d)[:150]}")
        raise RuntimeError("ai33 zaman asimi (240s)")

    def _indir(meta):
        au = meta.get("audio_url")
        if not au:
            raise RuntimeError("ai33 audio_url donmedi")
        with open(mp3_yolu, "wb") as f:
            f.write(requests.get(au, timeout=120).content)
        kel = []
        ju = meta.get("json_url")
        if ju:
            try:
                for blok in requests.get(ju, timeout=60).json():
                    for w in blok.get("words", []):
                        if w.get("type") == "word" and str(w.get("text", "")).strip():
                            kel.append({"t0": float(w["start"]), "t1": float(w["end"]),
                                        "kelime": str(w["text"]).strip()})
            except Exception:
                kel = []   # transkript alinamazsa orantili zamana duseriz
        return kel

    tid = await asyncio.to_thread(_basla)
    meta = await asyncio.to_thread(_bekle, tid)
    kelimeler = await asyncio.to_thread(_indir, meta)
    olculen = _ses_suresi(mp3_yolu)
    if not kelimeler:
        kelimeler = _orantili_zaman(metin, olculen)
    kuyruk = float(os.environ.get("TTS_KUYRUK", "0.30"))
    sure = max((kelimeler[-1]["t1"] + kuyruk) if kelimeler else 0,
               (olculen + 0.12) if olculen else 0,
               max(1.6, len(metin.split()) * 0.40))
    return kelimeler, sure


async def seslendir(metin: str, ses: str, mp3_yolu: str, ayar: dict = None):
    """ayar['motor']: 'openai' -> gpt-4o-mini-tts, 'ai33' -> Ai33.Pro premium, yoksa edge-tts."""
    if ayar and ayar.get("motor") == "openai":
        return await seslendir_openai(metin, mp3_yolu, ayar.get("ses") or "shimmer",
                                      ayar.get("talimat") or "", ayar.get("hiz") or 0.92)
    if ayar and ayar.get("motor") == "ai33":
        return await seslendir_ai33(metin, mp3_yolu,
                                    ayar.get("ses") or "elevenlabs_21m00Tcm4TlvDq8ikWAM",
                                    ayar.get("hiz") or 1.0)
    return await _seslendir_edge(metin, ses, mp3_yolu)


async def _seslendir_edge(metin: str, ses: str, mp3_yolu: str):
    # HIZ: edge-tts varsayilani ~100-110 kelime/dk cikiyordu (yavas, sahneler hedeften uzun).
    # Referans videolarin temposu icin +%15 hiz. TTS_RATE env'i ile ayarlanir ("+0%" = kapali).
    hiz = os.environ.get("TTS_RATE", "+15%")
    try:
        com = edge_tts.Communicate(metin, ses, rate=hiz)
    except TypeError:      # eski edge-tts imzasi
        com = edge_tts.Communicate(metin, ses)
    kelimeler = []
    with open(mp3_yolu, "wb") as f:
        async for olay in com.stream():
            if olay["type"] == "audio":
                f.write(olay["data"])
            elif olay["type"] == "WordBoundary":
                t0 = olay["offset"] / TICK
                t1 = (olay["offset"] + olay["duration"]) / TICK
                kelimeler.append({"t0": t0, "t1": t1, "kelime": olay["text"]})
    # Gercek dosya suresini olc; sahne, sesten KISA olmasin (anlatim kesilmesin).
    olculen = _ses_suresi(mp3_yolu)
    # Sahne sonu bosluk: 0.55 -> 0.30 sn. Referans videolarda olu hava az (%25 sessizlik);
    # her sahnede 0.25 sn kazanc, 100 sahnede 25 sn daha sikilastirilmis akis.
    kuyruk = float(os.environ.get("TTS_KUYRUK", "0.30"))
    if kelimeler:
        sure = max(kelimeler[-1]["t1"] + kuyruk, (olculen + 0.12) if olculen else 0)
    else:
        sure = (olculen + kuyruk) if olculen else max(2.5, len(metin.split()) * 0.40)
    return kelimeler, max(1.6, sure)


def altyazi_parcala(kelimeler, sure):
    parcalar, grup = [], []
    for k in kelimeler:
        grup.append(k)
        if len(grup) >= 4 or k["kelime"].rstrip().endswith((".", ",", "!", "?", ":", ";")):
            parcalar.append({"t0": round(grup[0]["t0"], 3),
                             "t1": round(min(grup[-1]["t1"] + 0.25, sure), 3),
                             "metin": " ".join(g["kelime"].strip() for g in grup)})
            grup = []
    if grup:
        parcalar.append({"t0": round(grup[0]["t0"], 3),
                         "t1": round(min(grup[-1]["t1"] + 0.25, sure), 3),
                         "metin": " ".join(g["kelime"].strip() for g in grup)})
    return parcalar


async def calistir(payload: dict) -> dict:
    is_adi = payload["is_adi"]
    ses = payload.get("voice", "en-US-AndrewMultilingualNeural")
    is_dizini = os.path.join(PUBLIC, "isler", is_adi)
    os.makedirs(is_dizini, exist_ok=True)
    os.makedirs(os.path.join(STUDYO, "out"), exist_ok=True)

    panlar = ["right", "left", "top", "bottom"]
    sahneler = sorted(payload["sahneler"], key=lambda s: s.get("n", 0))
    props_sahneler = []
    for i, s in enumerate(sahneler):
        n = s.get("n", i + 1)
        metin = (s.get("voiceover") or "").strip()
        prompt = (s.get("image_prompt") or "").strip()
        kaynak_tur = s.get("source", "ai")
        sorgu = (s.get("stock_query") or "").strip()
        if not metin:
            continue

        tur = "image"
        medya = None
        # 1) stok denemesi
        if kaynak_tur == "stock" and sorgu:
            yol = f"isler/{is_adi}/stok_{n}.mp4"
            print(f"sahne {n}: pexels '{sorgu}'...", file=sys.stderr)
            if pexels_video(sorgu, os.path.join(PUBLIC, yol)):
                medya, tur = yol, "video"
        # 2) AI gorsel (stok yoksa ya da source=ai)
        if medya is None and prompt:
            yol = f"isler/{is_adi}/sahne_{n}.png"
            print(f"sahne {n}: AI gorsel...", file=sys.stderr)
            if openai_gorsel(prompt, os.path.join(PUBLIC, yol)):
                medya, tur = yol, "image"
            time.sleep(13)  # OpenAI Tier1 hiz limiti
        if medya is None:
            print(f"sahne {n} atlandi (gorsel uretilemedi)", file=sys.stderr)
            continue

        ses_dosya = f"isler/{is_adi}/ses_{n}.mp3"
        print(f"sahne {n}: seslendiriliyor...", file=sys.stderr)
        kelimeler, sure = await seslendir(metin, ses, os.path.join(PUBLIC, ses_dosya))
        props_sahneler.append({
            "tur": tur, "medya": medya, "ses": ses_dosya, "sure": round(sure, 3),
            "zoom": "in" if i % 2 == 0 else "out", "pan": panlar[i % 4],
            "altyazi": altyazi_parcala(kelimeler, sure),
        })

    if not props_sahneler:
        raise SystemExit("Hic gecerli sahne yok (gorseller uretilemedi)")

    # Kapak
    kapak_yolu = None
    kp = (payload.get("kapak_prompt") or "").strip()
    if kp:
        hedef = os.path.join(is_dizini, "kapak.png")
        print("kapak uretiliyor...", file=sys.stderr)
        if openai_gorsel(kp, hedef, model="gpt-image-1.5", kalite="high"):
            kapak_yolu = hedef

    props = {"fps": 30, "genislik": 1920, "yukseklik": 1080, "sahneler": props_sahneler}
    props_yolu = os.path.join(is_dizini, "props.json")
    with open(props_yolu, "w") as f:
        json.dump(props, f, ensure_ascii=False)

    cikti = os.path.join(STUDYO, "out", f"{is_adi}.mp4")
    log_yolu = os.path.join(STUDYO, "out", f"{is_adi}_render.log")

    def logla(baslik, r):
        with open(log_yolu, "a") as lf:
            lf.write(f"\n===== {baslik} (exit={r.returncode}) =====\n")
            lf.write("STDOUT:\n" + (r.stdout or "")[-4000:] + "\n")
            lf.write("STDERR:\n" + (r.stderr or "")[-4000:] + "\n")

    print("remotion render basliyor...", file=sys.stderr)
    # concurrency=1 SART: VPS 1 vCPU, config'teki 4 hata verir
    # scale=0.6667 -> 1080p kompozisyon 720p ciktisi (dosya kucuk + render hizli, Telegram 50MB limiti)
    # crf=30 -> ek sikistirma (kalite/boyut dengesi)
    komut = ["npx", "remotion", "render", "src/index.ts", "VidrushVideo", cikti,
             f"--props={props_yolu}", "--concurrency=1", "--timeout=120000",
             "--scale=0.6667", "--crf=30"]
    if os.environ.get("REMOTION_BROWSER_EXECUTABLE"):
        komut.append(f"--browser-executable={os.environ['REMOTION_BROWSER_EXECUTABLE']}")
    if os.environ.get("REMOTION_GL"):
        komut.append(f"--gl={os.environ['REMOTION_GL']}")
    sonuc = subprocess.run(komut, cwd=STUDYO, capture_output=True, text=True, timeout=5400)
    logla("render", sonuc)
    if sonuc.returncode != 0:
        print(sonuc.stdout[-2000:], file=sys.stderr)
        print(sonuc.stderr[-2000:], file=sys.stderr)
        raise SystemExit(f"Remotion render basarisiz (log: {log_yolu})")

    # n8n readWriteFile sadece /home/node/.n8n-files'i okuyabiliyor -> son dosyalari oraya kopyala
    import shutil
    n8nfiles = "/home/node/.n8n-files"
    os.makedirs(n8nfiles, exist_ok=True)
    son_video = os.path.join(n8nfiles, f"{is_adi}.mp4")
    shutil.copy(cikti, son_video)
    son_kapak = None
    if kapak_yolu and os.path.exists(kapak_yolu):
        son_kapak = os.path.join(n8nfiles, f"{is_adi}_kapak.png")
        shutil.copy(kapak_yolu, son_kapak)

    toplam = round(sum(s["sure"] for s in props_sahneler), 1)
    return {"video": son_video, "kapak": son_kapak, "sure": toplam,
            "sahne_sayisi": len(props_sahneler)}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("Kullanim: uret.py <base64_payload | payload.json>")
    veri = payload_oku(sys.argv[1])
    sonuc = asyncio.run(calistir(veri))
    print(json.dumps(sonuc, ensure_ascii=False))
