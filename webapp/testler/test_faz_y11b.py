#!/usr/bin/env python3
"""FAZ Y-11b — FACTPACKET CANLI HATTA; SIMILARITY TAHMINI KALDIRILDI.

⚠ KODDAN DOGRULANAN KUSURLAR (bu atomun kapattiklari):

  1. `Y11B-SIMILARITY-TAHMINI` — `arastirma_kopru.fact_bagla` sahneyi
     olguya 0.16 JACCARD ORTUSMESI ile bagliyordu (`FACT_ESIK = 0.16`,
     yorumu: "Deger sezgisel; test bunu sabitliyor, uydurma degil ama
     OLCULMEDI"). fact_id URETIM ANINDA verilmiyor, SONRADAN METIN
     BENZERLIGIYLE TAHMIN EDILIYORDU.
  2. `Y11B-PREFILLED-KABUL` — `arastirma_kopru.py:249-253`: sahnede
     onceden yazili bir `fact_id` varsa DOGRULANMADAN "baglandi" sayilip
     kapsama ekleniyordu. Enjekte edilmis herhangi bir dizge kapiyi
     geciyordu.
  3. `Y11B-GENEL-ATIF-FALLBACK` — `researcher.py:317-321`: model bir
     iddiaya atif vermezse ARAMANIN GENEL ilk 2 atfi o iddiaya
     YAPISTIRILIYORDU. Iddia ile o sayfanin ilgisi OLCULMEMISTIR.
  4. `Y11B-SADECE-FOOTAGE` — `fact_bagla(yalnizca_footage=True)` ve
     `qa_on.py:298` (`if c.kaynak_turu != "medya": continue`): fact
     denetimi YALNIZCA footage/medya cekimlerine bakiyordu; fallback ve
     AI sahneler fact zorunlulugundan MUAFTI.
  5. `Y11B-GROUNDED-FAIL-OPEN` — `pipeline` olgu kapisi `if _olgular:`
     blogunun ICINDEYDI: arastirma KAPALI, HATALI ya da 0 olgu ise kapi
     HIC KOSMUYOR ve is kullanici metniyle SESSIZCE devam ediyordu.

── URETIM SOZLESMESI ──
  accepted FactPacket -> SectionPlan -> FactBeat -> narration/shot
  · Her render edilen shot URETIM ANINDA tam bir `primary_fact_id` alir.
  · Kimlik CONTENT-ADDRESSED; SIMILARITY ile BULUNMAZ.
  · Allowlist'e yalnizca `verification_status=accepted` VE kaniti REPLAY
    EDILEBILIR paket girer: exact_quote + locator + document_hash +
    source_id/canonical_url + stance=SUPPORT.
  · Ayni fact BIRDEN COK shotta kullanilabilir.

Kosum: .venv-test/bin/python3 webapp/testler/test_faz_y11b.py
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


fb = None
try:
    import fact_baglama as fb
    kontrol("modul yuklendi: webapp/fact_baglama.py", True)
except Exception as e:
    kontrol("modul yuklendi: webapp/fact_baglama.py", False,
            f"{type(e).__name__}: {e}")

if fb is None:
    print(f"\n{'=' * 62}\nGECEN: {gecen}   BASARISIZ: {len(basarisiz)}")
    for b in basarisiz:
        print(f"  XX {b}")
    sys.exit(1)

from arastirma import factpacket as FP   # noqa: E402

SAYFA = ("Japan Ministry of Health report\n\n"
         "In 2024, the National Police Agency recorded 76,941 cases of people "
         "who died alone at home.\n"
         "Of these, 39.4% were aged 75 or older.\n"
         # ⚠ Celiski kurgusu icin AYNI ozneyi olumsuzlayan cumle
         # (`refute` kapisi ACIK CELISKI ister).
         "The National Police Agency recorded no such cases of people.\n")
URL = "https://www.npa.go.jp/english/report-2024.html"


def paket(onerme, alinti, url=URL, stance="support", belge=SAYFA,
          durum="accepted"):
    """⚠ Kabul damgasi URETICIDEN gelir: `paket_dogrula` gecen paketi
    `havuz_kur` `accepted` damgalar. Test fixture'i o damgayi ACIKCA
    tasir — "alan yoksa accepted say" gevsemesi YOKTUR."""
    p = FP.paket_kur(onerme=onerme, exact_quote=alinti, belge_metni=belge,
                     url=url, baslik="NPA", erisim_tarihi="2026-08-15",
                     kategori="rakam", stance=stance)
    p.verification_status = durum
    return p


P1 = paket("In 2024, the National Police Agency recorded 76,941 cases of people",
           "In 2024, the National Police Agency recorded 76,941 cases of people")
P2 = paket("Of these, 39.4% were aged 75 or older",
           "Of these, 39.4% were aged 75 or older")


blok("Y-11b/1 — SOZLESME VE KARAR KODLARI")

_FBK = open(os.path.join(KOK, "fact_baglama.py"), encoding="utf-8").read()
for kod in ("Y11B-SIMILARITY-TAHMINI", "Y11B-PREFILLED-KABUL",
            "Y11B-GENEL-ATIF-FALLBACK", "Y11B-SADECE-FOOTAGE",
            "Y11B-GROUNDED-FAIL-OPEN"):
    kontrol(f"karar kodu belgelendi: {kod}", kod in _FBK)
for ad in ("allowlist_kur", "shot_fact_dogrula", "grounded_kapisi",
           "entail_dogrula", "KODLAR"):
    kontrol(f"disa acilan ad: {ad}", hasattr(fb, ad), "tanimli degil")


blok("Y-11b/2 — ALLOWLIST: YALNIZ ACCEPTED + REPLAY EDILEBILIR KANIT")

# ⚠ REPLAY BELGESI HER PAKET ICIN ZORUNLU (`Y11B1-REPLAY-BELGESIZ-KABUL`).
BELGE = {P1.source_id: SAYFA, P2.source_id: SAYFA}
_a = fb.allowlist_kur([P1, P2], belgeler=BELGE)
kontrol("kanit REPLAY EDILEN paketler allowlist'e girer",
        _a["allowlist"] == {P1.fact_id, P2.fact_id}, f"{_a}")
kontrol("kabul edilende red yok", not _a["redler"], f"{_a['redler']}")

# ⚠ DENETIM KARSI ORNEKLERI: belgesiz/yanlis source_id FAIL-OPEN OLAMAZ.
_bsz = fb.allowlist_kur([P1, P2])
kontrol("belgeler VERILMEZSE allowlist BOS", not _bsz["allowlist"], f"{_bsz}")
kontrol("belgesiz red stabil kod FACT-KANIT-ALINAMADI",
        all(x["kod"] == fb.KOD_KANIT_ALINAMADI for x in _bsz["redler"]),
        f"{_bsz['redler']}")
_bos = fb.allowlist_kur([P1], belgeler={})
kontrol("belgeler BOS harita -> allowlist BOS", not _bos["allowlist"], f"{_bos}")
_yanlis = fb.allowlist_kur([P1], belgeler={"s_baska_kaynak": SAYFA})
kontrol("YANLIS source_id -> FACT-KANIT-ALINAMADI",
        not _yanlis["allowlist"]
        and _yanlis["redler"][0]["kod"] == fb.KOD_KANIT_ALINAMADI,
        f"{_yanlis}")
_hash_yanlis = fb.allowlist_kur(
    [P1], belgeler={P1.source_id: SAYFA + "\nEK SATIR BELGEYI DEGISTIRDI"})
kontrol("YANLIS hash -> FACT-KANIT-BAYAT",
        not _hash_yanlis["allowlist"]
        and _hash_yanlis["redler"][0]["kod"] == fb.KOD_KANIT_BAYAT,
        f"{_hash_yanlis}")
kontrol("SAHTE accepted + eksik belge KABUL URETMEZ",
        not fb.allowlist_kur([P1])["allowlist"])

_span = paket("x", "kisa")                      # alinti cok kisa/locator yok
_span.locator = ""
_r = fb.allowlist_kur([_span], belgeler={_span.source_id: SAYFA})
kontrol("locator yoksa RED", _span.fact_id not in _r["allowlist"], f"{_r}")
kontrol("locator redi stabil kod",
        any(x["kod"] == fb.KOD_KANIT_EKSIK for x in _r["redler"]), f"{_r}")

_hash = paket("In 2024, the National Police Agency recorded 76,941 cases of people",
              "In 2024, the National Police Agency recorded 76,941 cases of people")
_hash.document_hash = ""
_rh = fb.allowlist_kur([_hash], belgeler={_hash.source_id: SAYFA})
kontrol("document_hash yoksa RED", not _rh["allowlist"], f"{_rh}")

_bayat = paket("In 2024, the National Police Agency recorded 76,941 cases of people",
               "In 2024, the National Police Agency recorded 76,941 cases of people")
_bayat.document_hash = "0" * 16
_rb = fb.allowlist_kur([_bayat], belgeler={_bayat.source_id: SAYFA})
kontrol("belge degismisse (stale) RED", not _rb["allowlist"], f"{_rb}")
kontrol("stale redi stabil kod",
        any(x["kod"] == fb.KOD_KANIT_BAYAT for x in _rb["redler"]), f"{_rb}")

_replay = fb.allowlist_kur([P1], belgeler={P1.source_id: SAYFA})
kontrol("quote GERCEKTEN replay edilir", P1.fact_id in _replay["allowlist"],
        f"{_replay}")
_yok = fb.allowlist_kur(
    [P1], belgeler={P1.source_id: "tamamen baska bir belge metni burada"})
kontrol("quote replay edilemezse RED", not _yok["allowlist"], f"{_yok}")

_ref = paket("Of these, 39.4% were aged 75 or older",
             "Of these, 39.4% were aged 75 or older", stance="refute")
_rr = fb.allowlist_kur([_ref], belgeler={_ref.source_id: SAYFA})
kontrol("stance=refute allowlist'e GIRMEZ", not _rr["allowlist"], f"{_rr}")
kontrol("refute redi stabil kod",
        any(x["kod"] == fb.KOD_STANCE_DESTEK_DEGIL for x in _rr["redler"]))

_srcsuz = paket("In 2024, the National Police Agency recorded 76,941 cases of people",
                "In 2024, the National Police Agency recorded 76,941 cases of people")
_srcsuz.source_id, _srcsuz.url = "", ""
kontrol("source_id/canonical_url yoksa RED",
        not fb.allowlist_kur([_srcsuz], belgeler={"": SAYFA})["allowlist"])


# ⚠ DENETIM: alan YOKSA "accepted" VARSAYILMAZ.
_damgasiz = paket("In 2024 police recorded 76,941 cases",
                  "the National Police Agency recorded 76,941 cases of people",
                  durum="")
_rd0 = fb.allowlist_kur([_damgasiz], belgeler={_damgasiz.source_id: SAYFA})
kontrol("verification_status ALANI YOKSA RED", not _rd0["allowlist"], f"{_rd0}")
kontrol("damgasiz red stabil kod",
        any(x["kod"] == fb.KOD_STATUS_ACCEPTED_DEGIL for x in _rd0["redler"]),
        f"{_rd0}")
kontrol("verification_status=pending RED",
        not fb.allowlist_kur(
            [paket("In 2024, the National Police Agency recorded 76,941 cases of people",
                   "In 2024, the National Police Agency recorded 76,941 cases of people",
                   durum="pending")],
            belgeler={P1.source_id: SAYFA})["allowlist"])
# ⚠ URETICI damgayi GERCEKTEN basiyor mu?
_uretilen, _ = FP.havuz_kur(
    "konu", [URL], erisim_tarihi="2026-08-15",
    getirici=lambda u: {"ok": True, "url": u, "baslik": "NPA",
                        "yayin_tarihi": "", "metin": SAYFA, "hata": ""},
    cikarici=lambda u, m, k, **_: [
        {"onerme": "In 2024, the National Police Agency recorded 76,941 cases of people",
         "alinti": "In 2024, the National Police Agency recorded 76,941 cases of people",
         "kategori": "rakam", "stance": "support"}])
kontrol("uretici dogrulama GECEN paketi accepted DAMGALAR",
        bool(_uretilen) and _uretilen[0].verification_status == "accepted",
        f"{[getattr(x, 'verification_status', None) for x in _uretilen]}")
kontrol("uretici ciktisi allowlist'e GIRER",
        fb.allowlist_kur(_uretilen,
                         belgeler={_uretilen[0].source_id: SAYFA}
                         )["allowlist"] == {_uretilen[0].fact_id})


blok("Y-11b/3 — CELISKI VE BAGIMSIZLIK")

_c1 = paket("In 2024, the National Police Agency recorded 76,941 cases of people",
            "In 2024, the National Police Agency recorded 76,941 cases of people")
_c2 = paket("In 2024, the National Police Agency recorded 76,941 cases",
            "The National Police Agency recorded no such cases of people",
            url="https://ornek.example.com/a", stance="refute")
_rc = fb.allowlist_kur([_c1, _c2],
                       belgeler={_c1.source_id: SAYFA,
                                 _c2.source_id: SAYFA})
# ⚠ FAZ Y-11b-1 — SOZLESME BILINCLI DEGISTI (`Y11B1-REFUTE-NLI-YOK`).
# ESKI IDDIA: "support/refute conflict IKISINI DE dusurur". O celiski
# karari token/pattern kurallariyla veriliyordu ve her denetim turunda
# yeni bir kacak uretti. ⚠ Artik `refute` FAIL-CLOSED `unresolved`:
# allowlist'e GIRMEZ ve GECERLI SUPPORT'U ZEHIRLEYEMEZ.
kontrol("refute allowlist'e GIRMEZ",
        _c2.fact_id not in _rc["allowlist"], f"{_rc['allowlist']}")
kontrol("refute red kodu stabil",
        any(x["kod"] == fb.KOD_REFUTE_COZULMEDI for x in _rc["redler"]),
        f"{_rc['redler']}")
kontrol("GECERLI support ZEHIRLENMEZ",
        _c1.fact_id in _rc["allowlist"], f"{_rc['allowlist']}")

_d1 = paket("In 2024, the National Police Agency recorded 76,941 cases of people",
            "In 2024, the National Police Agency recorded 76,941 cases of people",
            url="https://news.example.com/a")
_d2 = paket("Of these, 39.4% were aged 75 or older",
            "Of these, 39.4% were aged 75 or older",
            url="https://www.news.example.com/b?utm_source=x")
kontrol("ayni registrable domain IKINCI BAGIMSIZ kaynak SAYILMAZ",
        fb.bagimsiz_alan_sayisi([_d1, _d2]) == 1,
        f"{fb.bagimsiz_alan_sayisi([_d1, _d2])}")

_bilesik = paket(
    "In 2024 Japan recorded 76,941 solitary deaths and 39.4% were aged 75+",
    "Of these, 39.4% were aged 75 or older")
_rs = fb.allowlist_kur([_bilesik],
                       belgeler={_bilesik.source_id: SAYFA})
kontrol("bilesik claim tek parca destekliyse SPLIT/RED",
        not _rs["allowlist"]
        and any(x["kod"] == fb.KOD_BILESIK_CLAIM for x in _rs["redler"]),
        f"{_rs}")


blok("Y-11b/4 — COZULEMEYEN GETIRME: FALLBACK YOK")

for ad, hata in (("403", "HTTP 403"), ("paywall", "paywall"),
                 ("js-only", "javascript gerekli"), ("truncated", "kirpik"),
                 ("cid-pdf", "pdf metni cikarilamadi (gomulu font)"),
                 ("timeout", "timeout"), ("butce", "para tavani")):
    _u = fb.getirme_sonucu_degerlendir({"ok": False, "hata": hata})
    kontrol(f"{ad} -> unresolved (fallback yok)",
            _u["durum"] == "unresolved" and _u["kod"] == fb.KOD_KANIT_ALINAMADI,
            f"{_u}")
kontrol("basarili getirme unresolved DEGIL",
        fb.getirme_sonucu_degerlendir({"ok": True, "metin": SAYFA})["durum"]
        == "cozuldu")


blok("Y-11b/5 — TUM SHOTLAR: %100 KAPSAM, PREFILLED RED")

_izin = _a["allowlist"]
# ⚠ Y-11b-2 SOZLESMESI (`Y11B2-FACT-ID-FALLBACK`): `primary_fact_id` VE
# `fact_id` ZORUNLU ve BIREBIR AYNI; `or` fallback'i KALDIRILDI.
_shotlar = [{"scene_id": f"s{i:03d}", "kaynak": k,
             "primary_fact_id": P1.fact_id, "fact_id": P1.fact_id}
            for i, k in enumerate(["footage", "fallback", "ai", "footage"], 1)]
_sr = fb.shot_fact_dogrula(_shotlar, allowlist=_izin)
kontrol("footage OLMAYAN shotlar da denetlenir",
        _sr["hedef"] == 4, f"{_sr}")
kontrol("tam kapsam PASS", _sr["kapsam"] == 1.0 and not _sr["kod"], f"{_sr}")
kontrol("ayni fact BIRDEN COK shotta kullanilabilir",
        _sr["benzersiz_fact"] == 1 and not _sr["kod"], f"{_sr}")

_16_17 = [dict(x) for x in _shotlar] + [{"scene_id": "s005",
                                         "kaynak": "footage",
                                         "primary_fact_id": "",
                                         "fact_id": ""}]
_s16 = fb.shot_fact_dogrula(_16_17, allowlist=_izin)
kontrol("4/5 kapsam -> RED", _s16["kod"] == fb.KOD_SHOT_FACT_YOK, f"{_s16}")
kontrol("kapsam 1.0 degil", _s16["kapsam"] < 1.0, f"{_s16}")

_unknown = [dict(x) for x in _shotlar]
_unknown[2]["primary_fact_id"] = "f0000000000000000"
_unknown[2]["fact_id"] = "f0000000000000000"
_su = fb.shot_fact_dogrula(_unknown, allowlist=_izin)
kontrol("allowlist disi (unknown) fact -> RED",
        _su["kod"] == fb.KOD_SHOT_FACT_ALLOWLIST_DISI, f"{_su}")

_prefilled = [{"scene_id": "s001", "kaynak": "footage",
               "primary_fact_id": "f001", "fact_id": "f001"}]
kontrol("PREFILLED ordinal fact_id enjeksiyonu -> RED",
        fb.shot_fact_dogrula(_prefilled, allowlist=_izin)["kod"]
        == fb.KOD_SHOT_FACT_ALLOWLIST_DISI)
kontrol("allowlist BOSSA hicbir shot gecemez",
        fb.shot_fact_dogrula(_shotlar, allowlist=set())["kod"]
        == fb.KOD_SHOT_FACT_ALLOWLIST_DISI)


blok("Y-11b/6 — GROUNDED MOD FAIL-CLOSED")

# ⚠ Y-11b-2 SOZLESMESI: kapi GERCEK all-shot raporu OLMADAN PASS VERMEZ
# (`Y11B2-SHOT-RAPORU-YOK`). Saglikli fixture kendi GERCEK raporunu verir.
_saglikli_shot = fb.shot_fact_dogrula(_shotlar, allowlist=_izin)
kontrol("saglikli fixture all-shot raporu TEMIZ",
        not _saglikli_shot["kod"]
        and _saglikli_shot["bagli"] == _saglikli_shot["hedef"] > 0,
        f"{_saglikli_shot}")
# ⚠ P0 (`Y11B2-STRICT-VARSAYILAN`): STRICT sozlesme ACIKCA secilen
# arastirma profilinde olculur; kapi kapsami (mod, edit_id) ciftidir.
_ok = fb.grounded_kapisi(mod="documentary", edit_id="belgesel-arastirmaci",
                         arastirma_calisti=True,
                         arastirma_hatasi="", allowlist=_izin,
                         cozulemeyen=0, bolum_kapsami={"c01": 2},
                         shot_raporu=_saglikli_shot)
kontrol("saglikli grounded is GECER", _ok["gecti"] is True, f"{_ok}")
kontrol("AYNI is shot raporu OLMADAN GECMEZ",
        fb.grounded_kapisi(mod="documentary", edit_id="belgesel-arastirmaci",
                           arastirma_calisti=True,
                           arastirma_hatasi="", allowlist=_izin,
                           cozulemeyen=0, bolum_kapsami={"c01": 2},
                           shot_raporu=None)["kod"]
        == fb.KOD_SHOT_RAPORU_YOK)

for ad, kw, kod in (
        ("arastirma kapali", {"arastirma_calisti": False},
         fb.KOD_GROUNDED_ARASTIRMA_YOK),
        ("arastirma hatasi", {"arastirma_hatasi": "HTTP 500"},
         fb.KOD_GROUNDED_ARASTIRMA_HATA),
        ("0 fact", {"allowlist": set()}, fb.KOD_GROUNDED_FACT_YOK),
        ("cozulemeyen kanit", {"cozulemeyen": 3},
         fb.KOD_GROUNDED_KANIT_COZULEMEDI),
        ("bolum kapsami yetersiz", {"bolum_kapsami": {"c01": 0}},
         fb.KOD_GROUNDED_BOLUM_KAPSAMI)):
    _arg = {"mod": "documentary", "edit_id": "belgesel-arastirmaci",
            "arastirma_calisti": True,
            "arastirma_hatasi": "", "allowlist": _izin,
            "cozulemeyen": 0, "bolum_kapsami": {"c01": 2}}
    _arg.update(kw)
    _g = fb.grounded_kapisi(**_arg)
    kontrol(f"{ad} -> FAIL-CLOSED", _g["gecti"] is False, f"{_g}")
    kontrol(f"{ad} -> {kod}", _g["kod"] == kod, f"kod={_g.get('kod')!r}")

# ⚠ Grounded OLMAYAN yaratici modlar BOZULMAZ.
for _mod in ("animasyon", "hikaye"):
    _gm = fb.grounded_kapisi(mod=_mod, arastirma_calisti=False,
                             arastirma_hatasi="", allowlist=set(),
                             cozulemeyen=5, bolum_kapsami={})
    kontrol(f"grounded OLMAYAN mod ({_mod}) etkilenmez",
            _gm["gecti"] is True and _gm.get("kapsam_disi") is True, f"{_gm}")


blok("Y-11b/7 — ENTAILMENT: EXTRACTIVE SOZLESME (paraphrase YOK)")

# ⚠ SOZLESME DEGISIKLIGI (`Y11B2-HEURISTIK-SONSUZ`, kirmizi takim final
# denetimi): entailment kapisi SEZGISEL bir kural yigini idi (ortusme
# esigi, yeni sayi/yil/birim/ozel ad kirliligi, polarite/baglam
# cozumlemesi). Kirmizi takim her turda YENI bir kacak buldu; sezgisel
# enumerasyon SONSUZ oldugu icin kapi Y-11b-1'in EXACT-SUPPORT
# sozlesmesiyle TUTARLI en dar bicime cekildi:
#   konusulan metin, KANONIK onerme ile NORMALIZE EDILMIS BIREBIR AYNI
#   olmadan tahsis YOK -> TEK stabil kod `FACT-ENTAIL-EXTRACTIVE-DEGIL`.
# Bu YUZDEN eski "paraphrase GECER" beklentisi ARTIK GECERLI DEGILDIR:
# paraphrase da, yeni deger de, ilgisiz metin de AYNI kodla RED alir.
# ⚠ SERBEST PARAPHRASE/NLI bu atomda DESTEKLENMIYOR (kapsam siniri).
kontrol("KANONIK onerme BIREBIR GECER",
        fb.entail_dogrula(P1.onerme, P1)["gecti"] is True,
        f"{fb.entail_dogrula(P1.onerme, P1)}")
kontrol("yalniz BOSLUK/CASE farki GECER",
        fb.entail_dogrula("  " + P1.onerme.upper() + " ", P1)["gecti"] is True)
_KARSI7 = (
    ("PARAPHRASE (eski sozlesmede GECIYORDU)",
     "2024'te 76,941 vaka kaydedildi"),
    ("allowlist disi SAYI", "2024'te 76,941 vaka; artis %212 oldu"),
    ("allowlist disi TARIH", "1998'de 76,941 vaka kaydedildi"),
    ("fact'le ILGISIZ metin", "Sonuc olarak tablo degisti"),
    ("allowlist disi YER/ENTITY", "2024'te Osaka'da 76,941 vaka kaydedildi"),
    ("allowlist disi BIRIM",
     "National Police Agency 76,941 vaka; 12 milyar TL kayip"),
)
for _ad7, _t7 in _KARSI7:
    _d7 = fb.entail_dogrula(_t7, P1)
    kontrol(f"RED: {_ad7}", _d7["gecti"] is False, f"{_d7}")
    kontrol(f"{_ad7}: TEK stabil kod",
            _d7["kod"] == fb.KOD_ENTAIL_EXTRACTIVE_DEGIL, f"{_d7}")
kontrol("sezgisel kodlar KALDIRILDI (olu karmasiklik yok)",
        not hasattr(fb, "KOD_ENTAIL_YENI_DEGER")
        and not hasattr(fb, "KOD_ENTAIL_POLARITE")
        and not hasattr(fb, "polarite"),
        "sezgisel otorite hala tanimli")
kontrol("sessiz ALIAS eklenmedi (uretim tuketicisi yok)",
        "KOD_ENTAIL_YENI_DEGER" not in
        open(os.path.join(KOK, "fact_baglama.py"), encoding="utf-8").read())


blok("Y-11b/8 — DETERMINIZM: SIRA DEGISSE KIMLIK/SNAPSHOT AYNI")

_s1 = fb.allowlist_kur([P1, P2], belgeler=BELGE)
_s2 = fb.allowlist_kur([P2, P1], belgeler=BELGE)
kontrol("allowlist sira bagimsiz", _s1["allowlist"] == _s2["allowlist"])
kontrol("snapshot sira bagimsiz ve DETERMINISTIK",
        _s1["snapshot"] == _s2["snapshot"], f"{_s1['snapshot']} / {_s2['snapshot']}")
kontrol("content-addressed kimlik sira bagimsiz",
        P1.fact_id == FP.fact_id_uret(P1.onerme, P1.exact_quote, P1.source_id))


blok("Y-11b/9 — ARASTIRMA TARAFI: GENEL ATIF FALLBACK KALDIRILDI")

_RS = open(os.path.join(KOK, "arastirma", "researcher.py"),
           encoding="utf-8").read()
kontrol("researcher genel atif fallback'i KALDIRILDI",
        "Y11B-GENEL-ATIF-FALLBACK" in _RS
        and "sonuc.get(\"atiflar\")" not in _RS.split(
            "def arastir(")[1].split("if imza in gorulen_iddia")[0],
        "genel ilk-2 atif hala iddiaya yapistiriliyor")
kontrol("kaynaksiz iddia GORUNUR kilinir",
        "KAYNAKSIZ-IDDIA" in _RS, "sessiz dusus")

# ⚠ HAT ENTEGRASYONU (fact_bagla Jaccard kaldirimi, grounded kapisi,
# tum-shot denetimi, kapi-render sirasi) FAZ Y-11b-2'nin sozlesmesidir ve
# `test_faz_y11b2.py` icinde kilitlenir. Burada TEKRAR EDILMEZ.


print(f"\n{'=' * 62}\nGECEN: {gecen}   BASARISIZ: {len(basarisiz)}")
for b in basarisiz:
    print(f"  XX {b}")
sys.exit(1 if basarisiz else 0)
