#!/usr/bin/env python3
"""FAZ B unit testleri — AGSIZ (tum saglayici cevaplari fixture).

Kosum:  python3 webapp/testler/test_faz_b.py
Cikis kodu 0 = hepsi gecti.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)

from arastirma.butce import KosuSiniri  # noqa: E402
from arastirma.manifests import TelifIhlaliHatasi  # noqa: E402
from medya import (avci, guvenlik, kapsam, kayit, lisans,  # noqa: E402
                   siralama, sorgu_planlayici, vision)
from medya.aday import AdayManifesti, MedyaAdayi  # noqa: E402
from medya.providers import acik_arsivler, stok  # noqa: E402

BUGUN = "2026-08-11"
gecen, basarisiz = 0, []


def kontrol(ad, kosul, detay=""):
    global gecen
    if kosul:
        gecen += 1
        print(f"  ok   {ad}")
    else:
        basarisiz.append(f"{ad} — {detay}")
        print(f"  XX   {ad}  {detay}")


def blok(ad):
    print(f"\n── {ad} ──")


# ═════════════════ 1) GUVENLIK: SSRF / ozel IP / sema ═════════════════
blok("guvenlik: SSRF ve URL kapisi")
for kotu in ("http://localhost/x", "http://127.0.0.1/x", "http://10.0.0.5/a",
             "http://192.168.1.1/", "http://172.16.5.5/", "http://169.254.169.254/",
             "http://[::1]/", "http://metadata/x", "http://foo.internal/y",
             "file:///etc/passwd", "ftp://x.com/a", "gopher://x/1",
             "http://0.0.0.0/", "javascript:alert(1)"):
    try:
        guvenlik.url_dogrula(kotu, coz=lambda h: [])
        kontrol(f"reddedilir: {kotu[:34]}", False, "gecti!")
    except guvenlik.GuvenlikHatasi:
        kontrol(f"reddedilir: {kotu[:34]}", True)

for iyi in ("https://commons.wikimedia.org/wiki/File:X",
            "http://www.loc.gov/item/1/", "https://api.pexels.com/videos/search"):
    try:
        guvenlik.url_dogrula(iyi, coz=lambda h: ["93.184.216.34"])
        kontrol(f"kabul edilir: {iyi[:40]}", True)
    except guvenlik.GuvenlikHatasi as e:
        kontrol(f"kabul edilir: {iyi[:40]}", False, str(e))

# DNS ic IP'ye cozumleniyorsa reddedilir (rebinding)
try:
    guvenlik.url_dogrula("https://kotu.example.com/x", coz=lambda h: ["10.1.2.3"])
    kontrol("ic IP'ye cozumlenen ad reddedilir", False, "gecti!")
except guvenlik.GuvenlikHatasi:
    kontrol("ic IP'ye cozumlenen ad reddedilir", True)


# Yonlendirme ic aga giderse reddedilir
class _Y:
    def __init__(self, kod, konum="", tur="video/mp4", uzunluk=100):
        self.status_code = kod
        self.headers = {"Location": konum, "Content-Type": tur,
                        "Content-Length": str(uzunluk)}


def _istek_yonlendiren(yontem, url, **kw):
    if "disari" in url:
        return _Y(302, "http://169.254.169.254/latest/meta-data/")
    return _Y(200)


try:
    guvenlik.guvenli_istek("https://disari.example.com/a",
                           istek=_istek_yonlendiren, coz=lambda h: ["93.184.216.34"])
    kontrol("ic aga YONLENDIRME reddedilir", False, "gecti!")
except guvenlik.GuvenlikHatasi:
    kontrol("ic aga YONLENDIRME reddedilir", True)

ok, sebep = guvenlik.icerik_kapisi("text/html", 100)
kontrol("html icerik kabul", ok)
ok, sebep = guvenlik.icerik_kapisi("application/x-msdownload", 100)
kontrol("exe icerik reddedilir", not ok, sebep)
ok, sebep = guvenlik.icerik_kapisi("video/mp4", 900 * 1024 * 1024)
kontrol("boyut tavani asilirsa reddedilir", not ok, sebep)
ok, sebep = guvenlik.icerik_kapisi("image/jpeg", 500, beklenen="video/")
kontrol("beklenen tur uyusmazsa reddedilir", not ok, sebep)

# ═════════════════ 2) LISANS DUVARI ═════════════════
blok("lisans: kabul / red / atif")
VAKA = [
    ({"LicenseShortName": "CC BY-SA 4.0", "Artist": "<a>Foto Sahibi</a>"},
     "wikimedia", True, "cc-by-sa"),
    ({"LicenseShortName": "CC0", "Artist": ""}, "wikimedia", True, "cc0"),
    ({"LicenseShortName": "Public domain", "Artist": ""}, "wikimedia", True,
     "public-domain"),
    ({"LicenseShortName": "CC BY-NC 4.0", "Artist": "X"}, "wikimedia", False, ""),
    ({"LicenseShortName": "CC BY-ND 4.0", "Artist": "X"}, "wikimedia", False, ""),
    ({"UsageTerms": "All rights reserved", "Artist": "X"}, "wikimedia", False, ""),
    ({"rights": "Rights managed, editorial use only"}, "loc", False, ""),
    ({"rights": "No known copyright restrictions"}, "loc", True, "public-domain"),
    ({"license": "by", "creator": "Ali"}, "openverse", True, "cc-by"),
    ({"licenseurl": "http://creativecommons.org/licenses/by/4.0/",
      "creator": "Veli"}, "archive_org", True, "cc-by"),
    ({}, "pexels", True, "pexels"),
    ({}, "coverr", True, "coverr"),
    ({}, "wikimedia", False, ""),                    # lisans alani YOK -> belirsiz
    ({"LicenseShortName": "Creative Commons"}, "wikimedia", False, ""),  # hangi CC?
    ({"LicenseShortName": "CC BY 4.0", "Credit": "Getty Images"},
     "wikimedia", False, ""),                        # ham metinde Getty -> red
]
for kayit_d, sag, beklenen_ok, beklenen_ad in VAKA:
    k = lisans.lisans_karari(kayit_d, sag)
    isim = f"{sag}: {json.dumps(kayit_d, ensure_ascii=False)[:44]}"
    kontrol(f"lisans {'kabul' if beklenen_ok else 'red '} {isim}",
            k["render_kullanilabilir"] == beklenen_ok
            and (not beklenen_ok or k["lisans"] == beklenen_ad),
            f"cikan={k['lisans']} ok={k['render_kullanilabilir']} {k['red_nedeni'][:40]}")

# CC-BY atif metni eser sahibi olmadan render'a giremez
k = lisans.lisans_karari({"license": "cc-by", "creator": ""}, "openverse")
kontrol("cc-by + eser sahibi YOK -> render'a giremez",
        not k["render_kullanilabilir"], k["red_nedeni"])
kontrol("atif metni lisans ve sahibi icerir",
        "CC-BY" in lisans.atif_metni("cc-by", "Ali", "Baslik", "https://x/y")
        and "Ali" in lisans.atif_metni("cc-by", "Ali", "Baslik", "https://x/y"))
kontrol("cc0 atif metni bos", lisans.atif_metni("cc0", "Ali", "B", "https://x") == "")

# ═════════════════ 3) SORGU PLANLAYICI ═════════════════
blok("sorgu_planlayici: varlik cikarimi ve sorgu varyantlari")
IDDIA = ("In 2025 the National Police Agency of Japan recorded 76,941 unattended "
         "deaths in Tokyo Prefecture.")
v = sorgu_planlayici.varlik_cikar(IDDIA)
kontrol("kurum yakalanir", any("Police Agency" in k for k in v.kurumlar),
        str(v.kurumlar))
kontrol("yer yakalanir", any("Tokyo" in y for y in v.yerler), str(v.yerler))
kontrol("tarih yakalanir", "2025" in v.tarihler, str(v.tarihler))
kontrol("on yil turetilir", "2020s" in v.onyillar, str(v.onyillar))
kontrol("cumle basi 'In' oz ad sayilmaz",
        not any(y == "In" for y in v.yerler + v.kurumlar + v.kisiler))

for amac in sorgu_planlayici.SAHNE_AMACLARI:
    p = sorgu_planlayici.sorgu_plani(IDDIA, amac, konu="kodokushi")
    kontrol(f"amac '{amac}' sorgu uretir", len(p["sorgular"]) >= 1,
            str(p["sorgular"]))
    kontrol(f"amac '{amac}' bos sorgu uretmez",
            all(len(x.strip()) >= 4 for x in p["sorgular"]), str(p["sorgular"]))

p_harita = sorgu_planlayici.sorgu_plani(IDDIA, "harita")
kontrol("harita sorgusu EN SPESIFIK yeri icerir",
        any("tokyo" in s.lower() for s in p_harita["sorgular"]),
        str(p_harita["sorgular"]))
p_kisi = sorgu_planlayici.sorgu_plani("A report by Jane Smith in 2020.", "kisi")
kontrol("kisi kalibi kisi yoksa atlanir / varsa kullanilir",
        p_kisi["sorgular"] == [] or any("smith" in s.lower()
                                       for s in p_kisi["sorgular"]),
        str(p_kisi["sorgular"]))
kontrol("amac_ata deterministik",
        sorgu_planlayici.amac_ata(5) == sorgu_planlayici.amac_ata(5))
kontrol("kategori amaci ezer",
        sorgu_planlayici.amac_ata(3, "cografya") == "harita")
amaclar = {sorgu_planlayici.amac_ata(i) for i in range(40)}
kontrol("amac dagilimi cesitli", len(amaclar) >= 4, str(sorted(amaclar)))

# ═════════════════ 4) SAGLAYICI KAYIT + NORMALIZE ═════════════════
blok("kayit: saglayici kaydi, anahtar kapisi, devre kesici")
adlar = {s.ad for s in kayit.tum_saglayicilar()}
for beklenen in ("wikimedia", "openverse", "loc", "archive_org", "pexels", "coverr"):
    kontrol(f"saglayici kayitli: {beklenen}", beklenen in adlar, str(sorted(adlar)))

os.environ.pop("PEXELS_KEY", None)
os.environ.pop("COVERR_KEY", None)
kayit.kosu_sifirla()
aktif, atlanan = kayit.aktif_saglayicilar()
kontrol("anahtarsiz saglayicilar aktif",
        {"wikimedia", "openverse", "loc", "archive_org"} <= {s.ad for s in aktif},
        str([s.ad for s in aktif]))
kontrol("anahtar isteyen KONTROLLU atlanir",
        any(a["ad"] == "pexels" and "anahtar" in a["sebep"] for a in atlanan),
        str(atlanan))

os.environ["PEXELS_KEY"] = "test-anahtar"
aktif2, _ = kayit.aktif_saglayicilar()
kontrol("anahtar verilince aktif olur", "pexels" in {s.ad for s in aktif2})

# Devre kesici
w = kayit.saglayici("wikimedia")
w.sifirla()
w.basarisiz("timeout")
kontrol("1 hata devreyi kesmez", w.hazir_mi()[0])
w.basarisiz("timeout")
kontrol("esik dolunca devre kesilir", not w.hazir_mi()[0], w.devre_nedeni)
w.sifirla()
kontrol("sifirla devreyi acar", w.hazir_mi()[0])

# Normalize: fixture cevaplari
blok("saglayici normalize: fixture cevaplari")
WM = {"title": "File:Tokyo street 1985.jpg", "imageinfo": [{
    "url": "https://upload.wikimedia.org/tokyo.jpg",
    "descriptionurl": "https://commons.wikimedia.org/wiki/File:Tokyo_street_1985.jpg",
    "width": 3000, "height": 2000, "mediatype": "BITMAP",
    "extmetadata": {"LicenseShortName": {"value": "CC BY-SA 3.0"},
                    "Artist": {"value": "<a href='#'>Foto Sahibi</a>"},
                    "DateTimeOriginal": {"value": "1985-04-01"},
                    "ImageDescription": {"value": "A street in Tokyo"}}}]}
n = kayit.saglayici("wikimedia").normalize(WM)
kontrol("wikimedia normalize: provenance URL",
        n["orijinal_url"].startswith("https://commons.wikimedia.org/wiki/File:"))
kontrol("wikimedia normalize: olculer", n["genislik"] == 3000 and n["yukseklik"] == 2000)
kontrol("wikimedia normalize: Artist HTML temizlenir",
        lisans.eser_sahibi_oku(n) == "Foto Sahibi", lisans.eser_sahibi_oku(n))
kontrol("wikimedia normalize: baslik File: onekini atar",
        not n["baslik"].startswith("File:"), n["baslik"])

OV = {"foreign_landing_url": "https://ov.example/x", "url": "https://ov.example/x.jpg",
      "title": "Kodokushi apartment", "width": 1600, "height": 900,
      "license": "by-sa", "license_url": "https://cc/by-sa", "creator": "Ali"}
n2 = kayit.saglayici("openverse").normalize(OV)
kontrol("openverse normalize", n2["genislik"] == 1600
        and lisans.lisans_karari(n2, "openverse")["lisans"] == "cc-by-sa",
        json.dumps(lisans.lisans_karari(n2, "openverse")))

LOC = {"id": "https://www.loc.gov/item/123/", "title": "Tokyo 1950",
       "image_url": ["//tile.loc.gov/s.jpg", "//tile.loc.gov/b.jpg"],
       "rights": ["No known copyright restrictions"], "date": "1950",
       "location": ["Tokyo, Japan"], "contributor": ["Foto Cekeni"]}
n3 = kayit.saglayici("loc").normalize(LOC)
kontrol("loc normalize: // URL https'e cevrilir",
        n3["indirme_url"].startswith("https://"), n3["indirme_url"])
kontrol("loc normalize: en buyuk surum secilir", n3["indirme_url"].endswith("b.jpg"))
kontrol("loc rights kamu mali okunur",
        lisans.lisans_karari(n3, "loc")["render_kullanilabilir"])

IA = {"identifier": "kodokushi_film", "title": "Archive film",
      "licenseurl": "http://creativecommons.org/licenses/by/3.0/",
      "creator": "Arsiv", "date": "1988"}
n4 = kayit.saglayici("archive_org").normalize(IA)
kontrol("archive_org normalize: details/download URL",
        "archive.org/details/" in n4["orijinal_url"]
        and "archive.org/download/" in n4["indirme_url"])
kontrol("archive_org licenseurl cc-by okunur",
        lisans.lisans_karari(n4, "archive_org")["lisans"] == "cc-by")

PX = {"url": "https://www.pexels.com/video/tokyo-street-at-night-12345/",
      "duration": 12, "_tur": "video", "user": {"name": "Cekici"},
      "video_files": [{"file_type": "video/mp4", "width": 1920, "height": 1080,
                       "link": "https://p.example/hd.mp4"},
                      {"file_type": "video/mp4", "width": 3840, "height": 2160,
                       "link": "https://p.example/4k.mp4"},
                      {"file_type": "video/mp4", "width": 2560, "height": 1440,
                       "link": "https://p.example/2k.mp4"}]}
n5 = kayit.saglayici("pexels").normalize(PX)
kontrol("pexels normalize: 2560 rendition secilir",
        n5["indirme_url"].endswith("2k.mp4"), n5["indirme_url"])
kontrol("pexels normalize: slug baslik olur", "tokyo street" in n5["baslik"],
        n5["baslik"])

# ═════════════════ 5) SIRALAMA: puan, dedup, cesitlilik ═════════════════
blok("siralama: puanlama ve cezalar")


def _aday(**kw):
    d = {"asset_id": "x1", "saglayici": "wikimedia", "tur": "video",
         "orijinal_url": "https://commons.wikimedia.org/wiki/File:A",
         "indirme_url": "https://upload.wikimedia.org/a.webm",
         "baslik": "Tokyo street at night", "genislik": 3840, "yukseklik": 2160,
         "sure_sn": 10.0, "render_kullanilabilir": True, "erisim_tarihi": BUGUN}
    d.update(kw)
    return MedyaAdayi(**d)


VARLIK = {"yerler": ["Tokyo"], "kurumlar": [], "kisiler": [],
          "tarihler": ["2025"], "onyillar": ["2020s"],
          "konu_kelimeleri": ["unattended", "deaths"]}
dogru = siralama.puanla(_aday(), varliklar=VARLIK, amac="ortam")
yanlis = siralama.puanla(_aday(asset_id="x2", baslik="Berlin office meeting"),
                         varliklar=VARLIK, amac="ortam")
kontrol("dogru yer daha yuksek puan", dogru.toplam_skor > yanlis.toplam_skor,
        f"{dogru.toplam_skor} vs {yanlis.toplam_skor}")

dusuk = siralama.puanla(_aday(asset_id="x3", genislik=640, yukseklik=360),
                        varliklar=VARLIK, amac="ortam")
kontrol("dusuk cozunurluk cezalanir", dusuk.teknik_skor < dogru.teknik_skor,
        f"{dusuk.teknik_skor} vs {dogru.teknik_skor}")
kontrol("dusuk cozunurluk uyarisi yazilir",
        any("dusuk cozunurluk" in u for u in dusuk.skor_detay["teknik_uyari"]))

wm = siralama.puanla(_aday(asset_id="x4", baslik="Tokyo street WATERMARK preview"),
                     varliklar=VARLIK, amac="ortam")
kontrol("watermark cezalanir", wm.ceza >= 22.0, str(wm.skor_detay["ceza_neden"]))

tekrar = siralama.puanla(_aday(asset_id="x5"), varliklar=VARLIK, amac="ortam",
                         gorulen_hashler={_aday().tekil_anahtar})
kontrol("ayni icerik tekrar cezalanir", tekrar.ceza >= 60.0,
        str(tekrar.skor_detay["ceza_neden"]))

dikey = siralama.puanla(_aday(asset_id="x6", genislik=1080, yukseklik=1920),
                        varliklar=VARLIK, amac="ortam")
kontrol("dikey medya cezalanir", dikey.teknik_skor < dogru.teknik_skor)

urlsuz = siralama.puanla(_aday(asset_id="x7", indirme_url=""),
                         varliklar=VARLIK, amac="ortam")
kontrol("indirme URL'si olmayan cezalanir", urlsuz.ceza >= 40.0)

# Sahne amaci uyumu
belge = siralama.puanla(_aday(asset_id="x8", tur="image",
                              baslik="official report document page"),
                        varliklar=VARLIK, amac="belge")
kontrol("belge amaci belge kelimesini odullendirir",
        belge.skor_detay["amac"] > 60, str(belge.skor_detay["amac"]))

# Saglayici kotasi
blok("siralama: saglayici kotasi %40")
havuz = []
for i in range(10):
    a = _aday(asset_id=f"p{i}", saglayici="pexels", baslik="Tokyo street night")
    siralama.puanla(a, varliklar=VARLIK, amac="ortam")
    havuz.append(a)
sayac = {"pexels": 4}
sec, gerekce = siralama.sec(havuz, adet=1, saglayici_sayaci=sayac,
                           toplam_secilen=6)
kontrol("kota dolu saglayici secilmez", sec == [], str(gerekce)[:120])
kontrol("kota reddi gerekce yazar",
        any("kota" in g["sebep"] for g in gerekce), str(gerekce)[:120])
sec2, _ = siralama.sec(havuz, adet=1, saglayici_sayaci={"pexels": 1},
                       toplam_secilen=6)
kontrol("kota altinda secim yapilir", len(sec2) == 1)

# Lisanssiz aday siralamaya GIRMEZ
lisanssiz = _aday(asset_id="ls", render_kullanilabilir=False)
sec3, _ = siralama.sec([lisanssiz], adet=1)
kontrol("render_kullanilabilir=False secilemez", sec3 == [])

# ═════════════════ 6) VISION: enjekte + deterministik yedek ═════════════════
blok("vision: enjekte edilebilir arayuz ve yedek")
p, g = vision.deterministik_puanlayici(_aday(), VARLIK, "ortam")
kontrol("yedek puanlayici calisir (anahtarsiz)", 0 <= p <= 100, f"{p} {g[:60]}")
kontrol("yedek gerekcesi metadata oldugunu soyler", g.startswith("metadata:"), g[:50])
p_yanlis, g_yanlis = vision.deterministik_puanlayici(
    _aday(baslik="Berlin Germany street"), VARLIK, "ortam")
kontrol("yanlis kultur isareti puan dusurur", p_yanlis < p, f"{p_yanlis} vs {p}")
p_jen, g_jen = vision.deterministik_puanlayici(
    _aday(baslik="businessmen in a meeting"), VARLIK, "ortam")
kontrol("jenerik stok isareti puan dusurur", p_jen < p, f"{p_jen} vs {p}")

pl = vision.olustur_puanlayici(gercek=lambda a, v, m: (91.0, "gercek"),
                               anahtar_var=True)
kontrol("enjekte edilen puanlayici kullanilir",
        pl(_aday(), VARLIK, "ortam")[0] == 91.0)
pl_bozuk = vision.olustur_puanlayici(
    gercek=lambda a, v, m: (_ for _ in ()).throw(RuntimeError("api down")),
    anahtar_var=True)
p2, g2 = pl_bozuk(_aday(), VARLIK, "ortam")
kontrol("gercek vision patlarsa yedege duser", 0 <= p2 <= 100 and "basarisiz" in g2,
        g2[:70])
kontrol("anahtar yoksa yedek secilir",
        vision.olustur_puanlayici(gercek=lambda *a: (9.0, "x"), anahtar_var=False)
        is vision.deterministik_puanlayici)

# ═════════════════ 7) KAPSAM KAPISI ═════════════════
blok("kapsam: bosluk ve guvenli fallback")
k1 = kapsam.sahne_kapsami(scene_id="s1", sahne_amaci="ortam", adaylar=[],
                          secilen=[], iddia_metni=IDDIA, varliklar=VARLIK)
kontrol("aday yoksa bosluk", k1["bosluk"] and "aday dondurmedi" in k1["sebep"])
kontrol("bosluk fallback onerir", k1["onerilen_fallback"]["tur"] in
        kapsam.FALLBACK_SIRASI, str(k1["onerilen_fallback"]))

red = _aday(asset_id="r1", render_kullanilabilir=False)
red.red_nedeni = "lisans belirsiz"
k2 = kapsam.sahne_kapsami(scene_id="s2", sahne_amaci="ortam", adaylar=[red],
                          secilen=[], iddia_metni=IDDIA, varliklar=VARLIK)
kontrol("tumu lisansta reddedilirse bosluk", k2["bosluk"]
        and "lisans/guvenlik" in k2["sebep"], k2["sebep"])

k3 = kapsam.sahne_kapsami(scene_id="s3", sahne_amaci="ortam", adaylar=[dogru],
                          secilen=[dogru], iddia_metni=IDDIA, varliklar=VARLIK)
kontrol("secim varsa bosluk yok", not k3["bosluk"])

kontrol("konum iddiasi -> harita fallback",
        kapsam.fallback_oner(IDDIA, VARLIK, "establishing")["tur"] == "harita")
kontrol("sayi iddiasi -> belge fallback",
        kapsam.fallback_oner("76,941 cases were recorded.",
                             {"yerler": []}, "detay")["tur"] == "belge-yakin-plan")
kontrol("hicbir sinyal yok -> motion-graphic",
        kapsam.fallback_oner("An abstract idea.", {}, "detay")["tur"]
        in ("motion-graphic", "belge-yakin-plan"))
kontrol("fallback ASLA rastgele stok onermez",
        all(kapsam.fallback_oner(t, VARLIK, a)["tur"] != "stok"
            for t in (IDDIA, "abstract", "76,941 cases")
            for a in kapsam.FALLBACK_SIRASI))

# ═════════════════ 8) ADAY MANIFESTI + DUVAR ═════════════════
blok("aday: manifest serilestirme ve Faz A duvari")
man = AdayManifesti(konu="kodokushi", olusturma=BUGUN)
sec_a = _aday(asset_id="sec1", lisans="cc0", karar="secildi")
sec_a.atif_metni = ""
man.ekle(sec_a)
red_a = _aday(asset_id="red1", render_kullanilabilir=False)
red_a.reddet("lisans belirsiz")
man.ekle(red_a)
ozet = man.ozet()
kontrol("manifest ozeti aday sayar", ozet["aday"] == 2, json.dumps(ozet))
kontrol("manifest red dagilimini yazar", ozet["red_dagilimi"], json.dumps(ozet))

gecici = tempfile.mkdtemp(prefix="fb_")
try:
    yol = os.path.join(gecici, "asset_manifest.json")
    man.yaz(yol)
    d = json.load(open(yol, encoding="utf-8"))
    for alan in ("sema", "konu", "ozet", "adaylar", "kapsam_bosluklari",
                 "atif_blogu", "saglayici_hatalari"):
        kontrol(f"manifest alani: {alan}", alan in d)
    ilk = d["adaylar"][0]
    for alan in ("asset_id", "orijinal_url", "indirme_url", "saglayici",
                 "eser_sahibi", "lisans", "ham_lisans", "lisans_url",
                 "ticari_izin", "degistirme_izni", "atif_gerekli", "fact_id",
                 "scene_id", "semantik_skor", "vision_skor", "ulke", "tarih",
                 "genislik", "yukseklik", "sure_sn", "icerik_hash",
                 "indirme_durumu", "render_kullanilabilir", "red_nedeni"):
        kontrol(f"aday alani: {alan}", alan in ilk)
finally:
    shutil.rmtree(gecici, ignore_errors=True)

# Faz A duvari: lisanssiz aday MedyaVarligi'na cevrilemez
try:
    red_a.varliga_cevir()
    kontrol("lisanssiz aday varliga CEVRILEMEZ", False, "gecti!")
except TelifIhlaliHatasi:
    kontrol("lisanssiz aday varliga CEVRILEMEZ", True)

iyi = _aday(asset_id="iyi1", lisans="cc0", render_kullanilabilir=True)
iyi.erisim_tarihi = BUGUN
v_ok = iyi.varliga_cevir()
kontrol("lisansli aday varliga cevrilir", v_ok.asset_id == "iyi1"
        and v_ok.kullanilabilir)
kontrol("indirme_durumu varsayilan 'indirilmedi'",
        iyi.indirme_durumu == "indirilmedi")

# ═════════════════ 9) UCTAN UCA (fixture saglayici) ═════════════════
blok("avci: uctan uca dry-run (fixture)")


class _Yanit:
    def __init__(self, veri, kod=200):
        self._v, self.status_code = veri, kod
        self.headers = {"Content-Type": "application/json"}

    def json(self):
        return self._v


WM_YANIT = {"query": {"pages": {"1": WM}}}
OV_YANIT = {"results": [OV]}
LOC_YANIT = {"results": [LOC]}
IA_YANIT = {"response": {"docs": [IA]}}
PX_YANIT = {"videos": [PX]}
istek_sayaci = {"n": 0}


def sahte_get(url, **kw):
    istek_sayaci["n"] += 1
    if "commons.wikimedia.org" in url:
        return _Yanit(WM_YANIT)
    if "openverse" in url:
        return _Yanit(OV_YANIT)
    if "loc.gov" in url:
        return _Yanit(LOC_YANIT)
    if "archive.org" in url:
        return _Yanit(IA_YANIT)
    if "pexels" in url:
        return _Yanit(PX_YANIT)
    return _Yanit({}, 404)


os.environ["PEXELS_KEY"] = "test"
os.environ.pop("COVERR_KEY", None)
kayit.kosu_sifirla()
SAHNELER = [
    {"scene_id": "s001", "iddia_metni": IDDIA, "fact_id": "f001",
     "sahne_amaci": "ortam", "medya_turu": "video"},
    {"scene_id": "s002", "iddia_metni": IDDIA, "fact_id": "f001",
     "sahne_amaci": "arsiv", "medya_turu": "image"},
    {"scene_id": "s003", "iddia_metni": "An abstract concept with no entities.",
     "fact_id": "f002", "sahne_amaci": "detay", "medya_turu": "video"},
]
m = avci.avla(SAHNELER, konu="kodokushi", erisim_tarihi=BUGUN,
              bilinen_yerler=["Tokyo"], istek=sahte_get,
              coz=lambda h: ["93.184.216.34"],
              sinir=KosuSiniri(toplam_sure_sn=600))
oz = m.ozet()
kontrol("uctan uca aday toplandi", oz["aday"] > 0, json.dumps(oz))
kontrol("en az bir sahne kapsandi",
        len(m.secilenler()) >= 1, f"secilen={len(m.secilenler())}")
kontrol("her aday scene_id tasir", all(a.scene_id for a in m.adaylar))
kontrol("her aday fact_id tasir", all(a.fact_id for a in m.adaylar))
kontrol("hicbir aday indirilmedi (dry-run)",
        all(a.indirme_durumu == "indirilmedi" for a in m.adaylar))
kontrol("coverr anahtarsiz atlandi",
        any(h.get("ad") == "coverr" for h in m.saglayici_hatalari),
        str(m.saglayici_hatalari)[:120])
kontrol("tek saglayici orani %40'i asmaz veya <4 secim",
        len(m.secilenler()) < 4 or oz["tek_saglayici_orani"] <= 0.40,
        f"oran={oz['tek_saglayici_orani']} secilen={len(m.secilenler())}")
kontrol("secilenlerin HEPSI render_kullanilabilir",
        all(a.render_kullanilabilir for a in m.secilenler()))
kontrol("secilenlerin hepsi provenance URL'si tasir",
        all(a.orijinal_url.startswith("http") for a in m.secilenler()))
kontrol("atif gerektirenlerde atif metni var",
        all(a.atif_metni for a in m.secilenler() if a.atif_gerekli),
        str([(a.asset_id, a.lisans, a.atif_metni[:30]) for a in m.secilenler()]))

# Kosu siniri: sure bitmisse avlanma durur, kismi korunur
bitmis = KosuSiniri(toplam_sure_sn=0)
m2 = avci.avla(SAHNELER, konu="k", erisim_tarihi=BUGUN, istek=sahte_get,
               coz=lambda h: ["93.184.216.34"], sinir=bitmis)
kontrol("sure bitmisse avlanma durur", any("DURDURULDU" in n for n in m2.notlar),
        str(m2.notlar)[:120])
kontrol("durunca kalan sahneler kapsam boslugu olur",
        len(m2.kapsam_bosluklari) == len(SAHNELER), str(len(m2.kapsam_bosluklari)))

# SSRF'li saglayici cevabi: aday reddedilir, kosu devam eder
def sahte_ssrf(url, **kw):
    if "openverse" in url:
        return _Yanit({"results": [{**OV, "url": "http://169.254.169.254/x.jpg",
                                    "foreign_landing_url": "http://localhost/x"}]})
    return sahte_get(url, **kw)


kayit.kosu_sifirla()
m3 = avci.avla([{**SAHNELER[0], "medya_turu": "image"}], konu="k",
               erisim_tarihi=BUGUN, istek=sahte_ssrf,
               coz=lambda h: ["93.184.216.34"], sinir=KosuSiniri(toplam_sure_sn=600))
ssrf_red = [a for a in m3.adaylar if "guvenlik" in (a.karar_nedeni or "")]
kontrol("SSRF adayi reddedilir", len(ssrf_red) >= 1,
        str([(a.saglayici, a.karar_nedeni[:40]) for a in m3.adaylar])[:200])
kontrol("SSRF reddi kosuyu durdurmaz", len(m3.adaylar) > len(ssrf_red))

# Saglayici HTTP hatasi: devre kesici + kosu devam
def sahte_hata(url, **kw):
    if "loc.gov" in url:
        return _Yanit({}, 503)
    return sahte_get(url, **kw)


kayit.kosu_sifirla()
m4 = avci.avla([SAHNELER[0]], konu="k", erisim_tarihi=BUGUN, istek=sahte_hata,
               coz=lambda h: ["93.184.216.34"], sinir=KosuSiniri(toplam_sure_sn=600))
kontrol("saglayici hatasi kaydedilir",
        any("503" in str(h.get("sebep", "")) for h in m4.saglayici_hatalari),
        str(m4.saglayici_hatalari)[:140])
kontrol("bir saglayici hatasi kosuyu bitirmez", len(m4.adaylar) > 0)


# ═══ 10) KALITE KAPISI REGRESYONLARI (11 Agu 2026 canli kosusundan) ═══
blok("regresyon: taze surecte saglayici kaydi")
# ⚠ Bu test ELLE PROVIDER IMPORT ETMEZ. Canli kosuda kayit bos dondu ve
# butun sahneler kapsam boslugu oldu; agsiz test modulleri elle import
# ettigi icin hatayi MASKELEMISTI. Taze bir Python sureci sart.
import subprocess  # noqa: E402

_kod = (
    "import sys; sys.path.insert(0, %r)\n"
    "from medya import avci\n"
    "from medya import kayit\n"
    "adlar = sorted(s.ad for s in kayit.tum_saglayicilar())\n"
    "print(','.join(adlar))\n" % KOK)
_r = subprocess.run([sys.executable, "-c", _kod], capture_output=True, text=True,
                    timeout=90)
_cikan = (_r.stdout or "").strip().splitlines()[-1] if _r.stdout.strip() else ""
_beklenen = {"archive_org", "coverr", "loc", "openverse", "pexels", "wikimedia"}
kontrol("TAZE surecte yalniz 'medya.avci' import edilince 6 saglayici kayitli",
        set(_cikan.split(",")) == _beklenen,
        f"cikan={_cikan!r} hata={(_r.stderr or '')[-160:]}")

blok("regresyon: kapsam orani sinirlari")
for _sahne, _bosluk in ((0, 0), (0, 5), (3, 0), (3, 3), (3, 9), (1, 0), (1, 4),
                        (10, 2), (10, 25)):
    _m = AdayManifesti(konu="t")
    _m.sahne_sayisi = _sahne
    _m.kapsam_bosluklari = [{"scene_id": f"s{i}"} for i in range(_bosluk)]
    _o = kapsam.kapsam_ozeti(_m)
    kontrol(f"kapsam orani 0..1 arasinda (sahne={_sahne} bosluk={_bosluk})",
            0.0 <= _o["kapsam_orani"] <= 1.0 and _o["kapsanan"] >= 0,
            json.dumps(_o))

blok("regresyon: %40 kota KUCUK secim sayilarinda da gecerli")
kontrol("3 sahne -> saglayici tavani 1",
        siralama.saglayici_tavan_adedi(3) == 1)
kontrol("10 sahne -> saglayici tavani 4",
        siralama.saglayici_tavan_adedi(10) == 4)
kontrol("1 sahne -> en az 1", siralama.saglayici_tavan_adedi(1) == 1)

# 3 sahnelik kosuda ayni saglayici 2. kez secilemez
_havuz2 = []
for i in range(6):
    _a = _aday(asset_id=f"q{i}", saglayici="pexels", baslik="Tokyo street night")
    siralama.puanla(_a, varliklar=VARLIK, amac="ortam")
    _havuz2.append(_a)
_s1, _ = siralama.sec(_havuz2, adet=1, saglayici_sayaci={}, toplam_sahne=3)
_s2, _g2 = siralama.sec(_havuz2, adet=1, saglayici_sayaci={"pexels": 1},
                        toplam_secilen=1, toplam_sahne=3)
kontrol("3 sahnede ilk secim yapilir", len(_s1) == 1)
kontrol("3 sahnede AYNI saglayici 2. kez SECILEMEZ (istisna yok)",
        _s2 == [], f"secilen={len(_s2)}")
kontrol("kota reddi gerekce yazar (kucuk sayida da)",
        any("kota" in g["sebep"] for g in _g2), str(_g2)[:120])
# Alternatif saglayici varsa o secilir
_alt = _aday(asset_id="alt1", saglayici="wikimedia", baslik="Tokyo street night")
siralama.puanla(_alt, varliklar=VARLIK, amac="ortam")
_s3, _ = siralama.sec(_havuz2 + [_alt], adet=1, saglayici_sayaci={"pexels": 1},
                      toplam_secilen=1, toplam_sahne=3)
kontrol("kota dolunca ALTERNATIF saglayici secilir",
        len(_s3) == 1 and _s3[0].saglayici == "wikimedia",
        str([(x.saglayici) for x in _s3]))

blok("regresyon: LoC arama + oge-ayrinti fixture")
LOC_ARAMA = {"results": [{
    "id": "https://www.loc.gov/item/2017123456/",
    "title": "Tokyo street scene", "image_url": ["//tile.loc.gov/kucuk.jpg"],
    "date": "1955"}]}                      # ⚠ rights alani YOK (gercek davranis)
LOC_DETAY_ACIK = {"item": {
    "rights": "No known copyright restrictions",
    "date": "1955", "location": ["Tokyo, Japan"],
    "contributor": ["Foto Cekeni"]},
    "resources": [{"height": 2400, "files": [[
        {"url": "//tile.loc.gov/buyuk.jpg", "width": 3600}]]}]}
LOC_DETAY_BELIRSIZ = {"item": {"date": "1955"}, "resources": []}

_loc = kayit.saglayici("loc")
_n_loc = _loc.normalize(LOC_ARAMA["results"][0])
kontrol("LoC arama sonucunda lisans BELIRSIZ (gercek davranis)",
        not lisans.lisans_karari(_n_loc, "loc")["render_kullanilabilir"])

_ek = _loc.zenginlestir(LOC_ARAMA["results"][0], _n_loc,
                        istek=lambda u, **kw: _Yanit(LOC_DETAY_ACIK))
kontrol("oge ayrintisi rights alanini getirir",
        "No known copyright" in str(_ek.get("rights")), str(_ek)[:120])
kontrol("oge ayrintisi GERCEK indirilebilir URL getirir",
        str(_ek.get("indirme_url")).endswith("buyuk.jpg"), str(_ek.get("indirme_url")))
kontrol("oge ayrintisi olculeri getirir",
        _ek.get("genislik") == 3600 and _ek.get("yukseklik") == 2400, str(_ek)[:120])
kontrol("ACIK hak beyani -> usable",
        lisans.lisans_karari({**_n_loc, **_ek}, "loc")["render_kullanilabilir"],
        json.dumps(lisans.lisans_karari({**_n_loc, **_ek}, "loc")))

_ek2 = _loc.zenginlestir(LOC_ARAMA["results"][0], _n_loc,
                         istek=lambda u, **kw: _Yanit(LOC_DETAY_BELIRSIZ))
kontrol("BELIRSIZ ayrinti -> hala reddedilir",
        not lisans.lisans_karari({**_n_loc, **_ek2}, "loc")["render_kullanilabilir"])
_ek3 = _loc.zenginlestir(LOC_ARAMA["results"][0], _n_loc,
                         istek=lambda u, **kw: _Yanit({}, 500))
kontrol("ayrinti HTTP hatasi rapor edilir", "_detay_hata" in _ek3, str(_ek3))

# Uctan uca: LoC ayrinti cagrisi butceli ve raporlu
def _loc_akisi(url, **kw):
    if "loc.gov/item/" in url:
        return _Yanit(LOC_DETAY_ACIK)
    if "loc.gov" in url:
        return _Yanit(LOC_ARAMA)
    return _Yanit({}, 404)


kayit.kosu_sifirla()
_m_loc = avci.avla([{"scene_id": "L1", "iddia_metni": IDDIA, "fact_id": "f001",
                     "sahne_amaci": "arsiv", "medya_turu": "image"}],
                   konu="k", erisim_tarihi=BUGUN, istek=_loc_akisi,
                   coz=lambda h: ["93.184.216.34"],
                   istenen_saglayicilar=["loc"],
                   sinir=KosuSiniri(toplam_sure_sn=600))
kontrol("LoC adayi ayrinti ile USABLE olur",
        len(_m_loc.kullanilabilir()) >= 1,
        str([(a.saglayici, a.lisans, a.red_nedeni[:40]) for a in _m_loc.adaylar]))
kontrol("ayrinti cagrisi sayisi RAPORLANIR",
        _m_loc.detay_cagrisi >= 1 and _m_loc.detay_cagrisi <= avci.DETAY_BUTCESI,
        f"detay_cagrisi={_m_loc.detay_cagrisi} butce={avci.DETAY_BUTCESI}")
kontrol("ayrinti butcesi asilmaz",
        _m_loc.detay_cagrisi <= avci.DETAY_BUTCESI)

blok("regresyon: anahtarsiz saglayici KONTROLLU atlandi + sebep")
os.environ.pop("PEXELS_KEY", None)
os.environ.pop("COVERR_KEY", None)
_eski_dosya = {}
for _ad in ("pexels", "coverr"):
    _s = kayit.saglayici(_ad)
    _eski_dosya[_ad] = _s.anahtar_dosya
    _s.anahtar_dosya = "yok_boyle_bir_dosya.txt"    # dosyadan da okumasin
kayit.kosu_sifirla()
_akt, _atl = kayit.aktif_saglayicilar()
kontrol("anahtarsiz pexels ATLANDI (0 aday degil)",
        any(a["ad"] == "pexels" and "anahtar yok" in a["sebep"] for a in _atl),
        str(_atl))
kontrol("anahtarsiz coverr ATLANDI (0 aday degil)",
        any(a["ad"] == "coverr" and "anahtar yok" in a["sebep"] for a in _atl),
        str(_atl))
_m_atl = avci.avla([SAHNELER[0]], konu="k", erisim_tarihi=BUGUN, istek=sahte_get,
                   coz=lambda h: ["93.184.216.34"],
                   sinir=KosuSiniri(toplam_sure_sn=600))
kontrol("manifest atlanan saglayiciyi SEBEBIYLE raporlar",
        any(h.get("ad") == "pexels" and "anahtar" in str(h.get("sebep"))
            for h in _m_atl.saglayici_hatalari), str(_m_atl.saglayici_hatalari)[:160])
kontrol("pexels adayi YOK (atlandigi icin)",
        not any(a.saglayici == "pexels" for a in _m_atl.adaylar))
for _ad, _d in _eski_dosya.items():
    kayit.saglayici(_ad).anahtar_dosya = _d

blok("regresyon: sessiz 0 aday raporlanir")
def _bos_donen(url, **kw):
    if "openverse" in url:
        return _Yanit({"results": []})
    return sahte_get(url, **kw)


kayit.kosu_sifirla()
_m_bos = avci.avla([{**SAHNELER[0], "medya_turu": "image"}], konu="k",
                   erisim_tarihi=BUGUN, istek=_bos_donen,
                   coz=lambda h: ["93.184.216.34"],
                   istenen_saglayicilar=["openverse"],
                   sinir=KosuSiniri(toplam_sure_sn=600))
kontrol("0 aday donduren saglayici SEBEBIYLE raporlanir",
        any("sonuc yok" in str(h.get("sebep")) for h in _m_bos.saglayici_hatalari),
        str(_m_bos.saglayici_hatalari)[:140])

print(f"\n{'=' * 58}")
print(f"GECEN: {gecen}   BASARISIZ: {len(basarisiz)}")
for b in basarisiz:
    print(f"  XX {b}")
sys.exit(1 if basarisiz else 0)
