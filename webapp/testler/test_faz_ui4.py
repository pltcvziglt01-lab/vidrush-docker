#!/usr/bin/env python3
"""FAZ UI-4 testleri — KURGU YOGUNLUGU GECERLI EDIT KIMLIGINE BAGLANIR.

⚠ OLCULEN KUSUR (`UI4-EDIT-SEVIYESI-GECERSIZ`): `/akis`in "Kurgu
yogunlugu" secimi `az|orta|yuksek` gonderiyordu, ama documentary
`EDIT_STILLERI` bu kimlikleri TANIMIYOR. Sunucu gecersiz degeri SESSIZCE
`sinematik-belgesel` varsayilanina dusuruyordu. Gercek staging kaniti:

    istek edit=yuksek   ->   cevap EDIT=sinematik-belgesel

Yani kullanicinin kurgu secimi UYGULANMIYORDU — kapatilan
`UI2-KAYNAK-TERCIHI-SUNUCUYA-GITMIYOR` ile AYNI SINIF kusur.

Cozum (en kucuk): UI'de UC KONUM (Az/Orta/Yuksek) ve etiketler AYNEN
KALIR; istemci `edit` alanina DETERMINISTIK ve GECERLI bir stil kimligi
gonderir. `/api/generate` ust-seviye alan sayisi TAM 22 KALIR — `edit`
zaten o 22'nin icindedir, yalnizca DEGERI gecerli hale gelir.

⚠ Sunucunun gecersiz deger politikasi (sessiz dusus) KORUNUR: eski
istemcileri kirmamak icin oradadir. Degisen sey, ANA AKISIN artik
gecersiz deger URETMEMESIDIR.

Kosum: .venv-test/bin/python3 webapp/testler/test_faz_ui4.py
"""
from __future__ import annotations

import os
import re
import shutil
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEPO = os.path.dirname(KOK)
sys.path.insert(0, KOK)
sys.path.insert(0, os.path.join(DEPO, "app"))   # `uret` modulu pipeline icin

gecen, basarisiz, bloke = 0, [], []


def kontrol(ad, kosul, detay=""):
    global gecen
    if kosul:
        gecen += 1
        print(f"  ok   {ad}")
    else:
        basarisiz.append(f"{ad} — {detay}")
        print(f"  XX   {ad}  {detay}")


def bloke_yaz(ad, sebep):
    bloke.append(f"{ad} — {sebep}")
    print(f"  --   BLOKE {ad}: {sebep}")


def blok(ad):
    print(f"\n── {ad} ──")


def oku(*p):
    with open(os.path.join(*p), encoding="utf-8") as f:
        return f.read()


_UI = oku(KOK, "static", "js", "ui1.js")

# ═══════════ 1) HARITA VAR VE UC KONUMU KAPSIYOR ═══════════
blok("1) SEGMENT -> GECERLI EDIT KIMLIGI HARITASI")

# ⚠ Harita ISTEMCI KAYNAGINDAN okunur (iddia edilmez).
_h = re.search(r"const EDIT_HARITASI\s*=\s*\{([^}]*)\}", _UI)
HARITA = {}
if _h:
    for a, b in re.findall(r"(\w+)\s*:\s*\"([\w-]+)\"", _h.group(1)):
        HARITA[a] = b

kontrol("⭐ UI-4 BELIRLEYICI: `EDIT_HARITASI` istemcide TANIMLI",
        bool(HARITA), "harita bulunamadi")
kontrol("⭐ UI-4: harita TAM uc konumu kapsiyor (az/orta/yuksek)",
        set(HARITA) == {"az", "orta", "yuksek"}, str(sorted(HARITA)))
kontrol("⭐ UI-4: uc konum UC FARKLI stile gidiyor "
        "(secim gercekten fark yaratir)",
        len(set(HARITA.values())) == 3, str(HARITA))

# ═══════════ 2) HEDEFLER GERCEKTEN GECERLI + OLCULEBILIR ═══════════
blok("2) HEDEF KIMLIKLER GERCEK MODULDE GECERLI")

# ⚠ `pipeline` import aninda calisma kokunu kurar; testte GECICI kok
# verilmezse `/opt/vidrush` (sunucu yolu) denenir ve izin hatasi alinir.
_gk = tempfile.mkdtemp(prefix="ui4_kok_")
for _alt in (("webapp", "veri"), ("webapp", "ciktilar"), ("render-studio", "out")):
    os.makedirs(os.path.join(_gk, *_alt), exist_ok=True)
shutil.copy(os.path.join(DEPO, "app", "uret.py"), os.path.join(_gk, "uret.py"))
os.environ["VIDRUSH_KOK"] = _gk
try:
    import pipeline as P
    PIPELINE_VAR = True
except Exception as e:                                        # noqa: BLE001
    PIPELINE_VAR = False
    bloke_yaz("pipeline importu", f"{type(e).__name__}: {e}")

if PIPELINE_VAR:
    kontrol("⭐ UI-4 BELIRLEYICI: haritadaki HER kimlik `EDIT_STILLERI`de "
            "GERCEKTEN var (sessiz dusus IMKANSIZ)",
            bool(HARITA) and all(v in P.EDIT_STILLERI for v in HARITA.values()),
            str([v for v in HARITA.values() if v not in P.EDIT_STILLERI]))
    # ⚠ ESKI DAVRANISIN KANITI: `az|orta|yuksek` GECERLI DEGIL. Bu kontrol
    # kusurun gercekligini kilitler; gelecekte biri bu kimlikleri stil
    # sozlugune eklerse test bunu FARK EDER.
    kontrol("UI-4: ham segment adlari `EDIT_STILLERI`de YOK "
            "(kusurun kok nedeni)",
            not any(s in P.EDIT_STILLERI for s in ("az", "orta", "yuksek")))
    kontrol("UI-4: varsayilan hala `sinematik-belgesel` (gerileme yok)",
            P.VARSAYILAN_EDIT == "sinematik-belgesel", P.VARSAYILAN_EDIT)

    # ── OLCULEBILIR SAHNE YOGUNLUGU ──
    # `sahne_sn` = sahne basina saniye. KUCULDUKCE kesme yogunlugu ARTAR.
    if set(HARITA) == {"az", "orta", "yuksek"}:
        _sn = {k: float(P.EDIT_STILLERI[v]["sahne_sn"])
               for k, v in HARITA.items()}
        kontrol("⭐ UI-4 BELIRLEYICI: sahne yoganlugu OLCULEBILIR sekilde "
                f"artiyor (sahne_sn az>orta>yuksek: {_sn})",
                _sn["az"] > _sn["orta"] > _sn["yuksek"], str(_sn))
        # 60 sn'lik ayni metin icin TURETILEN sahne sayisi
        _adet = {k: round(60.0 / v) for k, v in _sn.items()}
        kontrol("⭐ UI-4: ayni 60 sn girdi UC FARKLI sahne sayisi uretir "
                f"({_adet})",
                len(set(_adet.values())) == 3
                and _adet["yuksek"] > _adet["orta"] > _adet["az"],
                str(_adet))
        kontrol("UI-4: `yuksek` en az 2 kat yogun (secim HISSEDILIR)",
                _adet["yuksek"] >= 2 * _adet["az"], str(_adet))

# ═══════════ 3) ISTEMCI HAM SEGMENT GONDERMIYOR ═══════════
blok("3) ANA AKIS ARTIK GECERSIZ DEGER URETMIYOR")

_GOVDE = _UI[_UI.index("async function uretimBaslat"):
             _UI.index("function oturumEtiketi")]
kontrol("⭐ UI-4 BELIRLEYICI: `edit` alanina HARITADAN gecen deger "
        "gonderiliyor (ham `#akis-edit` degeri DEGIL)",
        re.search(r'fd\.append\("edit",\s*editKimligi\(\)\)', _GOVDE)
        is not None, "ham deger gonderiliyor olabilir")
kontrol("⭐ UI-4: ham segment adi ARTIK varsayilan olarak gonderilmiyor "
        '(`|| "orta"` gibi gecersiz yedek YOK)',
        not re.search(r'fd\.append\("edit",[^\n]*"(az|orta|yuksek)"', _GOVDE),
        "gecersiz yedek deger var")
kontrol("UI-4: bilinmeyen segment GECERLI varsayilana duser "
        "(istemci de fail-safe)",
        "VARSAYILAN_EDIT_KIMLIGI" in _UI or "sinematik-belgesel" in _UI)

# ═══════════ 4) UI KONUMLARI VE ERISILEBILIRLIK KORUNDU ═══════════
blok("4) UC KONUM + ETIKETLER KORUNDU")

_SRV = oku(KOK, "server.py")
for _seg in ("az", "orta", "yuksek"):
    kontrol(f"UI-4 GERILEME YOK: `{_seg}` konumu sayfada DURUYOR",
            f'value="{_seg}"' in _SRV, _seg)
kontrol("UI-4 GERILEME YOK: `Kurgu yoğunluğu` etiketi ve `label[for]` bagi "
        "DEGISMEDI",
        'for="akis-edit"' in _SRV and "Kurgu yoğunluğu" in _SRV)
kontrol("UI-4 GERILEME YOK: sunucu `/api/generate` HTML'i ve 22 alan "
        "sozlesmesi DEGISMEDI",
        len(set(re.findall(r"\{ad: '(\w+)'",
                           oku(KOK, "static/js/api.js")))) == 22)

# ═══════════ 5) UI-2/UI-3 KAZANIMLARI BOZULMADI ═══════════
blok("5) UI-2 / UI-3 GERILEME YOK")

kontrol("UI-4 GERILEME YOK: kaynak tercihi ayri uctan gidiyor",
        '"/api/kaynak-tercihi"' in _UI
        and 'fd.append("kaynak_tercihi"' not in _UI)
kontrol("UI-4 GERILEME YOK: CSRF basligi duruyor",
        "x-csrf-token" in _UI and "vr_csrf" in _UI)
kontrol("UI-4 GERILEME YOK: fail-closed kapisi duruyor",
        "UI3-KAYNAK-TERCIHI-YAZILAMADI" in _GOVDE
        and _GOVDE.index("UI3-KAYNAK-TERCIHI-YAZILAMADI")
        < _GOVDE.index('fetch("/api/generate"'))
kontrol("UI-4 GERILEME YOK: OTURUM cerezi okunmuyor, cerez erisimi TEK",
        "vr_oturum" not in _UI
        and len(re.findall(r"document\.cookie", _UI)) == 1)
kontrol("UI-4 GERILEME YOK: generate govdesi hala 7 alan "
        "(22 alanin ALT KUMESI, buyumedi)",
        len(re.findall(r'fd\.append\("(\w+)"', _UI)) == 7,
        str(re.findall(r'fd\.append\("(\w+)"', _UI)))

shutil.rmtree(_gk, ignore_errors=True)

print(f"\n{'=' * 60}")
print(f"GECEN: {gecen}   BASARISIZ: {len(basarisiz)}   BLOKE: {len(bloke)}")
for b in basarisiz:
    print(f"  XX {b}")
for b in bloke:
    print(f"  -- BLOKE {b}")
sys.exit(1 if basarisiz else 0)
