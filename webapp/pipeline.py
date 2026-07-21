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
import uret as uretmod  # seslendir, altyazi_parcala (DIKKAT: bu dosyada 'uret' adli fonksiyon var,
                        # modulu takma adla al ki golgelenmesin)

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
        "altyazi": "orta", "motion": "sinematik", "mag": "films_n_photography",
        "gorsel_ek": ("cinematic wildlife/nature documentary still, shot on a cinema camera, "
                      "85mm telephoto, shallow depth of field, natural golden-hour light, high "
                      "dynamic range, rich saturated greens and blues, deep shadows, "
                      "photorealistic, absolutely no text, no graphics, no illustration"),
    },
    "anlati-video-essay": {
        "ad": "Anlatı Video-Essay",
        "ozet": "Johnny Harris / Vox Atlas — Ken Burns 2.0 push-in, analog texture, kinetik başlık",
        "sahne_sn": 4, "kelime": 11, "footage_pct": 55, "overlay": "yogun",
        "altyazi": "orta", "motion": "anlati", "mag": "films_n_photography",
        "gorsel_ek": ("photojournalistic documentary frame, warm faded film tones, subtle film "
                      "grain and light leaks, tactile analog texture (old paper / wood grain), "
                      "archival photo aesthetic, cinematic depth, muted vintage color grade"),
    },
    "hizli-explainer": {
        "ad": "Hızlı Explainer",
        "ozet": "Vox / Insider — 1.5-3sn hızlı kesme, sürekli kinetik metin, flat grafik",
        "sahne_sn": 2.4, "kelime": 6, "footage_pct": 45, "overlay": "yogun",
        "altyazi": "yogun", "motion": "hizli", "mag": "standard",
        "gorsel_ek": ("clean flat-design explainer graphic, bright saturated palette, bold "
                      "high-contrast infographic style, crisp vector shapes, solid or white "
                      "background, clear data-visualization aesthetic, modern editorial "
                      "motion-graphics look"),
    },
}
VARSAYILAN_EDIT = "sinematik-belgesel"

# Animasyon (stickman) — Documentary'den AYRI ust-duzey tur. Tamamen AI, gercek footage/Magnific YOK.
ANIMASYON_PROFIL = {
    "ad": "Animasyon (Stickman)",
    "ozet": "xkcd / whiteboard tarzı stickman animasyon; tamamen AI, hızlı ve anlaşılır",
    "sahne_sn": 4, "kelime": 11, "footage_pct": 0, "overlay": "yok",
    "altyazi": "yok", "motion": "sinematik", "mag": None,  # yazi YOK + blur YOK (1080p render hizli)
    "gorsel_ek": ("minimalist stickman line animation, simple black stick-figure characters with "
                  "round heads and thin clean outlines, flat solid pastel background, xkcd / "
                  "whiteboard-explainer style, expressive simple poses, lots of empty space, "
                  "2D vector, playful and clear, absolutely no photorealism, no real footage look"),
}


def profil_coz(tur, edit_id):
    """tur: 'animasyon' -> stickman; 'documentary' -> edit_id ile 3 stilden biri."""
    if tur == "animasyon":
        return ANIMASYON_PROFIL
    return EDIT_STILLERI.get(edit_id or VARSAYILAN_EDIT, EDIT_STILLERI[VARSAYILAN_EDIT])


def karakter_analiz(kar_yol: str) -> str:
    """Referans karakteri gpt-4.1-mini vision ile DETAYLI analiz eder -> character_lock metni.
    Bu metin her AI sahne promptuna KELIMESI KELIMESINE eklenir (gorsel referansla birlikte
    ikili garanti: karakter her sahnede birebir ayni cikar)."""
    if not kar_yol or not os.path.exists(kar_yol):
        return ""
    try:
        import base64
        with open(kar_yol, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        body = {
            "model": "gpt-4.1-mini",
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": (
                    "Describe this reference CHARACTER as a precise, reusable visual lock in ONE "
                    "compact English paragraph (35-60 words): species/type, exact colors, face, "
                    "hair, outfit/markings, body proportions, distinctive features. No scene/"
                    "background, ONLY the character so it can be redrawn IDENTICALLY every time. "
                    "Start with 'The character is'.")},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
            ]}],
            "max_tokens": 200, "temperature": 0.2,
        }
        r = requests.post("https://api.openai.com/v1/chat/completions",
                          headers=OAI_H, json=body, timeout=90)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"  karakter_analiz hata: {str(e)[:160]}", file=sys.stderr)
        return ""


def plan_sistem(prof, hedef_sahne=None, devam=False, onceki_ozet=""):
    footage = prof["footage_pct"]
    mag_var = bool(prof.get("mag"))
    overlay_kural = (
        "For EACH scene also give overlay: a punchy 2-5 word ALL-CAPS on-screen title in the "
        "ORIGINAL language that reinforces the narration (kinetic caption)."
        if prof["overlay"] != "yok" else
        "Leave overlay as an empty string for every scene (this style uses no on-screen titles)."
    )
    # 3) footage karari OTOMATIK: animasyon (footage=0) hic footage kullanmaz.
    if footage <= 0:
        footage_kural = (
            "3) This style uses NO real footage: set kaynak='ai' for EVERY scene. Still give "
            "footage_sorgu as an empty string.")
    else:
        footage_kural = (
            f"3) DECIDE per scene from the content: about {footage}% of scenes that depict a real "
            "place/action better shown with real video must be REAL FOOTAGE (set kaynak='footage' "
            "and footage_sorgu = a specific ENGLISH stock-footage query, e.g. 'aerial drone "
            "rainforest canopy'); scenes centered on the character/abstract ideas set kaynak='ai'.")
    # 7) HD (Magnific) karari OTOMATIK: sadece close-up/kilit detay AI sahnelerinde.
    hd_kural = (
        "7) hd (HD upscale need): set hd=true ONLY for AI scenes that are close-ups or key detail "
        "hero shots that clearly benefit from extra sharpness; set hd=false for all other scenes."
        if mag_var else
        "7) Set hd=false for every scene.")
    hedef = hedef_sahne or 40
    devam_kural = (
        f"\nCONTINUATION: This is a CONTINUING part of a longer video. Story so far (summary): "
        f"\"{onceki_ozet[:600]}\". Do NOT repeat it; continue the narrative naturally from where it "
        "left off, developing NEW points/scenes."
        if devam else "")
    return (
        "You are a professional video editor and scene planner. The user gives a story/script. "
        "The main CHARACTER is provided separately as a REFERENCE IMAGE, so never describe the "
        "character's appearance.\n"
        f"MODE/STYLE: {prof['ad']} — {prof['ozet']}.\n"
        f"{devam_kural}\n"
        "Rules:\n"
        "1) Detect the language of the story.\n"
        f"2) Produce EXACTLY {hedef} sequential scenes, each about {prof['sahne_sn']} seconds of "
        f"spoken audio (~{prof['kelime']} words per scene). If the source text is short, EXPAND it "
        "richly (more detail, examples, vivid narration) to fill the scenes. The voiceover fields "
        "together form continuous narration in the ORIGINAL language.\n"
        "8) Also return \"ozet\": a 2-sentence summary (in the story's language) of what THIS part "
        "covered, for continuity.\n"
        f"{footage_kural} IMPORTANT: give scene_prompt for EVERY scene = a vivid 16:9 ENGLISH "
        "description of the action/place/camera/mood featuring 'the character' (for footage scenes "
        "this is the fallback if no clip is found). Never describe the character's colors/face.\n"
        f"4) {overlay_kural}\n"
        "5) Choose a Microsoft Azure neural voice by language: tr->tr-TR-EmelNeural, "
        "en->en-US-AndrewMultilingualNeural, es->es-ES-AlvaroNeural, de->de-DE-ConradNeural, "
        "fr->fr-FR-HenriNeural; else a fitting one.\n"
        "6) Thumbnail: object with text = a punchy 2-5 word hook in the ORIGINAL language ALL CAPS, "
        "and prompt = a dramatic 16:9 scene featuring the character, strong emotion, high contrast.\n"
        f"{hd_kural}\n"
        "Respond ONLY valid JSON: {\"language\":\"en\",\"voice\":\"...\",\"ozet\":\"...\","
        "\"thumbnail\":{\"text\":\"...\",\"prompt\":\"...\"},"
        "\"scenes\":[{\"n\":1,\"voiceover\":\"...\",\"kaynak\":\"ai|footage\","
        "\"scene_prompt\":\"...\",\"footage_sorgu\":\"...\",\"overlay\":\"...\",\"hd\":false}]}"
    )


def plan_uret(story: str, prof: dict, hedef_sahne=40, devam=False, onceki_ozet="") -> dict:
    body = {
        "model": "gpt-4.1-mini",
        "messages": [{"role": "system",
                      "content": plan_sistem(prof, hedef_sahne, devam, onceki_ozet)},
                     {"role": "user", "content": story}],
        "response_format": {"type": "json_object"},
        "temperature": 0.7,
        "max_tokens": 16000,
    }
    r = requests.post("https://api.openai.com/v1/chat/completions",
                      headers=OAI_H, json=body, timeout=180)
    r.raise_for_status()
    icerik = r.json()["choices"][0]["message"]["content"]
    try:
        plan = json.loads(icerik)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Plan JSON parse edilemedi (truncate?): {str(e)[:120]}")
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
    plan["scenes"] = scenes[:60]   # tek cagri tavani (parca basina)
    return plan


# Uzun video (30 dk'ya kadar): parca parca planla, sahneleri birlestir.
MAKS_SAHNE = 420   # ~30 dk tavani (maliyet/render sinir)


def uzun_plan(story: str, prof: dict, sure_dk: float) -> dict:
    hedef_sahne = int(min(MAKS_SAHNE, max(1, (sure_dk * 60) / prof["sahne_sn"])))
    if hedef_sahne <= 55:
        return plan_uret(story, prof, hedef_sahne=hedef_sahne)
    # cok sahne -> parca parca (her parca ~40 sahne), sureklilik icin ozet aktarilir
    parca = 40
    toplam_plan = None
    ozet = ""
    scenes = []
    while len(scenes) < hedef_sahne:
        kalan = hedef_sahne - len(scenes)
        bu = min(parca, kalan)
        p = plan_uret(story, prof, hedef_sahne=bu, devam=bool(scenes), onceki_ozet=ozet)
        yeni = p.get("scenes", [])
        if not yeni:
            break
        scenes.extend(yeni)
        ozet = (ozet + " " + str(p.get("ozet", ""))).strip()[-1200:]
        if toplam_plan is None:
            toplam_plan = p            # ilk parca voice/thumbnail'i tasir
    if not scenes:
        raise RuntimeError("Sahne plani bos")
    toplam_plan["scenes"] = scenes[:hedef_sahne]
    return toplam_plan


def referansli_gorsel(scene_prompt: str, kar_yol: str, hedef: str,
                      stil_prompt: str = "", kar_kilit: str = "", stil_yol: str = "",
                      deneme=3) -> bool:
    """OpenAI images/edits: karakter referansi (+character_lock metni) + stil gorseli/art-direction.
    kar_kilit: karakter_analiz'den gelen birebir tarif -> her sahnede ayni karakter (ikili garanti)."""
    kar_var = bool(kar_yol and os.path.exists(kar_yol))
    stil_gor = bool(stil_yol and os.path.exists(stil_yol))
    prompt = scene_prompt.rstrip(". ") + "."
    if kar_var:
        prompt += " Keep the EXACT SAME character from the first reference image in every detail."
        if kar_kilit:
            prompt += f" {kar_kilit}"   # character_lock: birebir tarif
    if stil_gor:
        prompt += " Apply the exact ART STYLE/look of the last reference image."
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
            if stil_gor:
                fstil = open(stil_yol, "rb"); acik.append(fstil)
                files.append(("image[]", ("style.png", fstil, "image/png")))
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


async def uret(is_adi: str, story: str, kar_yol: str, stil_yol: str = "",
               mod: str = "documentary", edit_id: str = VARSAYILAN_EDIT,
               sure_dk: float = 2, gecis_acik: bool = True, zoom_acik: bool = True,
               ilerle=None) -> dict:
    """Tam hat. mod: 'animasyon'|'documentary'. stil_yol: referans stil gorseli (opsiyonel).
    sure_dk: hedef sure (maks 30). gecis_acik/zoom_acik: kullanicinin gecis/zoom tercihi.
    Footage (documentary) ve Magnific HD PLANA GORE OTOMATIK."""
    def bildir(mesaj, yuzde):
        if ilerle:
            ilerle(mesaj, yuzde)

    prof = profil_coz(mod, edit_id)
    gorsel_ek = prof["gorsel_ek"]
    motion = prof["motion"] if gecis_acik else "kesme"   # gecis kapali -> sade kesme
    overlay_stil = prof["overlay"]
    altyazi_stil = prof.get("altyazi", "orta")
    mag_profil = prof.get("mag")
    footage_acik = prof.get("footage_pct", 0) > 0
    yt_once = True
    sure_dk = max(0.3, min(30.0, float(sure_dk or 2)))   # 30 dk tavan

    # Karakter DETAY analizi (her sahnede birebir ayni karakter icin ikili garanti)
    kar_kilit = ""
    if kar_yol and os.path.exists(kar_yol):
        bildir("Karakter analiz ediliyor...", 3)
        kar_kilit = karakter_analiz(kar_yol)

    bildir("Hikaye sahnelere bölünüyor...", 5)
    plan = uzun_plan(story, prof, sure_dk)
    scenes = plan["scenes"]
    ses = plan.get("voice", "en-US-AndrewMultilingualNeural")

    is_dizini = os.path.join(PUBLIC, "isler", is_adi)
    os.makedirs(is_dizini, exist_ok=True)
    panlar = ["right", "left", "top", "bottom"]
    props_sahneler = []
    toplam = len(scenes)

    for i, s in enumerate(scenes):
        n = i + 1   # kanonik indeks (modelin 'n'i cakisirsa dosya uzerine yazilmasin)
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
            if not referansli_gorsel(sp, kar_yol, gyol_full, stil_prompt=gorsel_ek,
                                     kar_kilit=kar_kilit, stil_yol=stil_yol):
                print(f"sahne {n} atlandi", file=sys.stderr)
                continue
            if mag_profil and s.get("hd"):   # OTOMATIK: sadece plan HD isaretlediyse
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
            "zoom": ("in" if i % 2 == 0 else "out") if zoom_acik else "yok",
            "pan": panlar[i % 4] if zoom_acik else "yok",
            "overlay": overlay,
            "altyazi": uretmod.altyazi_parcala(kelimeler, sure),
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
        if referansli_gorsel(kp, kar_yol, khedef, stil_prompt=gorsel_ek,
                             kar_kilit=kar_kilit, stil_yol=stil_yol):
            if mag_profil:   # kapak: documentary'de her zaman HD (thumbnail kalitesi kritik)
                kaynak.magnific_upscale(khedef, optimized_for=mag_profil, scale="2x")
            kapak_yolu = khedef

    # Render
    bildir("Video render ediliyor (birkaç dakika)...", 78)
    props = {"fps": 30, "genislik": 1920, "yukseklik": 1080,
             "gecis": motion, "altyaziStil": altyazi_stil, "sahneler": props_sahneler}
    props_yolu = os.path.join(is_dizini, "props.json")
    with open(props_yolu, "w") as f:
        json.dump(props, f, ensure_ascii=False)

    ham = os.path.join(STUDYO, "out", f"{is_adi}.mp4")
    os.makedirs(os.path.join(STUDYO, "out"), exist_ok=True)
    # Full HD 1080p 16:9 (kompozisyon 1920x1080, scale YOK). Web aracinda boyut limiti yok.
    # concurrency ortamdan (Hetzner cok cekirdek): REMOTION_CONCURRENCY.
    konk = os.environ.get("REMOTION_CONCURRENCY", "1")
    komut = ["npx", "remotion", "render", "src/index.ts", "VidrushVideo", ham,
             f"--props={props_yolu}", f"--concurrency={konk}", "--timeout=180000",
             "--crf=21"]
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
    return await uretmod.seslendir(metin, ses, yol)
