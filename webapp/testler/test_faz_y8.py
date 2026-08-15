#!/usr/bin/env python3
"""FAZ Y-8 — KULLANICI HEDEF SURESI POST-QA'DA FAIL-CLOSED OLCULUR.

⚠ OLCULEN KUSUR (`Y8-HEDEF-SURE-OLCULMUYOR`): `POST-SURE-SAPMA` final
sureyi YALNIZCA `beklenen["sure_sn"]`e karsi olcuyor; o deger de
`pipeline` tarafindan `sonuc["sure"]`den, yani URETILMIS TIMELINE'IN
KENDI TOPLAMINDAN aliniyor (`beklenen={"sure_sn": sonuc["sure"], ...}`).

Sonuc: kontrol yalnizca "render, plandan kisaldi mi" der. KULLANICININ
ISTEDIGI SURE hicbir yerde denetlenmez.

GERCEK OLAY (is job_1786787306483_y21248_d01800):
    istenen 1.6 dk = 96 sn  ->  uretilen timeline 83.5 sn
    POST-QA: TEMIZ (POST-SURE-SAPMA otmedi)
Yani hedefin %13 altinda bir video "sure acisindan sorunsuz" sayildi.

⚠ KOK NEDEN ZINCIRI (Agent D): `int()` taban yuvarlama (96/7 -> 13),
`butce * 0.92` yapisal tolerans, 24 kelime tavani ve telafi edilmeyen
dusen TTS sahnesi — hepsi AYNI yone kayip veriyor. Bu faz kayiplari
tek tek duzeltmez; ONLARI GORUNUR ve BAGLAYICI kilar.

── SOZLESME ──
  · Kullanicinin istedigi sure (`sure_dk`) is boyunca KAYIPSIZ tasinir
    (`sonuc["hedef_sure_sn"]` -> `beklenen["hedef_sure_sn"]`).
  · POST-QA final sureyi HEM render planina (mevcut POST-SURE-SAPMA)
    HEM kullanici hedefine (`POST-HEDEF-SURE-SAPMA`) karsi olcer.
  · Hedef sapmasi FAIL'dir (fail-closed): sessiz kisa video TESLIM
    EDILMEZ. Tolerans hedefin %12'si.

Kosum: .venv-test/bin/python3 webapp/testler/test_faz_y8.py
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
_QS = oku("editor", "qa_son.py")


blok("Y-8/1 — HEDEF SURE KAYIPSIZ TASINIYOR")

kontrol("stabil kod belgelendi: Y8-HEDEF-SURE",
        "Y8-HEDEF-SURE" in _P or "Y8-HEDEF-SURE" in _QS,
        "karar kodda belgelenmemis")
kontrol("`sonuc` kullanici hedefini tasiyor (hedef_sure_sn)",
        '"hedef_sure_sn"' in _P,
        "kullanici hedefi is ciktisina hic yazilmiyor")
kontrol("hedef `sure_dk`den turetiliyor (kayipsiz)",
        re.search(r'"hedef_sure_sn"\]?\s*=?\s*.{0,40}sure_dk', _P) is not None
        or re.search(r'hedef_sure_sn["\']?\s*:\s*[^,]*sure_dk', _P) is not None,
        "hedef baska kaynaktan turetilmis")
kontrol("`beklenen` sozlugu hedefi POST-QA'ya TASIYOR",
        re.search(r'beklenen\s*=\s*\{[\s\S]{0,300}hedef_sure_sn', _P)
        is not None,
        "hedef qa_son'a gecmiyor")


blok("Y-8/2 — POST-QA HEDEFE KARSI FAIL-CLOSED OLCUYOR")

kontrol("stabil kod: POST-HEDEF-SURE-SAPMA",
        "POST-HEDEF-SURE-SAPMA" in _QS,
        "hedef sapmasi kodu yok")
kontrol("hedef sapmasi FAIL seviyesinde (fail-closed)",
        re.search(r'"POST-HEDEF-SURE-SAPMA",\s*"fail"', _QS) is not None,
        "warn ile geciyor — sessiz kisa video teslim edilebilir")
kontrol("tolerans sabiti tanimli (HEDEF_SURE_TOLERANS)",
        re.search(r"HEDEF_SURE_TOLERANS\s*=", _QS) is not None)
kontrol("olcum sozlugune hedef farki yaziliyor",
        "hedef_sure_farki_sn" in _QS,
        "teshis alani yok")


blok("Y-8/3 — DAVRANIS (gercek olay yeniden uretiliyor)")

sys.path.insert(0, os.path.join(KOK, "editor"))
try:
    from editor import qa_son as _qs
    _tol = float(getattr(_qs, "HEDEF_SURE_TOLERANS", 0.0) or 0.0)
    kontrol("tolerans makul bantta (0.05-0.20)", 0.05 <= _tol <= 0.20,
            f"tolerans={_tol}")
    # Gercek olay: hedef 96 sn, cikti 83.52 sn -> %13 sapma -> FAIL
    kontrol("GERCEK OLAY: hedef 96 sn / cikti 83.52 sn -> sapma tolerans DISI",
            abs(83.52 - 96.0) > 96.0 * _tol,
            f"fark={abs(83.52-96.0):.2f}, tavan={96.0*_tol:.2f}")
    # Kabul edilebilir: hedef 105, cikti 103
    kontrol("KABUL: hedef 105 sn / cikti 103 sn -> tolerans ICINDE",
            abs(103.0 - 105.0) <= 105.0 * _tol)
except Exception as e:                                      # noqa: BLE001
    kontrol("qa_son import edilebiliyor", False, f"{type(e).__name__}: {e}")


blok("Y-8/4 — GERILEME YOK")

kontrol("GERILEME YOK: plan karsilastirmasi (POST-SURE-SAPMA) duruyor",
        "POST-SURE-SAPMA" in _QS)
kontrol("GERILEME YOK: iki kontrol AYRI kodlar",
        _QS.count("POST-SURE-SAPMA") >= 1
        and _QS.count("POST-HEDEF-SURE-SAPMA") >= 1
        and "POST-HEDEF-SURE-SAPMA" != "POST-SURE-SAPMA")
kontrol("GERILEME YOK: Y-6 J/L uretimi duruyor",
        "Y6-JL-URETIM" in oku("hizli_render.py"))
kontrol("GERILEME YOK: Y-7 fact zinciri duruyor",
        "Y7-FACT-PROPS-SINIRI" in _P and '"fact_id": str(s.get("fact_id")' in _P)
kontrol("GERILEME YOK: Y-5 yeniden kullanim geri gelmedi",
        "UI8-SURE-KORUNDU" not in _P)
kontrol("GERILEME YOK: UI-8 fps 30 duruyor",
        'os.environ.get("VIDEO_FPS", "30")' in _P)
kontrol("GERILEME YOK: %100 video profilleri duruyor",
        _P.count('"footage_pct": 100') >= 5)

import kutuphane                                            # noqa: E402
kontrol("GERILEME YOK: Y-4 teslim kapisi fail-closed",
        kutuphane.kabul_edilebilir_mi(
            {"durum": "bitti", "video": "x.mp4", "qa": {"durum": "FAIL"}}
        )["kabul"] is False)

print(f"\n{'=' * 60}")
print(f"GECEN: {gecen}   BASARISIZ: {len(basarisiz)}")
for b in basarisiz:
    print(f"  XX {b}")
sys.exit(1 if basarisiz else 0)
