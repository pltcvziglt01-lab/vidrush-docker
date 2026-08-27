#!/usr/bin/env python3
"""HAYALET — CAPCUT: hizalanmis klipleri CapCut zaman cizgisine dizer.

`hayalet.kurgu` her cumleyi TAM suresine getirip ayri bir klip olarak
render eder. Bu modul o klipleri + anlatim sesini bir CapCut TASLAGI
haline getirir: kullanici CapCut'i acar, her cumle zaman cizgisinde ayri
bir parca olarak durur, gecis/yazi/efekt ekleyip elle oynatabilir.

⚠ SEMA BELGELENMIS DEGIL: CapCut'in taslak formati resmi degildir ve
surumden surume degisir. Bu yuzden sema TAHMIN EDILMEZ — kullanicinin
KENDI CapCut'indaki gercek bir projeden "bagisci sablon" olarak
kopyalanir (bkz. `bagisci_bul`). Boylece kurulu surumle birebir uyumlu
nesneler uretilir. Hicbir gercek proje bulunamazsa is BASLAMAZ.

⚠ CAPCUT KAPALI OLMALI: acik CapCut taslak klasorunu kendi hafizasindan
uzerine yazabilir.

Zaman birimi her yerde MIKROSANIYE (int).
"""
from __future__ import annotations

import copy
import json
import shutil
import time
import uuid
from pathlib import Path

# CapCut 9.x (macOS) taslak koku.
TASLAK_KOK = (Path.home() / "Movies" / "CapCut" / "User Data" / "Projects"
              / "com.lveditor.draft")

# Segmentin extra_material_refs'inde gecen yardimci material listeleri.
YARDIMCI = ("speeds", "placeholder_infos", "canvases", "sound_channel_mappings",
            "material_colors", "vocal_separations", "beats")


class CapcutHatasi(RuntimeError):
    """Taslak uretilemez — nedeni mesajda."""


def _kimlik() -> str:
    return str(uuid.uuid4()).upper()


def _us(sn: float) -> int:
    """Saniye -> mikrosaniye (CapCut'in birimi)."""
    return int(round(sn * 1_000_000))


# ─────────────────────────── bagisci sablon ───────────────────────────

def bagisci_bul(kok: Path = TASLAK_KOK) -> dict:
    """Kullanicinin kendi projelerinden sema sablonu cikarir.

    Doner: {"taslak", "video_seg", "audio_seg", "video_mat", "audio_mat",
            "video_iz", "audio_iz", "yardimci": {liste: nesne}}
    """
    if not kok.exists():
        raise CapcutHatasi(f"CapCut taslak klasoru yok: {kok}\n"
                           "CapCut kurulu mu? Bir kez acip proje olusturdun mu?")
    adaylar = sorted(kok.glob("*/draft_info.json"),
                     key=lambda p: p.stat().st_mtime, reverse=True)
    for yol in adaylar:
        try:
            d = json.loads(yol.read_text(encoding="utf-8"))
        except Exception:                                    # noqa: BLE001
            continue
        iz = {t.get("type"): t for t in (d.get("tracks") or [])
              if t.get("segments")}
        if "video" not in iz or "audio" not in iz:
            continue
        vseg = iz["video"]["segments"][0]
        aseg = iz["audio"]["segments"][0]
        mats = d.get("materials") or {}

        def bul(mid):
            for k, v in mats.items():
                if isinstance(v, list):
                    for o in v:
                        if isinstance(o, dict) and o.get("id") == mid:
                            return k, o
            return None, None

        _, vmat = bul(vseg.get("material_id"))
        _, amat = bul(aseg.get("material_id"))
        if not vmat or not amat:
            continue
        yardimci = {}
        for ref in (vseg.get("extra_material_refs") or []) + \
                   (aseg.get("extra_material_refs") or []):
            k, o = bul(ref)
            if k and k not in yardimci:
                yardimci[k] = o
        return {"taslak": d, "yol": yol,
                "video_seg": vseg, "audio_seg": aseg,
                "video_mat": vmat, "audio_mat": amat,
                "video_iz": iz["video"], "audio_iz": iz["audio"],
                "yardimci": yardimci}
    raise CapcutHatasi(
        f"{kok} altinda hem video hem ses izi olan bir CapCut projesi "
        "bulunamadi. Sema bu projelerden kopyalanir — once CapCut'ta bir "
        "videoyu ve bir sesi zaman cizgisine koyup kaydet, sonra tekrar dene.")


# ─────────────────────────── nesne uretimi ───────────────────────────

def _yardimci_uret(sablon: dict, listeler, havuz: dict) -> list:
    """Her segment icin TAZE yardimci material'lar — id'ler paylasilmaz."""
    refs = []
    for ad in listeler:
        proto = sablon["yardimci"].get(ad)
        if proto is None:
            continue
        o = copy.deepcopy(proto)
        o["id"] = _kimlik()
        havuz.setdefault(ad, []).append(o)
        refs.append(o["id"])
    return refs


def _video_ogesi(sablon, havuz, yol: Path, sn: float, basla: int,
                 en: int, boy: int, sira: int) -> dict:
    mat = copy.deepcopy(sablon["video_mat"])
    mat.update({"id": _kimlik(), "path": str(yol.resolve()),
                "material_name": yol.name, "duration": _us(sn),
                "width": en, "height": boy, "has_audio": False,
                "local_material_id": str(uuid.uuid4()),
                "type": "video", "category_name": "local"})
    havuz.setdefault("videos", []).append(mat)

    seg = copy.deepcopy(sablon["video_seg"])
    seg.update({"id": _kimlik(), "material_id": mat["id"],
                "source_timerange": {"start": 0, "duration": _us(sn)},
                "target_timerange": {"start": basla, "duration": _us(sn)},
                "render_index": sira, "track_render_index": 0,
                "volume": 0.0, "speed": 1.0, "keyframe_refs": [],
                "common_keyframes": [], "group_id": "", "template_id": "",
                "extra_material_refs": _yardimci_uret(
                    sablon, ("speeds", "placeholder_infos", "canvases",
                             "sound_channel_mappings", "material_colors",
                             "vocal_separations"), havuz)})
    return seg


def _ses_ogesi(sablon, havuz, yol: Path, sn: float) -> dict:
    mat = copy.deepcopy(sablon["audio_mat"])
    mat.update({"id": _kimlik(), "path": str(yol.resolve()), "name": yol.name,
                "duration": _us(sn), "local_material_id": str(uuid.uuid4()),
                "music_id": str(uuid.uuid4()), "category_name": "local"})
    havuz.setdefault("audios", []).append(mat)

    seg = copy.deepcopy(sablon["audio_seg"])
    seg.update({"id": _kimlik(), "material_id": mat["id"],
                "source_timerange": {"start": 0, "duration": _us(sn)},
                "target_timerange": {"start": 0, "duration": _us(sn)},
                "volume": 1.0, "last_nonzero_volume": 1.0, "speed": 1.0,
                "render_index": 0, "track_render_index": 1,
                "keyframe_refs": [], "common_keyframes": [], "group_id": "",
                "extra_material_refs": _yardimci_uret(
                    sablon, ("speeds", "placeholder_infos", "beats",
                             "sound_channel_mappings", "vocal_separations"),
                    havuz)})
    return seg


# ─────────────────────────── taslak yazimi ───────────────────────────

def taslak_yaz(ad: str, klipler: list, ses: Path, ses_sn: float,
               kok: Path = TASLAK_KOK, en: int = 1920, boy: int = 1080,
               fps: float = 30.0, bildir=print) -> Path:
    """klipler = [(Path, saniye), ...] sirayi KORUR. Taslak klasorunu doner."""
    if not klipler:
        raise CapcutHatasi("Zaman cizgisine dizilecek klip yok.")
    sablon = bagisci_bul(kok)
    bildir(f"Sema sablonu: {sablon['yol'].parent.name} "
           f"(CapCut surumu {sablon['taslak'].get('new_version')})")

    havuz: dict = {}

    klasor = kok / ad
    if klasor.exists():
        raise CapcutHatasi(f"Bu isimde taslak zaten var: {klasor}\n"
                           "Ustune yazmiyorum — baska isim ver.")
    klasor.mkdir(parents=True)

    # ⚠ MEDYA TASLAGIN ICINE KOPYALANIR. CapCut'in ~/Desktop ve ~/Documents
    # gibi TCC korumali klasorlere erisim izni olmayabilir; o zaman klipler
    # zaman cizgisinde "Dosya erisilemiyor" diye kirmizi gorunur. Kendi veri
    # klasorune (~/Movies/CapCut/...) her zaman erisebilir.
    medya_dizin = klasor / "Resources" / "hayalet"
    medya_dizin.mkdir(parents=True)

    def _tasi(kaynak: Path) -> Path:
        hedef = medya_dizin / Path(kaynak).name
        shutil.copy2(kaynak, hedef)
        return hedef

    v_segs, imlec = [], 0
    for i, (yol, sn) in enumerate(klipler):
        v_segs.append(_video_ogesi(sablon, havuz, _tasi(Path(yol)), sn,
                                   imlec, en, boy, i))
        imlec += _us(sn)
    a_seg = _ses_ogesi(sablon, havuz, _tasi(Path(ses)), ses_sn)

    d = copy.deepcopy(sablon["taslak"])
    d["materials"] = {k: ([] if isinstance(v, list) else v)
                      for k, v in (d.get("materials") or {}).items()}
    for k, v in havuz.items():
        d["materials"][k] = v
    v_iz = copy.deepcopy(sablon["video_iz"]); v_iz.update(
        {"id": _kimlik(), "segments": v_segs})
    a_iz = copy.deepcopy(sablon["audio_iz"]); a_iz.update(
        {"id": _kimlik(), "segments": [a_seg]})

    # ⚠ GERCEK PROJELERDE UCU DE AYNI: draft_info.json["id"],
    # Timelines/<UUID> klasor adi ve project.json.main_timeline_id.
    # Farkli olurlarsa CapCut projeyi listeler ama ACMAZ (sessizce).
    zc_id = _kimlik()
    taslak_id = _kimlik()          # draft_meta_info.json'daki ayri kimlik
    simdi = int(time.time() * 1_000_000)
    d.update({
        "id": zc_id, "name": ad, "tracks": [v_iz, a_iz],
        "duration": max(imlec, _us(ses_sn)), "fps": fps,
        "canvas_config": {"ratio": "original", "width": en, "height": boy,
                          "background": None},
        "create_time": simdi, "update_time": simdi,
        "keyframes": {k: [] for k in (d.get("keyframes") or {})},
        "keyframe_graph_list": [], "relationships": [], "time_marks": None,
        "group_container": None, "cover": None, "retouch_cover": None,
        "static_cover_image_path": "", "path": str(klasor.resolve()),
        "platform": d.get("platform"), "draft_type": "",
    })

    (klasor / "draft_info.json").write_text(
        json.dumps(d, ensure_ascii=False), encoding="utf-8")
    # CapCut 9.x taslagi ayrica Timelines/<UUID>/ altinda AYNISINI tutar,
    # ve project.json + timeline_layout.json bu UUID'ye ISARET ETMELIDIR —
    # bagiscininki oldugu gibi kopyalanirsa proje ACILMAZ.
    zc_ad = "Zaman çizelgesi 01"
    zc = klasor / "Timelines" / zc_id
    zc.mkdir(parents=True)
    (zc / "draft_info.json").write_text(
        json.dumps(d, ensure_ascii=False), encoding="utf-8")
    (klasor / "Timelines" / "project.json").write_text(json.dumps({
        "config": {"color_space": -1, "mixed_track_mode_on": False,
                   "render_index_track_mode_on": False,
                   "use_float_render": False},
        "create_time": simdi, "update_time": simdi, "version": 0,
        "id": _kimlik(), "main_timeline_id": zc_id,
        "timelines": [{"create_time": simdi, "update_time": simdi,
                       "id": zc_id, "is_marked_delete": False,
                       "name": zc_ad}],
    }, ensure_ascii=False), encoding="utf-8")
    (klasor / "timeline_layout.json").write_text(json.dumps({
        "dockItems": [{"dockIndex": 0, "ratio": 1, "timelineIds": [zc_id],
                       "timelineNames": [zc_ad]}],
        "layoutOrientation": 1}, ensure_ascii=False), encoding="utf-8")
    (klasor / "draft_virtual_store.json").write_text(
        json.dumps({"draft_materials": [], "draft_virtual_store": []}),
        encoding="utf-8")

    # Proje listesinde gorunmesi icin kunye — bagiscininki uyarlanir.
    kunye_yolu = sablon["yol"].parent / "draft_meta_info.json"
    if kunye_yolu.exists():
        k = json.loads(kunye_yolu.read_text(encoding="utf-8"))
        k.update({"draft_id": taslak_id, "draft_name": ad,
                  "draft_fold_path": str(klasor.resolve()),
                  "draft_root_path": str(kok.resolve()),
                  "draft_timeline_materials_size_": 0,
                  "tm_duration": d["duration"],
                  "draft_new_version": "",
                  "tm_draft_create": simdi, "tm_draft_modified": simdi,
                  "draft_removable_storage_device": "",
                  "draft_cover": "draft_cover.jpg"})
        k["draft_materials"] = [{"type": t, "value": []} for t in
                                (0, 1, 2, 3, 6, 7, 8)]
        (klasor / "draft_meta_info.json").write_text(
            json.dumps(k, ensure_ascii=False), encoding="utf-8")
    for yan in ("draft_agency_config.json", "draft_settings",
                "performance_opt_info.json"):
        kaynak = sablon["yol"].parent / yan
        if kaynak.exists():
            shutil.copy2(kaynak, klasor / yan)

    bildir(f"✓ CapCut taslagi: {klasor}")
    bildir(f"  {len(v_segs)} klip + 1 ses izi, "
           f"{d['duration'] / 1_000_000:.1f} sn")
    bildir("  CapCut'i KAPATIP tekrar ac — proje listesinde gorunur.")
    return klasor
