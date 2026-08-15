#!/usr/bin/env python3
"""FAZ K-2 — ARKA PLAN UGULTU/RUZGAR KAPISI (saf karar mantigi).

⚠ BU MODUL MEDYA ACMAZ, FFMPEG CALISTIRMAZ, DOSYA YAZMAZ. Butun olcumler
SAYI olarak DISARIDAN (remote worker) verilir — `benzerlik_okuyucu` /
`enerji_okuyucu` / `kare_okuyucu` ile ayni enjeksiyon desenidir. Bu sayede
karar mantigi yerelde MEDYASIZ test edilebilir.

⚠ EMIN DEGILSEN TEMIZ ICERIGI FAIL ETME. Her hukum bir GUVEN ARALIGI ile
verilir: olcum belirsizligi esigi kesiyorsa sonuc `supheli` olur ve
FAIL DEGIL WARN uretilir.

── DETERMINISTIK AKIS ──
    1. `gurultu_olcusu(...)`        : oznitelikleri karara baglar
    2. `filtre_profili_oner(...)`   : GUVENLI filtre zinciri (konusma bandina
                                      DOKUNMAZ); remote worker uygular
    3. `temizleme_dogrula(...)`     : temizleme SONRASI konusma netligi /
                                      spektral konusma bandi gerilemesi
    4. `gurultu_karari(...)`        : 1-3'u birlestirir; temizlenemiyorsa FAIL

── KAYNAK VIDEO SESI ──
`KAYNAK_SES_POLITIKASI` MUTLAK SIFIRDIR ve `kaynak_ses_sozlesmesi()` ile
kilitlenir. Kaynak sesi hicbir kosulda mikse girmez.
"""
from __future__ import annotations

from typing import Optional

SEMA_SURUM = "1.0.0"

# ═══════════════ KAYNAK VIDEO SESI: MUTLAK SIFIR ════════════════════════
# ⚠ Tartisilabilir bir ayar DEGILDIR. Harici klibin kendi sesi (ruzgar,
# trafik, konusma, muzik) mikse GIREMEZ; miks yalnizca VidRush anlatim +
# muzik + ambiyans + SFX'ten olusur.
KAYNAK_SES_POLITIKASI = "sifir"
# ⚠ FAZ Y-17 (`Y17-KAYNAK-SES-TOTOLOJI`): BOS STRING KABUL KUMESINDEN
# CIKARILDI. Bos beyan "sorun yok" DEGIL, "beyan yok" demektir; kumede
# kaldigi surece `KAYNAK-SES-SIZINTI` kapisi ERISILEMEZ oluyordu.
KAYNAK_SES_KABUL_EDILEN = ("yok", "sifir", "mute", "muted")


# ═══════════════ ESIKLER ════════════════════════════════════════════════
# ⚠ TURETILMIS: `kalite_kapisi.DUYULABILIR_FARK_DB` (30 dB) zaten "bu kadar
# altta kalan yatak sesi pratikte DUYULMAZ" diyor. Ayni esigin diger yuzu:
# gurultu tabani anlatimin 30 dB'den FAZLA altindaysa DUYULMAZ -> temizdir.
# Yeni sayi uydurulmadi, MEVCUT sabit ters yonde okundu.
GURULTU_SNR_ESIGI_DB = 30.0

# ⚠ BEYAN EDILMIS TASARIM ESIKLERI (dinleme testi DEGIL; `DUYULABILIR_FARK_DB`
# ile ayni durustluk etiketi). Hepsi parametre olarak disari acildi ki
# olculdukce kalibre edilebilsin.
SUREKLILIK_ESIGI = 0.80          # konusma disi karelerin >=%80'i ayni bantta
SPEKTRAL_DUZLUK_ESIGI = 0.35     # genis bantli (hiss/wind) izi
RUMBLE_BANT_ORANI_ESIGI = 0.30   # <120 Hz enerji payi
HISS_BANT_ORANI_ESIGI = 0.25     # >6 kHz enerji payi

# Olcum belirsizligi verilmezse varsayilan yarim-genislik (dB).
VARSAYILAN_BELIRSIZLIK_DB = 1.5

# ── TEMIZLEME SINIRLARI ──
# ⚠ KONUSMA NETLIGINI BOZAN DENOISE UYGULANMAZ. Konusma bandi 300-3400 Hz
# hicbir filtreyle zayiflatilmaz; temizleme SONRASI bu bantta izin verilen
# EN BUYUK gerileme asagidaki tavandir. Asilirsa filtre REDDEDILIR.
KONUSMA_BANDI_HZ = (300, 3400)
KONUSMA_GERILEME_TAVANI_DB = 1.0
ASR_GERILEME_TAVANI = 0.02       # ASR guveni bu kadardan fazla dusemez
# Rumble icin guvenli yuksek-geciren kesim: yetiskin konusma temel frekansi
# ~85 Hz'in ALTINDA kalir.
GUVENLI_HIGHPASS_HZ = 80
# Genis bantli gurultu icin izin verilen EN BUYUK bastirma (dB). Agresif
# denoise konusmayi "sualti" yapar; tavan bilerek DUSUK.
MAKS_GENIS_BANT_BASTIRMA_DB = 6.0


def _sayi(v, vars_=None):
    try:
        return float(v)
    except (TypeError, ValueError):
        return vars_


def kaynak_ses_sozlesmesi(sahneler) -> dict:
    """Her VIDEO cekiminin kaynak sesi SIFIR olarak beyan edilmis mi?

    ⚠ Bu bir tercih degil SOZLESMEDIR: ihlal `KALITE-KAYNAK-SES-SIZINTI`.
    """
    try:
        liste = [s for s in (sahneler or []) if isinstance(s, dict)]
    except TypeError:
        return {"olculdu": False, "neden": "GIRDI-BOZUK"}
    ihlal = []
    video_n = 0
    for i, s in enumerate(liste):
        if str(s.get("medya_turu") or "").lower() != "video":
            continue
        video_n += 1
        kanal = str(s.get("ses_kanali") or "").strip().lower()
        if kanal not in KAYNAK_SES_KABUL_EDILEN:
            ihlal.append({"indeks": i, "beat_id": str(s.get("beat_id") or ""),
                          "ses_kanali": kanal})
    return {"olculdu": True, "politika": KAYNAK_SES_POLITIKASI,
            "video_cekim": video_n, "ihlal": ihlal, "temiz": not ihlal}


def gurultu_olcusu(*, anlatim_lufs=None, konusma_disi_lufs=None,
                   sureklilik_orani=None, spektral_duzluk=None,
                   dusuk_frekans_orani=None, yuksek_frekans_orani=None,
                   belirsizlik_db: Optional[float] = None,
                   snr_esigi_db: float = GURULTU_SNR_ESIGI_DB,
                   sureklilik_esigi: float = SUREKLILIK_ESIGI,
                   duzluk_esigi: float = SPEKTRAL_DUZLUK_ESIGI,
                   rumble_esigi: float = RUMBLE_BANT_ORANI_ESIGI,
                   hiss_esigi: float = HISS_BANT_ORANI_ESIGI) -> dict:
    """TTS DISI SUREKLI gurultu var mi? (hiss / rumble / wind-like)

    ⚠ Butun girdiler remote worker'in OLCTUGU SAYILARDIR; bu modul medya
    acmaz. Eksik girdi -> `olculdu=False` ve HUKUM YOK ("temiz" DENMEZ).

    Karar: gurultu ancak (a) DUYULABILIR seviyede (SNR esigin altinda),
    (b) SUREKLI ve (c) genis bantli / rumble / hiss izi tasiyorsa vardir.
    Ucu birden gerekir — tek basina dusuk SNR bir muzik yataginda da olur.
    """
    a = _sayi(anlatim_lufs)
    n = _sayi(konusma_disi_lufs)
    sur = _sayi(sureklilik_orani)
    if a is None or n is None or sur is None:
        return {"olculdu": False, "neden": "OLCUM-EKSIK",
                "eksik": [k for k, v in (("anlatim_lufs", a),
                                         ("konusma_disi_lufs", n),
                                         ("sureklilik_orani", sur))
                          if v is None]}
    duz = _sayi(spektral_duzluk, 0.0)
    dfo = _sayi(dusuk_frekans_orani, 0.0)
    yfo = _sayi(yuksek_frekans_orani, 0.0)
    bel = _sayi(belirsizlik_db, VARSAYILAN_BELIRSIZLIK_DB)
    if bel is None or bel < 0:
        bel = VARSAYILAN_BELIRSIZLIK_DB

    snr = a - n                       # LUFS farki = konusma / gurultu tabani
    esik = _sayi(snr_esigi_db, GURULTU_SNR_ESIGI_DB)
    # ── GUVEN ARALIGI ──
    alt, ust = snr - bel, snr + bel
    surekli = sur >= _sayi(sureklilik_esigi, SUREKLILIK_ESIGI)
    izler = []
    if duz >= _sayi(duzluk_esigi, SPEKTRAL_DUZLUK_ESIGI):
        izler.append("genis-bant")
    if dfo >= _sayi(rumble_esigi, RUMBLE_BANT_ORANI_ESIGI):
        izler.append("rumble")
    if yfo >= _sayi(hiss_esigi, HISS_BANT_ORANI_ESIGI):
        izler.append("hiss")

    if not surekli or not izler:
        seviye = "temiz"             # sureksiz ya da izsiz -> gurultu DEGIL
    elif ust < esik:
        seviye = "gurultu"           # aralik TAMAMEN esigin altinda
    elif alt >= esik:
        seviye = "temiz"             # aralik TAMAMEN esigin ustunde
    else:
        seviye = "supheli"           # ⚠ aralik esigi KESIYOR -> FAIL YOK
    return {"olculdu": True, "seviye": seviye, "snr_db": round(snr, 3),
            "snr_alt": round(alt, 3), "snr_ust": round(ust, 3),
            "esik_db": esik, "belirsizlik_db": bel,
            "surekli": surekli, "sureklilik_orani": round(sur, 4),
            "izler": izler,
            "spektral_duzluk": round(duz, 4),
            "dusuk_frekans_orani": round(dfo, 4),
            "yuksek_frekans_orani": round(yfo, 4)}


def filtre_profili_oner(olcum: dict, *,
                        maks_bastirma_db: float = MAKS_GENIS_BANT_BASTIRMA_DB
                        ) -> dict:
    """Gurultu izlerine gore GUVENLI filtre zinciri (worker uygular).

    ⚠ KONUSMA BANDINA DOKUNULMAZ (300-3400 Hz). Agresif denoise YOK:
    genis bantli bastirma `maks_bastirma_db` ile TAVANLI. Zincir
    DETERMINISTIKTIR — ayni olcum ayni zinciri verir.
    """
    if not isinstance(olcum, dict) or not olcum.get("olculdu"):
        return {"onerildi": False, "neden": "OLCUM-YOK", "adimlar": []}
    if olcum.get("seviye") == "temiz":
        return {"onerildi": False, "neden": "GURULTU-YOK", "adimlar": []}
    izler = list(olcum.get("izler") or [])
    adimlar = []
    if "rumble" in izler:
        adimlar.append({"ad": "highpass", "parametre": {
            "f": GUVENLI_HIGHPASS_HZ, "poles": 2},
            "gerekce": "rumble; kesim konusma temel frekansinin ALTINDA"})
    if "hiss" in izler or "genis-bant" in izler:
        adimlar.append({"ad": "afftdn", "parametre": {
            "nr": round(min(float(maks_bastirma_db),
                            MAKS_GENIS_BANT_BASTIRMA_DB), 3),
            "nt": "w"},
            "gerekce": "genis bantli gurultu; bastirma TAVANLI"})
    return {"onerildi": bool(adimlar), "adimlar": adimlar,
            "konusma_bandi_hz": list(KONUSMA_BANDI_HZ),
            "konusma_bandina_dokunmaz": True,
            "maks_bastirma_db": min(float(maks_bastirma_db),
                                    MAKS_GENIS_BANT_BASTIRMA_DB),
            "neden": "GURULTU-IZI:" + ",".join(izler)}


def temizleme_dogrula(*, once: dict, sonra: dict,
                      konusma_bandi_lufs_once=None,
                      konusma_bandi_lufs_sonra=None,
                      asr_guven_once=None, asr_guven_sonra=None,
                      gerileme_tavani_db: float = KONUSMA_GERILEME_TAVANI_DB,
                      asr_tavani: float = ASR_GERILEME_TAVANI) -> dict:
    """Temizleme KONUSMAYI bozdu mu, gurultuyu GERCEKTEN dusurdu mu?

    ⚠ Konusma bandi gerilemesi tavani asarsa filtre REDDEDILIR — netligi
    bozan denoise UYGULANMAZ, gurultu kalsa bile.
    """
    kb_o = _sayi(konusma_bandi_lufs_once)
    kb_s = _sayi(konusma_bandi_lufs_sonra)
    gerileme = None
    if kb_o is not None and kb_s is not None:
        gerileme = kb_o - kb_s            # pozitif = konusma ZAYIFLADI
    asr_o, asr_s = _sayi(asr_guven_once), _sayi(asr_guven_sonra)
    asr_dusus = (asr_o - asr_s) if (asr_o is not None
                                    and asr_s is not None) else None

    tavan = _sayi(gerileme_tavani_db, KONUSMA_GERILEME_TAVANI_DB)
    at = _sayi(asr_tavani, ASR_GERILEME_TAVANI)
    netlik_bozuldu = ((gerileme is not None and gerileme > tavan)
                      or (asr_dusus is not None and asr_dusus > at))
    olculebildi = gerileme is not None or asr_dusus is not None

    sonra_seviye = (sonra or {}).get("seviye") if isinstance(sonra, dict) \
        else None
    gurultu_gitti = sonra_seviye in ("temiz", "supheli")
    return {"olculdu": bool(olculebildi and isinstance(sonra, dict)
                            and sonra.get("olculdu")),
            "konusma_gerilemesi_db": (None if gerileme is None
                                      else round(gerileme, 3)),
            "gerileme_tavani_db": tavan,
            "asr_dususu": None if asr_dusus is None else round(asr_dusus, 4),
            "asr_tavani": at,
            "netlik_bozuldu": bool(netlik_bozuldu),
            "gurultu_gitti": bool(gurultu_gitti),
            "once_seviye": (once or {}).get("seviye")
            if isinstance(once, dict) else None,
            "sonra_seviye": sonra_seviye,
            # ⚠ Netligi bozan filtre KABUL EDILMEZ.
            "filtre_kabul": bool(gurultu_gitti and not netlik_bozuldu)}


def gurultu_karari(*, olcum: dict, dogrulama: Optional[dict] = None) -> dict:
    """Nihai hukum: temiz / warn(supheli) / FAIL(temizlenemedi).

    ⚠ FAIL yalnizca (a) gurultu GUVEN ARALIGIYLA kesin ve (b) guvenli
    temizleme YA denenmedi YA da konusmayi bozmadan gideremedi ise verilir.
    """
    if not isinstance(olcum, dict) or not olcum.get("olculdu"):
        return {"olculdu": False, "karar": "OLCULEMEDI",
                "kod": "", "seviye": "",
                "neden": (olcum or {}).get("neden", "OLCUM-YOK")}
    sev = olcum.get("seviye")
    if sev == "temiz":
        return {"olculdu": True, "karar": "TEMIZ", "kod": "", "seviye": "",
                "neden": ""}
    if sev == "supheli":
        # ⚠ EMIN DEGILSEN TEMIZ ICERIGI FAIL ETME.
        return {"olculdu": True, "karar": "SUPHELI",
                "kod": "KALITE-SES-GURULTU", "seviye": "warn",
                "neden": (f"gurultu SNR guven araligi esigi kesiyor "
                          f"({olcum['snr_alt']}..{olcum['snr_ust']} dB, "
                          f"esik {olcum['esik_db']}) — hukum verilmedi")}
    if isinstance(dogrulama, dict) and dogrulama.get("filtre_kabul"):
        return {"olculdu": True, "karar": "TEMIZLENDI", "kod": "",
                "seviye": "", "neden": ""}
    if isinstance(dogrulama, dict) and dogrulama.get("netlik_bozuldu"):
        neden = ("guvenli filtre gurultuyu ancak KONUSMA NETLIGINI BOZARAK "
                 "dusuruyor -> filtre REDDEDILDI")
    elif isinstance(dogrulama, dict) and dogrulama.get("olculdu"):
        neden = "guvenli filtre uygulandi ama gurultu HALA esigin altinda"
    else:
        neden = "surekli arka plan gurultusu var; temizleme DOGRULANMADI"
    return {"olculdu": True, "karar": "FAIL",
            "kod": "KALITE-SES-GURULTU", "seviye": "fail",
            "neden": f"{neden} (izler: {','.join(olcum.get('izler') or [])})"}


def kapsam_ozeti() -> dict:
    return {
        "sema_surum": SEMA_SURUM,
        "medya_acar": False, "ffmpeg_calistirir": False,
        "olcum_enjekte_edilir": True,
        "kaynak_ses_politikasi": KAYNAK_SES_POLITIKASI,
        "kodlar": ["KALITE-SES-GURULTU", "KALITE-KAYNAK-SES-SIZINTI"],
        "esikler": {
            "snr_db": GURULTU_SNR_ESIGI_DB,
            "sureklilik": SUREKLILIK_ESIGI,
            "spektral_duzluk": SPEKTRAL_DUZLUK_ESIGI,
            "rumble_bant_orani": RUMBLE_BANT_ORANI_ESIGI,
            "hiss_bant_orani": HISS_BANT_ORANI_ESIGI,
            "konusma_gerileme_tavani_db": KONUSMA_GERILEME_TAVANI_DB,
            "maks_genis_bant_bastirma_db": MAKS_GENIS_BANT_BASTIRMA_DB,
        },
        "esik_kaynagi": {
            "snr_db": "TURETILMIS — kalite_kapisi.DUYULABILIR_FARK_DB (30 dB)",
            "digerleri": ("BEYAN EDILMIS tasarim esigi (dinleme testi DEGIL); "
                          "parametre olarak disari acildi"),
        },
        "konusma_bandi_hz": list(KONUSMA_BANDI_HZ),
        "agresif_denoise": False,
    }
