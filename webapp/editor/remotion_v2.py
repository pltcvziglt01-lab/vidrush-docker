"""FAZ C render_plan -> VidrushEditorV2 REMOTION RENDER kopruleri.

⚠ MEVCUT RENDER YOLUNA DOKUNMUYOR. `pipeline.py` hala `VidrushVideo`
kompozisyonunu cagiriyor; bu modul YALNIZCA acikca cagrildiginda
`VidrushEditorV2`'yi render eder (opt-in).

Iki isi var:
  1. `props_hazirla()` — adapter'in urettigi remotion_props'u Remotion'un
     bekledigi bicime getirir: medya yollarini `public/` altina kopyalar
     (Remotion `staticFile` ya da mutlak dosya yolu ister) ve parallax katman
     gorsellerini baglar.
  2. `render()` — `npx remotion render src/index.ts VidrushEditorV2` kosar.

Ayrica `destek_matrisi_oku()`: TypeScript'teki DESTEK_MATRISI'ni Python'a okur.
Boylece Faz C motion.py ile TS matrisi arasindaki sapma TEST EDILEBILIR —
"beyan var ama render yok" durumunun tekrarlanmamasi icin.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from typing import Callable, Optional

# Remotion projesinin koku (webapp/editor/ -> ../../app/render-studio)
STUDIO = os.path.normpath(os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "app", "render-studio"))
SOZLESME_TS = os.path.join(STUDIO, "src", "editorv2", "sozlesme.ts")
KOMPOZISYON = "VidrushEditorV2"


def destek_matrisi_oku(yol: str = SOZLESME_TS) -> dict:
    """TypeScript DESTEK_MATRISI'ni ayikla -> {spec_adi: durum}.

    Basit ayristirma: `'ad': {durum: 'gercek'...}` satirlarini yakalar.
    Amac tam TS parse etmek degil, iki tarafin AYNI spec kumesini bilmesini
    dogrulamak."""
    try:
        with open(yol, encoding="utf-8") as f:
            metin = f.read()
    except Exception:
        return {}
    i = metin.find("DESTEK_MATRISI")
    if i < 0:
        return {}
    j = metin.find("export const DESTEKLENEN_SPECLER", i)
    blok = metin[i:j if j > 0 else len(metin)]
    out = {}
    # "'ad':" veya "ad:" ardindan durum: 'x'
    for m in re.finditer(r"(?:'([a-z0-9.\-]+)'|^\s{2}([a-zA-Z][a-zA-Z0-9]*)):\s*\{"
                         r"[^}]*?durum:\s*'([a-z\-]+)'", blok, re.M | re.S):
        ad = m.group(1) or m.group(2)
        out[ad] = m.group(3)
    return out


def dogrula(remotion_props: dict, matris: Optional[dict] = None) -> dict:
    """PRE-RENDER KAPISI — `sozlesme.ts` icindeki `dogrula()`'nin Python aynasi.

    ⚠ NEDEN PYTHON TARAFINDA DA VAR:
    TS validator kompozisyonun ICINDE kosuyor. Orada FAIL uretse bile Remotion
    hata ekranini RENDER EDIP normal bitiyor ve `npx remotion render` rc=0
    donuyor. Yani TS validator bir "engel" degil, sadece ekrana basilan bir
    tesbit. Cagiran taraf (CLI, pipeline, test) rc=0 gorup "render basarili"
    sanabilir ve icinde hata ekrani olan bir videoyu teslim eder.

    Bu fonksiyon gercek engeli kuruyor: bilinmeyen ya da desteklenmeyen spec
    varsa `render()` npx'i HIC cagirmaz, props dosyasini bile YAZMAZ.

    Kod adlari TS ile AYNI tutuluyor (V2-...): iki tarafta ayni sorun ayni
    isimle raporlanmali, yoksa hangi kapinin durdurdugu anlasilmaz.
    """
    matris = matris if matris is not None else destek_matrisi_oku()
    sorunlar: list = []
    say = {"gercek": 0, "pseudo": 0, "ffmpeg-yolu": 0, "bilinmeyen": 0,
           "desteklenmiyor": 0}
    spec_sayisi = 0

    def _ekle(kod, seviye, sid, bid, spec, detay):
        sorunlar.append({"kod": kod, "seviye": seviye, "scene_id": sid,
                         "beat_id": bid, "spec": spec, "detay": detay})

    # Destek matrisi okunamadiysa hicbir spec dogrulanamaz — sessizce
    # "hepsi bilinmeyen" demek yerine ayri bir FAIL veriyoruz ki sebep belli olsun
    if not matris:
        _ekle("V2-MATRIS-OKUNAMADI", "fail", "", "", "",
              f"destek matrisi bos/okunamadi: {SOZLESME_TS}")

    sahneler = remotion_props.get("sahneler") or []
    if not sahneler:
        _ekle("V2-SAHNE-YOK", "fail", "", "", "", "props.sahneler bos")

    for i, sh in enumerate(sahneler):
        sid = sh.get("scene_id") or f"#{i}"
        bid = sh.get("beat_id") or f"#{i}"
        if not sh.get("beat_id") or not sh.get("scene_id"):
            _ekle("V2-IZLENEBILIRLIK", "fail", sid, bid, "",
                  "beat_id/scene_id zorunlu (izlenebilirlik)")
        try:
            sure = float(sh.get("sure") or 0)
        except (TypeError, ValueError):
            sure = 0.0
        if not sure > 0:
            _ekle("V2-SURE", "fail", sid, bid, "",
                  f"sure={sh.get('sure')} (>0 olmali)")
        if not sh.get("medya") and sh.get("tur") != "image":
            _ekle("V2-MEDYA-YOK", "warn", sid, bid, "",
                  "medya yolu bos — sentetik zemin cizilecek")

        for sp in sh.get("motion") or []:
            spec_sayisi += 1
            ad = sp.get("ad") or ""
            durum = matris.get(ad)
            if durum is None:
                say["bilinmeyen"] += 1
                _ekle("V2-BILINMEYEN-SPEC", "fail", sid, bid, ad,
                      f"'{ad}' destek matrisinde YOK — sessizce dusmemesi icin "
                      "render engellendi. Bilesen ekleyin ya da spec adini duzeltin.")
                continue
            if durum == "gercek":
                say["gercek"] += 1
            elif durum == "pseudo":
                say["pseudo"] += 1
                _ekle("V2-PSEUDO", "bilgi", sid, bid, ad, "yaklastirildi")
            elif durum == "ffmpeg-yolu":
                say["ffmpeg-yolu"] += 1
            else:                       # desteklenmiyor
                say["desteklenmiyor"] += 1
                _ekle("V2-DESTEKLENMIYOR", "fail", sid, bid, ad,
                      "bilincli kapsam disi — render engellendi")
            bez = sp.get("easing_bezier")
            if not isinstance(bez, (list, tuple)) or len(bez) != 4:
                _ekle("V2-EASING", "warn", sid, bid, ad,
                      "easing_bezier 4 elemanli olmali; lineere dusulecek")

    durum = ("FAIL" if any(s["seviye"] == "fail" for s in sorunlar)
             else "WARN" if any(s["seviye"] == "warn" for s in sorunlar)
             else "PASS")
    return {"durum": durum, "sorunlar": sorunlar,
            "ozet": {"sahne": len(sahneler), "spec": spec_sayisi, **say}}


def props_hazirla(remotion_props: dict, *, calisma_dizin: str,
                  varlik_haritasi: Optional[dict] = None,
                  parallax_haritasi: Optional[dict] = None) -> dict:
    """Medya yollarini Remotion'un okuyabilecegi hale getir.

    Remotion tarayicida kosuyor: `public/` altindaki dosyalara `staticFile()`
    ile, disaridakilere `file://` ile erisilir. En guvenli yol varliklari
    `public/editorv2/<is>/` altina kopyalamak.
    """
    varlik_haritasi = varlik_haritasi or {}
    parallax_haritasi = parallax_haritasi or {}
    hedef_dizin = os.path.join(STUDIO, "public", "editorv2", os.path.basename(
        calisma_dizin.rstrip("/")) or "is")
    os.makedirs(hedef_dizin, exist_ok=True)
    goreli_kok = os.path.relpath(hedef_dizin, os.path.join(STUDIO, "public"))

    props = json.loads(json.dumps(remotion_props))   # derin kopya
    for sh in props.get("sahneler") or []:
        aid = sh.get("asset_id") or ""
        kaynak = varlik_haritasi.get(aid) or sh.get("medya") or ""
        if kaynak and os.path.exists(kaynak):
            ad = f"{aid or sh.get('beat_id')}{os.path.splitext(kaynak)[1] or '.jpg'}"
            hedef = os.path.join(hedef_dizin, ad)
            if not os.path.exists(hedef):
                shutil.copy(kaynak, hedef)
            sh["medya"] = f"{goreli_kok}/{ad}".replace(os.sep, "/")
        else:
            sh["medya"] = ""
        kat = parallax_haritasi.get(aid) or []
        if kat:
            yollar = []
            for k, ky in enumerate(kat):
                if not os.path.exists(ky):
                    continue
                ad = f"{aid}_k{k}{os.path.splitext(ky)[1] or '.jpg'}"
                hedef = os.path.join(hedef_dizin, ad)
                if not os.path.exists(hedef):
                    shutil.copy(ky, hedef)
                yollar.append(f"{goreli_kok}/{ad}".replace(os.sep, "/"))
            if yollar:
                sh["parallax_katmanlari"] = yollar
    return props


def render(props: dict, cikti: str, *, olcu: tuple = (1280, 720),
           fps: int = 30, crf: int = 20, concurrency: int = 2,
           zaman_asimi: int = 900,
           kosucu: Optional[Callable] = None) -> dict:
    """VidrushEditorV2'yi render et.

    ⚠ PRE-RENDER KAPISI: `dogrula()` FAIL verirse npx/kosucu HIC cagrilmaz,
    props dosyasi bile YAZILMAZ ve rc!=0 doner. Sebep: TS validator kompozisyon
    icinde kosuyor, FAIL'de bile hata ekranini render edip rc=0 dondurebiliyor —
    yani kendi basina bir engel degil. Kapiyi cagiran taraf kurmak zorunda.

    Doner: {"rc","durum","sorunlar","sure_sn","komut","stderr","cikti","var_mi"}
    """
    import time

    # ── KAPI: her seyden ONCE, hicbir yan etki olmadan ──
    kontrol = dogrula(props)
    if kontrol["durum"] == "FAIL":
        engel = [s for s in kontrol["sorunlar"] if s["seviye"] == "fail"]
        return {
            "rc": 1,                        # CLI icin basarisiz
            "durum": "FAIL",
            "sorunlar": kontrol["sorunlar"],
            "ozet": kontrol["ozet"],
            "sure_sn": 0.0,
            "komut": None,                  # npx CAGRILMADI
            "stderr": "; ".join(f"{s['kod']} [{s['scene_id']}/{s['beat_id']}] "
                                f"{s['spec']}: {s['detay']}" for s in engel[:8]),
            "cikti": cikti,
            "var_mi": False,
        }

    os.makedirs(os.path.dirname(os.path.abspath(cikti)) or ".", exist_ok=True)
    props_yolu = os.path.join(STUDIO, "public", "editorv2", "props.json")
    os.makedirs(os.path.dirname(props_yolu), exist_ok=True)
    props = dict(props)
    props["genislik"], props["yukseklik"] = int(olcu[0]), int(olcu[1])
    props["fps"] = int(fps)
    with open(props_yolu, "w", encoding="utf-8") as f:
        json.dump(props, f, ensure_ascii=False)

    komut = ["npx", "remotion", "render", "src/index.ts", KOMPOZISYON, cikti,
             f"--props={props_yolu}", f"--concurrency={concurrency}",
             f"--crf={crf}", "--log=error"]
    for ev, bayrak in (("REMOTION_BROWSER_EXECUTABLE", "--browser-executable="),
                       ("REMOTION_GL", "--gl=")):
        if os.environ.get(ev):
            komut.append(bayrak + os.environ[ev])

    t0 = time.time()
    if kosucu is not None:
        r = kosucu(komut, zaman_asimi)
    else:
        try:
            p = subprocess.run(komut, cwd=STUDIO, capture_output=True, text=True,
                               timeout=zaman_asimi)
            r = {"rc": p.returncode, "stdout": p.stdout or "",
                 "stderr": p.stderr or ""}
        except Exception as e:
            r = {"rc": -1, "stdout": "", "stderr": str(e)[:400]}
    rc = r.get("rc")
    return {"rc": rc,
            "durum": kontrol["durum"] if rc == 0 else "RENDER-HATASI",
            "sorunlar": kontrol["sorunlar"],
            "ozet": kontrol["ozet"],
            "sure_sn": round(time.time() - t0, 1),
            "komut": " ".join(komut[:6]) + " ...",
            "stderr": (r.get("stderr") or "")[-1200:],
            "cikti": cikti, "var_mi": os.path.exists(cikti)}


def uygulanan_atlanan(remotion_props: dict, matris: Optional[dict] = None) -> dict:
    """Kac spec GERCEKTEN uygulandi, kaci yaklastirildi, kaci atlandi."""
    matris = matris if matris is not None else destek_matrisi_oku()
    say = {"gercek": 0, "pseudo": 0, "ffmpeg-yolu": 0, "bilinmeyen": 0}
    detay: dict = {}
    for sh in remotion_props.get("sahneler") or []:
        for sp in sh.get("motion") or []:
            ad = sp.get("ad") or ""
            durum = matris.get(ad, "bilinmeyen")
            if durum not in say:
                durum = "bilinmeyen"
            say[durum] += 1
            detay.setdefault(durum, {}).setdefault(ad, 0)
            detay[durum][ad] += 1
    say["toplam"] = sum(v for k, v in say.items() if k != "toplam")
    return {"sayim": say, "detay": detay}
