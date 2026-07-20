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


async def seslendir(metin: str, ses: str, mp3_yolu: str):
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
    sure = kelimeler[-1]["t1"] + 0.55 if kelimeler else max(2.5, len(metin.split()) * 0.45)
    return kelimeler, max(2.0, sure)


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
    print("remotion render basliyor...", file=sys.stderr)
    komut = ["npx", "remotion", "render", "src/index.ts", "VidrushVideo", cikti,
             f"--props={props_yolu}"]
    if os.environ.get("REMOTION_BROWSER_EXECUTABLE"):
        komut.append(f"--browser-executable={os.environ['REMOTION_BROWSER_EXECUTABLE']}")
    if os.environ.get("REMOTION_GL"):
        komut.append(f"--gl={os.environ['REMOTION_GL']}")
    sonuc = subprocess.run(komut, cwd=STUDYO, capture_output=True, text=True, timeout=5400)
    if sonuc.returncode != 0:
        print(sonuc.stdout[-1500:], file=sys.stderr)
        print(sonuc.stderr[-1500:], file=sys.stderr)
        raise SystemExit("Remotion render basarisiz")

    toplam = round(sum(s["sure"] for s in props_sahneler), 1)
    return {"video": cikti, "kapak": kapak_yolu, "sure": toplam,
            "sahne_sayisi": len(props_sahneler)}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("Kullanim: uret.py <base64_payload | payload.json>")
    veri = payload_oku(sys.argv[1])
    sonuc = asyncio.run(calistir(veri))
    print(json.dumps(sonuc, ensure_ascii=False))
