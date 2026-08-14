"""ORKESTRATOR — dort cikti dosyasini uretir.

    edit_manifest.json  : beat + cekim + motion + tipografi + ses kararlari
    render_plan.json    : render motorunun tuketecegi duz plan
    editor_qa.json      : pre-render QA (PASS/WARN/FAIL + oneriler)
    attribution.txt     : lisans atif metni (CC gerekliligi)

Her karar scene_id / fact_id / asset_id tasir — kullanicinin izlenebilirlik
sarti. Bu modul AG KULLANMAZ ve INDIRME YAPMAZ; girdiler Faz A/B
manifestlerinden gelir.
"""
from __future__ import annotations

import json
import os
import re
from typing import Optional

from . import (adapter, beat, gramer, kalite_kapisi, motion, profil, qa_on,
               ses, tipografi)
from .profil import EditProfili


def _json_yaz(yol: str, veri) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(yol)) or ".", exist_ok=True)
    gecici = yol + ".tmp"
    with open(gecici, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=1)
    os.replace(gecici, yol)


def _adaylari_indeksle(medya_manifest: dict) -> tuple:
    """asset_id -> aday, ve scene_id -> [adaylar]."""
    index, sahne = {}, {}
    for a in (medya_manifest.get("adaylar") or []):
        aid = a.get("asset_id")
        if aid:
            index[aid] = a
        sid = a.get("scene_id") or "-"
        sahne.setdefault(sid, []).append(a)
    return index, sahne


def _bosluk_indeksle(medya_manifest: dict) -> dict:
    return {b.get("scene_id"): b
            for b in (medya_manifest.get("kapsam_bosluklari") or [])
            if b.get("scene_id")}


def _yazi_katmanlari_kur(cekimler: list, beatler: list, adaylar_index: dict,
                         p: EditProfili,
                         kare_genislik: Optional[float] = None,
                         altyazi_var: bool = False) -> tuple:
    """Beat/cekimden yazi katmanlarini uret ve cakismalari coz.

    ⚠ `altyazi_var` (I-16): altyazi GERCEKTEN cizilirken ekranin alt seridi
    surekli doludur. Kaynak kunyesi varsayilan `0.895` konumunda o bandin
    TAM ICINDE kalirdi; bandin ustune tasinir ve cakisma cozucuye bant
    YASAK BOLGE olarak bildirilir.
    """
    katmanlar = []
    kunye_kararlari: list = []          # I-31: kunye politika kararlari
    baslik_siniri = kart_basligi_siniri(p, kare_genislik)
    kunye_y = tipografi.KAYNAK_ETIKETI_ALTYAZILI if altyazi_var else None
    yasak = tipografi.ALTYAZI_BANT if altyazi_var else None
    for c, b in zip(cekimler, beatler):
        # Bolum basligi: yalnizca perde basinda
        if b.perde == "acilis" and b.beat_id == beatler[0].beat_id:
            # ⚠ I-15 DUZELTMESI: burada SABIT `b.metin[:42]` dilimi vardi ve
            # basligi KELIME ORTASINDAN kesiyordu ("20 JULY" -> "20 JU",
            # I-14'te olculdu). Ayni dosyadaki `_kart_basligi` +
            # `kart_basligi_siniri` zaten dogru isi yapiyordu ama YALNIZCA
            # veri-karti fallback yolunda cagriliyordu; I-12 iki yoldan
            # birini duzeltmisti. Artik iki yol da AYNI hesabi kullaniyor.
            katmanlar.append(tipografi.katman_kur(
                "chapter-title",
                _kart_basligi(b.metin, baslik_siniri).upper(),
                b.bas_sn + 0.2,
                min(5.5, b.sure_sn + 1.5), fact_id=b.fact_id, p=p))
        # Kanit beat'lerinde alt band (yer/kurum)
        if b.islev == "kanit" and c.ulke:
            katmanlar.append(tipografi.katman_kur(
                "lower-third", c.ulke[:34], b.bas_sn + 0.3,
                min(4.7, b.sure_sn), fact_id=b.fact_id, p=p))
        # Kaynak etiketi: gercek medya varliklarinda
        aday = adaylar_index.get(c.asset_id) if c.asset_id else None
        if aday and aday.get("atif_gerekli"):
            # ⚠ I-31: EKRAN kunyesi = "sahip / LISANS" KISA bicimi. Uzun
            # sahip alani yatay guvenli alani asiyordu (I-30'da olculdu).
            # TAM eser adi + kaynak URL + lisans URL `atif_metni`de ve
            # `attribution.txt`te EKSIKSIZ kalir — burasi OZET'tir.
            # Sahip/lisans eksikse metin URETILMEZ (uydurma YOK); hukmu
            # PRE-QA verir (`KALITE-KUNYE-EKSIK`).
            _kb = kalite_kapisi.kunye_kisa_bicim(
                aday.get("eser_sahibi"), aday.get("lisans", ""),
                punto=p.tipografi.kaynak_etiketi,
                kare_genislik=float(kare_genislik or p.genislik),
                guvenli_kenar=p.tipografi.guvenli_kenar)
            kunye_kararlari.append(dict(_kb, scene_id=c.scene_id,
                                        beat_id=b.beat_id,
                                        asset_id=c.asset_id))
            if _kb.get("metin"):
                katmanlar.append(tipografi.katman_kur(
                    "source-label", _kb["metin"],
                    b.bas_sn + 0.4, min(3.0, b.sure_sn), fact_id=b.fact_id,
                    p=p, y_orani=kunye_y))
    _kat, _rap = tipografi.cakisma_coz(katmanlar, p=p, yasak_bant=yasak)
    return _kat, _rap, kunye_kararlari


_SAYI_KALIP = re.compile(r"\b(\d[\d.,]*)\b")
# Yil gibi gorunen sayilar VERI DEGILDIR (1915, 2024...) — cubuk grafigi
# olarak cizmek yaniltici olur.
_YIL_KALIP = re.compile(r"^(1[5-9]\d{2}|20\d{2})$")


def _beat_sayilari(metin: str, sinir: int = 6) -> list:
    """Beat metnindeki GERCEK sayilar. Yil ve sirasal ifadeler elenir.

    ⚠ Bos liste donerse veri sahnesi CIZILMEZ — sayi uydurulmaz.
    """
    cikti = []
    for ham in _SAYI_KALIP.findall(str(metin or "")):
        temiz = ham.replace(",", "").rstrip(".")
        if not temiz or _YIL_KALIP.match(temiz):
            continue
        try:
            d = float(temiz)
        except ValueError:
            continue
        if d <= 0:
            continue
        cikti.append(d)
        if len(cikti) >= sinir:
            break
    return cikti


# ⚠ I-15: em/bant sabitleri ARTIK BURADA TUTULMUYOR. Tek kaynak
# `kalite_kapisi` — o degerler `Grafikler.tsx`ten okundu ve QA kapisi da ayni
# sayilari kullaniyor. Iki ayri aritmetik tutmak I-14'te olculen kusurun ta
# kendisiydi: plan 0.68 ile hesapliyor, render 0.72 + `letterSpacing` ile
# ciziyordu; ikisi ayrisinca baslik kirpiliyordu.
BUYUK_HARF_EM = kalite_kapisi.EM_BUYUK_HARF
BANT_MAKS_ORAN = kalite_kapisi.BANT_MAKS_ORAN


def kart_basligi_siniri(p: EditProfili,
                        kare_genislik: Optional[float] = None) -> int:
    """Bolum kartina KAC KARAKTER sigar? Kirpilma olmasin diye HESAPLANIR.

    ⚠ `kare_genislik` GERCEK render olcusudur. Verilmezse profilin nominal
    genisligine duser — ama I-14'te olculdu ki ikisi ayrilabiliyor
    (profil 1920, render 1280) ve sinir o zaman IKI KATI fazla cikiyor.

    ⚠ `kucultme_tabani=1.0`: sinir TAM PUNTODA sigacak sekilde verilir.
    Render tarafinin %30'a kadar kucultme guvencesi (Grafikler.tsx) boylece
    bir GERI DUSUS agi olarak kalir, normal calisma sarti olmaz — baslik
    tasarlandigi boyutta cizilir.
    """
    return max(12, kalite_kapisi.sigan_karakter(
        max(1, int(p.tipografi.bolum_basligi)),
        float(kare_genislik or p.genislik),
        kucultme_tabani=1.0))


# Baslik sonunda yalniz kalmamasi gereken edat/baglac/artikel.
_SARKAN = frozenset((
    "in", "on", "at", "of", "to", "for", "with", "from", "by", "and",
    "or", "the", "a", "an", "as", "into", "over", "after", "before",
    "ve", "ile", "icin", "gibi", "kadar", "de", "da", "ki", "bir"))


def _kart_basligi(metin: str, sinir: int = 42) -> str:
    """Bolum karti basligi: ilk anlamli ibare, cumle noktalamasi olmadan."""
    ham = " ".join(str(metin or "").split())
    if not ham:
        return "BÖLÜM"
    # Ilk yan cumleye kadar al (virgul/noktali virgul/tire)
    for ayrac in (",", ";", " — ", " - "):
        if ayrac in ham:
            ham = ham.split(ayrac)[0]
            break
    ham = ham.rstrip(".!?")
    if len(ham) > sinir:
        kelimeler, birikim = ham.split(), []
        for k in kelimeler:
            if len(" ".join(birikim + [k])) > sinir:
                break
            birikim.append(k)
        # ⚠ SARKAN EDAT/BAGLAC ATILIR: "…Elephant Island in" gibi yarim kalan
        # baslik profesyonel gorunmuyor (20 sn render, 19. sn'de goruldu).
        while birikim and birikim[-1].lower().strip(",;:") in _SARKAN:
            birikim.pop()
        ham = " ".join(birikim) or ham[:sinir]
    return ham.rstrip(" ,;:-—")


def _altyazi_dagit(kupler, bas_sn: float, sure_sn: float) -> list:
    """Mutlak zamanli altyazi kuplerini SAHNEYE GORELI hale getir.

    ⚠ Remotion `Sequence` icinde `useCurrentFrame()` 0'dan baslar; mutlak
    zaman gecilseydi ilk sahne disindaki her altyazi ekranda hic gorunmezdi.
    Sahne sinirini asan kup KIRPILIR (silinmez) — yazinin sahne degisiminde
    havada kalmasi engellenir.
    """
    if not kupler:
        return []
    bit = bas_sn + sure_sn
    cikti = []
    for k in kupler:
        if not isinstance(k, dict):
            continue
        try:
            kb = float(k.get("bas_sn") or 0.0)
            ks = float(k.get("sure_sn") or 0.0)
        except (TypeError, ValueError):
            continue
        if ks <= 0:
            continue
        ust = max(kb, bas_sn)
        alt = min(kb + ks, bit)
        if alt - ust <= 0.05:          # sahneyle anlamli kesisim yok
            continue
        yeni = dict(k)
        yeni["bas_sn"] = round(ust - bas_sn, 3)      # SAHNEYE GORELI
        yeni["sure_sn"] = round(alt - ust, 3)
        yeni["mutlak_bas_sn"] = round(kb, 3)         # izlenebilirlik
        cikti.append(yeni)
    return cikti


def _motion_kur(cekimler: list, beatler: list, p: EditProfili,
                kare_genislik: Optional[float] = None,
                adaylar_index: Optional[dict] = None,
                kare_olcu: Optional[tuple] = None) -> list:
    """Her beat icin motion spec listesi (beat_id ile etiketli).

    ⚠ FAZ I-27 — PUNCH BUYUTME DUZELTMESI. Kamera kadraji kaynagi ekranda
    BUYUTUYORSA (kapsama x zoom > 1.0) plan, `motion.KADRAJ_MERDIVENI`
    icinden BUYUTMEYEN EN DAR kadraja DETERMINISTIK gecer. Yeni kadraj
    UYDURULMAZ, blur/pillarbox/sentetik doldurma YAPILMAZ, hareket
    (anlati islevi) DEGISMEZ — yalnizca kadraj darligi kaynagin tasiyabildigi
    kadar geri cekilir. Hicbir kadraj yetmiyorsa kadraj OLDUGU GIBI birakilir
    ve hukmu PRE-QA verir (`KALITE-PUNCH-BUYUTME` fail).
    """
    _kg, _ky = 0, 0
    if kare_olcu:
        try:
            _kg, _ky = int(kare_olcu[0]), int(kare_olcu[1])
        except (TypeError, ValueError, IndexError):
            _kg, _ky = 0, 0
    if not _kg or not _ky:
        _kg = int(kare_genislik or getattr(p, "genislik", 0) or 0)
        _ky = int(round(_kg * 9 / 16)) if _kg else 0
    specler = []
    _onceki_kadraj = ""
    for i, (c, b) in enumerate(zip(cekimler, beatler)):
        _aday = (adaylar_index or {}).get(getattr(c, "asset_id", "")) or {}
        _g, _y = _aday.get("genislik"), _aday.get("yukseklik")
        _pb = {"olculdu": False, "neden": "OLCU-YOK", "buyutuyor": False}
        if _g and _y and _kg and _ky and getattr(c, "kaynak_turu", "") == "medya":
            # Hareketin KENDI zoom ucu: kadraj carpani UYGULANMADAN.
            _taban = motion.kamera_spec(c.hareket, b.sure_sn, "tam", p=p)
            try:
                _tz = max(float(v) for v in _taban.parametre["zoom"])
            except (KeyError, TypeError, ValueError):
                _tz = 0.0
            if _tz > 0:
                _sec = kalite_kapisi.kadraj_buyutmeyen(
                    _g, _y, _kg, _ky, _tz, motion.KADRAJ_MERDIVENI,
                    motion.KADRAJ_OLCEK, tercih=c.kadraj,
                    kacinilacak=_onceki_kadraj)
                if _sec.get("secilen") and _sec.get("degisti"):
                    _eski = c.kadraj
                    c.kadraj = _sec["secilen"]
                    c.uyarilar.append(
                        f"PUNCH-BUYUTME: kadraj {_eski} -> {c.kadraj} "
                        f"(kaynak {_g}x{_y} buyutuluyordu)")
                _pb = dict(_sec.get("olcum") or _pb)
                _pb["denenen_kadraj"] = _sec.get("denenen")
                _pb["kadraj_degisti"] = bool(_sec.get("degisti"))
                _pb["cozulemedi"] = _sec.get("secilen") is None
        _onceki_kadraj = c.kadraj
        yerel = [motion.kamera_spec(c.hareket, b.sure_sn, c.kadraj, p=p)]
        # ⚠ Olcum spec'e ISLENIR: render_plan.json'da GORUNUR ve PRE-QA
        # onu YENIDEN TURETMEDEN okur (tek kaynak).
        try:
            yerel[0].parametre["punch_buyutme"] = _pb
        except (AttributeError, TypeError):
            pass
        yerel += motion.taban_katmanlar(b.sure_sn, p=p)

        if c.cekim_turu == "archive" and c.kaynak_turu == "medya":
            yerel.append(motion.parallax_spec(3, b.sure_sn, p=p))
        if c.cekim_turu == "document":
            yerel.append(motion.belge_vurgusu_spec((0.28, 0.32, 0.4, 0.22),
                                                   b.sure_sn))
        if c.cekim_turu == "map":
            yerel.append(motion.harita_spec(c.ulke or "", None, b.sure_sn))
        if c.cekim_turu == "data":
            # ⚠ SAYI UYDURMA YASAK. Onceki surum burada SABIT `[1]` geciyordu;
            # sonuc ekranda kocaman anlamsiz bir "1" ve tek sari cubuktu
            # (20 sn render smoke'unun 19. saniyesinde goruldu). Veri sahnesi
            # ancak GERCEK sayi varsa cizilir.
            _degerler = _beat_sayilari(b.metin)
            if _degerler:
                yerel.append(motion.veri_grafigi_spec(b.metin[:28], _degerler,
                                                      b.sure_sn))
            else:
                # Sayi yoksa PROFESYONEL BOLUM KARTI: baslik guvenli izgarada,
                # uydurma gosterge YOK. Bosluk rastgele stokla da kapanmaz.
                yerel.append(motion.bolum_basligi_spec(
                    _kart_basligi(b.metin,
                                  kart_basligi_siniri(p, kare_genislik)),
                    b.sure_sn, p=p))
        if b.islev == "hook" and i == 0:
            yerel.append(motion.light_sweep_spec(min(0.9, b.sure_sn * 0.4)))
        if b.perde == "kapanis" and b.islev == "sonuc":
            yerel.append(motion.film_burn_spec(0.5))

        onceki_islev = beatler[i - 1].islev if i else ""
        yerel.append(motion.sec_gecis(onceki_islev, b.islev, i,
                                      j_cut=b.j_cut, l_cut=b.l_cut))
        for sp in yerel:
            d = sp.sozluk()
            d["beat_id"] = b.beat_id
            d["scene_id"] = b.scene_id
            d["fact_id"] = b.fact_id
            specler.append(d)
    return specler


def _katman_specleri(katmanlar: list, beatler: list, p: EditProfili) -> list:
    """Cozulmus yazi katmanlarini motion spec'e cevir ve beat'e bagla.

    Katmanin basladigi ana denk gelen beat'e atanir; boylece adapter sahne
    bazinda dogru alana yazabilir (bolum / altBand / kaynakYazi / etiketler)."""
    out = []
    for k in katmanlar:
        hedef = None
        for b in beatler:
            if b.bas_sn <= k.bas_sn < b.bitis_sn + 0.001:
                hedef = b
                break
        hedef = hedef or (beatler[0] if beatler else None)
        if hedef is None:
            continue
        if k.ad == "chapter-title":
            sp = motion.bolum_basligi_spec(k.metin, k.sure_sn, p=p)
        elif k.ad == "lower-third":
            sp = motion.alt_band_spec(k.metin, "", k.sure_sn, p=p)
        elif k.ad == "source-label":
            sp = motion.kaynak_etiketi_spec(k.metin, k.fact_id, k.sure_sn, p=p)
        elif k.ad == "quote-card":
            sp = motion.alinti_karti_spec(k.metin, k.fact_id, k.sure_sn)
        else:
            sp = motion.callout_spec(k.metin, 0.5, k.y_orani, k.sure_sn, p=p)
        d = sp.sozluk()
        # ⚠ I-38'DE OLCULEN KUSUR: burada `d["bas_sn"] = k.bas_sn` yaziyordu,
        # yani katmanin MUTLAK zaman cizgisi baslangici. Ama spec bir SAHNEYE
        # bagli gidiyor ve tuketici (editorv2/Grafikler.tsx `KaynakEtiketi`,
        # `BolumBasligi`) `spec.bas_sn`i SAHNEYE GORELI okuyup zarfi
        # SAHNE-YEREL kare ile hesapliyor. Sonuc: b004 kunyesi 5.35 sn'lik
        # sahnede 10.037 sn'de baslamak zorunda kaliyor ve HIC cizilmiyor.
        # CC-BY/CC-BY-SA dort sahnenin ekran atfi boyle DUSTU.
        # `chapter-title` yalniz TESADUFEN calisiyordu (b001 sifirdan baslar).
        d["bas_sn"] = round(max(0.0, k.bas_sn - hedef.bas_sn), 3)
        d["beat_id"] = hedef.beat_id
        d["scene_id"] = hedef.scene_id
        d["fact_id"] = k.fact_id or hedef.fact_id
        d["parametre"]["y_orani"] = k.y_orani      # cakisma cozumu korunur
        out.append(d)
    return out


def uret(*, cumleler: list, medya_manifest: dict,
         arastirma_manifest: Optional[dict] = None,
         profil_adi: str = "premium-modern",
         beklenen_ulke: str = "", beklenen_donem: str = "",
         cikti_dizin: str = ".", ambience: str = "", muzik: str = "",
         saglayici_tavani: int = 4,
         kare_olcu: Optional[tuple] = None,
         anlatim_bitis_sn: Optional[float] = None,
         benzerlik_okuyucu=None,
         enerji_okuyucu=None,
         kare_okuyucu=None,
         altyazi_kupleri: Optional[list] = None,
         kalite_kapisi: bool = False) -> dict:
    """Tum Faz C zincirini kosur ve dort dosyayi yazar.

    Son dort parametre Faz I-14 kalite kapilarina aittir; hepsi opsiyonel ve
    `kalite_kapisi=False` iken QA hukmu DEGISMEZ (yalniz olcum yazilir).
    """
    p = profil.profil(profil_adi)
    index, sahne_adaylari = _adaylari_indeksle(medya_manifest)
    bosluklar = _bosluk_indeksle(medya_manifest)
    fact_idler = {i.get("fact_id") for i in
                  ((arastirma_manifest or {}).get("iddialar") or [])
                  if i.get("fact_id")}

    # 1) BEAT
    bplan = beat.plan_yap(cumleler, profil_=p)
    # 2) GRAMER
    cekimler = gramer.gramer_uygula(
        bplan.beatler, sahne_adaylari=sahne_adaylari,
        kapsam_bosluklari=bosluklar, saglayici_tavani=saglayici_tavani)
    # 3) MOTION
    _kare_gen = (kare_olcu or (None,))[0]
    specler = _motion_kur(cekimler, bplan.beatler, p, _kare_gen,
                          adaylar_index=index, kare_olcu=kare_olcu)
    # 4) TIPOGRAFI
    _altyazi_var = bool(altyazi_kupleri)
    katmanlar, tipo_rapor, kunye_kararlari = _yazi_katmanlari_kur(
        cekimler, bplan.beatler, index, p, _kare_gen, _altyazi_var)
    # ⚠ Cozulmus yazi katmanlari MOTION SPEC'e cevrilir. Ilk surumde katmanlar
    # yalnizca edit_manifest'te duruyordu; render_plan'a girmedigi icin adapter
    # bolum basligini ve kaynak yazisini GOREMIYORDU (test yakaladi) — yani
    # tipografi sessizce kayboluyordu.
    specler += _katman_specleri(katmanlar, bplan.beatler, p)
    # 5) SES
    splan = ses.plan_yap(bplan.beatler, profil_=p, ambience=ambience, muzik=muzik)
    # 6) PRE-RENDER QA
    q = qa_on.denetle(beat_plani=bplan, cekimler=cekimler,
                      yazi_katmanlari=katmanlar, motion_specler=specler,
                      ses_plani=splan, adaylar_index=index, profil_=p,
                      beklenen_ulke=beklenen_ulke,
                      beklenen_donem=beklenen_donem,
                      arastirma_fact_idler=fact_idler or None,
                      kare_olcu=kare_olcu,
                      anlatim_bitis_sn=anlatim_bitis_sn,
                      benzerlik_okuyucu=benzerlik_okuyucu,
                      enerji_okuyucu=enerji_okuyucu,
                      kare_okuyucu=kare_okuyucu,
                      altyazi_kupleri=altyazi_kupleri,
                      kunye_kararlari=kunye_kararlari,
                      kalite_kapisi=kalite_kapisi)

    # ── edit_manifest ──
    edit_manifest = {
        "sema": "1.0", "profil": p.token_sozlugu(),
        "profil_uyarilari": p.dogrula(),
        "beat_plani": bplan.sozluk(),
        "perde_ozeti": beat.perde_ozeti(bplan),
        "islev_ozeti": beat.islev_ozeti(bplan),
        "cekimler": [c.__dict__ for c in cekimler],
        "yazi_katmanlari": [k.__dict__ for k in katmanlar],
        "tipografi_raporu": tipo_rapor,
        # ⚠ I-31: EKRAN kunyesi kararlari IZLENEBILIR. Kisaltildiysa TAM
        # sahip adi da burada durur; provenance `attribution.txt`te.
        "kunye_kararlari": kunye_kararlari,
        "ses_plani": splan.sozluk(),
        "motion_spec_sayisi": len(specler),
    }

    # ── render_plan ──
    sahneler = []
    for c, b in zip(cekimler, bplan.beatler):
        aday = index.get(c.asset_id) if c.asset_id else None
        sahneler.append({
            "beat_id": b.beat_id, "scene_id": b.scene_id, "fact_id": b.fact_id,
            "asset_id": c.asset_id, "saglayici": c.saglayici,
            "kaynak_turu": c.kaynak_turu, "fallback_turu": c.fallback_turu,
            "medya_turu": (aday.get("tur") if aday else "image"),
            "medya_yolu": (aday.get("yerel_yol") or "") if aday else "",
            "indirme_url": (aday.get("indirme_url") or "") if aday else "",
            "orijinal_url": (aday.get("orijinal_url") or "") if aday else "",
            "lisans": (aday.get("lisans") or "") if aday else "",
            "ses_yolu": "", "sure_sn": b.sure_sn, "bas_sn": b.bas_sn,
            "altyazi_punto": p.tipografi.altyazi,
            "altyazi_y": tipografi.ALTYAZI_BANT[0],
            "islev": b.islev, "perde": b.perde,
            "cekim_turu": c.cekim_turu, "hareket": c.hareket, "kadraj": c.kadraj,
            "kaynak_aralik": list(c.kaynak_aralik),
            "j_cut": b.j_cut, "l_cut": b.l_cut,
            "altyazi": _altyazi_dagit(altyazi_kupleri, b.bas_sn, b.sure_sn),
            "motion": [s for s in specler if s.get("beat_id") == b.beat_id],
            "gerekce": c.gerekce,
        })
    render_plan = {
        "sema": "1.0", "fps": p.fps, "genislik": p.genislik,
        "yukseklik": p.yukseklik, "gecis_modu": "sinematik",
        "altyazi_stili": "bant-orta" if _altyazi_var else "yok",
        "toplam_sn": round(bplan.toplam_sn, 2),
        "sahne_sayisi": len(sahneler),
        "ses": splan.sozluk(),
        "sahneler": sahneler,
    }

    # ── attribution.txt ──
    atiflar, gorulen = [], set()
    for c in cekimler:
        aday = index.get(c.asset_id) if c.asset_id else None
        if not aday or not aday.get("atif_gerekli"):
            continue
        metin = aday.get("atif_metni") or ""
        if metin and metin not in gorulen:
            gorulen.add(metin)
            atiflar.append(f"[{c.fact_id or '-'}] {metin}")
    atif_metni = ("MEDYA ATIFLARI (video aciklamasina eklenmelidir)\n"
                  + ("\n".join(atiflar) if atiflar
                     else "(atif gerektiren medya kullanilmadi)") + "\n")

    # ── ADAPTER (bilgi amacli; render koduna baglanmiyor) ──
    don = adapter.donustur(render_plan, fps=p.fps, genislik=p.genislik,
                           yukseklik=p.yukseklik)
    edit_manifest["adapter"] = don.sozluk()
    # Premium (Remotion) gereksinimi render_plan'a da yazilir: Faz D
    # yonlendirmeyi buradan okuyacak, adapter'i yeniden kosmak zorunda kalmayacak.
    _premium = set(don.remotion_gerekli_sahneler)
    for sh in render_plan["sahneler"]:
        sh["remotion_gerekli"] = sh["beat_id"] in _premium
    render_plan["remotion_gerekli_sahne"] = sorted(_premium)
    render_plan["remotion_props_ozeti"] = {
        "sahne": len(don.remotion_sahneler),
        "spec": don.sozluk()["remotion_spec_sayisi"]}

    qa = q.sozluk()
    qa["adapter_kayip_efekt"] = don.kayip_efektler
    qa["adapter_remotion_gerekli"] = don.remotion_gerekli_sahneler

    _json_yaz(os.path.join(cikti_dizin, "edit_manifest.json"), edit_manifest)
    _json_yaz(os.path.join(cikti_dizin, "render_plan.json"), render_plan)
    _json_yaz(os.path.join(cikti_dizin, "editor_qa.json"), qa)
    with open(os.path.join(cikti_dizin, "attribution.txt"), "w",
              encoding="utf-8") as f:
        f.write(atif_metni)

    return {"edit_manifest": edit_manifest, "render_plan": render_plan,
            "editor_qa": qa, "attribution": atif_metni,
            "adapter": don, "beat_plani": bplan, "cekimler": cekimler,
            "ses_plani": splan, "yazi_katmanlari": katmanlar}
