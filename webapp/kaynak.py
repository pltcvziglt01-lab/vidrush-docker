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
import hashlib
import json
import threading

import requests

MAGNIFIC_KEY = os.environ.get("MAGNIFIC_KEY", "")

# ── COKLU FREEPIK ANAHTARI + GUNLUK KOTA TAKIBI (5 Agu 2026) ──
# Neden: Freepik API'sinde stok indirme Premium/Premium+/Pro planlarda KREDI HARCAMAZ ama
# GUNDE 100 ile sinirli (resmi belge). 40 dk'lik bir belgesel ~177 klip istiyor, yani tek
# anahtarla bir gunde bitmiyor. Ayrica tek anahtar iptal olursa / servis 5xx verirse is
# yarida kaliyordu.
# FREEPIK_KEYS = "anahtar1,anahtar2,anahtar3"  (MAGNIFIC_KEY geriye donuk calismaya devam eder)
# Sayac DISKTE tutulur: konteyner yeniden baslayinca kota sifirlanmis gibi davranmaz.
FREEPIK_KEYS = [k.strip() for k in os.environ.get("FREEPIK_KEYS", "").split(",") if k.strip()]
if not FREEPIK_KEYS and MAGNIFIC_KEY:
    FREEPIK_KEYS = [MAGNIFIC_KEY]
FP_GUNLUK_TAVAN = int(os.environ.get("FREEPIK_GUNLUK_TAVAN", "100"))
FP_KOTA_DOSYA = os.environ.get("FREEPIK_KOTA_DOSYA",
                               "/opt/vidrush/webapp/veri/freepik_kota.json")
_fp_kilit = threading.Lock()      # gorseller 4-8 paralel uretiliyor, sayac yarissiz olmali


def _fp_etiket(anahtar: str) -> str:
    """Anahtari dosyaya YAZMADAN kimliklendir (ilk 6 karakterin hash'i yeter)."""
    return hashlib.sha256(anahtar.encode()).hexdigest()[:10]


def _fp_kota_oku() -> dict:
    try:
        with open(FP_KOTA_DOSYA) as f:
            d = json.load(f)
    except Exception:
        return {}
    bugun = time.strftime("%Y-%m-%d")
    return d.get(bugun, {}) if isinstance(d, dict) else {}


def _fp_kota_yaz(sayaclar: dict) -> None:
    bugun = time.strftime("%Y-%m-%d")
    try:
        os.makedirs(os.path.dirname(FP_KOTA_DOSYA), exist_ok=True)
        # Sadece BUGUNU sakla: dosya suresiz buyumesin
        with open(FP_KOTA_DOSYA, "w") as f:
            json.dump({bugun: sayaclar}, f)
    except Exception as e:
        print(f"  freepik kota yazilamadi: {str(e)[:90]}", file=sys.stderr)


def freepik_anahtar_sec():
    """Bugun kotasi DOLMAMIS ilk anahtari dondurur. Hepsi doluysa None."""
    with _fp_kilit:
        sayac = _fp_kota_oku()
        for a in FREEPIK_KEYS:
            if sayac.get(_fp_etiket(a), 0) < FP_GUNLUK_TAVAN:
                return a
    return None


def freepik_sayac_artir(anahtar: str, adet: int = 1) -> None:
    """BASARILI indirmeden sonra cagrilir (basarisiz istek kota yemez)."""
    with _fp_kilit:
        sayac = _fp_kota_oku()
        e = _fp_etiket(anahtar)
        sayac[e] = sayac.get(e, 0) + adet
        _fp_kota_yaz(sayac)


def freepik_anahtar_doldu(anahtar: str) -> None:
    """Saglayici 'limit asildi' dediyse: bizim sayac ne derse desin bu anahtari bugun kapat.
    (Bizim sayacimiz web arayuzunden yapilan indirmeleri gormez, kayabilir.)"""
    with _fp_kilit:
        sayac = _fp_kota_oku()
        sayac[_fp_etiket(anahtar)] = FP_GUNLUK_TAVAN
        _fp_kota_yaz(sayac)


def freepik_kota_durum() -> list:
    """[(anahtar_etiketi, kullanilan, tavan)] — arayuz/log icin."""
    sayac = _fp_kota_oku()
    return [(_fp_etiket(a)[:6], sayac.get(_fp_etiket(a), 0), FP_GUNLUK_TAVAN)
            for a in FREEPIK_KEYS]
PEXELS_KEY = os.environ.get("PEXELS_KEY", "")
PIXABAY_KEY = os.environ.get("PIXABAY_KEY", "")
# 5 Agu 2026: api.magnific.com OLDU. Magnific, Freepik'e katildi ve API tek cati altinda
# toplandi. Eski adres 502 + Ispanyolca HTML hata sayfasi donuyordu — yani upscale HIC
# calismiyordu ve videolarda hicbir gorsel buyutulmemis. Dogru adres api.freepik.com;
# oradan gelen yanit yapilandirilmis JSON ("Error consuming credits" = kredi yok).
MAG_BASE = os.environ.get("MAG_BASE", "https://api.freepik.com/v1/ai/image-upscaler")
_MAG_KAPALI = False   # 402/401 gorulunce oturum boyunca kapat (bosa cagri yok)
_MAG_5XX = 0          # ust uste 5xx sayaci: servis coktuyse (or. 502) her sahnede bosuna deneme

# YouTube veri-merkezi IP'lerinden "Sign in to confirm you're not a bot" verir.
# Cozum: tarayicidan disa aktarilan Netscape cookies dosyasi (varsa) kullanilir.
YT_COOKIES = os.environ.get("YT_COOKIES_FILE", "/opt/vidrush/webapp/veri/yt_cookies.txt")


def _yt_cookie_opts(opts: dict) -> dict:
    if YT_COOKIES and os.path.exists(YT_COOKIES):
        opts["cookiefile"] = YT_COOKIES
    return opts


# ─────────────────────────── YouTube (yt-dlp) ───────────────────────────

# YouTube arama filtresi: "Creative Commons lisansi" (yeniden kullanima izinli).
# Bu, arama URL'sindeki sp= parametresinin CC degeri. Filtresiz arama STANDART
# YouTube lisansli videolari da getirir; onlari videoya koymak telif talebi/ihtar
# demektir — yani dogrudan para kaybi ve kanal riski. Bu yuzden footage aramasi
# VARSAYILAN OLARAK sadece CC arar.
YT_CC_FILTRE = "EgIwAQ%3D%3D"


def _lisans_cc_mi(url: str) -> bool:
    """Videonun lisansini TEK TEK dogrular. Arama filtresi bazen sizdirir; indirmeden
    once bunu kontrol etmek tek guvenli yol."""
    import yt_dlp
    # player_client=android_vr ZORUNLU. Duz istemci YouTube bot kontrolune takilip
    # "Requested format is not available" veriyor; o zaman lisans okunamiyor ve guvenli
    # taraf secildigi icin HER aday atlaniyordu — yani footage hic inmiyordu.
    opts = _yt_cookie_opts({"quiet": True, "skip_download": True, "no_warnings": True,
                            "noplaylist": True, "socket_timeout": 25, "retries": 1,
                            "extractor_args": {"youtube": {"player_client": ["android_vr"]}}})
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            b = ydl.extract_info(url, download=False) or {}
    except Exception as e:
        print(f"  lisans okunamadi ({str(e)[:80]}) -> guvenli tarafta kal, atla", file=sys.stderr)
        return False
    lis = str(b.get("license") or "")
    return "creative commons" in lis.lower()


def youtube_ara(sorgu: str, adet: int = 6, sadece_cc: bool = True):
    """yt-dlp ile YouTube araması. [{baslik,url,sure,kanal}] döner.
    sadece_cc=True (varsayilan): yalnizca Creative Commons lisansli sonuclar."""
    import yt_dlp
    opts = _yt_cookie_opts({"quiet": True, "skip_download": True, "extract_flat": True,
                            "noplaylist": True, "no_warnings": True,
                            "socket_timeout": 30, "retries": 1,    # hang koruması
                            "extractor_args": {"youtube": {"player_client": ["android_vr"]}}})
    if sadece_cc:
        hedef = ("https://www.youtube.com/results?search_query="
                 + requests.utils.quote(sorgu) + "&sp=" + YT_CC_FILTRE)
    else:
        hedef = f"ytsearch{adet}:{sorgu}"
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            r = ydl.extract_info(hedef, download=False)
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
    return [o for o in out if o["url"]][:adet]


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
        # player_client=android_vr: YouTube bot kontrolunu cookie OLMADAN geciyor.
        # 5 Agu 2026'da olculdu: duz istemci "Requested format is not available" veriyor,
        # android_vr ayni videoyu sorunsuz indiriyor. Cookie hala destekleniyor (varsa
        # eklenir) ama artik SART DEGIL.
        "extractor_args": {"youtube": {"player_client": ["android_vr"]}},
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


def youtube_sahne(sorgu: str, hedef: str, maks_sure: int = 25,
                  lisans_dogrula: bool = True) -> bool:
    """Sorgudan ilk uygun videoyu bul ve indir. Basarili ise True.
    lisans_dogrula=True: indirmeden ONCE lisans tek tek kontrol edilir; CC olmayan
    aday atlanir (telif talebi = para kaybi, o yuzden varsayilan acik)."""
    for aday in youtube_ara(sorgu, adet=6):
        s = aday.get("sure")
        if s and s > 3600:      # 1 saatten uzun canli/podcast'leri atla
            continue
        if lisans_dogrula and not _lisans_cc_mi(aday["url"]):
            print(f"  CC degil, atlandi: {aday['baslik'][:60]}", file=sys.stderr)
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

def _fp_kota_hatasi_mi(r) -> bool:
    """Saglayici gunluk indirme tavanini soyluyor mu? 429 ya da govdede limit ifadesi."""
    if r.status_code == 429:
        return True
    g = (r.text or "").lower()
    return any(k in g for k in ("daily", "limit", "quota", "exceeded"))


def freepik_video(sorgu: str, hedef: str) -> bool:
    """Freepik stok videosu indir. COKLU ANAHTAR: kotasi dolan anahtardan sonrakine gecer.
    Kota takibi disktedir (gunluk), yani konteyner yeniden baslasa da kayip olmaz."""
    denenen = set()
    while True:
        anahtar = freepik_anahtar_sec()
        if not anahtar or anahtar in denenen:
            if not anahtar:
                print("  freepik: TUM anahtarlarin gunluk kotasi dolu", file=sys.stderr)
            return False
        denenen.add(anahtar)
        h = {"x-freepik-api-key": anahtar, "Accept": "application/json"}
        try:
            r = requests.get("https://api.freepik.com/v1/videos", headers=h,
                             params={"term": sorgu, "per_page": 8}, timeout=30)
            if r.status_code in (401, 402, 403):
                # Bu anahtar yetkisiz/kredisiz: bugun bir daha denemeyelim, sonrakine gec
                print(f"  freepik anahtar {_fp_etiket(anahtar)[:6]} yetkisiz "
                      f"({r.status_code}) -> sonraki anahtar", file=sys.stderr)
                freepik_anahtar_doldu(anahtar)
                continue
            if _fp_kota_hatasi_mi(r):
                freepik_anahtar_doldu(anahtar)
                continue
            r.raise_for_status()
            for item in (r.json().get("data") or []):
                vid = item.get("id")
                if not vid:
                    continue
                dr = requests.get(f"https://api.freepik.com/v1/videos/{vid}/download",
                                  headers=h, timeout=30)
                if _fp_kota_hatasi_mi(dr):
                    freepik_anahtar_doldu(anahtar)
                    break          # bu anahtar bitti -> while donsun, sonrakini alsin
                if dr.status_code in (402, 403):
                    freepik_anahtar_doldu(anahtar)
                    break
                if dr.status_code >= 400:
                    continue
                url = (dr.json().get("data") or {}).get("url")
                if url and _indir_ve_hazirla(url, hedef):
                    freepik_sayac_artir(anahtar)   # SADECE basarili indirme kota yer
                    return True
            else:
                return False       # aramada sonuc vardi ama hicbiri inmedi: anahtar sorunu degil
        except Exception as e:
            print(f"  freepik hata ({_fp_etiket(anahtar)[:6]}): {str(e)[:120]}", file=sys.stderr)
            return False


def footage_getir(sorgu: str, hedef: str, yt_once: bool = True) -> bool:
    """Sahne footage'i getir. Oncelik GERCEK+UCRETSIZ stok video:
       Pexels -> Pixabay -> Freepik(kredi varsa) -> YouTube(cookie varsa).
    Her katman kendi timeout'una sahip; biri patlarsa digerine gecer; hicbiri yoksa
    False -> caller AI gorsele duser."""
    kaynaklar = [pexels_video, pixabay_video, freepik_video]
    if yt_once:
        # 5 Agu 2026: eskiden bu satir "YT_COOKIES varsa" diye kosulluydu. Cookie dosyasi
        # olmayan sunucuda YouTube HIC denenmiyordu; Pexels/Pixabay anahtari da bos olunca
        # footage zinciri komple bosa duser, her sahne AI gorsele kacardi. Seyahat belgeseli
        # gibi %92 footage'li bir stil bu haliyle calismaz. android_vr istemcisi cookie
        # gerektirmedigi icin kosul kaldirildi.
        kaynaklar.append(youtube_sahne)   # en sona: ucretsiz stok once denenir
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
    global _MAG_KAPALI, _MAG_5XX
    if _MAG_KAPALI or not FREEPIK_KEYS or not os.path.exists(gorsel_yolu):
        return False
    # Buyutme KREDI harcar (stok indirme gibi bedava degil), o yuzden gunluk indirme
    # sayacina bakmadan sirayla ilk anahtari kullanir; kredisiz olan 402/403 verir ve
    # cagiran zinciri kapatir.
    anahtar = freepik_anahtar_sec() or FREEPIK_KEYS[0]
    try:
        with open(gorsel_yolu, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        h = {"x-freepik-api-key": anahtar}   # Freepik cati anahtari (eski: x-magnific-*)
        body = {"image": b64, "scale_factor": scale,
                "optimized_for": optimized_for, "engine": "automatic"}
        r = requests.post(MAG_BASE, headers=h, json=body, timeout=90)
        if r.status_code >= 400:
            print(f"  magnific POST {r.status_code}: {r.text[:160]}", file=sys.stderr)
            if r.status_code in (401, 402, 403):
                _MAG_KAPALI = True   # kredi/yetki bitti -> bu is boyunca bir daha deneme
            elif r.status_code >= 500 and "consuming credits" in (r.text or "").lower():
                # Freepik kredi bitince 502 + "Error consuming credits" donuyor. Bu KALICI
                # bir durum; gecici 5xx gibi 3 kez denemek her sahnede bosa cagri demek.
                print("  magnific: kredi yok (Freepik) -> bu is boyunca devre disi",
                      file=sys.stderr)
                _MAG_KAPALI = True
            elif r.status_code >= 500:
                _MAG_5XX += 1        # servis tarafi coktu (or. 502 Bad Gateway)
                if _MAG_5XX >= 3:    # ust uste 3 kez -> bu is boyunca kapat, sahne basina bosa deneme olmasin
                    print("  magnific: ust uste 5xx, bu is boyunca devre disi", file=sys.stderr)
                    _MAG_KAPALI = True
            return False
        _MAG_5XX = 0
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
