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

STUDYO = "/opt/vidrush/render-studio"
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
GECIS_IMZA_FFMPEG = {
    "karartma": "fadeblack",
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


def _alt_band_filtre(sahne, fps, F):
    """Alt band (lower third) — Video.tsx'teki AltBand'in ffmpeg karsiligi.
    OLCULEN degerler: en yaygin yazi turu (%33), omur 4.7 sn, giris 0.28 sn.
    Sol kenardaki sari dikey cubuk drawbox ile, yazi drawtext ile."""
    ab = sahne.get("altBand")
    if not isinstance(ab, dict) or not str(ab.get("baslik") or "").strip():
        return ""
    b = _ffmpeg_kacir(str(ab["baslik"]).strip()[:34])
    a = _ffmpeg_kacir(str(ab.get("alt") or "").strip()[:40])
    gir, omur = 0.28, min(4.7, max(1.0, F / fps - 0.4))
    son = 0.3 + omur
    # alpha: 0.3'te girer, omur boyunca kalir, 0.28 sn'de soner
    alfa = (f"if(lt(t\\,0.3)\\,0\\,if(lt(t\\,{0.3 + gir:.2f})\\,(t-0.3)/{gir:.2f}\\,"
            f"if(lt(t\\,{son:.2f})\\,1\\,max(0\\,({son + gir:.2f}-t)/{gir:.2f}))))")
    f = ""
    # Sari dikey vurgu cubugu (AltBand'deki 6px'lik cubuk)
    f += (f",drawbox=x=100:y=ih*0.78:w=6:h=76:color=#F5E14B@1:t=fill:"
          f"enable='between(t\\,0.3\\,{son + gir:.2f})'")
    f += (f",drawtext={_font()}text='{b}':fontcolor=white:fontsize=44:"
          f"borderw=4:bordercolor=black@0.8:shadowcolor=black@0.9:shadowx=0:shadowy=3:"
          f"x=122:y=h*0.78:alpha='{alfa}'")
    if a:
        f += (f",drawtext={_font()}text='{a}':fontcolor=white@0.9:fontsize=26:"
              f"borderw=3:bordercolor=black@0.8:shadowcolor=black@0.9:shadowx=0:shadowy=2:"
              f"x=122:y=h*0.78+52:alpha='{alfa}'")
    return f


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
    """Bolum basligi — BolumBasligi'nin ffmpeg karsiligi.
    ust: sol ust 46px cumle duzeni | orta: ortali 68px BUYUK HARF."""
    b = str(sahne.get("bolum") or "").strip()
    if not b:
        return ""
    yer = str(sahne.get("bolumYeri") or "orta")
    metin = _ffmpeg_kacir(b.upper() if yer == "orta" else b)
    gir, omur = 0.28, 4.5
    son = 0.2 + omur
    alfa = (f"if(lt(t\\,0.2)\\,0\\,if(lt(t\\,{0.2 + gir:.2f})\\,(t-0.2)/{gir:.2f}\\,"
            f"if(lt(t\\,{son:.2f})\\,1\\,max(0\\,({son + gir:.2f}-t)/{gir:.2f}))))")
    if yer == "ust":
        return (f",drawtext={_font()}text='{metin}':fontcolor=white:fontsize=46:"
                f"borderw=4:bordercolor=black@0.8:shadowcolor=black@0.9:shadowx=0:shadowy=4:"
                f"x=w*0.032:y=h*0.044:alpha='{alfa}'")
    return (f",drawtext={_font()}text='{metin}':fontcolor=white:fontsize=68:"
            f"borderw=3:bordercolor=black@0.62:shadowcolor=black@0.85:shadowx=0:shadowy=6:"
            f"x=(w-text_w)/2:y=h*0.52:alpha='{alfa}'")


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
        vf = ((f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,"
               f"fps={fps}") + _overlay_filtre(sahne, fps, F)
              + _bolum_filtre(sahne, fps, F) + _alt_band_filtre(sahne, fps, F)
              + _etiket_filtre(sahne, fps, F) + _vurgu_kutu_filtre(sahne, fps, F)
              + ",format=yuv420p")
        komut = ["ffmpeg", "-y", "-loglevel", "error",
                 "-stream_loop", "-1", "-i", medya, "-i", ses,
                 "-filter_complex", f"[0:v]{vf}[v]",
                 "-map", "[v]", "-map", "1:a",
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
    vf += _overlay_filtre(sahne, fps, F)
    # ── EDIT KATMANLARI (11 Agu 2026) ──
    # Bu katmanlar sadece Remotion'da cizilebiliyordu, o yuzden katmanli isler hizli
    # motoru ATLIYORDU ve render ~7x gercek zamana cikiyordu (40 dk video = 4 saat).
    # Artik ffmpeg karsiliklari var: 40 dk video ~15 dk.
    vf += _bolum_filtre(sahne, fps, F)
    vf += _alt_band_filtre(sahne, fps, F)
    vf += _etiket_filtre(sahne, fps, F)
    vf += _vurgu_kutu_filtre(sahne, fps, F)
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
