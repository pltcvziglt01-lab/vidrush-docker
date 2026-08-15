#!/usr/bin/env python3
"""FAZ Y-7 — FACT ZINCIRI PROPS SINIRINDA KOPUYORDU.

⚠ OLCULEN KUSUR (`Y7-FACT-PROPS-SINIRI`) — gercek is
job_1786787306483_y21248_d01800:
    EDIT PLANI: QA=FAIL render_edilebilir=False
    FACT-BAGLANTI-YOK (fail) x22 — "cekim hicbir fact_id'ye bagli degil"
    TESLIM: False | KABUL-YOK:Y1-KURGU-QA-FAIL

⚠ KOK NEDEN (kanit zinciri):
  1. `arastirma_kopru.fact_bagla()` fact_id'yi GERCEKTEN yaziyor
     (`arastirma_kopru.py:278` -> `s["fact_id"] = ...`), ve ayni `s`
     sozlugu medya avcisina fact_id'yi BASARIYLA veriyor
     (`pipeline.py:4315`).
  2. AMA `props_sahneler.append({...})` sozlugu `fact_id` anahtarini HIC
     ICERMIYOR.
  3. `pipeline.py:5258` plan girdisini `props_sahneler`'den kuruyor:
     `"fact_id": str(x.get("fact_id") or "")` -> her cumle icin `""`.
  4. `beat.py:231` bos -> `gramer.py:338` `Cekim.fact_id=""` ->
     `qa_on.py:309` HER cekim icin fail.
22/22 fail bunu dogruluyor: kismi bir baglama olsaydi en az bir cekim
gecerdi.

⚠ Bu, `scene_id` (R-1d-b) ve `anlatim` (R-1d-b) ile BIREBIR AYNI SINIF
kusurdur: uretim tarafinda veri VAR, props sinirinda DUSUYOR.

⚠ KAPI GEVSETILMEZ: `FACT-BAGLANTI-YOK` fail olarak KALIR (Y-4). Bu faz
kapiyi degil, ZINCIRI onarir.

Kosum: .venv-test/bin/python3 webapp/testler/test_faz_y7.py
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


def oku(*p):
    with open(os.path.join(KOK, *p), encoding="utf-8") as f:
        return f.read()


_P = oku("pipeline.py")
_QAON = oku("editor", "qa_on.py")

# props montaj blogu (scene_id'den kumulatif_sn'e kadar)
_bas = _P.find("props_sahneler.append({")
_son = _P.find("kumulatif_sn += sure", _bas)
_MONTAJ = _P[_bas:_son] if _bas > 0 and _son > _bas else ""


blok("Y-7/1 — FACT_ID PROPS SINIRINI GECIYOR")

kontrol("props montaj blogu bulundu", bool(_MONTAJ))
kontrol("stabil kod belgelendi: Y7-FACT-PROPS-SINIRI",
        "Y7-FACT-PROPS-SINIRI" in _P,
        "karar kodda belgelenmemis")
kontrol("props `fact_id` TASIYOR",
        '"fact_id"' in _MONTAJ,
        "fact_id props sinirinda dusuyor -> her cekim FACT-BAGLANTI-YOK")
kontrol("fact_id sahne sozlugunden (`s`) turetiliyor",
        re.search(r'"fact_id":\s*str\(s\.get\("fact_id"\)', _MONTAJ)
        is not None,
        "kaynak yanlis")
kontrol("izlenebilirlik icin `iddia_metni` de tasiniyor",
        '"iddia_metni"' in _MONTAJ,
        "iddia metni yok — atif/izlenebilirlik zayif")


blok("Y-7/2 — PLAN GIRDISI ARTIK DOLU FACT_ID ALIYOR")

kontrol("plan girdisi props'tan fact_id okuyor (zincir kapali)",
        re.search(r'cumleler=\[\{[\s\S]{0,400}"fact_id":\s*str\(x\.get\("fact_id"\)',
                  _P) is not None,
        "plan girdisi fact_id okumuyor")


blok("Y-7/3 — KAPI GEVSETILMEDI (Y-4 sozlesmesi)")

kontrol("FACT-BAGLANTI-YOK hala FAIL seviyesinde",
        "FACT-BAGLANTI-YOK" in _QAON,
        "kapi kaldirilmis")
_fail_blok = _QAON[_QAON.find("FAIL_KODLARI"):
                   _QAON.find("FAIL_KODLARI") + 700]
kontrol("FACT-BAGLANTI-YOK FAIL_KODLARI icinde",
        "FACT-BAGLANTI-YOK" in _fail_blok,
        "fail listesinden dusurulmus")

import kutuphane                                            # noqa: E402
kontrol("teslim kapisi hala fail-closed (Y-4)",
        kutuphane.kabul_edilebilir_mi(
            {"durum": "bitti", "video": "x.mp4", "qa": {"durum": "PASS"},
             "edit_plani": {"ok": True, "render_edilebilir": False,
                            "qa": {"durum": "FAIL", "sorunlar": [
                                {"kod": "FACT-BAGLANTI-YOK",
                                 "seviye": "fail"}]}}})["kabul"] is False)
kontrol("YAYIN_KAPILARI daraltmasi geri gelmedi",
        not hasattr(kutuphane, "YAYIN_KAPILARI"))


blok("Y-7/4 — GERILEME YOK: PROPS SOZLESMESI")

kontrol("GERILEME YOK: scene_id duruyor (R-1d-b)",
        '"scene_id"' in _MONTAJ)
kontrol("GERILEME YOK: anlatim duruyor (R-1d-b)",
        '"anlatim": metin' in _MONTAJ)
kontrol("GERILEME YOK: kaynakYazi props'u duruyor (I-41)",
        "_kaynak_yazi_props(s)" in _MONTAJ)
kontrol("GERILEME YOK: Y-6 J/L uretimi duruyor",
        "Y6-JL-URETIM" in oku("hizli_render.py"))
kontrol("GERILEME YOK: Y-5 yeniden kullanim geri gelmedi",
        "UI8-SURE-KORUNDU" not in _P)
kontrol("GERILEME YOK: %100 video profilleri duruyor",
        _P.count('"footage_pct": 100') >= 5)
kontrol("GERILEME YOK: UI-8 fps 30 duruyor",
        'os.environ.get("VIDEO_FPS", "30")' in _P)

print(f"\n{'=' * 60}")
print(f"GECEN: {gecen}   BASARISIZ: {len(basarisiz)}")
for b in basarisiz:
    print(f"  XX {b}")
sys.exit(1 if basarisiz else 0)
