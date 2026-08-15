#!/usr/bin/env python3
"""FAZ UI-8 — VIDEO-ONLY AKISTA SURE + SORGU + MAGNIFIC + FPS.

⚠ OLCULEN KUSURLAR (gercek 120 sn staging isi job_1786783360170_ui7114_9c21aa,
UI-7 sonrasi). UI-7 hedefini TUTTURDU:
    RENDER-QA (gercek timeline): sahne=11 kapsam=1.0 gercek_video=1.0
ama cikti KABUL EDILEMEDI:

1. `UI8-TURKCE-SORGU`  — kapinin sorgu fallback'i TURKCE.
   `UI7-GORSEL-YASAK-KAPISI` `footage_sorgu` bossa `s["anlatim"]`e dusuyordu;
   o metin TURKCE. Pexels Turkce sorguyu karsilamiyor -> arama BOS donuyor.
   Olcum: `UI-7 kapisi gercek klip buldu` 0 kez, `MEDYA-VIDEO-YOK` 6 kez
   (sahne 1,2,6,9,12,13). Oysa plan sozlesmesi `footage_sorgu` icin
   "specific ENGLISH stock-footage query" diyor ve `scene_prompt` de
   INGILIZCE uretiliyor.

2. `UI8-SURE-KORUNMUYOR` — 6 sahne dusunce video 120 sn yerine 71.15 sn
   oldu (17 sahne planlandi, 11 kaldi). Video-only akista sahne dusmesi
   sureyi DETERMINISTIK olarak kisaltiyordu.

3. `UI8-MAGNIFIC-OTOMATIK-CAGRI` — is sirasinda otomatik upscale denendi:
       magnific POST 502: {"message":"Error consuming credits"}
       magnific: kredi yok (Freepik) -> bu is boyunca devre disi
   Kredi harcanmadi ama KREDI DENEMESI yapildi; video-only akista Magnific
   HIC cagrilmamalidir.

4. `UI8-FPS-UYUSMAZLIGI` — render 24 fps uretiyor, POST-QA profili 30 fps
   bekliyor: `POST-FPS warn: 24.0 fps, beklenen 30.0`. Tam PASS imkansiz.

Kosum: .venv-test/bin/python3 webapp/testler/test_faz_ui8.py
"""
from __future__ import annotations

import os
import re
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)

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


with open(os.path.join(KOK, "pipeline.py"), encoding="utf-8") as f:
    _P = f.read()

# UI-7 kapisinin govdesi
_i = _P.find("UI7-GORSEL-YASAK-KAPISI")
# ⚠ Pencere kapinin TAMAMINI kapsamali: sorgu turetme + yedekler + tekrar +
# UI-8 yeniden kullanim blogu + MEDYA-VIDEO-YOK cikisi.
_KAPI = _P[max(0, _i - 900):_i + 7000] if _i >= 0 else ""


blok("UI-8/1 — KAPI SORGUSU INGILIZCE (turkce anlatim KULLANILMAZ)")

kontrol("kapi govdesi bulundu", bool(_KAPI))
kontrol("kapi `scene_prompt` (INGILIZCE) kullaniyor",
        "scene_prompt" in _KAPI,
        "ingilizce sorgu kaynagi yok")
kontrol("kapi TURKCE `anlatim`i sorgu olarak KULLANMIYOR",
        not re.search(r'_sorgu\s*=\s*\([^)]*s\.get\("anlatim"\)', _KAPI),
        "turkce anlatim hala sorgu fallback'i")
kontrol("stabil kod: UI8-TURKCE-SORGU-YOK belgelendi",
        "UI8-TURKCE-SORGU" in _P,
        "karar kodda belgelenmemis")


blok("UI-8/2 — SURE DETERMINISTIK KORUNUR (sahne dusmez)")

kontrol("stabil kod: UI8-SURE-KORUNDU",
        "UI8-SURE-KORUNDU" in _P,
        "sure koruma yolu yok")
kontrol("son care: bu iste INDIRILMIS gercek klip YENIDEN KULLANILIR",
        ("sahne_*.mp4" in _KAPI or "sahne_" in _KAPI) and "glob" in _KAPI,
        "yeniden kullanim yolu yok")
kontrol("yeniden kullanim DETERMINISTIK (modulo secim)",
        re.search(r"%\s*len\(_mevcut\)", _KAPI) is not None,
        "secim deterministik degil")
kontrol("yeniden kullanimda PROVENANS/lisans tasiniyor",
        "stok_provenans" in _KAPI,
        "lisans kaydi tasinmiyor")
kontrol("MEDYA-VIDEO-YOK ARTIK yalnizca HIC klip yoksa "
        "(yeniden kullanim denemesinden SONRA)",
        re.search(r"if _mevcut:[\s\S]{0,2600}MEDYA_VIDEO_YOK", _KAPI)
        is not None,
        "klip varken de sahne dusuyor")


blok("UI-8/3 — VIDEO-ONLY AKISTA MAGNIFIC CAGRISI YOK")

kontrol("stabil kod: UI8-MAGNIFIC-KAPALI",
        "UI8-MAGNIFIC-KAPALI" in _P,
        "magnific kapatma karari belgelenmemis")
# Her iki magnific cagrisi da gorsel_yasak kontrolu ile korunmali
_mag = [m.start() for m in re.finditer(r"kaynak\.magnific_upscale\(", _P)]
kontrol("magnific cagri noktalari bulundu (2)", len(_mag) == 2, str(len(_mag)))
for _k, _pos in enumerate(_mag, 1):
    _onc = _P[max(0, _pos - 700):_pos]
    kontrol(f"magnific cagri {_k}: gorsel_yasak korumasi VAR",
            'gorsel_yasak' in _onc,
            "video-only akista da cagriliyor")


blok("UI-8/4 — FPS 30'A SABIT")

kontrol("render fps varsayilani 30",
        re.search(r'os\.environ\.get\("VIDEO_FPS",\s*"30"\)', _P) is not None,
        "hala 24")
kontrol("stabil kod: UI8-FPS-30",
        "UI8-FPS-30" in _P,
        "karar belgelenmemis")


blok("UI-8/5 — GERILEME YOK")

kontrol("GERILEME YOK: UI-7 kapisi duruyor",
        "UI7-GORSEL-YASAK-KAPISI" in _P)
kontrol("GERILEME YOK: %100 video profilleri duruyor",
        _P.count('"footage_pct": 100') >= 5
        and _P.count('"gorsel_yasak": True') >= 5)
kontrol("GERILEME YOK: MEDYA-VIDEO-YOK stabil kodu duruyor",
        "MEDYA-VIDEO-YOK" in _P)
kontrol("GERILEME YOK: UI-6 tani kodlari duruyor",
        "SAHNE-YOK-MEDYA-VE-TTS" in _P and "SAHNE-YOK-KESISIM" in _P)
kontrol("GERILEME YOK: kaynak tavani (<=8 sn) duruyor",
        "_kaynak_tavani_uygula" in _P)
kontrol("GERILEME YOK: AI gorsele dusme metni geri gelmedi",
        "AI gorsele mecbur" not in _P)
kontrol("GERILEME YOK: 1920x1080 kompozisyon sabit",
        '"genislik": 1920, "yukseklik": 1080' in _P)

import medya_kapisi as mk                                   # noqa: E402
kontrol("GERILEME YOK: UI-7 dar tarihsel tani duruyor",
        mk.tarihsel_mi("historic peninsula") is False
        and mk.tarihsel_mi("historic footage") is True)

print(f"\n{'=' * 60}")
print(f"GECEN: {gecen}   BASARISIZ: {len(basarisiz)}")
for b in basarisiz:
    print(f"  XX {b}")
sys.exit(1 if basarisiz else 0)
