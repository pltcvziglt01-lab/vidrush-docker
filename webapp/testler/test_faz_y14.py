#!/usr/bin/env python3
"""FAZ Y-14 — GERCEK SIDECHAIN DUCKING + OLCULEN ZARF.

⚠ OLCULEN KUSUR (`Y14-DUCKING-FILTRE-YOK`) — iki bagimsiz ajan buldu,
kodda dogrulandim: `grep -rn sidechaincompress webapp/` **SIFIR** eslesme.
Yani "ducking" hicbir ffmpeg filtre zincirinde YOKTU.
  · `pipeline.sfx_bindir` SFX'i anlatinin uzerine duz `amix=normalize=0`
    ile bindiriyordu — anlati bastirilmiyor, efekt anlatinin UZERINE
    biniyordu.
  · `editor/ses.py:119` `ducking_zarfi` yalnizca bir PLAN nesnesiydi;
    hicbir ffmpeg komutuna donusmuyordu.
  · `stil_profili` her profil icin `ducking_db` beyan ediyordu (-4…-12);
    bu deger HICBIR filtreye ulasmiyordu (sessiz kalite kaybi).
  · `gercek_qa` bu yuzden durustce `{"olculdu": False}` donuyordu — ama
    hukumsuz: hicbir kapi bunu FAIL'e cevirmiyordu.

⚠ IKINCI KUSUR (`Y14-SFX-OLCUM-KAYIP`): `sfx_bindir` kac SFX bindirdigini
YALNIZCA `stderr`'e basiyordu; hicbir olcum sozlugune yazmiyordu. `qa_on`
ise BASKA bir islev sozlugu (`editor/ses.ISLEV_SFX`) uzerinden sayiyordu
ve o sozluk `pipeline.ISLEV_TIPLERI` ile ORTUSMUYORDU — sayac hep 0.

── SOZLESME ──
  · SFX katmani anlatiya karsi GERCEK `sidechaincompress` ile bastirilir.
  · `sfx_bindir` artik `(video, olcum)` doner; `olcum` bindirilen SFX
    sayisini, islev dagilimini ve UYGULANAN ducking zarfini tasir.
  · Zarf UYDURULMAZ: her aralik gercekten bindirilen bir SFX'in
    baslangici + ffprobe ile OLCULEN suresidir.
  · SFX dizini yoksa / bindirme basarisizsa `olculdu: False` + stabil kod;
    sessiz atlama YOK.
  · ⚠ Zarf, UYGULANAN filtre parametrelerini raporlar (komut gercekten
    kosmustur); akustik bir "olculen bastirma" iddiasi DEGILDIR ve oyle
    adlandirilmaz.

Kosum: .venv-test/bin/python3 webapp/testler/test_faz_y14.py
"""
from __future__ import annotations

import ast
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


_PLK = open(os.path.join(KOK, "pipeline.py"), encoding="utf-8").read()

blok("Y-14/1 — GERCEK SIDECHAIN FILTRESI KODDA")

kontrol("sidechaincompress filtre zincirinde",
        "sidechaincompress" in _PLK,
        "ducking hala gercek bir filtre degil")
kontrol("karar kodu belgelendi: Y14-DUCKING-FILTRE-YOK",
        "Y14-DUCKING-FILTRE-YOK" in _PLK)
kontrol("karar kodu belgelendi: Y14-SFX-OLCUM-KAYIP",
        "Y14-SFX-OLCUM-KAYIP" in _PLK)

# `pipeline` `app/uret.py`'i `uret` adiyla arar ve `VIDRUSH_KOK` altina dizin
# acar. Testte ag/medya/render YOK; yalnizca import edilebilmesi icin gecici
# bir kok kurulur (test_faz_i.py ile AYNI yol).
import shutil as _sh          # noqa: E402
import tempfile as _tf        # noqa: E402

_pkok = _tf.mkdtemp(prefix="y14_kok_")
os.makedirs(_pkok, exist_ok=True)
_uret_kaynak = os.path.join(KOK, "..", "app", "uret.py")
if os.path.exists(_uret_kaynak):
    _sh.copy(_uret_kaynak, os.path.join(_pkok, "uret.py"))
sys.path.insert(0, _pkok)
os.environ["VIDRUSH_KOK"] = os.path.abspath(_pkok)
os.environ.setdefault("CIKTI_DIR", os.path.join(_pkok, "ciktilar"))

import pipeline as PL  # noqa: E402

for ad in ("sfx_bindir", "sfx_filtre_kur", "SFX_DUCKING_DB",
           "KOD_SFX_DIZIN_YOK", "KOD_SFX_BINDIRME_BASARISIZ"):
    kontrol(f"disa acilan ad: {ad}", hasattr(PL, ad), "tanimli degil")

kontrol("ducking derinligi anlamli (<= -3 dB)",
        float(getattr(PL, "SFX_DUCKING_DB", 0)) <= -3.0,
        f"SFX_DUCKING_DB={getattr(PL, 'SFX_DUCKING_DB', None)}")


blok("Y-14/2 — FILTRE ZINCIRI: ANLATI SIDECHAIN ANAHTARI")

# ⚠ Saf fonksiyon: ffmpeg CALISTIRMAZ, yalnizca zinciri kurar.
_parcalar = [(2.0, "/sfx/impact.wav"), (9.5, "/sfx/riser.wav")]
_z = PL.sfx_filtre_kur(_parcalar, ducking_db=-9.0)
_zincir = ";".join(_z["filtre"])

kontrol("anlati asplit ile ikiye ayrilir (biri sidechain anahtari)",
        "asplit" in _zincir, f"zincir={_zincir[:200]}")
kontrol("SFX katmani ONCE kendi arasinda mikslenir",
        "amix" in _zincir and _zincir.index("amix") < _zincir.rindex("amix")
        or _zincir.count("amix") >= 2,
        "tek amix var — SFX katmani ayri degil")
kontrol("sidechaincompress SFX katmanina uygulanir",
        "sidechaincompress" in _zincir, f"zincir={_zincir[:300]}")
kontrol("her SFX kendi baslangicina gecikmeli",
        _zincir.count("adelay") == len(_parcalar),
        f"adelay={_zincir.count('adelay')} != {len(_parcalar)}")
kontrol("cikis etiketi [mix]", any("[mix]" in f for f in _z["filtre"]))
kontrol("normalize=0 korunur (seviye dusmez)", "normalize=0" in _zincir)
kontrol("uygulanan derinlik raporlanir", _z.get("ducking_db") == -9.0,
        f"{_z.get('ducking_db')}")
kontrol("sidechain parametreleri raporlanir",
        bool(_z.get("parametreler")), f"{_z.get('parametreler')}")

_z0 = PL.sfx_filtre_kur([], ducking_db=-9.0)
kontrol("SFX yoksa zincir BOS (fail-closed)", not _z0["filtre"],
        f"{_z0}")


blok("Y-14/3 — OLCUM SOZLESMESI: (video, olcum) IKILISI")

_v, _o = PL.sfx_bindir("/yok/video.mp4", [], "/tmp")
kontrol("sfx_bindir ikili doner", isinstance(_o, dict), f"{type(_o)}")
kontrol("sahne yoksa video AYNEN doner", _v == "/yok/video.mp4")
kontrol("sahne yoksa bindirilen 0", _o.get("bindirilen") == 0, f"{_o}")
kontrol("sahne yoksa olculdu=False", _o.get("olculdu") is False, f"{_o}")
kontrol("sahne yoksa ducking zarfi BOS",
        not _o.get("ducking_zarfi"), f"{_o}")

_sahne = [{"islev": "acilis", "sure": 4.0},
          {"islev": "vurgu", "sure": 4.0},
          {"islev": "aciklama", "sure": 4.0},
          {"islev": "sonuc", "sure": 4.0}]
_v2, _o2 = PL.sfx_bindir("/yok/video.mp4", _sahne, "/tmp/yok-dizin")
kontrol("SFX dizini yoksa STABIL KOD yazilir",
        _o2.get("kod") in (PL.KOD_SFX_DIZIN_YOK,
                           PL.KOD_SFX_BINDIRME_BASARISIZ),
        f"kod={_o2.get('kod')!r}")
kontrol("basarisiz bindirmede olculdu=False",
        _o2.get("olculdu") is False, f"{_o2}")
kontrol("basarisiz bindirmede video KAYBOLMAZ",
        _v2 == "/yok/video.mp4", f"{_v2}")


blok("Y-14/4 — ZARF UYDURULMAZ: sure OLCULUR")

# `sure_okuyucu` enjekte edilir -> ffprobe/medya gerekmez.
_cagrilan = []


def _sahte_sure(yol):
    _cagrilan.append(yol)
    return 1.5


_zarf = PL.sfx_zarfi_kur([(2.0, "/sfx/impact.wav"), (9.5, "/sfx/riser.wav")],
                         ducking_db=-9.0, sure_okuyucu=_sahte_sure)
kontrol("zarf her SFX icin bir aralik uretir", len(_zarf) == 2, f"{_zarf}")
kontrol("aralik (bas, bit, db) uclusudur",
        all(isinstance(z, tuple) and len(z) == 3 for z in _zarf), f"{_zarf}")
kontrol("bitis OLCULEN sureden turer",
        _zarf[0][1] == 3.5 and _zarf[1][1] == 11.0, f"{_zarf}")
kontrol("derinlik uygulanan degerdir",
        all(z[2] == -9.0 for z in _zarf), f"{_zarf}")
kontrol("sure okuyucu GERCEKTEN cagrilir", len(_cagrilan) == 2, f"{_cagrilan}")

_zarf_olcusuz = PL.sfx_zarfi_kur([(2.0, "/sfx/impact.wav")], ducking_db=-9.0,
                                 sure_okuyucu=lambda y: 0.0)
kontrol("sure olculemezse aralik UYDURULMAZ", not _zarf_olcusuz,
        f"{_zarf_olcusuz}")


blok("Y-14/5 — ZARF gercek_qa SOZLESMESINDEN GECER")

import gercek_qa as GQ  # noqa: E402

_r = GQ.ses_kurgu_olcumu(
    [{"scene_id": "s1"}, {"scene_id": "s2"}],
    jl_raporu={"sayi": 2, "offset_sn": 0.12, "kaynak": "render-sonrasi",
               "artefakt_sha256": "a" * 64},
    artefakt_sha256="a" * 64,
    ducking_zarfi=_zarf)
_d = _r.get("ducking") or {}
# ⚠ FAZ Y-14b: zarf TEK BASINA olcum degildir. Zarf pencereleri verir;
# gercek gain reduction ayri olculur (bkz. test_faz_y14b.py).
kontrol("zarf pencereleri raporlanir", _d.get("aralik") == 2, f"{_d}")
kontrol("zarf tek basina olcum SAYILMAZ", _d.get("olculdu") is False, f"{_d}")

import kabul_105 as KB  # noqa: E402

_kr = KB._k_sfx_ducking({
    "sfx": {"semantik_sayi": 2, "olculdu": True},
    "ducking": {"yapilandirilmis_db": -9.0,
                "olculen_reduction_db": -8.4, "pencere": 2,
                "olculdu": True}})
kontrol("GERCEK olcumle KABUL-SFX-DUCKING gecer", _kr[0] is True, f"{_kr}")
kontrol("YALNIZ zarfla kriter GECMEZ",
        KB._k_sfx_ducking({"sfx": {"semantik_sayi": 2, "olculdu": True},
                           "ducking": _d})[0] is False, f"{_d}")


blok("Y-14/6 — PIPELINE ZARFI OLCUME GECIRIR")

_agac = ast.parse(_PLK)
_sfx_atama = [n for n in ast.walk(_agac)
              if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
              and n.func.id == "sfx_bindir"]
kontrol("pipeline sfx_bindir'i cagiriyor", bool(_sfx_atama))
kontrol("pipeline ducking_zarfi'ni olcume gecirir",
        "ducking_zarfi=" in _PLK,
        "zarf uretiliyor ama olcume gitmiyor")
kontrol("SFX olcumu is sonucuna yazilir",
        '"sfx"' in _PLK, "sfx olcumu hicbir yere yazilmiyor")


print(f"\n{'=' * 62}\nGECEN: {gecen}   BASARISIZ: {len(basarisiz)}")
for b in basarisiz:
    print(f"  XX {b}")
sys.exit(1 if basarisiz else 0)
