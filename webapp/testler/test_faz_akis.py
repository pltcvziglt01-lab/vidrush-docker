#!/usr/bin/env python3
"""TEK AKIS PIVOTU (20 Agu 2026) — sozlesme testleri.

URUN KARARI (kullanici, 20 Agu): "arac tamamen suna donuyor — gerektiginde
AI gerektiginde stok video; cumle basina 5-7 sn; motion gecisli hazir video;
TUM SISTEM Magnific'ten; arayuz tek akis, eskiler kalkar."

OLCULEN GERCEKLER (bu suite'in dayandigi kanit):
  · nano-banana-pro-flash tek cagrida 2752x1536 NATIVE 16:9 dondurdu
    (canli test, 20 Agu). 1536x1024 uretip kirpma + upscale zinciri
    bu yolda GEREKSIZ.
  · image-to-video uclari (kling/minimax/pixverse/wan/veo) anahtarla ACIK
    (sahte task-id GET -> 404 "Task not found"; yetkisizde 401 gelirdi).
  · Klip PAHALI (~$0.25-0.50/5sn) -> MAG_KLIP_MAKS sert tavani ZORUNLU.

RED-FIRST: bu dosyanin kontrolleri once pivot ONCESI kod uzerinde
dusunuldu — akis profili yokken profil cozumu varsayilana duser, magnific
saglayici dali yoktur, klip tavani yoktur. Hepsi FAIL olurdu.
"""
import os
import re
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)

GECEN = BASARISIZ = 0


def kontrol(ad, kosul, detay=""):
    global GECEN, BASARISIZ
    if kosul:
        GECEN += 1
        print(f"  ok   {ad}")
    else:
        BASARISIZ += 1
        print(f"  XX {ad} — {detay}")


def blok(b):
    print(f"\n── {b} ──")


import shutil                                                 # noqa: E402
import tempfile                                               # noqa: E402

# `pipeline` import'u `app/uret.py`yi bekler (Mac'te /opt yolu yok) —
# p0 suite'inin kurulumuyla ayni: uret.py gecici koke kopyalanir.
_kok2 = tempfile.mkdtemp(prefix="akis_kok_")
_uret_py = os.path.join(KOK, "..", "app", "uret.py")
if os.path.exists(_uret_py):
    shutil.copy(_uret_py, os.path.join(_kok2, "uret.py"))
sys.path.insert(0, _kok2)
os.environ["VIDRUSH_KOK"] = os.path.abspath(_kok2)
os.environ.setdefault("CIKTI_DIR", os.path.join(_kok2, "ciktilar"))

import magnific_motor as MM                                   # noqa: E402
import pipeline as PL                                         # noqa: E402

_PIPE = open(os.path.join(KOK, "pipeline.py"), encoding="utf-8").read()
_WIZ = open(os.path.join(KOK, "static", "js", "wizard.js"),
            encoding="utf-8").read()

# ══════════════════════════════════════════════════════════════════════
blok("AKIS/1 — PROFIL: cumle=sahne 5-7 sn, stok-once + AI-gorsel-acik")

kontrol("'akis' profili EDIT_STILLERI'nde", "akis" in PL.EDIT_STILLERI)
_p = PL.EDIT_STILLERI.get("akis", {})
kontrol("sahne 5-7 sn bandi (sahne_sn=6, maks=7)",
        _p.get("sahne_sn") == 6 and _p.get("maks_sahne_sn") == 7, f"{_p}")
kontrol("AI gorsel yolu ACIK (gorsel_yasak degil)",
        not _p.get("gorsel_yasak"), f"{_p.get('gorsel_yasak')}")
kontrol("stok-once karisim (footage_pct 100 DEGIL, 0 DEGIL)",
        0 < int(_p.get("footage_pct") or 0) < 100, f"{_p.get('footage_pct')}")
kontrol("magnific upscale adimi YOK (nano zaten 2K)", _p.get("mag") is None,
        f"{_p.get('mag')}")
kontrol("profil_coz 'akis'i GERCEKTEN cozer (sessiz varsayilan yok)",
        PL.profil_coz("documentary", "akis").get("ad") == "Akış")
# ⚠ Strict grounded'a SIZMAZ: akis best-effort belgeseldir.
import fact_baglama as FB                                     # noqa: E402
kontrol("akis STRICT grounded DEGIL (P0 karari korunur)",
        not FB.strict_grounded_mi("documentary", "akis"))

# ══════════════════════════════════════════════════════════════════════
blok("AKIS/2 — MAGNIFIC MOTOR: fail-closed sozlesme")

kontrol("anahtar yokken var()=False",
        (lambda: (os.environ.pop("FREEPIK_KEYS", None),
                  os.environ.pop("MAGNIFIC_KEY", None),
                  not MM.var())[-1])())
os.environ["MAGNIFIC_KEY"] = "test-anahtari-000000000000000000"
kontrol("anahtar varken var()=True (kalici kapali degilse)", MM.var())
kontrol("bos prompt gorsel URETMEZ (istek bile atilmaz)",
        MM.gorsel_uret("", "/tmp/yok.png") is False)
kontrol("olmayan gorselden klip URETILMEZ",
        MM.klip_uret("/tmp/boyle-bir-dosya-yok-akis.png", "/tmp/yok.mp4")
        is False)

_b = MM.IsButcesi("test-is")
kontrol("is basina butce: klip tavani MAG_KLIP_MAKS",
        _b.klip_hakki_var() is (MM.KLIP_MAKS > 0))
_b.klip = MM.KLIP_MAKS
kontrol("tavan dolunca klip hakki BITER", not _b.klip_hakki_var())
kontrol("tavan dolunca klip_uret REDDEDER (ikinci kapi)",
        MM.klip_uret(__file__, "/tmp/yok.mp4", butce=_b) is False)
kontrol("durum() anahtar DEGERI sizdirmaz",
        "test-anahtari" not in str(MM.durum()))

# ══════════════════════════════════════════════════════════════════════
blok("AKIS/3 — PIPELINE ENTEGRASYONU (kaynak kodda kilitli)")

kontrol("magnific_motor import edildi", "import magnific_motor" in _PIPE)
kontrol("akis modu tanimi: edit_id=='akis'",
        '_akis_modu = (edit_id == "akis")' in _PIPE)
kontrol("sahne gorseli akis modunda magnific saglayicisina gider",
        re.search(r'saglayici=\("magnific" if _akis_modu', _PIPE))
kontrol("referansli_gorsel'de magnific dali VAR ve dususte OpenAI'ye devam",
        "magnific_motor.gorsel_uret" in _PIPE
        and "OpenAI yoluna devam" in _PIPE)
kontrol("klip uretimi IKI kapili tavanla (_akis_butce.klip_hakki_var)",
        "_akis_butce.klip_hakki_var()" in _PIPE
        and "magnific_motor.klip_uret" in _PIPE)
kontrol("klip dususte gorsel+motion devam (is olmez)",
        'return ("image", f"isler/{is_adi}/sahne_{n}.png")' in _PIPE)

# ══════════════════════════════════════════════════════════════════════
blok("AKIS/4 — UI TEK AKIS (eski wizard kalkti)")

kontrol("wizard tek akis: tur/edit SABIT documentary+akis",
        "tur: 'documentary'" in _WIZ and "edit: 'akis'" in _WIZ)
kontrol("eski 5 adimli wizard KALKTI (adim kartlari yok)",
        "ADIMLAR" not in _WIZ and "adim3Govde" not in _WIZ)
# ⚠ Kelime degil KONTROL aranir: aciklama yorumu "palet/isik kalkti"
# yazabilir; olculen sey eski girdi id'lerinin yoklugudur.
kontrol("stil/palet/isik/karakter kontrolleri KALKTI",
        all(x not in _WIZ for x in ("wzIsik", "wzHex", 'grup="palet"',
                                    "wzKarGirdi", "wzRefGirdi", "wzModel")))
kontrol("uydurma tahmin YOK (uretim sirasinda hesaplanir yazisi)",
        "üretim sırasında hesaplanır" in _WIZ
        or "tahmin gösterilmez" in _WIZ)
kontrol("eski export sozlesmesi korunur (app.js kirilmaz)",
        all(f"export {x}" in _WIZ or f"export function {x}" in _WIZ
            or f"export async function {x}" in _WIZ
            for x in ("wizardCiz", "wizardAdim", "wizardKaynakHatalari"))
        and "generateDegerleri" in _WIZ)

print("\n" + "=" * 62)
print(f"GECEN: {GECEN}   BASARISIZ: {BASARISIZ}")
sys.exit(1 if BASARISIZ else 0)
