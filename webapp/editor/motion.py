"""MOTION TASARIM SPESIFIKASYONLARI — AE hissi, render edilebilir govde.

Her efekt bir SPEC uretir ve spec'te su ZORUNLU alanlar var:

    renderer   : "ffmpeg" | "remotion"        (nerede uretilecek)
    fallback   : ayni isi goren daha basit spec ya da None
    parametre  : renderer'a dogrudan cevrilebilir degerler

⚠ SESSIZ EFEKT KAYBI YASAK. 11 Agu'da olculen en pahali mimari hata buydu:
`Efektler.tsx`'te 35 bilesen vardi, hizli motor 6 filtre taniyordu ve
RENDER_MOTOR=ffmpeg varsayilan oldugu icin geri kalanlar SESSIZCE
kayboluyordu — kullanicinin gordugu tek "edit" grain+vinyet+zoom'du.
Bu yuzden burada her spec `renderer` beyan eder ve ffmpeg'de karsiligi
olmayan spec ya `fallback` verir ya `remotion_zorunlu=True` der.
Adapter (adapter.py) bunu okur ve isi dogru motora yonlendirir.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Optional

from .profil import EASING, EditProfili, VARSAYILAN

# ffmpeg'de karsiligi OLAN motion turleri (11 Agu'da 17 efekt tasindi)
FFMPEG_DESTEKLI = {
    "push-in", "pull-out", "pan-right", "pan-left", "static", "handheld",
    "slow-drift", "grain", "vignette", "letterbox", "grade", "chapter-title",
    "lower-third", "source-label", "callout", "hard-cut", "j-cut", "l-cut",
    "crossfade", "karartma", "flash", "chromatic", "directional-blur",
    "soft-zoom", "shake",
}
# Yalnizca Remotion'da yapilabilenler (2.5D, gercek maske, kinetik tipografi)
REMOTION_ZORUNLU = {
    "parallax-2.5d", "masked-reveal", "track-matte-wipe", "light-sweep",
    "film-burn", "quote-card", "map-route", "data-chart", "document-highlight",
    "kinetic-title", "text-in-video",
}


@dataclass
class MotionSpec:
    ad: str
    renderer: str = "ffmpeg"
    parametre: dict = field(default_factory=dict)
    easing: str = "kamera"
    bas_sn: float = 0.0
    sure_sn: float = 0.0
    katman: int = 0                     # 0 = zemin, artan = uste
    fallback: Optional[dict] = None     # basitlestirilmis spec (ffmpeg)
    remotion_zorunlu: bool = False
    gerekce: str = ""

    def sozluk(self) -> dict:
        d = asdict(self)
        d["easing_bezier"] = list(EASING.get(self.easing, EASING["lineer"]))
        return d


def _spec(ad: str, **kw) -> MotionSpec:
    zorunlu = ad in REMOTION_ZORUNLU
    r = "remotion" if zorunlu else ("ffmpeg" if ad in FFMPEG_DESTEKLI else "remotion")
    return MotionSpec(ad=ad, renderer=r, remotion_zorunlu=zorunlu, **kw)


# ═══════════════════════ KAMERA ═══════════════════════

# gramer.CEKIM_HAREKET'te gecen ama KAMERA hareketi olmayan adlar.
# Bunlarin animasyonu ilgili grafik spec'inden gelir (harita/veri/belge);
# kamera katmani sade kalir. Ilk surumde bu adlar kamera_spec'e dusuyor,
# renderer=remotion + fallback=None oluyordu ve QA "sessiz kayip" FAIL
# veriyordu (test yakaladi).
GRAFIK_HAREKETI = {
    "document-scan": "push-in",     # belgede ilgili bolgeye yaklas
    "map-route": "static",          # rota animasyonu harita spec'inde
    "data-reveal": "static",        # cubuk animasyonu veri spec'inde
}


# ⚠ FAZ I-27 — KADRAJ OLCEKLERI TEK KAYNAKTAN.
# Bu tablo `kamera_spec` icinde GOMULU idi. I-27'de plan tarafinin da ayni
# olcekleri bilmesi gerekti (kaynagi BUYUTMEYEN kadraji secmek icin); iki yere
# ayri yazmak sessiz ayrisma riski demekti. `Kamera.tsx > KADRAJ_OLCEK` ile
# AYNI degerler (TSX tarafi render'da ayni carpani uyguluyor).
KADRAJ_OLCEK = {"tam": 1.0, "ust": 1.2, "alt": 1.2,
                "punch-1.35": 1.35, "punch-1.6": 1.6}
# Buyutmeyen kadraj ararken denenecek SIRA: en genis (en az olcekli) EN SONDA.
# Deterministik; rastgelelik YOK.
KADRAJ_MERDIVENI = ("punch-1.6", "punch-1.35", "ust", "alt", "tam")


def _guvenli_pay(s_maks: float, guvenlik: float = 0.9) -> float:
    """Pan kaymasinin KENARDA SIYAH BANT uretmeyecegi en buyuk pay.

    ⚠ FAZ I-17'DE OLCULEN KUSUR. Render tarafi (`Kamera.tsx`) su transformu
    uyguluyor:  `transform: scale(S) translate(x%, y%)`
    CSS'te transform SAGDAN SOLA uygulanir ve yuzde kayma ELEMANIN KENDI
    genisligine goredir. Yani ekrandaki gercek yer degistirme `S * x`tir.
    Siyah kenar olmamasi icin bu, olceklenmis goruntunun tasma payini
    asmamali:

        S * pay  <=  (S - 1) / 2      ->      pay <= (S - 1) / (2S)

    Eski formul `max(0.04, (olcek-1)/2 + 0.04)` idi; hem S'yi (pan zoom'u
    dahil TOPLAM olcek) gormuyor hem de tasma payina EKLIYORDU. Olculen
    vaka: `pan-left` + `punch-1.6` -> S=1.696, pay=0.34, yer degistirme
    0.577 > tasma 0.348 -> sag kenarda SIYAH BANT (17.6 sn ciktinin
    16.72 sn karesinde goruldu).
    """
    try:
        s = float(s_maks)
    except (TypeError, ValueError):
        return 0.0
    if s <= 1.0:
        return 0.0
    return round(((s - 1.0) / (2.0 * s)) * guvenlik, 4)


def kamera_spec(hareket: str, sure_sn: float, kadraj: str, *,
                p: Optional[EditProfili] = None) -> MotionSpec:
    """Kamera keyframe'leri. Easing OLCULEN egriden (lineere yakin).

    Guvenli crop: zoom tavani 1.38 (olculen); pan taşma payi kadraja gore
    hesaplanir ki kenarlarda siyah bant olusmasin (21 Agu'daki "kenar
    siyahligi" hatasi bu payla cozulmustu)."""
    p = p or VARSAYILAN
    m = p.motion
    tavan = 1.38
    grafik_kaynagi = ""
    if hareket in GRAFIK_HAREKETI:
        grafik_kaynagi = hareket
        hareket = GRAFIK_HAREKETI[hareket]
    if hareket == "push-in":
        z0, z1 = 1.0, min(tavan, 1.0 + m.push_in_orani * sure_sn)
    elif hareket == "pull-out":
        z0, z1 = min(tavan, 1.0 + m.push_in_orani * sure_sn), 1.0
    elif hareket == "soft-zoom":
        z0, z1 = 1.0, min(tavan, 1.0 + m.yumusak_zoom_orani * sure_sn)
    else:
        z0 = z1 = 1.06 if hareket in ("pan-right", "pan-left", "slow-drift") else 1.0

    # ⚠ FAZ I-17 — PAN OLCULULUGU. Eskiden pan TAM aralikta (0.0-1.0)
    # kosuyordu; olculdu ki bu, 1.6 punch kadrajinda 4.7 sn'lik bir cekimde
    # optik hareketi 34.5'e cikariyor (komsu sahneler 3.5-5.4). Belgesel
    # dilinde Ken Burns pani YUMUSAKTIR. Aralik %70'e cekildi; `slow-drift`
    # zaten %30 kullaniyordu (tutarli aile).
    pan = {"pan-right": (0.15, 0.85), "pan-left": (0.85, 0.15),
           "slow-drift": (0.35, 0.65)}.get(hareket, (0.5, 0.5))
    olcek = KADRAJ_OLCEK.get(kadraj, 1.0)
    odak = {"ust": (0.5, 0.30), "alt": (0.5, 0.70)}.get(kadraj, (0.5, 0.5))

    return _spec("push-in" if hareket == "soft-zoom" else hareket,
                 sure_sn=sure_sn, easing="kamera",
                 parametre={"zoom": [round(z0 * olcek, 4), round(z1 * olcek, 4)],
                            "pan_x": list(pan), "odak": list(odak),
                            "guvenli_pay": _guvenli_pay(max(z0, z1) * olcek),
                            "tavan": tavan,
                            "handheld_genlik_px": 9 if hareket == "handheld" else 0},
                 gerekce=(f"{hareket}/{kadraj} — olculen easing, tavan {tavan}"
                          + (f" | animasyon {grafik_kaynagi} spec'inde"
                             if grafik_kaynagi else "")))


def parallax_spec(katman_sayisi: int, sure_sn: float, *,
                  p: Optional[EditProfili] = None) -> MotionSpec:
    """2.5D parallax — arsiv FOTOGRAFINI hareketlendirir.

    Neden Remotion: gercek katman ayrimi + per-katman transform gerekiyor.
    ffmpeg fallback'i tek katmanli yavas zoom (kaybi ACIKCA belirtiliyor)."""
    p = p or VARSAYILAN
    derinlik = list(p.motion.parallax_derinlik[:max(2, min(3, katman_sayisi))])
    return _spec("parallax-2.5d", sure_sn=sure_sn, easing="kamera", katman=0,
                 parametre={"katman_hizlari": derinlik,
                            "kamera_kaymasi_px": [0, 42],
                            "derinlik_bulaniklik": [0.0, 0.6, 1.2][:len(derinlik)]},
                 fallback={"ad": "soft-zoom", "renderer": "ffmpeg",
                           "parametre": {"zoom": [1.0, 1.05]},
                           "kayip": "2.5D katman ayrimi yok, tek katmanli zoom"},
                 gerekce="arsiv fotografini 2.5D katmanlarla hareketlendir")


# ═══════════════════════ REVEAL / ISIK ═══════════════════════

def masked_reveal_spec(yon: str = "left", sure_sn: float = 0.6) -> MotionSpec:
    return _spec("masked-reveal", sure_sn=sure_sn, easing="giris",
                 parametre={"yon": yon, "kenar_yumusakligi_px": 24},
                 fallback={"ad": "crossfade", "renderer": "ffmpeg",
                           "parametre": {"sure": min(0.4, sure_sn)},
                           "kayip": "maske kenari yok, duz crossfade"},
                 gerekce="bilgi katmanini maske ile ac")


def track_matte_wipe_spec(sure_sn: float = 0.5) -> MotionSpec:
    return _spec("track-matte-wipe", sure_sn=sure_sn, easing="giris",
                 parametre={"matte": "yazi-sekli", "yon": "left"},
                 fallback={"ad": "crossfade", "renderer": "ffmpeg",
                           "parametre": {"sure": min(0.35, sure_sn)},
                           "kayip": "track matte yok"},
                 gerekce="yazi seklinden goruntu acilimi")


def light_sweep_spec(sure_sn: float = 0.8, siddet: float = 0.35) -> MotionSpec:
    return _spec("light-sweep", sure_sn=sure_sn, easing="giris",
                 parametre={"aci": 24, "siddet": siddet, "genislik_orani": 0.22},
                 fallback={"ad": "flash", "renderer": "ffmpeg",
                           "parametre": {"sure": 0.12, "siddet": siddet * 0.5},
                           "kayip": "yonlu isik sizmasi yok, kisa flash"},
                 gerekce="baslik uzerinde kontrollu isik gecisi")


def film_burn_spec(sure_sn: float = 0.5, siddet: float = 0.18) -> MotionSpec:
    """RESTRAINED film-burn. Siddet tavani bilincli dusuk: yuksek deger
    "ucuz efekt" hissi veriyor ve referansta hic gorulmuyor."""
    return _spec("film-burn", sure_sn=sure_sn, easing="cikis",
                 parametre={"siddet": min(0.25, siddet), "sicaklik": 0.6},
                 fallback={"ad": "karartma", "renderer": "ffmpeg",
                           "parametre": {"dip": 0.13},
                           "kayip": "film yanigi dokusu yok, parlaklik dip'i"},
                 gerekce="perde gecisinde arsiv dokusu")


# ═══════════════════════ YAZI / GRAFIK KATMANLARI ═══════════════════════

def bolum_basligi_spec(metin: str, sure_sn: float, *,
                       p: Optional[EditProfili] = None) -> MotionSpec:
    p = p or VARSAYILAN
    t = p.tipografi
    return _spec("chapter-title", sure_sn=sure_sn, easing="giris", katman=30,
                 # ⚠ I-39: y_orani 0.70 IDI; altyazi bandina (0.81) yalniz
                 # 15.8 px kaliyordu, gerekli nefes 47.5 px. Deger
                 # `tipografi.KONUM["chapter-title"]` ile AYNI olmali —
                 # test bu esligi kilitliyor (iki ayri aritmetik I-14 kusuru).
                 parametre={"metin": metin, "punto": t.bolum_basligi,
                            "agirlik": 700, "x": t.izgara_x, "y_orani": 0.60,
                            "bant": True, "bant_opaklik": t.bant_opaklik,
                            "giris_sn": t.min_gorunme_sn * 0.23,
                            "kademe": 3},
                 gerekce="bolum aciligi — ortada DEGIL alt-uclu izgarada")


def alt_band_spec(baslik: str, alt: str, sure_sn: float, *,
                  p: Optional[EditProfili] = None) -> MotionSpec:
    p = p or VARSAYILAN
    t = p.tipografi
    return _spec("lower-third", sure_sn=min(sure_sn, 4.7), easing="giris",
                 katman=30,
                 parametre={"baslik": baslik, "alt": alt,
                            "punto": t.alt_band_baslik, "alt_punto": t.alt_band_alt,
                            "x": t.izgara_x + 22, "y_orani": 0.78,
                            "vurgu_cubugu": True, "bant": True,
                            "giris_sn": 0.28},
                 gerekce="olculen en yaygin yazi turu (%33), omur 4.7 sn")


def kaynak_etiketi_spec(kaynak: str, fact_id: str, sure_sn: float, *,
                        p: Optional[EditProfili] = None) -> MotionSpec:
    """Ekranda kaynak/atif — fact_id ile BAGLI (izlenebilirlik)."""
    p = p or VARSAYILAN
    return _spec("source-label", sure_sn=min(sure_sn, 3.0), easing="giris",
                 katman=20,
                 parametre={"metin": kaynak, "fact_id": fact_id,
                            "punto": p.tipografi.kaynak_etiketi,
                            # ⚠ I-39: "sag-alt" YAZIYORDU ama konumu artik
                            # yalniz `y_orani` belirliyor (altyazi varsa SAG
                            # UST). Yaniltici sabit yerine kaynak alan adi.
                            "konum": "y_orani", "opaklik": 0.62},
                 gerekce=f"kaynak gosterimi ({fact_id})")


def callout_spec(metin: str, x: float, y: float, sure_sn: float, *,
                 p: Optional[EditProfili] = None) -> MotionSpec:
    p = p or VARSAYILAN
    return _spec("callout", sure_sn=min(sure_sn, 1.8), easing="overshoot",
                 katman=25,
                 parametre={"metin": metin, "x": x, "y": y,
                            "punto": p.tipografi.callout, "nokta": True,
                            "cizgi": True},
                 gerekce="olculen kucuk etiket omru 1.8 sn")


def alinti_karti_spec(alinti: str, kaynak: str, sure_sn: float) -> MotionSpec:
    return _spec("quote-card", sure_sn=sure_sn, easing="giris", katman=40,
                 parametre={"alinti": alinti[:220], "kaynak": kaynak,
                            "hizalama": "sol", "tirnak": True},
                 fallback={"ad": "lower-third", "renderer": "ffmpeg",
                           "parametre": {"baslik": alinti[:34], "alt": kaynak},
                           "kayip": "alinti karti duzeni yok, alt banda dusuldu"},
                 gerekce="atifli alinti — haber ekran goruntusu TAKLIDI DEGIL")


def belge_vurgusu_spec(bolge: tuple, sure_sn: float) -> MotionSpec:
    return _spec("document-highlight", sure_sn=sure_sn, easing="giris", katman=25,
                 parametre={"bolge": list(bolge), "kenar_kalinlik": 3,
                            "karartma_disi": 0.45, "punch_zoom": 1.25},
                 fallback={"ad": "callout", "renderer": "ffmpeg",
                           "parametre": {"metin": "", "x": bolge[0], "y": bolge[1]},
                           "kayip": "belge disini karartma yok, sade cerceve"},
                 gerekce="kanit gosterimi: belgede ilgili bolgeye odak")


def harita_spec(yer: str, rota: Optional[list] = None,
                sure_sn: float = 4.0) -> MotionSpec:
    return _spec("map-route", sure_sn=sure_sn, easing="kamera", katman=10,
                 parametre={"yer": yer, "rota": rota or [],
                            "keypointler": [yer] if yer else [],
                            "cizim_sn": max(1.0, sure_sn * 0.55),
                            "zoom_hedefi": 1.4},
                 fallback={"ad": "callout", "renderer": "ffmpeg",
                           "parametre": {"metin": yer, "x": 0.5, "y": 0.5},
                           "kayip": "harita animasyonu yok, yer etiketi"},
                 gerekce="konum iddiasi -> harita (telif riski yok, kendi grafigimiz)")


def veri_grafigi_spec(baslik: str, degerler: list, sure_sn: float = 4.0) -> MotionSpec:
    return _spec("data-chart", sure_sn=sure_sn, easing="giris", katman=10,
                 parametre={"baslik": baslik, "degerler": degerler[:6],
                            "tur": "bar", "sayac_animasyonu": True,
                            "cizim_sn": max(0.8, sure_sn * 0.5)},
                 fallback={"ad": "callout", "renderer": "ffmpeg",
                           "parametre": {"metin": f"{baslik}: {degerler[:1]}",
                                         "x": 0.5, "y": 0.4},
                           "kayip": "grafik animasyonu yok, sayi etiketi"},
                 gerekce="sayisal kanit -> veri sahnesi")


# ═══════════════════════ TABAN KATMANLAR ═══════════════════════

def taban_katmanlar(sure_sn: float, *, p: Optional[EditProfili] = None) -> list:
    """Her cekimde bulunan doku katmanlari (grain/vinyet/letterbox/grade)."""
    p = p or VARSAYILAN
    m = p.motion
    out = [
        _spec("grain", sure_sn=sure_sn, katman=90, easing="lineer",
              parametre={"siddet": m.grain, "doku": "onceden-uretilmis"},
              gerekce="ince film dokusu"),
        _spec("vignette", sure_sn=sure_sn, katman=91, easing="lineer",
              parametre={"siddet": m.vignette, "aci": "PI/5"}),
        _spec("grade", sure_sn=sure_sn, katman=92, easing="lineer",
              parametre={"profil": m.grade}),
    ]
    if m.letterbox:
        out.append(_spec("letterbox", sure_sn=sure_sn, katman=93,
                         parametre={"oran": 2.39}))
    return out


# ═══════════════════════ GECISLER ═══════════════════════

# Motive edilmis gecisler: her birinin NEDEN kullanildigi yazili olmali
GECIS_GEREKCESI = {
    "hard-cut": "varsayilan — olculen %79.9",
    "j-cut": "ses onden girer: bilgi akisini yumusatir",
    "l-cut": "ses devam eder: goruntu once degisir",
    "crossfade": "zaman/mekan atlamasi",
    "karartma": "perde sonu (parlaklik dip'i, siyaha inmez)",
    "flash": "sok/vurgu ani",
    "match-cut": "gorsel eslesme",
    "whip": "hizli mekan degisimi",
    "zoom-through": "ayni nesnede olcek atlama",
    "glitch": "teknoloji/bozulma anlatimi",
}
# SEYREK kullanilmasi gereken gecisler (referansta toplam %2.4)
SEYREK_GECISLER = {"whip", "zoom-through", "glitch", "match-cut"}


def gecis_spec(tur: str, sure_sn: float = 0.0, *, gerekce: str = "") -> MotionSpec:
    tur = tur if tur in GECIS_GEREKCESI else "hard-cut"
    varsayilan_sure = {"hard-cut": 0.066, "j-cut": 0.0, "l-cut": 0.0,
                       "crossfade": 0.4, "karartma": 0.48, "flash": 0.16,
                       "match-cut": 0.066, "whip": 0.22, "zoom-through": 0.3,
                       "glitch": 0.2}.get(tur, 0.2)
    s = sure_sn or varsayilan_sure
    spec = _spec(tur if tur in FFMPEG_DESTEKLI else "crossfade",
                 sure_sn=s, easing="giris", katman=99,
                 parametre={"tur": tur, "sure": s},
                 gerekce=gerekce or GECIS_GEREKCESI[tur])
    if tur in SEYREK_GECISLER and not gerekce:
        spec.gerekce += " | ⚠ SEYREK GECIS: gerekce zorunlu"
    if tur == "karartma":
        # ffmpeg xfade=fadeblack ASIMETRIK (olculdu: inis 2 kare, cikis 8 kare).
        # Referans siyaha hic inmiyor; kendi dip'imizi kullaniyoruz.
        spec.parametre["uygulama"] = "eq-brightness-dip"
        spec.parametre["dip"] = 0.13
    return spec


def sec_gecis(onceki_islev: str, simdi_islev: str, indeks: int,
              j_cut: bool = False, l_cut: bool = False) -> MotionSpec:
    """MOTIVE EDILMIS gecis secimi — rastgele degil, islev degisimine bagli."""
    if j_cut:
        return gecis_spec("j-cut", gerekce=f"{onceki_islev}->{simdi_islev}: ses onden")
    if l_cut:
        return gecis_spec("l-cut", gerekce=f"{onceki_islev}->{simdi_islev}: ses devam")
    if simdi_islev == "hook" and indeks > 0:
        return gecis_spec("flash", gerekce="hook'a donus vurgusu")
    if onceki_islev == "sonuc" and simdi_islev == "sonuc":
        return gecis_spec("karartma", gerekce="perde sonu")
    if onceki_islev != simdi_islev and simdi_islev == "kanit":
        return gecis_spec("crossfade", gerekce="anlatimdan kanita gecis")
    # ⚠ FAZ I-17 — KAPANISA GIRIS. I-16 ciktisinda dort gecisin DORDU DE
    # `hard-cut`ti: mevcut kurallarin hicbiri hook->aciklama->aciklama->sonuc
    # diziliminde tetiklenmiyordu. Kapanis beat'ine GIRIS belgesel dilinde
    # yumusar; bu, rastgele cesitlilik degil ISLEVE BAGLI bir karardir.
    # ⚠ `sonuc -> sonuc` yukarida zaten `karartma`; burasi yalnizca GIRIS.
    if onceki_islev and onceki_islev != simdi_islev and simdi_islev == "sonuc":
        return gecis_spec("karartma", gerekce="kapanis beat'ine gecis")
    return gecis_spec("hard-cut")
