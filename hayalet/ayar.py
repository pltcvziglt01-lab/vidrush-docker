#!/usr/bin/env python3
"""HAYALET — masaustu uretim ajani. AYARLAR.

⚠ SIR REPODA DEGIL: Telegram token ve diger sirlar `~/.hayalet/gizli.env`
dosyasindan okunur. Bu dosya git'e GIRMEZ.

Klasor duzeni (her is icin):
  ~/Desktop/Hayalet/<is_adi>/
      videolar/     Flow'dan inen video klipler (sirali)
      gorseller/    Flow'dan inen gorseller (sirali)
      is.json       islem kunyesi (prompt'lar, durum, hatalar)

⚠ KAPSAM: KURGU/EDIT YOK. Bu ajan yalnizca URETIR, INDIRIR, KLASORLER;
montaji kullanici kendi araciyla yapar (kullanici karari, 20 Agu 2026).
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
CHROME_CDP = os.environ.get("HAYALET_CHROME_CDP", "http://127.0.0.1:9222")
FLOW_URL = os.environ.get("HAYALET_FLOW_URL", "https://labs.google/fx/tools/flow")
# Tek uretimin en fazla bekleme suresi (sn). Veo klipleri dakikalar surebiliyor.
FLOW_URETIM_TAVAN_SN = int(os.environ.get("HAYALET_FLOW_TAVAN", "900"))

def is_dizini(is_adi: str) -> Path:
    """Is klasorunu KURAR ve doner."""
    d = KOK / is_adi
    for alt in ("videolar", "gorseller"):
        (d / alt).mkdir(parents=True, exist_ok=True)
    return d


def eksik_ayarlar() -> list:
    """Calistirmadan ONCE bilinmesi gerekenler — sessiz basarisizlik YOK."""
    eksik = []
    if not TELEGRAM_TOKEN:
        eksik.append("HAYALET_TELEGRAM_TOKEN (BotFather'dan alinip "
                     f"{GIZLI_ENV} icine yazilmali)")
    return eksik
