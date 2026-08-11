#!/usr/bin/env python3
"""DERIN SAGLIK — gercek bagimliliklari OLCER, tahmin etmez.

⚠ NEDEN VAR (Faz H envanteri, 12 Agu 2026): `/api/saglik` yalnizca "hangi
anahtar kurulu" booleanlarini donduruyordu ve icinde `durum`/`status` alani
YOKTU. Arayuz ise `String(v.durum ?? v.status ?? 'ok')` okuyordu — yani alan
yoksa **'ok' varsayiyordu**. Sonuc: ffmpeg silinse, render studyosu kaybolsa,
cikti dizini salt-okunur olsa bile ust barda "Sistem hazir" yaziyordu.

Bu modul bunun tersini yapar: her bilesen GERCEKTEN denenir.

    · ffmpeg / ffprobe   -> `-version` calistirilir
    · render motoru      -> secili motor (ffmpeg | remotion) ve node/studyo
    · yazilabilirlik     -> cikti + gecici + durum dizinine GERCEK dosya yazilir
    · kuyruk/isci        -> isci thread'leri yasiyor mu
    · medya saglayicilari-> anahtar var mi (YETENEK, deger DEGIL)
    · arastirma          -> OPENAI_KEY + modul yuklenebiliyor mu

GENEL DURUM: `hazir` | `kisitli` | `kullanilamiyor`
    kullanilamiyor : KRITIK bir bilesen yok  -> video URETILEMEZ
    kisitli        : kritikler tamam, opsiyoneller eksik -> uretir ama kisitli
    hazir          : hepsi tamam

⚠ ANAHTAR DEGERI ASLA DONMEZ. Yalnizca `true/false` yetenek bilgisi.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time

# Bu bilesenler olmadan video URETILEMEZ. Biri bile eksikse durum
# "kullanilamiyor" olur ve arayuz uretim baslatmayi durust sekilde engeller.
KRITIK = ("ffmpeg", "ffprobe", "cikti_yazilabilir", "gecici_yazilabilir",
          "isci")

_ONBELLEK = {"t": 0.0, "veri": None}
ONBELLEK_SN = float(os.environ.get("SAGLIK_ONBELLEK_SN", "20"))


def _komut_var(ad: str, arg: str = "-version", zaman_asimi: int = 8) -> dict:
    """Komutu GERCEKTEN calistir. `shutil.which` YETMEZ: dosya var olup
    calistirilamayabilir (izin, bozuk kurulum, eksik kutuphane)."""
    yol = shutil.which(ad)
    if not yol:
        return {"ok": False, "detay": "PATH'te bulunamadi"}
    try:
        r = subprocess.run([yol, arg], capture_output=True, text=True,
                           timeout=zaman_asimi)
        if r.returncode != 0:
            return {"ok": False, "yol": yol,
                    "detay": f"cikis kodu {r.returncode}"}
        ilk = (r.stdout or r.stderr or "").strip().splitlines()
        return {"ok": True, "yol": yol,
                "surum": (ilk[0][:80] if ilk else "")}
    except subprocess.TimeoutExpired:
        return {"ok": False, "yol": yol, "detay": "zaman asimi"}
    except Exception as e:
        return {"ok": False, "yol": yol, "detay": f"{type(e).__name__}: {e}"[:120]}


def _yazilabilir(dizin: str) -> dict:
    """Dizine GERCEKTEN dosya yaz. `os.access` yaniltir (NFS, salt-okunur
    bagli birim, dolu disk). Yazip siliyoruz."""
    try:
        os.makedirs(dizin, exist_ok=True)
    except Exception as e:
        return {"ok": False, "yol": dizin,
                "detay": f"olusturulamadi: {type(e).__name__}"}
    try:
        with tempfile.NamedTemporaryFile(dir=dizin, prefix=".saglik_",
                                         delete=True) as f:
            f.write(b"ok")
            f.flush()
    except Exception as e:
        return {"ok": False, "yol": dizin, "detay": f"yazilamadi: {type(e).__name__}"}
    bilgi = {"ok": True, "yol": dizin}
    try:
        k = shutil.disk_usage(dizin)
        bilgi["bos_gb"] = round(k.free / (1024 ** 3), 1)
        # Disk %97'den doluysa render cikti yazamaz — uyari uret.
        if k.free < 2 * 1024 ** 3:
            bilgi["ok"] = False
            bilgi["detay"] = f"disk neredeyse dolu ({bilgi['bos_gb']} GB bos)"
    except Exception:
        pass
    return bilgi


def _render_motoru(pipeline) -> dict:
    """Hangi render motoru secili ve o motor GERCEKTEN kullanilabilir mi."""
    motor = os.environ.get("RENDER_MOTOR", "")
    if not motor:
        try:
            with open(os.path.join(pipeline.KOK_YOL, "RENDER_MOTOR")) as f:
                motor = f.read().strip()
        except Exception:
            motor = ""
    motor = motor or "remotion"
    d = {"motor": motor}
    if motor == "ffmpeg":
        # Hizli motor yalnizca ffmpeg'e ve font dizinine bagli.
        font_dizin = os.path.join(pipeline.PUBLIC, "fonts")
        var = os.path.isdir(font_dizin) and any(
            a.endswith(".ttf") for a in os.listdir(font_dizin)) \
            if os.path.isdir(font_dizin) else False
        d.update({"ok": True, "font_dizini": var,
                  "detay": "" if var else
                  "gomulu font bulunamadi — altyazi varsayilan fontla cizilir"})
        return d
    # Remotion: node + studyo dizini + node_modules gerekir
    node = _komut_var("node", "--version")
    studyo_var = os.path.isdir(pipeline.STUDYO)
    modul_var = os.path.isdir(os.path.join(pipeline.STUDYO, "node_modules"))
    d.update({"ok": bool(node["ok"] and studyo_var and modul_var),
              "node": node["ok"], "node_surum": node.get("surum", ""),
              "studyo": studyo_var, "node_modules": modul_var})
    if not d["ok"]:
        eksik = [a for a, v in (("node", node["ok"]), ("render-studio", studyo_var),
                                ("node_modules", modul_var)) if not v]
        d["detay"] = "eksik: " + ", ".join(eksik)
    return d


def _saglayicilar() -> dict:
    """Medya/AI saglayicilarinin YETENEK durumu. ⚠ DEGER ASLA DONMEZ."""
    import kaynak
    return {
        "openai": bool((os.environ.get("OPENAI_KEY") or "").strip()),
        "gemini": bool((os.environ.get("GEMINI_KEY") or "").strip()),
        "pexels": bool(kaynak.PEXELS_KEY),
        "pixabay": bool(kaynak.PIXABAY_KEY),
        "coverr": bool(kaynak.COVERR_KEY),
        "freepik_anahtar_sayisi": len(kaynak.FREEPIK_KEYS),
    }


def _arastirma() -> dict:
    """Faz A arastirma motoru gercekten kosabilir mi."""
    try:
        import arastirma_kopru
    except Exception as e:
        return {"ok": False, "detay": f"kopru yuklenemedi: {type(e).__name__}"}
    if not arastirma_kopru.ACIK:
        return {"ok": False, "acik": False,
                "detay": "ARASTIRMA_ACIK=0 ile kapatilmis"}
    try:
        from arastirma import fact_checker, researcher    # noqa: F401
    except Exception as e:
        return {"ok": False, "acik": True,
                "detay": f"modul yuklenemedi: {type(e).__name__}"}
    anahtar = bool((os.environ.get("OPENAI_KEY") or "").strip())
    return {"ok": anahtar, "acik": True, "anahtar": anahtar,
            "tavan_usd": arastirma_kopru.TAVAN_USD,
            "detay": "" if anahtar else
            "OPENAI_KEY yok — arastirma calismaz, anlatim yalnizca kullanici "
            "metnine dayanir"}


def derin(pipeline, *, isci_sayisi: int = 0, kuyruk_boyu: int = 0,
          durum_dizini: str = "", gecici_dizin: str = "") -> dict:
    """Tum bilesenleri OLC ve tek bir durum raporu dondur."""
    simdi = time.time()
    if _ONBELLEK["veri"] is not None and simdi - _ONBELLEK["t"] < ONBELLEK_SN:
        return _ONBELLEK["veri"]

    bilesenler = {
        "ffmpeg": _komut_var("ffmpeg"),
        "ffprobe": _komut_var("ffprobe"),
        "cikti_yazilabilir": _yazilabilir(pipeline.CIKTI_DIR),
        "gecici_yazilabilir": _yazilabilir(gecici_dizin or pipeline.CIKTI_DIR),
        "durum_yazilabilir": _yazilabilir(durum_dizini or pipeline.CIKTI_DIR),
        "render": _render_motoru(pipeline),
        "isci": {"ok": isci_sayisi > 0, "isci_sayisi": isci_sayisi,
                 "kuyrukta": kuyruk_boyu,
                 "detay": "" if isci_sayisi > 0 else
                 "kuyruk iscisi yok — is alinsa da islenmez"},
        "arastirma": _arastirma(),
    }

    eksik_kritik = [a for a in KRITIK
                    if not bilesenler.get(a, {}).get("ok", False)]
    # Kritik olmayan ama kaliteyi dusuren eksikler
    eksik_opsiyonel = [a for a, v in bilesenler.items()
                       if a not in KRITIK and not v.get("ok", False)]
    saglayici = _saglayicilar()
    # Belgesel gercek footage'a bagli: hicbir stok saglayici yoksa kisitli.
    if not any((saglayici["pexels"], saglayici["pixabay"], saglayici["coverr"])):
        eksik_opsiyonel.append("stok_medya")

    if eksik_kritik:
        durum = "kullanilamiyor"
        ozet = ("Video üretilemez — kritik bileşen eksik: "
                + ", ".join(eksik_kritik))
    elif eksik_opsiyonel:
        durum = "kisitli"
        ozet = ("Üretim çalışır ama kısıtlı: "
                + ", ".join(sorted(set(eksik_opsiyonel))))
    else:
        durum = "hazir"
        ozet = "Tüm bileşenler çalışıyor."

    veri = {
        "durum": durum,          # hazir | kisitli | kullanilamiyor
        "status": durum,
        "uretim_mumkun": not eksik_kritik,
        "ozet": ozet,
        "eksik_kritik": eksik_kritik,
        "eksik_opsiyonel": sorted(set(eksik_opsiyonel)),
        "bilesenler": bilesenler,
        "saglayicilar": saglayici,
        "olcum_zamani": int(simdi),
    }
    _ONBELLEK.update({"t": simdi, "veri": veri})
    return veri
