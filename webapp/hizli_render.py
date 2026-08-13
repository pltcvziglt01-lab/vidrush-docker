#!/usr/bin/env python3
"""HIZLI RENDER MOTORU — Chrome'suz, dogrudan ffmpeg ile.

Remotion yolu her kareyi headless Chrome'da cizip ekran goruntusu alir (30 dk video
= 43.200 screenshot ≈ 60-75 dk). Bu motor ayni gorunumu ffmpeg filtreleriyle uretir:
sahne basina zoompan (eased Ken Burns + hikaye 'vurgu' push-in) + vinyet, segmentler
PARALEL islenir, concat ile birlesir, altyazi ASS (libass) ile tek gecişte gomulur.
Ayni is ~8-12 dk.

KAPSAM (v1):
  - Tum sahneler IMAGE olmali (documentary footage klipleri varsa Remotion'a doner)
  - Overlay basligi olan sahne varsa Remotion'a doner (kinetik baslik v1'de yok)
  - Gecisler CROSSFADE (v2, 4 Agu 2026): xfade+acrossfade, obek obek zincirlenir
Uygunsuz durumda False doner; pipeline otomatik Remotion'a duser. RISK YOK.

ACMA/KAPAMA: env RENDER_MOTOR=ffmpeg  VEYA  /opt/vidrush/RENDER_MOTOR dosyasina
"ffmpeg" yaz (docker exec ile, konteyner yeniden yaratmadan acilir/kapanir).
"""
import os
import re
import sys
import json
import math
import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed

KOK_YOL = os.environ.get("VIDRUSH_KOK", "/opt/vidrush")
STUDYO = os.path.join(KOK_YOL, "render-studio")
PUBLIC = os.path.join(STUDYO, "public")
FONT_DIZIN = os.path.join(PUBLIC, "fonts")

# fontlar.ts'deki FontAdi -> TTF aile adi (ASS/libass bu adlarla bulur)
FONT_AILE = {"montserrat": "Montserrat", "anton": "Anton", "bebas": "Bebas Neue",
             "poppins": "Poppins", "oswald": "Oswald", "sistem": "DejaVu Sans"}

# fontlar.ts VARSAYILAN_AYAR'in birebir kopyasi (props'ta alan eksikse buradan tamamlanir)
VARSAYILAN_AYAR = {"font": "montserrat", "boyut": 52, "agirlik": 800, "renk": "#ffffff",
                   "konturRenk": "#000000", "konturKalinlik": 5, "arka": "yok",
                   "konum": "alt", "buyukHarf": False, "golge": True, "harfAralik": 0}


def _tr_buyuk(m):
    """Turkce-dogru buyuk harf (i->İ, ı->I; str.upper() bunu yanlis yapar)."""
    return m.replace("i", "İ").replace("ı", "I").upper()


def _hex_ass(renk, alpha="00"):
    """'#rrggbb' veya 'rgba(r,g,b,a)' -> ASS &HAABBGGRR& formati."""
    renk = (renk or "#ffffff").strip()
    try:
        if renk.startswith("rgba") or renk.startswith("rgb"):
            p = renk[renk.index("(") + 1:renk.rindex(")")].split(",")
            r, g, b = int(float(p[0])), int(float(p[1])), int(float(p[2]))
            a = float(p[3]) if len(p) > 3 else 1.0
            aa = max(0, min(255, int(round((1 - a) * 255))))   # ASS alpha: 00=opak FF=seffaf
            return f"&H{aa:02X}{b:02X}{g:02X}{r:02X}"
        h = renk.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"&H{alpha}{b:02X}{g:02X}{r:02X}"
    except Exception:
        return "&H00FFFFFF"


def _ass_zaman(sn):
    sn = max(0.0, sn)
    h = int(sn // 3600); m = int((sn % 3600) // 60); s = sn % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def _ass_kac(metin):
    """ASS ozel karakterlerini temizle (suslu parantez override bloklari acar)."""
    return (metin or "").replace("{", "(").replace("}", ")").replace("\n", "\\N")


def _ass_uret(sahneler, ayar, stil, yol):
    """Tum videonun altyazisini tek .ass dosyasina yazar. Sahne baslangic ofsetleri
    HARD CUT varsayimiyla kumulatif sure toplamidir (bu motor kesme kullanir)."""
    a = {**VARSAYILAN_AYAR, **(ayar if isinstance(ayar, dict) else {})}
    boyut = int(round(a["boyut"] * (1.12 if stil == "yogun" else 1.0)))
    hiza = {"alt": 2, "orta": 5, "ust": 8}.get(a.get("konum", "alt"), 2)
    kenar = 72 if a.get("konum") == "alt" else 90 if a.get("konum") == "ust" else 0
    kutulu = a.get("arka") not in (None, "", "yok", "transparent")
    # BorderStyle 3 = arka kutu (BackColour dolgu); 1 = kontur+golge
    border_style = 3 if kutulu else 1
    outline = 6 if kutulu else max(0, int(a.get("konturKalinlik", 0)))
    golge = 1 if (a.get("golge") and not kutulu) else 0
    stil_satiri = (
        f"Style: V,{FONT_AILE.get(a.get('font', 'montserrat'), 'Montserrat')},{boyut},"
        f"{_hex_ass(a.get('renk'))},&H000000FF,"
        f"{_hex_ass(a.get('arka') if kutulu else a.get('konturRenk'))},"
        f"{_hex_ass(a.get('arka'), ) if kutulu else _hex_ass('#000000', '60')},"
        f"{-1 if int(a.get('agirlik', 700)) >= 700 else 0},0,0,0,100,100,"
        f"{float(a.get('harfAralik', 0))},0,{border_style},{outline},{golge},"
        f"{hiza},60,60,{kenar},1"
    )
    satirlar = [
        "[Script Info]", "ScriptType: v4.00+", "PlayResX: 1920", "PlayResY: 1080",
        "WrapStyle: 0", "ScaledBorderAndShadow: yes", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        stil_satiri, "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    ofset = 0.0
    adet = 0
    for s in sahneler:
        for p in s.get("altyazi") or []:
            metin = _ass_kac(str(p.get("metin", "")).strip())
            if not metin:
                continue
            if a.get("buyukHarf"):
                metin = _tr_buyuk(metin)
            t0 = ofset + float(p.get("t0", 0))
            t1 = ofset + float(p.get("t1", 0))
            if t1 <= t0:
                continue
            satirlar.append(f"Dialogue: 0,{_ass_zaman(t0)},{_ass_zaman(t1)},V,,0,0,0,,{metin}")
            adet += 1
        ofset += float(s.get("sure", 0))
    with open(yol, "w", encoding="utf-8") as f:
        f.write("\n".join(satirlar) + "\n")
    return adet


def _motion_param(gecis, vurgu):
    """Video.tsx'teki hesaplayicilarin ffmpeg karsiligi: (buyume, panPx, giris_buyume, giris_pay).
    giris_*: sahne basindaki push-in (1+giris_buyume'den 1'e iner, ilk giris_pay karede)."""
    if gecis == "hikaye":
        if vurgu:
            # ACILIS: "videolasmis" his icin sert degerler (1.16/48 yetersizdi — olcumde fark
            # gorunuyor ama izleyici hissetmiyordu). 1.30 zoom + genis pan = kamera geziyor hissi.
            return 1.30, 110, 0.20, 4
        return 1.07, 26, 0.0, 4
    if gecis == "anlati":
        return 1.12, 40, 0.12, 4
    if gecis == "hizli":
        return 1.08, 30, 0.18, 4
    if gecis == "kesme":
        return 1.06, 20, 0.0, 4
    return 1.06, 22, 0.0, 4            # sinematik (varsayilan)


def _zoompan_ifadeleri(sahne, gecis, fps, F):
    """zoompan z/x/y ifadeleri. Easing: 1-(1-p)^2 (KB_EASING bezier'ine yakin easeOutQuad).
    Kaynak 1.5x buyutulmus (2880x1620) -> pan piksel degerleri 1.5 ile carpilir."""
    B, pan_px, giris_b, giris_pay = _motion_param(gecis, bool(sahne.get("vurgu")))
    p = f"(on/{max(F - 1, 1)})"
    pe = f"(1-pow(1-{p},2))"
    zoom = sahne.get("zoom", "yok")
    if zoom == "in":
        kb = f"(1+{B - 1:.4f}*{pe})"
    elif zoom == "out":
        kb = f"({B:.4f}-{B - 1:.4f}*{pe})"
    else:
        kb = "1"
    z = kb
    if giris_b > 0:   # push-in giris: ilk g karede 1+giris_b'den 1'e (easeOutCubic)
        g = max(6, min(14, F // giris_pay))
        z = f"({kb}*(1+{giris_b:.4f}*pow(1-min(on/{g},1),3)))"
    pan = sahne.get("pan", "yok") if zoom != "yok" else "yok"
    px = pan_px * 1.5   # 1920 tuval pikseli -> 2880 kaynak pikseli
    dx = f"{px:.1f}*{pe}" if pan == "right" else f"-{px:.1f}*{pe}" if pan == "left" else "0"
    dy = f"{px:.1f}*{pe}" if pan == "bottom" else f"-{px:.1f}*{pe}" if pan == "top" else "0"
    x = f"iw/2-(iw/zoom/2)+({dx})"
    y = f"ih/2-(ih/zoom/2)+({dy})"
    return z, x, y


# ── GECIS SECIMI — OLCULEN DAGILIM (7 Agu 2026 duzeltmesi) ──
# 20 referans videodan 786 kesme etiketlendi (kare cifti vision + piksel dogrulamasi):
#   sert-kesme %79.9 | karartma %7.6 | beyaz-flash %4.1 | whip-pan %3.3
#   crossfade %2.2 | wipe %1.1 | zoom-through %1.0 | match-cut %0.3
# Yani bu niste GECIS = SERT KESME. Susulu gecislerin toplami %2.4, pratikte yok.
#
# 5 Agu'daki halim YANLISTI: anlatim islevine 6 farkli gecis baglamistim
# (liste->slideleft, gecmis->fadegrays, vurgu->wipeleft, karsilastir->hlslice,
# soru->smoothleft, sonuc->fadeblack). Bu, kesmelerin neredeyse TAMAMINA efekt
# koyuyordu — referansin tam tersi. Simdi varsayilan SERT KESME.
#
# Kanal imzalari (olculdu, genel ortalamaya gore kat):
#   ZeroReports  karartma %23.1 (x3.0)  -> karanlik/gizemli ton
#   NavyDecoded  flash %10.3 (x2.5) + zoom-through %4.8 (x4.7) + whip %6.2 (x1.9)
#   Auralis      %97.5 saf sert kesme   -> sakin anlati
# ⚠ 11 Agu 2026 — "karartma" ARTIK fadeblack DEGIL.
# ffmpeg'in xfade=fadeblack'ini yalitilmis olctum (duz renkli iki klip, 30 fps):
#   d=0.40 -> 118, 118, 59, 0, 0, 0, 3, 16, 30, 44, 57, 66, 75, 84
# Yani inis 2 KARE, siyahta 3 kare, cikis 8 kare — ASIMETRIK. Ekranda "siyaha
# carpip yavas acilma" olarak goruluyor, hata gibi duruyor. Bizim kodun hatasi
# degil, filtrenin kendi davranisi.
# Referans olcumu (OLCUM_EDIT_TAKSONOMI, 786 gecis): karartmada parlaklik 88 -> 44,
# yani SIYAHA HIC INMIYOR, yariya dusuyor. Dogru karsilik: crossfade + iki tarafli
# kisa parlaklik dip'i (bkz. _karartma_dip).
GECIS_IMZA_FFMPEG = {
    "karartma": "fade",
    "flash": "fadewhite",
    "whip": "slideleft",
}


def _ffmpeg_kacir(t: str) -> str:
    """drawtext metin kacisi.

    VIRGUL SILINMEZ, KACIRILIR: ilk surumde siliyordum ve "400,000 DWT" ekranda
    "400000 DWT" olarak cikiyordu. Veri-sayi olculen yazi turlerinin %12'si; binlik
    ayraci kaybolunca sayi okunmaz hale geliyor."""
    return (str(t).replace("\\", "").replace(":", "\\:").replace("'", "")
            .replace("%", "\\%").replace(",", "\\,"))


def _font(ad="Montserrat-Bold.ttf") -> str:
    y = os.path.join(FONT_DIZIN, ad)
    return f"fontfile='{y}':" if os.path.exists(y) else ""


# ─────────────── YAZI SISTEMI (11 Agu 2026 — cikti okunmuyordu) ───────────────
# 11 Agu videosunda "KODOKUSHI: THE LONELY DEATH" ve "COMMUNITY EFFORTS AGAINST
# ISOLATION" ekranda gri/gorunmez cikti. Sebep kontrast: beyaz yazi ACIK zeminde
# (aydinlik koridor duvari) kayboluyor; borderw=3 black@0.62 ayirmaya yetmiyor.
#
# Vidrush ciktisinda olctugum cozum: yazi ZEMINE GUVENMIYOR, altina yari saydam
# koyu bant koyuluyor. Bant kontrasti garanti eder, zemin ne olursa olsun.
#
# Bant SERT acilmiyor: drawbox genislik ifadesi kabul ettigi icin soldan saga
# 0.28 sn'de aciliyor (referans olcumu: giris animasyonlari 0.5 sn'nin ALTINDA;
# 1 sn'lik fade "amator" gorunuyor). Yazi bant acildiktan 0.12 sn sonra beliriyor.
YAZI_GIRIS_SN = 0.28
YAZI_IZGARA_X = 100          # sol hizalama izgarasi


def _yazi_genislik(metin: str, fontsize: int) -> int:
    """Montserrat-Bold icin kaba genislik tahmini — bant yaziyi tam ortmeli."""
    buyuk = sum(1 for c in metin if c.isupper())
    oran = 0.63 if buyuk > len(metin) * 0.6 else 0.57
    return int(len(metin) * fontsize * oran)


def _bant_ve_yazi(metin, fontsize, x, y_ifade, bas, omur, alt_metin="", alt_fontsize=26):
    """Kademeli acilan koyu bant + uzerine kalin beyaz yazi.

    ⚠ FFMPEG TUZAGI (11 Agu 2026'da olcerek bulundu):
    drawbox'un w/h IFADELERINDE "t" DEGISKENI YOKTUR — sadece "enable" ifadesinde var.
    Ilk surumde bantı w='if(lt(t,0.2),0,GEN*(t-0.2)/0.28,...)' ile soldan saga acmaya
    calistim. t tanimsiz oldugu icin ifade son dala dusup 23.663 uretti ve ffmpeg bantı
    kareye kirpti: bant HER SAHNEDE tam ekran cizildi (piksel olcumu: x=75'ten 1919'a,
    yani tam olarak iw - x = 1845).
    Cozum: genislik SABIT sayilarla verilir, animasyon "enable" zaman pencereleriyle
    kademeli yapilir. 3 kademe x 0.07 sn = 0.21 sn acilis; referans olcumunde giris
    animasyonlari 0.5 sn'nin ALTINDA oldugu icin bu yeterli ve dogru."""
    gir = YAZI_GIRIS_SN
    son = bas + omur
    kapan = son + gir
    dolgu = int(fontsize * 0.42)
    gen = _yazi_genislik(metin, fontsize) + dolgu * 2
    if alt_metin:
        gen = max(gen, _yazi_genislik(alt_metin, alt_fontsize) + dolgu * 2)
    gen = min(gen, 1740)                    # kareyi tasmasin
    yuk = fontsize + dolgu * 2 + (alt_fontsize + 10 if alt_metin else 0)
    y_kutu = y_ifade.replace("h*", "ih*")   # drawbox'ta girdi yuksekligi "ih"
    kx = x - dolgu

    def kutu(w, t0, t1):
        return (f",drawbox=x={kx}:y='{y_kutu}-{dolgu}':w={int(w)}:h={yuk}:"
                f"color=black@0.62:t=fill:enable='between(t\,{t0:.3f}\,{t1:.3f})'")

    f = ""
    KADEME = 3
    adim = gir / (KADEME + 1)
    for k in range(1, KADEME + 1):                      # acilis
        f += kutu(gen * k / KADEME, bas + adim * (k - 1), bas + adim * k)
    f += kutu(gen, bas + gir, son)                      # tutma
    for k in (2, 1):                                    # kapanis
        f += kutu(gen * k / 3, son + gir * (2 - k) / 3, son + gir * (3 - k) / 3)

    # YAZI: alpha ifadesi drawtext'te CALISIR (drawbox'tan farkli olarak t var)
    y_bas = bas + 0.12
    alfa = (f"if(lt(t\,{y_bas:.2f})\,0\,"
            f"if(lt(t\,{y_bas + gir:.2f})\,(t-{y_bas:.2f})/{gir:.2f}\,"
            f"if(lt(t\,{son:.2f})\,1\,max(0\,({kapan:.2f}-t)/{gir:.2f}))))")
    f += (f",drawtext={_font()}text='{metin}':fontcolor=white:fontsize={fontsize}:"
          f"borderw=2:bordercolor=black@0.55:"
          f"x={x}:y='{y_ifade}':alpha='{alfa}'")
    if alt_metin:
        f += (f",drawtext={_font()}text='{alt_metin}':fontcolor=white@0.88:"
              f"fontsize={alt_fontsize}:borderw=2:bordercolor=black@0.55:"
              f"x={x}:y='{y_ifade}+{fontsize + 10}':alpha='{alfa}'")
    return f


def _alt_band_filtre(sahne, fps, F):
    """Alt band (lower third) — olculen EN YAYGIN yazi turu (%33), omur 4.7 sn.
    11 Agu 2026: kontrast bandina cevrildi; onceden sadece kontur vardi ve acik
    zeminde yazi kayboluyordu."""
    ab = sahne.get("altBand")
    if not isinstance(ab, dict) or not str(ab.get("baslik") or "").strip():
        return ""
    b = _ffmpeg_kacir(str(ab["baslik"]).strip()[:34])
    a = _ffmpeg_kacir(str(ab.get("alt") or "").strip()[:40])
    omur = min(4.7, max(1.0, F / fps - 0.4))
    bas = 0.3
    f = _bant_ve_yazi(b, 42, YAZI_IZGARA_X + 22, "h*0.78", bas, omur,
                      alt_metin=a, alt_fontsize=25)
    yuk = 42 + int(42 * 0.42) * 2 + (25 + 10 if a else 0)
    f += (f",drawbox=x={YAZI_IZGARA_X}:y='ih*0.78-{int(42 * 0.42)}':w=6:h={yuk}:"
          f"color=#F5E14B@0.95:t=fill:"
          f"enable='between(t\,{bas:.2f}\,{bas + omur + YAZI_GIRIS_SN:.2f})'")
    return f

def _kaynak_yazi_filtre(sahne, fps, F):
    """Sag altta kucuk, yari saydam kaynak yazisi — "Kanal Adi / CC BY".

    NEDEN VAR (11 Agu 2026, Polat'in onerisi): Creative Commons klip kullanmak ATIF
    ZORUNLULUGU getirir. Bu yaziyi koymadan CC klip kullanmak lisansi ihlal ediyordu.
    ONEMLI SINIR: bu yazi TELIF IZNI DEGILDIR. Telifli bir videoya kaynak yazmak onu
    kullanilabilir yapmaz; Content ID yine talep acar. Bu yuzden youtube_sahne CC
    disina cikmaz ve bu yazi da yalnizca CC kliplerde ciziliyor.
    Lisansin resmi atif yeri VIDEO ACIKLAMASI — kaynak.atif_listesi() onu uretiyor."""
    kanal = str(sahne.get("kaynakYazi") or "").strip()
    if not kanal:
        return ""
    m = _ffmpeg_kacir(kanal[:34])
    if not m:
        return ""
    fnt = _font("Montserrat-Bold.ttf")
    fs = 21
    # Okunurluk zemine birakilmaz: ince koyu kontur + hafif golge. Bant KOYMUYORUZ,
    # cunku bu yazi bilgi degil kunye — goze batmamali ama secilmeli.
    # ⚠ FAZ I-41: KONUM HESAPLANDI, "yeterince kenarda" VARSAYILMADI.
    # Eski `x=w-tw-26:y=h-th-22` 1080p'de alt kenardan 22 px'te duruyordu —
    # yayin guvenli alani (64 px) DISINDA ve altyazi seridinin dibinde.
    # Yeni konum SAG UST: oran `tipografi.KAYNAK_ETIKETI_ALTYAZILI` (0.075),
    # kenar 64 px. `Video.tsx > KaynakYazi` AYNI sayilari kullanir; iki
    # renderer arasinda IKINCI ARITMETIK YOKTUR (I-40 dersi).
    return (f",drawtext=fontfile='{fnt}':text='{m}':"
            f"x=w-tw-64:y=h*0.075:fontsize={fs}:fontcolor=white@0.62:"
            f"borderw=2:bordercolor=black@0.5:shadowx=1:shadowy=1:shadowcolor=black@0.4")


def _etiket_filtre(sahne, fps, F):
    """Saha etiketleri — SahaEtiketleri'nin ffmpeg karsiligi.
    OLCULEN omur 1.8 sn, giris 0.28 sn. Nokta+cizgi drawbox ile."""
    et = sahne.get("etiketler")
    if not isinstance(et, list) or not et:
        return ""
    f = ""
    for i, e in enumerate(et[:2]):
        if not isinstance(e, dict):
            continue
        m = _ffmpeg_kacir(str(e.get("metin") or "").strip()[:26])
        try:
            x, y = float(e.get("x")), float(e.get("y"))
        except Exception:
            continue
        if not m or not (0 < x < 1 and 0 < y < 1):
            continue
        bas = 0.35 + i * 0.5
        son = bas + 1.8
        gir = 0.28
        alfa = (f"if(lt(t\\,{bas:.2f})\\,0\\,if(lt(t\\,{bas + gir:.2f})\\,"
                f"(t-{bas:.2f})/{gir:.2f}\\,if(lt(t\\,{son:.2f})\\,1\\,"
                f"max(0\\,({son + gir:.2f}-t)/{gir:.2f}))))")
        saga = x < 0.5
        # nokta
        # Koyu halka + beyaz nokta: acik zeminde beyaz nokta tek basina kayboluyor
        f += (f",drawbox=x=iw*{x:.3f}-7:y=ih*{y:.3f}-7:w=14:h=14:color=black@0.55:t=fill:"
              f"enable='between(t\\,{bas:.2f}\\,{son + gir:.2f})'"
              f",drawbox=x=iw*{x:.3f}-5:y=ih*{y:.3f}-5:w=10:h=10:color=white@0.95:t=fill:"
              f"enable='between(t\\,{bas:.2f}\\,{son + gir:.2f})'")
        # cizgi
        cx = f"iw*{x:.3f}" if saga else f"iw*{x:.3f}-78"
        f += (f",drawbox=x={cx}:y=ih*{y:.3f}-1:w=78:h=3:color=white@0.95:t=fill:"
              f"enable='between(t\\,{bas:.2f}\\,{son + gir:.2f})'")
        # yazi
        tx = f"w*{x:.3f}+92" if saga else f"w*{x:.3f}-92-tw"
        f += (f",drawtext={_font()}text='{m.upper()}':fontcolor=white:fontsize=30:"
              f"borderw=3:bordercolor=black@0.85:shadowcolor=black@0.9:shadowx=0:shadowy=2:"
              f"x={tx}:y=h*{y:.3f}-15:alpha='{alfa}'")
    return f


def _vurgu_kutu_filtre(sahne, fps, F):
    """Cerceve vurgusu — CerceveVurgusu'nun ffmpeg karsiligi.
    Kose isaretleri yerine ince tam cerceve (drawbox tek dikdortgen cizer)."""
    k = sahne.get("vurguKutu")
    if not isinstance(k, dict):
        return ""
    try:
        x, y, w, h = float(k["x"]), float(k["y"]), float(k["w"]), float(k["h"])
    except Exception:
        return ""
    if not (0 <= x < 1 and 0 <= y < 1 and 0 < w <= 1 and 0 < h <= 1):
        return ""
    bas = 0.5
    son = max(bas + 1.5, F / fps - 0.4)
    # Koyu kalin cerceve ALTA, beyaz ince cerceve USTE -> her zeminde okunur
    return (f",drawbox=x=iw*{x:.3f}-2:y=ih*{y:.3f}-2:w=iw*{w:.3f}+4:h=ih*{h:.3f}+4:"
            f"color=black@0.55:t=8:enable='between(t\\,{bas:.2f}\\,{son:.2f})'"
            f",drawbox=x=iw*{x:.3f}:y=ih*{y:.3f}:w=iw*{w:.3f}:h=ih*{h:.3f}:"
            f"color=white@0.95:t=4:enable='between(t\\,{bas:.2f}\\,{son:.2f})'")


def _bolum_filtre(sahne, fps, F):
    """Bolum basligi. ARTIK EKRANIN ORTASINA YAZILMIYOR (11 Agu 2026): ortali baslik
    yuzun/konunun tam ustune denk geliyordu, hem okunmuyor hem goruntuyu kapatiyordu."""
    b = str(sahne.get("bolum") or "").strip()
    if not b:
        return ""
    yer = str(sahne.get("bolumYeri") or "orta")
    if yer == "ust":
        return _bant_ve_yazi(_ffmpeg_kacir(b[:46]), 44, YAZI_IZGARA_X, "h*0.055", 0.2, 4.5)
    return _bant_ve_yazi(_ffmpeg_kacir(b.upper()[:42]), 60, YAZI_IZGARA_X,
                         "h*0.70", 0.2, 5.5)

def _overlay_filtre(sahne, fps, F):
    """Overlay basligini drawtext ile ciz (4 Agu 2026 — bu eksik oldugu icin overlay'li
    isler Remotion'a dusuyordu ve 15 dk video 2 saat suruyordu).
    Remotion'daki gibi kelime kelime yay animasyonu ffmpeg'de yok; onun yerine
    yumusak fade-in/out + hafif yukari kayma yapilir. Kontur (borderw) her zeminde okunur."""
    metin = str(sahne.get("overlay") or "").strip()
    if not metin:
        return ""
    # drawtext'te ozel karakterler kacilmali
    g = (metin.replace("\\", "").replace(":", "\\:").replace("'", "")
              .replace("%", "\\%").replace(",", ""))
    gir = min(0.5, F / fps / 6)          # giris suresi
    # Ekranda kalma SINIRLI. 5 Agu 2026: 12 sn'lik sahnede baslik 11 sn boyunca duruyordu;
    # Remotion tarafinda ayni baslik ~2.7 sn sonra soluyor. Iki motor ayni videoda
    # karisabildigi icin davranis birebir ayni olmali. Rozet zaten sahne boyunca duruyor,
    # baslik onunla yarismasin.
    kal = max(0.6, min(2.6, F / fps - 2 * gir))
    font = os.path.join(FONT_DIZIN, "Montserrat-Bold.ttf")
    fontstr = f"fontfile='{font}':" if os.path.exists(font) else ""
    # alpha: 0 -> 1 -> 1 -> 0 (yumusak)
    # ffmpeg filtre ayristiricisi VIRGULU filtre ayraci sayar — ifade icindekiler
    # tirnak icinde olsa bile kacirilmali (\\,), yoksa "No such filter" hatasi verir.
    alpha = (f"if(lt(t\\,{gir:.2f})\\,t/{gir:.2f}\\,"
             f"if(lt(t\\,{gir + kal:.2f})\\,1\\,max(0\\,({gir * 2 + kal:.2f}-t)/{gir:.2f})))")
    # y: hafif yukari kayma (24 px), giris boyunca
    yy = f"120+24*(1-min(1\\,t/{gir:.2f}))"
    f = (f",drawtext={fontstr}text='{g}':fontcolor=white:fontsize=64:"
         f"borderw=5:bordercolor=black@0.9:shadowcolor=black@0.5:shadowx=0:shadowy=3:"
         f"x=(w-text_w)/2:y='{yy}':alpha='{alpha}'")
    # GERI SAYIM ROZETI: Video.tsx'teki GeriSayimRozeti'nin ffmpeg karsiligi.
    # Baslik bir sayiyla basliyorsa (or. "11 PAPER TOWELS") o sayi sol ustte SAHNE
    # BOYUNCA durur — referans kanalin liste videolarindaki omurga (olcum: %35 kare).
    m = re.match(r"^(\d{1,2})\b", metin.strip())
    if m:
        rfont = os.path.join(FONT_DIZIN, "Anton-Regular.ttf")
        rfontstr = f"fontfile='{rfont}':" if os.path.exists(rfont) else fontstr
        f += (f",drawtext={rfontstr}text='{m.group(1)}':fontcolor=white:fontsize=132:"
              f"borderw=7:bordercolor=black:shadowcolor=black@0.45:shadowx=0:shadowy=6:"
              f"x=56:y=48")
    return f


# ─────────────── CEKIM BOLME (11 Agu 2026 — en buyuk kurgu boslugu) ───────────────
# Olculen durum: 1 anlatim sahnesi = 1 klip = 1 kesintisiz cekim, ortalama 5.25 sn.
# Referans olcumu (OLCUM_EDIT_TAKSONOMI, 246 cekim): medyan cekim 6.5 sn AMA dagilim
# CIFT MODLU — cekimlerin %32'si 4 saniyenin ALTINDA. Yani bir anlatim beat'inin
# icinde birden fazla cekim var. Vidrush ciktisinda da olctum: 1-3 sn.
# Bizde bu hic yoktu, video "slayt gosterisi" gibi duruyordu.
#
# COZUM EKSTRA INDIRME GEREKTIRMIYOR: ayni klibin FARKLI ZAMAN NOKTASI + FARKLI
# KADRAJI ikinci cekim olarak kullaniliyor (kurguda "cutting within a shot" denen
# klasik teknik). Klip 12 saniyeye kirpiliyor, sahne 5-9 sn; yani ikinci cekim icin
# gercek malzeme var, donmus kare tekrari degil.
CEKIM_MIN_SN = 2.2          # bundan kisa cekim goz yormaya basliyor
CEKIM_BOL_ESIK = 5.0        # bu sureden uzun sahne bolunmeye ADAY olur
# ⚠ HER SAHNE BOLUNMEZ (11 Agu 2026 olcumu). Ilk surumde esigi gecen her sahneyi
# boluyordum ve sonuc TERS yone kacti: sahne suresi 6.55 sn (referans medyani 6.5,
# tam isabet) olmasina ragmen ortalama CEKIM 3.9 sn'ye, 4 sn alti cekim orani %59'a
# cikti — referans %32.
# Referansin dagilimi CIFT MODLU: cogu cekim uzun, azinligi cok kisa. Matematigi:
#   bolunen oran f ise -> cekim sayisi N(1+f), 4 sn alti pay 2f/(1+f)
#   hedef %32  ->  2f/(1+f) = 0.32  ->  f = 0.19
# Yani sahnelerin sadece ~%19'u bolunmeli. Secim deterministik (ayni sahne her
# uretimde ayni davranir), rastgele degil.
CEKIM_BOL_ORAN = int(os.environ.get("CEKIM_BOL_ORAN", "19"))   # yuzde
CEKIM_UC_BOL_ESIK = 10.0    # 3 parcaya sadece cok uzun sahneler bolunur


def _cekim_planla(sure: float, indeks: int) -> list:
    """Sahne suresini cekimlere bol. Deterministik: ayni sahne her uretimde ayni bolunur.
    Donen: [(baslangic_sn, sure_sn, kadraj_kodu)] — kadraj 0 = tam kare, 1-2 = punch-in."""
    if sure < CEKIM_BOL_ESIK:
        return [(0.0, sure, 0)]
    # ⚠ KULLANICI KURALI (7 Agu 2026, degismedi): hicbir goruntu 8 SANIYEDEN fazla
    # ekranda kalmaz. Bu kural %19'luk secici bolmeden ONCE gelir — 8 sn'yi asan
    # sahne SECIM DISI, her zaman bolunur. (11 Agu olcumu: secici bolmeye gecince
    # cekimlerin %18'i 8 sn'yi asti; kural ihlal ediliyordu.)
    ZORUNLU = 8.0
    if sure <= ZORUNLU and (indeks * 7919 + 13) % 100 >= CEKIM_BOL_ORAN:
        return [(0.0, sure, 0)]
    adet = 2 if sure < CEKIM_UC_BOL_ESIK else 3
    # 8 sn tavani: parca sayisi her parca 8 sn'nin altinda kalacak kadar artirilir
    while sure / adet > ZORUNLU and adet < 5:
        adet += 1
    if sure / adet < CEKIM_MIN_SN:
        adet = max(1, int(sure // CEKIM_MIN_SN))
    if adet < 2:
        return [(0.0, sure, 0)]
    # Esit bolmuyoruz: referansta cekimler esit degil. 55/45 ve 40/35/25 dagilimi
    # kullaniyoruz — esit bolme metronom gibi duyuluyor.
    paylar = {2: (0.55, 0.45), 3: (0.40, 0.35, 0.25),
              4: (0.30, 0.27, 0.23, 0.20), 5: (0.24, 0.22, 0.20, 0.18, 0.16)}[adet]
    # Sahne indeksine gore paylari cevir ki her sahne ayni ritimde olmasin
    if indeks % 2:
        paylar = tuple(reversed(paylar))
    cekimler, t = [], 0.0
    for k, pay in enumerate(paylar):
        d = sure * pay if k < adet - 1 else max(0.05, sure - t)
        # Kadraj: ilk cekim tam kare, sonrakiler punch-in (farkli bolge)
        cekimler.append((round(t, 3), round(d, 3), k))
        t += d
    return cekimler


def _kadraj_vf(kod: int, indeks: int) -> str:
    """Cekim kadraji. 0 = tam kare. 1/2 = punch-in: kaynagin bir bolgesine yaklas.
    Punch-in kaynak 2560 genislikte oldugu icin 1080p ciktida kayip yok."""
    if kod == 0:
        return "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080"
    olcek = 1.38 if kod == 1 else 1.62
    # Bolge secimi deterministik ama sahneye gore degisir (hep ayni yere yaklasmasin)
    yatay = [0.5, 0.34, 0.66, 0.42][(indeks + kod) % 4]
    dikey = [0.44, 0.5, 0.38, 0.56][(indeks * 3 + kod) % 4]
    g = int(1920 / olcek) // 2 * 2
    y = int(1080 / olcek) // 2 * 2
    return (f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,"
            f"crop={g}:{y}:x='(iw-{g})*{yatay:.2f}':y='(ih-{y})*{dikey:.2f}',"
            f"scale=1920:1080:flags=lanczos")


GECIS_SN_TAHMIN = 0.4       # HIZLI_GECIS_SN varsayilani (dip'i onune yerlestirmek icin)
KARARTMA_DIP_SN = 0.24      # dip'in her yarisi
KARARTMA_DIP = 0.13         # olculdu: 0.20 -> dip %32'ye iniyordu, referans %50


def _karartma_dip(sahne, sure: float) -> str:
    """Karartma imzasinin gercek karsiligi: sahnenin BASINDA ve/veya SONUNDA kisa
    parlaklik dip'i. Siyaha inmez — referansta olculen sey parlakligin YARIYA
    dusmesi (88 -> 44), tam karartma degil.
    eq'nun eval=frame kipi ifadelerde "t" kabul ediyor; drawbox'un aksine burada
    zaman degiskeni CALISIYOR."""
    parcalar = []
    if sahne.get("_karart_bas"):
        parcalar.append(f"if(lt(t\,{KARARTMA_DIP_SN})\,"
                        f"-{KARARTMA_DIP}*(1-t/{KARARTMA_DIP_SN})\,0)")
    if sahne.get("_karart_son"):
        # DIKKAT: dip crossfade penceresinin ONUNDE bitmeli. Ilk surumde dip'i
        # sahnenin son 0.24 sn'sine koydum; ama crossfade de son 0.4 sn'yi tuketiyor,
        # yani A zaten devreden cikarken kararmaya basliyordu ve ekranda inis
        # gorunmuyordu (olcum: 116 -> 37 tek karede). Dip crossfade'den ONCE tamamlanir
        # ve dipli seviye kuyruk boyunca korunur.
        bitis = max(0.0, sure - GECIS_SN_TAHMIN)
        t0 = max(0.0, bitis - KARARTMA_DIP_SN)
        parcalar.append(f"if(lt(t\,{t0:.3f})\,0\,"
                        f"if(lt(t\,{bitis:.3f})\,"
                        f"-{KARARTMA_DIP}*(t-{t0:.3f})/{KARARTMA_DIP_SN}\,"
                        f"-{KARARTMA_DIP}))")
    if not parcalar:
        return ""
    return f",eq=eval=frame:brightness='{'+'.join(parcalar)}'"


def _zoompan_efekt(g: float, sure: float, fps: int) -> str:
    """Kare kare degerlendirilen yavas zoom. zoompan'in "z" ifadesinde kare sayaci
    "on" kullanilabiliyor; crop/scale'in boyut ifadelerinde zaman YOK."""
    kare = max(1, int(round(sure * fps)))
    return (f",zoompan=z='1+{g:.4f}*on/{kare}':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d=1:s=1920x1080:fps={fps}")


def _efekt_ffmpeg(_ef: dict, sure: float, fps: int) -> str:
    """Efektler.tsx'te olan ama hizli motorda KARSILIGI OLMAYAN efektlerin ffmpeg hali.

    NEDEN (11 Agu 2026): iki render yolu ayrisiyordu. Efektler.tsx'te 35 bilesen,
    hizli motorda 6 filtre vardi ve RENDER_MOTOR=ffmpeg varsayilan oldugu icin
    sarsinti / elde-kamera / dolly-zoom / kromatik / yon-blur / glow gibi efektler
    SESSIZCE KAYBOLUYORDU. Kullanicinin gordugu tek "edit" grain + vinyet + zoom'du.
    Bu, kalite sistemi degil kura: hangi yol kosarsa o kalite cikiyordu.

    Buradaki karsiliklarin hepsi saf matematik — ffmpeg'de bedava yapilabiliyor.
    ZAMAN DEGISKENI NOTU: crop/rotate/rgbashift ifadelerinde "t" CALISIR
    (drawbox'un w/h ifadelerinin aksine, bkz. _bant_ve_yazi).
    """
    f = ""
    # ── SARSINTI: crop penceresini karesel titret. Referansta vurgu anlarinda var.
    for ad, carpan in (("sarsinti", 1.0), ("agresif-sarsinti", 2.6)):
        if ad in _ef:
            g = max(1.0, 6.0 * carpan * float(_ef[ad]))
            # Iki farkli frekans -> mekanik degil organik titreme
            dx = f"({g:.1f}*sin(t*37)+{g * 0.6:.1f}*sin(t*61))"
            dy = f"({g:.1f}*cos(t*43)+{g * 0.6:.1f}*sin(t*71))"
            pay = int(g * 2 + 4) * 2
            f += (f",scale=iw+{pay}:ih+{pay}:flags=bicubic,"
                  f"crop=w=iw-{pay}:h=ih-{pay}:x='{pay // 2}+{dx}':y='{pay // 2}+{dy}'")
            break
    # ── ELDE KAMERA: yavas, genis genlikli surukleme (sarsintidan farki: dusuk frekans)
    if "elde-kamera" in _ef:
        g = max(2.0, 9.0 * float(_ef["elde-kamera"]))
        pay = int(g * 2 + 6) * 2
        dx = f"({g:.1f}*sin(t*1.7)+{g * 0.5:.1f}*sin(t*2.9))"
        dy = f"({g:.1f}*cos(t*1.3)+{g * 0.5:.1f}*cos(t*2.3))"
        f += (f",scale=iw+{pay}:ih+{pay}:flags=bicubic,"
              f"crop=w=iw-{pay}:h=ih-{pay}:x='{pay // 2}+{dx}':y='{pay // 2}+{dy}'")
    # ── DOLLY ZOOM: sure boyunca kadraji yavasca daralt.
    # ⚠ crop ILE YAPILAMAZ (11 Agu 2026 olcumu): crop'un w/h ifadeleri config aninda
    # BIR KEZ degerlendiriliyor ve "t" tanimli degil — ffmpeg
    # "Error when evaluating the expression 'ih/1.1/(1+0.030*t/4.00)'" verip segmenti
    # tamamen dusuruyordu (sahne videodan kayboluyor). crop'ta t yalnizca x/y'de var.
    # zoompan'in "z" ifadesi kare kare degerlendiriliyor, dogru arac o.
    if "dolly-zoom" in _ef and sure > 0.5:
        g = min(0.16, 0.09 * float(_ef["dolly-zoom"]))
        f += _zoompan_efekt(g, sure, fps)
    # ── YON BLUR: karsilastirma anlarinda yatay kayma hissi
    if "yon-blur" in _ef:
        g = max(1, int(6 * float(_ef["yon-blur"])))
        f += f",gblur=sigma={g}:sigmaV=0"
    # ── KROMATIK: RGB kanallarini ayir (referansta gerilim anlarinda)
    if "kromatik" in _ef:
        k = max(1, int(3 * float(_ef["kromatik"])))
        f += f",rgbashift=rh=-{k}:bh={k}"
    # ── GLOW: parlak bolgeleri yumusatarak ust uste bindir
    if "glow" in _ef:
        g = float(_ef["glow"])
        f += f",unsharp=5:5:{-0.6 * g:.2f}:5:5:0,eq=brightness={0.02 * g:.3f}"
    # ── KESKINLESTIR
    if "keskinlestir" in _ef:
        f += f",unsharp=5:5:{0.8 * float(_ef['keskinlestir']):.2f}:5:5:0"
    # ── YUMUSAK ZOOM (sonuc sahnelerinde): cok hafif nefes
    if "yumusak-zoom" in _ef and sure > 0.5:
        g = min(0.05, 0.03 * float(_ef["yumusak-zoom"]))
        f += _zoompan_efekt(g, sure, fps)
    # ── SUZULME / DONME-3D: 2B'de karsiligi yok, atlanir (Remotion'a ozel)
    return f


def _segment_uret(sahne, gecis, fps, crf, seg_yol):
    """Tek sahne segmentini uretir. Gorsel sahne: Ken Burns + kendi sesi.
    VIDEO sahne (Sora klibi / footage): klip 1080p'ye olceklenir, gerekirse dongulenir,
    uzerine sahnenin TTS sesi biner (klibin kendi sesi kullanilmaz)."""
    medya = os.path.join(PUBLIC, sahne["medya"])
    ses = os.path.join(PUBLIC, sahne["ses"])
    sure = float(sahne["sure"])
    if not (os.path.exists(medya) and os.path.exists(ses)) or sure <= 0:
        return False
    F = max(1, int(round(sure * fps)))
    if sahne.get("tur") == "video":
        # Gercek video: Ken Burns YOK (klibin kendi hareketi var). Kisa klip donguyle uzar.
        # CEKIM BOLME: sahne CEKIM_BOL_ESIK'ten uzunsa ayni klipten farkli zaman
        # noktasi + farkli kadrajla 2-3 cekim uretilip birlestirilir. Katmanlar
        # (bolum/alt band/etiket/kunye) BIRLESTIRME SONRASINA uygulanir, cunku
        # zamanlamalari sahneye gore — cekim basina uygulansa her cekimde bastan baslar.
        sindeks = int(sahne.get("_indeks") or 0)
        cekimler = _cekim_planla(sure, sindeks)
        girisler, zincirler, etiketler = [], [], []
        for k, (bas, d, kadraj) in enumerate(cekimler):
            # -ss/-t GIRIS secenegi: her cekim klibin farkli anindan alinir.
            girisler += ["-stream_loop", "-1", "-ss", f"{bas:.3f}", "-t", f"{d:.3f}",
                         "-i", medya]
            _ef_v = {str(e.get("ad")): float(e.get("siddet") or 1)
                     for e in (sahne.get("efektler") or []) if isinstance(e, dict)}
            renk = ""
            if "grain" in _ef_v:
                renk += f",noise=alls={int(6 + 6 * _ef_v['grain'])}:allf=t+u"
            if "vinyet" in _ef_v:
                renk += ",vignette=angle=PI/5"
            if "siyah-beyaz" in _ef_v:
                renk += ",hue=s=0"
            if "kontrast-grade" in _ef_v:
                renk += f",eq=contrast={1 + 0.18 * _ef_v['kontrast-grade']:.3f}"
            if "sicak-grade" in _ef_v:
                renk += f",colortemperature=temperature={int(6500 - 700 * _ef_v['sicak-grade'])}"
            if "soguk-grade" in _ef_v:
                renk += f",colortemperature=temperature={int(6500 + 900 * _ef_v['soguk-grade'])}"
            renk += _efekt_ffmpeg(_ef_v, d, fps)
            zincirler.append(f"[{k}:v]{_kadraj_vf(kadraj, sindeks)},fps={fps}"
                             f"{renk},setsar=1[c{k}]")
            etiketler.append(f"[c{k}]")
        ses_giris = len(cekimler)
        if len(cekimler) > 1:
            zincirler.append("".join(etiketler) + f"concat=n={len(cekimler)}:v=1:a=0[cat]")
            kaynak_etiket = "[cat]"
        else:
            kaynak_etiket = etiketler[0]
        katman = (_karartma_dip(sahne, sure) + _overlay_filtre(sahne, fps, F)
                  + _bolum_filtre(sahne, fps, F) + _alt_band_filtre(sahne, fps, F)
                  + _etiket_filtre(sahne, fps, F) + _vurgu_kutu_filtre(sahne, fps, F)
                  + _kaynak_yazi_filtre(sahne, fps, F) + ",format=yuv420p")
        # katman "," ile basliyor; setpts ile sifirdan baslat ki drawtext zamanlari
        # birlestirme sonrasi sahne basina gore dogru olsun.
        zincirler.append(f"{kaynak_etiket}setpts=PTS-STARTPTS{katman}[v]")
        komut = ["ffmpeg", "-y", "-loglevel", "error"] + girisler + [
                 "-i", ses,
                 "-filter_complex", ";".join(zincirler),
                 "-map", "[v]", "-map", f"{ses_giris}:a",
                 "-af", f"apad=whole_dur={sure:.3f}",
                 "-t", f"{sure:.3f}", "-r", str(fps),
                 "-c:v", "libx264", "-crf", str(crf), "-preset", "veryfast",
                 "-c:a", "aac", "-ar", "44100", "-b:a", "160k",
                 seg_yol]
        try:
            r = subprocess.run(komut, capture_output=True, text=True, timeout=420)
            if r.returncode != 0:
                print(f"  ffmpeg video-segment hata: {r.stderr[-300:]}", file=sys.stderr)
                return False
            return os.path.exists(seg_yol) and os.path.getsize(seg_yol) > 1000
        except Exception as e:
            print(f"  ffmpeg video-segment istisna: {str(e)[:160]}", file=sys.stderr)
            return False
    gorsel = medya
    z, x, y = _zoompan_ifadeleri(sahne, gecis, fps, F)
    vf = (f"scale=2880:1620:force_original_aspect_ratio=increase,crop=2880:1620,"
          f"zoompan=z='{z}':x='{x}':y='{y}':d={F}:s=1920x1080:fps={fps}")
    if gecis in ("anlati", "hizli", "hikaye"):
        vf += ",vignette=angle=PI/5"   # Video.tsx'teki radial-gradient vinyetin karsiligi
    # ── EFEKT KARSILIKLARI (11 Agu 2026) ──
    # grain ve vinyet Efektler.tsx'te TEMEL efekt (her sahnede acik). Hizli motorda
    # karsiligi olmazsa bu isler ya Remotion'a duser (yavas) ya da efekt SESSIZCE
    # kaybolur. ffmpeg'in kendi noise/vignette filtreleri var, bedava.
    _ef = {str(e.get("ad")): float(e.get("siddet") or 1)
           for e in (sahne.get("efektler") or []) if isinstance(e, dict)}
    if "grain" in _ef:
        vf += f",noise=alls={int(6 + 6 * _ef['grain'])}:allf=t+u"
    if "vinyet" in _ef and gecis not in ("anlati", "hizli", "hikaye"):
        vf += ",vignette=angle=PI/5"
    if "siyah-beyaz" in _ef:
        vf += ",hue=s=0"
    if "kontrast-grade" in _ef:
        vf += f",eq=contrast={1 + 0.18 * _ef['kontrast-grade']:.3f}"
    if "sicak-grade" in _ef:
        vf += f",colortemperature=temperature={int(6500 - 700 * _ef['sicak-grade'])}"
    if "soguk-grade" in _ef:
        vf += f",colortemperature=temperature={int(6500 + 900 * _ef['soguk-grade'])}"
    vf += _efekt_ffmpeg(_ef, sure, fps)
    vf += _karartma_dip(sahne, sure)
    vf += _overlay_filtre(sahne, fps, F)
    # ── EDIT KATMANLARI (11 Agu 2026) ──
    # Bu katmanlar sadece Remotion'da cizilebiliyordu, o yuzden katmanli isler hizli
    # motoru ATLIYORDU ve render ~7x gercek zamana cikiyordu (40 dk video = 4 saat).
    # Artik ffmpeg karsiliklari var: 40 dk video ~15 dk.
    vf += _bolum_filtre(sahne, fps, F)
    vf += _alt_band_filtre(sahne, fps, F)
    vf += _etiket_filtre(sahne, fps, F)
    vf += _vurgu_kutu_filtre(sahne, fps, F)
    vf += _kaynak_yazi_filtre(sahne, fps, F)
    vf += ",format=yuv420p"
    komut = ["ffmpeg", "-y", "-loglevel", "error",
             "-loop", "1", "-i", gorsel, "-i", ses,
             "-filter_complex", f"[0:v]{vf}[v]",
             "-map", "[v]", "-map", "1:a",
             # apad: mp3 sureden kisa kalirsa sessizlikle doldur -> concat'ta A/V kaymasi olmaz
             "-af", f"apad=whole_dur={sure:.3f}",
             "-t", f"{sure:.3f}", "-r", str(fps),
             "-c:v", "libx264", "-crf", str(crf), "-preset", "veryfast",
             "-c:a", "aac", "-ar", "44100", "-b:a", "160k",
             seg_yol]
    try:
        r = subprocess.run(komut, capture_output=True, text=True, timeout=420)
        if r.returncode != 0:
            print(f"  ffmpeg segment hata: {r.stderr[-300:]}", file=sys.stderr)
            return False
        return os.path.exists(seg_yol) and os.path.getsize(seg_yol) > 1000
    except Exception as e:
        print(f"  ffmpeg segment istisna: {str(e)[:160]}", file=sys.stderr)
        return False


def ffmpeg_render(is_adi, props, hedef_mp4, ilerle=None):
    """props (Remotion props.json ile ayni sozluk) -> hedef_mp4. Basari: True.
    Kapsam disi durumda/hatada False doner; cagiran Remotion'a duser."""
    def bildir(mesaj, yuzde):
        if ilerle:
            ilerle(mesaj, yuzde)

    sahneler = props.get("sahneler") or []
    if not sahneler:
        return False
    # KAPSAM KONTROLU: video sahneleri artik DESTEKLI (Sora klipleri/footage segment olur).
    # Sadece overlay basligi olan isler Remotion'a gider (kinetik baslik v1'de yok).
    # Overlay engeli KALDIRILDI (4 Agu 2026): drawtext ile ciziliyor.
    # EDIT PAKETI engeli DURUYOR (5 Agu 2026): beyaz-tuval/olcu/alinti/metin/harita
    # sablonlari React+SVG ile ciziliyor (EditPaketi.tsx). ffmpeg'de karsiligi yok —
    # drawtext'le taklidi yarim kalir ve iki motor ayni videoda farkli gorunur.
    # Bu yuzden grafikli is Remotion'a duser (yavas ama DOGRU).
    for s in sahneler:
        if isinstance(s.get("grafik"), dict) and s["grafik"].get("tur"):
            print("  hizli motor: edit paketi grafigi var -> Remotion", file=sys.stderr)
            return False
        # BOLUM BASLIGI da Remotion'a ait (7 Agu 2026). BolumBasligi React bileseni
        # spring animasyonu + kontur + iki katmanli golge kullaniyor; ffmpeg drawtext'te
        # karsiligi yok. Engel OLMAZSA bu isler hizli motorda render edilir ve basliklar
        # SESSIZCE KAYBOLUR — RENDER_MOTOR=ffmpeg varsayilan oldugu icin bu durum
        # belgesel islerinin cogunda yasanirdi.

        # Saha etiketi / cerceve vurgusu da SVG+React ile ciziliyor (nokta+cizgi+yazi,
        # kose isaretli kutu, dash-offset ile cizilen daire). ffmpeg drawtext/drawbox ile
        # taklidi yarim kalir; engel olmazsa etiketler SESSIZCE kaybolur.


    fps = int(props.get("fps", 24))
    gecis = str(props.get("gecis", "sinematik"))
    crf = os.environ.get("RENDER_CRF", "18")
    # 10 cekirdekli sunucuda 8 isci: segment render CPU-agir, 2 cekirdek sisteme kalir
    paralel = max(1, int(os.environ.get("FFMPEG_PARALEL", "8")))

    tmp = tempfile.mkdtemp(prefix=f"hr_{is_adi}_", dir="/tmp")
    try:
        # ── 1) Segmentler PARALEL ──
        bildir(f"Hızlı render: {len(sahneler)} segment ({paralel} paralel)...", 79)
        seg_yollar = {}
        tamam = [0]
        with ThreadPoolExecutor(max_workers=paralel) as havuz:
            # _indeks: cekim bolmede kadraj/ritim secimi sahneye gore degissin diye
            # (deterministik — ayni sahne her uretimde ayni bolunur).
            for i, s in enumerate(sahneler):
                s["_indeks"] = i
                # Karartma imzasi GELEN sahnede duruyor; dip iki tarafli olmali ki
                # gecis simetrik gorunsun (tek tarafli dip yine "carpma" hissi verir).
                if str(s.get("gecisImza") or "") == "karartma":
                    s["_karart_bas"] = True
                    if i > 0:
                        sahneler[i - 1]["_karart_son"] = True
            isler = {havuz.submit(_segment_uret, s, gecis, fps, crf,
                                  os.path.join(tmp, f"seg_{i:04d}.mp4")): i
                     for i, s in enumerate(sahneler)}
            for g in as_completed(isler):
                i = isler[g]
                try:
                    ok = g.result()
                except Exception:
                    ok = False
                if ok:
                    seg_yollar[i] = os.path.join(tmp, f"seg_{i:04d}.mp4")
                tamam[0] += 1
                if tamam[0] % 10 == 0 or tamam[0] == len(sahneler):
                    yuzde = 79 + int(10 * tamam[0] / len(sahneler))
                    bildir(f"Hızlı render: segment {tamam[0]}/{len(sahneler)}", yuzde)
        # Tek segment bile eksikse guvenli yol: Remotion (video butunlugu bozulmasin)
        if len(seg_yollar) != len(sahneler):
            print(f"  hizli motor: {len(sahneler) - len(seg_yollar)} segment uretilemedi -> Remotion",
                  file=sys.stderr)
            return False

        # ── 2) Birlestirme ──
        # CROSSFADE (4 Agu 2026): v1'de sert kesme vardi ve bu yuzden motor kapali
        # duruyordu. Artik xfade ile yumusak gecis var. Cok girdili tek xfade zinciri
        # (132 segment) bellekte sisiyor -> OBEK OBEK zincirlenir, obekler de birbirine
        # xfade ile baglanir. Gecis suresi Remotion'daki ile ayni mantik: en kisa
        # komsu sahnenin yarisini asamaz.
        birlesik = os.path.join(tmp, "birlesik.mp4")
        GECIS_SN = float(os.environ.get("HIZLI_GECIS_SN", "0.4"))

        def _sure(yol):
            try:
                r2 = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                                     "format=duration", "-of", "csv=p=0", yol],
                                    capture_output=True, text=True, timeout=30)
                return float((r2.stdout or "0").strip())
            except Exception:
                return 0.0

        def _xfade_zincir(yollar, cikti, sahne_dilimi=None):
            """Verilen segmentleri xfade ile birlestirir. Tek segment ise kopyalar.
            sahne_dilimi verilirse gecis TURU her sahnenin anlati islevinden secilir."""
            if len(yollar) == 1:
                shutil.copy(yollar[0], cikti)
                return True
            sureler = [_sure(y) for y in yollar]
            if any(d <= 0 for d in sureler):
                return False
            girdi, filt, offset = [], [], 0.0
            son_v, son_a = "0:v", "0:a"
            onceki = ""
            for i, y in enumerate(yollar):
                girdi += ["-i", y]
            for i in range(1, len(yollar)):
                g = min(GECIS_SN, sureler[i - 1] / 2, sureler[i] / 2)
                offset = (offset + sureler[i - 1] - g) if i > 1 else (sureler[0] - g)
                vo, ao = f"v{i}", f"a{i}"
                # GELEN sahnenin IMZASI varsa efekt, yoksa cok kisa fade = sert kesme
                # (xfade zincirinde 0 sureli gecis kurulamaz; 1 kare fade sert kesmedir)
                imza = (str((sahne_dilimi[i] or {}).get("gecisImza") or "")
                        if sahne_dilimi and i < len(sahne_dilimi) else "")
                tur = GECIS_IMZA_FFMPEG.get(imza, "fade")
                if not imza:
                    g = min(g, 1.0 / max(1, fps) * 2)   # 2 kare = gozle sert kesme
                onceki = tur
                filt.append(f"[{son_v}][{i}:v]xfade=transition={tur}:duration={g:.3f}:"
                            f"offset={offset:.3f}[{vo}]")
                filt.append(f"[{son_a}][{i}:a]acrossfade=d={g:.3f}[{ao}]")
                son_v, son_a = vo, ao
            komut = (["ffmpeg", "-y", "-loglevel", "error"] + girdi +
                     ["-filter_complex", ";".join(filt),
                      "-map", f"[{son_v}]", "-map", f"[{son_a}]",
                      "-c:v", "libx264", "-crf", str(crf), "-preset", "veryfast",
                      "-c:a", "aac", "-ar", "44100", "-b:a", "160k", cikti])
            r2 = subprocess.run(komut, capture_output=True, text=True,
                                timeout=int(max(900, sum(sureler) * 4)))
            if r2.returncode != 0:
                print(f"  xfade hata: {r2.stderr[-300:]}", file=sys.stderr)
                return False
            return os.path.exists(cikti) and os.path.getsize(cikti) > 1000

        sirali = [seg_yollar[i] for i in range(len(sahneler))]
        OBEK = max(2, int(os.environ.get("HIZLI_OBEK", "12")))
        bildir("Hızlı render: geçişler ekleniyor...", 90)
        if len(sirali) <= OBEK:
            ok_birlestir = _xfade_zincir(sirali, birlesik, sahneler)
        else:
            obekler = []
            for k in range(0, len(sirali), OBEK):
                oy = os.path.join(tmp, f"obek_{k // OBEK:03d}.mp4")
                # obek icindeki gecisler o obegin sahnelerinden secilir
                if not _xfade_zincir(sirali[k:k + OBEK], oy, sahneler[k:k + OBEK]):
                    ok_birlestir = False
                    break
                obekler.append(oy)
            else:
                # obek SINIRLARI: burada anlati islevi bilinmiyor (obek ortalamasi anlamsiz)
                # -> sade fade. Obek sinirlari 12 sahnede bir, yani nadir.
                ok_birlestir = _xfade_zincir(obekler, birlesik)
        if not ok_birlestir:
            print("  hizli motor: xfade basarisiz -> Remotion", file=sys.stderr)
            return False

        # ── 3) Altyazi (varsa tek gecişte ASS ile gomulur) ──
        stil = str(props.get("altyaziStil", "orta"))
        toplam_sure = sum(float(s.get("sure", 0)) for s in sahneler)
        if stil != "yok":
            ass_yol = os.path.join(tmp, "altyazi.ass")
            adet = _ass_uret(sahneler, props.get("altyaziAyar"), stil, ass_yol)
            if adet > 0:
                bildir("Hızlı render: altyazı gömülüyor...", 92)
                # ass filtresi yol icindeki ozel karakterlere hassas -> tmp yollari guvenli (ascii)
                vf = f"ass={ass_yol}:fontsdir={FONT_DIZIN}"
                r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", birlesik,
                                    "-vf", vf, "-c:v", "libx264", "-crf", str(crf),
                                    "-preset", "veryfast", "-c:a", "copy", hedef_mp4],
                                   capture_output=True, text=True,
                                   timeout=int(max(600, toplam_sure * 3)))
                if r.returncode != 0 or not os.path.exists(hedef_mp4):
                    print(f"  hizli motor altyazi hata: {r.stderr[-300:]}", file=sys.stderr)
                    return False
                return True
        shutil.move(birlesik, hedef_mp4)
        return True
    except Exception as e:
        print(f"  hizli motor istisna: {str(e)[:200]}", file=sys.stderr)
        return False
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
