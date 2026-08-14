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
    # ⚠ I-39: 0.70 IDI. 1080p pilotunda OLCULDU — bant alt kenari
    # 0.70*1080 + 60*1.3 + dolgu 25 = 859 px, altyazi bandi 874.8 px'te
    # basliyor: arada 15.8 px kaliyordu. Gerekli nefes = altyazi puntosu
    # * 1.25 = 47.5 px. 0.60 -> alt 751 px, nefes 123.8 px.
    # (Sayi hesaplandi, "yeterince yukarida" varsayilmadi — I-12 dersi.)
    "chapter-title": 0.60,
    "lower-third": 0.78,
    "quote-card": 0.42,
    "callout": 0.45,          # x/y spec'ten gelir
    # 0.94 iken alt kenar 1063px oluyordu ve guvenli alani (1016px) tasiyordu
    # (onizleme QA'sinda goruldu). 0.91 -> alt kenar 1031... hala tasar; 0.90.
    # ⚠ 0.90 DA TASIYORDU: 0.90+0.045=0.945 -> 1020.6px > 1016. Uc denemede de
    # deger "yeterince asagi" sanildi ama HESAPLANMADI; 20 sn render smoke'unda
    # QA bunu UC KEZ WARN olarak bildirdi (TIPO-GUVENLI-ALT). Dogru ust sinir:
    #   y_orani <= (1080-64)/1080 - 0.045 = 0.8957
    # 0.895 -> alt 1015.2px, guvenli alanin ICINDE.
    "source-label": 0.895,
    # ⚠ 0.86 DA TASIYORDU: 0.86+0.085=0.945 -> 1020.6px > 1016. Ayni kusur
    # sinifi (source-label ile birebir ayni aritmetik hata). Altyazi katmani
    # henuz uretilmedigi icin QA'da hic gorunmemisti — I-12'de eklenen
    # "tum yazi turleri guvenli alanda" testi yakaladi. 0.855 -> 1015.2px.
    "subtitle": 0.855,
    "data-chart": 0.30,
}
# Katmanin kapladigi dikey yer (oran)
YUKSEKLIK = {
    "chapter-title": 0.105, "lower-third": 0.115, "quote-card": 0.24,
    "callout": 0.05, "source-label": 0.045, "subtitle": 0.085,
    "data-chart": 0.34,
}

# ─────────────────────── ALTYAZI BANDI (Faz I-16) ───────────────────────
# Altyazi artik GERCEKTEN ciziliyor (Remotion `Altyazi` bileseni) ve ekranin
# alt seridini SUREKLI isgal ediyor. Bu yuzden bir REZERVE BANT tanimlanir:
# hicbir yazi katmani buraya yerlestirilmez, cakisma cozucu de buraya
# kaydirmaz. Sinirlar HESAPLANDI, "yeterince asagi" varsayilmadi:
#   alt = 0.94 -> 0.94*1080 = 1015.2 px  (guvenli alan tavani 1080-64 = 1016)
#   ust = 0.81 -> iki satir 38 punto + dolgu icin 0.13 oran yeter
ALTYAZI_BANT = (0.81, 0.94)
# Altyazi varken kaynak kunyesi bandin USTUNE tasinir (varsayilan 0.895
# bandin TAM ICINDE kalirdi).
# ⚠ I-39: 0.755 IDI ve "bandin hemen ustu" YETMIYORDU. 1080p pilotunda
# OLCULDU: kunye alt kenari 0.755*1080 + 21*1.3 = 842.7 px, bant 874.8 px'te
# basliyor -> yalniz **32.1 px** bosluk. Gerekli nefes = altyazi puntosu
# * 1.25 = **47.5 px**. Goz iki blogu tek yigin okuyordu; ikisi de okunmuyordu.
# 0.075 -> SAG UST kose (ust kenar 81 px, guvenli kenar 64 px'in icinde),
# altyazidan 766.5 px uzakta. Kunye HALA ekranda ve atif EKSILMIYOR.
KAYNAK_ETIKETI_ALTYAZILI = 0.075


def bant_cakisiyor(y_ust: float, yukseklik: float,
                   bant=ALTYAZI_BANT) -> bool:
    """Katman rezerve altyazi bandina giriyor mu? Saf aritmetik."""
    if not bant:
        return False
    try:
        u, a = float(bant[0]), float(bant[1])
        k_ust = float(y_ust)
        k_alt = k_ust + float(yukseklik)
    except (TypeError, ValueError, IndexError):
        return False
    return not (k_alt <= u + 1e-9 or k_ust >= a - 1e-9)


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


def cakisma_coz(katmanlar: list, *, p: Optional[EditProfili] = None,
                yasak_bant=None) -> tuple:
    """Cakisan yazi katmanlarini coz. Doner (cozulmus_katmanlar, rapor).

    Strateji sirasi:
      1. Dusuk oncelikli katmani DIKEY KAYDIR (bosluk varsa)
      2. Kaydirilamiyorsa SURESINI KISALT (cakisma bitene kadar ertele)
      3. Ikisi de olmuyorsa DUSUR ve rapora yaz

    ⚠ `yasak_bant` (Faz I-16): altyazi seridi gibi REZERVE bir bolge.
    Kaydirma adayi bu banda giriyorsa SECILMEZ. Aksi halde cozucu
    `0.88`'e kaydirip katmani altyazinin USTUNE bindirirdi — cozdugu
    cakismanin yerine yenisini koymus olurdu.
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
            if yasak_bant and bant_cakisiyor(
                    hedef, YUKSEKLIK.get(k.ad, 0.08), yasak_bant):
                continue                       # rezerve banda kaydirma YOK
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


# ═══════ ACILIS BASLIK/SERIT SURESI (Faz K-3) — SAF HESAP ══════════════
#
# ⚠ OLCULEN KUSUR: acilis basligi `min(5.5, beat.sure_sn + 1.5)` ile
# kuruluyordu. Bu formul (a) METNE HIC BAKMIYOR — iki kelimelik baslik da
# 5.5 sn duruyordu, (b) `+1.5` ile INTRO BEAT'i ASABILIYORDU, yani anlatici
# cumlesi bittikten sonra yazi ekranda ASILI kaliyordu.
#
# K-3 politikasi: sure METINDEN turer, okunabilir bir ALT sinirin altina
# inmez, ust sinirlari ASLA asmaz.
#
# ── ESIK KAYNAKLARI (durustce etiketli) ──
# `BASLIK_MAKS_CPS`  : TURETILMIS — `kalite_kapisi.ALTYAZI_MAKS_CPS` (20.0)
#                      ayni izleyicinin ayni okuma hizidir; yeni sayi
#                      uydurulmadi.
# `BASLIK_KELIME_KPS`: BEYAN EDILMIS tasarim esigi (~210 kelime/dk = 3.5
#                      kelime/sn yayin pratigi). Dinleme/okuma testi DEGIL;
#                      parametre olarak disari acildi.
# `BASLIK_ASILI_TAVANI_SN` / `BASLIK_MAKS_SN`: BEYAN EDILMIS ust sinirlar.
BASLIK_MAKS_CPS = 20.0
BASLIK_KELIME_KPS = 3.5
BASLIK_ASILI_TAVANI_SN = 0.8
BASLIK_MAKS_SN = 5.5

# ⚠ K-4 KANCASI (simdi UYGULANMIYOR). `edit_seviyesi` geldiginde bu sozluk
# az|orta|yuksek katsayilarina baglanacak. Varsayilan 1.0 -> GERIYE UYUMLU;
# K-3 tek basina yalnizca GUVENLI KISALTMA yapar.
BASLIK_PROFIL_KATSAYISI = {"varsayilan": 1.0}


def acilis_baslik_suresi(metin: str, *, beat_sure_sn: float,
                         gecikme_sn: float = 0.0,
                         min_gorunme_sn: float = 1.2,
                         katsayi: float = 1.0,
                         maks_cps: float = BASLIK_MAKS_CPS,
                         kelime_kps: float = BASLIK_KELIME_KPS,
                         maks_sn: float = BASLIK_MAKS_SN) -> dict:
    """Acilis basligi/seridi ekranda NE KADAR kalmali? (saf hesap)

    `gecikme_sn`: baslik beat basindan ne kadar SONRA giriyor (plan 0.2 sn).
    ⚠ Uc SERT ust sinir birlikte uygulanir:
      1. `maks_sn` mutlak tavan,
      2. INTRO BEAT'in sonu — baslik beat'i ASLA asamaz,
      3. anlatici cumlesi bittikten sonra en fazla `asili_tavani_sn`.
    ⚠ ALT sinir `min_gorunme_sn`: okunamayacak kadar kisa da olamaz.
    """
    m = str(metin or "")
    kar = len(m.strip())
    kelime = len([w for w in m.split() if w])
    try:
        beat = float(beat_sure_sn)
    except (TypeError, ValueError):
        beat = 0.0
    try:
        gec = max(0.0, float(gecikme_sn))
    except (TypeError, ValueError):
        gec = 0.0
    kat = float(katsayi) if katsayi and float(katsayi) > 0 else 1.0

    # ── OKUMA IHTIYACI: karakter ve kelime bacaklarinin BUYUGU ──
    kar_sn = kar / float(maks_cps) if maks_cps > 0 else 0.0
    kel_sn = kelime / float(kelime_kps) if kelime_kps > 0 else 0.0
    okuma_sn = max(kar_sn, kel_sn) * kat
    istenen = max(float(min_gorunme_sn), okuma_sn)

    # ── UST SINIRLAR ──
    # ⚠ Anlatici cumlesi INTRO BEAT boyunca surer; dolayisiyla "cumle
    # bittikten sonra asili kalma" ile "beat'i asma" AYNI buyukluktur ve
    # tavani SIFIRDIR. `asili_tavani_sn` bu yuzden HESAPTA KULLANILMAZ —
    # yalnizca ESKI/dis kaynakli katmanlari denetleyen kapinin TOLERANSIDIR
    # (`baslik_suresi_denetle`). Olu ayar birakilmadi.
    beat_kalan = max(0.0, beat - gec)            # baslik girisinden beat sonuna
    sinirlar = {"maks_sn": float(maks_sn),
                "intro_beat_kalan": round(beat_kalan, 3),
                "asili_kalma_tavani_sn": 0.0}
    sure = min(istenen, float(maks_sn), beat_kalan)
    sure = max(0.0, round(sure, 3))
    return {
        "sure_sn": sure,
        "karakter": kar, "kelime": kelime,
        "karakter_bacagi_sn": round(kar_sn, 3),
        "kelime_bacagi_sn": round(kel_sn, 3),
        "okuma_ihtiyaci_sn": round(okuma_sn, 3),
        "istenen_sn": round(istenen, 3),
        "katsayi": kat,
        "sinirlar": sinirlar,
        "beat_asiyor": False,                    # tanim geregi: min() ile kesildi
        "kisaltildi": bool(sure + 1e-6 < istenen),
        "min_gorunme_sn": float(min_gorunme_sn),
    }


def baslik_suresi_denetle(*, bas_sn: float, sure_sn: float,
                          beat_bas_sn: float, beat_sure_sn: float,
                          asili_tavani_sn: float = BASLIK_ASILI_TAVANI_SN,
                          maks_sn: float = BASLIK_MAKS_SN) -> dict:
    """Kurulmus bir acilis basligi sinirlari ASIYOR mu? (kapi girdisi)"""
    try:
        b, sr = float(bas_sn), float(sure_sn)
        bb, bs = float(beat_bas_sn), float(beat_sure_sn)
    except (TypeError, ValueError):
        return {"olculdu": False, "neden": "GIRDI-BOZUK"}
    bitis = b + sr
    beat_bitis = bb + bs
    # ⚠ TEK BUYUKLUK: anlatici cumlesi beat boyunca surdugu icin "cumleden
    # sonra asili kalma" = "intro beat'i asma". Iki ad altinda AYNI sayiyi
    # raporlamak yaniltici olurdu; tek ad kullaniliyor.
    asili = round(max(0.0, bitis - beat_bitis), 3)
    tol = float(asili_tavani_sn)
    return {"olculdu": True, "bitis_sn": round(bitis, 3),
            "beat_bitis_sn": round(beat_bitis, 3),
            "asili_kalma_sn": asili,
            "asili_tolerans_sn": tol,
            "maks_sn": float(maks_sn),
            "maks_asimi_sn": round(max(0.0, sr - float(maks_sn)), 3),
            "temiz": (asili <= tol + 1e-6
                      and sr <= float(maks_sn) + 1e-6)}


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
