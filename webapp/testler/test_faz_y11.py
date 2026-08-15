#!/usr/bin/env python3
"""FAZ Y-11 — CLAIM-FIRST HAT KAYNAK-TEMELLI (EVIDENCE-FIRST) OLDU.

⚠ OLCULEN KUSUR (`Y11-IDDIA-ONCE-KAYNAK-SONRA`) — gercek is
job_1786792477656_y71414_df7e2a:
    ARASTIRMA: 1/11 olgu dogrulandi, 9 kaynak
    ...
    TESLIM: False | KABUL-YOK:Y1-KURGU-QA-FAIL:FACT-BAGLANTI-YOK

⚠ KOK NEDEN (bagimsiz denetim, 15 Agu 2026):
  1. `researcher.soru_arastir` MODELE once IDDIA yazdiriyor, atifi model
     kendi veriyor; iddia MODELIN cumlesi, sayfanin degil.
  2. Model atif vermezse `researcher.arastir` aramanin GENEL ilk 2 atfini
     iddiaya takiyor (`researcher.py:317-321`) — iddia ile o sayfanin
     ilgisi OLCULMEMISTIR.
  3. `Kaynak.alinti` (sayfadan alinan cumle) SAKLANIYOR ama
     `fact_checker.kaynak_dogrula` onu HIC KULLANMIYOR; dogrulama
     sayfayi bastan tarayan sayi/kelime eslesmesine ya da LLM hukmune
     dusuyor.
  4. `arastirma_kopru.fact_bagla` sahneyi olguya 0.16 Jaccard BENZERLIGI
     ile bagliyor — fact_id TAHMIN EDILIYOR.
  5. Sahnede onceden yazili `fact_id` varsa DOGRULANMADAN kabul ediliyor
     (`arastirma_kopru.py:250-253`).

── SOZLESME (FactPacket) ──
  · Akis TERSINE: kanit span -> kabul edilmis FactPacket -> bolum plani
    -> FactBeat -> anlatim/cekim. Once iddia yazip sonra kaynak ARANMAZ.
  · Her FactPacket: content-addressed `fact_id` + ATOMIK onerme +
    `exact_quote` + `locator` + `document_hash` + kanonik `source_id` +
    `source_class` + `stance`.
  · `exact_quote` INDIRILEN BELGEDE BIREBIR GECMEK ZORUNDA; gecmiyorsa
    paket REDDEDILIR (uydurma yok).
  · Bilesik iddia ATOMIK onermelere BOLUNUR.
  · HAM KAYNAK SAYISI KABUL GEREKCESI DEGILDIR; kabul yalnizca
    dogrulanmis paket sayisiyla olculur.
  · Ayni onermeye destek/red (support/refute) celiskisi varsa IKISI DE
    kabul edilmez.
  · Bilinmeyen / onceden doldurulmus fact_id REDDEDILIR.

Kosum: .venv-test/bin/python3 webapp/testler/test_faz_y11.py
"""
from __future__ import annotations

import os
import re
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


def oku(*p):
    with open(os.path.join(KOK, *p), encoding="utf-8") as f:
        return f.read()


# ═══════════════════ SAHTE (AGSIZ) GIRDILER ═══════════════════
# ⚠ Ag yok, ucretli API yok, medya yok. Sayfa metni ve LLM cikti
# sabit; testler saat ve ag bagimsiz kosar.

SAYFA_A = (
    "Japan Ministry of Health report\n\n"
    "In 2024, the National Police Agency recorded 76,941 cases of people "
    "who died alone at home.\n"
    "Of these, 39.4% were aged 75 or older.\n"
    "The ministry published the figure on 2025-04-12.\n"
)
SAYFA_B = (
    "Reuters\n\n"
    "Japanese police reported 76,941 solitary deaths in 2024, "
    "the first official national count.\n"
)
SAYFA_C = (
    "Daily blog\n\n"
    "Some say the number of solitary deaths in Japan was 21,000 in 2024, "
    "which contradicts the police figure.\n"
)

URL_A = "https://www.npa.go.jp/english/report-2024.html?utm_source=x"
URL_B = "https://www.reuters.com/world/japan-solitary-deaths-2024/"
URL_C = "https://ornek-blog.example.com/post/1"


def sahte_getirici(esleme):
    """url -> sayfa_getir() bicimli sozluk."""
    def _fn(url):
        m = esleme.get(url)
        if m is None:
            return {"ok": False, "url": url, "durum": 404, "baslik": "",
                    "yayin_tarihi": "", "metin": "", "hata": "HTTP 404"}
        return {"ok": True, "url": url, "durum": 200, "baslik": m["baslik"],
                "yayin_tarihi": m.get("tarih", ""), "metin": m["metin"],
                "hata": ""}
    return _fn


def sahte_cikarici(harita):
    """url -> [{"onerme","alinti","kategori","stance"}] dondurur.

    ⚠ LLM'in yerine gecer: PARA HARCANMAZ, cikti sabittir.
    """
    def _fn(url, metin, konu, **_k):
        return list(harita.get(url) or [])
    return _fn


# ═══════════════════ Y-11/1 — MODUL VE SOZLESME ═══════════════════

blok("Y-11/1 — FactPacket sozlesmesi var")

fp = None
try:
    from arastirma import factpacket as fp
    kontrol("modul yuklendi: arastirma/factpacket.py", True)
except Exception as e:
    kontrol("modul yuklendi: arastirma/factpacket.py", False,
            f"{type(e).__name__}: {e}")

if fp is not None:
    for ad in ("FactPacket", "fact_id_uret", "source_id_uret", "belge_ozeti",
               "alinti_dogrula", "onerme_bol", "havuz_kur", "paket_dogrula",
               "RED_KODLARI"):
        kontrol(f"disa acilan ad: {ad}", hasattr(fp, ad), "tanimli degil")

    kontrol("stabil kod belgelendi: Y11-IDDIA-ONCE-KAYNAK-SONRA",
            "Y11-IDDIA-ONCE-KAYNAK-SONRA" in oku("arastirma", "factpacket.py"),
            "karar kodda belgelenmemis")

# Buradan sonrasi modul olmadan anlamsiz.
if fp is None:
    print(f"\n{'=' * 62}\nGECEN: {gecen}   BASARISIZ: {len(basarisiz)}")
    for b in basarisiz:
        print(f"  XX {b}")
    sys.exit(1)


blok("Y-11/2 — fact_id CONTENT-ADDRESSED, tahmin edilemez")

_id1 = fp.fact_id_uret("Japan recorded 76,941 solitary deaths in 2024",
                       "recorded 76,941 cases", "s_npa")
_id2 = fp.fact_id_uret("Japan recorded 76,941 solitary deaths in 2024",
                       "recorded 76,941 cases", "s_npa")
_id3 = fp.fact_id_uret("Japan recorded 76,941 solitary deaths in 2024",
                       "different quote entirely", "s_npa")
kontrol("ayni icerik -> ayni fact_id", _id1 == _id2, f"{_id1} != {_id2}")
kontrol("farkli alinti -> farkli fact_id", _id1 != _id3, "id ceakismasi")
kontrol("fact_id bicimi f + 16 hex",
        re.fullmatch(r"f[0-9a-f]{16}", _id1) is not None, f"bicim: {_id1}")
# ⚠ DAVRANIS testi (metin araması DEGIL): manifest gercekten kabul ediyor mu?
from arastirma.manifests import Iddia, Kaynak, ManifestHatasi


def _iddia(fid):
    return Iddia(fact_id=fid, metin="x", guven="dogrulandi",
                 kaynaklar=[Kaynak(url="https://a.example.com/p", baslik="b",
                                   tur="haber-buyuk", erisim_tarihi="2026-08-15")])


def _gecerli_mi(fid):
    try:
        _iddia(fid).dogrula()
        return True
    except ManifestHatasi:
        return False


kontrol("manifest content-addressed fact_id'yi KABUL eder", _gecerli_mi(_id1),
        f"{_id1} reddedildi")
kontrol("manifest eski sirali f001 bicimini KORUR", _gecerli_mi("f001"),
        "geriye uyum kirildi")
kontrol("manifest bozuk fact_id'yi REDDEDER",
        not _gecerli_mi("fZZZ") and not _gecerli_mi("f01")
        and not _gecerli_mi("fabc") and not _gecerli_mi("f0123456789abcde"),
        "gecersiz bicim kabul edildi")


blok("Y-11/3 — source_id KANONIK (izleme parametresi id'yi degistirmez)")

_s1 = fp.source_id_uret("https://www.npa.go.jp/english/report-2024.html?utm_source=x")
_s2 = fp.source_id_uret("http://npa.go.jp/english/report-2024.html/")
_s3 = fp.source_id_uret("https://www.reuters.com/world/japan-solitary-deaths-2024/")
kontrol("utm/www/sema/slash farki ayni source_id verir", _s1 == _s2,
        f"{_s1} != {_s2}")
kontrol("farkli belge farkli source_id", _s1 != _s3, "source_id cakismasi")


blok("Y-11/4 — ALINTI BELGEDE BIREBIR GECMELI (quote/page mismatch)")

kontrol("bosluk/buyuk-kucuk farki alintiyi bozmaz",
        fp.alinti_dogrula("recorded   76,941 CASES of people", SAYFA_A) is True,
        "normalize edilmis birebir alinti reddedildi")
kontrol("uydurma alinti REDDEDILIR",
        fp.alinti_dogrula("recorded 21,000 cases of people", SAYFA_A) is False,
        "sayfada gecmeyen alinti kabul edildi")
kontrol("cok kisa alinti kanit sayilmaz",
        fp.alinti_dogrula("In 2024", SAYFA_A) is False,
        "asgari uzunluk kapisi yok")


blok("Y-11/5 — BELGE HASH BAYATLIGI olculur")

_h_a = fp.belge_ozeti(SAYFA_A)
_h_b = fp.belge_ozeti(SAYFA_B)
kontrol("ayni belge -> ayni ozet", _h_a == fp.belge_ozeti(SAYFA_A), "hash kararsiz")
kontrol("farkli belge -> farkli ozet", _h_a != _h_b, "hash cakismasi")

_p_bayat = fp.FactPacket(
    fact_id=fp.fact_id_uret("x", "recorded 76,941 cases", "s"),
    onerme="Japan recorded 76,941 solitary deaths in 2024",
    exact_quote="recorded 76,941 cases",
    locator="p1", document_hash=_h_b,        # ⚠ YANLIS belgenin hash'i
    source_id="s", source_class="resmi-kurum", stance="support",
    url=URL_A, alan="npa.go.jp", erisim_tarihi="2026-08-15")
_r = fp.paket_dogrula(_p_bayat, SAYFA_A)
kontrol("bayat document_hash REDDEDILIR",
        (not _r["kabul"]) and _r["kod"] == "Y11-BELGE-HASH-BAYAT",
        f"sonuc: {_r}")


blok("Y-11/6 — BILESIK IDDIA ATOMIK ONERMELERE BOLUNUR")

_bol = fp.onerme_bol(
    "In 2024 Japan recorded 76,941 solitary deaths and 39.4% were aged 75 or older")
kontrol("bilesik iddia >=2 atomik onermeye bolunur", len(_bol) >= 2,
        f"bolunmedi: {_bol}")
kontrol("atomik iddia bolunmez",
        len(fp.onerme_bol("Japan recorded 76,941 solitary deaths in 2024")) == 1,
        "atomik onerme gereksiz bolundu")


blok("Y-11/7 — HAVUZ: kanit span -> kabul (uydurma DUSER)")

_getir = sahte_getirici({
    URL_A: {"baslik": "NPA report 2024", "metin": SAYFA_A, "tarih": "2025-04-12"},
    URL_B: {"baslik": "Reuters", "metin": SAYFA_B},
})
_cikar = sahte_cikarici({
    URL_A: [
        # 1) gercek kanit
        {"onerme": "In 2024 the National Police Agency recorded 76,941 cases "
                   "of people who died alone at home",
         "alinti": "the National Police Agency recorded 76,941 cases of people "
                   "who died alone at home",
         "kategori": "rakam", "stance": "support"},
        # 2) gercek kanit
        {"onerme": "39.4% of those cases were aged 75 or older",
         "alinti": "Of these, 39.4% were aged 75 or older",
         "kategori": "rakam", "stance": "support"},
        # 3) UYDURMA — sayfada gecmiyor
        {"onerme": "The figure rose 12% from the previous year",
         "alinti": "the figure rose 12% from the previous year",
         "kategori": "rakam", "stance": "support"},
    ],
    URL_B: [
        {"onerme": "Japanese police reported 76,941 solitary deaths in 2024",
         "alinti": "Japanese police reported 76,941 solitary deaths in 2024",
         "kategori": "rakam", "stance": "support"},
    ],
})

_havuz, _rapor = fp.havuz_kur(
    "solitary deaths in Japan", [URL_A, URL_B],
    erisim_tarihi="2026-08-15", getirici=_getir, cikarici=_cikar)

kontrol("uydurma alintili paket havuza GIRMEDI", len(_havuz) == 3,
        f"kabul={len(_havuz)} (beklenen 3), rapor={_rapor}")
kontrol("red gerekcesi kayitli",
        any(r.get("kod") == "Y11-ALINTI-SAYFADA-YOK"
            for r in (_rapor.get("redler") or [])),
        f"redler: {_rapor.get('redler')}")
kontrol("her paketin exact_quote'u dolu",
        all(p.exact_quote for p in _havuz), "kanitsiz paket var")
kontrol("her paketin source_id'si dolu",
        all(p.source_id for p in _havuz), "source_id eksik")
kontrol("her paketin document_hash'i dolu",
        all(p.document_hash for p in _havuz), "document_hash eksik")
kontrol("her paketin source_class'i taninir",
        all(p.source_class for p in _havuz), "source_class eksik")
kontrol("fact_id'ler benzersiz",
        len({p.fact_id for p in _havuz}) == len(_havuz), "fact_id tekrar ediyor")


blok("Y-11/8 — HAM KAYNAK SAYISI KABUL GEREKCESI DEGILDIR")

_cikar_bos = sahte_cikarici({
    URL_A: [{"onerme": "Japan recorded 21,000 solitary deaths in 2024",
             "alinti": "Japan recorded 21,000 solitary deaths in 2024",
             "kategori": "rakam", "stance": "support"}],
    URL_B: [{"onerme": "Police reported 21,000 solitary deaths",
             "alinti": "Police reported 21,000 solitary deaths",
             "kategori": "rakam", "stance": "support"}],
})
_h2, _r2 = fp.havuz_kur("konu", [URL_A, URL_B], erisim_tarihi="2026-08-15",
                        getirici=_getir, cikarici=_cikar_bos)
kontrol("uydurma alintilar havuzu BOS birakir", len(_h2) == 0,
        f"kabul={len(_h2)}")
kontrol("rapor ham kaynak sayisini AYRI tutar",
        int(_r2.get("ham_kaynak") or 0) == 2 and int(_r2.get("kabul") or 0) == 0,
        f"rapor: {_r2}")
kontrol("yeterlilik ham kaynaga DEGIL kabul edilen pakete bakar",
        fp.havuz_yeterli_mi(_h2, gereken=1)["yeterli"] is False,
        "bos havuz yeterli sayildi")


blok("Y-11/9 — DESTEK/RED CELISKISI IKI PAKETI DE DUSURUR")

_getir3 = sahte_getirici({
    URL_A: {"baslik": "NPA report 2024", "metin": SAYFA_A},
    URL_C: {"baslik": "Daily blog", "metin": SAYFA_C},
})
_cikar3 = sahte_cikarici({
    URL_A: [{"onerme": "Japan recorded 76,941 solitary deaths in 2024",
             "alinti": "recorded 76,941 cases of people who died alone at home",
             "kategori": "rakam", "stance": "support"}],
    URL_C: [{"onerme": "Japan recorded 76,941 solitary deaths in 2024",
             "alinti": "the number of solitary deaths in Japan was 21,000 in 2024",
             "kategori": "rakam", "stance": "refute"}],
})
_h3, _r3 = fp.havuz_kur("konu", [URL_A, URL_C], erisim_tarihi="2026-08-15",
                        getirici=_getir3, cikarici=_cikar3)
kontrol("celiskili onerme HICBIR pakette kabul edilmez", len(_h3) == 0,
        f"kabul={len(_h3)}: {[p.onerme for p in _h3]}")
kontrol("celiski red kodu yazilir",
        any(r.get("kod") == "Y11-DESTEK-CELISKI"
            for r in (_r3.get("redler") or [])),
        f"redler: {_r3.get('redler')}")


blok("Y-11/10 — BILINMEYEN / ONCEDEN DOLDURULMUS fact_id REDDEDILIR")

_izin = fp.allowlist(_havuz)
kontrol("allowlist yalnizca kabul edilen fact_id'leri icerir",
        _izin == {p.fact_id for p in _havuz}, "allowlist havuzla ortusmuyor")
kontrol("bilinmeyen fact_id allowlist'te degil",
        "f0123456789abcdef" not in _izin, "uydurma id kabul edildi")
kontrol("onceden doldurulmus ordinal id (f001) kabul edilmez",
        "f001" not in _izin, "prefilled id kabul edildi")


blok("Y-11/11 — ERISILEMEYEN BELGE SESSIZ GECMEZ")

_h4, _r4 = fp.havuz_kur("konu", [URL_A, "https://yok.example.com/a"],
                        erisim_tarihi="2026-08-15", getirici=_getir,
                        cikarici=_cikar)
kontrol("erisilemeyen belge red olarak kayitli",
        any(r.get("kod") == "Y11-BELGE-ALINAMADI"
            for r in (_r4.get("redler") or [])),
        f"redler: {_r4.get('redler')}")


print(f"\n{'=' * 62}\nGECEN: {gecen}   BASARISIZ: {len(basarisiz)}")
for b in basarisiz:
    print(f"  XX {b}")
sys.exit(1 if basarisiz else 0)
