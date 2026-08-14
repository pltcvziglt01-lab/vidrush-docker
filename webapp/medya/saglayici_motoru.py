#!/usr/bin/env python3
"""FAZ R-1b — TENANT'A OZEL MEDYA EDINIM PROVIDER ZINCIRI.

Magnific YALNIZ bir ayar/UI kaydi DEGILDIR: planlayicinin urettigi semantik
shot isteginden timeline'a kadar giden zincirin BIR HALKASIDIR.

    planlayici -> provider registry -> job-scope token -> MCP capability
    discovery -> edinim -> object storage -> ffprobe -> provenance -> timeline

⚠ BU MODUL AG ACMAZ, MEDYA ACMAZ, SIFRELEME UYDURMAZ. Butun dis dunya
enjekte edilir (`mcp_cagirici`, `sifre_cozucu`, `olcer`, `indirici`) — mevcut
okuyucu-enjeksiyonu deseninin aynisi. Bu sayede zincir MEDYASIZ test edilir.

⚠ UYDURMA YOK: saglayici stok ARAMA yetenegi sunmuyorsa "arar gibi yapilmaz".
Sirasiyla generate/transform denenir, o da yoksa UCRETSIZ STOK fallback'e
gecilir ve raporda `provider_used` + `fallback_reason` GORUNUR.

⚠ TENANT TOKENI ISTEMCIYE CIKMAZ: `baglanti_ozeti()` token'i hicbir bicimde
dondurmez; yalniz durum/kredi/model alanlarini verir.
"""
from __future__ import annotations

from typing import Callable, Optional

SEMA_SURUM = "1.0.0"

# ── MCP yetenek adlari (capability discovery sonucunda beklenenler) ──
YETENEK_ARAMA = "video.search"
YETENEK_URETIM = "video.generate"
YETENEK_DONUSUM = "video.transform"
YETENEK_BAKIYE = "account.balance"

# Kullanicinin UI'da secebilecegi kaynak tercihi.
TERCIH_OTOMATIK = "otomatik"
TERCIH_MAGNIFIC = "magnific"
TERCIH_UCRETSIZ = "ucretsiz"
TERCIHLER = (TERCIH_OTOMATIK, TERCIH_MAGNIFIC, TERCIH_UCRETSIZ)

UCRETSIZ_SAGLAYICI = "wikimedia"

# ⚠ K-2 / J-5a sozlesmeleri BU ZINCIRDE DE gecerlidir.
KAYNAK_SES_POLITIKASI = "sifir"
KAYNAK_BASINA_TAVAN_SN = 8.0


def _s(v) -> str:
    return str(v or "").strip()


def _f(v, vars_=0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return vars_


# ═══════════════ 1) PLANLAYICI CIKTISI: SHOT ISTEGI ═════════════════════

def shot_istegi(*, scene_id: str, sorgu: str, negatifler=None,
                oran: str = "16:9", sure_sn: float = 0.0,
                kalite_hedefi: str = "1080p") -> dict:
    """Planlayicinin her sahne icin urettigi SEMANTIK istek.

    ⚠ `sure_sn` bir TALEPTIR; kaynak basina TAVAN ayrica uygulanir.
    """
    return {"scene_id": _s(scene_id), "sorgu": _s(sorgu),
            "negatifler": [_s(n) for n in (negatifler or []) if _s(n)],
            "oran": _s(oran) or "16:9",
            "sure_sn": min(_f(sure_sn), KAYNAK_BASINA_TAVAN_SN),
            "kalite_hedefi": _s(kalite_hedefi) or "1080p"}


# ═══════════════ 2) TENANT BAGLANTISI + REGISTRY ════════════════════════

def baglanti_ozeti(baglanti: dict) -> dict:
    """UI'ya donen GUVENLI ozet. ⚠ TOKEN HICBIR BICIMDE DONMEZ."""
    b = baglanti if isinstance(baglanti, dict) else {}
    return {"saglayici": _s(b.get("saglayici")),
            "aktif": bool(b.get("aktif")),
            "onayli": bool(b.get("onayli")),
            "kredi_onayi": bool(b.get("kredi_onayi")),
            "model_secimi": _s(b.get("model_secimi")) or "auto",
            "bakiye": b.get("bakiye"),
            "token_var": bool(b.get("sifreli_token")),
            # ⚠ token / sifreli_token ASLA burada DONMEZ.
            }


def kullanilabilir_mi(baglanti: dict) -> dict:
    """Baglanti gercekten kullanilabilir mi? Eksikse NEDENI ile soyler."""
    b = baglanti if isinstance(baglanti, dict) else {}
    eksik = []
    if not b:
        return {"kullanilabilir": False, "neden": "BAGLANTI-YOK"}
    if not b.get("aktif"):
        eksik.append("aktif-degil")
    if not b.get("onayli"):
        eksik.append("onayli-degil")
    if not b.get("sifreli_token"):
        eksik.append("token-yok")
    if not b.get("kredi_onayi"):
        eksik.append("kredi-onayi-yok")
    return {"kullanilabilir": not eksik,
            "neden": "+".join(eksik) if eksik else ""}


def saglayici_sec(kayit: dict, tenant_id: str, *,
                  tercih: str = TERCIH_OTOMATIK) -> dict:
    """Tenant'in AKTIF ve ONAYLI baglantisini sec; yoksa ucretsiz stok.

    ⚠ Baska tenant'in baglantisi ASLA secilmez (izolasyon).
    """
    t = _s(tenant_id)
    ter = _s(tercih).lower() or TERCIH_OTOMATIK
    if ter not in TERCIHLER:
        ter = TERCIH_OTOMATIK
    b = ((kayit or {}).get(t) or {}) if t else {}
    d = kullanilabilir_mi(b)
    if ter == TERCIH_UCRETSIZ:
        return {"saglayici": UCRETSIZ_SAGLAYICI, "tercih": ter,
                "baglanti": None, "fallback_reason": ""}
    if d["kullanilabilir"]:
        return {"saglayici": _s(b.get("saglayici")) or "magnific",
                "tercih": ter, "baglanti": b, "fallback_reason": ""}
    if ter == TERCIH_MAGNIFIC:
        # ⚠ Kullanici ACIKCA Magnific istedi ama baglanti kullanilamiyor.
        # Sessizce baska saglayiciya GECILMEZ; neden GORUNUR olur.
        return {"saglayici": UCRETSIZ_SAGLAYICI, "tercih": ter,
                "baglanti": None,
                "fallback_reason": f"MAGNIFIC-KULLANILAMIYOR:{d['neden']}"}
    return {"saglayici": UCRETSIZ_SAGLAYICI, "tercih": ter, "baglanti": None,
            "fallback_reason": f"BAGLANTI-YOK:{d['neden']}"}


# ═══════════════ 3) JOB-SCOPE TOKEN ═════════════════════════════════════

def job_scope_token(baglanti: dict, *, sifre_cozucu: Optional[Callable] = None
                    ) -> dict:
    """Sifreli token'i YALNIZ worker kapsaminda coz.

    ⚠ SIFRELEME UYDURULMAZ: gercek bir cozucu verilmezse token
    KULLANILMAZ ve `hazir=False` doner. Duz metin token KABUL EDILMEZ.
    """
    b = baglanti if isinstance(baglanti, dict) else {}
    sifreli = b.get("sifreli_token")
    if not sifreli:
        return {"hazir": False, "neden": "TOKEN-YOK"}
    if not callable(sifre_cozucu):
        return {"hazir": False, "neden": "SIFRE-COZUCU-YOK"}
    try:
        acik = sifre_cozucu(sifreli)
    except Exception as e:                                    # noqa: BLE001
        return {"hazir": False, "neden": f"COZULEMEDI:{type(e).__name__}"}
    if not _s(acik):
        return {"hazir": False, "neden": "TOKEN-BOS"}
    # ⚠ Token DONDURULUR ama cagiran taraf onu YALNIZ MCP cagrisinda
    # kullanmalidir; `baglanti_ozeti()` onu asla disari vermez.
    return {"hazir": True, "token": acik, "neden": ""}


# ═══════════════ 4) MCP CAPABILITY DISCOVERY ════════════════════════════

def yetenek_kesfi(mcp_cagirici: Optional[Callable], *, token: str = "") -> dict:
    """Saglayicinin GERCEKTEN sundugu yetenekleri ogren.

    ⚠ Varsayim YOK: cagirici yoksa ya da hata verirse yetenek listesi BOS
    kalir ve `olculdu=False` yazilir — "arama vardir" DENMEZ.
    """
    if not callable(mcp_cagirici):
        return {"olculdu": False, "yetenekler": [], "neden": "CAGIRICI-YOK"}
    try:
        ham = mcp_cagirici("capabilities", {"token": token})
    except Exception as e:                                    # noqa: BLE001
        return {"olculdu": False, "yetenekler": [],
                "neden": f"KESIF-HATASI:{type(e).__name__}"}
    liste = []
    if isinstance(ham, dict):
        liste = [_s(x) for x in (ham.get("capabilities") or []) if _s(x)]
    elif isinstance(ham, (list, tuple)):
        liste = [_s(x) for x in ham if _s(x)]
    return {"olculdu": True, "yetenekler": liste, "neden": ""}


def yol_sec(yetenekler: list) -> dict:
    """Hangi yolla medya alinacak? ⚠ UYDURMA YOK.

    Sira: ARAMA -> URETIM -> DONUSUM -> (hicbiri yoksa) UCRETSIZ FALLBACK.
    """
    y = set(yetenekler or [])
    if YETENEK_ARAMA in y:
        return {"yol": YETENEK_ARAMA, "fallback_reason": ""}
    if YETENEK_URETIM in y:
        return {"yol": YETENEK_URETIM,
                "fallback_reason": "STOK-ARAMA-YETENEGI-YOK"}
    if YETENEK_DONUSUM in y:
        return {"yol": YETENEK_DONUSUM,
                "fallback_reason": "STOK-ARAMA-VE-URETIM-YOK"}
    return {"yol": "", "fallback_reason": "UYGUN-YETENEK-YOK"}


# ═══════════════ 5) PROVENANCE ══════════════════════════════════════════

def provenance_kur(*, saglayici: str, yol: str, istek: dict, ham: dict,
                   olcum: dict, job_id: str = "",
                   tenant_id: str = "") -> dict:
    """license / model / credit / job metadata — EKSIK ALAN UYDURULMAZ."""
    h = ham if isinstance(ham, dict) else {}
    model = _s(h.get("model"))
    if not model or model.lower() == "auto":
        # ⚠ Auto mod model adini GARANTI ETMEZ; provenance'a DURUSTCE yazilir.
        model = "model_unknown/auto"
    return {
        "saglayici": _s(saglayici), "edinim_yolu": _s(yol),
        "scene_id": _s(istek.get("scene_id")),
        "sorgu": _s(istek.get("sorgu")),
        "baslik": _s(h.get("baslik")),
        "kaynak_url": _s(h.get("orijinal_url") or h.get("kaynak_url")),
        "lisans": _s(h.get("lisans")),
        "lisans_kaydi": _s(h.get("lisans_kaydi")),
        "eser_sahibi": _s(h.get("eser_sahibi")),
        "model": model,
        "kredi_tuketildi": bool(h.get("kredi_tuketildi")),
        "job_id": _s(job_id), "tenant_id": _s(tenant_id),
        "teknik": olcum if isinstance(olcum, dict) else {},
        "ses_kanali": KAYNAK_SES_POLITIKASI,
    }


# ═══════════════ 6) SIRALAMA + TIMELINE YERLESIMI ═══════════════════════

def aday_puani(aday: dict, istek: dict) -> dict:
    """Semantik uygunluk + GERCEK VIDEO tercihi + teknik kalite.

    ⚠ Tekrar cezasi cagiran tarafta uygulanir (`timeline_yerlestir`), cunku
    tekrar bir ADAY ozelligi degil DIZILIM ozelligidir.
    """
    a = aday if isinstance(aday, dict) else {}
    sorgu = set(_s(istek.get("sorgu")).lower().split())
    baslik = set(_s(a.get("baslik")).lower().replace("-", " ").split())
    ortusme = len(sorgu & baslik)
    neg = [n for n in (istek.get("negatifler") or [])
           if _s(n).lower() in " ".join(baslik)]
    video_mu = _s(a.get("medya_turu") or a.get("tur")).lower() == "video"
    tek = a.get("teknik") if isinstance(a.get("teknik"), dict) else {}
    piksel = _f(tek.get("genislik")) * _f(tek.get("yukseklik"))
    return {
        "semantik": ortusme,
        "negatif_ihlali": len(neg),
        "gercek_video": bool(video_mu),
        "piksel": piksel,
        "bitrate": _f(tek.get("bitrate")),
        # ⚠ Negatif ihlali olan aday ELENIR (puanla gizlenmez).
        "elendi": bool(neg),
    }


def timeline_yerlestir(adaylar: list, istekler: list) -> dict:
    """Her shot istegine EN IYI adayi ata; tekrar ve kaynak tavanini uygula.

    ⚠ Ayni kaynak toplam `KAYNAK_BASINA_TAVAN_SN` saniyeyi ASAMAZ (J-5b
    kullanici sarti). Asan aday atlanir, neden RAPORLANIR.
    """
    kullanim: dict = {}
    yerlesim, atlanan = [], []
    for istek in (istekler or []):
        en_iyi, en_puan = None, None
        for a in (adaylar or []):
            if _s(a.get("scene_id")) not in ("", _s(istek.get("scene_id"))):
                continue
            p = aday_puani(a, istek)
            if p["elendi"]:
                atlanan.append({"scene_id": istek.get("scene_id"),
                                "baslik": _s(a.get("baslik")),
                                "neden": "NEGATIF-IHLALI"})
                continue
            kimlik = _s(a.get("asset_id")) or _s(a.get("baslik"))
            kalan = KAYNAK_BASINA_TAVAN_SN - kullanim.get(kimlik, 0.0)
            if kalan <= 0:
                atlanan.append({"scene_id": istek.get("scene_id"),
                                "baslik": _s(a.get("baslik")),
                                "neden": "KAYNAK-TAVANI-DOLDU"})
                continue
            anahtar = (p["semantik"], p["gercek_video"], p["piksel"],
                       p["bitrate"])
            if en_puan is None or anahtar > en_puan:
                en_iyi, en_puan = a, anahtar
        if en_iyi is None:
            yerlesim.append({"scene_id": istek.get("scene_id"),
                             "aday": None, "neden": "ADAY-YOK"})
            continue
        kimlik = _s(en_iyi.get("asset_id")) or _s(en_iyi.get("baslik"))
        sure = min(_f(istek.get("sure_sn")),
                   KAYNAK_BASINA_TAVAN_SN - kullanim.get(kimlik, 0.0))
        kullanim[kimlik] = kullanim.get(kimlik, 0.0) + sure
        yerlesim.append({"scene_id": istek.get("scene_id"), "aday": en_iyi,
                         "sure_sn": round(sure, 3),
                         "ses_kanali": KAYNAK_SES_POLITIKASI, "neden": ""})
    return {"yerlesim": yerlesim, "atlanan": atlanan,
            "kaynak_kullanimi": {k: round(v, 3) for k, v in kullanim.items()},
            "kaynak_tavani_sn": KAYNAK_BASINA_TAVAN_SN}


# ═══════════════ 7) UCTAN UCA ZINCIR ════════════════════════════════════

def edin(*, kayit: dict, tenant_id: str, job_id: str, istekler: list,
         tercih: str = TERCIH_OTOMATIK,
         mcp_cagirici: Optional[Callable] = None,
         sifre_cozucu: Optional[Callable] = None,
         ucretsiz_arayici: Optional[Callable] = None,
         olcer: Optional[Callable] = None) -> dict:
    """Zincirin tamami. Disari cikan her sey ENJEKTE edilir.

    Doner: {provider_used, fallback_reason, yetenekler, adaylar,
            provenance, timeline}
    """
    sec = saglayici_sec(kayit, tenant_id, tercih=tercih)
    provider = sec["saglayici"]
    fallback = sec["fallback_reason"]
    yetenekler: list = []
    yol = ""

    if sec.get("baglanti"):
        tok = job_scope_token(sec["baglanti"], sifre_cozucu=sifre_cozucu)
        if not tok["hazir"]:
            provider, fallback = UCRETSIZ_SAGLAYICI, f"TOKEN:{tok['neden']}"
        else:
            kesif = yetenek_kesfi(mcp_cagirici, token=tok["token"])
            yetenekler = kesif["yetenekler"]
            if not kesif["olculdu"]:
                provider, fallback = (UCRETSIZ_SAGLAYICI,
                                      f"KESIF:{kesif['neden']}")
            else:
                secim = yol_sec(yetenekler)
                yol = secim["yol"]
                if not yol:
                    provider = UCRETSIZ_SAGLAYICI
                    fallback = secim["fallback_reason"]
                elif secim["fallback_reason"]:
                    fallback = secim["fallback_reason"]   # yol degisti, saglayici AYNI

    adaylar, prov = [], []
    for istek in (istekler or []):
        ham_liste = []
        if provider != UCRETSIZ_SAGLAYICI and callable(mcp_cagirici) and yol:
            try:
                cevap = mcp_cagirici(yol, {"istek": istek})
                ham_liste = list((cevap or {}).get("adaylar") or [])
            except Exception as e:                            # noqa: BLE001
                fallback = fallback or f"CAGRI-HATASI:{type(e).__name__}"
                ham_liste = []
        if not ham_liste:
            if provider != UCRETSIZ_SAGLAYICI:
                fallback = fallback or "SAGLAYICI-ADAY-DONDURMEDI"
                provider = UCRETSIZ_SAGLAYICI
            if callable(ucretsiz_arayici):
                try:
                    ham_liste = list(ucretsiz_arayici(istek) or [])
                except Exception as e:                        # noqa: BLE001
                    fallback = fallback or f"UCRETSIZ-HATA:{type(e).__name__}"
                    ham_liste = []
        for h in ham_liste:
            olcum = {}
            if callable(olcer):
                try:
                    olcum = olcer(h) or {}
                except Exception:                             # noqa: BLE001
                    olcum = {}
            aday = dict(h, scene_id=_s(istek.get("scene_id")), teknik=olcum)
            adaylar.append(aday)
            prov.append(provenance_kur(
                saglayici=provider, yol=yol or "ucretsiz-stok", istek=istek,
                ham=h, olcum=olcum, job_id=job_id, tenant_id=tenant_id))

    return {"provider_used": provider, "fallback_reason": fallback,
            "yetenekler": yetenekler, "edinim_yolu": yol or "ucretsiz-stok",
            "adaylar": adaylar, "provenance": prov,
            "timeline": timeline_yerlestir(adaylar, istekler)}


def kapsam_ozeti() -> dict:
    return {
        "sema_surum": SEMA_SURUM,
        "aga_cikar": False, "medya_acar": False,
        "sifreleme_uydurur": False,
        "duz_metin_token_kabul": False,
        "token_istemciye_cikar": False,
        "tercihler": list(TERCIHLER),
        "yetenekler": [YETENEK_ARAMA, YETENEK_URETIM, YETENEK_DONUSUM,
                       YETENEK_BAKIYE],
        "ucretsiz_fallback": UCRETSIZ_SAGLAYICI,
        "kaynak_ses_politikasi": KAYNAK_SES_POLITIKASI,
        "kaynak_basina_tavan_sn": KAYNAK_BASINA_TAVAN_SN,
        "not": ("saglayici stok arama sunmuyorsa UYDURULMAZ: uretim/donusum "
                "denenir, o da yoksa ucretsiz stok fallback; rapor "
                "provider_used + fallback_reason tasir"),
    }
