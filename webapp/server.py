#!/usr/bin/env python3
"""Vidrush/BEDOSAHO Web sunucusu (FastAPI).
Kullanici HER video icin karakter (opsiyonel) + stil (opsiyonel) gorselini DOGRUDAN yukler
(KALICI KAYIT YOK), metni + turu + gecis/zoom/sure tercihlerini verir. Uretim tek-cekirdek
VPS'i korumak icin sirayla (kuyruk) yapilir.
"""
import os
import io
import re
import time
import queue
import shutil
import asyncio
import threading
import traceback
from typing import List

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from PIL import Image

import pipeline
import anim_studyo
import imzali_url
import is_sozlesme   # Faz H: tek tip, geriye donuk uyumlu is sozlesmesi
import saglik_derin  # Faz H: bagimliliklari GERCEKTEN olcen saglik ucu
import girdi_analizi # Faz H: otomatik girdi analizi (LLM YOK, ucretsiz)
import kimlik        # Faz R-1c-a: Argon2id parola + oturum + tenant izolasyonu
import kutuphane     # Faz R-1c-b: tenant basina son 3 kabul edilmis video
import teslim        # Faz R-1d-a: zinciri UCTAN UCA baglayan teslim atomu

KOK = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(KOK, "static")
VERI = os.path.join(KOK, "veri")
GECICI = os.path.join(VERI, "gecici")     # is basina yuklenen gorseller (uretim sonrasi silinir)
IS_DURUM_DIR = os.path.join(VERI, "durumlar")
# ⚠ FAZ R-1a: cikti baglantilarini imzalayan anahtar. env -> veri/.imza_anahtari
# -> URETILIR. Anahtar hicbir yerde LOGLANMAZ, repoda DEGIL.
_IMZA_HAZIR = imzali_url.anahtar_kur(VERI)  # job state diske yazilir (restart'ta kaybolmasin)
os.makedirs(GECICI, exist_ok=True)
os.makedirs(IS_DURUM_DIR, exist_ok=True)

# ⚠ FAZ R-1d-a — TESLIM ZINCIRI. Oturum jetonunu muhurleyen anahtar (imza
# anahtarindan AYRI): env -> veri/.oturum_anahtari (0600) -> uretilir.
_OTURUM_HAZIR = teslim.anahtar_kur(VERI)
KULLANICI_DOSYA = os.path.join(VERI, "kullanicilar.json")
KUTUPHANE_DOSYA = os.path.join(VERI, "kutuphane.json")
# ⚠ ZORUNLU OTURUM varsayilan ACIK (R-1c-a fail-closed sozlesmesi). Kapatmak
# ACIK bir karardir ve `/api/saglik`ta GORUNUR — sessizce korumasiz calismaz.
ZORUNLU_OTURUM = os.environ.get("ZORUNLU_OTURUM", "1").lower() not in (
    "0", "false", "hayir", "off")
# ⚠ COOKIE `Secure` BAYRAGI — VARSAYILAN ACIK (kimlik.COOKIE_BAYRAKLARI).
# OLCULEN SORUN: bu kurulum HTTPS'siz (duz HTTP, IP uzerinden). Tarayici ve
# uzak istemciler `Secure` cerezi duz HTTP'de SAKLAMAZ; giris 200 doner ama
# sonraki istek 401 alir — yani oturum HIC KURULAMAZ (olculdu: uzak IP'den
# korumali uc 401).
# ⚠ Bayragi kapatmak oturum cerezinin duz metin tasinmasi demektir; bu ACIK
# bir karardir, SESSIZ bir zayiflama DEGIL: `/api/saglik` `cookie_secure`
# alanini ve baslangic logu uyariyi GOSTERIR. Kalici cozum HTTPS'tir.
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "1").lower() not in (
    "0", "false", "hayir", "off")
COOKIE_BAYRAKLARI = dict(kimlik.COOKIE_BAYRAKLARI, secure=COOKIE_SECURE)
if not COOKIE_SECURE:
    print("  ⚠ KIMLIK: COOKIE_SECURE=0 — oturum cerezi duz HTTP'de de "
          "gonderilecek. Bu GECICI bir kurulum tavizidir; HTTPS sart.")
# Signed URL omru (R-1a varsayilani).
IMZA_TTL_SN = imzali_url.VARSAYILAN_TTL_SN

_kimlik_kilidi = threading.Lock()
_giris_denemeleri: dict = {}     # hiz siniri durumu (kimlik.py durum tutmaz)

MAKS_UPLOAD = 20 * 1024 * 1024   # 20 MB gorsel tavani (OOM korumasi)

# ⚠ Isci thread'leri modulun SONUNDA baslatiliyor ama /api/saglik onlardan
# ONCE tanimlaniyor. Isim modul yuklenirken cozulmedigi icin sorun cikmaz,
# yine de erken bir istek NameError almasin diye burada 0 ile baslatilir.
_ISCI_SAYISI = 0

app = FastAPI(title="BEDOSAHO AI")

isler = {}
is_kuyrugu = queue.Queue()

_SES_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def _durum_kaydet(is_id):
    """Job state'i diske yaz — restart'ta poll 404 vermesin."""
    try:
        import json
        with open(os.path.join(IS_DURUM_DIR, f"{is_id}.json"), "w", encoding="utf-8") as f:
            json.dump(isler.get(is_id, {}), f, ensure_ascii=False)
    except Exception:
        pass


def _durumlari_yukle():
    """Baslangicta diskteki job state'leri geri yukle. Yarim kalmis (kuyrukta/uretiliyor)
    isler restart'ta kuyruktan dustugu icin 'hata' olarak isaretlenir — kullanici sonsuz
    poll yerine net mesaj gorur."""
    import json
    try:
        for ad in os.listdir(IS_DURUM_DIR):
            if not ad.endswith(".json"):
                continue
            try:
                with open(os.path.join(IS_DURUM_DIR, ad), encoding="utf-8") as f:
                    d = json.load(f)
                if d.get("durum") in ("kuyrukta", "uretiliyor"):
                    d.update({"durum": "hata", "mesaj": "Sunucu yeniden başladı",
                              "hata": "Üretim sırasında sunucu yeniden başladı — lütfen videoyu tekrar başlatın."})
                    # DISKE DE YAZ: aksi halde dosya sonsuza dek 'uretiliyor' kalir ve
                    # deploy.sh'in "aktif is var" korumasi kalici olarak deploy'u engeller.
                    try:
                        with open(os.path.join(IS_DURUM_DIR, ad), "w", encoding="utf-8") as g:
                            json.dump(d, g, ensure_ascii=False)
                    except Exception:
                        pass
                isler[ad[:-5]] = d
            except Exception:
                pass
    except Exception:
        pass


def _eski_ciktilari_temizle(gun=14):
    """Disk dolmasin: 14 gunden eski cikti + durum dosyalarini sil."""
    try:
        sinir = time.time() - gun * 86400
        for kok in (pipeline.CIKTI_DIR, IS_DURUM_DIR, os.path.join(pipeline.STUDYO, "out")):
            if not os.path.isdir(kok):
                continue
            for ad in os.listdir(kok):
                yol = os.path.join(kok, ad)
                try:
                    if os.path.isfile(yol) and os.path.getmtime(yol) < sinir:
                        os.remove(yol)
                except Exception:
                    pass
    except Exception:
        pass


def gecerli_session(session: str) -> str:
    if not _SES_RE.match(session or ""):
        raise HTTPException(400, "gecersiz session")
    return session


Image.MAX_IMAGE_PIXELS = 40_000_000   # ~40 MP tavan: sikistirma-bombasi upload'u OOM yapmasin


def _kucult(data: bytes, hedef: str, boyut=1024):
    im = Image.open(io.BytesIO(data))
    im.draft("RGB", (boyut, boyut))   # dusuk olcekte coz -> daha az RAM
    im = im.convert("RGB")
    im.thumbnail((boyut, boyut))
    im.save(hedef, "PNG")


_OZEL_SES_RE = re.compile(r"^ozel:(elevenlabs|minimax|fishaudio|kokoro|vbee|clone|edge)_[A-Za-z0-9_.-]{1,80}$")


def _ses_secimi(ses: str) -> str:
    """Ses form alanini dogrula: SESLER anahtari VEYA kutuphaneden 'ozel:<voice_id>' secimi."""
    s = (ses or "").strip()
    if s in pipeline.SESLER or _OZEL_SES_RE.match(s):
        return s
    return ""


def _bayrak(v) -> bool:
    return str(v).lower() in ("1", "true", "on", "evet", "yes")


# ═════════ FAZ R-1d-a — KIMLIK DEPOSU + ZORUNLU OTURUM KAPISI ═══════════
# ⚠ Depo dosyalari 0600: parola HASH'i disinda hicbir sey tutmaz, DUZ METIN
# parola ne saklanir ne loglanir (R-1c-a sozlesmesi).

def _json_oku(yol, varsayilan):
    try:
        import json
        with open(yol, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return varsayilan


def _json_yaz_0600(yol, veri):
    try:
        import json
        fd = os.open(yol, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(veri, f, ensure_ascii=False)
        return True
    except OSError:
        return False


def _kullanicilar():
    return _json_oku(KULLANICI_DOSYA, {})


def _kutuphane_oku():
    return _json_oku(KUTUPHANE_DOSYA, {})


def _kutuphane_yaz(d):
    return _json_yaz_0600(KUTUPHANE_DOSYA, d)


def _saglayici_kayitlari():
    """Tenant -> provider baglantisi (R-1b registry deposu).

    ⚠ GERCEK OAuth AKISI BU ATOMDA YOK: dosya yoksa depo BOS'tur ve her
    tenant ucretsiz stok fallback'ine duser. "Magnific bagli" gibi kanitsiz
    bir iddia URETILMEZ — `fallback_reason` bunu acikca yazar.
    """
    return _json_oku(os.path.join(VERI, "saglayicilar.json"), {})


def _provizyon():
    """Ilk hesabi env'den ac (`VIDRUSH_ADMIN_KULLANICI`/`_PAROLA`).

    ⚠ Parola koda/commit'e YAZILMAZ; yalnizca env'den okunur ve ANINDA
    hash'lenir. Hesap zaten varsa DOKUNULMAZ (parola SIFIRLANMAZ).
    """
    if not os.environ.get("VIDRUSH_ADMIN_KULLANICI"):
        return {"acildi": False, "neden": "ENV-YOK"}
    with _kimlik_kilidi:
        depo = _kullanicilar()
        ad = os.environ["VIDRUSH_ADMIN_KULLANICI"].strip()
        if ad in depo:
            return {"acildi": False, "neden": "ZATEN-VAR"}
        g = kimlik.provisioning_girdisi()
        if not g["hazir"]:
            print(f"  KIMLIK: hesap acilamadi — {g['neden']}")
            return {"acildi": False, "neden": g["neden"]}
        depo[g["kayit"]["kullanici"]] = {
            "parola_hash": g["kayit"]["parola_hash"],
            "tenant_id": g["kayit"]["tenant_id"]}
        _json_yaz_0600(KULLANICI_DOSYA, depo)
        print(f"  KIMLIK: hesap acildi ({g['kayit']['kullanici']}, "
              f"kdf={kimlik.kdf_adi()})")
        return {"acildi": True, "neden": ""}


def _oturum_jetonu(istek: Request) -> str:
    return istek.cookies.get(kimlik.OTURUM_COOKIE, "") if istek else ""


def _tenant(istek: Request) -> str:
    """Istegin tenant kimligi. ⚠ ZORUNLU OTURUM acikken kimliksiz = 401.

    Kapaliyken (`ZORUNLU_OTURUM=0`) bos string doner ve cagiran taraf eski
    davranisi surdurur — bu ACIK bir karardir, sessiz bir bosluk degil.
    """
    d = teslim.oturum_kapisi(_oturum_jetonu(istek))
    if d["izin"]:
        return d["tenant_id"]
    if not ZORUNLU_OTURUM:
        return ""
    # ⚠ Sunucu tarafi eksikligi (anahtar/KDF) ile kullanici tarafi eksikligi
    # (jeton yok/bozuk) AYIRT EDILIR: ilki 503, ikincisi 401.
    if d["neden"] in ("OTURUM-ANAHTARI-YOK", kimlik.KDF_HATA_KODU):
        raise HTTPException(503, f"oturum altyapisi hazir degil: {d['neden']}")
    raise HTTPException(401, f"giris gerekli: {d['neden'] or 'OTURUM-YOK'}")


def _imzalayici(tenant_id: str):
    """Tenant'a BAGLI imzalayici; tenant yoksa eski (tenant'siz) imzalayici."""
    im = teslim.imzalayici_kur(tenant_id, ttl_sn=IMZA_TTL_SN)
    return im or (imzali_url.imzala if not ZORUNLU_OTURUM else None)


@app.post("/api/giris")
async def giris(istek: Request, kullanici: str = Form(...),
                parola: str = Form(...)):
    """Giris. ⚠ Hiz sinirli, sabit-zamanli, parola LOGLANMAZ.

    Basarili girisde HttpOnly+SameSite oturum cerezi ve CSRF cerezi kurulur.
    """
    if not teslim.hazir():
        raise HTTPException(503, "oturum anahtari kurulmadi")
    if not kimlik.kdf_hazir():
        # ⚠ FAIL-CLOSED: zayif bir algoritmaya DUSULMEZ.
        raise HTTPException(503, kimlik.KDF_HATA_KODU)
    ad = (kullanici or "").strip()
    ip = (istek.client.host if istek and istek.client else "?")
    with _kimlik_kilidi:
        hs = kimlik.hiz_siniri(_giris_denemeleri, f"{ip}|{ad}")
    if not hs["izin"]:
        raise HTTPException(429, f"cok fazla deneme, {hs['bekle_sn']} sn bekleyin")
    kayit = _kullanicilar().get(ad) or {}
    # ⚠ Kullanici yoksa da parola dogrulamasi CALISTIRILIR (zamanlama farki
    # kullanici adi varligini SIZDIRMASIN).
    ok = kimlik.parola_dogrula(parola, kayit.get("parola_hash") or "")
    if not ok or not kayit.get("tenant_id"):
        with _kimlik_kilidi:
            kimlik.hiz_siniri_isle(_giris_denemeleri, f"{ip}|{ad}")
        raise HTTPException(401, "kullanici adi ya da parola hatali")
    jeton = kimlik.oturum_uret(kayit["tenant_id"], anahtar=teslim.anahtar())
    csrf = kimlik.csrf_uret()
    cevap = JSONResponse({"ok": True, "tenant_id": kayit["tenant_id"]})
    cevap.set_cookie(kimlik.OTURUM_COOKIE, jeton,
                     max_age=kimlik.OTURUM_OMRU_SN, path="/",
                     **COOKIE_BAYRAKLARI)
    # ⚠ CSRF cerezi JS tarafindan OKUNABILIR olmali (double-submit).
    cevap.set_cookie(kimlik.CSRF_COOKIE, csrf, max_age=kimlik.OTURUM_OMRU_SN,
                     path="/", httponly=False, samesite="lax",
                     secure=COOKIE_SECURE)
    return cevap


@app.post("/api/cikis")
def cikis():
    cevap = JSONResponse({"ok": True})
    cevap.delete_cookie(kimlik.OTURUM_COOKIE, path="/")
    cevap.delete_cookie(kimlik.CSRF_COOKIE, path="/")
    return cevap


@app.get("/api/oturum")
def oturum_durumu(istek: Request):
    """Arayuz "girisli miyim" diye buna bakar. ⚠ TENANT DISINDA bilgi vermez."""
    d = teslim.oturum_kapisi(_oturum_jetonu(istek))
    return {"girisli": d["izin"], "tenant_id": d["tenant_id"],
            "neden": d["neden"], "zorunlu": ZORUNLU_OTURUM,
            "kdf": kimlik.kdf_adi(), "kdf_hazir": kimlik.kdf_hazir()}


@app.get("/api/kutuphane")
def kutuphane_listesi(istek: Request):
    """Bu tenant'in SON 3 kabul edilmis videosu (R-1c-b), imzali URL ile.

    ⚠ Signed URL SAKLANMAZ — talep aninda ve TENANT'A BAGLI uretilir.
    """
    tid = _tenant(istek)
    if not tid:
        raise HTTPException(401, "giris gerekli")
    return teslim.listele(_kutuphane_oku(), tid, ttl_sn=IMZA_TTL_SN)


@app.get("/giris", response_class=HTMLResponse)
def giris_sayfasi():
    return _GIRIS_HTML


# ⚠ Zorunlu oturum acikken tarayici kullanicisi kilitli kalmasin diye asgari
# bir giris formu. Tek dosya, dis bagimlilik YOK.
_GIRIS_HTML = """<!doctype html><html lang="tr"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>BEDOSAHO AI — Giris</title>
<style>body{background:#0f1115;color:#e8eaed;font:15px system-ui,sans-serif;
display:flex;min-height:100vh;align-items:center;justify-content:center;margin:0}
form{background:#171a21;padding:28px;border-radius:12px;width:300px}
h1{font-size:17px;margin:0 0 18px}input{width:100%;box-sizing:border-box;
padding:10px;margin:6px 0 12px;border-radius:7px;border:1px solid #2c313c;
background:#0f1115;color:#e8eaed}button{width:100%;padding:10px;border:0;
border-radius:7px;background:#3b82f6;color:#fff;font-weight:600;cursor:pointer}
p{color:#f87171;min-height:18px;font-size:13px;margin:10px 0 0}</style>
<form id="f"><h1>BEDOSAHO AI — giris</h1>
<label>Kullanici</label><input name="kullanici" autocomplete="username" required>
<label>Parola</label><input name="parola" type="password"
 autocomplete="current-password" required>
<button>Giris</button><p id="h"></p></form>
<script>document.getElementById('f').onsubmit=async e=>{e.preventDefault();
const r=await fetch('/api/giris',{method:'POST',body:new FormData(e.target)});
if(r.ok){location.href='/';}else{const d=await r.json().catch(()=>({}));
document.getElementById('h').textContent=d.detail||('hata '+r.status);}};
</script></html>"""


@app.get("/", response_class=HTMLResponse)
def anasayfa(istek: Request):
    # ⚠ Zorunlu oturum acikken girisi olmayan kullaniciya uygulama DEGIL
    # giris formu gosterilir (uygulama zaten her ucta 401 alirdi).
    if ZORUNLU_OTURUM and not teslim.oturum_kapisi(
            _oturum_jetonu(istek))["izin"]:
        return _GIRIS_HTML
    with open(os.path.join(STATIC, "index.html"), encoding="utf-8") as f:
        return f.read()


@app.get("/api/saglik/derin")
def saglik_derin_uc():
    """DERIN SAGLIK — bagimliliklari GERCEKTEN dener (bkz. saglik_derin.py).

    ⚠ Eski `/api/saglik` yalnizca anahtar booleanlari donduruyor ve icinde
    `durum` alani BULUNMUYORDU; arayuz alan yoksa 'ok' varsayip "Sistem hazir"
    yaziyordu. Bu uc ffmpeg/ffprobe'u calistirir, dizinlere gercekten yazar,
    render motorunu ve isci thread'lerini kontrol eder.
    Genel durum: hazir | kisitli | kullanilamiyor. Anahtar DEGERI donmez.
    """
    return saglik_derin.derin(
        pipeline, isci_sayisi=_ISCI_SAYISI, kuyruk_boyu=is_kuyrugu.qsize(),
        durum_dizini=IS_DURUM_DIR, gecici_dizin=GECICI)


@app.get("/api/saglik")
def saglik():
    """Hangi servislerin anahtari kurulu (deger DONMEZ, sadece var/yok).

    ⚠ FAZ H: bu uc artik `durum` ve `uretim_mumkun` alanlarini da donduruyor.
    Onceden bu alanlar YOKTU ve arayuz eksik alani 'ok' sayip kritik bilesen
    coktuğunde bile "Sistem hazir" gosteriyordu. Ayrintili olcum icin
    `/api/saglik/derin`.
    """
    import kaynak
    _d = saglik_derin.derin(
        pipeline, isci_sayisi=_ISCI_SAYISI, kuyruk_boyu=is_kuyrugu.qsize(),
        durum_dizini=IS_DURUM_DIR, gecici_dizin=GECICI)
    return {
        "durum": _d["durum"],
        "uretim_mumkun": _d["uretim_mumkun"],
        "ozet": _d["ozet"],
        "eksik_kritik": _d["eksik_kritik"],
        "eksik_opsiyonel": _d["eksik_opsiyonel"],
        "openai": bool(os.environ.get("OPENAI_KEY")),
        "magnific": bool(os.environ.get("MAGNIFIC_KEY")),
        # 11 Agu 2026: bunlar env'e BAKIYORDU ama kaynak.py anahtari env YA DA
        # veri/*.txt dosyasindan okuyor. Dosyaya yazilan Pexels anahtari calisirken
        # gosterge "false" diyordu — yanlis teshise yol aciyor. kaynak'in cozdugu
        # degeri okuyoruz.
        "pexels": bool(kaynak.PEXELS_KEY),
        "pixabay": bool(kaynak.PIXABAY_KEY),
        "coverr": bool(kaynak.COVERR_KEY),
        "gemini": bool(os.environ.get("GEMINI_KEY")),
        # main (12 Agu): Grok/xAI unlu modu gorsel+video motoru
        "grok": bool(pipeline.XAI_KEY),
        "freepik_anahtar_sayisi": len(kaynak.FREEPIK_KEYS),
        # ⚠ FAZ R-1d-a: teslim zincirinin ON KOSULLARI GORUNUR. Kapali/eksik
        # bir koruma sessizce gizlenmez.
        "oturum_zorunlu": ZORUNLU_OTURUM,
        "oturum_anahtari": teslim.hazir(),
        "imza_anahtari": imzali_url.hazir(),
        "kdf": kimlik.kdf_adi(),
        "kdf_hazir": kimlik.kdf_hazir(),
        "hesap_sayisi": len(_kullanicilar()),
        "kutuphane_tavani": kutuphane.TAVAN,
        # ⚠ Cerez `Secure` bayragi KAPALIYSA bunu GIZLEME — denetlenebilir
        # olsun. false gorunuyorsa kurulum HTTPS'e tasinmali.
        "cookie_secure": COOKIE_SECURE,
    }


@app.get("/api/freepik-kota")
def freepik_kota():
    """Bugun her Freepik anahtarinda kac indirme kaldi.
    Freepik API'sinde stok indirme Premium'da gunde 100 ile sinirli; birden fazla anahtar
    varsa motor kotasi dolan anahtardan sonrakine geciyor. Bu uc o durumu gosterir.
    Anahtarin KENDISI donmez — sadece kisa bir kimlik etiketi."""
    import kaynak
    durum = kaynak.freepik_kota_durum()
    return {
        "tavan": kaynak.FP_GUNLUK_TAVAN,
        "anahtarlar": [{"etiket": e, "kullanilan": k, "kalan": max(0, t - k)}
                       for e, k, t in durum],
        "toplam_kalan": sum(max(0, t - k) for _, k, t in durum),
    }


@app.get("/api/edit-stilleri")
def edit_listesi():
    return [{"id": k, "ad": v["ad"], "ozet": v["ozet"],
             "sahne_sn": v["sahne_sn"], "footage_pct": v["footage_pct"]}
            for k, v in pipeline.EDIT_STILLERI.items()]


@app.get("/api/animasyon-stilleri")
def anim_listesi():
    """Animasyon alt-stilleri (anlati-deneme / egitici-explainer)."""
    ond = os.path.join(STATIC, "onizleme")
    return [{"id": k, "ad": v["ad"], "ozet": v["ozet"], "sahne_sn": v["sahne_sn"],
             "onizleme": (f"onizleme/{k}.jpg"
                          if os.path.exists(os.path.join(ond, f"{k}.jpg")) else "")}
            for k, v in pipeline.ANIMASYON_STILLERI.items()]


# Altyazi sablonlari — fontlar.ts'teki SABLONLAR ile AYNI olmali (tek dogruluk kaynagi burasi;
# Video.tsx sablon adini da tam ayar nesnesini de kabul eder).
ALTYAZI_SABLONLARI = [
    {"id": "beyaz-kontur", "ad": "Beyaz Kontur", "font": "Montserrat",
     "ozet": "Faceless kanalların en yaygını — beyaz + kalın siyah kenar",
     "ayar": {"font": "montserrat", "boyut": 52, "agirlik": 800, "renk": "#ffffff",
              "konturRenk": "#000000", "konturKalinlik": 5, "arka": "yok", "konum": "alt",
              "buyukHarf": False, "golge": True, "harfAralik": 0}},
    {"id": "youtube-sari", "ad": "YouTube Sarı", "font": "Anton",
     "ozet": "MrBeast tarzı — kalın sarı, ağır siyah kontur, BÜYÜK HARF",
     "ayar": {"font": "anton", "boyut": 68, "agirlik": 400, "renk": "#ffe000",
              "konturRenk": "#000000", "konturKalinlik": 7, "arka": "yok", "konum": "alt",
              "buyukHarf": True, "golge": True, "harfAralik": 1}},
    {"id": "hormozi", "ad": "Hormozi", "font": "Poppins",
     "ozet": "Kısa-video tarzı — çok kalın, büyük harf, orta konum",
     "ayar": {"font": "poppins", "boyut": 64, "agirlik": 900, "renk": "#ffffff",
              "konturRenk": "#000000", "konturKalinlik": 8, "arka": "yok", "konum": "orta",
              "buyukHarf": True, "golge": True, "harfAralik": 0}},
    {"id": "klasik-kutu", "ad": "Klasik Kutu", "font": "Montserrat",
     "ozet": "Belgesel — koyu yarı saydam kutu, her zeminde okunur",
     "ayar": {"font": "montserrat", "boyut": 46, "agirlik": 700, "renk": "#ffffff",
              "konturRenk": "#000000", "konturKalinlik": 0, "arka": "rgba(0,0,0,0.72)",
              "konum": "alt", "buyukHarf": False, "golge": True, "harfAralik": 0}},
    {"id": "sari-kutu", "ad": "Sarı Kutu", "font": "Poppins",
     "ozet": "Vurgulu explainer — sarı dolgu, koyu yazı",
     "ayar": {"font": "poppins", "boyut": 50, "agirlik": 700, "renk": "#0a0a0a",
              "konturRenk": "#000000", "konturKalinlik": 0, "arka": "rgba(255,212,0,0.95)",
              "konum": "alt", "buyukHarf": True, "golge": False, "harfAralik": 0.5}},
    {"id": "sinematik", "ad": "Sinematik", "font": "Oswald",
     "ozet": "İnce, geniş harf aralığı — belgesel/film hissi",
     "ayar": {"font": "oswald", "boyut": 44, "agirlik": 500, "renk": "#f2f2f2",
              "konturRenk": "#000000", "konturKalinlik": 2, "arka": "yok", "konum": "alt",
              "buyukHarf": False, "golge": True, "harfAralik": 1.5}},
    {"id": "podcast", "ad": "Podcast", "font": "Bebas Neue",
     "ozet": "Uzun, dar, iri harfler — sohbet/podcast klipleri",
     "ayar": {"font": "bebas", "boyut": 72, "agirlik": 400, "renk": "#ffffff",
              "konturRenk": "#000000", "konturKalinlik": 5, "arka": "yok", "konum": "alt",
              "buyukHarf": True, "golge": True, "harfAralik": 2}},
    {"id": "temiz", "ad": "Temiz Beyaz", "font": "Montserrat",
     "ozet": "Kontursuz, sadece yumuşak gölge — minimal/modern",
     "ayar": {"font": "montserrat", "boyut": 50, "agirlik": 700, "renk": "#ffffff",
              "konturRenk": "#000000", "konturKalinlik": 0, "arka": "yok", "konum": "alt",
              "buyukHarf": False, "golge": True, "harfAralik": 0}},
]


@app.get("/api/altyazi-sablonlari")
def altyazi_sablonlari():
    return ALTYAZI_SABLONLARI


@app.get("/fonts/{dosya}")
def font_ver(dosya: str):
    """Gomulu altyazi fontlarini arayuze de sun — canli onizleme gercek fontla cizilsin."""
    ad = os.path.basename(dosya)
    if not ad.endswith(".ttf"):
        raise HTTPException(404, "yok")
    yol = os.path.join(pipeline.STUDYO, "public", "fonts", ad)
    if not os.path.exists(yol):
        raise HTTPException(404, "yok")
    return FileResponse(yol, media_type="font/ttf",
                        headers={"Cache-Control": "public, max-age=604800"})


"""Arayuz varliklari — DAR ISTISNA (Faz F, kullanicinin acik izniyle).

⚠ NEDEN GEREKLI: sunucuda genel bir statik mount YOK; eski arayuz bu yuzden
tek 1698 satirlik `index.html` icinde inline stil/script tasiyordu. Arayuz
ayri dosyalara bolununce (`app.css`, `app.js`, `js/*.js`) bunlarin
sunulmasi gerekti.

⚠ NEDEN ALLOWLIST: `StaticFiles` ile tum `static/` dizinini acmak, is
ciktilarini ve yuklenen gorselleri de acardi. Burada YALNIZCA arayuz
dosyalari sunulur:
    app.css · app.js · js/<ad>.js
Bunun disindaki her sey 404. Ayrica `realpath` ile cozulen yol STATIC
onekiyle dogrulanir; `../` ile disari cikma denemesi reddedilir.

API, /api/generate ve pipeline davranisi DEGISMEDI.
"""
UI_TAM_IZIN = frozenset({"app.css", "app.js"})
UI_DIZIN_IZIN = frozenset({"js"})
UI_MIME = {".css": "text/css; charset=utf-8",
           ".js": "text/javascript; charset=utf-8"}


@app.get("/ui/{dosya:path}")
def ui_varlik(dosya: str):
    parcalar = [p for p in str(dosya).split("/") if p not in ("", ".")]
    # Traversal ve gizli dosya denemeleri: daha yol kurulmadan reddedilir
    if not parcalar or any(p == ".." or p.startswith(".") for p in parcalar):
        raise HTTPException(404, "yok")

    if len(parcalar) == 1:
        if parcalar[0] not in UI_TAM_IZIN:
            raise HTTPException(404, "yok")
    elif len(parcalar) == 2:
        if parcalar[0] not in UI_DIZIN_IZIN or not parcalar[1].endswith(".js"):
            raise HTTPException(404, "yok")
    else:
        raise HTTPException(404, "yok")

    uzanti = os.path.splitext(parcalar[-1])[1].lower()
    if uzanti not in UI_MIME:
        raise HTTPException(404, "yok")

    # ⚠ Ikinci savunma katmani: sembolik bag ya da beklenmeyen bir birlestirme
    # STATIC disina cikarsa dosya SUNULMAZ.
    kok = os.path.realpath(STATIC)
    yol = os.path.realpath(os.path.join(STATIC, *parcalar))
    if not (yol == kok or yol.startswith(kok + os.sep)):
        raise HTTPException(404, "yok")
    if not os.path.isfile(yol):
        raise HTTPException(404, "yok")

    # ⚠ ONBELLEK DERSI (Faz F tarayici testi): ilk surumde
    # `max-age=3600` vardi. Dosya adlarinda surum/hash YOK oldugu icin
    # deploy sonrasi tarayici 1 saat boyunca ESKI app.js/gorunumler.js'i
    # sunuyordu — testte tam bunu yasadim, ekranda duzeltilmis metinler
    # yerine eskisi cikti. Eski tek-dosya arayuzde bu sorun yoktu (index.html
    # her istekte tazeydi).
    # `no-cache` = her kullanimda dogrula; FileResponse ETag/Last-Modified
    # verdigi icin degismemis dosya 304 doner (bant genisligi maliyeti yok).
    return FileResponse(yol, media_type=UI_MIME[uzanti],
                        headers={"Cache-Control": "no-cache"})


@app.get("/api/paletler")
def paletler():
    """Kanal renk paletleri — gorsel promptuna KESIN HEX olarak girer (kelimeyle tarif degil)."""
    return [{"id": k, **v} for k, v in pipeline.PALETLER.items()]


@app.get("/onizleme/{dosya}")
def onizleme(dosya: str):
    """Stil onizleme gorselleri — arayuzde stil kartinin yaninda gorunur."""
    ad = os.path.basename(dosya)
    if not ad.endswith((".jpg", ".png")):
        raise HTTPException(404, "yok")
    yol = os.path.join(STATIC, "onizleme", ad)
    if not os.path.exists(yol):
        raise HTTPException(404, "yok")
    return FileResponse(yol, headers={"Cache-Control": "public, max-age=86400"})


@app.get("/api/sesler")
def sesler():
    """Anlatici sesleri. motor=openai olanlar sesin YASINI tarif edebiliyor (edge-tts edemez)."""
    return [{"id": k, "ad": v["ad"], "ozet": v.get("ozet", ""), "motor": v["motor"],
             "ucret": v.get("ucret", ""), "dil": v.get("dil", ""),
             "grup": v.get("grup", "ucretsiz"),
             "ornek": (f"ses-ornek/{k}.mp3"
                       if os.path.exists(os.path.join(STATIC, "ses-ornek", f"{k}.mp3")) else "")}
            for k, v in pipeline.SESLER.items()]


_SES_KUTUPHANE_ONBELLEK = {}   # saglayici -> (zaman, liste); Ai33'e her seferinde gitmeyelim


def _ai33_key():
    k = os.environ.get("AI33_KEY", "").strip()
    if not k:
        try:
            with open(os.path.join(pipeline.KOK_YOL, "AI33_KEY")) as f:
                k = f.read().strip()
        except Exception:
            k = ""
    return k


@app.get("/api/ses-kutuphane")
def ses_kutuphane(saglayici: str = "elevenlabs"):
    """Ai33 ses KUTUPHANESI — saglayicinin TUM katalogu (isim, tarif, onizleme).
    Kullanici istedigi sesi secer; secim 'ozel:<voice_id>' olarak generate'e gider."""
    if saglayici not in ("elevenlabs", "minimax", "fishaudio", "kokoro", "vbee", "clone"):
        raise HTTPException(400, "gecersiz saglayici")
    zaman, liste = _SES_KUTUPHANE_ONBELLEK.get(saglayici, (0, None))
    if liste is not None and time.time() - zaman < 1800:
        return liste
    import json
    # ── DISK ONBELLEGI ONCE ──
    # Sunucu IP'si Ai33'te kisitli (canli cekim 1-2 kayit donduruyor); tam katalog
    # (2071 ses) yerel makineden cekilip buraya kondu. 7 gunden tazeyse diski kullan.
    disk_yol = os.path.join(VERI, "ses-kutuphane", f"{saglayici}.json")
    ham = None
    try:
        if os.path.exists(disk_yol) and time.time() - os.path.getmtime(disk_yol) < 7 * 86400:
            with open(disk_yol, encoding="utf-8") as f:
                ham = json.load(f)
    except Exception:
        ham = None
    if ham:
        veri = ham
    else:
        veri = _ai33_canli_katalog(saglayici, disk_yol)
    return _katalog_donustur(saglayici, veri)


def _ai33_canli_katalog(saglayici, disk_yol):
    """Canli cekim (disk yoksa/bayatsa). Basarili genis cekim diske de yazilir."""
    import json
    key = _ai33_key()
    if not key:
        raise HTTPException(503, "AI33 anahtari kurulu degil")
    import requests
    # SAYFALAMA SART: varsayilan 30 kayit donuyor — elevenlabs'te 605, minimax'ta 481,
    # vbee'de 462 ses var. 100'luk sayfalarla tumu cekilir (guvenlik tavani 10 sayfa).
    veri = []
    gorulen = set()   # Ai33 sayfalamasi kararsiz: sayfalar arasi MUKERRER kayit gelebiliyor
    try:
        for sayfa in range(1, 11):
            parca = []
            for dene in range(3):   # Ai33 art arda isteklerde IP'yi kisip 1-2 kayit dondurebiliyor
                r = requests.get(f"https://api.ai33.pro/v3/voices?provider={saglayici}"
                                 f"&limit=100&page={sayfa}",
                                 headers={"xi-api-key": key}, timeout=30)
                parca = r.json().get("data", [])
                if len(parca) >= 30 or (sayfa > 1 and parca is not None):
                    break            # saglikli sayfa (son sayfa kucuk olabilir, o normal)
                time.sleep(2 + dene * 2)
            yeni = 0
            for v in parca:
                vid = v.get("voice_id")
                if vid and vid not in gorulen:
                    gorulen.add(vid)
                    veri.append(v)
                    yeni += 1
            if len(parca) < 100 or yeni == 0:   # kisa sayfa VEYA tamamen tekrar -> bitti
                break
            time.sleep(0.7)          # sayfalar arasi nefes: hiz sinirini tetikleme
    except Exception:
        if not veri:
            raise HTTPException(502, "Ses kütüphanesi alınamadı")
    # Genis cekim basarili olduysa diske yaz (7 gunluk taze onbellek)
    if len(veri) >= 30:
        try:
            os.makedirs(os.path.dirname(disk_yol), exist_ok=True)
            with open(disk_yol, "w", encoding="utf-8") as f:
                json.dump(veri, f, ensure_ascii=False)
        except Exception:
            pass
    return veri


def _katalog_donustur(saglayici, veri):
    # Saglayicilar dil degerini karisik gonderiyor: kimi ISO kod ("en"), kimi tam ad
    # ("English", "Cantonese"). KIRPMADAN ISO koda normallestir (eski [:5] kirpmasi
    # "engli"/"canto" gibi bozuk degerler uretiyordu).
    DIL_KOD = {"english": "en", "chinese": "zh", "chinese (mandarin)": "zh", "mandarin": "zh",
               "cantonese": "yue", "japanese": "ja", "korean": "ko", "french": "fr",
               "german": "de", "spanish": "es", "portuguese": "pt", "russian": "ru",
               "arabic": "ar", "turkish": "tr", "italian": "it", "dutch": "nl",
               "polish": "pl", "hindi": "hi", "indonesian": "id", "vietnamese": "vi",
               "thai": "th", "ukrainian": "uk", "swedish": "sv", "czech": "cs",
               "danish": "da", "greek": "el", "filipino": "fil", "hungarian": "hu",
               "malay": "ms", "romanian": "ro", "norwegian": "no", "finnish": "fi",
               "bulgarian": "bg", "croatian": "hr", "slovak": "sk", "hebrew": "he",
               "persian": "fa", "tamil": "ta", "urdu": "ur"}

    def _dil_kod(x):
        x = str(x or "").strip().lower()
        return DIL_KOD.get(x, x)

    def _diller(v):
        """Sesin konustugu TUM diller (languages listesi dict/str karisik gelebiliyor)."""
        out = []
        for d in (v.get("languages") or []):
            kod = _dil_kod(d.get("language") if isinstance(d, dict) else d)
            if kod and kod not in out:
                out.append(kod)
        ana = _dil_kod(v.get("language", ""))
        if ana and ana not in out:
            out.insert(0, ana)
        return out

    def _yas(v):   # "Middle Age" / "middle-aged" / "middle_aged" -> tek bicim; cop degerler elenir
        y = str(v.get("age", "")).strip().lower().replace("-", "_").replace(" ", "_")
        return "" if y in ("none", "null", "unknown", "n/a") else y

    liste = [{"voice_id": v.get("voice_id"), "ad": v.get("name") or v.get("voice_id"),
              "ozet": (v.get("description") or "")[:220],
              "cinsiyet": str(v.get("gender", "")).strip().lower(), "yas": _yas(v),
              "dil": _dil_kod(v.get("language", "")), "diller": _diller(v),
              "aksan": v.get("accent", ""), "kategori": v.get("category", ""),
              "onizleme": v.get("preview_url", "")}
             for v in veri if v.get("voice_id")]
    _SES_KUTUPHANE_ONBELLEK[saglayici] = (time.time(), liste)
    return liste


@app.get("/ses-ornek/{dosya}")
def ses_ornek(dosya: str):
    ad = os.path.basename(dosya)
    if not ad.endswith(".mp3"):
        raise HTTPException(404, "yok")
    yol = os.path.join(STATIC, "ses-ornek", ad)
    if not os.path.exists(yol):
        raise HTTPException(404, "yok")
    return FileResponse(yol, media_type="audio/mpeg",
                        headers={"Cache-Control": "public, max-age=86400"})


# ═══════════ ANIMASYON STUDYOSU (sohbet paneli) ═══════════
@app.post("/api/anim/analiz")
async def anim_analiz(oturum: str = Form(...), kare: List[UploadFile] = File(None)):
    """Referans kareleri coz: karakter + stil + palet + ISIK (olculur, tahmin degil)."""
    try:
        d = anim_studyo.oturum_dizini(oturum)
    except ValueError:
        raise HTTPException(400, "geçersiz oturum")
    yollar = []
    try:
        for i, dosya in enumerate((kare or [])[:6]):
            if dosya is None:
                continue
            veri = await dosya.read()
            if not veri:
                continue
            if len(veri) > MAKS_UPLOAD:
                raise HTTPException(413, "Görsel çok büyük (maks 20 MB)")
            y = os.path.join(d, f"ref_{i+1}.png")
            await asyncio.to_thread(_kucult, veri, y)
            yollar.append(y)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(400, "Görsel okunamadı (geçerli bir resim yükleyin)")
    if not yollar:
        raise HTTPException(400, "En az 1 referans kare gerekli")
    try:
        return await asyncio.to_thread(anim_studyo.analiz_yap, oturum, yollar)
    except pipeline.BakiyeHatasi as e:
        raise HTTPException(402, str(e))


@app.post("/api/anim/sorular")
async def anim_sorular(oturum: str = Form(...), metin: str = Form("")):
    """Motor SADECE cikaramadigi seyi sorar; her sey belliyse bos liste doner."""
    try:
        anim_studyo.oturum_dizini(oturum)
    except ValueError:
        raise HTTPException(400, "geçersiz oturum")
    return await asyncio.to_thread(anim_studyo.sorular_uret, oturum, metin)


@app.get("/api/isik-duzeyleri")
def isik_duzeyleri():
    """Isik duzeyi — stilin/arka planin karanlik egilimini EZER (olculen hedef: 162/255)."""
    return [{"id": k, **v} for k, v in pipeline.ISIK_DUZEYLERI.items()]


@app.get("/api/arkaplanlar")
def arkaplanlar():
    """Mekan/arka plan secenekleri — cerceve blogunun sonuna eklenir, yogunlugu ezebilir."""
    return [{"id": k, **v} for k, v in pipeline.ARKA_PLANLAR.items()]


@app.get("/api/profiller")
def profil_listesi():
    """Kanal profilleri — videolar ARASI stil/karakter tutarliligi icin."""
    return pipeline.profil_listele()


@app.post("/api/profil")
async def profil_olustur(pid: str = Form(...), ad: str = Form(""),
                         tur: str = Form("animasyon"), edit: str = Form(""),
                         altyazi_sablon: str = Form(""),
                         palet: str = Form(""), palet_ozel: str = Form(""),
                         arkaplan: str = Form(""), ses: str = Form(""),
                         isik: str = Form(""),
                      sahne_ref: List[UploadFile] = File(None),
                         karakter: UploadFile = File(None),
                         stil: UploadFile = File(None)):
    """Kanal profili olustur/guncelle. Karakter+stil gorselleri KALICI saklanir."""
    try:
        d = pipeline.profil_yolu(pid)
    except ValueError:
        raise HTTPException(400, "Geçersiz profil kimliği (harf/rakam/-/_ , maks 48)")
    os.makedirs(d, exist_ok=True)
    mod = tur if tur in ("animasyon", "documentary") else "animasyon"
    if mod == "animasyon":
        eid = edit if edit in pipeline.ANIMASYON_STILLERI else pipeline.VARSAYILAN_ANIM
    else:
        eid = edit if edit in pipeline.EDIT_STILLERI else pipeline.VARSAYILAN_EDIT
    try:
        for dosya, hedef_ad in ((karakter, "karakter.png"), (stil, "stil.png")):
            if dosya is not None:
                veri = await dosya.read()
                if veri:
                    if len(veri) > MAKS_UPLOAD:
                        raise HTTPException(413, "Görsel çok büyük (maks 20 MB)")
                    await asyncio.to_thread(_kucult, veri, os.path.join(d, hedef_ad))
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(400, "Görsel okunamadı (geçerli bir resim dosyası yükleyin)")
    pal = palet.strip() if (palet.strip() in pipeline.PALETLER or palet.strip() == "ozel") else ""
    pipeline.profil_yaz(pid, {"ad": ad.strip() or pid, "tur": mod, "edit": eid,
                              "altyazi_sablon": altyazi_sablon.strip() or None,
                              "palet": pal or None,
                              "palet_ozel": palet_ozel.strip()[:80] or None,
                              "arkaplan": (arkaplan.strip()
                                           if arkaplan.strip() in pipeline.ARKA_PLANLAR else "") or None,
                              "ses": (_ses_secimi(ses)) or None,
                              "isik": (isik.strip()
                                       if isik.strip() in pipeline.ISIK_DUZEYLERI else "") or None})
    return pipeline.profil_oku(pid) and {"ok": True, "id": pid}


@app.delete("/api/profil/{pid}")
def profil_sil(pid: str):
    try:
        d = pipeline.profil_yolu(pid)
    except ValueError:
        raise HTTPException(400, "gecersiz profil")
    if not os.path.isdir(d):
        raise HTTPException(404, "profil yok")
    shutil.rmtree(d, ignore_errors=True)
    return {"ok": True}


@app.post("/api/profil/{pid}/capa-sifirla")
def profil_capa_sifirla(pid: str):
    """Kanalin gorsel kilidini kaldir — bir sonraki video yeni gorunumu belirler."""
    try:
        y = os.path.join(pipeline.profil_yolu(pid), "capa.png")
    except ValueError:
        raise HTTPException(400, "gecersiz profil")
    if os.path.exists(y):
        os.remove(y)
    return {"ok": True, "kilitli": False}


@app.post("/api/analiz")
async def girdi_analiz_uc(story: str = Form(...), tur: str = Form(""),
                          sure_dk: str = Form(""), ses: str = Form(""),
                          edit: str = Form("")):
    """OTOMATIK GIRDI ANALIZI — uretimden ONCE, UCRETSIZ, LLM cagrisi YOK.

    ⚠ Wizard Adim 4'te "Guvenilir kaynak sayisi / Sahne sayisi / ... ->
    Uretim sirasinda hesaplanacak" YAZIYORDU ama o alanlarin ON-KONTROL ucu
    YOKTU. Bu uc olculebilir olanlari (girdi turu, dil, icerik turu, donem,
    varliklar, risk, onerilen sure) uretimden once verir.

    Kullanicinin ACIK secimi korunur; yalnizca BOS alanlar doldurulur ve
    hangisinin otomatik secildigi `otomatik_secimler` icinde RAPORLANIR.
    """
    if len((story or "").strip()) < 20:
        raise HTTPException(400, "Metin cok kisa (en az 20 karakter)")
    secim = {k: v for k, v in (("tur", tur), ("sure_dk", sure_dk),
                               ("ses", ses), ("edit", edit)) if v.strip()}
    return await asyncio.to_thread(girdi_analizi.analiz, story,
                                   kullanici_secimi=secim)


@app.post("/api/generate")
async def uret_baslat(istek: Request,
                      session: str = Form(...), story: str = Form(...),
                      tur: str = Form("documentary"),
                      edit: str = Form(pipeline.VARSAYILAN_EDIT),
                      sure_dk: str = Form("2"),
                      gecis: str = Form("1"),
                      zoom: str = Form("1"),
                      profil: str = Form(""),
                      altyazi: str = Form(""),
                      altyazi_sablon: str = Form(""),
                      palet: str = Form(""),
                      palet_ozel: str = Form(""),
                      acilis: str = Form(""),
                      sora: str = Form(""),
                      unlu: str = Form(""),
                      arkaplan: str = Form(""),
                      ses: str = Form(""),
                      isik: str = Form(""),
                      gorsel_model: str = Form(""),
                      karakter: UploadFile = File(None),
                      stil: UploadFile = File(None),
                      sahne_ref: List[UploadFile] = File(None)):
    """Karakter/stil gorselleri her video icin DOGRUDAN yuklenir (kalici kayit yok).
    Magnific ve footage plana gore OTOMATIK. tur: animasyon|documentary|hikaye."""
    # ⚠ FAZ R-1d-a: ZINCIRIN 1. HALKASI. `session` yalnizca bir arayuz
    # etiketidir, YETKI DEGILDIR — yetki oturum cerezinden gelir.
    tenant_id = _tenant(istek)
    session = gecerli_session(session)
    if len(story.strip()) < 20:
        raise HTTPException(400, "Hikaye metni cok kisa")
    mod = tur if tur in ("animasyon", "documentary", "hikaye") else "documentary"
    # edit: turun kendi stil sozlugunden secilir
    if mod == "animasyon":
        edit_id = edit if edit in pipeline.ANIMASYON_STILLERI else pipeline.VARSAYILAN_ANIM
    elif mod == "hikaye":
        edit_id = edit if edit in pipeline.HIKAYE_STILLERI else pipeline.VARSAYILAN_HIKAYE
    else:
        edit_id = edit if edit in pipeline.EDIT_STILLERI else pipeline.VARSAYILAN_EDIT
    try:
        # Sure tavani ture gore: hikaye kanali 60 dk, diger turler 14 dk (pipeline ile ayni)
        sd = max(0.3, min(60.0 if mod == "hikaye" else 14.0, float(sure_dk)))
    except Exception:
        sd = 2.0
    gecis_acik = _bayrak(gecis)
    zoom_acik = _bayrak(zoom)

    is_id = f"job_{int(time.time()*1000)}_{session[:6]}_{os.urandom(3).hex()}"
    idir = os.path.join(GECICI, is_id)
    os.makedirs(idir, exist_ok=True)
    sref = []
    try:
        kar = ""
        if karakter is not None:
            data = await karakter.read()
            if data:
                if len(data) > MAKS_UPLOAD:
                    raise HTTPException(413, "Karakter görseli çok büyük (maks 20 MB)")
                kar = os.path.join(idir, "character.png")
                await asyncio.to_thread(_kucult, data, kar)   # bloklamasin
        stil_yol = ""
        if stil is not None:
            data = await stil.read()
            if data:
                if len(data) > MAKS_UPLOAD:
                    raise HTTPException(413, "Stil görseli çok büyük (maks 20 MB)")
                stil_yol = os.path.join(idir, "style.png")
                await asyncio.to_thread(_kucult, data, stil_yol)
        # SAHNE REFERANSLARI: 1-4 kare. Karakter + cizim stili + palet + ISIK hepsi
        # bunlardan cikarilir (ayri ayri karakter/stil yuklemeye gerek kalmaz).
        for i, dosya in enumerate((sahne_ref or [])[:4]):
            if dosya is None:
                continue
            veri = await dosya.read()
            if not veri:
                continue
            if len(veri) > MAKS_UPLOAD:
                raise HTTPException(413, "Referans görseli çok büyük (maks 20 MB)")
            y = os.path.join(idir, f"ref_{i+1}.png")
            await asyncio.to_thread(_kucult, veri, y)
            sref.append(y)
    except HTTPException:
        shutil.rmtree(idir, ignore_errors=True)
        raise
    except Exception:
        shutil.rmtree(idir, ignore_errors=True)
        raise HTTPException(400, "Görsel okunamadı (geçerli bir resim dosyası yükleyin)")

    isler[is_id] = {"durum": "kuyrukta", "ilerleme": 0, "mesaj": "Sirada...",
                    "video": None, "kapak": None, "hata": None,
                    "olusturma_zamani": time.time()}
    # ⚠ FAZ R-1d-a — ZINCIRIN 2. ve 4. HALKASI, kuyruga girmeden ONCE:
    # is TENANT'a muhurlenir ve bu tenant'in SAGLAYICI KARARI (R-1b) yazilir.
    # Tenant'in onayli+kredili bir baglantisi yoksa (gercek OAuth/kredi YOK)
    # UCRETSIZ STOK'a duser ve `fallback_reason` GORUNUR kalir.
    _sag = teslim.saglayici_karari(_saglayici_kayitlari(), tenant_id)
    _dmg = teslim.is_damgala(isler[is_id], tenant_id=tenant_id,
                             metin=story, saglayici=_sag)
    if not _dmg["ok"] and ZORUNLU_OTURUM:
        # ⚠ Damgalanamayan is KUYRUGA GIRMEZ: sahipsiz is kimseye teslim
        # edilemez, uretmek bosa kredi olurdu.
        shutil.rmtree(idir, ignore_errors=True)
        del isler[is_id]
        raise HTTPException(401, f"is tenant'a baglanamadi: {_dmg['neden']}")
    _durum_kaydet(is_id)
    pal = palet.strip() if (palet.strip() in pipeline.PALETLER or palet.strip() == "ozel") else ""
    # Hikaye: hareketli acilis suresi (dk). "" = varsayilan (HIKAYE_ACILIS_SN); 0 = kapali.
    try:
        acilis_dk = max(0.0, min(60.0, float(acilis))) if acilis.strip() != "" else None
    except Exception:
        acilis_dk = None
    # ⚠ 3 Agu 2026 — REFERANSSIZ ANIMASYON REDDEDILIR.
    # Kullanici eski panelden referanssiz istek gonderdi, sistem fotogercekci "hikaye"
    # modunda 30 gorsel uretti ve para yandi. Artik animasyon istegi en az bir gorsel
    # referans ISTER — sessizce yanlis sey uretmektense NET HATA versin.
    if mod == "animasyon" and not sref and not kar and not stil_yol:
        shutil.rmtree(idir, ignore_errors=True)
        raise HTTPException(400,
            "Animasyon için en az 1 referans kare gerekli. Animasyon Stüdyosu'ndan "
            "yapmak istediğin tarzdan 2-6 kare yükle — karakter, çizim stili, palet ve "
            "ışık hepsi o karelerden çıkarılır.")

    is_kuyrugu.put((is_id, story.strip(), kar, stil_yol, mod, edit_id, sd, gecis_acik, zoom_acik,
                    profil.strip(), altyazi.strip(), altyazi_sablon.strip(),
                    pal, palet_ozel.strip()[:80],
                    arkaplan.strip() if arkaplan.strip() in pipeline.ARKA_PLANLAR else "",
                    _ses_secimi(ses),
                    isik.strip() if isik.strip() in pipeline.ISIK_DUZEYLERI else "",
                    acilis_dk, sref, _bayrak(sora), gorsel_model.strip(),
                    _bayrak(unlu)))
    # ⚠ FAZ H: cevap ARTIK tek tip sozlesmeden geciyor. Eskiden yalnizca
    # `job_id` donuyordu; wizard.js `cevap.job/is_id/id` okudugu icin is
    # kimligi HER ZAMAN bos kaliyordu. Simdi job_id + id + is_id birlikte var.
    cevap = is_sozlesme.normalize(is_id, isler[is_id],
                                  kuyruk_sira=_kuyruk_sirasi(is_id),
                                  kuyruk_toplam=is_kuyrugu.qsize(),
                                  imzalayici=_imzalayici(tenant_id))
    cevap.update({"kuyruk": is_kuyrugu.qsize(), "tur": mod, "edit": edit_id,
                  "profil": profil.strip(),
                  # ⚠ Saglayici karari BASTAN GORUNUR: kullanici videonun
                  # hangi kaynaktan cekilecegini uretim bitmeden bilir.
                  "saglayici": _sag["provider_used"],
                  "saglayici_fallback": _sag["fallback_reason"]})
    return cevap


@app.get("/api/isler")
def is_listesi(istek: Request, session: str):
    """Bu oturumun TUM isleri (Videolarim sekmesi) — sayfa yenilense/kapansa da is kaybolmaz.
    Kaynak: diskteki durum dosyalari; bellekte daha guncel hal varsa o kullanilir.
    Is id'si 'job_<ts>_<session[:6]>_<hex>' oldugu icin oturum eslesmesi id icinden yapilir."""
    import json
    tenant_id = _tenant(istek)
    session = gecerli_session(session)
    on6 = session[:6]
    imz = _imzalayici(tenant_id)
    cikti = []
    try:
        for ad in os.listdir(IS_DURUM_DIR):
            if not ad.endswith(".json") or f"_{on6}_" not in ad:
                continue
            yol = os.path.join(IS_DURUM_DIR, ad)
            try:
                d = isler.get(ad[:-5])
                if d is None:
                    with open(yol, encoding="utf-8") as f:
                        d = json.load(f)
                # ⚠ FAZ R-1d-a: `session` on eki TAHMIN EDILEBILIR bir
                # etikettir, yetki degildir. Zorunlu oturumda liste TENANT
                # SAHIPLIGINE gore suzulur; sahipsiz eski kayitlar GORUNMEZ.
                if tenant_id and not teslim.erisim_kapisi(d, tenant_id)["izin"]:
                    continue
                # ⚠ FAZ H: liste de TEK TIP sozlesmeden geciyor. Eskiden
                # `ilerleme` donuyordu ama arayuz `yuzde` okuyordu -> ilerleme
                # cubugu her zaman %0 gorunuyordu. normalize() ikisini de verir.
                cikti.append(is_sozlesme.normalize(
                    ad[:-5], d, zaman=os.path.getmtime(yol),
                    imzalayici=imz))
            except Exception:
                continue
    except Exception:
        pass
    cikti.sort(key=lambda x: -x["t"])
    return cikti[:30]


@app.get("/api/job/{is_id}")
def is_durum(istek: Request, is_id: str):
    """Tek isin CANLI durumu. Arayuz Projeler ekraninda bunu periyodik cagirir.
    ⚠ FAZ H: cevap `is_sozlesme.normalize()`ten geciyor — yeni (job_id/status/
    progress/stage/video_url/qa/attribution/fallbacks) ve eski (durum/ilerleme/
    mesaj/video) adlar BIRLIKTE donuyor."""
    tenant_id = _tenant(istek)
    imz = _imzalayici(tenant_id)
    d = isler.get(is_id)
    if not d:
        # bellekte yoksa (restart olmus olabilir) diskten dene
        try:
            import json
            yol = os.path.join(IS_DURUM_DIR, f"{gecerli_session(is_id)}.json")
            if os.path.exists(yol):
                with open(yol, encoding="utf-8") as f:
                    d = json.load(f)
                _erisim_dogrula(d, tenant_id)
                return is_sozlesme.normalize(is_id, d, imzalayici=imz)
        except HTTPException:
            raise
        except Exception:
            pass
        raise HTTPException(404, "is yok")
    _erisim_dogrula(d, tenant_id)
    sira = _kuyruk_sirasi(is_id) if d.get("durum") == "kuyrukta" else None
    return is_sozlesme.normalize(
        is_id, d, kuyruk_sira=sira,
        kuyruk_toplam=is_kuyrugu.qsize() if sira is not None else None,
        imzalayici=imz)


def _erisim_dogrula(kayit: dict, tenant_id: str) -> None:
    """⚠ FAZ R-1d-a: BASKA tenant'in isi 404 verir (403 DEGIL).

    403 "bu is var ama senin degil" bilgisini sizdirirdi; is kimlikleri
    tahmin edilebilir zaman damgasi tasidigi icin bu bir sayim yoluydu.
    """
    if not tenant_id:
        return
    if not teslim.erisim_kapisi(kayit, tenant_id)["izin"]:
        raise HTTPException(404, "is yok")


def _kuyruk_sirasi(is_id):
    """Kuyruktaki isin 1-tabanli sirasi; kuyrukta degilse None."""
    try:
        with is_kuyrugu.mutex:
            idler = [g[0] for g in list(is_kuyrugu.queue)]
        return idler.index(is_id) + 1
    except ValueError:
        return None


@app.get("/ciktilar/{dosya}")
def cikti(istek: Request, dosya: str, exp: str = "", sig: str = ""):
    """⚠ FAZ R-1a: cikti indirmesi IMZALI ve SURELI.
    ⚠ FAZ R-1d-a: imza ayrica TENANT'A BAGLI.

    Onceden dosya adini bilen HERKES indirebiliyordu (R-1a bunu kesti), ama
    imza dosya+sureye baglanmisti: SIZAN bir baglanti BASKA BIR HESAPTA da
    calisiyordu. Artik imza istegin OTURUMUNDAKI tenant ile dogrulanir —
    baglanti sizsa bile yabanci oturumda gecersizdir.

    Imza anahtari kurulamadiysa uc ACIK KALMAZ — 503 doner (sessizce
    korumasiz calismaktansa durustce reddeder).
    """
    ad = imzali_url.guvenli_ad(dosya)
    if not imzali_url.hazir():
        raise HTTPException(503, "imza anahtari kurulmadi")
    tenant_id = _tenant(istek)
    k = imzali_url.dogrula(ad, exp, sig, tenant=tenant_id)
    if not k["gecerli"]:
        raise HTTPException(403, f"baglanti gecersiz: {k['neden']}")
    yol = os.path.join(pipeline.CIKTI_DIR, ad)
    if not os.path.exists(yol):
        raise HTTPException(404, "yok")
    return FileResponse(yol)


def _bir_is(is_id, story, kar, stil_yol, mod, edit_id, sure_dk, gecis_acik, zoom_acik,
            profil_id="", altyazi="", altyazi_sablon="", palet="", palet_ozel="",
            arkaplan="", ses_secim="", isik="", acilis_dk=None, sahne_ref=None,
            sora_acik=False, gorsel_model_secim="", unlu_modu=False):
    d = isler.get(is_id)
    if not d:
        return
    d["durum"] = "uretiliyor"
    _durum_kaydet(is_id)

    def ilerle(msg, yuzde):
        d["mesaj"] = msg
        d["ilerleme"] = yuzde
        _durum_kaydet(is_id)   # diske de yaz: restart sonrasi gercek ilerleme gorunsun

    try:
        sonuc = asyncio.run(pipeline.uret(is_id, story, kar, stil_yol, mod, edit_id,
                                          sure_dk, gecis_acik, zoom_acik, ilerle,
                                          profil_id=profil_id, altyazi_sablon=altyazi_sablon,
                                          altyazi_ac=altyazi, palet=palet,
                                          palet_ozel=palet_ozel, arkaplan=arkaplan,
                                          ses_secim=ses_secim, isik=isik,
                                          acilis_dk=acilis_dk, sahne_ref=sahne_ref,
                                          sora_acik=sora_acik,
                                          gorsel_model_secim=gorsel_model_secim,
                                          unlu_modu=unlu_modu))
        d.update({"durum": "bitti", "ilerleme": 100, "mesaj": "Hazir!",
                  "video": "ciktilar/" + sonuc["video"],
                  "kapak": ("ciktilar/" + sonuc["kapak"]) if sonuc.get("kapak") else None,
                  "sure": sonuc.get("sure"), "sahne_sayisi": sonuc.get("sahne_sayisi"),
                  "edit": sonuc.get("edit"), "uyari": sonuc.get("uyari"),
                  "atiflar": sonuc.get("atiflar") or [],
                  # ── FAZ H: arastirma + QA + gorunur dususler ise yazilir ──
                  "arastirma": sonuc.get("arastirma") or {},
                  "kaynaklar": sonuc.get("kaynaklar") or [],
                  "qa": sonuc.get("qa") or {},
                  # ⚠ FAZ R-1d-e: PRE-QA kaniti (RENDER EDILEN zaman
                  # cizgisi). Bu satir YOKKEN olcum uretiliyor ama is
                  # kaydina HIC ULASMIYORDU -> zincir `pre_qa` halkasini
                  # kanitsiz gorup HER videoyu reddediyordu (olculdu:
                  # log "RENDER-QA ... FAIL sahne=8 kapsam=1.0" diyor,
                  # kayitta `render_qa` bos). Ayni kusur sinifi daha once
                  # avci ozetinde de yasandi: `d.update` anahtarlari ACIKCA
                  # listelidir, listeye girmeyen alan sessizce DUSER.
                  "render_qa": sonuc.get("render_qa") or {},
                  "edit_plani": sonuc.get("edit_plani") or {},
                  "dususler": sonuc.get("dususler") or []})
        # ── FAZ R-1d-a: ZINCIRIN SON HALKASI — TESLIM ──
        # ⚠ Burada RENDER/STORAGE yeniden yazilmaz; sadece bitmis isin
        # kanitlari toplanip kabul edilip edilmedigine karar verilir.
        _teslim_et(is_id, d)
    except Exception as e:
        traceback.print_exc()
        d.update({"durum": "hata", "hata": str(e)[:300], "mesaj": "Hata olustu"})
    finally:
        _durum_kaydet(is_id)
        # yuklenen karakter/stil + TUM ara ciktilar (sahne png/mp3, ham render) KALICI DEGIL
        try:
            shutil.rmtree(os.path.join(GECICI, is_id), ignore_errors=True)
            shutil.rmtree(os.path.join(pipeline.PUBLIC, "isler", is_id), ignore_errors=True)
            ham = os.path.join(pipeline.STUDYO, "out", f"{is_id}.mp4")
            if os.path.exists(ham):
                os.remove(ham)
        except Exception:
            pass


_teslim_kilidi = threading.Lock()


def _teslim_et(is_id, d):
    """Bitmis isi TESLIM ZINCIRINDEN gecir ve kabul edilirse kutuphaneye al.

    ⚠ TESLIM EDILMEMEK BIR HATA DEGILDIR: video dosyasi durur ve sahibi
    indirebilir; yalnizca "kabul edilmis final" SAYILMAZ ve son-3
    kutuphanesine GIRMEZ. Neden `d["teslim"]` icinde GORUNUR kalir.
    ⚠ Tavani asan kayit icin DOSYA SILINMEZ; silme KUYRUGU ise yazilir.
    """
    tid = str(d.get("tenant_id") or "")
    dosya = imzali_url.guvenli_ad(str(d.get("video") or ""))
    var = os.path.exists(os.path.join(pipeline.CIKTI_DIR, dosya)) if dosya \
        else False
    try:
        with _teslim_kilidi:
            depo = _kutuphane_oku()
            r = teslim.teslim_et(is_id=is_id, tenant_id=tid, kayit=d,
                                 kutuphane_deposu=depo,
                                 kabul_zamani=time.time(), dosya_var=var,
                                 ttl_sn=IMZA_TTL_SN)
            if r["teslim"]:
                _kutuphane_yaz(depo)
        d["teslim"] = {"teslim": r["teslim"], "neden": r["neden"],
                       "eksik": r["zincir"]["eksik"],
                       "silme_kuyrugu": r["silinecek"]}
        print(f"  TESLIM {is_id}: {'KABUL' if r['teslim'] else 'RED'}"
              f"{'' if r['teslim'] else ' — ' + r['neden']}")
    except Exception as e:                                    # noqa: BLE001
        # ⚠ Teslim karari patlarsa is "kabul edildi" SAYILMAZ.
        d["teslim"] = {"teslim": False, "neden": f"TESLIM-HATASI:{e}"[:200],
                       "eksik": [], "silme_kuyrugu": []}


def _isci():
    """Kuyruk iscisi. ISCI_SAYISI kadar paralel calisir (10 cekirdekli RX-4'te 2 is
    rahat sigar: gorsel asamasi ag-bekleme, CPU bosta; iki render cakisirsa ikisi de
    biraz yavaslar ama tamamlanir). Dis try/except: tek isteki hata isciyi OLDURMEZ."""
    while True:
        gorev = is_kuyrugu.get()
        try:
            _bir_is(*gorev)
        except Exception:
            traceback.print_exc()
        finally:
            is_kuyrugu.task_done()


def _temizlik_dongusu():
    """6 saatte bir eski dosyalari temizle (surec restart olmasa da disk dolmasin)."""
    while True:
        time.sleep(6 * 3600)
        _eski_ciktilari_temizle()


# ⚠ FAZ R-1d-a: ilk hesap env'den acilir (parola koda YAZILMAZ). Hesap yoksa
# ve ZORUNLU_OTURUM aciksa hicbir uc calismaz — bu FAIL-CLOSED sozlesmesinin
# istenen davranisi; `/api/saglik` `hesap_sayisi: 0` diyerek GORUNUR kilar.
_provizyon()
_durumlari_yukle()          # restart'ta eski job state'leri geri yukle (poll 404 vermesin)
_eski_ciktilari_temizle()   # 14 gunden eski cikti/durum dosyalarini temizle (disk)
threading.Thread(target=_temizlik_dongusu, daemon=True).start()
# 2 paralel isci (eski 2 vCPU sunucuda 1'di): iki kisi ayni anda video uretebilir.
# ISCI_SAYISI env ile ayarlanir; render cakismasi kabul edilebilir yavaslatma yaratir.
_ISCI_SAYISI = max(1, int(os.environ.get("ISCI_SAYISI", "2")))
for _ in range(_ISCI_SAYISI):
    threading.Thread(target=_isci, daemon=True).start()
