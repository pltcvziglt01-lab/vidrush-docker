#!/usr/bin/env python3
"""MAGNIFIC MOTORU — tek akis icin gorsel + video ureticisi (20 Agu 2026).

⚠ NEDEN VAR: urun karari — "tum sistem Magnific'ten". Olculen gercekler:
  · nano-banana-pro-flash: tek cagrida 2752x1536 NATIVE 16:9 (olculdu,
    /tmp/nb.jpg 7.7MB). Eski hattin 1536x1024 uretip 1536x864'e kirpma
    zorunlulugu ve Magnific upscale adimi BURADA GEREKSIZLESIR.
  · image-to-video uclari anahtarimizla ACIK (olculdu, sahte task-id GET
    -> 404 "Task not found"): kling-v2-5-pro, minimax-hailuo-02,
    pixverse-v5, wan-v2-2, runway-gen4-turbo, veo-3-1.
  · Video klip PAHALI (~$0.25-0.50 / 5sn) — gorselin 3-5 kati. Bu yuzden
    klip uretimi VIDEO BASINA SERT TAVANLIDIR (asagida IsButcesi).

TASARIM KURALLARI (kaynak.py ile ayni okul):
  1. HATTI COKERTMEZ: her hata yakalanir, False/None doner; cagiran
     OpenAI gorsel yoluna ya da efektli fotografa duser.
  2. KREDI BITTI != GECICI HATA: 401/402/403 ve "consuming credits"
     iceren 5xx KALICIDIR -> is boyunca kapanir (bosa cagri yok).
  3. SESSIZ DUSUS YOK: her dusus stderr'e nedeniyle yazilir ve
     `durum()` ozeti is sozlugune cikabilir.
  4. UYDURMA SAYI YOK: harcama sayaclari yalnizca BASARILI istekten artar.
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time

import requests

# kaynak.py ile AYNI anahtar zinciri: FREEPIK_KEYS > (dosya > MAGNIFIC_KEY).
# ⚠ Tek-anahtar yolunda DOSYA env'i YENER (kaynak._magnific_anahtar ile ayni
# karar): Config.Env'e gomulu anahtar panelden silindi; rotasyon mount'lu
# veri/magnific_key.txt uzerinden, konteyner yeniden yaratmadan yapilir.
def _anahtarlar() -> list:
    coklu = [a.strip() for a in os.environ.get("FREEPIK_KEYS", "").split(",")
             if a.strip()]
    if coklu:
        return coklu
    tek = ""
    try:
        _kok = os.environ.get("VIDRUSH_KOK", "/opt/vidrush")
        _d = os.environ.get("ANAHTAR_DIZIN",
                            os.path.join(_kok, "webapp", "veri"))
        with open(os.path.join(_d, "magnific_key.txt")) as f:
            tek = f.read().strip()
    except Exception:
        pass
    tek = tek or os.environ.get("MAGNIFIC_KEY", "").strip()
    return [tek] if tek else []


TABAN = os.environ.get("MAG_API_TABAN", "https://api.freepik.com/v1/ai")

# ── GORSEL ──
GORSEL_MODEL = os.environ.get("MAG_GORSEL_MODEL", "nano-banana-pro-flash")
GORSEL_COZUNURLUK = os.environ.get("MAG_GORSEL_COZUNURLUK", "2K")
GORSEL_POLL_SN = 6
GORSEL_TAVAN_SN = int(os.environ.get("MAG_GORSEL_TAVAN_SN", "180"))

# ── VIDEO KLIP ──
# Varsayilan motor MiniMax 768p: olculen ucuncu-taraf fiyat ~$0.04/sn —
# Kling'in ~yarisi. Kalite oncelikliyse env ile kling-v2-5-pro secilir.
VIDEO_MODEL = os.environ.get("MAG_VIDEO_MODEL", "minimax-hailuo-02-768p")
VIDEO_POLL_SN = 10
VIDEO_TAVAN_SN = int(os.environ.get("MAG_VIDEO_TAVAN_SN", "420"))
# VIDEO BASINA en fazla kac AI klip (maliyet sigortasi — SORA_KLIP_MAKS
# deseninin aynisi). 0 = klip uretimi tamamen kapali.
KLIP_MAKS = int(os.environ.get("MAG_KLIP_MAKS", "10"))

_KALICI_KAPALI = False      # kredi/yetki bitti -> surec boyunca kapali
_5XX = 0                    # ust uste sunucu hatasi sayaci
_kilit = threading.Lock()


class IsButcesi:
    """VIDEO BASINA sayac. Modul duzeyinde paylasilan sayac YOK —
    ayni surecte iki is kosarsa sayaclar birbirine karismaz
    (medya_kopru.is_butcesi_kur ile ayni ders)."""

    def __init__(self, is_adi: str):
        self.is_adi = is_adi
        self.gorsel = 0
        self.klip = 0
        self.dususler = []
        self._kilit = threading.Lock()

    def klip_hakki_var(self) -> bool:
        with self._kilit:
            return self.klip < KLIP_MAKS

    def ozet(self) -> dict:
        return {"gorsel": self.gorsel, "klip": self.klip,
                "klip_tavani": KLIP_MAKS, "dususler": list(self.dususler)}


def var() -> bool:
    return bool(_anahtarlar()) and not _KALICI_KAPALI


def _hata_isle(r, baglam: str) -> None:
    """401/402/403 + kredi-bitti-5xx KALICI kapatir; diger 5xx sayilir."""
    global _KALICI_KAPALI, _5XX
    govde = (r.text or "")[:160]
    print(f"  magnific {baglam} HTTP {r.status_code}: {govde}", file=sys.stderr)
    with _kilit:
        if r.status_code in (401, 402, 403):
            _KALICI_KAPALI = True
            print("  magnific: yetki/kredi sorunu -> surec boyunca KAPALI",
                  file=sys.stderr)
        elif r.status_code >= 500 and "consuming credits" in govde.lower():
            _KALICI_KAPALI = True
            print("  magnific: kredi bitti (Freepik) -> surec boyunca KAPALI",
                  file=sys.stderr)
        elif r.status_code >= 500:
            _5XX += 1
            if _5XX >= 3:
                _KALICI_KAPALI = True
                print("  magnific: ust uste 5xx -> surec boyunca KAPALI",
                      file=sys.stderr)


def _bekle_ve_indir(uc: str, tid: str, hedef: str, anahtar: str,
                    poll_sn: int, tavan_sn: int) -> bool:
    """task poll -> COMPLETED -> ilk cikti dosyaya. Gecici poll hatasi
    task'i TERK ETMEZ (kaynak.magnific_upscale ile ayni sabir)."""
    h = {"x-freepik-api-key": anahtar}
    bas = time.time()
    while time.time() - bas < tavan_sn:
        time.sleep(poll_sn)
        try:
            d = requests.get(f"{TABAN}/{uc}/{tid}", headers=h,
                             timeout=30).json().get("data", {})
        except Exception:
            continue
        durum = d.get("status")
        if durum == "COMPLETED" and d.get("generated"):
            resp = requests.get(d["generated"][0], timeout=300)
            resp.raise_for_status()
            if len(resp.content) < 10000:      # HTML/bozuk yanit -> basarisiz
                return False
            tmp = hedef + ".mag.tmp"
            with open(tmp, "wb") as f:
                f.write(resp.content)
            os.replace(tmp, hedef)             # atomik: yarim dosya kalmaz
            return True
        if durum == "FAILED":
            print(f"  magnific {uc} FAILED: {str(d.get('error'))[:120]}",
                  file=sys.stderr)
            return False
    print(f"  magnific {uc} zaman asimi ({tavan_sn}s)", file=sys.stderr)
    return False


def gorsel_uret(prompt: str, hedef: str, referanslar: list = None,
                butce: IsButcesi = None) -> bool:
    """Nano Banana ile 16:9 sahne gorseli. Basarida hedefe yazar, True.

    referanslar: karakter/capa/stil gorsel yollari (en fazla 14; biz 4
    gecirmeyiz). Base64 URI olarak gider — nano-banana coklu referansi
    NATIVE destekler (OpenAI edits zincirimizden daha genis).
    """
    global _5XX
    if _KALICI_KAPALI or not _anahtarlar() or not (prompt or "").strip():
        return False
    anahtar = _anahtarlar()[0]
    govde = {"prompt": prompt.strip()[:3000],
             "aspect_ratio": "16:9",
             "resolution": GORSEL_COZUNURLUK}
    refs = []
    import base64
    for yol in (referanslar or [])[:4]:
        try:
            if yol and os.path.exists(yol):
                with open(yol, "rb") as f:
                    refs.append("data:image/png;base64,"
                                + base64.b64encode(f.read()).decode())
        except Exception:
            continue
    if refs:
        govde["reference_images"] = refs
    try:
        r = requests.post(f"{TABAN}/text-to-image/{GORSEL_MODEL}",
                          headers={"x-freepik-api-key": anahtar,
                                   "Content-Type": "application/json"},
                          json=govde, timeout=60)
        if r.status_code >= 400:
            _hata_isle(r, "gorsel")
            return False
        with _kilit:
            _5XX = 0
        tid = r.json()["data"]["task_id"]
        ok = _bekle_ve_indir(f"text-to-image/{GORSEL_MODEL}", tid, hedef,
                             anahtar, GORSEL_POLL_SN, GORSEL_TAVAN_SN)
        if ok and butce is not None:
            with butce._kilit:
                butce.gorsel += 1
        return ok
    except Exception as e:
        print(f"  magnific gorsel hata: {str(e)[:140]}", file=sys.stderr)
        return False


def klip_uret(gorsel_yolu: str, hedef: str, prompt: str = "",
              sure_sn: int = 6, butce: IsButcesi = None) -> bool:
    """Sahne gorselini KISA VIDEO klibe cevirir (image-to-video).

    ⚠ PAHALI (~gorselin 3-5 kati). Cagiran once `butce.klip_hakki_var()`
    kontrol etmeli; burada da SON SAVUNMA olarak reddedilir — tavan iki
    kapida da tutulur (tek kapiya guven yok).
    """
    if _KALICI_KAPALI or not _anahtarlar():
        return False
    if butce is not None and not butce.klip_hakki_var():
        if "klip-tavani" not in butce.dususler:
            butce.dususler.append("klip-tavani")
            print(f"  magnific klip TAVANI doldu ({KLIP_MAKS}) -> "
                  f"kalan sahneler gorsel+motion", file=sys.stderr)
        return False
    if not (gorsel_yolu and os.path.exists(gorsel_yolu)):
        return False
    import base64
    with open(gorsel_yolu, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    govde = {"image": b64,
             "prompt": (prompt or "subtle cinematic motion, documentary "
                        "camera drift, natural movement")[:1500],
             "duration": str(int(min(10, max(5, sure_sn))))}
    try:
        r = requests.post(f"{TABAN}/image-to-video/{VIDEO_MODEL}",
                          headers={"x-freepik-api-key": _anahtarlar()[0],
                                   "Content-Type": "application/json"},
                          json=govde, timeout=90)
        if r.status_code >= 400:
            _hata_isle(r, "klip")
            return False
        tid = r.json()["data"]["task_id"]
        ok = _bekle_ve_indir(f"image-to-video/{VIDEO_MODEL}", tid, hedef,
                             _anahtarlar()[0], VIDEO_POLL_SN, VIDEO_TAVAN_SN)
        if ok and butce is not None:
            with butce._kilit:
                butce.klip += 1
        return ok
    except Exception as e:
        print(f"  magnific klip hata: {str(e)[:140]}", file=sys.stderr)
        return False


def durum() -> dict:
    """Arayuz/is sozlugu icin ozet — anahtar DEGERI asla donmez."""
    return {"acik": var(), "kalici_kapali": _KALICI_KAPALI,
            "gorsel_model": GORSEL_MODEL, "video_model": VIDEO_MODEL,
            "klip_tavani": KLIP_MAKS}
