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


print(f"\n{'=' * 62}\nGECEN: {gecen}   BASARISIZ: {len(basarisiz)}")
for b in basarisiz:
    print(f"  XX {b}")
sys.exit(1 if basarisiz else 0)
