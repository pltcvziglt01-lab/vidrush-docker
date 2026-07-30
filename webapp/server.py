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

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from PIL import Image

import pipeline

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


def _bayrak(v) -> bool:
    return str(v).lower() in ("1", "true", "on", "evet", "yes")


@app.get("/", response_class=HTMLResponse)
def anasayfa():
    with open(os.path.join(STATIC, "index.html"), encoding="utf-8") as f:
        return f.read()


@app.get("/api/saglik")
def saglik():
    """Hangi servislerin anahtari kurulu (deger DONMEZ, sadece var/yok)."""
    return {
        "openai": bool(os.environ.get("OPENAI_KEY")),
        "magnific": bool(os.environ.get("MAGNIFIC_KEY")),
        "pexels": bool(os.environ.get("PEXELS_KEY")),
    }


@app.get("/api/edit-stilleri")
def edit_listesi():
    return [{"id": k, "ad": v["ad"], "ozet": v["ozet"],
             "sahne_sn": v["sahne_sn"], "footage_pct": v["footage_pct"]}
            for k, v in pipeline.EDIT_STILLERI.items()]


@app.get("/api/animasyon-stilleri")
def anim_listesi():
    """Animasyon alt-stilleri (anlati-deneme / egitici-explainer)."""
    return [{"id": k, "ad": v["ad"], "ozet": v["ozet"], "sahne_sn": v["sahne_sn"]}
            for k, v in pipeline.ANIMASYON_STILLERI.items()]


@app.post("/api/generate")
async def uret_baslat(session: str = Form(...), story: str = Form(...),
                      tur: str = Form("documentary"),
                      edit: str = Form(pipeline.VARSAYILAN_EDIT),
                      sure_dk: str = Form("2"),
                      gecis: str = Form("1"),
                      zoom: str = Form("1"),
                      karakter: UploadFile = File(None),
                      stil: UploadFile = File(None)):
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
        sd = max(0.3, min(14.0, float(sure_dk)))
    except Exception:
        sd = 2.0
    gecis_acik = _bayrak(gecis)
    zoom_acik = _bayrak(zoom)

    is_id = f"job_{int(time.time()*1000)}_{session[:6]}_{os.urandom(3).hex()}"
    idir = os.path.join(GECICI, is_id)
    os.makedirs(idir, exist_ok=True)
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
    except HTTPException:
        shutil.rmtree(idir, ignore_errors=True)
        raise
    except Exception:
        shutil.rmtree(idir, ignore_errors=True)
        raise HTTPException(400, "Görsel okunamadı (geçerli bir resim dosyası yükleyin)")

    isler[is_id] = {"durum": "kuyrukta", "ilerleme": 0, "mesaj": "Sirada...",
                    "video": None, "kapak": None, "hata": None}
    _durum_kaydet(is_id)
    is_kuyrugu.put((is_id, story.strip(), kar, stil_yol, mod, edit_id, sd, gecis_acik, zoom_acik))
    return {"job_id": is_id, "kuyruk": is_kuyrugu.qsize(), "tur": mod, "edit": edit_id}


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


def _bir_is(is_id, story, kar, stil_yol, mod, edit_id, sure_dk, gecis_acik, zoom_acik):
    d = isler.get(is_id)
    if not d:
        return
    d["durum"] = "uretiliyor"
    _durum_kaydet(is_id)

    def ilerle(msg, yuzde):
        d["mesaj"] = msg
        d["ilerleme"] = yuzde

    try:
        sonuc = asyncio.run(pipeline.uret(is_id, story, kar, stil_yol, mod, edit_id,
                                          sure_dk, gecis_acik, zoom_acik, ilerle))
        d.update({"durum": "bitti", "ilerleme": 100, "mesaj": "Hazir!",
                  "video": "ciktilar/" + sonuc["video"],
                  "kapak": ("ciktilar/" + sonuc["kapak"]) if sonuc.get("kapak") else None,
                  "sure": sonuc.get("sure"), "sahne_sayisi": sonuc.get("sahne_sayisi"),
                  "edit": sonuc.get("edit"), "uyari": sonuc.get("uyari")})
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
    """Tek isci: kuyruktan is alir, sirayla uretir (1 vCPU korumasi).
    Dis try/except: tek isteki beklenmedik hata isciyi OLDURMEZ (kuyruk donmaz)."""
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
threading.Thread(target=_isci, daemon=True).start()
