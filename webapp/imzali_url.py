#!/usr/bin/env python3
"""FAZ R-1a — IMZALI (signed) CIKTI URL'LERI.

⚠ SORUN: `/ciktilar/{dosya}` IMZASIZDI — dosya adini bilen HERKES indirebilir.
Coklu kullanici gelmeden once bile bu bir sizinti yoluydu; tenant izolasyonu
(R-1b) icin de ON KOSULDUR.

⚠ TASARIM
  · HMAC-SHA256, sabit zamanli karsilastirma (`hmac.compare_digest`).
  · TTL zorunlu: her baglanti `exp` (unix saniye) tasir ve suresi dolunca
    REDDEDILIR. Baglanti PAYLASILSA bile omru sinirlidir.
  · Anahtar ASLA kodda/repoda DEGIL: once `IMZA_ANAHTARI` env, yoksa veri
    dizininde 0600 izinli dosyadan okunur, o da yoksa URETILIR ve yazilir.
    Anahtar hicbir yerde LOGLANMAZ.
  · Anahtar YOKSA ve URETILEMIYORSA imzalama SESSIZCE devre disi kalmaz —
    `hazir()` False doner ve cagiran taraf karar verir.

⚠ Bu modul AG/MEDYA acmaz; saf kripto + yol dogrulamasi.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import time
from typing import Optional

SEMA_SURUM = "1.0.0"

# Varsayilan omur: bir isin bitisinden sonra kullanicinin indirmesine yetecek
# kadar, ama sinirsiz degil.
VARSAYILAN_TTL_SN = 6 * 3600
ANAHTAR_DOSYA_ADI = ".imza_anahtari"
ENV_ADI = "IMZA_ANAHTARI"

_ANAHTAR: Optional[bytes] = None


def _dosyadan_oku(dizin: str) -> Optional[bytes]:
    yol = os.path.join(dizin, ANAHTAR_DOSYA_ADI)
    try:
        with open(yol, "rb") as f:
            ham = f.read().strip()
        return ham or None
    except OSError:
        return None


def _dosyaya_yaz(dizin: str, anahtar: bytes) -> bool:
    yol = os.path.join(dizin, ANAHTAR_DOSYA_ADI)
    try:
        os.makedirs(dizin, exist_ok=True)
        # ⚠ 0600: yalnizca sunucu kullanicisi okuyabilsin.
        fd = os.open(yol, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(anahtar)
        return True
    except OSError:
        return False


def anahtar_kur(veri_dizini: str = "", *, uret: bool = True) -> bool:
    """Imza anahtarini env -> dosya -> (gerekirse) URET sirasiyla hazirla.

    ⚠ Anahtar DONDURULMEZ ve LOGLANMAZ. Yalnizca hazir olup olmadigi bildirilir.
    """
    global _ANAHTAR
    ham = (os.environ.get(ENV_ADI) or "").strip()
    if ham:
        _ANAHTAR = ham.encode("utf-8")
        return True
    if veri_dizini:
        d = _dosyadan_oku(veri_dizini)
        if d:
            _ANAHTAR = d
            return True
        if uret:
            yeni = secrets.token_urlsafe(48).encode("ascii")
            if _dosyaya_yaz(veri_dizini, yeni):
                _ANAHTAR = yeni
                return True
    return False


def hazir() -> bool:
    return bool(_ANAHTAR)


def _imza(dosya: str, exp: int, tenant: str = "") -> str:
    """⚠ FAZ R-1d-a: `tenant` verilirse imza mesajina KARISIR.

    Boylece baglanti SIZSA BILE baska bir tenant'in oturumunda gecersizdir.
    ⚠ GERIYE UYUMLULUK: `tenant` bos ise mesaj ESKISIYLE BIT-BIT AYNIDIR;
    R-1a'da uretilmis baglantilar aynen dogrulanmaya devam eder.
    """
    t = str(tenant or "")
    mesaj = (f"{dosya}\n{exp}\n{t}" if t else f"{dosya}\n{exp}").encode("utf-8")
    ozet = hmac.new(_ANAHTAR or b"", mesaj, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(ozet).decode("ascii").rstrip("=")


def guvenli_ad(dosya: str) -> str:
    """Yol gezinmesini (path traversal) kes: yalnizca TABAN AD kalir."""
    return os.path.basename(str(dosya or "").strip())


def imzala(dosya: str, *, ttl_sn: int = VARSAYILAN_TTL_SN,
           simdi: Optional[int] = None, tenant: str = "") -> str:
    """`ciktilar/<ad>?exp=..&sig=..` uret. Anahtar yoksa BOS doner.

    ⚠ Bos donmek SESSIZ BASARI DEGILDIR: cagiran taraf `hazir()` ile
    durumu bilir ve kullaniciya durustce raporlar.
    ⚠ `tenant` verilirse baglanti O TENANT'A BAGLANIR (R-1d-a). Tenant
    kimligi URL'e YAZILMAZ — sunucu onu oturumdan okur; boylece link
    kimin oldugunu SIZDIRMAZ.
    """
    ad = guvenli_ad(dosya)
    if not ad or not hazir():
        return ""
    try:
        omur = max(1, int(ttl_sn))
    except (TypeError, ValueError):
        omur = VARSAYILAN_TTL_SN
    exp = int(simdi if simdi is not None else time.time()) + omur
    return f"ciktilar/{ad}?exp={exp}&sig={_imza(ad, exp, tenant)}"


def dogrula(dosya: str, exp, sig: str, *,
            simdi: Optional[int] = None, tenant: str = "") -> dict:
    """Imza gecerli ve suresi dolmamis mi?  {gecerli, neden}

    ⚠ `tenant` imzalamada kullanildiysa dogrulamada da AYNISI verilmelidir;
    baska tenant (ya da tenant'siz istek) `IMZA-GECERSIZ` alir.
    """
    ad = guvenli_ad(dosya)
    if not hazir():
        return {"gecerli": False, "neden": "ANAHTAR-YOK"}
    if not ad:
        return {"gecerli": False, "neden": "DOSYA-YOK"}
    try:
        e = int(exp)
    except (TypeError, ValueError):
        return {"gecerli": False, "neden": "EXP-BOZUK"}
    s = str(sig or "")
    if not s:
        return {"gecerli": False, "neden": "IMZA-YOK"}
    # ⚠ Once IMZA dogrulanir, sonra sure. Sirasi onemli: gecersiz imzali bir
    # istekten "suresi dolmus" bilgisi sizmasin.
    if not hmac.compare_digest(_imza(ad, e, tenant), s):
        return {"gecerli": False, "neden": "IMZA-GECERSIZ"}
    now = int(simdi if simdi is not None else time.time())
    if e < now:
        return {"gecerli": False, "neden": "SURESI-DOLMUS",
                "gecikme_sn": now - e}
    return {"gecerli": True, "neden": "", "kalan_sn": e - now}


def kapsam_ozeti() -> dict:
    return {
        "sema_surum": SEMA_SURUM,
        "algoritma": "HMAC-SHA256",
        "sabit_zamanli_karsilastirma": True,
        "ttl_zorunlu": True,
        "varsayilan_ttl_sn": VARSAYILAN_TTL_SN,
        "anahtar_kaynagi": [ENV_ADI, f"veri/{ANAHTAR_DOSYA_ADI} (0600)",
                            "uretilir"],
        "anahtar_repoda": False,
        "anahtar_loglanir": False,
        "yol_gezinmesi_engellenir": True,
        # ⚠ FAZ R-1d-a: imza artik tenant'a BAGLANABILIR (opsiyonel, geriye
        # uyumlu). Tenant kimligi URL'e yazilmaz.
        "tenant_baglanabilir": True,
        "tenant_url_de_gorunur": False,
        "aga_cikar": False,
    }
