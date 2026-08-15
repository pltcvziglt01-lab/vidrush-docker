"""PRE-RENDER EDITOR QA — render'a girmeden once plani denetler.

Cikti: PASS / WARN / FAIL + her sorun icin KOD, scene_id/beat_id ve
ONERILEN DUZELTME. Sadece "sorun var" demek yetmez; revizyon dongusu
(Faz D) bu onerilere gore otomatik duzeltme yapacak.

Neden pre-render: 11 Agu'da hatalar ancak render bittikten sonra goruldu ve
her tespit 4 dakika render + $0.20 maliyet demekti. Plan uzerinde yakalanan
hata bedava.

SEVIYE KURALI:
  FAIL = yayinlanamaz (telif, yanlis bilgi, sessiz efekt kaybi, 8 sn ihlali)
  WARN = kalite dususu ama yayinlanabilir
  PASS = temiz
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from . import gramer, kalite_kapisi, motion, ses_gurultu, tipografi

# ⚠ `denetle()` imzasinda `kalite_kapisi` adinda BOOL bir parametre var ve
# modul adini GOLGELIYOR. Modul fonksiyonlarina o kapsamdan erisebilmek
# icin golgelenmeyen bir takma ad tutuluyor.
_KK = kalite_kapisi
_SG = ses_gurultu

try:                          # ⚠ I-47: paket disi modul; yoksa kapi SESSIZ
    import medya_kapisi as medya_kapisi_modulu
except Exception:             # noqa: BLE001
    medya_kapisi_modulu = None
from .profil import OLCULEN, EditProfili, VARSAYILAN

# ── Sorun kodlari ve seviyeleri ──
# ⚠ FAZ Y-6 — UST SEVIYE KURGU ESIKLERI (kullanici karari, BAGLAYICI).
# Referans: `profil.gecis_dagilimi` j-cut %4 + l-cut %4 (~%8 gecis) —
# esik UYDURULMADI, mevcut profil hedefinden turetildi.
JL_EN_AZ = 2                 # yuksek kurgu presetinde en az 2 gercek J/L-cut
JL_ASGARI_SURE_SN = 45.0     # bu sureden kisa videoda J/L kapisi aranmaz
SFX_TAVAN_DK = 6.0           # SFX/dakika ust siniri (kota 6.0 sn ile tutarli)
SFX_ASGARI_SURE_SN = 60.0    # bu sureden uzun videoda hic SFX yoksa uyar

FAIL_KODLARI = {
    "LISANS-EKSIK", "LISANS-ATIF-EKSIK", "FACT-BAGLANTI-YOK",
    "EFEKT-SESSIZ-KAYIP", "SHOT-TAVAN-IHLAL", "ENTITY-DONEM",
    "MEDYA-KAPSAM-YOK", "SES-LUFS-HEDEF-YOK", "TIPO-KONTRAST",
    # ── Faz I-14 kalite kapilari ──
    "KALITE-BASLIK-KIRPIK", "KALITE-BASLIK-TASMA", "KALITE-MEDYA-TEKRAR",
    "KALITE-RITIM-SABIT", "KALITE-OLU-FINAL",
    # ── Faz I-16: altyazi + kunye + guvenli alan ──
    "KALITE-YAZI-CAKISMA", "KALITE-GUVENLI-ALAN",
    # ── Faz I-17: optik duraganlik ──
    "KALITE-OPTIK-DURGUN",
    # ── Faz I-22: medyasiz beat ──
    "KALITE-MEDYASIZ-BEAT",
    # ── Faz I-24: motion cesitliligi OLCULEBILIR KAPI ──
    "KALITE-MOTION-ACILIS-KAPANIS", "KALITE-MOTION-ISLEV-TEKRAR",
    # ── Faz I-31: gorunur kunye eksik olamaz ──
    "KALITE-KUNYE-EKSIK",
    # ── Faz I-37: beat->scene->fact->asset bagi KOPAMAZ ──
    "KALITE-BAG-KOPUK",
    # ── Faz I-38: yazi spec'i SAHNE PENCERESININ disinda baslayamaz ──
    "KALITE-YAZI-SAHNE-DISI",
    # ── Faz I-39: yazi ile altyazi arasinda NEFES BOSLUGU zorunlu ──
    "KALITE-YAZI-NEFES-YOK",
    # ── Faz I-27: kamera punch'i kaynagi BUYUTEMEZ ──
    "KALITE-PUNCH-BUYUTME",
    # ── Faz I-46: BEKLENEN optik hareket esigin altinda ──
    # ⚠ Bu kod FAIL'dir cunku hukum OLCULEN hata payiyla veriliyor:
    # yalnizca `beklenen x (1 + en_kotu_hata)` HALA esigin altindaysa uretilir
    # (12 kontrollu + 6 tutulan noktada YANLIS FAIL yok). Belirsiz bant
    # `warn` seviyesinde kalir -> EMIN DEGILSEN ENGELLEME korunur.
    "KALITE-OPTIK-DURGUN-BEKLENEN",
    # ── Faz K-1: B-ROLL GORSEL DILI ──
    # ⚠ Kamera-hareketi bacagi (I-24) gercek VIDEO cekimlerde MUAF; bosluk
    # bos birakilmadi, yerini bu kod aldi. Yapisal kosul, sayisal esik YOK.
    "KALITE-BROLL-CESITLILIK",
    # ── Faz K-2: arka plan ugultu/rumble/wind + kaynak ses sizintisi ──
    # ⚠ Olcum remote worker'dan SAYI olarak gelir; verilmezse HUKUM YOK.
    "KALITE-SES-GURULTU", "KALITE-KAYNAK-SES-SIZINTI",
    # ── Faz K-3: acilis basligi/seridi ekranda ASILI kalamaz ──
    "KALITE-BASLIK-SURESI",
}

# I-14 kapisinin urettigi kodlar. Kapi KAPALIYKEN bunlarin HICBIRI uretilmez;
# olcumler yine de `olcumler["kalite"]`e yazilir (gizlenmiyor, yalniz hukum
# verilmiyor). Boylece varsayilan yolun PASS/WARN/FAIL karari BIT-BIT ayni kalir.
KALITE_KODLARI = ("KALITE-BROLL-CESITLILIK",
                  "KALITE-SES-GURULTU", "KALITE-KAYNAK-SES-SIZINTI",
                  "KALITE-BASLIK-SURESI",
                  "KALITE-BASLIK-KIRPIK", "KALITE-BASLIK-TASMA",
                  "KALITE-MEDYA-TEKRAR", "KALITE-RITIM-SABIT",
                  "KALITE-OLU-FINAL", "KALITE-MEDYA-BENZER-OLCULEMEDI",
                  "KALITE-YAZI-CAKISMA", "KALITE-GUVENLI-ALAN",
                  "KALITE-ALTYAZI-OKUNMAZ", "KALITE-OPTIK-DURGUN",
                  "KALITE-MOTION-TEKRAR", "KALITE-GECIS-TEKDUZE",
                  "KALITE-MEDYASIZ-BEAT",
                  "KALITE-MOTION-ACILIS-KAPANIS",
                  "KALITE-MOTION-ISLEV-TEKRAR",
                  "KALITE-PUNCH-BUYUTME", "KALITE-KUNYE-EKSIK",
                  "KALITE-BAG-KOPUK", "KALITE-YAZI-SAHNE-DISI",
                  "KALITE-YAZI-NEFES-YOK",
                  # ── Faz I-44: gorselin UZAMSAL ENERJISI ──
                  # ⚠ FAIL_KODLARI'na BILEREK girmiyor: `EMIN DEGILSEN
                  # ENGELLEME` (edinim.py ile ayni sozlesme). Enerji TUM
                  # karede olculur, oysa `kadraj`/`punch` kaynagi KIRPABILIR
                  # ve kirpilan bolgenin enerjisi farkli olabilir. Kirpma
                  # bolgesinde olcmek AYRI ve OLCULMEMIS bir atomdur -> bu
                  # kapi RENDER'I BLOKLAMAZ, yalniz olculen riski GORUNUR
                  # kilar (render sonrasi `KALITE-OPTIK-DURGUN` zaten FAIL).
                  "KALITE-MEDYA-DUSUK-ENERJI",
                  "KALITE-MEDYA-ENERJI-OLCULEMEDI",
                  # ── Faz I-45: esigin KALIBRASYON ALANI disi ──
                  # ⚠ Esik TEK bir kamera konfigurasyonunda (gezinme
                  # 0.0577 /sn) olculdu. Daha hizli gezinen cekimde hukum
                  # VERILMEZ; sessizce de gecilmez -> ayri bilgi kodu.
                  "KALITE-MEDYA-ENERJI-KAPSAM-DISI",
                  # ── Faz I-46: risk OPTIK BIRIMDE ──
                  "KALITE-OPTIK-DURGUN-BEKLENEN",
                  # ── Faz I-47: donem uyusmazligi (TERS YON) ──
                  # ⚠ FAIL_KODLARI'na BILEREK girmiyor: sinyal yalniz DONEM
                  # celiskisini gorur (yer/ozne/tur uyusmazligi ULASILAMAZ)
                  # ve aday ELENMEZ — I-35'te olculdu ki nadir bir kalite
                  # kusurunu sik bir MEDYASIZ-BEAT ile takas etmek yanlis.
                  "KALITE-SEMANTIK-DONEM")


@dataclass
class Sorun:
    kod: str
    seviye: str = "warn"            # fail | warn | bilgi
    scene_id: str = ""
    beat_id: str = ""
    detay: str = ""
    oneri: str = ""

    def sozluk(self) -> dict:
        return {"kod": self.kod, "seviye": self.seviye, "scene_id": self.scene_id,
                "beat_id": self.beat_id, "detay": self.detay, "oneri": self.oneri}


@dataclass
class QaSonucu:
    durum: str = "PASS"
    sorunlar: list = field(default_factory=list)
    olcumler: dict = field(default_factory=dict)

    def ekle(self, s: Sorun) -> None:
        if s.kod in FAIL_KODLARI and s.seviye != "bilgi":
            s.seviye = "fail"
        self.sorunlar.append(s)

    def sonuclandir(self) -> "QaSonucu":
        if any(s.seviye == "fail" for s in self.sorunlar):
            self.durum = "FAIL"
        elif any(s.seviye == "warn" for s in self.sorunlar):
            self.durum = "WARN"
        else:
            self.durum = "PASS"
        return self

    def sozluk(self) -> dict:
        return {"durum": self.durum,
                "fail": sum(1 for s in self.sorunlar if s.seviye == "fail"),
                "warn": sum(1 for s in self.sorunlar if s.seviye == "warn"),
                "olcumler": self.olcumler,
                "sorunlar": [s.sozluk() for s in self.sorunlar]}


def denetle(*, beat_plani, cekimler: list, yazi_katmanlari: list,
            motion_specler: list, ses_plani, adaylar_index: dict,
            profil_: Optional[EditProfili] = None,
            beklenen_ulke: str = "", beklenen_donem: str = "",
            arastirma_fact_idler: Optional[set] = None,
            kare_olcu: Optional[tuple] = None,
            anlatim_bitis_sn: Optional[float] = None,
            benzerlik_okuyucu=None,
            enerji_okuyucu=None,
            kare_okuyucu=None,
            ses_gurultu_olcumu=None,
            altyazi_kupleri: Optional[list] = None,
            kunye_kararlari: Optional[list] = None,
            kalite_kapisi: bool = False) -> QaSonucu:
    """Pre-render denetim.

    Faz I-14 ek parametreleri (hepsi OPSIYONEL, varsayilan davranis degismez):
      `kare_olcu`        : render'in GERCEK (genislik, yukseklik) olcusu.
                           Verilmezse profilin nominal olcusu kullanilir.
                           ⚠ I-13'te profil 1920 diyordu, render 1280'e
                           yapiliyordu; baslik kirpilmasinin kok nedeni buydu.
      `anlatim_bitis_sn` : anlatim sesinin bittigi an (olu final olcumu icin).
      `benzerlik_okuyucu`: (yolA, yolB) -> 0..1. Verilmezse gorsel benzerlik
                           `olculemedi` yazilir; "benzer medya yok" DENMEZ.
      `ses_gurultu_olcumu`: remote worker'in OLCTUGU SAYILAR
                           ({"olcum": {...}, "dogrulama": {...}}). Bu modul
                           SES ACMAZ; verilmezse arka plan gurultusu
                           `olculemedi` yazilir ve "temiz" DENMEZ (K-2).
      `kare_okuyucu`     : (yol) -> dosyanin KARE SAYISI ya da None.
                           ⚠ FAZ J-2a: bu modul DOSYA ACMAZ; olcer
                           DISARIDAN verilir. Verilmezse medya turu
                           `olculemedi` yazilir; "statik fotograftir"
                           DENMEZ. YALNIZ RAPOR — kapi/esik URETMEZ.
      `enerji_okuyucu`   : (yol) -> uzamsal enerji (0-255) ya da None.
                           ⚠ FAZ I-44: bu modul GORSEL ACMAZ; olcer
                           DISARIDAN verilir (`benzerlik_okuyucu` ile ayni
                           sozlesme). Verilmezse enerji `olculemedi` yazilir;
                           "enerjisi yeterli" DENMEZ.
      `altyazi_kupleri`  : mutlak zamanli altyazi kupleri. Verilirse altyazi
                           bandi REZERVE sayilir, okunabilirlik olculur ve
                           kunye/baslik ile cakismasi denetlenir.
      `kalite_kapisi`    : False iken KALITE-* kodlari URETILMEZ, yalnizca
                           olcum yazilir. True iken kapi gercekten hukum verir.
    """
    p = profil_ or VARSAYILAN
    q = QaSonucu()

    # ⚠ HATA DUZELTMESI (R-1d-a deploy'unda yakalandi): K-1/K-2/K-3
    # atomlari bulgularini `_ekle(...)` ile yaziyordu, ama o yardimci
    # YALNIZCA `_kalite_denetle()` icinde tanimliydi. `denetle()` icinden
    # cagrilinca `NameError: name '_ekle' is not defined` firlatiyordu —
    # yani KALITE-BROLL-CESITLILIK / KALITE-BASLIK-SURESI /
    # KALITE-KAYNAK-SES-SIZINTI / KALITE-SES-GURULTU kapilari bir ihlal
    # bulunca RAPOR ETMEK yerine PRE-QA'yi COKERTIYORDU. Ihlal yokken kod
    # yolu hic calismadigi icin testlerden gecmisti.
    # `deploy.sh`in pyflakes taramasi bunu "undefined name" olarak yakaladi
    # ve deploy'u DURDURDU (koruma calisti).
    # ⚠ EN KUCUK DUZELTME: cagri yerleri DEGISTIRILMEDI; `_kalite_denetle`
    # ile AYNI imzada yerel bir yardimci tanimlaniyor.
    def _ekle(kod, seviye, detay, oneri, scene_id="", beat_id=""):
        q.ekle(Sorun(kod, seviye, scene_id, beat_id, detay, oneri))

    beatler = beat_plani.beatler
    toplam = beat_plani.toplam_sn or sum(b.sure_sn for b in beatler)

    # ═══ 1) RITIM / PACING ═══
    sureler = [b.sure_sn for b in beatler]
    if sureler:
        ort = sum(sureler) / len(sureler)
        kisa = sum(1 for s in sureler if s < 4.0) / len(sureler)
        q.olcumler["pacing"] = {
            "beat": len(sureler), "ortalama_sn": round(ort, 2),
            "en_kisa": round(min(sureler), 2), "en_uzun": round(max(sureler), 2),
            "kisa_cekim_orani": round(kisa, 3),
            "referans_kisa_orani": OLCULEN["kisa_cekim_orani"],
            "histogram": beat_plani.sure_histogrami(),
        }
        for b in beatler:
            if b.sure_sn > p.shot_kesin_tavan_sn:
                q.ekle(Sorun("SHOT-TAVAN-IHLAL", "fail", b.scene_id, b.beat_id,
                             f"{b.sure_sn} sn > {p.shot_kesin_tavan_sn} sn tavani",
                             "beat'i ikiye bol ya da anlatimi kisalt"))
            elif b.sure_sn < p.shot_min_sn - 0.01:
                q.ekle(Sorun("SHOT-COK-KISA", "warn", b.scene_id, b.beat_id,
                             f"{b.sure_sn} sn < {p.shot_min_sn} sn",
                             "komsu beat ile birlestir"))
        # Tekduzelik: tum sureler birbirine cok yakinsa "metronom" hissi
        if len(sureler) >= 4:
            yayilim = max(sureler) - min(sureler)
            if yayilim < 0.6:
                q.ekle(Sorun("PACING-TEKDUZE", "warn", detay=
                             f"tum cekimler {min(sureler)}-{max(sureler)} sn "
                             f"arasinda (yayilim {yayilim:.2f})",
                             oneri="bilgi yogunlugu farkini sureye yansit"))
        if abs(kisa - OLCULEN["kisa_cekim_orani"]) > 0.25:
            q.ekle(Sorun("PACING-KISA-ORAN", "warn", detay=
                         f"4 sn alti oran %{kisa*100:.0f}, referans "
                         f"%{OLCULEN['kisa_cekim_orani']*100:.0f}",
                         oneri="beat bolme esigini ayarla"))

    # ═══ 2) HOOK / PERDE ═══
    ilk8 = [b for b in beatler if b.bas_sn < 8.0]
    if not any(b.islev == "hook" for b in ilk8):
        q.ekle(Sorun("HOOK-YOK", "warn", detay="ilk 8 sn'de hook islevi yok",
                     oneri="ilk cumleyi soru/carpici ifadeye cevir"))
    perdeler = {b.perde for b in beatler}
    if len(perdeler) < 3 and toplam > 20:
        q.ekle(Sorun("PERDE-EKSIK", "warn",
                     detay=f"perdeler: {sorted(perdeler)} (3 perde bekleniyor)",
                     oneri="senaryoyu acilis/gelisme/kapanis olarak dengele"))
    q.olcumler["perde"] = {p2: sum(1 for b in beatler if b.perde == p2)
                           for p2 in ("acilis", "gelisme", "kapanis")}
    q.olcumler["islev"] = {}
    for b in beatler:
        q.olcumler["islev"][b.islev] = q.olcumler["islev"].get(b.islev, 0) + 1

    # ═══ 3) MEDYA KAPSAMI / LISANS / IZLENEBILIRLIK ═══
    fallback_n = sum(1 for c in cekimler if c.kaynak_turu == "fallback")
    q.olcumler["kapsam"] = {
        "cekim": len(cekimler), "medya": len(cekimler) - fallback_n,
        "fallback": fallback_n,
        "kapsam_orani": round((len(cekimler) - fallback_n) /
                              max(1, len(cekimler)), 3)}
    if cekimler and fallback_n == len(cekimler):
        q.ekle(Sorun("MEDYA-KAPSAM-YOK", "fail",
                     detay="hicbir cekimde gercek medya yok",
                     oneri="sorgu merdivenini genislet ya da varlik yukle"))
    for c in cekimler:
        if c.kaynak_turu != "medya":
            continue
        aday = adaylar_index.get(c.asset_id)
        if aday is None:
            q.ekle(Sorun("LISANS-EKSIK", "fail", c.scene_id, c.beat_id,
                         f"asset {c.asset_id} manifestte yok",
                         "varligi medya manifestinden dogrula"))
            continue
        if not aday.get("render_kullanilabilir"):
            q.ekle(Sorun("LISANS-EKSIK", "fail", c.scene_id, c.beat_id,
                         f"{c.asset_id}: render_kullanilabilir=False "
                         f"({aday.get('red_nedeni')})",
                         "lisansi acik bir alternatif sec"))
        if aday.get("atif_gerekli") and not aday.get("atif_metni"):
            q.ekle(Sorun("LISANS-ATIF-EKSIK", "fail", c.scene_id, c.beat_id,
                         f"{c.asset_id}: atif gerekli ama atif metni yok",
                         "eser sahibini doldur ya da atifsiz lisansli alternatif sec"))
        if not c.fact_id:
            q.ekle(Sorun("FACT-BAGLANTI-YOK", "fail", c.scene_id, c.beat_id,
                         "cekim hicbir fact_id'ye bagli degil",
                         "beat'i bir iddiaya bagla"))
        elif arastirma_fact_idler and c.fact_id not in arastirma_fact_idler:
            q.ekle(Sorun("FACT-BAGLANTI-YOK", "fail", c.scene_id, c.beat_id,
                         f"fact_id {c.fact_id} arastirma manifestinde yok",
                         "gecerli bir fact_id ata"))

    # ═══ 4) SUREKLILIK / TEKRAR ═══
    for s in gramer.sureklilik_denetimi(cekimler):
        q.ekle(Sorun(s["kod"], s.get("seviye", "warn"), beat_id=s.get("beat_id", ""),
                     detay=s["detay"], oneri="alternatif varlik/kadraj/hareket sec"))
    for s in gramer.entity_denetimi(cekimler, beklenen_ulke=beklenen_ulke,
                                    beklenen_donem=beklenen_donem):
        q.ekle(Sorun(s["kod"], s.get("seviye", "warn"), beat_id=s.get("beat_id", ""),
                     detay=s["detay"], oneri="yer/donem uyumlu varlik sec"))
    # Saglayici tekelleşmesi (Faz B kotasinin kurgu karsiligi)
    sag: dict = {}
    for c in cekimler:
        if c.saglayici:
            sag[c.saglayici] = sag.get(c.saglayici, 0) + 1
    medya_n = sum(sag.values())
    q.olcumler["saglayici"] = sag
    if medya_n:
        en = max(sag.values())
        oran = en / medya_n
        q.olcumler["tek_saglayici_orani"] = round(oran, 3)
        if oran > 0.40:
            q.ekle(Sorun("SAGLAYICI-TEKEL", "warn",
                         detay=f"tek saglayici %{oran*100:.0f} (tavan %40): "
                               f"{max(sag, key=sag.get)}",
                         oneri="alternatif saglayici adayi kullan ya da "
                               "coverage_gap birak"))

    # ═══ 4b) MEDYA TURU DAGILIMI (Faz J-2a — YALNIZ RAPOR) ═══
    # ⚠ HUKUM YOK: hicbir Sorun URETILMEZ, hicbir esik ENFORCE EDILMEZ.
    # Okuyucu yoksa `olculemedi` yazilir; statik VARSAYILMAZ.
    _j2_sahneler = [
        {"beat_id": getattr(c_, "beat_id", ""),
         "kaynak_turu": getattr(c_, "kaynak_turu", ""),
         "asset_id": getattr(c_, "asset_id", ""),
         "saglayici": getattr(c_, "saglayici", ""),
         "cekim_turu": getattr(c_, "cekim_turu", ""),
         # ⚠ K-2: politika "sifir"; aday ACIKCA baska bir kanal beyan
         # ederse (ornegin bir saglayici adaptoru) kapi YAKALAR.
         "ses_kanali": str((adaylar_index.get(getattr(c_, "asset_id", ""))
                            or {}).get("ses_kanali")
                           or _SG.KAYNAK_SES_POLITIKASI),
         # ⚠ K-1: B-ROLL GORSEL DILI bacagi icin gerekli iki alan.
         "islev": getattr(b_, "islev", ""),
         "medya_turu": str((adaylar_index.get(getattr(c_, "asset_id", ""))
                            or {}).get("medya_turu") or "image"),
         "lisans": ((adaylar_index.get(getattr(c_, "asset_id", "")) or {})
                    .get("lisans") or ""),
         "medya_yolu": ((adaylar_index.get(getattr(c_, "asset_id", "")) or {})
                        .get("yerel_yol") or ""),
         "sure_sn": getattr(b_, "sure_sn", 0.0)}
        for c_, b_ in zip(cekimler, beat_plani.beatler)]
    q.olcumler["medya_turu"] = _KK.medya_turu_ozeti(
        _j2_sahneler, kare_okuyucu=kare_okuyucu,
        motion_specler=motion_specler)

    # ═══ 4c) B-ROLL / CUTAWAY CESITLILIGI (Faz J-3 — YALNIZ RAPOR) ═══
    # ⚠ HUKUM YOK: Sorun URETILMEZ, esik ENFORCE EDILMEZ, SECIM DEGISMEZ.
    # Gercek video orani J-2a olcumunden OKUNUR; yeniden hesaplanmaz.
    _broll = _KK.broll_cesitliligi_ozeti(
        _j2_sahneler, medya_turu_ozeti_=q.olcumler["medya_turu"])
    q.olcumler["broll_cesitliligi"] = _broll
    # ⚠ K-1 KAPISI. I-24'un ISLEV kuralinin video karsiligi; kamera bacagi
    # video cekimlerde MUAF tutuldugu icin bosluk BURADA kapaniyor.
    # Kapi yalnizca `kalite_kapisi` ACIKKEN hukum verir (KALITE_KODLARI).
    if kalite_kapisi:
        for _bt in (_broll.get("video_islev_tur_tekrari") or []):
            _ekle("KALITE-BROLL-CESITLILIK", "fail",
                  f"'{_bt['islev']}' islevindeki iki VIDEO cekim ayni cekim "
                  f"turunu aliyor: {_bt['cekim_turu']} "
                  f"(sahne {_bt['ilk_indeks']} ve {_bt['indeks']})",
                  "ayni islevdeki B-roll cekimlerine FARKLI cekim turu ata "
                  "(genis/yakin/detay) ya da farkli bir kaynak sec",
                  beat_id=_bt.get("beat_id", ""))
        for _bt in (_broll.get("video_pencere_tur_tekrari") or []):
            _ekle("KALITE-BROLL-CESITLILIK", "warn",
                  f"son {_bt['pencere']} VIDEO cekimde ayni cekim turu "
                  f"tekrar etti: {_bt['cekim_turu']} (sahne {_bt['indeks']})",
                  "B-roll cekim turunu cesitlendir",
                  beat_id=_bt.get("beat_id", ""))

    # ═══ 4c2) ACILIS BASLIK/SERIT SURESI (Faz K-3) ═══
    # ⚠ Acilis basligi anlatici cumlesi bittikten sonra ekranda ASILI
    # kalamaz ve INTRO BEAT'i asamaz. Olcum PLANDAN turer (medya YOK).
    _bas_kayit = []
    _beat_ind = {getattr(b3, "beat_id", ""): b3 for b3 in (beatler or [])}
    for _k3 in (yazi_katmanlari or []):
        if getattr(_k3, "ad", "") != "chapter-title":
            continue
        _b3 = _beat_ind.get(getattr(_k3, "fact_id", ""))
        if _b3 is None:
            _b3 = (beatler or [None])[0]
        if _b3 is None:
            continue
        _d3 = tipografi.baslik_suresi_denetle(
            bas_sn=getattr(_k3, "bas_sn", 0.0),
            sure_sn=getattr(_k3, "sure_sn", 0.0),
            beat_bas_sn=getattr(_b3, "bas_sn", 0.0),
            beat_sure_sn=getattr(_b3, "sure_sn", 0.0))
        if not _d3.get("olculdu"):
            continue
        _bas_kayit.append(dict(_d3, metin=str(getattr(_k3, "metin", ""))[:40]))
        if kalite_kapisi and not _d3["temiz"]:
            _ekle("KALITE-BASLIK-SURESI", "fail",
                  f"acilis basligi anlatim bittikten sonra "
                  f"{_d3['asili_kalma_sn']} sn ASILI kaliyor "
                  f"(tolerans {_d3['asili_tolerans_sn']} sn, "
                  f"tavan {_d3['maks_sn']} sn)",
                  "sureyi metnin okuma ihtiyacindan turet; intro beat'i asma")
    # ⚠ `olcum` sozlugu bu noktada HENUZ YOK (kalite bolumunde kuruluyor);
    # olcum dogrudan `q.olcumler`e yazilir — K-1/K-2 ile ayni desen.
    q.olcumler["baslik_suresi"] = {
        "olculen": len(_bas_kayit), "kayitlar": _bas_kayit,
        "temiz": all(k["temiz"] for k in _bas_kayit)}

    # ═══ 4d) SES: KAYNAK SESI SIFIR + ARKA PLAN UGULTU (Faz K-2) ═══
    # ⚠ Bu modul SES ACMAZ. Kaynak-ses sozlesmesi PLANDAN, gurultu karari
    # ise DISARIDAN verilen SAYILARDAN turer. Olcum yoksa HUKUM YOK.
    _ks = _SG.kaynak_ses_sozlesmesi(_j2_sahneler)
    q.olcumler["kaynak_ses"] = _ks
    if kalite_kapisi:
        for _ih in (_ks.get("ihlal") or []):
            _ekle("KALITE-KAYNAK-SES-SIZINTI", "fail",
                  f"kaynak video sesi SIFIR degil: "
                  f"ses_kanali={_ih['ses_kanali']!r}",
                  "harici klibin kendi sesi mikse GIREMEZ; kanali sifirla",
                  beat_id=_ih.get("beat_id", ""))
    _sgo = ses_gurultu_olcumu if isinstance(ses_gurultu_olcumu, dict) else {}
    _gk = _SG.gurultu_karari(olcum=_sgo.get("olcum") or {},
                             dogrulama=_sgo.get("dogrulama"))
    q.olcumler["ses_gurultu"] = {
        "olcum": _sgo.get("olcum") or {"olculdu": False,
                                       "neden": "OLCUM-VERILMEDI"},
        "dogrulama": _sgo.get("dogrulama"),
        "karar": _gk,
        "filtre_onerisi": _SG.filtre_profili_oner(_sgo.get("olcum") or {}),
    }
    if kalite_kapisi and _gk.get("kod"):
        _ekle(_gk["kod"], _gk["seviye"], _gk["neden"],
              "gurultuyu KAYNAKTA gider ya da guvenli filtre profilini "
              "remote worker'da uygula; konusma netligini bozan denoise YOK")

    # ═══ 5) EFEKT YOGUNLUGU / RENDERABILITY ═══
    beat_efekt: dict = {}
    for sp in motion_specler:
        bid = sp.get("beat_id", "")
        beat_efekt[bid] = beat_efekt.get(bid, 0) + 1
        ad = sp.get("ad", "")
        renderer = sp.get("renderer", "")
        if renderer not in ("ffmpeg", "remotion"):
            q.ekle(Sorun("EFEKT-SESSIZ-KAYIP", "fail", beat_id=bid,
                         detay=f"{ad}: renderer beyani yok",
                         oneri="renderer=ffmpeg|remotion belirt"))
        if renderer == "remotion" and not sp.get("remotion_zorunlu") \
                and not sp.get("fallback"):
            q.ekle(Sorun("EFEKT-SESSIZ-KAYIP", "fail", beat_id=bid,
                         detay=f"{ad}: remotion isteniyor ama fallback yok",
                         oneri="ffmpeg fallback spec'i ekle"))
        if sp.get("remotion_zorunlu") and not sp.get("fallback"):
            q.ekle(Sorun("EFEKT-REMOTION-ZORUNLU", "bilgi", beat_id=bid,
                         detay=f"{ad}: yalniz Remotion'da uretilebilir",
                         oneri="sahne Remotion'a yonlendirilecek"))
    # ⚠ TABAN KATMAN PAYI: her cekimde ZORUNLU 5 spec var — kamera, grain,
    # vinyet, grade ve gecis. Esik yalnizca DEKORATIF efektleri saymali.
    # Ilk surumde +3 pay birakmistim ve saglikli plan bile "EFEKT-YOGUN"
    # uyarisi uretiyordu (onizleme kosusunda goruldu).
    TABAN_KATMAN = 5
    asiri = {k: v for k, v in beat_efekt.items()
             if v > p.motion.maks_es_zamanli_efekt + TABAN_KATMAN}
    for bid, n in asiri.items():
        q.ekle(Sorun("EFEKT-YOGUN", "warn", beat_id=bid,
                     detay=f"{n} efekt (dekoratif tavan "
                           f"{p.motion.maks_es_zamanli_efekt} + taban "
                           f"{TABAN_KATMAN})",
                     oneri="dekoratif efektleri kaldir"))
    q.olcumler["efekt"] = {"toplam": len(motion_specler),
                           "beat_basina_ort": round(
                               len(motion_specler) / max(1, len(beatler)), 2)}

    # ═══ 6) GECIS KOTUYE KULLANIMI ═══
    gecisler = [sp for sp in motion_specler
                if sp.get("parametre", {}).get("tur") in motion.GECIS_GEREKCESI]
    seyrek = [g for g in gecisler
              if g["parametre"]["tur"] in motion.SEYREK_GECISLER]
    q.olcumler["gecis"] = {"toplam": len(gecisler), "seyrek": len(seyrek)}
    if gecisler:
        sert = sum(1 for g in gecisler if g["parametre"]["tur"] == "hard-cut")
        oran = sert / len(gecisler)
        q.olcumler["gecis"]["hard_cut_orani"] = round(oran, 3)
        if oran < 0.55:
            q.ekle(Sorun("GECIS-ASIRI", "warn",
                         detay=f"sert kesme orani %{oran*100:.0f} "
                               f"(referans %{OLCULEN['sert_kesme_orani']*100:.0f})",
                         oneri="efektli gecisleri azalt"))
        if len(seyrek) / len(gecisler) > 0.10:
            q.ekle(Sorun("GECIS-SEYREK-ASIRI", "warn",
                         detay=f"{len(seyrek)}/{len(gecisler)} seyrek gecis "
                               f"(whip/glitch/zoom-through tavan %10)",
                         oneri="bu gecisleri gerekceli tek anlarda kullan"))

    # ═══ 7) TIPOGRAFI ═══
    tipo_sorun = 0
    for k in yazi_katmanlari:
        for s in tipografi.guvenli_alan_kontrol(k, p=p):
            tipo_sorun += 1
            q.ekle(Sorun(s["kod"], "warn" if s["kod"] != "TIPO-KONTRAST" else "fail",
                         beat_id="", detay=f"{k.ad}: {s['detay']}",
                         oneri="punto kucult / satir bol / konum degistir"))
    # Cakisma: cozulmemis olan var mi?
    _, cakisma_rapor = tipografi.cakisma_coz(list(yazi_katmanlari), p=p)
    for r in cakisma_rapor:
        if r["kod"] == "TIPO-CAKISMA-DUSURULDU":
            q.ekle(Sorun("TIPO-CAKISMA", "warn", detay=r["detay"],
                         oneri="katman sayisini azalt ya da zamanlamayi ayir"))
    q.olcumler["tipografi"] = {"katman": len(yazi_katmanlari),
                               "sorun": tipo_sorun}

    # ═══ 8) SES ═══
    _sfx_n = sum(1 for o in ses_plani.olaylar if o.tur == "sfx")
    _jl_n = sum(1 for o in ses_plani.olaylar if o.tur in ("j-cut", "l-cut"))
    q.olcumler["ses"] = {
        "lufs_hedef": ses_plani.lufs_hedef,
        "tepe_tavan": ses_plani.tepe_tavan,
        "sfx_dakikada": ses_plani.sfx_yogunlugu(toplam),
        "sfx_sayisi": _sfx_n,
        "jl_sayisi": _jl_n,
        "on_zincir_adim": len(ses_plani.on_zincir),
        "ducking_araligi": len(ses_plani.ducking_zarfi)}

    # ⚠ FAZ Y-6 — UST SEVIYE KURGU: J/L-CUT ve OLCULU SFX KAPILARI.
    # Kullanici karari (BAGLAYICI): bunlar tam PASS icin ZORUNLU.
    # ⚠ Kapilar YALNIZ olcum degil URETIM de gerektirir: `hizli_render`
    # J/L gecislerinde ses capraz gecisini kisaltir (Y6-JL-URETIM) ve
    # `pipeline.sfx_bindir` SFX'i gercekten bindirir.
    if toplam >= JL_ASGARI_SURE_SN and _jl_n < JL_EN_AZ:
        q.ekle(Sorun("KURGU-JL-YOK", "warn",
                     detay=f"{_jl_n} J/L-cut (en az {JL_EN_AZ} beklenir)",
                     oneri="kanit/vurgu beat'inde j-cut, sonuc beat'inde "
                           "l-cut planla"))
    # SFX bandi CIFT TARAFLI: ne sessiz ne asiri.
    _sfx_dk = ses_plani.sfx_yogunlugu(toplam)
    if toplam >= SFX_ASGARI_SURE_SN and _sfx_n == 0:
        q.ekle(Sorun("SES-SFX-BANT", "warn",
                     detay=f"hic SFX yok ({toplam:.0f} sn)",
                     oneri="hook/kanit/donus islevlerine olculu SFX ekle"))
    elif _sfx_dk > SFX_TAVAN_DK:
        q.ekle(Sorun("SES-SFX-BANT", "warn",
                     detay=f"{_sfx_dk}/dk > tavan {SFX_TAVAN_DK}/dk",
                     oneri="SFX kotasini seyrelt"))
    if ses_plani.lufs_hedef != p.lufs_hedef:
        q.ekle(Sorun("SES-LUFS-HEDEF-YOK", "fail",
                     detay=f"plan {ses_plani.lufs_hedef}, profil {p.lufs_hedef}",
                     oneri="ses planini profil hedefine hizala"))
    if not any(a.get("filtre") == "acompressor" for a in ses_plani.on_zincir):
        q.ekle(Sorun("SES-KOMPRESOR-YOK", "warn",
                     detay="normalizasyon oncesi kompresyon yok — hedef "
                           "tutmayabilir (11 Agu: -15.6 LUFS)",
                     oneri="on zincire acompressor ekle"))
    for u in ses_plani.uyarilar:
        q.ekle(Sorun("SES-UYARI", "warn", detay=u, oneri="ses planini gozden gecir"))

    for u in beat_plani.uyarilar:
        kod = u.split(":")[0] if ":" in u else "BEAT-UYARI"
        q.ekle(Sorun(kod, "warn" if "TAVAN" not in kod else "fail", detay=u,
                     oneri="beat planini duzelt"))

    # ═══ 9) FAZ I-14 KALITE KAPILARI ═══
    # ⚠ OLCUM HER ZAMAN yapilir ve `olcumler["kalite"]`e yazilir; HUKUM
    # yalnizca `kalite_kapisi=True` iken verilir. Boylece kapali yolda
    # PASS/WARN/FAIL karari degismez ama olcum de gizlenmez.
    _kalite_denetle(q, beatler=beatler, cekimler=cekimler,
                    yazi_katmanlari=yazi_katmanlari,
                    adaylar_index=adaylar_index, p=p, kare_olcu=kare_olcu,
                    anlatim_bitis_sn=anlatim_bitis_sn, toplam=toplam,
                    benzerlik_okuyucu=benzerlik_okuyucu,
                    enerji_okuyucu=enerji_okuyucu,
                    altyazi_kupleri=altyazi_kupleri,
                    motion_specler=motion_specler,
                    kunye_kararlari=kunye_kararlari, acik=kalite_kapisi)

    return q.sonuclandir()


def _kalite_denetle(q: QaSonucu, *, beatler, cekimler, yazi_katmanlari,
                    adaylar_index, p, kare_olcu, anlatim_bitis_sn, toplam,
                    benzerlik_okuyucu, acik: bool,
                    enerji_okuyucu=None,
                    altyazi_kupleri=None, motion_specler=None,
                    kunye_kararlari=None) -> None:
    """I-14 olcumlerini kos ve (kapi acikken) sorun uret. ASLA COKMEZ."""
    kk = kalite_kapisi
    try:
        # Baslik bandi YATAY tasar; yukseklik bu olcumde kullanilmaz.
        genislik = int((kare_olcu or (p.genislik,))[0] or p.genislik)
    except (TypeError, ValueError, IndexError):
        genislik = p.genislik
    olcum: dict = {"kare_genislik": genislik,
                   "kare_olcu_verildi": bool(kare_olcu),
                   "kapi_acik": bool(acik)}

    def _ekle(kod, seviye, detay, oneri, scene_id="", beat_id=""):
        if acik:
            q.ekle(Sorun(kod, seviye, scene_id, beat_id, detay, oneri))

    # ── (0) I-37: BEAT -> SCENE -> FACT -> ASSET BAGI ──
    # ⚠ I-37'DE OLCULEN KUSUR: cesitlilik siralayicisi varliklari SAHNELER
    # ARASINDA yeniden diziyordu. Varliklar sahnelere INDEKS ile eslendigi
    # icin anlatim ile gorsel KAYIYORDU: "thin, patchy lawn" cumlesinin
    # altinda fiskiye, "water lightly" cumlesinin altinda Ricinus fidesi
    # cikti (6 beat'in 3'u). Otomatik hicbir kapi bunu gormuyordu.
    # Bag artik DETERMINISTIK dogrulanir ve raporda GORUNUR.
    bag_kayit, bag_kopuk = [], []
    for _c0, _b0 in zip(cekimler, beatler):
        _aid = str(getattr(_c0, "asset_id", "") or "")
        _sid = str(getattr(_c0, "scene_id", "") or "")
        _kayit = {"beat_id": getattr(_b0, "beat_id", ""),
                  "scene_id": _sid, "fact_id": getattr(_b0, "fact_id", ""),
                  "asset_id": _aid,
                  "varlik_scene_id": "", "bagli": True}
        if _aid:
            _ad0 = (adaylar_index or {}).get(_aid) or {}
            _vsid = str(_ad0.get("scene_id") or "")
            _kayit["varlik_scene_id"] = _vsid
            if _vsid and _sid and _vsid != _sid:
                _kayit["bagli"] = False
                bag_kopuk.append(_kayit)
        bag_kayit.append(_kayit)
    olcum["beat_bagi"] = {"kayitlar": bag_kayit, "kopuk": bag_kopuk,
                          "temiz": not bag_kopuk}
    for _bk in bag_kopuk:
        _ekle("KALITE-BAG-KOPUK", "fail",
              f"{_bk['beat_id']} sahnesi {_bk['scene_id']} ama varlik "
              f"{_bk['asset_id']} sahne {_bk['varlik_scene_id']}'e ait — "
              f"anlatim ile gorsel KAYIYOR",
              "medya siralamasi/secimi SAHNE BAGINI korumali; varlik baska "
              "sahnenin beat'ine TASINAMAZ",
              scene_id=_bk["scene_id"], beat_id=_bk["beat_id"])

    # ── I-38: YAZI SPEC'I SAHNE PENCERESININ DISINDA BASLAYAMAZ ──
    # ⚠ OLCULEN KUSUR: grafik spec'ine katmanin MUTLAK zaman cizgisi
    # baslangici yaziliyordu; tuketici (Remotion) onu SAHNEYE GORELI okuyor.
    # `bas_sn >= sahne suresi` olan bir yazi katmani SAHNE-YEREL karede HIC
    # gelmez -> sessizce DUSER. Lawn pilotunda CC-BY/CC-BY-SA dort sahnenin
    # ekran kunyesi boyle kayboldu ve HICBIR kapi gormedi.
    _YAZI_ADLARI = ("chapter-title", "lower-third", "source-label", "callout",
                    "quote-card", "kinetic-title", "text-in-video")
    _sure_beat = {str(getattr(_b1, "beat_id", "") or ""):
                  float(getattr(_b1, "sure_sn", 0) or 0) for _b1 in beatler}
    _yazi_disarida, _yazi_olculen = [], 0
    for _sp1 in (motion_specler or []):
        if str(_sp1.get("ad") or "") not in _YAZI_ADLARI:
            continue
        _yazi_olculen += 1
        _bid1 = str(_sp1.get("beat_id") or "")
        _ssure = _sure_beat.get(_bid1)
        if not _ssure:
            continue
        _bas1 = float(_sp1.get("bas_sn") or 0)
        if _bas1 >= _ssure:
            _yazi_disarida.append({
                "beat_id": _bid1, "ad": _sp1.get("ad"),
                "scene_id": str(_sp1.get("scene_id") or ""),
                "bas_sn": round(_bas1, 3),
                "sahne_sure_sn": round(_ssure, 3)})
    olcum["yazi_sahne_penceresi"] = {"olculen": _yazi_olculen,
                                     "disarida": _yazi_disarida,
                                     "temiz": not _yazi_disarida}
    for _yd1 in _yazi_disarida:
        _ekle("KALITE-YAZI-SAHNE-DISI", "fail",
              f"{_yd1['beat_id']} {_yd1['ad']}: bas_sn {_yd1['bas_sn']} sn "
              f">= sahne suresi {_yd1['sahne_sure_sn']} sn — bu katman "
              f"SAHNE-YEREL karede HIC cizilmez (sessiz dusus)",
              "yazi spec'inin bas_sn'i SAHNEYE GORELI olmali "
              "(mutlak zaman cizgisi DEGIL)",
              scene_id=_yd1["scene_id"], beat_id=_yd1["beat_id"])

    # ── I-39: YAZI ILE ALTYAZI ARASINDA NEFES BOSLUGU ZORUNLU ──
    # ⚠ OLCULEN KUSUR: I-38 kunyeyi GORUNUR yapti, ama kunye altyazinin
    # DIBINDE duruyordu (32.1 px) ve bolum basligi daha da yakindi (15.8 px).
    # Ucu de "bandin disinda" oldugu icin `KALITE-GUVENLI-ALAN`,
    # `KALITE-YAZI-CAKISMA` ve `bant_cakisiyor` TEMIZ donuyordu — kusur ancak
    # KAREYE BAKINCA gorundu (I-33/I-38 dersinin aynisi). Esik altyazi
    # puntosundan TURETILIR (38 * 1.25 = 47.5 px), sabit piksel degil.
    # ⚠ Altyazi YOKSA bant da yoktur: olcum `olculdu=False` doner ve
    # HUKUM VERILMEZ (sessiz PASS degil, "olculemedi").
    if altyazi_kupleri:
        _nf = kk.altyazi_nefes_olcusu(
            [{"ad": getattr(k, "ad", ""),
              "y_orani": getattr(k, "y_orani", 0.0),
              "punto": getattr(k, "punto", 0),
              "bant": bool(getattr(k, "bant", False))}
             for k in (yazi_katmanlari or [])],
            kare_yukseklik=int((kare_olcu or (0, p.yukseklik))[1]
                               or p.yukseklik),
            bant_ust_orani=tipografi.ALTYAZI_BANT[0],
            altyazi_punto=p.tipografi.altyazi)
    else:
        _nf = {"olculdu": False, "neden": "ALTYAZI-YOK",
               "kayitlar": [], "ihlaller": []}
    olcum["altyazi_nefesi"] = _nf
    for _ih in (_nf.get("ihlaller") or []):
        _ekle("KALITE-YAZI-NEFES-YOK", "fail",
              f"{_ih['ad']} (y={_ih['y_orani']}) alt kenari {_ih['alt_px']} px; "
              f"altyazi bandi {_nf['bant_ust_px']} px'te basliyor — arada "
              f"yalniz {_ih['nefes_px']} px var (esik {_nf['esik_px']} px = "
              f"altyazi puntosu {_nf['altyazi_punto']} x {_nf['carpan']})",
              "yazi katmanini YUKARI tasi (kunye altyazi varken ust koseye, "
              "bolum basligi 0.60'a); altyazi puntosunu KUCULTME")

    # ── (1) BASLIK: kelime ortasi kesik + bant tasmasi ──
    baslik_olcumleri = []
    ham_metinler = {b.beat_id: str(getattr(b, "metin", "") or "")
                    for b in beatler}
    for k in yazi_katmanlari:
        if getattr(k, "ad", "") != "chapter-title":
            continue
        o = kk.baslik_olcusu(k.metin, punto=k.punto, kare_genislik=genislik)
        # Ham beat metni: katman ilk beat'ten uretiliyor (plan._yazi_katmanlari_kur)
        ham = ham_metinler.get(beatler[0].beat_id, "") if beatler else ""
        kes = kk.kelime_ortasi_kesik(ham, k.metin)
        o["kelime_kesik"] = kes
        o["sigan_karakter"] = kk.sigan_karakter(k.punto, genislik)
        baslik_olcumleri.append(o)
        if kes.get("kesik"):
            _ekle("KALITE-BASLIK-KIRPIK", "fail",
                  f"baslik kelime ortasindan kesik: "
                  f"{kes.get('yarim_kelime')!r} <- {kes.get('tam_kelime')!r} "
                  f"({o.get('karakter')} karakter, sigan {o['sigan_karakter']})",
                  "basligi KELIME SINIRINDA kisalt "
                  "(plan.kart_basligi_siniri kullanilmali, sabit dilim degil)")
        if o.get("olculdu") and not o.get("sigar"):
            _ekle("KALITE-BASLIK-TASMA", "fail",
                  f"bant {o['cizilen_px']}px cizim / {o['kullanilabilir_px']}px "
                  f"alan -> {o['tasma_px']}px tasma "
                  f"(punto {o['punto_taban']}->{o['uygulanan_punto']}, "
                  f"kucultme tabani vuruldu: {o['kucultme_tabani_vuruldu']})",
                  f"basligi {o['sigan_karakter']} karaktere indir ya da "
                  f"render kare genisligini ({genislik}) plana bildir")
    olcum["baslik"] = baslik_olcumleri

    # ── (2) MEDYA TEKRARI ──
    sahneler = []
    for c in cekimler:
        aday = adaylar_index.get(getattr(c, "asset_id", "") or "") or {}
        sahneler.append({
            "asset_id": getattr(c, "asset_id", "") or "",
            "scene_id": getattr(c, "scene_id", "") or "",
            "medya_yolu": aday.get("yerel_yol") or aday.get("medya_yolu") or ""})
    mt = kk.medya_tekrari(sahneler, benzerlik_okuyucu=benzerlik_okuyucu)
    olcum["medya_tekrari"] = mt
    if mt.get("olculdu"):
        for b in (mt.get("bitisik_ayni_asset") or []):
            _ekle("KALITE-MEDYA-TEKRAR", "fail",
                  f"ayni varlik ARKA ARKAYA: {b['asset_id']} "
                  f"(sahne {b['indeks']})",
                  "komsu sahneye farkli bir lisansli aday sec")
        for aid, n in (mt.get("tekrar_eden_asset") or {}).items():
            if not any(b["asset_id"] == aid
                       for b in (mt.get("bitisik_ayni_asset") or [])):
                _ekle("KALITE-MEDYA-TEKRAR", "fail",
                      f"ayni varlik {n} kez kullanildi: {aid}",
                      "tekrar eden sahnelerden birine alternatif aday sec")
        for c2 in (mt.get("benzer_ciftler") or []):
            _ekle("KALITE-MEDYA-TEKRAR", "fail",
                  f"ayirt edilemeyecek kadar benzer medya: {c2['asset_a']} ~ "
                  f"{c2['asset_b']} (benzerlik {c2['benzerlik']:.3f} >= "
                  f"{mt['benzerlik_esigi']})",
                  "gorsel olarak ayrisan bir aday sec")
        if not mt.get("benzerlik_olculdu"):
            # ⚠ SESSIZ PASS YOK: olcemedigimizi soyleriz, "temiz" demeyiz.
            _ekle("KALITE-MEDYA-BENZER-OLCULEMEDI", "bilgi",
                  "gorsel benzerlik OLCULEMEDI (okuyucu verilmedi); "
                  "yalniz ayni asset_id kontrolu yapildi",
                  "benzerlik_okuyucu enjekte et")

    # ── (2b) I-47: DONEM UYUSMAZLIGI (TERS YON) ──
    # ⚠ Anlatim GUNCEL ama aday TARIHSEL isaret tasiyorsa gorunur kilinir.
    # Saf metin; ag/saglayici cagrisi YOK. Aday ELENMEZ (secim degismez).
    donem_olcum = []
    for c3, b3 in zip(cekimler, beatler):
        _ad3 = adaylar_index.get(getattr(c3, "asset_id", "") or "") or {}
        _bas3 = str(_ad3.get("baslik") or "")
        _mtn3 = str(getattr(b3, "metin", "") or "")
        _du = medya_kapisi_modulu.donem_uyarisi(_mtn3, _bas3) if (
            medya_kapisi_modulu is not None) else {"olculdu": False}
        _du = dict(_du, beat_id=getattr(b3, "beat_id", ""),
                   scene_id=getattr(b3, "scene_id", ""))
        donem_olcum.append(_du)
        if _du.get("uyari"):
            _ekle("KALITE-SEMANTIK-DONEM", "warn",
                  f"{_du['beat_id']}: aday TARIHSEL isaret tasiyor "
                  f"{_du.get('isaretler')} ama anlatim GUNCEL — "
                  f"'{_bas3[:70]}'",
                  "guncel bir lisansli aday sec ya da anlatimi donemle "
                  "uyumlu hale getir (aday ELENMEDI, yalnizca isaretlendi)",
                  scene_id=_du["scene_id"], beat_id=_du["beat_id"])
    olcum["donem_uyusmazligi"] = donem_olcum

    # ── (3) RITIM: sabit blok + olu final ──
    plan_sahneleri = [{"sure_sn": getattr(b, "sure_sn", 0),
                       "metin": str(getattr(b, "metin", "") or "")}
                      for b in beatler]
    rt = kk.ritim_olcusu(plan_sahneleri, toplam_sn=toplam,
                         anlatim_bitis_sn=anlatim_bitis_sn)
    olcum["ritim"] = rt
    if rt.get("olculdu"):
        if rt.get("sabit_blok"):
            _ekle("KALITE-RITIM-SABIT", "fail",
                  f"{rt['sahne']} sahnenin hepsi ayni surede "
                  f"({rt['sureler']}, yayilim {rt['yayilim_sn']} sn <= "
                  f"{rt['sabit_esik_sn']} sn) — sure icerikten turetilmemis"
                  + (f"; anlatim agirligi %"
                     f"{(rt['agirlik_yayilim_orani'] or 0) * 100:.0f} degisiyor"
                     if rt.get("agirlik_yayilim_orani") else ""),
                  "sahne suresini anlatim/olgu uzunlugundan turet")
        elif rt.get("anlatim_bagi") is False:
            _ekle("KALITE-RITIM-SABIT", "fail",
                  f"sure yayilimi %{rt['sure_yayilim_orani'] * 100:.0f} ama "
                  f"anlatim agirligi %"
                  f"{(rt['agirlik_yayilim_orani'] or 0) * 100:.0f} degisiyor "
                  f"— sureler anlatima bagli degil",
                  "sahne suresini anlatim/olgu uzunlugundan turet")
        if rt.get("olu_final_asildi"):
            _ekle("KALITE-OLU-FINAL", "fail",
                  f"planin sonunda {rt['olu_final_sn']} sn anlatimsiz kuyruk "
                  f"(tavan {rt['olu_final_esigi']} sn): toplam "
                  f"{rt['toplam_sn']} sn, anlatim {rt['anlatim_bitis_sn']} sn",
                  "son sahneyi anlatim bitisine kadar kisalt")

    # ── (4) YAZI: GUVENLI ALAN + CAKISMA + ALTYAZI OKUNABILIRLIGI (I-16) ──
    try:
        yukseklik = int((kare_olcu or (0, p.yukseklik))[1] or p.yukseklik)
    except (TypeError, ValueError, IndexError):
        yukseklik = p.yukseklik
    kutular = [{"ad": getattr(k, "ad", ""),
                "y_ust": getattr(k, "y_orani", 0.0),
                "yukseklik": tipografi.YUKSEKLIK.get(getattr(k, "ad", ""), 0.08),
                "bas_sn": getattr(k, "bas_sn", 0.0),
                "sure_sn": getattr(k, "sure_sn", 0.0)}
               for k in (yazi_katmanlari or [])]
    if altyazi_kupleri:
        # Altyazi bandi TEK bir rezerve kutu olarak katilir: kupler ardisik
        # oldugu icin bant pratikte surekli doludur.
        _kb = [kk._sayi(c.get("bas_sn")) for c in altyazi_kupleri
               if isinstance(c, dict)]
        _ks = [kk._sayi(c.get("bas_sn")) + kk._sayi(c.get("sure_sn"))
               for c in altyazi_kupleri if isinstance(c, dict)]
        if _kb:
            kutular.append({
                "ad": "subtitle", "y_ust": tipografi.ALTYAZI_BANT[0],
                "yukseklik": (tipografi.ALTYAZI_BANT[1]
                              - tipografi.ALTYAZI_BANT[0]),
                "bas_sn": min(_kb), "sure_sn": max(_ks) - min(_kb)})
    ga = kk.guvenli_alan_olcusu(kutular, kare_yukseklik=yukseklik,
                                guvenli_kenar=p.tipografi.guvenli_kenar)
    ck = kk.yazi_cakismasi(kutular)
    olcum["guvenli_alan"] = ga
    olcum["yazi_cakismasi"] = ck
    # ── I-30: YATAY guvenli alan (sag/sol tasma) ──
    # ⚠ Bu boyut I-30'a kadar HIC olculmuyordu; `KaynakEtiketi` saga yaslanip
    # `maxWidth` TASIMADIGI icin uzun bir atif SOLA DOGRU SINIRSIZ buyuyebilir.
    # Olcum PLAN verisinden yapilir (metin uzunlugu + punto), OCR/ag YOK.
    _yatay_kutu = [{"ad": getattr(k, "ad", ""),
                    "metin": getattr(k, "metin", ""),
                    "punto": getattr(k, "punto", 0),
                    "hizalama": ("sag" if getattr(k, "ad", "") == "source-label"
                                 else "sol")}
                   for k in (yazi_katmanlari or [])]
    yg = kk.yatay_guvenli_alan_olcusu(
        _yatay_kutu, kare_genislik=genislik,
        guvenli_kenar=p.tipografi.guvenli_kenar)
    olcum["yatay_guvenli_alan"] = yg
    # ── I-31: GORUNUR KUNYE EKSIK OLAMAZ ──
    # ⚠ Atif zorunluyken sahip/lisans yoksa metin URETILMEZ (uydurma YOK)
    # ve kusur SESSIZ KALMAZ: burasi durustce FAIL yazar.
    _kk_eksik = [k for k in (kunye_kararlari or []) if k.get("eksik")]
    olcum["kunye_politikasi"] = {
        "karar": len(kunye_kararlari or []),
        "kisaltilan": [k for k in (kunye_kararlari or [])
                       if k.get("kisaltildi")],
        "eksik": _kk_eksik,
        "yontemler": sorted({str(k.get("yontem") or "")
                             for k in (kunye_kararlari or [])}),
        "temiz": not _kk_eksik}
    for _ke in _kk_eksik:
        _ekle("KALITE-KUNYE-EKSIK", "fail",
              f"{_ke.get('asset_id') or '?'}: gorunur kunye URETILEMEDI "
              f"({_ke.get('yontem')}) — {_ke.get('sebep') or ''}",
              "eser sahibi/lisans alanini kaynagindan doldur; "
              "UYDURULMAZ ve atif atlanamaz",
              scene_id=str(_ke.get("scene_id") or ""),
              beat_id=str(_ke.get("beat_id") or ""))
    for ih in (yg.get("ihlaller") or []):
        _ekle("KALITE-GUVENLI-ALAN", "fail",
              f"{ih['ad']}: YATAY tasma {ih['tasma_px']}px "
              f"({ih['karakter']} karakter, punto {ih['punto']}, "
              f"tahmini {ih['tahmini_genislik_px']}px > "
              f"kullanilabilir {ih['kullanilabilir_px']}px)",
              "atif metnini kisalt ya da katmana genislik siniri ver; "
              "kirpma LISANS ATFINI eksiltebilir — once atif politikasina bak")
    for ih in (ga.get("ihlaller") or []):
        _ekle("KALITE-GUVENLI-ALAN", "fail",
              f"{ih['ad']}: {ih['ihlal']} kenardan {ih['tasma_px']}px tasiyor "
              f"(ust {ih['ust_px']}px / alt {ih['alt_px']}px, "
              f"guvenli aralik {ih['taban_px']}-{ih['tavan_px']}px)",
              "katmani guvenli alanin icine tasi ya da puntoyu kucult")
    for c2 in (ck.get("cakisan_cift") or []):
        _ekle("KALITE-YAZI-CAKISMA", "fail",
              f"{c2['a']} ile {c2['b']} ayni anda ve ayni yerde: "
              f"zaman {c2['zaman']}, dikey {c2['dikey']}",
              "cakisma cozucuye yasak bant bildir ya da zamanlamayi ayir")

    if altyazi_kupleri:
        ao = kk.altyazi_kupleri(
            [{"bas": c.get("bas_sn"), "sure": c.get("sure_sn"),
              "metin": c.get("metin")} for c in altyazi_kupleri
             if isinstance(c, dict)],
            maks_karakter=p.tipografi.maks_satir_karakter)
        olcum["altyazi"] = {k2: v for k2, v in ao.items() if k2 != "kupler"}
        olcum["altyazi"]["kup_sayisi"] = ao.get("kup_sayisi")
        for kupe in (ao.get("cok_hizli") or []):
            _ekle("KALITE-ALTYAZI-OKUNMAZ", "warn",
                  f"kup cok hizli: {len(kupe['metin'])} karakter / "
                  f"{kupe['sure_sn']} sn > {ao['maks_cps']} kar/sn "
                  f"({kupe['metin'][:40]!r})",
                  "kupu bol ya da suresini uzat")
        for kupe in (ao.get("uzun_satir") or []) + (ao.get("cok_satir") or []):
            _ekle("KALITE-ALTYAZI-OKUNMAZ", "warn",
                  f"kup okunabilirlik sinirini asiyor: "
                  f"{len(kupe['satirlar'])} satir, en uzun "
                  f"{max((len(s) for s in kupe['satirlar']), default=0)} karakter",
                  "satir uzunlugunu/sayisini dusur")

    # ── (4b) MEDYASIZ BEAT (I-22) ──
    # ⚠ I-21'de OLCULDU: bolunme 5 beat uretti, saglayici kotasi 4'tu ve
    # b005 MEDYASIZ kalip statik fallback karta dustu. Sonuc: POST-SIYAH-KARE
    # + POST-OPTIK-DURGUN (optik ort 0.178, 3.75 sn donuk) + POST-KENAR-SIYAH.
    # Bu kusur RENDER SONRASI yakalaniyordu — yani 40 sn render harcandiktan
    # SONRA. Plan uzerinde bedava yakalanabilir: hicbir beat medyasiz kalmamali.
    medyasiz = [{"beat_id": getattr(c3, "beat_id", ""),
                 "scene_id": getattr(c3, "scene_id", ""),
                 "fallback_turu": getattr(c3, "fallback_turu", ""),
                 "gerekce": str(getattr(c3, "gerekce", ""))[:120]}
                for c3 in (cekimler or [])
                if getattr(c3, "kaynak_turu", "") != "medya"]
    olcum["medyasiz_beat"] = {
        "beat": len(cekimler or []), "medyasiz": len(medyasiz),
        "kayitlar": medyasiz[:6],
        "temiz": not medyasiz}
    for mb in medyasiz:
        _ekle("KALITE-MEDYASIZ-BEAT", "fail",
              f"{mb['beat_id']} ({mb['scene_id']}) medyasiz kaldi -> "
              f"fallback '{mb['fallback_turu'] or 'kart'}'; gerekce: "
              f"{mb['gerekce']}",
              "plan beat sayisi ile medya aday sayisini DETERMINISTIK eslestir "
              "(saglayici kotasi ya da aday adedi yetersiz)",
              scene_id=mb["scene_id"], beat_id=mb["beat_id"])

    # ── (5) MOTION GRAMMAR (I-17) — plan uzerinden, render'a bakmadan ──
    mg_sahne = []
    for c2, b2 in zip(cekimler, beatler):
        _s2 = {
            "beat_id": getattr(b2, "beat_id", ""),
            "hareket": getattr(c2, "hareket", ""),
            "islev": getattr(b2, "islev", ""),
            "sure_sn": getattr(b2, "sure_sn", 0.0)}
        # ── I-44: gorselin UZAMSAL ENERJISI (olcer DISARIDAN) ──
        # ⚠ Bu modul GORSEL ACMAZ. Okuyucu yoksa alan HIC yazilmaz ->
        # `motion_grammar_olcusu` "olculemedi" der, "yeterli" DEMEZ.
        _ad2 = adaylar_index.get(getattr(c2, "asset_id", "") or "") or {}
        _tur2 = str(_ad2.get("medya_turu")
                    or ("video" if "video" in str(_ad2.get("mime") or "")
                        else "image"))
        _s2["medya_turu"] = _tur2
        _s2["kadraj"] = getattr(c2, "kadraj", "")
        # ── I-45: ENERJI EKRANA GELEN BOLGEDE OLCULUR ──
        # ⚠ I-44 tum kareyi olcuyordu; renderer ise `kadraj`/`punch` ile
        # kirpiyor. Gorunen bolge cekimin KENDI kamera spec'inden turetilir
        # (`kalite_kapisi.kadraj_kirpma_bolgesi`, Kamera.tsx ile ayni
        # aritmetik). Iki ucta (t=0, t=1) olculur.
        _kirpma, _gezinme = None, None
        _prm2 = {}
        for _sp2 in (motion_specler or []):
            if _sp2.get("beat_id") == _s2["beat_id"] and (
                    _sp2.get("parametre") or {}).get("zoom"):
                _prm2 = _sp2.get("parametre") or {}
                break
        if _prm2:
            _z2 = _prm2.get("zoom") or [1.0, 1.0]
            _uc = [kk.kadraj_kirpma_bolgesi(
                olcek=_z2[0 if _t == 0.0 else -1],
                pan_x=_prm2.get("pan_x") or (0.5, 0.5),
                odak=_prm2.get("odak") or (0.5, 0.5),
                guvenli_pay=_prm2.get("guvenli_pay") or 0.0,
                kaynak_g=_ad2.get("genislik") or 0,
                kaynak_y=_ad2.get("yukseklik") or 0,
                kare_g=genislik, kare_y=(kare_olcu or (0, p.yukseklik))[1]
                or p.yukseklik, t=_t) for _t in (0.0, 1.0)]
            if all(u.get("olculdu") for u in _uc):
                _s2["kirpma"] = [_uc[0], _uc[1]]
                _gz2 = kk.kadraj_gezinme_hizi(_uc[0], _uc[1],
                                              sure_sn=_s2["sure_sn"])
                if _gz2.get("olculdu"):
                    _gezinme = _gz2["hiz"]
                    _s2["gezinme_hizi"] = _gezinme
                    _s2["gezinme"] = _gz2
                # ── I-46: YER DEGISTIRME ALANI (pan ve zoom AYRI) ──
                _yd2 = kk.yer_degistirme_alani(_uc[0], _uc[1],
                                               sure_sn=_s2["sure_sn"])
                if _yd2.get("olculdu"):
                    _s2["yer_degistirme"] = _yd2["d"]
                    _s2["yer_degistirme_alani"] = _yd2
                _kirpma = _uc
        if enerji_okuyucu:
            _yol2 = (_ad2.get("yerel_yol") or _ad2.get("medya_yolu") or "")
            if _yol2:
                # ⚠ IKI UC DA olculur ve EN YUKSEK enerji alinir:
                # `EMIN DEGILSEN ENGELLEME` yonunde muhafazakar — varliga
                # EN ELVERISLI uc esas alinir, en dar/en genis degil.
                _olculen = []
                for _kb2 in (_kirpma or [None]):
                    try:
                        _e2 = enerji_okuyucu(_yol2, _kb2)
                    except TypeError:  # eski sozlesmeli okuyucu (I-44)
                        try:
                            _e2 = enerji_okuyucu(_yol2)
                        except Exception:                        # noqa: BLE001
                            _e2 = None
                    except Exception:                            # noqa: BLE001
                        _e2 = None
                    if _e2 is not None:
                        _olculen.append(float(_e2))
                if _olculen:
                    _s2["uzamsal_enerji"] = max(_olculen)
                    _s2["kadraj_enerjileri"] = [round(x, 3) for x in _olculen]
        mg_sahne.append(_s2)
    _gec = {}
    for sp in (motion_specler or []):
        tur = (sp.get("parametre") or {}).get("tur")
        if tur in motion.GECIS_GEREKCESI:
            _gec.setdefault(sp.get("beat_id", ""), []).append(tur)
    for s2 in mg_sahne:
        s2["gecis"] = _gec.get(s2["beat_id"], [])
    mg = kk.motion_grammar_olcusu(mg_sahne)
    olcum["motion_grammar"] = mg
    if mg.get("olculdu"):
        for tk in (mg.get("ardisik_tekrar") or []):
            _ekle("KALITE-MOTION-TEKRAR", "fail",
                  f"ardisik ayni kamera hareketi: {tk['hareket']} "
                  f"(sahne {tk['indeks']})",
                  "komsu cekime farkli yon/siddet ver")
        for tk in (mg.get("pencere_tekrari") or []):
            _ekle("KALITE-MOTION-TEKRAR", "warn",
                  f"son {tk['pencere']} cekimde ayni hareket tekrar etti: "
                  f"{tk['hareket']} (sahne {tk['indeks']})",
                  "hareket yonunu/siddetini cesitlendir")
        # ── I-24: ACILIS ve KAPANIS AYNI HAREKET OLAMAZ ──
        # ⚠ Bu, teknoloji pilotunda `motion_cesitlilik` puanini 0/20 yapan
        # TEK kirmizi kosuldu ve RENDER SONRASI bile hukum uretmiyordu —
        # yalnizca puani dusuruyordu. Artik PLAN uzerinde BEDAVA yakalanir.
        if len(mg_sahne) >= 2 and not mg.get("acilis_kapanis_ayri"):
            _ekle("KALITE-MOTION-ACILIS-KAPANIS", "fail",
                  f"acilis ve kapanis AYNI kamera hareketi: "
                  f"{mg.get('acilis_hareketi')} "
                  f"(sahne 0 ve {len(mg_sahne) - 1})",
                  "kapanis hareketini acilistan FARKLI sec "
                  "(belgesel dilinde acilis iceri girer, kapanis geri cekilir)")
        # ── I-24: AYNI ANLATI ISLEVINDE AYNI HAREKET OLAMAZ ──
        for tk in (mg.get("islev_tekrari") or []):
            _ekle("KALITE-MOTION-ISLEV-TEKRAR", "fail",
                  f"'{tk['islev']}' islevindeki iki beat ayni hareketi "
                  f"aliyor: {tk['hareket']} "
                  f"(sahne {tk['ilk_indeks']} ve {tk['indeks']})",
                  "ayni islevdeki cekimlere farkli hareket ata; "
                  "islev pencereye takilmaz, videonun her yerine dagilir")
        # ── I-44: DUZ GORSEL, STATIK FOTOGRAF OLARAK HAREKET URETMEZ ──
        # ⚠ I-43'te uc renderle ayristirildi: ayni sure + ayni etkin hizda
        # kalibre gorsel 3.690 verirken duz gorsel 1.457 verdi; sure
        # uzatilip etkin hiz artirilinca bile 1.643'te kaldi. Yani kusur
        # kovada ya da surede DEGIL, gorselin kendisinde.
        # ⚠ SEVIYE `warn`, FAIL DEGIL — `EMIN DEGILSEN ENGELLEME`: enerji TUM
        # karede olculur, `kadraj`/`punch` ise kaynagi KIRPABILIR ve kirpilan
        # bolgenin enerjisi farkli olabilir (AYRI ve OLCULMEMIS atom).
        for de in (mg.get("dusuk_enerji") or []):
            _kdr = (mg_sahne[de["indeks"]].get("kadraj") or "tam")
            _ekle("KALITE-MEDYA-DUSUK-ENERJI", "warn",
                  f"{de['beat_id']}: gorselin uzamsal enerjisi "
                  f"{de['uzamsal_enerji']} <= esik {de['esik']} — statik "
                  f"fotograf olarak kamera hareketi ('{de['hareket']}', "
                  f"kadraj '{_kdr}') ekranda hareket URETMEYEBILIR "
                  f"(render sonrasi KALITE-OPTIK-DURGUN riski)",
                  "daha detayli (dokulu) bir lisansli aday sec ya da "
                  "kadraji dokunun yogun oldugu bolgeye getir",
                  beat_id=de["beat_id"])
        # ── I-46: RISK OPTIK BIRIMDE (enerji x yer degistirme) ──
        # ⚠ Yeni esik YOK: karsilastirma `OPTIK_DURGUN_ESIGI` ile yapilir;
        # eklenen tek sey modelin OLCULEN hata payidir.
        for orsk in (mg.get("optik_riski") or []):
            _sv = "fail" if orsk.get("seviye") == "fail" else "warn"
            _ek = ("olculen hata payiyla bile esigi GECEMEZ"
                   if _sv == "fail" else
                   "hata payi icinde esigi gecebilir — hukum KESIN DEGIL")
            _ekle("KALITE-OPTIK-DURGUN-BEKLENEN", _sv,
                  f"{orsk['beat_id']}: beklenen optik hareket "
                  f"{orsk['beklenen']} (ust sinir {orsk['ust_sinir']}) < esik "
                  f"{orsk['esik']} — enerji {orsk['enerji']} x yer degistirme "
                  f"{orsk['d']} ornek piksel/kare; {_ek}",
                  "daha detayli (dokulu) aday sec, kadraji dokuya getir ya da "
                  "kamera hareketini artir (zoom/pan)",
                  beat_id=orsk["beat_id"])
        # ── I-45: kalibrasyon alani disinda kalan cekimler ──
        for kd in (mg.get("gezinme_kapsam_disi") or []):
            _ekle("KALITE-MEDYA-ENERJI-KAPSAM-DISI", "bilgi",
                  f"{kd['beat_id']}: gorunen kadrajin uzamsal enerjisi "
                  f"{kd['uzamsal_enerji']} <= esik {kd['esik']} AMA kamera "
                  f"{kd['gezinme_hizi']}/sn geziniyor — esik "
                  f"{kd['kalibrasyon_hizi']}/sn konfigurasyonunda olculdu, "
                  f"bu cekim OLCUM ALANININ DISINDA; hukum VERILMEDI",
                  "bu gezinme hizinda enerji-optik iliskisini olcup "
                  "kalibre et (esigi tasima)",
                  beat_id=kd["beat_id"])
        if not mg.get("enerji_olculdu"):
            # ⚠ SESSIZ PASS YOK: olcemedigimizi soyleriz, "yeterli" demeyiz.
            _ekle("KALITE-MEDYA-ENERJI-OLCULEMEDI", "bilgi",
                  "gorsellerin uzamsal enerjisi OLCULEMEDI (okuyucu "
                  "verilmedi); statik fotograf hareket yeterliligi "
                  "yalniz RENDER SONRASI gorulebilir",
                  "enerji_okuyucu enjekte et")
        if len(mg_sahne) >= 3 and mg.get("benzersiz_gecis", 0) < 2:
            _ekle("KALITE-GECIS-TEKDUZE", "warn",
                  f"tek gecis ailesi kullanildi: {mg.get('gecis_dagilimi')} "
                  f"— isleve bagli en az iki aile beklenir",
                  "kapanis/kanit gecislerini isleve gore cesitlendir")
        # ── I-27: KAMERA PUNCH'I KAYNAGI BUYUTEMEZ ──
        # ⚠ Olcum YENIDEN TURETILMEZ: plan onu spec'e islemistir (tek kaynak).
        _pb_kayit = []
        for sp in (motion_specler or []):
            _pb = ((sp.get("parametre") or {}).get("punch_buyutme") or {})
            if not _pb.get("olculdu"):
                continue
            _pb_kayit.append(dict(_pb, beat_id=sp.get("beat_id", "")))
            if _pb.get("buyutuyor"):
                _ek = ("hicbir kadraj yetmedi"
                       if _pb.get("cozulemedi") else "kadraj dusurulemedi")
                _ekle("KALITE-PUNCH-BUYUTME", "fail",
                      f"{sp.get('beat_id', '')}: {_pb.get('sebep') or ''} "
                      f"({_ek})",
                      "daha yuksek cozunurluklu kaynak sec ya da kadraji "
                      "genislet; upscale/blur/pillarbox YAPILMAZ",
                      beat_id=sp.get("beat_id", ""))
        olcum["punch_buyutme"] = {
            "olculen_beat": len(_pb_kayit),
            "buyuten": [k for k in _pb_kayit if k.get("buyutuyor")],
            "kadraj_dusurulen": [k for k in _pb_kayit
                                 if k.get("kadraj_degisti")],
            "en_yuksek_oran": max([k.get("ekran_piksel_orani", 0)
                                   for k in _pb_kayit] or [0]),
            "temiz": not [k for k in _pb_kayit if k.get("buyutuyor")]}

        for st in (mg.get("statik_sahneler") or []):
            if kk._sayi(st.get("sure_sn")) > kk.OPTIK_DURGUN_FAIL_SN:
                _ekle("KALITE-OPTIK-DURGUN", "fail",
                      f"plan {st['sure_sn']} sn'lik sahneye 'static' hareket "
                      f"veriyor (tavan {kk.OPTIK_DURGUN_FAIL_SN} sn)",
                      "uzun cekimde Ken Burns yonu ata")

    q.olcumler["kalite"] = olcum
