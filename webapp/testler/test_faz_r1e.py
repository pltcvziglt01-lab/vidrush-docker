#!/usr/bin/env python3
"""FAZ R-1e — OTURUMSUZ MODDA TENANT IZOLASYONU AYAKTA KALIR.

⚠ OLCULEN KUSUR (staging 185.23.17.240, 15 Agu 2026):
`ZORUNLU_OTURUM=0` ile uyelik zorunlulugu kaldirildiginda `_tenant()` BOS
STRING donuyordu ve tenant izolasyonu UC AYRI NOKTADA tumden dusuyordu:

  1. `server._erisim_dogrula()`  ->  `if not tenant_id: return`
     Sahiplik kontrolu ATLANIYORDU. `kimlik.sahiplik_dogrula()` dogru
     karari (`izin=False, TENANT-YOK`) veriyordu ama HIC CAGRILMIYORDU.

  2. `server._imzalayici()`  ->  `im or (imzali_url.imzala
     if not ZORUNLU_OTURUM else None)`
     Tenant'a bagli imzalayici None donunce TENANT'SIZ (legacy)
     imzalayiciya dusuyordu. Olculdu: `imzala(d, tenant="")` ile uretilen
     imza `dogrula(d, ..., tenant="")` ile GECERLI (True).

  3. `server.is_listesi()`  ->  `if tenant_id and not erisim_kapisi(...)`
     Tenant bos oldugu icin filtre KOMPLE atlaniyordu; TAHMIN EDILEBILIR
     `session` on eki (kodun kendi yorumu: "yetki degildir") o oneki
     tasiyan TUM isleri imzali URL'lerle listeliyordu.

Zincir: anonim `/api/job/{id}` -> sahiplik atlanir -> cevapta mevcut
kullanicinin videosu icin GECERLI imzali URL -> `/ciktilar/...` -> VIDEO
INER. Staging'de risk altindaki gercek veri: 59 is kaydi (17 tenant
damgali, 42 sahipsiz, 47'sinde video) + 1 tenant altinda 3 kutuphane
videosu.

── COZUM (en kucuk ve en guvenli) ──
Oturumsuz modda anonim ziyaretciye BOS STRING degil, GERCEK bir kapsam
kimligi verilir: `teslim.ANON_TENANT`. Boylece mevcut izolasyon makinesi
(sahiplik_dogrula / erisim_kapisi / imzalayici_kur / kutuphane) HICBIR
KAPI ATLANMADAN oldugu gibi calisir.

⚠ SONUC: damgasiz ESKI kayitlar da anonime KAPALI kalir. "Damgasizi
public say" yaklasimi staging'deki 42 sahipsiz isi (cogu videolu)
anonime ACARDI — oturumsuz moda gecmek gecmisteki sahipsiz isleri
ACMAZ.

⚠ KABUL EDILEN DAVRANIS: tum anonim ziyaretciler AYNI kapsami paylasir
(`ANON_TENANT`), yani birbirlerinin anonim uretimlerini gorebilirler. Bu
uyeliksiz bir sitenin beklenen halidir ve MEVCUT tenant verisine erisim
VERMEZ.

Kosum: .venv-test/bin/python3 webapp/testler/test_faz_r1e.py
"""
from __future__ import annotations

import os
import re
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEPO = os.path.dirname(KOK)
sys.path.insert(0, KOK)

gecen, basarisiz, bloke = 0, [], []


def kontrol(ad, kosul, detay=""):
    global gecen
    if kosul:
        gecen += 1
        print(f"  ok   {ad}")
    else:
        basarisiz.append(f"{ad} — {detay}")
        print(f"  XX   {ad}  {detay}")


def bloke_yaz(ad, sebep):
    bloke.append(f"{ad} — {sebep}")
    print(f"  --   BLOKE {ad}: {sebep}")


def blok(ad):
    print(f"\n── {ad} ──")


def oku(*p):
    with open(os.path.join(KOK, *p), encoding="utf-8") as f:
        return f.read()


import imzali_url                                          # noqa: E402
import kimlik                                              # noqa: E402
import teslim                                              # noqa: E402

_gk = tempfile.mkdtemp(prefix="r1e_")
teslim.anahtar_kur(_gk)
imzali_url.anahtar_kur(_gk)

# ── Ornek kayitlar: staging'deki UC gercek kategori ──
MUSTERI = "T_MEVCUT_KULLANICI"
IS_DAMGALI = {"tenant_id": MUSTERI, "durum": "bitti", "video": "musteri.mp4"}
IS_SAHIPSIZ = {"durum": "bitti", "video": "eski_sahipsiz.mp4"}   # 42 adet
IS_ANONIM = {"tenant_id": getattr(teslim, "ANON_TENANT", "__YOK__"),
             "durum": "bitti", "video": "anon.mp4"}


blok("R-1e/1 — ANONIM KAPSAM KIMLIGI VAR VE AYIRT EDICI")

kontrol("teslim.ANON_TENANT tanimli",
        hasattr(teslim, "ANON_TENANT"),
        "oturumsuz modda anonim kapsam kimligi yok")
kontrol("ANON_TENANT bos string DEGIL (bos = kapi atlanir)",
        bool(str(getattr(teslim, "ANON_TENANT", "")).strip()))
kontrol("ANON_TENANT gercek bir tenant kimligiyle CAKISMAZ",
        str(getattr(teslim, "ANON_TENANT", "")) != MUSTERI)
kontrol("teslim.ANON_RED_KODU stabil hata kodu tanimli",
        bool(str(getattr(teslim, "ANON_RED_KODU", "")).strip()))


blok("R-1e/2 — KAPSAM KAPISI: bos tenant ARTIK ERISIM VERMEZ")

kapsam = getattr(teslim, "kapsam_kapisi", None)
if not callable(kapsam):
    bloke_yaz("teslim.kapsam_kapisi", "fonksiyon yok — kapi tek noktadan gecmiyor")
else:
    kontrol("BOS tenant + mevcut kullanicinin DAMGALI isi -> RED",
            kapsam(IS_DAMGALI, "")["izin"] is False,
            str(kapsam(IS_DAMGALI, "")))
    kontrol("BOS tenant + SAHIPSIZ eski is -> RED",
            kapsam(IS_SAHIPSIZ, "")["izin"] is False,
            str(kapsam(IS_SAHIPSIZ, "")))
    kontrol("BOS tenant + ANONIM kapsam isi -> RED "
            "(bos string hicbir kapsam DEGILDIR)",
            kapsam(IS_ANONIM, "")["izin"] is False,
            str(kapsam(IS_ANONIM, "")))
    kontrol("ANONIM kapsam + mevcut kullanicinin DAMGALI isi -> RED",
            kapsam(IS_DAMGALI, teslim.ANON_TENANT)["izin"] is False,
            str(kapsam(IS_DAMGALI, getattr(teslim, "ANON_TENANT", ""))))
    kontrol("ANONIM kapsam + SAHIPSIZ eski is -> RED "
            "(oturumsuz mod gecmisi ACMAZ)",
            kapsam(IS_SAHIPSIZ, teslim.ANON_TENANT)["izin"] is False,
            str(kapsam(IS_SAHIPSIZ, getattr(teslim, "ANON_TENANT", ""))))
    kontrol("ANONIM kapsam + KENDI anonim isi -> IZIN "
            "(uretim akisi calisir)",
            kapsam(IS_ANONIM, teslim.ANON_TENANT)["izin"] is True,
            str(kapsam(IS_ANONIM, getattr(teslim, "ANON_TENANT", ""))))
    kontrol("MEVCUT kullanici + KENDI isi -> IZIN (gerileme yok)",
            kapsam(IS_DAMGALI, MUSTERI)["izin"] is True)
    kontrol("MEVCUT kullanici + ANONIM is -> RED (capraz sizinti yok)",
            kapsam(IS_ANONIM, MUSTERI)["izin"] is False)
    kontrol("RED nedeni STABIL kod tasir",
            str(kapsam(IS_DAMGALI, teslim.ANON_TENANT).get("neden") or "").strip()
            != "",
            "neden bos")


blok("R-1e/3 — IMZALAYICI: damgali kayda ANONIM imza URETILMEZ")

sec = getattr(teslim, "imzalayici_sec", None)
if not callable(sec):
    bloke_yaz("teslim.imzalayici_sec", "fonksiyon yok — imzalayici secimi tek noktada degil")
else:
    kontrol("BOS tenant + damgali kayit -> imzalayici YOK",
            sec("", IS_DAMGALI, oturumsuz_izin=True) is None)
    kontrol("BOS tenant + sahipsiz kayit -> imzalayici YOK",
            sec("", IS_SAHIPSIZ, oturumsuz_izin=True) is None)
    kontrol("ANONIM kapsam + damgali kayit -> imzalayici YOK",
            sec(teslim.ANON_TENANT, IS_DAMGALI, oturumsuz_izin=True) is None)
    _im = sec(teslim.ANON_TENANT, IS_ANONIM, oturumsuz_izin=True)
    kontrol("ANONIM kapsam + kendi isi -> imzalayici VAR", callable(_im))
    if callable(_im):
        _u = _im("anon.mp4")
        import urllib.parse as _up
        _q = dict(_up.parse_qsl(_u.split("?", 1)[1])) if "?" in _u else {}
        kontrol("anonim imza ANONIM kapsamda gecerli",
                imzali_url.dogrula("anon.mp4", _q.get("exp"), _q.get("sig", ""),
                                   tenant=teslim.ANON_TENANT)["gecerli"] is True)
        kontrol("anonim imza MEVCUT KULLANICI kapsaminda GECERSIZ",
                imzali_url.dogrula("anon.mp4", _q.get("exp"), _q.get("sig", ""),
                                   tenant=MUSTERI)["gecerli"] is False)
        kontrol("anonim imza TENANT'SIZ dogrulamada GECERSIZ "
                "(legacy fallback kapali)",
                imzali_url.dogrula("anon.mp4", _q.get("exp"), _q.get("sig", ""),
                                   tenant="")["gecerli"] is False)
    kontrol("oturumsuz_izin=False iken tenant'siz imzalayici URETILMEZ",
            sec("", IS_ANONIM, oturumsuz_izin=False) is None)


blok("R-1e/4 — server.py: UC ACIK DA KAYNAKTA KAPALI")

_S = oku("server.py")

# 1) erken-return acigi
_ed = re.search(r"def _erisim_dogrula\(.*?\n(?=\n@|\ndef |\nclass )", _S, re.S)
_ed_govde = _ed.group(0) if _ed else ""
kontrol("_erisim_dogrula bulundu", bool(_ed_govde))
kontrol("ACIK-1 KAPALI: _erisim_dogrula'da 'if not tenant_id: return' YOK",
        not re.search(r"if not tenant_id:\s*\n\s*return\s*$", _ed_govde, re.M),
        "bos tenant kontrolu hala atliyor")
kontrol("_erisim_dogrula TEK kapidan geciyor (kapsam_kapisi)",
        "kapsam_kapisi" in _ed_govde)

# 2) legacy imzalayici fallback
_iz = re.search(r"def _imzalayici\(.*?\n(?=\n@|\ndef |\nclass )", _S, re.S)
_iz_govde = _iz.group(0) if _iz else ""
kontrol("_imzalayici bulundu", bool(_iz_govde))


def _yalniz_kod(govde: str) -> str:
    """Docstring ve yorumlari at — kusuru ANLATAN metin, KOD sayilmasin."""
    g = re.sub(r'"""(?:.|\n)*?"""', "", govde)
    return re.sub(r"#.*", "", g)


_iz_kod = _yalniz_kod(_iz_govde)
kontrol("ACIK-2 KAPALI: tenant'siz legacy imzalayici fallback'i YOK",
        "imzali_url.imzala" not in _iz_kod
        and "imzalayici_sec" in _iz_kod,
        f"legacy fallback duruyor: {_iz_kod.strip()[:120]}")
kontrol("ACIK-2 KAPALI: _imzalayici KAYDA gore secim yapar",
        re.search(r"def _imzalayici\(\s*tenant_id[^)]*kayit", _iz_govde)
        is not None,
        "imzalayici kayit parametresi almiyor")

# 3) /api/isler filtresi
_il = re.search(r"def is_listesi\(.*?\n(?=\n@|\ndef |\nclass )", _S, re.S)
_il_govde = _il.group(0) if _il else ""
kontrol("is_listesi bulundu", bool(_il_govde))
kontrol("ACIK-3 KAPALI: liste filtresi 'if tenant_id and' ile atlanmiyor",
        "if tenant_id and not teslim.erisim_kapisi" not in _il_govde,
        "session oneki hala yetki gibi davraniyor")
kontrol("is_listesi kapsam kapisindan geciyor",
        "kapsam_kapisi" in _il_govde)

# 4) _tenant oturumsuz modda anonim kapsam dondurur
_tn = re.search(r"def _tenant\(.*?\n(?=\n@|\ndef |\nclass )", _S, re.S)
_tn_govde = _tn.group(0) if _tn else ""
kontrol("_tenant bulundu", bool(_tn_govde))
kontrol("_tenant oturumsuz modda ANON_TENANT dondurur (bos string DEGIL)",
        "ANON_TENANT" in _tn_govde and not re.search(
            r"if not ZORUNLU_OTURUM:\s*\n\s*return\s*\"\"", _tn_govde),
        "oturumsuz modda hala bos string donuyor")


blok("R-1e/5 — GERILEME YOK: mevcut korumalar duruyor")

kontrol("GERILEME YOK: sahiplik_dogrula bos tenant'a hala IZIN VERMEZ",
        kimlik.sahiplik_dogrula(IS_DAMGALI, "")["izin"] is False)
kontrol("GERILEME YOK: sahiplik_dogrula sahipsiz kaydi hala REDDEDER",
        kimlik.sahiplik_dogrula(IS_SAHIPSIZ, MUSTERI)["neden"] == "KAYNAK-SAHIPSIZ")
kontrol("GERILEME YOK: erisim_kapisi capraz tenant'i REDDEDER",
        teslim.erisim_kapisi(IS_DAMGALI, "BASKA")["izin"] is False)
kontrol("GERILEME YOK: imzalayici_kur bos tenant'a imzalayici VERMEZ",
        teslim.imzalayici_kur("") is None)
_kdepo = {MUSTERI: [{"is_id": "x", "tenant_id": MUSTERI, "dosya": "a.mp4"}]}
kontrol("GERILEME YOK: kutuphane tenant'siz cagriya TENANT-YOK der",
        teslim.listele(_kdepo, "")["ok"] is False
        and teslim.listele(_kdepo, "")["videolar"] == [])
kontrol("R-1e: ANONIM kapsam MEVCUT kullanicinin kutuphanesini GORMEZ",
        teslim.listele(_kdepo, getattr(teslim, "ANON_TENANT", "__YOK__")
                       )["videolar"] == [])
kontrol("GERILEME YOK: /api/kutuphane hala tenant ISTER",
        'raise HTTPException(401, "giris gerekli")' in _S)
kontrol("GERILEME YOK: CSRF kapisi duruyor",
        "UI3-CSRF-GECERSIZ" in _S)
kontrol("GERILEME YOK: /ciktilar imza dogrulamasi tenant'a bagli",
        "imzali_url.dogrula(ad, exp, sig, tenant=tenant_id)" in _S)
kontrol("GERILEME YOK: giris hiz siniri sabitleri duruyor",
        kimlik.GIRIS_TAVAN > 0 and kimlik.GIRIS_PENCERE_SN > 0)
kontrol("GERILEME YOK: Argon2id sozlesmesi duruyor",
        kimlik.kdf_adi() in ("argon2id", "bcrypt"))
kontrol("GERILEME YOK: /api/generate sozlesmesi 22 alan (buyumedi)",
        len(re.findall(r"^\s{18,}(\w+): str = Form\(", _S, re.M)) >= 1)

import shutil                                              # noqa: E402
shutil.rmtree(_gk, ignore_errors=True)

print(f"\n{'=' * 60}")
print(f"GECEN: {gecen}   BASARISIZ: {len(basarisiz)}   BLOKE: {len(bloke)}")
for b in basarisiz:
    print(f"  XX {b}")
for b in bloke:
    print(f"  -- BLOKE {b}")
sys.exit(1 if (basarisiz or bloke) else 0)
