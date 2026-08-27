#!/usr/bin/env python3
"""HAYALET — KURGU: metin + ses + cumle basina medya -> senkron video.

Hayalet URETIR ve INDIRIR; bu modul o ciktilari SESLE HIZALAR.
Cumle i'nin sesteki suresi ne kadarsa, o cumlenin videosu/gorseli
ekranda tam o kadar durur. Premiere/Resolve gerekmez, sadece ffmpeg.

Cumle sinirlari nasil bulunur (sirasiyla denenir):
  1) ses bir KLASORSE  -> her cumlenin kendi ses dosyasi var, sure KESIN
  2) OpenAI anahtari varsa -> ASR kelime zaman damgalari (tek dosyada EN IYI)
  3) ffmpeg silencedetect -> duraklama sayisi cumle sayisini tutuyorsa
  4) hicbiri olmazsa -> karakter sayisina gore oranti (UYARI ile)

⚠ SESSIZ DUSUS YOK: hangi yontemin kullanildigi ve her cumlenin suresi
`kurgu.json` icine yazilir, ekrana da basilir.

Kullanim:
    python3 -m hayalet.kurgu --is is_20260821_1a2b
    python3 -m hayalet.kurgu --metin m.txt --ses ses.mp3 --medya klasor/ \
        --cikti final.mp4 --altyazi
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import urllib.request
import uuid
from pathlib import Path

from . import ayar
from .beyin import cumlelere_bol
from .capcut import CapcutHatasi

EN, BOY, FPS = 1920, 1080, 30
VIDEO_UZANTI = {".mp4", ".mov", ".webm", ".m4v", ".mkv"}
GORSEL_UZANTI = {".png", ".jpg", ".jpeg", ".webp"}
SES_UZANTI = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}

# Duraklamalari cumle siniri sayma esikleri.
# ⚠ OLCULDU (21 Agu 2026, macOS `say` ile uretilmis TR anlatim): -35dB/0.32s
# ile SIFIR duraklama bulundu (TTS cumle arasi nefes birakmiyor), -30dB/0.2s
# ile tam 4/4 dogru bulundu. Esik gevsetildi — yine de bu YEDEK yontemdir,
# birincil hizalama ASR kelime zaman damgalaridir.
SESSIZ_DB = "-30dB"
SESSIZ_MIN_SN = 0.22
# Bir cumleye ayrilabilecek en kisa sure — altina duserse hizalama bozuktur.
EN_KISA_SN = 0.4

# ── Kelime zaman damgali hizalama (EN IYI yontem) ──
# ⚠ NEDEN: tek seslendirme dosyasinda "duraklama say" yontemi ancak cumle
# sayisi kadar net duraklama varsa tutar; 40+ cumlelik anlatimda pratikte
# TUTMAZ ve karakter orantisina duseriz (kayma birikir). Transkripsiyon
# kelime bazinda ZAMAN verir; cumle sinirlarini gercek sesten okuruz.
OPENAI_KEY = os.environ.get("HAYALET_OPENAI_KEY",
                            os.environ.get("OPENAI_API_KEY", ""))
ASR_MODEL = os.environ.get("HAYALET_ASR_MODEL", "whisper-1")
ASR_BOY_TAVAN = 24 * 1024 * 1024          # whisper-1 sinirı 25MB


class KurguHatasi(RuntimeError):
    """Kurgu yapilamaz — nedeni mesajda, tahminle devam ETME."""


# ─────────────────────────── ffmpeg yardimcilari ───────────────────────────

def _kos(komut: list, yakala: bool = False) -> str:
    s = subprocess.run(komut, capture_output=True, text=True)
    if s.returncode != 0:
        kuyruk = (s.stderr or "").strip().splitlines()[-6:]
        raise KurguHatasi(f"ffmpeg dustu: {' '.join(komut[:3])}...\n"
                          + "\n".join(kuyruk))
    return (s.stdout if yakala else "") or ""


def _suzgec_var(ad: str) -> bool:
    """ffmpeg derlemesinde suzgec var mi? (Homebrew'un sade derlemesinde
    `subtitles` yok — libass olmadan altyazi YAKILAMAZ.)"""
    s = subprocess.run(["ffmpeg", "-hide_banner", "-filters"],
                       capture_output=True, text=True)
    return re.search(rf"^ \S\S\S? +{re.escape(ad)} ", s.stdout or "",
                     re.M) is not None


def sure(dosya: Path) -> float:
    cikti = _kos(["ffprobe", "-v", "error", "-show_entries",
                  "format=duration", "-of", "csv=p=0", str(dosya)], yakala=True)
    try:
        return float(cikti.strip())
    except ValueError:
        raise KurguHatasi(f"Sure okunamadi: {dosya.name}")


def _sessizlikler(ses: Path) -> list:
    """[(baslangic, bitis)] — ffmpeg silencedetect ciktisi."""
    s = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(ses), "-af",
         f"silencedetect=noise={SESSIZ_DB}:d={SESSIZ_MIN_SN}", "-f", "null", "-"],
        capture_output=True, text=True)
    metin = s.stderr or ""
    basla = [float(x) for x in re.findall(r"silence_start:\s*(-?[\d.]+)", metin)]
    bit = [float(x) for x in re.findall(r"silence_end:\s*(-?[\d.]+)", metin)]
    return list(zip(basla, bit))


# ─────────────────────────── cumle sureleri ───────────────────────────

def _sozcukle(metin: str) -> list:
    """Karsilastirma icin sadelestirilmis sozcukler (aksan/noktalama disi)."""
    d = unicodedata.normalize("NFKD", (metin or "").lower())
    d = "".join(k for k in d if not unicodedata.combining(k))
    return [w for w in re.findall(r"[0-9a-z]+", d) if w]


def _ses_kucult(ses: Path) -> Path:
    """ASR icin 16kHz mono m4a — 25MB sinirinin altina indirir."""
    hedef = Path(tempfile.mkdtemp(prefix="hayalet_asr_")) / "asr.m4a"
    _kos(["ffmpeg", "-y", "-i", str(ses), "-ac", "1", "-ar", "16000",
          "-c:a", "aac", "-b:a", "32k", str(hedef)])
    return hedef


def _asr_kelimeleri(ses: Path, bildir=print) -> list:
    """[(sozcuk, baslangic_sn, bitis_sn)] — OpenAI kelime zaman damgalari."""
    if not OPENAI_KEY:
        raise KurguHatasi("anahtar yok")
    yol = ses
    if yol.stat().st_size > ASR_BOY_TAVAN:
        bildir("  ses buyuk — ASR icin 16kHz mono'ya kucultuluyor")
        yol = _ses_kucult(yol)
        if yol.stat().st_size > ASR_BOY_TAVAN:
            raise KurguHatasi("ses kuculttukten sonra da 25MB'i asiyor")

    sinir = f"----hayalet{uuid.uuid4().hex}"
    govde = bytearray()

    def alan(ad, deger):
        govde.extend(f"--{sinir}\r\nContent-Disposition: form-data; "
                     f'name="{ad}"\r\n\r\n{deger}\r\n'.encode())

    alan("model", ASR_MODEL)
    alan("response_format", "verbose_json")
    alan("timestamp_granularities[]", "word")
    govde.extend(f'--{sinir}\r\nContent-Disposition: form-data; '
                 f'name="file"; filename="{yol.name}"\r\n'
                 f"Content-Type: application/octet-stream\r\n\r\n".encode())
    govde.extend(yol.read_bytes())
    govde.extend(f"\r\n--{sinir}--\r\n".encode())

    istek = urllib.request.Request(
        "https://api.openai.com/v1/audio/transcriptions", data=bytes(govde),
        headers={"Authorization": f"Bearer {OPENAI_KEY}",
                 "Content-Type": f"multipart/form-data; boundary={sinir}"})
    with urllib.request.urlopen(istek, timeout=600) as y:
        cevap = json.load(y)
    kelimeler = [(str(k.get("word", "")), float(k.get("start", 0.0)),
                  float(k.get("end", 0.0))) for k in (cevap.get("words") or [])]
    if not kelimeler:
        raise KurguHatasi("ASR kelime zamani dondurmedi")
    return kelimeler


def _hizala_kelime(cumleler: list, kelimeler: list, toplam: float) -> list:
    """Cumleleri ASR kelimelerine esleyip GERCEK sinir surelerini cikarir.

    ⚠ TRANSKRIPT METINLE BIREBIR OLMAZ (yanlis duyma, sayi/kisaltma yazimi).
    Bu yuzden difflib ile en uzun ortak diziler bulunur; eslenemeyen
    cumle siniri, komsu eslesmeler arasinda ORANTIYLA yerlestirilir.
    """
    metin_sozcuk, cumle_no = [], []
    for i, c in enumerate(cumleler):
        w = _sozcukle(c)
        metin_sozcuk.extend(w)
        cumle_no.extend([i] * len(w))
    asr_sozcuk = [_sozcukle(k[0])[0] if _sozcukle(k[0]) else "" for k in kelimeler]
    if not metin_sozcuk or not asr_sozcuk:
        raise KurguHatasi("hizalanacak sozcuk yok")

    # metin sozcuk indeksi -> asr sozcuk indeksi
    harita = {}
    for a, b, n in difflib.SequenceMatcher(
            None, metin_sozcuk, asr_sozcuk, autojunk=False).get_matching_blocks():
        for k in range(n):
            harita[a + k] = b + k
    if len(harita) < max(4, len(metin_sozcuk) * 0.30):
        raise KurguHatasi(
            f"transkript metinle ortusmuyor ({len(harita)}/{len(metin_sozcuk)} "
            "sozcuk esletti) — seslendirme metne ait olmayabilir")

    # Her cumlenin SON sozcugunun metin-indeksi = o cumlenin siniri
    son_idx = []
    for i in range(len(cumleler)):
        idx = [j for j, c in enumerate(cumle_no) if c == i]
        son_idx.append(idx[-1] if idx else None)

    sinirlar = []
    for i, mi in enumerate(son_idx):
        t = None
        if mi is not None:
            for adim in range(0, 6):        # kucuk pencerede eslesme ara
                for j in (mi - adim, mi + adim):
                    if j in harita and 0 <= harita[j] < len(kelimeler):
                        t = kelimeler[harita[j]][2]
                        break
                if t is not None:
                    break
        sinirlar.append(t)
    sinirlar[-1] = toplam                  # son cumle sesin sonuna kadar

    # Bosluklari komsular arasinda orantiyla doldur
    onceki = 0.0
    for i in range(len(sinirlar)):
        if sinirlar[i] is None:
            j = next((k for k in range(i + 1, len(sinirlar))
                      if sinirlar[k] is not None), len(sinirlar) - 1)
            adim = (sinirlar[j] - onceki) / (j - i + 1)
            sinirlar[i] = onceki + adim
        sinirlar[i] = max(sinirlar[i], onceki + EN_KISA_SN)
        onceki = sinirlar[i]
    olcek = toplam / sinirlar[-1] if sinirlar[-1] > toplam else 1.0
    sinirlar = [s * olcek for s in sinirlar]
    return [sinirlar[0]] + [sinirlar[i] - sinirlar[i - 1]
                            for i in range(1, len(sinirlar))]


def _orantili(cumleler: list, toplam: float) -> list:
    """Son care: karakter sayisina gore payla. Hizalama YAKLASIKTIR."""
    agirlik = [max(len(c), 1) for c in cumleler]
    top = sum(agirlik)
    return [toplam * a / top for a in agirlik]


def sureleri_cikar(cumleler: list, ses: Path, bildir=print) -> tuple:
    """(sureler, birlesik_ses, yontem) dondurur."""
    n = len(cumleler)

    # 1) Cumle basina ses dosyasi — kesin hizalama.
    if ses.is_dir():
        parcalar = sorted([p for p in ses.iterdir()
                           if p.suffix.lower() in SES_UZANTI],
                          key=_sira_anahtari)
        if len(parcalar) != n:
            raise KurguHatasi(
                f"Ses klasorunde {len(parcalar)} dosya var ama metinde {n} "
                f"cumle. Esitlemeden kurgu yapilmaz.")
        sureler = [sure(p) for p in parcalar]
        return sureler, _sesleri_birlestir(parcalar), "cumle basina ses dosyasi"

    toplam = sure(ses)

    # 2) Kelime zaman damgalari (ASR) — tek dosyada EN GUVENILIR yontem.
    if OPENAI_KEY:
        try:
            bildir("  cumle sinirlari icin ses cozumleniyor (ASR)…")
            kelimeler = _asr_kelimeleri(ses, bildir)
            sureler = _hizala_kelime(cumleler, kelimeler, toplam)
            return sureler, ses, f"ASR kelime zaman damgalari ({ASR_MODEL})"
        except KurguHatasi as e:
            bildir(f"⚠ ASR hizalama olmadi ({e}) — duraklamalara duşuluyor")
        except Exception as e:                               # noqa: BLE001
            bildir(f"⚠ ASR hizalama olmadi ({type(e).__name__}) — "
                   "duraklamalara duşuluyor")
    else:
        bildir("⚠ HAYALET_OPENAI_KEY yok — en iyi hizalama (ASR) atlandi")

    # 3) Duraklamalardan bol.
    bosluklar = [(a, b) for a, b in _sessizlikler(ses) if a > 0.05 and b < toplam - 0.05]
    if len(bosluklar) == n - 1:
        sinirlar = [0.0] + [(a + b) / 2 for a, b in bosluklar] + [toplam]
        sureler = [sinirlar[i + 1] - sinirlar[i] for i in range(n)]
        if all(s >= EN_KISA_SN for s in sureler):
            return sureler, ses, "sesteki duraklamalar (silencedetect)"
        bildir("⚠ Duraklama sayisi tuttu ama bazi cumleler cok kisa cikti.")
    else:
        bildir(f"⚠ Seste {len(bosluklar)} duraklama bulundu, {n - 1} bekleniyordu.")

    # 4) Oranti — yaklasik.
    bildir("⚠ YAKLASIK HIZALAMA: sureler karakter sayisina gore paylastirildi. "
           "Kesin senkron icin cumle basina ayri ses dosyasi ver.")
    return _orantili(cumleler, toplam), ses, "karakter orantisi (YAKLASIK)"


def sesleri_birlestir(parcalar: list, hedef: Path = None) -> Path:
    """Ses parcalarini SIRAYLA tek dosyada birlestirir.

    ⚠ ONCE TEK FORMATA GETIRILIR: parcalar farkli kaynaklardan gelebilir
    (Telegram sesli mesaji opus/ogg, telefondan m4a, bilgisayardan mp3).
    Concat demuxer'a farkli ornekleme hizi/kanal sayisi verilirse cikti
    sessiz ya da hizli/yavas olabilir — bu SESSIZ bir bozulmadir. Bu yuzden
    her parca once 44.1kHz mono AAC'ye cevrilir, sonra birlestirilir.
    """
    if not parcalar:
        raise KurguHatasi("Birlestirilecek ses parcasi yok.")
    gecici = Path(tempfile.mkdtemp(prefix="hayalet_ses_"))
    hedef = hedef or (gecici / "anlatim.m4a")
    hedef.parent.mkdir(parents=True, exist_ok=True)
    if len(parcalar) == 1:
        _kos(["ffmpeg", "-y", "-i", str(parcalar[0]), "-ac", "1",
              "-ar", "44100", "-c:a", "aac", "-b:a", "128k", str(hedef)])
        return hedef
    duzgun = []
    for i, p in enumerate(parcalar, 1):
        n = gecici / f"parca_{i:03d}.m4a"
        _kos(["ffmpeg", "-y", "-i", str(p), "-ac", "1", "-ar", "44100",
              "-c:a", "aac", "-b:a", "128k", str(n)])
        duzgun.append(n)
    liste = gecici / "liste.txt"
    liste.write_text("".join(f"file '{x}'\n" for x in duzgun), encoding="utf-8")
    _kos(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(liste),
          "-c", "copy", str(hedef)])
    # ⚠ SESSIZ KAYIP KONTROLU: birlesik sure parcalarin toplamini tutmali.
    beklenen = sum(sure(x) for x in duzgun)
    olan = sure(hedef)
    if abs(olan - beklenen) > max(1.0, beklenen * 0.02):
        raise KurguHatasi(
            f"Ses birlestirme tutmadi: beklenen {beklenen:.1f} sn, "
            f"olan {olan:.1f} sn. Parcalar bozuk olabilir.")
    return hedef


def _sesleri_birlestir(parcalar: list) -> Path:
    return sesleri_birlestir(parcalar)


# ─────────────────────────── medya eslesmesi ───────────────────────────

def _sira_anahtari(p: Path):
    """Dosya adinin BASINDAKI sayi = cumle sirasi. Yoksa ada gore."""
    m = re.match(r"0*(\d+)", p.stem)
    return (0, int(m.group(1))) if m else (1, p.stem.lower())


def medya_esle(medya: Path, n: int, bildir=print,
               eksige_izin: bool = False) -> list:
    """Cumle sirasi -> dosya. `eslesme.json` varsa o kazanir.

    eksige_izin=True ise uretilemeyen cumleler icin None dondurur; cagiran
    bosluklari ONCEKI SAHNEYI UZATARAK kapatir (bkz. `sahneleri_kur`).
    """
    harita = medya / "eslesme.json"
    if harita.exists():
        ham = json.loads(harita.read_text(encoding="utf-8"))
        yol = []
        eksik = []
        for i in range(1, n + 1):
            d = ham.get(str(i)) or ham.get(i)
            p = None
            if d:
                p = Path(d)
                p = p if p.is_absolute() else medya / p
                if not p.exists():
                    p = None
            if p is None:
                if not eksige_izin:
                    raise KurguHatasi(f"{i}. cumlenin medyasi yok.")
                eksik.append(i)
            yol.append(p)
        if eksik:
            bildir(f"⚠ {len(eksik)} cumlenin medyasi yok — onceki sahne "
                   f"uzatilarak kapatilacak (cumle: "
                   f"{', '.join(str(x) for x in eksik[:12])}"
                   f"{'…' if len(eksik) > 12 else ''})")
        bildir(f"Eslesme: eslesme.json ({n} cumle)")
        return yol

    dosyalar = sorted([p for p in medya.rglob("*")
                       if p.suffix.lower() in VIDEO_UZANTI | GORSEL_UZANTI],
                      key=_sira_anahtari)
    if len(dosyalar) != n:
        raise KurguHatasi(
            f"{medya} icinde {len(dosyalar)} medya var ama metinde {n} cumle.\n"
            f"Ya dosya adlarini 001_, 002_ diye numarala ya da "
            f"{medya}/eslesme.json yaz: {{\"1\": \"video/a.mp4\", ...}}")
    bildir(f"Eslesme: dosya adi sirasi ({n} cumle)")
    return dosyalar


# ─────────────────────────── sahne uretimi ───────────────────────────

# ⚠ CUMLE BASINA BIR GORSEL = STROBOSKOP (22 Agu 2026 olcumu): 179 cumlelik
# gercek iste ortanca klip 2.14 sn, %70'i 3 sn altinda, 24 tanesi 1 sn'den
# kisaydi. Goruntu surekli degisince izlemesi yorucu oluyor.
# COZUM: kisa cumleler ONCEKI SAHNEYE KATILIR; sahne bu esige ulasana kadar
# buyur. Grubun goruntusu ILK cumlenin gorselidir; digerlerinin gorselleri
# diskte durur (istenirse elle degistirilebilir).
EN_KISA_SAHNE_SN = float(os.environ.get("HAYALET_EN_KISA_SAHNE", "5.0"))
# Gorsel klip boyunca toplam yakinlasma orani (0.22 = %22 buyume).
ZOOM_ORAN = float(os.environ.get("HAYALET_ZOOM", "0.22"))


def sahneleri_grupla(sahneler: list, en_az_sn: float = None) -> list:
    """Kisa sahneleri birlestirerek her sahneyi en az `en_az_sn` yapar.

    Ses HIC KAYMAZ: sureler toplanir, toplam degismez. Yalnizca goruntunun
    kac saniyede bir degistigi kontrol edilir.
    """
    en_az = EN_KISA_SAHNE_SN if en_az_sn is None else en_az_sn
    if en_az <= 0 or not sahneler:
        return sahneler
    yeni = []
    for sh in sahneler:
        if yeni and yeni[-1]["sn"] < en_az:
            yeni[-1]["sn"] += sh["sn"]
            yeni[-1]["cumleler"] = yeni[-1]["cumleler"] + sh["cumleler"]
        else:
            yeni.append({"dosya": sh["dosya"], "sn": sh["sn"],
                         "cumleler": list(sh["cumleler"])})
    # Son sahne esigin altinda kaldiysa bir oncekine kat.
    if len(yeni) > 1 and yeni[-1]["sn"] < en_az:
        yeni[-2]["sn"] += yeni[-1]["sn"]
        yeni[-2]["cumleler"] += yeni[-1]["cumleler"]
        yeni.pop()
    return yeni


def sahneleri_kur(dosyalar: list, sureler: list, cumleler: list) -> list:
    """Eksik medyali cumleleri ONCEKI SAHNEYE KATARAK sahne listesi kurar.

    ⚠ NEDEN UZATMA: bir cumlenin gorseli uretilemediginde o araligi bos
    birakmak ya da klipleri kaydirmak senkronu bozar. Bunun yerine onceki
    goruntu ekranda DAHA UZUN kalir (6 sn yerine 12 sn gibi) — ses hic
    kaymaz, izleyici bosluk gormez.
    Ilk cumle(ler) eksikse sureleri ILK MEVCUT sahneye eklenir.

    Doner: [{"dosya", "sn", "cumleler": [no...]}]
    """
    sahneler, devir = [], 0.0
    for i, (dosya, sn) in enumerate(zip(dosyalar, sureler), 1):
        if dosya is None:
            if sahneler:
                sahneler[-1]["sn"] += sn
                sahneler[-1]["cumleler"].append(i)
            else:
                devir += sn          # bastaki eksikler ilk sahneye biner
            continue
        sahneler.append({"dosya": dosya, "sn": sn + devir, "cumleler": [i]})
        devir = 0.0
    if not sahneler:
        raise KurguHatasi("Hicbir cumlenin medyasi yok — kurgu yapilamaz.")
    return sahneler


_SIGDIR = (f"scale={EN}:{BOY}:force_original_aspect_ratio=decrease,"
           f"pad={EN}:{BOY}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={FPS}")


def sahne_yap(kaynak: Path, sn: float, hedef: Path) -> None:
    """Kaynagi TAM `sn` saniyelik, tek tip kodlanmis bir klibe cevirir."""
    gorsel = kaynak.suffix.lower() in GORSEL_UZANTI
    if gorsel:
        # Ken Burns: durgun gorsel ekranda olmesin.
        # Once 2x cerceveye TAM SIGDIR (videolarla ayni letterbox davranisi —
        # kare/dikey gorselin ustu altu kesilmesin), sonra yavas zoom.
        # ⚠ ZOOM KLIBIN TAMAMINA YAYILMALI (22 Agu 2026 kullanici geri
        # bildirimi): eski hal `min(zoom+0.0009,1.22)` idi — sabit hizla
        # buyuyup TAVANA CARPIYORDU. 0.22'lik yol 30fps'te ~8.1 saniye
        # suruyor; 10 saniyelik bir klipte son ~2 saniye DONUYORDU ve bu
        # durus kesme/gecis efekti gibi gorunuyordu.
        # Simdi artis klip suresinden hesaplanir: hangi uzunlukta olursa
        # olsun hareket ilk kareden son kareye kadar kesintisiz surer.
        kare = max(int(sn * FPS), 1)
        adim = ZOOM_ORAN / max(kare - 1, 1)
        suzgec = (f"scale={EN*2}:{BOY*2}:force_original_aspect_ratio=decrease,"
                  f"pad={EN*2}:{BOY*2}:(ow-iw)/2:(oh-ih)/2,"
                  f"zoompan=z='1+{adim:.8f}*on'"
                  f":d={kare}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                  f":s={EN}x{BOY}:fps={FPS},setsar=1")
        girdi = ["-loop", "1", "-i", str(kaynak)]
    else:
        # -stream_loop: klip kisaysa basa sarar, uzunsa -t zaten keser.
        suzgec = _SIGDIR
        girdi = ["-stream_loop", "-1", "-i", str(kaynak)]
    _kos(["ffmpeg", "-y", *girdi, "-t", f"{sn:.3f}", "-vf", suzgec,
          "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
          "-pix_fmt", "yuv420p", "-r", str(FPS), str(hedef)])


def _zaman(sn: float) -> str:
    ms = int(round(sn * 1000))
    s, ms = divmod(ms, 1000)
    d, s = divmod(s, 60)
    sa, d = divmod(d, 60)
    return f"{sa:02d}:{d:02d}:{s:02d},{ms:03d}"


def srt_yaz(cumleler: list, sureler: list, hedef: Path) -> None:
    t, satir = 0.0, []
    for i, (c, s) in enumerate(zip(cumleler, sureler), 1):
        satir.append(f"{i}\n{_zaman(t)} --> {_zaman(t + s)}\n{c}\n")
        t += s
    hedef.write_text("\n".join(satir), encoding="utf-8")


# ─────────────────────────── ana akis ───────────────────────────

def kurgula(metin: str, ses: Path, medya: Path, cikti: Path,
            altyazi: bool = False, capcut: str = "", bildir=print,
            eksige_izin: bool = True) -> dict:
    if not shutil.which("ffmpeg"):
        raise KurguHatasi("ffmpeg kurulu degil:  brew install ffmpeg")
    cumleler = cumlelere_bol(metin)
    if not cumleler:
        raise KurguHatasi("Metinde cumle yok.")
    bildir(f"{len(cumleler)} cumle bulundu.")

    dosyalar = medya_esle(medya, len(cumleler), bildir, eksige_izin)
    sureler, anlatim, yontem = sureleri_cikar(cumleler, ses, bildir)
    bildir(f"Hizalama yontemi: {yontem}")
    # Eksik medyali cumleler onceki sahneye katilir; ses HIC KAYMAZ.
    sahne_plani = sahneleri_kur(dosyalar, sureler, cumleler)
    eksikten = sum(len(x["cumleler"]) - 1 for x in sahne_plani)
    if eksikten:
        bildir(f"↔ {eksikten} cumle medyasi yok — onceki sahneye katildi")
    # Kisa sahneleri birlestir: goruntu her 1-2 saniyede degismesin.
    once = len(sahne_plani)
    sahne_plani = sahneleri_grupla(sahne_plani)
    uzatilan = sum(len(x["cumleler"]) - 1 for x in sahne_plani)
    if len(sahne_plani) != once:
        sur = sorted(x["sn"] for x in sahne_plani)
        bildir(f"🎞 sahne birlestirme (en az {EN_KISA_SAHNE_SN:g} sn): "
               f"{len(cumleler)} cumle → {len(sahne_plani)} klip · "
               f"ortanca {sur[len(sur)//2]:.1f} sn · en uzun {sur[-1]:.1f} sn")

    # ⚠ CapCut icin klipler KALICI olmali: taslak bu dosyalara yol verir,
    # gecici klasor silinirse zaman cizgisi bos medyayla acilir.
    if capcut:
        gecici = cikti.parent / (cikti.stem + "_klipler")
        gecici.mkdir(parents=True, exist_ok=True)
    else:
        gecici = Path(tempfile.mkdtemp(prefix="hayalet_kurgu_"))
    sahneler = []
    for i, sh in enumerate(sahne_plani, 1):
        parca = gecici / f"sahne_{i:04d}.mp4"
        etiket = (f"c{sh['cumleler'][0]}" if len(sh["cumleler"]) == 1
                  else f"c{sh['cumleler'][0]}-{sh['cumleler'][-1]}")
        bildir(f"  [{i}/{len(sahne_plani)}] {sh['sn']:5.2f}sn  {etiket}  "
               f"{Path(sh['dosya']).name}")
        sahne_yap(Path(sh["dosya"]), sh["sn"], parca)
        sahneler.append(parca)

    liste = gecici / "sahneler.txt"
    liste.write_text("".join(f"file '{p}'\n" for p in sahneler), encoding="utf-8")
    gorsel_akis = gecici / "gorsel.mp4"
    _kos(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(liste),
          "-c", "copy", str(gorsel_akis)])

    cikti.parent.mkdir(parents=True, exist_ok=True)
    komut = ["ffmpeg", "-y", "-i", str(gorsel_akis), "-i", str(anlatim)]
    altyazi_notu = "yok"
    if altyazi:
        srt = cikti.with_suffix(".srt")
        srt_yaz(cumleler, sureler, srt)
        if _suzgec_var("subtitles"):
            kacis = (str(srt).replace("\\", "/")
                     .replace(":", r"\:").replace("'", r"\'"))
            komut += ["-vf", f"subtitles='{kacis}':force_style="
                             "'FontSize=22,Outline=2,MarginV=48'",
                      "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                      "-pix_fmt", "yuv420p"]
            altyazi_notu = "goruntuye yakildi"
        else:
            # ⚠ SESSIZ DUSUS YOK: yakamiyorsak GOMULU iz olarak ekleriz.
            bildir("⚠ Bu ffmpeg derlemesinde `subtitles` suzgeci (libass) YOK "
                   "— altyazi goruntuye yakilamadi, gomulu iz olarak eklendi "
                   "(oynaticidan acilir). Yakmak icin libass'li ffmpeg gerekir.")
            komut += ["-i", str(srt), "-map", "0:v", "-map", "1:a", "-map", "2",
                      "-c:v", "copy", "-c:s", "mov_text"]
            altyazi_notu = f"gomulu iz + {srt.name}"
        komut += ["-c:a", "aac", "-b:a", "192k", "-shortest", str(cikti)]
    else:
        komut += ["-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                  "-shortest", str(cikti)]
    _kos(komut)

    kunye = {"cikti": str(cikti), "yontem": yontem,
             "altyazi": altyazi_notu,
             "toplam_sn": round(sum(sureler), 3),
             "cumle_sayisi": len(cumleler), "klip_sayisi": len(sahne_plani),
             "uzatilan_cumle": uzatilan, "en_kisa_sahne_sn": EN_KISA_SAHNE_SN,
             "medyasiz_cumleler": [i for i, d in enumerate(dosyalar, 1)
                                   if d is None],
             "sahneler": [{"sira": i, "sn": round(sh["sn"], 3),
                           "cumleler": sh["cumleler"],
                           "cumle": " ".join(cumleler[c - 1]
                                             for c in sh["cumleler"])[:300],
                           "dosya": str(sh["dosya"])}
                          for i, sh in enumerate(sahne_plani, 1)]}
    cikti.with_name(cikti.stem + "_kurgu.json").write_text(
        json.dumps(kunye, ensure_ascii=False, indent=2), encoding="utf-8")
    bildir(f"✓ {cikti}  ({kunye['toplam_sn']:.1f} sn)")

    if capcut:
        from .capcut import taslak_yaz          # gec import: CapCut sart degil
        # Anlatim sesi de kalici olmali (klasor ses ise birlestirilmisti).
        kalici_ses = gecici / "anlatim.m4a"
        if Path(anlatim).resolve() != kalici_ses.resolve():
            shutil.copy2(anlatim, kalici_ses)
        klasor = taslak_yaz(capcut,
                            [(y, sh["sn"]) for y, sh in
                             zip(sahneler, sahne_plani)],
                            kalici_ses, sum(sureler), bildir=bildir)
        kunye["capcut"] = str(klasor)
        cikti.with_name(cikti.stem + "_kurgu.json").write_text(
            json.dumps(kunye, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        shutil.rmtree(gecici, ignore_errors=True)
    return kunye


def main(argv=None) -> int:
    a = argparse.ArgumentParser(description="Hayalet ciktilarini sesle hizala.")
    a.add_argument("--is", dest="is_adi",
                   help="~/Desktop/Hayalet/<is_adi> klasorunu kullan")
    a.add_argument("--metin", help="Anlatim metni (.txt)")
    a.add_argument("--ses", help="Tek ses dosyasi VEYA cumle basina ses klasoru")
    a.add_argument("--medya", help="Video/gorsel klasoru")
    a.add_argument("--cikti", help="Cikti .mp4")
    a.add_argument("--altyazi", action="store_true", help="Altyaziyi videoya goc")
    a.add_argument("--capcut", metavar="AD", default="",
                   help="Ayni kurguyu CapCut taslagi olarak da yaz "
                        "(her cumle ayri klip, ses ayri iz)")
    n = a.parse_args(argv)

    if n.is_adi:
        d = ayar.KOK / n.is_adi
        n.metin = n.metin or str(d / "metin.txt")
        n.ses = n.ses or str(d / "ses")
        n.medya = n.medya or str(d)
        n.cikti = n.cikti or str(d / "final.mp4")
    if not (n.metin and n.ses and n.medya and n.cikti):
        a.error("--is ver ya da --metin --ses --medya --cikti hepsini ver")

    try:
        kurgula(Path(n.metin).read_text(encoding="utf-8"), Path(n.ses),
                Path(n.medya), Path(n.cikti), n.altyazi, n.capcut)
    except (KurguHatasi, CapcutHatasi) as e:
        print(f"✗ {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
