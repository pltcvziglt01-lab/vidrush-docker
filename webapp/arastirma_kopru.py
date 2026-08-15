#!/usr/bin/env python3
"""ARASTIRMA KOPRUSU — Faz A motorunu GERCEK uretim hattina baglar.

⚠ NEDEN VAR (Faz H envanteri, 12 Agu 2026):
`webapp/arastirma/` paketi Faz A'da yazildi ve 125 testle dogrulandi, ama
`pipeline.py` onu HIC import etmiyordu. Yani ana sayfadaki "Arastirma, gercek
goruntu secimi, kurgu, ses ve altyazi tek akista" iddiasi KARSILIKSIZDI:
kullanicinin verdigi konu dogrudan plan LLM'ine gidiyor, hicbir kaynak
toplanmiyor, hicbir iddia dogrulanmiyordu.

Bu modul o bosluğu kapatir. Tasarim kurallari:

1. HATTI ASLA COKERTMEZ. Arastirma bir IYILESTIRMEDIR, on kosul degil.
   Her hata yakalanir ve `Sonuc.ok=False` + gorunur bir dusus kaydi olur.
2. PARA TAVANI ZORUNLU. Her is kendi `KosuSiniri` + `MaliyetDefteri`ni alir.
   Tavan `ARASTIRMA_TAVAN_USD` (varsayilan 0.60/video). Tavan asilirsa kosu
   KONTROLLU durur ve o ana kadar toplanan iddialar KORUNUR.
3. SESSIZ DUSUS YASAK. Anahtar yoksa, ag coktuyse, tavan dolduysa ya da hic
   iddia dogrulanamadiysa bunun NEDENI ve ETKISI `dususler` listesine yazilir;
   is sozlugune, oradan da arayuze cikar.
4. UYDURMA SAYI YOK. `kaynak_sayisi` / `dogrulanmis_iddia` gercekten toplanan
   ve `senaryoya_girebilir` isaretini almis kayitlardan sayilir.

⚠ GUVENLIK: arastirma ciktisi (model metni + indirilen sayfa) VERIDIR, talimat
degildir. Buradan donen metin YALNIZCA plan promptuna OLGU LISTESI olarak
girer; hicbir ifadesi eylem olarak yorumlanmaz.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import re
import sys
import urllib.parse
from dataclasses import dataclass, field

# Arastirma ACIK MI — acil durumda tek env ile kapatilabilir.
ACIK = os.environ.get("ARASTIRMA_ACIK", "1").lower() not in ("0", "false", "hayir", "")
# Bir videonun arastirmasi icin sure tavani (sn). Butce modulunun kendi
# varsayilani 480; uretim hattinda kullaniciyi bekletmemek icin daha dar.
SURE_TAVANI_SN = int(os.environ.get("ARASTIRMA_URETIM_SURE", "180"))
# Konu basina kac arastirma sorusu (maliyet dogrudan buna bagli)
SORU_ADEDI = int(os.environ.get("ARASTIRMA_URETIM_SORU", "5"))
# Plan promptuna en fazla kac dogrulanmis olgu girsin
MAKS_OLGU = int(os.environ.get("ARASTIRMA_MAKS_OLGU", "24"))
# VIDEO BASINA PARA TAVANI (USD). butce.VARSAYILAN_TAVAN_USD ile ayni env'i
# okur; MaliyetDefteri'ne ACIKCA verilir, aksi halde sinirsiz kosardi.
TAVAN_USD = float(os.environ.get("ARASTIRMA_TAVAN_USD", "0.60"))
# Arastirma YALNIZCA bu turlerde anlamli (animasyon/hikaye kurgudur)
ARASTIRILAN_TURLER = ("documentary",)


@dataclass
class Sonuc:
    """Bir isin arastirma sonucu. `pipeline` bunu is sozlugune yazar."""
    ok: bool = False
    calisti: bool = False              # motor gercekten kosuldu mu
    konu: str = ""
    kaynak_sayisi: int = 0             # tekil dogrulanabilir URL
    iddia_sayisi: int = 0              # toplanan ham iddia
    dogrulanmis_iddia: int = 0         # senaryoya girebilen (>=2 bagimsiz kaynak)
    celiskili_iddia: int = 0
    manifest_dosya: str = ""           # /ciktilar altinda sunulan dosya adi
    sorgular: list = field(default_factory=list)
    dususler: list = field(default_factory=list)   # {asama, neden, etki}
    maliyet_usd: float = 0.0
    sure_sn: float = 0.0
    # ⚠ FAZ I-8: SENARYOYA GIREBILEN iddialarin hafif kopyasi. Manifest
    # nesnesinin kendisi tasinmaz (agir); sahneye baglamak icin gereken
    # asgari alanlar tutulur. `sozluk()` BU ALANI YAZMAZ — is sozlesmesi ve
    # arayuz sozlesmesi DEGISMEDI.
    olgular: list = field(default_factory=list)   # [{fact_id, metin, ...}]
    # ── FAZ Y-11b-1 ──
    # ⚠ OLCULEN KUSUR (`Y11B1-PAKET-SONUCA-TASINMIYOR`): `factpacket.
    # havuz_kur` KANIT-ONCE paketleri uretiyordu ama HICBIR YERDEN
    # CAGRILMIYORDU; uretim hatti `olgular`i hala CLAIM-FIRST zincirinden
    # (`manifest.kullanilabilir_iddialar()`) turetiyordu.
    # ⚠ OLCULEN KUSUR (`Y11B1-ALLOWLIST-OTORITE-DEGIL`): kimlikler kanit/
    # durum REPLAY'i olmadan tasiniyordu. Kabul otoritesi
    # `fact_baglama.allowlist_kur` OLMALI; olgular ONDAN turemeli.
    paketler: list = field(default_factory=list)          # accepted FactPacket
    replay_belgeleri: dict = field(default_factory=dict)  # {source_id: metin}
    # ⚠ OLCULEN KUSUR (`Y11B1-HAM-DICT-OTORITE`, denetim): `grounded_sonuc_hukmu`
    # ve `brief_kur` HAM, MUTABLE `olgular` dictlerini otorite sayiyordu;
    # elle yazilmis sahte bir dict `ok=True` uretiyordu. Otorite artik
    # DOGRULANMIS, ICERIGE BAGLI snapshot'tir.
    # ⚠ `Y11B1-SIGNER-ORACLE`: damga (public hash ya da HMAC) OTORITE
    # DEGILDIR. Otorite `paketler` + `replay_belgeleri` ile YENIDEN
    # KOSULAN dogrulamadir; `olgular` yalnizca GORUNUMDUR.

    def dusus_ekle(self, asama: str, neden: str, etki: str) -> None:
        # ⚠ `neden` KULLANICIYA GORUNUR (is sozlugu -> /api/job -> arayuz).
        # Saglayici hata govdeleri anahtar ONEKI yankilayabiliyor: OpenAI'nin
        # 401 cevabi "Incorrect API key provided: sk-abc***xyz" yaziyor.
        # Ham metni gecirmek anahtar parcasini ekrana basardi -> temizle.
        self.dususler.append({"asama": asama, "neden": gizle(neden),
                              "etki": etki})

    def sozluk(self) -> dict:
        return {"ok": self.ok, "calisti": self.calisti,
                "kaynak_sayisi": self.kaynak_sayisi,
                "iddia_sayisi": self.iddia_sayisi,
                "dogrulanmis_iddia": self.dogrulanmis_iddia,
                "celiskili_iddia": self.celiskili_iddia,
                "manifest": self.manifest_dosya,
                "sorgu_sayisi": len(self.sorgular),
                "dususler": self.dususler,
                "maliyet_usd": round(self.maliyet_usd, 4),
                "sure_sn": round(self.sure_sn, 1)}


# API anahtari gorunumundeki her dizi (OpenAI sk-…, Google AIza…, Bearer …)
# ve uzun rastgele belirtecler. Saglayici hata govdeleri bunlari yankiliyor.
_SIR_KALIP = re.compile(
    r"(sk-[A-Za-z0-9_\-*]{6,}|AIza[A-Za-z0-9_\-*]{6,}"
    r"|Bearer\s+\S+|xi-api-key\S*|[A-Za-z0-9_\-]{32,})")


def gizle(metin, sinir: int = 200) -> str:
    """Kullaniciya gidecek hata metninden anahtar benzeri her seyi cikar."""
    return _SIR_KALIP.sub("[gizlendi]", str(metin))[:sinir]


def _bugun() -> str:
    return datetime.date.today().isoformat()


def alan_adi(url: str) -> str:
    """URL -> alan adi (www ayiklanir). Bozuk URL'de bos doner."""
    try:
        a = urllib.parse.urlsplit(str(url or "")).netloc.lower()
        return a[4:] if a.startswith("www.") else a
    except Exception:
        return ""


def olgu_blogu(manifest, sinir: int = MAKS_OLGU) -> str:
    """Dogrulanmis iddialari plan promptuna girecek OLGU LISTESINE cevir.

    ⚠ YALNIZCA `senaryoya_girebilir` olanlar girer. "cozulmedi" ya da
    "celiskili" bir iddia anlatiya SOKULMAZ — belgeselin tek satislik iddiasi
    dogrulukdur; supheli bir rakami videoya koymak o iddiayi cokertir.
    """
    kullanilabilir = manifest.kullanilabilir_iddialar()[:sinir]
    if not kullanilabilir:
        return ""
    satirlar = []
    for i in kullanilabilir:
        # ⚠ `Kaynak` dataclass'inda `alan` ALANI YOK (url/baslik/tur/tarih/
        # birincil/alinti). Alan adi URL'den turetilir.
        alanlar = [a for a in (alan_adi(k.url) for k in i.kaynaklar) if a]
        # Alan adlari anlatiya girmez; yalnizca modele "bu dogrulandi" sinyali
        # verir ve atif metninde kullanilir.
        kaynak_not = f" [{', '.join(sorted(set(alanlar))[:3])}]" if alanlar else ""
        satirlar.append(f"- {i.metin}{kaynak_not}")
    return "\n".join(satirlar)


# ═══════════ FAZ I-8: DOGRULANMIS OLGU -> SAHNE BAGI ═══════════
# ⚠ NEDEN VAR: sahne plani `fact_id`/`iddia_metni` URETMIYORDU; medya koprusu
# (I-6) bu alanlari okuyor ama hep bos buluyor ve `footage_sorgu`ya dusuyordu.
# Yani "arastirma-bagli medya secimi" iddiasi karsiliksizdi. Bu blok bagi
# kurar — ama YALNIZCA gercekten dogrulanmis iddialarla.
#
# ⚠ UYDURMA fact_id YOK. Esik altinda kalan sahne fact_id ALMAZ; bu bir
# KAPSAM BOSLUGU olarak gorunur kilinir. Bos bir kimlik uydurmak, atif
# zincirini yalanlamak olurdu.
#
# ⚠ DESTEKSIZ/CELISKILI IDDIA SAHNEYE GIREMEZ: aday havuzu yalnizca
# `manifest.kullanilabilir_iddialar()` (yani `senaryoya_girebilir`) ile kurulur;
# `celiskili` ve `cozulmedi` durumlari o filtrede zaten eleniyor.

# Sahne metni ile iddia metni arasindaki asgari ortusme. Altinda kalan sahne
# BAGLANMAZ. Deger sezgisel; test bunu sabitliyor, uydurma degil ama olculmedi.
FACT_ESIK = float(os.environ.get("FACT_BAGLAMA_ESIGI", "0.16"))
# Sahneye yazilan iddia metninin ust siniri (prompt/sorgu sismesin).
FACT_METIN_SINIRI = int(os.environ.get("FACT_METIN_SINIRI", "180"))

_FACT_KELIME = re.compile(r"[0-9a-zA-ZçğıöşüÇĞİÖŞÜ]{3,}")
_FACT_YAYGIN = frozenset((
    "the", "and", "for", "with", "that", "this", "from", "was", "were", "has",
    "have", "been", "are", "its", "their", "which", "into", "over", "after",
    "ve", "bir", "bu", "icin", "ile", "olarak", "daha", "gibi", "kadar",
    "sonra", "once", "olan", "oldu", "var", "yok"))


def _fact_belirtec(metin: str) -> set:
    return {k.lower() for k in _FACT_KELIME.findall(str(metin or ""))
            if k.lower() not in _FACT_YAYGIN}


def olgu_listesi(manifest, sinir: int = 200) -> list:
    """Manifestten SENARYOYA GIREBILEN iddialarin hafif kopyasi.

    ⚠ `celiskili` / `cozulmedi` iddialar `kullanilabilir_iddialar()` filtresinde
    zaten eleniyor; bu liste onlari HIC gormez.
    """
    cikti = []
    try:
        for i in manifest.kullanilabilir_iddialar()[:sinir]:
            kaynaklar = []
            for k in (getattr(i, "kaynaklar", None) or [])[:4]:
                kaynaklar.append({"alan": str(getattr(k, "alan", "") or ""),
                                  "url": str(getattr(k, "url", "") or ""),
                                  "tur": str(getattr(k, "tur", "") or "")})
            cikti.append({
                "fact_id": str(getattr(i, "fact_id", "") or ""),
                "metin": str(getattr(i, "metin", "") or ""),
                "guven": str(getattr(i, "guven", "") or ""),
                "kategori": str(getattr(i, "kategori", "") or ""),
                "kritik": bool(getattr(i, "kritik", False)),
                "kaynaklar": kaynaklar,
            })
    except Exception as e:
        print(f"  olgu listesi cikarilamadi: {type(e).__name__}", file=sys.stderr)
    return [o for o in cikti if o["fact_id"] and o["metin"]]


def paketlerden_olgular(paketler=None, *, belgeler=None) -> list:
    """Olgu sozlukleri — TUKETICI KANITI YENIDEN DOGRULAYARAK uretir.

    ⚠ OLCULEN KUSUR (`Y11B1-SIGNER-ORACLE`, denetim): dogrulama ciktisini
    (public snapshot ya da HMAC muhuru) OTORITE saymak, imzalayiciyi bir
    ORACLE haline getiriyordu — muhurleme yolu erisilebilir oldugu surece
    cagiran istedigi icerigi "dogrulanmis" gosterebiliyordu.
    ⚠ Y-11b-1 SOZLESMESI: otorite bir DAMGA DEGIL, YENIDEN KOSULAN
    DOGRULAMADIR. Tuketici PAKETLERI ve REPLAY BELGELERINI verir;
    `fact_baglama.allowlist_kur` BURADA yeniden kosar ve olgular yalnizca
    o kosumun DONDURDUGU dogrulanmis paketlerden turer.
    ⚠ Belge verilmezse HICBIR olgu uretilmez (fail-closed).
    ⚠ IC API (`Y11B1-IC-API`): DISARIDAN `allowlist_sonucu` GIRISI YOKTUR.
    Otorite yalnizca `arastir_ve_zenginlestir`in IC yolundan gelir; o yol
    paketleri ve GUVENILIR GETIRME MAKBUZUNU (`replay_belgeleri`) birlikte
    tasir. ⚠ TEHDIT MODELI: surec ICINDE kotu niyetli bir cagiran
    (kendi sahte paketini + kendi sahte belgesini uyduran kod) KAPSAM
    DISIDIR; bu modul kaynak/ag kaynakli zehirlenmeye karsi korur.
    """
    import fact_baglama as _fbg
    _liste = [p for p in (paketler or []) if p is not None]
    if not _liste or belgeler is None:
        return []
    # ⚠ TEK OTORITE: BURADA yeniden kosulur.
    sonuc = _fbg.allowlist_kur(_liste, belgeler=belgeler)
    cikti = []
    for p in sorted(sonuc["paketler"], key=lambda x: getattr(x, "fact_id", "")):
        cikti.append({
            "fact_id": str(getattr(p, "fact_id", "")),
            "metin": str(getattr(p, "onerme", "")),
            "guven": "dogrulandi",
            "kategori": str(getattr(p, "kategori", "")),
            "kritik": bool(getattr(p, "kritik", False)),
            "kaynaklar": [{"alan": str(getattr(p, "alan", "")),
                           "url": str(getattr(p, "url", "")),
                           "tur": str(getattr(p, "source_class", ""))}],
            "exact_quote": str(getattr(p, "exact_quote", "")),
            "locator": str(getattr(p, "locator", "")),
            "document_hash": str(getattr(p, "document_hash", "")),
            "source_id": str(getattr(p, "source_id", "")),
            "stance": str(getattr(p, "stance", "")),
        })
    return cikti


def paket_havuzu_kur(konu: str, urller, *, erisim_tarihi: str,
                     getirici=None, cikarici=None, onbellek=None,
                     defter=None) -> dict:
    """KANIT-ONCE havuz: belge -> FactPacket -> allowlist -> olgu.

    ⚠ `allowlist_kur` TEK OTORITEDIR: paket kabul damgasi ve kanit replay'i
    oradan gecmeden hicbir olgu uretilmez.
    ⚠ Getirilen belgeler `replay_belgeleri` olarak DONER; boylece kanit
    daha sonra da REPLAY EDILEBILIR (bayat/uydurma tespiti).
    ⚠ ISTISNA FIRLATMAZ.
    """
    bos = {"paketler": [], "olgular": [], "allowlist": set(),
           "replay_belgeleri": {}, "redler": [], "snapshot": "",
           "ham_kaynak": 0}
    try:
        from arastirma import factpacket as _fp
        from arastirma import source_fetcher as _sf
        import fact_baglama as _fbg
    except Exception as e:                                   # noqa: BLE001
        return {**bos, "redler": [{"kod": "FACT-MODUL-YOK",
                                   "neden": f"{type(e).__name__}: {e}"}]}
    belgeler = {}

    def _getir(url):
        fn = getirici or (lambda u: _sf.sayfa_getir(u, onbellek=onbellek))
        sayfa = fn(url) or {}
        if sayfa.get("ok") and str(sayfa.get("metin") or "").strip():
            belgeler[_fp.source_id_uret(url)] = str(sayfa["metin"])
        return sayfa

    cik = cikarici or _fp.llm_cikarici(onbellek=onbellek, defter=defter)
    try:
        paketler, rapor = _fp.havuz_kur(konu, list(urller or []),
                                        erisim_tarihi=erisim_tarihi,
                                        getirici=_getir, cikarici=cik)
    except Exception as e:                                   # noqa: BLE001
        return {**bos, "replay_belgeleri": belgeler,
                "redler": [{"kod": "FACT-HAVUZ-HATASI",
                            "neden": f"{type(e).__name__}: {str(e)[:120]}"}]}
    # ⚠ TEK OTORITE: kanit REPLAY EDILEREK suzulur.
    izin = _fbg.allowlist_kur(paketler, belgeler=belgeler)
    kabul = izin["paketler"]
    _olg = paketlerden_olgular(kabul, belgeler=belgeler)
    return {"paketler": kabul,
            "olgular": _olg,
            "allowlist": izin["allowlist"],
            "replay_belgeleri": belgeler,
            "redler": list(rapor.get("redler") or []) + list(izin["redler"]),
            "snapshot": izin["snapshot"],
            "ham_kaynak": int(rapor.get("ham_kaynak") or 0)}


def fact_bagla(scenes, olgular, *, esik: float = None,
               yalnizca_footage: bool = True) -> dict:
    """Sahneleri DOGRULANMIS iddialara bagla. Sahneleri YERINDE gunceller.

    Her eslesen sahneye `fact_id` ve kisa `iddia_metni` yazilir. Eslesmeyen
    sahne fact_id ALMAZ (uydurma yok) ve `bosluklar` icinde gorunur.

    Doner: {"baglanan", "hedef", "kapsam_pct", "bosluklar", "esik",
            "olgu_sayisi", "kullanilan_fact"}

    ⚠ ISTISNA FIRLATMAZ. Olgu yoksa ya da girdi bozuksa hicbir sahne
    degistirilmez ve uretim hatti ESKISI GIBI surer.
    """
    esik = FACT_ESIK if esik is None else float(esik)
    rapor = {"baglanan": 0, "hedef": 0, "kapsam_pct": 0.0, "bosluklar": [],
             "esik": esik, "olgu_sayisi": 0, "kullanilan_fact": []}
    try:
        sahne_listesi = list(scenes or [])
        havuz = [o for o in (olgular or [])
                 if isinstance(o, dict) and o.get("fact_id") and o.get("metin")]
        rapor["olgu_sayisi"] = len(havuz)
        if not sahne_listesi:
            return rapor
        if not havuz:
            # ⚠ HAVUZ BOSSA DA SESSIZ KALMA: arastirma kostu ama senaryoya
            # girebilen tek bir iddia bile cikmadiysa bu bir KAPSAM
            # BOSLUGUDUR. Ilk surumde sessizce donuyordu; test yakaladi.
            for idx, s in enumerate(sahne_listesi):
                if not isinstance(s, dict):
                    continue
                if yalnizca_footage and str(s.get("kaynak")) != "footage":
                    continue
                rapor["hedef"] += 1
                rapor["bosluklar"].append(
                    {"sahne": idx,
                     "neden": "dogrulanmis olgu havuzu bos"})
            rapor["bosluklar"] = rapor["bosluklar"][:40]
            return rapor
        onbellek = [(o, _fact_belirtec(o["metin"])) for o in havuz]
        kullanilan = []
        for idx, s in enumerate(sahne_listesi):
            if not isinstance(s, dict):
                continue
            if yalnizca_footage and str(s.get("kaynak")) != "footage":
                continue
            rapor["hedef"] += 1
            # ⚠ Kullanicinin/planin ACIK fact_id'si varsa KORUNUR, ezilmez.
            if str(s.get("fact_id") or "").strip():
                rapor["baglanan"] += 1
                kullanilan.append(str(s["fact_id"]))
                continue
            sahne_bt = _fact_belirtec(
                f"{s.get('anlatim', '')} {s.get('footage_sorgu', '')} "
                f"{s.get('scene_prompt', '')}")
            if not sahne_bt:
                rapor["bosluklar"].append({"sahne": idx,
                                           "neden": "sahne metni bos"})
                continue
            en_iyi, en_puan = None, 0.0
            for o, bt in onbellek:
                if not bt:
                    continue
                ortak = len(sahne_bt & bt)
                if not ortak:
                    continue
                puan = ortak / float(len(sahne_bt | bt))
                if puan > en_puan:
                    en_iyi, en_puan = o, puan
            if en_iyi is None or en_puan < esik:
                # ⚠ UYDURMA fact_id YOK — bosluk GORUNUR kilinir.
                rapor["bosluklar"].append({
                    "sahne": idx,
                    "neden": (f"esik alti ortusme ({en_puan:.2f} < {esik:.2f})"
                              if en_iyi is not None else "eslesen olgu yok")})
                continue
            s["fact_id"] = en_iyi["fact_id"]
            s["iddia_metni"] = str(en_iyi["metin"])[:FACT_METIN_SINIRI]
            if en_iyi.get("kategori"):
                s.setdefault("sahne_amaci", "")
            rapor["baglanan"] += 1
            kullanilan.append(en_iyi["fact_id"])
        rapor["kullanilan_fact"] = sorted(set(kullanilan))
        if rapor["hedef"]:
            rapor["kapsam_pct"] = round(
                100.0 * rapor["baglanan"] / rapor["hedef"], 1)
        rapor["bosluklar"] = rapor["bosluklar"][:40]
    except Exception as e:
        print(f"  fact baglama hatasi: {type(e).__name__}: {e}",
              file=sys.stderr)
    return rapor


def olgu_blogu_paketten(olgular, sinir: int = MAKS_OLGU) -> str:
    """ACCEPTED paketlerden turemis olgulari plan promptu blogu yap.

    ⚠ OLCULEN KUSUR (`Y11B1-PLANNER-ESKI-CLAIM`, denetim): `brief_kur`
    `olgu_blogu(manifest)` cagiriyordu — yani planner/narration promptu
    hala CLAIM-FIRST zincirinden (`manifest.kullanilabilir_iddialar()`)
    besleniyordu. `Sonuc.olgular` kanit-once havuzdan gelse bile MODELE
    giden metin eski iddialardi: IKI FARKLI OTORITE.
    ⚠ Artik TEK OTORITE: accepted FactPacket -> `Sonuc.olgular` -> prompt.
    """
    liste = [o for o in (olgular or []) if isinstance(o, dict)][:sinir]
    if not liste:
        return ""
    satirlar = []
    for o in liste:
        alanlar = [a for a in (alan_adi(k.get("url", ""))
                               for k in (o.get("kaynaklar") or [])) if a]
        kaynak_not = (f" [{', '.join(sorted(set(alanlar))[:3])}]"
                      if alanlar else "")
        satirlar.append(f"- {o.get('metin', '')}{kaynak_not}")
    return "\n".join(satirlar)


def yetkili_olgular(sonuc: Sonuc) -> list:
    """YETKILI olgu listesi — YALNIZCA MUHURLU kayitlardan TUREtilir.

    ⚠ `Y11B1-HAM-DICT-OTORITE` + `-SIGNER-ORACLE`: `sonuc.olgular` HAM,
    MUTABLE dictlerdi; damga temelli otorite ise imzalayiciyi ORACLE
    yapiyordu.
    ⚠ Artik otorite `sonuc.paketler` + `sonuc.replay_belgeleri` uzerinden
    BURADA YENIDEN KOSULAN dogrulamadir. `sonuc.olgular` yalnizca GORUNUM.
    """
    return paketlerden_olgular(
        getattr(sonuc, "paketler", None) or [],
        belgeler=getattr(sonuc, "replay_belgeleri", None) or {})


def olgu_otoritesi_gecerli_mi(sonuc: Sonuc) -> bool:
    """Otorite (muhurlu kayit) VAR ve GECERLI mi?"""
    return bool(yetkili_olgular(sonuc))


def grounded_sonuc_hukmu(sonuc: Sonuc) -> dict:
    """Grounded arastirmanin HUKMU. ⚠ TEK OLCUT: accepted paket sayisi.

    ⚠ `Y11B1-PLANNER-ESKI-CLAIM`: hukum eskiden `dogrulanmis_iddia`
    (CLAIM-FIRST zinciri) uzerindendi; manifestte claim varsa 0 accepted
    paketle bile `ok=True` olup story ZENGINLESTIRILIYORDU.
    """
    yetkili = yetkili_olgular(sonuc)
    ham = len(getattr(sonuc, "olgular", None) or [])
    if ham and not yetkili:
        # ⚠ Olgu GORUNUYOR ama MUHURLU otorite YOK/BOZUK.
        return {"ok": False, "kod": "GROUNDED-OLGU-OTORITESI-YOK",
                "accepted": 0,
                "neden": "olgular MUHURLU kayitla dogrulanamadi"}
    if yetkili:
        return {"ok": True, "kod": "", "accepted": len(yetkili)}
    return {"ok": False, "kod": "GROUNDED-FACT-YOK", "accepted": 0,
            "neden": (f"{getattr(sonuc, 'dogrulanmis_iddia', 0)} claim-first "
                      f"iddia KABUL GEREKCESI DEGIL")}


def brief_kur(story: str, sonuc: Sonuc) -> str:
    """Kullanici metnini ACCEPTED FactPacket olgulariyla zenginlestir.

    ⚠ Kullanicinin kendi metni HER ZAMAN birincil kalir; olgular EK bolumdur.
    ⚠ TEK OTORITE: yalnizca `sonuc.olgular` (accepted paketlerden turemis).
    Accepted paket YOKSA metin AYNEN doner — eski manifest claim'i
    story'ye GIREMEZ.
    """
    # ⚠ `Y11B1-HAM-DICT-OTORITE`: otorite MUHURLU kayittir; ham
    # `sonuc.olgular` KULLANILMAZ.
    blok = olgu_blogu_paketten(yetkili_olgular(sonuc))
    if not blok:
        return story
    return (
        f"{story.strip()}\n\n"
        f"--- DOGRULANMIS OLGULAR (bagimsiz kaynaklarla teyit edildi) ---\n"
        f"Asagidakiler arastirma sonucu DOGRULANMIS olgulardir. Anlatimi bunlara\n"
        f"dayandir. Burada OLMAYAN bir rakam, tarih ya da isim UYDURMA.\n"
        f"{blok}\n"
        f"--- OLGU LISTESI SONU ---"
    )


def arastir_ve_zenginlestir(story: str, *, mod: str, is_adi: str,
                            cikti_dizin: str, bildir=None) -> tuple:
    """Ana giris. `(zenginlestirilmis_metin, Sonuc)` dondurur.

    HICBIR DURUMDA istisna firlatmaz — cagiran hat korunur.
    """
    import time
    t0 = time.time()
    s = Sonuc(konu=(story or "").strip()[:200])

    if mod not in ARASTIRILAN_TURLER:
        # Kurgu turlerinde arastirma anlamsiz; bu bir DUSUS DEGIL.
        return story, s
    if not ACIK:
        s.dusus_ekle("arastirma", "ARASTIRMA_ACIK=0 ile kapatilmis",
                     "Anlatim yalnizca kullanici metnine dayaniyor; "
                     "bagimsiz kaynak dogrulamasi yapilmadi.")
        return story, s

    try:
        from arastirma import fact_checker, researcher
        from arastirma.butce import KosuSiniri
        from arastirma.cache import MaliyetDefteri, Onbellek
    except Exception as e:
        s.dusus_ekle("arastirma", f"modul yuklenemedi: {type(e).__name__}: {e}",
                     "Arastirma atlandi; anlatim yalnizca kullanici metnine dayaniyor.")
        return story, s

    if not (os.environ.get("OPENAI_KEY") or "").strip():
        s.dusus_ekle("arastirma", "OPENAI_KEY kurulu degil",
                     "Web arastirmasi yapilamadi; anlatim yalnizca kullanici "
                     "metnine dayaniyor, bagimsiz kaynak yok.")
        return story, s

    if bildir:
        bildir("Konu araştırılıyor (kaynak toplanıyor)...", 2)

    try:
        sinir = KosuSiniri(toplam_sure_sn=SURE_TAVANI_SN)
        # ⚠ TAVAN ZORUNLU. `MaliyetDefteri(tavan_usd=None)` SINIRSIZ demektir
        # (cache.py: `float("inf") if self.tavan is None`). Video basina tavan
        # acikca verilir; asilirsa `ButceAsimi` firlar, researcher KONTROLLU
        # durur ve o ana kadarki iddialar KORUNUR.
        defter = MaliyetDefteri(is_adi=is_adi, tavan_usd=TAVAN_USD)
        onbellek = Onbellek()
        s.calisti = True
        manifest = researcher.arastir(
            s.konu, erisim_tarihi=_bugun(), soru_adedi=SORU_ADEDI,
            onbellek=onbellek, defter=defter, sinir=sinir)
    except Exception as e:
        s.sure_sn = time.time() - t0
        s.dusus_ekle("arastirma", f"{type(e).__name__}: {e}",
                     "Kaynak toplanamadi; anlatim yalnizca kullanici metnine "
                     "dayaniyor.")
        return story, s

    # ── DOGRULAMA: guven karari researcher'in degil fact_checker'in isi ──
    if bildir:
        bildir("İddialar bağımsız kaynaklarla doğrulanıyor...", 3)
    try:
        fact_checker.dogrula(manifest, bugun=_bugun(), onbellek=onbellek,
                             defter=defter, sinir=sinir)
    except Exception as e:
        s.dusus_ekle("dogrulama", f"{type(e).__name__}: {e}",
                     "Iddialar dogrulanamadi; DOGRULANMAMIS hicbir iddia "
                     "anlatiya SOKULMADI (guvenli taraf).")

    try:
        fact_checker.celiskileri_isaretle(manifest, bugun=_bugun())
    except Exception as e:
        s.dusus_ekle("celiski", f"{type(e).__name__}: {e}",
                     "Celiski taramasi yapilamadi.")

    # ── SAYIM: uydurma yok, gercek kayitlardan ──
    try:
        s.iddia_sayisi = len(manifest.iddialar)
        s.dogrulanmis_iddia = len(manifest.kullanilabilir_iddialar())
        s.celiskili_iddia = sum(1 for i in manifest.iddialar
                                if getattr(i, "guven", "") == "celiskili")
        s.kaynak_sayisi = len(manifest.arastirma_url_kumesi)
        s.sorgular = list(manifest.arama_sorgulari)
    except Exception as e:
        s.dusus_ekle("sayim", f"{type(e).__name__}: {e}", "Sayilar okunamadi.")

    # ── FAZ Y-11b-1: KANIT-ONCE HAVUZ, TEK OTORITE `allowlist_kur` ──
    # ⚠ `Y11B1-PAKET-SONUCA-TASINMIYOR`: `olgular` eskiden CLAIM-FIRST
    # zincirinden (`olgu_listesi(manifest)` -> `kullanilabilir_iddialar()`)
    # geliyordu. Artik ARAMANIN BULDUGU GERCEK URL'ler indirilip belge
    # metninden FactPacket cikarilir; kabul karari `allowlist_kur`indir.
    # ⚠ Kanit REPLAY EDILEBILIR: getirilen belgeler `replay_belgeleri`
    # olarak tasinir ve allowlist onlara karsi dogrulanir.
    try:
        _hav = paket_havuzu_kur(
            s.konu, sorted(manifest.arastirma_url_kumesi),
            erisim_tarihi=_bugun(), onbellek=onbellek, defter=defter)
        s.paketler = list(_hav["paketler"])
        s.replay_belgeleri = dict(_hav["replay_belgeleri"])
        # ⚠ OLGULAR YALNIZCA ACCEPTED PAKETLERDEN TURER.
        s.olgular = list(_hav["olgular"])
        print(f"  FACTPACKET HAVUZU: {len(s.paketler)} kabul, "
              f"{len(_hav.get('redler') or [])} red, "
              f"{_hav.get('ham_kaynak')} belge, "
              f"snapshot={_hav.get('snapshot')}", file=sys.stderr)
        if not s.paketler:
            s.dusus_ekle(
                "factpacket",
                "kanit-once havuzda KABUL EDILMIS paket yok",
                "Anlatiya girebilecek kanitli olgu URETILEMEDI; "
                "iddia UYDURULMADI.")
    except Exception as e:                                   # noqa: BLE001
        s.dusus_ekle("factpacket", f"{type(e).__name__}: {e}",
                     "Kanit-once havuz kurulamadi; kanitli olgu YOK.")

    try:
        s.maliyet_usd = float(getattr(defter, "toplam", 0.0) or 0.0)
    except Exception:
        s.maliyet_usd = 0.0

    # ── MANIFEST DOSYASI: /ciktilar altindan indirilebilir olsun ──
    try:
        os.makedirs(cikti_dizin, exist_ok=True)
        ad = f"{is_adi}_arastirma.json"
        manifest.yaz(os.path.join(cikti_dizin, ad))
        s.manifest_dosya = ad
    except Exception as e:
        s.dusus_ekle("manifest", f"{type(e).__name__}: {e}",
                     "Arastirma manifesti diske yazilamadi; sayilar yine de gecerli.")

    if sinir.durma_nedeni:
        s.dusus_ekle("arastirma", f"kontrollu durma: {sinir.durma_nedeni}",
                     f"Arastirma erken durdu; {s.dogrulanmis_iddia} dogrulanmis "
                     f"olguyla devam edildi.")

    s.sure_sn = time.time() - t0
    # ⚠ `Y11B1-PLANNER-ESKI-CLAIM`: hukum ARTIK accepted FactPacket
    # sayisindan gelir. Eski `dogrulanmis_iddia` (claim-first zinciri)
    # KABUL GEREKCESI DEGILDIR — manifestte claim olsa bile 0 accepted
    # paket varsa sonuc BASARISIZDIR ve story ZENGINLESTIRILMEZ.
    _hukum = grounded_sonuc_hukmu(s)
    if not _hukum["ok"]:
        s.dusus_ekle(
            "factpacket",
            "kanit-once havuzda KABUL EDILMIS paket yok "
            f"({s.dogrulanmis_iddia} claim-first iddia KABUL GEREKCESI DEGIL)",
            "Anlatim yalnizca kullanici metnine dayaniyor; videoda "
            "kanitli olgu YOK.")
        print(f"  ARASTIRMA: 0 KABUL EDILMIS paket "
              f"({s.iddia_sayisi} ham iddia, {s.kaynak_sayisi} kaynak) — "
              f"metin zenginlestirilmedi", file=sys.stderr)
        return story, s

    s.ok = True
    print(f"  ARASTIRMA: {len(s.olgular)} KABUL EDILMIS paket "
          f"({s.iddia_sayisi} ham iddia, {s.kaynak_sayisi} kaynak), "
          f"{s.sure_sn:.0f} sn, ${s.maliyet_usd:.3f}", file=sys.stderr)
    return brief_kur(story, s), s


def atiflar_paketten(olgular, sinir: int = 40) -> list:
    """ACCEPTED paketlerden atif/provenance satirlari.

    ⚠ `Y11B1-IKI-OTORITE`: atiflar eskiden CLAIM-FIRST manifest dosyasindan
    okunuyordu — planner bir otoriteden, atif BASKA bir otoriteden
    besleniyordu; reddedilmis iddialarin URL'leri de kaynakcaya giriyordu.
    ⚠ Artik atif da YALNIZCA accepted paketlerden turer.
    """
    gorulen, cikti = set(), []
    for o in (olgular or []):
        if not isinstance(o, dict):
            continue
        for k in (o.get("kaynaklar") or []):
            u = str(k.get("url") or "")
            if not u or u in gorulen:
                continue
            gorulen.add(u)
            cikti.append({"url": u,
                          "alan": str(k.get("alan") or alan_adi(u)),
                          "tur": str(k.get("tur") or ""),
                          "fact_id": str(o.get("fact_id") or "")})
            if len(cikti) >= sinir:
                return cikti
    return cikti


def atif_satirlari(cikti_dizin: str, manifest_dosya: str, sinir: int = 40,
                   *, olgular=None) -> list:
    """Kullaniciya gosterilecek kaynak listesi.

    ⚠ `olgular` (accepted paketlerden turemis) verilirse TEK OTORITE odur;
    manifest dosyasi OKUNMAZ. Geriye uyum icin `olgular` verilmezse eski
    manifest yolu korunur.
    """
    if olgular is not None:
        return atiflar_paketten(olgular, sinir)
    if not manifest_dosya:
        return []
    yol = os.path.join(cikti_dizin, manifest_dosya)
    try:
        with open(yol, encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        return []
    gorulen, cikti = set(), []
    for i in d.get("iddialar") or []:
        for k in i.get("kaynaklar") or []:
            u = k.get("url") or ""
            if not u or u in gorulen:
                continue
            gorulen.add(u)
            cikti.append({"baslik": (k.get("baslik") or alan_adi(u) or u)[:160],
                          "url": u, "alan": alan_adi(u),
                          "erisim": k.get("erisim_tarihi", "")})
            if len(cikti) >= sinir:
                return cikti
    return cikti
