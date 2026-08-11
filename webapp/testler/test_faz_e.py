#!/usr/bin/env python3
"""FAZ E testleri — AGSIZ, Remotion/npm/TTS GEREKTIRMEZ.

Kapsam (kullanicinin listesi):
  ses prop sozlesmesi · eksik ses raporu · Audio zaman cizelgesi ·
  J/L cut + ducking · yol kopyalama · konu/gorsel kapilari

⚠ FAZ D ACIGI: V2 `scene.ses` alanini TASIYORDU ama hicbir <Audio> yoktu;
video sessiz cikiyordu. Bu dosyanin ilk isi o durumun bir daha olusamayacagini
kanitlamak: TS tarafinda Audio VAR, Python tarafinda beyan edilen ses KAYBOLURSA
kapi FAIL veriyor.

Kosum: python3 webapp/testler/test_faz_e.py
"""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)

from editor import adapter, motion, profil, remotion_v2  # noqa: E402
from medya import siralama  # noqa: E402

STUDIO = remotion_v2.STUDIO
EDITORV2 = os.path.join(STUDIO, "src", "editorv2")
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


def _kod(ad: str) -> str:
    """Yorumsuz TS kaynagi (yorumda gecen ifade kod sayilmaz)."""
    m = open(os.path.join(EDITORV2, ad), encoding="utf-8").read()
    m = re.sub(r"/\*.*?\*/", "", m, flags=re.S)
    m = re.sub(r"^\s*//.*$", "", m, flags=re.M)
    return m


P = profil.profil("premium-modern")
SES_TS = _kod("Ses.tsx")
EV2_TS = _kod("EditorV2.tsx")
SOZ_TS = open(remotion_v2.SOZLESME_TS, encoding="utf-8").read()

# ═══════════ 1) AUDIO ZAMAN CIZELGESI GERCEKTEN VAR MI ═══════════
blok("Audio zaman cizelgesi (Faz D acigi kapandi mi)")
kontrol("Ses.tsx dosyasi var", os.path.exists(os.path.join(EDITORV2, "Ses.tsx")))
kontrol("Remotion Audio bileseni IMPORT edilmis",
        re.search(r"import\s*\{[^}]*\bAudio\b[^}]*\}\s*from\s*'remotion'", SES_TS)
        is not None)
kontrol("Audio GERCEKTEN kullanilmis (<Audio)", "<Audio" in SES_TS)
kontrol("master anlatim icin Audio var", "ayar.anlatim" in SES_TS
        and SES_TS.count("<Audio") >= 3, f"{SES_TS.count('<Audio')} adet")
kontrol("EditorV2 ses cizelgesini KOK seviyede cagiriyor",
        "<SesZamanCizelgesi" in EV2_TS)
# ⚠ Ilk surumde `EV2_TS.find("sahneler.map")` kullaniyordum ve `kareHesapla`
# icindeki `sahneler.map(...)` cagrisini buluyordu (dosyanin cok basi), yani
# test yanlis yeri karsilastiriyordu. Artik RENDER agacindaki cagri araniyor.
_render_map = EV2_TS.find("{sahneler.map((sh, i)")
kontrol("ses cizelgesi sahne Sequence'lerinin DISINDA",
        0 < EV2_TS.find("<SesZamanCizelgesi") < _render_map,
        f"ses={EV2_TS.find('<SesZamanCizelgesi')} sahne={_render_map}")
kontrol("sahne Sequence'i icinde <Audio YOK",
        "<Audio" not in EV2_TS,
        "sahne icine girerse J/L cut kirpilir")
kontrol("mevcut Video.tsx (V1) ses yolu DEGISMEDI",
        "<Audio src={kaynakCoz(sahne.ses)} />" in open(
            os.path.join(STUDIO, "src", "Video.tsx"), encoding="utf-8").read())

# ═══════════ 2) SES PROP SOZLESMESI ═══════════
blok("ses prop sozlesmesi (Python <-> TS)")
for alan in ("anlatim", "anlatim_bas_sn", "anlatim_seviye",
             "anlatim_araliklari", "ambans", "ambans_seviye", "muzik",
             "muzik_seviye", "ducking", "yapay_ses", "hedef_lufs",
             "hedef_tp_dbtp"):
    kontrol(f"SesAyari alani tanimli: {alan}", f"{alan}?:" in SOZ_TS
            or f"{alan}:" in SOZ_TS)
for alan in ("ses_bas_sn", "ses_seviye", "j_cut_sn", "l_cut_sn"):
    kontrol(f"EditorSahne ses alani tanimli: {alan}", f"{alan}?:" in SOZ_TS)
kontrol("EditorV2Props.ses tanimli", re.search(r"\n  ses\?:\s*SesAyari", SOZ_TS)
        is not None)

# Python tarafinin urettigi ses sozlugu TS alanlariyla ORTUSUYOR mu
_ses_props = {"anlatim": "editorv2/x/anlatim.wav", "anlatim_seviye": 1.0,
              "anlatim_araliklari": [[0, 2]], "ambans": ["editorv2/x/amb.wav"],
              "ambans_seviye": 0.22, "ducking": {"ambans": 0.3},
              "yapay_ses": True, "hedef_lufs": -14.0, "hedef_tp_dbtp": -1.0}
_ts_ses_blok = SOZ_TS[SOZ_TS.find("export interface SesAyari"):
                      SOZ_TS.find("export interface EditorV2Props")]
_ts_alanlar = set(re.findall(r"^\s{2}(\w+)\??:", _ts_ses_blok, re.M))
kontrol("Python ses sozlugunun TUM anahtarlari TS'te var",
        set(_ses_props) <= _ts_alanlar,
        f"TS'te yok: {sorted(set(_ses_props) - _ts_alanlar)}")


def _sahne(i=0, ses="/tmp/yok_bu.wav", j=False, l=False):
    sp = motion.kamera_spec("push-in", 4.0, "tam", p=P).sozluk()
    sp["beat_id"] = f"bE{i}"
    return {"beat_id": f"bE{i}", "scene_id": f"sE{i}", "fact_id": "f001",
            "asset_id": f"aE{i}", "saglayici": "wikimedia", "lisans": "cc0",
            "medya_turu": "image", "medya_yolu": "", "sure_sn": 4.0,
            "bas_sn": 0.0, "islev": "kanit", "perde": "gelisme",
            "cekim_turu": "archive", "hareket": "push-in", "kadraj": "tam",
            "kaynak_aralik": [0, 4], "j_cut": j, "l_cut": l, "altyazi": [],
            "motion": [sp], "gerekce": "test", "ses_yolu": ses}


# ═══════════ 3) EKSIK SES RAPORU (sessizce kaybolmaz) ═══════════
blok("eksik ses: sessizce kaybolmaz")
_gec = tempfile.mkdtemp(prefix="fe_")
try:
    _ses = os.path.join(_gec, "ger.wav")
    with open(_ses, "wb") as f:
        f.write(b"RIFF" + b"0" * 6000)

    # (a) BEYAN EDILEN ama var olmayan ses -> props_hazirla kayip yazar
    ham = {"fps": 30, "genislik": 1280, "yukseklik": 720,
           "gecis_modu": "sinematik", "altyazi_stili": "yok",
           "sahneler": [_sahne(0)]}
    don = adapter.donustur(ham)
    pr = don.remotion_props
    pr["sahneler"][0]["ses"] = "/kesinlikle/yok/ses.wav"
    pr["ses"] = {"anlatim": "/kesinlikle/yok/anlatim.wav", "yapay_ses": True}
    hazir = remotion_v2.props_hazirla(pr, calisma_dizin=_gec)
    kayiplar = hazir.get("_kayip_varliklar") or []
    kontrol("kayip defteri props'a YAZILIYOR",
            "_kayip_varliklar" in hazir)
    kontrol("var olmayan sahne sesi kayip olarak kaydedildi",
            any("ses" in k["etiket"] for k in kayiplar),
            json.dumps(kayiplar))
    kontrol("var olmayan master anlatim kayip olarak kaydedildi",
            any(k["etiket"] == "ses.anlatim" for k in kayiplar),
            json.dumps([k["etiket"] for k in kayiplar]))
    _d = remotion_v2.dogrula(hazir)
    kontrol("kapi eksik sesi FAIL sayar", _d["durum"] == "FAIL", _d["durum"])
    kontrol("kod V2-SES-KAYIP",
            any(x["kod"] == "V2-SES-KAYIP" for x in _d["sorunlar"]),
            str([x["kod"] for x in _d["sorunlar"]]))

    class _Sayac:
        def __init__(self):
            self.adet = 0

        def __call__(self, k, t):
            self.adet += 1
            return {"rc": 0, "stdout": "", "stderr": ""}

    _s = _Sayac()
    _r = remotion_v2.render(hazir, "/tmp/fe_kayip.mp4", kosucu=_s)
    kontrol("eksik ses -> npx HIC cagrilmaz", _s.adet == 0 and _r["rc"] != 0,
            f"sayac={_s.adet} rc={_r['rc']}")

    # (b) HIC ses beyan edilmemis -> WARN (durustce), FAIL degil
    ham2 = {"fps": 30, "genislik": 1280, "yukseklik": 720,
            "gecis_modu": "sinematik", "altyazi_stili": "yok",
            "sahneler": [_sahne(1)]}
    pr2 = adapter.donustur(ham2).remotion_props
    pr2["sahneler"][0]["ses"] = ""
    hazir2 = remotion_v2.props_hazirla(pr2, calisma_dizin=_gec)
    _d2 = remotion_v2.dogrula(hazir2)
    kontrol("ses hic yoksa FAIL DEGIL", _d2["durum"] != "FAIL", _d2["durum"])
    kontrol("ses hic yoksa V2-ANLATIM-YOK uyarisi",
            any(x["kod"] == "V2-ANLATIM-YOK" and x["seviye"] == "warn"
                for x in _d2["sorunlar"]),
            str([x["kod"] for x in _d2["sorunlar"]]))
    kontrol("sessiz video render EDILEBILIR (uyariyla)",
            remotion_v2.render(hazir2, "/tmp/fe_sessiz.mp4",
                               kosucu=lambda k, t: {"rc": 0, "stdout": "",
                                                    "stderr": ""})["rc"] == 0)

    # (c) J/L isaretli ama ses yok -> uyari
    pr3 = adapter.donustur({"fps": 30, "genislik": 1280, "yukseklik": 720,
                            "gecis_modu": "sinematik", "altyazi_stili": "yok",
                            "sahneler": [_sahne(2, j=True, l=True)]}
                           ).remotion_props
    pr3["sahneler"][0]["ses"] = ""
    _d3 = remotion_v2.dogrula(pr3)
    kontrol("j/l cut isaretli ama ses yok -> V2-JL-SESSIZ",
            any(x["kod"] == "V2-JL-SESSIZ" for x in _d3["sorunlar"]),
            str([x["kod"] for x in _d3["sorunlar"]]))

    # (d) yapay ses isareti raporlanir
    pr4 = adapter.donustur({"fps": 30, "genislik": 1280, "yukseklik": 720,
                            "gecis_modu": "sinematik", "altyazi_stili": "yok",
                            "sahneler": [_sahne(3)]}).remotion_props
    pr4["sahneler"][0]["ses"] = ""
    pr4["ses"] = {"anlatim": "editorv2/x.wav", "yapay_ses": True}
    _d4 = remotion_v2.dogrula(pr4)
    kontrol("yapay ses BILGI olarak raporlanir",
            any(x["kod"] == "V2-YAPAY-SES" for x in _d4["sorunlar"]),
            str([x["kod"] for x in _d4["sorunlar"]]))

    # ═══════════ 4) SES YOLU KOPYALAMA ═══════════
    blok("ses yolu kopyalama (public/ altina)")
    pr5 = adapter.donustur({"fps": 30, "genislik": 1280, "yukseklik": 720,
                            "gecis_modu": "sinematik", "altyazi_stili": "yok",
                            "sahneler": [_sahne(4, ses=_ses)]}).remotion_props
    pr5["sahneler"][0]["ses"] = _ses
    pr5["ses"] = {"ambans": [_ses], "anlatim": _ses, "yapay_ses": True}
    h5 = remotion_v2.props_hazirla(pr5, calisma_dizin=_gec)
    kontrol("sahne sesi goreli public yoluna cevrildi",
            h5["sahneler"][0]["ses"].startswith("editorv2/"),
            h5["sahneler"][0]["ses"])
    kontrol("master anlatim goreli yola cevrildi",
            str(h5["ses"]["anlatim"]).startswith("editorv2/"),
            str(h5["ses"]["anlatim"]))
    kontrol("ambans listesi goreli yola cevrildi",
            all(str(x).startswith("editorv2/") for x in h5["ses"]["ambans"]),
            str(h5["ses"]["ambans"]))
    kontrol("ses dosyasi GERCEKTEN kopyalandi",
            os.path.exists(os.path.join(STUDIO, "public",
                                        h5["sahneler"][0]["ses"])))
    kontrol("kopyalama sonrasi kayip YOK", not (h5.get("_kayip_varliklar") or []),
            json.dumps(h5.get("_kayip_varliklar")))
    kontrol("props_hazirla girdiyi BOZMUYOR", pr5["sahneler"][0]["ses"] == _ses)
    kontrol("http ses yolu oldugu gibi gecer",
            remotion_v2.props_hazirla(
                {"sahneler": [], "ses": {"anlatim": "https://x.test/a.mp3"}},
                calisma_dizin=_gec)["ses"]["anlatim"] == "https://x.test/a.mp3")
finally:
    import shutil
    shutil.rmtree(_gec, ignore_errors=True)

# ═══════════ 5) J/L CUT ve DUCKING (TS mantigi) ═══════════
blok("J/L cut ve ducking")
kontrol("J-cut sesi GERIYE kaydiriyor", "bas - Math.round(jSn * fps)" in SES_TS)
kontrol("L-cut uzunlugu UZATIYOR",
        "Math.round((jSn + lSn) * fps)" in SES_TS)
kontrol("J/L varsayilani 0.4 sn (olculen aralik)",
        "sayi(sh.j_cut_sn, 0.4)" in SES_TS and "sayi(sh.l_cut_sn, 0.4)" in SES_TS)
kontrol("sahne sesi kendi Sequence'inde (mutlak konum)",
        "<Sequence" in SES_TS and "from={baslangic}" in SES_TS)
kontrol("baslangic negatife DUSMUYOR", "Math.max(0, bas -" in SES_TS)
kontrol("ducking fonksiyonu var", "export const duckCarpani" in SES_TS)
kontrol("ambans ducking uygular",
        "duckCarpani(f, fps, etkinAraliklar, ambansDip)" in SES_TS)
kontrol("muzik ducking uygular",
        "duckCarpani(f, fps, etkinAraliklar, muzikDip)" in SES_TS)
kontrol("sahne sesine duck UYGULANMAZ (anlatim)",
        "volume={sayi(sh.ses_seviye, 1)}" in SES_TS)
kontrol("ducking rampasi var (ani dusus tik sesi yapar)",
        "gecisSn" in SES_TS and "DUCK.gecisSn" in SES_TS)
kontrol("muzik dibi ambanstan DAHA DERIN",
        "ambans: 0.35" in SES_TS and "muzik: 0.2" in SES_TS)
kontrol("anlatim araligi yoksa sahne seslerine dusulur",
        "sahneAraliklari(sahneler, kareler, fps)" in SES_TS)
kontrol("hic ses yoksa bilesen null doner", "return null;" in SES_TS)

# ═══════════ 6) KONU ve GORSEL KAPILARI ═══════════
blok("konu kapisi (Faz B alaka) ve gorsel kapi")


class _A:
    def __init__(self, baslik="", aciklama="", sorgu=""):
        self.baslik = baslik
        self.aciklama = aciklama
        self.konum = ""
        self.tarih = ""
        self.sorgu = sorgu
        self.saglayici = "wikimedia"
        self.baslik_ = baslik


kontrol("kendi sorgumuz KANIT sayilmaz (aday.sorgu havuzda yok)",
        "aday.sorgu" not in re.sub(r"#.*", "", open(
            os.path.join(KOK, "medya", "siralama.py"),
            encoding="utf-8").read().split("def semantik_puan")[1]
            .split("def amac_puan")[0]),
        "sorgu havuzda kalirsa her aday kendisiyle eslesir")
_ok, _s1 = siralama.alaka_kapisi(_A("MAJESTIC 12 Files", "ufo documents"), {},
                                 "Apollo 11 flight plan document page")
kontrol("ilgisiz arsiv ogesi reddedilir (MAJESTIC 12)", not _ok, _s1)
_ok2, _s2 = siralama.alaka_kapisi(
    _A("AS09-25-3683 - Apollo 9 - Apollo 9 Mission image", ""), {},
    "Apollo 11 lunar module")
kontrol("yanlis gorev reddedilir (Apollo 9 vs 11)", not _ok2, _s2)
_ok3, _s3 = siralama.alaka_kapisi(
    _A("AS11-40-5875 - Apollo 11 - Apollo 11 Mission image", ""), {},
    "Apollo 11 lunar module")
kontrol("dogru gorev KABUL edilir", _ok3, _s3)
_ok4, _s4 = siralama.alaka_kapisi(_A("Nothing at all", ""), {}, "1911 census")
kontrol("kelime siniri: '11' -> '1911' icinde eslesmez", not _ok4, _s4)

# Pilot betiginin video-seviyesi kapisi
sys.path.insert(0, os.path.join(KOK, "testler"))
import importlib.util  # noqa: E402
_sp = importlib.util.spec_from_file_location(
    "fe_medya", os.path.join(KOK, "testler", "faz_e_medya.py"))
_fe = importlib.util.module_from_spec(_sp)
sys.modules["fe_medya"] = _fe
_sp.loader.exec_module(_fe)
for baslik, beklenen, not_ in [
        ("Apollo, Armstrong County, Pennsylvania", False, "kasaba adi"),
        ("Gateway and Orion in lunar orbit (3).jpg", False, "Artemis donemi"),
        ("Lunar eclipse close-up - India.jpg", False, "ay tutulmasi"),
        ("S45-38-009 - STS-045 - STS-45 crew portrait", False, "uzay mekigi"),
        ("AS11-40-5875 - Apollo 11 - Apollo 11 Mission image", True, "dogru"),
        ("View of footpad of Apollo 11 Lunar Module", True, "dogru")]:
    ok, seb = _fe.konu_kapisi(_A(baslik, ""))
    kontrol(f"konu kapisi [{not_}]: {baslik[:34]}", ok == beklenen, seb[:70])

# ═══════════ 7) PILOT SABITLERI ═══════════
blok("pilot sabitleri ve durustluk isaretleri")
_pilot = open(os.path.join(KOK, "testler", "faz_e_pilot.py"),
              encoding="utf-8").read()
kontrol("hedef LUFS -14", "HEDEF_LUFS = -14.0" in _pilot)
kontrol("hedef TP -1 dBTP", "HEDEF_TP = -1.0" in _pilot)
kontrol("iki gecisli loudnorm (measured_* verilir)",
        "measured_I=" in _pilot and "measured_TP=" in _pilot)
kontrol("8 sn tavani korunuyor", "ZORUNLU_TAVAN_SN = 8.0" in _pilot)
kontrol("yapay ses ACIKCA isaretleniyor", '"yapay_ses": True' in _pilot)
kontrol("gorsel detay kapisi var", "DETAY_TABANI" in _pilot
        and "DETAY_IYI" in _pilot)
kontrol("kendi grafigi ACIKCA etiketlenir",
        "BEDOSAHO GRAFIGI · ARSIV GORUNTUSU DEGIL" in _pilot)
kontrol("her segment bir fact_id'ye bagli",
        _pilot.count('("f0') >= 10, "10 segment bekleniyor")
kontrol("dogrulanmamis iddia anlatima GIREMEZ",
        "DOGRULANMAMIS iddia anlatimda" in _pilot)
kontrol("ayni varlik tekrar kullanilmaz notu ve mantigi",
        "AYNI VARLIK TEKRAR KULLANILMAZ" in _pilot)

# Gercek pilot kosusu varsa raporu da dogrula
_rapor_yolu = os.path.join(os.path.dirname(KOK), "cikti", "faz_e",
                           "pilot_rapor.json")
if os.path.exists(_rapor_yolu):
    blok("gercek pilot kosusu raporu")
    R = json.load(open(_rapor_yolu, encoding="utf-8"))
    kontrol("rapor anlatimi YAPAY olarak isaretliyor",
            R["anlatim"]["yapay"] is True)
    kontrol("ses akisi gercekten uretilmis", R["ses_akisi"] >= 1,
            str(R["ses_akisi"]))
    kontrol("sure 45-60 sn", 45.0 <= R["sure_sn"] <= 60.0, str(R["sure_sn"]))
    kontrol("siyah kare yok", not R["qa"]["siyah"])
    kontrol("uzun donma yok", not R["qa"]["donma"])
    kontrol("bilinmeyen spec yok", R["spec_sayimi"]["bilinmeyen"] == 0)
    kontrol("kullanilan benzersiz varlik >= 8",
            R["medya"]["kullanilan_benzersiz"] >= 8)
    kontrol("arsiv hakimiyeti DURUSTCE raporlanmis",
            R["medya"]["tek_arsiv_payi"] >= 0.99
            and any("ARSIV HAKIMIYETI" in b.get("sebep", "")
                    for b in R["medya"]["kapsam_bosluklari"]),
            "tek arsiv payi 1.0 ise bosluk beyan edilmeli")
    kontrol("saglayici cesitliligi eksigi beyan edilmis",
            any("SAGLAYICI CESITLILIGI" in b.get("sebep", "")
                for b in R["medya"]["kapsam_bosluklari"]))
    kontrol("LUFS hedefte (±1)",
            abs(float(R["post_master"]["son"]["input_i"]) + 14.0) <= 1.0,
            R["post_master"]["son"]["input_i"])
    kontrol("TP tavanin altinda",
            float(R["post_master"]["son"]["input_tp"]) <= -1.0 + 0.05,
            R["post_master"]["son"]["input_tp"])
    kontrol("gorsel zayif kareler RAPORLANMIS (gizlenmemis)",
            "gorsel_zayif" in R["medya"])
else:
    print("  --   pilot kosusu yok; rapor testleri ATLANDI (durustce belirtiliyor)")



# ═══════════ 8) INDIRME KAPILARI — REGRESYON FIXTURE'LARI ═══════════
# ⚠ KULLANICI KALITE UYARISI (11 Agu): `guvenlik.icerik_kapisi()` (kabul, sebep)
# TUPLE dondurur, exception ATMAZ. Donus degeri yok sayilirsa (False, sebep)
# gelse bile dosya yazilir. Ayrica boyut tavani `Content-Length`e guveniyordu ve
# icerik hic DECODE EDILMIYORDU — `.jpg` uzantili HTML hata sayfasi medya diye
# gecebiliyordu. Asagidaki fixture'lar bu uc acigin KAPALI oldugunu kanitliyor.
blok("indirme kapilari: bayt tavani + gercek decode")

from medya import indirme  # noqa: E402

# Gercek, kucuk ama GECERLI bir JPEG uret (ffmpeg ile) — sahte fixture degil
_gd = tempfile.mkdtemp(prefix="fe_ind_")
try:
    import subprocess as _sp
    _gercek_jpg = os.path.join(_gd, "gercek.jpg")
    # ⚠ Duz renkli 640x480 JPEG yalnizca 2022 bayt cikiyor ve 8000 baytlik
    # asgari sinirin ALTINDA kaliyor — fixture gercekci degildi. Gurultulu
    # goruntu hem gercekci boyut veriyor hem de kirpma testini anlamli kiliyor
    # (duz renkte 1/3'e kirpilan dosya bile decode edilebiliyordu).
    # noise filtresi GIRDI ister; color kaynagi uzerine uygulaniyor
    _sp.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
             "color=c=gray:s=640x480:d=1,noise=alls=95:allf=t+u",
             "-frames:v", "1", "-q:v", "2", _gercek_jpg],
            check=True, timeout=120)
    _gercek_bayt = open(_gercek_jpg, "rb").read()

    class _Yanit:
        """requests.Response taklidi — akisli indirme yolunu tam kullanir."""

        def __init__(self, icerik: bytes, ct="image/jpeg", kod=200,
                     content_length="auto", basliklar=None):
            self._icerik = icerik
            self.status_code = kod
            self.headers = dict(basliklar or {})
            if ct:
                self.headers["Content-Type"] = ct
            if content_length == "auto":
                self.headers["Content-Length"] = str(len(icerik))
            elif content_length is not None:
                self.headers["Content-Length"] = str(content_length)
            self.kapatildi = False

        @property
        def content(self):
            return self._icerik

        def iter_content(self, chunk_size=65536):
            for i in range(0, len(self._icerik), chunk_size):
                yield self._icerik[i:i + chunk_size]

        def close(self):
            self.kapatildi = True

    def _istekci(yanit):
        def fn(yontem, url, **kw):
            return yanit
        return fn

    def _indir(yanit, ad, **kw):
        hedef = os.path.join(_gd, ad)
        r = indirme.guvenli_indir("https://ornek.test/a.jpg", hedef,
                                  istek=_istekci(yanit), coz=lambda h: ["93.184.216.34"],
                                  **kw)
        return r, hedef

    # ── (a) GECERLI gorsel gecer ──
    _r, _h = _indir(_Yanit(_gercek_bayt), "ok.jpg")
    kontrol("gecerli JPEG kabul edilir", _r["ok"], _r["sebep"])
    kontrol("gecerli JPEG diske yazilir", os.path.exists(_h))
    kontrol("olculen olcu raporlanir",
            _r["bilgi"].get("genislik") == 640 and _r["bilgi"].get("yukseklik") == 480,
            json.dumps(_r["bilgi"]))
    kontrol("sihirli tur tespit edildi", _r["bilgi"].get("sihirli_tur") == "jpeg",
            str(_r["bilgi"].get("sihirli_tur")))

    # ── (b) icerik_kapisi TUPLE sonucu YOK SAYILMAZ ──
    _r, _h = _indir(_Yanit(_gercek_bayt, ct="text/html"), "html_ct.jpg")
    kontrol("izinsiz Content-Type REDDEDILIR", not _r["ok"], _r["sebep"])
    kontrol("red edilen icerik DISKE YAZILMAZ", not os.path.exists(_h))
    kontrol("red sebebi icerik kapisini gosteriyor",
            "icerik kapisi" in _r["sebep"], _r["sebep"])
    kontrol("icerik_kapisi gercekten tuple donduruyor (exception degil)",
            isinstance(guvenlik_icerik_kapisi_sonucu := __import__(
                "medya.guvenlik", fromlist=["guvenlik"]).icerik_kapisi(
                    "text/html", 100, "image"), tuple)
            and guvenlik_icerik_kapisi_sonucu[0] is False,
            str(guvenlik_icerik_kapisi_sonucu))

    # ── (c) .jpg uzantili HTML hata sayfasi ──
    _html = (b"<!DOCTYPE html>\n<html><head><title>404</title></head>"
             b"<body>Not Found</body></html>" + b" " * 9000)
    _r, _h = _indir(_Yanit(_html, ct="image/jpeg"), "sahte.jpg")
    kontrol("HTML icerik gorsel diye GECMEZ", not _r["ok"], _r["sebep"])
    kontrol("HTML reddi diske yazmaz", not os.path.exists(_h))

    # ── (d) uzantisi sahte / taninmayan ikili ──
    _r, _h = _indir(_Yanit(b"\x00\x01\x02\x03" * 3000, ct="image/jpeg"),
                    "sahte2.jpg")
    kontrol("sihirli bayt taninmayan icerik REDDEDILIR", not _r["ok"], _r["sebep"])
    kontrol("taninmayan ikili diske yazmaz", not os.path.exists(_h))

    # ── (e) BOZUK/yarim JPEG: decode patlar ──
    _bozuk = _gercek_bayt[:len(_gercek_bayt) // 2]
    if len(_bozuk) < 8100:
        _bozuk = _bozuk + b"\x00" * (8100 - len(_bozuk))
    _r, _h = _indir(_Yanit(_bozuk, ct="image/jpeg"), "bozuk.jpg")
    kontrol("yarim/bozuk JPEG REDDEDILIR (bitis imzasi/decode)", not _r["ok"],
            _r["sebep"])
    kontrol("kirpilmis dosya reddi bitis imzasini gosteriyor",
            "bitis imzasi" in _r["sebep"] or "decode" in _r["sebep"],
            _r["sebep"])
    kontrol("bozuk dosya diske yazmaz", not os.path.exists(_h))

    # ── (f) BAYT TAVANI: Content-Length YALAN soyluyor ──
    _buyuk = _gercek_bayt + b"\x00" * 400_000
    _r, _h = _indir(_Yanit(_buyuk, ct="image/jpeg", content_length="1234"),
                    "yalan.jpg", maks_bayt=120_000)
    kontrol("Content-Length YALAN olsa da akis tavani calisir", not _r["ok"],
            _r["sebep"])
    kontrol("tavan reddi 'bayt tavani' diyor", "bayt tavani" in _r["sebep"],
            _r["sebep"])
    kontrol("tavani asan indirme diske yazmaz", not os.path.exists(_h))
    kontrol("okunan bayt tavanin hemen ustunde kesildi",
            120_000 < _r["okunan_bayt"] <= 120_000 + 65536,
            f"okunan={_r['okunan_bayt']}")

    # ── (g) Content-Length HIC YOK: tavan yine uygulanir ──
    _r, _h = _indir(_Yanit(_buyuk, ct="image/jpeg", content_length=None),
                    "clyok.jpg", maks_bayt=120_000)
    kontrol("Content-Length yoksa da tavan uygulanir", not _r["ok"], _r["sebep"])
    kontrol("Content-Length yok + tavan asildi -> diske yazmaz",
            not os.path.exists(_h))

    # ── (h) cok kucuk dosya ──
    _r, _h = _indir(_Yanit(_gercek_bayt[:200], ct="image/jpeg"), "mini.jpg")
    kontrol("cok kucuk dosya REDDEDILIR", not _r["ok"], _r["sebep"])

    # ── (i) HTTP hata kodu ──
    _r, _h = _indir(_Yanit(b"", ct="image/jpeg", kod=404), "yok404.jpg")
    kontrol("HTTP 404 reddedilir", not _r["ok"] and "404" in _r["sebep"],
            _r["sebep"])
    _r, _h = _indir(_Yanit(b"", ct="image/jpeg", kod=429,
                           basliklar={"Retry-After": "7"}), "hiz429.jpg")
    kontrol("429 Retry-After basligi tasiniyor", _r.get("retry_after") == "7",
            str(_r.get("retry_after")))

    # ── (j) gecici dosya SIZDIRMIYOR ──
    _kalan = [x for x in os.listdir(_gd) if x.startswith(".indir_")]
    kontrol("basarisiz indirmeler gecici dosya BIRAKMIYOR", not _kalan,
            str(_kalan))

    # ── (k) dosya_dogrula dogrudan ──
    ok, sebep, bilgi = indirme.dosya_dogrula(_gercek_jpg, beklenen="image")
    kontrol("dosya_dogrula gercek gorseli kabul eder", ok, sebep)
    kontrol("bitis imzasi dogrulandi", "bitis imzasi tam" in str(bilgi.get("bitis")),
            str(bilgi.get("bitis")))
    _htmly = os.path.join(_gd, "s.html")
    open(_htmly, "wb").write(_html)
    ok2, sebep2, _ = indirme.dosya_dogrula(_htmly, beklenen="image")
    kontrol("dosya_dogrula HTML'i reddeder", not ok2, sebep2)

    # ── (l) ses dogrulamasi (ffprobe yolu) ──
    _wav = os.path.join(_gd, "t.wav")
    _sp.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
             "anoisesrc=d=1:a=0.1", "-ar", "48000", _wav], check=True, timeout=120)
    ok3, sebep3, _ = indirme.dosya_dogrula(_wav, beklenen="audio",
                                           en_az_bayt=1000)
    kontrol("ses dosyasi ffprobe ile dogrulanir", ok3, sebep3)
    ok4, sebep4, _ = indirme.dosya_dogrula(_wav, beklenen="image",
                                           en_az_bayt=1000)
    kontrol("ses dosyasi GORSEL olarak kabul edilmez", not ok4, sebep4)
finally:
    import shutil as _sh2
    _sh2.rmtree(_gd, ignore_errors=True)

# ═══════════ 9) SAGLAYICI vs ARSIV CESITLILIGI AYRI ═══════════
blok("saglayici ve ARSIV cesitliligi ayri kapilar")
_fem = open(os.path.join(KOK, "testler", "faz_e_medya.py"), encoding="utf-8").read()
for k in ("SAGLAYICI cesitliligi>=3", "SAGLAYICI tek pay<=40%",
          "ARSIV cesitliligi>=2", "ARSIV tek pay<=40%",
          "guvenli_decode=hepsi"):
    kontrol(f"kapi ayri tanimli: {k}", k in _fem)
kontrol("arsiv kimligi NASA katalog numarasini taniyor",
        "as\\d{2}-\\d{2}" in _fem or "as\\d{2}-" in _fem,
        "AS11-43-6352 gibi numaralar nasa arsivi sayilmali")
kontrol("indirme reddi raporlaniyor", '"indirme_reddi"' in _fem)

print(f"\n{'=' * 60}")
print(f"GECEN: {gecen}   BASARISIZ: {len(basarisiz)}")
for b in basarisiz:
    print(f"  XX {b}")
sys.exit(1 if basarisiz else 0)
