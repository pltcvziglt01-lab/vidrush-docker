"""ANAHTARSIZ ACIK LISANS SAGLAYICILARI — Wikimedia, Openverse, LoC, Archive.org.

Bu dord saglayici da anahtar istemiyor ve kamu mali / CC iceriginin en buyuk
havuzlari. Faz B'nin asil kazanci burada: Vidrush'in kendi dokumani "web/genel
kaynaklari kapatinca kullanilabilir klip %90 dusuyor" diyor; bizim havuz
Pexels+Coverr'la sinirliydi.

⚠ HER SAGLAYICI ICIN AYRI LISANS GERCEGI:
  - Wikimedia Commons : lisans DOSYA BASINA degisir (CC0/CC-BY/CC-BY-SA ve
    bazen fair-use). `extmetadata.LicenseShortName` okunmadan indirme YOK.
  - Openverse         : yalnizca acik lisansli sonuc dondurur ama lisans alanini
    yine tek tek okuyoruz (guvenme, dogrula).
  - Library of Congress: cogu kamu mali ama HEPSI DEGIL; `rights` alani
    okunur, belirsizse reference_only.
  - Internet Archive  : "public domain" ETIKETI GUVENILMEZ; yuklenen icerigin
    cogu telifli. Yalnizca `licenseurl` alani acik olan ogeler kabul edilir.
"""
from __future__ import annotations

from typing import Callable, Optional

import requests

from ..kayit import AramaSonucu, Saglayici, kaydet

BASLIK = {"User-Agent": "BedosahoAI/1.0 (documentary research; contact via site)"}


def _get(istek: Optional[Callable], url: str, params: dict, zaman_asimi: int):
    fn = istek or requests.get
    return fn(url, params=params, headers=BASLIK, timeout=zaman_asimi)


@kaydet
class Wikimedia(Saglayici):
    ad = "wikimedia"
    oncelik = 90
    medya_turleri = ("image", "video")
    kamu_mali = True
    UC = "https://commons.wikimedia.org/w/api.php"

    def ara(self, sorgu, *, tur="image", adet=10, zaman_asimi=20, istek=None):
        s = AramaSonucu(sorgu=sorgu, saglayici=self.ad)
        # filetype araması: bitmap = gorsel, video = video
        tip = "video" if tur == "video" else "bitmap"
        params = {
            "action": "query", "format": "json", "generator": "search",
            "gsrsearch": f"filetype:{tip} {sorgu}", "gsrnamespace": 6,
            "gsrlimit": max(1, min(50, adet)),
            "prop": "imageinfo",
            "iiprop": "url|size|mime|extmetadata|mediatype",
            "iiurlwidth": 1920,
        }
        try:
            r = _get(istek, self.UC, params, zaman_asimi)
            s.istek_sayisi = 1
            if r.status_code != 200:
                s.hata = f"HTTP {r.status_code}"
                return s
            sayfalar = ((r.json().get("query") or {}).get("pages") or {})
            s.kayitlar = list(sayfalar.values())
        except Exception as e:
            s.hata = str(e)[:140]
        return s

    def normalize(self, kayit: dict) -> dict:
        bilgi = (kayit.get("imageinfo") or [{}])[0]
        em = bilgi.get("extmetadata") or {}

        def _em(ad):
            d = em.get(ad) or {}
            return str(d.get("value") or "")

        return {
            "orijinal_url": bilgi.get("descriptionurl") or "",
            "indirme_url": bilgi.get("url") or "",
            "baslik": str(kayit.get("title") or "").removeprefix("File:"),
            "aciklama": _em("ImageDescription")[:400],
            "genislik": int(bilgi.get("width") or 0),
            "yukseklik": int(bilgi.get("height") or 0),
            "sure_sn": float(bilgi.get("duration") or 0),
            "tur": "video" if str(bilgi.get("mediatype", "")).upper() == "VIDEO"
                   else "image",
            "tarih": _em("DateTimeOriginal")[:40],
            "konum": "",
            # Lisans alanlari lisans.py'nin okudugu adlarla
            "LicenseShortName": _em("LicenseShortName"),
            "licenseurl": _em("LicenseUrl"),
            "Artist": _em("Artist"),
            "Credit": _em("Credit"),
            "UsageTerms": _em("UsageTerms"),
        }


@kaydet
class Openverse(Saglayici):
    ad = "openverse"
    oncelik = 80
    # ⚠ Openverse gorsel ve SES sunuyor, VIDEO SUNMUYOR. Ilk surumde
    # medya_turleri'ne "video" yazmistim; video sahnesinde saglayici cagriliyor,
    # ara() hata donduruyor ve saglayici bosa "hatali" sayiliyordu (devre
    # kesiciyi de yanlissiz tetikleyebilirdi). Beyan gercekle ayni olmali.
    medya_turleri = ("image",)
    kamu_mali = True
    UC_GORSEL = "https://api.openverse.org/v1/images/"
    UC_SES = "https://api.openverse.org/v1/audio/"

    def ara(self, sorgu, *, tur="image", adet=10, zaman_asimi=20, istek=None):
        s = AramaSonucu(sorgu=sorgu, saglayici=self.ad)
        if tur == "video":
            s.hata = "openverse video desteklemiyor (gorsel + ses)"
            return s
        params = {"q": sorgu, "page_size": max(1, min(20, adet)),
                  # Yalnizca ticari kullanima ve degistirmeye acik lisanslar
                  "license_type": "commercial,modification"}
        try:
            r = _get(istek, self.UC_GORSEL, params, zaman_asimi)
            s.istek_sayisi = 1
            if r.status_code != 200:
                s.hata = f"HTTP {r.status_code}"
                return s
            s.kayitlar = r.json().get("results") or []
        except Exception as e:
            s.hata = str(e)[:140]
        return s

    def normalize(self, kayit: dict) -> dict:
        return {
            "orijinal_url": kayit.get("foreign_landing_url") or kayit.get("url") or "",
            "indirme_url": kayit.get("url") or "",
            "baslik": str(kayit.get("title") or "")[:200],
            "aciklama": "",
            "genislik": int(kayit.get("width") or 0),
            "yukseklik": int(kayit.get("height") or 0),
            "sure_sn": 0.0,
            "tur": "image",
            "tarih": str(kayit.get("date_created") or "")[:40],
            "konum": "",
            "license": str(kayit.get("license") or ""),
            "license_url": str(kayit.get("license_url") or ""),
            "creator": str(kayit.get("creator") or ""),
        }


@kaydet
class LibraryOfCongress(Saglayici):
    ad = "loc"
    oncelik = 75
    medya_turleri = ("image", "video")
    kamu_mali = True
    # ⚠ 11 Agu 2026 KALITE KAPISI: canli kuru testte LoC 32 aday dondurdu,
    # 32'sinin de lisansi "belirsiz" cikip TAMAMI reddedildi. Sebep: arama ucu
    # (`/search/?fo=json`) `rights` alanini DONDURMUYOR; o alan oge ayrintisinda
    # (`<item_url>?fo=json`). Yani en degerli arsiv kaynagi fiilen olu haldeydi.
    # Cozum: butceli oge-ayrinti cagrisi (bkz. zenginlestir).
    detay_destekli = True
    UC = "https://www.loc.gov/search/"

    def ara(self, sorgu, *, tur="image", adet=10, zaman_asimi=20, istek=None):
        s = AramaSonucu(sorgu=sorgu, saglayici=self.ad)
        params = {"q": sorgu, "fo": "json", "c": max(1, min(25, adet)),
                  "at": "results",
                  "fa": ("online-format:image" if tur == "image"
                         else "online-format:video")}
        try:
            r = _get(istek, self.UC, params, zaman_asimi)
            s.istek_sayisi = 1
            if r.status_code != 200:
                s.hata = f"HTTP {r.status_code}"
                return s
            d = r.json()
            s.kayitlar = d.get("results") or []
        except Exception as e:
            s.hata = str(e)[:140]
        return s

    def zenginlestir(self, ham_kayit, normalize, *, zaman_asimi=20, istek=None):
        """Oge ayrintisindan rights + gercek indirilebilir medya URL'si.

        Belirsiz kalan yine REDDEDILIR — bu cagri "her seyi kabul et" demek
        degil, "yetkili alani gercekten oku" demek."""
        url = str(normalize.get("orijinal_url") or "").rstrip("/")
        if not url.startswith("http"):
            return {}
        try:
            r = _get(istek, url + "/", {"fo": "json", "at": "item,resources"},
                     zaman_asimi)
            if r.status_code != 200:
                return {"_detay_hata": f"HTTP {r.status_code}"}
            d = r.json() or {}
        except Exception as e:
            return {"_detay_hata": str(e)[:100]}

        oge = d.get("item") or {}
        cikti: dict = {"_detay_alindi": True}

        # rights / rights_advisory serbest metin olabilir ya da liste
        for alan in ("rights", "rights_advisory", "rights_information"):
            deg = oge.get(alan)
            if isinstance(deg, list):
                deg = " ".join(str(x) for x in deg)
            if isinstance(deg, str) and deg.strip():
                cikti["rights"] = deg.strip()[:600]
                break

        # Gercek indirilebilir dosya: resources[].files[][] icinde en buyuk
        en_iyi, en_gen = "", 0
        for kaynak in (d.get("resources") or []):
            for dosya_grubu in (kaynak.get("files") or []):
                if not isinstance(dosya_grubu, list):
                    continue
                for f in dosya_grubu:
                    if not isinstance(f, dict):
                        continue
                    u = str(f.get("url") or "")
                    g = int(f.get("width") or 0)
                    if u.startswith("//"):
                        u = "https:" + u
                    if u.startswith("http") and g >= en_gen:
                        en_iyi, en_gen = u, g
        if en_iyi:
            cikti["indirme_url"] = en_iyi
            if en_gen:
                cikti["genislik"] = en_gen
            for kaynak in (d.get("resources") or []):
                if kaynak.get("height"):
                    cikti["yukseklik"] = int(kaynak["height"] or 0)
                    break
        if oge.get("date"):
            cikti["tarih"] = str(oge["date"])[:40]
        yer = oge.get("location") or []
        if isinstance(yer, list) and yer:
            cikti["konum"] = ", ".join(str(x) for x in yer)[:120]
        if oge.get("contributor"):
            k = oge["contributor"]
            cikti["creator"] = (", ".join(k) if isinstance(k, list) else str(k))[:160]
        return cikti

    def normalize(self, kayit: dict) -> dict:
        gorseller = kayit.get("image_url") or []
        indir = ""
        if isinstance(gorseller, list) and gorseller:
            indir = gorseller[-1]                 # en buyuk surum sonda
            if indir.startswith("//"):
                indir = "https:" + indir
        return {
            "orijinal_url": kayit.get("id") or kayit.get("url") or "",
            "indirme_url": indir,
            "baslik": str(kayit.get("title") or "")[:200],
            "aciklama": " ".join(kayit.get("description") or [])[:400],
            "genislik": 0, "yukseklik": 0, "sure_sn": 0.0,
            "tur": "image",
            "tarih": str(kayit.get("date") or "")[:40],
            "konum": ", ".join(kayit.get("location") or [])[:120],
            # LoC "rights" alani serbest metin — lisans.py serbest metinden okur
            "rights": " ".join(kayit.get("rights") or []) if isinstance(
                kayit.get("rights"), list) else str(kayit.get("rights") or ""),
            "creator": ", ".join(kayit.get("contributor") or [])[:160],
        }


@kaydet
class InternetArchive(Saglayici):
    ad = "archive_org"
    oncelik = 70
    medya_turleri = ("image", "video")
    kamu_mali = False        # ⚠ "public domain" etiketi guvenilmez
    UC = "https://archive.org/advancedsearch.php"

    def ara(self, sorgu, *, tur="image", adet=10, zaman_asimi=20, istek=None):
        s = AramaSonucu(sorgu=sorgu, saglayici=self.ad)
        medya = "movies" if tur == "video" else "image"
        # licenseurl ZORUNLU: bu alan yoksa oge zaten reddedilecek, bosa
        # cekmemek icin sorguya kosul olarak koyuyoruz.
        q = f'{sorgu} AND mediatype:({medya}) AND licenseurl:(*)'
        params = {"q": q, "output": "json", "rows": max(1, min(25, adet)),
                  "fl[]": ["identifier", "title", "description", "licenseurl",
                           "creator", "date", "year", "coverage", "downloads"]}
        try:
            r = _get(istek, self.UC, params, zaman_asimi)
            s.istek_sayisi = 1
            if r.status_code != 200:
                s.hata = f"HTTP {r.status_code}"
                return s
            d = r.json()
            s.kayitlar = ((d.get("response") or {}).get("docs") or [])
        except Exception as e:
            s.hata = str(e)[:140]
        return s

    def normalize(self, kayit: dict) -> dict:
        kimlik = str(kayit.get("identifier") or "")
        return {
            "orijinal_url": f"https://archive.org/details/{kimlik}" if kimlik else "",
            # Dogrudan dosya URL'si oge detayindan gelir; dry-run'da indirme yok.
            # Kapsam kapisi bunu "indirme_url yok" diye isaretler.
            "indirme_url": f"https://archive.org/download/{kimlik}" if kimlik else "",
            "baslik": str(kayit.get("title") or "")[:200],
            "aciklama": str(kayit.get("description") or "")[:400],
            "genislik": 0, "yukseklik": 0, "sure_sn": 0.0,
            "tur": "video",
            "tarih": str(kayit.get("date") or kayit.get("year") or "")[:40],
            "konum": str(kayit.get("coverage") or "")[:120],
            "licenseurl": str(kayit.get("licenseurl") or ""),
            "creator": str(kayit.get("creator") or "")[:160],
        }
