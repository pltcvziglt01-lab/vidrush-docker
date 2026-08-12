#!/usr/bin/env python3
"""KARE KAPISI — indirilen klibin GERCEK karesine bakarak yer/donem/biyom kapisi.

⚠ NEDEN VAR — FAZ H'NIN BELGELENMIS SINIRI (FAZ-H-HANDOFF.md §13 "Bilinen sinir"):

    sorgu   : "small boat South Georgia sea storm"
    secilen : "maltese pilot motorboat"        (Pexels)
    kapi    : TETIKLENMEDI

Malta Akdeniz'dir; Guney Georgia sub-Antarktik. Ama:
  - `kaynak._yer_dogru_mu` YER_TAKMA_AD'daki 19 ULKEYE bagli — ikisi de tabloda yok.
  - `medya_kapisi.biyom_kapisi` IKLIM KUSAGI celiskisine bakar — "maltese pilot
    motorboat" metni ne tropik ne col isareti tasir, celiski cikmaz.
  - `kaynak._vision_yer_uygun` (kare bakan katman) YALNIZCA `yer_terim` doluyken
    calisir; tablo disi yerde `_etkin_yer()` bos doner -> **vision hic cagrilmaz**.

Yani metinle yakalanamayan hatalar icin kare bakan katman vardi ama tam da
gerektigi durumda devre disiydi. Bu modul o kapiyi tablo BAGIMSIZ hale getirir.

⚠ TASARIM KURALLARI (Faz H kurallarinin devami — bozma)
1. **KARAR SAF.** `karar()` ag/dosya/saat gormez; girdisi gozlem sozlugudur.
   Boylece gercek vision olmadan da testlenebilir (Malta vakasi testte kilitli).
2. **EMIN DEGILSEN GECIR.** Yanlis pozitif (dogru klibi atmak) da kalite kaybidir.
   Guven esigin altindaysa, bolge cikmiyorsa, yakin plan ise -> GECER.
3. **HAVZA KURALI, ULKE KURALI DEGIL.** Fransa'nin Akdeniz kiyisi "akdeniz"
   bolgesi olarak okunabilir; bu bir hata degildir. Bu yuzden red yalnizca
   HAVZA (kabaca kita/deniz havzasi) farkliysa verilir.
4. **KATI SINIR.** Cagri sayisi, USD ve duvar saati ayri ayri tavanlidir.
   Tavan dolunca kapi SESSIZCE kapanmaz — "butce doldu" gerekcesiyle GECIRIR
   ve bunu deftere yazar.
5. **SESSIZ DUSUS YOK.** Her karar bir kod + gerekce dizesi dondurur.
6. **GENISLETILEBILIR.** Yeni yer eklemek = BOLGE tablosuna bir satir. Kod degismez.
"""
from __future__ import annotations

import re
import threading
import time

try:                                  # paket icinden de, duz yoldan da calissin
    import medya_kapisi as _mk
except Exception:                     # pragma: no cover
    from webapp import medya_kapisi as _mk  # type: ignore


# ───────────────────────────── BOLGE TABLOSU ─────────────────────────────
# bolge_kimligi -> (terimler, kusak, havza)
#   kusak : medya_kapisi'nin biyom kimlikleriyle AYNI sozluk (kutup/tropik/col/iliman)
#   havza : kabaca kita/deniz havzasi. RED yalnizca havza farkinda verilir (kural 3).
#
# ⚠ Bu tablo TAM DUNYA HARITASI DEGIL ve oyle oldugunu iddia etmiyor. Kapsam
# `kapsam_ozeti()` ile olculebilir; tabloda olmayan yer icin kapi biyoma duser.
BOLGE = {
    "sub_antarktik": (
        ("south georgia", "grytviken", "king haakon", "stromness",
         "elephant island", "weddell sea", "drake passage", "falkland",
         "south sandwich", "tierra del fuego", "cape horn", "ushuaia",
         "patagonia", "shackleton"),
        "kutup", "guney_kutup"),
    "antarktika": (
        ("antarctica", "antarctic", "mcmurdo", "ross sea", "ross ice shelf",
         "south pole", "vostok station", "palmer station"),
        "kutup", "guney_kutup"),
    "kuzey_kutup": (
        ("arctic", "greenland", "svalbard", "spitsbergen", "nunavut",
         "north pole", "lapland", "tromso", "siberia", "yukon", "alaska",
         "iceland", "reykjavik", "baffin"),
        "kutup", "kuzey_kutup"),
    "akdeniz": (
        ("mediterranean", "malta", "maltese", "valletta", "gozo", "sicily",
         "sicilian", "sardinia", "cyprus", "crete", "santorini", "aegean",
         "adriatic", "dubrovnik", "amalfi", "ibiza", "mallorca", "corsica",
         "greece", "greek island"),
        "iliman", "avrupa_akdeniz"),
    "bati_avrupa": (
        ("france", "french", "paris", "germany", "german", "berlin", "munich",
         "netherlands", "amsterdam", "belgium", "brussels", "britain",
         "british", "england", "london", "scotland", "ireland", "dublin",
         "switzerland", "swiss", "alps", "zurich", "vienna", "austria",
         "italy", "italian", "rome", "venice", "spain", "spanish", "madrid",
         "portugal", "lisbon", "norway", "sweden", "denmark", "finland"),
        "iliman", "avrupa_akdeniz"),
    "anadolu": (
        ("turkey", "turkish", "istanbul", "ankara", "izmir", "cappadocia",
         "anatolia", "bosphorus", "antalya", "pamukkale", "ephesus"),
        "iliman", "avrupa_akdeniz"),
    "kuzey_afrika": (
        ("sahara", "morocco", "moroccan", "marrakech", "egypt", "egyptian",
         "cairo", "giza", "nile", "tunisia", "algeria", "libya"),
        "col", "afrika_kuzey"),
    "afrika_sahra_alti": (
        ("kenya", "tanzania", "serengeti", "savanna", "savannah", "masai",
         "kilimanjaro", "south africa", "cape town", "namibia", "botswana",
         "zanzibar", "ethiopia", "nigeria", "ghana", "senegal"),
        "tropik", "afrika_guney"),
    "orta_dogu": (
        ("dubai", "abu dhabi", "united arab emirates", "saudi arabia",
         "riyadh", "qatar", "doha", "oman", "muscat", "arabian desert",
         "jordan", "petra", "israel", "jerusalem", "iran", "tehran",
         "iraq", "baghdad", "kuwait"),
        "col", "orta_dogu"),
    "dogu_asya": (
        ("japan", "japanese", "tokyo", "kyoto", "osaka", "shinjuku",
         "shibuya", "okinawa", "korea", "korean", "seoul", "busan",
         "china", "chinese", "beijing", "shanghai", "hong kong", "taiwan",
         "mongolia"),
        "iliman", "asya_dogu"),
    "guney_asya": (
        ("india", "indian", "delhi", "mumbai", "kerala", "rajasthan",
         "nepal", "kathmandu", "himalaya", "everest", "sri lanka",
         "bangladesh", "pakistan", "bhutan"),
        "iliman", "asya_guney"),
    "guneydogu_asya": (
        ("thailand", "bangkok", "vietnam", "hanoi", "indonesia", "jakarta",
         "bali", "philippines", "manila", "malaysia", "kuala lumpur",
         "singapore", "cambodia", "angkor", "myanmar", "laos"),
        "tropik", "asya_guneydogu"),
    "kuzey_amerika": (
        ("usa", "united states", "america", "american", "new york",
         "california", "los angeles", "san francisco", "texas", "chicago",
         "florida", "miami", "canada", "toronto", "vancouver", "montreal",
         "mexico", "mexico city"),
        "iliman", "amerika_kuzey"),
    "guney_amerika": (
        ("brazil", "brazilian", "rio de janeiro", "sao paulo", "amazon",
         "amazonia", "argentina", "buenos aires", "peru", "machu picchu",
         "cusco", "chile", "santiago", "bolivia", "colombia", "andes"),
        "tropik", "amerika_guney"),
    "karayip": (
        ("caribbean", "bahamas", "jamaica", "cuba", "havana", "barbados",
         "dominican republic", "puerto rico", "aruba", "antigua"),
        "tropik", "karayip"),
    "pasifik": (
        ("hawaii", "honolulu", "tahiti", "fiji", "polynesia", "samoa",
         "maldives", "bora bora", "guam", "micronesia", "vanuatu"),
        "tropik", "pasifik"),
    "okyanusya": (
        ("australia", "australian", "sydney", "melbourne", "brisbane",
         "outback", "great barrier reef", "new zealand", "auckland",
         "queenstown", "tasmania"),
        "iliman", "okyanusya"),
}

# HAVZA KOMSULUGU: ayni satirdakiler arasinda RED VERILMEZ (kural 3).
# ⚠ Neden gerekli: "Fransa" isteyip kadraja Akdeniz kiyisi gelmesi hata degil;
# "Patagonya" isteyip Ge. Amerika manzarasi gelmesi de hata degil.
KOMSU_HAVZA = (
    {"avrupa_akdeniz", "afrika_kuzey", "orta_dogu"},
    {"guney_kutup", "amerika_guney"},
    {"kuzey_kutup", "amerika_kuzey", "avrupa_akdeniz"},
    {"asya_guney", "asya_guneydogu", "asya_dogu"},
    {"karayip", "amerika_kuzey", "amerika_guney"},
    {"pasifik", "okyanusya", "asya_guneydogu"},
    {"afrika_guney", "afrika_kuzey"},
)

# Gozlemin reddi tetikleyebilmesi icin gereken en dusuk guven (kural 2).
GUVEN_ESIGI = 0.6
# Tek kare okumasinin varsayilan birim maliyeti (gpt-4.1-mini, detail=low).
# ⚠ Olculmus deger degil, SAGLAYICI FIYAT TABLOSUNDAN turetilmis ust sinir;
# defterin amaci tavani zorlamak, fatura tahmini yapmak degil.
KARE_BIRIM_USD = 0.0008

_KELIME_SINIRI = r"(?<![0-9a-zà-ÿğüşıöç])%s(?![0-9a-zà-ÿğüşıöç])"


def _gecer_mi(terim: str, metin: str) -> bool:
    return re.search(_KELIME_SINIRI % re.escape(terim), metin) is not None


def bolge_bul(metin: str) -> set:
    """Metnin ele verdigi bolge kimlikleri. Tabloda karsiligi yoksa bos kume."""
    d = " " + str(metin or "").lower() + " "
    return {b for b, (terimler, _k, _h) in BOLGE.items()
            if any(_gecer_mi(t, d) for t in terimler)}


def havzalar(bolgeler) -> set:
    return {BOLGE[b][2] for b in bolgeler if b in BOLGE}


def kusaklar(bolgeler) -> set:
    return {BOLGE[b][1] for b in bolgeler if b in BOLGE}


def _komsu_mu(h1: str, h2: str) -> bool:
    if h1 == h2:
        return True
    return any({h1, h2} <= grup for grup in KOMSU_HAVZA)


def kapsam_ozeti() -> dict:
    """Tablonun GERCEK kapsami — 'her yeri biliyoruz' iddiasi kurmamak icin."""
    return {"bolge": len(BOLGE),
            "terim": sum(len(t) for t, _k, _h in BOLGE.values()),
            "havza": len({h for _t, _k, h in BOLGE.values()}),
            "komsu_grup": len(KOMSU_HAVZA)}


# ───────────────────────────── BEKLENTI ─────────────────────────────

def beklenti_kur(sahne_metni: str, video_baglami: str = "",
                 varliklar=None) -> dict:
    """Sahnenin NE OLMASI GEREKTIGI — hepsi metinden, LLM'siz.

    Sahne sorgusu bolge/biyom vermiyorsa videonun genel konusuna DUSER
    (Shackleton isinde tam bu gerekmisti).
    """
    sahne = str(sahne_metni or "")
    baglam = str(video_baglami or "")
    bolge = bolge_bul(sahne) or bolge_bul(baglam)
    biyom = _mk.biyom_bul(sahne) or _mk.biyom_bul(baglam)
    if not biyom and bolge:
        biyom = {k for k in kusaklar(bolge) if k in _mk.CELISEN}
    return {
        "bolgeler": sorted(bolge),
        "havzalar": sorted(havzalar(bolge)),
        "biyomlar": sorted(biyom),
        "tarihsel": bool(_mk.tarihsel_mi(sahne) or _mk.tarihsel_mi(baglam)),
        "varliklar": [str(v).lower() for v in (varliklar or []) if str(v).strip()],
        "kaynak": ("sahne" if bolge_bul(sahne) or _mk.biyom_bul(sahne)
                   else "baglam" if bolge or biyom else "yok"),
    }


# ───────────────────────────── KARAR (SAF) ─────────────────────────────

def karar(beklenti: dict, gozlem: dict) -> tuple:
    """(ok, kod, gerekce) — kareye bakan modelin gozlemini beklentiyle karsilastir.

    `gozlem` sozlugu (kare okuyucu doldurur, hepsi opsiyonel):
        yer_tahmini   : str   — "Malta, Mediterranean harbour"
        biyom         : str   — "tropik" / "kutup" / serbest metin
        isaretler     : list  — gorunen ipuclari ("palm trees", "latin signage")
        modern_isaret : list  — ("smartphone", "solar panel")
        yakin_plan    : bool  — kulturel ipucu tasimayan makro cekim
        insan         : bool
        guven         : float 0..1

    ⚠ Bu fonksiyon SAFTIR: ag yok, dosya yok, saat yok. Testler Malta vakasini
    dogrudan buradan kilitler.
    """
    if not isinstance(gozlem, dict) or not gozlem:
        return True, "GOZLEM-YOK", "kare okunamadi — kapi uygulanmadi"

    try:
        guven = float(gozlem.get("guven", 0.0) or 0.0)
    except Exception:
        guven = 0.0

    ham = " ".join(str(x) for x in (
        gozlem.get("yer_tahmini") or "",
        " ".join(str(i) for i in (gozlem.get("isaretler") or [])),
    ))

    if guven < GUVEN_ESIGI:
        return True, "DUSUK-GUVEN", (
            f"gozlem guveni {guven:.2f} < {GUVEN_ESIGI} — kapi uygulanmadi")

    # Yakin plan + kulturel ipucu yok -> her yerde cekilmis olabilir (kural 2)
    if bool(gozlem.get("yakin_plan")) and not (bolge_bul(ham) or
                                               str(gozlem.get("biyom") or "")):
        return True, "YAKIN-PLAN", "kulturel ipucu tasimayan yakin plan — gecti"

    # ── 1) DONEM ──
    modern = [str(m).lower() for m in (gozlem.get("modern_isaret") or []) if str(m).strip()]
    if beklenti.get("tarihsel") and modern:
        return False, "DONEM", (
            f"DONEM CELISKISI: tarihsel sahnede kareye bakan okuma modern "
            f"isaret gordu {modern[:3]}")

    # ── 2) BIYOM ──
    bek_biyom = set(beklenti.get("biyomlar") or [])
    goz_biyom = _mk.biyom_bul(str(gozlem.get("biyom") or "")) | _mk.biyom_bul(ham)
    g_ham = str(gozlem.get("biyom") or "").strip().lower()
    if g_ham in _mk.CELISEN:
        goz_biyom.add(g_ham)
    for b in bek_biyom:
        ortak = set(_mk.CELISEN.get(b, ())) & goz_biyom
        if ortak and b not in goz_biyom:
            return False, "BIYOM", (
                f"BIYOM CELISKISI (kare): sahne '{b}' kusagi, karede "
                f"'{'/'.join(sorted(ortak))}' kusagi")

    # ── 3) BOLGE / HAVZA ──
    bek_havza = set(beklenti.get("havzalar") or [])
    goz_bolge = bolge_bul(ham)
    goz_havza = havzalar(goz_bolge)
    if bek_havza and goz_havza:
        if goz_havza & bek_havza:
            pass                                    # dogrudan isabet
        elif any(_komsu_mu(a, b) for a in bek_havza for b in goz_havza):
            pass                                    # komsu havza — red YOK (kural 3)
        else:
            return False, "HAVZA", (
                f"YER CELISKISI (kare): beklenen havza "
                f"{'/'.join(sorted(bek_havza))} ({'/'.join(beklenti['bolgeler'])}), "
                f"karede {'/'.join(sorted(goz_havza))} "
                f"({'/'.join(sorted(goz_bolge))})")
    elif bek_havza and not goz_havza:
        return True, "BOLGE-CIKMADI", (
            "karede taninan bolge yok — kapi bolgeye uygulanmadi")

    # ── 4) VARLIK (yalnizca model ACIKCA uyumsuz derse) ──
    if beklenti.get("varliklar") and gozlem.get("konu_uyumu") is False:
        return False, "VARLIK", (
            f"KONU CELISKISI (kare): beklenen varliklar "
            f"{beklenti['varliklar'][:3]} karede yok")

    return True, "GECTI", (
        f"kare uyumlu (beklenen={beklenti.get('bolgeler') or beklenti.get('biyomlar') or '-'}, "
        f"gozlem={sorted(goz_bolge) or sorted(goz_biyom) or '-'})")


# ───────────────────────────── BUTCE ─────────────────────────────

class KareButce:
    """Cagri / USD / duvar saati tavani. Ucu de KATI (kural 4).

    ⚠ `maks_*` degerleri None GECILEMEZ — sinirsiz butce Faz H'de yasaklandi
    (`arastirma.butce` ile ayni kural). Sifir gecmek kapiyi kapatir, sinirsiz yapmaz.

    ⚠ THREAD GUVENLI: `kaynak._sahne_medya` PARALEL thread'lerde kosar. Kilitsiz
    sayacla iki thread ayni anda `harca()` cagirinca sayim dusuk kalir ve tavan
    asilir — yani "kati sinir" iddiasi karsiliksiz olurdu.
    """

    def __init__(self, maks_cagri: int = 40, maks_usd: float = 0.05,
                 maks_sn: float = 90.0, saat=None):
        if maks_cagri is None or maks_usd is None or maks_sn is None:
            raise ValueError("KareButce: sinirsiz butce yasak — sayi ver")
        self.maks_cagri = int(maks_cagri)
        self.maks_usd = float(maks_usd)
        self.maks_sn = float(maks_sn)
        self._saat = saat or time.monotonic
        self._kilit = threading.Lock()
        self.baslangic = self._saat()
        self.cagri = 0
        self.usd = 0.0
        self.engel = []          # butce yuzunden atlanan kararlar (sessiz degil)

    def uygun_mu(self) -> tuple:
        with self._kilit:
            return self._uygun_mu()

    def _uygun_mu(self) -> tuple:
        if self.cagri >= self.maks_cagri:
            return False, f"cagri tavani doldu ({self.cagri}/{self.maks_cagri})"
        if self.usd + KARE_BIRIM_USD > self.maks_usd:
            return False, f"USD tavani doldu (${self.usd:.4f}/${self.maks_usd:.4f})"
        gecen = self._saat() - self.baslangic
        if gecen >= self.maks_sn:
            return False, f"sure tavani doldu ({gecen:.1f}/{self.maks_sn:.0f} sn)"
        return True, "butce uygun"

    def yer_ayir(self) -> tuple:
        """Kontrol + harcamayi TEK kilit altinda yap (kontrol-sonra-harca yarisi yok).

        (ok, neden). ok=True ise cagri hakki ZATEN dusulmustur; cagri basarisiz
        olsa bile geri alinmaz — saglayiciya istek gitmis sayilir, tavan boyle korunur.
        """
        with self._kilit:
            ok, neden = self._uygun_mu()
            if ok:
                self.cagri += 1
                self.usd = round(self.usd + KARE_BIRIM_USD, 6)
            elif len(self.engel) < 20:
                self.engel.append(neden)
            return ok, neden

    def harca(self, usd: float = KARE_BIRIM_USD) -> None:
        with self._kilit:
            self.cagri += 1
            self.usd = round(self.usd + float(usd), 6)

    def engelle(self, neden: str) -> None:
        with self._kilit:
            if len(self.engel) < 20:
                self.engel.append(neden)

    def ozet(self) -> dict:
        with self._kilit:
            return {"cagri": self.cagri, "maks_cagri": self.maks_cagri,
                    "usd": round(self.usd, 5), "maks_usd": self.maks_usd,
                    "gecen_sn": round(self._saat() - self.baslangic, 2),
                    "maks_sn": self.maks_sn, "engel": list(self.engel)}


# ───────────────────────── UCTAN UCA KAPI ─────────────────────────

def kare_kapisi(sahne_metni: str, video_baglami: str, okuyucu,
                *, butce: KareButce = None, varliklar=None,
                onbellek: dict = None, kimlik: str = "") -> tuple:
    """(ok, kod, gerekce). `okuyucu()` kareyi okuyup gozlem sozlugu dondurur.

    `okuyucu` cagrilabilir olmali; None ise kapi UYGULANMAZ (anahtarsiz kosu).
    Okuyucu istisna firlatirsa kapi GECIRIR — tek bir vision hatasi isi durdurmaz.
    """
    if okuyucu is None:
        return True, "OKUYUCU-YOK", "kare okuyucu yok — kapi uygulanmadi"

    if onbellek is not None and kimlik and kimlik in onbellek:
        ok, kod, ger = onbellek[kimlik]
        return ok, kod, f"{ger} (onbellek)"

    # ⚠ BEKLENTI ONCE: beklenti cikmiyorsa okuma da yapilmaz, butce de harcanmaz.
    beklenti = beklenti_kur(sahne_metni, video_baglami, varliklar)
    if not (beklenti["bolgeler"] or beklenti["biyomlar"] or beklenti["tarihsel"]):
        return True, "BEKLENTI-YOK", (
            "sahneden yer/biyom/donem beklentisi cikarilamadi — kapi uygulanmadi")

    if butce is not None:
        # Kontrol ve harcama TEK kilit altinda: paralel thread'lerde
        # "kontrol et sonra harca" yarisi tavani asirtir.
        uygun, neden = butce.yer_ayir()
        if not uygun:
            return True, "BUTCE", f"kare kapisi atlandi — {neden}"

    try:
        gozlem = okuyucu()
    except Exception as e:                     # tek hata isi durdurmaz (kural 2)
        return True, "OKUMA-HATASI", f"kare okunamadi: {str(e)[:70]}"

    ok, kod, gerekce = karar(beklenti, gozlem)
    if onbellek is not None and kimlik:
        onbellek[kimlik] = (ok, kod, gerekce)
    return ok, kod, gerekce
