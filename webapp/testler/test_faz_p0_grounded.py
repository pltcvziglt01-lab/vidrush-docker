#!/usr/bin/env python3
"""FAZ P0 — GROUNDED SECIMI ACIK OLSUN (davranissal, red-first).

⚠ CANLI OLCUM (16 Agu 2026, uretim sunucusu):
    · normal belgesel isi -> `GROUNDED-FACT-YOK: kabul edilmis FactPacket
      YOK (0 yetkili olgu)`; medya/TTS/render'a HIC gecmeden oldu.
    · ikinci is -> `Hic sahne uretilemedi`.

⚠ OLCULEN KUSUR (`Y11B2-STRICT-VARSAYILAN`): strict fail-closed grounded
sozlesmesi TEK BASINA `mod == "documentary"` kosuluna baglanmisti
(`fact_baglama.GROUNDED_MODLAR = ("documentary",)`), ama arayuzde ve
API'de grounded SECIMI HIC YOKTU:
    · `/api/edit-stilleri` yalnizca eski `EDIT_STILLERI` sozlugunu doner
      ve o sozlukte `belgesel-arastirmaci` / `bilim-anlatisi` YOKTUR;
    · `/api/generate` bilinmeyen `edit` degerini SESSIZCE
      `VARSAYILAN_EDIT`e dusurur.
Yani "arastirma odakli belgesel" niyetini bildirmenin YOLU YOKTU ve
BELGESEL SECEN HERKES fail-closed hatta dusuyordu.

── SOZLESME (bu testin kilitledigi) ──
  · `strict_grounded_mi(mod, edit_id)` SAF: yalnizca documentary + ACIKCA
    secilmis strict profil (`belgesel-arastirmaci` | `bilim-anlatisi`).
  · VARSAYILAN belgesel BEST-EFFORT'tur: accepted FactPacket VARSA
    kullanilir; 0 fact / arastirma hatasi -> is GORUNUR uyari ile
    kullanici metninden NON-GROUNDED surer (downstream CAGRILIR).
  · STRICT profilde sozlesmenin TEK MADDESI de gevsetilmedi: 0 fact ->
    stabil kod + medya/TTS/render 0-CALL.
  · STRICT profilde accepted paket varsa hat DURMAZ.
  · API grounded profilleri ACIKCA listeler ve KABUL EDER.

Kosum: .venv-test/bin/python3 webapp/testler/test_faz_p0_grounded.py
"""
from __future__ import annotations

import asyncio
import contextlib
import io
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

URL1, URL2 = "https://www.npa.go.jp/rapor", "https://www.mhlw.go.jp/rapor"
Q1 = "In 2024, the National Police Agency recorded 76,941 cases of people"
Q2 = "Of these, 39.4% were aged 75 or older"


def _paket(onerme, alinti, url):
    p = FP.paket_kur(onerme=onerme, exact_quote=alinti,
                     belge_metni=alinti + ".\n", url=url, baslik="rapor",
                     erisim_tarihi="2026-08-15", kategori="rakam",
                     stance="support")
    p.verification_status = "accepted"
    return p


P1, P2 = _paket(Q1, Q1, URL1), _paket(Q2, Q2, URL2)
BELGELER = {P1.source_id: Q1 + ".\n", P2.source_id: Q2 + ".\n"}


# ══════════════════════════════════════════════════════════════════════
blok("P0/1 — strict_grounded_mi: SAF VE DAR")

kontrol("STRICT profil listesi TAM OLARAK iki profil",
        tuple(FB.STRICT_EDIT_PROFILLERI)
        == ("belgesel-arastirmaci", "bilim-anlatisi"),
        f"{FB.STRICT_EDIT_PROFILLERI}")
for _e in FB.STRICT_EDIT_PROFILLERI:
    kontrol(f"documentary + {_e} -> STRICT",
            FB.strict_grounded_mi("documentary", _e))
    kontrol(f"animasyon + {_e} -> STRICT DEGIL (mod kapsam disi)",
            not FB.strict_grounded_mi("animasyon", _e))
    kontrol(f"hikaye + {_e} -> STRICT DEGIL (mod kapsam disi)",
            not FB.strict_grounded_mi("hikaye", _e))
for _e in ("", None, "sinematik-belgesel", "anlati-video-essay",
           "seyahat-belgeseli", "veri-anlatisi", "hizli-explainer",
           "belgesel-arastirmaci-x", "BELGESEL-ARASTIRMACI"):
    kontrol(f"documentary + {_e!r} -> STRICT DEGIL (best-effort)",
            not FB.strict_grounded_mi("documentary", _e))
kontrol("bosluk kirpilir (' bilim-anlatisi ' -> STRICT)",
        FB.strict_grounded_mi(" documentary ", " bilim-anlatisi "))
kontrol("helper DETERMINISTIK (env/ag/dosya OKUMAZ)",
        all(FB.strict_grounded_mi("documentary", "bilim-anlatisi")
            for _ in range(5)))
_os_env = dict(os.environ)
os.environ["GROUNDED_MODLAR"] = "hepsi"
os.environ["STRICT_EDIT_PROFILLERI"] = "hepsi"
kontrol("ENV ile GEVSETILEMEZ / GENISLETILEMEZ",
        not FB.strict_grounded_mi("documentary", "sinematik-belgesel"))
os.environ.clear()
os.environ.update(_os_env)


# ══════════════════════════════════════════════════════════════════════
blok("P0/2 — grounded_kapisi KAPSAMI (mod, edit_id) CIFTIYLE BELIRLENIR")

_bos = dict(arastirma_calisti=False, arastirma_hatasi="", allowlist=set())
kontrol("VARSAYILAN belgesel -> KAPSAM DISI (PASS)",
        FB.grounded_kapisi(mod="documentary", edit_id="sinematik-belgesel",
                           **_bos) == {"gecti": True, "kapsam_disi": True,
                                       "kod": "", "neden":
                                       "mod='documentary' "
                                       "edit='sinematik-belgesel' STRICT "
                                       "grounded degil"})
kontrol("edit_id VERILMEDIYSE -> KAPSAM DISI (acik secim YOK)",
        FB.grounded_kapisi(mod="documentary", **_bos)["kapsam_disi"])
for _e in FB.STRICT_EDIT_PROFILLERI:
    _k = FB.grounded_kapisi(mod="documentary", edit_id=_e, **_bos)
    kontrol(f"{_e}: arastirma YOK -> FAIL-CLOSED",
            not _k["gecti"] and _k["kod"] == FB.KOD_GROUNDED_ARASTIRMA_YOK,
            f"{_k}")
    _k0 = FB.grounded_kapisi(mod="documentary", edit_id=_e,
                             arastirma_calisti=True, arastirma_hatasi="",
                             allowlist=set())
    kontrol(f"{_e}: 0 accepted fact -> {FB.KOD_GROUNDED_FACT_YOK}",
            not _k0["gecti"] and _k0["kod"] == FB.KOD_GROUNDED_FACT_YOK,
            f"{_k0}")
    _kh = FB.grounded_kapisi(mod="documentary", edit_id=_e,
                             arastirma_calisti=True,
                             arastirma_hatasi="ag coktu", allowlist={"f1"})
    kontrol(f"{_e}: arastirma HATASI -> FAIL-CLOSED",
            not _kh["gecti"]
            and _kh["kod"] == FB.KOD_GROUNDED_ARASTIRMA_HATA, f"{_kh}")
kontrol("yaratici modlar KAPSAM DISI KALIR (gerileme yok)",
        all(FB.grounded_kapisi(mod=_m, edit_id=_e, **_bos)["kapsam_disi"]
            for _m in ("animasyon", "hikaye")
            for _e in ("", "belgesel-arastirmaci")))
kontrol("karar kodu belgelendi: Y11B2-STRICT-VARSAYILAN",
        "Y11B2-STRICT-VARSAYILAN" in
        open(os.path.join(KOK, "pipeline.py"), encoding="utf-8").read())


# ══════════════════════════════════════════════════════════════════════
blok("P0/3 — URETIM HATTI: VARSAYILAN BEST-EFFORT, STRICT FAIL-CLOSED")

_kok2 = tempfile.mkdtemp(prefix="p0_kok_")
_uret_py = os.path.join(KOK, "..", "app", "uret.py")
if os.path.exists(_uret_py):
    shutil.copy(_uret_py, os.path.join(_kok2, "uret.py"))
sys.path.insert(0, _kok2)
os.environ["VIDRUSH_KOK"] = os.path.abspath(_kok2)
os.environ.setdefault("CIKTI_DIR", os.path.join(_kok2, "ciktilar"))
import pipeline as PL                                        # noqa: E402

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
_SAYAC = {"medya": 0, "gorsel": 0, "tts": 0, "render": 0}


class _Sonuc(AK.Sonuc):
    """GERCEK `arastirma_kopru.Sonuc` — sahte ikiz DEGIL."""


def _say(ad):
    def _f(*a, **kw):
        _SAYAC[ad] += 1
        raise AssertionError(f"{ad} SINIRI CAGRILDI")
    return _f


_SAHNE = [{"voiceover": Q1, "bolum": "CH1", "islev": "vurgu",
           "scene_prompt": "police office", "footage_sorgu": "police"},
          {"voiceover": Q2, "islev": "vurgu",
           "scene_prompt": "elderly", "footage_sorgu": "elderly"}]


def _kos(sonuc, sahneler, mod="documentary", edit_id=PL.VARSAYILAN_EDIT):
    """Hattin ONUNU sahteler, downstream sinirlarini SAYAR. -> (hata, log)"""
    for k in _SAYAC:
        _SAYAC[k] = 0
    _eski = []

    def _yaz(sahip, ad, deger):
        _eski.append((sahip, ad, getattr(sahip, ad)))
        setattr(sahip, ad, deger)

    _log = io.StringIO()
    try:
        _yaz(PL.arastirma_kopru, "arastir_ve_zenginlestir",
             lambda story, **kw: (story, sonuc))
        for _sahip, _ad, _sayac_ad in _SINIRLAR:
            if hasattr(_sahip, _ad):
                _yaz(_sahip, _ad, _say(_sayac_ad))
        _yaz(PL, "uzun_plan",
             lambda *a, **kw: {"scenes": [dict(x) for x in sahneler],
                               "baslik": "T", "aciklama": ""})
        _yaz(PL, "metin_islev_analizi", lambda *a, **kw: [])
        _yaz(PL, "karakter_analiz", lambda *a, **kw: {})
        _yaz(PL, "stil_analiz", lambda *a, **kw: {})
        try:
            with contextlib.redirect_stderr(_log):
                asyncio.get_event_loop().run_until_complete(
                    PL.uret("p0_test", "konu metni", "", mod=mod,
                            edit_id=edit_id, sure_dk=1))
            return "", _log.getvalue()
        except Exception as e:                               # noqa: BLE001
            return f"{e}", _log.getvalue()
    finally:
        for _sahip, _ad, _deger in reversed(_eski):
            setattr(_sahip, _ad, _deger)


def _saglikli():
    return _Sonuc(calisti=True, paketler=[P1, P2],
                  replay_belgeleri=dict(BELGELER))


_GKOD = (FB.KOD_GROUNDED_ARASTIRMA_YOK, FB.KOD_GROUNDED_ARASTIRMA_HATA,
         FB.KOD_GROUNDED_FACT_YOK, FB.KOD_GROUNDED_KANIT_COZULEMEDI,
         FB.KOD_GROUNDED_BOLUM_KAPSAMI, FB.KOD_SHOT_RAPORU_YOK,
         FB.KOD_SHOT_FACT_YOK, FB.KOD_SHOT_FACT_ALLOWLIST_DISI,
         "ARASTIRMA-HAVUZ-YETERSIZ")

# ── (a) VARSAYILAN BELGESEL + 0 FACT -> DOWNSTREAM CAGRILIR ──
for _ad, _sonuc in (("arastirma KOSMADI", _Sonuc(calisti=False)),
                    ("arastirma HATASI", _Sonuc(calisti=True,
                                                hata="ag coktu")),
                    ("0 YETKILI OLGU", _Sonuc(calisti=True)),
                    ("kanit COZULEMEDI",
                     _Sonuc(calisti=True, cozulemeyen=2))):
    _h, _l = _kos(_sonuc, _SAHNE)
    kontrol(f"VARSAYILAN belgesel / {_ad} -> grounded kodu CIKMAZ",
            not any(k in _h for k in _GKOD), _h[:200])
    kontrol(f"VARSAYILAN belgesel / {_ad} -> downstream CAGRILIR",
            sum(_SAYAC.values()) > 0, f"{_SAYAC} | {_h[:160]}")
    kontrol(f"VARSAYILAN belgesel / {_ad} -> uyari GORUNUR (sessiz dusus yok)",
            "GROUNDED BEST-EFFORT" in _l, _l[-300:])

# ── (b) STRICT + 0 FACT -> FAIL-CLOSED, 0-CALL ──
for _e in FB.STRICT_EDIT_PROFILLERI:
    for _ad, _sonuc, _kod in (
            ("arastirma KOSMADI", _Sonuc(calisti=False),
             FB.KOD_GROUNDED_ARASTIRMA_YOK),
            ("arastirma HATASI", _Sonuc(calisti=True, hata="ag coktu"),
             FB.KOD_GROUNDED_ARASTIRMA_HATA),
            ("0 YETKILI OLGU", _Sonuc(calisti=True),
             FB.KOD_GROUNDED_FACT_YOK),
            ("kanit COZULEMEDI",
             _Sonuc(calisti=True, paketler=[P1], cozulemeyen=2,
                    replay_belgeleri=dict(BELGELER)),
             FB.KOD_GROUNDED_KANIT_COZULEMEDI)):
        _h, _l = _kos(_sonuc, _SAHNE, edit_id=_e)
        kontrol(f"STRICT {_e} / {_ad} -> stabil kod {_kod}",
                _kod in _h, _h[:200])
        kontrol(f"STRICT {_e} / {_ad} -> medya/TTS/render 0-CALL",
                sum(_SAYAC.values()) == 0, f"{_SAYAC}")

# ── (c) STRICT + ACCEPTED PAKET -> HAT DURMAZ ──
for _e in FB.STRICT_EDIT_PROFILLERI:
    _h, _l = _kos(_saglikli(), _SAHNE, edit_id=_e)
    kontrol(f"STRICT {_e} / accepted paket -> grounded kodu CIKMAZ",
            not any(k in _h for k in _GKOD), _h[:200])
    kontrol(f"STRICT {_e} / accepted paket -> downstream CAGRILIR",
            sum(_SAYAC.values()) > 0, f"{_SAYAC} | {_h[:160]}")

# ── (d) VARSAYILAN BELGESEL + ACCEPTED PAKET -> OLGULAR KULLANILIR ──
_cagri = {"tahsis": 0}
_e2 = AK.yetkili_tahsis


def _tahsis_spy(*a, **kw):
    _cagri["tahsis"] += 1
    return _e2(*a, **kw)


PL.arastirma_kopru.yetkili_tahsis = _tahsis_spy
try:
    _h, _l = _kos(_saglikli(), _SAHNE)
finally:
    PL.arastirma_kopru.yetkili_tahsis = _e2
kontrol("VARSAYILAN belgesel accepted paketi KULLANIR (tahsis kosar)",
        _cagri["tahsis"] == 1, f"{_cagri}")
kontrol("VARSAYILAN belgesel accepted paketle de DURMAZ",
        not any(k in _h for k in _GKOD) and sum(_SAYAC.values()) > 0,
        f"{_SAYAC} | {_h[:160]}")

# ── (e) YARATICI MODLAR: GERILEME YOK ──
for _mod in ("animasyon", "hikaye"):
    _h, _l = _kos(_Sonuc(calisti=False), _SAHNE, mod=_mod,
                  edit_id=PL.VARSAYILAN_ANIM if _mod == "animasyon"
                  else PL.VARSAYILAN_HIKAYE)
    kontrol(f"{_mod}: grounded kodu CIKMAZ",
            not any(k in _h for k in _GKOD), _h[:160])
    kontrol(f"{_mod}: downstream SINIRA ULASIR",
            sum(_SAYAC.values()) > 0, f"{_SAYAC} | {_h[:160]}")


# ══════════════════════════════════════════════════════════════════════
blok("P0/4 — API: GROUNDED SECIMI ACIKCA VAR")

import server as SV                                          # noqa: E402

_liste = SV.edit_listesi()
_ids = [x["id"] for x in _liste]
for _e in FB.STRICT_EDIT_PROFILLERI:
    kontrol(f"/api/edit-stilleri '{_e}' profilini LISTELER", _e in _ids,
            f"{_ids}")
    _kayit = next((x for x in _liste if x["id"] == _e), {})
    kontrol(f"'{_e}' grounded=True isaretli", _kayit.get("grounded") is True,
            f"{_kayit}")
    kontrol(f"'{_e}' ozeti KAYNAK ZORUNLU oldugunu SOYLER",
            "KAYNAK ZORUNLU" in (_kayit.get("ozet") or ""), f"{_kayit}")
    kontrol(f"/api/generate '{_e}' degerini KABUL EDER (dusurmez)",
            SV._edit_gecerli(_e) == _e, SV._edit_gecerli(_e))
kontrol("eski stiller grounded=False ile KORUNUR",
        all(x["grounded"] is False for x in _liste
            if x["id"] in PL.EDIT_STILLERI)
        and all(k in _ids for k in PL.EDIT_STILLERI), f"{_ids}")
kontrol("bilinmeyen edit hala VARSAYILANA duser",
        SV._edit_gecerli("uydurma-stil") == PL.VARSAYILAN_EDIT)
kontrol("strict profil pipeline'da GERCEKTEN cozulur (sessiz varsayilan yok)",
        all(PL.profil_coz("documentary", _e).get("_stil_kimligi") == _e
            for _e in FB.STRICT_EDIT_PROFILLERI))


# ══════════════════════════════════════════════════════════════════════
blok("P0/5 — STRICT PROFIL OTOMATIK SECILMEZ (ACIK NIYET SART)")

import girdi_analizi as GA                                   # noqa: E402

# ⚠ Konsept tahmini `belgesel.true_crime` / `egitim.bilim` dallarinda
# STRICT profil ONERIR. Otomatik ATANIRSA normal isler yine fail-closed
# olur — P0 geri gelir. Oneri GORUNUR kalir, UYGULANMAZ.
_METIN = ("Bir cinayet davasinin dosyalari yeniden acildi. Polis raporu, "
          "tanik ifadeleri ve mahkeme kayitlari birbirini tutmuyor; "
          "savcilik delil zincirini yeniden inceliyor.")
_a = GA.analiz(_METIN)
_oto_edit = (_a.get("otomatik_secimler") or {}).get("edit", {}).get("deger")
kontrol("otomatik secim STRICT profil ATAMAZ",
        _oto_edit not in FB.STRICT_EDIT_PROFILLERI, f"{_oto_edit!r}")
for _e in FB.STRICT_EDIT_PROFILLERI:
    _u = GA.analiz(_METIN, kullanici_secimi={"edit": _e})
    kontrol(f"kullanicinin ACIK '{_e}' secimi KORUNUR",
            (_u.get("korunan_secimler") or {}).get("edit", {}).get("deger")
            == _e, f"{_u.get('korunan_secimler')}")
kontrol("STRICT oneri GIZLENMEZ (uyari ile gorunur)",
        (_a.get("stil_profili") or {}).get("kimlik")
        not in FB.STRICT_EDIT_PROFILLERI
        or any("KAYNAK ZORUNLU" in u
               for u in (_a["stil_profili"].get("uyari") or [])),
        f"{(_a.get('stil_profili') or {}).get('uyari')}")


# ══════════════════════════════════════════════════════════════════════

print("\n" + "=" * 62)
print(f"GECEN: {gecen}   BASARISIZ: {len(basarisiz)}")
for x in basarisiz:
    print(f"  XX {x}")
shutil.rmtree(_kok2, ignore_errors=True)
sys.exit(1 if basarisiz else 0)
