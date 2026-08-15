#!/usr/bin/env python3
"""FAZ Y-9 — HARD-CUT'TA GERCEK SES/GORUNTU SINIR AYRIMI.

⚠ OLCULEN KUSUR (`Y9-JL-HARDCUT-ATLANIYOR`) — gercek is
job_1786792477656_y71414_df7e2a (Y-6 deploy SONRASI):
    footage 15/15 · MEDYA-VIDEO-YOK 0 · AI gorsel 0 · magnific 0
    Y6-JL-URETIM: 0        <-- HIC J/L URETILMEDI

KOK NEDEN: `sinematik-belgesel` profili `motion: "sinematik"` kullanir ->
sahnelerde `gecisImza` YOKTUR -> `hizli_render` gecis suresini
`g = min(g, 2/fps)` ile 2 KAREYE (30 fps'te 0.067 sn) dusurur; bu bilincli
bir "sert kesme" tasarimidir. Y-6'nin kosulu ise
`g > JL_OFFSET_SN + 0.02` (0.24) idi -> HICBIR hard-cut gecisinde
saglanamiyor. Yani J/L mantigi yalnizca UZUN gecislerde calisiyordu ama
belgesel neredeyse tamamen hard-cut.

⚠ Y-6'nin OLCUMU DOGRUYDU: `gercek_qa` 0 + `tam=False` dondu, sessiz PASS
URETMEDI. Kusur olcumde degil URETIMDE.

── COZUM ──
Hard-cut'ta goruntu 2 karede keser; SES capraz gecisi UZATILIR
(`ga = g + JL_OFFSET_SN`). Boylece ses siniri goruntu sinirindan
AYRISIR — J/L-cut tanimi tam olarak budur.
⚠ BEDEL VE SINIR: `acrossfade` toplam ses suresini `d` kadar kisaltir;
her J/L ~`JL_OFFSET_SN` kadar ses kaybi demektir. Bu yuzden offset KUCUK
(0.12 sn) ve sayi SINIRLI (`JL_MAKS`=3) tutulur -> toplam <= 0.36 sn,
`POST-OLU-FINAL` esigi olan 0.5 sn'nin ALTINDA kalir.

Kosum: .venv-test/bin/python3 webapp/testler/test_faz_y9.py
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


def oku(*p):
    with open(os.path.join(KOK, *p), encoding="utf-8") as f:
        return f.read()


_HR = oku("hizli_render.py")


blok("Y-9/1 — HARD-CUT'TA J/L URETILEBILIYOR")

kontrol("stabil kod belgelendi: Y9-JL-HARDCUT",
        "Y9-JL-HARDCUT" in _HR, "karar kodda belgelenmemis")
def _yalniz_kod(metin: str) -> str:
    """Yorum/docstring at — kusuru ANLATAN metin KOD sayilmasin."""
    g = re.sub(r'"""(?:.|\n)*?"""', "", metin)
    return re.sub(r"^\s*#.*$", "", g, flags=re.M)


_HR_KOD = _yalniz_kod(_HR)
kontrol("ESKI kosul KODDAN kalkti (g > JL_OFFSET_SN + 0.02)",
        "g > JL_OFFSET_SN + 0.02" not in _HR_KOD,
        "hard-cut hala atlaniyor")
kontrol("ses capraz gecisi UZATILIYOR (ga = g + offset)",
        re.search(r"ga\s*=\s*round\(\s*g\s*\+\s*JL_OFFSET_SN", _HR)
        is not None,
        "ses gecisi hala kisaltiliyor -> hard-cut'ta ayrim olusmaz")
kontrol("J/L sayisi SINIRLI (JL_MAKS)",
        re.search(r"JL_MAKS\s*=", _HR) is not None,
        "sinir yok -> ses kaybi birikir")
kontrol("offset kucuk tutuldu (<= 0.15 sn)",
        re.search(r'JL_OFFSET_SN.*"0\.1[0-5]"', _HR) is not None,
        "offset buyuk — olu final riski")


blok("Y-9/2 — BEDEL SINIRLI: OLU FINAL ESIGININ ALTINDA")

_m_off = re.search(r'JL_OFFSET_SN\s*=\s*float\(os\.environ\.get\("JL_OFFSET_SN",\s*"([0-9.]+)"\)',
                   _HR)
_m_maks = re.search(r"JL_MAKS\s*=\s*int\(os\.environ\.get\(\"JL_MAKS\",\s*\"(\d+)\"\)", _HR)
_off = float(_m_off.group(1)) if _m_off else 0.0
_maks = int(_m_maks.group(1)) if _m_maks else 0
kontrol("offset ve sinir okunabildi", _off > 0 and _maks > 0,
        f"offset={_off} maks={_maks}")
kontrol("toplam ses kaybi < 0.5 sn (POST-OLU-FINAL esigi)",
        _off * _maks < 0.5, f"{_off} x {_maks} = {_off * _maks:.2f} sn")
kontrol("kullanici sarti karsilanabilir: en az 2 J/L mumkun",
        _maks >= 2, f"maks={_maks}")


blok("Y-9/3 — SEMANTIK SECIM VE OLCUM KORUNDU")

kontrol("J/L karari hala SAHNE SEMANTIGINDEN (islev)",
        re.search(r'_islev in \("kanit", "vurgu"\)', _HR) is not None)
kontrol("sayac duruyor (_JL_SON)", "_JL_SON" in _HR)
kontrol("A/V senkronu: video suresi baglayici (-t)",
        re.search(r'"-t",\s*f"\{_toplam_v', _HR) is not None)
kontrol("gercek_qa gercek sayaci okuyor (uydurmuyor)",
        '"j_l_cut": _jl' in oku("gercek_qa.py"))


blok("Y-9/4 — GERILEME YOK")

kontrol("GERILEME YOK: xfade zinciri duruyor",
        "xfade=transition=" in _HR)
kontrol("GERILEME YOK: hard-cut 2 kare tasarimi duruyor",
        re.search(r"g = min\(g, 1\.0 / max\(1, fps\) \* 2\)", _HR) is not None,
        "sert kesme tasarimi bozulmus")
kontrol("GERILEME YOK: Y-6 kapilari duruyor",
        "KURGU-JL-YOK" in oku("editor", "qa_on.py")
        and "SES-SFX-BANT" in oku("editor", "qa_on.py"))
_P = oku("pipeline.py")
kontrol("GERILEME YOK: Y-7 fact zinciri duruyor",
        "Y7-FACT-PROPS-SINIRI" in _P)
kontrol("GERILEME YOK: Y-8 hedef sure duruyor",
        "hedef_sure_sn" in _P
        and "POST-HEDEF-SURE-SAPMA" in oku("editor", "qa_son.py"))
kontrol("GERILEME YOK: %100 video profilleri duruyor",
        _P.count('"footage_pct": 100') >= 5)

print(f"\n{'=' * 60}")
print(f"GECEN: {gecen}   BASARISIZ: {len(basarisiz)}")
for b in basarisiz:
    print(f"  XX {b}")
sys.exit(1 if basarisiz else 0)
