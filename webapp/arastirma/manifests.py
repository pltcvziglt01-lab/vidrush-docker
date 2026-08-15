"""ARASTIRMA ve MEDYA manifest veri modeli.

Bu modul BILEREK iki ayri manifest tanimliyor ve aralarina duvar koyuyor:

    research_manifest.json   -> IDDIALAR ve onlarin KAYNAKLARI (metin/bilgi)
    asset_manifest.json      -> KULLANILAN MEDYA ve onlarin LISANSLARI

Bu ayrim kozmetik degil, TELIF GUVENLIGIDIR. Bir haber sayfasini kaynak
gostermek o sayfadaki fotografi kullanma hakki VERMEZ. Kod duzeyinde
`MedyaVarligi.olustur()` bir arastirma kaynagindan gelen URL'yi reddeder
(bkz. ARASTIRMA_ALANI kontrolu) — yani bu hata "dikkat edilmesi gereken
bir sey" olmaktan cikip yapilamaz hale gelir.

Ikinci degismez kural: LISANS BELIRSIZSE MEDYA KULLANILMAZ. `lisans` alani
bos/None/"unknown" ise `kullanilabilir` False doner ve atlanabilir bayrak yoktur.
"Kaynak yazmak" izin anlamina gelmez (11 Agu 2026'da kullaniciya bu ayrim
acikca anlatildi: atif CC lisansinin SARTI, telifli icerigin CAREsi degil).

Disa bagimlilik yok — saf stdlib. Boylece testler agsiz kosar.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, field
from typing import Optional

SEMA_SURUM = "1.0"


class ManifestHatasi(ValueError):
    """Zorunlu alan eksik / deger gecersiz."""


class TelifIhlaliHatasi(ManifestHatasi):
    """Arastirma kaynagindan medya turetilmeye calisildi ya da lisans belirsiz."""


# ─────────────────────────── KAYNAK TURLERI ───────────────────────────
# Puanlama source_ranker.py'da; burada sadece gecerli degerler tanimli.
KAYNAK_TURLERI = (
    "resmi-kurum",      # bakanlik, istatistik ofisi, merkez bankasi, polis teskilati
    "akademik",         # dergi makalesi, universite yayini, tez
    "birincil-belge",   # kanun metni, mahkeme karari, arsiv belgesi, sirket raporu
    "haber-buyuk",      # Reuters/AP/BBC/NHK gibi kurumsal haber
    "haber-yerel",      # yerel/kucuk haber sitesi
    "kurulus",          # STK, meslek odasi, vakif
    "muze-arsiv",       # muze, kutuphane, ulusal arsiv
    "ansiklopedi",      # Wikipedia vb. — YONLENDIRICI, kanit degil
    "blog",             # kisisel/ticari blog
    "forum",            # forum, sosyal medya
    "bilinmiyor",
)

# Bu turler TEK BASINA kritik bir iddiayi dogrulayamaz.
ZAYIF_TURLER = frozenset({"ansiklopedi", "blog", "forum", "bilinmiyor"})

# Iddianin guven durumlari
GUVEN_DURUMLARI = ("dogrulandi", "tek-kaynak", "celiskili", "cozulmedi")

# ─────────────────────────── LISANSLAR ───────────────────────────
# Sadece BURADA yazan lisanslar kullanilabilir. Yeni lisans eklemek bilincli
# bir karar olmali; "belki uygundur" diye gecmemeli.
LISANS_KURALLARI = {
    # anahtar: (ticari_izin, degistirme_izni, atif_gerekli)
    "cc0":            (True, True, False),
    "public-domain":  (True, True, False),
    "pdm":            (True, True, False),   # Public Domain Mark
    "cc-by":          (True, True, True),
    "cc-by-sa":       (True, True, True),    # DIKKAT: turev ayni lisansla paylasilmali
    "nasa-public":    (True, True, True),    # telifsiz ama logo/isim onayi ayri
    "pexels":         (True, True, False),   # kendi lisansi; atif zorunlu degil
    "pixabay":        (True, True, False),
    "coverr":         (True, True, False),
    "kullanici-sahip": (True, True, False),  # kullanicinin kendi cektigi/haklari
}
# Kasten DISARIDA BIRAKILANLAR ve sebepleri:
#   cc-by-nc / cc-by-nc-sa / cc-by-nc-nd -> TICARI kullanim yok, YouTube monetize edilirse ihlal
#   cc-by-nd / cc-by-sa-nd               -> turev/degistirme yok, kurgu zaten degistirmedir
#   "editorial-only", "rights-managed"   -> belgesel kullanimi ayri lisans ister
#   "unknown", "", None                  -> belirsiz; kullanilamaz
YASAK_LISANS_ISARETLERI = ("-nc", "-nd", "editorial", "rights-managed", "royalty-free-limited")


def lisans_normalize(ham: Optional[str]) -> str:
    """Saglayicilarin farkli yazimlarini tek anahtara indirger.
    Taninmayan her sey "unknown" -> kullanilamaz.

    ⚠ Ilk surumde regex ile "cc" onekini normalize etmeye calistim ve "cc0"
    girdisini "cc-0"a cevirip TANINMAZ hale getirdim (test yakaladi: gecerli bir
    kamu malı lisansi "belirsiz" sayilip medya reddediliyordu). Artik acik
    esleme tablosu var — sihir yok.
    """
    if not ham:
        return "unknown"
    d = str(ham).strip().lower().replace("_", "-").replace(" ", "-")
    d = re.sub(r"-(\d+\.\d+|\d\.\d|\d+)$", "", d)      # surum sonekini at: cc-by-4.0 -> cc-by
    esler = {
        "cc0": "cc0", "cc-0": "cc0", "cc-zero": "cc0", "creativecommons-zero": "cc0",
        "publicdomain": "public-domain", "public-domain": "public-domain",
        "pd": "public-domain", "pd-us": "public-domain",
        "public-domain-mark": "pdm", "pdm": "pdm",
        "cc-by": "cc-by", "by": "cc-by",
        "cc-by-sa": "cc-by-sa", "by-sa": "cc-by-sa",
        "nasa": "nasa-public", "nasa-public": "nasa-public",
        "pexels": "pexels", "pixabay": "pixabay", "coverr": "coverr",
        "kullanici-sahip": "kullanici-sahip",
        # HANGI CC oldugu belirsiz -> kullanilamaz
        "creative-commons": "unknown", "cc": "unknown",
    }
    return esler.get(d, "unknown")


def lisans_kullanilabilir(ham: Optional[str]) -> tuple[bool, str]:
    """(kullanilabilir, sebep). Belirsiz lisans HER ZAMAN False."""
    ad = lisans_normalize(ham)
    if ad == "unknown":
        return False, f"lisans belirsiz ({str(ham)[:40] or 'bos'})"
    for isaret in YASAK_LISANS_ISARETLERI:
        if isaret in str(ham).lower():
            return False, f"lisans kisitli ({isaret})"
    if ad not in LISANS_KURALLARI:
        return False, f"lisans listede yok ({ad})"
    return True, ad


# ─────────────────────── ARASTIRMA MANIFESTI ───────────────────────

@dataclass
class Kaynak:
    """Bir iddiayi destekleyen TEK bir kaynak."""
    url: str
    baslik: str
    tur: str = "bilinmiyor"
    yayin_tarihi: str = ""          # ISO 8601 ya da bos
    erisim_tarihi: str = ""         # ISO 8601 — cagiran verir (Date.now yasak degil ama disardan)
    birincil: bool = False
    alinti: str = ""                # sayfadan dogrudan alinan cumle (dogrulama izi)

    def dogrula(self) -> None:
        if not str(self.url).startswith(("http://", "https://")):
            raise ManifestHatasi(f"Kaynak.url gecersiz: {self.url!r}")
        if not str(self.baslik).strip():
            raise ManifestHatasi("Kaynak.baslik bos olamaz")
        if self.tur not in KAYNAK_TURLERI:
            raise ManifestHatasi(f"Kaynak.tur taninmiyor: {self.tur!r}")
        if not str(self.erisim_tarihi).strip():
            raise ManifestHatasi("Kaynak.erisim_tarihi zorunlu (izlenebilirlik)")

    @property
    def alan(self) -> str:
        m = re.match(r"https?://([^/]+)", self.url or "")
        return (m.group(1).lower().removeprefix("www.") if m else "")


@dataclass
class Iddia:
    """Senaryoya girebilecek TEK bir olgusal iddia."""
    fact_id: str
    metin: str                                  # iddianin kendisi, tek cumle
    kaynaklar: list = field(default_factory=list)   # list[Kaynak]
    guven: str = "cozulmedi"
    kritik: bool = False                        # tarih/rakam/isim gibi kesinlik gerektiren
    celiski_notu: str = ""
    kategori: str = ""                          # tarih | rakam | isim | cografya | siralama | alinti | teknik

    def dogrula(self) -> None:
        # ⚠ FAZ Y-11: iki bicim gecerli.
        #   `f001`            — eski SIRALI sayac (claim-first hat)
        #   `f<16 hex>`       — CONTENT-ADDRESSED FactPacket kimligi
        # Content-addressed bicim `arastirma.factpacket.fact_id_uret` ile
        # (onerme, exact_quote, source_id) uclusunden turer; boylece bir
        # cekimin tasidigi fact_id BENZERLIKTEN TAHMIN EDILEMEZ, yalnizca
        # gercekten uretilmis bir paketle eslesir.
        if not re.fullmatch(r"f([0-9]{3,}|[0-9a-f]{16})", self.fact_id or ""):
            raise ManifestHatasi(
                f"fact_id 'f001' ya da 'f<16 hex>' biciminde olmali: "
                f"{self.fact_id!r}")
        if not str(self.metin).strip():
            raise ManifestHatasi(f"{self.fact_id}: metin bos")
        if self.guven not in GUVEN_DURUMLARI:
            raise ManifestHatasi(f"{self.fact_id}: guven taninmiyor: {self.guven!r}")
        for k in self.kaynaklar:
            k.dogrula()

    @property
    def bagimsiz_kaynak_sayisi(self) -> int:
        """AYNI alan adindan iki link = TEK kaynak. Bir haberin baska sitede
        yeniden yayinlanmasi bagimsiz dogrulama degildir."""
        alanlar = {k.alan for k in self.kaynaklar if k.alan}
        return len(alanlar)

    @property
    def senaryoya_girebilir(self) -> bool:
        """Kritik iddia icin: birincil kaynak VEYA iki bagimsiz kaynak sart.
        Zayif turler (ansiklopedi/blog/forum) tek basina yeterli degil."""
        if self.guven in ("celiskili", "cozulmedi"):
            return False
        if not self.kritik:
            return bool(self.kaynaklar)
        guclu = [k for k in self.kaynaklar if k.tur not in ZAYIF_TURLER]
        if any(k.birincil for k in guclu):
            return True
        return len({k.alan for k in guclu if k.alan}) >= 2


@dataclass
class ArastirmaManifesti:
    konu: str
    iddialar: list = field(default_factory=list)     # list[Iddia]
    olusturma: str = ""
    sema: str = SEMA_SURUM
    arama_sorgulari: list = field(default_factory=list)
    notlar: list = field(default_factory=list)

    def dogrula(self) -> None:
        if not str(self.konu).strip():
            raise ManifestHatasi("ArastirmaManifesti.konu bos")
        gorulen = set()
        for i in self.iddialar:
            i.dogrula()
            if i.fact_id in gorulen:
                raise ManifestHatasi(f"fact_id tekrar ediyor: {i.fact_id}")
            gorulen.add(i.fact_id)

    @property
    def arastirma_url_kumesi(self) -> set:
        """MEDYA bu kumeden TURETILEMEZ (bkz. MedyaVarligi.olustur)."""
        return {k.url for i in self.iddialar for k in i.kaynaklar}

    def kullanilabilir_iddialar(self) -> list:
        return [i for i in self.iddialar if i.senaryoya_girebilir]

    def yaz(self, yol: str) -> None:
        self.dogrula()
        _json_yaz(yol, {
            "sema": self.sema, "konu": self.konu, "olusturma": self.olusturma,
            "arama_sorgulari": self.arama_sorgulari, "notlar": self.notlar,
            "ozet": {
                "iddia": len(self.iddialar),
                "kullanilabilir": len(self.kullanilabilir_iddialar()),
                "kritik": sum(1 for i in self.iddialar if i.kritik),
                "celiskili": sum(1 for i in self.iddialar if i.guven == "celiskili"),
            },
            "iddialar": [asdict(i) for i in self.iddialar],
        })


# ─────────────────────── MEDYA (ASSET) MANIFESTI ───────────────────────

@dataclass
class MedyaVarligi:
    """Videoda KULLANILAN tek bir medya parcasi ve lisans kaydi."""
    asset_id: str
    tur: str                        # video | image
    orijinal_url: str               # medyanin bulundugu SAYFA
    indirme_url: str
    saglayici: str                  # wikimedia | archive_org | nasa | pexels | ...
    lisans: str
    eser_sahibi: str = ""
    lisans_url: str = ""
    atif_gerekli: bool = True
    ticari_izin: bool = False
    degistirme_izni: bool = False
    erisim_tarihi: str = ""
    fact_id: str = ""               # hangi anlatim satirina bagli
    anlatim_satiri: str = ""
    ulke: str = ""
    donem: str = ""
    baslik: str = ""
    genislik: int = 0
    yukseklik: int = 0
    sure_sn: float = 0.0
    secilen_aralik: tuple = (0.0, 0.0)
    vision_skoru: float = 0.0
    semantik_skoru: float = 0.0
    karar: str = "aday"             # aday | secildi | reddedildi
    karar_nedeni: str = ""
    yerel_yol: str = ""

    @property
    def kullanilabilir(self) -> bool:
        ok, _ = lisans_kullanilabilir(self.lisans)
        return ok and self.ticari_izin and self.degistirme_izni

    def dogrula(self) -> None:
        if not str(self.asset_id).strip():
            raise ManifestHatasi("asset_id bos")
        if self.tur not in ("video", "image"):
            raise ManifestHatasi(f"{self.asset_id}: tur video|image olmali ({self.tur!r})")
        for alan in ("orijinal_url", "indirme_url"):
            v = getattr(self, alan)
            if not str(v).startswith(("http://", "https://")):
                raise ManifestHatasi(f"{self.asset_id}: {alan} gecersiz ({v!r})")
        if not str(self.saglayici).strip():
            raise ManifestHatasi(f"{self.asset_id}: saglayici bos")
        if not str(self.erisim_tarihi).strip():
            raise ManifestHatasi(f"{self.asset_id}: erisim_tarihi zorunlu")
        ok, sebep = lisans_kullanilabilir(self.lisans)
        if not ok:
            raise TelifIhlaliHatasi(f"{self.asset_id}: {sebep}")
        if self.atif_gerekli and not str(self.eser_sahibi).strip():
            raise ManifestHatasi(
                f"{self.asset_id}: lisans atif istiyor ama eser_sahibi bos")

    @classmethod
    def olustur(cls, arastirma: Optional[ArastirmaManifesti] = None, **alanlar) -> "MedyaVarligi":
        """TEK giris kapisi. Iki seyi burada engelliyoruz:

        1) Medyanin ARASTIRMA kaynagindan turetilmesi. Bir haber sayfasini kaynak
           gostermek oradaki gorseli kullanma izni vermez; bu en kolay yapilan ve
           en pahali telif hatasi. Ayni URL hem kaynak hem medya olamaz.
        2) Lisansi belirsiz medyanin sisteme girmesi.
        """
        v = cls(**alanlar)
        if arastirma is not None:
            arastirma_urller = arastirma.arastirma_url_kumesi
            for alan in ("orijinal_url", "indirme_url"):
                if getattr(v, alan) in arastirma_urller:
                    raise TelifIhlaliHatasi(
                        f"{v.asset_id}: {alan} bir ARASTIRMA kaynagi "
                        f"({getattr(v, alan)[:60]}). Kaynak gostermek medya kullanma "
                        "izni degildir — medya lisansli bir medya saglayicisindan gelmeli.")
        # Lisans kurallari tek dogruluk kaynagi: cagiranin verdigi izinler EZILIR
        ad = lisans_normalize(v.lisans)
        if ad in LISANS_KURALLARI:
            tic, deg, atif = LISANS_KURALLARI[ad]
            v.ticari_izin, v.degistirme_izni, v.atif_gerekli = tic, deg, atif
        v.dogrula()
        return v


@dataclass
class MedyaManifesti:
    varliklar: list = field(default_factory=list)     # list[MedyaVarligi]
    sema: str = SEMA_SURUM
    olusturma: str = ""

    def ekle(self, v: MedyaVarligi) -> None:
        v.dogrula()
        if any(x.asset_id == v.asset_id for x in self.varliklar):
            raise ManifestHatasi(f"asset_id tekrar ediyor: {v.asset_id}")
        self.varliklar.append(v)

    def secilenler(self) -> list:
        return [v for v in self.varliklar if v.karar == "secildi"]

    def saglayici_dagilimi(self) -> dict:
        d = {}
        for v in self.secilenler():
            d[v.saglayici] = d.get(v.saglayici, 0) + 1
        return d

    def tek_saglayici_hakimiyeti(self, tavan: float = 0.6) -> Optional[str]:
        """Basari kriteri: tek saglayici toplam goruntulerin COGUNU olusturmamali.
        Asilirsa hakim saglayicinin adi doner."""
        sec = self.secilenler()
        if len(sec) < 4:
            return None
        d = self.saglayici_dagilimi()
        for ad, n in d.items():
            if n / len(sec) > tavan:
                return ad
        return None

    def atif_metni(self) -> str:
        """YouTube aciklamasina konacak atif blogu. Lisansin resmi atif yeri burasi."""
        satirlar, gorulen = [], set()
        for v in self.secilenler():
            if not v.atif_gerekli:
                continue
            anahtar = (v.eser_sahibi, v.orijinal_url)
            if anahtar in gorulen:
                continue
            gorulen.add(anahtar)
            lis = lisans_normalize(v.lisans).upper()
            satirlar.append(f"{v.baslik or 'Untitled'} — {v.eser_sahibi} "
                            f"({lis}) {v.orijinal_url}")
        return "\n".join(satirlar)

    def yaz(self, yol: str) -> None:
        for v in self.varliklar:
            v.dogrula()
        _json_yaz(yol, {
            "sema": self.sema, "olusturma": self.olusturma,
            "ozet": {
                "toplam": len(self.varliklar),
                "secildi": len(self.secilenler()),
                "saglayici_dagilimi": self.saglayici_dagilimi(),
                "hakim_saglayici": self.tek_saglayici_hakimiyeti(),
            },
            "atif_metni": self.atif_metni(),
            "varliklar": [asdict(v) for v in self.varliklar],
        })


def _json_yaz(yol: str, veri: dict) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(yol)) or ".", exist_ok=True)
    gecici = yol + ".tmp"
    with open(gecici, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=1)
    os.replace(gecici, yol)          # yarim dosya birakmaz
