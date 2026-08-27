#!/usr/bin/env python3
"""BEYIN — SENKRON MOD: metin -> cumle basina Flow promptu.

⚠ URETIM BURADA DEGIL: bu modul yalnizca cumleleri SINEMATIK INGILIZCE
prompta cevirir; gorsel/video uretimini yine Flow ajani yapar
(flow_surucu.parti_uret).

KURAL (kullanicinin urun tarifi): ILK %30 CUMLE VIDEO, kalani karisik.
Her cikti Telegram'a DAYANDIGI CUMLEYLE birlikte gonderilir — eslesme
bu moduldeki sira uzerinden tasinir.
"""
from __future__ import annotations

import json
import os
import re
import urllib.request

from . import ayar  # gizli.env'i yukler (HAYALET_OPENAI_KEY)

OPENAI_KEY = os.environ.get("HAYALET_OPENAI_KEY",
                            os.environ.get("OPENAI_API_KEY", ""))
# Kalite karari (20 Agu 2026): prompt yazimi videonun GORUNUMUNU belirler;
# gpt-4.1 farki video basina ~$0.05 — varsayilan tam model.
MODEL = os.environ.get("HAYALET_LLM_MODEL", "gpt-4.1")
# ⚠ URUN KURALI (21 Agu 2026 — kullanici karari): CUMLELERIN ILK %30'u
# KOSULSUZ VIDEO olur (kanal acilisi yogun hareket ister; Flow klipleri
# ~6 sn). Kalan %70'te LLM cumle cumle secer: hareket sartsa video, degilse
# gorsel. LLM yoksa giris-sonrasi hepsi gorsel.
# Eski HAYALET_ACILIS_KARAKTER (karakter esigi) BIRAKILDI — cumle sayisi
# uzerinden oran vermek metin uzunlugundan bagimsiz, ongorulebilir sonuc verir.
ACILIS_ORAN = float(os.environ.get("HAYALET_ACILIS_ORAN", "0.30"))

_CUMLE = re.compile(r"[^.!?…。！？؟]+[.!?…。！？؟]+|[^.!?…。！？؟]+$")
# ⚠ OLCULDU (21 Agu 2026): "Bu 3. cumledir." metni IKIYE bolunuyordu —
# Turkce sira sayilarindaki nokta (3., 1923., 2.) cumle sonu sanildi.
# Rakamdan hemen sonra gelen ve ardindan BUYUK HARFLE baslamayan nokta,
# cumle siniri DEGILDIR. Bolmeden once bu noktalar korunur.
_SIRA_NOKTA = re.compile(r"(?<=\d)\.(?=\s+\S)")
# Ondalik/tarih: 12.50, 01.09.2026 — iki rakam arasindaki nokta ASLA bolmez.
_ONDALIK = re.compile(r"(?<=\d)\.(?=\d)")
_KORUMA = "\x00"

# ⚠ STIL SORUSU YOK (kullanici karari, 21 Agu 2026): promptlari kullanici
# KENDISI yaziyor, stil zaten o promptlarin icinde. Sistemin ayrica stil
# dayatmasi promptu bozar.

# Uretim modu: hangi cumle video, hangisi gorsel?
MODLAR = {
    "karisik": f"🎞 İlk %{int(ACILIS_ORAN * 100)} video, kalanı görsel",
    "gorsel": "🖼 Tamamı görsel",
    "video": "🎬 Tamamı video",
}

# Promptun basindaki tur eki: "video: ..." / "gorsel: ..." satir bazinda
# MODU EZER. Boylece "tamami gorsel" secip birkac cumleyi video yapabilirsin.
_TUR_ONEK = re.compile(r"^\s*(video|g[oö]rsel|image|foto[gğ]raf)\s*[:\-–]\s*",
                       re.IGNORECASE)
# Satir basindaki numara: "1. ", "1) ", "1- ", "1 - "
_NUMARA = re.compile(r"^\s*\d{1,4}\s*[.)\-–]\s*")
# Prompt icinde karakteri cagirma isareti
_YER_TUTUCU = re.compile(r"@karakter|\{karakter\}", re.IGNORECASE)


def karakter_ayristir(tarif: str) -> tuple:
    """"Elif: 8 yasinda, kizil sacli" -> ("Elif", "Elif, 8 yasinda, kizil sacli")

    Ad verilmezse ("", tarif) doner — o zaman yalnizca @karakter isareti
    ile cagrilabilir.
    """
    t = (tarif or "").strip()
    if not t:
        return "", ""
    if ":" in t:
        ad, _, kalan = t.partition(":")
        ad, kalan = ad.strip(), kalan.strip()
        # Ad kisa olmali; uzunsa bu bir ad degil, cumlenin parcasidir.
        if kalan and 0 < len(ad.split()) <= 3:
            return ad, f"{ad}, {kalan}"
    return "", t


# ⚠ ENJEKTE EDILEN METIN KISA OLMALI (22 Agu 2026 olcumu): kullanici
# karakter alanina 1400 karakterlik TAM BIR REFERANS-SAYFASI PROMPTU
# yapistirdi ("...drawn three times side by side, front view, profile,
# No scene, no text..."). Bu metin sahne promptunun basina eklenince Flow
# sahneyi degil REFERANS SAYFASI uretti. Enjeksiyon icin yalnizca GORUNUS
# tarifi gerekir; stil/oran/"sahne yok" gibi meta talimatlar ZEHIRLIDIR.
KARAKTER_TAVAN = int(os.environ.get("HAYALET_KARAKTER_TAVAN", "260"))


def _kirp(metin: str, tavan: int = None) -> str:
    """Tavana kadar kirpar ama KELIMEYI ORTADAN BOLMEZ."""
    tavan = tavan or KARAKTER_TAVAN
    metin = " ".join((metin or "").split())
    if len(metin) <= tavan:
        return metin
    kesik = metin[:tavan]
    bosluk = kesik.rfind(" ")
    return (kesik[:bosluk] if bosluk > tavan * 0.6 else kesik).rstrip(" ,;-")

# Meta talimat sinyalleri — biri varsa metin sadelestirilmeli.
_META = ("reference sheet", "no scene", "no text", "no labels", "16:9",
         "high resolution", "style\n", "colour\n", "color\n", "clothing\n",
         "character\n", "side by side", "three-quarter", "sketchbook",
         "background.", "pixels")


def karakter_meta_mi(tarif: str) -> bool:
    """Bu bir GORUNUS tarifi mi, yoksa tam bir prompt mu?"""
    t = (tarif or "").lower()
    return len(tarif or "") > KARAKTER_TAVAN or any(m in t for m in _META)


def karakter_sadelestir(tarif: str, bildir=None) -> str:
    """Uzun/prompt-benzeri karakter metnini KISA gorunus cumlesine indirger.

    LLM varsa onu kullanir (her bicimi anlar); yoksa satir bazli temizlikle
    CHARACTER/CLOTHING bolumlerini toplar. Her halukarda TAVANLA kirpilir.
    """
    tarif = (tarif or "").strip()
    if not tarif or not karakter_meta_mi(tarif):
        return tarif
    if OPENAI_KEY:
        try:
            sistem = (
                "Compress the user's character definition into ONE short "
                "English clause describing ONLY the person's visible "
                "appearance: age, build, face, hair, and exact clothing with "
                "colours. Keep any single distinctive accent detail.\n"
                "REMOVE everything else: style/medium instructions, colour "
                "palette rules, aspect ratio, resolution, 'reference sheet', "
                "'front view/profile', 'no scene/no text', section headers.\n"
                f"Max {KARAKTER_TAVAN} characters. No line breaks. "
                'Return JSON: {"karakter":"..."}')
            c = json.loads(_oai([{"role": "system", "content": sistem},
                                 {"role": "user", "content": tarif[:4000]}]))
            kisa = str(c.get("karakter", "")).strip()
            if kisa:
                if bildir:
                    bildir(f"🧍 karakter sadeleştirildi: {kisa[:150]}")
                return _kirp(kisa)
        except Exception as e:                               # noqa: BLE001
            if bildir:
                bildir(f"⚠ karakter sadeleştirme düştü ({type(e).__name__})")
    # LLM yoksa: bolum basliklarindan sonrasini topla, meta satirlari at.
    satirlar, al = [], False
    for satir in tarif.splitlines():
        t = satir.strip()
        if not t:
            continue
        if t.upper() in ("CHARACTER", "CLOTHING"):
            al = True
            continue
        if t.upper() in ("STYLE", "COLOUR", "COLOR"):
            al = False
            continue
        if al and not any(m in t.lower() for m in _META):
            satirlar.append(t)
    kisa = " ".join(satirlar) or tarif
    return _kirp(kisa)


def karakter_yerlestir(prompt: str, ad: str, betim: str) -> str:  # noqa: D401
    """Promptta karaktere ATIF varsa TAM BETIMLEMEYI yerine koyar.

    ⚠ NEDEN GEREKLI: Flow her promptu bagimsiz uretir, onceki kareyi
    hatirlamaz. Promptta sadece "Elif" yazmak yetmez — Elif'in kim oldugunu
    bilmez. Bu yuzden ad gectigi ILK yerde tam betimleme ile degistirilir.
    Atif yoksa prompt AYNEN kalir (manzara kareleri bozulmasin).
    """
    if not betim:
        return prompt
    betim = _kirp(betim)                     # son emniyet: promptu bogmasin
    if _YER_TUTUCU.search(prompt):
        return _YER_TUTUCU.sub(lambda _m: betim, prompt)
    if ad:
        kalip = re.compile(rf"\b{re.escape(ad)}\b", re.IGNORECASE)
        if kalip.search(prompt):
            return kalip.sub(lambda _m: betim, prompt, count=1)
    return prompt


def promptlari_ayristir(metin: str) -> list:
    """Kullanicinin prompt blogu -> [(tur_ezme, prompt)] sirayla.

    tur_ezme: "video" | "gorsel" | "" (mod ne diyorsa o)
    Bos satirlar atlanir, satir basi numaralari temizlenir.
    """
    cikti = []
    for satir in (metin or "").splitlines():
        t = satir.strip()
        if not t:
            continue
        t = _NUMARA.sub("", t)
        ezme = ""
        m = _TUR_ONEK.match(t)
        if m:
            ilk = m.group(1).lower()
            ezme = "video" if ilk == "video" else "gorsel"
            t = t[m.end():].strip()
        if t:
            cikti.append((ezme, t))
    return cikti


def plan_elle(cumleler: list, promptlar: list, karakter: str = "",
              mod: str = "karisik") -> list:
    """KULLANICININ promptlarindan plan kurar — LLM YOK.

    promptlar: promptlari_ayristir ciktisi. Sayisi cumle sayisina ESIT olmali;
    cagiran bunu ONCEDEN dogrulamalidir (bkz. bot).
    """
    ad, betim = karakter_ayristir(karakter_sadelestir(karakter))
    if mod == "gorsel":
        varsayilan = ["gorsel"] * len(cumleler)
    elif mod == "video":
        varsayilan = ["video"] * len(cumleler)
    else:
        v = max(1, round(len(cumleler) * ACILIS_ORAN))
        varsayilan = ["video"] * v + ["gorsel"] * (len(cumleler) - v)

    plan = []
    for i, (cumle, (ezme, ham)) in enumerate(zip(cumleler, promptlar), 1):
        plan.append({"sira": i, "cumle": cumle,
                     "tur": ezme or varsayilan[i - 1],
                     "prompt": karakter_yerlestir(ham, ad, betim),
                     "stil": ""})
    return plan


def cumlelere_bol(metin: str) -> list:
    """Metni cumlelere boler. Sira sayisi noktalarini cumle sonu SAYMAZ."""
    ham = metin or ""
    korunmus = _ONDALIK.sub(_KORUMA, ham)
    korunmus = _SIRA_NOKTA.sub(
        lambda m: _KORUMA if not _sonrasi_buyuk(korunmus, m.end()) else ".",
        korunmus)
    return [c.replace(_KORUMA, ".").strip()
            for c in _CUMLE.findall(korunmus) if c.strip()]


def _sonrasi_buyuk(metin: str, konum: int) -> bool:
    """Noktadan sonraki ilk harf BUYUK mu? Buyukse gercek cumle sonudur."""
    kalan = metin[konum:].lstrip()
    return bool(kalan) and kalan[0].isupper()


def _oai(mesajlar, zaman_asimi=120) -> str:
    govde = json.dumps({"model": MODEL, "messages": mesajlar,
                        "response_format": {"type": "json_object"},
                        "temperature": 0.4}).encode()
    istek = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions", data=govde,
        headers={"Authorization": f"Bearer {OPENAI_KEY}",
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(istek, timeout=zaman_asimi) as y:
        return json.load(y)["choices"][0]["message"]["content"]


def plan_kur(metin: str, bildir=None, stil: str = "", karakter: str = "",
             mod: str = "karisik") -> list:
    """Metin -> [{"sira", "cumle", "tur", "prompt", "stil"}].

    stil     : gorsel stil tohumu (STILLER'den ya da kullanicinin kendi tarifi)
    karakter : her karede tekrar eden ANA KARAKTER tarifi (bos olabilir)
    mod      : "karisik" (ilk %30 video) | "gorsel" (hepsi) | "video" (hepsi)

    ⚠ LLM COKERSE IS OLMEZ: dusus promptu cumlenin kendisi + sinematik
    sabit sondur; kullanici bunu Telegram'da GORUR (sessiz dusus yok).
    """
    cumleler = cumlelere_bol(metin)
    if not cumleler:
        return []
    # MOD: animasyon/cizgi kanallarda genelde HEPSI GORSEL istenir — o zaman
    # giris kurali da uygulanmaz (kullanici karari, 21 Agu 2026).
    if mod == "gorsel":
        giris_video = set()
    elif mod == "video":
        giris_video = set(range(1, len(cumleler) + 1))
    else:
        # GIRIS SINIRI: ilk %30 cumle KOSULSUZ video. En az 1 cumle.
        giris_adet = max(1, round(len(cumleler) * ACILIS_ORAN))
        giris_video = set(range(1, giris_adet + 1))
    plan = []
    if OPENAI_KEY:
        try:
            # ── STIL + KARAKTER + MOD talimatlari ──
            stil_blok = (
                f"\nSTYLE (MANDATORY): The visual style is FIXED by the user "
                f"and must be obeyed in EVERY prompt:\n  {stil}\n"
                "Build the style bible AROUND this. Never drift toward a "
                "different medium or look, not even for one shot.\n"
                if stil else "")

            # ⚠ KARAKTER TUTARLILIGI: Flow her prompt'u BAGIMSIZ uretir —
            # onceki kareyi hatirlamaz. Tek yol, karakterin AYNI kelimelerle
            # her prompt'ta yeniden tarif edilmesidir. "the same girl" gibi
            # geri gonderme calismaz, cunku referans yoktur.
            karakter_blok = (
                f"\nRECURRING MAIN CHARACTER (MANDATORY): the user's series "
                f"has one recurring character:\n  {karakter}\n"
                "STEP 1a — Turn this into ONE fixed, concrete visual "
                "description (age, build, face, hair, exact clothing and "
                "colors, any signature prop). Put it in the style bible.\n"
                "STEP 2a — Repeat that description WORD-FOR-WORD inside "
                "EVERY prompt where the character appears. The generator has "
                "NO memory between prompts: phrases like \"the same girl\", "
                "\"her again\" or \"as before\" DO NOT WORK and are "
                "forbidden. Write the full description every single time.\n"
                "The character should appear in MOST shots, doing whatever "
                "that specific sentence describes — reacting, watching, "
                "walking through the scene. If a sentence is purely abstract "
                "or a wide landscape where a person makes no sense, you may "
                "leave them out.\n"
                if karakter else "")

            if mod == "gorsel":
                tur_blok = ('Set "type" to "image" for EVERY item.\n')
            elif mod == "video":
                tur_blok = ('Set "type" to "video" for EVERY item and give '
                            'each one a camera move.\n')
            else:
                tur_blok = ('Choose type per sentence: "video" if motion is '
                            'essential to the meaning, else "image".\n')

            sistem = (
                "You are a film director turning a narration script into "
                "Google Flow generation prompts. The script may be in ANY "
                "language; UNDERSTAND it fully first.\n"
                + stil_blok + karakter_blok +
                "\nSTEP 1 — STYLE BIBLE: derive ONE consistent visual "
                "identity for the whole script: era, location feel, color "
                "palette, light character, lens or medium, texture, mood. "
                "Every shot must look like it came from the same production."
                "\n\nSTEP 2 — PER SENTENCE: write ONE ENGLISH prompt that "
                "depicts THAT sentence, structured as: [shot type] + "
                "subject + action + setting + lighting + lens/medium + mood, "
                "and ALWAYS ending with the style bible tokens so every "
                "shot matches. For type=video prompts ADD a camera move "
                "(slow dolly-in, tracking, aerial rise, handheld drift...). "
                "No text, no watermark, no captions, no subtitles in frame.\n"
                + tur_blok +
                '\nReturn JSON: {"style":"<style bible, one line>",'
                '"items":[{"i":<n>,"type":"video"|"image","prompt":"..."}]} '
                f"with EXACTLY {len(cumleler)} items, same numbering.")
            girdi = "\n".join(f"{i+1}. {c}" for i, c in enumerate(cumleler))
            cevap = json.loads(_oai([{"role": "system", "content": sistem},
                                     {"role": "user", "content": girdi}]))
            stil_kitabi = str(cevap.get("style", "")).strip()
            eslesme = {int(x["i"]): (str(x.get("prompt", "")).strip(),
                                     str(x.get("type", "")).strip().lower())
                       for x in cevap.get("items", []) if x.get("i")}
        except Exception as e:                               # noqa: BLE001
            stil_kitabi = ""
            eslesme = {}
            if bildir:
                bildir(f"⚠ LLM plani dusdu ({type(e).__name__}) — "
                       f"cumleler dogrudan prompt olarak kullanilacak")
    else:
        stil_kitabi = ""
        eslesme = {}
        if bildir:
            bildir("⚠ LLM anahtari yok — cumleler dogrudan prompt olacak")
    for i, cumle in enumerate(cumleler, 1):
        prompt, llm_tur = (eslesme.get(i) or ("", ""))
        # ⚠ LLM COKERSE: cumlenin kendisi prompt olur ama STIL ve KARAKTER
        # yine de eklenir — yoksa kullanicinin sectigi tarz tamamen kaybolur.
        if not prompt:
            parcalar = [cumle]
            if karakter:
                parcalar.append(f"featuring: {karakter}")
            parcalar.append(stil or "cinematic, photorealistic, "
                                    "natural light, 35mm")
            prompt = " — ".join(parcalar)
        if i in giris_video:
            tur = "video"                       # giris: KOSULSUZ video
        elif llm_tur in ("video", "image"):
            tur = "video" if llm_tur == "video" else "gorsel"
        else:
            tur = "gorsel"                      # LLM yoksa: giris-sonrasi gorsel
        plan.append({"sira": i, "cumle": cumle, "tur": tur, "prompt": prompt,
                     "stil": stil_kitabi or stil})
    return plan


def plan_ozeti(plan: list) -> str:
    """Kullaniciya gosterilecek tek satirlik kunye."""
    v = sum(1 for p in plan if p["tur"] == "video")
    g = len(plan) - v
    # ⚠ KURAL IDDIA ETME: satir bazinda "video:/gorsel:" ezmesi olabilir,
    # o yuzden "ilk %30" gibi bir kural iddia etmek YANILTIR. Sayilari ver.
    if not v:
        return f"{len(plan)} cümle → hepsi görsel"
    if not g:
        return f"{len(plan)} cümle → hepsi video"
    return f"{len(plan)} cümle → {v} video + {g} görsel"
