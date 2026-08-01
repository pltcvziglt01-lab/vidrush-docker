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

# ═══════════════ KANAL PROFILI (videolar ARASI tutarlilik) ═══════════════
# Sorun: capa (stil kilidi) is dizininde tutuluyordu ve is bitince SILINIYORDU
# -> her video kendi capasini sifirdan uretiyor -> 50 videoluk kanalda stil kayiyor.
# Cozum: profil = KALICI karakter + capa + kilit metinleri. Her videoda ayni referanslar
# enjekte edilir -> tum kanal ayni gorunur. Bu dizin ASLA is temizliginde silinmez.
PROFIL_DIR = "/opt/vidrush/webapp/veri/profiller"
os.makedirs(PROFIL_DIR, exist_ok=True)
_PROFIL_RE = __import__("re").compile(r"^[A-Za-z0-9_-]{1,48}$")


def profil_yolu(pid: str) -> str:
    if not _PROFIL_RE.match(pid or ""):
        raise ValueError("gecersiz profil kimligi")
    return os.path.join(PROFIL_DIR, pid)


def profil_oku(pid: str) -> dict:
    """Profili diskten oku. Yoksa bos dict. Donen: ad, tur, edit, kar_kilit, stil_kilit,
    karakter/capa/stil dosya yollari (varsa)."""
    try:
        d = profil_yolu(pid)
        with open(os.path.join(d, "profil.json"), encoding="utf-8") as f:
            p = json.load(f)
    except Exception:
        return {}
    p["id"] = pid
    for ad, anahtar in (("karakter.png", "karakter_yol"), ("capa.png", "capa_yol"),
                        ("stil.png", "stil_yol")):
        y = os.path.join(profil_yolu(pid), ad)
        p[anahtar] = y if os.path.exists(y) else ""
    return p


def profil_yaz(pid: str, veri: dict):
    d = profil_yolu(pid)
    os.makedirs(d, exist_ok=True)
    mevcut = {}
    try:
        with open(os.path.join(d, "profil.json"), encoding="utf-8") as f:
            mevcut = json.load(f)
    except Exception:
        pass
    mevcut.update({k: v for k, v in veri.items() if v is not None})
    with open(os.path.join(d, "profil.json"), "w", encoding="utf-8") as f:
        json.dump(mevcut, f, ensure_ascii=False, indent=1)


def profil_listele() -> list:
    out = []
    try:
        for pid in sorted(os.listdir(PROFIL_DIR)):
            p = profil_oku(pid)
            if p:
                out.append({"id": pid, "ad": p.get("ad", pid), "tur": p.get("tur", ""),
                            "edit": p.get("edit", ""), "video_sayisi": p.get("video_sayisi", 0),
                            "kilitli": bool(p.get("capa_yol")),
                            "karakter_var": bool(p.get("karakter_yol"))})
    except Exception:
        pass
    return out


def profil_capa_kilitle(pid: str, kaynak_png: str) -> bool:
    """Profilin GORSEL CAPASI'ni sabitle. Bundan sonraki TUM videolar bu kareye kilitlenir
    -> kanal genelinde ayni stil/karakter. Bir kez kilitlenir, elle degistirilene kadar kalir."""
    try:
        if not (kaynak_png and os.path.exists(kaynak_png)):
            return False
        shutil.copy(kaynak_png, os.path.join(profil_yolu(pid), "capa.png"))
        return True
    except Exception as e:
        print(f"  profil capa kilitleme hata: {str(e)[:120]}", file=sys.stderr)
        return False


OAI_H = {"Authorization": f"Bearer {OPENAI_KEY}"}

# ─────────────── GORSEL MODELI (maliyet/kalite dengesi) ───────────────
# 1536x1024 medium ~1584 cikti token. Cikti fiyati: gpt-image-1 $40/1M, gpt-image-2 $30/1M,
# gpt-image-1-mini $8/1M  =>  ~$0.063 / ~$0.048 / ~$0.013 gorsel basina.
# ANIMASYON duz-vektor/stickman: mini yeterli (5x ucuz). DOCUMENTARY foto-gercekci:
# gpt-image-2 (hem su ankinden UCUZ hem karakter tutarliliginda en iyi).
# Env ile ezilebilir: IMAGE_MODEL (tum turler), IMAGE_MODEL_ANIM (sadece animasyon).
GORSEL_MODEL_DOC = os.environ.get("IMAGE_MODEL", "gpt-image-2")
GORSEL_MODEL_ANIM = os.environ.get("IMAGE_MODEL_ANIM", os.environ.get("IMAGE_MODEL", "gpt-image-1-mini"))


def _retry_after_bekle(r, d, taban=6, tavan=60):
    """429/5xx sonrasi ne kadar beklenecek. OpenAI 'Retry-After' basligini VERIRSE ona uy
    (dogru sure), yoksa ustel backoff. Boylece rate-limit'i asmadan tekrar deneriz."""
    ra = r.headers.get("retry-after") or r.headers.get("Retry-After") if r is not None else None
    if ra:
        try:
            return min(tavan, max(2.0, float(ra)) + 1.0)
        except Exception:
            pass
    return min(tavan, taban * (2 ** d))   # 6,12,24,48...


def _kota_hatasi_mi(r) -> bool:
    """Bakiye/harcama-limiti hatasi mi? (beklemek FAYDA ETMEZ — para/limit sorunu).
    OpenAI bunu 400 'billing_limit_user_error' veya 429 'insufficient_quota' ile dondurur."""
    try:
        e = (r.json().get("error", {}) or {})
        imza = f"{e.get('code','')} {e.get('type','')} {e.get('message','')}".lower()
        return any(k in imza for k in ("billing", "quota", "hard limit", "exceeded your current"))
    except Exception:
        return False


BAKIYE_MESAJI = ("OpenAI bakiyesi/harcama limiti doldu. platform.openai.com → Billing'den "
                 "kredi yükleyin veya Limits'ten aylık harcama limitini yükseltin. "
                 "(Hız limiti değil — beklemek çözmez.)")


# ─────────────────────────── GEMINI SAGLAYICI ───────────────────────────
# OpenAI kilitliyken (billing limit) tum hat Gemini uzerinden calisabilsin diye.
# SAGLAYICI=gemini -> planlama + gorsel Gemini'den; openai -> eski davranis.
GEMINI_KEY = os.environ.get("GEMINI_KEY", "")
SAGLAYICI = os.environ.get("AI_SAGLAYICI", "gemini" if GEMINI_KEY else "openai").lower()
GEM_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
GEM_METIN_MODEL = os.environ.get("GEMINI_TEXT_MODEL", "gemini-2.5-flash")
# ORTA kalite + en iyi fiyat: gemini-2.5-flash-image ("Nano Banana") $0.039/gorsel.
# Alternatifler: gemini-3.1-flash-image $0.067 (biraz daha iyi), 3.1-flash-lite $0.034,
# gemini-3-pro-image $0.134 (maksimum). GEMINI_IMAGE_MODEL env ile degistirilir.
GEM_GORSEL_MODEL = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")


def _gem_hata_kontrol(r):
    """Gemini bakiye/kota hatasini BakiyeHatasi'na cevir (retry anlamsiz)."""
    if r.status_code >= 400:
        t = r.text[:400].lower()
        if any(k in t for k in ("quota", "billing", "exceeded", "resource_exhausted")):
            raise BakiyeHatasi("Gemini bakiyesi/kotası doldu — Google AI Studio/Cloud "
                               "hesabına kredi yükleyin veya kotayı yükseltin.")


def gemini_chat(body: dict, timeout: int = 180, deneme: int = 5) -> dict:
    """OpenAI-sekilli 'body' alir, GEMINI'ye sorar, OpenAI-sekilli yanit doner.
    Boylece cagiran kodun (plan_uret, karakter_analiz, stil_analiz) hic degismesi gerekmez."""
    sistem, kullanici, gorseller = "", "", []
    for m in body.get("messages", []):
        ic = m.get("content")
        if isinstance(ic, list):          # vision mesaji (karakter/stil analizi)
            for p in ic:
                if p.get("type") == "text":
                    kullanici += p["text"] + "\n"
                elif p.get("type") == "image_url":
                    u = p["image_url"]["url"]
                    if u.startswith("data:"):
                        gorseller.append(u.split(",", 1)[1])
        elif m.get("role") == "system":
            sistem += str(ic) + "\n"
        else:
            kullanici += str(ic) + "\n"

    parts = [{"text": (sistem + "\n" + kullanici).strip()}]
    for b64 in gorseller:
        parts.append({"inline_data": {"mime_type": "image/png", "data": b64}})
    gcfg = {"temperature": body.get("temperature", 0.7),
            "maxOutputTokens": int(body.get("max_tokens", 8000))}
    if (body.get("response_format") or {}).get("type") == "json_object":
        gcfg["responseMimeType"] = "application/json"

    son = None
    for d in range(deneme):
        try:
            r = requests.post(f"{GEM_BASE}/{GEM_METIN_MODEL}:generateContent",
                              headers={"x-goog-api-key": GEMINI_KEY},
                              json={"contents": [{"parts": parts}], "generationConfig": gcfg},
                              timeout=timeout)
            _gem_hata_kontrol(r)
            if r.status_code in (429, 500, 502, 503, 504):
                son = RuntimeError(f"Gemini {r.status_code}")
                if d < deneme - 1:
                    time.sleep(_retry_after_bekle(r, d)); continue
                r.raise_for_status()
            r.raise_for_status()
            j = r.json()
            metin = ""
            for p in (j.get("candidates") or [{}])[0].get("content", {}).get("parts", []):
                metin += p.get("text", "")
            return {"choices": [{"message": {"content": metin}}]}
        except BakiyeHatasi:
            raise
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            son = e
            if d < deneme - 1:
                time.sleep(min(60, 6 * (2 ** d))); continue
    raise son or RuntimeError("gemini_chat basarisiz")


def gemini_gorsel(prompt: str, ref_yollar: list, hedef: str, deneme: int = 4) -> bool:
    """Gemini ile gorsel uret. ref_yollar: karakter/capa/stil referanslari (coklu referans
    -> karakter tutarliligi). Basarida hedef'e PNG yazar."""
    import base64
    parts = [{"text": prompt}]
    for y in ref_yollar:
        try:
            with open(y, "rb") as f:
                parts.append({"inline_data": {"mime_type": "image/png",
                                              "data": base64.b64encode(f.read()).decode()}})
        except Exception:
            pass
    for d in range(deneme):
        try:
            r = requests.post(f"{GEM_BASE}/{GEM_GORSEL_MODEL}:generateContent",
                              headers={"x-goog-api-key": GEMINI_KEY},
                              json={"contents": [{"parts": parts}]}, timeout=240)
            _gem_hata_kontrol(r)
            if r.status_code in (429, 500, 502, 503, 504) and d < deneme - 1:
                time.sleep(_retry_after_bekle(r, d)); continue
            r.raise_for_status()
            for p in (r.json().get("candidates") or [{}])[0].get("content", {}).get("parts", []):
                veri = (p.get("inline_data") or p.get("inlineData") or {}).get("data")
                if veri:
                    with open(hedef, "wb") as f:
                        f.write(base64.b64decode(veri))
                    return True
            print("  gemini gorsel: yanitta resim yok", file=sys.stderr)
        except BakiyeHatasi:
            raise
        except Exception as e:
            print(f"  gemini gorsel hata: {str(e)[:180]}", file=sys.stderr)
            time.sleep(5)
    return False



def altyazi_ayar_coz(girdi):
    """Altyazi ayari: JSON metni (tam ayar) VEYA sablon adi olabilir. Video.tsx ikisini de anlar.
    Bozuk JSON gelirse sablon adi gibi davranir; hicbiri yoksa varsayilan sablon."""
    g = (girdi or "").strip()
    if not g:
        return "beyaz-kontur"
    if g.startswith("{"):
        try:
            d = json.loads(g)
            return d if isinstance(d, dict) else "beyaz-kontur"
        except Exception:
            return "beyaz-kontur"
    return g


class BakiyeHatasi(RuntimeError):
    """Bakiye/limit hatasi. Retry ANLAMSIZ: hemen yukari firlar ki 40 sahne boyunca
    bosuna denenmesin ve o ana kadar URETILEN sahneler kurtarilabilsin."""
    pass


def oai_chat(body: dict, timeout: int = 180, deneme: int = 6) -> dict:
    """Metin cagrisi — DAYANIKLI. SAGLAYICI=gemini ise Gemini'ye yonlendirir (OpenAI kilitli
    olsa da calisir). 429/5xx/timeout'ta Retry-After'a uyup TEKRAR dener."""
    if SAGLAYICI == "gemini" and GEMINI_KEY:
        return gemini_chat(body, timeout=timeout)
    son_hata = None
    for d in range(deneme):
        try:
            r = requests.post("https://api.openai.com/v1/chat/completions",
                              headers=OAI_H, json=body, timeout=timeout)
            if r.status_code >= 400 and _kota_hatasi_mi(r):
                raise BakiyeHatasi(BAKIYE_MESAJI)   # 400/429 fark etmez: para/limit sorunu
            if r.status_code == 429:
                govde = r.text[:200].replace("\n", " ")
                print(f"  oai_chat 429 ({d+1}/{deneme}): {govde}", file=sys.stderr)
                son_hata = RuntimeError("OpenAI 429 (çok fazla istek — hız limiti)")
                if d < deneme - 1:
                    time.sleep(_retry_after_bekle(r, d)); continue
                raise son_hata
            if r.status_code in (500, 502, 503, 504):
                son_hata = RuntimeError(f"OpenAI {r.status_code}")
                if d < deneme - 1:
                    time.sleep(_retry_after_bekle(r, d)); continue
                r.raise_for_status()
            r.raise_for_status()
            return r.json()
        except (requests.exceptions.Timeout,
                requests.exceptions.ConnectionError,
                requests.exceptions.ChunkedEncodingError) as e:
            son_hata = e
            print(f"  oai_chat retry {d+1}/{deneme}: {str(e)[:120]}", file=sys.stderr)
            if d < deneme - 1:
                time.sleep(min(60, 6 * (2 ** d))); continue
    raise son_hata or RuntimeError("oai_chat basarisiz")


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

# ───────── HİKAYE KANALI (sinematik gerçekçi) — üçüncü üst tür ─────────
# YouTube hikaye kanalı formatı: normal tempolu anlatım, foto-gerçekçi "film karesi" görseller.
# İLK DAKİKALAR (HIKAYE_ACILIS_SN) yoğun hareketli açılış (izleyici tutma), sonrası standart
# Ken Burns + altyazı. Karakter tutarlılığı: çapa referansı + sabit karakter kuralı (aşağıda).
HKANAL_STIL = (
    "cinematic photorealistic film still, shot on 35mm anamorphic cinema lenses, shallow depth "
    "of field, dramatic motivated lighting, moody filmic color grade, subtle film grain, high "
    "dynamic range, realistic skin and fabric texture, professional movie production value, "
    "absolutely no text, no captions, no watermark, no logo, no illustration, no 3D render"
)
# Karakter yuklenmezse: gorunusu SABITLEMEZ (hikayeye gore model secer), ayni kalmasini SART kosar.
HKANAL_VARSAYILAN_KARAKTER = (
    "The recurring main character is the SAME real person in every scene: identical face, age, "
    "hair, build and outfit throughout the whole story — never swap, restyle or replace them"
)
HKANAL_CERCEVE = (
    "Frame like a narrative feature film: vary shot sizes deliberately across scenes (wide "
    "establishing, medium, close-up), keep the main character clearly visible and emotionally "
    "readable, single continuous frame, never split screens or collages"
)
HIKAYE_KANALI_PROFIL = {
    "ad": "Sinematik Hikaye",
    "ozet": "Hikaye kanalı formatı — film karesi görseller, hareketli açılış, altyazı, tutarlı karakter",
    "sahne_sn": float(os.environ.get("HIKAYE_SAHNE_SN", "6")), "kelime": 15,
    "footage_pct": 0, "overlay": "yok",
    "altyazi": "orta", "motion": "hikaye", "mag": "films_n_photography",
    "gorsel_ek": HKANAL_STIL,
    "varsayilan_karakter": HKANAL_VARSAYILAN_KARAKTER,
    "cerceve": HKANAL_CERCEVE,
}
HIKAYE_STILLERI = {"sinematik-hikaye": HIKAYE_KANALI_PROFIL}
VARSAYILAN_HIKAYE = "sinematik-hikaye"
# Açılış süresi (sn): bu süredeki sahneler props'ta "vurgu"=true alır -> Video.tsx yoğun hareket verir
HIKAYE_ACILIS_SN = float(os.environ.get("HIKAYE_ACILIS_SN", "150"))

# Animasyon (stickman) — Documentary'den AYRI ust-duzey tur. Tamamen AI, gercek footage/Magnific YOK.
# ───────── ANIMASYON SANAT YONETIMI (referans video analizinden turetildi) ─────────
# Hedef: elle cizilmis editorial karikatur — murekkep kontur + gouache dolgu + cel golge,
# kagit dokusu, soluk vintage palet, DETAYLI ortamlar, karakter kucuk-orta olcek.
ANIM_STIL = (
    "Hand-drawn editorial cartoon on textured paper: confident dark sepia-brown ink outlines with "
    "organic wobble and varying line weight, flat gouache fills, two-tone cel shading with strong "
    "directional light and deep cast shadows, subtle paper grain and soft offset-print texture. "
    "Muted sun-faded palette drawn from warm ochre, sage green, dusty slate blue, faded brick and "
    "warm cream; desaturated, never neon, glossy or flat digital vector. IMPORTANT — vary which of "
    "these colours DOMINATES this particular scene (one scene ochre-dominant, the next sage-green or "
    "dusty slate-blue or cool grey dominant) so consecutive scenes do not all share the same colour "
    "temperature, while the palette family and drawing style stay identical. Small natural in-world "
    "lettering on signs or labels is welcome. Melancholic, reflective, nostalgic essay-film mood. "
    "No photorealism, no 3D render, no pure white background, no subtitle bar, no watermark, no logo"
)
# Kullanici KARAKTER REFERANSI YUKLEMEZSE kullanilacak varsayilan kahraman tarifi.
# (Referans yuklenirse bu KULLANILMAZ — aksi halde kullanicinin karakteriyle CAKISIRDI.)
ANIM_VARSAYILAN_KARAKTER = (
    "The recurring character is a sophisticated stick figure: plain oval head, minimal face of two "
    "small dot eyes and one faint mouth line, no nose, no hair, pale cream body, thin simple limbs "
    "— identical in every scene"
)
# Kompozisyon/cerceveleme kurali (referansli_gorsel promptuna eklenir)
ANIM_CERCEVE = (
    " FRAMING: obey the shot type and character-scale phrase written in the scene description "
    "exactly; do not pull the camera closer, do not enlarge or centre the character. The ENVIRONMENT "
    "is the main subject. Build a complete believable place: a foreground object cutting into the "
    "frame, a middle ground where the action happens, and a detailed background with true perspective "
    "and receding depth. Objects, furniture and signage must run to all four edges of the image, and "
    "at least one piece of furniture or foreground object must pass in front of the character and "
    "partly overlap it — nothing floats in open space, no blank areas. Keep ONE dominant light source "
    "with a clearly visible direction, casting deep directional shadows that shape the composition."
)

# ═════════ EXPLAINER STILI (2. referans: "Salt" videosu analizinden) ═════════
EXP_STIL = (
    "Clean digital cartoon with a hand-drawn marker feel, identical in every frame. Every shape is "
    "fully closed with a solid black outline; the outer silhouette line one step thicker than "
    "interior lines. Fills are FLAT and saturated, plus exactly ONE darker flat tone of the same hue "
    "as attached shading inside an object's own shape — no cast shadows, no gradients, no glow. "
    "Bright cheerful educational mood, high contrast, generous empty space. "
    "COLOUR: keep a locked core of black outlines, pure white and one flat alert red (used only for "
    "negation or the single thing being singled out); pick three flat theme colours plus one neutral "
    "ground tone that suit the subject and reuse exactly those in every frame. Named flat colours "
    "only, never blended. Vary WHICH of the theme colours fills the background from scene to scene so "
    "consecutive colour scenes do not look alike, while the colour set itself stays fixed. "
    "BACKGROUND is one of exactly two things: a flat colour environment (one straight horizon band "
    "plus a few flat shapes), or a pure white void for concept cards — white edge to edge, no tint, "
    "no panel or card border. "
    "Any lettering is thick hand-lettered marker CAPITALS: upright, uniform stroke, solid fill, black "
    "or alert red only. Full-bleed art. Keep out: gradients, texture, grain, 3D or photographic "
    "rendering, borders, frames, logos, watermarks, subtitle bars"
)
EXP_VARSAYILAN_KARAKTER = (
    "The recurring hero is a simple cartoon everyman about 4.5 heads tall: round head, one flat skin "
    "tone, shaggy hair in one flat dark tone falling just over the eyebrows, two small solid-black "
    "dot eyes set wide apart, one tiny black dash nose, one thin curved mouth line, no eyebrows or "
    "facial shading, mitten hands, plain oval feet. His outfit is always exactly two flat colours "
    "(terracotta-orange upper, dark-brown lower). Identical in every scene — no ageing, no "
    "re-colouring, no added glasses/beard/hat"
)
EXP_CERCEVE = (
    " COMPOSITION: one single focal idea, eye level, no tilt, no vignette, no inner border. "
    "Everything sits on one flat plane — overlap is fine but no vanishing-point perspective, no depth "
    "blur, no cast shadows. DELIVERY CROP: the frame is centre-cropped to 16:9 later, so keep the top "
    "9% and bottom 9% of the canvas free of faces, lettering and arrow tips, and keep a clear 5% "
    "outer margin. In colour scenes the hero is never smaller than 20% of frame height (below that "
    "his locked features stop resolving) and at least 25% of the canvas stays empty flat colour. On a "
    "white card the frame is pure white to ALL FOUR EDGES with no signboard, placard or paper object "
    "— the lettering sits directly on the white, horizontal, never rotated, never overlapping a face "
    "or icon, inside the central 80% of the canvas, with at least 30% left empty white. "
    "SCALE DISCIPLINE: in wide establishing and high overview shots the hero occupies only about "
    "25-35% of the frame height and the environment fills the rest; never let the hero's head and "
    "torso dominate a wide shot. Only medium, close-detail and profile shots may show him large."
)
EXP_SOZLESME = (
    "SCENE PROMPT CONTRACT (educational explainer). Each scene_prompt is ONE English paragraph of "
    "25-45 words, present tense, exactly one action or one concept, and OPENS with either "
    "\"COLOUR SCENE -\" or \"WHITE CARD -\" followed by the shot type / card archetype.\n"
    "FRAME MIX — target roughly two colour scenes per white card. Base rhythm by 1-based index i: "
    "i mod 3 == 0 -> WHITE CARD, otherwise COLOUR SCENE; scene 1 is always a COLOUR SCENE. CONTENT "
    "OVERRIDE beats the rhythm: force a WHITE CARD when the beat's core is a quantity, date, "
    "duration, comparison, sequence/cycle, definition, category set or a rejected option; force a "
    "COLOUR SCENE when the core is a physical action, a place, a moment or a feeling. Never more than "
    "3 colour scenes in a row and never more than 2 white cards in a row.\n"
    "COLOUR SCENE SHOT ROTATION — count only colour scenes; for the a-th one use a mod 6: "
    "1 WIDE ESTABLISHING (full body, flat environment, horizon band, 3-4 background shapes); "
    "2 MEDIUM ACTION (knees-up, one clear action, one prop — cropping is intended); "
    "3 MULTI-CLONE GROUP (3-5 identical copies of the hero around one shared focus object); "
    "4 CLOSE DETAIL (hands and one object filling the frame); "
    "5 SIDE PROFILE MOMENT (hero in profile reacting to one thing entering frame); "
    "0 HIGH FLAT OVERVIEW (small top-down map-like layout of the place). The environment may repeat "
    "across scenes but the SHOT TYPE must change. Colour scenes contain NO on-screen text at all: "
    "max 2 props, max 4 background shapes, environment named in 6 words or fewer.\n"
    "WHITE CARD RULE (critical): the ENTIRE frame is pure white from edge to edge — no ground line, "
    "no horizon, no wall, no coloured background, and absolutely NO signboard, placard, poster, paper "
    "sheet or held object. The words are drawn DIRECTLY onto the white as free-standing lettering. "
    "Never write 'holds a sign' or 'holding a placard'; write that the words float on plain white.\n"
    "WHITE CARD ARCHETYPES — pick by beat content, never the same archetype twice in a row: "
    "GIANT PHRASE (a quantity/date/headline claim as one huge line, tiny hero beside it for scale); "
    "REJECT (a rejected or costly option as one word, with a thick alert-red X placed BESIDE or BELOW "
    "the word — never across the letters — plus one small flat icon); "
    "COMPARE (two flat icons side by side or a simple two-pan balance, one short line under each "
    "side); ANNOTATED SUBJECT (one central object with 2-3 thick black arrows, each arrow ending on a "
    "short label).\n"
    "TEXT BUDGET — the hard rule that keeps lettering legible. Give the wording as DOUBLE-QUOTED "
    "strings inside scene_prompt, phrased as: Hand-lettered bold marker capitals spelled exactly: "
    "\"FIRST LINE\" very large across the upper middle, and \"SECOND LINE\" smaller below. "
    "Limits: at most 2 quoted strings per card, at most 3 words and 14 characters per string, at most "
    "5 words in the whole image. ALL CAPS. Allowed characters ONLY: A-Z, 0-9, space, hyphen, question "
    "mark, percent sign. FORBIDDEN: commas, full stops, apostrophes, ampersands, slashes, plus signs, "
    "superscripts, chemical symbols. Write \"300 000 YEARS\" or \"300K YEARS\", never \"300,000\"; "
    "write \"SODIUM\", never \"Na+\". Never quote a sentence — split a long term over two lines "
    "(\"MINERAL\" / \"INTAKE\"); the voice-over carries the sentence.\n"
    "The character is referred to ONLY as \"the hero\" — never restate appearance, clothing or "
    "colours. Do NOT mention camera, lens, lighting, style, texture or medium in scene_prompt; all "
    "styling lives in the global block.\n"
)

ANIM_SOZLESME = (
    "SCENE PROMPT CONTRACT: every scene_prompt is ONE English paragraph of 45-65 words with "
    "these six slots IN THIS ORDER: (1) SHOT TYPE + camera height, taken verbatim from the "
    "rotation table below; (2) the CHARACTER SCALE PHRASE copied verbatim from the same row "
    "(or 'no character in frame'); (3) the character's single concrete PHYSICAL action and "
    "posture (a body doing a thing — never 'thinking', 'realizing', 'feeling'); (4) the "
    "LOCATION named specifically plus 4-6 concrete objects that truly belong there, named and "
    "split across foreground / middle ground / background (shelves, hand tools, crates, wall "
    "clock, desk lamp, tyres, glass jars, worn floorboards, bins, price tags, cardboard boxes, "
    "shop window); (5) ONE named LIGHT SOURCE and its direction (overhead shop lamp from "
    "above, low window light from the left, bare bulb behind, streetlight from the right); "
    "(6) one EMOTION word.\n"
    "SHOT ROTATION — assign strictly by scene index modulo 8, in order, never the same shot "
    "twice in a row: 1 wide establishing, eye level — 'small full-body figure seen from across "
    "the room, far from camera'; 2 medium, eye level — 'full body from a few steps back, "
    "standing off-centre'; 3 over-the-shoulder, slightly high — 'seen from behind one "
    "shoulder, back turned, upper body only'; 4 low angle looking up — 'small full-body figure "
    "dwarfed beneath towering shelves'; 5 close object detail — 'no character in frame; only "
    "hands or objects'; 6 high angle looking down — 'small figure seen from above, dwarfed by "
    "floor and furniture'; 7 deep aisle or corridor with a vanishing point, eye level — "
    "'distant small figure far down the receding space'; 8 two contrasting objects side by "
    "side on one surface — 'no character in frame' (never split the frame into two places, "
    "never draw two characters).\n"
    "LOCATION VARIETY: name a genuinely different place at least every third scene; never use "
    "the same location for more than two consecutive scenes; use at least ten distinct places "
    "across the video.\n"
    "BANNED WORDS in scene_prompt: empty background, plain background, simple background, "
    "white background, flat colour backdrop, minimalist, negative space, clean, abstract.\n"
    "IDENTITY FIREWALL: never describe the character's face, head, clothing, colour, body "
    "shape, age or gender — identity is locked globally.\n"
    "STYLE FIREWALL: do NOT describe art style, palette, line quality, texture or medium "
    "inside scene_prompt — the global style block already fixes those; repeating them breaks "
    "style consistency between scenes.\n"
    "TEXT: at most one short natural in-world sign, under four words, written as: sign reads "
    "\"NEW & IMPROVED\". Never captions, subtitles, watermarks or logos.\n"
)

# ═════════ HIKAYE / WHAT-IF STILI (3. referans: "You Wake Up 100,000 Years Ago") ═════════
# Imza: SADE duz beyaz stickman + ZENGIN boyali dunya. "Yagli boya tablonun ustune
# yapistirilmis kagit kesik" mantigi + ISIK USTUNLUGU (isik sadece dunyaya duser).
HIK_STIL = (
    "A richly painted 2D story-explainer illustration: a detailed hand-painted world with "
    "ultra-simple flat sticker-like figures placed on top of it, like paper cutouts pasted onto an "
    "oil painting. THE WORLD (everything except the figures) is fully painted and cinematic — "
    "saturated natural colour, visible brushwork, atmospheric haze, real light and real cast shadows, "
    "layered depth from a dark framing foreground to a hazy far vista; the world carries NO black "
    # NOT: burada RENK DAYATILMAZ. Onceden 'pure flat white shapes' yaziyordu ve kullanicinin
    # turuncu karakteriyle CATISIP sahneler arasi beyaz<->turuncu salinimina yol aciyordu.
    # Renk daima karakter kunyesinden gelir; stil sadece CIZIM DILINI tanimlar.
    "outlines and is never flat or vector. THE FIGURES are the exact opposite: flat unshaded shapes "
    "in their own solid colours, drawn with one clean uniform-width black ink line — no shading, no "
    "gradient, no texture, no rim light, no glow, no colour spill, keeping exactly the SAME colours "
    "at noon, at night, in caves and in firelight. LIGHT "
    "SUPREMACY: scene light falls on the world only; figures cast a flat hard-edged single-tone "
    "shadow on the ground but never receive light. All descriptive detail is spent on the "
    "environment, none on the figures. Palette: earth greens, volcanic red, warm gold, dusk blue. "
    "IMPORTANT — shift the DOMINANT colour and time of day from scene to scene (one scene golden "
    "sunset, the next cool green jungle shade, then blue night, then dusty red rock) so consecutive "
    "scenes never share the same colour temperature; the painting style stays identical throughout. "
    "Lettering, when present, is a bold flat uppercase sans-serif graphic overlay or a plain outlined "
    "label box drawn on top of the painting. Avoid: photorealism, 3D render, anime, outlined or "
    "vector-flat scenery, shaded or muscular or textured figures, detailed faces"
)
HIK_VARSAYILAN_KARAKTER = (
    "The hero is one white stick figure: thin uniform black outline, completely white unshaded head "
    "and body, hairline-thin straight arms and legs, small rounded hands and feet, no neck, no "
    "muscles, no body detail. Rounded head with two large white eyes with black pupils, short thick "
    "black eyebrows, one small simple mouth. Messy spiky black hair is the only dark mass on him and "
    "its silhouette never changes. He wears exactly one garment in one flat solid colour with no "
    "folds or texture (ancient era: a plain tan waist wrap; modern era: a plain rust-orange t-shirt "
    "with slate-grey trousers). Nothing else is ever added unless the scene names a held prop. "
    "Emotion comes only from eye size, eyebrow angle and posture. He is always the brightest value "
    "in the frame"
)
HIK_CERCEVE = (
    " FRAMING for a 16:9 centre crop of this 1536x1024 image: the top 9% and bottom 9% get cut away, "
    "so every face, letter, label box and key silhouette stays inside 10%-90% of frame height and 8% "
    "clear of the left and right edges. VALUE LAW (non-negotiable): the painted area directly behind "
    "and around a figure is mid-to-dark and visually calm so the flat white figure reads instantly as "
    "the lightest shape — never place a figure against bright sky, open fire, snow or busy painted "
    "texture. GROUNDING: every figure sits on the ground with a flat hard-edged single-tone shadow "
    "ellipse, never a soft or painted shadow. One focal point per frame placed on a third; horizon on "
    "the upper or lower third; build three depth layers (dark framing foreground, midground subject, "
    "hazy receding background). Keep clear negative space around every figure."
)
HIK_SOZLESME = (
    "SCENE CONTRACT — each scene_prompt is ONE English paragraph of 45-80 words, slots always in this "
    "order: (1) SHOT: the shot-type letter plus the hero's height as a percent of frame height; "
    "(2) WORLD: the painted environment with at least 3 concrete named details, ONE named light "
    "source, time of day and colour mood — spend the entire adjective budget here; (3) FIGURES: only "
    "what the figure(s) DO — pose, gesture and the emotion read from eyes and stance. NEVER state "
    "the character's colour (it is locked globally); close this slot with the fixed clause "
    "\"figures stay flat and unshaded with clean black outlines, unaffected by the scene light\"; "
    "(4) TEXT: either a lettering instruction in double quotes, or "
    "literally \"no text in this image\" — this slot is never empty.\n"
    "Never re-describe the hero's face, hair, clothing, outline, proportions or style — identity is "
    "injected separately and re-describing it causes drift. Prefix the paragraph with ANCIENT or "
    "MODERN when the era could be ambiguous.\n"
    "SHOT TYPES AND SCALE BANDS (bands never overlap; two consecutive scenes must use different "
    "bands): A WIDE ESTABLISHING — hero 10-18%, landscape dominant, deep perspective. B MEDIUM ACTION "
    "— hero 30-50%, mid-gesture, environment fully painted behind. C CLOSE-UP — hero 55-75%, chest "
    "up, eyes on the upper third, the emotional beat. D DRAMATIC LIGHT — hero 30-50%, dark painted "
    "scene lit by one fire, beam or opening; the ENVIRONMENT glows, the figure stays plain flat white "
    "— never glowing, never a silhouette, never orange-tinted. E CROWD — 4-8 figures on three depth "
    "planes, hero nearest and largest (30-50%), middle figures simplified, farthest figures "
    "featureless white silhouettes. F COMPARISON — one painted scene split by a natural divide into "
    "two contrasted situations; both figures identical in build, only posture and surroundings "
    "differ, never a bulky or muscular body; hero 30-50%. G INFOGRAPHIC — painted landscape overlaid "
    "with a drawn path or timeline, 2-3 arrows and at most 2 small outlined label boxes; hero 10-18%. "
    "H SFX BEAT — one big quoted onomatopoeia plus one simple graphic device (red pulse line, impact "
    "rays, dust puff); hero 30-50%.\n"
    "FREQUENCY BUDGET per rolling block of 10 scenes: at least 3 of A/B, at least 1 C, at least 1 D, "
    "at least 1 E, at most 1 F, at most 1 G, exactly 1 H. Narrative need outranks the rota; the "
    "budget is a ceiling and a tie-break, not a carousel. Never use the same type twice in a row.\n"
    "WORLD ROTATION: two consecutive scenes may not share biome AND time of day AND palette; rotate "
    "deliberately (volcanic valley, fern jungle, rock canyon, cave interior, night campfire, dusk "
    "huts and smoke, green oasis, river crossing, overgrown modern ruin) and change the camera angle "
    "every scene.\n"
    "TEXT BUDGET: at most 1 scene in 3 carries lettering. When it does: max 2 lines, each max 3 words "
    "and 14 characters, ALL CAPS, letters A-Z digits 0-9 and spaces only, inside double quotes. No "
    "commas, no punctuation, no plus signs, no chemical symbols, no thousand separators — write "
    "\"100K YEARS\" not \"100,000\". Each infographic label box obeys the same limit. Text never sits "
    "in the top or bottom 9% of the frame.\n"
)

ANIMASYON_PROFIL = {
    "ad": "Animasyon (Anlatı)",
    "ozet": "Elle çizilmiş editorial-karikatür anlatı animasyonu; detaylı ortamlar, sinematik çekimler",
    # MALIYET/TEMPO: referans video ~3.5sn kullaniyor. 5sn = 8dk'da ~96 gorsel (~$1.20/video,
    # 3 video/gun ~5.000 TL/ay). Daha ucuz: ANIM_SAHNE_SN=6 veya 7. Referans temposu: 4.
    "sahne_sn": float(os.environ.get("ANIM_SAHNE_SN", "5")), "kelime": 14,
    "footage_pct": 0, "overlay": "yok",
    "altyazi": "yok", "motion": "sinematik", "mag": None,  # yazi YOK + blur YOK (1080p render hizli)
    "gorsel_ek": ANIM_STIL,
    "varsayilan_karakter": ANIM_VARSAYILAN_KARAKTER,
    "cerceve": ANIM_CERCEVE,
    "sahne_sozlesme": ANIM_SOZLESME,
}

# Explainer profili — ayni iskelet, farkli sanat yonetimi/sozlesme
EXPLAINER_PROFIL = {
    "ad": "Animasyon (Eğitici)",
    "ozet": "Kalın konturlu explainer; canlı renkler + beyaz diyagram kartları, etiket ve oklar",
    "sahne_sn": float(os.environ.get("ANIM_SAHNE_SN", "5")), "kelime": 14,
    "footage_pct": 0, "overlay": "yok",
    "altyazi": "yok", "motion": "sinematik", "mag": None,
    "gorsel_ek": EXP_STIL,
    "varsayilan_karakter": EXP_VARSAYILAN_KARAKTER,
    "cerceve": EXP_CERCEVE,
    "sahne_sozlesme": EXP_SOZLESME,
}

HIKAYE_PROFIL = {
    "ad": "Animasyon (Hikaye)",
    "ozet": "Sade beyaz stickman + zengin boyalı sinematik dünya; macera/what-if anlatımı",
    "sahne_sn": float(os.environ.get("ANIM_SAHNE_SN", "5")), "kelime": 14,
    "footage_pct": 0, "overlay": "yok",
    "altyazi": "yok", "motion": "sinematik", "mag": None,
    "gorsel_ek": HIK_STIL,
    "varsayilan_karakter": HIK_VARSAYILAN_KARAKTER,
    "cerceve": HIK_CERCEVE,
    "sahne_sozlesme": HIK_SOZLESME,
}

# Animasyon ALT-STILLERI (documentary'deki 3 edit stili gibi)
ANIMASYON_STILLERI = {
    "anlati-deneme": ANIMASYON_PROFIL,
    "egitici-explainer": EXPLAINER_PROFIL,
    "hikaye-whatif": HIKAYE_PROFIL,
}
VARSAYILAN_ANIM = "anlati-deneme"


def profil_coz(tur, edit_id):
    """tur: 'animasyon' -> ANIMASYON_STILLERI; 'hikaye' -> HIKAYE_STILLERI; digeri -> EDIT_STILLERI."""
    if tur == "animasyon":
        return ANIMASYON_STILLERI.get(edit_id or VARSAYILAN_ANIM,
                                      ANIMASYON_STILLERI[VARSAYILAN_ANIM])
    if tur == "hikaye":
        return HIKAYE_STILLERI.get(edit_id or VARSAYILAN_HIKAYE,
                                   HIKAYE_STILLERI[VARSAYILAN_HIKAYE])
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
        j = oai_chat(body, timeout=90)
        return j["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"  karakter_analiz hata: {str(e)[:160]}", file=sys.stderr)
        return ""


def palet_olc(img_yol: str, adet: int = 5) -> list:
    """Referans gorselden BASKIN RENKLERI piksel duzeyinde olc (median-cut).
    LLM'e renk TAHMIN ETTIRMEK yerine gercek hex degerleri cikarilir -> 'turuncu karakter
    pembeye dondu' kaymasi kokten kapanir (renk artik kesin sayi olarak prompta girer)."""
    try:
        from PIL import Image
        im = Image.open(img_yol).convert("RGB")
        # kenar %12'yi kirp: arka plan yerine OZNENIN rengini olc
        w, h = im.size
        k = (int(w * 0.12), int(h * 0.12), int(w * 0.88), int(h * 0.88))
        im = im.crop(k).resize((160, 160))
        q = im.quantize(colors=adet, method=Image.MEDIANCUT)
        pal = q.getpalette()[: adet * 3]
        sayim = sorted(q.getcolors() or [], reverse=True)   # [(piksel, indeks), ...]
        out = []
        for piksel, idx in sayim[:adet]:
            r, g, b = pal[idx * 3: idx * 3 + 3]
            out.append({"hex": f"#{r:02X}{g:02X}{b:02X}",
                        "oran": round(piksel / (160 * 160), 3)})
        return out
    except Exception as e:
        print(f"  palet_olc hata: {str(e)[:120]}", file=sys.stderr)
        return []


KUNYE_ALANLARI = ("tur", "govde_rengi", "ikincil_renk", "kafa", "gozler", "sac",
                  "kiyafet", "oranlar", "ayirt_edici")


def _kunye_tek_okuma(img_yol: str, sicaklik: float, paletler: list) -> dict:
    """Referansi TEK vision cagrisiyla yapili kimlik kunyesine cevir."""
    import base64
    with open(img_yol, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    pal_txt = ", ".join(f"{p['hex']} (%{int(p['oran']*100)})" for p in paletler[:5]) or "yok"
    istek = (
        "You are a character model sheet analyst. Describe ONLY the character in this reference "
        "image as a reusable identity card. Return STRICT JSON with exactly these keys: "
        '"tur" (species/type, 3-6 words), "govde_rengi" (main body colour — pick the closest HEX '
        f"from this measured palette: {pal_txt}), "
        '"ikincil_renk" (secondary colour, HEX from the same palette or empty), '
        '"kafa" (head shape, 4-10 words), "gozler" (eyes, 4-10 words), "sac" (hair/fur on head, '
        '4-10 words or "none"), "kiyafet" (clothing/markings, 4-12 words or "none"), '
        '"oranlar" (body proportions, 4-10 words), "ayirt_edici" (single most distinctive '
        'permanent feature, 3-8 words). '
        "RULES: describe ONLY permanent identity. NEVER describe the pose, the camera angle, the "
        "background, the lighting, or any object the character is holding — those are temporary. "
        "If a field is not clearly visible, use an empty string rather than guessing. English only."
    )
    body = {
        "model": "gpt-4.1-mini",
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": istek},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
        ]}],
        "response_format": {"type": "json_object"},
        "max_tokens": 500, "temperature": sicaklik,
    }
    j = oai_chat(body, timeout=90)
    ic = (j.get("choices") or [{}])[0].get("message", {}).get("content") or "{}"
    try:
        return json.loads(ic)
    except Exception:
        return {}


def kimlik_kunyesi(img_yol: str) -> dict:
    """COK ASAMALI KIMLIK ANALIZI (kullanici: '3-4 kere suzgecten gecirsin').
    1) piksel duzeyinde palet olcumu (kod, $0)
    2) bagimsiz vision okumasi (dusuk sicaklik)
    3) IKINCI bagimsiz vision okumasi (yuksek sicaklik, ilkinden habersiz)
    4) KOD UZLASISI: iki okuma ayni diyorsa alan GECERLI, celisiyorsa alan ATILIR
       (celisen alan = modelin uydurdugu alandir; 100 karede 100 farkli uydurulur).
    Donen: {alanlar..., _palet, _guven} — guven dusukse cagiran uyarir."""
    paletler = palet_olc(img_yol)
    a = _kunye_tek_okuma(img_yol, 0.15, paletler)
    b = _kunye_tek_okuma(img_yol, 0.85, paletler)
    if not a and not b:
        return {}
    kunye, onayli, dolu = {}, 0, 0
    for alan in KUNYE_ALANLARI:
        va = str(a.get(alan, "") or "").strip()
        vb = str(b.get(alan, "") or "").strip()
        if not va and not vb:
            continue
        dolu += 1
        # renk alanlarinda birebir, metin alanlarinda kelime ortusmesi arar
        if alan.endswith("rengi") or alan == "ikincil_renk":
            uyum = va.upper() == vb.upper()
        else:
            ka, kb = set(va.lower().split()), set(vb.lower().split())
            uyum = bool(ka & kb) and len(ka & kb) >= max(1, min(len(ka), len(kb)) // 3)
        if uyum:
            kunye[alan] = va or vb
            onayli += 1
        # celisen alan bilerek ATILIR (uydurma alani promptta tekrarlamak zarardir)
    kunye["_palet"] = paletler
    kunye["_guven"] = round(onayli / dolu, 2) if dolu else 0.0
    return kunye


def kunye_metni(k: dict) -> str:
    """Kunyeyi POZITIF, olculu bir kimlik cumlesine cevir (negatif ifade YOK).
    Tasarim ilkesi: yasakli seyi ADLANDIRMA — 'pembe olmasin' demek yerine kesin rengi soyle."""
    if not k:
        return ""
    p = []
    if k.get("tur"):
        p.append(f"a {k['tur']}")
    if k.get("govde_rengi"):
        p.append(f"body colour exactly {k['govde_rengi']}")
    if k.get("ikincil_renk"):
        p.append(f"secondary colour {k['ikincil_renk']}")
    for alan, on in (("kafa", "head"), ("gozler", "eyes"), ("sac", "hair"),
                     ("kiyafet", "wearing"), ("oranlar", "proportions"),
                     ("ayirt_edici", "distinctive")):
        if k.get(alan) and str(k[alan]).lower() not in ("none", "yok"):
            p.append(f"{on}: {k[alan]}")
    return "The main character is " + ", ".join(p) + "." if p else ""


def stil_analiz(stil_yol: str) -> str:
    """Referans stil gorselinden TEK cumlelik kanonik STIL kilidi (gpt-4.1-mini vision).
    Her AI sahne promptuna eklenir -> stil de birebir sabitlenir (karakter kilidinin stil ikizi)."""
    if not stil_yol or not os.path.exists(stil_yol):
        return ""
    try:
        import base64
        with open(stil_yol, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        body = {
            "model": "gpt-4.1-mini",
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": (
                    "Describe ONLY the ART STYLE of this image as a reusable style lock in ONE compact "
                    "English sentence (20-40 words): rendering technique, line/brush quality, color "
                    "palette, shading, texture, level of detail and overall aesthetic. Do NOT describe "
                    "any subject/character/scene content. Start with 'Art style:'.")},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
            ]}],
            "max_tokens": 120, "temperature": 0.2,
        }
        j = oai_chat(body, timeout=90)
        return j["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"  stil_analiz hata: {str(e)[:160]}", file=sys.stderr)
        return ""


# Dil -> dogrulanmis Azure neural ses (model bos/bozuk/halusinasyon voice verirse dile gore dus)
DIL_SES = {
    "tr": "tr-TR-EmelNeural",    "en": "en-US-AndrewMultilingualNeural",
    "es": "es-ES-AlvaroNeural",  "de": "de-DE-ConradNeural",
    "fr": "fr-FR-HenriNeural",   "it": "it-IT-DiegoNeural",
    "pt": "pt-BR-AntonioNeural", "ru": "ru-RU-DmitryNeural",
    "ar": "ar-EG-ShakirNeural",
}
import re as _re
_SES_KALIP = _re.compile(r"^[a-z]{2,3}-[A-Z]{2}-\w+Neural$")


def ses_coz(plan: dict) -> str:
    """plan['voice']'i dogrula; bos/bozuk/dil-uyumsuzsa plan['language']'a gore yerel sesi sec.
    Boylece Turkce metin en-US sesle okunmaz ve halusinasyon voice tum isi oldurmez."""
    dil = str(plan.get("language", "")).strip().lower()[:2]
    ses = str(plan.get("voice", "")).strip()
    if not _SES_KALIP.match(ses):
        return DIL_SES.get(dil, DIL_SES["en"])
    if dil in DIL_SES and not ses.lower().startswith(dil + "-"):
        return DIL_SES[dil]
    return ses


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
    # Profilin kendi sahne SOZLESMESI varsa onu kullan (animasyon alt-stilleri), yoksa genel kural.
    if prof.get("sahne_sozlesme"):
        sahne_kural = prof["sahne_sozlesme"]
    else:
        sahne_kural = (
            "IMPORTANT: give scene_prompt for EVERY scene = a vivid 16:9 ENGLISH description of the "
            "action/place/camera/mood. CHARACTER CONSISTENCY IS THE #1 RULE: the SAME single main "
            "character is the clearly-visible subject of EVERY scene. EVERY scene_prompt MUST contain "
            "the exact phrase 'the main character' as the acting subject performing a clear "
            "pose/action. NEVER introduce a new, different, generic or additional figure. Do NOT "
            "describe the character's colors/face/design (that comes from the reference image); only "
            "describe its POSE/ACTION and the environment, giving EVERY scene a DIFFERENT specific "
            "pose/action/camera angle and setting. Describe ONE single continuous illustration — "
            "never panels, grids or split frames. (For footage scenes this prompt is the fallback if "
            "no clip is found.)\n"
        )
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
        f"2) Produce EXACTLY {hedef} sequential scenes. Every voiceover line must be "
        f"{prof['kelime']}-{prof['kelime'] + 3} words long — this is the TARGET BAND, land inside it; "
        f"the absolute ceiling is {prof['kelime'] + 4} words and lines shorter than {prof['kelime']} "
        f"words are too thin. Count the words before writing the next scene. A "
        f"scene is {prof['sahne_sn']} seconds of speech and a longer line breaks the edit rhythm and "
        "the requested video length. Write short, punchy sentences; split any longer thought across "
        "two consecutive scenes instead of writing one long line. If the source text is short, EXPAND "
        "it by adding MORE SCENES worth of detail — never by making individual lines longer. The "
        "voiceover fields together form continuous narration in the ORIGINAL language.\n"
        "8) Also return \"ozet\": a 2-sentence summary (in the story's language) of what THIS part "
        "covered, for continuity.\n"
        f"{footage_kural} {sahne_kural}"
        f"4) {overlay_kural}\n"
        "5) Choose a Microsoft Azure neural voice by language: tr->tr-TR-EmelNeural, "
        "en->en-US-AndrewMultilingualNeural, es->es-ES-AlvaroNeural, de->de-DE-ConradNeural, "
        "fr->fr-FR-HenriNeural; else a fitting one.\n"
        "6) Thumbnail: object with text = a punchy 2-5 word hook in the ORIGINAL language ALL CAPS, "
        "and prompt = a dramatic 16:9 scene featuring the character, strong emotion, high contrast.\n"
        f"{hd_kural}\n"
        # Gorsel API'leri gercek kisi tasvirini ISIMLE isteyince 400 basiyor (policy).
        # Isimsiz ama iyi tarif edilirse uretiyor -> planlayici ismi degil gorunusu yazsin.
        "REAL PEOPLE: NEVER write a real person's name inside scene_prompt or thumbnail.prompt "
        "(image APIs reject named-likeness requests). Instead describe an era-appropriate figure by "
        "APPEARANCE only: build, outfit, hairstyle, pose, decade styling — without naming or claiming "
        "identity (e.g. 'a slim pop star in a red leather jacket, 1980s stage lighting'). Real names "
        "ARE allowed in footage_sorgu (stock search).\n"
        "Respond ONLY valid JSON: {\"language\":\"en\",\"voice\":\"...\",\"ozet\":\"...\","
        "\"thumbnail\":{\"text\":\"...\",\"prompt\":\"...\"},"
        "\"scenes\":[{\"n\":1,\"voiceover\":\"...\",\"kaynak\":\"ai|footage\","
        "\"scene_prompt\":\"...\",\"footage_sorgu\":\"...\",\"overlay\":\"...\",\"hd\":false}]}"
    )


def plan_uret(story: str, prof: dict, hedef_sahne=40, devam=False, onceki_ozet="") -> dict:
    # max_tokens sahne sayisina gore OLCEKLI. Sabit 16000, dusuk-kademe OpenAI hesabinda
    # TPM (dakikadaki token) limitini asip HER cagriyi 429'a sokuyordu — retry bile kurtarmaz.
    # ~250 token/sahne yeterli; tavan 12000, taban 2000.
    mt = int(min(12000, max(2000, hedef_sahne * 250 + 1200)))
    body = {
        "model": "gpt-4.1-mini",
        "messages": [{"role": "system",
                      "content": plan_sistem(prof, hedef_sahne, devam, onceki_ozet)},
                     {"role": "user", "content": story}],
        "response_format": {"type": "json_object"},
        "temperature": 0.7,
        "max_tokens": mt,
    }
    j = oai_chat(body, timeout=180)
    icerik = (j.get("choices") or [{}])[0].get("message", {}).get("content")
    if not icerik:
        raise RuntimeError("OpenAI plan yanıtı boş (içerik filtresi?) — tekrar deneyin")
    try:
        plan = json.loads(icerik)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Plan JSON parse edilemedi (truncate?): {str(e)[:120]}")
    scenes = []
    for s in plan.get("scenes", []):
        if not str(s.get("voiceover", "")).strip():
            continue
        kayn = "footage" if str(s.get("kaynak")) == "footage" and str(s.get("footage_sorgu", "")).strip() else "ai"
        sp = str(s.get("scene_prompt", "")).strip()
        if kayn == "ai" and not sp:
            continue
        # Karakter-her-sahnede guvenlik agi: model kahramani unuttuysa promptun basina ekle.
        if kayn == "ai" and "main character" not in sp.lower():
            s["scene_prompt"] = "The main character is the large central foreground subject. " + sp
        scenes.append(s)
    if not scenes:
        raise RuntimeError("Sahne plani bos")
    plan["scenes"] = scenes[:60]   # tek cagri tavani (parca basina)
    return plan


# Uzun video (30 dk'ya kadar): parca parca planla, sahneleri birlestir.
MAKS_SAHNE = 620   # ~60 dk hikaye tavani (6 sn/sahne x 600 + pay). Maliyet siniri sure tavaninda.


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
        try:
            p = plan_uret(story, prof, hedef_sahne=bu, devam=bool(scenes), onceki_ozet=ozet)
        except Exception as e:
            # Bir parca yine de basarisizsa (retry'lar tukendi): elde sahne varsa onlarla
            # devam et, yoksa hatayi firlat. Boylece tek parca 30dk isi oldurmez.
            print(f"  uzun_plan parca hata: {str(e)[:160]}", file=sys.stderr)
            if scenes:
                break
            raise
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
    # Hedeften belirgin az sahne uretildiyse (parca basarisiz oldu) sessizce kisa video
    # verme — ust kata bildir.
    if len(scenes) < hedef_sahne * 0.85:
        toplam_plan["_eksik_oran"] = round(len(scenes) / hedef_sahne, 2)
    return toplam_plan


def referansli_gorsel(scene_prompt: str, kar_yol: str, hedef: str,
                      stil_prompt: str = "", kar_kilit: str = "", stil_yol: str = "",
                      capa_yol: str = "", stil_kilit: str = "", yazi_yasak: bool = True,
                      model: str = "", cerceve: str = "", deneme=5) -> bool:
    """OpenAI images/edits: karakter + stil + GORSEL CAPA referanslariyla sahne uretir.
    capa_yol: ilk uretilen sahnenin gorseli -> sonraki sahnelere ek referans olarak verilir,
    boylece karakter VE stil ilk kareye kilitlenir (her sahnede birebir ayni). kar_kilit:
    karakter tarifi, stil_kilit: kanonik stil cumlesi. yazi_yasak: goruntude yazi YASAK
    (animasyon icin kritik; kapakta False)."""
    kar_var = bool(kar_yol and os.path.exists(kar_yol))
    stil_gor = bool(stil_yol and os.path.exists(stil_yol))
    capa_var = bool(capa_yol and os.path.exists(capa_yol) and capa_yol != hedef)
    prompt = scene_prompt.rstrip(". ") + "."
    if kar_var or capa_var:
        # Karakter kilidi — cok kesin dil (kullanici: "her sahnede AYNI olmali")
        prompt += (" CHARACTER IDENTITY LOCK: the reference images define ONLY the character's visual "
                   "IDENTITY — its body and face design, exact colors, proportions and clothing style. "
                   "Keep that identity EXACTLY the same so it is unmistakably the same character in "
                   "every scene. CRITICAL: IGNORE the pose, camera angle, background and any object "
                   "the character happens to be holding in the reference images — those belong to the "
                   "reference only. RE-DRAW the character FRESH for THIS scene: a new pose, new "
                   "action, new expression and new surroundings exactly as described above. Do NOT "
                   "carry over props (for example a cup, a bag or an item in its hand) from the "
                   "reference unless this scene's description explicitly mentions them. Render exactly "
                   "ONE main character; do not add other figures. Follow the shot type and character "
                   "scale stated in the scene description exactly — do not re-frame, do not enlarge "
                   "or centre the character, and never let it fill the frame; the environment carries "
                   "the picture.")
        if kar_kilit:
            prompt += f" Character identity to match: {kar_kilit}"
        prompt += (" COLOUR LOCK: the character's colours are fixed and identical in every scene "
                   "regardless of lighting, time of day or background — the exact same hues at noon, "
                   "at night, in caves and in firelight. If any style instruction suggests a "
                   "different figure colour, the character's own locked colours always win.")
    if stil_gor or capa_var:
        prompt += (" ART-STYLE LOCK: match the EXACT art style of the reference images — identical "
                   "rendering technique, line weight, color palette, shading, texture and level of "
                   "detail. The whole series must look like one consistent piece by the same artist.")
    if stil_kilit:
        prompt += f" Canonical style: {stil_kilit}."
    if stil_prompt:
        prompt += f" Art direction: {stil_prompt}."
    if cerceve:
        prompt += cerceve   # kompozisyon/cerceveleme (ortam basrol, karakter cerceveyi doldurmaz)
    prompt += " 16:9 cinematic composition."
    if yazi_yasak:
        # Kullanici: goruntude MINIMAL yazi sorun degil; istenmeyen sey altyazi bandi/filigran.
        prompt += (" Do NOT add subtitle bars, caption strips, lower-thirds or watermarks. Small "
                   "incidental text that naturally belongs in the scene is fine, but keep it minimal "
                   "and never cover the image with words. Single full-bleed illustration: do NOT split "
                   "the image into panels, grids, frames, borders or comic strips.")

    # GEMINI yolu: ayni referanslarla (karakter + capa + stil) coklu-referans gorsel uretimi
    if SAGLAYICI == "gemini" and GEMINI_KEY:
        refler = [y for y in (kar_yol if kar_var else None,
                              capa_yol if capa_var else None,
                              stil_yol if (stil_gor and not capa_var) else None) if y]
        return gemini_gorsel(prompt, refler, hedef)

    for d in range(deneme):
        acik = []
        try:
            files = []
            # ── TEMIZ CAPA ILKESI (en kritik duzeltme) ──
            # Capa varsa SADECE capa gonderilir; kullanicinin ham referansi ARTIK GONDERILMEZ.
            # Sebep: "elindeki kahve her sahneye tasindi" bir PROMPT degil PIKSEL sorunuydu —
            # her cagriya fincanli goruntu giriyordu. Kopyalanacak fincan olmayinca sorun biter.
            if capa_var:
                fcapa = open(capa_yol, "rb"); acik.append(fcapa)
                files.append(("image[]", ("anchor.png", fcapa, "image/png")))
            else:
                # Capa yoksa (ilk kurulum) ham referans + stil gorseli kullanilir
                if kar_var:
                    fkar = open(kar_yol, "rb"); acik.append(fkar)
                    files.append(("image[]", ("character.png", fkar, "image/png")))
                if stil_gor:
                    fstil = open(stil_yol, "rb"); acik.append(fstil)
                    files.append(("image[]", ("style.png", fstil, "image/png")))
            # quality: OpenAI varsayilani 'auto' (~high, ~$0.28/gorsel). 'medium' (~$0.09)
            # %65-70 ucuz ve 1536x1024'te fark neredeyse gorunmez (ozellikle duz-vektor/
            # stickman animasyonda ayirt edilemez). IMAGE_QUALITY env ile deploysuz degistirilir:
            # low | medium | high | auto
            data = {"model": (model or GORSEL_MODEL_DOC), "prompt": prompt, "size": "1536x1024",
                    "quality": os.environ.get("IMAGE_QUALITY", "medium")}
            if files:
                r = requests.post("https://api.openai.com/v1/images/edits",
                                  headers=OAI_H, files=files, data=data, timeout=240)
            else:
                r = requests.post("https://api.openai.com/v1/images/generations",
                                  headers=OAI_H, json={**data}, timeout=240)
            if r.status_code >= 400 and _kota_hatasi_mi(r):
                raise BakiyeHatasi(BAKIYE_MESAJI)   # bakiye/limit: retry anlamsiz, hemen bildir
            if r.status_code == 429:
                if d < deneme - 1:
                    time.sleep(_retry_after_bekle(r, d)); continue
            r.raise_for_status()
            import base64
            b64 = r.json()["data"][0]["b64_json"]
            with open(hedef, "wb") as f:
                f.write(base64.b64decode(b64))
            return True
        except BakiyeHatasi:
            raise            # bakiye/limit: retry etme, yukari firlat (para bosa gitmesin)
        except Exception as e:
            # HTTP hatasinda API'nin donduğu govdeyi de yaz (400'un GERCEK sebebi orada:
            # policy reddi mi, parametre mi). Yoksa sadece "400 Bad Request" gorup kor kaliyoruz.
            govde = ""
            try:
                govde = f" | yanit: {e.response.text[:300]}"
            except Exception:
                pass
            print(f"  referansli gorsel hata: {str(e)[:200]}{govde}", file=sys.stderr)
            time.sleep(6)
        finally:
            for f in acik:
                try: f.close()
                except Exception: pass
    return False


CAPA_PROMPT = (
    "Full-body character model sheet of the SAME single character shown in the reference image. "
    "Front-facing, standing upright in a relaxed neutral pose, arms down at the sides, "
    "HANDS COMPLETELY OPEN AND EMPTY, entire body visible from head to feet, centred in frame. "
    "Plain flat neutral light-grey studio background, even soft lighting, no scenery, no furniture, "
    "no props, no shadows on the background. Reproduce the character's identity exactly: same "
    "species, same colours, same face, same hair, same clothing, same proportions. "
    "Single character only. No text, no watermark, no border."
)


def capa_uret(ref_yol: str, hedef: str, kimlik: str, stil: str, stil_yol: str = "",
              model: str = "") -> bool:
    """TEMIZ CAPA (A0) uretir: notr poz, ELLER BOS, sade zemin.
    Neden: kullanicinin referansi genelde 'kirli'dir (elinde nesne, ozel poz, dolu arka plan) ve
    her sahneye gonderilince bunlar KOPYALANIR. Bir kez temiz bir kanon uretip onu donduruyoruz;
    tum sahneler bu temiz kareye kilitlenir. Capa ASLA sahne ciktisiyla guncellenmez (aksi halde
    sapma bilesiklenip 'son sahnede karakter degisti' hatasini uretir)."""
    p = CAPA_PROMPT
    if kimlik:
        p += " " + kimlik
    if stil:
        p += f" Art style: {stil}."
    return referansli_gorsel(p, ref_yol, hedef, stil_prompt="", kar_kilit="",
                             stil_yol=stil_yol, capa_yol="", stil_kilit="",
                             yazi_yasak=True, model=model, cerceve="", deneme=3)


async def uret(is_adi: str, story: str, kar_yol: str, stil_yol: str = "",
               mod: str = "documentary", edit_id: str = VARSAYILAN_EDIT,
               sure_dk: float = 2, gecis_acik: bool = True, zoom_acik: bool = True,
               ilerle=None, profil_id: str = "", altyazi_sablon: str = "",
               altyazi_ac: str = "") -> dict:
    """Tam hat. mod: 'animasyon'|'documentary'. stil_yol: referans stil gorseli (opsiyonel).
    sure_dk: hedef sure (hikaye maks 60, digerleri maks 14). gecis_acik/zoom_acik: kullanicinin tercihi.
    profil_id: KANAL PROFILI — verilirse karakter/capa/kilitler profilden gelir ve tum
    videolar ayni gorunur (evergreen kanal tutarliligi). Footage/Magnific plana gore OTOMATIK."""
    def bildir(mesaj, yuzde):
        if ilerle:
            ilerle(mesaj, yuzde)

    # ── KANAL PROFILI: kalici karakter + capa + kilitler (videolar ARASI tutarlilik) ──
    kanal = profil_oku(profil_id) if profil_id else {}
    if kanal:
        mod = kanal.get("tur") or mod
        edit_id = kanal.get("edit") or edit_id

    prof = profil_coz(mod, edit_id)
    gorsel_ek = prof["gorsel_ek"]
    # Kullanici KARAKTER YUKLEMEDIYSE profilin varsayilan kahraman tarifini ekle.
    # Yuklediyse EKLEME — aksi halde onun karakteriyle (or. tilki) CAKISIR.
    if prof.get("varsayilan_karakter") and not (kar_yol and os.path.exists(kar_yol)):
        gorsel_ek = f"{gorsel_ek}. {prof['varsayilan_karakter']}"
    # Kompozisyon/cerceveleme kurali (animasyonda ortam basrol, karakter cerceveyi doldurmaz)
    cerceve_ek = prof.get("cerceve", "")
    motion = prof["motion"] if gecis_acik else "kesme"   # gecis kapali -> sade kesme
    overlay_stil = prof["overlay"]
    # Altyazi: profil varsayilani, ama kullanici acikca ac/kapat diyebilir (animasyonda da).
    # altyazi_ac: "" = profil karari, "1"/"orta"/"yogun" = ac, "0"/"yok" = kapat
    altyazi_stil = prof.get("altyazi", "orta")
    if altyazi_ac in ("0", "yok", "kapali"):
        altyazi_stil = "yok"
    elif altyazi_ac in ("1", "acik", "orta"):
        altyazi_stil = "orta"
    elif altyazi_ac == "yogun":
        altyazi_stil = "yogun"
    if kanal and not altyazi_sablon:
        altyazi_sablon = kanal.get("altyazi_sablon", "")   # kanal profili sablonu hatirlar
    mag_profil = prof.get("mag")
    footage_acik = prof.get("footage_pct", 0) > 0
    # Maliyet/kalite: animasyon (duz vektor) ucuz mini, documentary (foto-gercekci) gpt-image-2
    gorsel_model = GORSEL_MODEL_ANIM if mod == "animasyon" else GORSEL_MODEL_DOC
    yt_once = True
    # Sure tavani: hikaye kanali 60 dk (uzun hikaye formati), diger turler 14 dk.
    # DIKKAT: 60 dk hikaye = ~600 sahne gorseli + 2 vCPU'da ~10-12 saat render.
    tavan_dk = 60.0 if mod == "hikaye" else 14.0
    sure_dk = max(0.3, min(tavan_dk, float(sure_dk or 2)))

    # ── Karakter + STIL kilitleri ──
    # PROFIL VARSA: kayitli referans/kilitler kullanilir -> hem videolar arasi TUTARLILIK,
    # hem her videoda 2 vision cagrisi tasarrufu (daha hizli + daha ucuz).
    kar_kilit = kanal.get("kar_kilit", "") if kanal else ""
    stil_kilit = kanal.get("stil_kilit", "") if kanal else ""
    if kanal:
        # kullanici bu videoda ozel gorsel yuklemediyse profilinkini kullan
        if not (kar_yol and os.path.exists(kar_yol)) and kanal.get("karakter_yol"):
            kar_yol = kanal["karakter_yol"]
        if not (stil_yol and os.path.exists(stil_yol)) and kanal.get("stil_yol"):
            stil_yol = kanal["stil_yol"]
    kunye_guven = None
    if not kar_kilit and kar_yol and os.path.exists(kar_yol):
        # COK ASAMALI ANALIZ: palet olcumu + 2 bagimsiz vision okumasi + kod uzlasisi
        bildir("Karakter derin analiz ediliyor (çok aşamalı)...", 3)
        k = kimlik_kunyesi(kar_yol)
        kar_kilit = kunye_metni(k)
        kunye_guven = k.get("_guven")
        if kunye_guven is not None and kunye_guven < 0.6:
            print(f"  UYARI: kunye guveni dusuk ({kunye_guven}) — referans gorsel net degil",
                  file=sys.stderr)
        if not kar_kilit:      # analiz hic sonuc vermezse eski tek-gecisli yonteme dus
            kar_kilit = karakter_analiz(kar_yol)
    if not stil_kilit and stil_yol and os.path.exists(stil_yol):
        stil_kilit = stil_analiz(stil_yol)
    # Kilitleri profile YAZ (bir kez uretilir, sonraki tum videolarda hazir gelir)
    if kanal and (kar_kilit or stil_kilit):
        try:
            profil_yaz(profil_id, {"kar_kilit": kar_kilit or None,
                                   "stil_kilit": stil_kilit or None,
                                   "kunye_guven": kunye_guven})
        except Exception:
            pass

    bildir("Hikaye sahnelere bölünüyor...", 5)
    plan = uzun_plan(story, prof, sure_dk)
    scenes = plan["scenes"]
    ses = ses_coz(plan)   # dogrulanmis, dile uygun ses (en-US-on-Turkce ve halusinasyon fix)

    is_dizini = os.path.join(PUBLIC, "isler", is_adi)
    os.makedirs(is_dizini, exist_ok=True)
    panlar = ["right", "left", "top", "bottom"]
    props_sahneler = []
    toplam = len(scenes)
    # Gorsel capa: normalde ilk uretilen sahne sonrakilere kilit olur (video ICI tutarlilik).
    # PROFIL KILITLIYSE capa ta bastan gelir -> ILK SAHNE DAHIL her kare kanalin sabit
    # gorunumune kilitlenir (videolar ARASI tutarlilik). Kanal kimligi budur.
    capa_yol = kanal.get("capa_yol", "") if kanal else ""
    capa_profilden = bool(capa_yol)
    # TEMIZ CAPA: kullanici karakter verdiyse ve henuz kanon yoksa, sahnelerden ONCE notr/
    # eller-bos bir kanon karesi uret. Boylece referansin pozu-nesnesi sahnelere BULASMAZ ve
    # tum sahneler ayni temiz kareye kilitlenir. Sahne 1'i capa yapmak sapmayi bilesikliyordu.
    if not capa_yol and kar_yol and os.path.exists(kar_yol):
        bildir("Karakter kanonu (temiz çapa) üretiliyor...", 5)
        kanon = os.path.join(is_dizini, "_kanon.png")
        try:
            if capa_uret(kar_yol, kanon, kar_kilit, stil_kilit, stil_yol, gorsel_model):
                capa_yol = kanon
                capa_profilden = True     # DONDURULDU: sahne ciktisiyla guncellenmez
                if kanal:
                    profil_capa_kilitle(profil_id, kanon)
                    print(f"  profil '{profil_id}' TEMIZ capasi kilitlendi", file=sys.stderr)
        except BakiyeHatasi:
            raise
        except Exception as e:
            print(f"  capa uretilemedi, sahne-1 capasina dusuluyor: {str(e)[:120]}",
                  file=sys.stderr)
    kumulatif_sn = 0.0   # hikaye modu: acilis bolumu (HIKAYE_ACILIS_SN) takibi icin toplam sure

    bakiye_bitti = False   # bakiye/limit doldu mu (elde olanla kurtarma icin)
    ard_arda = 0           # ust uste basarisiz sahne sayaci
    for i, s in enumerate(scenes):
        n = i + 1   # kanonik indeks (modelin 'n'i cakisirsa dosya uzerine yazilmasin)
        metin = str(s.get("voiceover", "")).strip()   # model sayi/null verirse .strip() patlamasin
        if not metin:
            continue
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
            try:
                uretildi = referansli_gorsel(sp, kar_yol, gyol_full, stil_prompt=gorsel_ek,
                                             kar_kilit=kar_kilit, stil_yol=stil_yol,
                                             capa_yol=capa_yol, stil_kilit=stil_kilit,
                                             model=gorsel_model, cerceve=cerceve_ek)
            except BakiyeHatasi:
                # Bakiye/limit doldu: DAHA FAZLA PARA HARCAMA. Elde uretilmis sahneler varsa
                # onlarla videoyu tamamla (odenen para bosa gitmesin), yoksa net hata ver.
                bakiye_bitti = True
                print(f"  BAKIYE bitti — {len(props_sahneler)} uretilmis sahneyle devam",
                      file=sys.stderr)
                break
            if not uretildi:
                ard_arda += 1
                print(f"sahne {n} atlandi", file=sys.stderr)
                # Ust uste basarisizlik: sistem bozuk demektir, para yakmadan elde olanla bitir
                if ard_arda >= 4 and len(props_sahneler) >= 3:
                    print("  ust uste hata -> uretimi durdurup elde olanla tamamla",
                          file=sys.stderr)
                    break
                continue
            ard_arda = 0
            # CAPA yalnizca ANIMASYON + HIKAYE'de: documentary'de ilk sahnenin ICERIGI (or. hayvan,
            # obje) sonraki tum sahnelere kopyalaniyordu (referans gorseldeki icerik bulasmasi).
            # Animasyon/hikayede AYNI KARAKTER her sahnede sart -> capa istenen davranis;
            # documentary'de stil_yol + stil_kilit yeter.
            if not capa_yol and mod in ("animasyon", "hikaye"):   # ilk basarili AI sahne = capa. Magnific ONCESI kucuk kopya al
                capa_yol = os.path.join(is_dizini, "_capa.png")   # (dev upscale'i her sahnede yuklemesin)
                try:
                    shutil.copy(gyol_full, capa_yol)
                except Exception:
                    capa_yol = gyol_full
                # PROFIL VAR ama henuz kilitli degil -> ilk sahneyi kanalin KALICI capasi yap.
                # Bundan sonraki tum videolar bu goruntuye kilitlenir (kanal kimligi sabitlenir).
                if kanal and not capa_profilden:
                    if profil_capa_kilitle(profil_id, capa_yol):
                        capa_profilden = True
                        print(f"  profil '{profil_id}' capasi KILITLENDI", file=sys.stderr)
            if mag_profil and s.get("hd"):   # OTOMATIK: sadece plan HD isaretlediyse
                bildir(f"Sahne {i+1}/{toplam}: Magnific HD...", yuzde)
                kaynak.magnific_upscale(gyol_full, optimized_for=mag_profil, scale="2x")
            # OpenAI hiz limiti beklemesi. 11 sn cok muhafazakardi (96 sahne = 18 dk BOS bekleme).
            # 429 artik Retry-After'a uyup otomatik tekrar deniyor, bu yuzden guvenle dusuruldu.
            time.sleep(float(os.environ.get("GORSEL_BEKLE", "5")))
            tur = "image"
            medya = f"isler/{is_adi}/sahne_{n}.png"

        # 3) Seslendirme + sahne props
        syol = f"isler/{is_adi}/ses_{n}.mp3"
        kelimeler, sure = await uret_seslendir(metin, ses, os.path.join(PUBLIC, syol))
        if kelimeler is None:   # TTS retry'lar tukendi -> bu sahneyi atla, is olmesin
            print(f"sahne {n} sesi uretilemedi, atlandi", file=sys.stderr)
            continue
        props_sahneler.append({
            "tur": tur, "medya": medya, "ses": syol, "sure": round(sure, 3),
            "zoom": ("in" if i % 2 == 0 else "out") if zoom_acik else "yok",
            "pan": panlar[i % 4] if zoom_acik else "yok",
            "overlay": overlay,
            "altyazi": uretmod.altyazi_parcala(kelimeler, sure),
            # Hikaye kanali: acilis dakikalarindaki sahneler yogun hareket alir (Video.tsx "vurgu")
            "vurgu": mod == "hikaye" and kumulatif_sn < HIKAYE_ACILIS_SN,
        })
        kumulatif_sn += sure

    if not props_sahneler:
        # Hicbir sahne yoksa: sebebi bakiye ise NET soyle (kullanici 'neden' bilsin)
        raise RuntimeError(BAKIYE_MESAJI if bakiye_bitti else "Hiç sahne üretilemedi")
    if bakiye_bitti:
        # KURTARMA: odenen sahneler cope gitmesin — kisa da olsa video teslim edilir
        plan["_bakiye_kesildi"] = len(props_sahneler)
    # Render-eksigi: planlanan sahnelerin cogu uretilemezse sessizce kisa video verme
    if toplam and len(props_sahneler) < max(3, toplam * 0.6):
        plan["_render_eksik"] = (len(props_sahneler), toplam)

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
        # Kapak: baslik metni GOMULU olacak (thumbnail) -> yazi_yasak=False (aksi halde ban carpisir)
        if referansli_gorsel(kp, kar_yol, khedef, stil_prompt=gorsel_ek,
                             kar_kilit=kar_kilit, stil_yol=stil_yol, capa_yol=capa_yol,
                             stil_kilit=stil_kilit, yazi_yasak=False,
                             model=GORSEL_MODEL_DOC):   # kapak: her zaman en iyi model
            if mag_profil:   # kapak: documentary'de her zaman HD (thumbnail kalitesi kritik)
                kaynak.magnific_upscale(khedef, optimized_for=mag_profil, scale="2x")
            kapak_yolu = khedef

    # Render
    bildir("Video render ediliyor (birkaç dakika)...", 78)
    # fps 30->24: %20 daha az kare = %20 hizli render (darbogaz Chromium kare uretimi).
    # Statik gorsel + Ken Burns'te 24 fps sinematik durur, fark hissedilmez. VIDEO_FPS env ile geri alinir.
    props = {"fps": int(os.environ.get("VIDEO_FPS", "24")), "genislik": 1920, "yukseklik": 1080,
             "gecis": motion, "altyaziStil": altyazi_stil,
             "altyaziAyar": altyazi_ayar_coz(altyazi_sablon), "sahneler": props_sahneler}
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
             # HD indirme: crf 23 -> 18 (bit hizi ~3 Mbps'ten ~8-10 Mbps'e cikar, YouTube 1080p
             # onerisi 8 Mbps). Render suresine etkisi kucuk (darbogaz Chromium kare uretimi).
             # jpeg-quality 100 = kare yakalama kaybi yok.
             f"--crf={os.environ.get('RENDER_CRF','18')}", "--x264-preset=faster",
             # 100->90: kare yakalama belirgin hizlanir, gozle gorulur kalite farki yok
             "--jpeg-quality=90"]
    if os.environ.get("REMOTION_BROWSER_EXECUTABLE"):
        komut.append(f"--browser-executable={os.environ['REMOTION_BROWSER_EXECUTABLE']}")
    if os.environ.get("REMOTION_GL"):
        komut.append(f"--gl={os.environ['REMOTION_GL']}")
    # Render suresi videoya gore olcekli: min 30dk, video dakikasi basina ~12dk duvar.
    # Tavan 13 saat: 60 dk hikaye 2 vCPU'da ~10-12 saat surer; eski 5 saat tavani
    # 14 dk'lik videoda bile kil payiydi (2s45d gercek olcum), uzunu kesinlikle olduruyordu.
    render_timeout = int(min(46800, max(1800, sure_dk * 720)))
    try:
        sonuc = subprocess.run(komut, cwd=STUDYO, capture_output=True, text=True,
                               timeout=render_timeout)
    except subprocess.TimeoutExpired as e:
        # yetim remotion/chromium cocuklarini temizle ki kuyruk tikanmasin
        try:
            subprocess.run(["pkill", "-9", "-f", "remotion"], timeout=20)
            subprocess.run(["pkill", "-9", "-f", "chrome"], timeout=20)
        except Exception:
            pass
        cikti = (e.stderr or b"")
        if isinstance(cikti, bytes):
            cikti = cikti.decode("utf-8", "ignore")
        print(cikti[-2000:], file=sys.stderr)
        raise RuntimeError(f"Render zaman aşımına uğradı ({render_timeout//60} dk). "
                           "Daha kısa süre deneyin.")
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

    sonuc = {"video": f"{is_adi}.mp4",
             "kapak": f"{is_adi}_kapak.png" if son_kapak else None,
             "sure": round(sum(s["sure"] for s in props_sahneler), 1),
             "sahne_sayisi": len(props_sahneler),
             "edit": prof["ad"]}
    uyarilar = []
    if plan.get("_eksik_oran"):
        uyarilar.append(f"İçerik planı beklenenden kısa çıktı (~%{int(plan['_eksik_oran']*100)}).")
    if plan.get("_render_eksik"):
        u, p = plan["_render_eksik"]
        uyarilar.append(f"Planlanan {p} sahnenin {u} tanesi üretilebildi; video beklenenden kısa olabilir.")
    if plan.get("_bakiye_kesildi"):
        uyarilar.append(f"OpenAI bakiyesi/limiti üretim sırasında doldu — {plan['_bakiye_kesildi']} "
                        "sahne kurtarıldı ve videoya dönüştürüldü (harcanan para boşa gitmedi). "
                        "Kredi yükleyip tam sürümü tekrar üretebilirsiniz.")
    if uyarilar:
        sonuc["uyari"] = " ".join(uyarilar) + " Metni sadeleştirip tekrar deneyebilirsiniz."
    return sonuc


async def uret_seslendir(metin, ses, yol, deneme=3):
    """DAYANIKLI TTS. edge-tts agdan cekilir; gecici hata/bos metin olursa TEKRAR dener.
    Basarisiz ya da bos/bozuk ses dosyasi -> (None, None) doner ki cagiran o sahneyi
    ATLASIN (tek TTS hicgirigi tum 30dk isi oldurmesin). Basarida (kelimeler, sure)."""
    metin = (metin or "").strip()
    if not metin:
        return None, None
    son = None
    for d in range(deneme):
        try:
            # asyncio.wait_for: yari-acik TCP baglantisi edge-tts stream'ini SONSUZA dek
            # bekletebilir (retry sadece exception'da calisir). 120s tavan -> hata firlar ->
            # retry devreye girer -> tum kuyruk sonsuza kilitlenmez.
            kelimeler, sure = await asyncio.wait_for(
                uretmod.seslendir(metin, ses, yol), timeout=120)
            # Remotion'un <Audio> cozebilmesi icin dosya gercekten yazilmis olmali
            if os.path.exists(yol) and os.path.getsize(yol) > 1024:
                return kelimeler, sure
            son = RuntimeError("bos/kucuk ses dosyasi")
        except Exception as e:
            son = e
            print(f"  seslendir retry {d+1}/{deneme}: {str(e)[:120]}", file=sys.stderr)
        await asyncio.sleep(3 * (d + 1))
    print(f"  seslendir BASARISIZ (sahne atlanacak): {str(son)[:160]}", file=sys.stderr)
    return None, None
