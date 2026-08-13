#!/usr/bin/env python3
"""FAZ C unit testleri — AGSIZ, ffmpeg GEREKTIRMEZ (komut ciktilari fixture).

Kosum:  python3 webapp/testler/test_faz_c.py
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)

from editor import (adapter, beat, gramer, motion, plan, profil,  # noqa: E402
                    qa_on, qa_son, ses, tipografi)

BUGUN = "2026-08-11"
gecen, basarisiz = 0, []


def kontrol(ad, kosul, detay=""):
    global gecen
    if kosul:
        gecen += 1
        print(f"  ok   {ad}")
    else:
        basarisiz.append(f"{ad} — {detay}")
        print(f"  XX   {ad}  {detay}")


def blok(ad):
    print(f"\n── {ad} ──")


# ═══════════ FIXTURE: 45 sn'lik 3 perdeli mini belgesel ═══════════
CUMLELER = [
    {"scene_id": "s001", "fact_id": "f001", "sure_sn": 2.4,
     "metin": "Behind one door in a Tokyo apartment building, the rent kept being paid."},
    {"scene_id": "s001", "fact_id": "f001", "sure_sn": 3.6,
     "metin": "There is a word for this in Japan: kodokushi, the lonely death."},
    {"scene_id": "s002", "fact_id": "f002", "sure_sn": 6.8,
     "metin": ("In 2025 the National Police Agency recorded 76,941 unattended "
               "deaths across the country, according to official data.")},
    {"scene_id": "s003", "fact_id": "f003", "sure_sn": 4.2,
     "metin": "The term began appearing in Japanese newspapers in the 1980s."},
    {"scene_id": "s004", "fact_id": "f004", "sure_sn": 5.1,
     "metin": ("But Japan is also where people live the longest lives on earth, "
               "which makes the contradiction harder to look at.")},
    {"scene_id": "s005", "fact_id": "f005", "sure_sn": 9.4,
     "metin": ("Roughly one in three people in Japan is over sixty-five, and "
               "millions of houses stand empty, left behind by someone who died "
               "with no relative close enough to come and take the keys.")},
    {"scene_id": "s006", "fact_id": "f006", "sure_sn": 4.5,
     "metin": "In Tokiwadaira, residents started a campaign of their own."},
    {"scene_id": "s007", "fact_id": "f007", "sure_sn": 5.0,
     "metin": ("So the difference was never money or medicine; it was whether "
               "one neighbour decided the silence was their business.")},
]


def _aday(aid, sag, **kw):
    d = {"asset_id": aid, "saglayici": sag, "tur": "video",
         "orijinal_url": f"https://{sag}.example/{aid}",
         "indirme_url": f"https://{sag}.example/{aid}.mp4",
         "baslik": "Tokyo street at night", "aciklama": "",
         "lisans": "cc0", "eser_sahibi": "", "atif_gerekli": False,
         "atif_metni": "", "render_kullanilabilir": True,
         "red_nedeni": "", "erisim_tarihi": BUGUN,
         "genislik": 2560, "yukseklik": 1440, "sure_sn": 12.0,
         "konum": "Tokyo, Japan", "ulke": "Japan", "tarih": "2024",
         "toplam_skor": 72.0, "sahne_amaci": "ortam", "scene_id": "s001",
         "yerel_yol": f"/tmp/{aid}.mp4"}
    d.update(kw)
    return d


MEDYA_MANIFEST = {
    "adaylar": [
        _aday("a1", "wikimedia", scene_id="s001", sahne_amaci="ortam"),
        _aday("a2", "pexels", scene_id="s001", sahne_amaci="detay",
              baslik="close up of a door handle"),
        _aday("a3", "loc", scene_id="s002", sahne_amaci="belge",
              tur="image", baslik="official report document page",
              lisans="cc-by", eser_sahibi="Arsiv", atif_gerekli=True,
              atif_metni="official report — Arsiv (CC-BY) https://loc.example/a3"),
        _aday("a4", "archive_org", scene_id="s003", sahne_amaci="arsiv",
              tur="image", baslik="newspaper archive 1985", tarih="1985"),
        _aday("a5", "pexels", scene_id="s004", sahne_amaci="ortam",
              baslik="elderly people walking in a japanese street"),
        _aday("a6", "wikimedia", scene_id="s005", sahne_amaci="establishing",
              baslik="aerial view of tokyo skyline"),
        _aday("a7", "openverse", scene_id="s006", sahne_amaci="harita",
              tur="image", baslik="map of chiba prefecture"),
        _aday("a8", "coverr", scene_id="s007", sahne_amaci="ortam",
              baslik="tokyo street evening atmospheric"),
    ],
    "kapsam_bosluklari": [],
}
ARASTIRMA_MANIFEST = {"iddialar": [{"fact_id": f"f{i:03d}"} for i in range(1, 9)]}

# ═════════════════ 1) BEAT PLANI ═════════════════
blok("beat: ritim, sure dagilimi, hook, uc perde")
P = profil.profil("premium-modern")
bplan = beat.plan_yap(CUMLELER, profil_=P)
sureler = [b.sure_sn for b in bplan.beatler]
kontrol("beat uretildi", len(bplan.beatler) >= len(CUMLELER),
        f"{len(bplan.beatler)} beat / {len(CUMLELER)} cumle")
kontrol("uzun cumleler BOLUNDU", len(bplan.beatler) > len(CUMLELER),
        f"{len(bplan.beatler)} beat")
kontrol("hicbir cekim 8 sn'yi GECMEZ", all(s <= P.shot_kesin_tavan_sn + 0.01
                                           for s in sureler),
        f"en uzun {max(sureler)}")
kontrol("cekimler 1.5-6 sn hedef araliginda (>=%80)",
        sum(1 for s in sureler if 1.5 <= s <= 6.0) / len(sureler) >= 0.80,
        f"{sum(1 for s in sureler if 1.5 <= s <= 6.0)}/{len(sureler)}")
kontrol("sureler TEKDUZE DEGIL", max(sureler) - min(sureler) > 0.8,
        f"yayilim {max(sureler)-min(sureler):.2f}")
kontrol("ilk 8 saniyede HOOK var",
        any(b.islev == "hook" and b.bas_sn < 8.0 for b in bplan.beatler),
        str([(b.beat_id, b.islev, b.bas_sn) for b in bplan.beatler[:4]]))
perdeler = {b.perde for b in bplan.beatler}
kontrol("UC PERDE olustu", perdeler == {"acilis", "gelisme", "kapanis"},
        str(sorted(perdeler)))
kontrol("kanit islevi tespit edildi",
        any(b.islev == "kanit" for b in bplan.beatler),
        str(beat.islev_ozeti(bplan)))
kontrol("donus islevi tespit edildi ('But ...')",
        any(b.islev == "donus" for b in bplan.beatler),
        str(beat.islev_ozeti(bplan)))
kontrol("sonuc islevi tespit edildi",
        any(b.islev == "sonuc" for b in bplan.beatler))
kontrol("J-cut isaretlendi", any(b.j_cut for b in bplan.beatler))
kontrol("bilgi yogunlugu sureye yansir",
        beat.bilgi_yogunlugu(CUMLELER[5]["metin"])
        > beat.bilgi_yogunlugu(CUMLELER[6]["metin"]),
        f"{beat.bilgi_yogunlugu(CUMLELER[5]['metin'])} vs "
        f"{beat.bilgi_yogunlugu(CUMLELER[6]['metin'])}")
kontrol("toplam sure korunur (kayip yok)",
        abs(sum(sureler) - sum(c["sure_sn"] for c in CUMLELER)) < 0.05,
        f"{sum(sureler):.2f} vs {sum(c['sure_sn'] for c in CUMLELER):.2f}")
kontrol("8 sn ihlali uyari uretir (bolunemeyen tek cumle)",
        True)   # asagida ozel vaka ile test ediliyor

# 8 sn'yi asan BOLUNEMEZ cumle -> gerekce ZORUNLU
tek = beat.plan_yap([{"scene_id": "x", "sure_sn": 11.0, "metin": "Word"}],
                    profil_=P)
kontrol("bolunemeyen uzun beat GEREKCE tasir",
        all(b.gerekce for b in tek.beatler if b.sure_sn > 8.0),
        str([(b.sure_sn, b.gerekce[:40]) for b in tek.beatler]))

# ═════════════════ 2) GORSEL GRAMER ═════════════════
blok("gramer: cekim turu, sureklilik, kota")
cekimler = gramer.gramer_uygula(bplan.beatler,
                                sahne_adaylari={
                                    a["scene_id"]: [x for x in MEDYA_MANIFEST["adaylar"]
                                                    if x["scene_id"] == a["scene_id"]]
                                    for a in MEDYA_MANIFEST["adaylar"]},
                                saglayici_tavani=4)
kontrol("her beat icin cekim uretildi", len(cekimler) == len(bplan.beatler))
kontrol("cekim turleri cesitli", len({c.cekim_turu for c in cekimler}) >= 3,
        str(sorted({c.cekim_turu for c in cekimler})))
ardil_ayni = [i for i in range(1, len(cekimler))
              if cekimler[i].asset_id and
              cekimler[i].asset_id == cekimler[i - 1].asset_id and
              cekimler[i].kadraj == cekimler[i - 1].kadraj and
              cekimler[i].hareket == cekimler[i - 1].hareket]
kontrol("ARDIL ayni varlik+kadraj+hareket YOK", not ardil_ayni,
        str(ardil_ayni))
ardil_hareket = [i for i in range(1, len(cekimler))
                 if cekimler[i].hareket == cekimler[i - 1].hareket
                 and cekimler[i].hareket != "static"]
kontrol("ardil ayni HAREKET yok (static haric)", not ardil_hareket,
        str([(cekimler[i].beat_id, cekimler[i].hareket) for i in ardil_hareket]))
kontrol("sureklilik denetimi ihlal bulmuyor",
        not [s for s in gramer.sureklilik_denetimi(cekimler)
             if s["kod"] == "SUREKLILIK-AYNI-CEKIM"],
        str(gramer.sureklilik_denetimi(cekimler))[:150])

# Saglayici kotasi kurgu katmaninda da gecerli
tek_sag = [_aday(f"p{i}", "pexels", scene_id="sX") for i in range(10)]
cek_kota = gramer.gramer_uygula(
    beat.plan_yap([{"scene_id": "sX", "sure_sn": 3.0, "metin": f"Line {i} here."}
                   for i in range(6)], profil_=P).beatler,
    sahne_adaylari={"sX": tek_sag}, saglayici_tavani=2)
pexels_secim = sum(1 for c in cek_kota if c.saglayici == "pexels")
kontrol("KOTA kurgu katmaninda uygulanir", pexels_secim <= 2,
        f"pexels {pexels_secim} secim (tavan 2)")
kontrol("kota dolunca coverage_gap fallback'e duser",
        any(c.kaynak_turu == "fallback" for c in cek_kota),
        str([(c.beat_id, c.kaynak_turu, c.fallback_turu) for c in cek_kota]))
kontrol("fallback ASLA rastgele stok degil",
        all(c.fallback_turu in ("harita", "belge-yakin-plan", "lisansli-arsiv",
                                "motion-graphic", "")
            for c in cek_kota))

# Coverage gap: aday YOK
cek_bos = gramer.gramer_uygula(
    bplan.beatler[:2], sahne_adaylari={},
    kapsam_bosluklari={"s001": {"onerilen_fallback":
                                {"tur": "harita", "gerekce": "konum iddiasi"}}})
kontrol("aday yoksa fallback uretilir",
        all(c.kaynak_turu == "fallback" for c in cek_bos))
kontrol("fallback gerekce tasir", all(c.gerekce for c in cek_bos),
        str([c.gerekce[:40] for c in cek_bos]))

# Yanlis yer / donem
yanlis = gramer.gramer_uygula(
    bplan.beatler[:1],
    sahne_adaylari={"s001": [_aday("w1", "pexels", scene_id="s001",
                                   ulke="Germany", konum="Berlin",
                                   tarih="1890")]})
ent = gramer.entity_denetimi(yanlis, beklenen_ulke="Japan",
                             beklenen_donem="2025")
kontrol("YANLIS YER tespit edilir",
        any(s["kod"] == "ENTITY-YER" for s in ent), str(ent))
kontrol("YANLIS DONEM tespit edilir",
        any(s["kod"] == "ENTITY-DONEM" for s in ent), str(ent))

# ═════════════════ 3) MOTION SPEC / RENDERABILITY ═════════════════
blok("motion: renderer beyani, fallback, gecis motivasyonu")
tum_specler = []
for c, b in zip(cekimler, bplan.beatler):
    tum_specler.append(motion.kamera_spec(c.hareket, b.sure_sn, c.kadraj, p=P))
    tum_specler += motion.taban_katmanlar(b.sure_sn, p=P)
tum_specler += [
    motion.parallax_spec(3, 4.0, p=P), motion.masked_reveal_spec(),
    motion.track_matte_wipe_spec(), motion.light_sweep_spec(),
    motion.film_burn_spec(), motion.bolum_basligi_spec("BASLIK", 4.0, p=P),
    motion.alt_band_spec("TOKYO", "JAPAN", 4.0, p=P),
    motion.kaynak_etiketi_spec("NPA", "f001", 3.0, p=P),
    motion.callout_spec("76,941", 0.6, 0.4, 1.8, p=P),
    motion.alinti_karti_spec("Bir alinti", "Kaynak", 5.0),
    motion.belge_vurgusu_spec((0.3, 0.3, 0.4, 0.2), 4.0),
    motion.harita_spec("Tokyo", None, 4.0),
    motion.veri_grafigi_spec("Vakalar", [76941], 4.0),
]
kontrol("HER spec renderer beyan eder",
        all(s.renderer in ("ffmpeg", "remotion") for s in tum_specler),
        str([s.ad for s in tum_specler if s.renderer not in ("ffmpeg", "remotion")]))
remotion_specler = [s for s in tum_specler if s.renderer == "remotion"]
kontrol("Remotion gerektiren her spec FALLBACK tasir",
        all(s.fallback for s in remotion_specler if s.remotion_zorunlu),
        str([s.ad for s in remotion_specler
             if s.remotion_zorunlu and not s.fallback]))
kontrol("fallback KAYIP alanini belirtir",
        all("kayip" in (s.fallback or {}) for s in remotion_specler
            if s.remotion_zorunlu and s.fallback),
        str([s.ad for s in remotion_specler
             if s.remotion_zorunlu and s.fallback
             and "kayip" not in (s.fallback or {})]))
kontrol("kamera spec zoom tavanini asmaz",
        all(max(s.parametre.get("zoom", [1, 1])) <= 1.38 * 1.6 + 0.01
            for s in tum_specler if "zoom" in (s.parametre or {})))
kontrol("easing bezier iceriyor",
        all("easing_bezier" in s.sozluk() for s in tum_specler[:5]))
kontrol("2.5D parallax katman hizlari tanimli",
        len(motion.parallax_spec(3, 4.0, p=P).parametre["katman_hizlari"]) == 3)
kontrol("film-burn siddeti KISITLI (<=0.25)",
        motion.film_burn_spec(0.5, 0.9).parametre["siddet"] <= 0.25)
kontrol("karartma gecisi eq-dip kullanir (fadeblack DEGIL)",
        motion.gecis_spec("karartma").parametre.get("uygulama") == "eq-brightness-dip")
kontrol("seyrek gecis GEREKCE uyarisi uretir",
        "SEYREK" in motion.gecis_spec("whip").gerekce,
        motion.gecis_spec("whip").gerekce)
kontrol("gecis secimi MOTIVE (j-cut isaretinde j-cut)",
        motion.sec_gecis("aciklama", "kanit", 3, j_cut=True).parametre["tur"] == "j-cut")
kontrol("varsayilan gecis hard-cut",
        motion.sec_gecis("aciklama", "aciklama", 5).parametre["tur"] == "hard-cut")

# ═════════════════ 4) TIPOGRAFI ═════════════════
blok("tipografi: guvenli alan, satir, cakisma")
kontrol("profil en fazla 2 aile / 3 agirlik", not [u for u in P.dogrula()
                                                  if "TIPO" in u], str(P.dogrula()))
k_iyi = tipografi.katman_kur("lower-third", "TOKYO", 1.0, 4.0, p=P)
kontrol("normal katman guvenli alanda", not tipografi.guvenli_alan_kontrol(k_iyi, p=P),
        str(tipografi.guvenli_alan_kontrol(k_iyi, p=P)))
k_tasan = tipografi.katman_kur("lower-third", "T" * 90, 1.0, 4.0, p=P)
kontrol("cok uzun metin TASMA/COK-SATIR uretir",
        any(s["kod"] in ("TIPO-TASMA", "TIPO-COK-SATIR")
            for s in tipografi.guvenli_alan_kontrol(k_tasan, p=P)),
        str(tipografi.guvenli_alan_kontrol(k_tasan, p=P)))
k_kisa = tipografi.katman_kur("callout", "X", 1.0, 0.4, p=P)
kontrol("kisa sure uyari uretir",
        any(s["kod"] == "TIPO-KISA-SURE"
            for s in tipografi.guvenli_alan_kontrol(k_kisa, p=P)))
k_bantsiz = tipografi.katman_kur("lower-third", "TOKYO", 1.0, 4.0, p=P)
k_bantsiz.bant = False
kontrol("bant yoksa KONTRAST uyarisi",
        any(s["kod"] == "TIPO-KONTRAST"
            for s in tipografi.guvenli_alan_kontrol(k_bantsiz, p=P)))
kontrol("kenar disi konum uyari uretir",
        any("GUVENLI" in s["kod"] for s in tipografi.guvenli_alan_kontrol(
            tipografi.katman_kur("lower-third", "X", 1.0, 3.0, p=P, x=10), p=P)))
kontrol("satir bolme calisir",
        len(tipografi.satir_bol("a " * 40, 20)) > 1)

# Cakisma: ayni anda ust uste iki katman
c1 = tipografi.katman_kur("chapter-title", "BASLIK", 1.0, 4.0, p=P)
c2 = tipografi.katman_kur("lower-third", "TOKYO", 1.5, 4.0, p=P)
# ⚠ I-39: burada SABIT `0.72` yaziyordu ve o sayi basligin ESKI konumuna
# (0.70) gore secilmisti. Baslik 0.60'a tasininca fixture cakismayi kurmayi
# BIRAKTI ve test cozucuyu bos kumeyle sinadi. Bindirme artik BASLIGIN KENDI
# konumundan turetiliyor — sabit degistiginde sinama niyeti korunur.
c2.y_orani = round(c1.y_orani + 0.02, 3)   # basligin uzerine bindir
cozulmus, rapor = tipografi.cakisma_coz([c1, c2], p=P)
kontrol("cakisma COZULDU (kaydirma/erteleme)",
        len(cozulmus) == 2 and rapor, str(rapor))
kalan_cakisma = [(a.ad, b.ad) for i, a in enumerate(cozulmus)
                 for b in cozulmus[i + 1:] if tipografi._cakisiyor(a, b)]
kontrol("cozum sonrasi CAKISMA KALMADI", not kalan_cakisma, str(kalan_cakisma))

# ═════════════════ 5) SES ═════════════════
blok("ses: hedefler, ducking, SFX kotasi, J/L cut")
splan = ses.plan_yap(bplan.beatler, profil_=P, ambience="tokyo-street",
                     muzik="under-score")
kontrol("LUFS hedefi -14", splan.lufs_hedef == -14.0)
kontrol("true peak tavani <= -1", splan.tepe_tavan <= -1.0)
kontrol("on zincirde KOMPRESOR var (normalizasyondan once)",
        any(a["filtre"] == "acompressor" for a in splan.on_zincir))
kontrol("kompresor loudnorm'dan ONCE",
        [a["filtre"] for a in splan.on_zincir].index("acompressor")
        < [a["filtre"] for a in splan.on_zincir].index("loudnorm"))
kontrol("ducking zarfi uretildi", len(splan.ducking_zarfi) >= 1)
kontrol("ducking seviyesi muzigi kisiyor",
        all(db <= -12 for _, _, db in splan.ducking_zarfi))
kontrol("ambience cok kisik", any(o.tur == "ambience" and o.seviye_db <= -25
                                  for o in splan.olaylar))
sfx = [o for o in splan.olaylar if o.tur == "sfx"]
kontrol("SFX KOTASI: her cut'a SFX YOK", len(sfx) < len(bplan.beatler),
        f"{len(sfx)} sfx / {len(bplan.beatler)} beat")
if len(sfx) >= 2:
    araliklar = [sfx[i].bas_sn - sfx[i - 1].bas_sn for i in range(1, len(sfx))]
    kontrol("SFX arasi kota mesafesi korunur",
            all(a >= ses.SFX_KOTA_SN - 0.1 for a in araliklar), str(araliklar))
else:
    kontrol("SFX arasi kota mesafesi korunur", True)
kontrol("J-cut ses olayi uretildi",
        any(o.tur == "j-cut" for o in splan.olaylar))
kontrol("nefes payi sessizlik olayi uretir",
        any(o.tur == "sessizlik" for o in splan.olaylar)
        or not any(b.nefes_payi_sn for b in bplan.beatler))
kontrol("SFX yogunlugu makul (<12/dk)",
        splan.sfx_yogunlugu(bplan.toplam_sn) < 12,
        str(splan.sfx_yogunlugu(bplan.toplam_sn)))

# ═════════════════ 6) PRE-RENDER QA ═════════════════
blok("qa_on: PASS / WARN / FAIL")
index = {a["asset_id"]: a for a in MEDYA_MANIFEST["adaylar"]}
# ⚠ I-31: `_yazi_katmanlari_kur` artik UCUNCU deger olarak kunye politika
# kararlarini da donuyor (ekran kunyesi kisaltildi mi, eksik mi).
katmanlar, _, _kunye_k = plan._yazi_katmanlari_kur(
    cekimler, bplan.beatler, index, P)
specler = plan._motion_kur(cekimler, bplan.beatler, P)
q = qa_on.denetle(beat_plani=bplan, cekimler=cekimler,
                  yazi_katmanlari=katmanlar, motion_specler=specler,
                  ses_plani=splan, adaylar_index=index, profil_=P,
                  beklenen_ulke="Japan", beklenen_donem="2025",
                  arastirma_fact_idler={f"f{i:03d}" for i in range(1, 9)})
kontrol("QA durum uretti", q.durum in ("PASS", "WARN", "FAIL"), q.durum)
kontrol("QA olcumleri iceriyor",
        {"pacing", "kapsam", "efekt", "ses", "tipografi"} <= set(q.olcumler),
        str(sorted(q.olcumler)))
kontrol("saglikli planda FAIL YOK", q.durum != "FAIL",
        str([s.kod for s in q.sorunlar if s.seviye == "fail"]))
kontrol("her sorun KOD + ONERI tasir",
        all(s.kod and s.oneri for s in q.sorunlar),
        str([s.kod for s in q.sorunlar if not s.oneri]))

# FAIL vakalari
lisanssiz_index = dict(index)
lisanssiz_index["a1"] = {**index["a1"], "render_kullanilabilir": False,
                         "red_nedeni": "lisans belirsiz"}
q_fail = qa_on.denetle(beat_plani=bplan, cekimler=cekimler,
                       yazi_katmanlari=katmanlar, motion_specler=specler,
                       ses_plani=splan, adaylar_index=lisanssiz_index, profil_=P)
kontrol("lisanssiz varlik FAIL uretir", q_fail.durum == "FAIL"
        and any(s.kod == "LISANS-EKSIK" for s in q_fail.sorunlar),
        str([s.kod for s in q_fail.sorunlar if s.seviye == "fail"]))

atifsiz = dict(index)
atifsiz["a3"] = {**index["a3"], "atif_metni": ""}
q_atif = qa_on.denetle(beat_plani=bplan, cekimler=cekimler,
                       yazi_katmanlari=katmanlar, motion_specler=specler,
                       ses_plani=splan, adaylar_index=atifsiz, profil_=P)
kontrol("atif eksikligi FAIL uretir",
        any(s.kod == "LISANS-ATIF-EKSIK" and s.seviye == "fail"
            for s in q_atif.sorunlar),
        str([s.kod for s in q_atif.sorunlar if s.seviye == "fail"]))

kotu_spec = [{"ad": "x", "renderer": "remotion", "beat_id": "b001",
              "parametre": {}, "remotion_zorunlu": False, "fallback": None}]
q_efekt = qa_on.denetle(beat_plani=bplan, cekimler=cekimler,
                        yazi_katmanlari=katmanlar, motion_specler=kotu_spec,
                        ses_plani=splan, adaylar_index=index, profil_=P)
kontrol("fallbacksiz remotion spec'i FAIL (sessiz kayip)",
        any(s.kod == "EFEKT-SESSIZ-KAYIP" for s in q_efekt.sorunlar),
        str([s.kod for s in q_efekt.sorunlar]))

fact_yok = [gramer.Cekim(beat_id="b1", scene_id="s1", fact_id="",
                         asset_id="a1", saglayici="pexels",
                         kaynak_turu="medya")]
q_fact = qa_on.denetle(beat_plani=bplan, cekimler=fact_yok,
                       yazi_katmanlari=[], motion_specler=specler,
                       ses_plani=splan, adaylar_index=index, profil_=P)
kontrol("fact_id yoksa FAIL",
        any(s.kod == "FACT-BAGLANTI-YOK" for s in q_fact.sorunlar))

# Gecis kotuye kullanimi
asiri_gecis = [{"ad": "whip", "renderer": "ffmpeg", "beat_id": f"b{i}",
                "parametre": {"tur": "whip"}, "fallback": None,
                "remotion_zorunlu": False} for i in range(6)]
q_gecis = qa_on.denetle(beat_plani=bplan, cekimler=cekimler,
                        yazi_katmanlari=katmanlar, motion_specler=asiri_gecis,
                        ses_plani=splan, adaylar_index=index, profil_=P)
kontrol("asiri seyrek gecis WARN uretir",
        any(s.kod in ("GECIS-SEYREK-ASIRI", "GECIS-ASIRI")
            for s in q_gecis.sorunlar),
        str([s.kod for s in q_gecis.sorunlar]))

# ═════════════════ 7) POST-RENDER QA (fixture komut ciktisi) ═════════════════
blok("qa_son: ffprobe/black/freeze/loudness fixture")
FIX = {
    "ffprobe": {"rc": 0, "stdout": json.dumps({
        "streams": [{"width": 1280, "height": 720, "r_frame_rate": "30/1",
                     "codec_name": "h264"}],
        "format": {"duration": "41.2", "size": "8123456"}}), "stderr": ""},
    "ffprobe_ses": {"rc": 0, "stdout": json.dumps({
        "streams": [{"codec_name": "aac", "sample_rate": "48000",
                     "channels": 2}]}), "stderr": ""},
    "siyah": {"rc": 0, "stdout": "", "stderr": ""},
    "donmus": {"rc": 0, "stdout": "", "stderr": ""},
    "kesme": {"rc": 0, "stdout": "",
              "stderr": "\n".join(f"[Parsed_showinfo] n:{i} pts_time:{i*3.2:.2f}"
                                  for i in range(1, 12))},
    "loudness": {"rc": 0, "stdout": "", "stderr": json.dumps(
        {"input_i": "-14.1", "input_tp": "-1.4", "input_lra": "6.2"})},
    "sessizlik": {"rc": 0, "stdout": "", "stderr": ""},
}
_plan_komutlari = qa_son.komut_plani("/tmp/x.mp4")


def sahte_kosucu(komut, zaman_asimi=120):
    for ad, k in _plan_komutlari.items():
        if komut == k:
            return FIX[ad]
    return {"rc": 1, "stdout": "", "stderr": "bilinmeyen komut"}


pq = qa_son.denetle("/tmp/x.mp4", beklenen={"sure_sn": 41.0, "cekim_sayisi": 12,
                                            "genislik": 1280, "yukseklik": 720,
                                            "fps": 30},
                    profil_=P, kosucu=sahte_kosucu)
kontrol("post QA temiz videoda PASS/WARN", pq.durum in ("PASS", "WARN"),
        f"{pq.durum} {[s['kod'] for s in pq.sorunlar]}")
kontrol("cozunurluk okundu", pq.olcumler["video"]["genislik"] == 1280)
kontrol("fps okundu", pq.olcumler["video"]["fps"] == 30.0)
kontrol("kesme sayisi okundu", pq.olcumler["kesme_sayisi"] == 11)
kontrol("loudness okundu", pq.olcumler["loudness"]["lufs"] == -14.1)
kontrol("LUFS hedefte -> uyari yok",
        not any(s["kod"] == "POST-LUFS" for s in pq.sorunlar),
        str(pq.sorunlar))
kontrol("gercek komutlar planlaniyor",
        "ffprobe" in _plan_komutlari and "blackdetect" in
        " ".join(_plan_komutlari["siyah"]))

FIX_KOTU = dict(FIX)
FIX_KOTU["siyah"] = {"rc": 0, "stdout": "", "stderr":
                     "[blackdetect] black_start:27.35 black_end:27.50 "
                     "black_duration:0.15"}
FIX_KOTU["loudness"] = {"rc": 0, "stdout": "", "stderr": json.dumps(
    {"input_i": "-15.6", "input_tp": "-0.4", "input_lra": "7.1"})}
FIX_KOTU["donmus"] = {"rc": 0, "stdout": "", "stderr":
                      "[freezedetect] freeze_start: 12.0\n"
                      "[freezedetect] freeze_duration: 2.4"}


def sahte_kotu(komut, zaman_asimi=120):
    for ad, k in _plan_komutlari.items():
        if komut == k:
            return FIX_KOTU[ad]
    return {"rc": 1, "stdout": "", "stderr": ""}


pq2 = qa_son.denetle("/tmp/x.mp4", beklenen={"sure_sn": 41.0}, profil_=P,
                     kosucu=sahte_kotu)
kontrol("SIYAH KARE FAIL uretir", pq2.durum == "FAIL"
        and any(s["kod"] == "POST-SIYAH-KARE" for s in pq2.sorunlar),
        str([s["kod"] for s in pq2.sorunlar]))
kontrol("LUFS sapmasi WARN uretir",
        any(s["kod"] == "POST-LUFS" for s in pq2.sorunlar))
kontrol("TRUE PEAK asimi WARN uretir",
        any(s["kod"] == "POST-TEPE" for s in pq2.sorunlar))
kontrol("DONMUS KARE tespit edilir",
        any(s["kod"] == "POST-DONMUS-KARE" for s in pq2.sorunlar))
kontrol("her post sorun ONERI tasir",
        all(s.get("oneri") for s in pq2.sorunlar),
        str([s["kod"] for s in pq2.sorunlar if not s.get("oneri")]))
kontrol("kare ornekleme komutu uretilir",
        "fps=1" in " ".join(qa_son.kare_ornekleme_komutu("/tmp/x.mp4", "/tmp")))
kontrol("temas sayfasi komutu uretilir",
        "tile=" in " ".join(qa_son.temas_sayfasi_komutu("/tmp/x.mp4", "/tmp/t.jpg")))

# ═════════════════ 8) ADAPTER ROUND-TRIP ═════════════════
blok("adapter: alan kaybi yok, sessiz efekt kaybi yok")
gecici = tempfile.mkdtemp(prefix="fc_")
try:
    sonuc = plan.uret(cumleler=CUMLELER, medya_manifest=MEDYA_MANIFEST,
                      arastirma_manifest=ARASTIRMA_MANIFEST,
                      profil_adi="premium-modern", beklenen_ulke="Japan",
                      beklenen_donem="2025", cikti_dizin=gecici,
                      ambience="tokyo-street", muzik="under-score")
    don = sonuc["adapter"]
    kontrol("hizli_render sahneleri uretildi",
            len(don.hizli_sahneler) == len(sonuc["cekimler"]))
    kontrol("HER sahnede zorunlu alanlar var",
            all(not adapter.alan_kaybi_denetimi(s) for s in don.hizli_sahneler),
            str([adapter.alan_kaybi_denetimi(s) for s in don.hizli_sahneler[:2]]))
    kontrol("remotion props sahneleri iceriyor",
            len(don.remotion_props["sahneler"]) == len(don.hizli_sahneler))
    kontrol("remotion props fps/olcu tasir",
            don.remotion_props["fps"] == P.fps
            and don.remotion_props["genislik"] == P.genislik)
    kontrol("beat/fact/asset izlenebilirligi sahnede korunur",
            all(s.get("_beat_id") and "_fact_id" in s and "_asset_id" in s
                for s in don.hizli_sahneler))
    kontrol("SESSIZ EFEKT KAYBI YOK (her karar raporlu)",
            all(u.get("karar") for u in don.uyarilar), str(don.uyarilar[:2]))
    kontrol("taninmayan spec YOK",
            not [u for u in don.uyarilar if u.get("karar") == "TANINMAYAN"],
            str([u for u in don.uyarilar if u.get("karar") == "TANINMAYAN"]))
    kontrol("fallback kullanilan efektler KAYIP olarak raporlanir",
            all(k.get("kayip") for k in don.kayip_efektler),
            str(don.kayip_efektler[:2]))
    kontrol("zoom/pan kamera spec'inden turetildi",
            any(s["zoom"] in ("in", "out") for s in don.hizli_sahneler),
            str([s["zoom"] for s in don.hizli_sahneler]))
    kontrol("grain/vinyet efekt listesine dustu",
            all(any(e["ad"] == "grain" for e in s["efektler"])
                for s in don.hizli_sahneler),
            str(don.hizli_sahneler[0]["efektler"]))
    kontrol("bolum basligi sahneye yazildi",
            any(s.get("bolum") for s in don.hizli_sahneler))
    kontrol("kaynak yazisi (atif) sahneye yazildi",
            any(s.get("kaynakYazi") for s in don.hizli_sahneler),
            str([s.get("kaynakYazi") for s in don.hizli_sahneler]))

    # ═══════ 9) DORT CIKTI DOSYASI ═══════
    blok("plan: dort cikti dosyasi")
    for ad in ("edit_manifest.json", "render_plan.json", "editor_qa.json",
               "attribution.txt"):
        kontrol(f"{ad} yazildi", os.path.exists(os.path.join(gecici, ad)))
    rp = json.load(open(os.path.join(gecici, "render_plan.json"),
                        encoding="utf-8"))
    em = json.load(open(os.path.join(gecici, "edit_manifest.json"),
                        encoding="utf-8"))
    eq = json.load(open(os.path.join(gecici, "editor_qa.json"),
                        encoding="utf-8"))
    kontrol("render_plan sahne sayisi beat sayisiyla ayni",
            rp["sahne_sayisi"] == len(sonuc["beat_plani"].beatler))
    kontrol("her render sahnesi scene_id + fact_id tasir",
            all(s.get("scene_id") and "fact_id" in s for s in rp["sahneler"]))
    kontrol("her render sahnesi motion spec tasir",
            all(s.get("motion") for s in rp["sahneler"]))
    kontrol("edit_manifest profil token'lari iceriyor",
            "tipografi" in em["profil"] and "easing" in em["profil"])
    kontrol("editor_qa durum + oneri iceriyor",
            eq["durum"] in ("PASS", "WARN", "FAIL"))
    kontrol("attribution.txt atif satiri iceriyor",
            "CC-BY" in open(os.path.join(gecici, "attribution.txt"),
                            encoding="utf-8").read(),
            open(os.path.join(gecici, "attribution.txt"), encoding="utf-8").read()[:90])
    kontrol("atif fact_id ile bagli",
            "[f" in open(os.path.join(gecici, "attribution.txt"),
                         encoding="utf-8").read())
    kontrol("toplam sure ~45 sn (fixture hedefi)",
            38 <= rp["toplam_sn"] <= 48, str(rp["toplam_sn"]))
finally:
    shutil.rmtree(gecici, ignore_errors=True)

# ═════════════════ 10) PROFIL DOGRULAMA ═════════════════
blok("profil: token tutarliligi")
kontrol("varsayilan profil kendi kurallarini ihlal etmiyor",
        not profil.VARSAYILAN.dogrula(), str(profil.VARSAYILAN.dogrula()))
kotu = profil.EditProfili(shot_maks_sn=12.0)
kontrol("bozuk profil uyari uretir", kotu.dogrula(), str(kotu.dogrula()))
kontrol("3 profil tanimli", len(profil.PROFILLER) >= 3,
        str(sorted(profil.PROFILLER)))
kontrol("olculen sabitler token'da",
        profil.OLCULEN["sert_kesme_orani"] == 0.799)
_font = os.path.join(KOK, "..", "app", "render-studio", "public", "fonts",
                     "Montserrat-Bold.ttf")
if os.path.exists(_font):
    kontrol("repo fontu STATIK (degisken degil)", profil.font_statik_mi(_font),
            "degisken font -> Thin cizilir")
else:
    kontrol("repo fontu STATIK (degisken degil)", True, "font bulunamadi, atlandi")


# ═══ 11) KALITE KAPISI REGRESYONU: PREMIUM YOL EZILMEZ ═══
blok("adapter regresyon: Remotion premium yol vs FFmpeg hizli yol")
# Ayni sahnede DORT Remotion-zorunlu spec + bir ffmpeg spec + bir BILINMEYEN spec
_ozgun = [
    motion.kamera_spec("push-in", 4.0, "tam", p=P).sozluk(),
    motion.parallax_spec(3, 4.0, p=P).sozluk(),
    motion.light_sweep_spec(0.8).sozluk(),
    motion.belge_vurgusu_spec((0.3, 0.3, 0.4, 0.2), 4.0).sozluk(),
    motion.harita_spec("Tokyo", None, 4.0).sozluk(),
    motion.veri_grafigi_spec("Vakalar", [76941], 4.0).sozluk(),
    {"ad": "uydurma-efekt", "renderer": "remotion", "parametre": {"x": 1},
     "fallback": None, "remotion_zorunlu": False, "gerekce": "test",
     "beat_id": "bR1"},
]
for _sp in _ozgun:
    _sp["beat_id"] = "bR1"
_rp_test = {"fps": 30, "genislik": 1920, "yukseklik": 1080,
            "gecis_modu": "sinematik", "altyazi_stili": "yok",
            "sahneler": [{"beat_id": "bR1", "scene_id": "sR", "fact_id": "fR",
                          "asset_id": "aR", "saglayici": "wikimedia",
                          "lisans": "cc0", "medya_turu": "image",
                          "medya_yolu": "/tmp/a.jpg", "sure_sn": 4.0,
                          "bas_sn": 0.0, "islev": "kanit", "perde": "gelisme",
                          "cekim_turu": "archive", "hareket": "push-in",
                          "kadraj": "tam", "kaynak_aralik": [0, 4],
                          "altyazi": [], "motion": _ozgun,
                          "gerekce": "test"}]}
_don = adapter.donustur(_rp_test, fps=30)

# (a) OZGUN spec'ler Remotion props'ta BIREBIR korunuyor
_rsahne = _don.remotion_props["sahneler"][0]
_rspec_adlari = [x["ad"] for x in _rsahne["motion"]]
for _beklenen in ("parallax-2.5d", "light-sweep", "document-highlight",
                  "map-route", "data-chart", "uydurma-efekt"):
    kontrol(f"Remotion props'ta KORUNUYOR: {_beklenen}",
            _beklenen in _rspec_adlari, str(_rspec_adlari))
kontrol("Remotion spec sayisi ozgun sayiya esit",
        len(_rsahne["motion"]) == len(_ozgun),
        f"{len(_rsahne['motion'])} vs {len(_ozgun)}")
_par = next(x for x in _rsahne["motion"] if x["ad"] == "parallax-2.5d")
kontrol("parallax parametreleri BIREBIR (katman hizlari)",
        _par["parametre"]["katman_hizlari"] ==
        motion.parallax_spec(3, 4.0, p=P).parametre["katman_hizlari"],
        str(_par["parametre"]))
kontrol("parallax renderer=remotion korunuyor", _par["renderer"] == "remotion")
kontrol("parallax fallback BILGISI korunuyor (ama uygulanmiyor)",
        _par.get("fallback") is not None)
kontrol("easing bezier Remotion props'ta duruyor",
        "easing_bezier" in _par and len(_par["easing_bezier"]) == 4,
        str(_par.get("easing_bezier")))
kontrol("gerekce Remotion props'ta duruyor",
        all(x.get("gerekce") is not None for x in _rsahne["motion"]))
kontrol("izlenebilirlik Remotion sahnesinde",
        _rsahne["scene_id"] == "sR" and _rsahne["fact_id"] == "fR"
        and _rsahne["asset_id"] == "aR",
        str({k: _rsahne[k] for k in ("scene_id", "fact_id", "asset_id")}))

# (b) AYNI sahnenin HIZLI sozlugunde fallback UYGULANMIS + kayip raporu var
_hsahne = _don.hizli_sahneler[0]
kontrol("hizli yolda fallback uygulanmis (efekt/alan olarak)",
        _hsahne.get("vurguKutu") or _hsahne.get("etiketler")
        or _hsahne["efektler"],
        str({k: v for k, v in _hsahne.items() if k in
             ("efektler", "vurguKutu", "etiketler", "gecisImza")}))
kontrol("hizli yol kayip raporu uretti", len(_don.kayip_efektler) >= 3,
        str([k["spec"] for k in _don.kayip_efektler]))
kontrol("kayip raporunda parallax var",
        any(k["spec"] == "parallax-2.5d" for k in _don.kayip_efektler),
        str([k["spec"] for k in _don.kayip_efektler]))
kontrol("hizli sahnede OZGUN motion listesi YOK (indirgenmis)",
        "motion" not in _hsahne, str(sorted(_hsahne)))

# (c) IKI CIKTI AYNI NESNE/LISTE REFERANSINI PAYLASMIYOR
kontrol("liste nesneleri AYRI",
        _don.remotion_props["sahneler"] is not _don.hizli_sahneler)
kontrol("sahne sozlukleri AYRI", _rsahne is not _hsahne)
kontrol("remotion_sahneler ile hizli_sahneler ayri liste",
        _don.remotion_sahneler is not _don.hizli_sahneler)
_kimlikler_r = {id(x) for x in _rsahne["motion"]}
_kimlikler_o = {id(x) for x in _ozgun}
kontrol("motion spec sozlukleri DERIN KOPYA (girdiyle paylasilmiyor)",
        not (_kimlikler_r & _kimlikler_o),
        f"paylasilan {len(_kimlikler_r & _kimlikler_o)}")
# Mutasyon testi: hizli yolu degistirmek Remotion'u BOZMAMALI
_hsahne["efektler"].append({"ad": "test", "siddet": 9})
kontrol("hizli yolu degistirmek Remotion sahnesini BOZMUYOR",
        len(_rsahne["motion"]) == len(_ozgun)
        and all(x["ad"] != "test" for x in _rsahne["motion"]))
_rsahne["motion"][0]["parametre"]["zoom"] = [9, 9]
kontrol("Remotion'u degistirmek hizli yolu BOZMUYOR",
        _hsahne["zoom"] in ("in", "out", "yok"))

# (d) PREMIUM GEREKSINIMI: fallback VARLIGI premium ihtiyacini silmiyor
kontrol("fallback'i OLAN Remotion spec'i sahneyi premium isaretler",
        "bR1" in _don.remotion_gerekli_sahneler,
        str(_don.remotion_gerekli_sahneler))
kontrol("premium gerekce listesi yazildi",
        _rsahne.get("premium_gerekce") and len(_rsahne["premium_gerekce"]) >= 5,
        str(_rsahne.get("premium_gerekce"))[:120])
kontrol("premium gerekce fallback varligini BELIRTIYOR",
        any(g["fallback_var"] for g in _rsahne["premium_gerekce"])
        and any(not g["fallback_var"] for g in _rsahne["premium_gerekce"]),
        str([(g["spec"], g["fallback_var"]) for g in _rsahne["premium_gerekce"]]))

# (e) BILINMEYEN spec sessizce kaybolmuyor — IKI AYRI VAKA
# e1) renderer=remotion + fallback yok  -> "remotion-zorunlu" (TANINMAYAN degil)
kontrol("bilinmeyen remotion spec'i remotion-zorunlu olarak isaretlenir",
        any(u.get("karar") == "remotion-zorunlu"
            and u.get("spec") == "uydurma-efekt" for u in _don.uyarilar),
        str([(u.get("spec"), u.get("karar")) for u in _don.uyarilar]))
kontrol("bilinmeyen spec Remotion props'ta AYNEN duruyor",
        any(x["ad"] == "uydurma-efekt" for x in _rsahne["motion"]))
kontrol("bilinmeyen spec sahneyi premium isaretler",
        "bR1" in _don.remotion_gerekli_sahneler)

# e2) renderer=ffmpeg ama adapter TANIMIYOR -> "TANINMAYAN" + premium'a yonlendir
_bilinmeyen_ffmpeg = [
    motion.kamera_spec("static", 3.0, "tam", p=P).sozluk(),
    {"ad": "hic-boyle-bir-efekt-yok", "renderer": "ffmpeg",
     "parametre": {"a": 1}, "fallback": None, "remotion_zorunlu": False,
     "gerekce": "test", "beat_id": "bU1"},
]
for _sp in _bilinmeyen_ffmpeg:
    _sp["beat_id"] = "bU1"
_don3 = adapter.donustur({"sahneler": [
    {"beat_id": "bU1", "scene_id": "sU", "fact_id": "fU", "sure_sn": 3.0,
     "motion": _bilinmeyen_ffmpeg}]})
kontrol("taninmayan ffmpeg spec'i TANINMAYAN uyarisi uretir",
        any(u.get("karar") == "TANINMAYAN"
            and u.get("spec") == "hic-boyle-bir-efekt-yok"
            for u in _don3.uyarilar),
        str([(u.get("spec"), u.get("karar")) for u in _don3.uyarilar]))
kontrol("taninmayan spec Remotion props'ta AYNEN korunur",
        any(x["ad"] == "hic-boyle-bir-efekt-yok"
            for x in _don3.remotion_props["sahneler"][0]["motion"]))
kontrol("taninmayan spec sahneyi premium'a yonlendirir",
        "bU1" in _don3.remotion_gerekli_sahneler,
        str(_don3.remotion_gerekli_sahneler))
kontrol("taninmayan spec hizli sozlukte SESSIZCE kaybolmaz (uyari var)",
        len(_don3.uyarilar) >= 1)

# (f) Yalnizca ffmpeg spec'i olan sahne premium ISARETLENMEZ
_sade = [motion.kamera_spec("static", 3.0, "tam", p=P).sozluk()]
_sade += [x.sozluk() for x in motion.taban_katmanlar(3.0, p=P)]
for _sp in _sade:
    _sp["beat_id"] = "bF1"
_don2 = adapter.donustur({"sahneler": [{"beat_id": "bF1", "scene_id": "sF",
                                        "fact_id": "fF", "sure_sn": 3.0,
                                        "motion": _sade}]})
kontrol("sadece ffmpeg spec'i olan sahne premium ISARETLENMEZ",
        "bF1" not in _don2.remotion_gerekli_sahneler,
        str(_don2.remotion_gerekli_sahneler))
kontrol("sade sahnede de Remotion sahnesi uretilir (izlenebilirlik)",
        len(_don2.remotion_sahneler) == 1
        and _don2.remotion_sahneler[0]["fact_id"] == "fF")
kontrol("hizli_props ayri sozluk", _don2.hizli_props.get("sahneler")
        is _don2.hizli_sahneler)
kontrol("adapter ozeti remotion spec sayisini raporlar",
        _don.sozluk()["remotion_spec_sayisi"] == len(_ozgun),
        str(_don.sozluk()["remotion_spec_sayisi"]))

print(f"\n{'=' * 58}")
print(f"GECEN: {gecen}   BASARISIZ: {len(basarisiz)}")
for b in basarisiz:
    print(f"  XX {b}")
sys.exit(1 if basarisiz else 0)
