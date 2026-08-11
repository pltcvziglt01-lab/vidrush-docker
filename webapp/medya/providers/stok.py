"""STOK SAGLAYICI ADAPTORLERI — Pexels, Coverr.

⚠ MEVCUT KODU BOZMAMA KURALI: `webapp/kaynak.py` icindeki `pexels_video()` ve
`coverr_video()` CALISAN uretim koddur (bugun 12/12 footage bulma olcumu onunla
alindi). Bu adaptorler o fonksiyonlari CAGIRMIYOR ve DEGISTIRMIYOR.

Sebep: kaynak.py'deki fonksiyonlar "ara + indir + normalize et" isini birlikte
yapiyor ve dosya yoluna yaziyor. Faz B'nin ihtiyaci farkli: SADECE ARAMA
(dry-run'da indirme yok), tum adaylari gorme, lisans/provenance kaydi. Ayni
fonksiyonu iki farkli sozlesmeye zorlamak calisan kodu riske atardi.

Ortak olan tek sey anahtar okuma davranisi (env ya da veri/*.txt) ve o da
`Saglayici.anahtar()` icinde bagimsiz olarak uygulanmis durumda.
"""
from __future__ import annotations

import requests

from ..kayit import AramaSonucu, Saglayici, kaydet

BASLIK = {"User-Agent": "BedosahoAI/1.0"}


@kaydet
class Pexels(Saglayici):
    ad = "pexels"
    oncelik = 60
    anahtar_env = "PEXELS_KEY"
    anahtar_dosya = "pexels_key.txt"
    medya_turleri = ("video", "image")
    UC_VIDEO = "https://api.pexels.com/videos/search"
    UC_GORSEL = "https://api.pexels.com/v1/search"

    def ara(self, sorgu, *, tur="video", adet=10, zaman_asimi=20, istek=None):
        s = AramaSonucu(sorgu=sorgu, saglayici=self.ad)
        anah = self.anahtar()
        if not anah:
            s.hata = "anahtar yok"
            return s
        fn = istek or requests.get
        uc = self.UC_VIDEO if tur == "video" else self.UC_GORSEL
        params = {"query": sorgu, "per_page": max(1, min(20, adet)),
                  "orientation": "landscape"}
        if tur == "video":
            params["size"] = "large"        # 4K yerli klip (11 Agu olcumu)
        try:
            r = fn(uc, headers={"Authorization": anah, **BASLIK},
                   params=params, timeout=zaman_asimi)
            s.istek_sayisi = 1
            if r.status_code != 200:
                s.hata = f"HTTP {r.status_code}"
                return s
            d = r.json()
            s.kayitlar = d.get("videos") if tur == "video" else d.get("photos")
            s.kayitlar = s.kayitlar or []
            for k in s.kayitlar:
                k["_tur"] = tur
        except Exception as e:
            s.hata = str(e)[:140]
        return s

    def normalize(self, kayit: dict) -> dict:
        tur = kayit.get("_tur") or ("video" if kayit.get("video_files") else "image")
        indir, gen, yuk = "", 0, 0
        if tur == "video":
            dosyalar = [f for f in (kayit.get("video_files") or [])
                        if f.get("file_type") == "video/mp4"]
            dosyalar.sort(key=lambda f: (f.get("width") or 0))
            sec = next((f for f in dosyalar if (f.get("width") or 0) >= 2560),
                       dosyalar[-1] if dosyalar else {})
            indir = sec.get("link") or ""
            gen, yuk = int(sec.get("width") or 0), int(sec.get("height") or 0)
        else:
            kaynaklar = kayit.get("src") or {}
            indir = kaynaklar.get("large2x") or kaynaklar.get("original") or ""
            gen, yuk = int(kayit.get("width") or 0), int(kayit.get("height") or 0)
        return {
            "orijinal_url": kayit.get("url") or "",
            "indirme_url": indir,
            # Pexels baslik dondurmuyor; sayfa slug'i tek betimleyici kaynak
            "baslik": str(kayit.get("url") or "").rstrip("/").split("/")[-1
                                                                       ].replace("-", " "),
            "aciklama": str(kayit.get("alt") or "")[:300],
            "genislik": gen, "yukseklik": yuk,
            "sure_sn": float(kayit.get("duration") or 0),
            "tur": tur, "tarih": "", "konum": "",
            "creator": ((kayit.get("user") or {}).get("name") or ""),
            # Lisans saglayici sabiti (lisans.SAGLAYICI_SABIT_LISANS)
        }


@kaydet
class Coverr(Saglayici):
    ad = "coverr"
    oncelik = 55
    anahtar_env = "COVERR_KEY"
    anahtar_dosya = "coverr_key.txt"
    medya_turleri = ("video",)
    UC = "https://api.coverr.co/videos"

    def ara(self, sorgu, *, tur="video", adet=10, zaman_asimi=20, istek=None):
        s = AramaSonucu(sorgu=sorgu, saglayici=self.ad)
        if tur != "video":
            s.hata = "coverr yalniz video"
            return s
        anah = self.anahtar()
        if not anah:
            s.hata = "anahtar yok"
            return s
        fn = istek or requests.get
        try:
            r = fn(self.UC, headers=BASLIK,
                   params={"query": sorgu, "page_size": max(1, min(20, adet)),
                           "urls": "true"},
                   timeout=zaman_asimi)
            s.istek_sayisi = 1
            if r.status_code != 200:
                s.hata = f"HTTP {r.status_code}"
                return s
            s.kayitlar = (r.json().get("hits") or [])
        except Exception as e:
            s.hata = str(e)[:140]
        return s

    def normalize(self, kayit: dict) -> dict:
        urls = kayit.get("urls") or {}
        return {
            "orijinal_url": f"https://coverr.co/videos/{kayit.get('id','')}",
            "indirme_url": urls.get("mp4_download") or urls.get("mp4") or "",
            "baslik": str(kayit.get("title") or "")[:200],
            "aciklama": str(kayit.get("description") or "")[:300],
            "genislik": int(kayit.get("max_width") or 0),
            "yukseklik": int(kayit.get("max_height") or 0),
            "sure_sn": float(kayit.get("duration") or 0),
            "tur": "video", "tarih": "", "konum": "",
            "creator": "Coverr",
        }
