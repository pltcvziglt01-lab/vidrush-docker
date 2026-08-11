"""GORSEL GRAMER — hangi beat'e hangi CEKIM TURU ve hangi varlik.

Iki isi var:
  1. Beat'in islevine gore cekim turu secmek (establishing / medium /
     close-detail / archive / document / map / data / atmospheric)
  2. SUREKLILIK kurallarini uygulamak: ayni varlik, ayni kadraj, ayni kamera
     hareketi ARKA ARKAYA kullanilmaz.

Neden 2. madde kritik: 11 Agu ciktisinda ayni klip farkli kadrajla iki kez
kullanildi ve izleyici "ayni goruntu" diye algiladi. Profesyonel kurguda
ardil cekimlerin en az biri degisir: mesafe, aci ya da hareket.

Ayrica: coverage_gap varsa ASLA rastgele stok konmaz — Faz B'nin guvenli
fallback onerisi (map/document/data/motion-graphic) buraya tasinir.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Optional

CEKIM_TURLERI = ("establishing", "medium", "close-detail", "archive",
                 "document", "map", "data", "atmospheric")

# Islev -> tercih edilen cekim turleri (sirali). Ilk uygun olan secilir.
ISLEV_CEKIM = {
    "hook":      ("close-detail", "atmospheric", "establishing"),
    "kurulum":   ("establishing", "medium", "atmospheric"),
    "kanit":     ("document", "data", "close-detail", "archive"),
    "aciklama":  ("medium", "atmospheric", "close-detail"),
    "donus":     ("close-detail", "archive", "medium"),
    "sonuc":     ("establishing", "atmospheric", "medium"),
}

# Cekim turu -> kamera hareketi adaylari (motion.py bunlari spec'e cevirir)
CEKIM_HAREKET = {
    "establishing": ("push-in", "pull-out", "pan-right", "static"),
    "medium":       ("push-in", "pan-left", "static"),
    "close-detail": ("push-in", "static", "handheld"),
    "archive":      ("push-in", "static"),
    "document":     ("document-scan", "push-in"),
    "map":          ("map-route", "static"),
    "data":         ("data-reveal", "static"),
    "atmospheric":  ("slow-drift", "static", "pull-out"),
}

# Fallback turu -> cekim turu (Faz B kapsam.py ile ayni sozluk)
FALLBACK_CEKIM = {
    "harita": "map",
    "belge-yakin-plan": "document",
    "lisansli-arsiv": "archive",
    "motion-graphic": "data",
}


@dataclass
class Cekim:
    """Bir beat'in gorsel karari."""
    beat_id: str
    scene_id: str
    fact_id: str = ""
    cekim_turu: str = "medium"
    hareket: str = "static"
    asset_id: str = ""
    saglayici: str = ""
    kaynak_turu: str = "medya"        # medya | fallback | sentetik
    fallback_turu: str = ""
    kadraj: str = "tam"               # tam | punch-1.35 | punch-1.6 | ust | alt
    kaynak_aralik: tuple = (0.0, 0.0)  # varligin hangi saniye araligi
    ulke: str = ""
    tarih: str = ""
    gerekce: str = ""
    uyarilar: list = field(default_factory=list)


def _kadraj_sec(indeks: int, cekim_turu: str) -> str:
    """Deterministik kadraj. Ardil cekimlerde farkli olmasi surekliligi korur."""
    if cekim_turu in ("document", "map", "data"):
        return "tam"
    return ("tam", "punch-1.35", "ust", "punch-1.6", "alt")[indeks % 5]


def _hareket_sec(cekim_turu: str, indeks: int, yasak: str = "") -> str:
    adaylar = [h for h in CEKIM_HAREKET.get(cekim_turu, ("static",)) if h != yasak]
    if not adaylar:
        adaylar = list(CEKIM_HAREKET.get(cekim_turu, ("static",)))
    return adaylar[indeks % len(adaylar)]


def _varlik_sec(beat, adaylar: list, kullanilan_asset: set,
                son_saglayici: str, saglayici_sayaci: dict,
                saglayici_tavani: int) -> tuple:
    """Beat icin en uygun kullanilabilir varligi sec.

    Faz B'nin %40 saglayici kotasi BURAYA DA tasinir (kullanicinin istegi):
    kurgu katmani kotayi yok sayarsa Faz B'nin garantisi anlamsiz kalir.
    Doner: (aday | None, gerekce)
    """
    uygun = [a for a in adaylar
             if a.get("render_kullanilabilir") and a.get("asset_id")]
    if not uygun:
        return None, "kullanilabilir aday yok"
    # 1) Daha once kullanilmamis olanlar
    yeni = [a for a in uygun if a["asset_id"] not in kullanilan_asset]
    havuz = yeni or uygun
    tekrar_zorunlu = not yeni
    # 2) Kota dolu saglayicilari ele
    kotasiz = [a for a in havuz
               if saglayici_sayaci.get(a.get("saglayici", ""), 0) < saglayici_tavani]
    if kotasiz:
        havuz = kotasiz
    else:
        return None, (f"tum adaylarin saglayici kotasi dolu "
                      f"(tavan {saglayici_tavani}/saglayici)")
    # 3) Ardil ayni saglayiciyi tercih etme (cesitlilik)
    farkli = [a for a in havuz if a.get("saglayici") != son_saglayici]
    if farkli:
        havuz = farkli
    havuz = sorted(havuz, key=lambda a: -float(a.get("toplam_skor") or 0))
    sec = havuz[0]
    gerekce = f"puan {sec.get('toplam_skor')}"
    if tekrar_zorunlu:
        gerekce += " | TEKRAR: yeni aday kalmadi"
    return sec, gerekce


def gramer_uygula(beatler: list, *, sahne_adaylari: dict,
                  kapsam_bosluklari: Optional[dict] = None,
                  saglayici_tavani: int = 4) -> list:
    """Beat listesini Cekim listesine cevir.

    `sahne_adaylari`: {scene_id: [aday_sozlugu, ...]}  (Faz B AdayManifesti'nden)
    `kapsam_bosluklari`: {scene_id: {"onerilen_fallback": {...}}}
    """
    kapsam_bosluklari = kapsam_bosluklari or {}
    cikti: list = []
    kullanilan_asset: set = set()
    saglayici_sayaci: dict = {}
    son_saglayici, son_hareket, son_kadraj, son_asset = "", "", "", ""

    for i, b in enumerate(beatler):
        tercihler = ISLEV_CEKIM.get(b.islev, ("medium",))
        adaylar = sahne_adaylari.get(b.scene_id) or []
        bosluk = kapsam_bosluklari.get(b.scene_id)

        c = Cekim(beat_id=b.beat_id, scene_id=b.scene_id, fact_id=b.fact_id)

        sec, gerekce = _varlik_sec(b, adaylar, kullanilan_asset, son_saglayici,
                                   saglayici_sayaci, saglayici_tavani)
        if sec is None:
            # ── COVERAGE GAP: rastgele stok YOK, gerekceli fallback ──
            f = (bosluk or {}).get("onerilen_fallback") or {}
            ftur = f.get("tur") or "motion-graphic"
            c.kaynak_turu = "fallback"
            c.fallback_turu = ftur
            c.cekim_turu = FALLBACK_CEKIM.get(ftur, "data")
            c.hareket = _hareket_sec(c.cekim_turu, i, son_hareket)
            c.kadraj = "tam"
            c.gerekce = (f"coverage_gap -> {ftur}: "
                         f"{f.get('gerekce') or gerekce}")
            c.uyarilar.append("KAPSAM-BOSLUK")
        else:
            c.asset_id = sec["asset_id"]
            c.saglayici = sec.get("saglayici", "")
            c.ulke = sec.get("ulke") or sec.get("konum") or ""
            c.tarih = sec.get("tarih") or ""
            # Cekim turu: adayin sahne amacina uyan ilk tercih
            aday_amaci = sec.get("sahne_amaci") or ""
            eslesen = next((t for t in tercihler
                            if t in _amac_cekim(aday_amaci)), tercihler[0])
            c.cekim_turu = eslesen
            c.kaynak_turu = "medya"
            c.hareket = _hareket_sec(eslesen, i, son_hareket)
            c.kadraj = _kadraj_sec(i, eslesen)
            c.kaynak_aralik = (0.0, round(min(b.sure_sn, 12.0), 2))
            c.gerekce = gerekce
            kullanilan_asset.add(c.asset_id)
            saglayici_sayaci[c.saglayici] = saglayici_sayaci.get(c.saglayici, 0) + 1

        # ── SUREKLILIK KURALLARI ──
        if c.asset_id and c.asset_id == son_asset:
            # Ayni varlik ust uste: kadraj ve hareket MUTLAKA degismeli
            if c.kadraj == son_kadraj:
                c.kadraj = _kadraj_sec(i + 1, c.cekim_turu)
            if c.hareket == son_hareket:
                c.hareket = _hareket_sec(c.cekim_turu, i + 2, son_hareket)
            c.uyarilar.append("ARDIL-AYNI-VARLIK: kadraj+hareket degistirildi")
        if c.hareket == son_hareket and c.hareket != "static":
            c.hareket = _hareket_sec(c.cekim_turu, i + 1, son_hareket)
            c.uyarilar.append("ARDIL-AYNI-HAREKET: degistirildi")
        if c.kadraj == son_kadraj and c.kadraj != "tam":
            c.kadraj = _kadraj_sec(i + 3, c.cekim_turu)
            c.uyarilar.append("ARDIL-AYNI-KADRAJ: degistirildi")

        cikti.append(c)
        son_saglayici = c.saglayici or son_saglayici
        son_hareket, son_kadraj, son_asset = c.hareket, c.kadraj, c.asset_id
    return cikti


def _amac_cekim(sahne_amaci: str) -> tuple:
    """Faz B sahne amaci -> gramer cekim turleri."""
    return {
        "establishing": ("establishing", "atmospheric"),
        "ortam": ("medium", "atmospheric", "establishing"),
        "detay": ("close-detail", "medium"),
        "arsiv": ("archive", "document"),
        "belge": ("document", "data"),
        "harita": ("map",),
        "kisi": ("medium", "close-detail"),
    }.get(str(sahne_amaci or ""), CEKIM_TURLERI)


def sureklilik_denetimi(cekimler: list) -> list:
    """Plan uzerinde ardil tekrar ihlallerini bul (QA icin)."""
    sorunlar = []
    for i in range(1, len(cekimler)):
        a, b = cekimler[i - 1], cekimler[i]
        if a.asset_id and a.asset_id == b.asset_id:
            if a.kadraj == b.kadraj and a.hareket == b.hareket:
                sorunlar.append({"kod": "SUREKLILIK-AYNI-CEKIM",
                                 "beat_id": b.beat_id,
                                 "detay": f"ayni varlik+kadraj+hareket ({a.asset_id})"})
        if a.saglayici and a.saglayici == b.saglayici and a.kaynak_turu == "medya":
            sorunlar.append({"kod": "SUREKLILIK-AYNI-SAGLAYICI",
                             "beat_id": b.beat_id, "seviye": "uyari",
                             "detay": f"ardil ayni saglayici ({a.saglayici})"})
        if a.hareket == b.hareket and a.hareket != "static":
            sorunlar.append({"kod": "SUREKLILIK-AYNI-HAREKET",
                             "beat_id": b.beat_id, "seviye": "uyari",
                             "detay": f"ardil ayni hareket ({a.hareket})"})
    return sorunlar


def entity_denetimi(cekimler: list, *, beklenen_ulke: str = "",
                    beklenen_donem: str = "") -> list:
    """Yanlis yer/donem riski. Faz B vision kapisinin kurgu katmanindaki karsiligi."""
    sorunlar = []
    bu = str(beklenen_ulke or "").lower()
    for c in cekimler:
        if c.kaynak_turu != "medya":
            continue
        if bu:
            metin = f"{c.ulke}".lower()
            if metin and bu not in metin and metin not in bu:
                sorunlar.append({"kod": "ENTITY-YER", "beat_id": c.beat_id,
                                 "seviye": "uyari",
                                 "detay": f"beklenen '{beklenen_ulke}', varlik '{c.ulke}'"})
        # ⚠ ARSIV/BELGE cekimi FARKLI DONEMDEN OLMAK ZORUNDA. 1985 gazete
        # goruntusu "1980'lerde gazetelerde gorunmeye basladi" iddiasinin
        # KANITIDIR. Ilk surumde bu FAIL uretiyordu (test yakaladi).
        if c.cekim_turu in ("archive", "document"):
            continue
        if beklenen_donem and c.tarih:
            try:
                yil = int(str(c.tarih)[:4])
                hedef = int(str(beklenen_donem)[:4])
                if abs(yil - hedef) > 25:
                    sorunlar.append({"kod": "ENTITY-DONEM", "beat_id": c.beat_id,
                                     "detay": f"varlik {yil}, anlatim {hedef}"})
            except ValueError:
                pass
    return sorunlar
