#!/usr/bin/env python3
"""FAZ I-15 — KALITE KAPISI **ACIKKEN PASS** URETEN APOLLO MINI-BELGESELI.

I-14 kapilari kurdu ve I-13'un 10 sn ciktisi acik kapida **FAIL(4)** verdi.
Bu betik ayni Apollo tarih/belgesel fixture'iyla **gercekten duzeltilmis**
bir cikti uretir ve `kalite_kapisi=True` iken **PASS** hedefler.

I-13'e gore DEGISEN DORT SEY (hepsi olculuyor, hicbiri gizlenmiyor):

  1. BASLIK — `plan.py` artik sabit `[:42]` dilimi KULLANMIYOR; sinir
     GERCEK render genisliginden (1280) hesaplaniyor ve kesme KELIME
     SINIRINDA yapiliyor. Punto kucultulmuyor (tam 60).

  2. SURELER — sabit 3.2 sn blok YOK. Sahne sureleri edge-tts'in
     **SentenceBoundary** olaylarindan, yani GERCEK anlatim zamanlamasindan
     turetiliyor. Kelime sayisi vekili degil, olcum.

  3. OLU FINAL — anlatim master'i son cumlenin bitisi + `KUYRUK_SN`
     noktasindan KESILIYOR; videonun sonunda 0.5 sn'yi asan sessizlik yok.

  4. AMBIYANS — kaynak -48.7 LUFS'ti ve ducking TUM VIDEO boyunca
     uygulaniyordu (`anlatim_araliklari` hic gecirilmiyordu). Simdi ambiyans
     olculmus hedefe normalize ediliyor VE ducking yalnizca gercek konusma
     araliklarinda uygulaniyor.

⚠ SAHTE ESIK DUSURME YOK. Medya cesitliligi olculur ve **oldugu gibi**
raporlanir; benzerlik esigi (0.86) I-14'ten degistirilmedi.

⚠ SAHTE VIDEO URETILMEZ. Gercek zincir:
  edit_kopru.plan_kur -> editor.plan.uret (beat/gramer/motion/tipografi/ses/
  ON-RENDER QA) -> adapter.donustur -> remotion_v2 dogrula/props_hazirla/
  render -> Remotion `VidrushEditorV2` (Chrome headless + ffmpeg).
ffmpeg renk/test kaynagi (lavfi/testsrc/color) KULLANILMAZ.

⚠ MALIYET $0.00 — edge-tts anahtar istemez, saglayiciya hicbir istek yok.

Kosum:
    python3 webapp/testler/smoke_kalite_pass_i15.py
Cikti:
    outputs/sample/editorv2_kalite_pass_i15.mp4 (+ 6 kare ve JSON rapor)
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import subprocess
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # webapp/
DEPO = os.path.dirname(KOK)
sys.path.insert(0, KOK)
os.environ.setdefault("VIDRUSH_KOK", os.path.join(DEPO, "cikti", "_i15_kok"))

CIKTI_DIZIN = os.path.join(DEPO, "outputs", "sample")
VIDEO_ADI = "editorv2_kalite_pass_i15.mp4"
FIXTURE = os.path.join(DEPO, "app", "render-studio", "public", "editorv2",
                       "faz_e")
CALISMA = os.path.join(DEPO, "cikti", "_i15")
OLCU = (1280, 720)
FPS = 30

# ── ANLATIM: Faz E arastirma manifestindeki DOGRULANMIS iddialar ──
# `cikti/faz_e/manifest.json` -> guven == "dogrulandi". Uydurma olgu YOK.
# Turkce kayitli iddialar (f001, f006, f002) anlami degistirilmeden
# Ingilizceye cevrildi; iddianin KENDISI degismedi.
# ⚠ SIRA OLCUME GORE SECILDI. Ilk deneme f001 ile aciliyordu; o cumle
# 4.438 sn surdu ve beat motoru `hook`/`acilis` icin 4.05 sn bolunme esigi
# uyguladigi icin sahne IKI beat'e bolundu. Iki beat ayni sahnenin tek
# adayini paylasinca AYNI GORSEL ARKA ARKAYA cikti ve I-14 kapisi bunu
# dogru sekilde FAIL etti. Cozum esigi gevsetmek DEGIL: en carpici dogrulanmis
# cumleyi (f005, 3.475 sn) hook yapmak — hem esigin altinda kaliyor hem
# belgesel kurgusu olarak dogru acilis.
#
# ⚠ SAHNE SAYISI 4 — SAGLAYICI KOTASINDAN. Ilk denemede 5 sahne vardi;
# `gramer` bir saglayicidan en fazla `SAGLAYICI_TAVANI` (4) cekim aliyor ve
# fixture havuzunun TAMAMI `wikimedia`. Besinci sahneye medya DUSMEDI,
# motion-graphic fallback'e dustu: goruntusuz koyu zemin + 3.5 sn DONMUS
# kare + "ARMSTRONG TOOK" gibi yarim bir kart basligi (kare ile goruldu).
# Kotayi yukseltmek cozum DEGIL — o kota gercek bir cesitlilik guvencesi.
# Sahne sayisi kotaya uyduruldu.
# ⚠ ACILIS CUMLESI KISA TUTULDU (olculdu). `hook`/`acilis` icin beat motoru
# hedef sureyi bilgi yogunluguna gore ~2.0 sn'ye cekiyor ve bolunme esigi
# hedefin 1.5 kati oluyor (~3.06 sn). 3.575 sn'lik bir acilis cumlesi IKI
# beat'e bolundu, iki beat sahnenin tek adayini paylasti ve ayni gorsel arka
# arkaya cikti. Esigi gevsetmek yerine acilis gercekten kisaltildi — zaten
# hook'un olmasi gereken sey bu.
SAHNE_METINLERI = [
    ("f005", "The Eagle has landed."),
    ("f001", "The Eagle landed on the Moon in July, nineteen sixty-nine."),
    ("f002", "The guidance computer raised a twelve-oh-two alarm."),
    ("f004", "Armstrong took manual control of the lunar module."),
]
# `editor.plan.uret` varsayilani. Sahne sayisi bunu ASMAMALI, yoksa tek
# saglayicili havuzda son sahne(ler) medyasiz kalir.
SAGLAYICI_TAVANI = 4
OLGULAR = [{"fact_id": f, "guven": "dogrulandi", "metin": m}
           for f, m in SAHNE_METINLERI]
SES_ADAYLARI = ("en-GB-RyanNeural", "en-US-AndrewNeural", "en-US-BrianNeural")

# Videonun sonunda birakilan nefes payi. I-14 kapisinin tavani 0.5 sn.
KUYRUK_SN = 0.35
# Anlatim master hedefi = profil hedefi (premium-modern lufs_hedef -14).
ANLATIM_LUFS = -14.0
# Ambiyans hedefi: anlatimin ~24 dB altinda kalacak sekilde HESAPLANDI.
#   etkin = AMBANS_LUFS + 20log10(0.5) + 20log10(0.5) = AMBANS_LUFS - 12.04
#   fark  = -14.0 - etkin = 24.04 dB  -> [12, 30] bandinin ortasi
AMBANS_LUFS = -26.0
AMBANS_SEVIYE = 0.5
AMBANS_DUCK = 0.5

GORSEL_HAVUZU = [
    "a082_wiki_4ba3ccdace", "a086_wiki_effc9e462f", "a281_wiki_e42b89a1f6",
    "a282_wiki_56a60bf31b", "a283_wiki_58de9c1ba3", "a313_wiki_8ba105ee68",
    "a314_wiki_6cff017be6",
]
DETAY_ESIGI = 20.0          # I-13'te olculdu: esik alti kare DUZ GRI cikiyor
SAHNE_SAYISI = len(SAHNE_METINLERI)


def kos(cmd, t=300):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=t)


def ses_olc(yol, sessizlik_esigi="0.30"):
    """codec/sr/kanal + LUFS/TP/LRA + sessizlik araliklari. Uydurma yok."""
    o = {}
    r = kos(["ffprobe", "-v", "error", "-show_entries",
             "stream=codec_name,sample_rate,channels", "-show_entries",
             "format=duration", "-of", "json", yol], 60)
    try:
        d = json.loads(r.stdout or "{}")
        a = (d.get("streams") or [{}])[0]
        o.update({"codec": a.get("codec_name"),
                  "ornekleme_hz": int(a.get("sample_rate") or 0),
                  "kanal": int(a.get("channels") or 0),
                  "sure_sn": round(float((d.get("format") or {}).get(
                      "duration") or 0), 3)})
    except (ValueError, TypeError, IndexError):
        pass
    r = kos(["ffmpeg", "-nostdin", "-i", yol, "-af",
             "loudnorm=print_format=json", "-f", "null", "-"])
    m = re.findall(r"\{[^{}]*\"input_i\"[^{}]*\}", (r.stderr or ""), re.S)
    if m:
        try:
            d = json.loads(m[-1])
            o.update({"lufs": float(d.get("input_i", 0)),
                      "tepe_dbtp": float(d.get("input_tp", 0)),
                      "lra": float(d.get("input_lra", 0))})
        except (ValueError, TypeError):
            pass
    r = kos(["ffmpeg", "-nostdin", "-i", yol, "-af",
             f"silencedetect=noise=-45dB:d={sessizlik_esigi}", "-f", "null",
             "-"])
    basla = [float(x) for x in
             re.findall(r"silence_start: ([\d.-]+)", r.stderr or "")]
    sure = [float(x) for x in
            re.findall(r"silence_duration: ([\d.]+)", r.stderr or "")]
    o["sessizlikler"] = [{"bas": round(b, 3), "sure": round(s, 3)}
                         for b, s in zip(basla, sure)]
    top = sum(sure)
    o["sessiz_sn"] = round(top, 3)
    o["sessiz_pct"] = (round(100.0 * top / o["sure_sn"], 1)
                       if o.get("sure_sn") else 0.0)
    o["kirpma_var"] = bool(o.get("tepe_dbtp", -99) > -0.1)
    return o


# ────────────────────── 1) ANLATIM + GERCEK ZAMANLAMA ──────────────────────

def anlatim_uret(hedef_dizin):
    """edge-tts anlatim + **SentenceBoundary** zamanlamasi.

    Doner: (master_yolu, olcum, adaylar, cumle_araliklari) ya da (None, ...).

    ⚠ ZAMANLAMA VEKIL DEGIL OLCUM: `SentenceBoundary` olaylari motorun kendi
    sentez zaman cizelgesinden gelir. I-14'te kullanilan "kelime sayisi"
    yaklasimi yalnizca bir vekildi; bu gercek suredir.
    """
    try:
        import edge_tts
    except ImportError as e:
        print(f"BLOKE: edge-tts yok ({e}). Cozum: pip install edge-tts",
              file=sys.stderr)
        return None, {}, [], []
    os.makedirs(hedef_dizin, exist_ok=True)
    metin = " ".join(m for _, m in SAHNE_METINLERI)
    uretilen = []

    async def uret():
        for v in SES_ADAYLARI:
            y = os.path.join(hedef_dizin, f"aday_{v}.mp3")
            sinirlar = []
            try:
                c = edge_tts.Communicate(metin, v)
                with open(y, "wb") as f:
                    async for ch in c.stream():
                        if ch["type"] == "audio":
                            f.write(ch["data"])
                        elif ch["type"] == "SentenceBoundary":
                            sinirlar.append({
                                "bas": round(ch["offset"] / 1e7, 3),
                                "sure": round(ch["duration"] / 1e7, 3),
                                "metin": ch["text"]})
                uretilen.append((v, y, sinirlar))
            except Exception as e:                              # noqa: BLE001
                print(f"  aday {v} uretilemedi: {type(e).__name__}",
                      file=sys.stderr)

    try:
        asyncio.run(uret())
    except Exception as e:                                      # noqa: BLE001
        print(f"BLOKE: TTS cagrisi basarisiz: {type(e).__name__}: "
              f"{str(e)[:120]}", file=sys.stderr)
        return None, {}, [], []
    if not uretilen:
        return None, {}, [], []

    # ⚠ SECIM OLCUME DAYANIR: LRA (dinamik genislik) dogalligin en iyi
    # olculebilir vekili; duz TTS'te 0.5-1, ifadeli anlatimda 2+.
    # EK SART (I-15): cumle sayisi TAM eslesmeli, yoksa sahne eslemesi bozulur.
    olcumler = []
    for v, y, sinirlar in uretilen:
        o = ses_olc(y)
        o["ses"] = v
        o["cumle_siniri"] = len(sinirlar)
        olcumler.append(o)
    uygun = [(v, y, s) for v, y, s in uretilen if len(s) == SAHNE_SAYISI]
    if not uygun:
        print(f"BLOKE: hicbir aday {SAHNE_SAYISI} cumle siniri vermedi "
              f"(olculen: {[o['cumle_siniri'] for o in olcumler]}). "
              f"Sahte zamanlama URETILMEDI.", file=sys.stderr)
        return None, {}, olcumler, []
    en_iyi = max(uygun, key=lambda t: next(
        o.get("lra", 0) for o in olcumler if o["ses"] == t[0]))
    ses_adi, kaynak, sinirlar = en_iyi

    anlatim_bitis = round(sinirlar[-1]["bas"] + sinirlar[-1]["sure"], 3)
    kesim = round(anlatim_bitis + KUYRUK_SN, 3)
    master = os.path.join(hedef_dizin, "anlatim_master.wav")
    # ⚠ BAS SESSIZLIGI KIRPILMAZ: kirpmak `SentenceBoundary` ofsetlerini
    # kaydirir ve zamanlama olcumu YALAN olur. Yalnizca KUYRUK kesilir —
    # olu final kusurunun kok nedeni buydu.
    r = kos(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", kaynak,
             "-t", str(kesim), "-af",
             f"loudnorm=I={ANLATIM_LUFS}:TP=-1.5:LRA=7",
             "-ar", "48000", "-ac", "1", master])
    if r.returncode != 0 or not os.path.exists(master):
        print(f"BLOKE: anlatim master'lanamadi: {(r.stderr or '')[:160]}",
              file=sys.stderr)
        return None, {}, olcumler, []
    olcum = ses_olc(master)
    olcum["ses"] = ses_adi
    olcum["anlatim_bitis_sn"] = anlatim_bitis
    olcum["kesim_sn"] = kesim
    return master, olcum, olcumler, sinirlar


def ambans_hazirla(hedef_dizin, toplam_sn):
    """Ambiyansi OLCULMUS hedefe normalize et (I-13'te -48.7 LUFS'ti)."""
    kaynak = os.path.join(FIXTURE, "ambans0.wav")
    if not os.path.exists(kaynak):
        return "", {}, {}
    once = ses_olc(kaynak)
    hedef = os.path.join(hedef_dizin, "ambans_norm.wav")
    r = kos(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", kaynak,
             "-t", str(round(toplam_sn + 1.0, 3)), "-af",
             f"loudnorm=I={AMBANS_LUFS}:TP=-6:LRA=7",
             "-ar", "48000", "-ac", "1", hedef])
    if r.returncode != 0 or not os.path.exists(hedef):
        return "", once, {}
    return hedef, once, ses_olc(hedef)


# ────────────────────── 2) GORSEL SECIMI ve CESITLILIK ─────────────────────

def gorsel_detay(yol):
    """Kadraja dusen DETAY (luminans std sapmasi). Olcum, tahmin degil."""
    r = subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", "-i", yol, "-vf",
         "crop=iw*0.7:ih*0.7,scale=320:-1,format=gray", "-f", "rawvideo", "-"],
        capture_output=True, timeout=120)
    d = r.stdout or b""
    if len(d) < 1000:
        return 0.0
    n = len(d)
    mu = sum(d) / n
    return round((sum((b - mu) ** 2 for b in d) / n) ** 0.5, 1)


def dhash(yol, w=9, h=8):
    """64 bit yapisal parmak izi. Ag yok, deterministik."""
    r = subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", "-i", yol, "-vf",
         f"scale={w}:{h},format=gray", "-f", "rawvideo", "-"],
        capture_output=True, timeout=120)
    d = r.stdout or b""
    if len(d) < w * h:
        return None
    return [1 if d[y * w + x] > d[y * w + x + 1] else 0
            for y in range(h) for x in range(w - 1)]


def benzerlik(a, b):
    """dHash esitlik orani 0..1. Okunamazsa -1 (OLCULEMEDI)."""
    ha, hb = dhash(a), dhash(b)
    if not ha or not hb:
        return -1.0
    return sum(1 for x, y in zip(ha, hb) if x == y) / len(ha)


def gorsel_sec(adet):
    """Havuzdan EN DETAYLI `adet` gorseli sec. Esik alti KULLANILMAZ."""
    olcumler = []
    for ad in GORSEL_HAVUZU:
        y = os.path.join(FIXTURE, f"{ad}.jpg")
        if os.path.exists(y):
            olcumler.append({"asset_id": ad, "yol": y,
                             "detay_std": gorsel_detay(y)})
    uygun = [o for o in olcumler if o["detay_std"] >= DETAY_ESIGI]
    uygun.sort(key=lambda o: -o["detay_std"])
    return uygun[:adet], olcumler


def cesitli_sirala(secilen):
    """En benzer ciftin KOMSU OLMAMASI icin deterministik siralama.

    ⚠ Bu bir ESIK OYNAMASI DEGIL: hicbir kabul/red karari degismez, yalnizca
    ayni kumenin SIRASI secilir. Havuzun kendisi daha cesitli hale gelmez —
    olculdu ki mevcut 4'lu zaten havuzun en cesitli alt kumesi (en yuksek
    ikili benzerlik 0.6094) ve daha iyisi YOK. Yapilabilecek tek iyilestirme
    o ciftin arka arkaya DUSMEMESI.

    Ilk gorsel SABIT kalir (en yuksek detayli kare, acilis capasi); kalanlarin
    tum permutasyonlari arasindan komsu benzerligi en dusuk olan secilir.
    Kume kucuk (<=6) oldugu icin tam arama ucuz ve deterministik.
    """
    import itertools
    if len(secilen) < 3:
        return secilen, {}
    onbellek = {}

    def b(i, j):
        a1, a2 = secilen[i]["asset_id"], secilen[j]["asset_id"]
        k = tuple(sorted((a1, a2)))
        if k not in onbellek:
            onbellek[k] = benzerlik(secilen[i]["yol"], secilen[j]["yol"])
        return onbellek[k]

    def komsu_maks(sira):
        return max(b(sira[i], sira[i + 1]) for i in range(len(sira) - 1))

    kalan = list(range(1, len(secilen)))
    once = list(range(len(secilen)))
    en_iyi = min(([0] + list(p) for p in itertools.permutations(kalan)),
                 key=lambda s: (komsu_maks(s), s))
    return ([secilen[i] for i in en_iyi],
            {"once_sira": [secilen[i]["asset_id"] for i in once],
             "once_komsu_maks": round(komsu_maks(once), 4),
             "sonra_sira": [secilen[i]["asset_id"] for i in en_iyi],
             "sonra_komsu_maks": round(komsu_maks(en_iyi), 4),
             "not": ("yalnizca SIRA degisti; kume ve esikler ayni. Havuzun en "
                     "cesitli 4'lusu zaten seciliydi (olculdu).")})


def cesitlilik_raporu(secilen):
    """Secilen gorsellerin ikili benzerligi — DURUSTCE, esik OYNATILMADAN."""
    from editor import kalite_kapisi as kk
    ciftler = []
    for i in range(len(secilen)):
        for j in range(i + 1, len(secilen)):
            d = benzerlik(secilen[i]["yol"], secilen[j]["yol"])
            ciftler.append({"a": secilen[i]["asset_id"],
                            "b": secilen[j]["asset_id"],
                            "bitisik": bool(j == i + 1),
                            "benzerlik": round(d, 4)})
    olculen = [c["benzerlik"] for c in ciftler if c["benzerlik"] >= 0]
    return {
        "esik": kk.BENZERLIK_ESIGI,
        "esik_degistirildi_mi": False,
        "ciftler": ciftler,
        "en_yuksek": max(olculen) if olculen else None,
        "en_yuksek_bitisik": max(
            [c["benzerlik"] for c in ciftler
             if c["bitisik"] and c["benzerlik"] >= 0] or [0]),
        "esigi_asan": [c for c in ciftler
                       if c["benzerlik"] >= kk.BENZERLIK_ESIGI],
    }


# ────────────────────── 3) SAHNE SURELERI (GERCEK ZAMANLAMA) ───────────────

def girdi_kur(secilen, sinirlar, kesim_sn):
    """Sahne sureleri **SentenceBoundary**'den turetilir — sabit blok YOK.

    Sahne i, cumle i'nin basindan cumle i+1'in basina kadar surer; son sahne
    anlatimin bitisi + kuyruk payina kadar. Ilk sahne 0'dan baslar (bastaki
    ~0.1 sn nefes payi ilk sahneye dahildir).
    """
    cumleler, adaylar = [], []
    n = min(len(secilen), len(sinirlar), len(SAHNE_METINLERI))
    for i in range(n):
        bas = 0.0 if i == 0 else sinirlar[i]["bas"]
        son = sinirlar[i + 1]["bas"] if i + 1 < n else kesim_sn
        sure = round(son - bas, 3)
        fid, metin = SAHNE_METINLERI[i]
        sid = f"s{i + 1:03d}"
        se = secilen[i]
        cumleler.append({"scene_id": sid, "fact_id": fid,
                         "sure_sn": sure, "metin": metin})
        adaylar.append({
            "asset_id": se["asset_id"], "scene_id": sid, "fact_id": fid,
            "saglayici": "wikimedia", "lisans": "public-domain",
            "tur": "image", "medya_turu": "image",
            "yerel_yol": se["yol"], "medya_yolu": se["yol"],
            "orijinal_url": ("https://commons.wikimedia.org/wiki/File:"
                             f"{se['asset_id']}"),
            "eser_sahibi": "NASA", "atif_metni": "NASA / Public Domain",
            "atif_gerekli": False, "baslik": "Apollo 11 archive photograph",
            "genislik": 1920, "yukseklik": 1080, "sure_sn": sure,
            "toplam_skor": 90 - i, "render_kullanilabilir": True,
            "detay_std": se.get("detay_std"), "sahne_amaci": "arsiv"})
    return cumleler, {"adaylar": adaylar, "kapsam_bosluklari": []}


# ────────────────────────────── ANA AKIS ───────────────────────────────────

def main() -> int:
    print("=" * 72)
    print("FAZ I-15 — KALITE KAPISI ACIK, PASS HEDEFLI APOLLO BELGESELI")
    print("=" * 72)
    for arac in ("ffmpeg", "ffprobe"):
        if not shutil.which(arac):
            print(f"BLOKE: {arac} yok")
            return 2
    if not os.path.isdir(FIXTURE):
        print(f"BLOKE: fixture dizini yok: {FIXTURE}")
        return 2

    import edit_kopru
    from editor import kalite_kapisi as kk
    from editor import qa_son, remotion_v2
    if not os.path.isdir(os.path.join(remotion_v2.STUDIO, "node_modules")):
        print("BLOKE: Remotion node_modules yok — cd app/render-studio && npm ci")
        return 2

    os.makedirs(CALISMA, exist_ok=True)

    # ── [1/7] ANLATIM ──
    print("\n[1/7] ANLATICI SESI + GERCEK CUMLE ZAMANLAMASI (edge-tts, $0.00)")
    anlatim, ses_kalite, adaylar, sinirlar = anlatim_uret(
        os.path.join(CALISMA, "ses"))
    if not anlatim:
        print("BLOKE: kaliteli anlatim uretilemedi. Sahte ses URETILMEDI.")
        return 3
    for o in adaylar:
        print(f"      aday {o['ses']:<22} LRA={o.get('lra', 0):>4.1f} "
              f"cumle_siniri={o.get('cumle_siniri')} "
              f"sure={o.get('sure_sn', 0):>5.2f}sn")
    print(f"      SECILEN: {ses_kalite['ses']}")
    print(f"      master : {ses_kalite.get('codec')}/"
          f"{ses_kalite.get('ornekleme_hz')}Hz/{ses_kalite.get('kanal')}ch "
          f"{ses_kalite.get('sure_sn')}sn LUFS={ses_kalite.get('lufs')} "
          f"TP={ses_kalite.get('tepe_dbtp')} LRA={ses_kalite.get('lra')}")
    print(f"      anlatim bitisi {ses_kalite['anlatim_bitis_sn']} sn -> "
          f"kesim {ses_kalite['kesim_sn']} sn (kuyruk {KUYRUK_SN} sn)")
    for i, s in enumerate(sinirlar):
        print(f"        cumle{i + 1} bas={s['bas']:>6.3f} sure={s['sure']:>5.3f}"
              f"  {s['metin'][:46]}")

    # ── [2/7] GORSEL ──
    secilen, gorsel_olcumleri = gorsel_sec(SAHNE_SAYISI)
    if len(secilen) < SAHNE_SAYISI:
        print(f"BLOKE: detay esigini ({DETAY_ESIGI}) gecen {SAHNE_SAYISI} "
              f"Apollo gorseli yok ({len(secilen)} bulundu). "
              f"Sahte gorsel URETILMEDI.")
        return 2
    # ⚠ Tek saglayicili havuzda sahne sayisi kotayi asarsa son sahne(ler)
    # SESSIZCE medyasiz kalir (ilk denemede tam bu oldu). Sessiz kalmasin.
    saglayicilar = {"wikimedia"}
    if len(saglayicilar) == 1 and SAHNE_SAYISI > SAGLAYICI_TAVANI:
        print(f"BLOKE: {SAHNE_SAYISI} sahne > saglayici tavani "
              f"{SAGLAYICI_TAVANI} ve havuzda tek saglayici var; son sahne "
              f"medyasiz kalirdi. Kotayi yukseltmek yerine sahne sayisini "
              f"dusur.")
        return 2
    secilen, siralama = cesitli_sirala(secilen)
    cesitlilik = cesitlilik_raporu(secilen)
    cesitlilik["siralama"] = siralama
    print(f"\n[2/7] GORSEL: {len(secilen)} ayri varlik "
          f"(esik {DETAY_ESIGI}, degistirilmedi)")
    for o in sorted(gorsel_olcumleri, key=lambda x: -x["detay_std"]):
        isaret = ("SECILDI" if any(s["asset_id"] == o["asset_id"]
                                   for s in secilen)
                  else ("esik alti" if o["detay_std"] < DETAY_ESIGI else "-"))
        print(f"      {o['asset_id']:<26} detay_std={o['detay_std']:>6} {isaret}")
    if siralama:
        print(f"      siralama : komsu benzerligi "
              f"{siralama['once_komsu_maks']} -> "
              f"{siralama['sonra_komsu_maks']} (yalnizca SIRA degisti, "
              f"esik ayni)")
    print(f"      cesitlilik: en yuksek ikili benzerlik "
          f"{cesitlilik['en_yuksek']}, bitisik en yuksek "
          f"{cesitlilik['en_yuksek_bitisik']} (esik {cesitlilik['esik']}) -> "
          f"{len(cesitlilik['esigi_asan'])} cift esigi asiyor")

    # ── [3/7] SAHNE SURELERI ──
    cumleler, manifest = girdi_kur(secilen, sinirlar, ses_kalite["kesim_sn"])
    sureler = [c["sure_sn"] for c in cumleler]
    toplam = round(sum(sureler), 3)
    print(f"\n[3/7] SAHNE SURELERI (SentenceBoundary'den, sabit blok YOK)")
    for c in cumleler:
        print(f"      {c['scene_id']} {c['fact_id']} sure={c['sure_sn']:>6.3f} sn")
    print(f"      toplam {toplam} sn | yayilim "
          f"{round(max(sureler) - min(sureler), 3)} sn "
          f"| benzersiz sure {len(set(sureler))}/{len(sureler)}")

    ambans, ambans_once, ambans_sonra = ambans_hazirla(
        os.path.join(CALISMA, "ses"), toplam)
    if ambans:
        print(f"      ambiyans: {ambans_once.get('lufs')} LUFS -> "
              f"{ambans_sonra.get('lufs')} LUFS (hedef {AMBANS_LUFS})")

    # ── [4/7] PLAN + ON-RENDER KAPI ──
    sonuc = edit_kopru.plan_kur(
        cumleler=cumleler, medya_manifest=manifest, olgular=OLGULAR,
        stil=None, cikti_dizin=CALISMA,
        is_ayar={"editor_v2": True, "kalite_kapisi": True},
        ambience=ambans, kare_olcu=OLCU,
        anlatim_bitis_sn=ses_kalite["anlatim_bitis_sn"],
        benzerlik_okuyucu=benzerlik)
    if not sonuc["ok"]:
        print(f"BLOKE: plan kurulamadi -> {sonuc['neden']}")
        return 4
    qa = sonuc["qa"]
    print(f"\n[4/7] PLAN: profil={sonuc['profil_adi']} "
          f"QA={qa['durum']} (fail={qa['fail']} warn={qa['warn']}) "
          f"render_edilebilir={sonuc['render_edilebilir']}")
    # ⚠ BEAT BOLUNMESI SESSIZ KALMASIN. Bir sahne iki beat'e bolunurse iki
    # beat sahnenin tek adayini paylasir ve AYNI GORSEL ARKA ARKAYA cikar.
    # Kapi bunu zaten FAIL ediyor ama sebebi gormek icin ayrica raporlanir.
    zincir = edit_kopru.sahne_zinciri(sonuc["props"])
    if len(zincir) != len(cumleler):
        print(f"      ⚠ BEAT BOLUNMESI: {len(cumleler)} sahne -> "
              f"{len(zincir)} beat. Bolunen sahne(ler) tek adayi paylasir.")
        for z in zincir:
            print(f"        {z['beat_id']} {z['scene_id']} "
                  f"sure={z['sure_sn']} asset={z.get('asset_id') or '(YOK)'}")
    medyasiz = [z for z in zincir if not z.get("asset_id")]
    if medyasiz:
        print(f"      ⚠ MEDYASIZ SAHNE: {[z['beat_id'] for z in medyasiz]} "
              f"(saglayici kotasi ya da aday yoklugu) -> fallback kart")
    on_qa = json.load(open(os.path.join(CALISMA, "editor_qa.json"),
                           encoding="utf-8"))
    for s in on_qa["sorunlar"]:
        if s["seviye"] in ("fail", "warn"):
            print(f"        {s['seviye'].upper():<5} {s['kod']}: "
                  f"{s['detay'][:100]}")
    if not sonuc["render_edilebilir"]:
        print("BLOKE: on-render QA FAIL — render BASLATILMADI")
        return 5

    # ── [5/7] SES PROPS + RENDER ──
    props = dict(sonuc["props"])
    ses_blok = dict(props.get("ses") or {})
    ses_blok["anlatim"] = anlatim
    ses_blok["anlatim_seviye"] = 1.0
    ses_blok["yapay_ses"] = True
    if ambans:
        ses_blok["ambans"] = [ambans]
        ses_blok["ambans_seviye"] = AMBANS_SEVIYE
        ses_blok["ducking"] = {"ambans": AMBANS_DUCK}
        # ⚠ ASIL DUZELTME: `anlatim_araliklari` verilmediginde Ses.tsx TUM
        # videoyu anlatim sayiyor ve ambiyansi bastan sona kisiyor. Gercek
        # konusma araliklari verilince ambiyans cumle aralarinda geri geliyor.
        ses_blok["anlatim_araliklari"] = [
            [round(s["bas"], 3), round(s["bas"] + s["sure"], 3)]
            for s in sinirlar]
    props["ses"] = ses_blok

    props = remotion_v2.props_hazirla(props, calisma_dizin=CALISMA)
    kontrol = remotion_v2.dogrula(props)
    print(f"\n[5/7] ON-RENDER KAPISI: {kontrol['durum']} "
          f"({len(kontrol['sorunlar'])} sorun)")
    if kontrol["durum"] == "FAIL":
        for s in kontrol["sorunlar"][:5]:
            print(f"        FAIL {s.get('kod')}: {s.get('detay')}")
        return 6

    os.makedirs(CIKTI_DIZIN, exist_ok=True)
    video = os.path.join(CIKTI_DIZIN, VIDEO_ADI)
    print(f"      RENDER -> {os.path.relpath(video, DEPO)}")
    r = remotion_v2.render(props, video, olcu=OLCU, fps=FPS, crf=20,
                           concurrency=2, zaman_asimi=1200)
    if r["rc"] != 0 or not r.get("var_mi"):
        print(f"BLOKE: render basarisiz (rc={r['rc']}) "
              f"{str(r.get('stderr') or '')[:300]}")
        return 7
    print(f"      render {r['sure_sn']:.1f} sn")

    # ── [6/7] OLCUM ──
    print("\n[6/7] OLCUM")
    video_ses = ses_olc(video)
    pr = kos(["ffprobe", "-v", "error", "-show_entries",
              "stream=codec_type,codec_name,width,height,r_frame_rate,"
              "sample_rate,channels", "-show_entries",
              "format=duration,size,bit_rate", "-of", "json", video], 60)
    ffp = json.loads(pr.stdout or "{}")
    ak = ffp.get("streams") or []
    v = next((a for a in ak if a.get("codec_type") == "video"), {})
    a = next((a for a in ak if a.get("codec_type") == "audio"), {})
    bic = ffp.get("format") or {}
    print(f"      video : {v.get('codec_name')} {v.get('width')}x"
          f"{v.get('height')} @ {v.get('r_frame_rate')}")
    print(f"      ses   : {a.get('codec_name')} {a.get('sample_rate')}Hz / "
          f"{a.get('channels')}ch")
    print(f"      sure  : {float(bic.get('duration') or 0):.3f} sn  "
          f"boyut {int(bic.get('size') or 0) / 1e6:.2f} MB")
    print(f"      miks  : LUFS={video_ses.get('lufs')} "
          f"TP={video_ses.get('tepe_dbtp')} LRA={video_ses.get('lra')} "
          f"sessiz=%{video_ses.get('sessiz_pct')} "
          f"kirpma={video_ses.get('kirpma_var')}")

    # Kesme tespiti (gercek olcum)
    kr = kos(["ffmpeg", "-nostdin", "-i", video, "-filter:v",
              "select='gt(scene,0.12)',showinfo", "-f", "null", "-"])
    kesmeler = [round(float(l.split("pts_time:")[1].split()[0]), 3)
                for l in (kr.stderr or "").splitlines() if "pts_time:" in l]
    print(f"      kesme : {len(kesmeler)} adet {kesmeler[:8]}")

    # ── I-14 KAPILARI, RENDER SONRASI ──
    post = qa_son.denetle(video, kalite_kapisi=True,
                          ambans_lufs=(ambans_sonra or {}).get("lufs"),
                          anlatim_lufs=ses_kalite.get("lufs"),
                          ambans_seviye=AMBANS_SEVIYE, ducking=AMBANS_DUCK,
                          beklenen={"sure_sn": toplam,
                                    "genislik": OLCU[0], "yukseklik": OLCU[1],
                                    "fps": FPS})
    pd = post.sozluk()
    print(f"      POST-QA: {pd['durum']}")
    for s in pd["sorunlar"]:
        print(f"        {s['seviye'].upper():<5} {s['kod']}: {s['detay'][:110]}")
    kal = pd["olcumler"].get("kalite", {})
    mx, amb = kal.get("miks", {}), kal.get("ambans", {})
    print(f"      miks olcumu: sessiz %{(mx.get('sessiz_orani') or 0) * 100:.1f}"
          f" (tavan %{(mx.get('sessiz_oran_tavani') or 0) * 100:.0f}) | "
          f"olu final {mx.get('olu_final_sn')} sn "
          f"(tavan {mx.get('olu_final_esigi')} sn)")
    print(f"      ambiyans   : etkin {amb.get('etkin_lufs')} LUFS, anlatimin "
          f"{amb.get('fark_db')} dB altinda -> duyulabilir="
          f"{amb.get('duyulabilir')} bastiriyor={amb.get('bastiriyor')} "
          f"dengeli={amb.get('dengeli')}")

    # ── [7/7] KARELER (en az 6) ──
    print("\n[7/7] KARELER")
    # EN AZ 6 kare: her sahnenin ortasi + baslik bandi ani + video boyunca
    # esit araliklar. Yakin dusenler (< 0.35 sn) teke indirilir.
    sure_video = float(bic.get("duration") or toplam)
    adaylar_an = [1.2]                       # baslik bandinin gorundugu an
    _t = 0.0
    for c in cumleler:                       # her sahnenin ortasi
        adaylar_an.append(round(_t + c["sure_sn"] / 2, 2))
        _t += c["sure_sn"]
    for pay in (0.15, 0.4, 0.65, 0.9):       # esit araliklar (doldurucu)
        adaylar_an.append(round(sure_video * pay, 2))
    kare_anlari = []
    for t in sorted(set(adaylar_an)):
        if 0 <= t < sure_video and all(abs(t - x) >= 0.35 for x in kare_anlari):
            kare_anlari.append(t)
    if len(kare_anlari) < 6:
        print(f"      ⚠ yalnizca {len(kare_anlari)} ayri kare ani cikti")
    kareler = []
    for t in kare_anlari:
        ad = f"i15_kare_{str(t).replace('.', '_')}s.png"
        kare = os.path.join(CIKTI_DIZIN, ad)
        kos(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-ss", str(t),
             "-i", video, "-frames:v", "1", kare], 60)
        if os.path.exists(kare) and os.path.getsize(kare) > 1000:
            kareler.append({"an_sn": t, "dosya": os.path.relpath(kare, DEPO),
                            "bayt": os.path.getsize(kare)})
            print(f"      {t:>5} sn -> {os.path.relpath(kare, DEPO)} "
                  f"({os.path.getsize(kare) / 1000:.0f} KB)")

    # ── RAPOR ──
    baslik_katmani = next(
        (k for k in (sonuc["edit_manifest"].get("yazi_katmanlari") or [])
         if k.get("ad") == "chapter-title"), {})
    baslik_olcum = kk.baslik_olcusu(baslik_katmani.get("metin", ""),
                                    punto=baslik_katmani.get("punto", 60),
                                    kare_genislik=OLCU[0])
    baslik_olcum["kelime_kesik"] = kk.kelime_ortasi_kesik(
        SAHNE_METINLERI[0][1], baslik_katmani.get("metin", ""))
    rapor = {
        "atom": "I-15",
        "video": os.path.relpath(video, DEPO),
        "konu": "Apollo 11 ay inisi (20 Temmuz 1969)",
        "kalite_kapisi": "ACIK (kalite_kapisi=True)",
        "maliyet_usd": 0.0,
        "duzeltilen_kusurlar": {
            "baslik": {"olcum": baslik_olcum,
                       "metin": baslik_katmani.get("metin"),
                       "punto": baslik_katmani.get("punto"),
                       "kare_genislik": OLCU[0]},
            "sahne_sureleri": {
                "kaynak": "edge-tts SentenceBoundary (GERCEK zamanlama)",
                "sureler": sureler, "toplam_sn": toplam,
                "yayilim_sn": round(max(sureler) - min(sureler), 3),
                "benzersiz": len(set(sureler)),
                "cumle_sinirlari": sinirlar},
            "olu_final": {"anlatim_bitis_sn": ses_kalite["anlatim_bitis_sn"],
                          "kesim_sn": ses_kalite["kesim_sn"],
                          "kuyruk_sn": KUYRUK_SN,
                          "olculen_olu_final_sn": mx.get("olu_final_sn")},
            "ambiyans": {"kaynak_lufs": ambans_once.get("lufs"),
                         "normalize_lufs": ambans_sonra.get("lufs"),
                         "seviye": AMBANS_SEVIYE, "ducking": AMBANS_DUCK,
                         "anlatim_araliklari_gecildi": bool(ambans),
                         "olcum": amb}},
        # ⚠ DURUSTLUK NOTU: miksteki sessizlik %0 cikiyor cunku ambiyans bastan
        # sona duyulabilir seviyede. Bu "anlatimda bosluk yok" DEMEK DEGIL —
        # anlatimin KENDI bosluklari asagida ayrica olculuyor.
        "sessizlik_yorumu": {
            "mikste_sessiz_pct": video_ses.get("sessiz_pct"),
            "neden": ("ambiyans -45 dB esiginin uzerinde ve kesintisiz; "
                      "silencedetect bu yuzden aralik bulmuyor"),
            "anlatim_master_sessizlikleri": ses_kalite.get("sessizlikler"),
            "anlatim_master_sessiz_pct": ses_kalite.get("sessiz_pct"),
            "cumle_arasi_bosluklar_sn": [
                round(sinirlar[i + 1]["bas"]
                      - (sinirlar[i]["bas"] + sinirlar[i]["sure"]), 3)
                for i in range(len(sinirlar) - 1)]},
        "medya_cesitliligi": cesitlilik,
        "gorsel_secimi": {"esik_std": DETAY_ESIGI,
                          "olcumler": gorsel_olcumleri,
                          "secilen": [x["asset_id"] for x in secilen]},
        "anlatici_ses": {"motor": "edge-tts", "maliyet_usd": 0.0,
                         "secilen": ses_kalite["ses"], "adaylar": adaylar,
                         "master": ses_kalite},
        "plan": {"profil": sonuc["profil_adi"], "qa": qa,
                 "on_render_qa": on_qa,
                 "efekt_kapsami": sonuc["efekt_kapsami"],
                 "kapsam_boslugu": sonuc["kapsam_bosluklari"],
                 "elenen_medya": sonuc["elenen_medya"]},
        "zincir": edit_kopru.sahne_zinciri(sonuc["props"]),
        "ffprobe": ffp,
        "video_ses_olcumu": video_ses,
        "kesmeler": {"sayi": len(kesmeler), "anlar": kesmeler},
        "post_qa": pd,
        "kareler": kareler,
        "kapsam": {
            "gercek_motor": [
                "editor.plan.uret (beat/gramer/motion/tipografi/ses/QA-on)",
                "editor.adapter.donustur",
                "editor.remotion_v2 dogrula/props_hazirla/render",
                "Remotion VidrushEditorV2 (Chrome headless + ffmpeg)",
                "edge-tts anlatim + SentenceBoundary zamanlamasi",
                "kalite_kapisi ACIK: on-render + render sonrasi"],
            "kapsam_disi": [
                "WEB'DEN MEDYA BULMA — saglayiciya HIC istek atilmadi",
                "arastirma/fact-check motoru (olgular Faz E manifestinden)",
                "canli /api/generate hatti",
                "altyazi ve kaynak kunyesi (sonraki atom)",
                "1080p (bu cikti 1280x720)",
                "ucretli API (maliyet $0.00)"]},
    }
    with open(os.path.join(CIKTI_DIZIN, "kalite_pass_i15_rapor.json"), "w",
              encoding="utf-8") as f:
        json.dump(rapor, f, ensure_ascii=False, indent=2)
    print(f"\n      rapor : outputs/sample/kalite_pass_i15_rapor.json")

    pass_mi = (qa["durum"] != "FAIL" and pd["durum"] != "FAIL")
    print("\n" + "=" * 72)
    print(f"SONUC: on-render QA={qa['durum']} · render sonrasi QA={pd['durum']}"
          f" -> {'KAPI GECILDI' if pass_mi else 'KAPI GECILEMEDI'}")
    print("⚠ Medya WEB'DEN BULUNMADI — yerel Apollo fixture'i kullanildi.")
    print("=" * 72)
    return 0 if pass_mi else 8


if __name__ == "__main__":
    sys.exit(main())
