#!/usr/bin/env python3
"""FAZ Y-14b — DUCKING DERINLIGI BEYAN DEGIL, OLCULEN GAIN REDUCTION.

⚠ OLCULEN KUSUR (`Y14B-DUCKING-BEYAN-OLCUM-SANILDI`) — bagimsiz denetim:
Y-14 gercek `sidechaincompress` filtresini kurdu (yon dogru), ama zarfin
ucuncu alanina DOGRUDAN `SFX_DUCKING_DB = -9.0` yaziliyordu. Bu bir
YAPILANDIRMA degeridir, akustik olcum DEGIL:
  · `threshold`/`ratio` secimi gercek gain reduction'in -9 dB olmasini
    GARANTI ETMEZ (giris seviyesi, tepe/ortalama farki, makeup hepsi
    sonucu degistirir).
  · `gercek_qa` bunu `derinlik_db` diye rapor ediyordu ve
    `kabul_105._k_sfx_ducking` "olculdu" sayip GECIRIYORDU.
  · Yani filtre hic etki etmese bile (ornegin esik hic asilmasa) kriter
    PASS verirdi — SAHTE PASS.

── SOZLESME ──
  · `yapilandirilmis_db` ile `olculen_reduction_db` AYRI ALANLARDIR.
  · Olcum yontemi: AYNI SFX stem'inin sidechain ONCESI ve SONRASI hali,
    GERCEK SFX zaman pencerelerinde ffmpeg `astats`/`volumedetect` ile
    karsilastirilir; pencere basina `rms_son - rms_on` hesaplanir.
  · Raporlanan: `p50_db`, `p95_db`, `pencere` sayisi.
  · ⚠ Analiz kosturulamazsa `olculdu: False` + `DUCKING-GAIN-OLCULMEDI`.
    0 dB UYDURULMAZ.
  · ⚠ `kabul_105` YALNIZCA `olculen_reduction_db` + `olculdu is True`
    okur; `yapilandirilmis_db` TEK BASINA KABUL URETEMEZ.

Kosum: .venv-test/bin/python3 webapp/testler/test_faz_y14b.py
"""
from __future__ import annotations

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


_pkok = _tf.mkdtemp(prefix="y14b_kok_")
_uret_kaynak = os.path.join(KOK, "..", "app", "uret.py")
if os.path.exists(_uret_kaynak):
    _sh.copy(_uret_kaynak, os.path.join(_pkok, "uret.py"))
sys.path.insert(0, _pkok)
os.environ["VIDRUSH_KOK"] = os.path.abspath(_pkok)
os.environ.setdefault("CIKTI_DIR", os.path.join(_pkok, "ciktilar"))

import gercek_qa as GQ   # noqa: E402
import kabul_105 as KB   # noqa: E402
import pipeline as PL    # noqa: E402

_PLK = open(os.path.join(KOK, "pipeline.py"), encoding="utf-8").read()


# ───────────── SAHTE ffmpeg KOSUCUSU (ag/medya/render YOK) ─────────────
# `astats`/`volumedetect` ciktisini taklit eder. `rms` sozlugu
# (stem, pencere_indeksi) -> dB.

def kosucu_kur(rms: dict, patlat: bool = False):
    cagrilar = []

    def _kos(komut):
        cagrilar.append(list(komut))
        if patlat:
            return {"rc": 1, "stdout": "", "stderr": "sahte hata"}
        # `-i <stem>` ve `atrim=start=<b>:end=<s>` ayikla
        stem, bas = "", 0.0
        for i, a in enumerate(komut):
            if a == "-i" and i + 1 < len(komut):
                stem = os.path.basename(str(komut[i + 1]))
            if "atrim=start=" in str(a):
                try:
                    bas = float(str(a).split("atrim=start=")[1].split(":")[0])
                except (IndexError, ValueError):
                    bas = 0.0
        d = rms.get((stem, round(bas, 3)))
        if d is None:
            return {"rc": 0, "stdout": "", "stderr": "[Parsed_astats] baska satir"}
        return {"rc": 0, "stdout": "",
                "stderr": f"[Parsed_astats_0 @ 0x1] RMS level dB: {d}\n"}

    _kos.cagrilar = cagrilar
    return _kos


ZARF = [(2.0, 3.5, -9.0), (9.5, 11.0, -9.0)]


blok("Y-14b/1 — SOZLESME: ALANLAR AYRISTI")

kontrol("karar kodu belgelendi: Y14B-DUCKING-BEYAN-OLCUM-SANILDI",
        "Y14B-DUCKING-BEYAN-OLCUM-SANILDI" in _PLK,
        "karar kodda belgelenmemis")
for ad in ("ducking_stem_komutu", "rms_olc", "ducking_gain_olcumu",
           "KOD_DUCKING_GAIN_OLCULMEDI"):
    kontrol(f"disa acilan ad: {ad}", hasattr(PL, ad), "tanimli degil")


blok("Y-14b/2 — STEM KOMUTU: ONCE ve SONRA AYNI KOSUDA")

_k = PL.ducking_stem_komutu(
    "/yok/video.mp4", [(2.0, "/sfx/a.wav"), (9.5, "/sfx/b.wav")],
    ducking_db=-9.0, stem_on="/tmp/on.wav", stem_son="/tmp/son.wav")
_kmetin = " ".join(_k)
kontrol("sidechain ONCESI stem map'lenir", "[sfx]" in _kmetin, _kmetin[:200])
kontrol("sidechain SONRASI stem map'lenir", "[sfxduck]" in _kmetin,
        _kmetin[:200])
kontrol("iki stem de ciktiya yazilir",
        "/tmp/on.wav" in _k and "/tmp/son.wav" in _k, f"{_k}")
kontrol("video akisi yazilmaz (yalniz ses stem'i)", "-vn" in _k, f"{_k}")


blok("Y-14b/3 — GERCEK AZALMA OLCULUR (PASS yolu)")

_kos = kosucu_kur({
    ("on.wav", 2.0): -18.0, ("son.wav", 2.0): -27.5,    # -9.5 dB azalma
    ("on.wav", 9.5): -20.0, ("son.wav", 9.5): -28.2,    # -8.2 dB azalma
})
_o = PL.ducking_gain_olcumu("/tmp/on.wav", "/tmp/son.wav", ZARF,
                            yapilandirilmis_db=-9.0, kosucu=_kos)
kontrol("olculdu=True", _o.get("olculdu") is True, f"{_o}")
kontrol("pencere sayisi 2", _o.get("pencere") == 2, f"{_o}")
# ⚠ Iki olcumun medyani ortalamadir: (-9.5 + -8.2) / 2 = -8.85
kontrol("p50 azalma iki pencerenin medyani", _o.get("p50_db") == -8.85,
        f"p50={_o.get('p50_db')}")
kontrol("olculen_reduction_db p50'dir",
        _o.get("olculen_reduction_db") == _o.get("p50_db"), f"{_o}")
kontrol("p95 en agir azalmayi tasir", _o.get("p95_db") == -9.5,
        f"p95={_o.get('p95_db')}")
kontrol("yapilandirilmis_db AYRI alanda", _o.get("yapilandirilmis_db") == -9.0,
        f"{_o}")
kontrol("olcum stem basina pencere basina kosuldu",
        len(_kos.cagrilar) == 4, f"cagri={len(_kos.cagrilar)}")


blok("Y-14b/4 — CIKTI DEGISMIYORSA FAIL (denetim vakasi)")

# ⚠ Denetimin istedigi red-first vaka: yapilandirma -9 dB diyor ama
# sidechain oncesi/sonrasi RMS AYNI -> gercek azalma YOK.
_kos2 = kosucu_kur({
    ("on.wav", 2.0): -18.0, ("son.wav", 2.0): -18.0,
    ("on.wav", 9.5): -20.0, ("son.wav", 9.5): -20.0,
})
_o2 = PL.ducking_gain_olcumu("/tmp/on.wav", "/tmp/son.wav", ZARF,
                             yapilandirilmis_db=-9.0, kosucu=_kos2)
kontrol("olculdu=True (olcum kosuldu)", _o2.get("olculdu") is True, f"{_o2}")
kontrol("olculen azalma ~0", _o2.get("olculen_reduction_db") == 0.0, f"{_o2}")
kontrol("yapilandirma -9 olsa da olculen 0",
        _o2.get("yapilandirilmis_db") == -9.0
        and _o2.get("olculen_reduction_db") == 0.0, f"{_o2}")

_kr2 = KB._k_sfx_ducking({
    "sfx": {"semantik_sayi": 2, "olculdu": True},
    "ducking": {"yapilandirilmis_db": -9.0, "olculen_reduction_db": 0.0,
                "olculdu": True}})
kontrol("kabul kriteri FAIL verir", _kr2[0] is False, f"{_kr2}")
kontrol("FAIL gerekcesi olculen degeri soyler",
        "0.0" in str(_kr2[1]) or "olculen" in str(_kr2[1]).lower(), f"{_kr2}")


blok("Y-14b/5 — ANALIZ YOKSA UYDURMA YOK")

_o3 = PL.ducking_gain_olcumu("/tmp/on.wav", "/tmp/son.wav", ZARF,
                             yapilandirilmis_db=-9.0,
                             kosucu=kosucu_kur({}, patlat=True))
kontrol("analiz patlarsa olculdu=False", _o3.get("olculdu") is False, f"{_o3}")
kontrol("stabil kod DUCKING-GAIN-OLCULMEDI",
        _o3.get("kod") == PL.KOD_DUCKING_GAIN_OLCULMEDI,
        f"kod={_o3.get('kod')!r}")
kontrol("olculemeyende reduction alani SAYI olarak sunulmaz",
        _o3.get("olculen_reduction_db") is None, f"{_o3}")

_o4 = PL.ducking_gain_olcumu("/tmp/on.wav", "/tmp/son.wav", [],
                             yapilandirilmis_db=-9.0, kosucu=_kos)
kontrol("pencere yoksa olculdu=False", _o4.get("olculdu") is False, f"{_o4}")


blok("Y-14b/6 — gercek_qa OLCUMU TASIR, BEYANI TASIMAZ")

_r = GQ.ses_kurgu_olcumu(
    [{"scene_id": "s1"}, {"scene_id": "s2"}],
    jl_raporu={"sayi": 2, "offset_sn": 0.12, "kaynak": "render-sonrasi",
               "artefakt_sha256": "a" * 64},
    artefakt_sha256="a" * 64,
    ducking_zarfi=ZARF, ducking_olcum=_o)
_d = _r.get("ducking") or {}
kontrol("olculen_reduction_db tasinir",
        _d.get("olculen_reduction_db") == _o.get("olculen_reduction_db"),
        f"{_d}")
kontrol("yapilandirilmis_db AYRI tasinir",
        _d.get("yapilandirilmis_db") == -9.0, f"{_d}")
# ⚠ AST: `derinlik_db` adi YORUMDA gecebilir (kusuru belgeler); yasak olan
# CALISTIRILABILIR kodda ALAN ADI olarak OKUNMASIDIR.
import ast as _ast  # noqa: E402
_kb_agac = _ast.parse(open(os.path.join(KOK, "kabul_105.py"),
                           encoding="utf-8").read())
_kb_sabit = {n.value for n in _ast.walk(_kb_agac)
             if isinstance(n, _ast.Constant) and isinstance(n.value, str)}
kontrol("eski `derinlik_db` alani KABUL kriterinde OKUNMUYOR",
        "derinlik_db" not in _kb_sabit,
        "kabul hala beyan alanini okuyor")
kontrol("kabul `olculen_reduction_db` alanini okuyor",
        "olculen_reduction_db" in _kb_sabit,
        "kabul olculen degeri hic okumuyor")

_r2 = GQ.ses_kurgu_olcumu(
    [{"scene_id": "s1"}, {"scene_id": "s2"}],
    jl_raporu={"sayi": 2, "offset_sn": 0.12, "kaynak": "render-sonrasi",
               "artefakt_sha256": "a" * 64},
    artefakt_sha256="a" * 64,
    ducking_zarfi=ZARF)          # ⚠ olcum YOK, yalniz zarf
_d2 = _r2.get("ducking") or {}
kontrol("olcum verilmezse olculdu=False", _d2.get("olculdu") is False, f"{_d2}")
kontrol("zarf TEK BASINA kabul uretmez",
        KB._k_sfx_ducking({"sfx": {"semantik_sayi": 2, "olculdu": True},
                           "ducking": _d2})[0] is False, f"{_d2}")


blok("Y-14b/7 — KABUL KRITERI: YALNIZ OLCULEN DEGER")

_pass = KB._k_sfx_ducking({
    "sfx": {"semantik_sayi": 2, "olculdu": True},
    "ducking": {"yapilandirilmis_db": -9.0, "olculen_reduction_db": -8.2,
                "p95_db": -9.5, "pencere": 2, "olculdu": True}})
kontrol("gercek azalma >= 3 dB ise PASS", _pass[0] is True, f"{_pass}")

_zayif = KB._k_sfx_ducking({
    "sfx": {"semantik_sayi": 2, "olculdu": True},
    "ducking": {"yapilandirilmis_db": -9.0, "olculen_reduction_db": -1.4,
                "olculdu": True}})
kontrol("azalma esigin altindaysa FAIL", _zayif[0] is False, f"{_zayif}")

_beyan = KB._k_sfx_ducking({
    "sfx": {"semantik_sayi": 2, "olculdu": True},
    "ducking": {"yapilandirilmis_db": -9.0, "olculdu": True}})
kontrol("YALNIZ yapilandirma varsa FAIL (sahte PASS yok)",
        _beyan[0] is False, f"{_beyan}")

_olculmedi = KB._k_sfx_ducking({
    "sfx": {"semantik_sayi": 2, "olculdu": True},
    "ducking": {"yapilandirilmis_db": -9.0, "olculen_reduction_db": -8.2,
                "olculdu": False}})
kontrol("olculdu=False ise FAIL", _olculmedi[0] is False, f"{_olculmedi}")


blok("Y-14b/8 — HAT: OLCUM SFX BINDIRMEDEN SONRA KOSAR")

kontrol("sfx_bindir gain olcumunu cagirir",
        "ducking_gain_olcumu(" in _PLK, "olcum hatta bagli degil")
kontrol("stem'ler uretilir", "ducking_stem_komutu(" in _PLK)
kontrol("olcum is sonucuna tasinir", "ducking_olcum=" in _PLK,
        "olcum gercek_qa'ya gecirilmiyor")


print(f"\n{'=' * 62}\nGECEN: {gecen}   BASARISIZ: {len(basarisiz)}")
for b in basarisiz:
    print(f"  XX {b}")
sys.exit(1 if basarisiz else 0)
