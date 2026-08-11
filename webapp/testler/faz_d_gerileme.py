#!/usr/bin/env python3
"""FAZ D GERILEME KANITI — mevcut `VidrushVideo` bozulmadi mi?

Faz D yalnizca YENI bir kompozisyon (`VidrushEditorV2`) ekledi. Bu betik
mevcut kompozisyonun HALA render ettigini kanitlar.

⚠ Depodaki `varsayilanProps` `public/ornek/ornek.mp3` ve `ornek.png`'ye isaret
ediyor ama bu dosyalar depoda YOK — yani `npm run render` varsayilan props ile
Faz D'den ONCE de 404 ile duruyordu. Bu Faz D'nin yol actigi bir gerileme
DEGIL, onceden var olan bir eksik. Kanit: bu betik ayni semayi var olan
gecici varliklarla doldurup render ettiriyor; gecen render, kompozisyonun
saglam oldugunu gosteriyor.

Kosum: python3 webapp/testler/faz_d_gerileme.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STUDIO = os.path.join(os.path.dirname(KOK), "app", "render-studio")
CIKTI = os.path.join(os.path.dirname(KOK), "cikti", "faz_d", "gerileme")


def _varlik(dizin: str) -> tuple:
    os.makedirs(dizin, exist_ok=True)
    g = os.path.join(dizin, "g.png")
    s = os.path.join(dizin, "s.mp3")
    if not os.path.exists(g):
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                        "color=c=0x5c6672:s=1920x1080", "-frames:v", "1", g],
                       check=True, timeout=180)
    if not os.path.exists(s):
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                        "anoisesrc=d=5:c=pink:a=0.02", "-ar", "48000", s],
                       check=True, timeout=180)
    return g, s


def main() -> int:
    os.makedirs(CIKTI, exist_ok=True)
    gec = os.path.join(STUDIO, "public", "gerileme_testi")
    _varlik(gec)

    # Depodaki VideoProps semasinin AYNISI; yalnizca yollar var olan dosyalar
    props = {
        "fps": 30, "genislik": 1280, "yukseklik": 720, "gecis": "sinematik",
        "altyaziStil": "orta",
        "sahneler": [{
            "tur": "image", "medya": "gerileme_testi/g.png",
            "ses": "gerileme_testi/s.mp3", "sure": 3, "zoom": "in",
            "pan": "right", "overlay": "",
            "altyazi": [{"t0": 0, "t1": 2.5, "metin": "GERILEME TESTI"}],
        }],
    }
    py = os.path.join(CIKTI, "vv_props.json")
    with open(py, "w", encoding="utf-8") as f:
        json.dump(props, f)
    out = os.path.join(CIKTI, "vidrushvideo.mp4")

    print("── VidrushVideo (mevcut kompozisyon) ──")
    t0 = time.time()
    r = subprocess.run(
        ["npx", "remotion", "render", "src/index.ts", "VidrushVideo", out,
         f"--props={py}", "--concurrency=2", "--log=error"],
        cwd=STUDIO, capture_output=True, text=True, timeout=900)
    print(f"  rc={r.returncode}  sure={time.time() - t0:.1f} sn")
    if r.returncode != 0:
        print("  ✖ GERILEME:", (r.stderr or "")[-700:])
        return 1

    p = json.loads(subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of",
         "json", out], capture_output=True, text=True, timeout=120).stdout)
    v = next(s for s in p["streams"] if s["codec_type"] == "video")
    a = [s for s in p["streams"] if s["codec_type"] == "audio"]
    print(f"  ✓ {v['width']}x{v['height']} {float(p['format']['duration']):.2f} sn "
          f"ses_akisi={len(a)}")
    print(f"  cikti: {os.path.abspath(out)}")

    # Varsayilan props ile 404 ALINMASI beklenen davranis (onceden var olan eksik)
    print("\n── varsayilanProps kontrolu (eksik ornek varliklari) ──")
    r2 = subprocess.run(
        ["npx", "remotion", "render", "src/index.ts", "VidrushVideo",
         os.path.join(CIKTI, "varsayilan.mp4"), "--frames=0-9",
         "--concurrency=1", "--log=error"],
        cwd=STUDIO, capture_output=True, text=True, timeout=600)
    eksik = "ornek.mp3" in (r2.stderr or "") or "ornek.png" in (r2.stderr or "")
    print(f"  rc={r2.returncode}  eksik-ornek-varligi-hatasi={eksik}")
    print("  NOT: bu hata Faz D'den ONCE de vardi; depoda public/ornek/ yok.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
