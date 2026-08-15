#!/usr/bin/env python3
"""FAZ Y-1 — YAYIN KAPISI FAIL-CLOSED BAGLANIR.

⚠ TESLIM YOLU DONDURULDU (kullanici karari, 15 Agu 2026): YouTube belgesel /
16:9 / 90-120 sn / 1080p30 / Turkce TTS / yalniz lisansli Pexels-Coverr
gercek video / Magnific KAPALI. Bu faz motoru GENISLETMEZ; yalnizca ZATEN
VAR OLAN kalite kapilarinin KARARINI baglar.

⚠ OLCULEN KUSUR (`Y1-KARAR-UYGULANMIYOR`) — gercek is
job_1786783360170_ui7114_9c21aa:

    EDIT PLANI (EDITOR_V2 ortam degiskeni acik): QA=FAIL
        render_edilebilir=False sahne=20
    ...
    TESLIM job_1786783360170_ui7114_9c21aa: KABUL

`edit_kopru.plan_kur()` dokumantasyonu ACIKCA soyluyor:
    "3. QA-ON FAIL ISE RENDER BASLATILMAZ. `render_edilebilir=False` doner"
Ama `pipeline` bu karari YALNIZCA `sonuc["edit_plani"]` RAPOR ALANINA
yaziyor; `server._teslim_et` -> `teslim.teslim_et` ->
`kutuphane.kabul_edilebilir_mi` zinciri bu alani HIC OKUMUYOR. Sonuc:
kurgu QA'si FAIL veren video "kabul edilmis final" sayilip son-3
kutuphanesine giriyor ve kullaniciya yayina hazir gibi sunuluyor.

⚠ KAPILAR ZATEN VAR (yeniden yazilmiyor):
  qa_on : HOOK-YOK, KALITE-RITIM-SABIT, KALITE-GECIS-TEKDUZE,
          KALITE-BROLL-CESITLILIK, KALITE-GUVENLI-ALAN, KALITE-OLU-FINAL,
          KALITE-KAYNAK-SES-SIZINTI, KALITE-KUNYE-EKSIK, TAVAN, ...
  qa_son: POST-FPS, POST-LUFS, POST-TEPE, POST-SURE-SAPMA, POST-OLU-FINAL,
          POST-SESSIZLIK, ...
Bu faz onlarin HUKMUNU zorunlu kilar.

Kosum: .venv-test/bin/python3 webapp/testler/test_faz_y1.py
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


_TESLIM = oku("teslim.py")
_KUTUP = oku("kutuphane.py")
_SERVER = oku("server.py")

import kutuphane                                            # noqa: E402
import teslim                                               # noqa: E402


blok("Y-1/1 — KURGU QA HUKMU TESLIM KARARINA GIRIYOR")

kontrol("stabil kod tanimli: Y1-KURGU-QA-FAIL",
        "Y1-KURGU-QA-FAIL" in _KUTUP or "Y1-KURGU-QA-FAIL" in _TESLIM,
        "kurgu QA reddi icin stabil kod yok")
kontrol("`kabul_edilebilir_mi` edit_plani/render_edilebilir OKUYOR",
        "render_edilebilir" in _KUTUP,
        "kurgu QA karari kabul kapisina HIC girmiyor")


blok("Y-1/2 — DAVRANIS: render_edilebilir=False KABUL EDILMEZ")

_temel = {"durum": "bitti", "video": "x.mp4",
          "qa": {"durum": "PASS"}}

kontrol("GERILEME YOK: temel kayit (kurgu plani YOK) hala KABUL",
        kutuphane.kabul_edilebilir_mi(dict(_temel))["kabul"] is True,
        str(kutuphane.kabul_edilebilir_mi(dict(_temel))))

_fail = dict(_temel, edit_plani={"ok": True, "render_edilebilir": False,
                                 "qa": {"durum": "FAIL"}})
_r = kutuphane.kabul_edilebilir_mi(_fail)
kontrol("render_edilebilir=False -> KABUL EDILMEZ",
        _r["kabul"] is False, str(_r))
kontrol("red nedeni STABIL kod tasiyor",
        "Y1-KURGU-QA-FAIL" in str(_r.get("neden")), str(_r.get("neden")))

_pass = dict(_temel, edit_plani={"ok": True, "render_edilebilir": True,
                                 "qa": {"durum": "PASS"}})
kontrol("render_edilebilir=True -> KABUL",
        kutuphane.kabul_edilebilir_mi(_pass)["kabul"] is True,
        str(kutuphane.kabul_edilebilir_mi(_pass)))

_warn = dict(_temel, edit_plani={"ok": True, "render_edilebilir": True,
                                 "qa": {"durum": "WARN"}})
kontrol("kurgu QA WARN + render_edilebilir=True -> KABUL (teslim edilebilir)",
        kutuphane.kabul_edilebilir_mi(_warn)["kabul"] is True)

_medyasiz = dict(_temel, edit_plani={"ok": False, "neden": "MEDYA-YOK",
                                     "render_edilebilir": False})
kontrol("MEDYA-YOK (plan denenmedi) -> KABUL EDILMEZ",
        kutuphane.kabul_edilebilir_mi(_medyasiz)["kabul"] is False)


blok("Y-1/3 — POST-QA FAIL HALA REDDEDILIYOR (gerileme yok)")

kontrol("GERILEME YOK: QA FAIL reddediliyor",
        kutuphane.kabul_edilebilir_mi(
            dict(_temel, qa={"durum": "FAIL"}))["kabul"] is False)
kontrol("GERILEME YOK: QA olculmemis reddediliyor",
        kutuphane.kabul_edilebilir_mi(
            {"durum": "bitti", "video": "x.mp4"})["kabul"] is False)
kontrol("GERILEME YOK: video yoksa reddediliyor",
        kutuphane.kabul_edilebilir_mi(
            dict(_temel, video=""))["kabul"] is False)
kontrol("GERILEME YOK: KABUL_QA sozlesmesi (PASS/WARN) duruyor",
        tuple(kutuphane.KABUL_QA) == ("PASS", "WARN"))
kontrol("GERILEME YOK: tavan 3 duruyor", kutuphane.TAVAN == 3)


blok("Y-1/4 — TESLIM ZINCIRI AYNI KARARI VERIYOR")

_zincir_kayit = dict(_temel, edit_plani={"ok": True,
                                         "render_edilebilir": False,
                                         "qa": {"durum": "FAIL"}})
_t = teslim.teslim_et(is_id="j1", tenant_id="T1", kayit=_zincir_kayit,
                      kutuphane_deposu={}, kabul_zamani=1.0, dosya_var=True)
kontrol("teslim_et: kurgu QA FAIL -> TESLIM RED",
        _t["teslim"] is False, str(_t.get("neden"))[:120])
kontrol("teslim_et reddi stabil kod tasiyor",
        "Y1-KURGU-QA-FAIL" in str(_t.get("neden")),
        str(_t.get("neden"))[:160])


blok("Y-1/5 — GERILEME YOK: MEVCUT SOZLESMELER")

_P = oku("pipeline.py")
kontrol("GERILEME YOK: UI-8 fps 30 duruyor",
        'os.environ.get("VIDEO_FPS", "30")' in _P)
kontrol("GERILEME YOK: UI-8 magnific kapali duruyor",
        _P.count("UI8-MAGNIFIC-KAPALI") >= 1)
kontrol("GERILEME YOK: UI-8 sure koruma duruyor",
        "UI8-SURE-KORUNDU" in _P)
kontrol("GERILEME YOK: UI-7 gorsel yasak kapisi duruyor",
        "UI7-GORSEL-YASAK-KAPISI" in _P)
kontrol("GERILEME YOK: %100 video profilleri duruyor",
        _P.count('"footage_pct": 100') >= 5)
kontrol("GERILEME YOK: R-1e kapsam kapisi duruyor",
        "kapsam_kapisi" in _SERVER and "ANON_TENANT" in _SERVER)
kontrol("GERILEME YOK: teslim zincir raporu duruyor",
        "zincir_raporu" in _TESLIM)

print(f"\n{'=' * 60}")
print(f"GECEN: {gecen}   BASARISIZ: {len(basarisiz)}")
for b in basarisiz:
    print(f"  XX {b}")
sys.exit(1 if basarisiz else 0)
