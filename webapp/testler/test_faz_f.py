#!/usr/bin/env python3
"""FAZ F testleri — arayuz sozlesmesi ve regresyonlari (TARAYICI GEREKTIRMEZ).

Kapsam:
  1. API uclari server.py ile birebir  ·  generate alan haritasi tam
  2. Tekil DOM id'leri  ·  nav/wizard durumlari
  3. Adim 4'te SAHTE SAYI YOK  ·  emoji kalintisi YOK
  4. 390px tasma kurallari (CSS duzeyinde)  ·  erisilebilirlik temelleri
  5. Kullaniciya gorunen metinler DOGRU TURKCE karakterlerle (bagimsiz QA
     maddesi 1) — kod kimlikleri ASCII kalabilir
  6. Kok yolu: `<base href="/">` YOK, varlik/API yollari basinda / OLMADAN
  7. /ui allowlist + traversal reddi (server.py mantigi)
  8. Test artigi (.claude/launch.json) depoya girmemis

Kosum: python3 webapp/testler/test_faz_f.py
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEPO = os.path.dirname(KOK)
STATIC = os.path.join(KOK, "static")
JS_DIZIN = os.path.join(STATIC, "js")
gecen, basarisiz = 0, []


def kontrol(ad, kosul, detay=""):
    global gecen
    if kosul:
        gecen += 1
        print(f"  ok   {ad}")
    else:
        basarisiz.append(f"{ad} — {detay}")
        print(f"  XX   {ad}  {detay}")


def blok(ad):
    print(f"\n── {ad} ──")


def oku(*p):
    with open(os.path.join(STATIC, *p), encoding="utf-8") as f:
        return f.read()


HTML = oku("index.html")
CSS = oku("app.css")
APP = oku("app.js")
JS = {ad: oku("js", ad) for ad in sorted(os.listdir(JS_DIZIN)) if ad.endswith(".js")}
SUNUCU = open(os.path.join(KOK, "server.py"), encoding="utf-8").read()


def yorumsuz(metin, html=False):
    """Yorumlari cikar — yorumda gecen ifade 'kod' ya da 'kullanici metni' degil."""
    m = re.sub(r"/\*[\s\S]*?\*/", "", metin)
    m = re.sub(r"^\s*//.*$", "", m, flags=re.M)
    if html:
        m = re.sub(r"<!--[\s\S]*?-->", "", m)
    return m


TUM_JS = APP + "\n" + "\n".join(JS.values())
TUM_JS_KOD = yorumsuz(TUM_JS)
HTML_KOD = yorumsuz(HTML, html=True)

# ═══════════ 1) DOSYA YAPISI: monolit boluendu mu ═══════════
blok("dosya yapisi: 1698 satirlik monolit boluendu")
kontrol("index.html artik kucuk (<=200 satir)",
        HTML.count("\n") <= 200, f"{HTML.count(chr(10))} satir")
kontrol("app.css ayri dosya", len(CSS) > 4000, f"{len(CSS)} bayt")
kontrol("app.js ayri dosya", len(APP) > 1000, f"{len(APP)} bayt")
for zorunlu in ("ikon.js", "api.js", "durum.js", "bilesenler.js",
                "gorunumler.js", "wizard.js"):
    kontrol(f"modul var: js/{zorunlu}", zorunlu in JS)
kontrol("index.html'de inline <style> YOK", "<style" not in HTML_KOD)
kontrol("index.html'de inline is mantigi YOK",
        "<script" in HTML_KOD and "function" not in HTML_KOD,
        "yalnizca modul etiketi olmali")
kontrol("framework/CDN bagimliligi YOK",
        not re.search(r"https?://(cdn|unpkg|jsdelivr)", HTML + TUM_JS))

# ═══════════ 2) API UCLARI server.py ILE BIREBIR ═══════════
blok("API sozlesmesi")
sunucu_uclari = set(re.findall(r'@app\.(?:get|post|delete)\("([^"]+)"', SUNUCU))
uclar_blok = JS["api.js"][JS["api.js"].find("export const UCLAR"):
                          JS["api.js"].find("export const GENERATE_ALANLARI")]
on_uclar = set(re.findall(r":\s*'((?:api|ciktilar|onizleme|ses-ornek|fonts)[^']*)'",
                          uclar_blok))
kontrol("api.js en az 18 uc tanimliyor", len(on_uclar) >= 18, str(len(on_uclar)))
eksik = []
for u in sorted(on_uclar):
    tam = "/" + u
    if tam in sunucu_uclari:
        continue
    # Parametreli uclar: 'api/job/' -> '/api/job/{is_id}'
    if any(s.startswith(tam) and "{" in s for s in sunucu_uclari):
        continue
    eksik.append(u)
kontrol("arayuzun cagirdigi HER uc server.py'de var", not eksik,
        f"server.py'de YOK: {eksik}")

# generate alan haritasi <-> server.py imzasi
imza = SUNUCU[SUNUCU.find("async def uret_baslat"):]
imza = imza[:imza.find("):") + 2]
sunucu_alanlari = set(re.findall(r"(\w+):\s*(?:str|List\[UploadFile\]|UploadFile)", imza))
on_alanlar = set(re.findall(r"\{ad: '(\w+)'", JS["api.js"]))
# ⚠ Gercek sayi 21 (server.py `uret_baslat` imzasindan sayildi). Testi
# yazarken 22 demistim — kumeler birebir esitken sayiyi yanlis saymisim.
# 12 Agu 2026: main `unlu` (unlu modu) alanini ekledi -> 21 DEGIL 22.
kontrol("generate alan sayisi 22", len(on_alanlar) == 22, str(len(on_alanlar)))
kontrol("generate alanlari server.py imzasiyla AYNI",
        on_alanlar == sunucu_alanlari,
        f"fazla={sorted(on_alanlar - sunucu_alanlari)} "
        f"eksik={sorted(sunucu_alanlari - on_alanlar)}")
for zorunlu in ("session", "story", "tur", "sure_dk", "gecis", "zoom",
                "altyazi", "sahne_ref", "karakter", "stil", "sora", "acilis",
                "palet", "palet_ozel", "arkaplan", "ses", "isik",
                "gorsel_model", "altyazi_sablon", "profil", "edit"):
    kontrol(f"alan korundu: {zorunlu}", zorunlu in on_alanlar)
kontrol("bilinmeyen alan gonderimi HATA firlatir",
        "bilinmeyen alan" in JS["api.js"])

# Wizard'in urettigi degerler harita disina cikmiyor mu
wz_anahtarlar = set(re.findall(r"^\s*(?:d\.)?(\w+)\s*[:=]", "", re.M)) or set()
wz_atamalar = set(re.findall(r"d\.(\w+)\s*=", JS["wizard.js"]))
wz_sozluk = set(re.findall(r"^\s{4}(\w+):", JS["wizard.js"][
    JS["wizard.js"].find("const d = {"):
    JS["wizard.js"].find("const stil = t.tur")], re.M))
kontrol("wizard yalnizca sozlesmedeki alanlari kullaniyor",
        (wz_atamalar | wz_sozluk) <= on_alanlar,
        f"sozlesme disi: {sorted((wz_atamalar | wz_sozluk) - on_alanlar)}")

# ═══════════ 3) BILGI MIMARISI + WIZARD DURUMLARI ═══════════
blok("bilgi mimarisi ve wizard")
ekranlar = re.findall(r"\{id: '(\w+)', ad: '([^']+)'", APP)
kontrol("5 ana ekran", len(ekranlar) == 5, str(ekranlar))
kontrol("ekran id'leri beklenen",
        [e[0] for e in ekranlar] == ["ana", "yeni", "projeler", "sablonlar",
                                     "ayarlar"], str(ekranlar))
kontrol("Animasyon/Hikaye/Belgesel AYRI EKRAN DEGIL",
        not any(e[0] in ("animasyon", "hikaye", "documentary") for e in ekranlar))
# ⚠ TEK AKIS PIVOTU (20 Agu 2026, kullanici karari): eski 5 adimli wizard
# KALDIRILDI — "tek yeni akis, eskiler kalksin". Tur/stil/palet secimleri
# arayuzden cikti; uretim SABIT (tur=documentary, edit=akis) gider.
# Asagidaki kontroller eski urun kararlarini degil YENI akisi kilitler.
kontrol("tek akis: tur/edit SABIT (secim ekrani YOK)",
        "tur: 'documentary'" in JS["wizard.js"]
        and "edit: 'akis'" in JS["wizard.js"])
kontrol("alt nav 4 oge (altnav: true)", APP.count("altnav: true") == 4,
        str(APP.count("altnav: true")))
kontrol("wizard TEK ekran (adim listesi YOK)",
        "ADIMLAR" not in JS["wizard.js"])
kontrol("en az 20 karakter zorunlu", "20 karakter" in JS["wizard.js"])
kontrol("tur secim kartlari KALKTI",
        "grup: 'tur'" not in JS["wizard.js"])
kontrol("taslak localStorage'da", "bedosaho_taslak_v1" in JS["durum.js"])
kontrol("taslak dosyalari SAKLAMIYOR (durustce)",
        "Dosyalar (File nesneleri) saklanamaz" in JS["durum.js"])

# ⚠ TEK AKIS PIVOTU (20 Agu 2026): "eski ozellik kaybi yasak" kurali
# BILEREK KALDIRILDI — kullanici karari "tek yeni akis, eskiler kalksin".
# Sora/palet/isik/altyazi-sablonu/karakter-stil gorseli secimleri artik
# URUNUN PARCASI DEGIL; wizard onlari TASIMAZ (asagida negatif kilit).
blok("tek akis: eski secimler wizard'da YOK")
for ad, iz in [("Sora", "wzSora"), ("palet", 'grup="palet"'),
               ("isik", "wzIsik"), ("karakter gorseli", "wzKarGirdi"),
               ("referans kare", "wzRefGirdi"), ("gorsel model", "wzModel")]:
    kontrol(f"wizard'dan kalkti: {ad}", iz not in JS["wizard.js"])
kontrol("teknik ayarlar ayri profesyonel bolumlerde",
        JS["secim-deneyimi.js"].count("PRO_BOLUMLER") >= 2
        and 'data-pro-ac=' in JS["secim-deneyimi.js"],
        "4 bolumlu akordeon bekleniyor")

# ═══════════ 4) ADIM 4: SAHTE SAYI YOK ═══════════
blok("adim 4: uydurma sayi yasagi")
# ⚠ TEK AKIS PIVOTU (20 Agu 2026, kullanici karari): eski 5 adimli wizard
# KALDIRILDI — "tek yeni akis, eskiler kalksin". Tur/stil/palet secimleri
# arayuzden cikti; uretim SABIT (tur=documentary, edit=akis) gider.
# Asagidaki kontroller eski urun kararlarini degil YENI akisi kilitler.
kontrol("uydurma tahmin YOK (uretim sirasinda hesaplanir yazisi)",
        "tahmin gösterilmez" in JS["wizard.js"])
kontrol("sabit dolar tutari YOK",
        not re.search(r"\$\s?\d", TUM_JS_KOD), "maliyet uydurulmamali")
kontrol("sabit 'kaynak: N' sayisi YOK",
        not re.search(r"(kaynak|medya|iddia)['\"]?\s*[:,]\s*\d+", TUM_JS_KOD, re.I))
kontrol("ozet satirinda hesaplanacak sinifi var", ".hesaplanacak" in CSS)

# ═══════════ 5) EMOJI YOK, TEK IKON SISTEMI ═══════════
blok("ikon sistemi")
# ⚠ Ilk surumde aralik `☀-➿` ve `←-⇿` idi; bu `→` (U+2192) ve `⚠` (U+26A0)
# gibi TIPOGRAFIK isaretleri de emoji sayiyordu. "Pexels → Pixabay" gecerli
# tipografidir; HTML yorumundaki ⚠ de kullaniciya gorunmez. Lint yalnizca
# PIKTOGRAFIK emoji araligina bakiyor, tipografik isaretler allowlist'te.
TIPOGRAFIK_IZIN = "→←↑↓·—–…⚠✓×"
EMOJI = re.compile("[\U0001F300-\U0001FAFF\U0001F000-\U0001F2FF"
                   "\u2700-\u27bf\u2600-\u26ff]")
for ad, metin, html in [("index.html", HTML, True), ("app.css", CSS, False),
                        ("app.js", APP, False)] + \
                       [(f"js/{a}", m, False) for a, m in JS.items()]:
    temiz = yorumsuz(metin, html=html)
    for t in TIPOGRAFIK_IZIN:
        temiz = temiz.replace(t, '')
    kalan = EMOJI.findall(temiz)
    kontrol(f"emoji kalintisi yok: {ad}", not kalan, str(set(kalan)))
kontrol("tek ikon fonksiyonu", "export function ikon(" in JS["ikon.js"])
kontrol("ikonlar inline SVG", "viewBox=\"0 0 24 24\"" in JS["ikon.js"])
kontrol("ikonlar aria-hidden", 'aria-hidden="true"' in JS["ikon.js"])
kontrol("tanimsiz ikon SESSIZ dusmez", "tanimsiz ikon" in JS["ikon.js"])
ikon_adlari = set(re.findall(r"^  ([a-z][a-zA-Z0-9]*): `", JS["ikon.js"], re.M))
kullanilan = set(re.findall(r"ikon\('([a-z][a-zA-Z0-9]*)'", TUM_JS)) | \
    set(re.findall(r"data-ikon=\"([a-z][a-zA-Z0-9]*)\"", HTML)) | \
    set(re.findall(r"ikon: '([a-z][a-zA-Z0-9]*)'", APP))
kontrol("kullanilan her ikon tanimli", kullanilan <= ikon_adlari,
        f"tanimsiz: {sorted(kullanilan - ikon_adlari)}")

# ═══════════ 6) 390px TASMA KURALLARI ═══════════
blok("mobil 390px kurallari")
kontrol("kok overflow-x kilidi", "overflow-x: hidden" in CSS)
kontrol("mobil kirilma noktasi <=720px", "@media (max-width: 720px)" in CSS)
kontrol("390 altinda ek kural", "@media (max-width: 400px)" in CSS)
kontrol("izgaralar mobilde tek kolon",
        "grid-template-columns: minmax(0, 1fr)" in CSS)
kontrol("dokunma hedefi 44px degiskeni", "--dokunma: 44px" in CSS)
kontrol("dugme min-height dokunma hedefi",
        "min-height: var(--dokunma)" in CSS)
kontrol("alt nav yuksekligi >=44px",
        "--altnav-y: 62px" in CSS)
kontrol("sticky Devam mobilde", "position: sticky" in CSS and ".wz-alt {" in CSS)
kontrol("min-width:0 tasma korumasi", CSS.count("min-width: 0") >= 5,
        str(CSS.count("min-width: 0")))
kontrol("atla-baglantisi YATAY tasma yapmiyor",
        "left: -999px" not in CSS and "top: -120px" in CSS,
        "left:-999px belge genisligini buyutuyordu")
kontrol("guvenli alan (safe-area) dikkate alinmis",
        "env(safe-area-inset-bottom)" in CSS)

# ═══════════ 7) ERISILEBILIRLIK ═══════════
blok("erisilebilirlik")
kontrol("dil tr", 'lang="tr"' in HTML)
kontrol("icerige atla baglantisi", 'class="atla"' in HTML)
kontrol("ana icerik odaklanabilir", 'id="anaicerik"' in HTML and "tabindex=\"-1\"" in HTML)
kontrol("focus-visible halkasi", ":focus-visible" in CSS)
kontrol("reduced-motion destegi", "prefers-reduced-motion" in CSS)
kontrol("aria-live bolgesi", 'aria-live="polite"' in HTML)
# ⚠ Ilk surumde `<nav` sayisi == `aria-label` sayisi karsilastiriliyordu;
# marka baglantisinin da aria-label'i oldugu icin sayilar tutmuyordu. Dogru
# kural: HER <nav> kendi aria-label'ini tasiyor mu.
_navlar = re.findall(r"<nav[^>]*>", HTML)
kontrol("her <nav> aria-label tasiyor",
        _navlar and all('aria-label=' in n for n in _navlar),
        str([n for n in _navlar if 'aria-label=' not in n]))
kontrol("aktif ekran aria-current", "aria-current" in APP)
# ⚠ TEK AKIS PIVOTU (20 Agu 2026, kullanici karari): eski 5 adimli wizard
# KALDIRILDI — "tek yeni akis, eskiler kalksin". Tur/stil/palet secimleri
# arayuzden cikti; uretim SABIT (tur=documentary, edit=akis) gider.
# Asagidaki kontroller eski urun kararlarini degil YENI akisi kilitler.
# Tek ekranda adim dugmesi YOK; form alanlarinin erisilebilir adi var.
kontrol("form alanlari label tasiyor (tek akis)",
        'for="akMetin"' in JS["wizard.js"] and 'for="akSure"' in JS["wizard.js"]
        and 'for="akSes"' in JS["wizard.js"])
kontrol("uretim durumu aria-live", 'aria-live="polite"' in JS["wizard.js"])
kontrol("her cizimde duyuru temizlenir",
        "duyur('');" in JS["wizard.js"])
# QA maddesi 4: her form ogesinin adi
kontrol("secimAlani label uretiyor",
        '<label class="alan-ad" for=' in JS["bilesenler.js"])
_tum_on = "\n".join(JS.values()) + APP
kontrol("renk girdilerine gizli label",
        'class="gorunmez" for="wzAltRenk"' in _tum_on
        and 'class="gorunmez" for="wzHex' in _tum_on)
# ⚠ TEK AKIS: dosya (karakter/stil/referans) girdileri ARAYUZDEN KALKTI.
kontrol("dosya girdileri kalkti (tek akis)",
        'wzRefGirdi' not in JS["wizard.js"] and 'wzKarGirdi' not in JS["wizard.js"])
kontrol("anahtar gercek checkbox (klavye)",
        'type="checkbox"' in JS["bilesenler.js"])
# ⚠ Faz G: ozel div+aria yerine NATIVE <progress> kullaniliyor; rol ve
# deger anlamini tarayici sagliyor (inline stil de gerekmiyor).
kontrol("ilerleme gostergesi native <progress>",
        '<progress class="ilerleme"' in JS["bilesenler.js"]
        and 'max="100"' in JS["bilesenler.js"])
kontrol("kontrast notu: sessiz metin >=4.5:1", "4.9:1" in CSS)

# ═══════════ 8) KULLANICI METINLERI DOGRU TURKCE ═══════════
blok("Turkce karakter denetimi (QA maddesi 1)")
# Kullaniciya gorunen metinlerde bulunmamasi gereken ASCII yazimlar.
YASAK_ASCII = [
    "Turu", "Gorsel", "Sablon", "Taslagi", "Icerige", "Ozet", "Adim ",
    "Uretim", "Uretimde", "Tamamlandi", "Anlatici", "Altyazi ", "Isik duzeyi",
    "Sahne gecisleri", "Gomulu", "BUYUK HARF", "Golge", "Ozel renkler",
    "Acilis sahnesi", "Hedef sure", "Secilmedi", "Guvenilir", "Kullanilabilir",
    "Dogrulanmis", "Render suresi", "Henuz is yok", "alinamadi",
    "ulasilamiyor", "Varsayilan", "Yukleniyor", "Aciklama yok",
    # ── Tarayici testinde gozle yakalanan bosluk (Ayarlar ekrani) ──
    "gorsel", "gorseli", "yedegi", "lisansli", "dogrulanir", "dogrulanan",
    "Arsiv", "Acik", "kosullu", "calismiyor", "ogeye", "uretilemiyor",
    "Ucretsiz", "degildir", "toplayici", "ayrintisinda", "Yukseltme",
    "yukseltme", "Insan", "kayitlar", "kimligi",
]
# Yalnizca kullaniciya gorunen bolgeler: HTML metni + JS dize icerikleri
def js_dizeleri(kaynak_metin):
    """JS kaynagindan DIZE ICERIKLERINI ayikla — gercek tarayici, regex degil.

    ⚠ NEDEN REGEX YETMEDI: `'([^']{4,})'` ve `` `([^`]{4,})` `` kaliplari
    backtick'leri SIRAYLA eslestiriyor. `${...}` icinde ic ice sablon dizesi
    olunca eslesme kayiyor ve IKI dize ARASINDAKI KOD "kullanici metni" olarak
    yakalaniyordu (olculdu: `d.gorsel_model = t.gorselModel;` lint'i dusurdu).
    Bu yuzden karakter karakter yuruyen, `${}` derinligini sayan kucuk bir
    tarayici kullaniyoruz.
    """
    m = yorumsuz(kaynak_metin)
    cikti, i, n = [], 0, len(m)
    while i < n:
        c = m[i]
        if c in ("'", '"'):
            j, parca = i + 1, []
            while j < n and m[j] != c:
                if m[j] == "\\":
                    j += 2
                    continue
                if m[j] == "\n":
                    break
                parca.append(m[j])
                j += 1
            cikti.append("".join(parca))
            i = j + 1
            continue
        if c == "`":
            j, parca, derinlik = i + 1, [], 0
            while j < n:
                if m[j] == "\\":
                    j += 2
                    continue
                if derinlik == 0 and m[j] == "`":
                    break
                if m[j] == "$" and j + 1 < n and m[j + 1] == "{":
                    derinlik += 1
                    j += 2
                    continue
                if derinlik > 0:
                    if m[j] == "{":
                        derinlik += 1
                    elif m[j] == "}":
                        derinlik -= 1
                    j += 1
                    continue
                parca.append(m[j])
                j += 1
            cikti.append("".join(parca))
            i = j + 1
            continue
        i += 1
    return [x for x in cikti if len(x) >= 4]


gorunen = [HTML_KOD]
for m in JS.values():
    gorunen += js_dizeleri(m)
gorunen += js_dizeleri(APP)
# ⚠ Ilk surum kod kimliklerini kullanici metni sanip yanlis alarm veriyordu:
# `altyaziSablonlari` icinde "Sablon", `uretimBaslat` icinde "Uretim",
# `wzAltGolge` icinde "Golge". Iki daraltma:
#   a) yalnizca BOSLUK iceren dizeler (gercek cumleler) taranir — 'api/...'
#      ve camelCase kimlikler dusuyor
#   b) yasak yazim TAM KELIME olarak aranir (kelime siniri)
CUMLELER = [g for g in gorunen if " " in g]
birlesik = "\n".join(CUMLELER)
for y in YASAK_ASCII:
    kalip = r"(?<![0-9A-Za-z_\-çğıöşüÇĞİÖŞÜ])" + re.escape(y.strip()) + \
            r"(?![0-9A-Za-z_\-çğıöşüÇĞİÖŞÜ])"
    bulgu = re.search(kalip, birlesik)
    kontrol(f"ASCII yazim kalmadi: '{y.strip()}'", bulgu is None,
            (birlesik[max(0, bulgu.start() - 40):bulgu.end() + 30]
             if bulgu else ""))
kontrol("dogru Turkce karakter GERCEKTEN kullanilmis",
        sum(birlesik.count(c) for c in "çğıöşüÇĞİÖŞÜ") >= 120,
        str(sum(birlesik.count(c) for c in "çğıöşüÇĞİÖŞÜ")))

# ═══════════ 9) KOK YOLU / STATIK SERVIS ═══════════
blok("kok yolu ve /ui allowlist (QA maddesi 6)")
kontrol("<base> etiketi YOK", "<base" not in HTML_KOD,
        "sabit base alt dizini bozuyor")
kontrol("CSS yolu goreli (basinda / yok)", 'href="ui/app.css"' in HTML)
kontrol("JS yolu goreli (basinda / yok)", 'src="ui/app.js"' in HTML)
kontrol("API yollari basinda / OLMADAN",
        not re.search(r":\s*'/(api|ciktilar|onizleme)", JS["api.js"]))
kontrol("API cozumu document.baseURI uzerinden",
        "new URL(parca, document.baseURI)" in JS["api.js"])
kontrol("modul importlari goreli", "'./js/ikon.js'" in APP)

kontrol("/ui rotasi eklendi", '@app.get("/ui/{dosya:path}")' in SUNUCU)
kontrol("allowlist: yalnizca app.css/app.js",
        'UI_TAM_IZIN = frozenset({"app.css", "app.js"})' in SUNUCU)
kontrol("allowlist: yalnizca js/ dizini", 'UI_DIZIN_IZIN = frozenset({"js"})' in SUNUCU)
kontrol("traversal reddi (..)", 'p == ".."' in SUNUCU)
kontrol("gizli dosya reddi", 'p.startswith(".")' in SUNUCU)
kontrol("realpath + STATIC oneki dogrulamasi",
        "os.path.realpath(STATIC)" in SUNUCU
        and 'yol.startswith(kok + os.sep)' in SUNUCU)
kontrol("dogru MIME", 'text/css; charset=utf-8' in SUNUCU
        and 'text/javascript; charset=utf-8' in SUNUCU)
# ⚠ Surumlenmemis varlik + uzun max-age = deploy sonrasi bayat arayuz.
# Tarayici testinde gercekten yasandi; `no-cache` + ETag dogrulamasi sart.
kontrol("varlik onbellegi revalidate ediyor", '"Cache-Control": "no-cache"' in SUNUCU)
_ui_blok = SUNUCU[SUNUCU.find('@app.get("/ui/{dosya:path}")'):]
_ui_blok = _ui_blok[:_ui_blok.find('@app.get("/api/paletler")')]
# ⚠ `yorumsuz()` JS yorumlarini cikariyor; server.py PYTHON dosyasi ve
# aciklamada "max-age=3600" gectigi icin test kendini dusuruyordu.
_ui_kod = re.sub(r"^\s*#.*$", "", _ui_blok, flags=re.M)
kontrol("/ui rotasinda uzun max-age YOK (bayat arayuz riski)",
        "max-age" not in _ui_kod, _ui_kod.strip()[-140:])
# ⚠ FAZ R-1d-a: imzaya `istek: Request` EKLENDI — zorunlu oturum kapisi
# istegin cerezini okumak zorunda. Bu BILEREK yapilan tek eklemedir; 22
# Form/File alaninin HICBIRI degismedi (test_faz_h o sozlesmeyi ayrica
# kilitliyor). Eski tek-satirlik desen bu yuzden guncellendi, GEVSETILMEDI:
# alan adlari ve sirasi hala birebir dogrulaniyor.
kontrol("API/generate imzasi: yalniz `istek: Request` eklendi, Form alanlari "
        "AYNI",
        "async def uret_baslat(istek: Request,\n"
        "                      session: str = Form(...), story: str = Form(...)"
        in SUNUCU)
kontrol("API/generate 22 Form/File alani KORUNDU",
        len(re.findall(r"(\w+): [^=\n]+= (?:Form|File)\(",
                       SUNUCU[SUNUCU.find("async def uret_baslat("):
                              SUNUCU.find("async def uret_baslat(") + 1600]))
        == 22,
        len(re.findall(r"(\w+): [^=\n]+= (?:Form|File)\(",
                       SUNUCU[SUNUCU.find("async def uret_baslat("):
                              SUNUCU.find("async def uret_baslat(") + 1600])))
kontrol("pipeline cagrisi degismedi", "import pipeline" in SUNUCU)


def _ui_coz(dosya: str):
    """server.py ui_varlik mantiginin AYNISI — kabul/red kararini test eder."""
    parcalar = [p for p in str(dosya).split("/") if p not in ("", ".")]
    if not parcalar or any(p == ".." or p.startswith(".") for p in parcalar):
        return None
    if len(parcalar) == 1:
        if parcalar[0] not in ("app.css", "app.js"):
            return None
    elif len(parcalar) == 2:
        if parcalar[0] != "js" or not parcalar[1].endswith(".js"):
            return None
    else:
        return None
    if os.path.splitext(parcalar[-1])[1].lower() not in (".css", ".js"):
        return None
    kok = os.path.realpath(STATIC)
    yol = os.path.realpath(os.path.join(STATIC, *parcalar))
    if not (yol == kok or yol.startswith(kok + os.sep)):
        return None
    return yol if os.path.isfile(yol) else None


for kabul in ("app.css", "app.js", "js/wizard.js", "js/api.js", "js/ikon.js"):
    kontrol(f"/ui KABUL: {kabul}", _ui_coz(kabul) is not None)
for red in ("../server.py", "js/../../server.py", "index.html",
            "onizleme/x.png", "js/a/b.js", ".env", "js/gizli/.env",
            "app.css/../../server.py", "", "js", "js/x.py"):
    kontrol(f"/ui RED: {red or '(bos)'}", _ui_coz(red) is None)

# ═══════════ 10) YANLIS METINLER DUZELTILDI ═══════════
blok("yanlis bilgi duzeltmeleri (UX_DENETIM.md §8)")
kontrol("Magnific CALISMIYOR olarak yazili",
        "ÇALIŞMIYOR" in JS["gorunumler.js"])
# ⚠ TEK AKIS: AI gorsel yolu ACIK (stok bulunamazsa) — eski "belgeselde
# gorsel uretilmez" metni bu akista YANLIS olurdu; wizard onu TASIMAZ.
kontrol("tek akis AI gorseli DURUSTCE anlatiyor",
        "AI görsel" in JS["wizard.js"])
kontrol("YouTube yalnizca CC",
        "YALNIZCA Creative Commons" in JS["gorunumler.js"])
# ⚠ Ilk surum yorumlari da tariyordu; "Telifli indirme SUNULMUYOR" aciklamasi
# yasak metin sanildi. Kullaniciya gorunen kisma bakiliyor.
kontrol("telifli indirme secenek olarak SUNULMUYOR",
        "telifli" not in yorumsuz(JS["gorunumler.js"]).lower())
kontrol("kaynak zinciri gercek sira",
        "Pexels → Pixabay → Coverr → YouTube" in JS["gorunumler.js"])
kontrol("sunucu/ip/yenileme tarihi kullanici yuzunde YOK",
        not re.search(r"185\.23\.17\.240|Hostinger|Hetzner|2026-08-16", TUM_JS_KOD))
kontrol("sabit fiyat listesi YOK",
        "sabit bir fiyat listesi göstermiyoruz" in JS["gorunumler.js"])
kontrol("localStorage'in YEDEK oldugu yaziyor",
        "bu tarayıcıda" in JS["gorunumler.js"])

# ═══════════ 11) TEKIL ID'LER ═══════════
blok("tekil DOM id'leri")
html_idler = re.findall(r'\sid="([^"]+)"', HTML)
kontrol("index.html id'leri tekil",
        len(html_idler) == len(set(html_idler)),
        str([i for i in html_idler if html_idler.count(i) > 1]))
js_idler = re.findall(r'id="(wz[A-Za-z0-9]+|[a-z][A-Za-z0-9]*(?:Isler|Saglik|Liste|Profiller))"',
                      TUM_JS)
tekrar = sorted({i for i in js_idler if js_idler.count(i) > 1})
kontrol("uretilen id'ler tekrar etmiyor", not tekrar, str(tekrar))
kontrol("id'ler ASCII (kod kimligi)",
        all(i.isascii() for i in html_idler + js_idler))

# ═══════════ 12) TEST ARTIGI DEPODA YOK ═══════════
blok("test artigi (QA maddesi 5)")
izlenen = subprocess.run(["git", "ls-files", ".claude"], cwd=DEPO,
                         capture_output=True, text=True).stdout.strip()
kontrol(".claude/ depoda izlenmiyor", not izlenen, izlenen[:120])
kontrol("launch.json diskte de yok",
        not os.path.exists(os.path.join(DEPO, ".claude", "launch.json")))
gi = open(os.path.join(DEPO, ".gitignore"), encoding="utf-8").read()
kontrol(".gitignore .claude/ iceriyor", ".claude/" in gi)

# ═══════════ 13) SOZDIZIMI ═══════════
blok("sozdizimi (node --check)")
if subprocess.run(["node", "-v"], capture_output=True).returncode == 0:
    import tempfile
    for ad, metin in [("app.js", APP)] + [(f"js/{a}", m) for a, m in JS.items()]:
        with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False,
                                         encoding="utf-8") as f:
            f.write(metin)
            gecici = f.name
        r = subprocess.run(["node", "--check", gecici], capture_output=True,
                           text=True)
        os.unlink(gecici)
        kontrol(f"sozdizimi temiz: {ad}", r.returncode == 0,
                (r.stderr or "").strip().splitlines()[:1])
else:
    print("  --   node yok; sozdizimi kontrolu ATLANDI (durustce belirtiliyor)")

print(f"\n{'=' * 60}")
print(f"GECEN: {gecen}   BASARISIZ: {len(basarisiz)}")
for b in basarisiz:
    print(f"  XX {b}")
sys.exit(1 if basarisiz else 0)
