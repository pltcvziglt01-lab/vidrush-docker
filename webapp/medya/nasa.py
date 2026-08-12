"""NASA GORUNTU KUTUPHANESI SAGLAYICISI (Faz I-19) — anahtarsiz, kamu mali.

⚠ NEDEN VAR: I-18'de Wikimedia Commons'tan METADATA alinabiliyordu ama
BAYT indirme `HTTP 429 / Retry-After 600` ile duruyordu (ucu ayri olcumde
dogrulandi). Tek saglayiciya bagli bir edinim hatti, o saglayici hiz
sinirina takildiginda TAMAMEN duruyor. Bu modul ikinci bir GUVENLI kaynak
verir.

⚠ SOZ (commons.py ile ayni):
  · UCRETSIZ ve ANAHTARSIZ. `images-api.nasa.gov` anahtar istemez.
  · LISANS KARARINI KENDI VERMEZ -> `medya.lisans.lisans_karari`.
    (`lisans.SAGLAYICI_SABIT_LISANS` zaten "nasa" -> "nasa-public" biliyor.)
  · INDIRMEYI KENDI YAPMAZ -> `medya.indirme.guvenli_indir` (SSRF duvari).
  · PROVENANCE ZORUNLU: `rights`/merkez/baslik okunamayan aday ELENIR.
  · KONU ADI GOMULU DEGIL — sorgular disaridan gelir.

⚠ DURUST SINIR: NASA goruntu kutuphanesi agirlikli olarak YORUNGE/UYDU ve
gorev fotografciligidir. Yer seviyesinde manzara fotografi BEKLENMEMELI;
edinilen varligin NE OLDUGU basligiyla birlikte raporlanir ki anlatim
gorunmeyeni iddia etmesin.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Callable, Optional

from . import indirme, lisans

ARAMA = "https://images-api.nasa.gov/search"
KULLANICI_ARACISI = "vidrush-editorv2/1.0 (belgesel arastirma; yerel kosum)"
# Yer seviyesi manzara BEKLENMEYEN kaynak oldugunu cagirana hatirlatan etiket.
KAYNAK_NITELIGI = "yorunge/uydu ve gorev fotografciligi"


def _ac(url: str, zaman_asimi: int = 40):
    return urllib.request.urlopen(
        urllib.request.Request(url, headers={"User-Agent": KULLANICI_ARACISI}),
        timeout=zaman_asimi)


def varsayilan_istek(yontem: str, url: str, **kw):
    """`medya.guvenlik.guvenli_istek`in bekledigi `requests` bicimli cagirici."""
    import requests
    basliklar = dict(kw.pop("headers", None) or {})
    basliklar.setdefault("User-Agent", KULLANICI_ARACISI)
    return requests.request(yontem, url, headers=basliklar, **kw)


def _varlik_listesi(href: str, *, zaman_asimi: int, acan) -> list:
    try:
        with (acan or _ac)(href, zaman_asimi) as y:
            return json.load(y)
    except Exception:                                             # noqa: BLE001
        return []


def _en_iyi_jpg(dosyalar: list) -> str:
    """`~orig` > `~large` > herhangi bir jpg. PNG/TIF kasitli disarida."""
    for son in ("~orig.jpg", "~large.jpg", "~medium.jpg"):
        for u in dosyalar:
            if str(u).lower().endswith(son):
                return str(u)
    for u in dosyalar:
        if str(u).lower().endswith((".jpg", ".jpeg")):
            return str(u)
    return ""


def ara(sorgu: str, *, adet: int = 6, en_az_genislik: int = 0,
        zaman_asimi: int = 40, acan: Optional[Callable] = None) -> dict:
    """NASA kutuphanesinde ara; LISANS DUVARINDAN gecen adaylari don.

    ⚠ `en_az_genislik` BURADA UYGULANAMAZ: arama ucu piksel olcusu
    VERMIYOR. Olcu ancak indirildikten sonra bilinir — bu yuzden alan
    `genislik: 0` doner ve cagiran taraf olcuyu indirme SONRASI dogrular.
    Sahte olcu UYDURULMAZ.
    """
    sonuc = {"ok": False, "saglayici": "nasa", "sorgu": str(sorgu or ""),
             "denenen": 0, "adaylar": [], "elenen": [], "hata": ""}
    if not str(sorgu or "").strip():
        sonuc["hata"] = "SORGU-BOS"
        return sonuc
    url = ARAMA + "?" + urllib.parse.urlencode(
        {"q": sorgu, "media_type": "image"})
    try:
        with (acan or _ac)(url, zaman_asimi) as y:
            ham = json.load(y)
    except Exception as e:                                        # noqa: BLE001
        sonuc["hata"] = f"{type(e).__name__}: {str(e)[:140]}"
        return sonuc

    ogeler = ((ham.get("collection") or {}).get("items") or [])
    sonuc["denenen"] = len(ogeler)
    for oge in ogeler[:max(1, int(adet) * 3)]:
        veri = (oge.get("data") or [{}])[0]
        baslik = str(veri.get("title") or "").strip()
        if not baslik:
            sonuc["elenen"].append({"baslik": "(bassiz)",
                                    "neden": "BASLIK-YOK"})
            continue
        dosyalar = _varlik_listesi(oge.get("href") or "",
                                   zaman_asimi=zaman_asimi, acan=acan)
        indirme_url = _en_iyi_jpg(dosyalar)
        if not indirme_url:
            sonuc["elenen"].append({"baslik": baslik[:60],
                                    "neden": "JPG-YOK"})
            continue
        # ⚠ Lisans karari `lisans.py`nin isi. NASA icin sabit eslesme var
        # ama `rights` alani varsa O da gecirilir; karar yine oraya ait.
        kayit = {"rights": str(veri.get("rights") or ""),
                 "Artist": str(veri.get("photographer")
                               or veri.get("secondary_creator")
                               or veri.get("center") or ""),
                 "Credit": str(veri.get("center") or "NASA")}
        karar = lisans.lisans_karari(kayit, "nasa")
        aday = {
            "asset_id": "", "baslik": baslik,
            "saglayici": "nasa",
            "genislik": 0, "yukseklik": 0,          # ⚠ arama olcuyu VERMIYOR
            "olcu_bilinmiyor": True,
            "indirme_url": indirme_url,
            "orijinal_url": str(veri.get("nasa_id")
                                and f"https://images.nasa.gov/details-"
                                    f"{veri.get('nasa_id')}" or indirme_url),
            "lisans": karar.get("lisans", ""),
            "eser_sahibi": karar.get("eser_sahibi") or str(
                veri.get("center") or "NASA"),
            "atif_gerekli": bool(karar.get("atif_gerekli")),
            "render_kullanilabilir": bool(karar.get("render_kullanilabilir")),
            "red_nedeni": karar.get("red_nedeni", ""),
            "kaynak_niteligi": KAYNAK_NITELIGI,
            "aciklama": str(veri.get("description") or "")[:300],
        }
        aday["atif_metni"] = lisans.atif_metni(
            aday["lisans"], aday["eser_sahibi"], aday["baslik"],
            aday["orijinal_url"])
        if not aday["render_kullanilabilir"]:
            sonuc["elenen"].append({"baslik": baslik[:60],
                                    "neden": aday["red_nedeni"] or "LISANS"})
            continue
        if not aday["eser_sahibi"]:
            sonuc["elenen"].append({"baslik": baslik[:60],
                                    "neden": "ESER-SAHIBI-YOK"})
            continue
        sonuc["adaylar"].append(aday)
        if len(sonuc["adaylar"]) >= max(1, int(adet)):
            break
    sonuc["ok"] = bool(sonuc["adaylar"])
    return sonuc


def indir(aday: dict, hedef: str, *, istek: Optional[Callable] = None,
          maks_bayt: int = 40 * 1024 * 1024, zaman_asimi: int = 60,
          deneme: int = 1) -> dict:
    """Adayi GUVENLI indiriciyle indir. Kendi indiricisini YAZMAZ."""
    if not isinstance(aday, dict) or not aday.get("indirme_url"):
        return {"ok": False, "sebep": "URL-YOK"}
    if not aday.get("render_kullanilabilir"):
        return {"ok": False, "sebep": "LISANS-DUVARI"}
    try:
        return indirme.guvenli_indir(
            aday["indirme_url"], hedef, istek=istek or varsayilan_istek,
            beklenen="image", maks_bayt=maks_bayt, zaman_asimi=zaman_asimi)
    except Exception as e:                                        # noqa: BLE001
        return {"ok": False, "sebep": f"{type(e).__name__}: {str(e)[:140]}"}


def kapsam_ozeti() -> dict:
    return {
        "kaynak": "NASA Image and Video Library",
        "anahtar_gerekli": False, "maliyet_usd": 0.0,
        "lisans_karari": "medya.lisans.lisans_karari (bu modul karar VERMEZ)",
        "indirme": "medya.indirme.guvenli_indir (SSRF + bayt + decode)",
        "provenance_zorunlu": ["lisans", "eser_sahibi", "baslik"],
        "kaynak_niteligi": KAYNAK_NITELIGI,
        "kapsam_disi": ["yer seviyesi manzara fotografi (beklenmemeli)",
                        "video", "arama sonucunda piksel olcusu"],
    }
