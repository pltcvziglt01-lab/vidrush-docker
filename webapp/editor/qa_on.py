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

from . import gramer, motion, tipografi
from .profil import OLCULEN, EditProfili, VARSAYILAN

# ── Sorun kodlari ve seviyeleri ──
FAIL_KODLARI = {
    "LISANS-EKSIK", "LISANS-ATIF-EKSIK", "FACT-BAGLANTI-YOK",
    "EFEKT-SESSIZ-KAYIP", "SHOT-TAVAN-IHLAL", "ENTITY-DONEM",
    "MEDYA-KAPSAM-YOK", "SES-LUFS-HEDEF-YOK", "TIPO-KONTRAST",
}


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
            arastirma_fact_idler: Optional[set] = None) -> QaSonucu:
    p = profil_ or VARSAYILAN
    q = QaSonucu()
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
    q.olcumler["ses"] = {
        "lufs_hedef": ses_plani.lufs_hedef,
        "tepe_tavan": ses_plani.tepe_tavan,
        "sfx_dakikada": ses_plani.sfx_yogunlugu(toplam),
        "on_zincir_adim": len(ses_plani.on_zincir),
        "ducking_araligi": len(ses_plani.ducking_zarfi)}
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

    return q.sonuclandir()
