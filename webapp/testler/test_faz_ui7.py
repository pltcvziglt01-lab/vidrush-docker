#!/usr/bin/env python3
"""FAZ UI-7 — GORSEL YASAK HER YOLDA GECERLI + DAR TARIHSEL TANI.

⚠ OLCULEN KUSUR (gercek 120 sn staging isi job_1786781281945_r1e110_e88a4e,
15 Agu 2026). Sunucunun KENDI QA olcumu:

    RENDER-QA (gercek timeline): WARN sahne=17 kapsam=1.0 gercek_video=0.531

Yani `sinematik-belgesel` (footage_pct=100, gorsel_yasak=True) olmasina
RAGMEN timeline'in yalnizca %53'u gercek video. Log:

    sahne 14: KOPRU -> butceye secim yazildi (openai/uretilmis-eser)
    sahne 16: KOPRU -> butceye secim yazildi (openai/uretilmis-eser)

── KUSUR 1: `UI7-GORSEL-YASAK-YOLU-ATLANIYOR` ──
`_sahne_medya` footage blogunu SADECE su kosulla calistiriyor:

    if footage_acik and str(s.get("kaynak")) == "footage" and footage_sorgu:

Planlayici bir sahneyi `kaynak="gorsel"` isaretlerse footage blogu HIC
calismaz; `gorsel_yasak` kontrolu O BLOGUN ICINDE oldugu icin ATLANIR ve
akis dogrudan "2) AI gorsel" yoluna duser. Yani %100 video sozlesmesi
sahne bazinda SESSIZCE delinir.

── KUSUR 2: `UI7-CAGDAS-KONU-TARIHSEL-SANILIYOR` ──
`medya_kapisi._ESKI_ISARET` icinde "historic" TEK BASINA tarihsel sayiliyor.
Cagdas bir sehir belgeselinde "historic peninsula / historic walls" cok
yaygindir; bu sahneyi `tarihsel=True` yapinca `kare_kapisi` kareye bakip
modern isaret gordugu icin GERCEK klipleri eliyor:

    KARE RED [pexels] sahne_9.mp4: DONEM CELISKISI: tarihsel sahnede
    kareye bakan okuma modern isaret gordu ['cars on bridge','modern boats']

Sonra klip bulunamadigi icin AI gorsele dusuluyor -> kusur 1 ile birlesip
gercek video oranini dusuruyor.

⚠ DAR KAPSAM: "historic" yalnizca MEDYA TURU baglamında ("historic
footage/photograph/film/archive") tarihsel sayilir. Pre-1950 YIL ve
"archival/sepia/black and white/vintage" isaretleri AYNEN KORUNUR.

Kosum: .venv-test/bin/python3 webapp/testler/test_faz_ui7.py
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

import medya_kapisi as mk                                  # noqa: E402


blok("UI-7/1 — GORSEL YASAK: AI GORSEL YOLU HER KOSULDA KAPALI")

kontrol("stabil kod tanimli: UI7-GORSEL-YASAK-KAPISI",
        "UI7-GORSEL-YASAK-KAPISI" in _P,
        "AI gorsel yolundan once kapi yok")

# "2) AI gorsel" blogundan ONCE gorsel_yasak kapisi olmali.
_i_ai = _P.find("# 2) AI gorsel")
kontrol("AI gorsel blogu bulundu", _i_ai > 0)
_onceki = _P[max(0, _i_ai - 2200):_i_ai] if _i_ai > 0 else ""
kontrol("AI gorsel blogundan ONCE gorsel_yasak kapisi var",
        'prof.get("gorsel_yasak")' in _onceki
        and "MEDYA_VIDEO_YOK" in _onceki,
        "kapi yok — kaynak!=footage sahnede AI gorsele dusuluyor")
kontrol("kapi `kaynak` alanindan BAGIMSIZ (footage_sorgu sarti degil)",
        re.search(r'if prof\.get\("gorsel_yasak"\)[^\n]*:\s*\n(?:[^\n]*\n){0,30}?'
                  r'[^\n]*UI7-GORSEL-YASAK-KAPISI', _P) is not None,
        "kapi hala footage bloguna gomulu")


blok("UI-7/2 — DAR TARIHSEL TANI (cagdas konu yanlis siniflanmasin)")

# YANLIS POZITIFLER — cagdas cekim, tarihsel SAYILMAMALI
for _m in ("historic peninsula of istanbul",
           "historic walls and modern skyline",
           "historic building in the city center",
           "historic site drone view"):
    kontrol(f"cagdas: tarihsel DEGIL — {_m[:38]}",
            mk.tarihsel_mi(_m) is False,
            "hala tarihsel sayiliyor")

# GERCEK TARIHSEL — KORUNMALI
for _m, _ad in (("historic footage of the harbour", "historic footage"),
                ("historical photograph of the bridge", "historical photograph"),
                ("archival film reel", "archival"),
                ("sepia portrait", "sepia"),
                ("black and white street scene", "black and white"),
                ("vintage poster", "vintage"),
                ("the siege of 1453", "pre-1950 yil"),
                ("expedition of 1911", "expedition of 19")):
    kontrol(f"GERILEME YOK: hala tarihsel — {_ad}",
            mk.tarihsel_mi(_m) is True,
            "tarihsel tanisi kayboldu")


blok("UI-7/3 — GERILEME YOK: MEVCUT SOZLESMELER")

kontrol("GERILEME YOK: donem kapisi hala modern isareti reddediyor",
        mk.donem_kapisi("archival film reel", "a smartphone on the table")[0]
        is False)
kontrol("GERILEME YOK: tarihsel olmayan sahnede donem kapisi UYGULANMIYOR",
        mk.donem_kapisi("busy city street", "a smartphone")[0] is True)
kontrol("GERILEME YOK: UI-5 %100 video profilleri duruyor",
        _P.count('"footage_pct": 100') >= 5
        and _P.count('"gorsel_yasak": True') >= 5)
kontrol("GERILEME YOK: UI-5 MEDYA-VIDEO-YOK stabil kodu duruyor",
        "MEDYA-VIDEO-YOK" in _P)
kontrol("GERILEME YOK: UI-6 tani kodlari duruyor",
        "SAHNE-YOK-MEDYA-VE-TTS" in _P and "SAHNE-YOK-KESISIM" in _P)
kontrol("GERILEME YOK: kaynak tavani (<=8 sn) duruyor",
        "_kaynak_tavani_uygula" in _P)
kontrol("GERILEME YOK: 'AI gorsele mecbur' dususu geri gelmedi",
        "AI gorsele mecbur" not in _P)
kontrol("GERILEME YOK: modern isaret listesi bozulmadi",
        "smartphone" in mk.MODERN_ISARET and "solar panel" in mk.MODERN_ISARET)

print(f"\n{'=' * 60}")
print(f"GECEN: {gecen}   BASARISIZ: {len(basarisiz)}")
for b in basarisiz:
    print(f"  XX {b}")
sys.exit(1 if basarisiz else 0)
