# 👻 HAYALET — Metin + Ses → CapCut Projesi (TAM PAKET)

> **NASIL KULLANILIR:** Bu dosyayı Claude Code'a at ve şunu yaz:
> **"Bu dosyadaki sistemi kur"**. Claude önce BÖLÜM 1'deki dosyaları
> aynen oluşturur, sonra BÖLÜM 2'deki kurulum adımlarını işletim
> sistemine göre uygular.
>
> Senden istenenler: kendi Telegram bot token'ın, Chrome'da Flow girişi,
> bir OpenAI anahtarı, kurulu bir CapCut (en az bir kayıtlı projeyle).

**🧠 `/senkron`** — Telegram'a **metin + seslendirme** verirsin; her cümle
için görsel/video üretilir, cümle sınırları **sesin kendisinden** çıkarılır
ve her cümle **ayrı klip** olarak CapCut zaman çizgisine dizilir. Sen
sadece geçiş/yazı/efekt eklersin.

**🎬 `/hikaye`** — promptları sen yazarsın, bot üretip indirir (kurgu yok).

> ⚠ Bu dosya **elle düzenlenmez**, `python3 -m hayalet.paylas_uret` ile
> üretilir. Kaynağı: `hayalet/KURULUM.md` + `hayalet/*.py`.

---

# BÖLÜM 1 — KOD (Claude: bu dosyaları AYNEN oluştur)

Boş klasör aç (ör. `~/hayalet-ajan`), içine `hayalet/` paketi:

## Dosya: `hayalet/__init__.py`
```python

```

## Dosya: `hayalet/ayar.py`
```python
#!/usr/bin/env python3
"""HAYALET — masaustu uretim ajani. AYARLAR.

⚠ SIR REPODA DEGIL: Telegram token ve diger sirlar `~/.hayalet/gizli.env`
dosyasindan okunur. Bu dosya git'e GIRMEZ.

Klasor duzeni (her is icin):
  ~/Desktop/Hayalet/<is_adi>/
      video/        Flow'dan inen video klipler (sirali)
      gorsel/       Flow'dan inen gorseller (sirali)
      is.json       islem kunyesi (prompt'lar, durum, hatalar)

⚠ KAPSAM: uretim (Flow) ile kurgu (ffmpeg) AYRI. `hayalet.kurgu` metin +
ses + cumle basina medyayi senkron tek videoya cevirir; renk/ses tasarimi
gibi ince islerde kullanici NLE'sine gecer.
"""
from __future__ import annotations

import os
from pathlib import Path

# ── Sir dosyasi (repo DISI) ──
GIZLI_DIZIN = Path.home() / ".hayalet"
GIZLI_ENV = GIZLI_DIZIN / "gizli.env"


def _gizli_yukle() -> None:
    """`~/.hayalet/gizli.env` -> ortam degiskeni. Dosya yoksa sessiz gecer."""
    if not GIZLI_ENV.exists():
        return
    for satir in GIZLI_ENV.read_text(encoding="utf-8").splitlines():
        satir = satir.strip()
        if not satir or satir.startswith("#") or "=" not in satir:
            continue
        ad, _, deger = satir.partition("=")
        os.environ.setdefault(ad.strip(), deger.strip())


_gizli_yukle()

TELEGRAM_TOKEN = os.environ.get("HAYALET_TELEGRAM_TOKEN", "")
# Yalnizca bu kullanici(lar) botu kullanabilir. Bos ise ILK yazan sahiplenir.
IZINLI_KULLANICILAR = [x.strip() for x in
                       os.environ.get("HAYALET_IZINLI", "").split(",") if x.strip()]

# ── Klasorler ──
KOK = Path(os.environ.get("HAYALET_KOK", str(Path.home() / "Desktop" / "Hayalet")))

# ── Flow (tarayici otomasyonu) ──
# ⚠ Kullanicinin KENDI Chrome'una baglaniriz: Google oturumu zaten aciktir.
# Chrome su bayrakla baslatilmali:  --remote-debugging-port=9222
CHROME_PORT = int(os.environ.get("HAYALET_CHROME_PORT", "9222"))
CHROME_CDP = os.environ.get("HAYALET_CHROME_CDP",
                            f"http://127.0.0.1:{CHROME_PORT}")
# ⚠ KALICI PROFIL: Flow oturumu burada durur. chrome_baslat.sh de, Playwright
# de AYNI dizini kullanir — boylece bir kez giris yapmak yeter.
CHROME_PROFIL = Path(os.environ.get(
    "HAYALET_CHROME_PROFIL", str(GIZLI_DIZIN / "chrome-profil")))

# ── SENIN GERCEK CHROME PROFILINI KULLANMA (istege bagli) ──
# ⚠ OLCULDU (21 Agu 2026): bir Chrome profilini kopyalayarak oturum TASINMAZ.
# macOS'ta cerez anahtari Keychain'de ve uygulamaya baglidir; kopyalanan
# profil Flow'da OTURUMSUZ acilir (tanitim sayfasi gelir). Iki gecerli yol:
#   A) IZOLE PROFIL (varsayilan): ~/.hayalet/chrome-profil icinde BIR KEZ
#      giris yaparsin. Gunluk Chrome'un acik kalabilir. Onerilen.
#   B) GERCEK PROFIL: asagidaki iki degeri doldur. O zaman gunluk Chrome'un
#      TAMAMEN KAPALI olmali (Chrome ayni veri dizinini iki surecle acmaz).
CHROME_ANA_DIZIN = os.environ.get("HAYALET_CHROME_ANA_DIZIN", "")
CHROME_PROFIL_ADI = os.environ.get("HAYALET_CHROME_PROFIL_ADI", "")
FLOW_URL = os.environ.get("HAYALET_FLOW_URL", "https://labs.google/fx/tools/flow")
# Tek uretimin en fazla bekleme suresi (sn). Veo klipleri dakikalar surebiliyor.
FLOW_URETIM_TAVAN_SN = int(os.environ.get("HAYALET_FLOW_TAVAN", "900"))

def is_dizini(is_adi: str) -> Path:
    """Is klasorunu KURAR ve doner."""
    d = KOK / is_adi
    for alt in ("video", "gorsel"):
        (d / alt).mkdir(parents=True, exist_ok=True)
    return d


def eksik_ayarlar() -> list:
    """Calistirmadan ONCE bilinmesi gerekenler — sessiz basarisizlik YOK."""
    eksik = []
    if not TELEGRAM_TOKEN:
        eksik.append("HAYALET_TELEGRAM_TOKEN (BotFather'dan alinip "
                     f"{GIZLI_ENV} icine yazilmali)")
    return eksik
```

## Dosya: `hayalet/beyin.py`
```python
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
```

## Dosya: `hayalet/flow_surucu.py`
```python
#!/usr/bin/env python3
"""FLOW SURUCUSU — kullanicinin KENDI Chrome'unda uretim + indirme.

⚠ NEDEN CDP (Chrome DevTools Protocol): Flow Google oturumu ister. Yeni bir
otomasyon tarayicisi acmak yeniden giris/2FA demek. Bunun yerine kullanicinin
ZATEN ACIK ve GIRIS YAPMIS Chrome'una BAGLANIRIZ:

    Chrome'u su bayrakla bir kez baslat:
      --remote-debugging-port=9222

⚠ SESSIZ BASARISIZLIK YASAK: her prompt icin sonuc {durum, dosya, neden}
olarak doner; is.json'a yazilir ve Telegram'a cikar.

⚠ SECICI KALIBRASYONU: Flow'un arayuzu degisebilir. `kesfet()` sayfadaki
girdi/dugme adaylarini DOKER; secici tablosu tek yerden (SECICILER)
guncellenir — kod dagilmaz.
"""
from __future__ import annotations

import os
import re
import shutil
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

from . import ayar

# ── SECICI TABLOSU — 20 Agu 2026 CANLI KALIBRASYON ──
# Flow'un yeni "agent" arayuzunde olculdu (proje: flow/project/<uuid>):
#   · Prompt girdisi: alttaki contenteditable DIV (sayfadaki SON tanesi)
#   · Gonder: "arrow_forward" ikonlu Create dugmesi (SON tanesi)
#   · Sonuc: genisligi >200px olan <img>/<video>; src
#     "labs.google/fx/api/trpc/media.getMediaUrlRedirect?..." seklinde
#   · Indirme: sayfa baglaminda fetch (oturum cerezleri gecerli) — OLCULDU,
#     773KB PNG indi. Ayri indirme dugmesi GEREKMEZ.
# ⚠ ON KOSUL (bir kez, elle): proje icinde Agent settings ->
#   "Confirm before generating: NEVER" + Image x1. Aksi halde ajan HER
#   promptta onay sorar ve otomasyon takilir (KURULUM.md Adim 5.5).
SECICILER = {
    "prompt_girdi": ["div[contenteditable='true']"],
    "temizle_dugme": ["button:has-text('Clear prompt')"],
    "uret_dugme": ["button:has-text('arrow_forward')"],
}

# ⚠ CIKTI ORANI FLOW AYARINDADIR, PROMPTTA DEGIL (21 Agu 2026 olcumu):
# prompta "16:9" yazmak yetmez; Flow projesinin kendi oran secimi neyse ona
# gore uretir. Varsayilan 9:16 (dikey) gelebiliyor ve tum is dikey cikiyor.
# Panelde oranlar `role=tab` butonlaridir; ikon adi benzersizdir
# (crop_16_9 / crop_9_16), metne gore secmek guvenlidir.
ORAN_IKON = {"16:9": "crop_16_9", "9:16": "crop_9_16"}
# ⚠ CIKTI TURU DE FLOW AYARIDIR (21 Agu 2026): panelde Image/Video sekmeleri
# vardir ve secili olan KAZANIR. Prompta "Generate one image:" yazmak
# YETMEZ — tur "Video"da kaliyorsa gorsel istenen cumleler bile VIDEO cikar
# (kullanicinin yasadigi hata). Her partiden once tur de ayarlanir.
TUR_IKON = {"gorsel": "image", "video": "videocam"}
ORAN = __import__("os").environ.get("HAYALET_ORAN", "16:9")


def _ayar_cipi(sayfa):
    return sayfa.locator("button").filter(has_text="crop_").first


def _panel_ac(sayfa) -> bool:
    """Ayar panelini ACAR. Zaten aciksa DOKUNMAZ.

    ⚠ Cipe korlemesine tiklamak, panel ZATEN ACIKSA onu KAPATIR — bu tuzaga
    bir kez dusuldu. Once sekmeler gorunur mu diye bakilir.
    """
    sek = sayfa.locator("button[role='tab']")
    try:
        if sek.count() and sek.first.is_visible():
            return True
        _ayar_cipi(sayfa).click()
        sayfa.wait_for_timeout(1500)
        return sayfa.locator("button[role='tab']").count() > 0
    except Exception:                                    # noqa: BLE001
        return False


def _sekme_sec(sayfa, ikon: str) -> bool:
    """Ayar panelindeki `role=tab` butonlarindan ikonu eslesen KAZANIR."""
    if not _panel_ac(sayfa):
        return False
    sek = sayfa.locator(f"button[role='tab']:has-text('{ikon}')")
    if not sek.count():
        return False
    b = sek.first
    if (b.get_attribute("aria-selected") or "").lower() == "true":
        return True                                      # zaten secili
    b.click()
    sayfa.wait_for_timeout(1500)
    return (sayfa.locator(f"button[role='tab']:has-text('{ikon}')").first
            .get_attribute("aria-selected") or "").lower() == "true"


# ⚠ IKI FARKLI FLOW ARAYUZU (23 Agu 2026 olcumu):
#   A) ESKI: prompt kutusunun yaninda gorunur cip — "Video · 720p · 10s
#      crop_16_9 x1". Tiklayinca sekmeler acilir.
#   B) YENI: cip YOK; ayarlar `tune|Ayarlar` dugmesinin arkasindaki
#      "Ajan ayarlari" panelinde. Orada AYRICA iki tuzak var:
#        · "Uretme isleminden once onaylayin: Her zaman" → ajan HER promptta
#          onay sorar, otomasyon TAKILIR. "Hicbir zaman" olmali.
#        · "Varsayilan goruntu uretimi: x2" → her promptta 2 gorsel,
#          IKI KATI KREDI. x1 olmali.
# Panelde oran sekmeleri hem gorsel hem video icin AYRI AYRI durur; ikisi de
# ayarlanir.

def _ayar_paneli_ac(sayfa) -> bool:
    """Ayar panelini acar (her iki arayuz turunde). Aciksa dokunmaz."""
    try:
        sek = sayfa.locator("button[role='tab']")
        if sek.count() and sek.first.is_visible():
            return True
    except Exception:                                        # noqa: BLE001
        pass
    for sec in ("button:has-text('tune')",):                 # B) yeni arayuz
        try:
            o = sayfa.locator(sec).first
            if o.count():
                o.click(timeout=8000)
                sayfa.wait_for_timeout(2000)
                if sayfa.locator("button[role='tab']").count():
                    return True
        except Exception:                                    # noqa: BLE001
            pass
    try:                                                     # A) eski cip
        sayfa.locator("button").filter(has_text="crop_").first.click(timeout=6000)
        sayfa.wait_for_timeout(1500)
        return sayfa.locator("button[role='tab']").count() > 0
    except Exception:                                        # noqa: BLE001
        return False


def _tum_sekmeleri_sec(sayfa, ikon: str) -> int:
    """Ikonu eslesen TUM sekmeleri secer (gorsel ve video ayri ayri)."""
    sec = sayfa.locator(f"button[role='tab']:has-text('{ikon}')")
    n = 0
    for i in range(sec.count()):
        b = sec.nth(i)
        try:
            if (b.get_attribute("aria-selected") or "").lower() == "true":
                continue
            b.click(timeout=8000)
            sayfa.wait_for_timeout(700)
            n += 1
        except Exception:                                    # noqa: BLE001
            pass
    return n


def flow_ayarla(sayfa, tur: str = "gorsel", oran: str = None, bildir=None) -> bool:
    """Uretimden ONCE Flow ayarlarini garantiye alir.

    Yapilanlar: onay=Hicbir zaman · adet=x1 · oran=16:9 (gorsel+video) ·
    (eski arayuzde ayrica Image/Video tur sekmesi).
    """
    oran = oran or ORAN
    ikon = ORAN_IKON.get(oran, "crop_16_9")
    if not _ayar_paneli_ac(sayfa):
        if bildir:
            bildir("⚠ Flow ayar paneli acilamadi — ayarlar elle kontrol edilmeli")
        return False
    notlar = []
    # 1) Onay kapali olmali, yoksa ajan her promptta bekletir.
    for etiket in ("Hiçbir zaman", "Never"):
        try:
            o = sayfa.locator(f"text={etiket}").first
            if o.count():
                o.click(timeout=6000)
                sayfa.wait_for_timeout(700)
                notlar.append("onay=kapali")
                break
        except Exception:                                    # noqa: BLE001
            pass
    # 2) Prompt basina TEK cikti (x2 = iki kati kredi).
    if _tum_sekmeleri_sec(sayfa, "x1"):
        notlar.append("adet=x1")
    # 3) Oran.
    if _tum_sekmeleri_sec(sayfa, ikon):
        notlar.append(f"oran={oran}")
    # 4) Eski arayuzde cikti turu sekmesi de var.
    t_ikon = TUR_IKON.get(tur)
    if t_ikon and _tum_sekmeleri_sec(sayfa, t_ikon):
        notlar.append(f"tur={tur}")
    # ⚠ PANELDEN CIKIS: yeni arayuzde ayarlar prompt gorunumunun YERINE
    # aciliyor; Escape her zaman geri getirmiyor. Prompt kutusu yoksa
    # "Geri" dugmesine basiyoruz — aksi halde her partide sayfa yenilenip
    # ~40 sn bosa gidiyordu.
    try:
        sayfa.keyboard.press("Escape")
        sayfa.wait_for_timeout(800)
    except Exception:                                        # noqa: BLE001
        pass
    # ⚠ "Geri" DUGMESINE TIKLAMA: sol ustteki `arrow_back|Geri Dön`
    # projeden TAMAMEN CIKIYOR (denendi, 0/3 uretim). Proje adresine
    # dogrudan gitmek tek guvenli yol.
    if not _prompt_kutusu_var(sayfa, 4000):
        try:
            sayfa.goto(ayar.FLOW_URL, wait_until="domcontentloaded",
                       timeout=60000)
            sayfa.wait_for_timeout(6000)
            _prompt_kutusu_var(sayfa, 20000)
        except Exception:                                    # noqa: BLE001
            pass
    if bildir:
        bildir("⚙ Flow ayarlari: " + (", ".join(notlar) if notlar
                                       else "zaten dogru"))
    return True


def oran_ayarla(sayfa, oran: str = None, bildir=None) -> bool:
    """Flow'un cikti oranini ayarlar. Zaten dogruysa DOKUNMAZ."""
    oran = oran or ORAN
    ikon = ORAN_IKON.get(oran)
    if not ikon:
        return False
    try:
        if ikon in (_ayar_cipi(sayfa).inner_text() or ""):
            return True                                  # cip zaten dogru
        oldu = _sekme_sec(sayfa, ikon)
        sayfa.keyboard.press("Escape")
        sayfa.wait_for_timeout(800)
        if bildir:
            bildir(f"{'✓' if oldu else '⚠'} cikti orani {oran}"
                   f"{'' if oldu else ' AYARLANAMADI'}")
        return oldu
    except Exception as e:                               # noqa: BLE001
        if bildir:
            bildir(f"⚠ oran ayarlanamadi ({type(e).__name__})")
        return False


def tur_ayarla(sayfa, tur: str, bildir=None) -> bool:
    """Flow'un CIKTI TURUNU (Image / Video) ayarlar.

    ⚠ BU OLMADAN "gorsel" istegi VIDEO cikar: Flow'un tur sekmesi neyse o
    uretilir, promptaki "Generate one image:" ifadesi bunu EZMEZ.
    """
    ikon = TUR_IKON.get(tur)
    if not ikon:
        return False
    try:
        oldu = _sekme_sec(sayfa, ikon)
        sayfa.keyboard.press("Escape")
        sayfa.wait_for_timeout(800)
        if bildir:
            bildir(f"{'✓' if oldu else '⚠'} cikti turu "
                   f"{'GORSEL' if tur == 'gorsel' else 'VIDEO'}"
                   f"{'' if oldu else ' AYARLANAMADI'}")
        return oldu
    except Exception as e:                               # noqa: BLE001
        if bildir:
            bildir(f"⚠ tur ayarlanamadi ({type(e).__name__})")
        return False


# Ajan arayuzu TUR bilgisini prompttan alir — onek sozlesmesi:
TUR_ONEK = {"video": "Generate one video: ",
            "gorsel": "Generate one image: "}


class FlowHatasi(RuntimeError):
    """Flow tarafinda cozulemeyen durum — SESSIZ GECILMEZ."""


def _ilk_gorunur(sayfa, adaylar: list, zaman_asimi: int = 8000):
    """Aday secicilerden ilk GORUNUR olani dondur; yoksa None."""
    for s in adaylar:
        try:
            oge = sayfa.locator(s).first
            oge.wait_for(state="visible", timeout=zaman_asimi)
            return oge
        except Exception:
            continue
    return None


def _profil_chromeu_kapat(bildir=None) -> int:
    """SADECE Hayalet profilini kullanan Chrome'u kapatir. Kac tane, doner.

    ⚠ Kullanicinin gunluk Chrome'una DOKUNMAZ: eslesme `--user-data-dir=
    <hayalet profili>` uzerinden yapilir, o profil yalnizca bu ajanindir.
    """
    import signal
    import subprocess
    # ⚠ BASTAKI IKI TIRE YOK: `pgrep -f --user-data-dir=...` cagrisinda
    # pgrep bunu KENDI SECENEGI sanip hicbir sey bulamaz (sessizce 0 doner).
    isaret = f"user-data-dir={ayar.CHROME_PROFIL}"
    try:
        cikti = subprocess.run(["pgrep", "-f", isaret],
                               capture_output=True, text=True).stdout
    except Exception:                                        # noqa: BLE001
        return 0
    pidler = [int(x) for x in cikti.split() if x.strip().isdigit()
              and int(x) != os.getpid()]
    for pid in pidler:
        try:
            os.kill(pid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            pass
    for _ in range(20):
        if not any(_yasiyor(p) for p in pidler):
            break
        time.sleep(0.25)
    for pid in pidler:
        if _yasiyor(pid):
            try:
                os.kill(pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
    if pidler and bildir:
        bildir(f"↻ Chrome yeniden baslatiliyor ({len(pidler)} pencere kapatildi)")
    return len(pidler)


def _chrome_kullaniyor_mu(veri_dizini: str) -> bool:
    """O veri dizinini kullanan bir Chrome sureci var mi?"""
    import subprocess
    # pgrep kalibinda BASTAKI TIRELER OLMAZ (seçenek sanilir).
    r = subprocess.run(["pgrep", "-f", f"user-data-dir={veri_dizini}"],
                       capture_output=True, text=True)
    if [x for x in r.stdout.split() if x.strip()]:
        return True
    # Varsayilan dizinde acilan Chrome komut satirinda --user-data-dir TASIMAZ.
    varsayilan = os.path.expanduser(
        "~/Library/Application Support/Google/Chrome")
    if os.path.abspath(veri_dizini) == os.path.abspath(varsayilan):
        r = subprocess.run(["pgrep", "-f", "MacOS/Google Chrome"],
                           capture_output=True, text=True)
        for pid in [x for x in r.stdout.split() if x.strip()]:
            k = subprocess.run(["ps", "-p", pid, "-o", "command="],
                               capture_output=True, text=True).stdout
            if "MacOS/Google Chrome" in k and "user-data-dir=" not in k:
                return True
    return False


def _yasiyor(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _baska_hayalet_var_mi() -> int:
    """Baska bir Hayalet sureci Chrome'u kullaniyor mu? PID doner, yoksa 0.

    ⚠ OLCULDU (22 Agu 2026): calisan bot varken ikinci bir surec baglanmaya
    kalkinca `_profil_chromeu_kapat` botun tarayicisini KAPATTI ve calisan
    is yarida oldu. Iki surec ayni profili paylasamaz.
    """
    import subprocess
    r = subprocess.run(["pgrep", "-f", "hayalet.bot"],
                       capture_output=True, text=True)
    for x in r.stdout.split():
        if x.strip().isdigit() and int(x) != os.getpid():
            return int(x)
    return 0


def chrome_baglan(bildir=None):
    """(playwright, baglam) doner. Baglam bir BrowserContext'tir.

    ⚠ IKI YOL, SIRAYLA (21 Agu 2026 olcumu):
      1) connect_over_cdp — zaten acik Chrome'a baglanir. ESKI CHROME'LARDA
         calisir; Chrome 151 + Playwright 1.60'ta ARTIK CALISMIYOR:
            Protocol error (Browser.setDownloadBehavior):
            Browser context management is not supported.
         Playwright 1.60 en yeni surum, guncelleme cozmuyor.
      2) launch_persistent_context(channel="chrome") — Playwright Chrome'u
         KENDISI baslatir. Chrome 151'de calistigi OLCULDU. Ayni kalici
         profili kullandigi icin Flow oturumu korunur.
    Chrome o profille zaten acikken (2) baslatilamaz — once o pencere
    kapatilir; oturum profilde durdugu icin giris kaybolmaz.
    """
    baska = _baska_hayalet_var_mi()
    if baska and os.environ.get("HAYALET_KILIT_YOKSAY") != "1":
        raise FlowHatasi(
            f"Baska bir Hayalet sureci calisiyor (pid {baska}) ve Chrome'u "
            "kullaniyor.\nIki surec ayni tarayici profilini paylasamaz — "
            "devam edersem calisan isi yarida keserim.\n"
            "Once onu durdur (pencereyi kapat), sonra tekrar dene.\n"
            "Bilerek gecmek istersen: HAYALET_KILIT_YOKSAY=1")
    pw = sync_playwright().start()
    # ⚠ `except ... as e` degiskeni blok SONUNDA SILINIR (Python 3);
    # nedeni disariya tasimak icin ayri bir degiskene kopyalanir.
    cdp_hata = ""
    try:
        tarayici = pw.chromium.connect_over_cdp(ayar.CHROME_CDP)
        baglam = (tarayici.contexts[0] if tarayici.contexts
                  else tarayici.new_context())
        return pw, baglam
    except Exception as e:                                   # noqa: BLE001
        cdp_hata = f"{type(e).__name__}: {e}"

    bayraklar = ["--no-first-run", "--no-default-browser-check",
                 f"--remote-debugging-port={ayar.CHROME_PORT}"]
    if ayar.CHROME_ANA_DIZIN:
        # B YOLU: kullanicinin GERCEK Chrome profili (ornegin "Profile 48").
        # ⚠ Gunluk Chrome ACIKKEN olmaz — Chrome ayni veri dizinini iki
        # surecle acamaz. Bunu SESSIZCE denemek yerine NET soyluyoruz.
        veri_dizini = ayar.CHROME_ANA_DIZIN
        if _chrome_kullaniyor_mu(veri_dizini):
            pw.stop()
            raise FlowHatasi(
                "Gunluk Chrome'un ACIK ve senin gercek profilini kullanmak "
                "icin ayarlanmis durumda.\n"
                f"  veri dizini : {veri_dizini}\n"
                f"  profil      : {ayar.CHROME_PROFIL_ADI or 'Default'}\n\n"
                "Chrome ayni veri dizinini iki surecle acamaz. Ya Chrome'u "
                "TAMAMEN kapat, ya da izole profile don:\n"
                "  ~/.hayalet/gizli.env icinden HAYALET_CHROME_ANA_DIZIN "
                "satirini sil ve izole profilde bir kez Flow'a giris yap.")
        if ayar.CHROME_PROFIL_ADI:
            bayraklar.append(f"--profile-directory={ayar.CHROME_PROFIL_ADI}")
    else:
        veri_dizini = str(ayar.CHROME_PROFIL)
        _profil_chromeu_kapat(bildir)
    try:
        baglam = pw.chromium.launch_persistent_context(
            veri_dizini, channel="chrome", headless=False, args=bayraklar,
            # ⚠ BU IKI BAYRAK KALKMAZSA OTURUM ACILMAZ (21 Agu 2026 olcumu):
            # Playwright macOS'ta varsayilan olarak `--use-mock-keychain` ve
            # `--password-store=basic` ekler. Bunlar Chrome'un Keychain'deki
            # cerez sifreleme anahtarina ulasmasini engeller; cerezler diskte
            # DURUR ama COZULEMEZ, sayfa oturumsuz acilir (Flow'da tanitim
            # sayfasi gelir). Elle baslatilan Chrome'da sorun cikmamasinin
            # sebebi de budur.
            ignore_default_args=["--use-mock-keychain",
                                 "--password-store=basic"])
        return pw, baglam
    except Exception as e:                                   # noqa: BLE001
        pw.stop()
        raise FlowHatasi(
            "Chrome baslatilamadi.\n"
            f"· CDP baglantisi olmadi: {cdp_hata[:140]}\n"
            f"· Playwright de baslatamadi: {type(e).__name__}: {str(e)[:120]}\n"
            "Google Chrome kurulu mu? `bash hayalet/chrome_baslat.sh` ile "
            "elle acip Flow'a giris yapmayi dene.")


def kesfet(cikti: Path = None, bildir=None) -> dict:
    """TESHIS: Flow sayfasindaki girdi/dugme adaylarini doker.

    Secici tablosu kirildiginda ONCE bu calistirilir; ciktidan `SECICILER`
    guncellenir. Boylece 'neden calismiyor' korlemesine aranmaz.
    """
    pw, baglam = chrome_baglan(bildir)
    try:
        sayfa = _flow_sayfasi(baglam, dogrula=False)   # teshis: hata verme
        rapor = {"url": sayfa.url, "basliklar": [], "textarea": [], "dugme": []}
        for etiket, sec in (("textarea", "textarea, div[contenteditable='true']"),
                            ("dugme", "button")):
            for i in range(min(40, sayfa.locator(sec).count())):
                o = sayfa.locator(sec).nth(i)
                try:
                    if not o.is_visible():
                        continue
                    rapor[etiket].append({
                        "metin": (o.inner_text() or "")[:40],
                        "aria": o.get_attribute("aria-label") or "",
                        "placeholder": o.get_attribute("placeholder") or "",
                    })
                except Exception:
                    continue
        if cikti:
            import json
            cikti.write_text(json.dumps(rapor, ensure_ascii=False, indent=2),
                             encoding="utf-8")
        return rapor
    finally:
        pw.stop()


def _flow_sayfasi(baglam, dogrula: bool = True):
    """Acik sekmelerde Flow varsa ONU kullan; yoksa yeni sekmede ac.

    ⚠ PROJE URL'i SART: prompt kutusu Flow'un GIRIS sayfasinda degil, bir
    PROJENIN icinde bulunur (labs.google/fx/tools/flow/project/<uuid>).
    Eskiden kullanicinin zaten acik projesine baglaniyorduk; artik Chrome'u
    Playwright baslattigi icin taze sekme GIRIS sayfasina duser ve prompt
    kutusu bulunamaz. O durumda 15 dakika bosuna beklemek yerine NE
    YAPILACAGINI soyleyip duruyoruz.
    """
    for s in baglam.pages:
        if "labs.google" in (s.url or ""):
            s.bring_to_front()
            if not dogrula or _prompt_kutusu_var(s):
                return s
            break
    sayfa = baglam.new_page()
    sayfa.goto(ayar.FLOW_URL, wait_until="domcontentloaded", timeout=60000)
    if dogrula and not _prompt_kutusu_var(sayfa):
        raise FlowHatasi(
            "Flow acildi ama PROMPT KUTUSU bulunamadi — muhtemelen bir "
            "PROJENIN icinde degiliz.\n"
            f"Su an: {sayfa.url[:90]}\n\n"
            "Yapilacak (bir kez):\n"
            "1) Acilan Chrome'da Flow'da bir proje ac (New project)\n"
            "2) Adres cubugundaki .../flow/project/<uuid> adresini kopyala\n"
            "3) ~/.hayalet/gizli.env icine ekle:\n"
            "   HAYALET_FLOW_URL=<kopyaladigin adres>\n"
            "4) Botu yeniden baslat\n\n"
            "Giris yapilmamis olabilir de — acilan pencereden Google "
            "hesabina gir.")
    return sayfa


def _prompt_kutusu_var(sayfa, zaman_asimi: int = 12000) -> bool:
    """Prompt girdisi gorunur mu? Proje ici mi, giris sayfasi mi ayirir."""
    try:
        sayfa.locator(SECICILER["prompt_girdi"][0]).last.wait_for(
            state="visible", timeout=zaman_asimi)
        return True
    except Exception:                                        # noqa: BLE001
        return False


def _dosya_adi(sira: int, tur: str, prompt: str, uzanti: str) -> str:
    """Sirali + okunabilir ad: 003_gorsel_bir-adam-sahilde.png"""
    slug = re.sub(r"[^a-z0-9]+", "-", prompt.lower())[:40].strip("-") or "kare"
    return f"{sira:03d}_{tur}_{slug}{uzanti}"


def _medya_srcleri(sayfa, tur: str) -> set:
    """Sayfadaki medya src'leri.

    ⚠ OLCULEN KUSUR (20 Agu 2026, ilk video testi): uretilen <video>
    elementi DOM'da 0 PIKSEL genislikte durabiliyor (gorunmez kapsayici);
    ">200px" filtresi onu ELEYIP testi timeout'a dusurdu — video aslinda
    URETILMISTI. Video icin boyut filtresi YOK, src varligi yeter.
    Gorselde filtre durur: kucuk ikon/avatar img'leri elemek icin.
    """
    if tur == "video":
        return set(sayfa.evaluate(
            """() => [...document.querySelectorAll('video')]
                 .map(e => e.currentSrc || e.src || '')
                 .filter(u => u.length > 30)"""))
    return set(sayfa.evaluate(
        """() => [...document.querySelectorAll('img')].filter(e => {
             const r = e.getBoundingClientRect();
             return r.width > 200 && (e.currentSrc || e.src || '').length > 30;
           }).map(e => e.currentSrc || e.src)"""))


def uret_ve_indir(prompt: str, tur: str, sira: int, hedef_dizin: Path,
                  bildir=None) -> dict:
    """TEK prompt -> Flow agent'inda uret -> sayfa ici fetch ile indir.

    ⚠ YENI-SRC AYRIMI (kritik): ayni oturumda onceki uretimler DOM'da
    kalir. Gonderim ONCESI mevcut src kumesi alinir; yalnizca YENI beliren
    src indirilir. Bu olmadan hep ILK sonuc indirilirdi.
    Doner: {"ok": bool, "dosya": str, "neden": str}
    """
    def _bildir(m):
        if bildir:
            try:
                bildir(m)
            except Exception:
                pass

    pw = None
    try:
        pw, baglam = chrome_baglan(bildir)
        sayfa = _flow_sayfasi(baglam)
        # ⚠ HER PARTIDEN ONCE TUR VE ORANI DOGRULA: ikisi de Flow projesinde
        # saklanir; yanlis kalirsa tum is yanlis turde/oranda cikar
        # (gorsel istenirken video, 16:9 isterken dikey geldi).
        flow_ayarla(sayfa, tur, bildir=bildir)
        onceki = _medya_srcleri(sayfa, tur)

        # temizle + yaz + gonder
        try:
            sayfa.locator(SECICILER["temizle_dugme"][0]).first.click(timeout=2000)
        except Exception:
            pass
        girdi = sayfa.locator(SECICILER["prompt_girdi"][0]).last
        girdi.click()
        girdi.type(TUR_ONEK.get(tur, "") + prompt, delay=5)
        sayfa.locator(SECICILER["uret_dugme"][0]).last.click()
        _bildir(f"[{sira}] uretiliyor: {prompt[:50]}…")

        # YENI medya bekle
        bas = time.time()
        kaynak = ""
        while time.time() - bas < ayar.FLOW_URETIM_TAVAN_SN:
            time.sleep(5)
            yeni = _medya_srcleri(sayfa, tur) - onceki
            if yeni:
                kaynak = sorted(yeni)[0]
                break
        if not kaynak:
            return {"ok": False, "dosya": "",
                    "neden": f"{ayar.FLOW_URETIM_TAVAN_SN} sn icinde YENI "
                             f"{tur} gorunmedi (uretim uzun ya da hata)"}

        # sayfa baglaminda fetch (oturum cerezleri) — 20 Agu'da OLCULDU
        b64 = sayfa.evaluate(
            """async (u) => {
                const r = await fetch(u);
                const b = await r.arrayBuffer();
                let s = ''; const v = new Uint8Array(b);
                const parca = 0x8000;
                for (let i = 0; i < v.length; i += parca)
                    s += String.fromCharCode.apply(null, v.subarray(i, i + parca));
                return btoa(s);
            }""", kaynak)
        import base64 as _b64
        veri = _b64.b64decode(b64)
        if len(veri) < 5000:
            return {"ok": False, "dosya": "",
                    "neden": f"indirilen dosya supheli kucuk ({len(veri)} bayt)"}
        uzanti = ".mp4" if tur == "video" else ".png"
        hedef = hedef_dizin / _dosya_adi(sira, tur, prompt, uzanti)
        tmp = str(hedef) + ".tmp"
        Path(tmp).write_bytes(veri)
        Path(tmp).rename(hedef)
        _bildir(f"[{sira}] indi -> {hedef.name} ({len(veri)//1024} KB)")
        return {"ok": True, "dosya": str(hedef), "neden": ""}
    except FlowHatasi as e:
        return {"ok": False, "dosya": "", "neden": str(e)}
    except Exception as e:                                   # noqa: BLE001
        return {"ok": False, "dosya": "",
                "neden": f"{type(e).__name__}: {str(e)[:120]}"}
    finally:
        if pw is not None:
            try:
                pw.stop()
            except Exception:
                pass


# ⚠ OLCULDU (22 Agu 2026, 183 promptluk gercek is): parti basina 10 prompt
# gonderildiginde Flow ajani parti basina YALNIZCA 1 gorsel uretiyor. Kalan 9
# hic gelmiyor, bot tavan dolana kadar (45 dk) bosuna bekliyor ve sonraki
# partiye geciyor. 2 saatte 183 gorselden 2 tanesi indi.
# Bu yuzden VARSAYILAN 1: her prompt AYRI gonderilir. Daha yavas gorunur ama
# gercekte kat kat hizlidir, cunku bos bekleme olmaz.
PARTI_BOYU = int(__import__("os").environ.get("HAYALET_PARTI", "1"))

# Tek uretimin makul bekleme suresi. Gorsel saniyeler surer; video dakikalar.
# ⚠ Cok uzun tavan = hata durumunda saatlerce bosuna bekleme.
TEK_TAVAN_SN = {"gorsel": int(__import__("os").environ.get("HAYALET_GORSEL_TAVAN", "240")),
                "video": int(__import__("os").environ.get("HAYALET_VIDEO_TAVAN", "900"))}


def parti_uret(promptlar: list, tur: str, hedef_dizin: Path, bildir=None,
               iptal_mi=None, indi_cb=None, siralar: list = None) -> list:
    """PROMPTLARI 10'AR VERIP ciktilari BELIRDIKCE indirir (ajan modu).

    ⚠ NEDEN PARTI: ajan arayuzu sohbet tabanli — tek mesajda numarali N
    prompt verilebilir; ajan SIRAYLA uretir. Tek tek gondermeye gore cok
    daha hizli (her prompt icin ayri baglanti+bekleme yok).
    ⚠ ESLEME SINIRI (durust): cikti->prompt eslesmesi BELIRME SIRASIYLA
    yapilir; ajan sirayi bozarsa dosya adi yanlis prompta denk gelebilir.
    Icerik DOGRU iner; yalnizca adlandirma kayabilir. is.json'da parti
    kaydi tutulur.

    `siralar`: her promptun GERCEK CUMLE NUMARASI. Verilmezse liste ici
    sira (1..n) kullanilir.
    ⚠ SENKRON MODU ICIN SART: video ve gorsel promptlari AYRI listelere
    bolundugu icin liste-ici sira cumle numarasindan farklidir; dosya adi
    (007_video_...) cumle 7'yi gostermezse CapCut dizilimi kayar.
    """
    def _bildir(m):
        if bildir:
            try:
                bildir(m)
            except Exception:
                pass

    temiz = [((siralar[i] if siralar else i + 1), (p or "").strip())
             for i, p in enumerate(promptlar) if (p or "").strip()]
    if not temiz:
        return []
    sonuclar = []
    partiler = [temiz[i:i + PARTI_BOYU] for i in range(0, len(temiz), PARTI_BOYU)]
    pw = None
    try:
        pw, baglam = chrome_baglan(bildir)
        sayfa = _flow_sayfasi(baglam)
        # ⚠ HER PARTIDEN ONCE TUR VE ORANI DOGRULA: ikisi de Flow projesinde
        # saklanir; yanlis kalirsa tum is yanlis turde/oranda cikar
        # (gorsel istenirken video, 16:9 isterken dikey geldi).
        flow_ayarla(sayfa, tur, bildir=bildir)
        for p_no, parti in enumerate(partiler, 1):
            if iptal_mi is not None and iptal_mi():
                _bildir("🛑 iptal edildi")
                break
            onceki = _medya_srcleri(sayfa, tur)
            tur_ad = "videos" if tur == "video" else "images"
            if len(parti) == 1:
                # Tek prompt: ajanla pazarlik yok, dogrudan uretim istegi.
                mesaj = TUR_ONEK.get(tur, "") + parti[0][1]
            else:
                mesaj = (f"Generate {len(parti)} separate {tur_ad}, one for each "
                         f"numbered prompt below. Do not ask questions, do not "
                         f"combine them, generate all:\n"
                         + "\n".join(f"{i}. {p}" for i, p in parti))
            try:
                sayfa.locator(SECICILER["temizle_dugme"][0]).first.click(timeout=2000)
            except Exception:
                pass
            # ⚠ ARAYUZ KAYBOLABILIR (22 Agu 2026): 147. promptta prompt
            # kutusu yok oldu, Locator.click 30 sn sonra TimeoutError atti ve
            # TUM is oldu. Artik once kutu var mi diye bakilir; yoksa sayfa
            # YENILENIR ve bir kez daha denenir.
            if not _prompt_kutusu_var(sayfa, 8000):
                _bildir("⟳ prompt kutusu kayboldu — sayfa yenileniyor")
                try:
                    sayfa.reload(wait_until="domcontentloaded", timeout=60000)
                    sayfa.wait_for_timeout(6000)
                except Exception:                            # noqa: BLE001
                    pass
                if not _prompt_kutusu_var(sayfa, 20000):
                    _bildir("⚠ prompt kutusu yenilemeden sonra da yok — "
                            "kalan promptlar atlaniyor")
                    break
                flow_ayarla(sayfa, tur, bildir=bildir)
            girdi = sayfa.locator(SECICILER["prompt_girdi"][0]).last
            girdi.click(timeout=15000)
            # type() cok satirda Enter'i GONDER sanabilir -> panoya benzer insert
            sayfa.keyboard.insert_text(mesaj)
            sayfa.locator(SECICILER["uret_dugme"][0]).last.click(timeout=15000)
            _bildir(f"📦 parti {p_no}/{len(partiler)}: {len(parti)} prompt gonderildi")

            beklenen = len(parti)
            inen = {}
            bas = time.time()
            tavan = TEK_TAVAN_SN.get(tur, 240) * max(1, beklenen)
            while len(inen) < beklenen and time.time() - bas < tavan:
                if iptal_mi is not None and iptal_mi():
                    break
                time.sleep(6)
                yeniler = sorted(_medya_srcleri(sayfa, tur) - onceki
                                 - set(inen))
                for kaynak in yeniler:
                    sira, prompt = parti[min(len(inen), beklenen - 1)]
                    try:
                        b64 = sayfa.evaluate(
                            """async (u) => {
                                const r = await fetch(u);
                                const b = await r.arrayBuffer();
                                let s = ''; const v = new Uint8Array(b);
                                const k = 0x8000;
                                for (let i = 0; i < v.length; i += k)
                                    s += String.fromCharCode.apply(null, v.subarray(i, i + k));
                                return btoa(s);
                            }""", kaynak)
                        import base64 as _b64
                        veri = _b64.b64decode(b64)
                        if len(veri) < 5000:
                            continue
                        uzanti = ".mp4" if tur == "video" else ".png"
                        hedef = hedef_dizin / _dosya_adi(sira, tur, prompt, uzanti)
                        hedef.write_bytes(veri)
                        inen[kaynak] = str(hedef)
                        kayit = {"ok": True, "dosya": str(hedef),
                                 "neden": "", "prompt": prompt,
                                 "sira": sira, "tur": tur}
                        sonuclar.append(kayit)
                        _bildir(f"✅ {tur} {len(sonuclar)}/{len(temiz)} indi "
                                f"— devam ediyorum")
                        if indi_cb is not None:
                            try:
                                indi_cb(kayit)     # SENKRON: medya+cumle teslimi
                            except Exception:
                                pass
                    except Exception as e:                   # noqa: BLE001
                        _bildir(f"⚠ indirme hatasi: {type(e).__name__}")
            eksik = beklenen - sum(1 for r in sonuclar
                                   if r["sira"] in [x[0] for x in parti])
            for sira, prompt in parti:
                if not any(r["sira"] == sira and r["tur"] == tur
                           for r in sonuclar):
                    sonuclar.append({"ok": False, "dosya": "",
                                     "neden": "parti tavaninda uretilmedi",
                                     "prompt": prompt, "sira": sira,
                                     "tur": tur})
            if eksik > 0:
                _bildir(f"⚠ parti {p_no}: {eksik} cikti gelmedi (kayitli)")
    except FlowHatasi as e:
        for sira, prompt in temiz:
            if not any(r["sira"] == sira for r in sonuclar):
                sonuclar.append({"ok": False, "dosya": "", "neden": str(e),
                                 "prompt": prompt, "sira": sira, "tur": tur})
    finally:
        if pw is not None:
            try:
                pw.stop()
            except Exception:
                pass
    return sonuclar


TEKRAR = int(__import__("os").environ.get("HAYALET_TEKRAR", "2"))


def uret_tekrarli(promptlar: list, tur: str, hedef_dizin: Path, bildir=None,
                  iptal_mi=None, indi_cb=None, siralar: list = None,
                  tekrar: int = None) -> list:
    """parti_uret + BASARISIZLARI TEKRAR DENE.

    ⚠ NEDEN: Flow tek tek promptlarda "might violate our policies" ya da
    gecici hata verebiliyor. Tek denemede birakmak, o cumleyi medyasiz
    birakir. Basarisizlar toplanip yeniden gonderilir; ayni prompt ikinci
    denemede cogu zaman gecer. Kalici olarak reddedilenler icin kurgu
    tarafinda "onceki sahneyi uzat" cozumu devrededir.
    """
    tekrar = TEKRAR if tekrar is None else tekrar
    siralar = siralar or list(range(1, len(promptlar) + 1))
    sonuc = {}                                   # sira -> kayit
    kalan = list(zip(siralar, promptlar))

    for tur_no in range(tekrar + 1):
        if not kalan:
            break
        if tur_no and bildir:
            bildir(f"🔁 {len(kalan)} başarısız prompt tekrar deneniyor "
                   f"({tur_no}/{tekrar})")
        r = parti_uret([p for _, p in kalan], tur, hedef_dizin, bildir,
                       iptal_mi, indi_cb, [s for s, _ in kalan])
        for x in r:
            eski = sonuc.get(x["sira"])
            if x["ok"] or eski is None:
                sonuc[x["sira"]] = x
        kalan = [(s, p) for s, p in kalan
                 if not (sonuc.get(s) or {}).get("ok")]
        if iptal_mi is not None and iptal_mi():
            break

    if kalan and bildir:
        bildir(f"⚠ {len(kalan)} prompt {tekrar + 1} denemede de üretilemedi "
               f"(cümle: {', '.join(str(s) for s, _ in kalan[:10])}"
               f"{'…' if len(kalan) > 10 else ''})")
    return [sonuc[s] for s in siralar if s in sonuc]


def toplu_uret(promptlar: list, tur: str, hedef_dizin: Path, bildir=None,
               iptal_mi=None) -> list:
    """Prompt listesini SIRAYLA uretir. Basarisiz olan ATLANIR, kaydi kalir.

    ⚠ TAKIP SOZLESMESI (kullanici karari): her prompt sonrasi ilerleme
    bildirilir; hata GORUNUR olur; sorun yoksa "devam" denir. Cikti dosyasi
    Telegram'a GONDERILMEZ — diskte kalir.
    `iptal_mi`: cagirandan gelen durdurma sorgusu; True donerse SIRA KESILIR.
    """
    sonuclar = []
    n = len([x for x in promptlar if (x or "").strip()])
    ard_arda_hata = 0
    for i, p in enumerate(promptlar, 1):
        p = (p or "").strip()
        if not p:
            continue
        if iptal_mi is not None and iptal_mi():
            if bildir:
                bildir(f"🛑 iptal edildi — {tur}: {len(sonuclar)}/{n} islendi")
            break
        s = uret_ve_indir(p, tur, i, hedef_dizin, bildir=bildir)
        s["prompt"] = p
        s["sira"] = i
        s["tur"] = tur
        sonuclar.append(s)
        if s["ok"]:
            ard_arda_hata = 0
            if bildir:
                bildir(f"✅ {tur} {len(sonuclar)}/{n} indi — devam ediyorum")
        else:
            ard_arda_hata += 1
            if bildir:
                bildir(f"⚠ {tur}[{i}] BASARISIZ: {s['neden'][:180]}")
            # ⚠ ART ARDA 3 HATA = yapisal sorun (oturum dustu / secici kirildi).
            # Kalan 100 promptu bosuna denemek yerine DURUR ve soyler.
            if ard_arda_hata >= 3:
                if bildir:
                    bildir(f"🛑 arka arkaya 3 hata — {tur} durduruldu. "
                           f"Chrome/Flow oturumunu ve secicileri kontrol et.")
                break
    return sonuclar
```

## Dosya: `hayalet/capcut.py`
```python
#!/usr/bin/env python3
"""HAYALET — CAPCUT: hizalanmis klipleri CapCut zaman cizgisine dizer.

`hayalet.kurgu` her cumleyi TAM suresine getirip ayri bir klip olarak
render eder. Bu modul o klipleri + anlatim sesini bir CapCut TASLAGI
haline getirir: kullanici CapCut'i acar, her cumle zaman cizgisinde ayri
bir parca olarak durur, gecis/yazi/efekt ekleyip elle oynatabilir.

⚠ SEMA BELGELENMIS DEGIL: CapCut'in taslak formati resmi degildir ve
surumden surume degisir. Bu yuzden sema TAHMIN EDILMEZ — kullanicinin
KENDI CapCut'indaki gercek bir projeden "bagisci sablon" olarak
kopyalanir (bkz. `bagisci_bul`). Boylece kurulu surumle birebir uyumlu
nesneler uretilir. Hicbir gercek proje bulunamazsa is BASLAMAZ.

⚠ CAPCUT KAPALI OLMALI: acik CapCut taslak klasorunu kendi hafizasindan
uzerine yazabilir.

Zaman birimi her yerde MIKROSANIYE (int).
"""
from __future__ import annotations

import copy
import json
import shutil
import time
import uuid
from pathlib import Path

# CapCut 9.x (macOS) taslak koku.
TASLAK_KOK = (Path.home() / "Movies" / "CapCut" / "User Data" / "Projects"
              / "com.lveditor.draft")

# Segmentin extra_material_refs'inde gecen yardimci material listeleri.
YARDIMCI = ("speeds", "placeholder_infos", "canvases", "sound_channel_mappings",
            "material_colors", "vocal_separations", "beats")


class CapcutHatasi(RuntimeError):
    """Taslak uretilemez — nedeni mesajda."""


def _kimlik() -> str:
    return str(uuid.uuid4()).upper()


def _us(sn: float) -> int:
    """Saniye -> mikrosaniye (CapCut'in birimi)."""
    return int(round(sn * 1_000_000))


# ─────────────────────────── bagisci sablon ───────────────────────────

def bagisci_bul(kok: Path = TASLAK_KOK) -> dict:
    """Kullanicinin kendi projelerinden sema sablonu cikarir.

    Doner: {"taslak", "video_seg", "audio_seg", "video_mat", "audio_mat",
            "video_iz", "audio_iz", "yardimci": {liste: nesne}}
    """
    if not kok.exists():
        raise CapcutHatasi(f"CapCut taslak klasoru yok: {kok}\n"
                           "CapCut kurulu mu? Bir kez acip proje olusturdun mu?")
    adaylar = sorted(kok.glob("*/draft_info.json"),
                     key=lambda p: p.stat().st_mtime, reverse=True)
    for yol in adaylar:
        try:
            d = json.loads(yol.read_text(encoding="utf-8"))
        except Exception:                                    # noqa: BLE001
            continue
        iz = {t.get("type"): t for t in (d.get("tracks") or [])
              if t.get("segments")}
        if "video" not in iz or "audio" not in iz:
            continue
        vseg = iz["video"]["segments"][0]
        aseg = iz["audio"]["segments"][0]
        mats = d.get("materials") or {}

        def bul(mid):
            for k, v in mats.items():
                if isinstance(v, list):
                    for o in v:
                        if isinstance(o, dict) and o.get("id") == mid:
                            return k, o
            return None, None

        _, vmat = bul(vseg.get("material_id"))
        _, amat = bul(aseg.get("material_id"))
        if not vmat or not amat:
            continue
        yardimci = {}
        for ref in (vseg.get("extra_material_refs") or []) + \
                   (aseg.get("extra_material_refs") or []):
            k, o = bul(ref)
            if k and k not in yardimci:
                yardimci[k] = o
        return {"taslak": d, "yol": yol,
                "video_seg": vseg, "audio_seg": aseg,
                "video_mat": vmat, "audio_mat": amat,
                "video_iz": iz["video"], "audio_iz": iz["audio"],
                "yardimci": yardimci}
    raise CapcutHatasi(
        f"{kok} altinda hem video hem ses izi olan bir CapCut projesi "
        "bulunamadi. Sema bu projelerden kopyalanir — once CapCut'ta bir "
        "videoyu ve bir sesi zaman cizgisine koyup kaydet, sonra tekrar dene.")


# ─────────────────────────── nesne uretimi ───────────────────────────

def _yardimci_uret(sablon: dict, listeler, havuz: dict) -> list:
    """Her segment icin TAZE yardimci material'lar — id'ler paylasilmaz."""
    refs = []
    for ad in listeler:
        proto = sablon["yardimci"].get(ad)
        if proto is None:
            continue
        o = copy.deepcopy(proto)
        o["id"] = _kimlik()
        havuz.setdefault(ad, []).append(o)
        refs.append(o["id"])
    return refs


def _video_ogesi(sablon, havuz, yol: Path, sn: float, basla: int,
                 en: int, boy: int, sira: int) -> dict:
    mat = copy.deepcopy(sablon["video_mat"])
    mat.update({"id": _kimlik(), "path": str(yol.resolve()),
                "material_name": yol.name, "duration": _us(sn),
                "width": en, "height": boy, "has_audio": False,
                "local_material_id": str(uuid.uuid4()),
                "type": "video", "category_name": "local"})
    havuz.setdefault("videos", []).append(mat)

    seg = copy.deepcopy(sablon["video_seg"])
    seg.update({"id": _kimlik(), "material_id": mat["id"],
                "source_timerange": {"start": 0, "duration": _us(sn)},
                "target_timerange": {"start": basla, "duration": _us(sn)},
                "render_index": sira, "track_render_index": 0,
                "volume": 0.0, "speed": 1.0, "keyframe_refs": [],
                "common_keyframes": [], "group_id": "", "template_id": "",
                "extra_material_refs": _yardimci_uret(
                    sablon, ("speeds", "placeholder_infos", "canvases",
                             "sound_channel_mappings", "material_colors",
                             "vocal_separations"), havuz)})
    return seg


def _ses_ogesi(sablon, havuz, yol: Path, sn: float) -> dict:
    mat = copy.deepcopy(sablon["audio_mat"])
    mat.update({"id": _kimlik(), "path": str(yol.resolve()), "name": yol.name,
                "duration": _us(sn), "local_material_id": str(uuid.uuid4()),
                "music_id": str(uuid.uuid4()), "category_name": "local"})
    havuz.setdefault("audios", []).append(mat)

    seg = copy.deepcopy(sablon["audio_seg"])
    seg.update({"id": _kimlik(), "material_id": mat["id"],
                "source_timerange": {"start": 0, "duration": _us(sn)},
                "target_timerange": {"start": 0, "duration": _us(sn)},
                "volume": 1.0, "last_nonzero_volume": 1.0, "speed": 1.0,
                "render_index": 0, "track_render_index": 1,
                "keyframe_refs": [], "common_keyframes": [], "group_id": "",
                "extra_material_refs": _yardimci_uret(
                    sablon, ("speeds", "placeholder_infos", "beats",
                             "sound_channel_mappings", "vocal_separations"),
                    havuz)})
    return seg


# ─────────────────────────── taslak yazimi ───────────────────────────

def taslak_yaz(ad: str, klipler: list, ses: Path, ses_sn: float,
               kok: Path = TASLAK_KOK, en: int = 1920, boy: int = 1080,
               fps: float = 30.0, bildir=print) -> Path:
    """klipler = [(Path, saniye), ...] sirayi KORUR. Taslak klasorunu doner."""
    if not klipler:
        raise CapcutHatasi("Zaman cizgisine dizilecek klip yok.")
    sablon = bagisci_bul(kok)
    bildir(f"Sema sablonu: {sablon['yol'].parent.name} "
           f"(CapCut surumu {sablon['taslak'].get('new_version')})")

    havuz: dict = {}

    klasor = kok / ad
    if klasor.exists():
        raise CapcutHatasi(f"Bu isimde taslak zaten var: {klasor}\n"
                           "Ustune yazmiyorum — baska isim ver.")
    klasor.mkdir(parents=True)

    # ⚠ MEDYA TASLAGIN ICINE KOPYALANIR. CapCut'in ~/Desktop ve ~/Documents
    # gibi TCC korumali klasorlere erisim izni olmayabilir; o zaman klipler
    # zaman cizgisinde "Dosya erisilemiyor" diye kirmizi gorunur. Kendi veri
    # klasorune (~/Movies/CapCut/...) her zaman erisebilir.
    medya_dizin = klasor / "Resources" / "hayalet"
    medya_dizin.mkdir(parents=True)

    def _tasi(kaynak: Path) -> Path:
        hedef = medya_dizin / Path(kaynak).name
        shutil.copy2(kaynak, hedef)
        return hedef

    v_segs, imlec = [], 0
    for i, (yol, sn) in enumerate(klipler):
        v_segs.append(_video_ogesi(sablon, havuz, _tasi(Path(yol)), sn,
                                   imlec, en, boy, i))
        imlec += _us(sn)
    a_seg = _ses_ogesi(sablon, havuz, _tasi(Path(ses)), ses_sn)

    d = copy.deepcopy(sablon["taslak"])
    d["materials"] = {k: ([] if isinstance(v, list) else v)
                      for k, v in (d.get("materials") or {}).items()}
    for k, v in havuz.items():
        d["materials"][k] = v
    v_iz = copy.deepcopy(sablon["video_iz"]); v_iz.update(
        {"id": _kimlik(), "segments": v_segs})
    a_iz = copy.deepcopy(sablon["audio_iz"]); a_iz.update(
        {"id": _kimlik(), "segments": [a_seg]})

    # ⚠ GERCEK PROJELERDE UCU DE AYNI: draft_info.json["id"],
    # Timelines/<UUID> klasor adi ve project.json.main_timeline_id.
    # Farkli olurlarsa CapCut projeyi listeler ama ACMAZ (sessizce).
    zc_id = _kimlik()
    taslak_id = _kimlik()          # draft_meta_info.json'daki ayri kimlik
    simdi = int(time.time() * 1_000_000)
    d.update({
        "id": zc_id, "name": ad, "tracks": [v_iz, a_iz],
        "duration": max(imlec, _us(ses_sn)), "fps": fps,
        "canvas_config": {"ratio": "original", "width": en, "height": boy,
                          "background": None},
        "create_time": simdi, "update_time": simdi,
        "keyframes": {k: [] for k in (d.get("keyframes") or {})},
        "keyframe_graph_list": [], "relationships": [], "time_marks": None,
        "group_container": None, "cover": None, "retouch_cover": None,
        "static_cover_image_path": "", "path": str(klasor.resolve()),
        "platform": d.get("platform"), "draft_type": "",
    })

    (klasor / "draft_info.json").write_text(
        json.dumps(d, ensure_ascii=False), encoding="utf-8")
    # CapCut 9.x taslagi ayrica Timelines/<UUID>/ altinda AYNISINI tutar,
    # ve project.json + timeline_layout.json bu UUID'ye ISARET ETMELIDIR —
    # bagiscininki oldugu gibi kopyalanirsa proje ACILMAZ.
    zc_ad = "Zaman çizelgesi 01"
    zc = klasor / "Timelines" / zc_id
    zc.mkdir(parents=True)
    (zc / "draft_info.json").write_text(
        json.dumps(d, ensure_ascii=False), encoding="utf-8")
    (klasor / "Timelines" / "project.json").write_text(json.dumps({
        "config": {"color_space": -1, "mixed_track_mode_on": False,
                   "render_index_track_mode_on": False,
                   "use_float_render": False},
        "create_time": simdi, "update_time": simdi, "version": 0,
        "id": _kimlik(), "main_timeline_id": zc_id,
        "timelines": [{"create_time": simdi, "update_time": simdi,
                       "id": zc_id, "is_marked_delete": False,
                       "name": zc_ad}],
    }, ensure_ascii=False), encoding="utf-8")
    (klasor / "timeline_layout.json").write_text(json.dumps({
        "dockItems": [{"dockIndex": 0, "ratio": 1, "timelineIds": [zc_id],
                       "timelineNames": [zc_ad]}],
        "layoutOrientation": 1}, ensure_ascii=False), encoding="utf-8")
    (klasor / "draft_virtual_store.json").write_text(
        json.dumps({"draft_materials": [], "draft_virtual_store": []}),
        encoding="utf-8")

    # Proje listesinde gorunmesi icin kunye — bagiscininki uyarlanir.
    kunye_yolu = sablon["yol"].parent / "draft_meta_info.json"
    if kunye_yolu.exists():
        k = json.loads(kunye_yolu.read_text(encoding="utf-8"))
        k.update({"draft_id": taslak_id, "draft_name": ad,
                  "draft_fold_path": str(klasor.resolve()),
                  "draft_root_path": str(kok.resolve()),
                  "draft_timeline_materials_size_": 0,
                  "tm_duration": d["duration"],
                  "draft_new_version": "",
                  "tm_draft_create": simdi, "tm_draft_modified": simdi,
                  "draft_removable_storage_device": "",
                  "draft_cover": "draft_cover.jpg"})
        k["draft_materials"] = [{"type": t, "value": []} for t in
                                (0, 1, 2, 3, 6, 7, 8)]
        (klasor / "draft_meta_info.json").write_text(
            json.dumps(k, ensure_ascii=False), encoding="utf-8")
    for yan in ("draft_agency_config.json", "draft_settings",
                "performance_opt_info.json"):
        kaynak = sablon["yol"].parent / yan
        if kaynak.exists():
            shutil.copy2(kaynak, klasor / yan)

    bildir(f"✓ CapCut taslagi: {klasor}")
    bildir(f"  {len(v_segs)} klip + 1 ses izi, "
           f"{d['duration'] / 1_000_000:.1f} sn")
    bildir("  CapCut'i KAPATIP tekrar ac — proje listesinde gorunur.")
    return klasor
```

## Dosya: `hayalet/kurgu.py`
```python
#!/usr/bin/env python3
"""HAYALET — KURGU: metin + ses + cumle basina medya -> senkron video.

Hayalet URETIR ve INDIRIR; bu modul o ciktilari SESLE HIZALAR.
Cumle i'nin sesteki suresi ne kadarsa, o cumlenin videosu/gorseli
ekranda tam o kadar durur. Premiere/Resolve gerekmez, sadece ffmpeg.

Cumle sinirlari nasil bulunur (sirasiyla denenir):
  1) ses bir KLASORSE  -> her cumlenin kendi ses dosyasi var, sure KESIN
  2) OpenAI anahtari varsa -> ASR kelime zaman damgalari (tek dosyada EN IYI)
  3) ffmpeg silencedetect -> duraklama sayisi cumle sayisini tutuyorsa
  4) hicbiri olmazsa -> karakter sayisina gore oranti (UYARI ile)

⚠ SESSIZ DUSUS YOK: hangi yontemin kullanildigi ve her cumlenin suresi
`kurgu.json` icine yazilir, ekrana da basilir.

Kullanim:
    python3 -m hayalet.kurgu --is is_20260821_1a2b
    python3 -m hayalet.kurgu --metin m.txt --ses ses.mp3 --medya klasor/ \
        --cikti final.mp4 --altyazi
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import urllib.request
import uuid
from pathlib import Path

from . import ayar
from .beyin import cumlelere_bol
from .capcut import CapcutHatasi

EN, BOY, FPS = 1920, 1080, 30
VIDEO_UZANTI = {".mp4", ".mov", ".webm", ".m4v", ".mkv"}
GORSEL_UZANTI = {".png", ".jpg", ".jpeg", ".webp"}
SES_UZANTI = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}

# Duraklamalari cumle siniri sayma esikleri.
# ⚠ OLCULDU (21 Agu 2026, macOS `say` ile uretilmis TR anlatim): -35dB/0.32s
# ile SIFIR duraklama bulundu (TTS cumle arasi nefes birakmiyor), -30dB/0.2s
# ile tam 4/4 dogru bulundu. Esik gevsetildi — yine de bu YEDEK yontemdir,
# birincil hizalama ASR kelime zaman damgalaridir.
SESSIZ_DB = "-30dB"
SESSIZ_MIN_SN = 0.22
# Bir cumleye ayrilabilecek en kisa sure — altina duserse hizalama bozuktur.
EN_KISA_SN = 0.4

# ── Kelime zaman damgali hizalama (EN IYI yontem) ──
# ⚠ NEDEN: tek seslendirme dosyasinda "duraklama say" yontemi ancak cumle
# sayisi kadar net duraklama varsa tutar; 40+ cumlelik anlatimda pratikte
# TUTMAZ ve karakter orantisina duseriz (kayma birikir). Transkripsiyon
# kelime bazinda ZAMAN verir; cumle sinirlarini gercek sesten okuruz.
OPENAI_KEY = os.environ.get("HAYALET_OPENAI_KEY",
                            os.environ.get("OPENAI_API_KEY", ""))
ASR_MODEL = os.environ.get("HAYALET_ASR_MODEL", "whisper-1")
ASR_BOY_TAVAN = 24 * 1024 * 1024          # whisper-1 sinirı 25MB


class KurguHatasi(RuntimeError):
    """Kurgu yapilamaz — nedeni mesajda, tahminle devam ETME."""


# ─────────────────────────── ffmpeg yardimcilari ───────────────────────────

def _kos(komut: list, yakala: bool = False) -> str:
    s = subprocess.run(komut, capture_output=True, text=True)
    if s.returncode != 0:
        kuyruk = (s.stderr or "").strip().splitlines()[-6:]
        raise KurguHatasi(f"ffmpeg dustu: {' '.join(komut[:3])}...\n"
                          + "\n".join(kuyruk))
    return (s.stdout if yakala else "") or ""


def _suzgec_var(ad: str) -> bool:
    """ffmpeg derlemesinde suzgec var mi? (Homebrew'un sade derlemesinde
    `subtitles` yok — libass olmadan altyazi YAKILAMAZ.)"""
    s = subprocess.run(["ffmpeg", "-hide_banner", "-filters"],
                       capture_output=True, text=True)
    return re.search(rf"^ \S\S\S? +{re.escape(ad)} ", s.stdout or "",
                     re.M) is not None


def sure(dosya: Path) -> float:
    cikti = _kos(["ffprobe", "-v", "error", "-show_entries",
                  "format=duration", "-of", "csv=p=0", str(dosya)], yakala=True)
    try:
        return float(cikti.strip())
    except ValueError:
        raise KurguHatasi(f"Sure okunamadi: {dosya.name}")


def _sessizlikler(ses: Path) -> list:
    """[(baslangic, bitis)] — ffmpeg silencedetect ciktisi."""
    s = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(ses), "-af",
         f"silencedetect=noise={SESSIZ_DB}:d={SESSIZ_MIN_SN}", "-f", "null", "-"],
        capture_output=True, text=True)
    metin = s.stderr or ""
    basla = [float(x) for x in re.findall(r"silence_start:\s*(-?[\d.]+)", metin)]
    bit = [float(x) for x in re.findall(r"silence_end:\s*(-?[\d.]+)", metin)]
    return list(zip(basla, bit))


# ─────────────────────────── cumle sureleri ───────────────────────────

def _sozcukle(metin: str) -> list:
    """Karsilastirma icin sadelestirilmis sozcukler (aksan/noktalama disi)."""
    d = unicodedata.normalize("NFKD", (metin or "").lower())
    d = "".join(k for k in d if not unicodedata.combining(k))
    return [w for w in re.findall(r"[0-9a-z]+", d) if w]


def _ses_kucult(ses: Path) -> Path:
    """ASR icin 16kHz mono m4a — 25MB sinirinin altina indirir."""
    hedef = Path(tempfile.mkdtemp(prefix="hayalet_asr_")) / "asr.m4a"
    _kos(["ffmpeg", "-y", "-i", str(ses), "-ac", "1", "-ar", "16000",
          "-c:a", "aac", "-b:a", "32k", str(hedef)])
    return hedef


def _asr_kelimeleri(ses: Path, bildir=print) -> list:
    """[(sozcuk, baslangic_sn, bitis_sn)] — OpenAI kelime zaman damgalari."""
    if not OPENAI_KEY:
        raise KurguHatasi("anahtar yok")
    yol = ses
    if yol.stat().st_size > ASR_BOY_TAVAN:
        bildir("  ses buyuk — ASR icin 16kHz mono'ya kucultuluyor")
        yol = _ses_kucult(yol)
        if yol.stat().st_size > ASR_BOY_TAVAN:
            raise KurguHatasi("ses kuculttukten sonra da 25MB'i asiyor")

    sinir = f"----hayalet{uuid.uuid4().hex}"
    govde = bytearray()

    def alan(ad, deger):
        govde.extend(f"--{sinir}\r\nContent-Disposition: form-data; "
                     f'name="{ad}"\r\n\r\n{deger}\r\n'.encode())

    alan("model", ASR_MODEL)
    alan("response_format", "verbose_json")
    alan("timestamp_granularities[]", "word")
    govde.extend(f'--{sinir}\r\nContent-Disposition: form-data; '
                 f'name="file"; filename="{yol.name}"\r\n'
                 f"Content-Type: application/octet-stream\r\n\r\n".encode())
    govde.extend(yol.read_bytes())
    govde.extend(f"\r\n--{sinir}--\r\n".encode())

    istek = urllib.request.Request(
        "https://api.openai.com/v1/audio/transcriptions", data=bytes(govde),
        headers={"Authorization": f"Bearer {OPENAI_KEY}",
                 "Content-Type": f"multipart/form-data; boundary={sinir}"})
    with urllib.request.urlopen(istek, timeout=600) as y:
        cevap = json.load(y)
    kelimeler = [(str(k.get("word", "")), float(k.get("start", 0.0)),
                  float(k.get("end", 0.0))) for k in (cevap.get("words") or [])]
    if not kelimeler:
        raise KurguHatasi("ASR kelime zamani dondurmedi")
    return kelimeler


def _hizala_kelime(cumleler: list, kelimeler: list, toplam: float) -> list:
    """Cumleleri ASR kelimelerine esleyip GERCEK sinir surelerini cikarir.

    ⚠ TRANSKRIPT METINLE BIREBIR OLMAZ (yanlis duyma, sayi/kisaltma yazimi).
    Bu yuzden difflib ile en uzun ortak diziler bulunur; eslenemeyen
    cumle siniri, komsu eslesmeler arasinda ORANTIYLA yerlestirilir.
    """
    metin_sozcuk, cumle_no = [], []
    for i, c in enumerate(cumleler):
        w = _sozcukle(c)
        metin_sozcuk.extend(w)
        cumle_no.extend([i] * len(w))
    asr_sozcuk = [_sozcukle(k[0])[0] if _sozcukle(k[0]) else "" for k in kelimeler]
    if not metin_sozcuk or not asr_sozcuk:
        raise KurguHatasi("hizalanacak sozcuk yok")

    # metin sozcuk indeksi -> asr sozcuk indeksi
    harita = {}
    for a, b, n in difflib.SequenceMatcher(
            None, metin_sozcuk, asr_sozcuk, autojunk=False).get_matching_blocks():
        for k in range(n):
            harita[a + k] = b + k
    if len(harita) < max(4, len(metin_sozcuk) * 0.30):
        raise KurguHatasi(
            f"transkript metinle ortusmuyor ({len(harita)}/{len(metin_sozcuk)} "
            "sozcuk esletti) — seslendirme metne ait olmayabilir")

    # Her cumlenin SON sozcugunun metin-indeksi = o cumlenin siniri
    son_idx = []
    for i in range(len(cumleler)):
        idx = [j for j, c in enumerate(cumle_no) if c == i]
        son_idx.append(idx[-1] if idx else None)

    sinirlar = []
    for i, mi in enumerate(son_idx):
        t = None
        if mi is not None:
            for adim in range(0, 6):        # kucuk pencerede eslesme ara
                for j in (mi - adim, mi + adim):
                    if j in harita and 0 <= harita[j] < len(kelimeler):
                        t = kelimeler[harita[j]][2]
                        break
                if t is not None:
                    break
        sinirlar.append(t)
    sinirlar[-1] = toplam                  # son cumle sesin sonuna kadar

    # Bosluklari komsular arasinda orantiyla doldur
    onceki = 0.0
    for i in range(len(sinirlar)):
        if sinirlar[i] is None:
            j = next((k for k in range(i + 1, len(sinirlar))
                      if sinirlar[k] is not None), len(sinirlar) - 1)
            adim = (sinirlar[j] - onceki) / (j - i + 1)
            sinirlar[i] = onceki + adim
        sinirlar[i] = max(sinirlar[i], onceki + EN_KISA_SN)
        onceki = sinirlar[i]
    olcek = toplam / sinirlar[-1] if sinirlar[-1] > toplam else 1.0
    sinirlar = [s * olcek for s in sinirlar]
    return [sinirlar[0]] + [sinirlar[i] - sinirlar[i - 1]
                            for i in range(1, len(sinirlar))]


def _orantili(cumleler: list, toplam: float) -> list:
    """Son care: karakter sayisina gore payla. Hizalama YAKLASIKTIR."""
    agirlik = [max(len(c), 1) for c in cumleler]
    top = sum(agirlik)
    return [toplam * a / top for a in agirlik]


def sureleri_cikar(cumleler: list, ses: Path, bildir=print) -> tuple:
    """(sureler, birlesik_ses, yontem) dondurur."""
    n = len(cumleler)

    # 1) Cumle basina ses dosyasi — kesin hizalama.
    if ses.is_dir():
        parcalar = sorted([p for p in ses.iterdir()
                           if p.suffix.lower() in SES_UZANTI],
                          key=_sira_anahtari)
        if len(parcalar) != n:
            raise KurguHatasi(
                f"Ses klasorunde {len(parcalar)} dosya var ama metinde {n} "
                f"cumle. Esitlemeden kurgu yapilmaz.")
        sureler = [sure(p) for p in parcalar]
        return sureler, _sesleri_birlestir(parcalar), "cumle basina ses dosyasi"

    toplam = sure(ses)

    # 2) Kelime zaman damgalari (ASR) — tek dosyada EN GUVENILIR yontem.
    if OPENAI_KEY:
        try:
            bildir("  cumle sinirlari icin ses cozumleniyor (ASR)…")
            kelimeler = _asr_kelimeleri(ses, bildir)
            sureler = _hizala_kelime(cumleler, kelimeler, toplam)
            return sureler, ses, f"ASR kelime zaman damgalari ({ASR_MODEL})"
        except KurguHatasi as e:
            bildir(f"⚠ ASR hizalama olmadi ({e}) — duraklamalara duşuluyor")
        except Exception as e:                               # noqa: BLE001
            bildir(f"⚠ ASR hizalama olmadi ({type(e).__name__}) — "
                   "duraklamalara duşuluyor")
    else:
        bildir("⚠ HAYALET_OPENAI_KEY yok — en iyi hizalama (ASR) atlandi")

    # 3) Duraklamalardan bol.
    bosluklar = [(a, b) for a, b in _sessizlikler(ses) if a > 0.05 and b < toplam - 0.05]
    if len(bosluklar) == n - 1:
        sinirlar = [0.0] + [(a + b) / 2 for a, b in bosluklar] + [toplam]
        sureler = [sinirlar[i + 1] - sinirlar[i] for i in range(n)]
        if all(s >= EN_KISA_SN for s in sureler):
            return sureler, ses, "sesteki duraklamalar (silencedetect)"
        bildir("⚠ Duraklama sayisi tuttu ama bazi cumleler cok kisa cikti.")
    else:
        bildir(f"⚠ Seste {len(bosluklar)} duraklama bulundu, {n - 1} bekleniyordu.")

    # 4) Oranti — yaklasik.
    bildir("⚠ YAKLASIK HIZALAMA: sureler karakter sayisina gore paylastirildi. "
           "Kesin senkron icin cumle basina ayri ses dosyasi ver.")
    return _orantili(cumleler, toplam), ses, "karakter orantisi (YAKLASIK)"


def sesleri_birlestir(parcalar: list, hedef: Path = None) -> Path:
    """Ses parcalarini SIRAYLA tek dosyada birlestirir.

    ⚠ ONCE TEK FORMATA GETIRILIR: parcalar farkli kaynaklardan gelebilir
    (Telegram sesli mesaji opus/ogg, telefondan m4a, bilgisayardan mp3).
    Concat demuxer'a farkli ornekleme hizi/kanal sayisi verilirse cikti
    sessiz ya da hizli/yavas olabilir — bu SESSIZ bir bozulmadir. Bu yuzden
    her parca once 44.1kHz mono AAC'ye cevrilir, sonra birlestirilir.
    """
    if not parcalar:
        raise KurguHatasi("Birlestirilecek ses parcasi yok.")
    gecici = Path(tempfile.mkdtemp(prefix="hayalet_ses_"))
    hedef = hedef or (gecici / "anlatim.m4a")
    hedef.parent.mkdir(parents=True, exist_ok=True)
    if len(parcalar) == 1:
        _kos(["ffmpeg", "-y", "-i", str(parcalar[0]), "-ac", "1",
              "-ar", "44100", "-c:a", "aac", "-b:a", "128k", str(hedef)])
        return hedef
    duzgun = []
    for i, p in enumerate(parcalar, 1):
        n = gecici / f"parca_{i:03d}.m4a"
        _kos(["ffmpeg", "-y", "-i", str(p), "-ac", "1", "-ar", "44100",
              "-c:a", "aac", "-b:a", "128k", str(n)])
        duzgun.append(n)
    liste = gecici / "liste.txt"
    liste.write_text("".join(f"file '{x}'\n" for x in duzgun), encoding="utf-8")
    _kos(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(liste),
          "-c", "copy", str(hedef)])
    # ⚠ SESSIZ KAYIP KONTROLU: birlesik sure parcalarin toplamini tutmali.
    beklenen = sum(sure(x) for x in duzgun)
    olan = sure(hedef)
    if abs(olan - beklenen) > max(1.0, beklenen * 0.02):
        raise KurguHatasi(
            f"Ses birlestirme tutmadi: beklenen {beklenen:.1f} sn, "
            f"olan {olan:.1f} sn. Parcalar bozuk olabilir.")
    return hedef


def _sesleri_birlestir(parcalar: list) -> Path:
    return sesleri_birlestir(parcalar)


# ─────────────────────────── medya eslesmesi ───────────────────────────

def _sira_anahtari(p: Path):
    """Dosya adinin BASINDAKI sayi = cumle sirasi. Yoksa ada gore."""
    m = re.match(r"0*(\d+)", p.stem)
    return (0, int(m.group(1))) if m else (1, p.stem.lower())


def medya_esle(medya: Path, n: int, bildir=print,
               eksige_izin: bool = False) -> list:
    """Cumle sirasi -> dosya. `eslesme.json` varsa o kazanir.

    eksige_izin=True ise uretilemeyen cumleler icin None dondurur; cagiran
    bosluklari ONCEKI SAHNEYI UZATARAK kapatir (bkz. `sahneleri_kur`).
    """
    harita = medya / "eslesme.json"
    if harita.exists():
        ham = json.loads(harita.read_text(encoding="utf-8"))
        yol = []
        eksik = []
        for i in range(1, n + 1):
            d = ham.get(str(i)) or ham.get(i)
            p = None
            if d:
                p = Path(d)
                p = p if p.is_absolute() else medya / p
                if not p.exists():
                    p = None
            if p is None:
                if not eksige_izin:
                    raise KurguHatasi(f"{i}. cumlenin medyasi yok.")
                eksik.append(i)
            yol.append(p)
        if eksik:
            bildir(f"⚠ {len(eksik)} cumlenin medyasi yok — onceki sahne "
                   f"uzatilarak kapatilacak (cumle: "
                   f"{', '.join(str(x) for x in eksik[:12])}"
                   f"{'…' if len(eksik) > 12 else ''})")
        bildir(f"Eslesme: eslesme.json ({n} cumle)")
        return yol

    dosyalar = sorted([p for p in medya.rglob("*")
                       if p.suffix.lower() in VIDEO_UZANTI | GORSEL_UZANTI],
                      key=_sira_anahtari)
    if len(dosyalar) != n:
        raise KurguHatasi(
            f"{medya} icinde {len(dosyalar)} medya var ama metinde {n} cumle.\n"
            f"Ya dosya adlarini 001_, 002_ diye numarala ya da "
            f"{medya}/eslesme.json yaz: {{\"1\": \"video/a.mp4\", ...}}")
    bildir(f"Eslesme: dosya adi sirasi ({n} cumle)")
    return dosyalar


# ─────────────────────────── sahne uretimi ───────────────────────────

# ⚠ CUMLE BASINA BIR GORSEL = STROBOSKOP (22 Agu 2026 olcumu): 179 cumlelik
# gercek iste ortanca klip 2.14 sn, %70'i 3 sn altinda, 24 tanesi 1 sn'den
# kisaydi. Goruntu surekli degisince izlemesi yorucu oluyor.
# COZUM: kisa cumleler ONCEKI SAHNEYE KATILIR; sahne bu esige ulasana kadar
# buyur. Grubun goruntusu ILK cumlenin gorselidir; digerlerinin gorselleri
# diskte durur (istenirse elle degistirilebilir).
EN_KISA_SAHNE_SN = float(os.environ.get("HAYALET_EN_KISA_SAHNE", "5.0"))
# Gorsel klip boyunca toplam yakinlasma orani (0.22 = %22 buyume).
ZOOM_ORAN = float(os.environ.get("HAYALET_ZOOM", "0.22"))


def sahneleri_grupla(sahneler: list, en_az_sn: float = None) -> list:
    """Kisa sahneleri birlestirerek her sahneyi en az `en_az_sn` yapar.

    Ses HIC KAYMAZ: sureler toplanir, toplam degismez. Yalnizca goruntunun
    kac saniyede bir degistigi kontrol edilir.
    """
    en_az = EN_KISA_SAHNE_SN if en_az_sn is None else en_az_sn
    if en_az <= 0 or not sahneler:
        return sahneler
    yeni = []
    for sh in sahneler:
        if yeni and yeni[-1]["sn"] < en_az:
            yeni[-1]["sn"] += sh["sn"]
            yeni[-1]["cumleler"] = yeni[-1]["cumleler"] + sh["cumleler"]
        else:
            yeni.append({"dosya": sh["dosya"], "sn": sh["sn"],
                         "cumleler": list(sh["cumleler"])})
    # Son sahne esigin altinda kaldiysa bir oncekine kat.
    if len(yeni) > 1 and yeni[-1]["sn"] < en_az:
        yeni[-2]["sn"] += yeni[-1]["sn"]
        yeni[-2]["cumleler"] += yeni[-1]["cumleler"]
        yeni.pop()
    return yeni


def sahneleri_kur(dosyalar: list, sureler: list, cumleler: list) -> list:
    """Eksik medyali cumleleri ONCEKI SAHNEYE KATARAK sahne listesi kurar.

    ⚠ NEDEN UZATMA: bir cumlenin gorseli uretilemediginde o araligi bos
    birakmak ya da klipleri kaydirmak senkronu bozar. Bunun yerine onceki
    goruntu ekranda DAHA UZUN kalir (6 sn yerine 12 sn gibi) — ses hic
    kaymaz, izleyici bosluk gormez.
    Ilk cumle(ler) eksikse sureleri ILK MEVCUT sahneye eklenir.

    Doner: [{"dosya", "sn", "cumleler": [no...]}]
    """
    sahneler, devir = [], 0.0
    for i, (dosya, sn) in enumerate(zip(dosyalar, sureler), 1):
        if dosya is None:
            if sahneler:
                sahneler[-1]["sn"] += sn
                sahneler[-1]["cumleler"].append(i)
            else:
                devir += sn          # bastaki eksikler ilk sahneye biner
            continue
        sahneler.append({"dosya": dosya, "sn": sn + devir, "cumleler": [i]})
        devir = 0.0
    if not sahneler:
        raise KurguHatasi("Hicbir cumlenin medyasi yok — kurgu yapilamaz.")
    return sahneler


_SIGDIR = (f"scale={EN}:{BOY}:force_original_aspect_ratio=decrease,"
           f"pad={EN}:{BOY}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={FPS}")


def sahne_yap(kaynak: Path, sn: float, hedef: Path) -> None:
    """Kaynagi TAM `sn` saniyelik, tek tip kodlanmis bir klibe cevirir."""
    gorsel = kaynak.suffix.lower() in GORSEL_UZANTI
    if gorsel:
        # Ken Burns: durgun gorsel ekranda olmesin.
        # Once 2x cerceveye TAM SIGDIR (videolarla ayni letterbox davranisi —
        # kare/dikey gorselin ustu altu kesilmesin), sonra yavas zoom.
        # ⚠ ZOOM KLIBIN TAMAMINA YAYILMALI (22 Agu 2026 kullanici geri
        # bildirimi): eski hal `min(zoom+0.0009,1.22)` idi — sabit hizla
        # buyuyup TAVANA CARPIYORDU. 0.22'lik yol 30fps'te ~8.1 saniye
        # suruyor; 10 saniyelik bir klipte son ~2 saniye DONUYORDU ve bu
        # durus kesme/gecis efekti gibi gorunuyordu.
        # Simdi artis klip suresinden hesaplanir: hangi uzunlukta olursa
        # olsun hareket ilk kareden son kareye kadar kesintisiz surer.
        kare = max(int(sn * FPS), 1)
        adim = ZOOM_ORAN / max(kare - 1, 1)
        suzgec = (f"scale={EN*2}:{BOY*2}:force_original_aspect_ratio=decrease,"
                  f"pad={EN*2}:{BOY*2}:(ow-iw)/2:(oh-ih)/2,"
                  f"zoompan=z='1+{adim:.8f}*on'"
                  f":d={kare}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                  f":s={EN}x{BOY}:fps={FPS},setsar=1")
        girdi = ["-loop", "1", "-i", str(kaynak)]
    else:
        # -stream_loop: klip kisaysa basa sarar, uzunsa -t zaten keser.
        suzgec = _SIGDIR
        girdi = ["-stream_loop", "-1", "-i", str(kaynak)]
    _kos(["ffmpeg", "-y", *girdi, "-t", f"{sn:.3f}", "-vf", suzgec,
          "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
          "-pix_fmt", "yuv420p", "-r", str(FPS), str(hedef)])


def _zaman(sn: float) -> str:
    ms = int(round(sn * 1000))
    s, ms = divmod(ms, 1000)
    d, s = divmod(s, 60)
    sa, d = divmod(d, 60)
    return f"{sa:02d}:{d:02d}:{s:02d},{ms:03d}"


def srt_yaz(cumleler: list, sureler: list, hedef: Path) -> None:
    t, satir = 0.0, []
    for i, (c, s) in enumerate(zip(cumleler, sureler), 1):
        satir.append(f"{i}\n{_zaman(t)} --> {_zaman(t + s)}\n{c}\n")
        t += s
    hedef.write_text("\n".join(satir), encoding="utf-8")


# ─────────────────────────── ana akis ───────────────────────────

def kurgula(metin: str, ses: Path, medya: Path, cikti: Path,
            altyazi: bool = False, capcut: str = "", bildir=print,
            eksige_izin: bool = True) -> dict:
    if not shutil.which("ffmpeg"):
        raise KurguHatasi("ffmpeg kurulu degil:  brew install ffmpeg")
    cumleler = cumlelere_bol(metin)
    if not cumleler:
        raise KurguHatasi("Metinde cumle yok.")
    bildir(f"{len(cumleler)} cumle bulundu.")

    dosyalar = medya_esle(medya, len(cumleler), bildir, eksige_izin)
    sureler, anlatim, yontem = sureleri_cikar(cumleler, ses, bildir)
    bildir(f"Hizalama yontemi: {yontem}")
    # Eksik medyali cumleler onceki sahneye katilir; ses HIC KAYMAZ.
    sahne_plani = sahneleri_kur(dosyalar, sureler, cumleler)
    eksikten = sum(len(x["cumleler"]) - 1 for x in sahne_plani)
    if eksikten:
        bildir(f"↔ {eksikten} cumle medyasi yok — onceki sahneye katildi")
    # Kisa sahneleri birlestir: goruntu her 1-2 saniyede degismesin.
    once = len(sahne_plani)
    sahne_plani = sahneleri_grupla(sahne_plani)
    uzatilan = sum(len(x["cumleler"]) - 1 for x in sahne_plani)
    if len(sahne_plani) != once:
        sur = sorted(x["sn"] for x in sahne_plani)
        bildir(f"🎞 sahne birlestirme (en az {EN_KISA_SAHNE_SN:g} sn): "
               f"{len(cumleler)} cumle → {len(sahne_plani)} klip · "
               f"ortanca {sur[len(sur)//2]:.1f} sn · en uzun {sur[-1]:.1f} sn")

    # ⚠ CapCut icin klipler KALICI olmali: taslak bu dosyalara yol verir,
    # gecici klasor silinirse zaman cizgisi bos medyayla acilir.
    if capcut:
        gecici = cikti.parent / (cikti.stem + "_klipler")
        gecici.mkdir(parents=True, exist_ok=True)
    else:
        gecici = Path(tempfile.mkdtemp(prefix="hayalet_kurgu_"))
    sahneler = []
    for i, sh in enumerate(sahne_plani, 1):
        parca = gecici / f"sahne_{i:04d}.mp4"
        etiket = (f"c{sh['cumleler'][0]}" if len(sh["cumleler"]) == 1
                  else f"c{sh['cumleler'][0]}-{sh['cumleler'][-1]}")
        bildir(f"  [{i}/{len(sahne_plani)}] {sh['sn']:5.2f}sn  {etiket}  "
               f"{Path(sh['dosya']).name}")
        sahne_yap(Path(sh["dosya"]), sh["sn"], parca)
        sahneler.append(parca)

    liste = gecici / "sahneler.txt"
    liste.write_text("".join(f"file '{p}'\n" for p in sahneler), encoding="utf-8")
    gorsel_akis = gecici / "gorsel.mp4"
    _kos(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(liste),
          "-c", "copy", str(gorsel_akis)])

    cikti.parent.mkdir(parents=True, exist_ok=True)
    komut = ["ffmpeg", "-y", "-i", str(gorsel_akis), "-i", str(anlatim)]
    altyazi_notu = "yok"
    if altyazi:
        srt = cikti.with_suffix(".srt")
        srt_yaz(cumleler, sureler, srt)
        if _suzgec_var("subtitles"):
            kacis = (str(srt).replace("\\", "/")
                     .replace(":", r"\:").replace("'", r"\'"))
            komut += ["-vf", f"subtitles='{kacis}':force_style="
                             "'FontSize=22,Outline=2,MarginV=48'",
                      "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                      "-pix_fmt", "yuv420p"]
            altyazi_notu = "goruntuye yakildi"
        else:
            # ⚠ SESSIZ DUSUS YOK: yakamiyorsak GOMULU iz olarak ekleriz.
            bildir("⚠ Bu ffmpeg derlemesinde `subtitles` suzgeci (libass) YOK "
                   "— altyazi goruntuye yakilamadi, gomulu iz olarak eklendi "
                   "(oynaticidan acilir). Yakmak icin libass'li ffmpeg gerekir.")
            komut += ["-i", str(srt), "-map", "0:v", "-map", "1:a", "-map", "2",
                      "-c:v", "copy", "-c:s", "mov_text"]
            altyazi_notu = f"gomulu iz + {srt.name}"
        komut += ["-c:a", "aac", "-b:a", "192k", "-shortest", str(cikti)]
    else:
        komut += ["-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                  "-shortest", str(cikti)]
    _kos(komut)

    kunye = {"cikti": str(cikti), "yontem": yontem,
             "altyazi": altyazi_notu,
             "toplam_sn": round(sum(sureler), 3),
             "cumle_sayisi": len(cumleler), "klip_sayisi": len(sahne_plani),
             "uzatilan_cumle": uzatilan, "en_kisa_sahne_sn": EN_KISA_SAHNE_SN,
             "medyasiz_cumleler": [i for i, d in enumerate(dosyalar, 1)
                                   if d is None],
             "sahneler": [{"sira": i, "sn": round(sh["sn"], 3),
                           "cumleler": sh["cumleler"],
                           "cumle": " ".join(cumleler[c - 1]
                                             for c in sh["cumleler"])[:300],
                           "dosya": str(sh["dosya"])}
                          for i, sh in enumerate(sahne_plani, 1)]}
    cikti.with_name(cikti.stem + "_kurgu.json").write_text(
        json.dumps(kunye, ensure_ascii=False, indent=2), encoding="utf-8")
    bildir(f"✓ {cikti}  ({kunye['toplam_sn']:.1f} sn)")

    if capcut:
        from .capcut import taslak_yaz          # gec import: CapCut sart degil
        # Anlatim sesi de kalici olmali (klasor ses ise birlestirilmisti).
        kalici_ses = gecici / "anlatim.m4a"
        if Path(anlatim).resolve() != kalici_ses.resolve():
            shutil.copy2(anlatim, kalici_ses)
        klasor = taslak_yaz(capcut,
                            [(y, sh["sn"]) for y, sh in
                             zip(sahneler, sahne_plani)],
                            kalici_ses, sum(sureler), bildir=bildir)
        kunye["capcut"] = str(klasor)
        cikti.with_name(cikti.stem + "_kurgu.json").write_text(
            json.dumps(kunye, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        shutil.rmtree(gecici, ignore_errors=True)
    return kunye


def main(argv=None) -> int:
    a = argparse.ArgumentParser(description="Hayalet ciktilarini sesle hizala.")
    a.add_argument("--is", dest="is_adi",
                   help="~/Desktop/Hayalet/<is_adi> klasorunu kullan")
    a.add_argument("--metin", help="Anlatim metni (.txt)")
    a.add_argument("--ses", help="Tek ses dosyasi VEYA cumle basina ses klasoru")
    a.add_argument("--medya", help="Video/gorsel klasoru")
    a.add_argument("--cikti", help="Cikti .mp4")
    a.add_argument("--altyazi", action="store_true", help="Altyaziyi videoya goc")
    a.add_argument("--capcut", metavar="AD", default="",
                   help="Ayni kurguyu CapCut taslagi olarak da yaz "
                        "(her cumle ayri klip, ses ayri iz)")
    n = a.parse_args(argv)

    if n.is_adi:
        d = ayar.KOK / n.is_adi
        n.metin = n.metin or str(d / "metin.txt")
        n.ses = n.ses or str(d / "ses")
        n.medya = n.medya or str(d)
        n.cikti = n.cikti or str(d / "final.mp4")
    if not (n.metin and n.ses and n.medya and n.cikti):
        a.error("--is ver ya da --metin --ses --medya --cikti hepsini ver")

    try:
        kurgula(Path(n.metin).read_text(encoding="utf-8"), Path(n.ses),
                Path(n.medya), Path(n.cikti), n.altyazi, n.capcut)
    except (KurguHatasi, CapcutHatasi) as e:
        print(f"✗ {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

## Dosya: `hayalet/bot.py`
```python
#!/usr/bin/env python3
"""HAYALET TELEGRAM BOTU — /basla de, scripti at, gerisi otomatik.

KAPSAM (kullanici karari, 20 Agu 2026):
  · YALNIZCA uretim + indirme + klasorleme. KURGU/EDIT YOK.
  · Telegram = TAKIP KANALI: ilerleme + hata bildirir, DOSYA GONDERMEZ.
  · AKIS BILEREK BASIT (kullanici: "fazla karmasiklastirma"):
        /basla  ->  bot scripti ister  ->  script gelir  ->  uretim baslar

SCRIPT BICIMI (tek mesaj):
    video:
    bir balikci teknesi safakta limandan cikiyor
    dalgalar guverteyi dovuyor
    gorsel:
    yasli balikcinin yakin plan portresi
    limanda mezat sabahi

  · "video:" satirindan sonrakiler VIDEO, "gorsel:" sonrakiler GORSEL promptu.
  · Hic baslik yoksa TUM satirlar GORSEL sayilir (en yaygin kullanim).
"""
from __future__ import annotations

import asyncio
import json
import logging
import signal
import warnings
import re
import time
from pathlib import Path

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (Application, CommandHandler, MessageHandler, filters)

from . import ayar, beyin, flow_surucu, kurgu

# ⚠ SENKRON AKISI (21 Agu 2026 — kullanici karari): /senkron ARTIK IKI GIRDI
# ister ve isi SONUNA kadar goturur:
#     /senkron -> METIN -> SESLENDIRME -> Flow uretimi -> ses hizalama
#              -> CapCut taslagi (her cumle ayri klip) -> BITTI
# Kullanici CapCut'i acip gecis/yazi/efekt ekler; kesme islerini yapmaz.
# Telegram Bot API getFile tavani. Asilirsa indirme HATA verir — o yuzden
# denemeden once boyuta bakariz (bkz. ses_geldi).
TELEGRAM_INDIRME_TAVAN = 20 * 1024 * 1024

_BEKLEYEN = {}       # sohbet_id -> "hikaye" | "senkron_metin" | "senkron_ses"
_TASLAK = {}         # sohbet_id -> {"metin": ...} (adimlar arasi tasima)
_CALISAN = set()     # su an uretimde olan sohbetler (cifte /basla engeli)
_IPTAL = set()
_SON_IS = {}         # sohbet_id -> son is sozlugu (/durum icin)


_ETIKET = re.compile(
    r"^(video|g[oö]rsel|image)\s*(prompt\w*)?\s*\d*\s*[-–:.]\s*(.+)$",
    re.IGNORECASE)


def _blok_coz(metin: str) -> tuple:
    """TEK BLOK -> (video_promptlari, gorsel_promptlari).

    BICIM (kullanici karari, 20 Agu 2026):
        VIDEO PROMPT 1 - safakta limandan cikan tekne
        VIDEO PROMPT 2 - dalgalar guverteyi dovuyor
        GÖRSEL PROMPT 1 - yasli balikcinin portresi

    · Etiket buyuk/kucuk harf, numara ve ayirac (- – : .) toleransli.
    · Etiketsiz satir, ONCEKI promptun devami sayilir (cok satirli prompt);
      hic etiket gorulmemisse GORSEL kabul edilir.
    """
    videolar, gorseller = [], []
    son_liste = None
    for satir in (metin or "").splitlines():
        t = satir.strip()
        if not t:
            continue
        m = _ETIKET.match(t)
        if m:
            hedef = videolar if m.group(1).lower() == "video" else gorseller
            hedef.append(m.group(3).strip())
            son_liste = hedef
        elif son_liste:
            son_liste[-1] += " " + t          # onceki promptun devami
        else:
            gorseller.append(t)
            son_liste = gorseller
    return videolar, gorseller


def _kaydet(is_: dict) -> None:
    Path(is_["dizin"], "is.json").write_text(
        json.dumps(is_, ensure_ascii=False, indent=2), encoding="utf-8")


def _izinli(update: Update) -> bool:
    if not ayar.IZINLI_KULLANICILAR:
        return True
    return str(update.effective_user.id) in ayar.IZINLI_KULLANICILAR


async def komut_start(update: Update, _ctx):
    await update.message.reply_text(
        "👻 *Hayalet* hazır — iki mod:\n\n"
        "🎬 `/hikaye` — hazır promptlarını TEK BLOK gönderirsin\n"
        "   (`VIDEO PROMPT 1 - ...` / `GÖRSEL PROMPT 1 - ...`)\n\n"
        "🧠 `/senkron` — KARAKTER + METİN + PROMPTLAR + SESLENDİRME\n"
        "   verirsin; üretir, sesle hizalar ve *CapCut projesi* olarak\n"
        "   zaman çizgisine dizer. Sen sadece geçiş/yazı eklersin.\n\n"
        "`/durum` · `/cumleler` · `/tamam` · `/hazir` · `/sifirla` · `/iptal`",
        parse_mode="Markdown")


async def komut_hikaye(update: Update, _ctx):
    if not _izinli(update):
        return
    sohbet = update.effective_chat.id
    if sohbet in _CALISAN:
        await update.message.reply_text("⏳ Üretim sürüyor. `/iptal` ile durdur.")
        return
    _BEKLEYEN[sohbet] = "hikaye"
    await update.message.reply_text(
        "📜 Promptları TEK BLOK gönder:\n\n"
        "```\nVIDEO PROMPT 1 - şafakta limandan çıkan tekne\n"
        "GÖRSEL PROMPT 1 - yaşlı balıkçının portresi\n```",
        parse_mode="Markdown")


async def komut_senkron(update: Update, _ctx):
    if not _izinli(update):
        return
    sohbet = update.effective_chat.id
    if sohbet in _CALISAN:
        await update.message.reply_text("⏳ Üretim sürüyor. `/iptal` ile durdur.")
        return
    _TASLAK.pop(sohbet, None)
    await _karakter_sor(update, sohbet)


def _klavye(secenekler: list) -> ReplyKeyboardMarkup:
    """Tek sutunlu secim klavyesi — yazim hatasi olmasin diye dokunmalik."""
    return ReplyKeyboardMarkup([[x] for x in secenekler],
                               one_time_keyboard=True, resize_keyboard=True)



# Eski akisla uyum: /basla artik kip secim mesaji verir.
async def komut_basla(update: Update, _ctx):
    await update.message.reply_text(
        "İki mod var: 🎬 `/hikaye` (hazır promptlar) · 🧠 `/senkron` (metin ver)",
        parse_mode="Markdown")


async def komut_iptal(update: Update, _ctx):
    sohbet = update.effective_chat.id
    _BEKLEYEN.pop(sohbet, None)
    if sohbet in _CALISAN:
        _IPTAL.add(sohbet)
        await update.message.reply_text("🛑 İptal istendi — sıradaki prompttan sonra durur.")
    else:
        await update.message.reply_text("🛑 Bekleyen iş yok, istek iptal edildi.")


async def komut_durum(update: Update, _ctx):
    is_ = _SON_IS.get(update.effective_chat.id)
    if not is_:
        await update.message.reply_text("Henüz iş yok. `/basla` yaz.")
        return
    satir = (f"📋 *{is_['ad']}* ({is_.get('kip', '?')}) — {is_['durum']}\n"
             f"🎬 video: {len(is_['video_promptlari'])} · "
             f"🖼 görsel: {len(is_['gorsel_promptlari'])} · "
             f"⚠ hata: {len(is_['hatalar'])}\n")
    k = is_.get("kurgu")
    if k:
        satir += (f"🎞 CapCut: `{Path(k.get('capcut', '')).name}` · "
                  f"{k.get('toplam_sn', 0):.0f} sn\n")
    await update.message.reply_text(satir + f"📁 `{is_['dizin']}`",
                                    parse_mode="Markdown")


async def ses_geldi(update: Update, ctx):
    """SENKRON 2. ADIM: seslendirme. BIRDEN COK PARCA kabul eder.

    ⚠ NEDEN PARCALI: Telegram Bot API `getFile` 20MB ile sinirlidir ve bu
    sinir botun dosyayi INDIRMESINDEDIR — dosya Telegram sunucusunda durur,
    bot ona hic erisemez, dolayisiyla KENDISI BOLEMEZ. Bolme kacinilmaz
    olarak GONDEREN tarafta olur. Bu yuzden bot birden cok parca alip
    kendisi BIRLESTIRIR: 30 dk'lik anlatimi ikiye bolup gonderirsin.
    """
    if not _izinli(update):
        return
    sohbet = update.effective_chat.id
    if _BEKLEYEN.get(sohbet) != "senkron_ses":
        await update.message.reply_text(
            "Ses aldım ama sıra onda değil. `/senkron` ile başla.",
            parse_mode="Markdown")
        return
    m = update.message
    nesne = m.voice or m.audio or m.document
    if nesne is None:
        return

    boyut = getattr(nesne, "file_size", 0) or 0
    if boyut > TELEGRAM_INDIRME_TAVAN:
        await m.reply_text(
            f"❌ Bu parça *{boyut / 1048576:.1f} MB* — Telegram botları en "
            f"fazla {TELEGRAM_INDIRME_TAVAN // 1048576} MB indirebiliyor ve "
            "dosya sunucuda durduğu için ben bölemiyorum.\n\n"
            "*İki çözümden biri:*\n"
            "1️⃣ Sıkıştır (30 dk → ~14 MB):\n"
            "```\nffmpeg -i ses.mp3 -ac 1 -b:a 64k kucuk.mp3\n```\n"
            "2️⃣ Parçalara böl, sırayla gönder — ben birleştiririm:\n"
            "```\nffmpeg -i ses.mp3 -f segment -segment_time 900 \\\n"
            "  -c copy parca_%02d.mp3\n```\n"
            "_Sesli mesaj olarak gönderirsen zaten ~7 MB olur, hiç uğraşma._",
            parse_mode="Markdown")
        return

    taslak = _TASLAK.setdefault(sohbet, {})
    if "dizin" not in taslak:
        taslak["ad"] = f"is_{time.strftime('%Y%m%d_%H%M%S')}"
        taslak["dizin"] = str(ayar.is_dizini(taslak["ad"]))
        taslak["parcalar"] = []
    d = Path(taslak["dizin"])
    no = len(taslak["parcalar"]) + 1
    await m.reply_text(f"🎧 {no}. parça indiriliyor… "
                       f"({boyut / 1048576:.1f} MB)")
    try:
        dosya = await ctx.bot.get_file(nesne.file_id)
    except Exception as e:                                   # noqa: BLE001
        await m.reply_text(
            f"❌ Parça indirilemedi ({type(e).__name__}). Sıkıştırıp tekrar "
            "dene:\n```\nffmpeg -i ses.mp3 -ac 1 -b:a 64k kucuk.mp3\n```",
            parse_mode="Markdown")
        return
    uzanti = Path(getattr(nesne, "file_name", "") or "ses.ogg").suffix or ".ogg"
    yol = d / f"ses_parca_{no:02d}{uzanti}"
    await dosya.download_to_drive(str(yol))
    taslak["parcalar"].append(str(yol))

    try:
        toplam = sum(kurgu.sure(Path(x)) for x in taslak["parcalar"])
        sure_yazi = f" · toplam {toplam / 60:.1f} dk"
    except Exception:                                        # noqa: BLE001
        sure_yazi = ""
    await m.reply_text(
        f"✅ {no}. parça alındı{sure_yazi}\n\n"
        "Devamı varsa **sırayla** göndermeye devam et.\n"
        "Ses bittiyse ▶️ `/hazir` yaz, üretime başlayayım.",
        parse_mode="Markdown")


async def _karakter_sor(update: Update, sohbet: int):
    _BEKLEYEN[sohbet] = "senkron_karakter"
    await update.message.reply_text(
        "🧠 *Senkron mod* — sonuç CapCut projesi olur.\n"
        "_Görsel promptları sen yazacaksın; stil sormuyorum._\n\n"
        "*1️⃣ Ana karakter var mı?*\n"
        "Varsa `Ad: betimleme` şeklinde ver — promptunda o adı yazdığın "
        "yere tam betimlemesini koyarım:\n"
        "`Elif: 8 yaşında, kızıl örgülü saçlı, yeşil parkalı bir kız`\n\n"
        "_Adsız da verebilirsin; o zaman promptta_ `@karakter` _yazdığın "
        "yere koyarım._\n\n"
        "Karakter yoksa `yok` yaz.",
        reply_markup=_klavye(["🚫 Karakter yok"]), parse_mode="Markdown")


# ⚠ TELEGRAM 4096 KARAKTER SINIRI: 80+ promptluk bir liste ya da 30 dk'lik
# bir anlatim metni TEK mesaja SIGMAZ. Iki cikis yolu da desteklenir:
#   1) parca parca gonder — biriktirilir
#   2) .txt dosyasi olarak gonder — tek seferde alinir
# Prompt adiminda hedef sayi BELLI oldugu icin (cumle sayisi) sayi tutunca
# kendiliginden ilerler; metin adiminda hedef bilinmedigi icin /tamam gerekir.

async def _metin_parcasi(update: Update, sohbet: int, parca: str):
    """Anlatim metninin bir parcasi geldi — biriktir, ozet ver."""
    parca = (parca or "").strip()
    if not parca:
        return
    taslak = _TASLAK.setdefault(sohbet, {})
    yigin = taslak.setdefault("metin_parcalari", [])
    yigin.append(parca)
    tam = "\n".join(yigin)
    taslak["metin"] = tam
    n = len(beyin.cumlelere_bol(tam))
    await update.message.reply_text(
        f"📝 {len(yigin)}. parça alındı — toplam *{n} cümle* "
        f"({len(tam)} karakter)\n\n"
        "Devamı varsa göndermeye devam et.\n"
        "Metin bittiyse ▶️ `/tamam` yaz.", parse_mode="Markdown")


async def komut_tamam(update: Update, _ctx):
    """Metin bitti -> varsayilan tur sorusuna gec."""
    if not _izinli(update):
        return
    sohbet = update.effective_chat.id
    if _BEKLEYEN.get(sohbet) != "senkron_metin":
        await update.message.reply_text(
            "Şu an metin beklemiyorum. `/senkron` ile başla.",
            parse_mode="Markdown")
        return
    cumleler = beyin.cumlelere_bol((_TASLAK.get(sohbet) or {}).get("metin", ""))
    if not cumleler:
        await update.message.reply_text("Henüz metin gelmedi.")
        return
    _BEKLEYEN[sohbet] = "senkron_mod"
    await update.message.reply_text(
        f"✅ Metin tamam: *{len(cumleler)} cümle*\n"
        f"→ {len(cumleler)} prompt yazacaksın (`/cumleler` ile listeyi "
        "görebilirsin).\n\n*3️⃣ Varsayılan tür ne olsun?*",
        reply_markup=_klavye(list(beyin.MODLAR.values())),
        parse_mode="Markdown")


async def _prompt_parcasi(update: Update, sohbet: int, parca: str):
    """Prompt listesinin bir parcasi geldi — biriktir; sayi tutunca ilerle."""
    taslak = _TASLAK.setdefault(sohbet, {})
    cumleler = beyin.cumlelere_bol(taslak.get("metin", ""))
    hedef = len(cumleler)
    yigin = taslak.setdefault("promptlar", [])
    yeni = beyin.promptlari_ayristir(parca)
    if not yeni:
        return
    yigin.extend(yeni)

    if len(yigin) < hedef:
        kalan = hedef - len(yigin)
        await update.message.reply_text(
            f"📥 *{len(yigin)}/{hedef}* prompt alındı — {kalan} tane daha "
            "bekliyorum.\n_Kaldığın yerden devam et._\n\n"
            "Yanlış gittiyse `/sifirla` ile promptları temizle.",
            parse_mode="Markdown")
        return

    if len(yigin) > hedef:
        # ⚠ FAZLA PROMPT = KAYMA: hangisinin fazla oldugunu bilemeyiz, o
        # yuzden kesip devam ETMEYIZ. Kullanici temizleyip yeniden yollar.
        taslak["promptlar"] = []
        await update.message.reply_text(
            f"⚠ *{hedef} cümle* var ama *{len(yigin)} prompt* geldi.\n"
            "Fazlanın hangisi olduğunu bilemem; kesersem sonraki tüm "
            "cümleler yanlış görüntüye bağlanır.\n\n"
            "Promptları temizledim — `/cumleler` ile listeye bakıp "
            f"tam {hedef} satır olarak tekrar gönder.", parse_mode="Markdown")
        return

    _BEKLEYEN[sohbet] = "senkron_ses"
    v = sum(1 for e, _ in yigin if e == "video")
    g = sum(1 for e, _ in yigin if e == "gorsel")
    ezme = f" ({v} video + {g} görsel satır bazında ezildi)" if v or g else ""
    await update.message.reply_text(
        f"✅ {hedef} prompt tamam{ezme}\n\n"
        "*5️⃣ Şimdi SESLENDİRMEYİ gönder* (ses dosyası ya da sesli mesaj).\n"
        "_Metnin tamamının okunmuş hali olmalı._\n\n"
        "Uzunsa parçalara bölüp **sırayla** gönderebilirsin. "
        "Bitince `/hazir` yaz.", parse_mode="Markdown")


async def komut_sifirla(update: Update, _ctx):
    """Biriken promptlari (ya da metni) temizler — bastan yollamak icin."""
    if not _izinli(update):
        return
    sohbet = update.effective_chat.id
    kip = _BEKLEYEN.get(sohbet)
    taslak = _TASLAK.get(sohbet) or {}
    if kip == "senkron_promptlar":
        taslak["promptlar"] = []
        n = len(beyin.cumlelere_bol(taslak.get("metin", "")))
        await update.message.reply_text(
            f"🧹 Promptlar temizlendi. {n} satır olarak tekrar gönder.")
    elif kip == "senkron_metin":
        taslak["metin_parcalari"] = []
        taslak["metin"] = ""
        await update.message.reply_text("🧹 Metin temizlendi. Tekrar gönder.")
    else:
        await update.message.reply_text("Temizlenecek bir şey yok.")


async def belge_geldi(update: Update, ctx):
    """.txt dosyasi: metin ya da prompt listesi olarak alinir.

    ⚠ 80+ prompt icin EN PRATIK YOL budur — mesaj sinirina hic takilmaz.
    """
    if not _izinli(update):
        return
    sohbet = update.effective_chat.id
    kip = _BEKLEYEN.get(sohbet)
    if kip not in ("senkron_metin", "senkron_promptlar"):
        await update.message.reply_text(
            "Dosya aldım ama sırası değil. `/senkron` ile başla.",
            parse_mode="Markdown")
        return
    belge = update.message.document
    if belge is None:
        return
    if (belge.file_size or 0) > 2 * 1024 * 1024:
        await update.message.reply_text("❌ Dosya çok büyük (en fazla 2 MB).")
        return
    try:
        dosya = await ctx.bot.get_file(belge.file_id)
        ham = bytes(await dosya.download_as_bytearray())
    except Exception as e:                                   # noqa: BLE001
        await update.message.reply_text(f"❌ Dosya alınamadı ({type(e).__name__}).")
        return
    for kodlama in ("utf-8", "utf-8-sig", "cp1254", "latin-1"):
        try:
            icerik = ham.decode(kodlama)
            break
        except UnicodeDecodeError:
            continue
    else:
        await update.message.reply_text(
            "❌ Dosya okunamadı — düz metin (.txt), UTF-8 olmalı.")
        return
    await update.message.reply_text(f"📄 `{belge.file_name}` okundu.",
                                    parse_mode="Markdown")
    if kip == "senkron_metin":
        await _metin_parcasi(update, sohbet, icerik)
    else:
        await _prompt_parcasi(update, sohbet, icerik)


async def komut_cumleler(update: Update, _ctx):
    """Metnin nasil cumlelere bolundugunu GOSTERIR — prompt sayisi tutsun."""
    taslak = _TASLAK.get(update.effective_chat.id) or {}
    cumleler = beyin.cumlelere_bol(taslak.get("metin", ""))
    if not cumleler:
        await update.message.reply_text("Önce `/senkron` → metin gönder.",
                                        parse_mode="Markdown")
        return
    satir = [f"{i}. {c}" for i, c in enumerate(cumleler, 1)]
    # Telegram mesaj siniri 4096 — uzun metinlerde parcala.
    yigin, boy = [], 0
    for x in satir:
        if boy + len(x) > 3500:
            await update.message.reply_text("\n".join(yigin))
            yigin, boy = [], 0
        yigin.append(x); boy += len(x) + 1
    if yigin:
        await update.message.reply_text(
            "\n".join(yigin) + f"\n\n→ *{len(cumleler)} prompt* yaz.",
            parse_mode="Markdown")


async def komut_hazir(update: Update, ctx):
    """Ses parcalari tamam -> birlestir -> tam akisi baslat."""
    if not _izinli(update):
        return
    sohbet = update.effective_chat.id
    taslak = _TASLAK.get(sohbet) or {}
    parcalar = taslak.get("parcalar") or []
    if _BEKLEYEN.get(sohbet) != "senkron_ses" or not parcalar:
        await update.message.reply_text(
            "Önce `/senkron` → metin → ses gönder.", parse_mode="Markdown")
        return
    _BEKLEYEN.pop(sohbet, None)
    _TASLAK.pop(sohbet, None)
    d = Path(taslak["dizin"])
    try:
        if len(parcalar) > 1:
            await update.message.reply_text(
                f"🔗 {len(parcalar)} parça birleştiriliyor…")
        ses_yolu = await asyncio.to_thread(
            kurgu.sesleri_birlestir, [Path(x) for x in parcalar],
            d / "seslendirme.m4a")
    except kurgu.KurguHatasi as e:
        _BEKLEYEN[sohbet] = "senkron_ses"
        _TASLAK[sohbet] = taslak
        await update.message.reply_text(f"❌ Ses birleştirilemedi: {e}")
        return
    await _senkron_yurut(update, ctx, taslak["ad"], d,
                         taslak.get("metin", ""), ses_yolu, taslak)


async def metin_geldi(update: Update, ctx):
    if not _izinli(update):
        return
    sohbet = update.effective_chat.id
    kip = _BEKLEYEN.get(sohbet)
    if kip is None:
        await update.message.reply_text(
            "Mod seç: 🎬 `/hikaye` · 🧠 `/senkron`", parse_mode="Markdown")
        return

    if kip == "senkron_karakter":
        cevap = (update.message.text or "").strip()
        atla = cevap.lower() in ("yok", "/gec", "gec", "geç", "🚫 karakter yok")
        _BEKLEYEN[sohbet] = "senkron_metin"
        if atla:
            bilgi = "✅ Karakter yok.\n\n"
        else:
            # ⚠ NE ENJEKTE EDILECEGINI KULLANICI GORMELI (22 Agu 2026):
            # karakter alanina tam bir prompt yapistirilirsa ("referans
            # sayfasi, uc gorunus, sahne yok...") o metin sahne promptuna
            # girip sahneyi ZEHIRLER ve referans sayfasi uretilir. Artik
            # sadelestirip GOSTERIYORUZ; yanlissa kullanici hemen gorur.
            kisa = beyin.karakter_sadelestir(cevap)
            _TASLAK.setdefault(sohbet, {})["karakter_ham"] = cevap
            cevap = kisa                       # enjekte edilecek olan BU
            ad, _b = beyin.karakter_ayristir(kisa)
            bilgi = ("✅ Karakter kaydedildi"
                     + (f" — promptunda *{ad}* yazdığın yere koyacağım.\n"
                        if ad else
                        " — promptunda `@karakter` yazdığın yere koyacağım.\n")
                     + f"\n_Promptlara şu eklenecek:_\n`{kisa[:350]}`\n\n"
                     + ("_Uzun metnini görünüş tarifine indirgedim; sahne "
                        "promptunu bozmasın diye._\n\n"
                        if len(_TASLAK[sohbet]["karakter_ham"]) > len(kisa) + 20
                        else ""))
        # ⚠ KAYIT SADELESTIRMEDEN SONRA: once kaydedilirse HAM metin saklanir
        # ve kullaniciya gosterilenle enjekte edilen FARKLI olur.
        _TASLAK.setdefault(sohbet, {})["karakter"] = "" if atla else cevap
        await update.message.reply_text(
            bilgi + "*2️⃣ Şimdi anlatım METNİNİ gönder* (düz metin, her dilde)."
            "\n\nUzunsa iki yol var:\n"
            "· **parça parça** gönder — biriktiririm\n"
            "· ya da **.txt dosyası** olarak at — tek seferde alırım\n\n"
            "Metin bitince ▶️ `/tamam` yaz.",
            reply_markup=ReplyKeyboardRemove(), parse_mode="Markdown")
        return

    if kip == "senkron_mod":
        t = (update.message.text or "").strip()
        mod = next((k for k, v in beyin.MODLAR.items() if v == t), None)
        if mod is None:
            await update.message.reply_text(
                "Listeden birini seç.",
                reply_markup=_klavye(list(beyin.MODLAR.values())))
            return
        _TASLAK[sohbet]["mod"] = mod
        _BEKLEYEN[sohbet] = "senkron_promptlar"
        n = len(beyin.cumlelere_bol(_TASLAK[sohbet]["metin"]))
        await update.message.reply_text(
            f"*4️⃣ Şimdi {n} PROMPTU gönder* — her satır bir cümle, "
            "sırayla.\n\n"
            "```\n1. Karlı sokak, wide shot, 2D çizgi film\n"
            "2. Elif kapıyı açıyor, medium shot\n"
            "3. video: Kar taneleri düşüyor, yavaş dolly-in\n```\n"
            f"· Varsayılan tür: *{beyin.MODLAR[mod]}*\n"
            "· Bir satırı `video:` ya da `görsel:` ile başlatırsan o satır "
            "için varsayılanı ezersin\n"
            "· Satır başı numarası isteğe bağlı\n\n"
            f"⚠ *{n} satır tek mesaja sığmaz* (Telegram sınırı 4096 karakter). "
            "**Parça parça** gönder — kaçta kaç olduğunu sayarım, tamamlanınca "
            "kendiliğinden devam ederim. Ya da hepsini bir **.txt dosyası** "
            "olarak at.\n"
            "_Karıştırırsan_ `/sifirla` _ile promptları temizle._",
            reply_markup=ReplyKeyboardRemove(), parse_mode="Markdown")
        return

    if kip == "senkron_promptlar":
        return await _prompt_parcasi(update, sohbet, update.message.text)

    if kip == "senkron_metin":
        # ⚠ TELEGRAM MESAJ SINIRI 4096 KARAKTER: uzun anlatim TEK mesaja
        # sigmaz, kullanici bolerek gonderir. Eskiden her parca oncekini
        # EZIYORDU — sessizce metnin yalnizca son parcasi kaliyordu.
        # Artik biriktirilir; kullanici /tamam deyince kapanir.
        return await _metin_parcasi(update, sohbet, update.message.text)

    if kip == "senkron_ses":
        await update.message.reply_text(
            "🎧 Sırada SESLENDİRME var — metin değil. Ses dosyası gönder "
            "ya da `/iptal`.", parse_mode="Markdown")
        return

    # ── HIKAYE: hazir prompt blogu ──
    _BEKLEYEN.pop(sohbet, None)
    videolar, gorseller = _blok_coz(update.message.text)
    if not (videolar or gorseller):
        await update.message.reply_text("Blok boş görünüyor — `/hikaye` ile tekrar.")
        return

    ad = f"is_{time.strftime('%Y%m%d_%H%M%S')}"
    d = ayar.is_dizini(ad)
    is_ = {"ad": ad, "dizin": str(d), "kip": "hikaye",
           "video_promptlari": videolar, "gorsel_promptlari": gorseller,
           "cumleler": {}, "durum": "uretim", "sonuclar": {}, "hatalar": []}
    _SON_IS[sohbet] = is_
    _kaydet(is_)
    _CALISAN.add(sohbet)
    _IPTAL.discard(sohbet)
    await update.message.reply_text(
        f"🚀 Başlıyorum — 🎬 {len(videolar)} video + 🖼 {len(gorseller)} görsel.\n"
        f"📁 `{d}`", parse_mode="Markdown")

    async with _akitici(ctx, sohbet) as bildir:
        def iptal_mi():
            return sohbet in _IPTAL
        try:
            vids = await asyncio.to_thread(
                flow_surucu.parti_uret, videolar, "video", d / "video",
                bildir, iptal_mi, None)
            gors = await asyncio.to_thread(
                flow_surucu.parti_uret, gorseller, "gorsel", d / "gorsel",
                bildir, iptal_mi, None)
            is_["sonuclar"] = {"video": vids, "gorsel": gors}
            is_["hatalar"] = [f"{x['tur']}[{x['sira']}] {x['neden']}"
                              for x in (vids + gors) if not x["ok"]]
            is_["durum"] = "bitti" if not is_["hatalar"] else "bitti-eksikli"
            _kaydet(is_)
            baslik, detay = _ozet(is_, vids, gors, d)
            await ctx.bot.send_message(sohbet, baslik, parse_mode="Markdown")
            if detay:
                await ctx.bot.send_message(sohbet, detay[:3500])
        except Exception as e:                               # noqa: BLE001
            is_["durum"] = "hata"
            is_["hatalar"].append(f"{type(e).__name__}: {e}")
            _kaydet(is_)
            await ctx.bot.send_message(
                sohbet, f"❌ Beklenmeyen hata: {type(e).__name__}: {str(e)[:200]}")
        finally:
            _CALISAN.discard(sohbet)
            _IPTAL.discard(sohbet)


def _ozet(is_: dict, vids: list, gors: list, d: Path) -> tuple:
    """(baslik_markdown, detay_duz_metin) doner.

    ⚠ HATA METNI MARKDOWN OLARAK GONDERILEMEZ: icinde `gorsel[4]`,
    `chrome_baslat.sh`, dosya yollari gecer; Telegram `[...]`'i link,
    `_`'yi italik sanar ve mesaj okunamaz hale gelir (21 Agu 2026'da
    kullanicinin ekraninda goruldu). Detay AYRI ve DUZ gonderilir.
    """
    ok_v = sum(1 for x in vids if x["ok"])
    ok_g = sum(1 for x in gors if x["ok"])
    hatalar = is_.get("hatalar") or []
    baslik = (f"✅ *ÜRETİM BİTTİ*\n🎬 {ok_v}/{len(vids)} video · "
              f"🖼 {ok_g}/{len(gors)} görsel\n📁 `{d}`")
    if not hatalar:
        return baslik + "\n👍 Hata yok.", ""
    baslik += f"\n\n⚠ *{len(hatalar)} başarısız* — ayrıntı aşağıda."
    # Ayni nedenden dusen onlarca satiri tek tek yazmak ekrani doldurur;
    # nedene gore GRUPLA.
    gruplar = {}
    for h in hatalar:
        _, _, neden = h.partition("] ")
        gruplar.setdefault(neden.strip() or h, []).append(h.split("]")[0] + "]")
    satir = []
    for neden, ogeler in list(gruplar.items())[:5]:
        satir.append(f"• {len(ogeler)} adet — {neden[:300]}")
        satir.append(f"   ({', '.join(ogeler[:10])}"
                     f"{'…' if len(ogeler) > 10 else ''})")
    if len(gruplar) > 5:
        satir.append(f"… {len(gruplar) - 5} farklı hata daha (is.json içinde)")
    return baslik, "\n".join(satir)


class _akitici:
    """Arka plan is parcaciklarindan gelen ilerlemeyi Telegram'a akitir.

    ⚠ NEDEN AYRI: uretim `asyncio.to_thread` icinde doner; oradan dogrudan
    `await` edilemez. Kuyruk + tuketici gorev ile mesajlar sirayla cikar.
    """

    def __init__(self, ctx, sohbet):
        self.ctx, self.sohbet = ctx, sohbet
        self.kuyruk: asyncio.Queue = asyncio.Queue()

    async def __aenter__(self):
        async def tuket():
            while True:
                m = await self.kuyruk.get()
                if m is None:
                    break
                try:
                    await self.ctx.bot.send_message(self.sohbet, m[:400])
                except Exception:
                    pass
        self.gorev = asyncio.create_task(tuket())

        def bildir(m):
            try:
                self.kuyruk.put_nowait(m)
            except Exception:
                pass
        return bildir

    async def __aexit__(self, *_):
        await self.kuyruk.put(None)
        await self.gorev
        return False


async def _senkron_yurut(update: Update, ctx, ad: str, d: Path, metin: str,
                         ses_yolu: Path, secim: dict = None):
    """SENKRON TAM AKIS: plan -> Flow uretimi -> ses hizalama -> CapCut.

    ⚠ SONUC BIR CAPCUT PROJESIDIR, duz mp4 degil: kullanici gecis/yazi/efekt
    eklemek istiyor (kullanici karari, 21 Agu 2026). Yine de kontrol icin
    duz `final.mp4` de yazilir.
    """
    sohbet = update.effective_chat.id
    if not metin:
        await ctx.bot.send_message(sohbet, "Metin kayboldu — `/senkron` ile tekrar.")
        return
    _CALISAN.add(sohbet)
    _IPTAL.discard(sohbet)

    async with _akitici(ctx, sohbet) as bildir:
        def iptal_mi():
            return sohbet in _IPTAL
        is_ = {"ad": ad, "dizin": str(d), "kip": "senkron",
               "ses": str(ses_yolu), "video_promptlari": [],
               "gorsel_promptlari": [], "cumleler": {}, "durum": "plan",
               "sonuclar": {}, "hatalar": []}
        _SON_IS[sohbet] = is_
        try:
            secim = secim or {}
            karakter = secim.get("karakter", "")
            mod = secim.get("mod", "karisik")
            is_.update({"karakter": karakter, "mod": mod})
            # ⚠ LLM YOK: promptlari kullanici yazdi. Burada yalnizca karakter
            # betimlemesi yerlestirilir ve tur (video/gorsel) belirlenir.
            plan = beyin.plan_elle(beyin.cumlelere_bol(metin),
                                   secim.get("promptlar") or [],
                                   karakter, mod)
            if not plan:
                await ctx.bot.send_message(sohbet, "Metin boş — `/senkron` tekrar.")
                return
            videolar = [(p["sira"], p["prompt"]) for p in plan if p["tur"] == "video"]
            gorseller = [(p["sira"], p["prompt"]) for p in plan if p["tur"] == "gorsel"]
            is_.update({"video_promptlari": [p for _, p in videolar],
                        "gorsel_promptlari": [p for _, p in gorseller],
                        "cumleler": {str(p["sira"]): p["cumle"] for p in plan},
                        "durum": "uretim"})
            _kaydet(is_)
            await ctx.bot.send_message(
                sohbet, f"📋 {beyin.plan_ozeti(plan)}"
                        f"{' · 🧍 karakter yerleştirildi' if karakter else ''}"
                        f"\n📁 `{d}`\nÜretime başlıyorum — bu uzun sürebilir.",
                parse_mode="Markdown")

            # ⚠ URETIM COKSE BILE IS COPE GITMEZ (22 Agu 2026): 179 promptluk
            # is 168. adimda Flow arayuzu kaybolunca TimeoutError ile oldu ve
            # CapCut adimina HIC gelemedi. Artik hata yakalanir, o ana kadar
            # inen ne varsa onunla kurguya devam edilir.
            vids, gors = [], []
            try:
                vids = await asyncio.to_thread(
                    flow_surucu.uret_tekrarli, [p for _, p in videolar], "video",
                    d / "video", bildir, iptal_mi, None, [s for s, _ in videolar])
                gors = await asyncio.to_thread(
                    flow_surucu.uret_tekrarli, [p for _, p in gorseller], "gorsel",
                    d / "gorsel", bildir, iptal_mi, None,
                    [s for s, _ in gorseller])
            except Exception as e:                           # noqa: BLE001
                is_["hatalar"].append(f"uretim yarida kesildi: "
                                      f"{type(e).__name__}: {str(e)[:200]}")
                _kaydet(is_)
                await ctx.bot.send_message(
                    sohbet, f"⚠ Üretim yarıda kesildi ({type(e).__name__}).\n"
                            "İnen dosyalarla kurguya devam ediyorum — "
                            "eksik cümlelerde önceki görüntü uzayacak.")
            is_["sonuclar"] = {"video": vids, "gorsel": gors}
            is_["hatalar"] = [f"{x['tur']}[{x['sira']}] {x['neden']}"
                              for x in (vids + gors) if not x["ok"]]
            _kaydet(is_)
            baslik, detay = _ozet(is_, vids, gors, d)
            await ctx.bot.send_message(sohbet, baslik, parse_mode="Markdown")
            if detay:
                await ctx.bot.send_message(sohbet, detay[:3500])

            # ── ESLESME: cumle no -> inen dosya (CapCut dizilimi bunu okur) ──
            # ⚠ DISKTEN OKU, sonuc listesinden DEGIL: uretim yarida kesilse
            # ya da tekrar denemede dosya adi degisse bile diskteki gercek
            # durum dogru olandir. Dosya adinin basindaki sayi = cumle no.
            eslesme = {}
            for alt in ("video", "gorsel"):
                for yol in sorted((d / alt).glob("*")):
                    m = re.match(r"0*(\d+)_", yol.name)
                    if m and yol.is_file():
                        eslesme[str(int(m.group(1)))] = str(yol)
            eksik = [p["sira"] for p in plan if str(p["sira"]) not in eslesme]
            if eksik:
                # ⚠ ARTIK DURMUYORUZ (22 Agu 2026 kullanici karari): eksik
                # cumlenin araligi ONCEKI SAHNE UZATILARAK kapatilir. Ses hic
                # kaymaz; izleyici bosluk gormez, sadece bir goruntu daha uzun
                # kalir. Durmak, 183 cumlelik isi 1 eksik yuzunden copa atardi.
                await ctx.bot.send_message(
                    sohbet,
                    f"⚠ {len(eksik)} cümlenin medyası üretilemedi "
                    f"({', '.join(str(x) for x in eksik[:12])}"
                    f"{'…' if len(eksik) > 12 else ''}).\n"
                    "Bu cümlelerde *önceki görüntü daha uzun kalacak* — "
                    "ses kaymayacak.", parse_mode="Markdown")
            Path(d, "eslesme.json").write_text(
                json.dumps(eslesme, ensure_ascii=False, indent=2),
                encoding="utf-8")
            Path(d, "metin.txt").write_text(metin, encoding="utf-8")

            # ── HIZALAMA + CAPCUT ──
            is_["durum"] = "kurgu"
            _kaydet(is_)
            await ctx.bot.send_message(
                sohbet, "🎚 Sesle hizalayıp CapCut'a diziyorum…")
            proje = f"HAYALET_{time.strftime('%m%d_%H%M')}"
            kunye = await asyncio.to_thread(
                kurgu.kurgula, metin, ses_yolu, d, d / "final.mp4",
                False, proje, bildir)
            is_["durum"] = "bitti"
            is_["kurgu"] = kunye
            _kaydet(is_)
            await ctx.bot.send_message(
                sohbet,
                f"🎬 *HAZIR — CapCut'ta aç*\n\n"
                f"Proje: *{proje}*\n"
                f"{len(plan)} klip · {kunye['toplam_sn']:.0f} sn\n"
                f"Hizalama: _{kunye['yontem']}_\n\n"
                f"CapCut'ı kapat-aç, proje listesinde görünür. Her cümle ayrı "
                f"klip; geçiş/yazı/efekt eklemen için hazır.\n"
                f"📁 Kontrol videosu: `{d}/final.mp4`", parse_mode="Markdown")
        except kurgu.KurguHatasi as e:
            is_["durum"] = "kurgu-hatasi"
            is_["hatalar"].append(str(e))
            _kaydet(is_)
            await ctx.bot.send_message(
                sohbet, f"❌ Kurgu yapılamadı:\n`{str(e)[:600]}`\n\n"
                        f"Üretilen dosyalar duruyor: `{d}`",
                parse_mode="Markdown")
        except Exception as e:                               # noqa: BLE001
            is_["durum"] = "hata"
            is_["hatalar"].append(f"{type(e).__name__}: {e}")
            _kaydet(is_)
            await ctx.bot.send_message(
                sohbet, f"❌ Beklenmeyen hata: {type(e).__name__}: {str(e)[:200]}")
        finally:
            _CALISAN.discard(sohbet)
            _IPTAL.discard(sohbet)


def calistir():
    eksik = ayar.eksik_ayarlar()
    if eksik:
        print("EKSIK AYAR:")
        for e in eksik:
            print(f"  · {e}")
        raise SystemExit(1)
    app = Application.builder().token(ayar.TELEGRAM_TOKEN).build()
    for ad, fn in (("start", komut_start), ("basla", komut_basla),
                   ("hikaye", komut_hikaye), ("senkron", komut_senkron),
                   ("hazir", komut_hazir), ("cumleler", komut_cumleler),
                   ("tamam", komut_tamam), ("sifirla", komut_sifirla),
                   ("durum", komut_durum), ("iptal", komut_iptal)):
        app.add_handler(CommandHandler(ad, fn))
    # ⚠ SES ISLEYICISI METINDEN ONCE: sesli mesaj/ses dosyasi /senkron'un
    # 2. adimidir; TEXT filtresi bunlari zaten yakalamaz ama sirayi acik tut.
    app.add_handler(MessageHandler(
        filters.VOICE | filters.AUDIO | filters.Document.AUDIO, ses_geldi))
    # .txt: uzun metin / uzun prompt listesi — mesaj sinirini tamamen atlar.
    app.add_handler(MessageHandler(
        filters.Document.ALL & ~filters.Document.AUDIO, belge_geldi))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, metin_geldi))

    # ⚠ TEMIZ KAPANIS: pencere kapatilinca (SIGTERM/SIGINT) python-telegram-bot
    # kapanis anindaki ag cagrisini yarida kesiyor ve ~200 satirlik traceback
    # basiyor. Kullanici bunu COKME saniyor. Kapaniyor mu diye bayrak tutup
    # o durumda tek satir yaziyoruz; GERCEK hatalar (yanlis token vb.) ise
    # net sekilde gorunmeye devam ediyor.
    # Kapanis aninda yarida kalan coroutine icin PTB uyari basiyor —
    # zararsiz ama kullaniciyi telaslandiriyor.
    warnings.filterwarnings("ignore", message=".*never awaited.*",
                            category=RuntimeWarning)
    kapaniyor = {"evet": False}

    # ⚠ TRACEBACK'I except YAKALAYAMAZ: python-telegram-bot kapanis anindaki
    # ag hatasini KENDI LOGGER'INA basar (logger.exception), exception olarak
    # yukari firlatmaz. Logger'a filtre takmak da YETMEZ — bir logger'in
    # filtresi yalnizca O logger'a dogrudan yazilan kayitlara uygulanir,
    # alt logger'lardan (telegram.ext.*) propagate edilenlere DEGIL.
    # Tek kesin yol: kapanis basladigi anda loglamayi global olarak kapatmak.
    def _kapan(*_):
        kapaniyor["evet"] = True
        logging.disable(logging.CRITICAL)
        raise SystemExit(0)

    for _sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        try:
            signal.signal(_sig, _kapan)
        except (ValueError, OSError):
            pass

    print(f"👻 Hayalet calisiyor. Klasor koku: {ayar.KOK}")
    try:
        app.run_polling(stop_signals=None)
    except (KeyboardInterrupt, SystemExit):
        pass
    except Exception as e:                                   # noqa: BLE001
        if not kapaniyor["evet"]:
            print(f"\n❌ Bot durdu: {type(e).__name__}: {str(e)[:300]}")
            if "token" in str(e).lower() or "Unauthorized" in str(e):
                print("   → Telegram token yanlis olabilir: "
                      f"{ayar.GIZLI_ENV}")
            raise SystemExit(1)
    print("👻 Hayalet kapandi.")


if __name__ == "__main__":
    calistir()
```

## Dosya: `hayalet/chrome_baslat.sh`
```bash
#!/bin/bash
# Chrome'u UZAKTAN KONTROL portuyla baslatir (Hayalet buna baglanir).
# ⚠ Mevcut Chrome profilin ve Google oturumun AYNEN kullanilir.
PORT="${HAYALET_CHROME_PORT:-9222}"
case "$(uname -s)" in
  Darwin) CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";;
  Linux)  CHROME="$(command -v google-chrome || command -v chromium || command -v chromium-browser)";;
  *)      CHROME="$(command -v chrome)";;
esac
[ -x "$CHROME" ] || { echo "HATA: Chrome bulunamadi"; exit 1; }
if curl -s --max-time 2 "http://127.0.0.1:$PORT/json/version" >/dev/null 2>&1; then
  echo "✓ Chrome zaten $PORT portunda dinliyor"; exit 0
fi
echo "Chrome baslatiliyor (port $PORT)…"
"$CHROME" --remote-debugging-port="$PORT" \
  --user-data-dir="$HOME/.hayalet/chrome-profil" >/dev/null 2>&1 &
sleep 3
curl -s --max-time 3 "http://127.0.0.1:$PORT/json/version" >/dev/null 2>&1 \
  && echo "✓ hazir — acilan pencerede Google hesabina giris yap" \
  || echo "⚠ port yanit vermedi, birkaç saniye sonra tekrar dene"
```

---

# BÖLÜM 2 — KURULUM VE KULLANIM

## CLAUDE İÇİN KURULUM TALİMATLARI

### 0) Sistem tespiti
```bash
uname -s   # Darwin=macOS, Linux=Linux; Windows ise WSL2 öner
```

### 1) Araçlar
**macOS:** `brew install python@3.11 ffmpeg` (brew yoksa önce onu kur)
**Linux:** `sudo apt update && sudo apt install -y python3 python3-pip curl ffmpeg`

`ffmpeg` **zorunlu** — kurgu/hizalama onunla yapılır. Doğrula:
```bash
ffmpeg -version | head -1 && ffprobe -version | head -1
```

⚠ Altyazıyı görüntüye yakmak istiyorsan ffmpeg **libass** ile derlenmiş
olmalı. Kontrol:
```bash
ffmpeg -hide_banner -filters | grep -c " subtitles "
```
`0` dönerse yakma yok — SRT gömülü iz olarak eklenir (oynatıcıdan açılır).
Zaten yazıları CapCut'ta eklemek daha iyi; bu bir engel değil.

### 2) Python paketleri
```bash
python3 -m pip install --user --upgrade "python-telegram-bot>=21" playwright
```

### 3) Chrome kurulu olmalı
macOS: `/Applications/Google Chrome.app` var mı? Linux: `command -v google-chrome`.
Yoksa kullanıcıya https://google.com/chrome indirt.

### 3.5) CapCut kurulu olmalı + EN AZ BİR PROJESİ olmalı
CapCut'ın taslak formatı **belgelenmiş değildir** ve sürümden sürüme
değişir. Bu yüzden şema tahmin EDİLMEZ — kullanıcının **kendi CapCut'ındaki
gerçek bir projeden** kopyalanır (`hayalet/capcut.py` → `bagisci_bul`).
Böylece kurulu sürümle birebir uyumlu taslak üretilir.

Kullanıcıya söyle: CapCut'ı aç, **bir video + bir ses** zaman çizgisine
koyup kaydet, kapat. Bir kez yeterli. Doğrula:
```bash
python3 -c "
import sys; sys.path.insert(0,'.')
from hayalet.capcut import bagisci_bul
b = bagisci_bul(); print('✓ şablon:', b['yol'].parent.name,
                         '| CapCut', b['taslak'].get('new_version'))"
```
Hata verirse kullanıcı henüz uygun bir proje kaydetmemiştir.

### 4) Kullanıcıya KENDİ Telegram botunu kurdur
Kullanıcıya aynen şunu söyle:
1. Telegram'da **@BotFather**'ı aç
2. `/newbot` → bota isim ver → BotFather bir **token** verir (`12345:AAF...`)
3. Token'ı bana yapıştır
4. Kendi botunu Telegram'da açıp **/start** yaz (bot ancak önce sen yazınca cevap verebilir)

Token gelince (ASLA koda/repoya yazma):
```bash
mkdir -p ~/.hayalet && chmod 700 ~/.hayalet
echo "HAYALET_TELEGRAM_TOKEN=BURAYA_TOKEN" > ~/.hayalet/gizli.env
chmod 600 ~/.hayalet/gizli.env
TOKEN=$(grep TOKEN ~/.hayalet/gizli.env | cut -d= -f2)
curl -s "https://api.telegram.org/bot$TOKEN/getMe"   # "ok":true dönmeli
```

### 4.5) OpenAI anahtarı (senkron mod için ŞART)
İki yerde kullanılır: (a) her cümle için sinematik prompt yazımı,
(b) **cümle sınırlarının sesten çıkarılması** (ASR kelime zaman damgaları).
```bash
echo "HAYALET_OPENAI_KEY=sk-..." >> ~/.hayalet/gizli.env
```
Anahtar yoksa: promptlar cümlenin kendisi olur **ve** hizalama karakter
oranına düşer (kayma birikir). `/hikaye` modu anahtarsız çalışır.

### 5) Chrome'u kontrol portuyla başlat + Flow'a giriş
```bash
bash hayalet/chrome_baslat.sh
```
> ⚠ Bu adım **Flow'a giriş yapman içindir**. Üretim sırasında Playwright
> Chrome'u kendisi başlatır ve gerekirse bu pencereyi kapatıp yeniden açar
> — giriş kalıcı profilde durduğu için oturumun kaybolmaz.

Açılan pencere **temiz bir profildir** (normal Chrome'undan ayrı —
`~/.hayalet/chrome-profil`). Bu pencerede:
1. **Flow erişimi olan Google hesabına** giriş yap (hangi hesapta Flow
   aboneliğin varsa O hesap — yanlış hesapla girersen Flow açılmaz)
2. **https://labs.google/fx/tools/flow** adresini açıp Flow'un yüklendiğini gör

Giriş **bir keredir** — profil kalıcı, sonraki açılışlarda oturum durur.
Pencere üretim boyunca açık kalmalı.

### 5.5) Flow Agent ayarları (BİR KEZ — otomasyonun ön koşulu)
Flow'da bir proje aç (**New project**) ve prompt kutusunun yanındaki
**ayar (tune)** ikonuna bas:
1. **Confirm before generating → NEVER** seç
   ("Agent will generate media and spend credits automatically")
   — *Always kalırsa ajan her prompt'ta onay sorar ve otomasyon takılır.*
2. **Image generation default → x1** seç (x2 = her prompt'ta 2 görsel = 2 kat kredi)
3. Oranlar 16:9 kalsın · **Save**
4. **Proje adresini kopyala** (`.../flow/project/<uuid>`) ve kaydet:
   ```bash
   echo "HAYALET_FLOW_URL=<kopyaladığın adres>" >> ~/.hayalet/gizli.env
   ```
   Prompt kutusu yalnızca proje içinde vardır; bu olmadan üretim başlamaz.

Bu ayar profile kaydedilir, bir kez yapılır.

### 6) Flow seçici kalibrasyonu (arayüz DEĞİŞİRSE)
```bash
python3 -c "
import sys; sys.path.insert(0,'.')
from hayalet import flow_surucu
from pathlib import Path
r = flow_surucu.kesfet(Path('hayalet/flow_kesif.json'))
print('URL:', r['url'])
print('textarea:', r['textarea'][:5])
print('dugmeler:', [d['metin'] for d in r['dugme'][:12]])
"
```
Çıktıdaki gerçek alan/buton adlarına göre `hayalet/flow_surucu.py` içindeki
**`SECICILER`** tablosunu güncelle (tek nokta, kod dağılmaz).

### 7) Botu başlat
```bash
python3 -m hayalet.bot
```
`👻 Hayalet calisiyor` görünmeli; terminal açık kalır.
(İstenirse kalıcı: macOS'ta `launchd`, Linux'ta `systemd --user` servisi kur.)

---

## KULLANIM — iki mod

### 🎬 `/hikaye` — hazır promptlarını verirsin
Promptları TEK BLOK gönderirsin:
```
VIDEO PROMPT 1 - şafakta limandan çıkan balıkçı teknesi
GÖRSEL PROMPT 1 - yaşlı balıkçının portresi
```
Çıktılar diske iner; Telegram'a yalnızca ilerleme/hata düşer.

### 🧠 `/senkron` — metin + ses verirsin, CapCut projesi çıkar

**1.** Telegram'da `/senkron` yaz
**2.** **ANA KARAKTER** ver, ya da `yok` de
**3.** Anlatım **METNİNİ** gönder → parça parça ya da `.txt` dosyası
   olarak; bitince `/tamam` yaz
**4.** **VARSAYILAN TÜR** seç: karışık / tamamı görsel / tamamı video
**5.** **PROMPTLARI** gönder — her satır bir cümle, sırayla; parça parça
   ya da `.txt` dosyası olarak
**6.** **SESLENDİRMEYİ** gönder — uzunsa parçalara bölüp sırayla
**7.** `/hazir` yaz → Flow → indirme → hizalama → CapCut

> Stil sorusu **yoktur**: promptları sen yazdığın için stil zaten onların
> içindedir. Sistemin ayrıca stil dayatması promptu bozardı.

#### Ana karakter
`Ad: betimleme` biçiminde verirsin:
```
Elif: 8 yaşında, kızıl örgülü saçlı, yeşil parkalı bir kız
```
Promptunda **`Elif`** yazdığın yere tam betimlemeyi koyar. Adsız da
verebilirsin; o zaman promptta **`@karakter`** yazdığın yere koyar.
Promptta karaktere atıf yoksa prompt **aynen kalır** — manzara kareleri
bozulmaz.

> ⚠ **Neden yerine koyuyor?** Flow her promptu bağımsız üretir, önceki
> kareyi hatırlamaz. Sadece "Elif" yazmak yetmez; Elif'in kim olduğunu
> bilmez. Betimlemenin her seferinde yeniden yazılması tutarlılığın tek
> yoludur.
>
> ⚠ Betimleme **metindir**, fotoğraf değil. Flow'a gerçek referans fotoğrafı
> yüklemek tarayıcı otomasyonunda ayrı bir iş; henüz yok.

#### Promptlar
Her satır bir cümleye karşılık gelir. Satır başı numarası isteğe bağlı.
```
1. Karlı bir sokak, wide shot, kalın konturlu 2D çizgi film
2. video: Elif kapıyı açıyor, medium shot, yavaş dolly-in
3. Boş sokak, kuş bakışı, pastel renkler
```
Bir satırı `video:` ya da `görsel:` ile başlatırsan o satır için varsayılan
türü ezersin.

⚠ **Prompt sayısı cümle sayısına EŞİT olmalı.** Bir satır kayarsa sonraki
tüm cümleler yanlış görüntüye bağlanır ve bu sessizce olur.

#### 80+ prompt nasıl gönderilir
Telegram mesaj sınırı **4096 karakter** — 80 promptluk bir liste tek mesaja
sığmaz, Telegram onu bölerek gönderir. İki çözüm var:

**1. Parça parça gönder.** Bot biriktirir ve kaçta kaç olduğunu söyler
(`📥 45/81 prompt alındı — 36 tane daha bekliyorum`). Sayı tamamlanınca
kendiliğinden ses adımına geçer. Aynısı metin için de geçerli — orada
hedef sayı bilinmediği için bitince `/tamam` yazarsın.

**2. `.txt` dosyası olarak at.** *(en pratik yol)* Sınır tamamen atlanır,
81 prompt tek seferde alınır. UTF-8 düz metin, en fazla 2 MB. Aynı yol
anlatım metni için de çalışır.

| Komut | Ne yapar |
|---|---|
| `/cumleler` | Metnin tam olarak nasıl bölündüğünü listeler |
| `/tamam` | Metin bitti, sonraki adıma geç |
| `/sifirla` | Biriken promptları (ya da metni) temizle |

⚠ **Fazla prompt gelirse bot keser mi?** Hayır. Hangisinin fazla olduğunu
bilemeyeceği için hepsini temizler ve baştan ister — kesmek sonraki tüm
cümleleri kaydırırdı.

#### Varsayılan tür
| Seçenek | Ne olur |
|---|---|
| 🎞 İlk %30 video, kalanı görsel | Belgesel/anlatı için *(varsayılan)* |
| 🖼 Tamamı görsel | Hiç video yok — **animasyon/çizgi kanallar için** |
| 🎬 Tamamı video | Her cümle video *(en pahalı, en yavaş)* |

**Cümle sınırları nasıl bulunur** (sırayla denenir, hangisi kullanıldığı
her zaman yazılır — sessiz düşüş yok):

| # | Yöntem | Ne zaman | Doğruluk |
|---|---|---|---|
| 1 | Cümle başına ayrı ses dosyası | `--ses` bir klasörse | **Kesin** |
| 2 | ASR kelime zaman damgaları | OpenAI anahtarı varsa | **Çok iyi** |
| 3 | `silencedetect` duraklamaları | duraklama sayısı = cümle sayısı-1 | İyi |
| 4 | Karakter oranı | hiçbiri olmazsa | **Yaklaşık** (uyarır) |

> Ölçüm (21 Ağu 2026): macOS `say` ile üretilmiş 5 cümlelik TR anlatımda
> ASR sınırları, sesteki gerçek duraklamalarla **0.05–0.17 sn** içinde
> örtüştü. Aynı seste varsayılan eşikle `silencedetect` **hiç** duraklama
> bulamadı — bu yüzden ASR birincil yöntemdir.

⚠ **Telegram bot indirmesi 20MB ile sınırlıdır** (senin gönderme sınırın
2GB ama bot o kadarını *alamaz*). Bot dosyayı indirmeye kalkışmadan önce
boyuta bakar ve ne yapacağını söyler.

| 30 dk ses | Boyut | |
|---|---|---|
| Sesli mesaj (Telegram opus) | ~7 MB | ✅ |
| mp3 64kbps mono | ~14 MB | ✅ |
| m4a 96kbps | ~22 MB | ❌ |
| mp3 128kbps stereo | ~29 MB | ❌ |

**Çözüm 1 — sıkıştır** (30 dk → ~14 MB):
```bash
ffmpeg -i ses.mp3 -ac 1 -b:a 64k kucuk.mp3
```

**Çözüm 2 — parçalara böl, sırayla gönder** (bot birleştirir):
```bash
ffmpeg -i ses.mp3 -f segment -segment_time 900 -c copy parca_%02d.mp3
```
Parçaları **sırayla** gönder, bitince `/hazir` yaz. Parçalar farklı
formatlarda olabilir (sesli mesaj + mp3 + m4a karışık) — bot hepsini tek
formata getirip birleştirir ve süre kaybı olmadığını doğrular.

> ⚠ **Bot dosyayı kendisi bölemez.** 20MB sınırı botun *indirmesindedir*;
> dosya Telegram sunucusunda durur, bot ona hiç erişemez. Bölme kaçınılmaz
> olarak gönderen tarafta olur.

64kbps mono'da tek parça tavanı **~41 dakika**. Ses kalitesi hizalamayı
etkilemez — ASR zaten 16kHz mono'ya indirerek çözümler.

⚠ **UZUN ANLATIM = ÇOK ÜRETİM.** Bu maliyeti önceden bil: 30 dakikalık bir
anlatım kabaca **400-450 cümledir**. Kural gereği ilk %30'u video demek
~130 video klibi + ~300 görsel demektir. Flow'da video klipleri dakikalarca
sürer; bu iş **saatler** alır ve ciddi kredi harcar. Önce 2-3 dakikalık bir
metinle uçtan uca dene, sonucu gör, sonra uzun metne geç.

⚠ **Tek bir cümlenin medyası üretilemezse CapCut dizilimi YAPILMAZ.**
Eksik klip sırayı kaydırıp sessizce yanlış senkron üretir; bot durur ve
hangi cümlelerin eksik olduğunu söyler. Dosyalar diskte durur.

### 🎚 Telegram'sız kullanım (elle kurgu)

Dosyalar zaten diskteyse doğrudan:
```bash
python3 -m hayalet.kurgu --metin metin.txt --ses seslendirme.m4a \
    --medya ~/Desktop/Hayalet/is_xxx --cikti final.mp4 --capcut "PROJE_ADI"
```
Hangi medya hangi cümleye: dosya adının başındaki sayı (`001_`, `002_`)
ya da medya klasöründeki `eslesme.json`. `--capcut` vermezsen sadece düz
`final.mp4` üretir.

⚠ **CapCut kapalıyken çalıştır**, sonra aç — açık CapCut taslak klasörünü
kendi hafızasından üzerine yazabilir.

## YAŞANMIŞ HATALAR (gerçek kurulumlardan — oku, aynısını yaşama)

> **Claude'a talimat:** Bu bölüm YAŞAYAN bir kayıttır. Kurulumda veya
> kullanımda YENİ bir hata çözersen, buraya *belirti → kök neden → çözüm*
> formatında EKLE ve commit'le. Sonraki kuran kişi aynı duvara çarpmasın.

### 1) `Chrome'a baglanilamadi (http://127.0.0.1:9222)` — her prompt'ta
- **Yaşandı:** 20 Ağu 2026, ilk gerçek deneme. `/basla` yazıldı ama
  `chrome_baslat.sh` hiç çalıştırılmamıştı; 10 prompt tek tek bu hatayı aldı.
- **Kök neden:** Ajan senin Chrome'una debug portundan (9222) bağlanır;
  Chrome normal açılmışsa o port kapalıdır.
- **Çözüm:** `bash hayalet/chrome_baslat.sh` → açılan pencerede Google girişi
  + Flow. Bot artık üretime başlamadan portu yoklar ve hazır değilse tek
  mesajla söyler (scriptin kaybolmaz, tekrar gönderirsin).

### 2) Açılan Chrome'da Google oturumu yok / Flow açılmıyor
- **Kök neden:** `chrome_baslat.sh` TEMİZ profil açar — günlük Chrome'undaki
  oturum orada yoktur. Ayrıca Flow her Google hesabında yok; aboneliğin
  hangi hesaptaysa onunla girilmeli.
- **Çözüm:** Açılan pencerede Flow'lu hesabınla BİR KEZ giriş yap; profil
  kalıcıdır.

### 3) `telegram.error.Conflict: terminated by other getUpdates request`
- **Kök neden:** Aynı bot token'ıyla İKİ bot süreci çalışıyor (eski süreç
  ölmeden yenisi açılmış) — Telegram tek dinleyiciye izin verir.
- **Çözüm:** `pkill -f hayalet.bot` → 2 sn bekle → `python3 -m hayalet.bot`.
  Herkes KENDİ token'ını kullanmalı; token paylaşılırsa botlar birbirini düşürür.

### 5) Ajan her prompt'ta onay soruyor / üretim başlamıyor
- **Yaşandı:** 20 Ağu 2026, canlı kalibrasyon. Flow'un agent arayüzü
  varsayılan "Confirm before generating: Always" ile geliyor.
- **Çözüm:** Adım 5.5 — Agent settings → **Never** + Image **x1** + Save.

### 6) Her prompt'ta 2 görsel üretiliyor (kredi 2x gidiyor)
- **Kök neden:** Agent settings'te Image default **x2** seçili geliyordu.
- **Çözüm:** Adım 5.5'teki **x1**.

### 7) CapCut projeyi listeliyor ama AÇMIYOR (tıklayınca hiçbir şey olmuyor)
- **Yaşandı:** 21 Ağu 2026, CapCut 9.3.0 taslak üretimi geliştirilirken.
  Proje listede göründü, çift tıklamada sessizce hiçbir şey olmadı; log yok.
- **Kök neden:** Gerçek projelerde `draft_info.json` içindeki `id`,
  `Timelines/<UUID>` klasör adı ve `Timelines/project.json` içindeki
  `main_timeline_id` **aynı UUID** olmak zorunda. Üçü farklı olunca CapCut
  taslağı listeler ama yükleyemez ve sessizce vazgeçer.
- **Çözüm:** `capcut.py` üçünü tek `zc_id`'den üretir. Doğrula:
  ```bash
  python3 -c "
  import json,os,sys; d=sys.argv[1]
  i=json.load(open(f'{d}/draft_info.json'))['id']
  t=[x for x in os.listdir(f'{d}/Timelines') if not x.endswith('.json')][0]
  m=json.load(open(f'{d}/Timelines/project.json'))['main_timeline_id']
  print('ÜÇÜ AYNI' if i==t==m else f'FARKLI: {i} {t} {m}')" <taslak_klasörü>
  ```

### 8) CapCut açılıyor ama klipler kırmızı: "Dosya erişilemiyor"
- **Yaşandı:** 21 Ağu 2026. Klipler `/tmp` altındayken de,
  `~/Desktop` altındayken de kırmızı çıktı; `~/Downloads` altındaki
  medyayı olan gerçek projeler sorunsuzdu.
- **Kök neden:** macOS TCC — CapCut'ın Masaüstü/Belgeler klasörlerine
  erişim izni olmayabilir. `/tmp` zaten sandbox dışı.
- **Çözüm:** `capcut.py` klipleri taslağın kendi içine
  (`<taslak>/Resources/hayalet/`) **kopyalar**; orası CapCut'ın kendi veri
  klasörüdür, izin gerekmez. Taslak büyür ama kırık medya olmaz.

### 9) `Timelines/project.json` şeması uydurulursa proje bozulur
- **Kök neden:** Bu dosyanın gerçek şeması
  `{config, create_time, id, main_timeline_id, timelines:[…], version}`.
  Tahmini bir şema (ör. `{current_timeline_id, timeline_ids}`) yazılırsa
  proje açılmaz. Ayrıca `timeline_layout.json` de zaman çizgisi UUID'sine
  işaret eder — bağışçıdan olduğu gibi kopyalanmamalı.
- **Çözüm:** İkisi de `capcut.py` içinde üretilir, kopyalanmaz.

### 23) Flow'un İKİ farklı ayar arayüzü — otomasyonu bozan iki ayar
- **Yaşandı:** 23 Ağu 2026, başka bir hesabın projesine geçilince.
- **Kök neden:** Flow projeleri iki farklı arayüzle gelebiliyor:
  - **A)** Prompt kutusunun yanında görünür çip (`Video · 720p · 10s
    crop_16_9 x1`) — tıklayınca sekmeler açılır.
  - **B)** Çip YOK; ayarlar `tune|Ayarlar` düğmesinin arkasındaki
    "Ajan ayarları" panelinde.
  B'de iki ayar otomasyonu bozuyordu:
  - "Üretme işleminden önce onaylayın: **Her zaman**" → ajan her promptta
    onay sorar, üretim hiç başlamaz.
  - "Varsayılan görüntü üretimi: **x2**" → her promptta 2 görsel,
    **iki katı kredi**.
- **Çözüm:** `flow_surucu.flow_ayarla()` her iki arayüzü de tanıyor;
  üretimden önce onayı kapatıyor, adedi x1 yapıyor, oranı 16:9'a sabitliyor.
- **Tuzak 1:** Ayar paneli prompt görünümünün YERİNE açılıyor; Escape her
  zaman geri getirmiyordu, her partide sayfa yenilenip ~40 sn boşa gidiyordu.
- **Tuzak 2:** Panelden dönmek için `arrow_back` tıklamak **projeden
  tamamen çıkarıyor** (sol üstteki "Geri Dön"); üretim 0/3'e düştü.
  Doğru yol: proje adresine doğrudan `goto`.

### 24) Chrome profilini/hesabını değiştirme
Hayalet izole bir profil kullanır; gerçek profilinden **kopyalanır**
(mock-keychain bayrakları kalktığı için artık çalışıyor, bkz. madde 15):
```bash
K=~/Library/Application\ Support/Google/Chrome
H=~/.hayalet/chrome-profil
pkill -f "user-data-dir=$H"; rm -rf "$H"; mkdir -p "$H/Default"; touch "$H/First Run"
rsync -a --exclude='Cache' --exclude='Code Cache' --exclude='GPUCache' \
      --exclude='Service Worker/CacheStorage' --exclude='blob_storage' \
      --exclude='Extensions' "$K/Profile N/" "$H/Default/"
cp "$K/Local State" "$H/Local State"
```
Profil numarasını bulmak için `Local State` → `profile.info_cache` içindeki
`user_name` alanına bak. Sonra `HAYALET_FLOW_URL`'i o hesabın proje
adresiyle güncelle.

### 22) Görüntü 1-2 saniyede bir değişiyor — izlemesi yorucu
- **Yaşandı:** 22 Ağu 2026, 179 cümlelik gerçek iş. Cümle başına bir görsel
  konunca ortanca klip **2.14 sn**, %70'i 3 sn altında, 24 tanesi 1 sn'den
  kısa çıktı. Stroboskop etkisi.
- **Çözüm:** `kurgu.sahneleri_grupla()` — kısa cümleler önceki sahneye
  katılır, sahne `HAYALET_EN_KISA_SAHNE` (varsayılan **5 sn**) eşiğine
  ulaşana kadar büyür. Ses **hiç kaymaz**: süreler toplanır, toplam sabit.
  Grubun görüntüsü ilk cümlenin görselidir; diğerleri diskte kalır.
- **Ölçüm:** 179 klip / ortanca 2.14 sn → **68 klip / ortanca 6.2 sn**,
  en kısa 5.0, en uzun 10.0, 1 sn altında klip **0**.
- **Neden karakter sayısı değil süre:** karakter sayısı sürenin dolaylı
  tahminidir (konuşma hızı değişir); ASR'den gelen gerçek süreler zaten
  elimizde ve ekranda kalma süresini doğrudan verir.
- **Eşik denemeleri (aynı iş):** 3 sn→92 klip · 4→78 · 5→68 · 6→56 ·
  7→50 · 8→44 klip.

### 21) Üretim ortasında `Locator.click: Timeout 30000ms` — tüm iş ölüyor
- **Yaşandı:** 22 Ağu 2026. 179 promptluk iş 147. adımda çöktü; prompt
  kutusu (`div[contenteditable='true']`) sayfadan kayboldu. Bot
  "Beklenmeyen hata" deyip durdu ve **CapCut adımına hiç gelemedi** —
  o ana kadar inen 146 görsel boşa gidiyordu.
- **Kök neden (iki katmanlı):**
  1. Flow arayüzü uzun oturumlarda prompt kutusunu kaybedebiliyor.
  2. Üretim bir istisna atınca `_senkron_yurut` komple düşüyordu.
- **Çözüm 1 — kurtarma:** Her prompttan önce kutu var mı kontrol edilir;
  yoksa **sayfa yenilenir**, tür/oran yeniden ayarlanır ve devam edilir.
  Tıklamalarda 30 sn yerine 15 sn zaman aşımı.
- **Çözüm 2 — iş çöpe gitmesin:** Üretim çökse bile yakalanır ve **o ana
  kadar inenlerle kurguya devam edilir**; eksik cümlelerde önceki görüntü
  uzar (bkz. madde 18).
- **Çözüm 3 — eşleşme diskten:** Cümle→dosya eşleşmesi artık sonuç
  listesinden değil, **diskteki gerçek dosyalardan** kurulur (dosya adının
  başındaki sayı = cümle no). Yarıda kesilen iş de doğru eşleşir.
- **Yarım kalan işi sürdürme:** eksik cümleler `is.json` içindeki
  promptlardan yeniden üretilip aynı klasöre indirilebilir; sonra
  `kurgu.kurgula(...)` CapCut projesini kurar. Baştan başlamak gerekmez.

### 19) Karakter yerine ÜÇ GÖRÜNÜŞLÜ REFERANS SAYFASI üretiliyor
- **Yaşandı:** 22 Ağu 2026. Karakter alanına 1575 karakterlik **tam bir
  referans-sayfası promptu** yapıştırıldı ("A character reference sheet: the
  same man drawn three times side by side… **No scene, no text**… STYLE…
  COLOUR… 16:9, high resolution"). Kod bu metni `@karakter` geçen her yere
  **olduğu gibi** enjekte etti; sahne promptu zehirlendi ve Flow sahne
  yerine referans sayfası üretti.
- **Kök neden:** Enjeksiyon metninde uzunluk sınırı ve akıl kontrolü yoktu.
  Karaktere yalnızca **görünüş** tarifi girmeli; stil/oran/"sahne yok" gibi
  meta talimatlar sahneyi ele geçirir.
- **Çözüm:** `beyin.karakter_sadelestir()` — meta işaretleri (`reference
  sheet`, `no scene`, `16:9`, bölüm başlıkları…) ya da 260 karakter sınırı
  aşılırsa metin LLM ile **tek satırlık görünüş cümlesine** indirgenir
  (LLM yoksa CHARACTER/CLOTHING bölümleri toplanır). Kelime ortadan
  bölünmez. Bot enjekte edilecek hali **kullanıcıya gösterir**.
- **Doğrulandı (canlı):** 1575 → 249 karakter; aynı prompt artık kapı
  önünde duran adamı üretiyor (gri saç, sakal, turuncu yakalı mavi ceket
  korunmuş), referans sayfası değil.

### 20) Çalışan botun tarayıcısı aniden kapanıyor
- **Yaşandı:** 22 Ağu 2026. Bot iş yaparken ikinci bir Hayalet süreci
  başlatıldı; `_profil_chromeu_kapat` botun Chrome'unu kapattı ve iş yarıda
  öldü.
- **Kök neden:** İki süreç aynı Chrome profilini paylaşamaz.
- **Çözüm:** `chrome_baglan` başka bir `hayalet.bot` süreci varsa bağlanmayı
  **reddediyor** ve net söylüyor. Bilerek geçmek için `HAYALET_KILIT_YOKSAY=1`.

### 18) Bazı promptlar üretilemiyor — iş çöpe gitmesin
- **Belirti:** Flow tek tek promptlarda "might violate our policies" ya da
  geçici hata verebiliyor; o cümle medyasız kalır.
- **Çözüm 1 — tekrar dene:** `uret_tekrarli()` başarısızları toplayıp
  yeniden gönderiyor (`HAYALET_TEKRAR`, varsayılan 2 ek tur). Aynı prompt
  ikinci denemede çoğu zaman geçiyor.
- **Çözüm 2 — boşluğu önceki sahneyle kapat:** Kalıcı olarak üretilemeyen
  cümlelerde **artık durmuyoruz**. O cümlenin süresi bir önceki sahneye
  eklenir; önceki görüntü ekranda daha uzun kalır (ör. 2 sn yerine 7.6 sn).
  Ses **hiç kaymaz**, izleyici boşluk görmez.
- **Doğrulandı (canlı):** 5 cümle, 2'sinin medyası yok →
  `5 cümle → 3 klip`, 1. klip 2.04 sn yerine **7.64 sn**;
  ses 11.26 sn / video 11.23 sn → **fark 0.02 sn**.
- Künyede `medyasiz_cumleler` ve `uzatilan_cumle` alanları tutulur.

### 17) Üretim neredeyse hiç ilerlemiyor (2 saatte 2 görsel)
- **Yaşandı:** 22 Ağu 2026, 183 promptluk gerçek iş. 2 saatte yalnızca 2
  görsel indi; inen dosyalar 001 ve 021 — aradaki cümleler hiç üretilmedi.
- **Kök neden:** `parti_uret` tek mesajda 10 numaralı prompt gönderiyordu.
  Flow ajanı bu mesaja **parti başına yalnızca 1 görsel** üretiyor. Kalan 9
  hiç gelmiyor, bot tavan dolana kadar (45 dk) boşuna bekleyip sonraki
  partiye geçiyor. Yani toplu gönderim hızlandırmıyor, **kilitliyor**.
- **Çözüm:** `HAYALET_PARTI` varsayılanı **1** yapıldı — her prompt ayrı
  gönderilir. Ayrıca tek üretim tavanı gerçekçi tutuldu
  (`HAYALET_GORSEL_TAVAN`=240 sn, `HAYALET_VIDEO_TAVAN`=900 sn).
- **Ölçüm (canlı):** 3/3 başarılı, **görsel başına 30 saniye**.
  183 görsel ≈ **1.5 saat** (eski haliyle ~190 saat sürerdi).
- **Toplu gönderim tekrar denendi (22 Ağu, çıktı türü doğruyken):**
  5 prompt tek mesajda → **2 dakikada 0 görsel**; aynı sürede tekli modda
  ~4 görsel indi. Ajan toplu promptu kabul ediyor ama işlemesi çok yavaş.
  Karar: tekli mod kalıyor.

### 16) "Görsel" seçtim ama VİDEO üretiyor
- **Yaşandı:** 21 Ağu 2026. Tüm cümleler görsel seçilmesine rağmen video çıktı.
- **Kök neden:** Çıktı türü de Flow ayarıdır — panelde `Image` / `Video`
  sekmeleri var ve **seçili olan kazanır**. Prompttaki
  "Generate one image:" ifadesi bunu **ezmez**. Ayar "Video"da kalmıştı.
- **Çözüm:** `flow_surucu.tur_ayarla()` her partiden önce türü ayarlıyor
  (görsel partisi → Image, video partisi → Video).
- **Doğrulandı:** canlı üretim → `.png`, 1376x768 (video değil).

### 14) Görseller/videolar 16:9 değil, dikey (9:16) çıkıyor
- **Yaşandı:** 21 Ağu 2026. Tüm çıktılar dikey geldi.
- **Kök neden:** Oran **prompta yazılmaz** — Flow projesinin kendi ayarıdır
  ve varsayılanı 9:16 olabiliyor. Prompta "16:9" eklemek işe yaramaz.
- **Çözüm:** `flow_surucu.oran_ayarla()` her partiden önce oranı kontrol
  edip gerekirse düzeltiyor. Zaten doğruysa dokunmuyor.
  Değiştirmek için: `~/.hayalet/gizli.env` içine `HAYALET_ORAN=9:16`.
- **Tuzak:** Ayar çipine körlemesine tıklamak, panel **zaten açıksa onu
  kapatır**. Kod önce sekmenin görünür olup olmadığına bakıyor.
- **Doğrulandı:** canlı üretim → inen dosya 1280x720 (oran 1.778).

### 15) Chrome'a bağlanılıyor ama Flow oturumsuz — çerezler okunmuyor
- **Yaşandı:** 21 Ağu 2026. Kullanıcı defalarca giriş yaptı, her seferinde
  otomasyon oturumu göremedi ve çerezleri ezdi.
- **Kök neden:** Playwright macOS'ta Chrome'a `--use-mock-keychain` ve
  `--password-store=basic` bayraklarını **varsayılan olarak** ekler. Bunlar
  Chrome'un Keychain'deki çerez şifreleme anahtarına erişmesini engeller;
  çerezler diskte durur ama **çözülemez**. Elle başlatılan Chrome'da sorun
  çıkmamasının sebebi budur.
- **Çözüm:** `ignore_default_args=["--use-mock-keychain",
  "--password-store=basic"]`.
- **Yan sonuç:** Bu bayraklar kalkınca, gerçek Chrome profilini kopyalayarak
  oturum taşımak da **çalışır hale geldi** (önce çalışmıyordu — sebebi aynı
  bayraklardı). `rsync` ile profil kopyalanıp 18 oturum çerezi taşındı ve
  Flow açıldı. Günlük Chrome'a hiç dokunulmadı.

### 13) Flow "tanıtım sayfası" açılıyor — oturum yok
- **Belirti:** Proje adresi doğru ama sayfada "Try in Google Flow",
  "Pricing" yazıyor; prompt kutusu yok.
- **Kök neden:** Hayalet'in izole Chrome profilinde Google oturumu açılmamış.
- **Çözüm:** `bash hayalet/chrome_baslat.sh` ile açılan pencerede **Flow
  aboneliği olan hesapla giriş yap**. Bir kez yeterli; oturum profilde kalır.
- ⚠ **Profil kopyalayarak oturum TAŞINMAZ** (21 Ağu 2026'da denendi ve
  ölçüldü). macOS'ta çerez anahtarı Keychain'de ve uygulamaya bağlı;
  `Local State` dahil kopyalansa bile Flow oturumsuz açılıyor.
- **Gerçek profilini kullanmak istersen** (ör. "Curtis"), `~/.hayalet/gizli.env`:
  ```
  HAYALET_CHROME_ANA_DIZIN=/Users/<sen>/Library/Application Support/Google/Chrome
  HAYALET_CHROME_PROFIL_ADI=Profile 48
  ```
  ⚠ Bu yolda **günlük Chrome'un tamamen kapalı olmalı** — Chrome aynı veri
  dizinini iki süreçle açamaz. Bot bunu kontrol edip net söyler. Günlük
  Chrome'unu açık tutmak istiyorsan izole profilde giriş yap (yukarısı).

### 12) "Flow acildi ama PROMPT KUTUSU bulunamadi"
- **Kök neden:** Prompt kutusu Flow'un giriş sayfasında değil, bir
  **projenin içinde** bulunur. Artık Chrome'u Playwright başlattığı için
  taze sekme giriş sayfasına düşer.
- **Çözüm:** Proje adresini sabitle — bir kez:
  ```bash
  # Flow'da projeyi aç, adres çubuğundaki .../flow/project/<uuid> adresini kopyala
  echo "HAYALET_FLOW_URL=https://labs.google/fx/tools/flow/project/<uuid>" >> ~/.hayalet/gizli.env
  ```
  Sonra botu yeniden başlat. Bot bunu doğrulayıp bulamazsa 15 dakika
  beklemek yerine hemen bu talimatı yazar.

### 10) `Browser.setDownloadBehavior: Browser context management is not supported`
- **Yaşandı:** 21 Ağu 2026. Her prompt bu hatayla düştü, hiçbir görsel
  üretilmedi. Chrome 151.0.7922.170 + Playwright 1.60.0.
- **Kök neden:** Playwright'ın `connect_over_cdp` çağrısı bağlanırken
  `Browser.setDownloadBehavior` gönderir; Chrome 151 bunu artık reddediyor.
  Playwright 1.60 **en yeni sürüm** — güncellemek çözmüyor.
- **Çözüm:** Artık çalışan Chrome'a bağlanmak yerine **Playwright Chrome'u
  kendisi başlatıyor** (`launch_persistent_context(channel="chrome")`).
  Chrome 151'de çalıştığı ölçüldü. Aynı kalıcı profil kullanıldığı için
  Flow oturumu korunur. CDP yolu önce yine denenir (eski Chrome'larda
  çalışır), olmazsa bu yola düşer.
- **Yan etki:** O profille açık bir Chrome varsa **kapatılıp yeniden
  açılır** (yalnızca Hayalet profilini kullanan pencere; günlük Chrome'una
  dokunulmaz). Giriş profilde durduğu için oturum kaybolmaz.

### 11) Hata mesajları Telegram'da link/italik olup okunamıyor
- **Yaşandı:** 21 Ağu 2026, yukarıdaki hatanın raporunda.
- **Kök neden:** Özet `parse_mode="Markdown"` ile gönderiliyordu; hata
  metnindeki `gorsel[4]` link, `chrome_baslat.sh` içindeki `_` italik
  sanıldı ve mesaj karmakarışık göründü.
- **Çözüm:** Başlık Markdown, **ayrıntı ayrı ve düz metin** olarak
  gönderiliyor. Ayrıca aynı nedenden düşen satırlar gruplanıyor
  (20 satırlık tekrar yerine tek satır + numaralar).

### 4) 🛑 "arka arkaya 3 hata — durduruldu"
- **Kök neden:** Yapısal sorun sinyali: Flow oturumu düşmüş, arayüz değişmiş
  (seçiciler eski) ya da Chrome penceresi kapanmış.
- **Çözüm:** Chrome penceresi + Flow oturumu yerinde mi bak; değilse Adım 5.
  Yerindeyse Adım 6 (seçici kalibrasyonu) tekrar.

## Sorun giderme

| Belirti | Çözüm |
|---|---|
| `Chrome'a baglanilamadi` | `bash hayalet/chrome_baslat.sh`; pencereyi kapatma |
| `prompt alani bulunamadi` | Flow arayüzü değişti → Adım 6 kalibrasyonu |
| `sonuc gorunmedi` (15 dk) | `HAYALET_FLOW_TAVAN` artır (`~/.hayalet/gizli.env` içine, sn) |
| Bot cevap vermiyor | `getMe` testi (Adım 4); botuna Telegram'dan `/start` yazdın mı? |
| 🛑 art arda 3 hata | Chrome'da Flow oturumu düşmüş olabilir — giriş yap, `/basla` tekrar |

## Bilinen sınırlar (dürüstçe)
- Flow otomasyonu **kırılgandır**: Google arayüzü değişince Adım 6 tekrar gerekir.
  Sistem bunu sessizce geçmez, net hatayla söyler.
- Otomatik erişim Google ToS'ta gri alan — kendi hesabın, kendi riskin.
- Hız Flow'un üretim hızıdır; promptlar sırayla işlenir.
