"""KALITE KAPILARI (Faz I-14) — I-13'un 10 sn ciktisinda OLCULEN kusurlar.

`outputs/sample/editorv2_quality_voice_10sn.mp4` teknik olarak gecerliydi
(h264 1280x720 / aac 48 kHz / 9.643 sn) ama bagimsiz denetimde somut kalite
kusurlari olculdu ve **hicbiri QA'da FAIL/WARN uretmiyordu** — yani kapi yoktu.
Bu modul o kusurlarin her biri icin DETERMINISTIK bir olcum fonksiyonu verir.

Bu modulun sozu:
  · AG YOK, DOSYA OKUMA YOK, ALT SUREC YOK — hepsi saf fonksiyon.
    Piksel/ses gerektiren olcumler DISARIDAN enjekte edilir (`*_okuyucu`).
  · OLCEMEDIYSE "temiz" DEMEZ. Her sonuc `olculdu` bayragi tasir; okuyucu
    yoksa ya da patlarsa `olculemedi` yazilir, sessizce PASS uretilmez.
  · HICBIR GIRDIDE ISTISNA FIRLATMAZ. Bozuk/None/yanlis tipte girdi
    `olculemedi` ile doner.
  · Esikler SABIT SAYI DEGIL, render kodundan OKUNAN degerlerden hesaplanir.
    (I-12 dersi: `source-label` icin uc kez "yeterince asagi" varsayildi,
    hic hesaplanmadi ve ucunde de tasti.)

⚠ Seviye kararlari `qa_on` / `qa_son` tarafinda verilir; bu modul yalnizca
OLCER. Boylece ayni olcum hem on-render hem son-render tarafinda kullanilabilir.
"""
from __future__ import annotations

import math
import re
from typing import Callable, Optional

SEMA_SURUM = "1.0.0"

# ─────────────────────────────────────────────────────────────────────────
# RENDER KODUNDAN OKUNAN SABITLER
# Bunlar tahmin degil; `app/render-studio/src/editorv2/Grafikler.tsx`
# `BolumBasligi` bileseninden BIREBIR alindi. Render tarafi degisirse burasi
# da degismeli — test bu esligi kilitliyor.
# ─────────────────────────────────────────────────────────────────────────

# Grafikler.tsx:51 — BUYUK HARF Montserrat Bold em tahmini
EM_BUYUK_HARF = 0.72
# Grafikler.tsx:74 — `letterSpacing: '0.01em'`.
# ⚠ TSX'in KENDI sigdirma hesabi (satir 51) bu araligi HESABA KATMIYOR.
# Yani bant "sigar" dedigi halde cizim `letterSpacing` kadar tasabiliyor.
# Bu bosluk 10 sn ciktisinda olculdu; kapi bu yuzden araligi da sayar.
HARF_ARALIGI_EM = 0.01
# Grafikler.tsx:63 — `maxWidth: '84%'`
BANT_MAKS_ORAN = 0.84
# Grafikler.tsx:39 — `dolgu = Math.round(puntoTaban * 0.42)`
DOLGU_ORANI = 0.42
# Grafikler.tsx:49 — `width * 0.84 - dolgu * 2.4`
DOLGU_CARPANI = 2.4
# Grafikler.tsx:52 — `Math.max(0.7, ...)` punto kucultme TABANI.
# ⚠ Taban var oldugu icin kucultme HER ZAMAN yetmez: taban vurulduktan sonra
# metin hala sigmiyorsa `overflow: hidden` HARF ORTASINDAN keser.
KUCULTME_TABANI = 0.70
# temel.tsx — bant sol izgara noktasi
IZGARA_X = 100


def _sayi(d, varsayilan: float = 0.0) -> float:
    """Her turlu bozuk girdide sayiya duser; istisna firlatmaz."""
    try:
        v = float(d)
    except (TypeError, ValueError):
        return varsayilan
    if math.isnan(v) or math.isinf(v):
        return varsayilan
    return v


# ═════════════════════════ 1) BASLIK TASMASI / KIRPILMA ═════════════════

def baslik_olcusu(metin: str, *, punto: float, kare_genislik: float,
                  izgara_x: float = IZGARA_X,
                  em_orani: float = EM_BUYUK_HARF,
                  harf_araligi_em: float = HARF_ARALIGI_EM,
                  bant_maks_oran: float = BANT_MAKS_ORAN,
                  kucultme_tabani: float = KUCULTME_TABANI) -> dict:
    """Bolum basligi bandi GERCEK render genisliginde tasiyor mu?

    ⚠ `kare_genislik` PROFILIN nominal genisligi DEGIL, render'in GERCEK
    olcusudur. I-13 ciktisinda profil 1920 diyordu ama render 1280'e
    yapiliyordu (`remotion_v2.render(olcu=(1280,720))` props'u eziyor,
    `Root.tsx` `calculateMetadata` onu okuyor). Plan 1920'ye gore karakter
    siniri hesaplayip 1280'e ciziyordu — kirpilmanin kok nedeni budur.
    """
    ham = " ".join(str(metin or "").split())
    punto = _sayi(punto)
    kare_genislik = _sayi(kare_genislik)
    if not ham or punto <= 0 or kare_genislik <= 0:
        return {"olculdu": False, "neden": "GIRDI-EKSIK", "metin": ham,
                "karakter": len(ham), "sigar": None}

    dolgu = round(punto * DOLGU_ORANI)
    # Grafikler.tsx:49 ile BIREBIR ayni aritmetik.
    kullanilabilir = kare_genislik * bant_maks_oran - dolgu * DOLGU_CARPANI
    # TSX'in kendi tahmini (letterSpacing HARIC) — kucultme oranini o belirler.
    tsx_gerekli = max(1.0, len(ham) * punto * em_orani)
    olcek = max(kucultme_tabani, min(1.0, kullanilabilir / tsx_gerekli))
    uygulanan_punto = round(punto * olcek)
    # GERCEK cizim genisligi: letterSpacing DAHIL.
    cizilen = len(ham) * uygulanan_punto * (em_orani + harf_araligi_em)
    tasma = cizilen - kullanilabilir

    # Bandin sag kenari kareyi asiyor mu? (left = izgara_x - dolgu)
    bant_genislik = min(kullanilabilir + dolgu * DOLGU_CARPANI,
                        kare_genislik * bant_maks_oran)
    bant_sag = (izgara_x - dolgu) + bant_genislik

    return {
        "olculdu": True,
        "metin": ham,
        "karakter": len(ham),
        "punto_taban": punto,
        "kare_genislik": kare_genislik,
        "kullanilabilir_px": round(kullanilabilir, 1),
        "olcek": round(olcek, 4),
        "kucultme_tabani_vuruldu": bool(olcek <= kucultme_tabani + 1e-9),
        "uygulanan_punto": uygulanan_punto,
        "cizilen_px": round(cizilen, 1),
        "tasma_px": round(max(0.0, tasma), 1),
        "sigar": bool(tasma <= 0),
        "bant_sag_px": round(bant_sag, 1),
        "bant_kare_disi": bool(bant_sag > kare_genislik),
    }


def sigan_karakter(punto: float, kare_genislik: float, *,
                   em_orani: float = EM_BUYUK_HARF,
                   harf_araligi_em: float = HARF_ARALIGI_EM,
                   bant_maks_oran: float = BANT_MAKS_ORAN,
                   kucultme_tabani: float = KUCULTME_TABANI,
                   guvenlik_payi: float = 0.90) -> int:
    """Bu punto + kare genisliginde bandina KAC karakter SIGAR (hesaplanan).

    Kucultme tabani hesaba katilir: taban puntoda sigmayan uzunluk zaten
    kirpilir, dolayisiyla sinir TABAN puntoya gore verilir.
    """
    punto = _sayi(punto)
    kare_genislik = _sayi(kare_genislik)
    if punto <= 0 or kare_genislik <= 0:
        return 0
    dolgu = round(punto * DOLGU_ORANI)
    kullanilabilir = kare_genislik * bant_maks_oran - dolgu * DOLGU_CARPANI
    if kullanilabilir <= 0:
        return 0
    en_kucuk_punto = punto * kucultme_tabani
    birim = en_kucuk_punto * (em_orani + harf_araligi_em)
    if birim <= 0:
        return 0
    return max(0, int((kullanilabilir / birim) * guvenlik_payi))


_KELIME_SON = re.compile(r"[\wÀ-ɏ]$", re.UNICODE)
_KELIME_BAS = re.compile(r"^[\wÀ-ɏ]", re.UNICODE)


def kelime_ortasi_kesik(ham_metin: str, gosterilen: str) -> dict:
    """`gosterilen`, `ham_metin`in KELIME ORTASINDAN kesilmis hali mi?

    I-13 ciktisinda olculen vaka:
        ham       : "The Eagle began its final descent on 20 July 1969."
        gosterilen: "THE EAGLE BEGAN ITS FINAL DESCENT ON 20 JU"
                                                            ^^ "JULY" -> "JU"
    Kaynagi `plan.py`'nin SABIT `b.metin[:42]` dilimi (hesaplanan sinir 34).
    """
    ham = " ".join(str(ham_metin or "").split())
    gos = " ".join(str(gosterilen or "").split())
    if not ham or not gos:
        return {"olculdu": False, "neden": "GIRDI-EKSIK", "kesik": None}
    a, b = ham.upper(), gos.upper()
    if not a.startswith(b):
        # On ek degil — kisaltma baska bir kural ile yapilmis (ornegin
        # `_kart_basligi` kelime sinirinda kesiyor). Kesik iddiasi URETILMEZ.
        return {"olculdu": True, "on_ek": False, "kesik": False,
                "ham": ham, "gosterilen": gos}
    artan = a[len(b):]
    # ⚠ `match()` dizenin BASINDAN bagladigi icin "son karakter kelime mi"
    # sorusunu cevaplamiyordu; `[\w]$` deseni `match` ile ancak TEK karakterlik
    # dizede tutuyor ve olcum sessizce hep False donuyordu (I-14'te yakalandi).
    kesik = bool(artan and _KELIME_BAS.match(artan) and _KELIME_SON.search(b))
    yarim = ""
    if kesik:
        yarim = gos.split()[-1] + artan.split()[0] if gos.split() else ""
    return {"olculdu": True, "on_ek": True, "kesik": kesik,
            "ham": ham, "gosterilen": gos,
            "yarim_kelime": (gos.split()[-1] if kesik and gos.split() else ""),
            "tam_kelime": yarim}


# ═════════════════════════ 2) MEDYA TEKRARI ═════════════════════════════

# Ayni goruntunun kabul edildigi benzerlik esigi. dHash (64 bit) uzerinde
# %86 ustu esleme, ayni cekimin kirpilmis/olceklenmis kopyasi demektir;
# farkli ama ayni serideki kareler tipik olarak %60-80 bandinda kalir
# (Faz E Apollo havuzunda olculdu: a281-a283 %75.0, a082-a314 %60.9).
# ⚠ Bu esik OLCUMDEN turetildi ama "dogru esik" iddiasi tasimaz — havuz
# 7 goruntu. Parametre olarak disari acildi.
BENZERLIK_ESIGI = 0.86


def medya_tekrari(sahneler, *, benzerlik_okuyucu: Optional[Callable] = None,
                  benzerlik_esigi: float = BENZERLIK_ESIGI) -> dict:
    """Ayni varlik ya da ayirt edilemeyecek kadar benzer medya tekrari.

    `benzerlik_okuyucu(yolA, yolB) -> 0..1` DISARIDAN verilir; bu modul
    dosya acmaz. Okuyucu yoksa benzerlik bacagi `olculemedi` yazilir —
    "benzer medya yok" DENMEZ.
    """
    try:
        liste = [s for s in (sahneler or []) if isinstance(s, dict)]
    except TypeError:
        return {"olculdu": False, "neden": "GIRDI-BOZUK"}

    kimlikler = [str(s.get("asset_id") or "") for s in liste]
    yollar = [str(s.get("medya_yolu") or s.get("yerel_yol") or "")
              for s in liste]

    # ── (a) AYNI asset_id — her zaman olculebilir, okuyucu gerekmez ──
    sayim: dict = {}
    for k in kimlikler:
        if k:
            sayim[k] = sayim.get(k, 0) + 1
    tekrar_eden = {k: n for k, n in sayim.items() if n > 1}
    bitisik_ayni = []
    for i in range(1, len(kimlikler)):
        if kimlikler[i] and kimlikler[i] == kimlikler[i - 1]:
            bitisik_ayni.append({"indeks": i, "asset_id": kimlikler[i]})

    # ── (b) GORSEL benzerlik — yalniz okuyucu varsa ──
    benzer: list = []
    benzerlik_olculdu = False
    okunamayan = 0
    if callable(benzerlik_okuyucu):
        benzerlik_olculdu = True
        for i in range(len(yollar)):
            for j in range(i + 1, len(yollar)):
                if not yollar[i] or not yollar[j]:
                    okunamayan += 1
                    continue
                if kimlikler[i] and kimlikler[i] == kimlikler[j]:
                    continue        # (a) zaten yakaladi
                try:
                    d = _sayi(benzerlik_okuyucu(yollar[i], yollar[j]), -1.0)
                except Exception:
                    okunamayan += 1
                    continue
                if d < 0:
                    okunamayan += 1
                    continue
                if d >= benzerlik_esigi:
                    benzer.append({"a": i, "b": j, "bitisik": bool(j == i + 1),
                                   "asset_a": kimlikler[i],
                                   "asset_b": kimlikler[j],
                                   "benzerlik": round(d, 4)})

    return {
        "olculdu": True,
        "sahne": len(liste),
        "benzersiz_asset": len([k for k in set(kimlikler) if k]),
        "tekrar_eden_asset": tekrar_eden,
        "bitisik_ayni_asset": bitisik_ayni,
        "benzerlik_olculdu": benzerlik_olculdu,
        "benzerlik_esigi": benzerlik_esigi,
        "benzer_ciftler": benzer,
        "okunamayan_cift": okunamayan,
        # ⚠ Okuyucu yoksa BU ALAN False kalir; "benzer medya yok" iddiasi
        # uretilmez. Cagiran taraf bunu ayirt etmek zorunda.
        "benzerlik_temiz": bool(benzerlik_olculdu and not benzer),
    }


# ═════════════════════════ 3) RITIM / OLU FINAL ═════════════════════════

# Sureler birbirinden bu kadar (sn) az farkliysa "sabit blok" sayilir.
# Bir karede 30 fps'te 0.0333 sn; 0.05 sn ~1.5 kare, yani IZLEYICI ICIN
# ayirt edilemez. Yani bu esik kare suresinden turetildi, sezgiden degil.
SABIT_BLOK_ESIGI_SN = 0.05
# Anlatim agirliklari bu orandan fazla degisiyorsa sureler de degismeliydi.
ANLATIM_SAPMA_ESIGI = 0.15
# Videonun sonundaki sessiz kuyruk tavani (kullanici karari, I-14).
OLU_FINAL_ESIGI_SN = 0.5


def ritim_olcusu(sahneler, *, anlatim_agirliklari=None,
                 toplam_sn: Optional[float] = None,
                 anlatim_bitis_sn: Optional[float] = None,
                 sabit_esik_sn: float = SABIT_BLOK_ESIGI_SN,
                 anlatim_sapma_esigi: float = ANLATIM_SAPMA_ESIGI,
                 olu_final_esigi: float = OLU_FINAL_ESIGI_SN) -> dict:
    """Sahne sureleri SABIT BLOK mu, yoksa anlatim/olguya mi bagli?

    I-13 ciktisinda uc sahnenin ucu de **3.2 sn**; anlatim cumlelerinin
    uzunlugu ise 7-9 kelime arasinda degisiyordu. Yani sure icerikten
    turetilmemis, `(hedef - 0.4) / sahne` ile ESIT bolunmustu.

    ⚠ `qa_on.PACING-TEKDUZE` bu vakayi GORMUYORDU: o kontrol
    `len(sureler) >= 4` sarti tasiyor, uc sahnelik plan elenip geciyordu.
    """
    try:
        liste = [s for s in (sahneler or []) if isinstance(s, dict)]
    except TypeError:
        return {"olculdu": False, "neden": "GIRDI-BOZUK"}
    sureler = [round(_sayi(s.get("sure_sn")), 3) for s in liste]
    sureler = [s for s in sureler if s > 0]
    if not sureler:
        return {"olculdu": False, "neden": "SURE-YOK"}

    yayilim = round(max(sureler) - min(sureler), 3)
    sabit_blok = bool(len(sureler) >= 2 and yayilim <= sabit_esik_sn)

    # ── Anlatim bagi: sureler icerikle birlikte mi degisiyor? ──
    agirlik = None
    if anlatim_agirliklari is None:
        # Agirlik verilmediyse sahne metninden KELIME SAYISI turetilir.
        agirlik = []
        for s in liste:
            m = str(s.get("metin") or s.get("anlatim") or "")
            agirlik.append(float(len(m.split())))
        if not any(a > 0 for a in agirlik):
            agirlik = None
    else:
        try:
            agirlik = [_sayi(a) for a in anlatim_agirliklari]
        except TypeError:
            agirlik = None

    anlatim_bagi = None
    agirlik_yayilim_orani = None
    sure_yayilim_orani = round(yayilim / max(sureler), 4) if max(sureler) else 0.0
    if agirlik and len(agirlik) == len(sureler) and max(agirlik) > 0:
        agirlik_yayilim_orani = round(
            (max(agirlik) - min(agirlik)) / max(agirlik), 4)
        # Icerik belirgin degisiyor ama sure degismiyorsa bag YOK.
        anlatim_bagi = not (agirlik_yayilim_orani > anlatim_sapma_esigi
                            and sure_yayilim_orani <= anlatim_sapma_esigi)

    # ── Olu final ──
    olu_final = None
    top = _sayi(toplam_sn) if toplam_sn is not None else round(sum(sureler), 3)
    if anlatim_bitis_sn is not None and top > 0:
        olu_final = round(max(0.0, top - _sayi(anlatim_bitis_sn)), 3)

    return {
        "olculdu": True,
        "sahne": len(sureler),
        "sureler": sureler,
        "yayilim_sn": yayilim,
        "sure_yayilim_orani": sure_yayilim_orani,
        "sabit_esik_sn": sabit_esik_sn,
        "sabit_blok": sabit_blok,
        "anlatim_agirliklari": agirlik,
        "agirlik_yayilim_orani": agirlik_yayilim_orani,
        "anlatim_sapma_esigi": anlatim_sapma_esigi,
        "anlatim_bagi": anlatim_bagi,
        "toplam_sn": round(top, 3),
        "anlatim_bitis_sn": (round(_sayi(anlatim_bitis_sn), 3)
                             if anlatim_bitis_sn is not None else None),
        "olu_final_sn": olu_final,
        "olu_final_esigi": olu_final_esigi,
        "olu_final_asildi": (bool(olu_final is not None
                                  and olu_final > olu_final_esigi)),
    }


# ═════════════════════════ 4) MIKS: SESSIZLIK + AMBIYANS ════════════════

# Toplam sessizlik payi tavani — §31'in devir belgesindeki karar (%15).
SESSIZ_ORAN_TAVANI = 0.15
# Ambiyans anlatimin bu kadar dB altina duserse pratikte DUYULMAZ.
# ⚠ DURUST ETIKET: bu bir DINLEME TESTI olcumu DEGIL, beyan edilmis tasarim
# esigidir. Yayin pratiginde ambiyans/muzik yatagi konusmanin 15-25 dB
# altinda tutulur; 30 dB alti anlatimin maskeleme tabanina girer. Parametre
# olarak disari acildi ki kalibre edilebilsin.
DUYULABILIR_FARK_DB = 30.0
# ⚠ ALT SINIR (I-15): "duyulabilir" tek basina yetmez — ambiyans anlatima
# fazla yaklasirsa SOZU BOGAR. Ayni yayin pratiginin diger ucu: yatak sesi
# konusmanin 12 dB'den fazla yakinina cikmamali. Bu da beyan edilmis tasarim
# esigidir, dinleme testi degil.
BASTIRMA_FARK_DB = 12.0


def _oran_db(oran: float) -> float:
    """Dogrusal kazanci dB'ye cevirir. 0 ve negatif -> -inf yerine -120 dB."""
    o = _sayi(oran, 0.0)
    if o <= 0:
        return -120.0
    return 20.0 * math.log10(o)


def ambans_duyulabilirligi(*, ambans_lufs: Optional[float],
                           anlatim_lufs: Optional[float],
                           ambans_seviye: float = 1.0,
                           ducking: float = 1.0,
                           duyulabilir_fark_db: float = DUYULABILIR_FARK_DB,
                           bastirma_fark_db: float = BASTIRMA_FARK_DB) -> dict:
    """Ambiyans yatagi anlatimin altinda DUYULABILIR seviyede mi?

    I-13'te olculen zincir:
        kaynak ambans        -48.68 LUFS   (ffmpeg loudnorm, gercek olcum)
        seviye 0.20          -13.98 dB
        ducking 0.30         -10.46 dB
        --------------------------------
        etkin                -73.12 LUFS
        anlatim              -16.00 LUFS
        fark                  57.12 dB     -> DUYULMAZ
    Ducking'i tamamen yok saysak bile fark 46.66 dB; yani kusur ducking
    ayarindan degil, KAYNAGIN kendisinin -48.7 LUFS olmasindan geliyor.
    """
    if ambans_lufs is None or anlatim_lufs is None:
        return {"olculdu": False, "neden": "OLCUM-YOK", "duyulabilir": None}
    a = _sayi(ambans_lufs, -120.0)
    n = _sayi(anlatim_lufs, -120.0)
    seviye_db = _oran_db(ambans_seviye)
    duck_db = _oran_db(ducking)
    etkin = a + seviye_db + duck_db
    etkin_ducksuz = a + seviye_db
    fark = n - etkin
    return {
        "olculdu": True,
        "ambans_lufs": round(a, 2),
        "anlatim_lufs": round(n, 2),
        "ambans_seviye": _sayi(ambans_seviye, 1.0),
        "seviye_db": round(seviye_db, 2),
        "ducking": _sayi(ducking, 1.0),
        "ducking_db": round(duck_db, 2),
        "etkin_lufs": round(etkin, 2),
        "etkin_ducksuz_lufs": round(etkin_ducksuz, 2),
        "fark_db": round(fark, 2),
        "fark_ducksuz_db": round(n - etkin_ducksuz, 2),
        "esik_db": duyulabilir_fark_db,
        "bastirma_esik_db": bastirma_fark_db,
        "duyulabilir": bool(fark <= duyulabilir_fark_db),
        # ⚠ Ust sinir kadar ALT sinir da var: cok yakinsa sozu bogar.
        "bastiriyor": bool(fark < bastirma_fark_db),
        # Ikisi birden: hem duyulur hem anlatimi bogmaz.
        "dengeli": bool(bastirma_fark_db <= fark <= duyulabilir_fark_db),
        # Ducking sifirlansa bile duyulur mu? Kusurun kaynagini ayirt eder.
        "ducking_suz_duyulabilir": bool((n - etkin_ducksuz)
                                        <= duyulabilir_fark_db),
    }


def miks_olcusu(*, sure_sn: Optional[float], sessizlik_araliklari=None,
                sessiz_oran_tavani: float = SESSIZ_ORAN_TAVANI,
                olu_final_esigi: float = OLU_FINAL_ESIGI_SN,
                kuyruk_toleransi_sn: float = 0.05) -> dict:
    """Toplam sessizlik payi + videonun sonundaki OLU KUYRUK.

    `sessizlik_araliklari`: [{"bas","sure"} ...] — `qa_son._sessizlik_ayikla`
    ciktisiyla ayni bicim. Bu modul ffmpeg CAGIRMAZ.

    I-13 olcumu (silencedetect noise=-45dB d=0.30):
        5.390 -> 6.374  (0.984 sn)
        8.739 -> 9.643  (0.903 sn)   <- SON'A KADAR: olu kuyruk
        toplam 1.887 sn / 9.643 sn = %19.6
    """
    top = _sayi(sure_sn, 0.0)
    if top <= 0:
        return {"olculdu": False, "neden": "SURE-YOK"}
    try:
        ham = [s for s in (sessizlik_araliklari or []) if isinstance(s, dict)]
    except TypeError:
        return {"olculdu": False, "neden": "GIRDI-BOZUK"}

    araliklar = []
    for s in ham:
        bas = _sayi(s.get("bas"), -1.0)
        sure = _sayi(s.get("sure"), 0.0)
        if sure <= 0:
            continue
        araliklar.append({"bas": round(bas, 3), "sure": round(sure, 3),
                          "bitis": round(bas + sure, 3) if bas >= 0 else None})
    sessiz_sn = round(sum(a["sure"] for a in araliklar), 3)
    oran = round(sessiz_sn / top, 4)

    # ── Olu kuyruk: son sessizlik videonun SONUNA kadar suruyor mu? ──
    olu_final = 0.0
    for a in araliklar:
        if a["bitis"] is None:
            continue
        if a["bitis"] >= top - kuyruk_toleransi_sn:
            olu_final = max(olu_final, a["sure"])
    return {
        "olculdu": True,
        "sure_sn": round(top, 3),
        "aralik_sayisi": len(araliklar),
        "araliklar": araliklar,
        "sessiz_sn": sessiz_sn,
        "sessiz_orani": oran,
        "sessiz_oran_tavani": sessiz_oran_tavani,
        "sessiz_oran_asildi": bool(oran > sessiz_oran_tavani),
        "olu_final_sn": round(olu_final, 3),
        "olu_final_esigi": olu_final_esigi,
        "olu_final_asildi": bool(olu_final > olu_final_esigi),
    }


# ═════════════════════════ KAPSAM OZETI ═════════════════════════════════

def kapsam_ozeti() -> dict:
    """Bu modulun NE OLCTUGU sayilabilir olsun — "her seyi olcuyoruz" yok."""
    return {
        "sema_surum": SEMA_SURUM,
        "olcum": 5,
        "olcum_adlari": ["baslik_olcusu", "kelime_ortasi_kesik",
                         "medya_tekrari", "ritim_olcusu",
                         "ambans_duyulabilirligi", "miks_olcusu"],
        "render_sabiti": 7,
        "enjekte_edilen_okuyucu": 1,
        "esik": {
            "benzerlik": BENZERLIK_ESIGI,
            "sabit_blok_sn": SABIT_BLOK_ESIGI_SN,
            "anlatim_sapma": ANLATIM_SAPMA_ESIGI,
            "olu_final_sn": OLU_FINAL_ESIGI_SN,
            "sessiz_oran": SESSIZ_ORAN_TAVANI,
            "duyulabilir_fark_db": DUYULABILIR_FARK_DB,
        },
        # Kapsam DISI oldugunu acikca yaz — sonraki atomlarin isi.
        "kapsam_disi": ["altyazi varligi", "kaynak kunyesi (source-label)",
                        "1080p cozunurluk", "gelismis motion"],
    }
