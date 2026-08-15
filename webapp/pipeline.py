#!/usr/bin/env python3
"""Vidrush Web — uretim hatti (EDIT STILI odakli).
Kullanici referans KARAKTER gorseli + hikaye metni + EDIT STILI verir.
Her edit stili gercek belgesel YT kanallarindan turetildi (tempo, gecis, footage orani,
overlay, art-direction). Sahneler stile gore AI gorsel VEYA gercek footage (YouTube/Pexels)
olur; opsiyonel Magnific ile HD upscale; edge-tts seslendirir; Remotion 720p render eder.
"""
import os
import sys
import json
import time
import shutil
import asyncio
import threading
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

# ⚠ KOK YOLU (Faz H, 12 Agu 2026) — URETIM DAVRANISI DEGISMEDI.
# Varsayilan `/opt/vidrush`: konteynerdeki yerlesim aynen korunur. `VIDRUSH_KOK`
# env'i YALNIZCA yerel gelistirme/test icin baska bir koku isaret ettirir.
# NEDEN GEREKLI: bu modul IMPORT ANINDA `os.makedirs("/opt/vidrush/...")`
# cagiriyordu; yerelde `PermissionError` veriyor ve `pipeline` hic import
# edilemiyordu. Bu yuzden gercek FastAPI ucu yerelde HIC test edilememisti.
KOK_YOL = os.environ.get("VIDRUSH_KOK", "/opt/vidrush")

sys.path.insert(0, KOK_YOL)
import uret as uretmod  # seslendir, altyazi_parcala (DIKKAT: bu dosyada 'uret' adli fonksiyon var,
                        # modulu takma adla al ki golgelenmesin)

import kaynak  # YT/Pexels footage + Magnific upscale
import arastirma_kopru  # Faz H: arastirma motorunu bu hatta baglar (bkz. modul basligi)
import qa_kopru         # Faz H: render sonrasi kalite kapisi (bkz. modul basligi)
import medya_kopru      # Faz I-6: Faz B medya avcisi (OPT-IN, varsayilan KAPALI)
import edit_kopru       # Faz I-10: EditorV2 plan orkestrasyonu (OPT-IN, KAPALI)
import kaynak_tavani    # Faz R-1d-g: ayni kaynak <=8 sn bolme plani

# ⚠ FAZ I-2c — BILESIK STIL PROFILI KOPRUSU (OPSIYONEL, HATTI COKERTMEZ).
# `stil_profili.py` (Faz I-2b) surumlu/bilesik profil kaydidir. Bu hat onu
# YALNIZCA eski `EDIT_STILLERI` sozlugunde BULUNMAYAN bir stil kimligi
# geldiginde kullanir. Eski kimlikler (sinematik-belgesel, anlati-video-essay,
# seyahat-belgeseli, veri-anlatisi, hizli-explainer) bu koddan HIC gecmez ->
# ESKI GIRDILERDE DAVRANIS AYNEN KORUNUR (testle kilitli).
# Modul yuklenemezse `None` kalir ve hat bugunku davranisina duser.
try:
    import stil_profili
except Exception as _sp_hata:  # pragma: no cover - ortam sorunu
    stil_profili = None
    print(f"  stil_profili yuklenemedi, yalnizca eski stil sozlugu "
          f"kullanilacak: {type(_sp_hata).__name__}", file=sys.stderr)

OPENAI_KEY = os.environ.get("OPENAI_KEY", "")
STUDYO = os.path.join(KOK_YOL, "render-studio")
PUBLIC = os.path.join(STUDYO, "public")
# ═══════════ EFEKT ATAMASI (7 Agu 2026) ═══════════
# Efektler.tsx kutuphanesi vardi ama motor KULLANMIYORDU. Atama LLM'e sorulmuyor:
#   (a) her sahne icin efekt sormak plan promptunu sisirir ve tutarsiz secim uretir
#   (b) deterministik atama BEDAVA ve tekrar uretilebilir
#
# Iki katman:
#   TEMEL  — stilin kimligi, HER sahnede acik. Olculen kanal profillerinden:
#            ZeroReports %86 koyu kare -> koyu grade + vinyet + grain
#            Atrium %61 koyu, %71 3D    -> grade + letterbox
#            NextGen/MadeVision parlak  -> agir grade YOK, sadece hafif grain
#            Auralis yavas/parlak       -> cok hafif grain
#   VURGU  — anlatim islevine gore SEYREK aksan (her sahnede degil).
EFEKT_TEMEL = {
    "seyahat-belgeseli": [{"ad": "grain", "siddet": 0.7}, {"ad": "vinyet", "siddet": 0.8}],
    "veri-anlatisi":     [{"ad": "grain", "siddet": 0.5}],
    "sinematik-belgesel": [{"ad": "grain", "siddet": 0.9}, {"ad": "vinyet", "siddet": 1.0},
                           {"ad": "kontrast-grade", "siddet": 1.1}],
    "anlati-video-essay": [{"ad": "grain", "siddet": 1.1}, {"ad": "vinyet", "siddet": 0.9},
                           {"ad": "sicak-grade", "siddet": 0.8}],
    "hizli-explainer":   [],
}
# Islev -> vurgu efekti. Bos olan islevlerde efekt YOK.
EFEKT_ISLEV = {
    "vurgu":       [{"ad": "sarsinti", "siddet": 1.1}],
    "gecmis":      [{"ad": "siyah-beyaz", "siddet": 0.85}, {"ad": "grain", "siddet": 1.4}],
    "karsilastir": [{"ad": "yon-blur", "siddet": 0.9}],
    "sonuc":       [{"ad": "yumusak-zoom", "siddet": 1.0}],
}
EFEKT_SEYREKLIK = float(os.environ.get("EFEKT_SEYREKLIK", "0.7"))


# ══ FAZ I-2d — BILESIK PROFILDEN GORSEL IMZA ══
# ⚠ KAPATILAN ACIK (§18'de olculmustu): `EFEKT_TEMEL` ve `GECIS_IMZASI`
# tablolari ESKI kimliklerle anahtarli. Yeni-nesil bir kimlik geldiginde ikisi
# de varsayilanina dusuyordu: efekt=0, gecis imzasi=yok. Yani tempo/footage
# profilden geliyor ama grain/vinyet/grade ve gecis imzasi GELMIYORDU —
# kullanicinin sebebini bilmedigi SESSIZ bir kalite kaybi.
#
# ⚠ BU KURALLAR OLCUM DEGIL, TURETME KARARIDIR. Kaynak: profilin kendi
# `palet`/`gecis` beyani. Eski tabloya karsi kalibre edildi (test kilitliyor):
#   belgesel-sinematik -> grain/vinyet/kontrast-grade  (eski sinematik-belgesel)
#   bilim-anlatisi     -> grain 0.5                    (eski veri-anlatisi)
#   explainer-hizli    -> efekt YOK                    (eski hizli-explainer)
#
# ⚠ Uretilen ADLAR yalnizca render tarafinin BILDIGI adlardir; bilinmeyen ad
# sessizce yok sayilirdi (hizli_render `_ef_v` sozlugu ve GECIS_IMZA_FFMPEG).
GECERLI_EFEKT_ADI = ("grain", "vinyet", "siyah-beyaz", "kontrast-grade",
                     "sicak-grade", "soguk-grade")
GECERLI_GECIS_IMZA = ("karartma", "flash", "whip")

# `stil_profili` gecis turu -> render imzasi. 4 turun HEPSI eslenmis;
# eslenmeyen bir tur gelirse imza URETILMEZ (uydurma yok).
BILESIK_GECIS_IMZA = {
    "hard-cut": "karartma",    # sert kesme stilinde SEYREK karartma aksani
    "crossfade": "karartma",   # render tarafinda karartma = crossfade + dip
    "whip": "whip",
    "karisik": "flash",
}

# palet.grade icindeki anahtar -> renk/doku katmani. SIRA ONEMLI:
# "soguk-karanlik" hem "soguk" hem "karanlik" tasir; zengin olan once gelir.
_GRADE_KURALI = (
    ("vintage", (("grain", 1.1), ("sicak-grade", 0.8)), True),
    ("karanlik", (("grain", 0.9), ("vinyet", 1.0), ("soguk-grade", 0.9)), True),
    ("teal-orange", (("grain", 0.9), ("vinyet", 0.9),
                     ("kontrast-grade", 1.0)), True),
    # Parlak/temiz gorunum: DOKU YOK (eski `hizli-explainer` bos listesiyle
    # ayni ruh). `dokusuz=True` kontrast kuralini da bastirir.
    ("flat", (), False),
    ("temiz", (), False),
    ("pastel", (("sicak-grade", 0.5),), False),
    ("dogal", (("grain", 0.7), ("vinyet", 0.8)), True),
    ("sicak", (("sicak-grade", 0.8),), True),
    ("soguk", (("soguk-grade", 0.9),), True),
)


def _efekt_birlestir(hedef: list, ad: str, siddet: float) -> None:
    """Ayni efekt iki kez girmesin; siddeti YUKSEK olan kazanir."""
    if ad not in GECERLI_EFEKT_ADI:
        return
    for e in hedef:
        if e["ad"] == ad:
            e["siddet"] = max(float(e.get("siddet") or 0), float(siddet))
            return
    hedef.append({"ad": ad, "siddet": float(siddet)})


def bilesik_gorsel_imza(ek_profil) -> dict:
    """`_profil`ten efekt temeli + gecis imzasi turet (Faz I-2d).

    Donus: {"efektler": [...], "gecis_imza": str, "gecis_oran": float,
            "gerekce": [...], "uygulandi": bool}

    ⚠ HER KARAR IZLENEBILIR: `gerekce` hangi alanin hangi efekti dogurdugunu
    tek tek yazar. Kara kutu yok.
    ⚠ ISTISNA FIRLATMAZ: bozuk/eksik profilde `uygulandi=False` doner ve
    cagiran taraf ESKI tabloya duser (gerileme yok).
    """
    sonuc = {"efektler": [], "gecis_imza": "", "gecis_oran": 0.0,
             "gerekce": [], "uygulandi": False}
    try:
        ek = ek_profil if isinstance(ek_profil, dict) else {}
        palet = ek.get("palet") if isinstance(ek.get("palet"), dict) else {}
        gecis = ek.get("gecis") if isinstance(ek.get("gecis"), dict) else {}
        if not palet and not gecis:
            sonuc["gerekce"].append("profilde palet/gecis blogu yok")
            return sonuc

        # ── EFEKT TEMELI ──
        grade = str(palet.get("grade") or "").lower()
        kontrast = str(palet.get("kontrast") or "").lower()
        efektler, dokulu, eslesme = [], True, False
        for anahtar, cifter, doku in _GRADE_KURALI:
            if anahtar in grade:
                eslesme = True
                dokulu = dokulu and doku
                for ad, sid in cifter:
                    _efekt_birlestir(efektler, ad, sid)
                sonuc["gerekce"].append(
                    f"palet.grade '{grade}' -> '{anahtar}' kurali: "
                    + (", ".join(f"{a} {s}" for a, s in cifter) or "doku yok"))
        if kontrast == "yuksek" and dokulu:
            for ad, sid in (("kontrast-grade", 1.1), ("grain", 0.9),
                            ("vinyet", 0.9)):
                _efekt_birlestir(efektler, ad, sid)
            sonuc["gerekce"].append(
                "palet.kontrast 'yuksek' -> kontrast-grade 1.1, grain 0.9, "
                "vinyet 0.9")
        elif kontrast == "yuksek":
            sonuc["gerekce"].append(
                "palet.kontrast 'yuksek' ama grade parlak/temiz -> doku "
                "eklenmedi (parlak gorunum korunur)")
        if not efektler and dokulu and grade:
            # Hicbir kural tutmadiysa HAFIF taban doku (eski `veri-anlatisi`
            # grain 0.5 ile ayni). Parlak/temiz gorunumde bu da eklenmez.
            _efekt_birlestir(efektler, "grain", 0.5)
            sonuc["gerekce"].append(
                f"palet.grade '{grade}' icin ozel kural yok -> taban grain 0.5")
        if not eslesme and not grade:
            sonuc["gerekce"].append("palet.grade bos -> efekt turetilmedi")
        sonuc["efektler"] = efektler

        # ── GECIS IMZASI ──
        tur = str(gecis.get("tur") or "").lower()
        imza = BILESIK_GECIS_IMZA.get(tur, "")
        try:
            oran = max(0.0, min(1.0, float(gecis.get("oran_pct") or 0) / 100.0))
        except (TypeError, ValueError):
            oran = 0.0
        if imza in GECERLI_GECIS_IMZA and oran > 0:
            sonuc["gecis_imza"], sonuc["gecis_oran"] = imza, oran
            sonuc["gerekce"].append(
                f"gecis.tur '{tur}' + oran %{oran * 100:.0f} -> imza '{imza}'")
        elif tur and not imza:
            sonuc["gerekce"].append(
                f"gecis.tur '{tur}' render tarafinda karsiliksiz -> imza yok")
        elif tur:
            sonuc["gerekce"].append(
                f"gecis.tur '{tur}' oran 0 -> imza yok (saf sert kesme)")

        sonuc["uygulandi"] = bool(sonuc["efektler"] or sonuc["gecis_imza"])
    except Exception as e:                  # hat COKERTMEZ, eski tabloya duser
        sonuc["gerekce"].append(f"turetme hatasi: {type(e).__name__}")
    return sonuc


def efekt_ata(edit_id: str, islev: str, indeks: int, ek_profil=None) -> list:
    """Sahnenin efekt listesi: stil temeli + (seyrek) islev vurgusu.
    Ayni sahne her uretimde AYNI efekti alir (indeks tabanli, rastgelelik yok).

    ⚠ FAZ I-2d: `ek_profil` verilirse ve ondan efekt TURETILEBILIYORSA temel
    oradan gelir. Verilmezse (eski kimlikler) `EFEKT_TEMEL` aynen kullanilir —
    eski davranis bit-bit korunur.
    """
    temel = None
    if ek_profil:
        _tur = bilesik_gorsel_imza(ek_profil)
        if _tur["efektler"]:
            temel = [dict(e) for e in _tur["efektler"]]
    if temel is None:
        temel = [dict(e) for e in EFEKT_TEMEL.get(edit_id, [])]
    vurgu = EFEKT_ISLEV.get(islev or "", [])
    # Seyreklik: islev eslesse bile hepsine degil (surekli efekt yorucu olur)
    if vurgu and (indeks * 6151 % 100) / 100.0 < EFEKT_SEYREKLIK:
        adlar = {e["ad"] for e in temel}
        for e in vurgu:
            if e["ad"] in adlar:          # ayni efekt iki kez girmesin; siddeti yukselt
                for t in temel:
                    if t["ad"] == e["ad"]:
                        t["siddet"] = max(t.get("siddet", 1), e.get("siddet", 1))
            else:
                temel.append(dict(e))
    return temel


# ── GECIS IMZASI (7 Agu 2026, 786 kesme olcumu) ──
# Olculen: sert-kesme %79.9. Susulu gecisler pratikte yok. Kanal imzalari:
#   ZeroReports karartma %23.1 | NavyDecoded flash %10.3 + whip %6.2 | Auralis %97.5 saf kesme
# Stil basina: (imza, oran). Oran kadar sahneye imza konur, gerisi SERT KESME.
# ⚠ FAZ Y-15: bu tablo artik SECIM KAYNAGI DEGIL. Tek imza ">=3 gecis
# turu"nu yapisal olarak imkansiz kiliyordu (`Y15-GECIS-IMZA-TEKIL`).
# Secim `GECIS_IMZALARI` (imza LISTESI) uzerinden yapilir; bu ad yalnizca
# GERIYE UYUM GORUNUMU olarak asagida ONDAN TURETILIR.


# ─────────────── FAZ Y-15 — >=3 DETERMINISTIK GECIS TURU ───────────────
# ⚠ OLCULEN KUSUR (`Y15-GECIS-IMZA-TEKIL`): `GECIS_IMZASI` her `edit_id`
#   icin TEK bir `(imza, oran)` demeti veriyordu. `gecis_imza_sec` ya o TEK
#   imzayi ya da bos string donebiliyordu; bos imza `hizli_render`'da 2
#   karelik fade (= gozle SERT KESME) oluyor. Yani bir iste uretilebilecek
#   EN FAZLA tur sayisi 2'ydi (hard-cut + tek imza) ve kabul sarti olan
#   ">=3 gecis turu" YAPISAL OLARAK IMKANSIZDI.
#   Ustelik `hizli_render.GECIS_IMZA_FFMPEG` uc tur tanimliyordu
#   (`karartma`/`flash`/`whip`) ama `whip` hicbir `edit_id`'de gecmedigi
#   icin ERISILEMEZ olu koddu.
# ⚠ COZUM: her stil icin bir imza LISTESI. Secim DETERMINISTIK kalir —
#   ayni (edit_id, indeks) her uretimde AYNI imzayi verir; rastgelelik YOK.
#   `oran` hala hard-cut/efektli dengesini korur (her gecis efektli olsaydi
#   ritim bozulurdu, referans kanallarda da boyle degil).
GECIS_TURU_ASGARI = 3          # hard-cut dahil, kabul sarti ile AYNI deger

GECIS_IMZALARI = {
    #                          efektli gecis orani, sirayla uygulanan imzalar
    "seyahat-belgeseli":  {"oran": 0.34, "imzalar": ("karartma", "whip")},
    "veri-anlatisi":      {"oran": 0.34, "imzalar": ("flash", "whip")},
    "sinematik-belgesel": {"oran": 0.34, "imzalar": ("karartma", "flash")},
    "anlati-video-essay": {"oran": 0.34, "imzalar": ("karartma", "flash")},
    "hizli-explainer":    {"oran": 0.40, "imzalar": ("flash", "whip")},
}


# ⚠ GERIYE UYUM GORUNUMU — tek kaynak `GECIS_IMZALARI`.
GECIS_IMZASI = {k: (v["imzalar"][0], v["oran"])
                for k, v in GECIS_IMZALARI.items()}


def gecis_imza_sec(edit_id: str, indeks: int, ek_profil=None) -> str:
    """Bu sahneye hangi gecis imzasi konacak? ⚠ DETERMINISTIK.

    Doner: imza adi ya da `""` (= hard-cut). Ayni (edit_id, indeks) her
    uretimde AYNI sonucu verir.

    ⚠ FAZ I-2d: `ek_profil` verilirse ve ondan imza TURETILEBILIYORSA o
    imza listenin BASINA alinir; boylece bilesik profil hala belirleyici
    olur ama tur cesitliligi KAYBOLMAZ.
    ⚠ Bilinmeyen `edit_id` icin imza URETILMEZ (uydurma yok) — hard-cut.
    """
    kayit = GECIS_IMZALARI.get(edit_id) or {}
    imzalar = list(kayit.get("imzalar") or ())
    oran = float(kayit.get("oran") or 0.0)
    if ek_profil:
        _tur = bilesik_gorsel_imza(ek_profil)
        _p_imza, _p_oran = _tur["gecis_imza"], _tur["gecis_oran"]
        if _p_imza:
            imzalar = [_p_imza] + [i for i in imzalar if i != _p_imza]
            oran = float(_p_oran or oran)
    if not imzalar or oran <= 0:
        return ""
    if (indeks * 4177 % 1000) / 1000.0 >= oran:
        return ""                      # hard-cut — ritim korunur
    # ⚠ Efektli gecisler imzalar arasinda DETERMINISTIK olarak donusur.
    return imzalar[(indeks * 7919) % len(imzalar)]


SFX_DIR = os.environ.get("SFX_DIR", os.path.join(KOK_YOL, "sfx"))

# Anlatim islevi -> hangi ses efekti. Bos = o islevde ses yok (cogu sahne sessiz kalir).
SFX_ISLEV = {
    "vurgu": "impact",
    "liste": "whoosh-kisa",
    "gecmis": "projektor",
    "sonuc": "riser",
    "soru": "ui",
    "karsilastir": "whoosh-hizli",
}
SFX_SEYREKLIK = float(os.environ.get("SFX_SEYREKLIK", "0.75"))   # ayni islevde bile hepsine degil

# ─────────────────── FAZ Y-14 — GERCEK SIDECHAIN DUCKING ───────────────────
# ⚠ OLCULEN KUSUR (`Y14-DUCKING-FILTRE-YOK`): `grep -rn sidechaincompress
#   webapp/` SIFIR eslesme veriyordu. "Ducking" hicbir ffmpeg zincirinde
#   YOKTU:
#     · `sfx_bindir` SFX'i anlatinin uzerine duz `amix=normalize=0` ile
#       bindiriyordu; anlati bastirilmiyor, efekt anlatinin UZERINE biniyordu.
#     · `editor/ses.py` `ducking_zarfi` yalnizca bir PLAN nesnesiydi; hicbir
#       komuta donusmuyordu.
#     · `stil_profili` her profil icin `ducking_db` beyan ediyordu (-4…-12);
#       bu deger HICBIR filtreye ulasmiyordu (sessiz kalite kaybi).
#     · `gercek_qa` durustce `{"olculdu": False}` donuyordu ama hukumsuzdu.
# ⚠ OLCULEN KUSUR (`Y14-SFX-OLCUM-KAYIP`): bindirilen SFX sayisi YALNIZCA
#   stderr'e basiliyordu; hicbir olcum sozlugune yazilmiyordu.
SFX_DUCKING_DB = float(os.environ.get("SFX_DUCKING_DB", "-9.0"))
KOD_SFX_DIZIN_YOK = "SFX-DIZIN-YOK"
KOD_SFX_BINDIRME_BASARISIZ = "SFX-BINDIRME-BASARISIZ"
KOD_SFX_NOKTA_YOK = "SFX-NOKTA-YOK"


def _sfx_sure_oku(yol: str) -> float:
    """SFX dosyasinin GERCEK suresi (ffprobe). Okunamazsa 0.0."""
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", yol],
            capture_output=True, text=True, timeout=20)
        return float((r.stdout or "0").strip() or 0.0)
    except (OSError, ValueError, subprocess.SubprocessError):
        return 0.0


def _ducking_orani(ducking_db: float) -> float:
    """Hedef bastirma derinliginden `sidechaincompress` orani.

    ⚠ Yaklasik ve BELGELI: esik -26 dBFS civarinda, anlati tepe seviyesi
    esigi ~`d` dB asiyor kabul edilir; `ratio` buna gore secilir. Deger
    UYDURMA degil, uygulanan parametredir — zarf bunu raporlar.
    """
    d = abs(float(ducking_db or 0.0))
    if d <= 0:
        return 1.0
    return round(min(20.0, max(1.5, 1.0 + d * 0.9)), 2)


def sfx_filtre_kur(parcalar: list, *, ducking_db: float = None) -> dict:
    """SFX + GERCEK ducking filtre zincirini kur. ⚠ ffmpeg CALISTIRMAZ.

    Zincir:
      [0:a]asplit -> anlati (mikse) + anlati (sidechain ANAHTARI)
      [n:a]adelay -> her SFX kendi baslangicina
      SFX'ler amix -> TEK bir SFX katmani
      [sfx][anahtar]sidechaincompress -> anlati konusurken SFX BASTIRILIR
      [anlati][sfx_duck]amix -> nihai [mix]

    ⚠ Saf fonksiyon: testler ffmpeg/medya olmadan zinciri dogrulayabilir.
    """
    db = SFX_DUCKING_DB if ducking_db is None else float(ducking_db)
    if not parcalar:
        return {"filtre": [], "ducking_db": db, "parametreler": {}}
    oran = _ducking_orani(db)
    par = {"threshold": 0.05, "ratio": oran, "attack": 5, "release": 250,
           "makeup": 1, "level_sc": 1}
    filt = ["[0:a]asplit=2[anlati][anahtar]"]
    etiketler = []
    for n, (bas, _y) in enumerate(parcalar, start=1):
        ms = int(round(float(bas) * 1000))
        etiketler.append(f"[s{n}]")
        filt.append(f"[{n}:a]adelay={ms}|{ms},volume=0.8[s{n}]")
    if len(parcalar) == 1:
        filt.append("[s1]anull[sfx]")
    else:
        filt.append(f"{''.join(etiketler)}amix=inputs={len(parcalar)}"
                    f":duration=longest:dropout_transition=0:normalize=0[sfx]")
    filt.append(
        f"[sfx][anahtar]sidechaincompress=threshold={par['threshold']}"
        f":ratio={par['ratio']}:attack={par['attack']}:release={par['release']}"
        f":makeup={par['makeup']}:level_sc={par['level_sc']}[sfxduck]")
    filt.append("[anlati][sfxduck]amix=inputs=2:duration=first"
                ":dropout_transition=0:normalize=0[mix]")
    return {"filtre": filt, "ducking_db": db, "parametreler": par}


def sfx_zarfi_kur(parcalar: list, *, ducking_db: float = None,
                  sure_okuyucu=None) -> list:
    """UYGULANAN ducking zarfi: `[(bas_sn, bit_sn, db), ...]`.

    ⚠ UYDURMA YOK: her aralik gercekten bindirilen bir SFX'in baslangici ve
    OLCULEN suresidir. Sure okunamazsa (0) o aralik YAZILMAZ — "olculemedi"
    bir aralik uretmez.
    ⚠ `db` UYGULANAN filtre derinligidir; akustik olcum iddiasi DEGILDIR.
    """
    db = SFX_DUCKING_DB if ducking_db is None else float(ducking_db)
    oku = sure_okuyucu or _sfx_sure_oku
    zarf = []
    for bas, yol in (parcalar or []):
        sure = float(oku(yol) or 0.0)
        if sure <= 0:
            continue
        zarf.append((round(float(bas), 3), round(float(bas) + sure, 3), db))
    return zarf


KOD_DUCKING_GAIN_OLCULMEDI = "DUCKING-GAIN-OLCULMEDI"

# ⚠ OLCULEN KUSUR (`Y14B-DUCKING-BEYAN-OLCUM-SANILDI`, denetim 15 Agu):
#   Y-14 gercek `sidechaincompress` filtresini kurdu (yon dogru), ama
#   zarfin ucuncu alanina DOGRUDAN `SFX_DUCKING_DB = -9.0` yaziliyordu.
#   Bu bir YAPILANDIRMA degeridir, akustik olcum DEGIL: `threshold`/`ratio`
#   secimi gercek gain reduction'in -9 dB olmasini GARANTI ETMEZ (giris
#   seviyesi, tepe/ortalama farki ve makeup sonucu degistirir). `gercek_qa`
#   bunu `derinlik_db` diye raporluyordu ve `kabul_105` "olculdu" sayip
#   GECIRIYORDU: filtre hic etki etmese bile kriter PASS verirdi.
# ⚠ COZUM: AYNI SFX stem'inin sidechain ONCESI ve SONRASI hali, GERCEK SFX
#   zaman pencerelerinde `astats` ile karsilastirilir. `yapilandirilmis_db`
#   ile `olculen_reduction_db` AYRI ALANLARDIR ve kabul YALNIZCA olculeni
#   okur.
import re as _re_y14b   # ⚠ modul basi importlari bu satirdan SONRA
_RMS_DESEN = _re_y14b.compile(
    r"RMS level dB:\s*(-?\d+(?:\.\d+)?|-?inf)", _re_y14b.I)
DUCKING_MAKS_PENCERE = int(os.environ.get("DUCKING_MAKS_PENCERE", "12"))


def _ffmpeg_kos(komut: list) -> dict:
    """Varsayilan kosucu. ⚠ Hata YUTULMAZ: `rc` cagirana doner."""
    try:
        r = subprocess.run(komut, capture_output=True, text=True, timeout=120)
        return {"rc": r.returncode, "stdout": r.stdout or "",
                "stderr": r.stderr or ""}
    except (OSError, subprocess.SubprocessError) as e:
        return {"rc": -1, "stdout": "", "stderr": f"{type(e).__name__}: {e}"}


def sfx_stem_filtresi(parcalar: list, *, ducking_db: float = None) -> dict:
    """OLCUM icin STEM-ONLY filtre grafigi. ⚠ TUM CIKISLAR TUKETILIR.

    ⚠ OLCULEN KUSUR (`Y14B-BAGLANMAMIS-CIKIS`, denetim): ilk surumde olcum
    komutu `sfx_filtre_kur`'un TAM grafigini kullaniyordu. O grafik
    `[anlati][sfxduck]amix...[mix]` uretir; olcum ise yalnizca `[sfx]` ve
    `[sfxduck]` map ediyordu. `[mix]` BAGLANMAMIS CIKIS olarak kalir ve
    GERCEK ffmpeg "Filter ... has an unconnected output" ile DUSER.
    Sentetik kosucu bunu gormedigi icin test yesil, uretim ise HER ZAMAN
    olcumsuz kalirdi (fail-closed ama ULASILAMAZ kriter).

    ⚠ Bu grafik yalnizca IKI cikis uretir ve ikisi de map edilir:
        [stem_on]  — sidechain ONCESI SFX katmani
        [sfxduck]  — sidechain SONRASI SFX katmani
    Anlati yalnizca sidechain ANAHTARI olarak tuketilir; `[mix]` YOKTUR.
    """
    db = SFX_DUCKING_DB if ducking_db is None else float(ducking_db)
    if not parcalar:
        return {"filtre": [], "ciktilar": (), "ducking_db": db}
    par = sfx_filtre_kur(parcalar, ducking_db=db)["parametreler"]
    filt = ["[0:a]anull[anahtar]"]
    etiketler = []
    for n, (bas, _y) in enumerate(parcalar, start=1):
        ms = int(round(float(bas) * 1000))
        etiketler.append(f"[s{n}]")
        filt.append(f"[{n}:a]adelay={ms}|{ms},volume=0.8[s{n}]")
    if len(parcalar) == 1:
        filt.append("[s1]anull[sfxpre]")
    else:
        filt.append(f"{''.join(etiketler)}amix=inputs={len(parcalar)}"
                    f":duration=longest:dropout_transition=0:normalize=0[sfxpre]")
    # ⚠ Ayni stem ikiye ayrilir: biri OLCUM tabani, digeri sidechain girdisi.
    filt.append("[sfxpre]asplit=2[stem_on][stem_sc]")
    filt.append(
        f"[stem_sc][anahtar]sidechaincompress=threshold={par['threshold']}"
        f":ratio={par['ratio']}:attack={par['attack']}:release={par['release']}"
        f":makeup={par['makeup']}:level_sc={par['level_sc']}[sfxduck]")
    return {"filtre": filt, "ciktilar": ("stem_on", "sfxduck"),
            "ducking_db": db, "parametreler": par}


def ducking_stem_komutu(video: str, parcalar: list, *, ducking_db: float,
                        stem_on: str, stem_son: str) -> list:
    """Sidechain ONCESI ve SONRASI SFX stem'lerini TEK kosuda uret.

    ⚠ Ikisi de AYNI grafik ve AYNI girdilerden turer; tek fark sidechain
    uygulanip uygulanmamasidir — olculen fark YALNIZCA ducking'e
    atfedilebilir.
    ⚠ `sfx_stem_filtresi` kullanilir (TAM miks grafigi DEGIL): boylece
    BAGLANMAMIS CIKIS kalmaz ve gercek ffmpeg dusmez.
    """
    girdi = ["-i", video]
    for _, y in (parcalar or []):
        girdi += ["-i", y]
    z = sfx_stem_filtresi(parcalar, ducking_db=ducking_db)
    if not z["filtre"]:
        return []
    return (["ffmpeg", "-y", "-loglevel", "error"] + girdi
            + ["-filter_complex", ";".join(z["filtre"]),
               "-map", "[stem_on]", "-vn", "-c:a", "pcm_s16le", stem_on,
               "-map", "[sfxduck]", "-vn", "-c:a", "pcm_s16le", stem_son])


def rms_olc(yol: str, bas: float, bit: float, *, kosucu=None):
    """Bir zaman penceresinin RMS seviyesi (dB). Olculemezse `None`.

    ⚠ 0 ya da -inf UYDURULMAZ; okunamayan pencere `None` doner ve
    cagiran onu olcum disi birakir.
    """
    kos = kosucu or _ffmpeg_kos
    r = kos(["ffmpeg", "-hide_banner", "-nostats", "-i", str(yol),
             "-af", f"atrim=start={float(bas):.3f}:end={float(bit):.3f},astats",
             "-f", "null", "-"]) or {}
    if int(r.get("rc", -1)) != 0:
        return None
    m = _RMS_DESEN.search(str(r.get("stderr") or "") + str(r.get("stdout") or ""))
    if not m:
        return None
    ham = m.group(1).lower()
    if "inf" in ham:
        return None
    try:
        return float(ham)
    except ValueError:
        return None


def ducking_gain_olcumu(stem_on: str, stem_son: str, zarf: list, *,
                        yapilandirilmis_db: float,
                        kosucu=None,
                        maks_pencere: int = DUCKING_MAKS_PENCERE) -> dict:
    """GERCEK gain reduction: pencere basina `rms_son - rms_on`.

    Doner: {"olculdu", "olculen_reduction_db", "p50_db", "p95_db",
            "pencere", "yapilandirilmis_db", "kod"}
    ⚠ Hicbir pencere olculemezse `olculdu: False` + stabil kod; 0 dB
    UYDURULMAZ ve `olculen_reduction_db` SAYI OLARAK SUNULMAZ.
    """
    yapi = float(yapilandirilmis_db)
    pencereler = [z for z in (zarf or [])
                  if isinstance(z, (list, tuple)) and len(z) >= 2][:maks_pencere]
    atlanan = max(0, len([z for z in (zarf or [])
                          if isinstance(z, (list, tuple)) and len(z) >= 2])
                  - len(pencereler))
    temel = {"olculdu": False, "olculen_reduction_db": None,
             "p50_db": None, "p95_db": None, "pencere": 0,
             "yapilandirilmis_db": yapi, "atlanan_pencere": atlanan,
             "kod": KOD_DUCKING_GAIN_OLCULMEDI}
    if not pencereler:
        return {**temel, "neden": "olculecek SFX penceresi yok"}
    farklar = []
    for z in pencereler:
        bas, bit = float(z[0]), float(z[1])
        a = rms_olc(stem_on, bas, bit, kosucu=kosucu)
        b = rms_olc(stem_son, bas, bit, kosucu=kosucu)
        if a is None or b is None:
            continue
        farklar.append(round(b - a, 2))
    if not farklar:
        return {**temel, "neden": "hicbir pencere olculemedi (astats)"}
    sirali = sorted(farklar)                      # en negatif (agir) basta
    p50 = sirali[len(sirali) // 2] if len(sirali) % 2 else \
        round((sirali[len(sirali) // 2 - 1] + sirali[len(sirali) // 2]) / 2.0, 2)
    p95 = sirali[max(0, int(round(0.05 * (len(sirali) - 1))))]
    if atlanan:
        # ⚠ SESSIZ KIRPMA YOK: kac pencerenin olculmedigi raporlanir.
        print(f"  ducking olcumu: {atlanan} pencere tavan ({maks_pencere}) "
              f"nedeniyle olculmedi", file=sys.stderr)
    return {"olculdu": True, "olculen_reduction_db": p50,
            "p50_db": p50, "p95_db": p95, "pencere": len(farklar),
            "yapilandirilmis_db": yapi, "atlanan_pencere": atlanan, "kod": ""}


def sfx_bindir(video: str, sahneler: list, is_dizini: str, *,
               ducking_db: float = None, sure_okuyucu=None,
               kosucu=None) -> tuple:
    """Sahne baslangiclarina ses efekti bindirir + GERCEK ducking uygular.

    Doner: `(video_yolu, olcum)`.
    ⚠ Y14-SFX-OLCUM-KAYIP: sayac artik yalnizca stderr'e degil, `olcum`
    sozlugune yazilir; `gercek_qa` ducking zarfini oradan alir.
    ⚠ Basarisiz olursa GIRDIYI aynen dondurur (video asla kaybolmaz) ve
    `olculdu: False` + STABIL KOD yazar — sessiz atlama YOK.

    Neden seyrek: olculen referans kanallarda her kesmede ses yok; her kesmeye
    ses koymak "tik-tak" eden amatör bir is cikarir. Islev eslesen sahnelerin
    %75'ine, ve ust uste iki sahneye konmaz.
    """
    db = SFX_DUCKING_DB if ducking_db is None else float(ducking_db)

    def _bos(kod, **ek):
        d = {"bindirilen": 0, "olculdu": False, "kod": kod,
             "ducking_zarfi": [], "ducking_db": db, "islev_dagilimi": {}}
        d.update(ek)
        return video, d

    if not sahneler:
        return _bos(KOD_SFX_NOKTA_YOK, neden="sahne yok")
    if not os.path.isdir(SFX_DIR):
        return _bos(KOD_SFX_DIZIN_YOK, neden=f"SFX_DIR yok: {SFX_DIR}")

    parcalar, dagilim, t, onceki_var = [], {}, 0.0, False
    for i, sh in enumerate(sahneler):
        islev = str(sh.get("islev") or "")
        ad = SFX_ISLEV.get(islev, "")
        yol = os.path.join(SFX_DIR, f"{ad}.wav") if ad else ""
        # Ilk sahneye ses koymuyoruz (video sesle acilmaz), ust uste iki sahneye de.
        if (ad and i > 0 and not onceki_var and os.path.exists(yol)
                and (i * 7919 % 100) / 100.0 < SFX_SEYREKLIK):
            parcalar.append((t, yol))
            dagilim[islev] = dagilim.get(islev, 0) + 1
            onceki_var = True
        else:
            onceki_var = False
        t += float(sh.get("sure") or 0)
    if not parcalar:
        return _bos(KOD_SFX_NOKTA_YOK, neden="islev eslesen sahne yok")

    parcalar = parcalar[:40]        # filter_complex girdi sinirini asmamak icin
    girdi = ["-i", video]
    for _, y in parcalar:
        girdi += ["-i", y]
    _z = sfx_filtre_kur(parcalar, ducking_db=db)
    cikti = os.path.join(is_dizini, "sesli.mp4")
    try:
        r = subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error"] + girdi
            + ["-filter_complex", ";".join(_z["filtre"]),
               "-map", "0:v", "-map", "[mix]",
               "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
               cikti],
            capture_output=True, text=True, timeout=1800)
    except (OSError, subprocess.SubprocessError) as e:
        return _bos(KOD_SFX_BINDIRME_BASARISIZ,
                    neden=f"{type(e).__name__}: {str(e)[:120]}")
    if r.returncode != 0 or not os.path.exists(cikti) \
            or os.path.getsize(cikti) < 1024:
        print(f"  {KOD_SFX_BINDIRME_BASARISIZ}: {r.stderr[-200:]}",
              file=sys.stderr)
        return _bos(KOD_SFX_BINDIRME_BASARISIZ, neden=r.stderr[-160:])

    zarf = sfx_zarfi_kur(parcalar, ducking_db=db, sure_okuyucu=sure_okuyucu)

    # ── FAZ Y-14b: GERCEK GAIN REDUCTION OLCUMU ──
    # ⚠ Y14B-DUCKING-BEYAN-OLCUM-SANILDI: yapilandirma degeri kanit degildir.
    # Ayni stem'in sidechain ONCESI/SONRASI hali gercek SFX pencerelerinde
    # karsilastirilir. Olculemezse `olculdu: False` + stabil kod.
    _stem_on = os.path.join(is_dizini, "sfx_stem_on.wav")
    _stem_son = os.path.join(is_dizini, "sfx_stem_son.wav")
    _kos = kosucu or _ffmpeg_kos
    _gain = {"olculdu": False, "olculen_reduction_db": None,
             "yapilandirilmis_db": db, "kod": KOD_DUCKING_GAIN_OLCULMEDI,
             "neden": "stem uretilemedi"}
    try:
        _sr = _kos(ducking_stem_komutu(video, parcalar, ducking_db=db,
                                       stem_on=_stem_on, stem_son=_stem_son))
        # ⚠ Y14B-BAGLANMAMIS-CIKIS: rc TEK BASINA yetmez. Iki stem de
        # GERCEKTEN yazilmis ve BOS DEGIL olmali; aksi halde olcum
        # "olculmedi" kalir (fail-closed).
        _stem_ok = all(os.path.exists(_p) and os.path.getsize(_p) > 0
                       for _p in (_stem_on, _stem_son))
        if int((_sr or {}).get("rc", -1)) == 0 and _stem_ok:
            _gain = ducking_gain_olcumu(_stem_on, _stem_son, zarf,
                                        yapilandirilmis_db=db, kosucu=kosucu)
        else:
            _neden = ("stem dosyasi yazilmadi/bos" if not _stem_ok
                      else str((_sr or {}).get("stderr"))[-160:])
            _gain = {"olculdu": False, "olculen_reduction_db": None,
                     "yapilandirilmis_db": db,
                     "kod": KOD_DUCKING_GAIN_OLCULMEDI, "neden": _neden}
            print(f"  {KOD_DUCKING_GAIN_OLCULMEDI}: {_neden}",
                  file=sys.stderr)
    except Exception as e:                                   # noqa: BLE001
        _gain = {"olculdu": False, "olculen_reduction_db": None,
                 "yapilandirilmis_db": db,
                 "kod": KOD_DUCKING_GAIN_OLCULMEDI,
                 "neden": f"{type(e).__name__}: {str(e)[:120]}"}
    finally:
        for _s in (_stem_on, _stem_son):
            try:
                os.remove(_s)
            except OSError:
                pass

    print(f"  ses efekti: {len(parcalar)} nokta bindirildi | ducking "
          f"yapilandirma {db:.1f} dB (ratio={_z['parametreler']['ratio']}) | "
          f"OLCULEN azalma "
          f"{_gain.get('olculen_reduction_db') if _gain.get('olculdu') else 'OLCULMEDI'}"
          f" dB ({_gain.get('pencere', 0)} pencere)", file=sys.stderr)
    return cikti, {
        "bindirilen": len(parcalar),
        "olculdu": True,
        "kod": "",
        "islev_dagilimi": dagilim,
        # ⚠ BEYAN ile OLCUM AYRI ALANLAR — kabul yalnizca olculeni okur.
        "yapilandirilmis_db": db,
        "ducking_parametreleri": _z["parametreler"],
        "ducking_zarfi": zarf,
        "ducking_olcum": _gain,
    }


CIKTI_DIR = os.environ.get("CIKTI_DIR", os.path.join(KOK_YOL, "webapp", "ciktilar"))
os.makedirs(CIKTI_DIR, exist_ok=True)

# ═══════════════ KANAL PROFILI (videolar ARASI tutarlilik) ═══════════════
# Sorun: capa (stil kilidi) is dizininde tutuluyordu ve is bitince SILINIYORDU
# -> her video kendi capasini sifirdan uretiyor -> 50 videoluk kanalda stil kayiyor.
# Cozum: profil = KALICI karakter + capa + kilit metinleri. Her videoda ayni referanslar
# enjekte edilir -> tum kanal ayni gorunur. Bu dizin ASLA is temizliginde silinmez.
PROFIL_DIR = os.environ.get("PROFIL_DIR", os.path.join(KOK_YOL, "webapp", "veri", "profiller"))
os.makedirs(PROFIL_DIR, exist_ok=True)
_PROFIL_RE = __import__("re").compile(r"^[A-Za-z0-9_-]{1,48}$")


def profil_yolu(pid: str) -> str:
    if not _PROFIL_RE.match(pid or ""):
        raise ValueError("gecersiz profil kimligi")
    return os.path.join(PROFIL_DIR, pid)


def profil_oku(pid: str) -> dict:
    """Profili diskten oku. Yoksa bos dict. Donen: ad, tur, edit, kar_kilit, stil_kilit,
    karakter/capa/stil dosya yollari (varsa)."""
    try:
        d = profil_yolu(pid)
        with open(os.path.join(d, "profil.json"), encoding="utf-8") as f:
            p = json.load(f)
    except Exception:
        return {}
    p["id"] = pid
    for ad, anahtar in (("karakter.png", "karakter_yol"), ("capa.png", "capa_yol"),
                        ("stil.png", "stil_yol")):
        y = os.path.join(profil_yolu(pid), ad)
        p[anahtar] = y if os.path.exists(y) else ""
    return p


def profil_yaz(pid: str, veri: dict):
    d = profil_yolu(pid)
    os.makedirs(d, exist_ok=True)
    mevcut = {}
    try:
        with open(os.path.join(d, "profil.json"), encoding="utf-8") as f:
            mevcut = json.load(f)
    except Exception:
        pass
    mevcut.update({k: v for k, v in veri.items() if v is not None})
    with open(os.path.join(d, "profil.json"), "w", encoding="utf-8") as f:
        json.dump(mevcut, f, ensure_ascii=False, indent=1)


def profil_listele() -> list:
    out = []
    try:
        for pid in sorted(os.listdir(PROFIL_DIR)):
            p = profil_oku(pid)
            if p:
                out.append({"id": pid, "ad": p.get("ad", pid), "tur": p.get("tur", ""),
                            "edit": p.get("edit", ""), "video_sayisi": p.get("video_sayisi", 0),
                            "kilitli": bool(p.get("capa_yol")),
                            "karakter_var": bool(p.get("karakter_yol")),
                            "palet": p.get("palet", ""), "arkaplan": p.get("arkaplan", ""),
                            "ses": p.get("ses", "")})
    except Exception:
        pass
    return out


def profil_capa_kilitle(pid: str, kaynak_png: str) -> bool:
    """Profilin GORSEL CAPASI'ni sabitle. Bundan sonraki TUM videolar bu kareye kilitlenir
    -> kanal genelinde ayni stil/karakter. Bir kez kilitlenir, elle degistirilene kadar kalir."""
    try:
        if not (kaynak_png and os.path.exists(kaynak_png)):
            return False
        shutil.copy(kaynak_png, os.path.join(profil_yolu(pid), "capa.png"))
        return True
    except Exception as e:
        print(f"  profil capa kilitleme hata: {str(e)[:120]}", file=sys.stderr)
        return False


OAI_H = {"Authorization": f"Bearer {OPENAI_KEY}"}

# ─────────────── GORSEL MODELI (maliyet/kalite dengesi) ───────────────
# 1536x1024 medium ~1584 cikti token. Cikti fiyati: gpt-image-1 $40/1M, gpt-image-2 $30/1M,
# gpt-image-1-mini $8/1M  =>  ~$0.063 / ~$0.048 / ~$0.013 gorsel basina.
# ANIMASYON duz-vektor/stickman: mini yeterli (5x ucuz). DOCUMENTARY foto-gercekci:
# gpt-image-2 (hem su ankinden UCUZ hem karakter tutarliliginda en iyi).
# Env ile ezilebilir: IMAGE_MODEL (tum turler), IMAGE_MODEL_ANIM (sadece animasyon).
GORSEL_MODEL_DOC = os.environ.get("IMAGE_MODEL", "gpt-image-2")
GORSEL_MODEL_ANIM = os.environ.get("IMAGE_MODEL_ANIM", os.environ.get("IMAGE_MODEL", "gpt-image-1-mini"))


def _retry_after_bekle(r, d, taban=6, tavan=60):
    """429/5xx sonrasi ne kadar beklenecek. OpenAI 'Retry-After' basligini VERIRSE ona uy
    (dogru sure), yoksa ustel backoff. Boylece rate-limit'i asmadan tekrar deneriz."""
    ra = r.headers.get("retry-after") or r.headers.get("Retry-After") if r is not None else None
    if ra:
        try:
            return min(tavan, max(2.0, float(ra)) + 1.0)
        except Exception:
            pass
    return min(tavan, taban * (2 ** d))   # 6,12,24,48...


def _kota_hatasi_mi(r) -> bool:
    """Bakiye/harcama-limiti hatasi mi? (beklemek FAYDA ETMEZ — para/limit sorunu).
    OpenAI bunu 400 'billing_limit_user_error' veya 429 'insufficient_quota' ile dondurur."""
    try:
        e = (r.json().get("error", {}) or {})
        imza = f"{e.get('code','')} {e.get('type','')} {e.get('message','')}".lower()
        return any(k in imza for k in ("billing", "quota", "hard limit", "exceeded your current"))
    except Exception:
        return False


BAKIYE_MESAJI = ("OpenAI bakiyesi/harcama limiti doldu. platform.openai.com → Billing'den "
                 "kredi yükleyin veya Limits'ten aylık harcama limitini yükseltin. "
                 "(Hız limiti değil — beklemek çözmez.)")


# ─────────────────────────── GEMINI SAGLAYICI ───────────────────────────
# OpenAI kilitliyken (billing limit) tum hat Gemini uzerinden calisabilsin diye.
# SAGLAYICI=gemini -> planlama + gorsel Gemini'den; openai -> eski davranis.
GEMINI_KEY = os.environ.get("GEMINI_KEY", "")
if not GEMINI_KEY:   # konteyner yeniden yaratmadan kurulum: docker exec ile dosyaya yaz
    try:
        with open(os.path.join(KOK_YOL, "GEMINI_KEY")) as _f:
            GEMINI_KEY = _f.read().strip()
    except Exception:
        pass
# DIKKAT: eskiden "anahtar varsa varsayilan gemini" idi — GEMINI_KEY kurulunca TUM hat
# sessizce Gemini'ye donerdi. Artik global saglayici ACIKCA secilir (AI_SAGLAYICI=gemini);
# anahtarin varligi sadece UNLU MODU gibi is-bazli kullanimlari acar.
SAGLAYICI = os.environ.get("AI_SAGLAYICI", "openai").lower()

# ── GROK (xAI) — UNLU MODU icin: unlu benzerligine EN toleransli gorsel API ──
# console.x.ai'den anahtar; OpenAI-uyumlu uc (api.x.ai/v1). NOT: grok gorsel API'si
# REFERANS GORSEL almaz (text-to-image) -> unlu modunda tutarliligi ismin kendisi saglar.
XAI_KEY = os.environ.get("XAI_KEY", "")
if not XAI_KEY:   # konteyner yeniden yaratmadan kurulum
    try:
        with open(os.path.join(KOK_YOL, "XAI_KEY")) as _f:
            XAI_KEY = _f.read().strip()
    except Exception:
        pass


def grok_gorsel(prompt: str, hedef: str, deneme: int = 4) -> bool:
    """xAI Grok ile text-to-image (unlu modu). Basari: True; hata: False (cagiran atlar)."""
    if not XAI_KEY:
        return False
    for d in range(deneme):
        try:
            r = requests.post("https://api.x.ai/v1/images/generations",
                              headers={"Authorization": f"Bearer {XAI_KEY}"},
                              json={"model": os.environ.get("GROK_GORSEL_MODEL", "grok-imagine-image"),
                                    "prompt": prompt[:1024], "response_format": "b64_json"},
                              timeout=180)
            if r.status_code == 429:
                time.sleep(_retry_after_bekle(r, d)); continue
            if r.status_code >= 400:
                print(f"  grok gorsel hata {r.status_code}: {r.text[:200]}", file=sys.stderr)
                if r.status_code in (401, 402, 403):
                    # Kredi/anahtar bitti: TUM uretimi durdur (OpenAI bakiye kurtarmasi devreye
                    # girer, eldeki sahnelerle video tamamlanir — bosa deneme = bosa bekleme yok)
                    raise BakiyeHatasi("Grok (xAI) kredisi/yetkisi doldu — console.x.ai'den "
                                       "bakiye yukleyin.")
                time.sleep(5); continue
            import base64
            b64 = r.json()["data"][0]["b64_json"]
            with open(hedef, "wb") as f:
                f.write(base64.b64decode(b64))
            return True
        except Exception as e:
            print(f"  grok istisna: {str(e)[:160]}", file=sys.stderr)
            time.sleep(5)
    return False
GEM_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
GEM_METIN_MODEL = os.environ.get("GEMINI_TEXT_MODEL", "gemini-2.5-flash")
# ORTA kalite + en iyi fiyat: gemini-2.5-flash-image ("Nano Banana") $0.039/gorsel.
# Alternatifler: gemini-3.1-flash-image $0.067 (biraz daha iyi), 3.1-flash-lite $0.034,
# gemini-3-pro-image $0.134 (maksimum). GEMINI_IMAGE_MODEL env ile degistirilir.
GEM_GORSEL_MODEL = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")


def _gem_hata_kontrol(r):
    """Gemini bakiye/kota hatasini BakiyeHatasi'na cevir (retry anlamsiz)."""
    if r.status_code >= 400:
        t = r.text[:400].lower()
        if any(k in t for k in ("quota", "billing", "exceeded", "resource_exhausted")):
            raise BakiyeHatasi("Gemini bakiyesi/kotası doldu — Google AI Studio/Cloud "
                               "hesabına kredi yükleyin veya kotayı yükseltin.")


def gemini_chat(body: dict, timeout: int = 180, deneme: int = 5) -> dict:
    """OpenAI-sekilli 'body' alir, GEMINI'ye sorar, OpenAI-sekilli yanit doner.
    Boylece cagiran kodun (plan_uret, karakter_analiz, stil_analiz) hic degismesi gerekmez."""
    sistem, kullanici, gorseller = "", "", []
    for m in body.get("messages", []):
        ic = m.get("content")
        if isinstance(ic, list):          # vision mesaji (karakter/stil analizi)
            for p in ic:
                if p.get("type") == "text":
                    kullanici += p["text"] + "\n"
                elif p.get("type") == "image_url":
                    u = p["image_url"]["url"]
                    if u.startswith("data:"):
                        gorseller.append(u.split(",", 1)[1])
        elif m.get("role") == "system":
            sistem += str(ic) + "\n"
        else:
            kullanici += str(ic) + "\n"

    parts = [{"text": (sistem + "\n" + kullanici).strip()}]
    for b64 in gorseller:
        parts.append({"inline_data": {"mime_type": "image/png", "data": b64}})
    gcfg = {"temperature": body.get("temperature", 0.7),
            "maxOutputTokens": int(body.get("max_tokens", 8000))}
    if (body.get("response_format") or {}).get("type") == "json_object":
        gcfg["responseMimeType"] = "application/json"

    son = None
    for d in range(deneme):
        try:
            r = requests.post(f"{GEM_BASE}/{GEM_METIN_MODEL}:generateContent",
                              headers={"x-goog-api-key": GEMINI_KEY},
                              json={"contents": [{"parts": parts}], "generationConfig": gcfg},
                              timeout=timeout)
            _gem_hata_kontrol(r)
            if r.status_code in (429, 500, 502, 503, 504):
                son = RuntimeError(f"Gemini {r.status_code}")
                if d < deneme - 1:
                    time.sleep(_retry_after_bekle(r, d)); continue
                r.raise_for_status()
            r.raise_for_status()
            j = r.json()
            metin = ""
            for p in (j.get("candidates") or [{}])[0].get("content", {}).get("parts", []):
                metin += p.get("text", "")
            return {"choices": [{"message": {"content": metin}}]}
        except BakiyeHatasi:
            raise
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            son = e
            if d < deneme - 1:
                time.sleep(min(60, 6 * (2 ** d))); continue
    raise son or RuntimeError("gemini_chat basarisiz")


def gemini_gorsel(prompt: str, ref_yollar: list, hedef: str, deneme: int = 4) -> bool:
    """Gemini ile gorsel uret. ref_yollar: karakter/capa/stil referanslari (coklu referans
    -> karakter tutarliligi). Basarida hedef'e PNG yazar."""
    import base64
    parts = [{"text": prompt}]
    for y in ref_yollar:
        try:
            with open(y, "rb") as f:
                parts.append({"inline_data": {"mime_type": "image/png",
                                              "data": base64.b64encode(f.read()).decode()}})
        except Exception:
            pass
    for d in range(deneme):
        try:
            r = requests.post(f"{GEM_BASE}/{GEM_GORSEL_MODEL}:generateContent",
                              headers={"x-goog-api-key": GEMINI_KEY},
                              json={"contents": [{"parts": parts}]}, timeout=240)
            _gem_hata_kontrol(r)
            if r.status_code in (429, 500, 502, 503, 504) and d < deneme - 1:
                time.sleep(_retry_after_bekle(r, d)); continue
            r.raise_for_status()
            for p in (r.json().get("candidates") or [{}])[0].get("content", {}).get("parts", []):
                veri = (p.get("inline_data") or p.get("inlineData") or {}).get("data")
                if veri:
                    with open(hedef, "wb") as f:
                        f.write(base64.b64decode(veri))
                    return True
            print("  gemini gorsel: yanitta resim yok", file=sys.stderr)
        except BakiyeHatasi:
            raise
        except Exception as e:
            print(f"  gemini gorsel hata: {str(e)[:180]}", file=sys.stderr)
            time.sleep(5)
    return False



def altyazi_ayar_coz(girdi):
    """Altyazi ayari: JSON metni (tam ayar) VEYA sablon adi olabilir. Video.tsx ikisini de anlar.
    Bozuk JSON gelirse sablon adi gibi davranir; hicbiri yoksa varsayilan sablon."""
    g = (girdi or "").strip()
    if not g:
        return "beyaz-kontur"
    if g.startswith("{"):
        try:
            d = json.loads(g)
            return d if isinstance(d, dict) else "beyaz-kontur"
        except Exception:
            return "beyaz-kontur"
    return g


class BakiyeHatasi(RuntimeError):
    """Bakiye/limit hatasi. Retry ANLAMSIZ: hemen yukari firlar ki 40 sahne boyunca
    bosuna denenmesin ve o ana kadar URETILEN sahneler kurtarilabilsin."""
    pass


def oai_chat(body: dict, timeout: int = 180, deneme: int = 6) -> dict:
    """Metin cagrisi — DAYANIKLI. SAGLAYICI=gemini ise Gemini'ye yonlendirir (OpenAI kilitli
    olsa da calisir). 429/5xx/timeout'ta Retry-After'a uyup TEKRAR dener."""
    if SAGLAYICI == "gemini" and GEMINI_KEY:
        return gemini_chat(body, timeout=timeout)
    son_hata = None
    for d in range(deneme):
        try:
            r = requests.post("https://api.openai.com/v1/chat/completions",
                              headers=OAI_H, json=body, timeout=timeout)
            if r.status_code >= 400 and _kota_hatasi_mi(r):
                raise BakiyeHatasi(BAKIYE_MESAJI)   # 400/429 fark etmez: para/limit sorunu
            if r.status_code == 429:
                govde = r.text[:200].replace("\n", " ")
                print(f"  oai_chat 429 ({d+1}/{deneme}): {govde}", file=sys.stderr)
                son_hata = RuntimeError("OpenAI 429 (çok fazla istek — hız limiti)")
                if d < deneme - 1:
                    time.sleep(_retry_after_bekle(r, d)); continue
                raise son_hata
            if r.status_code in (500, 502, 503, 504):
                son_hata = RuntimeError(f"OpenAI {r.status_code}")
                if d < deneme - 1:
                    time.sleep(_retry_after_bekle(r, d)); continue
                r.raise_for_status()
            r.raise_for_status()
            return r.json()
        except (requests.exceptions.Timeout,
                requests.exceptions.ConnectionError,
                requests.exceptions.ChunkedEncodingError) as e:
            son_hata = e
            print(f"  oai_chat retry {d+1}/{deneme}: {str(e)[:120]}", file=sys.stderr)
            if d < deneme - 1:
                time.sleep(min(60, 6 * (2 ** d))); continue
    raise son_hata or RuntimeError("oai_chat basarisiz")


# ⚠ FAZ UI-5 — STABIL MEDYA HATA KODU.
# Belge/gercek-kaynak tabanli stillerde timeline medya turu %100 VIDEO'dur.
# Gercek video klip bulunamayan sahne AI STATIK GORSELE DUSMEZ; bu kodla
# bos birakilir ve neden kapsam boslugunda GORUNUR kalir. Sessiz dusus
# (zoom'lu statik kare) kullanici karariyla KALDIRILDI (15 Agu 2026).
MEDYA_VIDEO_YOK = "MEDYA-VIDEO-YOK"

# ⚠ FAZ Y-10 / Y10-HAVUZ-YETERSIZ — HER CEKIM DOGRULANMIS OLGUYA BAGLI.
# `qa_on` her cekim icin `FACT-BAGLANTI-YOK` (fail) verir, yani kapsam
# hedefi ZATEN %100'dur. Bu esik AYNI sozlesmeyi URETIMDEN ONCE uygular:
# yetersiz havuzla render'a girip ~10 dk sonra teslim kapisinda dusmek
# yerine, is BASTA ve NEDENIYLE durur. Env ile gevsetilebilir ama
# varsayilan qa_on ile TUTARLIDIR.
FACT_KAPSAM_ESIGI = float(os.environ.get("FACT_KAPSAM_ESIGI", "1.0"))

# ─────────────────────────── EDIT STILLERI ───────────────────────────
# Gercek belgesel kanallarindan turetilen 3 profesyonel kurgu profili.
# motion -> Remotion Video.tsx gecis modu; footage_pct -> gercek footage sahne orani;
# overlay -> kinetik baslik yogunlugu; gorsel_ek -> AI art-direction; mag -> Magnific profili.
EDIT_STILLERI = {
    "sinematik-belgesel": {
        "ad": "Sinematik Belgesel",
        "ozet": "BBC Earth / Nat Geo — yavaş, hard-cut, gerçek footage, orkestral",
        # ⚠ FAZ UI-5: timeline medya turu %100 VIDEO. AI statik gorsel
        # URETILMEZ; video bulunamayan sahne MEDYA_VIDEO_YOK ile bos
        # kalir (sessizce zoom slayta DUSULMEZ).
        "gorsel_yasak": True,
        "sahne_sn": 7, "kelime": 17, "footage_pct": 100, "overlay": "yok",
        "altyazi": "orta", "motion": "sinematik", "mag": "films_n_photography",
        "saha_etiketi": True, "etiket_pct": 24,
        "bolumler": True,   # bolum basligi + bolum bazli anlatim
        "gorsel_ek": ("cinematic wildlife/nature documentary still, shot on a cinema camera, "
                      "85mm telephoto, shallow depth of field, natural golden-hour light, high "
                      "dynamic range, rich saturated greens and blues, deep shadows, "
                      "photorealistic, absolutely no text, no graphics, no illustration"),
    },
    "anlati-video-essay": {
        "ad": "Anlatı Video-Essay",
        "ozet": "Johnny Harris / Vox Atlas — Ken Burns 2.0 push-in, analog texture, kinetik başlık",
        # ⚠ FAZ UI-5: timeline medya turu %100 VIDEO. AI statik gorsel
        # URETILMEZ; video bulunamayan sahne MEDYA_VIDEO_YOK ile bos
        # kalir (sessizce zoom slayta DUSULMEZ).
        "gorsel_yasak": True,
        "sahne_sn": 4, "kelime": 11, "footage_pct": 100, "overlay": "yogun",
        "altyazi": "orta", "motion": "anlati", "mag": "films_n_photography",
        "saha_etiketi": True, "etiket_pct": 28,
        "bolumler": True,   # bolum basligi + bolum bazli anlatim
        "gorsel_ek": ("photojournalistic documentary frame, warm faded film tones, subtle film "
                      "grain and light leaks, tactile analog texture (old paper / wood grain), "
                      "archival photo aesthetic, cinematic depth, muted vintage color grade"),
    },
    # ── SEYAHAT BELGESELI (5 Agu 2026, referans #12: @ImpossibleTravel38) ──
    # Olcum: 10 videodan 3'u kare kare olculdu (~1000 cekim). Medyan cekim 4.5-7.5 sn,
    # ortalama 7.5-12.7 sn — yani cok kisa kesmelerle uzun duran planlar karisik.
    # Diger 3 edit stilinden TEMEL farki: bu bir GORUNTU DERLEMESI. Karelerin tamami
    # gercek kamera goruntusu (drone hava cekimi + yer + makro) ve arsiv fotografi;
    # AI illustrasyon yok. KULLANICI KARARI (11 Agu 2026): "belgesel stilinde gorsel
    # kullanma, 0 gorsel olsun". Bu yuzden footage_pct 100 ve AI gorsele dusme YOK —
    # footage bulunamayan sahne, ulkeye capali genel klibe duser (bkz. _sahne_medya).
    # Sebep: 11 Agu ciktisinda AI gorseller belgesel dokusunu bozuyordu; referans
    # kanalda (@ImpossibleTravel38) tek kare AI gorsel yok.
    "seyahat-belgeseli": {
        "ad": "Seyahat Belgeseli (4K)",
        "ozet": "ImpossibleTravel — gerçek drone + yer görüntüsü derlemesi, yavaş anlatı, arşiv",
        # KULLANICI KARARI (7 Agu 2026): hicbir gorsel/video 8 sn'den fazla ekranda kalmasin.
        # Bu, olculen referansi GECERSIZ KILIYOR — referansin ortalama cekimi 12.5 sn ve
        # %29'u 12 sn'den uzun. Talep uzerine uygulandi.
        # 8 sn tavani altinda tutulabilen en yuksek ortalama 5.5 sn (bant dagilimi asagida):
        # bantlar 3.0 / 5.0 / 6.5 / 8.0 sn, agirliklar %32/%26/%14/%29 -> ortalama 5.5 sn.
        "sahne_sn": 5.5, "maks_sahne_sn": 8, "kelime": 15, "footage_pct": 100, "overlay": "yok",
        "gorsel_yasak": True,     # AI gorsel URETILMEZ; footage yoksa genel klip kullanilir
        "altyazi": "yok", "motion": "sinematik", "mag": "films_n_photography",
        "tempo": "cift-modlu",   # olculen dagilim: %33 kisa / %26 orta / %29 uzun
        "saha_etiketi": True, "etiket_pct": 25,
        "bolumler": True,   # bolum basligi + bolum bazli anlatim
        "gorsel_ek": ("photorealistic 4K travel documentary frame that must be indistinguishable "
                      "from real camera footage: either a high aerial drone view of coastline, "
                      "reef and settlement, or a ground-level handheld shot of local people at "
                      "work, or an extreme macro detail (sand, shells, hands, tools). Bright "
                      "tropical daylight, deep turquoise water, natural colour grade, real "
                      "lens depth of field and slight motion blur. Absolutely no illustration, "
                      "no 3D render, no text, no graphics, no map overlay"),
    },
    # ── VERI ANLATISI (5 Agu 2026, referans #13: @Neu "Broken Economics of Oil Tankers") ──
    # Olcum: 571 sn'lik videoda ffmpeg sahne-kesme esik 0.28'de SADECE 2 sert kesme buldu.
    # Yani video kesmeyle degil surekli animasyonla ilerliyor. 143 karede zemin analizi:
    #   %41 beyaz tuval (grafik/etiket/serif metin) | %43 tam kare footage | %16 karisik
    # Bu yuzden bu stilin ayirt edici ozelligi footage orani degil, GRAFIK KATMANI.
    "veri-anlatisi": {
        "ad": "Veri Anlatısı (Neu)",
        "ozet": "Beyaz tuvalde işaretli veri etiketleri, ölçü okları, alıntı kartları + gerçek footage",
        # ⚠ FAZ UI-5: timeline medya turu %100 VIDEO. AI statik gorsel
        # URETILMEZ; video bulunamayan sahne MEDYA_VIDEO_YOK ile bos
        # kalir (sessizce zoom slayta DUSULMEZ).
        "gorsel_yasak": True,
        "sahne_sn": 7, "maks_sahne_sn": 8, "kelime": 22, "footage_pct": 100, "overlay": "yok",
        "altyazi": "yok", "motion": "sinematik", "mag": "films_n_photography",
        "edit_paketi": True,      # plan 'grafik' alani uretir (EditPaketi.tsx sablonlari)
        "grafik_pct": 41,         # olculen beyaz-tuval orani
        "saha_etiketi": True, "etiket_pct": 28,
        "bolumler": True,   # bolum basligi + bolum bazli anlatim
        "gorsel_ek": ("photorealistic editorial documentary frame, natural light, restrained "
                      "colour grade, real lens depth of field, absolutely no text, no captions, "
                      "no graphics, no illustration"),
    },
    "hizli-explainer": {
        "ad": "Hızlı Explainer",
        "ozet": "Vox / Insider — 1.5-3sn hızlı kesme, sürekli kinetik metin, flat grafik",
        # ⚠ FAZ UI-5: timeline medya turu %100 VIDEO. AI statik gorsel
        # URETILMEZ; video bulunamayan sahne MEDYA_VIDEO_YOK ile bos
        # kalir (sessizce zoom slayta DUSULMEZ).
        "gorsel_yasak": True,
        "sahne_sn": 2.4, "kelime": 6, "footage_pct": 100, "overlay": "yogun",
        "altyazi": "yogun", "motion": "hizli", "mag": "standard",
        "gorsel_ek": ("clean flat-design explainer graphic, bright saturated palette, bold "
                      "high-contrast infographic style, crisp vector shapes, solid or white "
                      "background, clear data-visualization aesthetic, modern editorial "
                      "motion-graphics look"),
    },
}
VARSAYILAN_EDIT = "sinematik-belgesel"

# ───────── HİKAYE KANALI (sinematik gerçekçi) — üçüncü üst tür ─────────
# YouTube hikaye kanalı formatı: normal tempolu anlatım, foto-gerçekçi "film karesi" görseller.
# İLK DAKİKALAR (HIKAYE_ACILIS_SN) yoğun hareketli açılış (izleyici tutma), sonrası standart
# Ken Burns + altyazı. Karakter tutarlılığı: çapa referansı + sabit karakter kuralı (aşağıda).
HKANAL_STIL = (
    "cinematic photorealistic film still, shot on 35mm anamorphic cinema lenses, shallow depth "
    "of field, dramatic motivated lighting, moody filmic color grade, subtle film grain, high "
    "dynamic range, realistic skin and fabric texture, professional movie production value, "
    "absolutely no text, no captions, no watermark, no logo. "
    # SERT GERCEKCILIK KILIDI: mini/animasyon egilimli ciktilarda tema karismasi goruldu —
    # tek bir sahnenin bile cizim/anime gorunmesi tum kanali amatorlestirir.
    "STRICTLY LIVE-ACTION REALISM: this frame must look like real footage captured by a real "
    "cinema camera. NEVER cartoon, NEVER anime, NEVER illustration, NEVER painting, NEVER "
    "comic, NEVER 3D render or CGI look, NEVER stylized or flat art of any kind — if in doubt, "
    "make it MORE photographic, not less"
)
# Karakter yuklenmezse: gorunusu SABITLEMEZ (hikayeye gore model secer), ayni kalmasini SART kosar.
HKANAL_VARSAYILAN_KARAKTER = (
    "In every scene that includes the main character, they are the SAME real person: identical "
    "face, age, hair, build and outfit throughout the whole story — never swap, restyle or "
    "replace them. (Scenes marked 'no character' contain no people at all.)"
)
HKANAL_CERCEVE = (
    "Frame like a narrative feature film: vary shot sizes deliberately across scenes (wide "
    "establishing, medium, close-up), keep the main character clearly visible and emotionally "
    "readable, single continuous frame, never split screens or collages"
)
# Hikaye planlayici sozlesmesi — genel kuraldan iki kritik farki var:
# 1) ATMOSFER SAHNELERI: her ~4 sahneden 1'i KARAKTERSIZ olabilir (bos ev, sokak, gokyuzu,
#    onemli obje). Planlayici prompt'a 'no character' yazar -> referansli_gorsel kimlik
#    kilidini atlar, kareye figur zorlanmaz. Gercek hikaye kanallarinin dokusunu verir.
# 2) ILK GORUNUM TARIFI: karakter gorseli yuklenmediginde modelin karakteri hikayeye uygun
#    kurmasi icin ILK karakterli sahnede yas/tip/kiyafet tarifi YAZILIR (once yazilmiyordu;
#    'yasli saatci' genc cizilmisti). Sonraki sahneler tarifi TEKRARLAMAZ (capa tasir).
HKANAL_SOZLESME = (
    "IMPORTANT: give scene_prompt for EVERY scene = a vivid 16:9 ENGLISH description of the "
    "action/place/camera/mood, like a frame from a narrative feature film. CHARACTER RULE: the "
    "story has ONE main character who must look visually IDENTICAL across the whole video. In "
    "scenes where the character appears, the scene_prompt MUST contain the exact phrase 'the "
    "main character' as the acting subject. FIRST APPEARANCE ONLY: in the very first scene "
    "where the character appears, add a brief physical description drawn from the STORY right "
    "after that phrase (age, build, hair, clothing, era — e.g. 'the main character, an elderly "
    "watchmaker with white hair and a worn leather apron'); in every later scene do NOT "
    "describe the character's appearance at all (the reference image carries it) — only "
    "pose/action/emotion and the environment, with a DIFFERENT camera angle and setting per "
    "scene. ATMOSPHERE SHOTS: AT MOST one scene in five may be an establishing or atmosphere "
    "shot WITHOUT the character (an empty street, a house exterior, a stormy sky, a meaningful "
    "object in close-up); for those write 'no character' inside the scene_prompt and describe "
    "only the place/object/mood. The main character MUST appear in the large majority of "
    "scenes — they are the star of the video. Never invent additional recurring people; anonymous background "
    "extras are allowed when the story requires a crowd. Describe ONE single continuous frame — "
    "never panels, grids or split frames. (For footage scenes this prompt is the fallback if no "
    "clip is found.)\n"
)

HIKAYE_KANALI_PROFIL = {
    "ad": "Sinematik Hikaye",
    "ozet": "Hikaye kanalı formatı — film karesi görseller, hareketli açılış, altyazı, tutarlı karakter",
    # 6->8 sn: hikaye kanallarinda sakin tempo normal; %25 daha az gorsel = daha hizli + ucuz
    "sahne_sn": float(os.environ.get("HIKAYE_SAHNE_SN", "8")), "kelime": 19,
    "footage_pct": 0, "overlay": "yok",
    "altyazi": "orta", "motion": "hikaye", "mag": "films_n_photography",
    "gorsel_ek": HKANAL_STIL,
    "varsayilan_karakter": HKANAL_VARSAYILAN_KARAKTER,
    "cerceve": HKANAL_CERCEVE,
    "sahne_sozlesme": HKANAL_SOZLESME,
}
HIKAYE_STILLERI = {"sinematik-hikaye": HIKAYE_KANALI_PROFIL}
VARSAYILAN_HIKAYE = "sinematik-hikaye"
# Açılış süresi (sn): bu süredeki sahneler props'ta "vurgu"=true alır -> Video.tsx yoğun hareket verir
HIKAYE_ACILIS_SN = float(os.environ.get("HIKAYE_ACILIS_SN", "150"))

# Animasyon (stickman) — Documentary'den AYRI ust-duzey tur. Tamamen AI, gercek footage/Magnific YOK.
# ───────── ANIMASYON SANAT YONETIMI (referans video analizinden turetildi) ─────────
# Hedef: elle cizilmis editorial karikatur — murekkep kontur + gouache dolgu + cel golge,
# kagit dokusu, soluk vintage palet, DETAYLI ortamlar, karakter kucuk-orta olcek.
# ═══ DESTEK OGESI KURALI (tum animasyon stillerinde ZORUNLU) ═══
# Kullanici geri bildirimi: "bir sahne sadece karakterin on planda oldugu duz bir gorsel olarak
# gorunmemeli; ana karakter bir sey ANLATIYOR, yan destekleyici ogeler de kullanilmali."
# Yani her kare, o an anlatilan seyi GOSTEREN somut bir gorsel arac icermeli.
DESTEK_PLANLAYICI = (
    "SUPPORTING ELEMENT — MANDATORY IN EVERY SCENE. The character is NARRATING something, so each "
    "frame must SHOW what is being said, not just show the character. Besides the character and the "
    "setting, every scene_prompt must name at least ONE concrete supporting visual device that "
    "illustrates the exact point of that line, and must state how the character INTERACTS with it "
    "(holding, pointing at, leaning over, building, dropping, comparing, reacting to). Choose the "
    "device from: a real object or tool; a map, chart, timeline, diagram or plan; a document, letter "
    "or book; secondary figures (a crowd, soldiers, workers, a listener); a visual metaphor made of "
    "objects (scales, a growing plant, stacked coins, a cracked wall); a before/after or two-object "
    "comparison; an environmental event (fire, smoke, rain, collapse, dust, explosion). Vary the "
    "device from scene to scene — never repeat the same one twice in a row. A scene that is only a "
    "character standing in front of scenery is INVALID and must be rewritten.\n"
)
# ═══ KARE CESITLILIGI — KARAKTERSIZ KARELER ZORUNLU ═══
# Kullanici referansi (arac bakim kanali): 4 karenin 3'unde KARAKTER YOK — patlatilmis
# teknik sema, yazi karti, makro detay. Ritim: sema -> yazi -> sahne -> makro.
# Onceki halimiz her kareye karakter koyuyordu -> monoton "karakter + arka plan" akisi.
KARE_CESITLILIGI = (
    "FRAME VARIETY — THE CHARACTER IS NOT IN EVERY SCENE. This is a narrated explainer, so the "
    "pictures must alternate between the narrator and the SUBJECT being explained. Aim for roughly "
    "half the scenes WITHOUT any character. Choose each scene's frame type from this set and never "
    "use the same type twice in a row:\n"
    "  HERO ACTION — the character physically doing/handling something in a real setting.\n"
    "  OBJECT MACRO — extreme close-up of the object being discussed, filling the frame, NO "
    "character (write 'no character in frame').\n"
    "  HANDS ONLY — extreme close-up of two hands performing the exchange or action (handing over "
    "an envelope, passing a key, gripping a tool), cropped at the wrists, plain background, no "
    "faces and no bodies.\n"
    "  MAP ROUTE — a simple outline map of the relevant place with 2-3 labelled dots and a dashed "
    "route line between them, plus one small vehicle or object travelling along it; NO character "
    "figure (a tiny driver inside a vehicle is allowed).\n"
    "  INNER VOICE — the character alone in a wide atmospheric setting with 3-4 short thought "
    "fragments floating in the air around its head as small hand-written words, showing what it is "
    "feeling at that moment.\n"
    "  EXPLODED VIEW — the object taken apart, its parts floating separated and labelled by shape, "
    "on a clean plain background, NO character.\n"
    "  CONCEPT CARD — a very short phrase on a clean plain background, NO character.\n"
    "  COMPARISON — two objects or two states side by side (old vs new, right vs wrong), NO "
    "character.\n"
    "  PROCESS STEP — hands (or the character's hands only) performing one step on the object.\n"
    "  WIDE CONTEXT — the character small inside the full place, showing where this happens.\n"
    "When the narration is about a THING (how it works, what breaks, what to look for), prefer the "
    "character-free types; use HERO ACTION when the narration is about a person doing or deciding "
    "something. Scenes written as 'no character in frame' must not contain any figure at all.\n"
)

# ── CEKIM OLCEGI DENGESI (Polat, 4 Agu 2026: "cok uzaktan cekilmis gorseller
# kullanmasin, daha dogal olsun — yakinda olsun uzakta olsun") ──
# Olculen sorun: cerceve metni "kamerayi yakinlastirma" ve "nesneler dort kenara
# kadar dolsun" diyordu; bu her kareyi geriye itiyordu. Ustune "orta cekim" bandi
# %30-50 olarak tanimliydi, ki bu zaten uzak. Gercek kanallarda oran tersine:
# yakin ve orta agirlikli, genis plan az ve sadece MEKANI TANITMAK icin.
CEKIM_OLCEGI = (
    "SHOT DISTANCE — MATCH THIS MEASURED DISTRIBUTION. These percentages were measured frame by "
    "frame from the reference channel (60 sampled frames), so they are the target, not a "
    "suggestion. Across the whole video aim for roughly:\n"
    "  • 20% MEDIUM — the subject from the waist up, filling 45-70% of the frame height. This is "
    "the band that is most often missing: if in doubt, make the scene MEDIUM.\n"
    "  • 45% WIDE — the person full length with the room around them, room and person both read.\n"
    "  • 20% VERY WIDE — the room or place dominates and the person is small in it.\n"
    "  • 10% CLOSE — head and shoulders, or a pair of hands, or one object filling the frame.\n"
    "  • 5% VERY CLOSE — a face filling almost the whole frame, used only for the single "
    "strongest emotional beat.\n"
    "Two consecutive scenes must not use the same distance. Never repeat VERY WIDE twice in a "
    "row — that is what makes a video feel like it was shot from across the street.\n"
)

# ── KARAKTERSIZ KARELER DE AYNI ELDEN CIKMALI (4 Agu 2026) ──
# Olculen sorun: G INFOGRAPHIC / K MAP ROUTE / N SCREEN READOUT tipleri "duz kat plani,
# noktali cizgi, FRIDGE-STOVE etiketleri" ve "gercekci akilli telefon arayuzu" olarak
# ciziliyordu. Sicak elle cizilmis mutfakla ayni gorsel dilde DEGIL — video ortasinda
# baska bir programdan kesilmis gibi duruyor. Sema/ekran kareleri de stil sozlesmesine
# tabi olmali.
SEMA_STIL_KILIDI = (
    "DIAGRAMS, MAPS, SCREENS AND CARDS OBEY THE SAME STYLE. When a scene is an infographic, a "
    "map, a ledger, a screen or a lettered card, it must still be DRAWN BY THE SAME HAND in the "
    "same medium as every other frame — same line quality, same palette, same texture, same "
    "warmth. Never switch to clean software-style vector graphics, never render a realistic "
    "modern phone or app interface, never use generic UI chrome, flat grey wireframes, dotted "
    "CAD lines or system fonts. Draw the chart as if someone sketched it on paper in this "
    "world: a hand-drawn plan on a notepad, a map inked on a card, a list written in a "
    "notebook, numbers written by hand. Any device shown must belong to the era and setting "
    "of the rest of the video.\n"
)

DESTEK_GORSEL = (
    " STORYTELLING FRAME: this is a narrated explainer picture, so the frame must SHOW the idea, not "
    "just the character. Besides the character and the background, clearly render the supporting "
    "element named in the scene text — the object, map, diagram, document, crowd, metaphor or event "
    "— large enough to read at a glance, and show the character physically engaging with it. A flat "
    "picture of a character simply standing in front of scenery is not acceptable."
)

# ── VERI KARTI (567 referans karesinin EN GUCLU bulgusu) ──
# Aussie Money With Bruce'un 28 karesinin ~24'unde tutulan tabela / laptop ekrani / fiyat
# etiketi var ve ustunde anlatilan cumlenin TAM SAYISI yazili. Karakter hicbir zaman
# "sadece anlatmiyor", sayiyi GOSTERIYOR. Bizim eski kuralimiz "destekleyici oge olsun"
# diyordu ama "anlatilan sayiyi gorunur bir yuzeye yaz" DEMIYORDU.
VERI_KARTI_PLAN = (
    "DATA CARD — apply ONLY to a scene whose narration literally contains a NUMERAL: a price, "
    "percentage, year, count, quantity or duration written as digits. If the line has no numeral, "
    "the scene gets NO card, NO sign and NO lettered board — write \"no text in this image\" and "
    "move on. NEVER invent an abstract label card (\"EMOTIONAL EXPRESSION\", \"SALES GROWTH\", "
    "\"MINDSET\") — a card that does not carry a number from the narration is a FAILURE. "
    "When the line does contain a numeral you MUST name a "
    "physical surface inside the world that displays that exact fact — a held placard, a shop price "
    "tag, a laptop or phone screen, a TV, a noticeboard, a billboard, a printed letter, a menu or a "
    "hand-drawn chart — and write the words to be shown in double quotes. Do not paraphrase the "
    "number; use the same figure the narration says. If the narration compares two things, show "
    "both values on the same surface. If a scene's line carries no concrete fact, no data card is "
    "needed and you must not invent one.\n"
)
VERI_KARTI_GORSEL = (
    " DATA CARD: if the scene text puts words or figures on a surface (placard, screen, tag, board, "
    "chart), render that surface large, front-facing and fully legible, and place it on the opposite "
    "side of the frame from the character so the two do not overlap — character on one side, the "
    "information on the other. Draw the surface and any chart in the SAME medium and style as the "
    "rest of the picture. Spell the words exactly as written, ALL CAPS, no extra text invented."
)
# Marka guvenligi: Bruce gercek logolar kullaniyor (Netflix/Disney+). Biz KULLANMAYACAGIZ.
MARKA_YASAK = (
    " Never draw real company logos, brand marks, product names or recognisable trade dress; "
    "invent neutral generic equivalents instead."
)
# Iki BAGIMSIZ kanal (Paint Explainer + Simple Explainer) ayni seyi yapiyor: bir bolum boyunca
# AYNI mekan tekrar kullaniliyor, sadece aci/aksiyon degisiyor. Tesadufi degil, kural.
MEKAN_SUREKLILIGI = (
    "SETTING CONTINUITY: group your scenes into short runs of 2-4 consecutive scenes that share the "
    "SAME named location, and describe that location with the same concrete details each time, "
    "changing only the camera angle, the distance and what happens. Move to a new location only when "
    "the narration genuinely moves on. A video that teleports to a brand-new place every single "
    "scene feels incoherent; repeating a place makes it feel like a real world.\n"
)


ANIM_STIL = (
    "Hand-drawn editorial cartoon on textured paper: confident dark sepia-brown ink outlines with "
    "organic wobble and varying line weight, flat gouache fills, two-tone cel shading with strong "
    "directional light and deep cast shadows, subtle paper grain and soft offset-print texture. "
    "Sun-faded palette drawn from warm ochre, sage green, dusty slate blue, faded brick and "
    "warm cream, kept LIGHT and airy rather than dark; never neon, glossy or flat digital vector. IMPORTANT — vary which of "
    "these colours DOMINATES this particular scene (one scene ochre-dominant, the next sage-green or "
    "dusty slate-blue or cool grey dominant) so consecutive scenes do not all share the same colour "
    "temperature, while the palette family and drawing style stay identical. Small natural in-world "
    "lettering on signs or labels is welcome. Melancholic, reflective, nostalgic essay-film mood. "
    "No photorealism, no 3D render, no pure white background, no subtitle bar, no watermark, no logo"
)
# Kullanici KARAKTER REFERANSI YUKLEMEZSE kullanilacak varsayilan kahraman tarifi.
# (Referans yuklenirse bu KULLANILMAZ — aksi halde kullanicinin karakteriyle CAKISIRDI.)
ANIM_VARSAYILAN_KARAKTER = (
    "The recurring character is a sophisticated stick figure: plain oval head, minimal face of two "
    "small dot eyes and one faint mouth line, no nose, no hair, pale cream body, thin simple limbs "
    "— identical in every scene"
)
# Kompozisyon/cerceveleme kurali (referansli_gorsel promptuna eklenir)
ANIM_CERCEVE = (
    " FRAMING: obey the shot type and character-scale phrase written in the scene description "
    "as a guide; when the moment is intimate you may move CLOSER than the band suggests. The ENVIRONMENT "
    "is the main subject. Build a complete believable place: a foreground object cutting into the "
    "frame, a middle ground where the action happens, and a detailed background with true perspective "
    "and receding depth. Objects, furniture and signage must run to all four edges of the image, and "
    "at least one piece of furniture or foreground object must pass in front of the character and "
    "partly overlap it. In CLOSE shots the background may fall away entirely — that is correct. "
    "Light the scene to MATCH the measured brightness target given later in this prompt; if no target is given, use one soft dominant source with soft readable shadows."
)

# ═════════ EXPLAINER STILI (2. referans: "Salt" videosu analizinden) ═════════
EXP_STIL = (
    "Clean digital cartoon with a hand-drawn marker feel, identical in every frame. Every shape is "
    "fully closed with a solid black outline; the outer silhouette line one step thicker than "
    "interior lines. Fills are FLAT and saturated, plus exactly ONE darker flat tone of the same hue "
    "as attached shading inside an object's own shape — no cast shadows, no gradients, no glow. "
    "Bright cheerful educational mood, high contrast, generous empty space. "
    "COLOUR: keep a locked core of black outlines, pure white and one flat alert red (used only for "
    "negation or the single thing being singled out); pick three flat theme colours plus one neutral "
    "ground tone that suit the subject and reuse exactly those in every frame. Named flat colours "
    "only, never blended. Vary WHICH of the theme colours fills the background from scene to scene so "
    "consecutive colour scenes do not look alike, while the colour set itself stays fixed. "
    "BACKGROUND is one of exactly two things: a flat colour environment (one straight horizon band "
    "plus a few flat shapes), or a pure white void for concept cards — white edge to edge, no tint, "
    "no panel or card border. "
    "Any lettering is thick hand-lettered marker CAPITALS: upright, uniform stroke, solid fill, black "
    "or alert red only. Full-bleed art. Keep out: gradients, texture, grain, 3D or photographic "
    "rendering, borders, frames, logos, watermarks, subtitle bars."
    " This is a drawn illustration, NEVER a photograph: no photorealism, no camera lens "
    "effects, no real human skin or hair texture, no film still look."
)
EXP_VARSAYILAN_KARAKTER = (
    "The recurring hero is a simple cartoon everyman about 4.5 heads tall: round head, one flat skin "
    "tone, shaggy hair in one flat dark tone falling just over the eyebrows, two small solid-black "
    "dot eyes set wide apart, one tiny black dash nose, one thin curved mouth line, no eyebrows or "
    "facial shading, mitten hands, plain oval feet. His outfit is always exactly two flat colours "
    "(terracotta-orange upper, dark-brown lower). Identical in every scene — no ageing, no "
    "re-colouring, no added glasses/beard/hat"
)
EXP_CERCEVE = (
    " COMPOSITION: one single focal idea, eye level, no tilt, no vignette, no inner border. "
    "Everything sits on one flat plane — overlap is fine but no vanishing-point perspective, no depth "
    "blur, no cast shadows. DELIVERY CROP: the frame is centre-cropped to 16:9 later, so keep the top "
    "9% and bottom 9% of the canvas free of faces, lettering and arrow tips, and keep a clear 5% "
    "outer margin. In colour scenes the hero is never smaller than 20% of frame height (below that "
    "his locked features stop resolving) and at least 25% of the canvas stays empty flat colour. On a "
    "white card the frame is pure white to ALL FOUR EDGES with no signboard, placard or paper object "
    "— the lettering sits directly on the white, horizontal, never rotated, never overlapping a face "
    "or icon, inside the central 80% of the canvas, with at least 30% left empty white. "
    "SCALE DISCIPLINE: in wide establishing and high overview shots the hero occupies only about "
    "25-35% of the frame height and the environment fills the rest; never let the hero's head and "
    "torso dominate a wide shot. Only medium, close-detail and profile shots may show him large."
)
EXP_SOZLESME = (
    "SCENE PROMPT CONTRACT (educational explainer). Each scene_prompt is ONE English paragraph of "
    "25-45 words, present tense, exactly one action or one concept, and OPENS with either "
    "\"COLOUR SCENE -\" or \"WHITE CARD -\" followed by the shot type / card archetype.\n"
    "FRAME MIX — target roughly two colour scenes per white card. Base rhythm by 1-based index i: "
    "i mod 3 == 0 -> WHITE CARD, otherwise COLOUR SCENE; scene 1 is always a COLOUR SCENE. CONTENT "
    "OVERRIDE beats the rhythm: force a WHITE CARD when the beat's core is a quantity, date, "
    "duration, comparison, sequence/cycle, definition, category set or a rejected option; force a "
    "COLOUR SCENE when the core is a physical action, a place, a moment or a feeling. Never more than "
    "3 colour scenes in a row and never more than 2 white cards in a row.\n"
    "COLOUR SCENE SHOT ROTATION — count only colour scenes; for the a-th one use a mod 6: "
    "1 WIDE ESTABLISHING (full body, flat environment, horizon band, 3-4 background shapes); "
    "2 MEDIUM ACTION (knees-up, one clear action, one prop — cropping is intended); "
    "3 MULTI-CLONE GROUP (3-5 identical copies of the hero around one shared focus object); "
    "4 CLOSE DETAIL (hands and one object filling the frame); "
    "5 SIDE PROFILE MOMENT (hero in profile reacting to one thing entering frame); "
    "0 HIGH FLAT OVERVIEW (small top-down map-like layout of the place). The environment may repeat "
    "across scenes but the SHOT TYPE must change. Colour scenes contain NO on-screen text at all: "
    "max 2 props, max 4 background shapes, environment named in 6 words or fewer.\n"
    "WHITE CARD RULE (critical): the ENTIRE frame is pure white from edge to edge — no ground line, "
    "no horizon, no wall, no coloured background, and absolutely NO signboard, placard, poster, paper "
    "sheet or held object. The words are drawn DIRECTLY onto the white as free-standing lettering. "
    "Never write 'holds a sign' or 'holding a placard'; write that the words float on plain white.\n"
    "WHITE CARD ARCHETYPES — pick by beat content, never the same archetype twice in a row: "
    "GIANT PHRASE (a quantity/date/headline claim as one huge line, tiny hero beside it for scale); "
    "REJECT (a rejected or costly option as one word, with a thick alert-red X placed BESIDE or BELOW "
    "the word — never across the letters — plus one small flat icon); "
    "COMPARE (two flat icons side by side or a simple two-pan balance, one short line under each "
    "side); ANNOTATED SUBJECT (one central object with 2-3 thick black arrows, each arrow ending on a "
    "short label).\n"
    "TEXT BUDGET — the hard rule that keeps lettering legible. Give the wording as DOUBLE-QUOTED "
    "strings inside scene_prompt, phrased as: Hand-lettered bold marker capitals spelled exactly: "
    "\"FIRST LINE\" very large across the upper middle, and \"SECOND LINE\" smaller below. "
    "Limits: at most 2 quoted strings per card, at most 3 words and 14 characters per string, at most "
    "5 words in the whole image. ALL CAPS. Allowed characters ONLY: A-Z, 0-9, space, hyphen, question "
    "mark, percent sign. FORBIDDEN: commas, full stops, apostrophes, ampersands, slashes, plus signs, "
    "superscripts, chemical symbols. Write \"300 000 YEARS\" or \"300K YEARS\", never \"300,000\"; "
    "write \"SODIUM\", never \"Na+\". Never quote a sentence — split a long term over two lines "
    "(\"MINERAL\" / \"INTAKE\"); the voice-over carries the sentence.\n"
    "The character is referred to ONLY as \"the hero\" — never restate appearance, clothing or "
    "colours. Do NOT mention camera, lens, lighting, style, texture or medium in scene_prompt; all "
    "styling lives in the global block.\n"
    + KARE_CESITLILIGI + DESTEK_PLANLAYICI + VERI_KARTI_PLAN + MEKAN_SUREKLILIGI + CEKIM_OLCEGI + SEMA_STIL_KILIDI
)




ANIM_SOZLESME = (
    "SCENE PROMPT CONTRACT: every scene_prompt is ONE English paragraph of 45-65 words with "
    "these six slots IN THIS ORDER: (1) SHOT TYPE + camera height, taken verbatim from the "
    "rotation table below; (2) the CHARACTER SCALE PHRASE copied verbatim from the same row "
    "(or 'no character in frame'); (3) the character's single concrete PHYSICAL action and "
    "posture (a body doing a thing — never 'thinking', 'realizing', 'feeling'); (4) the "
    "LOCATION named specifically plus 4-6 concrete objects that truly belong there, named and "
    "split across foreground / middle ground / background (shelves, hand tools, crates, wall "
    "clock, desk lamp, tyres, glass jars, worn floorboards, bins, price tags, cardboard boxes, "
    "shop window); (5) ONE named LIGHT SOURCE and its direction (overhead shop lamp from "
    "above, low window light from the left, bare bulb behind, streetlight from the right); "
    "(6) one EMOTION word.\n"
    "SHOT ROTATION — assign strictly by scene index modulo 8, in order, never the same shot "
    "twice in a row: 1 wide establishing, eye level — 'small full-body figure seen from across "
    "the room, far from camera'; 2 medium, eye level — 'full body from a few steps back, "
    "standing off-centre'; 3 over-the-shoulder, slightly high — 'seen from behind one "
    "shoulder, back turned, upper body only'; 4 low angle looking up — 'small full-body figure "
    "dwarfed beneath towering shelves'; 5 close object detail — 'no character in frame; only "
    "hands or objects'; 6 high angle looking down — 'small figure seen from above, dwarfed by "
    "floor and furniture'; 7 deep aisle or corridor with a vanishing point, eye level — "
    "'distant small figure far down the receding space'; 8 two contrasting objects side by "
    "side on one surface — 'no character in frame' (never split the frame into two places, "
    "never draw two characters).\n"
    "LOCATION VARIETY: name a genuinely different place at least every third scene; never use "
    "the same location for more than two consecutive scenes; use at least ten distinct places "
    "across the video.\n"
    "BANNED WORDS in scene_prompt: empty background, plain background, simple background, "
    "white background, flat colour backdrop, minimalist, negative space, clean, abstract.\n"
    "IDENTITY FIREWALL: never describe the character's face, head, clothing, colour, body "
    "shape, age or gender — identity is locked globally.\n"
    "STYLE FIREWALL: do NOT describe art style, palette, line quality, texture or medium "
    "inside scene_prompt — the global style block already fixes those; repeating them breaks "
    "style consistency between scenes.\n"
    "TEXT: at most one short natural in-world sign, under four words, written as: sign reads "
    "\"NEW & IMPROVED\". Never captions, subtitles, watermarks or logos.\n"
    + KARE_CESITLILIGI + DESTEK_PLANLAYICI + VERI_KARTI_PLAN + MEKAN_SUREKLILIGI + CEKIM_OLCEGI + SEMA_STIL_KILIDI
)

# ═════════ HIKAYE / WHAT-IF STILI (3. referans: "You Wake Up 100,000 Years Ago") ═════════
# Imza: SADE duz beyaz stickman + ZENGIN boyali dunya. "Yagli boya tablonun ustune
# yapistirilmis kagit kesik" mantigi + ISIK USTUNLUGU (isik sadece dunyaya duser).
HIK_STIL = (
    "A richly painted 2D story-explainer illustration: a detailed hand-painted world with "
    "ultra-simple flat sticker-like figures placed on top of it, like paper cutouts pasted onto an "
    "oil painting. THE WORLD (everything except the figures) is fully painted and cinematic — "
    "saturated natural colour, visible brushwork, atmospheric haze, real light and real cast shadows, "
    "layered depth from a framing foreground to a hazy far vista; the world carries NO black "
    # NOT: burada RENK DAYATILMAZ. Onceden 'pure flat white shapes' yaziyordu ve kullanicinin
    # turuncu karakteriyle CATISIP sahneler arasi beyaz<->turuncu salinimina yol aciyordu.
    # Renk daima karakter kunyesinden gelir; stil sadece CIZIM DILINI tanimlar.
    "outlines and is never flat or vector. THE FIGURES are the exact opposite: flat unshaded shapes "
    "in their own solid colours, drawn with one clean uniform-width black ink line — no shading, no "
    "gradient, no texture, no rim light, no glow, no colour spill, keeping exactly the SAME colours "
    "at noon, at night, in caves and in firelight. LIGHT "
    "SUPREMACY: scene light falls on the world only; figures cast a flat hard-edged single-tone "
    "shadow on the ground but never receive light. All descriptive detail is spent on the "
    "environment, none on the figures. Palette: earth greens, volcanic red, warm gold, dusk blue. "
    "IMPORTANT — shift the DOMINANT colour and time of day from scene to scene (one scene golden "
    "sunset, the next cool green jungle shade, then blue night, then dusty red rock) so consecutive "
    "scenes never share the same colour temperature; the painting style stays identical throughout. "
    "Lettering, when present, is a bold flat uppercase sans-serif graphic overlay or a plain outlined "
    "label box drawn on top of the painting. Avoid: photorealism, 3D render, anime, outlined or "
    "vector-flat scenery, shaded or muscular or textured figures, detailed faces"
    " This is a drawn illustration, NEVER a photograph: no photorealism, no camera lens effects, no real human skin or hair texture, no film still look."
)
HIK_VARSAYILAN_KARAKTER = (
    "The hero is one white stick figure: thin uniform black outline, completely white unshaded head "
    "and body, hairline-thin straight arms and legs, small rounded hands and feet, no neck, no "
    "muscles, no body detail. Rounded head with two large white eyes with black pupils, short thick "
    "black eyebrows, one small simple mouth. Messy spiky black hair is the only dark mass on him and "
    "its silhouette never changes. He wears exactly one garment in one flat solid colour with no "
    "folds or texture (ancient era: a plain tan waist wrap; modern era: a plain rust-orange t-shirt "
    "with slate-grey trousers). Nothing else is ever added unless the scene names a held prop. "
    "Emotion comes only from eye size, eyebrow angle and posture. He is always the brightest value "
    "in the frame"
)
HIK_CERCEVE = (
    " FRAMING for a 16:9 centre crop of this 1536x1024 image: the top 9% and bottom 9% get cut away, "
    "so every face, letter, label box and key silhouette stays inside 10%-90% of frame height and 8% "
    "clear of the left and right edges. VALUE LAW (non-negotiable): the painted area directly behind "
    "and around a figure is mid-toned and visually calm so the flat white figure reads instantly as "
    "the lightest shape — never place a figure against bright sky, open fire, snow or busy painted "
    "texture. GROUNDING: every figure sits on the ground with a flat hard-edged single-tone shadow "
    "ellipse, never a soft or painted shadow. One focal point per frame placed on a third; horizon on "
    "the upper or lower third; build three depth layers (dark framing foreground, midground subject, "
    "hazy receding background). Keep clear negative space around every figure."
)
HIK_SOZLESME = (
    "RULE ZERO — READ FIRST: this is a narrated explainer, not a character showcase. AT LEAST "
    "40% OF ALL SCENES YOU WRITE MUST CONTAIN NO CHARACTER AT ALL (shot types G, I, J, K below) "
    "and must literally contain the words 'no character in frame'. Before you finish, COUNT "
    "your scenes: if fewer than 40% are character-free, rewrite the weakest character scenes as "
    "object macros, hands-only close-ups, maps or diagrams. A video where every frame shows the "
    "character standing in a landscape is the FAILURE MODE we are eliminating.\n"
    "SCENE CONTRACT — each scene_prompt is ONE English paragraph of 45-80 words, slots always in this "
    "order: (1) SHOT: the shot-type letter plus the hero's height as a percent of frame height; "
    "(2) WORLD: the painted environment with at least 3 concrete named details, ONE named light "
    "source, time of day and colour mood — spend the entire adjective budget here; (3) FIGURES: only "
    "what the figure(s) DO — pose, gesture and the emotion read from eyes and stance. NEVER state "
    "the character's colour (it is locked globally); close this slot with the fixed clause "
    "\"figures stay flat and unshaded with clean black outlines, unaffected by the scene light\"; "
    "(4) TEXT: either a lettering instruction in double quotes, or "
    "literally \"no text in this image\" — this slot is never empty.\n"
    "Never re-describe the hero's face, hair, clothing, outline, proportions or style — identity is "
    "injected separately and re-describing it causes drift. Prefix the paragraph with ANCIENT or "
    "MODERN when the era could be ambiguous.\n"
    "SHOT TYPES AND SCALE BANDS (bands never overlap; two consecutive scenes must use different "
    "bands): A WIDE ESTABLISHING — hero 10-18%, landscape dominant, deep perspective. B MEDIUM ACTION "
    "— hero 30-50%, mid-gesture, environment fully painted behind. C CLOSE-UP — hero 55-75%, chest "
    "up, eyes on the upper third, the emotional beat. D DRAMATIC LIGHT — hero 30-50%, dark painted "
    "scene lit by one fire, beam or opening; the ENVIRONMENT glows, the figure stays plain flat white "
    "— never glowing, never a silhouette, never orange-tinted. E CROWD — 4-8 figures on three depth "
    "planes, hero nearest and largest (30-50%), middle figures simplified, farthest figures "
    "featureless white silhouettes. F COMPARISON — one painted scene split by a natural divide into "
    "two contrasted situations; both figures identical in build, only posture and surroundings "
    "differ, never a bulky or muscular body; hero 30-50%. "
    "G INFOGRAPHIC — NO CHARACTER IN FRAME: a drawn path, timeline or diagram over a painted or plain "
    "ground, 2-3 arrows and at most 2 short outlined label boxes. "
    "H SFX BEAT — one big quoted onomatopoeia plus one simple graphic device (red pulse line, impact "
    "rays, dust puff); hero 30-50%. "
    "I OBJECT MACRO — NO CHARACTER IN FRAME: extreme close-up of the single object the line is about, "
    "filling the frame, painted in full detail. "
    "J HANDS ONLY — NO CHARACTER IN FRAME: extreme close-up of hands doing the action (handing "
    "something over, gripping a tool, opening a letter), cropped at the wrists. "
    "K MAP ROUTE — NO CHARACTER IN FRAME: a simple outline map of the relevant place with 2-3 "
    "labelled dots and a dashed route between them, one small vehicle or object on the route.\n"
    "FREQUENCY BUDGET per rolling block of 10 scenes — HARD RULE: AT LEAST 4 of the 10 scenes must be "
    "CHARACTER-FREE (types G, I, J or K). The video must alternate between the narrator and the "
    "subject being explained; a run of character-only frames is the single worst failure here. "
    "Also: at least 2 of A/B, at least 1 C, at least 1 D, at most 1 E, at most 1 F, exactly 1 H. "
    "Never use the same type twice in a row and never place two character-free scenes back to back. "
    "CHOOSING: when the line is about a THING (how it works, what it costs, where it travels, what it "
    "looks like, what it is made of) use G/I/J/K; when it is about a PERSON doing, deciding or feeling "
    "something use A/B/C/D/E. Scenes of types G/I/J/K must literally contain the words "
    "'no character in frame'.\n"
    "WORLD ROTATION: two consecutive scenes may not share biome AND time of day AND palette; rotate "
    "deliberately (volcanic valley, fern jungle, rock canyon, cave interior, night campfire, dusk "
    "huts and smoke, green oasis, river crossing, overgrown modern ruin) and change the camera angle "
    "every scene.\n"
    "TEXT BUDGET: at most 1 scene in 3 carries lettering. When it does: max 2 lines, each max 3 words "
    "and 14 characters, ALL CAPS, letters A-Z digits 0-9 and spaces only, inside double quotes. No "
    "commas, no punctuation, no plus signs, no chemical symbols, no thousand separators — write "
    "\"100K YEARS\" not \"100,000\". Each infographic label box obeys the same limit. Text never sits "
    "in the top or bottom 9% of the frame.\n"
    + KARE_CESITLILIGI + DESTEK_PLANLAYICI + VERI_KARTI_PLAN + MEKAN_SUREKLILIGI + CEKIM_OLCEGI + SEMA_STIL_KILIDI
)

# ═════════ RENKLI KALEM STILI (6. referans: "Aussie Money With Bruce") ═════════
# Fark: HIK_STIL "boyanmis dunya + duz figur" kontrastina dayanir. Burada TEK medyum var —
# her sey ayni renkli kalemle cizilmis. Kimlik yuzden degil IMZA AKSESUARDAN okunur.
KALEM_STIL = (
    "Hand-drawn coloured-pencil illustration on cream textured paper, one single medium for the "
    "whole image. Visible directional pencil hatching and crayon grain on every surface; soft "
    "slightly uneven contours drawn in dark pencil, thicker on the outer silhouette and lighter "
    "inside; colour built up in layered strokes so flat areas still show the tooth of the paper. "
    "Gentle natural daylight with soft pencil-shaded shadows — no hard cel shading, no gradients, "
    "no glow, no digital vector flatness. Warm, homely, everyday-life mood; ordinary places drawn "
    "with affection and a lot of small true-to-life clutter. Figures are ultra-simple: plain white "
    "rounded head, thin dark limbs, small oval hands and feet, no nose, no neck; all the drawing "
    "detail is spent on the ENVIRONMENT and the props, never on the body. "
    "Avoid: photorealism, 3D render, anime, glossy digital vector art, neon colours, airbrush"
    " This is a drawn illustration, NEVER a photograph: no photorealism, no camera lens effects, no real human skin or hair texture, no film still look."
)
KALEM_VARSAYILAN_KARAKTER = (
    "The narrator is one simple stick figure: plain white rounded head with two black dot eyes, two "
    "short black eyebrows that carry all the emotion, and one small mouth line; no nose, no ears, no "
    "hair, no neck. White body, thin dark limbs, small oval white hands and feet. He wears exactly "
    "one signature item — a green and gold diagonally striped necktie — and it is present, identical, "
    "in every single frame he appears in. Nothing else is ever added to him"
)
KALEM_CERCEVE = (
    " FRAMING for a 16:9 centre crop of this 1536x1024 image: the top 9% and bottom 9% get cut away, "
    "so every face, sign and key silhouette stays inside 10%-90% of frame height and 8% clear of the "
    "left and right edges. Obey the shot type and character-scale band written in the scene text "
    "as a guide; when the moment is intimate you may move CLOSER than the band suggests. THE PLACE IS THE SUBJECT: build a "
    "complete believable room or exterior with a foreground object cutting into the frame, a "
    "midground where the action happens and a background with true perspective, and let furniture, "
    "shelves, signage and clutter run to all four edges — nothing floats on blank paper. At least one "
    "object must pass in front of the figure and partly overlap it. "
    "Light the scene to MATCH the measured brightness target given later in this prompt; if no target is given, use one soft dominant source with soft pencil-shaded shadows. Keep the figure's white head clearly "
    "readable against whatever sits behind it."
)
KALEM_SOZLESME = (
    "RULE ZERO — READ FIRST: this is a narrated explainer, not a character showcase. AT LEAST "
    "40% OF ALL SCENES YOU WRITE MUST CONTAIN NO CHARACTER AT ALL (shot types G, I, J, K below) "
    "and must literally contain the words 'no character in frame'. Before you finish, COUNT your "
    "scenes: if fewer than 40% are character-free, rewrite the weakest character scenes as object "
    "macros, hands-only close-ups, maps or diagrams.\n"
    "SCENE CONTRACT — each scene_prompt is ONE English paragraph of 45-80 words, slots always in this "
    "order: (1) SHOT: the shot-type letter plus the narrator's height as a percent of frame height; "
    "(2) PLACE: a specific ordinary real-world setting with at least 4 concrete named objects in it "
    "(appliances, shelves, notices, plants, tools, furniture), ONE named light source and the time of "
    "day — spend the entire adjective budget here; (3) ACTION: only what the figure(s) DO — the "
    "gesture, what they are touching or holding, and the emotion read from eyebrow angle and posture. "
    "NEVER state the character's colours or clothing (identity is injected separately). "
    "(4) TEXT: either a lettering instruction in double quotes, or literally \"no text in this "
    "image\" — this slot is never empty.\n"
    "SUPPORTING CAST: when a scene needs other people, they are the same simple stick figures but "
    "are told apart ONLY by a plain garment, hair shape or hat — never by a different body style, "
    "and never by wearing the narrator's signature item.\n"
    "SHOT TYPES AND SCALE BANDS (bands never overlap; two consecutive scenes must use different "
    "bands): A WIDE ESTABLISHING — figure 12-20%, the whole room or street visible. B MEDIUM ACTION "
    "— figure 30-50%, mid-gesture, physically interacting with a named object. C CLOSE-UP — figure "
    "55-75%, head and shoulders, eyebrows carrying the emotional beat. D DRAMATIC LIGHT — figure "
    "30-50%, dim room lit by one lamp, window or screen. E CROWD — 3-6 figures on two depth planes, "
    "narrator nearest at 30-50%, the others differentiated by garment or hair. "
    "F HELD SIGN — figure 30-50% holding a large drawn placard, board or newspaper whose short text "
    "is the point of the scene. "
    "G INFOGRAPHIC — NO CHARACTER IN FRAME: a pinboard, whiteboard or drawn chart with 2-3 arrows or "
    "pinned cards and at most 2 short labels. "
    "H SFX BEAT — one big quoted onomatopoeia plus one simple pencil graphic device (impact rays, "
    "motion lines, dust puff); figure 30-50%. "
    "I OBJECT MACRO — NO CHARACTER IN FRAME: extreme close-up of the single object the line is about, "
    "filling the frame, drawn in full pencil detail. "
    "J HANDS ONLY — NO CHARACTER IN FRAME: extreme close-up of hands doing the action (passing an "
    "envelope, signing a form, counting notes), cropped at the wrists. "
    "K MAP ROUTE — NO CHARACTER IN FRAME: a simple hand-drawn map with 2-3 labelled dots and a dashed "
    "route between them.\n"
    "FREQUENCY BUDGET per rolling block of 10 scenes — HARD RULE: AT LEAST 4 of the 10 must be "
    "CHARACTER-FREE (G, I, J, K). Also: at least 2 of A/B, at least 1 C, at least 1 D, at most 1 E, "
    "at most 1 F, exactly 1 H. Never use the same type twice in a row and never place two "
    "character-free scenes back to back.\n"
    "PLACE ROTATION: two consecutive scenes may not share the same room or location; rotate "
    "deliberately (kitchen, living room, front yard, workplace lunch room, home office, hallway, "
    "street, shed) and change the camera angle every scene.\n"
    "TEXT BUDGET: at most 1 scene in 3 carries lettering. When it does: max 2 lines, each max 3 words "
    "and 14 characters, ALL CAPS, letters A-Z digits 0-9 spaces and the $ sign only, inside double "
    "quotes. No commas, no thousand separators — write \"12 MILLION\" not \"12,000,000\". Text never "
    "sits in the top or bottom 9% of the frame.\n"
    + KARE_CESITLILIGI + DESTEK_PLANLAYICI + VERI_KARTI_PLAN + MEKAN_SUREKLILIGI + CEKIM_OLCEGI + SEMA_STIL_KILIDI
)

# ═════════ ANI DEFTERI STILI (11. referans: "ThriftyHazel" — 216 kare) ═════════
# Digerlerinden temel farki: karakter COP ADAM DEGIL, gercekci-karikatur bir insan.
# Kanal ~11 dk'lik "N sey" listeleri yapiyor; kimlik anlaticinin YASI ve kiyafeti.
ANI_STIL = (
    "Warm hand-drawn storybook illustration: fine confident ink linework filled with soft coloured "
    "pencil and light watercolour washes, gentle paper grain, no hard cel shading and no digital "
    "vector flatness. Cosy nostalgic domestic mood in BRIGHT, AIRY DAYLIGHT: rooms are filled "
    "with broad soft window light, walls and large surfaces stay light and cheerful, shadows are "
    "pale and short, and there are no gloomy corners or deep blacks anywhere. Colours are light "
    "and gently desaturated like a children's picture book. Interiors are richly furnished and lived "
    "in: patterned wallpaper, floral curtains, potted plants, tea things, wall clocks, framed "
    "photographs, worn timber. People are drawn as REAL people in a friendly illustrated style — "
    "proper faces with age, expression and warmth — never as stick figures, never photorealistic, "
    "never anime. "
    "TIME CODING: anything set in the past is drawn in muted sepia-brown, desaturated tones; "
    "anything set in the present keeps the full warm palette. This contrast is how the viewer knows "
    "which era they are looking at. "
    "Avoid: 3D render, glossy digital art, neon colours, harsh outlines, stick figures"
)
ANI_VARSAYILAN_KARAKTER = (
    "The narrator is a warm, friendly woman in her early fifties: shoulder-length dark wavy hair, "
    "round thin-rimmed glasses, gentle laugh lines, kind expression. She wears exactly one signature "
    "outfit in every frame — a soft sage-green cardigan over a plain white collared blouse with dark "
    "trousers. Her build, face, hair and outfit never change from scene to scene"
)
ANI_CERCEVE = (
    " FRAMING for a 16:9 centre crop of this 1536x1024 image: the top 9% and bottom 9% get cut away, "
    "so every face, sign and key element stays inside 10%-90% of frame height and 8% clear of the "
    "left and right edges. TWO REGISTERS, alternating: a PRESENTER frame places the narrator alone "
    "against a plain pale backdrop with no environment at all, filling 55-75% of frame height, "
    "speaking directly to camera; a WORLD frame places her (or the objects) inside a fully furnished "
    "room or street with a foreground object cutting into the frame, a midground where the action "
    "happens and a background with real perspective. Never blend the two — a backdrop frame has NO "
    "scenery, a world frame is furnished with real depth. "
    "Light the scene to MATCH the measured brightness target given later in this prompt; if no target is given, use one soft dominant source, warm, with soft shadows."
)
ANI_SOZLESME = (
    "RULE ZERO — READ FIRST: this is a narrated first-person memoir explainer, not a character "
    "showcase. AT LEAST 40% OF ALL SCENES YOU WRITE MUST CONTAIN NO PERSON AT ALL (shot types G, I, "
    "J, K, N, O below) and must literally contain the words 'no character in frame'. Before you "
    "finish, COUNT your scenes; if fewer than 40% are person-free, rewrite the weakest ones as "
    "object still lifes, hands-only close-ups, ledgers or screens.\n"
    "SCENE CONTRACT — each scene_prompt is ONE English paragraph of 45-80 words, slots always in "
    "this order: (1) SHOT: the shot-type letter plus the narrator's height as a percent of frame "
    "height, and the word PRESENTER or WORLD for the register; (2) PLACE: for WORLD frames, a "
    "specific domestic or neighbourhood setting with at least 4 concrete named objects, ONE named "
    "warm light source and the era (PAST or PRESENT) — for PRESENTER frames write 'plain pale "
    "backdrop, no scenery'; (3) ACTION: only what the person DOES — the gesture, what she is "
    "holding or touching, the emotion read from eyes and posture. NEVER restate her face, hair, "
    "age or clothing (identity is injected separately). (4) TEXT: either a lettering instruction in "
    "double quotes, or literally \"no text in this image\".\n"
    "ERA CONTRAST: mark every scene PAST or PRESENT. PAST scenes are drawn in muted sepia-brown "
    "desaturated tones with period-correct objects; PRESENT scenes keep full warm colour. Put at "
    "least one PAST scene in every rolling block of 6.\n"
    "SHOT TYPES AND SCALE BANDS (two consecutive scenes must use different bands): "
    "A WIDE ESTABLISHING — person 12-20%, the whole room or street. "
    "B MEDIUM ACTION — person 30-50%, mid-gesture, handling a named object. "
    "C PRESENTER CARD — person 55-75% on a plain pale backdrop, no scenery, speaking to camera. "
    "D LAMPLIT MOMENT — person 30-50%, dim room lit by one lamp or window. "
    "E TWO PEOPLE — the narrator and one other person sharing a task or a table. "
    "F POV HANDS — the narrator's own hands entering the frame from the near edge, doing the action "
    "(opening a tin, cutting cloth, writing on a bill), seen from her eyes. "
    "G LEDGER OR LIST — NO CHARACTER IN FRAME: a handwritten notebook, ledger, receipt or list with "
    "legible dated rows and amounts. "
    "I OBJECT STILL LIFE — NO CHARACTER IN FRAME: one nostalgic object filling the frame in full "
    "detail (a tin, a rotary telephone, a mending basket, a pantry jar). "
    "J HANDS ONLY — NO CHARACTER IN FRAME: close-up of hands doing one step, cropped at the wrists. "
    "K THEN AND NOW — NO CHARACTER IN FRAME: one frame split between a sepia PAST object or scene "
    "and its full-colour PRESENT equivalent, each with a short label. "
    "N SCREEN READOUT — NO CHARACTER IN FRAME: a phone or app screen showing plans, prices or a "
    "balance, using an INVENTED generic brand name, never a real one. "
    "O OVERHEAD FLATLAY — NO CHARACTER IN FRAME: a table seen from directly above with the objects "
    "of the scene arranged on it.\n"
    "FREQUENCY BUDGET per rolling block of 10 scenes — HARD RULE: AT LEAST 4 must be PERSON-FREE "
    "(G, I, J, K, N, O). Also: at least 2 of A/B, at least 2 C presenter cards, at least 1 D, at "
    "least 1 F, at most 1 E. Never use the same type twice in a row and never place two person-free "
    "scenes back to back.\n"
    "PLACE ROTATION: rotate deliberately (kitchen, pantry, sitting room, hallway, porch, garden, "
    "corner shop, bedroom, garage) and change the camera angle every scene.\n"
    "TEXT BUDGET: at most 1 scene in 3 carries lettering. When it does: max 2 lines, each max 3 "
    "words and 14 characters, letters A-Z digits 0-9 spaces and the $ sign only, inside double "
    "quotes. No commas and no thousand separators — write \"1200 A MONTH\" not \"$1,200\". "
    "Handwritten ledger rows are exempt from the word limit but must stay short and legible. "
    "Text never sits in the top or bottom 9% of the frame.\n"
    # ThriftyHazel'in iki imza cihazi (216 karede tutarli):
    "COUNTDOWN BADGE — apply ONLY if the narration is a numbered list that counts down or up "
    "(\"rule 11\", \"number 9\", \"the third thing\"). On the OPENING scene of each numbered item add "
    "to the TEXT slot exactly: watermark numeral \"11\" (using that item's number). It is rendered "
    "very large in the TOP-RIGHT corner as a soft, low-contrast, semi-transparent numeral in a muted "
    "tone of the scene's own palette — a quiet watermark behind the action, NOT a bright badge, "
    "sticker, circle or outlined graphic, and never overlapping a face or the data card. Put it on "
    "the opening scene of an item only. If the script is not a numbered list, no numerals at all.\n"
    "CHAPTER CARD — if the script clearly breaks into 2-4 thematic sections, insert ONE full-frame "
    "card at the start of each section: a deep warm-brown panel with an ornate decorative border, "
    "the section name in elegant cream serif capitals across two lines (max 4 words), AND four to "
    "six small simple illustrations of objects from that section scattered around the title (for a "
    "cleaning section: a spray bottle, a mop, a pipe, a cloth). No character, no scenery. Write it "
    "as its own scene of shot type C with 'no character in frame'.\n"
    "REJECTION MARK — when the narration says something is wasteful, wrong or should be dropped, "
    "draw a single bold hand-drawn red cross over that one object. Only one crossed object per "
    "scene, and never over a person.\n"
    + KARE_CESITLILIGI + DESTEK_PLANLAYICI + VERI_KARTI_PLAN + MEKAN_SUREKLILIGI + CEKIM_OLCEGI + SEMA_STIL_KILIDI
)

ANIMASYON_PROFIL = {
    "ad": "Animasyon (Anlatı)",
    "ozet": "Elle çizilmiş editorial-karikatür anlatı animasyonu; detaylı ortamlar, sinematik çekimler",
    # MALIYET/TEMPO: 9 sn = 11 dk'da ~73 gorsel (~$0.95/video). Asagidaki olcum notuna bak —
    # bu stil icin referans temposu olculmedi, yavas (12 sn) ve hizli (5 sn) uclarin ortasi
    # secildi. Daha ucuz istersen ANIM_SAHNE_SN=12.
    "sahne_sn": float(os.environ.get("ANIM_SAHNE_SN", "9")), "kelime": 14,
    "footage_pct": 0, "overlay": "yok",
    "altyazi": "orta", "motion": "sinematik", "mag": None,  # yazi YOK + blur YOK (1080p render hizli)
    "gorsel_ek": ANIM_STIL,
    "varsayilan_karakter": ANIM_VARSAYILAN_KARAKTER,
    "cerceve": ANIM_CERCEVE,
    "sahne_sozlesme": ANIM_SOZLESME,
}

# Explainer profili — ayni iskelet, farkli sanat yonetimi/sozlesme
EXPLAINER_PROFIL = {
    "ad": "Animasyon (Eğitici)",
    "ozet": "Kalın konturlu explainer; canlı renkler + beyaz diyagram kartları, etiket ve oklar",
    "sahne_sn": float(os.environ.get("EXPLAINER_SAHNE_SN", "5")), "kelime": 14,
    "footage_pct": 0, "overlay": "yok",
    "altyazi": "orta", "motion": "sinematik", "mag": None,
    "gorsel_ek": EXP_STIL,
    "varsayilan_karakter": EXP_VARSAYILAN_KARAKTER,
    "cerceve": EXP_CERCEVE,
    "sahne_sozlesme": EXP_SOZLESME,
}

HIKAYE_PROFIL = {
    "ad": "Animasyon (Hikaye)",
    "ozet": "Sade beyaz stickman + zengin boyalı sinematik dünya; macera/what-if anlatımı",
    "sahne_sn": float(os.environ.get("HIKAYE_ANIM_SAHNE_SN", "9")), "kelime": 14,
    "footage_pct": 0, "overlay": "yok",
    "altyazi": "orta", "motion": "sinematik", "mag": None,
    "gorsel_ek": HIK_STIL,
    "varsayilan_karakter": HIK_VARSAYILAN_KARAKTER,
    "cerceve": HIK_CERCEVE,
    "sahne_sozlesme": HIK_SOZLESME,
}

KALEM_PROFIL = {
    "ad": "Animasyon (Renkli Kalem)",
    "ozet": "Kremli kâğıda renkli kurşun kalem; sıcak gündelik mekânlar, imza aksesuarlı stickman",
    "sahne_sn": float(os.environ.get("KALEM_SAHNE_SN", "12")), "kelime": 14,
    "footage_pct": 0, "overlay": "yok",
    "altyazi": "orta", "motion": "sinematik", "mag": None,
    "gorsel_ek": KALEM_STIL,
    "varsayilan_karakter": KALEM_VARSAYILAN_KARAKTER,
    "cerceve": KALEM_CERCEVE,
    "sahne_sozlesme": KALEM_SOZLESME,
    "palet": "aussie-kalem",     # bu stilin dogal paleti (kullanici degistirebilir)
}

ANI_PROFIL = {
    "ad": "Animasyon (Anı Defteri)",
    "ozet": "Sıcak nostaljik illüstrasyon; gerçekçi anlatıcı, geçmiş/bugün karşıtlığı, ev içi",
    "sahne_sn": float(os.environ.get("ANI_SAHNE_SN", "12")), "kelime": 14,
    "footage_pct": 0, "overlay": "yok",
    "altyazi": "orta", "motion": "sinematik", "mag": None,   # referans kanal altyazi KULLANIYOR
    "gorsel_ek": ANI_STIL,
    "varsayilan_karakter": ANI_VARSAYILAN_KARAKTER,
    "cerceve": ANI_CERCEVE,
    "sahne_sozlesme": ANI_SOZLESME,
    "palet": "ani-defteri",
    "gerisayim": True,   # "N sey" listelerinde kose rozeti
}

# ── SAHNE TEMPOSU NEDEN STIL BASINA AYRI (5 Agu 2026 olcumu) ──
# Referans kanallarin videolari ffmpeg sahne-kesme ile kare kare olculdu (592 sahne):
#   ThriftyHazel (ani-defteri)      medyan 12.8 sn   sahnelerin %90'i 8 sn'den uzun
#   Aussie Bruce (renkli-kalem)     medyan 11.9 sn   %98'i 8 sn'den uzun
#   Paint Explainer                 medyan  5.0 sn   iki modlu (hizli liste + yavas anlati)
#   Simple Explainer                medyan  2.8 sn   %53'u 3 sn'den kisa
# Hepsi tek bir ANIM_SAHNE_SN=5 sabitine baglanmisti; yani yavas anlati stilleri 2.5 kat
# hizli, hizli explainer ise 2 kat yavas kurgulaniyordu. Artik her stil kendi olcusunu
# kullanir. MALIYET: sahne uzadikca ayni dakika icin daha AZ gorsel uretilir — 11 dk'lik
# bir ani-defteri videosu ~130 gorsel yerine ~55 gorselle biter.
# Animasyon ALT-STILLERI (documentary'deki 3 edit stili gibi)
ANIMASYON_STILLERI = {
    "anlati-deneme": ANIMASYON_PROFIL,
    "egitici-explainer": EXPLAINER_PROFIL,
    "hikaye-whatif": HIKAYE_PROFIL,
    "renkli-kalem": KALEM_PROFIL,
    "ani-defteri": ANI_PROFIL,
}
VARSAYILAN_ANIM = "anlati-deneme"

# ═══════════════ RENK PALETI (kanal genelinde renk kimligi) ═══════════════
# Neden: stil promptu "muted ochre/sage" gibi KELIME tarif ediyordu -> model her sahnede
# baska bir yorum uretiyordu. Cozum: KESIN HEX listesi (palet_olc dersinin aynisi —
# rengi tarif etme, SAYIYLA ver). Palet DUNYAYI yonetir; karakterin kilitli renkleri
# her zaman ustundur (yoksa beyaz<->turuncu salinimi geri gelir).
PALETLER = {
    "otomatik": {"ad": "Otomatik (stile bırak)", "renkler": [],
                 "ozet": "Seçili animasyon stilinin kendi renk ailesi kullanılır"},
    "aussie-kalem": {"ad": "Sıcak Kalem (Aussie)", "ozet": "Kremli kâğıt, adaçayı, altın, kiremit",
                     "renkler": ["#F0E4CC", "#E0CBA0", "#7B8B5A", "#F2C230", "#B5651D", "#7A97B8"]},
    "vintage-editorial": {"ad": "Vintage Editorial", "ozet": "Oker, adaçayı, tozlu mavi, soluk tuğla",
                          "renkler": ["#EFE3CA", "#C8963E", "#8A9A7B", "#6E8399", "#A85A44", "#4A4038"]},
    "sicak-toprak": {"ad": "Sıcak Toprak", "ozet": "Terrakota, kum, zeytin, pas",
                     "renkler": ["#E3C99A", "#C1663F", "#7D7A45", "#9B4722", "#D9A574", "#3B2A1E"]},
    "soguk-mavi": {"ad": "Soğuk Mavi", "ozet": "Lacivert, deniz, buz, arduvaz",
                   "renkler": ["#EDE7D9", "#1F3A5F", "#2E7D8C", "#BFD9E0", "#5A7184", "#121D2B"]},
    "canli-explainer": {"ad": "Canlı Explainer", "ozet": "Kırmızı, sarı, mavi, beyaz, siyah",
                        "renkler": ["#FFFFFF", "#E63946", "#F4C430", "#2A6FDB", "#2BB673", "#111111"]},
    "gece-neon": {"ad": "Gece Neon", "ozet": "İndigo, magenta, camgöbeği, kömür",
                  "renkler": ["#1B1035", "#E0409A", "#38D6E0", "#F2A65A", "#221C2E", "#EDE6F5"]},
    "pastel-yumusak": {"ad": "Pastel Yumuşak", "ozet": "Pudra, nane, tereyağı, leylak",
                       "renkler": ["#FBF5EC", "#F3C8C2", "#BFE0CE", "#F7E6A8", "#C9BEE3", "#6E6A78"]},
    "sepya-belgesel": {"ad": "Sepya Belgesel", "ozet": "Koyu sepya, kahve, ten, kemik",
                       "renkler": ["#E6D8BF", "#C4A177", "#8C6A47", "#4A3520", "#241A10", "#9C8663"]},
    "orman-yesil": {"ad": "Orman Yeşili", "ozet": "Koyu orman, yosun, eğrelti, kabuk",
                    "renkler": ["#D7E2CC", "#93B06A", "#5E7F4A", "#234A2E", "#6B4A2E", "#16241A"]},
    # ThriftyHazel'in 100 karesinden OLCULDU. Eski palette #4A3728 (parlaklik 57) vardi,
    # model surekli ona yasleniyordu -> cikti kapkaranlik. Olculen baskin renklerin 8'i
    # 145+ parlaklikta; palet ona gore acildi.
    "ani-defteri": {"ad": "Anı Defteri", "ozet": "Açık krem, nane, kum, mercan — aydınlık",
                    "renkler": ["#F5F0DC", "#E8DCC0", "#D4D4CC", "#A8C8B8", "#E0956F", "#B08050"]},
    "mono-kontrast": {"ad": "Mono + Tek Vurgu", "ozet": "Siyah-beyaz-gri + tek kırmızı vurgu",
                      "renkler": ["#FFFFFF", "#D8D4CC", "#8C8880", "#3A3835", "#121110", "#D93025"]},
}
VARSAYILAN_PALET = "otomatik"
_HEX_RE = __import__("re").compile(r"^#[0-9A-Fa-f]{6}$")


def palet_renkleri(secim: str, ozel: str = "") -> list:
    """Palet kimligi -> hex listesi. 'ozel' verilirse (virgulle ayrilmis hexler) o kullanilir.
    Gecersiz/bos girdi -> [] (palet kilidi uygulanmaz, stilin kendi renk ailesi kalir)."""
    if (secim or "").strip() == "ozel" or (not secim and ozel):
        out = []
        for h in (ozel or "").replace(";", ",").split(","):
            h = h.strip()
            if not h.startswith("#"):
                h = "#" + h
            if _HEX_RE.match(h) and h.upper() not in out:
                out.append(h.upper())
        return out[:8]
    return list(PALETLER.get((secim or "").strip(), {}).get("renkler", []))


def palet_prompt(secim: str, ozel: str = "") -> str:
    """Gorsel promptuna eklenecek RENK KILIDI. Bos palet -> bos metin (davranis degismez)."""
    renkler = palet_renkleri(secim, ozel)
    if len(renkler) < 2:
        return ""
    liste = ", ".join(renkler)
    return (
        " CHANNEL COLOUR PALETTE (locked, identical in every scene of every video of this channel): "
        f"build the whole picture from this exact fixed set of hex colours — {liste}. Every surface, "
        "garment, prop, sky, ground and shadow must be one of these hues, or a lighter tint, darker "
        "shade or direct mix of two of them; do NOT introduce any hue outside this set. Vary WHICH of "
        "them dominates from scene to scene (one scene led by the darkest, the next by the warmest) so "
        "consecutive frames never look identical, but never leave the set. "
        "PRIORITY: if the locked character's own colours differ from this palette, the CHARACTER'S "
        "colours always win — this palette governs the world around the character, not their identity."
    )


# ═══════════════ ARKA PLAN (mekan dunyasi + yogunluk) ═══════════════
# Neden ayri bir eksen: 567 referans karesinin analizi iki ZIT dogru gosterdi —
# Paint Explainer (1.96M) karelerinin cogu BOMBOS beyaz zeminde tek oge; Bruce ve
# Serious History ise tikabasa dolu mekanlar kuruyor. Ikisi de calisiyor. Yani
# "her yer dolu olsun" evrensel bir kural DEGIL, kanal karari. Burasi o karar.
#
# DIKKAT: stil promptlari (*_CERCEVE) yogunluk dayatiyor ("objects must run to all
# four edges"). Arka plan secimi bununla CELISEBILIR. Renk paletindeki dersin aynisi:
# celiskiyi cozmeden birakma -> arka plan blogu en SONA eklenir ve oncelikli oldugunu
# acikca soyler.
ARKA_PLANLAR = {
    "otomatik": {"ad": "Otomatik (stile bırak)", "yogunluk": "-",
                 "ozet": "Seçili animasyon stilinin kendi mekân kuralı geçerli", "prompt": ""},
    "sade-beyaz": {
        "ad": "Sade Beyaz", "yogunluk": "sade",
        "ozet": "Bomboş beyaz zemin, tek öğe — Paint Explainer düzeni",
        "prompt": ("BACKGROUND: a plain empty white field. Draw ONLY the subject the scene names "
                   "and nothing else — no room, no furniture, no scenery, no horizon, no texture. "
                   "Generous empty space around the subject is the point, not a flaw. A thin ground "
                   "shadow is the only extra mark allowed.")},
    "sade-renkli": {
        "ad": "Sade Renk Alanı", "yogunluk": "sade",
        "ozet": "Tek düz renk zemin, dikkat dağıtan detay yok",
        "prompt": ("BACKGROUND: one single flat colour field filling the whole frame, chosen from the "
                   "locked palette. No scenery, no objects, no gradient, no texture. Only the subject "
                   "the scene names sits on it, with a simple flat ground shadow.")},
    "gundelik-ev": {
        "ad": "Gündelik Ev/Mahalle", "yogunluk": "zengin",
        "ozet": "Mutfak, salon, bahçe, iş yeri — yaşanmış detaylı mekânlar",
        "prompt": ("BACKGROUND: a specific, lived-in everyday place — a kitchen, living room, front "
                   "yard, workplace lunch room, home office, shed or suburban street. Fill it with at "
                   "least 5 small true-to-life details (appliances, notices, jars, plants, tools, "
                   "framed photos, worn floors) running to all four edges, with real perspective and "
                   "one named light source.")},
    "tarihi-donem": {
        "ad": "Tarihi Dönem", "yogunluk": "zengin",
        "ozet": "Kale, ordugâh, eski sokak, saray — dönem detaylı",
        "prompt": ("BACKGROUND: a period-accurate historical place — castle wall, war camp, throne "
                   "hall, cobbled old street, harbour, marketplace. Include at least 4 concrete "
                   "period props (banners, barrels, torches, weapons racks, carts) and build three "
                   "depth layers with atmospheric haze on the far one.")},
    "doga-manzara": {
        "ad": "Doğa / Manzara", "yogunluk": "zengin",
        "ozet": "Orman, dağ, okyanus, çöl — geniş sinematik doğa",
        "prompt": ("BACKGROUND: a wide natural landscape — forest, mountain range, ocean, desert, "
                   "river valley, cave. Build a dark framing foreground, a midground where the action "
                   "happens and a hazy receding far vista, with weather and time of day clearly "
                   "readable and one dominant light source.")},
    "sehir-modern": {
        "ad": "Modern Şehir", "yogunluk": "zengin",
        "ozet": "Cadde, ofis, dükkân, metro — çağdaş kent dokusu",
        "prompt": ("BACKGROUND: a contemporary urban place — a street with shopfronts, an open-plan "
                   "office, a supermarket aisle, a subway platform, an apartment interior. Include "
                   "signage, glazing, vehicles or crowds as depth layers, with believable perspective "
                   "running to all four edges.")},
    "calisma-panosu": {
        "ad": "Pano / Masa Üstü", "yogunluk": "orta",
        "ozet": "Mantar pano, beyaz tahta, masa — açıklayıcı kurulum",
        "prompt": ("BACKGROUND: an explainer setup — a corkboard with pinned cards and string, a "
                   "whiteboard with a diagram, or a desk seen from above with papers, pens and notes. "
                   "The board or desktop fills most of the frame and IS the environment; keep the "
                   "surrounding room minimal and out of focus.")},
    "karanlik-sinematik": {
        "ad": "Karanlık Sinematik", "yogunluk": "orta",
        "ozet": "Tek ışık kaynağı, koyu zemin, dramatik",
        "prompt": ("BACKGROUND: a dark, low-key environment lit by exactly ONE visible source — a "
                   "lamp, fire, screen, doorway or beam. Most of the frame falls into deep shadow "
                   "with only the essential shapes catching light; keep detail sparse and let the "
                   "darkness do the work.")},
}
VARSAYILAN_ARKAPLAN = "otomatik"

# ═══════════════ ISIK DUZEYI ═══════════════
# 1 Agu 2026 OLCUMU: hedef kanal (ThriftyHazel, 120 kare) ortalama parlaklik 162/255,
# doygunluk 57. Bizim ciktimiz 114 / 95 -> %30 daha KARANLIK, %67 daha DOYGUN (camurlu).
# Sebep: stil ve arka plan promptlari "tek isik kaynagi / derin golge / lamba isigi"
# vurguluyordu. Cozum: isik AYRI eksen olsun ve stilin karanlik egilimini EZEBILSIN.
ISIK_DUZEYLERI = {
    "parlak-gunduz": {
        "ad": "Parlak Gündüz", "ozet": "Aydınlık, yumuşak, gölgesiz — YouTube'da en okunaklısı",
        "prompt": (" LIGHTING — HIGH KEY (this OVERRIDES any earlier instruction about a single "
                   "light source, deep shadow, dim rooms or dramatic lighting): the whole picture is "
                   "brightly and EVENLY lit by broad soft daylight. Walls, floors and large surfaces "
                   "sit in the LIGHT half of the value range, never in gloom. Shadows are soft, pale "
                   "and short; no deep blacks, no heavy vignette anywhere. "
                   "BRIGHT IS NOT WASHED OUT — this is the most common failure: keep STRONG local "
                   "contrast and clearly distinct colours. Give the main objects and furniture their "
                   "own definite hues (a mint-green cupboard, a coral apron, a red tin) that stand "
                   "apart from the pale wall behind them, and keep crisp dark linework and clear "
                   "mid-tone accents so shapes separate instantly. A picture where everything is the "
                   "same pale beige is WRONG. Light and airy overall, but never flat, milky or "
                   "faded — it must read clearly at a glance on a small phone screen.")},
    "dengeli": {
        "ad": "Dengeli", "ozet": "Orta aydınlık, yumuşak gölge",
        "prompt": (" LIGHTING: soft natural daylight with gentle, readable shadows. Keep the overall "
                   "value in the middle-to-light range; avoid both washed-out flatness and deep "
                   "murky shadow. Colours natural, never oversaturated.")},
    "karanlik-sinematik": {
        "ad": "Karanlık Sinematik", "ozet": "Tek ışık kaynağı, derin gölge — dram için",
        "prompt": (" LIGHTING: low-key and dramatic, one visible light source, deep directional "
                   "shadows and rich darks shaping the composition.")},
}
VARSAYILAN_ISIK = "parlak-gunduz"


def isik_prompt(secim: str) -> str:
    v = ISIK_DUZEYLERI.get((secim or "").strip())
    return v["prompt"] if v else ""



def arkaplan_prompt(secim: str) -> str:
    """Cerceve blogunun SONUNA eklenecek mekan yonergesi. 'otomatik'/bilinmeyen -> bos."""
    a = ARKA_PLANLAR.get((secim or "").strip())
    if not a or not a.get("prompt"):
        return ""
    ek = " " + a["prompt"]
    if a.get("yogunluk") == "sade":
        # Stil bloklari "hicbir yer bos kalmasin" diyor; sade arka plan bunu ezmeli.
        ek += (" PRIORITY: this background instruction OVERRIDES any earlier instruction to fill the "
               "frame with objects, furniture, clutter or scenery running to the edges. Emptiness "
               "here is deliberate.")
    return ek


def profil_ek_oku(prof) -> dict:
    """Stil sozlugundeki `_profil` blogunu GUVENLI oku (Faz I-2c).

    `_profil`, eski `EDIT_STILLERI` bicimine SIGMAYAN boyutlari tasir
    (palet, ses, kanit, qa, gecis, dagitim, surum).

    ⚠ Eski stil girdilerinde bu blok YOKTUR -> `{}` doner ve cagiran taraf
    bugunku davranisini AYNEN surdurur. Bozuk/eksik tipte de `{}` doner:
    bu okuyucu HICBIR DURUMDA istisna firlatmaz.
    """
    try:
        ek = (prof or {}).get("_profil")
        return dict(ek) if isinstance(ek, dict) else {}
    except Exception:
        return {}


def bilesik_stile_cevir(edit_id):
    """Yeni-nesil (Faz I-2b) bilesik profil kimligini eski stil alanlarina cevir.

    ⚠ NEDEN VAR: `EDIT_STILLERI` disindaki her kimlik bugune kadar SESSIZCE
    `VARSAYILAN_EDIT`e dusuyordu — kullanici bambaska bir stil sectigini
    saniyordu. Artik kimlik `stil_profili` kaydinda varsa GERCEKTEN o profille
    uretilir; yoksa eski sessiz-varsayilan davranisi korunur.

    Donus: eski bicimde stil sozlugu (`_profil` blogu dahil) ya da None.
    ISTISNA FIRLATMAZ — cozulemezse cagiran taraf eski yolunu kullanir.
    """
    if not edit_id or stil_profili is None:
        return None
    try:
        p = stil_profili.profil_al(edit_id)
    except KeyError:
        return None          # kayitta yok -> eski sessiz-varsayilan davranisi
    except Exception as e:
        print(f"  bilesik stil okunamadi ({edit_id}): {type(e).__name__}",
              file=sys.stderr)
        return None
    try:
        eski = stil_profili.eski_edit_stiline(p)
    except Exception as e:
        print(f"  bilesik stil eski bicime cevrilemedi ({edit_id}): "
              f"{type(e).__name__}", file=sys.stderr)
        return None
    eski["_stil_kimligi"] = edit_id
    print(f"  BILESIK STIL: '{edit_id}' v{p.get('surum')} kullaniliyor "
          f"(sema {getattr(stil_profili, 'SEMA_SURUM', '?')})", file=sys.stderr)
    # ⚠ FAZ I-2d: gorsel imza artik PROFILDEN turetiliyor (bkz.
    # `bilesik_gorsel_imza`). Eski tablolarda karsilik olmamasi ARTIK sessiz
    # kalite kaybi DEGIL. Yine de turetme bos cikarsa bunu SESLI soyleriz:
    # kullanicinin sebebini bilmedigi bir dusus yasamasindansa loga yazilir.
    _imza = bilesik_gorsel_imza(eski.get("_profil"))
    if not _imza["uygulandi"]:
        print(f"  ⚠ '{edit_id}' icin bilesik profilden gorsel imza "
              f"TURETILEMEDI; eski tabloya dusuluyor "
              f"(efekt={len(EFEKT_TEMEL.get(edit_id, []))}, "
              f"gecis={GECIS_IMZASI.get(edit_id, ('yok', 0))[0]}). "
              f"Gerekce: {'; '.join(_imza['gerekce']) or 'belirtilmedi'}",
              file=sys.stderr)
    return eski


def profil_coz(tur, edit_id, ek_profil=None):
    """tur: 'animasyon' -> ANIMASYON_STILLERI; 'hikaye' -> HIKAYE_STILLERI; digeri -> EDIT_STILLERI.

    ⚠ FAZ I-2c: `ek_profil` verilirse (ya da `edit_id` eski sozlukte YOK ama
    `stil_profili` kaydinda VARSA) sonuc eski stil sozlugunun UZERINE yazilir.
    Ustune yazma her zaman bir TABAN sozluk uzerinde olur; boylece yeni bicimin
    tasiyamadigi eski alanlar (`gorsel_ek`, `mag`, `saha_etiketi`, `etiket_pct`)
    tabandan gelir ve asagidaki `prof["gorsel_ek"]` gibi zorunlu okumalar
    KeyError vermez.

    ⚠ GERILEME YOK: `ek_profil` None ve `edit_id` eski sozlukte varsa (ya da
    bosza) fonksiyon eskisiyle BIREBIR ayni sozlugu dondurur.
    """
    if tur == "animasyon":
        taban = ANIMASYON_STILLERI.get(edit_id or VARSAYILAN_ANIM,
                                       ANIMASYON_STILLERI[VARSAYILAN_ANIM])
    elif tur == "hikaye":
        taban = HIKAYE_STILLERI.get(edit_id or VARSAYILAN_HIKAYE,
                                    HIKAYE_STILLERI[VARSAYILAN_HIKAYE])
    else:
        taban = EDIT_STILLERI.get(edit_id or VARSAYILAN_EDIT,
                                  EDIT_STILLERI[VARSAYILAN_EDIT])
        if ek_profil is None and edit_id and edit_id not in EDIT_STILLERI:
            ek_profil = bilesik_stile_cevir(edit_id)
    if not isinstance(ek_profil, dict) or not ek_profil:
        return taban
    return {**taban, **ek_profil}


def karakter_analiz(kar_yol: str) -> str:
    """Referans karakteri gpt-4.1-mini vision ile DETAYLI analiz eder -> character_lock metni.
    Bu metin her AI sahne promptuna KELIMESI KELIMESINE eklenir (gorsel referansla birlikte
    ikili garanti: karakter her sahnede birebir ayni cikar)."""
    if not kar_yol or not os.path.exists(kar_yol):
        return ""
    try:
        import base64
        with open(kar_yol, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        body = {
            "model": "gpt-4.1-mini",
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": (
                    "Describe this reference CHARACTER as a precise, reusable visual lock in ONE "
                    "compact English paragraph (35-60 words): species/type, exact colors, face, "
                    "hair, outfit/markings, body proportions, distinctive features. No scene/"
                    "background, ONLY the character so it can be redrawn IDENTICALLY every time. "
                    "Start with 'The character is'.")},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
            ]}],
            "max_tokens": 200, "temperature": 0.2,
        }
        j = oai_chat(body, timeout=90)
        return j["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"  karakter_analiz hata: {str(e)[:160]}", file=sys.stderr)
        return ""


def palet_olc(img_yol: str, adet: int = 5) -> list:
    """Referans gorselden BASKIN RENKLERI piksel duzeyinde olc (median-cut).
    LLM'e renk TAHMIN ETTIRMEK yerine gercek hex degerleri cikarilir -> 'turuncu karakter
    pembeye dondu' kaymasi kokten kapanir (renk artik kesin sayi olarak prompta girer)."""
    try:
        from PIL import Image
        im = Image.open(img_yol).convert("RGB")
        # kenar %12'yi kirp: arka plan yerine OZNENIN rengini olc
        w, h = im.size
        k = (int(w * 0.12), int(h * 0.12), int(w * 0.88), int(h * 0.88))
        im = im.crop(k).resize((160, 160))
        q = im.quantize(colors=adet, method=Image.MEDIANCUT)
        pal = q.getpalette()[: adet * 3]
        sayim = sorted(q.getcolors() or [], reverse=True)   # [(piksel, indeks), ...]
        out = []
        for piksel, idx in sayim[:adet]:
            r, g, b = pal[idx * 3: idx * 3 + 3]
            out.append({"hex": f"#{r:02X}{g:02X}{b:02X}",
                        "oran": round(piksel / (160 * 160), 3)})
        return out
    except Exception as e:
        print(f"  palet_olc hata: {str(e)[:120]}", file=sys.stderr)
        return []


KUNYE_ALANLARI = ("tur", "govde_rengi", "ikincil_renk", "kafa", "gozler", "sac",
                  "kiyafet", "oranlar", "ayirt_edici")


def _kunye_tek_okuma(img_yol: str, sicaklik: float, paletler: list) -> dict:
    """Referansi TEK vision cagrisiyla yapili kimlik kunyesine cevir."""
    import base64
    with open(img_yol, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    pal_txt = ", ".join(f"{p['hex']} (%{int(p['oran']*100)})" for p in paletler[:5]) or "yok"
    istek = (
        "You are a character model sheet analyst. Describe ONLY the character in this reference "
        "image as a reusable identity card. Return STRICT JSON with exactly these keys: "
        '"tur" (species/type, 3-6 words), "govde_rengi" (main body colour — pick the closest HEX '
        f"from this measured palette: {pal_txt}), "
        '"ikincil_renk" (secondary colour, HEX from the same palette or empty), '
        '"kafa" (head shape, 4-10 words), "gozler" (eyes, 4-10 words), "sac" (hair/fur on head, '
        '4-10 words or "none"), "kiyafet" (clothing/markings, 4-12 words or "none"), '
        '"oranlar" (body proportions, 4-10 words), "ayirt_edici" (single most distinctive '
        'permanent feature, 3-8 words). '
        "RULES: describe ONLY permanent identity. NEVER describe the pose, the camera angle, the "
        "background, the lighting, or any object the character is holding — those are temporary. "
        "If a field is not clearly visible, use an empty string rather than guessing. English only."
    )
    body = {
        "model": "gpt-4.1-mini",
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": istek},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
        ]}],
        "response_format": {"type": "json_object"},
        "max_tokens": 500, "temperature": sicaklik,
    }
    j = oai_chat(body, timeout=90)
    ic = (j.get("choices") or [{}])[0].get("message", {}).get("content") or "{}"
    try:
        return json.loads(ic)
    except Exception:
        return {}


def kimlik_kunyesi(img_yol: str) -> dict:
    """COK ASAMALI KIMLIK ANALIZI (kullanici: '3-4 kere suzgecten gecirsin').
    1) piksel duzeyinde palet olcumu (kod, $0)
    2) bagimsiz vision okumasi (dusuk sicaklik)
    3) IKINCI bagimsiz vision okumasi (yuksek sicaklik, ilkinden habersiz)
    4) KOD UZLASISI: iki okuma ayni diyorsa alan GECERLI, celisiyorsa alan ATILIR
       (celisen alan = modelin uydurdugu alandir; 100 karede 100 farkli uydurulur).
    Donen: {alanlar..., _palet, _guven} — guven dusukse cagiran uyarir."""
    paletler = palet_olc(img_yol)
    a = _kunye_tek_okuma(img_yol, 0.15, paletler)
    b = _kunye_tek_okuma(img_yol, 0.85, paletler)
    if not a and not b:
        return {}
    kunye, onayli, dolu = {}, 0, 0
    for alan in KUNYE_ALANLARI:
        va = str(a.get(alan, "") or "").strip()
        vb = str(b.get(alan, "") or "").strip()
        if not va and not vb:
            continue
        dolu += 1
        # renk alanlarinda birebir, metin alanlarinda kelime ortusmesi arar
        if alan.endswith("rengi") or alan == "ikincil_renk":
            uyum = va.upper() == vb.upper()
        else:
            ka, kb = set(va.lower().split()), set(vb.lower().split())
            uyum = bool(ka & kb) and len(ka & kb) >= max(1, min(len(ka), len(kb)) // 3)
        if uyum:
            kunye[alan] = va or vb
            onayli += 1
        # celisen alan bilerek ATILIR (uydurma alani promptta tekrarlamak zarardir)
    kunye["_palet"] = paletler
    kunye["_guven"] = round(onayli / dolu, 2) if dolu else 0.0
    return kunye


def kunye_metni(k: dict) -> str:
    """Kunyeyi POZITIF, olculu bir kimlik cumlesine cevir (negatif ifade YOK).
    Tasarim ilkesi: yasakli seyi ADLANDIRMA — 'pembe olmasin' demek yerine kesin rengi soyle."""
    if not k:
        return ""
    p = []
    if k.get("tur"):
        p.append(f"a {k['tur']}")
    if k.get("govde_rengi"):
        p.append(f"body colour exactly {k['govde_rengi']}")
    if k.get("ikincil_renk"):
        p.append(f"secondary colour {k['ikincil_renk']}")
    for alan, on in (("kafa", "head"), ("gozler", "eyes"), ("sac", "hair"),
                     ("kiyafet", "wearing"), ("oranlar", "proportions"),
                     ("ayirt_edici", "distinctive")):
        if k.get(alan) and str(k[alan]).lower() not in ("none", "yok"):
            p.append(f"{on}: {k[alan]}")
    if not p:
        return ""
    metin = "The main character is " + ", ".join(p) + "."
    # IMZA AKSESUAR (6. referans dersi): minimal stickman'de kimlik yuzden degil TEK bir
    # ayirt edici parcadan okunur. Onu ayrica ve emir kipiyle tekrarla — yoksa model
    # sahneler arasinda "unutup" birakiyor ve karakter baskasina donuyor.
    imza = k.get("ayirt_edici") or k.get("kiyafet")
    if imza and str(imza).lower() not in ("none", "yok"):
        metin += (f" SIGNATURE (never omitted): {imza} — this must be clearly visible and identical "
                  "in EVERY frame the character appears in; it is how the viewer recognises them. "
                  "No other figure in any scene may wear or carry it.")
    return metin


# ═══════════ STIL KUNYESI — yuklenen stil gorselinin COK ASAMALI analizi ═══════════
# SORUN: stil_analiz() TEK cumle (20-40 kelime) uretiyordu, ama secili stilin kendi
# sanat yonergesi (ANIM_STIL vb.) 150-250 kelime. Iki blok yarisinca UZUN olan kazaniyor
# -> kullanici stil gorseli yukluyor ama cikti hala dahili stile benziyor.
# COZUM: karakter kunyesinin aynisi (palet olcumu + 2 bagimsiz okuma + kod uzlasisi),
# ve uretilen kunye dahili sanat yonergesinin YERINE gecer (yanina degil).
# 16 alan: bir gorsel stili KOPYALANABILIR kilan her sey. 8 alanla stil "yaklasik"
# tutuluyordu; kalan bosluklari model kendi genel AI estetigiyle dolduruyordu.
# Amac (Polat, 3 Agu 2026): YouTube'da ~100 animasyon stili var, hicbirini elle
# kodlamadan SADECE referans karelerden kilitlemek.
STIL_ALANLARI = ("medyum", "cizgi", "dolgu", "golgeleme", "kenar", "doku",
                 "isik", "kontrast", "detay", "arka_plan", "karakter_cizim",
                 "oranlar", "renk_uyumu", "yazi", "ruh", "kacinilacak")


def _stil_tek_okuma(img_yol: str, sicaklik: float, paletler: list) -> dict:
    import base64
    with open(img_yol, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    pal_txt = ", ".join(f"{p['hex']} (%{int(p['oran']*100)})" for p in paletler[:6]) or "yok"
    istek = (
        "You are a senior art-direction analyst. Another artist must be able to redraw ANY new "
        "scene so that it looks like it came from the SAME production as this image. Describe ONLY "
        "the visual style, in enough detail that nothing is left to imagination. "
        "Return STRICT JSON with exactly these keys:\n"
        '"medyum" (medium and rendering technique, 8-18 words — e.g. "flat digital vector cartoon, '
        'clean fills, no visible brush or pencil marks")\n'
        '"cizgi" (outlines: present or absent, their colour, weight, evenness, 6-16 words, '
        'or "none" if the art has no outlines)\n'
        '"dolgu" (how areas are filled: flat solid / two-tone / soft gradient / painterly / '
        'hatched, 5-14 words)\n'
        '"golgeleme" (shading model and how many tones, 5-14 words)\n'
        '"kenar" (edge quality: crisp vector / slightly wobbly hand-drawn / soft airbrushed / '
        'rough, 4-10 words)\n'
        '"doku" (surface texture or grain over the art, 4-12 words, or "none" if perfectly clean)\n'
        '"isik" (light direction, softness and whether shadows are cast, 6-14 words)\n'
        '"kontrast" (one of: low, medium, high)\n'
        '"detay" (one of: minimal, moderate, high, very high)\n'
        '"arka_plan" (how backgrounds are treated — density, depth, perspective, 6-14 words)\n'
        '"karakter_cizim" (CRITICAL — exactly how people are drawn: face construction, eye and '
        'mouth style, hair treatment, hands, how much anatomical detail, 10-22 words)\n'
        '"oranlar" (body proportions and stylisation level, 5-12 words)\n'
        '"renk_uyumu" (colour harmony and saturation behaviour, 6-14 words)\n'
        '"yazi" (how any on-image lettering is drawn, 5-12 words, or "none")\n'
        '"ruh" (overall mood in 3-6 words)\n'
        '"kacinilacak" (3-6 things this style is clearly NOT — name the nearest wrong looks that '
        "an AI would drift into, e.g. \"photorealism, 3D render, anime eyes, heavy grain\")\n"
        f"The measured dominant colours are: {pal_txt}. "
        "RULES: describe ONLY style. NEVER describe the subject, the character's identity, the "
        "objects or what is happening — those change every frame. If a field is not clearly "
        "readable, use an empty string rather than guessing. English only."
    )
    body = {
        "model": "gpt-4.1-mini",
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": istek},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
        ]}],
        "response_format": {"type": "json_object"},
        "max_tokens": 1100, "temperature": sicaklik,
    }
    j = oai_chat(body, timeout=90)
    ic = (j.get("choices") or [{}])[0].get("message", {}).get("content") or "{}"
    try:
        return json.loads(ic)
    except Exception:
        return {}


def stil_kunyesi(img_yol: str) -> dict:
    """Yuklenen stil gorselini 4 asamadan gecirir (kimlik_kunyesi ile ayni desen):
    1) piksel duzeyinde palet olcumu ($0, tahmin yok)
    2) dusuk sicaklikta bagimsiz vision okumasi
    3) yuksek sicaklikta IKINCI bagimsiz okuma
    4) kod uzlasisi — celisen alan ATILIR (uydurma alani tekrarlamak zarardir)"""
    if not (img_yol and os.path.exists(img_yol)):
        return {}
    try:
        paletler = palet_olc(img_yol, adet=6)
        a = _stil_tek_okuma(img_yol, 0.15, paletler)
        b = _stil_tek_okuma(img_yol, 0.85, paletler)
    except BakiyeHatasi:
        raise
    except Exception as e:
        print(f"  stil_kunyesi hata: {str(e)[:160]}", file=sys.stderr)
        return {}
    if not a and not b:
        return {}
    kunye, onayli, dolu = {}, 0, 0
    for alan in STIL_ALANLARI:
        va = str(a.get(alan, "") or "").strip()
        vb = str(b.get(alan, "") or "").strip()
        if not va and not vb:
            continue
        dolu += 1
        if alan in ("detay", "arka_plan"):
            uyum = va.lower() == vb.lower()
        else:
            ka, kb = set(va.lower().split()), set(vb.lower().split())
            uyum = bool(ka & kb) and len(ka & kb) >= max(1, min(len(ka), len(kb)) // 3)
        if uyum:
            kunye[alan] = va or vb
            onayli += 1
    kunye["_palet"] = paletler
    kunye["_guven"] = round(onayli / dolu, 2) if dolu else 0.0
    return kunye


def stil_kunye_metni(k: dict) -> str:
    """16 alanli stil kunyesini, HER sahne promptunda birebir tekrarlanan bir STIL
    PARMAK IZI'ne cevirir.

    Tasarim ilkesi (Polat, 3 Agu 2026): "YouTube'da yuze yakin animasyon stili var,
    tek tek ogretmek bitmez — sistem referansi o kadar iyi analiz etsin ki stili
    kilitlesin." Bu yuzden burada TARIF degil SOZLESME uretilir: numaralandirilmis,
    kisa, atlanmasi zor maddeler + acik bir YASAK listesi. Yasak listesi kritik —
    model bosluk buldugu her yerde kendi genel AI estetigine kayiyor.
    """
    if not k:
        return ""
    ETIKET = [
        ("medyum",         "MEDIUM"),
        ("cizgi",          "LINE"),
        ("dolgu",          "FILL"),
        ("golgeleme",      "SHADING"),
        ("kenar",          "EDGES"),
        ("doku",           "TEXTURE"),
        ("isik",           "LIGHT"),
        ("kontrast",       "CONTRAST"),
        ("detay",          "DETAIL LEVEL"),
        ("arka_plan",      "BACKGROUNDS"),
        ("karakter_cizim", "HOW PEOPLE ARE DRAWN"),
        ("oranlar",        "PROPORTIONS"),
        ("renk_uyumu",     "COLOUR"),
        ("yazi",           "LETTERING"),
        ("ruh",            "MOOD"),
    ]
    maddeler = []
    for alan, et in ETIKET:
        v = str(k.get(alan, "") or "").strip()
        if v and v.lower() not in ("none", "yok", "-"):
            maddeler.append(f"{et}: {v}")
    # GUVENLIK: renk ya da tek kelimelik olcek alani TEK BASINA stil degildir.
    # Gercek bir sanat alani cikmadiysa bos don -> dahili yonerge yerinde kalir.
    # "kontrast: high" ya da "detay: moderate" TEK BASINA stil degildir — bunlar olcek,
    # icerik degil. Gercek sanat alani sayilanlar sadece sunlar:
    ICERIK = ("medyum", "cizgi", "dolgu", "golgeleme", "kenar", "doku",
              "isik", "arka_plan", "karakter_cizim", "oranlar", "renk_uyumu")
    gercek = [a for a in ICERIK if str(k.get(a, "") or "").strip()
              and str(k.get(a)).lower() not in ("none", "yok", "-")]
    if not gercek:
        return ""

    hexler = [c["hex"] for c in (k.get("_palet") or [])][:6]
    if hexler:
        maddeler.append("EXACT COLOURS: build everything from " + ", ".join(hexler) +
                        " (tints, shades and mixes of these only)")

    yasak = str(k.get("kacinilacak", "") or "").strip()
    if not yasak or yasak.lower() in ("none", "yok"):
        yasak = "photorealism, 3D render, generic AI illustration look, unrequested texture or grain"

    return (
        " ══ STYLE CONTRACT (derived from the reference frames the user supplied — this is the "
        "definitive look and it OVERRIDES any other art direction) ══ "
        + " | ".join(f"{i+1}) {m}" for i, m in enumerate(maddeler)) +
        f" || FORBIDDEN — this style is NOT: {yasak}. "
        "Every single frame of this video must obey all of the above exactly, as if drawn by the "
        "same artist in the same session. Do not modernise it, do not add detail it does not have, "
        "do not simplify detail it does have, and never substitute a different illustration style."
    )

def gorsel_olcum(yol: str) -> dict:
    """Referans karenin parlaklik / doygunluk / kontrastini PIKSELDEN olcer ($0, tahmin yok)."""
    try:
        from PIL import Image
        import statistics as _st
        im = Image.open(yol).convert("RGB")
        im.thumbnail((180, 180))
        px = list(im.getdata())
        lum = [0.2126 * r + 0.7152 * g + 0.0722 * b for r, g, b in px]
        return {"parlaklik": round(sum(lum) / len(lum), 1),
                "doygunluk": round(sum(max(q) - min(q) for q in px) / len(px), 1),
                "kontrast": round(_st.pstdev(lum), 1)}
    except Exception as e:
        print(f"  gorsel_olcum hata: {str(e)[:120]}", file=sys.stderr)
        return {}


def renk_uydur(yol: str, hedef: dict, ad: str = "") -> bool:
    """Uretilen kareyi referansin OLCULEN parlaklik/doygunlugua dogru cekiverir.

    Neden gerekli: prompta "ortalama parlaklik 172 olsun" yazmak ISE YARAMIYOR — gorsel
    modeli sayisal bir hedefi tutturamaz. 5 Agu 2026 olcumu: hedef 172 iken uretim
    141-168 arasi geldi ve doygunluk hedefin (71) neredeyse iki kati (112-134) cikti;
    sonuc, referansta olmayan sepya/amber bir yikama.

    Cozum tahmin degil OLCUM: kareyi olc, hedefe oranla, PIL ile duzelt. Bedava, her
    animasyon stilinde ayni sekilde calisir (kullanicinin "tek tek stil ogretmeyelim"
    ilkesi). Carpanlar SINIRLI — duzeltme goruntuyu asla bozamaz, sadece yaklastirir.
    Iki gecis: parlaklik/doygunluk artisi dogrusal degil, ikinci gecis kalani kapatir.
    """
    if not hedef or not hedef.get("parlaklik"):
        return False
    try:
        from PIL import Image, ImageEnhance
    except Exception:
        return False
    P_ESIK, D_ESIK, K_ESIK = 8.0, 15.0, 6.0   # bu altindaki fark gozle gorunmez -> dokunma
    uygulandi = False
    try:
        for _ in range(2):
            o = gorsel_olcum(yol)
            if not o or not o.get("parlaklik"):
                break
            dp = hedef["parlaklik"] - o["parlaklik"]
            dd = hedef.get("doygunluk", 0) - o.get("doygunluk", 0)
            dk = hedef.get("kontrast", 0) - o.get("kontrast", 0)
            if abs(dp) < P_ESIK and abs(dd) < D_ESIK and abs(dk) < K_ESIK:
                break
            b = min(1.25, max(0.85, hedef["parlaklik"] / max(1.0, o["parlaklik"])))
            # DOYGUNLUK NEDEN TAM ESITLENMEZ: ortalama doygunluk kompozisyona bagli.
            # Genis planli bir referansta cerceveyi krem duvar doldurur, doygunluk dusuk
            # olcurur; ayni stildeki YAKIN PLAN portrede yuksek olcurur. 5 Agu 2026'da tam
            # esitleme denendi -> turuncu kazak grilesti, kare sepyalasti. Bu yuzden
            # doygunluk sadece YARI YOLA ve en fazla %18 tasinir: asirilik kirpilir,
            # mesru renk korunur. Parlaklik ise global bir isik ozelligi -> tam duzeltilir.
            c = 1.0
            if hedef.get("doygunluk") and o.get("doygunluk"):
                oran = hedef["doygunluk"] / max(1.0, o["doygunluk"])
                c = min(1.18, max(0.82, 1 + 0.5 * (oran - 1)))
            # KONTRAST da yari yolda: 5 Agu 2026 olcumu bizim video 42, Hazel 51 —
            # bizimki daha yumusak/pusluydu. Doygunluk gibi kompozisyona bagli oldugu
            # icin tam esitlenmez.
            kn = 1.0
            if hedef.get("kontrast") and o.get("kontrast"):
                oran_k = hedef["kontrast"] / max(1.0, o["kontrast"])
                kn = min(1.15, max(0.87, 1 + 0.5 * (oran_k - 1)))
            if abs(1 - b) < 0.02 and abs(1 - c) < 0.03 and abs(1 - kn) < 0.03:
                break
            im = Image.open(yol).convert("RGB")
            if abs(1 - b) >= 0.02:
                im = ImageEnhance.Brightness(im).enhance(b)
            if abs(1 - c) >= 0.03:
                im = ImageEnhance.Color(im).enhance(c)
            if abs(1 - kn) >= 0.03:
                im = ImageEnhance.Contrast(im).enhance(kn)
            im.save(yol)
            uygulandi = True
        if uygulandi:
            son = gorsel_olcum(yol)
            print(f"  renk uydurma{(' ' + ad) if ad else ''}: parlaklik "
                  f"{son.get('parlaklik')} / hedef {hedef['parlaklik']}, doygunluk "
                  f"{son.get('doygunluk')} / hedef {hedef.get('doygunluk')}, kontrast "
                  f"{son.get('kontrast')} / hedef {hedef.get('kontrast')}", file=sys.stderr)
    except Exception as e:
        print(f"  renk_uydur hata: {str(e)[:120]}", file=sys.stderr)
    return uygulandi


def olcum_isik_prompt(o: dict) -> str:
    """Olculen degerleri HEDEF olarak prompta yaz. Kelimeyle 'aydinlik olsun' demek yerine
    sayi vermek, palet dersinin isiga uygulanmis hali."""
    if not o or not o.get("parlaklik"):
        return ""
    p, d, k = o["parlaklik"], o.get("doygunluk", 0), o.get("kontrast", 0)
    if p >= 175:   ton = "very light and airy"
    elif p >= 150: ton = "light and bright"
    elif p >= 120: ton = "medium-toned"
    else:          ton = "deliberately dark and moody"
    dg = ("muted and gently desaturated" if d < 65 else
          "moderately saturated" if d < 100 else "richly saturated")
    kn = ("soft and low-contrast" if k < 35 else
          "clearly contrasted" if k < 55 else "high-contrast and punchy")
    return (f" LIGHT AND COLOUR MATCH — THIS OVERRIDES EVERY EARLIER LIGHTING INSTRUCTION, "
            f"including any 'one dominant light source', 'directional shadows' or 'lamplit' wording "
            f"above. Measured from the reference frames the user supplied — hit "
            f"these targets): the overall image should be {ton} (mean brightness about "
            f"{int(p)} out of 255), {dg} (mean saturation about {int(d)}), and {kn} "
            f"(tonal spread about {int(k)}). BRIGHT MUST NOT MEAN WASHED OUT: main objects keep "
            f"their own definite hues so they separate from the wall behind them, and linework "
            f"stays crisp. Match this light and colour feel in EVERY frame.")


def sahne_referansi(yollar: list, bildir=None) -> dict:
    """1-4 referans karesinden TEK SEFERDE: karakter kimligi + cizim stili + palet + isik.
    Birden fazla kare verilirse alanlar UZLASIYLA secilir (celisen alan atilir) — tek karede
    tesadufi olan sey, iki karede tekrar ediyorsa gercektir."""
    yollar = [y for y in (yollar or []) if y and os.path.exists(y)][:4]
    if not yollar:
        return {}
    kimlikler, stiller, olcumler, paletler = [], [], [], []
    for i, y in enumerate(yollar):
        if bildir:
            bildir(f"Referans {i+1}/{len(yollar)} analiz ediliyor...", 3)
        olcumler.append(gorsel_olcum(y))
        paletler += palet_olc(y, adet=6)
        try:
            kimlikler.append(kimlik_kunyesi(y))
        except BakiyeHatasi:
            raise
        except Exception as e:
            print(f"  ref{i+1} kimlik hata: {str(e)[:120]}", file=sys.stderr)
        try:
            stiller.append(stil_kunyesi(y))
        except BakiyeHatasi:
            raise
        except Exception as e:
            print(f"  ref{i+1} stil hata: {str(e)[:120]}", file=sys.stderr)

    def uzlas(sozlukler, alanlar):
        """Tek gorsel: oldugu gibi (guven okumanin kendi guveni).
        Coklu: en az iki gorselde AYNI cikan alan gecerli; guven = uzlasan/dolu."""
        sozlukler = [d for d in sozlukler if d]
        if not sozlukler:
            return {}
        if len(sozlukler) == 1:
            tek = dict(sozlukler[0])
            if "_guven" not in tek:      # ⚠ eksikti -> arayuzde 'guven=None' gorunuyordu
                dolu = sum(1 for a2 in alanlar if str(tek.get(a2, "") or "").strip())
                tek["_guven"] = round(dolu / max(1, len(alanlar)), 2)
            return tek
        out = {}
        _dolu = _uz = 0
        for alan in alanlar:
            degerler = [str(d.get(alan, "") or "").strip() for d in sozlukler]
            degerler = [v for v in degerler if v and v.lower() not in ("none", "yok")]
            if not degerler:
                continue
            _dolu += 1
            for i, a in enumerate(degerler):
                esles = False
                for b2 in degerler[i + 1:]:
                    ka, kb = set(a.lower().split()), set(b2.lower().split())
                    if ka & kb and len(ka & kb) >= max(1, min(len(ka), len(kb)) // 3):
                        esles = True
                        break
                if esles:
                    out[alan] = a
                    _uz += 1
                    break
        out["_guven"] = round(_uz / _dolu, 2) if _dolu else 0.0
        return out

    kimlik = uzlas(kimlikler, KUNYE_ALANLARI)
    stil = uzlas(stiller, STIL_ALANLARI)
    # Palet: TUM karelerin olculen renkleri, en baskin 6'si
    paletler.sort(key=lambda c: -c.get("oran", 0))
    gorulen, birlesik = set(), []
    for c in paletler:
        h = c["hex"].upper()
        if h not in gorulen:
            gorulen.add(h)
            birlesik.append(c)
        if len(birlesik) >= 6:
            break
    stil["_palet"] = birlesik
    olc = {}
    gecerli = [o for o in olcumler if o.get("parlaklik")]
    if gecerli:
        for k in ("parlaklik", "doygunluk", "kontrast"):
            olc[k] = round(sum(o.get(k, 0) for o in gecerli) / len(gecerli), 1)
    return {"kimlik": kimlik, "stil": stil, "olcum": olc,
            "palet_hex": [c["hex"] for c in birlesik],
            "kare_sayisi": len(yollar)}


def stil_analiz(stil_yol: str) -> str:
    """Referans stil gorselinden TEK cumlelik kanonik STIL kilidi (gpt-4.1-mini vision).
    Her AI sahne promptuna eklenir -> stil de birebir sabitlenir (karakter kilidinin stil ikizi)."""
    if not stil_yol or not os.path.exists(stil_yol):
        return ""
    try:
        import base64
        with open(stil_yol, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        body = {
            "model": "gpt-4.1-mini",
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": (
                    "Describe ONLY the ART STYLE of this image as a reusable style lock in ONE compact "
                    "English sentence (20-40 words): rendering technique, line/brush quality, color "
                    "palette, shading, texture, level of detail and overall aesthetic. Do NOT describe "
                    "any subject/character/scene content. Start with 'Art style:'.")},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
            ]}],
            "max_tokens": 120, "temperature": 0.2,
        }
        j = oai_chat(body, timeout=90)
        return j["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"  stil_analiz hata: {str(e)[:160]}", file=sys.stderr)
        return ""


# Dil -> dogrulanmis Azure neural ses (model bos/bozuk/halusinasyon voice verirse dile gore dus)
DIL_SES = {
    "tr": "tr-TR-EmelNeural",    "en": "en-US-AndrewMultilingualNeural",
    "es": "es-ES-AlvaroNeural",  "de": "de-DE-ConradNeural",
    "fr": "fr-FR-HenriNeural",   "it": "it-IT-DiegoNeural",
    "pt": "pt-BR-AntonioNeural", "ru": "ru-RU-DmitryNeural",
    "ar": "ar-EG-ShakirNeural",
}
import re as _re
_SES_KALIP = _re.compile(r"^[a-z]{2,3}-[A-Z]{2}-\w+Neural$")


# ═══════════════ SES SECENEKLERI ═══════════════
# edge-tts (bedava) + OpenAI gpt-4o-mini-tts (talimatli — GERCEK yasli ses).
# Neden OpenAI: edge-tts'in 322 sesinin hicbiri yasli degil; perde dusurmek genc sesi
# kalinlastirir, yaslandirmaz. gpt-4o-mini-tts sesin YASINI tarif etmeye izin veriyor.
# Maliyet: ~$0.02-0.03 / 11 dk video (+ whisper hizalama ~$0.07). edge-tts $0.
YASLI_KADIN_TALIMAT = (
    "An elderly woman, roughly seventy five. Frail, papery timbre with a gentle tremor, quiet "
    "and slow, full of lived experience. Speak softly, as if sitting in a kitchen chair.")

SESLER = {
    "otomatik": {"ad": "Otomatik (dile göre)", "motor": "edge", "grup": "ucretsiz", "ses": "",
                 "ozet": "Metnin diline uygun ücretsiz ses", "ucret": "ücretsiz", "dil": ""},
    # ── Kullanicinin 1 Agu 2026'da ORNEK DINLEYIP ONAYLADIGI ses ──
    "yasli-kadin": {"ad": "Yaşlı Kadın — 75 yaş", "motor": "openai", "grup": "karakterli", "ses": "shimmer",
                    "talimat": YASLI_KADIN_TALIMAT, "hiz": 0.92, "dil": "en",
                    "ozet": "Kırılgan, hafif titrek, sakin — tasarruf/anı kanalları için",
                    "ucret": "~$0.03/video"},
    # ── Yasli Amerikali kadin sesleri (Polat istegi, 4 Agu 2026) ──
    # Hepsi gpt-4o-mini-tts + talimat: model sesin YASINI ve aksanini tarif etmeye izin
    # veriyor. edge-tts'te bu imkansiz (322 sesin hicbiri yasli degil).
    "yasli-guneyli": {"ad": "Yaşlı Kadın · Güneyli — 72 yaş", "motor": "openai", "grup": "karakterli",
                      "ses": "sage", "hiz": 0.90, "dil": "en",
                      "talimat": ("An American woman of about seventy two from the deep South. Warm "
                                  "unhurried drawl, softened vowels, a little husky with age. She "
                                  "tells things like she is sitting on a porch with sweet tea. Kind, "
                                  "patient, faintly amused."),
                      "ozet": "Güney aksanı, ağır ağır, sıcak — veranda sohbeti tonu",
                      "ucret": "~$0.03/video"},
    "yasli-newyork": {"ad": "Yaşlı Kadın · New York — 70 yaş", "motor": "openai", "grup": "karakterli",
                      "ses": "nova", "hiz": 0.96, "dil": "en",
                      "talimat": ("A seventy year old woman from New York. Direct, quick, a little "
                                  "clipped, with the dryness of someone who has heard every excuse. "
                                  "Age shows in a slight rasp, not in slowness. No sweetness, just "
                                  "plain truth delivered fast."),
                      "ozet": "Keskin, hızlı, lafı dolandırmayan — kuru mizah",
                      "ucret": "~$0.03/video"},
    "yasli-cok-yasli": {"ad": "Çok Yaşlı Kadın — 85 yaş", "motor": "openai", "grup": "karakterli",
                        "ses": "alloy", "hiz": 0.86, "dil": "en",
                        "talimat": ("A woman of about eighty five. Thin, papery voice with a real "
                                    "tremor, short breaths, long pauses between thoughts. Very quiet "
                                    "and very slow, as if each memory takes a moment to find. Frail "
                                    "but completely lucid."),
                        "ozet": "Çok yavaş, titrek, nefes araları — en yaşlı ton",
                        "ucret": "~$0.03/video"},
    "yasli-neseli": {"ad": "Yaşlı Kadın · Neşeli — 70 yaş", "motor": "openai", "grup": "karakterli",
                     "ses": "verse", "hiz": 0.98, "dil": "en",
                     "talimat": ("A lively American woman of seventy who has not slowed down. Bright, "
                                 "playful, quick to laugh at herself. The voice has age in its texture "
                                 "but energy in its delivery. Think of a grandmother who still drives "
                                 "and still argues about politics."),
                     "ozet": "Enerjik, esprili, kendine gülen — yaşlı ama canlı",
                     "ucret": "~$0.03/video"},
    "yasli-ogretmen": {"ad": "Yaşlı Kadın · Öğretmen — 74 yaş", "motor": "openai", "grup": "karakterli",
                       "ses": "fable", "hiz": 0.92, "dil": "en",
                       "talimat": ("A retired American schoolteacher, about seventy four. Clear, "
                                   "measured, carefully articulated — every word lands. Patient and "
                                   "authoritative without being cold. She explains rather than tells, "
                                   "and pauses to let a point sink in."),
                       "ozet": "Net, ölçülü, açıklayıcı — emekli öğretmen",
                       "ucret": "~$0.03/video"},
    "yasli-kirsal": {"ad": "Yaşlı Kadın · Çiftlik — 78 yaş", "motor": "openai", "grup": "karakterli",
                     "ses": "shimmer", "hiz": 0.88, "dil": "en",
                     "talimat": ("A seventy eight year old woman from rural America who worked hard "
                                 "her whole life. Low, weathered, plain-spoken. No decoration, no "
                                 "performance — she says what happened and lets it stand. A quiet "
                                 "toughness under the warmth."),
                     "ozet": "Alçak, yıpranmış, süssüz — çalışmış kadın tonu",
                     "ucret": "~$0.03/video"},
    "olgun-kadin": {"ad": "Olgun Kadın — 68 yaş", "motor": "openai", "grup": "karakterli", "ses": "coral",
                    "talimat": ("Speak as a warm woman in her late sixties. Unhurried and gentle, "
                                "with the soft dryness and slight breathiness of an older voice. "
                                "Lower and thinner than a young voice, with small natural pauses, "
                                "as if remembering while she speaks. Kind, grandmotherly, never perky."),
                    "hiz": 0.94, "dil": "en", "ozet": "Anneanne tonu, hatırlarken duraklayan",
                    "ucret": "~$0.03/video"},
    "buyukanne-abd": {"ad": "Büyükanne (Orta Batı)", "motor": "openai", "grup": "karakterli", "ses": "ballad",
                      "talimat": ("A grandmother in her late sixties from the American midwest. "
                                  "Low, calm, plain-spoken, a touch of gravel. No enthusiasm, just "
                                  "quiet certainty from years of doing it herself."),
                      "hiz": 0.93, "dil": "en", "ozet": "Alçak, düz konuşan, çakıllı",
                      "ucret": "~$0.03/video"},
    "yasli-erkek": {"ad": "Yaşlı Erkek — 70 yaş", "motor": "openai", "grup": "karakterli", "ses": "onyx",
                    "talimat": ("A man of about seventy telling a story he has told before. Deep, "
                                "slow and weathered, with a dry rasp. Calm authority, no drama."),
                    "hiz": 0.92, "dil": "en", "ozet": "Derin, yavaş, yıpranmış",
                    "ucret": "~$0.03/video"},
    # ── Ucretsiz edge-tts secenekleri (yas TARIF EDILEMEZ, sadece ton farki) ──
    "en-kadin-sicak": {"ad": "Kadın · Sıcak (İng)", "motor": "edge", "grup": "ucretsiz", "ses": "en-US-JennyNeural",
                       "ozet": "Şefkatli, sakin anlatıcı", "ucret": "ücretsiz", "dil": "en"},
    "en-kadin-ingiliz": {"ad": "Kadın · İngiliz", "motor": "edge", "grup": "ucretsiz", "ses": "en-GB-SoniaNeural",
                         "ozet": "Ölçülü İngiliz aksanı", "ucret": "ücretsiz", "dil": "en"},
    "en-kadin-avustralya": {"ad": "Kadın · Avustralya", "motor": "edge", "grup": "ucretsiz", "ses": "en-AU-NatashaNeural",
                            "ozet": "Aussie kanalları için", "ucret": "ücretsiz", "dil": "en"},
    "en-erkek": {"ad": "Erkek · Anlatıcı (İng)", "motor": "edge", "grup": "ucretsiz",
                 "ses": "en-US-AndrewMultilingualNeural",
                 "ozet": "Belgesel tonu", "ucret": "ücretsiz", "dil": "en"},
    "tr-kadin": {"ad": "Kadın · Türkçe", "motor": "edge", "grup": "ucretsiz", "ses": "tr-TR-EmelNeural",
                 "ozet": "Türkçe anlatıcı", "ucret": "ücretsiz", "dil": "tr"},
    "tr-erkek": {"ad": "Erkek · Türkçe", "motor": "edge", "grup": "ucretsiz", "ses": "tr-TR-AhmetNeural",
                 "ozet": "Türkçe anlatıcı", "ucret": "ücretsiz", "dil": "tr"},
    # ── PREMIUM (Ai33.Pro — ElevenLabs kalitesi, her dilde; anahtar sunucuda AI33_KEY) ──
    # eleven_multilingual_v2 otomatik: ayni ses Turkce dahil her dili dogal okur.
    "premium-kadin": {"ad": "⭐ Premium Kadın", "motor": "ai33", "grup": "elevenlabs",
                      "ses": "elevenlabs_21m00Tcm4TlvDq8ikWAM", "hiz": 1.0, "dil": "",
                      "ozet": "ElevenLabs (Rachel) — en doğal kadın anlatıcı, her dil",
                      "ucret": "kredi"},
    "premium-erkek": {"ad": "⭐ Premium Erkek", "motor": "ai33", "grup": "elevenlabs",
                      "ses": "elevenlabs_pNInz6obpgDQGcFmaJgB", "hiz": 1.0, "dil": "",
                      "ozet": "ElevenLabs (Adam) — derin, doğal erkek anlatıcı, her dil",
                      "ucret": "kredi"},
    "eleven-bella": {"ad": "Bella · Yumuşak Kadın", "motor": "ai33", "grup": "elevenlabs",
                     "ses": "elevenlabs_EXAVITQu4vr4xnSDxMaL", "hiz": 1.0, "dil": "",
                     "ozet": "Yumuşak, genç, samimi kadın ses — duygusal hikayeler",
                     "ucret": "kredi"},
    "eleven-domi": {"ad": "Domi · Enerjik Kadın", "motor": "ai33", "grup": "elevenlabs",
                    "ses": "elevenlabs_AZnzlk1XvdvUeBnXmlld", "hiz": 1.0, "dil": "",
                    "ozet": "Canlı, kendinden emin kadın ses — tempolu anlatım",
                    "ucret": "kredi"},
    "eleven-antoni": {"ad": "Antoni · Sıcak Erkek", "motor": "ai33", "grup": "elevenlabs",
                      "ses": "elevenlabs_ErXwobaYiN019PkySvjV", "hiz": 1.0, "dil": "",
                      "ozet": "Sıcak, dengeli erkek ses — genel anlatıcı",
                      "ucret": "kredi"},
    "eleven-josh": {"ad": "Josh · Derin Genç Erkek", "motor": "ai33", "grup": "elevenlabs",
                    "ses": "elevenlabs_TxGEqnHWrfWFTfGW9XjX", "hiz": 1.0, "dil": "",
                    "ozet": "Derin, genç erkek ses — gerilim/karanlık hikayeler",
                    "ucret": "kredi"},
}
VARSAYILAN_SES = "otomatik"


def ses_ayari(secim: str, plan_sesi: str = "") -> dict:
    """Ses secimini motor+parametre sozlugune cevir. Bilinmeyen/otomatik -> edge, dile gore.
    'ozel:<voice_id>' = kullanicinin Ai33 KUTUPHANESINDEN sectigi herhangi bir ses."""
    secim = (secim or "").strip()
    if secim.startswith("ozel:"):
        return {"motor": "ai33", "ses": secim[5:], "hiz": 1.0}
    s = SESLER.get(secim)
    if s and s.get("motor") == "openai":
        return {"motor": "openai", "ses": s["ses"], "talimat": s.get("talimat", ""),
                "hiz": s.get("hiz", 0.92)}
    if s and s.get("motor") == "ai33":
        return {"motor": "ai33", "ses": s["ses"], "hiz": s.get("hiz", 1.0)}
    return {"motor": "edge", "ses": (s or {}).get("ses") or plan_sesi}


def ses_coz(plan: dict) -> str:
    """plan['voice']'i dogrula; bos/bozuk/dil-uyumsuzsa plan['language']'a gore yerel sesi sec.
    Boylece Turkce metin en-US sesle okunmaz ve halusinasyon voice tum isi oldurmez."""
    dil = str(plan.get("language", "")).strip().lower()[:2]
    ses = str(plan.get("voice", "")).strip()
    if not _SES_KALIP.match(ses):
        return DIL_SES.get(dil, DIL_SES["en"])
    if dil in DIL_SES and not ses.lower().startswith(dil + "-"):
        return DIL_SES[dil]
    return ses



# ── SAHNE TIPI ATAMASI (KODLA ZORLANIR) ──
# Prompt ile "%40 karaktersiz olsun" demek ISE YARAMADI (LLM 1/7 uretti). Cozum: tipi
# planlayiciya BIZ soyluyoruz. Tek sahne atlanamaz, oran garanti, ard arda karaktersiz olmaz.
TIP_KARAKTERLI = ["A WIDE ESTABLISHING", "B MEDIUM ACTION", "C CLOSE-UP",
                  "D DRAMATIC LIGHT", "E CROWD", "H SFX BEAT"]
# N/O: Simple Explainer + Bruce karelerinde dogrulandi (ekran arayuzu, tepeden cekim).
TIP_KARAKTERSIZ = ["I OBJECT MACRO", "J HANDS ONLY", "K MAP ROUTE", "G INFOGRAPHIC",
                   "N SCREEN READOUT", "O OVERHEAD FLATLAY"]


# ═══════════════ METIN DERIN ANALIZI → SAHNE BAZINDA EDIT ═══════════════
# Sorun (Polat, 4 Agu 2026): zoom tek-cift donuyordu, pan sirayla (sag/sol/ust/alt),
# vurgu sadece hikaye acilisinda. Yani KURGU metnin ne dedigini hic bilmiyordu.
# Cozum: her satirin ISLEVINI cikar (acilis / liste maddesi / vurgu / donus / sonuc...)
# ve editorun GERCEKTEN yapabildigi seylere cevir: zoom yonu, pan yonu, vurgu, overlay.
# Editorun kapasitesi olculdu: zoom(in/out), pan(4 yon), vurgu(derin zoom+push-in),
# overlay(kinetik yazi), sure. Sahne basina FARKLI GECIS TIPI yok — hepsi crossfade.
ISLEV_TIPLERI = {
    "acilis":      "opening hook — the first promise or question",
    "liste":       "the start of a numbered list item",
    "vurgu":       "the punch: a shocking number, a reveal, a turn",
    "aciklama":    "calm explanation or context",
    "ornek":       "a concrete example or small story",
    "gecmis":      "a memory or flashback to the past",
    "karsilastir": "comparing two things",
    "soru":        "a direct question to the viewer",
    "sonuc":       "the takeaway or closing line",
}


def metin_islev_analizi(scenes: list) -> list:
    """Her sahnenin ANLATIM ISLEVINI cikarir. LLM sadece kilitli listeden secebilir;
    uyduramaz. Basarisiz olursa [] doner ve cagiran eski mekanik atamaya duser —
    kurgu analizi yuzunden video OLMEZ."""
    if not scenes:
        return []
    satirlar = []
    for i, sc in enumerate(scenes):
        vo = (sc.get("voiceover") or "").strip().replace("\n", " ")
        satirlar.append(f"{i+1}. {vo[:220]}")
    istek = (
        "You are a video editor reading a narration script. For EACH numbered line, decide its "
        "narrative FUNCTION and how the camera should behave. Return STRICT JSON:\n"
        '{"sahneler": [{"n": <line number>, "islev": <one key below>, '
        '"yogunluk": <1-5>, "baslik": <short ALL-CAPS title or "">}]}\n'
        "ALLOWED islev KEYS (use these exact strings, nothing else):\n"
        + "\n".join(f'  "{k}" = {v}' for k, v in ISLEV_TIPLERI.items()) + "\n"
        "yogunluk = how much visual energy this moment deserves, 1 (calm) to 5 (peak).\n"
        "baslik = ONLY when islev is \"liste\" and the line clearly opens a numbered item "
        "(\"number nine\", \"rule three\", \"the fourth thing\"). Then give the item number and "
        "its subject as a very short ALL-CAPS title, max 3 words, e.g. \"9 GROCERY BILLS\". "
        "For every other line baslik MUST be an empty string.\n"
        "Return one entry for EVERY line, in order. No commentary.\n\n"
        + "\n".join(satirlar)[:14000]
    )
    try:
        j = oai_chat({"model": "gpt-4.1-mini",
                      "messages": [{"role": "user", "content": istek}],
                      "response_format": {"type": "json_object"},
                      "max_tokens": min(6000, 60 * len(scenes) + 400),
                      "temperature": 0.2}, timeout=180)
        ic = json.loads(j["choices"][0]["message"]["content"])
        ham = {int(x.get("n", 0)): x for x in (ic.get("sahneler") or []) if x.get("n")}
    except BakiyeHatasi:
        raise
    except Exception as e:
        print(f"  metin_islev_analizi hata (mekanik atamaya dusuluyor): {str(e)[:140]}",
              file=sys.stderr)
        return []
    out = []
    for i in range(len(scenes)):
        x = ham.get(i + 1) or {}
        islev = x.get("islev") if x.get("islev") in ISLEV_TIPLERI else "aciklama"
        try:
            yog = max(1, min(5, int(x.get("yogunluk") or 3)))
        except Exception:
            yog = 3
        baslik = str(x.get("baslik") or "").strip().upper()[:24] if islev == "liste" else ""
        out.append({"islev": islev, "yogunluk": yog, "baslik": baslik})
    dagilim = {}
    for o in out:
        dagilim[o["islev"]] = dagilim.get(o["islev"], 0) + 1
    print(f"  metin analizi: {dagilim} | vurgu(4-5)={sum(1 for o in out if o['yogunluk']>=4)}"
          f" | liste basligi={sum(1 for o in out if o['baslik'])}", file=sys.stderr)
    return out


def islev_kurgu(islev: str, yogunluk: int, i: int, onceki: dict = None) -> dict:
    """Anlatim islevini editorun YAPABILDIGI seylere cevirir.
    (Olculen kapasite: zoom in/out, pan 4 yon, vurgu bayragi, overlay yazi.)

    ⚠ 4 Agu 2026 DUZELTMESI — ilk surumde 9 islev 2 zoom yonune sikistirilmisti ve
    en sik cikan iki islev (aciklama %61 + ornek %19) AYNI yone bakiyordu.
    Sonuc: 132 sahnenin 120'si zoom=out, ard arda ayni zoom orani %84.
    Gorseller farkli olmasina ragmen kamera hep ayni seyi yapinca video
    TEKRAR EDIYORMUS gibi hissettiriyordu (Polat bildirdi).
    Cozum: (1) en sik islevler kendi ICINDE donusumlu, (2) onceki sahneyle
    ayni kombinasyon cikarsa ZORLA degistirilir.
    """
    # ── 7 Agu 2026 OLCUMU ILE IKINCI DUZELTME ──
    # 246 referans cekimi olculdu (piksel eslestirme): zoom'lu cekimlerin
    #   %78'i ZOOM-IN, %22'si zoom-out. Gorsel agirlikli kanallarda daha da uc:
    #   ZeroReports %93 in, Auralis %85, Atrium %77.
    # 4 Agu'daki duzeltmem sik islevleri "i % 2" ile 50/50 alternatiflemisti —
    # tekrar hissini cozdu ama orani BOZDU: referans 78/22, bizde 50/50 oldu.
    # Ayrica referansta cekimlerin %18-20'sinde kamera DURGUN. Bizde her sahnede
    # zoom vardi. Ama onlarin durgun cekimi CANLI footage; bizde durgun = donmus kare
    # (referansta o sadece %2). Bu yuzden %20 degil %12 hedeflenir.
    # karsilastir "out"tan "in"e cevrildi: 3 islevi zorla out yapmak toplam orani
    # %69/31'e cekiyordu, hedef %78/22. Karsilastirmada ice dogru yaklasmak da dogru
    # (izleyici ayrintiya bakar), disari acilmak degil.
    SABIT_ZOOM = {"vurgu": "in", "soru": "in", "acilis": "in", "karsilastir": "in",
                  "gecmis": "out", "sonuc": "out"}
    if islev in SABIT_ZOOM:
        zoom = SABIT_ZOOM[islev]
    else:                                   # aciklama / ornek / liste
        # 78/22 in-out: her 9 sahnede 2'si out (deterministik, indeks tabanli)
        zoom = "out" if (i * 3571 % 12) < 2 else "in"   # olculen dagilimda %78/22'a oturur
    # %12 durgun kare: uzun sahnelerde ve sadece sik islevlerde (vurgu/acilis durgun olmaz)
    if islev not in SABIT_ZOOM and (i * 6113 % 100) < 14:   # olculen dagilimda ~%12
        zoom = "yok"

    PAN = {"gecmis": "left", "sonuc": "right", "karsilastir": "right", "acilis": "top"}
    pan = PAN.get(islev) or ("right", "left", "top", "bottom")[i % 4]

    # Ard arda AYNI kombinasyon olmasin — tekrar hissinin asil kaynagi buydu
    if onceki and onceki.get("zoom") == zoom and onceki.get("pan") == pan:
        zoom = "out" if zoom == "in" else "in"
        if onceki.get("zoom") == zoom:       # yine ayniysa pan'i cevir
            zoom = onceki["zoom"]
            sira = ["right", "left", "top", "bottom"]
            pan = sira[(sira.index(pan) + 1) % 4] if pan in sira else "right"
    return {"zoom": zoom, "pan": pan, "vurgu": yogunluk >= 4}

def sahne_tipi_atamasi(adet: int) -> str:
    """Sahne basina cekim tipi atar: tek indeksler KARAKTERSIZ -> ~%50 oran, ard arda yok."""
    satir = []
    for i in range(adet):
        if i % 2 == 1:
            t = TIP_KARAKTERSIZ[(i // 2) % len(TIP_KARAKTERSIZ)]
            satir.append(f"{i+1}={t} (no character in frame)")
        else:
            t = TIP_KARAKTERLI[(i // 2) % len(TIP_KARAKTERLI)]
            satir.append(f"{i+1}={t}")
    return ("SHOT TYPE ASSIGNMENT — NON-NEGOTIABLE. The shot type of every scene is decided for you "
            "below. Write each scene using EXACTLY its assigned type and open the scene_prompt with "
            "that type's name. Scenes marked '(no character in frame)' must contain no figure at all "
            "and must literally include the words 'no character in frame'. Do not swap, skip or "
            "reorder types; fit the narration to the assigned type.\n" + "; ".join(satir) + "\n")


# ── SAHNE TEMPOSU: kelime butcesi SES HIZINA gore (4 Agu 2026) ──
# Olculen sorun: 132 sahne / 923 sn -> ortalama 7.0 sn (hedef 5), 39 sahne 8 sn'den uzun.
# Sebep: kelime bandi sabit (14-17) ama okuma hizi sese gore degisiyor.
#   edge-tts (+%15)      ~178 kelime/dk
#   OpenAI yasli sesler  speed 0.86-0.98 -> ~130-150
#   ai33/minimax         ~133 (bu videoda olculdu)
# Sabit kelime + yavas ses = uzun sahne. Artik butce sesin GERCEK hizindan turetilir.
SES_HIZI_DOSYA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "veri",
                              "ses_hizi.json")


def _ses_hizi_oku(anahtar: str):
    """Onceki islerden OLCULEN hiz. Tablodan onceliklidir."""
    try:
        with open(SES_HIZI_DOSYA) as f:
            d = json.load(f)
        v = d.get(anahtar)
        if v and 60 < float(v.get("wpm", 0)) < 400:
            return float(v["wpm"])
    except Exception:
        pass
    return None


def ses_hizi_kaydet(anahtar: str, kelime: int, saniye: float):
    """Isin GERCEK hizini kaydet — sonraki isler bunu kullanir (kendi kendini kalibre).

    NEDEN VAR (11 Agu 2026): tabloda edge-tts 178 wpm yaziyordu; 73 kelimelik metni
    seslendirip olctum, 212 wpm cikti. Sonuc: plan her videoda hedefin %19 altinda
    kelime yaziyordu ve VIDEO ISTENENDEN %33 KISA cikiyordu (olcum: durum "56.1 sn"
    diyor, dosya 39.2 sn). Ayrica sahneler 5.5 sn yerine 2.8 sn oluyordu, bu da cekim
    bolme esigini (5.0 sn) hic tetiklemiyordu — yani tempo duzeltmesi de calismiyordu.
    Sabit sayiya guvenmek yerine her isin sonunda gercek hiz yazilir; ses/model
    degisse bile sistem 1 videoda kendini toplar.
    """
    if kelime < 20 or saniye < 5:
        return                                  # olcum guvenilir degil
    wpm = kelime / saniye * 60.0
    if not (60 < wpm < 400):
        return
    try:
        os.makedirs(os.path.dirname(SES_HIZI_DOSYA), exist_ok=True)
        try:
            with open(SES_HIZI_DOSYA) as f:
                d = json.load(f)
        except Exception:
            d = {}
        eski = d.get(anahtar) or {}
        onceki = float(eski.get("wpm") or 0)
        # Yumusatma: tek is anormal cikarsa hedefi savurmasin
        yeni_wpm = wpm if onceki <= 0 else onceki * 0.6 + wpm * 0.4
        d[anahtar] = {"wpm": round(yeni_wpm, 1), "son_olcum": round(wpm, 1),
                      "kelime": kelime, "saniye": round(saniye, 1)}
        with open(SES_HIZI_DOSYA, "w") as f:
            json.dump(d, f, indent=1)
        print(f"  ses hizi kalibre: {anahtar} -> {yeni_wpm:.0f} wpm "
              f"(bu iste {wpm:.0f})", file=sys.stderr)
    except Exception as e:
        print(f"  ses hizi kaydedilemedi: {str(e)[:80]}", file=sys.stderr)


def ses_wpm(ses_secim: str) -> float:
    """Secili sesin GERCEK konusma hizi (kelime/dakika).
    Once onceki islerden OLCULEN deger, yoksa tablo."""
    anahtar = (ses_secim or "otomatik").strip() or "otomatik"
    olculen = _ses_hizi_oku(anahtar)
    if olculen:
        return olculen
    v = SESLER.get(anahtar) or {}
    motor = v.get("motor", "edge")
    if motor == "openai":
        return 165 * float(v.get("hiz", 0.95))      # 0.86-0.98 -> ~142-162
    if motor == "ai33" or anahtar.startswith("ozel:"):
        return 135                                  # olculdu (minimax, 4 Agu 2026)
    return 212                                      # OLCULDU 11 Agu 2026 (onceki: 178)


def kelime_butcesi(prof, ses_secim: str) -> int:
    """Hedef sahne suresini tutturacak kelime sayisi."""
    hedef_sn = float(prof.get("sahne_sn") or 5)
    wpm = ses_wpm(ses_secim)
    prof["_wpm"] = wpm          # plan_sistem cift-modlu bantlari bundan hesaplar
    kel = int(round(hedef_sn * wpm / 60))
    return max(6, min(24, kel))


# ⚠ `unlu` main'den geldi (unlu modu): gercek kisi ismi promptta YAZILIR.
def plan_sistem(prof, hedef_sahne=None, devam=False, onceki_ozet="", unlu=False):
    footage = prof["footage_pct"]
    mag_var = bool(prof.get("mag"))
    overlay_kural = (
        "For EACH scene also give overlay: a punchy 2-5 word ALL-CAPS on-screen title in the "
        "ORIGINAL language that reinforces the narration (kinetic caption)."
        if prof["overlay"] != "yok" else
        "Leave overlay as an empty string for every scene (this style uses no on-screen titles)."
    )
    # 3) footage karari OTOMATIK: animasyon (footage=0) hic footage kullanmaz.
    if footage <= 0:
        footage_kural = (
            "3) This style uses NO real footage: set kaynak='ai' for EVERY scene. Still give "
            "footage_sorgu as an empty string.")
    else:
        footage_kural = (
            f"3) DECIDE per scene from the content: about {footage}% of scenes that depict a real "
            "place/action better shown with real video must be REAL FOOTAGE (set kaynak='footage' "
            "and footage_sorgu = a specific ENGLISH stock-footage query, e.g. 'aerial drone "
            "rainforest canopy'); scenes centered on the character/abstract ideas set kaynak='ai'.")
    # ── EDIT PAKETI (grafik katmani) ──
    # Sadece edit_paketi=True stillerde istenir. Diger stillerde alan hic gecmez, yani
    # eski isler etkilenmez. Sayilar olculdu: referansin karelerinin %41'i beyaz tuval.
    if prof.get("edit_paketi"):
        gp = int(prof.get("grafik_pct") or 40)
        grafik_kural = (
            f"9) GRAPHIC LAYER — about {gp}% of scenes must carry a \"grafik\" object. This is "
            "the signature of the style: measured frame by frame, that share of the reference "
            "channel's frames are graphics on a white canvas, not photography. Choose the "
            "template that fits what the line is SAYING:\n"
            '   {"tur":"beyaz-tuval","etiketler":[{"metin":"458.5 M","x":0.3,"y":0.2,'
            '"buyuk":true}]} — the subject isolated on white with measured values called out. '
            "x/y are 0-1 fractions of the frame. Use when the line states dimensions, capacity "
            "or a comparison of sizes.\n"
            '   {"tur":"olcu","metin":"375 METERS","x1":0.16,"y1":0.72,"x2":0.84,"y2":0.72} — '
            "a dimension arrow across the subject. Use when the line states ONE length/distance.\n"
            '   {"tur":"alinti","baslik":"<headline>","metin":"<2-4 sentence quote>",'
            '"kaynak":"<publication or institution>"} — a source citation card. Use ONLY when the '
            "narration actually attributes a claim to a named source. NEVER invent a source or a "
            "quote: if the script does not name one, do not use this template.\n"
            '   {"tur":"metin","satirlar":["line one","line two","line three"]} — serif text on '
            "white, revealed line by line. Use for a definition or the thesis of the video.\n"
            '   {"tur":"harita","rota":true,"noktalar":[{"metin":"SUEZ","x":0.5,"y":0.35}]} — '
            "map annotation with circles and a dashed route. Use for routes and places.\n"
            "RULES: every number that appears in a grafik MUST come from the narration text you "
            "wrote for that scene — never make up a statistic to fill a label. Do not put a "
            "grafik on two consecutive scenes of the same tur. Scenes without a grafik leave the "
            "field out entirely.\n")
    else:
        grafik_kural = ""

    # ── SAHA ETIKETI + CERCEVE VURGUSU (7 Agu 2026, 20 video / 196 kare olcumu) ──
    # Olculen: en iyi kanallarin karelerinin %39-57'sinde EKRANDA YAZI var ve baskin tur
    # BUYUK BASLIK DEGIL, KUCUK ETIKET (yer/nesne/kisi/sayi adi). Bizim ciktida %0'di —
    # "edit minimum" hissinin birinci sebebi bu. Ikinci teknik: goruntunun bir bolgesini
    # kutu/daire ile isaretlemek (%7-18).
    #   NextGen %57 (etiket %50) | ZeroReports %57 (etiket %39) | MadeVision %46 (etiket %43)
    #   NavyDecoded %32 | ECHOES %29 | Auralis %25 | Atrium %11
    if prof.get("saha_etiketi"):
        oran = int(prof.get("etiket_pct") or 25)
        etiket_kural = (
            f"11) ON-SCREEN TEXT — about {oran}% of scenes carry text. MEASURED from 935 frames "
            "across 7 reference channels; the split INSIDE text-bearing frames is:\n"
            "   alt-band (lower third) 33% | big title 28% | small label 20% | data number 12%\n"
            "   Give the fields that apply; leave them out otherwise.\n"
            '   "alt_band":{"baslik":"RAS TANURA","alt":"SAUDI ARABIA"} — the MOST used type. '
            "A name/place/role in the lower left. baslik 1-4 words, alt is optional context.\n"
            '   "etiketler":[{"metin":"400,000 DWT","x":0.34,"y":0.58}] — small label pinned to '
            "a THING in frame. x/y are 0-1 fractions. Max 2 per scene (measured lifetime is only "
            "1.8 s, so they are quick call-outs, not signage).\n"
            "   Label only what the narration actually names — a place, a vessel, a role, a "
            "measured number. NEVER invent a name or a figure.\n"
            "   Avoid the bottom 12% (subtitle band) and do not put alt_band and etiketler on the "
            "same scene.\n"
            '12) HIGHLIGHT — about 15% of scenes get "vurgu_kutu": a corner-marked box (or circle) '
            "around the part of the frame the narration points at:\n"
            '     "vurgu_kutu":{"x":0.30,"y":0.28,"w":0.34,"h":0.30}   (add "daire":true for a circle)\n'
            "   MEASURED RULE: a highlight almost never appears without text (72% of graphic "
            "frames also carry text). So whenever you add vurgu_kutu, also add an alt_band or a "
            "label naming what is highlighted.\n"
            "   Do NOT produce timelines or split screens — measured 0% and 1% in the references.\n")
    else:
        etiket_kural = ""

    # 7) HD (Magnific) karari OTOMATIK: sadece close-up/kilit detay AI sahnelerinde.
    hd_kural = (
        "7) hd (HD upscale need): set hd=true ONLY for AI scenes that are close-ups or key detail "
        "hero shots that clearly benefit from extra sharpness; set hd=false for all other scenes."
        if mag_var else
        "7) Set hd=false for every scene.")
    hedef = hedef_sahne or 40

    # ── BOLUM YAPISI (5 Agu 2026, referans #12'nin bolum baslikliari) ──
    # Referans videolar duz bir sahne dizisi DEGIL: 5-8 bolume ayrilmis ve her bolumun
    # kendi basligi + kendi anlatim yayi var. Bizim plan tek duz liste uretiyordu, o yuzden
    # 40 dakika boyunca ayni tonda akip gidiyordu.
    # Bolum sayisi: ~5 dakikada bir bolum (kullanicinin gosterdigi referansta bu orandaydi).
    # Bolum sayisi: ~5 dakikada bir bolum. TABAN 3 DEGIL 1 (7 Agu 2026 duzeltmesi):
    # eski taban 3'tu ve 1 dakikalik bir testte 4 sahneye 3 bolum dusuyordu — neredeyse
    # her sahnede bir bolum basligi, yani sacma. 2 dakikanin altinda bolum yapisi zaten
    # anlamsiz: tek bolum basligi (acilis) kalir.
    if prof.get("bolumler"):
        toplam_dk = hedef * float(prof["sahne_sn"]) / 60.0
        bolum_adet = max(1, min(10, int(round(toplam_dk / 5.0))))
        bolum_kural = (
            (f"10) CHAPTERS — this video is short, so it has ONE chapter: put a single "
             "chapter title on the FIRST scene only and leave \"bolum\" out of every other "
             "scene. Use \"bolum_yeri\":\"orta\".\n"
             if bolum_adet == 1 else
             f"10) CHAPTERS — split the video into EXACTLY {bolum_adet} chapters. This is how the "
            "reference channel is built: not one flat narration, but chapters that each have "
            "their own title and their own arc.\n"
            "   Each chapter must work as a small self-contained piece: it opens with a line "
            "that raises a specific question, develops ONE idea, and closes with a line that "
            "hands over to the next chapter. Do not let two chapters cover the same ground.\n"
            "   On the FIRST scene of each chapter set \"bolum\" to that chapter's title, and "
            "\"bolum_yeri\" to either \"orta\" or \"ust\":\n"
            "     \"orta\" = a big centred chapter card, written as a THEME "
            "(e.g. \"Preserving Madeira's identity between tradition and the modern world\"). "
            "Use this for the chapter that opens a major new part of the story.\n"
            "     \"ust\" = a smaller top-left label, written as a descriptive phrase "
            "(e.g. \"A tourist paradise and the contradictions behind it\"). Use this for the "
            "rest.\n"
            "   Roughly one chapter in three uses \"orta\", the others \"ust\". Never put two "
            "\"orta\" chapters back to back.\n"
            "   Titles are 5-12 words, in the story's language, no numbering, no colon, and they "
            "must NOT repeat the video title.\n"
            "   EVERY OTHER scene leaves \"bolum\" out entirely.\n"))
    else:
        bolum_kural = ""

    # ── SAHNE UZUNLUGU: TEK BANT MI, CIFT MODLU MU (5 Agu 2026 olcumu) ──
    # Referans #12 (@ImpossibleTravel38) 8 videoda 1699 cekim olculdu: medyan 6.4 sn ama
    # dagilim CIFT MODLU — %33'u 4 sn'den kisa, %29'u 12 sn'den uzun (p10 1.7 sn, p90 28.1 sn).
    # Dar kelime bandi (kelime..kelime+3) her sahneyi ayni uzunlukta yapiyordu; belgeselde
    # bu "metronom" hissi veriyor. tempo="cift-modlu" profillerde ritim bilincli degisir.
    if prof.get("tempo") == "cift-modlu":
        # Bantlar OLCULEN dagilimdan turetilir ve AGIRLIKLI ORTALAMASI 1.0 x sahne_sn'dir.
        # Bu sart: sahne sayisi = hedef_sure / sahne_sn oldugu icin bantlarin ortalamasi
        # sahne_sn'i asarsa video hedeflenen sureden UZUN cikar (ilk yazimda %23 asiyordu).
        # Olculen (referans #12, 2147 cekim): %32 <4sn | %26 4-8sn | %14 8-12sn | %29 12sn+
        # ortalama 12.5 sn, medyan 6.5 sn. Agirlikli kontrol:
        #   .32*0.20 + .26*0.48 + .14*0.80 + .29*2.40 = 1.00  ✓
        wpm = float(prof.get("_wpm") or 150)
        sn = float(prof["sahne_sn"])
        tavan = float(prof.get("maks_sahne_sn") or 0)
        # Carpanlarin AGIRLIKLI ORTALAMASI 1.0 olmali (yoksa video hedef sureyi kacirir):
        #   .32*0.55 + .26*0.91 + .14*1.18 + .29*1.45 = 0.998  ✓
        # maks_sahne_sn varsa carpanlar bu daha DAR sete gecer: en uzun bant tavana oturur
        # (1.45 x 5.5 = 8.0 sn), boylece hicbir sahne tavani gecmez.
        # 1.45 -> 1.42: kelime->saniye yuvarlamasi en uzun banti 8.1 sn'ye cikariyordu.
        carpanlar = (0.55, 0.91, 1.18, 1.42) if tavan else (0.20, 0.48, 0.80, 2.40)

        def _sn(c):
            v = sn * c
            return min(v, tavan) if tavan else v

        def _k(c):             # saniye -> kelime
            return max(4, int(round(_sn(c) * wpm / 60)))
        k1, k2, k3, k4 = (_k(c) for c in carpanlar)
        kelime_kural = (
            f"2) Produce EXACTLY {hedef} sequential scenes. Scene LENGTH MUST VARY — this is a "
            "documentary, not a metronome. These proportions were measured shot by shot from the "
            "reference channel, so hit them:\n"
            f"   ~32% VERY SHORT: about {k1} words (max {k2 - 1}) — one hard beat, a single "
            "short sentence.\n"
            f"   ~26% SHORT: about {k2} words.\n"
            f"   ~14% MEDIUM: about {k3} words.\n"
            f"   ~29% LONG: about {k4} words"
            + (f" — HARD CEILING {k4} words, never more: no shot may stay on screen longer "
               f"than {int(prof['maks_sahne_sn'])} seconds.\n" if tavan else
               f" (range {int(k4*0.7)}-{int(k4*1.3)}) — three or four sentences that hold on ONE "
               "shot while the narration develops a whole thought.\n")
            + "Never put two VERY SHORT scenes back to back and never three scenes of the same "
            "class in a row. Alternate so the video breathes. If the source text is short, EXPAND "
            "it by adding MORE SCENES, never by pushing a line past its class range. The "
            "voiceover fields together form continuous narration in the ORIGINAL language.\n")
    else:
        kelime_kural = (
            f"2) Produce EXACTLY {hedef} sequential scenes. Every voiceover line must be "
            f"{prof['kelime']}-{prof['kelime'] + 3} words long — this is the TARGET BAND, land "
            f"inside it; the absolute ceiling is {prof['kelime'] + 4} words and lines shorter than "
            f"{prof['kelime']} words are too thin. Count the words before writing the next scene. A "
            f"scene is {prof['sahne_sn']} seconds of speech and a longer line breaks the edit rhythm "
            "and the requested video length. Write short, punchy sentences; split any longer thought "
            "across two consecutive scenes instead of writing one long line. If the source text is "
            "short, EXPAND it by adding MORE SCENES worth of detail — never by making individual "
            "lines longer. The voiceover fields together form continuous narration in the ORIGINAL "
            "language.\n")

    # Profilin kendi sahne SOZLESMESI varsa onu kullan (animasyon alt-stilleri), yoksa genel kural.
    if prof.get("sahne_sozlesme"):
        sahne_kural = prof["sahne_sozlesme"]
        if prof.get("tip_atamasi", True):
            sahne_kural = sahne_tipi_atamasi(hedef) + sahne_kural
    # UNLU MODU EZMESI: hikaye sozlesmesi "the main character" ifadesini SART kosuyor,
    # unlu kurali ise gercek isim istiyor — model sozlesmeye uyup ismi YAZMIYORDU.
    # Sonuc (4 Agu Marley testi): her sahnede FARKLI rastgele insan. Ezme kurali en sona
    # eklenir ki sozlesmeyi acikca gecersiz kilsin.
    if unlu:
        sahne_kural += (
            "\nCELEBRITY OVERRIDE (this beats every rule above): do NOT use the phrase 'the "
            "main character' anywhere. In EVERY scene_prompt and in thumbnail.prompt write the "
            "real person's actual NAME as the subject (e.g. 'Bob Marley'). The name itself "
            "guarantees identity consistency across scenes; never invent appearance details "
            "that contradict the real person, and keep every frame strictly photorealistic "
            "live-action — never cartoon, illustration or 3D-render style.")
    else:
        sahne_kural = (
            "IMPORTANT: give scene_prompt for EVERY scene = a vivid 16:9 ENGLISH description of the "
            "action/place/camera/mood. CHARACTER CONSISTENCY IS THE #1 RULE: the SAME single main "
            "character is the clearly-visible subject of EVERY scene. EVERY scene_prompt MUST contain "
            "the exact phrase 'the main character' as the acting subject performing a clear "
            "pose/action. NEVER introduce a new, different, generic or additional figure. Do NOT "
            "describe the character's colors/face/design (that comes from the reference image); only "
            "describe its POSE/ACTION and the environment, giving EVERY scene a DIFFERENT specific "
            "pose/action/camera angle and setting. Describe ONE single continuous illustration — "
            "never panels, grids or split frames. (For footage scenes this prompt is the fallback if "
            "no clip is found.)\n"
        )
    devam_kural = (
        f"\nCONTINUATION: This is a CONTINUING part of a longer video. Story so far (summary): "
        f"\"{onceki_ozet[:600]}\". Do NOT repeat it; continue the narrative naturally from where it "
        "left off, developing NEW points/scenes."
        if devam else "")
    return (
        "You are a professional video editor and scene planner. The user gives a story/script. "
        "The main CHARACTER is provided separately as a REFERENCE IMAGE, so never describe the "
        "character's appearance.\n"
        f"MODE/STYLE: {prof['ad']} — {prof['ozet']}.\n"
        f"{devam_kural}\n"
        "Rules:\n"
        "1) Detect the language of the story.\n"
        + kelime_kural +
        "8) Also return \"ozet\": a 2-sentence summary (in the story's language) of what THIS part "
        "covered, for continuity.\n"
        f"{footage_kural} {sahne_kural}"
        f"4) {overlay_kural}\n"
        "5) Choose a Microsoft Azure neural voice by language: tr->tr-TR-EmelNeural, "
        "en->en-US-AndrewMultilingualNeural, es->es-ES-AlvaroNeural, de->de-DE-ConradNeural, "
        "fr->fr-FR-HenriNeural; else a fitting one.\n"
        "6) Thumbnail: object with text = a punchy 2-5 word hook in the ORIGINAL language ALL CAPS, "
        "and prompt = a dramatic 16:9 scene featuring the character, strong emotion, high contrast.\n"
        f"{hd_kural}\n"
        f"{grafik_kural}"
        f"{bolum_kural}"
        f"{etiket_kural}"
        # UNLU MODU: kullanici acikca sectiyse (Gemini yolu benzerlik destekliyor) gercek isim
        # YAZILIR — her sahne ayni taninabilir kisiyi gosterir. Normal modda isim YASAK:
        # gorsel API'leri isimli talebi reddediyor (400) -> tarif yazilir.
        + ("REAL PEOPLE: this video is ABOUT a real public figure and the image engine supports "
           "likeness — you SHOULD write the person's real name in scene_prompt and thumbnail.prompt "
           "so every scene depicts the SAME recognizable person accurately in their era.\n"
           if unlu else
           "REAL PEOPLE: NEVER write a real person's name inside scene_prompt or thumbnail.prompt "
           "(image APIs reject named-likeness requests). Instead describe an era-appropriate figure by "
           "APPEARANCE only: build, outfit, hairstyle, pose, decade styling — without naming or claiming "
           "identity (e.g. 'a slim pop star in a red leather jacket, 1980s stage lighting'). Real names "
           "ARE allowed in footage_sorgu (stock search).\n")
        + "Respond ONLY valid JSON: {\"language\":\"en\",\"voice\":\"...\",\"ozet\":\"...\","
        "\"thumbnail\":{\"text\":\"...\",\"prompt\":\"...\"},"
        "\"scenes\":[{\"n\":1,\"voiceover\":\"...\",\"kaynak\":\"ai|footage\","
        "\"scene_prompt\":\"...\",\"footage_sorgu\":\"...\",\"overlay\":\"...\",\"hd\":false"
        + (",\"grafik\":{...}" if prof.get("edit_paketi") else "")
        + (",\"bolum\":\"\",\"bolum_yeri\":\"orta|ust\"" if prof.get("bolumler") else "")
        + (",\"alt_band\":{},\"etiketler\":[],\"vurgu_kutu\":{}"
           if prof.get("saha_etiketi") else "")
        + "}]}"
    )


def plan_uret(story: str, prof: dict, hedef_sahne=40, devam=False, onceki_ozet="",
              bolum_yonergesi="", unlu=False) -> dict:
    # max_tokens sahne sayisina gore OLCEKLI. Sabit 16000, dusuk-kademe OpenAI hesabinda
    # TPM (dakikadaki token) limitini asip HER cagriyi 429'a sokuyordu — retry bile kurtarmaz.
    # ~250 token/sahne yeterli; tavan 12000, taban 2000.
    mt = int(min(12000, max(2000, hedef_sahne * 250 + 1200)))
    sistem = plan_sistem(prof, hedef_sahne, devam, onceki_ozet, unlu=unlu)
    if bolum_yonergesi:   # paralel planlamada her parcaya "SEN SU BOLUMU anlat" yonergesi
        sistem += f"\nPART DIRECTIVE: {bolum_yonergesi}\n"
    body = {
        "model": "gpt-4.1-mini",
        "messages": [{"role": "system", "content": sistem},
                     {"role": "user", "content": story}],
        "response_format": {"type": "json_object"},
        "temperature": 0.7,
        "max_tokens": mt,
    }
    j = oai_chat(body, timeout=180)
    icerik = (j.get("choices") or [{}])[0].get("message", {}).get("content")
    if not icerik:
        raise RuntimeError("OpenAI plan yanıtı boş (içerik filtresi?) — tekrar deneyin")
    try:
        plan = json.loads(icerik)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Plan JSON parse edilemedi (truncate?): {str(e)[:120]}")
    scenes = []
    for s in plan.get("scenes", []):
        if not str(s.get("voiceover", "")).strip():
            continue
        kayn = "footage" if str(s.get("kaynak")) == "footage" and str(s.get("footage_sorgu", "")).strip() else "ai"
        sp = str(s.get("scene_prompt", "")).strip()
        if kayn == "ai" and not sp:
            continue
        # Karakter-her-sahnede guvenlik agi. DIKKAT: eskiden "large central foreground subject"
        # ekleniyordu; planlayici "the stickman commander" gibi yazdigi icin bu HER sahnede
        # tetikleniyor ve cekim sistemini (genis plan %15, orta %40) EZIYORDU -> karakter hep
        # ortada, buyuk ve dimdik cikiyordu. Artik sadece kahramanin VARLIGI garanti edilir,
        # olcek/kompozisyon cekim sozlesmesine birakilir.
        # Karaktersiz kareler MESRU (patlatilmis sema, makro detay, yazi karti) — zorlama.
        karaktersiz = any(x in sp.lower() for x in
                          ("no character", "object macro", "exploded view", "concept card",
                           "comparison", "no figure", "hands only", "map route"))
        if (kayn == "ai" and not karaktersiz and not any(
                x in sp.lower() for x in ("main character", "the hero", "stickman", "the character"))):
            s["scene_prompt"] = "The recurring main character appears in this scene. " + sp
        scenes.append(s)
    if not scenes:
        raise RuntimeError("Sahne plani bos")
    # KARAKTERSIZ ORAN SIGORTASI: planlayici atmosfer sahnesini abartabiliyor (testte %51
    # gorulmustu; hedef ~%20). Tavan %30: fazlasi karakterli sahneye cevrilir — kahraman
    # videonun yildizi kalir, tutarlilik capasi da daha cok sahnede calisir.
    karsiz_idx = [ix for ix, sx in enumerate(scenes)
                  if "no character" in str(sx.get("scene_prompt", "")).lower()]
    tavan = int(len(scenes) * 0.3)
    if len(karsiz_idx) > tavan:
        for ix in karsiz_idx[tavan:]:
            sp = str(scenes[ix].get("scene_prompt", ""))
            sp = sp.replace("no character", "").replace("No character", "").replace("NO CHARACTER", "")
            scenes[ix]["scene_prompt"] = "The recurring main character appears in this scene. " + sp.strip()
    plan["scenes"] = scenes[:60]   # tek cagri tavani (parca basina)
    return plan


# Uzun video (30 dk'ya kadar): parca parca planla, sahneleri birlestir.
MAKS_SAHNE = 620   # ~60 dk hikaye tavani (6 sn/sahne x 600 + pay). Maliyet siniri sure tavaninda.


def _iskelet_cikar(story: str, n_parca: int) -> list:
    """Hikayeyi n_parca ARDISIK bolume ayiran kisa iskelet (TEK ucuz LLM cagrisi).
    Paralel planlamanin temeli: her parca kendi bolum ozetini bilir, oncekini BEKLEMEZ."""
    body = {
        "model": "gpt-4.1-mini",
        "messages": [{"role": "system", "content": (
            f"Split the user's story/script into EXACTLY {n_parca} sequential PARTS of roughly "
            "equal length for video production. For each part write a 2-3 sentence summary (in "
            "the story's language) of the concrete events/points that part covers. Parts must "
            "not overlap and together must cover the WHOLE story in order. Respond ONLY valid "
            "JSON: {\"parts\":[{\"n\":1,\"summary\":\"...\"}]}")},
                     {"role": "user", "content": story}],
        "response_format": {"type": "json_object"},
        "temperature": 0.4,
        "max_tokens": min(4000, n_parca * 160 + 400),
    }
    j = oai_chat(body, timeout=120)
    veri = json.loads(j["choices"][0]["message"]["content"])
    parts = [str(p.get("summary", "")).strip() for p in veri.get("parts", [])]
    parts = [p for p in parts if p]
    if len(parts) != n_parca:
        raise RuntimeError(f"iskelet {len(parts)}/{n_parca} bolum dondu")
    return parts


def _uzun_plan_sirali(story: str, prof: dict, hedef_sahne: int, parca=40, unlu=False) -> dict:
    """ESKI guvenilir yol: parca parca SIRALI planla (her parca oncekinin ozetini bekler).
    Paralel yolun iskeleti cikarilamazsa buraya dusulur."""
    toplam_plan = None
    ozet = ""
    scenes = []
    while len(scenes) < hedef_sahne:
        kalan = hedef_sahne - len(scenes)
        bu = min(parca, kalan)
        try:
            p = plan_uret(story, prof, hedef_sahne=bu, devam=bool(scenes), onceki_ozet=ozet, unlu=unlu)
        except Exception as e:
            # Bir parca yine de basarisizsa (retry'lar tukendi): elde sahne varsa onlarla
            # devam et, yoksa hatayi firlat. Boylece tek parca 30dk isi oldurmez.
            print(f"  uzun_plan parca hata: {str(e)[:160]}", file=sys.stderr)
            if scenes:
                break
            raise
        yeni = p.get("scenes", [])
        if not yeni:
            break
        scenes.extend(yeni)
        ozet = (ozet + " " + str(p.get("ozet", ""))).strip()[-1200:]
        if toplam_plan is None:
            toplam_plan = p            # ilk parca voice/thumbnail'i tasir
    if not scenes:
        raise RuntimeError("Sahne plani bos")
    toplam_plan["scenes"] = scenes[:hedef_sahne]
    if len(scenes) < hedef_sahne * 0.85:
        toplam_plan["_eksik_oran"] = round(len(scenes) / hedef_sahne, 2)
    return toplam_plan


def _alt_band_props(s: dict) -> dict:
    """Alt band (lower third) — OLCULEN en yaygin yazi turu (%33).
    baslik 1-4 kelime, alt satir opsiyonel baglam."""
    ab = s.get("alt_band")
    if not isinstance(ab, dict):
        return {}
    b = " ".join(str(ab.get("baslik") or "").split())[:34].strip()
    if not b:
        return {}
    a = " ".join(str(ab.get("alt") or "").split())[:40].strip()
    return {"altBand": {"baslik": b, **({"alt": a} if a else {})}}


def _kaynak_yazi_props(s: dict) -> dict:
    """Ekran kunyesi (CC atfi) — sahne sozlugunden props'a KAYIPSIZ tasinir.

    ⚠ FAZ I-41'DE OLCULEN KUSUR: yukarida uc noktada `s["kaynakYazi"]`
    yaziliyordu (avci atfi, `kaynak.atif_al` kanali, genel yedek sorgu) ama
    `props_sahneler` sahneyi ALAN ALAN kurdugu icin bu alan props SINIRINDA
    DUSUYORDU. Sonuc: CC klip kullanan her uretimde ekran atfi HIC
    cizilmiyordu — ne Remotion `VidrushVideo` yolunda (tipte alan yoktu) ne de
    `hizli_render` yolunda (`_kaynak_yazi_filtre` alani okuyor ama props'ta
    alan olmadigi icin her zaman bos donuyordu).

    ⚠ Lisansin RESMI atif yeri video aciklamasidir (`kaynak.atif_listesi`);
    bu ekran kunyesi onun yerine GECMEZ, gorunur karsiligidir.

    Kunye yoksa alan HIC gecmez -> props eskisiyle BIT-BIT ayni kalir.
    """
    try:
        k = " ".join(str(s.get("kaynakYazi") or "").split()).strip()
    except Exception:
        return {}
    return {"kaynakYazi": k[:80]} if k else {}


def _etiket_props(s: dict) -> dict:
    """Plan'in urettigi etiket/vurgu alanlarini DOGRULAYIP props'a cevirir.
    Model bazen koordinati 0-100 olarak ya da metni cok uzun veriyor; kare disina
    tasan ya da okunmayan etiket, etiket olmamasindan kotudur."""
    cik = {}
    et = []
    for e in (s.get("etiketler") or [])[:2]:   # olculen omur 1.8 sn — 3 etiket kalabalik
        if not isinstance(e, dict):
            continue
        m = " ".join(str(e.get("metin") or "").split())[:26].strip()
        if not m:
            continue
        try:
            x, y = float(e.get("x")), float(e.get("y"))
        except Exception:
            continue
        if x > 1 or y > 1:            # 0-100 verilmis -> orana cevir
            x, y = x / 100.0, y / 100.0
        if not (0.04 <= x <= 0.96 and 0.06 <= y <= 0.86):
            continue                  # kare disi / altyazi bandi
        et.append({"metin": m.upper(), "x": round(x, 3), "y": round(y, 3)})
    if et:
        cik["etiketler"] = et
    k = s.get("vurgu_kutu")
    if isinstance(k, dict) and k:
        try:
            x, y, w, h = (float(k.get("x")), float(k.get("y")),
                          float(k.get("w")), float(k.get("h")))
            if max(x, y, w, h) > 1:
                x, y, w, h = x / 100.0, y / 100.0, w / 100.0, h / 100.0
            if (0 <= x < 1 and 0 <= y < 1 and 0.08 <= w <= 0.9 and 0.08 <= h <= 0.9
                    and x + w <= 1.0 and y + h <= 1.0):
                cik["vurguKutu"] = {"x": round(x, 3), "y": round(y, 3),
                                    "w": round(w, 3), "h": round(h, 3),
                                    **({"daire": True} if k.get("daire") else {})}
        except Exception:
            pass
    return cik


def _plan_kelime(plan: dict) -> int:
    return sum(len(str(sc.get("voiceover") or "").split())
               for sc in (plan.get("scenes") or []))


def satirlari_uzat(plan: dict, prof: dict, hedef_kel: int) -> dict:
    """Sahne SAYISINI degistirmeden her sahnenin anlatimini hedef uzunluga getirir.

    NEDEN VAR (11 Agu 2026 olcumu): sure_tamamla eksik sureyi SAHNE EKLEYEREK
    kapatiyordu. Sonuc: 60 sn'lik videoda 10 sahne hedeflenirken 13 sahne olustu ve
    ortalama cekim 3.8 sn'ye dustu (referans medyani 6.5 sn, olculen dagilim %32'si
    4 sn alti — bizde %64). Yani sureyi tutturmak ugruna TEMPO bozuluyordu.
    Dogru cozum: sahne sayisi hedefteyse satirlari UZAT, yeni sahne ekleme.
    """
    scenes = plan.get("scenes") or []
    if not scenes:
        return plan
    satirlar = [{"i": i, "voiceover": str(sc.get("voiceover") or "")}
                for i, sc in enumerate(scenes)]
    sistem = (
        "You rewrite documentary narration lines to be LONGER without changing meaning, "
        f"order, or count. Each line must become between {hedef_kel} and {hedef_kel + 2} "
        f"words (currently shorter). NEVER exceed {hedef_kel + 2} words on any line. "
        "Add concrete detail that belongs to that exact moment: a number, a texture, a "
        "consequence, a small observed fact. Do NOT add new scenes, do NOT merge or split "
        "lines, do NOT summarise, do NOT repeat other lines. Keep the same language and tone. "
        'Return JSON: {"lines":[{"i":<same index>,"voiceover":"<longer text>"}]} with EXACTLY '
        f"{len(satirlar)} entries.")
    try:
        j = oai_chat({"model": "gpt-4.1-mini",
                      "messages": [{"role": "system", "content": sistem},
                                   {"role": "user", "content": json.dumps(satirlar)}],
                      "response_format": {"type": "json_object"},
                      "temperature": 0.6,
                      "max_tokens": int(min(12000, max(2000, len(satirlar) * 160 + 800)))},
                     timeout=180)
        icerik = (j.get("choices") or [{}])[0].get("message", {}).get("content") or ""
        yeni = json.loads(icerik).get("lines") or []
    except Exception as e:
        print(f"  satir uzatma basarisiz: {str(e)[:120]}", file=sys.stderr)
        return plan
    degisen = 0
    for y in yeni:
        try:
            i = int(y.get("i"))
            metin = str(y.get("voiceover") or "").strip()
        except Exception:
            continue
        if not (0 <= i < len(scenes)) or not metin:
            continue
        # SADECE UZATMA: model kisaltirsa eskisi korunur (video daha da kisalmasin)
        if len(metin.split()) > len(str(scenes[i].get("voiceover") or "").split()):
            scenes[i]["voiceover"] = metin
            degisen += 1
    print(f"  satir uzatma: {degisen}/{len(scenes)} satir uzatildi", file=sys.stderr)
    return plan


def sure_tamamla(plan: dict, story: str, prof: dict, sure_dk: float,
                 bildir=None, hedef_sahne: int = 0) -> dict:
    """Plan hedef SUREYI tutuyor mu? Tutmuyorsa sahne EKLEYEREK tamamlar.

    NEDEN GEREKLI (7 Agu 2026, canli iste olculdu): 1 dakika istenen bir belgesel
    37.8 saniye cikti — %37 kisa. Sahne SAYISI dogruydu (10/10) ama plan her satiri
    bant hedefinden kisa yazdi (~112 kelime, butce 178). Sahne suresi seslendirme
    sesinin uzunlugundan geldigi icin kisa satir = kisa video, ve arada hicbir kontrol
    yoktu. Sahne sayisi kontrolu (_eksik_oran) bunu YAKALAMAZ: sayi tamdi.

    Butce = hedef saniye x sesin gercek WPM'i / 60. Eksik kaldiysa eksigi kapatacak
    kadar EK SAHNE istenir (en fazla 2 tur; her tur ~1 kurus'luk gpt-4.1-mini cagrisi).
    """
    wpm = float(prof.get("_wpm") or 150)
    butce = sure_dk * 60 * wpm / 60.0
    kel_sahne = max(4, float(prof.get("kelime") or 15))
    for tur in range(2):
        mevcut = _plan_kelime(plan)
        if mevcut >= butce * 0.92:
            break
        eksik = butce - mevcut
        # SAHNE SAYISI TAVANI: hedefe ulasildiysa yeni sahne EKLEMEYIZ, satirlari uzatiriz.
        # (11 Agu 2026: sahne ekleme temposu 3.8 sn'ye dusuruyordu, referans 6.5.)
        if hedef_sahne and len(plan.get("scenes") or []) >= hedef_sahne:
            # %8 pay birakiliyor: model hedefi ASIYOR (11 Agu olcumu: 17 kelime
            # istendi, 20.6 yazdi -> video 60 sn yerine 72 sn, yani %121).
            ihtiyac = int(round(butce * 0.92 / max(1, len(plan.get("scenes") or []))))
            print(f"  sahne sayisi hedefte ({len(plan.get('scenes') or [])}/{hedef_sahne}); "
                  f"sahne EKLENMIYOR, satirlar ~{ihtiyac} kelimeye uzatiliyor", file=sys.stderr)
            if bildir:
                bildir("Anlatım uzatılıyor (tempo korunuyor)...", None)
            plan = satirlari_uzat(plan, prof, ihtiyac)
            continue
        ek_sahne = int(min(60, max(1, round(eksik / kel_sahne))))
        if hedef_sahne:
            ek_sahne = min(ek_sahne, max(1, hedef_sahne - len(plan.get("scenes") or [])))
        tahmini = mevcut / wpm * 60
        mesaj = (f"Plan {tahmini:.0f} sn'lik ({mevcut} kelime / butce {butce:.0f}); "
                 f"{ek_sahne} sahne daha isteniyor")
        print(f"  sure tamamlama tur {tur+1}: {mesaj}", file=sys.stderr)
        if bildir:
            bildir("Süre tamamlanıyor (plan kısa kaldı)...", None)
        ozet = str(plan.get("ozet") or "")[:700]
        yon = ("The video is still SHORT of its target length. Continue the SAME video with "
               f"{ek_sahne} additional scenes that add NEW detail — new examples, numbers, "
               "consequences, or a closing section. Do NOT repeat anything already covered "
               "and do NOT summarise. Keep the same language and tone.")
        try:
            ek = plan_uret(story, prof, hedef_sahne=ek_sahne, devam=True,
                           onceki_ozet=ozet, bolum_yonergesi=yon)
        except Exception as e:
            print(f"  sure tamamlama basarisiz: {str(e)[:140]}", file=sys.stderr)
            break
        yeni = ek.get("scenes") or []
        if not yeni:
            break
        plan["scenes"] = (plan.get("scenes") or []) + yeni
    son = _plan_kelime(plan)
    print(f"  PLAN SURESI: {son} kelime -> ~{son / wpm * 60:.0f} sn "
          f"(hedef {sure_dk * 60:.0f} sn, {len(plan.get('scenes') or [])} sahne)",
          file=sys.stderr)
    return plan


# ⚠ `unlu` main'den geldi; plan_uret -> plan_sistem'e kadar tasinir.
def uzun_plan(story: str, prof: dict, sure_dk: float, bildir=None,
              unlu: bool = False) -> dict:
    hedef_sahne = int(min(MAKS_SAHNE, max(1, (sure_dk * 60) / prof["sahne_sn"])))
    if hedef_sahne <= 55:
        return sure_tamamla(plan_uret(story, prof, hedef_sahne=hedef_sahne,
                                      unlu=unlu),
                            story, prof, sure_dk, bildir, hedef_sahne=hedef_sahne)
    # ── PARALEL PLANLAMA ──
    # Eskiden parcalar SIRALI yaziliyordu (her biri oncekinin ozetini bekler; 30 dk video
    # ~8-10 dk plan). Simdi: 1 ucuz cagriyla hikaye ISKELETI (bolum ozetleri) cikar, sonra
    # tum parcalari AYNI ANDA yazdir — sureklilik iskeletten gelir. ~3x hizli.
    parca = 40
    n_parca = -(-hedef_sahne // parca)   # ceil
    try:
        bolumler = _iskelet_cikar(story, n_parca)
    except Exception as e:
        print(f"  iskelet cikarilamadi ({str(e)[:120]}) -> sirali plana donuluyor", file=sys.stderr)
        return _uzun_plan_sirali(story, prof, hedef_sahne, parca, unlu=unlu)
    gorevler = []
    for i in range(n_parca):
        bu = min(parca, hedef_sahne - parca * i)
        onceki = " ".join(bolumler[:i])[-700:]
        yon = (f"This is part {i+1} of {n_parca} of one continuous video. "
               + (f"Earlier parts already covered: \"{onceki}\" — do NOT repeat any of it. " if i else "")
               + f"THIS PART must cover ONLY the following, in order: \"{bolumler[i]}\"")
        gorevler.append((i, bu, yon))
    sonuc = [None] * n_parca
    with ThreadPoolExecutor(max_workers=min(4, n_parca)) as havuz:
        isler_f = {havuz.submit(plan_uret, story, prof, bu, i > 0, "", yon, unlu): i
                   for i, bu, yon in gorevler}
        for f in as_completed(isler_f):
            i = isler_f[f]
            try:
                sonuc[i] = f.result()
            except Exception as e:
                # Tek parca coktuyse o bolum atlanir; _eksik_oran ust kata bildirir
                print(f"  plan parca {i+1} hata: {str(e)[:140]}", file=sys.stderr)
    if not any(sonuc):
        raise RuntimeError("Sahne plani bos")
    toplam_plan = next(p for p in sonuc if p)   # ilk basarili parca voice/thumbnail'i tasir
    scenes = []
    for p in sonuc:
        if p:
            scenes.extend(p.get("scenes", []))
    toplam_plan["scenes"] = scenes[:hedef_sahne]
    if len(scenes) < hedef_sahne * 0.85:
        toplam_plan["_eksik_oran"] = round(len(scenes) / hedef_sahne, 2)
    # Uzun (paralel) yolda da SURE denetimi: parcalar kisa yazdiysa eksik kapatilir
    return sure_tamamla(toplam_plan, story, prof, sure_dk, bildir,
                        hedef_sahne=hedef_sahne)


def on_ciz_16x9(yol: str) -> bool:
    """Uretilen 1536x1024 (3:2) gorseli GERCEK 16:9'a (1536x864) merkezden kirpar.

    Neden (Polat, 4 Agu 2026: "gorseller saginda solundan tutulup uzatilmis gibi"):
    Render 1920x1080'e objectFit:cover ile basiyordu -> 3:2 gorsel 1.25x buyutulup
    dikeyden %15.6 kirpiliyordu. Ustune Ken Burns 1.12x zoom binince toplam 1.4x
    oluyor ve sahne ilerledikce gorselin ~%40'i kare disina tasiyor; kompozisyon
    sikisiyor, kenardaki nesneler kayboluyor.
    Cozum: kirpmayi ONCEDEN ve BIR KEZ yap. Boylece render'a giren gorsel zaten
    16:9 olur, cover hicbir sey yapmaz ve TEK olcekleme Ken Burns kalir — ne kadar
    kirpildigi tahmin edilebilir olur. Prompt zaten ust/alt %9'u bos biraktiriyor,
    yani kirpilan bolgede icerik yok.
    """
    try:
        from PIL import Image
        im = Image.open(yol)
        g, y = im.size
        hedef_y = int(round(g * 9 / 16))
        if y <= hedef_y + 1:
            return False                      # zaten 16:9 ya da daha genis
        ust = (y - hedef_y) // 2
        im.crop((0, ust, g, ust + hedef_y)).save(yol)
        return True
    except Exception as e:
        print(f"  16:9 kirpma atlandi: {str(e)[:120]}", file=sys.stderr)
        return False


def referansli_gorsel(scene_prompt: str, kar_yol: str, hedef: str,
                      stil_prompt: str = "", kar_kilit: str = "", stil_yol: str = "",
                      capa_yol: str = "", stil_kilit: str = "", yazi_yasak: bool = True,
                      model: str = "", cerceve: str = "", deneme=5,
                      kanon_modu: bool = False, saglayici: str = "") -> bool:
    """OpenAI images/edits: karakter + stil + GORSEL CAPA referanslariyla sahne uretir.
    capa_yol: ilk uretilen sahnenin gorseli -> sonraki sahnelere ek referans olarak verilir,
    boylece karakter VE stil ilk kareye kilitlenir (her sahnede birebir ayni). kar_kilit:
    karakter tarifi, stil_kilit: kanonik stil cumlesi. yazi_yasak: goruntude yazi YASAK
    (animasyon icin kritik; kapakta False)."""
    kar_var = bool(kar_yol and os.path.exists(kar_yol))
    stil_gor = bool(stil_yol and os.path.exists(stil_yol))
    capa_var = bool(capa_yol and os.path.exists(capa_yol) and capa_yol != hedef)
    # PROMPT SIRASI ONEMLI: once SAHNE/AKSIYON, sonra kisa kimlik kilidi.
    # Referans gorsel notr duruslu oldugu icin modelin PIKSEL egilimi "dimdik dur"a cekiyordu;
    # bu yuzden aksiyon en basta ve en guclu sekilde tekrarlanir.
    prompt = scene_prompt.rstrip(". ") + "."
    # KARAKTERSIZ KARE (patlatilmis sema / makro detay / yazi karti / karsilastirma):
    # kimlik kilidi EKLENMEZ, aksi halde model kareye zorla bir figur sokar.
    karaktersiz = any(x in (scene_prompt or "").lower() for x in
                      ("no character", "object macro", "exploded view", "concept card",
                       "no figure", "hands only", "map route"))
    if karaktersiz:
        prompt += (" This frame contains NO character and no people at all — the object, diagram "
                   "or lettering itself is the entire subject. Do not add any figure."
                   " It must still be drawn in EXACTLY the same medium, line quality, palette and "
                   "texture as the rest of the video — a hand-drawn plan, an inked map, a written "
                   "list. No clean vector graphics, no realistic phone or app interface, no system "
                   "fonts, no grey wireframes, no dotted CAD lines.")
    if (kar_var or capa_var) and not karaktersiz:
        # 1) POZ SERBESTLIGI — en kritik cumle. Referans SADECE tasarim kaynagi, poz kaynagi DEGIL.
        prompt += (" THE REFERENCE IMAGE IS A CHARACTER DESIGN SHEET, NOT A POSE REFERENCE. It shows "
                   "the character standing neutrally only so you can see how it is drawn. In THIS "
                   "picture the character must be fully ACTING OUT the moment described above — the "
                   "body language, gesture, posture and facial expression must match that action and "
                   "emotion. Do NOT draw the character standing upright and facing the camera with "
                   "arms at its sides unless the scene text explicitly asks for it. Show it leaning, "
                   "reaching, crouching, running, pointing, carrying, turning, looking — whatever the "
                   "moment requires, interacting with the objects and surroundings named in the scene.")
        # 2) KIMLIK — kisa tutulur; uzun kilit metni aksiyonu bogar
        prompt += (" IDENTITY LOCK: keep the character's design identical to the reference — same "
                   "body and face design, same exact colours, same proportions, same clothing and "
                   "markings — but carry over NOTHING else: not its pose, not its camera angle, not "
                   "its background, and not any object it holds there. Render exactly ONE main "
                   "character unless the scene describes others. Obey the shot type and character "
                   "scale given in the scene text; the environment carries the picture.")
        # ⚠ 1 Agu 2026: KANON'a destek/veri-karti EKLENMEZ. Kanon notr bir tasarim
        # sayfasidir; ona "anlatilan sayiyi bir yuzeye yaz" denince model UYDURUYOR
        # ("SALES GROWTH" grafigi) ve o kirli kanon 24 sahnenin HEPSINE kopyalaniyor.
        # Bu, cozdugumuz "kirli referans" hatasinin kendi elimizle geri getirilmis hali.
        if not kanon_modu:
            prompt += DESTEK_GORSEL + VERI_KARTI_GORSEL + MARKA_YASAK
        else:
            prompt += MARKA_YASAK
        if kar_kilit:
            prompt += f" Character identity to match: {kar_kilit}"
        prompt += (" COLOUR LOCK: the character's colours are fixed and identical in every scene "
                   "regardless of lighting, time of day or background — the exact same hues at noon, "
                   "at night, in caves and in firelight. If any style instruction suggests a "
                   "different figure colour, the character's own locked colours always win.")
    if stil_gor or capa_var:
        prompt += (" ART-STYLE LOCK: match the EXACT art style of the reference images — identical "
                   "rendering technique, line weight, color palette, shading, texture and level of "
                   "detail. The whole series must look like one consistent piece by the same artist.")
    # ── STIL: SON SOZ ONUN OLMALI ──
    # Onceden stil kunyesi hem "Canonical style" hem "Art direction" olarak IKI KEZ
    # giriyordu (ayni 1000+ karakter) ve ortada kaliyordu; sonrasindaki cerceve/kompozisyon
    # metni onu sulandiriyordu. Artik: referanstan tureyen SOZLESME varsa TEK KEZ ve
    # promptun EN SONUNDA verilir — modele en yakin talimat en guclusudur.
    sozlesme = stil_kilit if "STYLE CONTRACT" in (stil_kilit or "") else ""
    if not sozlesme and "STYLE CONTRACT" in (stil_prompt or ""):
        sozlesme = stil_prompt
    if sozlesme:
        if stil_prompt and stil_prompt != sozlesme:
            prompt += f" Art direction: {stil_prompt}."
    else:
        if stil_kilit:
            prompt += f" Canonical style: {stil_kilit}."
        if stil_prompt:
            prompt += f" Art direction: {stil_prompt}."
    if cerceve:
        prompt += cerceve   # kompozisyon/cerceveleme (ortam basrol, karakter cerceveyi doldurmaz)
    prompt += " 16:9 cinematic composition."
    if sozlesme:
        prompt += sozlesme          # EN SON: referanstan turemis stil sozlesmesi
    if yazi_yasak:
        # Kullanici: goruntude MINIMAL yazi sorun degil; istenmeyen sey altyazi bandi/filigran.
        prompt += (" Do NOT add subtitle bars, caption strips, lower-thirds or watermarks. Small "
                   "incidental text that naturally belongs in the scene is fine, but keep it minimal "
                   "and never cover the image with words. Single full-bleed illustration: do NOT split "
                   "the image into panels, grids, frames, borders or comic strips.")

    # GROK yolu (unlu modu): referans desteklemez, prompt tek basina gider — unlu ismin
    # kendisi tutarlilik cipasidir. Basarisizsa asagidaki yollara DUSMEZ (stil karismasin).
    if saglayici == "grok" and XAI_KEY:
        # Grok'un varsayilan estetigi stilize/oyun-sanati kaciyor; uzun promptta gercekcilik
        # kilidi eriyebiliyor -> EN SONA sert ve kisa bir kilit daha (son talimat agir basar).
        return grok_gorsel(prompt + " ULTRA-REALISTIC PHOTOGRAPH: this must look like a real "
                           "photo taken by a real camera — absolutely NOT illustration, NOT "
                           "3D render, NOT game art, NOT stylized.", hedef)
    # GEMINI yolu: global saglayici gemini ise VEYA bu is icin acikca istendiyse (unlu modu)
    if (saglayici or SAGLAYICI) == "gemini" and GEMINI_KEY:
        refler = [y for y in (kar_yol if kar_var else None,
                              capa_yol if capa_var else None,
                              stil_yol if (stil_gor and not capa_var) else None) if y]
        return gemini_gorsel(prompt, refler, hedef)

    for d in range(deneme):
        acik = []
        try:
            files = []
            # ── TEMIZ CAPA ILKESI (en kritik duzeltme) ──
            # Capa varsa SADECE capa gonderilir; kullanicinin ham referansi ARTIK GONDERILMEZ.
            # Sebep: "elindeki kahve her sahneye tasindi" bir PROMPT degil PIKSEL sorunuydu —
            # her cagriya fincanli goruntu giriyordu. Kopyalanacak fincan olmayinca sorun biter.
            if capa_var:
                fcapa = open(capa_yol, "rb"); acik.append(fcapa)
                files.append(("image[]", ("anchor.png", fcapa, "image/png")))
            else:
                # Capa yoksa (ilk kurulum) ham referans + stil gorseli kullanilir
                if kar_var:
                    fkar = open(kar_yol, "rb"); acik.append(fkar)
                    files.append(("image[]", ("character.png", fkar, "image/png")))
                if stil_gor:
                    fstil = open(stil_yol, "rb"); acik.append(fstil)
                    files.append(("image[]", ("style.png", fstil, "image/png")))
            # quality: OpenAI varsayilani 'auto' (~high, ~$0.28/gorsel). 'medium' (~$0.09)
            # %65-70 ucuz ve 1536x1024'te fark neredeyse gorunmez (ozellikle duz-vektor/
            # stickman animasyonda ayirt edilemez). IMAGE_QUALITY env ile deploysuz degistirilir:
            # low | medium | high | auto
            data = {"model": (model or GORSEL_MODEL_DOC), "prompt": prompt, "size": "1536x1024",
                    "quality": os.environ.get("IMAGE_QUALITY", "medium")}
            if files:
                r = requests.post("https://api.openai.com/v1/images/edits",
                                  headers=OAI_H, files=files, data=data, timeout=240)
            else:
                r = requests.post("https://api.openai.com/v1/images/generations",
                                  headers=OAI_H, json={**data}, timeout=240)
            if r.status_code >= 400 and _kota_hatasi_mi(r):
                raise BakiyeHatasi(BAKIYE_MESAJI)   # bakiye/limit: retry anlamsiz, hemen bildir
            if r.status_code == 429:
                if d < deneme - 1:
                    time.sleep(_retry_after_bekle(r, d)); continue
            r.raise_for_status()
            import base64
            b64 = r.json()["data"][0]["b64_json"]
            with open(hedef, "wb") as f:
                f.write(base64.b64decode(b64))
            # Sahne kareleri gercek 16:9'a kirpilir. Kanon (tasarim sayfasi) ve kapak
            # HARIC — onlar 3:2 kalmali (kanon referans olarak gonderiliyor, kapak 16:9
            # zaten ayri hesaplanacak).
            if not kanon_modu and not os.path.basename(hedef).startswith(("_kanon", "kapak")):
                on_ciz_16x9(hedef)
            return True
        except BakiyeHatasi:
            raise            # bakiye/limit: retry etme, yukari firlat (para bosa gitmesin)
        except Exception as e:
            # HTTP hatasinda API'nin donduğu govdeyi de yaz (400'un GERCEK sebebi orada:
            # policy reddi mi, parametre mi). Yoksa sadece "400 Bad Request" gorup kor kaliyoruz.
            govde = ""
            try:
                govde = f" | yanit: {e.response.text[:300]}"
            except Exception:
                pass
            print(f"  referansli gorsel hata: {str(e)[:200]}{govde}", file=sys.stderr)
            time.sleep(6)
        finally:
            for f in acik:
                try: f.close()
                except Exception: pass
    return False


CAPA_PROMPT = (
    # IKI POZLU tasarim sayfasi: tek notr figur, sonraki sahnelerde "dimdik dur" baskisi yapiyordu.
    # Iki farkli duruş gostermek modele "bu bir tasarim sayfasi, poz degil" sinyali verir.
    "Character design sheet of the SAME single character shown in the reference image, drawn TWICE "
    "side by side on one plain flat light-grey studio background: on the LEFT standing upright "
    "front-facing with arms relaxed at the sides and hands open and empty; on the RIGHT the same "
    "character in a three-quarter view mid-stride, one arm raised and reaching forward. "
    "Both figures full body from head to feet, even soft lighting, no scenery, no furniture, no "
    "props, no shadows on the background. Reproduce the character's identity exactly: same species, "
    "same colours, same face, same hair, same clothing, same proportions in both drawings. "
    "No other characters. No text, no watermark, no border."
)


def capa_uret(ref_yol: str, hedef: str, kimlik: str, stil: str, stil_yol: str = "",
              model: str = "") -> bool:
    """TEMIZ CAPA (A0) uretir: notr poz, ELLER BOS, sade zemin.
    Neden: kullanicinin referansi genelde 'kirli'dir (elinde nesne, ozel poz, dolu arka plan) ve
    her sahneye gonderilince bunlar KOPYALANIR. Bir kez temiz bir kanon uretip onu donduruyoruz;
    tum sahneler bu temiz kareye kilitlenir. Capa ASLA sahne ciktisiyla guncellenmez (aksi halde
    sapma bilesiklenip 'son sahnede karakter degisti' hatasini uretir)."""
    p = CAPA_PROMPT
    if kimlik:
        p += " " + kimlik
    if stil:
        p += f" Art style: {stil}."
    return referansli_gorsel(p, ref_yol, hedef, stil_prompt="", kar_kilit="",
                             stil_yol=stil_yol, capa_yol="", stil_kilit="",
                             yazi_yasak=True, model=model, cerceve="", deneme=3,
                             kanon_modu=True)


def grok_klip(gorsel_yol: str, scene_prompt: str, hedef_mp4: str) -> bool:
    """GROK (xAI) image-to-video: Sora'nin YARI fiyatina ($0.05/sn) + unlu yuzune toleransli.
    Dogrulanmis akis (4 Agu testi): data-URI gorsel -> request_id -> poll -> video.url indir.
    402/403 -> BakiyeHatasi (uretim temiz durur); diger hatalar -> False (Sora'ya dusulur)."""
    if not XAI_KEY:
        return False
    try:
        saniye = int(os.environ.get("GROK_VIDEO_SN", "8"))
        import base64
        with open(gorsel_yol, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        prompt = ((scene_prompt or "").strip()[:900] +
                  " Cinematic live-action: natural motion of the elements and characters, "
                  "subtle camera drift, photorealistic film look, no on-screen text.")
        r = requests.post("https://api.x.ai/v1/videos/generations",
                          headers={"Authorization": f"Bearer {XAI_KEY}"},
                          json={"model": os.environ.get("GROK_VIDEO_MODEL", "grok-imagine-video"),
                                "prompt": prompt,
                                "image": {"url": f"data:image/png;base64,{b64}"},
                                "duration": saniye}, timeout=120)
        if r.status_code in (401, 402, 403):
            raise BakiyeHatasi("Grok (xAI) kredisi/yetkisi doldu — console.x.ai'den bakiye yukleyin.")
        if r.status_code >= 400:
            print(f"  grok video hata {r.status_code}: {r.text[:200]}", file=sys.stderr)
            return False
        rid = r.json().get("request_id")
        if not rid:
            return False
        bas = time.time()
        url = ""
        while time.time() - bas < 420:
            time.sleep(8)
            try:
                d = requests.get(f"https://api.x.ai/v1/videos/{rid}",
                                 headers={"Authorization": f"Bearer {XAI_KEY}"}, timeout=30).json()
            except Exception:
                continue
            st = d.get("status", "")
            if st == "done":
                url = (d.get("video") or {}).get("url", "")
                break
            if st in ("failed", "error", "rejected"):
                print(f"  grok video basarisiz: {json.dumps(d)[:200]}", file=sys.stderr)
                return False
        if not url:
            print("  grok video zaman asimi", file=sys.stderr)
            return False
        c = requests.get(url, timeout=300)
        if c.status_code >= 400 or len(c.content) < 50000:
            return False
        with open(hedef_mp4, "wb") as f:
            f.write(c.content)
        return True
    except BakiyeHatasi:
        raise
    except Exception as e:
        print(f"  grok video istisna: {str(e)[:160]}", file=sys.stderr)
        return False


def sora_klip(gorsel_yol: str, scene_prompt: str, hedef_mp4: str) -> bool:
    """GERCEK VIDEOLASTIRMA: uretilmis sahne gorselini OpenAI Sora'ya referans verip
    gercek video klibe cevirir (yagmur yagar, karakter kipirdar, kamera suzulur).
    Maliyet ~$0.10/sn (sora-2 720p) -> 8 sn klip ~$0.80. Hata -> False (sahne
    efektli fotograf olarak devam eder, is asla yarim kalmaz)."""
    ref = hedef_mp4 + ".ref.png"
    try:
        saniye = os.environ.get("SORA_SANIYE", "8")
        # Sora input_reference cikti boyutuyla ayni olmali -> 1280x720 kirp
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", gorsel_yol,
                        "-vf", "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720",
                        ref], timeout=60, check=True)
        prompt = ((scene_prompt or "").strip()[:900] +
                  " Cinematic live-action: natural motion of the elements and characters, "
                  "subtle camera drift, photorealistic film look, no on-screen text.")
        with open(ref, "rb") as f:
            r = requests.post("https://api.openai.com/v1/videos", headers=OAI_H,
                              files={"input_reference": ("ref.png", f, "image/png")},
                              data={"model": os.environ.get("SORA_MODEL", "sora-2"),
                                    "size": "1280x720", "seconds": str(saniye),
                                    "prompt": prompt}, timeout=180)
        if r.status_code >= 400:
            print(f"  sora baslatma hata {r.status_code}: {r.text[:200]}", file=sys.stderr)
            return False
        vid = r.json().get("id")
        if not vid:
            return False
        bas = time.time()
        durum = ""
        while time.time() - bas < 420:   # klip basina 7 dk tavan
            time.sleep(10)
            try:
                d = requests.get(f"https://api.openai.com/v1/videos/{vid}",
                                 headers=OAI_H, timeout=30).json()
            except Exception:
                continue
            durum = d.get("status", "")
            if durum == "completed":
                break
            if durum == "failed":
                print(f"  sora klip basarisiz: {str(d.get('error'))[:200]}", file=sys.stderr)
                return False
        if durum != "completed":
            print("  sora klip zaman asimi", file=sys.stderr)
            return False
        c = requests.get(f"https://api.openai.com/v1/videos/{vid}/content",
                         headers=OAI_H, timeout=300)
        if c.status_code >= 400 or len(c.content) < 50000:
            return False
        with open(hedef_mp4, "wb") as f:
            f.write(c.content)
        return True
    except Exception as e:
        print(f"  sora istisna: {str(e)[:160]}", file=sys.stderr)
        return False
    finally:
        try:
            os.remove(ref)
        except Exception:
            pass


async def uret(is_adi: str, story: str, kar_yol: str, stil_yol: str = "",
               mod: str = "documentary", edit_id: str = VARSAYILAN_EDIT,
               sure_dk: float = 2, gecis_acik: bool = True, zoom_acik: bool = True,
               ilerle=None, profil_id: str = "", altyazi_sablon: str = "",
               altyazi_ac: str = "", palet: str = "", palet_ozel: str = "",
               arkaplan: str = "", ses_secim: str = "", isik: str = "",
               acilis_dk=None, sahne_ref: list = None, sora_acik: bool = False,
               gorsel_model_secim: str = "", unlu_modu: bool = False) -> dict:
    """Tam hat. mod: 'animasyon'|'documentary'. stil_yol: referans stil gorseli (opsiyonel).
    sure_dk: hedef sure (hikaye maks 60, digerleri maks 14). gecis_acik/zoom_acik: kullanicinin tercihi.
    profil_id: KANAL PROFILI — verilirse karakter/capa/kilitler profilden gelir ve tum
    videolar ayni gorunur (evergreen kanal tutarliligi). Footage/Magnific plana gore OTOMATIK."""
    def bildir(mesaj, yuzde):
        if ilerle:
            ilerle(mesaj, yuzde)

    # ── KANAL PROFILI: kalici karakter + capa + kilitler (videolar ARASI tutarlilik) ──
    kanal = profil_oku(profil_id) if profil_id else {}
    # ⚠ 1 Agu 2026 DUZELTMESI — profil ARTIK kullanicinin secimini EZMEZ.
    # Onceki hali: `mod = kanal.get("tur") or mod` -> kullanici "Ani Defteri" seciyor ama
    # profilde kayitli "hikaye-whatif" sessizce devreye giriyordu. Ustune profilin DONMUS
    # capasi her sahneye ESKI karakteri dayatiyordu; yeni yuklenen referans hic kullanilmiyordu.
    # Kural: BU VIDEODAKI SECIM HER ZAMAN KAZANIR. Profil sadece BOS birakilani doldurur.
    # SAHNE REFERANSI: karakter+stil+palet+isik hepsi ayni karelerden gelir.
    sahne_ref = [y for y in (sahne_ref or []) if y and os.path.exists(y)][:4]
    if sahne_ref:
        # Gorsel referans olarak ILK kareyi kullan (kanon ondan uretilir)
        kar_yol = kar_yol if (kar_yol and os.path.exists(kar_yol)) else sahne_ref[0]
        stil_yol = stil_yol if (stil_yol and os.path.exists(stil_yol)) else sahne_ref[0]
    sr = {}                     # sahne referansi analizi (asagida doldurulur)
    stil_kunye_txt_on = ""
    yeni_karakter = bool(kar_yol and os.path.exists(kar_yol)) or bool(sahne_ref)
    yeni_stil_gorseli = bool(stil_yol and os.path.exists(stil_yol)) or bool(sahne_ref)
    if kanal:
        if not mod:
            mod = kanal.get("tur") or mod
        if not edit_id:
            edit_id = kanal.get("edit") or edit_id
        if kanal.get("edit") and edit_id and kanal["edit"] != edit_id:
            print(f"  NOT: profil '{profil_id}' stili '{kanal['edit']}' ama bu videoda "
                  f"'{edit_id}' secilmis -> SECIM kazanir", file=sys.stderr)

    # ⚠ IS KUNYESI — her isin BASINDA ne aldigini tek satirda logla.
    # 3 Agu 2026'da "referanslar neden uygulanmadi" sorusunu cevaplamak icin log kazmak
    # zorunda kaldik. Artik ilk satirda gorunur: mod, stil, kac referans, profil.
    print(f"  ┌ IS KUNYESI {is_adi}\n"
          f"  │ mod={mod} edit={edit_id} sure={sure_dk}dk profil={profil_id or '-'}\n"
          f"  │ sahne_ref={len(sahne_ref or [])} karakter={'VAR' if (kar_yol and os.path.exists(kar_yol)) else 'yok'} "
          f"stil_gorseli={'VAR' if (stil_yol and os.path.exists(stil_yol)) else 'yok'}\n"
          f"  └ palet={palet or '-'} arkaplan={arkaplan or '-'} isik={isik or '-'} ses={ses_secim or '-'}",
          file=sys.stderr)

    prof = profil_coz(mod, edit_id)
    gorsel_ek = prof["gorsel_ek"]
    # Kullanici KARAKTER YUKLEMEDIYSE profilin varsayilan kahraman tarifini ekle.
    # Yuklediyse EKLEME — aksi halde onun karakteriyle (or. tilki) CAKISIR.
    if prof.get("varsayilan_karakter") and not (kar_yol and os.path.exists(kar_yol)):
        gorsel_ek = f"{gorsel_ek}. {prof['varsayilan_karakter']}"
    # ── RENK PALETI: bu videoda secilmediyse kanal profilininki (kanal genelinde ayni renk) ──
    # Oncelik: bu videodaki secim > kanal profili > stilin kendi dogal paleti ("Otomatik").
    if not palet and kanal:
        palet, palet_ozel = kanal.get("palet", ""), kanal.get("palet_ozel", "")
    if not palet:
        palet = prof.get("palet", "")
    pal_ek = palet_prompt(palet, palet_ozel)
    if pal_ek:
        gorsel_ek = gorsel_ek + "." + pal_ek
        print(f"  palet kilidi: {palet or 'ozel'} -> {palet_renkleri(palet, palet_ozel)}",
              file=sys.stderr)
    # Kompozisyon/cerceveleme kurali (animasyonda ortam basrol, karakter cerceveyi doldurmaz)
    cerceve_ek = prof.get("cerceve", "")
    # ── ARKA PLAN: bu videoda secilmediyse kanal profilininki. EN SONA eklenir ki
    #    stilin yogunluk dayatmasini ezebilsin (sade-beyaz secilirse "her yer dolsun" susar).
    if not arkaplan and kanal:
        arkaplan = kanal.get("arkaplan", "")
    ap_ek = arkaplan_prompt(arkaplan)
    if ap_ek:
        cerceve_ek = cerceve_ek + ap_ek
        print(f"  arka plan: {arkaplan}", file=sys.stderr)
    # ISIK EN SONA: hem stilin hem arka planin karanlik egilimini ezmesi gerekiyor.
    if not isik and kanal:
        isik = kanal.get("isik", "")
    if not isik:
        isik = VARSAYILAN_ISIK          # varsayilan PARLAK (olculen hedef 162/255)
    is_ek = isik_prompt(isik)
    if is_ek:
        cerceve_ek = cerceve_ek + is_ek
        print(f"  isik duzeyi: {isik}", file=sys.stderr)
    motion = prof["motion"] if gecis_acik else "kesme"   # gecis kapali -> sade kesme
    overlay_stil = prof["overlay"]
    # Altyazi: profil varsayilani, ama kullanici acikca ac/kapat diyebilir (animasyonda da).
    # altyazi_ac: "" = profil karari, "1"/"orta"/"yogun" = ac, "0"/"yok" = kapat
    altyazi_stil = prof.get("altyazi", "orta")
    if altyazi_ac in ("0", "yok", "kapali"):
        altyazi_stil = "yok"
    elif altyazi_ac in ("1", "acik", "orta"):
        altyazi_stil = "orta"
    elif altyazi_ac == "yogun":
        altyazi_stil = "yogun"
    if kanal and not altyazi_sablon:
        altyazi_sablon = kanal.get("altyazi_sablon", "")   # kanal profili sablonu hatirlar
    mag_profil = prof.get("mag")
    footage_acik = prof.get("footage_pct", 0) > 0
    # Maliyet/kalite: animasyon (duz vektor) ucuz mini, documentary (foto-gercekci) gpt-image-2
    gorsel_model = GORSEL_MODEL_ANIM if mod == "animasyon" else GORSEL_MODEL_DOC
    # Kullanici Studyo'dan kalite sectiyse o kazanir (Standart=mini / Yuksek=gpt-image-2).
    # ISTISNA — HIKAYE: mini model ANIMASYON icin ayarli; gercekci hikaye sahnelerine cizim/
    # animasyon gorunumu sizdiriyor (4 Agu testinde yer yer karisik tema cikti). Hikaye HER
    # ZAMAN foto-gercekci modelle calisir, kalite secimi yok sayilir.
    if mod != "hikaye" and gorsel_model_secim in ("gpt-image-1-mini", "gpt-image-2", "gpt-image-1"):
        gorsel_model = gorsel_model_secim
        print(f"  gorsel modeli (kullanici secimi): {gorsel_model}", file=sys.stderr)
    elif mod == "hikaye" and gorsel_model_secim and gorsel_model_secim != GORSEL_MODEL_DOC:
        print(f"  hikaye modu: '{gorsel_model_secim}' yok sayildi -> {GORSEL_MODEL_DOC} "
              "(gercekcilik korunur)", file=sys.stderr)
    yt_once = True
    # Sure tavani: hikaye kanali 60 dk (uzun hikaye formati), diger turler 14 dk.
    # 60 dk hikaye (8sn sahne, paralel gorsel, 10 cekirdek render) ~2-2.5 saat, ~$40 gorsel.
    tavan_dk = 60.0 if mod == "hikaye" else 14.0
    sure_dk = max(0.3, min(tavan_dk, float(sure_dk or 2)))

    # ── Karakter + STIL kilitleri ──
    # PROFIL VARSA: kayitli referans/kilitler kullanilir -> hem videolar arasi TUTARLILIK,
    # hem her videoda 2 vision cagrisi tasarrufu (daha hizli + daha ucuz).
    # ⚠ Profilin kayitli kunyesi ESKI referansi tarif eder. Bu videoda YENI bir gorsel
    # yuklendiyse onu kullanma — yoksa yeni referans analiz bile edilmez ve cikti eski
    # karaktere benzemeye devam eder (kullanicinin 1 Agu 2026'da bildirdigi hata).
    kar_kilit = kanal.get("kar_kilit", "") if (kanal and not yeni_karakter) else ""
    stil_kilit = kanal.get("stil_kilit", "") if (kanal and not yeni_stil_gorseli) else ""
    if kanal:
        # kullanici bu videoda ozel gorsel yuklemediyse profilinkini kullan
        if not (kar_yol and os.path.exists(kar_yol)) and kanal.get("karakter_yol"):
            kar_yol = kanal["karakter_yol"]
        if not (stil_yol and os.path.exists(stil_yol)) and kanal.get("stil_yol"):
            stil_yol = kanal["stil_yol"]
    kunye_guven = None
    sr = {}
    if sahne_ref:
        bildir(f"{len(sahne_ref)} referans karesi analiz ediliyor (karakter+stil+palet+ışık)...", 3)
        sr = sahne_referansi(sahne_ref, bildir)
        if sr:
            kar_kilit = kunye_metni(sr.get("kimlik") or {}) or kar_kilit
            kunye_guven = (sr.get("kimlik") or {}).get("_guven")
            sk_txt = stil_kunye_metni(sr.get("stil") or {})
            if sk_txt:
                stil_kunye_txt_on = sk_txt
            else:
                stil_kunye_txt_on = ""
            # Palet: referansin OLCULEN renkleri (kullanici ayrica secmediyse)
            if sr.get("palet_hex") and not palet_renkleri(palet, palet_ozel):
                palet, palet_ozel = "ozel", ",".join(sr["palet_hex"])
            print(f"  SAHNE REFERANSI: {sr.get('kare_sayisi')} kare | olcum={sr.get('olcum')} "
                  f"| palet={sr.get('palet_hex')}", file=sys.stderr)
    if not kar_kilit and kar_yol and os.path.exists(kar_yol):
        # COK ASAMALI ANALIZ: palet olcumu + 2 bagimsiz vision okumasi + kod uzlasisi
        bildir("Karakter derin analiz ediliyor (çok aşamalı)...", 3)
        k = kimlik_kunyesi(kar_yol)
        kar_kilit = kunye_metni(k)
        kunye_guven = k.get("_guven")
        if kunye_guven is not None and kunye_guven < 0.6:
            print(f"  UYARI: kunye guveni dusuk ({kunye_guven}) — referans gorsel net degil",
                  file=sys.stderr)
        if not kar_kilit:      # analiz hic sonuc vermezse eski tek-gecisli yonteme dus
            kar_kilit = karakter_analiz(kar_yol)
    # ── STIL GORSELI: cok asamali analiz + DAHILI SANAT YONERGESININ YERINE GECER ──
    # Neden yerine gecer, yanina degil: secili stilin blogu 150-250 kelime, tek cumlelik
    # stil kilidi yaninda erirdi -> kullanici stil yukluyor ama cikti dahili stile benziyordu.
    # Iki rakip sanat yonergesi = sahneler arasi salinim (renk kilidi dersinin aynisi).
    # Kompozisyon (cerceve + sahne sozlesmesi) DEGISMEZ: stil GORUNUSU, sozlesme YAPIYI belirler.
    stil_kunye_txt = kanal.get("stil_kunye", "") if (kanal and not yeni_stil_gorseli) else ""
    if sr and stil_kunye_txt_on:
        stil_kunye_txt = stil_kunye_txt_on      # sahne referansindan gelen zengin stil tarifi
    # OLCULEN ISIK: hazir kademeden daha kesin -> onun YERINE gecer. (sr burada hazir;
    # yukaridaki cerceve blogunda henuz bos oldugu icin burada uygulaniyor.)
    olcum_hedef = (sr.get("olcum") or {}) if sr else {}
    if sr and sr.get("olcum"):
        olculen_ek = olcum_isik_prompt(sr["olcum"])
        if olculen_ek:
            if is_ek and is_ek in cerceve_ek:
                cerceve_ek = cerceve_ek.replace(is_ek, olculen_ek)
            else:
                cerceve_ek += olculen_ek
            print(f"  isik REFERANSTAN OLCULDU: {sr['olcum']}", file=sys.stderr)
    stil_guven = None
    if stil_yol and os.path.exists(stil_yol) and not stil_kunye_txt:
        bildir("Stil görseli derin analiz ediliyor (çok aşamalı)...", 4)
        sk = stil_kunyesi(stil_yol)
        stil_guven = sk.get("_guven")
        stil_kunye_txt = stil_kunye_metni(sk)
        # Palet secilmemisse referansin OLCULEN renkleri paleti olsun
        if stil_kunye_txt and not palet_renkleri(palet, palet_ozel):
            olculen = [c["hex"] for c in (sk.get("_palet") or [])][:6]
            if len(olculen) >= 2:
                palet, palet_ozel = "ozel", ",".join(olculen)
                print(f"  stil gorselinden olculen palet: {olculen}", file=sys.stderr)
        if stil_guven is not None and stil_guven < 0.5:
            print(f"  UYARI: stil kunyesi guveni dusuk ({stil_guven}) — gorsel net degil",
                  file=sys.stderr)
    if stil_kunye_txt:
        # Dahili sanat yonergesini SOK, geri kalanini (varsayilan karakter + palet) koru
        taban = prof["gorsel_ek"]
        gorsel_ek = (stil_kunye_txt + gorsel_ek[len(taban):]) if gorsel_ek.startswith(taban) \
            else stil_kunye_txt
        # Palet stil gorselinden geldiyse simdi ekle (yukarida hesaplanmisti)
        yeni_pal = palet_prompt(palet, palet_ozel)
        if yeni_pal and yeni_pal not in gorsel_ek:
            gorsel_ek += "." + yeni_pal
        stil_kilit = stil_kunye_txt          # capa ve sahneler ayni zengin tarifi kullansin
        print(f"  STIL GORSELI devrede (guven={stil_guven}) — dahili sanat yonergesi devre disi",
              file=sys.stderr)
    elif not stil_kilit and stil_yol and os.path.exists(stil_yol):
        stil_kilit = stil_analiz(stil_yol)   # kunye cikmadiysa eski tek-cumlelik yonteme dus
    # Kilitleri profile YAZ (bir kez uretilir, sonraki tum videolarda hazir gelir)
    if kanal and (kar_kilit or stil_kilit or stil_kunye_txt):
        try:
            profil_yaz(profil_id, {"kar_kilit": kar_kilit or None,
                                   "stil_kilit": stil_kilit or None,
                                   "stil_kunye": stil_kunye_txt or None,
                                   "stil_guven": stil_guven,
                                   "kunye_guven": kunye_guven})
        except Exception:
            pass

    # ⚠ KELIME BUTCESI PLANDAN ONCE (11 Agu 2026'da olcerek bulundu).
    # Onceden butce plan URETILDIKTEN SONRA duzeltiliyordu; yani plan her zaman
    # profilin varsayilan kelime sayisi ve wpm=150 ile yazilıyordu. Olcum:
    #   log "Plan 41 sn'lik (102 kelime / butce 150)" -> butce 150 = wpm 150
    #   gercek ses hizi 212 wpm -> istenen 60 sn yerine 39 sn video
    # Butce plandan once hesaplaninca plan dogru uzunlukta yaziyor.
    prof = dict(prof)
    _eski_kel_on = prof.get("kelime")
    prof["kelime"] = kelime_butcesi(prof, ses_secim)      # prof["_wpm"] de burada set olur
    if prof["kelime"] != _eski_kel_on:
        print(f"  kelime butcesi (plan oncesi): {_eski_kel_on} -> {prof['kelime']} "
              f"(wpm={prof.get('_wpm'):.0f}, hedef {prof.get('sahne_sn')} sn)", file=sys.stderr)

    # ═══════ ARASTIRMA (Faz H, 12 Agu 2026) — ARTIK GERCEKTEN CALISIYOR ═══════
    # ⚠ Faz H envanteri: `webapp/arastirma/` paketi Faz A'da yazilmisti ama bu
    # dosya onu HIC import etmiyordu. Ana sayfadaki "Arastirma ... tek akista"
    # iddiasi karsiliksizdi. Kopru burada devreye giriyor:
    #   konu -> web arastirmasi -> bagimsiz kaynak dogrulamasi -> OLGU LISTESI
    # ve olgular plan promptuna giriyor, yani anlatim dogrulanmis olgulara
    # DAYANIYOR. Yalnizca `documentary` turunde; animasyon/hikaye kurgudur.
    #
    # ⚠ HAT ASLA COKMEZ: kopru istisna firlatmaz. Anahtar yok / ag coktu /
    # tavan doldu -> `arastirma_sonuc.dususler` doluyor ve bu is sozlugune,
    # oradan arayuze cikiyor. SESSIZ DUSUS YOK.
    story, arastirma_sonuc = arastirma_kopru.arastir_ve_zenginlestir(
        story, mod=mod, is_adi=is_adi, cikti_dizin=CIKTI_DIR, bildir=bildir)

    bildir("Hikaye sahnelere bölünüyor...", 5)
    # UNLU MODU: yalniz hikaye + GEMINI_KEY varken aktif (Gemini benzerlige tolerans).
    # Anahtar yoksa sessizce normal moda duser (OpenAI isimli talebi reddeder cunku).
    unlu_aktif = bool(unlu_modu and mod == "hikaye" and (XAI_KEY or GEMINI_KEY))
    # Motor onceligi: Grok (benzerlikte en toleransli) > Gemini
    unlu_motor = "grok" if XAI_KEY else "gemini"
    if unlu_modu and not unlu_aktif:
        print("  UNLU modu istendi ama XAI/GEMINI anahtari yok -> tarif-bazli normal mod", file=sys.stderr)
    if unlu_aktif:
        print(f"  UNLU MODU AKTIF: gercek isimler + {unlu_motor} gorsel yolu", file=sys.stderr)
    plan = uzun_plan(story, prof, sure_dk, unlu=unlu_aktif)
    scenes = plan["scenes"]
    # ── METIN DERIN ANALIZI: her satirin anlatim islevi -> sahne bazinda kurgu ──
    # Basarisiz olursa bos liste doner ve asagida eski mekanik atamaya dusulur.
    bildir("Metin kurgu açısından analiz ediliyor...", 6)
    try:
        kurgu_analiz = metin_islev_analizi(scenes)
    except BakiyeHatasi:
        raise
    except Exception:
        kurgu_analiz = []

    ses = ses_coz(plan)   # dogrulanmis, dile uygun ses (en-US-on-Turkce ve halusinasyon fix)
    # SES SECIMI: bu videoda secilmediyse kanal profilininki (kanal genelinde ayni anlatici)
    if not ses_secim and kanal:
        ses_secim = kanal.get("ses", "")
    ses_ayar = ses_ayari(ses_secim, ses)
    # Kelime butcesini secilen sesin GERCEK okuma hizina gore yeniden hesapla
    _eski_kel = prof.get("kelime")
    prof = dict(prof)
    prof["kelime"] = kelime_butcesi(prof, ses_secim)
    if prof["kelime"] != _eski_kel:
        print(f"  kelime butcesi: {_eski_kel} -> {prof['kelime']} "
              f"(ses={ses_secim or 'otomatik'}, hedef {prof.get('sahne_sn')} sn)", file=sys.stderr)
    if ses_ayar.get("motor") == "openai":
        print(f"  ses: OpenAI {ses_ayar['ses']} ({ses_secim})", file=sys.stderr)
    elif ses_ayar.get("ses"):
        ses = ses_ayar["ses"]

    is_dizini = os.path.join(PUBLIC, "isler", is_adi)
    os.makedirs(is_dizini, exist_ok=True)
    panlar = ["right", "left", "top", "bottom"]
    props_sahneler = []
    toplam = len(scenes)
    # ── FAZ I-8: DOGRULANMIS OLGU -> SAHNE BAGI ──
    # ⚠ YALNIZCA arastirma GERCEKTEN kostuysa ve senaryoya girebilen iddia
    # varsa calisir. Arastirma kapali/basarisizsa `olgular` bos kalir, hicbir
    # sahne degistirilmez ve hat ESKISIYLE BIT-BIT ayni surer.
    # ⚠ UYDURMA fact_id YOK: eslesmeyen sahne kimlik ALMAZ, bosluk GORUNUR.
    _fact_rapor = None
    if getattr(arastirma_sonuc, "calisti", False):
        _olgular = list(getattr(arastirma_sonuc, "olgular", None) or [])
        if _olgular:
            _fact_rapor = arastirma_kopru.fact_bagla(scenes, _olgular)
            print(f"  OLGU BAGI: {_fact_rapor['baglanan']}/"
                  f"{_fact_rapor['hedef']} footage sahnesi dogrulanmis iddiaya "
                  f"baglandi (%{_fact_rapor['kapsam_pct']}), "
                  f"{len(_fact_rapor['bosluklar'])} kapsam boslugu",
                  file=sys.stderr)
            # ⚠ FAZ Y-10 / Y10-HAVUZ-YETERSIZ — ERKEN VE FAIL-CLOSED DURUS.
            # OLCULEN ISRAF (is job_1786792477656_y71414_df7e2a):
            #   ARASTIRMA: 1/11 olgu dogrulandi, 9 kaynak
            #   ... ~10 dk render ...
            #   TESLIM: False | KABUL-YOK:...:FACT-BAGLANTI-YOK
            # Havuz yetersizligi BURADA (medya/TTS/render'dan ONCE) bellidir;
            # buna ragmen hat butun medyayi indirip TTS uretip render ediyor
            # ve ancak teslim kapisinda dusuyordu.
            # ⚠ FACT UYDURULMAZ, KAPI GEVSETILMEZ: `FACT-BAGLANTI-YOK` fail
            # olarak KALIR (qa_on). Bu kapi yalnizca kaybi ERKENE ceker ve
            # NEDENINI stabil kodla soyler.
            _hedef_n = int(_fact_rapor.get("hedef") or 0)
            _bagli_n = int(_fact_rapor.get("baglanan") or 0)
            if _hedef_n > 0:
                _kapsam = _bagli_n / float(_hedef_n)
                if _kapsam < FACT_KAPSAM_ESIGI:
                    raise RuntimeError(
                        f"ARASTIRMA-HAVUZ-YETERSIZ: {_bagli_n}/{_hedef_n} "
                        f"sahne dogrulanmis olguya baglanabildi "
                        f"(%{_kapsam * 100:.0f} < %{FACT_KAPSAM_ESIGI * 100:.0f}). "
                        f"Dogrulanmis olgu havuzu {len(_olgular)} iddia. "
                        f"Her cekim dogrulanmis bir olguya baglanmali; "
                        f"konu daha somut/olgusal yazilmali ya da arastirma "
                        f"kaynaklari genisletilmeli.")
    # ── FAZ I-2d: GORSEL IMZA KAYNAGI ──
    # Bilesik profil varsa efekt/gecis imzasi ONDAN turetilir. Eski stil
    # kimliklerinde `_profil` blogu YOKTUR -> `None` kalir ve `efekt_ata` /
    # `gecis_imza_sec` eski tablolariyla BIT-BIT ayni calisir.
    _gorsel_ek = profil_ek_oku(prof) or None
    _gorsel_imza = bilesik_gorsel_imza(_gorsel_ek) if _gorsel_ek else None
    # ── FAZ I-6: MEDYA AVCISI (OPT-IN, VARSAYILAN KAPALI) ──
    # ⚠ `_is_ayar` DAHILI kanal profili sozlugudur; `/api/generate`in 22 alani
    # buraya ULASMAZ. Bayrak kapaliysa `_avci_acik` False kalir ve asagidaki
    # medya yolu BUGUNKUYLE BIREBIR ayni calisir.
    _is_ayar = kanal if isinstance(kanal, dict) else None
    _avci_acik, _avci_gerekce = medya_kopru.acik_mi(_is_ayar)
    _avci_konsept, _avci_yerler, _avci_butce = None, [], None
    if _avci_acik:
        # ⚠ FAZ I-7: HER IS KENDI butce nesnesini kurar. Modul duzeyinde
        # paylasilan sayac YOK; ayni surecte iki is kosarsa sayaclar
        # BIRBIRINE KARISMAZ (test kilitliyor).
        _avci_butce = medya_kopru.is_butcesi_kur(is_adi)
        try:
            import taksonomi as _tx
            _avci_konsept = _tx.siniflandir(story or "")
        except Exception as e:
            print(f"  avci konsepti cozulemedi: {type(e).__name__}",
                  file=sys.stderr)
        _bo = _avci_butce.ozet()
        print(f"  MEDYA AVCISI ACIK ({_avci_gerekce}); konsept="
              f"{(_avci_konsept or {}).get('yol') or 'yok'}; butce="
              f"${_bo['maks_usd']:.2f} / {_bo['maks_istek']} istek / "
              f"{_bo['maks_sure_sn']:.0f} sn / {_bo['maks_kare']} kare",
              file=sys.stderr)
    if _gorsel_imza:
        _ef_adlari = [e["ad"] for e in _gorsel_imza["efektler"]] or ["yok"]
        _gz = _gorsel_imza["gecis_imza"] or "yok"
        if _gorsel_imza["gecis_imza"]:
            _gz += f" %{_gorsel_imza['gecis_oran'] * 100:.0f}"
        print(f"  GORSEL IMZA (bilesik): efekt={_ef_adlari} gecis={_gz}",
              file=sys.stderr)
        for _g in _gorsel_imza["gerekce"]:
            print(f"    · {_g}", file=sys.stderr)
    # Gorsel capa: normalde ilk uretilen sahne sonrakilere kilit olur (video ICI tutarlilik).
    # PROFIL KILITLIYSE capa ta bastan gelir -> ILK SAHNE DAHIL her kare kanalin sabit
    # gorunumune kilitlenir (videolar ARASI tutarlilik). Kanal kimligi budur.
    capa_yol = kanal.get("capa_yol", "") if kanal else ""
    # ⚠ 1 Agu 2026 DUZELTMESI — YENI REFERANS YUKLENDIYSE DONMUS CAPA YOK SAYILIR.
    # Onceki hali: profilin capasi kosulsuz kullaniliyordu. Kullanici yeni bir karakter
    # (ya da stil gorseli) yukleyip yeni bir stil secse bile ESKI donmus kare her sahneye
    # referans olarak gidiyordu -> cikti hep eski karaktere benziyordu ve yeni referans
    # HIC kullanilmiyordu. Yeni referans = yeni kanon niyeti demektir; eskiyi birak.
    if capa_yol and (yeni_karakter or yeni_stil_gorseli):
        print(f"  DONMUS CAPA YOK SAYILDI: bu videoda yeni referans yuklendi "
              f"(karakter={yeni_karakter}, stil={yeni_stil_gorseli}) -> yeni kanon uretilecek",
              file=sys.stderr)
        capa_yol = ""
    capa_profilden = bool(capa_yol)
    # TEMIZ CAPA: kullanici karakter verdiyse ve henuz kanon yoksa, sahnelerden ONCE notr/
    # eller-bos bir kanon karesi uret. Boylece referansin pozu-nesnesi sahnelere BULASMAZ ve
    # tum sahneler ayni temiz kareye kilitlenir. Sahne 1'i capa yapmak sapmayi bilesikliyordu.
    if not capa_yol and kar_yol and os.path.exists(kar_yol):
        bildir("Karakter kanonu (temiz çapa) üretiliyor...", 5)
        kanon = os.path.join(is_dizini, "_kanon.png")
        try:
            if capa_uret(kar_yol, kanon, kar_kilit, stil_kilit, stil_yol, gorsel_model):
                capa_yol = kanon
                capa_profilden = True     # DONDURULDU: sahne ciktisiyla guncellenmez
                if kanal:
                    profil_capa_kilitle(profil_id, kanon)
                    print(f"  profil '{profil_id}' TEMIZ capasi kilitlendi", file=sys.stderr)
        except BakiyeHatasi:
            raise
        except Exception as e:
            print(f"  capa uretilemedi, sahne-1 capasina dusuluyor: {str(e)[:120]}",
                  file=sys.stderr)
    kumulatif_sn = 0.0   # hikaye modu: acilis bolumu takibi icin toplam sure
    # Hareketli acilis suresi: kullanici secimi (acilis_dk, 0=kapali) > varsayilan env
    acilis_sn = float(acilis_dk) * 60 if acilis_dk is not None else HIKAYE_ACILIS_SN

    # ═══ SAHNE URETIMI — 3 FAZ (paralel) ═══
    # Eski hat sahneleri TEKER TEKER uretiyordu (gorsel + bekleme + TTS ust uste eklenirdi;
    # 300 sahne ~2 saat). Yeni hat: (A) capa sahnesi sirali, (B) kalan gorseller PARALEL
    # (GORSEL_PARALEL isci), (C) TTS paralel + montaj SIRALI. 429 gelirse referansli_gorsel
    # zaten Retry-After'a uyuyor -> paralellik hiz limitine karsi kendi kendini frenler.
    bakiye_bitti = False   # bakiye/limit doldu mu (elde olanla kurtarma icin)
    uretim_durdu = False   # toplu basarisizlikta yeni istek acilmasin (para yanmasin)
    gorsel_bekle = float(os.environ.get("GORSEL_BEKLE", "5"))
    paralel = max(1, int(os.environ.get("GORSEL_PARALEL", "4")))

    islenecek = []   # (i, n, sahne, metin, overlay) — bos voiceover'lar elenmis, sira sabit
    for i, s in enumerate(scenes):
        metin = str(s.get("voiceover", "")).strip()   # model sayi/null verirse .strip() patlamasin
        if not metin:
            continue
        islenecek.append((i, i + 1, s, metin,
                          str(s.get("overlay", "")).strip() if overlay_stil != "yok" else ""))

    sonuc_medya = {}          # n -> (tur, medya). Basarisiz sahne burada olmaz.
    sayac_kilit = threading.Lock()
    tamamlanan = [0]

    # ── SORA GERCEK VIDEO ADAYLARI ──
    # Kullanici "Gercek video (Sora)" actiysa: ACILIS suresine dusen ilk sahnelerin
    # gorselleri Sora'ya referans verilip GERCEK video klibe cevrilir (~$0.8/sahne).
    # Klip tavani SORA_KLIP_MAKS (maliyet sigortasi). Basarisiz klip -> efektli fotograf.
    sora_adaylari = set()
    if sora_acik and mod == "hikaye" and acilis_sn > 0:
        adet = int(min(float(os.environ.get("SORA_KLIP_MAKS", "20")),
                       max(0, round(acilis_sn / prof["sahne_sn"]))))
        for sira, (i, n, s, metin, ov) in enumerate(islenecek):
            if sira < adet:
                sora_adaylari.add(n)
        if sora_adaylari:
            print(f"  SORA acik: {len(sora_adaylari)} acilis sahnesi videolastirilacak",
                  file=sys.stderr)

    # Klip tekrarini onlemek icin gecmis her iste sifirlanir (kaynak.py modul duzeyinde
    # tutuyor; sifirlanmazsa onceki videonun klipleri bu videoda da "kullanildi" sayilir).
    kaynak.klip_gecmisi_sifirla()
    # VIDEONUN yerini metinden bir kez tespit et: plan bazi sahnelerin footage
    # sorgusuna ulkeyi yazmayi unutuyor ve o sahnelerde yer kapisi kapaniyor.
    # 11 Agu olcumu: Tokyo metnine tropik ada ve Filipinler ic mekani bu bosluktan girdi.
    try:
        kaynak.yer_baglami_kur(story)
    except Exception as e:
        print(f"  yer baglami kurulamadi: {str(e)[:80]}", file=sys.stderr)
    # ⚠ FAZ H — BIYOM KAPISI BAGLAMI. `yer_baglami_kur` YER_TAKMA_AD'daki 19
    # ulkeyle sinirli; tablonun disindaki yerlerde (South Georgia, Antarktika,
    # Elephant Island...) hicbir kapi calismiyordu. Shackleton pilotunda tam
    # bu bosluktan tropik sahil klibi "GUNEY GEORGIA" diye gecti.
    # Biyom kapisi ulke tablosundan BAGIMSIZ; genel konu metnini burada alir.
    try:
        # Planin ozeti + kullanici metni: ikisi birlikte iklim kusagini verir.
        _baglam = f"{story}\n{plan.get('ozet') or ''}"
        kaynak.video_baglami_kur(_baglam)
    except Exception as e:
        print(f"  biyom baglami kurulamadi: {str(e)[:80]}", file=sys.stderr)

    def _sahne_medya(n, s):
        """Tek sahnenin medyasini (footage / AI gorsel / Sora video) uretir. Thread'de kosar."""
        nonlocal bakiye_bitti, uretim_durdu
        if bakiye_bitti or uretim_durdu:
            return None
        # ⚠ FAZ R-1d-b: avci basarisiz olursa nedeni TUTULUR ama bosluk
        # HEMEN yazilmaz — gercek medya yolu bu sahneyi kurtarabilir.
        # ⚠ FAZ R-1d-d: yardimcilar footage blogunun DISINA alindi. Icerde
        # tanimliyken URETILEN GORSEL yolundan cagrilamiyorlardi (o yol
        # footage `if`inin DISINDA) — non-footage sahne NameError alirdi.
        _avci_bosluk_neden = ""

        def _kopru_yaz(_yol):
            """Gercek medya yolundaki secimi avci butcesine kopruler.

            ⚠ FAIL-CLOSED: provenans/lisans/kare dogrulamasi eksikse
            kayit YAPILMAZ; sahne kapsam BOSLUGU olarak yazilir.
            """
            if _avci_butce is None:
                return
            _pv = kaynak.stok_provenans_al(_yol)
            _kp = medya_kopru.stok_secimi_kaydet(
                _avci_butce, hedef_yol=_yol,
                scene_id=str(s.get("scene_id") or f"s{n:03d}"),
                provenans=_pv, fact_id=str(s.get("fact_id") or ""),
                sahne_amaci=str(s.get("sahne_amaci") or ""),
                sorgu=str(s.get("footage_sorgu") or "").strip())
            if _kp["kaydedildi"]:
                print(f"  sahne {n}: KOPRU -> butceye secim yazildi "
                      f"({_pv.get('saglayici')}/{_pv.get('lisans')})",
                      file=sys.stderr)
            else:
                _avci_butce.bosluk_ekle(
                    str(s.get("scene_id") or f"s{n:03d}"),
                    f"stok koprusu: {_kp['neden']}")

        def _bosluk_yaz(_neden):
            """Footage yolundan CIKARKEN kapsam boslugunu yaz."""
            if _avci_butce is not None:
                _avci_butce.bosluk_ekle(
                    str(s.get("scene_id") or f"s{n:03d}"),
                    _avci_bosluk_neden or _neden)

        # 1) Footage sahnesi mi?
        if footage_acik and str(s.get("kaynak")) == "footage" and str(s.get("footage_sorgu", "")).strip():
            vyol_full = os.path.join(PUBLIC, "isler", is_adi, f"sahne_{n}.mp4")
            # ── FAZ I-6: MEDYA AVCISI (OPT-IN, VARSAYILAN KAPALI) ──
            # ⚠ Kapaliyken bu blok hicbir sey yapmaz ve asagidaki MEVCUT yol
            # aynen calisir. Acikken bile basarisiz olursa yine eski yola
            # dusulur — uretim yolu HICBIR DURUMDA bozulmaz.
            if _avci_acik:
                _av = medya_kopru.sahne_medyasi(
                    sorgu=s["footage_sorgu"].strip(), hedef_yol=vyol_full,
                    sahne_amaci=str(s.get("sahne_amaci") or ""),
                    iddia_metni=str(s.get("iddia_metni") or s.get("anlatim") or ""),
                    fact_id=str(s.get("fact_id") or ""),
                    scene_id=str(s.get("scene_id") or f"s{n:03d}"),
                    konsept=_avci_konsept, bilinen_yerler=_avci_yerler,
                    konu=str(story or "")[:120],
                    yer_terim=kaynak._etkin_yer(s["footage_sorgu"].strip()),
                    istek=kaynak.avci_istek, kare_dogrula=kaynak._kare_dogrula,
                    is_ayar=_is_ayar, butce=_avci_butce)
                if _av["ok"]:
                    if _av.get("atif"):
                        s["kaynakYazi"] = _av["atif"][:80]
                    print(f"  sahne {n}: AVCI klibi "
                          f"{_av['aday'].get('saglayici')}/"
                          f"{_av['aday'].get('lisans')}", file=sys.stderr)
                    return ("video", f"isler/{is_adi}/sahne_{n}.mp4")
                # Basarisizlik SESSIZ degil; sebep dususlere yaziliyor.
                # ⚠ FAZ R-1d-b: kapsam boslugu ARTIK HEMEN yazilmiyor.
                # Eskiden avci aday veremeyince bosluk kaydediliyordu; ama
                # gercek medya yolu (`footage_getir`) hemen ardindan
                # LISANSLI + KARE DOGRULANMIS bir klip getirebiliyor. O
                # durumda "kapsam boslugu" YANLIS bir iddiadir. Bosluk artik
                # YALNIZCA gercek yol da basarisiz olursa yaziliyor.
                _avci_bosluk_neden = _av.get("neden") or "avci aday veremedi"
            if kaynak.footage_getir(s["footage_sorgu"].strip(), vyol_full, yt_once=yt_once):
                # CC klip geldiyse ekrana kucuk kaynak yazisi — lisans ATIF ISTIYOR.
                atif = kaynak.atif_al(vyol_full)
                if atif.get("kanal"):
                    s["kaynakYazi"] = atif["kanal"]
                # ── FAZ R-1d-b: GERCEK MEDYA YOLU -> AVCI BUTCESI KOPRUSU ──
                # ⚠ OLCULEN KUSUR (R-1d-a staging): uretimde medya BU yoldan
                # geliyor ama secim butceye HIC yazilmiyordu; `manifest_kur`
                # bos manifest uretiyor, `edit_kopru.plan_kur` denenmiyor ve
                # PRE-QA HIC KOSMUYORDU (`edit_plani=MEDYA-YOK`) -> teslim
                # zinciri `pre_qa` kanitsiz kalip videoyu REDDEDIYORDU.
                _kopru_yaz(vyol_full)
                return ("video", f"isler/{is_adi}/sahne_{n}.mp4")
            # 1b) GORSEL YASAK STILLERDE (belgesel) AI gorsele DUSMUYORUZ.
            # Kullanici karari 11 Agu 2026: "belgesel stilinde gorsel kullanma, 0 gorsel".
            # Onun yerine ulkeye capali genel klip denenir; o da olmazsa klip tekrarina
            # izin verilir (ayni ulkenin tekrar eden klibi, AI gorselden iyidir).
            if prof.get("gorsel_yasak"):
                for yedek_sorgu in kaynak.genel_yedek_sorgular(s["footage_sorgu"].strip()):
                    if kaynak.footage_getir(yedek_sorgu, vyol_full, yt_once=yt_once):
                        atif = kaynak.atif_al(vyol_full)
                        if atif.get("kanal"):
                            s["kaynakYazi"] = atif["kanal"]
                        print(f"  sahne {n}: genel yedek klip '{yedek_sorgu}'", file=sys.stderr)
                        _kopru_yaz(vyol_full)       # R-1d-b: yedek klip de kopruden gecer
                        return ("video", f"isler/{is_adi}/sahne_{n}.mp4")
                # Son care: tekrar yasagini gecici olarak kaldir
                if kaynak.footage_getir(s["footage_sorgu"].strip(), vyol_full,
                                        yt_once=yt_once, tekrara_izin=True):
                    print(f"  sahne {n}: klip TEKRARI (gorsel yasak)", file=sys.stderr)
                    _kopru_yaz(vyol_full)
                    return ("video", f"isler/{is_adi}/sahne_{n}.mp4")
                # ⚠ FAZ UI-5 — STABIL HATA, SESSIZ DUSUS DEGIL.
                # ESKI HAL: buradan AI STATIK GORSELE dusuluyordu ("AI gorsele
                # mecbur") ve kullanici "tamami video olacakti" derken
                # timeline'a zoom'lu statik kare giriyordu. Kullanici karari
                # (15 Agu 2026): video bulunamayan sahne AI statik gorsele
                # DUSMEZ; STABIL kodla bos birakilir ve neden GORUNUR kalir.
                # Sahne None doner -> ust katman onu "atlandi" sayar ve mevcut
                # esikler (basarisiz>=8 ve uretilmis<3) isi durdurur.
                print(f"  sahne {n}: {MEDYA_VIDEO_YOK} — gercek video klip yok, "
                      f"AI statik gorsele DUSULMUYOR", file=sys.stderr)
                _bosluk_yaz(f"{MEDYA_VIDEO_YOK}: gercek video klip bulunamadi "
                            f"(gorsel_yasak: statik gorsele dusulmedi)")
                return None
            # ⚠ FAZ R-1d-b: footage yolundan CIKIYORUZ (AI gorsele dusuluyor)
            # -> kapsam boslugu BURADA yazilir, RASTGELE STOKLA KAPANMAZ.
            _bosluk_yaz("footage bulunamadi; AI gorsele dusuldu")

        # ⚠ FAZ UI-7 — UI7-GORSEL-YASAK-KAPISI (AI GORSEL YOLU HER KOSULDA KAPALI)
        # OLCULEN KUSUR (gercek 120 sn is, gercek_video=0.531): yukaridaki
        # footage blogu YALNIZCA `kaynak == "footage"` sahnelerde calisiyor.
        # Planlayici bir sahneyi `kaynak="gorsel"` isaretleyince blok HIC
        # calismiyor, dolayisiyla icindeki `gorsel_yasak` kontrolu de ATLANIYOR
        # ve akis dogrudan AI gorsele dusuyordu (log: openai/uretilmis-eser).
        # ⚠ Kapi artik blogun DISINDA ve `kaynak`/`footage_sorgu` alanlarindan
        # BAGIMSIZ: gorsel_yasak stilde AI/statik gorsel URETILMEZ. Once bir
        # kez daha GERCEK VIDEO aranir (sorgu yoksa anlatimdan turetilir),
        # bulunamazsa sahne stabil kodla BOS birakilir.
        if prof.get("gorsel_yasak"):
            _vy = os.path.join(PUBLIC, "isler", is_adi, f"sahne_{n}.mp4")
            # ⚠ FAZ UI-8 / UI8-TURKCE-SORGU: SORGU INGILIZCE OLMALI.
            # OLCULEN KUSUR: fallback `s["anlatim"]` idi ve o metin TURKCE.
            # Pexels Turkce sorguyu karsilamiyor -> arama bos donuyor, sahne
            # dusuyordu (olcum: kapi 0 klip buldu, 6 sahne MEDYA-VIDEO-YOK).
            # Plan sozlesmesi `footage_sorgu`yu "specific ENGLISH stock-footage
            # query" olarak uretir; `scene_prompt` de INGILIZCE'dir. Turkce
            # anlatim ARTIK sorgu olarak KULLANILMAZ.
            _sorgu = (str(s.get("footage_sorgu") or "").strip()
                      or str(s.get("scene_prompt") or "").strip()[:160])
            _denenecek = ([_sorgu] + list(kaynak.genel_yedek_sorgular(_sorgu))
                          if _sorgu else [])
            for _sq in _denenecek:
                if kaynak.footage_getir(_sq, _vy, yt_once=yt_once):
                    _atif = kaynak.atif_al(_vy)
                    if _atif.get("kanal"):
                        s["kaynakYazi"] = _atif["kanal"]
                    print(f"  sahne {n}: UI-7 kapisi gercek klip buldu "
                          f"'{_sq[:40]}'", file=sys.stderr)
                    _kopru_yaz(_vy)
                    return ("video", f"isler/{is_adi}/sahne_{n}.mp4")
            if _sorgu and kaynak.footage_getir(_sorgu, _vy, yt_once=yt_once,
                                               tekrara_izin=True):
                print(f"  sahne {n}: UI-7 kapisi klip TEKRARI", file=sys.stderr)
                _kopru_yaz(_vy)
                return ("video", f"isler/{is_adi}/sahne_{n}.mp4")
            # ⚠ FAZ Y-5 / Y5-YENIDEN-KULLANIM-TAVANI-DELIYOR — KLIP YENIDEN
            # KULLANIMI KALDIRILDI.
            # UI-8'de buraya "sureyi korumak" icin, bu iste ZATEN INDIRILMIS
            # bir klibi kopyalayan bir son care konmustu. O yol GLOBAL
            # "ayni kaynak <= 8 sn" sozlesmesini MATEMATIKSEL OLARAK ihlal
            # ediyor: tavan 8.0 sn (medya/saglayici_motoru), belgesel sahne
            # suresi ~5.5-7 sn; ayni klip IKI sahnede kullanilirsa toplam
            # ~11-14 sn > 8 sn.
            # ⚠ Tavan UYGULAMASI sahne bazindadir (`_kaynak_tavani_uygula`
            # her sahnenin KENDI suresine bakar; sahneler arasi kullanim
            # akumulatoru YOKTUR). Gercek global mantik
            # `kaynak_tavani.bolme_plani` icinde ama uretimde CAGRILMIYOR.
            # Global ihlali yalnizca `gercek_qa` post-hoc yakalar
            # (`GERCEK-KAYNAK-TAVANI` fail) — yani yeniden kullanim, isi
            # QA'da FAIL'e dusuren bir TUZAKTI.
            # ⚠ OLCUM: bu yol son IKI gercek iste HIC devreye girmedi
            # (sayac 0; footage 17/17 ve 12/12) — UI-8'in INGILIZCE sorgu
            # duzeltmesi sahneleri zaten kurtariyor. Fayda saglamadan risk
            # tasiyordu.
            # ⚠ AYRICA duzeltildi: provenans `_pv.get("url")` ile okunuyordu;
            # `stok_provenans_al` sozlugunde o anahtar YOK (dogrusu
            # `orijinal_url`) — kaynak URL'i her seferinde BOS yaziliyordu.
            print(f"  sahne {n}: {MEDYA_VIDEO_YOK} (UI7-GORSEL-YASAK-KAPISI) — "
                  f"hic gercek klip yok; AI/statik gorsele DUSULMUYOR",
                  file=sys.stderr)
            _bosluk_yaz(f"{MEDYA_VIDEO_YOK}: UI7-GORSEL-YASAK-KAPISI "
                        f"(gercek video klip bulunamadi)")
            return None

        # 2) AI gorsel (footage yoksa/basarisizsa)
        sp = str(s.get("scene_prompt", "")).strip() or str(s.get("footage_sorgu", "")).strip()
        # BEYAZ TUVAL sahnesi: gorsel, beyaz zemine YALITILMIS konu olarak uretilmeli.
        # Aksi halde EditPaketi beyaz zemine tam kare fotograf yerlestirir ve referansin
        # ayirt edici gorunumu (nesne + olcu etiketleri) hic olusmaz.
        _gr = s.get("grafik") if isinstance(s.get("grafik"), dict) else {}
        if _gr.get("tur") == "beyaz-tuval":
            sp += (". CRITICAL FRAMING: the subject is CUT OUT and isolated on a COMPLETELY "
                   "PLAIN PURE WHITE background (#FFFFFF) with nothing else in frame — no room, "
                   "no ground, no sky, no props, no shadow on the floor, only a very soft contact "
                   "shadow directly under the subject. Product-catalogue isolation, subject "
                   "centred with generous white margin on all four sides. No text of any kind.")
        gyol_full = os.path.join(PUBLIC, "isler", is_adi, f"sahne_{n}.png")
        try:
            uretildi = referansli_gorsel(sp, kar_yol, gyol_full, stil_prompt=gorsel_ek,
                                         kar_kilit=kar_kilit, stil_yol=stil_yol,
                                         capa_yol=capa_yol, stil_kilit=stil_kilit,
                                         model=gorsel_model, cerceve=cerceve_ek,
                                         saglayici=unlu_motor if unlu_aktif else "")
        except BakiyeHatasi:
            # Bakiye/limit doldu: DAHA FAZLA PARA HARCAMA; diger isciler de yeni istek acmaz.
            bakiye_bitti = True
            return None
        if not uretildi:
            return None
        # ── FAZ R-1d-d: URETILEN GORSEL DE GERCEK MEDYADIR ──
        # ⚠ OLCULEN KUSUR (R-1d-c pilotu): `kapsam_orani 0.25`. Kopru YALNIZ
        # stok klipleri kaydediyordu; AI ile URETILEN sahne gorselleri
        # hicbir adaya baglanmiyordu ve o beat'ler GARANTILI `fallback`
        # oluyordu. Oysa bu gorsel GERCEKTEN uretildi, diskte duruyor ve
        # lisansi BIZE ait.
        # ⚠ UYDURMA YOK: `medya_turu` "image" yazilir (VIDEO DENMEZ), boylece
        # `gercek_video_orani` olcumu SISIRILMEZ.
        try:
            kaynak.stok_provenans_kaydet(
                gyol_full,
                saglayici=(SAGLAYICI or "openai"),
                asset_id=f"{is_adi}_s{n:03d}", url="",
                baslik=str(sp)[:80],
                sorgu=str(s.get("footage_sorgu") or "")[:120],
                sure_sn=0.0, kare_dogrulandi=True)
            kaynak.stok_provenans_isaretle(
                gyol_full, medya_turu="image", lisans="uretilmis-eser",
                model=str(gorsel_model or ""))
        except Exception:                                    # noqa: BLE001
            pass                       # provenans yazilamazsa uretim DURMAZ
        renk_uydur(gyol_full, olcum_hedef, f"sahne {n}")
        # ⚠ FAZ UI-8 / UI8-MAGNIFIC-KAPALI: VIDEO-ONLY AKISTA MAGNIFIC YOK.
        # OLCULEN KUSUR: is sirasinda otomatik upscale denendi ve KREDI
        # DENEMESI yapildi ("magnific POST 502: Error consuming credits").
        # Kredi harcanmadi ama denenmemeliydi: `gorsel_yasak` (video-only)
        # akista AI gorsel zaten URETILMEZ, dolayisiyla upscale ANLAMSIZDIR.
        if mag_profil and s.get("hd") and not prof.get("gorsel_yasak"):
            kaynak.magnific_upscale(gyol_full, optimized_for=mag_profil, scale="2x")
        # 3) GERCEK VIDEO: acilis sahnesiyse gorseli canlandir. Motor zinciri:
        #    GROK once ($0.40/8sn — Sora'nin yarisi + unlu toleransli) -> SORA ($0.80) -> efekt.
        #    VIDEO_MOTOR=sora ile Grok atlanabilir.
        if n in sora_adaylari and not bakiye_bitti and not uretim_durdu:
            svyol = os.path.join(PUBLIC, "isler", is_adi, f"sahne_{n}_sora.mp4")
            klip_ok = False
            if XAI_KEY and os.environ.get("VIDEO_MOTOR", "grok") != "sora":
                try:
                    klip_ok = grok_klip(gyol_full, sp, svyol)
                except BakiyeHatasi:
                    print("  grok kredisi bitti -> bu sahne icin Sora denenecek", file=sys.stderr)
            if not klip_ok:
                klip_ok = sora_klip(gyol_full, sp, svyol)
            if klip_ok:
                time.sleep(gorsel_bekle)
                return ("video", f"isler/{is_adi}/sahne_{n}_sora.mp4")
            print(f"  sahne {n}: video klip olmadi, efektli fotografla devam", file=sys.stderr)
        # Hiz limiti: her ISCI kendi isteginden sonra bekler (toplam hiz = paralel/(uretim+bekleme))
        time.sleep(gorsel_bekle)
        # ⚠ FAZ R-1d-d: uretilen gorsel de avci butcesine YAZILIR; aksi halde
        # bu sahnenin beat'leri GARANTILI `fallback` olurdu.
        _kopru_yaz(gyol_full)
        return ("image", f"isler/{is_adi}/sahne_{n}.png")

    # ── FAZ A+B tek fonksiyonda: thread'de kosar, SESLENDIRME ile AYNI ANDA ──
    def _gorsel_fazi():
        nonlocal capa_yol, capa_profilden, bakiye_bitti, uretim_durdu
        # FAZ A: CAPA (yalniz animasyon/hikaye ve profil capasi yoksa).
        # Ilk basarili sahne sonraki TUM sahnelere referans olacagi icin sirali uretilmek zorunda.
        basla = 0
        if mod in ("animasyon", "hikaye") and not capa_yol:
            while basla < len(islenecek) and not bakiye_bitti:
                i, n, s, _, _ = islenecek[basla]
                bildir(f"Sahne {n}/{toplam}: çapa görseli üretiliyor...", 8)
                r = _sahne_medya(n, s)
                basla += 1
                if r:
                    sonuc_medya[n] = r
                    gyol_full = os.path.join(PUBLIC, "isler", is_adi, f"sahne_{n}.png")
                    capa_yol = os.path.join(is_dizini, "_capa.png")   # Magnific ONCESI kucuk kopya
                    try:
                        shutil.copy(gyol_full, capa_yol)
                    except Exception:
                        capa_yol = gyol_full
                    # PROFIL VAR ama henuz kilitli degil -> ilk sahneyi kanalin KALICI capasi yap.
                    if kanal and not capa_profilden:
                        if profil_capa_kilitle(profil_id, capa_yol):
                            capa_profilden = True
                            print(f"  profil '{profil_id}' capasi KILITLENDI", file=sys.stderr)
                    break
                print(f"sahne {n} atlandi (capa denemesi)", file=sys.stderr)
                if basla >= 6:   # 6 denemede capa cikmadiysa sistemsel sorun var, para yakma
                    uretim_durdu = True
                    print("  capa uretilemedi -> uretim durduruldu", file=sys.stderr)

        # FAZ B: KALAN GORSELLER PARALEL
        kalan = islenecek[basla:]
        if kalan and not bakiye_bitti and not uretim_durdu:
            bildir(f"Görseller üretiliyor ({paralel} paralel)...", 9)
            basarisiz = 0
            with ThreadPoolExecutor(max_workers=paralel) as havuz:
                gelecek = {havuz.submit(_sahne_medya, n, s): n for i, n, s, _, _ in kalan}
                for g in as_completed(gelecek):
                    n = gelecek[g]
                    try:
                        r = g.result()
                    except Exception as e:   # beklenmedik istisna tek sahneyi yaksin, isi degil
                        r = None
                        print(f"  sahne {n} gorsel istisna: {str(e)[:140]}", file=sys.stderr)
                    if r:
                        sonuc_medya[n] = r
                    else:
                        basarisiz += 1
                        print(f"sahne {n} atlandi", file=sys.stderr)
                        # Cok basarisizlik + neredeyse hic basari yok: sistem bozuk, durdur
                        if basarisiz >= 8 and len(sonuc_medya) < 3:
                            uretim_durdu = True
                    with sayac_kilit:
                        tamamlanan[0] += 1
                        yuzde = 8 + int(50 * tamamlanan[0] / max(1, len(islenecek)))
                    bildir(f"Görsel {tamamlanan[0]}/{len(islenecek)} hazır", yuzde)
        if bakiye_bitti:
            print(f"  BAKIYE bitti — {len(sonuc_medya)} uretilmis sahneyle devam", file=sys.stderr)

    # ── GORSELLER (thread) + SESLENDIRME (asyncio) AYNI ANDA ──
    # TTS gorsele bagimli DEGIL (sadece metne bakar) ama eskiden gorseller bitince basliyordu
    # (30 dk videoda ~4 dk bosa bekleme). Simdi iki faz ust uste kosar; TTS tum sahneler icin
    # uretilir (gorseli cikmayanin sesi bosa gider — edge-tts bedava, kayip yok).
    tts_sem = asyncio.Semaphore(max(1, int(os.environ.get("TTS_PARALEL", "5"))))

    async def _tts(n, metin):
        async with tts_sem:
            syol = f"isler/{is_adi}/ses_{n}.mp3"
            kelimeler, sure = await uret_seslendir(metin, ses, os.path.join(PUBLIC, syol),
                                                  ayar=ses_ayar)
            return n, syol, kelimeler, sure

    gorsel_gorevi = asyncio.create_task(asyncio.to_thread(_gorsel_fazi))
    tts_cikti = await asyncio.gather(
        *[_tts(n, metin) for i, n, s, metin, _ in islenecek],
        return_exceptions=True)
    await gorsel_gorevi

    tts_sonuc = {}
    for t in tts_cikti:
        if isinstance(t, BaseException):
            print(f"  tts istisna: {str(t)[:120]}", file=sys.stderr)
            continue
        n, syol, kelimeler, sure = t
        if kelimeler is None:   # TTS retry'lar tukendi -> bu sahneyi atla, is olmesin
            print(f"sahne {n} sesi uretilemedi, atlandi", file=sys.stderr)
            continue
        tts_sonuc[n] = (syol, kelimeler, sure)

    # GERCEK konusma hizini kaydet — sonraki isler bunu kullanir
    try:
        # Kelime sayisi SAHNE METNINDEN sayilir. Ilk surumde uret_seslendir'in donen
        # "kelimeler" degerinden sayiyordum; o deger bos/farkli bicimde geldi ve
        # ses_hizi_kaydet sessizce "olcum guvenilir degil" diyerek cikti (kalibrasyon
        # dosyasi hic yazilmadi). Metin her zaman elimizde.
        _kel = sum(len(str(metin).split())
                   for _i, _n, _s, metin, _ov in islenecek if _n in tts_sonuc)
        _sn = sum(float(v[2] or 0) for v in tts_sonuc.values())
        print(f"  hiz olcumu: {_kel} kelime / {_sn:.1f} sn = "
              f"{(_kel / _sn * 60) if _sn else 0:.0f} wpm", file=sys.stderr)
        ses_hizi_kaydet(ses_secim or "otomatik", _kel, _sn)
    except Exception as e:
        print(f"  hiz kalibrasyonu atlandi: {str(e)[:80]}", file=sys.stderr)

    # ⚠ FAZ R-1d-g: bolme icin sahne basina HAM veri (props indeksiyle).
    _sahne_ham = {}

    def _kopru_kaydet(_yol, _sahne, _n):
        """Gercek medya secimini avci butcesine kopruler (ORTAK kaydedici).

        ⚠ FAIL-CLOSED: provenans/lisans/kare dogrulamasi eksikse kayit
        YAPILMAZ; sahne kapsam BOSLUGU olarak yazilir.
        """
        if _avci_butce is None:
            return False
        _pv = kaynak.stok_provenans_al(_yol)
        _kp = medya_kopru.stok_secimi_kaydet(
            _avci_butce, hedef_yol=_yol,
            scene_id=str((_sahne or {}).get("scene_id") or f"s{_n:03d}"),
            provenans=_pv, fact_id=str((_sahne or {}).get("fact_id") or ""),
            sahne_amaci=str((_sahne or {}).get("sahne_amaci") or ""),
            sorgu=str((_sahne or {}).get("footage_sorgu") or "").strip())
        if _kp["kaydedildi"]:
            print(f"  sahne {_n}: KOPRU -> butceye secim yazildi "
                  f"({_pv.get('saglayici')}/{_pv.get('lisans')})",
                  file=sys.stderr)
            return True
        _avci_butce.bosluk_ekle(
            str((_sahne or {}).get("scene_id") or f"s{_n:03d}"),
            f"stok koprusu: {_kp['neden']}")
        return False

    def _ses_dilimle(kaynak_ses, bas_sn, uzunluk_sn, hedef):
        """Sesi ffmpeg ile KES. ⚠ UCRETSIZ + YEREL; ag/kredi YOK.

        ⚠ TASINABILIR + DETERMINISTIK KODEK: `pcm_s16le` + `.wav`.
        Once sabit `libmp3lame` kullaniliyordu; bazi ffmpeg derlemelerinde o
        encoder YOK ve dilimleme SESSIZCE basarisiz oluyordu (pilotta
        olculdu: "3 parca atanamadi -> KAYNAK-TAVANI-SURE-BOZUK").
        Uzantidan kodek TURETMEK de yeterli DEGIL — `.mp3` hedefte yine
        MP3 encoder secilir. PCM WAV her derlemede vardir.
        ⚠ Doner: (ok, stderr) — basarisizlik SEBEBI raporlanabilsin.
        """
        try:
            r = subprocess.run(
                ["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{bas_sn:.3f}",
                 "-t", f"{uzunluk_sn:.3f}", "-i", kaynak_ses,
                 "-c:a", "pcm_s16le", "-ar", "44100", hedef],
                capture_output=True, text=True, timeout=180)
            ok = r.returncode == 0 and os.path.exists(hedef)
            return ok, (r.stderr or "")[-300:]
        except Exception as e:                               # noqa: BLE001
            return False, f"{type(e).__name__}: {str(e)[:160]}"

    def _kelime_dilimle(kelimeler, bas_sn, bitis_sn):
        """Kelime zaman damgalarini pencereye kirp ve SIFIRA tasi."""
        out = []
        for k in (kelimeler or []):
            t0, t1 = float(k.get("t0", 0)), float(k.get("t1", 0))
            if t1 <= bas_sn or t0 >= bitis_sn:
                continue
            out.append(dict(k, t0=round(max(0.0, t0 - bas_sn), 3),
                            t1=round(min(bitis_sn, t1) - bas_sn, 3)))
        return out

    def _kaynak_tavani_uygula(sahneler, ham):
        """Tavani asan sahneyi BOL, her parcaya FARKLI varlik ata.

        ⚠ FAIL-CLOSED: ikinci ucretsiz stok varlik EDINILEMEZSE sahne
        BOLUNMEZ ve `KAYNAK-TAVANI-VARLIK-YOK` raporlanir — ayni kaynak
        tekrar kullanilip tavan ASILMAZ, tavan YUKSELTILMEZ.
        ⚠ Ses ve altyazi SUNUCUDA senkron kesilir (ffmpeg; ucretsiz).
        """
        sorunlar, bolunen = [], 0
        yeni_liste = []
        for idx, sh in enumerate(list(sahneler)):
            h = ham.get(idx) or {}
            sure = float(sh.get("sure") or 0)
            n_parca = kaynak_tavani.parca_sayisi(sure)
            if n_parca <= 1 or not h:
                yeni_liste.append(sh)
                continue
            _s = h.get("s") or {}
            p_sure = round(sure / n_parca, 3)

            # ── (A) MEVCUT PARCANIN KIMLIGI ZORUNLU ──
            # ⚠ Mevcut klibin provider+asset_id+lisans kimligi YOKSA yeni
            # adayin ondan FARKLI oldugu KANITLANAMAZ -> FAIL-CLOSED.
            _mevcut_kimlik = kaynak_tavani.kimlik_normalize(
                kaynak.stok_provenans_al(
                    os.path.join(PUBLIC, str(sh.get("medya") or ""))))
            if not _mevcut_kimlik:
                sorunlar.append({"kod": kaynak_tavani.KOD_VARLIK_YOK,
                                 "scene_id": sh.get("scene_id"),
                                 "detay": ("mevcut parcanin provider/asset_id/"
                                           "lisans kimligi YOK -> farklilik "
                                           "kanitlanamaz")})
                yeni_liste.append(sh)
                continue

            # ── (B) SES DILIMLERI ONCE (transactional sira) ──
            # ⚠ Kesim basarisizsa HICBIR ek varlik EDINILMEZ ve kopruye
            # HICBIR SEY yazilmaz; butce/provenans olcumu KIRLENMEZ.
            # ⚠ OLCULEN KUSUR (pilot job_1786724831925): `syol` GORELIDIR
            # (`isler/<is>/ses_N.mp3`) ve dogrudan ffmpeg'e verilince surecin
            # cwd'sine gore cozuluyor, dosya BULUNAMIYORDU. Sunucuda
            # kanitlandi: ayni ffmpeg komutu MUTLAK yolla rc=0 veriyor.
            # Kaynak/hedef ffmpeg icin MUTLAK; props `ses` alani GORELI kalir
            # (renderer goreli bekliyor).
            _ses_yollari, _kesim_hata = [], ""
            _kaynak_ses_abs = os.path.join(PUBLIC, str(h["syol"]))
            for j in range(n_parca):
                _bas = round(j * p_sure, 3)
                _goreli = (f"{str(h['syol']).rsplit('.', 1)[0]}_p{j}.wav")
                _hedef = os.path.join(PUBLIC, _goreli)
                _ok, _err = _ses_dilimle(_kaynak_ses_abs, _bas, p_sure, _hedef)
                if not _ok:
                    _kesim_hata = _err or "bilinmeyen"
                    break
                _ses_yollari.append(_goreli)      # props GORELI yol tutar
            if _kesim_hata:
                sorunlar.append({"kod": kaynak_tavani.KOD_SURE_BOZUK,
                                 "scene_id": sh.get("scene_id"),
                                 "detay": f"ses dilimlenemedi: {_kesim_hata}"})
                for _y in _ses_yollari:            # yarim kalan dilimleri sil
                    try:
                        os.remove(os.path.join(PUBLIC, _y))
                    except OSError:
                        pass
                yeni_liste.append(sh)
                continue

            # ── (C) EK VARLIKLAR: FARKLI KAYNAKLI ucretsiz stok klipler ──
            # ⚠ Kabul karari `kaynak_tavani.ek_varlik_edin`e aittir: kimlik
            # (saglayici|asset_id) MEVCUT parcadan ve birbirinden FARKLI
            # olmali, lisans/saglayici/asset_id DOLU olmali ve KOPRU KAYDI
            # BASARILI olmali. Aksi halde aday REDDEDILIR, siradaki denenir.
            # ⚠ FAZ R-1d-i: URETILMIS GORSEL sahnesinde `footage_sorgu`
            # BOSTUR; eski kod bu durumda aday havuzunu BOS birakiyor ve
            # sahne BOLUNEMIYORDU (olculdu: `..._s001` 8.172 sn ihlali
            # suruyordu). Sorgu artik sahnenin KENDI INGILIZCE gorsel
            # tarifinden (`scene_prompt`) DETERMINISTIK turetilir.
            # ⚠ LLM/ucret YOK. Turetilemezse STABIL KOD ile fail-closed.
            _sorgu = str(_s.get("footage_sorgu") or "").strip()
            _sq = kaynak_tavani.stok_sorgulari(
                str(_s.get("scene_prompt") or _s.get("anlatim") or ""),
                mevcut_sorgu=_sorgu)
            if not _sq["ok"]:
                sorunlar.append({"kod": _sq["kod"],
                                 "scene_id": sh.get("scene_id"),
                                 "detay": _sq.get("neden", "")})
                for _y in _ses_yollari:
                    try:
                        os.remove(os.path.join(PUBLIC, _y))
                    except OSError:
                        pass
                yeni_liste.append(sh)
                continue
            _sorgular = list(_sq["sorgular"])
            if _sorgu:
                _sorgular += list(kaynak.genel_yedek_sorgular(_sorgu))[:3]

            def _aday(sira, _n=h["n"], _sorg=_sorgular):
                if sira >= len(_sorg):
                    return None
                hedef = os.path.join(PUBLIC, "isler", is_adi,
                                     f"sahne_{_n}_p{sira + 1}.mp4")
                if kaynak.footage_getir(_sorg[sira], hedef, yt_once=False):
                    return hedef
                return None

            _ed = kaynak_tavani.ek_varlik_edin(
                adet=n_parca - 1, mevcut_kimlikler=[_mevcut_kimlik],
                aday_uretici=_aday,
                provenans_okuyucu=kaynak.stok_provenans_al,
                kopru_yazici=lambda y: _kopru_kaydet(y, _s, h["n"]),
                maks_deneme=len(_sorgular))
            if not _ed["ok"]:
                # ⚠ FAIL-CLOSED: bolme YAPILMAZ; kapi ihlali GORUNUR kalir.
                sorunlar.append({"kod": _ed["kod"],
                                 "scene_id": sh.get("scene_id"),
                                 "detay": (f"{_ed['istenen']} ek FARKLI "
                                           f"kaynak gerekti, {_ed['bulunan']} "
                                           f"bulundu; red: "
                                           f"{[r.get('neden') for r in _ed['red']][:4]}")})
                for _y in _ses_yollari:
                    try:
                        os.remove(os.path.join(PUBLIC, _y))
                    except OSError:
                        pass
                yeni_liste.append(sh)
                continue
            ek_yollar = [os.path.relpath(k["yol"], PUBLIC)
                         for k in _ed["kabul"]]

            # ── (D) PARCALARI KUR ──
            parcalar = []
            for j in range(n_parca):
                _bas = round(j * p_sure, 3)
                yeni = dict(sh)
                yeni["sure"] = p_sure
                yeni["ses"] = _ses_yollari[j]
                yeni["scene_id"] = f"{sh.get('scene_id')}p{j + 1}"
                yeni["medya"] = (sh.get("medya") if j == 0
                                 else ek_yollar[j - 1])
                yeni["altyazi"] = uretmod.altyazi_parcala(
                    _kelime_dilimle(h["kelimeler"], _bas, _bas + p_sure),
                    p_sure)
                parcalar.append(yeni)
            bolunen += 1
            yeni_liste.extend(parcalar)
        sahneler[:] = yeni_liste
        return {"bolunen_sahne": bolunen, "sorunlar": sorunlar,
                "tavan_sn": kaynak_tavani.KAYNAK_BASINA_TAVAN_SN}

    # Ard arda ayni kamera hareketi olmasin diye bir onceki sahnenin kurgusu tutulur
    _son_kurgu = {}
    # Montaj: orijinal sahne sirasi korunur (paralellik sirayi bozamaz)
    for i, n, s, metin, overlay in islenecek:
        if n not in sonuc_medya or n not in tts_sonuc:
            continue
        tur, medya = sonuc_medya[n]
        syol, kelimeler, sure = tts_sonuc[n]
        props_sahneler.append({
            # ⚠ FAZ R-1d-b: SAHNE KIMLIGI. Sahneler bugune kadar `scene_id`
            # TASIMIYORDU: `edit_kopru.plan_kur(cumleler=...)` her cumleye
            # `scene_id: ""` veriyor, medya manifesti ise `s001/s002...`
            # tasiyordu -> `editor.plan` beat ile adayi ESLESTIREMIYOR ve
            # plan SIFIR cekimle donuyordu (olculdu: `sahne=0`, butun PRE-QA
            # olcum sozlukleri BOS). Kimlik `_sahne_medya(n, s)` ile AYNI
            # `n`den turer, boylece iki taraf BIT-BIT ayni kimligi kullanir.
            # ⚠ Video.tsx bu alani OKUMAZ; bilinmeyen props anahtari cizimi
            # etkilemez (22 alan sozlesmesi de DEGISMEDI).
            "scene_id": str(s.get("scene_id") or f"s{n:03d}"),
            # ⚠ FAZ R-1d-b: ANLATIM METNI. `edit_kopru.plan_kur(cumleler=...)`
            # her cumlenin metnini `x.get("anlatim")`dan okuyor ama
            # `props_sahneler` bu alani HIC TASIMIYORDU -> her cumle BOS
            # metinle gidiyor, beat plani kurulamiyor ve plan SIFIR cekimle
            # donuyordu (olculdu: `sahne=0`, PRE-QA vakumda hukum veriyor).
            # ⚠ Sunucuda dogrulandi: ayni cagri DOLU metinle 10 cekim ve
            # GERCEK olcumler uretiyor. Video.tsx bu alani OKUMAZ.
            "anlatim": metin,
            # ⚠ FAZ Y-7 / Y7-FACT-PROPS-SINIRI — FACT ZINCIRI BURADA
            # KOPUYORDU. `arastirma_kopru.fact_bagla()` fact_id'yi GERCEKTEN
            # yaziyor (`s["fact_id"] = ...`) ve ayni `s` sozlugu medya
            # avcisina fact_id'yi basariyla veriyor. AMA bu props sozlugu
            # `fact_id` anahtarini HIC TASIMIYORDU; `edit_kopru.plan_kur`
            # girdisi props'tan kuruldugu icin her cumle `fact_id: ""`
            # aliyor -> `beat` bos -> `Cekim.fact_id=""` -> `qa_on` HER
            # cekime `FACT-BAGLANTI-YOK` (fail) veriyordu. Gercek iste
            # 22/22 fail bunu dogruladi.
            # ⚠ `scene_id` (R-1d-b) ve `anlatim` (R-1d-b) ile BIREBIR AYNI
            # SINIF kusur: uretimde veri VAR, props sinirinda DUSUYOR.
            # ⚠ Video.tsx bu alanlari OKUMAZ; `/api/generate` 22 alan
            # sozlesmesi DEGISMEZ.
            "fact_id": str(s.get("fact_id") or ""),
            "iddia_metni": str(s.get("iddia_metni") or ""),
            "tur": tur, "medya": medya, "ses": syol, "sure": round(sure, 3),
            **({"zoom": "yok", "pan": "yok"} if not zoom_acik else
               (lambda k: (_son_kurgu.update(k), {"zoom": k["zoom"], "pan": k["pan"]})[1])(
                   islev_kurgu(kurgu_analiz[i]["islev"], kurgu_analiz[i]["yogunluk"], i,
                               dict(_son_kurgu))
                   if i < len(kurgu_analiz) else
                   {"zoom": "in" if i % 2 == 0 else "out", "pan": panlar[i % 4]})),
            # Liste maddesi acilisinda basligi kareye yaz ("9 GROCERY BILLS")
            "overlay": (kurgu_analiz[i]["baslik"] if i < len(kurgu_analiz)
                        and kurgu_analiz[i].get("baslik") else overlay),
            "altyazi": uretmod.altyazi_parcala(kelimeler, sure),
            # Vurgu: metin analizi yogunluk>=4 dediyse VEYA hikaye acilisindaysa
            "vurgu": bool((i < len(kurgu_analiz) and kurgu_analiz[i]["yogunluk"] >= 4)
                          or (mod == "hikaye" and kumulatif_sn < acilis_sn)),
            # Anlatim islevi -> Video.tsx GECIS TIPINI buna gore secer
            # (liste=yandan kayma, gecmis=saat silme, vurgu=keskin silme, digeri=crossfade)
            "islev": (kurgu_analiz[i]["islev"] if i < len(kurgu_analiz) else "aciklama"),
            # Edit paketi grafigi (EditPaketi.tsx sablonlari). Plan uretmediyse alan hic
            # gecmez -> Video.tsx tarafinda katman cizilmez, eski davranis aynen korunur.
            **({"grafik": s["grafik"]} if isinstance(s.get("grafik"), dict) else {}),
            # Bolum basligi: plan sadece bolumun ILK sahnesine koyar, digerlerinde bos
            **_etiket_props(s),
            **_alt_band_props(s),
            # ⚠ FAZ I-41: CC/lisansli klip atfi. Bu satir YOKKEN kunye props
            # sinirinda dusuyordu ve IKI renderer da onu goremiyordu.
            **_kaynak_yazi_props(s),
            # Efekt atamasi: stil temeli + islev vurgusu (deterministik, LLM'e sorulmaz)
            # ⚠ FAZ I-2d: bilesik profil varsa gorsel imza ONDAN turetilir;
            # yoksa `_gorsel_ek` None kalir ve eski tablolar aynen isler.
            **({"gecisImza": _gi} if (_gi := gecis_imza_sec(edit_id, i, _gorsel_ek))
               else {}),
            **({"efektler": _ef} if (_ef := efekt_ata(
                edit_id, kurgu_analiz[i]["islev"] if i < len(kurgu_analiz) else "aciklama",
                i, _gorsel_ek))
               else {}),
            **({"bolum": str(s["bolum"]).strip(),
                "bolumYeri": ("ust" if str(s.get("bolum_yeri")) == "ust" else "orta")}
               if str(s.get("bolum") or "").strip() else {}),
        })
        # ⚠ FAZ R-1d-g: bolme icin gereken HAM veriler (ses/kelime/sorgu).
        _sahne_ham[len(props_sahneler) - 1] = {
            "n": n, "s": s, "syol": syol, "kelimeler": kelimeler,
            "sure": sure, "medya": medya, "tur": tur}
        kumulatif_sn += sure

    # ── FAZ R-1d-g: AYNI KAYNAK <= 8.0 sn — PLAN GERCEK HATTA UYGULANIR ──
    _tavan_rapor = _kaynak_tavani_uygula(props_sahneler, _sahne_ham)
    if _tavan_rapor.get("sorunlar"):
        print(f"  KAYNAK TAVANI: {len(_tavan_rapor['sorunlar'])} parca "
              f"atanamadi -> {_tavan_rapor['sorunlar'][0].get('kod')}",
              file=sys.stderr)

    if not props_sahneler:
        # Hicbir sahne yoksa: sebebi bakiye ise NET soyle (kullanici 'neden' bilsin)
        if bakiye_bitti:
            raise RuntimeError(BAKIYE_MESAJI)
        # ⚠ FAZ UI-6 — TESHIS EDILEBILIR HATA.
        # OLCULEN OLAY (14 Agu 2026 23:04, anonim is): mesaj yalnizca
        # "Hiç sahne üretilemedi" diyordu; HANGI KATMANIN coktugu
        # GORUNMUYORDU. Kok neden ancak elle remote probe ile bulunabildi
        # (bilesenler saglamdi; is bir AG KESINTISI penceresine denk
        # gelmisti). Sahne ancak `n in sonuc_medya AND n in tts_sonuc`
        # ise eklenir; bu iki kumeden hangisinin bosaldigi TANIYI belirler.
        # ⚠ Uretim davranisi DEGISMEZ — yalnizca hata AYIRT EDILEBILIR olur.
        _n_med, _n_tts = len(sonuc_medya), len(tts_sonuc)
        _kod = ("SAHNE-YOK-MEDYA-VE-TTS" if not _n_med and not _n_tts else
                "SAHNE-YOK-MEDYA" if not _n_med else
                "SAHNE-YOK-TTS" if not _n_tts else
                "SAHNE-YOK-KESISIM")
        raise RuntimeError(
            f"Hiç sahne üretilemedi ({_kod}): {len(islenecek)} sahne denendi, "
            f"medya {_n_med}, seslendirme {_n_tts}. "
            f"Iki kume de dolu ama kesisim bossa sahne kimlikleri uyusmuyor; "
            f"biri bossa o katman (stok video / TTS) erisilemedi.")
    if bakiye_bitti:
        # KURTARMA: odenen sahneler cope gitmesin — kisa da olsa video teslim edilir
        plan["_bakiye_kesildi"] = len(props_sahneler)
    # Render-eksigi: planlanan sahnelerin cogu uretilemezse sessizce kisa video verme
    if toplam and len(props_sahneler) < max(3, toplam * 0.6):
        plan["_render_eksik"] = (len(props_sahneler), toplam)

    # Kapak
    bildir("Kapak üretiliyor...", 72)
    kapak_yolu = None
    t = plan.get("thumbnail", {})
    kp = str(t.get("prompt", "")).strip()
    ktext = str(t.get("text", "")).strip()
    if kp:
        if ktext:
            kp += (f". Render the exact text \"{ktext}\" as huge bold baked-in title typography, "
                   "high contrast, professional YouTube thumbnail. No other text.")
        khedef = os.path.join(is_dizini, "kapak.png")
        # Kapak: baslik metni GOMULU olacak (thumbnail) -> yazi_yasak=False (aksi halde ban carpisir)
        if referansli_gorsel(kp, kar_yol, khedef, stil_prompt=gorsel_ek,
                             kar_kilit=kar_kilit, stil_yol=stil_yol, capa_yol=capa_yol,
                             stil_kilit=stil_kilit, yazi_yasak=False,
                             model=GORSEL_MODEL_DOC,
                             saglayici=unlu_motor if unlu_aktif else ""):   # kapak: en iyi model
            # ⚠ FAZ UI-8 / UI8-MAGNIFIC-KAPALI: video-only akista kapak da
            # Magnific'e GITMEZ — kredi denemesi olmamalidir.
            if mag_profil and not prof.get("gorsel_yasak"):
                kaynak.magnific_upscale(khedef, optimized_for=mag_profil, scale="2x")
            kapak_yolu = khedef

    # Render
    bildir("Video render ediliyor (birkaç dakika)...", 78)
    # ⚠ FAZ UI-8 / UI8-FPS-30 — RENDER FPS ILE POST-QA BEKLENTISI AYNI.
    # OLCULEN KUSUR: render 24 fps uretiyordu ama POST-QA profili 30 fps
    # bekliyordu -> her iste `POST-FPS warn: 24.0 fps, beklenen 30.0` ve TAM
    # PASS IMKANSIZ. Iki taraf 30'da birlestirildi (qa_son `beklenen.fps`
    # profil degerini okur).
    # ESKI NOT (gecersiz): "fps 30->24 %20 daha hizli render" — hiz kazanci
    # tam PASS'i engelliyorsa kabul edilemez. VIDEO_FPS env ile geri alinir.
    props = {"fps": int(os.environ.get("VIDEO_FPS", "30")), "genislik": 1920, "yukseklik": 1080,
             "gecis": motion, "altyaziStil": altyazi_stil,
             "altyaziAyar": altyazi_ayar_coz(altyazi_sablon), "sahneler": props_sahneler}
    props_yolu = os.path.join(is_dizini, "props.json")
    with open(props_yolu, "w") as f:
        json.dump(props, f, ensure_ascii=False)

    def _kare_sayisi_oku(yol):
        """ffprobe ile kare sayisi. ⚠ UCRETSIZ + YEREL; ag/kredi YOK.

        ⚠ Okunamazsa None doner — "statiktir" DENMEZ; olcum tarafi
        `olculemedi` yazar (uydurma sinif ATANMAZ).
        ⚠ FAZ R-1d-e: tanim RENDER ONCESINE alindi; render-QA da bunu
        kullaniyor (once yalnizca editorv2 blogunda tanimliydi).
        """
        try:
            if not yol or not os.path.exists(yol):
                return None
            r = subprocess.run(
                ["ffprobe", "-v", "error", "-select_streams", "v:0",
                 "-count_packets", "-show_entries", "stream=nb_read_packets",
                 "-of", "csv=p=0", yol],
                capture_output=True, text=True, timeout=25)
            ham = (r.stdout or "").strip().rstrip(",")
            return int(ham) if ham.isdigit() else None
        except Exception:                                    # noqa: BLE001
            return None

    # ── FAZ R-1d-e: PRE-QA **RENDER EDILEN** ZAMAN CIZGISINDEN, RENDER ONCESI ──
    # ⚠ OLCULEN KUSUR (R-1d-d pilotu): PRE-QA, video ZATEN render edildikten
    # SONRA calisan ve HICBIR ZAMAN RENDER EDILMEYEN editorv2 planini
    # olcuyordu. Iki artefakt olcumle ayrisiyordu (MP4: 8 sahne / 8 kesme;
    # plan: 16 cekim, kapsam 0.5). Yani teslim zincirinin `pre_qa` halkasi
    # TESLIM EDILEN videoya ait OLMAYAN bir kanit tasiyordu.
    # ⚠ Olcum modulleri DEGISMEDI; degisen tek sey GIRDI ve ZAMANLAMA.
    _render_qa = {}
    try:
        import gercek_qa
        _render_qa = gercek_qa.olc(
            gercek_qa.sahneleri_cevir(
                props_sahneler, kok_dizin=PUBLIC,
                provenans_okuyucu=kaynak.stok_provenans_al,
                olgu_raporu=_fact_rapor),
            kare_okuyucu=_kare_sayisi_oku)
        print(f"  RENDER-QA (gercek timeline): {_render_qa.get('durum')} "
              f"sahne={_render_qa.get('sahne')} "
              f"kapsam={(_render_qa.get('kapsam') or {}).get('kapsam_orani')} "
              f"gercek_video={_render_qa.get('gercek_video_orani')}",
              file=sys.stderr)
    except Exception as e:                                   # noqa: BLE001
        # ⚠ Olcum patlarsa "PASS" DENMEZ; durum ACIKCA OLCULEMEDI olur.
        _render_qa = {"durum": "OLCULEMEDI",
                      "neden": f"{type(e).__name__}: {str(e)[:120]}"}
        print(f"  RENDER-QA olculemedi: {_render_qa['neden']}", file=sys.stderr)

    ham = os.path.join(STUDYO, "out", f"{is_adi}.mp4")
    os.makedirs(os.path.join(STUDYO, "out"), exist_ok=True)

    # ── HIZLI MOTOR (ffmpeg, Chrome'suz — ~8x hizli) ──
    # Acma: env RENDER_MOTOR=ffmpeg VEYA /opt/vidrush/RENDER_MOTOR dosyasina "ffmpeg" yaz
    # (docker exec ile konteyner yeniden yaratmadan). Kapsam disi is/hata -> Remotion'a duser.
    motor = os.environ.get("RENDER_MOTOR", "")
    if not motor:
        try:
            with open(os.path.join(KOK_YOL, "RENDER_MOTOR")) as f:
                motor = f.read().strip()
        except Exception:
            motor = ""
    hizli_ok = False
    if motor == "ffmpeg":
        try:
            import hizli_render
            hizli_ok = hizli_render.ffmpeg_render(is_adi, props, ham, ilerle=bildir)
        except Exception as e:
            print(f"  hizli motor hata: {str(e)[:200]}", file=sys.stderr)
        if not hizli_ok:
            print("  hizli motor kullanilamadi -> Remotion ile devam", file=sys.stderr)

    # Full HD 1080p 16:9 (kompozisyon 1920x1080, scale YOK). Web aracinda boyut limiti yok.
    # concurrency ortamdan (Hetzner cok cekirdek): REMOTION_CONCURRENCY.
    konk = os.environ.get("REMOTION_CONCURRENCY", "1")
    if not hizli_ok:
        komut = ["npx", "remotion", "render", "src/index.ts", "VidrushVideo", ham,
                 f"--props={props_yolu}", f"--concurrency={konk}", "--timeout=180000",
                 # HD indirme: crf 23 -> 18 (bit hizi ~3 Mbps'ten ~8-10 Mbps'e cikar, YouTube 1080p
                 # onerisi 8 Mbps). Render suresine etkisi kucuk (darbogaz Chromium kare uretimi).
                 # jpeg-quality 100 = kare yakalama kaybi yok.
                 f"--crf={os.environ.get('RENDER_CRF','18')}", "--x264-preset=faster",
                 # 100->90: kare yakalama belirgin hizlanir, gozle gorulur kalite farki yok
                 "--jpeg-quality=90"]
        if os.environ.get("REMOTION_BROWSER_EXECUTABLE"):
            komut.append(f"--browser-executable={os.environ['REMOTION_BROWSER_EXECUTABLE']}")
        if os.environ.get("REMOTION_GL"):
            komut.append(f"--gl={os.environ['REMOTION_GL']}")
        # ⚠ FAZ Y-2 / Y2-RENDER-TIMEOUT — BUTCE 1080p30 GERCEGINE GORE.
        # OLCULEN KUSUR (is job_1786784567124_ui8120_aea2e9): icerik TAM
        # hedefteydi (footage 17/17, gercek_video=1.0, AI gorsel 0, magnific
        # 0) ama render 30 dk butcesine sigmadi ve video KAYBEDILDI:
        #     RuntimeError: Render zaman aşımına uğradı (30 dk)
        # Eski formul (`sure_dk * 720`, min 1800) 24 fps donemine aitti.
        # UI-8 ile render 30 fps'e cikti (POST-QA ile hizalanmak icin) ve
        # kare sayisi ~%25 artti; 17 segmentlik 1080p30 kompozisyon 30 dk'ya
        # SIGMIYOR. Butce: min 60 dk, video dakikasi basina ~25 dk duvar.
        # ⚠ Kalite kapilari GEVSETILMEDI; yalnizca zaman butcesi buyudu.
        # Tavan 13 saat AYNEN korunuyor (sonsuz bekleme YOK).
        render_timeout = int(min(46800, max(3600, sure_dk * 1500)))
        try:
            sonuc = subprocess.run(komut, cwd=STUDYO, capture_output=True, text=True,
                                   timeout=render_timeout)
        except subprocess.TimeoutExpired as e:
            # yetim remotion/chromium cocuklarini temizle ki kuyruk tikanmasin
            try:
                subprocess.run(["pkill", "-9", "-f", "remotion"], timeout=20)
                subprocess.run(["pkill", "-9", "-f", "chrome"], timeout=20)
            except Exception:
                pass
            cikti = (e.stderr or b"")
            if isinstance(cikti, bytes):
                cikti = cikti.decode("utf-8", "ignore")
            print(cikti[-2000:], file=sys.stderr)
            raise RuntimeError(f"Render zaman aşımına uğradı ({render_timeout//60} dk). "
                               "Daha kısa süre deneyin.")
        if sonuc.returncode != 0:
            print(sonuc.stderr[-2000:], file=sys.stderr)
            raise RuntimeError("Remotion render basarisiz")

    # ── SES EFEKTLERI (7 Agu 2026, "Ultimate 500 Preset Pack" bonusundan) ──
    # Pakette 18 ses efekti vardi; belgesele UYMAYAN oyun sesleri (minecraft, kilic,
    # para sayaci) atildi, kalan 13'u -18 LUFS mono 48 kHz'e normalize edilip
    # /opt/vidrush/sfx altina konuldu. -18 LUFS bilincli: anlati -14'te, efekt onun
    # ALTINDA kalmali; ustune cikarsa amatör durur.
    # Efekt HER kesmeye konmaz — referans kanallarda da yok. Anlatim islevine bagli
    # ve seyrek: vurgu -> impact, liste -> kisa whoosh, gecmis -> projektor, sonuc -> riser.
    # ⚠ FAZ Y-14: `sfx_bindir` artik (video, olcum) doner. Olcum ducking
    # zarfini tasir ve render sonrasi ses olcumune GECIRILIR — eskiden
    # bindirilen SFX sayisi yalnizca stderr'e basiliyordu (Y14-SFX-OLCUM-KAYIP).
    _sfx_olcum = {"bindirilen": 0, "olculdu": False,
                  "kod": KOD_SFX_DIZIN_YOK, "ducking_zarfi": []}
    try:
        ham, _sfx_olcum = sfx_bindir(ham, props_sahneler, is_dizini)
    except Exception as e:
        _sfx_olcum = {"bindirilen": 0, "olculdu": False,
                      "kod": KOD_SFX_BINDIRME_BASARISIZ,
                      "ducking_zarfi": [], "neden": str(e)[:150]}
        print(f"  sfx atlandi: {str(e)[:150]}", file=sys.stderr)

    bildir("Ses seviyesi ayarlanıyor...", 96)
    son_video = os.path.join(CIKTI_DIR, f"{is_adi}.mp4")
    # ── SES NORMALIZASYONU (4 Agu 2026) ──
    # Olculdu: cikti -15.80 LUFS, YouTube -14 LUFS'a normalize ediyor -> videomuz
    # rakiplerden 1.8 dB kisik caliyordu. Tek gecisli loudnorm ile hedefe cekilir.
    # GORUNTU YENIDEN KODLANMAZ (-c:v copy) -> ek sure ~saniyeler, kalite kaybi yok.
    # Basarisiz olursa ham dosya oldugu gibi kopyalanir; video ASLA kaybolmaz.
    # ZINCIR (preset paketindeki ses presetlerinin ffmpeg karsiligi):
    #   highpass 80 Hz  = "Anti Mic Rumble" (TTS'te de dusuk frekans cop var)
    #   deesser         = "DeEsser" (s/ş sesleri tizde bicak gibi ciktigi icin)
    #   loudnorm -14    = YouTube hedefi
    #   alimiter        = "Hard Limiter" (tepe noktalari kirpilmadan tutulur)
    # acompressor: NORMALIZASYONDAN ONCE tepe-ortalama farkini daraltir.
    # NEDEN (11 Agu 2026 olcumu): iki gecisli loudnorm kurdum ama cikti yine -15.6
    # LUFS geldi. Sebep kaynak: ham ses -21.97 LUFS ve tepeleri yuksek; -14'e cikmak
    # icin +8 dB gerekiyor, bu da TP'yi -1.5'in ustune atacagi icin loudnorm
    # kendini kisiyor (linear mod dinamige duser ve hedefi tutturamaz).
    # Hafif kompresyon (3:1, -18 dB esik) tepeleri toparlar, +8 dB sigar.
    ON_ZINCIR = ("highpass=f=80,deesser=i=0.35:m=0.5:f=0.18,"
                 "acompressor=threshold=-18dB:ratio=3:attack=8:release=140:makeup=2")

    # ── IKI GECISLI LOUDNORM (11 Agu 2026) ──
    # Tek gecisli loudnorm AKIS halinde calisiyor: dosyanin tamamini gormeden
    # kademeli duzeltiyor ve hedefi tutturamiyor. Olcum: hedef -14 istenirken
    # cikti -15.9 LUFS, yani 4 Agu'daki -15.8'den neredeyse hic iyilesme yok —
    # "duzeltildi" sandigim sey calismiyordu.
    # Dogru yontem: 1. gecis SADECE OLCER (print_format=json), 2. gecis olculen
    # degerleri parametre olarak alir ve tek adimda tam hedefe getirir.
    olculen = {}
    try:
        r_olc = subprocess.run(
            ["ffmpeg", "-hide_banner", "-nostdin", "-i", ham, "-af",
             f"{ON_ZINCIR},loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json",
             "-f", "null", "-"], capture_output=True, text=True, timeout=1800)
        blok = r_olc.stderr[r_olc.stderr.rfind("{"):r_olc.stderr.rfind("}") + 1]
        olculen = json.loads(blok)
        print(f"  ses olcumu: {olculen.get('input_i')} LUFS -> hedef -14", file=sys.stderr)
    except Exception as e:
        print(f"  ses olcumu basarisiz, tek gecise dusuluyor: {str(e)[:100]}", file=sys.stderr)

    if olculen.get("input_i"):
        ln = ("loudnorm=I=-14:TP=-1.5:LRA=11:linear=true"
              f":measured_I={olculen['input_i']}"
              f":measured_TP={olculen['input_tp']}"
              f":measured_LRA={olculen['input_lra']}"
              f":measured_thresh={olculen['input_thresh']}"
              f":offset={olculen.get('target_offset', '0.0')}")
    else:
        ln = "loudnorm=I=-14:TP=-1.5:LRA=11"

    ses_ok = False
    try:
        r_ses = subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", ham,
             # alimiter loudnorm'dan SONRA gelir ama artik "level=disabled" ile
             # seviyeyi degistirmiyor, sadece tepe kirpmayi onluyor.
             "-af", f"{ON_ZINCIR},{ln},alimiter=limit=0.95:level=disabled",
             "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", son_video],
            capture_output=True, text=True, timeout=1800)
        ses_ok = (r_ses.returncode == 0 and os.path.exists(son_video)
                  and os.path.getsize(son_video) > 1024)
        if not ses_ok:
            print(f"  loudnorm basarisiz, ham kopyalanacak: {r_ses.stderr[-200:]}", file=sys.stderr)
    except Exception as e:
        print(f"  loudnorm atlandi: {str(e)[:140]}", file=sys.stderr)
    if not ses_ok:
        shutil.copy(ham, son_video)

    bildir("Tamamlanıyor...", 98)
    son_kapak = None
    if kapak_yolu and os.path.exists(kapak_yolu):
        son_kapak = os.path.join(CIKTI_DIR, f"{is_adi}_kapak.png")
        shutil.copy(kapak_yolu, son_kapak)

    sonuc = {"video": f"{is_adi}.mp4",
             "kapak": f"{is_adi}_kapak.png" if son_kapak else None,
             "sure": round(sum(s["sure"] for s in props_sahneler), 1),
             "sahne_sayisi": len(props_sahneler),
             "edit": prof["ad"],
             # ⚠ FAZ Y-8 / Y8-HEDEF-SURE: KULLANICININ ISTEDIGI SURE.
             # Is boyunca KAYIPSIZ tasinir ve POST-QA'da BAGLAYICI olur.
             # Olculen kusur: hedef hicbir yere yazilmadigi icin 96 sn
             # istenen bir iste 83.5 sn cikti uretildi ve POST-QA "temiz"
             # dedi (yalnizca uretilmis timeline'in KENDI toplamina
             # bakiyordu). Kayiplarin kaynagi ayri (taban yuvarlama, %92
             # butce tolerani, kelime tavani, dusen TTS sahnesi) — bu alan
             # onlari GORUNUR ve HESAP VERILEBILIR kilar.
             "hedef_sure_sn": round(float(sure_dk) * 60.0, 1),
             # CC kliplerin atif metni. Lisans atfi ACIKLAMADA istiyor; ekrandaki kucuk
             # kunye yazisi ek. Bu liste bos ise videoda CC klip kullanilmamis demektir.
             "atiflar": kaynak.atif_listesi(),
             # ── FAZ H: arastirma sonucu ise YAZILIR ──
             # Wizard Adim 4'te "Guvenilir kaynak sayisi / Dogrulanmis iddia ->
             # Uretim sirasinda hesaplanacak" YAZIYORDU ama hicbir zaman
             # hesaplanmiyordu. Artik gercek sayilar burada.
             "arastirma": arastirma_sonuc.sozluk(),
             "kaynaklar": arastirma_kopru.atif_satirlari(
                 CIKTI_DIR, arastirma_sonuc.manifest_dosya),
             # Gorunur dusus kayitlari: hangi asamada neden geri duselduği.
             "dususler": list(arastirma_sonuc.dususler),
             # ⚠ FAZ R-1d-e: RENDER EDILEN zaman cizgisinin PRE-QA'si.
             # Teslim zinciri `pre_qa` kanitini BURADAN okur; `edit_plani`
             # (render EDILMEYEN alternatif plan) kanit SAYILMAZ.
             "render_qa": _render_qa}
    # ── FAZ I-8: OLGU BAGI OZETI (yalnizca bag KURULDUYSA yazilir) ──
    # ⚠ Arastirma kapaliysa anahtar HIC eklenmez -> eski islerde `sonuc`
    # bit-bit ayni. Kapsam bosluklari GORUNUR: "her sahne kaynakli" gibi
    # kanitsiz iddia uretilmez.
    if _fact_rapor is not None:
        sonuc["olgu_bagi"] = _fact_rapor
        for _b in _fact_rapor["bosluklar"][:20]:
            sonuc["dususler"].append({
                "asama": "olgu-bagi", "neden": _b["neden"],
                "etki": (f"sahne {_b['sahne']} dogrulanmis bir iddiaya "
                         f"baglanamadi; medya secimi genel sorguyla yapildi")})
    # ── FAZ I-6: MEDYA AVCISI OZETI (yalnizca ACIKKEN yazilir) ──
    # ⚠ Kapaliyken anahtar HIC eklenmez -> eski islerde `sonuc` bit-bit ayni.
    # Acikken kapinin hic calismadigi durum da GORUNUR (denenen=0), boylece
    # "avci kullandik" gibi kanitsiz iddia uretilmez.
    if _avci_acik and _avci_butce is not None:
        sonuc["medya_avcisi"] = _avci_butce.ozet()
        sonuc["dususler"].extend(_avci_butce.dususler())
    # ── FAZ I-10: EDITORV2 PLAN ORKESTRASYONU (OPT-IN, RENDER YOK) ──
    # ⚠ Bu blok RENDER ETMEZ. Yalnizca plan/props ve karar ozeti uretir;
    # gercek render MEVCUT `VidrushVideo` yoluyla zaten yapildi.
    # ⚠ Manifest YALNIZCA avci GERCEKTEN lisansli + kare-dogrulanmis aday
    # verdiyse kurulur; aksi halde plan denenmez (uydurma manifest yok).
    _ed_acik, _ed_gerekce = edit_kopru.acik_mi(_is_ayar)
    if _ed_acik:
        try:
            _manifest = (medya_kopru.manifest_kur(_avci_butce)
                         if _avci_butce is not None else
                         {"adaylar": [], "kapsam_bosluklari": []})
            if not (_manifest.get("adaylar") or []):
                sonuc["edit_plani"] = {
                    "ok": False, "neden": "MEDYA-YOK",
                    "aciklama": ("avci lisansli + kare dogrulanmis aday "
                                 "vermedi; plan denenmedi"),
                    "render_edilebilir": False}
            else:
                _ep = edit_kopru.plan_kur(
                    cumleler=[{"scene_id": str(x.get("scene_id") or ""),
                               "fact_id": str(x.get("fact_id") or ""),
                               "sure_sn": float(x.get("sure") or 0),
                               "metin": str(x.get("anlatim") or "")}
                              for x in props_sahneler],
                    medya_manifest=_manifest,
                    # ⚠ FAZ R-1d-c: GERCEK VIDEO ORANI icin KARE OKUYUCU.
                    # Medya turu olcumu dosya ACMAZ; kare
                    # sayisini DISARIDAN ister. Okuyucu verilmeyince olcum
                    # `KARE-OKUYUCU-YOK` ile duruyordu ve "gercek video
                    # orani" HIC olculemiyordu (R-1d-b pilot 3'te olculdu).
                    # ⚠ UCRETSIZ ve YEREL: yalnizca ffprobe; ag/kredi YOK.
                    kare_okuyucu=_kare_sayisi_oku,
                    olgular=list(getattr(arastirma_sonuc, "olgular", None)
                                 or []),
                    stil=None, cikti_dizin=CIKTI_DIR, is_ayar=_is_ayar)
                sonuc["edit_plani"] = {
                    "ok": _ep["ok"], "neden": _ep["neden"],
                    "render_edilebilir": _ep["render_edilebilir"],
                    "qa": _ep["qa"], "profil": _ep["profil_adi"],
                    "elenen_medya": len(_ep["elenen_medya"]),
                    "kapsam_boslugu": len(_ep["kapsam_bosluklari"]),
                    "efekt_kapsami": (_ep["efekt_kapsami"] or {}).get("sayim"),
                    "sahne": len((_ep["props"] or {}).get("sahneler") or []),
                    "uyarilar": _ep["uyarilar"][:10]}
                _qa_durum = (_ep["qa"] or {}).get("durum", "?")
                print(f"  EDIT PLANI ({_ed_gerekce}): QA={_qa_durum} "
                      f"render_edilebilir={_ep['render_edilebilir']} "
                      f"sahne={sonuc['edit_plani']['sahne']}",
                      file=sys.stderr)
        except Exception as e:
            # ⚠ KONTROLLU FALLBACK: plan hatasi uretimi BOZMAZ.
            sonuc["edit_plani"] = {"ok": False, "neden": "HATA",
                                   "aciklama": f"{type(e).__name__}",
                                   "render_edilebilir": False}
            print(f"  edit plani kurulamadi: {type(e).__name__}",
                  file=sys.stderr)
    # ── FAZ I-2c: BILESIK STIL PROFILI KUNYESI (yalnizca VARSA yazilir) ──
    # ⚠ I-2b'nin kapattigi acik: "bir stilin sahne_sn'i degisince dun uretilmis
    # is yeniden uretilemez; hangi ayarla ciktigi kayitli degildi." Kunye o
    # kaydin ta kendisi: kimlik + profil surumu + sema surumu.
    # Eski stil girdilerinde `_profil` YOKTUR -> anahtar HIC eklenmez, yani
    # eski isler icin `sonuc` sozlugu bit-bit ayni kalir.
    _stil_ek = profil_ek_oku(prof)
    if _stil_ek:
        sonuc["stil_profili"] = {
            "kimlik": prof.get("_stil_kimligi") or edit_id or "",
            "surum": _stil_ek.get("surum") or "",
            "sema_surum": getattr(stil_profili, "SEMA_SURUM", ""),
            "boyutlar": sorted(k for k in _stil_ek if k != "surum"),
        }
        # ── FAZ I-2d: GORSEL IMZA IZLENEBILIRLIGI ──
        # Hangi efektin/gecisin NEDEN uygulandigi ise yazilir; "efekt yok"
        # durumu da gerekcesiyle gorunur (sessiz kalite kaybi yok).
        _gi_ozet = bilesik_gorsel_imza(_stil_ek)
        sonuc["stil_profili"]["gorsel_imza"] = {
            "uygulandi": _gi_ozet["uygulandi"],
            "efektler": _gi_ozet["efektler"],
            "gecis_imza": _gi_ozet["gecis_imza"],
            "gecis_oran": _gi_ozet["gecis_oran"],
            "gerekce": _gi_ozet["gerekce"],
        }
    # ── FAZ H: MEDYA KAPISI — reddedilen adaylar GORUNUR olur ──
    # Sessiz dusus yasak: kapi bir klibi attiysa kullanici NEDEN atildigini
    # gorebilmeli. Uydurma yok, gercek red kayitlari.
    # ── FAZ H: KALITE KAPISI — render sonrasi GERCEK olcum ──
    # ⚠ editor/qa_son.py Faz C'de yazilmisti ama pipeline onu HIC cagirmiyordu;
    # is sozlesmesindeki `qa` alani HER ZAMAN bos sozlukttu ve video hicbir
    # olcumden gecmeden "Hazir!" diye teslim ediliyordu.
    # FAIL ise is basarili GORUNMEZ (bkz. is_sozlesme.kalite_durumu) ve
    # UCRETSIZ + DETERMINISTIK bir duzeltme (ses remaster) denenir.
    try:
        _qa = qa_kopru.denetle(
            son_video, bildir=bildir,
            # ⚠ FAZ Y-8 / Y8-HEDEF-SURE — IKI AYRI OLCUT.
            # `sure_sn` URETILMIS timeline toplamidir; ona karsi olcmek
            # yalnizca "render plandan kisaldi mi" der. KULLANICININ
            # ISTEDIGI SURE bugune kadar POST-QA'da HIC denetlenmiyordu:
            # gercek iste 96 sn istendi, 83.5 sn uretildi ve POST-QA TEMIZ
            # gecti. `hedef_sure_sn` kullanici hedefini KAYIPSIZ tasir ve
            # `qa_son` ona karsi FAIL-CLOSED olcer.
            beklenen={"sure_sn": sonuc["sure"],
                      "hedef_sure_sn": sonuc.get("hedef_sure_sn"),
                      "cekim_sayisi": sonuc["sahne_sayisi"],
                      "genislik": 1920, "yukseklik": 1080})
        sonuc["qa"] = qa_kopru.ozet(_qa)
        sonuc["dususler"].extend(qa_kopru.dususe_cevir(_qa))
    except Exception as e:
        # QA HATTI COKERTMEZ — video yine teslim edilir, ama PASS DENMEZ.
        print(f"  QA kopru hatasi: {str(e)[:120]}", file=sys.stderr)
        sonuc["qa"] = {"durum": "OLCULEMEDI", "not": str(e)[:160]}

    # ── FAZ Y-13b / Y13B-OLCUM-RENDER-SONRASI — SES KURGUSU OLCUMU ──
    # ⚠ OLCULEN KUSUR: `gercek_qa.olc` (yukarida) RENDER'DAN ONCE kosar —
    # kapsam/provenans icin bu DOGRUDUR (R-1d-e). Ama J/L-cut RENDER
    # SIRASINDA uretilir; eski kod onu `hizli_render._JL_SON` modul
    # global'inden okuyordu ve o an deger HENUZ YAZILMAMISTI. Teslim
    # raporundaki `ses.j_l_cut` hicbir zaman o ise ait degildi.
    #
    # ⚠ Y13B-DAMGA-SON-ARTEFAKT (denetim, 15 Agu): olcumu render'in hemen
    # ardina koymak da YETMEZ. `ham` dosyasi bu noktadan sonra EN AZ UC KEZ
    # yeniden yaziliyor:
    #     1. `sfx_bindir`            (SFX bindirme)
    #     2. ses normalizasyonu       -> `son_video`
    #     3. `qa_kopru.denetle`       (ses remaster'i dosyayi YERINDE ezer)
    # Bu yuzden damga BU NOKTADA, yani TUM post islemler bittikten sonra,
    # GERCEKTEN TESLIM EDILECEK `son_video` uzerinde yenilenir. Aksi halde
    # kabul degerlendiricisinin karsilastirdigi sha256, indirilen MP4'un
    # ozetiyle TUTMAZ ve olcum sessizce baska bir dosyaya ait olur.
    # ⚠ Video akisi bu adimlarda YENIDEN KODLANMAZ (`-c:v copy`), yani
    # kesme yapisi ve J/L sayisi DEGISMEZ; degisen yalnizca kapsayici ve
    # ses akisidir. Damga bu yuzden yenilenebilir — sayi yeniden uretilmez,
    # yalnizca NIHAI artefakta yeniden BAGLANIR.
    try:
        import gercek_qa as _gq_son
        _jl_rapor, _artefakt_ozet = {}, ""
        if hizli_ok:
            import hizli_render as _hr_son
            # ⚠ NIHAI dosyaya yeniden damgala; basarisizsa rapor damgasiz
            # kalir ve olcum "olculmedi" doner (fail-closed).
            _hr_son.jl_damgala(is_adi, son_video)
            _jl_rapor = _hr_son.render_raporu(is_adi)
            _artefakt_ozet = str(_jl_rapor.get("artefakt_sha256") or "")
        _ses_son = _gq_son.ses_kurgu_olcumu(
            _gq_son.sahneleri_cevir(
                props_sahneler, kok_dizin=PUBLIC,
                provenans_okuyucu=kaynak.stok_provenans_al,
                olgu_raporu=_fact_rapor),
            jl_raporu=_jl_rapor or None,
            artefakt_sha256=_artefakt_ozet,
            ducking_zarfi=(_sfx_olcum or {}).get("ducking_zarfi"),
            ducking_olcum=(_sfx_olcum or {}).get("ducking_olcum"))
        if isinstance(_render_qa, dict):
            _render_qa["ses"] = _ses_son
            _olc = _render_qa.get("olcumler")
            if isinstance(_olc, dict):
                _olc["ses"] = _ses_son
        # ── FAZ Y-17: KAYNAK SESI MUTLAK SIFIR, GRAF KANITIYLA ──
        # ⚠ Metadata beyani DEGIL: her basarili segmentin URETILEN
        # komutundan cikarilan kaynak-ses map kaniti okunur ve graf
        # TAMLIGI (kayit sayisi == render edilen sahne sayisi) aranir.
        _ses_sifir = _gq_son.kaynak_ses_olcumu(
            ses_raporu=_jl_rapor or None,
            artefakt_sha256=_artefakt_ozet,
            beklenen_segment=len(props_sahneler or []),
            # ⚠ Y-17: SAYISAL stem olcumu (en kotu segment) rapordan gelir;
            # yoksa kriter "olculmedi" kalir ve KABUL URETMEZ.
            leakage_db=(_jl_rapor or {}).get("kaynak_ses_leak_db"),
            sample_peak=(_jl_rapor or {}).get("kaynak_ses_peak"))
        if isinstance(_render_qa, dict):
            _render_qa["kaynak_ses"] = _ses_sifir
        sonuc["kaynak_ses"] = _ses_sifir
        print(f"  RENDER-SONRASI KAYNAK-SES: "
              f"olculdu={_ses_sifir.get('olculdu')} "
              f"graf_tam={_ses_sifir.get('graf_tam')} "
              f"sizinti={_ses_sifir.get('sizinti')} "
              f"segment={_ses_sifir.get('segment')} "
              f"kod={_ses_sifir.get('kod') or '-'}", file=sys.stderr)

        # ── FAZ Y-16: ORTALAMA PLAN SURESI, RENDER EDILEN CEKIMLERDEN ──
        # ⚠ Sahne suresinden TURETILMEZ: `_cekim_planla` sahneyi 8 sn
        # tavaniyla bolen gercek cekimleri uretir ve onlari kaydeder.
        _ritim = _gq_son.ritim_olcumu(cekim_raporu=_jl_rapor or None,
                                      artefakt_sha256=_artefakt_ozet)
        if isinstance(_render_qa, dict):
            _render_qa["ritim"] = _ritim
        sonuc["ritim"] = _ritim
        print(f"  RENDER-SONRASI RITIM: olculdu={_ritim.get('olculdu')} "
              f"ort={_ritim.get('ort_plan_sn')} sn "
              f"cekim={_ritim.get('cekim')} "
              f"bant_ici={_ritim.get('band_ici')} "
              f"kod={_ritim.get('kod') or '-'}", file=sys.stderr)
        sonuc["artefakt_sha256"] = _artefakt_ozet
        sonuc["sfx"] = dict(_sfx_olcum or {})
        print(f"  RENDER-SONRASI SES (nihai artefakt): "
              f"olculdu={_ses_son.get('olculdu')} "
              f"J/L={_ses_son.get('j_l_cut')} tam={_ses_son.get('tam')} "
              f"sha={_artefakt_ozet[:12] or '-'} "
              f"kod={_ses_son.get('kod') or '-'}", file=sys.stderr)
    except Exception as e:                                   # noqa: BLE001
        # ⚠ Olcum patlarsa PASS DENMEZ: alan acikca "olculemedi" kalir.
        if isinstance(_render_qa, dict):
            _render_qa["ses"] = {
                "olculdu": False, "tam": False,
                "kod": "GERCEK-TIMELINE-JL-OLCULMEDI",
                "neden": f"{type(e).__name__}: {str(e)[:120]}"}
        print(f"  RENDER-SONRASI SES olculemedi: {type(e).__name__}",
              file=sys.stderr)
        sonuc["dususler"].append({
            "asama": "qa", "neden": f"{type(e).__name__}",
            "etki": "Kalite ölçümü yapılamadı; PASS olduğu varsayılmıyor."})

    try:
        _redler = kaynak.kapi_redleri()
        if _redler:
            sonuc["medya_kapisi"] = {"red_sayisi": len(_redler),
                                     "redler": _redler[:12]}
            sonuc["dususler"].append({
                "asama": "medya",
                "neden": f"{len(_redler)} aday biyom/donem celiskisi ile reddedildi",
                "etki": "Yanlis iklim/donem gorseli kullanilmadi; sahneler "
                        "uygun klip ya da kapsam bosluğu olarak islendi."})
    except Exception as e:
        print(f"  kapi redleri okunamadi: {str(e)[:80]}", file=sys.stderr)

    # Faz I-1: KARE KAPISI ozeti — olculmus, uydurma yok. Kapi kapaliysa ya da
    # hic cagri yapilmadiysa bunu DURUSTCE yazar; "her kare dogrulandi" demez.
    try:
        _kare = kaynak.kare_ozet()
        sonuc["kare_kapisi"] = _kare
        if _kare.get("red_sayisi"):
            sonuc["dususler"].append({
                "asama": "medya",
                "neden": f"{_kare['red_sayisi']} aday KARE dogrulamasinda reddedildi "
                         f"(yer/donem/biyom celiskisi)",
                "etki": "Metin kapilarindan gecen ama karesi sahneyle celisen "
                        "klipler kullanilmadi."})
        for _eng in (_kare.get("butce") or {}).get("engel", [])[:1]:
            sonuc["dususler"].append({
                "asama": "medya",
                "neden": f"kare kapisi butcesi: {_eng}",
                "etki": "Kalan klipler kare dogrulamasi OLMADAN gecti — "
                        "yer isabeti bu klipler icin garanti degil."})
    except Exception as e:
        print(f"  kare ozeti okunamadi: {str(e)[:80]}", file=sys.stderr)
    uyarilar = []
    if plan.get("_eksik_oran"):
        uyarilar.append(f"İçerik planı beklenenden kısa çıktı (~%{int(plan['_eksik_oran']*100)}).")
    if plan.get("_render_eksik"):
        u, p = plan["_render_eksik"]
        uyarilar.append(f"Planlanan {p} sahnenin {u} tanesi üretilebildi; video beklenenden kısa olabilir.")
    if plan.get("_bakiye_kesildi"):
        uyarilar.append(f"OpenAI bakiyesi/limiti üretim sırasında doldu — {plan['_bakiye_kesildi']} "
                        "sahne kurtarıldı ve videoya dönüştürüldü (harcanan para boşa gitmedi). "
                        "Kredi yükleyip tam sürümü tekrar üretebilirsiniz.")
    if uyarilar:
        sonuc["uyari"] = " ".join(uyarilar) + " Metni sadeleştirip tekrar deneyebilirsiniz."
    return sonuc


async def uret_seslendir(metin, ses, yol, deneme=3, ayar=None):
    """DAYANIKLI TTS. edge-tts agdan cekilir; gecici hata/bos metin olursa TEKRAR dener.
    Basarisiz ya da bos/bozuk ses dosyasi -> (None, None) doner ki cagiran o sahneyi
    ATLASIN (tek TTS hicgirigi tum 30dk isi oldurmesin). Basarida (kelimeler, sure)."""
    metin = (metin or "").strip()
    if not metin:
        return None, None
    son = None
    for d in range(deneme):
        try:
            # asyncio.wait_for: yari-acik TCP baglantisi edge-tts stream'ini SONSUZA dek
            # bekletebilir (retry sadece exception'da calisir). 120s tavan -> hata firlar ->
            # retry devreye girer -> tum kuyruk sonsuza kilitlenmez.
            kelimeler, sure = await asyncio.wait_for(
                uretmod.seslendir(metin, ses, yol, ayar), timeout=240)
            # Remotion'un <Audio> cozebilmesi icin dosya gercekten yazilmis olmali
            if os.path.exists(yol) and os.path.getsize(yol) > 1024:
                return kelimeler, sure
            son = RuntimeError("bos/kucuk ses dosyasi")
        except Exception as e:
            son = e
            print(f"  seslendir retry {d+1}/{deneme}: {str(e)[:120]}", file=sys.stderr)
        await asyncio.sleep(3 * (d + 1))
    print(f"  seslendir BASARISIZ (sahne atlanacak): {str(son)[:160]}", file=sys.stderr)
    return None, None
