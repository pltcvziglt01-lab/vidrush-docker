"""SORGU PLANLAYICI — iddiadan arama sorgularina.

Faz A'nin ciktisi iddia metinleri. Onlari dogrudan stok aramaya vermek
11 Agu'da olculen hataya goturuyor: "Japanese apartment electric meter and
light switch" gibi bir cumle stokta karsiligi olmayan bir CEKIM tarif ediyor
ve arama alakasiz sonuc donduruyor.

Bu modul iddiadan once VARLIKLARI cikariyor (kisi, kurum, yer, tarih), sonra
SAHNE AMACINA gore sorgu varyantlari uretiyor. Ayni iddia icin:

  establishing : "tokyo apartment building exterior"
  detay        : "close up electricity meter"
  arsiv        : "1980s japan newspaper archive"
  belge        : "japanese government document scan"
  harita       : "japan map chiba prefecture"
  ortam        : "tokyo residential street evening"

Varlik cikarimi LLM'SIZ: buyuk harfli oz ad kaliplari, tarih desenleri ve
kurum sonekleri (Ministry/Agency/Bureau/University) yeterli. LLM'e her iddia
icin sormak para harcar ve deterministik olmaz — testler de kosamaz.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# Sahne amaclari ve her birinin sorgu bicimi
SAHNE_AMACLARI = ("establishing", "detay", "arsiv", "belge", "harita", "ortam", "kisi")

# Kurum adi sonekleri — bunlari iceren oz ad kurum sayilir
KURUM_ISARETI = re.compile(
    r"\b(Ministry|Agency|Bureau|Department|Office|Institute|University|College|"
    r"Foundation|Association|Commission|Council|Authority|Corporation|Company|"
    r"Police|Court|Parliament|Congress|Senate|Bank|Hospital|Museum|Library|"
    r"Bakanlig[iı]|Kurumu|Universitesi|Enstitusu)\b", re.I)

# Yer isaretleri — cografi ozel adlar icin ipucu
YER_ISARETI = re.compile(
    r"\b(City|Town|Village|District|Prefecture|Province|State|County|Region|"
    r"Island|Mountain|River|Sea|Ocean|Desert|Valley|Street|Avenue|Station|Airport|"
    r"Sehri|Ili|Ilcesi|Bolgesi)\b", re.I)

# Oz ad: buyuk harfle baslayan 1-4 kelimelik obek (cumle basi haric tutulmaya
# calisilmiyor — fazla yakalamak, az yakalamaktan iyidir; siralama filtreliyor)
OZ_AD = re.compile(r"\b([A-Z][\w'’-]+(?:\s+(?:of|de|del|van|der|the)\s+)?"
                   r"(?:\s+[A-Z][\w'’-]+){0,3})\b")

TARIH = re.compile(r"\b(1[6-9]\d{2}|20\d{2})(?:\s*[-–]\s*(1[6-9]\d{2}|20\d{2}))?\b")
ON_YIL = re.compile(r"\b(1[6-9]\d0s|20\d0s|(?:nineteen|twenty)\s+\w+)\b", re.I)

# Cumle basinda gelen ve oz ad OLMAYAN yaygin kelimeler
YOK_SAY = {"The", "This", "That", "These", "Those", "In", "On", "At", "By", "For",
           "From", "With", "When", "While", "After", "Before", "During", "Its",
           "Their", "His", "Her", "Japan's", "According", "Under", "Between",
           "About", "Around", "Some", "Most", "Many", "Every", "Each", "One",
           "Two", "Three", "Roughly", "Nearly", "Almost", "Since", "Because"}

# Sahne amacina gore sorgu kalibi. {yer} {kurum} {kisi} {konu} {yil} doldurulur.
KALIP = {
    "establishing": ["{yer} city aerial view", "{yer} skyline", "{yer} street wide shot",
                     "{yer} landscape"],
    "detay":        ["close up {konu}", "macro {konu}", "{konu} detail"],
    "arsiv":        ["{yer} {onyil} archive footage", "{onyil} {konu} archive",
                     "historical {yer} film"],
    "belge":        ["{kurum} document scan", "official report page {konu}",
                     "newspaper page {onyil}"],
    "harita":       ["{yer} map", "map of {yer}", "{yer} location map"],
    "ortam":        ["{yer} residential street", "{yer} daily life",
                     "{yer} evening atmosphere"],
    "kisi":         ["{kisi} portrait", "{kisi} photograph"],
}


# ═══════════════════ FAZ I-5 — KONSEPT FARKINDALIGI (EK BILGI) ═══════════════════
# ⚠ NEDEN VAR (olculdu): `KALIP` ve `AMAC_DAGILIMI` tamamen BELGESEL bicimliydi.
# Bir seyahat videosu da, bir urun tanitimi da, bir ders anlatimi da AYNI
# "{yer} city aerial view / close up {konu} / {kurum} document scan" kaliplarina
# giriyordu -> farkli konseptler AYNI JENERIK STOK sonuclarini seciyordu.
#
# ⚠ GERIYE UYUMLULUK: `konsept=None` verildiginde bu blogun HICBIRI calismaz;
# `sorgu_plani()` ve `amac_ata()` eskisiyle BIREBIR ayni sonucu dondurur (testli).
#
# ⚠ BILINMEYENDE RASTGELE STOK YOK: konsept cozulemezse ya da aile tabloda
# yoksa eski belgesel davranisina DUSULUR — uydurma sorgu uretilmez.

# Taksonomi ailesi -> sahne amacina EKLENEN sorgu kaliplari.
# Var olan kaliplar SILINMEZ; aile kaliplari ONCE denenir (daha spesifik).
KONSEPT_KALIP = {
    "seyahat": {
        "establishing": ["{yer} aerial drone 4k", "{yer} scenic viewpoint",
                         "{yer} coastline aerial"],
        "ortam": ["{yer} local market street", "{yer} cafe terrace people",
                  "{yer} old town walking"],
        "detay": ["{yer} local food close up", "traditional {konu} detail"],
        "harita": ["{yer} travel route map"],
    },
    "urun": {
        "detay": ["{konu} product close up studio", "{konu} texture macro",
                  "hands using {konu}"],
        "establishing": ["{konu} product on clean background",
                         "modern studio product shot"],
        "ortam": ["customer using {konu} lifestyle", "retail store interior"],
    },
    "egitim": {
        "detay": ["{konu} diagram animation", "laboratory {konu} close up"],
        "belge": ["scientific paper {konu}", "research data chart {konu}"],
        "harita": ["{konu} infographic chart", "data visualization {konu}"],
        "establishing": ["research laboratory wide shot",
                         "university campus exterior"],
        "ortam": ["classroom lecture people", "engineer working workspace"],
    },
    "hikaye": {
        "ortam": ["{yer} empty corridor night", "moody atmosphere fog",
                  "silhouette walking alone"],
        "detay": ["hand on door handle close up", "eyes close up dim light"],
        "establishing": ["lonely house exterior dusk", "empty street night wide"],
    },
    "kultur": {
        "ortam": ["live concert crowd", "musician playing close up"],
        "detay": ["instrument strings macro", "stage lights close up"],
        "establishing": ["concert hall wide shot", "festival stage aerial"],
    },
    "yasam": {
        "ortam": ["home kitchen daily life", "morning routine sunlight"],
        "detay": ["hands preparing {konu} close up"],
        "establishing": ["modern living room interior"],
    },
    # `belgesel` KASITLI OLARAK YOK: mevcut KALIP zaten belgesel icin yazildi.
}

# Ailenin sahne amaci dagilimi. Toplamlari 1.0 olmak ZORUNDA (testli).
# ⚠ Bu dagilimlar OLCUM DEGIL, TUR KONVANSIYONUNDAN turetilmis tasarim
# kararlaridir; gercek kanal olcumuyle dogrulanmadi (bilinen sinir).
KONSEPT_AMAC_DAGILIMI = {
    # Seyahat: yer gostermek esas; belge/kisi neredeyse yok.
    "seyahat": (("establishing", 0.34), ("ortam", 0.34), ("detay", 0.20),
                ("harita", 0.08), ("arsiv", 0.04)),
    # Urun: cekim detayda; arsiv/harita/belge anlamsiz.
    "urun": (("detay", 0.46), ("ortam", 0.28), ("establishing", 0.22),
             ("kisi", 0.04)),
    # Egitim/veri: sema, belge ve detay agirlikli.
    "egitim": (("detay", 0.30), ("harita", 0.22), ("belge", 0.18),
               ("establishing", 0.16), ("ortam", 0.14)),
    # Hikaye: atmosfer ve detay; belge/harita YOK.
    "hikaye": (("ortam", 0.42), ("detay", 0.30), ("establishing", 0.24),
               ("kisi", 0.04)),
    "kultur": (("ortam", 0.38), ("detay", 0.30), ("establishing", 0.26),
               ("kisi", 0.06)),
    "yasam": (("ortam", 0.40), ("detay", 0.34), ("establishing", 0.26)),
}


def konsept_ailesi(konsept) -> str:
    """`taksonomi.siniflandir()` ciktisindan AILE adi. Cozulemezse "".

    ⚠ Bu modul `taksonomi`yi IMPORT ETMEZ (Faz B paketi bagimsiz kalsin);
    yalnizca sozluk alanlarini okur. Bilinmeyen/belirsiz -> "" -> eski yol.
    """
    try:
        if not isinstance(konsept, dict):
            return ""
        yol = str(konsept.get("yol") or "")
        if not yol or yol == "belirsiz":
            return ""
        aile = str(konsept.get("aile") or yol.split(".")[0])
        return aile if aile in KONSEPT_AMAC_DAGILIMI or aile in KONSEPT_KALIP \
            else ""
    except Exception:
        return ""


@dataclass
class Varliklar:
    kisiler: list = field(default_factory=list)
    kurumlar: list = field(default_factory=list)
    yerler: list = field(default_factory=list)
    tarihler: list = field(default_factory=list)
    onyillar: list = field(default_factory=list)
    konu_kelimeleri: list = field(default_factory=list)

    def bos_mu(self) -> bool:
        return not (self.kisiler or self.kurumlar or self.yerler
                    or self.konu_kelimeleri)


def varlik_cikar(metin: str, bilinen_yerler: list = None) -> Varliklar:
    """Iddia metninden kisi/kurum/yer/tarih cikar. LLM YOK, deterministik."""
    v = Varliklar()
    m = str(metin or "")
    for t in TARIH.finditer(m):
        for g in t.groups():
            if g and g not in v.tarihler:
                v.tarihler.append(g)
    for o in ON_YIL.finditer(m):
        d = o.group(0)
        if d not in v.onyillar:
            v.onyillar.append(d)
    # Yillardan on yil turet: 1987 -> 1980s
    for y in v.tarihler:
        try:
            d = f"{int(y) // 10 * 10}s"
            if d not in v.onyillar:
                v.onyillar.append(d)
        except ValueError:
            pass

    adaylar = []
    for m2 in OZ_AD.finditer(m):
        ad = m2.group(1).strip()
        if not ad or ad.split()[0] in YOK_SAY:
            continue
        if len(ad) < 3 or ad.isupper() and len(ad) <= 3:
            continue
        adaylar.append(ad)

    for ad in adaylar:
        if KURUM_ISARETI.search(ad):
            if ad not in v.kurumlar:
                v.kurumlar.append(ad)
        elif YER_ISARETI.search(ad):
            if ad not in v.yerler:
                v.yerler.append(ad)
        elif len(ad.split()) >= 2 and all(p[:1].isupper() for p in ad.split()):
            # Iki buyuk harfli kelime: kisi adi olma olasiligi yuksek
            if ad not in v.kisiler:
                v.kisiler.append(ad)
        else:
            if ad not in v.yerler:
                v.yerler.append(ad)          # tek kelimeli oz ad -> yer varsay

    # Arastirmadan gelen bilinen yerler (Faz A yer baglami) her zaman gecerli
    for y in (bilinen_yerler or []):
        if y and y not in v.yerler:
            v.yerler.insert(0, y)

    # YER SIRALAMASI: en SPESIFIK yer basa. "Tokyo Prefecture" ile "Japan"
    # ayni iddiada gecebilir; harita/establishing sahnesi icin spesifik olan
    # dogru secim (test yakaladi: "Japan map" yerine "Tokyo map" gerekiyordu).
    # Olcut: kelime sayisi, sonra uzunluk.
    v.yerler.sort(key=lambda y: (-len(str(y).split()), -len(str(y))))

    # Konu kelimeleri: buyuk harfle baslamayan, 4+ harfli, yaygin olmayan
    yaygin = {"that", "this", "with", "from", "have", "been", "were", "their",
              "which", "about", "there", "these", "those", "than", "then",
              "also", "into", "more", "most", "over", "some", "such", "only",
              "other", "after", "recorded", "reported", "according", "people",
              "government", "official", "number", "cases", "year", "years"}
    for k in re.findall(r"\b([a-z][a-z-]{3,})\b", m):
        if k not in yaygin and k not in v.konu_kelimeleri:
            v.konu_kelimeleri.append(k)
    v.konu_kelimeleri = v.konu_kelimeleri[:6]
    return v


def _doldur(kalip: str, v: Varliklar, konu: str) -> str:
    yer = (v.yerler[0] if v.yerler else "").strip()
    kurum = (v.kurumlar[0] if v.kurumlar else "").strip()
    kisi = (v.kisiler[0] if v.kisiler else "").strip()
    onyil = (v.onyillar[0] if v.onyillar else "").strip()
    yil = (v.tarihler[0] if v.tarihler else "").strip()
    konu_k = " ".join(v.konu_kelimeleri[:2]) or konu
    d = (kalip.replace("{yer}", yer).replace("{kurum}", kurum)
              .replace("{kisi}", kisi).replace("{onyil}", onyil)
              .replace("{yil}", yil).replace("{konu}", konu_k))
    return re.sub(r"\s+", " ", d).strip()


def sorgu_plani(iddia_metni: str, sahne_amaci: str = "establishing", *,
                konu: str = "", bilinen_yerler: list = None,
                maks: int = 4, konsept=None) -> dict:
    """Tek iddia + sahne amaci -> sorgu varyantlari.

    Doner: {"amac", "varliklar", "sorgular": [...], "gerekce": "...",
            "konsept_ailesi": "..."}

    ⚠ FAZ I-5: `konsept` verilirse (taksonomi ciktisi) ONCE ailenin kendi
    kaliplari denenir, sonra genel `KALIP`. `konsept=None` ise davranis
    ESKISIYLE BIREBIR AYNI (testli).
    """
    amac = sahne_amaci if sahne_amaci in SAHNE_AMACLARI else "establishing"
    v = varlik_cikar(iddia_metni, bilinen_yerler)
    aile = konsept_ailesi(konsept)
    # Aile kaliplari ONCE: daha spesifik olan once denenir, jenerik olan yedek.
    kaliplar = list(KONSEPT_KALIP.get(aile, {}).get(amac, [])) + list(
        KALIP.get(amac, []))
    sorgular, gorulen = [], set()
    for kalip in kaliplar:
        # Kalibin gerektirdigi varlik yoksa o kalip atlanir (bos sorgu uretmeyiz)
        if "{kisi}" in kalip and not v.kisiler:
            continue
        if "{kurum}" in kalip and not v.kurumlar:
            continue
        if "{yer}" in kalip and not v.yerler:
            continue
        if "{onyil}" in kalip and not v.onyillar:
            continue
        d = _doldur(kalip, v, konu)
        if len(d) < 4 or d in gorulen:
            continue
        gorulen.add(d)
        sorgular.append(d)
    # Hicbir kalip tutmadiysa: konu kelimeleri + yer ile yalin sorgu
    if not sorgular:
        yalin = " ".join(filter(None, [(v.yerler[0] if v.yerler else ""),
                                       " ".join(v.konu_kelimeleri[:3])])).strip()
        if len(yalin) >= 4:
            sorgular.append(yalin)
        elif konu:
            sorgular.append(str(konu)[:60])
    return {"amac": amac, "varliklar": v.__dict__.copy(),
            "sorgular": sorgular[:maks],
            "konsept_ailesi": aile,
            "gerekce": (f"{len(v.yerler)} yer, {len(v.kurumlar)} kurum, "
                        f"{len(v.kisiler)} kisi, {len(v.onyillar)} on yil"
                        + (f"; konsept ailesi '{aile}' kaliplari once denendi"
                           if aile else "; konsept yok -> genel kaliplar"))}


# Sahne amaci dagilimi: bir belgeselde her sahne "establishing" olmamali.
# OLCUM_EDIT_TAKSONOMI'deki kaynak turu dagilimindan turetildi
# (modern video %73, arsiv film %8, arsiv foto %1, 3D/animasyon %17).
AMAC_DAGILIMI = (
    ("establishing", 0.22), ("ortam", 0.24), ("detay", 0.20),
    ("arsiv", 0.14), ("belge", 0.08), ("harita", 0.07), ("kisi", 0.05),
)


def amac_ata(indeks: int, kategori: str = "", konsept=None) -> str:
    """Sahne indeksinden DETERMINISTIK sahne amaci.

    Iddia kategorisi belirleyiciyse onu kullanir (rakam -> belge/harita gibi),
    aksi halde olculen dagilimdan secer.

    ⚠ FAZ I-5: `konsept` verilirse ailenin KENDI dagilimi kullanilir — seyahatte
    belge sahnesi, urunde arsiv sahnesi aramak jenerik sonuc uretiyordu.
    `konsept=None` ise dagilim ESKISIYLE BIREBIR AYNI (testli).
    ⚠ Iddia kategorisi (alinti/cografya/isim/tarih) HER ZAMAN once gelir:
    somut sinyal, tur konvansiyonunu yener.
    """
    kat = (kategori or "").lower()
    if kat == "alinti":
        return "belge"
    if kat == "cografya":
        return "harita"
    if kat == "isim":
        return "kisi"
    if kat == "tarih":
        return "arsiv"
    aile = konsept_ailesi(konsept)
    dagilim = KONSEPT_AMAC_DAGILIMI.get(aile) or AMAC_DAGILIMI
    esik = (indeks * 37 + 11) % 100 / 100.0
    toplam = 0.0
    for ad, pay in dagilim:
        toplam += pay
        if esik < toplam:
            return ad
    # Dagilimlar 1.0'a topluyor (testli) -> buraya normalde ULASILMAZ. Yine de
    # ESKI davranis birebir korunur: varsayilan dagilimda "ortam" donerdi.
    return "ortam" if dagilim is AMAC_DAGILIMI else dagilim[-1][0]
