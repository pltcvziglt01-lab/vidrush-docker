"""DISK ONBELLEGI + MALIYET DEFTERI.

Iki isi bir arada yapiyor cunku ikisi ayni seyi koruyor: PARA.

Onbellek: web arama, sayfa indirme ve vision cagrilarinin sonuclari diske yazilir.
Ayni URL ikinci kez sorulmaz. 30 dk'lik bir belgeselde ~40 iddia + ~400 klip adayi
var; onbelleksiz her deneme bastan para yakar. Kullanicinin kalici kurali:
"yapilan her hata benim cebimden para olarak cikiyor".

Maliyet defteri: her cagri is bazinda kaydedilir ve TAVAN asilirsa ButceAsimi
firlatilir. Tavan tavsiye degil, sert duvar — asildiginda cagri YAPILMAZ.

Disa bagimlilik yok (stdlib). Zaman disaridan verilir (`simdi` parametresi) ki
testler saat bagimsiz kossun.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from typing import Any, Callable, Optional

VERI_DIZIN = os.environ.get(
    "ANAHTAR_DIZIN",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "veri"))
ONBELLEK_DIZIN = os.path.join(VERI_DIZIN, "onbellek")

# Varsayilan yasam sureleri (saniye). Web arama sonucu tazeligi onemli;
# lisans bilgisi ve sayfa metni daha uzun yasar.
TTL = {
    "arama": 7 * 24 * 3600,       # web arama — 1 hafta
    "sayfa": 30 * 24 * 3600,      # indirilen sayfa metni — 1 ay
    "vision": 90 * 24 * 3600,     # klip vision karari — degismez, uzun
    "lisans": 30 * 24 * 3600,
    "medya_arama": 3 * 24 * 3600,
}


class ButceAsimi(RuntimeError):
    """Isin maliyet tavani asildi — cagri YAPILMADI."""


def _anahtar(ad_alani: str, veri: Any) -> str:
    ham = json.dumps(veri, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(f"{ad_alani}|{ham}".encode()).hexdigest()[:40]


class Onbellek:
    """Basit, dayanikli disk onbellegi. Bozuk/eksik dosya yok sayilir."""

    def __init__(self, kok: str = ONBELLEK_DIZIN, kapali: bool = False):
        self.kok = kok
        self.kapali = kapali
        self.isabet = 0
        self.kacik = 0
        self._kilit = threading.Lock()

    def _yol(self, ad_alani: str, anahtar: str) -> str:
        return os.path.join(self.kok, ad_alani, anahtar[:2], anahtar + ".json")

    def oku(self, ad_alani: str, veri: Any, simdi: Optional[float] = None) -> Optional[Any]:
        if self.kapali:
            return None
        yol = self._yol(ad_alani, _anahtar(ad_alani, veri))
        try:
            with open(yol, encoding="utf-8") as f:
                kayit = json.load(f)
        except Exception:
            with self._kilit:
                self.kacik += 1
            return None
        ttl = TTL.get(ad_alani, 7 * 24 * 3600)
        t = simdi if simdi is not None else time.time()
        if ttl and (t - float(kayit.get("zaman", 0))) > ttl:
            with self._kilit:
                self.kacik += 1
            return None
        with self._kilit:
            self.isabet += 1
        return kayit.get("deger")

    def yaz(self, ad_alani: str, veri: Any, deger: Any,
            simdi: Optional[float] = None) -> None:
        if self.kapali:
            return
        yol = self._yol(ad_alani, _anahtar(ad_alani, veri))
        os.makedirs(os.path.dirname(yol), exist_ok=True)
        gecici = yol + f".tmp{os.getpid()}"
        try:
            with open(gecici, "w", encoding="utf-8") as f:
                json.dump({"zaman": simdi if simdi is not None else time.time(),
                           "deger": deger}, f, ensure_ascii=False)
            os.replace(gecici, yol)
        except Exception:
            try:
                os.remove(gecici)
            except Exception:
                pass

    def getir(self, ad_alani: str, veri: Any, uret: Callable[[], Any],
              simdi: Optional[float] = None) -> Any:
        """Onbellekte varsa dondur, yoksa uret() cagir ve yaz.
        `uret` PARA HARCAYAN tek yer — onbellek isabetinde HIC cagrilmaz."""
        d = self.oku(ad_alani, veri, simdi)
        if d is not None:
            return d
        d = uret()
        if d is not None:
            self.yaz(ad_alani, veri, d, simdi)
        return d

    def ozet(self) -> dict:
        toplam = self.isabet + self.kacik
        return {"isabet": self.isabet, "kacik": self.kacik,
                "isabet_orani": round(self.isabet / toplam, 3) if toplam else 0.0}


# ─────────────────────────── MALIYET ───────────────────────────
# Olculen birim fiyatlar (11 Agu 2026). Model fiyati degisirse BURASI guncellenir;
# kodun baska yerine fiyat yazilmaz.
BIRIM_FIYAT = {
    # (giris_1M_usd, cikis_1M_usd)
    "gpt-4.1":       (2.00, 8.00),
    "gpt-4.1-mini":  (0.40, 1.60),
    "gpt-4o-mini-tts": (0.60, 0.0),     # 1M karakter basina yaklasik
    "whisper-1":     (0.006, 0.0),      # dakika basina
    "gpt-image-1-mini": (0.013, 0.0),   # gorsel basina
    "gpt-image-2":   (0.048, 0.0),      # gorsel basina
}
# Arac cagrisi basina sabit ucretler
ARAC_FIYAT = {
    "web_search": 0.010,      # cagri basina (olculdu: ~$0.035 toplam, token dahil)
}


class MaliyetDefteri:
    """Is bazinda harcama kaydi + SERT tavan.

    Tavan asildiginda `kontrol()` ButceAsimi firlatir; cagiran para harcamadan
    durur. Kullanicinin acik istegi: "uretim basina maksimum maliyet siniri".
    """

    def __init__(self, is_adi: str = "test", tavan_usd: Optional[float] = None):
        self.is_adi = is_adi
        self.tavan = tavan_usd
        self.kayitlar: list = []
        self._kilit = threading.Lock()

    @property
    def toplam(self) -> float:
        return round(sum(k["usd"] for k in self.kayitlar), 6)

    def kalan(self) -> float:
        return float("inf") if self.tavan is None else max(0.0, self.tavan - self.toplam)

    def kontrol(self, tahmini_usd: float = 0.0) -> None:
        """Cagri YAPILMADAN once cagrilir. Tavan asilacaksa firlatir."""
        if self.tavan is None:
            return
        if self.toplam + tahmini_usd > self.tavan:
            raise ButceAsimi(
                f"{self.is_adi}: maliyet tavani asilacak "
                f"(harcanan ${self.toplam:.4f} + tahmini ${tahmini_usd:.4f} "
                f"> tavan ${self.tavan:.4f})")

    def kaydet(self, asama: str, kalem: str, usd: float, detay: str = "") -> None:
        with self._kilit:
            self.kayitlar.append({"asama": asama, "kalem": kalem,
                                  "usd": round(float(usd), 6), "detay": detay[:120]})

    def llm_kaydet(self, asama: str, model: str, kullanim: dict,
                   arac_cagrisi: int = 0) -> float:
        """OpenAI usage sozlugunden gercek maliyeti hesapla ve kaydet."""
        gir, cik = BIRIM_FIYAT.get(model, (0.0, 0.0))
        gi = float(kullanim.get("input_tokens") or kullanim.get("prompt_tokens") or 0)
        co = float(kullanim.get("output_tokens") or kullanim.get("completion_tokens") or 0)
        usd = gi / 1_000_000 * gir + co / 1_000_000 * cik
        usd += arac_cagrisi * ARAC_FIYAT["web_search"]
        self.kaydet(asama, model, usd,
                    f"{int(gi)} giris + {int(co)} cikis"
                    + (f" + {arac_cagrisi} arama" if arac_cagrisi else ""))
        return usd

    def rapor(self) -> dict:
        asama_toplam: dict = {}
        for k in self.kayitlar:
            asama_toplam[k["asama"]] = round(
                asama_toplam.get(k["asama"], 0.0) + k["usd"], 6)
        return {"is": self.is_adi, "toplam_usd": self.toplam,
                "tavan_usd": self.tavan, "kalan_usd": self.kalan(),
                "asama_bazinda": asama_toplam, "kalem_sayisi": len(self.kayitlar)}

    def yaz(self, yol: str) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(yol)) or ".", exist_ok=True)
        with open(yol, "w", encoding="utf-8") as f:
            json.dump({**self.rapor(), "kayitlar": self.kayitlar},
                      f, ensure_ascii=False, indent=1)
