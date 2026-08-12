"""SIRALAMA — hangi aday secilir.

Puan bilesenleri (0-100):
  semantik  : konu/varlik/konum/tarih uygunlugu
  amac      : sahne amaci ve cekim turu uyumu
  teknik    : cozunurluk, video suresi, en-boy
  vision    : gorsel dogrulama (enjekte edilebilir; anahtar yoksa deterministik)
  ceza      : watermark/yazi, tekrar, cok kisa/uzun sure

Ve SERT bir kural: TEK SAGLAYICI SECILENLERIN %40'INI ASAMAZ. Bu bir puan
degil kota — Pexels her zaman en zengin havuz oldugu icin puanla yarissa
neredeyse tum sahneleri o kazanirdi ve "tek saglayici hakimiyeti" kabul
kriterine takilirdik.
"""
from __future__ import annotations

import re
from typing import Optional

# Tek saglayici tavani (kabul kriteri: %40)
SAGLAYICI_TAVANI = 0.40

AGIRLIK = {"semantik": 0.34, "amac": 0.18, "teknik": 0.22, "vision": 0.26}

# Watermark / gomulu yazi isaretleri — basliktan/aciklamadan tespit
WATERMARK_ISARETI = re.compile(
    r"\b(watermark|logo|stock\s*footage|preview|sample|demo|trailer|"
    r"copyright|getty|shutterstock|alamy|dreamstime|123rf|"
    r"subtitle|caption|lower\s*third|title\s*card)\b", re.I)

# Sahne amacina uygun cekim kelimeleri
AMAC_KELIME = {
    "establishing": ("aerial", "skyline", "wide", "panorama", "cityscape",
                     "drone", "landscape", "overview", "establishing"),
    "detay":        ("close", "closeup", "close-up", "macro", "detail", "hands"),
    "arsiv":        ("archive", "archival", "historical", "vintage", "old",
                     "footage", "film", "newsreel", "black and white", "1900",
                     "1950", "1960", "1970", "1980", "1990"),
    "belge":        ("document", "paper", "report", "newspaper", "manuscript",
                     "letter", "page", "print", "scan", "certificate"),
    "harita":       ("map", "atlas", "chart", "cartography", "globe"),
    "ortam":        ("street", "daily", "life", "neighbourhood", "neighborhood",
                     "market", "evening", "morning", "people", "crowd"),
    "kisi":         ("portrait", "photograph", "headshot", "face", "person"),
}


# ═══════════════ FAZ I-5 — KONSEPT FARKINDALIGI (EK BILGI) ═══════════════
# ⚠ NEDEN VAR: `AMAC_KELIME` sahne amacini biliyordu ama KONSEPTI bilmiyordu.
# "close up" araniyorsa bir URUN videosunda studyo cekimi, bir KORKU
# hikayesinde loş atmosfer dogru adaydir; ikisi ayni puani aliyordu ve
# saglayici havuzundan AYNI JENERIK klip seciliyordu.
#
# ⚠ GERIYE UYUMLULUK: `konsept=None` iken bu blogun HICBIRI calismaz ve
# `puanla()` eskisiyle BIREBIR ayni skoru uretir (testli).
# ⚠ AGIRLIK VEKTORU DEGISMEDI. Konsept yalnizca `amac` bilesenini SINIRLI
# olcude kaydirir (en fazla +-KONSEPT_KAYMA puan). Yeni bir agirlik eklemek
# tum eski skorlari degistirirdi.
# ⚠ ALAKA KAPISI ve LISANS DUVARI BU ADIMDA DEGISMEDI — konsept puani bir
# adayi kapidan GECIREMEZ, yalnizca gecenler arasinda siralamayi degistirir.
KONSEPT_KAYMA = 12.0

# Aile -> (tercih edilen cekim kelimeleri, cezalandirilan kelimeler)
KONSEPT_TERIM = {
    "seyahat": (("aerial", "drone", "scenic", "coastline", "landscape",
                 "travel", "viewpoint", "old town", "market", "hiking"),
                ("studio", "white background", "office", "laboratory",
                 "isolated")),
    "urun": (("product", "studio", "packshot", "white background", "macro",
              "unboxing", "showroom", "retail"),
             ("archive", "historical", "newsreel", "vintage film", "map")),
    "egitim": (("diagram", "chart", "infographic", "data", "laboratory",
                "research", "classroom", "whiteboard", "microscope"),
               ("party", "nightlife", "fashion", "dance")),
    "hikaye": (("moody", "atmosphere", "silhouette", "fog", "dim", "night",
                "shadow", "cinematic", "dramatic"),
               ("infographic", "chart", "document scan", "product", "studio")),
    "kultur": (("concert", "stage", "musician", "instrument", "festival",
                "performance", "audience"),
               ("laboratory", "document scan", "chart")),
    "yasam": (("home", "kitchen", "routine", "lifestyle", "cozy", "morning",
               "family"),
              ("archive", "newsreel", "laboratory")),
    "belgesel": (("archive", "archival", "historical", "documentary",
                  "newsreel", "vintage"),
                 ("packshot", "white background", "unboxing")),
}


def konsept_ailesi(konsept) -> str:
    """`taksonomi.siniflandir()` ciktisindan AILE adi. Cozulemezse "".

    ⚠ Bu modul `taksonomi`yi IMPORT ETMEZ; yalnizca sozluk alanlarini okur.
    Bilinmeyen/belirsiz -> "" -> eski davranis (konsept etkisi YOK).
    """
    try:
        if not isinstance(konsept, dict):
            return ""
        yol = str(konsept.get("yol") or "")
        if not yol or yol == "belirsiz":
            return ""
        aile = str(konsept.get("aile") or yol.split(".")[0])
        return aile if aile in KONSEPT_TERIM else ""
    except Exception:
        return ""


def konsept_kaymasi(aday, konsept) -> tuple:
    """Konsepte gore `amac` puanina uygulanacak kayma. Doner (kayma, gerekce).

    ⚠ SINIRLI: en fazla +-`KONSEPT_KAYMA`. Bir adayi kapidan gecirmez,
    yalnizca GECENLER arasinda siralamayi degistirir.
    """
    aile = konsept_ailesi(konsept)
    if not aile:
        return 0.0, ""
    tercih, ceza = KONSEPT_TERIM[aile]
    havuz = f"{aday.baslik} {aday.aciklama} {aday.sorgu}".lower()
    art = sum(1 for k in tercih if k in havuz)
    eksi = sum(1 for k in ceza if k in havuz)
    kayma = max(-KONSEPT_KAYMA, min(KONSEPT_KAYMA,
                                    4.0 * art - 6.0 * eksi))
    if not art and not eksi:
        return 0.0, f"konsept '{aile}': notr (isaret yok)"
    return round(kayma, 1), (f"konsept '{aile}': {art} tercih, {eksi} ceza "
                             f"-> {kayma:+.1f}")


def _kelime_kumesi(metin: str) -> set:
    return {k for k in re.findall(r"[a-z0-9]{3,}", str(metin or "").lower())}


def semantik_puan(aday, varliklar: dict, iddia_metni: str = "") -> tuple[float, dict]:
    """Adayin metadata'si iddianin varliklariyla ne kadar ortusuyor?"""
    # ⚠ 11 Agu (Faz E canli kosusu): havuza `aday.sorgu` DAHILDI. O metin
    # BIZIM sorgumuz, saglayicinin verdigi kanit degil. Sonuc: her aday kendi
    # sorgumuzla eslesip konu/yer puani topluyordu; "MAJESTIC 12 Files" ve
    # "Aryan Christ" gibi Apollo ile ilgisiz arsiv ogeleri secildi.
    # Kanit YALNIZCA saglayici metadata'si olabilir.
    havuz = _kelime_kumesi(
        f"{aday.baslik} {aday.aciklama} {aday.konum} {aday.tarih}")
    detay: dict = {}
    puan = 0.0

    # Yer: en agirlikli sinyal (11 Agu olcumu: yanlis ulke en gorunur hata)
    yerler = [str(y).lower() for y in (varliklar.get("yerler") or [])]
    yer_tut = sum(1 for y in yerler if _kelime_kumesi(y) & havuz)
    if yerler:
        detay["yer"] = f"{yer_tut}/{len(yerler)}"
        puan += 34.0 * (yer_tut / len(yerler))
    else:
        puan += 17.0                       # yer iddiasi yok -> notr

    # Kisi / kurum
    for ad, agir in (("kisiler", 14.0), ("kurumlar", 12.0)):
        liste = [str(x).lower() for x in (varliklar.get(ad) or [])]
        if not liste:
            puan += agir * 0.5
            continue
        tut = sum(1 for x in liste if _kelime_kumesi(x) & havuz)
        detay[ad] = f"{tut}/{len(liste)}"
        puan += agir * (tut / len(liste))

    # Tarih / on yil
    tarihler = [str(t) for t in (varliklar.get("tarihler") or [])
                + (varliklar.get("onyillar") or [])]
    if tarihler:
        tut = sum(1 for t in tarihler if t.rstrip("s") in
                  f"{aday.tarih} {aday.baslik} {aday.aciklama}")
        detay["tarih"] = f"{tut}/{len(tarihler)}"
        puan += 14.0 * (1.0 if tut else 0.0)
    else:
        puan += 7.0

    # Konu kelimeleri
    konu = [str(k).lower() for k in (varliklar.get("konu_kelimeleri") or [])]
    if konu:
        tut = sum(1 for k in konu if k in havuz)
        detay["konu"] = f"{tut}/{len(konu)}"
        puan += 26.0 * min(1.0, tut / max(1, min(3, len(konu))))
    else:
        puan += 13.0
    return round(min(100.0, puan), 1), detay


def amac_puan(aday, amac: str) -> float:
    """Aday, sahne amacinin istedigi cekim turune uyuyor mu?"""
    kelimeler = AMAC_KELIME.get(amac, ())
    if not kelimeler:
        return 50.0
    havuz = f"{aday.baslik} {aday.aciklama} {aday.sorgu}".lower()
    tut = sum(1 for k in kelimeler if k in havuz)
    taban = 40.0 if tut == 0 else min(100.0, 55.0 + 15.0 * tut)
    # Tur uyumu: arsiv/belge/harita gorsel de olabilir; establishing video ister
    if amac in ("establishing", "ortam") and aday.tur == "video":
        taban += 8.0
    if amac in ("belge", "harita", "kisi") and aday.tur == "image":
        taban += 8.0
    return round(min(100.0, taban), 1)


def teknik_puan(aday) -> tuple[float, list]:
    """Cozunurluk / sure / en-boy. Doner (puan, uyarilar)."""
    uyari = []
    puan = 50.0
    gen, yuk = aday.genislik or 0, aday.yukseklik or 0
    if gen and yuk:
        if gen >= 3840:
            puan = 100.0
        elif gen >= 2560:
            puan = 92.0
        elif gen >= 1920:
            puan = 80.0
        elif gen >= 1280:
            puan = 58.0
        else:
            puan = 24.0
            uyari.append(f"dusuk cozunurluk {gen}x{yuk}")
        # Dikey/kare medya 16:9 kurguda kenar bosluk yaratir
        if aday.en_boy and aday.en_boy < 1.2:
            puan -= 18.0
            uyari.append(f"en-boy {aday.en_boy} (16:9 degil)")
    else:
        uyari.append("cozunurluk bilinmiyor")
        puan = 45.0
    if aday.tur == "video":
        sn = aday.sure_sn or 0
        if 0 < sn < 3:
            puan -= 20.0
            uyari.append(f"cok kisa klip {sn}sn")
        elif sn > 600:
            puan -= 8.0
            uyari.append(f"cok uzun kaynak {sn}sn")
    return round(max(0.0, min(100.0, puan)), 1), uyari


def ceza_puan(aday, gorulen_hashler: set) -> tuple[float, list]:
    """Ceza puani (dusulecek). Doner (ceza, nedenler)."""
    ceza, neden = 0.0, []
    metin = f"{aday.baslik} {aday.aciklama}"
    m = WATERMARK_ISARETI.search(metin)
    if m:
        ceza += 22.0
        neden.append(f"watermark/yazi isareti: {m.group(0)}")
    if aday.tekil_anahtar in gorulen_hashler:
        ceza += 60.0
        neden.append("ayni icerik zaten kullanildi")
    if not aday.indirme_url:
        ceza += 40.0
        neden.append("dogrudan medya URL'si yok")
    return round(ceza, 1), neden


# Sorgu/iddia metninden zorunlu terim cikarirken atlanacak kelimeler.
ALAKA_DURAK = frozenset({
    "the", "and", "for", "from", "with", "during", "into", "over", "near",
    "seen", "view", "image", "photo", "photograph", "picture", "footage",
    "video", "detail", "close", "shot", "scene", "page", "document",
})


def alaka_terimleri(varliklar: dict, iddia_metni: str = "") -> list:
    """Adayin metadata'sinda GECMESI ZORUNLU terimler.

    Once cikarilan varliklar (yer/kisi/kurum/konu). Hicbiri yoksa iddia
    metninin ayirt edici kelimelerine DUSULUR — ilk surumde varlik cikmayinca
    hicbir zorunluluk kalmiyordu ve her sey notr puanla geciyordu.
    """
    terimler: list = []
    for ad in ("yerler", "kisiler", "kurumlar", "konu_kelimeleri"):
        for x in (varliklar.get(ad) or []):
            t = str(x).strip().lower()
            if len(t) >= 3:
                terimler.append(t)
    if not terimler:
        for k in re.findall(r"[A-Za-z0-9À-ÿĞÜŞİÖÇğüşıöç]{3,}",
                            str(iddia_metni or "").lower()):
            if k not in ALAKA_DURAK:
                terimler.append(k)
    # Tekrarsiz, sirali
    out, gorulen = [], set()
    for t in terimler:
        if t not in gorulen:
            gorulen.add(t)
            out.append(t)
    return out


def alaka_kapisi(aday, varliklar: dict, iddia_metni: str = "") -> tuple:
    """SERT KAPI: aday konuyla gercekten ilgili mi? (ok, sebep)

    ⚠ Faz E canli kosusunda olculdu: archive_org tam-metin aramasi
    "Landscape with Saint John the Baptist", "MAJESTIC 12 Files", "Aryan Christ"
    gibi ogeleri dondurdu ve hepsi SECILDI. Puanlama yumusak oldugu icin
    (varlik cikmayinca notr puan) ilgisiz oge esigi geciyordu. Kullanicinin
    kurali net: "alakasiz stok yok". Bu yuzden puan degil KAPI.

    Kural: saglayici metadata'sinda zorunlu terimlerden EN AZ BIRI gecmeli.
    Metadata bosca gelirse kapi de gecilemez — bilinmeyen icerik kullanilmaz.
    """
    metadata = f"{aday.baslik} {aday.aciklama} {getattr(aday, 'konum', '')}".lower()
    if not metadata.strip():
        return False, "saglayici metadata'si bos — icerik dogrulanamiyor"
    terimler = alaka_terimleri(varliklar, iddia_metni)
    if not terimler:
        return True, "zorunlu terim uretilemedi (kapi uygulanamaz)"

    # KELIME SINIRI: alt dizi eslemesi "11"i "1911" icinde buluyordu
    tutan = [t for t in terimler
             if re.search(rf"(?<![0-9a-zà-ÿğüşıöç]){re.escape(t)}"
                          rf"(?![0-9a-zà-ÿğüşıöç])", metadata)]
    # ESIK 1 YETERLI: kelime siniri eklendikten sonra olculdu — "MAJESTIC 12
    # Files" 0/N ile dusuyor. Esigi 2'ye cikarmak mesru adaylari da dusurdu
    # (LoC public-domain ogesi 1/2 ile reddedildi, 3 Faz B testi kirildi).
    if not tutan:
        return False, (f"konu terimlerinin HICBIRI metadata'da yok "
                       f"(kelime siniriyla): {terimler[:6]}")

    # ── SERI UYUSMAZLIGI ──
    # ⚠ Olculdu: "Apollo 11" sorgusuna "AS06-02-1445 - Apollo 6" adayi
    # geliyordu ve "apollo" tuttugu icin kapiyi geciyordu. Apollo 6 goruntusu
    # Apollo 11 belgeselinde YANLIS bilgi olur. Iddiada numarali bir ozel ad
    # varsa (Apollo 11), metadata'da AYNI ozel adin FARKLI numarasi geciyorsa
    # ve dogru numara HIC gecmiyorsa reddedilir.
    for ad, no in re.findall(r"([a-zà-ÿğüşıöç]{4,})\s+(\d{1,3})\b",
                             str(iddia_metni or "").lower()):
        dogru = re.search(rf"(?<![0-9a-z]){ad}\s*-?\s*{no}(?![0-9])", metadata)
        if dogru:
            continue
        yanlis = re.findall(rf"(?<![0-9a-z]){ad}\s*-?\s*(\d{{1,3}})(?![0-9])",
                            metadata)
        if yanlis and no not in yanlis:
            return False, (f"seri uyusmazligi: '{ad} {no}' isteniyor ama "
                           f"metadata '{ad} {yanlis[:3]}' diyor")

    return True, f"alaka {len(tutan)}: {tutan[:4]}"


def puanla(aday, *, varliklar: dict, amac: str, iddia_metni: str = "",
           gorulen_hashler: Optional[set] = None,
           vision_puanlayici=None, konsept=None) -> "object":
    """Adayin tum puanlarini hesapla ve uzerine yaz.

    ⚠ FAZ I-5: `konsept` verilirse `amac` bileseni SINIRLI olcude kaydirilir
    (bkz. `konsept_kaymasi`). `konsept=None` ise skor ESKISIYLE BIREBIR AYNI.
    Agirlik vektoru DEGISMEDI; alaka kapisi ve lisans duvari DOKUNULMADI.
    """
    gorulen_hashler = gorulen_hashler or set()
    sem, sem_detay = semantik_puan(aday, varliklar, iddia_metni)
    am = amac_puan(aday, amac)
    k_kayma, k_gerekce = konsept_kaymasi(aday, konsept) if konsept else (0.0, "")
    if k_kayma:
        am = round(max(0.0, min(100.0, am + k_kayma)), 1)
    tek, tek_uyari = teknik_puan(aday)
    ceza, ceza_neden = ceza_puan(aday, gorulen_hashler)
    vis = 50.0
    vis_detay = "puanlayici yok"
    if vision_puanlayici is not None:
        try:
            vis, vis_detay = vision_puanlayici(aday, varliklar, amac)
        except Exception as e:
            vis, vis_detay = 50.0, f"vision hata: {str(e)[:60]}"

    aday.semantik_skor = sem
    aday.vision_skor = round(float(vis), 1)
    aday.teknik_skor = tek
    aday.ceza = ceza
    aday.toplam_skor = round(max(0.0, min(100.0,
        AGIRLIK["semantik"] * sem + AGIRLIK["amac"] * am
        + AGIRLIK["teknik"] * tek + AGIRLIK["vision"] * float(vis) - ceza)), 1)
    alaka_ok, alaka_sebep = alaka_kapisi(aday, varliklar, iddia_metni)
    aday.skor_detay = {"semantik": sem_detay, "amac": am, "teknik": tek,
                       "teknik_uyari": tek_uyari, "vision": vis_detay,
                       "ceza_neden": ceza_neden, "alaka": alaka_sebep}
    # Konsept kaymasi SESSIZ degil: neden uygulandigi kayda gecer.
    if k_gerekce:
        aday.skor_detay["konsept"] = k_gerekce
    if not alaka_ok:
        # Lisans duvarindan gecse bile ALAKA kapisindan gecemeyen oge render'a
        # giremez; referans olarak kalir.
        aday.render_kullanilabilir = False
        aday.red_nedeni = (f"alaka kapisi: {alaka_sebep}"[:200]
                           if not aday.red_nedeni else aday.red_nedeni)
    return aday


def saglayici_tavan_adedi(toplam_sahne: int) -> int:
    """Bir saglayicinin secebilecegi EN FAZLA oge sayisi.

    ⚠ 11 Agu 2026 — KALITE KAPISI REDDI. Ilk surumde kota yalnizca
    "gelecek_toplam >= 4" ise uygulaniyordu; gerekce "kucuk sayilarda oran
    matematigi oynak" idi. Sonuc: 3 sahnelik canli kuru testte Pexels 2/3
    secimi aldi (tek saglayici orani %67) ve %40 kabul kriteri IHLAL EDILDI.
    Istisna gereksinimi gevsetmisti.

    Artik tavan SECIM SAYISINDAN DEGIL PLANLANAN SAHNE SAYISINDAN turetiliyor:
      3 sahne  -> floor(3*0.40)=1  -> her saglayici en fazla 1 (3 farkli saglayici)
      10 sahne -> floor(10*0.40)=4
    En az 1 birakiliyor, aksi halde tek sahnelik kosuda hicbir sey secilemez.
    Alternatif lisansli aday yoksa secim YAPILMAZ ve kapsam boslugu kalir —
    tekelleşmiş secim yapmaktan iyidir (kullanicinin acik istegi).
    """
    n = max(1, int(toplam_sahne or 1))
    return max(1, int(n * SAGLAYICI_TAVANI))


def sec(adaylar: list, *, adet: int = 1, saglayici_sayaci: Optional[dict] = None,
        toplam_secilen: int = 0, min_puan: float = 45.0,
        toplam_sahne: int = 0) -> tuple[list, list]:
    """Puanli adaylardan sec. Doner (secilenler, red_gerekceleri).

    SAGLAYICI KOTASI: bir saglayici `saglayici_tavan_adedi(toplam_sahne)`
    adedinden fazla secilemez. Kota dolu olan saglayicinin adayi ATLANIR ve
    gerekce yazilir; puanla yarismaz. Istisna YOK.
    """
    sayac = dict(saglayici_sayaci or {})
    tavan = saglayici_tavan_adedi(toplam_sahne or (toplam_secilen + adet))
    secilen, gerekce = [], []
    sirali = sorted([a for a in adaylar if a.render_kullanilabilir],
                    key=lambda a: -a.toplam_skor)
    for a in sirali:
        if len(secilen) >= adet:
            break
        if a.toplam_skor < min_puan:
            gerekce.append({"asset_id": a.asset_id, "sebep":
                            f"puan esigin altinda ({a.toplam_skor} < {min_puan})"})
            continue
        if sayac.get(a.saglayici, 0) + 1 > tavan:
            gerekce.append({"asset_id": a.asset_id, "sebep":
                            f"saglayici kotasi doldu ({a.saglayici}: "
                            f"{sayac.get(a.saglayici, 0)}/{tavan}, "
                            f"tavan %{int(SAGLAYICI_TAVANI * 100)})"})
            continue
        a.karar = "secildi"
        sayac[a.saglayici] = sayac.get(a.saglayici, 0) + 1
        secilen.append(a)
    return secilen, gerekce
