#!/usr/bin/env python3
"""FAZ UI-5 — MEDYA KAYNAGI GORUNUR + BELGESEL %100 VIDEO.

⚠ OLCULEN KUSURLAR (canli UI denetimi, 15 Agu 2026, 185.23.17.240):

1. `UI5-SAGLAYICI-ANA-AKISTA-YOK`
   Kaynak tercihi arayuzu YALNIZCA `/akis` sayfasinin scripti `ui1.js`de
   var (FAZ UI-3 oraya eklemis). ANA uygulama zincirinde — `index.html`
   -> `app.js` -> `basit.js` / `wizard.js` / `secim-deneyimi.js` —
   `magnific|provider|kaynak-tercihi|saglayici` kelimeleri HIC GECMIYOR.
   Canli DOM teyit etti: `#/yeni` Basit modda yalnizca stil, sure ve
   gelismis ayarlar var; medya kaynagi secimi YOK.

2. `UI5-MAGNIFIC-STOK-SAGLAYICI-DEGIL`
   Magnific bir MEDYA SAGLAYICISI DEGIL, bir UPSCALE servisidir
   (`kaynak.magnific_upscale`, Freepik'e katildi, FREEPIK_KEYS ile ayni
   anahtar). Stok arama yetenegi YOK. Dahasi `saglayici_motoru
   .saglayici_sec()` UC DALIN UCUNDE DE `wikimedia` (ucretsiz) donuyor —
   gercek OAuth/kredi YOK, `mcp.magnific.com` baglantisi YOK
   (`mcp_cagirici` enjekte edilen test-double). Yani "Magnific"i bir stok
   secenegi gibi sunmak GERCEGI YANLIS TEMSIL EDER.

3. `UI5-BELGESEL-STATIK-GORSELE-DUSUYOR`
   `footage_pct`: sinematik-belgesel=85, anlati-video-essay=55,
   veri-anlatisi=45, hizli-explainer=45 — yalnizca seyahat-belgeseli=100.
   Ustelik `gorsel_yasak` zinciri bile SONUNDA AI STATIK GORSELE
   DUSUYOR ("footage YOK ve gorsel yasak -> AI gorsele mecbur",
   pipeline.py). Kullanici karari: statik foto/zoom slayt timeline'a
   OTOMATIK GIRMESIN; video yoksa STABIL HATA versin.

4. `UI5-YAS-ETIKETI-ADET-SANILIYOR`
   Ses adi "Yaşlı Kadın (75)" parantezli sayi tasiyor ve kullanici bunu
   MEDYA ADEDI ("75 gorsel") sandi. Canli DOM taramasi: taze DOM'da
   BASKA 75 YOK; arayuzde medya adedi gosteren HICBIR alan da yok.

5. `UI5-ANONIM-CSRF-YOK`
   Oturumsuz modda `POST /api/kaynak-tercihi` -> 403 `UI3-CSRF-GECERSIZ`
   cunku `vr_csrf` cerezi YALNIZCA `/api/giris` basarisinda kuruluyor.

⚠ KORUNACAK SOZLESMELER: `/api/generate` TAM 22 alan (buyumez),
I-23 / I-24 / I-25 / I-38, R-1e kapsam kapisi, deploy.sh.

Kosum: .venv-test/bin/python3 webapp/testler/test_faz_ui5.py
"""
from __future__ import annotations

import os
import re
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEPO = os.path.dirname(KOK)
sys.path.insert(0, KOK)
sys.path.insert(0, os.path.join(DEPO, "app"))

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


def yalniz_kod(govde: str) -> str:
    """Docstring/yorum at — kusuru ANLATAN metin KOD sayilmasin."""
    g = re.sub(r'"""(?:.|\n)*?"""', "", govde)
    g = re.sub(r"^\s*#.*$", "", g, flags=re.M)
    return re.sub(r"/\*(?:.|\n)*?\*/", "", g)


_PIPE = oku("pipeline.py")
_BASIT = oku("static", "js", "basit.js")
_SECIM = oku("static", "js", "secim-deneyimi.js")
_WIZ = oku("static", "js", "wizard.js")
_API = oku("static", "js", "api.js")
_SERVER = oku("server.py")

# Belge/gercek-kaynak tabanli TUM edit stilleri (kullanici karari 15 Agu).
BELGE_STILLERI = ("sinematik-belgesel", "anlati-video-essay",
                  "seyahat-belgeseli", "veri-anlatisi", "hizli-explainer")


blok("UI-5/1 — BELGESEL MEDYA HEDEFI: %100 GERCEK VIDEO")

def _stil_blogu(sid: str) -> str:
    """EDIT_STILLERI icindeki TEK stil sozlugunun metni.

    ⚠ `pipeline` Mac'te import EDILEMEZ (/opt/vidrush yolu). Stil profili
    saf veridir; metinden okumak kanit degerini dusurmez — uzak kosum
    (konteyner) ayrica gercek nesneyi de dogrular.
    """
    # ⚠ 20 Agu 2026 duzeltmesi: eski arama TUM dosyada ilk eslesmeyi aliyordu
    # ve `GECIS_IMZALARI` sozlugundeki ayni isimli anahtara takiliyordu —
    # araya yeni bir stil ("akis") girince YANLIS blogu yakaladigi olculdu.
    # Arama artik EDIT_STILLERI govdesine CAPALI.
    _i = _PIPE.find("EDIT_STILLERI = {")
    _seg = _PIPE[_i:_PIPE.find("\nVARSAYILAN_EDIT", _i)] if _i >= 0 else _PIPE
    m = re.search(r'\n    "%s": \{([\s\S]*?)\n    \},' % re.escape(sid), _seg)
    return m.group(1) if m else ""


for _sid in BELGE_STILLERI:
    _b = _stil_blogu(_sid)
    kontrol(f"{_sid}: stil blogu bulundu", bool(_b))
    _fp = re.search(r'"footage_pct": *(\d+)', _b)
    kontrol(f"{_sid}: footage_pct == 100",
            bool(_fp) and _fp.group(1) == "100",
            f"footage_pct={_fp.group(1) if _fp else 'yok'}")
    kontrol(f"{_sid}: gorsel_yasak == True",
            re.search(r'"gorsel_yasak": *True', _b) is not None,
            "gorsel_yasak yok")

# ⚠ Gercek nesne dogrulamasi: yalnizca import EDILEBILDIGINDE (konteyner).
try:
    import pipeline                                        # noqa: E402
    _ES = pipeline.EDIT_STILLERI
    for _sid in BELGE_STILLERI:
        kontrol(f"[gercek nesne] {_sid}: footage_pct=100 + gorsel_yasak",
                (_ES.get(_sid) or {}).get("footage_pct") == 100
                and (_ES.get(_sid) or {}).get("gorsel_yasak") is True,
                str({k: v for k, v in (_ES.get(_sid) or {}).items()
                     if k in ("footage_pct", "gorsel_yasak")}))
except Exception:                                          # noqa: BLE001
    _ES = None
    print("  ..   (pipeline import yok — stiller METINDEN olculdu; "
          "gercek nesne dogrulamasi UZAK kosumda)")

blok("UI-5/2 — VIDEO YOKSA STABIL HATA (AI STATIK GORSELE DUSME YOK)")

kontrol("stabil hata kodu tanimli: MEDYA-VIDEO-YOK",
        "MEDYA-VIDEO-YOK" in _PIPE,
        "gorsel yasakta video bulunamazsa stabil kod yok")
_kod = yalniz_kod(_PIPE)
kontrol("'AI gorsele mecbur' DUSUSU KOD'DAN kalkti",
        "AI gorsele mecbur" not in _kod,
        "gorsel_yasak zinciri hala AI statik gorsele dusuyor")
kontrol("gorsel_yasak DALI (prof.get) stabil kodla bitiyor",
        re.search(r'if prof\.get\("gorsel_yasak"\)[\s\S]{0,2600}'
                  r'MEDYA_VIDEO_YOK[\s\S]{0,400}return None', _PIPE)
        is not None,
        "gorsel_yasak dali stabil kodla bitmiyor")
kontrol("bosluk nedeni (`_bosluk_yaz`) stabil kodu TASIYOR",
        re.search(r"_bosluk_yaz\(f?\"\{MEDYA_VIDEO_YOK\}", _PIPE) is not None,
        "kapsam boslugu stabil kod tasimiyor")


blok("UI-5/3 — YAS ETIKETI ADET SANILMASIN")

kontrol("'Yaşlı Kadın (75)' parantezli bicim KALKTI",
        "Yaşlı Kadın (75)" not in _PIPE,
        "parantezli yas etiketi duruyor (adet sanildi)")
kontrol("'Yaşlı Kadın — 75 yaş' bicimi VAR",
        "Yaşlı Kadın — 75 yaş" in _PIPE)
kontrol("yas etiketlerinde parantezli SAYI kalmadi (tutarli)",
        not re.search(r'"ad": "[^"]*\(\d{2}\)"', _PIPE),
        str(re.findall(r'"ad": "[^"]*\(\d{2}\)"', _PIPE)[:4]))


blok("UI-5/4 — MEDYA KAYNAGI ANA AKISTA GORUNUR")

kontrol("secim-deneyimi.js `medyaBolumu` export ediyor",
        re.search(r"export function medyaBolumu\b", _SECIM) is not None,
        "medyaBolumu yok")
kontrol("BASIT mod medyaBolumu KULLANIYOR",
        "medyaBolumu(" in _BASIT,
        "basit.js medya bolumunu cagirmiyor")
kontrol("BASIT modda medya bolumu GELISMIS ayarlarin DISINDA (gorunur)",
        _BASIT.index("medyaBolumu(") < _BASIT.index("gelismis('Gelişmiş ayarlar'")
        if ("medyaBolumu(" in _BASIT
            and "gelismis('Gelişmiş ayarlar'" in _BASIT) else False,
        "medya bolumu gizli details icinde")
kontrol("ADIM ADIM Gorsel adimi (adim3Govde) medyaBolumu KULLANIYOR",
        re.search(r"adim3Govde[\s\S]{0,1400}medyaBolumu\(", _SECIM)
        is not None,
        "adim3Govde medya bolumunu cagirmiyor")


blok("UI-5/5 — MAGNIFIC STOK SAGLAYICI GIBI SUNULMUYOR")

_mb = re.search(r"export function medyaBolumu\([\s\S]*?\n\}", _SECIM)
_mb_govde = _mb.group(0) if _mb else ""
kontrol("medyaBolumu bulundu", bool(_mb_govde))
if _mb_govde:
    _secenekler = re.findall(r"id: *'([a-z]+)'", _mb_govde)
    kontrol("medya KAYNAGI secenekleri arasinda 'magnific' YOK",
            "magnific" not in _secenekler,
            f"secenekler={_secenekler}")
    kontrol("AYRI 'Magnific iyileştirme' alani VAR",
            "Magnific iyileştirme" in _mb_govde,
            "ayri iyilestirme alani yok")
    kontrol("Magnific durumu DURUST: 'Bağlı değil'",
            "Bağlı değil" in _mb_govde)
    kontrol("Magnific: 'kredi kullanılmadı' ACIKCA yaziyor",
            "kredi kullanılmadı" in _mb_govde)
    kontrol("Magnific: ucretsiz stok VIDEO fallback'i ACIK yaziyor",
            "ücretsiz stok video" in _mb_govde.lower())
    kontrol("VIDEO HEDEFI gorunur: '%100 gerçek video'",
            "%100 gerçek video" in _mb_govde)
    kontrol("KLIP SAYACI var: 'video klip' ifadesi",
            "video klip" in _mb_govde)
    kontrol("sahte 'bağlı' iddiasi YOK",
            not re.search(r"Bağlı\b(?! değil)", _mb_govde),
            "sahte bagli gosterimi")


blok("UI-5/6 — SECIM GERCEKTEN HATTA BAGLI (yalniz CSS/metin degil)")

kontrol("secim `/api/kaynak-tercihi`ye POST ediliyor",
        "/api/kaynak-tercihi" in _SECIM,
        "secim sunucuya gitmiyor")
kontrol("CSRF basligi gonderiliyor",
        "x-csrf-token" in _SECIM)
kontrol("SESSIZ BASARI YOK: yazilamazsa stabil kod gosteriliyor",
        "UI5-KAYNAK-TERCIHI-YAZILAMADI" in _SECIM)
kontrol("provider_used / fallback_reason kullaniciya GORUNUR",
        ("saglayici" in _SECIM and "fallback" in _SECIM.lower()))


blok("UI-5/7 — ANONIM CSRF (oturumsuz modda secim kullanilabilsin)")

kontrol("server oturumsuz modda vr_csrf cerezi KURUYOR",
        re.search(r"ZORUNLU_OTURUM[\s\S]{0,900}CSRF_COOKIE", _SERVER)
        is not None
        or "_anonim_csrf" in _SERVER,
        "anonim CSRF cerezi kurulmuyor -> secim 403 alir")
kontrol("anonim CSRF cerezi HttpOnly DEGIL (double-submit okunmali)",
        re.search(r"_anonim_csrf[\s\S]{0,700}httponly=False", _SERVER)
        is not None,
        "double-submit icin JS okumali")


blok("UI-5/8 — GERILEME YOK: KORUNACAK SOZLESMELER")

_alanlar = re.search(r"export const GENERATE_ALANLARI = \[([\s\S]*?)\n\];", _API)
_n_alan = len(re.findall(r"\{ad: '", _alanlar.group(1))) if _alanlar else 0
kontrol("GERILEME YOK: /api/generate TAM 22 alan (buyumedi)",
        _n_alan == 22, f"alan sayisi={_n_alan}")
kontrol("GERILEME YOK: kaynak tercihi generate payload'ina EKLENMEDI",
        "fd.append('kaynak" not in _SECIM
        and 'fd.append("kaynak' not in _SECIM)
kontrol("GERILEME YOK: R-1e kapsam kapisi duruyor",
        "kapsam_kapisi" in _SERVER and "ANON_TENANT" in _SERVER)
kontrol("GERILEME YOK: R-1e legacy imzalayici geri gelmedi",
        "imzali_url.imzala if not ZORUNLU_OTURUM" not in _SERVER)
kontrol("GERILEME YOK: CSRF dogrulamasi hala ZORUNLU (mutasyon ucu)",
        "UI3-CSRF-GECERSIZ" in _SERVER)
kontrol("GERILEME YOK: deploy.sh degismedi (kanit: 5 asamali akis)",
        "5 Durumu imaja bas" in oku("..", "deploy.sh"))
kontrol("GERILEME YOK: UI-3 kaynak tercihi ucu duruyor",
        "/api/kaynak-tercihi" in _SERVER)
kontrol("GERILEME YOK: seyahat-belgeseli 8 sn tavani duruyor",
        _ES is None or _ES["seyahat-belgeseli"].get("maks_sahne_sn") == 8)
kontrol("GERILEME YOK: I-38 yazi spec'i sahneye goreli sabiti duruyor",
        "source-label" in _PIPE or "saha_etiketi" in _PIPE)

print(f"\n{'=' * 60}")
print(f"GECEN: {gecen}   BASARISIZ: {len(basarisiz)}   BLOKE: {len(bloke)}")
for b in basarisiz:
    print(f"  XX {b}")
for b in bloke:
    print(f"  -- BLOKE {b}")
sys.exit(1 if (basarisiz or bloke) else 0)
