#!/usr/bin/env python3
"""FAZ UI-2 — UZAK ON KONTROL (staging konteyneri icinde kosar).

Gorevi TEK: uzak tarayici hattinin (`ui2_uzak_akis.mjs`) ihtiyaci olan
CREDENTIALSIZ test oturumunu ve KREDISIZ is kimligini hazirlamak.

⚠ CREDENTIAL YOK. Kullanici adi/parola OKUNMAZ, URETILMEZ, YAZDIRILMAZ.
  Oturum jetonu sunucunun DISKTEKI MEVCUT anahtariyla uretilir
  (`teslim.anahtar_kur(..., uret=False)`) — YENI anahtar URETILMEZ,
  boylece canli oturumlar gecersiz kilinmaz.
⚠ KIMLIK SIZINTISI YOK. stdout'a yalnizca ANONIM sayi, alan adi ve
  MASKELI (sha256[:8]) kimlik cikar. Jeton yalnizca 0600 izinli ayar
  dosyasina yazilir.
⚠ HICBIR SEY URETILMEZ: kuyruga is ATILMAZ, kredi HARCANMAZ.

Cikis kodlari (stabil):
  0 hazir · 2 UI2-OTURUM-ANAHTARI-YOK · 3 UI2-BITMIS-IS-YOK
  4 UI2-STAGING-TEST-SESSION-YOK
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import sys

WEBAPP = os.environ.get("UI2_WEBAPP", "/opt/vidrush/webapp")
VERI = os.path.join(WEBAPP, "veri")
DURUMLAR = os.path.join(VERI, "durumlar")
CIKTILAR = os.environ.get("UI2_CIKTILAR", os.path.join(WEBAPP, "ciktilar"))
KANIT = os.environ.get("UI2_KANIT", "/tmp/ui2_kanit/kosu")
TABAN = os.environ.get("UI2_TABAN", "http://127.0.0.1:8080")
# ⚠ Jetonu tasiyan ayar dosyasi KANIT dizinine YAZILMAZ: kanit dizini
# staging host'una tasinir, jeton orada kalmamalidir.
AYAR_YOLU = os.environ.get("UI2_AYAR", "/tmp/ui2_hat/ayar.json")
# Belirli bir isi sabitlemek icin (varsayilan: en yeni uygun is).
IS_ZORLA = os.environ.get("UI2_IS_ID", "")

sys.path.insert(0, WEBAPP)


def maske(d) -> str:
    """Kimlikleri raporda AYIRT EDILEBILIR ama GERI COZULEMEZ yap."""
    return hashlib.sha256(str(d or "").encode("utf-8")).hexdigest()[:8]


def kod_cik(kod: str, kabuk: int) -> None:
    print(f"UI2_KOD={kod}")
    sys.exit(kabuk)


import kimlik      # noqa: E402
import teslim      # noqa: E402

# ── 1) MEVCUT oturum anahtari (YENI URETME) ──────────────────────────────
if not teslim.anahtar_kur(VERI, uret=False):
    kod_cik("UI2-OTURUM-ANAHTARI-YOK", 2)
if not kimlik.kdf_hazir():
    kod_cik("UI2-STAGING-TEST-SESSION-YOK", 4)

# ── 2) KREDISIZ is: ZATEN BITMIS, tenant'a muhurlu, videosu diskte ───────
# ⚠ Yeni is BASLATILMAZ. Zincirin "uretim/kalite/indirme" halkalari
# MEVCUT bir isin GERCEK verisiyle olculur; boylece $0.00 harcanir.
durum_dosyalari = sorted(glob.glob(os.path.join(DURUMLAR, "*.json")))
adaylar = []
for yol in durum_dosyalari:
    try:
        with open(yol, encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        continue
    tid = str(d.get("tenant_id") or "")
    video = str(d.get("video") or "")
    if not tid or not video:
        continue
    if str(d.get("durum") or "") not in ("bitti", "tamam", "done"):
        continue
    ad = os.path.basename(video)
    if not os.path.isfile(os.path.join(CIKTILAR, ad)):
        continue
    adaylar.append((os.path.getmtime(yol), os.path.basename(yol)[:-5], tid, ad))

print(f"DURUM_DOSYA_SAYISI={len(durum_dosyalari)}")
print(f"KREDISIZ_ADAY_SAYISI={len(adaylar)}")
if not adaylar:
    kod_cik("UI2-BITMIS-IS-YOK", 3)

adaylar.sort()
secim = ([a for a in adaylar if a[1] == IS_ZORLA] or [adaylar[-1]])[-1]
_, is_id, tenant_id, video_ad = secim

# ── 3) CREDENTIALSIZ oturum jetonu ───────────────────────────────────────
try:
    jeton = kimlik.oturum_uret(tenant_id, anahtar=teslim.anahtar())
except Exception:
    jeton = ""
if not jeton:
    kod_cik("UI2-STAGING-TEST-SESSION-YOK", 4)
# Uretilen jeton GERCEKTEN gecerli mi — kapiya sorulur (fail-closed).
if not teslim.oturum_kapisi(jeton)["izin"]:
    kod_cik("UI2-STAGING-TEST-SESSION-YOK", 4)

# ── 4) AYAR dosyasi (0600) — jeton YALNIZ burada ─────────────────────────
os.makedirs(KANIT, exist_ok=True)
os.makedirs(os.path.dirname(AYAR_YOLU), exist_ok=True)
ayar = {
    "taban": TABAN,
    "cerez_adi": kimlik.OTURUM_COOKIE,
    "jeton": jeton,
    "is_id": is_id,
    "durumlar_dizini": DURUMLAR,
    "kanit_dizini": KANIT,
    "tenant_maske": maske(tenant_id),
    "is_maske": maske(is_id),
}
ayar_yolu = AYAR_YOLU
fd = os.open(ayar_yolu, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
with os.fdopen(fd, "w", encoding="utf-8") as f:
    json.dump(ayar, f)

# ── 5) ANONIM rapor ──────────────────────────────────────────────────────
print(f"TENANT_MASKE={ayar['tenant_maske']}")
print(f"IS_MASKE={ayar['is_maske']}")
print(f"VIDEO_VAR={os.path.isfile(os.path.join(CIKTILAR, video_ad))}")
print(f"AYAR_IZIN={oct(os.stat(ayar_yolu).st_mode & 0o777)}")
print("UI2_KOD=HAZIR")
