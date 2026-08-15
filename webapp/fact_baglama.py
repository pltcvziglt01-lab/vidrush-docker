"""FACT BAGLAMA URETIM SOZLESMESI. FAZ Y-11b.

    accepted FactPacket -> SectionPlan -> FactBeat -> narration/shot

⚠ KODDAN DOGRULANAN KUSURLAR (bu modulun kapattiklari):

  1. `Y11B-SIMILARITY-TAHMINI` — `arastirma_kopru.fact_bagla` sahneyi
     olguya 0.16 JACCARD ORTUSMESIYLE bagliyordu (`FACT_ESIK = 0.16`;
     kendi yorumu: "Deger sezgisel; ... uydurma degil ama OLCULMEDI").
     fact_id URETIM ANINDA verilmiyor, SONRADAN METIN BENZERLIGIYLE
     TAHMIN EDILIYORDU. Kimlik SIMILARITY ILE BULUNMAZ.
  2. `Y11B-PREFILLED-KABUL` — `arastirma_kopru.py:249-253`: sahnede
     onceden yazili bir `fact_id` varsa DOGRULANMADAN "baglandi" sayilip
     kapsama ekleniyordu; enjekte edilmis herhangi bir dizge geciyordu.
  3. `Y11B-GENEL-ATIF-FALLBACK` — `researcher.py:317-321`: model bir
     iddiaya atif vermezse ARAMANIN GENEL ilk 2 atfi o iddiaya
     YAPISTIRILIYORDU; iddia ile o sayfanin ilgisi OLCULMEMISTIR.
  4. `Y11B-SADECE-FOOTAGE` — `fact_bagla(yalnizca_footage=True)` ve
     `qa_on.py:298` (`if c.kaynak_turu != "medya": continue`): fact
     denetimi yalnizca footage/medya cekimlerine bakiyordu; fallback ve
     AI sahneler fact zorunlulugundan MUAFTI.
  5. `Y11B-GROUNDED-FAIL-OPEN` — pipeline olgu kapisi `if _olgular:`
     blogunun ICINDEYDI: arastirma KAPALI, HATALI ya da 0 olgu ise kapi
     HIC KOSMUYOR, is kullanici metniyle SESSIZCE devam ediyordu.

── SOZLESME ──
  · Allowlist'e YALNIZCA `verification_status=accepted` VE kaniti REPLAY
    EDILEBILIR paket girer: `exact_quote` + `locator` + `document_hash` +
    `source_id`/canonical URL + `stance=SUPPORT`.
  · missing / unknown / stale / conflict -> RED (stabil kod).
  · Ayni REGISTRABLE DOMAIN ikinci bagimsiz kaynak SAYILMAZ.
  · Bilesik claim tek parca destekleniyorsa SPLIT/RED.
  · Getirme cozulemezse (403/paywall/JS/kirpik/CID-PDF/timeout/butce)
    durum `unresolved`; FALLBACK YOK.
  · Her render edilen shot — footage OLSUN OLMASIN — allowlist'ten tam
    bir `primary_fact_id` tasir. Ayni fact BIRDEN COK shotta kullanilabilir.
  · Grounded belgesel modunda arastirma yok/hata/0 fact/cozulemeyen
    kanit/yetersiz bolum kapsami -> FAIL-CLOSED, sessiz devam YOK.
    ⚠ Grounded OLMAYAN yaratici modlar KAPSAM DISIDIR (davranis degismez).
  · Narration/shot, primary fact'i ENTAIL etmeli: allowlist disi
    sayi/tarih EKLENEMEZ.

⚠ Bu modul SAF: ag/dosya/render YOK, rastgelelik YOK, sira bagimsizdir.
"""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import types

# ── Grounded (kaynak-temelli) modlar. Digerleri KAPSAM DISI. ──
GROUNDED_MODLAR = ("documentary",)

# Bir chapter'in tasimasi gereken en az KABUL EDILMIS fact sayisi.
BOLUM_ASGARI_FACT = 1

KOD_KANIT_EKSIK = "FACT-KANIT-EKSIK"
KOD_KANIT_BAYAT = "FACT-KANIT-BAYAT"
KOD_KANIT_ALINAMADI = "FACT-KANIT-ALINAMADI"
KOD_STANCE_DESTEK_DEGIL = "FACT-STANCE-DESTEK-DEGIL"
KOD_CELISKI = "FACT-DESTEK-CELISKI"
KOD_BILESIK_CLAIM = "FACT-BILESIK-CLAIM"
KOD_SHOT_FACT_YOK = "SHOT-FACT-YOK"
KOD_SHOT_FACT_ALLOWLIST_DISI = "SHOT-FACT-ALLOWLIST-DISI"
KOD_GROUNDED_ARASTIRMA_YOK = "GROUNDED-ARASTIRMA-YOK"
KOD_GROUNDED_ARASTIRMA_HATA = "GROUNDED-ARASTIRMA-HATA"
KOD_GROUNDED_FACT_YOK = "GROUNDED-FACT-YOK"
KOD_GROUNDED_KANIT_COZULEMEDI = "GROUNDED-KANIT-COZULEMEDI"
KOD_GROUNDED_BOLUM_KAPSAMI = "GROUNDED-BOLUM-KAPSAMI-YETERSIZ"
KOD_ENTAIL_YENI_DEGER = "FACT-ENTAIL-YENI-DEGER"
KOD_ENTAIL_ILGISIZ = "FACT-ENTAIL-ILGISIZ"
KOD_STATUS_ACCEPTED_DEGIL = "FACT-STATUS-ACCEPTED-DEGIL"
# ⚠ OLCULEN KUSUR (`Y11B1-ONERME-QUOTE-UYUMSUZ`, denetim): belge ve quote
# "recorded 76,941 cases" derken ONERME "recorded 999,999 cases" diyebiliyordu.
# `paket_dogrula` YALNIZCA quote'un belgede gectigini kontrol ediyordu; onermenin
# quote TARAFINDAN DESTEKLENDIGINI HIC olcmuyordu. Y-11b-1'in tum kabul varsayimi
# (kanit-once) bu acikta cokerdi: uydurma bir rakam gercek bir alintiya
# yaslanarak allowlist'e girerdi.
KOD_ONERME_QUOTE_UYUMSUZ = "FACT-ONERME-QUOTE-UYUMSUZ"
KOD_REFUTE_COZULMEDI = "FACT-REFUTE-COZULMEDI"
# ⚠ `Y11B1-KIMLIK-YENIDEN-TURETIM`: tuketici replay'i URETICI ile BIREBIR
# ayni olmali; `fact_id` GUNCEL icerikten yeniden turetilmezse ESKI kimlik
# altinda MUTASYONA UGRAMIS claim gecebilir.
KOD_KIMLIK_UYUMSUZ = "FACT-KIMLIK-ICERIKTEN-TUREMIYOR"
# ⚠ `Y11B1-SPAN-CEVRE-BAGLAMI`: quote BIREBIR gecse bile CEVRESI onu
# curutuyor olabilir ("It is false that ...", "VERDICT: FALSE", "myth",
# "debunked", "retracted", "disputed").
KOD_CEVRE_CURUTUYOR = "FACT-SPAN-CEVRESI-CURUTUYOR"
# ⚠ `Y11B1-SPAN-IDDIA-DEGIL`: span'in KENDISI iddia olmayabilir — soru
# cumlesi ("Did the agency record ...?") TAM ESITLIK sozlesmesini gecer
# ama HICBIR SEY ONERMEZ.
KOD_SPAN_IDDIA_DEGIL = "FACT-SPAN-IDDIA-DEGIL"

KODLAR = (KOD_KANIT_EKSIK, KOD_KANIT_BAYAT, KOD_KANIT_ALINAMADI,
          KOD_STANCE_DESTEK_DEGIL, KOD_CELISKI, KOD_BILESIK_CLAIM,
          KOD_SHOT_FACT_YOK, KOD_SHOT_FACT_ALLOWLIST_DISI,
          KOD_GROUNDED_ARASTIRMA_YOK, KOD_GROUNDED_ARASTIRMA_HATA,
          KOD_GROUNDED_FACT_YOK, KOD_GROUNDED_KANIT_COZULEMEDI,
          KOD_GROUNDED_BOLUM_KAPSAMI, KOD_ENTAIL_YENI_DEGER,
          KOD_ENTAIL_ILGISIZ, KOD_STATUS_ACCEPTED_DEGIL,
          KOD_ONERME_QUOTE_UYUMSUZ, KOD_REFUTE_COZULMEDI,
          KOD_KIMLIK_UYUMSUZ, KOD_CEVRE_CURUTUYOR, KOD_SPAN_IDDIA_DEGIL)

# ⚠ Cozulemeyen getirme imzalari — hicbiri FALLBACK uretmez.
_COZULEMEYEN = ("403", "401", "paywall", "subscribe", "javascript", "js",
                "kirpik", "truncat", "gomulu font", "timeout", "zaman asimi",
                "para tavani", "butce", "http 5", "sayfa alinamadi",
                "metin degil", "cikarilamadi")

_SAYI = re.compile(r"\d[\d.,]*")
_YIL = re.compile(r"\b(1[6-9]\d{2}|20\d{2})\b")
_BAGLAC = re.compile(r"\s+and\s+|\s*;\s+|\s+ve\s+", re.I)


def _norm_sayi(metin: str) -> set:
    """"76,941" ve "76941" AYNI sayidir."""
    out = set()
    for m in _SAYI.finditer(str(metin or "")):
        sade = m.group(0).rstrip(".,").replace(",", "").replace(".", "")
        if sade.isdigit():
            out.add(sade.lstrip("0") or "0")
    return out


def registrable_alan(url: str) -> str:
    """Kayit edilebilir alan (eTLD+1 yaklasimi). ⚠ `www.` ve alt alanlar
    AYNI kaynaktir — sendikasyon bagimsiz dogrulama DEGILDIR."""
    m = re.match(r"(?:https?://)?([^/?#]+)", str(url or "").strip(), re.I)
    if not m:
        return ""
    ana = m.group(1).lower().split(":")[0]
    parcalar = [p for p in ana.split(".") if p]
    if len(parcalar) < 2:
        return ana
    # co.uk / go.jp / com.tr gibi iki kademeli sonekler
    if len(parcalar) >= 3 and parcalar[-2] in ("co", "com", "org", "net",
                                               "gov", "ac", "go"):
        return ".".join(parcalar[-3:])
    return ".".join(parcalar[-2:])


def bagimsiz_alan_sayisi(paketler) -> int:
    """Kac BAGIMSIZ kaynak? ⚠ Ayni registrable domain TEK sayilir."""
    return len({registrable_alan(getattr(p, "url", "") or "")
                for p in (paketler or [])} - {""})


def bilesik_claim_mi(onerme: str, exact_quote: str) -> bool:
    """Bilesik claim TEK bir kanit span'iyla desteklenemez.

    ⚠ Iki tarafi da SAYI iceren bir baglac varsa ve alinti taraflardan
    yalnizca birini kapsiyorsa claim BOLUNMELIDIR.
    """
    parcalar = [p.strip() for p in _BAGLAC.split(str(onerme or "")) if p.strip()]
    if len(parcalar) < 2:
        return False
    sayili = [p for p in parcalar if _norm_sayi(p)]
    if len(sayili) < 2:
        return False
    q = _norm_sayi(exact_quote)
    kapsanan = sum(1 for p in sayili if _norm_sayi(p) <= q)
    return kapsanan < len(sayili)


# ⚠ `Y11B1-UYUM-IMPORT-FAIL-OPEN`: onerme<->quote uyum OLCUMU ARTIK
# `arastirma.factpacket` icinde yasar (capraz import + `except ImportError:
# pass` fail-open'i kaldirildi).
# ⚠ KATMANLI STABIL KOD SOZLESMESI (`Y11B1-KATMAN-KOD-SOZLESMESI`): her
# katman KENDI belgelenmis kodunu tutar; kod adlari katmanlar arasinda
# SESSIZCE SIZMAZ.
#   · URETICI  (`arastirma.factpacket.paket_dogrula`) -> `Y11-...`
#   · ALLOWLIST (`fact_baglama.*`)                    -> `FACT-...`
from arastirma import factpacket as _fp_uyum   # noqa: E402

# Uretici kodundan allowlist katmani koduna eslesme.
URETICI_KOD_ESLEME = {"Y11-ONERME-QUOTE-UYUMSUZ": KOD_ONERME_QUOTE_UYUMSUZ}


def onerme_quote_uyumu(onerme: str, exact_quote: str,
                       stance: str = "support") -> tuple:
    """ALLOWLIST katmaninin onerme<->quote uyum kapisi.

    ⚠ Olcum ureticiden (`factpacket`) gelir; DONEN KOD bu katmanin
    sozlesmesine cevrilir (`FACT-ONERME-QUOTE-UYUMSUZ`). Boylece uretici
    kodu (`Y11-...`) allowlist raporlarina SIZMAZ.
    """
    ok, kod, neden = _fp_uyum.onerme_quote_uyumu(onerme, exact_quote, stance)
    return ok, (URETICI_KOD_ESLEME.get(kod, kod) if kod else ""), neden


# Iddia CEVRESINDE gorulurse span'i CURUTEN isaretler.
_CEVRE_CURUTEN = (
    "it is false", "is false", "false", "verdict", "myth", "debunk",
    "retracted", "disputed", "denied", "denies", "deny", "hoax",
    "misleading", "unfounded", "baseless", "no evidence", "rumor", "rumour",
    "untrue", "not true", "fake", "reject", "alleged", "allegedly",
    "purported", "claim that", "claimed that", "yalanla", "asilsiz",
    "iddia edildi", "iddiasi", "soylenti", "dogrulanmadi", "yalan",
    "curutuldu", "geri cekildi", "reddetti", "reddedildi",
)
# ⚠ OLCULEN KUSUR (`Y11B1-SABIT-PENCERE-KOR`, commit-sonrasi denetim):
# ±160 karakterlik SABIT pencere, ayni paragrafta quote'tan 160+ karakter
# UZAKTA duran "this myth was debunked" cumlesini GOREMIYORDU. Cevre artik
# karakter sayisiyla degil, quote'u KAPSAYAN IDDIA BLOGU (paragraf) ile
# tanimlanir; blok bulunamazsa fail-closed olarak TUM belge taranir.
_PARAGRAF = re.compile(r"\n\s*\n")
_CUMLE_SONU = ".?!"


def kapsayan_blok(exact_quote: str, belge_metni: str) -> str:
    """Quote'u KAPSAYAN iddia blogu (paragraf). Bulunamazsa TUM belge."""
    from arastirma import factpacket as _fp
    q = _fp.normalize(exact_quote)
    for parca in _PARAGRAF.split(str(belge_metni or "")):
        blok = _fp.normalize(parca)
        if q and q in blok:
            return blok
    return _fp.normalize(belge_metni)


def iddia_mi(metin: str) -> tuple:
    """Metnin KENDISI bir iddia mi? `(iddia, neden)`.

    ⚠ `Y11B1-SPAN-IDDIA-DEGIL`: soru cumlesi TAM ESITLIK sozlesmesini
    gecer ama hicbir sey ONERMEZ; olgu havuzuna giremez.
    """
    from arastirma import factpacket as _fp
    if "?" in _fp.normalize(metin):
        return False, "metin SORU isareti tasiyor"
    return True, ""


def cevre_curutuyor_mu(exact_quote: str, belge_metni: str) -> tuple:
    """Quote'un BELGEDEKI CEVRESI onu curutuyor mu? `(curuk, kanit)`.

    ⚠ `Y11B1-SPAN-CEVRE-BAGLAMI`: TAM ESITLIK sozlesmesi bile span'in
    CEVRESINI gormez. "It is false that <quote>", "FALSE: <quote>",
    "Officials rejected the claim that <quote>" ya da paragrafin ilerisinde
    duran "this myth was debunked" biciminde belgede quote BIREBIR gecer
    ama iddia DESTEKLENMEZ. Kapsayan blok fail-closed taranir.
    """
    from arastirma import factpacket as _fp
    q, b = _fp.normalize(exact_quote), _fp.normalize(belge_metni)
    if q not in b:
        return False, ""
    blok = kapsayan_blok(exact_quote, belge_metni)
    i = blok.find(q)
    if i < 0:
        return True, "span kapsayan blokta cozulemedi"
    # Quote'u tasiyan CUMLE soru ise iddia degildir.
    kalan = blok[i + len(q):]
    for ch in kalan:
        if ch in _CUMLE_SONU:
            if ch == "?":
                return True, "span bir SORU cumlesinin parcasi"
            break
    for cue in _CEVRE_CURUTEN:
        if cue in blok.replace(q, " "):
            return True, f"cevre isareti: {cue!r}"
    return False, ""


def kanit_replay_edilebilir_mi(paket, belge_metni: str = "") -> tuple:
    """Paketin kaniti REPLAY edilebilir mi? `(ok, kod, neden)`.

    Belge verilirse quote GERCEKTEN belgede aranir ve `document_hash`
    belgeyle karsilastirilir (stale tespiti).
    """
    from arastirma import factpacket as _fp
    for alan, kod in (("exact_quote", KOD_KANIT_EKSIK),
                      ("locator", KOD_KANIT_EKSIK),
                      ("document_hash", KOD_KANIT_EKSIK),
                      ("source_id", KOD_KANIT_EKSIK)):
        if not str(getattr(paket, alan, "") or "").strip():
            return False, kod, f"{alan} yok"
    _url = str(getattr(paket, "url", "") or "").strip()
    if not _url:
        return False, KOD_KANIT_EKSIK, "canonical_url yok"
    # ⚠ OLCULEN KUSUR (`Y11B1-SOURCE-BAGI-YOK`, denetim): `source_id` ile
    # `url` BAGIMSIZ alanlardi; replay sonrasi url degistirilse bile
    # source_id ayni kaliyor ve kanit ZEHIRLI bir URL'ye baglaniyordu.
    if str(getattr(paket, "source_id", "")) != _fp.source_id_uret(_url):
        return False, KOD_KANIT_EKSIK, "source_id canonical_url ile TUTMUYOR"
    if str(getattr(paket, "stance", "")).lower() != "support":
        return False, KOD_STANCE_DESTEK_DEGIL, f"stance={paket.stance!r}"
    # ⚠ OLCULEN KUSUR (`Y11B1-SPAN-IDDIA-DEGIL`, commit-sonrasi denetim):
    # span'in KENDISI soru cumlesi olabilir; TAM ESITLIK gecer ama iddia yok.
    for _alan in ("onerme", "exact_quote"):
        _iddia, _n = iddia_mi(getattr(paket, _alan, ""))
        if not _iddia:
            return False, KOD_SPAN_IDDIA_DEGIL, f"{_alan}: {_n}"
    if bilesik_claim_mi(paket.onerme, paket.exact_quote):
        return False, KOD_BILESIK_CLAIM, "bilesik claim tek span destekliyor"
    # ⚠ ONERME kendi QUOTE'u tarafindan DESTEKLENMELI (uydurma rakam kapisi).
    # ⚠ STANCE-AWARE: support -> entailment, refute -> acik celiski.
    _ok, _kod, _neden = onerme_quote_uyumu(paket.onerme, paket.exact_quote,
                                           getattr(paket, "stance", "support"))
    if not _ok:
        return False, KOD_ONERME_QUOTE_UYUMSUZ, _neden
    if belge_metni:
        if _fp.belge_ozeti(belge_metni) != str(paket.document_hash or ""):
            return False, KOD_KANIT_BAYAT, "document_hash belgeyle tutmuyor"
        if not _fp.alinti_dogrula(paket.exact_quote, belge_metni):
            return False, KOD_KANIT_EKSIK, "quote replay edilemedi"
        _curuk, _kanit = cevre_curutuyor_mu(paket.exact_quote, belge_metni)
        if _curuk:
            return False, KOD_CEVRE_CURUTUYOR, _kanit
    return True, "", ""


# ─────────────────── MUHURLU (SEALED) KAYIT ───────────────────
# ⚠ OLCULEN KUSUR (`Y11B1-PUBLIC-HASH-YETKI-DEGIL`, denetim): dogrulama
# ciktisi PUBLIC, ANAHTARSIZ bir ozet (`icerik_snapshot`) idi. Cagiran
# kendi sahte paketini uretip AYNI fonksiyonla kendi snapshot'ini
# hesaplayabiliyor ve REPLAY OLMADAN "dogrulanmis olgu" uretebiliyordu.
# Ayni acik `olgu_snapshot_uret` icin de gecerliydi.
# ⚠ OLCULEN KUSUR (`Y11B1-MUHURSUZ-ALAN-MUTASYONU`): muhur yalnizca bir
# kac alani kapsayinca REPLAY SONRASI `paket.url` ya da ic ice
# `kaynaklar[].url` degistirilebiliyor ve olgu/atif ZEHIRLI URL tasiyordu.
# ⚠ COZUM: dogrulayici, TUM alanlari DERIN DONDURULMUS (deep-frozen) bir
# kayda kopyalar ve SUREC ICI GIZLI ANAHTARLA muhurler. Yetki YALNIZCA
# muhurlu kayittan turer; ham paket/dict KABUL EDILMEZ.
_MUHUR_ANAHTARI = secrets.token_bytes(32)      # ⚠ disa ACILMAZ, surec ici

_MUHURLU_ALANLAR = ("fact_id", "onerme", "exact_quote", "locator",
                    "document_hash", "source_id", "source_class", "stance",
                    "url", "alan", "baslik", "yayin_tarihi", "erisim_tarihi",
                    "kategori", "kritik", "verification_status")


def _dondur(deger):
    """Derin DONDURMA: dict -> MappingProxy, list -> tuple."""
    if isinstance(deger, dict):
        return types.MappingProxyType(
            {k: _dondur(v) for k, v in sorted(deger.items())})
    if isinstance(deger, (list, tuple, set)):
        return tuple(_dondur(v) for v in deger)
    return deger


def _muhur_govdesi(alanlar: dict) -> str:
    return "\n".join(f"{k}={alanlar.get(k)!r}"
                      for k in sorted(alanlar))


def _muhurle(alanlar: dict) -> str:
    return hmac.new(_MUHUR_ANAHTARI,
                    _muhur_govdesi(alanlar).encode("utf-8"),
                    hashlib.sha256).hexdigest()


def muhurlu_kayit(paket) -> types.MappingProxyType:
    """Paketten DERIN DONDURULMUS, MUHURLU kayit uret.

    ⚠ Cagiran bu muhuru URETEMEZ: anahtar surec icidir ve disa acilmaz.
    """
    alanlar = {a: _dondur(getattr(paket, a, None)) for a in _MUHURLU_ALANLAR}
    alanlar["muhur"] = _muhurle({k: v for k, v in alanlar.items()})
    return types.MappingProxyType(alanlar)


def muhur_gecerli_mi(kayit) -> bool:
    """Kayit MUHURLU ve BOZULMAMIS mi?"""
    if not isinstance(kayit, types.MappingProxyType):
        return False
    m = kayit.get("muhur")
    if not m:
        return False
    govde = {k: v for k, v in kayit.items() if k != "muhur"}
    return hmac.compare_digest(str(m), _muhurle(govde))


def icerik_snapshot(paketler) -> str:
    """Paket kumesinin ICERIGE BAGLI, SIRA BAGIMSIZ ozeti.

    ⚠ `Y11B1-SNAPSHOT-ICERIKSIZ`: kimlik listesi TEK BASINA snapshot
    olamaz — dogrulama sonrasi icerik mutasyonunu yakalayamaz.
    """
    parcalar = []
    for p in (paketler or []):
        parcalar.append("|".join((
            str(getattr(p, "fact_id", "")),
            str(getattr(p, "onerme", "")),
            str(getattr(p, "exact_quote", "")),
            str(getattr(p, "document_hash", "")),
            str(getattr(p, "source_id", "")),
            str(getattr(p, "stance", "")),
            str(getattr(p, "verification_status", "")),
        )))
    return hashlib.sha256(
        "\n".join(sorted(parcalar)).encode("utf-8")).hexdigest()[:32]


def kimlik_icerikten_mi(paket) -> bool:
    """`fact_id` GUNCEL icerikten mi turuyor? Mutasyon yakalar."""
    from arastirma import factpacket as _fp
    return str(getattr(paket, "fact_id", "")) == _fp.fact_id_uret(
        getattr(paket, "onerme", ""), getattr(paket, "exact_quote", ""),
        getattr(paket, "source_id", ""))


def allowlist_kur(paketler, *, belgeler=None) -> dict:
    """KABUL EDILMIS FactPacket allowlist'i. ⚠ SIRA BAGIMSIZ, deterministik.

    ⚠ OLCULEN KUSUR (`Y11B1-REPLAY-BELGESIZ-KABUL`, denetim): ilk yazimda
    `belgeler` OPSIYONELDI — verilmezse ya da paketin `source_id`si
    haritada yoksa kanit REPLAY EDILMEDEN paket KABUL EDILIYORDU. Bu,
    "yalnizca kaniti REPLAY EDILEBILIR paket allowlist'e girer"
    sozlesmesinin FAIL-OPEN ihlaliydi: sahte bir `accepted` damgasi +
    eksik belge ile paket geciyordu.
    ⚠ ARTIK REPLAY BELGESI HER PAKET ICIN ZORUNLUDUR:
      · `belgeler` yok / paketin `source_id`si haritada yok
        -> `FACT-KANIT-ALINAMADI`
      · belge var ama `document_hash` tutmuyor -> `FACT-KANIT-BAYAT`
      · belge var, hash tutuyor ama quote gecmiyor -> `FACT-KANIT-EKSIK`

    `belgeler`: `{source_id: belge_metni}` — ZORUNLU.
    Doner: {"allowlist": set, "paketler": [...], "redler": [...],
            "snapshot": str}
    """
    from arastirma import factpacket as _fp
    bel = belgeler or {}
    aday, redler = [], []
    for p in (paketler or []):
        # ⚠ OLCULEN KUSUR (`Y11B-STATUS-VARSAYILAN-ACCEPTED`, denetim):
        # ilk yazimda alan YOKSA "accepted" VARSAYILIYORDU — bu, "yalnizca
        # verification_status=accepted allowlist'e girer" sozlesmesinin
        # DOGRUDAN IHLALIDIR. Alan YOKSA da RED.
        durum = str(getattr(p, "verification_status", "") or "")
        if durum.lower() != "accepted":
            redler.append({"kod": KOD_STATUS_ACCEPTED_DEGIL,
                           "fact_id": getattr(p, "fact_id", ""),
                           "neden": (f"verification_status={durum!r}"
                                     if durum else
                                     "verification_status ALANI YOK")})
            continue
        _sid = str(getattr(p, "source_id", "") or "")
        _belge = bel.get(_sid, "")
        if not _belge:
            # ⚠ FAIL-CLOSED: replay belgesi YOKSA kanit DOGRULANAMAZ.
            redler.append({"kod": KOD_KANIT_ALINAMADI,
                           "fact_id": getattr(p, "fact_id", ""),
                           "neden": (f"replay belgesi yok (source_id="
                                     f"{_sid[:12] or 'YOK'})")})
            continue
        # ⚠ `Y11B1-KIMLIK-YENIDEN-TURETIM`: tuketici replay'i URETICI ile
        # BIREBIR ayni — `fact_id` GUNCEL icerikten yeniden turetilir.
        if not kimlik_icerikten_mi(p):
            redler.append({"kod": KOD_KIMLIK_UYUMSUZ,
                           "fact_id": getattr(p, "fact_id", ""),
                           "neden": "fact_id GUNCEL icerikten turemiyor "
                                    "(eski kimlik altinda mutasyon)"})
            continue
        ok, kod, neden = kanit_replay_edilebilir_mi(p, _belge)
        if ok:
            aday.append(p)
        else:
            redler.append({"kod": kod, "fact_id": getattr(p, "fact_id", ""),
                           "neden": neden})
    # ⚠ CELISKI — Y-11b-1'de KURULMAZ.
    # ONCEKI TURLAR: `Y11B1-STALE-REFUTE-ZEHIRI` (bayat/ilgisiz refute
    # gecerli support'u dusuruyordu) ve `Y11B1-CELISKI-ZAMAN-KOR` (yil
    # bazli kapsam 2024-01 destegini 2024-02 reddiyle zehirliyordu).
    # Ikisi de token/pattern temelli celiski kararinin semptomlariydi.
    # OLCULEN KUSUR (`Y11B1-ERKEN-CELISKI-KARARI`, denetim): celiski karari
    # birden fazla yerde (uretici `celiski_tara` + burada) veriliyordu ve
    # her token/pattern kurali yeni bir zehirleme yolu aciyordu. ⚠ Refute
    # paketleri artik FAIL-CLOSED `unresolved` (bkz. `factpacket.
    # onerme_quote_uyumu`); allowlist'e girmez ve GECERLI SUPPORT'U
    # ZEHIRLEYEMEZ. Tek otorite BU fonksiyondur.
    for p in (paketler or []):
        if str(getattr(p, "stance", "")).lower() == "refute":
            redler.append({"kod": "FACT-REFUTE-COZULMEDI",
                           "fact_id": getattr(p, "fact_id", ""),
                           "neden": "refute Y-11b-1'de fail-closed unresolved"})
    kabul = list(aday)
    # ⚠ MUHURLU kayitlar: yetki YALNIZCA bunlardan turer.
    muhurlu = tuple(muhurlu_kayit(p) for p in kabul)
    izin = {p.fact_id for p in kabul}
    # ⚠ OLCULEN KUSUR (`Y11B1-SNAPSHOT-ICERIKSIZ`, denetim): snapshot
    # yalnizca KIMLIKLERDEN turetiliyordu. Sonuc: (a) herhangi bos-olmayan
    # bir sozde-snapshot + kimlik listesi REPLAY OLMADAN kabul goruyordu,
    # (b) dogrulamadan SONRA `paket.onerme` mutasyona ugrasa bile AYNI
    # fact_id altinda geciyordu.
    # ⚠ Snapshot artik ICERIGE BAGLI ve SIRA BAGIMSIZ.
    snap = icerik_snapshot(kabul)
    return {"allowlist": izin,
            "muhurlu": muhurlu,
            "paketler": sorted(kabul, key=lambda x: x.fact_id),
            "redler": redler, "snapshot": snap,
            "bagimsiz_alan": bagimsiz_alan_sayisi(kabul)}


# ── SECTIONPLAN -> FACTBEAT -> SHOT TAHSISI ──
# ⚠ OLCULEN KUSUR (`Y11B-TAHSIS-YOLU-YOK`, denetim): yalnizca allowlist +
# dogrulayici olmasi atomu KAPATMAZ. Her scene/shot'in `primary_fact_id`i
# URETIM ANINDA, DETERMINISTIK bir tahsisten gelmeli; sonradan eslestirme
# YOK. Asagidaki fonksiyon o tahsis yoludur.
# ⚠ Roller: `sonuc`/`closing` YENI fact getiremez — yalnizca o chapter'da
# ZATEN tahsis edilmis bir fact'i tekrar kullanir (Y-18 sozlesmesiyle
# birebir ayni kural).
SONUC_ROLLERI = ("sonuc", "closing")


def tahsis_et(paketler, sahneler, *, allowlist=None) -> dict:
    """accepted FactPacket -> SectionPlan -> FactBeat -> shot tahsisi.

    ⚠ DETERMINISTIK ve SIRA BAGIMSIZ: paketler `fact_id`ye gore siralanir,
    sahneler girdi sirasini korur ama tahsis yalnizca (chapter, sira)
    fonksiyonudur — ayni girdi kumesi her zaman AYNI snapshot'i verir.
    ⚠ Ayni fact BIRDEN COK shotta kullanilabilir.

    Doner: {"tahsis": {scene_id: fact_id}, "bolum_kapsami": {cid: n},
            "snapshot": str, "kod": str, "neden": str}
    """
    izin = set(allowlist) if allowlist is not None else {
        getattr(p, "fact_id", "") for p in (paketler or [])}
    havuz = sorted({getattr(p, "fact_id", "") for p in (paketler or [])}
                   & izin)
    liste = [s for s in (sahneler or []) if isinstance(s, dict)]
    bos = {"tahsis": {}, "bolum_kapsami": {}, "snapshot": "", "kod": "",
           "neden": ""}
    if not liste:
        return {**bos, "kod": KOD_SHOT_FACT_YOK, "neden": "sahne yok"}
    if not havuz:
        return {**bos, "kod": KOD_GROUNDED_FACT_YOK,
                "neden": "kabul edilmis FactPacket YOK"}

    # ── SectionPlan: chapter sirasi KORUNUR ──
    bolum_sira, bolum_sahne = [], {}
    for i, s in enumerate(liste):
        cid = str(s.get("chapter_id") or s.get("bolum_id") or "c01")
        if cid not in bolum_sahne:
            bolum_sahne[cid] = []
            bolum_sira.append(cid)
        bolum_sahne[cid].append((i, s))

    tahsis, kapsam = {}, {}
    for b_i, cid in enumerate(bolum_sira):
        # ⚠ Chapter havuzu: DETERMINISTIK dilim (bolum indeksinden kayar).
        n = len(havuz)
        c_havuz = [havuz[(b_i + k) % n] for k in range(n)]
        kullanilan = []
        for j, (idx, s) in enumerate(bolum_sahne[cid]):
            sid = str(s.get("scene_id") or f"s{idx + 1:03d}")
            rol = str(s.get("beat_role") or "").lower()
            if rol in SONUC_ROLLERI and kullanilan:
                # ⚠ Sonuc/kapanis YENI fact GETIREMEZ.
                fid = kullanilan[0]
            else:
                fid = c_havuz[j % len(c_havuz)]
                kullanilan.append(fid)
            tahsis[sid] = fid
        kapsam[cid] = len(set(kullanilan))
    snap = hashlib.sha256(
        "|".join(f"{k}={tahsis[k]}" for k in sorted(tahsis)).encode()
    ).hexdigest()[:16]
    return {"tahsis": tahsis, "bolum_kapsami": kapsam, "snapshot": snap,
            "kod": "", "neden": ""}


def getirme_sonucu_degerlendir(sayfa) -> dict:
    """Kaynak getirme sonucu. ⚠ COZULEMEYEN durumda FALLBACK YOK."""
    d = sayfa if isinstance(sayfa, dict) else {}
    if d.get("ok") and str(d.get("metin") or "").strip():
        return {"durum": "cozuldu", "kod": ""}
    hata = str(d.get("hata") or "").lower()
    _ = any(x in hata for x in _COZULEMEYEN)      # tani icin; hepsi ayni sonuc
    return {"durum": "unresolved", "kod": KOD_KANIT_ALINAMADI,
            "neden": str(d.get("hata") or "kanit alinamadi")[:160]}


def shot_fact_dogrula(shotlar, *, allowlist) -> dict:
    """⚠ TUM shotlar denetlenir — footage OLSUN OLMASIN (Y11B-SADECE-FOOTAGE).

    Her shot allowlist'ten tam bir `primary_fact_id` tasimak ZORUNDA.
    ⚠ Onceden doldurulmus (prefilled) kimlik DOGRULANMADAN kabul EDILMEZ:
    allowlist'te yoksa RED (Y11B-PREFILLED-KABUL).
    ⚠ Ayni fact BIRDEN COK shotta kullanilabilir — bu bir ihlal DEGILDIR.
    """
    izin = set(allowlist or ())
    liste = [s for s in (shotlar or []) if isinstance(s, dict)]
    bos, disi, kullanilan = [], [], []
    for i, s in enumerate(liste):
        fid = str(s.get("primary_fact_id") or s.get("fact_id") or "").strip()
        sid = str(s.get("scene_id") or f"#{i + 1}")
        if not fid:
            bos.append(sid)
        elif fid not in izin:
            disi.append(f"{sid}:{fid}")
        else:
            kullanilan.append(fid)
    hedef = len(liste)
    bagli = len(kullanilan)
    kapsam = round(bagli / hedef, 4) if hedef else 0.0
    kod, neden = "", ""
    if disi:
        kod, neden = (KOD_SHOT_FACT_ALLOWLIST_DISI,
                      f"allowlist disi fact_id: {disi[:6]}")
    elif bos:
        kod, neden = KOD_SHOT_FACT_YOK, f"fact_id tasimayan shot: {bos[:6]}"
    return {"hedef": hedef, "bagli": bagli, "kapsam": kapsam,
            "benzersiz_fact": len(set(kullanilan)),
            "bos": bos, "allowlist_disi": disi,
            "kod": kod, "neden": neden}


def grounded_kapisi(*, mod: str, arastirma_calisti: bool,
                    arastirma_hatasi: str, allowlist,
                    cozulemeyen: int = 0, bolum_kapsami=None) -> dict:
    """Grounded belgesel FAIL-CLOSED kapisi.

    ⚠ `Y11B-GROUNDED-FAIL-OPEN`: eski kapi `if _olgular:` blogunun
    ICINDEYDI — arastirma kapali/hatali/0 olgu ise HIC KOSMUYOR ve is
    kullanici metniyle SESSIZCE devam ediyordu.
    ⚠ Grounded OLMAYAN yaratici modlar KAPSAM DISIDIR: davranislari
    DEGISMEZ (`gecti=True, kapsam_disi=True`).
    """
    if str(mod or "") not in GROUNDED_MODLAR:
        return {"gecti": True, "kapsam_disi": True, "kod": "",
                "neden": f"mod={mod!r} grounded degil"}
    izin = set(allowlist or ())
    if not arastirma_calisti:
        return {"gecti": False, "kapsam_disi": False,
                "kod": KOD_GROUNDED_ARASTIRMA_YOK,
                "neden": "grounded belgeselde arastirma KOSMADI"}
    if str(arastirma_hatasi or "").strip():
        return {"gecti": False, "kapsam_disi": False,
                "kod": KOD_GROUNDED_ARASTIRMA_HATA,
                "neden": str(arastirma_hatasi)[:160]}
    if not izin:
        return {"gecti": False, "kapsam_disi": False,
                "kod": KOD_GROUNDED_FACT_YOK,
                "neden": "kabul edilmis FactPacket YOK (0 fact)"}
    try:
        coz = int(cozulemeyen or 0)
    except (TypeError, ValueError):
        coz = 1
    if coz > 0:
        return {"gecti": False, "kapsam_disi": False,
                "kod": KOD_GROUNDED_KANIT_COZULEMEDI,
                "neden": f"{coz} kanit cozulemedi (fetch/parse/verify)"}
    kapsam = bolum_kapsami if isinstance(bolum_kapsami, dict) else {}
    zayif = sorted(c for c, n in kapsam.items()
                   if int(n or 0) < BOLUM_ASGARI_FACT)
    if not kapsam or zayif:
        return {"gecti": False, "kapsam_disi": False,
                "kod": KOD_GROUNDED_BOLUM_KAPSAMI,
                "neden": (f"bolum fact kapsami yetersiz: {zayif[:6]}"
                          if zayif else "bolum fact kapsami olculmedi")}
    return {"gecti": True, "kapsam_disi": False, "kod": "", "neden": ""}


# ── ENTAILMENT ──
# Fact'in TASIYICI unsurlari: sayilar, yillar, birimler, ozel adlar/yerler.
_BIRIM = re.compile(r"\b(%|yuzde|percent|kisi|vaka|case[s]?|deaths?|olum|"
                    r"yil|year[s]?|ay|month[s]?|gun|day[s]?|km|m|kg|ton|"
                    r"tl|usd|eur|dolar|euro|milyon|milyar|bin|thousand|"
                    r"million|billion)\b", re.I)
_OZEL_AD = re.compile(r"\b([A-ZÇĞİÖŞÜ][\wçğıöşü]{2,})\b")
_ENTAIL_ASGARI_ORTUSME = 0.34


def _entail_belirtec(metin: str) -> set:
    return {k.lower() for k in re.findall(
        r"[0-9a-zA-ZçğıöşüÇĞİÖŞÜ]{4,}", str(metin or ""))
        if k.lower() not in {
            "olarak", "icin", "sonuc", "bunu", "bunun", "daha", "gibi",
            "kadar", "sonra", "once", "olan", "oldu", "ancak", "yani",
            "this", "that", "with", "from", "have", "been", "were",
            "their", "which", "about", "there", "these", "those"}}


def entail_dogrula(metin: str, paket) -> dict:
    """Anlatim/shot, primary fact'i GERCEKTEN entail ediyor mu?

    ⚠ OLCULEN KUSUR (`Y11B-ENTAIL-TEK-YONLU`, denetim): ilk yazim YALNIZCA
    "yeni sayi/yil eklendi mi" diye bakiyordu. Bu yuzden fact'le HIC
    ILGISI OLMAYAN bir cumle ("Sonuc olarak tablo degisti") PASS
    aliyordu — entailment OLCULMUYORDU, yalnizca kirlilik olculuyordu.

    ⚠ Iki yonlu olcum:
      A) ILGI — metin, fact'in tasiyici unsurlarindan (sayi/yil/ozel ad/
         anahtar kelime) YETERINCE pay tasimali; taşımıyorsa ILGISIZ.
      B) KIRLILIK — metin, fact'te GECMEYEN sayi/yil/birim/ozel ad
         EKLEYEMEZ (entity/name/unit/time/place/scope farki).
    """
    kaynak = f"{getattr(paket, 'onerme', '')} {getattr(paket, 'exact_quote', '')}"
    m = str(metin or "")

    izinli_sayi = _norm_sayi(kaynak)
    izinli_yil = set(_YIL.findall(kaynak))
    izinli_birim = {x.lower() for x in _BIRIM.findall(kaynak)}
    izinli_ad = {x.lower() for x in _OZEL_AD.findall(kaynak)}
    izinli_bt = _entail_belirtec(kaynak)

    m_sayi, m_yil = _norm_sayi(m), set(_YIL.findall(m))
    m_birim = {x.lower() for x in _BIRIM.findall(m)}
    m_ad = {x.lower() for x in _OZEL_AD.findall(m)}
    m_bt = _entail_belirtec(m)

    # ── (A) ILGI: fact'in tasiyici unsurlarindan pay ──
    tasiyici = (izinli_sayi | izinli_yil | izinli_ad) or izinli_bt
    ortak = (m_sayi | m_yil | m_ad | m_bt) & tasiyici
    ortusme = (len(ortak) / len(tasiyici)) if tasiyici else 0.0
    if not ortak or ortusme < _ENTAIL_ASGARI_ORTUSME:
        return {"gecti": False, "kod": KOD_ENTAIL_ILGISIZ,
                "ortusme": round(ortusme, 3), "yeni_sayi": [], "yeni_yil": [],
                "neden": (f"metin fact'i entail etmiyor "
                          f"(ortusme {ortusme:.2f} < "
                          f"{_ENTAIL_ASGARI_ORTUSME:.2f})")}

    # ── (B) KIRLILIK: allowlist disi deger/entity ──
    yeni_yil = sorted(m_yil - izinli_yil)
    yeni_sayi = sorted(s for s in (m_sayi - izinli_sayi) if s not in yeni_yil)
    # ⚠ Birim TEK BASINA ihlal DEGILDIR: fact "cases" derken anlatim
    # "vaka" diyebilir (dil/es anlam). Ihlal, YENI BIR SAYIYA baglanan
    # birimdir — yani olcek/kapsam GERCEKTEN degismistir.
    yeni_birim = (sorted(m_birim - izinli_birim)
                  if (yeni_sayi or yeni_yil) else [])
    yeni_ad = sorted(m_ad - izinli_ad)
    if yeni_sayi or yeni_yil or yeni_birim or yeni_ad:
        return {"gecti": False, "kod": KOD_ENTAIL_YENI_DEGER,
                "ortusme": round(ortusme, 3),
                "yeni_sayi": yeni_sayi[:6], "yeni_yil": yeni_yil[:4],
                "yeni_birim": yeni_birim[:4], "yeni_ad": yeni_ad[:4],
                "neden": (f"fact disi unsur: sayi={yeni_sayi[:3]} "
                          f"yil={yeni_yil[:3]} birim={yeni_birim[:3]} "
                          f"ad={yeni_ad[:3]}")}
    return {"gecti": True, "kod": "", "ortusme": round(ortusme, 3),
            "yeni_sayi": [], "yeni_yil": []}
