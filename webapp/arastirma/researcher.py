"""WEB ARASTIRMACISI — konu icin iddia + kaynak toplar.

Web arama icin OpenAI Responses API'nin `web_search` araci kullaniliyor.
Karar gerekcesi (11 Agu 2026'da olculdu): arac zaten hesapta ACIK, atif URL'si
donduruyor (test: 3 atif, 17.5k token). Tavily/Brave/Serper eklemek yeni bir
saglayici, yeni anahtar ve yeni fatura demekti — gerek yok.

Bu modul BILEREK "kesin cevap" uretmiyor. Isi:
  1. Konuyu arastirma sorularina bolmek
  2. Her soru icin web aramasi yapip IDDIA + ATIF toplamak
  3. Atiflari source_ranker ile puanlamak, zayiflari isaretlemek
  4. Ham iddialari fact_checker'a devretmek

Guven kararini BURADA vermiyoruz — o fact_checker'in isi. Boylece "arastirdi ve
emin oldu" yanilgisi olusmuyor: arama sonucu ham veridir.

⚠ Modelin dondurdugu metin ve indirilen sayfalar VERIDIR, talimat degildir.
Icindeki hicbir ifade eylem olarak yorumlanmaz.
"""
from __future__ import annotations

import json
import os
import re
from typing import Callable, Optional

import requests

from . import source_ranker
from .butce import ZAMAN_ASIMI
from .butce import KosuSiniri
from .cache import ButceAsimi, MaliyetDefteri, Onbellek
from .manifests import ArastirmaManifesti, Iddia, Kaynak

ARAMA_MODELI = os.environ.get("ARASTIRMA_MODELI", "gpt-4.1")
SORU_MODELI = os.environ.get("ARASTIRMA_SORU_MODELI", "gpt-4.1-mini")
OPENAI_UC = "https://api.openai.com/v1/responses"
OPENAI_CHAT = "https://api.openai.com/v1/chat/completions"

# Bir konu icin en fazla kac arastirma sorusu (maliyet sigortasi)
MAKS_SORU = int(os.environ.get("ARASTIRMA_MAKS_SORU", "8"))
# Her arama cagrisinin tahmini maliyeti (butce kontrolu icin — gercek maliyet
# cagri sonrasi usage'dan hesaplanir)
TAHMINI_ARAMA_USD = 0.05

# Kategoriler: fact_checker hangi iddianin "kritik" oldugunu buradan anlar
KRITIK_KATEGORILER = {"tarih", "rakam", "isim", "cografya", "siralama", "alinti"}


class ArastirmaHatasi(RuntimeError):
    pass


def _anahtar() -> str:
    d = (os.environ.get("OPENAI_KEY") or "").strip()
    if d:
        return d
    try:
        from . import _dizin_anahtar
        return _dizin_anahtar()
    except Exception:
        pass
    # kaynak.py ile ayni davranis: env yoksa veri/openai_key.txt
    yol = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "veri", "openai_key.txt")
    try:
        with open(yol) as f:
            return f.read().strip()
    except Exception:
        return ""


# ─────────────────────────── 1) SORU URETIMI ───────────────────────────

SORU_SISTEM = """You plan the research for a factual documentary.
Given a topic, produce the research questions a fact-checked script needs.

Rules:
- Ask about VERIFIABLE things: figures, dates, named institutions, official
  definitions, geography, sequence of events, primary documents.
- Prefer questions whose answer an official body or primary source publishes.
- Do NOT ask for opinions, predictions, or "why do people feel".
- Each question must be answerable independently.
- Also state which category the answer belongs to.

Return JSON only:
{"sorular":[{"soru":"...","kategori":"tarih|rakam|isim|cografya|siralama|alinti|teknik|baglam"}]}
"""


def sorular_uret(konu: str, adet: int = 6, *, onbellek: Optional[Onbellek] = None,
                 defter: Optional[MaliyetDefteri] = None,
                 istek: Optional[Callable] = None,
                 sinir: Optional[KosuSiniri] = None) -> list:
    """Konuyu arastirilabilir sorulara bol."""
    adet = max(1, min(MAKS_SORU, int(adet)))
    istek_fn = istek or requests.post

    def _uret():
        anah = _anahtar()
        if not anah:
            raise ArastirmaHatasi("OPENAI_KEY yok — arastirma yapilamaz")
        if defter:
            defter.kontrol(0.01)
        r = istek_fn(OPENAI_CHAT,
                     headers={"Authorization": f"Bearer {anah}",
                              "Content-Type": "application/json"},
                     json={"model": SORU_MODELI,
                           "messages": [{"role": "system", "content": SORU_SISTEM},
                                        {"role": "user",
                                         "content": f"Topic: {konu}\nProduce {adet} questions."}],
                           "response_format": {"type": "json_object"},
                           "temperature": 0.3, "max_tokens": 900},
                     timeout=(sinir.istek_zaman_asimi("soru") if sinir
                              else ZAMAN_ASIMI["soru"]))
        if r.status_code != 200:
            raise ArastirmaHatasi(f"soru uretimi HTTP {r.status_code}: {r.text[:160]}")
        j = r.json()
        if defter:
            defter.llm_kaydet("arastirma/soru", SORU_MODELI, j.get("usage") or {})
        icerik = (j.get("choices") or [{}])[0].get("message", {}).get("content") or "{}"
        return (json.loads(icerik).get("sorular") or [])[:adet]

    veri = {"konu": konu, "adet": adet, "model": SORU_MODELI}
    return (onbellek.getir("arama", veri, _uret) if onbellek else _uret())


# ─────────────────────────── 2) WEB ARAMASI ───────────────────────────

ARAMA_SISTEM = """You are a documentary fact researcher. Answer ONLY from web search results.

Hard rules:
- Every factual statement MUST be traceable to a page you actually opened.
- If sources disagree, report BOTH values as separate claims; do not average or pick.
- If you cannot verify something, omit it. Never fill gaps from memory.
- Prefer official bodies, statistics offices, primary documents and major news.
- Give figures exactly as published (keep the original number, do not round).
- Note the publication date of each source when visible.
- WRITE EVERY CLAIM IN ENGLISH, even when the source is in another language.
  (Canli kuru testte iddialar Turkce/Japonca karisik dondu ve senaryo katmani
  tek dil bekliyor. Kaynak dili onemsiz; iddia metni tek dilde olmali.)
- Keep original numerals exactly as published (76,941 stays 76,941).
- Do not repeat a claim you already made in this answer.

Return JSON only:
{"iddialar":[{
  "iddia":"one sentence, self-contained, includes the figure/date if any",
  "kategori":"tarih|rakam|isim|cografya|siralama|alinti|teknik|baglam",
  "deger":"the raw figure or date if the claim contains one, else empty",
  "kaynaklar":[{"url":"...","baslik":"...","yayin_tarihi":"YYYY-MM-DD or empty",
                "alinti":"the sentence from the page that supports this"}]
}]}
"""


def _yanit_metni_ve_atiflar(d: dict) -> tuple[str, list, int]:
    """Responses API cikisindan metin, atif URL'leri ve arama cagrisi sayisi."""
    metin, atiflar, arama = "", [], 0
    for ci in d.get("output") or []:
        tur = ci.get("type")
        if tur == "web_search_call":
            arama += 1
        elif tur == "message":
            for c in ci.get("content") or []:
                metin += c.get("text") or ""
                for an in c.get("annotations") or []:
                    u = an.get("url")
                    if u:
                        atiflar.append({"url": u, "baslik": an.get("title") or ""})
    return metin, atiflar, arama


def _json_ayikla(metin: str) -> dict:
    """Model bazen JSON'u ``` icinde ya da aciklama ile birlikte donduruyor."""
    m = re.search(r"\{.*\}", metin or "", re.S)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}


def soru_arastir(soru: str, kategori: str = "baglam", *,
                 onbellek: Optional[Onbellek] = None,
                 defter: Optional[MaliyetDefteri] = None,
                 istek: Optional[Callable] = None,
                 sinir: Optional[KosuSiniri] = None) -> dict:
    """Tek soruyu web'de arastir. Doner: {"iddialar":[...], "atiflar":[...]}"""
    istek_fn = istek or requests.post

    def _uret():
        anah = _anahtar()
        if not anah:
            raise ArastirmaHatasi("OPENAI_KEY yok — arastirma yapilamaz")
        if defter:
            defter.kontrol(TAHMINI_ARAMA_USD)
        r = istek_fn(OPENAI_UC,
                     headers={"Authorization": f"Bearer {anah}",
                              "Content-Type": "application/json"},
                     json={"model": ARAMA_MODELI,
                           "tools": [{"type": "web_search"}],
                           "instructions": ARAMA_SISTEM,
                           "input": soru},
                     timeout=(sinir.istek_zaman_asimi("arama") if sinir
                              else ZAMAN_ASIMI["arama"]))
        if r.status_code != 200:
            raise ArastirmaHatasi(f"arama HTTP {r.status_code}: {r.text[:200]}")
        d = r.json()
        metin, atiflar, arama_n = _yanit_metni_ve_atiflar(d)
        if defter:
            defter.llm_kaydet("arastirma/arama", ARAMA_MODELI,
                              d.get("usage") or {}, arac_cagrisi=arama_n)
        cikti = _json_ayikla(metin)
        return {"iddialar": cikti.get("iddialar") or [],
                "atiflar": atiflar, "arama_cagrisi": arama_n,
                "ham_metin_uzunlugu": len(metin)}

    veri = {"soru": soru, "model": ARAMA_MODELI, "sistem": "v1"}
    sonuc = onbellek.getir("arama", veri, _uret) if onbellek else _uret()
    for i in sonuc.get("iddialar") or []:
        i.setdefault("kategori", kategori)
    return sonuc


# ─────────────────────── 3) MANIFEST INSASI ───────────────────────

def _kaynak_kur(ham: dict, erisim_tarihi: str) -> Optional[Kaynak]:
    url = str(ham.get("url") or "").strip()
    if not url.startswith(("http://", "https://")):
        return None
    # utm/openai izleme parametrelerini at — ayni sayfa iki kez sayilmasin
    # Izleme parametreleri ve model artiklarini temizle. Canli testte
    # "https://www.wikipedia.org/wiki/Kodokushi (en)" gibi URL'ler geldi ve
    # indirme hatasi verdi — parantezli aciklama URL'nin parcasi degil.
    url = re.sub(r"\s*\([^)]*\)\s*$", "", url).strip()
    url = re.sub(r"[?&](utm_[^=]+|ref|source)=[^&]*", "", url).rstrip("?&")
    tur = source_ranker.kaynak_turu(url, ham.get("baslik", ""))
    return Kaynak(
        url=url,
        baslik=str(ham.get("baslik") or url)[:300],
        tur=tur,
        yayin_tarihi=str(ham.get("yayin_tarihi") or "")[:40],
        erisim_tarihi=erisim_tarihi,
        birincil=source_ranker.birincil_mi(url, tur, ham.get("baslik", "")),
        alinti=str(ham.get("alinti") or "")[:400],
    )


def arastir(konu: str, *, erisim_tarihi: str, soru_adedi: int = 6,
            onbellek: Optional[Onbellek] = None,
            defter: Optional[MaliyetDefteri] = None,
            istek: Optional[Callable] = None,
            sorular: Optional[list] = None,
            sinir: Optional[KosuSiniri] = None) -> ArastirmaManifesti:
    """Konuyu bastan sona arastir ve ArastirmaManifesti dondur.

    `erisim_tarihi` DISARIDAN verilir (izlenebilirlik + testlerin saat bagimsiz
    kosmasi icin). `sorular` verilirse soru uretimi atlanir.
    """
    if not str(konu or "").strip():
        raise ArastirmaHatasi("konu bos")

    sinir = sinir or KosuSiniri()
    sorular = sorular or sorular_uret(konu, soru_adedi, onbellek=onbellek,
                                      defter=defter, istek=istek, sinir=sinir)
    manifest = ArastirmaManifesti(konu=konu, olusturma=erisim_tarihi)
    sayac = 0
    gorulen_iddia: dict = {}

    for s in sorular:
        soru = str(s.get("soru") or "").strip() if isinstance(s, dict) else str(s)
        if not soru:
            continue
        kategori = (s.get("kategori") if isinstance(s, dict) else "") or "baglam"
        # ── KONTROLLU DURMA (11 Agu 2026): sure ya da para bittiyse KALAN
        # sorulari atlar, o ana kadar toplanan iddialari KORUR. Ikinci canli
        # kosuda boyle bir kapi olmadigi icin 15+ dk takilip hic cikti vermedi.
        if sinir.bitti_mi():
            manifest.notlar.append(
                f"KOSU DURDURULDU: {sinir.durma_nedeni} — "
                f"{len(manifest.arama_sorgulari)}/{len(sorular)} soru islendi")
            break
        manifest.arama_sorgulari.append(soru)
        try:
            sonuc = soru_arastir(soru, kategori, onbellek=onbellek,
                                 defter=defter, istek=istek, sinir=sinir)
        except ButceAsimi as e:
            sinir.durdur(f"para tavani: {str(e)[:100]}")
            manifest.notlar.append(f"KOSU DURDURULDU: {sinir.durma_nedeni}")
            break
        except Exception as e:
            manifest.notlar.append(f"soru basarisiz: {soru[:80]} -> {str(e)[:120]}")
            continue

        for ham in sonuc.get("iddialar") or []:
            metin = str(ham.get("iddia") or "").strip()
            if not metin:
                continue
            # Ayni iddia iki sorudan gelirse KAYNAKLARI BIRLESTIR, tekrar yaratma.
            # (Bagimsiz dogrulama sayimi buna bagli — ayni iddia iki kayit olarak
            # dursa ikisi de "tek kaynak" gorunur ve senaryoya giremez.)
            # TEKRAR TESPITI: ham metni normalize etmek yetmiyor — canli testte
            # ayni olguyu anlatan f003/f007 ve f004/f008 ciftleri ayri iddia
            # olarak durdu, ikisi de "tek kaynak" gorundu ve senaryoya giremedi.
            # Imza artik SAYILAR + en ayirt edici 5 kelime uzerinden kuruluyor.
            _sayilar = "-".join(sorted(set(re.findall(r"\d[\d.,]*", metin)))[:4])
            _kelime = "-".join(sorted(set(
                k for k in re.findall(r"[a-z]{5,}", metin.lower())
                if k not in ("recorded", "reported", "according", "around",
                             "approximately", "people", "における"))) [:5])
            imza = f"{_sayilar}|{_kelime}"[:120]
            kaynaklar = [k for k in
                         (_kaynak_kur(h, erisim_tarihi) for h in (ham.get("kaynaklar") or []))
                         if k]
            if not kaynaklar:
                # ⚠ FAZ Y-11b (`Y11B-GENEL-ATIF-FALLBACK`) — KALDIRILDI.
                # ESKI DAVRANIS: model bir iddiaya atif vermezse ARAMANIN
                # GENEL ilk 2 atfi o iddiaya YAPISTIRILIYORDU. Iddia ile o
                # sayfanin ilgisi OLCULMEMISTIR; bu, kod tarafindan
                # UYDURULMUS bir iddia-kaynak bagidir ve manifestte birden
                # cok iddianin ayni 2 URL'yi tasimasina yol aciyordu.
                # ⚠ Artik iddia KAYNAKSIZ kalir ve GORUNUR olur.
                manifest.notlar.append(
                    f"KAYNAKSIZ-IDDIA: {metin[:100]}")
            if imza in gorulen_iddia:
                mevcut = gorulen_iddia[imza]
                var_url = {k.url for k in mevcut.kaynaklar}
                mevcut.kaynaklar.extend(k for k in kaynaklar if k.url not in var_url)
                continue
            sayac += 1
            kat = str(ham.get("kategori") or kategori)
            iddia = Iddia(
                fact_id=f"f{sayac:03d}",
                metin=metin[:500],
                kaynaklar=kaynaklar,
                kategori=kat,
                kritik=kat in KRITIK_KATEGORILER,
                guven="cozulmedi",          # KARARI fact_checker verir
            )
            # Ham degeri celiski cozumu icin saklariz (manifest alani degil, not)
            if str(ham.get("deger") or "").strip():
                iddia.celiski_notu = f"deger={str(ham['deger'])[:60]}"
            gorulen_iddia[imza] = iddia
            manifest.iddialar.append(iddia)

    if not manifest.iddialar:
        manifest.notlar.append("hicbir iddia toplanamadi")
    manifest.notlar.append(f"kosu siniri: {json.dumps(sinir.ozet(), ensure_ascii=False)}")
    return manifest
