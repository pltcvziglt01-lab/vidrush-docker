#!/usr/bin/env python3
"""FAZ E PILOT — gercek lisansli medya avi + CESITLILIK ve KONU denetimi.

Faz B avcisini CANLI kosar, lisans duvarindan gecenlere VIDEO SEVIYESI konu
kapisi uygular, indirir ve kullanicinin sartlarini olcer:

  - en az 8 BENZERSIZ varlik (icerik hash'i)
  - ideal 3 saglayici, tek saglayici <= %40
  - ⚠ AYNI ARSIVIN AYNALARI CESITLILIK SAYILMAZ (kullanicinin acik sarti):
    Apollo goruntulerinin cogu NASA arsivinden. wikimedia'dan gelen bir NASA
    fotografi ile archive_org'dan gelen ayni NASA fotografi "iki saglayici"
    gorunur ama TEK arsivdir. `arsiv_kimligi()` bunu ayirir; NASA hakimiyeti
    kapsam BOSLUGU olarak yazilir ve kendi grafiklerimizle doldurulur.

Kosum: python3 webapp/testler/faz_e_medya.py [--sinir-sn 1200]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)

from arastirma.butce import KosuSiniri  # noqa: E402
from arastirma.cache import MaliyetDefteri, Onbellek  # noqa: E402
from medya import avci, guvenlik, indirme, providers, siralama  # noqa: E402,F401

ERISIM = "2026-08-11"
CIKTI = os.path.join(os.path.dirname(KOK), "cikti", "faz_e")
MEDYA_DIZIN = os.path.join(CIKTI, "medya")

# ⚠ SORGU DERSI (canli olcum): genel sorgular ("lunar surface craters",
# "Neil Armstrong portrait") arsivlerden ilgisiz sonuc getirdi ve konu
# kapisinda %89 red aldi. NASA/Wikimedia arsivinde Apollo 11 fotograflari
# "AS11-<magazin>-<kare>" kalibiyla ve "Apollo 11" ifadesiyle etiketli;
# sorgular bu kalibi hedefliyor. Sorgular INGILIZCE: arsiv etiketleri Ingilizce,
# Turkce sorgu sifir sonuc dondurur.
SAHNELER = [
    {"scene_id": "sE01", "fact_id": "f001", "sahne_amaci": "establishing",
     "iddia_metni": "Apollo 11 launch Saturn V July 1969", "medya_turu": "image"},
    {"scene_id": "sE02", "fact_id": "f006", "sahne_amaci": "establishing",
     "iddia_metni": "Apollo 11 lunar module Eagle lunar orbit", "medya_turu": "image"},
    {"scene_id": "sE03", "fact_id": "f002", "sahne_amaci": "arsiv",
     "iddia_metni": "Apollo 11 mission control Houston flight controllers",
     "medya_turu": "image"},
    {"scene_id": "sE04", "fact_id": "f003", "sahne_amaci": "belge",
     "iddia_metni": "Apollo guidance computer DSKY lunar module",
     "medya_turu": "image"},
    {"scene_id": "sE05", "fact_id": "f004", "sahne_amaci": "detay",
     "iddia_metni": "AS11 Apollo 11 Armstrong lunar module cabin",
     "medya_turu": "image"},
    {"scene_id": "sE06", "fact_id": "f007", "sahne_amaci": "kanit",
     "iddia_metni": "Apollo 11 landing site Sea of Tranquility lunar surface",
     "medya_turu": "image"},
    {"scene_id": "sE07", "fact_id": "f005", "sahne_amaci": "kanit",
     "iddia_metni": "Apollo 11 bootprint lunar surface soil", "medya_turu": "image"},
    {"scene_id": "sE08", "fact_id": "f005", "sahne_amaci": "kapanis",
     "iddia_metni": "AS11 Apollo 11 lunar module on the Moon", "medya_turu": "image"},
    {"scene_id": "sE09", "fact_id": "f001", "sahne_amaci": "detay",
     "iddia_metni": "Apollo 11 Earth from lunar orbit", "medya_turu": "image"},
    {"scene_id": "sE10", "fact_id": "f004", "sahne_amaci": "detay",
     "iddia_metni": "Apollo 11 Aldrin lunar surface visor", "medya_turu": "image"},
    {"scene_id": "sE11", "fact_id": "f002", "sahne_amaci": "arsiv",
     "iddia_metni": "Apollo 11 crew lunar module simulator training",
     "medya_turu": "image"},
    {"scene_id": "sE12", "fact_id": "f006", "sahne_amaci": "detay",
     "iddia_metni": "Apollo 11 lunar module descent stage engine",
     "medya_turu": "image"},
    {"scene_id": "sE13", "fact_id": "f003", "sahne_amaci": "belge",
     "iddia_metni": "Apollo 11 lunar module pilot checklist page",
     "medya_turu": "image"},
    {"scene_id": "sE14", "fact_id": "f007", "sahne_amaci": "harita",
     "iddia_metni": "Apollo 11 lunar landing site map chart", "medya_turu": "image"},
    {"scene_id": "sE15", "fact_id": "f005", "sahne_amaci": "kanit",
     "iddia_metni": "Apollo 11 plaque lunar module leg", "medya_turu": "image"},
    {"scene_id": "sE16", "fact_id": "f001", "sahne_amaci": "arsiv",
     "iddia_metni": "Apollo 11 Saturn V rollout launch pad", "medya_turu": "image"},
    {"scene_id": "sE17", "fact_id": "f004", "sahne_amaci": "detay",
     "iddia_metni": "AS11 Apollo 11 lunar surface experiment package",
     "medya_turu": "image"},
    {"scene_id": "sE18", "fact_id": "f006", "sahne_amaci": "establishing",
     "iddia_metni": "Apollo 11 lunar module ascent stage rendezvous",
     "medya_turu": "image"},
    # ⚠ KOTA ARITMETIGI: saglayici tavani floor(sahne*0.40). 18 sahnede tavan 7
    # ve 8 gercek varlik sartina ulasilamiyordu. Sahne sayisi 25'e cikarilarak
    # tavan 10'a yukseltildi. NASA arsivindeki Apollo 11 kareleri "AS11-<mag>"
    # kalibinda numaralandigi icin sorgular magazin numaralarini hedefliyor.
    {"scene_id": "sE19", "fact_id": "f005", "sahne_amaci": "kanit",
     "iddia_metni": "AS11-40 Apollo 11 lunar surface", "medya_turu": "image"},
    {"scene_id": "sE20", "fact_id": "f004", "sahne_amaci": "detay",
     "iddia_metni": "AS11-44 Apollo 11 lunar module", "medya_turu": "image"},
    {"scene_id": "sE21", "fact_id": "f007", "sahne_amaci": "kanit",
     "iddia_metni": "AS11-37 Apollo 11 lunar surface", "medya_turu": "image"},
    {"scene_id": "sE22", "fact_id": "f001", "sahne_amaci": "arsiv",
     "iddia_metni": "Apollo 11 Saturn V launch tower flame", "medya_turu": "image"},
    {"scene_id": "sE23", "fact_id": "f002", "sahne_amaci": "arsiv",
     "iddia_metni": "Apollo 11 mission control celebration consoles",
     "medya_turu": "image"},
    {"scene_id": "sE24", "fact_id": "f006", "sahne_amaci": "detay",
     "iddia_metni": "Apollo 11 command module Columbia interior",
     "medya_turu": "image"},
    {"scene_id": "sE25", "fact_id": "f003", "sahne_amaci": "belge",
     "iddia_metni": "Apollo 11 lunar module descent stage detail",
     "medya_turu": "image"},
    # ⚠ PARLAKLIK DERSI (canli olcum): "AS11-41-*" yorunge kareleri %90 bos
    # uzay; ortalama luma 27-34 ve gamma ile ancak 41-46'ya cikiyor. Bir
    # belgeselde tam kare olarak kullanilamazlar (blackdetect hakli).
    # Bu sorgular AYDINLIK konulari hedefliyor: gunduz firlatma, kapali
    # mekan kontrol odasi, ekip portresi, gunes altindaki LM.
    {"scene_id": "sE26", "fact_id": "f001", "sahne_amaci": "arsiv",
     "iddia_metni": "Apollo 11 crew portrait Armstrong Collins Aldrin",
     "medya_turu": "image"},
    {"scene_id": "sE27", "fact_id": "f002", "sahne_amaci": "arsiv",
     "iddia_metni": "Apollo mission control room consoles interior",
     "medya_turu": "image"},
    {"scene_id": "sE28", "fact_id": "f001", "sahne_amaci": "establishing",
     "iddia_metni": "Apollo 11 Saturn V launch daylight smoke tower",
     "medya_turu": "image"},
    {"scene_id": "sE29", "fact_id": "f004", "sahne_amaci": "detay",
     "iddia_metni": "Apollo 11 astronaut spacesuit training facility",
     "medya_turu": "image"},
    {"scene_id": "sE30", "fact_id": "f006", "sahne_amaci": "detay",
     "iddia_metni": "Apollo 11 lunar module sunlit surface astronaut",
     "medya_turu": "image"},
    {"scene_id": "sE31", "fact_id": "f003", "sahne_amaci": "belge",
     "iddia_metni": "Apollo guidance computer DSKY panel museum",
     "medya_turu": "image"},
    {"scene_id": "sE32", "fact_id": "f005", "sahne_amaci": "kanit",
     "iddia_metni": "Apollo 11 commemorative plaque lunar module ladder",
     "medya_turu": "image"},
    {"scene_id": "sE33", "fact_id": "f007", "sahne_amaci": "harita",
     "iddia_metni": "Apollo 11 traverse map lunar module surface chart",
     "medya_turu": "image"},
]

# ═══════════ VIDEO SEVIYESI KONU KAPISI ═══════════
# ⚠ Faz B'nin genel alaka kapisi TEK terim eslesmesiyle yetiniyor; bir belgesel
# icin YETERSIZ. Canli olcum (11 Agu) neyi gecirdigi:
#   "Apollo, Armstrong County, Pennsylvania" -> 'apollo'+'armstrong' tuttu.
#      Pennsylvania'da Apollo adli bir KASABA var; en tehlikeli yanlis pozitif.
#   "Drone view of a city (Unsplash)"        -> genel terimle gecti
#   "AS09-25-3683 - Apollo 9"                -> YANLIS GOREV
#   "S45-38-009 - STS-45 crew portrait"      -> Uzay Mekigi, Apollo degil
#   "MAJESTIC 12 Files", "Pit 10. Human cranium" -> tamamen ilgisiz
# Faz B'nin genel kapisi DEGISMIYOR (200 test yesil); bu kapi onun UZERINE biner.

# 1) Metadata'da EN AZ BIRI gecmeli — konu capasi
# ⚠ IKINCI TUR SIZINTI (olculdu): capa listesinde "lunar" ve "lunar orbit"
# vardi ve sunlari gecirdi:
#   "Gateway and Orion in lunar orbit (3).jpg"  -> ARTEMIS donemi araci, 1969 degil
#   "Lunar eclipse close-up - India.jpg"        -> ay tutulmasi fotografi
# Tek kelime "lunar" konu capasi DEGIL. Capalar artik IFADE duzeyinde ve
# Apollo 11'e ozgu; ayrica modern donanim adlari yasakli listeye eklendi.
ZORUNLU_IFADELER = (
    "apollo 11", "apollo-11", "apollo11", "as11-",
    "lunar module", "lunar surface", "lunar soil", "lunar dust",
    "sea of tranquility", "tranquility base", "moon landing",
    "mission control", "flight controller", "guidance computer", "dsky",
    "saturn v", "command module", "descent stage", "ascent stage",
)
# 2) Ayni serinin BASKA numarasi reddedilir (Apollo 9/6/13 != Apollo 11)
SERI_ADI = "apollo"
SERI_NO = "11"
# 3) Konu disi programlar
YASAK_PROGRAM = ("sts-", "space shuttle", "gemini ", "mercury-", "skylab",
                 "soyuz", "artemis", "gateway", "orion", "sls ", "starship",
                 "international space station", "iss ", "crew dragon",
                 "eclipse", "telescope")


def konu_kapisi(aday) -> tuple:
    """Belgesel kesinligi: aday GERCEKTEN Apollo 11 konusuna ait mi?"""
    md = f"{aday.baslik} {aday.aciklama} {getattr(aday, 'konum', '')}".lower()
    if not md.strip():
        return False, "metadata bos"
    for p in YASAK_PROGRAM:
        if p in md:
            return False, f"konu disi program: '{p.strip()}'"
    numaralar = re.findall(
        rf"(?<![0-9a-z]){SERI_ADI}\s*-?\s*(\d{{1,2}})(?![0-9])", md)
    if numaralar and SERI_NO not in numaralar:
        return False, f"yanlis gorev: apollo {sorted(set(numaralar))}"
    capa = [i for i in ZORUNLU_IFADELER if i in md]
    if not capa:
        return False, "konu capasi yok (apollo 11 / lunar / mission control ...)"
    return True, f"capa: {capa[:3]}"


def arsiv_kimligi(v) -> str:
    """Varligin GERCEK kaynak arsivi. Saglayici yalnizca AYNA olabilir."""
    metin = " ".join(str(x or "") for x in (
        getattr(v, "eser_sahibi", ""), getattr(v, "baslik", ""),
        getattr(v, "aciklama", ""), getattr(v, "orijinal_url", ""))).lower()
    # ⚠ "AS11-43-6352" gibi NASA katalog numaralari eser_sahibi "unknown author"
    # olarak geliyordu ve arsiv NASA sayilmiyordu. Bu, arsiv hakimiyetini
    # OLDUGUNDAN AZ gosteriyordu — tam tersini yapmaya calisiyoruz.
    if re.search(r"\bnasa\b|johnson space|jsc|gsfc|jpl|apollo archive"
                 r"|\bas\d{2}-\d{2}-\d{4}\b|\bas\d{2}-\d{2}\b", metin):
        return "nasa"
    if "loc.gov" in metin or "library of congress" in metin:
        return "loc"
    if "smithsonian" in metin or "si.edu" in metin:
        return "smithsonian"
    return (f"{getattr(v, 'saglayici', 'bilinmiyor')}:"
            f"{(getattr(v, 'eser_sahibi', '') or 'anon')[:24].lower()}")


# ⚠ 429 DERSI: jenerik UA ile wikimedia `Retry-After: 600` verdi (10 dk ceza).
# Politika bicimli UA ayni URL'ye 200 + 1.3 MB dondu. Sahte kisisel iletisim
# UYDURMUYORUZ; araci ve etiket sayfasini isaret ediyoruz.
UA = ("BEDOSAHO-DocBot/1.0 (+https://www.mediawiki.org/wiki/API:Etiquette) "
      "python-requests")
BEKLE_SN = 1.4
GERI_CEKILME = (3.0, 8.0, 15.0)
MAKS_BEKLE_SN = 45.0


def _istek(yontem, url, **kw):
    """guvenli_istek'in bekledigi imza: (yontem, url, **kw)."""
    import requests
    kw.setdefault("timeout", 45)
    bas = kw.pop("headers", None) or {}
    bas.setdefault("User-Agent", UA)
    return requests.request(yontem, url, headers=bas, **kw)


def _indir_dayanikli(url: str, hedef: str) -> tuple:
    """Sertlestirilmis indirme; 429'da Retry-After'i ONURLANDIR.

    Doner (hata_mesaji, bilgi). hata bos ise basarili.

    ⚠ KULLANICI KALITE UYARISI (11 Agu): burada onceden `icerik_kapisi`nin
    tuple sonucu yok sayiliyordu, boyut tavani `Content-Length`e guveniyordu ve
    icerik DECODE EDILMIYORDU. Uc kapinin hepsi artik `medya/indirme.py`
    icinde ve donus degerleri KULLANILIYOR.
    """
    son, bilgi = "", {}
    for deneme in range(len(GERI_CEKILME) + 1):
        r = indirme.guvenli_indir(url, hedef, istek=_istek, beklenen="image",
                                  zaman_asimi=45)
        if r["ok"]:
            return "", r["bilgi"]
        son, bilgi = r["sebep"], r.get("bilgi") or {}
        if r.get("http") == 429:
            ra = r.get("retry_after")
            try:
                istenen = float(ra) if ra else 0.0
            except (TypeError, ValueError):
                istenen = 0.0
            son = f"HTTP 429 (Retry-After={ra or '-'})"
            if deneme < len(GERI_CEKILME) and istenen <= MAKS_BEKLE_SN:
                time.sleep(min(MAKS_BEKLE_SN,
                               max(istenen + 1.0, GERI_CEKILME[deneme])))
                continue
            return son, bilgi
        # Decode/icerik reddi KALICIDIR: yeniden denemek ayni sonucu verir
        if "decode" in son or "icerik kapisi" in son or "HTML" in son:
            return son, bilgi
        if deneme < len(GERI_CEKILME):
            time.sleep(GERI_CEKILME[deneme])
            continue
    return son or "bilinmeyen hata", bilgi


def _hash(yol: str) -> str:
    h = hashlib.sha256()
    with open(yol, "rb") as f:
        for p in iter(lambda: f.read(65536), b""):
            h.update(p)
    return h.hexdigest()[:16]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sinir-sn", type=int, default=1200)
    ap.add_argument("--sahne-basina", type=int, default=2)
    a = ap.parse_args()
    os.makedirs(MEDYA_DIZIN, exist_ok=True)

    print("═" * 62)
    print("FAZ E — GERCEK LISANSLI MEDYA AVI (canli)")
    print("═" * 62)

    man = avci.avla(SAHNELER, konu="Apollo 11 Ay'a inis", erisim_tarihi=ERISIM,
                    sinir=KosuSiniri(toplam_sure_sn=a.sinir_sn),
                    onbellek=Onbellek(), defter=MaliyetDefteri())

    kullanilabilir = man.kullanilabilir()
    print(f"\n  aday: {len(man.adaylar)}  avci secimi: {len(man.secilenler())}  "
          f"lisans-kullanilabilir: {len(kullanilabilir)}")

    # ── KONU KAPISI ──
    gecen, red = [], {}
    for c in kullanilabilir:
        ok, sebep = konu_kapisi(c)
        if ok:
            gecen.append(c)
        else:
            k = sebep.split(":")[0]
            red[k] = red.get(k, 0) + 1
    print(f"  konu kapisini gecen: {len(gecen)}/{len(kullanilabilir)}")
    for k, v in sorted(red.items(), key=lambda x: -x[1])[:6]:
        print(f"    red {v:4}x  {k}")

    # ── SECIM ONCESI DEDUP ──
    # ⚠ Olculdu: 10 secim yapildi ama 4'u AYNI dosyaydi (farkli sahnelerde ayni
    # goruntu). Dedup indirmeden SONRA calisiyordu, yani saglayici kotasi
    # kopyalara harcaniyor ve benzersiz varlik sayisi 6'da kaliyordu.
    # Artik ayni indirme URL'si secime bir kez giriyor.
    gorulen_url: set = set()
    tekil = []
    for c in gecen:
        anahtar = (getattr(c, "icerik_hash", "") or c.indirme_url or "").lower()
        if anahtar in gorulen_url:
            continue
        gorulen_url.add(anahtar)
        tekil.append(c)
    print(f"  secim oncesi dedup: {len(gecen)} -> {len(tekil)}")

    # ── SECIM: GLOBAL havuz + Faz B saglayici kotasi ──
    # ⚠ Sahne-bazli secim 6'da tikandi: konu kapisini gecen 12 tekil varlik
    # yalnizca 3-4 sahnede kumelenmis, kalan sahnelerde hic aday yok. Sahne
    # basina 2 ile ust sinir 6-8 oluyordu. Belgesel icin varliklarin hangi
    # sorgudan geldigi degil KAC TEKIL varlik oldugu onemli; secim global
    # havuzdan yapiliyor, saglayici kotasi (floor(sahne*0.40)) korunuyor.
    hedef_adet = max(8, min(12, len(tekil)))
    sayac: dict = {}
    secilen, gerekceler = siralama.sec(
        tekil, adet=hedef_adet, saglayici_sayaci=sayac,
        toplam_secilen=0, toplam_sahne=len(SAHNELER))
    for c in secilen:
        sayac[c.saglayici] = sayac.get(c.saglayici, 0) + 1
    print(f"  secilen (global, kota sonrasi): {len(secilen)}/{hedef_adet}  "
          f"dagilim={sayac}")
    for g in gerekceler[:3]:
        print(f"    red: {g.get('sebep', '')[:88]}")

    # ── INDIRME ──
    indirilen, hashler, red_indirme = [], {}, []
    for v in secilen:
        aid = getattr(v, "asset_id", "") or f"a{len(indirilen):02d}"
        url = getattr(v, "indirme_url", "")
        if not url:
            continue
        uzanti = os.path.splitext(url.split("?")[0])[1][:5] or ".jpg"
        hedef = os.path.join(MEDYA_DIZIN, f"{aid}{uzanti}")
        time.sleep(BEKLE_SN)                     # nazik hiz
        hata, dbilgi = _indir_dayanikli(url, hedef)
        if hata:
            print(f"    ✖ {aid}: {hata}")
            red_indirme.append({"asset_id": aid, "sebep": hata})
            continue
        h = _hash(hedef)
        if h in hashler:
            os.remove(hedef)
            print(f"    ~ dedup {aid} == {hashler[h]}")
            continue
        hashler[h] = aid
        indirilen.append({
            "asset_id": aid, "yol": os.path.abspath(hedef), "hash": h,
            "saglayici": v.saglayici, "lisans": v.lisans,
            "lisans_url": v.lisans_url, "eser_sahibi": v.eser_sahibi,
            "baslik": v.baslik, "orijinal_url": v.orijinal_url,
            "fact_id": v.fact_id, "scene_id": v.scene_id,
            "sahne_amaci": v.sahne_amaci, "arsiv": arsiv_kimligi(v),
            # Olculen gercek degerler (saglayicinin beyani DEGIL)
            "genislik": dbilgi.get("genislik") or v.genislik,
            "yukseklik": dbilgi.get("yukseklik") or v.yukseklik,
            "boyut": os.path.getsize(hedef),
            "dogrulama": dbilgi,
        })

    # ── CESITLILIK OLCUMU ──
    n = len(indirilen)
    sag, ars = {}, {}
    for d in indirilen:
        sag[d["saglayici"]] = sag.get(d["saglayici"], 0) + 1
        ars[d["arsiv"]] = ars.get(d["arsiv"], 0) + 1

    print(f"\n  ── indirilen benzersiz varlik: {n} ──")
    for d in indirilen:
        print(f"    {d['asset_id']:22} {d['saglayici']:12} {d['lisans']:14} "
              f"arsiv={d['arsiv']:10} {d['baslik'][:40]}")

    tek_sag = (max(sag.values()) / n) if n else 0.0
    tek_ars = (max(ars.values()) / n) if n else 0.0
    print(f"\n  saglayici dagilimi: {sag}")
    print(f"  ARSIV dagilimi     : {ars}")
    print(f"  en buyuk saglayici payi: {tek_sag:.0%} (tavan %40)")
    print(f"  en buyuk ARSIV payi    : {tek_ars:.0%}")

    # ⚠ IKI AYRI OLCU, IKI AYRI KAPI (kullanicinin acik sarti):
    #   saglayici = medyayi SUNAN site (wikimedia, archive_org, loc...)
    #   ARSIV     = medyanin GERCEK kaynagi (nasa, loc, smithsonian...)
    # Ayni NASA fotografinin iki farkli sitede bulunmasi "cesitlilik" DEGILDIR.
    # Bu yuzden arsiv kapisi ayri ve baskin olcu olarak raporlaniyor.
    kapilar = {
        "benzersiz>=8": n >= 8,
        "guvenli_decode=hepsi": n > 0 and all(
            d.get("dogrulama", {}).get("sihirli_tur") for d in indirilen),
        "SAGLAYICI cesitliligi>=3": len(sag) >= 3,
        "SAGLAYICI tek pay<=40%": tek_sag <= 0.40 + 1e-9,
        "ARSIV cesitliligi>=2": len(ars) >= 2,
        "ARSIV tek pay<=40%": tek_ars <= 0.40 + 1e-9,
    }
    for k, v in kapilar.items():
        print(f"  {'✓' if v else '✖'} {k}")

    bosluk = list(getattr(man, "kapsam_bosluklari", []))
    if tek_ars > 0.40:
        bosluk.append({"scene_id": "*", "sebep":
                       f"ARSIV HAKIMIYETI: '{max(ars, key=ars.get)}' arsivi "
                       f"varliklarin %{tek_ars * 100:.0f}'ini sagliyor; farkli "
                       "saglayicilardan gelmeleri cesitlilik DEGIL, ayni "
                       "arsivin aynalari.",
                       "onerilen_fallback": "kendi belge/harita/data grafigi"})
    if not kapilar["saglayici>=3"]:
        bosluk.append({"scene_id": "*", "sebep":
                       f"SAGLAYICI CESITLILIGI SAGLANAMADI: {len(sag)} saglayici. "
                       "Apollo 11 icin acik lisansli alternatif arsiv bulunamadi; "
                       "alakasiz stok kullanmak yerine bosluk beyan edildi.",
                       "onerilen_fallback": "kendi belge/harita/data grafigi"})

    # ── ATIF DEFTERI (fact_id ile) ──
    atif = os.path.join(CIKTI, "attribution.txt")
    with open(atif, "w", encoding="utf-8") as f:
        f.write("FAZ E PILOT — MEDYA ATIFLARI\n")
        f.write(f"erisim tarihi: {ERISIM}\n" + "=" * 70 + "\n\n")
        for d in indirilen:
            f.write(f"[{d['fact_id'] or '-'}] {d['asset_id']}  "
                    f"(sahne {d['scene_id']})\n")
            f.write(f"  baslik      : {d['baslik']}\n")
            f.write(f"  eser sahibi : {d['eser_sahibi'] or '(belirtilmemis)'}\n")
            f.write(f"  saglayici   : {d['saglayici']}   arsiv: {d['arsiv']}\n")
            f.write(f"  lisans      : {d['lisans']}  {d['lisans_url']}\n")
            f.write(f"  kaynak sayfa: {d['orijinal_url']}\n\n")

    rapor = {"varliklar": indirilen, "indirme_reddi": red_indirme,
             "saglayici_dagilimi": sag,
             "arsiv_dagilimi": ars, "tek_saglayici_payi": round(tek_sag, 3),
             "tek_arsiv_payi": round(tek_ars, 3), "kapilar": kapilar,
             "konu_kapisi_red": red, "kapsam_bosluklari": bosluk,
             "notlar": list(getattr(man, "notlar", [])),
             "attribution": os.path.abspath(atif)}
    ry = os.path.join(CIKTI, "medya_rapor.json")
    with open(ry, "w", encoding="utf-8") as f:
        json.dump(rapor, f, ensure_ascii=False, indent=1)
    print(f"\n  kapsam boslugu: {len(bosluk)}")
    print(f"  atif defteri : {os.path.abspath(atif)}")
    print(f"  medya raporu : {os.path.abspath(ry)}")
    return 0 if all(kapilar.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
