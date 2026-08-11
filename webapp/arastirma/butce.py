"""KOSU SINIRLARI — sure ve para tavani.

NEDEN VAR (11 Agu 2026, ikinci canli kosu): birinci kosu 18 iddia + $0.26 ile
bitti. Ikinci kosu ONBELLEK TEMIZLENDIGI icin bastan arama yapmak zorunda kaldi
ve 15+ dakika sonuc uretmedi; elle oldurmek gerekti. Tek bir kaynagin
takilmasi TUM kosuyu kilitliyordu ve kismi sonuc bile alinamiyordu.

Bu modul uc guvence veriyor:

  1. ISTEK BASINA zaman asimi  — her HTTP cagrisinin kendi tavani (zaten vardi,
     burada tek yerden yonetiliyor)
  2. TOPLAM KOSU suresi        — sure biterse kosu KONTROLLU durur ve o ana
     kadarki iddialar korunur; manifeste neden yazilir
  3. PARA tavani               — MaliyetDefteri ile birlikte; asilirsa cagri
     YAPILMADAN durulur

Tasarim karari: sure/para bittiginde HATA FIRLATMIYORUZ, "dur" sinyali
veriyoruz. Cunku 12 iddia toplanmisken 13.'de sure bitmesi bir basarisizlik
degil — kismi sonuc kullanilabilir ve manifest bunu acikca yaziyor.
"""
from __future__ import annotations

import os
import time
from typing import Optional

# Istek basina varsayilanlar (saniye)
ZAMAN_ASIMI = {
    "soru": int(os.environ.get("ARASTIRMA_TO_SORU", "60")),
    "arama": int(os.environ.get("ARASTIRMA_TO_ARAMA", "90")),
    "sayfa": int(os.environ.get("ARASTIRMA_TO_SAYFA", "20")),
    "llm": int(os.environ.get("ARASTIRMA_TO_LLM", "60")),
}
# Toplam kosu tavani. Ikinci kosu 15+ dk takildigi icin varsayilan 8 dakika:
# birinci kosu (18 iddia, tam arama) ~4.5 dakikada bitmisti.
TOPLAM_SURE_SN = int(os.environ.get("ARASTIRMA_TOPLAM_SURE", "480"))
# Kucuk varsayilan para tavani — kullanici istegi. Birinci kosu $0.26 idi.
VARSAYILAN_TAVAN_USD = float(os.environ.get("ARASTIRMA_TAVAN_USD", "0.60"))


class KosuSiniri:
    """Bir arastirma kosusunun sure/para sinirlarini tutar ve 'devam edilir mi'
    sorusunu cevaplar. `simdi` disaridan verilebilir (testler saat bagimsiz)."""

    def __init__(self, toplam_sure_sn: Optional[int] = None,
                 baslangic: Optional[float] = None):
        self.toplam_sure = (TOPLAM_SURE_SN if toplam_sure_sn is None
                            else int(toplam_sure_sn))
        self.baslangic = time.monotonic() if baslangic is None else float(baslangic)
        self.durma_nedeni = ""
        self._saat = None            # testte sabit saat icin

    def saat_ayarla(self, fn) -> None:
        """Test icin: monotonic yerine kullanilacak fonksiyon."""
        self._saat = fn

    def _simdi(self) -> float:
        return self._saat() if self._saat else time.monotonic()

    @property
    def gecen(self) -> float:
        return max(0.0, self._simdi() - self.baslangic)

    @property
    def kalan(self) -> float:
        return max(0.0, self.toplam_sure - self.gecen)

    def bitti_mi(self) -> bool:
        if self.durma_nedeni:
            return True
        if self.kalan <= 0:
            self.durma_nedeni = (f"toplam sure tavani asildi "
                                 f"({self.toplam_sure} sn)")
            return True
        return False

    def durdur(self, neden: str) -> None:
        if not self.durma_nedeni:
            self.durma_nedeni = neden

    def istek_zaman_asimi(self, tur: str) -> int:
        """Istek basina zaman asimi — KALAN SUREYI ASAMAZ.

        Kritik incelik: 90 sn'lik bir arama cagrisi, toplam sureden 20 sn kalmisken
        baslatilirsa tavan 70 sn asilir. Bu yuzden istek tavani kalan sureyle
        kirpilir; en az 5 sn birakilir ki anlamsiz cagri yapilmasin."""
        temel = ZAMAN_ASIMI.get(tur, 60)
        return max(5, min(temel, int(self.kalan)))

    def ozet(self) -> dict:
        return {"toplam_sure_sn": self.toplam_sure,
                "gecen_sn": round(self.gecen, 1),
                "kalan_sn": round(self.kalan, 1),
                "durma_nedeni": self.durma_nedeni}
