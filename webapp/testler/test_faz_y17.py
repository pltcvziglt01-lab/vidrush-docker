#!/usr/bin/env python3
"""FAZ Y-17 — KAYNAK SESI MUTLAK SIFIR: METADATA DEGIL, GRAF KANITI.

⚠ OLCULEN KUSUR (`Y17-KAYNAK-SES-TOTOLOJI`) — iki bagimsiz ajan buldu,
kodda dogruladim: `gercek_qa.sahneleri_cevir`
    "ses_kanali": _s(pv.get("ses_kanali")) or _sg.KAYNAK_SES_POLITIKASI
Provenans `ses_kanali` beyan etmiyorsa (NORMAL durum) DENETLENEN ALANA
POLITIKANIN KENDISI ("sifir") yaziliyordu. `ses_gurultu.
kaynak_ses_sozlesmesi` tam o alani `KAYNAK_SES_KABUL_EDILEN`'e karsi
kontrol ediyor ve o kume BOS STRINGI de kabul ediyordu. Yani kapi KENDI
GIRDISINI URETIYORDU: `GERCEK-KAYNAK-SES-SIZINTI` (bir FAIL kodu)
YAPISAL OLARAK ERISILEMEZ olu koddu.

⚠ IKINCI KUSUR (`Y17-GRAF-KANITI-YOK`): "kaynak sesi sifir" iddiasi
`hizli_render`'in klip girdilerini ses olarak MAP ETMEMESINE dayaniyordu
— dogru bir yapisal garanti, ama HICBIR YERDE OLCULMUYOR ve TESLIM EDILEN
ARTEFAKTA BAGLANMIYORDU. Bir gun bir `-map 0:a` eklense kimse gormezdi.

── SOZLESME ──
  · Her BASARILI video segmenti icin, uretilen KOMUTUN kendisinden
    cikarilan kanit kaydedilir: klip girdi indeksleri, ses map'leri ve
    klip sesinin map EDILIP EDILMEDIGI.
  · Kayit IS ANAHTARLI ve SEGMENT ANAHTARLI (retry iki kez saymaz).
  · Rapor NIHAI artefakta damgalanir.
  · Graf TAM degilse (render edilen segment sayisi kadar kayit yoksa) ->
    `SOURCE-AUDIO-ZERO-OLCULMEDI`. ⚠ 0 UYDURULMAZ.
  · Herhangi bir segmentte klip sesi map edilmisse -> `SOURCE-AUDIO-LEAK`.
  · `kabul_105` YALNIZCA `olculdu is True` + mutlak sifir esigini okur;
    metadata beyani KABUL URETEMEZ.

⚠ Mac'te medya/ses fixture URETILMEZ. Gercek ffmpeg olcumu uzak pilotta.

Kosum: .venv-test/bin/python3 webapp/testler/test_faz_y17.py
"""
from __future__ import annotations

import ast
import hashlib
import os
import shutil as _sh
import sys
import tempfile as _tf

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)

gecen, basarisiz = 0, []


def kontrol(ad, kosul, detay=""):
    global gecen
    if kosul:
        gecen += 1
        print(f"  ok   {ad}")
    else:
        basarisiz.append(f"{ad} — {detay}")
        print(f"  XX   {ad}  {detay}")


def blok(ad):
    print(f"\n── {ad} ──")


_pkok = _tf.mkdtemp(prefix="y17_kok_")
_uret_kaynak = os.path.join(KOK, "..", "app", "uret.py")
if os.path.exists(_uret_kaynak):
    _sh.copy(_uret_kaynak, os.path.join(_pkok, "uret.py"))
sys.path.insert(0, _pkok)
os.environ["VIDRUSH_KOK"] = os.path.abspath(_pkok)
os.environ.setdefault("CIKTI_DIR", os.path.join(_pkok, "ciktilar"))

import gercek_qa as GQ      # noqa: E402
import hizli_render as HR   # noqa: E402
import kabul_105 as KB      # noqa: E402
from editor import ses_gurultu as SG   # noqa: E402

_HRK = open(os.path.join(KOK, "hizli_render.py"), encoding="utf-8").read()
_GQK = open(os.path.join(KOK, "gercek_qa.py"), encoding="utf-8").read()


blok("Y-17/1 — TOTOLOJI KALDIRILDI")

kontrol("karar kodu belgelendi: Y17-KAYNAK-SES-TOTOLOJI",
        "Y17-KAYNAK-SES-TOTOLOJI" in _GQK, "karar kodda belgelenmemis")
kontrol("karar kodu belgelendi: Y17-GRAF-KANITI-YOK",
        "Y17-GRAF-KANITI-YOK" in _HRK)

# ⚠ AST: politika sabiti artik DENETLENEN ALANA yazilmamali.
_gq_agac = ast.parse(_GQK)
_cevir = next((n for n in ast.walk(_gq_agac)
               if isinstance(n, ast.FunctionDef) and n.name == "sahneleri_cevir"),
              None)
_cevir_kaynak = ast.dump(_cevir) if _cevir else ""
kontrol("sahneleri_cevir politikayi ses_kanali'na YAZMIYOR",
        "KAYNAK_SES_POLITIKASI" not in _cevir_kaynak,
        "denetlenen alan politikanin kendisiyle dolduruluyor")

_s = GQ.sahneleri_cevir([{"medya": "k.mp4", "tur": "video", "sure": 4.0}])
kontrol("beyan yoksa ses_kanali BEYAN-YOK",
        _s and _s[0].get("ses_kanali") == "BEYAN-YOK",
        f"{_s[0].get('ses_kanali') if _s else None!r}")

kontrol("bos string artik KABUL EDILEN kumede degil",
        "" not in SG.KAYNAK_SES_KABUL_EDILEN,
        f"{SG.KAYNAK_SES_KABUL_EDILEN}")
_soz = SG.kaynak_ses_sozlesmesi(_s)
kontrol("beyansiz sahne SOZLESMEYI IHLAL eder (kapi artik erisilebilir)",
        _soz.get("temiz") is False, f"{_soz}")


blok("Y-17/2 — GRAF KANITI IS + SEGMENT ANAHTARLI")

for ad in ("ses_grafi_kaydet", "ses_map_kaniti"):
    kontrol(f"hizli_render disa aciyor: {ad}", hasattr(HR, ad), "tanimli degil")
for ad in ("kaynak_ses_olcumu", "KOD_KAYNAK_SES_OLCULMEDI",
           "KOD_KAYNAK_SES_LEAK"):
    kontrol(f"gercek_qa disa aciyor: {ad}", hasattr(GQ, ad), "tanimli degil")

HR.jl_sifirla("j17_A")
HR.ses_grafi_kaydet("j17_A", "seg0",
                    {"klip_girdileri": [0], "ses_maplari": ["1:a"],
                     "kaynak_ses_map": False})
HR.ses_grafi_kaydet("j17_A", "seg0",       # RETRY — ezilmeli
                    {"klip_girdileri": [0], "ses_maplari": ["1:a"],
                     "kaynak_ses_map": False})
HR.ses_grafi_kaydet("j17_A", "seg1",
                    {"klip_girdileri": [0], "ses_maplari": ["1:a"],
                     "kaynak_ses_map": False})
_ra = HR.render_raporu("j17_A")
kontrol("retry ayni segmenti iki kez saymaz",
        len(_ra.get("ses_kayitlari") or {}) == 2, f"{_ra.get('ses_kayitlari')}")

HR.jl_sifirla("j17_B")
HR.ses_grafi_kaydet("j17_B", "seg0",
                    {"klip_girdileri": [0], "ses_maplari": ["0:a"],
                     "kaynak_ses_map": True})
kontrol("baska ise SIZMAZ",
        HR.render_raporu("j17_A").get("ses_kayitlari", {})
        .get("seg0", {}).get("kaynak_ses_map") is False,
        f"{HR.render_raporu('j17_A').get('ses_kayitlari')}")
kontrol("bilinmeyen ise YAZILMAZ",
        (HR.ses_grafi_kaydet("j17-yok", "s", {"kaynak_ses_map": False}),
         HR.render_raporu("j17-yok").get("ses_kayitlari") == {})[1])


blok("Y-17/3 — KOMUTTAN KANIT CIKARIMI (saf fonksiyon)")

_temiz_komut = ["ffmpeg", "-y", "-stream_loop", "-1", "-i", "/k/klip.mp4",
                "-i", "/t/tts.mp3", "-filter_complex", "[0:v]scale[v]",
                "-map", "[v]", "-map", "1:a", "/o/seg.mp4"]
_k = HR.ses_map_kaniti(_temiz_komut, klip_girdileri=[0])
kontrol("temiz komutta kaynak_ses_map False",
        _k.get("kaynak_ses_map") is False, f"{_k}")
kontrol("ses maplari cikarildi", _k.get("ses_maplari") == ["1:a"], f"{_k}")

_sizinti = list(_temiz_komut)
_sizinti[_sizinti.index("1:a")] = "0:a"
_k2 = HR.ses_map_kaniti(_sizinti, klip_girdileri=[0])
kontrol("klip sesi map edilirse YAKALANIR",
        _k2.get("kaynak_ses_map") is True, f"{_k2}")

_k3 = HR.ses_map_kaniti(_temiz_komut + ["-map", "0:a"], klip_girdileri=[0])
kontrol("ek klip ses map'i de YAKALANIR",
        _k3.get("kaynak_ses_map") is True, f"{_k3}")


blok("Y-17/4 — OLCUM: GRAF TAM + SIFIR")

with _tf.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
    f.write(b"y17-artefakt")
    _yol = f.name
_ozet = hashlib.sha256(b"y17-artefakt").hexdigest()
try:
    HR.jl_damgala("j17_A", _yol)
    _rap = HR.render_raporu("j17_A")
    # ⚠ SAYISAL stem olcumu ZORUNLU (denetim karsi ornegi, asagida ayrica
    # kilitleniyor): yapisal graf kaniti TEK BASINA "olculdu" saymaz.
    _o = GQ.kaynak_ses_olcumu(ses_raporu=_rap, artefakt_sha256=_ozet,
                              beklenen_segment=2,
                              leakage_db=-91.0, sample_peak=0.0)
    kontrol("olculdu=True", _o.get("olculdu") is True, f"{_o}")
    kontrol("sizinti yok", _o.get("sizinti") is False and not _o.get("kod"),
            f"{_o}")
    kontrol("segment sayisi raporlanir", _o.get("segment") == 2, f"{_o}")
    kontrol("graf tam", _o.get("graf_tam") is True, f"{_o}")

    blok("Y-17/5 — GRAF EKSIKSE OLCULMEDI (0 UYDURULMAZ)")

    _eksik = GQ.kaynak_ses_olcumu(ses_raporu=_rap, artefakt_sha256=_ozet,
                                  beklenen_segment=5,
                                  leakage_db=-91.0, sample_peak=0.0)
    kontrol("eksik graf -> olculdu=False", _eksik.get("olculdu") is False,
            f"{_eksik}")
    kontrol("stabil kod SOURCE-AUDIO-ZERO-OLCULMEDI",
            _eksik.get("kod") == GQ.KOD_KAYNAK_SES_OLCULMEDI,
            f"kod={_eksik.get('kod')!r}")
    kontrol("olculmeyende sizinti SAYI/BOOL olarak sunulmaz",
            _eksik.get("sizinti") is None, f"{_eksik}")

    blok("Y-17/6 — SIZINTI ENJEKSIYONU -> FAIL")

    HR.jl_sifirla("j17_L")
    HR.ses_grafi_kaydet("j17_L", "seg0",
                        {"klip_girdileri": [0], "ses_maplari": ["1:a"],
                         "kaynak_ses_map": False})
    HR.ses_grafi_kaydet("j17_L", "seg1",
                        {"klip_girdileri": [0], "ses_maplari": ["0:a"],
                         "kaynak_ses_map": True})
    HR.jl_damgala("j17_L", _yol)
    _ol = GQ.kaynak_ses_olcumu(ses_raporu=HR.render_raporu("j17_L"),
                               artefakt_sha256=_ozet, beklenen_segment=2,
                               leakage_db=-91.0, sample_peak=0.0)
    kontrol("tek segment sizintisi bile YAKALANIR",
            _ol.get("sizinti") is True, f"{_ol}")
    kontrol("stabil kod SOURCE-AUDIO-LEAK",
            _ol.get("kod") == GQ.KOD_KAYNAK_SES_LEAK, f"kod={_ol.get('kod')!r}")
    kontrol("sizan segment ADLARI raporlanir",
            _ol.get("sizan_segmentler") == ["seg1"], f"{_ol}")
    kontrol("sizinti varken olculdu=True (olcum kosuldu, hukum FAIL)",
            _ol.get("olculdu") is True, f"{_ol}")

    blok("Y-17/7 — BAYAT/DAMGASIZ RAPOR REDDEDILIR")

    _bayat = GQ.kaynak_ses_olcumu(ses_raporu=_rap, artefakt_sha256="f" * 64,
                                  beklenen_segment=2,
                                  leakage_db=-91.0, sample_peak=0.0)
    kontrol("baska artefakta ait rapor REDDEDILIR",
            _bayat.get("olculdu") is False, f"{_bayat}")
    kontrol("bayat kod", _bayat.get("kod") == GQ.KOD_KAYNAK_SES_OLCULMEDI,
            f"kod={_bayat.get('kod')!r}")
finally:
    try:
        os.unlink(_yol)
    except OSError:
        pass

_yok = GQ.kaynak_ses_olcumu()
kontrol("rapor yoksa olculdu=False", _yok.get("olculdu") is False, f"{_yok}")


blok("Y-17/8 — OLCULEN TEPE DEGERI (varsa) MUTLAK SIFIR ESIGI")

_pik = GQ.kaynak_ses_olcumu(
    ses_raporu={"olculdu": True, "artefakt_sha256": "a" * 64,
                "ses_kayitlari": {"s0": {"kaynak_ses_map": False}}},
    artefakt_sha256="a" * 64, beklenen_segment=1,
    leakage_db=-91.0, sample_peak=0.0)
kontrol("olculen tepe/leak raporlanir",
        _pik.get("leakage_db") == -91.0 and _pik.get("sample_peak") == 0.0,
        f"{_pik}")
kontrol("mutlak sifir esigi karsilandi", _pik.get("sizinti") is False,
        f"{_pik}")

_pik2 = GQ.kaynak_ses_olcumu(
    ses_raporu={"olculdu": True, "artefakt_sha256": "a" * 64,
                "ses_kayitlari": {"s0": {"kaynak_ses_map": False}}},
    artefakt_sha256="a" * 64, beklenen_segment=1,
    leakage_db=-12.0, sample_peak=0.31)
kontrol("olculen tepe esigi asarsa SIZINTI",
        _pik2.get("sizinti") is True
        and _pik2.get("kod") == GQ.KOD_KAYNAK_SES_LEAK, f"{_pik2}")


blok("Y-17/8b — YAPISAL BEYAN TEK BASINA OLCUM DEGILDIR (karsi ornek)")

# ⚠ DENETIM KARSI ORNEGI (`Y17-YAPISAL-BEYAN-OLCUM-SANILDI`): graf TAM,
# tum `kaynak_ses_map` False, ama SAYISAL stem olcumu YOK. Onceki surumde
# bu `olculdu=True, sizinti=False` donuyordu — yani kabul, komutun neyi
# map ettigine dayaniyordu; URETILEN SESIN sessiz oldugu OLCULMEMISTI.
_yapisal = GQ.kaynak_ses_olcumu(
    ses_raporu={"olculdu": True, "artefakt_sha256": "a" * 64,
                "ses_kayitlari": {"s0": {"kaynak_ses_map": False},
                                  "s1": {"kaynak_ses_map": False}}},
    artefakt_sha256="a" * 64, beklenen_segment=2)
kontrol("graf tam + map yok AMA sayisal olcum yok -> olculdu=False",
        _yapisal.get("olculdu") is False, f"{_yapisal}")
kontrol("stabil kod SOURCE-AUDIO-ZERO-OLCULMEDI",
        _yapisal.get("kod") == GQ.KOD_KAYNAK_SES_OLCULMEDI,
        f"kod={_yapisal.get('kod')!r}")
kontrol("sizinti BOOL olarak SUNULMAZ", _yapisal.get("sizinti") is None,
        f"{_yapisal}")
kontrol("graf kaniti yine de raporlanir (tani icin)",
        _yapisal.get("graf_tam") is True, f"{_yapisal}")
kontrol("TEK BASINA leakage_db yetmez",
        GQ.kaynak_ses_olcumu(
            ses_raporu={"olculdu": True, "artefakt_sha256": "a" * 64,
                        "ses_kayitlari": {"s0": {"kaynak_ses_map": False}}},
            artefakt_sha256="a" * 64, beklenen_segment=1,
            leakage_db=-91.0).get("olculdu") is False)
kontrol("TEK BASINA sample_peak yetmez",
        GQ.kaynak_ses_olcumu(
            ses_raporu={"olculdu": True, "artefakt_sha256": "a" * 64,
                        "ses_kayitlari": {"s0": {"kaynak_ses_map": False}}},
            artefakt_sha256="a" * 64, beklenen_segment=1,
            sample_peak=0.0).get("olculdu") is False)
kontrol("kabul kriteri de bu karsi ornekte FAIL verir",
        KB._k_kaynak_ses({"kaynak_ses": _yapisal})[0] is False, f"{_yapisal}")


blok("Y-17/8c — SAYISAL STEM URETICISI (saf komut kurulumu)")

for ad in ("kaynak_ses_stem_komutu", "astats_oku"):
    kontrol(f"hizli_render disa aciyor: {ad}", hasattr(HR, ad), "tanimli degil")

_seg_komut = ["ffmpeg", "-y", "-stream_loop", "-1", "-i", "/k/klip.mp4",
              "-i", "/t/tts.mp3", "-filter_complex", "[0:v]scale[v]",
              "-map", "[v]", "-map", "1:a", "-c:v", "libx264",
              "-t", "4.250", "/o/seg.mp4"]
_sk = HR.kaynak_ses_stem_komutu(_seg_komut, "/tmp/src_stem.wav",
                                ses_maplari=["1:a"])
_skm = " ".join(_sk)
kontrol("anlati girdisi SESSIZLIKLE degistirilir",
        "anullsrc" in _skm and "/t/tts.mp3" not in _skm, f"{_skm}")
kontrol("klip girdisi KORUNUR (katki olculecek)",
        "/k/klip.mp4" in _sk, f"{_sk}")
kontrol("cikti stem yoluna yazilir", "/tmp/src_stem.wav" in _sk, f"{_sk}")
kontrol("yalniz ses yazilir", "-vn" in _sk and "pcm_s16le" in _sk, f"{_sk}")
kontrol("anlati girdisi yoksa komut URETILMEZ (fail-closed)",
        HR.kaynak_ses_stem_komutu(["ffmpeg", "-i", "/k/a.mp4", "/o/x.mp4"],
                                  "/tmp/s.wav", ses_maplari=["0:a"]) == [])
kontrol("ses map'i yoksa komut URETILMEZ",
        HR.kaynak_ses_stem_komutu(_seg_komut, "/tmp/s.wav",
                                  ses_maplari=[]) == [])
# ⚠ Y17-STEM-VIDEO-CIKISI: video ile ilgili hicbir sey tasinmamali.
kontrol("stem komutunda filtre grafigi YOK",
        "-filter_complex" not in _sk, f"{_sk}")
kontrol("stem komutunda video map'i YOK",
        "[v]" not in " ".join(_sk), f"{_sk}")
kontrol("stem komutunda video kodlayici YOK",
        "libx264" not in _sk, f"{_sk}")
kontrol("stem komutu ayni ses map'ini kullanir", "1:a" in _sk, f"{_sk}")
# ⚠ Y17-STEM-SONSUZ-KAYNAK: `anullsrc` sonsuzdur; SONLU `-t` SART.
kontrol("stem komutu SONLU sure tasir (-t)",
        "-t" in _sk and "4.250" in _sk, f"{_sk}")
kontrol("sure bulunamazsa komut URETILMEZ (sonsuz kosu yok)",
        HR.kaynak_ses_stem_komutu(
            [a for a in _seg_komut if a not in ("-t", "4.250")],
            "/tmp/s.wav", ses_maplari=["1:a"]) == [],
        "sonsuz anullsrc ile komut uretiliyor")
# ⚠ Y17-STEM-METRIK-YOK: astats olmadan ffmpeg metrik YAZMAZ.
kontrol("stem komutunda astats filtresi VAR",
        any("astats" in str(a) for a in _sk), f"{_sk}")


blok("Y-17/8d — URETIMDE GERCEKTEN CAGRILIYOR (erisilebilirlik)")

# ⚠ OLCULEN KUSUR (denetim): `kaynak_ses_stem_komutu`/`astats_oku` TANIMLI
# ama URETIMDE HIC CAGRILMIYORDU -> her gercek is
# `SOURCE-AUDIO-ZERO-OLCULMEDI` kalirdi (ulasilamaz kriter).
kontrol("hizli_render ses_stem_olc'u CAGIRIYOR",
        any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
            and n.func.id == "ses_stem_olc"
            for n in ast.walk(ast.parse(_HRK))),
        "sayisal olcum uretimde hic kosmuyor")

_cagrilan = []


def _sahte_kos(sonuc):
    def _k(komut):
        _cagrilan.append(list(komut))
        return sonuc
    return _k


HR.jl_sifirla("j17_S")
_stem = os.path.join(_pkok, "stem.wav")
with open(_stem, "wb") as f:
    f.write(b"x" * 64)
_k4 = HR.ses_stem_olc(
    "j17_S", "seg0", _seg_komut, [0], _stem,
    kosucu=_sahte_kos({"rc": 0, "stdout": "",
                       "stderr": "Peak level dB: -inf\nRMS level dB: -inf\n"}))
kontrol("stem komutu GERCEKTEN kosuldu", len(_cagrilan) == 1, f"{_cagrilan}")
kontrol("olcum kayda yazildi",
        HR.render_raporu("j17_S")["ses_kayitlari"]["seg0"]["sample_peak"] == 0.0,
        f"{HR.render_raporu('j17_S').get('ses_kayitlari')}")
kontrol("aggregate rapora tasindi",
        HR.render_raporu("j17_S").get("kaynak_ses_peak") == 0.0,
        f"{HR.render_raporu('j17_S').get('kaynak_ses_peak')}")

with open(_stem, "wb") as f:
    f.write(b"x" * 64)
HR.jl_sifirla("j17_F")
HR.ses_stem_olc("j17_F", "seg0", _seg_komut, [0], _stem,
                kosucu=_sahte_kos({"rc": 1, "stdout": "", "stderr": "hata"}))
kontrol("rc!=0 ise SAYI YAZILMAZ",
        HR.render_raporu("j17_F")["ses_kayitlari"]["seg0"]["sample_peak"]
        is None,
        f"{HR.render_raporu('j17_F').get('ses_kayitlari')}")
kontrol("olcumsuz segment aggregate'i None yapar",
        HR.render_raporu("j17_F").get("kaynak_ses_peak") is None)

with open(_stem, "wb") as f:
    f.write(b"x" * 64)
HR.jl_sifirla("j17_P")
HR.ses_stem_olc("j17_P", "seg0", _seg_komut, [0], _stem,
                kosucu=_sahte_kos({"rc": 0, "stdout": "",
                                   "stderr": "cozulemeyen cikti"}))
kontrol("astats cozulemezse SAYI YAZILMAZ",
        HR.render_raporu("j17_P")["ses_kayitlari"]["seg0"]["sample_peak"]
        is None)

for _ in range(2):
    with open(_stem, "wb") as f:
        f.write(b"x" * 64)
    HR.ses_stem_olc("j17_S", "seg0", _seg_komut, [0], _stem,
                    kosucu=_sahte_kos({"rc": 0, "stdout": "",
                                       "stderr": "Peak level dB: -inf\n"
                                                 "RMS level dB: -inf\n"}))
# ⚠ Kosucuya GIDEN komut sonlu ve metrikli olmali (davranis enjeksiyonu).
kontrol("kosucuya giden komut SONLU sure tasiyor",
        "-t" in _cagrilan[0], f"{_cagrilan[0]}")
kontrol("kosucuya giden komut astats iceriyor",
        any("astats" in str(a) for a in _cagrilan[0]), f"{_cagrilan[0]}")

# ── SESSIZ stem (sizinti yok) -> -inf parse, tepe 0.0 ──
with open(_stem, "wb") as f:
    f.write(b"x" * 64)
HR.jl_sifirla("j17_Q")
HR.ses_stem_olc("j17_Q", "seg0", _seg_komut, [0], _stem,
                kosucu=_sahte_kos({"rc": 0, "stdout": "",
                                   "stderr": "[Parsed_astats_0 @ 0x1] "
                                             "Peak level dB: -inf\n"
                                             "[Parsed_astats_0 @ 0x1] "
                                             "RMS level dB: -inf\n"}))
_q = HR.render_raporu("j17_Q")["ses_kayitlari"]["seg0"]
kontrol("SESSIZ stem -> tepe 0.0", _q.get("sample_peak") == 0.0, f"{_q}")
kontrol("SESSIZ stem -> leak taban degeri", _q.get("leakage_db") == -120.0,
        f"{_q}")
kontrol("SESSIZ stem kabul URETIR",
        KB._k_kaynak_ses({"kaynak_ses": GQ.kaynak_ses_olcumu(
            ses_raporu={**HR.render_raporu("j17_Q"), "olculdu": True,
                        "artefakt_sha256": "a" * 64},
            artefakt_sha256="a" * 64, beklenen_segment=1)})[0] is True)

# ── SIZINTILI stem -> sayisal parse, kabul FAIL ──
with open(_stem, "wb") as f:
    f.write(b"x" * 64)
HR.jl_sifirla("j17_Z")
HR.ses_stem_olc("j17_Z", "seg0", _seg_komut, [0], _stem,
                kosucu=_sahte_kos({"rc": 0, "stdout": "",
                                   "stderr": "[Parsed_astats_0 @ 0x1] "
                                             "Peak level dB: -10.5\n"
                                             "[Parsed_astats_0 @ 0x1] "
                                             "RMS level dB: -18.2\n"}))
_z = HR.render_raporu("j17_Z")["ses_kayitlari"]["seg0"]
kontrol("SIZINTILI stem -> tepe > esik",
        (_z.get("sample_peak") or 0) > GQ.KAYNAK_SES_TEPE_TAVANI, f"{_z}")
kontrol("SIZINTILI stem -> leak sayisal", _z.get("leakage_db") == -18.2, f"{_z}")
_zo = GQ.kaynak_ses_olcumu(
    ses_raporu={**HR.render_raporu("j17_Z"), "olculdu": True,
                "artefakt_sha256": "a" * 64},
    artefakt_sha256="a" * 64, beklenen_segment=1)
kontrol("SIZINTILI stem -> SOURCE-AUDIO-LEAK",
        _zo.get("sizinti") is True and _zo.get("kod") == GQ.KOD_KAYNAK_SES_LEAK,
        f"{_zo}")
kontrol("SIZINTILI stem kabul URETMEZ",
        KB._k_kaynak_ses({"kaynak_ses": _zo})[0] is False, f"{_zo}")

kontrol("retry IDEMPOTENT (tek kayit)",
        len(HR.render_raporu("j17_S").get("ses_kayitlari") or {}) == 1,
        f"{HR.render_raporu('j17_S').get('ses_kayitlari')}")

_dijital_sessiz = HR.astats_oku(
    "[Parsed_astats_0 @ 0x1] Peak level dB: -inf\n"
    "[Parsed_astats_0 @ 0x1] RMS level dB: -inf\n")
kontrol("dijital sessizlikte tepe 0.0", _dijital_sessiz.get("sample_peak") == 0.0,
        f"{_dijital_sessiz}")
_sizintili = HR.astats_oku(
    "[Parsed_astats_0 @ 0x1] Peak level dB: -10.5\n"
    "[Parsed_astats_0 @ 0x1] RMS level dB: -18.2\n")
kontrol("sizintili stem tepe > 0", (_sizintili.get("sample_peak") or 0) > 0.1,
        f"{_sizintili}")
kontrol("astats okunamazsa None", HR.astats_oku("").get("sample_peak") is None)


blok("Y-17/9 — KABUL KRITERI YALNIZ OLCUMU OKUR")

kontrol("olculdu + sizinti yok + SAYISAL olcum -> PASS",
        KB._k_kaynak_ses({"kaynak_ses": {
            "olculdu": True, "sizinti": False, "graf_tam": True,
            "artefakt_sha256": "a" * 64,
            "leakage_db": -91.0, "sample_peak": 0.0}})[0] is True)
kontrol("sayisal olcum YOKSA kabul FAIL",
        KB._k_kaynak_ses({"kaynak_ses": {
            "olculdu": True, "sizinti": False, "graf_tam": True,
            "artefakt_sha256": "a" * 64}})[0] is False,
        "yapisal beyan kabul uretiyor")
kontrol("artefakt SHA yoksa kabul FAIL",
        KB._k_kaynak_ses({"kaynak_ses": {
            "olculdu": True, "sizinti": False, "graf_tam": True,
            "leakage_db": -91.0, "sample_peak": 0.0}})[0] is False,
        "olcum artefakta bagli olmadan geciyor")
kontrol("sizinti -> FAIL",
        KB._k_kaynak_ses({"kaynak_ses": {
            "olculdu": True, "sizinti": True, "graf_tam": True}})[0] is False)
kontrol("olculmemis -> FAIL",
        KB._k_kaynak_ses({"kaynak_ses": {
            "olculdu": False, "sizinti": False}})[0] is False)
kontrol("graf eksik -> FAIL",
        KB._k_kaynak_ses({"kaynak_ses": {
            "olculdu": True, "sizinti": False, "graf_tam": False}})[0]
        is False)
# ⚠ METADATA BEYANI TEK BASINA KABUL URETEMEZ.
kontrol("yalniz metadata beyani -> FAIL",
        KB._k_kaynak_ses({"kaynak_ses": {
            "ses_kanali": "sifir", "olculdu": True}})[0] is False,
        "beyan hala kabul uretiyor")

_kb_sabit = {n.value for n in ast.walk(ast.parse(
    open(os.path.join(KOK, "kabul_105.py"), encoding="utf-8").read()))
    if isinstance(n, ast.Constant) and isinstance(n.value, str)}
kontrol("kabul kriteri `ses_kanali` metadata alanini OKUMUYOR",
        "ses_kanali" not in _kb_sabit, "kabul metadata okuyor")
kontrol("kabul kriteri `sizinti`/`graf_tam` okuyor",
        {"sizinti", "graf_tam"} <= _kb_sabit, f"okunan: {_kb_sabit & {'sizinti', 'graf_tam'}}")


blok("Y-17/10 — HAT BAGLANTISI")

kontrol("hizli_render ses grafi kanitini KAYDEDIYOR",
        any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
            and n.func.id == "ses_grafi_kaydet"
            for n in ast.walk(ast.parse(_HRK))),
        "kanit hicbir yerde kaydedilmiyor")
_PLK = open(os.path.join(KOK, "pipeline.py"), encoding="utf-8").read()
kontrol("pipeline kaynak ses olcumunu kosuyor",
        "kaynak_ses_olcumu(" in _PLK, "olcum hatta bagli degil")
kontrol("pipeline SAYISAL olcumu de gecirir",
        "kaynak_ses_leak_db" in _PLK and "kaynak_ses_peak" in _PLK,
        "aggregate sayisal olcum olcume gitmiyor")


print(f"\n{'=' * 62}\nGECEN: {gecen}   BASARISIZ: {len(basarisiz)}")
for b in basarisiz:
    print(f"  XX {b}")
sys.exit(1 if basarisiz else 0)
