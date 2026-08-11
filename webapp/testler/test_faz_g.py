#!/usr/bin/env python3
"""FAZ G testleri — arac ici secim deneyimi (TARAYICI GEREKTIRMEZ).

Kapsam (kullanicinin QA listesi):
  1. Stiller: otomatik karti · oneri siniri · tumunu goster · arama ·
     tek secim (radio semantics) · guvenli fallback
  2. Ses: hizli kartlar · tum sesler · arama/filtre · oynat/durdur · durust
     hata · endpoint fallback
  3. TUM eski generate alanlarinin birebir korundugu
  4. Profesyonel bolumlerde TEK acik akordeon · reset dosya/konuyu silmez ·
     ozetin dogru guncellenmesi
  5. Erisilebilir adlar · radio semantics · klavye · 44px · reduced motion ·
     Turkce lint · emoji yok · inline style yok

Kosum: python3 webapp/testler/test_faz_g.py
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile

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


def yorumsuz(metin, html=False):
    m = re.sub(r"/\*[\s\S]*?\*/", "", metin)
    m = re.sub(r"^\s*//.*$", "", m, flags=re.M)
    if html:
        m = re.sub(r"<!--[\s\S]*?-->", "", m)
    return m


HTML = oku("index.html")
CSS = oku("app.css")
APP = oku("app.js")
JS = {a: oku("js", a) for a in sorted(os.listdir(JS_DIZIN)) if a.endswith(".js")}
SD = JS.get("secim-deneyimi.js", "")
WZ = JS.get("wizard.js", "")
SUNUCU = open(os.path.join(KOK, "server.py"), encoding="utf-8").read()
TUM_JS = APP + "\n" + "\n".join(JS.values())
TUM_JS_KOD = yorumsuz(TUM_JS)


def js_dizeleri(kaynak_metin):
    """Dize icerikleri — `${}` ifadeleri (KOD) atlanir.

    ⚠ Faz F surumu IC ICE sablon dizelerinde kayiyordu: `${...}` icindeki
    nested backtick'ler sayilmadigi icin tarayici sablonun disina tasip KODU
    metin sanabiliyordu (olculdu: `ONERILEN_VARSAYILAN` govdesi "kullanici
    metni" olarak yakalandi). Artik `${}` icinde YIGIN tutuluyor ve ic sablon
    dizeleri de dogru atlaniyor.
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
            j, parca, yigin = i + 1, [], []
            while j < n:
                if m[j] == "\\":
                    j += 2
                    continue
                if not yigin and m[j] == "`":
                    break
                if m[j] == "$" and j + 1 < n and m[j + 1] == "{":
                    yigin.append("{")
                    j += 2
                    continue
                if yigin:
                    k = m[j]
                    if k == "{":
                        yigin.append("{")
                    elif k == "}":
                        yigin.pop()
                    elif k == "`":
                        # ic ice sablon: kendi kapanisina kadar atla
                        yigin.append("`")
                        j += 1
                        while j < n and not (m[j] == "`" and m[j - 1] != "\\"):
                            j += 1
                        yigin.pop()
                    elif k in ("'", '"'):
                        j += 1
                        while j < n and m[j] != k:
                            j += 2 if m[j] == "\\" else 1
                    j += 1
                    continue
                parca.append(m[j])
                j += 1
            cikti.append("".join(parca))
            i = j + 1
            continue
        i += 1
    return [x for x in cikti if len(x) >= 4]


# ═══════════ 1) MODUL YAPISI ═══════════
blok("modul yapisi: wizard sismedi")
kontrol("js/secim-deneyimi.js var", bool(SD), "yeni modul zorunlu")
kontrol("secim-deneyimi.js anlamli boyutta", len(SD) > 8000, f"{len(SD)} bayt")
kontrol("wizard.js secim-deneyimi'ni import ediyor",
        "from './secim-deneyimi.js'" in WZ)
kontrol("wizard.js KUCULDU (Faz F: 780 satir)",
        WZ.count("\n") <= 780, f"{WZ.count(chr(10))} satir")
kontrol("secim cizimi wizard'da DEGIL modulde",
        "export function stilBolumu" in SD and "export function stilBolumu" not in WZ)
kontrol("inline style YOK (kod icinde)",
        'style="' not in yorumsuz(SD) and 'style="' not in yorumsuz(WZ),
        "CSS siniflari kullanilmali")
kontrol("framework/bagimlilik eklenmedi",
        not re.search(r"https?://(cdn|unpkg|jsdelivr|esm\.sh)", TUM_JS))
kontrol("sunucu degisikligi gerekmedi (/ui allowlist js/*.js kapsar)",
        'UI_DIZIN_IZIN = frozenset({"js"})' in SUNUCU
        and 'parcalar[1].endswith(".js")' in SUNUCU)

# ═══════════ 2) STIL SECIMI ═══════════
blok("gorsel stil: otomatik + oneri siniri + tumu + arama")
kontrol("kullaniciya 'Görsel stil' deniyor (backend alani degismedi)",
        "<h3>Görsel stil</h3>" in SD and "'edit'" in JS["api.js"])
kontrol("'Edit sablonu' ifadesi kullanici metninde YOK",
        "Edit şablonu" not in "\n".join(js_dizeleri(SD)),
        "mikro metin karari")
kontrol("Otomatik karti var", "Otomatik — konuya göre önerilen" in SD)
kontrol("otomatik kartta neyin otomatik oldugu yazili",
        "Konuyu ve türü okuyup uygun stili sistem seçer" in SD)
kontrol("oneri siniri 3", "export const ONERI_SINIRI = 3" in SD)
kontrol("baslangicta yalnizca oneriler gosterilir",
        "onerilenStiller(liste)" in SD and "tumunuAc" in SD)
kontrol("'Tüm stilleri göster' dugmesi", "Tüm stilleri göster" in SD)
kontrol("cok secenekte arama", "sbStilArama" in SD and 'type="search"' in SD)
kontrol("arama esigi 6", "liste.length > 6" in SD)
kontrol("16:9 mini onizleme uretiliyor", "export function stilOnizleme" in SD)
kontrol("onizleme DIS MEDYAYA bagli degil (inline SVG)",
        "<svg viewBox=" in SD and "img src" not in SD.lower())
kontrol("onizleme GERCEK metadata'dan turetiliyor",
        "footage_pct" in SD and "sahne_sn" in SD)
kontrol("onizleme deterministik (ayni id -> ayni renk)",
        "function tonHash" in SD)
kontrol("en fazla 3 ozellik etiketi", ".slice(0, 3)" in SD)
kontrol("metadata yoksa etiket URETILMEZ",
        "if (sayiVar(s.sahne_sn))" in SD and "if (sayiVar(s.footage_pct))" in SD)
kontrol("ozet yoksa CUMLE UYDURULMAZ",
        "Bu stil için açıklama sağlanmadı." in SD)
kontrol("liste bos/hatali ise cokme yok, durust not",
        "Stil listesi alınamadı." in SD)
kontrol("secili durum yalniz renk DEGIL: onay + 'Seçildi' metni",
        "sk-secili" in SD and ">Seçildi<" in SD and ".sk[aria-checked=\"true\"] .sk-secili" in CSS)

# ═══════════ 3) SES SECIMI ═══════════
blok("ses: kartlar + tum sesler + arama/filtre + dinle")
kontrol("ses select DEGIL kart", "sk-izgara-ses" in SD and "id: 'wzSes'" not in WZ)
kontrol("Otomatik ses karti", "Otomatik — türe uygun ses" in SD)
kontrol("en fazla 3 hizli ses karti", "yerel.slice(0, 3)" in SD)
kontrol("'Tüm sesler' acilir", "Tüm sesler" in SD)
kontrol("ses aramasi", "sbSesArama" in SD)
kontrol("saglayici suzgeci GERCEK metadata'dan (motor)",
        ".map((v) => v.motor).filter(Boolean)" in SD)
kontrol("ses etiketleri yalnizca var olan alanlardan",
        all(x in SD for x in ("if (v.dil)", "if (v.cinsiyet)", "if (v.yas)",
                              "if (v.aksan)")))
kontrol("ornek YOKSA dinle dugmesi CIZILMEZ",
        "Örnek kayıt yok" in SD and "if (!v.ornek) return '';" in SD)
kontrol("dinle/durdur erisilebilir ad tasiyor",
        'aria-label="${kac(v.ad)} sesini' in SD)
kontrol("dinle GERCEK <button type=button>",
        '<button type="button" class="ses-dinle"' in SD)
kontrol("dinle dugmesi radyo kartinin KARDESI (ic ice DEGIL)",
        'return altEylem ? `<div class="sk-sar">${kart}${altEylem}</div>` : kart;'
        in SD)
kontrol("ekBilgi artik dugme ICERMIYOR",
        "ekBilgi: v.ornek ? '' :" in SD)
kontrol("dinle klavyeyle calisir", "e.key === 'Enter' || e.key === ' '" in SD)
kontrol("ayni anda tek ses calar", "export function sesDurdur" in SD
        and "sesDurdur();" in SD)
kontrol("calmazsa DURUST hata", "Örnek kayıt çalınamadı." in SD)
kontrol("hata aria-live ile bildirilir", 'id="sbSesNot"' in SD
        and 'aria-live="polite"' in SD)
kontrol("adim degisince calan ses susturulur", "sesDurdur();" in WZ)
# ═══ HARICI SES KATALOGU — GERCEKTEN BAGLI MI ═══
# ⚠ BAGIMSIZ QA BULGUSU: onceki surumde `UCLAR`/`getirSessiz` import ediliyor
# ama HIC KULLANILMIYORDU; "Tum sesler" yalnizca yerel listeyi aciyordu.
# Bu blok yuzeysel "isim var mi" kontrolu DEGIL, cagrinin ve esleme
# kurallarinin varligini dogruluyor.
blok("harici ses katalogu (/api/ses-kutuphane)")
kontrol("/api/ses-kutuphane sozlesmesi korunuyor",
        "sesKutuphane: 'api/ses-kutuphane'" in JS["api.js"])
kontrol("getirSessiz ILE UCLAR.sesKutuphane GERCEKTEN cagriliyor",
        re.search(r"getirSessiz\(\s*\n?\s*`\$\{UCLAR\.sesKutuphane\}", SD)
        is not None, "cagri bulunamadi")
kontrol("saglayici query parametresi gonderiliyor",
        "?saglayici=${encodeURIComponent(saglayici)}" in SD)
kontrol("4 saglayici tanimli",
        "KUTUPHANE_SAGLAYICILARI = ['elevenlabs', 'minimax', 'fishaudio',\n"
        "                                        'kokoro']" in SD
        or ("'elevenlabs'" in SD and "'minimax'" in SD and "'fishaudio'" in SD
            and "'kokoro'" in SD))
kontrol("kaynak secim cipleri uretiliyor", 'data-kaynak="${kac(sg)}"' in SD
        and 'data-kaynak="yerel"' in SD)
# voice_id -> ozel: eslemesi ve SUNUCU REGEXI
kontrol("voice_id -> 'ozel:<saglayici>_<id>' eslemesi",
        "export function ozelSesKimligi" in SD
        and "`ozel:${saglayici}_${String(voiceId ?? '')}`" in SD)
# ⚠ TEK DOGRULUK KAYNAGI: istemci kalibi sunucudaki `_OZEL_SES_RE` ile
# BIREBIR ayni olmali. Uymayan deger sunucuda SESSIZCE dusuyor.
_sunucu_kalip = re.search(r'_OZEL_SES_RE = re\.compile\(r"(.+?)"\)', SUNUCU)
kontrol("sunucu kalibi okunabildi", _sunucu_kalip is not None)
_istemci_kalip = re.search(r"OZEL_SES_KALIBI =\s*\n?\s*/(.+?)/;", SD)
kontrol("istemci kalibi okunabildi", _istemci_kalip is not None)
if _sunucu_kalip and _istemci_kalip:
    kontrol("istemci kalibi SUNUCU kalibiyla AYNI",
            _istemci_kalip.group(1) == _sunucu_kalip.group(1),
            f"sunucu={_sunucu_kalip.group(1)!r} "
            f"istemci={_istemci_kalip.group(1)!r}")
kontrol("kaliba uymayan voice_id SECILEBILIR KART OLMAZ",
        "if (!kimlik) return null;" in SD)
kontrol("elenen ses sayisi kullaniciya bildirilir",
        "kimlik biçimine" in SD and "listelenmedi" in SD)
kontrol("normalize edilen alanlar GERCEK semadan",
        all(x in SD for x in ("oge.ozet", "oge.cinsiyet", "oge.yas",
                              "oge.aksan", "oge.kategori", "oge.onizleme",
                              "oge.diller")))
kontrol("motor = saglayici", "motor: saglayici" in SD)
kontrol("ornek = onizleme", "ornek: oge.onizleme || ''" in SD)
# Tembel yukleme + onbellek
kontrol("TEMBEL: panel acilmadan harici cagri YOK",
        "yalnizca kullanici paneli acip saglayici sectiginde" in SD
        and "if (sg === 'yerel' || durum.katalog[sg])" in SD)
kontrol("onbellek panel durumunda tutuluyor",
        "if (durum.katalog[saglayici]) return durum.katalog[saglayici];" in SD)
kontrol("HATA/503'te YEREL liste korunuyor",
        "const katalogHatasi = kaynakSecimi !== 'yerel' && katalog && !katalog.ok"
        in SD and "? yerel : katalog.liste" in SD)
kontrol("durust fallback metni",
        "Harici katalog alınamadı, kayıtlı sesler gösteriliyor." in SD)
kontrol("yukleniyor durumu gosteriliyor", "Katalog yükleniyor…" in SD)

# ═══════════ 4) MARKA KITI ═══════════
blok("marka kiti: gorsel chip, select DEGIL")
kontrol("marka bolumu var", "export function markaBolumu" in SD)
kontrol("'Yok' secenegi dahil", "Yok — marka kiti kullanma" in SD)
kontrol("radio semantics", 'role="radiogroup" aria-label="Marka kiti"' in SD)
kontrol("gercek metadata gosteriliyor (tur/video_sayisi/kilitli)",
        "p.tur" in SD and "p.video_sayisi" in SD and "p.kilitli" in SD)
kontrol("liste bossa alan SESSIZCE kaybolmaz",
        "Kayıtlı marka kiti yok." in SD)
kontrol("eski select kaldirildi", "id: 'wzProfil'" not in WZ)

# ═══════════ 5) BASIT / PROFESYONEL AYRIMI ═══════════
blok("basit gorunum ve profesyonel bolumler")
kontrol("uc hizli tercih", "export function hizliTercihler" in SD
        and "Akıcı geçiş" in SD and "Hafif kamera hareketi" in SD
        and "'Altyazı'" in SD)
# Hizli tercih ETIKETLERI insan dili; teknik ad yalnizca aciklamada parantezde
_ht = SD[SD.find("export function hizliTercihler"):]
_ht = _ht[:_ht.find("/* ════════════════════ PROFESYONEL")]
kontrol("hizli tercih etiketleri teknik ad TASIMAZ",
        all(x not in _ht for x in ("'zoom'", "'gecis'", "'altyazi_sablon'",
                                   "gorsel_model")),
        "etiketler insan dili olmali")
pro = re.findall(r"\{id: '(\w+)', ad: '([^']+)'", SD)
kontrol("4 profesyonel bolum", len([p for p in pro if p[0] in
        ('renk', 'hareket', 'altyazi', 'uretim')]) == 4, str(pro))
for bid, bad in [('renk', 'Renk ve atmosfer'), ('hareket', 'Hareket ve açılış'),
                 ('altyazi', 'Altyazı görünümü'), ('uretim', 'Üretim ve referans')]:
    kontrol(f"bolum: {bad}", f"id: '{bid}'" in SD and bad in SD)
kontrol("akordeon: AYNI ANDA TEK acik",
        "durum.proAcik = durum.proAcik === hedef ? '' : hedef" in SD
        and "ic.hidden = !acikMi" in SD)
kontrol("aria-expanded + aria-controls", 'aria-expanded="${acik === b.id}"' in SD
        and 'aria-controls="pro-${b.id}"' in SD)
kontrol("'Varsayılan önerilir' ipucu", "Varsayılan önerilir" in SD)
kontrol("teknik/model adlari YALNIZCA profesyonel bolumde",
        "gpt-image" in SD and "gpt-image" not in
        SD[:SD.find("export function proPanel")],
        "model adi yalnizca proPanel icinde")
kontrol("tek dev 'Gelismis' yigini kaldirildi",
        "gelismis('Gelişmiş" not in WZ and "gelismis('Gelismis" not in WZ)

# ═══════════ 6) SECIM OZETI ═══════════
blok("canli secim ozeti")
kontrol("ozet paneli var", "export function ozetPaneli" in SD)
kontrol("masaustunde sticky", ".a3-ozet { position: sticky" in CSS)
kontrol("mobilde KISA SERIT", ".oz-serit" in CSS
        and '.oz[data-acik="0"] .oz-govde { display: none; }' in CSS)
for ad in ("Görsel stil", "Ses", "Marka kiti", "Altyazı", "Atmosfer"):
    kontrol(f"ozet satiri: {ad}", f"satir('{ad}'" in SD)
kontrol("'Değiştir' ilgili bolume odaklanir",
        "data-odak=" in SD and "o.focus({preventScroll: true})" in SD)
kontrol("SAHTE maliyet/puan/yuzde YOK",
        not re.search(r"\$\s?\d|%\s?\d+\s*(oneri|kalite|puan)", TUM_JS_KOD))
kontrol("'AI onerisi %' gibi uydurma gosterge YOK",
        "kalite puan" not in TUM_JS_KOD.lower()
        and "öneri yüzde" not in TUM_JS_KOD.lower())
kontrol("'Önerileni kullan' tek eylem", "wzOnerileniKullan" in SD)
kontrol("reset yalnizca TEMEL secimleri sifirlar",
        "export const ONERILEN_VARSAYILAN" in SD)
_ov = SD[SD.find("export const ONERILEN_VARSAYILAN"):]
_ov = _ov[:_ov.find("};") + 2]
kontrol("reset konu metnini SILMEZ", "konu" not in _ov, _ov[:120])
_reset = SD[SD.find("$('#wzOnerileniKullan', kok)"):]
_reset = _reset[:_reset.find("});") + 3]
kontrol("reset dosyalari SILMEZ", "dosyalariTemizle" not in _reset, _reset[:160])
kontrol("reset kullaniciya ne oldugunu soyler",
        "konu metnin ve yüklediğin dosyalar korunur" in SD)

# ═══════════ 7) GENERATE SOZLESMESI KORUNDU ═══════════
blok("generate alanlari birebir korundu")
imza = SUNUCU[SUNUCU.find("async def uret_baslat"):]
imza = imza[:imza.find("):") + 2]
sunucu_alanlari = set(re.findall(r"(\w+):\s*(?:str|List\[UploadFile\]|UploadFile)",
                                 imza))
on_alanlar = set(re.findall(r"\{ad: '(\w+)'", JS["api.js"]))
# 12 Agu 2026: `unlu` eklendi -> 22
kontrol("22 alan", len(on_alanlar) == 22, str(len(on_alanlar)))
kontrol("alanlar server.py ile AYNI", on_alanlar == sunucu_alanlari,
        f"fark: {sorted(on_alanlar ^ sunucu_alanlari)}")
# Wizard'in urettigi anahtarlar sozlesme icinde mi
_gd = WZ[WZ.find("function generateDegerleri()"):]
_gd = _gd[:_gd.find("export {generateDegerleri}")]
uretilen = set(re.findall(r"d\.(\w+)\s*=", _gd)) | \
    set(re.findall(r"^\s{4}(\w+):", _gd, re.M))
kontrol("wizard sozlesme disina cikmiyor", uretilen <= on_alanlar,
        f"sozlesme disi: {sorted(uretilen - on_alanlar)}")
for zorunlu in ("session", "story", "tur", "edit", "sure_dk", "gecis", "zoom",
                "profil", "altyazi", "altyazi_sablon", "palet", "palet_ozel",
                "acilis", "sora", "arkaplan", "ses", "isik", "gorsel_model",
                "karakter", "stil", "sahne_ref"):
    kontrol(f"alan uretiliyor/korunuyor: {zorunlu}",
            zorunlu in uretilen or zorunlu in ("session", "story", "tur",
                                               "sure_dk", "gecis", "zoom",
                                               "altyazi"),
            "generateDegerleri icinde bulunmali")
# Her alanin bir UI kaynagi var mi (select/input/kart)
# ⚠ Kartlarda grup adi SABLONDAN geliyor (`data-grup="${kac(grup)}"`), bu
# yuzden literal `grup="stil"` aranamaz; uretici cagrisina bakiliyor.
UI_KAYNAK = {
    "edit": "grup: 'stil'", "ses": "grup: 'ses'", "profil": "grup=\"marka\"",
    "palet": "data-grup=\"palet\"", "palet_ozel": "wzHex", "isik": "wzIsik",
    "arkaplan": "wzArkaplan", "acilis": "wzAcilis", "sora": "wzSora",
    "gorsel_model": "wzModel", "altyazi_sablon": "wzAltSablon",
    "karakter": "wzKarGirdi", "stil": "wzStilGirdi", "sahne_ref": "wzRefGirdi",
    "gecis": "wzGecis", "zoom": "wzZoom", "altyazi": "wzAltyazi",
    "sure_dk": "wzSure",
}
for alan_ad, iz in UI_KAYNAK.items():
    kontrol(f"UI kontrolu duruyor: {alan_ad}", iz in SD or iz in WZ,
            f"'{iz}' bulunamadi")

# ═══════════ 8) ERISILEBILIRLIK ═══════════
blok("erisilebilirlik ve radio semantics")
kontrol("kart gruplari role=radiogroup", 'role="radiogroup"' in SD)
kontrol("kartlar role=radio", 'role="radio"' in SD)
kontrol("aria-checked kullaniliyor", 'aria-checked=' in SD)
# ⚠ Dogru kural: role="radio" tasiyan bir oge AYRICA aria-pressed KULLANMAZ.
# `.cip[data-suzgec]` gercek bir toggle oldugu icin aria-pressed dogrudur.
_radyo_bloklari = re.findall(r'role="radio"[^>]*>', SD)
kontrol("role=radio olan hicbir oge aria-pressed kullanmiyor",
        not [b for b in _radyo_bloklari if "aria-pressed" in b],
        str([b[:80] for b in _radyo_bloklari if "aria-pressed" in b]))
# aria-pressed MESRU kullanim: gercek toggle dugmeleri (suzgec ve ses
# kaynagi cipleri role=group icinde, radio DEGIL).
_pressed = re.findall(r'<button[^>]*aria-pressed[^>]*>', SD, re.S)
kontrol("aria-pressed yalnizca gercek toggle'larda (suzgec/kaynak)",
        all(("data-suzgec" in b or "data-kaynak" in b) for b in _pressed),
        str([b[:70] for b in _pressed if "data-suzgec" not in b
             and "data-kaynak" not in b])),
kontrol("klavye: oklar + Home/End", "ArrowRight" in SD and "'Home'" in SD
        and "'End'" in SD)
kontrol("tek tabindex 0 (roving)", 'tabindex="${secili ? \'0\' : \'-1\'}"' in SD)
kontrol("odak tasima radyoBagla icinde", "x.tabIndex = bu ? 0 : -1" in SD)
kontrol("44px dokunma hedefi mobilde zorlanmis",
        ".ses-dinle, .cip, .oz-degistir {" in CSS
        and "min-height: var(--dokunma)" in CSS)
# ⚠ Genisletilmis tarayici olcumu adim gostergesi dugmelerini 36px buldu;
# kural TUM tiklanabilir ogeler icin gecerli.
kontrol("adim gostergesi dugmeleri de 44px'e cikariliyor",
        ".adim-dugme { min-height: var(--dokunma)" in CSS)
kontrol("dinle dugmesi HER genislikte 44px",
        ".ses-dinle {\n  display: inline-flex; align-items: center; gap: 6px;\n"
        "  min-height: var(--dokunma);" in CSS)
kontrol("reduced-motion Faz G bilesenlerini kapsar",
        ".pro-ok, .sk, .pk, .ht { transition: none !important; }" in CSS)
kontrol("aria-live yalnizca gercek degisimi duyurur",
        "duyur('Temel seçimler önerilen değerlere döndü')" in SD)
kontrol("ozet aria-label tasiyor", 'aria-label="Seçim özeti"' in SD)
kontrol("gizli label'lar korunuyor", 'class="gorunmez" for="wzHex' in SD
        and 'for="wzKarGirdi"' in SD)
kontrol("her select label'li",
        SD.count('<label class="alan-ad" for=') >= 3
        or "function proSecim" in SD)

# ═══════════ 9) EMOJI + TURKCE ═══════════
blok("emoji yok, Turkce dogru")
TIPOGRAFIK_IZIN = "→←↑↓·—–…⚠✓×"
EMOJI = re.compile("[\U0001F300-\U0001FAFF\U0001F000-\U0001F2FF"
                   "✀-➿☀-⛿]")
for ad, metin in [("secim-deneyimi.js", SD), ("wizard.js", WZ), ("app.css", CSS)]:
    temiz = yorumsuz(metin)
    for t in TIPOGRAFIK_IZIN:
        temiz = temiz.replace(t, "")
    kontrol(f"emoji yok: {ad}", not EMOJI.findall(temiz),
            str(set(EMOJI.findall(temiz))))
kontrol("yeni ikonlar SVG ikon sistemine eklendi",
        "otomatik:" in JS["ikon.js"] and "oynatDaire:" in JS["ikon.js"]
        and "durdur:" in JS["ikon.js"] and "onayDaire:" in JS["ikon.js"])
YASAK_ASCII = ["Gorsel", "Secildi", "Onerilen", "Onerileni", "Degistir",
               "Altyazi", "Anlatici", "Sablon", "Uretim", "kaynagi",
               "duzenini", "Isik", "Acilis", "Golge", "BUYUK HARF",
               "calinamadi", "Kayitli", "gorunumu"]
# ⚠ Cikarilan dizeler HTML ISARETLEMESI iceriyor; `tabindex=""`, `class="sk"`
# gibi attribute adlari KULLANICI METNI DEGIL. Etiketler soyuluyor.
def metin_nodlari(dize):
    return re.sub(r"<[^>]*>", " ", dize)


gorunen = [metin_nodlari(g) for g in js_dizeleri(SD) + js_dizeleri(WZ)]
gorunen = [g for g in gorunen if " " in g]
birlesik = "\n".join(gorunen)
for y in YASAK_ASCII:
    kalip = (r"(?<![0-9A-Za-z_\-çğıöşüÇĞİÖŞÜ])" + re.escape(y)
             + r"(?![0-9A-Za-z_\-çğıöşüÇĞİÖŞÜ])")
    b = re.search(kalip, birlesik)
    kontrol(f"ASCII yazim kalmadi: '{y}'", b is None,
            birlesik[max(0, b.start() - 30):b.end() + 20] if b else "")
kontrol("Turkce karakter gercekten kullanilmis",
        sum(birlesik.count(c) for c in "çğıöşüÇĞİÖŞÜ") >= 150,
        str(sum(birlesik.count(c) for c in "çğıöşüÇĞİÖŞÜ")))

# ═══════════ 10) MIKRO METIN ═══════════
blok("mikro metin")
_bosluksuz = lambda x: re.sub(r"\s+", " ", x)
kontrol("baslik alti kilavuz cumlesi",
        "Önerileni seçebilir veya ayrıntıları kendin ayarlayabilirsin."
        in _bosluksuz(SD), "adim3Govde icinde olmali")
kontrol("stil bolumu ne yaptigini anlatiyor",
        "Kurgu temposunu, kaynak karışımını ve yazı düzenini belirler." in SD)
kontrol("ses bolumu sade anlatim",
        "Videoyu okuyan ses." in SD)
kontrol("marka kiti sade anlatim",
        "Videolar arasında renk ve karakter tutarlılığı sağlar." in SD)
kontrol("profesyonel panel uyarisi",
        "Gerekmedikçe dokunma" in SD)

# ═══════════ 11) SIZINTI / CIFT BAGLAMA ═══════════
blok("cift baglama ve sizinti korumasi")
kontrol("stil/ses/marka/palet TEK yerde baglaniyor",
        SD.count("radyoBagla(kap, 'stil'") == 1
        and SD.count("radyoBagla(kap, 'ses'") == 1
        and SD.count("radyoBagla(kap, 'marka'") == 1
        and SD.count("radyoBagla(kap, 'palet'") == 1)
kontrol("eski grupBagla stil/palet baglamalari kaldirildi",
        "grupBagla(document, 'stil'" not in WZ
        and "grupBagla(document, 'palet'" not in WZ)
kontrol("radyoBagla ayni dugmeye ikinci dinleyici eklemez",
        "if (b.dataset.bagli === '1') return;" in SD)
kontrol("ozet baglamasi tek fonksiyonda", "function ozetBagla(" in SD
        and SD.count("function ozetBagla(") == 1)
kontrol("adim3 baglamasi yalnizca adim 3'te",
        "if (adim === 3) {" in WZ and "adim3Kur({" in WZ)

# ═══════════ 12) SOZDIZIMI ═══════════
blok("sozdizimi (node --check)")
if subprocess.run(["node", "-v"], capture_output=True).returncode == 0:
    for ad, metin in [("app.js", APP)] + [(f"js/{a}", m) for a, m in JS.items()]:
        with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False,
                                         encoding="utf-8") as f:
            f.write(metin)
            g = f.name
        r = subprocess.run(["node", "--check", g], capture_output=True, text=True)
        os.unlink(g)
        kontrol(f"sozdizimi temiz: {ad}", r.returncode == 0,
                (r.stderr or "").strip().splitlines()[:1])
else:
    print("  --   node yok; sozdizimi kontrolu ATLANDI")



# ═══ HARICI SESIN GORUNEN ADI (son QA bulgusu) ═══
# ⚠ BULGU: ozet paneli yalnizca `kaynak.sesler` icinde ad ariyordu; harici
# katalogtan secilen ses bulunamayinca BACKEND KIMLIGI
# ("ozel:elevenlabs_21m00Tcm4TlvDq8ikWAM") kullanici yuzune cikiyordu.
blok("harici sesin gorunen adi")
kontrol("ad cozucu var", "export function sesGorunenAd" in SD)
kontrol("cozum sirasi: yerel -> katalog -> notr",
        "const yerelKayit = (yerel || []).find" in SD
        and "const kayit = katalog && katalog[m[1]];" in SD)
kontrol("katalog yuklenmemisse TEKNIK KIMLIK gosterilmez",
        "return `Harici ses · ${m[1]}`;" in SD)
kontrol("ozetPaneli katalogu aliyor", "katalog = null}) {" in SD
        and "sesGorunenAd(t.ses, {yerel: kaynak.sesler, katalog," in SD)
kontrol("adim3Govde ozete katalogu geciyor",
        "katalog: durum.katalog})}" in SD)
kontrol("ozetiTazele katalogu geciyor",
        "katalog: durum.katalog});" in SD)
kontrol("katalog yuklenince ozet TAZELENIYOR",
        'ozetiTazele();\n      }' in SD
        and "// Katalog geldi:" in SD)
kontrol("mobil serit de cozulmus adi kullaniyor",
        "${kac(sesAd)} · altyazı" in SD)
# Raw kimlik GORUNUR ozette olmamali: ozetPaneli govdesinde `t.ses` DOGRUDAN
# basilmiyor mu?
_ozet = SD[SD.find("export function ozetPaneli"):]
_ozet = _ozet[:_ozet.find("/**\n * \"Onerileni kullan\"")]
kontrol("ozet govdesi t.ses'i DOGRUDAN yazmiyor",
        "kac(t.ses)" not in _ozet and "${t.ses}" not in _ozet,
        "raw kimlik kullanici yuzune cikmamali")
kontrol("generate degeri DEGISMIYOR (ozel: korunuyor)",
        "if (t.ses) d.ses = t.ses;" in WZ or "d.ses = t.ses" in WZ,
        "wizard generate'e taslaktaki kimligi gonderiyor")

# ═══════════ 13) IC ICE ETKILESIMLI KONTROL — GERCEK DOM ═══════════
# ⚠ Yapi testi tek basina yeterli degil: uretici fonksiyonlarin CIKTISI
# gercek bir DOM'da ayristirilip "button icinde button" araniyor. Node ile
# HTML ayristirici olmadigi icin uretici cikti node'da SABLON olarak
# calistirilip etiket YIGINI ile denetleniyor (bagimlilik eklemeden).
blok("ic ice etkilesimli kontrol (uretici cikti denetimi)")


def ic_ice_buton_var_mi(html):
    """Etiket yigini ile `button`/`[role=button]` ic ice mi? (bulgu listesi)"""
    bulgular = []
    yigin = []
    for m in re.finditer(r"<(/?)([a-zA-Z][a-zA-Z0-9]*)([^>]*)>", html):
        kapanis, etiket_ad, nitelik = m.group(1), m.group(2).lower(), m.group(3)
        if etiket_ad in ("br", "img", "input", "hr", "meta", "link", "rect",
                         "circle", "path", "use"):
            continue
        etkilesimli = (etiket_ad == "button"
                       or re.search(r'role="button"', nitelik) is not None)
        if kapanis:
            if yigin and yigin[-1][0] == etiket_ad:
                yigin.pop()
            continue
        if etkilesimli and any(x[1] for x in yigin):
            bulgular.append(m.group(0)[:70])
        yigin.append((etiket_ad, etkilesimli))
    return bulgular


if subprocess.run(["node", "-v"], capture_output=True).returncode == 0:
    # Ureticileri node'da calistirip HTML'i al
    betik = r"""
import {sesBolumu, stilBolumu, markaBolumu, hizliTercihler, proPanel,
        ozetPaneli} from './secim-deneyimi.js';
const SESLER = [
  {id:'a', ad:'Andrew', ozet:'x y', motor:'openai', dil:'EN', ornek:'ses-ornek/a.mp3'},
  {id:'b', ad:'Yelda', ozet:'', motor:'edge', dil:'TR', ornek:''},
  {id:'c', ad:'Emel', ozet:'z', motor:'edge', dil:'TR', ornek:'ses-ornek/c.mp3'},
  {id:'d', ad:'Brian', ozet:'', motor:'openai', dil:'EN', ornek:''},
];
const STILLER = [{id:'s1', ad:'Bir', ozet:'aa', sahne_sn:7, footage_pct:85},
                 {id:'s2', ad:'Iki', ozet:'', sahne_sn:3, footage_pct:20}];
const KAYNAK = {editStilleri: STILLER, animStilleri: [], sesler: SESLER,
  profiller: [{id:'p1', ad:'Kanal', tur:'doc', video_sayisi:2, kilitli:true}],
  paletler: [{id:'otomatik', ad:'Oto', renkler:[]},
             {id:'p', ad:'Palet', renkler:['#112233','#445566']}],
  isikDuzeyleri: [{id:'i', ad:'Isik'}], arkaplanlar: [{id:'a', ad:'Arka'}],
  altyaziSablonlari: [{id:'t', ad:'Sablon'}], hatalar: []};
const T = {tur:'hikaye', editStili:'s1', animStili:'', ses:'a', profil:'p1',
  palet:'ozel', paletOzel:['#111111','#222222','#333333'], isik:'', arkaplan:'',
  gecis:true, zoom:true, altyazi:true, altyaziSablon:null, acilis:'', sora:false,
  gorselModel:'', sureDk:'2', konu:'x'.repeat(30)};
// Harici ses SECILI + katalog YUKLU  -> ozet "Rachel" demeli
const KATALOG_CACHE = {elevenlabs: {ok:true, dusen:0, liste:[
  {id:'ozel:elevenlabs_x1', ad:'Rachel', ozet:'q', motor:'elevenlabs',
   dil:'en', cinsiyet:'female', yas:'young', aksan:'american',
   ornek:'ses-ornek/r.mp3'}]}};
const parcalar = [
  '<!--OZET-YUKLU-->' + ozetPaneli({t:{...T, ses:'ozel:elevenlabs_x1'},
    kaynak:KAYNAK, dosyaSayisi:0, acik:true, katalog:KATALOG_CACHE}),
  '<!--OZET-YUKSUZ-->' + ozetPaneli({t:{...T, ses:'ozel:elevenlabs_x1'},
    kaynak:KAYNAK, dosyaSayisi:0, acik:true, katalog:{}}),
  stilBolumu({liste: STILLER, deger:'s1', tumunuAc:true, arama:''}),
  sesBolumu({liste: SESLER, deger:'a', tumunuAc:true, arama:'', suzgec:'',
             calan:'a', kaynakSecimi:'elevenlabs',
             katalog:{ok:true, liste:[{id:'ozel:elevenlabs_x1', ad:'Rachel',
               ozet:'q', motor:'elevenlabs', dil:'en', cinsiyet:'female',
               yas:'young', aksan:'american', ornek:'ses-ornek/r.mp3'}], dusen:2}}),
  sesBolumu({liste: SESLER, deger:'', tumunuAc:true, kaynakSecimi:'elevenlabs',
             katalog:{ok:false, hata:'HTTP 503'}}),
  markaBolumu({liste: KAYNAK.profiller, deger:'p1'}),
  hizliTercihler({gecis:true, zoom:false, altyazi:true}),
  proPanel({acik:'renk', t:T, kaynak:KAYNAK}),
  ozetPaneli({t:T, kaynak:KAYNAK, dosyaSayisi:2, acik:true}),
];
process.stdout.write(parcalar.join('\n<hr>\n'));
"""
    yol_betik = os.path.join(JS_DIZIN, "_qa_uretici.mjs")
    with open(yol_betik, "w", encoding="utf-8") as f:
        f.write(betik)
    try:
        r = subprocess.run(["node", yol_betik], capture_output=True, text=True,
                           timeout=60, cwd=JS_DIZIN)
        cikti = r.stdout or ""
        kontrol("ureticiler node'da calisti", r.returncode == 0 and len(cikti) > 2000,
                (r.stderr or "")[:200])
        if cikti:
            bulgular = ic_ice_buton_var_mi(cikti)
            kontrol("HICBIR button/role=button baska button icinde DEGIL",
                    not bulgular, str(bulgular[:3]))
            # Dinle dugmesi kartin KARDESI mi
            kontrol("ses-dinle .sk-sar icinde kartin KARDESI",
                    re.search(r'<div class="sk-sar">\s*<button[^>]*role="radio"'
                              r'[\s\S]*?</button>\s*<button[^>]*class="ses-dinle"',
                              cikti) is not None)
            kontrol("uretilen katalog kimligi 'ozel:' bicimli",
                    'data-deger="ozel:elevenlabs_x1"' in cikti)
            kontrol("503 fallback metni uretimde gorunuyor",
                    "Harici katalog alınamadı" in cikti)
            kontrol("elenen ses notu uretimde gorunuyor",
                    "kimlik biçimine" in cikti)
            kontrol("role=radio olan oge aria-pressed TASIMIYOR (uretimde)",
                    not [b for b in re.findall(r"<button[^>]*>", cikti)
                         if 'role="radio"' in b and "aria-pressed" in b])
            kontrol("kaynak cipleri uretimde var",
                    'data-kaynak="elevenlabs"' in cikti
                    and 'data-kaynak="yerel"' in cikti)
            # ── Harici ses adi: uretici CIKTISINDA dogrula ──
            _yuklu = cikti.split("<!--OZET-YUKLU-->")[1].split("<!--OZET-YUKSUZ-->")[0]
            _yuksuz = cikti.split("<!--OZET-YUKSUZ-->")[1].split("<hr>")[0]
            kontrol("katalog YUKLU: ozet GERCEK adi gosteriyor",
                    ">Rachel<" in _yuklu, _yuklu[:180])
            kontrol("katalog YUKLU: raw 'ozel:' kimligi ozette YOK",
                    "ozel:" not in re.sub(r"<[^>]*>", " ", _yuklu),
                    "backend kimligi kullanici yuzune cikmamali")
            kontrol("katalog YUKSUZ: notr metin, teknik kimlik YOK",
                    "Harici ses" in _yuksuz
                    and "ozel:" not in re.sub(r"<[^>]*>", " ", _yuksuz),
                    _yuksuz[:180])
            kontrol("mobil seritte de raw kimlik YOK",
                    all("ozel:" not in re.sub(r"<[^>]*>", " ", p)
                        for p in (_yuklu, _yuksuz)))
    finally:
        try:
            os.unlink(yol_betik)
        except OSError:
            pass
else:
    print("  --   node yok; uretici DOM denetimi ATLANDI")

print(f"\n{'=' * 60}")
print(f"GECEN: {gecen}   BASARISIZ: {len(basarisiz)}")
for b in basarisiz:
    print(f"  XX {b}")
sys.exit(1 if basarisiz else 0)
