"""MEDYA AVCISI — Faz B orkestratoru.

Akis (sahne basina):
  iddia + sahne amaci
    -> sorgu_planlayici: varlik cikarimi + sorgu varyantlari
    -> kayit: aktif saglayicilar (anahtarsizlar dahil, eksik anahtar ATLANIR)
    -> saglayici.ara(): ham kayitlar
    -> guvenlik: URL kapisi (SSRF/ozel IP/sema)
    -> lisans: karar + atif; acik lisans yoksa reference_only
    -> siralama: puan + saglayici kotasi + dedup
    -> kapsam: usable aday yoksa coverage_gap + guvenli fallback onerisi

Faz A'nin sinirlari AYNEN kullaniliyor (`arastirma.butce.KosuSiniri`,
`arastirma.cache`): toplam sure tavani, istek basina zaman asimi, para tavani
ve kontrollu durma. Faz A'da tek takilan cagri 15+ dakika kosuyu kilitledi;
ayni hatayi saglayici katmaninda tekrarlamamak icin her saglayicinin devre
kesicisi de var (kayit.Saglayici.basarisiz).

⚠ Bu modul INDIRME YAPMAZ. Dry-run guvenligi: `indirme_durumu` daima
"indirilmedi" kalir. Indirme Faz C'nin isi ve ayri bir kapiyi daha gecmesi
gerekecek (icerik turu + boyut + gercek dosya hash'i).
"""
from __future__ import annotations

import hashlib
from typing import Callable, Optional

import requests

from arastirma.butce import ZAMAN_ASIMI, KosuSiniri
from arastirma.cache import ButceAsimi, MaliyetDefteri, Onbellek

from . import guvenlik, kapsam, kayit, lisans, siralama, sorgu_planlayici, vision
# Saglayicilarin kendilerini kayda eklemesi icin ZORUNLU ice aktarim.
# Bu satir olmadan kayit BOS kalir ve tum sahneler kapsam boslugu olur
# (11 Agu canli kuru testinde tam bu yasandi).
from . import providers  # noqa: F401
from .aday import AdayManifesti, MedyaAdayi

# Sahne basina saglayici basina cekilecek aday sayisi
ADAY_ADEDI = 8
# KOSU BASINA en fazla kac oge-ayrinti cagrisi yapilir.
# LoC arama ucu rights vermiyor; ayrinti cagrisi ZORUNLU ama her aday icin
# yapmak kosuyu uzatir (32 aday = 32 ek istek). Butce ile siniriyoruz ve
# raporluyoruz. Adaylar PUANA gore degil GELIS SIRASINA gore denenir cunku
# lisans bilinmeden puan da guvenilir degil.
DETAY_BUTCESI = int(__import__("os").environ.get("MEDYA_DETAY_BUTCESI", "6"))


def _asset_id(saglayici: str, url: str, sayac: int) -> str:
    h = hashlib.sha256(f"{saglayici}|{url}".encode()).hexdigest()[:10]
    return f"a{sayac:03d}_{saglayici[:4]}_{h}"


def sahne_ara(*, scene_id: str, iddia_metni: str, fact_id: str = "",
              sahne_amaci: str = "establishing", konu: str = "",
              bilinen_yerler: Optional[list] = None,
              erisim_tarihi: str = "",
              istenen_saglayicilar: Optional[list] = None,
              medya_turu: str = "video",
              sinir: Optional[KosuSiniri] = None,
              onbellek: Optional[Onbellek] = None,
              defter: Optional[MaliyetDefteri] = None,
              istek: Optional[Callable] = None,
              coz: Optional[Callable] = None,
              vision_puanlayici: Optional[Callable] = None,
              gorulen_hashler: Optional[set] = None,
              saglayici_sayaci: Optional[dict] = None,
              toplam_secilen: int = 0,
              toplam_sahne: int = 0,
              sayac_baslangic: int = 0,
              detay_butcesi: Optional[list] = None,
              konsept: Optional[dict] = None) -> dict:
    """Tek sahne icin aday topla, puanla, sec.

    Doner: {"adaylar": [...], "secilen": [...], "sorgular": [...],
            "saglayici_hatalari": [...], "kapsam": {...}, "red_gerekceleri": [...]}
    """
    sinir = sinir or KosuSiniri()
    gorulen_hashler = gorulen_hashler if gorulen_hashler is not None else set()
    # ⚠ FAZ I-5: `konsept` OPSIYONEL ek bilgidir. None ise sorgu plani ve
    # puanlama ESKISIYLE BIREBIR AYNI calisir (testli).
    plan = sorgu_planlayici.sorgu_plani(
        iddia_metni, sahne_amaci, konu=konu, bilinen_yerler=bilinen_yerler,
        konsept=konsept)
    varliklar = plan["varliklar"]
    sorgular = plan["sorgular"]

    aktif, atlanan = kayit.aktif_saglayicilar(istenen_saglayicilar)
    saglayici_hatalari = list(atlanan)
    adaylar: list = []
    sayac = sayac_baslangic

    for s in aktif:
        if sinir.bitti_mi():
            saglayici_hatalari.append({"ad": s.ad, "sebep":
                                       f"kosu siniri: {sinir.durma_nedeni}"})
            break
        tur = medya_turu if medya_turu in s.medya_turleri else (
            "image" if "image" in s.medya_turleri else s.medya_turleri[0])
        for sorgu in sorgular[:2]:            # sahne basina saglayici basina 2 sorgu
            if sinir.bitti_mi():
                break
            ok, sebep = s.hazir_mi()
            if not ok:
                saglayici_hatalari.append({"ad": s.ad, "sebep": sebep})
                break

            def _ara():
                return s.ara(sorgu, tur=tur, adet=ADAY_ADEDI,
                             zaman_asimi=sinir.istek_zaman_asimi("sayfa"),
                             istek=istek)

            try:
                if onbellek is not None:
                    ham = onbellek.getir(
                        "medya_arama",
                        {"s": s.ad, "q": sorgu, "t": tur, "n": ADAY_ADEDI},
                        lambda: {"kayitlar": _ara().kayitlar})
                    kayitlar = (ham or {}).get("kayitlar") or []
                    hata = ""
                else:
                    sonuc = _ara()
                    kayitlar, hata = sonuc.kayitlar, sonuc.hata
            except ButceAsimi as e:
                sinir.durdur(f"para tavani: {str(e)[:80]}")
                saglayici_hatalari.append({"ad": s.ad, "sebep": "para tavani"})
                break
            except Exception as e:
                hata, kayitlar = str(e)[:120], []

            if hata:
                s.basarisiz(hata)
                saglayici_hatalari.append({"ad": s.ad, "sorgu": sorgu, "sebep": hata})
                continue
            if kayitlar:
                s.basarili()
            else:
                # SESSIZ BOS DONUS RAPORLANIR. Canli kuru testte Coverr 0 aday
                # dondurdu, hata da kaydetmedi ve raporda hic gorunmedi —
                # "sagliklı ama sonucsuz" ile "bozuk" ayirt edilemiyordu.
                saglayici_hatalari.append(
                    {"ad": s.ad, "sorgu": sorgu, "sebep": "sonuc yok (0 aday)"})

            for ham_kayit in kayitlar:
                sayac += 1
                try:
                    n = s.normalize(ham_kayit)
                except Exception as e:
                    saglayici_hatalari.append(
                        {"ad": s.ad, "sebep": f"normalize hatasi: {str(e)[:80]}"})
                    continue

                a = MedyaAdayi(
                    asset_id=_asset_id(s.ad, n.get("indirme_url")
                                       or n.get("orijinal_url") or str(sayac), sayac),
                    saglayici=s.ad, tur=n.get("tur") or tur,
                    orijinal_url=n.get("orijinal_url") or "",
                    indirme_url=n.get("indirme_url") or "",
                    baslik=n.get("baslik") or "", aciklama=n.get("aciklama") or "",
                    genislik=int(n.get("genislik") or 0),
                    yukseklik=int(n.get("yukseklik") or 0),
                    sure_sn=float(n.get("sure_sn") or 0),
                    konum=n.get("konum") or "", tarih=n.get("tarih") or "",
                    fact_id=fact_id, scene_id=scene_id,
                    sahne_amaci=plan["amac"], sorgu=sorgu,
                    erisim_tarihi=erisim_tarihi,
                    varliklar=(varliklar.get("kisiler") or [])
                    + (varliklar.get("kurumlar") or []))

                # ── 1) URL GUVENLIK KAPISI ──
                url_hatasi = ""
                for alan in ("orijinal_url", "indirme_url"):
                    d = getattr(a, alan)
                    if not d:
                        continue
                    try:
                        guvenlik.url_dogrula(d, coz=coz)
                    except guvenlik.GuvenlikHatasi as e:
                        url_hatasi = f"{alan}: {str(e)[:80]}"
                        break
                if url_hatasi:
                    a.reddet(f"guvenlik: {url_hatasi}")
                    a.karar = "reddedildi"     # guvenlik reddi reference_only DEGIL
                    adaylar.append(a)
                    continue
                if not a.orijinal_url:
                    a.reddet("provenance yok: orijinal sayfa URL'si bos")
                    a.karar = "reddedildi"
                    adaylar.append(a)
                    continue

                # ── 2) LISANS DUVARI ──
                karar = lisans.lisans_karari(ham_kayit if isinstance(ham_kayit, dict)
                                             else {}, s.ad)
                # normalize edilmis alanlar da lisans tasiyabilir (LoC rights vb.)
                if not karar["render_kullanilabilir"]:
                    karar2 = lisans.lisans_karari(n, s.ad)
                    if karar2["render_kullanilabilir"]:
                        karar = karar2
                a.ham_lisans = karar["ham_lisans"]
                a.lisans = karar["lisans"]
                a.lisans_url = karar["lisans_url"]
                a.eser_sahibi = karar["eser_sahibi"] or (n.get("creator") or "")
                a.atif_gerekli = karar["atif_gerekli"]
                a.ticari_izin = karar["ticari_izin"]
                a.degistirme_izni = karar["degistirme_izni"]
                a.render_kullanilabilir = karar["render_kullanilabilir"]
                a.red_nedeni = karar["red_nedeni"]
                if a.render_kullanilabilir:
                    a.atif_metni = lisans.atif_metni(
                        a.lisans, a.eser_sahibi, a.baslik, a.orijinal_url)
                else:
                    # Atif gerekli ama sahip bilinmiyorsa normalize'daki creator
                    # ile bir kez daha dene (Wikimedia Artist HTML iceriyor)
                    if (a.eser_sahibi and "atif istiyor" in a.red_nedeni):
                        tekrar = lisans.lisans_karari(
                            {**(ham_kayit if isinstance(ham_kayit, dict) else {}),
                             "creator": a.eser_sahibi}, s.ad)
                        if tekrar["render_kullanilabilir"]:
                            a.lisans = tekrar["lisans"]
                            a.render_kullanilabilir = True
                            a.red_nedeni = ""
                            a.atif_metni = lisans.atif_metni(
                                a.lisans, a.eser_sahibi, a.baslik, a.orijinal_url)
                    # ── 2b) OGE AYRINTISI ile ZENGINLESTIRME (butceli) ──
                    # Arama ucu lisansi vermiyorsa oge ayrintisina bakilir.
                    # 11 Agu kalite kapisi: LoC'un 32 adayinin 32'si bu adim
                    # olmadigi icin reddediliyordu.
                    if (not a.render_kullanilabilir and s.detay_destekli
                            and detay_butcesi is not None
                            and detay_butcesi[0] > 0 and not sinir.bitti_mi()):
                        detay_butcesi[0] -= 1
                        try:
                            ek = s.zenginlestir(
                                ham_kayit if isinstance(ham_kayit, dict) else {}, n,
                                zaman_asimi=sinir.istek_zaman_asimi("sayfa"),
                                istek=istek) or {}
                        except Exception as e:
                            ek = {"_detay_hata": str(e)[:80]}
                        if ek.get("_detay_hata"):
                            saglayici_hatalari.append(
                                {"ad": s.ad, "sebep":
                                 f"oge ayrintisi: {ek['_detay_hata']}"})
                        else:
                            zengin = {**n, **{k: v for k, v in ek.items()
                                              if not k.startswith("_")}}
                            if zengin.get("indirme_url"):
                                a.indirme_url = zengin["indirme_url"]
                            for alan in ("genislik", "yukseklik"):
                                if zengin.get(alan):
                                    setattr(a, alan, int(zengin[alan]))
                            if zengin.get("konum"):
                                a.konum = zengin["konum"]
                            if zengin.get("tarih"):
                                a.tarih = zengin["tarih"]
                            k2 = lisans.lisans_karari(zengin, s.ad)
                            if k2["render_kullanilabilir"]:
                                a.ham_lisans = k2["ham_lisans"]
                                a.lisans = k2["lisans"]
                                a.lisans_url = k2["lisans_url"]
                                a.eser_sahibi = (k2["eser_sahibi"]
                                                 or zengin.get("creator") or "")
                                a.atif_gerekli = k2["atif_gerekli"]
                                a.ticari_izin = k2["ticari_izin"]
                                a.degistirme_izni = k2["degistirme_izni"]
                                a.render_kullanilabilir = True
                                a.red_nedeni = ""
                                a.atif_metni = lisans.atif_metni(
                                    a.lisans, a.eser_sahibi, a.baslik,
                                    a.orijinal_url)
                            else:
                                a.ham_lisans = k2["ham_lisans"] or a.ham_lisans
                                a.red_nedeni = (k2["red_nedeni"]
                                                + " (oge ayrintisi da belirsiz)")

                    if not a.render_kullanilabilir:
                        a.reddet(a.red_nedeni or "lisans belirsiz")
                        adaylar.append(a)
                        continue

                # ── 3) PUANLAMA ──
                siralama.puanla(a, varliklar=varliklar, amac=plan["amac"],
                                iddia_metni=iddia_metni,
                                gorulen_hashler=gorulen_hashler,
                                vision_puanlayici=vision_puanlayici,
                                konsept=konsept)
                adaylar.append(a)

    # ── 4) SECIM (saglayici kotasi + puan esigi) ──
    secilen, red_gerekceleri = siralama.sec(
        adaylar, adet=1, saglayici_sayaci=saglayici_sayaci,
        toplam_secilen=toplam_secilen, toplam_sahne=toplam_sahne)
    for a in secilen:
        gorulen_hashler.add(a.tekil_anahtar)
    for g in red_gerekceleri:
        for a in adaylar:
            if a.asset_id == g["asset_id"] and a.karar == "aday":
                a.karar_nedeni = g["sebep"]

    kapsam_karari = kapsam.sahne_kapsami(
        scene_id=scene_id, sahne_amaci=plan["amac"], adaylar=adaylar,
        secilen=secilen, iddia_metni=iddia_metni, varliklar=varliklar)

    return {"adaylar": adaylar, "secilen": secilen, "sorgular": sorgular,
            "plan": plan, "saglayici_hatalari": saglayici_hatalari,
            "kapsam": kapsam_karari, "red_gerekceleri": red_gerekceleri,
            "sayac": sayac}


def avla(sahneler: list, *, konu: str = "", erisim_tarihi: str = "",
         bilinen_yerler: Optional[list] = None,
         istenen_saglayicilar: Optional[list] = None,
         sinir: Optional[KosuSiniri] = None,
         onbellek: Optional[Onbellek] = None,
         defter: Optional[MaliyetDefteri] = None,
         istek: Optional[Callable] = None,
         coz: Optional[Callable] = None,
         vision_puanlayici: Optional[Callable] = None,
         konsept: Optional[dict] = None) -> AdayManifesti:
    """Tum sahneler icin medya avla.

    `sahneler`: [{"scene_id","iddia_metni","fact_id","sahne_amaci","medya_turu"}]
    """
    sinir = sinir or KosuSiniri()
    kayit.kosu_sifirla()
    if vision_puanlayici is None:
        vision_puanlayici = vision.deterministik_puanlayici

    man = AdayManifesti(konu=konu, olusturma=erisim_tarihi)
    man.sahne_sayisi = len(sahneler)
    detay_butcesi = [DETAY_BUTCESI]
    gorulen: set = set()
    sayac_dag: dict = {}
    sayac = 0

    for i, sh in enumerate(sahneler):
        if sinir.bitti_mi():
            man.notlar.append(
                f"AVLANMA DURDURULDU: {sinir.durma_nedeni} — "
                f"{i}/{len(sahneler)} sahne islendi")
            for kalan in sahneler[i:]:
                man.kapsam_bosluklari.append({
                    "scene_id": kalan.get("scene_id"),
                    "sebep": "kosu siniri nedeniyle aranmadi",
                    "onerilen_fallback": "motion-graphic"})
            break
        sonuc = sahne_ara(
            scene_id=sh.get("scene_id") or f"s{i:03d}",
            iddia_metni=sh.get("iddia_metni") or "",
            fact_id=sh.get("fact_id") or "",
            sahne_amaci=sh.get("sahne_amaci")
            or sorgu_planlayici.amac_ata(i, konsept=konsept),
            konu=konu, bilinen_yerler=bilinen_yerler,
            erisim_tarihi=erisim_tarihi,
            istenen_saglayicilar=istenen_saglayicilar,
            medya_turu=sh.get("medya_turu") or "video",
            sinir=sinir, onbellek=onbellek, defter=defter, istek=istek, coz=coz,
            vision_puanlayici=vision_puanlayici,
            gorulen_hashler=gorulen, saglayici_sayaci=sayac_dag,
            toplam_secilen=len(man.secilenler()),
            toplam_sahne=len(sahneler), sayac_baslangic=sayac,
            detay_butcesi=detay_butcesi, konsept=konsept)
        sayac = sonuc["sayac"]
        for a in sonuc["adaylar"]:
            man.ekle(a)
        for a in sonuc["secilen"]:
            sayac_dag[a.saglayici] = sayac_dag.get(a.saglayici, 0) + 1
        man.saglayici_hatalari.extend(sonuc["saglayici_hatalari"])
        if sonuc["kapsam"]["bosluk"]:
            man.kapsam_bosluklari.append(sonuc["kapsam"])

    man.notlar.append(f"kosu siniri: {sinir.ozet()}")
    man.detay_cagrisi = DETAY_BUTCESI - detay_butcesi[0]
    man.notlar.append(
        f"oge-ayrinti cagrisi: {man.detay_cagrisi}/{DETAY_BUTCESI}")
    return man
