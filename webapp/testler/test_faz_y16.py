#!/usr/bin/env python3
"""FAZ Y-16 — ORTALAMA PLAN SURESI RENDER EDILEN TIMELINE'DAN OLCULUR.

⚠ OLCULEN KUSUR (`Y16-ORT-PLAN-OLCULMUYOR`) — ajan bulgusu, kodda
dogrulandi: repo genelinde ortalama plan (cekim) suresi HIC olculmuyordu.
  · `editor/kalite_kapisi.ritim_olcusu` YAYILIM olcuyor (`yayilim_sn`,
    `sabit_blok`), ORTALAMA degil.
  · `editor/qa_on.py:242` bir `ortalama_sn` yaziyor ama o, HIC RENDER
    EDILMEYEN EditorV2 planinin beat sureleridir (R-1d-d'de kanitlanan
    "hayalet plan" sinifi).
  · `editor/profil.py` `shot_min_sn`/`shot_maks_sn` TEK CEKIM tavanidir,
    ORTALAMA BANDI degil.
Yani kabul sarti olan "ortalama plan 2.5-4.5 sn" icin hicbir olcum kaynagi
YOKTU.

⚠ IKINCI KUSUR (`Y16-SAHNE-CEKIM-KARISTI`): sahne suresi ile CEKIM suresi
ayni sey degildir. `hizli_render._cekim_planla` bir sahneyi 8 sn tavani ve
%19 secici bolme kuraliyla 1-5 CEKIME boler. Ortalamayi sahne suresinden
hesaplamak GERCEK plan uzunlugunu OLDUGUNDAN UZUN gosterir.

── SOZLESME ──
  · `hizli_render` render SIRASINDA uretilen GERCEK cekim surelerini
    IS ANAHTARLI kaydeder (Y-13b registry'siyle ayni desen).
  · Rapor NIHAI artefakta damgalanir; damgasiz/bayat rapor KANIT DEGIL.
  · `gercek_qa.ritim_olcumu` ortalama + medyan + bant sonucunu doner;
    rapor yoksa `olculdu: False` + `GERCEK-TIMELINE-RITIM-OLCULMEDI`.
    ⚠ Ortalama UYDURULMAZ, sahne suresinden TURETILMEZ.
  · Esik `kabul_105.ORT_PLAN_BANDI_SN` ile AYNI kaynaktan.

Kosum: .venv-test/bin/python3 webapp/testler/test_faz_y16.py
"""
from __future__ import annotations

import ast
import hashlib
import os
import shutil as _sh
import sys
import tempfile as _tf

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


_pkok = _tf.mkdtemp(prefix="y16_kok_")
_uret_kaynak = os.path.join(KOK, "..", "app", "uret.py")
if os.path.exists(_uret_kaynak):
    _sh.copy(_uret_kaynak, os.path.join(_pkok, "uret.py"))
sys.path.insert(0, _pkok)
os.environ["VIDRUSH_KOK"] = os.path.abspath(_pkok)
os.environ.setdefault("CIKTI_DIR", os.path.join(_pkok, "ciktilar"))

import gercek_qa as GQ      # noqa: E402
import hizli_render as HR   # noqa: E402
import kabul_105 as KB      # noqa: E402

_HRK = open(os.path.join(KOK, "hizli_render.py"), encoding="utf-8").read()
_GQK = open(os.path.join(KOK, "gercek_qa.py"), encoding="utf-8").read()


blok("Y-16/1 — SOZLESME VE KARAR KODLARI")

kontrol("karar kodu belgelendi: Y16-ORT-PLAN-OLCULMUYOR",
        "Y16-ORT-PLAN-OLCULMUYOR" in _GQK, "karar kodda belgelenmemis")
kontrol("karar kodu belgelendi: Y16-SAHNE-CEKIM-KARISTI",
        "Y16-SAHNE-CEKIM-KARISTI" in _HRK)
for ad in ("cekim_kaydet", "render_raporu"):
    kontrol(f"hizli_render disa aciyor: {ad}", hasattr(HR, ad), "tanimli degil")
for ad in ("ritim_olcumu", "KOD_RITIM_OLCULMEDI", "ORT_PLAN_BANDI_SN"):
    kontrol(f"gercek_qa disa aciyor: {ad}", hasattr(GQ, ad), "tanimli degil")
kontrol("bant kabul kriteri ile AYNI kaynak",
        tuple(GQ.ORT_PLAN_BANDI_SN) == tuple(KB.ORT_PLAN_BANDI_SN),
        f"olcum={GQ.ORT_PLAN_BANDI_SN} kabul={KB.ORT_PLAN_BANDI_SN}")


blok("Y-16/2 — CEKIM SURELERI IS ANAHTARLI BIRIKIR")

HR.jl_sifirla("j16_A")
HR.cekim_kaydet("j16_A", "seg0", [3.0, 4.0])
HR.cekim_kaydet("j16_A", "seg1", [2.5])
_ra = HR.render_raporu("j16_A")
kontrol("cekim sureleri birikir",
        _ra.get("cekim_sureleri") == [3.0, 4.0, 2.5], f"{_ra}")

HR.jl_sifirla("j16_B")
HR.cekim_kaydet("j16_B", "seg0", [8.0])
kontrol("baska isin cekimleri SIZMAZ",
        HR.render_raporu("j16_B").get("cekim_sureleri") == [8.0]
        and HR.render_raporu("j16_A").get("cekim_sureleri") == [3.0, 4.0, 2.5],
        f"A={HR.render_raporu('j16_A')} B={HR.render_raporu('j16_B')}")
kontrol("bilinmeyen ise kayit YAZILMAZ",
        (HR.cekim_kaydet("j16-yok", "seg0", [5.0]),
         HR.render_raporu("j16-yok").get("cekim_sureleri") == [])[1],
        "sifirlanmamis ise yaziliyor")
kontrol("yeni is cekimleri temizler",
        (HR.jl_sifirla("j16_A"),
         HR.render_raporu("j16_A").get("cekim_sureleri") == [])[1])


blok("Y-16/3 — RAPOR ARTEFAKTA DAMGALANIR")

with _tf.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
    f.write(b"y16-artefakt")
    _yol = f.name
_ozet = hashlib.sha256(b"y16-artefakt").hexdigest()
try:
    HR.jl_sifirla("j16_C")
    HR.cekim_kaydet("j16_C", "seg0", [3.0, 3.5, 4.0])
    kontrol("damgadan once olculdu=False",
            HR.render_raporu("j16_C").get("olculdu") is False)
    HR.jl_damgala("j16_C", _yol)
    _rc = HR.render_raporu("j16_C")
    kontrol("damga cekim raporunu da kapsar",
            _rc.get("olculdu") is True
            and _rc.get("artefakt_sha256") == _ozet, f"{_rc}")

    blok("Y-16/4 — OLCUM: ortalama + medyan + bant")

    _o = GQ.ritim_olcumu(cekim_raporu=_rc, artefakt_sha256=_ozet)
    kontrol("olculdu=True", _o.get("olculdu") is True, f"{_o}")
    kontrol("ortalama dogru", _o.get("ort_plan_sn") == 3.5, f"{_o}")
    kontrol("medyan dogru", _o.get("medyan_sn") == 3.5, f"{_o}")
    kontrol("cekim sayisi", _o.get("cekim") == 3, f"{_o}")
    kontrol("bant ici", _o.get("band_ici") is True and not _o.get("kod"),
            f"{_o}")
    kontrol("en uzun cekim raporlanir", _o.get("en_uzun_sn") == 4.0, f"{_o}")
finally:
    try:
        os.unlink(_yol)
    except OSError:
        pass


blok("Y-16/5 — BANT DISI: STABIL KOD")

def _rap(sureler, ozet="e" * 64):
    return {"cekim_sureleri": list(sureler), "olculdu": True,
            "kaynak": "render-sonrasi", "artefakt_sha256": ozet}


_uzun = GQ.ritim_olcumu(cekim_raporu=_rap([6.0, 6.4, 6.2]),
                        artefakt_sha256="e" * 64)
kontrol("ortalama bant ustunde -> band_ici False",
        _uzun.get("band_ici") is False, f"{_uzun}")
kontrol("bant disinda stabil kod", _uzun.get("kod") == GQ.KOD_RITIM_BANT_DISI,
        f"kod={_uzun.get('kod')!r}")
kontrol("olcum yine de OLCULDU (deger var)",
        _uzun.get("olculdu") is True and _uzun.get("ort_plan_sn") == 6.2,
        f"{_uzun}")

_kisa = GQ.ritim_olcumu(cekim_raporu=_rap([1.8, 2.0, 1.9]),
                        artefakt_sha256="e" * 64)
kontrol("ortalama bant altinda -> band_ici False",
        _kisa.get("band_ici") is False, f"{_kisa}")


blok("Y-16/6 — RAPOR YOKSA / BAYATSA UYDURMA YOK")

_yok = GQ.ritim_olcumu()
kontrol("rapor yoksa olculdu=False", _yok.get("olculdu") is False, f"{_yok}")
kontrol("rapor yoksa stabil kod", _yok.get("kod") == GQ.KOD_RITIM_OLCULMEDI,
        f"kod={_yok.get('kod')!r}")
kontrol("olculmeyende ortalama SAYI olarak sunulmaz",
        _yok.get("ort_plan_sn") is None, f"{_yok}")

_bayat = GQ.ritim_olcumu(cekim_raporu=_rap([3.0, 3.5], ozet="f" * 64),
                         artefakt_sha256="e" * 64)
kontrol("baska artefakta ait rapor REDDEDILIR",
        _bayat.get("olculdu") is False, f"{_bayat}")
kontrol("bayat rapor stabil kod", _bayat.get("kod") == GQ.KOD_RITIM_BAYAT,
        f"kod={_bayat.get('kod')!r}")

_damgasiz = GQ.ritim_olcumu(
    cekim_raporu={"cekim_sureleri": [3.0], "olculdu": False},
    artefakt_sha256="e" * 64)
kontrol("damgasiz rapor REDDEDILIR", _damgasiz.get("olculdu") is False,
        f"{_damgasiz}")

_bos = GQ.ritim_olcumu(cekim_raporu=_rap([]), artefakt_sha256="e" * 64)
kontrol("cekim listesi bossa olculdu=False", _bos.get("olculdu") is False,
        f"{_bos}")


blok("Y-16/7 — SAHNE SURESI ORTALAMA URETMEZ")

# ⚠ Y16-SAHNE-CEKIM-KARISTI: sahne 12 sn olsa da render onu 8 sn tavaniyla
# boler; ortalama SAHNE suresinden hesaplanirsa GERCEGINDEN UZUN cikar.
_cekimler = HR._cekim_planla(12.0, 3)
kontrol("12 sn sahne birden cok cekime bolunur", len(_cekimler) >= 2,
        f"{_cekimler}")
kontrol("hicbir cekim 8 sn'yi asmaz",
        all(d <= 8.0 + 1e-6 for _b, d, _k in _cekimler), f"{_cekimler}")
_ort_cekim = round(sum(d for _b, d, _k in _cekimler) / len(_cekimler), 2)
kontrol("cekim ortalamasi sahne suresinden KUCUK", _ort_cekim < 12.0,
        f"ort={_ort_cekim}")
kontrol("olcum SAHNE listesinden ortalama TURETMIYOR",
        "sure_sn" not in _GQK.split("def ritim_olcumu")[1].split("def ")[0],
        "ritim_olcumu hala sahne suresi okuyor")


blok("Y-16/8 — KABUL KRITERI OLCULEN DEGERI OKUR")

kontrol("bant ici PASS",
        KB._k_ort_plan({"ritim": {"ort_plan_sn": 3.5, "olculdu": True}})[0]
        is True)
kontrol("bant disi FAIL",
        KB._k_ort_plan({"ritim": {"ort_plan_sn": 6.2, "olculdu": True}})[0]
        is False)
kontrol("olculmemis FAIL",
        KB._k_ort_plan({"ritim": {"ort_plan_sn": 3.5, "olculdu": False}})[0]
        is False)


blok("Y-16/9 — HAT: CEKIM KAYDI VE OLCUM BAGLI")

blok("Y-16/9b — KAYIT IDEMPOTENT VE YALNIZ BASARILI SEGMENTTEN")

# ⚠ OLCULEN KUSUR (`Y16-CEKIM-KAYIT-IDEMPOTENT-DEGIL`, denetim): ilk
# yazimda kayit ffmpeg segmenti BASARIYLA olusmadan yapiliyordu; basarisiz
# deneme olcume giriyor, RETRY ayni segmenti IKI KEZ sayiyordu.
HR.jl_sifirla("j16_R")
HR.cekim_kaydet("j16_R", "seg3", [4.0, 4.0])      # 1. deneme (varsayalim fail)
HR.cekim_kaydet("j16_R", "seg3", [4.0, 4.0])      # RETRY basarili
kontrol("ayni segment IKI KEZ sayilmaz",
        HR.render_raporu("j16_R").get("cekim_sureleri") == [4.0, 4.0],
        f"{HR.render_raporu('j16_R').get('cekim_sureleri')}")
HR.cekim_kaydet("j16_R", "seg4", [3.0])
kontrol("farkli segment ayri sayilir",
        len(HR.render_raporu("j16_R").get("cekim_sureleri")) == 3,
        f"{HR.render_raporu('j16_R').get('cekim_sureleri')}")
kontrol("kayitlar segment anahtarli tutulur",
        set(HR.render_raporu("j16_R").get("cekim_kayitlari") or {})
        == {"seg3", "seg4"},
        f"{HR.render_raporu('j16_R').get('cekim_kayitlari')}")
kontrol("baska is kirlenmez",
        HR.render_raporu("j16_B").get("cekim_sureleri") == [8.0],
        f"{HR.render_raporu('j16_B')}")

_HRK2 = open(os.path.join(KOK, "hizli_render.py"), encoding="utf-8").read()
kontrol("karar kodu belgelendi: Y16-CEKIM-KAYIT-IDEMPOTENT-DEGIL",
        "Y16-CEKIM-KAYIT-IDEMPOTENT-DEGIL" in _HRK2)
# ⚠ Kayit cagrilari YALNIZCA basari kontrolunden SONRA olmali.
_basarili_kayit = [
    n for n in ast.walk(ast.parse(_HRK2))
    if isinstance(n, ast.If)
    and any(isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
            and c.func.id == "cekim_kaydet" for c in ast.walk(n))]
kontrol("kayit bir BASARI kosulunun icinde",
        len(_basarili_kayit) >= 2,
        "kayit kosulsuz cagriliyor (basarisiz segment de sayilir)")


blok("Y-16/9c — HAT BAGLANTISI")

kontrol("hizli_render cekim_kaydet'i CAGIRIYOR",
        any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
            and n.func.id == "cekim_kaydet"
            for n in ast.walk(ast.parse(_HRK))),
        "cekim sureleri hicbir yerde kaydedilmiyor")

_PLK = open(os.path.join(KOK, "pipeline.py"), encoding="utf-8").read()
kontrol("pipeline ritim olcumunu kosuyor", "ritim_olcumu(" in _PLK,
        "olcum hatta bagli degil")
kontrol("pipeline olcumu render raporundan besliyor",
        "render_raporu(" in _PLK, "cekim raporu okunmuyor")


print(f"\n{'=' * 62}\nGECEN: {gecen}   BASARISIZ: {len(basarisiz)}")
for b in basarisiz:
    print(f"  XX {b}")
sys.exit(1 if basarisiz else 0)
