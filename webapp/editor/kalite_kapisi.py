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


# ═══════════════ 5) YAZI: GUVENLI ALAN + CAKISMA (Faz I-16) ═════════════
#
# Altyazi GERCEKTEN cizilmeye baslayinca ekranin alt seridi surekli dolu
# oluyor. Baslik, kaynak kunyesi ve altyazi ayni anda ekranda olabilir;
# ucunun de yayin guvenli alaninda kalmasi VE birbirini ortmemesi gerekiyor.
# Bu iki olcum saf geometridir — render'a bakmaz, plandan olculur.

def guvenli_alan_olcusu(katmanlar, *, kare_yukseklik: float,
                        guvenli_kenar: float) -> dict:
    """Her yazi katmani yayin guvenli alaninin ICINDE mi?

    `katmanlar`: [{"ad","y_ust","yukseklik","bas_sn","sure_sn"} ...]
    Oran (0..1) girdiler piksele HESAPLANARAK cevrilir — "yeterince asagi"
    varsayimi yok (I-12'de ucuncu kez o varsayimla tasilmisti).
    """
    try:
        liste = [k for k in (katmanlar or []) if isinstance(k, dict)]
    except TypeError:
        return {"olculdu": False, "neden": "GIRDI-BOZUK"}
    h = _sayi(kare_yukseklik)
    kenar = _sayi(guvenli_kenar)
    if h <= 0:
        return {"olculdu": False, "neden": "OLCU-YOK"}
    alt_sinir = h - kenar
    ihlaller, olcumler = [], []
    for k in liste:
        ust_px = _sayi(k.get("y_ust")) * h
        alt_px = (_sayi(k.get("y_ust")) + _sayi(k.get("yukseklik"))) * h
        kayit = {"ad": str(k.get("ad") or ""), "ust_px": round(ust_px, 1),
                 "alt_px": round(alt_px, 1), "tavan_px": round(alt_sinir, 1),
                 "taban_px": round(kenar, 1)}
        if alt_px > alt_sinir + 1e-6:
            kayit["ihlal"] = "ALT"
            kayit["tasma_px"] = round(alt_px - alt_sinir, 1)
            ihlaller.append(kayit)
        elif ust_px < kenar - 1e-6:
            kayit["ihlal"] = "UST"
            kayit["tasma_px"] = round(kenar - ust_px, 1)
            ihlaller.append(kayit)
        olcumler.append(kayit)
    return {"olculdu": True, "kare_yukseklik": h, "guvenli_kenar": kenar,
            "alt_sinir_px": round(alt_sinir, 1), "katman": len(liste),
            "olcumler": olcumler, "ihlaller": ihlaller,
            "temiz": not ihlaller}


# ═══════════ 5a2) ALTYAZI NEFES BOSLUGU (Faz I-39) ══════════════════════
#
# ⚠ NEDEN VAR — I-38'IN 1080p PILOTUNDA OLCULEN KUSUR:
# I-38 ekran kunyesini GORUNUR yapti, ama kunye altyazi bandinin DIBINDE
# duruyordu. Iki katman da bandin ICINE GIRMEDIGI icin `guvenli_alan_olcusu`,
# `yazi_cakismasi` ve `bant_cakisiyor` UCU DE TEMIZ donuyordu:
#     source-label  y=0.755 -> alt 842.7 px, bant ustu 874.8 px -> 32.1 px
#     chapter-title y=0.70  -> alt 859.0 px                     -> 15.8 px
# "Degmiyorsa sorun yok" YANLIS bir kabuldu: iki yazi kutusu birkac on piksel
# arayla ust uste yigildiginda goz ikisini TEK BLOK okuyor ve altyazi da
# kunye de okunmuyor. Bu yuzden AYRI bir olcum gerekiyor: BOSLUGUN KENDISI.
#
# ESIK — uydurma degil, TIPOGRAFIK: iki metin blogu arasinda en az BIR SATIR
# yuksekligi bosluk kalmali. Altyazi satir yuksekligi = altyazi puntosu * 1.25
# (38 punto -> 47.5 px). Carpan altyazi bileseninin kendi olcusune bagli, sabit
# piksel DEGIL: punto degisirse esik de degisir.
NEFES_CARPANI = 1.25
# Grafikler.tsx:191 — `KaynakEtiketi` KENDI alt sinirini `punto * 1.3` ile
# hesapliyor (`height - GUVENLI_KENAR - punto * 1.3`). Cizilen satir kutusunun
# yuksekligi orada puntonun 1.3 kati sayiliyor; ayni oran bantli katmanlarin
# satir kutusu icin de kullanilir. Render tarafi degisirse BURASI da degismeli.
SATIR_KUTU_ORANI = 1.3
# Bandin ICINDE olan katmanlar bu olcumun konusu DEGILDIR (onlari
# `yazi_cakismasi` + `guvenli_alan_olcusu` zaten FAIL ediyor); yine de negatif
# nefes olarak kayda gecer, gizlenmez.


def yazi_alt_kenari_px(*, ad: str, y_orani, punto, bant: bool,
                       kare_yukseklik: float,
                       satir_orani: float = SATIR_KUTU_ORANI,
                       dolgu_orani: float = DOLGU_ORANI) -> float:
    """Katmanin EKRANDA CIZILEN alt kenari (px). Saf aritmetik.

    ⚠ `tipografi.YUKSEKLIK` oranlari YERLESIM icin kaba bir rezervdir;
    burada render'in KENDI geometrisi kullanilir:
      · bantsiz katman (`source-label`): ust + punto * 1.3
      · bantli katman (`chapter-title`, `lower-third`...): Grafikler.tsx
        `top: yOrani*height - dolgu` + `padding: dolgu` ile ciziyor, yani
        metin ust kenari `yOrani*height`te, bandin alti bir DOLGU asagida.
    """
    h = _sayi(kare_yukseklik)
    p = _sayi(punto)
    ust = _sayi(y_orani) * h
    alt = ust + p * _sayi(satir_orani, SATIR_KUTU_ORANI)
    if bant:
        alt += round(p * _sayi(dolgu_orani, DOLGU_ORANI))
    return alt


def altyazi_nefes_olcusu(katmanlar, *, kare_yukseklik: float,
                         bant_ust_orani, altyazi_punto,
                         carpan: float = NEFES_CARPANI) -> dict:
    """Yazi katmanlari ile altyazi bandi arasinda YETERLI BOSLUK var mi?

    `katmanlar`: [{"ad","y_orani","punto","bant"} ...]
    Doner: esik, bant ust kenari, her katmanin nefesi ve ihlal listesi.

    ⚠ OLCEMEDIYSE "temiz" DEMEZ: altyazi yoksa/olculer bozuksa `olculdu`
    False doner ve hukum verilmez (sessiz PASS yok).
    """
    try:
        liste = [k for k in (katmanlar or []) if isinstance(k, dict)]
    except TypeError:
        return {"olculdu": False, "neden": "GIRDI-BOZUK"}
    h = _sayi(kare_yukseklik)
    ust_orani = _sayi(bant_ust_orani)
    alt_punto = _sayi(altyazi_punto)
    if h <= 0 or not 0 < ust_orani <= 1 or alt_punto <= 0:
        return {"olculdu": False, "neden": "OLCU-YOK",
                "kare_yukseklik": h, "altyazi_punto": alt_punto}
    esik = alt_punto * _sayi(carpan, NEFES_CARPANI)
    bant_ust_px = ust_orani * h
    kayitlar, ihlaller = [], []
    for k in liste:
        ad = str(k.get("ad") or "")
        if ad == "subtitle":          # altyazinin kendisi olculmez
            continue
        alt_px = yazi_alt_kenari_px(
            ad=ad, y_orani=k.get("y_orani"), punto=k.get("punto"),
            bant=bool(k.get("bant")), kare_yukseklik=h)
        nefes = bant_ust_px - alt_px
        kayit = {"ad": ad, "y_orani": _sayi(k.get("y_orani")),
                 "punto": _sayi(k.get("punto")), "bant": bool(k.get("bant")),
                 "alt_px": round(alt_px, 1), "nefes_px": round(nefes, 1),
                 "yeterli": nefes >= esik - 1e-6}
        kayitlar.append(kayit)
        if not kayit["yeterli"]:
            ihlaller.append(kayit)
    return {"olculdu": True, "esik_px": round(esik, 3),
            "carpan": _sayi(carpan, NEFES_CARPANI),
            "altyazi_punto": alt_punto, "kare_yukseklik": h,
            "bant_ust_px": round(bant_ust_px, 3), "katman": len(kayitlar),
            "kayitlar": kayitlar, "ihlaller": ihlaller,
            "temiz": not ihlaller}


# ═══════════ 5b) YATAY GUVENLI ALAN (Faz I-30) ══════════════════════════
#
# ⚠ NEDEN VAR — I-30'DA OLCULEN BOSLUK:
# `guvenli_alan_olcusu` YALNIZCA DIKEY olcuyordu (`y_ust`, `yukseklik`).
# Sag/sol tasma HIC olculmuyordu. Risk somut: `Grafikler.tsx > KaynakEtiketi`
# `position:absolute; right: GUVENLI_KENAR` ile SAGA yaslaniyor ve
# `maxWidth` TASIMIYOR — yani uzun bir atif metni SOLA DOGRU SINIRSIZ buyur.
# Baslik bandinda (`maxWidth:'84%'`) ve altyazida (`maxWidth:900`) boyle bir
# sinir VAR; kunyede YOK. Pilotun KENDI aday havuzunda 155 karakterlik bir
# atif olculdu ("NASA, ESA, AURA/Caltech, Palomar Observatory The science
# team consists of: ..."), yani bu teorik degil.
#
# GENISLIK MODELI — uydurma degil, RENDER'IN KENDI SABITI:
# `Grafikler.tsx:67` genislik tahmini `uzunluk * punto * (0.72 + 0.01)`
# kullaniyor. Kunyenin harf araligi 0.01 degil **0.04** (Grafikler.tsx:205),
# bu yuzden kunye icin `EM_BUYUK_HARF + 0.04` alinir.
# ⚠ DURUST SINIR: bu model BUYUK HARF icin turetilmis; kunye KARISIK HARF.
# Render karesinden dogrudan olcmeyi denedim ve GUVENILIR CIKMADI (dusuk
# opakliktaki yazi degisken foto zemininde esikle ayrilamiyor; ornekler
# 0.003-0.769 arasinda savruldu). Yalniz KENDI KENDINI DOGRULAYAN tek ornek
# (t=5.99, sag kenar 1854 ~ beklenen 1856) **0.769** verdi ve bu, render'in
# belgeli 0.76 sabitiyle %1 icinde ORTUSUYOR. Model bu tek dogrulamaya
# dayanir; daha iyi bir olcum cikarsa BURASI guncellenmeli.
KUNYE_HARF_ARALIGI_EM = 0.04


# ═══════════ 5d) KARE ORNEKLEME PLANI (Faz I-32) ═══════════════════════
#
# ⚠ NEDEN VAR — I-31'DE OLCULEN KOR NOKTA:
# Zorunlu gorsel/semantik inceleme karelerini secen kod SAHNE (cumle)
# suresi uzerinden gidiyordu, BEAT uzerinden DEGIL. Pilotta 4 cumle ama
# 5 beat vardi: s001 cumlesi 2.587 sn oldugu icin "sahne ortasi" 1.29'a
# dusuyordu — yani b002'nin icine. **b001 (0-0.862 sn) HICBIR kareyle
# orneklenmiyordu** ve kusurlu ACILIS PLANI incelemenin disinda kaldi
# (cam arkasi muze vitrini ancak ELLE kare cikarilinca goruldu).
# Ustelik yakinlik elemesi (`>= 0.35 sn`) bir beat'in TEK temsilcisini de
# eleyebiliyordu — sessiz atlama.
#
# BU PLANLAYICI: her beat'e ZORUNLU bir temsil karesi verir; zorunlu kareler
# yakinlik elemesiyle ASLA dusurulmez. Kare zamanlari FPS izgarasina oturur
# ve beat sinirindan yarim kare (epsilon) iceride tutulur — boylece komsu
# beat'e TASMAZ. Toplam hedef `max(en_az_kare, beat_sayisi)`: beat sayisi
# 11'i asarsa kare sayisi OLCULU olarak yukseltilir, sessizce atlanmaz.
KARE_EN_AZ = 11
KARE_MIN_AYRIM_SN = 0.35


def kare_ornekleme_plani(beatler, *, sure_sn: float,
                         en_az_kare: int = KARE_EN_AZ, fps: float = 30.0,
                         min_ayrim_sn: float = KARE_MIN_AYRIM_SN) -> dict:
    """Her beat'i EN AZ bir kareyle kapsayan DETERMINISTIK ornekleme plani.

    `beatler`: [{"beat_id","bas_sn","sure_sn"} ...]
    Doner: {"anlar", "beat_kare", "kapsanmayan", "zorunlu", "dolgu",
            "hedef", "yeterli", "epsilon_sn"}
    Ag/dosya KULLANMAZ; rastgelelik YOK.
    """
    try:
        liste = [b for b in (beatler or []) if isinstance(b, dict)]
    except TypeError:
        return {"olculdu": False, "neden": "GIRDI-BOZUK", "yeterli": False}
    toplam = _sayi(sure_sn)
    f = _sayi(fps) or 30.0
    if not liste or toplam <= 0 or f <= 0:
        return {"olculdu": False, "neden": "OLCU-YOK", "yeterli": False}
    eps = 0.5 / f                      # YARIM KARE — sinirdan iceride kal
    hedef = max(int(en_az_kare or 0), len(liste))

    def _izgara(t, alt, ust):
        """Zamani FPS izgarasina oturt ve [alt, ust] araliginda TUT."""
        t = min(max(t, alt), ust)
        k = round(t * f)
        v = k / f
        if v < alt:
            v = math.ceil(alt * f) / f
        if v > ust:
            v = math.floor(ust * f) / f
        return round(min(max(v, alt), ust), 4)

    zorunlu, beat_kare, kapsanmayan = [], {}, []
    for b in liste:
        bid = str(b.get("beat_id") or "")
        b0 = _sayi(b.get("bas_sn"))
        b1 = b0 + _sayi(b.get("sure_sn"))
        b1 = min(b1, toplam)
        alt, ust = b0 + eps, b1 - eps
        if ust < alt:                  # beat yarim kareden kisa
            kapsanmayan.append(bid)
            beat_kare[bid] = []
            continue
        t = _izgara(b0 + (b1 - b0) / 2.0, alt, ust)
        zorunlu.append(t)
        beat_kare[bid] = [t]

    # ── DOLGU: hedefe ulasmak icin zaman cizgisine DETERMINISTIK dagit ──
    anlar = list(zorunlu)
    dolgu = []
    if len(anlar) < hedef:
        bolme = hedef - len(anlar) + 1
        adaylar = [toplam * (i / bolme) for i in range(1, bolme)]
        # Ek aday: her beat'in ilk ve son ceyregi (deterministik sira)
        for b in liste:
            b0 = _sayi(b.get("bas_sn"))
            b1 = min(b0 + _sayi(b.get("sure_sn")), toplam)
            if b1 - b0 > 4 * eps:
                adaylar.append(b0 + (b1 - b0) * 0.25)
                adaylar.append(b0 + (b1 - b0) * 0.75)
        for ham in adaylar:
            if len(anlar) >= hedef:
                break
            # Dolgu karesi de BIR BEAT'IN ICINDE olmali (edge-safe)
            yer = None
            for b in liste:
                b0 = _sayi(b.get("bas_sn"))
                b1 = min(b0 + _sayi(b.get("sure_sn")), toplam)
                if b0 + eps <= ham <= b1 - eps:
                    yer = (str(b.get("beat_id") or ""), b0 + eps, b1 - eps)
                    break
            if not yer:
                continue
            t = _izgara(ham, yer[1], yer[2])
            if any(abs(t - x) < min_ayrim_sn for x in anlar):
                continue
            anlar.append(t)
            dolgu.append(t)
            beat_kare.setdefault(yer[0], []).append(t)

    anlar = sorted(set(anlar))
    for bid in beat_kare:
        beat_kare[bid] = sorted(set(beat_kare[bid]))
    return {
        "olculdu": True, "anlar": anlar, "beat_kare": beat_kare,
        "kapsanmayan": kapsanmayan, "zorunlu": sorted(set(zorunlu)),
        "dolgu": sorted(set(dolgu)), "hedef": hedef, "fps": f,
        "epsilon_sn": round(eps, 5), "beat": len(liste),
        "kare": len(anlar),
        "yeterli": (not kapsanmayan) and len(anlar) >= hedef,
        "sebep": ("" if (not kapsanmayan) and len(anlar) >= hedef else
                  (f"kapsanmayan beat: {kapsanmayan}" if kapsanmayan else
                   f"{len(anlar)} kare < hedef {hedef}")),
    }


# ═══════════ 5c) EKRAN KUNYESI KISA BICIMI (Faz I-31) ══════════════════
#
# ⚠ POLITIKA (I-31, deterministik ve aciklanabilir):
# EKRANDAKI kunye YALNIZCA "eser sahibi / LISANS KISA ADI" tasir.
# TAM eser adi, kaynak URL, lisans URL ve provenance `lisans.atif_metni`
# ciktisinda ve `attribution.txt`te EKSIKSIZ kalir — ekran kunyesi bir
# OZET'tir, atfin YERINE GECMEZ.
#
# I-30'da olculen kusur: `eser_sahibi` uzun oldugunda satir yatay guvenli
# alani asiyordu (olculen gercek vaka: 155 karakterlik Palomar/STScI bilim
# ekibi kunyesi -> 2473.8px > 1792px).
#
# SIRALI ve DETERMINISTIK cozum (rastgelelik YOK):
#   1. TAM bicim sigiyorsa AYNEN kullanilir (mevcut davranis korunur).
#   2. Sigmiyorsa KURUM BICIMI: sahip alani ayraclardan (`,` `;` `/` `|`
#      ` - ` ` — `) bolunur ve BIRINCI parca (birincil kurum/kisi) alinir.
#      Bu bir UYDURMA DEGIL, metnin kendi ilk ogesidir.
#   3. Hala sigmiyorsa kurum adi KELIME SINIRINDA kirpilir + "…".
# ⚠ LISANS KISA ADI HICBIR ADIMDA KIRPILMAZ. Lisans tek basina bile
# sigmiyorsa metin URETILMEZ ve karar cagirana birakilir (PRE-QA fail).
# ⚠ SAHIP BOSSA UYDURULMAZ: `eksik=True` doner, PRE-QA durustce BLOKE eder.
KUNYE_AYIRAC = re.compile(r"\s*[,;/|]\s*|\s+—\s+|\s+-\s+")
KUNYE_BIRLESTIRICI = " / "


def kunye_kisa_bicim(eser_sahibi, lisans_kisa, *, punto: float,
                     kare_genislik: float, guvenli_kenar: float,
                     em_orani: float = EM_BUYUK_HARF,
                     harf_araligi_em: float = KUNYE_HARF_ARALIGI_EM) -> dict:
    """Ekran kunyesinin KISA bicimi. Saf fonksiyon; ag/dosya KULLANMAZ."""
    sahip = str(eser_sahibi or "").strip()
    lis = str(lisans_kisa or "").strip().upper()
    punto = _sayi(punto)
    g = _sayi(kare_genislik)
    kenar = _sayi(guvenli_kenar)
    birim = punto * (_sayi(em_orani) + _sayi(harf_araligi_em))
    temel = {"eser_sahibi": sahip, "lisans": lis, "punto": punto,
             "kullanilabilir_px": round(g - 2 * kenar, 1)}
    if not sahip:
        return dict(temel, metin="", eksik=True, yontem="SAHIP-YOK",
                    kisaltildi=False,
                    sebep="atif zorunlu ama eser sahibi YOK — UYDURULMAZ")
    if not lis:
        return dict(temel, metin="", eksik=True, yontem="LISANS-YOK",
                    kisaltildi=False,
                    sebep="atif zorunlu ama lisans kisa adi YOK — UYDURULMAZ")
    if punto <= 0 or g <= 0 or birim <= 0:
        # Olculemez -> KISALTMA YAPMA, tam bicimi don (engelleme yok).
        return dict(temel, metin=f"{sahip}{KUNYE_BIRLESTIRICI}{lis}",
                    eksik=False, yontem="OLCULEMEDI", kisaltildi=False)
    kullanilabilir = g - 2 * kenar
    ek = f"{KUNYE_BIRLESTIRICI}{lis}"
    ek_px = len(ek) * birim
    sahip_butce = int((kullanilabilir - ek_px) // birim)
    if sahip_butce <= 0:
        # ⚠ LISANS TEK BASINA SIGMIYOR -> metin URETME; hukmu PRE-QA verir.
        return dict(temel, metin="", eksik=True, yontem="LISANS-SIGMIYOR",
                    kisaltildi=False, sahip_butce=sahip_butce,
                    sebep=(f"lisans kisa adi tek basina yatay guvenli alana "
                           f"sigmiyor (punto {punto}) — lisans KIRPILMAZ"))
    if len(sahip) <= sahip_butce:
        return dict(temel, metin=f"{sahip}{ek}", eksik=False,
                    yontem="TAM", kisaltildi=False, sahip_butce=sahip_butce)
    # 2) KURUM BICIMI — metnin KENDI ilk ogesi
    kurum = (KUNYE_AYIRAC.split(sahip)[0] or "").strip()
    if kurum and len(kurum) <= sahip_butce:
        return dict(temel, metin=f"{kurum}{ek}", eksik=False,
                    yontem="KURUM", kisaltildi=True, sahip_butce=sahip_butce,
                    tam_sahip=sahip)
    # 3) KELIME SINIRINDA KIRPMA (yalniz SAHIP alani)
    ham = kurum or sahip
    hedef = max(1, sahip_butce - 1)
    kirpik = ham[:hedef]
    if " " in kirpik and len(ham) > hedef:
        kirpik = kirpik.rsplit(" ", 1)[0]
    kirpik = kirpik.rstrip(" ,;/|-—")
    return dict(temel, metin=f"{kirpik}…{ek}", eksik=False,
                yontem="KIRPMA", kisaltildi=True, sahip_butce=sahip_butce,
                tam_sahip=sahip)


def yatay_guvenli_alan_olcusu(katmanlar, *, kare_genislik: float,
                              guvenli_kenar: float,
                              em_orani: float = EM_BUYUK_HARF,
                              harf_araligi_em: float = KUNYE_HARF_ARALIGI_EM
                              ) -> dict:
    """Yazi katmanlari YATAY guvenli alani asiyor mu? (saf fonksiyon)

    `katmanlar`: [{"ad","metin","punto","hizalama"?} ...]
    `hizalama`: "sag" (kunye) | "sol" (baslik/altyazi). Verilmezse "sol".
    Olculemeyen katman ENGELLENMEZ (olcu/metin yoksa atlanir).
    """
    try:
        liste = [k for k in (katmanlar or []) if isinstance(k, dict)]
    except TypeError:
        return {"olculdu": False, "neden": "GIRDI-BOZUK"}
    g = _sayi(kare_genislik)
    kenar = _sayi(guvenli_kenar)
    if g <= 0:
        return {"olculdu": False, "neden": "OLCU-YOK"}
    kullanilabilir = g - 2 * kenar
    birim = _sayi(em_orani) + _sayi(harf_araligi_em)
    ihlaller, olcumler = [], []
    for k in liste:
        metin = str(k.get("metin") or "")
        punto = _sayi(k.get("punto"))
        if not metin or punto <= 0 or birim <= 0:
            continue                      # olculemez -> ENGELLEME
        genislik_px = len(metin) * punto * birim
        kayit = {"ad": str(k.get("ad") or ""), "karakter": len(metin),
                 "punto": punto,
                 "tahmini_genislik_px": round(genislik_px, 1),
                 "kullanilabilir_px": round(kullanilabilir, 1),
                 "hizalama": str(k.get("hizalama") or "sol"),
                 "em_birim": round(birim, 4)}
        if genislik_px > kullanilabilir + 1e-6:
            kayit["ihlal"] = "YATAY"
            kayit["tasma_px"] = round(genislik_px - kullanilabilir, 1)
            ihlaller.append(kayit)
        olcumler.append(kayit)
    return {"olculdu": True, "kare_genislik": g, "guvenli_kenar": kenar,
            "kullanilabilir_px": round(kullanilabilir, 1),
            "em_birim": round(birim, 4), "katman": len(olcumler),
            "olcumler": olcumler, "ihlaller": ihlaller,
            "sigan_karakter_tavani": (int(kullanilabilir / (birim * 21))
                                      if birim > 0 else 0),
            "temiz": not ihlaller}


def yazi_cakismasi(katmanlar, *, tolerans: float = 0.005) -> dict:
    """Ayni anda ekranda olan yazilar birbirini ORTUYOR mu?

    Cakisma = ZAMAN araliklari kesisiyor **ve** DIKEY araliklar kesisiyor.
    Ikisi birden olmadan cakisma yoktur (11 Agu'da baslik ile alt band tam
    boyle bindirmisti ve ikisi de okunamaz olmustu).
    """
    try:
        liste = [k for k in (katmanlar or []) if isinstance(k, dict)]
    except TypeError:
        return {"olculdu": False, "neden": "GIRDI-BOZUK"}
    ciftler = []
    for i in range(len(liste)):
        for j in range(i + 1, len(liste)):
            a, b = liste[i], liste[j]
            a0, a1 = _sayi(a.get("bas_sn")), _sayi(a.get("bas_sn")) + _sayi(
                a.get("sure_sn"))
            b0, b1 = _sayi(b.get("bas_sn")), _sayi(b.get("bas_sn")) + _sayi(
                b.get("sure_sn"))
            if a1 <= b0 + 1e-9 or b1 <= a0 + 1e-9:
                continue                      # zaman kesismiyor
            au, aa = _sayi(a.get("y_ust")), _sayi(a.get("y_ust")) + _sayi(
                a.get("yukseklik"))
            bu, ba = _sayi(b.get("y_ust")), _sayi(b.get("y_ust")) + _sayi(
                b.get("yukseklik"))
            if aa <= bu + tolerans or ba <= au + tolerans:
                continue                      # dikey kesismiyor
            ciftler.append({
                "a": str(a.get("ad") or ""), "b": str(b.get("ad") or ""),
                "zaman": [round(max(a0, b0), 3), round(min(a1, b1), 3)],
                "dikey": [round(max(au, bu), 4), round(min(aa, ba), 4)]})
    return {"olculdu": True, "katman": len(liste), "cakisan_cift": ciftler,
            "tolerans": tolerans, "temiz": not ciftler}


# ═══════════════ 6) ALTYAZI KUPLERI (Faz I-16) ══════════════════════════

# Okunabilirlik siniri: satir basina karakter ve satir sayisi.
# BBC/Netflix altyazi kilavuzlarinin ortak paydasi 37-42 karakter/satir ve
# en fazla 2 satirdir. Profilin `maks_satir_karakter` degeri (42) taban alinir.
ALTYAZI_MAKS_SATIR = 2
# Bir kupun ekranda kalmasi gereken en kisa sure (profil `min_gorunme_sn`).
# Bundan kisa kup KOMSUSUYLA BIRLESTIRILIR, ekrana atilmaz.
ALTYAZI_MIN_SN = 1.2
# Okuma hizi tavani (karakter/sn). 20 cps yayin pratiginde rahat okunur ust
# siniridir; asilirsa kup "cok hizli" olarak RAPORLANIR (uydurma yok).
ALTYAZI_MAKS_CPS = 20.0


def altyazi_kupleri(cumleler, *, maks_karakter: int = 42,
                    maks_satir: int = ALTYAZI_MAKS_SATIR,
                    min_sn: float = ALTYAZI_MIN_SN,
                    maks_cps: float = ALTYAZI_MAKS_CPS) -> dict:
    """Cumle zamanlamalarindan OKUNABILIR altyazi kupleri uret.

    `cumleler`: [{"bas","sure","metin"} ...] — edge-tts `SentenceBoundary`
    ciktisi. Cumle kendi icinde `maks_karakter*maks_satir`e sigmiyorsa
    KELIME SINIRINDA parcalara bolunur ve cumlenin suresi parcalara
    KARAKTER AGIRLIGIYLA dagitilir.

    ⚠ DURUST ETIKET: parca ici zamanlama OLCUM DEGIL, orantili dagitimdir.
    Motor cumle sinirlari veriyor, kelime sinirlari vermiyor (edge-tts 7.2.8
    yalnizca `SentenceBoundary` uretiyor — olculdu). Her kup
    `zamanlama: "olculdu" | "orantili"` alani tasir; iddia sisirilmez.
    """
    try:
        liste = [c for c in (cumleler or []) if isinstance(c, dict)]
    except TypeError:
        return {"olculdu": False, "neden": "GIRDI-BOZUK", "kupler": []}
    kapasite = max(8, int(maks_karakter) * max(1, int(maks_satir)))
    kupler = []
    for c in liste:
        metin = " ".join(str(c.get("metin") or "").split())
        bas = _sayi(c.get("bas"))
        sure = _sayi(c.get("sure"))
        if not metin or sure <= 0:
            continue
        if len(metin) <= kapasite:
            parcalar = [metin]
        else:
            # ⚠ DENGELI BOLME, acgozlu doldurma DEGIL. Acgozlu doldurma son
            # parcayi ARTIK olarak birakiyor: olculdu ki 88 karakterlik bir
            # cumle "76 + 12" seklinde bolununce ikinci kup 0.659 sn suruyor
            # ve `min_sn` (1.2 sn) okunabilirlik tabaninin ALTINA dusuyor.
            # Parca sayisi once hesaplanir, sonra kelimeler esit paylastirilir.
            kelimeler = metin.split()
            adet = max(2, -(-len(metin) // kapasite))
            parcalar = _dengeli_bol(kelimeler, adet, kapasite)
        toplam_karakter = sum(len(p) for p in parcalar) or 1
        t = bas
        for i, p in enumerate(parcalar):
            pay = sure * (len(p) / toplam_karakter)
            if i == len(parcalar) - 1:
                pay = max(0.0, (bas + sure) - t)     # yuvarlama artigi son kupe
            kupler.append({
                "bas_sn": round(t, 3), "sure_sn": round(pay, 3),
                "metin": p,
                "satirlar": _satir_bol(p, maks_karakter, maks_satir),
                "zamanlama": "olculdu" if len(parcalar) == 1 else "orantili"})
            t += pay

    # ── Cok kisa kupleri KOMSUSUYLA BIRLESTIR (ekrana atma) ──
    birlesik, atlanan = [], 0
    for k in kupler:
        if birlesik and k["sure_sn"] < min_sn and \
                abs(birlesik[-1]["bas_sn"] + birlesik[-1]["sure_sn"]
                    - k["bas_sn"]) < 0.05:
            onceki = birlesik[-1]
            yeni = f"{onceki['metin']} {k['metin']}".strip()
            if len(yeni) <= kapasite:
                onceki["metin"] = yeni
                onceki["satirlar"] = _satir_bol(yeni, maks_karakter, maks_satir)
                onceki["sure_sn"] = round(onceki["sure_sn"] + k["sure_sn"], 3)
                onceki["zamanlama"] = "orantili"
                atlanan += 1
                continue
        birlesik.append(k)

    hizli = [k for k in birlesik
             if k["sure_sn"] > 0 and len(k["metin"]) / k["sure_sn"] > maks_cps]
    uzun_satir = [k for k in birlesik
                  if any(len(s) > maks_karakter for s in k["satirlar"])]
    cok_satir = [k for k in birlesik if len(k["satirlar"]) > maks_satir]
    return {
        "olculdu": True, "kupler": birlesik, "kup_sayisi": len(birlesik),
        "birlestirilen": atlanan,
        "maks_karakter": int(maks_karakter), "maks_satir": int(maks_satir),
        "min_sn": min_sn, "maks_cps": maks_cps,
        "olculen_kup": sum(1 for k in birlesik
                           if k["zamanlama"] == "olculdu"),
        "orantili_kup": sum(1 for k in birlesik
                            if k["zamanlama"] == "orantili"),
        "cok_hizli": hizli, "uzun_satir": uzun_satir, "cok_satir": cok_satir,
        "temiz": not (hizli or uzun_satir or cok_satir),
    }


# Bir satirin/kupun SONUNDA yalniz kalmamasi gereken kelimeler.
# `plan._SARKAN` ile ayni fikir: baslikta "…Elephant Island in" nasil yarim
# duruyorsa, altyazida da "…on the Moon / on" oyle duruyor (1080p kosusunda
# kareyle goruldu). Ayni kusur sinifi, ayni cozum.
_SARKAN_KELIME = frozenset((
    "in", "on", "at", "of", "to", "for", "with", "from", "by", "and",
    "or", "the", "a", "an", "as", "into", "over", "after", "before",
    "is", "was", "were", "that", "which", "but",
    "ve", "ile", "icin", "gibi", "kadar", "de", "da", "ki", "bir"))


def _sarkani_tasi(parcalar: list, kapasite: int) -> list:
    """Parca/satir sonundaki SARKAN kelimeyi bir sonrakine tasi.

    Tasima yalnizca (a) sonraki parca varsa, (b) kapasite tasmiyorsa ve
    (c) parca bosalmiyorsa yapilir. Aksi halde OLDUGU GIBI birakilir —
    zorla duzeltip metni bozmaktansa kusur gorunur kalir.
    """
    out = [list(str(p).split()) for p in parcalar]
    for i in range(len(out) - 1):
        while (len(out[i]) > 1
               and out[i][-1].lower().strip(",;:.") in _SARKAN_KELIME
               and len(" ".join(out[i + 1])) + len(out[i][-1]) + 1 <= kapasite):
            out[i + 1].insert(0, out[i].pop())
    return [" ".join(p) for p in out if p]


def _dengeli_bol(kelimeler: list, adet: int, kapasite: int) -> list:
    """Kelimeleri `adet` parcaya OLABILDIGINCE ESIT uzunlukta bol.

    Hedef uzunluk = toplam/adet. Bir parca hedefi asmak uzereyse kesilir;
    kapasite ASILAMAZ (kapasite asilirsa parca sayisi artirilir). Kelime
    ortasindan ASLA bolunmez.
    """
    if adet < 2 or not kelimeler:
        return [" ".join(kelimeler)] if kelimeler else [""]
    toplam = len(" ".join(kelimeler))
    for deneme in range(adet, adet + 4):        # kapasite tutmazsa artir
        hedef = toplam / deneme
        parcalar, su_an = [], ""
        for k in kelimeler:
            aday = f"{su_an} {k}".strip()
            if su_an and (len(aday) > kapasite or
                          (len(su_an) >= hedef and
                           len(parcalar) < deneme - 1)):
                parcalar.append(su_an)
                su_an = k
            else:
                su_an = aday
        if su_an:
            parcalar.append(su_an)
        parcalar = _sarkani_tasi(parcalar, kapasite)
        if all(len(p) <= kapasite for p in parcalar):
            return parcalar
    return parcalar


def _satir_bol(metin: str, maks_karakter: int, maks_satir: int) -> list:
    """Kelime sinirinda satirlara bol; harf ortasindan ASLA kesme."""
    kelimeler = str(metin or "").split()
    satirlar, su_an = [], ""
    for k in kelimeler:
        aday = f"{su_an} {k}".strip()
        if len(aday) > maks_karakter and su_an:
            satirlar.append(su_an)
            su_an = k
        else:
            su_an = aday
    if su_an:
        satirlar.append(su_an)
    # ⚠ Satir sonunda sarkan edat/baglac birakma ("…on the Moon" / "on").
    satirlar = _sarkani_tasi(satirlar, maks_karakter)
    return satirlar[:max(1, int(maks_satir))] or [""]


# ═══════════ 7) OPTIK HAREKET / DURAGANLIK (Faz I-17) ═══════════════════
#
# I-16 ciktisi teknik olarak temizdi ama IZLEYICI ICIN amatordu: dort statik
# fotograf 17.6 sn boyunca duruyordu ve bir sahne 5.21 sn boyunca neredeyse
# HIC DEGISMIYORDU. "hareket=static" plan tarafinda gorunuyordu ama hicbir
# kapi bunu olcmuyordu. Bu bolum ekranda GERCEKTEN ne kadar hareket
# oldugunu olcer — plan beyanini degil, cikti karelerini.
#
# ⚠ OLCUM SOZLESMESI: `farklar`, videodan `ornek_fps` hizinda alinan
# ardisik gri kareler arasindaki ORTALAMA MUTLAK FARK degerleridir
# (0-255 olceginde). Esikler bu ornekleme ile ANLAMLIDIR; ornekleme
# degisirse esikler de yeniden kalibre edilmelidir. Ornekleyici bu modulde
# DEGIL (saf kalsin diye) — komutu `optik_ornek_komutu()` uretir.

OPTIK_ORNEK_FPS = 4
OPTIK_ORNEK_OLCU = (64, 36)

# ⚠ ESIK GERCEK OLCUMDEN TURETILDI (I-16 ciktisi, 4 fps / 64x36):
#     b002 "static"   -> 0.914   (kusurlu sahne)
#     b001 push-in    -> 3.551   (olculen EN ZAYIF hareketli sahne)
#     b003 push-in    -> 5.102
#     b004 pull-out   -> 7.030
# Esik iki olcum arasina, DURAGAN tarafa yakin konuldu ki yanlis pozitif
# uretmesin: 2.0. (Orta nokta 2.23 olurdu; 2.0 daha muhafazakar.)
OPTIK_DURGUN_ESIGI = 2.0
# Sureler PROFILDEN turetildi, uydurulmadi:
#   WARN = shot_min_sn (1.5) — profilin izin verdigi EN KISA cekim kadar
#          duragan kalmak zaten bir cekim boyu olu demektir
#   FAIL = 2 x shot_min_sn (3.0)
OPTIK_DURGUN_WARN_SN = 1.5
OPTIK_DURGUN_FAIL_SN = 3.0
# ⚠ UST SINIR — duraganligin AYNASI: kamera COK HIZLI olabilir.
#
# ⚠ DURUST SINIR (I-17'de olculdu): bu esik SIYAH KENAR TESPITI DEGILDIR.
# Siyah bantli kare 38.911, duzeltilmis TEMIZ hizli pan 34.525 olctu —
# aralarinda yalnizca %12 var, yani optik BUYUKLUK bu iki durumu AYIRT
# EDEMEZ. Kenar tasmasi icin ayri ve dogru enstruman eklendi:
# `kenar_siyahligi_olcusu`. Bu esik yalnizca "kamera fazla hizli" sinyalidir
# ve olculen mesru en hizli panin (24-35 bandi) USTUNE konuldu.
OPTIK_ASIRI_ESIGI = 45.0


# Kenarin "siyah" sayildigi parlaklik (0-255). Gercek goruntu kenari nadiren
# 16'nin altina duser; tasma bolgesi ise TAM siyahtir (0).
KENAR_SIYAH_ESIGI = 16.0
# Kenar seridinin kare genisligine orani (orneklenmis karede en az 1 sutun).
KENAR_SERIT_ORANI = 0.04


def kenar_siyahligi_olcusu(ham: bytes, *, olcu: tuple = OPTIK_ORNEK_OLCU,
                           siyah_esigi: float = KENAR_SIYAH_ESIGI,
                           serit_orani: float = KENAR_SERIT_ORANI) -> dict:
    """Kadrajdan TASMA sonucu kenarda SIYAH BANT olusmus mu?

    ⚠ I-17'de GERCEKTEN yasandi: `pan-left` + `punch-1.6` kadrajinda sag
    kenarda siyah bant olustu (16.72 sn karesinde goruldu). Kok neden
    `motion._guvenli_pay`in CSS `scale(S) translate(x%)` sirasini hesaba
    katmamasiydi — kayma ekranda S KAT buyuyor.
    """
    try:
        g, y = int(olcu[0]), int(olcu[1])
    except (TypeError, ValueError, IndexError):
        return {"olculdu": False, "neden": "OLCU-YOK"}
    n = g * y
    if not ham or n <= 0 or len(ham) < n:
        return {"olculdu": False, "neden": "ORNEK-YOK"}
    serit = max(1, int(g * _sayi(serit_orani, KENAR_SERIT_ORANI)))
    adet = len(ham) // n
    kareler = []
    for k in range(adet):
        blok = ham[k * n:(k + 1) * n]
        sol, sag = [], []
        for satir in range(y):
            bas = satir * g
            sol.extend(blok[bas:bas + serit])
            sag.extend(blok[bas + g - serit:bas + g])
        genel = sum(blok) / n
        kareler.append({
            "kare": k,
            "sol": round(sum(sol) / max(1, len(sol)), 2),
            "sag": round(sum(sag) / max(1, len(sag)), 2),
            "genel": round(genel, 2)})
    # Kenar SIYAH sayilir: esigin altinda VE genel parlakligin cok altinda
    # (koyu bir goruntuyu yanlislikla "tasma" saymamak icin).
    ihlal = [k for k in kareler
             if (k["sol"] < siyah_esigi or k["sag"] < siyah_esigi)
             and k["genel"] > siyah_esigi * 2]
    return {
        "olculdu": True, "kare": adet, "serit_sutun": serit,
        "siyah_esigi": siyah_esigi,
        "ihlal_kare": len(ihlal), "ihlal_orani": round(len(ihlal) / max(1, adet), 4),
        "ornek_ihlal": ihlal[:3],
        "en_koyu_sol": min((k["sol"] for k in kareler), default=None),
        "en_koyu_sag": min((k["sag"] for k in kareler), default=None),
        "temiz": not ihlal,
    }


def optik_ornek_komutu(video_yolu: str, *, ornek_fps: int = OPTIK_ORNEK_FPS,
                       olcu: tuple = OPTIK_ORNEK_OLCU) -> list:
    """Ornekleme komutunu URETIR — bu modul onu CALISTIRMAZ.

    Kisa ve kararli: tek gecis, ham gri bayt akisi, alt surec yok.
    """
    g, y = int(olcu[0]), int(olcu[1])
    return ["ffmpeg", "-nostdin", "-v", "error", "-i", video_yolu, "-vf",
            f"fps={int(ornek_fps)},scale={g}:{y},format=gray",
            "-f", "rawvideo", "-"]


def optik_farklar(ham: bytes, *, olcu: tuple = OPTIK_ORNEK_OLCU) -> list:
    """Ham gri kare akisindan ardisik ORTALAMA MUTLAK FARK listesi.

    Saf hesap: dosya acmaz, komut kosturmaz. `ham` disaridan verilir.
    """
    try:
        g, y = int(olcu[0]), int(olcu[1])
    except (TypeError, ValueError, IndexError):
        return []
    n = g * y
    if not ham or n <= 0 or len(ham) < 2 * n:
        return []
    adet = len(ham) // n
    out = []
    for i in range(1, adet):
        a = ham[(i - 1) * n:i * n]
        b = ham[i * n:(i + 1) * n]
        out.append(round(sum(abs(a[j] - b[j]) for j in range(n)) / n, 4))
    return out


def optik_hareket_olcusu(farklar, *, ornek_fps: int = OPTIK_ORNEK_FPS,
                         sahneler=None,
                         durgun_esigi: float = OPTIK_DURGUN_ESIGI,
                         asiri_esigi: float = OPTIK_ASIRI_ESIGI,
                         warn_sn: float = OPTIK_DURGUN_WARN_SN,
                         fail_sn: float = OPTIK_DURGUN_FAIL_SN,
                         kesme_payi_sn: float = 0.5) -> dict:
    """Ekranda GERCEKTEN ne kadar hareket var? Sahne sahne olcer.

    `sahneler`: [{"ad","bas_sn","sure_sn"} ...] — verilirse sahne bazinda,
    verilmezse yalnizca genel olcum yapilir.

    ⚠ Sahne kenarlarindaki `kesme_payi_sn` DISLANIR: kesme ani devasa bir
    fark uretir ve duragan bir sahneyi "hareketli" gosterirdi.
    """
    try:
        dizi = [_sayi(f, -1.0) for f in (farklar or [])]
    except TypeError:
        return {"olculdu": False, "neden": "GIRDI-BOZUK"}
    dizi = [f for f in dizi if f >= 0]
    fps = max(1, int(_sayi(ornek_fps, OPTIK_ORNEK_FPS)))
    if len(dizi) < 2:
        return {"olculdu": False, "neden": "ORNEK-YETERSIZ",
                "ornek": len(dizi)}

    def _an(i):                       # i. farkin karsiligi olan zaman
        return (i + 1) / fps

    sahne_olcum, ihlaller = [], []
    if sahneler:
        for s in sahneler:
            if not isinstance(s, dict):
                continue
            bas = _sayi(s.get("bas_sn"))
            sure = _sayi(s.get("sure_sn"))
            if sure <= 0:
                continue
            ic = [f for i, f in enumerate(dizi)
                  if bas + kesme_payi_sn <= _an(i) < bas + sure - kesme_payi_sn]
            if not ic:
                ic = [f for i, f in enumerate(dizi)
                      if bas <= _an(i) < bas + sure]
            if not ic:
                continue
            ort = sum(ic) / len(ic)
            # En uzun KESINTISIZ duraganlik serisi
            en_uzun, su_an = 0, 0
            for f in ic:
                su_an = su_an + 1 if f < durgun_esigi else 0
                en_uzun = max(en_uzun, su_an)
            durgun_sn = round(en_uzun / fps, 3)
            kayit = {"ad": str(s.get("ad") or ""),
                     "bas_sn": round(bas, 3), "sure_sn": round(sure, 3),
                     "ornek": len(ic), "ortalama": round(ort, 3),
                     "en_dusuk": round(min(ic), 3),
                     "en_yuksek": round(max(ic), 3),
                     "durgun_sn": durgun_sn,
                     "durgun": bool(ort < durgun_esigi),
                     "asiri": bool(ort > asiri_esigi)}
            # ⚠ SEVIYE IKI OLCUMDEN BIRDEN turetilir:
            #   (a) kesintisiz duraganlik serisi
            #   (b) SAHNE ORTALAMASI duragan + sahne UZUN
            # Yalniz (a)'ya bakmak yetmiyordu: I-16'nin `static` sahnesinde
            # ortalama 0.914 (acikca duragan) ama tek tek ornekler esigin
            # etrafinda salindigi icin en uzun seri 2.0 sn cikiyor ve kapi
            # 5.21 sn'lik donuklugu WARN'a dusuruyordu. (b) tam olarak
            # "ayni asset uzun sure optik donuk" vakasini yakalar.
            uzun_ve_durgun = bool(ort < durgun_esigi and sure > fail_sn)
            uzun_ve_durgun_warn = bool(ort < durgun_esigi and sure > warn_sn)
            if durgun_sn > fail_sn or uzun_ve_durgun:
                kayit["seviye"] = "fail"
                kayit["gerekce"] = ("kesintisiz seri" if durgun_sn > fail_sn
                                    else "sahne ortalamasi duragan + uzun")
                ihlaller.append(kayit)
            elif durgun_sn > warn_sn or uzun_ve_durgun_warn:
                kayit["seviye"] = "warn"
                kayit["gerekce"] = ("kesintisiz seri" if durgun_sn > warn_sn
                                    else "sahne ortalamasi duragan")
                ihlaller.append(kayit)
            elif kayit["asiri"]:
                kayit["seviye"] = "warn"
                kayit["gerekce"] = ("optik hareket asiri — kamera cok hizli "
                                    "ya da kadrajdan tasmis olabilir")
                ihlaller.append(kayit)
            sahne_olcum.append(kayit)

    return {
        "olculdu": True, "ornek": len(dizi), "ornek_fps": fps,
        "durgun_esigi": durgun_esigi, "asiri_esigi": asiri_esigi,
        "warn_sn": warn_sn, "fail_sn": fail_sn,
        "genel_ortalama": round(sum(dizi) / len(dizi), 3),
        "sahneler": sahne_olcum, "ihlaller": ihlaller,
        "en_durgun_sahne": (min(sahne_olcum, key=lambda k: k["ortalama"])
                            if sahne_olcum else None),
        "temiz": not ihlaller,
    }


# ═══════════ 7c) GORSELIN UZAMSAL ENERJISI (Faz I-44) ═══════════════════
#
# ⚠ NEDEN VAR — I-43'TE OLCULEN KUSUR:
# I-43 zoom kovalarini optik olcum birimiyle hizaladi (taban %4.5/sn) ve
# pilotta esigi gecen sahne 2/6 -> 5/6 oldu. Kalan tek sahnenin kok nedeni
# UC RENDERLE ayristirildi ve KOVA DEGILDI:
#     ayni sure + ayni etkin hiz, KALIBRE gorsel   -> optik 3.690  ✅
#     ayni sure + ayni etkin hiz, s1'in gorseli    -> optik 1.457  ⛔
#     sure UZATILIP etkin hiz ARTIRILDI, s1 gorseli-> optik 1.643  ⛔
# Yani DUZ (dusuk uzamsal detayli) bir varlik STATIK FOTOGRAF olarak
# kullanildiginda kamera ne yaparsa yapsin ekranda hareket URETMIYOR.
# Optik kapi bunu ancak RENDER'DAN SONRA gorebiliyordu; medya secimi ve
# plan tarafinda gorselin uzamsal enerjisi HIC OLCULMUYORDU.
#
# ⚠ OLCUM SOZLESMESI OPTIKLE BIREBIR AYNI (ikinci aritmetik YOK): gorsel
# `OPTIK_ORNEK_OLCU` (64x36) griye indirgenir; enerji = KOMSU PIKSELLER
# ARASI ORTALAMA MUTLAK FARK (yatay + dikey), 0-255 olceginde. Ornekleyici
# bu modulde DEGIL (saf kalsin diye) — komutu `gorsel_ornek_komutu()` uretir.
GORSEL_ORNEK_OLCU = OPTIK_ORNEK_OLCU

# ⚠ ESIK GERCEK RENDER'DAN TURETILDI, TAHMIN EDILMEDI.
# NEDENSEL AILE: TEK gorselin efektif cozunurlugu kademeli dusuruldu
# (scale W -> geri 1920, DUZGUN yeniden ornekleme; `neighbor` blok kenari
# uretip enerjiyi YAPAY yuksek tuttugu icin elendi — olculdu). Icerik ve
# kompozisyon AYNI; degisen TEK sey uzamsal enerji. Her uye URETIM TABANI
# oraniyla (0.045), 4.0 sn, EN KOTU kamera birlesimiyle (`pan: yok`) 1080p
# render edilip `optik_hareket_olcusu` ile olculdu:
#     enerji   optik   pay     en uzun duragan seri
#      5.866   0.719   x0.36     3.0 sn   ⛔ esigin ALTINDA
#      7.590   1.011   x0.51     3.0 sn   ⛔
#      9.092   1.294   x0.65     3.0 sn   ⛔
#     10.249   1.522   x0.76     3.0 sn   ⛔
#     11.589   1.841   x0.92     1.0 sn   ⛔ <- OLCULEN EN YUKSEK KALAN
#     12.589   2.172   x1.09     0.5 sn   ✅ <- OLCULEN EN DUSUK GECEN
#     15.789   2.819   x1.41     0.0 sn   ✅
# DOGAL KONTROL (6 gercek onbellek gorseli): 7.557 / 12.330 / 13.867 /
# 14.887 / 15.792 / 18.083 — I-43 pilotunda optigi esigin ALTINDA kalan TEK
# gorsel 7.557 olandi. Nedensel aile ve dogal kontrol AYNI yeri isaret ediyor.
#
# Esik OLCULEN KUSURLU tarafa konuldu (11.589 = optigi esigin altinda oldugu
# olculen EN YUKSEK enerji) ki kapi, GECTIGI OLCULEN hicbir varligi
# (en dusuk gecen 12.589) reddetmesin.
UZAMSAL_ENERJI_ESIGI = 11.589


def gorsel_ornek_komutu(gorsel_yolu: str, *,
                        olcu: tuple = GORSEL_ORNEK_OLCU,
                        kirpma: Optional[dict] = None) -> list:
    """Ornekleme komutunu URETIR — bu modul onu CALISTIRMAZ.

    ⚠ `optik_ornek_komutu` ile AYNI olcu ve AYNI gri bicim; tek fark tek
    kare alinmasi. Iki taraf ayrisirsa esik anlamini yitirir.

    ⚠ FAZ I-45: `kirpma` verilirse (normalize {x,y,w,h}) once KIRPILIR,
    sonra ornek olcusune indirgenir — cunku renderer da once kadrajlar.
    Kirpma YOKSA komut I-44'teki haliyle BIT-BIT aynidir.
    """
    g, y = int(olcu[0]), int(olcu[1])
    vf = f"scale={g}:{y},format=gray"
    if kirpma:
        try:
            kx, ky = _sayi(kirpma.get("x")), _sayi(kirpma.get("y"))
            kw, kh = _sayi(kirpma.get("w")), _sayi(kirpma.get("h"))
        except (AttributeError, TypeError):
            kx = ky = kw = kh = 0.0
        if kw > 0 and kh > 0:
            vf = (f"crop=iw*{kw:.6f}:ih*{kh:.6f}:iw*{kx:.6f}:ih*{ky:.6f},"
                  + vf)
    return ["ffmpeg", "-nostdin", "-v", "error", "-i", gorsel_yolu, "-vf",
            vf, "-frames:v", "1", "-f", "rawvideo", "-"]


# ═══════════ 7d) GOSTERILEN KADRAJ BOLGESI (Faz I-45) ═══════════════════
#
# ⚠ NEDEN VAR — I-44 PILOTUNDA OLCULEN YANLIS ALARM:
# I-44 enerjiyi TUM KAREDE olcuyordu, oysa renderer `kadraj`/`punch` ile
# KIRPIYOR: olculen piksellerin bir kismi ekrana HIC gelmiyor. b002 tam
# karede 7.557 olcup isaretlendi ama gercek render'da optik 2.288 ile esigi
# GECTI.
#
# ⚠ GEOMETRI UYDURULMADI — `editorv2/Kamera.tsx`ten BIREBIR turetildi:
#     Zemin %100x%100, objectFit: cover,
#     transform: scale(S) translate(x%, y%), transformOrigin center.
#     CSS transform SAGDAN SOLA uygulanir ve yuzde kayma ELEMANIN KENDI
#     olcusune goredir:   q = merkez + S * ((p - merkez) + (dx, dy))
#     Tersi -> ekranda gorunen ELEMAN dikdortgeni:
#         genislik W/S, yukseklik H/S, merkez (W/2 - dx, H/2 - dy)
#     `cover` icin kapsama = max(W/sw, H/sh)  — `punch_buyutme_olcusu` ile
#     AYNI aritmetik (tek kaynak). KAYNAK piksel uzayinda normalize:
#         w = W/(S*kapsama*sw)     cx = 0.5 - dx/(kapsama*sw)
#         h = H/(S*kapsama*sh)     cy = 0.5 - dy/(kapsama*sh)
#     Kamera.tsx: kaymaX = (pxT-0.5)*2*pay*100,
#                 kaymaY = (0.5-odakY)*2*pay*100   (dx = kaymaX/100 * W)


def kadraj_kirpma_bolgesi(*, olcek, pan_x=(0.5, 0.5), odak=(0.5, 0.5),
                          guvenli_pay: float = 0.0,
                          kaynak_g=0, kaynak_y=0,
                          kare_g: float = 1920.0, kare_y: float = 1080.0,
                          t: float = 0.0) -> dict:
    """`t` aninda EKRANDA GORUNEN kaynak bolgesi (normalize, saf aritmetik).

    ⚠ OLCEMEDIYSE ENGELLEMEZ: gecersiz olcude `olculdu=False` doner
    (cozunurluk/oran kapilariyla ayni "emin degilsen engelleme" sozlesmesi).
    """
    try:
        W, H = float(kare_g), float(kare_y)
        sw, sh = float(kaynak_g), float(kaynak_y)
        S = float(olcek)
        pay = float(guvenli_pay)
        tt = min(max(float(t), 0.0), 1.0)
    except (TypeError, ValueError):
        return {"olculdu": False, "neden": "OLCU-OKUNAMADI"}
    if W <= 0 or H <= 0 or sw <= 0 or sh <= 0 or S <= 0:
        return {"olculdu": False, "neden": "OLCU-GECERSIZ"}
    try:
        px0 = float(pan_x[0])
        px1 = float(pan_x[1]) if len(pan_x) > 1 else px0
        odak_y = float(odak[1]) if len(odak) > 1 else 0.5
    except (TypeError, ValueError, IndexError):
        px0 = px1 = 0.5
        odak_y = 0.5
    kapsama = max(W / sw, H / sh)
    pxT = px0 + (px1 - px0) * tt
    dx = (pxT - 0.5) * 2.0 * pay * W
    dy = (0.5 - odak_y) * 2.0 * pay * H
    w = W / (S * kapsama * sw)
    h = H / (S * kapsama * sh)
    cx = 0.5 - dx / (kapsama * sw)
    cy = 0.5 - dy / (kapsama * sh)
    x0 = min(max(cx - w / 2.0, 0.0), 1.0)
    y0 = min(max(cy - h / 2.0, 0.0), 1.0)
    return {"olculdu": True, "olcek": round(S, 4), "kapsama": round(kapsama, 4),
            "x": round(x0, 6), "y": round(y0, 6),
            "w": round(min(w, 1.0 - x0), 6), "h": round(min(h, 1.0 - y0), 6)}


# ⚠ ESIGIN KALIBRASYON ALANI — UYDURMA DEGIL, I-44 KALIBRASYONUNUN KENDI
# KONFIGURASYONUNDAN TURETILDI. `UZAMSAL_ENERJI_ESIGI` (11.589) su tek
# konfigurasyonda olculmustu: `VidrushVideo`, oran 0.045, 4.0 sn, pan=yok.
# O konfigurasyonun kendi aritmetigi (Video.tsx `kbHesap`/`SURE_ZOOM`):
#     taban olcek = 1 + 2*22/1920 + 0.012 = 1.0349
#     tepe  olcek = max(1 + 0.045*4, taban + 0.06) = 1.1800
# Ic ice (merkezli) dikdortgenlerde ortusme  IoU = (1.0349/1.1800)^2 = 0.769
#     gezinme hizi = (1 - 0.769) / 4.0 sn = 0.0577 /sn
#
# ⚠ I-45'TE OLCULEN NEDEN: editorv2 cekimleri 0.0527-0.1139 /sn araliginda
# geziniyor. b002 tam 0.1025 /sn ile kalibrasyonun 1.78 KATI; kalibrasyon
# ailesinde ~9.1 enerjide optik 1.294 olculmustu ve 1.294 x 1.78 = 2.30,
# gercek render'da olculen 2.288 ile ortusuyor. Yani esigi BASKA bir
# gezinme hizinda uygulamak I-43'un birim uyusmazliginin AYNISIDIR ->
# alan disinda HUKUM VERILMEZ.
KALIBRASYON_GEZINME_HIZI = 0.0577


def kadraj_gezinme_hizi(bas: dict, son: dict, *, sure_sn: float,
                        kalibrasyon: float = KALIBRASYON_GEZINME_HIZI) -> dict:
    """Kameranin saniyede ne kadar YENI icerik gosterdigi (saf aritmetik).

    Iki uc kadraj dikdortgeninin ortusmemesi (1 - IoU) sureye bolunur.
    ⚠ Olcemezse hukum vermez: `olculdu=False`.
    """
    try:
        s = float(sure_sn)
    except (TypeError, ValueError):
        return {"olculdu": False, "neden": "SURE-OKUNAMADI"}
    if s <= 0 or not (isinstance(bas, dict) and isinstance(son, dict)):
        return {"olculdu": False, "neden": "GIRDI-YOK"}
    if not (bas.get("olculdu") and son.get("olculdu")):
        return {"olculdu": False, "neden": "KIRPMA-OLCULEMEDI"}
    ax0, ay0 = _sayi(bas.get("x")), _sayi(bas.get("y"))
    ax1, ay1 = ax0 + _sayi(bas.get("w")), ay0 + _sayi(bas.get("h"))
    bx0, by0 = _sayi(son.get("x")), _sayi(son.get("y"))
    bx1, by1 = bx0 + _sayi(son.get("w")), by0 + _sayi(son.get("h"))
    kesisim = (max(0.0, min(ax1, bx1) - max(ax0, bx0))
               * max(0.0, min(ay1, by1) - max(ay0, by0)))
    birlesim = ((ax1 - ax0) * (ay1 - ay0) + (bx1 - bx0) * (by1 - by0)
                - kesisim)
    if birlesim <= 0:
        return {"olculdu": False, "neden": "ALAN-YOK"}
    ortusme = kesisim / birlesim
    hiz = (1.0 - ortusme) / s
    kal = _sayi(kalibrasyon, KALIBRASYON_GEZINME_HIZI)
    return {"olculdu": True, "ortusme": round(ortusme, 4),
            "hiz": round(hiz, 4), "sure_sn": round(s, 3),
            "kalibrasyon_hizi": kal,
            # ⚠ Esik yalniz KALIBRASYON HIZINA KADAR gecerlidir.
            "kalibrasyon_icinde": bool(hiz <= kal + 1e-9)}


def uzamsal_enerji_olcusu(ham, *, olcu: tuple = GORSEL_ORNEK_OLCU,
                          esik: float = UZAMSAL_ENERJI_ESIGI) -> dict:
    """Gorselin UZAMSAL DETAYI: komsu pikseller arasi ort. mutlak fark.

    Saf hesap: dosya acmaz, komut kosturmaz. `ham` disaridan verilir.

    ⚠ OLCEMEDIYSE "yeterli" DEMEZ: `olculdu=False` doner ve `yeterli`
    anahtari HIC yazilmaz (sessiz pass yok).
    """
    try:
        g, y = int(olcu[0]), int(olcu[1])
    except (TypeError, ValueError, IndexError):
        return {"olculdu": False, "neden": "OLCU-YOK"}
    n = g * y
    if not ham or n <= 0 or len(ham) < n:
        return {"olculdu": False, "neden": "ORNEK-YOK"}
    px = ham[:n]
    toplam, adet = 0, 0
    for satir in range(y):                       # yatay komsuluk
        bas = satir * g
        for x in range(g - 1):
            toplam += abs(px[bas + x + 1] - px[bas + x])
            adet += 1
    for satir in range(y - 1):                   # dikey komsuluk
        bas = satir * g
        for x in range(g):
            toplam += abs(px[bas + g + x] - px[bas + x])
            adet += 1
    enerji = round(toplam / max(1, adet), 3)
    return {"olculdu": True, "enerji": enerji, "esik": _sayi(esik,
                                                             UZAMSAL_ENERJI_ESIGI),
            "olcu": [g, y], "ornek_piksel": n,
            "yeterli": bool(enerji > _sayi(esik, UZAMSAL_ENERJI_ESIGI))}


# ═══════════ 8) MOTION GRAMMAR (Faz I-17) ═══════════════════════════════

# Ardisik olmayan tekrari da yakalamak icin bakilan pencere. I-16'da
# push-in b001 ve b003'te kullanildi; komsu olmadiklari icin mevcut
# `ARDIL-AYNI-HAREKET` kurali gormedi. 3 = bir onceki ve iki onceki.
HAREKET_PENCERESI = 3


def motion_grammar_olcusu(sahneler, *, pencere: int = HAREKET_PENCERESI,
                          enerji_esigi: float = UZAMSAL_ENERJI_ESIGI) -> dict:
    """Kamera hareketi ve gecis CESITLILIGI — plan uzerinden olcum.

    `sahneler`: [{"beat_id","hareket","gecis","islev","sure_sn",
                  "medya_turu"?,"uzamsal_enerji"?} ...]

    ⚠ FAZ I-44: hareket CESITLILIGI tek basina yetmiyor — DUZ bir gorsel
    STATIK FOTOGRAF olarak kullanildiginda kamera ne yaparsa yapsin ekranda
    hareket uretmiyor (I-43'te uc renderle ayristirildi). `uzamsal_enerji`
    verilirse bu bacak da olculur; VERILMEZSE `enerji_olculdu=False` yazilir
    ve "temiz" DENMEZ. Olcum yalniz STATIK FOTOGRAFA uygulanir: video
    klibin KENDI hareketi vardir, hukum ona verilmez.
    """
    try:
        liste = [s for s in (sahneler or []) if isinstance(s, dict)]
    except TypeError:
        return {"olculdu": False, "neden": "GIRDI-BOZUK"}
    if not liste:
        return {"olculdu": False, "neden": "SAHNE-YOK"}

    hareketler = [str(s.get("hareket") or "") for s in liste]
    gecisler = []
    for s in liste:
        g = s.get("gecis")
        if isinstance(g, (list, tuple)):
            gecisler.extend(str(x) for x in g if x)
        elif g:
            gecisler.append(str(g))

    ardisik_tekrar = [{"indeks": i, "hareket": hareketler[i]}
                      for i in range(1, len(hareketler))
                      if hareketler[i] and hareketler[i] == hareketler[i - 1]]
    pencere_tekrar = []
    for i in range(len(hareketler)):
        onceki = hareketler[max(0, i - pencere):i]
        if hareketler[i] and hareketler[i] in onceki:
            pencere_tekrar.append({"indeks": i, "hareket": hareketler[i],
                                   "pencere": pencere})
    statik = [{"indeks": i, "sure_sn": _sayi(liste[i].get("sure_sn"))}
              for i, h in enumerate(hareketler) if h == "static"]

    # ── ISLEV TEKRARI (Faz I-24) ──
    # ⚠ `islev` bu olcume I-17'den beri GELIYORDU ama HIC KULLANILMIYORDU.
    # Ayni anlati islevindeki (hook/aciklama/sonuc) iki beat ayni kamera
    # hareketini alirsa, komsu olmasalar bile izleyici ayni "cumleyi" iki kez
    # duyar. Ardisiklik ve pencere bunu YAKALAMAZ: pencere yalnizca SON N
    # cekime bakar, islev ise videonun HER YERINE dagilabilir.
    islevler = [str(s.get("islev") or "") for s in liste]
    _islev_gorulen: dict = {}
    islev_tekrari = []
    for i, (isl, h) in enumerate(zip(islevler, hareketler)):
        if not isl or not h:
            continue
        onceki = _islev_gorulen.setdefault(isl, {})
        if h in onceki:
            islev_tekrari.append({"indeks": i, "islev": isl, "hareket": h,
                                  "ilk_indeks": onceki[h]})
        else:
            onceki[h] = i

    # ── UZAMSAL ENERJI BACAGI (Faz I-44) ──
    # ⚠ Yalniz STATIK FOTOGRAF: `medya_turu` "video" ise atlanir.
    # ⚠ FAZ I-45: esik TEK bir kamera konfigurasyonunda (gezinme 0.0577 /sn)
    # olculdu. `gezinme_hizi` verilen ve o hizin USTUNDE gezinen cekimlerde
    # HUKUM VERILMEZ — olculen alanin disina hukum tasimak I-43'un birim
    # uyusmazliginin aynisidir. Sessizce gecilmez: `gezinme_kapsam_disi`.
    _esik = _sayi(enerji_esigi, UZAMSAL_ENERJI_ESIGI)
    dusuk_enerji, enerji_olculdu, gezinme_kapsam_disi = [], False, []
    for i, s in enumerate(liste):
        ham = s.get("uzamsal_enerji")
        if ham is None:
            continue
        enerji_olculdu = True
        if str(s.get("medya_turu") or "image").lower() == "video":
            continue
        e = _sayi(ham, -1.0)
        if not (0 <= e <= _esik):
            continue
        _gz = s.get("gezinme_hizi")
        if _gz is not None and _sayi(_gz, 0.0) > KALIBRASYON_GEZINME_HIZI + 1e-9:
            gezinme_kapsam_disi.append({
                "indeks": i, "beat_id": str(s.get("beat_id") or ""),
                "uzamsal_enerji": round(e, 3), "esik": _esik,
                "gezinme_hizi": round(_sayi(_gz, 0.0), 4),
                "kalibrasyon_hizi": KALIBRASYON_GEZINME_HIZI})
            continue
        dusuk_enerji.append({
            "indeks": i, "beat_id": str(s.get("beat_id") or ""),
            "hareket": hareketler[i], "uzamsal_enerji": round(e, 3),
            "esik": _esik,
            **({"gezinme_hizi": round(_sayi(_gz, 0.0), 4)}
               if _gz is not None else {})})

    return {
        "olculdu": True,
        "sahne": len(liste),
        "hareketler": hareketler,
        "islevler": islevler,
        "islev_tekrari": islev_tekrari,
        # ⚠ SESSIZ PASS YOK: olcemedigimizde `enerji_olculdu=False`.
        "enerji_olculdu": enerji_olculdu,
        "enerji_esigi": _esik,
        "dusuk_enerji": dusuk_enerji,
        # ⚠ I-45: esigin kalibrasyon alani DISINDA kalan cekimler.
        "gezinme_kapsam_disi": gezinme_kapsam_disi,
        "kalibrasyon_gezinme_hizi": KALIBRASYON_GEZINME_HIZI,
        "benzersiz_hareket": len({h for h in hareketler if h}),
        "ardisik_tekrar": ardisik_tekrar,
        "pencere_tekrari": pencere_tekrar,
        "pencere": pencere,
        "statik_sahneler": statik,
        "gecisler": gecisler,
        "benzersiz_gecis": len({g for g in gecisler if g}),
        "gecis_dagilimi": {g: gecisler.count(g) for g in set(gecisler) if g},
        # Acilis/kapanis ritmi: ilk ve son sahnenin hareketi ayni olmamali
        "acilis_hareketi": hareketler[0] if hareketler else "",
        "kapanis_hareketi": hareketler[-1] if hareketler else "",
        "acilis_kapanis_ayri": bool(
            len(hareketler) > 1 and hareketler[0] != hareketler[-1]),
    }


# ═══════════ 8b) PUNCH BUYUTME (Faz I-27) ═══════════════════════════════
#
# ⚠ NEDEN VAR — I-26'DA OLCULEN IHLAL:
# Depo "upscale YAPILMIYOR" diyor, ama bu soz yalnizca EDINIM esigi
# (`en_az_genislik=1920`) icin geceriydi. Kamera `punch` kadraji uygularken
# kaynak SESSIZCE buyutuluyordu:
#     b002  2240x1344  punch-1.35  ->  1.281x  BUYUTME
#     b004  3000x2250  punch-1.6   ->  1.085x  BUYUTME  (I-24/I-25'in KABUL
#                                                        EDILEN render'inda DA)
# `objectFit: cover` ile kaynagin ekrandaki olcegi:
#     kapsama = max(kare_g / kaynak_g, kare_y / kaynak_y)
# Kamera zoom'u BUNUN USTUNE biner:
#     ekran_piksel_orani = kapsama x maks_zoom
# Oran > 1.0 ise kaynagin 1 pikseli ekranda 1'den fazla piksele yayilir —
# YUMUSAMA. 1080p iddiasi o cekimde KARSILIKSIZ kalir.
PUNCH_BUYUTME_TAVANI = 1.0

# ⚠ I-27'DE OLCULEN IKINCI HALKA — KADRAJ DARALTMA ile OPTIK DURAGANLIK
# BIRBIRINE BAGLI. Pan surusuyle hareket eden cekimlerde (`slow-drift`,
# `pan-*`) zoom SABITTIR (1.06); tum hareket pan'dan gelir ve pan payi
# `_guvenli_pay(zoom x kadraj_olcek)` ile olceklenir:
#     tam (1.00) -> pay 0.0255      <- HAREKET ACLIGI
#     ust (1.20) -> pay 0.0962      <- yaklasik 4 KATI
# Yani buyutmemek icin kadraji `tam`a cekmek, hareketi I-17'nin duraganlik
# esigi altina dusurebiliyor (olculdu: b005 optik 1.415 < 2.0 -> FAIL).
# Cozum kadraji zorlamak DEGIL, kaynagin EN AZ BIR punch'i tasimasini
# istemektir. En dar non-`tam` kadraj 1.2 oldugundan:
#     en_az_genislik = kare_genislik x 1.2 x 1.06
PAN_TABANLI_ZOOM = 1.06
EN_DAR_PUNCH_OLCEGI = 1.2


def en_az_kaynak_genisligi(kare_genislik, *,
                           kadraj_olcek: float = EN_DAR_PUNCH_OLCEGI,
                           taban_zoom: float = PAN_TABANLI_ZOOM) -> int:
    """Kaynak, EN AZ BIR punch kadrajini BUYUTMEDEN tasiyabilmeli.

    ⚠ `en_az_genislik=1920` yalnizca `tam` kadraji garanti eder; o kadrajda
    pan payi 0.0255'e duser ve cekim DURAGAN sayilir. Bu esik uydurma degil,
    kadraj merdiveni ile `_guvenli_pay` aritmetiginden TURETILMISTIR.
    """
    try:
        kg = float(kare_genislik)
        return int(math.ceil(kg * float(kadraj_olcek) * float(taban_zoom)))
    except (TypeError, ValueError):
        return 0


def punch_buyutme_olcusu(kaynak_g, kaynak_y, kare_g, kare_y,
                         maks_zoom, *, tavan: float = PUNCH_BUYUTME_TAVANI,
                         kadraj: str = "") -> dict:
    """Kamera kadraji kaynagi EKRANDA BUYUTUYOR mu? (saf fonksiyon)

    Ag/dosya KULLANMAZ. Olculemezse `olculdu=False` doner ve ENGELLEMEZ —
    cozunurluk/oran kapilariyla ayni sozlesme ("emin degilsen engelleme").
    """
    try:
        g, y = float(kaynak_g), float(kaynak_y)
        kg, ky = float(kare_g), float(kare_y)
        z = float(maks_zoom)
    except (TypeError, ValueError):
        return {"olculdu": False, "neden": "OLCU-OKUNAMADI", "buyutuyor": False}
    if g <= 0 or y <= 0 or kg <= 0 or ky <= 0 or z <= 0:
        return {"olculdu": False, "neden": "OLCU-GECERSIZ", "buyutuyor": False}
    kapsama = max(kg / g, ky / y)
    oran = kapsama * z
    try:
        tvn = float(tavan)
    except (TypeError, ValueError):
        tvn = PUNCH_BUYUTME_TAVANI
    return {
        "olculdu": True,
        "kaynak": [int(g), int(y)], "kare": [int(kg), int(ky)],
        "kadraj": str(kadraj or ""),
        "kapsama": round(kapsama, 4),
        "maks_zoom": round(z, 4),
        "ekran_piksel_orani": round(oran, 4),
        "tavan": tvn,
        "buyutuyor": bool(oran > tvn),
        "sebep": "" if oran <= tvn else (
            f"PUNCH-BUYUTME: kaynak {int(g)}x{int(y)} kadraj "
            f"{kadraj or '?'} ile ekranda {oran:.3f}x buyuyor "
            f"(kapsama {kapsama:.3f} x zoom {z:.3f} > tavan {tvn:.3f})"),
    }


def kadraj_buyutmeyen(kaynak_g, kaynak_y, kare_g, kare_y, taban_zoom,
                      merdiven, olcek_tablosu, *,
                      tercih: str = "", kacinilacak: str = "",
                      tavan: float = PUNCH_BUYUTME_TAVANI) -> dict:
    """Kaynagi BUYUTMEYEN EN DAR kadraji DETERMINISTIK sec.

    `taban_zoom`: kadraj carpani UYGULANMADAN once hareketin kendi zoom ucu.
    `merdiven`  : denenecek kadraj sirasi (en dar -> en genis).
    `tercih`    : plan bu kadraji istedi; BUYUTMUYORSA aynen korunur.
    `kacinilacak`: onceki cekimin kadraji — esit gecerli iki aday arasinda
                   surekliligi korumak icin ikinci sirada denenir.

    ⚠ Rastgelelik YOK, yeni kadraj UYDURULMAZ: yalnizca `merdiven`de zaten
    var olan kadrajlar denenir. Hicbiri buyutmuyorsa `secilen=None` doner ve
    KARARI CAGIRAN VERIR (kapi FAIL yazar) — sessizce kirpma/blur YOK.
    """
    def _oran(kadraj):
        z = float(taban_zoom or 0.0) * float(
            (olcek_tablosu or {}).get(kadraj, 1.0))
        return punch_buyutme_olcusu(kaynak_g, kaynak_y, kare_g, kare_y, z,
                                    tavan=tavan, kadraj=kadraj)

    istenen = _oran(tercih) if tercih else {"olculdu": False}
    if istenen.get("olculdu") and not istenen.get("buyutuyor"):
        return {"secilen": tercih, "degisti": False, "olcum": istenen,
                "denenen": [tercih]}
    if not istenen.get("olculdu"):
        # Olculemedi -> ENGELLEME, plani OLDUGU GIBI birak.
        return {"secilen": tercih or None, "degisti": False,
                "olcum": istenen, "denenen": []}
    # Sirali arama: once merdiven, ama `kacinilacak` esitlerde geri plana.
    sirali = [k for k in (merdiven or ()) if k != kacinilacak]
    sirali += [k for k in (merdiven or ()) if k == kacinilacak]
    denenen = []
    for k in sirali:
        denenen.append(k)
        o = _oran(k)
        if o.get("olculdu") and not o.get("buyutuyor"):
            return {"secilen": k, "degisti": k != tercih, "olcum": o,
                    "denenen": denenen}
    return {"secilen": None, "degisti": False, "olcum": istenen,
            "denenen": denenen}


# ═══════════ 9) IZLEYICI KALITE PUANI (Faz I-17) ════════════════════════
#
# ⚠ DURUST ETIKET: bu bir IZLEYICI ARASTIRMASI DEGIL. Zaten OLCULEN
# boyutlarin agirlikli birlesimidir ve her bilesen ham degeriyle birlikte
# raporlanir (kara kutu yok). "Izleyiciler bunu daha cok begeniyor" gibi
# bir iddia TASIMAZ; yalnizca "olculen kusur sayisi azaldi" der.
KALITE_AGIRLIK = {
    "optik_hareket": 25,      # ekranda gercekten hareket var mi
    "motion_cesitlilik": 20,  # yon/gecis tekrari
    "ritim": 15,              # sabit blok / olu final
    "tipografi": 15,          # guvenli alan + cakisma + altyazi
    "medya": 15,              # tekrar / benzerlik
    "ses": 10,                # LUFS / ambiyans dengesi
}


def izleyici_kalite_puani(*, optik=None, grammar=None, ritim=None,
                          guvenli_alan=None, cakisma=None, altyazi=None,
                          medya=None, miks=None, ambans=None) -> dict:
    """0-100 arasi BILESIK puan. Her bilesen kendi gerekcesiyle raporlanir."""
    bilesenler = {}

    def _ekle(ad, tam_puan, kosul, gerekce, olculdu=True):
        bilesenler[ad] = {
            "agirlik": tam_puan,
            "puan": (round(tam_puan * (1.0 if kosul else 0.0), 2)
                     if olculdu else None),
            "olculdu": bool(olculdu),
            "gerekce": gerekce}

    _ekle("optik_hareket", KALITE_AGIRLIK["optik_hareket"],
          bool((optik or {}).get("temiz")),
          f"duragan ihlal: {len((optik or {}).get('ihlaller') or [])}",
          olculdu=bool((optik or {}).get("olculdu")))
    g = grammar or {}
    # ⚠ I-24'TE BULUNAN RAPORLAMA KUSURU: burasi yalnizca GECEN uc kosulu
    # yaziyordu ve DUSEN kosuldan hic soz etmiyordu. Teknoloji pilotunda puan
    # 0/20 iken gerekce "benzersiz hareket 4, benzersiz gecis 3, pencere
    # tekrari 0" diyordu — hepsi YESIL. Tek kirmizi `acilis_kapanis_ayri`
    # idi (acilis ve kapanis ikisi de push-in) ama GORUNMUYORDU. Puan
    # hepsi-ya-hicbiri oldugu icin gorunmeyen kosul kusuru GIZLIYOR.
    _kosullar = {
        "ardisik_tekrar_yok": not g.get("ardisik_tekrar"),
        "pencere_tekrari_yok": not g.get("pencere_tekrari"),
        "islev_tekrari_yok": not g.get("islev_tekrari"),
        "benzersiz_gecis>=2": g.get("benzersiz_gecis", 0) >= 2,
        "acilis_kapanis_ayri": bool(g.get("acilis_kapanis_ayri")),
    }
    _dusen = [k for k, v in _kosullar.items() if not v]
    _ekle("motion_cesitlilik", KALITE_AGIRLIK["motion_cesitlilik"],
          bool(g.get("olculdu") and not _dusen),
          (f"TUM KOSULLAR GECTI (benzersiz hareket "
           f"{g.get('benzersiz_hareket')}, benzersiz gecis "
           f"{g.get('benzersiz_gecis')})" if not _dusen else
           f"DUSEN KOSUL: {', '.join(_dusen)} | acilis="
           f"{g.get('acilis_hareketi')} kapanis={g.get('kapanis_hareketi')} "
           f"| islev tekrari {len(g.get('islev_tekrari') or [])} "
           f"| pencere tekrari {len(g.get('pencere_tekrari') or [])}"),
          olculdu=bool(g.get("olculdu")))
    bilesenler["motion_cesitlilik"]["kosullar"] = _kosullar
    bilesenler["motion_cesitlilik"]["dusen_kosullar"] = _dusen
    r = ritim or {}
    _ekle("ritim", KALITE_AGIRLIK["ritim"],
          bool(r.get("olculdu") and not r.get("sabit_blok")
               and not r.get("olu_final_asildi")),
          f"sabit_blok={r.get('sabit_blok')} "
          f"olu_final={r.get('olu_final_sn')}",
          olculdu=bool(r.get("olculdu")))
    ga, ck, ay = guvenli_alan or {}, cakisma or {}, altyazi or {}
    _ekle("tipografi", KALITE_AGIRLIK["tipografi"],
          bool(ga.get("temiz") and ck.get("temiz")
               and (ay.get("temiz") if ay.get("olculdu") else True)),
          f"guvenli_alan={ga.get('temiz')} cakisma={ck.get('temiz')} "
          f"altyazi={ay.get('temiz')}",
          olculdu=bool(ga.get("olculdu")))
    m = medya or {}
    _ekle("medya", KALITE_AGIRLIK["medya"],
          bool(m.get("olculdu") and not m.get("tekrar_eden_asset")
               and not m.get("bitisik_ayni_asset")
               and not m.get("benzer_ciftler")),
          f"tekrar={len(m.get('tekrar_eden_asset') or {})} "
          f"bitisik={len(m.get('bitisik_ayni_asset') or [])}",
          olculdu=bool(m.get("olculdu")))
    mx, am = miks or {}, ambans or {}
    _ekle("ses", KALITE_AGIRLIK["ses"],
          bool(not mx.get("sessiz_oran_asildi")
               and not mx.get("olu_final_asildi")
               and (am.get("dengeli") if am.get("olculdu") else True)),
          f"sessiz_asildi={mx.get('sessiz_oran_asildi')} "
          f"ambans_dengeli={am.get('dengeli')}",
          olculdu=bool(mx.get("olculdu")))

    olculen = [b for b in bilesenler.values() if b["olculdu"]]
    toplam_agirlik = sum(b["agirlik"] for b in olculen)
    kazanilan = sum(b["puan"] or 0 for b in olculen)
    return {
        "olculdu": bool(olculen),
        "puan": (round(100.0 * kazanilan / toplam_agirlik, 1)
                 if toplam_agirlik else None),
        "kazanilan": round(kazanilan, 2),
        "olculen_agirlik": toplam_agirlik,
        "olculemeyen": [a for a, b in bilesenler.items() if not b["olculdu"]],
        "bilesenler": bilesenler,
        "not": ("olculen kusur bilesenlerinin agirlikli birlesimi; "
                "izleyici arastirmasi DEGILDIR"),
    }


# ═════════════════════════ KAPSAM OZETI ═════════════════════════════════

def kapsam_ozeti() -> dict:
    """Bu modulun NE OLCTUGU sayilabilir olsun — "her seyi olcuyoruz" yok."""
    return {
        "sema_surum": SEMA_SURUM,
        "olcum": 13,
        "olcum_adlari": ["baslik_olcusu", "kelime_ortasi_kesik",
                         "medya_tekrari", "ritim_olcusu",
                         "ambans_duyulabilirligi", "miks_olcusu",
                         "guvenli_alan_olcusu", "yazi_cakismasi",
                         "altyazi_kupleri", "optik_hareket_olcusu",
                         "motion_grammar_olcusu", "izleyici_kalite_puani",
                         "kenar_siyahligi_olcusu"],
        "render_sabiti": 7,
        "enjekte_edilen_okuyucu": 1,
        "esik": {
            "benzerlik": BENZERLIK_ESIGI,
            "sabit_blok_sn": SABIT_BLOK_ESIGI_SN,
            "anlatim_sapma": ANLATIM_SAPMA_ESIGI,
            "olu_final_sn": OLU_FINAL_ESIGI_SN,
            "sessiz_oran": SESSIZ_ORAN_TAVANI,
            "duyulabilir_fark_db": DUYULABILIR_FARK_DB,
            "bastirma_fark_db": BASTIRMA_FARK_DB,
            "altyazi_maks_satir": ALTYAZI_MAKS_SATIR,
            "altyazi_min_sn": ALTYAZI_MIN_SN,
            "altyazi_maks_cps": ALTYAZI_MAKS_CPS,
            "optik_durgun": OPTIK_DURGUN_ESIGI,
            "optik_durgun_warn_sn": OPTIK_DURGUN_WARN_SN,
            "optik_durgun_fail_sn": OPTIK_DURGUN_FAIL_SN,
            "optik_asiri": OPTIK_ASIRI_ESIGI,
            "kenar_siyah": KENAR_SIYAH_ESIGI,
            "hareket_penceresi": HAREKET_PENCERESI,
        },
        # Kapsam DISI oldugunu acikca yaz — sonraki atomlarin isi.
        # ⚠ I-16'da altyazi, kaynak kunyesi ve 1080p KAPSAMA ALINDI; listeden
        # cikarildilar. Kalanlar hala kapsam disidir.
        "kapsam_disi": ["hareketli video B-roll", "web'den medya bulma",
                        "gercek parallax katman gorselleri"],
    }
