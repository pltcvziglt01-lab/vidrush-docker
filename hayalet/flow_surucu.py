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
    """Sayfadaki BUYUK medya src'leri (genislik > 200px)."""
    etiket = "video" if tur == "video" else "img"
    return set(sayfa.evaluate(
        """(et) => [...document.querySelectorAll(et)].filter(e => {
             const r = e.getBoundingClientRect();
             return r.width > 200 && (e.currentSrc || e.src || '').length > 30;
           }).map(e => e.currentSrc || e.src)""", etiket))


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
