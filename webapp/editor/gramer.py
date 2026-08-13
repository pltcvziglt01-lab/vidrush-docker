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
#
# ⚠ FAZ I-17 — KEN BURNS YON CESITLILIGI. Eski havuzlar 2-4 elemanliydi ve
# `medium` yalnizca ("push-in","pan-left","static") iceriyordu. Uzun cekimde
# `static` elenip bir onceki hareket de yasaklaninca GERIYE TEK ADAY kaliyor,
# bu yuzden `push-in` b001 ve b003'te TEKRAR ediyordu (I-16 ciktisinda
# olculdu). Havuzlar `motion.kamera_spec`in GERCEKTEN destekledigi yonlerle
# genisletildi.
#
# ⚠ `soft-zoom` KASITLI OLARAK YOK: `kamera_spec` onu spec'e "push-in" adiyla
# yaziyor, yani plan adi ile render adi ayrisirdi ve olcum yalan soylerdi.
# Sirlama IDIOMATIK: her turun en dogal hareketi basta, `static` en sonda
# (uzun cekimde zaten eleniyor).
CEKIM_HAREKET = {
    "establishing": ("pull-out", "pan-right", "push-in", "pan-left",
                     "slow-drift", "static"),
    "medium":       ("push-in", "pan-left", "pull-out", "pan-right",
                     "slow-drift", "static"),
    "close-detail": ("push-in", "slow-drift", "pull-out", "pan-right",
                     "static"),
    "archive":      ("push-in", "pull-out", "slow-drift", "pan-left",
                     "static"),
    "document":     ("document-scan", "push-in"),
    "map":          ("map-route", "static"),
    "data":         ("data-reveal", "static"),
    "atmospheric":  ("slow-drift", "pull-out", "pan-right", "push-in",
                     "static"),
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


# ⚠ FAZ I-17 — DURAGAN CEKIM SINIRI.
# I-16 ciktisinda `medium` cekimine `static` atandi ve sahne 5.21 sn boyunca
# ekranda neredeyse HIC DEGISMEDI (optik olcum: ortalama 0.914; hareketli
# sahneler 3.5-7.0). Hareketsiz bir FOTOGRAFI uzun sure hareketsiz tutmak
# belgesel dilinde bir karar degil, ihmal. Bu esigin USTUNDEKI cekimlerde
# `static` aday havuzundan CIKARILIR.
# Deger profilin `shot_min_sn`inden turetildi (1.5) — bir cekim boyu kadar
# duragan kalmak zaten sinirin ta kendisi.
DURAGAN_TAVAN_SN = 1.5

# Ardisik olmayan tekrari da onlemek icin bakilan pencere. I-16'da `push-in`
# b001 ve b003'te kullanildi; komsu olmadiklari icin eski kural GORMEDI.
HAREKET_PENCERESI = 3

# Acilis ve kapanis ritmi: belgesel dilinde acilis ICERI girer (push-in),
# kapanis GERI cekilir (pull-out). Yalnizca aday havuzunda varsa uygulanir;
# zorla enjekte edilmez.
RITIM_TERCIHI = {"hook": "push-in", "sonuc": "pull-out"}

# ═════════ MEDYA GEOMETRISI -> HAREKET AILESI (Faz I-24) ═════════
#
# ⚠ NEDEN: `Kamera.tsx > Zemin` `objectFit:'cover'` kullanir. Kaynak 16:9'dan
# GENISSE cover FAZLA GENISLIGI kirpar — yani goruntude YATAY pay vardir ve
# yatay pan kaynagin GERCEKTEN daha fazlasini gosterir. Kaynak 16:9'dan
# DARSA (or. 4:3) kirpma DIKEY olur; yatay pan ayni kirpimi kaydirmaktan
# ibarettir, yeni bilgi getirmez — o kaynakta iceri/disari hareket daha
# durusttur.
#
# ⚠ DURUST SINIR: bu bir YASAK DEGIL, DETERMINISTIK SIRALAMADIR. Havuzu
# asla bosaltmaz; yalnizca esit gecerli adaylar arasinda hangisinin once
# denenecegini belirler. Boylece mevcut gramer ve kullanici secimleri
# bozulmaz, yalnizca beraberlik geometriyle cozulur.
GEOMETRI_HAREKET = {
    "genis": ("pan-right", "pan-left", "slow-drift"),
    "dar":   ("push-in", "pull-out", "slow-drift"),
}
# 16:9'a bu bagil yakinlikta olan kaynak "notr" sayilir (siralama yapilmaz).
GEOMETRI_NOTR_BANDI = 0.02


def geometri_sinifi(genislik=None, yukseklik=None,
                    hedef_oran: float = 16.0 / 9.0) -> str:
    """Kaynagin hedef kareye gore YATAY mi DIKEY mi payi var? (saf fonksiyon)

    Doner: "genis" | "dar" | "notr" (olculemezse "notr" — emin degilsen
    siralamaya karisma).
    """
    try:
        g, y = float(genislik), float(yukseklik)
    except (TypeError, ValueError):
        return "notr"
    if g <= 0 or y <= 0 or hedef_oran <= 0:
        return "notr"
    oran = g / y
    if oran > hedef_oran * (1.0 + GEOMETRI_NOTR_BANDI):
        return "genis"
    if oran < hedef_oran * (1.0 - GEOMETRI_NOTR_BANDI):
        return "dar"
    return "notr"


def _hareket_sec(cekim_turu: str, indeks: int, yasak: str = "",
                 sure_sn=None, son_hareketler=(), islev: str = "",
                 acilis_hareketi: str = "", islev_hareketleri=(),
                 genislik=None, yukseklik=None) -> str:
    """Kamera hareketi sec.

    Faz I-17 ek parametreleri (hepsi OPSIYONEL — verilmezse eski davranis):
      `sure_sn`        : cekim suresi. `DURAGAN_TAVAN_SN`i asiyorsa `static`
                         aday havuzundan CIKARILIR.
      `son_hareketler` : son kullanilan hareketler (pencere). Icindekiler
                         SON TERCIH edilir; tumu doluysa eski davraniga duser.
      `islev`          : `hook`/`sonuc` icin acilis-kapanis ritmi tercihi.

    Faz I-24 ek parametreleri (hepsi OPSIYONEL — verilmezse eski davranis):
      `acilis_hareketi`   : KAPANIS cekiminde verilir; acilisin hareketi
                            havuzdan CIKARILIR (havuz bosalmadigi surece).
      `islev_hareketleri` : AYNI anlati islevinde daha once kullanilan
                            hareketler; CIKARILIR.
      `genislik/yukseklik`: kaynak olcusu — esit adaylar arasinda
                            DETERMINISTIK siralama icin (yasak degil).
    """
    taban = list(CEKIM_HAREKET.get(cekim_turu, ("static",)))
    adaylar = [h for h in taban if h != yasak]
    if not adaylar:
        adaylar = list(taban)

    # 0) I-24 SERT KISITLAR — acilis/kapanis ve islev tekrari.
    # ⚠ Havuzu ASLA bosaltmaz: filtre sonrasi bos kalirsa eski havuz korunur
    # (kusuru gizlemek icin degil, secimi COKERTMEMEK icin; kapi zaten
    # PRE-QA'da hukum veriyor ve gizli kalmiyor).
    _sert = {h for h in (list(islev_hareketleri or []) +
                         ([acilis_hareketi] if acilis_hareketi else [])) if h}
    if _sert:
        kalan = [h for h in adaylar if h not in _sert]
        if kalan:
            adaylar = kalan

    # 1) Uzun cekimde DURAGAN yasak (havuz tamamen bosalmadigi surece)
    if sure_sn is not None:
        try:
            uzun = float(sure_sn) > DURAGAN_TAVAN_SN
        except (TypeError, ValueError):
            uzun = False
        if uzun:
            hareketli = [h for h in adaylar if h != "static"]
            if hareketli:
                adaylar = hareketli

    # 2) PENCERE TEKRARI — yakin gecmiste kullanilmayani tercih et
    if son_hareketler:
        taze = [h for h in adaylar if h not in son_hareketler]
        if taze:
            adaylar = taze

    # 2b) MEDYA GEOMETRISI — beraberligi DETERMINISTIK coz (I-24).
    # Kararli siralama: tercih edilen aile basa alinir, geri kalan SIRASI
    # KORUNARAK arkaya. Havuz kucultulmez, yalnizca yeniden siralanir.
    _gsinif = geometri_sinifi(genislik, yukseklik)
    if _gsinif != "notr" and len(adaylar) > 1:
        _tercihli = GEOMETRI_HAREKET.get(_gsinif, ())
        adaylar = ([h for h in adaylar if h in _tercihli]
                   + [h for h in adaylar if h not in _tercihli])

    # 3) ACILIS/KAPANIS RITMI — ama CESITLILIGE TABI.
    # ⚠ Ilk surumde bu blok pencere kontrolunden ONCE donuyordu ve kapanis
    # icin `pull-out` zorlaniyordu; o hareket ortada zaten kullanildiginda
    # tekrar uretiyordu (I-17'nin ilk render'inda olculdu: b002 ve b004'un
    # ikisi de pull-out). Ritim bir TERCIHTIR, tekrar uretme pahasina
    # uygulanmaz — acilis ile kapanisin FARKLI olmasi zaten korunuyor.
    tercih = RITIM_TERCIHI.get(str(islev or ""))
    if tercih and tercih in adaylar and tercih != yasak:
        return tercih
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
    pencere: list = []          # Faz I-17: son hareketler penceresi
    # ── Faz I-24 durumu ──
    # `islev_kullanim`: anlati islevi -> o islevde KULLANILMIS hareketler.
    # `son_indeks`    : kapanis cekimi; acilisin hareketini tekrar edemez.
    islev_kullanim: dict = {}
    son_indeks = len(beatler) - 1

    for i, b in enumerate(beatler):
        _isl = str(getattr(b, "islev", "") or "")
        _islev_yasak = tuple(islev_kullanim.get(_isl) or ())
        # Acilis hareketi YALNIZCA kapanis cekiminde kisittir.
        _acilis_yasak = (cikti[0].hareket
                         if (i == son_indeks and i > 0 and cikti) else "")
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
            c.hareket = _hareket_sec(c.cekim_turu, i, son_hareket,
                                     sure_sn=b.sure_sn,
                                     son_hareketler=tuple(pencere),
                                     islev=_isl,
                                     acilis_hareketi=_acilis_yasak,
                                     islev_hareketleri=_islev_yasak)
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
            c.hareket = _hareket_sec(eslesen, i, son_hareket,
                                     sure_sn=b.sure_sn,
                                     son_hareketler=tuple(pencere),
                                     islev=_isl,
                                     acilis_hareketi=_acilis_yasak,
                                     islev_hareketleri=_islev_yasak,
                                     genislik=sec.get("genislik"),
                                     yukseklik=sec.get("yukseklik"))
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
                # ⚠ I-24: DUZELTME YOLLARI da ayni kisitlari tasimali; aksi
                # halde burasi acilis/islev tekrarini GERI GETIREBILIR.
                c.hareket = _hareket_sec(c.cekim_turu, i + 2, son_hareket,
                                         sure_sn=b.sure_sn,
                                         son_hareketler=tuple(pencere),
                                         acilis_hareketi=_acilis_yasak,
                                         islev_hareketleri=_islev_yasak)
            c.uyarilar.append("ARDIL-AYNI-VARLIK: kadraj+hareket degistirildi")
        if c.hareket == son_hareket and c.hareket != "static":
            c.hareket = _hareket_sec(c.cekim_turu, i + 1, son_hareket,
                                     sure_sn=b.sure_sn,
                                     son_hareketler=tuple(pencere),
                                     acilis_hareketi=_acilis_yasak,
                                     islev_hareketleri=_islev_yasak)
            c.uyarilar.append("ARDIL-AYNI-HAREKET: degistirildi")
        if c.kadraj == son_kadraj and c.kadraj != "tam":
            c.kadraj = _kadraj_sec(i + 3, c.cekim_turu)
            c.uyarilar.append("ARDIL-AYNI-KADRAJ: degistirildi")

        cikti.append(c)
        son_saglayici = c.saglayici or son_saglayici
        son_hareket, son_kadraj, son_asset = c.hareket, c.kadraj, c.asset_id
        pencere.append(c.hareket)
        del pencere[:-HAREKET_PENCERESI]
        # I-24: bu islevde kullanilan hareketi KAYDET (pencereden bagimsiz).
        if _isl and c.hareket:
            islev_kullanim.setdefault(_isl, set()).add(c.hareket)
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
