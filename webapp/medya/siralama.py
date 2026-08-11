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


def _kelime_kumesi(metin: str) -> set:
    return {k for k in re.findall(r"[a-z0-9]{3,}", str(metin or "").lower())}


def semantik_puan(aday, varliklar: dict, iddia_metni: str = "") -> tuple[float, dict]:
    """Adayin metadata'si iddianin varliklariyla ne kadar ortusuyor?"""
    havuz = _kelime_kumesi(
        f"{aday.baslik} {aday.aciklama} {aday.konum} {aday.tarih} {aday.sorgu}")
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


def puanla(aday, *, varliklar: dict, amac: str, iddia_metni: str = "",
           gorulen_hashler: Optional[set] = None,
           vision_puanlayici=None) -> "object":
    """Adayin tum puanlarini hesapla ve uzerine yaz."""
    gorulen_hashler = gorulen_hashler or set()
    sem, sem_detay = semantik_puan(aday, varliklar, iddia_metni)
    am = amac_puan(aday, amac)
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
    aday.skor_detay = {"semantik": sem_detay, "amac": am, "teknik": tek,
                       "teknik_uyari": tek_uyari, "vision": vis_detay,
                       "ceza_neden": ceza_neden}
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
