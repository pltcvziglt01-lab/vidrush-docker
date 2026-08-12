#!/usr/bin/env python3
"""QA KOPRUSU — render sonrasi kalite kapisini GERCEK uretim hattina baglar.

⚠ NEDEN VAR (Faz H envanteri): `webapp/editor/qa_son.py` Faz C'de yazildi ve
testlerle dogrulandi, ama `pipeline.py` onu HIC cagirmiyordu. Yani uretilen
video hicbir olcumden gecmeden "Hazir!" diye kullaniciya veriliyordu.
Is sozlesmesinde `qa` alani vardi ama HER ZAMAN bos sozlukttu.

Bu modul o boslugu kapatir:
    render bitti -> ffprobe + siyah + donmus + kesme + loudness + sessizlik
                 -> PASS / WARN / FAIL
    FAIL ise is "basarili" GORUNMEZ ve kontrollu bir duzeltme denenir.

⚠ TASARIM KURALLARI
1. QA HATTI COKERTMEZ. Olcum basarisiz olursa video yine teslim edilir ama
   `qa.durum = "OLCULEMEDI"` yazilir — sessizce "PASS" DENMEZ.
2. FAIL SAKLANMAZ. `sonuc["qa"]` + `dususler` + arayuzde kirmizi rozet.
3. KONTROLLU RETRY: yalnizca DETERMINISTIK ve UCRETSIZ duzeltmeler denenir
   (ses yeniden mastering). Yeniden gorsel uretmek gibi PARA HARCAYAN bir
   retry BURADA YAPILMAZ — kullanicinin kredisi sessizce yanmaz.
4. UYDURMA OLCUM YOK. Butun sayilar ffmpeg/ffprobe ciktisindan.
"""
from __future__ import annotations

import os
import subprocess
import sys

# QA acik mi (acil durumda kapatilabilir)
ACIK = os.environ.get("QA_KAPISI", "1").lower() not in ("0", "false", "")
# Olcum icin tavan sure (sn). Uzun videoda ffmpeg taramasi da uzar.
ZAMAN_ASIMI = int(os.environ.get("QA_ZAMAN_ASIMI", "600"))
# Ses hedefleri (OLCUM_BELGESEL.md): -14 LUFS, tepe <= -1.5 dBTP
HEDEF_LUFS = float(os.environ.get("QA_HEDEF_LUFS", "-14.0"))
LUFS_TOLERANS = float(os.environ.get("QA_LUFS_TOLERANS", "1.5"))
HEDEF_TEPE = float(os.environ.get("QA_HEDEF_TEPE", "-1.0"))


def _ses_yeniden_master(video: str) -> tuple:
    """Kontrollu retry: sesi iki gecisli loudnorm ile YENIDEN masterle.

    UCRETSIZ ve DETERMINISTIK — API cagrisi yok, gorsel yeniden uretilmez.
    (ok, mesaj). Basarisizsa orijinal dosyaya DOKUNULMAZ.
    """
    gecici = video + ".qa_fix.mp4"
    try:
        r = subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", video,
             "-af", f"loudnorm=I={HEDEF_LUFS}:TP={HEDEF_TEPE}:LRA=11,"
                    f"alimiter=limit=0.95:level=disabled",
             "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
             gecici],
            capture_output=True, text=True, timeout=ZAMAN_ASIMI)
        if r.returncode == 0 and os.path.getsize(gecici) > 1024:
            os.replace(gecici, video)
            return True, "ses yeniden masterlendi (loudnorm)"
        return False, f"ffmpeg rc={r.returncode}: {r.stderr[-160:]}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"
    finally:
        if os.path.exists(gecici):
            try:
                os.remove(gecici)
            except OSError:
                pass


def _ses_sorunu_mu(sorunlar: list) -> bool:
    """FAIL/WARN'lar arasinda SES kaynakli olan var mi (retry edilebilir)."""
    return any(str(s.get("kod", "")).upper().find("LOUD") >= 0
               or str(s.get("kod", "")).upper().find("SES") >= 0
               or str(s.get("kod", "")).upper().find("TEPE") >= 0
               for s in sorunlar)


def denetle(video_yolu: str, *, beklenen: dict = None, bildir=None,
            retry: bool = True) -> dict:
    """Render sonrasi kalite kapisi. HICBIR DURUMDA istisna firlatmaz.

    Doner: {"durum": PASS|WARN|FAIL|OLCULEMEDI|KAPALI, "olcumler": {...},
            "sorunlar": [...], "retry": {...}}
    """
    if not ACIK:
        return {"durum": "KAPALI", "olcumler": {}, "sorunlar": [],
                "not": "QA_KAPISI=0 ile kapatilmis"}
    if not video_yolu or not os.path.exists(video_yolu):
        return {"durum": "OLCULEMEDI", "olcumler": {}, "sorunlar": [],
                "not": "video dosyasi bulunamadi"}

    try:
        from editor import qa_son
    except Exception as e:
        return {"durum": "OLCULEMEDI", "olcumler": {}, "sorunlar": [],
                "not": f"qa_son yuklenemedi: {type(e).__name__}: {e}"}

    if bildir:
        bildir("Kalite kontrolü (ölçüm)...", 99)
    try:
        q = qa_son.denetle(video_yolu, beklenen=beklenen or {},
                           zaman_asimi=ZAMAN_ASIMI)
        d = q.sozluk()
    except Exception as e:
        print(f"  QA olculemedi: {type(e).__name__}: {e}", file=sys.stderr)
        return {"durum": "OLCULEMEDI", "olcumler": {}, "sorunlar": [],
                "not": f"{type(e).__name__}: {str(e)[:160]}"}

    # ── KONTROLLU RETRY: yalnizca ses sorunlarinda, yalnizca bir kez ──
    if (retry and d.get("durum") == "FAIL"
            and _ses_sorunu_mu(d.get("sorunlar") or [])):
        if bildir:
            bildir("Kalite kapısı: ses yeniden seviyeleniyor...", 99)
        ok, mesaj = _ses_yeniden_master(video_yolu)
        d["retry"] = {"denendi": True, "tur": "ses-remaster",
                      "basarili": ok, "mesaj": mesaj}
        if ok:
            try:
                q2 = qa_son.denetle(video_yolu, beklenen=beklenen or {},
                                    zaman_asimi=ZAMAN_ASIMI)
                d2 = q2.sozluk()
                d2["retry"] = d["retry"]
                d2["retry"]["onceki_durum"] = d.get("durum")
                d = d2
            except Exception as e:
                d["retry"]["mesaj"] += f" (yeniden olcum basarisiz: {e})"
    else:
        d["retry"] = {"denendi": False}

    print(f"  QA: {d.get('durum')} — {len(d.get('sorunlar') or [])} sorun",
          file=sys.stderr)
    return d


def ozet(qa: dict) -> dict:
    """Arayuz icin kucuk ozet — is sozlesmesine bu girer."""
    qa = qa or {}
    o = qa.get("olcumler") or {}
    v = o.get("video") or {}
    ln = o.get("loudness") or {}
    return {
        "durum": qa.get("durum") or "OLCULMEDI",
        "cozunurluk": (f"{v.get('genislik')}x{v.get('yukseklik')}"
                       if v.get("genislik") else ""),
        "fps": v.get("fps"),
        # ⚠ ANAHTAR ADLARI qa_son._ffprobe_ayikla/_loudness_ayikla ile BIREBIR
        # olmali. Ilk surumde "sure"/"I"/"Peak" yazmistim; o adlar yok, sonuc
        # olarak sure ve LUFS arayuzde HEP bos gorunuyordu. Testle kilitli.
        "sure_sn": v.get("sure_sn"),
        "boyut_bayt": v.get("boyut_bayt"),
        "codec": v.get("codec"),
        "lufs": ln.get("lufs"),
        "tepe_dbtp": ln.get("tepe_dbtp"),
        "lra": ln.get("lra"),
        "siyah_aralik": len(o.get("siyah_araliklar") or []),
        "donmus_aralik": len(o.get("donmus_araliklar") or []),
        "kesme_sayisi": o.get("kesme_sayisi"),
        "sorun_sayisi": len(qa.get("sorunlar") or []),
        "sorunlar": [{"kod": s.get("kod"), "seviye": s.get("seviye"),
                      "detay": str(s.get("detay"))[:160]}
                     for s in (qa.get("sorunlar") or [])[:8]],
        "retry": qa.get("retry") or {"denendi": False},
        "not": qa.get("not") or "",
    }


def dususe_cevir(qa: dict) -> list:
    """QA sonucunu GORUNUR dusus kayitlarina cevir (sessiz kalite kaybi yok)."""
    qa = qa or {}
    durum = qa.get("durum")
    if durum in ("PASS", "KAPALI", None):
        return []
    if durum == "OLCULEMEDI":
        return [{"asama": "qa",
                 "neden": qa.get("not") or "olcum yapilamadi",
                 "etki": "Video teslim edildi ama kalite ölçümü YAPILAMADI; "
                         "PASS olduğu varsayılmıyor."}]
    kodlar = ", ".join(str(s.get("kod")) for s in (qa.get("sorunlar") or [])[:5])
    etki = ("Video kalite kapısını GEÇEMEDİ." if durum == "FAIL"
            else "Video kalite kapısını uyarılarla geçti.")
    r = qa.get("retry") or {}
    if r.get("denendi"):
        etki += (f" Kontrollü düzeltme denendi ({r.get('tur')}): "
                 f"{'başarılı' if r.get('basarili') else 'başarısız'}.")
    return [{"asama": "qa", "neden": f"{durum}: {kodlar}", "etki": etki}]
