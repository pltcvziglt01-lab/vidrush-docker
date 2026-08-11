#!/usr/bin/env python3
"""FAZ E PILOT — Apollo 11 arastirma manifesti + UCRETSIZ dogrulama.

Konu: Apollo 11'in inisindeki kritik son dakikalar.

⚠ UCRETLI API YOK. Faz A'nin `researcher.py`'si OpenAI web_search kullaniyor;
burada onu CAGIRMIYORUZ. Iddialar elle yazildi, dogrulama `fact_checker`'in
UCRETSIZ yolundan geciyor (sayfa getir + sayi/ifade esleme, LLM yok).

Her KRITIK iddia icin iki BAGIMSIZ alan adi zorunlu (kullanicinin sarti).

Kosum: python3 webapp/testler/faz_e_manifest.py [--cikti yol.json]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)

from arastirma import fact_checker, manifests  # noqa: E402
from arastirma.butce import KosuSiniri  # noqa: E402
from arastirma.cache import MaliyetDefteri, Onbellek  # noqa: E402

ERISIM = "2026-08-11"

# ── KAYNAKLAR ──
# ⚠ OLU BAGLANTI DERSI (11 Agu): ilk surumde `hq.nasa.gov/alsj/...` kullandim.
# Sayfalar HTTP 200 donuyordu AMA hepsi ayni 12.102 karakterlik JS kabuguna
# yonleniyordu; icerikte ne "1202" ne "Tranquility Base" vardi. Yani atif
# gorunurde gecerli, gercekte BOSTU. fact_checker bunu yakaladi (6/7 cozulmedi).
# ALSJ NASA tarafinda su adrese tasinmis; asagidaki her URL icerik icin
# TEK TEK dogrulandi (token matrisi ile).
ALSJ_ALARM = ("https://www.nasa.gov/wp-content/uploads/static/history/alsj/a11/"
              "a11.1201-pa.html",
              "Apollo 11 Lunar Surface Journal — Program Alarms 1201/1202",
              "birincil-belge")
NASA_50YIL = ("https://www.nasa.gov/history/"
              "50-years-ago-one-small-step-one-giant-leap/",
              "NASA — 50 Years Ago: One Small Step, One Giant Leap",
              "resmi-kurum")
NASA_WIDE = ("https://www.nasa.gov/missions/apollo/apollo-11/"
             "wide-awake-on-the-sea-of-tranquillity/",
             "NASA — Wide Awake on the Sea of Tranquillity", "resmi-kurum")
NASA_GENEL = ("https://www.nasa.gov/history/apollo-11-mission-overview/",
              "NASA — Apollo 11 Mission Overview", "resmi-kurum")
# BAGIMSIZ ALAN: Royal Museums Greenwich (nasa.gov'dan bagimsiz muze arsivi)
RMG = ("https://www.rmg.co.uk/stories/space-astronomy/"
       "apollo-11-moon-landing-minute-minute",
       "Royal Museums Greenwich — Apollo 11 Moon landing: minute by minute",
       "muze-arsiv")
# BAGIMSIZ ALAN: MIT (rehber bilgisayar yazilimini gelistiren kurum)
MIT = ("https://news.mit.edu/2019/behind-scenes-apollo-mission-0718",
       "MIT News — Behind the scenes of the Apollo mission at MIT", "akademik")


def _k(t: tuple, alinti: str = "", birincil: bool = False) -> manifests.Kaynak:
    return manifests.Kaynak(url=t[0], baslik=t[1], tur=t[2],
                            erisim_tarihi=ERISIM, birincil=birincil,
                            alinti=alinti)


def manifest_kur() -> manifests.ArastirmaManifesti:
    """Iddialar.

    ⚠ DIL KOPRUSU: sayfalar INGILIZCE, anlatim TURKCE. Ucretsiz dogrulayici
    iddia metnindeki ayirt edici SAYI ve kelimeleri sayfada ariyor; salt Turkce
    yazilmis iddia %14 kelime ortusmesiyle dusuyordu. Bu yuzden iddialar
    dogrulanabilir INGILIZCE terimi (1202, "Tranquility Base", "powered
    descent") ICINDE tasiyor. Anlatim metni ayri; oradaki dil tamamen Turkce.
    """
    iddialar = [
        manifests.Iddia(
            fact_id="f001",
            metin="Eagle ay modulu 20 July 1969 gunu Ay'a indi.",
            kategori="tarih", kritik=True,
            kaynaklar=[_k(NASA_50YIL, birincil=True), _k(RMG)]),
        manifests.Iddia(
            fact_id="f002",
            metin="Inis sirasinda rehber bilgisayar 1202 program alarm verdi.",
            kategori="teknik", kritik=True,
            kaynaklar=[_k(ALSJ_ALARM, birincil=True), _k(RMG), _k(MIT)]),
        manifests.Iddia(
            fact_id="f003",
            metin="Inis sirasinda 1201 program alarm da goruldu.",
            kategori="teknik", kritik=True,
            kaynaklar=[_k(ALSJ_ALARM, birincil=True), _k(RMG)]),
        manifests.Iddia(
            fact_id="f004",
            metin="Armstrong took manual control of the lunar module during "
                  "the final descent.",
            kategori="teknik", kritik=False,
            kaynaklar=[_k(NASA_50YIL, birincil=True), _k(RMG)]),
        manifests.Iddia(
            fact_id="f005",
            metin="Houston, Tranquility Base here. The Eagle has landed.",
            kategori="alinti", kritik=True,
            kaynaklar=[_k(NASA_WIDE, birincil=True), _k(RMG)]),
        manifests.Iddia(
            fact_id="f006",
            metin="Powered descent yaklasik 12 dakika surdu.",
            kategori="rakam", kritik=True,
            kaynaklar=[_k(NASA_GENEL, birincil=True), _k(RMG)]),
        manifests.Iddia(
            fact_id="f007",
            # Turkce-Ingilizce karisik yazim %14 ortusme veriyordu; tamamen
            # Ingilizce yazildi. Yine de TEK alan (nasa.gov) — anlatimda
            # KULLANILMIYOR, yalnizca sinirin belgesi olarak duruyor.
            metin="The landing site was a field of boulders near West Crater.",
            kategori="cografya", kritik=False,
            kaynaklar=[_k(NASA_50YIL, birincil=True), _k(NASA_WIDE)]),
    ]
    return manifests.ArastirmaManifesti(
        konu="Apollo 11 inisindeki kritik son dakikalar",
        iddialar=iddialar, olusturma=ERISIM,
        arama_sorgulari=["apollo 11 landing 1202 program alarm",
                         "apollo 11 powered descent duration",
                         "apollo 11 tranquility base eagle has landed"],
        notlar=[
            "Arastirma UCRETSIZ yoldan dogrulandi: sayfa getir + sayi/ifade "
            "esleme. LLM cagrisi 0.",
            "Yakit marji rakamlari (25 sn / 45 sn) kaynaklar arasinda "
            "CELISKILI oldugu icin iddia olarak alinmadi ve anlatimda gecmiyor.",
            "f006: kesin rakam 756.3 saniye YALNIZCA nasa.gov'da bulundu; "
            "bagimsiz ikinci alanda dogrulanamadigi icin anlatimda kesin "
            "saniye DEGIL 'yaklasik 12 dakika' kullanildi.",
            "f007: iki kaynak da nasa.gov; bagimsiz ikinci alan bulunamadi, "
            "bu yuzden kritik isaretlenmedi ve anlatimda temkinli ifade edildi.",
        ])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cikti", default=os.path.join(
        os.path.dirname(KOK), "cikti", "faz_e", "manifest.json"))
    a = ap.parse_args()
    os.makedirs(os.path.dirname(a.cikti), exist_ok=True)

    m = manifest_kur()
    m.dogrula()
    print(f"konu: {m.konu}")
    print(f"iddia: {len(m.iddialar)}  (kritik: "
          f"{sum(1 for i in m.iddialar if i.kritik)})")

    # UCRETSIZ dogrulama: llm_istek VERILMIYOR -> LLM yolu hic acilmaz
    onbellek = Onbellek()
    defter = MaliyetDefteri()
    sinir = KosuSiniri(toplam_sure_sn=420)
    print("\n── kaynak dogrulama (ucretsiz: sayfa + ifade/sayi esleme) ──")
    rapor = fact_checker.dogrula(m, bugun=ERISIM, onbellek=onbellek,
                                 defter=defter, sinir=sinir)

    for i in m.iddialar:
        alanlar = sorted({k.alan for k in i.kaynaklar})
        print(f"  {i.fact_id}  {i.guven:12} kritik={str(i.kritik):5} "
              f"alan={len(alanlar)} {alanlar}")
        if i.celiski_notu:
            print(f"      celiski: {i.celiski_notu[:110]}")

    # Kritik iddialarda IKI bagimsiz alan sarti
    eksik = [i.fact_id for i in m.iddialar
             if i.kritik and len({k.alan for k in i.kaynaklar}) < 2]
    dogrulanan = [i.fact_id for i in m.iddialar if i.guven == "dogrulandi"]
    cozulmeyen = [i.fact_id for i in m.iddialar if i.guven == "cozulmedi"]

    print(f"\n  dogrulandi: {len(dogrulanan)}/{len(m.iddialar)}  {dogrulanan}")
    if cozulmeyen:
        print(f"  cozulmedi : {cozulmeyen}")
    print(f"  iki-alan sarti eksik: {eksik or 'YOK'}")

    with open(a.cikti, "w", encoding="utf-8") as f:
        json.dump({"manifest": m.sozluk() if hasattr(m, "sozluk") else None,
                   "rapor": rapor,
                   "iddialar": [{"fact_id": i.fact_id, "metin": i.metin,
                                 "guven": i.guven, "kritik": i.kritik,
                                 "kategori": i.kategori,
                                 "celiski_notu": i.celiski_notu,
                                 "kaynaklar": [{"url": k.url, "baslik": k.baslik,
                                                "tur": k.tur, "alan": k.alan,
                                                "birincil": k.birincil}
                                               for k in i.kaynaklar]}
                                for i in m.iddialar],
                   "notlar": m.notlar}, f, ensure_ascii=False, indent=1)
    print(f"\n  manifest: {os.path.abspath(a.cikti)}")
    return 0 if not eksik else 1


if __name__ == "__main__":
    sys.exit(main())
