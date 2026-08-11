"""TIPOGRAFI — guvenli alan, satir uzunlugu, minimum sure, CAKISMA COZUCU.

Neden cakisma cozucu gerekiyor: alt band (y=%78), altyazi (y=%86) ve bolum
basligi (y=%70) ayni anda ekranda olabilir. 11 Agu ciktisinda bolum basligi ile
alt band ust uste bindi ve ikisi de okunamaz hale geldi (kareyi gorunce fark
ettim). Bu modul ayni zaman aralikinda cakisan yazi katmanlarini bulup
birini KAYDIRIR ya da erteler.

Kontrast kurali: yazi zemine GUVENMEZ. Beyaz yazi acik zeminde kayboluyor
(11 Agu, aydinlik koridor duvari) — bu yuzden her yazi katmani bant tasir.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .profil import EditProfili, VARSAYILAN

# Yazi katmani turleri ve varsayilan dikey konumlari (0-1)
KONUM = {
    "chapter-title": 0.70,
    "lower-third": 0.78,
    "quote-card": 0.42,
    "callout": 0.45,          # x/y spec'ten gelir
    # 0.94 iken alt kenar 1063px oluyordu ve guvenli alani (1016px) tasiyordu
    # (onizleme QA'sinda goruldu). 0.91 -> alt kenar 1031... hala tasar; 0.90.
    "source-label": 0.90,
    "subtitle": 0.86,
    "data-chart": 0.30,
}
# Katmanin kapladigi dikey yer (oran)
YUKSEKLIK = {
    "chapter-title": 0.105, "lower-third": 0.115, "quote-card": 0.24,
    "callout": 0.05, "source-label": 0.045, "subtitle": 0.085,
    "data-chart": 0.34,
}


@dataclass
class YaziKatmani:
    ad: str
    metin: str = ""
    bas_sn: float = 0.0
    sure_sn: float = 0.0
    x: int = 100
    y_orani: float = 0.78
    punto: int = 40
    agirlik: int = 700
    bant: bool = True
    fact_id: str = ""
    kaydirildi: bool = False
    uyarilar: list = field(default_factory=list)

    @property
    def bitis_sn(self) -> float:
        return self.bas_sn + self.sure_sn

    @property
    def alt_kenar(self) -> float:
        return self.y_orani + YUKSEKLIK.get(self.ad, 0.08)


def satir_bol(metin: str, maks: int) -> list:
    """Uzun metni satirlara bol. Okunabilirlik: satir 42 karakteri gecmemeli."""
    kelimeler = str(metin or "").split()
    satirlar, su_an = [], ""
    for k in kelimeler:
        if len(su_an) + len(k) + 1 > maks and su_an:
            satirlar.append(su_an)
            su_an = k
        else:
            su_an = f"{su_an} {k}".strip()
    if su_an:
        satirlar.append(su_an)
    return satirlar or [""]


def guvenli_alan_kontrol(k: YaziKatmani, *, p: Optional[EditProfili] = None) -> list:
    """Katman yayin guvenli alaninin icinde mi?"""
    p = p or VARSAYILAN
    t = p.tipografi
    sorunlar = []
    sol_pay = k.x
    if sol_pay < t.guvenli_kenar:
        sorunlar.append({"kod": "TIPO-GUVENLI-SOL",
                         "detay": f"x={k.x} < guvenli kenar {t.guvenli_kenar}"})
    ust_px = k.y_orani * p.yukseklik
    alt_px = k.alt_kenar * p.yukseklik
    if ust_px < t.guvenli_kenar:
        sorunlar.append({"kod": "TIPO-GUVENLI-UST",
                         "detay": f"ust={int(ust_px)}px < {t.guvenli_kenar}"})
    if alt_px > p.yukseklik - t.guvenli_kenar:
        sorunlar.append({"kod": "TIPO-GUVENLI-ALT",
                         "detay": f"alt={int(alt_px)}px > "
                                  f"{p.yukseklik - t.guvenli_kenar}"})
    # Metin genisligi (kaba tahmin: Montserrat Bold ~0.60em)
    satirlar = satir_bol(k.metin, t.maks_satir_karakter)
    en_uzun = max((len(s) for s in satirlar), default=0)
    genislik = int(en_uzun * k.punto * 0.60)
    if k.x + genislik > p.genislik - t.guvenli_kenar:
        sorunlar.append({"kod": "TIPO-TASMA",
                         "detay": f"tahmini genislik {genislik}px, "
                                  f"{en_uzun} karakter"})
    if len(satirlar) > 2 and k.ad != "quote-card":
        sorunlar.append({"kod": "TIPO-COK-SATIR",
                         "detay": f"{len(satirlar)} satir (tavan 2)"})
    if k.sure_sn < t.min_gorunme_sn:
        sorunlar.append({"kod": "TIPO-KISA-SURE",
                         "detay": f"{k.sure_sn} sn < {t.min_gorunme_sn} sn"})
    # ⚠ KUNYE ISTISNASI: kaynak etiketi bant TASIMAZ, kontur+golge ile cizilir
    # (hizli_render._kaynak_yazi_filtre). Bilgi yazisi degil kunye oldugu icin
    # goze batmamasi gerekiyor. Ilk surumde bu FAIL uretiyordu (test yakaladi).
    if not k.bant and k.ad != "source-label":
        sorunlar.append({"kod": "TIPO-KONTRAST",
                         "detay": "bant yok — acik zeminde okunmaz "
                                  "(11 Agu olcumu)"})
    return sorunlar


def _cakisiyor(a: YaziKatmani, b: YaziKatmani) -> bool:
    """Zaman VE dikey konum ust uste biniyor mu?"""
    zaman = not (a.bitis_sn <= b.bas_sn + 0.01 or b.bitis_sn <= a.bas_sn + 0.01)
    if not zaman:
        return False
    return not (a.alt_kenar <= b.y_orani + 0.005 or b.alt_kenar <= a.y_orani + 0.005)


# Katman onceligi: cakismada DUSUK onceligi olan kaydirilir
ONCELIK = {"quote-card": 5, "chapter-title": 4, "data-chart": 4,
           "lower-third": 3, "subtitle": 2, "callout": 2, "source-label": 1}


def cakisma_coz(katmanlar: list, *, p: Optional[EditProfili] = None) -> tuple:
    """Cakisan yazi katmanlarini coz. Doner (cozulmus_katmanlar, rapor).

    Strateji sirasi:
      1. Dusuk oncelikli katmani DIKEY KAYDIR (bosluk varsa)
      2. Kaydirilamiyorsa SURESINI KISALT (cakisma bitene kadar ertele)
      3. Ikisi de olmuyorsa DUSUR ve rapora yaz
    """
    p = p or VARSAYILAN
    rapor = []
    kalan = sorted(katmanlar, key=lambda k: (-ONCELIK.get(k.ad, 0), k.bas_sn))
    yerlesmis: list = []

    for k in kalan:
        cakisanlar = [y for y in yerlesmis if _cakisiyor(k, y)]
        if not cakisanlar:
            yerlesmis.append(k)
            continue
        # 1) Dikey kaydirma dene
        cozuldu = False
        for hedef in (0.60, 0.52, 0.34, 0.88, 0.26):
            deneme = YaziKatmani(**{**k.__dict__, "y_orani": hedef,
                                    "uyarilar": list(k.uyarilar)})
            if not any(_cakisiyor(deneme, y) for y in yerlesmis) and \
                    not guvenli_alan_kontrol(deneme, p=p):
                k.y_orani = hedef
                k.kaydirildi = True
                k.uyarilar.append(f"CAKISMA-KAYDIRILDI: y={hedef}")
                rapor.append({"kod": "TIPO-CAKISMA-KAYDIRILDI", "katman": k.ad,
                              "detay": f"y {KONUM.get(k.ad)} -> {hedef} "
                                       f"({[c.ad for c in cakisanlar]})"})
                yerlesmis.append(k)
                cozuldu = True
                break
        if cozuldu:
            continue
        # 2) Erteleme: cakisan en gec biteni bekle
        en_gec = max(c.bitis_sn for c in cakisanlar)
        yeni_bas = en_gec + 0.15
        kalan_sure = (k.bas_sn + k.sure_sn) - yeni_bas
        if kalan_sure >= p.tipografi.min_gorunme_sn:
            k.bas_sn, k.sure_sn = round(yeni_bas, 3), round(kalan_sure, 3)
            k.uyarilar.append("CAKISMA-ERTELENDI")
            rapor.append({"kod": "TIPO-CAKISMA-ERTELENDI", "katman": k.ad,
                          "detay": f"bas {yeni_bas:.2f} sn"})
            yerlesmis.append(k)
            continue
        # 3) Dusur
        rapor.append({"kod": "TIPO-CAKISMA-DUSURULDU", "katman": k.ad,
                      "seviye": "uyari",
                      "detay": f"cozulemedi ({[c.ad for c in cakisanlar]})"})
    return sorted(yerlesmis, key=lambda k: k.bas_sn), rapor


def katman_kur(spec_adi: str, metin: str, bas_sn: float, sure_sn: float, *,
               fact_id: str = "", p: Optional[EditProfili] = None,
               x: Optional[int] = None,
               y_orani: Optional[float] = None) -> YaziKatmani:
    p = p or VARSAYILAN
    t = p.tipografi
    punto = {"chapter-title": t.bolum_basligi, "lower-third": t.alt_band_baslik,
             "callout": t.callout, "source-label": t.kaynak_etiketi,
             "subtitle": t.altyazi, "quote-card": t.alt_band_baslik}.get(
        spec_adi, t.callout)
    return YaziKatmani(ad=spec_adi, metin=metin, bas_sn=round(bas_sn, 3),
                       sure_sn=round(sure_sn, 3),
                       x=t.izgara_x if x is None else x,
                       y_orani=KONUM.get(spec_adi, 0.78) if y_orani is None
                       else y_orani,
                       punto=punto, agirlik=700,
                       bant=spec_adi != "source-label", fact_id=fact_id)
