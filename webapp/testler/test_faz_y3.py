#!/usr/bin/env python3
"""FAZ Y-3 — TESLIMI ENGELLEYEN KAPILAR DONDURULMUS KAPSAMA GORE.

⚠ OLCULEN OLAY (gercek is job_1786787306483_y21248_d01800):
    POST-QA WARN · fps 30.0 · 1920x1080 · gercek_video=1.0
    footage 12/12 · MEDYA-VIDEO-YOK 0 · AI gorsel 0 · magnific 0
    EDIT PLANI: QA=FAIL render_edilebilir=False sahne=22
    TESLIM: False | KABUL-YOK:Y1-KURGU-QA-FAIL:QA-FAIL

Y-1 kapisi DOGRU calisti. Ama FAIL'in TEK kaynagi:
    FACT-BAGLANTI-YOK (fail) x22 — "cekim hicbir fact_id'ye bagli degil"
    (yaninda yalnizca WARN'lar: SHOT-COK-KISA x3, PACING-KISA-ORAN)

`FACT-BAGLANTI-YOK` bir GAZETECILIK IZLENEBILIRLIK kapisidir: her cekimin
DOGRULANMIS bir olguya baglanmasini ister. Arastirma motoru bu iste 1/11
olgu dogrulayabildigi icin 22 cekim baglanamadi.

⚠ KULLANICI KAPSAMI (15 Agu 2026) teslim yolunu DONDURDU ve teslimi
engelleyecek kapilari ACIKCA saydi: hook, ortalama plan suresi, semantik
cutaway, gecis cesitliligi, J/L-cut, olculu SFX, altyazi/baslik guvenli
alani, guclu kapanis, kaynak sesi sifir, muzik/TTS temiz, provenance,
ayni kaynak <=8 sn, PRE/POST-QA. `FACT-BAGLANTI-YOK` BU LISTEDE YOK.

⚠ BU FAZ QA'YI GEVSETMEZ: `qa_on`/`qa_son` kapilari, seviyeleri ve
`edit_kopru` karari AYNEN kalir; rapor da AYNEN gorunur. Degisen tek sey,
TESLIM kararinin hangi FAIL kodlarina baktigidir. Liste DISI bir FAIL
teslimi engellemez ama kayitta GORUNUR kalir (sessiz gecis YOK).

Kosum: .venv-test/bin/python3 webapp/testler/test_faz_y3.py
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
        "qa": {"durum": "FAIL" if any(s.get("seviye") == "fail"
                                      for s in sorunlar) else "WARN",
               "sorunlar": sorunlar}})


blok("Y-3/1 — YAYIN KAPILARI LISTESI KODDA TANIMLI")

kontrol("kutuphane.YAYIN_KAPILARI tanimli",
        hasattr(kutuphane, "YAYIN_KAPILARI"),
        "dondurulmus kapsam kodda yok")
_YK = set(getattr(kutuphane, "YAYIN_KAPILARI", ()) or ())
for _k in ("HOOK-YOK", "KALITE-KAYNAK-SES-SIZINTI", "KALITE-GUVENLI-ALAN",
           "KALITE-OLU-FINAL", "KALITE-GECIS-TEKDUZE",
           "KALITE-BROLL-CESITLILIK", "KALITE-KUNYE-EKSIK", "TAVAN"):
    kontrol(f"yayin kapisi listede: {_k}", _k in _YK, str(sorted(_YK))[:120])
kontrol("FACT-BAGLANTI-YOK listede DEGIL (kapsam disi)",
        "FACT-BAGLANTI-YOK" not in _YK)


blok("Y-3/2 — LISTE DISI FAIL TESLIMI ENGELLEMEZ")

_sadece_fact = [{"kod": "FACT-BAGLANTI-YOK", "seviye": "fail",
                 "beat_id": f"b{i:03d}"} for i in range(1, 23)]
_r = kutuphane.kabul_edilebilir_mi(_ep(_sadece_fact))
kontrol("yalniz FACT-BAGLANTI-YOK fail -> KABUL",
        _r["kabul"] is True, str(_r))

_karisik = _sadece_fact + [{"kod": "SHOT-COK-KISA", "seviye": "warn"},
                           {"kod": "PACING-KISA-ORAN", "seviye": "warn"}]
kontrol("liste disi fail + warn'lar -> KABUL",
        kutuphane.kabul_edilebilir_mi(_ep(_karisik))["kabul"] is True)


blok("Y-3/3 — YAYIN KAPISI FAIL'I TESLIMI ENGELLER (fail-closed)")

for _kod in ("HOOK-YOK", "KALITE-KAYNAK-SES-SIZINTI", "KALITE-GUVENLI-ALAN",
             "KALITE-OLU-FINAL", "TAVAN"):
    _r2 = kutuphane.kabul_edilebilir_mi(
        _ep([{"kod": _kod, "seviye": "fail", "beat_id": "b001"}]))
    kontrol(f"{_kod} fail -> KABUL EDILMEZ", _r2["kabul"] is False, str(_r2))
    kontrol(f"{_kod} reddi STABIL kod + kapi adi tasiyor",
            "Y1-KURGU-QA-FAIL" in str(_r2.get("neden"))
            and _kod in str(_r2.get("neden")),
            str(_r2.get("neden"))[:100])

_cok = kutuphane.kabul_edilebilir_mi(
    _ep([{"kod": "HOOK-YOK", "seviye": "fail"},
         {"kod": "FACT-BAGLANTI-YOK", "seviye": "fail"}]))
kontrol("liste ici + liste disi fail karisik -> KABUL EDILMEZ",
        _cok["kabul"] is False, str(_cok))


blok("Y-3/4 — GERILEME YOK")

kontrol("GERILEME YOK: POST-QA FAIL hala RED",
        kutuphane.kabul_edilebilir_mi(
            dict(_TEMEL, qa={"durum": "FAIL"}))["kabul"] is False)
kontrol("GERILEME YOK: QA olculmemis RED",
        kutuphane.kabul_edilebilir_mi(
            {"durum": "bitti", "video": "x.mp4"})["kabul"] is False)
kontrol("GERILEME YOK: video yoksa RED",
        kutuphane.kabul_edilebilir_mi(dict(_TEMEL, video=""))["kabul"] is False)
kontrol("GERILEME YOK: edit_plani YOKSA eski kayit KABUL",
        kutuphane.kabul_edilebilir_mi(dict(_TEMEL))["kabul"] is True)
kontrol("GERILEME YOK: plan kurulamadi (MEDYA-YOK) -> RED",
        kutuphane.kabul_edilebilir_mi(
            dict(_TEMEL, edit_plani={"ok": False, "neden": "MEDYA-YOK",
                                     "render_edilebilir": False}))["kabul"]
        is False)
kontrol("GERILEME YOK: render_edilebilir=True -> KABUL",
        kutuphane.kabul_edilebilir_mi(
            dict(_TEMEL, edit_plani={"ok": True, "render_edilebilir": True,
                                     "qa": {"durum": "PASS"}}))["kabul"]
        is True)
kontrol("GERILEME YOK: KABUL_QA (PASS/WARN) duruyor",
        tuple(kutuphane.KABUL_QA) == ("PASS", "WARN"))
kontrol("GERILEME YOK: teslim_et ayni karari veriyor",
        teslim.teslim_et(is_id="j", tenant_id="T", kayit=_ep(
            [{"kod": "HOOK-YOK", "seviye": "fail"}]),
            kutuphane_deposu={}, kabul_zamani=1.0,
            dosya_var=True)["teslim"] is False)

print(f"\n{'=' * 60}")
print(f"GECEN: {gecen}   BASARISIZ: {len(basarisiz)}")
for b in basarisiz:
    print(f"  XX {b}")
sys.exit(1 if basarisiz else 0)
