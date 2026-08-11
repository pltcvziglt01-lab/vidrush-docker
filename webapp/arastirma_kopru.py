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


def brief_kur(story: str, manifest, sonuc: Sonuc) -> str:
    """Kullanici metnini DOGRULANMIS OLGULARLA zenginlestir.

    ⚠ Kullanicinin kendi metni HER ZAMAN birincil kalir; olgular EK bolumdur.
    Hicbir olgu kullanicinin anlatisini ezmez, yalnizca dogruluk cercevesi verir.
    """
    blok = olgu_blogu(manifest)
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
    if s.dogrulanmis_iddia == 0:
        s.dusus_ekle("dogrulama", "hicbir iddia bagimsiz kaynakla dogrulanamadi",
                     "Anlatim yalnizca kullanici metnine dayaniyor; videoda "
                     "arastirma kaynakli olgu YOK.")
        print(f"  ARASTIRMA: 0 dogrulanmis olgu ({s.iddia_sayisi} ham iddia, "
              f"{s.kaynak_sayisi} kaynak) — metin zenginlestirilmedi", file=sys.stderr)
        return story, s

    s.ok = True
    print(f"  ARASTIRMA: {s.dogrulanmis_iddia}/{s.iddia_sayisi} olgu dogrulandi, "
          f"{s.kaynak_sayisi} kaynak, {s.sure_sn:.0f} sn, ${s.maliyet_usd:.3f}",
          file=sys.stderr)
    return brief_kur(story, manifest, s), s


def atif_satirlari(cikti_dizin: str, manifest_dosya: str, sinir: int = 40) -> list:
    """Yazilmis manifestten kullaniciya gosterilecek kaynak listesi uret.
    Dosya yoksa BOS liste doner (uydurma kaynak yazmaz)."""
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
