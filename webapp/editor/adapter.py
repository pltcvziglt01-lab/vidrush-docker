"""ADAPTER — render_plan'i MEVCUT render motorlarinin sozlesmesine cevirir.

Iki hedef bicim:
  1. Remotion props  (app/render-studio/src/Video.tsx'in bekledigi sozluk)
  2. hizli_render sahne sozlugu (webapp/hizli_render.py'nin bekledigi)

⚠ BU MODUL MEVCUT RENDER KODUNA BAGLANMIYOR. Faz C'nin siniri: adapter + test.
Cagirma Faz D'de yapilacak. Burada sadece DONUSTURUCU var; import bile
etmiyoruz ki calisan hat riske girmesin.

⚠⚠ IKI AYRI CIKTI, PAYLASILAN NESNE YOK (11 Agu 2026 kalite kapisi reddi):
Ilk surumde `remotion_props["sahneler"] = hizli_sahneler` yaziyordum — AYNI
LISTE VE AYNI SOZLUKLER. Sonuc: premium Remotion yolu, ffmpeg icin
indirgenmis sahneleri aliyordu; parallax-2.5d / light-sweep /
document-highlight / map-route / data-chart gibi OZGUN spec'ler Remotion
tarafinda da kayboluyor, yerine fallback kaliyordu. Yani `renderer=remotion`
beyani render edilebilir bir sozlesme DEGILDI, sadece bir not.

Artik iki liste AYRI uretiliyor ve derin kopyalaniyor:
  hizli_sahneler    -> ffmpeg sozlesmesi, fallback UYGULANIR, kayip raporlanir
  remotion_sahneler -> OZGUN spec listesi AYNEN korunur (renderer, fallback,
                       gerekce, keyframe/easing, katman, sure) + izlenebilirlik
Premium yol asla fallback ile EZILMEZ. Fallback yalnizca hizli yolun carasidir.

EN ONEMLI KURAL — SESSIZ KAYIP YASAK:
ffmpeg'de karsiligi olmayan bir motion spec'i sessizce dusurmek 11 Agu'da
olculen en pahali hataydi (35 efektten 29'u kayboluyordu). Bu yuzden:
  - spec ffmpeg'de destekliyse -> ffmpeg alanina yazilir
  - fallback varsa -> fallback yazilir + UYARI uretilir (ne kaybedildi)
  - fallback yoksa -> sahne "remotion_gerekli" isaretlenir
Hicbir durumda spec sessizce yok sayilmaz; donusturucu her karar icin
uyari/karar kaydi doner.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Optional

from . import motion

# hizli_render sahne sozlugunun BILINEN alanlari (kaybolmamasi gerekenler)
HIZLI_RENDER_ALANLARI = (
    "tur", "medya", "ses", "sure", "zoom", "pan", "overlay", "vurgu", "islev",
    "altyazi", "efektler", "bolum", "bolumYeri", "altBand", "etiketler",
    "vurguKutu", "gecisImza", "kaynakYazi", "grafik",
)
# Remotion props sahne alanlari
REMOTION_ALANLARI = HIZLI_RENDER_ALANLARI

# motion spec adi -> hizli_render "efektler" listesindeki ad
EFEKT_ADI = {
    "grain": "grain", "vignette": "vinyet", "grade": None,
    "shake": "sarsinti", "handheld": "elde-kamera", "chromatic": "kromatik",
    "directional-blur": "yon-blur", "soft-zoom": "yumusak-zoom",
    "push-in": None, "pull-out": None, "pan-right": None, "pan-left": None,
    "static": None, "slow-drift": None, "letterbox": None,
}


@dataclass
class DonusumSonucu:
    remotion_props: dict = field(default_factory=dict)
    hizli_sahneler: list = field(default_factory=list)
    remotion_sahneler: list = field(default_factory=list)
    uyarilar: list = field(default_factory=list)
    remotion_gerekli_sahneler: list = field(default_factory=list)
    kayip_efektler: list = field(default_factory=list)
    hizli_props: dict = field(default_factory=dict)

    def sozluk(self) -> dict:
        return {"uyari": len(self.uyarilar),
                "remotion_gerekli": self.remotion_gerekli_sahneler,
                "kayip_efekt": self.kayip_efektler,
                "uyarilar": self.uyarilar,
                "sahne_sayisi": len(self.hizli_sahneler),
                "remotion_sahne_sayisi": len(self.remotion_sahneler),
                "remotion_spec_sayisi": sum(
                    len(s.get("motion") or []) for s in self.remotion_sahneler)}


def _zoom_pan(spec: dict) -> tuple:
    """Kamera spec'ini hizli_render'in zoom/pan alanlarina cevir."""
    ad = spec.get("ad", "static")
    prm = spec.get("parametre") or {}
    z = prm.get("zoom") or [1.0, 1.0]
    if ad in ("push-in", "soft-zoom") or (len(z) == 2 and z[1] > z[0]):
        zoom = "in"
    elif ad == "pull-out" or (len(z) == 2 and z[1] < z[0]):
        zoom = "out"
    else:
        zoom = "yok"
    pan = {"pan-right": "right", "pan-left": "left", "slow-drift": "right"}.get(
        ad, "yok")
    return zoom, pan


def donustur(render_plan: dict, *, fps: int = 30, genislik: int = 1920,
             yukseklik: int = 1080) -> DonusumSonucu:
    """render_plan.json -> (remotion props, hizli_render sahneleri) + uyarilar."""
    s = DonusumSonucu()
    sahneler_giris = render_plan.get("sahneler") or []

    for i, sh in enumerate(sahneler_giris):
        beat_id = sh.get("beat_id") or f"b{i:03d}"
        # ── PREMIUM (Remotion) SAHNESI: ozgun spec'ler AYNEN, derin kopya ──
        # Bu sozluk hizli yolla HICBIR nesne paylasmaz (copy.deepcopy).
        remotion_sahne = {
            "beat_id": beat_id,
            "scene_id": sh.get("scene_id") or "",
            "fact_id": sh.get("fact_id") or "",
            "asset_id": sh.get("asset_id") or "",
            "saglayici": sh.get("saglayici") or "",
            "lisans": sh.get("lisans") or "",
            "tur": sh.get("medya_turu") or "image",
            "medya": sh.get("medya_yolu") or "",
            "ses": sh.get("ses_yolu") or "",
            "sure": round(float(sh.get("sure_sn") or 0), 3),
            "bas_sn": round(float(sh.get("bas_sn") or 0), 3),
            "islev": sh.get("islev") or "aciklama",
            "perde": sh.get("perde") or "",
            "cekim_turu": sh.get("cekim_turu") or "",
            "hareket": sh.get("hareket") or "",
            "kadraj": sh.get("kadraj") or "",
            "kaynak_aralik": list(sh.get("kaynak_aralik") or [0.0, 0.0]),
            "j_cut": bool(sh.get("j_cut")), "l_cut": bool(sh.get("l_cut")),
            "altyazi": copy.deepcopy(sh.get("altyazi") or []),
            # OZGUN MOTION SPEC LISTESI — renderer/fallback/gerekce/easing/katman
            # alanlariyla birlikte, hicbiri indirgenmeden.
            "motion": copy.deepcopy(sh.get("motion") or []),
            "gerekce": sh.get("gerekce") or "",
        }
        hedef: dict = {
            "tur": sh.get("medya_turu") or "image",
            "medya": sh.get("medya_yolu") or "",
            "ses": sh.get("ses_yolu") or "",
            "sure": round(float(sh.get("sure_sn") or 0), 3),
            "zoom": "yok", "pan": "yok", "overlay": "", "vurgu": False,
            "islev": sh.get("islev") or "aciklama",
            "altyazi": sh.get("altyazi") or [],
            "efektler": [],
        }
        remotion_gerekli = False
        specler = sh.get("motion") or []

        for sp in specler:
            ad = sp.get("ad", "")
            renderer = sp.get("renderer", "ffmpeg")
            prm = sp.get("parametre") or {}

            # ── Kamera ──
            if ad in ("push-in", "pull-out", "pan-right", "pan-left",
                      "static", "slow-drift", "soft-zoom", "handheld"):
                z, pan = _zoom_pan(sp)
                if z != "yok":
                    hedef["zoom"] = z
                if pan != "yok":
                    hedef["pan"] = pan
                if ad == "handheld":
                    hedef["efektler"].append({"ad": "elde-kamera", "siddet": 1.0})
                continue

            # ── Yazi / grafik katmanlari ──
            if ad == "chapter-title":
                hedef["bolum"] = prm.get("metin", "")
                hedef["bolumYeri"] = "orta"
                continue
            if ad == "lower-third":
                hedef["altBand"] = {"baslik": prm.get("baslik", ""),
                                    "alt": prm.get("alt", "")}
                continue
            if ad == "callout":
                hedef.setdefault("etiketler", []).append(
                    {"metin": prm.get("metin", ""),
                     "x": float(prm.get("x") or 0.5),
                     "y": float(prm.get("y") or 0.45)})
                continue
            if ad == "source-label":
                hedef["kaynakYazi"] = prm.get("metin", "")
                continue
            if ad == "document-highlight":
                b = prm.get("bolge") or [0.3, 0.3, 0.3, 0.3]
                hedef["vurguKutu"] = {"x": b[0], "y": b[1],
                                      "w": b[2] if len(b) > 2 else 0.3,
                                      "h": b[3] if len(b) > 3 else 0.3}
                continue

            # ── Gecis imzasi ──
            if prm.get("tur") in motion.GECIS_GEREKCESI:
                tur = prm["tur"]
                if tur in ("karartma", "flash", "whip"):
                    hedef["gecisImza"] = tur
                elif tur in ("j-cut", "l-cut"):
                    # hizli_render'da karsiligi YOK -> ses planinda kaliyor
                    s.uyarilar.append({
                        "beat_id": beat_id, "spec": tur, "karar": "ses-planinda",
                        "detay": "J/L cut goruntu motorunda degil ses "
                                 "montajinda uygulanir"})
                continue

            # ── Taban doku katmanlari ──
            if ad in EFEKT_ADI:
                efekt_adi = EFEKT_ADI[ad]
                if efekt_adi:
                    hedef["efektler"].append(
                        {"ad": efekt_adi,
                         "siddet": float(prm.get("siddet") or 1.0)})
                elif ad == "grade":
                    prof = str(prm.get("profil") or "")
                    if "soguk" in prof:
                        hedef["efektler"].append({"ad": "soguk-grade",
                                                  "siddet": 0.8})
                    elif "sicak" in prof:
                        hedef["efektler"].append({"ad": "sicak-grade",
                                                  "siddet": 0.8})
                    if "kontrast" in prof:
                        hedef["efektler"].append({"ad": "kontrast-grade",
                                                  "siddet": 1.0})
                continue

            # ── ffmpeg'de KARSILIGI OLMAYAN ──
            if renderer == "remotion" or sp.get("remotion_zorunlu"):
                fb = sp.get("fallback")
                if fb:
                    fb_ad = fb.get("ad", "")
                    if fb_ad in EFEKT_ADI and EFEKT_ADI[fb_ad]:
                        hedef["efektler"].append(
                            {"ad": EFEKT_ADI[fb_ad],
                             "siddet": float((fb.get("parametre") or {}).get(
                                 "siddet") or 1.0)})
                    elif fb_ad == "lower-third":
                        p2 = fb.get("parametre") or {}
                        hedef["altBand"] = {"baslik": p2.get("baslik", ""),
                                            "alt": p2.get("alt", "")}
                    elif fb_ad == "callout":
                        p2 = fb.get("parametre") or {}
                        hedef.setdefault("etiketler", []).append(
                            {"metin": p2.get("metin", ""),
                             "x": float(p2.get("x") or 0.5),
                             "y": float(p2.get("y") or 0.45)})
                    elif fb_ad in ("crossfade", "karartma", "flash"):
                        hedef["gecisImza"] = ("karartma" if fb_ad == "karartma"
                                              else fb_ad)
                    s.uyarilar.append({
                        "beat_id": beat_id, "spec": ad, "karar": "fallback",
                        "fallback": fb_ad, "kayip": fb.get("kayip", "")})
                    s.kayip_efektler.append(
                        {"beat_id": beat_id, "spec": ad,
                         "kayip": fb.get("kayip", "belirtilmemis")})
                else:
                    # Fallback YOK -> sahne Remotion'a gider. SESSIZCE DUSMEZ.
                    remotion_gerekli = True
                    s.uyarilar.append({
                        "beat_id": beat_id, "spec": ad,
                        "karar": "remotion-zorunlu",
                        "detay": "ffmpeg karsiligi ve fallback yok"})
                continue

            # Taninmayan spec — asla sessiz gecilmez
            s.uyarilar.append({
                "beat_id": beat_id, "spec": ad, "karar": "TANINMAYAN",
                "detay": "adapter bu spec'i hizli yola ceviremiyor; "
                         "Remotion sahnesinde AYNEN korunuyor (sessiz kayip yok)"})
            remotion_gerekli = True

        # Beat kimligi izlenebilirlik icin sahnede kalir
        hedef["_beat_id"] = beat_id
        hedef["_fact_id"] = sh.get("fact_id") or ""
        hedef["_asset_id"] = sh.get("asset_id") or ""

        # ── PREMIUM GEREKSINIMI: fallback VARLIGI premium ihtiyacini SILMEZ ──
        # Ilk surumde yalnizca "fallback yok" durumunda isaretliyordum; fallback'i
        # olan parallax/light-sweep gibi spec'ler Remotion gereksinimini
        # kaybediyordu ve sahne premium yola HIC gitmiyordu.
        remotion_specleri = [sp for sp in (sh.get("motion") or [])
                             if sp.get("renderer") == "remotion"
                             or sp.get("remotion_zorunlu")]
        if remotion_specleri or remotion_gerekli:
            s.remotion_gerekli_sahneler.append(beat_id)
            remotion_sahne["premium_gerekce"] = [
                {"spec": sp.get("ad"), "gerekce": sp.get("gerekce", ""),
                 "fallback_var": bool(sp.get("fallback"))}
                for sp in remotion_specleri]
        s.hizli_sahneler.append(hedef)
        s.remotion_sahneler.append(remotion_sahne)

    # ⚠ remotion_props OZGUN sahneleri tasir; hizli_sahneler'i DEGIL.
    s.remotion_props = {
        "fps": fps, "genislik": genislik, "yukseklik": yukseklik,
        "gecis": render_plan.get("gecis_modu") or "sinematik",
        "altyaziStil": render_plan.get("altyazi_stili") or "yok",
        "sahneler": s.remotion_sahneler,
    }
    # Hizli yol icin ayri props (mevcut hizli_render sozlesmesi)
    s.hizli_props = {
        "fps": fps, "genislik": genislik, "yukseklik": yukseklik,
        "gecis": render_plan.get("gecis_modu") or "sinematik",
        "altyaziStil": render_plan.get("altyazi_stili") or "yok",
        "sahneler": s.hizli_sahneler,
    }
    return s


def alan_kaybi_denetimi(hedef_sahne: dict) -> list:
    """Donusum sonrasi BILINEN alanlar duruyor mu? (round-trip guvencesi)"""
    eksik = [a for a in HIZLI_RENDER_ALANLARI
             if a in ("tur", "medya", "ses", "sure", "zoom", "pan", "islev",
                      "efektler", "altyazi", "overlay", "vurgu")
             and a not in hedef_sahne]
    return eksik
