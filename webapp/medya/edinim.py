"""MEDYA EDINIM DAYANIKLILIGI ve KAYNAK CESITLENDIRME (Faz I-19).

⚠ NEDEN VAR — I-18'DE OLCULEN KUSUR:
Edinim hatti TEK saglayiciya (Wikimedia Commons) bagliydi. O saglayici
`HTTP 429 / Retry-After 600` verince hat TAMAMEN durdu ve ikinci konsept
pilotu uretilemedi. Uc ayri olcumde dogrulandi (ilk kosum, 11 dk sonrasi,
6 sabirli deneme) — gecici bir patlama siniri DEGIL.

Bu modul uc sey ekler:

  1. DEVRE KESICI (circuit breaker). Bir HOST arka arkaya `esik` kadar
     kalici hata verirse devre ACILIR ve o host `soguma` boyunca HIC
     DENENMEZ. Ayni hostu zorlamak hem bosa zaman hem de hiz sinirini
     uzatabilir.
  2. SIRALI SAGLAYICI ZINCIRI. Ilk saglayici duserse ikinciye gecilir.
     Gecis SURESI olculur — "hizli failover" bir iddia degil, sayidir.
  3. ARAMA/METADATA ile GERCEK BAYT AYRIMI. Bir saglayici metadata
     verip bayt vermeyebilir (I-18'de tam bu oldu). Ikisi AYRI sayilir:
     `metadata_bulundu` ve `bayt_indirildi`.

⚠ SERT KURALLAR:
  · TELIF/ATIF EKSIK MEDYA KESIN RED. Karar saglayici modullerinde degil
    `medya.lisans`tadir; burada yalnizca sonucu DOGRULANIR.
  · INDIRME saglayicinin `indir()`i uzerinden, o da `guvenli_indir`
    kullanir (SSRF duvari). Bu modul kendi indiricisini YAZMAZ.
  · YOUTUBE ya da izinsiz kaynak YOK. Saglayici listesi disaridan verilir
    ve bu modulde hicbir saglayici adresi gomulu degildir.
  · ONBELLEK: ayni URL ikinci kez INDIRILMEZ.
"""
from __future__ import annotations

import os
import time
from typing import Callable, Optional

# Bir host bu kadar ardisik KALICI hata verirse devre acilir.
DEVRE_ESIGI = 2
# Devre acikken host bu kadar saniye DENENMEZ.
DEVRE_SOGUMA_SN = 900.0
# `Retry-After` bu tavani asarsa beklemeyiz — devreyi acip SIRADAKINE geceriz.
# ⚠ I-18 olcumu: Wikimedia `Retry-After: 600` dondu. 600 sn beklemek bir
# render hattinda kabul edilemez; dogru davranis BEKLEMEK DEGIL, GECMEKTIR.
BEKLENEBILIR_TAVAN_SN = 30.0
# Kalici sayilan HTTP kodlari (gecici ag hatasi degil, sunucu reddi).
KALICI_KODLAR = (401, 403, 429, 451, 500, 502, 503, 504)

# ═════════════ EN-BOY ORANI UYUMLULUK KAPISI (Faz I-23) ═════════════
#
# ⚠ I-22'DE KALAN TEK FAIL'IN **OLCULEN** KOK NEDENI — devralinan aciklama
# YANLISTI ve burada duzeltiliyor:
#
#   Devralinan iddia : "s02 kaynagi 2048x3072 DIKEY; 16:9 karede PILLARBOX
#                       (yan siyah bant) veriyor."
#   OLCULEN GERCEK   : POST-KENAR-SIYAH'in 6/68 ihlalinin 6'si da
#                       **b002**'de (1.00-2.25 sn). b002'nin varligi s01'in
#                       YEDEGI `s01_..._1.jpg` = **2832x3603** (oran 0.786).
#                       s02 (2048x3072) b003'u besliyor ve **SIFIR** ihlal
#                       uretmis. Yani hem varlik hem mekanizma yanlis
#                       atfedilmisti.
#
# MEKANIZMA PILLARBOX **DEGIL**. `Kamera.tsx > Zemin` `objectFit: 'cover'`
# kullanir; kare TAMAMEN doludur. Olculdu: ihlal karesinde 0-200. sutunlar
# ort 8.2 / std 1.24 / min 6 / max 13 — yani GERCEK (koyu) fotograf icerigi.
# Sentetik bir bant SABIT olurdu (std 0), 8.2 degil 0 okunurdu.
#
# GERCEK MEKANIZMA — ASIRI COVER-CROP. 16:9'u 0.786 oranli bir kaynaktan
# `cover` ile doldurmak kaynagin yuksekliginin yalnizca %44'unu birakir;
# uzerine `punch-1.35` binince gorulen alan kaynagin ~%33'une duser. Geriye
# kalan dar dilim temsili olmayan bir golge koridoruydu: sol serit 8.2 <
# esik 16 -> POST-KENAR-SIYAH.
#
# ESIK NEREDEN GELIYOR (uydurma degil, AYNI render'dan olculdu):
#   korunan_oran = min(r/R, R/r)   (cover ile kaynaktan geriye kalan pay)
#     1.480 (4192x2832) -> 0.832  temiz, 0 ihlal
#     1.333 (3000x2250) -> 0.750  temiz, 0 ihlal   <- en DAR temiz olcum
#     1.332 (4986x3744) -> 0.750  temiz, 0 ihlal
#     0.786 (2832x3603) -> 0.442  IHLAL URETEN
#     0.667 (2048x3072) -> 0.375  (bu render'da ihlal uretmedi ama ayni
#                                  sinifta: kaynagin %62'si atiliyor)
# Sinir (0.442, 0.750] araliginda olmak zorunda. 0.70 secildi: en dar TEMIZ
# olcumun (0.750) hemen altinda, ihlal uretenin (0.442) cok uzerinde.
# 4:3 — kamu mali fotografin baskin formati — gecer; kare (0.562) ve
# dikey (0.442/0.375) gecmez.
#
# ⚠ DURUST SINIR: 5:4 (1.25 -> 0.703) bu esigi KIL PAYI geciyor ve
# olculmedi. Cok genis panorama da ayni formulle elenir (3:1 -> 0.593):
# yatayda %41 atmak da temsili olmayan bir dilim birakir.
HEDEF_ORAN_16_9 = 16.0 / 9.0
ORAN_EN_AZ_KORUNAN = 0.70


class DevreKesici:
    """Host bazli devre kesici. Saat DISARIDAN verilebilir (test icin)."""

    def __init__(self, *, esik: int = DEVRE_ESIGI,
                 soguma_sn: float = DEVRE_SOGUMA_SN,
                 saat: Optional[Callable] = None):
        self.esik = max(1, int(esik))
        self.soguma_sn = float(soguma_sn)
        self._saat = saat or time.monotonic
        self._sayac: dict = {}
        self._acilma: dict = {}

    def acik_mi(self, host: str) -> bool:
        """Devre ACIK mi (yani host atlanmali mi)?"""
        t = self._acilma.get(str(host or ""))
        if t is None:
            return False
        if self._saat() - t >= self.soguma_sn:
            self.sifirla(host)          # soguma bitti, yeniden denenebilir
            return False
        return True

    def basari(self, host: str) -> None:
        self.sifirla(host)

    def hata(self, host: str, *, kalici: bool = True) -> bool:
        """Hatayi isle. Doner: devre ACILDI mi."""
        h = str(host or "")
        if not kalici:
            return self.acik_mi(h)
        self._sayac[h] = self._sayac.get(h, 0) + 1
        if self._sayac[h] >= self.esik and h not in self._acilma:
            self._acilma[h] = self._saat()
            return True
        return h in self._acilma

    def sifirla(self, host: str) -> None:
        h = str(host or "")
        self._sayac.pop(h, None)
        self._acilma.pop(h, None)

    def ozet(self) -> dict:
        return {"esik": self.esik, "soguma_sn": self.soguma_sn,
                "ardisik_hata": dict(self._sayac),
                "acik_devreler": sorted(self._acilma)}


def _host(url: str) -> str:
    ham = str(url or "")
    if "//" in ham:
        ham = ham.split("//", 1)[1]
    return ham.split("/", 1)[0].lower()


def _kalici_mi(sonuc: dict) -> bool:
    kod = (sonuc or {}).get("http")
    if kod in KALICI_KODLAR:
        return True
    sebep = str((sonuc or {}).get("sebep") or "")
    return any(str(k) in sebep for k in KALICI_KODLAR)


def bekle_karari(sonuc: dict, *,
                 tavan_sn: float = BEKLENEBILIR_TAVAN_SN) -> dict:
    """`Retry-After`a gore BEKLE mi GEC mi?

    ⚠ Bu ayrim I-18'in dersi: sunucu 600 sn isteyince beklemek yanlis
    davranistir. Tavani asan istek "bekleme" degil "devreyi ac" demektir.
    """
    try:
        ra = float((sonuc or {}).get("retry_after") or 0)
    except (TypeError, ValueError):
        ra = 0.0
    if ra <= 0:
        return {"karar": "GEC", "retry_after": 0.0, "bekleme_sn": 0.0,
                "sebep": "Retry-After yok"}
    if ra > float(tavan_sn):
        return {"karar": "DEVRE-AC", "retry_after": ra, "bekleme_sn": 0.0,
                "sebep": f"Retry-After {ra} sn > tavan {tavan_sn} sn"}
    return {"karar": "BEKLE", "retry_after": ra, "bekleme_sn": ra,
            "sebep": f"Retry-After {ra} sn <= tavan {tavan_sn} sn"}


def _olcu_yeter(yol: str, aday: dict, en_az_genislik: int,
                okuyucu: Optional[Callable]) -> bool:
    """Indirilen dosyanin GERCEK genisligi yeterli mi?

    Okuyucu verilmezse ya da olcu okunamazsa GECIRILIR (emin degilsen
    engelleme) ama `olculen_olcu` alani None kalir — sahte olcu yazilmaz.
    """
    if not en_az_genislik or not callable(okuyucu):
        return True
    try:
        olcu = okuyucu(yol)
    except Exception:                                             # noqa: BLE001
        return True
    try:
        g = int((olcu or (0, 0))[0])
    except (TypeError, ValueError, IndexError):
        return True
    aday["olculen_olcu"] = list(olcu or (0, 0))
    if g <= 0:
        return True
    return g >= int(en_az_genislik)


def oran_karari(genislik, yukseklik, *,
                hedef_oran: float = HEDEF_ORAN_16_9,
                en_az_korunan: float = ORAN_EN_AZ_KORUNAN) -> dict:
    """Kaynak, hedef karede GUVENLE kullanilabilir mi? (saf fonksiyon)

    Olcut "oran farki" degil **cover ile kaynaktan geriye kalan pay**tir:
    `korunan = min(r/R, R/r)`. Cunku kusuru ureten sey oran sayisinin
    kendisi degil, kirpmanin kaynagin ne kadarini ATTIGIDIR.

    Ag/dosya KULLANMAZ; yalnizca olculmus iki sayiyi degerlendirir.
    """
    try:
        g, y = float(genislik), float(yukseklik)
    except (TypeError, ValueError):
        return {"olculdu": False, "sebep": "OLCU-OKUNAMADI", "uygun": True}
    try:
        hedef = float(hedef_oran)
    except (TypeError, ValueError):
        hedef = HEDEF_ORAN_16_9
    if g <= 0 or y <= 0 or hedef <= 0:
        # ⚠ EMIN DEGILSEN ENGELLEME — cozunurluk kapisiyla ayni sozlesme.
        return {"olculdu": False, "sebep": "OLCU-GECERSIZ", "uygun": True}
    try:
        taban = float(en_az_korunan)
    except (TypeError, ValueError):
        taban = ORAN_EN_AZ_KORUNAN
    oran = g / y
    korunan = min(oran / hedef, hedef / oran)
    if oran > hedef * 1.005:
        yon = "asiri-genis"
    elif oran >= hedef * 0.995:
        yon = "hedefe-uygun"
    elif oran < 0.95:
        yon = "dikey"
    elif oran < 1.05:
        yon = "kare"
    else:
        yon = "dar-yatay"          # yatay ama 16:9'dan dar (or. 4:3)
    uygun = korunan >= taban
    return {
        "olculdu": True,
        "olculen_olcu": [int(g), int(y)],
        "olculen_oran": round(oran, 4),
        "hedef_oran": round(hedef, 4),
        "korunan_oran": round(korunan, 4),
        "en_az_korunan": round(taban, 4),
        "atilan_oran": round(1.0 - korunan, 4),
        "yon": yon,
        "uygun": uygun,
        "sebep": "" if uygun else (
            f"ORAN-UYUMSUZ ({yon}): olculen {oran:.3f} vs hedef {hedef:.3f}; "
            f"cover kirpmasi kaynagin %{(1.0 - korunan) * 100:.0f}'ini atiyor "
            f"(korunan {korunan:.3f} < en az {taban:.3f})"),
    }


def _oran_yeter(yol: str, aday: dict, hedef_oran: float,
                en_az_korunan: float, okuyucu: Optional[Callable]) -> bool:
    """Indirilen dosyanin GERCEK en-boy orani hedef kareye uyuyor mu?

    ⚠ OLCUM PAYLASILIR: `_olcu_yeter` zaten olctuyse `olculen_olcu` doludur
    ve IKINCI bir ffprobe CALISTIRILMAZ. Kapi kapaliysa (hedef_oran=0)
    hicbir sey olculmez — geriye tam uyumlu.
    """
    if not hedef_oran:
        return True
    olcu = aday.get("olculen_olcu")
    if not olcu:
        if not callable(okuyucu):
            return True
        try:
            olcu = list(okuyucu(yol) or ())
        except Exception:                                         # noqa: BLE001
            return True
        if olcu:
            aday["olculen_olcu"] = list(olcu)
    try:
        g, y = int(olcu[0]), int(olcu[1])
    except (TypeError, ValueError, IndexError):
        return True
    karar = oran_karari(g, y, hedef_oran=hedef_oran,
                        en_az_korunan=en_az_korunan)
    aday["oran_karari"] = karar
    return bool(karar.get("uygun", True))


def saglayici_ozeti(toplanan) -> dict:
    """KULLANILAN saglayici ve dagilim — YALNIZ TOPLANAN varliklardan.

    ⚠ NEDEN VAR — I-35'TE OLCULEN TUTARSIZLIK:
    `kullanilan_saglayici` zinciri ERKEN DONUS anindaki saglayiciya (`ad`)
    esitleniyordu. Gercek vaka (I-33, s01): Commons BIR varlik indirdi (vitrin),
    sonra 429 aldi; NASA ikinciyi verdi ve erken donus `kullanilan_saglayici`yi
    **nasa** yazdi. Oysa KABUL EDILEN ilk varlik (b001) **wikimedia**'dandi.
    Rapor ayrica Commons denemesini `BAYT-YOK` gosteriyordu — bayt GELMISTI.
    Sonuc: "hangi saglayici neyi verdi" sorusu uc atom boyunca yaniltici
    cevaplandi.

    Artik hukum SEcILEN VARLIKLARDAN turer; son hata genel saglayiciyi
    degistiremez. Ag/dosya KULLANMAZ.
    """
    liste = [t for t in (toplanan or []) if isinstance(t, dict)]
    dagilim: dict = {}
    for t in liste:
        s = str(t.get("kaynak_saglayici") or "")
        if s:
            dagilim[s] = dagilim.get(s, 0) + 1
    return {
        "kullanilan_saglayici": (str(liste[0].get("kaynak_saglayici") or "")
                                 if liste else ""),
        "saglayici_dagilimi": dagilim,
        "toplanan_adet": len(liste),
    }


def _indir_tek(modul, aday: dict, hedef_yol: str) -> dict:
    """Saglayicidan TEK deneme iste — yeniden deneme politikasi BU MODULUN.

    ⚠ I-19'da olculdu: `commons.indir` kendi icinde 3 kez deniyordu ve
    devre kesici devreye girmeden once 103.8 sn harcaniyordu. Iki katmanin
    da yeniden denemesi "hizli failover" iddiasini karsiliksiz birakir.
    Saglayici `deneme` parametresini desteklemiyorsa eski cagriya duser.
    """
    try:
        return modul.indir(aday, hedef_yol, deneme=1)
    except TypeError:
        pass
    except Exception as e:                                        # noqa: BLE001
        return {"ok": False, "sebep": f"{type(e).__name__}: {str(e)[:100]}"}
    try:
        return modul.indir(aday, hedef_yol)
    except Exception as e:                                        # noqa: BLE001
        return {"ok": False, "sebep": f"{type(e).__name__}: {str(e)[:100]}"}


def edin(sorgu: str, hedef_yol: str, *, saglayicilar: list,
         en_az_genislik: int = 0, kesici: Optional[DevreKesici] = None,
         onbellek: Optional[dict] = None, uyu: Optional[Callable] = None,
         saat: Optional[Callable] = None, aday_secici: Optional[Callable] = None,
         olcu_okuyucu: Optional[Callable] = None, adet: int = 1,
         hedef_oran: float = 0.0,
         en_az_korunan: float = ORAN_EN_AZ_KORUNAN,
         benzerlik_okuyucu: Optional[Callable] = None,
         benzerlik_esigi: float = 0.0) -> dict:
    """Saglayici zincirini SIRAYLA dene; ilk GERCEK BAYT ile don.

    `saglayicilar`: [{"ad", "modul", "sorgu"?}] — `modul` `ara()`/`indir()`
    tasiyan herhangi bir nesne olabilir (test icin sahte modul verilebilir).

    ⚠ Bu modulde HICBIR saglayici adresi gomulu DEGILDIR.
    """
    saat = saat or time.monotonic
    bekle = uyu or time.sleep
    kesici = kesici if kesici is not None else DevreKesici(saat=saat)
    onbellek = onbellek if onbellek is not None else {}
    basla = saat()
    istenen = max(1, int(adet))
    toplanan: list = []
    rapor = {"ok": False, "sorgu": str(sorgu or ""), "aday": None,
             "adaylar": [], "istenen_adet": istenen,
             "kullanilan_saglayici": "", "saglayici_dagilimi": {},
             "denemeler": [],
             "metadata_bulundu": 0, "bayt_indirildi": 0,
             "onbellekten": False, "failover_sn": None,
             "devre": None,
             # ⚠ I-23: OLCULEN oran, HEDEF oran ve RED NEDENI raporda GORUNUR.
             "oran_kapisi": {"acik": bool(hedef_oran),
                             "hedef_oran": round(float(hedef_oran or 0.0), 4),
                             "en_az_korunan": round(float(en_az_korunan), 4),
                             "reddedilen": [], "kabul_edilen": []},
             # ⚠ I-23b: ORAN KAPISI, AYIRT EDILEBILIRLIGI BOZABILIYOR.
             # Olculdu: dikey aday elenince s01'in siradaki adayi BIRINCININ
             # neredeyse ayni karesi cikti (dHash 0.875 >= 0.86) ve
             # KALITE-MEDYA-TEKRAR FAIL verdi. Iki kisit AYNI anda saglanmali;
             # aksi halde birini greedy secmek digerini kiriyor.
             "ayirt_kapisi": {"acik": bool(benzerlik_okuyucu
                                           and benzerlik_esigi),
                              "esik": round(float(benzerlik_esigi or 0.0), 4),
                              "reddedilen": []}}

    def _kapilar(aday: dict, yol: str) -> dict:
        """INDIRME SONRASI kapilar. Gecerse {}; gecemezse RED `son`u doner.

        ⚠ ARAMA BEYANI ile GERCEK BAYT AYRI: bazi saglayicilar (NASA) arama
        ucunda piksel olcusu VERMIYOR. "1920 istedim" demek yetmez; olcu
        ancak INDIRDIKTEN sonra bilinir. Upscale ya da pillarbox/blur ile
        doldurma YAPILMAZ — uymayan aday REDDEDILIR ve AYNI mevcut arama
        listesindeki SIRADAKI lisansli adaya gecilir (EK AG CAGRISI YOK).

        ⚠ I-23'TE BULUNAN BOSLUK: bu iki kapi eskiden yalnizca ILK indirme
        denemesine uygulaniyordu; `Retry-After` sonrasi yeniden deneme
        BASARILI olursa aday HIC OLCULMEDEN kabul ediliyordu. Artik iki yol
        da buradan gecer.
        """
        if not _olcu_yeter(yol, aday, en_az_genislik, olcu_okuyucu):
            return {"ok": False, "sebep": "COZUNURLUK-YETERSIZ",
                    "olculen": aday.get("olculen_olcu")}
        if not _oran_yeter(yol, aday, hedef_oran, en_az_korunan, olcu_okuyucu):
            k = dict(aday.get("oran_karari") or {})
            k["baslik"] = str(aday.get("baslik") or "")[:80]
            rapor["oran_kapisi"]["reddedilen"].append(k)
            return {"ok": False, "sebep": k.get("sebep") or "ORAN-UYUMSUZ",
                    "oran": k}
        # ── AYIRT EDILEBILIRLIK ──
        # ⚠ Bu modul dHash HESAPLAMAZ; olcer DISARIDAN verilir (tipki
        # `kalite_kapisi.medya_tekrari` gibi). Edinim icerik-agnostik kalir.
        # Olcer yoksa ya da "olcemedim" (<0) derse ENGELLENMEZ.
        if benzerlik_okuyucu and benzerlik_esigi:
            for _onceki in toplanan:
                _oy = str(_onceki.get("yol") or "")
                if not _oy:
                    continue
                try:
                    _b = float(benzerlik_okuyucu(yol, _oy))
                except Exception:                                 # noqa: BLE001
                    continue
                if _b < 0 or _b < float(benzerlik_esigi):
                    continue
                k = {"benzerlik": round(_b, 4),
                     "esik": round(float(benzerlik_esigi), 4),
                     "benzedigi": os.path.basename(_oy),
                     "baslik": str(aday.get("baslik") or "")[:80],
                     "sebep": (f"AYIRT-EDILEMEZ: benzerlik {_b:.3f} >= esik "
                               f"{float(benzerlik_esigi):.3f}")}
                rapor["ayirt_kapisi"]["reddedilen"].append(k)
                return {"ok": False, "sebep": k["sebep"], "ayirt": k}
        kabul = aday.get("oran_karari")
        if kabul:
            rapor["oran_kapisi"]["kabul_edilen"].append(
                {a: kabul.get(a) for a in
                 ("olculen_olcu", "olculen_oran", "hedef_oran",
                  "korunan_oran", "yon")})
        return {}

    for sag in (saglayicilar or []):
        ad = str((sag or {}).get("ad") or "")
        modul = (sag or {}).get("modul")
        # ⚠ I-25 TANI KOR NOKTASI KAPATILDI. Eskiden yalnizca `metadata`
        # (gecen aday) ve `elenen` yaziliyordu. Ikisi de 0 oldugunda
        # "API HIC SONUC DONMEDI" ile "sonuc geldi ama HEPSI ELENDI"
        # AYIRT EDILEMIYORDU — SAGLAYICI-TEKEL kusuru tam bu yuzden dort
        # atom boyunca "lisans duvari" sanildi. `denenen` = saglayicinin
        # ham sonuc sayisi; `kullanilan_sorgu` = O SAGLAYICIYA GERCEKTEN
        # gonderilen sorgu (raporda sahne sorgusu gorunuyordu, saglayici
        # sorgusu DEGIL — bulasan bu yuzden gorunmez kalmisti).
        # ⚠ I-36: bu saglayicinin KATKISI, deneme boyunca toplanan artisiyla
        # olculur. Sondaki 429 basarili gecmisi EZEMEZ.
        _katki_basla = len(toplanan)
        deneme = {"saglayici": ad, "kullanilan_sorgu": "",
                  "denenen": None, "metadata": 0, "elenen": 0,
                  "durum": "", "sebep": "", "sn": None}
        d_basla = saat()
        if modul is None:
            deneme.update({"durum": "MODUL-YOK", "sebep": "modul verilmedi"})
            rapor["denemeler"].append(deneme)
            continue
        if kesici.acik_mi(ad):
            deneme.update({"durum": "DEVRE-ACIK",
                           "sebep": "onceki kalici hatalar sonrasi atlandi",
                           "sn": 0.0})
            rapor["denemeler"].append(deneme)
            continue

        # ── ARAMA / METADATA ──
        _sorgu = str(sag.get("sorgu") or sorgu)
        deneme["kullanilan_sorgu"] = _sorgu
        try:
            bulgu = modul.ara(_sorgu, adet=6, en_az_genislik=en_az_genislik)
        except Exception as e:                                    # noqa: BLE001
            deneme.update({"durum": "ARAMA-HATA",
                           "sebep": f"{type(e).__name__}: {str(e)[:100]}",
                           "sn": round(saat() - d_basla, 3)})
            kesici.hata(ad, kalici=False)
            rapor["denemeler"].append(deneme)
            continue
        adaylar = list((bulgu or {}).get("adaylar") or [])
        deneme["metadata"] = len(adaylar)
        deneme["elenen"] = len((bulgu or {}).get("elenen") or [])
        _denenen = (bulgu or {}).get("denenen")
        deneme["denenen"] = _denenen
        deneme["elenme_nedenleri"] = sorted({
            str((e or {}).get("neden") or "").split(" (")[0]
            for e in ((bulgu or {}).get("elenen") or [])})
        rapor["metadata_bulundu"] += len(adaylar)
        if not adaylar:
            # ⚠ I-25: "ARAMA HIC SONUC VERMEDI" ile "SONUC GELDI, HEPSI
            # ELENDI" AYRI SEBEPTIR. Ikisini tek cumleye sikistirmak
            # SAGLAYICI-TEKEL kusurunu dort atom boyunca gizledi.
            if _denenen == 0:
                # ⚠ I-26'DA OLCULEN SINIF: cok terimli sorgu SESSIZCE bos
                # doner. Bircok arama ucu (Commons/CirrusSearch dahil)
                # terimleri VARSAYILAN OLARAK AND'ler; terim sayisi arttikca
                # eslesme olasiligi duser. Olculen vaka: 5 terimli
                # "Silicon Carbide Integrated Circuit Chip" -> 0 sonuc;
                # ayni konunun 4 terimlisi -> 2 sonuc. Bu ipucu BEDAVA
                # (ek cagri YOK) ve kok nedeni ilk bakista gorunur kilar.
                _terim = len([t for t in str(_sorgu or "").split() if t])
                _sebep = (f"ARAMA-BOS: saglayici {_sorgu!r} icin HIC sonuc "
                          f"dondurmedi (lisans duvari CALISMADI BILE)"
                          + (f" — sorgu {_terim} terim; cok terimli sorgu "
                             f"terimleri AND'leyen uclarda BOS donebilir, "
                             f"daha genel bir es-anlamli DENENMELI"
                             if _terim >= 4 else ""))
                deneme["sorgu_terim_sayisi"] = _terim
            elif _denenen:
                _sebep = (f"HEPSI-ELENDI: {_denenen} ham sonuc geldi, "
                          f"{deneme['elenen']} aday elendi "
                          f"({', '.join(deneme['elenme_nedenleri']) or 'sebep yok'})")
            else:
                _sebep = "lisans/provenance duvarini gecen aday yok"
            deneme.update({"durum": "ADAY-YOK",
                           "sebep": (bulgu or {}).get("hata") or _sebep,
                           "sn": round(saat() - d_basla, 3)})
            kesici.hata(ad, kalici=bool((bulgu or {}).get("hata")))
            rapor["denemeler"].append(deneme)
            continue
        if callable(aday_secici):
            try:
                adaylar = [a for a in adaylar if aday_secici(a)] or adaylar
            except Exception:                                     # noqa: BLE001
                pass

        # ── GERCEK BAYT ──
        son = {}
        # ⚠ N ADAY MEVCUT ARAMA LISTESINDEN secilir — EK AG CAGRISI YOK.
        # `ara()` zaten 6 aday dondurmustu; I-21'e kadar yalnizca ILKI
        # kullaniliyordu ve bolunen iki beat AYNI varligi paylasiyordu.
        _kok, _uzanti = os.path.splitext(hedef_yol)
        for _sira, aday in enumerate(adaylar[:max(3, istenen * 3)]):
            if len(toplanan) >= istenen:
                break
            url = str(aday.get("indirme_url") or "")
            _yol = hedef_yol if _sira == 0 else f"{_kok}_{_sira}{_uzanti}"
            if url in onbellek and os.path.exists(onbellek[url]):
                _k = dict(aday)
                _k["yol"] = onbellek[url]
                # ⚠ I-36: varligin GERCEK kaynagi TOPLAMA aninda isaretlenir.
                _k["kaynak_saglayici"] = ad
                toplanan.append(_k)
                rapor["onbellekten"] = True
                if len(toplanan) >= istenen:
                    rapor.update({"ok": True, "aday": dict(toplanan[0]),
                                  "adaylar": list(toplanan)})
                    rapor.update(saglayici_ozeti(toplanan))
                    deneme.update({"durum": "ONBELLEK",
                                   "sn": round(saat() - d_basla, 3)})
                    rapor["denemeler"].append(deneme)
                    rapor["failover_sn"] = round(saat() - basla, 3)
                    rapor["devre"] = kesici.ozet()
                    return rapor
                continue
            # ⚠ TELIF/ATIF DOGRULAMASI — saglayici ne derse desin BURADA da
            # kontrol edilir; eksikse KESIN RED.
            if not aday.get("render_kullanilabilir") or not aday.get(
                    "eser_sahibi") or not aday.get("lisans"):
                son = {"ok": False, "sebep": "PROVENANCE-EKSIK"}
                continue
            son = _indir_tek(modul, aday, _yol)
            if son.get("ok"):
                _red = _kapilar(aday, _yol)
                if _red:
                    son = _red
                    continue
            if son.get("ok"):
                onbellek[url] = _yol
                kesici.basari(ad)
                _k = dict(aday)
                _k["yol"] = _yol
                _k["kaynak_saglayici"] = ad          # I-36
                toplanan.append(_k)
                rapor["bayt_indirildi"] += 1
                if len(toplanan) >= istenen:
                    rapor.update({"ok": True, "aday": dict(toplanan[0]),
                                  "adaylar": list(toplanan)})
                    rapor.update(saglayici_ozeti(toplanan))
                    deneme.update({"durum": "OK",
                                   "sn": round(saat() - d_basla, 3)})
                    rapor["denemeler"].append(deneme)
                    rapor["failover_sn"] = round(saat() - basla, 3)
                    rapor["devre"] = kesici.ozet()
                    return rapor
                continue
            karar = bekle_karari(son)
            if karar["karar"] == "BEKLE":
                bekle(karar["bekleme_sn"])
                son = _indir_tek(modul, aday, _yol)
                if son.get("ok"):
                    _red = _kapilar(aday, _yol)
                    if _red:
                        son = _red
                        continue
                if son.get("ok"):
                    onbellek[url] = _yol
                    kesici.basari(ad)
                    _k = dict(aday)
                    _k["yol"] = _yol
                    _k["kaynak_saglayici"] = ad      # I-36
                    toplanan.append(_k)
                    rapor["bayt_indirildi"] += 1
                    if len(toplanan) >= istenen:
                        rapor.update({"ok": True, "aday": dict(toplanan[0]),
                                      "adaylar": list(toplanan)})
                        rapor.update(saglayici_ozeti(toplanan))
                        deneme.update({"durum": "OK-BEKLEDIKTEN-SONRA",
                                       "sn": round(saat() - d_basla, 3)})
                        rapor["denemeler"].append(deneme)
                        rapor["failover_sn"] = round(saat() - basla, 3)
                        rapor["devre"] = kesici.ozet()
                        return rapor
                    continue
            elif karar["karar"] == "DEVRE-AC":
                deneme["bekleme_karari"] = karar
                break                    # ayni hostu ZORLAMA, sirakine gec

        kalici = _kalici_mi(son)
        acildi = kesici.hata(ad, kalici=kalici)
        _katki = len(toplanan) - _katki_basla
        _hata = {"sebep": str(son.get("sebep") or "indirilemedi")[:120],
                 "http": son.get("http"), "kalici": kalici,
                 "devre_acildi": acildi}
        # ⚠ I-36'DA OLCULEN KUSUR: bu saglayici BAYT VERDIYSE (katki > 0)
        # sonraki 429 onu "BAYT-YOK" yapamaz. I-33'te tam bu oldu: Commons
        # vitrin varligini INDIRDI, sonra 429 aldi ve rapor Commons'i
        # BAYT-YOK gosterdi. Basarili gecmis KORUNUR; son hata AYRI alanda.
        deneme.update({
            "durum": ("KISMI-OK" if _katki > 0 else "BAYT-YOK"),
            "toplanan_katki": _katki,
            "son_hata": _hata,
            # Geriye uyumluluk: eski tuketiciler `sebep`/`http` okuyor.
            "sebep": ((f"{_katki} varlik ALINDI, sonra: {_hata['sebep']}")
                      if _katki > 0 else _hata["sebep"]),
            "http": _hata["http"], "kalici": kalici, "devre_acildi": acildi,
            "sn": round(saat() - d_basla, 3)})
        rapor["denemeler"].append(deneme)

    # ⚠ KISMI BASARI DURUSTCE: N istendi, daha azi geldiyse ELDE OLANI don
    # ve kac tane geldigini RAPORLA. Sahte aday uretilmez.
    if toplanan:
        rapor.update({"ok": True, "aday": dict(toplanan[0]),
                      "adaylar": list(toplanan)})
        rapor.update(saglayici_ozeti(toplanan))
    rapor["failover_sn"] = round(saat() - basla, 3)
    rapor["devre"] = kesici.ozet()
    return rapor


def kapsam_ozeti() -> dict:
    return {
        "devre_esigi": DEVRE_ESIGI,
        "devre_soguma_sn": DEVRE_SOGUMA_SN,
        "beklenebilir_tavan_sn": BEKLENEBILIR_TAVAN_SN,
        "kalici_kod": list(KALICI_KODLAR),
        "saglayici_gomulu_mu": False,
        "ayri_sayilan": ["metadata_bulundu", "bayt_indirildi"],
        "hedef_oran_16_9": round(HEDEF_ORAN_16_9, 4),
        "oran_en_az_korunan": ORAN_EN_AZ_KORUNAN,
        "indirme_sonrasi_kapilar": ["COZUNURLUK-YETERSIZ", "ORAN-UYUMSUZ",
                                    "AYIRT-EDILEMEZ"],
        "olcerler_disaridan": ["olcu_okuyucu", "benzerlik_okuyucu"],
        "kapsam_disi": ["youtube ve izinsiz kaynaklar",
                        "odemeli saglayicilar",
                        "kare-bakan icerik dogrulamasi",
                        # ⚠ I-23 DURUST SINIR: kapi kaynagi REDDEDER, kareyi
                        # DUZELTMEZ. Blur/pillarbox/sentetik doldurma YOK.
                        "uymayan kaynagi kirparak KURTARMA"],
    }
