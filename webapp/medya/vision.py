"""VISION PUANLAYICI — enjekte edilebilir arayuz + deterministik yedek.

Kullanici istegi: "vision scorer icin enjekte edilebilir arayuz olustur; API
anahtari olmadan deterministik fallback calissin."

Neden ikisi birden:
  - Gercek gorsel dogrulama (11 Agu'da olculdu, isini yapiyor: "Signage in
    English, lacks Japanese script" diyerek yanlis klibi reddetti) ama PARA
    harciyor ve ag ister.
  - Testler ve anahtarsiz kosular icin DETERMINISTIK bir yedek sart. Yedek
    "her seye 50 ver" demiyor — metadata'dan cikarilabilen sinyalleri
    kullaniyor, boylece siralama tamamen kor kalmiyor.

Arayuz sozlesmesi:  puanlayici(aday, varliklar, amac) -> (puan_0_100, gerekce)
"""
from __future__ import annotations

import re
from typing import Callable, Optional

# Metadata'dan "yanlis yer" sinyali: baska bir ulke/kultur acikca gecerse
KULTUR_ISARETI = {
    "japan": ("japan", "japanese", "tokyo", "kyoto", "osaka", "shinjuku",
              "shibuya", "nippon", "okinawa"),
    "korea": ("korea", "korean", "seoul", "busan"),
    "china": ("china", "chinese", "beijing", "shanghai"),
    "usa": ("usa", "america", "american", "new york", "california", "texas"),
    "uk": ("britain", "british", "england", "london", "scotland"),
    "france": ("france", "french", "paris"),
    "germany": ("germany", "german", "berlin", "munich"),
    "italy": ("italy", "italian", "rome", "venice"),
    "india": ("india", "indian", "delhi", "mumbai"),
    "brazil": ("brazil", "brazilian", "rio"),
    "turkey": ("turkey", "turkish", "istanbul", "ankara"),
}

# Jenerik reklam stogu isaretleri (11 Agu olcumu: "businessmen in a meeting"
# tam bu havuzdan gelip Tokyo belgeselini bozdu)
JENERIK = re.compile(
    r"\b(businessman|businessmen|businesswoman|corporate|teamwork|startup|"
    r"coworking|handshake|mockup|isolated|white background|studio shot|"
    r"model posing|smiling family|happy family|lifestyle|presentation|"
    r"brainstorming|office meeting|copy space|advertisement)\b", re.I)


def deterministik_puanlayici(aday, varliklar: dict, amac: str) -> tuple[float, str]:
    """Anahtarsiz yedek: metadata'dan cikarilabilen sinyallerle puan.

    ⚠ Bu GORSELE BAKMIYOR. Adi "vision" ama gercekte metadata sezgisi;
    isim boyle cunku siralama ayni yuvayi kullaniyor. Gercek vision
    devredeyse bu fonksiyon hic cagrilmaz. Karistirmamak icin gerekce
    metninde acikca "metadata" yaziyor.
    """
    metin = f"{aday.baslik} {aday.aciklama} {aday.konum} {aday.sorgu}".lower()
    puan, notlar = 55.0, []

    m = JENERIK.search(metin)
    if m:
        puan -= 30.0
        notlar.append(f"jenerik stok isareti: {m.group(0)}")

    # Beklenen ulke(ler)
    beklenen = set()
    for y in (varliklar.get("yerler") or []):
        yl = str(y).lower()
        for ulke, adlar in KULTUR_ISARETI.items():
            if any(a in yl for a in adlar):
                beklenen.add(ulke)
    if beklenen:
        gecen = {u for u, adlar in KULTUR_ISARETI.items()
                 if any(a in metin for a in adlar)}
        if gecen & beklenen:
            puan += 30.0
            notlar.append(f"beklenen kultur dogrulandi: {sorted(gecen & beklenen)}")
        elif gecen - beklenen:
            puan -= 35.0
            notlar.append(f"YANLIS kultur isareti: {sorted(gecen - beklenen)}")
        else:
            notlar.append("kultur isareti yok (notr)")

    if aday.tur == "video" and (aday.sure_sn or 0) >= 4:
        puan += 5.0
    if (aday.genislik or 0) >= 1920:
        puan += 5.0

    return round(max(0.0, min(100.0, puan)), 1), "metadata: " + "; ".join(
        notlar or ["belirgin sinyal yok"])


def olustur_puanlayici(gercek: Optional[Callable] = None,
                       anahtar_var: bool = False) -> Callable:
    """Kullanilacak puanlayiciyi sec.

    `gercek` verilmisse (ve anahtar varsa) o kullanilir; hata verirse
    deterministik yedege DUSER — tek bir vision hatasi kosuyu durdurmaz.
    """
    if gercek is None or not anahtar_var:
        return deterministik_puanlayici

    def sarmalayici(aday, varliklar, amac):
        try:
            sonuc = gercek(aday, varliklar, amac)
            if (isinstance(sonuc, (list, tuple)) and len(sonuc) == 2
                    and isinstance(sonuc[0], (int, float))):
                return float(sonuc[0]), str(sonuc[1])
            return deterministik_puanlayici(aday, varliklar, amac)
        except Exception as e:
            p, g = deterministik_puanlayici(aday, varliklar, amac)
            return p, f"{g} | gercek vision basarisiz: {str(e)[:60]}"

    return sarmalayici
