#!/usr/bin/env python3
"""Vidrush Web — dis kaynak yardimcilari.
- YouTube arama + indirme (yt-dlp): gercek footage'i sahnelere katmak icin ('any video' modu).
- Magnific upscale: uretilen sahne/kapak gorsellerini profesyonel cozunurluge yukseltmek icin.

TELIF NOTU: 'any video' modu telifli YT icerigini indirir. Bu icerigi kendi monetize
kanalinda kullanmak copyright strike/demonetizasyon riski tasir. Sorumluluk kullanicidadir.
"""
import os
import sys
import time
import base64

import requests

MAGNIFIC_KEY = os.environ.get("MAGNIFIC_KEY", "")
PEXELS_KEY = os.environ.get("PEXELS_KEY", "")
MAG_BASE = "https://api.magnific.com/v1/ai/image-upscaler"

# Edit stiline gore Magnific optimize profili
MAG_PROFIL = {
    "sinematik-belgesel": "films_n_photography",
    "anlati-belgesel": "nature_n_landscapes",
    "hizli-retention": "standard",
}


# ─────────────────────────── YouTube (yt-dlp) ───────────────────────────

def youtube_ara(sorgu: str, adet: int = 6):
    """yt-dlp ile YouTube araması. [{baslik,url,sure,kanal}] döner."""
    import yt_dlp
    opts = {"quiet": True, "skip_download": True, "extract_flat": True,
            "noplaylist": True, "no_warnings": True}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            r = ydl.extract_info(f"ytsearch{adet}:{sorgu}", download=False)
    except Exception as e:
        print(f"  youtube_ara hata: {str(e)[:160]}", file=sys.stderr)
        return []
    out = []
    for e in (r.get("entries") or []):
        vid = e.get("id")
        out.append({
            "baslik": e.get("title") or "",
            "url": e.get("url") or (f"https://youtu.be/{vid}" if vid else ""),
            "sure": e.get("duration"),
            "kanal": e.get("channel") or e.get("uploader") or "",
        })
    return [o for o in out if o["url"]]


def youtube_indir(url: str, hedef: str, maks_sure: int = 60) -> bool:
    """En iyi mp4 (<=1080p) indir; maks_sure saniyeye kadar (hizli + kucuk).
    hedef .mp4 yolu (uzantisiz verilirse yt-dlp ekler)."""
    import yt_dlp
    taban = hedef[:-4] if hedef.endswith(".mp4") else hedef
    opts = {
        "quiet": True, "no_warnings": True, "noplaylist": True,
        "format": ("bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/"
                   "best[height<=1080][ext=mp4]/best[height<=1080]/best"),
        "outtmpl": taban + ".%(ext)s",
        "merge_output_format": "mp4",
        "retries": 2,
        "socket_timeout": 30,
    }
    if maks_sure:
        try:
            opts["download_ranges"] = yt_dlp.utils.download_range_func(None, [(0, maks_sure)])
            opts["force_keyframes_at_cuts"] = True
        except Exception:
            pass  # eski yt-dlp
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
    except Exception as e:
        print(f"  youtube_indir hata: {str(e)[:160]}", file=sys.stderr)
        return False
    son = taban + ".mp4"
    return os.path.exists(son) and os.path.getsize(son) > 10000


def youtube_sahne(sorgu: str, hedef: str, maks_sure: int = 25) -> bool:
    """Sorgudan ilk uygun videoyu bul ve indir. Basarili ise True."""
    for aday in youtube_ara(sorgu, adet=5):
        s = aday.get("sure")
        if s and s > 3600:      # 1 saatten uzun canli/podcast'leri atla
            continue
        if youtube_indir(aday["url"], hedef, maks_sure=maks_sure):
            return True
    return False


# ─────────────────────────── Pexels (lisansli stok yedegi) ───────────────────────────

def pexels_video(sorgu: str, hedef: str) -> bool:
    """Pexels'ten yatay stok video indir (YT basarisiz olursa guvenli yedek)."""
    if not PEXELS_KEY:
        return False
    try:
        r = requests.get("https://api.pexels.com/videos/search",
                         headers={"Authorization": PEXELS_KEY},
                         params={"query": sorgu, "per_page": 5, "orientation": "landscape"},
                         timeout=30)
        r.raise_for_status()
        for v in r.json().get("videos", []):
            files = [f for f in v.get("video_files", [])
                     if f.get("file_type") == "video/mp4" and (f.get("width") or 0) >= 1280]
            files.sort(key=lambda f: f.get("width", 0))   # en kucuk >=1280 (hafif)
            if not files:
                continue
            data = requests.get(files[0]["link"], timeout=150).content
            with open(hedef, "wb") as f:
                f.write(data)
            if os.path.exists(hedef) and os.path.getsize(hedef) > 10000:
                return True
    except Exception as e:
        print(f"  pexels hata: {str(e)[:140]}", file=sys.stderr)
    return False


def footage_getir(sorgu: str, hedef: str, yt_once: bool = True) -> bool:
    """Sahne footage'i getir: YT (any-video) once, sonra Pexels yedek.
    yt_once False ise once Pexels dener (guvenli mod)."""
    kaynaklar = [youtube_sahne, pexels_video] if yt_once else [pexels_video, youtube_sahne]
    for fn in kaynaklar:
        try:
            if fn(sorgu, hedef):
                return True
        except Exception:
            continue
    return False


# ─────────────────────────── Magnific upscale ───────────────────────────

def magnific_var() -> bool:
    return bool(MAGNIFIC_KEY)


def magnific_upscale(gorsel_yolu: str, optimized_for: str = "films_n_photography",
                     scale: str = "2x", zaman_asimi: int = 210) -> bool:
    """Gorseli Magnific ile upscale eder; yerinde uzerine yazar. Basarili ise True.
    Async: POST -> task_id -> GET poll -> COMPLETED URL indir."""
    if not MAGNIFIC_KEY or not os.path.exists(gorsel_yolu):
        return False
    try:
        with open(gorsel_yolu, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        h = {"x-magnific-api-key": MAGNIFIC_KEY}
        body = {"image": b64, "scale_factor": scale,
                "optimized_for": optimized_for, "engine": "automatic"}
        r = requests.post(MAG_BASE, headers=h, json=body, timeout=90)
        if r.status_code >= 400:
            print(f"  magnific POST {r.status_code}: {r.text[:160]}", file=sys.stderr)
            return False
        tid = r.json()["data"]["task_id"]
        bas = time.time()
        while time.time() - bas < zaman_asimi:
            time.sleep(6)
            d = requests.get(f"{MAG_BASE}/{tid}", headers=h, timeout=30).json().get("data", {})
            durum = d.get("status")
            if durum == "COMPLETED" and d.get("generated"):
                img = requests.get(d["generated"][0], timeout=180).content
                with open(gorsel_yolu, "wb") as f:
                    f.write(img)
                return True
            if durum == "FAILED":
                print("  magnific FAILED", file=sys.stderr)
                return False
        print("  magnific zaman asimi", file=sys.stderr)
        return False
    except Exception as e:
        print(f"  magnific hata: {str(e)[:160]}", file=sys.stderr)
        return False
