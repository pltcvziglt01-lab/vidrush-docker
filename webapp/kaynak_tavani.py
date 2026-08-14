#!/usr/bin/env python3
"""FAZ R-1d-g — AYNI KAYNAK TOPLAM <= 8.0 sn GARANTISI (deterministik).

⚠ OLCULEN KUSUR (R-1d-f pilotu, job_1786721869701):
    GERCEK-KAYNAK-TAVANI: 36560908  8.508 sn   (tavan 8.0)
                          ..._s001  8.124 sn
                          38614588  8.052 sn
                          15924008  8.028 sn
Gercek render hattinda **1 SAHNE = 1 VARLIK**. Bir sahne 8.0 sn'yi asarsa o
varlik TEK BASINA tavani asar ve baska care yoktur. Kabul bu yuzden SUREYE
BAGLI ve KARARSIZDI: R-1d-e pilotunda sahneler 7.1-7.6 sn oldugu icin ayni
urun KABUL EDILMISTI, R-1d-f'te 8.0 asilinca REDDEDILDI.

⚠ TAVAN YUKSELTILMEZ. `KAYNAK_BASINA_TAVAN_SN` J-5b kullanici sartidir ve
`medya.saglayici_motoru` ile AYNI TEK SABITTEN okunur.

── POLITIKA (deterministik, rastgelelik YOK) ──
  1. Suresi tavani ASMAYAN sahne BOLUNMEZ (davranis aynen korunur).
  2. Asan sahne, her parcasi <= tavan olacak EN AZ sayida ESIT parcaya
     bolunur (`ceil(sure / tavan)`).
  3. Her parcaya FARKLI bir varlik atanir; bir varligin TOPLAM kullanimi
     tavani asacaksa o varlik ATANMAZ.
  4. Aday sirasi verilen sirayla taranir -> ayni girdi AYNI cikti.
  5. Yeterli FARKLI varlik yoksa parca ATANMAZ ve STABIL KOD yazilir:
     `KAYNAK-TAVANI-VARLIK-YOK`. ⚠ Ayni kaynak tekrar kullanilarak toplam
     ASILMAZ; tavan da yukseltilmez — FAIL-CLOSED.

⚠ Bu modul MEDYA ACMAZ, DOSYA YAZMAZ, AG KULLANMAZ, RENDER ETMEZ. Saf
karar mantigi; bolme uygulamasi cagiran tarafin isidir.
"""
from __future__ import annotations

import math

SEMA_SURUM = "1.0.0"

try:                                                         # pragma: no cover
    from medya.saglayici_motoru import KAYNAK_BASINA_TAVAN_SN
except Exception:                                            # noqa: BLE001
    KAYNAK_BASINA_TAVAN_SN = 8.0

# ── STABIL KODLAR ──
KOD_VARLIK_YOK = "KAYNAK-TAVANI-VARLIK-YOK"
KOD_SURE_BOZUK = "KAYNAK-TAVANI-SURE-BOZUK"

# Kayan nokta toleransi: 8.000000001 "asti" sayilmasin.
EPS = 1e-9


def _f(v, d=0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def parca_sayisi(sure_sn, *, tavan_sn: float = KAYNAK_BASINA_TAVAN_SN) -> int:
    """Bu sahne kac parcaya bolunmeli? ⚠ Tavani asmayan sahne 1 kalir."""
    s = _f(sure_sn)
    if s <= 0 or tavan_sn <= 0:
        return 1
    return max(1, int(math.ceil(s / tavan_sn - EPS)))


def bolme_plani(sahneler, *, adaylar=None,
                tavan_sn: float = KAYNAK_BASINA_TAVAN_SN) -> dict:
    """Zaman cizgisini tavana UYAN parcalara boler ve varlik atar.

    `sahneler`: [{"scene_id", "sure_sn", "asset_id"(mevcut atama, ops.)}]
    `adaylar` : [{"asset_id", "saglayici", "lisans"}] — ATANABILIR havuz.
        ⚠ Lisansi/saglayicisi olmayan aday havuzdan ELENIR (provenanssiz
        varlik ATANMAZ).

    Doner: {"ok", "parcalar", "kullanim", "tavan_sn", "sorunlar", "bolunen"}
    ⚠ `ok=False` iken de parcalar DONER — cagiran taraf neyin atanamadigini
    GORUR; sessiz bir "hallettik" YOKTUR.
    """
    havuz = [a for a in (adaylar or [])
             if isinstance(a, dict) and str(a.get("asset_id") or "").strip()
             and str(a.get("lisans") or "").strip()
             and str(a.get("saglayici") or "").strip()]
    kullanim: dict = {}
    parcalar, sorunlar = [], []
    bolunen = 0

    for s in (sahneler or []):
        if not isinstance(s, dict):
            continue
        sid = str(s.get("scene_id") or "")
        sure = _f(s.get("sure_sn"))
        if sure <= 0:
            sorunlar.append({"kod": KOD_SURE_BOZUK, "scene_id": sid,
                             "detay": f"sure={s.get('sure_sn')!r}"})
            continue
        n = parca_sayisi(sure, tavan_sn=tavan_sn)
        if n > 1:
            bolunen += 1
        # ⚠ ESIT bolme: her parca sure/n (hepsi <= tavan, tanim geregi).
        p_sure = round(sure / n, 3)
        # Mevcut atama once denenir (gereksiz degisiklik YAPILMAZ).
        oncelik = []
        mevcut = str(s.get("asset_id") or "").strip()
        if mevcut:
            oncelik = [a for a in havuz if a["asset_id"] == mevcut]
        sira = oncelik + [a for a in havuz if a not in oncelik]
        for i in range(n):
            sec = None
            for a in sira:
                aid = a["asset_id"]
                if kullanim.get(aid, 0.0) + p_sure <= tavan_sn + EPS:
                    sec = a
                    break
            if sec is None:
                # ⚠ FAIL-CLOSED: ayni kaynagi tekrar kullanip tavani ASMAK
                # ya da tavani YUKSELTMEK YOK.
                sorunlar.append({"kod": KOD_VARLIK_YOK, "scene_id": sid,
                                 "parca": i + 1,
                                 "detay": (f"{p_sure} sn icin tavani asmayan "
                                           f"FARKLI varlik yok")})
                parcalar.append({"scene_id": sid, "parca": i + 1,
                                 "parca_sayisi": n, "sure_sn": p_sure,
                                 "asset_id": None, "saglayici": None,
                                 "lisans": None, "atandi": False})
                continue
            kullanim[sec["asset_id"]] = round(
                kullanim.get(sec["asset_id"], 0.0) + p_sure, 3)
            parcalar.append({"scene_id": sid, "parca": i + 1,
                             "parca_sayisi": n, "sure_sn": p_sure,
                             "asset_id": sec["asset_id"],
                             "saglayici": sec.get("saglayici"),
                             "lisans": sec.get("lisans"), "atandi": True})
            # ⚠ Ayni varlik ARDIL parcada tekrar kullanilmasin (gorsel
            # tekrar); sira dondurulur.
            sira = [a for a in sira if a["asset_id"] != sec["asset_id"]] + \
                   [a for a in sira if a["asset_id"] == sec["asset_id"]]

    asan = [{"asset_id": a, "sure_sn": v} for a, v in sorted(kullanim.items())
            if v > tavan_sn + EPS]
    return {"ok": not sorunlar and not asan,
            "tavan_sn": tavan_sn, "parcalar": parcalar,
            "kullanim": kullanim, "asan": asan,
            "bolunen_sahne": bolunen, "sorunlar": sorunlar}


def dogrula(kullanim: dict, *,
            tavan_sn: float = KAYNAK_BASINA_TAVAN_SN) -> dict:
    """Nihai kullanim tavana UYUYOR mu? ⚠ Tolerans yalniz kayan nokta icin."""
    k = kullanim if isinstance(kullanim, dict) else {}
    asan = [{"asset_id": a, "sure_sn": round(_f(v), 3)}
            for a, v in sorted(k.items()) if _f(v) > tavan_sn + EPS]
    return {"ok": not asan, "tavan_sn": tavan_sn, "asan": asan,
            "kod": "" if not asan else KOD_VARLIK_YOK}


def kapsam_ozeti() -> dict:
    return {
        "sema_surum": SEMA_SURUM,
        "tavan_sn": KAYNAK_BASINA_TAVAN_SN,
        "tavan_yukseltilir": False,
        "ayni_kaynak_tekrar_ile_asilir": False,
        "deterministik": True, "rastgelelik": False,
        "stabil_kodlar": [KOD_VARLIK_YOK, KOD_SURE_BOZUK],
        "provenanssiz_varlik_atanir": False,
        "aga_cikar": False, "medya_acar": False, "dosya_yazar": False,
        "render_eder": False,
    }
