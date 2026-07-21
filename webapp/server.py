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
os.makedirs(GECICI, exist_ok=True)

app = FastAPI(title="BEDOSAHO AI")

isler = {}
is_kuyrugu = queue.Queue()

_SES_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def gecerli_session(session: str) -> str:
    if not _SES_RE.match(session or ""):
        raise HTTPException(400, "gecersiz session")
    return session


def _kucult(data: bytes, hedef: str, boyut=1024):
    im = Image.open(io.BytesIO(data)).convert("RGB")
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
    Magnific ve footage plana gore OTOMATIK. tur: animasyon|documentary."""
    session = gecerli_session(session)
    if len(story.strip()) < 20:
        raise HTTPException(400, "Hikaye metni cok kisa")
    mod = tur if tur in ("animasyon", "documentary") else "documentary"
    edit_id = edit if edit in pipeline.EDIT_STILLERI else pipeline.VARSAYILAN_EDIT
    try:
        sd = max(0.3, min(30.0, float(sure_dk)))
    except Exception:
        sd = 2.0
    gecis_acik = _bayrak(gecis)
    zoom_acik = _bayrak(zoom)

    is_id = f"job_{int(time.time()*1000)}_{session[:6]}"
    idir = os.path.join(GECICI, is_id)
    os.makedirs(idir, exist_ok=True)
    kar = ""
    if karakter is not None:
        data = await karakter.read()
        if data:
            kar = os.path.join(idir, "character.png")
            _kucult(data, kar)
    stil_yol = ""
    if stil is not None:
        data = await stil.read()
        if data:
            stil_yol = os.path.join(idir, "style.png")
            _kucult(data, stil_yol)

    isler[is_id] = {"durum": "kuyrukta", "ilerleme": 0, "mesaj": "Sirada...",
                    "video": None, "kapak": None, "hata": None}
    is_kuyrugu.put((is_id, story.strip(), kar, stil_yol, mod, edit_id, sd, gecis_acik, zoom_acik))
    return {"job_id": is_id, "kuyruk": is_kuyrugu.qsize(), "tur": mod, "edit": edit_id}


@app.get("/api/job/{is_id}")
def is_durum(is_id: str):
    d = isler.get(is_id)
    if not d:
        raise HTTPException(404, "is yok")
    return d


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
                  "edit": sonuc.get("edit")})
    except Exception as e:
        traceback.print_exc()
        d.update({"durum": "hata", "hata": str(e)[:300], "mesaj": "Hata olustu"})
    finally:
        # yuklenen karakter/stil KALICI DEGIL — is dizinini temizle
        try:
            shutil.rmtree(os.path.join(GECICI, is_id), ignore_errors=True)
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


threading.Thread(target=_isci, daemon=True).start()
