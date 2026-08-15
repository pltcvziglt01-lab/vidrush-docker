#!/usr/bin/env python3
"""FAZ Y-13b — GERCEK J/L RAPORU URETILIYOR VE ARTEFAKTA BAGLANIYOR.

Y-13a olcum TARAFINI onardi (`gercek_qa` artik bayat global okumuyor,
rapor enjekte edilmezse "olculmedi" diyor). Bu faz URETIM tarafini onarir:
raporu KIM uretecek ve nasil artefakta baglanacak.

⚠ OLCULEN KUSUR 1 (`Y13B-SAYAC-EZILIYOR`) — `hizli_render.py:1030`
    _JL_SON["sayi"] = jl_sayisi[0]
bir ATAMADIR ve `jl_sayisi` her `_xfade_zincir` CAGRISINDA sifirdan
baslar. 12'den uzun islerde hat obek obek render eder
(`hizli_render.py:1053-1069`) ve SON cagri obek birlestirmesidir:
    ok_birlestir = _xfade_zincir(obekler, birlesik)     # sahne_dilimi=None
`sahne_dilimi` olmadigi icin hicbir J/L secilmez -> `jl_sayisi[0] == 0`
-> sayac 0'a EZILIR. Yani 12'den uzun HER iste uretim gercekten J/L
yapmis olsa bile rapor 0'dir.

⚠ OLCULEN KUSUR 2 (`Y13B-KOTA-OBEK-BASINA`): `JL_MAKS` (3) her cagrida
yeniden uygulaniyordu; 3 obekli bir iste 9 J/L uretilebilirdi. Oysa
kotanin gerekcesi ses kaybi butcesidir (`0.12 x 3 = 0.36 sn <
POST-OLU-FINAL esigi 0.5 sn`) ve o butce IS BASINADIR, obek basina degil.

⚠ OLCULEN KUSUR 3 (`Y13B-ARTEFAKT-BAGI-YOK`): sayac hicbir dosyaya
baglanmiyordu. Hangi MP4'un olcusu oldugu bilinmiyordu; surec omurlu
global oldugu icin baska bir isin degeri kolayca kanit yerine geciyordu.

⚠ OLCULEN KUSUR 4 (`Y13B-TEK-GLOBAL-IZOLASYONSUZ`, denetim): rapor TEK
bir modul sozlugu olarak yazilirsa `Lock` ATOMIKLIK verir ama IZOLASYON
vermez. `server.py` `ISCI_SAYISI` VARSAYILANI 2'dir: A isi kaydederken
B isi `jl_sifirla` yaparsa A'nin sayaci SIFIRLANIR, B damgalarsa A'nin
raporu B'nin MP4'une baglanir.

⚠ OLCULEN KUSUR 5 (`Y13B-DAMGA-SON-ARTEFAKT`, denetim): render bittikten
SONRA `sfx_bindir`, ses normalizasyonu ve `qa_kopru` ses remaster'i MP4'u
YENIDEN YAZAR. Render anindaki damga BAYATLAR ve kabul kriterinin
karsilastirdigi "indirilen dosyanin ozeti" ile TUTMAZ.

── SOZLESME ──
  · Rapor IS ANAHTARLI (job-scoped): her cagri `is_adi` ister.
    ⚠ TEK GLOBAL KABUL DEGIL.
  · `jl_sifirla(is_adi)` — YALNIZCA o isin kaydini temizler.
  · `jl_kaydet(is_adi, n, sinirlar)` — BIRIKTIRIR (`+=`), EZMEZ.
  · `jl_kota_kalan(is_adi)` — kota IS BASINA, obek basina DEGIL.
  · `jl_damgala(is_adi, yol)` — TUM post islemler bittikten sonra,
    GERCEKTEN TESLIM EDILECEK dosya uzerinde cagrilir.
  · `jl_damga_gecerli_mi(is_adi, yol)` — damga hala o dosyaya mi ait?
  · `jl_raporu(is_adi)` — damgalanmadan `olculdu: False`; bilinmeyen is
    icin BOS rapor (baska isin degeri ASLA sizmaz).

Kosum: .venv-test/bin/python3 webapp/testler/test_faz_y13b.py
"""
from __future__ import annotations

import ast
import hashlib
import os
import sys
import tempfile

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


import gercek_qa as GQ      # noqa: E402
import hizli_render as HR   # noqa: E402

_HRK = open(os.path.join(KOK, "hizli_render.py"), encoding="utf-8").read()


blok("Y-13b/1 — URETICI SOZLESMESI VAR")

for ad in ("jl_sifirla", "jl_kaydet", "jl_raporu", "jl_damgala",
           "jl_kota_kalan", "jl_damga_gecerli_mi"):
    kontrol(f"disa acilan ad: {ad}", hasattr(HR, ad), "tanimli degil")

kontrol("karar kodu belgelendi: Y13B-SAYAC-EZILIYOR",
        "Y13B-SAYAC-EZILIYOR" in _HRK, "karar kodda belgelenmemis")
kontrol("kota gerekcesi belgelendi: Y13B-KOTA-OBEK-BASINA",
        "Y13B-KOTA-OBEK-BASINA" in _HRK)
kontrol("artefakt bagi belgelendi: Y13B-ARTEFAKT-BAGI-YOK",
        "Y13B-ARTEFAKT-BAGI-YOK" in _HRK)

# ⚠ Eski bayat global CALISTIRILABILIR kodda kalmamali (yorumda serbest).
_kod_adlari = {n.attr for n in ast.walk(ast.parse(_HRK))
               if isinstance(n, ast.Attribute)} | \
              {n.id for n in ast.walk(ast.parse(_HRK))
               if isinstance(n, ast.Name)}
kontrol("_JL_SON calistirilabilir kodda kalmadi",
        "_JL_SON" not in _kod_adlari,
        "bayat global hala kodda")


blok("Y-13b/2 — IS BASINDA SIFIRLANIR (kontaminasyon yok)")

HR.jl_sifirla("job_A")
HR.jl_kaydet("job_A", 3, [0.12, 0.12, 0.12])
_a = HR.jl_raporu("job_A")
kontrol("A isinde sayac birikti", _a.get("sayi") == 3, f"{_a}")

HR.jl_sifirla("job_B")
_b = HR.jl_raporu("job_B")
kontrol("B isi 0'dan basliyor", _b.get("sayi") == 0,
        f"onceki isin degeri tasindi: {_b}")
kontrol("is adi damgalandi", _b.get("is_adi") == "job_B", f"{_b}")
kontrol("sifirlamadan sonra olculdu=False", _b.get("olculdu") is False,
        "damgasiz rapor olculmus gorunuyor")


blok("Y-13b/2b — ES ZAMANLI IKI IS BIRBIRINI EZEMEZ (izolasyon)")

# ⚠ OLCULEN KUSUR 4 (`Y13B-TEK-GLOBAL-IZOLASYONSUZ`): rapor TEK bir modul
# sozluguyken `Lock` yalnizca ATOMIKLIK veriyordu, IZOLASYON vermiyordu.
# `server.py` `ISCI_SAYISI` VARSAYILANI 2'dir — iki is AYNI ANDA kosar.
# Asagidaki serpistirme (interleaving) tam da o senaryodur.
with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
    f.write(b"B-isinin-artefakti")
    _yol_b = f.name
_ozet_b = hashlib.sha256(b"B-isinin-artefakti").hexdigest()

try:
    HR.jl_sifirla("is_A")                       # A basladi
    HR.jl_kaydet("is_A", 2, [0.12, 0.12])       # A 2 J/L uretti
    HR.jl_sifirla("is_B")                       # B ARAYA GIRDI
    HR.jl_kaydet("is_B", 1, [0.12])             # B 1 J/L uretti
    HR.jl_damgala("is_B", _yol_b)               # B once bitti ve damgalandi

    _ra, _rb = HR.jl_raporu("is_A"), HR.jl_raporu("is_B")
    kontrol("B'nin sifirlamasi A'nin sayacini EZMEDI",
            _ra.get("sayi") == 2, f"A sayi={_ra.get('sayi')} (beklenen 2)")
    kontrol("A'nin sayaci B'ye SIZMADI",
            _rb.get("sayi") == 1, f"B sayi={_rb.get('sayi')} (beklenen 1)")
    kontrol("B'nin damgasi A'ya SIZMADI",
            not _ra.get("artefakt_sha256"),
            f"A artefakt={_ra.get('artefakt_sha256')!r}")
    kontrol("A hala damgasiz -> olculdu=False",
            _ra.get("olculdu") is False, f"{_ra}")
    kontrol("B damgali -> olculdu=True ve kendi artefaktina bagli",
            _rb.get("olculdu") is True
            and _rb.get("artefakt_sha256") == _ozet_b, f"{_rb}")
    kontrol("is_adi alanlari ayri", _ra.get("is_adi") == "is_A"
            and _rb.get("is_adi") == "is_B", f"{_ra.get('is_adi')} / "
            f"{_rb.get('is_adi')}")

    # A simdi KENDI artefaktini damgaliyor — B'nin damgasi bozulmamali.
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        f.write(b"A-isinin-artefakti")
        _yol_a = f.name
    _ozet_a = hashlib.sha256(b"A-isinin-artefakti").hexdigest()
    try:
        HR.jl_damgala("is_A", _yol_a)
        _ra2, _rb2 = HR.jl_raporu("is_A"), HR.jl_raporu("is_B")
        kontrol("A kendi artefaktina baglandi",
                _ra2.get("artefakt_sha256") == _ozet_a, f"{_ra2}")
        kontrol("A'nin damgasi B'yi BOZMADI",
                _rb2.get("artefakt_sha256") == _ozet_b, f"{_rb2}")
        kontrol("iki damga da kendi dosyasinda gecerli",
                HR.jl_damga_gecerli_mi("is_A", _yol_a) is True
                and HR.jl_damga_gecerli_mi("is_B", _yol_b) is True)
        kontrol("capraz dosyada damga GECERSIZ",
                HR.jl_damga_gecerli_mi("is_A", _yol_b) is False
                and HR.jl_damga_gecerli_mi("is_B", _yol_a) is False,
                "bir isin damgasi digerinin dosyasini dogruluyor")
        kontrol("gercek_qa A'nin raporunu B'nin artefaktina karsi REDDEDER",
                GQ.ses_kurgu_olcumu(
                    [{"scene_id": "s1"}, {"scene_id": "s2"}],
                    jl_raporu=_ra2, artefakt_sha256=_ozet_b
                ).get("kod") == GQ.KOD_JL_BAYAT)
    finally:
        try:
            os.unlink(_yol_a)
        except OSError:
            pass
finally:
    try:
        os.unlink(_yol_b)
    except OSError:
        pass

kontrol("bilinmeyen is BOS rapor doner (sizinti yok)",
        HR.jl_raporu("hic-olmayan-is").get("sayi") == 0
        and HR.jl_raporu("hic-olmayan-is").get("olculdu") is False)
kontrol("bilinmeyen ise kayit YAZILMAZ",
        (HR.jl_kaydet("hic-olmayan-is", 5, [0.12] * 5),
         HR.jl_raporu("hic-olmayan-is").get("sayi") == 0)[1],
        "sifirlanmamis ise sessizce yaziliyor")
kontrol("bilinmeyen is damgalanamaz",
        HR.jl_damgala("hic-olmayan-is", _yol_b if False else __file__) is False,
        "sifirlanmamis is damgalandi")


blok("Y-13b/3 — SAYAC BIRIKTIRIR, EZMEZ (obek kusuru)")

HR.jl_sifirla("job_obek")
HR.jl_kaydet("job_obek", 2, [0.12, 0.12])   # obek 1
HR.jl_kaydet("job_obek", 1, [0.12])         # obek 2
HR.jl_kaydet("job_obek", 0, [])             # obek BIRLESTIRMESI
_o = HR.jl_raporu("job_obek")
kontrol("obek birlestirmesi sayaci EZMEZ", _o.get("sayi") == 3,
        f"sayi={_o.get('sayi')} (beklenen 3) — ezilme suruyor")
kontrol("sinir farklari birikir",
        len(_o.get("sinir_farklari_sn") or []) == 3,
        f"sinirlar={_o.get('sinir_farklari_sn')}")


blok("Y-13b/4 — KOTA IS BASINA, OBEK BASINA DEGIL")

HR.jl_sifirla("job_kota")
kontrol("bas kotasi JL_MAKS", HR.jl_kota_kalan("job_kota") == HR.JL_MAKS,
        f"kalan={HR.jl_kota_kalan('job_kota')} maks={HR.JL_MAKS}")
HR.jl_kaydet("job_kota", HR.JL_MAKS, [0.12] * HR.JL_MAKS)
kontrol("kota dolunca kalan 0", HR.jl_kota_kalan("job_kota") == 0,
        f"kalan={HR.jl_kota_kalan('job_kota')}")
HR.jl_kaydet("job_kota", 2, [0.12, 0.12])
kontrol("kota asilirsa sayac kotanin ustune cikmaz",
        HR.jl_raporu("job_kota").get("sayi") == HR.JL_MAKS,
        f"sayi={HR.jl_raporu('job_kota').get('sayi')} > kota {HR.JL_MAKS}")


blok("Y-13b/5 — ARTEFAKT DAMGASI (sha256 + render-sonrasi)")

with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
    f.write(b"sahte-artefakt-icerigi-y13b")
    _yol = f.name
_beklenen = hashlib.sha256(b"sahte-artefakt-icerigi-y13b").hexdigest()

try:
    HR.jl_sifirla("job_damga")
    HR.jl_kaydet("job_damga", 2, [0.12, 0.12])
    _once = HR.jl_raporu("job_damga")
    kontrol("damgadan ONCE olculdu=False", _once.get("olculdu") is False,
            f"{_once}")
    kontrol("damgadan ONCE artefakt bagi yok",
            not _once.get("artefakt_sha256"), f"{_once}")

    _dmg = HR.jl_damgala("job_damga", _yol)
    _son = HR.jl_raporu("job_damga")
    kontrol("damga basarili", _dmg is True, f"jl_damgala={_dmg}")
    kontrol("sha256 dosyanin GERCEK ozeti",
            _son.get("artefakt_sha256") == _beklenen,
            f"{_son.get('artefakt_sha256')} != {_beklenen}")
    kontrol("kaynak render-sonrasi", _son.get("kaynak") == "render-sonrasi",
            f"kaynak={_son.get('kaynak')!r}")
    kontrol("damgadan SONRA olculdu=True", _son.get("olculdu") is True)

    blok("Y-13b/6 — URETICI CIKTISI OLCUM SOZLESMESINDEN GECER")

    _r = GQ.ses_kurgu_olcumu(
        [{"scene_id": "s1"}, {"scene_id": "s2"}, {"scene_id": "s3"}],
        jl_raporu=_son, artefakt_sha256=_beklenen)
    kontrol("gercek_qa uretici raporunu KABUL eder",
            _r.get("olculdu") is True and _r.get("j_l_cut") == 2, f"{_r}")
    kontrol("tam=True (esik karsilandi)", _r.get("tam") is True)

    _r2 = GQ.ses_kurgu_olcumu(
        [{"scene_id": "s1"}, {"scene_id": "s2"}],
        jl_raporu=_son, artefakt_sha256="f" * 64)
    kontrol("baska artefakt ozetiyle REDDEDILIR",
            _r2.get("olculdu") is False and _r2.get("kod") == GQ.KOD_JL_BAYAT,
            f"{_r2}")

    blok("Y-13b/6b — POST ISLEM DOSYAYI DEGISTIRINCE DAMGA BAYATLAR")

    # ⚠ Y13B-DAMGA-SON-ARTEFAKT (denetim bulgusu): render bittikten SONRA
    # `sfx_bindir` + ses normalizasyonu + QA ses remaster'i MP4'u YENIDEN
    # YAZAR. Render anindaki damga o an BAYATLAR ve kabul kriteri
    # "indirilen dosyanin ozeti" ile TUTMAZ.
    kontrol("damga taze dosyada gecerli",
            HR.jl_damga_gecerli_mi("job_damga", _yol) is True, "taze damga gecersiz sayildi")

    with open(_yol, "ab") as f:                 # SFX bindirmesini taklit et
        f.write(b"-sfx-bindirildi")
    _yeni_ozet = hashlib.sha256(
        b"sahte-artefakt-icerigi-y13b-sfx-bindirildi").hexdigest()

    kontrol("dosya degisince damga BAYAT sayilir",
            HR.jl_damga_gecerli_mi("job_damga", _yol) is False,
            "bayat damga hala gecerli gorunuyor")
    _bayat = GQ.ses_kurgu_olcumu(
        [{"scene_id": "s1"}, {"scene_id": "s2"}],
        jl_raporu=HR.jl_raporu("job_damga"), artefakt_sha256=_yeni_ozet)
    kontrol("bayat rapor NIHAI artefakta karsi REDDEDILIR",
            _bayat.get("olculdu") is False
            and _bayat.get("kod") == GQ.KOD_JL_BAYAT, f"{_bayat}")

    kontrol("NIHAI dosyaya yeniden damga sart ve yeterli",
            HR.jl_damgala("job_damga", _yol) is True
            and HR.jl_damga_gecerli_mi("job_damga", _yol) is True
            and HR.jl_raporu("job_damga").get("artefakt_sha256") == _yeni_ozet,
            f"yeniden damga sonrasi: {HR.jl_raporu('job_damga')}")
    _tekrar = GQ.ses_kurgu_olcumu(
        [{"scene_id": "s1"}, {"scene_id": "s2"}],
        jl_raporu=HR.jl_raporu("job_damga"), artefakt_sha256=_yeni_ozet)
    kontrol("yeniden damgadan sonra olcum KABUL edilir",
            _tekrar.get("olculdu") is True and _tekrar.get("j_l_cut") == 2,
            f"{_tekrar}")
    kontrol("yeniden damga J/L SAYISINI degistirmez "
            "(yalniz artefakta yeniden baglar)",
            HR.jl_raporu("job_damga").get("sayi") == 2,
            f"sayi={HR.jl_raporu('job_damga').get('sayi')}")

    blok("Y-13b/7 — YENI IS DAMGAYI TEMIZLER")

    HR.jl_sifirla("job_sonraki")
    _y = HR.jl_raporu("job_sonraki")
    kontrol("yeni iste artefakt bagi temiz", not _y.get("artefakt_sha256"),
            f"onceki artefakt bagi tasindi: {_y}")
    kontrol("yeni iste kaynak damgasi temiz",
            _y.get("kaynak") != "render-sonrasi", f"{_y}")
    kontrol("gercek_qa temiz raporu REDDEDER",
            GQ.ses_kurgu_olcumu([{"scene_id": "s1"}, {"scene_id": "s2"}],
                                jl_raporu=_y).get("olculdu") is False,
            "damgasiz rapor kabul edildi")
finally:
    try:
        os.unlink(_yol)
    except OSError:
        pass


blok("Y-13b/8 — DAMGA OLMAYAN DOSYADA FAIL-CLOSED")

HR.jl_sifirla("job_yok")
HR.jl_kaydet("job_yok", 2, [0.12, 0.12])
kontrol("var olmayan dosya damgalanmaz",
        HR.jl_damgala("job_yok", "/yok/olmayan/dosya.mp4") is False,
        "olmayan dosya damgalandi")
kontrol("basarisiz damgadan sonra olculdu=False",
        HR.jl_raporu("job_yok").get("olculdu") is False,
        "damgasiz rapor olculmus gorunuyor")


blok("Y-13b/9 — PIPELINE OLCUMU RENDER SONRASINA BAGLANDI")

_PL = open(os.path.join(KOK, "pipeline.py"), encoding="utf-8").read()


def _cagri_satirlari(kaynak: str, ad: str) -> list:
    """AST ile `... .ad(...)` cagrilarinin satir numaralari.

    ⚠ Metin araması DEGIL: takma ad (`_hr_son.jl_raporu()`) da yakalanir,
    yorum icindeki ayni metin yakalanMAZ.
    """
    out = []
    for n in ast.walk(ast.parse(kaynak)):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) \
                and n.func.attr == ad:
            out.append(n.lineno)
    return sorted(out)


_s_render = _cagri_satirlari(_PL, "ffmpeg_render")
# ⚠ FAZ Y-16: rapor artik `render_raporu` adiyla da okunuyor
# (AYNI kayit; ad olcumun yalniz J/L olmadigini belirtir).
_s_jl = (_cagri_satirlari(_PL, "jl_raporu")
         + _cagri_satirlari(_PL, "render_raporu"))
kontrol("pipeline uretici raporunu okuyor", bool(_s_jl),
        "jl_raporu() hic cagrilmiyor")
kontrol("J/L olcumu RENDER'DAN SONRA okunuyor",
        bool(_s_jl) and bool(_s_render) and min(_s_jl) > max(_s_render),
        f"jl_raporu@{_s_jl} render@{_s_render} — hala render'dan once")
kontrol("render sonrasi ses olcumu ayri bir cagri",
        any(s > max(_s_render or [0])
            for s in _cagri_satirlari(_PL, "ses_kurgu_olcumu")),
        "render sonrasi ses_kurgu_olcumu cagrisi yok")

# ⚠ Y13B-DAMGA-SON-ARTEFAKT: damga TUM post islemlerden SONRA olmali.
# `ham` dosyasi render'dan sonra sirasiyla `sfx_bindir` (SFX),
# ses normalizasyonu ve `qa_kopru.denetle` (ses remaster'i dosyayi
# YERINDE ezer) tarafindan YENIDEN YAZILIYOR.
_s_sfx = _cagri_satirlari(_PL, "sfx_bindir") + [
    n.lineno for n in ast.walk(ast.parse(_PL))
    if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
    and n.func.id == "sfx_bindir"]
_s_qa = _cagri_satirlari(_PL, "denetle")
_s_damga = _cagri_satirlari(_PL, "jl_damgala")
_son_post = max(_s_sfx + _s_qa + [0])
kontrol("damga SFX bindirmesinden SONRA",
        bool(_s_damga) and min(_s_damga) > max(_s_sfx or [0]),
        f"damga@{_s_damga} sfx@{_s_sfx} — SFX MP4'u sonra eziyor")
kontrol("damga TUM post islemlerden (SFX + ses remaster) SONRA",
        bool(_s_damga) and min(_s_damga) > _son_post,
        f"damga@{_s_damga} son_post@{_son_post}")
kontrol("olcum de tum post islemlerden SONRA",
        min(_cagri_satirlari(_PL, "ses_kurgu_olcumu") or [0]) > _son_post,
        "olcum bayat artefakta bakiyor")
# ⚠ AST ile: damga cagrisinin argumanlari arasinda NIHAI teslim dosyasi
# (`son_video`) olmali; ara dosya (`ham`) SFX/normalizasyon tarafindan
# yeniden yazildigi icin kanit olamaz.
_damga_arg = set()
for _n in ast.walk(ast.parse(_PL)):
    if isinstance(_n, ast.Call) and isinstance(_n.func, ast.Attribute) \
            and _n.func.attr == "jl_damgala":
        _damga_arg |= {a.id for a in _n.args if isinstance(a, ast.Name)}
kontrol("damga NIHAI teslim dosyasina (son_video) yapiliyor",
        "son_video" in _damga_arg,
        f"damga argumanlari={sorted(_damga_arg)} — ara dosyaya yapiliyor")
kontrol("damga ARA dosyaya (ham) yapilmiyor",
        "ham" not in _damga_arg,
        "SFX/normalizasyon sonrasi bayatlayacak dosya damgalaniyor")
kontrol("damga IS ANAHTARLI cagriliyor (is_adi)",
        "is_adi" in _damga_arg,
        "job-scope disi damga — es zamanli isler birbirini ezer")
kontrol("karar kodu belgelendi: Y13B-DAMGA-SON-ARTEFAKT",
        "Y13B-DAMGA-SON-ARTEFAKT" in _PL)
kontrol("is sonucu nihai artefakt ozetini tasir",
        '"artefakt_sha256"' in _PL,
        "kabul degerlendiricisi karsilastiracak ozeti bulamaz")
kontrol("olcum artefakt ozetiyle birlikte gecirilir",
        "artefakt_sha256=" in _PL, "artefakt bagi gecirilmiyor")
kontrol("karar kodu belgelendi: Y13B-OLCUM-RENDER-SONRASI",
        "Y13B-OLCUM-RENDER-SONRASI" in _PL)


print(f"\n{'=' * 62}\nGECEN: {gecen}   BASARISIZ: {len(basarisiz)}")
for b in basarisiz:
    print(f"  XX {b}")
sys.exit(1 if basarisiz else 0)
