#!/usr/bin/env python3
"""FAZ R-1d-h — SIYAH/DONMUS KARE: ILK BOZULAN KATMANI KANITLA.

⚠ OLCULEN KUSUR (R-1d-g pilotu, job_1786725532851):
    POST-SIYAH-KARE  (fail): 28.458-28.667 · 30.917-31.417 ·
                             34.542-40.458  (5.92 sn)
    POST-DONMUS-KARE (warn): 34.542 (+5.83 sn)
Teslim edilen MP4'un ortasinda ~5.9 sn SIYAH + DONMUS bolum var. POST-QA
bunu yakaliyor ama HANGI KATMANDA olustugunu SOYLEMIYOR: kaynak klip mi,
segment uretimi mi, xfade zinciri mi?

Bu modul o soruyu deterministik olarak cevaplar: ayni olcum (blackdetect /
freezedetect) HER KATMANA ayri ayri uygulanir ve **ilk bozulan katman**
raporlanir. Boylece duzeltme dogru yere yapilir — tahminle degil.

⚠ Bu modul MEDYA ACMAZ, AG KULLANMAZ, DOSYA YAZMAZ. `kosucu` (ffmpeg
calistirici) DISARIDAN enjekte edilir; boylece karar mantigi MEDYASIZ test
edilir ve gercek olcum YALNIZCA uzak worker'da kosar.
"""
from __future__ import annotations

import re

SEMA_SURUM = "1.0.0"

# ── KATMAN SIRASI (uretim sirasiyla; ilk bozulan bu sirada aranir) ──
KATMANLAR = ("kaynak", "segment", "birlesik", "final")

# ── STABIL KODLAR ──
KOD_SIYAH = "KATMAN-SIYAH-KARE"
KOD_DONMUS = "KATMAN-DONMUS-KARE"
KOD_OLCULEMEDI = "KATMAN-OLCULEMEDI"
KOD_ATFEDILEMEDI = "KATMAN-ATFEDILEMEDI"

# Esikler qa_son ile AYNI (yeniden tanimlanmaz, kopyalanir ve BEYAN edilir).
SIYAH_FILTRE = "blackdetect=d=0.05:pix_th=0.10"
DONMUS_FILTRE = "freezedetect=n=0.003:d=1.0"


def siyah_komutu(yol):
    return ["ffmpeg", "-hide_banner", "-nostats", "-i", str(yol),
            "-vf", SIYAH_FILTRE, "-f", "null", "-"]


def donmus_komutu(yol):
    return ["ffmpeg", "-hide_banner", "-nostats", "-i", str(yol),
            "-vf", DONMUS_FILTRE, "-f", "null", "-"]


def _siyah_ayikla(stderr: str) -> list:
    out = []
    for m in re.finditer(r"black_start:([\d.]+)\s+black_end:([\d.]+)",
                         str(stderr or "")):
        b, e = float(m.group(1)), float(m.group(2))
        out.append({"bas": round(b, 3), "bitis": round(e, 3),
                    "sure": round(e - b, 3)})
    return out


def _donmus_ayikla(stderr: str) -> list:
    out = []
    for m in re.finditer(r"freeze_start:\s*([\d.]+)", str(stderr or "")):
        out.append({"bas": round(float(m.group(1)), 3)})
    return out


def olc(yol, *, kosucu) -> dict:
    """Tek dosyanin siyah/donmus araliklari. ⚠ Olculemezse UYDURULMAZ.

    `kosucu(komut) -> stderr` DISARIDAN verilir (bu modul surec ACMAZ).
    """
    try:
        s_err = kosucu(siyah_komutu(yol))
        d_err = kosucu(donmus_komutu(yol))
    except Exception as e:                                   # noqa: BLE001
        return {"olculdu": False, "kod": KOD_OLCULEMEDI,
                "neden": f"{type(e).__name__}", "yol": str(yol)}
    return {"olculdu": True, "yol": str(yol),
            "siyah": _siyah_ayikla(s_err), "donmus": _donmus_ayikla(d_err)}


def temiz_mi(olcum) -> bool:
    o = olcum if isinstance(olcum, dict) else {}
    if not o.get("olculdu"):
        return False                      # ⚠ Olculmeyen TEMIZ SAYILMAZ.
    return not (o.get("siyah") or o.get("donmus"))


def ilk_bozulan_katman(katman_olcumleri: dict) -> dict:
    """Uretim sirasinda ILK bozulan katmani bul. ⚠ Tahmin YOK.

    `katman_olcumleri`: {katman_adi: olc() ciktisi | [olc(), ...]}
    Bir katmanda BIRDEN COK dosya olabilir (ornegin segmentler); listedeki
    HERHANGI biri bozuksa katman bozuktur ve BOZUK OLANLAR raporlanir.

    ⚠ `final` bozuk ama ONCEKI katmanlarin HICBIRI olculemediyse hukum
    `KATMAN-ATFEDILEMEDI`dir — "herhalde xfade'dir" DENMEZ.
    """
    sonuc, bozuk_katman = {}, None
    for ad in KATMANLAR:
        ham = katman_olcumleri.get(ad)
        if ham is None:
            continue
        liste = ham if isinstance(ham, list) else [ham]
        olculdu = [o for o in liste if isinstance(o, dict) and o.get("olculdu")]
        bozuk = [o for o in olculdu if not temiz_mi(o)]
        sonuc[ad] = {"dosya": len(liste), "olculdu": len(olculdu),
                     "bozuk": len(bozuk),
                     "ornek": [{"yol": o.get("yol"),
                                "siyah": o.get("siyah"),
                                "donmus": o.get("donmus")} for o in bozuk[:3]]}
        if bozuk and bozuk_katman is None:
            bozuk_katman = ad
    if bozuk_katman is None:
        return {"bozuk": False, "katman": None, "kod": "", "katmanlar": sonuc}
    # Kod: siyah mi donmus mu (ikisi de varsa SIYAH onceliklidir — daha agir).
    ilk = sonuc[bozuk_katman]["ornek"][0] if sonuc[bozuk_katman]["ornek"] else {}
    kod = KOD_SIYAH if (ilk.get("siyah")) else KOD_DONMUS
    return {"bozuk": True, "katman": bozuk_katman, "kod": kod,
            "katmanlar": sonuc}


def atif(katman_olcumleri: dict) -> dict:
    """`final` bozuksa SUCU dogru katmana yaz; atfedilemezse ACIKCA soyle."""
    r = ilk_bozulan_katman(katman_olcumleri)
    fin = katman_olcumleri.get("final")
    fin_l = fin if isinstance(fin, list) else ([fin] if fin else [])
    fin_bozuk = any(isinstance(o, dict) and o.get("olculdu")
                    and not temiz_mi(o) for o in fin_l)
    if not fin_bozuk:
        return {**r, "final_bozuk": False, "atfedildi": bool(r["bozuk"])}
    onceki_olculdu = any(
        (katman_olcumleri.get(a) is not None)
        and any(isinstance(o, dict) and o.get("olculdu")
                for o in (katman_olcumleri[a]
                          if isinstance(katman_olcumleri[a], list)
                          else [katman_olcumleri[a]]))
        for a in KATMANLAR[:-1])
    if not onceki_olculdu:
        return {**r, "final_bozuk": True, "atfedildi": False,
                "kod": KOD_ATFEDILEMEDI, "katman": None}
    return {**r, "final_bozuk": True, "atfedildi": True}


def kapsam_ozeti() -> dict:
    return {
        "sema_surum": SEMA_SURUM,
        "katmanlar": list(KATMANLAR),
        "siyah_filtre": SIYAH_FILTRE, "donmus_filtre": DONMUS_FILTRE,
        "esik_qa_son_ile_ayni": True,
        "stabil_kodlar": [KOD_SIYAH, KOD_DONMUS, KOD_OLCULEMEDI,
                          KOD_ATFEDILEMEDI],
        "olculmeyen_temiz_sayilir": False,
        "tahmin_eder": False,
        "surec_acar": False, "aga_cikar": False, "dosya_yazar": False,
    }
