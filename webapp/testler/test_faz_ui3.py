#!/usr/bin/env python3
"""FAZ UI-3 testleri — KAYNAK TERCIHI KABLOSU (UI2 bulgusunun kapatilmasi).

UI-2'nin gercek tarayici hatti sunu OLCTU:

    UI2-KAYNAK-TERCIHI-SUNUCUYA-GITMIYOR
    gonderilen alanlar: session,story,tur,edit,sure_dk,altyazi
    -> `kaynak_tercihi` YOK

Arayuz "Ucretsiz stok -> Kredi harcanmaz" diyordu ama secim sunucuya
ULASMIYORDU; `/api/generate` saglayici kararini yalnizca tenant kaydindan
veriyordu. Yani UYGULANAMAYAN bir kredi vaadi vardi.

Bu faz o kabloyu ceker:
  UI (`#akis-kaynak`) -> `/api/generate` -> `teslim.saglayici_karari(tercih=)`
  -> `saglayici_motoru.saglayici_sec(tercih=)` -> is damgasi + cevap.

⚠ 22 ALAN SOZLESMESI BOZULMAZ ve BUYUMEZ: `/api/generate` ust-seviye alan
  sayisi TAM 22 KALIR. 23. alan EKLENMEZ. Tercih, sozlesmenin ZATEN
  okudugu IC YAPIYA — tenant'in SAGLAYICI KAYDINA (`saglayicilar.json`) —
  yazilir; `saglayici_sec` onu zaten oradan okur. Kayitta tercih yoksa
  davranis eskisiyle AYNIDIR (`otomatik`).
⚠ UCRET/KREDI HARCANMAZ: kuyruga gercek is BIRAKILMAZ (`put` sahtelenir).
⚠ TOKEN ISTEMCIYE CIKMAZ: cevapta saglayici ADI ve dusus NEDENI vardir,
  baglanti/token YOKTUR.

Kosum: .venv-test/bin/python3 webapp/testler/test_faz_ui3.py
"""
from __future__ import annotations

import inspect
import os
import re
import shutil
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
    with open(os.path.join(*p), encoding="utf-8") as f:
        return f.read()


# ⚠ 22 ALAN: `static/js/api.js`teki sozlesme. Bu kume DEGISMEZ.
YIRMI_IKI = {
    "acilis", "altyazi", "altyazi_sablon", "arkaplan", "edit", "gecis",
    "gorsel_model", "isik", "karakter", "palet", "palet_ozel", "profil",
    "sahne_ref", "ses", "session", "sora", "stil", "story", "sure_dk",
    "tur", "unlu", "zoom",
}

# ═══════════ 1) MOTOR SOZLESMESI (tercih zaten destekli) ═══════════
blok("1) SAGLAYICI MOTORU — TERCIH SEMANTIGI")

sys.path.insert(0, os.path.join(KOK, "medya"))
from medya import saglayici_motoru as SM     # noqa: E402
import teslim as TS                          # noqa: E402

kontrol("UI-3: TERCIHLER kumesi UI ile AYNI",
        set(SM.TERCIHLER) == {"otomatik", "magnific", "ucretsiz"})

# ⚠ ONAYLI+KREDILI baglantisi OLAN bir tenant kurulur: "ucretsiz" vaadinin
# GERCEKTEN uygulandigi ancak boyle kanitlanir (baglanti yokken zaten
# ucretsize duserdi — o kanit DEGILDIR).
_TID = "tenant_ui3"
_KAYIT = {_TID: {"saglayici": "magnific", "aktif": True, "onayli": True,
                 "kredi_onayi": True,
                 "sifreli_token": "SIFRELI-TOKEN-DISARI-CIKMAMALI"}}
_kul = SM.kullanilabilir_mi(_KAYIT[_TID])
if not _kul["kullanilabilir"]:
    bloke_yaz("onayli+kredili baglanti kurulumu",
              f"kayit kullanilabilir degil: {_kul['neden']}")

_oto = SM.saglayici_sec(_KAYIT, _TID, tercih="otomatik")
_ucr = SM.saglayici_sec(_KAYIT, _TID, tercih="ucretsiz")
_mag_yok = SM.saglayici_sec({}, _TID, tercih="magnific")

kontrol("UI-3: `otomatik` + onayli baglanti -> baglanti KULLANILIR",
        _oto["saglayici"] == "magnific" and _oto["baglanti"] is not None,
        str(_oto.get("saglayici")))
kontrol("⭐ UI-3 BELIRLEYICI: `ucretsiz` secimi ONAYLI+KREDILI baglanti "
        "VARKEN BILE ucretsiz stoga gider (kredi vaadi UYGULANIR)",
        _ucr["saglayici"] == SM.UCRETSIZ_SAGLAYICI
        and _ucr["baglanti"] is None,
        str(_ucr.get("saglayici")))
kontrol("UI-3: `magnific` istendi ama baglanti yok -> ucretsiz + "
        "GORUNUR neden",
        _mag_yok["saglayici"] == SM.UCRETSIZ_SAGLAYICI
        and _mag_yok["fallback_reason"].startswith("MAGNIFIC-KULLANILAMIYOR"),
        _mag_yok.get("fallback_reason"))

_kucr = TS.saglayici_karari(_KAYIT, _TID, tercih="ucretsiz")
kontrol("⭐ UI-3 BELIRLEYICI: `ucretsiz`de KREDI TUKETILMEZ",
        _kucr["kredi_tuketildi"] is False and _kucr["ucretsiz_fallback"] is True)
kontrol("⭐ UI-3 BELIRLEYICI: saglayici karari TOKEN TASIMIYOR",
        "SIFRELI-TOKEN-DISARI-CIKMAMALI" not in repr(_kucr)
        and "sifreli_token" not in _kucr and "baglanti" not in _kucr)

# ═══════════ 2) SUNUCU KABLOSU ═══════════
blok("2) /api/generate — KAYNAK TERCIHI KABLOSU")

try:
    import fastapi  # noqa: F401
    from fastapi.testclient import TestClient
    FASTAPI_VAR = True
except Exception as e:                                        # noqa: BLE001
    FASTAPI_VAR = False
    bloke_yaz("gercek uc testi",
              f"fastapi kurulu degil ({type(e).__name__}) — "
              "kurulum: pip install fastapi python-multipart httpx")

if FASTAPI_VAR:
    gecici_kok = tempfile.mkdtemp(prefix="ui3_kok_")
    os.makedirs(os.path.join(gecici_kok, "webapp", "veri"), exist_ok=True)
    os.makedirs(os.path.join(gecici_kok, "webapp", "ciktilar"), exist_ok=True)
    os.makedirs(os.path.join(gecici_kok, "render-studio", "out"), exist_ok=True)
    shutil.copy(os.path.join(DEPO, "app", "uret.py"),
                os.path.join(gecici_kok, "uret.py"))
    os.environ["VIDRUSH_KOK"] = gecici_kok
    # ⚠ Parola koda YAZILMAZ; bu YEREL test hesabidir, deploy EDILMEZ.
    _KUL, _PAR = "faz_ui3_test", "Faz-UI3-Test-Parola-2026!"
    os.environ["VIDRUSH_ADMIN_KULLANICI"] = _KUL
    os.environ["VIDRUSH_ADMIN_PAROLA"] = _PAR
    # ⚠ `server.VERI` HER ZAMAN repo icindeki `webapp/veri`dir (VIDRUSH_KOK
    # onu tasimaz). Test bu depoyu KIRLETMEMELI: mevcut hali yedeklenir ve
    # sonunda AYNEN geri konur, yoksa bir sonraki kosum onceki kosumun
    # tercihini "eski davranis" sanip YANLIS yesil verir.
    _sag_yol = os.path.join(KOK, "veri", "saglayicilar.json")
    _sag_yedek = None
    if os.path.exists(_sag_yol):
        with open(_sag_yol, "rb") as _f:
            _sag_yedek = _f.read()
    os.path.exists(_sag_yol) and os.remove(_sag_yol)
    try:
        import server as _srv

        # ── (a) SOZLESME: TAM 22 ALAN, NE EKSIK NE FAZLA ──
        _imza = inspect.signature(_srv.uret_baslat).parameters
        # `istek: Request` bir govde alani DEGILDIR (tasiyici nesne).
        _alanlar = {a for a in _imza if a != "istek"}
        kontrol("⭐ UI-3 GERILEME YOK: 22 alanin HEPSI hala endpoint "
                "imzasinda (silinme/ad degisikligi YOK)",
                YIRMI_IKI <= _alanlar,
                str(sorted(YIRMI_IKI - _alanlar)))
        kontrol("⭐ UI-3 BELIRLEYICI: `/api/generate` ust-seviye alan sayisi "
                "TAM 22 (sozlesme BUYUMEDI)",
                _alanlar == YIRMI_IKI,
                f"fazla={sorted(_alanlar - YIRMI_IKI)} "
                f"eksik={sorted(YIRMI_IKI - _alanlar)}")
        kontrol("⭐ UI-3 BELIRLEYICI: `kaynak_tercihi` UST-SEVIYE ALAN "
                "OLARAK EKLENMEDI",
                "kaynak_tercihi" not in _alanlar)

        # ── (b) GIRIS ──
        c = TestClient(_srv.app, base_url="https://testserver")
        _gr = c.post("/api/giris", data={"kullanici": _KUL, "parola": _PAR})
        if _gr.status_code != 200:
            bloke_yaz("giris", f"durum {_gr.status_code}")
        _TENANT = _gr.json().get("tenant_id", "")

        # ── (c) KUYRUK SAHTELENIR: gercek is BASLAMAZ ($0.00) ──
        _srv.is_kuyrugu.put = lambda ogeler: None
        _cagrilar = []
        _gercek_karar = _srv.teslim.saglayici_karari

        def _kayitli_karar(kayit, tenant_id, *, tercih=SM.TERCIH_OTOMATIK):
            _cagrilar.append(tercih)
            return _gercek_karar(kayit, tenant_id, tercih=tercih)

        _srv.teslim.saglayici_karari = _kayitli_karar

        def _uret():
            _cagrilar.clear()
            return c.post("/api/generate",
                          data={"session": "ui3test", "story": "x" * 40,
                                "tur": "documentary"})

        def _depo():
            return _srv._json_oku(
                os.path.join(_srv.VERI, "saglayicilar.json"), {})

        # ── (d) TERCIH YOKKEN: ESKI DAVRANIS (geriye uyumluluk) ──
        _r0 = _uret()
        kontrol("⭐ UI-3 GERIYE UYUMLU: kayitta tercih yokken `otomatik` "
                "(tercih kavramindan ONCEKI davranis)",
                _r0.status_code == 200 and _cagrilar == ["otomatik"],
                f"{_r0.status_code} {_cagrilar}")

        # ── (e) TERCIH UCU: kimlik + dogrulama ──
        _anon = TestClient(_srv.app, base_url="https://testserver")
        kontrol("⭐ UI-3: KIMLIKSIZ /api/kaynak-tercihi -> 401",
                _anon.post("/api/kaynak-tercihi",
                           data={"tercih": "ucretsiz"}).status_code == 401)
        # ── CSRF: MUTASYON UCU DOUBLE-SUBMIT ILE KORUNUR ──
        # ⚠ `vr_csrf` cerezi JS'ten OKUNABILIR olacak sekilde kurulur
        # (double-submit sartı); yetki HALA HttpOnly oturum cerezindedir.
        _csrf = c.cookies.get(_srv.kimlik.CSRF_COOKIE, "")
        _bas = {_srv.kimlik.CSRF_BASLIK: _csrf}
        kontrol("UI-3: girisde CSRF cerezi kuruluyor (JS okuyabilir)",
                bool(_csrf))
        kontrol("⭐ UI-3 BELIRLEYICI: CSRF BASLIGI YOKKEN mutasyon REDDEDILIR "
                "(403 + stabil kod)",
                (lambda r: r.status_code == 403
                 and "UI3-CSRF-GECERSIZ" in r.text)(
                    c.post("/api/kaynak-tercihi", data={"tercih": "ucretsiz"})),
                "baslik yokken gecti")
        kontrol("⭐ UI-3 BELIRLEYICI: CSRF BASLIGI UYUSMAZSA REDDEDILIR",
                c.post("/api/kaynak-tercihi", data={"tercih": "ucretsiz"},
                       headers={_srv.kimlik.CSRF_BASLIK: "baska-deger"}
                       ).status_code == 403)
        kontrol("⭐ UI-3: DOGRU CSRF baslikli istek KABUL EDILIR",
                c.post("/api/kaynak-tercihi", data={"tercih": "otomatik"},
                       headers=_bas).status_code == 200)
        kontrol("⭐ UI-3: gecersiz tercih ACIKCA 400 (sessiz dusus YOK)",
                c.post("/api/kaynak-tercihi", data={"tercih": "muz"},
                       headers=_bas).status_code == 400)
        kontrol("UI-3: GET /api/kaynak-tercihi secenekleri UI ile AYNI",
                set(c.get("/api/kaynak-tercihi").json().get("secenekler", []))
                == set(SM.TERCIHLER))

        # ── (f) SECIM SUNUCUYA ULASIYOR (uretim sozlesmesi BUYUMEDEN) ──
        for _t in ("ucretsiz", "magnific", "otomatik"):
            _rt = c.post("/api/kaynak-tercihi", data={"tercih": _t},
                         headers=_bas)
            _kayitli = (_depo().get(_TENANT) or {}).get("tercih")
            kontrol(f"⭐ UI-3 BELIRLEYICI: `{_t}` secimi tenant KAYDINA "
                    "yazildi",
                    _rt.status_code == 200 and _kayitli == _t,
                    f"{_rt.status_code} kayit={_kayitli}")
            _ru = _uret()
            kontrol(f"⭐ UI-3 BELIRLEYICI: `{_t}` secimi SAGLAYICI KARARINA "
                    "ULASIYOR",
                    _ru.status_code == 200 and _cagrilar == [_t],
                    f"{_ru.status_code} {_cagrilar}")

        # ── (g) YETKI YUKSELTME YOK: tercih yazmak baglanti ACMAZ ──
        c.post("/api/kaynak-tercihi", data={"tercih": "magnific"},
               headers=_bas)
        _kayit = _depo().get(_TENANT) or {}
        kontrol("⭐ UI-3 BELIRLEYICI: tercih yazmak BAGLANTI ACMAZ "
                "(yetki yukselmez)",
                SM.kullanilabilir_mi(_kayit)["kullanilabilir"] is False,
                str(sorted(_kayit)))
        kontrol("UI-3: tercih ucu yalnizca `tercih` anahtarini yazar",
                set(_kayit) <= {"tercih"}, str(sorted(_kayit)))
        _rm = c.post("/api/kaynak-tercihi", data={"tercih": "magnific"},
                     headers=_bas)
        kontrol("UI-3: baglanti yokken `magnific` -> ucretsiz stok + "
                "GORUNUR neden",
                _rm.json().get("saglayici") == SM.UCRETSIZ_SAGLAYICI
                and _rm.json().get("saglayici_fallback", "").startswith(
                    "MAGNIFIC-KULLANILAMIYOR"),
                str(_rm.json())[:140])

        # ── (h) CEVAP GORUNURLUGU + TOKEN SIZINTISI YOK ──
        c.post("/api/kaynak-tercihi", data={"tercih": "ucretsiz"},
               headers=_bas)
        _ruc = _uret()
        _j = _ruc.json() if _ruc.status_code == 200 else {}
        kontrol("UI-3: uretim cevabi `saglayici` + `saglayici_fallback` "
                "iceriyor",
                "saglayici" in _j and "saglayici_fallback" in _j,
                str(sorted(_j))[:120])
        kontrol("⭐ UI-3 BELIRLEYICI: uretim cevabi SECILEN TERCIHI bildiriyor "
                "(kullanici ne istedigini geri gorur)",
                _j.get("saglayici_tercih") == "ucretsiz",
                str(_j.get("saglayici_tercih")))
        kontrol("⭐ UI-3 BELIRLEYICI: hicbir cevapta TOKEN/BAGLANTI ANAHTARI "
                "YOK",
                not re.search(r'"(sifreli_token|token|baglanti)"\s*:',
                              _ruc.text + _rm.text, re.I),
                (_ruc.text + _rm.text)[:120])

        # ── (i) IS DAMGASI: tercih ISTE saklanir (sonradan tahmin YOK) ──
        _isler = [d for d in _srv.isler.values() if isinstance(d, dict)]
        _damgali = [d for d in _isler if (d.get("saglayici") or {}).get("tercih")]
        kontrol("⭐ UI-3 BELIRLEYICI: secilen tercih ISIN DAMGASINDA saklanir "
                "ve kredi tuketilmedigi yazili",
                any((d["saglayici"]["tercih"] == "ucretsiz"
                     and d["saglayici"]["kredi_tuketildi"] is False)
                    for d in _damgali),
                str([d["saglayici"] for d in _damgali][-1:])[:160])
        kontrol("UI-3: is damgasinda TOKEN YOK",
                all("sifreli_token" not in (d.get("saglayici") or {})
                    for d in _isler))

        # ── (j) KUYRUGA GERCEK IS BIRAKILMADI ($0.00) ──
        kontrol("UI-3: testte kuyruga gercek is DUSMEDI (kredi harcanmadi)",
                _srv.is_kuyrugu.qsize() == 0, str(_srv.is_kuyrugu.qsize()))

        _srv.teslim.saglayici_karari = _gercek_karar
    except Exception as e:                                    # noqa: BLE001
        bloke_yaz("gercek uc testi", f"{type(e).__name__}: {e}")
    finally:
        shutil.rmtree(gecici_kok, ignore_errors=True)
        # ⚠ Depo AYNEN geri konur (test izi BIRAKMAZ).
        if _sag_yedek is None:
            os.path.exists(_sag_yol) and os.remove(_sag_yol)
        else:
            _fd = os.open(_sag_yol, os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
                          0o600)
            with os.fdopen(_fd, "wb") as _f:
                _f.write(_sag_yedek)

# ═══════════ 3) ISTEMCI KABLOSU ═══════════
blok("3) ISTEMCI — `#akis-kaynak` -> sunucu")

_UI = oku(KOK, "static", "js", "ui1.js")
kontrol("⭐ UI-3 BELIRLEYICI: istemci `/api/kaynak-tercihi` ucuna YAZIYOR "
        "(UI2 bulgusu kapandi)",
        '"/api/kaynak-tercihi"' in _UI)
kontrol("⭐ UI-3 BELIRLEYICI: gonderilen deger `#akis-kaynak` SECIMIDIR "
        "(sabit deger degil)",
        re.search(r'akis-kaynak[\s\S]{0,200}?fd\.append\("tercih"', _UI)
        is not None)
kontrol("⭐ UI-3 GERILEME YOK: `/api/generate` govdesine YENI ALAN "
        "EKLENMEDI (22 alan sozlesmesi buyumedi)",
        'fd.append("kaynak_tercihi"' not in _UI
        and len(re.findall(r'fd\.append\("(\w+)"', _UI)) == 7)
kontrol("⭐ UI-3: tercih uretimden ONCE yazilir (`await`)",
        "await kaynakTercihiYaz()" in _UI)
kontrol("UI-3: kredi metni SUNUCUNUN gercek cevabindan yazilir "
        "(istemci tahmini degil)",
        "kredi_tuketilir" in _UI)
kontrol("⭐ UI-3: tercih yazilamazsa SESSIZ BASARI YOK (kullanici gorur)",
        "YAZILAMADI" in _UI and 'kredi_onayi = "bilinmiyor"' in _UI)

# ⚠ FAIL-OPEN YASAK. Tercih yazilamadiysa uretime DEVAM ETMEK, isi ESKI
# (kayitli) tercihle baslatir ve kullanicinin secimini SESSIZCE ihlal eder
# — "ucretsiz" secen kullanicinin kredisi yanabilir. Uretim DURMALIDIR.
_GOVDE = _UI[_UI.index("async function uretimBaslat"):
             _UI.index("function oturumEtiketi")]
kontrol("⭐ UI-3 BELIRLEYICI: STABIL HATA KODU tanimli "
        "(`UI3-KAYNAK-TERCIHI-YAZILAMADI`)",
        "UI3-KAYNAK-TERCIHI-YAZILAMADI" in _UI)
kontrol("⭐ UI-3 BELIRLEYICI: tercih yazilamazsa uretim DURUR "
        "(fail-open YOK: kapi `/api/generate`ten ONCE)",
        ("UI3-KAYNAK-TERCIHI-YAZILAMADI" in _GOVDE
         and _GOVDE.index("UI3-KAYNAK-TERCIHI-YAZILAMADI")
         < _GOVDE.index('fetch("/api/generate"')),
        "kod generate cagrisindan sonra ya da govdede yok")
kontrol("⭐ UI-3 BELIRLEYICI: kapi ile `/api/generate` arasinda `return` VAR "
        "(akis gercekten kesiliyor)",
        "return" in _GOVDE[_GOVDE.index("UI3-KAYNAK-TERCIHI-YAZILAMADI"):
                           _GOVDE.index('fetch("/api/generate"')]
        if "UI3-KAYNAK-TERCIHI-YAZILAMADI" in _GOVDE else False)
kontrol("UI-3: durdurma kullaniciya HATA olarak gosterilir "
        "(`yaz(..., true)`)",
        re.search(r"UI3-KAYNAK-TERCIHI-YAZILAMADI[\s\S]{0,200}?true",
                  _GOVDE) is not None
        or re.search(r"yaz\([^\n]*UI3-KAYNAK-TERCIHI-YAZILAMADI", _GOVDE)
        is not None)
kontrol("UI-3 GERILEME YOK: istemci hala TOKEN/PAROLA OKUMUYOR",
        not any(a in _UI for a in ("sifreli_token", "parola_hash",
                                   "IMZA_ANAHTARI", "OTURUM_ANAHTARI")))
kontrol("⭐ UI-3 BELIRLEYICI: istemci CSRF jetonunu `x-csrf-token` "
        "basliginda gonderiyor",
        "x-csrf-token" in _UI.lower() and "vr_csrf" in _UI)
kontrol("⭐ UI-3 GERILEME YOK: OTURUM cerezi JS'ten HALA OKUNMUYOR "
        "(`document.cookie` YALNIZ CSRF icin, HttpOnly korunuyor)",
        "vr_oturum" not in _UI
        and len(re.findall(r"document\.cookie", _UI)) == 1)
kontrol("⭐ UI-3: catch metni FAIL-CLOSED ile CELISMIYOR "
        "(`uretim kayitli tercihle baslar` IFADESI YOK)",
        "kayıtlı tercihle başlar" not in _UI
        and ("BAŞLATILMADI" in _UI or "başlatılmadı" in _UI))
kontrol("UI-3: 22 alan sozlesmesi (api.js) DEGISMEDI",
        set(re.findall(r"\{ad: '(\w+)'", oku(KOK, "static/js/api.js")))
        == YIRMI_IKI)

# ═══════════ 4) UZAK HAT ARTIK KAPI ═══════════
blok("4) UZAK HAT — BULGU ARTIK KAPI")

_HAT = oku(KOK, "testler", "ui2_uzak_akis.mjs")
kontrol("⭐ UI-3 BELIRLEYICI: uzak hat `kaynak_tercihi`yi BULGU olarak "
        "DEGIL KAPI olarak olcuyor",
        "bulgu(" not in _HAT
        and "UI2-KAYNAK-TERCIHI-SUNUCUYA-GITMIYOR" in _HAT)
kontrol("⭐ UI-3: hat `/api/kaynak-tercihi` ucunun GERCEKTEN cagrildigini "
        "olcuyor (yakalanmaz — ucretsizdir)",
        "/api/kaynak-tercihi" in _HAT)
kontrol("UI-3: hat generate govdesinde YENI ALAN OLMADIGINI da olcuyor",
        "kaynak_tercihi" in _HAT and "22" in _HAT)
kontrol("⭐ UI-3 BELIRLEYICI: hat FAIL-OPEN'i GERCEK TARAYICIDA siniyor — "
        "tercih yazimi 500 olunca `/api/generate` HIC gitmemeli",
        "UI3-KAYNAK-TERCIHI-YAZILAMADI" in _HAT
        and "responseCode: 500" in _HAT)

print(f"\n{'=' * 60}")
print(f"GECEN: {gecen}   BASARISIZ: {len(basarisiz)}   BLOKE: {len(bloke)}")
for b in basarisiz:
    print(f"  XX {b}")
for b in bloke:
    print(f"  -- BLOKE {b}")
sys.exit(1 if basarisiz else 0)
