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
         olcu_okuyucu: Optional[Callable] = None) -> dict:
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
    rapor = {"ok": False, "sorgu": str(sorgu or ""), "aday": None,
             "kullanilan_saglayici": "", "denemeler": [],
             "metadata_bulundu": 0, "bayt_indirildi": 0,
             "onbellekten": False, "failover_sn": None,
             "devre": None}

    for sag in (saglayicilar or []):
        ad = str((sag or {}).get("ad") or "")
        modul = (sag or {}).get("modul")
        deneme = {"saglayici": ad, "metadata": 0, "elenen": 0,
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
        try:
            bulgu = modul.ara(str(sag.get("sorgu") or sorgu),
                              adet=6, en_az_genislik=en_az_genislik)
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
        rapor["metadata_bulundu"] += len(adaylar)
        if not adaylar:
            deneme.update({"durum": "ADAY-YOK",
                           "sebep": (bulgu or {}).get("hata") or
                                    "lisans/provenance duvarini gecen aday yok",
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
        for aday in adaylar[:3]:
            url = str(aday.get("indirme_url") or "")
            if url in onbellek and os.path.exists(onbellek[url]):
                rapor.update({"ok": True, "aday": dict(aday),
                              "kullanilan_saglayici": ad, "onbellekten": True})
                rapor["aday"]["yol"] = onbellek[url]
                deneme.update({"durum": "ONBELLEK", "sn": round(saat() - d_basla, 3)})
                rapor["denemeler"].append(deneme)
                rapor["failover_sn"] = round(saat() - basla, 3)
                rapor["devre"] = kesici.ozet()
                return rapor
            # ⚠ TELIF/ATIF DOGRULAMASI — saglayici ne derse desin BURADA da
            # kontrol edilir; eksikse KESIN RED.
            if not aday.get("render_kullanilabilir") or not aday.get(
                    "eser_sahibi") or not aday.get("lisans"):
                son = {"ok": False, "sebep": "PROVENANCE-EKSIK"}
                continue
            son = _indir_tek(modul, aday, hedef_yol)
            if son.get("ok") and not _olcu_yeter(
                    hedef_yol, aday, en_az_genislik, olcu_okuyucu):
                # ⚠ ARAMA BEYANI ile GERCEK BAYT AYRI: bazi saglayicilar
                # (NASA) arama ucunda piksel olcusu VERMIYOR. "1920 istedim"
                # demek yetmez; olcu ancak INDIRDIKTEN sonra bilinir ve
                # yetersizse aday REDDEDILIR. Upscale YAPILMAZ.
                son = {"ok": False, "sebep": "COZUNURLUK-YETERSIZ",
                       "olculen": aday.get("olculen_olcu")}
                continue
            if son.get("ok"):
                onbellek[url] = hedef_yol
                kesici.basari(ad)
                rapor.update({"ok": True, "aday": dict(aday),
                              "kullanilan_saglayici": ad})
                rapor["aday"]["yol"] = hedef_yol
                rapor["bayt_indirildi"] += 1
                deneme.update({"durum": "OK", "sn": round(saat() - d_basla, 3)})
                rapor["denemeler"].append(deneme)
                rapor["failover_sn"] = round(saat() - basla, 3)
                rapor["devre"] = kesici.ozet()
                return rapor
            karar = bekle_karari(son)
            if karar["karar"] == "BEKLE":
                bekle(karar["bekleme_sn"])
                son = _indir_tek(modul, aday, hedef_yol)
                if son.get("ok"):
                    onbellek[url] = hedef_yol
                    kesici.basari(ad)
                    rapor.update({"ok": True, "aday": dict(aday),
                                  "kullanilan_saglayici": ad})
                    rapor["aday"]["yol"] = hedef_yol
                    rapor["bayt_indirildi"] += 1
                    deneme.update({"durum": "OK-BEKLEDIKTEN-SONRA",
                                   "sn": round(saat() - d_basla, 3)})
                    rapor["denemeler"].append(deneme)
                    rapor["failover_sn"] = round(saat() - basla, 3)
                    rapor["devre"] = kesici.ozet()
                    return rapor
            elif karar["karar"] == "DEVRE-AC":
                deneme["bekleme_karari"] = karar
                break                    # ayni hostu ZORLAMA, sirakine gec

        kalici = _kalici_mi(son)
        acildi = kesici.hata(ad, kalici=kalici)
        deneme.update({"durum": "BAYT-YOK",
                       "sebep": str(son.get("sebep") or "indirilemedi")[:120],
                       "http": son.get("http"),
                       "kalici": kalici, "devre_acildi": acildi,
                       "sn": round(saat() - d_basla, 3)})
        rapor["denemeler"].append(deneme)

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
        "kapsam_disi": ["youtube ve izinsiz kaynaklar",
                        "odemeli saglayicilar",
                        "kare-bakan icerik dogrulamasi"],
    }
