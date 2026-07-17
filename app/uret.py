#!/usr/bin/env python3
"""Vidrush yerel render orkestrasi.
Girdi: base64 kodlu JSON (argv[1]) ya da JSON dosya yolu.
  { "is_adi": "is_123", "voice": "tr-TR-EmelNeural",
    "sahneler": [ { "n":1, "voiceover":"...", "gorsel_url":"isler/.../sahne_1.png ya da https://...", "tur":"image|video" } ] }
Yapilanlar: edge-tts ile seslendirme (+kelime zamanlari -> altyazi),
stok videolari indirme, Remotion ile 1080p render.
Cikti (stdout son satir): {"video": "<mutlak yol>", "sure": <saniye>}
"""
import asyncio
import base64
import json
import os
import subprocess
import sys
import urllib.request

import edge_tts

KOK = os.path.dirname(os.path.abspath(__file__))
STUDYO = os.path.join(KOK, "render-studio")
PUBLIC = os.path.join(STUDYO, "public")

TICK = 10_000_000  # 100ns -> saniye


def payload_oku(arg: str) -> dict:
    if os.path.exists(arg):
        with open(arg) as f:
            return json.load(f)
    return json.loads(base64.b64decode(arg))


def indir(url: str, hedef: str) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as r, open(hedef, "wb") as f:
        while True:
            parca = r.read(1 << 16)
            if not parca:
                break
            f.write(parca)


async def seslendir(metin: str, ses: str, mp3_yolu: str):
    """Ses dosyasini uretir; (kelime_listesi, toplam_sure) dondurur."""
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
    if kelimeler:
        sure = kelimeler[-1]["t1"] + 0.55
    else:
        sure = max(2.5, len(metin.split()) * 0.45)
    return kelimeler, max(2.0, sure)


def altyazi_parcala(kelimeler, sure):
    """Kelime zamanlarini 3-5 kelimelik altyazi parcalarina boler."""
    parcalar = []
    grup = []
    for k in kelimeler:
        grup.append(k)
        bitir = len(grup) >= 4 or k["kelime"].rstrip().endswith((".", ",", "!", "?", ":", ";"))
        if bitir:
            parcalar.append({
                "t0": round(grup[0]["t0"], 3),
                "t1": round(min(grup[-1]["t1"] + 0.25, sure), 3),
                "metin": " ".join(g["kelime"].strip() for g in grup),
            })
            grup = []
    if grup:
        parcalar.append({
            "t0": round(grup[0]["t0"], 3),
            "t1": round(min(grup[-1]["t1"] + 0.25, sure), 3),
            "metin": " ".join(g["kelime"].strip() for g in grup),
        })
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
        kaynak = (s.get("gorsel_url") or "").strip()
        tur = "video" if s.get("tur") == "video" else "image"
        if not metin or not kaynak:
            print(f"sahne {n} atlandi (eksik veri)", file=sys.stderr)
            continue

        if kaynak.startswith("http"):
            uzanti = ".mp4" if tur == "video" else ".jpg"
            yerel = f"isler/{is_adi}/indirilen_{n}{uzanti}"
            print(f"sahne {n}: indiriliyor...", file=sys.stderr)
            indir(kaynak, os.path.join(PUBLIC, yerel))
            medya = yerel
        else:
            medya = kaynak

        ses_dosya = f"isler/{is_adi}/ses_{n}.mp3"
        print(f"sahne {n}: seslendiriliyor...", file=sys.stderr)
        kelimeler, sure = await seslendir(metin, ses, os.path.join(PUBLIC, ses_dosya))
        props_sahneler.append({
            "tur": tur,
            "medya": medya,
            "ses": ses_dosya,
            "sure": round(sure, 3),
            "zoom": "in" if i % 2 == 0 else "out",
            "pan": panlar[i % 4],
            "altyazi": altyazi_parcala(kelimeler, sure),
        })

    if not props_sahneler:
        raise SystemExit("Hic gecerli sahne yok")

    props = {
        "fps": 30,
        "genislik": 1920,
        "yukseklik": 1080,
        "sahneler": props_sahneler,
    }
    props_yolu = os.path.join(is_dizini, "props.json")
    with open(props_yolu, "w") as f:
        json.dump(props, f, ensure_ascii=False)

    cikti = os.path.join(STUDYO, "out", f"{is_adi}.mp4")
    print("remotion render basliyor...", file=sys.stderr)
    komut = ["npx", "remotion", "render", "src/index.ts", "VidrushVideo", cikti,
             f"--props={props_yolu}"]
    # Docker/Linux icin Chromium bayraklari (env ile verilir; host'ta bos)
    chrome = os.environ.get("REMOTION_BROWSER_EXECUTABLE")
    if chrome:
        komut.append(f"--browser-executable={chrome}")
    gl = os.environ.get("REMOTION_GL")
    if gl:
        komut.append(f"--gl={gl}")
    sonuc = subprocess.run(
        komut, cwd=STUDYO, capture_output=True, text=True, timeout=3600,
    )
    if sonuc.returncode != 0:
        print(sonuc.stdout[-1500:], file=sys.stderr)
        print(sonuc.stderr[-1500:], file=sys.stderr)
        raise SystemExit("Remotion render basarisiz")

    toplam = round(sum(s["sure"] for s in props_sahneler), 1)
    return {"video": cikti, "sure": toplam, "sahne_sayisi": len(props_sahneler)}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("Kullanim: uret.py <base64_payload | payload.json>")
    veri = payload_oku(sys.argv[1])
    sonuc = asyncio.run(calistir(veri))
    print(json.dumps(sonuc, ensure_ascii=False))
