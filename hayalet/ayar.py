#!/usr/bin/env python3
"""HAYALET — masaustu uretim ajani. AYARLAR.

⚠ SIR REPODA DEGIL: Telegram token ve diger sirlar `~/.hayalet/gizli.env`
dosyasindan okunur. Bu dosya git'e GIRMEZ.

Klasor duzeni (her is icin):
  ~/Desktop/Hayalet/<is_adi>/
      video/        Flow'dan inen video klipler (sirali)
      gorsel/       Flow'dan inen gorseller (sirali)
      is.json       islem kunyesi (prompt'lar, durum, hatalar)

⚠ KAPSAM: uretim (Flow) ile kurgu (ffmpeg) AYRI. `hayalet.kurgu` metin +
ses + cumle basina medyayi senkron tek videoya cevirir; renk/ses tasarimi
gibi ince islerde kullanici NLE'sine gecer.
"""
from __future__ import annotations

import os
from pathlib import Path

# ── Sir dosyasi (repo DISI) ──
GIZLI_DIZIN = Path.home() / ".hayalet"
GIZLI_ENV = GIZLI_DIZIN / "gizli.env"


def _gizli_yukle() -> None:
    """`~/.hayalet/gizli.env` -> ortam degiskeni. Dosya yoksa sessiz gecer."""
    if not GIZLI_ENV.exists():
        return
    for satir in GIZLI_ENV.read_text(encoding="utf-8").splitlines():
        satir = satir.strip()
        if not satir or satir.startswith("#") or "=" not in satir:
            continue
        ad, _, deger = satir.partition("=")
        os.environ.setdefault(ad.strip(), deger.strip())


_gizli_yukle()

TELEGRAM_TOKEN = os.environ.get("HAYALET_TELEGRAM_TOKEN", "")
# Yalnizca bu kullanici(lar) botu kullanabilir. Bos ise ILK yazan sahiplenir.
IZINLI_KULLANICILAR = [x.strip() for x in
                       os.environ.get("HAYALET_IZINLI", "").split(",") if x.strip()]

# ── Klasorler ──
KOK = Path(os.environ.get("HAYALET_KOK", str(Path.home() / "Desktop" / "Hayalet")))

# ── Flow (tarayici otomasyonu) ──
# ⚠ Kullanicinin KENDI Chrome'una baglaniriz: Google oturumu zaten aciktir.
# Chrome su bayrakla baslatilmali:  --remote-debugging-port=9222
CHROME_PORT = int(os.environ.get("HAYALET_CHROME_PORT", "9222"))
CHROME_CDP = os.environ.get("HAYALET_CHROME_CDP",
                            f"http://127.0.0.1:{CHROME_PORT}")
# ⚠ KALICI PROFIL: Flow oturumu burada durur. chrome_baslat.sh de, Playwright
# de AYNI dizini kullanir — boylece bir kez giris yapmak yeter.
CHROME_PROFIL = Path(os.environ.get(
    "HAYALET_CHROME_PROFIL", str(GIZLI_DIZIN / "chrome-profil")))

# ── SENIN GERCEK CHROME PROFILINI KULLANMA (istege bagli) ──
# ⚠ OLCULDU (21 Agu 2026): bir Chrome profilini kopyalayarak oturum TASINMAZ.
# macOS'ta cerez anahtari Keychain'de ve uygulamaya baglidir; kopyalanan
# profil Flow'da OTURUMSUZ acilir (tanitim sayfasi gelir). Iki gecerli yol:
#   A) IZOLE PROFIL (varsayilan): ~/.hayalet/chrome-profil icinde BIR KEZ
#      giris yaparsin. Gunluk Chrome'un acik kalabilir. Onerilen.
#   B) GERCEK PROFIL: asagidaki iki degeri doldur. O zaman gunluk Chrome'un
#      TAMAMEN KAPALI olmali (Chrome ayni veri dizinini iki surecle acmaz).
CHROME_ANA_DIZIN = os.environ.get("HAYALET_CHROME_ANA_DIZIN", "")
CHROME_PROFIL_ADI = os.environ.get("HAYALET_CHROME_PROFIL_ADI", "")
FLOW_URL = os.environ.get("HAYALET_FLOW_URL", "https://labs.google/fx/tools/flow")
# Tek uretimin en fazla bekleme suresi (sn). Veo klipleri dakikalar surebiliyor.
FLOW_URETIM_TAVAN_SN = int(os.environ.get("HAYALET_FLOW_TAVAN", "900"))

def is_dizini(is_adi: str) -> Path:
    """Is klasorunu KURAR ve doner."""
    d = KOK / is_adi
    for alt in ("video", "gorsel"):
        (d / alt).mkdir(parents=True, exist_ok=True)
    return d


def eksik_ayarlar() -> list:
    """Calistirmadan ONCE bilinmesi gerekenler — sessiz basarisizlik YOK."""
    eksik = []
    if not TELEGRAM_TOKEN:
        eksik.append("HAYALET_TELEGRAM_TOKEN (BotFather'dan alinip "
                     f"{GIZLI_ENV} icine yazilmali)")
    return eksik
