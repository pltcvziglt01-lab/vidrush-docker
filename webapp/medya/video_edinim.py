#!/usr/bin/env python3
"""FAZ J-5a — GERCEK VIDEO EDINIMI (dar kapsam, anahtarsiz, tavanli).

⚠ SERT SINIRLAR (kod ile uygulanir, "dikkat ederiz" DEGIL):
  · EN FAZLA 1 dosya indirilir (`INDIRME_TAVANI_DOSYA`).
  · EN FAZLA 300 MB (`INDIRME_TAVANI_BAYT`) — akis sirasinda kesilir.
  · Anahtar gerektiren saglayici KULLANILMAZ (Pexels/Pixabay YOK).
  · NASA yalnizca sorgu GERCEKTEN uzay/NASA konusuysa ikinci saglayicidir.
  · KONU DISI FALLBACK YOKTUR: aday bulunamazsa BOS doner, "bari sunu al"
    diye alakasiz video ALINMAZ.
  · Maliyet $0 (Commons ve NASA anahtarsiz ve ucretsiz).

⚠ KABUL KAPISI J-4'TUR. `video_lisans.video_provenance_karari()` iki kez
kosar: indirmeden ONCE (kanitlarin indirilebilir kismi) ve indirmeden SONRA
(ffprobe ile OLCULEN codec/cozunurluk/bitrate ile). Ikisinden biri
reddederse dosya SILINIR ve varlik KULLANILMAZ. EMIN DEGILSEN ALMA.

⚠ Bu modul gorsel edinimini HIC DEGISTIRMEZ.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timezone
from typing import Callable, Optional

from . import commons, indirme, video_lisans

SEMA_SURUM = "1.0.0"

# ── SERT TAVANLAR ──
INDIRME_TAVANI_DOSYA = 1
INDIRME_TAVANI_BAYT = 300 * 1024 * 1024

# Anahtar gerektiren saglayicilar — BU ATOMDA KULLANILMAZ.
ANAHTARLI_SAGLAYICI = ("pexels", "pixabay", "freepik", "storyblocks")

# NASA'yi ikinci saglayici yapan konu isaretleri. ⚠ Liste DAR tutuldu:
# amac "her seye NASA" degil, yalnizca gercekten uzay olan sorgular.
UZAY_ISARETLERI = (
    "nasa", "space", "uzay", "spacecraft", "satellite", "uydu", "orbit",
    "yorunge", "mars", "moon", "ay yuzeyi", "lunar", "jupiter", "saturn",
    "galaxy", "galaksi", "nebula", "bulutsu", "astronaut", "astronot",
    "rocket", "roket", "telescope", "teleskop", "iss", "apollo", "artemis",
    "asteroid", "comet", "kuyruklu yildiz", "solar system", "gunes sistemi",
)


def uzay_sorgusu_mu(sorgu: str) -> bool:
    """Sorgu GERCEKTEN uzay/NASA konusu mu? Degilse NASA kullanilmaz."""
    m = " " + re.sub(r"[^a-z0-9ığüşöç ]+", " ", str(sorgu or "").lower()) + " "
    return any(f" {k} " in m or m.strip().startswith(k) for k in UZAY_ISARETLERI)


def simdi_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def teknik_olc(yol: str) -> dict:
    """ffprobe ile OLCULEN teknik kanit. Okunamazsa BOS doner (varsayim yok)."""
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_streams", "-show_format",
             "-of", "json", yol], capture_output=True, text=True, timeout=180)
        d = json.loads(r.stdout or "{}")
    except Exception:
        return {}
    vid = [s for s in (d.get("streams") or [])
           if s.get("codec_type") == "video"]
    if not vid:
        return {}
    v = vid[0]
    bicim = d.get("format") or {}

    def _int(x):
        try:
            return int(float(x))
        except (TypeError, ValueError):
            return 0

    br = _int(v.get("bit_rate")) or _int(bicim.get("bit_rate"))
    boyut, sure = _int(bicim.get("size")), float(bicim.get("duration") or 0)
    if not br and boyut and sure > 0:
        br = int(boyut * 8 / sure)          # bicimden TURETILDI, uydurma degil
    return {"codec": v.get("codec_name") or "", "genislik": _int(v.get("width")),
            "yukseklik": _int(v.get("height")), "bitrate": br,
            "sure_sn": sure, "boyut_bayt": boyut,
            "ses_akisi": any(s.get("codec_type") == "audio"
                             for s in (d.get("streams") or []))}


def aday_sec(adaylar: list, *, en_az_sure_sn: float = 0.0,
             tavan_bayt: int = INDIRME_TAVANI_BAYT) -> tuple:
    """TAVAN ICINDEKI izinli ozgunler arasindan EN YUKSEK kaliteyi sec.

    Sira: cozunurluk (piksel) -> bitrate tahmini -> sure.
    ⚠ Konu disi aday BURAYA GELMEZ: liste zaten SEMANTIK sorgunun kendi
    sonucudur ve alaka sirasi `commons.video_ara` icinde uygulanmistir.
    Doner: (secilen | None, elenenler)
    """
    uygun, elenen = [], []
    for a in adaylar or []:
        if not isinstance(a, dict):
            continue
        ad = str(a.get("baslik") or "")
        if int(a.get("boyut_bayt") or 0) > int(tavan_bayt):
            elenen.append({"baslik": ad, "neden": (
                f"TAVAN-ASIYOR ({int(a.get('boyut_bayt') or 0)} > "
                f"{int(tavan_bayt)})")})
            continue
        if en_az_sure_sn and float(a.get("sure_sn") or 0) < float(en_az_sure_sn):
            elenen.append({"baslik": ad, "neden": "SURE-YETERSIZ"})
            continue
        uygun.append(a)
    if not uygun:
        return None, elenen
    uygun.sort(key=lambda a: (-(int(a.get("genislik") or 0)
                               * int(a.get("yukseklik") or 0)),
                              -int(a.get("bitrate_tahmini") or 0),
                              -float(a.get("sure_sn") or 0)))
    return uygun[0], elenen


def _kunye_yaz(yol: str, aday: dict, karar: dict) -> str:
    kunye = {
        "sema": SEMA_SURUM, "asset_id": aday.get("asset_id", ""),
        "baslik": aday.get("baslik", ""), "tur": "video",
        "saglayici": aday.get("saglayici", ""),
        "lisans": karar.get("lisans", ""),
        "lisans_url": karar.get("lisans_url", ""),
        "lisans_kaydi": (karar.get("kanit") or {}).get("lisans_kaydi", ""),
        "eser_sahibi": karar.get("eser_sahibi", ""),
        "atif_gerekli": bool(karar.get("atif_gerekli")),
        "atif_metni": aday.get("atif_metni", ""),
        "orijinal_url": aday.get("orijinal_url", ""),
        "indirme_url": aday.get("indirme_url", ""),
        "indirme_zamani": (karar.get("kanit") or {}).get("indirme_zamani", ""),
        "teknik": karar.get("teknik_olculen") or {},
        "video_kabul": bool(karar.get("video_kabul")),
        "uyarilar": list(karar.get("uyarilar") or []),
    }
    hedef = yol + ".kunye.json"
    with open(hedef, "w", encoding="utf-8") as f:
        json.dump(kunye, f, ensure_ascii=False, indent=1)
    return hedef


def video_edin(sorgu: str, hedef_dizin: str, *, ad: str = "video",
               en_az_sure_sn: float = 0.0, en_az_genislik: int = 1280,
               tavan_dosya: int = INDIRME_TAVANI_DOSYA,
               tavan_bayt: int = INDIRME_TAVANI_BAYT,
               arayici: Optional[Callable] = None,
               istek: Optional[Callable] = None) -> dict:
    """Bir sorgu icin EN FAZLA `tavan_dosya` gercek video indir.

    ⚠ Anahtarli saglayici KULLANILMAZ. NASA yalnizca `uzay_sorgusu_mu()`
    True ise devreye girer. Aday yoksa KONU DISI fallback YAPILMAZ.
    """
    rapor = {"sema": SEMA_SURUM, "sorgu": str(sorgu or ""), "ok": False,
             "indirilen": [], "elenen": [], "reddedilen": [], "hata": "",
             "saglayici_sirasi": ["wikimedia"],
             "anahtarli_saglayici_kullanildi": False,
             "tavan": {"dosya": int(tavan_dosya), "bayt": int(tavan_bayt)},
             "maliyet_usd": 0.0}
    if uzay_sorgusu_mu(sorgu):
        rapor["saglayici_sirasi"].append("nasa")
    if int(tavan_dosya) < 1:
        rapor["hata"] = "TAVAN-SIFIR"
        return rapor

    ara = arayici or commons.video_ara
    try:
        bulunan = ara(sorgu, adet=8, en_az_genislik=en_az_genislik,
                      en_az_sure_sn=en_az_sure_sn)
    except Exception as e:                                        # noqa: BLE001
        rapor["hata"] = f"{type(e).__name__}: {str(e)[:140]}"
        return rapor
    rapor["denenen"] = int(bulunan.get("denenen") or 0)
    rapor["elenen"].extend(bulunan.get("elenen") or [])
    if not bulunan.get("adaylar"):
        # ⚠ KONU DISI FALLBACK YOK. Bos donmek DOGRU davranistir.
        rapor["hata"] = bulunan.get("hata") or "ADAY-YOK"
        return rapor

    secilen, elenen2 = aday_sec(bulunan["adaylar"],
                                en_az_sure_sn=en_az_sure_sn,
                                tavan_bayt=tavan_bayt)
    rapor["elenen"].extend(elenen2)
    if not secilen:
        rapor["hata"] = "TAVAN-ICINDE-ADAY-YOK"
        return rapor

    # ── KAPI 1: INDIRMEDEN ONCE J-4 (teknik kanit haric) ──
    on = video_lisans.video_provenance_karari(
        secilen, secilen.get("saglayici", ""),
        teknik={"codec": "on-kontrol", "genislik": secilen.get("genislik"),
                "yukseklik": secilen.get("yukseklik"),
                "bitrate": secilen.get("bitrate_tahmini")},
        indirme_zamani="on-kontrol")
    if not on.get("video_kabul"):
        rapor["reddedilen"].append({"baslik": secilen.get("baslik", ""),
                                    "asama": "on-kontrol",
                                    "neden": on.get("red_nedeni", "")})
        rapor["hata"] = "J4-ON-KONTROL-RED"
        return rapor

    os.makedirs(hedef_dizin, exist_ok=True)
    uzanti = ".webm" if "webm" in str(secilen.get("mime")) else ".ogv"
    yol = os.path.join(hedef_dizin, f"{ad}{uzanti}")
    zaman = simdi_iso()
    ind = indirme.guvenli_indir(
        secilen["indirme_url"], yol,
        istek=istek or commons.varsayilan_istek, beklenen="video",
        maks_bayt=int(tavan_bayt), en_az_bayt=8000, zaman_asimi=180)
    if not ind.get("ok"):
        rapor["reddedilen"].append({"baslik": secilen.get("baslik", ""),
                                    "asama": "indirme",
                                    "neden": str(ind.get("sebep"))[:200]})
        rapor["hata"] = "INDIRME-RED"
        return rapor

    # ── KAPI 2: INDIRMEDEN SONRA — OLCULEN teknik kanitla J-4 TEKRAR ──
    teknik = teknik_olc(yol)
    son = video_lisans.video_provenance_karari(
        dict(secilen, indirme_zamani=zaman), secilen.get("saglayici", ""),
        teknik=teknik, indirme_zamani=zaman)
    son["teknik_olculen"] = teknik
    if not son.get("video_kabul"):
        try:
            os.remove(yol)                      # ⚠ RED -> DOSYA KALMAZ
        except OSError:
            pass
        rapor["reddedilen"].append({"baslik": secilen.get("baslik", ""),
                                    "asama": "son-kontrol",
                                    "neden": son.get("red_nedeni", "")})
        rapor["hata"] = "J4-SON-KONTROL-RED"
        return rapor

    kunye_yolu = _kunye_yaz(yol, secilen, son)
    rapor["indirilen"].append({
        "baslik": secilen.get("baslik", ""), "yol": yol,
        "kunye": kunye_yolu, "saglayici": secilen.get("saglayici", ""),
        "lisans": son.get("lisans", ""), "teknik": teknik,
        "okunan_bayt": ind.get("okunan_bayt", 0),
        "indirme_zamani": zaman, "uyarilar": son.get("uyarilar") or []})
    rapor["ok"] = True
    return rapor


def kapsam_ozeti() -> dict:
    return {
        "sema_surum": SEMA_SURUM,
        "tavan_dosya": INDIRME_TAVANI_DOSYA,
        "tavan_bayt": INDIRME_TAVANI_BAYT,
        "anahtarli_saglayici_kullanilmaz": list(ANAHTARLI_SAGLAYICI),
        "nasa_kosulu": "yalniz uzay_sorgusu_mu(sorgu) True ise",
        "konu_disi_fallback": False,
        "kabul_kapisi": "medya.video_lisans.video_provenance_karari (2 kez)",
        "indirme": "medya.indirme.guvenli_indir (SSRF + bayt + HTML + ffprobe)",
        "maliyet_usd": 0.0,
        "gorsel_yolunu_degistirir": False,
    }
