#!/usr/bin/env python3
"""Vidrush Web sunucusu (FastAPI).
Kullanici referans KARAKTER + STIL gorseli yukler (bir kez), sonra hikaye metni gonderir.
Uretim tek-cekirdek VPS'i korumak icin sirayla (kuyruk) yapilir.
"""
import os
import io
import json
import time
import queue
import asyncio
import threading
import traceback

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image

import pipeline

KOK = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(KOK, "static")
VERI = os.path.join(KOK, "veri")
PRESET = os.path.join(VERI, "presets")
os.makedirs(PRESET, exist_ok=True)

app = FastAPI(title="Vidrush Web")

isler = {}          # job_id -> durum
is_kuyrugu = queue.Queue()


def _kucult(data: bytes, hedef: str, boyut=1024):
    im = Image.open(io.BytesIO(data)).convert("RGB")
    im.thumbnail((boyut, boyut))
    im.save(hedef, "PNG")


@app.get("/", response_class=HTMLResponse)
def anasayfa():
    with open(os.path.join(STATIC, "index.html"), encoding="utf-8") as f:
        return f.read()


@app.post("/api/preset")
async def preset_kaydet(session: str = Form(...),
                        karakter: UploadFile = File(...),
                        stil: UploadFile = File(None)):
    if not session.strip():
        raise HTTPException(400, "session gerekli")
    kdir = os.path.join(PRESET, session)
    os.makedirs(kdir, exist_ok=True)
    _kucult(await karakter.read(), os.path.join(kdir, "character.png"))
    var_stil = False
    if stil is not None:
        _kucult(await stil.read(), os.path.join(kdir, "style.png"))
        var_stil = True
    return {"ok": True, "stil": var_stil}


@app.get("/api/preset/{session}")
def preset_var(session: str):
    kdir = os.path.join(PRESET, session)
    return {"karakter": os.path.exists(os.path.join(kdir, "character.png")),
            "stil": os.path.exists(os.path.join(kdir, "style.png"))}


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
def uret_baslat(session: str = Form(...), story: str = Form(...),
                edit: str = Form(pipeline.VARSAYILAN_EDIT),
                magnific: str = Form("0"),
                kaynak_modu: str = Form("yt")):
    kdir = os.path.join(PRESET, session)
    kar = os.path.join(kdir, "character.png")
    if not os.path.exists(kar):
        raise HTTPException(400, "Once referans karakter gorseli yukle")
    if len(story.strip()) < 20:
        raise HTTPException(400, "Hikaye metni cok kisa")
    edit_id = edit if edit in pipeline.EDIT_STILLERI else pipeline.VARSAYILAN_EDIT
    mag = str(magnific).lower() in ("1", "true", "on", "evet")
    modu = kaynak_modu if kaynak_modu in ("yt", "guvenli", "kapali") else "yt"
    is_id = f"job_{int(time.time()*1000)}_{session[:6]}"
    isler[is_id] = {"durum": "kuyrukta", "ilerleme": 0, "mesaj": "Sirada...",
                    "video": None, "kapak": None, "hata": None}
    is_kuyrugu.put((is_id, story.strip(), kar, edit_id, mag, modu))
    return {"job_id": is_id, "kuyruk": is_kuyrugu.qsize(), "edit": edit_id}


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


def _isci():
    """Tek isci: kuyruktan is alir, sirayla uretir (1 vCPU korumasi)."""
    while True:
        is_id, story, kar, edit_id, magnific, kaynak_modu = is_kuyrugu.get()
        d = isler[is_id]
        d["durum"] = "uretiliyor"

        def ilerle(msg, yuzde):
            d["mesaj"] = msg
            d["ilerleme"] = yuzde

        try:
            sonuc = asyncio.run(pipeline.uret(is_id, story, kar, edit_id, magnific,
                                              kaynak_modu, ilerle))
            d.update({"durum": "bitti", "ilerleme": 100, "mesaj": "Hazir!",
                      "video": "ciktilar/" + sonuc["video"],
                      "kapak": ("ciktilar/" + sonuc["kapak"]) if sonuc.get("kapak") else None,
                      "sure": sonuc.get("sure"), "sahne_sayisi": sonuc.get("sahne_sayisi"),
                      "edit": sonuc.get("edit")})
        except Exception as e:
            traceback.print_exc()
            d.update({"durum": "hata", "hata": str(e)[:300], "mesaj": "Hata olustu"})
        finally:
            is_kuyrugu.task_done()


threading.Thread(target=_isci, daemon=True).start()
