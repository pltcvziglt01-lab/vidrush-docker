# 👻 HAYALET — Telegram'dan Google Flow Üretim Ajanı (TAM PAKET)

> **NASIL KULLANILIR:** Bu dosyayı Claude Code'a at ve şunu yaz:
> **"Bu dosyadaki sistemi kur"**. Claude önce aşağıdaki KOD bölümündeki
> dosyaları aynen oluşturur, sonra KURULUM adımlarını işletim sistemine göre
> sırayla uygular. Senden sadece 2 şey ister:
> 1) Kendi Telegram bot token'ın (@BotFather'dan)
> 2) Açılan Chrome penceresinde **Flow erişimi olan Google hesabınla** giriş

Bu sistem: Telegram'dan prompt bloğu gönderirsin → bilgisayarındaki
Chrome'da Google Flow'a girip görselleri/videoları üretir → masaüstünde
`Hayalet/is_<tarih>/video/` ve `gorsel/` klasörlerine indirir → Telegram'dan
ilerleme/hata bildirir. Dosyalar Telegram'a gönderilmez, diskte kalır.
Edit/kurgu yok — montajı kendin yaparsın.

---

# BÖLÜM 1 — KOD (Claude: bu dosyaları AYNEN oluştur)

Proje için boş bir klasör aç (ör. `~/hayalet-ajan`), içine `hayalet/` paketi:

## Dosya: `hayalet/__init__.py`
```python
# bos
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

⚠ KAPSAM: KURGU/EDIT YOK. Bu ajan yalnizca URETIR, INDIRIR, KLASORLER;
montaji kullanici kendi araciyla yapar (kullanici karari, 20 Agu 2026).
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
CHROME_CDP = os.environ.get("HAYALET_CHROME_CDP", "http://127.0.0.1:9222")
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


def chrome_baglan():
    """Kullanicinin acik Chrome'una CDP ile baglan. Baglanamazsa NET hata."""
    pw = sync_playwright().start()
    try:
        tarayici = pw.chromium.connect_over_cdp(ayar.CHROME_CDP)
    except Exception as e:
        pw.stop()
        raise FlowHatasi(
            f"Chrome'a baglanilamadi ({ayar.CHROME_CDP}). Chrome'u su komutla "
            f"baslat:\n  bash hayalet/chrome_baslat.sh\n"
            f"Ayrinti: {type(e).__name__}: {str(e)[:120]}")
    baglam = tarayici.contexts[0] if tarayici.contexts else tarayici.new_context()
    return pw, tarayici, baglam


def kesfet(cikti: Path = None) -> dict:
    """TESHIS: Flow sayfasindaki girdi/dugme adaylarini doker.

    Secici tablosu kirildiginda ONCE bu calistirilir; ciktidan `SECICILER`
    guncellenir. Boylece 'neden calismiyor' korlemesine aranmaz.
    """
    pw, _t, baglam = chrome_baglan()
    try:
        sayfa = _flow_sayfasi(baglam)
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


def _flow_sayfasi(baglam):
    """Acik sekmelerde Flow varsa ONU kullan; yoksa yeni sekmede ac."""
    for s in baglam.pages:
        if "labs.google" in (s.url or ""):
            s.bring_to_front()
            return s
    sayfa = baglam.new_page()
    sayfa.goto(ayar.FLOW_URL, wait_until="domcontentloaded", timeout=60000)
    return sayfa


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
        pw, _t, baglam = chrome_baglan()
        sayfa = _flow_sayfasi(baglam)
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


PARTI_BOYU = int(__import__("os").environ.get("HAYALET_PARTI", "10"))


def parti_uret(promptlar: list, tur: str, hedef_dizin: Path, bildir=None,
               iptal_mi=None) -> list:
    """PROMPTLARI 10'AR VERIP ciktilari BELIRDIKCE indirir (ajan modu).

    ⚠ NEDEN PARTI: ajan arayuzu sohbet tabanli — tek mesajda numarali N
    prompt verilebilir; ajan SIRAYLA uretir. Tek tek gondermeye gore cok
    daha hizli (her prompt icin ayri baglanti+bekleme yok).
    ⚠ ESLEME SINIRI (durust): cikti->prompt eslesmesi BELIRME SIRASIYLA
    yapilir; ajan sirayi bozarsa dosya adi yanlis prompta denk gelebilir.
    Icerik DOGRU iner; yalnizca adlandirma kayabilir. is.json'da parti
    kaydi tutulur.
    """
    def _bildir(m):
        if bildir:
            try:
                bildir(m)
            except Exception:
                pass

    temiz = [(i + 1, (p or "").strip()) for i, p in enumerate(promptlar)
             if (p or "").strip()]
    if not temiz:
        return []
    sonuclar = []
    partiler = [temiz[i:i + PARTI_BOYU] for i in range(0, len(temiz), PARTI_BOYU)]
    pw = None
    try:
        pw, _t, baglam = chrome_baglan()
        sayfa = _flow_sayfasi(baglam)
        for p_no, parti in enumerate(partiler, 1):
            if iptal_mi is not None and iptal_mi():
                _bildir("🛑 iptal edildi")
                break
            onceki = _medya_srcleri(sayfa, tur)
            tur_ad = "videos" if tur == "video" else "images"
            mesaj = (f"Generate {len(parti)} separate {tur_ad}, one for each "
                     f"numbered prompt below. Do not ask questions, do not "
                     f"combine them, generate all:\n"
                     + "\n".join(f"{i}. {p}" for i, p in parti))
            try:
                sayfa.locator(SECICILER["temizle_dugme"][0]).first.click(timeout=2000)
            except Exception:
                pass
            girdi = sayfa.locator(SECICILER["prompt_girdi"][0]).last
            girdi.click()
            # type() cok satirda Enter'i GONDER sanabilir -> panoya benzer insert
            sayfa.keyboard.insert_text(mesaj)
            sayfa.locator(SECICILER["uret_dugme"][0]).last.click()
            _bildir(f"📦 parti {p_no}/{len(partiler)}: {len(parti)} prompt gonderildi")

            beklenen = len(parti)
            inen = {}
            bas = time.time()
            tavan = ayar.FLOW_URETIM_TAVAN_SN * max(1, beklenen // 3)
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
                        sonuclar.append({"ok": True, "dosya": str(hedef),
                                         "neden": "", "prompt": prompt,
                                         "sira": sira, "tur": tur})
                        _bildir(f"✅ {tur} {len(sonuclar)}/{len(temiz)} indi "
                                f"— devam ediyorum")
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
import re
import time
from pathlib import Path

from telegram import Update
from telegram.ext import (Application, CommandHandler, MessageHandler, filters)

from . import ayar, flow_surucu

_BEKLEYEN = set()    # /basla demis, tek-blok script bekleyen sohbetler
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
        "👻 *Hayalet* hazır.\n\n"
        "`/basla` yaz → promptları TEK BLOK gönder:\n\n"
        "```\nVIDEO PROMPT 1 - şafakta limandan çıkan balıkçı teknesi\nVIDEO PROMPT 2 - dalgalar güverteyi dövüyor\nGÖRSEL PROMPT 1 - yaşlı balıkçının portresi\nGÖRSEL PROMPT 2 - limanda mezat sabahı\n```\n"
        "Dosyalar bilgisayarına iner; buraya sadece durum düşer.\n"
        "`/durum` · `/iptal`", parse_mode="Markdown")


async def komut_basla(update: Update, _ctx):
    if not _izinli(update):
        return
    sohbet = update.effective_chat.id
    if sohbet in _CALISAN:
        await update.message.reply_text(
            "⏳ Zaten bir üretim çalışıyor. `/iptal` ile durdurabilirsin.")
        return
    _BEKLEYEN.add(sohbet)
    await update.message.reply_text(
        "📜 Promptları TEK BLOK gönder:\n\n"
        "```\nVIDEO PROMPT 1 - şafakta limandan çıkan balıkçı teknesi\nVIDEO PROMPT 2 - dalgalar güverteyi dövüyor\nGÖRSEL PROMPT 1 - yaşlı balıkçının portresi\nGÖRSEL PROMPT 2 - limanda mezat sabahı\n```\n"
        , parse_mode="Markdown")


async def komut_iptal(update: Update, _ctx):
    sohbet = update.effective_chat.id
    _BEKLEYEN.discard(sohbet)
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
    await update.message.reply_text(
        f"📋 *{is_['ad']}* — {is_['durum']}\n"
        f"🎬 video: {len(is_['video_promptlari'])} · "
        f"🖼 görsel: {len(is_['gorsel_promptlari'])} · "
        f"⚠ hata: {len(is_['hatalar'])}\n"
        f"📁 `{is_['dizin']}`", parse_mode="Markdown")


async def metin_geldi(update: Update, ctx):
    if not _izinli(update):
        return
    sohbet = update.effective_chat.id
    if sohbet not in _BEKLEYEN:
        await update.message.reply_text("Üretim için `/basla` yaz.")
        return
    videolar, gorseller = _blok_coz(update.message.text)
    if not (videolar or gorseller):
        await update.message.reply_text("Blok boş görünüyor — tekrar gönder.")
        return
    _BEKLEYEN.discard(sohbet)

    # ⚠ ON KONTROL (20 Agu 2026, ilk gercek deneme): Chrome debug portunda
    # degilken uretim baslatildi; her prompt ayri ayri "baglanilamadi" hatasi
    # uretti. Kapi BURADA: port kapaliysa is HIC baslamaz, tek mesajla soylenir.
    import urllib.request as _ur
    try:
        _ur.urlopen(ayar.CHROME_CDP + "/json/version", timeout=3)
    except Exception:
        _BEKLEYEN.add(sohbet)          # script kaybolmasin: tekrar gonderebilir
        await update.message.reply_text(
            "🔌 *Chrome hazır değil.*\n\n"
            "Bilgisayarında şunu çalıştır:\n"
            "`bash hayalet/chrome_baslat.sh`\n\n"
            "Açılan pencerede Google hesabına girip Flow'u aç:\n"
            "https://labs.google/fx/tools/flow\n\n"
            "Sonra scripti TEKRAR gönder — bekliyorum.",
            parse_mode="Markdown")
        return

    ad = f"is_{time.strftime('%Y%m%d_%H%M%S')}"
    d = ayar.is_dizini(ad)
    is_ = {"ad": ad, "dizin": str(d), "video_promptlari": videolar,
           "gorsel_promptlari": gorseller, "durum": "uretim",
           "sonuclar": {}, "hatalar": []}
    _SON_IS[sohbet] = is_
    _kaydet(is_)
    _CALISAN.add(sohbet)
    _IPTAL.discard(sohbet)
    await update.message.reply_text(
        f"🚀 Başlıyorum — 🎬 {len(videolar)} video + 🖼 {len(gorseller)} görsel.\n"
        f"📁 `{d}`\n(Chrome açık ve Flow'a giriş yapılmış olmalı.)",
        parse_mode="Markdown")

    kuyruk: asyncio.Queue = asyncio.Queue()

    def bildir(m):
        try:
            kuyruk.put_nowait(m)
        except Exception:
            pass

    async def akitici():
        while True:
            m = await kuyruk.get()
            if m is None:
                break
            try:
                await ctx.bot.send_message(sohbet, m[:400])
            except Exception:
                pass

    akit = asyncio.create_task(akitici())

    def iptal_mi():
        return sohbet in _IPTAL

    try:
        # PARTI MODU (kullanici istegi): promptlar 10'ar verilir, ciktilar
        # belirdikce indirilir — tek tek gondermekten cok daha hizli.
        vids = await asyncio.to_thread(
            flow_surucu.parti_uret, videolar, "video", d / "video",
            bildir, iptal_mi)
        gors = await asyncio.to_thread(
            flow_surucu.parti_uret, gorseller, "gorsel", d / "gorsel",
            bildir, iptal_mi)
        is_["sonuclar"] = {"video": vids, "gorsel": gors}
        hatalar = [f"{x['tur']}[{x['sira']}] {x['neden']}"
                   for x in (vids + gors) if not x["ok"]]
        is_["hatalar"] = hatalar
        is_["durum"] = "bitti" if not hatalar else "bitti-eksikli"
        _kaydet(is_)
        ok_v = sum(1 for x in vids if x["ok"])
        ok_g = sum(1 for x in gors if x["ok"])
        ozet = (f"✅ *BİTTİ*\n🎬 {ok_v}/{len(vids)} video · "
                f"🖼 {ok_g}/{len(gors)} görsel\n📁 `{d}`")
        if hatalar:
            ilk = "\n".join(f"• {h}" for h in hatalar[:8])
            ozet += (f"\n\n⚠ *{len(hatalar)} başarısız:*\n{ilk}"
                     + ("\n… tamamı is.json içinde" if len(hatalar) > 8 else ""))
        else:
            ozet += "\n👍 Hata yok."
        await ctx.bot.send_message(sohbet, ozet, parse_mode="Markdown")
    except Exception as e:                                   # noqa: BLE001
        is_["durum"] = "hata"
        is_["hatalar"].append(f"{type(e).__name__}: {e}")
        _kaydet(is_)
        await ctx.bot.send_message(
            sohbet, f"❌ Beklenmeyen hata: {type(e).__name__}: {str(e)[:200]}")
    finally:
        _CALISAN.discard(sohbet)
        _IPTAL.discard(sohbet)
        await kuyruk.put(None)
        await akit


def calistir():
    eksik = ayar.eksik_ayarlar()
    if eksik:
        print("EKSIK AYAR:")
        for e in eksik:
            print(f"  · {e}")
        raise SystemExit(1)
    app = Application.builder().token(ayar.TELEGRAM_TOKEN).build()
    for ad, fn in (("start", komut_start), ("basla", komut_basla),
                   ("durum", komut_durum), ("iptal", komut_iptal)):
        app.add_handler(CommandHandler(ad, fn))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, metin_geldi))
    print(f"👻 Hayalet calisiyor. Klasor koku: {ayar.KOK}")
    app.run_polling()


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
**macOS:** `brew install python@3.11` (brew yoksa önce onu kur)
**Linux:** `sudo apt update && sudo apt install -y python3 python3-pip curl`

### 2) Python paketleri
```bash
python3 -m pip install --user --upgrade "python-telegram-bot>=21" playwright
```

### 3) Chrome kurulu olmalı
macOS: `/Applications/Google Chrome.app` var mı? Linux: `command -v google-chrome`.
Yoksa kullanıcıya https://google.com/chrome indirt.

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

### 5) Chrome'u kontrol portuyla başlat + Flow'a giriş
```bash
bash hayalet/chrome_baslat.sh
```
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

## KULLANIM (2 mesaj)

1. Botuna `/basla` yaz
2. Promptları **tek blok** gönder:

```
VIDEO PROMPT 1 - şafakta limandan çıkan balıkçı teknesi
VIDEO PROMPT 2 - dalgalar güverteyi dövüyor
GÖRSEL PROMPT 1 - yaşlı balıkçının portresi
GÖRSEL PROMPT 2 - limanda mezat sabahı
```

Etiket toleranslıdır (`video 3:`, `Görsel Prompt -` de olur); etiketsiz satır
önceki promptun devamı sayılır. Üretim **10'arlı partiler** halinde tek ajan
mesajıyla gönderilir (canlıda ölçüldü: 3 görsel ~40 sn) — çıktılar belirdikçe
indirilir; her indirmede ✅ ilerleme, hatada ⚠ neden gelir.
Parti boyu: `HAYALET_PARTI` (varsayılan 10). `/durum` künye · `/iptal` durdurur.
Dosyalar: `~/Desktop/Hayalet/is_<tarih>/video|gorsel/`

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
