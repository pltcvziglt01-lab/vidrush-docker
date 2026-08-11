"""KAPSAM KAPISI — usable aday yoksa ne olur.

Degismez kural (kullanicinin acik istegi): "her sahne icin usable aday yoksa
SESSIZCE ALAKASIZ STOK KOYMA". 11 Agu'da tam bu oldu — footage bulunamayan
sahneye "ilgili gorunen" bir klip konuldu ve Tokyo belgeselinde Filipinler
mutfagi cikti.

Bu modul bosluk oldugunda ALAKASIZ MEDYA KOYMAK YERINE ne yapilacagini
soyluyor. Onerilen yedekler yalnizca GUVENLI turler:

  harita            — konum iddiasi varsa; veri kendi elimizde, telif yok
  belge-yakin-plan  — sayi/tarih iddiasi varsa; kendi urettigimiz grafik
  lisansli-arsiv    — daha genis sorguyla arsiv saglayicilarini tekrar dene
  motion-graphic    — hicbiri olmazsa: tipografi/veri gorseli (medya gerekmez)

Hicbir durumda "rastgele stok" onerilmiyor.
"""
from __future__ import annotations

import re

# Bir sahnenin kabul edilmesi icin gereken en dusuk toplam puan
KABUL_ESIGI = 45.0

FALLBACK_SIRASI = ("harita", "belge-yakin-plan", "lisansli-arsiv", "motion-graphic")

_SAYI = re.compile(r"\d[\d.,]*")


def fallback_oner(iddia_metni: str, varliklar: dict, sahne_amaci: str) -> dict:
    """Bosluk icin GUVENLI yedek oner. Alakasiz stok ASLA onerilmez."""
    yerler = varliklar.get("yerler") or []
    tarihler = (varliklar.get("tarihler") or []) + (varliklar.get("onyillar") or [])
    sayilar = _SAYI.findall(str(iddia_metni or ""))

    if sahne_amaci == "harita" or (yerler and sahne_amaci in ("establishing", "ortam")):
        return {"tur": "harita",
                "gerekce": f"konum iddiasi var ({yerler[:2]}) — harita kendi "
                           "urettigimiz grafik, telif riski yok",
                "parametre": {"yer": yerler[0] if yerler else "", "vurgu": True}}
    if sayilar or sahne_amaci == "belge":
        return {"tur": "belge-yakin-plan",
                "gerekce": f"{len(sayilar)} sayisal deger var — veri/belge sahnesi "
                           "medya gerektirmez",
                "parametre": {"sayilar": sayilar[:3]}}
    if tarihler or sahne_amaci == "arsiv":
        return {"tur": "lisansli-arsiv",
                "gerekce": f"tarih iddiasi var ({tarihler[:2]}) — arsiv "
                           "saglayicilarinda daha genis sorguyla tekrar denenmeli",
                "parametre": {"onyil": tarihler[0] if tarihler else "",
                              "saglayicilar": ["loc", "archive_org", "wikimedia"]}}
    return {"tur": "motion-graphic",
            "gerekce": "uygun ve lisansli medya bulunamadi; tipografi/veri "
                       "gorseli medya gerektirmez",
            "parametre": {}}


def sahne_kapsami(*, scene_id: str, sahne_amaci: str, adaylar: list,
                  secilen: list, iddia_metni: str = "",
                  varliklar: dict = None) -> dict:
    """Sahnenin kapsam durumu. bosluk=True ise render'a medya KOYULMAZ."""
    varliklar = varliklar or {}
    kullanilabilir = [a for a in adaylar if a.render_kullanilabilir]
    lisans_reddi = [a for a in adaylar if not a.render_kullanilabilir]
    esik_alti = [a for a in kullanilabilir if a.toplam_skor < KABUL_ESIGI]

    if secilen:
        return {"scene_id": scene_id, "bosluk": False,
                "aday": len(adaylar), "kullanilabilir": len(kullanilabilir),
                "lisans_reddi": len(lisans_reddi),
                "secilen": secilen[0].asset_id,
                "secilen_puan": secilen[0].toplam_skor,
                "secilen_saglayici": secilen[0].saglayici}

    if not adaylar:
        sebep = "hicbir saglayici aday dondurmedi"
    elif not kullanilabilir:
        sebep = (f"{len(adaylar)} adayin tamami lisans/guvenlik duvarinda "
                 f"reddedildi")
    elif esik_alti:
        sebep = (f"{len(kullanilabilir)} lisansli aday var ama hepsi kabul "
                 f"esiginin altinda (en yuksek "
                 f"{max(a.toplam_skor for a in kullanilabilir):.1f} < {KABUL_ESIGI})")
    else:
        sebep = "saglayici kotasi nedeniyle secim yapilamadi"

    return {"scene_id": scene_id, "bosluk": True, "sebep": sebep,
            "aday": len(adaylar), "kullanilabilir": len(kullanilabilir),
            "lisans_reddi": len(lisans_reddi),
            "onerilen_fallback": fallback_oner(iddia_metni, varliklar, sahne_amaci)}


def kapsam_ozeti(manifest) -> dict:
    """Tum kosunun kapsam tablosu."""
    # ⚠ Toplam sahne sayisi ADAYLARDAN turetilemez: hicbir saglayici cevap
    # vermezse aday listesi bos olur, sahne sayisi 0 gorunur ve oran negatife
    # duser (canli kuru testte "kapsanan: -3, oran: -2.0" cikti).
    sahne_bazinda = manifest.sahne_bazinda()
    toplam = int(getattr(manifest, "sahne_sayisi", 0) or len(sahne_bazinda) or 0)
    bosluk = min(len(manifest.kapsam_bosluklari), toplam) if toplam else \
        len(manifest.kapsam_bosluklari)
    if not toplam:
        return {"sahne": 0, "kapsanan": 0, "bosluk": bosluk,
                "kapsam_orani": 0.0,
                "fallback_dagilimi": _fallback_dag(manifest.kapsam_bosluklari)}
    return {"sahne": toplam,
            "kapsanan": max(0, toplam - bosluk),
            "bosluk": bosluk,
            "kapsam_orani": round(max(0.0, (toplam - bosluk) / toplam), 3),
            "fallback_dagilimi": _fallback_dag(manifest.kapsam_bosluklari)}


def _fallback_dag(bosluklar: list) -> dict:
    d: dict = {}
    for b in bosluklar:
        f = b.get("onerilen_fallback")
        ad = f.get("tur") if isinstance(f, dict) else str(f or "belirsiz")
        d[ad] = d.get(ad, 0) + 1
    return d
