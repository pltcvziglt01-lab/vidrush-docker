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
PIXABAY_KEY = os.environ.get("PIXABAY_KEY", "")
MAG_BASE = "https://api.magnific.com/v1/ai/image-upscaler"
_MAG_KAPALI = False   # 402/401 gorulunce oturum boyunca kapat (bosa cagri yok)

# YouTube veri-merkezi IP'lerinden "Sign in to confirm you're not a bot" verir.
# Cozum: tarayicidan disa aktarilan Netscape cookies dosyasi (varsa) kullanilir.
YT_COOKIES = os.environ.get("YT_COOKIES_FILE", "/opt/vidrush/webapp/veri/yt_cookies.txt")


def _yt_cookie_opts(opts: dict) -> dict:
    if YT_COOKIES and os.path.exists(YT_COOKIES):
        opts["cookiefile"] = YT_COOKIES
    return opts


# ─────────────────────────── YouTube (yt-dlp) ───────────────────────────

def youtube_ara(sorgu: str, adet: int = 6):
    """yt-dlp ile YouTube araması. [{baslik,url,sure,kanal}] döner."""
    import yt_dlp
    opts = _yt_cookie_opts({"quiet": True, "skip_download": True, "extract_flat": True,
                            "noplaylist": True, "no_warnings": True,
                            "socket_timeout": 30, "retries": 1})   # hang koruması
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
    son = taban + ".mp4"
    opts = {
        "quiet": True, "no_warnings": True, "noplaylist": True,
        "format": ("bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/"
                   "best[height<=1080][ext=mp4]/best[height<=1080]/best"),
        "outtmpl": taban + ".%(ext)s",
        "merge_output_format": "mp4",
        # merge/fallback .mkv/.webm uretebilir -> ffmpeg ile mp4'e cevir (Remotion mp4 bekler)
        "postprocessors": [{"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}],
        "retries": 2,
        "socket_timeout": 30,
    }
    _yt_cookie_opts(opts)
    if maks_sure:
        try:
            opts["download_ranges"] = yt_dlp.utils.download_range_func(None, [(0, maks_sure)])
            opts["force_keyframes_at_cuts"] = True
        except Exception:
            print("  yt-dlp download_ranges desteklenmiyor (maks_sure yok sayildi)", file=sys.stderr)
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
    except Exception as e:
        print(f"  youtube_indir hata: {str(e)[:160]}", file=sys.stderr)
    if os.path.exists(son) and os.path.getsize(son) > 10000:
        return True
    # Yedek: convertor calismadi -> gercek dosyayi bul, ffmpeg ile mp4'e remux
    import glob
    import subprocess
    adaylar = [f for f in glob.glob(taban + ".*")
               if os.path.exists(f) and os.path.getsize(f) > 10000 and f != son]
    if not adaylar:
        return False
    en_buyuk = max(adaylar, key=os.path.getsize)
    try:
        # -c copy DEGIL: VP9/webm'i H.264/AAC'e RE-ENCODE et. Aksi halde .mp4 uzantili ama
        # Remotion'un headless Chrome'unun cozemedigi bir konteyner cikip sahne siyah kalirdi.
        r = subprocess.run(
            ["ffmpeg", "-y", "-i", en_buyuk, "-c:v", "libx264", "-preset", "veryfast",
             "-pix_fmt", "yuv420p", "-c:a", "aac", "-movflags", "+faststart", son],
            capture_output=True, timeout=300)
        if r.returncode != 0:
            print(f"  ffmpeg remux rc={r.returncode}: {r.stderr[-200:]}", file=sys.stderr)
    except Exception as e:
        print(f"  ffmpeg remux hata: {str(e)[:120]}", file=sys.stderr)
    # temiz uretim: ara/orijinal dosyalari birak (disk hijyeni)
    for a in adaylar:
        try: os.remove(a)
        except Exception: pass
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


# ─────────────────────── Stok video ortak yardimcilari ───────────────────────

def _stok_indir(url: str, ham_yol: str, zaman_asimi: int = 120) -> bool:
    """URL'i parca parca (stream) diske yaz. RAM sismez, yavas CDN'de asilmaz."""
    try:
        with requests.get(url, stream=True, timeout=(15, zaman_asimi)) as r:
            r.raise_for_status()
            with open(ham_yol, "wb") as f:
                for parca in r.iter_content(chunk_size=1 << 16):
                    if parca:
                        f.write(parca)
    except Exception as e:
        print(f"  stok indir hata: {str(e)[:140]}", file=sys.stderr)
        return False
    return os.path.exists(ham_yol) and os.path.getsize(ham_yol) > 20000


def _remotion_uygun_yap(ham_yol: str, hedef: str) -> bool:
    """Ham stok mp4'u Remotion'un headless Chrome'unun KESIN cozebilecegi bicime getir.
    H.264+yuv420p ise sadece +faststart remux; degilse H.264'e RE-ENCODE (siyah sahne olmasin)."""
    import subprocess
    codec = ""; piks = ""
    try:
        p = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=codec_name,pix_fmt", "-of", "default=nw=1:nk=1", ham_yol],
            capture_output=True, timeout=30)
        satirlar = p.stdout.decode(errors="ignore").split()
        if satirlar:
            codec = satirlar[0]
            piks = satirlar[1] if len(satirlar) > 1 else ""
    except Exception:
        pass
    uygun = (codec == "h264" and piks == "yuv420p")
    try:
        if uygun:
            cmd = ["ffmpeg", "-y", "-i", ham_yol, "-c", "copy", "-movflags", "+faststart", hedef]
        else:
            cmd = ["ffmpeg", "-y", "-i", ham_yol, "-c:v", "libx264", "-preset", "veryfast",
                   "-pix_fmt", "yuv420p", "-an", "-movflags", "+faststart", hedef]
        r = subprocess.run(cmd, capture_output=True, timeout=300)
        if r.returncode != 0 and uygun:   # remux tutmadiysa re-encode'a dus
            r = subprocess.run(
                ["ffmpeg", "-y", "-i", ham_yol, "-c:v", "libx264", "-preset", "veryfast",
                 "-pix_fmt", "yuv420p", "-an", "-movflags", "+faststart", hedef],
                capture_output=True, timeout=300)
        if r.returncode != 0:
            print(f"  ffmpeg normalize rc={r.returncode}", file=sys.stderr)
    except Exception as e:
        print(f"  ffmpeg normalize hata: {str(e)[:120]}", file=sys.stderr)
    finally:
        try:
            if os.path.abspath(ham_yol) != os.path.abspath(hedef):
                os.remove(ham_yol)
        except Exception:
            pass
    return os.path.exists(hedef) and os.path.getsize(hedef) > 20000


def _indir_ve_hazirla(url: str, hedef: str, zaman_asimi: int = 120) -> bool:
    ham = hedef + ".ham"
    if not _stok_indir(url, ham, zaman_asimi):
        try: os.remove(ham)
        except Exception: pass
        return False
    return _remotion_uygun_yap(ham, hedef)


# ─────────────────────────── Pexels (ucretsiz stok) ───────────────────────────

def pexels_video(sorgu: str, hedef: str) -> bool:
    """Pexels'ten yatay 1080p stok video. Ucretsiz API anahtari yeter (PEXELS_KEY)."""
    if not PEXELS_KEY:
        return False
    try:
        r = requests.get("https://api.pexels.com/videos/search",
                         headers={"Authorization": PEXELS_KEY},
                         params={"query": sorgu, "per_page": 8,
                                 "orientation": "landscape", "size": "medium"}, timeout=30)
        if r.status_code == 401:
            print("  pexels 401 (anahtar gecersiz/placeholder)", file=sys.stderr)
            return False
        r.raise_for_status()
        for v in r.json().get("videos", []):
            files = [f for f in v.get("video_files", [])
                     if f.get("file_type") == "video/mp4"
                     and (f.get("width") or 0) >= 1280 and (f.get("height") or 0) >= 700]
            if not files:
                continue
            files.sort(key=lambda f: (0 if f.get("width", 0) <= 1920 else 1,
                                      abs(f.get("width", 0) - 1920)))
            if _indir_ve_hazirla(files[0]["link"], hedef):
                return True
    except Exception as e:
        print(f"  pexels hata: {str(e)[:140]}", file=sys.stderr)
    return False


# ─────────────────────────── Pixabay (ucretsiz stok) ───────────────────────────

def pixabay_video(sorgu: str, hedef: str) -> bool:
    """Pixabay'den yatay stok video. Ucretsiz API anahtari yeter (PIXABAY_KEY)."""
    if not PIXABAY_KEY:
        return False
    try:
        r = requests.get("https://pixabay.com/api/videos/",
                         params={"key": PIXABAY_KEY, "q": sorgu,
                                 "per_page": 12, "safesearch": "true"}, timeout=30)
        if r.status_code in (400, 401, 403):
            print(f"  pixabay {r.status_code} (anahtar/sorgu)", file=sys.stderr)
            return False
        r.raise_for_status()
        for hit in r.json().get("hits", []):
            vids = hit.get("videos", {}) or {}
            aday = None
            for boyut in ("large", "medium", "small"):
                v = vids.get(boyut) or {}
                w = v.get("width") or 0; h = v.get("height") or 0
                if v.get("url") and w >= 1280 and w >= h:
                    aday = v["url"]; break
            if aday and _indir_ve_hazirla(aday, hedef):
                return True
    except Exception as e:
        print(f"  pixabay hata: {str(e)[:140]}", file=sys.stderr)
    return False


# ────────────── Freepik stok video (opsiyonel — arama bedava, indirme kredi ister) ──────────────

def freepik_video(sorgu: str, hedef: str) -> bool:
    if not MAGNIFIC_KEY:
        return False
    h = {"x-freepik-api-key": MAGNIFIC_KEY, "Accept": "application/json"}
    try:
        r = requests.get("https://api.freepik.com/v1/videos", headers=h,
                         params={"term": sorgu, "per_page": 8}, timeout=30)
        if r.status_code in (401, 402, 403):
            return False
        r.raise_for_status()
        for item in (r.json().get("data") or []):
            vid = item.get("id")
            if not vid:
                continue
            dr = requests.get(f"https://api.freepik.com/v1/videos/{vid}/download",
                              headers=h, timeout=30)
            if dr.status_code in (402, 403):
                return False   # kredi yok -> sonraki id'ler de ayni, hemen cik
            if dr.status_code >= 400:
                continue
            url = (dr.json().get("data") or {}).get("url")
            if url and _indir_ve_hazirla(url, hedef):
                return True
    except Exception as e:
        print(f"  freepik hata: {str(e)[:140]}", file=sys.stderr)
    return False


def footage_getir(sorgu: str, hedef: str, yt_once: bool = True) -> bool:
    """Sahne footage'i getir. Oncelik GERCEK+UCRETSIZ stok video:
       Pexels -> Pixabay -> Freepik(kredi varsa) -> YouTube(cookie varsa).
    Her katman kendi timeout'una sahip; biri patlarsa digerine gecer; hicbiri yoksa
    False -> caller AI gorsele duser."""
    kaynaklar = [pexels_video, pixabay_video, freepik_video]
    if yt_once and YT_COOKIES and os.path.exists(YT_COOKIES):
        kaynaklar.append(youtube_sahne)   # cookie varsa YT'yi de dene (en sona)
    for fn in kaynaklar:
        try:
            if fn(sorgu, hedef):
                print(f"  footage OK: {fn.__name__} -> {os.path.basename(hedef)}", file=sys.stderr)
                return True
        except Exception as e:
            print(f"  {fn.__name__} atlandi: {str(e)[:100]}", file=sys.stderr)
            continue
    print(f"  footage YOK (AI gorsele dusulecek): {sorgu[:60]}", file=sys.stderr)
    return False


# ─────────────────────────── Magnific upscale ───────────────────────────

def magnific_var() -> bool:
    return bool(MAGNIFIC_KEY)


def magnific_upscale(gorsel_yolu: str, optimized_for: str = "films_n_photography",
                     scale: str = "2x", zaman_asimi: int = 210) -> bool:
    """Gorseli Magnific ile upscale eder; yerinde uzerine yazar. Basarili ise True.
    Async: POST -> task_id -> GET poll -> COMPLETED URL indir."""
    global _MAG_KAPALI
    if _MAG_KAPALI or not MAGNIFIC_KEY or not os.path.exists(gorsel_yolu):
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
            if r.status_code in (401, 402, 403):
                _MAG_KAPALI = True   # kredi/yetki bitti -> bu is boyunca bir daha deneme
            return False
        tid = r.json()["data"]["task_id"]
        bas = time.time()
        while time.time() - bas < zaman_asimi:
            time.sleep(6)
            try:  # gecici 429/500/timeout tek poll'u atlar, task'i terk etmez
                d = requests.get(f"{MAG_BASE}/{tid}", headers=h, timeout=30).json().get("data", {})
            except Exception:
                continue
            durum = d.get("status")
            if durum == "COMPLETED" and d.get("generated"):
                resp = requests.get(d["generated"][0], timeout=180)
                resp.raise_for_status()
                if len(resp.content) < 10000:  # bozuk/HTML yanit -> orijinali KORU
                    return False
                tmp = gorsel_yolu + ".mag.tmp"   # once temp, sonra atomik replace
                with open(tmp, "wb") as f:
                    f.write(resp.content)
                os.replace(tmp, gorsel_yolu)
                return True
            if durum == "FAILED":
                print("  magnific FAILED", file=sys.stderr)
                return False
        print("  magnific zaman asimi", file=sys.stderr)
        return False
    except Exception as e:
        print(f"  magnific hata: {str(e)[:160]}", file=sys.stderr)
        return False
