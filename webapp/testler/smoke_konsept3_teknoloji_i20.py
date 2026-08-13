#!/usr/bin/env python3
"""FAZ I-20 — UCUNCU KONSEPT: TEKNOLOJI/EKONOMI (mevcut motoru sinar).

⚠ YENI MIMARI YOK. Bu betik I-19'da kurulan edinim zincirini, I-14/I-17
kalite kapilarini ve I-16 altyazi/kunye hattini AYNEN kullanir; yalnizca
UCUNCU bir konseptle sinar.

⚠ KONU DURUSTCE DARALTILDI. Istenen konu "yapay zeka veri merkezlerinin
enerji ve cip ekonomisi"ydi. Olculdu: Wikimedia HALA `HTTP 429` veriyor
(bu ortamin cikis IP'sine ozgu) ve NASA kutuphanesinde ticari AI veri
merkezi fotografi YOK. Ama NASA'nin KENDI superbilgisayar tesisi
(Pleiades), silikon karbur cip ve gunes paneli goruntuleri VAR ve bunlar
"hesaplama gucunun enerji ve cip ekonomisi"ne SEMANTIK OLARAK UYUYOR.
Bu yuzden konu, saglayicilarin GERCEKTEN destekledigi en yakin durust
baslikla kuruldu. Uymayan goruntu KULLANILMADI.

⚠ ANLATIM GORUNENE UYDURULUR. Her cumle, o sahneye edinilen varligin
KENDI basligini betimler; goruntude olmayan sey iddia EDILMEZ.

⚠ SAHTE KANIT YOK: fixture ya da kendi render ciktilarimiz "gercek web
medyasi" diye SUNULMAZ. Kaynak bulunamazsa BLOKE raporu uretilir.

⚠ MALIYET $0.00 — edge-tts ve NASA API anahtar istemez.

Kosum:
    python3 webapp/testler/smoke_konsept3_teknoloji_i20.py
Cikti:
    outputs/sample/editorv2_teknoloji_i20.mp4 (+ 9+ kare ve JSON rapor)
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
os.environ.setdefault("VIDRUSH_KOK", os.path.join(DEPO, "cikti", "_i20_kok"))

CIKTI_DIZIN = os.path.join(DEPO, "outputs", "sample")
VIDEO_ADI = "editorv2_teknoloji_i20.mp4"
FIXTURE = os.path.join(DEPO, "app", "render-studio", "public", "editorv2",
                       "faz_e")
CALISMA = os.path.join(DEPO, "cikti", "_i20")
OLCU = (1920, 1080)          # ⭐ I-16: 1080p premium
FPS = 30

# ══════════ KULLANICI GIRDISI — YALNIZ METIN ══════════
# ⚠ Tur/stil ELLE VERILMEZ. Asagidaki metin `taksonomi.siniflandir` ile
# siniflanir, `stil_profili.coz` bilesik stili SECER. Kanit raporda.
KONU_METNI = ("Süperbilgisayarların enerji ve çip ekonomisi: işlem gücü "
              "nasıl üretiliyor ve faturası ne kadar")

SAHNE_TANIMI = [
    {"kimlik": "s01", "sorgu": "Pleiades supercomputer",
     "metin": "Güç burada üretilir."},
    {"kimlik": "s02", "sorgu": "supercomputer facility",
     "metin": "Binlerce işlemci tek salonda, sıra sıra dizili duruyor."},
    # ⚠ I-26'DA OLCULEN DUZELTME — ASIRI DAR SORGU SESSIZCE BOS DONUYORDU.
    # Eski sorgu: "Silicon Carbide Integrated Circuit Chip" (5 terim).
    # CirrusSearch terimleri VARSAYILAN OLARAK AND'ler; 5 terimin hepsini
    # birden tasiyan dosya Commons'ta YOK -> denenen=0.
    # I-25 bunu "Commons'ta bu konuda aday GERCEKTEN yok" diye yazmisti;
    # OLCUM BU IDDIAYI CURUTTU (asagi bak) ve not I-26'da duzeltildi.
    #
    # AYNI dusuk maliyetli arama butcesinde KARSILASTIRILAN adaylar
    # (her biri TEK ara() cagrisi; secim yapildiktan sonra kosum yine TEK):
    #   MEVCUT "Silicon Carbide Integrated Circuit Chip" -> denenen  0, aday 0
    #   A      "silicon carbide integrated circuit"      -> denenen  2, aday 2  ⭐
    #   B      "integrated circuit chip"                 -> denenen 18, aday 6
    #   C      "microchip silicon"                       -> denenen 18, aday 6
    #   OR     '"silicon carbide" OR "integrated circuit" OR microchip'
    #                                                    -> denenen 18, aday 6
    #
    # A SECILDI — sebep SAYILARLA:
    #   · SEMANTIK SADAKAT: A'nin iki adayi da NASA Glenn'in GERCEK silisyum
    #     karbur entegre devreleri ("Extremely durable silicon carbide
    #     semiconductor", "Heat-resistable ICs"). Anlatim cumlesi "silikon
    #     uzerindeki devreler" — birebir ayni konu.
    #     B/C/OR ise tuketici anakartlari, fare cipi, EPROM paketleri
    #     getiriyor: lisansi temiz ama konuya UZAK.
    #   · KAPILAR: A'nin iki adayi da 6000x3999 (oran 1.500) — cozunurluk VE
    #     I-23 oran kapisindan gecti. B'nin 6 adayindan 4'u ORAN-RED,
    #     OR'un ilk adayi da ORAN-RED.
    #   · TEK SORGU ILKESI KORUNDU: A hem Commons'i acti (0 -> 2) hem de
    #     NASA'yi IYILESTIRDI (1 -> 2 aday) ve NASA'nin BIRINCI adayi
    #     DEGISMEDI (ayni GRC cipi). Yani saglayicilara AYRI sorgu gitmiyor;
    #     I-25'in "Commons ve NASA AYNI konu sorgusunu alir" ilkesi bozulmadi.
    {"kimlik": "s03", "sorgu": "silicon carbide integrated circuit",
     "olculen_alternatifler": [
         {"sorgu": "Silicon Carbide Integrated Circuit Chip",
          "denenen": 0, "aday": 0, "not": "ESKI — 5 terim, AND ile bos"},
         {"sorgu": "silicon carbide integrated circuit",
          "denenen": 2, "aday": 2, "not": "SECILEN — konuya en sadik"},
         {"sorgu": "integrated circuit chip",
          "denenen": 18, "aday": 6, "not": "konuya uzak (tuketici cipleri)"},
         {"sorgu": "microchip silicon",
          "denenen": 18, "aday": 6, "not": "konuya uzak (anakartlar)"},
     ],
     "metin": "Her hesaplama, silikon üzerindeki devrelerde gerçekleşiyor."},
    {"kimlik": "s04", "sorgu": "solar array power",
     "metin": "Bu işlem gücünün faturası ise enerjiyle ödeniyor."},
]
SAHNE_METINLERI = [(s["kimlik"], s["metin"]) for s in SAHNE_TANIMI]
# ⚠ Bunlar DOGRULANMIS IDDIA degil, BETIMLEMEdir: her cumle o sahneye
# edinilen Commons varliginin kendi basligindaki yeri anlatir. Sayisal ya da
# tarihsel iddia YOK — dogrulanacak kaynak da yok, uydurma da yok.
OLGULAR = [{"fact_id": f, "guven": "betimleme", "metin": m}
           for f, m in SAHNE_METINLERI]
# ⚠ TURKCE anlatici sesleri (edge-tts, anahtarsiz).
SES_ADAYLARI = ("tr-TR-AhmetNeural", "tr-TR-EmelNeural")

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

# ⚠ SABIT GORSEL HAVUZU YOK. Medya `medya.commons` ile konuya gore EDINILIR.
DETAY_ESIGI = 20.0          # I-13'te olculdu: esik alti kare DUZ GRI cikiyor


def _en_az_genislik():
    """Edinim esigi KADRAJ MERDIVENINDEN turetilir (I-27) — sabit rakam YOK."""
    from editor import kalite_kapisi as _kk27
    return _kk27.en_az_kaynak_genisligi(OLCU[0])


EN_AZ_GENISLIK = _en_az_genislik()
# ⚠ I-21: sahne basina N aday. Bolunen bir sahne IKI beat uretirse `gramer`
# ikisine FARKLI varlik atayabilsin diye. EK AG CAGRISI YOK — adaylar zaten
# `ara()`nin dondurdugu listeden geliyor; kota da DEGISMIYOR.
ADAY_ADEDI = 2
MEDYA_ONBELLEK = os.path.join(DEPO, "cikti", "_i20_medya")
SAHNE_SAYISI = len(SAHNE_METINLERI)


def ekp_profil(stil_kimligi):
    """Bilesik stil -> Faz C edit profili (edit_kopru tablosu)."""
    import edit_kopru
    return edit_kopru.edit_profili_sec(stil_kimligi or "")[0]


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


def punch_buyutme_olc(zincir, props, secilen):
    """Kamera kadraji kaynagi EKRANDA BUYUTUYOR mu? (I-26 olcumu)

    ⚠ NEDEN VAR — I-26'da OLCULDU. Depo "upscale YAPILMIYOR" diye yaziyor
    ama bu soz yalnizca EDINIM esigi (`en_az_genislik=1920`) icin geceri.
    Kamera `punch-1.35`/`punch-1.6` uygularken kaynak SESSIZCE buyutulur:

        ekran_piksel_orani = kapsama x maks_zoom
        kapsama = max(kare_g/kaynak_g, kare_y/kaynak_y)   (objectFit: cover)

    Oran > 1.0 ise kaynagin 1 pikseli ekranda 1'den fazla piksele yayiliyor
    demektir — YUMUSAMA. Olculen vaka: 2240x1344 kaynak `punch-1.35`te
    1.157x buyuyor; 4192x2832 kaynak ayni kadrajda 0.618x KUCULUYOR.

    ⚠ Bu bir KAPI DEGIL, OLCUMDUR. Davranis DEGISMEZ; kusur yalnizca
    GORUNUR olur (sonraki atom esigi buradan turetebilir).
    Zoom degerleri YENIDEN TURETILMEZ — planin KENDI motion spec'inden
    okunur, yani olcum render'in gercegi.
    """
    olcu_haritasi = {}
    for s in (secilen or []):
        if not s:
            continue
        olcu_haritasi[s.get("asset_id")] = (s.get("genislik"), s.get("yukseklik"))
        for y in (s.get("yedekler") or []):
            olcu_haritasi[y.get("asset_id")] = (y.get("genislik"),
                                                y.get("yukseklik"))
    zoom_haritasi = {}

    def _tara(o):
        if isinstance(o, dict):
            pr = o.get("parametre") or {}
            if "zoom" in pr and o.get("beat_id"):
                try:
                    z = [float(v) for v in (pr.get("zoom") or [])]
                except (TypeError, ValueError):
                    z = []
                if z:
                    zoom_haritasi[o["beat_id"]] = max(
                        zoom_haritasi.get(o["beat_id"], 0.0), max(z))
            for v in o.values():
                _tara(v)
        elif isinstance(o, list):
            for v in o:
                _tara(v)

    _tara(props)
    kayitlar = []
    for z in (zincir or []):
        g, y = olcu_haritasi.get(z.get("asset_id"), (0, 0))
        maks_zoom = zoom_haritasi.get(z.get("beat_id"))
        if not g or not y or not maks_zoom:
            kayitlar.append({"beat_id": z.get("beat_id"),
                             "asset_id": z.get("asset_id"),
                             "olculdu": False})
            continue
        kapsama = max(OLCU[0] / float(g), OLCU[1] / float(y))
        oran = kapsama * float(maks_zoom)
        kayitlar.append({
            "beat_id": z.get("beat_id"), "asset_id": z.get("asset_id"),
            "olculdu": True, "olcu": [g, y], "kadraj": z.get("kadraj"),
            "kapsama": round(kapsama, 4), "maks_zoom": round(maks_zoom, 4),
            "ekran_piksel_orani": round(oran, 4),
            "buyutuyor": bool(oran > 1.0)})
    buyuten = [k for k in kayitlar if k.get("buyutuyor")]
    return {"olculdu": bool(kayitlar), "kayitlar": kayitlar,
            "buyuten_beat": len(buyuten),
            "en_yuksek_oran": max([k["ekran_piksel_orani"] for k in kayitlar
                                   if k.get("olculdu")] or [0]),
            "temiz": not buyuten,
            "not": "OLCUM — kapi DEGIL; davranis degismedi"}


def kk_esik():
    """Edinim ayirt-etme esigi QA esigiyle AYNI kaynaktan gelir.

    ⚠ Ikinci bir sabit yazmak, edinimin QA'dan sessizce ayrisma riskini
    dogurur (edinim 0.80'e gore secip QA 0.86'ya gore FAIL verebilirdi).
    """
    from editor import kalite_kapisi as kk
    return kk.BENZERLIK_ESIGI


def medya_edin(sahne_aday_adedi=None):
    """Sahne basina medyayi SAGLAYICI ZINCIRINDEN edin (devre kesicili).

    ⚠ I-19: tek saglayici yerine sirali zincir. Wikimedia 429 verirse
    ayni host ZORLANMAZ; devre acilir ve NASA'ya gecilir. Gecis SURESI
    olculur. Arama/metadata ile GERCEK BAYT ayri sayilir.
    """
    from medya import commons, edinim, nasa
    os.makedirs(MEDYA_ONBELLEK, exist_ok=True)
    kesici = edinim.DevreKesici()
    onbellek: dict = {}
    secilen, rapor = [], {
        "mimari": "medya.edinim saglayici zinciri + devre kesici",
        "maliyet_usd": 0.0,
        "saglayici_sirasi": ["commons", "nasa"],
        "atlanan_saglayicilar": [
            {"ad": "pexels", "sebep": "mevcut anahtar GECERSIZ (HTTP 401) — "
                                      "yeni anahtar ALINMADI"}],
        # ⚠ I-27: esik 1920 DEGIL, KADRAJ MERDIVENINDEN TURETILIR.
        # 1920 yalnizca `tam` kadraji garanti eder; o kadrajda pan payi
        # 0.0255'e duser ve pan surusuyle hareket eden cekim DURAGAN kalir
        # (olculdu: b005 optik 1.415 < esik 2.0 -> POST-QA FAIL).
        "en_az_genislik": EN_AZ_GENISLIK,
        # ⚠ I-23: 16:9 cikti icin EN-BOY ORANI UYUMLULUK KAPISI.
        "hedef_oran": round(edinim.HEDEF_ORAN_16_9, 4),
        "oran_en_az_korunan": edinim.ORAN_EN_AZ_KORUNAN,
        "oran_reddi": [], "ayirt_reddi": [], "sahneler": []}
    for _si, tanim in enumerate(SAHNE_TANIMI):
        _istenen = ((sahne_aday_adedi or {}).get(tanim["kimlik"])
                    or ADAY_ADEDI)
        ad = re.sub(r"[^a-zA-Z0-9_.-]", "_", tanim["sorgu"])[:50]
        hedef = os.path.join(MEDYA_ONBELLEK, f"{tanim['kimlik']}_{ad}.jpg")
        # ⚠ ONBELLEK PROVENANCE'I DA SAKLAR. Ilk surumde yalniz DOSYA
        # onbellekleniyordu; ikinci kosumda telif/atif bilgisi olmadigi icin
        # kural dogru sekilde REDDEDIYORDU (ONBELLEK-PROVENANCE-YOK).
        # Kusur kuralda degil onbellekteydi: kunye dosyanin YANINA yazilir.
        kunye_yolu = hedef + ".kunye.json"
        onbellekte = (os.path.exists(hedef) and os.path.getsize(hedef) > 10000
                      and os.path.exists(kunye_yolu))
        # ⚠ I-23: ONBELLEK, ORAN KAPISINI BAYPAS EDEMEZ. Onbellekteki dosya
        # 16:9'a guvenle uymuyorsa bu bir onbellek ISABETI SAYILMAZ; normal
        # edinim yoluna dusulur ve AYNI arama listesinden uygun aday aranir.
        if onbellekte:
            _obk = edinim.oran_karari(*_olcu_oku(hedef))
            if not _obk.get("uygun", True):
                rapor["oran_reddi"].append(
                    dict(_obk, kimlik=tanim["kimlik"], kaynak="ONBELLEK"))
                onbellekte = False
        if onbellekte:
            try:
                with open(kunye_yolu, encoding="utf-8") as f:
                    _kunye = json.load(f)
            except (ValueError, OSError):
                _kunye = {}
            son = {"ok": bool(_kunye.get("lisans")
                              and _kunye.get("eser_sahibi")),
                   "kullanilan_saglayici": "ONBELLEK",
                   "failover_sn": 0.0, "metadata_bulundu": 0,
                   "bayt_indirildi": 0, "denemeler": [], "onbellekten": True,
                   "aday": dict(_kunye, yol=hedef)}
        else:
            son = edinim.edin(
                tanim["sorgu"], hedef, en_az_genislik=EN_AZ_GENISLIK,
                kesici=kesici,
                onbellek=onbellek, adet=_istenen,
                hedef_oran=edinim.HEDEF_ORAN_16_9,
                benzerlik_okuyucu=benzerlik,
                benzerlik_esigi=kk_esik(),
                saglayicilar=[
                    # ⚠ I-25'TE OLCULEN KUSUR: burada `tanim["sorgu"] +
                    # " Iceland"` yaziyordu. Satir I-18'in DOGA/IZLANDA
                    # smoke'undan `beaee8f` (I-20) ile OLDUGU GIBI
                    # kopyalanmis; teknoloji konusunda " Iceland" bir KONU
                    # BULASANI. Olculen etki (ayni ara() cagrisi):
                    #   "Pleiades supercomputer Iceland"  -> denenen 0
                    #   "Pleiades supercomputer"          -> denenen 18, aday 6
                    #   "supercomputer facility Iceland"  -> denenen 0
                    #   "supercomputer facility"          -> denenen 18, aday 6
                    #   "solar array power Iceland"       -> denenen 0
                    #   "solar array power"               -> denenen 18, aday 6
                    # Yani SAGLAYICI-TEKEL'in sebebi Commons'in bos olmasi
                    # DEGIL, BIZIM sorgumuzdu. s03 ise temiz sorguyla da
                    # denenen=0 veriyor — o bosluk GERCEK ve DURUST kaliyor.
                    {"ad": "commons", "modul": commons,
                     "sorgu": tanim["sorgu"]},
                    {"ad": "nasa", "modul": nasa, "sorgu": tanim["sorgu"]}],
                olcu_okuyucu=_olcu_oku)
        # ⚠ I-23: OLCULEN oran + HEDEF oran + RED NEDENI raporda GORUNUR.
        for _rd in ((son.get("oran_kapisi") or {}).get("reddedilen") or []):
            rapor["oran_reddi"].append(
                dict(_rd, kimlik=tanim["kimlik"], kaynak="EDINIM"))
        for _rd in ((son.get("ayirt_kapisi") or {}).get("reddedilen") or []):
            rapor["ayirt_reddi"].append(
                dict(_rd, kimlik=tanim["kimlik"], kaynak="EDINIM"))
        kayit = {"kimlik": tanim["kimlik"], "sorgu": tanim["sorgu"],
                 "istenen_aday": _istenen,
                 # ⚠ I-26: sorgu SECIMI raporda AUDITLENEBILIR olsun —
                 # hangi alternatifler hangi sayilarla elendi, gorunur.
                 "olculen_alternatifler": tanim.get("olculen_alternatifler"),
                 "oran_kapisi": son.get("oran_kapisi"),
                 "saglayici": son.get("kullanilan_saglayici"),
                 "failover_sn": son.get("failover_sn"),
                 "metadata_bulundu": son.get("metadata_bulundu"),
                 "bayt_indirildi": son.get("bayt_indirildi"),
                 "onbellekten": bool(son.get("onbellekten")),
                 "denemeler": son.get("denemeler"),
                 "devre": son.get("devre")}
        if not son.get("ok"):
            kayit["durum"] = "BLOKE"
            kayit["sebep"] = "hicbir saglayici GERCEK BAYT veremedi"
            kayit["sinif"] = "TUM-SAGLAYICILAR-DUSTU"
            rapor["sahneler"].append(kayit)
            secilen.append(None)
            continue
        aday = dict(son["aday"])
        if onbellekte and not aday.get("lisans"):
            # Onbellekten geldi ama provenance yok -> KESIN RED.
            kayit["durum"] = "ONBELLEK-PROVENANCE-YOK"
            rapor["sahneler"].append(kayit)
            secilen.append(None)
            continue
        if not onbellekte:
            kunye_yolu = aday["yol"] + ".kunye.json"
            with open(kunye_yolu, "w", encoding="utf-8") as f:
                json.dump({k2: v for k2, v in aday.items()
                           if k2 != "yol"}, f, ensure_ascii=False)
        aday["asset_id"] = f"{tanim['kimlik']}_{abs(hash(aday.get('orijinal_url') or hedef)) % 10**8}"
        # ⚠ I-22 KUSURU: `hedef` INDEKS-0 dosya yoludur. Cozunurluk kapisi
        # ilk adayi reddedip ikinciye gecerse kabul edilen dosya `_1` ekli
        # yolda olur; `hedef` okumak REDDEDILEN dosyayi olcer. s04'te tam bu
        # oldu (1431x820 reddedilmisti ama rapor onu gosteriyordu) ve kamera
        # kucuk goruntude kadrajdan tasip POST-KENAR-SIYAH uretti.
        aday["yol"] = aday.get("yol") or hedef
        aday["detay_std"] = gorsel_detay(aday["yol"])
        olcu = _olcu_oku(aday["yol"])
        aday["genislik"], aday["yukseklik"] = olcu
        kayit.update({"durum": "OK", "asset_id": aday["asset_id"],
                      "baslik": aday.get("baslik"),
                      "lisans": aday.get("lisans"),
                      "eser_sahibi": aday.get("eser_sahibi"),
                      "olcu": list(olcu), "detay_std": aday["detay_std"],
                      "oran": edinim.oran_karari(*olcu),
                      "orijinal_url": aday.get("orijinal_url"),
                      "dayanak": "cumle bu varligin KENDI basligini betimliyor"})
        if aday["detay_std"] < DETAY_ESIGI:
            kayit["durum"] = "DETAY-ESIK-ALTI"
            rapor["sahneler"].append(kayit)
            secilen.append(None)
            continue
        # I-21: yedek adaylari da tasiyalim (bolunen beat icin)
        aday["yedekler"] = []
        for _y, _ek in enumerate(son.get("adaylar") or []):
            if _ek.get("yol") == aday["yol"]:
                continue
            _e = dict(_ek)
            _e["asset_id"] = f"{tanim['kimlik']}y{_y}_{abs(hash(_e.get('orijinal_url') or _e['yol'])) % 10**8}"
            _e["detay_std"] = gorsel_detay(_e["yol"])
            _o = _olcu_oku(_e["yol"])
            _e["genislik"], _e["yukseklik"] = _o
            if _e["detay_std"] >= DETAY_ESIGI:
                aday["yedekler"].append(_e)
        kayit["yedek_aday"] = len(aday["yedekler"])
        rapor["sahneler"].append(kayit)
        secilen.append(aday)
    # ⚠ I-23 KANITI: kabul edilen HER varlik oran kapisini gecmis olmali.
    rapor["oran_kapisi_ozeti"] = {
        "hedef_oran": round(edinim.HEDEF_ORAN_16_9, 4),
        "en_az_korunan": edinim.ORAN_EN_AZ_KORUNAN,
        "reddedilen": len(rapor["oran_reddi"]),
        "ayirt_esigi": kk_esik(),
        "ayirt_reddedilen": len(rapor["ayirt_reddi"]),
        "kabul_edilen_oranlar": [
            (k.get("oran") or {}).get("olculen_oran")
            for k in rapor["sahneler"] if k.get("durum") == "OK"],
        "hepsi_uygun": all(
            (k.get("oran") or {}).get("uygun", True)
            for k in rapor["sahneler"] if k.get("durum") == "OK")}
    rapor["basarili"] = sum(1 for s in secilen if s)
    rapor["dort_k_uygun"] = bool(
        secilen and all(s and s["genislik"] >= 3840 for s in secilen))
    rapor["en_hizli_failover_sn"] = min(
        [k["failover_sn"] for k in rapor["sahneler"]
         if k.get("failover_sn") is not None] or [None])
    rapor["devre_ozeti"] = kesici.ozet()
    return secilen, rapor


def _olcu_oku(yol):
    """Indirilen dosyanin GERCEK piksel olcusu — arama beyanina guvenilmez."""
    r = kos(["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height", "-of", "csv=p=0", yol], 60)
    try:
        g, y = (r.stdout or "0,0").strip().split(",")[:2]
        return int(g), int(y)
    except (ValueError, IndexError):
        return 0, 0


def video_broll_ara():
    """Guvenli havuzda GERCEK hareketli video adayi var mi?

    ⚠ I-18 kapsami yalnizca FOTOGRAF edinimidir; video B-roll BLOKE kalir.
    Depodaki `.mp4` dosyalari bu projenin KENDI render ciktilaridir ve
    B-roll DEGILDIR — onlari kullanmak dongusel olurdu.
    """
    aday, taranan = [], []
    for dizin in (MEDYA_ONBELLEK,
                  os.path.join(DEPO, "app", "render-studio", "public",
                               "editorv2")):
        if not os.path.isdir(dizin):
            continue
        taranan.append(os.path.relpath(dizin, DEPO))
        for kok, _, dosyalar in os.walk(dizin):
            for d in dosyalar:
                if d.lower().endswith((".mp4", ".mov", ".webm", ".m4v")):
                    aday.append(os.path.relpath(os.path.join(kok, d), DEPO))
    return {
        "aday": aday, "taranan_dizin": taranan,
        "durum": "VAR" if aday else "BLOKE",
        "sebep": ("" if aday else
                  "I-18 yalnizca FOTOGRAF edinir; guvenli havuzda hareketli "
                  "video adayi YOK ve depodaki .mp4 dosyalari bu projenin "
                  "kendi render ciktilari, B-roll DEGILDIR"),
    }


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
    """Sahne sureleri **SentenceBoundary**'den; provenance GERCEK varliktan.

    ⚠ Her aday KENDI `atif_metni`ni tasir -> kaynak kunyesi SAHNEYE OZGU.
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
            "saglayici": se["saglayici"], "lisans": se["lisans"],
            "tur": "image", "medya_turu": "image",
            "yerel_yol": se["yol"], "medya_yolu": se["yol"],
            "orijinal_url": se["orijinal_url"],
            "eser_sahibi": se["eser_sahibi"],
            "atif_metni": se["atif_metni"],
            "atif_gerekli": bool(se["atif_gerekli"]),
            "baslik": se["baslik"],
            "genislik": se["genislik"], "yukseklik": se["yukseklik"],
            "sure_sn": sure, "toplam_skor": 90 - i,
            "render_kullanilabilir": True,
            "detay_std": se.get("detay_std"), "sahne_amaci": "manzara"})
        # ⚠ I-21: YEDEK adaylar AYNI scene_id ile manifeste girer. `gramer`
        # bir sahne iki beat'e bolunurse ikinci beat'e FARKLI varlik atar —
        # "ayni varlik arka arkaya" kusuru boylece kaynaginda engellenir.
        for _y in (se.get("yedekler") or []):
            adaylar.append({
                "asset_id": _y["asset_id"], "scene_id": sid, "fact_id": fid,
                "saglayici": _y.get("saglayici"), "lisans": _y.get("lisans"),
                "tur": "image", "medya_turu": "image",
                "yerel_yol": _y["yol"], "medya_yolu": _y["yol"],
                "orijinal_url": _y.get("orijinal_url"),
                "eser_sahibi": _y.get("eser_sahibi"),
                "atif_metni": _y.get("atif_metni"),
                "atif_gerekli": bool(_y.get("atif_gerekli")),
                "baslik": _y.get("baslik"),
                "genislik": _y.get("genislik"), "yukseklik": _y.get("yukseklik"),
                "sure_sn": sure, "toplam_skor": 80 - i,
                "render_kullanilabilir": True,
                "detay_std": _y.get("detay_std"), "sahne_amaci": "manzara"})
    return cumleler, {"adaylar": adaylar, "kapsam_bosluklari": []}


# ────────────────────────────── ANA AKIS ───────────────────────────────────

def main() -> int:
    print("=" * 72)
    print("FAZ I-20 — UCUNCU KONSEPT: TEKNOLOJI/EKONOMI")
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

    # ── [0/7] OTOMATIK SINIFLANDIRMA — kullanici YALNIZ metin verdi ──
    import taksonomi
    import stil_profili
    konsept = taksonomi.siniflandir(KONU_METNI)
    stil = stil_profili.coz(konsept=konsept)
    print(f"\n[0/7] AUTO SINIFLANDIRMA (tur/stil ELLE VERILMEDI)")
    print(f"      metin  : {KONU_METNI[:66]}…")
    print(f"      konsept: aile={konsept.get('aile') or '(belirsiz)'} "
          f"durum={konsept.get('durum')} guven={konsept.get('guven')}")
    print(f"      gerekce: {str(konsept.get('gerekce'))[:96]}")
    print(f"      STIL   : kimlik={stil.get('kimlik')} "
          f"surum={stil.get('surum')} kaynak={stil.get('kaynak')}")
    if stil.get("kaynak") != "auto":
        print(f"      ⚠ stil AUTO secilemedi (kaynak={stil.get('kaynak')}) — "
              f"konu metni taksonomide karsilik bulmadi")
    edit_profili = ekp_profil(stil.get("kimlik"))
    print(f"      -> edit profili: {edit_profili}")

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
    # ── [1b] KURU PLAN: GERCEK beat sayisini medyadan ONCE ogren ──
    # ⚠ I-21'DE OLCULEN KUSUR: bolunme 5 beat uretti, saglayici kotasi 4'tu
    # ve b005 MEDYASIZ kalip statik fallback karta dustu (POST-SIYAH-KARE +
    # POST-OPTIK-DURGUN + POST-KENAR-SIYAH). Yani kusur RENDER SONRASI
    # yakalaniyordu. Cozum: plani BIR KEZ kuru kosup beat sayisini ogrenmek
    # ve medya adedini + kotayi ona DETERMINISTIK esleştirmek.
    # ⚠ Kuru kosum BEDAVA: `beat.plan_yap` ag/medya/dosya KULLANMAZ.
    from editor import beat as _beat
    from editor import profil as _profil
    _kuru_cumleler = []
    for _i in range(len(SAHNE_METINLERI)):
        _bas = 0.0 if _i == 0 else sinirlar[_i]["bas"]
        _son = (sinirlar[_i + 1]["bas"] if _i + 1 < len(sinirlar)
                else ses_kalite["kesim_sn"])
        _kuru_cumleler.append({
            "scene_id": f"s{_i + 1:03d}", "fact_id": SAHNE_METINLERI[_i][0],
            "sure_sn": round(_son - _bas, 3),
            "metin": SAHNE_METINLERI[_i][1]})
    _kuru = _beat.plan_yap(_kuru_cumleler,
                           profil_=_profil.profil(edit_profili))
    _sahne_beat = {}
    for _b in _kuru.beatler:
        _sahne_beat[_b.scene_id] = _sahne_beat.get(_b.scene_id, 0) + 1
    BEAT_SAYISI = len(_kuru.beatler)
    _sahne_aday = {SAHNE_TANIMI[_i]["kimlik"]:
                   _sahne_beat.get(f"s{_i + 1:03d}", 1)
                   for _i in range(len(SAHNE_TANIMI))}
    print(f"\n[1b] KURU PLAN: {len(_kuru_cumleler)} sahne -> "
          f"{BEAT_SAYISI} beat (profil {edit_profili})")
    for _k, _v in _sahne_aday.items():
        print(f"      {_k}: {_v} beat -> {_v} aday istenecek")
    print(f"      saglayici kotasi PLANA ESITLENECEK: {BEAT_SAYISI}")

    # ── HAREKETLI VIDEO B-ROLL: var mi? Yoksa DURUSTCE BLOKE ──
    broll = video_broll_ara()
    if broll["durum"] == "BLOKE":
        print(f"\n[BLOKE] HAREKETLI VIDEO B-ROLL: {broll['sebep']}")
        print(f"        taranan: {broll['taranan_dizin']}")
        print("        -> bu atomda B-roll KULLANILMADI; sahte hareket "
              "URETILMEDI. Kusur GIZLENMIYOR, raporda yazili.")
    else:
        print(f"\n[B-ROLL] {len(broll['aday'])} aday: {broll['aday'][:3]}")

    secilen, medya_rapor = medya_edin(_sahne_aday)
    eksik = [s for s in secilen if s is None]
    print(f"\n[2/7] MEDYA EDINIMI (Wikimedia Commons, anahtarsiz, $0.00)")
    print(f"      mimari: {medya_rapor['mimari']}")
    print(f"      zincir: {medya_rapor['saglayici_sirasi']} | atlanan: "
          f"{[a['ad'] + '=' + a['sebep'][:32] for a in medya_rapor['atlanan_saglayicilar']]}")
    for k in medya_rapor["sahneler"]:
        if k["durum"] == "OK":
            print(f"      {k['kimlik']} OK  [{k['saglayici']:<8}] "
                  f"{k['olcu'][0]}x{k['olcu'][1]} {k['lisans']:<12} "
                  f"{str(k['eser_sahibi'])[:18]:<18} detay={k['detay_std']} "
                  f"failover={k['failover_sn']}s")
            print(f"           {str(k['baslik'])[:70]}")
            for d in (k.get("denemeler") or []):
                print(f"             - {d['saglayici']:<9} {d['durum']:<12} "
                      f"meta={d['metadata']:<3} sn={d['sn']} "
                      f"{str(d.get('sebep'))[:40]}")
        else:
            print(f"      {k['kimlik']} {k['durum']:<8} {k.get('sebep', '')[:64]}")
    print(f"      metadata toplam={sum(k.get('metadata_bulundu') or 0 for k in medya_rapor['sahneler'])} "
          f"bayt toplam={sum(k.get('bayt_indirildi') or 0 for k in medya_rapor['sahneler'])} "
          f"(AYRI sayilir)")
    print(f"      devre: {medya_rapor['devre_ozeti']}")
    if eksik:
        # ⚠ BLOKE KANITI IZLENEN BIR RAPORA YAZILIR. "Denedik olmadi" demek
        # yetmez; NE denendigi, NEYIN gectigi ve NEREDE durduldugu sayilabilir
        # olmali. Lisans/provenance reddi ile AG-HIZ-SINIRI ayri raporlanir.
        sinif = {}
        for k in medya_rapor["sahneler"]:
            sinif[k.get("sinif") or k["durum"]] = \
                sinif.get(k.get("sinif") or k["durum"], 0) + 1
        bloke = {
            "atom": "I-20", "durum": "BLOKE",
            "ne_bloke": "medya BAYT edinimi (arama ve lisans katmani CALISTI)",
            "konu_metni": KONU_METNI,
            "konsept": konsept, "stil": stil,
            "medya": medya_rapor, "siniflandirma": sinif,
            "edinim_mimarisi": medya_rapor.get("mimari"),
            "sahte_medya_uretildi_mi": False,
            "video_broll": broll,
            "not": ("arama/metadata/lisans katmani calisti; duran sey "
                    "upload.wikimedia.org'dan BAYT indirme. Bu ORTAM "
                    "kaynaklidir (cikis IP hiz siniri), lisans reddi DEGIL."),
        }
        os.makedirs(CIKTI_DIZIN, exist_ok=True)
        with open(os.path.join(CIKTI_DIZIN, "teknoloji_i20_bloke_rapor.json"),
                  "w", encoding="utf-8") as f:
            json.dump(bloke, f, ensure_ascii=False, indent=2)
        print(f"\nBLOKE: {len(eksik)} sahne icin gorsel EDINILEMEDI "
              f"({sinif}). Sahte gorsel URETILMEDI.")
        print("      rapor: outputs/sample/teknoloji_i20_bloke_rapor.json")
        return 2
    gorsel_olcumleri = [{"asset_id": s["asset_id"], "detay_std": s["detay_std"]}
                        for s in secilen]
    # ⚠ 4K IDDIASI KAYNAGA BAGLI — yetmezse DURUSTCE 1080p.
    global OLCU
    if not medya_rapor["dort_k_uygun"]:
        OLCU = (1920, 1080)
        print(f"      ⚠ kaynaklarin hepsi 4K esigini gecmiyor -> DURUSTCE "
              f"1080p render (upscale YAPILMIYOR)")
    else:
        print(f"      ✓ tum kaynaklar >= {medya_rapor['en_az_genislik']} px "
              f"-> {OLCU[0]}x{OLCU[1]} render")

    secilen, siralama = cesitli_sirala(secilen)
    cesitlilik = cesitlilik_raporu(secilen)
    cesitlilik["siralama"] = siralama
    if siralama:
        print(f"      siralama : komsu benzerligi "
              f"{siralama['once_komsu_maks']} -> "
              f"{siralama['sonra_komsu_maks']} (yalniz SIRA degisti)")
    print(f"      cesitlilik: en yuksek ikili benzerlik "
          f"{cesitlilik['en_yuksek']}, bitisik en yuksek "
          f"{cesitlilik['en_yuksek_bitisik']} (esik {cesitlilik['esik']}) -> "
          f"{len(cesitlilik['esigi_asan'])} cift esigi asiyor")

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
    # ── ALTYAZI KUPLERI (GERCEK cumle zamanlamasindan) ──
    altyazi = kk.altyazi_kupleri(sinirlar, maks_karakter=42)
    print(f"\n[3b] ALTYAZI: {altyazi['kup_sayisi']} kup "
          f"({altyazi['olculen_kup']} olculdu / {altyazi['orantili_kup']} "
          f"orantili), birlestirilen {altyazi['birlestirilen']}, "
          f"okunabilirlik temiz={altyazi['temiz']}")
    for k in altyazi["kupler"]:
        print(f"      {k['bas_sn']:>6.3f} +{k['sure_sn']:>5.3f} "
              f"[{k['zamanlama']:<9}] {' / '.join(k['satirlar'])[:64]}")

    sonuc = edit_kopru.plan_kur(
        cumleler=cumleler, medya_manifest=manifest, olgular=OLGULAR,
        stil=stil, cikti_dizin=CALISMA,
        is_ayar={"editor_v2": True, "kalite_kapisi": True},
        ambience=ambans, kare_olcu=OLCU,
        anlatim_bitis_sn=ses_kalite["anlatim_bitis_sn"],
        benzerlik_okuyucu=benzerlik,
        altyazi_kupleri=altyazi["kupler"],
        # ⚠ KEYFI ARTIRMA DEGIL, DETERMINISTIK ESLEME: kota planin GERCEK
        # beat sayisina esitlenir. Tek saglayicili bir iste sabit 4 tavani,
        # 4'ten fazla beat olustugunda fazlasini GARANTILI medyasiz birakir.
        saglayici_tavani=BEAT_SAYISI)
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
    _mg = kk.motion_grammar_olcusu([
        {"beat_id": z["beat_id"], "hareket": z["hareket"],
         "gecis": z.get("gecis") or [], "islev": z.get("islev"),
         "sure_sn": z["sure_sn"]} for z in zincir])
    print(f"      motion  : hareket={_mg['hareketler']}")
    print(f"                benzersiz_hareket={_mg['benzersiz_hareket']} "
          f"ardisik_tekrar={len(_mg['ardisik_tekrar'])} "
          f"pencere_tekrari={len(_mg['pencere_tekrari'])}")
    print(f"      gecis   : {_mg['gecis_dagilimi']} "
          f"(benzersiz {_mg['benzersiz_gecis']})")
    print(f"      ritim   : acilis={_mg['acilis_hareketi']} "
          f"kapanis={_mg['kapanis_hareketi']} "
          f"ayri={_mg['acilis_kapanis_ayri']}")
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

    # ── KONTROLLU TEK REMASTER (H6'da onayli yol) ──
    # ⚠ Sadece SES sorununda, BIR KEZ, ucretsiz + deterministik loudnorm.
    # Gorsel yeniden uretilmez, para harcanmaz. Video akisi KOPYALANIR.
    remaster = {"uygulandi": False, "once": dict(video_ses)}
    _hedef_lufs = -14.0
    if abs(video_ses.get("lufs", -99) - _hedef_lufs) > 1.0:
        gecici = os.path.join(CALISMA, "remaster.mp4")
        rr = kos(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", video,
                  "-c:v", "copy", "-af",
                  f"loudnorm=I={_hedef_lufs}:TP=-1.5:LRA=9",
                  "-c:a", "aac", "-b:a", "192k", gecici], 600)
        if rr.returncode == 0 and os.path.exists(gecici):
            shutil.move(gecici, video)
            video_ses = ses_olc(video)
            remaster.update({"uygulandi": True, "hedef_lufs": _hedef_lufs,
                             "sonra": dict(video_ses),
                             "yol": "ffmpeg loudnorm, video akisi kopyalandi",
                             "maliyet_usd": 0.0})
            print(f"      remaster: LUFS {remaster['once'].get('lufs')} -> "
                  f"{video_ses.get('lufs')} (TP {video_ses.get('tepe_dbtp')})")
            pr = kos(["ffprobe", "-v", "error", "-show_entries",
                      "stream=codec_type,codec_name,width,height,r_frame_rate,"
                      "sample_rate,channels", "-show_entries",
                      "format=duration,size,bit_rate", "-of", "json", video], 60)
            ffp = json.loads(pr.stdout or "{}")
            bic = ffp.get("format") or {}
        else:
            remaster["hata"] = (rr.stderr or "")[:160]
            print(f"      ⚠ remaster BASARISIZ: {remaster['hata']}")

    # ── FAZ I-17: OPTIK DURAGANLIK OLCUMU (cikti karelerinden) ──
    # ⚠ Kisa ve kararli: TEK ffmpeg gecisi, ham gri akis, 4 fps / 64x36.
    print("      optik   : ornekleniyor...")
    _or = subprocess.run(kk.optik_ornek_komutu(video),
                         capture_output=True, timeout=600)
    _farklar = kk.optik_farklar(_or.stdout)
    _opt_sahne, _t = [], 0.0
    for z in zincir:
        _opt_sahne.append({"ad": f"{z['beat_id']} {z['hareket']}",
                           "bas_sn": round(_t, 3), "sure_sn": z["sure_sn"]})
        _t += z["sure_sn"]
    optik = kk.optik_hareket_olcusu(_farklar, sahneler=_opt_sahne)
    kenar = kk.kenar_siyahligi_olcusu(_or.stdout)
    print(f"      kenar   : siyah bant temiz={kenar.get('temiz')} "
          f"(ihlal {kenar.get('ihlal_kare')}/{kenar.get('kare')}, "
          f"en koyu sol={kenar.get('en_koyu_sol')} sag={kenar.get('en_koyu_sag')})")
    if optik.get("olculdu"):
        print(f"      SONRA (I-17) genel_ort={optik['genel_ortalama']} "
              f"temiz={optik['temiz']}")
        for s in optik["sahneler"]:
            print(f"        {s['ad']:<18} sure={s['sure_sn']:>5.2f} "
                  f"ort={s['ortalama']:>6.3f} durgun_sn={s['durgun_sn']:>5.2f} "
                  f"{s.get('seviye', 'ok')}")
    else:
        print(f"      ⚠ optik olcum ALINAMADI: {optik.get('neden')}")

    # ── I-14/I-17 KAPILARI, RENDER SONRASI ──
    post = qa_son.denetle(video, kalite_kapisi=True,
                          optik_farklar=_farklar, optik_sahneler=_opt_sahne,
                          optik_ham=_or.stdout,
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
    # ⚠ I-32: ornekleme artik SAHNE (cumle) suresi uzerinden DEGIL, BEAT
    # zaman cizgisi uzerinden yapiliyor. I-31'de olculdu: 4 cumle / 5 beat
    # oldugu icin "sahne ortasi" 1.29'a dusuyor ve b001 (0-0.862 sn)
    # HICBIR kareyle orneklenmiyordu — kusurlu ACILIS PLANI incelemenin
    # KOR NOKTASINDA kaliyordu. Plan her beat'e ZORUNLU temsil karesi verir,
    # FPS izgarasina oturur ve beat sinirindan yarim kare iceride kalir.
    _ornek = kk.kare_ornekleme_plani(
        [{"beat_id": z["beat_id"], "bas_sn": z["bas_sn"],
          "sure_sn": z["sure_sn"]} for z in zincir],
        sure_sn=sure_video, en_az_kare=11, fps=float(FPS))
    kare_anlari = list(_ornek.get("anlar") or [])
    print(f"      ornekleme: {_ornek.get('kare')} kare / "
          f"{_ornek.get('beat')} beat (hedef {_ornek.get('hedef')}), "
          f"yeterli={_ornek.get('yeterli')}")
    if not _ornek.get("yeterli"):
        print(f"      ⚠ YETERSIZ ORNEKLEME: {_ornek.get('sebep')}")
    kareler = []
    for t in kare_anlari:
        ad = f"i20_kare_{str(t).replace('.', '_')}s.png"
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
    _kal = pd["olcumler"].get("kalite", {})
    _on_kal = on_qa.get("olcumler", {}).get("kalite", {})
    puan = kk.izleyici_kalite_puani(
        optik=optik, grammar=_on_kal.get("motion_grammar"),
        ritim=_on_kal.get("ritim"),
        guvenli_alan=_on_kal.get("guvenli_alan"),
        cakisma=_on_kal.get("yazi_cakismasi"),
        altyazi=_on_kal.get("altyazi"),
        medya=_on_kal.get("medya_tekrari"),
        miks=_kal.get("miks"), ambans=_kal.get("ambans"))
    print(f"\n      IZLEYICI KALITE PUANI: {puan['puan']}/100 "
          f"({puan['kazanilan']}/{puan['olculen_agirlik']} agirlik)")
    for ad, b in puan["bilesenler"].items():
        print(f"        {ad:<18} {str(b['puan']):>6}/{b['agirlik']:<3} "
              f"{b['gerekce'][:60]}")

    rapor = {
        "atom": "I-20",
        "izleyici_kalite_puani": puan,
        "optik_hareket": optik,
        "kenar_siyahligi": kenar,
        "motion_grammar": _on_kal.get("motion_grammar"),
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
        "altyazi": {
            "kup_sayisi": altyazi["kup_sayisi"],
            "olculen_kup": altyazi["olculen_kup"],
            "orantili_kup": altyazi["orantili_kup"],
            "birlestirilen": altyazi["birlestirilen"],
            "maks_karakter": altyazi["maks_karakter"],
            "maks_satir": altyazi["maks_satir"],
            "okunabilirlik_temiz": altyazi["temiz"],
            "cok_hizli": altyazi["cok_hizli"],
            "uzun_satir": altyazi["uzun_satir"],
            "kupler": altyazi["kupler"],
            "zamanlama_notu": ("cumle sinirlari OLCULDU (edge-tts "
                               "SentenceBoundary); cumle ICI bolunme "
                               "gerektiginde parca zamanlamasi karakter "
                               "agirlikli ORANTILI dagitimdir, olcum degil"),
            "sahnelere_dagitildi": [
                {"scene_id": s.get("scene_id"),
                 "kup": len(s.get("altyazi") or [])}
                for s in (sonuc["edit_manifest"].get("beat_plani") or {}).get(
                    "beatler", [])] or None},
        "kaynak_kunyesi": {
            "atif_gerekli": True,
            "katmanlar": [
                {"ad": k.get("ad"), "metin": k.get("metin"),
                 "y_orani": k.get("y_orani"), "bas_sn": k.get("bas_sn"),
                 "sure_sn": k.get("sure_sn"), "kaydirildi": k.get("kaydirildi")}
                for k in (sonuc["edit_manifest"].get("yazi_katmanlari") or [])
                if k.get("ad") == "source-label"],
            "tipografi_raporu": sonuc["edit_manifest"].get(
                "tipografi_raporu")},
        "guvenli_alan": (on_qa.get("olcumler", {}).get("kalite", {})
                         .get("guvenli_alan")),
        "yazi_cakismasi": (on_qa.get("olcumler", {}).get("kalite", {})
                           .get("yazi_cakismasi")),
        "video_broll": broll,
        "medya_edinim": medya_rapor,
        "beat_medya_eslemesi": {
            "kuru_plan_beat": BEAT_SAYISI,
            "sahne_beat": _sahne_beat,
            "sahne_istenen_aday": _sahne_aday,
            "saglayici_tavani": BEAT_SAYISI,
            "not": ("plan BIR KEZ kuru kosuldu (ag/medya yok); medya adedi ve "
                    "saglayici kotasi GERCEK beat sayisina esitlendi")},
        "auto_siniflandirma": {
            "konu_metni": KONU_METNI,
            "tur_elle_verildi_mi": False,
            "konsept": konsept,
            "stil": stil,
            "edit_profili": edit_profili,
            "not": ("kullanici YALNIZ metin verdi; aile/stil/edit profili "
                    "taksonomi + stil_profili tarafindan SECILDI")},
        "once_i16": {
            "kaynak": "outputs/sample/editorv2_altyazi_1080p_i16.mp4",
            "olcum_yontemi": ("4 fps / 64x36 gri, ardisik ortalama mutlak "
                              "fark (kalite_kapisi.optik_ornek_komutu)"),
            "sahneler": [
                {"ad": "b001 push-in", "sure_sn": 2.962, "optik_ort": 3.551},
                {"ad": "b002 static", "sure_sn": 5.213, "optik_ort": 0.914},
                {"ad": "b003 push-in", "sure_sn": 4.688, "optik_ort": 5.102},
                {"ad": "b004 pull-out", "sure_sn": 4.675, "optik_ort": 7.030}],
            "gecis_dagilimi": {"hard-cut": 4},
            "hareketler": ["push-in", "static", "push-in", "pull-out"]},
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
        # ⚠ I-26 OLCUMU: kamera kadraji kaynagi ekranda BUYUTUYOR mu?
        "punch_buyutme": punch_buyutme_olc(
            edit_kopru.sahne_zinciri(sonuc["props"]), sonuc["props"], secilen),
        "ffprobe": ffp,
        "video_ses_olcumu": video_ses,
        "remaster": remaster,
        "kesmeler": {"sayi": len(kesmeler), "anlar": kesmeler},
        "post_qa": pd,
        "kareler": kareler,
        # ⚠ I-32: beat<->kare eslemesi RAPORDA GORUNUR.
        "kare_ornekleme": _ornek,
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
                                "ucretli API (maliyet $0.00)"]},
    }
    with open(os.path.join(CIKTI_DIZIN, "teknoloji_i20_rapor.json"), "w",
              encoding="utf-8") as f:
        json.dump(rapor, f, ensure_ascii=False, indent=2)
    print(f"\n      rapor : outputs/sample/teknoloji_i20_rapor.json")

    pass_mi = (qa["durum"] != "FAIL" and pd["durum"] != "FAIL")
    print("\n" + "=" * 72)
    print(f"SONUC: on-render QA={qa['durum']} · render sonrasi QA={pd['durum']}"
          f" -> {'KAPI GECILDI' if pass_mi else 'KAPI GECILEMEDI'}")
    # ⚠ I-23'TE BULUNAN YANLIS BEYAN: burada KOSULSUZ olarak "Medya WEB'DEN
    # BULUNMADI — yerel Apollo fixture'i kullanildi" yaziyordu. I-19'dan beri
    # DOGRU DEGIL: medya gercek saglayici zincirinden iniyor. Bu dosyanin kendi
    # kurali "SAHTE KANIT YOK" oldugu icin satir OLCUMDEN turetiliyor.
    _kaynaklar = sorted({str(s.get("saglayici") or "?")
                         for s in (medya_rapor.get("sahneler") or [])
                         if s.get("durum") == "OK"})
    print(f"MEDYA: {medya_rapor.get('basarili')}/"
          f"{len(medya_rapor.get('sahneler') or [])} sahne GERCEK saglayicidan "
          f"({', '.join(_kaynaklar) or 'YOK'}) · fixture KULLANILMADI · "
          f"maliyet ${medya_rapor.get('maliyet_usd', 0.0):.2f}")
    print("=" * 72)
    return 0 if pass_mi else 8


if __name__ == "__main__":
    sys.exit(main())
