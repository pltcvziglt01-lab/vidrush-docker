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
# ⚠ Bu tuple YALNIZCA "grounded UYGUN mod" demektir; TEK BASINA STRICT
# fail-closed YETKISI DEGILDIR (bkz. `strict_grounded_mi`).
GROUNDED_MODLAR = ("documentary",)

# ── P0 (16 Agu 2026, CANLI OLCUM): STRICT GROUNDED ACIKCA SECILIR ──
# ⚠ OLCULEN KUSUR (`Y11B2-STRICT-VARSAYILAN`): strict kapi YALNIZCA
# `mod == "documentary"` kosuluna baglanmisti. Arayuzde/API'de grounded
# SECIMI HIC YOKTU, yani belgesel secen HER kullanici — konusu arastirma
# odakli olmasa da — fail-closed hatta dusuyordu. Canli sonuc: normal bir
# belgesel isi `GROUNDED-FACT-YOK: kabul edilmis FactPacket YOK (0 yetkili
# olgu)` ile medya/TTS/render'a HIC gecmeden oldu.
# Karar: STRICT yalnizca ACIKCA arastirma sozu veren edit profillerinde
# uygulanir. Digerleri BEST-EFFORT'tur: accepted FactPacket VARSA kullanilir,
# yoksa is GORUNUR bir uyari ile kullanici metninden non-grounded surer.
# ⚠ Bu bir GEVSETME DEGIL, KAPSAM TANIMIDIR: strict profilde sozlesmenin
# TEK BIR MADDESI de gevsetilmedi (0 fact/hata/cozulemeyen kanit -> FAIL).
STRICT_EDIT_PROFILLERI = ("belgesel-arastirmaci", "bilim-anlatisi")

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
# ⚠ `Y11B2-SHOT-RAPORU-YOK`: `grounded_kapisi` tum-shot bilgisi OLMADAN
# PASS veremez — "olculemedi" GECTI demek DEGILDIR.
KOD_SHOT_RAPORU_YOK = "SHOT-RAPORU-YOK"
# ⚠ `Y11B2-KANONIK-BYPASS`: ayni sahnede HEM kanonik (`chapter_id`/
# `beat_role`) HEM ham (`bolum`/`islev`) alan varsa otorite BELIRSIZDIR.
KOD_PROJEKSIYON_BELIRSIZ = "SHOT-PROJEKSIYON-BELIRSIZ"
# ⚠ OLCULEN KUSUR (`Y11B2-RESOLVER-AYRISMASI`, exact-matcher denetimi):
# tahsis kapisi konusulan metni `voiceover > anlatim > narration` diye
# COZUYORDU, ama TTS YALNIZCA ham `voiceover` alanini okuyor
# (`metin = str(s.get("voiceover", "")).strip()`). Iki resolver ayrisinca
# `voiceover` bos/None/False/0/[]/{} iken `anlatim` kanonik olabiliyor;
# shot yetkili kimligi ve all-shot kapisini GECIYOR ama DOGRULANAN CUMLE
# HIC SESLENDIRILMIYORDU. Tek ortak resolver + fail-closed sozlesme.
KOD_KONUSULAN_ALAN_GECERSIZ = "SHOT-KONUSULAN-ALAN-GECERSIZ"
# ⚠ `Y11B2-SURE-CATISMASI`: kanonik fact cumleleri kelime bandindan MUAF
# oldugu icin hedef sure tutturulamayabilir. Sessiz uzatma YOK.
KOD_GROUNDED_SURE_YETERSIZ = "GROUNDED-SURE-YETERSIZ"
# ⚠ `Y11B2-HEURISTIK-SONSUZ`: anlatim tarafindaki SEZGISEL polarite/
# baglam/kapsam kodlari OTORITE OLMAKTAN CIKARILDI ve KALDIRILDI (olu
# karmasiklik birakilmadi). Yerine TEK, DAR, fail-closed kural:
# konusulan metin KANONIK onerme ile normalize BIREBIR AYNI olmali.
KOD_ENTAIL_EXTRACTIVE_DEGIL = "FACT-ENTAIL-EXTRACTIVE-DEGIL"

KODLAR = (KOD_KANIT_EKSIK, KOD_KANIT_BAYAT, KOD_KANIT_ALINAMADI,
          KOD_STANCE_DESTEK_DEGIL, KOD_CELISKI, KOD_BILESIK_CLAIM,
          KOD_SHOT_FACT_YOK, KOD_SHOT_FACT_ALLOWLIST_DISI,
          KOD_GROUNDED_ARASTIRMA_YOK, KOD_GROUNDED_ARASTIRMA_HATA,
          KOD_GROUNDED_FACT_YOK, KOD_GROUNDED_KANIT_COZULEMEDI,
          KOD_GROUNDED_BOLUM_KAPSAMI,
          KOD_ENTAIL_ILGISIZ, KOD_STATUS_ACCEPTED_DEGIL,
          KOD_ONERME_QUOTE_UYUMSUZ, KOD_REFUTE_COZULMEDI,
          KOD_KIMLIK_UYUMSUZ, KOD_CEVRE_CURUTUYOR, KOD_SPAN_IDDIA_DEGIL,
          KOD_SHOT_RAPORU_YOK,
          KOD_PROJEKSIYON_BELIRSIZ, KOD_ENTAIL_EXTRACTIVE_DEGIL,
          KOD_KONUSULAN_ALAN_GECERSIZ, KOD_GROUNDED_SURE_YETERSIZ)

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

# ── ORTAK YAY PROJEKSIYONU (Y-18 ile TEK KAYNAK) ──
# ⚠ OLCULEN KUSUR (`Y11B2-DURAGAN-PROJEKSIYON`, final denetim): pipeline
# projeksiyonu `chapter_id = bolum or "c01"` biciminde DURAGANDI. Uretim
# planinda `bolum` basligi YALNIZCA bolumun ILK sahnesinde dolar; araya
# giren sahneler bos gelir. Duragan projeksiyon bunlarin hepsini "c01"e
# yiginca CH2'nin kapanisi CH1'in fact'lerini "onceki" sayiyor ve chapter
# kapsami YANLIS olculuyordu. Dogru davranis `yay_plani_kur` ile AYNI:
# bolum basligi dolu olan sahne YENI bolum acar, sonrakiler ona AITTIR.
ISLEV_YAY_ROLU = {
    "acilis": "hook", "soru": "hook",
    "aciklama": "baglam", "gecmis": "baglam",
    "vurgu": "kanit", "liste": "kanit", "ornek": "kanit",
    "karsilastir": "karsitlik",
    "sonuc": "sonuc",
    "kapanis": "closing",
}


# ⚠ OLCULEN KUSUR (`Y11B2-KANONIK-BYPASS`, final denetim): projeksiyon HAM
# alanlari (`bolum`/`islev`) okuyup KANONIK alanlari EZIYORDU. Iki somut
# kacak olculdu: (a) `beat_role="kapanis"` NORMALIZE EDILMEDIGI icin
# `SONUC_ROLLERI` ("sonuc"/"closing") ile eslesmiyor ve KAPANIS YASAGINI
# ATLIYORDU; (b) acikca verilmis `chapter_id="c02"` ham sayac tarafindan
# "c01"e INDIRILIYOR, ikinci bolumun kapanisi birinci bolumun fact'lerini
# "onceki" sayiyordu. Kanonik alanlar KORUNUR ve NORMALIZE edilir; ham
# alanlar DURUM TASIYAN sayacla eslenir; IKISI KARISIRSA fail-closed.
_BOLUM_NO = re.compile(r"^c(\d+)$", re.I)


def rol_normalize(deger: str) -> str:
    """Ham ya da kanonik rolu KANONIK bicime indirger ("kapanis"->"closing")."""
    d = str(deger or "").strip().lower()
    return ISLEV_YAY_ROLU.get(d, d)


def yay_rolu(sahne) -> str:
    """Sahnenin YAPISAL yay rolu. ⚠ Metinden SEZILMEZ, IMAL EDILMEZ."""
    d = sahne if isinstance(sahne, dict) else {}
    return rol_normalize(
        str(d.get("beat_role") or "").strip()
        or ("kapanis" if d.get("kapanis") is True else "")
        or str(d.get("islev") or ""))


def yay_projeksiyonu(sahneler) -> list:
    """`(chapter_id, beat_role)` — kanonik KORUNUR, ham DURUMLA eslenir.

    ⚠ `yay_plani_kur` ile AYNI mantik (tek kaynak): `bolum` basligi dolu
    olan sahne yeni bolum acar; araya girenler ONCEKI bolume aittir.
    ⚠ Ayni sahnede HEM kanonik HEM ham alan varsa hangisinin otorite
    oldugu BELIRSIZDIR -> `("", "")` (fail-closed).
    """
    cikti, cno = [], 0
    for s in (sahneler or []):
        d = s if isinstance(s, dict) else {}
        kanonik_c = str(d.get("chapter_id") or "").strip()
        ham_b = str(d.get("bolum") or d.get("bolum_id") or "").strip()
        kanonik_r = str(d.get("beat_role") or "").strip()
        ham_r = (str(d.get("islev") or "").strip()
                 or ("kapanis" if d.get("kapanis") is True else ""))
        if (kanonik_c and ham_b) or (kanonik_r and ham_r):
            cikti.append(("", ""))          # ⚠ BELIRSIZ -> fail-closed
            continue
        if kanonik_c:
            cid = kanonik_c                 # ⚠ KANONIK KIMLIK KORUNUR
            m = _BOLUM_NO.match(cid)
            if m:                           # ham sayac kanonikle SENKRON
                cno = max(cno, int(m.group(1)))
        else:
            if ham_b or cno == 0:
                cno += 1
            cid = f"c{cno:02d}"
        cikti.append((cid, rol_normalize(kanonik_r or ham_r)))
    return cikti


# ⚠ OLCULEN KUSUR (`Y11B2-VOICEOVER-KOR`, pozitif kontrol kosumu): bu
# cozumleyicinin ilk surumu URETIM sahnelerinin anlatimi tasidigi
# `voiceover` alanini HIC OKUMUYORDU (`pipeline.py`:
# `metin = str(s.get("voiceover", "")).strip()`). Entailment BOS METIN
# olcuyor, her sahne ilgisiz sayiliyor ve grounded belgesel HER ZAMAN
# duruyordu. Kusur, 0-call olcumunun bos olup olmadigini sinayan pozitif
# kontrolde ortaya cikti: kapi gecildiginde downstream spy'lari hic
# ateslenmiyordu.
#
# ⚠ OLCULEN KUSUR (`Y11B2-YETKI-AKLAMA`, adversarial denetim): duzeltmenin
# ilk hali konusulan metni YARDIMCI alanlarla (`iddia_metni`,
# `footage_sorgu`, `scene_prompt`, `gorsel_prompt`) BIRLESTIRIYORDU.
# `iddia_metni` zaten FACT'IN KENDI METNI oldugu icin, izleyicinin DUYDUGU
# cumle fact'le tamamen ILGISIZ olsa bile skor yardimci alanlardan geliyor
# ve tahsis PASS aliyordu — kimlik AKLANIYORDU.
#
# Her ikisi de asagidaki TEK fail-closed cozumleyiciyle kapandi: yetkili
# konusulan alan YALNIZCA `voiceover`dir; yardimci alanlar skoru
# ARTIRAMAZ ve `anlatim`/`narration` fallback'i KALDIRILMISTIR.
def konusulan_alan(sahne) -> tuple:
    """TEK ORTAK RESOLVER: `(metin, kod, neden)`.

    ⚠ `Y11B2-RESOLVER-AYRISMASI`: grounded belgeselde SESLENDIRILEN alan
    YALNIZCA `voiceover`dir ve BOS OLMAYAN GERCEK BIR DIZGE olmak
    zorundadir. `None`/`False`/`0`/`[]`/`{}`/bos dizge — ya da alternatif
    bir alanda (`anlatim`/`narration`) metin bulunmasi — FAIL-CLOSED'dur:
    aksi halde dogrulanan cumle ile SESLENDIRILEN cumle AYRISIR.
    ⚠ TTS de AYNI ciktiyi tuketir; ikinci bir cozumleme YOKTUR.
    """
    d = sahne if isinstance(sahne, dict) else {}
    v = d.get("voiceover", None)
    if isinstance(v, str) and v.strip():
        return v.strip(), "", ""
    alternatif = [k for k in ("anlatim", "narration")
                  if str(d.get(k) or "").strip()]
    if v is None and not alternatif:
        return "", KOD_KONUSULAN_ALAN_GECERSIZ, "voiceover YOK"
    return "", KOD_KONUSULAN_ALAN_GECERSIZ, (
        f"voiceover gecersiz ({type(v).__name__}={v!r:.24}); "
        f"alternatif alan: {alternatif or 'yok'}")


def sahne_metni(sahne) -> str:
    """Sahnenin YETKILI konusulan metni. ⚠ Gecersizse BOS (fail-closed)."""
    return konusulan_alan(sahne)[0]


def tahsis_et(paketler, sahneler, *, allowlist) -> dict:
    """accepted FactPacket -> SectionPlan -> FactBeat -> shot tahsisi.

    ⚠ OLCULEN KUSUR (`Y11B2-BENZERLIK-OTORITESI`, 1a8c013 sonrasi denetim):
    uretim yolu `arastirma_kopru.fact_bagla` idi ve tahsisi **0.16 JACCARD**
    ile yapiyordu. Davranissal kanit: allowlist'te OLMAYAN
    `UYDURMA-KIMLIK-000` kimligi, yalnizca kelime ortusmesiyle bir footage
    sahnesine YAZILDI (`baglanan=1`). Kimlik BENZERLIKLE BULUNMAZ.
    ⚠ OLCULEN KUSUR (`Y11B2-KOR-ROUND-ROBIN`): bu fonksiyonun ilk surumu
    fact'i sahneye `(bolum, sira)` moduloyla — yani sahnenin NE ANLATTIGINA
    HIC BAKMADAN — dagitiyordu. Tahsis artik `entail_dogrula` ile OLCULUR;
    hicbir fact sahneyi entail etmiyorsa sahne fact ALMAZ (uydurma yok).
    ⚠ `allowlist` ZORUNLUDUR: paketin kendisi kendi yetkisi olamaz.
    ⚠ DETERMINISTIK ve SIRA BAGIMSIZ: esit entailment puaninda `fact_id`
    alfabetik kazanir; ayni girdi her zaman AYNI snapshot'i verir.
    ⚠ Ayni fact BIRDEN COK shotta kullanilabilir.

    Doner: {"tahsis": {scene_id: fact_id}, "bolum_kapsami": {cid: n},
            "bosluklar": [...], "snapshot": str, "kod": str, "neden": str}
    """
    if allowlist is None:
        return {"tahsis": {}, "bolum_kapsami": {}, "bosluklar": [],
                "snapshot": "", "kod": KOD_GROUNDED_FACT_YOK,
                "neden": "allowlist verilmedi (paket kendi yetkisi DEGIL)"}
    izin = set(allowlist)
    paket_ile = {getattr(p, "fact_id", ""): p for p in (paketler or [])
                 if getattr(p, "fact_id", "") in izin}
    havuz = sorted(paket_ile)
    liste = [s for s in (sahneler or []) if isinstance(s, dict)]
    bos = {"tahsis": {}, "bolum_kapsami": {}, "bosluklar": [],
           "snapshot": "", "kod": "", "neden": ""}
    if not liste:
        return {**bos, "kod": KOD_SHOT_FACT_YOK, "neden": "sahne yok"}
    if not havuz:
        return {**bos, "kod": KOD_GROUNDED_FACT_YOK,
                "neden": "kabul edilmis FactPacket YOK"}

    # ── SectionPlan: chapter sirasi KORUNUR ──
    bolum_sira, bolum_sahne = [], {}
    # ⚠ TEK KAYNAK: bolum/rol ORTAK projeksiyondan gelir (`yay_plani_kur`
    # ile AYNI). Ham `islev`/`bolum` da, kanonik alanlar da BURADA cozulur.
    _proj = yay_projeksiyonu(liste)
    belirsiz = [i for i, (c, _) in enumerate(_proj) if not c]
    if belirsiz:
        return {**bos, "kod": KOD_PROJEKSIYON_BELIRSIZ,
                "neden": (f"{len(belirsiz)} sahnede kanonik ve ham yay alani "
                          f"BIRLIKTE: {belirsiz[:6]}")}
    for i, s in enumerate(liste):
        cid = _proj[i][0]
        if cid not in bolum_sahne:
            bolum_sahne[cid] = []
            bolum_sira.append(cid)
        bolum_sahne[cid].append((i, s))

    tahsis, kapsam, bosluklar = {}, {}, []
    for cid in bolum_sira:
        kullanilan = []
        for idx, s in bolum_sahne[cid]:
            sid = str(s.get("scene_id") or f"s{idx + 1:03d}")
            metin, _kkod, _kneden = konusulan_alan(s)
            if _kkod:
                bosluklar.append({"sahne": sid, "kod": _kkod,
                                  "neden": _kneden})
                continue
            rol = _proj[idx][1]
            # ⚠ Onceden yazili kimlik DOGRULANMADAN kabul EDILMEZ
            # (`Y11B-PREFILLED-KABUL`): allowlist'te olmali VE entail etmeli.
            # ⚠ OLCULEN KUSUR (`Y11B2-PREFILL-NORMALIZE-BYPASS`, adversarial
            # denetim): `primary_fact_id or fact_id` FALLBACK'i uc kacaga
            # izin veriyordu — yalniz `primary_fact_id`, yalniz `fact_id`,
            # ve `primary=gecerli` + `fact_id=BOGUS`. Ucu de sessizce
            # NORMALIZE edilip final esitlik kapisini GECIYORDU. Girdide
            # HERHANGI bir prefill alani varsa IKISI DE zorunlu, BIREBIR
            # esit, allowlist'te ve entail eden olmalidir.
            _pid = str(s.get("primary_fact_id") or "").strip()
            _aid = str(s.get("fact_id") or "").strip()
            onceki = ""
            if _pid or _aid:
                if not _pid or not _aid or _pid != _aid:
                    bosluklar.append({
                        "sahne": sid, "kod": KOD_SHOT_FACT_YOK,
                        "neden": (f"prefill eksik/uyusmaz: "
                                  f"primary_fact_id={_pid!r} "
                                  f"fact_id={_aid!r}")})
                    continue
                onceki = _pid
                if onceki not in izin:
                    bosluklar.append({
                        "sahne": sid, "kod": KOD_SHOT_FACT_ALLOWLIST_DISI,
                        "neden": f"prefilled {onceki!r} allowlist disi"})
                    continue
            # ⚠ Sonuc/kapanis YENI fact GETIREMEZ — bolumde gecen fact'lerle
            # sinirli. ⚠ OLCULEN KUSUR (`Y11B2-ILK-SAHNE-CLOSING`, mid-WIP
            # denetim): chapter'in ILK sahnesi closing ise `kullanilan` BOS
            # oldugu icin kapi atlaniyor ve kapanis sahnesi YEPYENI bir fact
            # ALIYORDU. Kapanis yeni fact getiremez: fail-closed RED.
            if rol in SONUC_ROLLERI and not kullanilan:
                bosluklar.append({"sahne": sid, "kod": KOD_SHOT_FACT_YOK,
                                  "neden": "chapter ILK sahnesi closing: "
                                           "yeni fact getiremez"})
                continue
            aday = ([f for f in havuz if f in set(kullanilan)]
                    if rol in SONUC_ROLLERI else list(havuz))
            if onceki:
                aday = [onceki] if onceki in aday else []
            en_iyi, en_puan = "", -1.0
            for fid in aday:
                d = entail_dogrula(metin, paket_ile[fid])
                if not d.get("gecti"):
                    continue
                puan = float(d.get("ortusme") or 0.0)
                if puan > en_puan:          # esitlikte alfabetik ILK kazanir
                    en_iyi, en_puan = fid, puan
            if not en_iyi:
                # ⚠ UYDURMA fact_id YOK: entail edilemeyen sahne kimlik ALMAZ.
                bosluklar.append({"sahne": sid, "kod": KOD_ENTAIL_ILGISIZ,
                                  "neden": "hicbir allowlist fact'i sahneyi "
                                           "entail etmiyor"})
                continue
            tahsis[sid] = en_iyi
            kullanilan.append(en_iyi)
        kapsam[cid] = len(set(kullanilan))
    snap = hashlib.sha256(
        "|".join(f"{k}={tahsis[k]}" for k in sorted(tahsis)).encode()
    ).hexdigest()[:16]
    kod, neden = "", ""
    if bosluklar:
        kod = str(bosluklar[0].get("kod") or KOD_SHOT_FACT_YOK)
        neden = f"{len(bosluklar)} sahne tahsis edilemedi: {bosluklar[:3]}"
    return {"tahsis": tahsis, "bolum_kapsami": kapsam,
            "bosluklar": bosluklar, "snapshot": snap,
            "kod": kod, "neden": neden}


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
        # ⚠ OLCULEN KUSUR (`Y11B2-FACT-ID-FALLBACK`, final denetim):
        # `primary_fact_id or fact_id` FALLBACK'i, birincil alani BOS olan
        # bir shot'un ikincil alanla gecmesine izin veriyordu. Iki alan da
        # ZORUNLU ve BIREBIR AYNI olmalidir; aksi halde hangi kimligin
        # otorite oldugu BELIRSIZDIR.
        pid = str(s.get("primary_fact_id") or "").strip()
        aid = str(s.get("fact_id") or "").strip()
        sid = str(s.get("scene_id") or f"#{i + 1}")
        if not pid or not aid or pid != aid:
            bos.append(sid)
            continue
        fid = pid
        if fid not in izin:
            disi.append(f"{sid}:{fid}")
        else:
            kullanilan.append(fid)
    hedef = len(liste)
    bagli = len(kullanilan)
    kapsam = round(bagli / hedef, 4) if hedef else 0.0
    kod, neden = "", ""
    # ⚠ OLCULEN KUSUR (`Y11B2-BOS-SHOT-PASS`, mid-WIP denetim): shot listesi
    # BOSKEN `hedef=0` olup hicbir kod uretilmiyordu -> "0 shot denetlendi"
    # PASS sayiliyordu. OLCULEMEDI GECTI DEGILDIR.
    if not liste:
        kod, neden = KOD_SHOT_FACT_YOK, "denetlenecek shot YOK (bos liste)"
    elif disi:
        kod, neden = (KOD_SHOT_FACT_ALLOWLIST_DISI,
                      f"allowlist disi fact_id: {disi[:6]}")
    elif bos:
        kod, neden = KOD_SHOT_FACT_YOK, f"fact_id tasimayan shot: {bos[:6]}"
    return {"hedef": hedef, "bagli": bagli, "kapsam": kapsam,
            "benzersiz_fact": len(set(kullanilan)),
            "bos": bos, "allowlist_disi": disi,
            "kod": kod, "neden": neden}


def strict_grounded_mi(mod, edit_id) -> bool:
    """STRICT (fail-closed) grounded sozlesmesi BU IS icin gecerli mi?

    ⚠ SAF: ag/dosya/env/rastgelelik YOK; yalnizca iki degerin fonksiyonu.
    TEK KURAL: mod grounded UYGUN (`GROUNDED_MODLAR`) **VE** edit profili
    ACIKCA arastirma sozu veren bir profil (`STRICT_EDIT_PROFILLERI`).
    Digerleri BEST-EFFORT'tur (`P0-STRICT-VARSAYILAN`).
    """
    return (str(mod or "").strip() in GROUNDED_MODLAR
            and str(edit_id or "").strip() in STRICT_EDIT_PROFILLERI)


def grounded_kapisi(*, mod: str, arastirma_calisti: bool,
                    arastirma_hatasi: str, allowlist,
                    cozulemeyen: int = 0, bolum_kapsami=None,
                    shot_raporu=None, edit_id: str = "") -> dict:
    """Grounded belgesel FAIL-CLOSED kapisi.

    ⚠ `Y11B-GROUNDED-FAIL-OPEN`: eski kapi `if _olgular:` blogunun
    ICINDEYDI — arastirma kapali/hatali/0 olgu ise HIC KOSMUYOR ve is
    kullanici metniyle SESSIZCE devam ediyordu.
    ⚠ Grounded OLMAYAN yaratici modlar KAPSAM DISIDIR: davranislari
    DEGISMEZ (`gecti=True, kapsam_disi=True`).
    ⚠ P0 (`Y11B2-STRICT-VARSAYILAN`): STRICT olmayan belgesel de KAPSAM
    DISIDIR — `edit_id` ACIKCA bir strict profil degilse kapi PASS verir
    ve karar best-effort akisa birakilir. Kapsam ICINDEKI sozlesme
    MADDELERI DEGISMEDI.
    """
    if not strict_grounded_mi(mod, edit_id):
        return {"gecti": True, "kapsam_disi": True, "kod": "",
                "neden": (f"mod={mod!r} edit={edit_id!r} STRICT grounded "
                          f"degil")}
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
    # ⚠ OLCULEN KUSUR (`Y11B2-SHOT-RAPORU-YOK`, mid-WIP denetim): kapi
    # TUM-SHOT denetimi HIC KOSMADAN da PASS verebiliyordu. "Olculemedi"
    # GECTI demek DEGILDIR: shot raporu YOKSA ya da bir shot fact
    # tasimiyorsa kapi FAIL-CLOSED durur.
    if not isinstance(shot_raporu, dict) or not shot_raporu:
        return {"gecti": False, "kapsam_disi": False,
                "kod": KOD_SHOT_RAPORU_YOK,
                "neden": "tum-shot fact denetimi KOSMADI (rapor yok)"}
    if str(shot_raporu.get("kod") or ""):
        return {"gecti": False, "kapsam_disi": False,
                "kod": str(shot_raporu["kod"]),
                "neden": str(shot_raporu.get("neden") or "")[:160]}
    _hedef = int(shot_raporu.get("hedef") or 0)
    if _hedef <= 0 or int(shot_raporu.get("bagli") or 0) != _hedef:
        return {"gecti": False, "kapsam_disi": False,
                "kod": KOD_SHOT_FACT_YOK,
                "neden": (f"tum shot kapsanmadi: "
                          f"{shot_raporu.get('bagli')}/{_hedef}")}
    return {"gecti": True, "kapsam_disi": False, "kod": "", "neden": ""}


# ── ENTAILMENT: EN DAR GUVENLI SOZLESME (EXTRACTIVE) ──
# ⚠ OLCULEN KUSUR (`Y11B2-HEURISTIK-SONSUZ`, kirmizi takim final denetimi):
# Y-11b-2 tahsis kapisi bir SEZGISEL KURAL YIGINIYDI — polarite kelime/ek
# listeleri, baglac ayiricilari, cue kumeleri, retorik istisnalari,
# kapsam esikleri. Her tur denetim YENI bir kacak buldu ve her seferinde
# listeye bir madde daha eklendi:
#   · `or` / `after` / `before` ile olumsuzluk yer degistirmesi
#   · Turkce `-miyor` simdiki zaman olumsuzu
#   · cue'nun FACT ICINDE de gecmesiyle self-exemption ("rumor")
#   · `may have` / `reportedly` / `unverified` / `guya`
#   · NOKTALAMASIZ soru ("did the agency record 76941 cases")
#   · desteklenmemis YENI YUKLEM
#   · sayi BUYUKLUK degisimi (39.4 -> 394; 76,941 -> 769.41)
#   · komedi/ironi kaynakli yanlis negatifler
# Bu enumerasyon SONSUZDUR: dogal dil ustunde sezgisel bir kapi, kapali
# bir kume degildir. Karar: sezgisel kod ARTIK OTORITE DEGIL ve
# BIRAKILMADI (olu karmasiklik yok). Yerine Y-11b-1'in EXACT-SUPPORT
# sozlesmesiyle TUTARLI, EN DAR guvenli kural konuldu:
#
#   Yetkili fact tasiyan KONUSULAN alan, FactPacket'in KANONIK onermesi
#   (`onerme` == `exact_quote`, Y-11b-1 TAM ESITLIK sozlesmesi) ile
#   NORMALIZE EDILMIS bicimde BIREBIR AYNI olmadan `fact_id` TAHSIS
#   EDILMEZ.
#
# Normalizasyon YALNIZCA bosluk/buyuk-kucuk harf/duz tirnaktir
# (`factpacket.normalize`); icerik DEGISTIRILMEZ. Ek olgusal ya da
# retorik yantumce, modal, cue, soru, paraphrase, sayi bicim/buyukluk
# degisimi -> hepsi TEK ve STABIL kodla fail-closed.
#
# ⚠ KAPSAM SINIRI (handoff'ta da yazili): SERBEST PARAPHRASE ve NLI bu
# atomda DESTEKLENMIYOR. Planlayici, fact cumlesini SAHNE METNINE
# BIREBIR KOPYALAMAK zorundadir; bir shotta BIR kanonik fact.
def kanonik_onerme(paket) -> str:
    """Paketin KANONIK onermesi — normalize edilmis tek dogru metin.

    ⚠ Y-11b-1 support sozlesmesi geregi `onerme` ile `exact_quote`
    normalize edilmis bicimde AYNIDIR; ikisi ayrisirsa paket zaten
    allowlist'e GIREMEZ.
    """
    return _fp_uyum.normalize(str(getattr(paket, "onerme", "") or ""))


def entail_dogrula(metin: str, paket) -> dict:
    """Konusulan metin, yetkili fact'in KANONIK onermesi MI?

    ⚠ EXTRACTIVE SOZLESME: normalize edilmis BIREBIR ESITLIK disinda
    HICBIR SEY kabul edilmez (`Y11B2-HEURISTIK-SONSUZ`). Sezgisel
    polarite/baglam/kapsam olcumleri OTORITE DEGILDIR ve KALDIRILMISTIR.
    """
    m = _fp_uyum.normalize(str(metin or ""))
    kanonik = kanonik_onerme(paket)
    alinti = _fp_uyum.normalize(str(getattr(paket, "exact_quote", "") or ""))
    if not m or not kanonik:
        return {"gecti": False, "kod": KOD_ENTAIL_EXTRACTIVE_DEGIL,
                "ortusme": 0.0, "yeni_sayi": [], "yeni_yil": [],
                "neden": "konusulan metin ya da kanonik onerme BOS"}
    if m != kanonik and m != alinti:
        return {"gecti": False, "kod": KOD_ENTAIL_EXTRACTIVE_DEGIL,
                "ortusme": 0.0, "yeni_sayi": [], "yeni_yil": [],
                "neden": ("konusulan metin kanonik onerme ile BIREBIR AYNI "
                          "DEGIL (paraphrase/ek/modal/soru/sayi bicimi "
                          "DESTEKLENMIYOR)")}
    return {"gecti": True, "kod": "", "ortusme": 1.0,
            "yeni_sayi": [], "yeni_yil": []}
