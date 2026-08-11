"""SAGLAYICI KAYIT SISTEMI.

Tasarim hedefi (kullanici istegi): "yeni saglayici TEK SINIFLA eklenebilsin".

Bir saglayici `Saglayici` sinifindan turer, `ara()` metodunu yazar ve
`@kaydet` ile kendini kaydeder. Baska hicbir yere dokunmak gerekmez —
`aktif_saglayicilar()` onu otomatik gorur.

Iki onemli davranis:

  1. ANAHTAR GEREKTIREN saglayici anahtar yoksa KONTROLLU ATLANIR.
     Hata firlatmaz, `atlandi` listesine sebep yazilir. Wikimedia/Openverse/
     LoC/Archive.org anahtarsiz calisir; Pexels/Coverr anahtar ister.
  2. DEVRE KESICI (circuit breaker): bir saglayici ust uste basarisiz
     olursa o kosu boyunca DEVRE DISI kalir. Neden: Faz A'da tek takilan
     bir cagri 15+ dakika kosuyu kilitledi. Ayni hatayi saglayici katmaninda
     tekrarlamamak icin her saglayicinin kendi sabir siniri var.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

_KAYIT: dict = {}

# Bir saglayici kac kez ust uste basarisiz olursa devreden cikar
DEVRE_ESIGI = int(os.environ.get("MEDYA_DEVRE_ESIGI", "2"))


def kaydet(sinif):
    """Sinif dekoratoru: saglayiciyi kayda ekler."""
    ornek = sinif()
    _KAYIT[ornek.ad] = ornek
    return sinif


def saglayici(ad: str):
    return _KAYIT.get(ad)


def tum_saglayicilar() -> list:
    return list(_KAYIT.values())


def aktif_saglayicilar(istenen: Optional[list] = None) -> tuple[list, list]:
    """(kullanilabilir, atlanan). Atlanan: [{"ad":..,"sebep":..}]"""
    kullanilabilir, atlanan = [], []
    for s in _KAYIT.values():
        if istenen and s.ad not in istenen:
            continue
        ok, sebep = s.hazir_mi()
        (kullanilabilir if ok else atlanan).append(s if ok else
                                                  {"ad": s.ad, "sebep": sebep})
    kullanilabilir.sort(key=lambda x: (-x.oncelik, x.ad))
    return kullanilabilir, atlanan


@dataclass
class AramaSonucu:
    """Saglayicinin ham donusu — henuz lisans karari verilmemis."""
    kayitlar: list = field(default_factory=list)   # list[dict] ham saglayici kaydi
    hata: str = ""
    sorgu: str = ""
    saglayici: str = ""
    istek_sayisi: int = 0


class Saglayici:
    """Tum saglayicilarin taban sinifi.

    Alt sinif SADECE sunlari tanimlar:
      ad, oncelik, anahtar_env (varsa), medya_turleri
      ara(sorgu, ...) -> AramaSonucu
      normalize(kayit) -> dict   (ortak alan adlarina cevirme)
    """
    ad: str = "taban"
    oncelik: int = 0                 # yuksek = once denenir
    anahtar_env: str = ""            # bos = anahtar gerekmez
    anahtar_dosya: str = ""
    medya_turleri: tuple = ("image",)
    # Arsiv/kamu malı saglayicilar cesitlilik icin oncelikli sayilir
    kamu_mali: bool = False

    def __init__(self):
        self.hata_sayisi = 0
        self.devre_disi = False
        self.devre_nedeni = ""
        self.son_istek = 0.0

    # ── anahtar yonetimi ──
    def anahtar(self) -> str:
        if not self.anahtar_env:
            return ""
        d = (os.environ.get(self.anahtar_env) or "").strip()
        if d:
            return d
        if self.anahtar_dosya:
            yol = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "veri", self.anahtar_dosya)
            try:
                with open(yol) as f:
                    return f.read().strip()
            except Exception:
                return ""
        return ""

    def hazir_mi(self) -> tuple[bool, str]:
        if self.devre_disi:
            return False, f"devre disi: {self.devre_nedeni}"
        if self.anahtar_env and not self.anahtar():
            return False, f"anahtar yok ({self.anahtar_env})"
        return True, ""

    # ── devre kesici ──
    def basarisiz(self, sebep: str) -> None:
        self.hata_sayisi += 1
        if self.hata_sayisi >= DEVRE_ESIGI:
            self.devre_disi = True
            self.devre_nedeni = f"{self.hata_sayisi} ust uste hata: {sebep[:80]}"

    def basarili(self) -> None:
        self.hata_sayisi = 0

    def sifirla(self) -> None:
        self.hata_sayisi = 0
        self.devre_disi = False
        self.devre_nedeni = ""

    # Oge ayrintisi cekilerek lisans/medya URL'si zenginlestirilebilir mi?
    # (LoC arama ucu rights alanini VERMIYOR — bkz. acik_arsivler.LibraryOfCongress)
    detay_destekli: bool = False

    def zenginlestir(self, ham_kayit: dict, normalize: dict, *,
                     zaman_asimi: int = 20,
                     istek: Optional[Callable] = None) -> dict:
        """Oge ayrintisindan eksik alanlari doldur. Varsayilan: hicbir sey.

        BUTCELI cagrilir (bkz. avci.DETAY_BUTCESI): her aday icin ayri istek
        atmak kosuyu uzatir, o yuzden yalnizca lisansi BELIRSIZ kalan ve
        detay_destekli saglayicilarin adaylari icin calisir."""
        return {}

    # ── alt siniflarin yazdigi ──
    def ara(self, sorgu: str, *, tur: str = "image", adet: int = 10,
            zaman_asimi: int = 20, istek: Optional[Callable] = None) -> AramaSonucu:
        raise NotImplementedError

    def normalize(self, kayit: dict) -> dict:
        """Ham kaydi ortak alanlara cevir.
        Beklenen anahtarlar: orijinal_url, indirme_url, baslik, aciklama,
        genislik, yukseklik, sure_sn, tur, konum, tarih + lisans alanlari."""
        raise NotImplementedError


def kosu_sifirla() -> None:
    """Her kosu basinda devre kesicileri temizle."""
    for s in _KAYIT.values():
        s.sifirla()
