"""ONIZLEME RENDER'I — render_plan.json'i dogrudan ffmpeg ile videoya cevirir.

⚠ BU MODUL MEVCUT RENDER KODUNU CAGIRMAZ (Faz C siniri). `hizli_render.py`
ve Remotion'a dokunulmuyor; burada onizleme icin BAGIMSIZ, kucuk bir ffmpeg
yolu var. Amaci kalite kanitlamak, uretim hattini degistirmek degil.

KAPSAM DURUSTLUGU: yalnizca `renderer=ffmpeg` olan spec'ler uygulanir.
Remotion gerektiren spec'ler (2.5D parallax, harita, veri grafigi, alinti
karti, maske) UYGULANMAZ ve `atlanan` listesinde RAPORLANIR. Sessiz kayip yok.

Guvenlik: indirme yalnizca `render_kullanilabilir=True` adaylarda, icerik
turu + boyut kapisindan sonra, en fazla `MAKS_VARLIK` adet.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from typing import Callable, Optional

from . import kalite_kapisi as _kk
from . import tipografi as _tg
from .profil import EditProfili, VARSAYILAN

# ⚠ drawtext FONTFILE OLMADAN calismaz (macOS/bazi ffmpeg derlemeleri).
# Onizleme ilk kosusunda "sentetik gorsel uretilemedi" hatasinin sebebi buydu.
# Repodaki STATIK Montserrat Bold kullanilir (degisken font Thin cizer).
def _font_yolu() -> str:
    aday = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)))), "app", "render-studio", "public",
            "fonts", "Montserrat-Bold.ttf"),
        os.path.join(os.environ.get("VIDRUSH_KOK", "/opt/vidrush"),
                     "render-studio", "public", "fonts", "Montserrat-Bold.ttf"),
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for y in aday:
        if os.path.exists(y):
            return y
    return ""


def _fontstr() -> str:
    y = _font_yolu()
    return f"fontfile='{y}':" if y else ""


_DRAWTEXT_ONBELLEK = [None]


def drawtext_var_mi() -> bool:
    """ffmpeg drawtext filtresiyle DERLENMIS mi?

    ⚠ 11 Agu 2026: yerel homebrew ffmpeg libfreetype OLMADAN derlenmis ve
    "Filter not found" ile TUM segmentleri dusurdu. Konteynerdeki ffmpeg'de
    filtre var. Bu yuzden yetenek yoklamasi yapiyoruz: filtre yoksa yazi
    katmanlari SESSIZCE dusmez, `atlanan` listesine yazilir."""
    if _DRAWTEXT_ONBELLEK[0] is None:
        r = _kos(["ffmpeg", "-hide_banner", "-filters"], 30)
        _DRAWTEXT_ONBELLEK[0] = " drawtext" in (r.get("stdout") or "")
    return bool(_DRAWTEXT_ONBELLEK[0])


# ─────────────────── YAZI GEOMETRISI — TEK KAYNAK (Faz I-40) ───────────────
#
# ⚠ NEDEN VAR — I-40'TA OLCULEN AYRISMA:
# Bu modul yazi katmanlarini SABIT sayilarla ciziyordu (`y=h*0.70`,
# `y=h*0.80`, `y=h-th-14`, punto 34/26/15) ve PLANIN KENDI spec'ini
# (`parametre.y_orani`, `parametre.punto`) HIC OKUMUYORDU. Sonuc IKI AYRI
# GEOMETRI: I-39'da bolum basligi 0.60'a, kunye 0.075'e tasindi ama onizleme
# hala 0.70 / ekran DIBI ciziyordu. Bu, I-14'te olculen kusur sinifinin
# aynisi (plan bir sey hesaplar, cizim baskasini cizer) ve I-16'da Remotion
# tarafinda duzeltilen `bottom: 22` kusurunun onizlemedeki ikizi.
#
# Kural: KONUM/PUNTO/HIZALAMA **spec'ten** gelir; spec sessizse
# `tipografi.KONUM` ve profil puntosu kullanilir — bu dosyada UYDURMA SABIT
# TUTULMAZ. Puntolar profil NOMINAL genisliginde uretildigi icin onizleme
# olcusune ORANLA kucultulur.
NOMINAL_GENISLIK = 1920.0
# Yalniz kunye SAGA yaslanir (Remotion `KaynakEtiketi` ile ayni).
SAG_HIZALI = ("source-label",)
# Dikey konumu `y_orani` yerine `y` alaninda tasiyan spec'ler.
_Y_ALAN = ("y_orani", "y")


def _profil_punto(ad: str, p: EditProfili) -> float:
    t = p.tipografi
    return {"chapter-title": t.bolum_basligi, "lower-third": t.alt_band_baslik,
            "source-label": t.kaynak_etiketi, "callout": t.callout,
            "quote-card": t.alt_band_baslik}.get(ad, t.callout)


def yazi_yerlesimi(ad: str, prm, *, gen: float, yuk: float,
                   p: Optional[EditProfili] = None) -> dict:
    """Onizleme yazi katmaninin punto/x/y'si. Saf; ISTISNA FIRLATMAZ.

    ⚠ TEK KAYNAK: deger once PLANIN spec'inden, sonra `tipografi.KONUM` ve
    profil puntosundan gelir. Bu dosyada ikinci bir aritmetik yoktur.

    ⚠ Kunye guvenli kenari ZORLAR — Remotion `KaynakEtiketi` ile birebir ayni
    hesap: `min(y*yuk, yuk - guvenli_kenar - punto * SATIR_KUTU_ORANI)`.
    """
    p = p or VARSAYILAN
    prm = prm if isinstance(prm, dict) else {}
    ad = str(ad or "")
    g = _kk._sayi(gen, NOMINAL_GENISLIK)
    y_kare = _kk._sayi(yuk, 1080.0)
    olcek = max(0.05, (g / NOMINAL_GENISLIK) if g > 0 else 1.0)

    punto = max(8, int(round(_kk._sayi(prm.get("punto"),
                                       _profil_punto(ad, p)) * olcek)))
    y_orani = None
    for alan in _Y_ALAN:
        if alan in prm:
            d = _kk._sayi(prm.get(alan), -1.0)
            if 0.0 <= d <= 1.0:
                y_orani = d
                break
    if y_orani is None:
        y_orani = _kk._sayi(_tg.KONUM.get(ad), 0.78)

    sag = ad in SAG_HIZALI
    guvenli = p.tipografi.guvenli_kenar * olcek
    if ad == "callout":
        # callout `x`i ORAN tasir (0..1), izgara noktasi degil.
        x_px = int(round(min(max(_kk._sayi(prm.get("x"), 0.6), 0.0), 1.0) * g))
    else:
        x_px = int(round(_kk._sayi(prm.get("x"), p.tipografi.izgara_x) * olcek))

    y_px = y_orani * y_kare
    tavan = y_kare - guvenli - punto * _kk.SATIR_KUTU_ORANI
    kirpildi = bool(sag and y_px > tavan)
    if kirpildi:
        y_px = tavan
    return {"ad": ad, "punto": punto, "x_px": x_px,
            "y_orani": round(y_orani, 6), "y_px": round(y_px, 3),
            "dolgu": max(2, int(round(punto * _kk.DOLGU_ORANI))),
            "sag_hizali": sag, "guvenli_kenar_px": round(guvenli, 3),
            "tavan_px": round(tavan, 3), "kirpildi": kirpildi,
            "olcek": round(olcek, 6)}


MAKS_VARLIK = 3
MAKS_BAYT = 80 * 1024 * 1024          # varlik basina 80 MB (kullanici siniri)
ONIZLEME_TAVAN_SN = 30.0


def _kos(komut: list, zaman_asimi: int = 300) -> dict:
    try:
        r = subprocess.run(komut, capture_output=True, text=True,
                           timeout=zaman_asimi)
        return {"rc": r.returncode, "stdout": r.stdout or "",
                "stderr": r.stderr or ""}
    except Exception as e:
        return {"rc": -1, "stdout": "", "stderr": str(e)[:300]}


def _kacir(t: str) -> str:
    """ffmpeg drawtext kacirma. VIRGUL SILINMEZ, KACIRILIR (11 Agu: '400,000 DWT'
    ekranda '400000 DWT' cikiyordu)."""
    return (str(t).replace("\\", "").replace(":", "\\:").replace("'", "")
            .replace("%", "\\%").replace(",", "\\,"))


def varlik_indir(adaylar: list, hedef_dizin: str, *,
                 guvenlik_modulu=None, indirici: Optional[Callable] = None,
                 maks: int = MAKS_VARLIK) -> tuple:
    """En fazla `maks` LISANSLI varligi indir. Doner (indirilenler, rapor).

    Lisans duvarindan gecmeyen aday ASLA indirilmez.
    """
    import requests

    rapor, indirilen = [], []
    os.makedirs(hedef_dizin, exist_ok=True)
    uygun = [a for a in adaylar if a.get("render_kullanilabilir")
             and a.get("indirme_url")]
    for a in uygun:
        if len(indirilen) >= maks:
            break
        url = a["indirme_url"]
        # ── GUVENLIK KAPISI ──
        if guvenlik_modulu is not None:
            try:
                guvenlik_modulu.url_dogrula(url)
            except Exception as e:
                rapor.append({"asset_id": a["asset_id"], "karar": "reddedildi",
                              "sebep": f"guvenlik: {str(e)[:70]}"})
                continue
        try:
            fn = indirici or requests.get
            r = fn(url, timeout=60, stream=True,
                   headers={"User-Agent": "BedosahoAI/1.0 (preview)"})
            if getattr(r, "status_code", 0) != 200:
                rapor.append({"asset_id": a["asset_id"], "karar": "basarisiz",
                              "sebep": f"HTTP {getattr(r, 'status_code', '?')}"})
                continue
            tur = str(r.headers.get("Content-Type", "")).lower()
            if guvenlik_modulu is not None:
                ok, sebep = guvenlik_modulu.icerik_kapisi(
                    tur, r.headers.get("Content-Length"))
                if not ok:
                    rapor.append({"asset_id": a["asset_id"], "karar": "reddedildi",
                                  "sebep": sebep})
                    continue
            uzanti = ".mp4" if "video" in tur else (
                ".jpg" if "jpeg" in tur else (".png" if "png" in tur else ".bin"))
            yol = os.path.join(hedef_dizin, f"{a['asset_id']}{uzanti}")
            toplam = 0
            with open(yol, "wb") as f:
                for parca in r.iter_content(1 << 16):
                    if not parca:
                        continue
                    toplam += len(parca)
                    if toplam > MAKS_BAYT:
                        rapor.append({"asset_id": a["asset_id"],
                                      "karar": "reddedildi",
                                      "sebep": f"boyut tavani {MAKS_BAYT} asildi"})
                        f.close()
                        os.remove(yol)
                        yol = ""
                        break
                    f.write(parca)
            if not yol or not os.path.exists(yol):
                continue
            a["yerel_yol"] = yol
            a["indirme_durumu"] = "indirildi"
            indirilen.append(a)
            rapor.append({"asset_id": a["asset_id"], "karar": "indirildi",
                          "bayt": toplam, "tur": tur,
                          "lisans": a.get("lisans")})
        except Exception as e:
            rapor.append({"asset_id": a["asset_id"], "karar": "basarisiz",
                          "sebep": str(e)[:80]})
    return indirilen, rapor


def sentetik_gorsel(yol: str, renk: str, metin: str, olcu: str = "1280x720") -> bool:
    """Lisansli varlik yoksa SENTETIK test goruntusu. Durustluk: bunun
    sentetik oldugu raporda acikca yazilir."""
    vf = (f"drawtext={_fontstr()}text='{_kacir(metin)}':fontcolor=white@0.35:"
          f"fontsize=44:x=(w-tw)/2:y=(h-th)/2") if drawtext_var_mi() else \
         "drawbox=x=iw*0.42:y=ih*0.47:w=iw*0.16:h=6:color=white@0.3:t=fill"
    r = _kos(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "lavfi",
              "-i", f"color=c={renk}:s={olcu}", "-vf", vf,
              "-frames:v", "1", yol])
    return r["rc"] == 0 and os.path.exists(yol)


def _segment_filtresi(sahne: dict, sure: float, fps: int, yuk: int,
                      gen: int) -> tuple:
    """Sahnenin ffmpeg filtre zinciri + atlanan spec listesi."""
    atlanan = []
    vf = [f"scale={gen}:{yuk}:force_original_aspect_ratio=increase",
          f"crop={gen}:{yuk}", f"fps={fps}"]
    kare = max(1, int(round(sure * fps)))

    for sp in (sahne.get("motion") or []):
        ad = sp.get("ad", "")
        prm = sp.get("parametre") or {}
        if sp.get("renderer") != "ffmpeg":
            atlanan.append({"beat_id": sp.get("beat_id"), "spec": ad,
                            "sebep": "renderer=remotion",
                            "fallback": (sp.get("fallback") or {}).get("ad")})
            continue
        if ad in ("push-in", "pull-out", "pan-right", "pan-left", "slow-drift",
                  "static", "handheld"):
            z = prm.get("zoom") or [1.0, 1.0]
            z0, z1 = float(z[0]), float(z[-1])
            if abs(z1 - z0) > 0.001:
                vf.append(f"zoompan=z='{z0:.4f}+({z1 - z0:.4f})*on/{kare}':"
                          f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                          f"d=1:s={gen}x{yuk}:fps={fps}")
            elif z0 > 1.001:
                vf.append(f"scale=iw*{z0:.3f}:ih*{z0:.3f},crop={gen}:{yuk}")
        elif ad == "grain":
            vf.append(f"noise=alls={int(4 + 8 * float(prm.get('siddet') or 0.35))}"
                      f":allf=t+u")
        elif ad == "vignette":
            vf.append("vignette=angle=PI/5")
        elif ad == "grade":
            prof = str(prm.get("profil") or "")
            if "soguk" in prof:
                vf.append("colortemperature=temperature=7200")
            if "kontrast" in prof:
                vf.append("eq=contrast=1.12")
        elif ad in ("chapter-title", "lower-third", "source-label", "callout") \
                and not drawtext_var_mi():
            atlanan.append({"beat_id": sp.get("beat_id"), "spec": ad,
                            "sebep": "ffmpeg drawtext filtresi YOK "
                                     "(libfreetype olmadan derlenmis)"})
            continue
        elif ad in ("chapter-title", "lower-third"):
            # ⚠ I-40: punto/x/y artik SPEC'ten geliyor (sabit 34/26/0.70/0.80
            # DEGIL). Bant dolgusu da Grafikler.tsx'in `DOLGU_ORANI`si.
            yer = yazi_yerlesimi(ad, prm, gen=gen, yuk=yuk)
            vf.append(_bant_yazi(
                prm.get("metin" if ad == "chapter-title" else "baslik", ""),
                yer, sure))
        elif ad == "source-label":
            # ⚠ I-40: `y=h-th-14` SABITI KALDIRILDI. O sabit planin hesabini
            # HIC okumuyordu ve guvenli kenarin DISINDA kaliyordu — I-16'da
            # Remotion'da duzeltilen `bottom: 22` kusurunun ikizi.
            m = _kacir(str(prm.get("metin", ""))[:40])
            if m:
                yer = yazi_yerlesimi(ad, prm, gen=gen, yuk=yuk)
                vf.append(f"drawtext={_fontstr()}text='{m}':"
                          f"fontcolor=white@0.62:fontsize={yer['punto']}:"
                          f"x=w-tw-{int(round(yer['guvenli_kenar_px']))}:"
                          f"y=h*{yer['y_orani']:.3f}:"
                          f"borderw=2:bordercolor=black@0.5")
        elif ad == "callout":
            m = _kacir(str(prm.get("metin", ""))[:26])
            if m:
                yer = yazi_yerlesimi(ad, prm, gen=gen, yuk=yuk)
                vf.append(f"drawtext={_fontstr()}text='{m}':"
                          f"fontcolor=white:fontsize={yer['punto']}:"
                          f"x={yer['x_px']}:y=h*{yer['y_orani']:.3f}:"
                          f"box=1:boxcolor=black@0.62:"
                          f"boxborderw={yer['dolgu']}")
        elif prm.get("tur") in ("hard-cut", "j-cut", "l-cut", "crossfade",
                                "karartma", "flash"):
            pass                      # gecisler concat asamasinda
        else:
            atlanan.append({"beat_id": sp.get("beat_id"), "spec": ad,
                            "sebep": "onizleme yolunda uygulanmiyor"})
    vf.append("format=yuv420p")
    return ",".join(vf), atlanan


def _bant_yazi(metin: str, yer: dict, sure: float) -> str:
    """Kontrast banti + kalin yazi. drawtext'in kendi box'i kullaniliyor —
    drawbox'un w/h ifadelerinde 't' YOK (11 Agu tuzagi).

    ⚠ I-40: punto/x/y ve bant dolgusu artik ARGUMAN DEGIL, `yazi_yerlesimi`
    sozlugu — yani PLANIN spec'i. Onceki surumde bu fonksiyona SABIT sayilar
    (34/26 punto, 0.70/0.80 oran, x=66, dolgu 14) geciriliyordu.
    """
    m = _kacir(str(metin or "")[:44])
    if not m:
        return "null"
    return (f"drawtext={_fontstr()}text='{m}':fontcolor=white:"
            f"fontsize={yer['punto']}:x={yer['x_px']}:"
            f"y=h*{yer['y_orani']:.3f}:box=1:boxcolor=black@0.62:"
            f"boxborderw={yer['dolgu']}:"
            f"enable='between(t\\,0.15\\,{max(0.6, sure - 0.1):.2f})'")


def onizleme_uret(render_plan: dict, *, cikti: str, calisma_dizin: str,
                  varlik_haritasi: dict, tavan_sn: float = ONIZLEME_TAVAN_SN,
                  fps: int = 30, gen: int = 1280, yuk: int = 720) -> dict:
    """render_plan -> 720p onizleme mp4. Doner rapor sozlugu."""
    os.makedirs(calisma_dizin, exist_ok=True)
    rapor = {"segment": [], "atlanan_spec": [], "hata": [],
             "sure_sn": 0.0, "sahne": 0, "sentetik_kullanildi": False}
    segmentler = []
    t_toplam = 0.0

    for sh in (render_plan.get("sahneler") or []):
        if t_toplam >= tavan_sn:
            break
        sure = min(float(sh.get("sure_sn") or 0), tavan_sn - t_toplam)
        if sure < 0.4:
            continue
        kaynak = varlik_haritasi.get(sh.get("asset_id") or "")
        sentetik = False
        if not kaynak or not os.path.exists(kaynak):
            kaynak = os.path.join(calisma_dizin, f"sent_{sh['beat_id']}.png")
            renk = ["0x14181D", "0x1B2128", "0x0E1013", "0x202832"][
                len(segmentler) % 4]
            if not sentetik_gorsel(kaynak, renk,
                                   f"{sh.get('cekim_turu','')} / "
                                   f"{sh.get('islev','')}", f"{gen}x{yuk}"):
                rapor["hata"].append(f"{sh['beat_id']}: sentetik gorsel uretilemedi")
                continue
            sentetik = True
            rapor["sentetik_kullanildi"] = True

        vf, atlanan = _segment_filtresi(sh, sure, fps, yuk, gen)
        rapor["atlanan_spec"].extend(atlanan)
        seg = os.path.join(calisma_dizin, f"seg_{len(segmentler):03d}.mp4")
        video_mu = str(kaynak).lower().endswith((".mp4", ".webm", ".mov", ".mkv"))
        giris = (["-stream_loop", "-1", "-t", f"{sure:.3f}", "-i", kaynak]
                 if video_mu else ["-loop", "1", "-t", f"{sure:.3f}", "-i", kaynak])
        r = _kos(["ffmpeg", "-nostdin", "-loglevel", "error", "-y"] + giris +
                 ["-vf", vf, "-r", str(fps), "-an",
                  "-c:v", "libx264", "-crf", "20", "-preset", "veryfast",
                  "-pix_fmt", "yuv420p", seg], 300)
        if r["rc"] != 0 or not os.path.exists(seg):
            rapor["hata"].append(f"{sh['beat_id']}: {r['stderr'][-160:]}")
            continue
        segmentler.append(seg)
        rapor["segment"].append({"beat_id": sh["beat_id"], "sure": round(sure, 2),
                                 "cekim": sh.get("cekim_turu"),
                                 "hareket": sh.get("hareket"),
                                 "kaynak": "sentetik" if sentetik else "lisansli",
                                 "asset_id": sh.get("asset_id") or ""})
        t_toplam += sure

    if not segmentler:
        rapor["hata"].append("hicbir segment uretilemedi")
        return rapor

    # ── CONCAT (sert kesme; gecis efektleri onizlemede uygulanmiyor) ──
    liste = os.path.join(calisma_dizin, "liste.txt")
    with open(liste, "w") as f:
        for s in segmentler:
            f.write(f"file '{s}'\n")
    sessiz = os.path.join(calisma_dizin, "bed.wav")
    # Ambience yatagi: anlatim YOK (ucretli TTS kullanilmiyor). Loudness
    # olcumunun anlamli olmasi icin -30 dB pembe gurultu.
    _kos(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "lavfi",
          "-i", f"anoisesrc=color=pink:amplitude=0.03:d={t_toplam:.2f}",
          "-ar", "48000", "-ac", "2", sessiz])
    ham = os.path.join(calisma_dizin, "ham.mp4")
    r = _kos(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "concat",
              "-safe", "0", "-i", liste, "-i", sessiz,
              "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
              "-shortest", ham], 300)
    if r["rc"] != 0:
        rapor["hata"].append(f"concat: {r['stderr'][-200:]}")
        return rapor

    # ── SES MASTERING (Faz C ses plani zinciri) ──
    zincir = ("highpass=f=80,acompressor=threshold=-18dB:ratio=3:attack=8:"
              "release=140:makeup=2,loudnorm=I=-14:TP=-1.0:LRA=11,"
              "alimiter=limit=0.95:level=disabled")
    r2 = _kos(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", ham,
               "-af", zincir, "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
               cikti], 300)
    if r2["rc"] != 0:
        shutil.copy(ham, cikti)
        rapor["hata"].append(f"ses mastering basarisiz, ham kopyalandi: "
                             f"{r2['stderr'][-140:]}")
    rapor["sure_sn"] = round(t_toplam, 2)
    rapor["sahne"] = len(segmentler)
    rapor["cikti"] = cikti
    return rapor
