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
import threading
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

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
    # 6->8 sn: hikaye kanallarinda sakin tempo normal; %25 daha az gorsel = daha hizli + ucuz
    "sahne_sn": float(os.environ.get("HIKAYE_SAHNE_SN", "8")), "kelime": 19,
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
# ═══ DESTEK OGESI KURALI (tum animasyon stillerinde ZORUNLU) ═══
# Kullanici geri bildirimi: "bir sahne sadece karakterin on planda oldugu duz bir gorsel olarak
# gorunmemeli; ana karakter bir sey ANLATIYOR, yan destekleyici ogeler de kullanilmali."
# Yani her kare, o an anlatilan seyi GOSTEREN somut bir gorsel arac icermeli.
DESTEK_PLANLAYICI = (
    "SUPPORTING ELEMENT — MANDATORY IN EVERY SCENE. The character is NARRATING something, so each "
    "frame must SHOW what is being said, not just show the character. Besides the character and the "
    "setting, every scene_prompt must name at least ONE concrete supporting visual device that "
    "illustrates the exact point of that line, and must state how the character INTERACTS with it "
    "(holding, pointing at, leaning over, building, dropping, comparing, reacting to). Choose the "
    "device from: a real object or tool; a map, chart, timeline, diagram or plan; a document, letter "
    "or book; secondary figures (a crowd, soldiers, workers, a listener); a visual metaphor made of "
    "objects (scales, a growing plant, stacked coins, a cracked wall); a before/after or two-object "
    "comparison; an environmental event (fire, smoke, rain, collapse, dust, explosion). Vary the "
    "device from scene to scene — never repeat the same one twice in a row. A scene that is only a "
    "character standing in front of scenery is INVALID and must be rewritten.\n"
)
# ═══ KARE CESITLILIGI — KARAKTERSIZ KARELER ZORUNLU ═══
# Kullanici referansi (arac bakim kanali): 4 karenin 3'unde KARAKTER YOK — patlatilmis
# teknik sema, yazi karti, makro detay. Ritim: sema -> yazi -> sahne -> makro.
# Onceki halimiz her kareye karakter koyuyordu -> monoton "karakter + arka plan" akisi.
KARE_CESITLILIGI = (
    "FRAME VARIETY — THE CHARACTER IS NOT IN EVERY SCENE. This is a narrated explainer, so the "
    "pictures must alternate between the narrator and the SUBJECT being explained. Aim for roughly "
    "half the scenes WITHOUT any character. Choose each scene's frame type from this set and never "
    "use the same type twice in a row:\n"
    "  HERO ACTION — the character physically doing/handling something in a real setting.\n"
    "  OBJECT MACRO — extreme close-up of the object being discussed, filling the frame, NO "
    "character (write 'no character in frame').\n"
    "  HANDS ONLY — extreme close-up of two hands performing the exchange or action (handing over "
    "an envelope, passing a key, gripping a tool), cropped at the wrists, plain background, no "
    "faces and no bodies.\n"
    "  MAP ROUTE — a simple outline map of the relevant place with 2-3 labelled dots and a dashed "
    "route line between them, plus one small vehicle or object travelling along it; NO character "
    "figure (a tiny driver inside a vehicle is allowed).\n"
    "  INNER VOICE — the character alone in a wide atmospheric setting with 3-4 short thought "
    "fragments floating in the air around its head as small hand-written words, showing what it is "
    "feeling at that moment.\n"
    "  EXPLODED VIEW — the object taken apart, its parts floating separated and labelled by shape, "
    "on a clean plain background, NO character.\n"
    "  CONCEPT CARD — a very short phrase on a clean plain background, NO character.\n"
    "  COMPARISON — two objects or two states side by side (old vs new, right vs wrong), NO "
    "character.\n"
    "  PROCESS STEP — hands (or the character's hands only) performing one step on the object.\n"
    "  WIDE CONTEXT — the character small inside the full place, showing where this happens.\n"
    "When the narration is about a THING (how it works, what breaks, what to look for), prefer the "
    "character-free types; use HERO ACTION when the narration is about a person doing or deciding "
    "something. Scenes written as 'no character in frame' must not contain any figure at all.\n"
)

DESTEK_GORSEL = (
    " STORYTELLING FRAME: this is a narrated explainer picture, so the frame must SHOW the idea, not "
    "just the character. Besides the character and the background, clearly render the supporting "
    "element named in the scene text — the object, map, diagram, document, crowd, metaphor or event "
    "— large enough to read at a glance, and show the character physically engaging with it. A flat "
    "picture of a character simply standing in front of scenery is not acceptable."
)

# ── VERI KARTI (567 referans karesinin EN GUCLU bulgusu) ──
# Aussie Money With Bruce'un 28 karesinin ~24'unde tutulan tabela / laptop ekrani / fiyat
# etiketi var ve ustunde anlatilan cumlenin TAM SAYISI yazili. Karakter hicbir zaman
# "sadece anlatmiyor", sayiyi GOSTERIYOR. Bizim eski kuralimiz "destekleyici oge olsun"
# diyordu ama "anlatilan sayiyi gorunur bir yuzeye yaz" DEMIYORDU.
VERI_KARTI_PLAN = (
    "DATA CARD — apply to every scene whose narration contains a concrete fact: a number, price, "
    "percentage, year, count, duration or a two-way comparison. In that scene you MUST name a "
    "physical surface inside the world that displays that exact fact — a held placard, a shop price "
    "tag, a laptop or phone screen, a TV, a noticeboard, a billboard, a printed letter, a menu or a "
    "hand-drawn chart — and write the words to be shown in double quotes. Do not paraphrase the "
    "number; use the same figure the narration says. If the narration compares two things, show "
    "both values on the same surface. If a scene's line carries no concrete fact, no data card is "
    "needed and you must not invent one.\n"
)
VERI_KARTI_GORSEL = (
    " DATA CARD: if the scene text puts words or figures on a surface (placard, screen, tag, board, "
    "chart), render that surface large, front-facing and fully legible, and place it on the opposite "
    "side of the frame from the character so the two do not overlap — character on one side, the "
    "information on the other. Draw the surface and any chart in the SAME medium and style as the "
    "rest of the picture. Spell the words exactly as written, ALL CAPS, no extra text invented."
)
# Marka guvenligi: Bruce gercek logolar kullaniyor (Netflix/Disney+). Biz KULLANMAYACAGIZ.
MARKA_YASAK = (
    " Never draw real company logos, brand marks, product names or recognisable trade dress; "
    "invent neutral generic equivalents instead."
)
# Iki BAGIMSIZ kanal (Paint Explainer + Simple Explainer) ayni seyi yapiyor: bir bolum boyunca
# AYNI mekan tekrar kullaniliyor, sadece aci/aksiyon degisiyor. Tesadufi degil, kural.
MEKAN_SUREKLILIGI = (
    "SETTING CONTINUITY: group your scenes into short runs of 2-4 consecutive scenes that share the "
    "SAME named location, and describe that location with the same concrete details each time, "
    "changing only the camera angle, the distance and what happens. Move to a new location only when "
    "the narration genuinely moves on. A video that teleports to a brand-new place every single "
    "scene feels incoherent; repeating a place makes it feel like a real world.\n"
)


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
    + KARE_CESITLILIGI + DESTEK_PLANLAYICI + VERI_KARTI_PLAN + MEKAN_SUREKLILIGI
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
    + KARE_CESITLILIGI + DESTEK_PLANLAYICI + VERI_KARTI_PLAN + MEKAN_SUREKLILIGI
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
    "RULE ZERO — READ FIRST: this is a narrated explainer, not a character showcase. AT LEAST "
    "40% OF ALL SCENES YOU WRITE MUST CONTAIN NO CHARACTER AT ALL (shot types G, I, J, K below) "
    "and must literally contain the words 'no character in frame'. Before you finish, COUNT "
    "your scenes: if fewer than 40% are character-free, rewrite the weakest character scenes as "
    "object macros, hands-only close-ups, maps or diagrams. A video where every frame shows the "
    "character standing in a landscape is the FAILURE MODE we are eliminating.\n"
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
    "differ, never a bulky or muscular body; hero 30-50%. "
    "G INFOGRAPHIC — NO CHARACTER IN FRAME: a drawn path, timeline or diagram over a painted or plain "
    "ground, 2-3 arrows and at most 2 short outlined label boxes. "
    "H SFX BEAT — one big quoted onomatopoeia plus one simple graphic device (red pulse line, impact "
    "rays, dust puff); hero 30-50%. "
    "I OBJECT MACRO — NO CHARACTER IN FRAME: extreme close-up of the single object the line is about, "
    "filling the frame, painted in full detail. "
    "J HANDS ONLY — NO CHARACTER IN FRAME: extreme close-up of hands doing the action (handing "
    "something over, gripping a tool, opening a letter), cropped at the wrists. "
    "K MAP ROUTE — NO CHARACTER IN FRAME: a simple outline map of the relevant place with 2-3 "
    "labelled dots and a dashed route between them, one small vehicle or object on the route.\n"
    "FREQUENCY BUDGET per rolling block of 10 scenes — HARD RULE: AT LEAST 4 of the 10 scenes must be "
    "CHARACTER-FREE (types G, I, J or K). The video must alternate between the narrator and the "
    "subject being explained; a run of character-only frames is the single worst failure here. "
    "Also: at least 2 of A/B, at least 1 C, at least 1 D, at most 1 E, at most 1 F, exactly 1 H. "
    "Never use the same type twice in a row and never place two character-free scenes back to back. "
    "CHOOSING: when the line is about a THING (how it works, what it costs, where it travels, what it "
    "looks like, what it is made of) use G/I/J/K; when it is about a PERSON doing, deciding or feeling "
    "something use A/B/C/D/E. Scenes of types G/I/J/K must literally contain the words "
    "'no character in frame'.\n"
    "WORLD ROTATION: two consecutive scenes may not share biome AND time of day AND palette; rotate "
    "deliberately (volcanic valley, fern jungle, rock canyon, cave interior, night campfire, dusk "
    "huts and smoke, green oasis, river crossing, overgrown modern ruin) and change the camera angle "
    "every scene.\n"
    "TEXT BUDGET: at most 1 scene in 3 carries lettering. When it does: max 2 lines, each max 3 words "
    "and 14 characters, ALL CAPS, letters A-Z digits 0-9 and spaces only, inside double quotes. No "
    "commas, no punctuation, no plus signs, no chemical symbols, no thousand separators — write "
    "\"100K YEARS\" not \"100,000\". Each infographic label box obeys the same limit. Text never sits "
    "in the top or bottom 9% of the frame.\n"
    + KARE_CESITLILIGI + DESTEK_PLANLAYICI + VERI_KARTI_PLAN + MEKAN_SUREKLILIGI
)

# ═════════ RENKLI KALEM STILI (6. referans: "Aussie Money With Bruce") ═════════
# Fark: HIK_STIL "boyanmis dunya + duz figur" kontrastina dayanir. Burada TEK medyum var —
# her sey ayni renkli kalemle cizilmis. Kimlik yuzden degil IMZA AKSESUARDAN okunur.
KALEM_STIL = (
    "Hand-drawn coloured-pencil illustration on cream textured paper, one single medium for the "
    "whole image. Visible directional pencil hatching and crayon grain on every surface; soft "
    "slightly uneven contours drawn in dark pencil, thicker on the outer silhouette and lighter "
    "inside; colour built up in layered strokes so flat areas still show the tooth of the paper. "
    "Gentle natural daylight with soft pencil-shaded shadows — no hard cel shading, no gradients, "
    "no glow, no digital vector flatness. Warm, homely, everyday-life mood; ordinary places drawn "
    "with affection and a lot of small true-to-life clutter. Figures are ultra-simple: plain white "
    "rounded head, thin dark limbs, small oval hands and feet, no nose, no neck; all the drawing "
    "detail is spent on the ENVIRONMENT and the props, never on the body. "
    "Avoid: photorealism, 3D render, anime, glossy digital vector art, neon colours, airbrush"
)
KALEM_VARSAYILAN_KARAKTER = (
    "The narrator is one simple stick figure: plain white rounded head with two black dot eyes, two "
    "short black eyebrows that carry all the emotion, and one small mouth line; no nose, no ears, no "
    "hair, no neck. White body, thin dark limbs, small oval white hands and feet. He wears exactly "
    "one signature item — a green and gold diagonally striped necktie — and it is present, identical, "
    "in every single frame he appears in. Nothing else is ever added to him"
)
KALEM_CERCEVE = (
    " FRAMING for a 16:9 centre crop of this 1536x1024 image: the top 9% and bottom 9% get cut away, "
    "so every face, sign and key silhouette stays inside 10%-90% of frame height and 8% clear of the "
    "left and right edges. Obey the shot type and character-scale band written in the scene text "
    "exactly; do not pull the camera closer or enlarge the figure. THE PLACE IS THE SUBJECT: build a "
    "complete believable room or exterior with a foreground object cutting into the frame, a "
    "midground where the action happens and a background with true perspective, and let furniture, "
    "shelves, signage and clutter run to all four edges — nothing floats on blank paper. At least one "
    "object must pass in front of the figure and partly overlap it. Keep ONE dominant light source "
    "with a clear direction and soft pencil-shaded shadows. Keep the figure's white head clearly "
    "readable against whatever sits behind it."
)
KALEM_SOZLESME = (
    "RULE ZERO — READ FIRST: this is a narrated explainer, not a character showcase. AT LEAST "
    "40% OF ALL SCENES YOU WRITE MUST CONTAIN NO CHARACTER AT ALL (shot types G, I, J, K below) "
    "and must literally contain the words 'no character in frame'. Before you finish, COUNT your "
    "scenes: if fewer than 40% are character-free, rewrite the weakest character scenes as object "
    "macros, hands-only close-ups, maps or diagrams.\n"
    "SCENE CONTRACT — each scene_prompt is ONE English paragraph of 45-80 words, slots always in this "
    "order: (1) SHOT: the shot-type letter plus the narrator's height as a percent of frame height; "
    "(2) PLACE: a specific ordinary real-world setting with at least 4 concrete named objects in it "
    "(appliances, shelves, notices, plants, tools, furniture), ONE named light source and the time of "
    "day — spend the entire adjective budget here; (3) ACTION: only what the figure(s) DO — the "
    "gesture, what they are touching or holding, and the emotion read from eyebrow angle and posture. "
    "NEVER state the character's colours or clothing (identity is injected separately). "
    "(4) TEXT: either a lettering instruction in double quotes, or literally \"no text in this "
    "image\" — this slot is never empty.\n"
    "SUPPORTING CAST: when a scene needs other people, they are the same simple stick figures but "
    "are told apart ONLY by a plain garment, hair shape or hat — never by a different body style, "
    "and never by wearing the narrator's signature item.\n"
    "SHOT TYPES AND SCALE BANDS (bands never overlap; two consecutive scenes must use different "
    "bands): A WIDE ESTABLISHING — figure 12-20%, the whole room or street visible. B MEDIUM ACTION "
    "— figure 30-50%, mid-gesture, physically interacting with a named object. C CLOSE-UP — figure "
    "55-75%, head and shoulders, eyebrows carrying the emotional beat. D DRAMATIC LIGHT — figure "
    "30-50%, dim room lit by one lamp, window or screen. E CROWD — 3-6 figures on two depth planes, "
    "narrator nearest at 30-50%, the others differentiated by garment or hair. "
    "F HELD SIGN — figure 30-50% holding a large drawn placard, board or newspaper whose short text "
    "is the point of the scene. "
    "G INFOGRAPHIC — NO CHARACTER IN FRAME: a pinboard, whiteboard or drawn chart with 2-3 arrows or "
    "pinned cards and at most 2 short labels. "
    "H SFX BEAT — one big quoted onomatopoeia plus one simple pencil graphic device (impact rays, "
    "motion lines, dust puff); figure 30-50%. "
    "I OBJECT MACRO — NO CHARACTER IN FRAME: extreme close-up of the single object the line is about, "
    "filling the frame, drawn in full pencil detail. "
    "J HANDS ONLY — NO CHARACTER IN FRAME: extreme close-up of hands doing the action (passing an "
    "envelope, signing a form, counting notes), cropped at the wrists. "
    "K MAP ROUTE — NO CHARACTER IN FRAME: a simple hand-drawn map with 2-3 labelled dots and a dashed "
    "route between them.\n"
    "FREQUENCY BUDGET per rolling block of 10 scenes — HARD RULE: AT LEAST 4 of the 10 must be "
    "CHARACTER-FREE (G, I, J, K). Also: at least 2 of A/B, at least 1 C, at least 1 D, at most 1 E, "
    "at most 1 F, exactly 1 H. Never use the same type twice in a row and never place two "
    "character-free scenes back to back.\n"
    "PLACE ROTATION: two consecutive scenes may not share the same room or location; rotate "
    "deliberately (kitchen, living room, front yard, workplace lunch room, home office, hallway, "
    "street, shed) and change the camera angle every scene.\n"
    "TEXT BUDGET: at most 1 scene in 3 carries lettering. When it does: max 2 lines, each max 3 words "
    "and 14 characters, ALL CAPS, letters A-Z digits 0-9 spaces and the $ sign only, inside double "
    "quotes. No commas, no thousand separators — write \"12 MILLION\" not \"12,000,000\". Text never "
    "sits in the top or bottom 9% of the frame.\n"
    + KARE_CESITLILIGI + DESTEK_PLANLAYICI + VERI_KARTI_PLAN + MEKAN_SUREKLILIGI
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

KALEM_PROFIL = {
    "ad": "Animasyon (Renkli Kalem)",
    "ozet": "Kremli kâğıda renkli kurşun kalem; sıcak gündelik mekânlar, imza aksesuarlı stickman",
    "sahne_sn": float(os.environ.get("ANIM_SAHNE_SN", "5")), "kelime": 14,
    "footage_pct": 0, "overlay": "yok",
    "altyazi": "yok", "motion": "sinematik", "mag": None,
    "gorsel_ek": KALEM_STIL,
    "varsayilan_karakter": KALEM_VARSAYILAN_KARAKTER,
    "cerceve": KALEM_CERCEVE,
    "sahne_sozlesme": KALEM_SOZLESME,
    "palet": "aussie-kalem",     # bu stilin dogal paleti (kullanici degistirebilir)
}

# Animasyon ALT-STILLERI (documentary'deki 3 edit stili gibi)
ANIMASYON_STILLERI = {
    "anlati-deneme": ANIMASYON_PROFIL,
    "egitici-explainer": EXPLAINER_PROFIL,
    "hikaye-whatif": HIKAYE_PROFIL,
    "renkli-kalem": KALEM_PROFIL,
}
VARSAYILAN_ANIM = "anlati-deneme"

# ═══════════════ RENK PALETI (kanal genelinde renk kimligi) ═══════════════
# Neden: stil promptu "muted ochre/sage" gibi KELIME tarif ediyordu -> model her sahnede
# baska bir yorum uretiyordu. Cozum: KESIN HEX listesi (palet_olc dersinin aynisi —
# rengi tarif etme, SAYIYLA ver). Palet DUNYAYI yonetir; karakterin kilitli renkleri
# her zaman ustundur (yoksa beyaz<->turuncu salinimi geri gelir).
PALETLER = {
    "otomatik": {"ad": "Otomatik (stile bırak)", "renkler": [],
                 "ozet": "Seçili animasyon stilinin kendi renk ailesi kullanılır"},
    "aussie-kalem": {"ad": "Sıcak Kalem (Aussie)", "ozet": "Kremli kâğıt, adaçayı, altın, kiremit",
                     "renkler": ["#F0E4CC", "#E0CBA0", "#7B8B5A", "#F2C230", "#B5651D", "#7A97B8"]},
    "vintage-editorial": {"ad": "Vintage Editorial", "ozet": "Oker, adaçayı, tozlu mavi, soluk tuğla",
                          "renkler": ["#EFE3CA", "#C8963E", "#8A9A7B", "#6E8399", "#A85A44", "#4A4038"]},
    "sicak-toprak": {"ad": "Sıcak Toprak", "ozet": "Terrakota, kum, zeytin, pas",
                     "renkler": ["#E3C99A", "#C1663F", "#7D7A45", "#9B4722", "#D9A574", "#3B2A1E"]},
    "soguk-mavi": {"ad": "Soğuk Mavi", "ozet": "Lacivert, deniz, buz, arduvaz",
                   "renkler": ["#EDE7D9", "#1F3A5F", "#2E7D8C", "#BFD9E0", "#5A7184", "#121D2B"]},
    "canli-explainer": {"ad": "Canlı Explainer", "ozet": "Kırmızı, sarı, mavi, beyaz, siyah",
                        "renkler": ["#FFFFFF", "#E63946", "#F4C430", "#2A6FDB", "#2BB673", "#111111"]},
    "gece-neon": {"ad": "Gece Neon", "ozet": "İndigo, magenta, camgöbeği, kömür",
                  "renkler": ["#1B1035", "#E0409A", "#38D6E0", "#F2A65A", "#221C2E", "#EDE6F5"]},
    "pastel-yumusak": {"ad": "Pastel Yumuşak", "ozet": "Pudra, nane, tereyağı, leylak",
                       "renkler": ["#FBF5EC", "#F3C8C2", "#BFE0CE", "#F7E6A8", "#C9BEE3", "#6E6A78"]},
    "sepya-belgesel": {"ad": "Sepya Belgesel", "ozet": "Koyu sepya, kahve, ten, kemik",
                       "renkler": ["#E6D8BF", "#C4A177", "#8C6A47", "#4A3520", "#241A10", "#9C8663"]},
    "orman-yesil": {"ad": "Orman Yeşili", "ozet": "Koyu orman, yosun, eğrelti, kabuk",
                    "renkler": ["#D7E2CC", "#93B06A", "#5E7F4A", "#234A2E", "#6B4A2E", "#16241A"]},
    "mono-kontrast": {"ad": "Mono + Tek Vurgu", "ozet": "Siyah-beyaz-gri + tek kırmızı vurgu",
                      "renkler": ["#FFFFFF", "#D8D4CC", "#8C8880", "#3A3835", "#121110", "#D93025"]},
}
VARSAYILAN_PALET = "otomatik"
_HEX_RE = __import__("re").compile(r"^#[0-9A-Fa-f]{6}$")


def palet_renkleri(secim: str, ozel: str = "") -> list:
    """Palet kimligi -> hex listesi. 'ozel' verilirse (virgulle ayrilmis hexler) o kullanilir.
    Gecersiz/bos girdi -> [] (palet kilidi uygulanmaz, stilin kendi renk ailesi kalir)."""
    if (secim or "").strip() == "ozel" or (not secim and ozel):
        out = []
        for h in (ozel or "").replace(";", ",").split(","):
            h = h.strip()
            if not h.startswith("#"):
                h = "#" + h
            if _HEX_RE.match(h) and h.upper() not in out:
                out.append(h.upper())
        return out[:8]
    return list(PALETLER.get((secim or "").strip(), {}).get("renkler", []))


def palet_prompt(secim: str, ozel: str = "") -> str:
    """Gorsel promptuna eklenecek RENK KILIDI. Bos palet -> bos metin (davranis degismez)."""
    renkler = palet_renkleri(secim, ozel)
    if len(renkler) < 2:
        return ""
    liste = ", ".join(renkler)
    return (
        " CHANNEL COLOUR PALETTE (locked, identical in every scene of every video of this channel): "
        f"build the whole picture from this exact fixed set of hex colours — {liste}. Every surface, "
        "garment, prop, sky, ground and shadow must be one of these hues, or a lighter tint, darker "
        "shade or direct mix of two of them; do NOT introduce any hue outside this set. Vary WHICH of "
        "them dominates from scene to scene (one scene led by the darkest, the next by the warmest) so "
        "consecutive frames never look identical, but never leave the set. "
        "PRIORITY: if the locked character's own colours differ from this palette, the CHARACTER'S "
        "colours always win — this palette governs the world around the character, not their identity."
    )


# ═══════════════ ARKA PLAN (mekan dunyasi + yogunluk) ═══════════════
# Neden ayri bir eksen: 567 referans karesinin analizi iki ZIT dogru gosterdi —
# Paint Explainer (1.96M) karelerinin cogu BOMBOS beyaz zeminde tek oge; Bruce ve
# Serious History ise tikabasa dolu mekanlar kuruyor. Ikisi de calisiyor. Yani
# "her yer dolu olsun" evrensel bir kural DEGIL, kanal karari. Burasi o karar.
#
# DIKKAT: stil promptlari (*_CERCEVE) yogunluk dayatiyor ("objects must run to all
# four edges"). Arka plan secimi bununla CELISEBILIR. Renk paletindeki dersin aynisi:
# celiskiyi cozmeden birakma -> arka plan blogu en SONA eklenir ve oncelikli oldugunu
# acikca soyler.
ARKA_PLANLAR = {
    "otomatik": {"ad": "Otomatik (stile bırak)", "yogunluk": "-",
                 "ozet": "Seçili animasyon stilinin kendi mekân kuralı geçerli", "prompt": ""},
    "sade-beyaz": {
        "ad": "Sade Beyaz", "yogunluk": "sade",
        "ozet": "Bomboş beyaz zemin, tek öğe — Paint Explainer düzeni",
        "prompt": ("BACKGROUND: a plain empty white field. Draw ONLY the subject the scene names "
                   "and nothing else — no room, no furniture, no scenery, no horizon, no texture. "
                   "Generous empty space around the subject is the point, not a flaw. A thin ground "
                   "shadow is the only extra mark allowed.")},
    "sade-renkli": {
        "ad": "Sade Renk Alanı", "yogunluk": "sade",
        "ozet": "Tek düz renk zemin, dikkat dağıtan detay yok",
        "prompt": ("BACKGROUND: one single flat colour field filling the whole frame, chosen from the "
                   "locked palette. No scenery, no objects, no gradient, no texture. Only the subject "
                   "the scene names sits on it, with a simple flat ground shadow.")},
    "gundelik-ev": {
        "ad": "Gündelik Ev/Mahalle", "yogunluk": "zengin",
        "ozet": "Mutfak, salon, bahçe, iş yeri — yaşanmış detaylı mekânlar",
        "prompt": ("BACKGROUND: a specific, lived-in everyday place — a kitchen, living room, front "
                   "yard, workplace lunch room, home office, shed or suburban street. Fill it with at "
                   "least 5 small true-to-life details (appliances, notices, jars, plants, tools, "
                   "framed photos, worn floors) running to all four edges, with real perspective and "
                   "one named light source.")},
    "tarihi-donem": {
        "ad": "Tarihi Dönem", "yogunluk": "zengin",
        "ozet": "Kale, ordugâh, eski sokak, saray — dönem detaylı",
        "prompt": ("BACKGROUND: a period-accurate historical place — castle wall, war camp, throne "
                   "hall, cobbled old street, harbour, marketplace. Include at least 4 concrete "
                   "period props (banners, barrels, torches, weapons racks, carts) and build three "
                   "depth layers with atmospheric haze on the far one.")},
    "doga-manzara": {
        "ad": "Doğa / Manzara", "yogunluk": "zengin",
        "ozet": "Orman, dağ, okyanus, çöl — geniş sinematik doğa",
        "prompt": ("BACKGROUND: a wide natural landscape — forest, mountain range, ocean, desert, "
                   "river valley, cave. Build a dark framing foreground, a midground where the action "
                   "happens and a hazy receding far vista, with weather and time of day clearly "
                   "readable and one dominant light source.")},
    "sehir-modern": {
        "ad": "Modern Şehir", "yogunluk": "zengin",
        "ozet": "Cadde, ofis, dükkân, metro — çağdaş kent dokusu",
        "prompt": ("BACKGROUND: a contemporary urban place — a street with shopfronts, an open-plan "
                   "office, a supermarket aisle, a subway platform, an apartment interior. Include "
                   "signage, glazing, vehicles or crowds as depth layers, with believable perspective "
                   "running to all four edges.")},
    "calisma-panosu": {
        "ad": "Pano / Masa Üstü", "yogunluk": "orta",
        "ozet": "Mantar pano, beyaz tahta, masa — açıklayıcı kurulum",
        "prompt": ("BACKGROUND: an explainer setup — a corkboard with pinned cards and string, a "
                   "whiteboard with a diagram, or a desk seen from above with papers, pens and notes. "
                   "The board or desktop fills most of the frame and IS the environment; keep the "
                   "surrounding room minimal and out of focus.")},
    "karanlik-sinematik": {
        "ad": "Karanlık Sinematik", "yogunluk": "orta",
        "ozet": "Tek ışık kaynağı, koyu zemin, dramatik",
        "prompt": ("BACKGROUND: a dark, low-key environment lit by exactly ONE visible source — a "
                   "lamp, fire, screen, doorway or beam. Most of the frame falls into deep shadow "
                   "with only the essential shapes catching light; keep detail sparse and let the "
                   "darkness do the work.")},
}
VARSAYILAN_ARKAPLAN = "otomatik"


def arkaplan_prompt(secim: str) -> str:
    """Cerceve blogunun SONUNA eklenecek mekan yonergesi. 'otomatik'/bilinmeyen -> bos."""
    a = ARKA_PLANLAR.get((secim or "").strip())
    if not a or not a.get("prompt"):
        return ""
    ek = " " + a["prompt"]
    if a.get("yogunluk") == "sade":
        # Stil bloklari "hicbir yer bos kalmasin" diyor; sade arka plan bunu ezmeli.
        ek += (" PRIORITY: this background instruction OVERRIDES any earlier instruction to fill the "
               "frame with objects, furniture, clutter or scenery running to the edges. Emptiness "
               "here is deliberate.")
    return ek


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
    if not p:
        return ""
    metin = "The main character is " + ", ".join(p) + "."
    # IMZA AKSESUAR (6. referans dersi): minimal stickman'de kimlik yuzden degil TEK bir
    # ayirt edici parcadan okunur. Onu ayrica ve emir kipiyle tekrarla — yoksa model
    # sahneler arasinda "unutup" birakiyor ve karakter baskasina donuyor.
    imza = k.get("ayirt_edici") or k.get("kiyafet")
    if imza and str(imza).lower() not in ("none", "yok"):
        metin += (f" SIGNATURE (never omitted): {imza} — this must be clearly visible and identical "
                  "in EVERY frame the character appears in; it is how the viewer recognises them. "
                  "No other figure in any scene may wear or carry it.")
    return metin


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



# ── SAHNE TIPI ATAMASI (KODLA ZORLANIR) ──
# Prompt ile "%40 karaktersiz olsun" demek ISE YARAMADI (LLM 1/7 uretti). Cozum: tipi
# planlayiciya BIZ soyluyoruz. Tek sahne atlanamaz, oran garanti, ard arda karaktersiz olmaz.
TIP_KARAKTERLI = ["A WIDE ESTABLISHING", "B MEDIUM ACTION", "C CLOSE-UP",
                  "D DRAMATIC LIGHT", "E CROWD", "H SFX BEAT"]
# N/O: Simple Explainer + Bruce karelerinde dogrulandi (ekran arayuzu, tepeden cekim).
TIP_KARAKTERSIZ = ["I OBJECT MACRO", "J HANDS ONLY", "K MAP ROUTE", "G INFOGRAPHIC",
                   "N SCREEN READOUT", "O OVERHEAD FLATLAY"]


def sahne_tipi_atamasi(adet: int) -> str:
    """Sahne basina cekim tipi atar: tek indeksler KARAKTERSIZ -> ~%50 oran, ard arda yok."""
    satir = []
    for i in range(adet):
        if i % 2 == 1:
            t = TIP_KARAKTERSIZ[(i // 2) % len(TIP_KARAKTERSIZ)]
            satir.append(f"{i+1}={t} (no character in frame)")
        else:
            t = TIP_KARAKTERLI[(i // 2) % len(TIP_KARAKTERLI)]
            satir.append(f"{i+1}={t}")
    return ("SHOT TYPE ASSIGNMENT — NON-NEGOTIABLE. The shot type of every scene is decided for you "
            "below. Write each scene using EXACTLY its assigned type and open the scene_prompt with "
            "that type's name. Scenes marked '(no character in frame)' must contain no figure at all "
            "and must literally include the words 'no character in frame'. Do not swap, skip or "
            "reorder types; fit the narration to the assigned type.\n" + "; ".join(satir) + "\n")


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
        if prof.get("tip_atamasi", True):
            sahne_kural = sahne_tipi_atamasi(hedef) + sahne_kural
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
        # Karakter-her-sahnede guvenlik agi. DIKKAT: eskiden "large central foreground subject"
        # ekleniyordu; planlayici "the stickman commander" gibi yazdigi icin bu HER sahnede
        # tetikleniyor ve cekim sistemini (genis plan %15, orta %40) EZIYORDU -> karakter hep
        # ortada, buyuk ve dimdik cikiyordu. Artik sadece kahramanin VARLIGI garanti edilir,
        # olcek/kompozisyon cekim sozlesmesine birakilir.
        # Karaktersiz kareler MESRU (patlatilmis sema, makro detay, yazi karti) — zorlama.
        karaktersiz = any(x in sp.lower() for x in
                          ("no character", "object macro", "exploded view", "concept card",
                           "comparison", "no figure", "hands only", "map route"))
        if (kayn == "ai" and not karaktersiz and not any(
                x in sp.lower() for x in ("main character", "the hero", "stickman", "the character"))):
            s["scene_prompt"] = "The recurring main character appears in this scene. " + sp
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
    # PROMPT SIRASI ONEMLI: once SAHNE/AKSIYON, sonra kisa kimlik kilidi.
    # Referans gorsel notr duruslu oldugu icin modelin PIKSEL egilimi "dimdik dur"a cekiyordu;
    # bu yuzden aksiyon en basta ve en guclu sekilde tekrarlanir.
    prompt = scene_prompt.rstrip(". ") + "."
    # KARAKTERSIZ KARE (patlatilmis sema / makro detay / yazi karti / karsilastirma):
    # kimlik kilidi EKLENMEZ, aksi halde model kareye zorla bir figur sokar.
    karaktersiz = any(x in (scene_prompt or "").lower() for x in
                      ("no character", "object macro", "exploded view", "concept card",
                       "no figure", "hands only", "map route"))
    if karaktersiz:
        prompt += (" This frame contains NO character and no people at all — the object, diagram "
                   "or lettering itself is the entire subject. Do not add any figure.")
    if (kar_var or capa_var) and not karaktersiz:
        # 1) POZ SERBESTLIGI — en kritik cumle. Referans SADECE tasarim kaynagi, poz kaynagi DEGIL.
        prompt += (" THE REFERENCE IMAGE IS A CHARACTER DESIGN SHEET, NOT A POSE REFERENCE. It shows "
                   "the character standing neutrally only so you can see how it is drawn. In THIS "
                   "picture the character must be fully ACTING OUT the moment described above — the "
                   "body language, gesture, posture and facial expression must match that action and "
                   "emotion. Do NOT draw the character standing upright and facing the camera with "
                   "arms at its sides unless the scene text explicitly asks for it. Show it leaning, "
                   "reaching, crouching, running, pointing, carrying, turning, looking — whatever the "
                   "moment requires, interacting with the objects and surroundings named in the scene.")
        # 2) KIMLIK — kisa tutulur; uzun kilit metni aksiyonu bogar
        prompt += (" IDENTITY LOCK: keep the character's design identical to the reference — same "
                   "body and face design, same exact colours, same proportions, same clothing and "
                   "markings — but carry over NOTHING else: not its pose, not its camera angle, not "
                   "its background, and not any object it holds there. Render exactly ONE main "
                   "character unless the scene describes others. Obey the shot type and character "
                   "scale given in the scene text; the environment carries the picture.")
        prompt += DESTEK_GORSEL + VERI_KARTI_GORSEL + MARKA_YASAK
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
    # IKI POZLU tasarim sayfasi: tek notr figur, sonraki sahnelerde "dimdik dur" baskisi yapiyordu.
    # Iki farkli duruş gostermek modele "bu bir tasarim sayfasi, poz degil" sinyali verir.
    "Character design sheet of the SAME single character shown in the reference image, drawn TWICE "
    "side by side on one plain flat light-grey studio background: on the LEFT standing upright "
    "front-facing with arms relaxed at the sides and hands open and empty; on the RIGHT the same "
    "character in a three-quarter view mid-stride, one arm raised and reaching forward. "
    "Both figures full body from head to feet, even soft lighting, no scenery, no furniture, no "
    "props, no shadows on the background. Reproduce the character's identity exactly: same species, "
    "same colours, same face, same hair, same clothing, same proportions in both drawings. "
    "No other characters. No text, no watermark, no border."
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
               altyazi_ac: str = "", palet: str = "", palet_ozel: str = "",
               arkaplan: str = "") -> dict:
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
    # ── RENK PALETI: bu videoda secilmediyse kanal profilininki (kanal genelinde ayni renk) ──
    # Oncelik: bu videodaki secim > kanal profili > stilin kendi dogal paleti ("Otomatik").
    if not palet and kanal:
        palet, palet_ozel = kanal.get("palet", ""), kanal.get("palet_ozel", "")
    if not palet:
        palet = prof.get("palet", "")
    pal_ek = palet_prompt(palet, palet_ozel)
    if pal_ek:
        gorsel_ek = gorsel_ek + "." + pal_ek
        print(f"  palet kilidi: {palet or 'ozel'} -> {palet_renkleri(palet, palet_ozel)}",
              file=sys.stderr)
    # Kompozisyon/cerceveleme kurali (animasyonda ortam basrol, karakter cerceveyi doldurmaz)
    cerceve_ek = prof.get("cerceve", "")
    # ── ARKA PLAN: bu videoda secilmediyse kanal profilininki. EN SONA eklenir ki
    #    stilin yogunluk dayatmasini ezebilsin (sade-beyaz secilirse "her yer dolsun" susar).
    if not arkaplan and kanal:
        arkaplan = kanal.get("arkaplan", "")
    ap_ek = arkaplan_prompt(arkaplan)
    if ap_ek:
        cerceve_ek = cerceve_ek + ap_ek
        print(f"  arka plan: {arkaplan}", file=sys.stderr)
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
    # 60 dk hikaye (8sn sahne, paralel gorsel, 10 cekirdek render) ~2-2.5 saat, ~$40 gorsel.
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

    # ═══ SAHNE URETIMI — 3 FAZ (paralel) ═══
    # Eski hat sahneleri TEKER TEKER uretiyordu (gorsel + bekleme + TTS ust uste eklenirdi;
    # 300 sahne ~2 saat). Yeni hat: (A) capa sahnesi sirali, (B) kalan gorseller PARALEL
    # (GORSEL_PARALEL isci), (C) TTS paralel + montaj SIRALI. 429 gelirse referansli_gorsel
    # zaten Retry-After'a uyuyor -> paralellik hiz limitine karsi kendi kendini frenler.
    bakiye_bitti = False   # bakiye/limit doldu mu (elde olanla kurtarma icin)
    uretim_durdu = False   # toplu basarisizlikta yeni istek acilmasin (para yanmasin)
    gorsel_bekle = float(os.environ.get("GORSEL_BEKLE", "5"))
    paralel = max(1, int(os.environ.get("GORSEL_PARALEL", "4")))

    islenecek = []   # (i, n, sahne, metin, overlay) — bos voiceover'lar elenmis, sira sabit
    for i, s in enumerate(scenes):
        metin = str(s.get("voiceover", "")).strip()   # model sayi/null verirse .strip() patlamasin
        if not metin:
            continue
        islenecek.append((i, i + 1, s, metin,
                          str(s.get("overlay", "")).strip() if overlay_stil != "yok" else ""))

    sonuc_medya = {}          # n -> (tur, medya). Basarisiz sahne burada olmaz.
    sayac_kilit = threading.Lock()
    tamamlanan = [0]

    def _sahne_medya(n, s):
        """Tek sahnenin medyasini (footage veya AI gorsel) uretir. Thread icinde calisir."""
        nonlocal bakiye_bitti, uretim_durdu
        if bakiye_bitti or uretim_durdu:
            return None
        # 1) Footage sahnesi mi?
        if footage_acik and str(s.get("kaynak")) == "footage" and str(s.get("footage_sorgu", "")).strip():
            vyol_full = os.path.join(PUBLIC, "isler", is_adi, f"sahne_{n}.mp4")
            if kaynak.footage_getir(s["footage_sorgu"].strip(), vyol_full, yt_once=yt_once):
                return ("video", f"isler/{is_adi}/sahne_{n}.mp4")
        # 2) AI gorsel (footage yoksa/basarisizsa)
        sp = str(s.get("scene_prompt", "")).strip() or str(s.get("footage_sorgu", "")).strip()
        gyol_full = os.path.join(PUBLIC, "isler", is_adi, f"sahne_{n}.png")
        try:
            uretildi = referansli_gorsel(sp, kar_yol, gyol_full, stil_prompt=gorsel_ek,
                                         kar_kilit=kar_kilit, stil_yol=stil_yol,
                                         capa_yol=capa_yol, stil_kilit=stil_kilit,
                                         model=gorsel_model, cerceve=cerceve_ek)
        except BakiyeHatasi:
            # Bakiye/limit doldu: DAHA FAZLA PARA HARCAMA; diger isciler de yeni istek acmaz.
            bakiye_bitti = True
            return None
        if not uretildi:
            return None
        if mag_profil and s.get("hd"):   # OTOMATIK: sadece plan HD isaretlediyse
            kaynak.magnific_upscale(gyol_full, optimized_for=mag_profil, scale="2x")
        # Hiz limiti: her ISCI kendi isteginden sonra bekler (toplam hiz = paralel/(uretim+bekleme))
        time.sleep(gorsel_bekle)
        return ("image", f"isler/{is_adi}/sahne_{n}.png")

    # ── FAZ A: CAPA (yalniz animasyon/hikaye ve profil capasi yoksa) ──
    # Ilk basarili sahne sonraki TUM sahnelere referans olacagi icin sirali uretilmek zorunda.
    basla = 0
    if mod in ("animasyon", "hikaye") and not capa_yol:
        while basla < len(islenecek) and not bakiye_bitti:
            i, n, s, _, _ = islenecek[basla]
            bildir(f"Sahne {n}/{toplam}: çapa görseli üretiliyor...", 8)
            r = _sahne_medya(n, s)
            basla += 1
            if r:
                sonuc_medya[n] = r
                gyol_full = os.path.join(PUBLIC, "isler", is_adi, f"sahne_{n}.png")
                capa_yol = os.path.join(is_dizini, "_capa.png")   # Magnific ONCESI kucuk kopya
                try:
                    shutil.copy(gyol_full, capa_yol)
                except Exception:
                    capa_yol = gyol_full
                # PROFIL VAR ama henuz kilitli degil -> ilk sahneyi kanalin KALICI capasi yap.
                if kanal and not capa_profilden:
                    if profil_capa_kilitle(profil_id, capa_yol):
                        capa_profilden = True
                        print(f"  profil '{profil_id}' capasi KILITLENDI", file=sys.stderr)
                break
            print(f"sahne {n} atlandi (capa denemesi)", file=sys.stderr)
            if basla >= 6:   # 6 denemede capa cikmadiysa sistemsel sorun var, para yakma
                uretim_durdu = True
                print("  capa uretilemedi -> uretim durduruldu", file=sys.stderr)

    # ── FAZ B: KALAN GORSELLER PARALEL ──
    kalan = islenecek[basla:]
    if kalan and not bakiye_bitti and not uretim_durdu:
        bildir(f"Görseller üretiliyor ({paralel} paralel)...", 9)
        basarisiz = 0
        with ThreadPoolExecutor(max_workers=paralel) as havuz:
            gelecek = {havuz.submit(_sahne_medya, n, s): n for i, n, s, _, _ in kalan}
            for g in as_completed(gelecek):
                n = gelecek[g]
                try:
                    r = g.result()
                except Exception as e:   # beklenmedik istisna tek sahneyi yaksin, isi degil
                    r = None
                    print(f"  sahne {n} gorsel istisna: {str(e)[:140]}", file=sys.stderr)
                if r:
                    sonuc_medya[n] = r
                else:
                    basarisiz += 1
                    print(f"sahne {n} atlandi", file=sys.stderr)
                    # Cok basarisizlik + neredeyse hic basari yok: sistem bozuk, kalanini durdur
                    if basarisiz >= 8 and len(sonuc_medya) < 3:
                        uretim_durdu = True
                with sayac_kilit:
                    tamamlanan[0] += 1
                    yuzde = 8 + int(50 * tamamlanan[0] / max(1, len(islenecek)))
                bildir(f"Görsel {tamamlanan[0]}/{len(islenecek)} hazır", yuzde)
    if bakiye_bitti:
        print(f"  BAKIYE bitti — {len(sonuc_medya)} uretilmis sahneyle devam", file=sys.stderr)

    # ── FAZ C: SESLENDIRME PARALEL (TTS_PARALEL isci) + MONTAJ SIRALI ──
    bildir("Seslendirme üretiliyor...", 60)
    tts_sem = asyncio.Semaphore(max(1, int(os.environ.get("TTS_PARALEL", "3"))))

    async def _tts(n, metin):
        async with tts_sem:
            syol = f"isler/{is_adi}/ses_{n}.mp3"
            kelimeler, sure = await uret_seslendir(metin, ses, os.path.join(PUBLIC, syol))
            return n, syol, kelimeler, sure

    tts_sonuc = {}
    tts_cikti = await asyncio.gather(
        *[_tts(n, metin) for i, n, s, metin, _ in islenecek if n in sonuc_medya],
        return_exceptions=True)
    for t in tts_cikti:
        if isinstance(t, BaseException):
            print(f"  tts istisna: {str(t)[:120]}", file=sys.stderr)
            continue
        n, syol, kelimeler, sure = t
        if kelimeler is None:   # TTS retry'lar tukendi -> bu sahneyi atla, is olmesin
            print(f"sahne {n} sesi uretilemedi, atlandi", file=sys.stderr)
            continue
        tts_sonuc[n] = (syol, kelimeler, sure)

    # Montaj: orijinal sahne sirasi korunur (paralellik sirayi bozamaz)
    for i, n, s, metin, overlay in islenecek:
        if n not in sonuc_medya or n not in tts_sonuc:
            continue
        tur, medya = sonuc_medya[n]
        syol, kelimeler, sure = tts_sonuc[n]
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

    # ── HIZLI MOTOR (ffmpeg, Chrome'suz — ~8x hizli) ──
    # Acma: env RENDER_MOTOR=ffmpeg VEYA /opt/vidrush/RENDER_MOTOR dosyasina "ffmpeg" yaz
    # (docker exec ile konteyner yeniden yaratmadan). Kapsam disi is/hata -> Remotion'a duser.
    motor = os.environ.get("RENDER_MOTOR", "")
    if not motor:
        try:
            with open("/opt/vidrush/RENDER_MOTOR") as f:
                motor = f.read().strip()
        except Exception:
            motor = ""
    hizli_ok = False
    if motor == "ffmpeg":
        try:
            import hizli_render
            hizli_ok = hizli_render.ffmpeg_render(is_adi, props, ham, ilerle=bildir)
        except Exception as e:
            print(f"  hizli motor hata: {str(e)[:200]}", file=sys.stderr)
        if not hizli_ok:
            print("  hizli motor kullanilamadi -> Remotion ile devam", file=sys.stderr)

    # Full HD 1080p 16:9 (kompozisyon 1920x1080, scale YOK). Web aracinda boyut limiti yok.
    # concurrency ortamdan (Hetzner cok cekirdek): REMOTION_CONCURRENCY.
    konk = os.environ.get("REMOTION_CONCURRENCY", "1")
    if not hizli_ok:
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
        # Tavan 13 saat (60 dk hikaye eski 2 vCPU'da ~10-12 saatti; hizli motor bunu asmaz zaten).
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
