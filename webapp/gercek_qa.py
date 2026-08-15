#!/usr/bin/env python3
"""FAZ R-1d-e — PRE-QA KANITI **RENDER EDILEN** ZAMAN CIZGISINDEN URETILIR.

⚠ OLCULEN KUSUR (R-1d-d pilotu, job_1786717796777):
`uret()` icinde sira soyleydi —
    4655  hizli_render.ffmpeg_render(is_adi, props, ...)   <- VIDEO BURADA RENDER EDILIR
    4822  editorv2 plan blogu                              <- PRE-QA BURADA KOSAR
Yani PRE-QA, video ZATEN render edildikten SONRA, **hicbir zaman render
EDILMEYEN** alternatif bir plani olcuyordu (kodun kendi yorumu: "Bu blok
RENDER ETMEZ"). Iki artefakt olcumle ayrisiyordu:

    teslim edilen MP4 : 8 sahne · POST-QA 8 kesme · 64.8 sn
    PRE-QA'nin plani  : 16 cekim · kapsam {medya:8, fallback:8, oran:0.5}

Sonuc: teslim zincirinin `pre_qa` halkasi, TESLIM EDILEN videoya ait
OLMAYAN bir kanit tasiyordu. O plandaki `kapsam_orani`'ni yukseltmek MP4'u
iyilestirmez; halkayi PASS'a dondurmek ise YANLIS BIR KABUL SINYALI uretir.

Bu modul o bosluktur: **render EDILEN sahne listesinden** (`props_sahneler`)
olcum uretir ve render **ONCESINDE** kosar.

⚠ OLCUM MODULLERI DEGISMEDI. `editor.kalite_kapisi` ve `editor.ses_gurultu`
AYNEN kullanilir; degisen tek sey GIRDI: hayali plan yerine gercek zaman
cizgisi.

⚠ UYDURMA YOK — TURETILEMEYEN OLCUM URETILMEZ. Gercek hat sahnelere
`cekim_turu` (establishing/medium/close-detail...) ATAMAZ; onun yerine
`zoom`/`pan` kararlari vardir. Bu yuzden CEKIM TURU tabanli B-roll gorsel
dili olcumu bu zaman cizgisinde UYGULANAMAZ ve stabil kodla bildirilir:
`GERCEK-TIMELINE-CEKIM-TURU-YOK`. Sahte bir cekim turu URETILMEZ.

⚠ Bu modul AG ACMAZ, MEDYA ACMAZ, DOSYA YAZMAZ, RENDER ETMEZ. Kare sayaci
ve provenans okuyucusu DISARIDAN enjekte edilir.
"""
from __future__ import annotations

import os
from typing import Callable, Optional

from editor import kalite_kapisi as _kk
from editor import ses_gurultu as _sg

SEMA_SURUM = "1.0.0"

# ── STABIL HATA/DURUM KODLARI (deterministik politika) ──
KOD_CEKIM_TURU_YOK = "GERCEK-TIMELINE-CEKIM-TURU-YOK"
KOD_PROVENANS_YOK = "GERCEK-TIMELINE-PROVENANS-YOK"
KOD_SAHNE_YOK = "GERCEK-TIMELINE-SAHNE-YOK"
KOD_GECIS_YOK = "GERCEK-TIMELINE-GECIS-YOK"
# ⚠ FAZ Y-15 (`Y15-GECIS-TUR-OLCUMU-YOK`): `imza_dagilimi` uretiliyordu ama
# TUR SAYISI ve ESIK yoktu; hicbir kapi ">=3 gecis turu" sartini
# denetlemiyordu.
KOD_GECIS_TUR_AZ = "GERCEK-TIMELINE-GECIS-TUR-AZ"
# ⚠ Esik TEK KAYNAKTAN okunur — kabul kriteri ve hat ile AYNI deger.
GECIS_TURU_ASGARI = 3
KOD_DUCKING_YOK = "GERCEK-TIMELINE-DUCKING-VERISI-YOK"
# ⚠ FAZ Y-14b: yapilandirma degeri KANIT DEGIL — gercek gain
# reduction olculmediginde bu kod doner.
KOD_DUCKING_GAIN_OLCULMEDI = "DUCKING-GAIN-OLCULMEDI"
# ⚠ FAZ Y-13a — J/L olcumu artik ENJEKTE edilir; bayat modul global'i
# (`hizli_render._JL_SON`) KANIT SAYILMAZ. Bkz. `ses_kurgu_olcumu`.
KOD_JL_OLCULMEDI = "GERCEK-TIMELINE-JL-OLCULMEDI"
KOD_JL_BAYAT = "GERCEK-TIMELINE-JL-BAYAT"

# Bir isin "tam" sayilmasi icin gereken en az gercek J/L-cut sayisi.
# ⚠ `editor/qa_on.JL_EN_AZ` ile AYNI deger; orada plan uzerinden, burada
# URETILEN artefakt uzerinden olculur.
JL_EN_AZ = 2

# Kapilar. ⚠ Esikler MEVCUT kaynaklardan OKUNUR, burada YENIDEN TANIMLANMAZ.
KAYNAK_TAVANI_SN = _kk.KAYNAK_BASINA_TAVAN_SN_PLAN
TEK_SAGLAYICI_TAVANI = 0.40          # `SAGLAYICI-TEKEL` ile AYNI esik

FAIL_KODLARI = (
    "GERCEK-KAYNAK-SES-SIZINTI",
    "GERCEK-KAYNAK-TAVANI",
    "GERCEK-KAPSAM-YOK",
)


def _s(v) -> str:
    return str(v or "").strip()


def _f(v, d=0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def sahneleri_cevir(props_sahneler: list, *, kok_dizin: str = "",
                    provenans_okuyucu: Optional[Callable] = None,
                    olgu_raporu: Optional[dict] = None) -> list:
    """RENDER EDILEN sahneleri olcum sozlesmesine cevir.

    ⚠ `provenans_okuyucu(mutlak_yol) -> dict` DISARIDAN verilir; bu modul
    dosya ACMAZ. Provenans yoksa sahne `fallback` sayilir — "herhalde
    lisanslidir" DENMEZ.
    """
    bosluk_sahneler = {str(b.get("sahne")) for b in
                       ((olgu_raporu or {}).get("bosluklar") or [])}
    cikti = []
    for i, s in enumerate(props_sahneler or []):
        if not isinstance(s, dict):
            continue
        medya = _s(s.get("medya"))
        yol = os.path.join(kok_dizin, medya) if (kok_dizin and medya) else medya
        pv = {}
        if callable(provenans_okuyucu) and yol:
            try:
                pv = provenans_okuyucu(yol) or {}
            except Exception:                                # noqa: BLE001
                pv = {}
        var = bool(pv.get("saglayici")) and bool(pv.get("lisans"))
        sid = _s(s.get("scene_id")) or f"s{i + 1:03d}"
        cikti.append({
            "beat_id": sid, "scene_id": sid,
            # ⚠ Provenans YOKSA `medya` DENMEZ.
            "kaynak_turu": "medya" if var else "fallback",
            "asset_id": _s(pv.get("asset_id")),
            "saglayici": _s(pv.get("saglayici")),
            "lisans": _s(pv.get("lisans")),
            # ⚠ Gercek hattin kendi tur bilgisi: props `tur` alani.
            "medya_turu": _s(pv.get("medya_turu")) or _s(s.get("tur")) or "image",
            "medya_yolu": yol,
            # ⚠ K-2: kaynak sesi politikasi. Gercek hat harici klibi
            # `OffthreadVideo ... muted` ile ciziyor; sozlesme MAKINE OKUNUR
            # yazilir ki kapi denetleyebilsin.
            "ses_kanali": _s(pv.get("ses_kanali")) or _sg.KAYNAK_SES_POLITIKASI,
            "islev": _s(s.get("islev")) or "aciklama",
            "sure_sn": _f(s.get("sure")),
            # ⚠ CEKIM TURU URETILMEZ (gercek hat atamiyor) — bos birakilir.
            "cekim_turu": "",
            # ⚠ FAZ R-1d-j: gercek hattin GECIS KARARI. `hizli_render`
            # imza YOKSA 2 karelik fade (= SERT KESME) uygular; imza VARSA
            # `GECIS_IMZA_FFMPEG` efektini uygular.
            "gecis_imza": _s(s.get("gecisImza")),
            "olgu_boslugu": str(i + 1) in bosluk_sahneler,
        })
    return cikti


def gecis_olcumu(sahneler: list) -> dict:
    """FAZ R-1d-j — GECIS METRIGI, gercek zaman cizgisinden.

    ⚠ OLCULEN BOSLUK (R-1d-i pilotu): `hard_cut_orani` = None idi.
    ⚠ Kaynak UYDURMA DEGIL: `hizli_render._xfade_zincir` gecis TURUNU
    sahnenin `gecisImza` alanindan secer; imza YOKSA gecis suresini 2 kareye
    kirpar — bu GOZLE SERT KESMEDIR. Metrik tam bu karardan turer.
    ⚠ Iki sahneden az varsa GECIS YOKTUR: oran UYDURULMAZ, stabil kod doner.
    """
    liste = [x for x in (sahneler or []) if isinstance(x, dict)]
    gecis = max(0, len(liste) - 1)
    if gecis < 1:
        # ⚠ Olculmemis deger SAYI olarak sunulmaz (`tur_sayisi` YOK).
        return {"olculdu": False, "kod": KOD_GECIS_YOK,
                "neden": "en az iki sahne gerekir", "gecis": gecis,
                "esik": GECIS_TURU_ASGARI, "esik_karsilandi": False}
    # Gecis, GELEN sahnenin imzasiyla belirlenir (ilk sahnenin gecisi yoktur).
    gelenler = liste[1:]
    imzalar = [_s(x.get("gecis_imza")) for x in gelenler]
    hard = sum(1 for i in imzalar if not i)
    dagilim: dict = {}
    for i in imzalar:
        if i:
            dagilim[i] = dagilim.get(i, 0) + 1
    # ⚠ FAZ Y-15: TUR SAYISI = farkli imza sayisi + (varsa) hard-cut.
    # Hard-cut da bir gecis TURUDUR (2 karelik fade = gozle sert kesme).
    tur_sayisi = len(dagilim) + (1 if hard else 0)
    esik_ok = tur_sayisi >= GECIS_TURU_ASGARI
    return {"olculdu": True,
            "kod": "" if esik_ok else KOD_GECIS_TUR_AZ,
            "gecis": gecis, "hard_cut": hard,
            "efektli": gecis - hard,
            "hard_cut_orani": round(hard / gecis, 3),
            "imza_dagilimi": dagilim,
            "tur_sayisi": tur_sayisi,
            "esik": GECIS_TURU_ASGARI,
            "esik_karsilandi": esik_ok}


def _ducking_olcumu(ducking_zarfi, ducking_olcum=None) -> dict:
    """Ducking raporu. ⚠ BEYAN ile OLCUM AYRI.

    ⚠ OLCULEN KUSUR (`Y14B-DUCKING-BEYAN-OLCUM-SANILDI`): ilk surumde
    zarfin ucuncu alanindaki YAPILANDIRMA degeri (`SFX_DUCKING_DB`)
    `derinlik_db` diye raporlaniyordu ve kabul kriteri onu "olculdu"
    sayiyordu. `threshold`/`ratio` secimi gercek gain reduction'in o
    deger olmasini GARANTI ETMEZ — filtre hic etki etmese bile kriter
    PASS verirdi.

    ── SOZLESME ──
      · `zarf` yalnizca PENCERELERI verir (kac aralik, ne kadar sure).
      · GERCEK azalma `ducking_olcum` ile DISARIDAN gelir
        (`pipeline.ducking_gain_olcumu`: stem'in sidechain oncesi/sonrasi
        RMS farki). Yoksa `olculdu: False` KALIR.
      · `yapilandirilmis_db` ve `olculen_reduction_db` AYRI alanlardir.
    """
    zarf = [z for z in (ducking_zarfi or [])
            if isinstance(z, (list, tuple)) and len(z) >= 3]
    olcum = ducking_olcum if isinstance(ducking_olcum, dict) else {}
    try:
        toplam_sn = round(sum(float(z[1]) - float(z[0]) for z in zarf), 3)
        yapi = round(min(float(z[2]) for z in zarf), 2) if zarf else None
    except (TypeError, ValueError):
        toplam_sn, yapi = 0.0, None
    if olcum.get("yapilandirilmis_db") is not None:
        yapi = olcum.get("yapilandirilmis_db")
    temel = {"aralik": len(zarf), "toplam_sn": toplam_sn,
             "yapilandirilmis_db": yapi}
    if not zarf:
        return {**temel, "olculdu": False, "kod": KOD_DUCKING_YOK,
                "olculen_reduction_db": None,
                "neden": "gercek zaman cizgisi ducking zarfi tasimiyor"}
    if not olcum or olcum.get("olculdu") is not True:
        # ⚠ Zarf TEK BASINA kabul uretmez: pencere var ama azalma OLCULMEDI.
        return {**temel, "olculdu": False,
                "kod": str(olcum.get("kod") or KOD_DUCKING_GAIN_OLCULMEDI),
                "olculen_reduction_db": None,
                "neden": str(olcum.get("neden")
                             or "gercek gain reduction olcumu verilmedi")}
    return {**temel, "olculdu": True, "kod": "",
            "olculen_reduction_db": olcum.get("olculen_reduction_db"),
            "p50_db": olcum.get("p50_db"), "p95_db": olcum.get("p95_db"),
            "pencere": olcum.get("pencere"),
            "atlanan_pencere": olcum.get("atlanan_pencere")}


def ses_kurgu_olcumu(sahneler: list, *, jl_raporu: Optional[dict] = None,
                     artefakt_sha256: str = "",
                     ducking_zarfi=None, ducking_olcum=None) -> dict:
    """FAZ R-1d-j / Y-13a — SES KURGUSU (J/L-cut + ducking).

    ⚠ OLCULEN KUSUR (`Y13-OLCUM-NIYETI-OKUYOR`): bu fonksiyon eskiden
    `hizli_render._JL_SON` MODUL GLOBAL'INI okuyordu. Uc ayri kirilma:
      1. SIRA — `pipeline.py` `gercek_qa.olc`'u RENDER'DAN ONCE kosuyor;
         `_JL_SON` ise render SIRASINDA yaziliyor. Okunan deger o is icin
         HICBIR ZAMAN taze degildi.
      2. OBEK EZILMESI — `hizli_render` sayaci ATIYOR (`=`, `+=` degil) ve
         obek birlestirmesi `sahne_dilimi=None` ile cagrildigi icin sayac
         0'a EZILIYOR: 12'den uzun her iste olcum yapisal olarak 0.
      3. KONTAMINASYON — `_JL_SON` surec omurlu ve is basi sifirlanmiyor;
         uzun omurlu iscide A isinin QA'si B isinin sayisini raporluyor.
    Bu, R-1d-e'de bir kez duzeltilen kusurun AYNISIDIR (o zaman hic render
    edilmeyen `edit_plani` kanit sayiliyordu).

    ── SOZLESME ──
      · J/L raporu DISARIDAN enjekte edilir (`kare_okuyucu` deseniyle ayni).
      · Rapor yoksa -> `olculdu: False` + `KOD_JL_OLCULMEDI`.
        ⚠ 0 UYDURULMAZ; `j_l_cut` anahtari SAYI OLARAK SUNULMAZ, boylece
        "olculmemis 0" ile "olculen 0" karistirilamaz.
      · Rapor render'dan ONCE uretilmisse (`kaynak != "render-sonrasi"`) ya
        da BASKA bir artefakta aitse -> `olculdu: False` + `KOD_JL_BAYAT`.
      · `tam` yalnizca OLCULEN deger `JL_EN_AZ` esigini karsilarsa True.
      · Ducking zarfi verilmezse `olculdu: False` KALIR (uydurma yok).
    """
    liste = [x for x in (sahneler or []) if isinstance(x, dict)]
    ses_gecis = max(0, len(liste) - 1)
    ducking = _ducking_olcumu(ducking_zarfi, ducking_olcum)
    if ses_gecis < 1:
        return {"olculdu": False, "kod": KOD_GECIS_YOK,
                "neden": "en az iki sahne gerekir", "tam": False,
                "ducking": ducking}

    def _red(kod, neden):
        # ⚠ `j_l_cut` BILEREK YOK: olculmemis deger sayi gibi sunulmaz.
        return {"olculdu": False, "kod": kod, "neden": neden,
                "ses_gecis": ses_gecis, "tam": False, "ducking": ducking}

    if not isinstance(jl_raporu, dict) or not jl_raporu:
        return _red(KOD_JL_OLCULMEDI,
                    "J/L raporu enjekte edilmedi (render sonrasi olcum yok)")
    _kaynak = str(jl_raporu.get("kaynak") or "")
    if _kaynak != "render-sonrasi":
        return _red(KOD_JL_BAYAT,
                    f"olcum kaynagi {_kaynak!r} — render sonrasi degil")
    _ozet = str(jl_raporu.get("artefakt_sha256") or "")
    if not _ozet:
        return _red(KOD_JL_BAYAT, "olcum bir artefakta bagli degil")
    if artefakt_sha256 and _ozet != str(artefakt_sha256):
        return _red(KOD_JL_BAYAT,
                    f"olcum baska artefakta ait ({_ozet[:12]} != "
                    f"{str(artefakt_sha256)[:12]})")
    try:
        _jl = int(jl_raporu.get("sayi") or 0)
        _jl_off = float(jl_raporu.get("offset_sn") or 0.0)
    except (TypeError, ValueError) as e:
        return _red(KOD_JL_OLCULMEDI, f"rapor okunamadi: {type(e).__name__}")
    return {
        "olculdu": True, "kod": "",
        "ses_gecis": ses_gecis,
        "j_l_cut": _jl,
        "jl_offset_sn": _jl_off,
        "artefakt_sha256": _ozet,
        "sinir_farklari_sn": list(jl_raporu.get("sinir_farklari_sn") or [])[:40],
        "gerekce": (f"{_jl} gecisde ses siniri goruntuden {_jl_off:.2f} sn "
                    f"AYRISTI (render sonrasi, artefakta bagli olcum)"
                    if _jl else
                    "olculdu: bu artefaktta J/L secilen gecis yok"),
        "ducking": ducking,
        # ⚠ Esik OLCULEN degere uygulanir; olculmemislik `tam` uretemez.
        "tam": _jl >= JL_EN_AZ,
    }


def olc(sahneler: list, *, kare_okuyucu: Optional[Callable] = None,
        jl_raporu: Optional[dict] = None, artefakt_sha256: str = "",
        ducking_zarfi=None, ducking_olcum=None) -> dict:
    """Gercek zaman cizgisinin PRE-QA olcumu + hukmu.

    ⚠ Olcum fonksiyonlari DEGISMEDI; yalnizca girdi gercek zaman cizgisi.
    ⚠ Turetilemeyen olcum `olculdu: False` + STABIL KOD ile bildirilir.
    """
    liste = [s for s in (sahneler or []) if isinstance(s, dict)]
    if not liste:
        return {"durum": "OLCULEMEDI", "neden": KOD_SAHNE_YOK,
                "fail": 0, "warn": 0, "sorunlar": [], "olcumler": {}}

    sorunlar = []

    def _ekle(kod, seviye, detay, scene_id=""):
        sorunlar.append({"kod": kod, "seviye": seviye, "detay": str(detay)[:160],
                         "beat_id": _s(scene_id), "scene_id": _s(scene_id)})

    # ── 1) KAPSAM (medya vs fallback) ──
    medya = [s for s in liste if s.get("kaynak_turu") == "medya"]
    kapsam = {"cekim": len(liste), "medya": len(medya),
              "fallback": len(liste) - len(medya),
              "kapsam_orani": round(len(medya) / max(1, len(liste)), 3)}
    if not medya:
        _ekle("GERCEK-KAPSAM-YOK", "fail",
              "hicbir sahnede lisans/provenans kayitli medya yok")

    # ── 2) MEDYA TURU / GERCEK VIDEO ORANI (mevcut olcum modulu) ──
    medya_turu = _kk.medya_turu_ozeti(liste, kare_okuyucu=kare_okuyucu)

    # ── 3) KAYNAK SESI SIFIR (K-2 sozlesmesi, mevcut modul) ──
    kaynak_ses = _sg.kaynak_ses_sozlesmesi(liste)
    for ih in (kaynak_ses.get("ihlal") or []):
        _ekle("GERCEK-KAYNAK-SES-SIZINTI", "fail",
              f"kaynak video sesi SIFIR degil: {ih.get('ses_kanali')!r}",
              ih.get("beat_id"))

    # ── 4) AYNI KAYNAK <= TAVAN ──
    kullanim: dict = {}
    for s in medya:
        aid = _s(s.get("asset_id"))
        if aid:
            kullanim[aid] = kullanim.get(aid, 0.0) + _f(s.get("sure_sn"))
    asan = [{"asset_id": a, "sure_sn": round(v, 3)}
            for a, v in sorted(kullanim.items()) if v > KAYNAK_TAVANI_SN + 1e-9]
    for a in asan:
        _ekle("GERCEK-KAYNAK-TAVANI", "fail",
              f"{a['asset_id']} toplam {a['sure_sn']} sn "
              f"(tavan {KAYNAK_TAVANI_SN} sn)")
    kaynak_kullanimi = {
        "olculdu": True, "tavan_sn": KAYNAK_TAVANI_SN,
        "varlik_sayisi": len(kullanim),
        "kullanim": {a: round(v, 3) for a, v in sorted(kullanim.items())},
        "en_uzun_sn": round(max(kullanim.values()), 3) if kullanim else 0.0,
        "asan": asan, "temiz": not asan}

    # ── 5) SAGLAYICI DAGILIMI (SAGLAYICI-TEKEL ile AYNI esik) ──
    sag: dict = {}
    toplam_medya_sn = sum(_f(s.get("sure_sn")) for s in medya)
    for s in medya:
        k = _s(s.get("saglayici")) or "?"
        h = sag.setdefault(k, {"cekim": 0, "sure_sn": 0.0})
        h["cekim"] += 1
        h["sure_sn"] = round(h["sure_sn"] + _f(s.get("sure_sn")), 3)
    tek_oran = (round(max((v["sure_sn"] for v in sag.values()), default=0.0)
                      / toplam_medya_sn, 4) if toplam_medya_sn > 0 else None)
    if tek_oran is not None and tek_oran > TEK_SAGLAYICI_TAVANI:
        _ekle("SAGLAYICI-TEKEL", "warn",
              f"tek saglayici %{tek_oran * 100:.0f} "
              f"(tavan %{TEK_SAGLAYICI_TAVANI * 100:.0f})")

    # ── 6) SUREKLILIK: ARDIL AYNI VARLIK ──
    for i in range(1, len(liste)):
        a, b = liste[i - 1], liste[i]
        if (a.get("kaynak_turu") == "medya" and b.get("kaynak_turu") == "medya"
                and _s(a.get("asset_id"))
                and _s(a.get("asset_id")) == _s(b.get("asset_id"))):
            _ekle("SUREKLILIK-AYNI-CEKIM", "warn",
                  f"ardil ayni varlik ({_s(b.get('asset_id'))})",
                  b.get("scene_id"))

    # ── 7) OLGU BAGI ──
    kopuk = [s for s in liste if s.get("olgu_boslugu")]
    for s in kopuk:
        _ekle("FACT-BAGLANTI-YOK", "warn",
              "sahne dogrulanmis bir iddiaya baglanamadi", s.get("scene_id"))

    # ── 8) UYGULANAMAYAN OLCUM — STABIL KODLA BILDIRILIR ──
    # ⚠ Gercek hat sahneye `cekim_turu` ATAMAZ (zoom/pan kararlari var).
    # Sahte tur URETMEK yerine olcum ACIKCA yapilamadi denir.
    # ── 8b) FAZ R-1d-j: GECIS + SES KURGUSU ──
    gecis = gecis_olcumu(liste)
    # ⚠ FAZ Y-13a: J/L ve ducking olcumu DISARIDAN gelir. Cagiran render
    # SONRASI olculmus, artefakta bagli raporu gecirmezse `ses_kurgu`
    # "olculmedi" doner — 0 UYDURULMAZ.
    ses_kurgu = ses_kurgu_olcumu(liste, jl_raporu=jl_raporu,
                                 artefakt_sha256=artefakt_sha256,
                                 ducking_zarfi=ducking_zarfi,
                                 ducking_olcum=ducking_olcum)

    broll = {"olculdu": False, "neden": KOD_CEKIM_TURU_YOK,
             "video_cekim_sayisi": sum(1 for s in medya
                                       if _s(s.get("medya_turu")) == "video"),
             "kaynak_saglayici_dagilimi": sag,
             "tek_saglayici_sure_orani": tek_oran}

    fail = sum(1 for s in sorunlar if s["seviye"] == "fail")
    warn = sum(1 for s in sorunlar if s["seviye"] == "warn")
    durum = "FAIL" if fail else ("WARN" if warn else "PASS")
    return {
        "durum": durum, "fail": fail, "warn": warn,
        "sorun_sayisi": len(sorunlar), "sorunlar": sorunlar[:40],
        "kaynak": "render-edilen-timeline",
        "sahne": len(liste),
        "kapsam": kapsam,
        "medya_turu": medya_turu,
        "gercek_video_orani": (medya_turu or {}).get("video_sure_orani"),
        "kaynak_ses": kaynak_ses,
        "kaynak_kullanimi": kaynak_kullanimi,
        "saglayici": sag,
        "broll_cesitliligi": broll,
        # ⚠ FAZ R-1d-j: teslim raporunun olcebilmesi icin UST SEVIYEDE de.
        "gecis": gecis, "ses": ses_kurgu,
        "olcumler": {"kapsam": kapsam, "medya_turu": medya_turu,
                     "kaynak_ses": kaynak_ses,
                     "kaynak_kullanimi": kaynak_kullanimi,
                     "saglayici": sag, "broll_cesitliligi": broll,
                     "gecis": gecis, "ses": ses_kurgu},
    }


def kapsam_ozeti() -> dict:
    return {
        "sema_surum": SEMA_SURUM,
        "kaynak": "render-edilen-timeline",
        "render_oncesi_kosar": True,
        "olcum_modulleri_degismedi": True,
        "uydurma_cekim_turu": False,
        "stabil_kodlar": [KOD_CEKIM_TURU_YOK, KOD_PROVENANS_YOK,
                          KOD_SAHNE_YOK, KOD_GECIS_YOK, KOD_DUCKING_YOK],
        "fail_kodlari": list(FAIL_KODLARI),
        "kaynak_tavani_sn": KAYNAK_TAVANI_SN,
        "tek_saglayici_tavani": TEK_SAGLAYICI_TAVANI,
        "aga_cikar": False, "medya_acar": False, "dosya_yazar": False,
        "render_eder": False,
    }
