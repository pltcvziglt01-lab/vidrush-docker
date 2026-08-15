#!/usr/bin/env python3
"""FAZ UI-6 — "Hiç sahne üretilemedi" TESHIS EDILEBILIR OLSUN.

⚠ OLCULEN OLAY (staging 185.23.17.240): 14 Agu 2026 23:04'te anonim bir is
(`anon:oturumsuz`) %58 ilerlemede `durum=hata`, `hata="Hiç sahne
üretilemedi"` ile dustu. Mesaj HANGI KATMANIN coktugunu SOYLEMIYORDU.

Kok neden ancak ELLE probe ile bulunabildi (15 Agu, remote):
  · stok video  : Pexels 2560x1440 klip DONDU (calisiyor)
  · TTS         : edge-tts OK (21 KB), OpenAI OK (99 KB) (calisiyor)
  · render/disk : ffmpeg+ffprobe OK, 95 GB bos, 2 isci, kuyruk 0
Yani bilesenlerin HEPSI saglam; is, sunucunun o saatlerde yasadigi AG
KESINTISI penceresine denk geldi (ayni kesinti disaridan HTTP:000 ve SSH
timeout olarak da olculdu).

⚠ GERCEK KUSUR KOD'DA: `pipeline.py` sahneyi ancak `n in sonuc_medya AND
n in tts_sonuc` ise ekliyor. Ikisinden HERHANGI biri komple bosalirsa
`props_sahneler` bos kalir ve kullaniciya TEK ve AYIRT EDILEMEZ bir mesaj
doner. Operator "medya mi TTS mi coktu" sorusunu LOGSUZ yanitlayamaz.

⚠ BU FAZ TANIYI DUZELTIR, URETIM DAVRANISINI DEGISTIRMEZ: sahne secim
kurali, kuyruk, QA ve kredi yollari AYNEN KALIR.

Kosum: .venv-test/bin/python3 webapp/testler/test_faz_ui6.py
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

# "Hiç sahne üretilemedi" yukseltme noktasinin BAGLAMI (+- 40 satir)
_i = _P.find("Hiç sahne üretilemedi")
_BAGLAM = _P[max(0, _i - 2000):_i + 1600] if _i >= 0 else ""


blok("UI-6/1 — STABIL TANI KODLARI")

for _kod in ("SAHNE-YOK-MEDYA-VE-TTS", "SAHNE-YOK-MEDYA",
             "SAHNE-YOK-TTS", "SAHNE-YOK-KESISIM"):
    kontrol(f"stabil kod tanimli: {_kod}", _kod in _P,
            "ayirt edici tani kodu yok")


blok("UI-6/2 — HATA HANGI KATMANIN COKTUGUNU SOYLER")

kontrol("hata yukseltme noktasi bulundu", bool(_BAGLAM))
kontrol("medya sayaci (`sonuc_medya`) hata metnine giriyor",
        "len(sonuc_medya)" in _BAGLAM,
        "medya sayisi raporlanmiyor")
kontrol("seslendirme sayaci (`tts_sonuc`) hata metnine giriyor",
        "len(tts_sonuc)" in _BAGLAM,
        "TTS sayisi raporlanmiyor")
kontrol("denenen sahne sayisi raporlaniyor",
        "len(islenecek)" in _BAGLAM,
        "kac sahne denendigi yazilmiyor")
kontrol("tani kodu hata metnine GOMULU",
        re.search(r"Hiç sahne üretilemedi \(\{_?kod", _BAGLAM) is not None
        or re.search(r'f"Hiç sahne üretilemedi \(\{', _BAGLAM) is not None,
        "mesaj hala sabit metin")


blok("UI-6/3 — GERILEME YOK: URETIM DAVRANISI AYNI")

kontrol("GERILEME YOK: sahne secim kurali DEGISMEDI "
        "(medya VE tts sarti duruyor)",
        "if n not in sonuc_medya or n not in tts_sonuc:" in _P)
kontrol("GERILEME YOK: bakiye mesaji hala AYRI yolda",
        "BAKIYE_MESAJI" in _BAGLAM)
kontrol("GERILEME YOK: UI-5 %100 video sozlesmesi duruyor",
        _P.count('"footage_pct": 100') >= 5
        and _P.count('"gorsel_yasak": True') >= 5)
kontrol("GERILEME YOK: UI-5 MEDYA_VIDEO_YOK stabil kodu duruyor",
        "MEDYA-VIDEO-YOK" in _P)
kontrol("GERILEME YOK: kaynak tavani (<=8 sn) sozlesmesi duruyor",
        "_kaynak_tavani_uygula" in _P)
kontrol("GERILEME YOK: yas etiketleri '— NN yaş' biciminde",
        not re.search(r'"ad": "[^"]*\(\d{2}\)"', _P))

print(f"\n{'=' * 60}")
print(f"GECEN: {gecen}   BASARISIZ: {len(basarisiz)}")
for b in basarisiz:
    print(f"  XX {b}")
sys.exit(1 if basarisiz else 0)
