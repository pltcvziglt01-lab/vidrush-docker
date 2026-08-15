#!/usr/bin/env python3
"""FAZ Y-15 — >=3 DETERMINISTIK GECIS TURU (yapisal imkansizlik kaldirildi).

⚠ OLCULEN KUSUR (`Y15-GECIS-IMZA-TEKIL`) — ajan bulgusu, kodda dogrulandi:
`pipeline.GECIS_IMZASI` her `edit_id` icin TEK bir `(imza, oran)` demeti
veriyordu:
    "sinematik-belgesel": ("karartma", 0.20)
`gecis_imza_sec` ya o TEK imzayi ya da bos string donebiliyordu. Bos imza
`hizli_render` tarafinda 2 karelik fade (= gozle SERT KESME) oluyor.
Yani bir iste uretilebilecek EN FAZLA gecis turu sayisi 2'ydi
(hard-cut + tek imza) — kabul sarti olan ">=3 gecis turu" YAPISAL OLARAK
IMKANSIZDI. Ustelik `hizli_render.GECIS_IMZA_FFMPEG` uc tur tanimliyordu
(`karartma`->fade, `flash`->fadewhite, `whip`->slideleft) ama `whip`
hicbir `edit_id`'de gecmedigi icin ERISILEMEZ olu koddu.

⚠ IKINCI KUSUR (`Y15-GECIS-TUR-OLCUMU-YOK`): `gercek_qa.gecis_olcumu`
`imza_dagilimi` uretiyordu ama TUR SAYISI ve ESIK yoktu; hicbir kapi
">=3 tur" sartini denetlemiyordu.

── SOZLESME ──
  · Her `edit_id` icin bir imza LISTESI tanimlidir (en az 2 imza).
  · `gecis_imza_sec` deterministiktir: ayni (edit_id, indeks) her
    uretimde AYNI imzayi verir — rastgelelik YOK.
  · Yeterli sahne varsa uretilen tur sayisi >= 3 olur (hard-cut dahil).
  · `gecis_olcumu` `tur_sayisi` ve `esik_karsilandi` raporlar; esik
    altinda STABIL KOD doner.
  · ⚠ Olcum GERCEK zaman cizgisinden (`gecis_imza` alani) turer.

Kosum: .venv-test/bin/python3 webapp/testler/test_faz_y15.py
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


_pkok = _tf.mkdtemp(prefix="y15_kok_")
_uret_kaynak = os.path.join(KOK, "..", "app", "uret.py")
if os.path.exists(_uret_kaynak):
    _sh.copy(_uret_kaynak, os.path.join(_pkok, "uret.py"))
sys.path.insert(0, _pkok)
os.environ["VIDRUSH_KOK"] = os.path.abspath(_pkok)
os.environ.setdefault("CIKTI_DIR", os.path.join(_pkok, "ciktilar"))

import gercek_qa as GQ      # noqa: E402
import hizli_render as HR   # noqa: E402
import kabul_105 as KB      # noqa: E402
import pipeline as PL       # noqa: E402

_PLK = open(os.path.join(KOK, "pipeline.py"), encoding="utf-8").read()


blok("Y-15/1 — SOZLESME VE KARAR KODLARI")

kontrol("karar kodu belgelendi: Y15-GECIS-IMZA-TEKIL",
        "Y15-GECIS-IMZA-TEKIL" in _PLK, "karar kodda belgelenmemis")
kontrol("karar kodu belgelendi: Y15-GECIS-TUR-OLCUMU-YOK",
        "Y15-GECIS-TUR-OLCUMU-YOK" in open(
            os.path.join(KOK, "gercek_qa.py"), encoding="utf-8").read())
for ad in ("GECIS_IMZALARI", "gecis_imza_sec", "GECIS_TURU_ASGARI"):
    kontrol(f"disa acilan ad: {ad}", hasattr(PL, ad), "tanimli degil")
kontrol("stabil kod tanimli: KOD_GECIS_TUR_AZ",
        hasattr(GQ, "KOD_GECIS_TUR_AZ"), "tanimli degil")


blok("Y-15/2 — HER edit_id ICIN EN AZ IKI IMZA")

_tablo = getattr(PL, "GECIS_IMZALARI", {})
kontrol("tablo bos degil", bool(_tablo), f"{_tablo}")
for _eid, _kayit in _tablo.items():
    _imzalar = _kayit.get("imzalar") if isinstance(_kayit, dict) else _kayit
    kontrol(f"{_eid}: en az 2 imza", len(_imzalar or []) >= 2,
            f"imzalar={_imzalar}")
    kontrol(f"{_eid}: imzalar renderer'da TANIMLI",
            all(i in HR.GECIS_IMZA_FFMPEG for i in (_imzalar or [])),
            f"taninmayan imza: "
            f"{[i for i in (_imzalar or []) if i not in HR.GECIS_IMZA_FFMPEG]}")

kontrol("renderer'in TUM turleri erisilebilir (olu tur yok)",
        set(HR.GECIS_IMZA_FFMPEG) <= {
            i for k in _tablo.values()
            for i in (k.get("imzalar") if isinstance(k, dict) else k)},
        f"erisilemeyen: {set(HR.GECIS_IMZA_FFMPEG) - {i for k in _tablo.values() for i in (k.get('imzalar') if isinstance(k, dict) else k)}}")


blok("Y-15/3 — DETERMINIZM: ayni girdi ayni imza")

_eid = "sinematik-belgesel"
_bir = [PL.gecis_imza_sec(_eid, i) for i in range(60)]
_iki = [PL.gecis_imza_sec(_eid, i) for i in range(60)]
kontrol("iki kosum BIREBIR ayni", _bir == _iki, "rastgelelik var")


blok("Y-15/4 — >=3 TUR YAPISAL OLARAK MUMKUN")

for _eid2 in _tablo:
    _uretilen = {PL.gecis_imza_sec(_eid2, i) for i in range(60)}
    _tur = len(_uretilen)          # bos string = hard-cut, o da bir turdur
    kontrol(f"{_eid2}: >=3 gecis turu uretilebiliyor",
            _tur >= PL.GECIS_TURU_ASGARI,
            f"uretilen={sorted(_uretilen)} tur={_tur}")

kontrol("hard-cut hala uretiliyor (her gecis efektli degil)",
        "" in {PL.gecis_imza_sec(_eid, i) for i in range(60)},
        "tum gecisler efektli — ritim bozulur")


blok("Y-15/5 — OLCUM: tur_sayisi ve esik")


def _sahneler(imzalar):
    return [{"scene_id": f"s{i}", "gecis_imza": im}
            for i, im in enumerate([""] + list(imzalar))]


_o3 = GQ.gecis_olcumu(_sahneler(["karartma", "flash", ""]))
kontrol("tur_sayisi olculuyor", _o3.get("tur_sayisi") == 3,
        f"{_o3}")
kontrol("esik karsilaninca kod bos", _o3.get("esik_karsilandi") is True
        and not _o3.get("kod"), f"{_o3}")

_o2 = GQ.gecis_olcumu(_sahneler(["karartma", "karartma", ""]))
kontrol("tek imza + hard-cut = 2 tur", _o2.get("tur_sayisi") == 2, f"{_o2}")
kontrol("esik altinda esik_karsilandi False",
        _o2.get("esik_karsilandi") is False, f"{_o2}")
kontrol("esik altinda STABIL KOD", _o2.get("kod") == GQ.KOD_GECIS_TUR_AZ,
        f"kod={_o2.get('kod')!r}")

_o1 = GQ.gecis_olcumu([{"scene_id": "s1"}])
kontrol("tek sahnede olculdu=False", _o1.get("olculdu") is False, f"{_o1}")
kontrol("olculmeyende tur_sayisi SAYI olarak sunulmaz",
        _o1.get("tur_sayisi") is None, f"{_o1}")


blok("Y-15/6 — KABUL KRITERI OLCULEN TUR SAYISINI OKUR")

kontrol("3 tur PASS",
        KB._k_gecis_tur({"gecis": {"tur_sayisi": 3, "olculdu": True}})[0]
        is True)
kontrol("2 tur FAIL",
        KB._k_gecis_tur({"gecis": {"tur_sayisi": 2, "olculdu": True}})[0]
        is False)
kontrol("olculmemis FAIL",
        KB._k_gecis_tur({"gecis": {"tur_sayisi": 3, "olculdu": False}})[0]
        is False)
kontrol("kabul esigi ile hat esigi AYNI",
        KB.GECIS_TURU_ASGARI == PL.GECIS_TURU_ASGARI == GQ.GECIS_TURU_ASGARI,
        f"kabul={KB.GECIS_TURU_ASGARI} hat={PL.GECIS_TURU_ASGARI} "
        f"olcum={GQ.GECIS_TURU_ASGARI}")


blok("Y-15/7 — GERILEME: eski tek-imza tablosu KALDIRILDI")

kontrol("GECIS_IMZASI artik tek demet dondurmuyor",
        not isinstance(getattr(PL, "GECIS_IMZASI", {}).get(_eid), tuple)
        or hasattr(PL, "GECIS_IMZALARI"),
        "eski tekil tablo hala tek kaynak")
kontrol("bilinmeyen edit_id'de imza URETILMEZ (uydurma yok)",
        PL.gecis_imza_sec("hic-olmayan-stil", 3) == "",
        "bilinmeyen stil icin imza uyduruluyor")


print(f"\n{'=' * 62}\nGECEN: {gecen}   BASARISIZ: {len(basarisiz)}")
for b in basarisiz:
    print(f"  XX {b}")
sys.exit(1 if basarisiz else 0)
