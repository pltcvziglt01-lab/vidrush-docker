#!/usr/bin/env python3
"""FAZ D testleri — AGSIZ, Remotion/npm GEREKTIRMEZ.

Iki tarafi karsilastirir:
  Python  : webapp/editor/motion.py (spec ureticileri) + adapter
  TypeScript: app/render-studio/src/editorv2/sozlesme.ts (DESTEK_MATRISI)

Amac: "beyan var ama render yok" durumunun tekrar etmemesi. Faz C'de adapter
premium yolu eziyordu; burada TS matrisi ile Python spec kumesi arasindaki
her sapma FAIL uretir.

Kosum:  python3 webapp/testler/test_faz_d.py
"""
from __future__ import annotations

import json
import os
import re
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)

from editor import adapter, motion, plan, profil, remotion_v2  # noqa: E402

STUDIO = remotion_v2.STUDIO
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


P = profil.profil("premium-modern")

# ═══════════ 1) DOSYA VARLIGI ve OPT-IN GUVENCESI ═══════════
blok("opt-in: mevcut kompozisyon korunuyor mu")
for yol in ("src/editorv2/sozlesme.ts", "src/editorv2/temel.ts",
            "src/editorv2/Kamera.tsx", "src/editorv2/Katmanlar.tsx",
            "src/editorv2/Grafikler.tsx", "src/editorv2/EditorV2.tsx"):
    kontrol(f"dosya var: {yol}", os.path.exists(os.path.join(STUDIO, yol)))

_root = open(os.path.join(STUDIO, "src", "Root.tsx"), encoding="utf-8").read()
kontrol("Root.tsx'te VidrushVideo HALA kayitli", 'id="VidrushVideo"' in _root)
kontrol("Root.tsx'te VidrushEditorV2 kayitli", 'id="VidrushEditorV2"' in _root)
kontrol("VidrushVideo bileseni degismedi (ayni import)",
        "import {VidrushVideo, varsayilanProps, VideoProps, normMotion, hesaplaKareler}"
        in _root)
_video = open(os.path.join(STUDIO, "src", "Video.tsx"), encoding="utf-8").read()
kontrol("Video.tsx editorv2'yi IMPORT ETMIYOR (bagimsizlik)",
        "editorv2" not in _video)
_pkg = json.load(open(os.path.join(STUDIO, "package.json"), encoding="utf-8"))
kontrol("package.json render scripti hala VidrushVideo",
        "VidrushVideo" in _pkg["scripts"]["render"],
        _pkg["scripts"]["render"])

# ═══════════ 2) DESTEK MATRISI = TEK DOGRULUK KAYNAGI ═══════════
blok("destek matrisi: TS <-> Python sapmasi")
matris = remotion_v2.destek_matrisi_oku()
kontrol("TS destek matrisi okunabildi", len(matris) >= 25, f"{len(matris)} kayit")
kontrol("durum degerleri gecerli",
        set(matris.values()) <= {"gercek", "pseudo", "ffmpeg-yolu", "desteklenmiyor"},
        str(sorted(set(matris.values()))))

# Python'un urettigi TUM spec adlari matriste olmali
_uretilen = set()
for fn, arg in (
        (lambda: motion.kamera_spec("push-in", 3.0, "tam", p=P), None),
        (lambda: motion.kamera_spec("pull-out", 3.0, "tam", p=P), None),
        (lambda: motion.kamera_spec("pan-right", 3.0, "tam", p=P), None),
        (lambda: motion.kamera_spec("pan-left", 3.0, "tam", p=P), None),
        (lambda: motion.kamera_spec("slow-drift", 3.0, "tam", p=P), None),
        (lambda: motion.kamera_spec("static", 3.0, "tam", p=P), None),
        (lambda: motion.kamera_spec("handheld", 3.0, "tam", p=P), None),
        (lambda: motion.kamera_spec("document-scan", 3.0, "tam", p=P), None),
        (lambda: motion.kamera_spec("map-route", 3.0, "tam", p=P), None),
        (lambda: motion.kamera_spec("data-reveal", 3.0, "tam", p=P), None),
        (lambda: motion.parallax_spec(3, 3.0, p=P), None),
        (lambda: motion.masked_reveal_spec(), None),
        (lambda: motion.track_matte_wipe_spec(), None),
        (lambda: motion.light_sweep_spec(), None),
        (lambda: motion.film_burn_spec(), None),
        (lambda: motion.bolum_basligi_spec("X", 3.0, p=P), None),
        (lambda: motion.alt_band_spec("A", "B", 3.0, p=P), None),
        (lambda: motion.kaynak_etiketi_spec("K", "f1", 3.0, p=P), None),
        (lambda: motion.callout_spec("C", 0.5, 0.5, 1.8, p=P), None),
        (lambda: motion.alinti_karti_spec("A", "K", 4.0), None),
        (lambda: motion.belge_vurgusu_spec((0.3, 0.3, 0.3, 0.2), 4.0), None),
        (lambda: motion.harita_spec("Tokyo", None, 4.0), None),
        (lambda: motion.veri_grafigi_spec("B", [1], 4.0), None)):
    _uretilen.add(fn().ad)
for t in motion.taban_katmanlar(3.0, p=P):
    _uretilen.add(t.ad)
for g in motion.GECIS_GEREKCESI:
    _uretilen.add(motion.gecis_spec(g).ad)
    _uretilen.add(g)

_eksik = sorted(x for x in _uretilen if x not in matris)
kontrol("Python'un urettigi HER spec TS matrisinde var", not _eksik,
        f"matriste YOK: {_eksik}")

# Matriste olup Python'un hic uretmedigi spec -> olu kayit uyarisi
# Kanonik kume = motion.py'nin kendi beyani. Testin elle liste tutmasi,
# Faz C'de yakalanan "iki yerde iki dogruluk" hatasinin aynisi olurdu.
KANONIK = set(motion.FFMPEG_DESTEKLI) | set(motion.REMOTION_ZORUNLU)
kontrol("elle uretilen specler kanonik kumenin altkumesi",
        _uretilen <= KANONIK | {"match-cut", "whip", "zoom-through", "glitch"},
        f"kanonikte yok: {sorted(_uretilen - KANONIK)}")
_eksik2 = sorted(x for x in KANONIK if x not in matris)
kontrol("motion.py'nin BEYAN ETTIGI her spec TS matrisinde var", not _eksik2,
        f"matriste YOK: {_eksik2}")
_olu = sorted(x for x in matris if x not in KANONIK and x not in _uretilen)
kontrol("matriste olu kayit yok (ne kanonik ne uretilen)", not _olu,
        f"olu: {_olu}")

# ffmpeg-yolu olarak isaretlenenler gercekten ses/hizli yolun isi mi
kontrol("j-cut ve l-cut ffmpeg-yolu olarak isaretli",
        matris.get("j-cut") == "ffmpeg-yolu" and matris.get("l-cut") == "ffmpeg-yolu",
        f"j={matris.get('j-cut')} l={matris.get('l-cut')}")
kontrol("parallax ve map-route PSEUDO olarak beyan edilmis",
        matris.get("parallax-2.5d") == "pseudo"
        and matris.get("map-route") == "pseudo",
        f"parallax={matris.get('parallax-2.5d')} map={matris.get('map-route')}")

_ts = open(remotion_v2.SOZLESME_TS, encoding="utf-8").read()
for ad in ("parallax-2.5d", "track-matte-wipe", "map-route"):
    i = _ts.find(f"'{ad}'")
    blok_ts = _ts[i:i + 500] if i > 0 else ""
    kontrol(f"pseudo '{ad}' KAYIP alanini beyan ediyor", "kayip:" in blok_ts,
            blok_ts[:80])

# ═══════════ 3) PROP SOZLESMESI: Python -> TS alan uyumu ═══════════
blok("prop sozlesmesi: adapter cikisi TS arayuzunu karsiliyor")
_specler = [
    motion.kamera_spec("push-in", 4.0, "tam", p=P).sozluk(),
    motion.parallax_spec(3, 4.0, p=P).sozluk(),
    motion.light_sweep_spec(0.8).sozluk(),
    motion.belge_vurgusu_spec((0.3, 0.3, 0.4, 0.2), 4.0).sozluk(),
    motion.harita_spec("Tokyo", None, 4.0).sozluk(),
    motion.veri_grafigi_spec("Vakalar", [76941], 4.0).sozluk(),
    motion.bolum_basligi_spec("BASLIK", 4.0, p=P).sozluk(),
    motion.alt_band_spec("TOKYO", "JAPAN", 4.0, p=P).sozluk(),
    motion.kaynak_etiketi_spec("NPA", "f001", 3.0, p=P).sozluk(),
    motion.gecis_spec("karartma").sozluk(),
] + [t.sozluk() for t in motion.taban_katmanlar(4.0, p=P)]
for sp in _specler:
    sp["beat_id"] = "bD1"
_rp = {"fps": 30, "genislik": 1920, "yukseklik": 1080, "gecis_modu": "sinematik",
       "altyazi_stili": "yok",
       "sahneler": [{"beat_id": "bD1", "scene_id": "sD", "fact_id": "fD",
                     "asset_id": "aD", "saglayici": "wikimedia", "lisans": "cc0",
                     "medya_turu": "image", "medya_yolu": "/tmp/x.jpg",
                     "sure_sn": 4.0, "bas_sn": 0.0, "islev": "kanit",
                     "perde": "gelisme", "cekim_turu": "archive",
                     "hareket": "push-in", "kadraj": "tam",
                     "kaynak_aralik": [0, 4], "j_cut": False, "l_cut": False,
                     "altyazi": [], "motion": _specler, "gerekce": "test"}]}
_don = adapter.donustur(_rp)
_rsahne = _don.remotion_props["sahneler"][0]

# TS EditorSahne arayuzunun ZORUNLU alanlari
TS_SAHNE_ALANLARI = ["beat_id", "scene_id", "fact_id", "asset_id", "saglayici",
                     "lisans", "tur", "medya", "ses", "sure", "bas_sn", "islev",
                     "perde", "cekim_turu", "hareket", "kadraj",
                     "kaynak_aralik", "j_cut", "l_cut", "altyazi", "motion",
                     "gerekce"]
_eksik_alan = [a for a in TS_SAHNE_ALANLARI if a not in _rsahne]
kontrol("remotion sahnesi TS EditorSahne alanlarinin TAMAMINI tasiyor",
        not _eksik_alan, f"eksik: {_eksik_alan}")

# TS MotionSpec zorunlu alanlari
TS_SPEC_ALANLARI = ["ad", "renderer", "parametre", "easing", "easing_bezier",
                    "bas_sn", "sure_sn", "katman", "fallback",
                    "remotion_zorunlu", "gerekce"]
_spec_eksik = set()
for sp in _rsahne["motion"]:
    for a in TS_SPEC_ALANLARI:
        if a not in sp:
            _spec_eksik.add(a)
kontrol("her motion spec TS MotionSpec alanlarini tasiyor", not _spec_eksik,
        f"eksik: {sorted(_spec_eksik)}")
kontrol("easing_bezier 4 elemanli",
        all(len(sp["easing_bezier"]) == 4 for sp in _rsahne["motion"]),
        str([len(sp["easing_bezier"]) for sp in _rsahne["motion"]]))
kontrol("renderer degerleri gecerli",
        all(sp["renderer"] in ("ffmpeg", "remotion") for sp in _rsahne["motion"]))

# TS arayuzunde tanimli alan adlari Python cikisiyla ORTUSUYOR mu
# ⚠ IKI HATA DUZELTILDI (Faz E'de yakalandi):
# 1) Blok sonu "export interface EditorV2Props" ile bulunuyordu. Faz E arada
#    `SesAyari` arayuzunu ekleyince onun alanlari da EditorSahne sayildi.
#    Artik blok KENDI kapanis suslu parantezinde bitiyor.
# 2) Opsiyonel alanlar elle listeleniyordu (premium_gerekce, parallax_...).
#    Yeni opsiyonel alan eklenince test kiriliyordu. Artik `alan?:` yazimi
#    OPSIYONEL olarak taniniyor — asil kural bu.
_i = _ts.find("export interface EditorSahne")
_ts_sahne_blok = _ts[_i:_ts.find("\n}", _i)]
_ts_zorunlu = set(re.findall(r"^\s{2}(\w+):", _ts_sahne_blok, re.M))
_ts_opsiyonel = set(re.findall(r"^\s{2}(\w+)\?:", _ts_sahne_blok, re.M))
kontrol("EditorSahne blogu dogru ayrildi (SesAyari sizmadi)",
        "anlatim" not in _ts_zorunlu | _ts_opsiyonel,
        f"zorunlu={sorted(_ts_zorunlu)[:6]}")
_ts_fazla = sorted(_ts_zorunlu - set(_rsahne.keys()))
kontrol("TS'de Python'un uretmedigi ZORUNLU alan yok", not _ts_fazla,
        f"TS'de var Python'da yok: {_ts_fazla}")
kontrol("ses alanlari OPSIYONEL olarak tanimli",
        {"ses_bas_sn", "ses_seviye", "j_cut_sn", "l_cut_sn"} <= _ts_opsiyonel,
        f"opsiyonel={sorted(_ts_opsiyonel)}")

# ═══════════ 4) UYGULANAN / ATLANAN SAYIMI ═══════════
blok("uygulanan/atlanan spec sayimi")
_say = remotion_v2.uygulanan_atlanan(_don.remotion_props, matris)
kontrol("sayim uretildi", _say["sayim"]["toplam"] == len(_specler),
        f"{_say['sayim']['toplam']} vs {len(_specler)}")
kontrol("bilinmeyen spec YOK", _say["sayim"]["bilinmeyen"] == 0,
        json.dumps(_say["detay"].get("bilinmeyen", {})))
kontrol("gercek uygulanan >= 8", _say["sayim"]["gercek"] >= 8,
        json.dumps(_say["sayim"]))
kontrol("pseudo sayisi raporlaniyor", _say["sayim"]["pseudo"] >= 1,
        json.dumps(_say["sayim"]))

# Bilinmeyen spec eklenince sayim onu YAKALAR
_bozuk = json.loads(json.dumps(_don.remotion_props))
_bozuk["sahneler"][0]["motion"].append(
    {"ad": "hic-yok-boyle", "renderer": "remotion", "parametre": {},
     "easing": "lineer", "easing_bezier": [0, 0, 1, 1], "bas_sn": 0,
     "sure_sn": 1, "katman": 0, "fallback": None, "remotion_zorunlu": True,
     "gerekce": ""})
_say2 = remotion_v2.uygulanan_atlanan(_bozuk, matris)
kontrol("bilinmeyen spec sayimda YAKALANIR",
        _say2["sayim"]["bilinmeyen"] == 1,
        json.dumps(_say2["sayim"]))

# ═══════════ 5) TS VALIDATOR MANTIGI (Python aynasi) ═══════════
blok("validator: bilinmeyen spec FAIL")
# TS validator'i node ile kosmak icin kucuk bir kontrol: dogrula() FAIL
# uretmeli. node yoksa test atlanir ama ATLANDIGI YAZILIR.
_node_var = os.system("node -v >/dev/null 2>&1") == 0
if _node_var:
    import subprocess
    _betik = os.path.join(STUDIO, "src", "editorv2", "_test_validator.mjs")
    with open(_betik, "w", encoding="utf-8") as f:
        f.write("""
// Gecici test betigi (test sonunda silinir). TS'i tsc ile derlemek yerine
// DESTEK_MATRISI'ni regex ile okuyup ayni mantigi dogruluyoruz.
import {readFileSync} from 'fs';
const ts = readFileSync(new URL('./sozlesme.ts', import.meta.url), 'utf8');
const i = ts.indexOf('DESTEK_MATRISI');
const j = ts.indexOf('export const DESTEKLENEN_SPECLER');
const blok = ts.slice(i, j);
const adlar = [...blok.matchAll(/(?:'([a-z0-9.\\-]+)'|^\\s{2}([a-zA-Z][a-zA-Z0-9]*)):\\s*\\{/gm)]
  .map((m) => m[1] || m[2]);
const failVar = ts.includes("kod: 'V2-BILINMEYEN-SPEC'") && ts.includes("seviye: 'fail'");
console.log(JSON.stringify({adet: adlar.length, failVar}));
""")
    try:
        r = subprocess.run(["node", _betik], capture_output=True, text=True,
                           timeout=60)
        d = json.loads((r.stdout or "{}").strip().splitlines()[-1])
        kontrol("node ile TS matrisi okunabiliyor", d.get("adet", 0) >= 25,
                str(d))
        kontrol("validator BILINMEYEN-SPEC icin FAIL tanimliyor",
                bool(d.get("failVar")), str(d))
    except Exception as e:
        kontrol("node ile TS dogrulamasi", False, str(e)[:120])
    finally:
        try:
            os.remove(_betik)
        except Exception:
            pass
else:
    print("  --   node yok, TS validator testi ATLANDI (durustce belirtiliyor)")

kontrol("TS validator bilinmeyen spec icin FAIL kodu iceriyor",
        "V2-BILINMEYEN-SPEC" in _ts and "seviye: 'fail'" in _ts)
kontrol("TS validator izlenebilirlik (beat/scene) zorunlu tutuyor",
        "V2-IZLENEBILIRLIK" in _ts)
kontrol("TS validator sure>0 kontrolu yapiyor", "V2-SURE" in _ts)
kontrol("TS validator pseudo icin BILGI notu uretiyor", "V2-PSEUDO" in _ts)

# ═══════════ 6) FALLBACK DAVRANISI ═══════════
blok("fallback: premium ezilmiyor, hizli yol fallback uyguluyor")
kontrol("remotion sahnesinde parallax OZGUN duruyor",
        any(x["ad"] == "parallax-2.5d" for x in _rsahne["motion"]))
kontrol("hizli sahnede parallax YOK (fallback uygulandi)",
        not any(e.get("ad") == "parallax-2.5d"
                for e in _don.hizli_sahneler[0]["efektler"]))
kontrol("fallback kaybi raporlandi",
        any(k["spec"] == "parallax-2.5d" for k in _don.kayip_efektler),
        str([k["spec"] for k in _don.kayip_efektler]))
kontrol("iki cikti nesne paylasmiyor",
        _don.remotion_props["sahneler"] is not _don.hizli_sahneler)
kontrol("premium gerekce sahnede", bool(_rsahne.get("premium_gerekce")))

# ═══════════ 7) SURE / FPS / GUVENLI ALAN ═══════════
blok("sure, fps ve guvenli alan sabitleri")
_temel = open(os.path.join(STUDIO, "src", "editorv2", "temel.ts"),
              encoding="utf-8").read()
kontrol("guvenli kenar 64px (yayin standardi)", "GUVENLI_KENAR = 64" in _temel)
kontrol("izgara x=100 (Faz C ile ayni)", "IZGARA_X = 100" in _temel)
kontrol("olculen kamera easing TS'te ayni",
        "[0.42, 0.32, 0.58, 0.68]" in _temel,
        "profil.EASING['kamera'] ile ayni olmali")
kontrol("Python kamera easing ile TS AYNI",
        list(profil.EASING["kamera"]) == [0.42, 0.32, 0.58, 0.68])
def _kodu(ad: str) -> str:
    """TS dosyasini YORUMSUZ oku. Yorumda gecen bir ifade kod sayilmamali:
    'Math.random YASAK' yazan yorum, testi yanlis yere dusuruyordu."""
    m = open(os.path.join(STUDIO, "src", "editorv2", ad), encoding="utf-8").read()
    m = re.sub(r"/\*.*?\*/", "", m, flags=re.S)          # blok yorum
    m = re.sub(r"^\s*//.*$", "", m, flags=re.M)            # satir yorumu
    m = re.sub(r"(?<![:'\"])//[^\n'\"`]*$", "", m, flags=re.M)  # satir sonu yorumu
    return m


_kod_temel = _kodu("temel.ts")
_kod_katman = _kodu("Katmanlar.tsx")
kontrol("Math.random KULLANILMIYOR (deterministik render)",
        "Math.random" not in _kod_temel and "Math.random" not in _kod_katman,
        "her kare ayni olmali")
kontrol("tohum() deterministik pseudo-rastgele saglıyor",
        "export const tohum" in _temel)
_ev2 = open(os.path.join(STUDIO, "src", "editorv2", "EditorV2.tsx"),
            encoding="utf-8").read()
kontrol("kareHesapla sure*fps kullaniyor", "sure, 1) * fps" in _ev2
        or "sayi(s.sure, 1) * fps" in _ev2)
kontrol("karartma gecisi SIYAHA INMIYOR (dip)",
        "dip" in _ev2 and "SIYAHA INMEZ" in _ev2)
_grafik = open(os.path.join(STUDIO, "src", "editorv2", "Grafikler.tsx"),
               encoding="utf-8").read()
kontrol("her bilgi yazisi BANT tasiyor (kontrast)",
        "bantStil" in _grafik and _grafik.count("bantStil(") >= 4)
kontrol("kunye bant TASIMIYOR (kontur+golge)",
        "textShadow" in _grafik)
kontrol("grain onceden uretilmis dokuyu kullaniyor (kodda feTurbulence YOK)",
        "staticFile('doku/grain.png')" in _kod_katman
        and "feTurbulence" not in _kod_katman,
        "11 Agu: her karede yeni feTurbulence bir videoyu oldurdu")
kontrol("grain doku dosyasi GERCEKTEN var",
        os.path.exists(os.path.join(STUDIO, "public", "doku", "grain.png")),
        "yoksa grain katmani sessizce bos kalir")

# ═══════════ 8) PROPS HAZIRLAMA ═══════════
blok("props_hazirla: medya yollari")
import tempfile  # noqa: E402
_gec = tempfile.mkdtemp(prefix="fd_")
try:
    _kaynak = os.path.join(_gec, "test.jpg")
    with open(_kaynak, "wb") as f:
        f.write(b"\xff\xd8\xff\xdb" + b"0" * 64)
    _hazir = remotion_v2.props_hazirla(
        _don.remotion_props, calisma_dizin=_gec,
        varlik_haritasi={"aD": _kaynak})
    kontrol("medya yolu public/ altina goreli cevrildi",
            _hazir["sahneler"][0]["medya"].startswith("editorv2/"),
            _hazir["sahneler"][0]["medya"])
    _kopya = os.path.join(STUDIO, "public", _hazir["sahneler"][0]["medya"])
    kontrol("dosya gercekten kopyalandi", os.path.exists(_kopya), _kopya)
    kontrol("props_hazirla girdiyi BOZMUYOR (derin kopya)",
            _don.remotion_props["sahneler"][0]["medya"] == "/tmp/x.jpg",
            _don.remotion_props["sahneler"][0]["medya"])
    _hazir2 = remotion_v2.props_hazirla(_don.remotion_props, calisma_dizin=_gec,
                                        varlik_haritasi={})
    kontrol("varlik yoksa medya bos (sentetik zemin cizilecek)",
            _hazir2["sahneler"][0]["medya"] == "")
finally:
    import shutil as _sh
    _sh.rmtree(_gec, ignore_errors=True)

kontrol("render komutu VidrushEditorV2 cagiriyor",
        remotion_v2.KOMPOZISYON == "VidrushEditorV2")

# ═══════════ 9) PRE-RENDER KAPISI ═══════════
# ⚠ Bu blok, kullanicinin 11 Agu kalite kapisinda isaret ettigi acikligi
# kilitliyor: TS `dogrula()` kompozisyon ICINDE kosuyor ve FAIL'de bile hata
# ekranini render edip rc=0 dondurebiliyor. Yani TS tarafi bir ENGEL DEGIL.
# Gercek engel Python'da: props yazilmadan, npx cagrilmadan durmali.
blok("pre-render kapisi: bilinmeyen spec npx'i HIC cagirmamali")


class _Sayac:
    """Kosucunun cagrilip cagrilmadigini sayar. 'Cagrilmadi' iddiasi
    ancak sayacla kanitlanir; rc'ye bakmak yetmez."""

    def __init__(self):
        self.adet = 0
        self.komutlar = []

    def __call__(self, komut, zaman_asimi):
        self.adet += 1
        self.komutlar.append(komut)
        return {"rc": 0, "stdout": "", "stderr": ""}


def _props(*, bozuk_spec=False, izlenebilirlik_yok=False, sure_sifir=False):
    sp = motion.kamera_spec("push-in", 4.0, "tam", p=P).sozluk()
    sp["beat_id"] = "bG1"
    specler = [sp]
    if bozuk_spec:
        specler.append({"ad": "hic-yok-boyle-bir-spec", "renderer": "remotion",
                        "parametre": {}, "easing": "lineer",
                        "easing_bezier": [0, 0, 1, 1], "bas_sn": 0, "sure_sn": 1,
                        "katman": 0, "fallback": None, "remotion_zorunlu": True,
                        "gerekce": ""})
    return {"fps": 30, "genislik": 1280, "yukseklik": 720, "gecis": "sinematik",
            "altyaziStil": "yok",
            "sahneler": [{
                "beat_id": "" if izlenebilirlik_yok else "bG1",
                "scene_id": "" if izlenebilirlik_yok else "sG1",
                "fact_id": "fG1", "asset_id": "aG1", "saglayici": "wikimedia",
                "lisans": "cc0", "tur": "image", "medya": "editorv2/x.jpg",
                "ses": "", "sure": 0 if sure_sifir else 4.0, "bas_sn": 0.0,
                "islev": "kanit", "perde": "gelisme", "cekim_turu": "archive",
                "hareket": "push-in", "kadraj": "tam", "kaynak_aralik": [0, 4],
                "j_cut": False, "l_cut": False, "altyazi": [],
                "motion": specler, "gerekce": "kapi testi"}]}


# ── NEGATIF: bilinmeyen spec ──
_props_yolu = os.path.join(STUDIO, "public", "editorv2", "props.json")
_onceki = os.path.getmtime(_props_yolu) if os.path.exists(_props_yolu) else None
_s = _Sayac()
_r = remotion_v2.render(_props(bozuk_spec=True), "/tmp/kapi_negatif.mp4",
                        kosucu=_s)
kontrol("bilinmeyen spec -> rc != 0", _r["rc"] != 0, f"rc={_r['rc']}")
kontrol("bilinmeyen spec -> durum FAIL", _r["durum"] == "FAIL", _r["durum"])
kontrol("bilinmeyen spec -> KOSUCU HIC CAGRILMADI (sayac 0)", _s.adet == 0,
        f"kosucu {_s.adet} kez cagrildi")
kontrol("bilinmeyen spec -> komut uretilmedi", _r["komut"] is None,
        str(_r["komut"]))
kontrol("bilinmeyen spec -> kod V2-BILINMEYEN-SPEC",
        any(x["kod"] == "V2-BILINMEYEN-SPEC" and x["seviye"] == "fail"
            for x in _r["sorunlar"]),
        str([x["kod"] for x in _r["sorunlar"]]))
kontrol("bilinmeyen spec -> sorun listesi spec adini veriyor",
        any(x["spec"] == "hic-yok-boyle-bir-spec" for x in _r["sorunlar"]))
kontrol("bilinmeyen spec -> izlenebilirlik (scene/beat) raporlaniyor",
        any(x["scene_id"] == "sG1" and x["beat_id"] == "bG1"
            for x in _r["sorunlar"] if x["kod"] == "V2-BILINMEYEN-SPEC"))
_simdi = os.path.getmtime(_props_yolu) if os.path.exists(_props_yolu) else None
kontrol("bilinmeyen spec -> props.json YAZILMADI", _simdi == _onceki,
        "kapi props dosyasina bile dokunmamali")
kontrol("bilinmeyen spec -> cikti dosyasi yok", not _r["var_mi"])

# ── NEGATIF: izlenebilirlik eksik ──
_s2 = _Sayac()
_r2 = remotion_v2.render(_props(izlenebilirlik_yok=True), "/tmp/kapi_iz.mp4",
                         kosucu=_s2)
kontrol("beat/scene yok -> rc != 0 ve kosucu cagrilmadi",
        _r2["rc"] != 0 and _s2.adet == 0, f"rc={_r2['rc']} sayac={_s2.adet}")
kontrol("beat/scene yok -> kod V2-IZLENEBILIRLIK",
        any(x["kod"] == "V2-IZLENEBILIRLIK" for x in _r2["sorunlar"]))

# ── NEGATIF: sure 0 ──
_s3 = _Sayac()
_r3 = remotion_v2.render(_props(sure_sifir=True), "/tmp/kapi_sure.mp4",
                         kosucu=_s3)
kontrol("sure=0 -> rc != 0 ve kosucu cagrilmadi",
        _r3["rc"] != 0 and _s3.adet == 0, f"rc={_r3['rc']} sayac={_s3.adet}")
kontrol("sure=0 -> kod V2-SURE",
        any(x["kod"] == "V2-SURE" for x in _r3["sorunlar"]))

# ── NEGATIF: bos sahne listesi ──
_s4 = _Sayac()
_r4 = remotion_v2.render({"sahneler": []}, "/tmp/kapi_bos.mp4", kosucu=_s4)
kontrol("bos sahne listesi -> rc != 0 ve kosucu cagrilmadi",
        _r4["rc"] != 0 and _s4.adet == 0, f"rc={_r4['rc']} sayac={_s4.adet}")
kontrol("bos sahne -> kod V2-SAHNE-YOK",
        any(x["kod"] == "V2-SAHNE-YOK" for x in _r4["sorunlar"]))

# ── POZITIF: bilinen fixture render'i CAGIRIR ──
blok("pre-render kapisi: gecerli fixture npx'i cagirmali")
_s5 = _Sayac()
_r5 = remotion_v2.render(_props(), "/tmp/kapi_pozitif.mp4", kosucu=_s5)
kontrol("gecerli props -> kosucu 1 kez cagrildi", _s5.adet == 1,
        f"sayac={_s5.adet}")
kontrol("gecerli props -> rc == 0", _r5["rc"] == 0, f"rc={_r5['rc']}")
kontrol("gecerli props -> durum FAIL DEGIL", _r5["durum"] != "FAIL",
        _r5["durum"])
kontrol("gecerli props -> komut VidrushEditorV2 iceriyor",
        "VidrushEditorV2" in (_s5.komutlar[0] if _s5.komutlar else []),
        str(_s5.komutlar[:1]))
kontrol("gecerli props -> props.json YAZILDI", os.path.exists(_props_yolu))
kontrol("gecerli props -> ozet spec sayisi dogru",
        _r5["ozet"]["spec"] == 1, json.dumps(_r5["ozet"]))

# ── Faz C'nin GERCEK ciktisi kapiyi gecmeli (yoksa kapi kullanilamaz) ──
_gecer = remotion_v2.dogrula(_don.remotion_props)
kontrol("Faz C adapter ciktisi kapiyi GECIYOR", _gecer["durum"] != "FAIL",
        json.dumps([s["kod"] for s in _gecer["sorunlar"]
                    if s["seviye"] == "fail"]))
kontrol("pseudo spec kapiyi DURDURMUYOR (yalnizca bilgi)",
        _gecer["ozet"]["pseudo"] >= 1
        and all(s["seviye"] != "fail" for s in _gecer["sorunlar"]
                if s["kod"] == "V2-PSEUDO"),
        json.dumps(_gecer["ozet"]))

# ── Kod adlari TS ile AYNI olmali (iki kapi ayni dili konusmali) ──
for kod in ("V2-BILINMEYEN-SPEC", "V2-IZLENEBILIRLIK", "V2-SURE",
            "V2-SAHNE-YOK", "V2-PSEUDO", "V2-DESTEKLENMIYOR", "V2-EASING",
            "V2-MEDYA-YOK"):
    kontrol(f"kod TS ve Python'da ayni: {kod}",
            kod in _ts and kod in open(
                os.path.join(KOK, "editor", "remotion_v2.py"),
                encoding="utf-8").read())

# ── Matris okunamazsa sessizce gecmemeli ──
_s6 = _Sayac()
_r6 = remotion_v2.render(_props(), "/tmp/kapi_matris.mp4", kosucu=_s6)
_bos = remotion_v2.dogrula(_props(), matris={})
kontrol("matris bos -> FAIL (sessiz gecis yok)", _bos["durum"] == "FAIL")
kontrol("matris bos -> kod V2-MATRIS-OKUNAMADI",
        any(x["kod"] == "V2-MATRIS-OKUNAMADI" for x in _bos["sorunlar"]))

print(f"\n{'=' * 58}")
print(f"GECEN: {gecen}   BASARISIZ: {len(basarisiz)}")
for b in basarisiz:
    print(f"  XX {b}")
sys.exit(1 if basarisiz else 0)
