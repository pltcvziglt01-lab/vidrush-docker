#!/usr/bin/env python3
"""FAZ UI-2 testleri — UZAK GERCEK TARAYICI KANIT HATTI.

UI-1 `/akis` sayfasini KAYNAK duzeyinde dogrulamisti (dize aramasi). Bu faz
onu GERCEK bir tarayicida, GERCEK staging uclarina karsi kosturan hatti
kurar ve masaustu + mobil GORSEL kanit uretir.

⚠ DEGISMEZ KURALLAR (test bunlari KILITLER):
  1. Mac'e screenshot/medya/QA artefakti YAZILMAZ. Yakalama da, kanit da
     UZAK ortamda (staging konteyneri -> staging host diski) kalir.
  2. UCRETLI API/KREDI HARCANMAZ. Paranin harcandigi TEK sinir
     `POST /api/generate`tir; hat o istegi tarayici icinde YAKALAR ve
     sunucuya GECIRMEZ (test-double). Zincirin geri kalani — is izleme,
     QA, imzali indirme, son-3 — GERCEK sunucuya gider.
  3. CREDENTIAL YOK: gercek kullanici adi/parola OKUNMAZ, URETILMEZ,
     YAZDIRILMAZ. Oturum sunucu tarafinda, diskteki MEVCUT anahtarla
     uretilir (`uret=False` — yeni anahtar URETILMEZ, canli oturumlar
     gecersiz kilinmaz).
  4. Kimlik/tenant/is kimligi ekrana MASKELI cikar.

Kosum: python3 webapp/testler/test_faz_ui2.py
"""
from __future__ import annotations

import os
import re
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
    with open(os.path.join(*p), encoding="utf-8") as f:
        return f.read()


T = os.path.join(KOK, "testler")
YOL_ON = os.path.join(T, "ui2_onkontrol.py")
YOL_HAT = os.path.join(T, "ui2_uzak_akis.mjs")
YOL_KOS = os.path.join(T, "ui2_kos.sh")

# ⚠ RED-FIRST: bu uc dosya YOKKEN test kirmizidir. Uretim kodu once
# YAZILMAZ; kapi once konur.
for _ad, _y in (("onkontrol", YOL_ON), ("uzak hat", YOL_HAT),
                ("kosucu", YOL_KOS)):
    kontrol(f"UI-2: {_ad} dosyasi var ({os.path.basename(_y)})",
            os.path.isfile(_y), _y)

if basarisiz:
    print(f"\n{'=' * 60}")
    print(f"GECEN: {gecen}   BASARISIZ: {len(basarisiz)}   BLOKE: {len(bloke)}")
    for b in basarisiz:
        print(f"  XX {b}")
    print("\n⚠ RED-FIRST: hat henuz kurulmadi.")
    sys.exit(1)

ON = oku(YOL_ON)
HAT = oku(YOL_HAT)
KOS = oku(YOL_KOS)
HEPSI = ON + HAT + KOS

# ═══════════ (1) MAC'E ARTEFAKT YASAGI ═══════════
blok("1) MAC'E ARTEFAKT YASAGI")

kontrol("⭐ UI-2 BELIRLEYICI: hicbir dosya Mac yoluna yazmiyor "
        "(/Users/... hedefi YOK)",
        "/Users/" not in HEPSI)
kontrol("UI-2: kanit dizini UZAK yol olarak tanimli (/tmp/ui2_kanit "
        "konteynerde, /root/ui2_kanit staging host'unda)",
        "/root/ui2_kanit" in KOS and "/tmp/ui2_kanit" in KOS)
# `docker cp` YALNIZ konteyner -> staging host yonunde olmali; kanitin
# Mac'e inmesi icin kullanilacak bir `scp ...:... .` cagrisi OLMAMALI.
kontrol("⭐ UI-2 BELIRLEYICI: kanit Mac'e CEKILMIYOR (uzaktan-yerele scp/"
        "rsync YOK)",
        not re.search(r"scp[^\n]*root@[^\n]*:[^\n]*\s+[.~/]|rsync[^\n]*"
                      r"root@[^\n]*:", KOS))
kontrol("UI-2: kanit konteynerden staging HOST diskine tasinir "
        "(`docker cp` — tek yon)",
        "docker cp" in KOS and "KANIT_HOST" in KOS)
kontrol("⭐ UI-2 BELIRLEYICI: jetonu tasiyan ayar dosyasi kanit dizinine "
        "YAZILMAZ ve kosum sonunda SILINIR",
        "UI2_AYAR" in KOS and "rm -f $AYAR" in KOS
        and "KANIT dizinine YAZILMAZ" in ON)

# ═══════════ (2) UCRETLI SINIR: /api/generate YAKALANIR ═══════════
blok("2) UCRETLI SINIR — KREDI HARCANMAZ")

kontrol("⭐ UI-2 BELIRLEYICI: `/api/generate` tarayici icinde YAKALANIR "
        "(CDP Fetch alani)",
        "Fetch.enable" in HAT and "/api/generate" in HAT)
kontrol("⭐ UI-2 BELIRLEYICI: yakalanan istek sunucuya GECIRILMEZ, "
        "test-double ile karsilanir (`Fetch.fulfillRequest`)",
        "Fetch.fulfillRequest" in HAT)
kontrol("UI-2: `Fetch.continueRequest` /api/generate icin KULLANILMAZ "
        "(gecirseydi kredi yanardi)",
        not re.search(r"generate[\s\S]{0,400}?Fetch\.continueRequest", HAT))
kontrol("UI-2: kredi sinirinin asilmadigi OLCULUR "
        "(is sayisi once/sonra karsilastirilir)",
        "is_sayisi_once" in HEPSI and "is_sayisi_sonra" in HEPSI)
kontrol("UI-2: test-double GERCEK ve TAMAMLANMIS bir isin kimligini "
        "kullanir (uydurma is kimligi YOK)",
        "UI2_IS_ID" in HAT and "UI2_IS_ID" in ON)

# ═══════════ (3) CREDENTIAL YOK — SUNUCU TARAFLI OTURUM ═══════════
blok("3) CREDENTIALSIZ TEST OTURUMU")

kontrol("⭐ UI-2 BELIRLEYICI: oturum sunucu tarafinda uretilir "
        "(`kimlik.oturum_uret`), parola KULLANILMAZ",
        "oturum_uret" in ON)
kontrol("⭐ UI-2 BELIRLEYICI: MEVCUT anahtar okunur, YENI anahtar "
        "URETILMEZ (`uret=False`) — canli oturumlar bozulmaz",
        "uret=False" in ON)
kontrol("UI-2: parola/hash/anahtar HICBIR yerde yazdirilmaz",
        not re.search(r"print\([^\n]*(parola|hash|anahtar|token|jeton)",
                      ON, re.I))
kontrol("UI-2: jeton diske 0600 ile yazilir (stdout'a DEGIL)",
        "0o600" in ON)
kontrol("UI-2: gecersiz giris denemesi GERCEK bir kullanici adi "
        "kullanmaz (hiz siniri kovasi kirletilmez)",
        "ui2-gecersiz-" in HAT)

# ═══════════ (4) MASAUSTU + MOBIL GORSEL KANIT ═══════════
blok("4) MASAUSTU + MOBIL KANIT")

kontrol("⭐ UI-2 BELIRLEYICI: masaustu 1280x800 yakalanir",
        "1280" in HAT and "800" in HAT)
kontrol("⭐ UI-2 BELIRLEYICI: mobil 390x844 yakalanir",
        "390" in HAT and "844" in HAT)
kontrol("UI-2: mobil pasta GERCEK mobil emulasyonu var "
        "(`Emulation.setDeviceMetricsOverride`, mobile:true)",
        "Emulation.setDeviceMetricsOverride" in HAT
        and re.search(r"mobil(e)?:\s*true", HAT) is not None)
kontrol("UI-2: her iki pastada da ekran goruntusu alinir "
        "(`Page.captureScreenshot`)",
        "Page.captureScreenshot" in HAT)
_asamalar = ("kimliksiz", "akis", "ayarlar", "sonuc")
for _a in _asamalar:
    kontrol(f"UI-2: `{_a}` asamasinin ekran goruntusu var",
            f'"{_a}"' in HAT or f"'{_a}'" in HAT, _a)

# ═══════════ (5) E2E ZINCIRI ═══════════
blok("5) UCTAN UCA ZINCIR")

_uclar = ("/akis", "/giris", "/api/giris", "/api/job/", "/api/kutuphane")
for _u in _uclar:
    kontrol(f"UI-2: zincir `{_u}` ucuna gercekten gider",
            _u in HAT, _u)
kontrol("UI-2: ilerleme GERCEK `/api/job/{id}` cevabindan okunur "
        "(aria-valuenow)",
        "aria-valuenow" in HAT)
kontrol("UI-2: QA hukmu okunur (`data-teslim_ok`)",
        "teslim_ok" in HAT)
kontrol("⭐ UI-2 BELIRLEYICI: indirme baglantisi IMZALI olmali; ham "
        "`ciktilar/` yolu KABUL EDILMEZ",
        "ciktilar/" in HAT and "imza" in HAT.lower())
kontrol("UI-2: imzali URL uc durumda sinanir — oturumla 200, "
        "oturumsuz 401/403, imza bozulunca 403",
        "401" in HAT and "403" in HAT and "200" in HAT)
kontrol("UI-2: son-3 listesi GERCEK `/api/kutuphane`den doldurulur",
        "akis-kutuphane" in HAT)

# ═══════════ (6) ERISILEBILIRLIK + RESPONSIVE SOZLESMESI ═══════════
blok("6) ERISILEBILIRLIK + RESPONSIVE")

kontrol("UI-2: 6 adim gostergesi canli DOM'da sayilir",
        "data-adim" in HAT)
kontrol("UI-2: her form alaninin `label[for]` bagi CANLI DOM'da dogrulanir "
        "(kaynak dizesi degil)",
        "labels" in HAT or "label[for" in HAT)
kontrol("UI-2: `role=progressbar` canli DOM'da aranir",
        "progressbar" in HAT)
kontrol("⭐ UI-2 BELIRLEYICI: mobilde YATAY TASMA olcumu var "
        "(scrollWidth > innerWidth => hata)",
        "scrollWidth" in HAT and "innerWidth" in HAT)
kontrol("UI-2: dokunma hedefi en az 44 px olcumu var",
        "44" in HAT)
kontrol("UI-2: konsol hatalari sayilir (0 olmali)",
        "Runtime.consoleAPICalled" in HAT or "Log.entryAdded" in HAT)

# ═══════════ (7) GUVENLIK: TOKEN/TENANT SIZINTISI ═══════════
blok("7) TENANT / TOKEN GUVENLIGI")

kontrol("⭐ UI-2 BELIRLEYICI: tenant ve is kimligi ciktida MASKELENIR",
        "maske" in HAT.lower() and "maske" in ON.lower())
kontrol("UI-2: canli sayfa kaynaginda token/parola izi ARANIR",
        "sifreli_token" in HAT and "parola_hash" in HAT)
kontrol("UI-2: oturum cerezi HttpOnly kurulur "
        "(JS'ten okunamadigi dogrulanir)",
        "httpOnly" in HAT and "document.cookie" in HAT)

# ═══════════ (8) STABIL HATA KODLARI ═══════════
blok("8) STABIL HATA KODLARI")

# ⚠ Kodlar DONDURULMUS kumedir: rapor tuketicileri (CI, handoff) bunlara
# gore ayrisir. Kod adi degistirmek GERILEMEDIR.
KODLAR = (
    "UI2-OTURUM-ANAHTARI-YOK",
    "UI2-STAGING-TEST-SESSION-YOK",
    "UI2-BITMIS-IS-YOK",
    "UI2-KIMLIK-KAPISI-ACIK",
    "UI2-GECERSIZ-GIRIS-STABIL-DEGIL",
    "UI2-ADIM-EKSIK",
    "UI2-ETIKET-BAGI-YOK",
    "UI2-PROGRESSBAR-YOK",
    "UI2-MOBIL-YATAY-TASMA",
    "UI2-DOKUNMA-HEDEFI-KUCUK",
    "UI2-KREDI-METNI-DEGISMIYOR",
    "UI2-GENERATE-SUNUCUYA-SIZDI",
    "UI2-IS-IZLEME-YOK",
    "UI2-QA-GORUNMUYOR",
    "UI2-IMZASIZ-INDIRME",
    "UI2-IMZALI-URL-200-DEGIL",
    "UI2-IMZASIZ-ERISIM-ACIK",
    "UI2-SON3-YOK",
    "UI2-KONSOL-HATASI",
    "UI2-TOKEN-SIZINTISI",
    "UI2-KAYNAK-TERCIHI-SUNUCUYA-GITMIYOR",
)
for _k in KODLAR:
    kontrol(f"UI-2 kod: `{_k}` tanimli", _k in HEPSI, _k)
kontrol("⭐ UI-2 BELIRLEYICI: hukum makine-okunur JSON olarak yazilir "
        "(`sonuc.json`)",
        "sonuc.json" in HAT)
kontrol("UI-2: hukumde PASS/FAIL ve OLCULEMEDI AYRI sayilir "
        "(olculemedi PASS sayilmaz)",
        "olculemedi" in HAT.lower())

# ═══════════ (9) GERILEME YOK ═══════════
blok("9) GERILEME YOK")

kontrol("UI-2 GERILEME YOK: 22 alan `generate` sozlesmesi DEGISMEDI",
        len(set(re.findall(r"\{ad: '(\w+)'",
                           oku(KOK, "static/js/api.js")))) == 22)
kontrol("UI-2 GERILEME YOK: `/akis` sayfasi ve `ui1.js` bu fazda "
        "DEGISTIRILMEDI (hat yalnizca OLCER)",
        "akis-form" in oku(KOK, "static", "js", "ui1.js")
        and "_AKIS_HTML" in oku(KOK, "server.py"))
kontrol("UI-2 GERILEME YOK: hat `webapp/testler/` altinda — deploy.sh "
        "test betiklerini canliya GONDERMEZ",
        "'/testler/' not in y" in oku(KOK, "..", "deploy.sh"))

print(f"\n{'=' * 60}")
print(f"GECEN: {gecen}   BASARISIZ: {len(basarisiz)}   BLOKE: {len(bloke)}")
for b in basarisiz:
    print(f"  XX {b}")
for b in bloke:
    print(f"  -- BLOKE {b}")
sys.exit(1 if basarisiz else 0)
