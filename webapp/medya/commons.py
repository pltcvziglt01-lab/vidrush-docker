"""WIKIMEDIA COMMONS MEDYA EDINIMI (Faz I-18) — anahtarsiz, ucretsiz.

⚠ NEDEN VAR: I-13'ten I-17'ye kadar her pilot AYNI Apollo fixture'iyla
kosuldu. Ikinci bir konsept (doga/seyahat) pilotu icin havuzda TEK BIR
uygun gorsel yoktu — olculdu: `cikti/faz_e/medya/` altindaki 12 varligin
12'si de Apollo 11 / Ay, `cikti/faz_d/zemin/` altindakiler ise SENTETIK
GRADYAN (fotograf degil). Yani konsept pilotu ya sahte medyayla yapilacakti
ya da gercek medya EDINILECEKTI.

⚠ SOZ:
  · UCRETSIZ ve ANAHTARSIZ. Commons API anahtar istemez; maliyet $0.00.
  · LISANS DUVARI ATLANMAZ. Karar `medya.lisans.lisans_karari`in isidir;
    bu modul yalnizca Commons `extmetadata`sini o fonksiyonun bekledigi
    bicime cevirir. Kendi lisans karari VERMEZ.
  · INDIRME `medya.indirme.guvenli_indir` UZERINDEN. SSRF/bayt tavani/
    decode kapilari aynen gecerli. Bu modul kendi indiricisini YAZMAZ.
  · PROVENANCE ZORUNLU. Eser sahibi ya da lisans okunamayan aday ELENIR;
    "bilinmiyor" ile gecilmez. Her aday kendi ATIF METNINI tasir — boylece
    kaynak kunyesi SAHNEYE OZGU olur (I-16/I-17'de her sahnede ayni genel
    etiket vardi, bu onun kok nedeniydi).
  · KONUYA BAGLI, HARD-CODE DEGIL. Sorgular disaridan verilir; bu modulde
    hicbir konu adi gomulu degildir.
"""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from typing import Callable, Optional

from . import indirme, lisans

API = "https://commons.wikimedia.org/w/api.php"
# Commons kimlik politikasi acikca tanimlanabilir bir User-Agent ister.
KULLANICI_ARACISI = "vidrush-editorv2/1.0 (belgesel arastirma; yerel kosum)"
# Aramada dosya ad alani (namespace 6 = File:)
DOSYA_AD_ALANI = 6
# Bu genisligin altindaki kaynak 4K hedefe YETMEZ; "4K uretiyoruz" demek
# icin kaynak GERCEKTEN yetmelidir (yukseltme sahte cozunurluktur).
DORT_K_EN_AZ_GENISLIK = 3840


def _metni_temizle(ham: str) -> str:
    """Commons `extmetadata` HTML dondurur; duz metne cevir."""
    metin = re.sub(r"<[^>]+>", " ", str(ham or ""))
    metin = metin.replace("&amp;", "&").replace("&quot;", '"')
    metin = metin.replace("&#039;", "'").replace("&nbsp;", " ")
    return " ".join(metin.split())


def varsayilan_istek(yontem: str, url: str, **kw):
    """`medya.guvenlik.guvenli_istek`in bekledigi `requests` bicimli cagirici.

    ⚠ Imza SERBEST DEGIL: guvenlik katmani `istek(yontem, url, timeout=...,
    allow_redirects=False, stream=...)` diye cagiriyor. Ilk surumde
    `(url, zaman_asimi)` yazmistim ve indirme `TypeError` ile dusuyordu —
    kapi dogru calisti, sebep gorunur oldu.
    Yonlendirmeleri guvenlik katmani ADIM ADIM kendisi cozer; burada
    `allow_redirects` DEGISTIRILMEZ.
    """
    import requests
    basliklar = dict(kw.pop("headers", None) or {})
    basliklar.setdefault("User-Agent", KULLANICI_ARACISI)
    return requests.request(yontem, url, headers=basliklar, **kw)


def _api_cagir(parametreler: dict, *, zaman_asimi: int = 30,
               acan: Optional[Callable] = None) -> dict:
    p = dict(parametreler)
    p.setdefault("action", "query")
    p.setdefault("format", "json")
    url = API + "?" + urllib.parse.urlencode(p)
    ac = acan or (lambda u: urllib.request.urlopen(
        urllib.request.Request(u, headers={"User-Agent": KULLANICI_ARACISI}),
        timeout=zaman_asimi))
    with ac(url) as yanit:
        return json.load(yanit)


def ara(sorgu: str, *, adet: int = 6, en_az_genislik: int = 0,
        zaman_asimi: int = 30, acan: Optional[Callable] = None) -> dict:
    """Commons'ta ara ve LISANS DUVARINDAN gecen adaylari don.

    Doner: {"ok","sorgu","denenen","adaylar","elenen","hata"}
    ⚠ Istisna FIRLATMAZ: ag hatasi `ok=False` + gorunur `hata` olur.
    """
    sonuc = {"ok": False, "sorgu": str(sorgu or ""), "denenen": 0,
             "adaylar": [], "elenen": [], "hata": ""}
    if not str(sorgu or "").strip():
        sonuc["hata"] = "SORGU-BOS"
        return sonuc
    try:
        ham = _api_cagir({
            "generator": "search",
            "gsrsearch": f"filetype:bitmap {sorgu}",
            "gsrnamespace": DOSYA_AD_ALANI,
            "gsrlimit": max(1, int(adet) * 3),
            "prop": "imageinfo",
            "iiprop": "url|size|mime|extmetadata",
        }, zaman_asimi=zaman_asimi, acan=acan)
    except Exception as e:                                        # noqa: BLE001
        sonuc["hata"] = f"{type(e).__name__}: {str(e)[:140]}"
        return sonuc

    sayfalar = list(((ham.get("query") or {}).get("pages") or {}).values())
    sonuc["denenen"] = len(sayfalar)
    for sayfa in sayfalar:
        bilgi = (sayfa.get("imageinfo") or [{}])[0]
        em = bilgi.get("extmetadata") or {}

        def al(alan):
            return _metni_temizle((em.get(alan) or {}).get("value") or "")

        baslik = _metni_temizle(sayfa.get("title") or "")
        genislik = int(bilgi.get("width") or 0)
        yukseklik = int(bilgi.get("height") or 0)
        # ⚠ Lisans karari BU MODULUN isi DEGIL — kayit `lisans.py`nin
        # bekledigi bicime cevrilir ve karar ORAYA birakilir.
        kayit = {"LicenseShortName": al("LicenseShortName"),
                 "license_url": al("LicenseUrl"),
                 "Artist": al("Artist"),
                 "Credit": al("Credit"),
                 "UsageTerms": al("UsageTerms")}
        karar = lisans.lisans_karari(kayit, "wikimedia")
        aday = {
            "asset_id": "",
            "baslik": baslik[5:] if baslik.lower().startswith("file:") else baslik,
            "saglayici": "wikimedia",
            "genislik": genislik, "yukseklik": yukseklik,
            "mime": str(bilgi.get("mime") or ""),
            "indirme_url": str(bilgi.get("url") or ""),
            "orijinal_url": str(bilgi.get("descriptionurl")
                                or bilgi.get("url") or ""),
            "lisans": karar.get("lisans", ""),
            "lisans_url": karar.get("lisans_url", ""),
            "eser_sahibi": karar.get("eser_sahibi", ""),
            "atif_gerekli": bool(karar.get("atif_gerekli")),
            "render_kullanilabilir": bool(karar.get("render_kullanilabilir")),
            "red_nedeni": karar.get("red_nedeni", ""),
        }
        aday["atif_metni"] = lisans.atif_metni(
            aday["lisans"], aday["eser_sahibi"], aday["baslik"],
            aday["orijinal_url"])

        if not aday["render_kullanilabilir"]:
            sonuc["elenen"].append({"baslik": aday["baslik"],
                                    "neden": aday["red_nedeni"] or "LISANS"})
            continue
        # ⚠ PROVENANCE ZORUNLU: eser sahibi okunamayan aday GECMEZ.
        if not aday["eser_sahibi"]:
            sonuc["elenen"].append({"baslik": aday["baslik"],
                                    "neden": "ESER-SAHIBI-YOK"})
            continue
        if en_az_genislik and genislik < int(en_az_genislik):
            sonuc["elenen"].append({
                "baslik": aday["baslik"],
                "neden": f"COZUNURLUK-YETERSIZ ({genislik} < {en_az_genislik})"})
            continue
        if not aday["indirme_url"]:
            sonuc["elenen"].append({"baslik": aday["baslik"],
                                    "neden": "URL-YOK"})
            continue
        sonuc["adaylar"].append(aday)

    # En yuksek cozunurluk once — 4K hedefi icin kaynak payi onemli.
    sonuc["adaylar"].sort(key=lambda a: -(a["genislik"] * a["yukseklik"]))
    sonuc["adaylar"] = sonuc["adaylar"][:max(1, int(adet))]
    sonuc["ok"] = bool(sonuc["adaylar"])
    return sonuc


def indir(aday: dict, hedef: str, *, istek: Optional[Callable] = None,
          maks_bayt: int = 40 * 1024 * 1024, zaman_asimi: int = 60,
          deneme: int = 3, bekleme_tavani: float = 20.0,
          uyu: Optional[Callable] = None) -> dict:
    """Adayi GUVENLI indiriciyle indir. Kendi indiricisini YAZMAZ.

    ⚠ NAZIK YENIDEN DENEME: Wikimedia yuk sunuculari hizli ardisik istekte
    `HTTP 429` donuyor (I-18'de olculdu — dort sahnenin dordu de 429 aldi).
    `guvenli_indir` zaten `retry_after` raporluyor; burada SINIRLI (varsayilan
    3) ve TAVANLI bekleme uygulanir. Sonsuz deneme YOK, agresif dongu YOK.
    """
    if not isinstance(aday, dict) or not aday.get("indirme_url"):
        return {"ok": False, "sebep": "URL-YOK"}
    if not aday.get("render_kullanilabilir"):
        return {"ok": False, "sebep": "LISANS-DUVARI"}
    import time
    bekle = uyu or time.sleep
    son = {"ok": False, "sebep": "DENENMEDI"}
    for i in range(max(1, int(deneme))):
        try:
            son = indirme.guvenli_indir(
                aday["indirme_url"], hedef, istek=istek or varsayilan_istek,
                beklenen="image", maks_bayt=maks_bayt,
                zaman_asimi=zaman_asimi)
        except Exception as e:                                    # noqa: BLE001
            son = {"ok": False, "sebep": f"{type(e).__name__}: {str(e)[:140]}"}
        if son.get("ok"):
            return son
        if son.get("http") != 429 and "429" not in str(son.get("sebep", "")):
            return son                       # 429 disinda tekrar denenmez
        if i == int(deneme) - 1:
            break
        gecikme = min(float(bekle_suresi(son, i)), float(bekleme_tavani))
        son["bekleme_sn"] = gecikme
        bekle(gecikme)
    return son


def bekle_suresi(sonuc: dict, deneme_indeksi: int) -> float:
    """Sunucunun `Retry-After`i varsa ONA uy; yoksa ustel geri cekilme."""
    try:
        ra = float((sonuc or {}).get("retry_after") or 0)
    except (TypeError, ValueError):
        ra = 0.0
    return ra if ra > 0 else float(2 ** max(0, int(deneme_indeksi)) * 2)


def kapsam_ozeti() -> dict:
    """Ne yaptigi SAYILABILIR olsun — "her medyayi buluruz" iddiasi yok."""
    return {
        "kaynak": "Wikimedia Commons",
        "anahtar_gerekli": False,
        "maliyet_usd": 0.0,
        "lisans_karari": "medya.lisans.lisans_karari (bu modul karar VERMEZ)",
        "indirme": "medya.indirme.guvenli_indir (SSRF + bayt + decode)",
        "provenance_zorunlu": ["lisans", "eser_sahibi"],
        "dort_k_en_az_genislik": DORT_K_EN_AZ_GENISLIK,
        "kapsam_disi": ["video/hareketli B-roll", "diger saglayicilar",
                        "kare-bakan icerik dogrulamasi (vision)"],
    }
