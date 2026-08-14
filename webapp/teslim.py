#!/usr/bin/env python3
"""FAZ R-1d-a — TESLIM ATOMU: ZINCIRI UCTAN UCA BAGLAR.

⚠ NEDEN VAR: R-1a (imzali URL), R-1b (tenant provider zinciri), R-1c-a
(zorunlu oturum) ve R-1c-b (son-3 kutuphane) HEPSI YAZILDI ama hicbiri
GERCEK ISTEK YOLUNA BAGLI DEGILDI. `server.py` bunlarin ucunu de import
etmiyordu: `/api/generate` hala serbest `session` string'i aliyordu,
`/ciktilar/` imzayi dogruluyordu ama TENANT'a bakmiyordu, kutuphane hicbir
zaman doldurulmuyordu. Yani moduller vardi, TESLIM YOKTU.

Bu modul o bosluktur: **karar mantigi**, mevcut queue/render/storage hatti
YENIDEN YAZILMADAN.

── ZINCIR (sirali, fail-closed) ──
    oturum -> metin -> plan -> saglayici(R-1b) -> uzak_tts_render
    -> pre_qa -> post_qa -> depolama -> imzali_url -> kutuphane(R-1c-b)

⚠ HER HALKA KANIT ISTER. Bir halkanin kaniti yoksa "muhtemelen olmustur"
DENMEZ: `tamam=False` yazilir ve TESLIM EDILMEZ. Teslim edilmeyen is
kutuphaneye GIRMEZ ve "kabul edilmis video" SAYILMAZ.

⚠ BU MODUL AG ACMAZ, MEDYA ACMAZ, DOSYA SILMEZ, RENDER ETMEZ. Butun dis
dunya enjekte edilir (`imzalayici`, `dosya_var_mi`, `zaman`) — repodaki
okuyucu-enjeksiyonu deseninin aynisi.
"""
from __future__ import annotations

import os
import secrets
from typing import Callable, Optional

import kimlik
import kutuphane
import imzali_url
from medya import saglayici_motoru

SEMA_SURUM = "1.0.0"

# ── Oturum imza anahtari (imzali_url ile AYNI desen; AYRI anahtar) ──
ENV_ADI = "OTURUM_ANAHTARI"
ANAHTAR_DOSYA_ADI = ".oturum_anahtari"
_ANAHTAR: Optional[bytes] = None

# ⚠ Zincirin halkalari. Sira ONEMLI: sonraki halka oncekinin kanitina dayanir.
ZINCIR = (
    ("oturum", "zorunlu giris + tenant guard (R-1c-a)"),
    ("metin", "kullanici metni"),
    ("plan", "senaryo plani (sahneler)"),
    ("saglayici", "tenant provider registry (R-1b)"),
    ("uzak_tts_render", "uzak seslendirme + render"),
    ("pre_qa", "PRE-QA (render oncesi kalite kapisi)"),
    ("post_qa", "POST-QA (render sonrasi olcum)"),
    ("depolama", "object storage (cikti dosyasi)"),
    ("imzali_url", "tenant korumali signed URL (R-1a)"),
    ("kutuphane", "son-3 kabul edilmis video (R-1c-b)"),
)
ZINCIR_ADLARI = tuple(a for a, _ in ZINCIR)

# QA hukmu: kabul edilebilir olanlar. ⚠ `kutuphane` ile AYNI sozlesme.
QA_KABUL = kutuphane.KABUL_QA          # ("PASS", "WARN")


def _s(v) -> str:
    return str(v or "").strip()


# ═══════════════ OTURUM ANAHTARI ════════════════════════════════════════

def anahtar_kur(veri_dizini: str = "", *, uret: bool = True) -> bool:
    """env -> dosya(0600) -> URET. ⚠ Anahtar DONDURULMEZ ve LOGLANMAZ."""
    global _ANAHTAR
    ham = (os.environ.get(ENV_ADI) or "").strip()
    if ham:
        _ANAHTAR = ham.encode("utf-8")
        return True
    if veri_dizini:
        yol = os.path.join(veri_dizini, ANAHTAR_DOSYA_ADI)
        try:
            with open(yol, "rb") as f:
                d = f.read().strip()
            if d:
                _ANAHTAR = d
                return True
        except OSError:
            pass
        if uret:
            yeni = secrets.token_urlsafe(48).encode("ascii")
            try:
                os.makedirs(veri_dizini, exist_ok=True)
                fd = os.open(yol, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
                with os.fdopen(fd, "wb") as f:
                    f.write(yeni)
                _ANAHTAR = yeni
                return True
            except OSError:
                return False
    return False


def hazir() -> bool:
    return bool(_ANAHTAR)


def anahtar() -> bytes:
    return _ANAHTAR or b""


# ═══════════════ 1) OTURUM KAPISI (zorunlu) ═════════════════════════════

def oturum_kapisi(jeton: str, *, simdi: Optional[int] = None) -> dict:
    """Istegi tenant'a bagla. ⚠ FAIL-CLOSED: supheliyse ERISIM YOK.

    Uc ayri sebeple reddeder ve UCUNU DE AYIRT EDER:
      · `OTURUM-ANAHTARI-YOK`  — sunucu imza anahtarini kuramadi
      · `KIMLIK-KDF-YOK`       — guclu parola algoritmasi kurulu degil
      · jeton nedeni           — BICIM-BOZUK / IMZA-GECERSIZ / SURESI-DOLMUS
    """
    if not hazir():
        return {"izin": False, "tenant_id": "", "neden": "OTURUM-ANAHTARI-YOK"}
    if not kimlik.kdf_hazir():
        # ⚠ KDF yoksa giris zaten yapilamaz; acik kalan bir yol BIRAKILMAZ.
        return {"izin": False, "tenant_id": "", "neden": kimlik.KDF_HATA_KODU}
    d = kimlik.tenant_coz(jeton, anahtar=anahtar(), simdi=simdi)
    if not d["yetkili"]:
        return {"izin": False, "tenant_id": "", "neden": d["neden"]}
    return {"izin": True, "tenant_id": d["tenant_id"], "neden": ""}


def erisim_kapisi(kaynak: dict, tenant_id: str) -> dict:
    """Kaynak BU tenant'a mi ait? ⚠ Sahipsiz kayit ERISILEMEZ (R-1c-a)."""
    return kimlik.sahiplik_dogrula(kaynak, tenant_id)


# ═══════════════ 2) SAGLAYICI KARARI (R-1b halkasi) ═════════════════════

def saglayici_karari(baglanti_kayit: dict, tenant_id: str, *,
                     tercih: str = saglayici_motoru.TERCIH_OTOMATIK) -> dict:
    """Bu tenant bu isi HANGI saglayiciyla cekecek?

    ⚠ GERCEK OAuth / KREDI YOK: tenant'in onayli+kredili bir baglantisi
    yoksa (uretimde normal durum) UCRETSIZ STOK'a duser ve `fallback_reason`
    GORUNUR kalir. Sessizce "magnific kullandik" DENMEZ.
    ⚠ Token bu sozluge KOYULMAZ (`baglanti` disari verilmez).
    """
    sec = saglayici_motoru.saglayici_sec(baglanti_kayit or {}, tenant_id,
                                         tercih=tercih)
    return {"provider_used": sec["saglayici"],
            "fallback_reason": sec["fallback_reason"],
            "tercih": sec["tercih"],
            "kredi_tuketildi": bool(sec.get("baglanti")),
            "ucretsiz_fallback":
                sec["saglayici"] == saglayici_motoru.UCRETSIZ_SAGLAYICI}


def is_damgala(kayit: dict, *, tenant_id: str, metin: str = "",
               saglayici: Optional[dict] = None) -> dict:
    """Isi tenant'a ve saglayici kararina MUHURLE (kuyruga girmeden once).

    ⚠ Tenant'siz is OLUSTURULMAZ: damgalanmayan is `erisim_kapisi`nden
    gecemez, dolayisiyla sahibi bile goremez — sessiz sizinti yerine acik red.
    """
    t = _s(tenant_id)
    if not t:
        return {"ok": False, "neden": "TENANT-YOK", "kayit": kayit}
    k = kayit if isinstance(kayit, dict) else {}
    k["tenant_id"] = t
    k["metin_uzunlugu"] = len(_s(metin))
    if saglayici:
        # ⚠ Provider karari ISIN KENDISINDE saklanir; provenance buradan
        # turer (sonradan "hangi saglayiciydi" tahmin EDILMEZ).
        k["saglayici"] = {"provider_used": _s(saglayici.get("provider_used")),
                          "fallback_reason":
                              _s(saglayici.get("fallback_reason")),
                          "tercih": _s(saglayici.get("tercih")),
                          "kredi_tuketildi":
                              bool(saglayici.get("kredi_tuketildi"))}
    return {"ok": True, "neden": "", "kayit": k}


# ═══════════════ 3) TENANT KORUMALI SIGNED URL (R-1a halkasi) ═══════════

def imzalayici_kur(tenant_id: str, *, ttl_sn: Optional[int] = None
                   ) -> Optional[Callable]:
    """Bu tenant'a BAGLI imzalayici uret.

    ⚠ Uretilen baglanti BASKA tenant'in oturumunda GECERSIZDIR: imza
    mesajina tenant kimligi karisir. Baglanti sizsa bile yabanci bir
    oturumda calismaz.
    ⚠ Tenant yoksa imzalayici URETILMEZ (None) — imzasiz link SIZDIRILMAZ.
    """
    t = _s(tenant_id)
    if not t or not imzali_url.hazir():
        return None

    def _im(dosya: str) -> str:
        if ttl_sn is None:
            return imzali_url.imzala(dosya, tenant=t)
        return imzali_url.imzala(dosya, ttl_sn=ttl_sn, tenant=t)
    return _im


# ═══════════════ 4) ZINCIR RAPORU (kanit temelli) ═══════════════════════

def _qa_durum(d) -> str:
    if isinstance(d, dict):
        return _s(d.get("durum")).upper()
    return _s(d).upper()


def zincir_raporu(kayit: dict, *, tenant_id: str = "",
                  dosya_var: Optional[bool] = None) -> dict:
    """Her halkanin KANITINI topla. ⚠ Kanit yoksa halka TAMAM DEGILDIR.

    `dosya_var`: object storage kaniti — cikti dosyasi GERCEKTEN duruyor mu?
    None verilirse OLCULMEDI sayilir ve halka TAMAMLANMAZ (varsayim yok).
    """
    k = kayit if isinstance(kayit, dict) else {}
    t = _s(tenant_id) or _s(k.get("tenant_id"))
    sag = k.get("saglayici") if isinstance(k.get("saglayici"), dict) else {}
    plan = k.get("edit_plani") if isinstance(k.get("edit_plani"), dict) else {}
    plan_qa = plan.get("qa")
    on_durum = _qa_durum(plan_qa)
    # ⚠ FAZ R-1d-b — ICI BOS PRE-QA HUKMU KABUL EDILMEZ.
    # OLCULEN KUSUR (staging, 14 Agu): kopru manifesti doldurdu, `plan_kur`
    # calisti ve `QA=WARN` dondu — ama plan SIFIR cekim uretmisti
    # (`sahne=0`) ve butun olcum sozlukleri BOSTU. "WARN" hukmu sifir sahne
    # uzerinde VAKUMDA olusmustu; zincir bunu KANIT sayip videoyu KABUL etti.
    # Bu, "kanitsiz halka gecmez" sozlesmesinin ihlaliydi.
    # ⚠ Artik hukum YETMEZ, OLCULMUS OLMAK da sart: plan en az 1 cekim
    # kapsamali VE PRE-QA gercekten olcum yazmis olmali.
    try:
        on_sahne = int(plan.get("sahne") or 0)
    except (TypeError, ValueError):
        on_sahne = 0
    on_olcum = (plan_qa.get("olcumler") if isinstance(plan_qa, dict) else None)
    on_olculdu = bool(on_sahne >= 1 and isinstance(on_olcum, dict) and on_olcum)
    on_neden = ""
    if on_durum not in QA_KABUL:
        on_neden = f"PRE-QA:{on_durum or 'olculmedi'}"
    elif not on_olculdu:
        on_neden = f"PRE-QA-BOS:sahne={on_sahne},olcum={len(on_olcum or {})}"
    son_durum = _qa_durum(k.get("qa"))
    sahne = k.get("sahne_sayisi")
    try:
        sahne_n = int(sahne or 0)
    except (TypeError, ValueError):
        sahne_n = 0
    try:
        sure = float(k.get("sure") or 0)
    except (TypeError, ValueError):
        sure = 0.0

    halkalar = [
        {"asama": "oturum", "tamam": bool(t),
         "kanit": {"tenant_id": t}, "neden": "" if t else "TENANT-YOK"},
        {"asama": "metin", "tamam": int(k.get("metin_uzunlugu") or 0) > 0,
         "kanit": {"metin_uzunlugu": k.get("metin_uzunlugu")},
         "neden": "" if int(k.get("metin_uzunlugu") or 0) > 0 else "METIN-YOK"},
        {"asama": "plan", "tamam": sahne_n >= 1,
         "kanit": {"sahne_sayisi": sahne_n},
         "neden": "" if sahne_n >= 1 else "PLAN-YOK"},
        {"asama": "saglayici", "tamam": bool(_s(sag.get("provider_used"))),
         "kanit": {"provider_used": _s(sag.get("provider_used")),
                   "fallback_reason": _s(sag.get("fallback_reason"))},
         "neden": "" if _s(sag.get("provider_used")) else "SAGLAYICI-KARARI-YOK"},
        {"asama": "uzak_tts_render",
         "tamam": bool(_s(k.get("video"))) and sure > 0,
         "kanit": {"video": _s(k.get("video")), "sure_sn": sure},
         "neden": "" if (_s(k.get("video")) and sure > 0) else "RENDER-KANITI-YOK"},
        {"asama": "pre_qa", "tamam": not on_neden,
         "kanit": {"durum": on_durum or None, "sahne": on_sahne,
                   "olcum_sayisi": len(on_olcum or {})},
         "neden": on_neden},
        {"asama": "post_qa", "tamam": son_durum in QA_KABUL,
         "kanit": {"durum": son_durum or None},
         "neden": "" if son_durum in QA_KABUL else f"POST-QA:{son_durum or 'olculmedi'}"},
        {"asama": "depolama", "tamam": dosya_var is True,
         "kanit": {"dosya_var": dosya_var},
         "neden": "" if dosya_var is True else
                  ("DOSYA-YOK" if dosya_var is False else "DEPOLAMA-OLCULMEDI")},
        {"asama": "imzali_url", "tamam": bool(t) and imzali_url.hazir(),
         "kanit": {"imza_anahtari": imzali_url.hazir(),
                   "tenant_bagli": bool(t)},
         "neden": "" if (t and imzali_url.hazir()) else "IMZALANAMAZ"},
    ]
    eksik = [h["asama"] for h in halkalar if not h["tamam"]]
    return {"halkalar": halkalar, "eksik": eksik, "tam": not eksik,
            "zincir": list(ZINCIR_ADLARI)}


# ═══════════════ 5) TESLIM ════════════════════════════════════════════════

def teslim_et(*, is_id: str, tenant_id: str, kayit: dict,
              kutuphane_deposu: dict, kabul_zamani: float,
              dosya_var: Optional[bool] = None,
              ttl_sn: Optional[int] = None) -> dict:
    """Zincirin son halkasi: KABUL -> kutuphane -> tenant korumali URL.

    ⚠ UC AYRI KAPI, hepsi fail-closed:
      1. `zincir_raporu` TAM olmali (her halkanin kaniti var).
      2. `kutuphane.kabul_edilebilir_mi` KABUL demeli (QA FAIL/olculmemis GIRMEZ).
      3. Kayit tenant'a ait olmali.
    Ucu de gecmeyen is TESLIM EDILMEZ; `teslim=False` ve NEDEN doner.
    ⚠ Bu fonksiyon DOSYA SILMEZ: tavan asilirsa `silinecek` KUYRUGU doner.
    """
    t = _s(tenant_id)
    k = kayit if isinstance(kayit, dict) else {}
    rapor = zincir_raporu(k, tenant_id=t, dosya_var=dosya_var)
    kabul = kutuphane.kabul_edilebilir_mi(k)
    sahiplik = erisim_kapisi(k, t)

    nedenler = []
    if not rapor["tam"]:
        nedenler.append("ZINCIR-EKSIK:" + ",".join(rapor["eksik"]))
    if not kabul["kabul"]:
        nedenler.append("KABUL-YOK:" + kabul["neden"])
    if not sahiplik["izin"]:
        nedenler.append("SAHIPLIK:" + sahiplik["neden"])
    if nedenler:
        return {"teslim": False, "neden": "+".join(nedenler),
                "zincir": rapor, "silinecek": [], "video_url": None,
                "kutuphane": list((kutuphane_deposu or {}).get(t) or [])}

    sag = k.get("saglayici") if isinstance(k.get("saglayici"), dict) else {}
    kt_kayit = kutuphane.kayit_kur(
        is_id=is_id, tenant_id=t,
        dosya=imzali_url.guvenli_ad(_s(k.get("video"))),
        kayit={
            "olusturma_zamani": k.get("olusturma_zamani"),
            "duration": k.get("sure"),
            "qa": k.get("qa") if isinstance(k.get("qa"), dict) else {},
            "provenance": {
                "provider_used": _s(sag.get("provider_used")),
                "fallback_reason": _s(sag.get("fallback_reason")),
                # ⚠ Model adi UYDURULMAZ: bilinmiyorsa None kalir.
                "model": _s(sag.get("model")) or None,
                "kredi_tuketildi": bool(sag.get("kredi_tuketildi")),
                "lisanslar": list(k.get("atiflar") or []),
                "kaynaklar": list(k.get("kaynaklar") or []),
            },
        },
        kabul_zamani=float(kabul_zamani))
    ek = kutuphane.ekle(kutuphane_deposu, kt_kayit)
    if not ek["eklendi"]:
        return {"teslim": False, "neden": "KUTUPHANE:" + ek["neden"],
                "zincir": rapor, "silinecek": [], "video_url": None,
                "kutuphane": list((kutuphane_deposu or {}).get(t) or [])}

    imz = imzalayici_kur(t, ttl_sn=ttl_sn)
    url = imz(kt_kayit["dosya"]) if imz else ""
    return {"teslim": True, "neden": "", "zincir": rapor,
            "silinecek": ek["silinecek"], "kayit": kt_kayit,
            # ⚠ Imzalanamadiysa BOS LINK verilmez, None + bayrak doner.
            "video_url": url or None, "imzalanamadi": not url,
            "kutuphane": ek["kutuphane"]}


def listele(kutuphane_deposu: dict, tenant_id: str, *,
            ttl_sn: Optional[int] = None) -> dict:
    """Tenant'in son-3 kutuphanesi, TENANT'A BAGLI signed URL ile."""
    return kutuphane.listele(kutuphane_deposu, tenant_id,
                             imzalayici=imzalayici_kur(tenant_id,
                                                       ttl_sn=ttl_sn))


def kapsam_ozeti() -> dict:
    return {
        "sema_surum": SEMA_SURUM,
        "zincir": list(ZINCIR_ADLARI),
        "fail_closed": True,
        "kanitsiz_halka_gecer": False,
        "oturum_zorunlu": True,
        "signed_url_tenant_bagli": True,
        "imzasiz_link_uretilir": False,
        "gercek_oauth": False,
        "kredi_tuketir": False,
        "aga_cikar": False, "medya_acar": False, "dosya_siler": False,
        "render_eder": False,
        "kutuphane_tavani": kutuphane.TAVAN,
        "qa_kabul": list(QA_KABUL),
        "not": ("halkalarin kaniti isin KENDI kaydindan okunur; kanit yoksa "
                "'muhtemelen olmustur' DENMEZ, teslim EDILMEZ"),
    }
