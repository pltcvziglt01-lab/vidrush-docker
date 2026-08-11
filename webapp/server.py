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

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from PIL import Image

import pipeline
import anim_studyo

KOK = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(KOK, "static")
VERI = os.path.join(KOK, "veri")
GECICI = os.path.join(VERI, "gecici")     # is basina yuklenen gorseller (uretim sonrasi silinir)
IS_DURUM_DIR = os.path.join(VERI, "durumlar")  # job state diske yazilir (restart'ta kaybolmasin)
os.makedirs(GECICI, exist_ok=True)
os.makedirs(IS_DURUM_DIR, exist_ok=True)

MAKS_UPLOAD = 20 * 1024 * 1024   # 20 MB gorsel tavani (OOM korumasi)

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


_OZEL_SES_RE = re.compile(r"^ozel:(elevenlabs|minimax|fishaudio|kokoro)_[A-Za-z0-9_-]{1,64}$")


def _ses_secimi(ses: str) -> str:
    """Ses form alanini dogrula: SESLER anahtari VEYA kutuphaneden 'ozel:<voice_id>' secimi."""
    s = (ses or "").strip()
    if s in pipeline.SESLER or _OZEL_SES_RE.match(s):
        return s
    return ""


def _bayrak(v) -> bool:
    return str(v).lower() in ("1", "true", "on", "evet", "yes")


@app.get("/", response_class=HTMLResponse)
def anasayfa():
    with open(os.path.join(STATIC, "index.html"), encoding="utf-8") as f:
        return f.read()


@app.get("/api/saglik")
def saglik():
    """Hangi servislerin anahtari kurulu (deger DONMEZ, sadece var/yok)."""
    import kaynak
    return {
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
        "freepik_anahtar_sayisi": len(kaynak.FREEPIK_KEYS),
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
    if saglayici not in ("elevenlabs", "minimax", "fishaudio", "kokoro"):
        raise HTTPException(400, "gecersiz saglayici")
    zaman, liste = _SES_KUTUPHANE_ONBELLEK.get(saglayici, (0, None))
    if liste is not None and time.time() - zaman < 600:
        return liste
    key = _ai33_key()
    if not key:
        raise HTTPException(503, "AI33 anahtari kurulu degil")
    import requests
    try:
        r = requests.get(f"https://api.ai33.pro/v3/voices?provider={saglayici}",
                         headers={"xi-api-key": key}, timeout=30)
        veri = r.json().get("data", [])
    except Exception:
        raise HTTPException(502, "Ses kütüphanesi alınamadı")
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


@app.post("/api/generate")
async def uret_baslat(session: str = Form(...), story: str = Form(...),
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
                      arkaplan: str = Form(""),
                      ses: str = Form(""),
                      isik: str = Form(""),
                      gorsel_model: str = Form(""),
                      karakter: UploadFile = File(None),
                      stil: UploadFile = File(None),
                      sahne_ref: List[UploadFile] = File(None)):
    """Karakter/stil gorselleri her video icin DOGRUDAN yuklenir (kalici kayit yok).
    Magnific ve footage plana gore OTOMATIK. tur: animasyon|documentary|hikaye."""
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
                    "video": None, "kapak": None, "hata": None}
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
                    acilis_dk, sref, _bayrak(sora), gorsel_model.strip()))
    return {"job_id": is_id, "kuyruk": is_kuyrugu.qsize(), "tur": mod, "edit": edit_id,
            "profil": profil.strip()}


@app.get("/api/isler")
def is_listesi(session: str):
    """Bu oturumun TUM isleri (Videolarim sekmesi) — sayfa yenilense/kapansa da is kaybolmaz.
    Kaynak: diskteki durum dosyalari; bellekte daha guncel hal varsa o kullanilir.
    Is id'si 'job_<ts>_<session[:6]>_<hex>' oldugu icin oturum eslesmesi id icinden yapilir."""
    import json
    session = gecerli_session(session)
    on6 = session[:6]
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
                cikti.append({"id": ad[:-5], "durum": d.get("durum"),
                              "ilerleme": d.get("ilerleme", 0), "mesaj": d.get("mesaj", ""),
                              "video": d.get("video"), "kapak": d.get("kapak"),
                              "sure": d.get("sure"), "edit": d.get("edit"),
                              "t": os.path.getmtime(yol)})
            except Exception:
                continue
    except Exception:
        pass
    cikti.sort(key=lambda x: -x["t"])
    return cikti[:30]


@app.get("/api/job/{is_id}")
def is_durum(is_id: str):
    d = isler.get(is_id)
    if not d:
        # bellekte yoksa (restart olmus olabilir) diskten dene
        try:
            import json
            yol = os.path.join(IS_DURUM_DIR, f"{gecerli_session(is_id)}.json")
            if os.path.exists(yol):
                with open(yol, encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        raise HTTPException(404, "is yok")
    if d.get("durum") == "kuyrukta":
        sira = _kuyruk_sirasi(is_id)
        if sira is not None:
            d = {**d, "kuyruk_sira": sira, "kuyruk_toplam": is_kuyrugu.qsize()}
    return d


def _kuyruk_sirasi(is_id):
    """Kuyruktaki isin 1-tabanli sirasi; kuyrukta degilse None."""
    try:
        with is_kuyrugu.mutex:
            idler = [g[0] for g in list(is_kuyrugu.queue)]
        return idler.index(is_id) + 1
    except ValueError:
        return None


@app.get("/ciktilar/{dosya}")
def cikti(dosya: str):
    yol = os.path.join(pipeline.CIKTI_DIR, os.path.basename(dosya))
    if not os.path.exists(yol):
        raise HTTPException(404, "yok")
    return FileResponse(yol)


def _bir_is(is_id, story, kar, stil_yol, mod, edit_id, sure_dk, gecis_acik, zoom_acik,
            profil_id="", altyazi="", altyazi_sablon="", palet="", palet_ozel="",
            arkaplan="", ses_secim="", isik="", acilis_dk=None, sahne_ref=None,
            sora_acik=False, gorsel_model_secim=""):
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
                                          gorsel_model_secim=gorsel_model_secim))
        d.update({"durum": "bitti", "ilerleme": 100, "mesaj": "Hazir!",
                  "video": "ciktilar/" + sonuc["video"],
                  "kapak": ("ciktilar/" + sonuc["kapak"]) if sonuc.get("kapak") else None,
                  "sure": sonuc.get("sure"), "sahne_sayisi": sonuc.get("sahne_sayisi"),
                  "edit": sonuc.get("edit"), "uyari": sonuc.get("uyari"),
                  "atiflar": sonuc.get("atiflar") or []})
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


_durumlari_yukle()          # restart'ta eski job state'leri geri yukle (poll 404 vermesin)
_eski_ciktilari_temizle()   # 14 gunden eski cikti/durum dosyalarini temizle (disk)
threading.Thread(target=_temizlik_dongusu, daemon=True).start()
# 2 paralel isci (eski 2 vCPU sunucuda 1'di): iki kisi ayni anda video uretebilir.
# ISCI_SAYISI env ile ayarlanir; render cakismasi kabul edilebilir yavaslatma yaratir.
for _ in range(max(1, int(os.environ.get("ISCI_SAYISI", "2")))):
    threading.Thread(target=_isci, daemon=True).start()
