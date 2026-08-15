#!/usr/bin/env python3
"""FAZ Y-4 — TESLIM KAPISI TUM NEDENLERLE FAIL-CLOSED (Y-3 GERI ALINDI).

⚠ KULLANICI DUZELTMESI (BAGLAYICI, 15 Agu 2026):
`FACT-BAGLANTI-YOK` teslim engelinden CIKARILAMAZ. "Her bolum aciklaniyor
olmali" talebi gazetecilik izlenebilirligini ZORUNLU kilar: her anlatici
cumlesi / cekim DOGRULANMIS bir `fact_id` ve kaynak/provenance ile bagli
olmalidir.

⚠ Y-3'TE YAPILAN HATA: teslim kapisi `edit_plani.qa.sorunlar` icindeki
FAIL kodlarini `YAYIN_KAPILARI` listesine gore suzuyordu ve liste DISI
FAIL'ler (ozellikle `FACT-BAGLANTI-YOK`) teslimi engellemiyordu. Bu,
izlenebilirlik kapisini fiilen GEVSETIYORDU. GERI ALINDI.

⚠ YENI SOZLESME: `edit_plani` alani VARSA ve `render_edilebilir` False ise
is KABUL EDILMEZ — NEDEN NE OLURSA OLSUN. Kapi kod listesine BAKMAZ.

⚠ GERIYE UYUMLULUK KORUNUR: `edit_plani` alani OLMAYAN eski kayitlarda
kapi uygulanmaz (sessiz sikilastirma yok).

Kosum: .venv-test/bin/python3 webapp/testler/test_faz_y4.py
"""
from __future__ import annotations

import os
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


import kutuphane                                            # noqa: E402
import teslim                                               # noqa: E402

_TEMEL = {"durum": "bitti", "video": "x.mp4", "qa": {"durum": "PASS"}}


def _ep(sorunlar, render_edilebilir=False):
    return dict(_TEMEL, edit_plani={
        "ok": True, "render_edilebilir": render_edilebilir,
        "qa": {"durum": "FAIL", "sorunlar": sorunlar}})


blok("Y-4/1 — Y-3 DARALTMASI GERI ALINDI")

kontrol("YAYIN_KAPILARI suzgeci KALDIRILDI",
        not hasattr(kutuphane, "YAYIN_KAPILARI"),
        "liste hala var — teslim kapisi daraltilmis olabilir")
_K = open(os.path.join(KOK, "kutuphane.py"), encoding="utf-8").read()
kontrol("kabul kapisi FAIL kodlarini SUZMUYOR",
        "YAYIN_KAPILARI" not in _K,
        "kod listesine gore suzme duruyor")
kontrol("stabil kod korundu: Y1-KURGU-QA-FAIL",
        "Y1-KURGU-QA-FAIL" in _K)


blok("Y-4/2 — FACT-BAGLANTI-YOK TESLIMI ENGELLER (izlenebilirlik)")

_fact = [{"kod": "FACT-BAGLANTI-YOK", "seviye": "fail",
          "beat_id": f"b{i:03d}"} for i in range(1, 23)]
_r = kutuphane.kabul_edilebilir_mi(_ep(_fact))
kontrol("yalniz FACT-BAGLANTI-YOK fail -> KABUL EDILMEZ",
        _r["kabul"] is False, str(_r))
kontrol("red nedeni stabil kod tasiyor",
        "Y1-KURGU-QA-FAIL" in str(_r.get("neden")), str(_r.get("neden"))[:90])
kontrol("teslim_et de REDDEDIYOR",
        teslim.teslim_et(is_id="j", tenant_id="T", kayit=_ep(_fact),
                         kutuphane_deposu={}, kabul_zamani=1.0,
                         dosya_var=True)["teslim"] is False)


blok("Y-4/3 — HER NEDEN FAIL-CLOSED")

for _ad, _kayit in (
        ("kurgu QA FAIL (kod listesi bos)",
         dict(_TEMEL, edit_plani={"ok": True, "render_edilebilir": False,
                                  "qa": {"durum": "FAIL", "sorunlar": []}})),
        ("plan kurulamadi (MEDYA-YOK)",
         dict(_TEMEL, edit_plani={"ok": False, "neden": "MEDYA-YOK",
                                  "render_edilebilir": False})),
        ("plan hatasi (HATA)",
         dict(_TEMEL, edit_plani={"ok": False, "neden": "HATA",
                                  "render_edilebilir": False})),
        ("bilinmeyen kod ile FAIL",
         _ep([{"kod": "YEPYENI-KAPI", "seviye": "fail"}])),
        ("yayin kapisi FAIL (HOOK-YOK)",
         _ep([{"kod": "HOOK-YOK", "seviye": "fail"}])),
        ("karisik FAIL",
         _ep([{"kod": "HOOK-YOK", "seviye": "fail"},
              {"kod": "FACT-BAGLANTI-YOK", "seviye": "fail"}])),
):
    kontrol(f"{_ad} -> KABUL EDILMEZ",
            kutuphane.kabul_edilebilir_mi(_kayit)["kabul"] is False,
            str(kutuphane.kabul_edilebilir_mi(_kayit))[:90])


blok("Y-4/4 — GECERLI IS HALA TESLIM EDILEBILIR")

kontrol("render_edilebilir=True -> KABUL",
        kutuphane.kabul_edilebilir_mi(
            dict(_TEMEL, edit_plani={"ok": True, "render_edilebilir": True,
                                     "qa": {"durum": "PASS"}}))["kabul"]
        is True)
kontrol("kurgu QA WARN + render_edilebilir=True -> KABUL",
        kutuphane.kabul_edilebilir_mi(
            dict(_TEMEL, edit_plani={"ok": True, "render_edilebilir": True,
                                     "qa": {"durum": "WARN"}}))["kabul"]
        is True)
kontrol("GERIYE UYUM: edit_plani YOKSA eski kayit KABUL",
        kutuphane.kabul_edilebilir_mi(dict(_TEMEL))["kabul"] is True)


blok("Y-4/5 — GERILEME YOK")

kontrol("GERILEME YOK: POST-QA FAIL hala RED",
        kutuphane.kabul_edilebilir_mi(
            dict(_TEMEL, qa={"durum": "FAIL"}))["kabul"] is False)
kontrol("GERILEME YOK: QA olculmemis RED",
        kutuphane.kabul_edilebilir_mi(
            {"durum": "bitti", "video": "x.mp4"})["kabul"] is False)
kontrol("GERILEME YOK: video yoksa RED",
        kutuphane.kabul_edilebilir_mi(dict(_TEMEL, video=""))["kabul"] is False)
kontrol("GERILEME YOK: KABUL_QA (PASS/WARN) duruyor",
        tuple(kutuphane.KABUL_QA) == ("PASS", "WARN"))
kontrol("GERILEME YOK: tavan 3 duruyor", kutuphane.TAVAN == 3)

_P = open(os.path.join(KOK, "pipeline.py"), encoding="utf-8").read()
kontrol("GERILEME YOK: Y-2 render butcesi duruyor",
        "Y2-RENDER-TIMEOUT" in _P)
kontrol("GERILEME YOK: UI-8 fps 30 duruyor",
        'os.environ.get("VIDEO_FPS", "30")' in _P)
kontrol("GERILEME YOK: UI-8 magnific kapali duruyor",
        "UI8-MAGNIFIC-KAPALI" in _P)
kontrol("GERILEME YOK: UI-7 gorsel yasak kapisi duruyor",
        "UI7-GORSEL-YASAK-KAPISI" in _P)
kontrol("GERILEME YOK: %100 video profilleri duruyor",
        _P.count('"footage_pct": 100') >= 5)

print(f"\n{'=' * 60}")
print(f"GECEN: {gecen}   BASARISIZ: {len(basarisiz)}")
for b in basarisiz:
    print(f"  XX {b}")
sys.exit(1 if basarisiz else 0)
