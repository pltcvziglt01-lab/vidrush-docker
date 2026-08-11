"""CELISKI COZUMU — ayni olgu icin farkli kaynaklar farkli deger veriyorsa ne olur.

Kullanicinin kurali net: "Celiskide birincil ve daha guncel kaynaga oncelik ver.
Cozulemeyen iddiayi senaryoya kesin bilgi olarak sokma."

Bu modul KARAR VERIR ama KESINLIK UYDURMAZ. Iki guclu kaynak farkli sayi
veriyorsa ve aralarinda net bir ustunluk yoksa sonuc "cozulmedi" olur ve iddia
senaryoya giremez. Bu, sistemin en onemli durustluk kapisi: yanlis bir rakami
"kaynakli" diye yayinlamak, hic rakam vermemekten cok daha kotudur.

LLM kullanmiyor — karar tamamen kaynak metadata'sindan (tur, birincillik,
tarih) turetiliyor, yani deterministik ve ucretsiz.
"""
from __future__ import annotations

import re
from typing import Optional

from . import source_ranker

# Iki degerin "ayni" sayilmasi icin izin verilen sapma.
# Neden var: kaynaklar yuvarlar. "76.941" ve "yaklasik 77 bin" celiski DEGILDIR.
# ⚠ %2 COK GEVSEKTI (test yakaladi): 76.941 ile 78.000 ayni sayilirdi — belgeselde
# 1.000 kisilik fark onemlidir. %0.5 hem yuvarlamayi ("yaklasik 77 bin") tolere
# eder hem gercek farki yakalar.
GORECELI_TOLERANS = 0.005     # %0.5
MUTLAK_TOLERANS = 1.0

# Bir kaynagi digerine tercih etmek icin gereken minimum puan farki.
# Bunun altinda "hangisi dogru" demeye hakkimiz yok -> cozulmedi.
BELIRLEYICI_PUAN_FARKI = 12.0


def sayi_coz(metin: str) -> Optional[float]:
    """Metinden ilk anlamli sayiyi cikar. "76,941" -> 76941.0, "%3.2" -> 3.2"""
    d = str(metin or "").replace(" ", " ")
    m = re.search(r"-?\d[\d.,]*", d)
    if not m:
        return None
    ham = m.group(0).rstrip(".,")
    # 1.234.567 (nokta binlik) vs 1234.56 (nokta ondalik) ayrimi
    if ham.count(",") and ham.count("."):
        # son gelen ayirici ondalik kabul edilir
        if ham.rfind(",") > ham.rfind("."):
            ham = ham.replace(".", "").replace(",", ".")
        else:
            ham = ham.replace(",", "")
    elif ham.count(","):
        # 76,941 -> binlik ; 3,2 -> ondalik (virgulden sonra 1-2 hane ve tek virgul)
        parcalar = ham.split(",")
        ham = (ham.replace(",", ".") if len(parcalar) == 2 and len(parcalar[1]) <= 2
               else ham.replace(",", ""))
    elif ham.count(".") > 1:
        ham = ham.replace(".", "")
    try:
        return float(ham)
    except ValueError:
        return None


def _yakin(sa: float, sb: float) -> bool:
    if abs(sa - sb) <= MUTLAK_TOLERANS:
        return True
    buyuk = max(abs(sa), abs(sb)) or 1.0
    return abs(sa - sb) / buyuk <= GORECELI_TOLERANS


def ayni_deger_mi(a: str, b: str) -> bool:
    """Iki degerin pratikte ayni olup olmadigi (yuvarlama toleransli).

    NOKTA/VIRGUL BELIRSIZLIGI: "76.941" Ingilizce metinde ondalik, Almanca/Turkce
    metinde binliktir ve hangisi oldugunu METINDEN bilemeyiz. Bu yuzden iki okuma
    da denenir; biri tutuyorsa AYNI kabul edilir. Yon bilincli: yanlis "farkli"
    demek celiski uydurup dogru iddiayi dusurur, yanlis "ayni" demekten daha zararli
    degil — cunku deger yine EN GUCLU kaynaktan aliniyor."""
    sa, sb = sayi_coz(a), sayi_coz(b)
    if sa is None or sb is None:
        return str(a or "").strip().lower() == str(b or "").strip().lower()
    if _yakin(sa, sb):
        return True
    for x, y in ((sa, sb), (sb, sa)):
        # "76.941" ondalik okunduysa binlik okumasini da dene
        if 0 < x < 1000 and abs(x - int(x)) > 0:
            binlik = float(str(x).replace(".", ""))
            if _yakin(binlik, y):
                return True
    return False


def coz(adaylar: list, bugun: str = "") -> dict:
    """Ayni olgu icin gelen adaylardan birini sec ya da cozulmedi de.

    adaylar: [{"deger": "76941", "url":.., "baslik":.., "tur":.., "yayin_tarihi":..}]
    Doner: {"durum", "secilen", "gerekce", "gruplar", "kazanan_puan", "rakip_puan"}
      durum: "tek" | "uyumlu" | "cozuldu" | "cozulmedi"
    """
    temiz = [a for a in (adaylar or []) if str(a.get("deger", "")).strip()]
    if not temiz:
        return {"durum": "cozulmedi", "secilen": None,
                "gerekce": "deger iceren aday yok", "gruplar": []}

    puanli = source_ranker.sirala(temiz, bugun=bugun)

    # 1) Ayni degeri veren adaylari grupla
    gruplar: list = []
    for a in puanli:
        for g in gruplar:
            if ayni_deger_mi(g["deger"], a["deger"]):
                g["adaylar"].append(a)
                break
        else:
            gruplar.append({"deger": a["deger"], "adaylar": [a]})

    if len(gruplar) == 1:
        g = gruplar[0]
        bagimsiz = len({source_ranker.alan_adi(x.get("url", "")) for x in g["adaylar"]}
                       - {""})
        return {"durum": "uyumlu" if bagimsiz >= 2 else "tek",
                "secilen": g["adaylar"][0],
                "gerekce": (f"{bagimsiz} bagimsiz kaynak ayni degeri veriyor"
                            if bagimsiz >= 2 else "tek kaynak"),
                "gruplar": [{"deger": g["deger"], "kaynak": len(g["adaylar"])}]}

    # 2) Celiski var. Grup gucu = grubun EN GUCLU kaynagi + bagimsizlik primi
    def grup_gucu(g: dict) -> float:
        en = max(x["puan"] for x in g["adaylar"])
        bagimsiz = len({source_ranker.alan_adi(x.get("url", "")) for x in g["adaylar"]}
                       - {""})
        return en + (4.0 if bagimsiz >= 2 else 0.0)

    sirali = sorted(gruplar, key=grup_gucu, reverse=True)
    kazanan, rakip = sirali[0], sirali[1]
    kg, rg = grup_gucu(kazanan), grup_gucu(rakip)

    ozet = [{"deger": g["deger"], "kaynak": len(g["adaylar"]),
             "guc": round(grup_gucu(g), 1)} for g in sirali]

    if kg - rg < BELIRLEYICI_PUAN_FARKI:
        # ⚠ BILINCLI SECIM: burada "en yuksek puanli kazandi" demek KOLAY olurdu.
        # Ama iki esit guclu kaynak farkli rakam veriyorsa hangisinin dogru
        # oldugunu BILMIYORUZ. Senaryoya kesin bilgi olarak sokmak = izleyiciye
        # yanlis bilgi vermek. Cozulmedi diyoruz ve iddia dusuyor.
        return {"durum": "cozulmedi", "secilen": None,
                "gerekce": (f"celiskili degerler ve belirleyici ustunluk yok "
                            f"(guc farki {kg - rg:.1f} < {BELIRLEYICI_PUAN_FARKI})"),
                "gruplar": ozet, "kazanan_puan": round(kg, 1), "rakip_puan": round(rg, 1)}

    en_iyi = max(kazanan["adaylar"], key=lambda x: (x["puan"], x["birincil"]))
    neden = []
    if en_iyi.get("birincil"):
        neden.append("birincil kaynak")
    if en_iyi.get("tur"):
        neden.append(en_iyi["tur"])
    if en_iyi.get("yil"):
        neden.append(str(en_iyi["yil"]))
    return {"durum": "cozuldu", "secilen": en_iyi,
            "gerekce": "belirgin ustunluk: " + ", ".join(neden),
            "gruplar": ozet, "kazanan_puan": round(kg, 1), "rakip_puan": round(rg, 1)}
