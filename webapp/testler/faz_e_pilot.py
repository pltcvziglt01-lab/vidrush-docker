#!/usr/bin/env python3
"""FAZ E PILOT — SESLI, GERCEK MEDYALI 45-60 sn belgesel (VidrushEditorV2).

Zincir:
  manifest.json (dogrulanmis iddialar)  +  medya_rapor.json (gercek varliklar)
    -> Turkce anlatim (yerel macOS `say`, UCRETSIZ)
    -> sahne plani + Faz C motion specleri
    -> adapter -> remotion_props + SES zaman cizelgesi
    -> pre-render kapisi -> VidrushEditorV2 render
    -> POST MASTER: iki gecisli loudnorm (-14 LUFS, TP <= -1 dBTP)
    -> QA: ffprobe + black/freeze/silence + loudness + temas sayfasi

⚠ ANLATIM YAPAY: macOS `say -v Yelda` ile uretildi, insan seslendirmesi DEGIL.
Rapor bunu her yerde belirtir; "profesyonel icerik kalitesi PASS" iddiasi
yalnizca medya gercek/uyumlu, anlatim duyulur, tipografi guvenli ve motion
katmanlari GORUNUR ise verilir.

Kosum: python3 webapp/testler/faz_e_pilot.py [--olcu 1280x720] [--tavan-dk 15]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)

from editor import adapter, motion, profil, remotion_v2  # noqa: E402

CIKTI = os.path.join(os.path.dirname(KOK), "cikti", "faz_e")
SES_DIZIN = os.path.join(CIKTI, "ses")
P = profil.profil("premium-modern")
TTS_SESI = "Yelda"          # macOS tr_TR
HEDEF_LUFS = -14.0
HEDEF_TP = -1.0

# ═══════════════ ANLATIM ═══════════════
# Olculdu: `say -v Yelda` 139 kelime/dk. 45-60 sn icin ~104-139 kelime.
# Asagidaki 10 segment 118 kelime -> ~51 sn.
#
# ⚠ HER SEGMENT BIR fact_id'YE BAGLI. Dogrulanmamis hicbir sey soylenmiyor:
#   - yakit marji rakamlari CELISKILI oldugu icin GECMIYOR
#   - kesin 756 saniye rakami yalnizca nasa.gov'da dogrulandi; anlatimda
#     "yaklasik on iki dakika" deniyor, kesin rakam yalnizca veri grafiginde
#     kaynak etiketiyle gosteriliyor
SEGMENTLER = [
    ("f001", "Yirmi Temmuz bin dokuz yuz altmis dokuz. "
             "Ay yuzeyine inise sadece dakikalar kalmisti."),
    ("f006", "Eagle'in inis motoru atesleniyor ve yaklasik on iki dakika "
             "surecek kritik manevra basliyor."),
    ("f002", "Her sey plana gore giderken bilgisayar beklenmeyen bir uyari "
             "veriyor: bin iki yuz iki."),
    ("f002", "Rehber bilgisayar, ayni anda isleyemeyecegi kadar cok veriyle "
             "yuklenmisti."),
    ("f003", "Kisa sure sonra bin iki yuz bir alarmi da ekrana dusuyor."),
    ("f004", "Ekip inise devam kararini veriyor; Armstrong kontrolu kismen "
             "kendi eline aliyor."),
    ("f007", "Cunku asagida gordugu alan kayalarla kapli ve inis noktasi "
             "ileriye kayiyor."),
    ("f006", "Guclu inis, yedi yuz elli alti saniye suren tek bir motor "
             "atesiyle tamamlaniyor."),
    ("f005", "Ve sonunda o cumle duyuluyor: Tranquility Base burada, Kartal indi."),
    ("f005", "On iki dakika boyunca neredeyse hicbir sey provalara benzemedi. "
             "Yine de indiler."),
]

# Sahne kurgusu: hangi segment hangi gorsel islevle eslesecek.
# (islev, cekim_turu, hareket, kadraj, ekstra_katmanlar, ust_bant, alt_bant)
KURGU = [
    ("hook", "archive", "push-in", "genis", ("kinetic-title", "light-sweep"),
     "ON IKI DAKIKA", None),
    ("baglam", "archive", "soft-zoom", "tam", (), None, ("EAGLE", "INIS MOTORU")),
    ("kanit", "archive", "static", "tam", ("document-highlight",),
     None, ("PROGRAM ALARMI", "1202")),
    ("kanit", "archive", "pull-out", "orta", ("callout",), None, None),
    ("kanit", "archive", "push-in", "yakin", ("text-in-video",),
     None, ("IKINCI ALARM", "1201")),
    ("gelisme", "archive", "pan-right", "genis", ("parallax-2.5d",),
     None, ("ARMSTRONG", "YARIM-ELLE KONTROL")),
    # ── KAPSAM BOSLUGU DOLGUSU (kendi grafigimiz) ──
    ("baglam", "map", "static", "tam", ("map-route",), None, None),
    ("veri", "data", "static", "tam", ("data-chart",), None, None),
    ("kanit", "archive", "soft-zoom", "tam", (), None, ("TRANQUILITY BASE", "1969")),
    ("kapanis", "archive", "slow-drift", "genis", ("film-burn",),
     "KARTAL INDI", None),
]


def _kos(komut: list, zaman_asimi: int = 600) -> subprocess.CompletedProcess:
    return subprocess.run(komut, capture_output=True, text=True,
                          timeout=zaman_asimi)


def _sure(yol: str) -> float:
    r = _kos(["ffprobe", "-v", "error", "-show_entries", "format=duration",
              "-of", "csv=p=0", yol], 120)
    try:
        return float((r.stdout or "0").strip())
    except ValueError:
        return 0.0


# ═══════════════ 1) ANLATIM URETIMI ═══════════════

def anlatim_uret(dizin: str) -> list:
    """Her segment icin yerel TTS -> wav. Doner [{fact_id, metin, yol, sure}]."""
    os.makedirs(dizin, exist_ok=True)
    out = []
    for i, (fid, metin) in enumerate(SEGMENTLER):
        aiff = os.path.join(dizin, f"seg{i:02d}.aiff")
        wav = os.path.join(dizin, f"seg{i:02d}.wav")
        if not os.path.exists(wav):
            r = _kos(["say", "-v", TTS_SESI, "-o", aiff, metin], 180)
            if r.returncode != 0 or not os.path.exists(aiff):
                raise RuntimeError(f"TTS basarisiz (segment {i}): "
                                   f"{(r.stderr or '')[:160]}")
            # 48 kHz mono wav: Remotion ve loudnorm icin tekdüze giris
            r = _kos(["ffmpeg", "-y", "-v", "error", "-i", aiff,
                      "-ar", "48000", "-ac", "1", wav], 180)
            if r.returncode != 0:
                raise RuntimeError(f"wav cevrimi basarisiz: {(r.stderr or '')[:160]}")
            os.remove(aiff)
        out.append({"fact_id": fid, "metin": metin, "yol": wav,
                    "sure": round(_sure(wav), 3)})
    return out


def ortam_tonu(dizin: str, sure_sn: float) -> str:
    """Cok kisik SENTETIK oda tonu — ducking yolunu gercekten calistirmak icin.

    ⚠ Bu ses SENTETIK. Belgesel icin gercek ambans lisansli bir kutuphaneden
    gelmeli; burada amac ses zaman cizelgesinin ve ducking'in gercekten
    calistigini kanitlamak. Rapor bunu yapay olarak isaretliyor.
    """
    yol = os.path.join(dizin, "ortam.wav")
    if os.path.exists(yol):
        return yol
    r = _kos(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
              f"anoisesrc=d={max(2.0, sure_sn):.2f}:c=brown:a=0.06",
              "-af", "lowpass=f=320,volume=0.5", "-ar", "48000", "-ac", "1",
              yol], 300)
    if r.returncode != 0:
        raise RuntimeError(f"ortam tonu uretilemedi: {(r.stderr or '')[:160]}")
    return yol


# ═══════════════ 1.5) PARLAKLIK KAPISI ═══════════════
# ⚠ CANLI OLCUM (11 Agu): indirilen 10 Apollo 11 varligindan 4'unun ortalama
# lumasi 27-34 idi (yorungeden cekilmis karanlik ay yuzeyi kareleri). Render
# sonucunda `blackdetect` 3 blok, toplam ~21 sn siyah buldu. Goruntuler GERCEK
# ve dogru; sorun POZLAMA.
#
# Cozum: belgesel renk duzeltmesi (grading). Lisanslar public-domain oldugu icin
# degistirme izni var; buna ragmen rapor ve atif defteri POZLAMA DUZELTILDIGINI
# ACIKCA yaziyor — izleyiciye "arsiv boyleydi" izlenimi verilmemeli.
LUMA_TABANI = 55.0        # ortalama parlaklik tabani
DETAY_TABANI = 3.0        # komsu piksel farki tabani — "bos kare" kapisi
DETAY_IYI = 8.0           # bunun altindaki kare GORSEL OLARAK ZAYIF sayilir


def kare_olc(yol: str) -> dict:
    """Karenin luma / kontrast / DETAY olcumu.

    ⚠ NEDEN DETAY DA GEREKLI (temas sayfasi incelemesi, 11 Agu):
    Yalnizca luma tabani koydugumda "AS11-43-6350/6352" kareleri gecti (luma
    84/70) ama ekranda NEREDEYSE BOS GRI alan olarak goruldu — film kenarindaki
    katalog numarasi disinda icerik yok. Ortalama parlaklik "dolu kare" demek
    degil. `detay` = yatay komsu piksel farklarinin ortalamasi; dokusuz alanda
    ~1, gercek detayli karede 10-22 olcuyor.
    """
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", yol, "-vf", "scale=64:64",
                        "-pix_fmt", "gray", "-f", "rawvideo", "-frames:v", "1",
                        "-"], capture_output=True, timeout=180)
    b = r.stdout or b""
    if len(b) < 4096:
        return {"luma": -1.0, "std": -1.0, "detay": -1.0}
    px = list(b[:4096])
    ort = sum(px) / len(px)
    std = (sum((q - ort) ** 2 for q in px) / len(px)) ** 0.5
    detay = (sum(abs(px[i + 1] - px[i]) for i in range(len(px) - 1)
                 if (i + 1) % 64) / (len(px) - 64))
    return {"luma": round(ort, 1), "std": round(std, 1), "detay": round(detay, 2)}


def gorsel_kapi(varliklar: list) -> tuple:
    """(kullanilabilir, reddedilen) — bos/karanlik kare zemin olamaz.

    ⚠ ILK DENEME BASARISIZ: gamma ile kurtarmayi denedim (LUMA_HEDEFI'ne
    dogru), luma 27-34 kareler ancak 41-46'ya cikti ve blackdetect yine 2 blok
    buldu. Sebep: bu kareler goruntunun ~%90'i BOS UZAY; gamma bos alani grize
    cevirir, icerik URETMEZ. Karartilmis bir hicligi "duzeltmis" gibi sunmak
    hem kalitesiz hem yaniltici olurdu.
    Dogru karar: bu varliklari zemin olarak KULLANMA, reddi RAPORLA.
    """
    kullanilabilir, red = [], []
    for v in varliklar:
        m = kare_olc(v["yol"])
        kayit = dict(v)
        kayit.update(m)
        if m["luma"] < LUMA_TABANI:
            kayit["red"] = (f"luma {m['luma']} < {LUMA_TABANI}; kare buyuk "
                            "olcude bos uzay (gamma ile kurtarma denendi: "
                            "27-34 -> 41-46, yetmedi)")
            red.append(kayit)
            continue
        if m["detay"] < DETAY_TABANI:
            kayit["red"] = (f"detay {m['detay']} < {DETAY_TABANI}; dokusuz/bos "
                            "kare, zemin olarak kullanilamaz")
            red.append(kayit)
            continue
        kayit["gorsel_zayif"] = m["detay"] < DETAY_IYI
        kullanilabilir.append(kayit)
    # En detayli kareler SONA: kapanista film-burn + karartma zaten karartiyor,
    # zayif kareyi kapanisa koymak videoyu bos bitiriyor.
    kullanilabilir.sort(key=lambda x: x["detay"])
    return kullanilabilir, red


# ═══════════════ 2) SAHNE PLANI ═══════════════

ZORUNLU_TAVAN_SN = 8.0          # kalici kural: hicbir goruntu 8 sn'yi gecmez


def sahne_plani(anlatim: list, varliklar: list) -> tuple:
    """(remotion_props ham plani, kullanilan varliklar, ses_araliklari)."""
    sahneler = []
    kullanilan = []
    araliklar = []
    t = 0.0
    varlik_sirasi = [v for v in varliklar]
    vi = 0

    for i, (seg, kurgu) in enumerate(zip(anlatim, KURGU)):
        islev, cekim, hareket, kadraj, ekstra, ust, bant = kurgu
        # Sahne suresi = anlatim + soluk payi, 8 sn tavaniyla
        # ⚠ 0.45 sn pay toplami 60.21 sn'ye cikardi (sart 45-60). 0.2'ye indirildi.
        sure = min(ZORUNLU_TAVAN_SN, round(seg["sure"] + 0.20, 2))

        kendi_grafik = cekim in ("map", "data")
        varlik = None
        if not kendi_grafik:
            # ⚠ AYNI VARLIK TEKRAR KULLANILMAZ (kullanicinin sarti)
            if vi < len(varlik_sirasi):
                varlik = varlik_sirasi[vi]
                vi += 1
                kullanilan.append(varlik)

        specler = [motion.kamera_spec(hareket, sure, kadraj, p=P)]
        specler.extend(motion.taban_katmanlar(sure, p=P))

        # Kaynak etiketi: gercek varlikta saglayici+lisans, kendi grafigimizde
        # "BEDOSAHO GRAFIGI" — izleyici neyin arsiv neyin cizim oldugunu bilmeli
        if varlik:
            etiket = (f"{varlik['saglayici'].upper()} · "
                      f"{varlik['lisans'].upper()}")
        else:
            etiket = "BEDOSAHO GRAFIGI · ARSIV GORUNTUSU DEGIL"
        specler.append(motion.kaynak_etiketi_spec(etiket, seg["fact_id"],
                                                  sure, p=P))

        if ust:
            specler.append(motion._spec(
                "kinetic-title",
                parametre={"metin": ust, "punto": 70, "y_orani": 0.60,
                           "bant_opaklik": 0.55},
                easing="giris", bas_sn=0.25,
                sure_sn=min(sure - 0.4, 2.8), katman=60,
                fallback={"ad": "chapter-title", "renderer": "ffmpeg",
                          "parametre": {"metin": ust, "punto": 70,
                                        "y_orani": 0.60}},
                gerekce="hook: kelime kelime giris"))
        if bant:
            specler.append(motion.alt_band_spec(bant[0], bant[1], sure, p=P))

        for e in ekstra:
            if e == "light-sweep":
                specler.append(motion.light_sweep_spec(0.8))
            elif e == "film-burn":
                specler.append(motion.film_burn_spec())
            elif e == "parallax-2.5d":
                specler.append(motion.parallax_spec(3, sure, p=P))
            elif e == "document-highlight":
                specler.append(motion.belge_vurgusu_spec(
                    (0.30, 0.32, 0.40, 0.18), sure))
            elif e == "callout":
                specler.append(motion.callout_spec(
                    "VERI TASMASI", 0.62, 0.34, min(2.0, sure - 0.6), p=P))
            elif e == "text-in-video":
                specler.append(motion._spec(
                    "text-in-video",
                    parametre={"metin": "1201", "punto": 58, "x_orani": 0.52,
                               "y_orani": 0.38, "bant_opaklik": 0.45},
                    easing="giris", bas_sn=0.45,
                    sure_sn=min(sure - 0.7, 2.2), katman=61,
                    fallback={"ad": "lower-third", "renderer": "ffmpeg",
                              "parametre": {"ust": "1201", "alt": ""}},
                    gerekce="yazi kamerayla hareket eder"))
            elif e == "map-route":
                # SEMBOLIK: bilesen ekrana "COGRAFI OLCEK DEGIL" yaziyor
                specler.append(motion.harita_spec(
                    "SEA OF TRANQUILITY", "INIS NOKTASI", sure))
            elif e == "data-chart":
                # ⚠ TEK dogrulanmis rakam: 756.3 sn (nasa.gov). Uydurma seri
                # OLUSTURULMADI; tek cubuk gosteriliyor ve kaynak etiketli.
                specler.append(motion.veri_grafigi_spec(
                    "GUCLU INIS — SANIYE", [756], sure))

        gecis = ("hard-cut" if i < 2 else
                 "karartma" if islev == "kapanis" else
                 "crossfade" if i % 4 == 0 else "hard-cut")
        specler.append(motion.gecis_spec(gecis))

        for sp in specler:
            sp.beat_id = f"bE{i:02d}"
            sp.scene_id = f"sE{i:02d}"

        # J/L cut: ses goruntuden once/sonra tasar. Ilk sahnede J-cut yok
        # (videonun basinda negatif ofset anlamsiz).
        j = i > 0 and i % 3 == 1
        l = i % 3 == 2

        sahneler.append({
            "beat_id": f"bE{i:02d}", "scene_id": f"sE{i:02d}",
            "fact_id": seg["fact_id"],
            "asset_id": (varlik["asset_id"] if varlik else f"grafik{i:02d}"),
            "saglayici": (varlik["saglayici"] if varlik else "bedosaho"),
            "lisans": (varlik["lisans"] if varlik else "kendi-grafigi"),
            "medya_turu": "image",
            "medya_yolu": (varlik["yol"] if varlik else ""),
            "ses_yolu": seg["yol"],
            "sure_sn": sure, "bas_sn": round(t, 2), "islev": islev,
            "perde": ("acilis" if i < 2 else
                      "kapanis" if i >= len(SEGMENTLER) - 1 else "gelisme"),
            "cekim_turu": cekim, "hareket": hareket, "kadraj": kadraj,
            "kaynak_aralik": [0, sure], "j_cut": j, "l_cut": l,
            "altyazi": [], "motion": [sp.sozluk() for sp in specler],
            "gerekce": f"{islev}/{cekim}/{seg['fact_id']}",
        })
        araliklar.append([round(t, 3), round(t + seg["sure"], 3)])
        t += sure

    ham = {"fps": 30, "genislik": 1920, "yukseklik": 1080,
           "gecis_modu": "sinematik", "altyazi_stili": "yok",
           "sahneler": sahneler}
    return ham, kullanilan, araliklar


# ═══════════════ 3) POST MASTER ═══════════════

def loudness_olc(yol: str) -> dict:
    """ffmpeg loudnorm ANALIZ gecisi — gercek olcum."""
    r = _kos(["ffmpeg", "-hide_banner", "-nostats", "-i", yol,
              "-af", f"loudnorm=I={HEDEF_LUFS}:TP={HEDEF_TP}:LRA=11:print_format=json",
              "-f", "null", "-"], 900)
    log = r.stderr or ""
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", log, re.S)
    if not m:
        return {"hata": "loudnorm ciktisi ayristirilamadi",
                "log_kuyruk": log[-260:]}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError as e:
        return {"hata": f"json: {e}"}


def post_master(girdi: str, cikti: str) -> dict:
    """IKI GECISLI loudnorm: -14 LUFS, TP <= -1 dBTP.

    ⚠ Tek gecisli loudnorm hedefi vurmuyor (ilk gecis akisi tanimadigi icin
    tahmin yapar). Olculen degerler ikinci gecise `measured_*` olarak verilir.
    """
    ilk = loudness_olc(girdi)
    if "hata" in ilk:
        return {"durum": "olculemedi", "ilk": ilk}
    af = (f"loudnorm=I={HEDEF_LUFS}:TP={HEDEF_TP}:LRA=11"
          f":measured_I={ilk['input_i']}:measured_TP={ilk['input_tp']}"
          f":measured_LRA={ilk['input_lra']}:measured_thresh={ilk['input_thresh']}"
          f":offset={ilk.get('target_offset', 0)}:linear=true")
    r = _kos(["ffmpeg", "-y", "-v", "error", "-i", girdi,
              "-af", af, "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
              cikti], 900)
    if r.returncode != 0 or not os.path.exists(cikti):
        return {"durum": "basarisiz", "stderr": (r.stderr or "")[-400:],
                "ilk": ilk}
    son = loudness_olc(cikti)
    return {"durum": "tamam", "ilk": ilk, "son": son}


# ═══════════════ 4) QA ═══════════════

def qa_tespit(yol: str) -> dict:
    r = _kos(["ffmpeg", "-v", "info", "-i", yol, "-af",
              "silencedetect=noise=-45dB:d=1.2", "-vf",
              "blackdetect=d=0.15:pic_th=0.98,freezedetect=n=0.001:d=1.0",
              "-f", "null", "-"], 900)
    log = r.stderr or ""
    return {
        "siyah": [x.strip() for x in log.splitlines() if "black_start" in x],
        "donma": [x.strip() for x in log.splitlines() if "freeze_start" in x],
        "sessizlik": [x.strip() for x in log.splitlines()
                      if "silence_start" in x],
    }


def temas_sayfasi(yol: str, hedef: str, adet: int = 24) -> str:
    sure = _sure(yol) or 1.0
    r = _kos(["ffmpeg", "-y", "-v", "error", "-i", yol, "-vf",
              f"fps={adet / sure:.4f},scale=426:-1,tile=6x4",
              "-frames:v", "1", "-q:v", "3", hedef], 900)
    return hedef if r.returncode == 0 and os.path.exists(hedef) else ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--olcu", default="1280x720")
    ap.add_argument("--tavan-dk", type=float, default=15.0)
    a = ap.parse_args()
    g, y = (int(x) for x in a.olcu.lower().split("x"))
    os.makedirs(CIKTI, exist_ok=True)

    print("═" * 64)
    print("FAZ E PILOT — SESLI, GERCEK MEDYALI BELGESEL (VidrushEditorV2)")
    print("⚠ ANLATIM YAPAY: macOS `say -v Yelda`; insan seslendirmesi DEGIL")
    print("═" * 64)

    # ── girdiler ──
    mr = os.path.join(CIKTI, "medya_rapor.json")
    mf = os.path.join(CIKTI, "manifest.json")
    for p in (mr, mf):
        if not os.path.exists(p):
            print(f"  ✖ eksik girdi: {p}")
            print("    once faz_e_medya.py ve faz_e_manifest.py kosulmali")
            return 2
    medya = json.load(open(mr, encoding="utf-8"))
    manifest = json.load(open(mf, encoding="utf-8"))
    varliklar = [v for v in medya["varliklar"] if os.path.exists(v["yol"])]

    # ── SERT DECODE KAPISI (kullanicinin kalite uyarisi) ──
    # Medya raporu decode dogrulamasi tasiyor olsa da pilot BAGIMSIZ olarak
    # tekrar dogruluyor: dosya rapordan sonra bozulmus/degistirilmis olabilir.
    # `indirme.dosya_dogrula` sirasi: boyut -> HTML izi -> sihirli bayt ->
    # bitis imzasi -> Pillow decode -> ffprobe.
    from medya import indirme as _ind
    guvenli, decode_red = [], []
    for v in varliklar:
        ok, sebep, bilgi = _ind.dosya_dogrula(v["yol"], beklenen="image")
        if ok:
            v = dict(v)
            v["dogrulama"] = bilgi
            guvenli.append(v)
        else:
            decode_red.append({"asset_id": v["asset_id"], "sebep": sebep})
    print(f"  sert decode kapisi: {len(guvenli)}/{len(varliklar)} gecti")
    for r in decode_red:
        print(f"    ✖ {r['asset_id']}: {r['sebep'][:70]}")
    varliklar = guvenli
    varliklar, gorsel_red = gorsel_kapi(varliklar)
    print(f"  gorsel kapi: {len(varliklar)} gecti, {len(gorsel_red)} reddedildi"
          f" (luma>={LUMA_TABANI:.0f}, detay>={DETAY_TABANI})")
    for v in gorsel_red:
        print(f"    ✖ {v['asset_id']} luma {v['luma']} detay {v['detay']}  "
              f"{v['red'][:52]}")
    zayif = [v for v in varliklar if v.get("gorsel_zayif")]
    if zayif:
        print(f"  ⚠ GORSEL OLARAK ZAYIF (detay < {DETAY_IYI}): {len(zayif)} kare "
              "— duz/az detayli, profesyonel kalite iddiasini DUSURUR")
        for v in zayif:
            print(f"    ~ {v['asset_id']} detay {v['detay']}  {v['baslik'][:38]}")
    print(f"\n  gercek varlik: {len(varliklar)}")
    print(f"  SAGLAYICI dagilimi: {medya['saglayici_dagilimi']}  "
          f"tek pay %{medya['tek_saglayici_payi'] * 100:.0f}")
    print(f"  ARSIV dagilimi    : {medya['arsiv_dagilimi']}  "
          f"tek pay %{medya['tek_arsiv_payi'] * 100:.0f}")
    print("  ── medya cesitlilik kapilari (DURUST SONUC) ──")
    for k, ok in (medya.get("kapilar") or {}).items():
        print(f"    {'✓' if ok else '✖'} {k}")
    dogrulanan = [i["fact_id"] for i in manifest["iddialar"]
                  if i["guven"] == "dogrulandi"]
    print(f"  dogrulanmis iddia: {len(dogrulanan)}/{len(manifest['iddialar'])}")
    kullanilan_fid = sorted({f for f, _ in SEGMENTLER})
    eksik_dogrulama = [f for f in kullanilan_fid if f not in dogrulanan]
    print(f"  anlatimda kullanilan fact_id: {kullanilan_fid}")
    if eksik_dogrulama:
        print(f"  ✖ DOGRULANMAMIS iddia anlatimda: {eksik_dogrulama}")
        return 3

    # ── 1) anlatim ──
    print("\n  ── anlatim uretimi (yerel TTS) ──")
    anlatim = anlatim_uret(SES_DIZIN)
    toplam_konusma = sum(s["sure"] for s in anlatim)
    print(f"  segment: {len(anlatim)}   toplam konusma: {toplam_konusma:.1f} sn")
    for s in anlatim:
        print(f"    {s['fact_id']}  {s['sure']:5.2f} sn  {s['metin'][:56]}…")

    # ── 2) sahne plani ──
    ham, kullanilan, araliklar = sahne_plani(anlatim, varliklar)
    toplam = sum(s["sure_sn"] for s in ham["sahneler"])
    print(f"\n  sahne: {len(ham['sahneler'])}   toplam sure: {toplam:.2f} sn")
    print(f"  kullanilan BENZERSIZ varlik: {len(kullanilan)}  "
          f"(id'ler tekil mi: {len({k['asset_id'] for k in kullanilan}) == len(kullanilan)})")
    if not (45.0 <= toplam <= 60.0):
        print(f"  ⚠ sure 45-60 sn araliginda DEGIL: {toplam:.2f}")

    # ── 3) adapter + ses ──
    don = adapter.donustur(ham)
    props = don.remotion_props
    # Sahne seslerini props'a bagla (adapter ses alanini tasimiyor)
    for sh, kaynak in zip(props["sahneler"], ham["sahneler"]):
        sh["ses"] = kaynak["ses_yolu"]
        sh["ses_seviye"] = 1.0
        sh["j_cut_sn"] = 0.4
        sh["l_cut_sn"] = 0.45
    props["ses"] = {
        "ambans": [ortam_tonu(SES_DIZIN, toplam)],
        "ambans_seviye": 0.22,
        "anlatim_araliklari": araliklar,
        "ducking": {"ambans": 0.30},
        "yapay_ses": True,
        "hedef_lufs": HEDEF_LUFS, "hedef_tp_dbtp": HEDEF_TP,
    }

    varlik_haritasi = {s["asset_id"]: s["medya_yolu"]
                       for s in ham["sahneler"] if s["medya_yolu"]}
    hazir = remotion_v2.props_hazirla(props, calisma_dizin=CIKTI,
                                      varlik_haritasi=varlik_haritasi)
    hazir["hatalariGoster"] = False

    kapi = remotion_v2.dogrula(hazir)
    print(f"\n  pre-render kapisi: {kapi['durum']}   ozet={kapi['ozet']}")
    for so in kapi["sorunlar"]:
        if so["seviye"] in ("fail", "warn"):
            print(f"    {so['seviye']:4} {so['kod']} [{so['scene_id']}] "
                  f"{so['spec']}: {so['detay'][:80]}")
    if kapi["durum"] == "FAIL":
        print("  ✖ KAPI DURDURDU")
        return 4

    say = remotion_v2.uygulanan_atlanan(hazir)
    print(f"  spec: {say['sayim']}")

    with open(os.path.join(CIKTI, "props.json"), "w", encoding="utf-8") as f:
        json.dump(hazir, f, ensure_ascii=False, indent=1)

    # ── 4) render ──
    ham_mp4 = os.path.join(CIKTI, "pilot_ham.mp4")
    print(f"\n  render ({g}x{y}, tavan {a.tavan_dk} dk)…")
    r = remotion_v2.render(hazir, ham_mp4, olcu=(g, y), fps=30,
                           zaman_asimi=int(a.tavan_dk * 60))
    print(f"  rc={r['rc']} durum={r.get('durum')} sure={r['sure_sn']} sn")
    if r["rc"] != 0 or not os.path.exists(ham_mp4):
        print("  ✖ RENDER BASARISIZ")
        print("  stderr:", r["stderr"][-900:])
        return 5

    # ── 5) post master ──
    print("\n  ── post master (iki gecisli loudnorm) ──")
    son_mp4 = os.path.join(CIKTI, "pilot_master.mp4")
    pm = post_master(ham_mp4, son_mp4)
    print(f"  durum: {pm['durum']}")
    if pm.get("ilk") and "input_i" in pm["ilk"]:
        print(f"  once : {pm['ilk']['input_i']} LUFS  TP {pm['ilk']['input_tp']} dBTP")
    if pm.get("son") and "input_i" in pm["son"]:
        print(f"  sonra: {pm['son']['input_i']} LUFS  TP {pm['son']['input_tp']} dBTP")
    olculen = son_mp4 if pm["durum"] == "tamam" else ham_mp4

    # ── 6) QA ──
    pr = json.loads(_kos(["ffprobe", "-v", "error", "-show_format",
                          "-show_streams", "-of", "json", olculen], 300).stdout
                    or "{}")
    v = next((s for s in pr.get("streams", []) if s["codec_type"] == "video"), {})
    au = [s for s in pr.get("streams", []) if s["codec_type"] == "audio"]
    sure = float(pr.get("format", {}).get("duration") or 0)
    t = qa_tespit(olculen)
    ts = temas_sayfasi(olculen, os.path.join(CIKTI, "temas_sayfasi.jpg"))

    print(f"\n  ── QA ──")
    print(f"  {v.get('width')}x{v.get('height')} {v.get('r_frame_rate')} "
          f"{sure:.2f} sn  {os.path.getsize(olculen) / 1e6:.1f} MB")
    print(f"  ses akisi: {len(au)}"
          + (f"  ({au[0].get('codec_name')} {au[0].get('sample_rate')} Hz)"
             if au else "  ✖ SES YOK"))
    print(f"  siyah kare: {len(t['siyah'])}  uzun donma: {len(t['donma'])}  "
          f"uzun sessizlik: {len(t['sessizlik'])}")
    for k in ("siyah", "donma", "sessizlik"):
        for x in t[k][:3]:
            print(f"    {x}")

    lufs = tp = None
    if pm.get("son") and "input_i" in pm["son"]:
        lufs = float(pm["son"]["input_i"])
        tp = float(pm["son"]["input_tp"])

    kapilar = {
        "sure 45-60 sn": 45.0 <= sure <= 60.0,
        "720p": int(v.get("height") or 0) >= 720,
        "ses akisi var": len(au) >= 1,
        "siyah kare = 0": len(t["siyah"]) == 0,
        "uzun donma = 0": len(t["donma"]) == 0,
        f"LUFS {HEDEF_LUFS}±1": lufs is not None and abs(lufs - HEDEF_LUFS) <= 1.0,
        f"TP <= {HEDEF_TP}": tp is not None and tp <= HEDEF_TP + 0.05,
        "benzersiz varlik >= 8": len(kullanilan) >= 8,
        "bilinmeyen spec = 0": say["sayim"]["bilinmeyen"] == 0,
        # ⚠ Bu kapi PASS demeden once gorsel doluluk sartini da zorunlu kiliyor.
        # Duz gri kareler olcumle gecse bile izleyici icin bos ekrandir.
        f"kullanilan karelerin hepsi detay >= {DETAY_IYI}":
            not [v for v in kullanilan if v.get("gorsel_zayif")],
        # Kullanilan her kare GERCEKTEN decode edilebilir bir gorsel mi
        "kullanilan karelerin hepsi guvenli-decode":
            bool(kullanilan) and all(
                v.get("dogrulama", {}).get("sihirli_tur") for v in kullanilan),
        # Cesitlilik kapilari: gecmezse DURUST FAIL (kapsam boslugu yazili)
        "SAGLAYICI cesitliligi (>=3 ve <=%40)":
            bool((medya.get("kapilar") or {}).get("SAGLAYICI cesitliligi>=3"))
            and bool((medya.get("kapilar") or {}).get("SAGLAYICI tek pay<=40%")),
        "ARSIV cesitliligi (>=2 ve <=%40)":
            bool((medya.get("kapilar") or {}).get("ARSIV cesitliligi>=2"))
            and bool((medya.get("kapilar") or {}).get("ARSIV tek pay<=40%")),
    }
    print("\n  ── KALITE KAPILARI ──")
    for k, ok in kapilar.items():
        print(f"  {'✓' if ok else '✖'} {k}")

    rapor = {
        "anlatim": {"yapay": True, "motor": f"macOS say -v {TTS_SESI}",
                    "segment": len(anlatim),
                    "toplam_konusma_sn": round(toplam_konusma, 2),
                    "metinler": [{"fact_id": s["fact_id"], "metin": s["metin"],
                                  "sure": s["sure"]} for s in anlatim]},
        "medya": {"kullanilan_benzersiz": len(kullanilan),
                  "saglayici": medya["saglayici_dagilimi"],
                  "arsiv": medya["arsiv_dagilimi"],
                  "tek_saglayici_payi": medya["tek_saglayici_payi"],
                  "tek_arsiv_payi": medya["tek_arsiv_payi"],
                  "kapsam_bosluklari": medya["kapsam_bosluklari"],
                  "decode_reddi": decode_red,
                  "medya_kapilari": medya.get("kapilar") or {},
                  "gorsel_reddi": [{"asset_id": v["asset_id"],
                                    "luma": v["luma"], "detay": v["detay"],
                                    "red": v["red"]} for v in gorsel_red],
                  "gorsel_zayif": [{"asset_id": v["asset_id"],
                                    "detay": v["detay"],
                                    "baslik": v["baslik"]} for v in zayif],
                  "varliklar": [{"asset_id": k["asset_id"],
                                 "baslik": k["baslik"],
                                 "lisans": k["lisans"],
                                 "saglayici": k["saglayici"],
                                 "arsiv": k["arsiv"],
                                 "luma": k.get("luma"),
                                 "detay": k.get("detay"),
                                 "gorsel_zayif": bool(k.get("gorsel_zayif")),
                                 "dogrulama": k.get("dogrulama")}
                                for k in kullanilan]},
        "spec_sayimi": say["sayim"], "spec_detay": say["detay"],
        "kapi": {"durum": kapi["durum"], "ozet": kapi["ozet"],
                 "sorunlar": kapi["sorunlar"]},
        "render_sure_sn": r["sure_sn"],
        "post_master": pm, "qa": t, "kalite_kapilari": kapilar,
        "olcu": f"{v.get('width')}x{v.get('height')}", "sure_sn": round(sure, 2),
        "ses_akisi": len(au),
        "ciktilar": {"ham": os.path.abspath(ham_mp4),
                     "master": os.path.abspath(son_mp4)
                     if os.path.exists(son_mp4) else None,
                     "temas_sayfasi": os.path.abspath(ts) if ts else None,
                     "props": os.path.abspath(os.path.join(CIKTI, "props.json")),
                     "attribution": medya.get("attribution"),
                     "ses_dizini": os.path.abspath(SES_DIZIN)},
    }
    ry = os.path.join(CIKTI, "pilot_rapor.json")
    with open(ry, "w", encoding="utf-8") as f:
        json.dump(rapor, f, ensure_ascii=False, indent=1)

    print(f"\n  master : {os.path.abspath(son_mp4)}")
    print(f"  temas  : {os.path.abspath(ts) if ts else '(uretilemedi)'}")
    print(f"  rapor  : {os.path.abspath(ry)}")
    return 0 if all(kapilar.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
