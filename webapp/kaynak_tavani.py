#!/usr/bin/env python3
"""FAZ R-1d-g — AYNI KAYNAK TOPLAM <= 8.0 sn GARANTISI (deterministik).

⚠ OLCULEN KUSUR (R-1d-f pilotu, job_1786721869701):
    GERCEK-KAYNAK-TAVANI: 36560908  8.508 sn   (tavan 8.0)
                          ..._s001  8.124 sn
                          38614588  8.052 sn
                          15924008  8.028 sn
Gercek render hattinda **1 SAHNE = 1 VARLIK**. Bir sahne 8.0 sn'yi asarsa o
varlik TEK BASINA tavani asar ve baska care yoktur. Kabul bu yuzden SUREYE
BAGLI ve KARARSIZDI: R-1d-e pilotunda sahneler 7.1-7.6 sn oldugu icin ayni
urun KABUL EDILMISTI, R-1d-f'te 8.0 asilinca REDDEDILDI.

⚠ TAVAN YUKSELTILMEZ. `KAYNAK_BASINA_TAVAN_SN` J-5b kullanici sartidir ve
`medya.saglayici_motoru` ile AYNI TEK SABITTEN okunur.

── POLITIKA (deterministik, rastgelelik YOK) ──
  1. Suresi tavani ASMAYAN sahne BOLUNMEZ (davranis aynen korunur).
  2. Asan sahne, her parcasi <= tavan olacak EN AZ sayida ESIT parcaya
     bolunur (`ceil(sure / tavan)`).
  3. Her parcaya FARKLI bir varlik atanir; bir varligin TOPLAM kullanimi
     tavani asacaksa o varlik ATANMAZ.
  4. Aday sirasi verilen sirayla taranir -> ayni girdi AYNI cikti.
  5. Yeterli FARKLI varlik yoksa parca ATANMAZ ve STABIL KOD yazilir:
     `KAYNAK-TAVANI-VARLIK-YOK`. ⚠ Ayni kaynak tekrar kullanilarak toplam
     ASILMAZ; tavan da yukseltilmez — FAIL-CLOSED.

⚠ Bu modul MEDYA ACMAZ, DOSYA YAZMAZ, AG KULLANMAZ, RENDER ETMEZ. Saf
karar mantigi; bolme uygulamasi cagiran tarafin isidir.
"""
from __future__ import annotations

import math
import re

SEMA_SURUM = "1.0.0"

try:                                                         # pragma: no cover
    from medya.saglayici_motoru import KAYNAK_BASINA_TAVAN_SN
except Exception:                                            # noqa: BLE001
    KAYNAK_BASINA_TAVAN_SN = 8.0

# ── STABIL KODLAR ──
KOD_VARLIK_YOK = "KAYNAK-TAVANI-VARLIK-YOK"
KOD_SURE_BOZUK = "KAYNAK-TAVANI-SURE-BOZUK"
KOD_SORGU_YOK = "KAYNAK-TAVANI-SORGU-TURETILEMEDI"

# Kayan nokta toleransi: 8.000000001 "asti" sayilmasin.
EPS = 1e-9


def _f(v, d=0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def parca_sayisi(sure_sn, *, tavan_sn: float = KAYNAK_BASINA_TAVAN_SN) -> int:
    """Bu sahne kac parcaya bolunmeli? ⚠ Tavani asmayan sahne 1 kalir."""
    s = _f(sure_sn)
    if s <= 0 or tavan_sn <= 0:
        return 1
    return max(1, int(math.ceil(s / tavan_sn - EPS)))


def bolme_plani(sahneler, *, adaylar=None,
                tavan_sn: float = KAYNAK_BASINA_TAVAN_SN) -> dict:
    """Zaman cizgisini tavana UYAN parcalara boler ve varlik atar.

    `sahneler`: [{"scene_id", "sure_sn", "asset_id"(mevcut atama, ops.)}]
    `adaylar` : [{"asset_id", "saglayici", "lisans"}] — ATANABILIR havuz.
        ⚠ Lisansi/saglayicisi olmayan aday havuzdan ELENIR (provenanssiz
        varlik ATANMAZ).

    Doner: {"ok", "parcalar", "kullanim", "tavan_sn", "sorunlar", "bolunen"}
    ⚠ `ok=False` iken de parcalar DONER — cagiran taraf neyin atanamadigini
    GORUR; sessiz bir "hallettik" YOKTUR.
    """
    havuz = [a for a in (adaylar or [])
             if isinstance(a, dict) and str(a.get("asset_id") or "").strip()
             and str(a.get("lisans") or "").strip()
             and str(a.get("saglayici") or "").strip()]
    kullanim: dict = {}
    parcalar, sorunlar = [], []
    bolunen = 0

    for s in (sahneler or []):
        if not isinstance(s, dict):
            continue
        sid = str(s.get("scene_id") or "")
        sure = _f(s.get("sure_sn"))
        if sure <= 0:
            sorunlar.append({"kod": KOD_SURE_BOZUK, "scene_id": sid,
                             "detay": f"sure={s.get('sure_sn')!r}"})
            continue
        n = parca_sayisi(sure, tavan_sn=tavan_sn)
        if n > 1:
            bolunen += 1
        # ⚠ ESIT bolme: her parca sure/n (hepsi <= tavan, tanim geregi).
        p_sure = round(sure / n, 3)
        # Mevcut atama once denenir (gereksiz degisiklik YAPILMAZ).
        oncelik = []
        mevcut = str(s.get("asset_id") or "").strip()
        if mevcut:
            oncelik = [a for a in havuz if a["asset_id"] == mevcut]
        sira = oncelik + [a for a in havuz if a not in oncelik]
        for i in range(n):
            sec = None
            for a in sira:
                aid = a["asset_id"]
                if kullanim.get(aid, 0.0) + p_sure <= tavan_sn + EPS:
                    sec = a
                    break
            if sec is None:
                # ⚠ FAIL-CLOSED: ayni kaynagi tekrar kullanip tavani ASMAK
                # ya da tavani YUKSELTMEK YOK.
                sorunlar.append({"kod": KOD_VARLIK_YOK, "scene_id": sid,
                                 "parca": i + 1,
                                 "detay": (f"{p_sure} sn icin tavani asmayan "
                                           f"FARKLI varlik yok")})
                parcalar.append({"scene_id": sid, "parca": i + 1,
                                 "parca_sayisi": n, "sure_sn": p_sure,
                                 "asset_id": None, "saglayici": None,
                                 "lisans": None, "atandi": False})
                continue
            kullanim[sec["asset_id"]] = round(
                kullanim.get(sec["asset_id"], 0.0) + p_sure, 3)
            parcalar.append({"scene_id": sid, "parca": i + 1,
                             "parca_sayisi": n, "sure_sn": p_sure,
                             "asset_id": sec["asset_id"],
                             "saglayici": sec.get("saglayici"),
                             "lisans": sec.get("lisans"), "atandi": True})
            # ⚠ Ayni varlik ARDIL parcada tekrar kullanilmasin (gorsel
            # tekrar); sira dondurulur.
            sira = [a for a in sira if a["asset_id"] != sec["asset_id"]] + \
                   [a for a in sira if a["asset_id"] == sec["asset_id"]]

    asan = [{"asset_id": a, "sure_sn": v} for a, v in sorted(kullanim.items())
            if v > tavan_sn + EPS]
    return {"ok": not sorunlar and not asan,
            "tavan_sn": tavan_sn, "parcalar": parcalar,
            "kullanim": kullanim, "asan": asan,
            "bolunen_sahne": bolunen, "sorunlar": sorunlar}


def dogrula(kullanim: dict, *,
            tavan_sn: float = KAYNAK_BASINA_TAVAN_SN) -> dict:
    """Nihai kullanim tavana UYUYOR mu? ⚠ Tolerans yalniz kayan nokta icin."""
    k = kullanim if isinstance(kullanim, dict) else {}
    asan = [{"asset_id": a, "sure_sn": round(_f(v), 3)}
            for a, v in sorted(k.items()) if _f(v) > tavan_sn + EPS]
    return {"ok": not asan, "tavan_sn": tavan_sn, "asan": asan,
            "kod": "" if not asan else KOD_VARLIK_YOK}


# ⚠ FAZ R-1d-i — SORGU TURETME.
# OLCULEN KUSUR (R-1d-h pilotu, job_1786727121434): `..._s001` bir AI
# URETILMIS GORSEL sahnesiydi (openai/uretilmis-eser), 8.172 sn ile tavani
# ASIYORDU ama BOLUNEMIYORDU: bolme yolu ek varligi YALNIZCA `footage_sorgu`
# uzerinden ucretsiz stok klip cekerek buluyor ve uretilmis-gorsel
# sahnesinde o sorgu BOS. Aday havuzu bos kalinca fail-closed devreye girip
# sahne bolunmuyor ve kapi ihlali SURUYORDU.
#
# ⚠ Sorgu SAHNENIN KENDI INGILIZCE gorsel tarifinden (`scene_prompt`)
# turetilir — LLM cagrisi YOK, ucret YOK, rastgelelik YOK.
# ⚠ Ayni gorseli kadrajlayip "farkli asset" gibi gostermek YAPILMAZ; amac
# GERCEKTEN farkli kaynakli bir stok klip bulmaktir.

# Sorguya katkisi olmayan yaygin kelimeler (deterministik, sabit liste).
_ETKISIZ = frozenset("""
a an the of in on at to for with and or but from by as is are was were be
been being this that these those it its into over under near very more most
no not none some any each other another while during before after above
below up down out off again further then once here there all both few
scene shot view image picture photo camera frame background foreground
cinematic wide close detail medium angle lighting light dark color colour
16:9 aspect ratio high quality realistic photo-realistic
""".split())

# Sorgu basina en fazla kelime (stok aramalari uzun sorguda bosa duser).
SORGU_KELIME_TAVANI = 3
# En fazla kac aday sorgu turetilir.
SORGU_TAVANI = 4


def _kelimeler(metin: str) -> list:
    ham = re.findall(r"[a-zA-Z][a-zA-Z\-]{2,}", str(metin or ""))
    out, gorulen = [], set()
    for k in ham:
        d = k.lower().strip("-")
        if len(d) < 3 or d in _ETKISIZ or d in gorulen:
            continue
        gorulen.add(d)
        out.append(d)
    return out


def stok_sorgulari(gorsel_tarif: str, *, mevcut_sorgu: str = "") -> dict:
    """Sahnenin INGILIZCE gorsel tarifinden DETERMINISTIK stok sorgulari.

    ⚠ Kelime sirasi TARIFTEKI ILK GECIS sirasidir (frekans/rastgelelik YOK)
    -> ayni girdi AYNI cikti.
    ⚠ Kullanilabilir kelime yoksa `ok=False` + STABIL KOD
    `KAYNAK-TAVANI-SORGU-TURETILEMEDI`; UYDURMA sorgu URETILMEZ.
    """
    if str(mevcut_sorgu or "").strip():
        return {"ok": True, "kod": "", "kaynak": "mevcut_sorgu",
                "sorgular": [str(mevcut_sorgu).strip()]}
    kel = _kelimeler(gorsel_tarif)
    if not kel:
        return {"ok": False, "kod": KOD_SORGU_YOK, "kaynak": "gorsel_tarif",
                "sorgular": [], "neden": "kullanilabilir kelime yok"}
    sorgular, gorulen = [], set()
    # En genisten en dara: 3 kelime -> 2 kelime -> 1 kelime, sonra kaydirma.
    for n in range(min(SORGU_KELIME_TAVANI, len(kel)), 0, -1):
        q = " ".join(kel[:n])
        if q not in gorulen:
            gorulen.add(q)
            sorgular.append(q)
    for i in range(1, len(kel)):
        if len(sorgular) >= SORGU_TAVANI:
            break
        q = " ".join(kel[i:i + 2]) if i + 1 < len(kel) else kel[i]
        if q and q not in gorulen:
            gorulen.add(q)
            sorgular.append(q)
    return {"ok": True, "kod": "", "kaynak": "gorsel_tarif",
            "sorgular": sorgular[:SORGU_TAVANI]}


def kimlik_normalize(provenans) -> str:
    """Provenanstan NORMALIZE kaynak kimligi. ⚠ Eksikse BOS doner.

    Kimlik `saglayici|asset_id`dir. Lisans/saglayici/asset_id'den BIRI bile
    eksikse kimlik URETILMEZ — "herhalde farklidir" DENMEZ.
    """
    p = provenans if isinstance(provenans, dict) else {}
    sag = str(p.get("saglayici") or "").strip()
    aid = str(p.get("asset_id") or "").strip()
    lis = str(p.get("lisans") or "").strip()
    if not (sag and aid and lis):
        return ""
    return f"{sag}|{aid}"


def ek_varlik_edin(*, adet: int, mevcut_kimlikler,
                   aday_uretici, provenans_okuyucu, kopru_yazici,
                   maks_deneme: int = 6, mevcut_zorunlu: bool = True) -> dict:
    """Bolme icin `adet` tane FARKLI kaynakli varlik edin. FAIL-CLOSED.

    ⚠ OLCULEN KUSUR (bagimsiz denetim, cd3a5b5): ek klip edinimi
    `footage_getir` TRUE dondu diye kabul ediliyordu. Iki delik vardi:
      (1) Saglayici AYNI `asset_id`i tekrar dondurebilir; kimlik HIC
          karsilastirilmiyordu -> ayni kaynak iki parcada kullanilip toplam
          tavani ASABILIYORDU.
      (2) `kopru_yazici` False donse (lisans/kare dogrulamasi GECMEDI) bile
          klip listeye ekleniyor ve TIMELINE'A GIRIYORDU.

    Sozlesme (hepsi enjekte edilir; bu modul AG/MEDYA/DOSYA'ya DOKUNMAZ):
      `aday_uretici(sira) -> yol | None`   : sirayla UCRETSIZ aday uretir
      `provenans_okuyucu(yol) -> dict`     : o yolun provenansi
      `kopru_yazici(yol) -> bool`          : lisans+kare kaydi BASARILI mi

    Kabul kosullari (HEPSI):
      · normalize kimlik URETILEBILIYOR (lisans + saglayici + asset_id dolu)
      · kimlik MEVCUT ve daha once KABUL EDILEN kimliklerden FARKLI
      · kopru kaydi BASARILI
    Aksi halde aday REDDEDILIR ve SIRADAKI denenir; secenek tukenirse
    `ok=False` + `KAYNAK-TAVANI-VARLIK-YOK`.
    """
    # ⚠ MEVCUT PARCANIN KIMLIGI ZORUNLU (bagimsiz denetim bulgusu):
    # kimlik yoksa yeni adayin mevcut klipten FARKLI oldugu KANITLANAMAZ.
    # Bos liste ya da bos kimlik iceren liste -> FAIL-CLOSED.
    ham_mevcut = list(mevcut_kimlikler or [])
    if mevcut_zorunlu and (not ham_mevcut
                           or any(not str(k or "").strip()
                                  for k in ham_mevcut)):
        return {"ok": False, "kabul": [], "kod": KOD_VARLIK_YOK,
                "istenen": int(adet), "bulunan": 0,
                "red": [{"neden": "MEVCUT-KIMLIK-YOK"}]}
    gorulen = {str(k) for k in ham_mevcut if str(k or "")}
    kabul, red = [], []
    sira = 0
    while len(kabul) < int(adet) and sira < int(maks_deneme):
        try:
            yol = aday_uretici(sira)
        except Exception as e:                               # noqa: BLE001
            red.append({"sira": sira, "neden": f"URETICI-HATA:{type(e).__name__}"})
            sira += 1
            continue
        sira += 1
        if not yol:
            red.append({"sira": sira - 1, "neden": "ADAY-YOK"})
            continue
        try:
            pv = provenans_okuyucu(yol) or {}
        except Exception:                                    # noqa: BLE001
            pv = {}
        kimlik = kimlik_normalize(pv)
        if not kimlik:
            red.append({"yol": yol, "neden": "PROVENANS-EKSIK"})
            continue
        if kimlik in gorulen:
            # ⚠ Ayni kaynak: tavan bu yolla ASILAMAZ.
            red.append({"yol": yol, "kimlik": kimlik, "neden": "AYNI-KAYNAK"})
            continue
        try:
            yazildi = bool(kopru_yazici(yol))
        except Exception:                                    # noqa: BLE001
            yazildi = False
        if not yazildi:
            # ⚠ Kopru kaydi YOKSA timeline'a GIRMEZ.
            red.append({"yol": yol, "kimlik": kimlik, "neden": "KOPRU-RED"})
            continue
        gorulen.add(kimlik)
        kabul.append({"yol": yol, "kimlik": kimlik,
                      "saglayici": pv.get("saglayici"),
                      "asset_id": pv.get("asset_id"),
                      "lisans": pv.get("lisans")})
    ok = len(kabul) >= int(adet)
    return {"ok": ok, "kabul": kabul, "red": red,
            "kod": "" if ok else KOD_VARLIK_YOK,
            "istenen": int(adet), "bulunan": len(kabul)}


def kapsam_ozeti() -> dict:
    return {
        "sema_surum": SEMA_SURUM,
        "tavan_sn": KAYNAK_BASINA_TAVAN_SN,
        "tavan_yukseltilir": False,
        "ayni_kaynak_tekrar_ile_asilir": False,
        "deterministik": True, "rastgelelik": False,
        "stabil_kodlar": [KOD_VARLIK_YOK, KOD_SURE_BOZUK, KOD_SORGU_YOK],
        "sorgu_llm_kullanir": False, "sorgu_ucret": False,
        "ayni_gorseli_kadrajlayip_farkli_asset_sayar": False,
        "provenanssiz_varlik_atanir": False,
        "aga_cikar": False, "medya_acar": False, "dosya_yazar": False,
        "render_eder": False,
    }
