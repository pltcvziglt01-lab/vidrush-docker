"""LISANS / PROVENANCE DUVARI.

Faz A'daki `arastirma.manifests.lisans_*` fonksiyonlarini YENIDEN YAZMIYOR,
uzerine saglayici-ozel bilgi ekliyor:

  - saglayicinin lisans alanini nerede tuttugu ve nasil okundugu
  - atif metninin lisansa gore nasil kurulacagi
  - "render'a girebilir mi" karari ve GEREKCESI

Degismez kural (Faz A'dan devam): ACIK LISANSI KANITLANAMAYAN OGE RENDER'A
GIRMEZ. Boyle bir oge manifestte `reference_only` olarak durabilir — arastirma
sirasinda "boyle bir goruntu var" bilgisi degerlidir — ama `render_kullanilabilir`
False ve `red_nedeni` doludur.

Neden reference_only diye bir sey var: bir Wikimedia dosyasinin lisansi
okunamadiginda onu tamamen atmak yerine kaydetmek, sonra elle kontrol veya
farkli bir surumunu bulma imkani veriyor. Ama render hattina ASLA giremez.
"""
from __future__ import annotations

import re

from arastirma.manifests import (LISANS_KURALLARI, YASAK_LISANS_ISARETLERI,
                                 lisans_kullanilabilir, lisans_normalize)

# Saglayicinin kendi lisansi sabitse burada tanimli (API her ogede dondurmuyor)
SAGLAYICI_SABIT_LISANS = {
    "pexels": "pexels",
    "coverr": "coverr",
    "pixabay": "pixabay",
    "nasa": "nasa-public",
}

# Saglayici yanitindaki lisans alan adlari — biri bulunursa okunur
LISANS_ALANLARI = ("license", "licence", "LicenseShortName", "license_short_name",
                   "licenseurl", "license_url", "rights", "usage_terms",
                   "UsageTerms", "lisans")
SAHIP_ALANLARI = ("artist", "Artist", "author", "creator", "Credit", "credit",
                  "photographer", "uploader", "attribution", "eser_sahibi", "user")

# Ham lisans metninde gecen ve ACIK REDDI gerektiren kaliplar.
# Not: arastirma.manifests da benzer bir liste tutuyor; burasi saglayicilarin
# gerceklikte donderdigi serbest metinlere bakiyor (daha gurultulu).
# ⚠ "copyright " KALIBI KALDIRILDI (test yakaladi). Library of Congress'in
# kamu malı beyani "No known copyright restrictions" — icinde "copyright"
# gectigi icin reddediliyor ve EN DEGERLI arsiv kaynagi elenmis oluyordu.
# Artik PD kaliplari RED kaliplarindan ONCE kontrol ediliyor (bkz. lisans_karari)
# ve red listesi yalnizca kesin ifadeler tutuyor.
RED_KALIPLARI = (
    "all rights reserved", "tum haklari sakli", "©",
    "editorial use only", "editorial only", "rights managed", "rights-managed",
    "noncommercial", "non-commercial", "noderiv", "no deriv",
    "getty", "shutterstock", "adobe stock", "alamy",
)
# "public domain" ifadesinin serbest metinde gectigi durumlar
PD_KALIPLARI = ("public domain", "pd-us", "pd-old", "no known copyright",
                "kamu mali", "cc0", "creative commons zero")


def ham_lisans_oku(kayit: dict) -> tuple[str, str]:
    """Saglayici kaydindan (ham_lisans, lisans_url) cikar."""
    ham, url = "", ""
    for a in LISANS_ALANLARI:
        d = kayit.get(a)
        if isinstance(d, dict):                       # {"value": "...", "url": "..."}
            ham = ham or str(d.get("value") or d.get("text") or "")
            url = url or str(d.get("url") or "")
        elif isinstance(d, str) and d.strip():
            if d.strip().lower().startswith("http"):
                url = url or d.strip()
            else:
                ham = ham or d.strip()
    return ham.strip(), url.strip()


def eser_sahibi_oku(kayit: dict) -> str:
    for a in SAHIP_ALANLARI:
        d = kayit.get(a)
        if isinstance(d, dict):
            d = d.get("value") or d.get("text") or d.get("name")
        if isinstance(d, str) and d.strip():
            # Wikimedia "Artist" alani HTML iceriyor
            return re.sub(r"<[^>]+>", "", d).strip()[:160]
    return ""


def _url_den_lisans(lisans_url: str) -> str:
    """CC lisans URL'sinden lisans adi. archive_org ve Openverse lisansi
    METIN olarak degil URL olarak veriyor; ilk surumde bu okunmuyordu ve
    gecerli CC-BY ogeler "belirsiz" diye reddediliyordu (test yakaladi)."""
    d = str(lisans_url or "").lower()
    if not d:
        return "unknown"
    if "publicdomain/zero" in d or "/cc0" in d:
        return "cc0"
    if "publicdomain/mark" in d:
        return "pdm"
    if "publicdomain" in d:
        return "public-domain"
    m = re.search(r"/licenses/(by(?:-[a-z]{2})*)/", d)
    if m:
        parcalar = m.group(1).split("-")          # by, by-sa, by-nc-nd ...
        if "nc" in parcalar or "nd" in parcalar:
            return "unknown"                      # NC/ND kabul edilmiyor
        return "cc-by-sa" if "sa" in parcalar else "cc-by"
    return "unknown"


def _serbest_metinden_lisans(ham: str) -> str:
    """Saglayici yapilandirilmis lisans vermediginde serbest metinden cikar.
    Sadece KESIN olan durumlarda deger doner; belirsizse "unknown"."""
    d = str(ham or "").lower()
    if not d:
        return "unknown"
    for k in RED_KALIPLARI:
        if k in d:
            return "unknown"                  # acik red -> kullanilamaz
    if any(k in d for k in PD_KALIPLARI):
        return "cc0" if "cc0" in d or "zero" in d else "public-domain"
    m = re.search(r"cc[\s\-_]?by(?:[\s\-_]?(sa|nc|nd))?", d)
    if m:
        ek = m.group(1) or ""
        if ek in ("nc", "nd"):
            return "unknown"                  # NC/ND kabul edilmiyor
        return "cc-by-sa" if ek == "sa" else "cc-by"
    return "unknown"


def lisans_karari(kayit: dict, saglayici: str) -> dict:
    """Bir saglayici kaydinin lisans durumunu karara baglar.

    Doner:
      {ham_lisans, lisans, lisans_url, eser_sahibi, atif_gerekli,
       ticari_izin, degistirme_izni, render_kullanilabilir, red_nedeni}
    """
    ham, lurl = ham_lisans_oku(kayit)
    sahip = eser_sahibi_oku(kayit)

    # DENETIM METNI: lisans alani + kunye + eser sahibi + kullanim sartlari.
    # Neden hepsi: Wikimedia'da lisans "CC BY 4.0" yazarken kunyede
    # "Getty Images" olabilir. Ilk surumde yalnizca lisans alanina bakiyordum
    # ve bu oge KABUL EDILIYORDU (test yakaladi).
    denetim = " ".join(str(kayit.get(a) or "") if not isinstance(kayit.get(a), dict)
                       else str((kayit.get(a) or {}).get("value") or "")
                       for a in (LISANS_ALANLARI + SAHIP_ALANLARI)).lower()
    denetim += " " + str(ham).lower() + " " + str(sahip).lower()

    # 1) KAMU MALI beyani her seyden ONCE kontrol edilir. "No known copyright
    #    restrictions" bir PD beyanidir; red kaliplarindan once bakilmazsa
    #    icindeki "copyright" kelimesi yuzunden reddedilir.
    pd_beyani = any(k in denetim for k in PD_KALIPLARI)

    # 2) Acik red kaliplari (PD beyani yoksa)
    if not pd_beyani:
        for k in RED_KALIPLARI:
            if k in denetim:
                return _red(ham, lurl, sahip, f"lisans metni kisitli: '{k}'")
    # Ticari saglayici adi PD beyanina RAGMEN reddedilir (Getty "PD" demez)
    for k in ("getty", "shutterstock", "adobe stock", "alamy", "dreamstime"):
        if k in denetim:
            return _red(ham, lurl, sahip, f"ticari stok kaynagi: '{k}'")
    for k in YASAK_LISANS_ISARETLERI:
        if k in denetim:
            return _red(ham, lurl, sahip, f"lisans kisitli: '{k}'")

    # 3) Lisans adini belirle: saglayici sabiti -> metin -> URL -> serbest metin
    sabit = SAGLAYICI_SABIT_LISANS.get(str(saglayici).lower())
    ad = lisans_normalize(sabit) if sabit else lisans_normalize(ham)
    if ad == "unknown":
        ad = _url_den_lisans(lurl)
    if ad == "unknown":
        ad = _serbest_metinden_lisans(ham)
    if ad == "unknown" and pd_beyani:
        ad = "public-domain"

    ok, sebep = lisans_kullanilabilir(ad)
    if not ok:
        return _red(ham, lurl, sahip, sebep)

    tic, deg, atif = LISANS_KURALLARI[ad]
    if atif and not sahip:
        # Atif zorunlu ama eser sahibi bilinmiyor -> atif YAPILAMAZ -> render'a giremez
        return _red(ham, lurl, sahip,
                    f"{ad} atif istiyor ama eser sahibi bilinmiyor")
    return {"ham_lisans": ham, "lisans": ad, "lisans_url": lurl,
            "eser_sahibi": sahip, "atif_gerekli": atif,
            "ticari_izin": tic, "degistirme_izni": deg,
            "render_kullanilabilir": True, "red_nedeni": ""}


def _red(ham: str, lurl: str, sahip: str, neden: str) -> dict:
    return {"ham_lisans": ham, "lisans": "unknown", "lisans_url": lurl,
            "eser_sahibi": sahip, "atif_gerekli": True,
            "ticari_izin": False, "degistirme_izni": False,
            "render_kullanilabilir": False, "red_nedeni": neden}


def atif_metni(lisans: str, eser_sahibi: str, baslik: str, orijinal_url: str) -> str:
    """Lisansin istedigi bicimde atif satiri. Atif gerekmiyorsa bos doner."""
    ad = lisans_normalize(lisans)
    if ad not in LISANS_KURALLARI:
        return ""
    if not LISANS_KURALLARI[ad][2]:
        return ""
    parcalar = [p for p in [(baslik or "").strip()[:120],
                            (eser_sahibi or "").strip()[:120]] if p]
    return " — ".join(parcalar) + f" ({ad.upper()}) {orijinal_url}"
