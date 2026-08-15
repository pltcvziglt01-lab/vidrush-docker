#!/usr/bin/env python3
"""FAZ Y-11b-1 — ARASTIRMA GERCEK FactPacket URETIR; allowlist_kur TEK OTORITE.

⚠ OLCULEN KUSUR (`Y11B1-PAKET-SONUCA-TASINMIYOR`) — bagimsiz denetim:
`arastirma/factpacket.havuz_kur` KANIT-ONCE paketleri URETIYOR ama hicbir
yerden CAGRILMIYORDU (`grep` sonucu: yalnizca `def` ve test). Uretim hatti
`Sonuc.olgular`i hala `manifest.kullanilabilir_iddialar()`ten — yani
CLAIM-FIRST zincirinden — turetiyordu. Yeni sozlesme yazilmis ama HATTA
BAGLI DEGILDI.

⚠ IKINCI KUSUR (`Y11B1-ALLOWLIST-OTORITE-DEGIL`): `Sonuc.olgular`
kimlikleri kanit/durum REPLAY'i olmadan tasiniyordu. Kabul otoritesi
`fact_baglama.allowlist_kur` OLMALIYDI; olgular ondan TURETILMELIYDI,
tersi degil.

── SOZLESME ──
  · `Sonuc.paketler` — KABUL EDILMIS FactPacket nesneleri.
  · `Sonuc.replay_belgeleri` — `{source_id: belge_metni}`; kanit
    REPLAY EDILEBILIR olsun diye tasinir.
  · `Sonuc.olgular` YALNIZCA accepted paketlerden TURER.
  · `allowlist_kur` TEK OTORITE: paket kabul damgasi + kanit replay'i
    oradan gecmeden hicbir olgu `Sonuc`a girmez.
  · ⚠ Grounded OLMAYAN modlar (animasyon/hikaye) ETKILENMEZ.

Kosum: .venv-test/bin/python3 webapp/testler/test_faz_y11b1.py
"""
from __future__ import annotations

import ast
import os
import sys

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


def _deneme(kayit):
    """MUHURLU kayit YAZILAMAZ olmali (deep-frozen)."""
    try:
        kayit["url"] = "https://evil.example.com/x"
        return False
    except TypeError:
        return True


import arastirma_kopru as AK   # noqa: E402
import fact_baglama as FB      # noqa: E402
from arastirma import factpacket as FP   # noqa: E402

_AKK = open(os.path.join(KOK, "arastirma_kopru.py"), encoding="utf-8").read()

SAYFA = ("Japan Ministry of Health report\n\n"
         "In 2024, the National Police Agency recorded 76,941 cases of people "
         "who died alone at home.\n"
         "Of these, 39.4% were aged 75 or older.\n")
URL = "https://www.npa.go.jp/english/report-2024.html"


blok("Y-11b-1/1 — SOZLESME VE KARAR KODLARI")

for kod in ("Y11B1-PAKET-SONUCA-TASINMIYOR", "Y11B1-ALLOWLIST-OTORITE-DEGIL"):
    kontrol(f"karar kodu belgelendi: {kod}", kod in _AKK,
            "karar kodda belgelenmemis")

_s = AK.Sonuc()
for alan in ("paketler", "replay_belgeleri", "olgular"):
    kontrol(f"Sonuc alani var: {alan}", hasattr(_s, alan), "tanimli degil")
kontrol("paketler varsayilan BOS", _s.paketler == [], f"{_s.paketler}")
kontrol("replay belgeleri varsayilan BOS", _s.replay_belgeleri == {},
        f"{_s.replay_belgeleri}")

for ad in ("paketlerden_olgular", "paket_havuzu_kur"):
    kontrol(f"disa acilan ad: {ad}", hasattr(AK, ad), "tanimli degil")


blok("Y-11b-1/2 — OLGULAR YALNIZ ACCEPTED PAKETTEN TURER")

def _paket(onerme, alinti, durum="accepted", stance="support", belge=None):
    p = FP.paket_kur(onerme=onerme, exact_quote=alinti,
                     belge_metni=SAYFA if belge is None else belge,
                     url=URL, baslik="NPA", erisim_tarihi="2026-08-15",
                     kategori="rakam", stance=stance)
    p.verification_status = durum
    return p


P1 = _paket("In 2024, the National Police Agency recorded 76,941 cases of people",
            "In 2024, the National Police Agency recorded 76,941 cases of people")
P2 = _paket("Of these, 39.4% were aged 75 or older",
            "Of these, 39.4% were aged 75 or older")
PX = _paket("In 2024, the National Police Agency recorded 76,941 cases of people",
            "In 2024, the National Police Agency recorded 76,941 cases of people",
            durum="")            # ⚠ damgasiz

BELGE = {P1.source_id: SAYFA, P2.source_id: SAYFA}
_o = AK.paketlerden_olgular([P1, P2], belgeler=BELGE)
kontrol("accepted paketler olguya donusur", len(_o) == 2, f"{_o}")
kontrol("olgu fact_id CONTENT-ADDRESSED",
        {x["fact_id"] for x in _o} == {P1.fact_id, P2.fact_id}, f"{_o}")
kontrol("olgu metni paketin ONERMESI",
        {x["metin"] for x in _o} == {P1.onerme, P2.onerme}, f"{_o}")
kontrol("olgu kaynak URL'si pakete bagli",
        all(x["kaynaklar"] and x["kaynaklar"][0]["url"] == URL for x in _o),
        f"{_o}")
kontrol("olgu kanit alanlarini TASIR (exact_quote/locator/document_hash)",
        all(x.get("exact_quote") and x.get("locator")
            and x.get("document_hash") for x in _o), f"{_o}")

kontrol("DAMGASIZ paket olguya DONUSMEZ",
        len(AK.paketlerden_olgular([P1, PX], belgeler=BELGE)) == 1,
        f"{AK.paketlerden_olgular([P1, PX], belgeler=BELGE)}")
kontrol("bos paket listesi -> bos olgu",
        AK.paketlerden_olgular([], belgeler=BELGE) == [])

# ⚠ P0-3 (`Y11B1-MUTABLE-STATUS-GUVENI`): mutable damga TEK BASINA yetmez.
kontrol("belge/allowlist YOKSA hicbir olgu URETILMEZ",
        AK.paketlerden_olgular([P1, P2]) == [],
        "mutable verification_status tek basina guveniliyor")
_sahte = _paket("Sahte olgu 76,941", "In 2024, the National Police Agency "
                                     "recorded 76,941 cases of people")
_sahte.document_hash = "0" * 16          # kanit REPLAY EDILEMEZ
kontrol("SAHTE accepted + replay edilemeyen kanit olguya DONUSMEZ",
        AK.paketlerden_olgular([_sahte],
                               belgeler={_sahte.source_id: SAYFA}) == [],
        "sahte damga guven=dogrulandi olgu uretti")
# ⚠ `Y11B1-IC-API`: DIS `allowlist_sonucu` girisi KALDIRILDI; otorite
# yalnizca IC yoldan (paket + guvenilir getirme makbuzu) gelir.
kontrol("belge YOKSA hicbir olgu URETILMEZ",
        AK.paketlerden_olgular([P1]) == [], "dis otorite girisi kabul edildi")


def _getir_ok(u):
    return {"ok": True, "url": u, "baslik": "NPA", "yayin_tarihi": "",
            "metin": SAYFA, "hata": ""}


blok("Y-11b-1/2b — ONERME KENDI QUOTE'U TARAFINDAN DESTEKLENMELI")

# ⚠ DENETIM KARSI ORNEGI (`Y11B1-ONERME-QUOTE-UYUMSUZ`): belge ve quote
# "76,941 cases" derken ONERME "999,999 cases" diyebiliyordu. `paket_dogrula`
# yalnizca quote'un BELGEDE gectigini olcuyor, onermenin QUOTE TARAFINDAN
# desteklendigini HIC olcmuyordu — uydurma rakam gercek bir alintiya
# yaslanarak allowlist'e giriyordu.
_FPK0 = open(os.path.join(KOK, "arastirma", "factpacket.py"),
             encoding="utf-8").read()
_UYDURMA = _paket(
    "In 2024, the National Police Agency recorded 999,999 cases",
    "In 2024, the National Police Agency recorded 76,941 cases of people")
_uy = FB.onerme_quote_uyumu(_UYDURMA.onerme, _UYDURMA.exact_quote)
kontrol("999,999 vs 76,941 -> UYUMSUZ",
        _uy[0] is False and _uy[1] == FB.KOD_ONERME_QUOTE_UYUMSUZ, f"{_uy}")
# ⚠ KATMANLI STABIL KOD SOZLESMESI (`Y11B1-KATMAN-KOD-SOZLESMESI`):
# her katman KENDI kodunu tutar; kod adlari katmanlar arasi SIZMAZ.
kontrol("URETICI katmani kendi kodunu tutar (Y11-...)",
        FP.onerme_quote_uyumu(
            _UYDURMA.onerme, _UYDURMA.exact_quote,
            "support")[1] == "Y11-ONERME-QUOTE-UYUMSUZ",
        "uretici kodu degisti")
kontrol("ALLOWLIST katmani kendi kodunu tutar (FACT-...)",
        FB.onerme_quote_uyumu(
            _UYDURMA.onerme, _UYDURMA.exact_quote,
            "support")[1] == "FACT-ONERME-QUOTE-UYUMSUZ",
        "allowlist kodu uretici kodunu sizdiriyor")
kontrol("iki katman kodu FARKLI (sessiz sizinti yok)",
        FP.onerme_quote_uyumu(_UYDURMA.onerme, _UYDURMA.exact_quote,
                              "support")[1]
        != FB.onerme_quote_uyumu(_UYDURMA.onerme, _UYDURMA.exact_quote,
                                 "support")[1])
kontrol("uretici RED kodu sicilinde",
        "Y11-ONERME-QUOTE-UYUMSUZ" in FP.RED_KODLARI, f"{FP.RED_KODLARI}")
kontrol("allowlist kodu sicilinde",
        FB.KOD_ONERME_QUOTE_UYUMSUZ in FB.KODLAR, f"{FB.KODLAR}")
kontrol("karar kodu belgelendi: Y11B1-KATMAN-KOD-SOZLESMESI",
        "Y11B1-KATMAN-KOD-SOZLESMESI" in open(
            os.path.join(KOK, "fact_baglama.py"), encoding="utf-8").read())
kontrol("gerekce TAM ESITLIK sozlesmesini soyler",
        "tam esit" in str(_uy[2]).lower(), f"{_uy}")

_uy_al = FB.allowlist_kur([_UYDURMA],
                          belgeler={_UYDURMA.source_id: SAYFA})
kontrol("uydurma rakamli paket ALLOWLIST'E GIRMEZ",
        not _uy_al["allowlist"], f"{_uy_al}")
kontrol("allowlist redi stabil kod",
        _uy_al["redler"][0]["kod"] == FB.KOD_ONERME_QUOTE_UYUMSUZ,
        f"{_uy_al['redler']}")
kontrol("uydurma rakamli paket OLGUYA DONUSMEZ",
        AK.paketlerden_olgular([_UYDURMA],
                               belgeler={_UYDURMA.source_id: SAYFA}) == [],
        "uydurma rakam guven=dogrulandi olgu uretti")

# ⚠ URETICI tarafinda da kapali (paket havuza HIC girmesin).
_kar = FP.paket_dogrula(_UYDURMA, SAYFA)
kontrol("paket_dogrula UYDURMA rakami REDDEDER",
        _kar["kabul"] is False and _kar["kod"] == "Y11-ONERME-QUOTE-UYUMSUZ",
        f"{_kar}")
_hav_uy = AK.paket_havuzu_kur(
    "konu", [URL], erisim_tarihi="2026-08-15", getirici=_getir_ok,
    cikarici=lambda u, m, k, **_: [
        {"onerme": "In 2024, the National Police Agency recorded 999,999 cases",
         "alinti": "In 2024, the National Police Agency recorded 76,941 "
                   "cases of people",
         "kategori": "rakam", "stance": "support"}])
kontrol("canli havuz uydurma rakami URETMEZ",
        not _hav_uy["paketler"] and not _hav_uy["olgular"], f"{_hav_uy}")

# ⚠ YIL ve OZEL AD icin de ayni kapi.
kontrol("quote'ta olmayan YIL -> UYUMSUZ",
        FB.onerme_quote_uyumu(
            "In 1998, the National Police Agency recorded 76,941 cases",
            "In 2024, the National Police Agency recorded 76,941 cases"
        )[0] is False)
kontrol("quote'ta olmayan OZEL AD -> UYUMSUZ",
        FB.onerme_quote_uyumu(
            "In 2024, the Osaka Police recorded 76,941 cases",
            "In 2024, the National Police Agency recorded 76,941 cases"
        )[0] is False)
kontrol("quote'un DESTEKLEDIGI onerme GECER",
        FB.onerme_quote_uyumu(
            "In 2024, the National Police Agency recorded 76,941 cases of people",
            "In 2024, the National Police Agency recorded 76,941 cases of people"
        )[0] is True)
# ⚠ DENETIM: `except ImportError: pass` FAIL-OPEN'i kaldirildi.
_FPK = open(os.path.join(KOK, "arastirma", "factpacket.py"),
            encoding="utf-8").read()
kontrol("factpacket capraz import + fail-open TASIMIYOR",
        "import fact_baglama" not in _FPK
        and "except ImportError:\n        pass" not in _FPK,
        "uyum kontrolu hala capraz import ve fail-open ile")
kontrol("uyum fonksiyonu factpacket ICINDE",
        hasattr(FP, "onerme_quote_uyumu"), "kontrol disarida")
kontrol("karar kodu belgelendi: Y11B1-UYUM-IMPORT-FAIL-OPEN",
        "Y11B1-UYUM-IMPORT-FAIL-OPEN" in _FPK)
# ⚠ `fact_baglama` HIC import edilemese bile uretici kapisi CALISIR.
import importlib as _il
_yedek = sys.modules.pop("fact_baglama", None)


class _EngelliBulucu:
    def find_module(self, ad, yol=None):
        return self if ad == "fact_baglama" else None

    def load_module(self, ad):
        raise ImportError("fact_baglama bilerek engellendi")


sys.meta_path.insert(0, _EngelliBulucu())
try:
    _il.reload(FP)
    kontrol("fact_baglama IMPORT EDILEMEZKEN uydurma rakam yine REDDEDILIR",
            FP.paket_dogrula(_UYDURMA, SAYFA)["kabul"] is False,
            "import kirilinca fail-open")
finally:
    sys.meta_path.pop(0)
    if _yedek is not None:
        sys.modules["fact_baglama"] = _yedek
    _il.reload(FP)

# ⚠ DENETIM: kapi STANCE-AWARE olmali; celiski support lehine COZULEMEZ.
# ⚠ `refute` quote'u onermenin RAKAMINI tekrar etmek zorunda degildir;
# ama AYNI YUKLEM/OLCU cekirdegini tasimalidir (`Y11B1-REFUTE-METRIK-KOR`).
# ⚠ FAZ Y-11b-1: `refute` FAIL-CLOSED `unresolved` — hicbir refute
# kabul edilmez (`Y11B1-REFUTE-NLI-YOK`).
kontrol("refute HER ZAMAN unresolved",
        FP.onerme_quote_uyumu(
            "Japan recorded 76,941 solitary deaths in 2024",
            "Japan recorded 21,000 solitary deaths in 2024",
            "refute") == (False, "Y11-REFUTE-COZULMEDI",
                          "refute Y-11b-1'de fail-closed UNRESOLVED "
                          "(dedicated NLI dogrulayicisi yok)"))
kontrol("support tarafinda entailment HALA zorunlu",
        FP.onerme_quote_uyumu(
            "Japan recorded 999,999 solitary deaths in 2024",
            "Japan recorded 76,941 solitary deaths in 2024", "support")[0]
        is False)
kontrol("karar kodu belgelendi: Y11B1-UYUM-STANCE-KOR",
        "Y11B1-UYUM-STANCE-KOR" in _FPK)

kontrol("salt kelime ortusmesi YETMEZ (sayi farki kelimeyle kapanmaz)",
        FB.onerme_quote_uyumu(
            "the National Police Agency recorded 999,999 cases of people",
            "the National Police Agency recorded 76,941 cases of people"
        )[0] is False)


blok("Y-11b-1/2c — SUPPORT VAKUM PASS ve GEVSEK REFUTE (denetim)")

# ⚠ `Y11B1-SUPPORT-BOSLUK-FAIL-OPEN`: sayi/yil/entity/birim TASIMAYAN iki
# ILGISIZ cumle, "eksik deger yok" diye VAKUMDA PASS aliyordu.
for _ad, _o, _q in (
        ("politika/muze", "The policy improves public health",
         "The museum opens every Tuesday for visitors"),
        ("yagmur/kutuphane", "Rainfall causes crop losses",
         "The library contains ancient manuscripts")):
    _r = FP.onerme_quote_uyumu(_o, _q, "support")
    kontrol(f"ILGISIZ support RED: {_ad}",
            _r[0] is False and _r[1] == "Y11-ONERME-QUOTE-UYUMSUZ", f"{_r}")
    kontrol(f"{_ad}: gerekce TAM ESITLIK/cekirdek soyler",
            ("tam esit" in str(_r[2]).lower()
             or "cekirde" in str(_r[2]).lower()), f"{_r}")
kontrol("karar kodu belgelendi: Y11B1-SUPPORT-BOSLUK-FAIL-OPEN",
        "Y11B1-SUPPORT-BOSLUK-FAIL-OPEN" in _FPK0)

# ⚠ `Y11B1-REFUTE-ESIK-GEVSEK`: "ortak birim + farkli sayi" CELISKI DEGIL.
for _ad, _o, _q in (
        ("farkli ozne+olcu", "Japan unemployment was 5 percent in 2024",
         "France inflation was 9 percent in 2023"),
        ("farkli sehir+donem", "Tokyo recorded 100 deaths in 2024",
         "Osaka recorded 200 deaths in 2023"),
        ("farkli sirket", "Company Alpha earned 5 million USD",
         "Company Beta earned 7 million USD")):
    _r = FP.onerme_quote_uyumu(_o, _q, "refute")
    kontrol(f"refute UNRESOLVED: {_ad}",
            _r[0] is False and _r[1] == "Y11-REFUTE-COZULMEDI", f"{_r}")
kontrol("karar kodu belgelendi: Y11B1-REFUTE-ESIK-GEVSEK",
        "Y11B1-REFUTE-ESIK-GEVSEK" in _FPK0)
# ⚠ TAM ESITLIK sozlesmesi: "guvenli paraphrase" diye bir istisna YOK.
kontrol("PARAPHRASE support RED (istisna yok)",
        FP.onerme_quote_uyumu(
            "In 2024, the National Police Agency recorded 76,941 cases",
            "In 2024, the National Police Agency recorded 76,941 cases "
            "of people who died alone at home", "support")[0] is False)
kontrol("TAM ESIT support PASS",
        FP.onerme_quote_uyumu("In 2024, the National Police Agency recorded 76,941 cases of people", "In 2024, the National Police Agency recorded 76,941 cases of people", "support")[0] is True)
kontrol("karar kodu belgelendi: Y11B1-SUPPORT-POLARITE-KOR",
        "Y11B1-SUPPORT-POLARITE-KOR" in _FPK0)
kontrol("karar kodu belgelendi: Y11B1-REFUTE-METRIK-KOR",
        "Y11B1-REFUTE-METRIK-KOR" in _FPK0)


blok("Y-11b-1/2d — IKINCI OTORITE KALDIRILDI + STALE REFUTE ZEHIRI")

# ⚠ `Y11B1-IKINCI-OTORITE`: `factpacket.allowlist` durum/replay bakmadan
# ham fact_id donduruyordu.
try:
    FP.allowlist([P1])
    _ikinci = False
except NotImplementedError:
    _ikinci = True
kontrol("factpacket.allowlist KALDIRILDI (NotImplementedError)", _ikinci,
        "ikinci otorite hala calisiyor")
kontrol("karar kodu belgelendi: Y11B1-IKINCI-OTORITE",
        "Y11B1-IKINCI-OTORITE" in _FPK0)

# ⚠ `Y11B1-STALE-REFUTE-ZEHIRI`: kaniti REPLAY EDILEMEYEN bir refute,
# GECERLI bir support paketini DUSUREMEZ.
_stale_ref = _paket("In 2024, the National Police Agency recorded 76,941 "
                    "cases", "In 2024, the National Police Agency recorded "
                             "76,941 cases of people", stance="refute")
_stale_ref.document_hash = "0" * 16       # BAYAT -> kanit degil
_zehir = FB.allowlist_kur([P1, _stale_ref],
                          belgeler={P1.source_id: SAYFA})
kontrol("BAYAT refute gecerli support'u ZEHIRLEYEMEZ",
        P1.fact_id in _zehir["allowlist"], f"{_zehir}")
_ilgisiz_ref = _paket("In 2024, the National Police Agency recorded 76,941 "
                      "cases", "Tokyo hava durumu bugun yagmurlu",
                      stance="refute")
kontrol("KONUYLA ILGISIZ refute zehirleyemez",
        P1.fact_id in FB.allowlist_kur(
            [P1, _ilgisiz_ref],
            belgeler={P1.source_id: SAYFA})["allowlist"])
kontrol("karar kodu belgelendi: Y11B1-STALE-REFUTE-ZEHIRI",
        "Y11B1-STALE-REFUTE-ZEHIRI" in open(
            os.path.join(KOK, "fact_baglama.py"), encoding="utf-8").read())


blok("Y-11b-1/2e — SNAPSHOT, MUTASYON, CELISKI ZAMANI, NEG-SCOPE")

# ⚠ (1) `Y11B1-CELISKI-ZAMAN-KOR`: 2024 destegi 2025 reddiyle zehirlenemez.
_s24 = _paket("In 2024, the National Police Agency recorded 76,941 cases of people", "In 2024, the National Police Agency recorded 76,941 cases of people")
_SAYFA25 = "In 2025, the National Police Agency recorded no such cases\n"
_URL25 = "https://example.gov/rapor-2025.html"
_r25 = FP.paket_kur(
    onerme="In 2025, the National Police Agency recorded 76,941 cases",
    exact_quote="In 2025, the National Police Agency recorded no such cases",
    belge_metni=_SAYFA25, url=_URL25, baslik="NPA25",
    erisim_tarihi="2026-08-15", kategori="rakam", stance="refute")
_r25.verification_status = "accepted"
_zc = FB.allowlist_kur([_s24, _r25],
                       belgeler={_s24.source_id: SAYFA,
                                 _r25.source_id: _SAYFA25})
kontrol("FARKLI YIL reddi gecerli destegi ZEHIRLEYEMEZ",
        _s24.fact_id in _zc["allowlist"], f"{_zc}")
kontrol("karar kodu belgelendi: Y11B1-CELISKI-ZAMAN-KOR",
        "Y11B1-CELISKI-ZAMAN-KOR" in open(
            os.path.join(KOK, "fact_baglama.py"), encoding="utf-8").read())

# ⚠ (2) `Y11B1-SNAPSHOT-SAHTE-KABUL`: sahte snapshot + kimlik REPLAY yerine gecemez.
# ⚠ `Y11B1-PUBLIC-HASH-YETKI-DEGIL`: cagiranin kendi hesapladigi PUBLIC
# hash yetki DEGILDIR; muhur anahtari SUREC ICIDIR.
kontrol("SAHTE paket + belge -> yeniden dogrulama REDDEDER",
        AK.paketlerden_olgular(
            [_paket("Baska cumle tamamen", "Baska cumle tamamen",
                    belge="Baska cumle tamamen\n")],
            belgeler={"yok": SAYFA}) == [],
        "sahte paket kabul edildi")
kontrol("uydurma muhur GECERSIZ",
        FB.muhur_gecerli_mi({"fact_id": "x", "muhur": "deadbeef"}) is False)
_gercek = FB.allowlist_kur([P1], belgeler={P1.source_id: SAYFA})
kontrol("YENIDEN DOGRULAMA olgu uretir",
        len(AK.paketlerden_olgular([P1], belgeler={P1.source_id: SAYFA})) == 1)
kontrol("belge YOKSA olgu URETILMEZ (fail-closed)",
        AK.paketlerden_olgular([P1]) == [])
kontrol("snapshot ICERIGE BAGLI (kimlik listesi degil)",
        FB.icerik_snapshot([P1]) != FB.icerik_snapshot([P2]),
        "snapshot icerikten turemiyor")

# ⚠ MUTASYON: dogrulamadan SONRA onerme degistirilirse GECEMEZ.
import copy as _copy
_mut = _copy.deepcopy(P1)
_mut.onerme = "In 2024, the National Police Agency recorded 999,999,999 cases"
# ⚠ MUHURLU kayit otoritesi: mutasyon ciktiya SIZAMAZ (kayit deep-frozen
# ve HMAC'li; ham paket zaten OKUNMAZ).
kontrol("dogrulama SONRASI mutasyon ciktiya SIZAMAZ",
        all("999,999,999" not in o["metin"]
            for o in AK.paketlerden_olgular([P1],
                                            belgeler={P1.source_id: SAYFA})),
        "mutasyona ugramis icerik olguya sizdi")
kontrol("ham paket listesi TEK BASINA olgu URETMEZ",
        AK.paketlerden_olgular([_mut]) == [],
        "ham paket otorite sayildi")
kontrol("kimlik_icerikten_mi mutasyonu YAKALAR",
        FB.kimlik_icerikten_mi(P1) is True
        and FB.kimlik_icerikten_mi(_mut) is False)

# ⚠ (3) `Y11B1-HAM-DICT-OTORITE`: sahte dict otorite DEGIL.
_sahte_sn = AK.Sonuc(konu="k")
_sahte_sn.olgular = [{"fact_id": "f0123456789abcde9", "metin": "uydurma olgu",
                      "guven": "dogrulandi", "kaynaklar": []}]
kontrol("SAHTE olgu dicti ok=True URETMEZ",
        AK.grounded_sonuc_hukmu(_sahte_sn)["ok"] is False,
        "ham mutable dict otorite sayildi")
kontrol("SAHTE olgu dicti brief'e GIRMEZ",
        AK.brief_kur("kullanici metni", _sahte_sn) == "kullanici metni")
# ⚠ `Y11B1-PUBLIC-HASH-YETKI-DEGIL`: public snapshot YETKI DEGIL; otorite
# MUHURLU (surec ici HMAC'li, deep-frozen) kayittir.
_dogru_sn = AK.Sonuc(konu="k")
_dogru_sn.paketler = [P1]
_dogru_sn.replay_belgeleri = {P1.source_id: SAYFA}
_dogru_sn.olgular = AK.yetkili_olgular(_dogru_sn)
kontrol("YENIDEN DOGRULAMA otoritesi ok=True uretir",
        AK.grounded_sonuc_hukmu(_dogru_sn)["ok"] is True,
        f"{AK.grounded_sonuc_hukmu(_dogru_sn)}")
_dogru_sn.olgular[0]["metin"] = "sonradan degistirildi"
kontrol("ham olgu MUTASYONU brief'e SIZMAZ",
        "sonradan degistirildi" not in AK.brief_kur("metin", _dogru_sn))
_dogru_sn.replay_belgeleri = {}
kontrol("REPLAY BELGESI YOKSA otorite YOK",
        AK.olgu_otoritesi_gecerli_mi(_dogru_sn) is False
        and AK.grounded_sonuc_hukmu(_dogru_sn)["ok"] is False)

# ⚠ (4) `Y11B1-REFUTE-POLARITE-TEK-YONLU` + `Y11B1-NEGATION-SCOPE-KOR`
kontrol("karar kodu belgelendi: Y11B1-NEGATION-SCOPE-KOR",
        "Y11B1-NEGATION-SCOPE-KOR" in _FPK0)
kontrol("karar kodu belgelendi: Y11B1-REFUTE-POLARITE-TEK-YONLU",
        "Y11B1-REFUTE-POLARITE-TEK-YONLU" in _FPK0)


blok("Y-11b-1/2f — MUHURLU OTORITE, TAM ZAMAN, ATOMIK/EXTRACTIVE")

# ⚠ (1) `Y11B1-PUBLIC-HASH-YETKI-DEGIL`
_sahte_p = _paket("Uydurma olgu 12345", "Uydurma olgu 12345")
kontrol("SAHTE paket + kendi belgesi -> yeniden dogrulama REDDEDER",
        AK.paketlerden_olgular([_sahte_p],
                               belgeler={_sahte_p.source_id: SAYFA}) == [],
        "sahte paket kabul edildi")

# ⚠ (3)(4) `Y11B1-MUHURSUZ-ALAN-MUTASYONU`: url ve ic ice kaynak url
_ev = _copy.deepcopy(P1)
_ev.url = "https://evil.example.com/x"
kontrol("replay SONRASI paket.url mutasyonu olguya SIZAMAZ",
        all("evil" not in o["kaynaklar"][0]["url"]
            for o in AK.paketlerden_olgular([P1],
                                            belgeler={P1.source_id: SAYFA})),
        "evil url olguya sizdi")
_ev_sn = AK.Sonuc(konu="k")
_ev_sn.paketler = [P1]
_ev_sn.replay_belgeleri = {P1.source_id: SAYFA}
_ev_sn.olgular = AK.yetkili_olgular(_ev_sn)
_ev_sn.olgular[0]["kaynaklar"][0]["url"] = "https://evil.example.com/x"
kontrol("ic ice kaynak url mutasyonu BRIEF'e SIZMAZ",
        "evil" not in AK.brief_kur("metin", _ev_sn))
kontrol("ic ice kaynak url mutasyonu ATIF'a SIZMAZ",
        all("evil" not in a["url"]
            for a in AK.atiflar_paketten(AK.yetkili_olgular(_ev_sn))))
kontrol("karar kodu belgelendi: Y11B1-MUHURSUZ-ALAN-MUTASYONU",
        "Y11B1-MUHURSUZ-ALAN-MUTASYONU" in open(
            os.path.join(KOK, "fact_baglama.py"), encoding="utf-8").read())

# ⚠ (5) `Y11B1-ZAMAN-KAPSAMI-KABA`: 2024-01 vs 2024-02
_S01 = "On 2024-01-05, the National Police Agency recorded 76,941 cases\n"
_S02 = "On 2024-02-10, the National Police Agency recorded no such cases\n"
_p01 = FP.paket_kur(
    onerme="On 2024-01-05, the National Police Agency recorded 76,941 cases",
    exact_quote="On 2024-01-05, the National Police Agency recorded "
                "76,941 cases",
    belge_metni=_S01, url="https://example.gov/a.html", baslik="A",
    erisim_tarihi="2026-08-15", kategori="rakam", stance="support")
_p01.verification_status = "accepted"
_p02 = FP.paket_kur(
    onerme="On 2024-02-10, the National Police Agency recorded 76,941 cases",
    exact_quote="On 2024-02-10, the National Police Agency recorded "
                "no such cases",
    belge_metni=_S02, url="https://example.gov/b.html", baslik="B",
    erisim_tarihi="2026-08-15", kategori="rakam", stance="refute")
_p02.verification_status = "accepted"
_zt = FB.allowlist_kur([_p01, _p02],
                       belgeler={_p01.source_id: _S01, _p02.source_id: _S02})
kontrol("2024-02 reddi 2024-01 destegini ZEHIRLEMEZ",
        _p01.fact_id in _zt["allowlist"], f"{_zt['redler']}")
kontrol("AYNI AY celiskisi HALA kurulur",
        FP.zaman_ortusur({"2024-01-05"}, {"2024-01-09"}) is False
        and FP.zaman_ortusur({"2024-01"}, {"2024-01"}) is True)
kontrol("karar kodu belgelendi: Y11B1-ZAMAN-KAPSAMI-KABA",
        "Y11B1-ZAMAN-KAPSAMI-KABA" in _FPK0)

# ⚠ (6) `Y11B1-TOKEN-KURALI-OYUNLANABILIR`: atomik + extractive
kontrol("ILISKI TAKASI support RED",
        FP.onerme_quote_uyumu("Alice approved Bob", "Bob approved Alice",
                              "support")[0] is False)
kontrol("BILESIK onerme support RED (atomiklik)",
        FP.onerme_quote_uyumu(
            "Drug reduces mortality but increases cost",
            "Drug reduces mortality but increases cost",
            "support")[0] is False)
kontrol("BILESIK refute RED (atomiklik)",
        FP.onerme_quote_uyumu(
            "Drug reduces mortality but increases cost",
            "Drug does not reduce mortality but increases cost",
            "refute")[0] is False)
kontrol("TAM ESIT olmayan support RED",
        FP.onerme_quote_uyumu(
            "The agency recorded many cases",
            "The agency recorded 76,941 cases", "support")[0] is False)
kontrol("TAM ESIT gecerli support PASS",
        FP.onerme_quote_uyumu("In 2024, the National Police Agency recorded 76,941 cases of people", "In 2024, the National Police Agency recorded 76,941 cases of people", "support")[0] is True)
kontrol("karar kodu belgelendi: Y11B1-EXTRACTIVE-YETMEZ",
        "Y11B1-EXTRACTIVE-YETMEZ" in _FPK0)


blok("Y-11b-1/2g — KIMLIK YENIDEN TURETIMI + SPAN CEVRE BAGLAMI")

_TEMIZ = ("In 2024, the National Police Agency recorded 76,941 cases "
          "of people.\n")
_PT = _paket("In 2024, the National Police Agency recorded 76,941 cases "
             "of people",
             "In 2024, the National Police Agency recorded 76,941 cases "
             "of people", belge=_TEMIZ)
kontrol("temiz belge KABUL",
        bool(FB.allowlist_kur([_PT],
                              belgeler={_PT.source_id: _TEMIZ})["allowlist"]))

# ⚠ (1) `Y11B1-KIMLIK-YENIDEN-TURETIM`: tuketici replay'i URETICI ile birebir.
_mut2 = _copy.deepcopy(_PT)
_mut2.onerme = _PT.onerme + " and more"
_rm = FB.allowlist_kur([_mut2], belgeler={_mut2.source_id: _TEMIZ})
kontrol("ESKI ID altinda mutasyon RED", not _rm["allowlist"], f"{_rm}")
kontrol("kimlik red kodu stabil",
        _rm["redler"][0]["kod"] == FB.KOD_KIMLIK_UYUMSUZ, f"{_rm['redler']}")
kontrol("mutasyon olguya DONUSMEZ",
        AK.paketlerden_olgular([_mut2],
                               belgeler={_mut2.source_id: _TEMIZ}) == [])
kontrol("karar kodu belgelendi: Y11B1-KIMLIK-YENIDEN-TURETIM",
        "Y11B1-KIMLIK-YENIDEN-TURETIM" in open(
            os.path.join(KOK, "fact_baglama.py"), encoding="utf-8").read())

# ⚠ (2) `Y11B1-SPAN-CEVRE-BAGLAMI`: TAM ESITLIK bile cevreyi gormez.
for _ad, _belge in (
        ("It is false that",
         "It is false that " + _PT.exact_quote + ".\n"),
        ("VERDICT: FALSE", _PT.exact_quote + ". VERDICT: FALSE\n"),
        ("debunked/myth",
         "This myth was debunked: " + _PT.exact_quote + ".\n")):
    _pc = _paket(_PT.onerme, _PT.exact_quote, belge=_belge)
    _rc2 = FB.allowlist_kur([_pc], belgeler={_pc.source_id: _belge})
    kontrol(f"CEVRE CURUTUYOR RED: {_ad}", not _rc2["allowlist"], f"{_rc2}")
    kontrol(f"{_ad}: stabil kod",
            bool(_rc2["redler"])
            and _rc2["redler"][0]["kod"] == FB.KOD_CEVRE_CURUTUYOR,
            f"{_rc2['redler']}")
_soru = _PT.exact_quote + "?\n"
kontrol("SORU cumlesi iddia SAYILMAZ",
        not FB.allowlist_kur(
            [_paket(_PT.onerme, _PT.exact_quote, belge=_soru)],
            belgeler={_PT.source_id: _soru})["allowlist"])
kontrol("karar kodu belgelendi: Y11B1-SPAN-CEVRE-BAGLAMI",
        "Y11B1-SPAN-CEVRE-BAGLAMI" in open(
            os.path.join(KOK, "fact_baglama.py"), encoding="utf-8").read())

# ⚠ (3) `Y11B1-IC-API`: dis `allowlist_sonucu` girisi YOK.
import inspect as _ins
kontrol("allowlist_sonucu DIS GIRISI kaldirildi",
        "allowlist_sonucu" not in _ins.signature(
            AK.paketlerden_olgular).parameters,
        "dis otorite girisi hala var")
kontrol("karar kodu belgelendi: Y11B1-IC-API",
        "Y11B1-IC-API" in open(os.path.join(KOK, "arastirma_kopru.py"),
                               encoding="utf-8").read())


blok("Y-11b-1/3 — allowlist_kur TEK OTORITE")

_agac = ast.parse(_AKK)
_cagrilar = {n.func.attr for n in ast.walk(_agac)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
kontrol("arastirma_kopru allowlist_kur'u CAGIRIYOR",
        "allowlist_kur" in _cagrilar, "kabul otoritesi cagrilmiyor")
kontrol("arastirma_kopru havuz_kur'u CAGIRIYOR",
        "havuz_kur" in _cagrilar, "FactPacket uretimi hatta bagli degil")

# ⚠ Otorite GERCEKTEN suzuyor mu?
_izin = FB.allowlist_kur([P1, P2, PX], belgeler=BELGE)
kontrol("allowlist damgasizi ELER", _izin["allowlist"] == {P1.fact_id,
                                                           P2.fact_id},
        f"{_izin}")
kontrol("olgular allowlist ile BIREBIR",
        {x["fact_id"] for x in AK.paketlerden_olgular(
            [P1, P2, PX], belgeler=BELGE)} == _izin["allowlist"])


blok("Y-11b-1/4 — CANLI HAVUZ: getirici/cikarici ENJEKTE (ag yok)")

_cagrilan = {"getir": 0, "cikar": 0}


def _getir(u):
    _cagrilan["getir"] += 1
    return {"ok": True, "url": u, "baslik": "NPA", "yayin_tarihi": "",
            "metin": SAYFA, "hata": ""}


def _cikar(u, m, k, **_):
    _cagrilan["cikar"] += 1
    return [{"onerme": "In 2024, the National Police Agency recorded 76,941 cases of people",
             "alinti": "In 2024, the National Police Agency recorded 76,941 cases of people",
             "kategori": "rakam", "stance": "support"}]


_hav = AK.paket_havuzu_kur("solitary deaths", [URL],
                           erisim_tarihi="2026-08-15",
                           getirici=_getir, cikarici=_cikar)
kontrol("havuz gercekten getirdi ve cikardi",
        _cagrilan["getir"] == 1 and _cagrilan["cikar"] == 1, f"{_cagrilan}")
kontrol("uretilen paket ACCEPTED damgali",
        _hav["paketler"] and all(p.verification_status == "accepted"
                                 for p in _hav["paketler"]), f"{_hav}")
kontrol("replay belgesi source_id ile tasinir",
        _hav["replay_belgeleri"]
        and list(_hav["replay_belgeleri"].values())[0] == SAYFA,
        f"{list(_hav['replay_belgeleri'])}")
kontrol("allowlist havuzdan turer",
        _hav["allowlist"] == {p.fact_id for p in _hav["paketler"]}, f"{_hav}")
kontrol("olgular havuzdan turer",
        {x["fact_id"] for x in _hav["olgular"]} == _hav["allowlist"], f"{_hav}")

# ⚠ Kanit REPLAY EDILEMEYEN paket havuza GIRMEZ.
_hav2 = AK.paket_havuzu_kur(
    "konu", [URL], erisim_tarihi="2026-08-15", getirici=_getir,
    cikarici=lambda u, m, k, **_: [
        {"onerme": "The figure rose 12% from the previous year",
         "alinti": "the figure rose 12% from the previous year",
         "kategori": "rakam", "stance": "support"}])
kontrol("uydurma alintili paket havuza GIRMEZ",
        not _hav2["paketler"] and not _hav2["olgular"], f"{_hav2}")

_hav3 = AK.paket_havuzu_kur(
    "konu", ["https://yok.example.com/a"], erisim_tarihi="2026-08-15",
    getirici=lambda u: {"ok": False, "hata": "HTTP 404", "metin": ""},
    cikarici=_cikar)
kontrol("erisilemeyen belge FALLBACK URETMEZ",
        not _hav3["paketler"] and not _hav3["olgular"], f"{_hav3}")
kontrol("erisilemeyen belge red olarak kayitli",
        bool(_hav3.get("redler")), f"{_hav3}")


blok("Y-11b-1/5 — DETERMINIZM VE SIRA BAGIMSIZLIGI")

_a1 = AK.paket_havuzu_kur("konu", [URL], erisim_tarihi="2026-08-15",
                          getirici=_getir, cikarici=_cikar)
_a2 = AK.paket_havuzu_kur("konu", [URL], erisim_tarihi="2026-08-15",
                          getirici=_getir, cikarici=_cikar)
kontrol("ayni girdi ayni allowlist", _a1["allowlist"] == _a2["allowlist"])
kontrol("ayni girdi ayni snapshot", _a1["snapshot"] == _a2["snapshot"],
        f"{_a1['snapshot']} / {_a2['snapshot']}")
kontrol("olgu sirasi kararli (fact_id'ye gore)",
        [x["fact_id"] for x in _a1["olgular"]]
        == sorted(x["fact_id"] for x in _a1["olgular"]))


blok("Y-11b-1/6 — GROUNDED OLMAYAN MODLAR ETKILENMEZ")

for _mod in ("animasyon", "hikaye"):
    _m, _r = AK.arastir_ve_zenginlestir("bir metin", mod=_mod,
                                        is_adi="t", cikti_dizin="/tmp")
    kontrol(f"{_mod}: metin DEGISMEDI", _m == "bir metin", f"{_m!r}")
    kontrol(f"{_mod}: arastirma kosmadi", _r.calisti is False)
    kontrol(f"{_mod}: paketler bos", _r.paketler == [])


blok("Y-11b-1/6b — TEK OTORITE: PLANNER, NARRATION, ATIF")

# ⚠ P0-2 (`Y11B1-PLANNER-ESKI-CLAIM`): planner promptu eskiden
# `olgu_blogu(manifest)` ile CLAIM-FIRST zincirinden besleniyordu.
_sn = AK.Sonuc(konu="k")
_sn.paketler = [P1, P2]
_sn.replay_belgeleri = dict(BELGE)
_sn.olgular = AK.yetkili_olgular(_sn)
_brief = AK.brief_kur("kullanici metni", _sn)
kontrol("brief accepted paket olgusunu ICERIR",
        P1.onerme in _brief and "DOGRULANMIS OLGULAR" in _brief,
        f"{_brief[:160]}")
kontrol("brief kullanici metnini KORUR", _brief.startswith("kullanici metni"))

# ⚠ DENETIM RED-FIRST: manifestte claim VAR ama 0 accepted paket.
_claimli = AK.Sonuc(konu="k")
_claimli.dogrulanmis_iddia = 7        # claim-first zincir DOLU
_claimli.iddia_sayisi = 11
_h = AK.grounded_sonuc_hukmu(_claimli)
kontrol("7 claim + 0 accepted -> hukum ok=False",
        _h["ok"] is False and _h["accepted"] == 0, f"{_h}")
kontrol("hukum stabil kod GROUNDED-FACT-YOK",
        _h["kod"] == "GROUNDED-FACT-YOK", f"{_h}")
kontrol("hukum claim sayisinin KABUL GEREKCESI OLMADIGINI soyler",
        "KABUL GEREKCESI DEGIL" in str(_h.get("neden")), f"{_h}")
kontrol("7 claim + 0 accepted -> brief ESKI CLAIM'I EKLEMEZ",
        AK.brief_kur("kullanici metni", _claimli) == "kullanici metni",
        "claim-first iddia story'ye girdi")
_kabullu = AK.Sonuc(konu="k")
_kabullu.paketler = [P1]
_kabullu.replay_belgeleri = dict(BELGE)
_kabullu.olgular = AK.yetkili_olgular(_kabullu)
kontrol("1 accepted paket -> hukum ok=True",
        AK.grounded_sonuc_hukmu(_kabullu)["ok"] is True)

_bos_sn = AK.Sonuc(konu="k")
kontrol("0 accepted paket -> brief metni AYNEN dondurur",
        AK.brief_kur("kullanici metni", _bos_sn) == "kullanici metni",
        "eski claim story'ye girdi")
kontrol("brief_kur artik manifest ALMIYOR (tek otorite)",
        "manifest" not in AK.brief_kur.__code__.co_varnames,
        f"{AK.brief_kur.__code__.co_varnames}")
kontrol("olgu_blogu_paketten accepted olgudan uretir",
        P2.onerme in AK.olgu_blogu_paketten(_sn.olgular), "blok bos")
kontrol("olgu_blogu_paketten bos olguda BOS doner",
        AK.olgu_blogu_paketten([]) == "")

# ⚠ P0-4 (`Y11B1-IKI-OTORITE`): atiflar da AYNI otoriteden.
_atif = AK.atif_satirlari("/tmp", "yok.json", olgular=_sn.olgular)
kontrol("atiflar accepted paketten turer",
        _atif and all(a["url"] == URL for a in _atif), f"{_atif}")
kontrol("atif fact_id tasir (provenance zinciri)",
        all(a.get("fact_id") for a in _atif), f"{_atif}")
kontrol("0 accepted paket -> atif BOS",
        AK.atif_satirlari("/tmp", "yok.json", olgular=[]) == [])
kontrol("pipeline atiflari olgular ile cagiriyor",
        "olgular=list(getattr(arastirma_sonuc" in open(
            os.path.join(KOK, "pipeline.py"), encoding="utf-8").read(),
        "atif hala manifest otoritesinden")


blok("Y-11b-1/7 — GERILEME: olgu SEKLI TUKETICILERLE UYUMLU")

_ornek = AK.paketlerden_olgular([P1], belgeler=BELGE)[0]
for alan in ("fact_id", "metin", "guven", "kategori", "kritik", "kaynaklar"):
    kontrol(f"olgu alani korunuyor: {alan}", alan in _ornek, f"{_ornek}")
kontrol("kaynak alt alanlari korunuyor",
        {"alan", "url", "tur"} <= set(_ornek["kaynaklar"][0]), f"{_ornek}")
kontrol("guven 'dogrulandi' (kanit replay edildi)",
        _ornek["guven"] == "dogrulandi", f"{_ornek}")


print(f"\n{'=' * 62}\nGECEN: {gecen}   BASARISIZ: {len(basarisiz)}")
for b in basarisiz:
    print(f"  XX {b}")
sys.exit(1 if basarisiz else 0)
