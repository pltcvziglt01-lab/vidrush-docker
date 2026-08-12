#!/usr/bin/env python3
"""REFERANS VIDEO STIL PARMAK IZI — SOZLESME ve GUVENLI ANALIZ KAPISI (Faz I-4).

⚠ BU ADIMDA NE YAPILMIYOR: tam vision modeli, ucretli analiz, kare okuma.
Burada YALNIZCA (a) surumlu/genisletilebilir OZELLIK SOZLESMESI, (b) kaynak
kimligi/provenance, (c) ornekleme plani ve (d) GUVENLI KAPI var. Gercek olcum
`olcum_fn` ile DISARIDAN enjekte edilir; verilmezse modul uydurma uretmez,
`OLCULMEDI` der.

⚠ TASARIM KURALLARI

1. KAYNAK VIDEO KOPYALANMAZ. Cikti SOYUT ISTATISTIKtir: ritim, cekim uzunlugu
   dagilimi, gecis yogunlugu, tipografi DAVRANISI, renk/kontrast egilimi,
   kamera hareketi, ses ritmi. `YASAK_ALAN` tablosundaki hicbir sey (kisi
   kimligi, marka/logo, ozgun metin, sahne kopyasi, muzik kopyasi) URETILMEZ
   ve sozlesmeye yazilamaz — `dogrula()` bunu REDDEDER.

2. UYDURMA PARMAK IZI YOK. Video yoksa, bozuksa, provenance/lisans eksikse ya
   da butce kapandiysa `bos_parmak()` doner: `durum="OLCULMEDI"` ve gorunur
   gerekce. Sessizce "olctuk" denmez.

3. OLCULEMEYEN ALAN GIZLENMEZ. Her alan `kaynak` tasir:
   `olculdu | varsayilan | olculemedi`. Fallback degeri kullanildiysa bu
   ACIKCA yazilir; guven 0.0 olur.

4. BUTCE ZORUNLU. `ParmakButce(None, ...)` -> ValueError. Sinirsiz butce
   yasak (Faz H/I kurali, `KareButce` ile ayni ruh).

5. CEKIRDEK KOD DEGISMEDEN GENISLER. Yeni ozellik = `OZELLIK_SEMASI`ya bir
   satir. Yeni surum = `SEMA_SURUM` + `arsivle()`.

6. AG YOK. Bu modulde hicbir ag cagrisi bulunmaz (testle kilitli).
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import stat
import threading
import time

SEMA_SURUM = "1.0.0"

# ═══════════════════════ YASAK ALANLAR (sozlesmenin kalbi) ═══════════════════════
# ⚠ Bunlar "yapmamaya calisiriz" degil, SOZLESME IHLALIdir. `dogrula()` bu
# anahtarlardan birini tasiyan parmak izini reddeder; `yasak_denetle()` ic ice
# sozluklerde de arar. Amac: referans videodan STIL ogrenmek, ICERIK CALMAK degil.
YASAK_ALAN = {
    "kisi_kimligi": "Kisi tanima/eslestirme, yuz imzasi, isim cikarimi",
    "yuz_bicimi": "Yuz geometrisi, biyometrik olcum",
    "marka_logo": "Marka adi, logo sablonu, ticari isaret cikarimi",
    "ozgun_metin": "Ekrandaki ozgun yazi/altyazi/senaryo metninin kopyasi",
    "sahne_kopyasi": "Sahne sirasinin/kompozisyonunun birebir kopyasi",
    "kare_verisi": "Ham kare, thumbnail, piksel dizisi, gomulu goruntu",
    "ses_kopyasi": "Ses/muzik ornegi, melodi imzasi, konusma dokumu",
    "seslendirme_klonu": "Konusmaci ses klonlama icin ozellik",
}

# Yasak ic-anahtar arama kaliplari (alt sozluklerde de taranir).
_YASAK_IZ = tuple(YASAK_ALAN)

# ═══════════════════════ OZELLIK SEMASI (7 boyut) ═══════════════════════
# Her alan: (tip, birim, varsayilan_fallback, aciklama)
# ⚠ YENI OZELLIK EKLEMEK: buraya bir satir. Cekirdek kod DEGISMEZ.
OZELLIK_SEMASI = {
    # ── 1. KURGU RITMI ──
    "ritim": {
        "kesme_dk": (float, "kesme/dakika", 8.0, "Dakikada ortalama kesme"),
        "tempo_sinifi": (str, "", "orta", "yavas|orta|hizli"),
        "ritim_duzenliligi": (float, "0-1", 0.5,
                              "Kesme araliklarinin duzenliligi (1=metronom)"),
    },
    # ── 2. CEKIM UZUNLUGU DAGILIMI ──
    "cekim": {
        "medyan_sn": (float, "sn", 5.0, "Medyan cekim suresi"),
        "ortalama_sn": (float, "sn", 6.0, "Ortalama cekim suresi"),
        "p90_sn": (float, "sn", 12.0, "Cekimlerin %90'i bu surenin altinda"),
        "kisa_pay_pct": (float, "%", 25.0, "2 sn altindaki cekimlerin payi"),
        "uzun_pay_pct": (float, "%", 15.0, "10 sn ustundeki cekimlerin payi"),
        "dagilim_sinifi": (str, "", "tek-modlu", "tek-modlu|cift-modlu"),
    },
    # ── 3. GECIS YOGUNLUGU / TURU ──
    "gecis": {
        "gecisli_pay_pct": (float, "%", 20.0, "Yumusak gecisli kesme orani"),
        "baskin_tur": (str, "", "hard-cut", "hard-cut|crossfade|karartma|whip"),
        "ortalama_sure_sn": (float, "sn", 0.4, "Gecislerin ortalama suresi"),
    },
    # ── 4. TIPOGRAFI DAVRANISI (metnin KENDISI DEGIL) ──
    # ⚠ Burada yalnizca DAVRANIS olculur: yazi ne siklikta gorunuyor, ekranin
    # neresinde duruyor, ne kadar kaliyor. Yazinin ICERIGI `ozgun_metin`
    # yasagina girer ve URETILMEZ.
    "tipografi": {
        "yazi_kapsama_pct": (float, "%", 30.0, "Yazi goruenen kare orani"),
        "konum_egilimi": (str, "", "alt", "ust|orta|alt|karisik"),
        "ortalama_kalis_sn": (float, "sn", 2.5, "Yazinin ekranda kalma suresi"),
        "hareket_sinifi": (str, "", "sabit", "sabit|yumusak|kinetik"),
        "guvenli_alan_pct": (float, "%", 88.0, "Yazinin kaldigi guvenli alan"),
    },
    # ── 5. RENK / KONTRAST ──
    "renk": {
        "parlaklik_ort": (float, "0-1", 0.45, "Ortalama parlaklik"),
        "kontrast_sinifi": (str, "", "orta", "dusuk|orta|yuksek"),
        "doygunluk_sinifi": (str, "", "orta", "dusuk|orta|yuksek"),
        "sicaklik_egilimi": (str, "", "notr", "soguk|notr|sicak"),
        "koyu_kare_pay_pct": (float, "%", 30.0, "Koyu karelerin payi"),
    },
    # ── 6. KAMERA HAREKETI ──
    "kamera": {
        "hareket_yogunlugu": (float, "0-100", 35.0, "Kare-ici hareket miktari"),
        "baskin_hareket": (str, "", "sabit",
                           "sabit|ken-burns|push-in|handheld|drone"),
        "sabit_kare_pay_pct": (float, "%", 45.0, "Hareketsiz karelerin payi"),
    },
    # ── 7. SES RITMI / DUCKING ──
    "ses": {
        "konusma_yogunluk_pct": (float, "%", 65.0, "Konusma iceren sure orani"),
        "sessizlik_pay_pct": (float, "%", 8.0, "Sessiz bosluk orani"),
        "muzik_var": (bool, "", False, "Altta surekli muzik yatagi var mi"),
        "ducking_db": (float, "dB", -8.0, "Konusmada muzigin kisilma miktari"),
        "ritim_hizalanmasi": (float, "0-1", 0.3,
                              "Kesmelerin ses vurusuna hizalanmasi"),
    },
}

BOYUTLAR = tuple(OZELLIK_SEMASI)

# Alan kaynagi — her alan bunlardan BIRINI tasimak ZORUNDA.
KAYNAK_DEGERLERI = ("olculdu", "varsayilan", "olculemedi")

# Kapinin verebilecegi DURDURMA nedenleri (sessiz gecis yok).
DURDURMA_NEDENI = {
    "VIDEO-YOK": "Referans video verilmedi",
    "DOSYA-YOK": "Dosya bulunamadi",
    "DOSYA-TURU": "Duz dosya degil (dizin/aygit/baglanti)",
    "YOL-GUVENSIZ": "Yol izinli kok disinda ya da gecis (traversal) iceriyor",
    "BOYUT-ASIMI": "Dosya butce siniri ustunde",
    "BOZUK-MEDYA": "Medya okunamadi ya da video akisi yok",
    "SURE-ASIMI": "Video suresi butce siniri ustunde",
    "SURE-YETERSIZ": "Video anlamli istatistik icin cok kisa",
    "PROVENANCE-EKSIK": "Kaynak beyani eksik",
    "LISANS-EKSIK": "Kullanim hakki beyani eksik ya da tanimsiz",
    "BUTCE": "Analiz butcesi kapali",
    "ARAC-YOK": "Olcum araci yok",
}

# Kabul edilen lisans/hak beyanlari. "bilinmiyor" KABUL EDILMEZ.
GECERLI_LISANS = ("sahibiyim", "izinli", "cc0", "cc-by", "cc-by-sa",
                  "public-domain")

# Sadece stil ogrenmek icin kullanilabilecegi ACIKCA beyan edilmis olmali.
GECERLI_KAYNAK_TURU = ("yukleme", "kendi-arsivim", "lisansli-arsiv")


# ═══════════════════════ BUTCE ═══════════════════════

class ParmakButce:
    """Kare / duvar saati / USD tavani. UCU DE ZORUNLU.

    ⚠ `None` gecmek YASAK — sinirsiz butce bu depoda yasaklandi
    (`arastirma.butce`, `medya.kare_kapisi.KareButce` ile ayni kural).
    Sifir gecmek kapiyi KAPATIR, sinirsiz yapmaz.

    ⚠ THREAD GUVENLI: kontrol ve harcama tek kilit altinda (`yer_ayir`).
    """

    def __init__(self, maks_kare: int = 40, maks_sn: float = 60.0,
                 maks_usd: float = 0.0, maks_bayt: int = 512 * 1024 * 1024,
                 maks_sure_sn: float = 1800.0, saat=None):
        if (maks_kare is None or maks_sn is None or maks_usd is None
                or maks_bayt is None or maks_sure_sn is None):
            raise ValueError("ParmakButce: sinirsiz butce yasak — sayi ver")
        if min(float(maks_kare), float(maks_sn), float(maks_usd),
               float(maks_bayt), float(maks_sure_sn)) < 0:
            raise ValueError("ParmakButce: negatif tavan olamaz")
        self.maks_kare = int(maks_kare)
        self.maks_sn = float(maks_sn)
        self.maks_usd = float(maks_usd)
        self.maks_bayt = int(maks_bayt)
        self.maks_sure_sn = float(maks_sure_sn)
        self._saat = saat or time.monotonic
        self._kilit = threading.Lock()
        self.baslangic = self._saat()
        self.kare = 0
        self.usd = 0.0
        self.engel = []

    def _uygun_mu(self, birim_usd: float):
        if self.kare >= self.maks_kare:
            return False, f"kare tavani doldu ({self.kare}/{self.maks_kare})"
        if self.usd + birim_usd > self.maks_usd:
            return False, (f"USD tavani doldu "
                           f"(${self.usd:.4f}+${birim_usd:.4f}/${self.maks_usd:.4f})")
        gecen = self._saat() - self.baslangic
        if gecen >= self.maks_sn:
            return False, f"sure tavani doldu ({gecen:.1f}/{self.maks_sn:.0f} sn)"
        return True, "butce uygun"

    def uygun_mu(self, birim_usd: float = 0.0):
        with self._kilit:
            return self._uygun_mu(float(birim_usd))

    def yer_ayir(self, birim_usd: float = 0.0):
        """Kontrol + harcama TEK kilit altinda (kontrol-sonra-harca yarisi yok)."""
        with self._kilit:
            ok, neden = self._uygun_mu(float(birim_usd))
            if ok:
                self.kare += 1
                self.usd = round(self.usd + float(birim_usd), 6)
            elif len(self.engel) < 20:
                self.engel.append(neden)
            return ok, neden

    def engelle(self, neden: str) -> None:
        with self._kilit:
            if len(self.engel) < 20:
                self.engel.append(neden)

    def ozet(self) -> dict:
        with self._kilit:
            return {"kare": self.kare, "maks_kare": self.maks_kare,
                    "usd": round(self.usd, 6), "maks_usd": self.maks_usd,
                    "gecen_sn": round(self._saat() - self.baslangic, 2),
                    "maks_sn": self.maks_sn, "maks_bayt": self.maks_bayt,
                    "maks_sure_sn": self.maks_sure_sn,
                    "engel": list(self.engel)}


def varsayilan_butce() -> ParmakButce:
    """Env ile ayarlanabilir varsayilan. ⚠ `maks_usd` VARSAYILAN 0.0 —
    yani bu adimda UCRETLI cagriya yer ayrilmaz; acmak ACIK karardir."""
    return ParmakButce(
        maks_kare=int(os.environ.get("REF_MAKS_KARE", "40")),
        maks_sn=float(os.environ.get("REF_MAKS_SN", "60")),
        maks_usd=float(os.environ.get("REF_MAKS_USD", "0")),
        maks_bayt=int(os.environ.get("REF_MAKS_BAYT", str(512 * 1024 * 1024))),
        maks_sure_sn=float(os.environ.get("REF_MAKS_SURE_SN", "1800")))


# ═══════════════════════ KAYNAK KIMLIGI / PROVENANCE ═══════════════════════

# Anlamli istatistik icin gereken en kisa sure.
ASGARI_SURE_SN = float(os.environ.get("REF_ASGARI_SURE_SN", "10"))
_HASH_PARCA = 1024 * 1024


def dosya_ozeti(yol: str, maks_bayt: int) -> dict:
    """sha256 + boyut. Butce ustundeyse HASH ALINMAZ (buyuk dosya okumayiz).

    ⚠ Hash KIMLIK icindir, icerik saklamak icin degil: parmak izi kaydinda
    yalnizca ozet durur, videonun kendisi DEGIL.
    """
    boyut = os.path.getsize(yol)
    if boyut > maks_bayt:
        return {"bayt": boyut, "sha256": "", "hash_alindi": False}
    h = hashlib.sha256()
    with open(yol, "rb") as f:
        while True:
            parca = f.read(_HASH_PARCA)
            if not parca:
                break
            h.update(parca)
    return {"bayt": boyut, "sha256": h.hexdigest(), "hash_alindi": True}


def yol_guvenli_mi(yol: str, izinli_kok: str = None) -> tuple:
    """(ok, neden). Traversal ve izinli-kok disi yollari REDDEDER.

    ⚠ `os.path.realpath` ile sembolik baglanti da cozulur; aksi halde izinli
    dizindeki bir symlink kok disini okuturdu.
    """
    if not yol or not str(yol).strip():
        return False, "VIDEO-YOK"
    ham = str(yol)
    if "\x00" in ham:
        return False, "YOL-GUVENSIZ"
    tam = os.path.realpath(os.path.abspath(ham))
    if izinli_kok:
        kok = os.path.realpath(os.path.abspath(izinli_kok))
        if tam != kok and not tam.startswith(kok + os.sep):
            return False, "YOL-GUVENSIZ"
    return True, ""


def medya_probe_komutu(yol: str) -> list:
    """ffprobe komutu. UCRETSIZ ve YEREL; vision/model cagrisi DEGIL."""
    return ["ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries",
            "stream=width,height,r_frame_rate,codec_name,nb_frames",
            "-show_entries", "format=duration,size,format_name",
            "-of", "json", yol]


def probe_ayikla(stdout: str) -> dict:
    """ffprobe JSON -> {genislik, yukseklik, fps, codec, sure_sn, bicim}."""
    try:
        d = json.loads(stdout or "{}")
    except (json.JSONDecodeError, TypeError):
        return {}
    akislar = d.get("streams") or []
    akis = akislar[0] if akislar else {}
    bicim = d.get("format") or {}
    fps = 0.0
    ham = str(akis.get("r_frame_rate") or "")
    if "/" in ham:
        try:
            a, b = ham.split("/")
            fps = round(float(a) / float(b), 3) if float(b) else 0.0
        except (ValueError, ZeroDivisionError):
            fps = 0.0
    try:
        sure = float(bicim.get("duration") or 0)
    except (TypeError, ValueError):
        sure = 0.0
    return {"genislik": int(akis.get("width") or 0),
            "yukseklik": int(akis.get("height") or 0),
            "fps": fps,
            "codec": str(akis.get("codec_name") or ""),
            "sure_sn": round(sure, 3),
            "bicim": str(bicim.get("format_name") or "")}


def provenance_dogrula(beyan: dict) -> tuple:
    """(ok, neden). Kaynak ve lisans beyani ZORUNLU; 'bilinmiyor' kabul EDILMEZ."""
    b = beyan or {}
    kaynak = str(b.get("kaynak_turu") or "").strip().lower()
    lisans = str(b.get("lisans") or "").strip().lower()
    if kaynak not in GECERLI_KAYNAK_TURU:
        return False, "PROVENANCE-EKSIK"
    if lisans not in GECERLI_LISANS:
        return False, "LISANS-EKSIK"
    if not b.get("stil_izni", False):
        # Kullanici "bu videodan yalnizca STIL ogrenilmesine izin veriyorum"
        # demeden analiz baslamaz. Sessiz varsayim yok.
        return False, "LISANS-EKSIK"
    return True, ""


# ═══════════════════════ ORNEKLEME PLANI ═══════════════════════

def ornekleme_plani(sure_sn: float, butce: ParmakButce,
                    kenar_pay: float = 0.02) -> dict:
    """Hangi saniyeler orneklenecek? DETERMINISTIK — rastgelelik YOK.

    ⚠ Rastgele ornekleme ayni videoda iki farkli parmak izi uretirdi ve
    "tekrar uretilebilir" iddiasi karsiliksiz kalirdi. Plan yalnizca sureye
    ve butceye baglidir.

    Kenarlardan `kenar_pay` kadar kirpilir: acilis logosu ve kapanis jenerigi
    stilin kendisi degildir, istatistigi bozar.
    """
    sure = max(0.0, float(sure_sn or 0))
    adet = max(0, int(butce.maks_kare))
    if sure <= 0 or adet == 0:
        return {"adet": 0, "saniyeler": [], "aralik_sn": 0.0,
                "kirpma_sn": 0.0, "gerekce": "sure ya da kare butcesi sifir"}
    kirpma = round(sure * float(kenar_pay), 3)
    bas, son = kirpma, max(kirpma, sure - kirpma)
    etkin = max(0.0, son - bas)
    if adet == 1:
        sn = [round(bas + etkin / 2, 3)]
    else:
        adim = etkin / (adet - 1) if adet > 1 else 0.0
        sn = [round(bas + i * adim, 3) for i in range(adet)]
    return {"adet": len(sn), "saniyeler": sn,
            "aralik_sn": round(etkin / max(1, adet - 1), 3) if adet > 1 else 0.0,
            "kirpma_sn": kirpma,
            "gerekce": (f"{len(sn)} kare, {bas:.2f}-{son:.2f} sn arasi esit "
                        f"aralikli (deterministik)")}


# ═══════════════════════ GUVENLI KAPI ═══════════════════════

def kapi(yol: str, *, beyan: dict = None, butce: ParmakButce = None,
         izinli_kok: str = None, probe_fn=None, arac_var: bool = True) -> dict:
    """Analiz baslasin mi? KONTROLLU DUR — uydurma parmak izi URETMEZ.

    Donus: {"acik": bool, "neden": kod, "aciklama": ..., "medya": {...},
            "kimlik": {...}, "plan": {...}}

    `probe_fn(komut) -> stdout` enjekte edilebilir; verilmezse ve `arac_var`
    False ise ARAC-YOK ile durur. Bu fonksiyon AG CAGIRMAZ.
    """
    butce = butce or varsayilan_butce()

    def dur(kod, ek=None):
        d = {"acik": False, "neden": kod,
             "aciklama": DURDURMA_NEDENI.get(kod, kod),
             "medya": {}, "kimlik": {}, "plan": {}}
        if ek:
            d.update(ek)
        butce.engelle(f"{kod}: {d['aciklama']}")
        return d

    ok, neden = yol_guvenli_mi(yol, izinli_kok)
    if not ok:
        return dur(neden)
    tam = os.path.realpath(os.path.abspath(str(yol)))
    if not os.path.exists(tam):
        return dur("DOSYA-YOK")
    try:
        durum = os.stat(tam)
    except OSError:
        return dur("DOSYA-YOK")
    if not stat.S_ISREG(durum.st_mode):
        return dur("DOSYA-TURU")
    if durum.st_size <= 0:
        return dur("BOZUK-MEDYA")
    if durum.st_size > butce.maks_bayt:
        return dur("BOYUT-ASIMI")

    p_ok, p_neden = provenance_dogrula(beyan)
    if not p_ok:
        return dur(p_neden)

    b_ok, b_neden = butce.uygun_mu(0.0)
    if not b_ok:
        return dur("BUTCE", {"aciklama": b_neden})

    if probe_fn is None and not arac_var:
        return dur("ARAC-YOK")
    try:
        ham = probe_fn(medya_probe_komutu(tam)) if probe_fn else ""
    except Exception as e:                     # olcum araci COKERTMEZ
        return dur("BOZUK-MEDYA", {"aciklama": f"probe hatasi: "
                                               f"{type(e).__name__}"})
    medya = probe_ayikla(ham)
    if not medya or not medya.get("genislik") or not medya.get("yukseklik"):
        return dur("BOZUK-MEDYA")
    if medya["sure_sn"] <= 0:
        return dur("BOZUK-MEDYA")
    if medya["sure_sn"] > butce.maks_sure_sn:
        return dur("SURE-ASIMI")
    if medya["sure_sn"] < ASGARI_SURE_SN:
        return dur("SURE-YETERSIZ")

    kimlik = dosya_ozeti(tam, butce.maks_bayt)
    kimlik["ad"] = os.path.basename(tam)
    kimlik["kaynak_turu"] = str((beyan or {}).get("kaynak_turu") or "")
    kimlik["lisans"] = str((beyan or {}).get("lisans") or "")
    return {"acik": True, "neden": "", "aciklama": "kapi acik",
            "medya": medya, "kimlik": kimlik,
            "plan": ornekleme_plani(medya["sure_sn"], butce)}


# ═══════════════════════ PARMAK IZI KURULUMU ═══════════════════════

def _alan(deger, kaynak, guven, kanit):
    return {"deger": deger, "kaynak": kaynak, "guven": round(float(guven), 3),
            "kanit": str(kanit)}


def bos_parmak(neden: str, aciklama: str = "") -> dict:
    """OLCULMEDI parmak izi — her alan fallback, guven 0, sebep GORUNUR.

    ⚠ Bu fonksiyon "basarisiz" degil "durust" ciktidir: cagiran taraf
    varsayilanla devam edebilir ama olcum yapildigini SANMAZ.
    """
    ozellik = {}
    for boyut, alanlar in OZELLIK_SEMASI.items():
        ozellik[boyut] = {
            ad: _alan(fb, "olculemedi", 0.0, f"olculmedi: {neden}")
            for ad, (_t, _b, fb, _a) in alanlar.items()}
    return {
        "sema_surum": SEMA_SURUM,
        "durum": "OLCULMEDI",
        "neden": neden,
        "aciklama": aciklama or DURDURMA_NEDENI.get(neden, neden),
        "kimlik": {}, "medya": {}, "plan": {},
        "ozellik": ozellik,
        "olculen_alan": 0,
        "toplam_alan": sum(len(a) for a in OZELLIK_SEMASI.values()),
        "guven": 0.0,
        "yasak_beyani": sorted(YASAK_ALAN),
        "butce": {},
    }


def parmak_kur(kapi_sonucu: dict, olcumler: dict = None,
               butce: ParmakButce = None) -> dict:
    """Olculen degerlerden parmak izi kur. `olcumler` YOKSA uydurma YOK.

    `olcumler`: {boyut: {alan: (deger, guven, kanit)}} — disaridan enjekte
    edilir (bu adimda gercek olcum motoru YAZILMADI, sozlesme yazildi).

    Semada olup olculmeyen her alan `varsayilan` kaynagiyla ve guven 0.0 ile
    doldurulur; hangi alanin olculdugu `olculen_alan` sayisiyla GORUNURDUR.
    """
    if not kapi_sonucu or not kapi_sonucu.get("acik"):
        neden = (kapi_sonucu or {}).get("neden") or "VIDEO-YOK"
        p = bos_parmak(neden, (kapi_sonucu or {}).get("aciklama", ""))
        if butce:
            p["butce"] = butce.ozet()
        return p

    olcumler = olcumler if isinstance(olcumler, dict) else {}
    ozellik, olculen = {}, 0
    guvenler = []
    for boyut, alanlar in OZELLIK_SEMASI.items():
        ozellik[boyut] = {}
        gelen = olcumler.get(boyut) if isinstance(olcumler.get(boyut), dict) else {}
        for ad, (tip, _birim, fallback, _acik) in alanlar.items():
            ham = gelen.get(ad)
            deger, guven, kanit = None, 0.0, ""
            if isinstance(ham, (tuple, list)) and len(ham) >= 1:
                deger = ham[0]
                guven = float(ham[1]) if len(ham) > 1 else 0.5
                kanit = str(ham[2]) if len(ham) > 2 else "olculdu"
            elif ham is not None:
                deger, guven, kanit = ham, 0.5, "olculdu"
            if deger is None or not _tip_uygun(deger, tip):
                ozellik[boyut][ad] = _alan(
                    fallback, "varsayilan", 0.0,
                    "olcum gelmedi; sema varsayilani kullanildi")
                continue
            guven = max(0.0, min(1.0, guven))
            ozellik[boyut][ad] = _alan(deger, "olculdu", guven,
                                       kanit or "olculdu")
            olculen += 1
            guvenler.append(guven)

    toplam = sum(len(a) for a in OZELLIK_SEMASI.values())
    return {
        "sema_surum": SEMA_SURUM,
        "durum": "OLCULDU" if olculen else "OLCULMEDI",
        "neden": "" if olculen else "ARAC-YOK",
        "aciklama": ("" if olculen else
                     "kapi acildi ama hicbir alan olculmedi"),
        "kimlik": dict(kapi_sonucu.get("kimlik") or {}),
        "medya": dict(kapi_sonucu.get("medya") or {}),
        "plan": dict(kapi_sonucu.get("plan") or {}),
        "ozellik": ozellik,
        "olculen_alan": olculen,
        "toplam_alan": toplam,
        "guven": round(sum(guvenler) / len(guvenler), 3) if guvenler else 0.0,
        "yasak_beyani": sorted(YASAK_ALAN),
        "butce": butce.ozet() if butce else {},
    }


def _tip_uygun(deger, tip) -> bool:
    if tip is bool:
        return isinstance(deger, bool)
    if tip is float:
        return isinstance(deger, (int, float)) and not isinstance(deger, bool)
    if tip is str:
        return isinstance(deger, str) and bool(deger.strip())
    return False


# ═══════════════════════ DOGRULAMA / YASAK DENETIMI ═══════════════════════

def yasak_denetle(veri, _derinlik: int = 0) -> list:
    """Ic ice sozluk/listede YASAK alan izi ara. Bulunanlarin listesi doner.

    ⚠ Yalnizca anahtar adina bakmaz; uzun ham metin (or. altyazi dokumu) ya da
    base64/veri-URI gibi ICERIK TASIYAN degerler de ihlaldir.
    """
    bulunan = []
    if _derinlik > 8:
        return bulunan
    if isinstance(veri, dict):
        for k, v in veri.items():
            ad = str(k).lower()
            for iz in _YASAK_IZ:
                if iz in ad:
                    bulunan.append(f"yasak alan: {k}")
            bulunan.extend(yasak_denetle(v, _derinlik + 1))
    elif isinstance(veri, (list, tuple)):
        for v in veri:
            bulunan.extend(yasak_denetle(v, _derinlik + 1))
    elif isinstance(veri, str):
        d = veri.strip().lower()
        if d.startswith("data:") or d.startswith("base64,"):
            bulunan.append("gomulu veri (data/base64) tasinamaz")
        elif len(veri) > 400:
            bulunan.append(f"asiri uzun metin ({len(veri)} karakter) — "
                           f"ozgun icerik kopyasi olabilir")
    elif isinstance(veri, (bytes, bytearray)):
        bulunan.append("ham ikili veri tasinamaz")
    return bulunan


def dogrula(parmak: dict) -> list:
    """Parmak izini semaya gore dogrula. Donus: hata listesi (bos = gecerli).

    ⚠ FAZLA ALAN DA HATADIR: sessiz yazim yanlisi kaydin yarisini devre disi
    birakirdi (`stil_profili.dogrula` ile ayni kural).
    """
    hata = []
    if not isinstance(parmak, dict):
        return ["parmak izi sozluk degil"]
    for zorunlu in ("sema_surum", "durum", "ozellik", "olculen_alan",
                    "toplam_alan", "yasak_beyani"):
        if zorunlu not in parmak:
            hata.append(f"eksik ust alan: {zorunlu}")
    if parmak.get("durum") not in ("OLCULDU", "OLCULMEDI"):
        hata.append(f"gecersiz durum: {parmak.get('durum')!r}")
    if str(parmak.get("sema_surum", "")).split(".")[0] != SEMA_SURUM.split(".")[0]:
        hata.append(f"sema surumu uyumsuz: {parmak.get('sema_surum')!r}")

    # ⚠ Yasak alan denetimi — sozlesmenin en sert kurali.
    for iz in yasak_denetle({k: v for k, v in parmak.items()
                             if k != "yasak_beyani"}):
        hata.append(f"SOZLESME IHLALI — {iz}")

    ozellik = parmak.get("ozellik")
    if not isinstance(ozellik, dict):
        return hata + ["ozellik bloku yok"]
    fazla_boyut = set(ozellik) - set(OZELLIK_SEMASI)
    if fazla_boyut:
        hata.append(f"bilinmeyen boyut: {sorted(fazla_boyut)}")
    for boyut, alanlar in OZELLIK_SEMASI.items():
        blok = ozellik.get(boyut)
        if not isinstance(blok, dict):
            hata.append(f"eksik boyut: {boyut}")
            continue
        fazla = set(blok) - set(alanlar)
        if fazla:
            hata.append(f"{boyut}: bilinmeyen alan {sorted(fazla)}")
        for ad, (tip, _birim, _fb, _acik) in alanlar.items():
            v = blok.get(ad)
            if not isinstance(v, dict):
                hata.append(f"{boyut}.{ad} eksik")
                continue
            if v.get("kaynak") not in KAYNAK_DEGERLERI:
                hata.append(f"{boyut}.{ad} kaynak gecersiz: {v.get('kaynak')!r}")
            if not _tip_uygun(v.get("deger"), tip):
                hata.append(f"{boyut}.{ad} tip uyusmuyor: {v.get('deger')!r}")
            g = v.get("guven")
            if not isinstance(g, (int, float)) or not 0.0 <= float(g) <= 1.0:
                hata.append(f"{boyut}.{ad} guven araligi disi: {g!r}")
            if v.get("kaynak") != "olculdu" and float(g or 0) != 0.0:
                hata.append(f"{boyut}.{ad} olculmedigi halde guven > 0")
    return hata


# ═══════════════════════ SURUM ARSIVI ═══════════════════════

ARSIV = {}


def arsivle(kimlik: str, parmak: dict) -> tuple:
    """Parmak izini (kimlik, sema_surum) anahtariyla dondur.

    ⚠ Sema degistirilmeden ONCE cagrilmali; aksi halde eski referansla
    uretilmis is TEKRAR URETILEMEZ.
    """
    anahtar = (str(kimlik), str(parmak.get("sema_surum") or SEMA_SURUM))
    ARSIV[anahtar] = copy.deepcopy(parmak)
    return anahtar


def arsivden_al(kimlik: str, surum: str) -> dict:
    """Kayitli surumu AYNEN getir. Yoksa SESSIZCE baskasi DONMEZ -> KeyError."""
    return copy.deepcopy(ARSIV[(str(kimlik), str(surum))])


def kapsam_ozeti() -> dict:
    """Sozlesmenin GERCEK kapsami — 'her stili olcebiliyoruz' iddiasi yok."""
    return {
        "sema_surum": SEMA_SURUM,
        "boyut": len(OZELLIK_SEMASI),
        "alan": sum(len(a) for a in OZELLIK_SEMASI.values()),
        "yasak_alan": len(YASAK_ALAN),
        "durdurma_nedeni": len(DURDURMA_NEDENI),
        "lisans": len(GECERLI_LISANS),
        "kaynak_turu": len(GECERLI_KAYNAK_TURU),
        "arsiv": len(ARSIV),
    }
