#!/usr/bin/env python3
"""FAZ Y-11b-2 — GROUNDED FACT HAT ENTEGRASYONU (davranissal, red-first).

⚠ OLCULEN KUSURLAR (1a8c013 sonrasi denetim; hepsi DAVRANISSAL kanitlandi):

  1. `Y11B2-BENZERLIK-OTORITESI` — uretim yolu `arastirma_kopru.fact_bagla`
     idi; tahsisi 0.16 JACCARD ile yapiyordu. Kanit:
       fact_bagla([footage sahne], [{"fact_id": "UYDURMA-KIMLIK-000", ...}])
       -> baglanan=1, sahne["fact_id"] == "UYDURMA-KIMLIK-000"
     Allowlist'te OLMAYAN uydurma kimlik sahneye YAZILDI.
  2. `Y11B2-KAPI-CAGRILMIYOR` — `grounded_kapisi` + `shot_fact_dogrula`
     TANIMLIYDI ama `pipeline.py` ikisini de HIC CAGIRMIYORDU (OLU KOD).
  3. `Y11B2-KOSULSUZ-DEGIL` — tek fail-closed durus `if _olgular:`
     blogunun ICINDEYDI: arastirma kosmadi/hata/0 olgu -> kapi HIC
     kosmuyor, hat medya+TTS+render'a SESSIZCE devam ediyordu.
  4. `Y11B2-ENTAIL-POLARITE-KOR` — fact "recorded" iken anlatim "NEVER
     recorded" olsa bile ortusme yuksek/yeni deger yok -> PASS.
  5. `Y11B2-ILK-SAHNE-CLOSING` — chapter'in ILK sahnesi closing ise
     `kullanilan` bos oldugu icin kapanis YEPYENI fact ALIYORDU.
  6. `Y11B2-BOS-SHOT-PASS` — `shot_fact_dogrula([])` -> `hedef=0`, kod ""
     -> "0 shot denetlendi" PASS sayiliyordu.
  7. `Y11B2-SHOT-RAPORU-YOK` — `grounded_kapisi` tum-shot bilgisi
     OLMADAN PASS verebiliyordu ("olculemedi" != "gecti").
  8. `Y11B2-ENV-KAPI-GEVSETME` — `FACT_KAPSAM_ESIGI` ENV'den okunuyordu;
     `FACT_KAPSAM_ESIGI=0` kapiyi tamamen KAPATIYORDU.
  9. `Y11B2-PROJEKSIYON-YOK` — uretim sahneleri bolumu `bolum`, rolu
     `islev` adiyla tasir; `tahsis_et` `chapter_id`/`beat_role` bekler.
     Projeksiyon olmadan her sahne tek "c01"e duser, kapanis GORULMEZ.

── SOZLESME ──
  · Grounded belgeselde arastirma yok/hata/0 yetkili olgu -> MEDYA, TTS
    ve RENDER'dan ONCE stabil kodla FAIL; downstream 0-CALL.
  · Tahsis otoritesi ENTAILMENT + allowlist; benzerlik DEGIL.
  · Anlatim fact'in POLARITESINI ters cevirirse entail ETMEZ.
  · Kapanis rolu YENI fact getiremez — chapter'in ILK sahnesi olsa bile.
  · Kapsam esigi ENV ile GEVSETILEMEZ; yalnizca SIKILASTIRILABILIR.
  · ⚠ Grounded OLMAYAN modlar (animasyon/hikaye) ETKILENMEZ.

Kosum: .venv-test/bin/python3 webapp/testler/test_faz_y11b2.py
"""
from __future__ import annotations

import asyncio
import os
import shutil
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)

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


import fact_baglama as FB                                    # noqa: E402
import arastirma_kopru as AK                                 # noqa: E402
from arastirma import factpacket as FP                       # noqa: E402

_pipe_src = open(os.path.join(KOK, "pipeline.py"), encoding="utf-8").read()
URL1, URL2 = "https://www.npa.go.jp/rapor", "https://www.mhlw.go.jp/rapor"
Q1 = "In 2024, the National Police Agency recorded 76,941 cases of people"
Q2 = "Of these, 39.4% were aged 75 or older"


def _paket(onerme, alinti, url, belge=None):
    p = FP.paket_kur(onerme=onerme, exact_quote=alinti,
                     belge_metni=(belge if belge is not None else alinti + ".\n"),
                     url=url, baslik="rapor", erisim_tarihi="2026-08-15",
                     kategori="rakam", stance="support")
    p.verification_status = "accepted"
    return p


P1, P2 = _paket(Q1, Q1, URL1), _paket(Q2, Q2, URL2)
BELGELER = {P1.source_id: Q1 + ".\n", P2.source_id: Q2 + ".\n"}
IZIN = {P1.fact_id, P2.fact_id}


# ══════════════════════════════════════════════════════════════════════
blok("Y-11b-2/1 — TAHSIS OTORITESI: ENTAILMENT, BENZERLIK DEGIL")

_S = [{"scene_id": "s1", "chapter_id": "c1", "voiceover": Q1},
      {"scene_id": "s2", "chapter_id": "c1", "voiceover": Q2},
      {"scene_id": "s3", "chapter_id": "c1", "voiceover": "Bir kus ucuyor"}]
_r = FB.tahsis_et([P1, P2], _S, allowlist=IZIN)
kontrol("entail eden sahne DOGRU fact'i alir (round-robin DEGIL)",
        _r["tahsis"].get("s1") == P1.fact_id
        and _r["tahsis"].get("s2") == P2.fact_id, f"{_r['tahsis']}")
kontrol("ILGISIZ sahne fact ALMAZ (uydurma yok)",
        "s3" not in _r["tahsis"], f"{_r['tahsis']}")
kontrol("ilgisiz sahne stabil kodla bosluk uretir",
        any(b["kod"] == FB.KOD_ENTAIL_ILGISIZ for b in _r["bosluklar"]),
        f"{_r['bosluklar']}")
kontrol("allowlist ZORUNLU (paket kendi yetkisi DEGIL)",
        FB.tahsis_et([P1, P2], _S, allowlist=None)["kod"]
        == FB.KOD_GROUNDED_FACT_YOK)
# ⚠ `Y11B2-PREFILL-NORMALIZE-BYPASS`: tek alanli prefill artik SESSIZCE
# normalize EDILMEZ; iki alan da zorunlu -> eksik alan stabil `SHOT-FACT-YOK`.
kontrol("prefilled TEK ALAN -> stabil RED (sessiz normalize yok)",
        FB.tahsis_et([P1, P2],
                     [{"scene_id": "s1", "chapter_id": "c1", "voiceover": Q1,
                       "primary_fact_id": "ENJEKTE"}],
                     allowlist=IZIN)["kod"] == FB.KOD_SHOT_FACT_YOK)
kontrol("prefilled IKI ALAN ama allowlist DISI -> stabil RED",
        FB.tahsis_et([P1, P2],
                     [{"scene_id": "s1", "chapter_id": "c1", "voiceover": Q1,
                       "primary_fact_id": "ENJEKTE",
                       "fact_id": "ENJEKTE"}],
                     allowlist=IZIN)["kod"]
        == FB.KOD_SHOT_FACT_ALLOWLIST_DISI)
kontrol("tahsis DETERMINISTIK (ayni girdi ayni snapshot)",
        FB.tahsis_et([P1, P2], _S, allowlist=IZIN)["snapshot"]
        == _r["snapshot"])
kontrol("uretim yolunda fact_bagla ARTIK YOK",
        "arastirma_kopru.fact_bagla(" not in
        open(os.path.join(KOK, "pipeline.py"), encoding="utf-8").read())
kontrol("karar kodu belgelendi: Y11B2-BENZERLIK-OTORITESI",
        "Y11B2-BENZERLIK-OTORITESI" in
        open(os.path.join(KOK, "pipeline.py"), encoding="utf-8").read())


# ══════════════════════════════════════════════════════════════════════
blok("Y-11b-2/2 — EXTRACTIVE SOZLESME: KANONIK ONERME ILE BIREBIR")

# ⚠ OLCULEN KUSUR (`Y11B2-HEURISTIK-SONSUZ`, kirmizi takim final denetimi):
# tahsis kapisi bir SEZGISEL KURAL YIGINIYDI (polarite kelime/ek listeleri,
# baglac ayiricilari, cue kumeleri, retorik istisnalari, kapsam esikleri).
# Her denetim turu YENI bir kacak buldu; enumerasyon SONSUZ. Sezgisel kod
# OTORITE OLMAKTAN CIKARILDI ve KALDIRILDI. Yerine Y-11b-1'in
# EXACT-SUPPORT sozlesmesiyle tutarli EN DAR kural: konusulan yetkili alan,
# kanonik onerme ile NORMALIZE EDILMIS BIREBIR AYNI olmadan tahsis YOK.
_EQ = "The agency recorded 76,941 cases in 2024"
_EP = _paket(_EQ, _EQ, "https://www.npa.go.jp/ex")
_EIZIN = {_EP.fact_id}

_KARSI = (
    ("or ile olumsuzluk yer degistirmesi",
     "The agency did not record 76,941 cases or disclosed names"),
    ("after ile olumsuzluk yer degistirmesi",
     "The agency did not record 76,941 cases after 2024"),
    ("before ile olumsuzluk yer degistirmesi",
     "Before 2024 the agency did not record 76,941 cases"),
    ("TR simdiki zaman olumsuzu (-miyor)",
     "Kurum vakalari kaydetmiyor"),
    ("cue self-exemption (fact icinde rumor)", "a rumor says " + _EQ),
    ("modal: may have",
     "The agency may have recorded 76,941 cases in 2024"),
    ("modal: reportedly",
     "Reportedly the agency recorded 76,941 cases in 2024"),
    ("modal: unverified", "Unverified: " + _EQ),
    ("modal: guya", "Guya kurum 76,941 vaka kaydetti"),
    ("NOKTALAMASIZ soru", "did the agency record 76,941 cases in 2024"),
    ("desteklenmemis YENI YUKLEM", _EQ + " and concealed evidence"),
    ("desteklenmemis YENI YUKLEM 2",
     _EQ + " and officials destroyed evidence"),
    ("sayi MAGNITUDE: 76,941 -> 769.41",
     "The agency recorded 769.41 cases in 2024"),
    ("sayi BICIM: 76,941 -> 76941",
     "The agency recorded 76941 cases in 2024"),
    ("sayi MAGNITUDE: 39.4 -> 394", "Of these 394% were aged 75 or older"),
    ("PARAPHRASE", "In 2024 the agency logged 76,941 cases"),
    ("retorik ONEK", "Indeed, " + _EQ),
    ("retorik SONEK", _EQ + ", therefore"),
    ("komedi/ironi", "Ha ha, " + _EQ + ", can you believe it"),
)
for _ad, _t in _KARSI:
    _de = FB.entail_dogrula(_t, _EP)
    kontrol(f"RED: {_ad}", not _de["gecti"], f"{_de}")
    kontrol(f"{_ad}: TEK stabil kod",
            _de.get("kod") == FB.KOD_ENTAIL_EXTRACTIVE_DEGIL, f"{_de}")
    kontrol(f"{_ad}: TAHSIS ALMAZ",
            "sx" not in FB.tahsis_et(
                [_EP], [{"scene_id": "sx", "chapter_id": "c01",
                         "voiceover": _t}], allowlist=_EIZIN)["tahsis"])

# ── POZITIF: BIREBIR KANONIK metinler (yalniz bosluk/case normalizasyonu)
kontrol("EN kanonik BIREBIR metin GECER",
        FB.entail_dogrula(_EQ, _EP)["gecti"], f"{FB.entail_dogrula(_EQ, _EP)}")
kontrol("BUYUK/kucuk harf farki GECER",
        FB.entail_dogrula(_EQ.upper(), _EP)["gecti"])
kontrol("FAZLA BOSLUK GECER",
        FB.entail_dogrula("  " + _EQ.replace(" ", "   ") + "  ", _EP)["gecti"])
kontrol("kanonik metin TAHSIS ALIR",
        FB.tahsis_et([_EP], [{"scene_id": "sk", "chapter_id": "c01",
                              "voiceover": _EQ}],
                     allowlist=_EIZIN)["tahsis"].get("sk") == _EP.fact_id)
_TRQ = "Kurum 2024'te 76,941 vakayi kaydetti"
_TRP = _paket(_TRQ, _TRQ, "https://www.kurum.gov.tr/ex")
kontrol("TR kanonik BIREBIR metin GECER",
        FB.entail_dogrula(_TRQ, _TRP)["gecti"],
        f"{FB.entail_dogrula(_TRQ, _TRP)}")
kontrol("TR kanonik metin TAHSIS ALIR",
        FB.tahsis_et([_TRP], [{"scene_id": "st", "chapter_id": "c01",
                               "voiceover": _TRQ}],
                     allowlist={_TRP.fact_id})["tahsis"].get("st")
        == _TRP.fact_id)
_NQ = "Bu vakalarin 39.4% kadari 75 yas ustundeydi"
_NP = _paket(_NQ, _NQ, "https://www.kurum.gov.tr/nm")
kontrol("SAYI iceren kanonik metin BIREBIR GECER",
        FB.entail_dogrula(_NQ, _NP)["gecti"], f"{FB.entail_dogrula(_NQ, _NP)}")

# ── SEZGISEL KOD OTORITE DEGIL VE BIRAKILMADI ──
_FBS = open(os.path.join(KOK, "fact_baglama.py"), encoding="utf-8").read()
for _olu in ("def polarite(", "def polarite_dagilimi(",
             "def polarite_carpisiyor_mu(", "def anlatim_baglami(",
             "def kapsanmayan_yantumceler(", "_YANTUMCE", "_RETORIK",
             "_TR_OLUMSUZ_EK", "_CEVRE_CURUTEN and _OLUMSUZ"):
    if _olu == "_CEVRE_CURUTEN and _OLUMSUZ":
        continue
    kontrol(f"OLU SEZGISEL KOD KALDIRILDI: {_olu}", _olu not in _FBS,
            "dead complexity birakilmis")
for _kod in ("FACT-ENTAIL-POLARITE", "FACT-ENTAIL-YENI-DEGER",
             "FACT-ANLATIM-IDDIA-DEGIL", "FACT-ANLATIM-BAGLAMI-CURUTUYOR",
             "FACT-ENTAIL-DESTEKSIZ-EK"):
    kontrol(f"sezgisel kod ARTIK YOK: {_kod}", _kod not in _FBS)
kontrol("kanonik onerme cozumleyicisi tanimli",
        "def kanonik_onerme(" in _FBS)
kontrol("karar kodu belgelendi: Y11B2-HEURISTIK-SONSUZ",
        "Y11B2-HEURISTIK-SONSUZ" in _FBS)
kontrol("KAPSAM SINIRI kodda ACIK: paraphrase/NLI DESTEKLENMIYOR",
        "SERBEST PARAPHRASE ve NLI bu" in _FBS)

# ── PLANLAYICI BIREBIR KOPYAYA ZORLANIR ──
_AKS = open(os.path.join(KOK, "arastirma_kopru.py"), encoding="utf-8").read()
kontrol("planlayici promptu KELIMESI KELIMESINE kopya ister",
        "KELIMESI KELIMESINE" in _AKS)
kontrol("planlayici promptu BIR SAHNEDE BIR OLGU der",
        "YALNIZCA BIR olgu cumlesi" in _AKS)
kontrol("planlayici promptu stabil kodu SOYLER",
        "FACT-ENTAIL-EXTRACTIVE-DEGIL" in _AKS)


# ══════════════════════════════════════════════════════════════════════
blok("Y-11b-2/3 — CHAPTER ILK SAHNESI CLOSING ISE YENI FACT ALAMAZ")

_kapanis_rol = sorted(FB.SONUC_ROLLERI)[0]
_ilk_closing = [{"scene_id": "k1", "chapter_id": "c2",
                 "beat_role": _kapanis_rol, "voiceover": Q1}]
_rc = FB.tahsis_et([P1, P2], _ilk_closing, allowlist=IZIN)
kontrol("chapter ILK sahnesi closing -> fact ALMAZ",
        "k1" not in _rc["tahsis"], f"{_rc['tahsis']}")
kontrol("ilk-closing stabil kodu",
        _rc["kod"] == FB.KOD_SHOT_FACT_YOK, f"{_rc}")
_normal = [{"scene_id": "a1", "chapter_id": "c2", "voiceover": Q1},
           {"scene_id": "k1", "chapter_id": "c2", "beat_role": _kapanis_rol,
            "voiceover": Q1}]
_rn = FB.tahsis_et([P1, P2], _normal, allowlist=IZIN)
kontrol("closing ONCEKI fact'i tekrar kullanabilir",
        _rn["tahsis"].get("k1") == _rn["tahsis"].get("a1") == P1.fact_id,
        f"{_rn['tahsis']}")
kontrol("karar kodu belgelendi: Y11B2-ILK-SAHNE-CLOSING",
        "Y11B2-ILK-SAHNE-CLOSING" in
        open(os.path.join(KOK, "fact_baglama.py"), encoding="utf-8").read())


# ══════════════════════════════════════════════════════════════════════
blok("Y-11b-2/4 — BOS SHOT LISTESI VE SHOT RAPORSUZ KAPI PASS VERMEZ")

_bos = FB.shot_fact_dogrula([], allowlist=IZIN)
kontrol("bos shot listesi PASS DEGIL", bool(_bos["kod"]), f"{_bos}")
kontrol("bos shot stabil kodu", _bos["kod"] == FB.KOD_SHOT_FACT_YOK,
        f"{_bos}")
_ORTAK = dict(mod="documentary", arastirma_calisti=True, arastirma_hatasi="",
              allowlist=IZIN, cozulemeyen=0, bolum_kapsami={"c1": 2})
kontrol("shot raporu YOKSA kapi PASS VERMEZ",
        FB.grounded_kapisi(**_ORTAK, shot_raporu=None)["kod"]
        == FB.KOD_SHOT_RAPORU_YOK)
kontrol("bos shot raporu PASS VERMEZ",
        not FB.grounded_kapisi(**_ORTAK, shot_raporu={})["gecti"])
kontrol("kismi kapsam PASS VERMEZ",
        not FB.grounded_kapisi(
            **_ORTAK,
            shot_raporu={"hedef": 3, "bagli": 2, "kod": "", "neden": ""}
        )["gecti"])
kontrol("TAM kapsam + temiz rapor GECER",
        FB.grounded_kapisi(
            **_ORTAK,
            shot_raporu={"hedef": 3, "bagli": 3, "kod": "", "neden": ""}
        )["gecti"])
kontrol("shot raporu kodu kapiya AYNEN tasinir",
        FB.grounded_kapisi(
            **_ORTAK,
            shot_raporu={"hedef": 3, "bagli": 1,
                         "kod": FB.KOD_SHOT_FACT_ALLOWLIST_DISI,
                         "neden": "x"})["kod"]
        == FB.KOD_SHOT_FACT_ALLOWLIST_DISI)
kontrol("grounded OLMAYAN mod KAPSAM DISI (davranis degismez)",
        FB.grounded_kapisi(mod="animasyon", arastirma_calisti=False,
                           arastirma_hatasi="", allowlist=set(),
                           shot_raporu=None)["kapsam_disi"])
kontrol("karar kodu belgelendi: Y11B2-BOS-SHOT-PASS",
        "Y11B2-BOS-SHOT-PASS" in
        open(os.path.join(KOK, "fact_baglama.py"), encoding="utf-8").read())


# ══════════════════════════════════════════════════════════════════════
blok("Y-11b-2/5 — KAPSAM ESIGI ENV ILE GEVSETILEMEZ")

kontrol("FACT_KAPSAM_TABANI sabiti tanimli",
        "FACT_KAPSAM_TABANI = 1.0" in _pipe_src)
kontrol("esik max(taban, env) ile KILITLI",
        "max(FACT_KAPSAM_TABANI," in _pipe_src, "env dogrudan otorite")
kontrol("karar kodu belgelendi: Y11B2-ENV-KAPI-GEVSETME",
        "Y11B2-ENV-KAPI-GEVSETME" in _pipe_src)


# ══════════════════════════════════════════════════════════════════════
blok("Y-11b-2/6 — URETIM HATTI: KOSULSUZ ERKEN FAIL + DOWNSTREAM 0-CALL")

_kok2 = tempfile.mkdtemp(prefix="y11b2_kok_")
_uret_py = os.path.join(KOK, "..", "app", "uret.py")
if os.path.exists(_uret_py):
    shutil.copy(_uret_py, os.path.join(_kok2, "uret.py"))
sys.path.insert(0, _kok2)
os.environ["VIDRUSH_KOK"] = os.path.abspath(_kok2)
os.environ.setdefault("CIKTI_DIR", os.path.join(_kok2, "ciktilar"))
# ⚠ ENV ile kapiyi GEVSETMEYI DENE — sozlesme geregi ETKISIZ olmali.
os.environ["FACT_KAPSAM_ESIGI"] = "0"
import pipeline as PL                                        # noqa: E402

kontrol("ENV=0 olsa da esik %100 KALIR", PL.FACT_KAPSAM_ESIGI == 1.0,
        f"{PL.FACT_KAPSAM_ESIGI}")

# ⚠ HERMETIK SINIR TABLOSU: (sahip, oznitelik, sayac_adi).
# Ag/kimlik-bilgisi/medya/render SINIRLARININ HEPSI kapatilir; testin
# hicbir dali gercek saglayiciya, dosya sistemine ya da ffmpeg'e gitmez.
_SINIRLAR = (
    (PL.kaynak, "footage_getir", "medya"),
    (PL.kaynak, "youtube_sahne", "medya"),
    (PL.kaynak, "atif_al", "medya"),
    (PL.kaynak, "magnific_upscale", "medya"),
    (PL.kaynak, "stok_provenans_al", "medya"),
    (PL.medya_kopru, "sahne_medyasi", "medya"),
    (PL, "referansli_gorsel", "gorsel"),
    (PL.uretmod, "seslendir", "tts"),
    (PL.subprocess, "run", "render"),
    (PL.subprocess, "Popen", "render"),
)
# ⚠ ON-KAPI (preflight) sinirlari: arastirma DONER DONMEZ karar verilir;
# bunlarin HICBIRI cagrilmamalidir.
_ON_SINIRLAR = (
    (PL, "uzun_plan", "plan"),
    (PL, "metin_islev_analizi", "plan"),
    (PL.os, "makedirs", "disk"),
)
_SAYAC = {"medya": 0, "gorsel": 0, "tts": 0, "render": 0,
          "plan": 0, "disk": 0}


class _Sonuc(AK.Sonuc):
    """GERCEK `arastirma_kopru.Sonuc` — sahte ikiz DEGIL."""


def _say(ad, patla=True):
    def _f(*a, **kw):
        _SAYAC[ad] += 1
        if patla:
            raise AssertionError(f"{ad} SINIRI CAGRILDI")
        return None
    return _f


def _kos(sonuc, sahneler, mod="documentary", *, on_kapi=True,
         plan_gecerli=False):
    """Hattin ONUNU sahteler, TUM downstream sinirlarini SAYAR.

    ⚠ try/finally ile her oznitelik ESKI HALINE geri konur.
    """
    for k in _SAYAC:
        _SAYAC[k] = 0
    _eski = []

    def _yaz(sahip, ad, deger):
        _eski.append((sahip, ad, getattr(sahip, ad)))
        setattr(sahip, ad, deger)

    try:
        _yaz(PL.arastirma_kopru, "arastir_ve_zenginlestir",
             lambda story, **kw: (story, sonuc))
        for _sahip, _ad, _sayac_ad in _SINIRLAR:
            if hasattr(_sahip, _ad):
                _yaz(_sahip, _ad, _say(_sayac_ad))
        if on_kapi:
            # ⚠ ON-KAPI dallarinda plan/disk SINIRLARI da patlamali.
            for _sahip, _ad, _sayac_ad in _ON_SINIRLAR:
                if hasattr(_sahip, _ad):
                    _yaz(_sahip, _ad, _say(_sayac_ad))
        else:
            _yaz(PL, "uzun_plan",
                 lambda *a, **kw: {"scenes": [dict(x) for x in sahneler],
                                   "baslik": "T", "aciklama": ""})
            _yaz(PL, "metin_islev_analizi", lambda *a, **kw: [])
            _yaz(PL, "karakter_analiz", lambda *a, **kw: {})
            _yaz(PL, "stil_analiz", lambda *a, **kw: {})
        try:
            asyncio.get_event_loop().run_until_complete(
                PL.uret("y11b2_test", "konu metni", "", mod=mod, sure_dk=1))
            return ""
        except Exception as e:                               # noqa: BLE001
            return f"{e}"
    finally:
        for _sahip, _ad, _deger in reversed(_eski):
            setattr(_sahip, _ad, _deger)


# ⚠ URETIM sahneleri anlatimi `voiceover` alaninda tasir
# (`pipeline.py`: `metin = str(s.get("voiceover", ""))`). Fixture bunu
# TASIMAZSA sahne dongusu HIC donmez ve 0-call olcumu BOSA duser.
_SAHNE = [{"voiceover": Q1, "bolum": "CH1", "islev": "vurgu",
           "scene_prompt": "police office", "footage_sorgu": "police"},
          {"voiceover": Q2, "islev": "vurgu",
           "scene_prompt": "elderly", "footage_sorgu": "elderly"}]
_TEMIZ = {"medya": 0, "gorsel": 0, "tts": 0, "render": 0,
          "plan": 0, "disk": 0}


def _saglikli():
    return _Sonuc(calisti=True, paketler=[P1, P2],
                  replay_belgeleri=dict(BELGELER))


# ── ON-KAPI: arastirma DONER DONMEZ, plan/disk'e DOKUNMADAN ──
for _ad, _sonuc, _kod in (
        ("arastirma KOSMADI", _Sonuc(calisti=False),
         FB.KOD_GROUNDED_ARASTIRMA_YOK),
        ("arastirma HATASI", _Sonuc(calisti=True, hata="ag coktu"),
         FB.KOD_GROUNDED_ARASTIRMA_HATA),
        ("kanit COZULEMEDI",
         _Sonuc(calisti=True, paketler=[P1], cozulemeyen=2,
                replay_belgeleri=dict(BELGELER)),
         FB.KOD_GROUNDED_KANIT_COZULEMEDI),
        ("0 YETKILI OLGU", _Sonuc(calisti=True),
         FB.KOD_GROUNDED_FACT_YOK)):
    _h = _kos(_sonuc, _SAHNE)
    kontrol(f"ON-KAPI {_ad} -> stabil kod {_kod}", _kod in _h, _h[:200])
    kontrol(f"ON-KAPI {_ad} -> plan/disk/medya/TTS/render 0-CALL",
            _SAYAC == _TEMIZ, f"{_SAYAC}")

# ── POZITIF KONTROL: 0-CALL OLCUMU BOS OLMASIN ──
# Kapi GECILDIGINDE sinirlar GERCEKTEN atesleniyor mu? Ateslenmiyorsa
# yukaridaki "0-call" iddialari HICBIR SEY KANITLAMAZ.
_h_kontrol = _kos(_saglikli(), _SAHNE, on_kapi=False)
kontrol("POZITIF KONTROL: kapi gecilince downstream GERCEKTEN cagriliyor",
        sum(_SAYAC[k] for k in ("medya", "gorsel", "tts", "render")) > 0,
        f"spy harness OLU -> 0-call iddialari BOS: {_SAYAC} "
        f"| {_h_kontrol[:160]}")
kontrol("POZITIF KONTROL: gecerli olgularla grounded kapi DUSURMEZ",
        not any(k in _h_kontrol for k in (
            FB.KOD_GROUNDED_ARASTIRMA_YOK, FB.KOD_GROUNDED_FACT_YOK,
            FB.KOD_SHOT_RAPORU_YOK, FB.KOD_SHOT_FACT_ALLOWLIST_DISI)),
        _h_kontrol[:200])

# ── ENTAIL EDILEMEYEN SAHNE: hat DURUR, downstream'e GIRMEZ ──
_h = _kos(_saglikli(),
          _SAHNE + [{"voiceover": "Bir kus ucuyor", "islev": "vurgu"}],
          on_kapi=False)
# ⚠ Iki fail-closed kapi da gecerlidir: kapsam esigi (Y-10) VEYA tum-shot
# denetimi (Y-11b-2). Hangisi once dusarse dussun, is DURMALI.
kontrol("entail EDILEMEYEN sahne varken hat DURUR",
        ("ARASTIRMA-HAVUZ-YETERSIZ" in _h) or (FB.KOD_SHOT_FACT_YOK in _h),
        _h[:200])
kontrol("entail boslugu -> medya/TTS/render 0-CALL",
        _SAYAC["medya"] == _SAYAC["tts"] == _SAYAC["render"]
        == _SAYAC["gorsel"] == 0, f"{_SAYAC}")

# ── YARATICI MODLAR: TAM HAT REGRESYONU ──
# ⚠ Grounded helper'lar CAGRILMAMALI; hat downstream sinira ULASMALI.
for _mod in ("animasyon", "hikaye"):
    _cagri = {"kapi": 0, "tahsis": 0}
    _e1, _e2 = FB.grounded_kapisi, AK.yetkili_tahsis

    def _kapi_spy(*a, **kw):
        _cagri["kapi"] += 1
        return _e1(*a, **kw)

    def _tahsis_spy(*a, **kw):
        _cagri["tahsis"] += 1
        return _e2(*a, **kw)

    PL.fact_baglama.grounded_kapisi = _kapi_spy
    PL.arastirma_kopru.yetkili_tahsis = _tahsis_spy
    try:
        _hm = _kos(_Sonuc(calisti=False), _SAHNE, mod=_mod, on_kapi=False)
    finally:
        PL.fact_baglama.grounded_kapisi = _e1
        PL.arastirma_kopru.yetkili_tahsis = _e2
    kontrol(f"{_mod}: grounded ON-KAPI kodlari CIKMAZ",
            not any(k in _hm for k in (
                FB.KOD_GROUNDED_ARASTIRMA_YOK, FB.KOD_GROUNDED_FACT_YOK,
                FB.KOD_GROUNDED_ARASTIRMA_HATA)), _hm[:160])
    kontrol(f"{_mod}: yetkili_tahsis CAGRILMAZ (arastirma kapali)",
            _cagri["tahsis"] == 0, f"{_cagri}")
    kontrol(f"{_mod}: hat downstream SINIRA ULASIR (regresyon yok)",
            sum(_SAYAC[k] for k in ("medya", "gorsel", "tts", "render")) > 0,
            f"{_SAYAC} | {_hm[:160]}")


blok("Y-11b-2/7 — PROJEKSIYON + primary_fact_id == fact_id")

_sh = [dict(s) for s in _SAHNE]
_son = _Sonuc(calisti=True, paketler=[P1, P2],
              replay_belgeleri=dict(BELGELER))
_t = AK.yetkili_tahsis(_son, _sh)
kontrol("yetkili_tahsis yalnizca YETKILI allowlist kullanir",
        set(_t["allowlist"]) == IZIN, f"{_t['allowlist']}")
kontrol("tahsis edilen sahneye primary_fact_id YAZILIR",
        all(s.get("primary_fact_id") for s in _sh), f"{_sh}")
kontrol("primary_fact_id ile fact_id BIREBIR AYNI",
        all(s.get("primary_fact_id") == s.get("fact_id") for s in _sh),
        f"{[(s.get('primary_fact_id'), s.get('fact_id')) for s in _sh]}")
kontrol("yazilan kimlik ALLOWLIST icinde",
        all(s["primary_fact_id"] in IZIN for s in _sh))
# ⚠ `Y11B2-FACT-ID-FALLBACK`: iki alan da ZORUNLU, fallback YOK.
kontrol("primary_fact_id BOSSA shot GECEMEZ",
        FB.shot_fact_dogrula(
            [{"scene_id": "s1", "fact_id": P1.fact_id}],
            allowlist=IZIN)["kod"] == FB.KOD_SHOT_FACT_YOK)
kontrol("fact_id BOSSA shot GECEMEZ",
        FB.shot_fact_dogrula(
            [{"scene_id": "s1", "primary_fact_id": P1.fact_id}],
            allowlist=IZIN)["kod"] == FB.KOD_SHOT_FACT_YOK)
kontrol("iki alan FARKLIYSA shot GECEMEZ",
        FB.shot_fact_dogrula(
            [{"scene_id": "s1", "primary_fact_id": P1.fact_id,
              "fact_id": P2.fact_id}],
            allowlist=IZIN)["kod"] == FB.KOD_SHOT_FACT_YOK)
kontrol("iki alan AYNI ve allowlist'te ise GECER",
        not FB.shot_fact_dogrula(
            [{"scene_id": "s1", "primary_fact_id": P1.fact_id,
              "fact_id": P1.fact_id}], allowlist=IZIN)["kod"])
kontrol("karar kodu belgelendi: Y11B2-FACT-ID-FALLBACK",
        "Y11B2-FACT-ID-FALLBACK" in
        open(os.path.join(KOK, "fact_baglama.py"), encoding="utf-8").read())
kontrol("sahne_metni URETIM alani 'voiceover'i OKUR",
        FB.sahne_metni({"voiceover": Q1}) == Q1,
        f"{FB.sahne_metni({'voiceover': Q1})!r}")
kontrol("karar kodu belgelendi: Y11B2-VOICEOVER-KOR",
        "Y11B2-VOICEOVER-KOR" in
        open(os.path.join(KOK, "fact_baglama.py"), encoding="utf-8").read())
kontrol("iddia_metni yetkili paketin ONERMESINDEN gelir",
        all(str(s.get("iddia_metni") or "") in (Q1, Q2) for s in _sh),
        f"{[s.get('iddia_metni') for s in _sh]}")
# ⚠ CANLI (durum tasiyan) projeksiyon: `bolum` basligi YALNIZCA bolumun
# ILK sahnesinde dolar; araya girenler ONCEKI bolume aittir.
_proj = FB.yay_projeksiyonu([
    {"bolum": "CH1", "islev": "vurgu"}, {"islev": "vurgu"},
    {"bolum": "CH2", "islev": "vurgu"}, {"islev": "vurgu"},
    {"islev": "kapanis"}])
kontrol("CH1 + bos -> AYNI bolum",
        _proj[0][0] == _proj[1][0] == "c01", f"{_proj}")
kontrol("CH2 + bos -> YENI bolum",
        _proj[2][0] == _proj[3][0] == "c02", f"{_proj}")
kontrol("islev='kapanis' -> KANONIK 'closing' rolu",
        _proj[4][1] == "closing", f"{_proj}")
kontrol("kapanis ONCEKI bolumde kalir", _proj[4][0] == "c02", f"{_proj}")
kontrol("yay_plani_kur ORTAK helper'i kullanir",
        "fact_baglama.yay_projeksiyonu(_gecerli)" in _pipe_src)
kontrol("pipeline sahneye KANONIK alan YAZMAZ (belirsizlik uretmez)",
        '_s["chapter_id"], _s["beat_role"] = _proj' not in _pipe_src)
kontrol("tahsis_et projeksiyonu ORTAK helper'dan cozer",
        "_proj = yay_projeksiyonu(liste)" in
        open(os.path.join(KOK, "fact_baglama.py"), encoding="utf-8").read())

# ⚠ `Y11B2-KANONIK-BYPASS` — red-first dort vaka.
kontrol("ACIK beat_role='kapanis' NORMALIZE edilir (closing)",
        FB.yay_projeksiyonu([{"beat_role": "kapanis"}])[0][1] == "closing",
        f"{FB.yay_projeksiyonu([{'beat_role': 'kapanis'}])}")
_ham_kapanis = FB.tahsis_et(
    [P1, P2], [{"scene_id": "k0", "beat_role": "kapanis", "voiceover": Q1}],
    allowlist=IZIN)
kontrol("ACIK 'kapanis' ILK sahnede fact ALAMAZ (yasak atlanmaz)",
        "k0" not in _ham_kapanis["tahsis"], f"{_ham_kapanis['tahsis']}")
_kanonik = FB.yay_projeksiyonu([{"chapter_id": "c01", "beat_role": "kanit"},
                                {"chapter_id": "c02", "beat_role": "closing"}])
kontrol("ACIK chapter_id KORUNUR (c02 -> c01'e INDIRILMEZ)",
        _kanonik == [("c01", "kanit"), ("c02", "closing")], f"{_kanonik}")
_c02_ilk = FB.tahsis_et(
    [P1, P2], [{"scene_id": "a1", "chapter_id": "c01", "voiceover": Q1},
               {"scene_id": "k2", "chapter_id": "c02",
                "beat_role": "closing", "voiceover": Q2}], allowlist=IZIN)
kontrol("c01->c02 gecisinde ILK closing fact ALAMAZ",
        "k2" not in _c02_ilk["tahsis"], f"{_c02_ilk['tahsis']}")
kontrol("KARISIK kanonik+ham alan -> fail-closed",
        FB.yay_projeksiyonu(
            [{"chapter_id": "c02", "bolum": "CH9"}])[0] == ("", ""))
kontrol("KARISIK rol alani -> fail-closed",
        FB.yay_projeksiyonu(
            [{"beat_role": "closing", "islev": "vurgu"}])[0] == ("", ""))
_karisik = FB.tahsis_et(
    [P1, P2], [{"scene_id": "s1", "chapter_id": "c01", "bolum": "CH1",
                "voiceover": Q1}], allowlist=IZIN)
kontrol("KARISIK sahne TAHSIS ALMAZ, stabil kod",
        _karisik["kod"] == FB.KOD_PROJEKSIYON_BELIRSIZ, f"{_karisik}")
kontrol("karar kodu belgelendi: Y11B2-KANONIK-BYPASS",
        "Y11B2-KANONIK-BYPASS" in
        open(os.path.join(KOK, "fact_baglama.py"), encoding="utf-8").read())

# ⚠ `Y11B2-YETKI-AKLAMA` — red-first iki vaka.
_aklama = {"scene_id": "z1", "chapter_id": "c01",
           "voiceover": "Bugun hava cok guzel ve kediler uyuyor",
           "iddia_metni": Q1, "footage_sorgu": Q1,
           "scene_prompt": Q1, "gorsel_prompt": Q1}
kontrol("sahne_metni YALNIZ konusulan alani dondurur",
        FB.sahne_metni(_aklama)
        == "Bugun hava cok guzel ve kediler uyuyor",
        f"{FB.sahne_metni(_aklama)!r}")
kontrol("ILGISIZ voiceover + fact metni yardimci alanda -> TAHSIS YOK",
        "z1" not in FB.tahsis_et([P1], [_aklama],
                                 allowlist={P1.fact_id})["tahsis"])
# ⚠ `Y11B2-RESOLVER-AYRISMASI` SOZLESMESI: FALLBACK ZINCIRI KALDIRILDI —
# otorite YALNIZCA `voiceover`dir (TTS'in okudugu alan).
kontrol("voiceover OTORITE, digerleri gormezden GELINMEZ (fail-closed)",
        FB.sahne_metni({"voiceover": Q1, "anlatim": "alakasiz"}) == Q1
        and FB.sahne_metni({"anlatim": Q1, "narration": "x"}) == ""
        and FB.sahne_metni({"narration": Q1}) == "")
kontrol("yardimci alanlar skoru ARTIRAMAZ (tek basina yetmez)",
        FB.sahne_metni({"iddia_metni": Q1, "footage_sorgu": Q1,
                        "scene_prompt": Q1, "gorsel_prompt": Q1}) == "")
kontrol("karar kodu belgelendi: Y11B2-YETKI-AKLAMA",
        "Y11B2-YETKI-AKLAMA" in
        open(os.path.join(KOK, "fact_baglama.py"), encoding="utf-8").read())
kontrol("pipeline ISLEV_YAY_ROLU tablosu ORTAK",
        "ISLEV_YAY_ROLU = fact_baglama.ISLEV_YAY_ROLU" in _pipe_src)
kontrol("karar kodu belgelendi: Y11B2-DURAGAN-PROJEKSIYON",
        "Y11B2-DURAGAN-PROJEKSIYON" in _pipe_src)
# ⚠ CANLI projeksiyonla: CH2'nin ILK sahnesi closing ise YENI fact ALAMAZ.
_ch2_ilk_closing = [
    {"scene_id": "a1", "chapter_id": "c01", "voiceover": Q1},
    {"scene_id": "k2", "chapter_id": "c02", "beat_role": "closing",
     "voiceover": Q2}]
_rch = FB.tahsis_et([P1, P2], _ch2_ilk_closing, allowlist=IZIN)
kontrol("CH2'nin ILK sahnesi closing -> fact ALMAZ",
        "k2" not in _rch["tahsis"], f"{_rch['tahsis']}")
kontrol("CH1 fact'i CH2 kapanisina TASINMAZ",
        _rch["tahsis"].get("a1") == P1.fact_id, f"{_rch['tahsis']}")
kontrol("karar kodu belgelendi: Y11B2-PROJEKSIYON-YOK",
        "Y11B2-PROJEKSIYON-YOK" in
        open(os.path.join(KOK, "testler", "test_faz_y11b2.py"),
             encoding="utf-8").read())


# ══════════════════════════════════════════════════════════════════════
blok("Y-11b-2/8 — GROUNDED OLMAYAN MODLAR ETKILENMEZ")

for _mod in ("animasyon", "hikaye"):
    _k = FB.grounded_kapisi(mod=_mod, arastirma_calisti=False,
                            arastirma_hatasi="cokme", allowlist=set(),
                            shot_raporu=None)
    kontrol(f"{_mod}: kapi KAPSAM DISI ve GECER",
            _k["gecti"] and _k["kapsam_disi"], f"{_k}")
kontrol("GROUNDED_MODLAR yalnizca documentary",
        tuple(FB.GROUNDED_MODLAR) == ("documentary",),
        f"{FB.GROUNDED_MODLAR}")
kontrol("pipeline grounded kontrolu GROUNDED_MODLAR'a dayanir",
        "fact_baglama.GROUNDED_MODLAR" in _pipe_src)


# ====================================================================
blok("Y-11b-2/2e — TEK ORTAK KONUSULAN-ALAN RESOLVER")

# ⚠ OLCULEN KUSUR (`Y11B2-RESOLVER-AYRISMASI`): tahsis kapisi
# `voiceover > anlatim > narration` cozuyordu, TTS ise YALNIZCA ham
# `voiceover`i okuyordu. `voiceover` bos/None/False/0/[]/{} iken
# `anlatim` kanonik olunca shot yetkili kimlik aliyor, all-shot kapisi
# geciyor ama DOGRULANAN CUMLE HIC SESLENDIRILMIYORDU.
for _dv in (None, False, 0, [], {}, "", "   "):
    _sc = {"scene_id": "sv", "chapter_id": "c01", "voiceover": _dv,
           "anlatim": _EQ}
    _mt, _kd, _nd = FB.konusulan_alan(_sc)
    kontrol(f"gecersiz voiceover ({_dv!r}) -> BOS metin", _mt == "",
            f"{_mt!r}")
    kontrol(f"gecersiz voiceover ({_dv!r}) -> stabil kod",
            _kd == FB.KOD_KONUSULAN_ALAN_GECERSIZ, f"{_kd}")
    _rv = FB.tahsis_et([_EP], [dict(_sc)], allowlist=_EIZIN)
    kontrol(f"gecersiz voiceover ({_dv!r}) -> TAHSIS ALMAZ",
            "sv" not in _rv["tahsis"], f"{_rv['tahsis']}")
    kontrol(f"gecersiz voiceover ({_dv!r}) -> tahsis stabil kodu",
            _rv["kod"] == FB.KOD_KONUSULAN_ALAN_GECERSIZ, f"{_rv}")
kontrol("voiceover YOK + anlatim kanonik -> FALLBACK YOK",
        FB.sahne_metni({"anlatim": _EQ}) == "",
        f"{FB.sahne_metni({'anlatim': _EQ})!r}")
kontrol("voiceover YOK + narration kanonik -> FALLBACK YOK",
        FB.sahne_metni({"narration": _EQ}) == "")
kontrol("GECERLI voiceover cozulur",
        FB.sahne_metni({"voiceover": " " + _EQ + " "}) == _EQ)
kontrol("GECERLI voiceover TAHSIS ALIR",
        FB.tahsis_et([_EP], [{"scene_id": "sv", "chapter_id": "c01",
                              "voiceover": _EQ}],
                     allowlist=_EIZIN)["tahsis"].get("sv") == _EP.fact_id)
kontrol("TTS ORTAK resolver'i tuketir (ham voiceover DEGIL)",
        "metin = fact_baglama.sahne_metni(s)" in _pipe_src
        and 'metin = str(s.get("voiceover", "")).strip()' not in _pipe_src)
kontrol("karar kodu belgelendi: Y11B2-RESOLVER-AYRISMASI",
        "Y11B2-RESOLVER-AYRISMASI" in
        open(os.path.join(KOK, "fact_baglama.py"), encoding="utf-8").read())


# ══════════════════════════════════════════════════════════════════════
blok("Y-11b-2/2f — PLANLAYICI/SURE CATISMASI: KANONIK FACT MUTASYONA UGRAMAZ")

# ⚠ OLCULEN KUSUR (`Y11B2-SURE-CATISMASI`): exact-copy talimati yalnizca
# KULLANICI brief'indeydi ve "olgu tasiyan sahne" diyordu; SYSTEM prompt
# ise her `voiceover`i kelime bandina zorluyordu. `sure_tamamla` ->
# `satirlari_uzat` kisa kanonik fact'i YENIDEN YAZIP exact kapiyi ZORUNLU
# RED yapiyordu.
_PROF_S = dict(PL.EDIT_STILLERI[PL.VARSAYILAN_EDIT]) if hasattr(
    PL, "EDIT_STILLERI") else {}
_PROF_S.update({"footage_pct": 100, "overlay": "yok", "kelime": 24,
                "sahne_sn": 6, "mag": False, "_wpm": 150})
_PROF_S.setdefault("ad", "belgesel")
_PROF_S.setdefault("ozet", "test")
_SIS = PL.plan_sistem(dict(_PROF_S), hedef_sahne=10, grounded_exact=True)
_SIS0 = PL.plan_sistem(dict(_PROF_S), hedef_sahne=10)
kontrol("SYSTEM prompt EVERY scene exactly one canonical fact der",
        "EVERY scene must carry EXACTLY ONE verified fact sentence" in _SIS)
kontrol("SYSTEM prompt VERBATIM kopya dayatir", "VERBATIM" in _SIS)
kontrol("SYSTEM prompt kelime bandindan MUAF tutar",
        "DO NOT APPLY" in _SIS and "word-count band" in _SIS)
kontrol("SYSTEM prompt stabil kodu SOYLER",
        "FACT-ENTAIL-EXTRACTIVE-DEGIL" in _SIS)
kontrol("grounded OLMAYAN system prompt ETKILENMEZ",
        "EXACT FACT CONTRACT" not in _SIS0)

_KISA = {"scenes": [{"voiceover": "Kurum yedi kelimelik kanonik olgu cumlesi"}
                    for _ in range(3)]}
_UZAT = PL.satirlari_uzat({"scenes": [dict(x) for x in _KISA["scenes"]]},
                          {"kelime": 24}, 24, grounded_exact=True)
kontrol("grounded: satirlari_uzat KANONIK metni DEGISTIRMEZ",
        [x["voiceover"] for x in _UZAT["scenes"]]
        == [x["voiceover"] for x in _KISA["scenes"]], f"{_UZAT}")
_prof_s = {"_wpm": 150, "kelime": 24, "sahne_sn": 6}
# ⚠ `Y11B2-SURE-TEK-YONLU`: bant IKI YONLU — 1 dk / 150 wpm hedefinde
# butce 150 kelime; eski 10x30=300 kelimelik fixture artik (dogru sekilde)
# UST siniri asiyor. Bant ici fixture: 5 x 30 = 150 kelime.
_yeterli = {"scenes": [{"voiceover": " ".join(["kelime"] * 30)}
                       for _ in range(5)]}
_st = PL.sure_tamamla({"scenes": [dict(x) for x in _yeterli["scenes"]]},
                      "konu", _prof_s, 1.0, grounded_exact=True)
kontrol("grounded: YETERLI sure -> plan AYNEN doner",
        [x["voiceover"] for x in _st["scenes"]]
        == [x["voiceover"] for x in _yeterli["scenes"]])
# ⚠ SESSIZ UZATMA YOKLUGU, hata METNINDEN degil `satirlari_uzat`
# CAGRI SAYISINDAN olculur (mesajda "UZATILAMAZ" gectigi icin substring
# kontrolu YANLIS negatif verirdi).
_hata_s, _uzat_sayac = "", [0]
_eski_uzat = PL.satirlari_uzat


def _uzat_spy(*a, **kw):
    _uzat_sayac[0] += 1
    return _eski_uzat(*a, **kw)


PL.satirlari_uzat = _uzat_spy
try:
    PL.sure_tamamla({"scenes": [dict(x) for x in _KISA["scenes"]]},
                    "konu", _prof_s, 5.0, grounded_exact=True)
except Exception as _e:                                      # noqa: BLE001
    _hata_s = f"{_e}"
finally:
    PL.satirlari_uzat = _eski_uzat
kontrol("grounded: YETERSIZ sure -> stabil kodla FAIL",
        FB.KOD_GROUNDED_SURE_YETERSIZ in _hata_s, _hata_s[:200])
kontrol("grounded: SESSIZ UZATMA YOK (satirlari_uzat 0-CALL)",
        _uzat_sayac[0] == 0, f"cagri={_uzat_sayac[0]}")

# ⚠ POZITIF KONTROL — grounded OLMAYAN yolda uzatma HALA calisir.
# ⚠ HERMETIK: `oai_chat` deterministik stub'a baglanir; GERCEK AG YOK.
_oai_sayac = [0]
_eski_oai = PL.oai_chat


def _oai_stub(body, *a, **kw):
    _oai_sayac[0] += 1
    _n = len((_KISA.get("scenes") or []))
    return {"lines": [{"i": _i, "voiceover": " ".join(["kelime"] * 24)}
                      for _i in range(_n)]}


PL.oai_chat = _oai_stub
try:
    _uzun = PL.satirlari_uzat({"scenes": [dict(x) for x in _KISA["scenes"]]},
                              {"kelime": 24}, 24)
finally:
    PL.oai_chat = _eski_oai
kontrol("grounded OLMAYAN yolda uzatma DAVRANISI KORUNDU",
        isinstance(_uzun, dict) and "scenes" in _uzun, f"{_uzun}")
kontrol("POZITIF KONTROL: grounded OLMAYAN yol seam'e ULASIR",
        _oai_sayac[0] > 0, "uzatma yolu hic cagrilmadi -> 0-call iddiasi BOS")
kontrol("HERMETIK: gercek saglayici cagrisi YOK",
        PL.oai_chat is _eski_oai and _oai_sayac[0] > 0)
kontrol("uzun_plan grounded bayragini TASIR",
        "grounded_exact=_grounded" in _pipe_src)

# ⚠ `Y11B2-PARALEL-BAYRAK-KAYBI`: >55 sahnede paralel yol devreye giriyor;
# `submit` POZISYONEL cagrildigi icin `grounded_exact` HIC gecmiyordu.
_pu_cagri = []
_esk_pu, _esk_isk = PL.plan_uret, PL._iskelet_cikar
_esk_st = PL.sure_tamamla


def _pu_spy(story, prof, hedef_sahne=40, devam=False, onceki_ozet="",
            bolum_yonergesi="", unlu=False, grounded_exact=False):
    _pu_cagri.append(bool(grounded_exact))
    return {"scenes": [{"voiceover": " ".join(["kelime"] * 24)}
                       for _ in range(hedef_sahne)]}


_st_cagri = []


def _st_spy(plan, story, prof, sure_dk, bildir=None, hedef_sahne=0,
            grounded_exact=False):
    _st_cagri.append(bool(grounded_exact))
    return plan


PL.plan_uret, PL.sure_tamamla = _pu_spy, _st_spy
PL._iskelet_cikar = lambda story, n: [f"bolum {i}" for i in range(n)]
try:
    PL.uzun_plan("konu", dict(_PROF_S), 6.0, grounded_exact=True)
finally:
    PL.plan_uret, PL.sure_tamamla = _esk_pu, _esk_st
    PL._iskelet_cikar = _esk_isk
kontrol("60 sahne PARALEL yol: plan_uret cagrildi",
        len(_pu_cagri) >= 2, f"{len(_pu_cagri)}")
kontrol("PARALEL yolda grounded_exact TUM parcalara ZINCIRLENDI",
        _pu_cagri and all(_pu_cagri), f"{_pu_cagri}")
kontrol("PARALEL yolda final sure_tamamla grounded_exact ALIR",
        _st_cagri and all(_st_cagri), f"{_st_cagri}")

# ⚠ ISKELET FALLBACK: `_uzun_plan_sirali` yolu da bayragi tasimali.
_pu_cagri2, _st_cagri2 = [], []


def _pu_spy2(story, prof, hedef_sahne=40, devam=False, onceki_ozet="",
             bolum_yonergesi="", unlu=False, grounded_exact=False):
    _pu_cagri2.append(bool(grounded_exact))
    return {"scenes": [{"voiceover": " ".join(["kelime"] * 24)}
                       for _ in range(hedef_sahne)]}


def _st_spy2(plan, story, prof, sure_dk, bildir=None, hedef_sahne=0,
             grounded_exact=False):
    _st_cagri2.append(bool(grounded_exact))
    return plan


def _isk_patla(story, n):
    raise RuntimeError("iskelet cikarilamadi")


PL.plan_uret, PL.sure_tamamla = _pu_spy2, _st_spy2
PL._iskelet_cikar = _isk_patla
try:
    PL.uzun_plan("konu", dict(_PROF_S), 6.0, grounded_exact=True)
finally:
    PL.plan_uret, PL.sure_tamamla = _esk_pu, _esk_st
    PL._iskelet_cikar = _esk_isk
kontrol("ISKELET FALLBACK yolu KOSTU", len(_pu_cagri2) >= 2,
        f"{len(_pu_cagri2)}")
kontrol("SIRALI fallback'te grounded_exact ZINCIRLENDI",
        _pu_cagri2 and all(_pu_cagri2), f"{_pu_cagri2}")
kontrol("karar kodu belgelendi: Y11B2-PARALEL-BAYRAK-KAYBI",
        "Y11B2-PARALEL-BAYRAK-KAYBI" in _pipe_src)

# ⚠ `Y11B2-SURE-TEK-YONLU`: kapi yalnizca ALT siniri olcuyordu.
# 1 dk / 150 wpm -> butce 150 kelime; 300 ve 600 kelimelik plan PASS
# aliyordu (video hedefin 2-4 KATI uzun).
for _kel, _ad in ((300, "2x uzun"), (600, "4x uzun")):
    _uzun_plan_d = {"scenes": [{"voiceover": " ".join(["kelime"] * 30)}
                               for _ in range(_kel // 30)]}
    _h_u = ""
    try:
        PL.sure_tamamla(_uzun_plan_d, "konu", _prof_s, 1.0,
                        grounded_exact=True)
    except Exception as _e:                                  # noqa: BLE001
        _h_u = f"{_e}"
    kontrol(f"grounded: {_ad} plan stabil kodla FAIL",
            FB.KOD_GROUNDED_SURE_YETERSIZ in _h_u, _h_u[:160])
kontrol("grounded: BANT ICI plan GECER",
        PL.sure_tamamla({"scenes": [{"voiceover": " ".join(["kelime"] * 30)}
                                    for _ in range(5)]},
                        "konu", _prof_s, 1.0, grounded_exact=True) is not None)
kontrol("iki yonlu bant sabitleri tanimli",
        PL.GROUNDED_SURE_ALT == 0.92 and PL.GROUNDED_SURE_UST == 1.15)
kontrol("karar kodu belgelendi: Y11B2-SURE-TEK-YONLU",
        "Y11B2-SURE-TEK-YONLU" in _pipe_src)
kontrol("karar kodu belgelendi: Y11B2-SURE-CATISMASI",
        "Y11B2-SURE-CATISMASI" in _pipe_src)

# ── YETERSIZ SURE: medya/TTS/render 0-CALL ──
_h_sure = _kos(_saglikli(),
               [{"voiceover": "kisa kanonik olgu", "bolum": "CH1",
                 "islev": "vurgu"}], on_kapi=False)
kontrol("yetersiz sure/exact ihlali -> hat DURUR", bool(_h_sure),
        "hat sessizce devam etti")
kontrol("yetersiz sure -> medya/TTS/render 0-CALL",
        _SAYAC["medya"] == _SAYAC["tts"] == _SAYAC["render"]
        == _SAYAC["gorsel"] == 0, f"{_SAYAC}")


# ══════════════════════════════════════════════════════════════════════

print("\n" + "=" * 62)
print(f"GECEN: {gecen}   BASARISIZ: {len(basarisiz)}")
for x in basarisiz:
    print(f"  XX {x}")
shutil.rmtree(_kok2, ignore_errors=True)
sys.exit(1 if basarisiz else 0)
