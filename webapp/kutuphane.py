#!/usr/bin/env python3
"""FAZ R-1c-b — TENANT BASINA SON 3 KABUL EDILMIS FINAL VIDEO.

⚠ BU MODUL MEDYA ACMAZ, DOSYA SILMEZ, AG KULLANMAZ. Yalnizca METADATA
yasam dongusunu yonetir. Gercek silme, dondurdugu SILME KUYRUGUNU isleyen
remote lifecycle isinin isidir — "hemen sil" YAPILMAZ.

── SOZLESME ──
  · Kutuphaneye YALNIZCA basarili VE QA'dan KABUL EDILMIS final video girer.
    Basarisiz / QA reddi / render yarim -> GIRMEZ (`kabul_edilebilir_mi`).
  · Tenant basina EN FAZLA `TAVAN` (3) kayit tutulur; 4. kabul edilince EN
    ESKI kayit SILME KUYRUGUNA alinir (kutuphaneden dusurulur).
  · Signed URL SAKLANMAZ; `listele()` sirasinda TALEP ANINDA uretilir ve
    yalnizca kaydin SAHIBI olan tenant icin verilir.
  · Metadata QA / provenance / provider / model / credit / zaman damgalari
    tasir; eksik alan UYDURULMAZ.
"""
from __future__ import annotations

from typing import Callable, Optional

SEMA_SURUM = "1.0.0"

# Tenant basina saklanan kabul edilmis final video sayisi.
TAVAN = 3

# Kutuphaneye girmeye HAK KAZANAN is durumlari.
KABUL_DURUMLARI = ("bitti",)
# QA hukmu bunlardan biri olmalidir. ⚠ "WARN" KABUL EDILIR (uyari kaliteyi
# dusurur ama teslim edilebilir); "FAIL" ve olculmemis olan EDILMEZ.
KABUL_QA = ("PASS", "WARN")

# ⚠ FAZ Y-1 — KURGU (EDIT) QA HUKMU DE BAGLAYICIDIR.
# OLCULEN KUSUR (`Y1-KARAR-UYGULANMIYOR`, is job_1786783360170_ui7114_9c21aa):
#     EDIT PLANI: QA=FAIL render_edilebilir=False sahne=20
#     TESLIM job_1786783360170_ui7114_9c21aa: KABUL
# `edit_kopru.plan_kur()` dokumani "QA-ON FAIL ISE RENDER BASLATILMAZ" diyor
# ve `render_edilebilir=False` donuyordu; ama bu karar YALNIZCA rapor alanina
# yaziliyor, kabul kapisi onu HIC OKUMUYORDU. Sonuc: kurgu QA'si FAIL veren
# video "kabul edilmis final" sayilip son-3 kutuphanesine giriyordu.
KURGU_QA_RED = "Y1-KURGU-QA-FAIL"


def _s(v) -> str:
    return str(v or "").strip()


def kabul_edilebilir_mi(kayit: dict) -> dict:
    """Bu is kutuphaneye girebilir mi? ⚠ Belirsizse GIRMEZ."""
    k = kayit if isinstance(kayit, dict) else {}
    durum = _s(k.get("durum") or k.get("status")).lower()
    qa = _s((k.get("qa") or {}).get("durum")
            if isinstance(k.get("qa"), dict) else k.get("qa")).upper()
    video = _s(k.get("video") or k.get("video_url"))
    eksik = []
    if durum not in KABUL_DURUMLARI:
        eksik.append(f"DURUM:{durum or 'yok'}")
    if not video:
        eksik.append("VIDEO-YOK")
    if qa not in KABUL_QA:
        # ⚠ QA olculmemisse KABUL EDILMEZ — "muhtemelen iyidir" DENMEZ.
        eksik.append(f"QA:{qa or 'olculmedi'}")
    # ⚠ FAZ Y-1: KURGU QA KAPISI (fail-closed).
    # `edit_plani` alani VARSA hukmu BAGLAYICIDIR: `render_edilebilir=False`
    # ise (kurgu QA FAIL ya da plan hic kurulamadi/MEDYA-YOK) is kabul
    # EDILMEZ. Alan YOKSA eski kayitlar bozulmasin diye kapi UYGULANMAZ —
    # sessiz siki(las)tirma YOK, acik ve geriye uyumlu bir karar.
    ep = k.get("edit_plani")
    if isinstance(ep, dict) and ep:
        if not ep.get("render_edilebilir"):
            _kqa = _s((ep.get("qa") or {}).get("durum")
                      if isinstance(ep.get("qa"), dict) else "").upper()
            _nd = _s(ep.get("neden")) or _kqa or "render_edilebilir=False"
            eksik.append(f"{KURGU_QA_RED}:{_nd}")
    return {"kabul": not eksik, "neden": "+".join(eksik)}


def kayit_kur(*, is_id: str, tenant_id: str, dosya: str, kayit: dict,
              kabul_zamani: float) -> dict:
    """Kutuphane kaydi — QA/provenance/provider/model/credit/zaman.

    ⚠ Signed URL BURADA URETILMEZ ve SAKLANMAZ (talep aninda uretilir).
    ⚠ Eksik alan UYDURULMAZ; bilinmiyorsa None/bos kalir.
    """
    k = kayit if isinstance(kayit, dict) else {}
    prov = k.get("provenance") if isinstance(k.get("provenance"), dict) else {}
    qa = k.get("qa") if isinstance(k.get("qa"), dict) else {}
    return {
        "is_id": _s(is_id), "tenant_id": _s(tenant_id),
        "dosya": _s(dosya),
        "kabul_zamani": float(kabul_zamani),
        "olusturma_zamani": k.get("olusturma_zamani"),
        "sure_sn": k.get("duration") or k.get("sure_sn"),
        "qa": {"durum": _s(qa.get("durum")).upper() or None,
               "fail": qa.get("fail"), "warn": qa.get("warn"),
               "puan": qa.get("puan")},
        "provenance": {
            "provider_used": _s(prov.get("provider_used")) or None,
            "fallback_reason": _s(prov.get("fallback_reason")) or None,
            "model": _s(prov.get("model")) or None,
            "kredi_tuketildi": prov.get("kredi_tuketildi"),
            "lisanslar": list(prov.get("lisanslar") or []),
            "kaynaklar": list(prov.get("kaynaklar") or []),
        },
    }


def ekle(kutuphane: dict, kayit: dict, *, tavan: int = TAVAN) -> dict:
    """Kabul edilmis videoyu ekle; tavani asan EN ESKIYI silme kuyruguna al.

    `kutuphane`: {tenant_id: [kayit, ...]} — cagiran tarafta saklanir.
    ⚠ Bu fonksiyon DOSYA SILMEZ; yalnizca `silinecek` listesi doner.
    """
    t = _s(kayit.get("tenant_id"))
    if not t:
        return {"eklendi": False, "neden": "TENANT-YOK", "silinecek": []}
    liste = [x for x in (kutuphane.get(t) or []) if isinstance(x, dict)]
    # Ayni is iki kez eklenmesin (idempotan davranis).
    liste = [x for x in liste if _s(x.get("is_id")) != _s(kayit.get("is_id"))]
    liste.append(kayit)
    # EN YENI once.
    liste.sort(key=lambda x: float(x.get("kabul_zamani") or 0), reverse=True)
    tut, dus = liste[:max(1, int(tavan))], liste[max(1, int(tavan)):]
    kutuphane[t] = tut
    return {"eklendi": True, "neden": "",
            "kutuphane": tut,
            # ⚠ GUVENLI YASAM DONGUSU: hemen silinmez, KUYRUGA alinir.
            "silinecek": [{"tenant_id": t, "is_id": _s(x.get("is_id")),
                           "dosya": _s(x.get("dosya")),
                           "sebep": "TAVAN-ASILDI"} for x in dus]}


def listele(kutuphane: dict, tenant_id: str, *,
            imzalayici: Optional[Callable] = None) -> dict:
    """Dashboard/API listeleme sozlesmesi.

    ⚠ TENANT KORUMALI: yalnizca `tenant_id`in KENDI kayitlari doner.
    ⚠ Signed URL TALEP ANINDA uretilir; imzalayici yoksa `video_url` None
    kalir ve `imzalanamadi` bayragi ACIKCA yazilir (sessiz bos link YOK).
    """
    t = _s(tenant_id)
    if not t:
        return {"ok": False, "neden": "TENANT-YOK", "videolar": []}
    liste = [x for x in (kutuphane.get(t) or []) if isinstance(x, dict)]
    cikti = []
    for x in liste:
        # ⚠ Ikinci savunma hatti: kaydin sahibi gercekten bu tenant mi?
        if _s(x.get("tenant_id")) != t:
            continue
        url = None
        if callable(imzalayici):
            try:
                url = imzalayici(_s(x.get("dosya"))) or None
            except Exception:                             # noqa: BLE001
                url = None
        cikti.append({
            "is_id": x.get("is_id"), "dosya": x.get("dosya"),
            "video_url": url, "imzalanamadi": url is None,
            "kabul_zamani": x.get("kabul_zamani"),
            "sure_sn": x.get("sure_sn"),
            "qa": x.get("qa"), "provenance": x.get("provenance"),
        })
    return {"ok": True, "neden": "", "tavan": TAVAN,
            "sayi": len(cikti), "videolar": cikti}


def kapsam_ozeti() -> dict:
    return {
        "sema_surum": SEMA_SURUM,
        "tavan": TAVAN,
        "kabul_durumlari": list(KABUL_DURUMLARI),
        "kabul_qa": list(KABUL_QA),
        "medya_acar": False, "dosya_siler": False, "aga_cikar": False,
        "signed_url_saklanir": False,
        "signed_url_talep_aninda": True,
        "tenant_korumali": True,
        "silme": "kuyruga alinir; gercek silme remote lifecycle isinin isi",
    }
