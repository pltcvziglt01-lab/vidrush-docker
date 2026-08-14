#!/usr/bin/env python3
"""EDIT PLANI KOPRUSU — analiz + stil profili + dogrulanmis olgu + secilmis
medya zincirini PROFESYONEL EDIT PLANINA (EditorV2) baglar (Faz I-9).

⚠ NEDEN VAR: parcalar tek tek vardi ama ARALARINDA BAG YOKTU:
  · `girdi_analizi` konsepti ve stili cozuyordu   -> edit planina GITMIYORDU
  · `stil_profili` tempo/gecis/palet/ses tasiyordu -> EditorV2 props'a GITMIYORDU
  · `arastirma_kopru` dogrulanmis olgulari veriyordu -> plan onlari GORMUYORDU
  · `medya_kopru` lisansli klipleri seciyordu     -> render planina GECMIYORDU
Yani "tek akista arastirma + medya + kurgu" iddiasi uctan uca KANITLANMAMISTI.

⚠ VARSAYILAN KAPALI (opt-in): `EDITOR_V2=1` ya da is ayarinda
`{"editor_v2": True}`. Kapaliyken bu modulun hicbir satiri uretim kararina
karisMAZ; `pipeline.py` MEVCUT `VidrushVideo` hizli render yolunu aynen surdurur.

⚠ BU MODUL RENDER ETMEZ ve AG CAGIRMAZ. Yalnizca plan/props uretir ve QA-on
kararini raporlar. Gercek render `editor.remotion_v2.render()` isidir ve bu
kopru onu CAGIRMAZ.

⚠ SERT KURALLAR:
  1. LISANSSIZ MEDYA RENDER PLANINA GIREMEZ. Aday havuzu `render_kullanilabilir`
     olanlarla kurulur; digerleri ELENIR ve elenme GORUNUR olur.
  2. KAPSAM BOSLUGU RASTGELE STOKLA KAPANMAZ. Bosluk boslugudur; plana
     `kapsam_bosluklari` olarak gecer ve raporlanir.
  3. QA-ON FAIL ISE RENDER BASLATILMAZ. `render_edilebilir=False` doner;
     PASS/WARN ayrimi ayrica gorunur.
  4. DESTEKLENMEYEN EFEKT GIZLENMEZ. `efekt_kapsami` uygulanan/yaklastirilan/
     atlanan sayilariyla raporlanir.
"""
from __future__ import annotations

import copy
import os
import sys

# ── OPT-IN BAYRAGI — VARSAYILAN KAPALI ──
ACIK = os.environ.get("EDITOR_V2", "0").lower() in ("1", "true", "evet", "on")

# Bileşik stil profili kimligi -> Faz C edit profili adi.
# ⚠ Bilinmeyen kimlik `premium-modern`e duser (uydurma profil URETILMEZ).
STIL_EDIT_PROFILI = {
    "belgesel-sinematik": "premium-modern",
    "belgesel-arastirmaci": "investigative-essay",
    "seyahat-4k": "atlas-journey",
    "ambient-sakin": "atlas-journey",
    "explainer-hizli": "premium-modern",
    "bilim-anlatisi": "investigative-essay",
    "hikaye-sinematik": "premium-modern",
    "korku-gerilim": "premium-modern",
    "cocuk-yumusak": "atlas-journey",
    "urun-tanitim": "premium-modern",
    "yasam-dinamik": "atlas-journey",
    "kultur-muzik": "premium-modern",
}
VARSAYILAN_EDIT_PROFILI = "premium-modern"

# Motion spec listesindeki TIPOGRAFI katmanlari. Altyazi DIZISI ayrica
# vardir ama TTS zamanlamasindan gelir; basliklar/etiketler spec olarak
# tasinir — ikisi de sayilir ki tipografi karari "kayboldu" sanilmasin.
TIPOGRAFI_SPECLERI = frozenset((
    "chapter-title", "callout", "lower-third", "kaynak-yazi", "alt-band",
    "etiket", "vurgu-kutu", "data-chart"))

# Motion spec listesindeki GECIS adlari (ayri bir props alani yoktur).
GECIS_SPECLERI = frozenset((
    "hard-cut", "crossfade", "flash", "karartma", "whip", "whip-pan",
    "zoom-through", "dissolve", "wipe"))

NEDEN = {
    "KAPALI": "EditorV2 plani acik degil (opt-in)",
    "MODUL-YOK": "Faz C editor paketi yuklenemedi",
    "CUMLE-YOK": "anlatim cumlesi verilmedi",
    "MEDYA-YOK": "lisans duvarindan gecen tek aday bile yok",
    "QA-FAIL": "on-render QA FAIL — render BASLATILMAZ",
    "HATA": "beklenmeyen hata",
}


def acik_mi(is_ayar=None) -> tuple:
    """(acik, gerekce). Env bayragi YA DA dahili is ayari.

    ⚠ `is_ayar` DAHILI sozluktur; 22 alanlik generate sozlesmesi buraya
    ulasmaz (arayuz bu alani gondermez, `server.py` okumaz).
    """
    if ACIK:
        return True, "EDITOR_V2 ortam degiskeni acik"
    try:
        if isinstance(is_ayar, dict) and is_ayar.get("editor_v2") is True:
            return True, "is ayari editor_v2=True"
    except Exception:
        pass
    return False, NEDEN["KAPALI"]


def kalite_kapisi_acik(is_ayar=None, acik_istek=None) -> bool:
    """Faz I-14 kalite kapisi acik mi? VARSAYILAN KAPALI.

    Uc yol, ucu de ACIK KARAR (sirasiyla):
      1. cagri parametresi  `kalite_kapisi=True`
      2. ortam degiskeni    `KALITE_KAPISI=1`
      3. dahili is ayari    `{"kalite_kapisi": True}`

    ⚠ `is_ayar` DAHILI sozluktur; 22 alanlik generate sozlesmesi buraya
    ulasmaz. Yalnizca gercek `True` acar — `"evet"`, `1`, `"true"` ACMAZ.
    """
    if acik_istek is True:
        return True
    if acik_istek is False:
        return False
    if os.environ.get("KALITE_KAPISI", "").strip() == "1":
        return True
    try:
        return bool(isinstance(is_ayar, dict)
                    and is_ayar.get("kalite_kapisi") is True)
    except Exception:
        return False


def edit_profili_sec(stil_kimligi: str) -> tuple:
    """(profil_adi, gerekce). Bilinmeyen kimlikte VARSAYILANA duser."""
    k = str(stil_kimligi or "").strip()
    if k in STIL_EDIT_PROFILI:
        return STIL_EDIT_PROFILI[k], f"stil '{k}' -> {STIL_EDIT_PROFILI[k]}"
    return (VARSAYILAN_EDIT_PROFILI,
            (f"stil '{k}' eslesmedi -> varsayilan {VARSAYILAN_EDIT_PROFILI}"
             if k else f"stil verilmedi -> varsayilan {VARSAYILAN_EDIT_PROFILI}"))


def lisans_suz(medya_manifest: dict) -> tuple:
    """LISANS DUVARI: yalnizca `render_kullanilabilir` adaylar gecer.

    Doner: (temiz_manifest, elenen_kayitlari). Elenme SESSIZ degil.
    ⚠ Kapsam bosluklari AYNEN tasinir — rastgele stokla KAPANMAZ.
    """
    m = medya_manifest if isinstance(medya_manifest, dict) else {}
    gecen, elenen = [], []
    for a in (m.get("adaylar") or []):
        if not isinstance(a, dict):
            continue
        if a.get("render_kullanilabilir") is True:
            gecen.append(a)
        else:
            elenen.append({
                "asset_id": str(a.get("asset_id") or ""),
                "saglayici": str(a.get("saglayici") or ""),
                "lisans": str(a.get("lisans") or "unknown"),
                "neden": str(a.get("red_nedeni")
                             or "render_kullanilabilir degil")[:160]})
    temiz = dict(m)
    temiz["adaylar"] = gecen
    # ⚠ Bosluklar KAPATILMAZ, aynen tasinir.
    temiz["kapsam_bosluklari"] = list(m.get("kapsam_bosluklari") or [])
    return temiz, elenen


def _fact_manifesti(olgular) -> dict:
    """Dogrulanmis olgulari `plan.uret`in bekledigi bicime cevir.

    ⚠ Havuz zaten `arastirma_kopru.olgu_listesi` filtresinden gecti; burada
    yalnizca bicim degistirilir, YENI iddia URETILMEZ.
    """
    iddialar = []
    for o in (olgular or []):
        if isinstance(o, dict) and o.get("fact_id"):
            iddialar.append({"fact_id": str(o["fact_id"]),
                             "metin": str(o.get("metin") or ""),
                             "guven": str(o.get("guven") or "")})
    return {"iddialar": iddialar}


def stil_kararlari(stil_profili_sozlugu) -> dict:
    """Bilesik profilin EditorV2'ye tasinacak kararlari (Faz I-2b boyutlari).

    ⚠ Bu sozluk props'a EK olarak yazilir; Remotion bilmedigi alani yok sayar.
    Amac izlenebilirlik: "hangi stil karari hangi videoda uygulandi".
    """
    p = stil_profili_sozlugu if isinstance(stil_profili_sozlugu, dict) else {}
    prof = p.get("profil") if isinstance(p.get("profil"), dict) else {}
    if not prof:
        return {}
    al = lambda boyut, alan, vars_=None: (                       # noqa: E731
        (prof.get(boyut) or {}).get(alan, vars_)
        if isinstance(prof.get(boyut), dict) else vars_)
    return {
        "kimlik": str(p.get("kimlik") or ""),
        "surum": str(p.get("surum") or ""),
        "kaynak": str(p.get("kaynak") or ""),
        "tempo": {"plan_sn": al("tempo", "plan_sn"),
                  "maks_plan_sn": al("tempo", "maks_plan_sn"),
                  "dagilim": al("tempo", "dagilim")},
        "gecis": {"tur": al("gecis", "tur"), "sure_sn": al("gecis", "sure_sn"),
                  "oran_pct": al("gecis", "oran_pct")},
        "kamera": {"hareket": al("kamera", "hareket"),
                   "yogunluk": al("kamera", "yogunluk")},
        "tipografi": {"altyazi": al("tipografi", "altyazi"),
                      "baslik": al("tipografi", "baslik"),
                      "guvenli_alan_pct": al("tipografi", "guvenli_alan_pct")},
        "renk": {"grade": al("palet", "grade"),
                 "kontrast": al("palet", "kontrast"),
                 "doygunluk": al("palet", "doygunluk")},
        "ses": {"muzik": al("ses", "muzik"), "muzik_db": al("ses", "muzik_db"),
                "ducking_db": al("ses", "ducking_db"),
                "sfx": al("ses", "sfx")},
    }


def plan_kur(*, cumleler, medya_manifest, olgular=None, stil=None,
             analiz=None, cikti_dizin: str = ".", is_ayar=None,
             ambience: str = "", muzik: str = "", beklenen_ulke: str = "",
             beklenen_donem: str = "", fps: int = 30,
             genislik: int = 1920, yukseklik: int = 1080,
             destek_matrisi=None, kare_olcu=None,
             anlatim_bitis_sn=None, benzerlik_okuyucu=None,
             enerji_okuyucu=None,
             kare_okuyucu=None,
             altyazi_kupleri=None, kalite_kapisi=None,
             saglayici_tavani=None) -> dict:
    """Uctan uca: analiz + stil + olgu + medya -> EditorV2 props.

    Doner:
      {"ok", "neden", "render_edilebilir", "qa", "profil_adi", "profil_gerekce",
       "stil_kararlari", "elenen_medya", "kapsam_bosluklari", "efekt_kapsami",
       "props", "edit_manifest", "uyarilar"}

    ⚠ RENDER ETMEZ. `render_edilebilir` yalnizca bir KARARDIR.
    ⚠ ISTISNA FIRLATMAZ; hata durumunda `ok=False` + gorunur neden doner.
    """
    bos = {"ok": False, "neden": "", "render_edilebilir": False, "qa": {},
           "profil_adi": "", "profil_gerekce": "", "stil_kararlari": {},
           "elenen_medya": [], "kapsam_bosluklari": [], "efekt_kapsami": {},
           "props": {}, "edit_manifest": {}, "uyarilar": []}
    acik, gerekce = acik_mi(is_ayar)
    if not acik:
        return {**bos, "neden": "KAPALI"}
    if not cumleler:
        return {**bos, "neden": "CUMLE-YOK"}

    try:
        from editor import adapter, plan, remotion_v2
    except Exception as e:
        print(f"  editor paketi yuklenemedi: {type(e).__name__}: {str(e)[:120]}",
              file=sys.stderr)
        return {**bos, "neden": "MODUL-YOK"}

    uyarilar = []
    # ── 1) STIL PROFILI -> EDIT PROFILI ──
    stil_kimlik = str((stil or {}).get("kimlik") or "") if isinstance(stil, dict) else ""
    profil_adi, profil_gerekce = edit_profili_sec(stil_kimlik)
    kararlar = stil_kararlari(stil)

    # ── 2) LISANS DUVARI ──
    temiz_medya, elenen = lisans_suz(medya_manifest)
    if elenen:
        uyarilar.append(f"{len(elenen)} aday lisans/kullanilabilirlik "
                        f"duvarindan gecemedi ve plana ALINMADI")
    if not (temiz_medya.get("adaylar") or []):
        return {**bos, "neden": "MEDYA-YOK", "profil_adi": profil_adi,
                "profil_gerekce": profil_gerekce, "stil_kararlari": kararlar,
                "elenen_medya": elenen,
                "kapsam_bosluklari": list(temiz_medya.get("kapsam_bosluklari") or []),
                "uyarilar": uyarilar + ["kapsam boslugu RASTGELE STOKLA "
                                        "KAPANMADI"]}

    # ── 3) PLAN (beat -> gramer -> motion -> tipografi -> ses -> QA-on) ──
    try:
        cikti = plan.uret(
            cumleler=list(cumleler), medya_manifest=temiz_medya,
            arastirma_manifest=_fact_manifesti(olgular),
            profil_adi=profil_adi, beklenen_ulke=beklenen_ulke,
            beklenen_donem=beklenen_donem, cikti_dizin=cikti_dizin,
            ambience=ambience, muzik=muzik,
            kare_olcu=kare_olcu, anlatim_bitis_sn=anlatim_bitis_sn,
            benzerlik_okuyucu=benzerlik_okuyucu,
            enerji_okuyucu=enerji_okuyucu,
            kare_okuyucu=kare_okuyucu,
            altyazi_kupleri=altyazi_kupleri,
            # ⚠ I-22: varsayilan 4 tavani COK SAGLAYICILI durum icin bir
            # cesitlilik guvencesidir. TEK saglayicili bir iste 4'ten fazla
            # beat olusursa fazlasi GARANTILI medyasiz kalir. Cagiran taraf
            # tavani PLANIN GERCEK BEAT SAYISIYLA eslestirebilir; verilmezse
            # eski davranis (4) aynen surer.
            **({"saglayici_tavani": int(saglayici_tavani)}
               if saglayici_tavani else {}),
            kalite_kapisi=kalite_kapisi_acik(is_ayar, kalite_kapisi))
    except Exception as e:
        print(f"  edit plani uretilemedi: {type(e).__name__}: {str(e)[:140]}",
              file=sys.stderr)
        return {**bos, "neden": "HATA", "profil_adi": profil_adi,
                "profil_gerekce": profil_gerekce, "stil_kararlari": kararlar,
                "elenen_medya": elenen,
                "uyarilar": uyarilar + [f"{type(e).__name__}: {str(e)[:120]}"]}

    render_plan = cikti.get("render_plan") or {}
    edit_manifest = cikti.get("edit_manifest") or {}
    qa = cikti.get("editor_qa") or {}
    qa_durum = str(qa.get("durum") or "OLCULMEDI")

    # ── 4) ADAPTER -> Remotion props ──
    # ⚠ `plan.uret` adapter donusumunu ZATEN yapiyor; ikinci kez cevirmek
    # sapma riski dogururdu. Onun ciktisi kullanilir, yoksa yeniden cevrilir.
    props, efekt_kapsami = {}, {}
    try:
        donusum = cikti.get("adapter")
        if donusum is None:
            donusum = adapter.donustur(render_plan, fps=fps, genislik=genislik,
                                       yukseklik=yukseklik)
        props = copy.deepcopy(getattr(donusum, "remotion_props", None) or {})
        uyarilar.extend([str(u) for u in
                         (getattr(donusum, "uyarilar", None) or [])][:20])
        # ⚠ DESTEKLENMEYEN EFEKT GORUNUR KAYIP: adapter'in kendi kayip
        # listesi de raporlanir (sessizce dusmesin).
        for k in (getattr(donusum, "kayip_efektler", None) or [])[:10]:
            uyarilar.append(f"kayip efekt: {k}")
    except Exception as e:
        print(f"  adapter donusumu basarisiz: {type(e).__name__}", file=sys.stderr)
        uyarilar.append(f"adapter: {type(e).__name__}: {str(e)[:100]}")

    # ── 5) STIL KARARLARI PROPS'A (izlenebilirlik) ──
    if props and kararlar:
        props["stilProfili"] = kararlar

    # ── 6) DESTEKLENMEYEN EFEKT GORUNUR KAYIP ──
    try:
        efekt_kapsami = remotion_v2.uygulanan_atlanan(props, destek_matrisi)
        atlanan = (efekt_kapsami.get("sayim") or {}).get("bilinmeyen", 0)
        if atlanan:
            uyarilar.append(f"{atlanan} motion spec Remotion destek "
                            f"matrisinde YOK — render'da uygulanmayacak")
    except Exception as e:
        efekt_kapsami = {"hata": f"{type(e).__name__}"}
        uyarilar.append("efekt kapsami olculemedi")

    # ── 7) QA-ON KARARI: FAIL ise RENDER BASLATILMAZ ──
    render_edilebilir = qa_durum in ("PASS", "WARN")
    if not render_edilebilir:
        uyarilar.append(f"on-render QA '{qa_durum}' — RENDER BASLATILMAZ")

    return {
        "ok": True,
        "neden": "" if render_edilebilir else "QA-FAIL",
        "render_edilebilir": render_edilebilir,
        # ⚠ J-2a: `medya_turu` YALNIZ RAPOR alanidir — durum/fail/warn
        # hesabina GIRMEZ, hicbir esik ENFORCE ETMEZ.
        "qa": {"durum": qa_durum, "fail": qa.get("fail", 0),
               "warn": qa.get("warn", 0),
               "sorun_sayisi": len(qa.get("sorunlar") or []),
               "medya_turu": (qa.get("olcumler") or {}).get("medya_turu")},
        "profil_adi": profil_adi, "profil_gerekce": profil_gerekce,
        "stil_kararlari": kararlar,
        "elenen_medya": elenen,
        "kapsam_bosluklari": list(temiz_medya.get("kapsam_bosluklari") or []),
        "efekt_kapsami": efekt_kapsami,
        "props": props, "edit_manifest": edit_manifest,
        "uyarilar": uyarilar[:30],
    }


def sahne_zinciri(props: dict) -> list:
    """Her sahnenin KORUNMASI gereken bag alanlarini cikar (denetim icin).

    ⚠ Bu fonksiyon bir ISPAT ARACIDIR: scene_id / fact_id / asset /
    provenance / ritim / motion / gecis zincirinin props'a kadar geldigini
    tek bakista gosterir.
    """
    cikti = []
    for sh in ((props or {}).get("sahneler") or []):
        if not isinstance(sh, dict):
            continue
        motion = [m.get("ad") for m in (sh.get("motion") or [])
                  if isinstance(m, dict)]
        # ⚠ Gecis AYRI bir alan DEGIL; motion spec listesinin icindedir
        # (hard-cut / crossfade / flash ...). Ayri alan aramak bos deger
        # dondururdu — olculdu, duzeltildi.
        gecisler = [m for m in motion if m in GECIS_SPECLERI]
        cikti.append({
            # ── bag / provenance ──
            "beat_id": sh.get("beat_id") or "",
            "scene_id": sh.get("scene_id") or "",
            "fact_id": sh.get("fact_id") or "",
            "asset_id": sh.get("asset_id") or "",
            "saglayici": sh.get("saglayici") or "",
            "lisans": sh.get("lisans") or "",
            # ── ritim / cekim suresi ──
            "sure_sn": sh.get("sure"),
            "bas_sn": sh.get("bas_sn"),
            # ── kamera / motion / gecis ──
            "cekim_turu": sh.get("cekim_turu") or "",
            "hareket": sh.get("hareket") or "",
            "kadraj": sh.get("kadraj") or "",
            "motion": motion,
            "gecis": gecisler,
            # ── tipografi ──
            "altyazi_adet": len(sh.get("altyazi") or []),
            "tipografi": [m for m in motion if m in TIPOGRAFI_SPECLERI],
            # ── ses / ducking ──
            "ses": sh.get("ses") or "",
            "j_cut": bool(sh.get("j_cut")),
            "l_cut": bool(sh.get("l_cut")),
            "islev": sh.get("islev") or "",
        })
    return cikti
