#!/usr/bin/env python3
"""FAZ Y-12 — TEK FAIL-CLOSED KABUL DEGERLENDIRICISI (105 sn YUKSEK EDIT).

⚠ OLCULEN KUSUR (`Y12-VARLIK-DEGERE-ESIT-SAYILDI`) — bagimsiz denetim,
15 Agu 2026. Sentetik karsi ornek:
    render_qa = WARN
    fact kapsami = 0.25, video kapsami = 0.25
    ayni kaynak en uzun = 99 sn (tavan 8)
    gecis turu = 0, J/L = 0, ducking OLCULMEDI
… iken `teslim.zincir_raporu(...)["tam"]` **True** dondu ve is TESLIM
EDILDI.

⚠ KOK NEDEN (dogrulandi):
  1. `teslim.py:307-312` PRE-QA kanitini DEGERLERE degil dict VARLIGINA
     bakarak olcuyor:
         on_olcumler = [a for a in (...) if isinstance(_pq.get(a), dict)]
     `gercek_qa.olc` bu sozlukleri HER ZAMAN dondurdugu icin koruma
     yapisal olarak hep tatmin oluyor.
  2. `teslim.py:60` `QA_KABUL = kutuphane.KABUL_QA == ("PASS","WARN")`
     -> WARN teslim ediyor.
  3. `teslim.py:351` post_qa halkasi yalnizca durumun KABUL kumesinde
     olmasina bakiyor; olculen tek bir deger okunmuyor.

── SOZLESME (bu preset icin) ──
  · WARN KABUL DEGILDIR. Yalnizca PASS.
  · OLCULMEMIS kriter GECMIS SAYILMAZ (`*-OLCULMEDI` ile duser).
  · Her kriter DEGER uzerinden olculur; sozluk varligi kanit degildir.
  · J/L olcumu ARTEFAKTA BAGLI olmali: `artefakt_sha256` teslim edilen
    MP4'un ozetiyle ayni ve `kaynak == "render-sonrasi"`. Bayat modul
    global'i (`hizli_render._JL_SON`) KANIT SAYILMAZ.
  · Kriterlerden BIRI bile duserse `kabul=False`.

Kosum: .venv-test/bin/python3 webapp/testler/test_faz_y12.py
"""
from __future__ import annotations

import copy
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


# ═════════════ TAM PASS OLCUMU (tek gercek kaynak) ═════════════
# ⚠ Bu sozluk, hattin URETTIGI olcumlerin bicimini taklit eder.
# Her mutasyon TEK bir kriteri bozar; baska hicbir sey degismez.

SHA = "a" * 64

TAM = {
    "is_id": "job_kabul_1",
    "tenant_id": "t-1",
    "artefakt": {"yol": "ciktilar/kabul.mp4", "sha256": SHA, "olculdu": True},
    "video": {"genislik": 1920, "yukseklik": 1080, "fps": 30.0,
              "sure_sn": 105.2, "olculdu": True},
    "hedef_sure_sn": 105.0,
    "kapsam": {"video_orani": 1.0, "cekim": 30, "video_cekim": 30,
               "olculdu": True},
    "provenans": {"tam": True, "eksik": [], "asset_id_eksik": 0,
                  "olculdu": True},
    "kaynak_kullanimi": {"en_uzun_sn": 7.4, "kimlik_eksik": 0,
                         "olculdu": True},
    "kaynak_ses": {"olculdu": True, "sizinti": False, "graf_tam": True,
                   "segment": 30, "artefakt_sha256": SHA,
                   "leakage_db": -91.0, "sample_peak": 0.0},
    "fact": {"kapsam": 1.0, "cekim": 30, "bagli": 30, "allowlist_disi": 0,
             "olculdu": True},
    "anlati": {"bolum": 3, "eksik_halka": [], "kapanis_skoru": 0.81,
               "olculdu": True},
    "gecis": {"tur_sayisi": 3, "olculdu": True},
    "jl": {"sayi": 2, "kaynak": "render-sonrasi", "artefakt_sha256": SHA,
           "olculdu": True},
    "sfx": {"semantik_sayi": 4, "olculdu": True},
    "ducking": {"yapilandirilmis_db": -9.0,
                "olculen_reduction_db": -8.2, "pencere": 2,
                "olculdu": True},
    "ritim": {"ort_plan_sn": 3.5, "olculdu": True},
    "qa": {"on": "PASS", "son": "PASS"},
    "teslim": {"imzali_url": "https://x/ciktilar/kabul.mp4?exp=1&sig=zz",
               "tenant_id": "t-1"},
}


def boz(*yol_ve_deger):
    """TAM'in derin kopyasinda TEK bir alani degistir/sil."""
    d = copy.deepcopy(TAM)
    yol, deger = yol_ve_deger
    parcalar = yol.split(".")
    hedef = d
    for p in parcalar[:-1]:
        hedef = hedef[p]
    if deger is ...:
        hedef.pop(parcalar[-1], None)
    else:
        hedef[parcalar[-1]] = deger
    return d


# ═════════════ MODUL ═════════════

blok("Y-12/1 — DEGERLENDIRICI VAR")

kb = None
try:
    import kabul_105 as kb
    kontrol("modul yuklendi: webapp/kabul_105.py", True)
except Exception as e:
    kontrol("modul yuklendi: webapp/kabul_105.py", False,
            f"{type(e).__name__}: {e}")

if kb is None:
    print(f"\n{'=' * 62}\nGECEN: {gecen}   BASARISIZ: {len(basarisiz)}")
    for b in basarisiz:
        print(f"  XX {b}")
    sys.exit(1)

for ad in ("PRESET", "KRITERLER", "KODLAR", "degerlendir"):
    kontrol(f"disa acilan ad: {ad}", hasattr(kb, ad), "tanimli degil")

kontrol("preset adi sabit",
        getattr(kb, "PRESET", "") == "acceptance_105_high_edit",
        f"preset={getattr(kb, 'PRESET', None)!r}")
kontrol("karar kodu belgelendi: Y12-VARLIK-DEGERE-ESIT-SAYILDI",
        "Y12-VARLIK-DEGERE-ESIT-SAYILDI" in open(
            os.path.join(KOK, "kabul_105.py"), encoding="utf-8").read(),
        "karar kodda belgelenmemis")


blok("Y-12/2 — TAM OLCUM KABUL EDILIR (yanlis-negatif yok)")

_t = kb.degerlendir(TAM)
kontrol("tam olcum kabul edilir", _t.get("kabul") is True,
        f"kabul={_t.get('kabul')} kodlar={_t.get('kodlar')}")
kontrol("kabulde kod listesi bos", not _t.get("kodlar"),
        f"kodlar={_t.get('kodlar')}")
kontrol("her kriter raporlanir",
        len(_t.get("kriterler") or []) == len(kb.KRITERLER),
        f"{len(_t.get('kriterler') or [])} != {len(kb.KRITERLER)}")
kontrol("rapor preset adini tasir", _t.get("preset") == kb.PRESET)
kontrol("rapor artefakt ozetini tasir",
        (_t.get("artefakt_sha256") or "") == SHA, "artefakt bagi yok")


blok("Y-12/3 — HER KRITERI TEK TEK BOZ (red-first, parametrik)")

# (ad, bozulmus olcum, beklenen stabil kod)
VAKALAR = [
    # (a) 1920x1080
    ("cozunurluk dusuk", boz("video.genislik", 1280), "KABUL-COZUNURLUK"),
    ("cozunurluk yuksek", boz("video.yukseklik", 720), "KABUL-COZUNURLUK"),
    ("cozunurluk olculmedi", boz("video.genislik", ...), "KABUL-COZUNURLUK"),
    # (b) 30 fps
    ("fps 25", boz("video.fps", 25.0), "KABUL-FPS"),
    ("fps olculmedi", boz("video.fps", None), "KABUL-FPS"),
    # (c) 90-120 sn bandi
    ("sure bant alti", boz("video.sure_sn", 84.0), "KABUL-SURE-BANT"),
    ("sure bant ustu", boz("video.sure_sn", 131.0), "KABUL-SURE-BANT"),
    # (d) kullanici hedefine tolerans
    ("hedef sapmasi", boz("hedef_sure_sn", 90.0), "KABUL-HEDEF-SURE"),
    ("hedef verilmedi", boz("hedef_sure_sn", None), "KABUL-HEDEF-SURE"),
    # (e) video kapsami = 1.0
    ("video kapsami eksik", boz("kapsam.video_orani", 0.25),
     "KABUL-VIDEO-KAPSAM"),
    ("video kapsami olculmedi", boz("kapsam.olculdu", False),
     "KABUL-VIDEO-KAPSAM"),
    # (f) provenance tam + asset_id
    ("provenans eksik", boz("provenans.tam", False), "KABUL-PROVENANS"),
    ("asset_id eksik", boz("provenans.asset_id_eksik", 3), "KABUL-PROVENANS"),
    ("provenans olculmedi", boz("provenans.olculdu", False),
     "KABUL-PROVENANS"),
    # (g) global ayni kaynak <= 8 sn
    ("kaynak tavani asildi", boz("kaynak_kullanimi.en_uzun_sn", 99.0),
     "KABUL-KAYNAK-TAVAN"),
    ("kaynak kimligi eksik", boz("kaynak_kullanimi.kimlik_eksik", 2),
     "KABUL-KAYNAK-TAVAN"),
    ("kaynak kullanimi olculmedi", boz("kaynak_kullanimi.olculdu", False),
     "KABUL-KAYNAK-TAVAN"),
    # (h) source audio GERCEK olculen = 0
    ("kaynak sesi duyuluyor", boz("kaynak_ses.leakage_db", -12.0),
     "KABUL-KAYNAK-SES"),
    ("kaynak sesi tepe asiyor", boz("kaynak_ses.sample_peak", 0.31),
     "KABUL-KAYNAK-SES"),
    ("kaynak sesi olculmedi", boz("kaynak_ses.olculdu", False),
     "KABUL-KAYNAK-SES"),
    ("kaynak ses grafi eksik", boz("kaynak_ses.graf_tam", False),
     "KABUL-KAYNAK-SES"),
    ("kaynak ses sizintisi", boz("kaynak_ses.sizinti", True),
     "KABUL-KAYNAK-SES"),
    ("sayisal olcum yok (yapisal beyan)", boz("kaynak_ses.leakage_db", ...),
     "KABUL-KAYNAK-SES"),
    ("olcum artefakta bagli degil", boz("kaynak_ses.artefakt_sha256", ""),
     "KABUL-KAYNAK-SES"),
    # (i) fact kapsami = 1.0 + allowlist
    ("fact kapsami eksik", boz("fact.kapsam", 0.25), "KABUL-FACT-KAPSAM"),
    ("allowlist disi fact", boz("fact.allowlist_disi", 1),
     "KABUL-FACT-KAPSAM"),
    ("fact olculmedi", boz("fact.olculdu", False), "KABUL-FACT-KAPSAM"),
    # (j) bolum yayi + kapanis
    ("yay halkasi eksik", boz("anlati.eksik_halka", ["karsitlik"]),
     "KABUL-BOLUM-YAY"),
    ("kapanis zayif", boz("anlati.kapanis_skoru", 0.2), "KABUL-BOLUM-YAY"),
    ("anlati olculmedi", boz("anlati.olculdu", False), "KABUL-BOLUM-YAY"),
    # (k) >=3 gecis turu
    ("gecis turu az", boz("gecis.tur_sayisi", 2), "KABUL-GECIS-TUR"),
    ("gecis olculmedi", boz("gecis.olculdu", False), "KABUL-GECIS-TUR"),
    # (l) render SONRASI olculen J/L >= 2, BAYAT YASAK
    ("J/L az", boz("jl.sayi", 1), "KABUL-JL"),
    ("J/L olculmedi", boz("jl.olculdu", False), "KABUL-JL"),
    ("J/L bayat global", boz("jl.kaynak", "render-oncesi"), "KABUL-JL"),
    ("J/L baska artefakta ait", boz("jl.artefakt_sha256", "b" * 64),
     "KABUL-JL"),
    # (m) semantik SFX + ducking
    ("SFX yok", boz("sfx.semantik_sayi", 0), "KABUL-SFX-DUCKING"),
    ("ducking olculmedi", boz("ducking.olculdu", False),
     "KABUL-SFX-DUCKING"),
    # (n) ortalama plan 2.5-4.5 sn
    ("ort plan uzun", boz("ritim.ort_plan_sn", 6.2), "KABUL-ORT-PLAN"),
    ("ort plan kisa", boz("ritim.ort_plan_sn", 1.9), "KABUL-ORT-PLAN"),
    ("ritim olculmedi", boz("ritim.olculdu", False), "KABUL-ORT-PLAN"),
    # (o) QA — WARN BU PRESET ICIN KABUL DEGIL
    ("PRE-QA WARN", boz("qa.on", "WARN"), "KABUL-QA"),
    ("POST-QA WARN", boz("qa.son", "WARN"), "KABUL-QA"),
    ("QA olculmedi", boz("qa.son", ""), "KABUL-QA"),
    # (p) signed URL gercekten var + tenant dogru
    ("imzali url bos", boz("teslim.imzali_url", ""), "KABUL-IMZALI-URL"),
    ("imzasiz url", boz("teslim.imzali_url", "https://x/ciktilar/kabul.mp4"),
     "KABUL-IMZALI-URL"),
    ("tenant uyusmuyor", boz("teslim.tenant_id", "t-2"), "KABUL-IMZALI-URL"),
    # (q) artefakt kanitli olmali
    ("artefakt olculmedi", boz("artefakt.olculdu", False), "KABUL-ARTEFAKT"),
    ("artefakt ozeti yok", boz("artefakt.sha256", ""), "KABUL-ARTEFAKT"),
]

for ad, olcum, beklenen in VAKALAR:
    r = kb.degerlendir(olcum)
    kodlar = list(r.get("kodlar") or [])
    kontrol(f"{ad} -> teslim=False", r.get("kabul") is False,
            f"kabul={r.get('kabul')}")
    kontrol(f"{ad} -> {beklenen}", beklenen in kodlar,
            f"kodlar={kodlar}")


blok("Y-12/4 — HER KRITER EN AZ BIR VAKAYLA KAPSANDI")

_kapsanan = {k for _, _, k in VAKALAR}
_tanimli = {k["kod"] for k in kb.KRITERLER}
kontrol("kapsanmayan kriter yok", _tanimli <= _kapsanan,
        f"kapsanmayan: {sorted(_tanimli - _kapsanan)}")
kontrol("tanimsiz kod bekleniyor degil", _kapsanan <= _tanimli,
        f"tanimsiz: {sorted(_kapsanan - _tanimli)}")
kontrol("kod listesi benzersiz", len(_tanimli) == len(kb.KRITERLER),
        "kriterlerde kod tekrari var")


blok("Y-12/5 — BOS / BOZUK GIRDI FAIL-CLOSED")

for ad, girdi in (("bos sozluk", {}), ("None", None), ("liste", []),
                  ("metin", "PASS")):
    r = kb.degerlendir(girdi)
    kontrol(f"{ad} -> kabul=False", r.get("kabul") is False,
            f"kabul={r.get('kabul')}")
kontrol("bos girdide TUM kriterler duser",
        len(kb.degerlendir({}).get("kodlar") or []) == len(kb.KRITERLER),
        "bazi kriterler bos girdide gecti")


blok("Y-12/6 — WARN BU PRESET ICIN KABUL DEGIL (acik sozlesme)")

kontrol("kabul edilen QA kumesi yalnizca PASS",
        tuple(getattr(kb, "KABUL_QA", ())) == ("PASS",),
        f"KABUL_QA={getattr(kb, 'KABUL_QA', None)}")


print(f"\n{'=' * 62}\nGECEN: {gecen}   BASARISIZ: {len(basarisiz)}")
for b in basarisiz:
    print(f"  XX {b}")
sys.exit(1 if basarisiz else 0)
