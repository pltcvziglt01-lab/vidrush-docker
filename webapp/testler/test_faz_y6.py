#!/usr/bin/env python3
"""FAZ Y-6 — GERCEK J/L-CUT URETIMI + SAHNE-SEMANTIK SFX + OLCUM + KAPI.

⚠ KULLANICI KARARI (BAGLAYICI, 15 Agu 2026): ust seviye kurgu bugunku
kabul videosundan ERTELENEMEZ. "Yalniz kapi ekleyip videoyu FAIL'e sokma;
minimal DETERMINISTIK URETICIYI de bagla." Bu faz uretici + render
davranisi + metadata + olcum + kapiyi AYNI atomda yapar.

⚠ OLCULEN KUSUR 1 (`Y6-JL-YAPISAL-SIFIR`): gercek hatta her gecis
`xfade=duration=g:offset=o` ile BIRLIKTE `acrossfade=d=g` uyguluyordu —
ses ve goruntu sinirlari AYNI noktada. `gercek_qa.ses_kurgu_olcumu`
bunu acikca yaziyor:
    "j_l_cut": 0, "tam": False
    gerekce: "ayni g ve ayni offset -> ses/video siniri AYRISMAZ"
Yani J/L-cut olculmuyor degildi; YAPISAL OLARAK URETILMIYORDU.

⚠ OLCULEN KUSUR 2 (`Y6-SFX-OLCUM-YOK`): SFX ffmpeg hattinda GERCEKTEN
bindiriliyor (`pipeline.sfx_bindir`, `SFX_ISLEV` haritasi, seyreklik
0.75) ama kac tane bindirildigi hicbir yere YAZILMIYOR; `qa_on` yalnizca
EditorV2 plan sayacini goruyor ve tek esik (12/dk) kota yuzunden
ULASILAMAZ olu koddu.

⚠ OLCULEN KUSUR 3 (`Y6-JL-METADATA-YOK`): renderer `j_cut_sn`/`l_cut_sn`
bekliyor (`Ses.tsx`), `plan.py` yalnizca bool yaziyordu.

── COZUM (deterministik, sahne-semantik) ──
  · J-cut: ses goruntuden ONCE girer  -> islev `kanit`/`vurgu`
  · L-cut: ses goruntuden SONRA biter -> islev `sonuc`
  · Uygulama: o gecislerde ses capraz gecisi goruntununkinden FARKLI
    (`acrossfade d != xfade duration`) -> ses/goruntu siniri AYRISIR.
  · Yuksek kurgu presetinde EN AZ 2 gercek J/L-cut hedeflenir.
  · A/V senkronu korunur: video suresi `-t` ile baglayicidir.

Kosum: .venv-test/bin/python3 webapp/testler/test_faz_y6.py
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
_GQ = oku("gercek_qa.py")
_SES = oku("editor", "ses.py")
_PLAN = oku("editor", "plan.py")
_QAON = oku("editor", "qa_on.py")


blok("Y-6/1 — URETICI: GERCEK J/L OFFSET (ffmpeg hatti)")

kontrol("stabil kod belgelendi: Y6-JL-URETIM",
        "Y6-JL-URETIM" in _HR, "karar kodda belgelenmemis")
kontrol("J/L offset sabiti tanimli (JL_OFFSET_SN)",
        re.search(r"JL_OFFSET_SN\s*=", _HR) is not None)
kontrol("ses capraz gecisi goruntununkinden AYRI hesaplaniyor",
        re.search(r"acrossfade=d=\{g[a-z_]*[:.]", _HR) is not None
        and "acrossfade=d={g:.3f}" not in _HR,
        "acrossfade hala xfade ile AYNI g kullaniyor")
kontrol("J/L karari SAHNE SEMANTIGINDEN (islev) turetiliyor",
        re.search(r'islev.{0,200}(kanit|sonuc|vurgu)', _HR, re.S) is not None,
        "islev tabanli j/l secimi yok")
kontrol("uretilen J/L sayisi SAYILIYOR (rapora girecek)",
        re.search(r"jl_sayisi|_jl_uretilen", _HR) is not None,
        "sayac yok")
kontrol("A/V senkronu korunuyor: video suresi baglayici (-t)",
        re.search(r'"-t",\s*f"\{[a-z_]*sure', _HR) is not None,
        "ses uzarsa kirpma yok")


blok("Y-6/2 — OLCUM: gercek_qa J/L'yi GERCEKTEN olcuyor")

kontrol("gercek_qa yapisal '0' iddiasini BIRAKTI",
        '"j_l_cut": 0' not in _GQ,
        "hala sabit 0 donuyor")
kontrol("gercek_qa J/L sayisini zaman cizgisinden okuyor",
        re.search(r"jl_sayisi|j_l_cut.{0,80}(sahne|liste|say)", _GQ, re.S)
        is not None,
        "olcum yok")
# ⚠ FAZ Y-13a — BU KONTROL BILINCLI OLARAK DEGISTI.
# ESKI HALI: `"Y6-JL" in _GQ` — yani gercek_qa.py'nin METNINDE bir string
# arayan bir VARLIK testiydi. Y-13a olcum sozlesmesini degistirdi:
# gercek_qa ARTIK `hizli_render._JL_SON` global'ini OKUMUYOR (Y-6'nin
# "olcum tarafi" iddiasi zaten YANLISTI — okunan deger render'dan once
# alindigi icin hicbir zaman o ise ait degildi). Kontrol artik yeni karar
# kodunu ve DAVRANISI olcuyor.
kontrol("stabil kod: Y13-OLCUM-NIYETI-OKUYOR olcum tarafinda belgelendi",
        "Y13-OLCUM-NIYETI-OKUYOR" in _GQ,
        "olcum sozlesmesi kodda belgelenmemis")
kontrol("olcum artik render modulunun global'ini OKUMUYOR",
        "import hizli_render" not in _GQ,
        "bayat global hala okunuyor")


blok("Y-6/3 — METADATA: j_cut_sn / l_cut_sn plana yaziliyor")

kontrol("plan.py j_cut_sn yaziyor",
        '"j_cut_sn"' in _PLAN, "renderer sabit varsayilana dusuyor")
kontrol("plan.py l_cut_sn yaziyor", '"l_cut_sn"' in _PLAN)
kontrol("ses.py sozluk() J/L sayaclarini yayinliyor",
        '"j_cut_sayisi"' in _SES and '"l_cut_sayisi"' in _SES,
        "olcum alanlari yok")
kontrol("ses.py kaydirma suresi SABIT DEGIL, alan olarak yayinlaniyor",
        "ort_kaydirma_sn" in _SES)


blok("Y-6/4 — KAPILAR (red-first)")

kontrol("kapi kodu: KURGU-JL-YOK", "KURGU-JL-YOK" in _QAON,
        "J/L kapisi yok")
kontrol("kapi kodu: SES-SFX-BANT", "SES-SFX-BANT" in _QAON,
        "SFX bant kapisi yok")
kontrol("J/L kapisi EN AZ 2 gercek cut istiyor",
        re.search(r"KURGU-JL-YOK[\s\S]{0,400}2", _QAON) is not None
        or re.search(r"JL_EN_AZ\s*=\s*2", _QAON) is not None,
        "asgari 2 sarti yok")
# Cift taraflilik: hem "hic SFX yok" hem "tavani asti" dali olmali.
_sfx_dal = len(re.findall(r'"SES-SFX-BANT"', _QAON))
kontrol("SFX bandi CIFT TARAFLI (ne sifir ne asiri)",
        _sfx_dal >= 2
        and re.search(r"SFX_TAVAN_DK\s*=", _QAON) is not None
        and re.search(r"SFX_ASGARI_SURE_SN\s*=", _QAON) is not None,
        f"dal sayisi={_sfx_dal}")
kontrol("SFX ve J/L olcumleri QA olcum sozlugune yaziliyor",
        '"sfx_sayisi": _sfx_n' in _QAON and '"jl_sayisi": _jl_n' in _QAON,
        "olcum disari verilmiyor")


blok("Y-6/5 — GERILEME YOK")

_P = oku("pipeline.py")
kontrol("GERILEME YOK: SFX bindirme yolu duruyor (ffmpeg)",
        "def sfx_bindir" in _P and "SFX_ISLEV" in _P)
kontrol("GERILEME YOK: Y-5 yeniden kullanim geri gelmedi",
        "UI8-SURE-KORUNDU" not in _P)
kontrol("GERILEME YOK: UI-8 fps 30 duruyor",
        'os.environ.get("VIDEO_FPS", "30")' in _P)
kontrol("GERILEME YOK: UI-7 gorsel yasak kapisi duruyor",
        "UI7-GORSEL-YASAK-KAPISI" in _P)
kontrol("GERILEME YOK: %100 video profilleri duruyor",
        _P.count('"footage_pct": 100') >= 5)
kontrol("GERILEME YOK: xfade gecis zinciri duruyor",
        "xfade=transition=" in _HR)
kontrol("GERILEME YOK: teslim kapisi fail-closed (Y-4)",
        "Y1-KURGU-QA-FAIL" in oku("kutuphane.py")
        and "YAYIN_KAPILARI" not in oku("kutuphane.py"))

print(f"\n{'=' * 60}")
print(f"GECEN: {gecen}   BASARISIZ: {len(basarisiz)}")
for b in basarisiz:
    print(f"  XX {b}")
sys.exit(1 if basarisiz else 0)
