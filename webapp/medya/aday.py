"""MEDYA ADAYI veri modeli + aday manifesti.

Neden Faz A'daki `MedyaVarligi` yeterli degil: o sinif RENDER'A GIRECEK varligi
temsil ediyor ve `dogrula()` lisans bozuksa ISTISNA FIRLATIYOR. Bu, Faz A'nin
en degerli guvencesi ve zayiflatilmayacak.

Ama Faz B'nin isi ADAY toplamak: bir sahne icin 20 aday bulunur, 14'u lisans
yuzunden reddedilir, 6'si siralanir, 1'i secilir. Reddedilenlerin GEREKCESIYLE
kaydedilmesi gerekiyor (kullanicinin istegi: "her aday ve ret gerekcesi").
Istisna firlatan bir sinifla bunu yapamayiz.

Cozum: iki ayri tur.
  MedyaAdayi   — her sey, red gerekceleri dahil (bu dosya)
  MedyaVarligi — yalnizca SECILEN ve lisansi kanitli olan (Faz A, degismedi)

`MedyaAdayi.varliga_cevir()` kopruyu kuruyor ve lisans duvarindan gecmeyen
adayi cevirmeyi REDDEDIYOR.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from typing import Optional

from arastirma.manifests import MedyaVarligi, TelifIhlaliHatasi

SEMA_SURUM = "1.0"


@dataclass
class MedyaAdayi:
    """Bir sahne icin bulunmus TEK medya adayi — secilmis ya da reddedilmis."""
    asset_id: str
    saglayici: str
    tur: str = "image"                  # image | video
    orijinal_url: str = ""              # medyanin bulundugu SAYFA (provenance)
    indirme_url: str = ""               # dogrudan medya dosyasi
    baslik: str = ""
    aciklama: str = ""

    # ── lisans / provenance ──
    ham_lisans: str = ""
    lisans: str = "unknown"
    lisans_url: str = ""
    eser_sahibi: str = ""
    atif_gerekli: bool = True
    atif_metni: str = ""
    ticari_izin: bool = False
    degistirme_izni: bool = False
    render_kullanilabilir: bool = False
    red_nedeni: str = ""
    erisim_tarihi: str = ""

    # ── baglanti ──
    fact_id: str = ""
    scene_id: str = ""
    sahne_amaci: str = ""               # establishing | detay | arsiv | belge | harita | ortam
    sorgu: str = ""

    # ── teknik ──
    genislik: int = 0
    yukseklik: int = 0
    sure_sn: float = 0.0
    en_boy: float = 0.0
    icerik_hash: str = ""
    indirme_durumu: str = "indirilmedi"   # indirilmedi | indirildi | basarisiz | atlandi

    # ── metadata ──
    ulke: str = ""
    konum: str = ""
    tarih: str = ""
    varliklar: list = field(default_factory=list)   # kisi/kurum adlari

    # ── puanlar ──
    semantik_skor: float = 0.0
    vision_skor: float = 0.0
    teknik_skor: float = 0.0
    ceza: float = 0.0
    toplam_skor: float = 0.0
    skor_detay: dict = field(default_factory=dict)

    karar: str = "aday"                 # aday | secildi | reddedildi | reference_only
    karar_nedeni: str = ""

    def __post_init__(self):
        if self.genislik and self.yukseklik and not self.en_boy:
            self.en_boy = round(self.genislik / self.yukseklik, 4)
        if not self.icerik_hash:
            # Icerik indirilmeden once kimlik: dogrudan URL'nin hash'i.
            # Indirme sonrasi gercek dosya hash'i ile DEGISTIRILIR.
            self.icerik_hash = "url:" + hashlib.sha256(
                (self.indirme_url or self.orijinal_url or self.asset_id).encode()
            ).hexdigest()[:24]

    @property
    def tekil_anahtar(self) -> str:
        """Dedup icin: ayni dosya farkli saglayicidan gelebilir."""
        return self.icerik_hash

    def reddet(self, neden: str) -> "MedyaAdayi":
        self.karar = "reference_only" if self.orijinal_url else "reddedildi"
        self.karar_nedeni = neden
        self.render_kullanilabilir = False
        return self

    def varliga_cevir(self, arastirma=None) -> MedyaVarligi:
        """Faz A'nin katı MedyaVarligi'na cevir.

        Lisans duvarindan gecmemis adayi cevirmeyi REDDEDER — boylece
        reference_only bir oge kazara render hattina giremez.
        """
        if not self.render_kullanilabilir:
            raise TelifIhlaliHatasi(
                f"{self.asset_id}: render_kullanilabilir=False "
                f"({self.red_nedeni or 'gerekce yok'}) — varliga cevrilemez")
        return MedyaVarligi.olustur(
            arastirma=arastirma,
            asset_id=self.asset_id, tur=self.tur,
            orijinal_url=self.orijinal_url, indirme_url=self.indirme_url,
            saglayici=self.saglayici, lisans=self.lisans,
            eser_sahibi=self.eser_sahibi, lisans_url=self.lisans_url,
            erisim_tarihi=self.erisim_tarihi, fact_id=self.fact_id,
            ulke=self.ulke, donem=self.tarih, baslik=self.baslik,
            genislik=self.genislik, yukseklik=self.yukseklik,
            sure_sn=self.sure_sn, vision_skoru=self.vision_skor,
            semantik_skoru=self.semantik_skor, karar="secildi",
            karar_nedeni=self.karar_nedeni)


@dataclass
class AdayManifesti:
    """Tum sahnelerin tum adaylari + kapsam bosluklari."""
    konu: str = ""
    olusturma: str = ""
    sema: str = SEMA_SURUM
    # Islenmeye BASLANAN sahne sayisi. Kapsam orani bundan hesaplanir; adaylardan
    # turetmek yanlisti: hic aday yoksa sahne sayisi 0 gorunup oran -2.0 cikiyordu.
    sahne_sayisi: int = 0
    detay_cagrisi: int = 0          # kac oge-ayrinti istegi yapildi (butce raporu)
    adaylar: list = field(default_factory=list)          # list[MedyaAdayi]
    kapsam_bosluklari: list = field(default_factory=list)
    saglayici_hatalari: list = field(default_factory=list)
    notlar: list = field(default_factory=list)

    def ekle(self, a: MedyaAdayi) -> None:
        self.adaylar.append(a)

    def secilenler(self) -> list:
        return [a for a in self.adaylar if a.karar == "secildi"]

    def kullanilabilir(self) -> list:
        return [a for a in self.adaylar if a.render_kullanilabilir]

    def sahne_bazinda(self) -> dict:
        d: dict = {}
        for a in self.adaylar:
            d.setdefault(a.scene_id or "-", []).append(a)
        return d

    def saglayici_dagilimi(self) -> dict:
        d: dict = {}
        for a in self.secilenler():
            d[a.saglayici] = d.get(a.saglayici, 0) + 1
        return d

    def red_dagilimi(self) -> dict:
        d: dict = {}
        for a in self.adaylar:
            if a.karar in ("reddedildi", "reference_only"):
                anahtar = (a.red_nedeni or a.karar_nedeni or "belirsiz")[:60]
                d[anahtar] = d.get(anahtar, 0) + 1
        return d

    def atif_blogu(self) -> str:
        satirlar, gorulen = [], set()
        for a in self.secilenler():
            if not a.atif_metni:
                continue
            if a.atif_metni in gorulen:
                continue
            gorulen.add(a.atif_metni)
            satirlar.append(a.atif_metni)
        return "\n".join(satirlar)

    def ozet(self) -> dict:
        sec = self.secilenler()
        dag = self.saglayici_dagilimi()
        hakim = ""
        if sec:
            en = max(dag.values())
            if en / len(sec) > 0.40:
                hakim = max(dag, key=dag.get)
        return {
            "aday": len(self.adaylar),
            "kullanilabilir": len(self.kullanilabilir()),
            "secildi": len(sec),
            "reddedildi": sum(1 for a in self.adaylar if a.karar == "reddedildi"),
            "reference_only": sum(1 for a in self.adaylar if a.karar == "reference_only"),
            "saglayici_dagilimi": dag,
            "tek_saglayici_orani": (round(max(dag.values()) / len(sec), 3)
                                    if sec and dag else 0.0),
            "cesitlilik_ihlali": hakim,
            "kapsam_boslugu": len(self.kapsam_bosluklari),
            "red_dagilimi": self.red_dagilimi(),
        }

    def yaz(self, yol: str) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(yol)) or ".", exist_ok=True)
        gecici = yol + ".tmp"
        with open(gecici, "w", encoding="utf-8") as f:
            json.dump({"sema": self.sema, "konu": self.konu,
                       "olusturma": self.olusturma, "sahne_sayisi": self.sahne_sayisi,
                       "detay_cagrisi": self.detay_cagrisi, "ozet": self.ozet(),
                       "atif_blogu": self.atif_blogu(),
                       "kapsam_bosluklari": self.kapsam_bosluklari,
                       "saglayici_hatalari": self.saglayici_hatalari,
                       "notlar": self.notlar,
                       "adaylar": [asdict(a) for a in self.adaylar]},
                      f, ensure_ascii=False, indent=1)
        os.replace(gecici, yol)
