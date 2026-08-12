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
    "BUTCE": "is butcesi tavani doldu (para/sure/istek/bayt/kare)",
    "HATA": "beklenmeyen hata",
}

# ── FAZ I-7: BUTCE VARSAYILANLARI ──
# ⚠ `MEDYA_AVCI_MAKS_USD` VARSAYILAN 0.0 — yani hicbir UCRETLI cagriya yer
# ayrilmaz. Acmak ACIK bir karardir ve env/config ile yapilir.
VARSAYILAN_MAKS_USD = float(os.environ.get("MEDYA_AVCI_MAKS_USD", "0"))
VARSAYILAN_MAKS_ISTEK = int(os.environ.get("MEDYA_AVCI_MAKS_ISTEK", "60"))
VARSAYILAN_MAKS_BAYT = int(os.environ.get("MEDYA_AVCI_MAKS_BAYT",
                                          str(400 * 1024 * 1024)))
VARSAYILAN_MAKS_KARE = int(os.environ.get("MEDYA_AVCI_MAKS_KARE", "40"))


class IsButcesi:
    """TEK ISE ait para / sure / istek / bayt / kare tavani (Faz I-7).

    ⚠ NEDEN VAR: I-6'da sayaclar MODUL DUZEYINDE global bir sozlukteydi. Ayni
    surecte iki is kosarsa sayaclar birbirine karisiyordu ve "is basina tavan"
    iddiasi karsiliksiz kaliyordu. Artik her is KENDI nesnesini tasir.

    ⚠ BES TAVAN DA ZORUNLU: `None` gecmek `ValueError`. Sinirsiz butce bu
    depoda yasak (`arastirma.butce`, `kare_kapisi.KareButce` ile ayni kural).
    Sifir gecmek kapiyi KAPATIR, sinirsiz yapmaz.

    ⚠ THREAD GUVENLI: `_sahne_medya` paralel thread'lerde kosar. Kontrol ve
    harcama TEK kilit altinda (`*_ayir`) yapilir; kilitsiz sayacla iki thread
    ayni anda kontrol edip tavani asardi.
    """

    def __init__(self, is_adi: str = "is", *, maks_usd: float = None,
                 maks_sure_sn: float = None, maks_istek: int = None,
                 maks_bayt: int = None, maks_kare: int = None, saat=None):
        maks_usd = VARSAYILAN_MAKS_USD if maks_usd is None else maks_usd
        maks_sure_sn = (IS_SURE_TAVANI_SN if maks_sure_sn is None
                        else maks_sure_sn)
        maks_istek = VARSAYILAN_MAKS_ISTEK if maks_istek is None else maks_istek
        maks_bayt = VARSAYILAN_MAKS_BAYT if maks_bayt is None else maks_bayt
        maks_kare = VARSAYILAN_MAKS_KARE if maks_kare is None else maks_kare
        degerler = (float(maks_usd), float(maks_sure_sn), float(maks_istek),
                    float(maks_bayt), float(maks_kare))
        if min(degerler) < 0:
            raise ValueError("IsButcesi: negatif tavan olamaz")
        self.is_adi = str(is_adi)
        self.maks_usd = float(maks_usd)
        self.maks_sure_sn = float(maks_sure_sn)
        self.maks_istek = int(maks_istek)
        self.maks_bayt = int(maks_bayt)
        self.maks_kare = int(maks_kare)
        self._saat = saat or time.monotonic
        self._kilit = threading.Lock()
        self.baslangic = self._saat()
        self.istek = 0
        self.bayt = 0
        self.kare = 0
        self.denenen = 0
        self.secilen = 0
        self._dususler = []
        self._secimler = []      # Faz I-10: manifest icin
        self._bosluklar = []     # Faz I-10: kapsam bosluklari
        # Faz A/B nesneleri — avciya GECIRILIR, boylece para tavani gercekten
        # saglayici katmaninda uygulanir (I-6'da `defter=None` geciyordu).
        self.defter = None
        self.sinir = None
        try:
            from arastirma.butce import KosuSiniri
            from arastirma.cache import MaliyetDefteri
            self.defter = MaliyetDefteri(self.is_adi, tavan_usd=self.maks_usd)
            self.sinir = KosuSiniri(toplam_sure_sn=int(self.maks_sure_sn))
        except Exception as e:                     # ortam sorunu COKERTMEZ
            print(f"  butce nesneleri kurulamadi: {type(e).__name__}",
                  file=sys.stderr)

    # ── sayac + tavan ──
    def gecen_sn(self) -> float:
        return max(0.0, self._saat() - self.baslangic)

    def _sure_doldu(self) -> bool:
        return self.gecen_sn() >= self.maks_sure_sn

    def bitti_mi(self) -> tuple:
        """(bitti, neden). Herhangi bir tavan dolduysa True."""
        with self._kilit:
            return self._bitti_mi()

    def _bitti_mi(self) -> tuple:
        if self._sure_doldu():
            return True, (f"sure tavani doldu "
                          f"({self.gecen_sn():.1f}/{self.maks_sure_sn:.0f} sn)")
        if self.istek >= self.maks_istek:
            return True, f"istek tavani doldu ({self.istek}/{self.maks_istek})"
        if self.bayt >= self.maks_bayt:
            return True, f"bayt tavani doldu ({self.bayt}/{self.maks_bayt})"
        if self.kare >= self.maks_kare:
            return True, f"kare cagrisi tavani doldu ({self.kare}/{self.maks_kare})"
        harcanan = self.defter.toplam if self.defter is not None else 0.0
        if harcanan > self.maks_usd:
            return True, (f"USD tavani asildi "
                          f"(${harcanan:.4f}/${self.maks_usd:.4f})")
        return False, ""

    def istek_ayir(self, adet: int = 1) -> tuple:
        """Kontrol + harcama TEK kilit altinda (kontrol-sonra-harca yarisi yok)."""
        with self._kilit:
            bitti, neden = self._bitti_mi()
            if bitti:
                return False, neden
            if self.istek + adet > self.maks_istek:
                return False, (f"istek tavani doldu "
                               f"({self.istek}+{adet}/{self.maks_istek})")
            self.istek += adet
            return True, ""

    def kare_ayir(self, adet: int = 1) -> tuple:
        with self._kilit:
            bitti, neden = self._bitti_mi()
            if bitti:
                return False, neden
            if self.kare + adet > self.maks_kare:
                return False, (f"kare cagrisi tavani doldu "
                               f"({self.kare}+{adet}/{self.maks_kare})")
            self.kare += adet
            return True, ""

    def bayt_ayir(self, adet: int) -> tuple:
        with self._kilit:
            bitti, neden = self._bitti_mi()
            if bitti:
                return False, neden
            if self.bayt + int(adet or 0) > self.maks_bayt:
                return False, (f"bayt tavani doldu "
                               f"({self.bayt}+{int(adet or 0)}/{self.maks_bayt})")
            self.bayt += int(adet or 0)
            return True, ""

    def denendi(self) -> None:
        with self._kilit:
            self.denenen += 1

    def secildi(self, kayit: dict = None) -> None:
        """Secimi say ve — verilmisse — MANIFEST icin kaydet (Faz I-10).

        ⚠ Kayit IS BASINA tutulur; paralel isler birbirinin secimini gormez.
        """
        with self._kilit:
            self.secilen += 1
            if isinstance(kayit, dict) and len(self._secimler) < 400:
                self._secimler.append(dict(kayit))

    def secimler(self) -> list:
        """Bu iste GERCEKTEN secilmis (lisansli + kare dogrulanmis) kayitlar."""
        with self._kilit:
            return [dict(k) for k in self._secimler]

    def bosluk_ekle(self, scene_id: str, neden: str) -> None:
        """Kapsam boslugu — RASTGELE STOKLA KAPANMAZ, kayda gecer."""
        with self._kilit:
            if len(self._bosluklar) < 200:
                self._bosluklar.append({"scene_id": str(scene_id or ""),
                                        "neden": str(neden or "")[:160]})

    def bosluklar(self) -> list:
        with self._kilit:
            return [dict(b) for b in self._bosluklar]

    def dusus(self, neden_kodu: str, ayrinti: str = "", sahne: str = "") -> dict:
        kayit = {"asama": "medya-avcisi", "neden": neden_kodu,
                 "etki": NEDEN.get(neden_kodu, neden_kodu),
                 "ayrinti": str(ayrinti)[:200]}
        if sahne:
            kayit["sahne"] = str(sahne)
        with self._kilit:
            if len(self._dususler) < 60:
                self._dususler.append(kayit)
        return kayit

    def dususler(self) -> list:
        with self._kilit:
            return list(self._dususler)

    def ozet(self) -> dict:
        """BES TAVAN BIRLIKTE raporlanir — biri gizlenmez."""
        with self._kilit:
            harcanan = self.defter.toplam if self.defter is not None else 0.0
            bitti, neden = self._bitti_mi()
            return {
                "is_adi": self.is_adi,
                "denenen": self.denenen, "secilen": self.secilen,
                "usd": round(harcanan, 6), "maks_usd": self.maks_usd,
                "istek": self.istek, "maks_istek": self.maks_istek,
                "bayt": self.bayt, "maks_bayt": self.maks_bayt,
                "kare_cagrisi": self.kare, "maks_kare": self.maks_kare,
                "gecen_sn": round(self.gecen_sn(), 2),
                "maks_sure_sn": self.maks_sure_sn,
                "tavan_doldu": bitti, "durma_nedeni": neden,
                "dusus_sayisi": len(self._dususler),
                "secim_kaydi": len(self._secimler),
                "kapsam_boslugu": len(self._bosluklar),
                "dususler": list(self._dususler[:20]),
            }


def is_butcesi_kur(is_adi: str = "is", **ez) -> IsButcesi:
    """Her is icin YENI ve IZOLE butce. Sayaclar onceki isten TASINMAZ."""
    return IsButcesi(is_adi, **ez)


# ⚠ GERIYE UYUMLULUK: `butce` verilmeden cagrilan eski yollar icin MODUL
# duzeyinde varsayilan bir butce tutulur. Pipeline artik IS BASINA nesne
# kuruyor; bu varsayilan yalnizca eski imzayi kirmamak icin var.
_KILIT = threading.Lock()
_VARSAYILAN_BUTCE = [None]


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


def kayit_sifirla(is_adi: str = "is", **ez) -> IsButcesi:
    """MODUL varsayilan butcesini yeniler ve DONDURUR.

    ⚠ Faz I-7: is-basi izolasyon icin `is_butcesi_kur()` kullanilmali ve
    donen nesne `sahne_medyasi(butce=...)` ile gecirilmelidir. Bu fonksiyon
    yalnizca `butce` verilmeyen ESKI cagri yolunu kirmamak icin duruyor.
    """
    b = IsButcesi(is_adi, **ez)
    with _KILIT:
        _VARSAYILAN_BUTCE[0] = b
    return b


def _varsayilan_butce() -> IsButcesi:
    with _KILIT:
        if _VARSAYILAN_BUTCE[0] is None:
            _VARSAYILAN_BUTCE[0] = IsButcesi("varsayilan")
        return _VARSAYILAN_BUTCE[0]


def ozet() -> dict:
    """MODUL varsayilan butcesinin ozeti (eski cagri yolu)."""
    o = _varsayilan_butce().ozet()
    o["acik"] = bool(ACIK)
    return o


def dususler() -> list:
    return _varsayilan_butce().dususler()


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
                  coz=None, butce=None) -> dict:
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
    # ⚠ FAZ I-7: butce IS BASINA nesnedir. Verilmezse modul varsayilanina
    # dusulur (eski cagri yolu); pipeline her is icin KENDI nesnesini kurar.
    b = butce if isinstance(butce, IsButcesi) else _varsayilan_butce()
    if not callable(kare_dogrula):
        return {**bos, "neden": "DOGRULAYICI-YOK",
                "dususler": [b.dusus("DOGRULAYICI-YOK", sahne=scene_id)]}
    if not callable(istek):
        return {**bos, "neden": "ISTEK-YOK",
                "dususler": [b.dusus("ISTEK-YOK", sahne=scene_id)]}
    _bitti, _neden = b.bitti_mi()
    if _bitti:
        return {**bos, "neden": "BUTCE",
                "dususler": [b.dusus("BUTCE", _neden, scene_id)]}

    avci, indirme = _avci_yukle()
    if avci is None:
        return {**bos, "neden": "MODUL-YOK",
                "dususler": [b.dusus("MODUL-YOK", sahne=scene_id)]}

    # ⚠ Saglayici arama TEK istek hakki tuketir; tavan dolarsa ARAMA YAPILMAZ.
    _ok_i, _n_i = b.istek_ayir(1)
    if not _ok_i:
        return {**bos, "neden": "BUTCE",
                "dususler": [b.dusus("BUTCE", _n_i, scene_id)]}

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
            sinir=sinir if sinir is not None else b.sinir,
            onbellek=onbellek,
            defter=defter if defter is not None else b.defter,
            istek=istek, coz=coz, konsept=konsept)
    except Exception as e:
        return {**bos, "neden": "HATA",
                "dususler": [b.dusus("HATA", f"{type(e).__name__}: {e}",
                                     scene_id)]}

    # ── LISANS + PROVENANCE DUVARI ──
    # Aday listesi DEGIL, avcinin SECTIKLERI kullanilir; ustune
    # `render_kullanilabilir` bir kez daha dogrulanir (derinlemesine savunma).
    adaylar = [a for a in (sonuc.get("secilen") or [])
               if getattr(a, "render_kullanilabilir", False)
               and str(getattr(a, "indirme_url", "") or "").strip()]
    if not adaylar:
        return {**bos, "neden": "ADAY-YOK",
                "dususler": [b.dusus(
                    "ADAY-YOK",
                    f"{len(sonuc.get('adaylar') or [])} aday tarandi, "
                    f"lisans/alaka duvarindan gecen yok", scene_id)]}

    son_neden = "ADAY-YOK"
    for aday in adaylar[:MAKS_DENEME]:
        _bitti, _neden = b.bitti_mi()
        if _bitti or (time.monotonic() - sahne_bas) >= SAHNE_SURE_TAVANI_SN:
            son_neden = "BUTCE" if _bitti else "SURE-ASIMI"
            b.dusus(son_neden, _neden or "sahne tavani", scene_id)
            break
        b.denendi()
        # Indirme de bir ISTEK hakki tuketir (tavan dolarsa indirilmez).
        _ok_d, _n_d = b.istek_ayir(1)
        if not _ok_d:
            son_neden = "BUTCE"
            b.dusus("BUTCE", _n_d, scene_id)
            break
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
            son_neden = "INDIRME-BASARISIZ"
            b.dusus("INDIRME-BASARISIZ", f"{aday.saglayici}: {ind_not}",
                    scene_id)
            _sil(hedef_yol)
            continue

        # Inen bayt is tavanina yazilir; tavan asildiysa klip KABUL EDILMEZ.
        _inen = int((ind or {}).get("okunan_bayt") or 0) if isinstance(ind, dict) else 0
        _ok_b, _n_b = b.bayt_ayir(_inen)
        if not _ok_b:
            son_neden = "BUTCE"
            b.dusus("BUTCE", f"{_n_b} ({aday.saglayici})", scene_id)
            _sil(hedef_yol)
            break

        # ── KARE KAPISI (BYPASS EDILEMEZ) ──
        # ⚠ Kare cagrisi PARA harcayabilir (vision). Tavan dolduysa klip
        # DOGRULANAMAZ, dolayisiyla KABUL DE EDILMEZ (fail-closed).
        _ok_k, _n_k = b.kare_ayir(1)
        if not _ok_k:
            son_neden = "BUTCE"
            b.dusus("BUTCE", f"{_n_k} — kare dogrulanamadi, aday reddedildi",
                    scene_id)
            _sil(hedef_yol)
            break
        try:
            kare_ok = bool(kare_dogrula(hedef_yol, sorgu, list(yer_terim or []),
                                        str(getattr(aday, "asset_id", "")),
                                        str(getattr(aday, "saglayici", ""))))
        except Exception as e:
            # Dogrulayici patlarsa aday KABUL EDILMEZ (fail-closed).
            kare_ok = False
            ind_not = f"kare dogrulayici hatasi: {type(e).__name__}: {e}"
        if not kare_ok:
            son_neden = "KARE-KAPISI"
            b.dusus("KARE-KAPISI", f"{aday.saglayici}/{aday.asset_id}",
                    scene_id)
            _sil(hedef_yol)
            continue

        _kayit = {
            "scene_id": str(scene_id or ""),
            "fact_id": str(fact_id or getattr(aday, "fact_id", "") or ""),
            "asset_id": str(getattr(aday, "asset_id", "")),
            "saglayici": str(getattr(aday, "saglayici", "")),
            "lisans": str(getattr(aday, "lisans", "")),
            "orijinal_url": str(getattr(aday, "orijinal_url", "")),
            "eser_sahibi": str(getattr(aday, "eser_sahibi", "")),
            "atif_metni": str(getattr(aday, "atif_metni", "") or ""),
            "atif_gerekli": bool(getattr(aday, "atif_gerekli", True)),
            "sorgu": str(getattr(aday, "sorgu", "") or ""),
            "medya_yolu": hedef_yol,
            # ⚠ `editor.plan` medya yolunu `yerel_yol` alanindan OKUR
            # (plan.py:203). Yalnizca `medya_yolu` yazmak sessiz bir
            # kayipti: plan aday buluyor ama MEDYASI BOS kaliyordu —
            # 20 sn smoke render'inda GORSELLERIN HIC GORUNMEMESIYLE
            # olculdu. Iki ad da yazilir (geriye uyumlu).
            "yerel_yol": hedef_yol,
            "medya_turu": medya_turu,
            "tur": medya_turu,
            "sahne_amaci": str(sahne_amaci or ""),
            "baslik": str(getattr(aday, "baslik", "") or ""),
            "genislik": int(getattr(aday, "genislik", 0) or 0),
            "yukseklik": int(getattr(aday, "yukseklik", 0) or 0),
            "sure_sn": float(getattr(aday, "sure_sn", 0) or 0),
            "toplam_skor": getattr(aday, "toplam_skor", 0),
            # ⚠ Bu kayit YALNIZCA lisans duvarindan VE kare kapisindan
            # gecmis adaylar icin olusur; bayrak burada dogrudur.
            "render_kullanilabilir": True,
        }
        b.secildi(_kayit)
        return {"ok": True, "yol": hedef_yol, "neden": "",
                # ⚠ FAZ I-8: ATIF ZINCIRI fact_id'yi KORUR. Aday, sorgu ve
                # atif ayni olguya baglidir; "hangi iddia icin hangi klip"
                # sorusu sonradan cevaplanabilir olmali.
                "fact_id": str(fact_id or getattr(aday, "fact_id", "") or ""),
                "aday": {"saglayici": str(getattr(aday, "saglayici", "")),
                         "asset_id": str(getattr(aday, "asset_id", "")),
                         "lisans": str(getattr(aday, "lisans", "")),
                         "orijinal_url": str(getattr(aday, "orijinal_url", "")),
                         "eser_sahibi": str(getattr(aday, "eser_sahibi", "")),
                         "fact_id": str(fact_id or getattr(aday, "fact_id", "")
                                        or ""),
                         "sorgu": str(getattr(aday, "sorgu", "") or ""),
                         "skor": getattr(aday, "toplam_skor", 0)},
                "atif": str(getattr(aday, "atif_metni", "") or ""),
                "dususler": []}

    # ⚠ Son neden GERCEK sebebi bildirir: butce yuzunden durduysak
    # "kare kapisi" demek yanlis olurdu (olculdu, duzeltildi).
    return {**bos, "neden": son_neden,
            "dususler": [b.dusus(
                son_neden,
                "tum adaylar denendi; son sebep yukarida", scene_id)]}


def manifest_kur(butce, *, kapsam_bosluklari=None) -> dict:
    """Is butcesindeki SECIMLERI `editor.plan` medya manifestine cevir (I-10).

    ⚠ YALNIZCA GERCEKTEN SECILMIS kayitlar girer. Bir kayit ancak lisans
    duvarindan VE kare kapisindan gectikten sonra olusur; yani bu manifest
    tanim geregi lisansli + kare dogrulanmis adaylar icerir.
    ⚠ fact_id / provenance / lisans / atif KAYBOLMAZ — hepsi tasinir.
    ⚠ KAPSAM BOSLUGU RASTGELE STOKLA KAPANMAZ: bosluklar aynen tasinir.
    ⚠ ISTISNA FIRLATMAZ; bozuk girdide bos manifest doner.
    """
    bos = {"adaylar": [], "kapsam_bosluklari": [], "ozet": {
        "aday": 0, "bosluk": 0, "kaynak": "medya-avcisi"}}
    try:
        secimler = butce.secimler() if hasattr(butce, "secimler") else []
    except Exception:
        return bos
    adaylar = []
    for k in secimler:
        if not isinstance(k, dict) or not k.get("asset_id"):
            continue
        if k.get("render_kullanilabilir") is not True:
            # Savunma: kayit yalnizca gecen adaylar icin olusur; yine de
            # bayragi olmayan bir kayit MANIFESTE ALINMAZ.
            continue
        adaylar.append(dict(k))
    bosluk = list(kapsam_bosluklari or [])
    try:
        bosluk += butce.bosluklar() if hasattr(butce, "bosluklar") else []
    except Exception:
        pass
    # Ayni sahne icin tekrar eden bosluk kaydini teke indir (gorunurluk kaybi yok)
    gorulen, temiz_bosluk = set(), []
    for b in bosluk:
        if not isinstance(b, dict):
            continue
        anahtar = (str(b.get("scene_id") or ""), str(b.get("neden") or ""))
        if anahtar in gorulen:
            continue
        gorulen.add(anahtar)
        temiz_bosluk.append(dict(b))
    return {"adaylar": adaylar, "kapsam_bosluklari": temiz_bosluk,
            "ozet": {"aday": len(adaylar), "bosluk": len(temiz_bosluk),
                     "kaynak": "medya-avcisi"}}


def _sil(yol: str) -> None:
    try:
        if yol and os.path.exists(yol):
            os.remove(yol)
    except OSError:
        pass
