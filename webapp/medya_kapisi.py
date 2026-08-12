#!/usr/bin/env python3
"""MEDYA DOGRULUK KAPISI — biyom/donem celiskisi ve alaka kapisi.

⚠ NEDEN VAR — CANLI PILOTTA OLCULDU (12 Agu 2026, Shackleton isi
`job_1786491521724_fazh15_102297`):

    sorgu   : "South Georgia island approach boat"
    secilen : "aerial view of boat approaching TROPICAL shore"   (Pexels)
    ekranda : "GUNEY GEORGIA / SAHIL" alt bandiyla gosterildi

Guney Georgia sub-Antarktik bir ada; ekrana tropik sahil geldi.

KOK NEDEN: `kaynak.py`'nin yer kapisi `YER_TAKMA_AD` tablosuna bagli ve o
tablo 19 ULKE iceriyor. "South Georgia", "Antarctica", "Elephant Island",
"Patagonia" gibi yerler tabloda YOK ->
    `_sorgu_yer_terimleri()` -> []
    `_etkin_yer()`           -> []  (video baglami da bos, cunku metin Turkce
                                     ve "Guney Georgia" da tabloda yok)
    `_yer_dogru_mu(h, [])`   -> True  (yer iddiasi yok -> KAPI YOK)
Yani tablonun disindaki HER YER icin hicbir kapi calismiyordu.

BU MODULUN COZUMU: ulke tablosundan BAGIMSIZ calisan bir **biyom celiskisi**
kapisi. Sahnenin ima ettigi iklim kusagi ile adayin metadata'sindaki iklim
isaretleri CELISIYORSA aday reddedilir. "Guney Georgia" -> kutup/soguk kusak;
"tropical shore" -> tropik kusak; celiski -> RED.

⚠ TASARIM KURALLARI
1. KAPI, PUAN DEGIL. Celiski varsa aday DUSER. Yumusak puanlama Faz E'de
   olculdu ve alakasiz ogeler esigi geciyordu.
2. SESSIZ DUSUS YOK. Her red bir gerekce dizesi dondurur; cagiran bunu
   loglar ve ise `dususler` olarak yazar.
3. EMIN DEGILSEN GECIR. Sahnenin biyomu cikarilamiyorsa kapi UYGULANMAZ.
   Yanlis pozitif (dogru klibi atmak) da bir kalite kaybidir.
4. SAHTE KONUM ETIKETI YASAK. Kapi bir klibi reddettiginde cagiran ya baska
   aday dener ya da sahneyi kapsam bosluğu isaretler; "yaklasik dogru" bir
   klibi dogru yer etiketiyle GOSTERMEZ.
"""
from __future__ import annotations

import os
import re

# Kapi acik mi (acil durumda tek env ile kapatilir)
ACIK = os.environ.get("MEDYA_KAPISI", "1").lower() not in ("0", "false", "")

# ─────────────────────────── BIYOM SOZLUGU ───────────────────────────
# Anahtar: biyom kimligi. Deger: o biyomu ELE VEREN metin isaretleri.
# ⚠ Isaretler DAR tutuldu: "ice" tek basina "ice cream"e de uyar, bu yuzden
# kelime siniriyla ve cok anlamli olanlar disarida birakilarak eslenir.
BIYOM_ISARETI = {
    "kutup": (
        "antarctic", "antarctica", "arctic", "polar", "iceberg", "ice floe",
        "ice sheet", "glacier", "glacial", "pack ice", "sea ice", "tundra",
        "snowfield", "ice cap", "icebreaker", "permafrost", "crevasse",
        "penguin", "polar bear", "walrus", "igloo", "blizzard",
        "south georgia", "elephant island", "svalbard", "greenland",
        "patagonia", "tierra del fuego", "siberia", "yukon", "lapland",
    ),
    "tropik": (
        "tropical", "tropics", "palm tree", "palm trees", "coconut",
        "jungle", "rainforest", "lagoon", "coral reef", "atoll",
        "turquoise water", "turquoise sea", "caribbean", "maldives",
        "bali", "hawaii", "tahiti", "bahamas", "mangrove", "monsoon",
        "banana tree", "hibiscus", "toucan", "parrot", "flamingo",
    ),
    "col": (
        "desert", "sahara", "dune", "dunes", "sand dune", "arid",
        "oasis", "camel", "cactus", "badlands", "salt flat", "mesa",
    ),
    "kent": (
        "skyscraper", "downtown", "city street", "traffic jam", "subway",
        "metro station", "highway", "shopping mall", "office building",
    ),
}

# CELISKI TABLOSU: hangi biyom hangisiyle AYNI KAREDE olamaz.
# ⚠ Simetrik. "kent" bilerek DISARIDA: kutup arastirma istasyonu da,
# tropik ada kasabasi da yerlesim icerebilir — kent celiski uretmez.
CELISEN = {
    "kutup": ("tropik", "col"),
    "tropik": ("kutup", "col"),
    "col": ("kutup", "tropik"),
}

# ─────────────────────────── DONEM SOZLUGU ───────────────────────────
# Modern teknoloji isaretleri: tarihsel (pre-1950) bir sahnede gorunurse
# donem celiskisi olur.
MODERN_ISARET = (
    "smartphone", "iphone", "android phone", "laptop", "tablet computer",
    "drone shot of city", "wind turbine", "solar panel", "electric car",
    "gps", "modern office", "computer screen", "led screen", "selfie",
    "sneakers", "hoodie", "plastic bottle", "helicopter tour",
)
# Tarihsel donem: sahne metninde bu yillar/kaliplar varsa "tarihsel" sayilir
_YIL = re.compile(r"\b(1[0-8]\d{2}|19[0-4]\d)\b")
_ESKI_ISARET = ("vintage", "historic", "archival", "black and white",
                "sepia", "expedition of 19", "wooden ship", "sailing ship",
                "steam ship", "schooner")

_KELIME_SINIRI = r"(?<![0-9a-zà-ÿğüşıöç])%s(?![0-9a-zà-ÿğüşıöç])"


def _gecer_mi(isaret: str, metin: str) -> bool:
    """Kelime siniriyla ara. Alt dizi eslemesi 'ice'i 'service' icinde bulur."""
    return re.search(_KELIME_SINIRI % re.escape(isaret), metin) is not None


def biyom_bul(metin: str) -> set:
    """Metnin ele verdigi biyom(lar). Hicbiri yoksa bos kume."""
    d = " " + str(metin or "").lower() + " "
    return {b for b, isaretler in BIYOM_ISARETI.items()
            if any(_gecer_mi(i, d) for i in isaretler)}


def tarihsel_mi(metin: str) -> bool:
    """Sahne tarihsel bir doneme mi ait (pre-1950 yil ya da donem isareti)."""
    d = " " + str(metin or "").lower() + " "
    if _YIL.search(d):
        return True
    return any(_gecer_mi(i, d) for i in _ESKI_ISARET)


def modern_isaretler(metin: str) -> list:
    d = " " + str(metin or "").lower() + " "
    return [i for i in MODERN_ISARET if _gecer_mi(i, d)]


def biyom_kapisi(sahne_metni: str, aday_metni: str,
                 video_baglami: str = "") -> tuple:
    """(ok, gerekce). Sahne ile aday iklim kusagi celisiyorsa ok=False.

    `sahne_metni`   : sahnenin sorgusu/anlatimi (ne aranıyor)
    `aday_metni`    : saglayici metadata'si (baslik + aciklama)
    `video_baglami` : tum videonun konusu — sahne sorgusu biyom vermezse
                      buradan turetilir (Shackleton isinde tam bu gerekti:
                      sorgu "South Georgia island approach boat" biyom veriyor
                      ama vermeseydi konu metni "Antarktika/buz" diyordu)

    ⚠ EMIN DEGILSEN GECIR: sahnenin ya da adayin biyomu cikmiyorsa kapi
    UYGULANMAZ ve (True, "...") doner.
    """
    if not ACIK:
        return True, "kapi kapali (MEDYA_KAPISI=0)"
    sahne_b = biyom_bul(sahne_metni) or biyom_bul(video_baglami)
    if not sahne_b:
        return True, "sahnenin biyomu cikarilamadi — kapi uygulanmadi"
    aday_b = biyom_bul(aday_metni)
    if not aday_b:
        return True, "adayin biyomu cikarilamadi — kapi uygulanmadi"

    for s in sahne_b:
        celisen = set(CELISEN.get(s, ()))
        ortak = celisen & aday_b
        if ortak and s not in aday_b:
            # ⚠ `s not in aday_b`: aday HEM kutup HEM tropik isareti tasiyorsa
            # (or. "from tropics to the antarctic") celiski saymayiz.
            return False, (f"BIYOM CELISKISI: sahne '{s}' kusagi, aday "
                           f"'{'/'.join(sorted(ortak))}' kusagi")
    return True, f"biyom uyumlu (sahne={sorted(sahne_b)}, aday={sorted(aday_b)})"


def donem_kapisi(sahne_metni: str, aday_metni: str,
                 video_baglami: str = "") -> tuple:
    """(ok, gerekce). Tarihsel sahnede MODERN teknoloji isareti varsa reddet."""
    if not ACIK:
        return True, "kapi kapali"
    if not (tarihsel_mi(sahne_metni) or tarihsel_mi(video_baglami)):
        return True, "sahne tarihsel degil — donem kapisi uygulanmadi"
    modern = modern_isaretler(aday_metni)
    if modern:
        return False, f"DONEM CELISKISI: tarihsel sahnede modern isaret {modern[:3]}"
    return True, "donem uyumlu"


def kapi(sahne_metni: str, aday_metni: str, video_baglami: str = "") -> tuple:
    """Tum kapilari sirayla uygula. Ilk red kazanir. (ok, gerekce)."""
    for fn in (biyom_kapisi, donem_kapisi):
        ok, gerekce = fn(sahne_metni, aday_metni, video_baglami)
        if not ok:
            return False, gerekce
    return True, "kapilar gecildi"


# ─────────────────── CESITLILIK OLCUMU (uydurma yok) ───────────────────

def cesitlilik_olc(kayitlar: list) -> dict:
    """Kullanilan kliplerin GERCEK cesitliligini olc.

    `kayitlar`: [{"saglayici": str, "kimlik": str, "baslik": str}, ...]
    Uydurma puan URETMEZ — yalnizca sayar.
    """
    if not kayitlar:
        return {"klip": 0, "tekil_klip": 0, "tekrar_orani": 0.0,
                "saglayici_dagilimi": {}, "en_baskin_saglayici_orani": 0.0}
    kimlikler = [str(k.get("kimlik") or k.get("baslik") or "") for k in kayitlar]
    tekil = len(set(x for x in kimlikler if x))
    dagilim: dict = {}
    for k in kayitlar:
        s = str(k.get("saglayici") or "bilinmiyor")
        dagilim[s] = dagilim.get(s, 0) + 1
    baskin = max(dagilim.values()) / len(kayitlar) if dagilim else 0.0
    return {
        "klip": len(kayitlar),
        "tekil_klip": tekil,
        "tekrar_orani": round(1 - (tekil / len(kayitlar)), 3) if kayitlar else 0.0,
        "saglayici_dagilimi": dagilim,
        "en_baskin_saglayici_orani": round(baskin, 3),
    }
