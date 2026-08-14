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

import medya_kapisi   # Faz H: biyom/donem celiski kapisi (bkz. modul basligi)

# Faz I-1: kare tabanli yer/donem/biyom kapisi. Import basarisiz olursa hat
# CALISMAYA DEVAM EDER — kapi yoksa eski davranis gecerlidir (sessiz cokme yok).
try:
    from medya import kare_kapisi as _kare_kapisi
except Exception as _e:                                    # pragma: no cover
    _kare_kapisi = None
    print(f"  kare kapisi yuklenemedi ({str(_e)[:60]}) — eski akis", file=sys.stderr)

# ── ANAHTAR OKUMA: ortam degiskeni VEYA dosya ──
# Neden dosya secenegi: mevcut anahtarlar konteynerin Config.Env'ine gomulu. Yeni bir
# ortam degiskeni eklemek konteyneri YENIDEN YARATMAYI gerektirir; bu, uzerinde calisan
# isi oldurur ve imaja islenmis durumu riske atar. Dosyadan okumak ise deploy'un
# docker commit'i sayesinde kalici olur ve yeniden baslatmaya dayanir.
#   Ekleme:  docker exec bedosaho sh -c 'echo ANAHTAR > /opt/vidrush/webapp/veri/coverr_key.txt'
KOK_YOL = os.environ.get("VIDRUSH_KOK", "/opt/vidrush")
ANAHTAR_DIZIN = os.environ.get("ANAHTAR_DIZIN",
                               os.path.join(KOK_YOL, "webapp", "veri"))


def _anahtar_oku(env_ad: str, dosya_ad: str) -> str:
    """Once ortam degiskeni, yoksa veri/<dosya_ad>. Ikisi de yoksa bos."""
    d = os.environ.get(env_ad, "").strip()
    if d:
        return d
    try:
        with open(os.path.join(ANAHTAR_DIZIN, dosya_ad)) as f:
            return f.read().strip()
    except Exception:
        return ""


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
FP_KOTA_DOSYA = os.environ.get(
    "FREEPIK_KOTA_DOSYA", os.path.join(ANAHTAR_DIZIN, "freepik_kota.json"))
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
PEXELS_KEY = _anahtar_oku("PEXELS_KEY", "pexels_key.txt")
COVERR_KEY = _anahtar_oku("COVERR_KEY", "coverr_key.txt")
PIXABAY_KEY = _anahtar_oku("PIXABAY_KEY", "pixabay_key.txt")
# 5 Agu 2026: api.magnific.com OLDU. Magnific, Freepik'e katildi ve API tek cati altinda
# toplandi. Eski adres 502 + Ispanyolca HTML hata sayfasi donuyordu — yani upscale HIC
# calismiyordu ve videolarda hicbir gorsel buyutulmemis. Dogru adres api.freepik.com;
# oradan gelen yanit yapilandirilmis JSON ("Error consuming credits" = kredi yok).
MAG_BASE = os.environ.get("MAG_BASE", "https://api.freepik.com/v1/ai/image-upscaler")
_MAG_KAPALI = False   # 402/401 gorulunce oturum boyunca kapat (bosa cagri yok)
_MAG_5XX = 0          # ust uste 5xx sayaci: servis coktuyse (or. 502) her sahnede bosuna deneme

# YouTube veri-merkezi IP'lerinden "Sign in to confirm you're not a bot" verir.
# Cozum: tarayicidan disa aktarilan Netscape cookies dosyasi (varsa) kullanilir.
YT_COOKIES = os.environ.get("YT_COOKIES_FILE",
                            os.path.join(ANAHTAR_DIZIN, "yt_cookies.txt"))


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


# ── YOUTUBE ADAY FILTRESI (7 Agu 2026, canli videoda REKLAM cikti) ──
# Teslim edilen 37 sn'lik belgeselin son 5 saniyesi bir MOBIL OYUN REKLAMI oldu
# ("HardCore Realm" oyun arayuzu + "Everything you need to know about" yazisi).
# Sebep: oyun/uygulama tanitim videolari cogu zaman CC lisansli ve genel sorgularla
# eslesiyor; ustune biz videonun BASINDAN indiriyoruz ve baslarda tam da tanitim/logo/
# arayuz kismi oluyor. Monetize kanalda bu hem utanc hem politika riski.
_YT_YASAK_KELIME = {
    # oyun / uygulama tanitimi
    "gameplay", "game", "gaming", "roblox", "minecraft", "fortnite", "mod", "modded",
    "update", "patch", "server", "server", "noob", "pro", "hack", "cheat", "glitch",
    "tycoon", "simulator", "codes", "code", "script", "afk", "grind", "loadout",
    # tanitim / cagri
    "trailer", "teaser", "subscribe", "giveaway", "promo", "advert", "advertisement",
    "sponsored", "download", "install", "app", "review", "unboxing", "tutorial",
    "how to get", "click", "link in", "discount", "coupon", "sale",
    # ekran kaydi
    "screen recording", "screencast", "walkthrough", "lets play", "let's play",
    "stream", "livestream", "vod", "reaction",
}


def _yt_aday_uygun(aday: dict, sorgu: str) -> bool:
    """Adayin BASLIGI reklam/oyun/ekran-kaydi isaretleri tasiyor mu, ve sorguyla
    alakali mi? Coverr'daki mantigin aynisi: alakasiz klip, klipsizlikten kotudur."""
    baslik = str(aday.get("baslik") or "").lower()
    if not baslik:
        return False
    for y in _YT_YASAK_KELIME:
        if y in baslik:
            print(f"  YT atlandi (reklam/oyun isareti '{y}'): {baslik[:56]}", file=sys.stderr)
            return False
    # Alaka: sorgunun KONU kelimelerinden en az biri baslikta olmali
    konu = [k.lower() for k in sorgu.replace(",", " ").split()
            if len(k) > 3 and k.lower() not in _COVERR_KAMERA_KELIME]
    if konu and not any(k in baslik or k.rstrip("s") in baslik for k in konu):
        print(f"  YT atlandi (sorguyla alakasiz): {baslik[:56]}", file=sys.stderr)
        return False
    # YER KAPISI — stok kaynaklarla ayni kural (11 Agu 2026). Bu olmadan Japonya
    # metnine Avrupa CC klibi girebiliyordu; kapiyi sadece Pexels'e koymak yetmez.
    bilgi = {"title": baslik, "description": ""}
    if not _kapi_gecti_mi(bilgi, sorgu, "youtube"):
        return False                       # biyom/donem celiskisi (Faz H)
    yer = _etkin_yer(sorgu)
    if yer and not (_yer_dogru_mu(bilgi, yer) or _notr_cekim_mi(bilgi)):
        print(f"  YT atlandi (yanlis ulke riski): {baslik[:56]}", file=sys.stderr)
        return False
    return True


def youtube_sahne(sorgu: str, hedef: str, maks_sure: int = 25,
                  lisans_dogrula: bool = True) -> bool:
    """Sorgudan ilk uygun videoyu bul ve indir. Basarili ise True.
    lisans_dogrula=True: indirmeden ONCE lisans tek tek kontrol edilir; CC olmayan
    aday atlanir (telif talebi = para kaybi, o yuzden varsayilan acik)."""
    for aday in youtube_ara(sorgu, adet=6):
        s = aday.get("sure")
        if s and s > 3600:      # 1 saatten uzun canli/podcast'leri atla
            continue
        if not _yt_aday_uygun(aday, sorgu):
            continue
        if lisans_dogrula and not _lisans_cc_mi(aday["url"]):
            print(f"  CC degil, atlandi: {aday['baslik'][:60]}", file=sys.stderr)
            continue
        if youtube_indir(aday["url"], hedef, maks_sure=maks_sure):
            atif_kaydet(hedef, kanal=aday.get("kanal") or "", baslik=aday.get("baslik") or "",
                        url=aday.get("url") or "", lisans="CC BY")
            return True
    return False


def atif_kaydet(hedef: str, kanal: str, baslik: str = "", url: str = "", lisans: str = ""):
    with _KULLANILAN_KILIT:
        _ATIFLAR[os.path.abspath(hedef)] = {"kanal": kanal, "baslik": baslik,
                                            "url": url, "lisans": lisans}


def atif_al(hedef: str) -> dict:
    with _KULLANILAN_KILIT:
        return dict(_ATIFLAR.get(os.path.abspath(hedef)) or {})


def atif_listesi() -> list:
    """Videoda kullanilan tum CC kaynaklari — YouTube aciklamasina konur.
    Lisans metni atfi ACIKLAMADA istiyor; ekrandaki kucuk yazi ek nezaket."""
    with _KULLANILAN_KILIT:
        gorulen, out = set(), []
        for v in _ATIFLAR.values():
            anahtar = (v.get("kanal"), v.get("url"))
            if anahtar in gorulen:
                continue
            gorulen.add(anahtar)
            out.append(dict(v))
        return out


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


def _indir_ve_hazirla(url: str, hedef: str, zaman_asimi: int = 120) -> bool:
    ham = hedef + ".ham"
    if not _stok_indir(url, ham, zaman_asimi):
        try: os.remove(ham)
        except Exception: pass
        return False
    return _remotion_uygun_yap(ham, hedef)


# BU VIDEODA kullanilan klip kimlikleri. _sahne_medya PARALEL THREAD'lerde kostugu icin
# kilitli. Is basinda klip_gecmisi_sifirla() ile temizlenir; is icinde ASLA temizlenmez
# (temizlense paralel thread'ler birbirinin kaydini siler ve tekrar geri gelir).
import threading as _th
_KULLANILAN = set()
_KULLANILAN_KILIT = _th.Lock()
# Tekrar izni THREAD-YEREL: _sahne_medya paralel kosuyor. Modul geneli olsa bir
# sahnenin son-care izni digerlerinin tekrar yasagini da kaldirirdi ve sessizce
# tekrar eden klipler girerdi.
_YEREL = _th.local()


def _tekrara_izin_var():
    return bool(getattr(_YEREL, "tekrar", False))


# ATIF DEFTERI. Creative Commons (CC BY) klip kullanmak ATIF ZORUNLULUGU getirir:
# kaynak belirtilmeden kullanmak lisansi ihlal eder. Bu defter hem ekrana basilacak
# kucuk yaziyi hem YouTube aciklamasina konacak listeyi besler.
# DIKKAT: atif TELIF IZNI DEGILDIR. Telifli bir videoya kaynak yazmak onu kullanilabilir
# yapmaz — Content ID yine talep acar. Bu yuzden youtube_sahne CC disina CIKMAZ.
_ATIFLAR = {}                # {hedef_dosya_yolu: {"kanal":..,"baslik":..,"url":..,"lisans":..}}

# ⚠ FAZ R-1d-b — STOK PROVENANSI.
# OLCULEN KUSUR: `_ATIFLAR` YALNIZCA YouTube/CC yolunda doluyordu; Pexels /
# Pixabay / Coverr / Freepik kabul noktalarinda HICBIR kayit tutulmuyordu.
# Bu yuzden gercek medya yolu (`footage_getir`) ile calisan bir isin
# saglayici / asset / lisans / olcu bilgisi HICBIR YERDE yoktu ve
# `medya_kopru.manifest_kur()` bu sahneleri GORMUYORDU -> PRE-QA hic
# kosmuyordu (R-1d-a staging olcumu: `edit_plani=MEDYA-YOK`).
# ⚠ Bu kayit ATIF DEGILDIR: `atif_listesi()` semantigi (ekran kunyesi +
# aciklama atfi) DEGISMEDI. Burasi yalnizca PROVENANS/QA icin.
_STOK_PROVENANS = {}         # {hedef_dosya_yolu: {...}}

# Stok saglayicilarin lisans KIMLIKLERI. ⚠ Lisans METNI burada YORUMLANMAZ;
# yalnizca hangi lisans altinda alindigi KAYDEDILIR.
STOK_LISANSLARI = {
    "pexels": "pexels-license",
    "pixabay": "pixabay-content-license",
    "coverr": "coverr-license",
    "freepik": "freepik-license",
}


def stok_provenans_kaydet(hedef: str, *, saglayici: str, asset_id: str,
                          url: str = "", baslik: str = "", sorgu: str = "",
                          genislik: int = 0, yukseklik: int = 0,
                          sure_sn: float = 0.0,
                          kare_dogrulandi: bool = False) -> None:
    """Kabul edilmis stok klibin GERCEK provenansini kaydet.

    ⚠ YALNIZCA kare kapisindan GECMIS klip icin cagrilir; `kare_dogrulandi`
    bayragi UYDURULMAZ, cagiran taraf gercekten dogruladiysa True verir.
    """
    with _KULLANILAN_KILIT:
        _STOK_PROVENANS[os.path.abspath(hedef)] = {
            "saglayici": str(saglayici or ""),
            "asset_id": str(asset_id or ""),
            "orijinal_url": str(url or ""),
            "baslik": str(baslik or "")[:120],
            "sorgu": str(sorgu or "")[:120],
            "lisans": STOK_LISANSLARI.get(str(saglayici or ""), ""),
            "genislik": int(genislik or 0),
            "yukseklik": int(yukseklik or 0),
            "sure_sn": float(sure_sn or 0.0),
            "kare_dogrulandi": bool(kare_dogrulandi),
            "medya_turu": "video",
        }


def stok_provenans_isaretle(hedef: str, *, medya_turu: str = "",
                            lisans: str = "", model: str = "") -> None:
    """Var olan provenans kaydinin TURUNU/LISANSINI duzelt (R-1d-d).

    ⚠ URETILEN gorseller stok DEGILDIR: `STOK_LISANSLARI`nda karsiligi yok
    ve `medya_turu` "video" OLAMAZ. Bu yardimci o iki alani ACIKCA yazar;
    kayit yoksa HICBIR SEY yapmaz (bostan kayit URETMEZ).
    """
    with _KULLANILAN_KILIT:
        k = _STOK_PROVENANS.get(os.path.abspath(hedef))
        if not k:
            return
        if medya_turu:
            k["medya_turu"] = str(medya_turu)
        if lisans:
            k["lisans"] = str(lisans)
        if model:
            k["model"] = str(model)


def stok_provenans_al(hedef: str) -> dict:
    """Kayit yoksa BOS doner — cagiran taraf 'lisansli' VARSAYMAZ."""
    with _KULLANILAN_KILIT:
        return dict(_STOK_PROVENANS.get(os.path.abspath(hedef)) or {})


def klip_gecmisi_sifirla():
    """Yeni is baslarken cagrilir — onceki videonun klip gecmisi tasinmasin."""
    global _YER_BAGLAM
    _YER_BAGLAM = []
    _vision_sayac[0] = 0
    _vision_onbellek.clear()
    with _KULLANILAN_KILIT:
        _KULLANILAN.clear()
        _ATIFLAR.clear()
        _STOK_PROVENANS.clear()
    # Faz H: biyom kapisinin is-basina durumu da sifirlanir
    _KAPI_REDLERI.clear()
    # Faz I-1: kare kapisinin butcesi/onbellegi de is basina sifirlanir.
    # ⚠ Sifirlanmazsa onceki isin USD/cagri harcamasi tasinir ve yeni is
    # daha ilk klipte "butce doldu" der (kapi sessizce devre disi kalir).
    kare_butce_kur()


# ⚠ FAZ H: tum videonun konu metni. Biyom kapisi, sahne sorgusu biyom
# vermediginde buraya duser. Shackleton pilotunda kok neden tam buydu:
# yer kapisi YER_TAKMA_AD'daki 19 ulkeye bagli, "South Georgia" tabloda YOK
# -> hicbir kapi calismadi -> tropik sahil klibi "GUNEY GEORGIA" diye gecti.
_VIDEO_BAGLAM_METNI = ""
# Kapinin reddettigi adaylar — ise `dususler` olarak yazilir (sessiz dusus yok)
_KAPI_REDLERI = []
_KAPI_KILIT = _th.Lock()


def video_baglami_kur(metin: str) -> None:
    """Is basinda cagrilir: biyom kapisinin dusecegi genel konu metni."""
    global _VIDEO_BAGLAM_METNI
    _VIDEO_BAGLAM_METNI = str(metin or "")[:4000]
    _KAPI_REDLERI.clear()


def kapi_redleri() -> list:
    """Bu iste kapinin reddettigi adaylar (gerekceleriyle)."""
    with _KAPI_KILIT:
        return list(_KAPI_REDLERI)


def _kapi_gecti_mi(bilgi: dict, sorgu: str, saglayici: str = "") -> bool:
    """BIYOM/DONEM KAPISI — ulke tablosundan BAGIMSIZ calisir.

    `_yer_dogru_mu` yalnizca YER_TAKMA_AD'daki 19 ulkeyi bilir; tablonun
    disindaki her yer icin kapi YOKTU. Bu kapi iklim kusagi celiskisine
    bakar, dolayisyla tablodan bagimsizdir.
    """
    aday_metni = f"{bilgi.get('title') or ''} {bilgi.get('description') or ''}"
    ok, gerekce = medya_kapisi.kapi(sorgu, aday_metni, _VIDEO_BAGLAM_METNI)
    if not ok:
        print(f"  KAPI RED [{saglayici}] {aday_metni[:52]!r}: {gerekce}",
              file=sys.stderr)
        with _KAPI_KILIT:
            if len(_KAPI_REDLERI) < 50:
                _KAPI_REDLERI.append({"saglayici": saglayici,
                                      "sorgu": sorgu[:90],
                                      "aday": aday_metni[:110],
                                      "gerekce": gerekce})
    return ok
    _vision_sayac[0] = 0
    _vision_onbellek.clear()
    with _KULLANILAN_KILIT:
        _KULLANILAN.clear()
        _ATIFLAR.clear()
        _STOK_PROVENANS.clear()


def _klip_kullanildi_mi(kimlik: str) -> bool:
    with _KULLANILAN_KILIT:
        return str(kimlik) in _KULLANILAN


def _klip_isaretle(kimlik: str):
    with _KULLANILAN_KILIT:
        _KULLANILAN.add(str(kimlik))


FOOTAGE_MAKS_GEN = 2560     # kaynak genislik tavani
FOOTAGE_MAKS_SN = 12        # kaynak sure tavani (sahne tavani 8 sn + pay)


def _remotion_uygun_yap(ham_yol: str, hedef: str) -> bool:
    """Ham stok mp4'u Remotion'un headless Chrome'unun KESIN cozebilecegi bicime getir,
    ve AYNI ADIMDA kirp + olcekle.

    NEDEN KIRPMA/OLCEKLEME (11 Agu 2026 olcumu): Pexels 4K'ya gecince tek klip
    558 MB geldi. Sahne basina ortalama 125 MB x ~330 sahne = 41 GB — 10 Agu'da
    diski doldurup bir render'i oldurdugum tabloya geri donerdik. Ustelik sahne
    5-8 sn kullaniyor, klibin geri kalan 50 saniyesi indirilip cozuluyor ve
    ATILIYOR.

    NEDEN 2560 KAYIP DEGIL: cikti 1920x1080 ve Ken Burns zoom tavani 1.38 —
    yani en yakin karede bile 1920x1.38 = 2650 pikselin altinda ornekleme
    gerekmiyor; 2560 kaynak 1080p ciktida gozle ayirt edilemez. Alt tarafi
    4K'nin decode maliyeti 2.25 kat ve render'i yavaslatiyor.
    ONEMLI: 4K'yi Pexels'ten ISTEMEYE devam ediyoruz — kotu 1080p kaynagi
    buyutmek ile iyi 4K kaynagi kucultmek ayni sey degil, ikincisi keskin.
    """
    import subprocess
    codec = ""; piks = ""; gen = 0; sure = 0.0
    try:
        p = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=codec_name,pix_fmt,width",
             "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", ham_yol],
            capture_output=True, timeout=30)
        alan = p.stdout.decode(errors="ignore").split()
        for a in alan:
            if a in ("h264", "hevc", "vp9", "av1", "mpeg4"):
                codec = a
            elif a.startswith("yuv") or a.startswith("gbr"):
                piks = a
            elif a.isdigit() and int(a) > 200:
                gen = max(gen, int(a))
            else:
                try:
                    sure = max(sure, float(a))
                except Exception:
                    pass
    except Exception:
        pass

    kucult = gen > FOOTAGE_MAKS_GEN
    kirp = sure > FOOTAGE_MAKS_SN + 1
    uygun = (codec == "h264" and piks == "yuv420p" and not kucult)

    def _re_encode():
        k = ["ffmpeg", "-nostdin", "-y", "-i", ham_yol]
        if kirp:
            k += ["-t", str(FOOTAGE_MAKS_SN)]
        if kucult:
            k += ["-vf", f"scale={FOOTAGE_MAKS_GEN}:-2:flags=lanczos"]
        k += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
              "-pix_fmt", "yuv420p", "-an", "-movflags", "+faststart", hedef]
        return subprocess.run(k, capture_output=True, timeout=600)

    try:
        if uygun:
            k = ["ffmpeg", "-nostdin", "-y", "-i", ham_yol]
            if kirp:
                k += ["-t", str(FOOTAGE_MAKS_SN)]
            k += ["-c", "copy", "-an", "-movflags", "+faststart", hedef]
            r = subprocess.run(k, capture_output=True, timeout=300)
            if r.returncode != 0:
                r = _re_encode()
        else:
            r = _re_encode()
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



# ─────────────────────────── Pexels (ucretsiz stok) ───────────────────────────

def _yer_ekli_sorgu(sorgu: str) -> str:
    """Sorguda yer kelimesi yoksa VIDEONUN ulkesini basa ekle. Kapi zaten reddedecek;
    sorguyu da duzeltmek bosa arama yapmayi onler ve dogru klibi bulma sansini artirir."""
    if not _YER_BAGLAM or _sorgu_yer_terimleri(sorgu):
        return sorgu
    takma = YER_TAKMA_AD.get(_YER_BAGLAM[0], [])
    return f"{takma[0]} {sorgu}" if takma else sorgu


def _yer_yedek_sorgular(sorgu: str) -> list:
    """Sorgu stokta KARSILIGI OLMAYAN bir cekim istiyorsa, ULKEYI KORUYARAK genellestir.

    Vidrush'in AI Prompt Checker'i ayni sorunu uretimden once yakaliyor ve kullaniciya
    "kesin cekimi degil, konuyu tarif et" diyor. Bizde kullaniciya sormak yerine kod
    genellestiriyor. Ornek (11 Agu'da videoyu bozan sorgu):
      "Japanese apartment electric meter and light switch"  -> stokta YOK
      yedekler: "japan apartment", "tokyo apartment", "tokyo street", "japan city"
    Boylece klip Japonya'da kalir; alternatif (eski davranis) Avrupa sigorta kutusuydu.
    """
    yerler = _etkin_yer(sorgu)
    if not yerler:
        return []
    takma = YER_TAKMA_AD.get(yerler[0], [])
    if not takma:
        return []
    ulke = takma[0]
    sehir = takma[2] if len(takma) > 2 else ulke
    konu = [k.lower() for k in sorgu.replace(",", " ").split()
            if len(k) > 3 and k.lower() not in _COVERR_KAMERA_KELIME
            and k.lower() not in _YER_KELIME_HARITA]
    yedek = []
    for kel in konu[:2]:
        yedek += [f"{ulke} {kel}", f"{sehir} {kel}"]
    yedek += [f"{sehir} street", f"{ulke} city", f"{ulke} daily life"]
    gorulen, temiz = set(), []
    for y in yedek:
        if y not in gorulen:
            gorulen.add(y)
            temiz.append(y)
    return temiz


def _coverr_sorgular(sorgu: str):
    """Coverr'in kutuphanesi kucuk ve anahtar kelimeleri AND'liyor: 7 Agu 2026 olcumu ->
      "aerial drone remote pacific island village" = 0 sonuc
      "aerial drone island village"                = 1
      "island village"                             = 1
      "island"                                     = 132
      "aerial island"                              = 84
    Yani plan'in uzun betimleyici footage_sorgu'sunu oldugu gibi yollamak bos donuyor.
    Cozum: sorguyu kademeli kisalt, sonuc CIKAN ilk varyantta dur."""
    sorgu = _yer_ekli_sorgu(sorgu)
    kel = [k for k in sorgu.replace(",", " ").split() if len(k) > 2]
    # YER KELIMESI ONE ALINIR (11 Agu 2026). Kisaltma sondan kirpiyor; "elderly community
    # meeting Japan" 2 kelimeye inince "elderly community" oluyor ve ulke kayboluyor.
    # Ulke kaybolunca arama Bati sonucu donduruyor, alaka kapisi hepsini reddediyor ve
    # bosa API cagrisi yapiliyor. Yer kelimesi basa alinirsa her varyantta korunur.
    kel.sort(key=lambda x: 0 if x.lower() in _YER_KELIME_HARITA else 1)
    varyant, gorulen = [], set()
    for n in (len(kel), 4, 3, 2):
        if n < 1:
            continue
        v = " ".join(kel[:n]).strip()
        if v and v not in gorulen:
            gorulen.add(v)
            varyant.append(v)
    # TEK KELIMEYE INMIYORUZ (7 Agu 2026, canli iste yakalandi).
    # Eskiden son care olarak en uzun tek kelime deneniyordu ve su oldu:
    #   "boat arriving after six day journey" -> "arriving" -> Coverr "Train arriving"
    # Uzak bir Atlantik adasi belgeselinde TREN goruntusu. Alaka kapisi da gecirdi cunku
    # "arriving" basliкta gercekten vardi — ama kelime konuyu tasimiyor.
    # Iki kelimenin altinda anlam kalmiyor; bulunamazsa Coverr False donsun ve zincir
    # Pexels/Pixabay/YouTube CC'ye dussun. Alakasiz klip, klipsizlikten kotudur.
    return varyant + _yer_yedek_sorgular(sorgu)


# Kamera/genel kelimeler: bunlar KONUYU anlatmiyor, sadece cekimi tarif ediyor.
# Alaka kontrolunde sayilmazlar, yoksa "aerial" kelimesi her hava cekimini "alakali"
# gosterir ve konu tamamen kayar.
_COVERR_KAMERA_KELIME = {
    "aerial", "drone", "close", "closeup", "view", "shot", "footage", "video", "clip",
    "scene", "background", "top", "wide", "slow", "motion", "time", "lapse", "pan",
    "zoom", "shots", "views", "camera", "flying", "flyover", "overhead", "detail",
    # Eylem/genel kelimeler: bunlar da konuyu tasimiyor ve alaka kapisini yaniltiyor
    # ("arriving" -> "Train arriving" gibi).
    "arriving", "leaving", "moving", "walking", "standing", "looking", "waiting",
    "struggling", "working", "going", "coming", "sitting", "holding", "using",
    "after", "before", "during", "through", "around", "between", "toward",
}


# ─────────────── YER DOGRULUGU (11 Agu 2026 — canli iste yakalandi) ───────────────
# Tokyo/kodokushi metniyle uretilen videoda 12 sahnenin 9'u Bati Avrupa cikti:
#   "Japanese apartment electric meter"  -> "person flicking switches" (Avrupa sigorta kutusu)
#   "elderly community meeting Japan"    -> "businessmen in a meeting"
#   "smart home elderly care Japan"      -> "elderly person using a tablet"
# Sebep: alaka kapisi "switch/meeting/tablet" gibi YARDIMCI kelimeyle geciyordu, yani
# metnin en belirleyici kelimesini (ulkeyi) istege bagli sayiyordu.
#
# Ama duz "sorguda Japan varsa klipte de Japan yazsin" kurali da YANLIS: iyi kliplerin
# basliginda ulke adi gecmiyor ("bustling nightlife in shinjuku s kabukicho district"
# tam istedigimiz klip ama icinde "japan" yok). Bu yuzden takma-ad tablosu var.
YER_TAKMA_AD = {
    "japan": ["japan", "japanese", "tokyo", "kyoto", "osaka", "shinjuku", "shibuya",
              "kabukicho", "ginza", "akihabara", "fuji", "nippon", "okinawa", "sapporo",
              "hokkaido", "nara", "kanto", "shinkansen", "torii", "ryokan", "izakaya"],
    "korea": ["korea", "korean", "seoul", "busan", "gangnam", "hanbok", "hangul"],
    "china": ["china", "chinese", "beijing", "shanghai", "shenzhen", "guangzhou",
              "hong kong", "chengdu", "xian"],
    "india": ["india", "indian", "delhi", "mumbai", "kolkata", "bangalore", "varanasi",
              "rajasthan", "kerala"],
    "usa": ["usa", "america", "american", "new york", "manhattan", "brooklyn", "chicago",
            "los angeles", "california", "texas", "washington", "boston", "detroit"],
    "uk": ["uk", "britain", "british", "england", "english", "london", "scotland",
           "wales", "manchester", "liverpool"],
    "france": ["france", "french", "paris", "marseille", "lyon", "eiffel", "provence"],
    "germany": ["germany", "german", "berlin", "munich", "hamburg", "bavaria"],
    "italy": ["italy", "italian", "rome", "milan", "venice", "florence", "naples", "sicily"],
    "spain": ["spain", "spanish", "madrid", "barcelona", "seville", "andalusia"],
    "russia": ["russia", "russian", "moscow", "petersburg", "siberia", "kremlin"],
    "brazil": ["brazil", "brazilian", "rio", "sao paulo", "amazon", "favela"],
    "turkey": ["turkey", "turkish", "istanbul", "ankara", "izmir", "cappadocia", "bosphorus"],
    "egypt": ["egypt", "egyptian", "cairo", "nile", "giza", "pyramid", "luxor"],
    "mexico": ["mexico", "mexican", "cancun", "oaxaca", "yucatan", "aztec", "maya"],
    "thailand": ["thailand", "thai", "bangkok", "phuket", "chiang mai"],
    "vietnam": ["vietnam", "vietnamese", "hanoi", "saigon", "mekong"],
    "africa": ["africa", "african", "kenya", "nigeria", "ethiopia", "sahara", "serengeti"],
    "arab": ["arab", "dubai", "saudi", "emirates", "qatar", "riyadh", "abu dhabi", "bedouin"],
}
# Sorgudaki hangi kelime "yer iddiasi" sayilir: takma-ad tablosundaki HERHANGI bir kelime.
_YER_KELIME_HARITA = {kel: ulke for ulke, kelimeler in YER_TAKMA_AD.items() for kel in kelimeler}

# REKLAM STOGU REDDI: bu kelimeler stok sitesinin "kurumsal tanitim" havuzunu isaret eder.
# Belgesel tonuna asla oturmaz — 11 Agu videosundaki "businessmen in a meeting" ve
# "woman in apron reading letter" tam bu havuzdan geldi.
REKLAM_STOK_KELIME = {
    "businessman", "businessmen", "businesswoman", "corporate", "startup", "teamwork",
    "coworking", "handshake", "mockup", "isolated", "white background", "green screen",
    "studio shot", "model posing", "smiling family", "happy family", "lifestyle",
    "presentation", "brainstorming", "office meeting", "customer service", "influencer",
    "copy space", "advertisement", "commercial", "product shot",
}
# NOTR CEKIM — 11 Agu 2026'da DARALTILDI, cunku ilk surumu videoyu bozdu.
# Ilk listede "water", "sea", "sky", "door", "window", "hallway", "night" gibi
# kelimeler vardi ve bunlari "kulturel iz tasimaz" saymistim. YANLISTI: Tokyo
# metnine turkuaz sulu bir TROPIK ADA havadan cekimi girdi (slug'da "water"
# oldugu icin), Avrupa mutfagi girdi (slug'da "door"), Filipinler mutfagi girdi.
# Genis plan HER ZAMAN yer soyler — mimari, bitki, isik, insan.
# Gercekten kultursuz olan tek sey MAKRO/YAKIN PLAN: bir elin parmagi, cam
# uzerindeki yagmur damlasi, saatin yelkovani her ulkede ayni gorunur.
# Bu yuzden notr kademe artik SADECE yakin plan isareti tasiyan klipleri kabul eder.
NOTR_ZORUNLU_ISARET = {"close up", "closeup", "close-up", "macro", "extreme close"}
NOTR_KONU_KELIME = {
    "hands", "hand", "fingers", "finger", "texture", "detail", "raindrops",
    "droplets", "candle", "flame", "smoke", "steam", "dust", "clock", "keyhole",
    "key", "lock", "paper", "pen", "ink", "fabric", "thread", "grain", "sand",
    "coin", "coins", "switch", "button", "dial", "wire", "screw",
}
# Bu kelimeler ekranda TANIMLANABILIR insan oldugunu gosterir — yer dogrulanmadan kabul
# edilemez, cunku yanlis ulkenin insani en cok goze batan hata.
INSAN_KELIME = {
    "man", "men", "woman", "women", "person", "people", "boy", "girl", "child", "children",
    "family", "couple", "crowd", "group", "worker", "student", "teacher", "doctor", "nurse",
    "elderly", "senior", "guy", "lady", "male", "female", "portrait", "face",
}


# ── VIDEO DUZEYINDE YER BAGLAMI (11 Agu 2026, ucuncu deneme) ──
# Yer kapisini once klip basligina, sonra makro-notr kurala baglayarak sikilastirdim.
# IKISI DE YETMEDI: Tokyo metnine yine turkuaz sulu TROPIK ADA ve Filipinler ic mekani
# girdi. Sebep basit ve benim gozden kacirdigim sey: o sahnelerin SORGUSUNDA hic yer
# kelimesi yoktu ("aerial view of coastal community" gibi), kapi da yer iddiasi
# olmayan sorguda kendini KAPATIYOR.
# Dogru cozum: ulkeyi tek tek sorgudan degil, VIDEONUN METNINDEN bir kez tespit edip
# butun sahnelere zorunlu kilmak. Boylece plan ulkeyi yazmayi unutsa da kapi acik kalir.
_YER_BAGLAM = []


_YER_BAGLAM = []


def yer_baglami_kur(metin: str) -> list:
    """Videonun tamaminin gectigi yer(ler)i metinden tespit et ve is boyunca sabitle."""
    global _YER_BAGLAM
    d = " " + (metin or "").lower().replace(",", " ").replace(".", " ") + " "
    sayim = {}
    for kel, ulke in _YER_KELIME_HARITA.items():
        n = d.count(f" {kel} ")
        if n:
            sayim[ulke] = sayim.get(ulke, 0) + n
    # Tek baskin ulke varsa onu al; ikisi baskinsa ikisini de kabul et (kiyas videolari)
    if not sayim:
        _YER_BAGLAM = []
    else:
        en = max(sayim.values())
        _YER_BAGLAM = [u for u, n in sorted(sayim.items(), key=lambda x: -x[1])
                       if n >= max(2, en * 0.4)][:2]
    print(f"  yer baglami: {_YER_BAGLAM or 'yok'} (sayim: {sayim})", file=sys.stderr)
    return _YER_BAGLAM


# ── VISION DOGRULAMASI (11 Agu 2026, dorduncu ve son katman) ──
# Slug tabanli yer kapisi ucuncu denemede tropik adayi durdurdu ama iki klip yine gecti:
# basliginda "japanese apartment" yazan, iceride BATILI oyuncu olan reklam stogu.
# Bunu metin okuyarak yakalamak IMKANSIZ — yukleyici mekani "japanese" diye etiketlemis.
# Tek dogru yol KAREYE BAKMAK. Klip indikten sonra ortasindan bir kare cikarilip
# gpt-4.1-mini vision'a soruluyor. Maliyet ~$0.0008/klip; 30 dk videoda ~330 klip
# icin ~$0.26 — yanlis ulke klibinin bedeli bundan cok daha yuksek.
VISION_DOGRULA = os.environ.get("VISION_DOGRULA", "1") not in ("0", "false", "")
VISION_MAKS = int(os.environ.get("VISION_MAKS", "600"))       # is basina cagri tavani
_vision_sayac = [0]
_vision_onbellek = {}


def _kare_base64(video_yolu: str) -> str:
    """Klibin %40'indan bir kare -> 512px JPEG -> base64."""
    import base64
    import subprocess
    try:
        sure = 0.0
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                            "-of", "csv=p=0", video_yolu], capture_output=True, text=True,
                           timeout=30)
        sure = float((r.stdout or "0").strip() or 0)
    except Exception:
        sure = 0.0
    t = max(0.0, sure * 0.4)
    gec = video_yolu + ".kare.jpg"
    try:
        import subprocess as sp
        sp.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-ss", f"{t:.2f}",
                "-i", video_yolu, "-frames:v", "1", "-vf", "scale=512:-2", "-q:v", "4",
                gec], capture_output=True, timeout=60)
        with open(gec, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return ""
    finally:
        try:
            os.remove(gec)
        except Exception:
            pass


def _vision_yer_uygun(video_yolu: str, sorgu: str, yerler: list, kimlik: str = "") -> bool:
    """Klip GERCEKTEN o ulkede mi cekilmis gorunuyor? Kareye bakarak karar verir.
    Anahtar yoksa / cagri basarisizsa True doner (kapiyi kapatmaz, sadece ek suzgec)."""
    if not (VISION_DOGRULA and yerler):
        return True
    if _vision_sayac[0] >= VISION_MAKS:
        return True
    if kimlik and kimlik in _vision_onbellek:
        return _vision_onbellek[kimlik]
    anahtar = _anahtar_oku("OPENAI_KEY", "openai_key.txt")
    if not anahtar:
        return True
    b64 = _kare_base64(video_yolu)
    if not b64:
        return True
    ulke = yerler[0]
    takma = YER_TAKMA_AD.get(ulke, [ulke])
    ulke_adi = takma[0].upper()
    sistem = (
        f"You verify stock footage for a documentary set in {ulke_adi}. "
        f"Look at the frame. Decide if it could plausibly have been SHOT IN {ulke_adi}. "
        "Use architecture, signage and script on signs, vehicles, vegetation, interior "
        "style, and the apparent ethnicity of any visible people. "
        f"If people are visible and they clearly do not look like residents of {ulke_adi}, "
        "answer false. If the frame is a tight close-up with no cultural cues at all, "
        "answer true. "
        'Reply ONLY as JSON: {"uygun": true|false, "neden": "<max 12 words>"}')
    try:
        _vision_sayac[0] += 1
        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {anahtar}", "Content-Type": "application/json"},
            json={"model": "gpt-4.1-mini",
                  "messages": [
                      {"role": "system", "content": sistem},
                      {"role": "user", "content": [
                          {"type": "text", "text": f"Scene intent: {sorgu[:120]}"},
                          {"type": "image_url",
                           "image_url": {"url": f"data:image/jpeg;base64,{b64}",
                                         "detail": "low"}}]}],
                  "response_format": {"type": "json_object"},
                  "temperature": 0,
                  "max_tokens": 60},
            timeout=45)
        if r.status_code != 200:
            print(f"  vision {r.status_code}, atlandi", file=sys.stderr)
            return True
        icerik = (r.json().get("choices") or [{}])[0].get("message", {}).get("content") or "{}"
        d = json.loads(icerik)
        uygun = bool(d.get("uygun", True))
        if not uygun:
            print(f"  VISION RED ({ulke}): {str(d.get('neden'))[:50]} "
                  f"[{os.path.basename(video_yolu)}]", file=sys.stderr)
        if kimlik:
            _vision_onbellek[kimlik] = uygun
        return uygun
    except Exception as e:
        print(f"  vision hata: {str(e)[:90]}", file=sys.stderr)
        return True


# ═════════════ FAZ I-1: KARE KAPISI — tablo BAGIMSIZ yer/donem/biyom ═════════════
# ⚠ NEDEN: `_vision_yer_uygun` yalnizca `yerler` DOLUYKEN calisir; `_etkin_yer()`
# ise YER_TAKMA_AD'daki 19 ulkeye bagli. "South Georgia" tabloda YOK -> kare bakan
# katman tam da gerektigi vakada DEVRE DISIYDI (FAZ-H-HANDOFF §13 "Bilinen sinir":
# "small boat South Georgia sea storm" sorgusuna gelen "maltese pilot motorboat").
# Bu kapi bolge/havza tablosuyla calisir; kapsami `kare_kapisi.kapsam_ozeti()`.
KARE_KAPISI = os.environ.get("KARE_KAPISI", "1").lower() not in ("0", "false", "")
KARE_MAKS_CAGRI = int(os.environ.get("KARE_MAKS_CAGRI", "60"))
KARE_MAKS_USD = float(os.environ.get("KARE_MAKS_USD", "0.08"))
KARE_MAKS_SN = float(os.environ.get("KARE_MAKS_SN", "180"))
KARE_ZAMAN_ASIMI = int(os.environ.get("KARE_ZAMAN_ASIMI", "30"))

_kare_butce = [None]           # is basina butce (klip_gecmisi_sifirla ile kurulur)
_kare_onbellek = {}            # klip kimligi -> (ok, kod, gerekce)
_KARE_REDLERI = []
# ⚠ `_sahne_medya` PARALEL thread'lerde kosar (bkz. _KULLANILAN_KILIT gerekcesi).
# Onbellek/red listesi kilitsiz olsaydi hem kayit kaybi hem is-ortasi butce
# sifirlanmasi olurdu.
_KARE_KILIT = _th.Lock()


def kare_butce_kur():
    """Is basinda butceyi sifirla. ⚠ Sinirsiz butce YASAK (Faz H kurali 2)."""
    with _KARE_KILIT:
        if _kare_kapisi is None:
            _kare_butce[0] = None
            return None
        _kare_butce[0] = _kare_kapisi.KareButce(
            maks_cagri=KARE_MAKS_CAGRI, maks_usd=KARE_MAKS_USD, maks_sn=KARE_MAKS_SN)
        _kare_onbellek.clear()
        _KARE_REDLERI.clear()
        return _kare_butce[0]


def kare_ozet() -> dict:
    """Ise yazilacak olculmus ozet — uydurma sayi yok.

    Kapi hic calismadiysa bunu `butce.cagri == 0` ile GORUNUR kilar; "her kare
    dogrulandi" gibi kanitsiz bir iddia URETMEZ.
    """
    with _KARE_KILIT:
        b = _kare_butce[0]
        return {"acik": bool(KARE_KAPISI and _kare_kapisi is not None
                             and VISION_DOGRULA),
                "kapsam": (_kare_kapisi.kapsam_ozeti() if _kare_kapisi else {}),
                "butce": (b.ozet() if b else {}),
                "red_sayisi": len(_KARE_REDLERI),
                "redler": list(_KARE_REDLERI[:20])}


def _kare_gozlem_oku(video_yolu: str) -> dict:
    """Kareyi TEK vision cagrisiyla YAPILI gozleme cevir.

    ⚠ Tek cagri: eski `_vision_yer_uygun` ile birlikte kosulsa klip basina IKI
    vision faturasi cikardi. Bu okuma her ikisinin sordugunu birden dondurur;
    `_kare_dogrula` eski katmani yalnizca bu kapi UYGULANAMADIGINDA cagirir.

    Model kararsizsa `guven` dusuk doner ve `kare_kapisi.karar()` GECIRIR.
    """
    anahtar = _anahtar_oku("OPENAI_KEY", "openai_key.txt")
    if not anahtar:
        raise RuntimeError("OPENAI_KEY yok")
    b64 = _kare_base64(video_yolu)
    if not b64:
        raise RuntimeError("kare cikarilamadi")
    sistem = (
        "You inspect a single frame from stock footage for a documentary. "
        "Report ONLY what the image shows — do not guess from the scene brief. "
        "Name the most likely real-world region using well-known place names "
        "(country, sea, island group). Use architecture, signage script, "
        "vehicles, vegetation, light and terrain. "
        "If the frame is a tight close-up or has no geographic cue at all, set "
        "yakin_plan true and guven low. Be honest about uncertainty: guven is "
        "your confidence 0..1 that your region guess is right. "
        'Reply ONLY as JSON: {"yer_tahmini":"<place names, max 8 words>",'
        '"biyom":"<polar|tropical|desert|temperate|unknown>",'
        '"isaretler":["<cue>","<cue>"],"modern_isaret":["<modern tech seen>"],'
        '"yakin_plan":true|false,"insan":true|false,"guven":0.0}')
    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {anahtar}", "Content-Type": "application/json"},
        json={"model": "gpt-4.1-mini",
              "messages": [
                  {"role": "system", "content": sistem},
                  {"role": "user", "content": [
                      {"type": "image_url",
                       "image_url": {"url": f"data:image/jpeg;base64,{b64}",
                                     "detail": "low"}}]}],
              "response_format": {"type": "json_object"},
              "temperature": 0,
              "max_tokens": 160},
        timeout=KARE_ZAMAN_ASIMI)
    if r.status_code != 200:
        raise RuntimeError(f"vision {r.status_code}")
    icerik = (r.json().get("choices") or [{}])[0].get("message", {}).get("content") or "{}"
    d = json.loads(icerik)
    # Ingilizce biyom adlarini modulun sozluguyle hizala (kare_kapisi biyom_bul
    # zaten metinde arar; burada yalnizca dogrudan kimlik eslemesi yapilir).
    esle = {"polar": "kutup", "tropical": "tropik", "desert": "col",
            "temperate": "iliman", "unknown": ""}
    d["biyom"] = esle.get(str(d.get("biyom") or "").strip().lower(),
                          str(d.get("biyom") or ""))
    return d


def _kare_dogrula(video_yolu: str, sorgu: str, yer_terim: list,
                  kimlik: str = "", saglayici: str = "") -> bool:
    """Indirilmis klibin karesi sahneyle uyumlu mu? Uyumsuzsa False (klip DUSER).

    Sira:
      1) Kare kapisi (tablo bagimsiz). Uygulanabildiyse KARARI O VERIR.
      2) Uygulanamadiysa (beklenti yok / butce / anahtar yok) ve `yer_terim`
         doluysa ESKI `_vision_yer_uygun` katmani calisir — gerileme yok.
    """
    if _kare_kapisi is None or not KARE_KAPISI:
        return _vision_yer_uygun(video_yolu, sorgu, yer_terim, kimlik)
    if not VISION_DOGRULA:
        return True
    with _KARE_KILIT:
        # ⚠ Is ortasinda ASLA yeniden kurma: paralel thread'ler ayni anda
        # gorse butce sifirlanir ve tavan anlamini yitirir.
        butce = _kare_butce[0]
    if butce is None:
        butce = kare_butce_kur()
    ok, kod, gerekce = _kare_kapisi.kare_kapisi(
        sorgu, _VIDEO_BAGLAM_METNI,
        (lambda: _kare_gozlem_oku(video_yolu)),
        butce=butce, onbellek=_kare_onbellek, kimlik=kimlik)
    if not ok:
        print(f"  KARE RED [{saglayici}] {os.path.basename(video_yolu)}: {gerekce}",
              file=sys.stderr)
        with _KARE_KILIT:
            if len(_KARE_REDLERI) < 50:
                _KARE_REDLERI.append({"saglayici": saglayici, "sorgu": str(sorgu)[:90],
                                      "kod": kod, "gerekce": gerekce})
        return False
    # Kapi UYGULANAMADI -> eski katmana dus (gerileme yok)
    if kod in ("BEKLENTI-YOK", "BUTCE", "OKUMA-HATASI", "OKUYUCU-YOK"):
        return _vision_yer_uygun(video_yolu, sorgu, yer_terim, kimlik)
    return True


def avci_istek(url, **kw):
    """Faz B avcisi/indiricisi icin `requests.get` TASIYICISI (Faz I-6).

    ⚠ Bu yalnizca tasiyicidir: SSRF dogrulamasi, icerik turu, bayt tavani ve
    decode kapilari `medya.guvenlik` / `medya.indirme` tarafinda uygulanir.
    Burada hicbir kapi ATLANMAZ; kopru bu fonksiyonu dogrudan degil, her
    zaman `guvenli_indir`/`guvenli_istek` uzerinden kullanir.
    """
    return requests.get(url, **kw)


def _etkin_yer(sorgu: str) -> list:
    """Bu sorgu icin gecerli yer kisiti: sorgununki varsa o, yoksa VIDEONUN yeri."""
    return _sorgu_yer_terimleri(sorgu) or list(_YER_BAGLAM)


def _sorgu_yer_terimleri(sorgu: str) -> list:
    """Sorgunun ICINDEKI yer iddialarini bul -> ["japan"] gibi ulke anahtarlari."""
    d = " " + sorgu.lower().replace(",", " ") + " "
    bulunan = []
    for kel, ulke in _YER_KELIME_HARITA.items():
        if f" {kel} " in d and ulke not in bulunan:
            bulunan.append(ulke)
    return bulunan


def _havuz(h: dict) -> str:
    return (str(h.get("title") or "") + " " + str(h.get("description") or "")).lower()


def _reklam_stogu_mu(h: dict) -> bool:
    havuz = _havuz(h)
    return any(k in havuz for k in REKLAM_STOK_KELIME)


def _yer_dogru_mu(h: dict, yer_terimleri: list) -> bool:
    """Klip, sorgunun iddia ettigi yerlerden BIRINE ait mi (takma adlar dahil)?"""
    if not yer_terimleri:
        return True                       # sorgunun yer iddiasi yok, kapi yok
    havuz = " " + _havuz(h) + " "
    for ulke in yer_terimleri:
        for takma in YER_TAKMA_AD.get(ulke, []):
            if f" {takma} " in havuz or havuz.startswith(takma + " "):
                return True
    return False


def _notr_cekim_mi(h: dict) -> bool:
    """Yer dogrulanamadi; klip yine de kullanilabilir mi?

    IKI SART BIRLIKTE (11 Agu 2026'da sikilastirildi):
      1) Klip YAKIN PLAN oldugunu SOYLEMELI ("close up" / "macro"). Genis plan
         her zaman yer belli eder; tek gecerli kultursuz cerceve makrodur.
      2) Konusu kultursuz bir nesne olmali ve ekranda insan olmamali.
    Bu kadar dar olmasinin sebebi olculdu: gevsek listeyle Tokyo metnine tropik
    ada ve Filipinler mutfagi girdi."""
    havuz = " " + _havuz(h) + " "
    if not any(k in havuz for k in NOTR_ZORUNLU_ISARET):
        return False                      # yakin plan degil -> yer belli eder
    if any(f" {k} " in havuz for k in INSAN_KELIME):
        return False                      # insan var -> yanlis ulkenin insani riski
    return any(f" {k} " in havuz for k in NOTR_KONU_KELIME)


def _coverr_alakali(h: dict, sorgu: str) -> bool:
    """Klip GERCEKTEN sorgunun konusuyla ilgili mi?

    7 Agu 2026'da olculdu: kademeli kisaltma sonuc buluyor AMA konu kayiyor —
      "aerial drone remote pacific island village" -> "Lush Green Mountain Pathway"
      "close up hands weaving basket"              -> "A man using his smartphone"
    Belgeselde alakasiz klip, klip olmamasindan KOTU: anlatici Pasifik adasindan
    bahsederken daglik bir yol goruntusu izleyiciyi aninda kaybettirir.
    Bu yuzden adayin basligi/etiketleri, sorgunun KONU kelimelerinden en az birini
    icermek zorunda. Gecemezse zincir Pexels/YouTube CC/AI gorsele duser."""
    konu = [k.lower() for k in sorgu.replace(",", " ").split()
            if len(k) > 3 and k.lower() not in _COVERR_KAMERA_KELIME]
    if not konu:
        return True          # sorgu tamamen kamera kelimesiyse alaka aranamaz
    # ETIKETLER KULLANILMIYOR. 7 Agu 2026'da olculdu: Coverr'in etiketleri cok comert —
    # "Sunset Aerial of Rugged Cliffs" klibinin etiketleri arasinda "remote", "travel",
    # "nature" gibi genel kelimeler var; etiketle eslesme "dag yolu = Pasifik ada koyu"
    # gibi sonuclar uretiyordu. Baslik ve aciklama insan yazimi ve spesifik.
    havuz = (str(h.get("title") or "") + " " + str(h.get("description") or "")).lower()
    for k in konu:
        # basit kok eslesme: "islands" ~ "island", "villages" ~ "village"
        if k in havuz or k.rstrip("s") in havuz:
            return True
    return False


def _coverr_mp4(h: dict) -> str:
    """Indirme URL'si. DIKKAT: urls.mp4 ARAMA sonucunda GELMIYOR (7 Agu 2026'da olculdu:
    arama hit'lerinde urls yok, /videos/{id} ucunda var). base_filename'den kurmak hem
    dogru hem ekstra istek gerektirmiyor:
      https://cdn.coverr.co/videos/<base_filename>/1080p.mp4"""
    u = (h.get("urls") or {}).get("mp4")
    if u:
        return u
    bf = str(h.get("base_filename") or "").strip()
    return f"https://cdn.coverr.co/videos/{bf}/1080p.mp4" if bf else ""


def coverr_video(sorgu: str, hedef: str) -> bool:
    """Coverr stok videosu (ucretsiz, gunluk tavan yok). 7 Agu 2026'da eklendi.

    Coverr'in ayirt edici avantaji: arama sonucunda su alanlar geliyor ->
      is_ai_generated : AI uretimi mi (BELGESELDE ISTEMIYORUZ — gercek kamera lazim)
      is_vertical     : dikey mi (16:9 kurguda dikey klip asiri kirpilir)
      max_width/height, fps
    Bu yuzden burada saglam bir filtre kurulabiliyor: gercek + yatay + en az 1080p.
    Olculdu: filtre AI uretimi 1280x720 bir klibi dogru sekilde eledi.
    """
    if not COVERR_KEY:
        return False
    for q in _coverr_sorgular(sorgu):
        try:
            r = requests.get("https://api.coverr.co/videos",
                             params={"query": q, "page_size": 16, "api_key": COVERR_KEY},
                             timeout=30)
            if r.status_code in (401, 402, 403):
                print(f"  coverr {r.status_code}: anahtar gecersiz/yetkisiz", file=sys.stderr)
                return False
            r.raise_for_status()
            adaylar = r.json().get("hits") or []
        except Exception as e:
            print(f"  coverr arama hata: {str(e)[:120]}", file=sys.stderr)
            return False
        if not adaylar:
            continue                       # bu varyant bos -> daha kisa sorguyu dene

        def uygun(h):
            if h.get("is_ai_generated"):
                return False               # belgeselde AI goruntusu istemiyoruz
            if h.get("is_vertical"):
                return False               # 16:9 kurgu
            try:
                if int(h.get("max_height") or 0) < 1080:
                    return False           # HD alti klip 1080p kurguda yumusak durur
            except Exception:
                return False
            if not _coverr_alakali(h, sorgu):
                return False               # konu kaymasi: alakasiz klip kullanilmaz
            if _reklam_stogu_mu(h):
                return False               # kurumsal tanitim havuzu
            if not _kapi_gecti_mi(h, sorgu, "coverr"):
                return False               # biyom/donem celiskisi (Faz H)
            if not (_yer_dogru_mu(h, _etkin_yer(sorgu)) or _notr_cekim_mi(h)):
                return False               # yanlis ulke riski
            return bool(_coverr_mp4(h))

        secilmis = sorted([h for h in adaylar if uygun(h)],
                          key=lambda h: -(h.get("downloads") or 0))
        if not secilmis:
            continue
        for h in secilmis[:4]:
            if _indir_ve_hazirla(_coverr_mp4(h), hedef):
                # Faz I-1: Coverr'da indirme sonrasi kare kapisi HIC YOKTU —
                # metin kapilarini gecen yanlis-yer klibi buradan gecebiliyordu.
                if not _kare_dogrula(hedef, sorgu, _etkin_yer(sorgu),
                                     str(h.get("id") or _coverr_mp4(h)), "coverr"):
                    try:
                        os.remove(hedef)
                    except Exception:
                        pass
                    continue
                stok_provenans_kaydet(
                    hedef, saglayici="coverr",
                    asset_id=str(h.get("id") or ""), url=_coverr_mp4(h),
                    baslik=str(h.get("title") or ""), sorgu=q,
                    genislik=int(h.get("max_width") or 0),
                    yukseklik=int(h.get("max_height") or 0),
                    kare_dogrulandi=True)
                print(f"  coverr OK [{q}]: {str(h.get('title'))[:40]} "
                      f"({h.get('max_width')}x{h.get('max_height')})", file=sys.stderr)
                return True
    print(f"  coverr: uygun klip yok ({sorgu[:44]})", file=sys.stderr)
    return False


def _slug_kelimeleri(url: str) -> str:
    """Pexels video sayfa URL'sindeki slug betimleyici kelimeleri tasir:
    /video/tranquil-narrow-street-in-traditional-japanese-town-12345/
    API baslik/aciklama alani DONDURMUYOR, alaka kontrolu icin tek kaynak bu."""
    try:
        p = [x for x in str(url).rstrip("/").split("/") if x]
        return p[-1].replace("-", " ").lower() if p else ""
    except Exception:
        return ""


def pexels_video(sorgu: str, hedef: str) -> bool:
    """Pexels'ten YATAY 4K stok video (yoksa Full HD'ye duser).

    NEDEN 4K (11 Agu 2026): render 1920x1080 ama Ken Burns zoom KIRPARAK calisiyor —
    1.38 tavana kadar. 1080p kaynakta zoom sonunda etkin cozunurluk ~780p'ye iniyor ve
    goruntu yumusuyor. 4K kaynakta zoom sonunda bile 1080p'nin ustunde kaliyor.
    Pexels arama ucunda size=large = 4K filtresi var, kaynakta filtreleyip bosa
    indirme yapmiyoruz.

    ALAKA KAPISI: Coverr'da olculen sorun burada da gecerli — sorgu kisalinca konu
    kayiyor. Pexels API baslik dondurmedigi icin sayfa URL'sindeki slug kullanilir.
    """
    if not PEXELS_KEY:
        return False
    bas_h = {"Authorization": PEXELS_KEY}

    def ara(q, boyut):
        try:
            r = requests.get("https://api.pexels.com/videos/search", headers=bas_h,
                             params={"query": q, "per_page": 15,
                                     "orientation": "landscape", "size": boyut}, timeout=30)
            if r.status_code == 401:
                print("  pexels 401 (anahtar gecersiz)", file=sys.stderr)
                return None
            if r.status_code == 429:
                print("  pexels 429 (saatlik limit doldu)", file=sys.stderr)
                return []
            r.raise_for_status()
            return r.json().get("videos", [])
        except Exception as e:
            print(f"  pexels hata: {str(e)[:120]}", file=sys.stderr)
            return []

    # size=large (4K) ONCE; bulunmazsa medium (Full HD). Sorgu da kademeli kisalir.
    for boyut in ("large", "medium"):
        for q in _coverr_sorgular(sorgu):
            adaylar = ara(q, boyut)
            if adaylar is None:
                return False                      # anahtar bozuk, denemeye devam etme
            if not adaylar:
                continue
            yer_terim = _etkin_yer(sorgu)
            kademe1, kademe2 = [], []      # 1 = yeri dogrulanmis, 2 = notr cekim
            for v in adaylar:
                h = {"title": _slug_kelimeleri(v.get("url")), "description": ""}
                if not _coverr_alakali(h, sorgu):
                    continue
                if _reklam_stogu_mu(h):
                    continue               # kurumsal tanitim havuzu — belgesele oturmaz
                if not _tekrara_izin_var() and _klip_kullanildi_mi(v.get("id")):
                    continue               # bu klip videoda zaten var
                if not _kapi_gecti_mi(h, sorgu, "pexels"):
                    continue               # biyom/donem celiskisi (Faz H)
                if _yer_dogru_mu(h, yer_terim):
                    kademe = kademe1
                elif _notr_cekim_mi(h):
                    kademe = kademe2
                else:
                    continue               # yanlis ulke riski -> AI gorsele birak
                dosyalar = [f for f in (v.get("video_files") or [])
                            if f.get("file_type") == "video/mp4"
                            and (f.get("width") or 0) >= 1920]
                if not dosyalar:
                    continue
                # RENDITION SECIMI: arama zaten size=large ile filtrelendi, yani klip
                # 4K-YERLI. Ama Pexels ayni klibin 3840/2560/1920 surumlerini sunuyor.
                # Ciktimiz 1080p ve zoom tavani 1.38 -> 2650 pikselin ustu bosa gidiyor.
                # 2560'a esit/ustu EN KUCUK dosyayi aliyoruz: 558 MB yerine ~60 MB iner,
                # goruntu 1080p ciktida ayni. 2560+ yoksa en buyugunu alip yerelde
                # kucultuyoruz (_remotion_uygun_yap).
                dosyalar.sort(key=lambda f: (f.get("width") or 0))
                sec = next((f for f in dosyalar if (f.get("width") or 0) >= FOOTAGE_MAKS_GEN),
                           dosyalar[-1])
                kademe.append((v, sec))
            uygunlar = kademe1 + kademe2   # yeri dogrulanmis olan HER ZAMAN once
            if not uygunlar:
                continue
            for v, f in uygunlar[:4]:
                if f.get("link") and _indir_ve_hazirla(f["link"], hedef):
                    # KAREYE BAK: slug "japanese" diyor olabilir ama iceride Batili
                    # oyuncu olan reklam stogu olabilir. Reddedilirse dosya silinip
                    # siradaki aday denenir.
                    if not _kare_dogrula(hedef, sorgu, yer_terim,
                                         str(v.get("id")), "pexels"):
                        _klip_isaretle(v.get("id"))     # bir daha denenmesin
                        try:
                            os.remove(hedef)
                        except Exception:
                            pass
                        continue
                    _klip_isaretle(v.get("id"))
                    # ⚠ FAZ R-1d-b: kare kapisi GECILDI -> provenans KAYDA GECER.
                    stok_provenans_kaydet(
                        hedef, saglayici="pexels", asset_id=str(v.get("id")),
                        url=str(v.get("url") or ""),
                        baslik=_slug_kelimeleri(v.get("url")), sorgu=q,
                        genislik=int(f.get("width") or 0),
                        yukseklik=int(f.get("height") or 0),
                        sure_sn=float(v.get("duration") or 0),
                        kare_dogrulandi=True)
                    print(f"  pexels OK [{q}/{boyut}]: {_slug_kelimeleri(v.get('url'))[:44]} "
                          f"({f.get('width')}x{f.get('height')})", file=sys.stderr)
                    return True
    print(f"  pexels: uygun klip yok ({sorgu[:44]})", file=sys.stderr)
    return False


def pixabay_video(sorgu: str, hedef: str) -> bool:
    """Pixabay'den YATAY 4K stok video (yoksa Full HD'ye duser).

    Pexels'ten farki: arama ucunde cozunurluk filtresi YOK, o yuzden gelen
    sonuclarin icinden 'large' varyanti 4K olanlar secilir. Pixabay 'tags'
    alani donduruyor — alaka kapisi bunun uzerinden calisir.
    """
    if not PIXABAY_KEY:
        return False
    for q in _coverr_sorgular(sorgu):
        try:
            r = requests.get("https://pixabay.com/api/videos/",
                             params={"key": PIXABAY_KEY, "q": q, "per_page": 20,
                                     "safesearch": "true", "order": "popular"}, timeout=30)
            if r.status_code in (400, 401, 403):
                print(f"  pixabay {r.status_code} (anahtar/sorgu)", file=sys.stderr)
                return False
            if r.status_code == 429:
                print("  pixabay 429 (limit)", file=sys.stderr)
                return False
            r.raise_for_status()
            hits = r.json().get("hits", [])
        except Exception as e:
            print(f"  pixabay hata: {str(e)[:140]}", file=sys.stderr)
            return False

        dortk, fullhd = [], []
        yer_terim = _etkin_yer(sorgu)
        for hit in hits:
            # DIKKAT: asagidaki boyut dongusu "h" adini yukseklik icin kullaniyor.
            # Aday sozlugune "bilgi" diyoruz ki gizlice int'e donusmesin.
            bilgi = {"title": hit.get("tags", ""), "description": ""}
            if not _coverr_alakali(bilgi, sorgu):
                continue
            if _reklam_stogu_mu(bilgi):
                continue
            if not _kapi_gecti_mi(bilgi, sorgu, "pixabay"):
                continue                   # biyom/donem celiskisi (Faz H)
            if not (_yer_dogru_mu(bilgi, yer_terim) or _notr_cekim_mi(bilgi)):
                continue
            for boyut in ("large", "medium"):
                v = (hit.get("videos") or {}).get(boyut) or {}
                w, h = v.get("width") or 0, v.get("height") or 0
                if not v.get("url") or w < h:          # dikey ele
                    continue
                (dortk if w >= 3840 else fullhd if w >= 1920 else []).append(
                    (v["url"], w, h, hit.get("tags", "")))
                break
        for url, w, h, etiket in (dortk + fullhd)[:4]:
            if _indir_ve_hazirla(url, hedef):
                if not _kare_dogrula(hedef, sorgu, yer_terim, url, "pixabay"):
                    try:
                        os.remove(hedef)
                    except Exception:
                        pass
                    continue
                stok_provenans_kaydet(
                    hedef, saglayici="pixabay", asset_id=str(url), url=str(url),
                    baslik=str(etiket or ""), sorgu=q,
                    genislik=int(w or 0), yukseklik=int(h or 0),
                    kare_dogrulandi=True)
                print(f"  pixabay OK [{q}]: {etiket[:44]} ({w}x{h})", file=sys.stderr)
                return True
    print(f"  pixabay: uygun klip yok ({sorgu[:44]})", file=sys.stderr)
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
                    # ⚠ Kota ZATEN yendi (indirme oldu); kare reddederse klip
                    # silinir ama sayac geri alinmaz — saglayici tarafinda
                    # indirme gerceklesti, sahte muhasebe yapmiyoruz.
                    if not _kare_dogrula(hedef, sorgu, _etkin_yer(sorgu),
                                         str(vid), "freepik"):
                        try:
                            os.remove(hedef)
                        except Exception:
                            pass
                        continue
                    stok_provenans_kaydet(
                        hedef, saglayici="freepik", asset_id=str(vid),
                        url=str(url), sorgu=sorgu, kare_dogrulandi=True)
                    return True
            else:
                return False       # aramada sonuc vardi ama hicbiri inmedi: anahtar sorunu degil
        except Exception as e:
            print(f"  freepik hata ({_fp_etiket(anahtar)[:6]}): {str(e)[:120]}", file=sys.stderr)
            return False


def genel_yedek_sorgular(sorgu: str) -> list:
    """Gorsel yasakli stillerde (belgesel) son merdiven: ULKEYI koruyan genel sorgular.
    Sahnenin kendi konusu stokta yoksa bile ulke dogru kalir."""
    yerler = _etkin_yer(sorgu)
    if not yerler:
        return ["establishing shot city street", "aerial cityscape", "street at night"]
    takma = YER_TAKMA_AD.get(yerler[0], [])
    ulke = takma[0] if takma else ""
    sehir = takma[2] if len(takma) > 2 else ulke
    return [f"{sehir} street", f"{ulke} city aerial", f"{ulke} neighbourhood",
            f"{sehir} at night", f"{ulke} landscape"]


def footage_getir(sorgu: str, hedef: str, yt_once: bool = True,
                  tekrara_izin: bool = False) -> bool:
    """Sahne footage'i getir. Oncelik GERCEK+UCRETSIZ stok video:
       Coverr -> Pexels -> Pixabay -> Freepik(kredi varsa) -> YouTube(CC).
    Her katman kendi timeout'una sahip; biri patlarsa digerine gecer; hicbiri yoksa
    False -> caller AI gorsele duser."""
    # Coverr EN BASTA: ucretsiz, gunluk tavan yok, ve gercek/yatay/HD filtresi
    # uygulanabiliyor (is_ai_generated + is_vertical + max_height alanlari sayesinde).
    kaynaklar = [pexels_video, pixabay_video, coverr_video, freepik_video]
    if yt_once:
        # 5 Agu 2026: eskiden bu satir "YT_COOKIES varsa" diye kosulluydu. Cookie dosyasi
        # olmayan sunucuda YouTube HIC denenmiyordu; Pexels/Pixabay anahtari da bos olunca
        # footage zinciri komple bosa duser, her sahne AI gorsele kacardi. Seyahat belgeseli
        # gibi %92 footage'li bir stil bu haliyle calismaz. android_vr istemcisi cookie
        # gerektirmedigi icin kosul kaldirildi.
        kaynaklar.append(youtube_sahne)   # en sona: ucretsiz stok once denenir
    # AYNI KLIP IKI KEZ KULLANILMASIN (11 Agu 2026 olcumu): 8 sorgunun 2'si ayni
    # "traditional japanese temple" klibini getirdi. Yer kapisi sikilastikca havuz
    # daraliyor ve tekrar olasiligi artiyor; izleyicinin fark ettigi ilk sey bu.
    _YEREL.tekrar = bool(tekrara_izin)
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
