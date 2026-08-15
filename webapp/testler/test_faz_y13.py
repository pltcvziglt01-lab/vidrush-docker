#!/usr/bin/env python3
"""FAZ Y-13a — J/L OLCUMU ARTIK BAYAT MODUL GLOBAL'INDEN OKUNMUYOR.

⚠ OLCULEN KUSUR (`Y13-OLCUM-NIYETI-OKUYOR`) — iki bagimsiz ajan ayni
kok nedeni buldu, ben de kodda dogruladim:

  `gercek_qa.py:181-184`
      import hizli_render as _hr
      _jl = int((getattr(_hr, "_JL_SON", None) or {}).get("sayi") or 0)

  yani "olcum" URETILEN ZAMAN CIZGISINE degil, RENDER MODULUNUN
  MODUL-DUZEYI GLOBAL SAYACINA bakiyor. Uc ayri kirilma:

  1. SIRA: `pipeline.py:5071` (`gercek_qa.olc`) render'dan
     (`pipeline.py:5105` `hizli_render.ffmpeg_render`) ONCE kosuyor.
     `_JL_SON` ise `hizli_render.py:1030`'da render SIRASINDA yaziliyor.
     Yani okunan deger o is icin HICBIR ZAMAN taze degildir.
  2. OBEK EZILMESI: `hizli_render.py:1030` `_JL_SON["sayi"] = ...` bir
     ATAMADIR. `hizli_render.py:1069` obek birlestirmesi
     `_xfade_zincir(obekler, birlesik)` -> `sahne_dilimi=None` -> J/L
     secilmez -> sayac 0'a EZILIR. 12'den uzun her iste olcum yapisal
     olarak 0'dir.
  3. KONTAMINASYON: `_JL_SON` surec omurludur ve
     `kaynak.klip_gecmisi_sifirla()` listesinde YOKTUR. Uzun omurlu
     iscide A isinin QA'si B isinin J/L sayisini raporlar.

⚠ Bu, R-1d-e'de bir kez duzeltilen kusurun AYNISIDIR: o zaman
`edit_plani` (hic render edilmeyen plan) kanit sayiliyordu; simdi
render'dan once okunan bir sayac kanit sayiliyor.

── SOZLESME ──
  · `ses_kurgu_olcumu` ARTIK `hizli_render` IMPORT ETMEZ.
  · J/L raporu DISARIDAN enjekte edilir (`jl_raporu=`), tipki
    `kare_okuyucu` / `provenans_okuyucu` gibi.
  · Rapor yoksa -> `olculdu: False` + `GERCEK-TIMELINE-JL-OLCULMEDI`.
    ⚠ 0 UYDURULMAZ, "olculdu" DENMEZ.
  · Rapor render'dan once uretilmisse ya da BASKA bir artefakta aitse
    -> `olculdu: False` + `GERCEK-TIMELINE-JL-BAYAT`.
  · Ducking zarfi verilmezse yine `olculdu: False` (bugunku dogru
    davranis KORUNUR); verilirse GERCEKTEN olculur.

Kosum: .venv-test/bin/python3 webapp/testler/test_faz_y13.py
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


import gercek_qa as GQ  # noqa: E402

SHA = "c" * 64
BASKA = "d" * 64


def sahne(sid):
    return {"scene_id": sid, "kaynak_turu": "medya", "sure_sn": 3.5,
            "medya_turu": "video", "saglayici": "pexels",
            "lisans": "pexels-license", "asset_id": f"a-{sid}",
            "fact_id": "f0123456789abcde0", "ses_kanali": "sifir"}


UC = [sahne("s1"), sahne("s2"), sahne("s3")]


def rapor(**ek):
    d = {"sayi": 2, "offset_sn": 0.12, "kaynak": "render-sonrasi",
         "artefakt_sha256": SHA, "is_adi": "job_1",
         "sinir_farklari_sn": [0.12, 0.12]}
    d.update(ek)
    return d


blok("Y-13a/1 — SOZLESME: hizli_render GLOBAL'I ARTIK OKUNMUYOR")

_kaynak = open(os.path.join(KOK, "gercek_qa.py"), encoding="utf-8").read()
kontrol("gercek_qa artik hizli_render import etmiyor",
        "import hizli_render" not in _kaynak,
        "modul global'i hala okunuyor")
# ⚠ `_JL_SON` adi KUSURU BELGELEYEN yorumda gecebilir; yasak olan
# CALISTIRILABILIR koddan okunmasidir. AST ile ayirt ediyoruz: modulun
# derlenmis kodunda o ad bir sabit/isim olarak GECMEMELI.
import ast  # noqa: E402

_agac = ast.parse(_kaynak)
_kod_adlari = {
    n.attr for n in ast.walk(_agac) if isinstance(n, ast.Attribute)
} | {
    n.id for n in ast.walk(_agac) if isinstance(n, ast.Name)
} | {
    n.value for n in ast.walk(_agac)
    if isinstance(n, ast.Constant) and isinstance(n.value, str)
}
kontrol("_JL_SON calistirilabilir kodda okunmuyor (yalniz yorumda)",
        "_JL_SON" not in _kod_adlari, "bayat global hala kodda referansli")
kontrol("karar kodu belgelendi: Y13-OLCUM-NIYETI-OKUYOR",
        "Y13-OLCUM-NIYETI-OKUYOR" in _kaynak, "karar kodda belgelenmemis")
for ad in ("KOD_JL_OLCULMEDI", "KOD_JL_BAYAT"):
    kontrol(f"stabil kod tanimli: {ad}", hasattr(GQ, ad), "tanimli degil")


blok("Y-13a/2 — RAPOR YOKSA 0 UYDURULMAZ")

_r = GQ.ses_kurgu_olcumu(UC)
kontrol("rapor yokken olculdu=False", _r.get("olculdu") is False,
        f"olculdu={_r.get('olculdu')}")
kontrol("rapor yokken stabil kod yazilir",
        _r.get("kod") == GQ.KOD_JL_OLCULMEDI, f"kod={_r.get('kod')!r}")
kontrol("rapor yokken tam=False", _r.get("tam") is False)
kontrol("rapor yokken j_l_cut sayi olarak SUNULMAZ",
        _r.get("j_l_cut") is None,
        f"j_l_cut={_r.get('j_l_cut')!r} — olculmemis deger sayi gibi sunuluyor")


blok("Y-13a/3 — BAYAT MODUL GLOBAL'I ARTIK KANIT DEGIL")

# Kusurun ta kendisi: modulde eski isin sayaci duruyor.
try:
    import hizli_render as _hr
    _hr._JL_SON["sayi"] = 7
except Exception:
    pass
_r2 = GQ.ses_kurgu_olcumu(UC)
kontrol("onceki isin sayaci raporlanmaz", _r2.get("j_l_cut") != 7,
        f"j_l_cut={_r2.get('j_l_cut')} — kontaminasyon suruyor")
kontrol("global varken bile olculdu=False", _r2.get("olculdu") is False,
        f"olculdu={_r2.get('olculdu')}")


blok("Y-13a/4 — ENJEKTE EDILEN RAPOR OLCULUR")

_r3 = GQ.ses_kurgu_olcumu(UC, jl_raporu=rapor(), artefakt_sha256=SHA)
kontrol("rapor verilince olculdu=True", _r3.get("olculdu") is True,
        f"{_r3}")
kontrol("j_l_cut rapordan gelir", _r3.get("j_l_cut") == 2,
        f"j_l_cut={_r3.get('j_l_cut')}")
kontrol("tam=True (esik karsilandi)", _r3.get("tam") is True)
kontrol("kod bos", not _r3.get("kod"), f"kod={_r3.get('kod')!r}")


blok("Y-13a/5 — RENDER ONCESI OLCUM BAYAT SAYILIR")

_r4 = GQ.ses_kurgu_olcumu(UC, jl_raporu=rapor(kaynak="render-oncesi"),
                          artefakt_sha256=SHA)
kontrol("render-oncesi kaynak reddedilir", _r4.get("olculdu") is False,
        f"{_r4}")
kontrol("bayat kodu yazilir", _r4.get("kod") == GQ.KOD_JL_BAYAT,
        f"kod={_r4.get('kod')!r}")


blok("Y-13a/6 — BASKA ARTEFAKTA AIT OLCUM REDDEDILIR")

_r5 = GQ.ses_kurgu_olcumu(UC, jl_raporu=rapor(artefakt_sha256=BASKA),
                          artefakt_sha256=SHA)
kontrol("artefakt ozeti uyusmazsa reddedilir", _r5.get("olculdu") is False,
        f"{_r5}")
kontrol("bayat kodu yazilir (artefakt)", _r5.get("kod") == GQ.KOD_JL_BAYAT,
        f"kod={_r5.get('kod')!r}")

_r6 = GQ.ses_kurgu_olcumu(UC, jl_raporu=rapor(artefakt_sha256=""),
                          artefakt_sha256=SHA)
kontrol("artefakt bagi olmayan rapor reddedilir",
        _r6.get("olculdu") is False, f"{_r6}")


blok("Y-13a/7 — ESIK: J/L < 2 OLCULUR AMA TAM DEGIL")

_r7 = GQ.ses_kurgu_olcumu(UC, jl_raporu=rapor(sayi=1), artefakt_sha256=SHA)
kontrol("1 J/L olculur", _r7.get("olculdu") is True and _r7.get("j_l_cut") == 1,
        f"{_r7}")
kontrol("1 J/L tam DEGIL", _r7.get("tam") is False,
        "esik altinda tam=True donuyor")
kontrol("0 J/L olculur ama tam degil",
        (lambda r: r.get("olculdu") is True and r.get("tam") is False)(
            GQ.ses_kurgu_olcumu(UC, jl_raporu=rapor(sayi=0),
                                artefakt_sha256=SHA)),
        "olculen 0 ile olculmemis 0 ayirt edilmiyor")


blok("Y-13a/8 — DUCKING: ZARF VERILIRSE OLCULUR")

# ⚠ FAZ Y-14b — SOZLESME BILINCLI DEGISTI.
# ESKI IDDIA (buradaydi): "zarf verilince ducking OLCULUR" ve
# "derinlik_db == -9.0". O deger zarfin ucuncu alanindaki YAPILANDIRMA
# degeriydi (`SFX_DUCKING_DB`), akustik olcum DEGIL: `threshold`/`ratio`
# secimi gercek gain reduction'in -9 dB olmasini GARANTI ETMEZ. Filtre hic
# etki etmese bile bu iddia PASS uretirdi — SAHTE PASS.
# ⚠ YENI SOZLESME: zarf yalnizca PENCERELERI verir; gercek azalma
# `ducking_olcum` ile DISARIDAN gelir (stem'in sidechain oncesi/sonrasi
# RMS farki). Tam sozlesme: webapp/testler/test_faz_y14b.py
_ZARF8 = [(0.0, 3.2, -9.0), (5.0, 8.0, -9.0)]
_r8 = GQ.ses_kurgu_olcumu(UC, jl_raporu=rapor(), artefakt_sha256=SHA,
                          ducking_zarfi=_ZARF8)
_d8 = _r8.get("ducking") or {}
kontrol("zarf TEK BASINA olcum sayilmaz", _d8.get("olculdu") is False,
        f"ducking={_d8}")
kontrol("zarf tek basinayken stabil kod yazilir",
        _d8.get("kod") == GQ.KOD_DUCKING_GAIN_OLCULMEDI,
        f"kod={_d8.get('kod')!r}")
kontrol("olculmemis azalma SAYI olarak sunulmaz",
        _d8.get("olculen_reduction_db") is None, f"{_d8}")
kontrol("pencereler yine de raporlanir", _d8.get("aralik") == 2, f"{_d8}")

_r8b = GQ.ses_kurgu_olcumu(
    UC, jl_raporu=rapor(), artefakt_sha256=SHA, ducking_zarfi=_ZARF8,
    ducking_olcum={"olculdu": True, "olculen_reduction_db": -8.4,
                   "p50_db": -8.4, "p95_db": -9.1, "pencere": 2,
                   "yapilandirilmis_db": -9.0})
_d8b = _r8b.get("ducking") or {}
kontrol("GERCEK olcum verilince ducking olculur",
        _d8b.get("olculdu") is True, f"{_d8b}")
kontrol("olculen azalma tasinir",
        _d8b.get("olculen_reduction_db") == -8.4, f"{_d8b}")
kontrol("yapilandirma AYRI alanda kalir",
        _d8b.get("yapilandirilmis_db") == -9.0, f"{_d8b}")
kontrol("zarf yokken ducking olculmedi KALIR",
        (GQ.ses_kurgu_olcumu(UC, jl_raporu=rapor(), artefakt_sha256=SHA)
         .get("ducking") or {}).get("olculdu") is False,
        "zarf yokken ducking gecmis sayiliyor")


blok("Y-13a/9 — olc() PARAMETRELERI GECIRIR")

_o = GQ.olc([sahne("s1"), sahne("s2"), sahne("s3")],
            jl_raporu=rapor(), artefakt_sha256=SHA,
            ducking_zarfi=[(0.0, 3.0, -9.0)])
_ses = (_o.get("ses") or {})
kontrol("olc jl_raporu'nu ses olcumune gecirir",
        _ses.get("olculdu") is True and _ses.get("j_l_cut") == 2,
        f"ses={_ses}")
kontrol("olc ducking_zarfi'ni gecirir (pencere gorunur)",
        (_ses.get("ducking") or {}).get("aralik") == 1,
        f"ducking={_ses.get('ducking')}")
kontrol("olc ducking_olcum'u gecirir",
        (GQ.olc([sahne("s1"), sahne("s2"), sahne("s3")],
                jl_raporu=rapor(), artefakt_sha256=SHA,
                ducking_zarfi=[(0.0, 3.0, -9.0)],
                ducking_olcum={"olculdu": True,
                               "olculen_reduction_db": -7.7,
                               "yapilandirilmis_db": -9.0})
         .get("ses") or {}).get("ducking", {}).get("olculdu") is True,
        "gercek olcum olc() uzerinden gecmiyor")
kontrol("olc parametresiz cagrilinca da patlamaz (geriye uyum)",
        isinstance(GQ.olc([sahne("s1"), sahne("s2")]), dict))


blok("Y-13a/10 — IKI SAHNEDEN AZ: ESKI DAVRANIS KORUNUR")

_r10 = GQ.ses_kurgu_olcumu([sahne("s1")], jl_raporu=rapor(),
                           artefakt_sha256=SHA)
kontrol("tek sahnede olculdu=False", _r10.get("olculdu") is False)
kontrol("tek sahnede gecis-yok kodu", _r10.get("kod") == GQ.KOD_GECIS_YOK,
        f"kod={_r10.get('kod')!r}")


print(f"\n{'=' * 62}\nGECEN: {gecen}   BASARISIZ: {len(basarisiz)}")
for b in basarisiz:
    print(f"  XX {b}")
sys.exit(1 if basarisiz else 0)
