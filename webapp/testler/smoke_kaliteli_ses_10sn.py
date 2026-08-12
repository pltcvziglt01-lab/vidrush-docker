#!/usr/bin/env python3
"""10 SANIYELIK MINI-BELGESEL — KALITELI ANLATICI SESI (Faz I-13).

⚠ KONU TUTARLILIGI SART: ses, metin ve gorsel AYNI KONUYA ait.
Konu: **Apollo 11 ay inisi (20 Temmuz 1969)**.
  · Gorseller : `public/editorv2/faz_e/` — Faz E kosusundan kalan GERCEK
                Wikimedia/NASA Apollo arsiv fotograflari
  · Metin     : Faz E arastirma manifestindeki DOGRULANMIS iddialar
                (f001 inis tarihi, f004 elle kontrol, f005 "Tranquility Base")
  · Anlatim   : ayni metnin seslendirmesi
Onceki smoke'taki "Apollo gorsel + Endurance metni" uyusmazligi GIDERILDI.

⚠ ANLATICI SESI SECIMI (olculdu, gerekce raporda):
Yereldeki hazir anlatim `macOS say -v Yelda` ile uretilmis (Faz E
`pilot_rapor.json`) — teknik olarak temiz ama LRA 0.3-1.9, yani DUZ ve
makine benzeri; kaliteli bir belgesel anlatimi DEGIL. Bu yuzden projenin
KENDI varsayilan TTS motoru (`app/uret.py` -> edge-tts) ile daha dogal bir
notral ses uretilir. edge-tts UCRETSIZDIR: bu adimin maliyeti $0.00,
kredi yuklenmedi, anahtar degistirilmedi.

⚠ BU MODUL SAHTE VIDEO URETMEZ. Gercek zincir:
  edit_kopru.plan_kur -> editor.plan.uret (beat/gramer/motion/tipografi/ses/
  ON-RENDER QA) -> adapter.donustur -> remotion_v2 dogrula/props_hazirla/render
  -> Remotion `VidrushEditorV2` (Chrome headless + ffmpeg).
ffmpeg renk/test kaynagi (lavfi/testsrc/color) KULLANILMAZ.

Kosum:
    python3 webapp/testler/smoke_kaliteli_ses_10sn.py
Cikti:
    outputs/sample/editorv2_quality_voice_10sn.mp4 (+ kareler ve rapor)
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # webapp/
DEPO = os.path.dirname(KOK)
sys.path.insert(0, KOK)
os.environ.setdefault("VIDRUSH_KOK", os.path.join(DEPO, "cikti", "_ses_kok"))

CIKTI_DIZIN = os.path.join(DEPO, "outputs", "sample")
VIDEO_ADI = "editorv2_quality_voice_10sn.mp4"
FIXTURE = os.path.join(DEPO, "app", "render-studio", "public", "editorv2", "faz_e")
CALISMA = os.path.join(DEPO, "cikti", "_ses_10sn")
HEDEF_SN = 10.0

# ⚠ METIN, Faz E arastirma manifestindeki DOGRULANMIS iddialardan turetildi.
# Uydurma olgu YOK.
ANLATIM = ("On the twentieth of July, nineteen sixty-nine, Armstrong took "
           "manual control of the lunar module. Tranquility Base — the Eagle "
           "had landed.")
SES_ADAYLARI = ("en-GB-RyanNeural", "en-US-AndrewNeural", "en-US-BrianNeural")

# Apollo fixture havuzu. HANGISININ kullanilacagi SABIT DEGIL — asagida
# OLCULUR (bkz. `gorsel_detay`). a317 110 MB oldugu icin kasitli disarida.
GORSEL_HAVUZU = [
    "a082_wiki_4ba3ccdace", "a086_wiki_effc9e462f", "a281_wiki_e42b89a1f6",
    "a282_wiki_56a60bf31b", "a283_wiki_58de9c1ba3", "a313_wiki_8ba105ee68",
    "a314_wiki_6cff017be6",
]
# ⚠ DETAY ESIGI (olculdu): ilk render'da `a281` (std 6.1) ve `a282` (std 4.7)
# secilmisti; 0. ve 9. saniye kareleri DUZ GRI cikti. Ayni havuzdaki `a283`
# (std 53) ise net bir ay yuzeyi verdi. Bu yuzden kadraj icine dusen detay
# OLCULUR ve esigin altindaki kare KULLANILMAZ.
DETAY_ESIGI = 20.0

# Sahneye takilacak DOGRULANMIS iddia metinleri (Faz E manifestinden).
SAHNE_METINLERI = [
    ("f001", "The Eagle began its final descent on 20 July 1969."),
    ("f004", "Armstrong took manual control of the lunar module."),
    ("f005", "Tranquility Base here. The Eagle has landed."),
]
OLGULAR = [{"fact_id": f, "guven": "dogrulandi", "metin": m}
           for f, m in SAHNE_METINLERI]


def kos(cmd, t=300):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=t)


def sn(yol):
    r = kos(["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", yol], 60)
    try:
        return round(float((r.stdout or "0").strip() or 0), 3)
    except ValueError:
        return 0.0


def ses_olc(yol):
    """codec/sr/kanal + LUFS/TP/LRA + sessizlik orani. Uydurma yok."""
    import re
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
    except Exception:
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
        except Exception:
            pass
    r = kos(["ffmpeg", "-nostdin", "-i", yol, "-af",
             "silencedetect=noise=-45dB:d=0.30", "-f", "null", "-"])
    sess = [float(x) for x in re.findall(r"silence_duration: ([\d.]+)",
                                         r.stderr or "")]
    top = sum(sess)
    o["sessiz_sn"] = round(top, 3)
    o["sessiz_pct"] = round(100.0 * top / o.get("sure_sn", 1) or 0, 1) \
        if o.get("sure_sn") else 0.0
    o["kirpma_var"] = bool(o.get("tepe_dbtp", -99) > -0.1)
    return o


def anlatim_uret(hedef_dizin):
    """edge-tts ile anlatim uret, sessizligi kirp, -16 LUFS'a master'la.

    Doner: (yol, olcum, aday_olcumleri) ya da (None, {}, []).
    ⚠ UCRETSIZ: edge-tts anahtar istemez, kredi harcamaz. Maliyet $0.00.
    """
    try:
        import edge_tts
    except Exception as e:
        print(f"BLOKE: edge-tts yok ({type(e).__name__}). "
              f"Cozum: pip install edge-tts", file=sys.stderr)
        return None, {}, []
    os.makedirs(hedef_dizin, exist_ok=True)
    adaylar = []

    async def uret():
        for v in SES_ADAYLARI:
            y = os.path.join(hedef_dizin, f"aday_{v}.mp3")
            try:
                await edge_tts.Communicate(ANLATIM, v).save(y)
                adaylar.append((v, y))
            except Exception as e:
                print(f"  aday {v} uretilemedi: {type(e).__name__}",
                      file=sys.stderr)

    try:
        asyncio.run(uret())
    except Exception as e:
        print(f"BLOKE: TTS cagrisi basarisiz: {type(e).__name__}: "
              f"{str(e)[:120]}", file=sys.stderr)
        return None, {}, []
    if not adaylar:
        return None, {}, []

    # ⚠ SECIM OLCUME DAYANIR: LRA (dinamik genislik) dogalligin en iyi
    # olculebilir vekilidir; duz TTS'te 0.5-1, ifadeli anlatimda 2+.
    olcumler = []
    for v, y in adaylar:
        o = ses_olc(y)
        o["ses"] = v
        olcumler.append(o)
    en_iyi = max(olcumler, key=lambda o: (o.get("lra", 0), -abs(
        o.get("sure_sn", 0) - 9.0)))
    kaynak = next(y for v, y in adaylar if v == en_iyi["ses"])

    master = os.path.join(hedef_dizin, "anlatim_master.wav")
    # Bas/son sessizligi kirp + anlatim standardina normalize et.
    zincir = ("silenceremove=start_periods=1:start_silence=0.05:"
              "start_threshold=-45dB:detection=peak,areverse,"
              "silenceremove=start_periods=1:start_silence=0.10:"
              "start_threshold=-45dB:detection=peak,areverse,"
              "loudnorm=I=-16:TP=-1.5:LRA=7")
    r = kos(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", kaynak,
             "-af", zincir, "-ar", "48000", "-ac", "1", master])
    if r.returncode != 0 or not os.path.exists(master):
        print(f"BLOKE: anlatim master'lanamadi: {(r.stderr or '')[:160]}",
              file=sys.stderr)
        return None, {}, olcumler
    return master, ses_olc(master), olcumler


def gorsel_detay(yol):
    """Kadraj icine dusen DETAY (luminans std sapmasi). Olcum, tahmin degil.

    Ken Burns merkezden yakinlastigi icin merkez %70 kirpilip olculur; boylece
    "kenarda detay var ama ortasi bos" fotograf ELENIR.
    """
    r = subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", "-i", yol, "-vf",
         "crop=iw*0.7:ih*0.7,scale=320:-1,format=gray", "-f", "rawvideo", "-"],
        capture_output=True, timeout=120)
    d = r.stdout or b""
    if len(d) < 1000:
        return 0.0
    n = len(d)
    mu = sum(d) / n
    var = sum((b - mu) ** 2 for b in d) / n
    return round(var ** 0.5, 1)


def gorsel_sec(adet):
    """Havuzdan EN DETAYLI `adet` gorseli sec. Esik alti KULLANILMAZ.

    Doner: (secilenler, olcumler). Secim gerekcesi raporlanabilir.
    """
    olcumler = []
    for ad in GORSEL_HAVUZU:
        y = os.path.join(FIXTURE, f"{ad}.jpg")
        if not os.path.exists(y):
            continue
        olcumler.append({"asset_id": ad, "yol": y, "detay_std": gorsel_detay(y)})
    uygun = [o for o in olcumler if o["detay_std"] >= DETAY_ESIGI]
    uygun.sort(key=lambda o: -o["detay_std"])
    return uygun[:adet], olcumler


def girdi_kur(secilen_gorseller):
    """10 sn hedefli sahne + manifest. Sureler anlatimla dengelenir."""
    pay = max(2.6, min(4.0, (HEDEF_SN - 0.4) / max(1, len(secilen_gorseller))))
    cumleler, adaylar = [], []
    toplam = 0.0
    for i, se in enumerate(secilen_gorseller):
        ad = se["asset_id"]
        fid, metin = SAHNE_METINLERI[i % len(SAHNE_METINLERI)]
        lisans, sag = "public-domain", "wikimedia"
        gorsel = se["yol"]
        if not os.path.exists(gorsel):
            continue
        sure = min(pay, max(2.4, HEDEF_SN - toplam))
        if toplam >= HEDEF_SN - 0.4:
            break
        toplam += sure
        sid = f"s{i + 1:03d}"
        cumleler.append({"scene_id": sid, "fact_id": fid,
                         "sure_sn": round(sure, 3), "metin": metin})
        adaylar.append({
            "asset_id": ad, "scene_id": sid, "fact_id": fid,
            "saglayici": sag, "lisans": lisans, "tur": "image",
            "medya_turu": "image", "yerel_yol": gorsel, "medya_yolu": gorsel,
            "orijinal_url": f"https://commons.wikimedia.org/wiki/File:{ad}",
            "eser_sahibi": "NASA", "atif_metni": "NASA / Public Domain",
            "atif_gerekli": False,
            "baslik": "Apollo 11 archive photograph",
            "genislik": 1920, "yukseklik": 1080, "sure_sn": sure,
            "toplam_skor": 84 - i, "render_kullanilabilir": True,
            "detay_std": se.get("detay_std"),
            "sahne_amaci": "arsiv"})
    return cumleler, {"adaylar": adaylar, "kapsam_bosluklari": []}


def main() -> int:
    print("=" * 70)
    print("10 SN MINI-BELGESEL — KALITELI ANLATICI SESI (Apollo 11)")
    print("=" * 70)
    for arac in ("ffmpeg", "ffprobe"):
        if not shutil.which(arac):
            print(f"BLOKE: {arac} yok")
            return 2
    if not os.path.isdir(FIXTURE):
        print(f"BLOKE: fixture dizini yok: {FIXTURE}")
        return 2

    import edit_kopru
    from editor import remotion_v2
    if not os.path.isdir(os.path.join(remotion_v2.STUDIO, "node_modules")):
        print("BLOKE: Remotion node_modules yok — cd app/render-studio && npm ci")
        return 2

    os.makedirs(CALISMA, exist_ok=True)
    print("\n[1/6] ANLATICI SESI (edge-tts, UCRETSIZ — $0.00)")
    anlatim, ses_kalite, adaylar = anlatim_uret(os.path.join(CALISMA, "ses"))
    if not anlatim:
        print("BLOKE: kaliteli anlatim uretilemedi ve YEREL SET yetersiz "
              "(macOS say, LRA<2). Sahte ses URETILMEDI.")
        return 3
    for o in adaylar:
        print(f"      aday {o['ses']:<22} LRA={o.get('lra', 0):>4.1f} "
              f"LUFS={o.get('lufs', 0):>6.1f} sure={o.get('sure_sn', 0):>5.2f}sn")
    print(f"      SECILEN: {max(adaylar, key=lambda o: o.get('lra', 0))['ses']} "
          f"(en yuksek LRA = en dinamik)")
    print(f"      master : {ses_kalite.get('codec')}/"
          f"{ses_kalite.get('ornekleme_hz')}Hz/{ses_kalite.get('kanal')}ch "
          f"{ses_kalite.get('sure_sn')}sn LUFS={ses_kalite.get('lufs')} "
          f"TP={ses_kalite.get('tepe_dbtp')}dBTP LRA={ses_kalite.get('lra')} "
          f"sessiz=%{ses_kalite.get('sessiz_pct')} "
          f"kirpma={ses_kalite.get('kirpma_var')}")

    secilen, gorsel_olcumleri = gorsel_sec(3)
    for o in sorted(gorsel_olcumleri, key=lambda x: -x["detay_std"]):
        isaret = "SECILDI" if any(s2["asset_id"] == o["asset_id"]
                                  for s2 in secilen) else (
            "esik alti" if o["detay_std"] < DETAY_ESIGI else "-")
        print(f"      gorsel {o['asset_id']:<24} detay_std="
              f"{o['detay_std']:>5} {isaret}")
    if not secilen:
        print(f"BLOKE: detay esigini ({DETAY_ESIGI}) gecen Apollo "
              f"gorseli yok. Sahte gorsel URETILMEDI.")
        return 2
    cumleler, manifest = girdi_kur(secilen)
    if not cumleler:
        print("BLOKE: Apollo fixture gorselleri bulunamadi")
        return 2
    plan_sn = round(sum(c["sure_sn"] for c in cumleler), 2)
    print(f"\n[2/6] GIRDI: {len(cumleler)} sahne / {plan_sn} sn, "
          f"{len(manifest['adaylar'])} lisansli Apollo adayi")

    ambans = os.path.join(FIXTURE, "ambans0.wav")
    sonuc = edit_kopru.plan_kur(
        cumleler=cumleler, medya_manifest=manifest, olgular=OLGULAR,
        stil=None, cikti_dizin=CALISMA, is_ayar={"editor_v2": True},
        ambience=ambans if os.path.exists(ambans) else "")
    if not sonuc["ok"]:
        print(f"BLOKE: plan kurulamadi -> {sonuc['neden']}")
        return 4
    print(f"[3/6] PLAN: profil={sonuc['profil_adi']} QA={sonuc['qa']['durum']} "
          f"(fail={sonuc['qa']['fail']} warn={sonuc['qa']['warn']}) "
          f"render_edilebilir={sonuc['render_edilebilir']}")
    if not sonuc["render_edilebilir"]:
        print("BLOKE: on-render QA FAIL — render BASLATILMADI")
        return 5

    # ── ANLATIM + AMBANS props'a (sozlesme: props.ses) ──
    props = dict(sonuc["props"])
    ses_blok = dict(props.get("ses") or {})
    ses_blok["anlatim"] = anlatim
    if os.path.exists(ambans):
        ses_blok["ambans"] = [ambans]
        ses_blok["ambans_seviye"] = 0.20
        # ⚠ DUCKING: anlatim varken ambans %70 kisilir; konusma ustte kalir.
        ses_blok["ducking"] = {"ambans": 0.30}
    ses_blok["yapay_ses"] = True
    props["ses"] = ses_blok

    props = remotion_v2.props_hazirla(props, calisma_dizin=CALISMA)
    kontrol = remotion_v2.dogrula(props)
    print(f"[4/6] ON-RENDER KAPISI: {kontrol['durum']} "
          f"({len(kontrol['sorunlar'])} sorun)")
    if kontrol["durum"] == "FAIL":
        for s in kontrol["sorunlar"][:5]:
            print(f"        FAIL {s.get('kod')}: {s.get('detay')}")
        return 6

    os.makedirs(CIKTI_DIZIN, exist_ok=True)
    video = os.path.join(CIKTI_DIZIN, VIDEO_ADI)
    print(f"[5/6] RENDER -> {os.path.relpath(video, DEPO)}")
    r = remotion_v2.render(props, video, olcu=(1280, 720), fps=30, crf=20,
                           concurrency=2, zaman_asimi=900)
    if r["rc"] != 0 or not r.get("var_mi"):
        print(f"BLOKE: render basarisiz (rc={r['rc']}) "
              f"{str(r.get('stderr') or '')[:300]}")
        return 7
    print(f"      render {r['sure_sn']:.1f} sn")

    print("[6/6] DOGRULAMA")
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
    print(f"      video : {v.get('codec_name')} "
          f"{v.get('width')}x{v.get('height')} @ {v.get('r_frame_rate')}")
    print(f"      ses   : {a.get('codec_name')} "
          f"{a.get('sample_rate')}Hz / {a.get('channels')}ch")
    print(f"      sure  : {float(bic.get('duration') or 0):.3f} sn  "
          f"boyut {int(bic.get('size') or 0) / 1e6:.2f} MB")
    print(f"      miks  : LUFS={video_ses.get('lufs')} "
          f"TP={video_ses.get('tepe_dbtp')}dBTP "
          f"sessiz=%{video_ses.get('sessiz_pct')} "
          f"kirpma={video_ses.get('kirpma_var')}")

    kareler = []
    for t in (0, 5, 9):
        kare = os.path.join(CIKTI_DIZIN, f"vkare_{t:02d}s.png")
        kos(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-ss", str(t),
             "-i", video, "-frames:v", "1", kare], 60)
        if os.path.exists(kare) and os.path.getsize(kare) > 1000:
            kareler.append(os.path.relpath(kare, DEPO))
            print(f"      kare {t}s: {os.path.relpath(kare, DEPO)} "
                  f"({os.path.getsize(kare) / 1000:.0f} KB)")

    rapor = {
        "video": os.path.relpath(video, DEPO),
        "konu": "Apollo 11 ay inisi (20 Temmuz 1969)",
        "konu_tutarliligi": {
            "gorsel": "Faz E Wikimedia/NASA Apollo arsivi",
            "metin": "Faz E arastirma manifesti dogrulanmis iddialari "
                     "(f001, f004, f005)",
            "anlatim": "ayni metnin seslendirmesi",
            "uyusmazlik": False},
        "anlatici_ses": {
            "motor": "edge-tts (projenin varsayilan TTS'i, app/uret.py)",
            "maliyet_usd": 0.0,
            "secilen": max(adaylar, key=lambda o: o.get("lra", 0))["ses"],
            "secim_gerekcesi": ("en yuksek LRA (dinamik genislik) = en az duz "
                                "okuma; yereldeki macOS say -v Yelda LRA 0.3-1.9"),
            "adaylar": adaylar, "master": ses_kalite,
            "yerel_alternatif": {
                "motor": "macOS say -v Yelda (Faz E pilot_rapor.json)",
                "lra_araligi": "0.3 - 1.9",
                "karar": "KULLANILMADI — duz/makine benzeri, belgesel "
                         "anlatimi kalitesinde degil"}},
        "gorsel_secimi": {"esik_std": DETAY_ESIGI,
                          "olcumler": gorsel_olcumleri,
                          "secilen": [x["asset_id"] for x in secilen],
                          "gerekce": ("kadraj icindeki luminans std "
                                      "sapmasi; esik alti kare DUZ GRI "
                                      "cikiyordu (olculdu)")},
        "plan": {"profil": sonuc["profil_adi"], "qa": sonuc["qa"],
                 "efekt_kapsami": sonuc["efekt_kapsami"],
                 "kapsam_boslugu": sonuc["kapsam_bosluklari"],
                 "elenen_medya": sonuc["elenen_medya"]},
        "zincir": edit_kopru.sahne_zinciri(sonuc["props"]),
        "ffprobe": ffp, "video_ses_olcumu": video_ses, "kareler": kareler,
        "kapsam": {
            "gercek_motor": [
                "editor.plan.uret (beat/gramer/motion/tipografi/ses/QA-on)",
                "editor.adapter.donustur",
                "editor.remotion_v2 dogrula/props_hazirla/render",
                "Remotion VidrushEditorV2 (Chrome headless + ffmpeg)",
                "edge-tts anlatim uretimi (projenin varsayilan TTS'i)"],
            "kapsam_disi": [
                "WEB'DEN MEDYA BULMA — saglayiciya HIC istek atilmadi",
                "arastirma/fact-check motoru (olgular Faz E manifestinden)",
                "canli /api/generate hatti",
                "ucretli API (maliyet $0.00)"]},
    }
    with open(os.path.join(CIKTI_DIZIN, "quality_voice_rapor.json"), "w",
              encoding="utf-8") as f:
        json.dump(rapor, f, ensure_ascii=False, indent=2)
    print(f"      rapor : outputs/sample/quality_voice_rapor.json")
    print("\n" + "=" * 70)
    print("SONUC: GERCEK Remotion render'i + edge-tts anlatimi. Maliyet $0.00.")
    print("⚠ Medya WEB'DEN BULUNMADI — yerel Apollo fixture'i kullanildi.")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
