#!/usr/bin/env python3
"""OTOMATIK GIRDI ANALIZI — kullanici yalnizca metin + stil versin, gerisini
sistem OLCULEBILIR GEREKCEYLE secsin.

⚠ NEDEN VAR (Faz H): wizard kullaniciyi 22 alanla karsiliyor ve sure/ses/
gorsel strateji/edit profilini ELLE sectiriyordu. Kullanicinin hedefi net:
"Kullanici yalnizca metin + stil secsin; sistem sure/ses/gorsel strateji/
edit profilini olculebilir gerekceyle otomatik secsin."

⚠ TASARIM KURALLARI
1. KULLANICININ ACIK SECIMI HER ZAMAN KAZANIR. Bu modul yalnizca BOS
   birakilan alanlari doldurur ve neyi doldurdugunu RAPORLAR.
2. UYDURMA PUAN YOK. Her karar SAYILABILIR bir olcume dayanir (kelime
   sayisi, yil gecisi, ozel ad sayisi, anahtar kelime isabeti). "Kalite
   puani %87" gibi uydurma metrik URETILMEZ.
3. LLM CAGRISI YOK. Tamamen deterministik ve UCRETSIZ. Analiz icin para
   harcamak, asil urettigi degerden pahali olurdu.
4. EMIN DEGILSEN VARSAYILANA DUS. Sinyal zayifsa "belirsiz" der ve
   varsayilani kullanir; zorla bir tur secmez.
"""
from __future__ import annotations

import os
import re

# Olculen TTS hizi (pipeline `veri/ses_hizi.json` ile kendini kalibre ediyor;
# burada yalnizca SURE TAHMINI icin taban deger kullaniliyor)
VARSAYILAN_WPM = float(os.environ.get("ANALIZ_WPM", "160"))
# Konu mu tam metin mi: bu kelime sayisinin ustu "tam metin" sayilir.
# ⚠ Esik keyfi degil: `/api/generate` en az 20 KARAKTER istiyor ve tipik bir
# "konu" bir-iki cumle (< 60 kelime). 60+ kelime yazan kullanici zaten
# anlatim metni yapistiriyor demektir.
TAM_METIN_ESIGI = int(os.environ.get("ANALIZ_TAM_METIN_ESIGI", "60"))

# ─────────────────────── TUR SINYALLERI ───────────────────────
# Her tur icin AYIRT EDICI kelimeler. Puan = kac tanesi gecti (sayilabilir).
TUR_SINYALI = {
    "belgesel": ("tarih", "history", "expedition", "sefer", "savaş", "war",
                 "keşif", "discovery", "arşiv", "archive", "gerçek hikaye",
                 "true story", "yüzyıl", "century", "olayı", "felaket",
                 "disaster", "biyografi", "biography", "belgesel"),
    "seyahat": ("gezi", "travel", "şehir turu", "city tour", "gezilecek",
                "destination", "rota", "itinerary", "otel", "plaj", "beach",
                "manzara", "landscape", "seyahat", "tatil", "vacation"),
    "aciklayici": ("nasıl", "how to", "nedir", "what is", "adım adım",
                   "step by step", "açıklama", "explained", "rehber",
                   "guide", "öğren", "learn", "çalışır", "works", "neden",
                   "why", "fark", "difference"),
    "urun": ("ürün", "product", "satın al", "buy", "fiyat", "price",
             "özellik", "feature", "inceleme", "review", "kampanya",
             "indirim", "marka", "brand", "müşteri", "customer"),
    "hikaye": ("hikaye", "story", "karakter", "character", "roman", "novel",
               "masal", "kurgu", "fiction", "hayal", "bir varmış",
               "once upon"),
}

# Belgesel/seyahat -> gercek goruntu; hikaye -> AI gorsel serbest
GORSEL_STRATEJISI = {
    "belgesel": ("gercek-footage", "Belgeselde yapay görsel üretilmez; "
                 "yalnızca gerçek arşiv/stok görüntüsü kullanılır."),
    "seyahat": ("gercek-footage", "Seyahat içeriği gerçek mekân görüntüsü "
                "ister; yapay görsel mekânı yanlış temsil eder."),
    "aciklayici": ("karma", "Açıklayıcı içerikte grafik/şema ile gerçek "
                   "görüntü birlikte kullanılır."),
    "urun": ("karma", "Ürün içeriğinde gerçek çekim tercih edilir."),
    "hikaye": ("ai-gorsel", "Kurgu anlatıda yapay görsel serbesttir."),
}

# Tur -> pipeline `tur` alani (uretim hattinin bildigi 3 deger)
PIPELINE_TURU = {
    "belgesel": "documentary", "seyahat": "documentary",
    "aciklayici": "documentary", "urun": "documentary",
    "hikaye": "hikaye",
}

# ─────────────────────── DIL TESPITI ───────────────────────
# Turkce'ye OZGU karakterler + cok sik islevsel kelimeler. Deterministik.
_TR_HARF = set("çğıöşüÇĞİÖŞÜ")
TR_KELIME = frozenset((
    "ve", "bir", "bu", "için", "ile", "de", "da", "ama", "çok", "daha",
    "sonra", "gibi", "kadar", "olarak", "her", "ne", "var", "yok", "olan"))
EN_KELIME = frozenset((
    "the", "and", "of", "to", "in", "is", "that", "for", "with", "was",
    "on", "as", "by", "at", "from", "this", "it", "are"))

_YIL = re.compile(r"\b(1[0-9]{3}|20[0-9]{2})\b")
_OZEL_AD = re.compile(r"\b([A-ZĞÜŞİÖÇ][a-zğüşıöç]{2,}(?:\s+[A-ZĞÜŞİÖÇ][a-zğüşıöç]{2,})*)\b")
_SAYI = re.compile(r"\b\d[\d.,]*\b")

# Risk isaretleri — kullaniciya UYARI olarak gosterilir, uretim ENGELLENMEZ
RISK_ISARETI = {
    "saglik": ("tedavi", "ilaç", "hastalık", "kanser", "aşı", "teşhis",
               "treatment", "cure", "diagnosis", "vaccine", "symptom"),
    "finans": ("yatırım", "hisse", "kripto", "borsa", "kazanç garantisi",
               "invest", "stock", "crypto", "trading", "profit guaranteed"),
    "siyaset": ("seçim", "parti", "cumhurbaşkanı", "election", "president",
                "government", "protest", "siyasi"),
    "kisisel": ("cinayet", "taciz", "istismar", "intihar", "murder",
                "abuse", "suicide", "harassment"),
}


def _kelimeler(metin: str) -> list:
    return re.findall(r"[A-Za-zÀ-ÿĞÜŞİÖÇğüşıöç]+", str(metin or ""))


def dil_tespit(metin: str) -> tuple:
    """(dil_kodu, gerekce). Sayilabilir: TR harf sayisi + islevsel kelime."""
    kel = [k.lower() for k in _kelimeler(metin)]
    if not kel:
        return "", "metin bos"
    tr_harf = sum(1 for c in str(metin) if c in _TR_HARF)
    tr = sum(1 for k in kel if k in TR_KELIME)
    en = sum(1 for k in kel if k in EN_KELIME)
    if tr_harf >= 3 or tr > en:
        return "tr", f"TR harf {tr_harf}, TR islevsel kelime {tr} vs EN {en}"
    if en > tr:
        return "en", f"EN islevsel kelime {en} vs TR {tr}"
    return "", f"belirsiz (TR {tr}, EN {en}, TR harf {tr_harf})"


def girdi_turu(metin: str) -> tuple:
    """(konu|tam-metin, kelime_sayisi, gerekce)."""
    n = len(_kelimeler(metin))
    if n >= TAM_METIN_ESIGI:
        return "tam-metin", n, (f"{n} kelime >= {TAM_METIN_ESIGI} esigi — "
                                f"hazir anlatim metni sayildi")
    return "konu", n, (f"{n} kelime < {TAM_METIN_ESIGI} esigi — konu basligi "
                       f"sayildi, anlatim uretilecek")


def tur_tespit(metin: str) -> tuple:
    """(tur, puanlar, gerekce). Sinyal yoksa 'belirsiz'."""
    d = " " + str(metin or "").lower() + " "
    puan = {t: sum(1 for k in kelimeler if k in d)
            for t, kelimeler in TUR_SINYALI.items()}
    en_iyi = max(puan, key=lambda t: puan[t])
    if puan[en_iyi] == 0:
        return "belirsiz", puan, "hicbir tur sinyali bulunamadi"
    # Beraberlik varsa belirsiz say — zorla secme
    berabere = [t for t, p in puan.items() if p == puan[en_iyi]]
    if len(berabere) > 1:
        return "belirsiz", puan, f"beraberlik: {berabere} ({puan[en_iyi]} isaret)"
    return en_iyi, puan, f"{en_iyi}: {puan[en_iyi]} isaret (digerleri {puan})"


def varlik_cikar(metin: str) -> dict:
    """Yil / ozel ad / sayi — hepsi SAYILABILIR, hicbiri LLM'den degil."""
    m = str(metin or "")
    yillar = sorted(set(int(y) for y in _YIL.findall(m)))
    # Cumle basi buyuk harfleri elemek icin: en az 2 kez gecen ya da coklu
    # kelimeli ozel adlar daha guvenilir.
    ham = _OZEL_AD.findall(m)
    sayim: dict = {}
    for a in ham:
        sayim[a] = sayim.get(a, 0) + 1
    adlar = [a for a, n in sorted(sayim.items(), key=lambda x: -x[1])
             if n >= 2 or " " in a][:12]
    return {"yillar": yillar,
            "donem": ("tarihsel" if yillar and min(yillar) < 1990
                      else "guncel" if yillar else "belirsiz"),
            "ozel_adlar": adlar,
            "sayi_adedi": len(_SAYI.findall(m))}


def risk_tara(metin: str) -> list:
    d = " " + str(metin or "").lower() + " "
    return [{"tur": t, "isaret": [k for k in kelimeler if k in d][:4]}
            for t, kelimeler in RISK_ISARETI.items()
            if any(k in d for k in kelimeler)]


def sure_oner(metin: str, girdi_tur: str, kelime: int) -> tuple:
    """Hedef sure (dk) + gerekce. Tam metinde OLCUM, konuda varsayilan."""
    if girdi_tur == "tam-metin":
        dk = max(0.5, round(kelime / VARSAYILAN_WPM, 1))
        return dk, (f"{kelime} kelime / {VARSAYILAN_WPM:.0f} kelime-dk "
                    f"= {dk} dk (metnin GERCEK uzunlugu)")
    return 2.0, "konu verildi; anlatim uretilecek — varsayilan 2 dk"


def analiz(metin: str, *, kullanici_secimi: dict = None) -> dict:
    """Tam analiz + otomatik secimler.

    `kullanici_secimi`: {"tur":..., "sure_dk":..., "ses":..., "edit":...}
    Dolu olan HER alan KORUNUR; yalnizca bos olanlar doldurulur.
    """
    secim = {k: v for k, v in (kullanici_secimi or {}).items()
             if v not in (None, "", [])}
    dil, dil_gerekce = dil_tespit(metin)
    gtur, kelime, gtur_gerekce = girdi_turu(metin)
    tur, tur_puan, tur_gerekce = tur_tespit(metin)
    varliklar = varlik_cikar(metin)
    riskler = risk_tara(metin)
    sure, sure_gerekce = sure_oner(metin, gtur, kelime)

    strateji, strateji_gerekce = GORSEL_STRATEJISI.get(
        tur, ("gercek-footage", "Tür belirlenemedi; en güvenli strateji "
              "gerçek görüntü."))

    otomatik: dict = {}
    korunan: dict = {}

    def _ata(alan, deger, gerekce):
        if alan in secim:
            korunan[alan] = {"deger": secim[alan],
                             "not": "kullanıcının açık seçimi korundu"}
        else:
            otomatik[alan] = {"deger": deger, "gerekce": gerekce}

    _ata("tur", PIPELINE_TURU.get(tur, "documentary"),
         f"içerik türü '{tur}' — {tur_gerekce}")
    _ata("sure_dk", sure, sure_gerekce)
    _ata("gorsel_strateji", strateji, strateji_gerekce)
    _ata("dil", dil or "tr", dil_gerekce)

    return {
        "girdi_turu": gtur,
        "kelime_sayisi": kelime,
        "dil": dil,
        "icerik_turu": tur,
        "tur_puanlari": tur_puan,
        "varliklar": varliklar,
        "riskler": riskler,
        "otomatik_secimler": otomatik,
        "korunan_secimler": korunan,
        "gerekceler": {
            "girdi_turu": gtur_gerekce,
            "dil": dil_gerekce,
            "icerik_turu": tur_gerekce,
            "sure": sure_gerekce,
            "gorsel_strateji": strateji_gerekce,
        },
    }
