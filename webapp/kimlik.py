#!/usr/bin/env python3
"""FAZ R-1c-a — ZORUNLU OTURUM + TENANT IZOLASYONU TEMELI.

⚠ PAROLA HASH SOZLESMESI — FAIL-CLOSED
Uretimde YALNIZCA **Argon2id** ya da **bcrypt** kabul edilir. PBKDF2/scrypt
gibi zayif geri dususlerle YENI PAROLA URETILMEZ. Desteklenen guclu
algoritma kurulu degilse hesap acma ve giris BASLAMAZ; stabil hata kodu
`KIMLIK-KDF-YOK` doner (sessiz zayiflama YOK).

Bagimlilik repo yonetiminde sabitlidir: `argon2-cffi==23.1.0`
(Dockerfile + Dockerfile.sunucu).

⚠ GECIS (migration): ESKI kayitlar (`scrypt`/`pbkdf2`) YALNIZCA
`eski_hash_dogrula()` ile dogrulanabilir — bu ayri ve acik bir yoldur.
Normal `parola_dogrula()` guclu algoritma yoksa hukum vermez.

⚠ Parola hicbir yerde DUZ METIN saklanmaz, LOGLANMAZ, koda/commit'e
YAZILMAZ. Hesap acma yalnizca `provisioning_girdisi()` ile env/stdin'den
okunur.

⚠ Bu modul AG/MEDYA acmaz; saf kripto + karar mantigi. Depolama enjekte
edilir (`kullanici_okuyucu` / `kullanici_yazici`).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import time
from typing import Callable, Optional

SEMA_SURUM = "1.0.0"

# ── GUCLU KDF (teslim sozlesmesi) ──
KDF_HATA_KODU = "KIMLIK-KDF-YOK"
_ARGON2 = None
_BCRYPT = None
try:                                                    # pragma: no cover
    from argon2 import PasswordHasher as _Argon2Sinif   # type: ignore
    from argon2 import exceptions as _argon2_hata       # type: ignore
    # OWASP 2024 onerisi civari: 64 MiB bellek, 3 tur, 4 paralellik.
    _ARGON2 = _Argon2Sinif(time_cost=3, memory_cost=64 * 1024,
                           parallelism=4)
except Exception:                                       # noqa: BLE001
    _argon2_hata = None
if _ARGON2 is None:                                     # pragma: no cover
    try:
        import bcrypt as _BCRYPT                        # type: ignore
    except Exception:                                   # noqa: BLE001
        _BCRYPT = None

# ⚠ Yalnizca GECIS dogrulamasi icin taninan ESKI bicimler. YENI parola
# BUNLARLA URETILMEZ.
ESKI_BICIMLER = ("scrypt", "pbkdf2")


def kdf_hazir() -> bool:
    """Guclu bir parola algoritmasi kurulu mu? (Argon2id ya da bcrypt)"""
    return _ARGON2 is not None or _BCRYPT is not None


def kdf_adi() -> str:
    return "argon2id" if _ARGON2 is not None else (
        "bcrypt" if _BCRYPT is not None else "")


# ── Oturum / CSRF ──
OTURUM_COOKIE = "vr_oturum"
CSRF_COOKIE = "vr_csrf"
CSRF_BASLIK = "x-csrf-token"
OTURUM_OMRU_SN = 12 * 3600
# ⚠ Cookie bayraklari: HttpOnly (JS okuyamaz), SameSite=Lax (CSRF yuzeyi
# daralir), Secure (HTTPS disinda gonderilmez).
COOKIE_BAYRAKLARI = {"httponly": True, "samesite": "lax", "secure": True}

# ── Giris hiz siniri ──
GIRIS_PENCERE_SN = 300
GIRIS_TAVAN = 5


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode("ascii").rstrip("=")


def _b64c(s: str) -> bytes:
    s = s + "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s.encode("ascii"))


# ═══════════════ PAROLA ═════════════════════════════════════════════════

def parola_hashle(parola: str) -> str:
    """Argon2id (ya da bcrypt) ile hash. ⚠ Duz metin ASLA saklanmaz.

    ⚠ FAIL-CLOSED: guclu algoritma yoksa `RuntimeError(KIMLIK-KDF-YOK)`.
    Zayif bir algoritmaya DUSULMEZ.
    """
    if not kdf_hazir():
        raise RuntimeError(KDF_HATA_KODU)
    p = (parola or "")
    if not p:
        raise ValueError("PAROLA-BOS")
    if _ARGON2 is not None:
        return "argon2id$" + _ARGON2.hash(p)
    tuz = _BCRYPT.gensalt(rounds=12)                    # pragma: no cover
    return "bcrypt$" + _BCRYPT.hashpw(p.encode("utf-8"),
                                      tuz).decode("ascii")


def eski_hash_dogrula(parola: str, kayit: str) -> dict:
    """GECIS yolu: eski `scrypt`/`pbkdf2` kayitlarini dogrula.

    ⚠ AYRI ve ACIK bir yoldur; dogrulanan kullanicinin parolasi ILK
    GIRISTE `parola_hashle()` ile YENIDEN hash'lenmelidir.
    """
    k, p = str(kayit or ""), (parola or "").encode("utf-8")
    parcalar = k.split("$")
    if len(parcalar) != 6 or parcalar[0] not in ESKI_BICIMLER:
        return {"gecerli": False, "neden": "ESKI-BICIM-DEGIL",
                "yeniden_hashle": False}
    try:
        tuz, ozet = _b64c(parcalar[4]), _b64c(parcalar[5])
        if parcalar[0] == "scrypt":
            if not hasattr(hashlib, "scrypt"):
                return {"gecerli": False, "neden": "SCRYPT-YOK",
                        "yeniden_hashle": False}
            yeni = hashlib.scrypt(p, salt=tuz, n=int(parcalar[1]),
                                  r=int(parcalar[2]), p=int(parcalar[3]),
                                  dklen=len(ozet))
        else:
            yeni = hashlib.pbkdf2_hmac("sha256", p, tuz, int(parcalar[1]),
                                       dklen=len(ozet))
    except Exception:                                   # noqa: BLE001
        return {"gecerli": False, "neden": "COZULEMEDI",
                "yeniden_hashle": False}
    ok = hmac.compare_digest(yeni, ozet)
    # ⚠ Dogrulandiysa MUTLAKA guclu algoritmaya tasinmali.
    return {"gecerli": ok, "neden": "" if ok else "PAROLA-YANLIS",
            "yeniden_hashle": ok}


def parola_dogrula(parola: str, kayit: str) -> bool:
    """Sabit zamanli dogrulama — YALNIZCA guclu bicimler.

    ⚠ Eski (`scrypt`/`pbkdf2`) kayitlar BURADA GECMEZ; gecis icin
    `eski_hash_dogrula()` ACIKCA cagrilmalidir.
    ⚠ Guclu algoritma kurulu degilse HUKUM VERILMEZ (False).
    """
    k = str(kayit or "")
    p = parola or ""
    if not k or not p or not kdf_hazir():
        return False
    if k.startswith("argon2id$"):
        if _ARGON2 is None:
            return False
        try:
            return bool(_ARGON2.verify(k[len("argon2id$"):], p))
        except Exception:                               # noqa: BLE001
            return False
    if k.startswith("bcrypt$"):                         # pragma: no cover
        if _BCRYPT is None:
            return False
        try:
            return bool(_BCRYPT.checkpw(p.encode("utf-8"),
                                        k[len("bcrypt$"):].encode("ascii")))
        except Exception:                               # noqa: BLE001
            return False
    return False


def parola_gucu(parola: str) -> dict:
    """Asgari guc olcutu — UYDURMA SKOR YOK, sayilabilir kosullar."""
    p = str(parola or "")
    kosullar = {
        "uzunluk_12": len(p) >= 12,
        "harf": any(c.isalpha() for c in p),
        "rakam": any(c.isdigit() for c in p),
        "sembol": any(not c.isalnum() for c in p),
    }
    return {"gecerli": all(kosullar.values()), "kosullar": kosullar}


# ═══════════════ OTURUM ═════════════════════════════════════════════════

def oturum_uret(tenant_id: str, *, anahtar: bytes,
                omur_sn: int = OTURUM_OMRU_SN,
                simdi: Optional[int] = None) -> str:
    """`tenant.exp.imza` — HMAC ile muhurlenmis oturum jetonu."""
    t = str(tenant_id or "").strip()
    if not t:
        raise ValueError("TENANT-BOS")
    exp = int(simdi if simdi is not None else time.time()) + int(omur_sn)
    govde = f"{_b64(t.encode())}.{exp}"
    imza = hmac.new(anahtar, govde.encode(), hashlib.sha256).digest()
    return f"{govde}.{_b64(imza)}"


def oturum_coz(jeton: str, *, anahtar: bytes,
               simdi: Optional[int] = None) -> dict:
    """Jetonu dogrula. ⚠ Once IMZA, sonra sure (bilgi sizmasin)."""
    parcalar = str(jeton or "").split(".")
    if len(parcalar) != 3:
        return {"gecerli": False, "neden": "BICIM-BOZUK"}
    govde = f"{parcalar[0]}.{parcalar[1]}"
    try:
        beklenen = hmac.new(anahtar, govde.encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(_b64(beklenen), parcalar[2]):
            return {"gecerli": False, "neden": "IMZA-GECERSIZ"}
        exp = int(parcalar[1])
        tid = _b64c(parcalar[0]).decode("utf-8")
    except Exception:                                   # noqa: BLE001
        return {"gecerli": False, "neden": "COZULEMEDI"}
    if exp < int(simdi if simdi is not None else time.time()):
        return {"gecerli": False, "neden": "SURESI-DOLMUS"}
    return {"gecerli": True, "tenant_id": tid, "exp": exp, "neden": ""}


# ═══════════════ CSRF ═══════════════════════════════════════════════════

def csrf_uret() -> str:
    return secrets.token_urlsafe(32)


def csrf_dogrula(cerez: str, baslik: str) -> bool:
    """Double-submit: cerezdeki ile basliktaki AYNI olmali (sabit zamanli)."""
    c, b = str(cerez or ""), str(baslik or "")
    if not c or not b:
        return False
    return hmac.compare_digest(c, b)


# ═══════════════ GIRIS HIZ SINIRI ═══════════════════════════════════════

def hiz_siniri(kayit: dict, anahtar: str, *, pencere_sn: int = GIRIS_PENCERE_SN,
               tavan: int = GIRIS_TAVAN, simdi: Optional[float] = None) -> dict:
    """Kayan pencere. ⚠ Kayit cagiran tarafta tutulur (bu modul durum tutmaz)."""
    now = float(simdi if simdi is not None else time.time())
    k = str(anahtar or "")
    liste = [t for t in (kayit.get(k) or []) if now - t < float(pencere_sn)]
    kayit[k] = liste
    if len(liste) >= int(tavan):
        return {"izin": False, "kalan": 0,
                "bekle_sn": round(float(pencere_sn) - (now - liste[0]), 1)}
    return {"izin": True, "kalan": int(tavan) - len(liste) - 1, "bekle_sn": 0}


def hiz_siniri_isle(kayit: dict, anahtar: str, *,
                    simdi: Optional[float] = None) -> None:
    """Basarisiz denemeyi kaydet."""
    now = float(simdi if simdi is not None else time.time())
    kayit.setdefault(str(anahtar or ""), []).append(now)


# ═══════════════ TENANT IZOLASYONU ══════════════════════════════════════

def tenant_coz(jeton: str, *, anahtar: bytes,
               simdi: Optional[int] = None) -> dict:
    """Istekten tenant kimligini cikar. ⚠ Kimlik YOKSA ERISIM YOK."""
    d = oturum_coz(jeton, anahtar=anahtar, simdi=simdi)
    if not d["gecerli"]:
        return {"yetkili": False, "tenant_id": "", "neden": d["neden"]}
    return {"yetkili": True, "tenant_id": d["tenant_id"], "neden": ""}


def sahiplik_dogrula(kaynak: dict, tenant_id: str) -> dict:
    """Kaynak (job/video/provider) BU tenant'a mi ait?

    ⚠ `tenant_id` alani OLMAYAN eski kayitlar SAHIPSIZDIR ve ERISILEMEZ —
    "herkese acik" SAYILMAZ. Sessiz sizinti yerine acik RED.
    """
    sahip = str((kaynak or {}).get("tenant_id") or "").strip()
    t = str(tenant_id or "").strip()
    if not t:
        return {"izin": False, "neden": "TENANT-YOK"}
    if not sahip:
        return {"izin": False, "neden": "KAYNAK-SAHIPSIZ"}
    if not hmac.compare_digest(sahip, t):
        return {"izin": False, "neden": "BASKA-TENANT"}
    return {"izin": True, "neden": ""}


# ═══════════════ GUVENLI PROVISIONING (env/stdin) ═══════════════════════

def provisioning_girdisi(*, env: Optional[dict] = None,
                         stdin_okuyucu: Optional[Callable] = None) -> dict:
    """Hesap acma girdisini env ya da stdin'den al.

    ⚠ PAROLA HICBIR ZAMAN koda/commit'e/argumana YAZILMAZ. Yalnizca
    `VIDRUSH_ADMIN_KULLANICI` + `VIDRUSH_ADMIN_PAROLA` env ya da stdin.
    ⚠ Donen sozlukte parola DUZ METIN TUTULMAZ: dogrudan HASH'lenir.
    """
    e = env if env is not None else os.environ
    kullanici = str(e.get("VIDRUSH_ADMIN_KULLANICI") or "").strip()
    parola = e.get("VIDRUSH_ADMIN_PAROLA") or ""
    if not parola and callable(stdin_okuyucu):
        parola = stdin_okuyucu() or ""
    if not kullanici or not parola:
        return {"hazir": False, "neden": "GIRDI-EKSIK",
                "ipucu": ("VIDRUSH_ADMIN_KULLANICI ve VIDRUSH_ADMIN_PAROLA "
                          "env ile verin ya da stdin'den okutun")}
    if not kdf_hazir():
        # ⚠ FAIL-CLOSED: guclu algoritma yoksa hesap ACILMAZ.
        return {"hazir": False, "neden": KDF_HATA_KODU,
                "ipucu": "argon2-cffi (ya da bcrypt) kurulu olmali"}
    g = parola_gucu(parola)
    if not g["gecerli"]:
        return {"hazir": False, "neden": "PAROLA-ZAYIF",
                "kosullar": g["kosullar"]}
    kayit = {"kullanici": kullanici, "parola_hash": parola_hashle(parola),
             "tenant_id": secrets.token_urlsafe(12)}
    del parola                                   # ⚠ bellekte tutma
    return {"hazir": True, "kayit": kayit, "neden": ""}


def kapsam_ozeti() -> dict:
    return {
        "sema_surum": SEMA_SURUM,
        "parola_algoritmasi": kdf_adi(),
        "kdf_hazir": kdf_hazir(),
        "fail_closed": True,
        "kdf_hata_kodu": KDF_HATA_KODU,
        "zayif_fallback": False,
        "gecis_dogrulamasi": list(ESKI_BICIMLER),
        "duz_metin_parola_saklanir": False,
        "parola_loglanir": False,
        "cookie_bayraklari": dict(COOKIE_BAYRAKLARI),
        "csrf": "double-submit (cerez + baslik, sabit zamanli)",
        "giris_hiz_siniri": {"pencere_sn": GIRIS_PENCERE_SN,
                             "tavan": GIRIS_TAVAN},
        "kimliksiz_erisim": False,
        "sahipsiz_kaynak_erisilir": False,
        "aga_cikar": False,
    }
