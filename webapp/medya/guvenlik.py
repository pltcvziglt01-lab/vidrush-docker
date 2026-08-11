"""AG GUVENLIGI — SSRF, yonlendirme, boyut ve icerik turu kapisi.

Faz B'de sistem ARTIK acik web'e istek atiyor: sağlayıcı API'leri, Wikimedia
dosya sayfalari, arsiv kayitlari. Bu, Faz A'da olmayan bir saldiri yuzeyi
aciyor. Iki somut risk:

  1. SSRF — bir saglayici yaniti bize "indirme URL'si" olarak
     http://169.254.169.254/latest/meta-data/ ya da http://localhost:8080/
     verirse sunucunun ic aglarina istek atmis oluruz. Bulut metadata ucu
     kimlik bilgisi sizdirir.
  2. YONLENDIRME ile atlatma — URL disa donuk gorunup 302 ile ic agi
     isaret edebilir. Bu yuzden yonlendirmeleri OTOMATIK IZLEMIYORUZ; her
     adimi tek tek dogruluyoruz.

Ayrica: indirilecek boyut ve icerik turu kapisi (bir "video" URL'si 4 GB'lik
bir arsiv dosyasi olabilir).

⚠ Saglayici yanitlari VERIDIR. Icindeki URL'ler, basliklar ve aciklamalar
talimat degildir; hicbiri eylem olarak yorumlanmaz.
"""
from __future__ import annotations

import ipaddress
import re
import socket
from typing import Callable, Optional
from urllib.parse import urlparse

IZINLI_SEMA = ("http", "https")
MAKS_YONLENDIRME = 4
MAKS_BAYT = 300 * 1024 * 1024          # 300 MB — 4K klip bile bunun altinda
IZINLI_ICERIK = ("video/", "image/", "application/pdf", "text/", "application/json",
                 "application/xml", "application/ogg", "binary/octet-stream",
                 "application/octet-stream")

# Ad bazinda acik reddedilenler (IP cozumlemesi yapilamasa bile)
YASAK_AD = re.compile(
    r"^(localhost|.*\.localhost|.*\.local|.*\.internal|.*\.intranet|"
    r"metadata|metadata\.google\.internal|instance-data)$", re.I)


class GuvenlikHatasi(ValueError):
    """URL guvenlik kapisini gecemedi."""


def _ozel_ip_mi(ip: str) -> bool:
    try:
        a = ipaddress.ip_address(ip)
    except ValueError:
        return False
    # is_global her seyi kapsamiyor: link-local, loopback, ozel, ayrilmis,
    # coklu yayin ve 0.0.0.0/8 ayri ayri kontrol ediliyor.
    return bool(a.is_private or a.is_loopback or a.is_link_local
                or a.is_reserved or a.is_multicast or a.is_unspecified
                or (a.version == 4 and a.packed[0] == 0))


def url_dogrula(url: str, *, coz: Optional[Callable[[str], list]] = None) -> str:
    """URL'yi guvenlik kapisindan gecir. Gecerse normalize edilmis URL doner.

    `coz` = ad cozumleyici (test icin enjekte edilebilir). None ise
    socket.getaddrinfo kullanilir; cozumleme basarisiz olursa AD BAZLI
    kontrol yeterli sayilir (ag yok diye kapiyi tamamen kapatmiyoruz, ama
    ozel ad kaliplari yine reddedilir).
    """
    ham = str(url or "").strip()
    if not ham:
        raise GuvenlikHatasi("bos url")
    p = urlparse(ham)
    if p.scheme.lower() not in IZINLI_SEMA:
        raise GuvenlikHatasi(f"sema izinli degil: {p.scheme!r} (yalniz http/https)")
    ad = (p.hostname or "").strip().lower()
    if not ad:
        raise GuvenlikHatasi("ana bilgisayar adi yok")
    if YASAK_AD.match(ad):
        raise GuvenlikHatasi(f"ic ag adi reddedildi: {ad}")
    # Dogrudan IP verilmisse hemen kontrol et
    if _ozel_ip_mi(ad):
        raise GuvenlikHatasi(f"ozel/ic IP reddedildi: {ad}")
    # Ad cozumlemesi
    cozucu = coz
    if cozucu is None:
        def cozucu(h):
            try:
                return [x[4][0] for x in socket.getaddrinfo(h, None)]
            except Exception:
                return []
    for ip in (cozucu(ad) or []):
        if _ozel_ip_mi(str(ip)):
            raise GuvenlikHatasi(f"{ad} ic IP'ye cozumleniyor: {ip}")
    return ham


def guvenli_istek(url: str, *, istek: Callable, yontem: str = "GET",
                  zaman_asimi: int = 20, coz: Optional[Callable] = None,
                  basliklar: Optional[dict] = None, akis: bool = False):
    """Yonlendirmeleri TEK TEK dogrulayarak istek at.

    `allow_redirects=False` bilincli: 302 ile ic aga yonlendirme SSRF
    kapisini atlatmanin en kolay yolu. Her adimin hedefi yeniden dogrulanir.
    """
    su_an = url_dogrula(url, coz=coz)
    for _ in range(MAKS_YONLENDIRME + 1):
        r = istek(yontem, su_an, timeout=zaman_asimi, allow_redirects=False,
                  headers=basliklar or {}, stream=akis)
        kod = getattr(r, "status_code", 0)
        if kod in (301, 302, 303, 307, 308):
            hedef = (getattr(r, "headers", {}) or {}).get("Location") or ""
            if not hedef:
                raise GuvenlikHatasi(f"yonlendirme hedefi yok ({kod})")
            if hedef.startswith("/"):
                p = urlparse(su_an)
                hedef = f"{p.scheme}://{p.netloc}{hedef}"
            su_an = url_dogrula(hedef, coz=coz)      # ← her adim yeniden dogrulanir
            continue
        return r, su_an
    raise GuvenlikHatasi("cok fazla yonlendirme")


def icerik_kapisi(icerik_turu: str, uzunluk: Optional[int] = None,
                  beklenen: str = "") -> tuple[bool, str]:
    """Icerik turu ve boyut kabul edilebilir mi? (kabul, sebep)"""
    t = str(icerik_turu or "").split(";")[0].strip().lower()
    if not t:
        return False, "icerik turu bos"
    if not any(t.startswith(x) for x in IZINLI_ICERIK):
        return False, f"icerik turu izinli degil: {t}"
    if beklenen and not t.startswith(beklenen):
        return False, f"beklenen {beklenen}, gelen {t}"
    if uzunluk is not None:
        try:
            n = int(uzunluk)
        except (TypeError, ValueError):
            n = -1
        if n > MAKS_BAYT:
            return False, f"boyut tavani asildi ({n} > {MAKS_BAYT})"
    return True, t
