#!/usr/bin/env python3
"""FAZ Y-2 — RENDER ZAMAN BUTCESI 1080p30 GERCEGINE UYAR.

⚠ OLCULEN KUSUR (`Y2-RENDER-TIMEOUT-DAR`) — gercek is
job_1786784567124_ui8120_aea2e9 (%90'da dustu):

    RuntimeError: Render zaman aşımına uğradı (30 dk). Daha kısa süre deneyin.

Is ICERIK olarak TAM HEDEFTEYDI:
    footage OK 17/17 · MEDYA-VIDEO-YOK 0 · UI8-SURE-KORUNDU 0
    uretilmis-eser 0 · magnific 0
    RENDER-QA (gercek timeline): sahne=17 kapsam=1.0 gercek_video=1.0
Yani %100 gercek video hedefi TUTTU; video YALNIZCA render butcesi
yetmedigi icin kaybedildi.

KOK NEDEN: `render_timeout = min(46800, max(1800, sure_dk * 720))`
  · 2 dk -> max(1800, 1440) = 1800 sn = 30 dk
Bu formul 24 fps donemine aitti. UI-8 ile render 30 fps'e cikti (POST-QA
ile hizalanmak icin) ve kare sayisi ~%25 artti; 17 segmentlik 1080p30
kompozisyon 30 dk'ya SIGMIYOR.

⚠ BU FAZ KALITE KAPILARINI GEVSETMEZ: yalnizca zaman butcesini gercek
olcume gore buyutur. Uretim davranisi, QA hukmu ve teslim kapisi AYNI.

Kosum: .venv-test/bin/python3 webapp/testler/test_faz_y2.py
"""
from __future__ import annotations

import os
import re
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)

gecen, basarisiz = 0, []


def kontrol(ad, kosul, detay=""):
    global gecen
    if kosul:
        gecen += 1
        print(f"  ok   {ad}")
    else:
        basarisiz.append(f"{ad} — {detay}")
        print(f"  XX   {ad}  {detay}")


def blok(ad):
    print(f"\n── {ad} ──")


with open(os.path.join(KOK, "pipeline.py"), encoding="utf-8") as f:
    _P = f.read()

_m = re.search(r"render_timeout = int\(min\((\d+), max\((\d+), "
               r"sure_dk \* (\d+)\)\)\)", _P)


def _butce(sure_dk: float) -> int:
    """Kodun formulunu AYNEN uygular (kaynaktan okunur)."""
    if not _m:
        return -1
    ust, alt, kat = int(_m.group(1)), int(_m.group(2)), int(_m.group(3))
    return int(min(ust, max(alt, sure_dk * kat)))


blok("Y-2/1 — BUTCE 1080p30 OLCUMUNE UYUYOR")

kontrol("render_timeout formulu bulundu", _m is not None,
        "formul degismis")
kontrol("stabil kod belgelendi: Y2-RENDER-TIMEOUT",
        "Y2-RENDER-TIMEOUT" in _P,
        "karar kodda belgelenmemis")
# Olculen gercek: 2 dk / 17 segment / 1080p30 render 30 dk'yi ASTI.
kontrol("2 dk is icin butce >= 60 dk (olculen 30 dk YETMEDI)",
        _butce(2) >= 3600, f"butce={_butce(2)} sn")
kontrol("1.5 dk (90 sn) is icin butce >= 45 dk",
        _butce(1.5) >= 2700, f"butce={_butce(1.5)} sn")
kontrol("butce sure ile ORANTILI buyuyor",
        _butce(4) > _butce(2), f"{_butce(2)} -> {_butce(4)}")


blok("Y-2/2 — GERILEME YOK: UST SINIR VE KALITE KAPILARI")

kontrol("GERILEME YOK: ust sinir korunuyor (sonsuz bekleme YOK)",
        _butce(999) <= 46800, f"butce={_butce(999)}")
kontrol("GERILEME YOK: zaman asimi hala STABIL hata veriyor",
        "Render zaman aşımına uğradı" in _P)
kontrol("GERILEME YOK: Y-1 kurgu QA kapisi duruyor",
        "Y1-KURGU-QA-FAIL" in open(
            os.path.join(KOK, "kutuphane.py"), encoding="utf-8").read())
kontrol("GERILEME YOK: UI-8 fps 30 duruyor",
        'os.environ.get("VIDEO_FPS", "30")' in _P)
kontrol("GERILEME YOK: UI-8 magnific kapali duruyor",
        "UI8-MAGNIFIC-KAPALI" in _P)
kontrol("GERILEME YOK: Y-5 — yeniden kullanim yolu geri GELMEDI",
        "UI8-SURE-KORUNDU" not in _P)
kontrol("GERILEME YOK: UI-7 gorsel yasak kapisi duruyor",
        "UI7-GORSEL-YASAK-KAPISI" in _P)
kontrol("GERILEME YOK: %100 video profilleri duruyor",
        _P.count('"footage_pct": 100') >= 5)
kontrol("GERILEME YOK: 1920x1080 sabit",
        '"genislik": 1920, "yukseklik": 1080' in _P)

print(f"\n{'=' * 60}")
print(f"GECEN: {gecen}   BASARISIZ: {len(basarisiz)}")
for b in basarisiz:
    print(f"  XX {b}")
sys.exit(1 if basarisiz else 0)
