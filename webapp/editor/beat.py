"""BEAT / SEKANS PLANLAYICI — anlatiyi kurgu ritmine cevirir.

Neden gerekli: 11 Agu ciktisinda her sahne SABIT ~5.5 sn'ydi ve video
"slayt gosterisi" gibi duruyordu. Profesyonel belgeselde sure sabit degil;
cumlenin ISLEVINE ve bilgi yogunluguna gore degisiyor. Hook 2 sn'lik carpici
bir cekim isterken, kanit cumlesi belgenin okunmasi icin 5 sn istiyor.

Bu modul LLM KULLANMIYOR: islev siniflandirmasi dilbilgisel kaliplarla
(soru isareti, sayi varligi, baglac, zaman zarfi) yapiliyor. Sebep hem maliyet
hem determinizm — ayni senaryo her uretimde ayni ritmi almali, testler de
kosabilmeli.

UC PERDE: hook (ilk %12) -> gelisme -> sonuc (son %18). Perde sinirlari
ritmi degistirir: sonuc perdesinde cekimler uzar ve nefes payi artar.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Optional

from .profil import EditProfili, VARSAYILAN

ISLEVLER = ("hook", "kurulum", "kanit", "aciklama", "donus", "sonuc")
PERDELER = ("acilis", "gelisme", "kapanis")

# ── Islev tespiti icin dilbilgisel isaretler ──
_SORU = re.compile(r"\?\s*$")
_SAYI = re.compile(r"\d")
_KAYNAK_ISARETI = re.compile(
    r"\b(according to|reported|recorded|published|official|data|survey|study|"
    r"ministry|agency|bureau|census|report)\b", re.I)
_DONUS = re.compile(
    r"\b(but|yet|however|although|though|instead|on the other hand|"
    r"and yet|the truth is|in fact|actually)\b", re.I)
_SONUC = re.compile(
    r"\b(so|therefore|which means|in the end|finally|that is why|the lesson|"
    r"what this tells us|go back to)\b", re.I)
_KURULUM = re.compile(
    r"\b(there is|there was|it began|start with|imagine|consider|"
    r"in \d{4}|once|behind)\b", re.I)


@dataclass
class Beat:
    """Tek bir kurgu birimi: bir cumlenin bir bolumu, tek cekimlik."""
    beat_id: str
    scene_id: str
    fact_id: str = ""
    cumle_indeksi: int = 0
    metin: str = ""
    islev: str = "aciklama"
    perde: str = "gelisme"
    bas_sn: float = 0.0
    sure_sn: float = 0.0
    bilgi_yogunlugu: float = 0.0      # 0-1
    j_cut: bool = False               # ses GORUNTUDEN once girer
    l_cut: bool = False               # ses goruntuden sonra devam eder
    nefes_payi_sn: float = 0.0
    gerekce: str = ""                 # sure/istisna gerekcesi

    @property
    def bitis_sn(self) -> float:
        return round(self.bas_sn + self.sure_sn, 3)


@dataclass
class BeatPlani:
    beatler: list = field(default_factory=list)
    toplam_sn: float = 0.0
    perde_sinirlari: dict = field(default_factory=dict)
    uyarilar: list = field(default_factory=list)

    def sozluk(self) -> dict:
        return {"toplam_sn": round(self.toplam_sn, 2),
                "beat_sayisi": len(self.beatler),
                "perde_sinirlari": self.perde_sinirlari,
                "uyarilar": self.uyarilar,
                "beatler": [asdict(b) for b in self.beatler]}

    def sure_histogrami(self, kova: float = 1.0) -> dict:
        h: dict = {}
        for b in self.beatler:
            k = f"{int(b.sure_sn // kova) * kova:.0f}-{int(b.sure_sn // kova) * kova + kova:.0f}"
            h[k] = h.get(k, 0) + 1
        return dict(sorted(h.items(), key=lambda x: float(x[0].split("-")[0])))


def islev_belirle(metin: str, indeks: int, toplam: int) -> str:
    """Cumlenin anlatidaki islevi. Ilk cumle her zaman hook adayi."""
    m = str(metin or "").strip()
    if indeks == 0:
        return "hook"
    if _SORU.search(m):
        return "hook" if indeks < max(2, toplam * 0.15) else "donus"
    if _DONUS.search(m):
        return "donus"
    if _SONUC.search(m) or indeks >= toplam - 1:
        return "sonuc"
    if _SAYI.search(m) and _KAYNAK_ISARETI.search(m):
        return "kanit"
    if _SAYI.search(m):
        return "kanit"
    if _KURULUM.search(m) and indeks < toplam * 0.4:
        return "kurulum"
    return "aciklama"


def bilgi_yogunlugu(metin: str) -> float:
    """0-1. Sayi, oz ad ve uzunluk bilgi yogunlugunu artirir.

    Neden onemli: yogun cumle daha UZUN cekim ister (izleyici okuyup
    sindirmeli), seyrek cumle kisa cekim tasir. Sabit sure bu farki yok
    sayiyordu."""
    m = str(metin or "")
    if not m.strip():
        return 0.0
    kelime = max(1, len(m.split()))
    sayi = len(re.findall(r"\d[\d.,]*", m))
    ozad = len(re.findall(r"\b[A-Z][a-z]{2,}", m))
    virgul = m.count(",")
    p = (0.30 * min(1.0, sayi / 2.0)
         + 0.25 * min(1.0, ozad / 3.0)
         + 0.20 * min(1.0, virgul / 3.0)
         + 0.25 * min(1.0, kelime / 26.0))
    return round(min(1.0, p), 3)


def _perde(bas_sn: float, toplam_sn: float) -> str:
    if toplam_sn <= 0:
        return "gelisme"
    o = bas_sn / toplam_sn
    if o < 0.12:
        return "acilis"
    if o > 0.82:
        return "kapanis"
    return "gelisme"


def _hedef_shot_sn(islev: str, yogunluk: float, perde: str, p: EditProfili) -> float:
    """Cekim suresi: islev + bilgi yogunlugu + perde."""
    taban = {
        "hook": 2.0,        # carpici, kisa
        "kurulum": 4.2,
        "kanit": 5.0,       # belge/sayi okunacak
        "aciklama": 3.6,
        "donus": 2.6,       # ritim kirilir
        "sonuc": 5.2,       # nefes
    }.get(islev, 3.6)
    taban += 2.2 * yogunluk                      # yogun bilgi -> uzun cekim
    if perde == "kapanis":
        taban += 0.6
    if perde == "acilis":
        taban -= 0.4
    return max(p.shot_min_sn, min(p.shot_maks_sn, round(taban, 2)))


def cumleyi_bol(metin: str, sure_sn: float, islev: str, yogunluk: float,
                perde: str, p: EditProfili) -> list:
    """Bir cumlenin ses suresini cekimlere bol.

    Tek cekim hedef araligi asiyorsa BOLUNUR. Bolme noktalari cumlenin
    dogal duraklamalarindan (virgul, noktali virgul, baglac) secilir —
    keyfi zaman bolmesi goruntu ile sesi ayirir."""
    hedef = _hedef_shot_sn(islev, yogunluk, perde, p)
    if sure_sn <= p.shot_maks_sn and sure_sn <= hedef * 1.5:
        return [(metin, sure_sn, "")]

    adet = max(1, int(round(sure_sn / hedef)))
    # 8 sn kesin tavani: gerekirse parca sayisi artirilir
    while adet > 0 and sure_sn / adet > p.shot_kesin_tavan_sn:
        adet += 1
    if adet <= 1:
        return [(metin, sure_sn, f"tek cekim {sure_sn:.1f} sn — bolunemedi")]

    # Dogal duraklamalar
    parcalar = [x for x in re.split(r"(?<=[,;:])\s+|\s+(?=(?:and|but|which|because|while|after|before)\b)",
                                    metin) if x and x.strip()]
    if len(parcalar) < adet:
        # Yetersiz duraklama -> kelime bazli esit bolme (son care)
        kelimeler = metin.split()
        if len(kelimeler) >= adet:
            n = len(kelimeler) // adet
            parcalar = [" ".join(kelimeler[i * n:(i + 1) * n]) for i in range(adet - 1)]
            parcalar.append(" ".join(kelimeler[(adet - 1) * n:]))
        else:
            parcalar = [metin] * adet
    # Parcalari adet kadar gruba topla
    grup = [[] for _ in range(adet)]
    for i, pc in enumerate(parcalar):
        grup[min(adet - 1, i * adet // max(1, len(parcalar)))].append(pc)
    metinler = [" ".join(g).strip() or metin for g in grup]
    # Sureyi kelime agirligina gore dagit (esit bolme metronom gibi duyulur)
    agirlik = [max(1, len(m.split())) for m in metinler]
    toplam_a = sum(agirlik)
    sureler = [round(sure_sn * a / toplam_a, 3) for a in agirlik]
    # Yuvarlama farkini son parcaya ver
    sureler[-1] = round(sure_sn - sum(sureler[:-1]), 3)
    return [(metinler[i], sureler[i], "") for i in range(adet)]


def plan_yap(cumleler: list, *, profil_: Optional[EditProfili] = None) -> BeatPlani:
    """Cumlelerden beat plani.

    `cumleler`: [{"metin","sure_sn","fact_id","scene_id"}]  (sure_sn = anlatim suresi)
    """
    p = profil_ or VARSAYILAN
    temiz = [c for c in (cumleler or []) if str(c.get("metin", "")).strip()]
    toplam = sum(float(c.get("sure_sn") or 0) for c in temiz)
    plan = BeatPlani(toplam_sn=toplam)
    if not temiz:
        plan.uyarilar.append("BEAT-BOS: cumle yok")
        return plan

    t = 0.0
    sayac = 0
    for i, c in enumerate(temiz):
        metin = str(c["metin"]).strip()
        sure = float(c.get("sure_sn") or 0)
        if sure <= 0:
            plan.uyarilar.append(f"BEAT-SURE: cumle {i} suresi 0, atlandi")
            continue
        islev = islev_belirle(metin, i, len(temiz))
        yog = bilgi_yogunlugu(metin)
        perde = _perde(t, toplam)
        for j, (pm, ps, gerekce) in enumerate(
                cumleyi_bol(metin, sure, islev, yog, perde, p)):
            sayac += 1
            b = Beat(beat_id=f"b{sayac:03d}",
                     scene_id=str(c.get("scene_id") or f"s{i:03d}"),
                     fact_id=str(c.get("fact_id") or ""),
                     cumle_indeksi=i, metin=pm, islev=islev, perde=perde,
                     bas_sn=round(t, 3), sure_sn=round(ps, 3),
                     bilgi_yogunlugu=yog, gerekce=gerekce)
            # 8 sn tavani asiliyorsa GEREKCE ZORUNLU
            if b.sure_sn > p.shot_kesin_tavan_sn and not b.gerekce:
                b.gerekce = (f"kesin tavan {p.shot_kesin_tavan_sn} sn asildi "
                             f"({b.sure_sn} sn) — bolunemeyen tek cumle")
                plan.uyarilar.append(
                    f"SHOT-TAVAN: {b.beat_id} {b.sure_sn} sn (tavan "
                    f"{p.shot_kesin_tavan_sn})")
            plan.beatler.append(b)
            t += ps

    _audio_cut_isaretle(plan, p)
    _hook_kontrol(plan)
    plan.perde_sinirlari = {"acilis_bitis": round(toplam * 0.12, 2),
                            "kapanis_bas": round(toplam * 0.82, 2)}
    return plan


def _audio_cut_isaretle(plan: BeatPlani, p: EditProfili) -> None:
    """J-cut / L-cut isaretle.

    J-cut: ses bir sonraki sahneden ONCE girer (izleyici duymaya baslar,
    sonra gorur) — bilgi akisini yumusatir.
    L-cut: ses onceki sahneden DEVAM eder (goruntu once degisir).
    Islev degisiminde kullanilir; her kesmeye koymak "efekt gosterisi" olur.
    """
        # Referans olcumu: bu iki gecis toplamda ~%8, yani SEYREK.
    for i in range(1, len(plan.beatler)):
        onceki, simdi = plan.beatler[i - 1], plan.beatler[i]
        if onceki.cumle_indeksi == simdi.cumle_indeksi:
            continue                       # ayni cumlenin icindeki bolme
        if simdi.islev in ("kanit", "donus") and onceki.islev != simdi.islev:
            simdi.j_cut = True             # kanita gecerken ses onden girer
        elif onceki.islev in ("sonuc",) and simdi.islev == "sonuc":
            onceki.l_cut = True
        # Sonuc perdesinde nefes payi
        if simdi.perde == "kapanis" and simdi.islev == "sonuc":
            simdi.nefes_payi_sn = 0.4


def _hook_kontrol(plan: BeatPlani) -> None:
    """Ilk 8 saniyede hook var mi? Yoksa UYARI (bu bir kurgu kurali)."""
    ilk8 = [b for b in plan.beatler if b.bas_sn < 8.0]
    if not ilk8:
        plan.uyarilar.append("HOOK-YOK: ilk 8 sn'de beat yok")
        return
    if not any(b.islev == "hook" for b in ilk8):
        plan.uyarilar.append(
            "HOOK-YOK: ilk 8 saniyede hook islevi yok — izleyici kaybi riski")
    # Hook cok uzun olmamali
    for b in ilk8:
        if b.islev == "hook" and b.sure_sn > 4.0:
            plan.uyarilar.append(
                f"HOOK-UZUN: {b.beat_id} {b.sure_sn} sn (hook 4 sn'yi asmamali)")


def perde_ozeti(plan: BeatPlani) -> dict:
    d: dict = {p: {"beat": 0, "sure": 0.0} for p in PERDELER}
    for b in plan.beatler:
        d[b.perde]["beat"] += 1
        d[b.perde]["sure"] = round(d[b.perde]["sure"] + b.sure_sn, 2)
    return d


def islev_ozeti(plan: BeatPlani) -> dict:
    d: dict = {}
    for b in plan.beatler:
        d[b.islev] = d.get(b.islev, 0) + 1
    return d
