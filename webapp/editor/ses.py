"""SES PLANI — anlati merkezli mix, ducking, ambience, SFX kotasi.

Kurallar (kullanicinin acik istegi + olculen degerler):
  - Hedef -14 LUFS, true peak <= -1.0 dBTP
  - Muzik anlatiyi ORTMEZ: anlatim varken -18 dB ducking
  - Ambience bed: konuma bagli, cok kisik (-30 dB)
  - Vurgu SFX KOTASI: her cut'a whoosh EKLENMEZ. Referansta SFX seyrek.
  - J/L cut isaretleri beat plani'ndan gelir; ses ile goruntu ayni anda
    kesilmez (bu en cok "amator" gosteren seydir)
  - Nefes payi: sonuc perdesinde sessizlik birakilir

⚠ 11 Agu olcumu: iki gecisli loudnorm kurdum ama cikti -15.6 LUFS geldi.
Sebep kaynak dinamigi: ham ses -21.97 LUFS ve tepeleri yuksek; +8 dB kazanc
TP'yi asacagi icin loudnorm kendini kisiyor. Bu yuzden plan artik
NORMALIZASYONDAN ONCE hafif kompresyon iceriyor (3:1, -18 dB esik).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Optional

from .profil import EditProfili, VARSAYILAN

# Her N saniyede en fazla 1 vurgu SFX (referansta SFX seyrek)
SFX_KOTA_SN = 6.0
# Anlatim varken muzik seviyesi (dB)
DUCK_DB = -18.0
MUZIK_TABAN_DB = -8.0
AMBIENCE_DB = -30.0

# Islev -> uygun vurgu SFX. Bos = SFX YOK (varsayilan sessizlik).
ISLEV_SFX = {
    "hook": "impact-low",
    "kanit": "paper-turn",
    "donus": "riser-short",
    "sonuc": "",
    "kurulum": "",
    "aciklama": "",
}


@dataclass
class SesOlayi:
    tur: str                      # anlati | muzik | ambience | sfx | sessizlik
    bas_sn: float = 0.0
    sure_sn: float = 0.0
    seviye_db: float = 0.0
    ad: str = ""
    beat_id: str = ""
    gerekce: str = ""


@dataclass
class SesPlani:
    olaylar: list = field(default_factory=list)
    lufs_hedef: float = -14.0
    tepe_tavan: float = -1.0
    on_zincir: list = field(default_factory=list)
    ducking_zarfi: list = field(default_factory=list)   # [(bas, bitis, db)]
    uyarilar: list = field(default_factory=list)

    def sozluk(self) -> dict:
        # ⚠ FAZ Y-6: J/L-cut ve kaydirma suresi OLCUM ALANI olarak yayinlanir.
        # ESKI HAL: yalnizca `sfx_sayisi` disari veriliyordu; J/L olaylari
        # `olaylar` icinde gomuluydu ve QA bir SAYI bulamiyordu (kapi
        # kurulamiyordu). Kaydirma suresi de kodda SABITTI (0.35/0.4) —
        # simdi olculen deger olarak disari cikiyor.
        _j = [o for o in self.olaylar if o.tur == "j-cut"]
        _l = [o for o in self.olaylar if o.tur == "l-cut"]
        _kay = [float(o.sure_sn or 0.0) for o in (_j + _l)]
        return {"lufs_hedef": self.lufs_hedef, "tepe_tavan_dbtp": self.tepe_tavan,
                "on_zincir": self.on_zincir,
                "ducking_zarfi": [list(x) for x in self.ducking_zarfi],
                "sfx_sayisi": sum(1 for o in self.olaylar if o.tur == "sfx"),
                "j_cut_sayisi": len(_j), "l_cut_sayisi": len(_l),
                "ort_kaydirma_sn": (round(sum(_kay) / len(_kay), 3)
                                    if _kay else 0.0),
                "uyarilar": self.uyarilar,
                "olaylar": [asdict(o) for o in self.olaylar]}

    def sfx_yogunlugu(self, toplam_sn: float) -> float:
        n = sum(1 for o in self.olaylar if o.tur == "sfx")
        return round(n / max(1.0, toplam_sn / 60.0), 2)   # SFX/dakika


def plan_yap(beatler: list, *, profil_: Optional[EditProfili] = None,
             ambience: str = "", muzik: str = "") -> SesPlani:
    p = profil_ or VARSAYILAN
    toplam = sum(b.sure_sn for b in beatler) if beatler else 0.0
    plan = SesPlani(lufs_hedef=p.lufs_hedef, tepe_tavan=p.tepe_tavan_dbtp)

    # ── ON ZINCIR: kompresyon normalizasyondan ONCE ──
    plan.on_zincir = [
        {"filtre": "highpass", "f": 80,
         "gerekce": "TTS'te dusuk frekans cop var"},
        {"filtre": "deesser", "i": 0.35, "m": 0.5, "f": 0.18,
         "gerekce": "s/s sesleri tizde bicak gibi cikiyor"},
        {"filtre": "acompressor", "threshold": "-18dB", "ratio": 3,
         "attack": 8, "release": 140, "makeup": 2,
         "gerekce": "tepe-ortalama farkini darralt; +8 dB kazanc TP'yi asmasin "
                    "(11 Agu: iki gecisli loudnorm -15.6'da kaliyordu)"},
        {"filtre": "loudnorm", "gecis": 2, "I": p.lufs_hedef,
         "TP": p.tepe_tavan_dbtp, "LRA": 11, "linear": True,
         "gerekce": "olculen degerlerle tek adimda hedefe"},
        {"filtre": "alimiter", "limit": 0.95, "level": "disabled",
         "gerekce": "tepe kirpmasini onle, seviyeyi DEGISTIRME"},
    ]

    if not beatler:
        plan.uyarilar.append("SES-BOS: beat yok")
        return plan

    # ── ANLATI ──
    for b in beatler:
        plan.olaylar.append(SesOlayi(
            tur="anlati", bas_sn=b.bas_sn, sure_sn=b.sure_sn,
            seviye_db=0.0, beat_id=b.beat_id, ad=f"vo_{b.beat_id}"))

    # ── MUZIK + DUCKING ZARFI ──
    if muzik:
        plan.olaylar.append(SesOlayi(
            tur="muzik", bas_sn=0.0, sure_sn=toplam, seviye_db=MUZIK_TABAN_DB,
            ad=muzik, gerekce="anlati altinda yatak"))
        # Anlatim olan her aralikta duck
        for b in beatler:
            plan.ducking_zarfi.append(
                (round(max(0.0, b.bas_sn - 0.25), 3),
                 round(b.bas_sn + b.sure_sn + 0.35, 3), DUCK_DB))
        plan.ducking_zarfi = _zarf_birlestir(plan.ducking_zarfi)

    # ── AMBIENCE ──
    if ambience:
        plan.olaylar.append(SesOlayi(
            tur="ambience", bas_sn=0.0, sure_sn=toplam, seviye_db=AMBIENCE_DB,
            ad=ambience, gerekce="konum atmosferi, cok kisik"))

    # ── SFX (KOTALI) ──
    son_sfx = -999.0
    for b in beatler:
        sfx = ISLEV_SFX.get(b.islev, "")
        if not sfx:
            continue
        if b.bas_sn - son_sfx < SFX_KOTA_SN:
            continue                       # kota: her cut'a whoosh YOK
        plan.olaylar.append(SesOlayi(
            tur="sfx", bas_sn=round(b.bas_sn - 0.05, 3), sure_sn=0.7,
            seviye_db=-12.0, ad=sfx, beat_id=b.beat_id,
            gerekce=f"{b.islev} vurgusu (kota {SFX_KOTA_SN} sn)"))
        son_sfx = b.bas_sn

    # ── NEFES PAYI / SESSIZLIK ──
    for b in beatler:
        if b.nefes_payi_sn > 0:
            plan.olaylar.append(SesOlayi(
                tur="sessizlik", bas_sn=round(b.bitis_sn, 3),
                sure_sn=b.nefes_payi_sn, ad="nefes",
                beat_id=b.beat_id, gerekce="sonuc perdesinde nefes"))

    # ── J/L CUT: ses ile goruntu ayni anda kesilmez ──
    for b in beatler:
        if b.j_cut:
            plan.olaylar.append(SesOlayi(
                tur="j-cut", bas_sn=round(max(0.0, b.bas_sn - 0.35), 3),
                sure_sn=0.35, beat_id=b.beat_id,
                gerekce="ses goruntuden 0.35 sn ONCE girer"))
        if b.l_cut:
            plan.olaylar.append(SesOlayi(
                tur="l-cut", bas_sn=round(b.bitis_sn, 3), sure_sn=0.4,
                beat_id=b.beat_id,
                gerekce="ses goruntu kesildikten sonra 0.4 sn devam eder"))

    _kontrol(plan, toplam)
    return plan


def _zarf_birlestir(zarf: list) -> list:
    if not zarf:
        return []
    s = sorted(zarf)
    out = [list(s[0])]
    for bas, bitis, db in s[1:]:
        if bas <= out[-1][1] + 0.05:
            out[-1][1] = max(out[-1][1], bitis)
        else:
            out.append([bas, bitis, db])
    return [tuple(x) for x in out]


def _kontrol(plan: SesPlani, toplam_sn: float) -> None:
    yog = plan.sfx_yogunlugu(toplam_sn)
    if yog > 12:
        plan.uyarilar.append(f"SES-SFX-YOGUN: {yog}/dk (tavan 12)")
    duck = sum(b - a for a, b, _ in plan.ducking_zarfi)
    if toplam_sn and duck / toplam_sn > 0.95 and plan.ducking_zarfi:
        plan.uyarilar.append(
            "SES-DUCK-SUREKLI: muzik neredeyse hep kisik — muzik gereksiz olabilir")
    if plan.lufs_hedef > -13.0:
        plan.uyarilar.append("SES-LUFS: hedef -13'ten yuksek, YouTube kisar")
