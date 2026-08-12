#!/usr/bin/env python3
"""MEDYA AVCISI KOPRUSU — Faz B `medya/avci` motorunu gercek uretim hattina
GUVENLI ve OPT-IN olarak baglar (Faz I-6).

⚠ NEDEN VAR (§1 ve §10 madde 1, 12 Agu): `webapp/medya/` paketi (6 saglayici,
lisans duvari, provenance, alaka kapisi, konsept farkindalikli siralama)
yazildi ve testlendi ama `/api/generate` hatti onu HIC CAGIRMIYORDU. Canli
uretim yalnizca `kaynak.py` uzerinden calisiyordu.

⚠ VARSAYILAN KAPALI. Bu kopru YALNIZCA acikca acildiginda devreye girer:
    · `MEDYA_AVCISI=1` ortam degiskeni, ya da
    · is ayarinda `{"medya_avcisi": True}` (DAHILI alan — 22 alanlik generate
      sozlesmesine DOKUNULMADI, arayuz bu alani gondermez).
Kapaliyken bu modulun hicbir satiri uretim kararina karisMAZ.

⚠ UC KAPI DA ZORUNLU — BYPASS YOK:
  1. LISANS + PROVENANCE : yalnizca `render_kullanilabilir` adaylar gecer.
     Aday listesi degil, avcinin SECTIKLERI kullanilir.
  2. SSRF / INDIRME      : indirme `medya.indirme.guvenli_indir` ile yapilir;
     bu modul ASLA dogrudan `requests` cagirmaz.
  3. KARE KAPISI         : indirilen her klip `kare_dogrula` ile sinanir.
     Dogrulayici VERILMEZSE aday KABUL EDILMEZ (fail-closed).

⚠ UYDURMA/RASTGELE STOK YOK. Uygun aday cikmazsa `ok=False` doner ve cagiran
taraf MEVCUT guvenli yolunu surdurur. Sessiz gecis yok: her red `dususler`e
gerekcesiyle yazilir.

⚠ HATTI COKERTMEZ. Import hatasi, istisna, zaman asimi ya da butce bitisi
uretim yolunu bozmaz; `ok=False` + gorunur neden doner.
"""
from __future__ import annotations

import os
import sys
import threading
import time

# ── OPT-IN BAYRAGI — VARSAYILAN KAPALI ──
ACIK = os.environ.get("MEDYA_AVCISI", "0").lower() in ("1", "true", "evet", "on")

# Tek sahne icin duvar saati tavani. Asilirsa aday aranmaz, eski yola dusulur.
SAHNE_SURE_TAVANI_SN = float(os.environ.get("MEDYA_AVCI_SAHNE_SN", "25"))
# Tum is icin toplam tavan (paralel sahneler ortak sayar).
IS_SURE_TAVANI_SN = float(os.environ.get("MEDYA_AVCI_IS_SN", "240"))
# Bir sahnede en fazla kac aday indirilip kare kapisindan gecirilir.
MAKS_DENEME = int(os.environ.get("MEDYA_AVCI_MAKS_DENEME", "3"))

# Durdurma nedenleri — hepsi GORUNUR, hicbiri sessiz degil.
NEDEN = {
    "KAPALI": "medya avcisi acik degil (opt-in)",
    "MODUL-YOK": "Faz B medya paketi yuklenemedi",
    "DOGRULAYICI-YOK": "kare dogrulayici verilmedi — fail-closed",
    "ISTEK-YOK": "ag istegi cagrilabiliri verilmedi",
    "SURE-ASIMI": "is/sahne sure tavani doldu",
    "ADAY-YOK": "lisans+provenance duvarindan gecen aday cikmadi",
    "INDIRME-BASARISIZ": "aday indirilemedi ya da dosya dogrulamasi tutmadi",
    "KARE-KAPISI": "indirilen klip kare kapisindan gecemedi",
    "HATA": "beklenmeyen hata",
}

_KILIT = threading.Lock()
_DURUM = {"baslangic": None, "denenen": 0, "secilen": 0, "dususler": []}


def acik_mi(is_ayar=None) -> tuple:
    """(acik, gerekce). Env bayragi YA DA dahili is ayari.

    ⚠ `is_ayar` DAHILI bir sozluktur; `/api/generate`in 22 alani buraya
    ulasmaz (arayuz bu alani gondermez, `server.py` de okumaz).
    """
    if ACIK:
        return True, "MEDYA_AVCISI ortam degiskeni acik"
    try:
        if isinstance(is_ayar, dict) and is_ayar.get("medya_avcisi") is True:
            return True, "is ayari medya_avcisi=True"
    except Exception:
        pass
    return False, NEDEN["KAPALI"]


def kayit_sifirla() -> None:
    """Her isin basinda cagrilir. Sayaclar ONCEKI isten TASINMAZ."""
    with _KILIT:
        _DURUM["baslangic"] = time.monotonic()
        _DURUM["denenen"] = 0
        _DURUM["secilen"] = 0
        _DURUM["dususler"] = []


def _dusus(neden_kodu: str, ayrinti: str = "", sahne: str = "") -> dict:
    kayit = {"asama": "medya-avcisi", "neden": neden_kodu,
             "etki": NEDEN.get(neden_kodu, neden_kodu),
             "ayrinti": str(ayrinti)[:200]}
    if sahne:
        kayit["sahne"] = str(sahne)
    with _KILIT:
        if len(_DURUM["dususler"]) < 60:
            _DURUM["dususler"].append(kayit)
    return kayit


def _sure_doldu() -> bool:
    with _KILIT:
        bas = _DURUM["baslangic"]
    if bas is None:
        return False
    return (time.monotonic() - bas) >= IS_SURE_TAVANI_SN


def ozet() -> dict:
    """Ise yazilacak GORUNUR ozet. Kapi hic calismadiysa bu da gorunur."""
    with _KILIT:
        return {"acik": bool(ACIK), "denenen": _DURUM["denenen"],
                "secilen": _DURUM["secilen"],
                "dusus_sayisi": len(_DURUM["dususler"]),
                "dususler": list(_DURUM["dususler"][:20])}


def dususler() -> list:
    with _KILIT:
        return list(_DURUM["dususler"])


def _avci_yukle():
    """Faz B paketini GEC yukle. Import hatasi hatti COKERTMEZ."""
    try:
        from medya import avci, indirme          # noqa: F401
        return avci, indirme
    except Exception as e:
        print(f"  medya avcisi yuklenemedi: {type(e).__name__}: "
              f"{str(e)[:120]}", file=sys.stderr)
        return None, None


def sahne_medyasi(*, sorgu: str, hedef_yol: str, sahne_amaci: str = "",
                  iddia_metni: str = "", fact_id: str = "", scene_id: str = "",
                  konsept=None, bilinen_yerler=None, konu: str = "",
                  yer_terim=None, erisim_tarihi: str = "",
                  istek=None, kare_dogrula=None, sinir=None, defter=None,
                  onbellek=None, is_ayar=None, medya_turu: str = "video",
                  coz=None) -> dict:
    """Tek sahne icin Faz B avcisiyla medya bul, indir, KARE KAPISINDAN gecir.

    Doner: {"ok": bool, "yol": str, "neden": str, "aday": {...},
            "atif": str, "dususler": [...]}

    ⚠ HICBIR DURUMDA ISTISNA FIRLATMAZ. `ok=False` ise cagiran taraf MEVCUT
    guvenli yolunu (kaynak.footage_getir) aynen surdurur.
    ⚠ `kare_dogrula` VERILMEZSE hicbir aday kabul edilmez (fail-closed):
    kare kapisi bu koprunun BYPASS EDILEMEZ sartidir.
    """
    bos = {"ok": False, "yol": "", "neden": "", "aday": {}, "atif": "",
           "dususler": []}
    acik, _g = acik_mi(is_ayar)
    if not acik:
        return {**bos, "neden": "KAPALI"}
    if not callable(kare_dogrula):
        return {**bos, "neden": "DOGRULAYICI-YOK",
                "dususler": [_dusus("DOGRULAYICI-YOK", sahne=scene_id)]}
    if not callable(istek):
        return {**bos, "neden": "ISTEK-YOK",
                "dususler": [_dusus("ISTEK-YOK", sahne=scene_id)]}
    if _sure_doldu():
        return {**bos, "neden": "SURE-ASIMI",
                "dususler": [_dusus("SURE-ASIMI", "is tavani", scene_id)]}

    avci, indirme = _avci_yukle()
    if avci is None:
        return {**bos, "neden": "MODUL-YOK",
                "dususler": [_dusus("MODUL-YOK", sahne=scene_id)]}

    sahne_bas = time.monotonic()
    try:
        sonuc = avci.sahne_ara(
            scene_id=scene_id or "s000",
            iddia_metni=iddia_metni or sorgu,
            fact_id=fact_id or "",
            sahne_amaci=sahne_amaci or "establishing",
            konu=konu, bilinen_yerler=list(bilinen_yerler or []),
            erisim_tarihi=erisim_tarihi or "",
            medya_turu=medya_turu,
            sinir=sinir, onbellek=onbellek, defter=defter, istek=istek,
            coz=coz, konsept=konsept)
    except Exception as e:
        return {**bos, "neden": "HATA",
                "dususler": [_dusus("HATA", f"{type(e).__name__}: {e}",
                                    scene_id)]}

    # ── LISANS + PROVENANCE DUVARI ──
    # Aday listesi DEGIL, avcinin SECTIKLERI kullanilir; ustune
    # `render_kullanilabilir` bir kez daha dogrulanir (derinlemesine savunma).
    adaylar = [a for a in (sonuc.get("secilen") or [])
               if getattr(a, "render_kullanilabilir", False)
               and str(getattr(a, "indirme_url", "") or "").strip()]
    if not adaylar:
        return {**bos, "neden": "ADAY-YOK",
                "dususler": [_dusus(
                    "ADAY-YOK",
                    f"{len(sonuc.get('adaylar') or [])} aday tarandi, "
                    f"lisans/alaka duvarindan gecen yok", scene_id)]}

    for aday in adaylar[:MAKS_DENEME]:
        if _sure_doldu() or (time.monotonic() - sahne_bas) >= SAHNE_SURE_TAVANI_SN:
            _dusus("SURE-ASIMI", "sahne tavani", scene_id)
            break
        with _KILIT:
            _DURUM["denenen"] += 1
        # ── SSRF-GUVENLI INDIRME (dogrudan requests YOK) ──
        # ⚠ `guvenli_indir` SOZLUK doner: {"ok", "sebep", ...}. SSRF, icerik
        # turu, bayt tavani ve decode kapilari ORADA uygulanir; bu kopru
        # onlarin hicbirini atlamaz.
        try:
            ind = indirme.guvenli_indir(
                str(aday.indirme_url), hedef_yol, istek=istek, coz=coz,
                beklenen=("video" if medya_turu == "video" else "image"))
            ok_ind = bool(isinstance(ind, dict) and ind.get("ok"))
            ind_not = (ind or {}).get("sebep", "") if isinstance(ind, dict) \
                else "beklenmeyen indirme donusu"
        except Exception as e:
            ok_ind, ind_not = False, f"{type(e).__name__}: {e}"
        if not ok_ind:
            _dusus("INDIRME-BASARISIZ", f"{aday.saglayici}: {ind_not}", scene_id)
            _sil(hedef_yol)
            continue

        # ── KARE KAPISI (BYPASS EDILEMEZ) ──
        try:
            kare_ok = bool(kare_dogrula(hedef_yol, sorgu, list(yer_terim or []),
                                        str(getattr(aday, "asset_id", "")),
                                        str(getattr(aday, "saglayici", ""))))
        except Exception as e:
            # Dogrulayici patlarsa aday KABUL EDILMEZ (fail-closed).
            kare_ok = False
            ind_not = f"kare dogrulayici hatasi: {type(e).__name__}: {e}"
        if not kare_ok:
            _dusus("KARE-KAPISI", f"{aday.saglayici}/{aday.asset_id}", scene_id)
            _sil(hedef_yol)
            continue

        with _KILIT:
            _DURUM["secilen"] += 1
        return {"ok": True, "yol": hedef_yol, "neden": "",
                "aday": {"saglayici": str(getattr(aday, "saglayici", "")),
                         "asset_id": str(getattr(aday, "asset_id", "")),
                         "lisans": str(getattr(aday, "lisans", "")),
                         "orijinal_url": str(getattr(aday, "orijinal_url", "")),
                         "eser_sahibi": str(getattr(aday, "eser_sahibi", "")),
                         "skor": getattr(aday, "toplam_skor", 0)},
                "atif": str(getattr(aday, "atif_metni", "") or ""),
                "dususler": []}

    return {**bos, "neden": "KARE-KAPISI",
            "dususler": [_dusus("ADAY-YOK",
                                "tum adaylar indirme/kare kapisinda dustu",
                                scene_id)]}


def _sil(yol: str) -> None:
    try:
        if yol and os.path.exists(yol):
            os.remove(yol)
    except OSError:
        pass
