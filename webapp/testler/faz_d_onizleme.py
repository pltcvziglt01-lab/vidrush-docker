#!/usr/bin/env python3
"""FAZ D GERCEK REMOTION ONIZLEMESI — VidrushEditorV2 ile piksel uretir.

Kullanicinin sarti: 20-30 sn, 720p, EN AZ 7 farkli gorsel segment, ilk 8 sn
hook, ve su bilesenler GORUNUR olmali:
  parallax · light-sweep · document-highlight · data-chart · map-route ·
  lower-third · source-label

ANLATIM (seslendirme) YOKTUR — bu bir MOTION onizlemesidir. Ses/anlatim
olmadan "profesyonel icerik kalitesi" iddiasi edilmez.

Medya: cevrimici indirme YOK. Yerel olcum kareleri varsa onlar kullanilir,
yoksa ffmpeg ile sentetik ama BELGESEL TONUNDA (dusuk doygunluk, film grain
yok — onu Remotion katmani ekler) zemin uretilir.

Kosum:
  python3 webapp/testler/faz_d_onizleme.py [--olcu 1280x720] [--tavan-dk 15]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import subprocess
import sys
import time

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)

from editor import adapter, motion, profil, remotion_v2  # noqa: E402

CIKTI_DIZIN = os.path.join(os.path.dirname(KOK), "cikti", "faz_d")
P = profil.profil("premium-modern")


# ═══════════════ zemin gorselleri ═══════════════

def _yerel_kareler(adet: int) -> list:
    """Daha once olculen referans karelerini kullan (yeniden indirme YOK)."""
    desenler = [
        os.path.join(os.path.dirname(KOK), "referans", "**", "*.jpg"),
        os.path.join(os.path.dirname(KOK), "olcum", "**", "*.jpg"),
        os.path.join(os.path.dirname(KOK), "cikti", "**", "kare_*.jpg"),
    ]
    bulunan: list = []
    for d in desenler:
        for y in sorted(glob.glob(d, recursive=True)):
            # ⚠ GERI BESLEME ENGELI: onceki kosunun QA kareleri zemin olarak
            # geri girmemeli. Bir kez oldu (11 Agu) ve zeminler kendi
            # cikitisinin ekran goruntusu haline geldi.
            if os.path.abspath(CIKTI_DIZIN) in os.path.abspath(y):
                continue
            if os.path.getsize(y) > 40_000:
                bulunan.append(y)
            if len(bulunan) >= adet:
                return bulunan
    return bulunan


def _sentetik_zemin(dizin: str, indeks: int, etiket: str) -> str:
    """Belgesel tonunda zemin: DUSUK DOYGUNLUK.

    ⚠ Ilk surumde `geq` ile kanal basina sinus ekledim ve doygun kirmizi/mavi
    bloblar cikti (kontak sayfasi olcumu): belgesel tonunun tam tersi. Sebep,
    taban rengin karanlik olmasi — sinus terimi tek kanali doyuruyor. Cozum:
    gradyan + gurultu URET, sonra `hue=s=` ile doygunlugu ZORLA kis ve
    `eq` ile parlakligi belgesel araligina cek.

    Yazi YOK: yerel ffmpeg'de drawtext bulunmuyor (11 Agu olcumu).
    """
    yol = os.path.join(dizin, f"zemin_{indeks:02d}.jpg")
    if os.path.exists(yol):
        return yol
    # Nötr-koyu taban tonlari (mavi-gri / kahve-gri): grade sonrasi belgesel
    tonlar = ["0x5c6672", "0x6b6354", "0x54606d", "0x6d605c",
              "0x5a6664", "0x6b6654", "0x4f5a67", "0x685e5a"]
    renk = tonlar[indeks % len(tonlar)]
    # Her segment farkli bir gradyan yonu: kamera hareketi olcumu icin
    # zeminde farkli parlaklik dagilimi gerekiyor
    yon = ["X", "Y", "X+Y", "X-Y"][indeks % 4]   # geq BUYUK harf ister
    komut = [
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", f"color=c={renk}:s=2560x1440",
        "-f", "lavfi", "-i", f"nullsrc=s=2560x1440,noise=alls=34:allf=t+u",
        "-filter_complex",
        # 1) gradyan: tek kanal degil PARLAKLIK degisimi (doygunluk artmaz)
        f"[0:v]geq=lum='lum(X,Y)+34*sin(({yon})/520+{indeks})':"
        f"cb='cb(X,Y)':cr='cr(X,Y)'[grad];"
        # 2) gurultu: film dokusu degil, yuzey kirliligi (grain'i Remotion ekler)
        "[1:v]format=gray,scale=2560:1440[gur];"
        "[grad][gur]blend=all_mode=overlay:all_opacity=0.16,"
        # 3) DOYGUNLUGU KIS + belgesel parlaklik araligi
        "hue=s=0.34,eq=brightness=0.02:contrast=1.04:saturation=0.9,"
        # vignette=PI/5 kenarlari siyaha cakiyordu (olculdu): PI/9 yeterli
        "vignette=PI/9,format=yuvj420p[v]",
        "-map", "[v]", "-frames:v", "1", "-q:v", "3", yol,
    ]
    r = subprocess.run(komut, capture_output=True, text=True, timeout=180)
    if r.returncode != 0 or not os.path.exists(yol):
        raise RuntimeError(f"sentetik zemin uretilemedi: {r.stderr[-300:]}")
    return yol


# ═══════════════ sahne plani ═══════════════
# 8 segment: hook(2) + kanit + veri + harita + belge + kapanis
# Sureler 8 sn tavanini ASMAZ (kullanicinin kalici kurali).

SEGMENTLER = [
    # (islev, cekim, hareket, kadraj, sure, baslik, altbant, ekstra)
    #
    # ⚠ TEMPO NOTU: toplam 27.8 sn (sart: 20-30 sn). Ortalama cekim 3.5 sn,
    # yani UYGULAMADA hedeflenen 6.5 sn medyanin ALTINDA. Bu bilincli:
    # onizlemenin isi 8 farkli bileseni 30 sn'ye sigdirmak. Uretim temposu
    # bu dosyadan degil `beat.py`/`gramer.py`'den gelir — buradaki sureler
    # belgesel tempo referansi DEGILDIR.
    ("hook",     "wide",      "push-in",    "genis", 3.2,
     "TOKYO'DA SESSIZ BIR KRIZ", None, ("kinetic-title", "light-sweep")),
    ("hook",     "detail",    "soft-zoom",  "yakin", 3.0,
     None, ("KODOKUSHI", "YALNIZ OLUM"), ("text-in-video",)),
    ("baglam",   "wide",      "pan-right",  "genis", 4.0,
     None, ("TOKIWADAIRA", "CHIBA"), ("parallax-2.5d",)),
    ("kanit",    "archive",   "static",     "tam",   3.6,
     None, None, ("document-highlight",)),
    ("veri",     "data",      "static",     "tam",   4.0,
     None, None, ("data-chart",)),
    ("baglam",   "map",       "static",     "tam",   3.4,
     None, None, ("map-route",)),
    ("kanit",    "detail",    "pull-out",   "orta",  3.2,
     None, ("2024 VERISI", "ULUSAL POLIS AJANSI"), ("light-sweep",)),
    ("kapanis",  "wide",      "slow-drift", "genis", 3.4,
     "SORU HALA CEVAPSIZ", None, ("film-burn",)),
]


def _sahne_uret(zeminler: list) -> dict:
    sahneler = []
    t = 0.0
    for i, (islev, cekim, hareket, kadraj, sure, baslik, bant, ekstra) in \
            enumerate(SEGMENTLER):
        specler = []

        # Kamera
        specler.append(motion.kamera_spec(hareket, sure, kadraj, p=P))
        # Taban doku katmanlari (grain/vinyet/grade)
        specler.extend(motion.taban_katmanlar(sure, p=P))
        # Kaynak etiketi HER sahnede (telif/atif zorunlulugu)
        specler.append(motion.kaynak_etiketi_spec(
            "WIKIMEDIA COMMONS · CC BY-SA", f"f{i:03d}", sure, p=P))

        if baslik:
            if "kinetic-title" in ekstra:
                specler.append(motion._spec(
                    "kinetic-title",
                    parametre={"metin": baslik, "punto": 74, "y_orani": 0.60,
                               "bant_opaklik": 0.55},
                    easing="giris", bas_sn=0.3,
                    sure_sn=min(sure - 0.4, 3.2), katman=60,
                    fallback={"ad": "chapter-title", "renderer": "ffmpeg",
                              "parametre": {"metin": baslik, "punto": 74,
                                            "y_orani": 0.60}},
                    gerekce="hook: kelime kelime giris dikkati tutar"))
            else:
                specler.append(motion.bolum_basligi_spec(baslik, sure, p=P))
        if bant:
            specler.append(motion.alt_band_spec(bant[0], bant[1], sure, p=P))

        for e in ekstra:
            if e == "parallax-2.5d":
                specler.append(motion.parallax_spec(3, sure, p=P))
            elif e == "light-sweep":
                specler.append(motion.light_sweep_spec(0.85))
            elif e == "film-burn":
                specler.append(motion.film_burn_spec())
            elif e == "document-highlight":
                specler.append(motion.belge_vurgusu_spec(
                    (0.26, 0.34, 0.44, 0.16), sure))
            elif e == "data-chart":
                specler.append(motion.veri_grafigi_spec(
                    "YALNIZ OLUM VAKALARI", [76941, 68000, 54000, 41000], sure))
            elif e == "map-route":
                specler.append(motion.harita_spec("TOKYO", "CHIBA", sure))
            elif e == "text-in-video":
                specler.append(motion._spec(
                    "text-in-video",
                    parametre={"metin": "KODOKUSHI", "punto": 52,
                               "x_orani": 0.5, "y_orani": 0.40,
                               "bant_opaklik": 0.45},
                    easing="giris", bas_sn=0.5,
                    sure_sn=min(sure - 0.8, 2.4), katman=61,
                    fallback={"ad": "lower-third", "renderer": "ffmpeg",
                              "parametre": {"ust": "KODOKUSHI", "alt": ""}},
                    gerekce="yazi kamerayla hareket eder: goruntuye kilitli"))

        # Gecis: ilk 8 sn'de HARD-CUT (hook temposu), sonra degisken
        gecis = "hard-cut" if i < 2 else (
            "karartma" if islev == "kapanis" else
            ("crossfade" if i % 3 == 0 else "hard-cut"))
        specler.append(motion.gecis_spec(gecis))

        for sp in specler:
            sp.beat_id = f"bD{i:02d}"
            sp.scene_id = f"sD{i:02d}"

        zemin = zeminler[i % len(zeminler)] if zeminler else ""
        sahneler.append({
            "beat_id": f"bD{i:02d}", "scene_id": f"sD{i:02d}",
            "fact_id": f"f{i:03d}", "asset_id": f"aD{i:02d}",
            "saglayici": "wikimedia", "lisans": "cc-by-sa",
            "medya_turu": "image", "medya_yolu": zemin,
            "sure_sn": sure, "bas_sn": round(t, 2), "islev": islev,
            "perde": "acilis" if i < 2 else ("kapanis" if i == 7 else "gelisme"),
            "cekim_turu": cekim, "hareket": hareket, "kadraj": kadraj,
            "kaynak_aralik": [0, sure], "j_cut": False, "l_cut": i == 6,
            "altyazi": [], "motion": [s.sozluk() for s in specler],
            "gerekce": f"{islev}/{cekim}",
        })
        t += sure

    return {"fps": 30, "genislik": 1920, "yukseklik": 1080,
            "gecis_modu": "sinematik", "altyazi_stili": "yok",
            "sahneler": sahneler}


# ═══════════════ QA ═══════════════

def _ffprobe(yol: str) -> dict:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_format", "-show_streams",
         "-of", "json", yol], capture_output=True, text=True, timeout=120)
    return json.loads(r.stdout or "{}")


def _tespit(yol: str) -> dict:
    """Siyah kare / donmus kare taramasi (kalici QA kurali)."""
    r = subprocess.run(
        ["ffmpeg", "-v", "info", "-i", yol,
         "-vf", "blackdetect=d=0.15:pic_th=0.98,freezedetect=n=0.001:d=1.0",
         "-f", "null", "-"], capture_output=True, text=True, timeout=600)
    log = r.stderr or ""
    siyah = [l.strip() for l in log.splitlines() if "black_start" in l]
    donma = [l.strip() for l in log.splitlines() if "freeze_start" in l]
    return {"siyah": siyah, "donma": donma}


def _kontak_sayfa(yol: str, hedef: str, adet: int = 24) -> str:
    sure = float(_ffprobe(yol).get("format", {}).get("duration") or 0) or 1
    r = subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", yol, "-vf",
         f"fps={adet / sure:.4f},scale=426:-1,tile=6x4", "-frames:v", "1",
         "-q:v", "3", hedef], capture_output=True, text=True, timeout=600)
    return hedef if r.returncode == 0 and os.path.exists(hedef) else ""


def _kareler(yol: str, dizin: str, saniyeler: list) -> list:
    os.makedirs(dizin, exist_ok=True)
    out = []
    for sn in saniyeler:
        h = os.path.join(dizin, f"kare_{sn:05.1f}.jpg")
        r = subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-ss", str(sn), "-i", yol,
             "-frames:v", "1", "-q:v", "2", h],
            capture_output=True, text=True, timeout=180)
        if r.returncode == 0 and os.path.exists(h):
            out.append(h)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--olcu", default="1280x720")
    ap.add_argument("--tavan-dk", type=float, default=15.0)
    a = ap.parse_args()
    g, y = (int(x) for x in a.olcu.lower().split("x"))
    os.makedirs(CIKTI_DIZIN, exist_ok=True)
    zemin_dizin = os.path.join(CIKTI_DIZIN, "zemin")
    os.makedirs(zemin_dizin, exist_ok=True)

    print("═" * 62)
    print("FAZ D ONIZLEME — VidrushEditorV2 (ANLATIM YOK, sadece motion)")
    print("═" * 62)

    # 1) Zeminler
    zeminler = _yerel_kareler(len(SEGMENTLER))
    kaynak = "yerel referans kareleri"
    if len(zeminler) < len(SEGMENTLER):
        print(f"  yerel kare: {len(zeminler)} — eksik kalan sentetik uretilecek")
        for i in range(len(zeminler), len(SEGMENTLER)):
            zeminler.append(_sentetik_zemin(zemin_dizin, i, f"SEG{i}"))
        kaynak = f"{len(_yerel_kareler(len(SEGMENTLER)))} yerel + sentetik"
    print(f"  zemin kaynagi: {kaynak}")

    # 2) Plan -> adapter
    rp = _sahne_uret(zeminler)
    don = adapter.donustur(rp)
    props = don.remotion_props
    varlik = {sh["asset_id"]: sh["medya_yolu"] for sh in rp["sahneler"]}
    hazir = remotion_v2.props_hazirla(props, calisma_dizin=CIKTI_DIZIN,
                                      varlik_haritasi=varlik)
    hazir["hatalariGoster"] = False

    # PRE-RENDER KAPISI — render() de bunu kosuyor; burada RAPORLAMAK icin
    # cagiriyoruz ki hangi sorunun durdurdugu ekrana yazilsin.
    kapi = remotion_v2.dogrula(props)
    print(f"  pre-render kapisi: {kapi['durum']}")
    for so in kapi["sorunlar"]:
        if so["seviye"] == "fail":
            print(f"    ✖ {so['kod']} [{so['scene_id']}] {so['spec']}: {so['detay']}")
    if kapi["durum"] == "FAIL":
        print("  ✖ KAPI DURDURDU — npx cagrilmayacak")
        return 2

    say = remotion_v2.uygulanan_atlanan(props)
    print(f"  sahne: {len(props['sahneler'])}   spec: {say['sayim']['toplam']}")
    print(f"  gercek={say['sayim']['gercek']} pseudo={say['sayim']['pseudo']} "
          f"ffmpeg-yolu={say['sayim']['ffmpeg-yolu']} "
          f"bilinmeyen={say['sayim']['bilinmeyen']}")
    beklenen = {"parallax-2.5d", "light-sweep", "document-highlight",
                "data-chart", "map-route", "lower-third", "source-label"}
    var = {sp["ad"] for sh in props["sahneler"] for sp in sh["motion"]}
    eksik = sorted(beklenen - var)
    print(f"  zorunlu bilesenler: {'TAMAM' if not eksik else 'EKSIK ' + str(eksik)}")

    plan_yolu = os.path.join(CIKTI_DIZIN, "props.json")
    with open(plan_yolu, "w", encoding="utf-8") as f:
        json.dump(hazir, f, ensure_ascii=False, indent=1)

    # 3) Render
    cikti = os.path.join(CIKTI_DIZIN, "faz_d_onizleme.mp4")
    print(f"\n  render basliyor ({g}x{y}, tavan {a.tavan_dk} dk)…")
    t0 = time.time()
    r = remotion_v2.render(hazir, cikti, olcu=(g, y), fps=30,
                           zaman_asimi=int(a.tavan_dk * 60))
    print(f"  rc={r['rc']}  durum={r.get('durum')}  sure={r['sure_sn']} sn")
    if r["rc"] != 0 or not os.path.exists(cikti):
        print("  ✖ RENDER BASARISIZ")
        print("  stderr:", r["stderr"][-900:])
        return 3

    # 4) QA
    pr = _ffprobe(cikti)
    v = next((s for s in pr.get("streams", []) if s.get("codec_type") == "video"), {})
    sure = float(pr.get("format", {}).get("duration") or 0)
    print(f"\n  ── QA ──")
    print(f"  cozunurluk: {v.get('width')}x{v.get('height')}  "
          f"fps: {v.get('r_frame_rate')}  sure: {sure:.2f} sn")
    print(f"  boyut: {os.path.getsize(cikti) / 1e6:.1f} MB")
    t = _tespit(cikti)
    print(f"  siyah kare: {len(t['siyah'])}   donmus blok: {len(t['donma'])}")
    for l in t["siyah"][:4]:
        print(f"    {l}")
    for l in t["donma"][:4]:
        print(f"    {l}")

    ks = _kontak_sayfa(cikti, os.path.join(CIKTI_DIZIN, "kontak_sayfa.jpg"))
    kare_dizin = os.path.join(CIKTI_DIZIN, "kareler")
    ornek = [1.0, 3.0, 5.0, 7.5, 10.0, 13.5, 17.0, 21.0, 25.5, 29.0, 33.0]
    kareler = _kareler(cikti, kare_dizin, [s for s in ornek if s < sure])

    rapor = {
        "cikti": os.path.abspath(cikti),
        "props": os.path.abspath(plan_yolu),
        "kontak_sayfa": os.path.abspath(ks) if ks else None,
        "kareler": [os.path.abspath(k) for k in kareler],
        "render_sure_sn": r["sure_sn"],
        "olcu": f"{v.get('width')}x{v.get('height')}",
        "sure_sn": round(sure, 2),
        "segment": len(props["sahneler"]),
        "spec_sayimi": say["sayim"],
        "spec_detay": say["detay"],
        "eksik_bilesen": eksik,
        "siyah_kare": t["siyah"],
        "donmus_blok": t["donma"],
        "anlatim": "YOK — bu motion onizlemesidir, icerik kalitesi iddiasi yok",
    }
    rp_yolu = os.path.join(CIKTI_DIZIN, "rapor.json")
    with open(rp_yolu, "w", encoding="utf-8") as f:
        json.dump(rapor, f, ensure_ascii=False, indent=1)
    print(f"\n  rapor: {os.path.abspath(rp_yolu)}")
    print(f"  video: {os.path.abspath(cikti)}")
    if ks:
        print(f"  kontak sayfa: {os.path.abspath(ks)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
