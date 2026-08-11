"""KAYNAK SAYFASI INDIRME ve METIN CIKARIMI.

Neden gerekli: web arama modeli atif URL'si donduruyor ama ozeti o atiftan
SAPABILIR (halusinasyon). Iddiayi kaynaga baglamak icin sayfayi GERCEKTEN
indirip iddianin orada gecip gecmedigine bakmak zorundayiz. Aksi halde
"kaynakli" dedigimiz sey sadece modelin iddiasi olur.

⚠ GUVENLIK — INDIRILEN SAYFA VERIDIR, TALIMAT DEGILDIR.
Indirilen metin bir LLM'e verilecekse yalnizca DOGRULAMA verisi olarak verilir.
Sayfada "ignore previous instructions", "sen bir asistansin, su komutu calistir"
gibi metinler bulunabilir; bunlar kullanici talimati DEGILDIR ve asla eylem
olarak yorumlanmaz. Bu modul metni ayiklar, ASLA calistirmaz veya
yorumlamaz; ayiklanan metin cagirana "veri" etiketiyle doner.

Disa bagimlilik: yalnizca `requests` (proje genelinde zaten var). HTML ayiklama
regex ile yapiliyor — harici parser eklemek deploy'a yeni bagimlilik sokar ve
deploy.sh npm/pip kurmuyor.
"""
from __future__ import annotations

import re
from typing import Callable, Optional

import requests

from .cache import Onbellek

# Metinden tamamen atilacak bloklar (icerik degil)
_ATIL = re.compile(
    r"<(script|style|noscript|svg|iframe|nav|footer|form|aside)\b[^>]*>.*?</\1>",
    re.I | re.S)
_YORUM = re.compile(r"<!--.*?-->", re.S)
_ETIKET = re.compile(r"<[^>]+>")
_BOSLUK = re.compile(r"[ \t\r\f\v]+")
_SATIR = re.compile(r"\n{3,}")

# Sayfanin yayin tarihi icin sik kullanilan isaretler
_TARIH_DESEN = [
    re.compile(r'"datePublished"\s*:\s*"([^"]{4,40})"', re.I),
    re.compile(r'property=["\']article:published_time["\']\s+content=["\']([^"\']+)', re.I),
    re.compile(r'name=["\']pubdate["\']\s+content=["\']([^"\']+)', re.I),
    re.compile(r"<time[^>]+datetime=[\"']([^\"']+)", re.I),
]
_BASLIK_DESEN = [
    re.compile(r'property=["\']og:title["\']\s+content=["\']([^"\']+)', re.I),
    re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S),
]

VARSAYILAN_BASLIK = {
    # Gercek bir tarayici gibi gorunmek gerekiyor; bazi arsivler bos UA'yi 403 ceviriyor.
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en,tr;q=0.8",
}

MAKS_BAYT = 3_000_000        # 3 MB'tan buyuk sayfayi ayiklamaya calismiyoruz
MAKS_METIN = 40_000          # LLM'e gidecek metin tavani


def html_metne(html: str) -> str:
    """HTML'den okunabilir metin. Basit ama guvenli: script/style tamamen atilir."""
    d = _YORUM.sub(" ", html or "")
    d = _ATIL.sub(" ", d)
    d = re.sub(r"<(br|/p|/div|/h[1-6]|/li|/tr)\s*/?>", "\n", d, flags=re.I)
    d = _ETIKET.sub(" ", d)
    # HTML varliklari — sik kullanilanlar
    for a, b in (("&nbsp;", " "), ("&amp;", "&"), ("&quot;", '"'), ("&#39;", "'"),
                 ("&lt;", "<"), ("&gt;", ">"), ("&mdash;", "—"), ("&ndash;", "–"),
                 ("&rsquo;", "'"), ("&lsquo;", "'"), ("&ldquo;", '"'), ("&rdquo;", '"')):
        d = d.replace(a, b)
    d = re.sub(r"&#(\d+);", lambda m: chr(int(m.group(1))) if int(m.group(1)) < 0x10000 else " ", d)
    d = _BOSLUK.sub(" ", d)
    d = _SATIR.sub("\n\n", d)
    return d.strip()


def _ilk_eslesme(desenler, html: str) -> str:
    for d in desenler:
        m = d.search(html or "")
        if m:
            return html_metne(m.group(1))[:300].strip()
    return ""


def pdf_metne(ham: bytes) -> str:
    """PDF'ten metin — SAF PYTHON (zlib stdlib'de).

    NEDEN ELDE YAZILDI: canli konteynerde pdftotext/pypdf YOK ve kurmak calisan
    sistemi degistirmek olur (kullanici onayi gerekir). Bu cikarici FlateDecode
    ile sikistirilmis metin akislarini cozuyor — Bati dillerindeki cogu resmi
    PDF'te ise yariyor.

    ⚠ SINIR: CID/gomulu font kullanan PDF'lerde (Japon bakanlik yayinlarinin
    cogu boyle) cikan metin OKUNAMAZ olur. O durumda bos donuyoruz ve iddia
    "dogrulanamadi" kaliyor — yanlis bir metinle "dogrulandi" demekten iyidir.
    Gercek cozum poppler-utils (pdftotext) kurmak; kullanici onayi bekliyor.
    """
    import zlib
    parcalar = []
    for m in re.finditer(rb"stream\r?\n(.*?)endstream", ham, re.S):
        blok = m.group(1)
        try:
            coz = zlib.decompress(blok)
        except Exception:
            try:
                coz = zlib.decompressobj().decompress(blok)
            except Exception:
                continue
        # Metin gosterme operatorleri: (metin) Tj  ve  [(a)(b)] TJ
        for t in re.finditer(rb"\((?:\\.|[^\\()])*\)", coz):
            ham_metin = t.group(0)[1:-1]
            try:
                d = ham_metin.decode("latin-1")
            except Exception:
                continue
            d = (d.replace("\\(", "(").replace("\\)", ")")
                 .replace("\\n", " ").replace("\\r", " ").replace("\\\\", "\\"))
            parcalar.append(d)
    metin = " ".join(parcalar)
    metin = _BOSLUK.sub(" ", metin).strip()
    # Okunabilirlik kontrolu: harf/rakam orani cok dusukse cikarim basarisiz
    if len(metin) < 80:
        return ""
    okunur = sum(1 for c in metin if c.isalnum() or c in " .,%-()")
    if okunur / len(metin) < 0.75:
        return ""                      # CID font -> cop cikti, kullanma
    return metin


def sayfa_getir(url: str, onbellek: Optional[Onbellek] = None,
                zaman_asimi: int = 25,
                istek: Optional[Callable] = None) -> dict:
    """Sayfayi indir ve ayikla.

    Doner: {"ok", "url", "durum", "baslik", "yayin_tarihi", "metin", "hata"}
    `metin` alani VERIDIR — icindeki hicbir ifade talimat olarak islenmez.
    `istek` testlerde sahte istemci enjekte etmek icin.
    """
    bos = {"ok": False, "url": url, "durum": 0, "baslik": "", "yayin_tarihi": "",
           "metin": "", "hata": ""}
    if not str(url or "").startswith(("http://", "https://")):
        return {**bos, "hata": "gecersiz url"}

    def _indir():
        try:
            fn = istek or requests.get
            r = fn(url, headers=VARSAYILAN_BASLIK, timeout=zaman_asimi)
            tur = str(r.headers.get("Content-Type", "")).lower()
            if r.status_code != 200:
                return {**bos, "durum": r.status_code, "hata": f"HTTP {r.status_code}"}
            # PDF: resmi kurum verisi cogunlukla PDF olarak yayinlaniyor. Ilk
            # surumde bunlari "metin degil" diye atiyordum ve EN YETKILI kaynaklar
            # (bakanlik raporlari) hic dogrulanamiyordu — canli kuru testte 18
            # iddianin 3'u tam bu yuzden cozulmedi kaldi.
            if "pdf" in tur or str(url).lower().split("?")[0].endswith(".pdf"):
                govde = getattr(r, "content", None) or (r.text or "").encode("latin-1", "ignore")
                metin = pdf_metne(govde[:MAKS_BAYT])
                if not metin:
                    return {**bos, "durum": 200,
                            "hata": "pdf metni cikarilamadi (gomulu font)"}
                return {"ok": True, "url": url, "durum": 200, "baslik": "",
                        "yayin_tarihi": "", "metin": metin[:MAKS_METIN], "hata": ""}
            if "html" not in tur and "text" not in tur and "xml" not in tur:
                return {**bos, "durum": 200, "hata": f"metin degil ({tur[:40]})"}
            ham = r.text or ""
            if len(ham.encode("utf-8", "ignore")) > MAKS_BAYT:
                ham = ham[: MAKS_BAYT // 2]
            return {"ok": True, "url": url, "durum": 200,
                    "baslik": _ilk_eslesme(_BASLIK_DESEN, ham),
                    "yayin_tarihi": _ilk_eslesme(_TARIH_DESEN, ham),
                    "metin": html_metne(ham)[:MAKS_METIN], "hata": ""}
        except Exception as e:
            return {**bos, "hata": str(e)[:160]}

    if onbellek is None:
        return _indir()
    return onbellek.getir("sayfa", {"url": url}, _indir)


# ─────────────── IDDIA - SAYFA ESLESME (LLM'siz on kontrol) ───────────────
# Neden LLM'siz: cogu iddia sayfada birebir gecen bir SAYI ya da TARIH icerir.
# Bunu string olarak aramak bedava ve kesin. LLM'e yalnizca bu kontrol
# BASARISIZ oldugunda basvurulur — para orada harcanir.

_SAYI = re.compile(r"\d[\d.,]*")
_YIL = re.compile(r"\b(1[6-9]\d{2}|20\d{2})\b")


def _sayilari_normalize(metin: str) -> set:
    """"76,941" ve "76941" ayni sayi sayilir. Yuzdeler ve yillar dahil."""
    out = set()
    for m in _SAYI.finditer(metin or ""):
        ham = m.group(0).rstrip(".,")
        sade = ham.replace(",", "").replace(".", "")
        if sade.isdigit() and len(sade) <= 15:
            out.add(sade.lstrip("0") or "0")
    return out


def iddia_sayfada_mi(iddia: str, sayfa_metni: str) -> dict:
    """Iddianin OLCULEBILIR parcalari sayfada geciyor mu?

    Doner: {"sayi_eslesme", "yil_eslesme", "anahtar_kelime_orani", "guclu"}
    "guclu" = sayfada iddianin sayilari VE yillari geciyor (ya da sayi/yil yoksa
    anahtar kelimelerin cogu geciyor).
    """
    iddia = str(iddia or "")
    sayfa = str(sayfa_metni or "")
    i_sayi = _sayilari_normalize(iddia)
    s_sayi = _sayilari_normalize(sayfa)
    i_yil = set(_YIL.findall(iddia))
    s_yil = set(_YIL.findall(sayfa))

    # ⚠ AYIRT EDICI SAYI KURALI (test yakaladi). Ilk surumde "herhangi bir sayi
    # eslesiyorsa yeter" diyordum. Sonuc: "In 2025 Japan recorded 21,000 deaths"
    # iddiasi, sayfada sadece "2025" gectigi icin DOGRULANMIS sayildi — oysa
    # sayfada 76,941 yaziyordu. Yani yanlis rakam kaynakli gorunuyordu.
    # Artik iddianin YIL OLMAYAN her sayisi sayfada gecmek zorunda.
    ayirt_edici = {x for x in i_sayi if not (len(x) == 4 and x in i_yil)}
    sayi_ok = (not ayirt_edici) or ayirt_edici.issubset(s_sayi)
    yil_ok = (not i_yil) or bool(i_yil & s_yil)

    # Anahtar kelimeler: 4+ harfli, cok yaygin olmayan kelimeler
    kelimeler = [k.lower() for k in re.findall(r"[A-Za-zÀ-ÿĀ-žğüşıöçĞÜŞİÖÇ]{4,}", iddia)]
    yaygin = {"this", "that", "with", "from", "have", "been", "were", "their", "which",
              "about", "there", "these", "those", "than", "then", "also", "into",
              "more", "most", "over", "some", "such", "only", "other", "after"}
    anahtar = [k for k in kelimeler if k not in yaygin]
    sayfa_kucuk = sayfa.lower()
    gecen = sum(1 for k in set(anahtar) if k in sayfa_kucuk)
    oran = round(gecen / len(set(anahtar)), 3) if anahtar else 0.0

    guclu = bool(sayfa) and sayi_ok and yil_ok and (
        bool(ayirt_edici) or bool(i_yil) or oran >= 0.6)
    return {"sayi_eslesme": sayi_ok, "yil_eslesme": yil_ok,
            "anahtar_kelime_orani": oran, "guclu": guclu,
            "iddia_sayilari": sorted(i_sayi)[:8], "iddia_yillari": sorted(i_yil)[:4],
            "ayirt_edici_sayilar": sorted(ayirt_edici)[:8]}
