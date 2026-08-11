"""TASARIM TOKEN'LARI ve EDIT PROFILI.

Neden token: 11 Agu ciktisinda her sahne kendi kararini veriyordu ve video
"sablon montaji" gibi duruyordu. Profesyonel belgesel hissi tek tek efektlerden
degil TUTARLILIKTAN geliyor — ayni font, ayni izgara, ayni easing, ayni gecis
ailesi. Bu dosya o tutarliligin tek dogruluk kaynagi.

Varsayilan profil "Premium Modern Documentary": koyu sinematik taban, kirik
beyaz tipografi, TEK vurgu rengi, temiz izgara, ince grain.

⚠ FONT GERCEGI (11 Agu 2026'da olcerek bulundu): repodaki
`Montserrat-Bold.ttf` DEGISKEN fonttu ve varsayilan agirligi 100 (Thin);
ffmpeg varsayilan ornegi cizdigi icin butun yazilar INCE cikiyordu. Statik
700 ornegi uretildi. Bu yuzden token'lar font DOSYA ADI degil, agirlik
NUMARASI tutuyor ve dogrulama fonksiyonu statik olup olmadigini kontrol ediyor.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# ── Referans olcumunden gelen sabitler (OLCUM_EDIT_TAKSONOMI.md) ──
# Bu degerler tahmin degil, 20 rakip videodan olculdu.
OLCULEN = {
    "sert_kesme_orani": 0.799,       # 786 kesme etiketlendi
    "karartma_orani": 0.076,
    "flash_orani": 0.041,
    "whip_orani": 0.033,
    "crossfade_orani": 0.022,
    "zoom_in_payi": 0.78,            # zoomlu cekimlerin %78'i in
    "zoom_hizi_medyan": 0.0157,      # %1.57/sn
    "zoom_tavani": 1.38,
    "durgun_kare_orani": 0.12,
    "cekim_medyani_sn": 6.5,
    "kisa_cekim_orani": 0.32,        # 4 sn altindaki cekimler
    "yazi_giris_sn": 0.28,           # %1.8'i yariyolda yakalandi -> <0.3 sn
    "alt_band_omru_sn": 4.7,
    "kucuk_etiket_omru_sn": 1.8,
    "yazili_kare_orani": 0.27,       # bimodal; profil bazli
    "grafiksiz_kare_orani": 0.84,
}

# ── EASING (AE Graph Editor karsiligi) ──
# Referans rampa olcumu (n=134): son/ilk = 1.03 -> kamera hareketi LINEERE YAKIN.
# Ilk surumde bezier(0.33,0,0.2,1) kullaniyordum; hareketin ~7 katini ilk
# ceyrege yiguyordu ve "yazilim zoom'u" gibi duruyordu.
EASING = {
    "kamera": (0.42, 0.32, 0.58, 0.68),      # olculen: lineere yakin
    "giris": (0.16, 1.00, 0.30, 1.00),       # yazi/grafik girisi: hizli cikis
    "cikis": (0.70, 0.00, 0.84, 0.00),
    "overshoot": (0.34, 1.56, 0.64, 1.00),   # settle'li; AE "overshoot" hissi
    "lineer": (0.00, 0.00, 1.00, 1.00),
}


@dataclass
class Tipografi:
    # EN FAZLA 2 aile / 3 agirlik (kullanici siniri)
    baslik_ailesi: str = "Montserrat"
    metin_ailesi: str = "Montserrat"
    agirliklar: tuple = (400, 600, 700)
    # ⚠ Bu fontlarin STATIK olmasi zorunlu (degisken font -> Thin cizilir)
    statik_zorunlu: bool = True
    # Punto olcegi (1080p taban)
    bolum_basligi: int = 60
    alt_band_baslik: int = 42
    alt_band_alt: int = 25
    callout: int = 30
    kaynak_etiketi: int = 21
    altyazi: int = 38
    # Izgara / guvenli alan
    izgara_x: int = 100
    guvenli_kenar: int = 64          # %5.9 — yayin guvenli alani
    maks_satir_karakter: int = 42
    min_gorunme_sn: float = 1.2      # bundan kisa yazi okunamaz
    # Kontrast: yazi zemine GUVENMEZ, arkasina bant konur
    bant_opaklik: float = 0.62
    bant_dolgu_orani: float = 0.42


@dataclass
class Renk:
    taban: str = "#0E1013"           # koyu sinematik taban
    yazi: str = "#F5F3EF"            # kirik beyaz
    vurgu: str = "#F5E14B"           # TEK vurgu rengi
    bant: str = "#000000"
    harita_kara: str = "#1C2026"
    harita_su: str = "#0A0D10"
    veri_cubuk: str = "#F5E14B"
    uyari: str = "#E2564D"


@dataclass
class Motion:
    grain: float = 0.35             # ince — "film dokusu", gorunur gurultu degil
    vignette: float = 0.45
    letterbox: bool = False
    grade: str = "notr-soguk"
    parallax_derinlik: tuple = (1.0, 0.62, 0.34)   # on / orta / arka katman hizi
    push_in_orani: float = 0.062    # sn basina %6.2 (olculen agresif kova)
    yumusak_zoom_orani: float = 0.014
    maks_es_zamanli_efekt: int = 3   # bundan fazlasi "efekt gosterisi"


@dataclass
class EditProfili:
    ad: str = "Premium Modern Documentary"
    tipografi: Tipografi = field(default_factory=Tipografi)
    renk: Renk = field(default_factory=Renk)
    motion: Motion = field(default_factory=Motion)
    fps: int = 30
    genislik: int = 1920
    yukseklik: int = 1080
    # Hedef cekim suresi araligi (kullanici siniri: 1.5-6 sn)
    shot_min_sn: float = 1.5
    shot_maks_sn: float = 6.0
    shot_kesin_tavan_sn: float = 8.0   # asilirsa gerekce ZORUNLU
    # Ses
    lufs_hedef: float = -14.0
    tepe_tavan_dbtp: float = -1.0
    # Gecis dagilimi olculen degerlerden
    gecis_dagilimi: dict = field(default_factory=lambda: {
        "hard-cut": OLCULEN["sert_kesme_orani"],
        "j-cut": 0.04, "l-cut": 0.04,
        "crossfade": OLCULEN["crossfade_orani"],
        "karartma": OLCULEN["karartma_orani"],
        "flash": OLCULEN["flash_orani"],
        "match-cut": 0.003, "whip": OLCULEN["whip_orani"],
    })

    def token_sozlugu(self) -> dict:
        return {"ad": self.ad, "fps": self.fps,
                "olcu": [self.genislik, self.yukseklik],
                "tipografi": self.tipografi.__dict__,
                "renk": self.renk.__dict__,
                "motion": self.motion.__dict__,
                "easing": {k: list(v) for k, v in EASING.items()},
                "shot": {"min": self.shot_min_sn, "maks": self.shot_maks_sn,
                         "kesin_tavan": self.shot_kesin_tavan_sn},
                "ses": {"lufs": self.lufs_hedef, "tepe": self.tepe_tavan_dbtp}}

    def dogrula(self) -> list:
        """Profil kendi kurallarini ihlal ediyor mu? Uyari listesi doner."""
        u = []
        aileler = {self.tipografi.baslik_ailesi, self.tipografi.metin_ailesi}
        if len(aileler) > 2:
            u.append(f"TIPO-AILE: {len(aileler)} font ailesi (tavan 2)")
        if len(self.tipografi.agirliklar) > 3:
            u.append(f"TIPO-AGIRLIK: {len(self.tipografi.agirliklar)} agirlik (tavan 3)")
        if self.shot_min_sn < 1.0:
            u.append("SHOT-MIN: 1 sn altinda cekim goz yorar")
        if self.shot_maks_sn > self.shot_kesin_tavan_sn:
            u.append("SHOT-TAVAN: hedef maks kesin tavani asiyor")
        if self.motion.maks_es_zamanli_efekt > 4:
            u.append("EFEKT-YOGUNLUK: 4'ten fazla es zamanli efekt")
        return u


VARSAYILAN = EditProfili()

# Alternatif profiller — sablonlar galerisi icin (ozgun adlar, marka adi yok)
PROFILLER = {
    "premium-modern": VARSAYILAN,
    "atlas-journey": EditProfili(
        ad="Atlas Journey",
        renk=Renk(vurgu="#7FD1C1"),
        motion=Motion(grain=0.22, vignette=0.32, push_in_orani=0.032),
        shot_min_sn=2.0, shot_maks_sn=6.5),
    "investigative-essay": EditProfili(
        ad="Investigative Essay",
        renk=Renk(taban="#0A0A0C", vurgu="#E2564D"),
        motion=Motion(grain=0.5, vignette=0.6, grade="soguk-kontrast"),
        shot_min_sn=1.5, shot_maks_sn=5.0),
}


def profil(ad: str = "premium-modern") -> EditProfili:
    return PROFILLER.get(ad, VARSAYILAN)


def font_statik_mi(yol: str) -> bool:
    """Font DEGISKEN mi? Degiskense ffmpeg varsayilan (genelde Thin) ornegi cizer.

    11 Agu 2026: Montserrat-Bold.ttf adinda ama fvar tablosu iceren degisken
    fonttu; bugune kadarki tum yazilar Thin cizilmis. Bu kontrol o hatanin
    tekrarlanmamasi icin."""
    try:
        with open(yol, "rb") as f:
            bas = f.read(4000)
        return b"fvar" not in bas
    except Exception:
        return False
