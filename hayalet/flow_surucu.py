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
