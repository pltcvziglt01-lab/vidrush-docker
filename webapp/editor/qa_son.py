"""POST-RENDER QA — bitmis dosyayi GERCEK ffprobe/ffmpeg ile olcer.

Komutlar gercekten kosar; testlerde `kosucu` enjekte edilip fixture cikti
verilir. Boylece hem gercek kullanimda olcum yapiliyor hem testler agsiz/
ffmpeg'siz kosuyor.

Olculenler ve NEDEN (hepsi 11 Agu'da canli videoda yasanan sorunlar):
  - cozunurluk/fps/sure : plan ile cikti uyusmuyorsa sessiz kayip var
  - siyah kare          : 27. saniyede tam siyah kare vardi (xfade fadeblack)
  - donmus kare         : klip donguye girip donarsa izleyici "bozuk" sanir
  - kesme yogunlugu     : ritim hedefiyle karsilastirma
  - LUFS / true peak    : -15.6 cikmisti, hedef -14
  - sessizlik           : anlatim boslugu / kayip ses parcasi
  - yazi guvenli alani  : kare ornekleme hook'u (vision/piksel)
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from typing import Callable, Optional

from . import kalite_kapisi
from .profil import EditProfili, VARSAYILAN


def varsayilan_kosucu(komut: list, zaman_asimi: int = 120) -> dict:
    """Gercek komut kosucusu. Doner {"rc","stdout","stderr"}."""
    try:
        r = subprocess.run(komut, capture_output=True, text=True,
                           timeout=zaman_asimi)
        return {"rc": r.returncode, "stdout": r.stdout or "",
                "stderr": r.stderr or ""}
    except Exception as e:
        return {"rc": -1, "stdout": "", "stderr": str(e)[:200]}


@dataclass
class PostQa:
    durum: str = "PASS"
    olcumler: dict = field(default_factory=dict)
    sorunlar: list = field(default_factory=list)
    komutlar: list = field(default_factory=list)

    def ekle(self, kod: str, seviye: str, detay: str, oneri: str = "") -> None:
        self.sorunlar.append({"kod": kod, "seviye": seviye, "detay": detay,
                              "oneri": oneri})

    def sonuclandir(self) -> "PostQa":
        if any(s["seviye"] == "fail" for s in self.sorunlar):
            self.durum = "FAIL"
        elif any(s["seviye"] == "warn" for s in self.sorunlar):
            self.durum = "WARN"
        else:
            self.durum = "PASS"
        return self

    def sozluk(self) -> dict:
        return {"durum": self.durum, "olcumler": self.olcumler,
                "sorunlar": self.sorunlar, "komutlar": self.komutlar}


# ─────────────────────────── KOMUT PLANLAYICI ───────────────────────────

def komut_plani(video_yolu: str, *, ince_sessizlik: bool = False) -> dict:
    """Kosulacak gercek komutlar. Testler bu plani okuyup fixture eslesir.

    ⚠ `ince_sessizlik` (Faz I-14): varsayilan `sessizlik` gecisi
    `d=1.2` kullaniyor — yani 1.2 sn'den KISA sessizligi HIC GORMUYOR.
    I-13 ciktisindaki iki bosluk 0.984 sn ve 0.903 sn'ydi; ikisi de bu
    esigin altinda kaldigi icin post-QA'da **hic gorunmediler**. Olu kuyruk
    olcumu bu yuzden ayri, ince (`d=0.30`) bir gecis ister. Varsayilan
    KAPALI: canli yolda fazladan ffmpeg gecisi kosulmaz.
    """
    plan = {
        "ffprobe": ["ffprobe", "-v", "error", "-select_streams", "v:0",
                    "-show_entries",
                    "stream=width,height,r_frame_rate,nb_frames,codec_name",
                    "-show_entries", "format=duration,size",
                    "-of", "json", video_yolu],
        "ffprobe_ses": ["ffprobe", "-v", "error", "-select_streams", "a:0",
                        "-show_entries", "stream=codec_name,sample_rate,channels",
                        "-of", "json", video_yolu],
        "siyah": ["ffmpeg", "-nostdin", "-i", video_yolu, "-vf",
                  "blackdetect=d=0.05:pix_th=0.10", "-f", "null", "-"],
        "donmus": ["ffmpeg", "-nostdin", "-i", video_yolu, "-vf",
                   "freezedetect=n=0.003:d=1.0", "-f", "null", "-"],
        "kesme": ["ffmpeg", "-nostdin", "-i", video_yolu, "-filter:v",
                  "select='gt(scene,0.12)',showinfo", "-f", "null", "-"],
        "loudness": ["ffmpeg", "-nostdin", "-i", video_yolu, "-af",
                     "loudnorm=print_format=json", "-f", "null", "-"],
        "sessizlik": ["ffmpeg", "-nostdin", "-i", video_yolu, "-af",
                      "silencedetect=noise=-45dB:d=1.2", "-f", "null", "-"],
    }
    if ince_sessizlik:
        plan["sessizlik_ince"] = ["ffmpeg", "-nostdin", "-i", video_yolu,
                                  "-af", "silencedetect=noise=-45dB:d=0.30",
                                  "-f", "null", "-"]
    return plan


def kare_ornekleme_komutu(video_yolu: str, hedef_dizin: str,
                          fps: float = 1.0) -> list:
    """Yazi guvenli alani / vision denetimi icin kare cikarma."""
    return ["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", video_yolu,
            "-vf", f"fps={fps},scale=640:-1", "-q:v", "3",
            os.path.join(hedef_dizin, "kare_%04d.jpg")]


def temas_sayfasi_komutu(video_yolu: str, cikti: str, sutun: int = 5,
                         satir: int = 6) -> list:
    return ["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", video_yolu,
            "-vf", f"fps=1,scale=440:-1,tile={sutun}x{satir}:margin=6:padding=4",
            cikti]


# ─────────────────────────── AYRISTIRICILAR ───────────────────────────

def _ffprobe_ayikla(stdout: str) -> dict:
    try:
        d = json.loads(stdout or "{}")
    except json.JSONDecodeError:
        return {}
    akis = (d.get("streams") or [{}])[0]
    bicim = d.get("format") or {}
    fps = 0.0
    ham = str(akis.get("r_frame_rate") or "")
    if "/" in ham:
        try:
            a, b = ham.split("/")
            fps = round(float(a) / float(b), 3) if float(b) else 0.0
        except (ValueError, ZeroDivisionError):
            fps = 0.0
    return {"genislik": int(akis.get("width") or 0),
            "yukseklik": int(akis.get("height") or 0),
            "fps": fps, "codec": akis.get("codec_name") or "",
            "sure_sn": float(bicim.get("duration") or 0),
            "boyut_bayt": int(bicim.get("size") or 0)}


def _siyah_ayikla(stderr: str) -> list:
    out = []
    for m in re.finditer(
            r"black_start:([\d.]+)\s+black_end:([\d.]+)\s+black_duration:([\d.]+)",
            stderr or ""):
        out.append({"bas": float(m.group(1)), "bitis": float(m.group(2)),
                    "sure": float(m.group(3))})
    return out


def _donmus_ayikla(stderr: str) -> list:
    out = []
    for m in re.finditer(r"freeze_start: ([\d.]+)", stderr or ""):
        out.append({"bas": float(m.group(1))})
    for i, m in enumerate(re.finditer(r"freeze_duration: ([\d.]+)", stderr or "")):
        if i < len(out):
            out[i]["sure"] = float(m.group(1))
    return out


def _kesme_ayikla(stderr: str) -> list:
    return [float(l.split("pts_time:")[1].split()[0])
            for l in (stderr or "").splitlines() if "pts_time:" in l]


def _loudness_ayikla(stderr: str) -> dict:
    blok = (stderr or "")[(stderr or "").rfind("{"):(stderr or "").rfind("}") + 1]
    try:
        d = json.loads(blok)
    except json.JSONDecodeError:
        return {}
    try:
        return {"lufs": float(d.get("input_i")),
                "tepe_dbtp": float(d.get("input_tp")),
                "lra": float(d.get("input_lra"))}
    except (TypeError, ValueError):
        return {}


def _sessizlik_ayikla(stderr: str) -> list:
    out = []
    for m in re.finditer(r"silence_start: ([\d.-]+)", stderr or ""):
        out.append({"bas": float(m.group(1))})
    for i, m in enumerate(re.finditer(r"silence_duration: ([\d.]+)", stderr or "")):
        if i < len(out):
            out[i]["sure"] = float(m.group(1))
    return out


# ─────────────────────────── ANA DENETIM ───────────────────────────

def denetle(video_yolu: str, *, beklenen: Optional[dict] = None,
            profil_: Optional[EditProfili] = None,
            kosucu: Optional[Callable] = None,
            zaman_asimi: int = 180,
            kalite_kapisi: bool = False,
            ambans_lufs: Optional[float] = None,
            anlatim_lufs: Optional[float] = None,
            ambans_seviye: float = 1.0,
            ducking: float = 1.0) -> PostQa:
    """Bitmis videoyu olcer.

    `beklenen`: {"sure_sn","cekim_sayisi","genislik","yukseklik","fps"}
    `kosucu`: (komut:list, zaman_asimi:int) -> {"rc","stdout","stderr"}

    Faz I-14 (hepsi OPSIYONEL, varsayilan davranis degismez):
      `kalite_kapisi` : False iken POST-SESSIZ-ORAN / POST-OLU-FINAL /
                        POST-AMBANS-DUYULMAZ kodlari URETILMEZ ve ince
                        sessizlik gecisi KOSULMAZ. Olcum yine de
                        `olcumler["kalite"]`e yazilir (kapali yolda yalniz
                        kaba `sessizlik` verisinden turetilir).
      `ambans_lufs` / `anlatim_lufs` / `ambans_seviye` / `ducking`:
                        ambiyans duyulabilirligi icin GERCEK olcumler.
                        Verilmezse duyulabilirlik `olculemedi` yazilir.
    """
    p = profil_ or VARSAYILAN
    beklenen = beklenen or {}
    kos = kosucu or varsayilan_kosucu
    q = PostQa()
    plan = komut_plani(video_yolu, ince_sessizlik=bool(kalite_kapisi))

    if not os.path.exists(video_yolu) and kosucu is None:
        q.ekle("POST-DOSYA-YOK", "fail", f"video bulunamadi: {video_yolu}",
               "render adimini kontrol et")
        return q.sonuclandir()

    for ad, komut in plan.items():
        r = kos(komut, zaman_asimi)
        q.komutlar.append({"ad": ad, "komut": " ".join(komut[:6]) + " ...",
                           "rc": r.get("rc")})
        if ad == "ffprobe":
            q.olcumler["video"] = _ffprobe_ayikla(r.get("stdout", ""))
        elif ad == "ffprobe_ses":
            try:
                akis = (json.loads(r.get("stdout") or "{}").get("streams")
                        or [{}])[0]
                q.olcumler["ses_akisi"] = {
                    "codec": akis.get("codec_name") or "",
                    "ornekleme": int(akis.get("sample_rate") or 0),
                    "kanal": int(akis.get("channels") or 0)}
            except Exception:
                q.olcumler["ses_akisi"] = {}
        elif ad == "siyah":
            q.olcumler["siyah_araliklar"] = _siyah_ayikla(r.get("stderr", ""))
        elif ad == "donmus":
            q.olcumler["donmus_araliklar"] = _donmus_ayikla(r.get("stderr", ""))
        elif ad == "kesme":
            k = _kesme_ayikla(r.get("stderr", ""))
            q.olcumler["kesmeler"] = k
            q.olcumler["kesme_sayisi"] = len(k)
        elif ad == "loudness":
            q.olcumler["loudness"] = _loudness_ayikla(r.get("stderr", ""))
        elif ad == "sessizlik":
            q.olcumler["sessizlikler"] = _sessizlik_ayikla(r.get("stderr", ""))
        elif ad == "sessizlik_ince":
            q.olcumler["sessizlikler_ince"] = _sessizlik_ayikla(
                r.get("stderr", ""))

    # ── DEGERLENDIRME ──
    v = q.olcumler.get("video") or {}
    if not v.get("genislik"):
        q.ekle("POST-PROBE-YOK", "fail", "ffprobe cozunurluk vermedi",
               "dosya bozuk olabilir")
    else:
        bg = int(beklenen.get("genislik") or p.genislik)
        by = int(beklenen.get("yukseklik") or p.yukseklik)
        if v["genislik"] != bg or v["yukseklik"] != by:
            q.ekle("POST-COZUNURLUK", "warn",
                   f"{v['genislik']}x{v['yukseklik']}, beklenen {bg}x{by}",
                   "render cozunurlugunu profile hizala")
        bfps = float(beklenen.get("fps") or p.fps)
        if v.get("fps") and abs(v["fps"] - bfps) > 0.5:
            q.ekle("POST-FPS", "warn", f"{v['fps']} fps, beklenen {bfps}",
                   "fps ayarini kontrol et")
        if beklenen.get("sure_sn"):
            fark = abs(v.get("sure_sn", 0) - float(beklenen["sure_sn"]))
            q.olcumler["sure_farki_sn"] = round(fark, 2)
            if fark > max(1.5, float(beklenen["sure_sn"]) * 0.08):
                q.ekle("POST-SURE-SAPMA", "warn",
                       f"cikti {v.get('sure_sn')} sn, plan {beklenen['sure_sn']} sn "
                       f"(fark {fark:.1f})",
                       "gecis kisalmasi ya da eksik segment olabilir")

    if q.olcumler.get("siyah_araliklar"):
        n = len(q.olcumler["siyah_araliklar"])
        q.ekle("POST-SIYAH-KARE", "fail",
               f"{n} siyah aralik: {q.olcumler['siyah_araliklar'][:3]}",
               "karartma gecisini eq-brightness dip'e cevir (fadeblack asimetrik)")
    uzun_donmus = [d for d in (q.olcumler.get("donmus_araliklar") or [])
                   if d.get("sure", 0) >= 1.5]
    if uzun_donmus:
        q.ekle("POST-DONMUS-KARE", "warn",
               f"{len(uzun_donmus)} donmus aralik: {uzun_donmus[:3]}",
               "kisa klibi donguye sokmak yerine baska varlik sec")

    ld = q.olcumler.get("loudness") or {}
    if ld:
        if abs(ld.get("lufs", -99) - p.lufs_hedef) > 1.0:
            q.ekle("POST-LUFS", "warn",
                   f"{ld.get('lufs')} LUFS, hedef {p.lufs_hedef}",
                   "normalizasyon oncesi kompresyon ekle")
        if ld.get("tepe_dbtp", -99) > p.tepe_tavan_dbtp:
            q.ekle("POST-TEPE", "warn",
                   f"true peak {ld.get('tepe_dbtp')} dBTP > {p.tepe_tavan_dbtp}",
                   "alimiter limitini dusur")
    else:
        q.ekle("POST-LOUDNESS-YOK", "warn", "loudness olcumu alinamadi",
               "ses akisini kontrol et")

    uzun_sessizlik = [s for s in (q.olcumler.get("sessizlikler") or [])
                      if s.get("sure", 0) >= 2.0]
    if uzun_sessizlik:
        q.ekle("POST-SESSIZLIK", "warn",
               f"{len(uzun_sessizlik)} uzun sessizlik: {uzun_sessizlik[:2]}",
               "anlatim bosluklarini kapat ya da ambience ekle")

    if beklenen.get("cekim_sayisi"):
        b = int(beklenen["cekim_sayisi"])
        g = q.olcumler.get("kesme_sayisi", 0) + 1
        q.olcumler["cekim_sapmasi"] = g - b
        if abs(g - b) > max(2, b * 0.35):
            q.ekle("POST-KESME-SAPMA", "warn",
                   f"tespit edilen ~{g} cekim, plan {b}",
                   "gecis suresi kesme tespitini etkiliyor olabilir")

    # ── FAZ I-14: MIKS SESSIZLIGI + AMBIYANS DUYULABILIRLIGI ──
    # ⚠ Olcum HER ZAMAN yazilir; HUKUM yalniz `kalite_kapisi=True` iken.
    _miks_denetle(q, sure_sn=(v.get("sure_sn") or beklenen.get("sure_sn")),
                  ambans_lufs=ambans_lufs, anlatim_lufs=anlatim_lufs,
                  ambans_seviye=ambans_seviye, ducking=ducking,
                  acik=bool(kalite_kapisi))
    return q.sonuclandir()


def _miks_denetle(q: PostQa, *, sure_sn, ambans_lufs, anlatim_lufs,
                  ambans_seviye, ducking, acik: bool) -> None:
    """I-14 miks olcumleri. ASLA COKMEZ; olcemezse `olculemedi` yazar."""
    # Ince gecis varsa ONU kullan: kaba gecis (d=1.2) 1 sn altindaki
    # boslugu hic gormuyor, dolayisiyla olu kuyrugu KACIRIR.
    ince = q.olcumler.get("sessizlikler_ince")
    kaynak = "sessizlik_ince(d=0.30)" if ince is not None else "sessizlik(d=1.2)"
    araliklar = ince if ince is not None else q.olcumler.get("sessizlikler")
    mx = kalite_kapisi.miks_olcusu(sure_sn=sure_sn,
                                   sessizlik_araliklari=araliklar)
    mx["kaynak_gecis"] = kaynak
    amb = kalite_kapisi.ambans_duyulabilirligi(
        ambans_lufs=ambans_lufs, anlatim_lufs=anlatim_lufs,
        ambans_seviye=ambans_seviye, ducking=ducking)
    q.olcumler["kalite"] = {"kapi_acik": bool(acik), "miks": mx, "ambans": amb}
    if not acik:
        return

    if mx.get("olculdu"):
        if mx.get("sessiz_oran_asildi"):
            q.ekle("POST-SESSIZ-ORAN", "fail",
                   f"miksin %{mx['sessiz_orani'] * 100:.1f}'i sessiz "
                   f"({mx['sessiz_sn']} sn / {mx['sure_sn']} sn, tavan "
                   f"%{mx['sessiz_oran_tavani'] * 100:.0f}) [{kaynak}]",
                   "anlatim bosluklarini kapat ya da duyulabilir ambiyans ekle")
        if mx.get("olu_final_asildi"):
            q.ekle("POST-OLU-FINAL", "fail",
                   f"videonun sonunda {mx['olu_final_sn']} sn sessiz kuyruk "
                   f"(tavan {mx['olu_final_esigi']} sn) [{kaynak}]",
                   "son sahneyi anlatim bitisine kadar kisalt")
    else:
        q.ekle("POST-MIKS-OLCULEMEDI", "warn",
               f"miks sessizlik olcumu alinamadi ({mx.get('neden')})",
               "ffprobe sure ve silencedetect ciktisini kontrol et")

    if amb.get("olculdu"):
        if not amb.get("duyulabilir"):
            q.ekle("POST-AMBANS-DUYULMAZ", "fail",
                   f"ambiyans anlatimin {amb['fark_db']} dB altinda "
                   f"(tavan {amb['esik_db']} dB): kaynak {amb['ambans_lufs']} "
                   f"LUFS, seviye {amb['ambans_seviye']} "
                   f"({amb['seviye_db']} dB), ducking {amb['ducking']} "
                   f"({amb['ducking_db']} dB) -> etkin {amb['etkin_lufs']} LUFS"
                   + ("; ducking kapatilsa BILE duyulmaz "
                      f"({amb['fark_ducksuz_db']} dB)"
                      if not amb.get("ducking_suz_duyulabilir")
                      else "; ducking'i azaltmak yeterli olabilir"),
                   "ambiyans kaynagini yukselt ya da seviye/ducking dengesini "
                   "olculmus hedefe gore kur")
        elif amb.get("bastiriyor"):
            q.ekle("POST-AMBANS-BASKIN", "fail",
                   f"ambiyans anlatimin yalnizca {amb['fark_db']} dB altinda "
                   f"(alt sinir {amb['bastirma_esik_db']} dB) — sozu bogar",
                   "ambans seviyesini dusur ya da ducking'i derinlestir")
    elif ambans_lufs is not None or anlatim_lufs is not None:
        # Yarim girdi verilmis: sessizce gecme, olcemedigini soyle.
        q.ekle("POST-AMBANS-OLCULEMEDI", "warn",
               "ambiyans duyulabilirligi OLCULEMEDI (ambans_lufs ve "
               "anlatim_lufs birlikte gerekir)",
               "iki LUFS olcumunu de gecir")
