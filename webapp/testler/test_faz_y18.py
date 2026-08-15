#!/usr/bin/env python3
"""FAZ Y-18 — BOLUM MINI-YAYI VE GUCLU KAPANIS OLCULUYOR.

⚠ OLCULEN KUSUR (`Y18-YAY-PROMPT-SEZGISI`) — ajan bulgusu, kodda
dogrulandi: "her bolum hook -> baglam -> kanit/karsitlik -> sonuc" kurali
sistemde YALNIZCA bir LLM PROMPT CUMLESI olarak vardi
(`pipeline.bolum_kural`); donen JSON uzerinde HICBIR dogrulama yoktu.
Kod tarafinda `Bolum` diye bir varlik, kimlik ya da uyelik iliskisi
olmadigi icin kural DOGRULANAMIYORDU — dogrulanamayan kural, kural degil
TEMENNIDIR.

⚠ IKINCI KUSUR (`Y18-ISLEV-TAUTOLOJI`): `editor/beat.islev_belirle`
ilk cumleye KOSULSUZ "hook", son cumleye KOSULSUZ "sonuc" etiketi
veriyordu (`indeks == 0` / `indeks >= toplam - 1`). Bu yuzden `HOOK-YOK`
ve kapanis kapilari YAPISAL OLARAK ateslenemiyordu: olcum sifir bilgi
tasiyordu. Ustelik desenler SALT INGILIZCEYDI, hat ise Turkce anlatim
uretiyor — `karsitlik` rolu Turkce iste HIC olusmuyordu.

⚠ UCUNCU KUSUR (`Y18-KAPANIS-OLCULMUYOR`): kapanis gucu hicbir yerde
olculmuyordu; `qa_son` yalnizca SESSIZ KUYRUK saniyesini (`POST-OLU-FINAL`)
olcuyor, kapanisin anlatisal gucunu DEGIL.

── SOZLESME ──
  · Olcum YAPILANDIRILMIS alanlardan yapilir: `chapter_id`, `beat_role`,
    `primary_fact_id`. ⚠ Serbest metin sezgisi ya da prompt varligi KABUL
    DEGILDIR.
  · Her chapter DORT rolu de DOGRU SIRADA tasir:
        hook -> baglam -> (kanit | karsitlik) -> sonuc
  · `kanit`/`karsitlik` rolu KABUL EDILMIS FactPacket allowlist'inden bir
    `primary_fact_id` tasimak ZORUNDA.
  · `sonuc` rolu YENI fact UYDURAMAZ: tasidigi fact o chapter'da zaten
    kullanilmis olmali.
  · Kapanis: SON chapter'da `sonuc` + `closing` beat; olculen kapanis
    gucu >= 0.60.
  · Render kapsami: render edilen her sahne bir beat'e karsilik gelmeli.
  · Eksik / sira bozuk / rol tekrari / zayif kapanis -> STABIL KOD + tek
    DETERMINISTIK yeniden plan denemesi, sonra FAIL.

Kosum: .venv-test/bin/python3 webapp/testler/test_faz_y18.py
"""
from __future__ import annotations

import os
import sys

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


ay = None
try:
    import anlati_yay as ay
    kontrol("modul yuklendi: webapp/anlati_yay.py", True)
except Exception as e:
    kontrol("modul yuklendi: webapp/anlati_yay.py", False,
            f"{type(e).__name__}: {e}")

if ay is None:
    print(f"\n{'=' * 62}\nGECEN: {gecen}   BASARISIZ: {len(basarisiz)}")
    for b in basarisiz:
        print(f"  XX {b}")
    sys.exit(1)

import kabul_105 as KB  # noqa: E402

F1, F2, F3 = "f0123456789abcde1", "f0123456789abcde2", "f0123456789abcde3"
IZIN = {F1, F2, F3}


def beat(cid, rol, fid="", sn=0.0, metin=""):
    return {"chapter_id": cid, "beat_role": rol, "primary_fact_id": fid,
            "bas_sn": sn, "sure_sn": 3.0, "metin": metin}


def _tam_plan():
    """Iki chapter + kapanis: sozlesmeye TAM uyan plan."""
    return [
        beat("c1", "hook", "", 0.0, "Tokyo'da kac kisi yalniz oluyor"),
        beat("c1", "baglam", "", 3.0, "Sehir hizla yaslaniyor"),
        beat("c1", "kanit", F1, 6.0, "Polis 76,941 vaka kaydetti"),
        beat("c1", "sonuc", F1, 9.0, "Sayi bir esigi asti"),
        beat("c2", "hook", "", 12.0, "Peki neden kimse fark etmiyor"),
        beat("c2", "baglam", "", 15.0, "Komsuluk baglari zayifladi"),
        beat("c2", "karsitlik", F2, 18.0, "Oysa resmi kayitlar tersini soyluyor"),
        beat("c2", "sonuc", F2, 21.0, "Boylece tablo degisiyor"),
        beat("c2", "closing", F2, 24.0, "Tokyo'da yalniz olenlerin sayisi"),
    ]


blok("Y-18/1 — SOZLESME VE KARAR KODLARI")

_AYK = open(os.path.join(KOK, "anlati_yay.py"), encoding="utf-8").read()
for kod in ("Y18-YAY-PROMPT-SEZGISI", "Y18-ISLEV-TAUTOLOJI",
            "Y18-KAPANIS-OLCULMUYOR"):
    kontrol(f"karar kodu belgelendi: {kod}", kod in _AYK)
for ad in ("YAY_SIRASI", "ROLLER", "KAPANIS_ASGARI", "yay_olcumu",
           "yeniden_planla", "kapanis_gucu", "KODLAR"):
    kontrol(f"disa acilan ad: {ad}", hasattr(ay, ad), "tanimli degil")
kontrol("yay 4 halkali", len(ay.YAY_SIRASI) == 4, f"{ay.YAY_SIRASI}")
kontrol("kapanis esigi kabul kriteriyle AYNI",
        ay.KAPANIS_ASGARI == KB.KAPANIS_ASGARI,
        f"{ay.KAPANIS_ASGARI} != {KB.KAPANIS_ASGARI}")


blok("Y-18/2 — TAM PLAN GECER (yanlis-negatif yok)")

_t = ay.yay_olcumu(_tam_plan(), allowlist=IZIN, render_sahne=9)
kontrol("olculdu=True", _t.get("olculdu") is True, f"{_t}")
kontrol("eksik halka yok", _t.get("eksik_halka") == [], f"{_t}")
kontrol("bolum sayisi 2", _t.get("bolum") == 2, f"{_t}")
kontrol("kapanis skoru esigin ustunde",
        (_t.get("kapanis_skoru") or 0) >= ay.KAPANIS_ASGARI, f"{_t}")
kontrol("kod bos", not _t.get("kod"), f"kod={_t.get('kod')!r}")
kontrol("kabul kriteri PASS",
        KB._k_bolum_yay({"anlati": _t})[0] is True, f"{_t}")


blok("Y-18/3 — EKSIK HALKA")

_eksik = [b for b in _tam_plan() if not (b["chapter_id"] == "c1"
                                         and b["beat_role"] == "baglam")]
_r = ay.yay_olcumu(_eksik, allowlist=IZIN, render_sahne=8)
kontrol("eksik halka yakalanir",
        any("baglam" in str(x) for x in (_r.get("eksik_halka") or [])),
        f"{_r.get('eksik_halka')}")
kontrol("stabil kod ANLATI-YAY-EKSIK-HALKA",
        _r.get("kod") == ay.KOD_EKSIK_HALKA, f"kod={_r.get('kod')!r}")
kontrol("kabul kriteri FAIL", KB._k_bolum_yay({"anlati": _r})[0] is False)


blok("Y-18/4 — SIRA BOZUK + TEK DETERMINISTIK YENIDEN PLAN")

_bozuk = _tam_plan()
_bozuk[1], _bozuk[2] = _bozuk[2], _bozuk[1]      # baglam <-> kanit
_rb = ay.yay_olcumu(_bozuk, allowlist=IZIN, render_sahne=9)
kontrol("sira bozuklugu yakalanir", _rb.get("kod") == ay.KOD_SIRA_BOZUK,
        f"kod={_rb.get('kod')!r}")
kontrol("sira bozuk bolum adlandirilir",
        "c1" in str(_rb.get("sira_bozuk") or []), f"{_rb}")

_onarilan = ay.yeniden_planla(_bozuk)
kontrol("yeniden plan DETERMINISTIK (iki kosum ayni)",
        ay.yeniden_planla(_bozuk) == _onarilan, "rastgelelik var")
_ro = ay.yay_olcumu(_onarilan, allowlist=IZIN, render_sahne=9)
kontrol("yeniden plandan SONRA yay TAM", _ro.get("kod") == "", f"{_ro}")
kontrol("yeniden plan beat SAYISINI degistirmez",
        len(_onarilan) == len(_bozuk), f"{len(_onarilan)} != {len(_bozuk)}")

# ⚠ Eksik halka YENIDEN PLANLA ile ONARILAMAZ (uydurma yok).
_re2 = ay.yay_olcumu(ay.yeniden_planla(_eksik), allowlist=IZIN,
                     render_sahne=8)
kontrol("eksik halka yeniden planla ile UYDURULMAZ",
        _re2.get("kod") == ay.KOD_EKSIK_HALKA, f"{_re2}")


blok("Y-18/5 — ROL TEKRARI")

_tekrar = _tam_plan()
_tekrar.insert(3, beat("c1", "kanit", F3, 8.0, "Ikinci kanit"))
_rt = ay.yay_olcumu(_tekrar, allowlist=IZIN, render_sahne=10)
kontrol("ayni chapter'da hook/sonuc tekrari YASAK",
        ay.yay_olcumu(
            _tam_plan() + [beat("c2", "sonuc", F2, 27.0)],
            allowlist=IZIN, render_sahne=10).get("kod") == ay.KOD_ROL_TEKRAR,
        "tekrar eden zorunlu rol gecti")
kontrol("kanit/karsitlik BIRDEN FAZLA olabilir (kanit yigmak serbest)",
        _rt.get("kod") == "", f"{_rt}")


blok("Y-18/6 — KANIT ROLU KABUL EDILMIS FACT'E BAGLI")

_factsiz = _tam_plan()
for b in _factsiz:
    if b["beat_role"] == "kanit":
        b["primary_fact_id"] = ""
_rf = ay.yay_olcumu(_factsiz, allowlist=IZIN, render_sahne=9)
kontrol("fact'siz kanit yakalanir", _rf.get("kod") == ay.KOD_KANIT_FACT_YOK,
        f"kod={_rf.get('kod')!r}")

_disi = _tam_plan()
for b in _disi:
    if b["beat_role"] == "kanit":
        b["primary_fact_id"] = "f9999999999999999"     # allowlist DISI
_rd = ay.yay_olcumu(_disi, allowlist=IZIN, render_sahne=9)
kontrol("allowlist disi fact yakalanir",
        _rd.get("kod") == ay.KOD_KANIT_FACT_YOK, f"{_rd}")
kontrol("allowlist verilmezse OLCULMEZ (uydurma yok)",
        ay.yay_olcumu(_tam_plan(), render_sahne=9).get("kod")
        == ay.KOD_OLCULMEDI,
        "allowlist'siz olcum kabul uretiyor")


blok("Y-18/7 — SONUC YENI FACT UYDURAMAZ")

_yeni = _tam_plan()
for b in _yeni:
    if b["chapter_id"] == "c1" and b["beat_role"] == "sonuc":
        b["primary_fact_id"] = F3          # c1'de hic kullanilmadi
_ry = ay.yay_olcumu(_yeni, allowlist=IZIN, render_sahne=9)
kontrol("sonucta yeni fact yakalanir", _ry.get("kod") == ay.KOD_SONUC_YENI_FACT,
        f"kod={_ry.get('kod')!r}")
kontrol("sonuc fact'siz olabilir",
        (lambda p: ay.yay_olcumu(p, allowlist=IZIN, render_sahne=9).get("kod")
         == "")([{**b, "primary_fact_id": ""}
                 if b["beat_role"] == "sonuc" else b for b in _tam_plan()]))


blok("Y-18/8 — KAPANIS: SON BOLUMDE sonuc + closing")

_kapanissiz = [b for b in _tam_plan() if b["beat_role"] != "closing"]
_rk = ay.yay_olcumu(_kapanissiz, allowlist=IZIN, render_sahne=8)
kontrol("closing yoksa yakalanir", _rk.get("kod") == ay.KOD_KAPANIS_ZAYIF,
        f"kod={_rk.get('kod')!r}")
kontrol("closing yoksa skor 0", _rk.get("kapanis_skoru") == 0.0, f"{_rk}")

# ⚠ Kapanis gucu OLCULUR: hook geri cagirimi + cozum + yeni fact yok.
_guclu = ay.kapanis_gucu(_tam_plan())
kontrol("guclu kapanis >= esik", _guclu >= ay.KAPANIS_ASGARI, f"{_guclu}")

_zayif_plan = _tam_plan()
_zayif_plan[-1]["metin"] = "Bir sonraki videoda gorusmek uzere"   # geri cagirim yok
_zayif_plan[-1]["primary_fact_id"] = F3                            # YENI fact
_zayif = ay.kapanis_gucu(_zayif_plan)
kontrol("zayif kapanis < esik", _zayif < ay.KAPANIS_ASGARI, f"{_zayif}")
kontrol("zayif kapanis stabil kodla FAIL",
        ay.yay_olcumu(_zayif_plan, allowlist=IZIN,
                      render_sahne=9).get("kod") in
        (ay.KOD_KAPANIS_ZAYIF, ay.KOD_SONUC_YENI_FACT), "hukum yok")
kontrol("kapanis gucu DETERMINISTIK",
        ay.kapanis_gucu(_tam_plan()) == _guclu, "rastgelelik var")


blok("Y-18/9 — RENDER KAPSAMI (timeline ile ortusme)")

_rr = ay.yay_olcumu(_tam_plan(), allowlist=IZIN, render_sahne=14)
kontrol("render sahnesi beat'ten FAZLAYSA yakalanir",
        _rr.get("kod") == ay.KOD_RENDER_KAPSAMI, f"{_rr}")
kontrol("render kapsami raporlanir",
        _rr.get("render_kapsam") is not None, f"{_rr}")
kontrol("render sahnesi verilmezse OLCULMEZ",
        ay.yay_olcumu(_tam_plan(), allowlist=IZIN).get("kod")
        == ay.KOD_OLCULMEDI, "kapsamsiz olcum kabul uretiyor")


blok("Y-18/10 — BOS / BOZUK GIRDI FAIL-CLOSED")

for ad, girdi in (("bos liste", []), ("None", None), ("metin", "x")):
    _rz = ay.yay_olcumu(girdi, allowlist=IZIN, render_sahne=0)
    kontrol(f"{ad} -> olculdu=False", _rz.get("olculdu") is False, f"{_rz}")
    kontrol(f"{ad} -> kapanis skoru SAYI olarak sunulmaz",
            _rz.get("kapanis_skoru") is None, f"{_rz}")

kontrol("yapilandirilmamis beat (rol yok) OLCULMEZ",
        ay.yay_olcumu([{"metin": "serbest metin"}], allowlist=IZIN,
                      render_sahne=1).get("kod") == ay.KOD_OLCULMEDI,
        "serbest metinden rol SEZILIYOR")


blok("Y-18/11 — KABUL KRITERI GERCEK OLCUMU OKUR")

kontrol("olculmemis -> FAIL",
        KB._k_bolum_yay({"anlati": {"olculdu": False}})[0] is False)
kontrol("eksik halka -> FAIL",
        KB._k_bolum_yay({"anlati": {
            "olculdu": True, "bolum": 2, "eksik_halka": ["c1:baglam"],
            "kapanis_skoru": 0.9}})[0] is False)
kontrol("zayif kapanis -> FAIL",
        KB._k_bolum_yay({"anlati": {
            "olculdu": True, "bolum": 2, "eksik_halka": [],
            "kapanis_skoru": 0.2}})[0] is False)
kontrol("kabul kriteri kod tasiyan olcumu REDDEDER",
        KB._k_bolum_yay({"anlati": {
            "olculdu": True, "bolum": 2, "eksik_halka": [],
            "kapanis_skoru": 0.9, "kod": ay.KOD_SIRA_BOZUK}})[0] is False,
        "stabil kod varken kabul uretiliyor")


blok("Y-18b — DENETIM KARSI ORNEKLERI")

# (1) ⚠ Y18B-KAPANIS-IMALATI: `sonuc` son beat olsa bile AYRI bir
# `closing` yoksa kapanis YOKTUR; kapi bunu IMAL ETMEZ.
_sonuc_son = [b for b in _tam_plan() if b["beat_role"] != "closing"]
_rs = ay.yay_olcumu(_sonuc_son, allowlist=IZIN, render_sahne=8)
kontrol("sonuc son ama AYRI closing yok -> FAIL",
        _rs.get("kod") == ay.KOD_KAPANIS_ZAYIF, f"{_rs}")
_PLK0 = open(os.path.join(KOK, "pipeline.py"), encoding="utf-8").read()
kontrol("karar kodu belgelendi: Y18B-KAPANIS-IMALATI",
        "Y18B-KAPANIS-IMALATI" in _PLK0)
kontrol("hat closing beat'i IMAL ETMIYOR",
        'beat_role"] = "closing"' not in _PLK0,
        "kapi kendi kapanisini uretiyor (totoloji)")

# (2) ⚠ Y18B-KAPSAM-TOTOLOJI: olcum kendi listesini kapsam sanamaz.
_9props = [f"s{i:03d}" for i in range(1, 10)]
_10beat = _tam_plan() + [beat("c2", "kanit", F3, 27.0)]
for i, b in enumerate(_10beat):
    b["scene_id"] = f"s{i + 1:03d}"
_rc = ay.yay_olcumu(_10beat, allowlist=IZIN, render_sahne=9,
                    render_scene_idler=_9props)
kontrol("9 props + 10 beat -> RENDER KAPSAMI FAIL",
        _rc.get("kod") == ay.KOD_RENDER_KAPSAMI, f"{_rc}")
kontrol("fazla beat kimlikle adlandirilir",
        any("s010" in str(x) for x in (_rc.get("kapsam_eksik") or [])),
        f"{_rc.get('kapsam_eksik')}")
_tam_id = _tam_plan()
for i, b in enumerate(_tam_id):
    b["scene_id"] = f"s{i + 1:03d}"
kontrol("birebir eslesen kimlikler GECER",
        ay.yay_olcumu(_tam_id, allowlist=IZIN, render_sahne=9,
                      render_scene_idler=_9props).get("kod") == "",
        f"{ay.yay_olcumu(_tam_id, allowlist=IZIN, render_sahne=9, render_scene_idler=_9props)}")
kontrol("scene_id tasimayan beat kapsam DOGRULATAMAZ",
        ay.yay_olcumu(_tam_plan(), allowlist=IZIN, render_sahne=9,
                      render_scene_idler=_9props).get("kod")
        == ay.KOD_RENDER_KAPSAMI)
kontrol("karar kodu belgelendi: Y18B-KAPSAM-TOTOLOJI",
        "Y18B-KAPSAM-TOTOLOJI" in open(
            os.path.join(KOK, "anlati_yay.py"), encoding="utf-8").read())

# (3) ⚠ Y18B-POST-HOC-SIRALAMA: render SONRASI siralama PASS uretemez.
kontrol("karar kodu belgelendi: Y18B-POST-HOC-SIRALAMA",
        "Y18B-POST-HOC-SIRALAMA" in _PLK0)
_i_render = _PLK0.find("hizli_render.ffmpeg_render(")
_i_onarim = _PLK0.find("yeniden_planla(")
kontrol("deterministik onarim RENDER'DAN ONCE",
        0 < _i_onarim < _i_render, f"onarim@{_i_onarim} render@{_i_render}")
kontrol("render SONRASI yeniden_planla CAGRISI YOK",
        _PLK0.count("yeniden_planla(") == 1
        and _PLK0.rfind("yeniden_planla(") < _i_render,
        "olcum post-hoc siralanip makyajlaniyor")
kontrol("on-onarim props_sahneler'i GERCEKTEN yeniden siralar",
        "props_sahneler.sort(" in _PLK0,
        "onarim timeline'i degistirmiyor")


blok("Y-18c — CANLI HAT: KAPANIS GERCEKTEN URETILEBILIR")

# ⚠ OLCULEN KUSUR (`Y18C-KAPANIS-URETILEMEZ`, denetim): otomatik imalat
# kaldirilinca `closing` rolunu URETEBILECEK hicbir yol kalmamisti —
# `props_sahneler` `beat_role`/`kapanis` alanini HIC yazmiyor ve
# `ISLEV_TIPLERI` yalnizca `sonuc` iceriyordu. Tum isler duserdi.
import shutil as _sh18   # noqa: E402
import tempfile as _tf18  # noqa: E402

_k18 = _tf18.mkdtemp(prefix="y18_kok_")
_u18 = os.path.join(KOK, "..", "app", "uret.py")
if os.path.exists(_u18):
    _sh18.copy(_u18, os.path.join(_k18, "uret.py"))
sys.path.insert(0, _k18)
os.environ["VIDRUSH_KOK"] = os.path.abspath(_k18)
os.environ.setdefault("CIKTI_DIR", os.path.join(_k18, "ciktilar"))
import pipeline as PL18  # noqa: E402

kontrol("ISLEV_TIPLERI `kapanis` iceriyor",
        "kapanis" in PL18.ISLEV_TIPLERI, f"{sorted(PL18.ISLEV_TIPLERI)}")
kontrol("rol eslemesi kapanis -> closing",
        PL18.ISLEV_YAY_ROLU.get("kapanis") == "closing",
        f"{PL18.ISLEV_YAY_ROLU}")
kontrol("senaryo promptu AYRI kapanis zorluyor",
        "CLOSING RULE" in _PLK0 and 'islev=\\"kapanis\\"' in _PLK0
        or "CLOSING RULE" in _PLK0,
        "prompt kapanisi ayri satir olarak zorlamiyor")

# ── CANLI props -> beat plani: islev=kapanis GERCEK closing uretir ──
_props_ok = [
    {"scene_id": "s001", "bolum": "BOLUM 1", "islev": "acilis", "sure": 3.0,
     "anlatim": "Tokyo'da kac kisi yalniz oluyor", "fact_id": ""},
    {"scene_id": "s002", "islev": "aciklama", "sure": 3.0,
     "anlatim": "Sehir hizla yaslaniyor", "fact_id": ""},
    {"scene_id": "s003", "islev": "vurgu", "sure": 3.0,
     "anlatim": "Polis 76,941 vaka kaydetti", "fact_id": F1},
    {"scene_id": "s004", "islev": "sonuc", "sure": 3.0,
     "anlatim": "Sayi bir esigi asti", "fact_id": F1},
    {"scene_id": "s005", "islev": "kapanis", "sure": 3.0,
     "anlatim": "Tokyo'da yalniz olenlerin sayisi bir esik", "fact_id": F1},
]
_b18 = PL18.yay_plani_kur(_props_ok)
kontrol("canli props'ta islev=kapanis -> closing rolu",
        _b18[-1]["beat_role"] == "closing", f"{[b['beat_role'] for b in _b18]}")
kontrol("closing GERCEK scene_id tasir",
        _b18[-1]["scene_id"] == "s005", f"{_b18[-1]}")
kontrol("closing GERCEK sure tasir (0 sn sahte beat yok)",
        float(_b18[-1].get("sure_sn") or 0) > 0, f"{_b18[-1]}")
kontrol("beat sayisi props sayisina ESIT (imalat yok)",
        len(_b18) == len(_props_ok), f"{len(_b18)} != {len(_props_ok)}")
_o18 = ay.yay_olcumu(_b18, allowlist=IZIN, render_sahne=len(_props_ok),
                     render_scene_idler=[p["scene_id"] for p in _props_ok])
kontrol("canli plan yay olcumunden GECER", _o18.get("kod") == "", f"{_o18}")

# ── YALNIZ sonuc ile biten plan FAIL ──
_props_sonuc = [dict(x) for x in _props_ok[:-1]]
_b18b = PL18.yay_plani_kur(_props_sonuc)
kontrol("yalniz sonuc final -> closing URETILMEZ",
        all(b["beat_role"] != "closing" for b in _b18b),
        f"{[b['beat_role'] for b in _b18b]}")
kontrol("yalniz sonuc final -> KAPANIS ZAYIF FAIL",
        ay.yay_olcumu(_b18b, allowlist=IZIN, render_sahne=len(_props_sonuc),
                      render_scene_idler=[p["scene_id"]
                                          for p in _props_sonuc])
        .get("kod") == ay.KOD_KAPANIS_ZAYIF, "kapanissiz plan geciyor")

# ── Hicbir uretim alani yazmiyorsa STATIK test KIRMIZI olmali ──
kontrol("uretimde closing uretebilecek EN AZ BIR yol var",
        ("kapanis" in PL18.ISLEV_TIPLERI
         and PL18.ISLEV_YAY_ROLU.get("kapanis") == "closing"),
        "closing uretilemez — tum isler duser")
kontrol("karar kodu belgelendi: Y18C-KAPANIS-URETILEMEZ",
        "Y18C-KAPANIS-URETILEMEZ" in _PLK0)


blok("Y-18/12 — HAT BAGLANTISI")

_PLK = open(os.path.join(KOK, "pipeline.py"), encoding="utf-8").read()
kontrol("pipeline yapilandirilmis alanlari URETIYOR",
        "chapter_id" in _PLK and "beat_role" in _PLK
        and "primary_fact_id" in _PLK,
        "plan sozlesmesi hatta yok")
kontrol("pipeline yay olcumunu kosuyor", "yay_olcumu(" in _PLK,
        "olcum hatta bagli degil")
kontrol("pipeline tek yeniden plan denemesi yapiyor",
        "yeniden_planla(" in _PLK, "deterministik onarim denemesi yok")
kontrol("pipeline GERCEK render sahne kimliklerini gecirir",
        "render_scene_idler=" in _PLK, "kapsam kimlikle dogrulanmiyor")


print(f"\n{'=' * 62}\nGECEN: {gecen}   BASARISIZ: {len(basarisiz)}")
for b in basarisiz:
    print(f"  XX {b}")
sys.exit(1 if basarisiz else 0)
