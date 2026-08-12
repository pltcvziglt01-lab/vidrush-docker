#!/usr/bin/env python3
"""FAZ H testleri — UCTAN UCA OZELLIK SAGLIGI ve SOZLESME KILIDI.

Kapsam:
  1. Kok yolu tasinabilirligi (VIDRUSH_KOK) — sabit /opt/vidrush kalmadi
  2. deploy.sh alt paketleri kopyaliyor + tariyor
  3. Is sozlesmesi (is_sozlesme.normalize): yeni + eski alanlar birlikte
  4. UI <-> backend alan uyumu (STATIK): job_id, progress, video_url, saglik
  5. GERCEK FastAPI: tum uclarin basari ve HATA yollari
  6. Arastirma koprusu: hat COKMEZ, dusus GORUNUR, para tavani ZORUNLU
  7. Derin saglik: gercek olcum, anahtar SIZMAZ, kritik eksikte ready DEMEZ
  8. 21 generate alani birebir korunuyor

⚠ DURUSTLUK KURALI: FastAPI kurulu degilse o blok "BLOKE" yazilir ve
BASARILI SAYILMAZ; fixture basarisi canli basari diye sunulmaz.

Kosum: python3 webapp/testler/test_faz_h.py
  (gercek uc testi icin: VENV_PY=/yol/python3 python3 webapp/testler/test_faz_h.py)
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEPO = os.path.dirname(KOK)
STATIC = os.path.join(KOK, "static")
JS_DIZIN = os.path.join(STATIC, "js")
sys.path.insert(0, KOK)

gecen, basarisiz, bloke = 0, [], []


def kontrol(ad, kosul, detay=""):
    global gecen
    if kosul:
        gecen += 1
        print(f"  ok   {ad}")
    else:
        basarisiz.append(f"{ad} — {detay}")
        print(f"  XX   {ad}  {detay}")


def bloke_yaz(ad, sebep):
    bloke.append(f"{ad} — {sebep}")
    print(f"  --   BLOKE {ad}: {sebep}")


def blok(ad):
    print(f"\n── {ad} ──")


def oku(*p):
    with open(os.path.join(*p), encoding="utf-8") as f:
        return f.read()


def yorumsuz(metin):
    m = re.sub(r"/\*[\s\S]*?\*/", "", metin)
    return re.sub(r"^\s*//.*$", "", m, flags=re.M)


# ═══════════════ 1. KOK YOLU TASINABILIRLIGI ═══════════════
blok("1. Kok yolu tasinabilirligi (VIDRUSH_KOK)")

SUNUCU_MODULLERI = ["pipeline.py", "kaynak.py", "hizli_render.py", "server.py"]
for ad in SUNUCU_MODULLERI:
    kaynak_metin = oku(KOK, ad)
    # Yorum satirlari haric SABIT "/opt/vidrush" dizesi kalmamali
    kod = "\n".join(s for s in kaynak_metin.splitlines()
                    if not s.strip().startswith("#"))
    sabitler = [s for s in re.findall(r'"(/opt/vidrush[^"]*)"', kod)
                if s != "/opt/vidrush"]
    kontrol(f"{ad}: sabit /opt/vidrush yolu yok", not sabitler, str(sabitler[:3]))

kontrol("pipeline.KOK_YOL env ile ezilebilir",
        'os.environ.get("VIDRUSH_KOK", "/opt/vidrush")' in oku(KOK, "pipeline.py"))
kontrol("kaynak.py VIDRUSH_KOK okuyor",
        'VIDRUSH_KOK' in oku(KOK, "kaynak.py"))
kontrol("hizli_render.py VIDRUSH_KOK okuyor",
        'VIDRUSH_KOK' in oku(KOK, "hizli_render.py"))
kontrol("varsayilan URETIM yolu degismedi (/opt/vidrush)",
        oku(KOK, "pipeline.py").count('"/opt/vidrush"') >= 1)

# ═══════════════ 2. DEPLOY KAPSAMI ═══════════════
blok("2. deploy.sh alt paket kapsami")

DEPLOY = oku(DEPO, "deploy.sh")
for paket in ("arastirma", "medya", "editor"):
    kontrol(f"deploy.sh {paket}/ kopyaliyor",
            f"webapp/$_p/*.py" in DEPLOY or f"webapp/{paket}/" in DEPLOY,
            "alt paket kopyalanmazsa canlida ModuleNotFoundError")
kontrol("deploy.sh medya/providers/ kopyaliyor",
        "medya/providers/*.py" in DEPLOY)
kontrol("deploy.sh sozdizimi taramasi alt paketleri kapsiyor",
        "webapp/*/*.py" in DEPLOY)
kontrol("deploy.sh testler/ dizinini CANLIYA GONDERMIYOR",
        "'/testler/' not in y" in DEPLOY or "/testler/" in DEPLOY)
kontrol("pyflakes taramasi alt paketleri kapsiyor",
        "webapp/arastirma/*.py" in DEPLOY and "webapp/editor/*.py" in DEPLOY)

# ═══════════════ 3. IS SOZLESMESI ═══════════════
blok("3. Is sozlesmesi (is_sozlesme.normalize)")

import is_sozlesme  # noqa: E402

YENI_ALANLAR = ("job_id", "status", "progress", "stage", "message",
                "video_url", "error", "qa", "attribution", "fallbacks")
ESKI_ALANLAR = ("durum", "ilerleme", "yuzde", "mesaj", "video", "kapak",
                "hata", "atiflar")

n = is_sozlesme.normalize("job_1", {"durum": "uretiliyor", "ilerleme": 42,
                                    "mesaj": "Render"})
for a in YENI_ALANLAR:
    kontrol(f"yeni alan var: {a}", a in n)
for a in ESKI_ALANLAR:
    kontrol(f"eski alan KORUNDU: {a}", a in n, "geriye donuk uyum kirilir")

kontrol("durum eslemesi uretiliyor -> running", n["status"] == "running", n["status"])
kontrol("progress = ilerleme", n["progress"] == 42 and n["ilerleme"] == 42)
kontrol("yuzde alias dolu (arayuz bunu okuyordu)", n["yuzde"] == 42)
kontrol("job_id = id = is_id", n["job_id"] == n["id"] == n["is_id"] == "job_1")

b = is_sozlesme.normalize("j", {"durum": "bitti", "ilerleme": 90,
                                "video": "ciktilar/j.mp4"})
kontrol("bitti -> status done", b["status"] == "done")
kontrol("bitti -> progress 100'e cekilir", b["progress"] == 100, str(b["progress"]))
kontrol("video_url dolu", b["video_url"] == "ciktilar/j.mp4")
kontrol("bitti -> stage 'bitti'", b["stage"] == "bitti", b["stage"])

h = is_sozlesme.normalize("j", {"durum": "hata", "hata": "patladi"})
kontrol("hata -> status error", h["status"] == "error")
kontrol("hata -> error alani dolu", h["error"] == "patladi")
kontrol("hata -> stage 'hata'", h["stage"] == "hata")

k = is_sozlesme.normalize("j", {"durum": "kuyrukta"}, kuyruk_sira=2,
                          kuyruk_toplam=5)
kontrol("kuyrukta -> status queued", k["status"] == "queued")
kontrol("queue_position dolu", k["queue_position"] == 2)
kontrol("eski kuyruk_sira da dolu", k["kuyruk_sira"] == 2)

# Asama esikleri pipeline'in GERCEK bildir() yuzdeleriyle uyumlu
for yuzde, beklenen in ((2, "arastirma"), (5, "plan"), (30, "medya"),
                        (72, "kapak"), (78, "render"), (96, "ses"),
                        (98, "tamamlaniyor")):
    s2, _ = is_sozlesme.asama_coz("uretiliyor", yuzde)
    kontrol(f"asama %{yuzde} -> {beklenen}", s2 == beklenen, s2)

# Bozuk girdi COKMEZ
for bozuk in ({}, {"ilerleme": "abc"}, {"durum": None}, {"ilerleme": 999},
              {"ilerleme": -5}):
    try:
        r = is_sozlesme.normalize("x", bozuk)
        kontrol(f"bozuk girdi cokmuyor: {bozuk}",
                0 <= r["progress"] <= 100)
    except Exception as e:
        kontrol(f"bozuk girdi cokmuyor: {bozuk}", False, f"{type(e).__name__}: {e}")

# Arastirma dususleri UST duzeye tasiniyor (kullanici tek yerde gorsun)
ad = is_sozlesme.normalize("x", {
    "arastirma": {"dususler": [{"asama": "arastirma", "neden": "n", "etki": "e"}]}})
kontrol("arastirma dususleri fallbacks'e tasiniyor",
        len(ad["fallbacks"]) == 1, str(ad["fallbacks"]))

# ═══════════════ 4. UI <-> BACKEND ALAN UYUMU (STATIK) ═══════════════
blok("4. UI <-> backend alan uyumu (statik kilit)")

API_JS = yorumsuz(oku(JS_DIZIN, "api.js"))
WIZARD = yorumsuz(oku(JS_DIZIN, "wizard.js"))
BILESEN = yorumsuz(oku(JS_DIZIN, "bilesenler.js"))
GORUNUM = yorumsuz(oku(JS_DIZIN, "gorunumler.js"))
SERVER = oku(KOK, "server.py")

kontrol("api.js is kimligi cozucusu job_id'yi BIRINCIL okuyor",
        "isKimligiCoz" in API_JS and "c.job_id" in API_JS)
kontrol("wizard.js artik cevap.job||is_id||id kaliBINI KULLANMIYOR",
        "cevap.job || cevap.is_id" not in WIZARD,
        "eski kirik kalip geri gelmis")
kontrol("wizard.js isKimligiCoz kullaniyor", "isKimligiCoz(cevap)" in WIZARD)
kontrol("wizard.js bos kimlikte SESSIZ GECMIYOR",
        "Sunucu iş kimliği döndürmedi" in WIZARD)

kontrol("isKart progress alanini BIRINCIL okuyor",
        "is.progress" in BILESEN, "yuzde tek basina yeterli degil")
kontrol("isKart eski yuzde/ilerleme yedegini koruyor",
        "is.ilerleme" in BILESEN and "is.yuzde" in BILESEN)
kontrol("isKart video_url ile oynatici ciziyor",
        "video_url" in BILESEN and "<video" in BILESEN)
kontrol("isKart indirme baglantisi veriyor", "download" in BILESEN)
kontrol("isKart gorunur dususleri gosteriyor", "fallbacks" in BILESEN)
kontrol("isKart hata metnini gosteriyor",
        "is.error" in BILESEN and "hata-yazi" in BILESEN)

kontrol("Projeler ekrani isDurumu() ile POLL ediyor",
        "isDurumu" in GORUNUM and "poll: true" in GORUNUM,
        "eskiden isDurumu HIC cagrilmiyordu")
kontrol("poll arka planda duruyor (bosa istek yok)",
        "document.hidden" in GORUNUM)
kontrol("poll ekran degisince temizleniyor",
        "isConnected" in GORUNUM and "pollDurdur" in GORUNUM)
kontrol("ag hatasi sahte 'hata' durumu YAZMIYOR",
        "Ag kesintisi TAKIBI DURDURMAZ" in oku(JS_DIZIN, "gorunumler.js"))

kontrol("saglik: alan yoksa ARTIK 'ok' varsayilmiyor",
        "v.status ?? 'ok'" not in GORUNUM,
        "yanlis pozitif 'Sistem hazir' geri gelmis")
kontrol("saglik: uc durum ayrimi var",
        all(x in GORUNUM for x in ("hazir", "kisitli", "kullanilamiyor")))
kontrol("saglik: durum bilinmiyorsa hazir DENMIYOR",
        "Durum bilinmiyor" in GORUNUM)
kontrol("api.js derin saglik ucunu taniyor", "saglikDerin" in API_JS)

# ═══════════════ 5. 21 GENERATE ALANI ═══════════════
blok("5. 21 generate alani birebir korunuyor")

alanlar_js = re.findall(r"\{ad: '([a-z_]+)'", API_JS)
imza = re.search(r"async def uret_baslat\((.*?)\):", SERVER, re.S)
alanlar_py = re.findall(r"(\w+): [^=]+= (?:Form|File)\(", imza.group(1)) if imza else []
# ⚠ 12 Agu 2026: main `unlu` (unlu modu) alanini ekledi -> 21 DEGIL 22.
# Sayi degisirse iki taraf da degismeli; bu test tam o senkronu kilitler.
ALAN_SAYISI = 22
kontrol(f"api.js {ALAN_SAYISI} generate alani listeliyor",
        len(alanlar_js) == ALAN_SAYISI, f"{len(alanlar_js)} bulundu")
kontrol(f"server.py {ALAN_SAYISI} Form/File alani tanimliyor",
        len(alanlar_py) == ALAN_SAYISI, f"{len(alanlar_py)} bulundu")
kontrol("22. alan `unlu` iki tarafta da var",
        "unlu" in alanlar_js and "unlu" in alanlar_py,
        f"js={'unlu' in alanlar_js} py={'unlu' in alanlar_py}")
kontrol("wizard unlu'yu hikayede gonderiyor", "d.unlu" in WIZARD)
kontrol("alan adlari BIREBIR ayni", set(alanlar_js) == set(alanlar_py),
        f"fark: {set(alanlar_js) ^ set(alanlar_py)}")
kontrol("wizard tum alanlari uretebiliyor",
        all(f"d.{a}" in WIZARD or f"'{a}'" in WIZARD or f"{a}:" in WIZARD
            for a in ("session", "story", "tur", "sure_dk", "gecis", "zoom")))

# ── SES KUTUPHANESI SAGLAYICI SENKRONU (main, 12 Agu) ──
# Arayuzdeki liste ile server.py'nin dogrulamasi ayrisirsa kullanicinin
# sectigi ses SESSIZCE reddedilir ve varsayilana duser.
SECIM = yorumsuz(oku(JS_DIZIN, "secim-deneyimi.js"))
_py_sag = re.search(r'if saglayici not in \(([^)]*)\)', SERVER)
_py_kume = set(re.findall(r'"(\w+)"', _py_sag.group(1))) if _py_sag else set()
_js_sag = re.search(r"KUTUPHANE_SAGLAYICILARI = \[([^\]]*)\]", SECIM)
_js_kume = set(re.findall(r"'(\w+)'", _js_sag.group(1))) if _js_sag else set()
kontrol("ses saglayici listeleri BIREBIR ayni", _py_kume == _js_kume,
        f"py={sorted(_py_kume)} js={sorted(_js_kume)}")
kontrol("vbee ve clone iki tarafta da var",
        {"vbee", "clone"} <= _py_kume and {"vbee", "clone"} <= _js_kume)
kontrol("ozel ses kalibi vbee/clone kabul ediyor",
        "vbee|clone" in SECIM and "vbee|clone" in SERVER)

# ═══════════════ 6. ARASTIRMA KOPRUSU ═══════════════
blok("6. Arastirma koprusu (hat cokmez, dusus gorunur, tavan zorunlu)")

import arastirma_kopru  # noqa: E402

kontrol("pipeline arastirma_kopru'yu IMPORT ediyor",
        "import arastirma_kopru" in oku(KOK, "pipeline.py"),
        "Faz A motoru yine bagli degil")
kontrol("pipeline koprüyu CAGIRIYOR",
        "arastir_ve_zenginlestir" in oku(KOK, "pipeline.py"))
kontrol("sonuc sozlugune arastirma yaziliyor",
        '"arastirma": arastirma_sonuc.sozluk()' in oku(KOK, "pipeline.py"))
kontrol("para tavani ACIKCA veriliyor (sinirsiz DEGIL)",
        "tavan_usd=TAVAN_USD" in oku(KOK, "arastirma_kopru.py"),
        "MaliyetDefteri(tavan_usd=None) SINIRSIZ demektir")
kontrol("tavan env ile ayarlanabilir",
        'ARASTIRMA_TAVAN_USD' in oku(KOK, "arastirma_kopru.py"))

# Anahtar yokken: COKMEZ, dusus URETIR, metni DEGISTIRMEZ
_eski = os.environ.pop("OPENAI_KEY", None)
try:
    metin, sonuc = arastirma_kopru.arastir_ve_zenginlestir(
        "Test konusu", mod="documentary", is_adi="t1",
        cikti_dizin=tempfile.mkdtemp())
    kontrol("anahtar yokken COKMUYOR", True)
    kontrol("anahtar yokken metin DEGISMIYOR", metin == "Test konusu")
    kontrol("anahtar yokken dusus GORUNUR", len(sonuc.dususler) == 1,
            str(sonuc.dususler))
    kontrol("dusus kaydinda neden VE etki var",
            all(k in sonuc.dususler[0] for k in ("asama", "neden", "etki")))
    kontrol("anahtar yokken ok=False (sahte basari yok)", sonuc.ok is False)
    kontrol("sayilar UYDURULMUYOR (hepsi 0)",
            sonuc.kaynak_sayisi == 0 and sonuc.dogrulanmis_iddia == 0)
    # Kurgu turlerinde arastirma CALISMAZ ve bu bir dusus DEGIL
    m2, s3 = arastirma_kopru.arastir_ve_zenginlestir(
        "x", mod="animasyon", is_adi="t2", cikti_dizin=tempfile.mkdtemp())
    kontrol("animasyonda arastirma kosmuyor", s3.calisti is False)
    kontrol("animasyonda BOSUNA dusus yazilmiyor", len(s3.dususler) == 0)
finally:
    if _eski is not None:
        os.environ["OPENAI_KEY"] = _eski

# ── SIR SIZINTISI: dusus metni KULLANICIYA GIDIYOR ──
# OpenAI'nin 401 govdesi "Incorrect API key provided: sk-abc***xyz" yaziyor;
# ham gecirilirse anahtar oneki ekrana basardi.
SIR_ORNEK = [
    "Incorrect API key provided: sk-abc123def456ghijklmn***xyz. Find it at",
    "Authorization: Bearer sk-proj-AAAABBBBCCCCDDDDEEEEFFFF",
    "?key=AIzaSyD-1234567890abcdefghijklmno",
]
for ham_sir in SIR_ORNEK:
    temiz = arastirma_kopru.gizle(ham_sir)
    kontrol(f"sir gizlendi: {ham_sir[:34]}...",
            "sk-" not in temiz and "AIza" not in temiz and
            "[gizlendi]" in temiz, temiz)
_s = arastirma_kopru.Sonuc()
_s.dusus_ekle("arastirma", "HTTP 401 sk-abcdef123456ghijklmnop", "etki")
kontrol("dusus_ekle sirri OTOMATIK gizliyor",
        "sk-abcdef" not in json.dumps(_s.sozluk()), json.dumps(_s.sozluk())[:120])
kontrol("gizle() bos/None girdide cokmuyor",
        arastirma_kopru.gizle(None) == "None")

kontrol("manifest yoksa atif listesi BOS (uydurma kaynak yok)",
        arastirma_kopru.atif_satirlari("/yok/olan", "") == [])
kontrol("alan_adi www ayikliyor",
        arastirma_kopru.alan_adi("https://www.nasa.gov/x") == "nasa.gov")
kontrol("alan_adi bozuk URL'de cokmuyor",
        arastirma_kopru.alan_adi("////") == "")

# ═══════════════ 6b. MEDYA DOGRULUK KAPISI (Faz H4) ═══════════════
blok("6b. Medya dogruluk kapisi — CANLI PILOT REGRESYONU")

import medya_kapisi  # noqa: E402

# ⚠ BU TEST CANLI BIR HATAYI KILITLIYOR (12 Agu 2026, Shackleton pilotu
# job_1786491521724_fazh15_102297): "South Georgia island approach boat"
# sorgusu "aerial view of boat approaching TROPICAL shore" klibini secti ve
# klip videoda "GUNEY GEORGIA / SAHIL" alt bandiyla gosterildi.
PILOT_SORGU = "South Georgia island approach boat"
PILOT_ADAY = "aerial view of boat approaching tropical shore"
PILOT_BAGLAM = "Shackleton Endurance seferi Antarktika buz Guney Georgia"

_ok, _g = medya_kapisi.kapi(PILOT_SORGU, PILOT_ADAY, PILOT_BAGLAM)
kontrol("PILOT REGRESYONU: Guney Georgia -> tropik kiyi REDDEDILIYOR",
        not _ok, f"gecti! gerekce={_g}")
kontrol("red gerekcesi biyom celiskisini SOYLUYOR",
        "BIYOM CELISKISI" in _g, _g)

# Yanlis pozitif kontrolu: pilotta GERCEKTEN kullanilan mesru klipler gecmeli
MESRU = ["icebreaker ship navigating frozen sea",
         "people hiking on a snowy mountain",
         "small fishing boat navigating rocky waves",
         "penguins on a rocky beach south georgia",
         "aerial view of boat approaching shore"]
for _a in MESRU:
    _o, _r = medya_kapisi.kapi(PILOT_SORGU, _a, PILOT_BAGLAM)
    kontrol(f"mesru aday GECIYOR: {_a[:38]}", _o, _r)

# Diger celiski ciftleri
for _s, _a, _bek in (("Sahara desert caravan", "tropical rainforest jungle", False),
                     ("Antarctic research station", "sand dunes of the sahara", False),
                     ("Maldives coral reef", "glacier and pack ice", False),
                     ("city street traffic", "downtown skyscraper", True),
                     ("office meeting", "tropical beach", True)):
    _o, _ = medya_kapisi.kapi(_s, _a)
    kontrol(f"kapi: {_s[:24]} vs {_a[:24]} -> {'gecer' if _bek else 'red'}",
            _o == _bek)

# EMIN DEGILSEN GECIR kurali
kontrol("biyom cikmiyorsa kapi UYGULANMAZ",
        medya_kapisi.kapi("bir sey", "baska sey")[0] is True)
kontrol("aday hem kutup hem tropik ise celiski SAYILMAZ",
        medya_kapisi.kapi("antarctic ice", "from the tropics to the antarctic")[0])
kontrol("kelime siniri: 'ice' 'service' icinde eslesmiyor",
        "kutup" not in medya_kapisi.biyom_bul("customer service desk"))
kontrol("MEDYA_KAPISI=0 ile kapatilabilir",
        'os.environ.get("MEDYA_KAPISI"' in oku(KOK, "medya_kapisi.py"))

# Donem kapisi
kontrol("tarihsel sahnede modern isaret REDDEDILIYOR",
        not medya_kapisi.donem_kapisi("1915 expedition wooden ship",
                                      "man using smartphone on deck")[0])
kontrol("modern sahnede modern isaret SORUN DEGIL",
        medya_kapisi.donem_kapisi("2024 city tour", "man using smartphone")[0])

# kaynak.py baglantisi
KAYNAK = oku(KOK, "kaynak.py")
kontrol("kaynak.py medya_kapisi'ni import ediyor",
        "import medya_kapisi" in KAYNAK)
kontrol("kapi 4 saglayiciya da bagli",
        all(f'"{p}"' in KAYNAK for p in ("pexels", "pixabay", "coverr", "youtube"))
        and KAYNAK.count("_kapi_gecti_mi(") >= 5,
        f"cagri sayisi={KAYNAK.count('_kapi_gecti_mi(')}")
kontrol("video_baglami_kur pipeline'dan cagriliyor",
        "kaynak.video_baglami_kur" in oku(KOK, "pipeline.py"))
kontrol("kapi redleri ise GORUNUR yaziliyor",
        "medya_kapisi" in oku(KOK, "pipeline.py")
        and "kapi_redleri()" in oku(KOK, "pipeline.py"))

# Cesitlilik olcumu — uydurma yok
_c = medya_kapisi.cesitlilik_olc([
    {"saglayici": "pexels", "kimlik": "a"}, {"saglayici": "pexels", "kimlik": "a"},
    {"saglayici": "coverr", "kimlik": "b"}])
kontrol("cesitlilik: klip sayisi", _c["klip"] == 3)
kontrol("cesitlilik: tekil klip", _c["tekil_klip"] == 2, str(_c))
kontrol("cesitlilik: tekrar orani gercek", abs(_c["tekrar_orani"] - 0.333) < 0.01)
kontrol("cesitlilik: bos girdide cokmuyor",
        medya_kapisi.cesitlilik_olc([])["klip"] == 0)

# ⚠ 12 Agu 2026: kapi baglanirken `klip_gecmisi_sifirla()` GOVDESI kazara
# ezildi (blok `_YER_BAGLAM = []` satirini fonksiyon ICINDE yakaladi).
# pyflakes yakaladi ve deploy'u blokladi. Bu testler o sinifi kalici kilitler.
import kaynak as _kaynak  # noqa: E402
kontrol("klip_gecmisi_sifirla govdesi SAGLAM",
        all(x in oku(KOK, "kaynak.py") for x in
            ("_vision_sayac[0] = 0", "_KULLANILAN.clear()", "_ATIFLAR.clear()")),
        "fonksiyon govdesi bozulmus")
try:
    _kaynak.klip_gecmisi_sifirla()
    kontrol("klip_gecmisi_sifirla GERCEKTEN kosuyor", True)
except Exception as _e:
    kontrol("klip_gecmisi_sifirla GERCEKTEN kosuyor", False,
            f"{type(_e).__name__}: {_e}")
kontrol("medya_kapisi MODUL duzeyinde import ediliyor",
        any(l.startswith("import medya_kapisi")
            for l in oku(KOK, "kaynak.py").splitlines()),
        "fonksiyon icine kacmis import pyflakes'te undefined name verir")
_kaynak.video_baglami_kur("Shackleton Antarktika buz Guney Georgia")
kontrol("CALISMA ZAMANI: tropik aday reddediliyor",
        _kaynak._kapi_gecti_mi(
            {"title": "aerial view of boat approaching tropical shore"},
            "South Georgia island approach boat", "pexels") is False)
kontrol("CALISMA ZAMANI: mesru aday geciyor",
        _kaynak._kapi_gecti_mi(
            {"title": "icebreaker ship navigating frozen sea"},
            "South Georgia island approach boat", "pexels") is True)
kontrol("red kaydi gerekceyle tutuluyor",
        len(_kaynak.kapi_redleri()) == 1
        and "BIYOM" in _kaynak.kapi_redleri()[0]["gerekce"])
_kaynak.klip_gecmisi_sifirla()
kontrol("yeni iste redler sifirlaniyor", _kaynak.kapi_redleri() == [])

# pyflakes kapisi: deploy.sh bunu kosuyor, testte de kosalim
if shutil.which("python3"):
    _pf = subprocess.run([sys.executable, "-m", "pyflakes",
                          os.path.join(KOK, "kaynak.py"),
                          os.path.join(KOK, "pipeline.py"),
                          os.path.join(KOK, "server.py"),
                          os.path.join(KOK, "medya_kapisi.py")],
                         capture_output=True, text=True)
    _tanimsiz = [l for l in _pf.stdout.splitlines() if "undefined name" in l]
    if _pf.returncode == 0 or _pf.stdout or _pf.stderr:
        if "No module named" in _pf.stderr:
            bloke_yaz("pyflakes taramasi", "pyflakes kurulu degil")
        else:
            kontrol("pyflakes: tanimsiz isim YOK", not _tanimsiz, str(_tanimsiz[:3]))

# ═══════════════ 6c. QA KAPISI (Faz H6) ═══════════════
blok("6c. Render sonrasi kalite kapisi")

import qa_kopru  # noqa: E402

PIPE = oku(KOK, "pipeline.py")
kontrol("pipeline qa_kopru'yu IMPORT ediyor", "import qa_kopru" in PIPE)
kontrol("pipeline QA'yi CAGIRIYOR", "qa_kopru.denetle(" in PIPE)
kontrol("QA sonucu ise yaziliyor", 'sonuc["qa"] = qa_kopru.ozet(' in PIPE)
kontrol("QA dususleri GORUNUR", "qa_kopru.dususe_cevir(" in PIPE)
kontrol("QA hattı cokertmiyor (try/except sarmali)",
        "QA kopru hatasi" in PIPE)

# ⚠ ANAHTAR ADI REGRESYONU: ozet() qa_son'un GERCEK anahtarlarini okumali.
# Ilk surumde "sure"/"I"/"Peak" yaziyordu; o adlar qa_son'da YOK ve sure ile
# LUFS arayuzde HEP bos gorunuyordu.
QAK = oku(KOK, "qa_kopru.py")
for _anahtar in ('v.get("sure_sn")', 'ln.get("lufs")', 'ln.get("tepe_dbtp")'):
    kontrol(f"ozet dogru anahtari okuyor: {_anahtar}", _anahtar in QAK)

_bos = qa_kopru.ozet({})
kontrol("bos QA ozeti cokmuyor", _bos["durum"] == "OLCULMEDI")
kontrol("olculemedi PASS SAYILMIYOR",
        qa_kopru.dususe_cevir({"durum": "OLCULEMEDI"})[0]["asama"] == "qa")
kontrol("PASS dusus uretmiyor", qa_kopru.dususe_cevir({"durum": "PASS"}) == [])
kontrol("FAIL dusus uretiyor",
        len(qa_kopru.dususe_cevir({"durum": "FAIL", "sorunlar": []})) == 1)
kontrol("olmayan dosya OLCULEMEDI doner",
        qa_kopru.denetle("/yok/olan.mp4")["durum"] == "OLCULEMEDI")
kontrol("QA_KAPISI env ile kapatilabilir", 'os.environ.get("QA_KAPISI"' in QAK)
kontrol("retry UCRETSIZ ve deterministik (ses remaster)",
        "_ses_yeniden_master" in QAK and "loudnorm" in QAK)
kontrol("retry PARA HARCAYAN yol denemiyor",
        "referansli_gorsel" not in QAK and "oai_chat" not in QAK)

# Sozlesme: QA FAIL isi basarili GOSTERMEZ
_f = is_sozlesme.normalize("j", {"durum": "bitti", "qa": {"durum": "FAIL"}})
kontrol("QA FAIL -> kalite alani FAIL", _f["kalite"] == "FAIL")
kontrol("QA FAIL -> kalite_ok False", _f["kalite_ok"] is False)
_p = is_sozlesme.normalize("j", {"durum": "bitti", "qa": {"durum": "PASS"}})
kontrol("QA PASS -> kalite_ok True", _p["kalite_ok"] is True)
_y = is_sozlesme.normalize("j", {"durum": "bitti"})
kontrol("QA yoksa OLCULMEDI (PASS varsayilmiyor)", _y["kalite"] == "OLCULMEDI")
kontrol("QA yoksa kalite_ok False", _y["kalite_ok"] is False)

kontrol("arayuz FAIL'de 'Tamamlandi' DEMIYOR",
        "Kalite: BAŞARISIZ" in BILESEN and "kaliteKotu" in BILESEN)
kontrol("arayuz QA olcumlerini gosteriyor",
        "Kalite ölçümü" in BILESEN and "is.qa.lufs" in BILESEN)
kontrol("arayuz dogru anahtari okuyor (tepe_dbtp)",
        "is.qa.tepe_dbtp" in BILESEN)

# GERCEK VIDEO uzerinde olcum (pilot ciktisi varsa)
_pilot = os.environ.get("QA_TEST_VIDEO", "")
if _pilot and os.path.exists(_pilot):
    _o = qa_kopru.ozet(qa_kopru.denetle(_pilot, beklenen={"sure_sn": 60},
                                        retry=False))
    kontrol("gercek video: cozunurluk okundu", bool(_o["cozunurluk"]), str(_o))
    kontrol("gercek video: LUFS okundu", _o["lufs"] is not None, str(_o["lufs"]))
    kontrol("gercek video: sure okundu", _o["sure_sn"] is not None)
else:
    bloke_yaz("gercek video QA olcumu",
              "QA_TEST_VIDEO ayarlanmadi (opsiyonel)")

# ═══════════════ 7. DERIN SAGLIK ═══════════════
blok("7. Derin saglik (gercek olcum, anahtar sizmaz)")

kontrol("server /api/saglik/derin ucunu tanimliyor",
        '"/api/saglik/derin"' in SERVER)
kontrol("/api/saglik artik durum alani donduruyor",
        '"durum": _d["durum"]' in SERVER)
kontrol("kritik bilesen listesi tanimli",
        "KRITIK" in oku(KOK, "saglik_derin.py"))
kontrol("ffmpeg GERCEKTEN calistiriliyor (which yetmez)",
        "subprocess.run" in oku(KOK, "saglik_derin.py"))
kontrol("yazilabilirlik GERCEK dosya yazarak olculuyor",
        "NamedTemporaryFile" in oku(KOK, "saglik_derin.py"))
kontrol("anahtar DEGERI donmuyor (yalniz bool)",
        "bool((os.environ.get(\"OPENAI_KEY\") or \"\").strip())"
        in oku(KOK, "saglik_derin.py"))

import saglik_derin  # noqa: E402
kontrol("kritik listede ffmpeg/ffprobe/yazilabilirlik/isci var",
        {"ffmpeg", "ffprobe", "cikti_yazilabilir", "isci"} <=
        set(saglik_derin.KRITIK))

# ═══════════════ 8. GERCEK FastAPI UC TESTI ═══════════════
blok("8. GERCEK FastAPI uc testi")

try:
    import fastapi  # noqa: F401
    from fastapi.testclient import TestClient
    FASTAPI_VAR = True
except Exception as e:
    FASTAPI_VAR = False
    bloke_yaz("gercek uc testi",
              f"fastapi kurulu degil ({type(e).__name__}) — "
              "kurulum: pip install fastapi python-multipart httpx")

if FASTAPI_VAR:
    gecici_kok = tempfile.mkdtemp(prefix="fazh_kok_")
    os.makedirs(os.path.join(gecici_kok, "webapp", "veri"), exist_ok=True)
    os.makedirs(os.path.join(gecici_kok, "webapp", "ciktilar"), exist_ok=True)
    os.makedirs(os.path.join(gecici_kok, "render-studio", "out"), exist_ok=True)
    shutil.copy(os.path.join(DEPO, "app", "uret.py"),
                os.path.join(gecici_kok, "uret.py"))
    os.environ["VIDRUSH_KOK"] = gecici_kok
    try:
        import server as _srv
        c = TestClient(_srv.app)

        GET_UCLARI = [
            ("/", 200), ("/api/saglik", 200), ("/api/saglik/derin", 200),
            ("/api/edit-stilleri", 200), ("/api/animasyon-stilleri", 200),
            ("/api/sesler", 200), ("/api/paletler", 200),
            ("/api/arkaplanlar", 200), ("/api/isik-duzeyleri", 200),
            ("/api/altyazi-sablonlari", 200), ("/api/profiller", 200),
            ("/api/freepik-kota", 200), ("/api/isler?session=abc123", 200),
        ]
        for u, bek in GET_UCLARI:
            r = c.get(u)
            kontrol(f"GET {u} -> {bek}", r.status_code == bek,
                    f"gelen {r.status_code}")

        # ── HATA YOLLARI ──
        kontrol("GET /api/job/olmayan -> 404",
                c.get("/api/job/olmayan_is").status_code == 404)
        kontrol("GET /api/isler gecersiz session -> 400",
                c.get("/api/isler?session=ge%20cersiz").status_code == 400)
        kontrol("GET /ciktilar/olmayan.mp4 -> 404",
                c.get("/ciktilar/olmayan.mp4").status_code == 404)
        kontrol("GET /ui/../server.py -> 404 (traversal kapali)",
                c.get("/ui/../server.py").status_code == 404)
        kontrol("GET /ui/gizli.txt -> 404 (allowlist disi)",
                c.get("/ui/gizli.txt").status_code == 404)
        kontrol("GET /ui/app.css -> 200", c.get("/ui/app.css").status_code == 200)
        kontrol("GET /ui/js/api.js -> 200",
                c.get("/ui/js/api.js").status_code == 200)
        kontrol("GET /api/ses-kutuphane?saglayici=yok -> 400",
                c.get("/api/ses-kutuphane?saglayici=yok").status_code == 400)
        kontrol("DELETE /api/profil/olmayan -> 404",
                c.delete("/api/profil/olmayan").status_code == 404)
        kontrol("DELETE /api/profil/ge!cersiz -> 400",
                c.delete("/api/profil/ge!cersiz").status_code == 400)
        kontrol("POST /api/generate kisa metin -> 400",
                c.post("/api/generate",
                       data={"session": "abc123", "story": "kisa"}
                       ).status_code == 400)
        kontrol("POST /api/generate gecersiz session -> 400",
                c.post("/api/generate",
                       data={"session": "ge cersiz", "story": "x" * 40}
                       ).status_code == 400)
        kontrol("POST /api/generate animasyon+referanssiz -> 400",
                c.post("/api/generate",
                       data={"session": "abc123", "story": "x" * 40,
                             "tur": "animasyon"}).status_code == 400)
        kontrol("POST /api/generate eksik alan -> 422",
                c.post("/api/generate", data={"session": "abc123"}
                       ).status_code == 422)

        # ── SAGLIK SOZLESMESI ──
        s = c.get("/api/saglik").json()
        kontrol("/api/saglik `durum` donduruyor", "durum" in s)
        kontrol("/api/saglik durumu gecerli deger",
                s.get("durum") in ("hazir", "kisitli", "kullanilamiyor"),
                str(s.get("durum")))
        kontrol("/api/saglik uretim_mumkun donduruyor", "uretim_mumkun" in s)
        d = c.get("/api/saglik/derin").json()
        kontrol("derin saglik bilesenleri var", bool(d.get("bilesenler")))
        kontrol("derin saglik ffmpeg'i GERCEKTEN olcmus",
                "ok" in (d["bilesenler"].get("ffmpeg") or {}))
        ham_json = json.dumps(d)
        kontrol("ANAHTAR DEGERI SIZMIYOR",
                "sk-" not in ham_json and "AIza" not in ham_json)
        kontrol("saglayici bilgisi yalniz bool/sayi",
                all(isinstance(v, (bool, int))
                    for v in d["saglayicilar"].values()))

        # ── IS SOZLESMESI CANLI ──
        _srv.isler["job_test_abc123_ff"] = {
            "durum": "uretiliyor", "ilerleme": 42, "mesaj": "Render",
            "video": None, "kapak": None, "hata": None}
        j = c.get("/api/job/job_test_abc123_ff").json()
        for a in ("job_id", "status", "progress", "stage", "video_url",
                  "fallbacks", "durum", "ilerleme", "yuzde"):
            kontrol(f"/api/job cevabinda {a} var", a in j)
        kontrol("/api/job status=running", j["status"] == "running")
        kontrol("/api/job progress=42", j["progress"] == 42)

        # ⚠ `IS_DURUM_DIR` server.py'nin YANINDA (webapp/veri/durumlar),
        # VIDRUSH_KOK altinda DEGIL. Test yazdigi durum dosyalarini kendisi
        # SILMELI; aksi halde depoyu kirletiyor (ilk kosuda tam bu oldu).
        _test_isler = ["job_test_abc123_ff"]
        _srv._durum_kaydet("job_test_abc123_ff")
        lst = c.get("/api/isler?session=abc123").json()
        kontrol("/api/isler liste donduruyor", isinstance(lst, list))
        if lst:
            kontrol("/api/isler ogesinde job_id var", "job_id" in lst[0])
            kontrol("/api/isler ogesinde progress var", "progress" in lst[0])
            kontrol("/api/isler ogesinde yuzde alias'i da var",
                    "yuzde" in lst[0])
    except Exception as e:
        import traceback
        traceback.print_exc()
        kontrol("gercek uc testi kosuldu", False, f"{type(e).__name__}: {e}")
    finally:
        # Testin yazdigi HER durum dosyasini temizle (depo kirlenmesin)
        try:
            for _ad in os.listdir(_srv.IS_DURUM_DIR):
                if _ad.startswith("job_test_"):
                    os.remove(os.path.join(_srv.IS_DURUM_DIR, _ad))
        except Exception:
            pass
        shutil.rmtree(gecici_kok, ignore_errors=True)

# ═══════════════ 9. DERLEME + JS SOZDIZIMI ═══════════════
blok("9. Derleme ve JS sozdizimi")

import glob  # noqa: E402
py_yollar = [y for y in (sorted(glob.glob(os.path.join(KOK, "*.py")))
                         + sorted(glob.glob(os.path.join(KOK, "*", "*.py")))
                         + sorted(glob.glob(os.path.join(KOK, "*", "*", "*.py"))))
             if os.sep + "testler" + os.sep not in y]
py_hata = []
for f in py_yollar:
    try:
        compile(open(f, encoding="utf-8").read(), f, "exec")
    except SyntaxError as e:
        py_hata.append(f"{os.path.basename(f)}:{e.lineno}")
kontrol(f"tum python dosyalari derleniyor ({len(py_yollar)})",
        not py_hata, str(py_hata))

if shutil.which("node"):
    js_hata = []
    for f in sorted(glob.glob(os.path.join(JS_DIZIN, "*.js"))) + \
            [os.path.join(STATIC, "app.js")]:
        r = subprocess.run(["node", "--check", f], capture_output=True,
                           text=True, timeout=30)
        if r.returncode != 0:
            js_hata.append(os.path.basename(f))
    kontrol("tum JS dosyalari node --check geciyor", not js_hata, str(js_hata))
else:
    bloke_yaz("node --check", "node kurulu degil")

css = oku(STATIC, "app.css")
kontrol("app.css suslu parantez dengesi",
        css.count("{") == css.count("}"),
        f"{css.count('{')} vs {css.count('}')}")
kontrol("yeni is karti stilleri var",
        ".iskart-oynatici" in css and ".iskart-eylem" in css)

print(f"\n{'=' * 60}")
print(f"GECEN: {gecen}   BASARISIZ: {len(basarisiz)}   BLOKE: {len(bloke)}")
for b in basarisiz:
    print(f"  XX {b}")
for b in bloke:
    print(f"  -- BLOKE {b}")
sys.exit(1 if basarisiz else 0)
