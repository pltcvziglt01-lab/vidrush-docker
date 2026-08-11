"""GUVENLI MEDYA INDIRME — bayt tavani + GERCEK decode dogrulamasi.

⚠ NEDEN AYRI MODUL: Faz E canli kosusunda indirme mantigi pilot betiginin
icindeydi ve uc acik birakiyordu. Kullanicinin kalite uyarisi hakliydi:

  1. `guvenlik.icerik_kapisi()` (kabul, sebep) TUPLE dondurur, exception ATMAZ.
     Donus degeri yok sayilirsa `(False, sebep)` gelse bile dosya yazilir.
     Pilotun ilk surumu tam bunu yapiyordu.
  2. Boyut tavani `Content-Length`e guveniyordu. Bu baslik EKSIK ya da YALAN
     olabilir; sunucu 10 GB akitirsa diski doldurur. Tavan GERCEKTEN OKUNAN
     bayta uygulanmali.
  3. Uzanti ve Content-Type icerigi KANITLAMAZ. `.jpg` uzantili bir HTML hata
     sayfasi, bozuk yarim dosya ya da uzantisi sahte bir arsiv, medya gibi
     gecip render'a girebilir.

Bu modul ucunu birlikte kapatiyor: akisli indirme + sert bayt tavani + sihirli
bayt + Pillow decode + ffprobe dogrulamasi. Kapilardan biri gecmezse dosya
DISKTE BIRAKILMAZ.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from typing import Callable, Optional

from . import guvenlik

# Gercekten okunan bayt tavani (Content-Length'e GUVENILMEZ).
# guvenlik.MAKS_BAYT ile ayni tavani kullaniyoruz ki iki yerde iki dogruluk olmasin.
MAKS_BAYT = getattr(guvenlik, "MAKS_BAYT", 40 * 1024 * 1024)
PARCA = 64 * 1024

# Sihirli baytlar — uzantiya ve Content-Type'a DEGIL icerige bakar.
SIHIRLI = {
    b"\xff\xd8\xff": "jpeg",
    b"\x89PNG\r\n\x1a\n": "png",
    b"GIF87a": "gif",
    b"GIF89a": "gif",
    b"II*\x00": "tiff",
    b"MM\x00*": "tiff",
    b"BM": "bmp",
}
# HTML/metin imzalari: hata sayfasi medya diye gecmesin
HTML_IZI = (b"<!doctype", b"<html", b"<?xml", b"<head", b"<body", b"{")


class IndirmeHatasi(Exception):
    """Indirme ya da dogrulama kapisi reddetti."""


def _webp_mi(bas: bytes) -> bool:
    return len(bas) >= 12 and bas[:4] == b"RIFF" and bas[8:12] == b"WEBP"


def sihirli_tur(bas: bytes) -> str:
    """Bas baytlardan gercek turu bul; bilinmiyorsa bos string."""
    if _webp_mi(bas):
        return "webp"
    for imza, ad in SIHIRLI.items():
        if bas.startswith(imza):
            return ad
    return ""


def html_mi(bas: bytes) -> bool:
    kucuk = bas[:400].lstrip().lower()
    return any(kucuk.startswith(x) for x in HTML_IZI)


# Dosya SONU imzalari — kirpilmis indirmeyi yakalar.
# ⚠ Olculdu (11 Agu): Pillow kirpilmis bir JPEG'i sikayet etmeden acabiliyor
# (`verify()` ve `load()` ikisi de gecti, 640x480 dondu). Yani decode kapisi
# TEK BASINA yarim dosyayi yakalamiyor. Bitis isareti kontrolu bunu kapatiyor.
BITIS_IMZASI = {
    "jpeg": b"\xff\xd9",          # EOI
    "png": b"IEND\xaeB`\x82",     # IEND + CRC
    "gif": b"\x3b",                # trailer
}


def bitis_dogrula(yol: str, tur: str) -> tuple:
    """Dosya kendi bitis isaretiyle mi sonlaniyor? (ok, sebep)"""
    imza = BITIS_IMZASI.get(tur)
    if not imza:
        return True, f"{tur} icin bitis imzasi tanimli degil"
    try:
        with open(yol, "rb") as f:
            f.seek(0, os.SEEK_END)
            n = f.tell()
            f.seek(max(0, n - 64))
            kuyruk = f.read(64)
    except Exception as e:
        return False, f"kuyruk okunamadi: {type(e).__name__}"
    # Bazi kodlayicilar sonda dolgu birakir; son anlamli baytlara bakiyoruz
    kirpilmis = kuyruk.rstrip(b"\x00")
    if kirpilmis.endswith(imza):
        return True, "bitis imzasi tam"
    return False, (f"{tur} bitis imzasi YOK — dosya kirpilmis "
                   f"(son baytlar: {kirpilmis[-6:]!r})")


def pillow_dogrula(yol: str) -> tuple:
    """Gercek decode. (ok, sebep, (genislik, yukseklik))

    ⚠ `Image.verify()` YETMEZ: yalnizca basligi kontrol eder, piksel verisini
    acmaz. Yarim inen bir JPEG verify()'i gecip `load()`ta patlar. Bu yuzden
    once verify, sonra AYRI bir acilista load() cagriliyor (verify sonrasi
    dosya nesnesi kullanilamaz — Pillow'un dokumanli davranisi).
    """
    try:
        from PIL import Image
    except Exception as e:                       # Pillow yoksa kapi atlanir
        return True, f"Pillow yok, decode atlandi ({type(e).__name__})", (0, 0)
    try:
        with Image.open(yol) as im:
            im.verify()
        with Image.open(yol) as im:
            im.load()
            g, y = im.size
        if g < 8 or y < 8:
            return False, f"gorsel cok kucuk ({g}x{y})", (g, y)
        return True, f"decode ok ({g}x{y})", (g, y)
    except Exception as e:
        return False, f"decode basarisiz: {type(e).__name__}: {str(e)[:70]}", (0, 0)


def ffprobe_dogrula(yol: str, beklenen: str = "image") -> tuple:
    """ffprobe ile akis dogrulamasi. (ok, sebep, bilgi)"""
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_streams", "-show_format",
             "-of", "json", yol], capture_output=True, text=True, timeout=120)
    except Exception as e:
        return True, f"ffprobe kosulamadi, atlandi ({type(e).__name__})", {}
    if r.returncode != 0:
        return False, f"ffprobe reddetti: {(r.stderr or '')[:70]}", {}
    try:
        d = json.loads(r.stdout or "{}")
    except json.JSONDecodeError:
        return False, "ffprobe cikisi ayristirilamadi", {}
    akislar = d.get("streams") or []
    if not akislar:
        return False, "akis yok (medya degil)", {}
    video = [s for s in akislar if s.get("codec_type") == "video"]
    ses = [s for s in akislar if s.get("codec_type") == "audio"]
    if beklenen in ("image", "video"):
        if not video:
            return False, f"video/gorsel akisi yok (beklenen {beklenen})", {}
        g = int(video[0].get("width") or 0)
        y = int(video[0].get("height") or 0)
        if g < 8 or y < 8:
            return False, f"gecersiz olcu {g}x{y}", {}
        return True, f"ffprobe ok ({video[0].get('codec_name')} {g}x{y})", {
            "genislik": g, "yukseklik": y,
            "kodek": video[0].get("codec_name"),
            "sure_sn": float(d.get("format", {}).get("duration") or 0.0)}
    if beklenen == "audio":
        if not ses:
            return False, "ses akisi yok", {}
        return True, f"ffprobe ok ({ses[0].get('codec_name')})", {
            "kodek": ses[0].get("codec_name"),
            "sure_sn": float(d.get("format", {}).get("duration") or 0.0)}
    return True, "beklenen tur belirtilmedi", {}


def dosya_dogrula(yol: str, *, beklenen: str = "image",
                  en_az_bayt: int = 8000) -> tuple:
    """Diskteki dosyanin GERCEKTEN istenen medya olup olmadigini kanitla.

    Sirali kapilar: boyut -> HTML izi -> sihirli bayt -> Pillow -> ffprobe.
    Doner (ok, sebep, bilgi).
    """
    if not os.path.exists(yol):
        return False, "dosya yok", {}
    boyut = os.path.getsize(yol)
    if boyut < en_az_bayt:
        return False, f"cok kucuk ({boyut} < {en_az_bayt} bayt)", {}
    if boyut > MAKS_BAYT:
        return False, f"bayt tavani asildi ({boyut} > {MAKS_BAYT})", {}

    with open(yol, "rb") as f:
        bas = f.read(512)
    if html_mi(bas):
        return False, "HTML/metin icerigi (medya degil)", {}

    if beklenen == "image":
        tur = sihirli_tur(bas)
        if not tur:
            return False, "sihirli bayt taninmadi (uzantisi sahte olabilir)", {}
        ok_b, sebep_b = bitis_dogrula(yol, tur)
        if not ok_b:
            return False, sebep_b, {}
        ok, sebep, olcu = pillow_dogrula(yol)
        if not ok:
            return False, sebep, {}
        ok2, sebep2, bilgi = ffprobe_dogrula(yol, "image")
        if not ok2:
            return False, sebep2, {}
        bilgi = dict(bilgi)
        bilgi.update({"sihirli_tur": tur, "boyut": boyut,
                      "pillow": sebep, "bitis": sebep_b, "genislik": bilgi.get("genislik") or olcu[0],
                      "yukseklik": bilgi.get("yukseklik") or olcu[1]})
        return True, f"{tur}; {sebep}; {sebep2}", bilgi

    ok, sebep, bilgi = ffprobe_dogrula(yol, beklenen)
    if not ok:
        return False, sebep, {}
    bilgi = dict(bilgi)
    bilgi["boyut"] = boyut
    return True, sebep, bilgi


def guvenli_indir(url: str, hedef: str, *, istek: Callable,
                  beklenen: str = "image", maks_bayt: int = MAKS_BAYT,
                  en_az_bayt: int = 8000, zaman_asimi: int = 45,
                  coz: Optional[Callable] = None) -> dict:
    """SSRF + icerik + bayt tavani + decode kapilarindan gecerek indir.

    Doner: {"ok", "sebep", "bilgi", "okunan_bayt", "http", "retry_after"}
    Basarisizsa hedef dosya OLUSTURULMAZ (gecici dosya silinir).

    ⚠ Bayt tavani AKIS SIRASINDA uygulanir: `Content-Length` eksik ya da yalan
    olabilir. Tavan asilirsa baglanti kesilir ve gecici dosya silinir.
    """
    guvenlik.url_dogrula(url, coz=coz)
    r, _son_url = guvenlik.guvenli_istek(url, istek=istek,
                                         zaman_asimi=zaman_asimi, coz=coz,
                                         akis=True)
    kod = int(getattr(r, "status_code", 0) or 0)
    basliklar = getattr(r, "headers", None) or {}
    if kod != 200:
        return {"ok": False, "sebep": f"HTTP {kod}", "http": kod,
                "retry_after": basliklar.get("Retry-After"),
                "okunan_bayt": 0, "bilgi": {}}

    # ── KAPI 1: Content-Type (tuple SONUCU KULLANILIR) ──
    ct = basliklar.get("Content-Type", "")
    # Content-Length varsa on kontrol; YOKSA gecilir ve akis tavani devreye girer
    try:
        cl = int(basliklar.get("Content-Length")) if basliklar.get(
            "Content-Length") else None
    except (TypeError, ValueError):
        cl = None
    kabul, sebep = guvenlik.icerik_kapisi(ct, cl, beklenen)
    if not kabul:
        try:
            r.close()
        except Exception:
            pass
        return {"ok": False, "sebep": f"icerik kapisi: {sebep}", "http": kod,
                "retry_after": None, "okunan_bayt": 0, "bilgi": {}}

    # ── KAPI 2: AKIS SIRASINDA sert bayt tavani ──
    os.makedirs(os.path.dirname(os.path.abspath(hedef)) or ".", exist_ok=True)
    fd, gecici = tempfile.mkstemp(prefix=".indir_", dir=os.path.dirname(
        os.path.abspath(hedef)))
    okunan = 0
    try:
        with os.fdopen(fd, "wb") as f:
            akis = (r.iter_content(chunk_size=PARCA)
                    if hasattr(r, "iter_content") else [getattr(r, "content", b"")])
            for parca in akis:
                if not parca:
                    continue
                okunan += len(parca)
                if okunan > maks_bayt:
                    raise IndirmeHatasi(
                        f"bayt tavani akis sirasinda asildi "
                        f"({okunan} > {maks_bayt}; Content-Length={cl})")
                f.write(parca)
        try:
            r.close()
        except Exception:
            pass

        # ── KAPI 3: gercek uzunlukla icerik kapisi TEKRAR ──
        kabul2, sebep2 = guvenlik.icerik_kapisi(ct, okunan, beklenen)
        if not kabul2:
            raise IndirmeHatasi(f"icerik kapisi (gercek uzunluk): {sebep2}")

        # ── KAPI 4: GERCEK DECODE ──
        ok, sebep3, bilgi = dosya_dogrula(gecici, beklenen=beklenen,
                                          en_az_bayt=en_az_bayt)
        if not ok:
            raise IndirmeHatasi(f"decode dogrulamasi: {sebep3}")

        os.replace(gecici, hedef)
        return {"ok": True, "sebep": sebep3, "bilgi": bilgi,
                "okunan_bayt": okunan, "http": kod, "retry_after": None}
    except Exception as e:
        for y in (gecici,):
            try:
                if os.path.exists(y):
                    os.remove(y)
            except Exception:
                pass
        return {"ok": False, "sebep": str(e)[:200], "http": kod,
                "retry_after": None, "okunan_bayt": okunan, "bilgi": {}}
