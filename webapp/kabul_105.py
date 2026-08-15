"""KABUL DEGERLENDIRICISI — `acceptance_105_high_edit`. FAZ Y-12.

90-120 sn "YUKSEK edit" kabul videosunun TEK kapisi. Her kriter DEGER
uzerinden olculur ve fail-closed'dir.

⚠ OLCULEN KUSUR (`Y12-VARLIK-DEGERE-ESIT-SAYILDI`) — bagimsiz denetim,
15 Agu 2026. Sentetik karsi ornekte:
    render_qa = WARN | fact kapsami 0.25 | video kapsami 0.25
    ayni kaynak en uzun 99 sn (tavan 8) | gecis turu 0 | J/L 0
    ducking OLCULMEDI
… iken `teslim.zincir_raporu(...)["tam"]` **True** dondu.

⚠ KOK NEDEN (kanit):
  1. `teslim.py:307-312` PRE-QA kanitini DEGERLERE degil dict VARLIGINA
     bakarak sayiyor (`isinstance(_pq.get(a), dict)`). `gercek_qa.olc`
     bu sozlukleri HER ZAMAN dondurdugu icin koruma yapisal olarak hep
     tatmin oluyor — icindeki degerler ne olursa olsun.
  2. `teslim.py:60` `QA_KABUL = kutuphane.KABUL_QA == ("PASS","WARN")`;
     `kutuphane.py` WARN'i teslim ediyor.
  3. `teslim.py:351` post_qa halkasi yalnizca durum etiketine bakiyor;
     olculen tek bir deger okumuyor.

── SOZLESME ──
  · ⚠ WARN BU PRESET ICIN KABUL DEGILDIR. Yalnizca PASS.
  · ⚠ OLCULMEMIS KRITER GECMIS SAYILMAZ. Deger yoksa/tur yanlissa kriter
    DUSER; "olculemedi -> gecti" yolu YOKTUR.
  · ⚠ SOZLUK VARLIGI KANIT DEGILDIR. Her kriter sayisal/mantiksal degeri
    esikle karsilastirir.
  · ⚠ J/L OLCUMU ARTEFAKTA BAGLIDIR: `jl.artefakt_sha256` teslim edilen
    MP4'un ozetiyle AYNI olmali ve `jl.kaynak == "render-sonrasi"`
    olmali. Bayat modul global'i (`hizli_render._JL_SON`) — ki render'dan
    ONCE okunuyor ve onceki isin degerini tasiyabiliyor — KANIT SAYILMAZ.
  · Kriterlerden BIRI bile duserse `kabul=False`.

⚠ Bu modul YALNIZCA hukum verir. Olcumu URETMEZ; olcum sozlugunu
uretmek hattin isidir. Boylece "kapi kendi girdisini uretiyor"
(self-fulfilling) sinifi kusur bu katmanda imkansizdir.
"""
from __future__ import annotations

import re
from typing import Optional

PRESET = "acceptance_105_high_edit"

# ⚠ WARN YOK. Bu preset icin tek kabul edilen QA hukmu PASS'tir.
KABUL_QA = ("PASS",)

# Bu dosyanin karar kodu — testler ve handoff bunu arar.
KARAR_KODU = "Y12-VARLIK-DEGERE-ESIT-SAYILDI"

# ── ESIKLER (tek yerde; koda gomulu ikinci deger yok) ──
COZUNURLUK = (1920, 1080)
FPS = 30.0
FPS_TOLERANS = 0.5
SURE_BANDI_SN = (90.0, 120.0)
HEDEF_TOLERANS = 0.12          # kullanici hedefine +-%12
VIDEO_KAPSAM_ASGARI = 1.0      # %100 lisansli gercek video
KAYNAK_TAVANI_SN = 8.0         # global: ayni kaynak <= 8 sn
KAYNAK_SES_TAVANI_DB = -60.0   # "mutlak 0" — sessizlik tabani
FACT_KAPSAM_ASGARI = 1.0       # her cekim 1 kabul edilmis primary_fact_id
KAPANIS_ASGARI = 0.60
GECIS_TURU_ASGARI = 3
JL_ASGARI = 2
SFX_ASGARI = 1
DUCKING_TAVANI_DB = -3.0       # gercek ducking en az 3 dB bastirmali
ORT_PLAN_BANDI_SN = (2.5, 4.5)

_SHA = re.compile(r"^[0-9a-f]{16,64}$")


# ─────────────────────────── OKUYUCULAR ───────────────────────────
# ⚠ Hepsi "olculmedi" ile "kotu deger"i AYIRT EDER: eksik/None/yanlis tur
# -> None doner ve kriter DUSER.

def _blok(olcum, ad: str) -> dict:
    d = olcum.get(ad) if isinstance(olcum, dict) else None
    return d if isinstance(d, dict) else {}


def _olculdu(blok: dict) -> bool:
    return blok.get("olculdu") is True


def _sayi(blok: dict, ad: str) -> Optional[float]:
    d = blok.get(ad)
    if isinstance(d, bool) or d is None:
        return None
    try:
        return float(d)
    except (TypeError, ValueError):
        return None


def _tam_sayi(blok: dict, ad: str) -> Optional[int]:
    f = _sayi(blok, ad)
    return None if f is None else int(f)


def _metin(blok: dict, ad: str) -> str:
    d = blok.get(ad)
    return d.strip() if isinstance(d, str) else ""


# ─────────────────────────── KRITERLER ───────────────────────────
# Her denetci `(gecti: bool, olculen: str)` doner. `gecti=False` ise
# `olculen` NEDEN dustugunu ACIKCA yazar (uydurma yok).

def _k_artefakt(o) -> tuple:
    a = _blok(o, "artefakt")
    ozet = _metin(a, "sha256")
    yol = _metin(a, "yol")
    if not _olculdu(a):
        return False, "artefakt olculmedi"
    if not _SHA.match(ozet):
        return False, f"artefakt ozeti gecersiz: {ozet[:16]!r}"
    if not yol:
        return False, "artefakt yolu bos"
    return True, f"{yol} sha={ozet[:12]}"


def _k_cozunurluk(o) -> tuple:
    v = _blok(o, "video")
    g, y = _tam_sayi(v, "genislik"), _tam_sayi(v, "yukseklik")
    if not _olculdu(v) or g is None or y is None:
        return False, "cozunurluk olculmedi"
    if (g, y) != COZUNURLUK:
        return False, f"{g}x{y} != {COZUNURLUK[0]}x{COZUNURLUK[1]}"
    return True, f"{g}x{y}"


def _k_fps(o) -> tuple:
    v = _blok(o, "video")
    f = _sayi(v, "fps")
    if not _olculdu(v) or f is None:
        return False, "fps olculmedi"
    if abs(f - FPS) > FPS_TOLERANS:
        return False, f"{f} != {FPS}"
    return True, f"{f}"


def _k_sure_bant(o) -> tuple:
    v = _blok(o, "video")
    s = _sayi(v, "sure_sn")
    if not _olculdu(v) or s is None:
        return False, "sure olculmedi"
    alt, ust = SURE_BANDI_SN
    if not (alt <= s <= ust):
        return False, f"{s:.1f} sn bant disi ({alt:.0f}-{ust:.0f})"
    return True, f"{s:.1f} sn"


def _k_hedef_sure(o) -> tuple:
    v = _blok(o, "video")
    s = _sayi(v, "sure_sn")
    h = _sayi(o if isinstance(o, dict) else {}, "hedef_sure_sn")
    if h is None or h <= 0:
        # ⚠ Hedef yoksa GECMIS SAYILMAZ: kullanici hedefi bu presetin
        # kabul sartidir, olculemiyorsa kabul edilemez.
        return False, "kullanici hedef suresi verilmedi"
    if s is None or not _olculdu(v):
        return False, "sure olculmedi"
    sapma = abs(s - h) / h
    if sapma > HEDEF_TOLERANS:
        return False, (f"hedef {h:.0f} sn, olculen {s:.1f} sn "
                       f"(sapma %{sapma * 100:.1f} > %{HEDEF_TOLERANS * 100:.0f})")
    return True, f"hedef {h:.0f} sn, sapma %{sapma * 100:.1f}"


def _k_video_kapsam(o) -> tuple:
    k = _blok(o, "kapsam")
    oran = _sayi(k, "video_orani")
    cekim, video_cekim = _tam_sayi(k, "cekim"), _tam_sayi(k, "video_cekim")
    if not _olculdu(k) or oran is None:
        return False, "video kapsami olculmedi"
    if oran < VIDEO_KAPSAM_ASGARI:
        return False, f"video orani {oran:.2f} < {VIDEO_KAPSAM_ASGARI:.2f}"
    if cekim is not None and video_cekim is not None and video_cekim != cekim:
        return False, f"{video_cekim}/{cekim} cekim gercek video"
    return True, f"oran {oran:.2f}, {video_cekim}/{cekim} cekim"


def _k_provenans(o) -> tuple:
    p = _blok(o, "provenans")
    eksik = p.get("eksik")
    asset_eksik = _tam_sayi(p, "asset_id_eksik")
    if not _olculdu(p):
        return False, "provenans olculmedi"
    if p.get("tam") is not True:
        return False, "provenans tam degil"
    if isinstance(eksik, list) and eksik:
        return False, f"eksik alan: {eksik[:4]}"
    if asset_eksik is None or asset_eksik > 0:
        return False, f"asset_id eksik: {asset_eksik}"
    return True, "tum varliklar kimlikli ve lisansli"


def _k_kaynak_tavan(o) -> tuple:
    k = _blok(o, "kaynak_kullanimi")
    en_uzun = _sayi(k, "en_uzun_sn")
    kimlik_eksik = _tam_sayi(k, "kimlik_eksik")
    if not _olculdu(k) or en_uzun is None:
        return False, "kaynak kullanimi olculmedi"
    # ⚠ Kimliksiz varlik tavan muhasebesinden KACAR; bu bir bypass'tir.
    if kimlik_eksik is None or kimlik_eksik > 0:
        return False, f"kimliksiz varlik: {kimlik_eksik} (tavan olculemez)"
    if en_uzun > KAYNAK_TAVANI_SN:
        return False, f"en uzun {en_uzun:.1f} sn > {KAYNAK_TAVANI_SN:.0f} sn"
    return True, f"en uzun {en_uzun:.1f} sn"


def _k_kaynak_ses(o) -> tuple:
    s = _blok(o, "kaynak_ses")
    db = _sayi(s, "rms_db")
    if not _olculdu(s):
        return False, "kaynak sesi olculmedi"
    # ⚠ BEYAN KANIT DEGILDIR: gercek olculen deger sart.
    if db is None:
        return False, "kaynak sesi beyan edildi ama OLCULMEDI"
    if db > KAYNAK_SES_TAVANI_DB:
        return False, f"{db:.1f} dB > {KAYNAK_SES_TAVANI_DB:.0f} dB (sizinti)"
    return True, f"{db:.1f} dB"


def _k_fact_kapsam(o) -> tuple:
    f = _blok(o, "fact")
    kapsam = _sayi(f, "kapsam")
    disi = _tam_sayi(f, "allowlist_disi")
    cekim, bagli = _tam_sayi(f, "cekim"), _tam_sayi(f, "bagli")
    if not _olculdu(f) or kapsam is None:
        return False, "fact kapsami olculmedi"
    if kapsam < FACT_KAPSAM_ASGARI:
        return False, f"kapsam {kapsam:.2f} < {FACT_KAPSAM_ASGARI:.2f}"
    # ⚠ Y-11 sozlesmesi: her cekim ALLOWLIST'ten TEK bir kabul edilmis
    # primary_fact_id tasir; benzerlikten tahmin YASAK.
    if disi is None or disi > 0:
        return False, f"allowlist disi fact_id: {disi}"
    if cekim is not None and bagli is not None and bagli != cekim:
        return False, f"{bagli}/{cekim} cekim fact'e bagli"
    return True, f"kapsam {kapsam:.2f}, {bagli}/{cekim} cekim"


def _k_bolum_yay(o) -> tuple:
    a = _blok(o, "anlati")
    eksik = a.get("eksik_halka")
    kapanis = _sayi(a, "kapanis_skoru")
    bolum = _tam_sayi(a, "bolum")
    if not _olculdu(a):
        return False, "anlati yayi olculmedi"
    if bolum is None or bolum < 1:
        return False, f"bolum sayisi: {bolum}"
    if not isinstance(eksik, list):
        return False, "eksik halka listesi olculmedi"
    if eksik:
        return False, f"eksik halka: {eksik[:5]}"
    if kapanis is None:
        return False, "kapanis olculmedi"
    if kapanis < KAPANIS_ASGARI:
        return False, f"kapanis skoru {kapanis:.2f} < {KAPANIS_ASGARI:.2f}"
    return True, f"{bolum} bolum, yay tam, kapanis {kapanis:.2f}"


def _k_gecis_tur(o) -> tuple:
    g = _blok(o, "gecis")
    n = _tam_sayi(g, "tur_sayisi")
    if not _olculdu(g) or n is None:
        return False, "gecis turleri olculmedi"
    if n < GECIS_TURU_ASGARI:
        return False, f"{n} tur < {GECIS_TURU_ASGARI}"
    return True, f"{n} tur"


def _k_jl(o) -> tuple:
    j = _blok(o, "jl")
    a = _blok(o, "artefakt")
    n = _tam_sayi(j, "sayi")
    kaynak = _metin(j, "kaynak")
    ozet = _metin(j, "artefakt_sha256")
    artefakt_ozet = _metin(a, "sha256")
    if not _olculdu(j) or n is None:
        return False, "J/L olculmedi"
    # ⚠ BAYAT OLCUM YASAK: deger render SONRASI ve TESLIM EDILEN
    # artefakttan gelmeli. `hizli_render._JL_SON` render'dan ONCE
    # okunuyor ve onceki isin degerini tasiyabiliyor.
    if kaynak != "render-sonrasi":
        return False, f"olcum kaynagi {kaynak!r} (render-sonrasi degil)"
    if not artefakt_ozet or ozet != artefakt_ozet:
        return False, (f"olcum baska artefakta ait "
                       f"({ozet[:12]!r} != {artefakt_ozet[:12]!r})")
    if n < JL_ASGARI:
        return False, f"{n} J/L < {JL_ASGARI}"
    return True, f"{n} J/L (render sonrasi, artefakta bagli)"


def _k_sfx_ducking(o) -> tuple:
    s = _blok(o, "sfx")
    d = _blok(o, "ducking")
    n = _tam_sayi(s, "semantik_sayi")
    db = _sayi(d, "derinlik_db")
    if not _olculdu(s) or n is None:
        return False, "SFX olculmedi"
    if n < SFX_ASGARI:
        return False, f"semantik SFX {n} < {SFX_ASGARI}"
    if not _olculdu(d):
        return False, "ducking OLCULMEDI"
    if db is None:
        return False, "ducking beyan edildi ama derinligi olculmedi"
    if db > DUCKING_TAVANI_DB:
        return False, f"ducking {db:.1f} dB > {DUCKING_TAVANI_DB:.0f} dB"
    return True, f"{n} SFX, ducking {db:.1f} dB"


def _k_ort_plan(o) -> tuple:
    r = _blok(o, "ritim")
    ort = _sayi(r, "ort_plan_sn")
    if not _olculdu(r) or ort is None:
        return False, "ortalama plan suresi olculmedi"
    alt, ust = ORT_PLAN_BANDI_SN
    if not (alt <= ort <= ust):
        return False, f"{ort:.2f} sn bant disi ({alt}-{ust})"
    return True, f"{ort:.2f} sn"


def _k_qa(o) -> tuple:
    q = _blok(o, "qa")
    on, son = _metin(q, "on").upper(), _metin(q, "son").upper()
    # ⚠ WARN KABUL DEGIL. Bu presette "gecti ama uyari var" diye bir
    # durum YOKTUR; olculmemis (bos) hukum de kabul degildir.
    if on not in KABUL_QA:
        return False, f"PRE-QA={on or 'olculmedi'} (yalniz PASS kabul)"
    if son not in KABUL_QA:
        return False, f"POST-QA={son or 'olculmedi'} (yalniz PASS kabul)"
    return True, "PRE-QA=PASS, POST-QA=PASS"


def _k_imzali_url(o) -> tuple:
    t = _blok(o, "teslim")
    url = _metin(t, "imzali_url")
    tenant = _metin(t, "tenant_id")
    beklenen = _metin(o if isinstance(o, dict) else {}, "tenant_id")
    if not url:
        return False, "imzali URL bos"
    if "sig=" not in url:
        return False, "URL IMZASIZ (sig= yok)"
    if not beklenen or tenant != beklenen:
        return False, f"tenant uyusmuyor ({tenant!r} != {beklenen!r})"
    return True, f"imzali, tenant={tenant}"


# ── KRITER SICILI: kod -> denetci. Kod tekrari YOK (test kilitler). ──
KRITERLER = (
    {"kod": "KABUL-ARTEFAKT", "ad": "teslim edilen artefakt kanitli",
     "denetci": _k_artefakt},
    {"kod": "KABUL-COZUNURLUK", "ad": "1920x1080", "denetci": _k_cozunurluk},
    {"kod": "KABUL-FPS", "ad": "30 fps", "denetci": _k_fps},
    {"kod": "KABUL-SURE-BANT", "ad": "90-120 sn", "denetci": _k_sure_bant},
    {"kod": "KABUL-HEDEF-SURE", "ad": "kullanici hedefine tolerans icinde",
     "denetci": _k_hedef_sure},
    {"kod": "KABUL-VIDEO-KAPSAM", "ad": "%100 lisansli gercek video",
     "denetci": _k_video_kapsam},
    {"kod": "KABUL-PROVENANS", "ad": "her asset_id + provenans tam",
     "denetci": _k_provenans},
    {"kod": "KABUL-KAYNAK-TAVAN", "ad": "global ayni kaynak <= 8 sn",
     "denetci": _k_kaynak_tavan},
    {"kod": "KABUL-KAYNAK-SES", "ad": "source audio gercek olculen 0",
     "denetci": _k_kaynak_ses},
    {"kod": "KABUL-FACT-KAPSAM", "ad": "her cekim 1 kabul edilmis fact",
     "denetci": _k_fact_kapsam},
    {"kod": "KABUL-BOLUM-YAY", "ad": "bolum yayi tam + guclu kapanis",
     "denetci": _k_bolum_yay},
    {"kod": "KABUL-GECIS-TUR", "ad": ">=3 gecis turu", "denetci": _k_gecis_tur},
    {"kod": "KABUL-JL", "ad": "render sonrasi olculen J/L >= 2",
     "denetci": _k_jl},
    {"kod": "KABUL-SFX-DUCKING", "ad": "semantik SFX + olculen ducking",
     "denetci": _k_sfx_ducking},
    {"kod": "KABUL-ORT-PLAN", "ad": "ortalama plan 2.5-4.5 sn",
     "denetci": _k_ort_plan},
    {"kod": "KABUL-QA", "ad": "PRE ve POST QA PASS (WARN kabul degil)",
     "denetci": _k_qa},
    {"kod": "KABUL-IMZALI-URL", "ad": "imzali URL dolu + dogru tenant",
     "denetci": _k_imzali_url},
)

KODLAR = tuple(k["kod"] for k in KRITERLER)


def degerlendir(olcum) -> dict:
    """Kabul hukmu ver. ⚠ ISTISNA FIRLATMAZ, ⚠ FAIL-CLOSED.

    Doner:
      {"preset", "kabul": bool, "kodlar": [...], "kriterler": [...],
       "neden": str, "artefakt_sha256": str}

    Bozuk/eksik girdi TUM kriterleri dusurur — "olculemedi -> gecti"
    yolu YOKTUR.
    """
    o = olcum if isinstance(olcum, dict) else {}
    kriterler, kodlar = [], []
    for k in KRITERLER:
        try:
            gecti, olculen = k["denetci"](o)
        except Exception as e:          # ⚠ Denetci patlarsa KRITER DUSER.
            gecti, olculen = False, f"denetci hatasi: {type(e).__name__}: {e}"
        kriterler.append({"kod": k["kod"], "ad": k["ad"],
                          "gecti": bool(gecti), "olculen": str(olculen)[:200]})
        if not gecti:
            kodlar.append(k["kod"])
    return {
        "preset": PRESET,
        "kabul": not kodlar,
        "kodlar": kodlar,
        "kriterler": kriterler,
        "neden": "" if not kodlar else "KABUL-YOK:" + ",".join(kodlar),
        "artefakt_sha256": _metin(_blok(o, "artefakt"), "sha256"),
        "is_id": _metin(o, "is_id"),
        "tenant_id": _metin(o, "tenant_id"),
    }


def ozet(sonuc: dict) -> str:
    """Insan okunur tek satir — log ve handoff icin."""
    s = sonuc if isinstance(sonuc, dict) else {}
    if s.get("kabul"):
        return f"KABUL ({PRESET}): {len(KRITERLER)}/{len(KRITERLER)} kriter PASS"
    dusen = [k for k in (s.get("kriterler") or []) if not k.get("gecti")]
    ayrinti = "; ".join(f"{k['kod']}={k['olculen']}" for k in dusen[:6])
    return (f"KABUL-YOK ({PRESET}): {len(dusen)}/{len(KRITERLER)} kriter "
            f"dustu — {ayrinti}")
