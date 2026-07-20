#!/usr/bin/env python3
"""Vidrush Web — uretim hatti (EDIT STILI odakli).
Kullanici referans KARAKTER gorseli + hikaye metni + EDIT STILI verir.
Her edit stili gercek belgesel YT kanallarindan turetildi (tempo, gecis, footage orani,
overlay, art-direction). Sahneler stile gore AI gorsel VEYA gercek footage (YouTube/Pexels)
olur; opsiyonel Magnific ile HD upscale; edge-tts seslendirir; Remotion 720p render eder.
"""
import os
import sys
import json
import time
import shutil
import asyncio
import subprocess

import requests

sys.path.insert(0, "/opt/vidrush")
import uret  # seslendir, altyazi_parcala

import kaynak  # YT/Pexels footage + Magnific upscale

OPENAI_KEY = os.environ.get("OPENAI_KEY", "")
STUDYO = "/opt/vidrush/render-studio"
PUBLIC = os.path.join(STUDYO, "public")
CIKTI_DIR = "/opt/vidrush/webapp/ciktilar"
os.makedirs(CIKTI_DIR, exist_ok=True)

OAI_H = {"Authorization": f"Bearer {OPENAI_KEY}"}


# ─────────────────────────── EDIT STILLERI ───────────────────────────
# Gercek belgesel kanallarindan turetilen 3 profesyonel kurgu profili.
# motion -> Remotion Video.tsx gecis modu; footage_pct -> gercek footage sahne orani;
# overlay -> kinetik baslik yogunlugu; gorsel_ek -> AI art-direction; mag -> Magnific profili.
EDIT_STILLERI = {
    "sinematik-belgesel": {
        "ad": "Sinematik Belgesel",
        "ozet": "BBC Earth / Nat Geo — yavaş, hard-cut, gerçek footage, orkestral",
        "sahne_sn": 7, "kelime": 17, "footage_pct": 85, "overlay": "yok",
        "motion": "sinematik", "mag": "films_n_photography",
        "gorsel_ek": ("cinematic wildlife/nature documentary still, shot on a cinema camera, "
                      "85mm telephoto, shallow depth of field, natural golden-hour light, high "
                      "dynamic range, rich saturated greens and blues, deep shadows, "
                      "photorealistic, absolutely no text, no graphics, no illustration"),
    },
    "anlati-video-essay": {
        "ad": "Anlatı Video-Essay",
        "ozet": "Johnny Harris / Vox Atlas — Ken Burns 2.0 push-in, analog texture, kinetik başlık",
        "sahne_sn": 4, "kelime": 11, "footage_pct": 55, "overlay": "yogun",
        "motion": "anlati", "mag": "films_n_photography",
        "gorsel_ek": ("photojournalistic documentary frame, warm faded film tones, subtle film "
                      "grain and light leaks, tactile analog texture (old paper / wood grain), "
                      "archival photo aesthetic, cinematic depth, muted vintage color grade"),
    },
    "hizli-explainer": {
        "ad": "Hızlı Explainer",
        "ozet": "Vox / Insider — 1.5-3sn hızlı kesme, sürekli kinetik metin, flat grafik",
        "sahne_sn": 2.4, "kelime": 6, "footage_pct": 45, "overlay": "yogun",
        "motion": "hizli", "mag": "standard",
        "gorsel_ek": ("clean flat-design explainer graphic, bright saturated palette, bold "
                      "high-contrast infographic style, crisp vector shapes, solid or white "
                      "background, clear data-visualization aesthetic, modern editorial "
                      "motion-graphics look"),
    },
}
VARSAYILAN_EDIT = "sinematik-belgesel"


def edit_coz(edit_id):
    return EDIT_STILLERI.get(edit_id or VARSAYILAN_EDIT, EDIT_STILLERI[VARSAYILAN_EDIT])


def plan_sistem(prof):
    footage = prof["footage_pct"]
    overlay_kural = (
        "For EACH scene also give overlay: a punchy 2-5 word ALL-CAPS on-screen title in the "
        "ORIGINAL language that reinforces the narration (kinetic caption)."
        if prof["overlay"] != "yok" else
        "Leave overlay as an empty string for every scene (this style uses no on-screen titles)."
    )
    return (
        "You are a professional documentary video editor and scene planner. The user gives a "
        "story/script. The main CHARACTER is provided separately as a REFERENCE IMAGE, so never "
        "describe the character's appearance.\n"
        f"EDIT STYLE: {prof['ad']} — {prof['ozet']}.\n"
        "Rules:\n"
        "1) Detect the language of the story.\n"
        f"2) Split into sequential scenes of about {prof['sahne_sn']} seconds of spoken audio each "
        f"(~{prof['kelime']} words per scene). Use as many scenes as the story needs (HARD MAX 45). "
        "The voiceover fields together cover the whole story in the ORIGINAL language, lightly "
        "smoothed for narration.\n"
        f"3) About {footage}% of scenes must be REAL FOOTAGE: set kaynak='footage' and give "
        "footage_sorgu = a specific ENGLISH stock-footage search query (e.g. 'aerial drone "
        "rainforest canopy 4k', 'busy tokyo street night timelapse'). The remaining scenes set "
        "kaynak='ai' and give scene_prompt = a vivid 16:9 ENGLISH description of the action/place/"
        "camera/mood featuring 'the character'. Never describe the character's colors/face.\n"
        f"4) {overlay_kural}\n"
        "5) Choose a Microsoft Azure neural voice by language: tr->tr-TR-EmelNeural, "
        "en->en-US-AndrewMultilingualNeural, es->es-ES-AlvaroNeural, de->de-DE-ConradNeural, "
        "fr->fr-FR-HenriNeural; else a fitting one.\n"
        "6) Thumbnail: object with text = a punchy 2-5 word hook in the ORIGINAL language ALL CAPS, "
        "and prompt = a dramatic 16:9 scene featuring the character, strong emotion, high contrast.\n"
        "Respond ONLY valid JSON: {\"language\":\"en\",\"voice\":\"...\","
        "\"thumbnail\":{\"text\":\"...\",\"prompt\":\"...\"},"
        "\"scenes\":[{\"n\":1,\"voiceover\":\"...\",\"kaynak\":\"ai|footage\","
        "\"scene_prompt\":\"...\",\"footage_sorgu\":\"...\",\"overlay\":\"...\"}]}"
    )


def plan_uret(story: str, prof: dict) -> dict:
    body = {
        "model": "gpt-4.1-mini",
        "messages": [{"role": "system", "content": plan_sistem(prof)},
                     {"role": "user", "content": story}],
        "response_format": {"type": "json_object"},
        "temperature": 0.7,
    }
    r = requests.post("https://api.openai.com/v1/chat/completions",
                      headers=OAI_H, json=body, timeout=120)
    r.raise_for_status()
    plan = json.loads(r.json()["choices"][0]["message"]["content"])
    scenes = []
    for s in plan.get("scenes", []):
        if not str(s.get("voiceover", "")).strip():
            continue
        kayn = "footage" if str(s.get("kaynak")) == "footage" and str(s.get("footage_sorgu", "")).strip() else "ai"
        if kayn == "ai" and not str(s.get("scene_prompt", "")).strip():
            continue
        scenes.append(s)
    if not scenes:
        raise RuntimeError("Sahne plani bos")
    plan["scenes"] = scenes[:45]
    return plan


def referansli_gorsel(scene_prompt: str, kar_yol: str, hedef: str,
                      stil_prompt: str = "", deneme=3) -> bool:
    """OpenAI images/edits: karakter referansi + art-direction promptu ile sahne uretir."""
    kar_var = bool(kar_yol and os.path.exists(kar_yol))
    prompt = scene_prompt.rstrip(". ") + "."
    if kar_var:
        prompt += (" Keep the SAME character from the reference image (identical face, colors, "
                   "outfit, proportions).")
    if stil_prompt:
        prompt += f" Art direction: {stil_prompt}."
    prompt += " 16:9 cinematic composition. No captions or watermark."

    for d in range(deneme):
        acik = []
        try:
            files = []
            if kar_var:
                fkar = open(kar_yol, "rb"); acik.append(fkar)
                files.append(("image[]", ("character.png", fkar, "image/png")))
            data = {"model": "gpt-image-1", "prompt": prompt, "size": "1536x1024"}
            if files:
                r = requests.post("https://api.openai.com/v1/images/edits",
                                  headers=OAI_H, files=files, data=data, timeout=240)
            else:
                r = requests.post("https://api.openai.com/v1/images/generations",
                                  headers=OAI_H, json={**data}, timeout=240)
            if r.status_code == 429 and d < deneme - 1:
                time.sleep(20); continue
            r.raise_for_status()
            import base64
            b64 = r.json()["data"][0]["b64_json"]
            with open(hedef, "wb") as f:
                f.write(base64.b64decode(b64))
            return True
        except Exception as e:
            print(f"  referansli gorsel hata: {str(e)[:200]}", file=sys.stderr)
            time.sleep(6)
        finally:
            for f in acik:
                try: f.close()
                except Exception: pass
    return False


async def uret(is_adi: str, story: str, kar_yol: str, edit_id: str = VARSAYILAN_EDIT,
               magnific: bool = False, kaynak_modu: str = "yt", ilerle=None) -> dict:
    """Tam hat. edit_id -> EDIT_STILLERI; magnific -> HD upscale; kaynak_modu: yt|guvenli|kapali."""
    def bildir(mesaj, yuzde):
        if ilerle:
            ilerle(mesaj, yuzde)

    prof = edit_coz(edit_id)
    gorsel_ek = prof["gorsel_ek"]
    motion = prof["motion"]
    overlay_stil = prof["overlay"]
    mag_profil = prof["mag"]
    yt_once = kaynak_modu != "guvenli"
    footage_acik = kaynak_modu != "kapali"

    bildir("Hikaye sahnelere bölünüyor...", 4)
    plan = plan_uret(story, prof)
    scenes = plan["scenes"]
    ses = plan.get("voice", "en-US-AndrewMultilingualNeural")

    is_dizini = os.path.join(PUBLIC, "isler", is_adi)
    os.makedirs(is_dizini, exist_ok=True)
    panlar = ["right", "left", "top", "bottom"]
    props_sahneler = []
    toplam = len(scenes)

    for i, s in enumerate(scenes):
        n = s.get("n", i + 1)
        metin = s["voiceover"].strip()
        overlay = str(s.get("overlay", "")).strip() if overlay_stil != "yok" else ""
        yuzde = 8 + int(58 * i / max(1, toplam))
        tur = "image"
        medya = None

        # 1) Footage sahnesi mi?
        if footage_acik and str(s.get("kaynak")) == "footage" and str(s.get("footage_sorgu", "")).strip():
            bildir(f"Sahne {i+1}/{toplam}: footage indiriliyor...", yuzde)
            vyol_full = os.path.join(PUBLIC, "isler", is_adi, f"sahne_{n}.mp4")
            if kaynak.footage_getir(s["footage_sorgu"].strip(), vyol_full, yt_once=yt_once):
                tur = "video"
                medya = f"isler/{is_adi}/sahne_{n}.mp4"

        # 2) AI gorsel (footage yoksa/basarisizsa)
        if medya is None:
            bildir(f"Sahne {i+1}/{toplam}: görsel üretiliyor...", yuzde)
            sp = str(s.get("scene_prompt", "")).strip() or str(s.get("footage_sorgu", "")).strip()
            gyol_full = os.path.join(PUBLIC, "isler", is_adi, f"sahne_{n}.png")
            if not referansli_gorsel(sp, kar_yol, gyol_full, stil_prompt=gorsel_ek):
                print(f"sahne {n} atlandi", file=sys.stderr)
                continue
            if magnific:
                bildir(f"Sahne {i+1}/{toplam}: Magnific HD...", yuzde)
                kaynak.magnific_upscale(gyol_full, optimized_for=mag_profil, scale="2x")
            time.sleep(11)  # OpenAI Tier1 hiz limiti
            tur = "image"
            medya = f"isler/{is_adi}/sahne_{n}.png"

        # 3) Seslendirme + sahne props
        syol = f"isler/{is_adi}/ses_{n}.mp3"
        kelimeler, sure = await uret_seslendir(metin, ses, os.path.join(PUBLIC, syol))
        props_sahneler.append({
            "tur": tur, "medya": medya, "ses": syol, "sure": round(sure, 3),
            "zoom": "in" if i % 2 == 0 else "out", "pan": panlar[i % 4],
            "overlay": overlay,
            "altyazi": uret.altyazi_parcala(kelimeler, sure),
        })

    if not props_sahneler:
        raise RuntimeError("Hiç sahne üretilemedi")

    # Kapak
    bildir("Kapak üretiliyor...", 72)
    kapak_yolu = None
    t = plan.get("thumbnail", {})
    kp = str(t.get("prompt", "")).strip()
    ktext = str(t.get("text", "")).strip()
    if kp:
        if ktext:
            kp += (f". Render the exact text \"{ktext}\" as huge bold baked-in title typography, "
                   "high contrast, professional YouTube thumbnail. No other text.")
        khedef = os.path.join(is_dizini, "kapak.png")
        if referansli_gorsel(kp, kar_yol, khedef, stil_prompt=gorsel_ek):
            if magnific:
                kaynak.magnific_upscale(khedef, optimized_for=mag_profil, scale="2x")
            kapak_yolu = khedef

    # Render
    bildir("Video render ediliyor (birkaç dakika)...", 78)
    props = {"fps": 30, "genislik": 1920, "yukseklik": 1080,
             "gecis": motion, "altyaziStil": overlay_stil, "sahneler": props_sahneler}
    props_yolu = os.path.join(is_dizini, "props.json")
    with open(props_yolu, "w") as f:
        json.dump(props, f, ensure_ascii=False)

    ham = os.path.join(STUDYO, "out", f"{is_adi}.mp4")
    os.makedirs(os.path.join(STUDYO, "out"), exist_ok=True)
    komut = ["npx", "remotion", "render", "src/index.ts", "VidrushVideo", ham,
             f"--props={props_yolu}", "--concurrency=1", "--timeout=120000",
             "--scale=0.6667", "--crf=30"]
    if os.environ.get("REMOTION_BROWSER_EXECUTABLE"):
        komut.append(f"--browser-executable={os.environ['REMOTION_BROWSER_EXECUTABLE']}")
    if os.environ.get("REMOTION_GL"):
        komut.append(f"--gl={os.environ['REMOTION_GL']}")
    sonuc = subprocess.run(komut, cwd=STUDYO, capture_output=True, text=True, timeout=5400)
    if sonuc.returncode != 0:
        print(sonuc.stderr[-2000:], file=sys.stderr)
        raise RuntimeError("Remotion render basarisiz")

    bildir("Tamamlanıyor...", 96)
    son_video = os.path.join(CIKTI_DIR, f"{is_adi}.mp4")
    shutil.copy(ham, son_video)
    son_kapak = None
    if kapak_yolu and os.path.exists(kapak_yolu):
        son_kapak = os.path.join(CIKTI_DIR, f"{is_adi}_kapak.png")
        shutil.copy(kapak_yolu, son_kapak)

    return {"video": f"{is_adi}.mp4",
            "kapak": f"{is_adi}_kapak.png" if son_kapak else None,
            "sure": round(sum(s["sure"] for s in props_sahneler), 1),
            "sahne_sayisi": len(props_sahneler),
            "edit": prof["ad"]}


async def uret_seslendir(metin, ses, yol):
    return await uret.seslendir(metin, ses, yol)
