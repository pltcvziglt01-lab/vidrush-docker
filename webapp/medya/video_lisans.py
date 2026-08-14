#!/usr/bin/env python3
"""FAZ J-4 — GERCEK VIDEO VARLIKLARI ICIN KORUYUCU PROVENANCE SOZLESMESI.

⚠ BU MODUL YALNIZCA ENGELLER. Hicbir varligi kabul EDILEBILIR HALE GETIRMEZ:
mevcut `lisans.lisans_karari()` REDDETTIYSE burasi o karari ASLA cevirmez.
Video icin YALNIZCA EK SART koyar. Gorsel yolu HIC DEGISMEZ.

⚠ EMIN DEGILSEN ALMA. Varsayilan karar REDDIR; kabul yalnizca kanitlarin
HEPSI varken verilir. Eksik/bos/okunamayan her kanit REDDE gider, "muhtemelen
uygundur" DENMEZ.

⚠ BU ATOMDA AG KULLANILMAZ, INDIRME YAPILMAZ. Modul saf bir karar
fonksiyonudur; edinim hattina BAGLANMADI (secim/render davranisi
degismesin diye). Baglama isi ayri bir atomdur.

── NEDEN AYRI BIR SOZLESME? ──
Gorsel icin lisans + eser sahibi yeterliydi. Video icin degil:
  · video dosyalari cogu zaman AYRI bir lisansa tabi (platform ToS'u),
  · "en yuksek ozgun kalite" iddiasi TEKNIK KANIT ister (codec/cozunurluk/
    bitrate) — yoksa neyin indirildigi bilinmiyor demektir,
  · indirme ZAMANI olmadan lisansin o an gecerli oldugu gosterilemez.
"""
from __future__ import annotations

from typing import Optional
from urllib.parse import urlparse

from .lisans import lisans_karari

SEMA_SURUM = "1.0.0"

# Video kabulu icin ZORUNLU kanit alanlari. Biri bile eksikse RED.
VIDEO_ZORUNLU_KANIT = (
    "kaynak_url",        # varligin insan tarafindan acilabilir kaynak sayfasi
    "saglayici",         # hangi saglayicidan alindi
    "lisans_turu",       # normalize edilmis lisans anahtari
    "lisans_kaydi",      # SAGLAYICININ lisans kaydi (API/sayfa) — beyan DEGIL
    "indirme_zamani",    # ISO8601; lisansin o an gecerli oldugunun kaydi
    "codec",             # ffprobe ile OLCULEN
    "cozunurluk",        # (genislik, yukseklik) — OLCULEN
    "bitrate",           # OLCULEN (bit/s)
)

# Lisans kaydini MAKINE OKUNUR bicimde veren ve indirme izni ACIK olan
# saglayicilar. ⚠ Bu liste bir "guvenilir kaynak" listesi DEGIL, yalnizca
# "lisans kaydi ALINABILIR" listesidir; lisansin kendisi yine
# `lisans_karari()` ile denetlenir.
LISANS_KAYDI_VEREN_SAGLAYICI = (
    "wikimedia", "commons", "nasa", "pexels", "pixabay", "coverr",
    "archive.org", "archive", "loc.gov", "loc", "openverse",
)

# ⚠ INDIRME IZNI ve KULLANIM KOSULLARI ACIK OLMAYAN platformlar.
# Bu platformlarda video ACIKLAMASINDAKI lisans beyani TEK BASINA YETMEZ:
# yukleyen kisi eseri lisanslama hakkina sahip olmayabilir ve platformun
# kullanim kosullari indirmeyi AYRICA kisitlar.
IZIN_KANITI_ZORUNLU_PLATFORM = (
    "youtube.com", "youtu.be", "vimeo.com", "dailymotion.com",
    "tiktok.com", "instagram.com", "facebook.com", "twitter.com", "x.com",
    "reddit.com", "pinterest.com",
)

# Bu platformlarda kabul icin AYRICA gereken ACIK izin kanitlari.
PLATFORM_IZIN_KANITI = ("indirme_izni", "tos_uyumu", "hak_sahibi_dogrulandi")


def _metin(v) -> str:
    return str(v or "").strip()


def _host(url: str) -> str:
    try:
        return (urlparse(_metin(url)).hostname or "").lower().lstrip("www.")
    except Exception:
        return ""


def platform_gerekli_mi(kaynak_url: str, saglayici: str) -> bool:
    """Bu kaynak, ACIK indirme izni kaniti gerektiren bir platform mu?"""
    h = _host(kaynak_url)
    s = _metin(saglayici).lower()
    for p in IZIN_KANITI_ZORUNLU_PLATFORM:
        kok = p.split(".")[0]
        if h == p or h.endswith("." + p) or s == kok or s == p:
            return True
    return False


def _teknik_kanit(teknik) -> tuple[dict, list]:
    """ffprobe ile OLCULEN teknik kanit — eksik/gecersizse RAPOR EDILIR."""
    t = teknik if isinstance(teknik, dict) else {}
    eksik = []
    codec = _metin(t.get("codec") or t.get("codec_name"))
    if not codec:
        eksik.append("codec")
    g, y = t.get("genislik"), t.get("yukseklik")
    coz = None
    try:
        gi, yi = int(g), int(y)
        if gi > 0 and yi > 0:
            coz = (gi, yi)
    except (TypeError, ValueError):
        coz = None
    if coz is None:
        eksik.append("cozunurluk")
    br = None
    try:
        b = int(t.get("bitrate") or t.get("bit_rate") or 0)
        if b > 0:
            br = b
    except (TypeError, ValueError):
        br = None
    if br is None:
        eksik.append("bitrate")
    return {"codec": codec, "cozunurluk": coz, "bitrate": br}, eksik


def video_provenance_karari(kayit: dict, saglayici: str, *,
                            teknik: Optional[dict] = None,
                            indirme_zamani: Optional[str] = None) -> dict:
    """Bir VIDEO adayinin kabul edilip edilemeyecegi.

    ⚠ YALNIZ ENGELLER: once mevcut `lisans_karari()` calisir; o REDDETTIYSE
    karar REDDIR ve burada CEVRILMEZ. Gecmisse video icin EK kanitlar aranir.

    Doner: lisans_karari alanlari + {video_kabul, red_nedeni, eksik_kanit,
    uyarilar, kanit, platform}.
    ⚠ `video_kabul` True DONMEDIKCE varlik indirilmemeli/kullanilmamalidir.
    """
    k = kayit if isinstance(kayit, dict) else {}

    # ── 1) MEVCUT LISANS DUVARI (GEVSETILMEZ, ATLANMAZ) ──
    temel = lisans_karari(k, saglayici)
    sonuc = dict(temel)
    sonuc.update({"sema": SEMA_SURUM, "video_kabul": False,
                  "eksik_kanit": [], "uyarilar": []})

    kaynak_url = _metin(k.get("orijinal_url") or k.get("kaynak_url"))
    lisans_kaydi = _metin(k.get("lisans_kaydi") or k.get("lisans_url")
                          or temel.get("lisans_url"))
    zaman = _metin(indirme_zamani or k.get("indirme_zamani"))
    tek, tek_eksik = _teknik_kanit(teknik if teknik is not None
                                   else k.get("teknik"))

    sonuc["kanit"] = {
        "kaynak_url": kaynak_url, "saglayici": _metin(saglayici),
        "lisans_turu": _metin(temel.get("lisans")),
        "lisans_kaydi": lisans_kaydi, "indirme_zamani": zaman,
        "codec": tek["codec"], "cozunurluk": tek["cozunurluk"],
        "bitrate": tek["bitrate"],
    }
    platform = platform_gerekli_mi(kaynak_url, saglayici)
    sonuc["platform"] = {
        "izin_kaniti_zorunlu": platform,
        "host": _host(kaynak_url),
        "beyan_tek_basina_yeterli": False,
    }

    if temel.get("render_kullanilabilir") is not True:
        sonuc["red_nedeni"] = (_metin(temel.get("red_nedeni"))
                               or "lisans duvari reddetti")
        return sonuc

    # ── 2) ZORUNLU KANITLAR ──
    eksik = []
    if not kaynak_url or _host(kaynak_url) == "":
        eksik.append("kaynak_url")
    if not _metin(saglayici):
        eksik.append("saglayici")
    if _metin(temel.get("lisans")) in ("", "unknown"):
        eksik.append("lisans_turu")
    if not lisans_kaydi:
        eksik.append("lisans_kaydi")
    if not zaman:
        eksik.append("indirme_zamani")
    eksik.extend(tek_eksik)
    sonuc["eksik_kanit"] = eksik

    # ── 3) PLATFORM KURALI (YouTube ve benzerleri) ──
    # ⚠ Video aciklamasindaki lisans beyani TEK BASINA YETERLI SAYILMAZ.
    if platform:
        eksik_izin = [a for a in PLATFORM_IZIN_KANITI if k.get(a) is not True]
        sonuc["platform"]["eksik_izin_kaniti"] = eksik_izin
        if eksik_izin:
            sonuc["uyarilar"].append(
                "PLATFORM-IZIN-KANITI-YOK: kullanim kosullari ve indirme "
                "izni ACIK degil; aciklamadaki lisans beyani tek basina "
                "yeterli SAYILMAZ")
            sonuc["red_nedeni"] = (
                f"{_host(kaynak_url) or _metin(saglayici)}: indirme izni / "
                f"kullanim kosullari kaniti eksik ({', '.join(eksik_izin)})")
            return sonuc
        if lisans_kaydi and _host(lisans_kaydi) == _host(kaynak_url):
            # Lisans "kaydi" olarak yine izleme sayfasinin kendisi verilmis:
            # bu bir BEYANDIR, bagimsiz bir lisans kaydi DEGILDIR.
            sonuc["uyarilar"].append(
                "PLATFORM-LISANS-KAYDI-BEYAN: lisans kaydi olarak videonun "
                "kendi sayfasi gosterilmis; bagimsiz kayit DEGIL")
            sonuc["red_nedeni"] = ("lisans kaydi bagimsiz degil "
                                   "(videonun kendi sayfasi)")
            return sonuc

    if eksik:
        sonuc["red_nedeni"] = f"video kaniti eksik: {', '.join(eksik)}"
        return sonuc

    # ── 4) KABUL ──
    sonuc["video_kabul"] = True
    sonuc["red_nedeni"] = ""
    if not platform and _metin(saglayici).lower() not in \
            LISANS_KAYDI_VEREN_SAGLAYICI:
        # Kabul ediliyor (kanitlarin hepsi var) ama saglayici taninmiyor —
        # bu SESSIZ GECMEMELI.
        sonuc["uyarilar"].append(
            f"SAGLAYICI-TANINMIYOR: '{saglayici}' lisans kaydi veren bilinen "
            f"saglayicilar arasinda degil; kanitlar elle dogrulanmali")
    return sonuc


def kapsam_ozeti() -> dict:
    """Bu modulun NE ENGELLEDIGI sayilabilir olsun."""
    return {
        "sema_surum": SEMA_SURUM,
        "zorunlu_kanit": list(VIDEO_ZORUNLU_KANIT),
        "izin_kaniti_zorunlu_platform": list(IZIN_KANITI_ZORUNLU_PLATFORM),
        "platform_izin_kaniti": list(PLATFORM_IZIN_KANITI),
        "yalniz_engeller": True,
        "gorsel_yolunu_degistirir": False,
        "aga_cikar": False,
        "edinim_hattina_bagli": False,   # ⚠ J-4'te BILEREK baglanmadi
        "not": ("yalniz VIDEO adaylari icin EK sart; lisans_karari()'nin "
                "reddini ASLA cevirmez"),
    }
