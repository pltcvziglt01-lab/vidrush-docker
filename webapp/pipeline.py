#!/usr/bin/env python3
"""Vidrush Web — uretim hatti.
Referans karakter + referans stil GORSELI kullanarak (OpenAI image edits/reference)
her sahneyi tutarli uretir; edge-tts seslendirir; Remotion ile 720p render eder.
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
import uret  # seslendir, altyazi_parcala, render mantigi

OPENAI_KEY = os.environ.get("OPENAI_KEY", "")
STUDYO = "/opt/vidrush/render-studio"
PUBLIC = os.path.join(STUDYO, "public")
CIKTI_DIR = "/opt/vidrush/webapp/ciktilar"       # servis edilen videolar
os.makedirs(CIKTI_DIR, exist_ok=True)

OAI_H = {"Authorization": f"Bearer {OPENAI_KEY}"}

PLAN_SISTEM = (
 "You are a video scene planner. The user gives a story/script. The visual CHARACTER and "
 "ART STYLE are provided separately as REFERENCE IMAGES, so do NOT describe the character's "
 "appearance or the art style — focus each scene on setting, action, camera and mood.\n"
 "Rules: 1) Detect the language of the story. 2) Split into sequential scenes of ~5 seconds of "
 "spoken audio each (~10-15 words per scene). Use as many scenes as the story needs "
 "(1000 chars ~ 14-18 scenes; HARD MAX 40). The voiceover fields together cover the whole story "
 "in the ORIGINAL language, lightly smoothed for narration. 3) For each scene write scene_prompt "
 "in ENGLISH: a vivid 16:9 description of WHAT HAPPENS (place, action, camera angle, lighting, "
 "mood). The main character from the reference image should be the focus of most scenes; refer to "
 "it simply as 'the character'. Never describe its colors/face/outfit (the reference image "
 "defines that). 4) Choose a Microsoft Azure neural voice by language: tr->tr-TR-EmelNeural, "
 "en->en-US-AndrewMultilingualNeural, es->es-ES-AlvaroNeural, de->de-DE-ConradNeural, "
 "fr->fr-FR-HenriNeural; else a fitting one. 5) Thumbnail: object with text = a punchy 2-5 word "
 "hook in the ORIGINAL language ALL CAPS, and prompt = a dramatic 16:9 scene featuring the "
 "character, strong emotion, high contrast, clean background. "
 "Respond ONLY valid JSON: {\"language\":\"en\",\"voice\":\"...\","
 "\"thumbnail\":{\"text\":\"...\",\"prompt\":\"...\"},"
 "\"scenes\":[{\"n\":1,\"voiceover\":\"...\",\"scene_prompt\":\"...\"}]}"
)


def plan_uret(story: str) -> dict:
    body = {
        "model": "gpt-4.1-mini",
        "messages": [{"role": "system", "content": PLAN_SISTEM},
                     {"role": "user", "content": story}],
        "response_format": {"type": "json_object"},
        "temperature": 0.7,
    }
    r = requests.post("https://api.openai.com/v1/chat/completions",
                      headers=OAI_H, json=body, timeout=120)
    r.raise_for_status()
    plan = json.loads(r.json()["choices"][0]["message"]["content"])
    scenes = [s for s in plan.get("scenes", [])
              if str(s.get("voiceover", "")).strip() and str(s.get("scene_prompt", "")).strip()]
    if not scenes:
        raise RuntimeError("Sahne plani bos")
    plan["scenes"] = scenes[:40]
    return plan


def referansli_gorsel(scene_prompt: str, kar_yol: str, stil_yol: str,
                      hedef: str, deneme=3) -> bool:
    """OpenAI images/edits: karakter + stil referansiyla sahne uretir."""
    prompt = (scene_prompt +
              ". Keep the SAME character from the first reference image (identical face, colors, "
              "outfit, proportions). Apply the exact ART STYLE of the second reference image. "
              "16:9 cinematic composition. No text or captions.")
    for d in range(deneme):
        acik = []
        try:
            fkar = open(kar_yol, "rb"); acik.append(fkar)
            files = [("image[]", ("character.png", fkar, "image/png"))]
            if stil_yol and os.path.exists(stil_yol):
                fstil = open(stil_yol, "rb"); acik.append(fstil)
                files.append(("image[]", ("style.png", fstil, "image/png")))
            data = {"model": "gpt-image-1", "prompt": prompt, "size": "1536x1024"}
            r = requests.post("https://api.openai.com/v1/images/edits",
                              headers=OAI_H, files=files, data=data, timeout=240)
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


async def uret(is_adi: str, story: str, kar_yol: str, stil_yol: str,
               ilerle=None) -> dict:
    """Tam hat. ilerle(callback) durum bildirimi icin."""
    def bildir(mesaj, yuzde):
        if ilerle:
            ilerle(mesaj, yuzde)

    bildir("Hikaye sahnelere bolunuyor...", 5)
    plan = plan_uret(story)
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
        sp = s["scene_prompt"].strip()
        bildir(f"Sahne {i+1}/{toplam} gorseli uretiliyor...", 10 + int(60 * i / max(1, toplam)))
        gyol = f"isler/{is_adi}/sahne_{n}.png"
        if not referansli_gorsel(sp, kar_yol, stil_yol, os.path.join(PUBLIC, gyol)):
            print(f"sahne {n} atlandi", file=sys.stderr)
            continue
        time.sleep(11)  # OpenAI Tier1 hiz limiti
        syol = f"isler/{is_adi}/ses_{n}.mp3"
        kelimeler, sure = await uret_seslendir(metin, ses, os.path.join(PUBLIC, syol))
        props_sahneler.append({
            "tur": "image", "medya": gyol, "ses": syol, "sure": round(sure, 3),
            "zoom": "in" if i % 2 == 0 else "out", "pan": panlar[i % 4],
            "altyazi": uret.altyazi_parcala(kelimeler, sure),
        })

    if not props_sahneler:
        raise RuntimeError("Hic sahne uretilemedi")

    # Kapak
    bildir("Kapak uretiliyor...", 72)
    kapak_yolu = None
    t = plan.get("thumbnail", {})
    kp = str(t.get("prompt", "")).strip()
    ktext = str(t.get("text", "")).strip()
    if kp:
        if ktext:
            kp += (f". Render the exact text \"{ktext}\" as huge bold baked-in title typography, "
                   "high contrast, professional YouTube thumbnail. No other text.")
        khedef = os.path.join(is_dizini, "kapak.png")
        if referansli_gorsel(kp, kar_yol, stil_yol, khedef):
            kapak_yolu = khedef

    # Render
    bildir("Video render ediliyor (birkaç dakika)...", 78)
    props = {"fps": 30, "genislik": 1920, "yukseklik": 1080, "sahneler": props_sahneler}
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

    bildir("Tamamlaniyor...", 96)
    son_video = os.path.join(CIKTI_DIR, f"{is_adi}.mp4")
    shutil.copy(ham, son_video)
    son_kapak = None
    if kapak_yolu and os.path.exists(kapak_yolu):
        son_kapak = os.path.join(CIKTI_DIR, f"{is_adi}_kapak.png")
        shutil.copy(kapak_yolu, son_kapak)

    return {"video": f"{is_adi}.mp4",
            "kapak": f"{is_adi}_kapak.png" if son_kapak else None,
            "sure": round(sum(s["sure"] for s in props_sahneler), 1),
            "sahne_sayisi": len(props_sahneler)}


async def uret_seslendir(metin, ses, yol):
    return await uret.seslendir(metin, ses, yol)
