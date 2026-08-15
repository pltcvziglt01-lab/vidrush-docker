#!/usr/bin/env python3
"""FAZ Y-5 — KLIP YENIDEN KULLANIMI KALDIRILDI (GLOBAL <=8 sn TAVANI).

⚠ OLCULEN KUSUR (`Y5-YENIDEN-KULLANIM-TAVANI-DELIYOR`):
UI-8'de eklenen `UI8-SURE-KORUNDU` yolu, video bulunamayan sahne icin BU
ISTE ZATEN INDIRILMIS bir klibi kopyaliyordu. Amac sureyi korumakti; ama
bu yol GLOBAL "ayni kaynak <= 8 sn" sozlesmesini MATEMATIKSEL OLARAK
ihlal ediyor:

  · `KAYNAK_BASINA_TAVAN_SN = 8.0` (medya/saglayici_motoru.py)
  · belgesel sahne suresi ~5.5-7 sn (EDIT_STILLERI `sahne_sn`)
  · ayni klip IKI sahnede kullanilirsa toplam ~11-14 sn > 8 sn

⚠ Tavan UYGULAMASI zaten SAHNE BAZINDA: `_kaynak_tavani_uygula` her
sahnenin KENDI suresine bakip boluyor; sahneler arasi kullanim
akumulatoru YOK. Gercek global mantik `kaynak_tavani.bolme_plani`
icinde ama uretimde HIC CAGRILMIYOR (olu kod). Global ihlali yalnizca
`gercek_qa` post-hoc yakaliyor (`GERCEK-KAYNAK-TAVANI` fail) — yani
yeniden kullanim, isi QA'da FAIL'e dusuren bir tuzak.

⚠ IKINCI KUSUR (`Y5-PROVENANS-URL-KAYBI`): yeniden kullanim yolunda
provenans `_pv.get("url")` ile okunuyordu; `stok_provenans_al` sozlugunde
boyle bir anahtar YOK — dogrusu `orijinal_url`. Kaynak URL'i her seferinde
bos yaziliyordu (sessiz veri kaybi; hicbir kapi otmuyordu).

⚠ OLCUM: yeniden kullanim yolu son IKI gercek iste HIC devreye girmedi
(`UI8-SURE-KORUNDU` sayaci 0; footage 17/17 ve 12/12). UI-8'in INGILIZCE
sorgu duzeltmesi sahneleri zaten kurtariyor. Yani bu yol fayda
saglamadan risk tasiyordu — KALDIRILDI.

⚠ SONUC: gercek video bulunamayan sahne `MEDYA-VIDEO-YOK` ile BOS kalir
(AI/statik gorsele DUSULMEZ). Sure kisalirsa bu GORUNUR olur; sessizce
tavan delinmez.

Kosum: .venv-test/bin/python3 webapp/testler/test_faz_y5.py
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

_i = _P.find("UI7-GORSEL-YASAK-KAPISI")
_KAPI = _P[max(0, _i - 900):_i + 7000] if _i >= 0 else ""


blok("Y-5/1 — KLIP YENIDEN KULLANIMI KALDIRILDI")

kontrol("stabil kod belgelendi: Y5-YENIDEN-KULLANIM-TAVANI-DELIYOR",
        "Y5-YENIDEN-KULLANIM-TAVANI-DELIYOR" in _P,
        "karar kodda belgelenmemis")
kontrol("`UI8-SURE-KORUNDU` yeniden kullanim yolu YOK",
        "UI8-SURE-KORUNDU" not in _P,
        "yeniden kullanim hala var — global tavan delinebilir")
kontrol("klip KOPYALAMA (shutil.copy) kapida YOK",
        "shutil.copy(_sec" not in _P and "_mevcut[n % len(_mevcut)]" not in _P,
        "kopyalama yolu duruyor")
def _yalniz_kod(metin: str) -> str:
    """Yorum ve docstring at — kusuru ANLATAN metin KOD sayilmasin."""
    g = re.sub(r'"""(?:.|\n)*?"""', "", metin)
    return re.sub(r"^\s*#.*$", "", g, flags=re.M)


_KOD = _yalniz_kod(_P)
kontrol("hatali provenans anahtari `_pv.get(\"url\")` KODDA YOK",
        '_pv.get("url")' not in _KOD,
        "orijinal_url yerine url okunuyor (sessiz veri kaybi)")
kontrol("provenans kopyalama cagrisi kodda YOK (yol kalkti)",
        "stok_provenans_kaydet(\n                            _vy" not in _KOD
        and "_atif2" not in _KOD)


blok("Y-5/2 — KAPI HALA FAIL-CLOSED (AI/statik gorsele dusme YOK)")

kontrol("kapi duruyor: UI7-GORSEL-YASAK-KAPISI", "UI7-GORSEL-YASAK-KAPISI" in _P)
kontrol("kapi INGILIZCE sorgu kullaniyor (UI-8)",
        "scene_prompt" in _KAPI and "UI8-TURKCE-SORGU" in _P)
kontrol("kapi turkce `anlatim`i sorgu olarak KULLANMIYOR",
        not re.search(r'_sorgu\s*=\s*\([^)]*s\.get\("anlatim"\)', _KAPI))
kontrol("genel yedek sorgular deneniyor",
        "genel_yedek_sorgular" in _KAPI)
kontrol("son care klip TEKRARI (ayni sorgu) duruyor",
        "tekrara_izin=True" in _KAPI)
kontrol("bulunamazsa MEDYA-VIDEO-YOK ile BOS kalir",
        "MEDYA_VIDEO_YOK" in _KAPI and "return None" in _KAPI)
kontrol("AI gorsele dusme metni yok",
        "AI gorsele mecbur" not in _P)


blok("Y-5/3 — GLOBAL TAVAN SOZLESMESI GORUNUR")

import kaynak_tavani                                        # noqa: E402
kontrol("tavan sabiti 8.0 sn",
        float(kaynak_tavani.KAYNAK_BASINA_TAVAN_SN) == 8.0,
        str(kaynak_tavani.KAYNAK_BASINA_TAVAN_SN))
kontrol("global bolme plani mevcut (ileride baglanacak)",
        hasattr(kaynak_tavani, "bolme_plani"))
kontrol("sahne bazli tavan uygulamasi duruyor",
        "_kaynak_tavani_uygula" in _P)


blok("Y-5/4 — GERILEME YOK")

kontrol("GERILEME YOK: %100 video profilleri duruyor",
        _P.count('"footage_pct": 100') >= 5
        and _P.count('"gorsel_yasak": True') >= 5)
kontrol("GERILEME YOK: UI-8 fps 30 duruyor",
        'os.environ.get("VIDEO_FPS", "30")' in _P)
kontrol("GERILEME YOK: UI-8 magnific kapali duruyor",
        "UI8-MAGNIFIC-KAPALI" in _P)
kontrol("GERILEME YOK: Y-2 render butcesi duruyor",
        "Y2-RENDER-TIMEOUT" in _P)
kontrol("GERILEME YOK: UI-6 tani kodlari duruyor",
        "SAHNE-YOK-MEDYA-VE-TTS" in _P)
kontrol("GERILEME YOK: 1920x1080 sabit",
        '"genislik": 1920, "yukseklik": 1080' in _P)

import kutuphane                                            # noqa: E402
kontrol("GERILEME YOK: Y-4 teslim kapisi fail-closed",
        kutuphane.kabul_edilebilir_mi(
            {"durum": "bitti", "video": "x.mp4", "qa": {"durum": "PASS"},
             "edit_plani": {"ok": True, "render_edilebilir": False,
                            "qa": {"durum": "FAIL", "sorunlar": [
                                {"kod": "FACT-BAGLANTI-YOK",
                                 "seviye": "fail"}]}}})["kabul"] is False)

print(f"\n{'=' * 60}")
print(f"GECEN: {gecen}   BASARISIZ: {len(basarisiz)}")
for b in basarisiz:
    print(f"  XX {b}")
sys.exit(1 if basarisiz else 0)
