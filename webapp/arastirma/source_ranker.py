"""KAYNAK PUANLAMA — bir URL'nin ne kadar guvenilir oldugunu belirler.

Neden kod, neden LLM'e sormuyoruz: kaynak turu URL'den DETERMINISTIK olarak
cikarilabilir (nhk.or.jp resmi yayinci, stat.go.jp istatistik ofisi, reddit.com
forum). LLM'e sormak hem para harcar hem her cagrida farkli cevap verir.
Belirsiz kalan alan adlari icin ipucu tabanli tahmin var, ve tahmin ASLA
"resmi-kurum" gibi yuksek guvene cikmaz.

Puanlama kullanimi: fact_checker celiskide HANGI kaynaga uyacagini buradan
ogrenir (birincil ve daha guncel kazanir), researcher zayif kaynaklari eler.
"""
from __future__ import annotations

import re

from .manifests import KAYNAK_TURLERI, ZAYIF_TURLER

# ── Alan adi sonekleri: en guclu sinyal ──
# Bu sonekler dunyanin cogunda kurumsal/akademik tahsis gerektiriyor.
KURUM_SONEK = (".gov", ".gov.uk", ".go.jp", ".gc.ca", ".gov.au", ".govt.nz",
               ".gob.mx", ".gov.br", ".gov.tr", ".europa.eu", ".un.org",
               ".who.int", ".oecd.org", ".imf.org", ".worldbank.org")
AKADEMIK_SONEK = (".edu", ".ac.uk", ".ac.jp", ".edu.au", ".ac.nz", ".edu.tr",
                  ".uni-", ".ac.kr", ".edu.cn")
MUZE_ARSIV_SONEK = (".museum",)

# ── Ada gore bilinen kaynaklar ──
BUYUK_HABER = frozenset({
    "reuters.com", "apnews.com", "bbc.com", "bbc.co.uk", "nhk.or.jp", "npr.org",
    "nytimes.com", "washingtonpost.com", "wsj.com", "ft.com", "economist.com",
    "theguardian.com", "bloomberg.com", "afp.com", "dw.com", "aljazeera.com",
    "japantimes.co.jp", "asahi.com", "mainichi.jp", "yomiuri.co.jp", "kyodonews.net",
    "lemonde.fr", "spiegel.de", "elpais.com", "cbc.ca", "abc.net.au",
    # 11 Agu 2026 canli kuru testinde eklendi: nippon.com Japonya'nin kamu
    # yararina calisan yayin kurulusu (Nippon Communications Foundation) ama
    # "bilinmiyor" cikiyordu ve SADECE bu yuzden 8 iddia tek-kaynak kaliyordu.
    "nippon.com", "japan-forward.com", "nikkei.com", "jiji.com", "sankei.com",
    "channelnewsasia.com", "straitstimes.com", "scmp.com", "koreaherald.com",
    "thehindu.com", "indianexpress.com", "haaretz.com", "trtworld.com",
    "anadoluajansi.com.tr", "aa.com.tr", "hurriyet.com.tr", "milliyet.com.tr",
})
# Arastirma kurulusu / dusunce kurulusu: haber degil, akademige yakin
ARASTIRMA_KURULUSU = frozenset({
    "nli-research.co.jp", "pewresearch.org", "brookings.edu", "rand.org",
    "chathamhouse.org", "csis.org", "carnegieendowment.org", "iiss.org",
    "statista.com", "ourworldindata.org", "jri.co.jp", "dir.co.jp",
})
MUZE_ARSIV = frozenset({
    "loc.gov", "archives.gov", "nationalarchives.gov.uk", "europeana.eu",
    "britishmuseum.org", "si.edu", "smithsonianmag.com", "rijksmuseum.nl",
    "metmuseum.org", "getty.edu", "bnf.fr", "dpla.org", "archive.org",
    "commons.wikimedia.org", "ndl.go.jp",
})
AKADEMIK_AD = frozenset({
    "nature.com", "science.org", "sciencedirect.com", "springer.com", "wiley.com",
    "jstor.org", "pubmed.ncbi.nlm.nih.gov", "ncbi.nlm.nih.gov", "arxiv.org",
    "doi.org", "plos.org", "cambridge.org", "oup.com", "tandfonline.com",
    "researchgate.net", "ssrn.com", "jstage.jst.go.jp",
})
ANSIKLOPEDI = frozenset({"wikipedia.org", "britannica.com", "wikiwand.com",
                         "citizendium.org", "everipedia.org"})
FORUM = frozenset({"reddit.com", "quora.com", "x.com", "twitter.com", "facebook.com",
                   "medium.com", "substack.com", "tiktok.com", "youtube.com",
                   "stackexchange.com", "stackoverflow.com", "linkedin.com"})
KURULUS_IPUCU = (".org",)

# Tur -> temel guven puani (0-100). fact_checker bunu esik olarak kullanir.
TUR_PUANI = {
    "resmi-kurum": 92,
    "birincil-belge": 90,
    "akademik": 86,
    "muze-arsiv": 82,
    "haber-buyuk": 74,
    "kurulus": 62,
    "haber-yerel": 52,
    "ansiklopedi": 40,      # YONLENDIRICI: kaynagina git, kendisini kanit sayma
    "blog": 26,
    "forum": 18,
    "bilinmiyor": 20,
}


def alan_adi(url: str) -> str:
    m = re.match(r"https?://([^/?#]+)", str(url or "").strip(), re.I)
    if not m:
        return ""
    return m.group(1).lower().removeprefix("www.")


def kaynak_turu(url: str, baslik: str = "") -> str:
    """URL'den kaynak turunu belirle. Emin olunamazsa "bilinmiyor" — asla
    iyimser tahmin yapmaz, cunku yanlis "resmi-kurum" etiketi tek kaynakli bir
    iddianin dogrulanmis sayilmasina yol acar."""
    alan = alan_adi(url)
    if not alan:
        return "bilinmiyor"
    # ⚠ ACIK AD LISTELERI SONEK KURALLARINDAN ONCE. loc.gov (Library of Congress)
    # hem ".gov" hem arsiv; test yakaladi: sonek once bakilinca "resmi-kurum"
    # cikiyordu ve medya arayan katman onu arsiv saglayicisi saymiyordu.
    if alan in MUZE_ARSIV or any(alan.endswith("." + a) for a in MUZE_ARSIV) \
            or any(alan.endswith(s) for s in MUZE_ARSIV_SONEK):
        return "muze-arsiv"
    if alan in AKADEMIK_AD or any(alan.endswith("." + a) for a in AKADEMIK_AD):
        return "akademik"
    if alan in ARASTIRMA_KURULUSU or any(alan.endswith("." + a)
                                        for a in ARASTIRMA_KURULUSU):
        return "kurulus"
    if any(alan.endswith(s) or f"{s}." in alan for s in KURUM_SONEK):
        return "resmi-kurum"
    if any(alan.endswith(s) or s in alan for s in AKADEMIK_SONEK):
        return "akademik"
    if any(alan == a or alan.endswith("." + a) for a in ANSIKLOPEDI):
        return "ansiklopedi"
    if any(alan == a or alan.endswith("." + a) for a in FORUM):
        return "forum"
    if alan in BUYUK_HABER or any(alan.endswith("." + a) for a in BUYUK_HABER):
        return "haber-buyuk"
    if any(alan.endswith(s) for s in KURULUS_IPUCU):
        return "kurulus"
    # Haber gorunumlu ama taninmayan: yerel haber say (52 puan — tek basina yetmez)
    if re.search(r"(news|haber|times|post|herald|gazette|tribune|journal|press)", alan):
        return "haber-yerel"
    return "bilinmiyor"


def birincil_mi(url: str, tur: str = "", baslik: str = "") -> bool:
    """Birincil kaynak = olayin/verinin KENDISINI yayinlayan taraf.
    Resmi istatistik tablosu birincildir; onu haberlestiren gazete ikincildir."""
    if tur in ("resmi-kurum", "birincil-belge"):
        return True
    u = str(url or "").lower()
    b = str(baslik or "").lower()
    if tur == "akademik" and re.search(r"(doi\.org|arxiv|/article/|/full/|pubmed)", u):
        return True
    if re.search(r"(annual-report|white-?paper|statistics|dataset|census|"
                 r"press-?release|official|gazette|ruling|judgment)", u + " " + b):
        return True
    return False


def puan(url: str, baslik: str = "", tur: str = "", yayin_tarihi: str = "",
         bugun: str = "") -> dict:
    """Kaynagin degerlendirmesi: {tur, puan, birincil, zayif, guncellik_yili}.

    Guncellik puanı DUSURUR ama tur puanini ezmez: 20 yillik resmi istatistik,
    dunku bir blogtan hala guvenilirdir.
    """
    t = tur if tur in KAYNAK_TURLERI and tur != "bilinmiyor" else kaynak_turu(url, baslik)
    p = float(TUR_PUANI.get(t, 20))
    bir = birincil_mi(url, t, baslik)
    if bir:
        p += 6
    yil = _yil(yayin_tarihi)
    bugun_yil = _yil(bugun) or 0
    if yil and bugun_yil:
        yas = max(0, bugun_yil - yil)
        # 0-2 yil: ceza yok. Sonra yilda 1.5 puan, tavan 18.
        p -= min(18.0, max(0.0, (yas - 2) * 1.5))
    elif not yil:
        p -= 4.0                       # tarihsiz kaynak: izlenebilirlik zayif
    return {"tur": t, "puan": round(max(0.0, min(100.0, p)), 1),
            "birincil": bir, "zayif": t in ZAYIF_TURLER, "yil": yil}


def _yil(tarih: str) -> int:
    m = re.search(r"(19|20)\d{2}", str(tarih or ""))
    return int(m.group(0)) if m else 0


def sirala(kaynaklar: list, bugun: str = "") -> list:
    """Kaynak listesini guvenden dusuge sirala. Girdi: [{url, baslik, ...}]."""
    olcut = []
    for k in kaynaklar:
        d = puan(k.get("url", ""), k.get("baslik", ""), k.get("tur", ""),
                 k.get("yayin_tarihi", ""), bugun)
        olcut.append({**k, **d})
    return sorted(olcut, key=lambda x: (-x["puan"], not x["birincil"]))
