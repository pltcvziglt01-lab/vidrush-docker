#!/usr/bin/env python3
"""FAZ Y-10 — YETERSIZ OLGU HAVUZU ERKEN VE FAIL-CLOSED DURUR.

⚠ OLCULEN KUSUR (`Y10-HAVUZ-YETERSIZ-SESSIZ`) — gercek is
job_1786792477656_y71414_df7e2a:
    ARASTIRMA: 1/11 olgu dogrulandi, 9 kaynak
    ...
    TESLIM: False | KABUL-YOK:Y1-KURGU-QA-FAIL:FACT-BAGLANTI-YOK

Y-7 `fact_id`yi props sinirindan GECIRDI (zincir onarildi), ama havuzda
YALNIZCA 1 dogrulanmis olgu vardi; 15 sahnenin cogu baglanamadi ve is
RENDER BITTIKTEN SONRA teslim kapisinda dustu.

⚠ ISRAF: yetersiz havuz URETIMDEN ONCE bellidir (olgu bagi sahne
planlamasindan hemen sonra, medya/TTS/render'dan ONCE kosar). Buna ragmen
hat tum medyayi indirip TTS uretip ~10 dk render yapiyor ve sonra
reddediliyordu.

⚠ KOK NEDEN (havuzun kendisi): `manifests.senaryoya_girebilir()` kritik
iddia icin birincil kaynak VEYA iki bagimsiz GUCLU alan sart kosar;
`fact_checker` destekleyen kaynak bulamadigi iddiayi `cozulmedi` yapar.
11 iddia icin toplam 9 kaynak toplanmisti — cogu iddia destekleyen kaynak
bulamadi.

── SOZLESME ──
  · Olgu bagi sonrasi KAPSAM olculur (`baglanan / hedef`).
  · Kapsam esigin altindaysa is ERKEN ve STABIL kodla durur:
    `ARASTIRMA-HAVUZ-YETERSIZ` — medya/TTS/render'a HIC girilmez.
  · ⚠ FACT UYDURULMAZ, KAPI GEVSETILMEZ: `FACT-BAGLANTI-YOK` fail olarak
    KALIR; bu faz yalnizca kaybi ERKENE ceker ve NEDENINI soyler.

Kosum: .venv-test/bin/python3 webapp/testler/test_faz_y10.py
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


_P = oku("pipeline.py")


blok("Y-10/1 — ERKEN KAPI VAR VE STABIL KOD TASIR")

kontrol("stabil kod tanimli: ARASTIRMA-HAVUZ-YETERSIZ",
        "ARASTIRMA-HAVUZ-YETERSIZ" in _P,
        "yetersiz havuz icin stabil kod yok")
kontrol("stabil kod belgelendi: Y10-HAVUZ-YETERSIZ",
        "Y10-HAVUZ-YETERSIZ" in _P,
        "karar kodda belgelenmemis")
kontrol("kapsam esigi sabiti tanimli (FACT_KAPSAM_ESIGI)",
        re.search(r"FACT_KAPSAM_ESIGI\s*=", _P) is not None)


blok("Y-10/2 — KAPI URETIMDEN ONCE CALISIYOR (kredi yakmadan)")

# ⚠ Y-11b-2 SOZLESMESI: tahsis otoritesi `fact_bagla` (0.16 Jaccard)
# DEGIL, `yetkili_tahsis` (allowlist + entailment).
_i_kapi = _P.find("ARASTIRMA-HAVUZ-YETERSIZ")
_i_medya = _P.find("def _sahne_medya")
_i_bag = _P.find("arastirma_kopru.yetkili_tahsis(")
_i_gate = _P.find("fact_baglama.grounded_kapisi(")
kontrol("kapi olgu bagindan SONRA", _i_kapi > _i_bag > 0,
        f"kapi={_i_kapi} bag={_i_bag}")
kontrol("kapi medya uretiminden ONCE (israf yok)",
        0 < _i_kapi < _i_medya,
        f"kapi={_i_kapi} medya={_i_medya} — render'dan sonra dusuyor")
kontrol("KOSULSUZ grounded kapi medya uretiminden ONCE",
        0 < _i_gate < _i_medya, f"kapi={_i_gate} medya={_i_medya}")
kontrol("eski benzerlik yolu (fact_bagla) uretimden KALDIRILDI",
        "arastirma_kopru.fact_bagla(" not in _P)


blok("Y-10/3 — FACT UYDURULMUYOR, KAPI GEVSETILMIYOR")

_QAON = oku("editor", "qa_on.py")
kontrol("FACT-BAGLANTI-YOK hala FAIL",
        "FACT-BAGLANTI-YOK" in _QAON
        and "FACT-BAGLANTI-YOK" in _QAON[_QAON.find("FAIL_KODLARI"):
                                         _QAON.find("FAIL_KODLARI") + 700])
kontrol("uydurma fact_id uretilmiyor (eslesmeyen sahne kimlik ALMAZ)",
        "UYDURMA fact_id YOK" in _P)
import kutuphane                                            # noqa: E402
kontrol("Y-4 teslim kapisi fail-closed duruyor",
        kutuphane.kabul_edilebilir_mi(
            {"durum": "bitti", "video": "x.mp4", "qa": {"durum": "PASS"},
             "edit_plani": {"ok": True, "render_edilebilir": False,
                            "qa": {"durum": "FAIL", "sorunlar": [
                                {"kod": "FACT-BAGLANTI-YOK",
                                 "seviye": "fail"}]}}})["kabul"] is False)
kontrol("YAYIN_KAPILARI daraltmasi geri gelmedi",
        not hasattr(kutuphane, "YAYIN_KAPILARI"))


blok("Y-10/4 — ESIK GERCEKCI VE GERCEK OLAYI YAKALIYOR")

# ⚠ Y-11b-2 SOZLESMESI (`Y11B2-ENV-KAPI-GEVSETME`): esik ENV'den
# OKUNABILIR ama ENV kapiyi GEVSETEMEZ — yalnizca SIKILASTIRABILIR.
_m = re.search(r"FACT_KAPSAM_TABANI\s*=\s*([0-9.]+)", _P)
_esik = float(_m.group(1)) if _m else -1.0
kontrol("esik tabani okunabildi", _esik > 0, f"esik={_esik}")
kontrol("esik TAM KAPSAM (1.0) — her shot fact_id tasimali",
        _esik == 1.0, f"esik={_esik}")
kontrol("esik max(taban, env) ile KILITLI (env GEVSETEMEZ)",
        "max(FACT_KAPSAM_TABANI," in _P, "env dogrudan otorite")
kontrol("karar kodu belgelendi: Y11B2-ENV-KAPI-GEVSETME",
        "Y11B2-ENV-KAPI-GEVSETME" in _P)
# Gercek olay: 1 olgu havuzu -> 15 sahnenin cogu baglanamaz
kontrol("GERCEK OLAY: 1/15 kapsam esigin ALTINDA (is erken durur)",
        (1.0 / 15.0) < _esik)
kontrol("TAM KAPSAM (15/15) esigi GECER",
        (15.0 / 15.0) >= _esik)


blok("Y-10/5 — GERILEME YOK")

kontrol("GERILEME YOK: Y-9 hard-cut J/L duruyor",
        "Y9-JL-HARDCUT" in oku("hizli_render.py"))
kontrol("GERILEME YOK: Y-8 hedef sure duruyor",
        "hedef_sure_sn" in _P
        and "POST-HEDEF-SURE-SAPMA" in oku("editor", "qa_son.py"))
kontrol("GERILEME YOK: Y-7 fact zinciri duruyor",
        "Y7-FACT-PROPS-SINIRI" in _P)
kontrol("GERILEME YOK: Y-5 yeniden kullanim geri gelmedi",
        "UI8-SURE-KORUNDU" not in _P)
kontrol("GERILEME YOK: %100 video profilleri duruyor",
        _P.count('"footage_pct": 100') >= 5)
kontrol("GERILEME YOK: UI-8 fps 30 duruyor",
        'os.environ.get("VIDEO_FPS", "30")' in _P)
# ⚠ Y-11b-2 SOZLESME DEGISIKLIGI (`Y11B2-KOSULSUZ-DEGIL`): eskiden kapi
# YALNIZ arastirma calistiysa ve olgu havuzu varsa uygulaniyordu; grounded
# belgeselde bu bir FAIL-OPEN'di (arastirma kapali -> sessiz devam).
# Artik GROUNDED modda kapi KOSULSUZ; grounded OLMAYAN modlar KAPSAM DISI
# ve davranislari BIT-BIT ayni kalir.
kontrol("GERILEME YOK: grounded OLMAYAN modlar hat eskisi gibi surer",
        "KAPSAM DISIDIR" in _P and "fact_baglama.GROUNDED_MODLAR" in _P)
kontrol("GROUNDED modda arastirma yoklugu KOSULSUZ FAIL",
        "KOD_GROUNDED_ARASTIRMA_YOK" in _P
        and _P.find("KOD_GROUNDED_ARASTIRMA_YOK") < _i_medya)
kontrol("davranissal 0-call kaniti ayri suitte",
        os.path.exists(os.path.join(KOK, "testler", "test_faz_y11b2.py")))

print(f"\n{'=' * 60}")
print(f"GECEN: {gecen}   BASARISIZ: {len(basarisiz)}")
for b in basarisiz:
    print(f"  XX {b}")
sys.exit(1 if basarisiz else 0)
