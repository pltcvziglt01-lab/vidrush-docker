#!/usr/bin/env python3
"""20 SANIYELIK EDITORV2 RENDER SMOKE — GERCEK render, DIS AG YOK (Faz I-11).

⚠ DURUSTCE: BU VIDEO NEYI KANITLAR, NEYI KANITLAMAZ?

KANITLAR (gercek motorun kullanilan kismi):
  · `edit_kopru.plan_kur()` -> `editor.plan.uret()` tam Faz C zinciri:
    beat -> gramer -> motion -> tipografi -> ses -> ON-RENDER QA
  · `editor.adapter.donustur()` ile GERCEK Remotion props uretimi
  · `editor.remotion_v2.dogrula()` on-render kapisi
  · `editor.remotion_v2.props_hazirla()` + `render()` ile GERCEK Remotion
    (`VidrushEditorV2` kompozisyonu) render'i — Chrome headless + ffmpeg
  · Lisans duvari, kapsam boslugu ve fact_id zincirinin props'a kadar gelmesi

KANITLAMAZ (bu smoke'un KAPSAMI DISI):
  · WEB'DEN MEDYA BULMA. Hicbir saglayiciya istek atilmaz. Gorseller ve
    sesler DAHA ONCE indirilmis YEREL fixture'lardir
    (`app/render-studio/public/editorv2/faz_e/`, Faz E kosusundan kalma).
  · Arastirma/fact-check motoru. Olgular sabit fixture'dir.
  · TTS uretimi. Ses dosyalari hazir `.wav` fixture'lardir.
  · Canli `/api/generate` hatti. Pipeline CAGRILMAZ.
  · Ucretli hicbir API. Ag cagrisi YOK.

Yani bu, "kurgu motoru gercekten video uretiyor mu" sorusunun cevabidir;
"uctan uca web medyasiyla belgesel uretiyor mu" sorusunun DEGIL.

Kosum:
    python3 webapp/testler/smoke_editorv2_20sn.py
Cikti:
    outputs/sample/editorv2_smoke_20sn.mp4  (+ kareler ve rapor)
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # webapp/
DEPO = os.path.dirname(KOK)
sys.path.insert(0, KOK)
os.environ.setdefault("VIDRUSH_KOK", os.path.join(DEPO, "cikti", "_smoke_kok"))

CIKTI_DIZIN = os.path.join(DEPO, "outputs", "sample")
VIDEO_ADI = "editorv2_smoke_20sn.mp4"
FIXTURE = os.path.join(DEPO, "app", "render-studio", "public", "editorv2", "faz_e")
HEDEF_SN = 20.0

# Fixture gorselleri (Faz E kosusundan kalma GERCEK Wikimedia dosyalari).
# ⚠ a317 dosyasi 115 MB — Remotion'da gereksiz yavaslatir, KASITLI disarida.
GORSELLER = [
    ("a082_wiki_4ba3ccdace", "cc-by-sa", "wikimedia"),
    ("a086_wiki_effc9e462f", "cc-by", "wikimedia"),
    ("a281_wiki_e42b89a1f6", "public-domain", "wikimedia"),
    ("a282_wiki_56a60bf31b", "cc-by", "wikimedia"),
    ("a283_wiki_58de9c1ba3", "cc-by-sa", "wikimedia"),
    ("a313_wiki_8ba105ee68", "public-domain", "wikimedia"),
    ("a314_wiki_6cff017be6", "cc-by", "wikimedia"),
]

CUMLELER = [
    ("s001", "f001", "The Endurance became trapped in pack ice in January 1915."),
    ("s002", "f002", "The ship drifted with the floe for ten months before it was crushed."),
    ("s003", "f003", "The crew hauled three lifeboats across the moving ice."),
    ("s004", "f004", "They reached Elephant Island in April 1916, the first solid ground in months."),
    ("s005", "f005", "A small boat crossed eight hundred miles of open sea to South Georgia."),
    ("s006", "f006", "Every member of the expedition survived the ordeal."),
    ("s007", "f007", "The photographs were carried out on glass plates and survive today."),
]

OLGULAR = [
    {"fact_id": f"f{i:03d}", "guven": "dogrulandi", "metin": m}
    for i, (_s, _f, m) in enumerate(CUMLELER, start=1)
]


def _sn(yol: str) -> float:
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                            "format=duration", "-of", "csv=p=0", yol],
                           capture_output=True, text=True, timeout=30)
        return round(float((r.stdout or "0").strip() or 0), 3)
    except Exception:
        return 0.0


def girdi_kur() -> tuple:
    """Fixture'lardan cumle listesi + medya manifesti kur (20 sn hedefli)."""
    cumleler, adaylar, bosluklar = [], [], []
    toplam = 0.0
    for i, ((sid, fid, metin), (ad, lisans, sag)) in enumerate(
            zip(CUMLELER, GORSELLER)):
        gorsel = os.path.join(FIXTURE, f"{ad}.jpg")
        ses = os.path.join(FIXTURE, f"ses_{ad}.wav")
        if not os.path.exists(gorsel):
            bosluklar.append({"scene_id": sid, "neden": f"fixture yok: {ad}"})
            continue
        ses_sn = _sn(ses) if os.path.exists(ses) else 0.0
        # 20 sn hedefi: kalan sureyi asma
        sure = min(ses_sn or 3.0, max(2.0, HEDEF_SN - toplam))
        if toplam >= HEDEF_SN - 0.5:
            break
        toplam += sure
        cumleler.append({"scene_id": sid, "fact_id": fid,
                         "sure_sn": round(sure, 3), "metin": metin})
        adaylar.append({
            "asset_id": ad, "scene_id": sid, "fact_id": fid,
            "saglayici": sag, "lisans": lisans, "tur": "image",
            "medya_turu": "image", "yerel_yol": gorsel,
            "medya_yolu": gorsel,
            "ses_yolu": ses if os.path.exists(ses) else "",
            "orijinal_url": f"https://commons.wikimedia.org/wiki/File:{ad}",
            "eser_sahibi": "Wikimedia contributor",
            "atif_metni": f"Wikimedia contributor / {lisans.upper()}",
            "atif_gerekli": lisans.startswith("cc-by"),
            "baslik": "Endurance expedition archive photograph",
            "genislik": 1920, "yukseklik": 1080, "sure_sn": ses_sn,
            "toplam_skor": 80 - i, "render_kullanilabilir": True,
            "sahne_amaci": "arsiv" if i % 2 else "establishing"})
    return cumleler, {"adaylar": adaylar, "kapsam_bosluklari": bosluklar}


def main() -> int:
    print("=" * 68)
    print("20 SN EDITORV2 RENDER SMOKE — GERCEK render, DIS AG YOK")
    print("=" * 68)
    if not os.path.isdir(FIXTURE):
        print(f"BLOKE: fixture dizini yok: {FIXTURE}")
        return 2
    for arac in ("ffmpeg", "ffprobe"):
        if not shutil.which(arac):
            print(f"BLOKE: {arac} bulunamadi (PATH)")
            return 2

    import edit_kopru
    from editor import remotion_v2

    if not os.path.isdir(os.path.join(remotion_v2.STUDIO, "node_modules")):
        print(f"BLOKE: Remotion node_modules yok: {remotion_v2.STUDIO}")
        print("       Cozum: cd app/render-studio && npm ci")
        return 2

    cumleler, manifest = girdi_kur()
    if not cumleler:
        print("BLOKE: fixture'lardan tek sahne bile kurulamadi")
        return 2
    plan_sn = round(sum(c["sure_sn"] for c in cumleler), 2)
    print(f"\n[1/5] GIRDI: {len(cumleler)} sahne, plan suresi {plan_sn} sn, "
          f"{len(manifest['adaylar'])} lisansli aday "
          f"({len(manifest['kapsam_bosluklari'])} bosluk)")

    calisma = os.path.join(DEPO, "cikti", "_smoke_editorv2")
    os.makedirs(calisma, exist_ok=True)
    # ⚠ GERCEK ZINCIR: plan_kur -> plan.uret (beat/gramer/motion/tipografi/
    # ses/QA-on) -> adapter.donustur
    sonuc = edit_kopru.plan_kur(
        cumleler=cumleler, medya_manifest=manifest, olgular=OLGULAR,
        stil=None, cikti_dizin=calisma, is_ayar={"editor_v2": True},
        ambience=os.path.join(FIXTURE, "ambans0.wav"))
    if not sonuc["ok"]:
        print(f"BLOKE: plan kurulamadi -> {sonuc['neden']}")
        for u in sonuc["uyarilar"][:6]:
            print(f"        {u}")
        return 3
    print(f"[2/5] PLAN: profil={sonuc['profil_adi']} QA={sonuc['qa']['durum']} "
          f"(fail={sonuc['qa']['fail']} warn={sonuc['qa']['warn']}) "
          f"render_edilebilir={sonuc['render_edilebilir']}")
    print(f"      elenen medya={len(sonuc['elenen_medya'])} "
          f"kapsam boslugu={len(sonuc['kapsam_bosluklari'])} "
          f"efekt={(sonuc['efekt_kapsami'] or {}).get('sayim')}")
    if not sonuc["render_edilebilir"]:
        print("BLOKE: on-render QA FAIL — render BASLATILMADI (kural geregi)")
        return 4

    # ⚠ GERCEK props hazirligi: varliklari public/ altina kopyalar
    props = remotion_v2.props_hazirla(sonuc["props"], calisma_dizin=calisma)
    kontrol = remotion_v2.dogrula(props)
    print(f"[3/5] ON-RENDER KAPISI: {kontrol['durum']} "
          f"({len(kontrol['sorunlar'])} sorun)")
    if kontrol["durum"] == "FAIL":
        for s in kontrol["sorunlar"][:5]:
            print(f"        FAIL {s.get('kod')}: {s.get('detay')}")
        return 5

    os.makedirs(CIKTI_DIZIN, exist_ok=True)
    video = os.path.join(CIKTI_DIZIN, VIDEO_ADI)
    print(f"[4/5] RENDER basliyor -> {os.path.relpath(video, DEPO)}")
    r = remotion_v2.render(props, video, olcu=(1280, 720), fps=30, crf=22,
                           concurrency=2, zaman_asimi=900)
    if r["rc"] != 0 or not r.get("var_mi"):
        print(f"BLOKE: render basarisiz (rc={r['rc']})")
        print(f"        {str(r.get('stderr') or '')[:400]}")
        return 6
    print(f"      render {r['sure_sn']:.1f} sn surdu")

    # ── DOGRULAMA: ffprobe + kareler ──
    print("[5/5] DOGRULAMA (ffprobe)")
    rapor = {"video": os.path.relpath(video, DEPO),
             "plan_sure_sn": plan_sn, "sahne": len(cumleler),
             "qa": sonuc["qa"], "profil": sonuc["profil_adi"],
             "efekt_kapsami": sonuc["efekt_kapsami"],
             "kapsam_boslugu": sonuc["kapsam_bosluklari"],
             "elenen_medya": sonuc["elenen_medya"],
             "zincir": edit_kopru.sahne_zinciri(sonuc["props"])}
    try:
        pr = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "stream=codec_type,codec_name,width,height,r_frame_rate,"
             "sample_rate,channels", "-show_entries",
             "format=duration,size,bit_rate", "-of", "json", video],
            capture_output=True, text=True, timeout=60)
        veri = json.loads(pr.stdout or "{}")
        rapor["ffprobe"] = veri
        akislar = veri.get("streams") or []
        v = next((a for a in akislar if a.get("codec_type") == "video"), {})
        s = next((a for a in akislar if a.get("codec_type") == "audio"), {})
        bicim = veri.get("format") or {}
        print(f"      codec      : {v.get('codec_name')} / "
              f"{s.get('codec_name') or 'SES YOK'}")
        print(f"      cozunurluk : {v.get('width')}x{v.get('height')} @ "
              f"{v.get('r_frame_rate')}")
        print(f"      sure       : {float(bicim.get('duration') or 0):.3f} sn")
        print(f"      boyut      : {int(bicim.get('size') or 0) / 1e6:.2f} MB")
        print(f"      ses        : {s.get('sample_rate') or '-'} Hz / "
              f"{s.get('channels') or 0} kanal")
    except Exception as e:
        print(f"      ffprobe okunamadi: {type(e).__name__}: {e}")

    kareler = []
    for t in (0, 10, 19):
        kare = os.path.join(CIKTI_DIZIN, f"kare_{t:02d}s.png")
        try:
            subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y",
                            "-ss", str(t), "-i", video, "-frames:v", "1",
                            kare], capture_output=True, timeout=60)
            if os.path.exists(kare) and os.path.getsize(kare) > 1000:
                kareler.append(os.path.relpath(kare, DEPO))
                print(f"      kare {t:>2}s   : "
                      f"{os.path.relpath(kare, DEPO)} "
                      f"({os.path.getsize(kare) / 1000:.0f} KB)")
            else:
                print(f"      kare {t:>2}s   : CIKARILAMADI")
        except Exception as e:
            print(f"      kare {t:>2}s   : {type(e).__name__}")
    rapor["kareler"] = kareler
    rapor["kapsam"] = {
        "gercek_motor": ["editor.plan.uret (beat/gramer/motion/tipografi/ses)",
                         "editor.qa_on on-render QA",
                         "editor.adapter.donustur",
                         "editor.remotion_v2.dogrula + props_hazirla + render",
                         "Remotion VidrushEditorV2 kompozisyonu"],
        "fixture": ["yerel Wikimedia gorselleri (Faz E kosusundan)",
                    "yerel TTS .wav dosyalari", "yerel ambiyans .wav"],
        "kapsam_disi": ["web'den medya bulma (saglayici istegi YOK)",
                        "arastirma/fact-check motoru",
                        "TTS uretimi", "canli /api/generate hatti",
                        "ucretli API"],
    }
    with open(os.path.join(CIKTI_DIZIN, "smoke_rapor.json"), "w",
              encoding="utf-8") as f:
        json.dump(rapor, f, ensure_ascii=False, indent=2)
    print(f"\n      rapor      : "
          f"{os.path.relpath(os.path.join(CIKTI_DIZIN, 'smoke_rapor.json'), DEPO)}")
    print("\n" + "=" * 68)
    print("SONUC: GERCEK Remotion render'i uretildi.")
    print("⚠ Medya WEB'DEN BULUNMADI — yerel fixture kullanildi (bkz. rapor).")
    print("=" * 68)
    return 0


if __name__ == "__main__":
    sys.exit(main())
