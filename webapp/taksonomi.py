#!/usr/bin/env python3
"""HIYERARSIK KONSEPT / NIYET TAKSONOMISI — genisletilebilir, deterministik.

⚠ NEDEN VAR (Faz I-2a): `girdi_analizi.TUR_SINYALI` **sabit BES etiket**
tutuyordu (belgesel/seyahat/aciklayici/urun/hikaye) ve karari TEK BIR
anahtar-kelime sayimina dayandiriyordu. Sonuclari olculdu:

    "3-1'lik macin 90. dakikasindaki golle biten derbi ozeti"  -> belirsiz
    "iPhone 15 vs Galaxy S24 fiyat karsilastirmasi"            -> urun (alt tur YOK)
    "kabus gibi bir gece: kapinin ardindaki golge"             -> belirsiz

Yani sistem "spor ozeti", "urun karsilastirmasi", "korku hikayesi" gibi
YAYGIN konseptleri ya hic taniyamiyor ya da tek duz etikete eziyordu.

⚠ GERIYE UYUMLULUK — BOZULMAZ
`girdi_analizi.tur_tespit()` ve `GORSEL_STRATEJISI` **aynen kaliyor**; bu modul
onlarin YERINE gecmiyor, USTUNE biniyor. `ESKI_ETIKET` haritasi her aileyi eski
bes etiketten birine indirger, boylece pipeline sozlesmesi hic degismez.

⚠ TASARIM KURALLARI
1. **SADECE ANAHTAR KELIME DEGIL.** Karar iki bacakli: (a) sozluk isabeti,
   (b) OLCULEBILIR YAPISAL SINYALLER (yil yogunlugu, para birimi, skor kalibi,
   olcu birimi, cozunurluk simgesi, adim isareti, m2/oda kalibi...). Sinyaller
   metnin BICIMINDEN gelir, kelime listesinden degil.
2. **AG YOK, PARA YOK.** Bu modulde hicbir ag cagrisi yoktur. Belirsizlikte
   kullanilabilecek model analizi ENJEKTE EDILEN bir cagrilabilir'dir
   (`model_coz`); varsayilan None ve o zaman motor tamamen deterministiktir.
3. **MODEL SERBEST KONUSAMAZ.** Enjekte edilen model yalnizca motorun urettigi
   ADAY LISTESINDEN secebilir. Liste disi cevap YOK SAYILIR ve deterministik
   karara donulur. Model kullanildiysa `kaynak="model"` diye RAPORLANIR.
4. **DURUST GUVEN.** Guven skoru uydurma degil; marj (1. ve 2. aday farki) ve
   KANIT SAYISI'ndan hesaplanir, formulu `guven_hesapla()` icinde acik.
   Kanit yetersizse motor **"belirsiz"** der ve zorla etiket secmez.
5. **MELEZ MESRUDUR.** Iki aday yakinsa tek etikete ezmek yerine `durum="melez"`
   ve ikincil dal RAPORLANIR.
6. **GENISLETILEBILIR.** Yeni konsept eklemek = `AGAC`a bir satir. Motor kodu
   degismez. Kapsam `kapsam_ozeti()` ile OLCULUR — "her stili biliyoruz" gibi
   kanitsiz iddia kurulmaz.
"""
from __future__ import annotations

import re

# ═══════════════════════════ OLCULEBILIR SINYALLER ═══════════════════════════
# Her sinyal metnin BICIMINDEN sayilabilir bir kanit uretir. Donus: kac kez.
# ⚠ Bunlar "konu kelimesi" DEGIL; kelime listesi degistirilmeden de calisirlar.

_YIL = re.compile(r"\b(1[0-9]{3}|20[0-9]{2})\b")
_ESKI_YIL = re.compile(r"\b(1[0-9]{3}|19[0-8][0-9])\b")
_PARA = re.compile(r"(\$|€|₺|\bTL\b|\bUSD\b|\bEUR\b|\bdolar\b|\beuro\b|"
                   r"\bfiyat\w*\b|\bprice\b|\bucret\w*\b|\bücret\w*\b)", re.I)
_YUZDE = re.compile(r"(%\s?\d|\d\s?%|\byuzde\b|\byüzde\b|\bpercent\b)", re.I)
_SKOR = re.compile(r"\b\d{1,2}\s?[-:]\s?\d{1,2}\b")
_DAKIKA = re.compile(r"\b\d{1,3}\s?(\.|')\s?(dakika|dk|minute|min)\b|\b\d{1,3}'\w*\b", re.I)
_OLCU = re.compile(r"\b\d+\s?(g|gr|gram|kg|ml|lt|litre|cl|adet|yemek kasigi|"
                   r"yemek kaşığı|cay kasigi|çay kaşığı|tbsp|tsp|cup|bardak|"
                   r"su bardagi|su bardağı|dilim|paket)\b", re.I)
_ADIM = re.compile(r"(\badim\s?\d|\badım\s?\d|\bstep\s?\d|^\s*\d+[\.\)]\s|"
                   r"\bonce\b|\bönce\b|\bsonra\b|\bardindan\b|\bardından\b|"
                   r"\bilk olarak\b|\bson olarak\b|\bfirst\b|\bthen\b|\bfinally\b)",
                  re.I | re.M)
_SORU = re.compile(r"(\bnasil\b|\bnasıl\b|\bneden\b|\bnedir\b|\bnicin\b|\bniçin\b|"
                   r"\bhow to\b|\bhow does\b|\bwhat is\b|\bwhy\b|\bexplained\b)", re.I)
_COZUNURLUK = re.compile(r"\b(4k|8k|uhd|1080p|60\s?fps|hdr|hyperlapse|timelapse|"
                         r"time lapse|drone|dron|hava cekimi|hava çekimi|aerial)\b", re.I)
_EMLAK_OLCU = re.compile(r"(\b\d+\s?(m2|m²|metrekare|sqft|sq ft)\b|\b\d\+\d\b|"
                         r"\b\d+\s?(oda|odali|odalı|bedroom)\b)", re.I)
_MODEL_NO = re.compile(r"\b[A-Z][a-zA-Z]{2,}\s?\d{2,4}\b")
_KARSILASTIRMA = re.compile(r"(\bvs\b|\bversus\b|\bkarsilastir\w*\b|\bkarşılaştır\w*\b|"
                            r"\bhangisi\b|\bfarki\b|\bfarkı\b|\bcomparison\b)", re.I)
_DIYALOG = re.compile(r"[\"“”«][^\"“”»]{6,}[\"“”»]|\s—\s\w")
_EMIR = re.compile(r"\b\w+(?:ın|in|un|ün)(?:ız|iz|uz|üz)\b|\b(ekleyin|karistirin|"
                   r"karıştırın|pisirin|pişirin|dokun|tikla|tıkla|abone ol|"
                   r"subscribe|click|try it)\b", re.I)
_BORSA = re.compile(r"(\bhisse\w*\b|\bborsa\b|\benflasyon\b|\bfaiz\b|\bportfoy\w*\b|"
                    r"\bportföy\w*\b|\byatirim\w*\b|\byatırım\w*\b|\bkripto\b|"
                    r"\bbitcoin\b|\bstock market\b|\binflation\b|\betf\b|\bnasdaq\b)", re.I)
_SUC = re.compile(r"(\bcinayet\w*\b|\bkatil\b|\bfail\b|\bdava\b|\bmahkeme\b|"
                  r"\bsanik\w*\b|\bsanık\w*\b|\bdedektif\b|\bsoruşturma\b|"
                  r"\bsorusturma\b|\bkayboldu\b|\bmurder\b|\bdetective\b|"
                  r"\bcold case\b|\bunsolved\b|\bkurban\b)", re.I)
_OZEL_AD_COK = re.compile(r"\b[A-ZĞÜŞİÖÇ][a-zğüşıöçA-Z]{2,}\s+[A-ZĞÜŞİÖÇ][a-zğüşıöç]{2,}\b")

SINYAL = {
    "yil": lambda m: len(_YIL.findall(m)),
    "eski_yil": lambda m: len(_ESKI_YIL.findall(m)),
    "para": lambda m: len(_PARA.findall(m)),
    "yuzde": lambda m: len(_YUZDE.findall(m)),
    "skor": lambda m: len(_SKOR.findall(m)),
    "dakika": lambda m: len(_DAKIKA.findall(m)),
    "olcu": lambda m: len(_OLCU.findall(m)),
    "adim": lambda m: len(_ADIM.findall(m)),
    "soru": lambda m: len(_SORU.findall(m)),
    "cozunurluk": lambda m: len(_COZUNURLUK.findall(m)),
    "emlak_olcu": lambda m: len(_EMLAK_OLCU.findall(m)),
    "model_no": lambda m: len(_MODEL_NO.findall(m)),
    "karsilastirma": lambda m: len(_KARSILASTIRMA.findall(m)),
    "diyalog": lambda m: len(_DIYALOG.findall(m)),
    "emir": lambda m: len(_EMIR.findall(m)),
    "borsa": lambda m: len(_BORSA.findall(m)),
    "suc": lambda m: len(_SUC.findall(m)),
    "kisi_adi": lambda m: len(_OZEL_AD_COK.findall(m)),
}


# ═══════════════════════════ AGAC ═══════════════════════════
# yol -> {ust, ad, anahtar, sinyal, karsit}
#   yol      : "aile.tur" — nokta ile hiyerarsi. Yeni dal = YENI SATIR.
#   anahtar  : konu kelimeleri (TR+EN). Tek basina karar VERMEZ.
#   sinyal   : {sinyal_adi: agirlik} — yapisal kanit.
#   karsit   : bu dal OLMADIGINI gosteren kelimeler (yanlis pozitif korumasi).
#
# ⚠ Bu agac dunyanin tum icerik turlerini KAPSAMIYOR ve oyle oldugunu iddia
# etmiyor. Gercek kapsam `kapsam_ozeti()` ile sayilir; disinda kalan girdi
# "belirsiz" doner (zorla etiketlenmez).
AGAC = {
    # ───────────────────────── BELGESEL ─────────────────────────
    "belgesel.tarih": {
        "ad": "Tarih belgeseli",
        "anahtar": ("tarih", "history", "historical", "sefer", "expedition",
                    "savas", "savaş", "war", "imparatorluk", "empire",
                    "arsiv", "arşiv", "archive", "yuzyil", "yüzyıl", "century",
                    "donem", "dönem", "antik", "ancient", "kesif", "keşif",
                    "hanedan", "dynasty", "devrim", "revolution"),
        "sinyal": {"eski_yil": 2.0, "yil": 1.0},
        "karsit": ("tarif", "recipe", "inceleme", "unboxing"),
    },
    "belgesel.biyografi": {
        "ad": "Biyografi",
        "anahtar": ("biyografi", "biography", "hayati", "hayatı", "yasami",
                    "yaşamı", "life story", "kimdi", "who was", "portre",
                    "portrait", "dogdu", "doğdu", "olumu", "ölümü",
                    "kariyeri", "career of", "yukselisi", "yükselişi",
                    "imparatoru", "kurucusu", "founder"),
        "sinyal": {"kisi_adi": 1.5, "eski_yil": 1.0},
        "karsit": ("tarif", "recipe"),
    },
    "belgesel.arastirma": {
        "ad": "Arastirma / inceleme belgeseli",
        "anahtar": ("arastirma", "araştırma", "investigation", "belge",
                    "ifsa", "ifşa", "expose", "gercekler", "gerçekler",
                    "perde arkasi", "perde arkası", "behind the scenes",
                    "raporu", "dosyasi", "dosyası", "iddialar"),
        "sinyal": {"yuzde": 1.0, "kisi_adi": 0.5},
        "karsit": ("tarif", "recipe"),
    },
    "belgesel.haber": {
        "ad": "Haber / gundem analizi",
        "anahtar": ("haber", "news", "gundem", "gündem", "son dakika",
                    "breaking", "analiz", "analysis", "kriz", "crisis",
                    "secim", "seçim", "election", "aciklama", "açıklama",
                    "gelismeler", "gelişmeler", "briefing"),
        "sinyal": {"yuzde": 1.0, "kisi_adi": 0.5},
        "karsit": ("tarif", "recipe", "masal"),
    },
    "belgesel.doga": {
        "ad": "Doga belgeseli",
        "anahtar": ("doga belgeseli", "doğa belgeseli", "vahsi", "vahşi",
                    "wildlife", "ekosistem", "ecosystem", "tur", "species",
                    "yasam alani", "yaşam alanı", "habitat", "gocu", "göçü",
                    "migration", "avci", "avcı", "predator", "okyanus",
                    "orman", "rainforest", "kutup", "safari"),
        "sinyal": {},
        "karsit": ("otel", "rezervasyon", "tarif"),
    },
    "belgesel.true_crime": {
        "ad": "True crime",
        "anahtar": ("true crime", "faili mechul", "faili meçhul", "seri katil",
                    "serial killer", "kayip vaka", "kayıp vaka", "gizemli olay",
                    "cozulmemis", "çözülmemiş", "adli", "forensic", "cinayet dosyasi"),
        "sinyal": {"suc": 2.0, "kisi_adi": 0.5},
        "karsit": ("tarif", "recipe", "masal", "cocuk", "çocuk"),
    },

    # ───────────────────────── SEYAHAT ─────────────────────────
    "seyahat.sehir": {
        "ad": "Sehir rehberi",
        "anahtar": ("sehir turu", "şehir turu", "city tour", "gezilecek",
                    "gorulecek", "görülecek", "rehber", "guide", "rota",
                    "itinerary", "otel", "hotel", "konaklama", "ulasim",
                    "ulaşım", "gezi", "seyahat", "travel", "tatil", "vacation",
                    "sokaklari", "sokakları"),
        "sinyal": {},
        "karsit": ("tarif", "hisse", "cinayet"),
    },
    "seyahat.ulke_4k": {
        "ad": "Ulke / sehir 4K sinematik",
        "anahtar": ("4k", "8k", "cinematic", "sinematik", "relaxing",
                    "scenic", "manzara", "landscape", "ulke", "ülke",
                    "country", "virtual tour", "sanal tur", "walking tour",
                    "yuruyus turu", "yürüyüş turu"),
        "sinyal": {"cozunurluk": 2.5},
        "karsit": ("tarif", "hisse", "unboxing"),
    },
    "seyahat.doga_manzara": {
        "ad": "Doga / manzara",
        # ⚠ FAZ I-18'DE OLCULEN KAPSAM BOSLUGU. Bu dal yalnizca 19 kelime
        # tasiyordu ve seyahat ailesi pratikte HIZMET sozluguyle ("gezi",
        # "rehber", "tur") tetikleniyordu. Olculen sonuc: uc ayri doga metni
        # de `belirsiz` cikti ve stil `belgesel-sinematik` VARSAYILANINA
        # dustu — yani "doga metni otomatik seyahat/sinematik siniflanir"
        # iddiasi KARSILIKSIZDI:
        #   "İzlanda ... buzul lagunleri ... siyah kum plajlari"  -> belirsiz (0 isaret)
        #   "Norvec fiyortlarinda ... selaleler ve kayaliklar"     -> belirsiz (1 isaret)
        #   "Patagonya ... granit kuleler, buzul golleri, pampa"   -> belirsiz (0 isaret)
        # Eksik olan MANZARA/YER SEKLI sozluguydu. §16'nin tasarim sozu
        # geregi yalnizca AGAC'a satir eklendi; motor kodu DEGISMEDI.
        # ⚠ Kisa terimler (gol/dag) ek toleransi ALMAZ (§16 siniri); bu
        # yuzden cekimli biciimler ayrica yazildi.
        "anahtar": ("doga manzarasi", "doğa manzarası", "dag", "dağ",
                    "mountain", "gol", "göl", "lake", "sahil", "beach",
                    "vadi", "valley", "selale", "şelale", "waterfall",
                    "milli park", "national park", "patika", "trail",
                    # ── I-18: buz / kutup ──
                    "buzul", "glacier", "buzulu", "gletscher", "aysberg",
                    "iceberg", "kutup", "arctic", "tundra", "permafrost",
                    "lagun", "lagün", "lagoon",
                    # ── I-18: kiyi / deniz yer sekli ──
                    "fiyort", "fjord", "kiyi", "kıyı", "coastline",
                    "plaj", "plaji", "plajı", "kumsal", "falez", "cliff",
                    "kayalik", "kayalık", "kayaliklar", "kayalıklar",
                    "koy", "körfez", "korfez", "bay ", "delta",
                    # ── I-18: dag / ic bolge yer sekli ──
                    "zirve", "zirvesi", "summit", "peak", "yayla",
                    "plato", "plateau", "kanyon", "canyon", "gorge",
                    "vadisi", "krater", "crater", "kaldera", "caldera",
                    "volkan", "yanardag", "yanardağ", "volcano",
                    "magara", "mağara", "cave", "obruk",
                    # ── I-18: ortu / iklim kusagi ──
                    "orman", "ormani", "ormanı", "forest", "ormanlik",
                    "col ", "çöl", "desert", "bozkir", "bozkır", "step",
                    "pampa", "savan", "jungle", "yagmur ormani",
                    "yağmur ormanı", "gokkusagi", "gökkuşağı",
                    "kuzey isiklari", "kuzey ışıkları", "aurora",
                    # ── I-18: su ──
                    "nehir", "nehri", "river", "irmak", "cay ", "çay ",
                    "kaplica", "kaplıca", "gayzer", "geyser", "hot spring",
                    "golu", "gölü", "golleri", "gölleri", "lakes",
                    # ── I-18: cekimli/bilesik yer sekli formlari ──
                    # ⚠ Kisa kokler (vadi=4, dag=3) ek toleransi ALMIYOR;
                    # cekimli bicimler bu yuzden AYRICA yazildi (olculdu:
                    # "vadiler" tek basina hicbir dala isaret uretmiyordu).
                    "vadiler", "vadileri", "daglar", "dağlar", "daglari",
                    "dağları", "goller", "göller", "sahiller", "kiyilari",
                    "kıyıları", "peribacasi", "peribacası", "peri bacasi",
                    "peri bacası", "peribacalari", "peribacaları", "hoodoo",
                    "yeralti", "yeraltı", "kumul", "kumullar", "kayalik",
                    "buzullar", "buzullari", "buzulları", "selaleler",
                    "şelaleler", "kanyonlar", "magaralar", "mağaralar"),
        "sinyal": {"cozunurluk": 1.0},
        "karsit": ("tarif", "hisse"),
    },
    "seyahat.hava_drone": {
        "ad": "Hava cekimi / drone",
        "anahtar": ("drone", "dron", "hava cekimi", "hava çekimi", "aerial",
                    "kus bakisi", "kuş bakışı", "birds eye", "fpv"),
        "sinyal": {"cozunurluk": 2.0},
        "karsit": ("tarif", "hisse"),
    },
    "seyahat.ambient": {
        "ad": "Ambient / meditasyon",
        "anahtar": ("ambient", "meditasyon", "meditation", "rahatlatici",
                    "rahatlatıcı", "relaxing", "sakinlestirici", "sakinleştirici",
                    "uyku", "sleep", "nefes", "breathing", "zen", "lofi",
                    "beyaz gurultu", "beyaz gürültü", "white noise", "huzur",
                    "spa", "yoga"),
        "sinyal": {},
        "karsit": ("cinayet", "hisse", "unboxing", "mac", "maç"),
    },

    # ───────────────────────── EGITIM ─────────────────────────
    "egitim.aciklayici": {
        "ad": "Aciklayici",
        "anahtar": ("aciklama", "açıklama", "explained", "nedir", "what is",
                    "nasil calisir", "nasıl çalışır", "how it works",
                    "adim adim", "adım adım", "step by step", "basitce",
                    "basitçe", "ozetle", "özetle", "temel", "basics"),
        "sinyal": {"soru": 2.0, "adim": 1.0},
        "karsit": ("tarif", "recipe"),
    },
    "egitim.bilim": {
        "ad": "Bilim",
        "anahtar": ("bilim", "science", "fizik", "physics", "kimya",
                    "chemistry", "biyoloji", "biology", "evren", "universe",
                    "kuantum", "quantum", "hucre", "hücre", "cell", "genetik",
                    "genetics", "atom", "molekul", "molekül", "deney",
                    "experiment", "teori", "theory", "arastirmacilar",
                    "araştırmacılar", "researchers", "nasa", "uzay", "space",
                    "kara delik", "black hole", "evrim", "evolution"),
        "sinyal": {"soru": 1.0, "yuzde": 0.5},
        "karsit": ("tarif", "unboxing", "otel"),
    },
    "egitim.teknoloji": {
        "ad": "Teknoloji",
        "anahtar": ("teknoloji", "technology", "yapay zeka", "artificial "
                    "intelligence", "yazilim", "yazılım", "software",
                    "algoritma", "algorithm", "kod", "coding", "internet",
                    "siber", "cyber", "veri merkezi", "data center", "cip",
                    "çip", "chip", "islemci", "işlemci", "processor",
                    "blockchain", "robotik", "robotics", "makine ogrenmesi",
                    "makine öğrenmesi", "machine learning"),
        "sinyal": {"soru": 1.0, "model_no": 0.5},
        "karsit": ("tarif", "otel", "cinayet"),
    },
    "egitim.finans": {
        "ad": "Finans / ekonomi",
        "anahtar": ("finans", "finance", "ekonomi", "economy", "economics",
                    "butce", "bütçe", "budget", "tasarruf", "saving",
                    "kredi", "loan", "vergi", "tax", "gelir", "income",
                    "piyasa", "market", "resesyon", "recession"),
        "sinyal": {"borsa": 2.5, "para": 1.0, "yuzde": 1.0},
        "karsit": ("tarif", "masal", "cinayet"),
    },
    "egitim.ders": {
        "ad": "Ders / kurs",
        "anahtar": ("ders", "lesson", "kurs", "course", "egitim", "eğitim",
                    "ogren", "öğren", "learn", "mufredat", "müfredat",
                    "konu anlatimi", "konu anlatımı", "sinav", "sınav",
                    "exam", "odev", "ödev", "alistirma", "alıştırma",
                    "tutorial", "ogretmen", "öğretmen", "ogrenci", "öğrenci"),
        "sinyal": {"adim": 1.5, "soru": 0.5},
        "karsit": ("cinayet", "unboxing"),
    },

    # ───────────────────────── HIKAYE ─────────────────────────
    "hikaye.kurgu": {
        "ad": "Kurgu / anlati",
        "anahtar": ("hikaye", "hikâye", "story", "kurgu", "fiction", "roman",
                    "novel", "karakter", "character", "bir varmis",
                    "bir varmış", "once upon", "anlati", "anlatı", "senaryo",
                    "bolum", "bölüm", "chapter"),
        "sinyal": {"diyalog": 1.5},
        "karsit": ("tarif", "hisse", "inceleme", "belgesel"),
    },
    "hikaye.korku": {
        "ad": "Korku",
        "anahtar": ("korku", "horror", "kabus", "nightmare", "hayalet",
                    "ghost", "lanet", "curse", "perili", "haunted",
                    "gerilim", "thriller", "karanlik", "karanlık", "urperti",
                    "ürperti", "creepy", "canavar", "monster", "golge",
                    "gölge", "cığlık", "ciglik", "scream"),
        "sinyal": {"diyalog": 1.0},
        "karsit": ("cocuk masali", "çocuk masalı", "tarif", "hisse"),
    },
    "hikaye.cocuk": {
        "ad": "Cocuk hikayesi",
        "anahtar": ("cocuk", "çocuk", "children", "kids", "masal",
                    "fairy tale", "uyku masali", "uyku masalı", "bedtime",
                    "sevimli", "cute", "tavsan", "tavşan", "bunny",
                    "ayicik", "ayıcık", "prenses", "princess", "ejderha",
                    "dragon", "arkadaslik", "arkadaşlık", "friendship"),
        "sinyal": {"diyalog": 1.0},
        "karsit": ("cinayet", "korku", "hisse", "kanli", "kanlı"),
    },

    # ───────────────────────── URUN ─────────────────────────
    "urun.inceleme": {
        "ad": "Urun incelemesi",
        "anahtar": ("inceleme", "review", "kullanim deneyimi",
                    "kullanım deneyimi", "test ettik", "hands on",
                    "unboxing", "kutu acilimi", "kutu açılımı",
                    "arti eksi", "artı eksi", "pros and cons",
                    "degir mi", "değer mi", "worth it"),
        "sinyal": {"model_no": 1.5, "para": 1.0},
        "karsit": ("masal", "cinayet"),
    },
    "urun.karsilastirma": {
        "ad": "Urun karsilastirmasi",
        "anahtar": ("karsilastirma", "karşılaştırma", "comparison", "vs",
                    "versus", "hangisi", "which one", "farki", "farkı",
                    "alternatif", "alternative"),
        "sinyal": {"karsilastirma": 2.5, "model_no": 1.0, "para": 0.5},
        "karsit": ("masal", "cinayet"),
    },
    "urun.tanitim": {
        "ad": "Urun tanitimi",
        "anahtar": ("tanitim", "tanıtım", "lansman", "launch", "yeni urun",
                    "yeni ürün", "new product", "ozellikleri", "özellikleri",
                    "features", "kampanya", "campaign", "indirim", "discount",
                    "marka", "brand", "promosyon", "showcase"),
        "sinyal": {"para": 1.5, "model_no": 1.0, "emir": 0.5},
        "karsit": ("masal", "cinayet", "tarif"),
    },
    "urun.ugc_reklam": {
        "ad": "UGC / reklam",
        "anahtar": ("ugc", "reklam", "advertisement", "sponsorlu",
                    "sponsored", "influencer", "affiliate", "link aciklamada",
                    "link açıklamada", "abone ol", "subscribe", "testimonial",
                    "musteri yorumu", "müşteri yorumu"),
        "sinyal": {"emir": 2.0, "para": 0.5},
        "karsit": ("masal", "belgesel"),
    },

    # ───────────────────────── YASAM ─────────────────────────
    "yasam.yemek": {
        "ad": "Yemek / tarif",
        "anahtar": ("tarif", "recipe", "yemek", "food", "mutfak", "kitchen",
                    "pisir", "pişir", "cook", "firin", "fırın", "oven",
                    "malzemeler", "ingredients", "hamur", "dough", "sos",
                    "sauce", "kek", "cake", "corba", "çorba", "soup",
                    "tencere", "tarifi", "lezzet", "sef", "şef", "chef"),
        "sinyal": {"olcu": 2.5, "adim": 1.0, "emir": 1.0},
        "karsit": ("hisse", "cinayet", "drone"),
    },
    "yasam.spor": {
        "ad": "Spor",
        "anahtar": ("spor", "sport", "mac", "maç", "match", "gol", "goal",
                    "sampiyona", "şampiyona", "championship", "lig", "league",
                    "derbi", "derby", "takim", "takım", "team", "oyuncu",
                    "player", "antrenman", "training", "turnuva", "tournament",
                    "puan durumu", "ozet", "özet", "highlights", "skor",
                    "forma", "stadyum", "stadium"),
        "sinyal": {"skor": 2.5, "dakika": 1.5},
        "karsit": ("tarif", "masal", "hisse"),
    },
    "yasam.emlak": {
        "ad": "Emlak",
        "anahtar": ("emlak", "real estate", "daire", "apartment", "villa",
                    "ev turu", "house tour", "konut", "housing", "kiralik",
                    "kiralık", "for rent", "satilik", "satılık", "for sale",
                    "tapu", "metrekare", "oda", "salon", "mimari", "interior",
                    "ic mimari", "iç mimari", "dekorasyon"),
        "sinyal": {"emlak_olcu": 2.5, "para": 1.0},
        "karsit": ("tarif", "cinayet", "masal"),
    },
    "yasam.otomotiv": {
        "ad": "Otomotiv",
        "anahtar": ("otomobil", "araba", "car", "otomotiv", "automotive",
                    "motor", "engine", "beygir", "horsepower", "tork",
                    "torque", "surus", "sürüş", "drive", "sasi", "şasi",
                    "elektrikli arac", "elektrikli araç", "electric vehicle",
                    "suv", "sedan", "pist", "track", "hizlanma", "hızlanma",
                    "0-100", "test surusu", "test sürüşü"),
        "sinyal": {"model_no": 1.5, "skor": 0.5},
        "karsit": ("tarif", "masal"),
    },
    "yasam.moda": {
        "ad": "Moda / stil",
        "anahtar": ("moda", "fashion", "stil", "style", "kombin", "outfit",
                    "koleksiyon", "collection", "podyum", "runway", "tasarimci",
                    "tasarımcı", "designer", "giyim", "clothing", "trend",
                    "lookbook", "guzellik", "güzellik", "beauty", "makyaj",
                    "makeup"),
        "sinyal": {},
        "karsit": ("tarif", "cinayet", "hisse"),
    },
    "yasam.saglik_fitness": {
        "ad": "Saglik / fitness",
        "anahtar": ("fitness", "antrenman programi", "antrenman programı",
                    "workout", "egzersiz", "exercise", "kas", "muscle",
                    "kardiyo", "cardio", "beslenme", "nutrition", "diyet",
                    "diet", "kilo", "weight loss", "saglik", "sağlık",
                    "health", "bagisiklik", "bağışıklık"),
        "sinyal": {"adim": 0.5, "olcu": 0.5},
        "karsit": ("cinayet", "hisse"),
    },

    # ───────────────────────── KULTUR / SOSYAL ─────────────────────────
    "kultur.muzik": {
        "ad": "Muzik",
        "anahtar": ("muzik", "müzik", "music", "sarki", "şarkı", "song",
                    "album", "albüm", "beste", "composer", "besteci",
                    "orkestra", "orchestra", "konser", "concert", "enstruman",
                    "enstrüman", "instrument", "melodi", "melody", "ritim",
                    "rhythm", "sanatci", "sanatçı", "musician", "gitar",
                    "piyano", "playlist"),
        "sinyal": {},
        "karsit": ("tarif", "cinayet", "hisse"),
    },
    "kultur.sanat": {
        "ad": "Sanat / kultur",
        "anahtar": ("sanat", "art", "resim", "painting", "heykel",
                    "sculpture", "muze", "müze", "museum", "sergi",
                    "exhibition", "ressam", "painter", "edebiyat",
                    "literature", "siir", "şiir", "poetry", "tiyatro",
                    "theatre", "kultur", "kültür", "culture", "gelenek",
                    "tradition", "festival"),
        "sinyal": {},
        "karsit": ("tarif", "hisse", "unboxing"),
    },
    "kultur.podcast": {
        "ad": "Podcast / sohbet",
        "anahtar": ("podcast", "sohbet", "roportaj", "röportaj", "interview",
                    "konuk", "guest", "bolum", "bölüm", "episode",
                    "mikrofon", "yayin", "yayın", "stream", "soru cevap",
                    "q&a"),
        "sinyal": {"diyalog": 1.0},
        "karsit": ("tarif", "4k"),
    },
    "kultur.listicle": {
        "ad": "Listicle / siralama",
        "anahtar": ("en iyi", "best of", "top 10", "top 5", "siralama",
                    "sıralama", "ranking", "liste", "list", "madde",
                    "10 sey", "10 şey", "things you", "bilmeniz gereken"),
        "sinyal": {"adim": 1.0},
        "karsit": ("tarif",),
    },
}

# Aile duzeyinde insan okunur adlar (yol'un ilk parcasi)
AILE_AD = {
    "belgesel": "Belgesel",
    "seyahat": "Seyahat",
    "egitim": "Egitim / aciklayici",
    "hikaye": "Hikaye",
    "urun": "Urun",
    "yasam": "Yasam",
    "kultur": "Kultur / sosyal",
}

# ⚠ GERIYE UYUMLULUK KOPRUSU — pipeline'in bildigi BES etikete indirger.
# `girdi_analizi.TUR_SINYALI` ve `GORSEL_STRATEJISI` HIC DEGISMEDI.
ESKI_ETIKET = {
    "belgesel": "belgesel",
    "seyahat": "seyahat",
    "egitim": "aciklayici",
    "hikaye": "hikaye",
    "urun": "urun",
    "yasam": "aciklayici",     # yemek/spor/emlak/otomotiv: gercek goruntu + anlatim
    "kultur": "belgesel",      # muzik/sanat/podcast: gercek goruntu agirlikli
}

# ═══════════════════════════ ESIKLER ═══════════════════════════
# ⚠ Keyfi degil, davranisi belirledikleri icin ACIKCA sabit ve testle kilitli.
KANIT_ESIGI = 2          # bu kadar kanit birimi altinda karar VERILMEZ
KESIN_ESIGI = 0.60       # bunun ustunde "kesin"
ZAYIF_ESIGI = 0.40       # bunun altinda "belirsiz"
MELEZ_MARJI = 0.25       # 1. ve 2. aday bu kadar yakinsa "melez"

# ⚠ TURKCE EK TOLERANSI — olculdu, tasarim acigiydi:
#   terim "kara delik" metindeki "kara delikler"e UYMUYORDU
#   terim "teori"      metindeki "teorisi"e       UYMUYORDU
#   terim "arastirmacilar" metindeki "arastirmacilarinin"e UYMUYORDU
# Turkce eklemeli bir dil; kati kelime siniri sozlugun yarisini korlestiriyordu.
# COZUM: SOL sinir kati kalir (kelime ORTASINDA eslesme yok), SAG tarafta
# sinirli ek toleransi verilir.
# ⚠ NEDEN SINIRLI: tolerans serbest olsaydi "kek" -> "kekik", "gol" -> "golge"
# gibi yanlis pozitifler gelirdi. Bu yuzden kisa terimlerde tolerans YOK.
SON_EK_TAVANI = 6        # en fazla kac harflik ek yutulur
EK_MIN_UZUNLUK = 5       # bu uzunlugun ALTINDAKI terimlerde ek TOLERANSI YOK

_SOL = r"(?<![0-9a-zà-ÿğüşıöç])"
_SAG = r"(?![0-9a-zà-ÿğüşıöç])"


def _gecti(terim: str, metin: str) -> bool:
    t = re.escape(terim)
    if len(terim) >= EK_MIN_UZUNLUK:
        desen = "%s%s[a-zà-ÿğüşıöç]{0,%d}%s" % (_SOL, t, SON_EK_TAVANI, _SAG)
    else:
        desen = "%s%s%s" % (_SOL, t, _SAG)
    return re.search(desen, metin) is not None


def kapsam_ozeti() -> dict:
    """Agacin GERCEK kapsami — 'her konsepti biliyoruz' iddiasi kurmamak icin."""
    aileler = sorted({y.split(".")[0] for y in AGAC})
    return {
        "aile": len(aileler),
        "aileler": aileler,
        "dal": len(AGAC),
        "anahtar": sum(len(d["anahtar"]) for d in AGAC.values()),
        "sinyal": len(SINYAL),
        "sinyal_bagi": sum(len(d["sinyal"]) for d in AGAC.values()),
        "karsit": sum(len(d["karsit"]) for d in AGAC.values()),
    }


def sinyalleri_olc(metin: str) -> dict:
    """Metnin BICIMINDEN sayilabilir kanitlar. Sifir olanlar dislanir."""
    m = str(metin or "")
    olcum = {}
    for ad, fn in SINYAL.items():
        try:
            n = int(fn(m))
        except Exception:
            n = 0
        if n:
            olcum[ad] = n
    return olcum


def dal_puanla(metin: str, olcum: dict = None) -> dict:
    """Her dal icin (puan, kanit, ayrinti). Tamamen deterministik.

    Puan iki bacakli:
      - anahtar isabeti: her TEKIL anahtar 1 puan (tavan 4 — uzun metin
        tek dali sisirmesin)
      - sinyal: agirlik x min(sayim, 3)
      - karsit: her isabet -2 puan (yanlis pozitif korumasi)
    """
    d = " " + str(metin or "").lower() + " "
    olcum = sinyalleri_olc(metin) if olcum is None else olcum
    sonuc = {}
    for yol, dal in AGAC.items():
        vurgun = [a for a in dal["anahtar"] if _gecti(a.lower(), d)]
        anahtar_puan = float(min(len(vurgun), 4))
        sinyal_puan, sinyal_ayrinti = 0.0, {}
        for ad, agirlik in dal["sinyal"].items():
            n = olcum.get(ad, 0)
            if n:
                p = float(agirlik) * min(n, 3)
                sinyal_puan += p
                sinyal_ayrinti[ad] = {"sayim": n, "puan": round(p, 2)}
        karsit = [k for k in dal["karsit"] if _gecti(k.lower(), d)]
        puan = anahtar_puan + sinyal_puan - 2.0 * len(karsit)
        # Kanit birimi: kac BAGIMSIZ isaret var (puan degil, SAYI)
        kanit = len(vurgun) + len(sinyal_ayrinti)
        sonuc[yol] = {
            "puan": round(max(0.0, puan), 2),
            "kanit": kanit,
            "anahtar_isabet": vurgun[:6],
            "sinyal_isabet": sinyal_ayrinti,
            "karsit_isabet": karsit,
        }
    return sonuc


def guven_hesapla(p1: float, p2: float, kanit: int) -> float:
    """Guven = taban + marj katkisi + kanit katkisi. Formul ACIK, uydurma yok.

    - marj  : (p1 - p2) / p1  — ikinci aday ne kadar uzakta
    - kanit : kac BAGIMSIZ isaret var (5'te doyar)
    Tavan 0.95: hicbir deterministik siniflandirma 'kesin dogru' degildir.
    """
    if p1 <= 0:
        return 0.0
    marj = max(0.0, (p1 - max(0.0, p2)) / p1)
    return round(min(0.95, 0.30 + 0.45 * marj + 0.20 * (min(kanit, 5) / 5.0)), 2)


def siniflandir(metin: str, *, model_coz=None, aday_sayisi: int = 3) -> dict:
    """Hiyerarsik konsept tespiti. AG YOK; `model_coz` verilmezse %100 deterministik.

    Donus sozlesmesi:
        yol         : "aile.tur" ya da "belirsiz"
        aile / tur  : ayrisik parcalar ("" olabilir)
        ad          : insan okunur ad
        guven       : 0.0-0.95
        durum       : kesin | melez | zayif | belirsiz
        ikincil     : melezde ikinci dal (yoksa None)
        adaylar     : [(yol, puan, kanit)] — ilk `aday_sayisi` tanesi
        gerekce     : neden bu karar (olculen sayilarla)
        kanit       : toplam bagimsiz isaret
        sinyaller   : olculen yapisal sinyaller
        eski_etiket : eski BES etiketten biri (geriye uyumluluk)
        kaynak      : "deterministik" | "model"

    ⚠ `model_coz(metin, adaylar)` YALNIZCA durum belirsiz/melez ise ve
    cagrilabilir verilmisse cagrilir. Donusu ADAY LISTESI DISINDAYSA YOK SAYILIR.
    """
    olcum = sinyalleri_olc(metin)
    puanlar = dal_puanla(metin, olcum)
    sirali = sorted(puanlar.items(), key=lambda kv: (-kv[1]["puan"], kv[0]))
    adaylar = [(y, v["puan"], v["kanit"]) for y, v in sirali[:max(1, aday_sayisi)]]

    p1_yol, p1 = sirali[0][0], sirali[0][1]["puan"]
    p2 = sirali[1][1]["puan"] if len(sirali) > 1 else 0.0
    kanit = sirali[0][1]["kanit"]

    temel = {
        "adaylar": adaylar,
        "kanit": kanit,
        "sinyaller": olcum,
        "kapsam": kapsam_ozeti(),
        "kaynak": "deterministik",
        "model_kullanildi": False,
    }

    # ── Kanit yetersiz: ZORLA ETIKET YOK ──
    if p1 <= 0 or kanit < KANIT_ESIGI:
        temel.update({
            "yol": "belirsiz", "aile": "", "tur": "", "ad": "Belirsiz",
            "guven": 0.0, "durum": "belirsiz", "ikincil": None,
            "eski_etiket": "belirsiz",
            "gerekce": (f"kanit yetersiz ({kanit} bagimsiz isaret < "
                        f"{KANIT_ESIGI}); zorla tur secilmedi"),
        })
        return _model_dene(temel, metin, model_coz)

    guven = guven_hesapla(p1, p2, kanit)
    marj = (p1 - p2) / p1 if p1 else 0.0
    ikincil = sirali[1][0] if (len(sirali) > 1 and p2 > 0) else None

    if guven < ZAYIF_ESIGI:
        durum = "belirsiz"
    elif marj < MELEZ_MARJI and ikincil and p2 > 0:
        durum = "melez"
    elif guven >= KESIN_ESIGI:
        durum = "kesin"
    else:
        durum = "zayif"

    aile, _, tur = p1_yol.partition(".")
    ay = puanlar[p1_yol]
    temel.update({
        "yol": p1_yol if durum != "belirsiz" else "belirsiz",
        "aile": aile if durum != "belirsiz" else "",
        "tur": tur if durum != "belirsiz" else "",
        "ad": AGAC[p1_yol]["ad"] if durum != "belirsiz" else "Belirsiz",
        "guven": guven,
        "durum": durum,
        "ikincil": (ikincil if durum == "melez" else None),
        "eski_etiket": (ESKI_ETIKET.get(aile, "belirsiz")
                        if durum != "belirsiz" else "belirsiz"),
        "gerekce": (
            f"{p1_yol}: puan {p1} (2. {ikincil or '-'} {p2}), "
            f"kanit {kanit} = {len(ay['anahtar_isabet'])} anahtar "
            f"+ {len(ay['sinyal_isabet'])} yapisal sinyal"
            + (f", karsit {ay['karsit_isabet']}" if ay["karsit_isabet"] else "")),
    })
    return _model_dene(temel, metin, model_coz)


def _model_dene(sonuc: dict, metin: str, model_coz) -> dict:
    """Belirsiz/melez durumda SINIRLI model analizi. Ag bu modulde YOK.

    ⚠ KLAMP: model yalnizca `adaylar` listesinden secebilir. Liste disi cevap,
    bicimsiz cevap ya da istisna -> deterministik karar KORUNUR ve bu durum
    `model_notu` ile gorunur kilinir (sessiz gecis yok).
    """
    if model_coz is None or sonuc["durum"] not in ("belirsiz", "melez", "zayif"):
        return sonuc
    izinli = {y for y, _p, _k in sonuc["adaylar"]}
    try:
        cevap = model_coz(metin, list(sonuc["adaylar"]))
    except Exception as e:
        sonuc["model_notu"] = f"model hatasi, deterministik korundu: {str(e)[:60]}"
        return sonuc
    if not isinstance(cevap, dict) or cevap.get("yol") not in izinli:
        sonuc["model_notu"] = ("model aday listesi disinda cevap verdi, "
                               "YOK SAYILDI")
        return sonuc
    yol = cevap["yol"]
    aile, _, tur = yol.partition(".")
    try:
        mg = float(cevap.get("guven", 0.0))
    except Exception:
        mg = 0.0
    sonuc.update({
        "yol": yol, "aile": aile, "tur": tur, "ad": AGAC[yol]["ad"],
        "guven": round(min(0.90, max(0.0, mg)), 2),   # model 0.95'e CIKAMAZ
        "durum": "model",
        "eski_etiket": ESKI_ETIKET.get(aile, "belirsiz"),
        "kaynak": "model",
        "model_kullanildi": True,
        "model_notu": str(cevap.get("gerekce") or "")[:200],
    })
    return sonuc
