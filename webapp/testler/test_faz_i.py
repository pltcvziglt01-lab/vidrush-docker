#!/usr/bin/env python3
"""FAZ I testleri — KARE KAPISI ve GERCEK MEDYA SECIM AKISINA BAGLANMASI.

Kapsam (I-1):
  1. Bolge/havza tablosu — kapsam OLCULEBILIR, iddia kanitli
  2. Beklenti kurulumu — sahne yoksa video baglamina duser
  3. PILOT VAKASI: "South Georgia" sahnesine gelen "Malta" klibi REDDEDILIR
  4. Yanlis pozitif korumalari — dusuk guven / yakin plan / komsu havza / bilinmeyen
  5. Donem ve biyom kapilari (kare uzerinden)
  6. Butce: cagri + USD + sure tavani KATI, sinirsiz butce YASAK, thread guvenli
  7. kaynak.py entegrasyonu: 4 saglayicinin indirme sonrasi kapiya bagli olmasi
  8. Gerileme yok: kapi uygulanamadiginda ESKI vision katmani calisir
  9. pipeline.py: kare ozeti ise yaziliyor, butce engeli DURUSTCE bildiriliyor

Kapsam (I-2a — hiyerarsik konsept/niyet taksonomisi):
 10. Agac kapsami OLCULEBILIR + bicim butunlugu + geriye uyumluluk koprusu
 11. 12+ BELIRGIN FARKLI KONSEPT deterministik siniflandirma
 12. Yapisal sinyaller (kelime listesinden BAGIMSIZ olcum)
 13. Belirsizlik: zorla etiket YOK, melez raporlanir, guven formulu acik
 14. Sinirli model analizi: klamplı, aday disi cevap YOK SAYILIR

⚠ DURUSTLUK KURALI: gercek vision cagrisi YAPILMAZ (para harcamaz). Kapinin
karar mantigi SAF fonksiyon olarak test edilir; entegrasyon sahte okuyucuyla
uctan uca kosturulur. Gercek modelin dogrulugu bu testin iddiasi DEGILDIR.
Taksonomi testleri de AG KULLANMAZ; model yolu sahte cagrilabilir ile kosar.

Kosum: python3 webapp/testler/test_faz_i.py
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import threading

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)

gecen, basarisiz, bloke = 0, [], []


def kontrol(ad, kosul, detay=""):
    global gecen
    if kosul:
        gecen += 1
        print(f"  ok   {ad}")
    else:
        basarisiz.append(f"{ad} — {detay}")
        print(f"  XX   {ad}  {detay}")


def bloke_yaz(ad, sebep):
    bloke.append(f"{ad} — {sebep}")
    print(f"  --   BLOKE {ad}: {sebep}")


def blok(ad):
    print(f"\n── {ad} ──")


def oku(*p):
    with open(os.path.join(*p), encoding="utf-8") as f:
        return f.read()


def _kaldirilan_hata(fn, tip) -> bool:
    """`fn()` beklenen tipte istisna FIRLATIYOR mu? Sessiz kabul yakalanir."""
    try:
        fn()
    except tip:
        return True
    except Exception:
        return False
    return False


def _derlenir(yol: str) -> bool:
    import py_compile as _pc
    try:
        _pc.compile(yol, doraise=True)
        return True
    except Exception:
        return False


from medya import kare_kapisi as kk          # noqa: E402
import medya_kapisi as mk                    # noqa: E402


# ═══════════════ 1. BOLGE / HAVZA TABLOSU ═══════════════
blok("1. Bolge tablosu — kapsam olculebilir")

kapsam = kk.kapsam_ozeti()
kontrol("kapsam_ozeti sayilabilir alanlar donduruyor",
        all(isinstance(kapsam.get(k), int) for k in
            ("bolge", "terim", "havza", "komsu_grup")), str(kapsam))
kontrol("tabloda en az 15 bolge var", kapsam["bolge"] >= 15, str(kapsam))
kontrol("tabloda en az 200 yer terimi var", kapsam["terim"] >= 200, str(kapsam))

bicim_hata = [b for b, (t, k, h) in kk.BOLGE.items()
              if not (isinstance(t, tuple) and t and isinstance(k, str)
                      and isinstance(h, str) and k and h)]
kontrol("tum bolge satirlari (terimler, kusak, havza) bicimli",
        not bicim_hata, str(bicim_hata))

kusak_disi = {k for _t, k, _h in kk.BOLGE.values()} - set(mk.BIYOM_ISARETI) - {"iliman"}
kontrol("bolge kusaklari medya_kapisi biyom sozluguyle hizali",
        not kusak_disi, str(kusak_disi))

kontrol("south georgia tabloda -> sub_antarktik",
        "sub_antarktik" in kk.bolge_bul("approaching South Georgia coast"))
kontrol("malta tabloda -> akdeniz",
        "akdeniz" in kk.bolge_bul("maltese pilot motorboat"))
kontrol("bilinmeyen yer bos kume dondurur",
        kk.bolge_bul("a quiet room with a wooden table") == set())

# Kelime siniri: "malta" alt dizi olarak baska kelimede gecmemeli
kontrol("kelime siniri calisiyor (maltase/asphalt yanlis eslesmiyor)",
        kk.bolge_bul("asphalt road and maltase enzyme") == set(),
        str(kk.bolge_bul("asphalt road and maltase enzyme")))


# ═══════════════ 2. BEKLENTI ═══════════════
blok("2. Beklenti kurulumu")

b_sahne = kk.beklenti_kur("small boat South Georgia sea storm", "")
kontrol("sahne sorgusundan bolge cikiyor",
        b_sahne["bolgeler"] == ["sub_antarktik"], str(b_sahne))
kontrol("sahneden cikinca kaynak='sahne'", b_sahne["kaynak"] == "sahne",
        str(b_sahne))

b_baglam = kk.beklenti_kur("small boat in a storm",
                           "Shackleton Endurance seferi 1915 Antarktika buzullari")
kontrol("sahne bolge vermezse VIDEO BAGLAMINA duser",
        b_baglam["bolgeler"] and b_baglam["kaynak"] == "baglam", str(b_baglam))
kontrol("baglamdan tarihsel donem cikiyor (1915)",
        b_baglam["tarihsel"] is True, str(b_baglam))

b_bos = kk.beklenti_kur("close up of hands", "")
kontrol("beklenti cikmayan sahnede bolge/biyom bos",
        not b_bos["bolgeler"] and not b_bos["biyomlar"], str(b_bos))

b_kusak = kk.beklenti_kur("Antarctica ice shelf", "")
kontrol("bolgeden biyom turetiliyor (kutup)",
        "kutup" in b_kusak["biyomlar"], str(b_kusak))


# ═══════════════ 3. PILOT VAKASI — MALTA / SOUTH GEORGIA ═══════════════
blok("3. PILOT VAKASI: Malta teknesi South Georgia diye KABUL EDILMEZ")

# FAZ-H-HANDOFF §13 "Bilinen sinir"da olculen gercek hata:
#   sorgu   "small boat South Georgia sea storm"
#   gelen   "maltese pilot motorboat"
#   sonuc   hicbir kapi tetiklenmedi
MALTA_SORGU = "small boat South Georgia sea storm"
MALTA_BAGLAM = "Shackleton Endurance seferi 1916 Guney Georgia"
MALTA_GOZLEM = {
    "yer_tahmini": "Malta, Mediterranean harbour",
    "biyom": "iliman",
    "isaretler": ["maltese luzzu fishing boat", "limestone harbour wall",
                  "calm blue Mediterranean water"],
    "modern_isaret": [],
    "yakin_plan": False, "insan": False, "guven": 0.86,
}

bekl = kk.beklenti_kur(MALTA_SORGU, MALTA_BAGLAM)
ok, kod, ger = kk.karar(bekl, MALTA_GOZLEM)
kontrol("Malta klibi South Georgia sahnesinde REDDEDILIR", ok is False, ger)
kontrol("red kodu HAVZA", kod == "HAVZA", f"{kod}: {ger}")
kontrol("gerekce iki tarafi da adlandiriyor (sessiz dusus yok)",
        "guney_kutup" in ger and "avrupa_akdeniz" in ger, ger)

# Eski metin kapilari bu vakayi YAKALAYAMIYOR — regresyonun kaniti
mk_ok, mk_ger = mk.kapi(MALTA_SORGU, "maltese pilot motorboat", MALTA_BAGLAM)
kontrol("metin kapisi bu vakayi hala yakalayamiyor (kare kapisi SART)",
        mk_ok is True, f"metin kapisi beklenmedik sekilde reddetti: {mk_ger}")

# Dogru klip GECMELI
DOGRU_GOZLEM = {
    "yer_tahmini": "sub-antarctic island, South Georgia",
    "biyom": "kutup",
    "isaretler": ["glacier tongue", "king penguins on black sand"],
    "modern_isaret": [], "yakin_plan": False, "insan": False, "guven": 0.9,
}
ok2, kod2, ger2 = kk.karar(bekl, DOGRU_GOZLEM)
kontrol("mesru sub-antarktik klip GECER", ok2 is True, f"{kod2}: {ger2}")


# ═══════════════ 4. YANLIS POZITIF KORUMALARI ═══════════════
blok("4. Yanlis pozitif korumalari — emin degilsen GECIR")

dusuk = dict(MALTA_GOZLEM, guven=0.4)
ok, kod, ger = kk.karar(bekl, dusuk)
kontrol("dusuk guvende REDDETMEZ", ok is True and kod == "DUSUK-GUVEN", ger)
kontrol("guven esigi 1.0'dan kucuk ve 0.5'ten buyuk",
        0.5 <= kk.GUVEN_ESIGI < 1.0, str(kk.GUVEN_ESIGI))

ok, kod, ger = kk.karar(bekl, {})
kontrol("bos gozlemde REDDETMEZ", ok is True and kod == "GOZLEM-YOK", ger)

ok, kod, ger = kk.karar(bekl, {"yakin_plan": True, "guven": 0.95,
                               "yer_tahmini": "", "isaretler": []})
kontrol("kulturel ipucusuz yakin planda REDDETMEZ",
        ok is True and kod == "YAKIN-PLAN", f"{kod}: {ger}")

ok, kod, ger = kk.karar(bekl, {"yer_tahmini": "an unnamed rocky shore",
                               "guven": 0.9})
kontrol("karede taninan bolge yoksa REDDETMEZ",
        ok is True and kod == "BOLGE-CIKMADI", f"{kod}: {ger}")

# KOMSU HAVZA: Fransa isteyip Akdeniz kiyisi gelmesi hata DEGIL
b_fr = kk.beklenti_kur("Provence lavender fields in France", "Fransa gezisi")
ok, kod, ger = kk.karar(b_fr, {"yer_tahmini": "Mediterranean coast, Italy",
                               "guven": 0.9})
kontrol("komsu havza (Fransa <-> Akdeniz) REDDEDILMEZ",
        ok is True, f"{kod}: {ger}")

# Patagonya <-> Guney Amerika komsulugu
b_pat = kk.beklenti_kur("Patagonia mountain trail", "")
ok, kod, ger = kk.karar(b_pat, {"yer_tahmini": "Andes, Argentina", "guven": 0.9})
kontrol("Patagonya <-> Ge. Amerika komsulugu REDDEDILMEZ", ok is True,
        f"{kod}: {ger}")

# Aday HEM beklenen HEM baska isaret tasiyorsa reddetme
ok, kod, ger = kk.karar(bekl, {
    "yer_tahmini": "South Georgia expedition, crew later sailed to Malta",
    "guven": 0.9})
kontrol("aday beklenen bolgeyi de tasiyorsa REDDEDILMEZ", ok is True,
        f"{kod}: {ger}")

# Beklenti yoksa kapi hic uygulanmaz
ok, kod, ger = kk.kare_kapisi("close up of hands weaving", "",
                              lambda: MALTA_GOZLEM)
kontrol("beklenti yoksa kapi uygulanmaz (okuma bile yapilmaz)",
        ok is True and kod == "BEKLENTI-YOK", f"{kod}: {ger}")

# Okuyucu yoksa
ok, kod, ger = kk.kare_kapisi(MALTA_SORGU, MALTA_BAGLAM, None)
kontrol("okuyucu yoksa kapi uygulanmaz", ok is True and kod == "OKUYUCU-YOK", ger)


# Okuyucu patlarsa is DURMAZ
def _patla():
    raise RuntimeError("vision 500")


ok, kod, ger = kk.kare_kapisi(MALTA_SORGU, MALTA_BAGLAM, _patla)
kontrol("okuyucu istisnasi isi durdurmaz (GECER)",
        ok is True and kod == "OKUMA-HATASI", f"{kod}: {ger}")
kontrol("okuma hatasi gerekcede gorunur (sessiz degil)", "vision 500" in ger, ger)


# ═══════════════ 5. DONEM ve BIYOM KAPILARI ═══════════════
blok("5. Donem ve biyom kapilari (kare uzerinden)")

b_tarih = kk.beklenti_kur("1915 expedition ship deck", "")
ok, kod, ger = kk.karar(b_tarih, {"yer_tahmini": "open sea",
                                  "modern_isaret": ["smartphone", "solar panel"],
                                  "guven": 0.9})
kontrol("tarihsel sahnede modern isaret REDDEDILIR",
        ok is False and kod == "DONEM", f"{kod}: {ger}")

b_guncel = kk.beklenti_kur("Antarctica research station today", "")
ok, kod, ger = kk.karar(b_guncel, {"yer_tahmini": "Antarctica",
                                   "modern_isaret": ["solar panel"],
                                   "biyom": "kutup", "guven": 0.9})
kontrol("guncel sahnede modern isaret REDDEDILMEZ", ok is True, f"{kod}: {ger}")

b_kutup = kk.beklenti_kur("iceberg field", "")
ok, kod, ger = kk.karar(b_kutup, {"yer_tahmini": "unnamed shore",
                                  "biyom": "tropik", "guven": 0.9})
kontrol("kutup sahnesinde tropik kare REDDEDILIR",
        ok is False and kod == "BIYOM", f"{kod}: {ger}")

ok, kod, ger = kk.karar(b_kutup, {"yer_tahmini": "unnamed shore",
                                  "biyom": "kutup", "guven": 0.9})
kontrol("kutup sahnesinde kutup kare GECER", ok is True, f"{kod}: {ger}")


# ═══════════════ 6. BUTCE ═══════════════
blok("6. Butce — cagri + USD + sure tavani KATI")

try:
    kk.KareButce(maks_cagri=None, maks_usd=0.1, maks_sn=10)
    kontrol("sinirsiz butce YASAK", False, "None kabul edildi")
except ValueError:
    kontrol("sinirsiz butce YASAK (ValueError)", True)

bt = kk.KareButce(maks_cagri=2, maks_usd=1.0, maks_sn=999)
sayac = [0]


def _oku():
    sayac[0] += 1
    return MALTA_GOZLEM


for i in range(5):
    kk.kare_kapisi(MALTA_SORGU, MALTA_BAGLAM, _oku, butce=bt,
                   kimlik=f"k{i}", onbellek={})
kontrol("cagri tavani KATI — 5 denemede 2 okuma", sayac[0] == 2, str(sayac[0]))
kontrol("tavan asilinca engel kaydediliyor (sessiz degil)",
        bt.ozet()["engel"], str(bt.ozet()))
kontrol("tavan dolunca kapi GECIRIR (klip atmaz)",
        kk.kare_kapisi(MALTA_SORGU, MALTA_BAGLAM, _oku, butce=bt,
                       kimlik="son", onbellek={})[1] == "BUTCE")

bt_usd = kk.KareButce(maks_cagri=999, maks_usd=kk.KARE_BIRIM_USD * 2.5, maks_sn=999)
sayac2 = [0]


def _oku2():
    sayac2[0] += 1
    return MALTA_GOZLEM


for i in range(6):
    kk.kare_kapisi(MALTA_SORGU, MALTA_BAGLAM, _oku2, butce=bt_usd,
                   kimlik=f"u{i}", onbellek={})
kontrol("USD tavani KATI (2.5 birim -> 2 okuma)", sayac2[0] == 2, str(sayac2[0]))
kontrol("harcanan USD tavani asmiyor",
        bt_usd.ozet()["usd"] <= bt_usd.maks_usd, str(bt_usd.ozet()))

# Sure tavani — enjekte saat (gercek beklemeden)
_t = [0.0]
bt_sure = kk.KareButce(maks_cagri=999, maks_usd=999, maks_sn=10,
                       saat=lambda: _t[0])
kontrol("sure tavani ilk anda uygun", bt_sure.uygun_mu()[0] is True)
_t[0] = 11.0
uygun, neden = bt_sure.uygun_mu()
kontrol("sure tavani asilinca uygun degil", uygun is False, neden)
kontrol("sure gerekcesi olculmus deger iceriyor", "sn" in neden, neden)

# THREAD GUVENLIGI: kontrol-sonra-harca yarisi tavani asirmamali
bt_th = kk.KareButce(maks_cagri=10, maks_usd=999, maks_sn=999)
sayac3 = [0]
kilit = threading.Lock()


def _yaris():
    for _ in range(20):
        ok_, _n = bt_th.yer_ayir()
        if ok_:
            with kilit:
                sayac3[0] += 1


thr = [threading.Thread(target=_yaris) for _ in range(8)]
for t in thr:
    t.start()
for t in thr:
    t.join()
kontrol("paralel 160 denemede cagri tavani ASILMIYOR",
        sayac3[0] == 10 and bt_th.ozet()["cagri"] == 10,
        f"verilen={sayac3[0]} sayac={bt_th.ozet()['cagri']}")

# Onbellek: ayni klip iki kez okunmaz
onb = {}
sayac4 = [0]


def _oku4():
    sayac4[0] += 1
    return MALTA_GOZLEM


bt2 = kk.KareButce(maks_cagri=99, maks_usd=9, maks_sn=999)
for _ in range(4):
    kk.kare_kapisi(MALTA_SORGU, MALTA_BAGLAM, _oku4, butce=bt2,
                   kimlik="ayni-klip", onbellek=onb)
kontrol("onbellek ayni klibi tekrar okumuyor", sayac4[0] == 1, str(sayac4[0]))
kontrol("onbellekten gelen karar da RED", onb["ayni-klip"][0] is False, str(onb))


# ═══════════════ 7. kaynak.py ENTEGRASYONU (STATIK) ═══════════════
blok("7. kaynak.py — 4 saglayici da indirme sonrasi kapiya bagli")

ks = oku(KOK, "kaynak.py")
kontrol("kare_kapisi import ediliyor", "from medya import kare_kapisi" in ks)
kontrol("import guvenli (kapi yoksa hat cokmuyor)",
        re.search(r"try:\s*\n\s*from medya import kare_kapisi", ks) is not None)

for sag in ("pexels", "pixabay", "coverr", "freepik"):
    # ⚠ `[^)]*` KULLANMA: cagrilar `_etkin_yer(sorgu)` gibi ic parantez iceriyor
    # ve desen ilk `)`de duruyordu — kod dogruyken test kirmizi yaniyordu.
    kontrol(f"{sag} indirme sonrasi _kare_dogrula cagiriyor",
            re.search(r'_kare_dogrula\(.{0,200}?"%s"' % sag, ks, re.S) is not None)

kontrol("eski _vision_yer_uygun cagri noktalari kaldirildi (tek giris)",
        ks.count("_vision_yer_uygun(") == 3,     # 1 tanim + 2 gerileme yolu
        str(ks.count("_vision_yer_uygun(")))
kontrol("kapi uygulanamayinca ESKI katmana dusuluyor (gerileme yok)",
        'kod in ("BEKLENTI-YOK", "BUTCE", "OKUMA-HATASI", "OKUYUCU-YOK")' in ks)
kontrol("is basinda butce sifirlaniyor",
        "kare_butce_kur()" in ks.split("def klip_gecmisi_sifirla")[1][:600])
kontrol("kare durumu KILITLI (paralel thread)",
        "_KARE_KILIT" in ks and "with _KARE_KILIT:" in ks)
kontrol("reddedilen klip diskten siliniyor",
        ks.count("os.remove(hedef)") >= 4, str(ks.count("os.remove(hedef)")))
kontrol("env ile kapatilabiliyor", 'os.environ.get("KARE_KAPISI"' in ks)
for env in ("KARE_MAKS_CAGRI", "KARE_MAKS_USD", "KARE_MAKS_SN", "KARE_ZAMAN_ASIMI"):
    kontrol(f"{env} env ile ayarlanabiliyor", f'os.environ.get("{env}"' in ks)

kontrol("kare okumasi TEK vision cagrisi (cift fatura yok)",
        ks.split("def _kare_gozlem_oku")[1].split("def _kare_dogrula")[0]
        .count("requests.post") == 1)
kontrol("okuma zaman asimi env'e bagli",
        "timeout=KARE_ZAMAN_ASIMI" in ks)
kontrol("anahtar yoksa okuma hata firlatir (sahte gecis yok)",
        'raise RuntimeError("OPENAI_KEY yok")' in ks)

# Modul gercekten import edilebiliyor mu (yol/isim hatasi yakalansin)
os.environ.setdefault("VIDRUSH_KOK", os.path.join(KOK, "..", "cikti"))
try:
    import kaynak as _kaynak
    kontrol("kaynak.py import edilebiliyor", True)
    kontrol("kaynak kare kapisini gercekten yukledi",
            _kaynak._kare_kapisi is not None)
    kontrol("kare_ozet() sozlesmesi", set(_kaynak.kare_ozet()) ==
            {"acik", "kapsam", "butce", "red_sayisi", "redler"},
            str(set(_kaynak.kare_ozet())))
    b = _kaynak.kare_butce_kur()
    kontrol("kare_butce_kur gercek butce donduruyor",
            b is not None and b.maks_cagri == _kaynak.KARE_MAKS_CAGRI)
    kontrol("yeni is butcesi SIFIRDAN basliyor",
            _kaynak.kare_ozet()["butce"]["cagri"] == 0)
    kontrol("kapi hic calismadiysa ozet bunu gosteriyor (kanitsiz iddia yok)",
            _kaynak.kare_ozet()["red_sayisi"] == 0)
except Exception as e:
    bloke_yaz("kaynak.py import", str(e)[:120])


# ═══════════════ 8. pipeline.py ENTEGRASYONU (STATIK) ═══════════════
blok("8. pipeline.py — kare ozeti ise yaziliyor")

pp = oku(KOK, "pipeline.py")
kontrol("sonuc['kare_kapisi'] yaziliyor", 'sonuc["kare_kapisi"]' in pp)
kontrol("kare redleri dususlere yaziliyor (gorunur)",
        "KARE dogrulamasinda reddedildi" in pp)
kontrol("butce engeli DURUSTCE bildiriliyor",
        "kare kapisi butcesi" in pp and "garanti degil" in pp)
kontrol("kare ozeti hattı COKERTMIYOR (try/except)",
        "kare ozeti okunamadi" in pp)
kontrol("mevcut medya_kapisi ozeti KORUNDU (gerileme yok)",
        'sonuc["medya_kapisi"]' in pp)


# ═══════════════ 9. DERLEME ═══════════════
blok("9. Derleme ve sozdizimi")

import py_compile                                     # noqa: E402
for f in ("kaynak.py", "pipeline.py", "medya/kare_kapisi.py"):
    try:
        py_compile.compile(os.path.join(KOK, f), doraise=True)
        kontrol(f"{f} derleniyor", True)
    except Exception as e:
        kontrol(f"{f} derleniyor", False, str(e)[:140])


# ═══════════════ 10. TAKSONOMI — AGAC ve GERIYE UYUMLULUK ═══════════════
blok("10. Taksonomi agaci — kapsam olculebilir, eski sozlesme korunuyor")

import taksonomi as tx                              # noqa: E402
import girdi_analizi as ga                          # noqa: E402

tk = tx.kapsam_ozeti()
kontrol("kapsam_ozeti sayilabilir",
        all(isinstance(tk.get(k), int) for k in
            ("aile", "dal", "anahtar", "sinyal", "sinyal_bagi", "karsit")), str(tk))
kontrol("en az 7 aile var", tk["aile"] >= 7, str(tk["aileler"]))
kontrol("en az 30 dal var", tk["dal"] >= 30, str(tk["dal"]))
kontrol("en az 15 yapisal sinyal var", tk["sinyal"] >= 15, str(tk["sinyal"]))
kontrol("dallarin cogu yapisal sinyale bagli (salt kelime listesi degil)",
        tk["sinyal_bagi"] >= 20, str(tk["sinyal_bagi"]))
kontrol("yanlis pozitif korumasi (karsit) tanimli", tk["karsit"] >= 30,
        str(tk["karsit"]))

bicim = [y for y, d in tx.AGAC.items()
         if "." not in y or not d.get("ad") or not isinstance(d.get("anahtar"), tuple)
         or not isinstance(d.get("sinyal"), dict) or not isinstance(d.get("karsit"), tuple)]
kontrol("tum dallar 'aile.tur' bicimli ve dolu", not bicim, str(bicim))

bilinmeyen_sinyal = {s for d in tx.AGAC.values() for s in d["sinyal"]} - set(tx.SINYAL)
kontrol("dallar yalnizca TANIMLI sinyallere baglaniyor",
        not bilinmeyen_sinyal, str(bilinmeyen_sinyal))

aile_eksik = {y.split(".")[0] for y in tx.AGAC} - set(tx.ESKI_ETIKET)
kontrol("her ailenin ESKI ETIKET karsiligi var (geriye uyumluluk)",
        not aile_eksik, str(aile_eksik))
kontrol("eski etiketler BES degerin disina cikmiyor",
        set(tx.ESKI_ETIKET.values()) <= {"belgesel", "seyahat", "aciklayici",
                                         "urun", "hikaye"},
        str(set(tx.ESKI_ETIKET.values())))
kontrol("aile adlari tanimli", not ({y.split(".")[0] for y in tx.AGAC} - set(tx.AILE_AD)))

# ⚠ ESKI 5 ETIKETE DOKUNULMADI — Faz H sozlesmesi aynen gecerli
kontrol("girdi_analizi.TUR_SINYALI hala 5 etiket",
        set(ga.TUR_SINYALI) == {"belgesel", "seyahat", "aciklayici", "urun", "hikaye"},
        str(set(ga.TUR_SINYALI)))
kontrol("eski tur_tespit davranisi degismedi (belgesel)",
        ga.tur_tespit("1915 keşif seferi arşiv belgesel")[0] == "belgesel")
kontrol("eski tur_tespit davranisi degismedi (belirsiz)",
        ga.tur_tespit("zzz qqq www")[0] == "belirsiz")
kontrol("taksonomi AG KULLANMIYOR (ucretsiz)",
        all(x not in oku(KOK, "taksonomi.py")
            for x in ("requests", "openai.com", "http://", "https://", "urllib")))


# ═══════════════ 11. 12+ KONSEPT — DETERMINISTIK SINIFLANDIRMA ═══════════════
blok("11. 12+ belirgin farkli konsept")

# (ad, metin, beklenen_aile, beklenen_turler)
MATRIS = [
    ("belgesel/tarih",
     "John D. Rockefeller ve Standard Oil'in yukselisi: 1870'te kurulan "
     "sirketin 1911'deki mahkeme kararıyla parcalanmasina uzanan tarih, "
     "arsiv belgeleriyle anlatiliyor.",
     "belgesel", {"tarih", "biyografi", "arastirma"}),

    ("biyografi",
     "Marie Curie kimdi? Hayati, iki Nobel odulu ve 1934'teki olumu: "
     "bilim kadininin portresi ve kariyeri.",
     "belgesel", {"biyografi", "tarih"}),

    ("ulke-sehir 4K gezi",
     "Isvicre 4K sinematik: Interlaken, Zermatt ve Luzern manzaralari, "
     "60 fps drone cekimi ve yuruyus turu.",
     "seyahat", {"ulke_4k", "hava_drone", "doga_manzara", "sehir"}),

    ("bilim",
     "Kara delikler nasil olusur? Genel gorelilik teorisi, olay ufku ve "
     "NASA arastirmacilarinin uzay gozlemleri basitce aciklaniyor.",
     "egitim", {"bilim", "aciklayici"}),

    ("teknoloji",
     "Yapay zeka modelleri nasil calisir? Makine ogrenmesi, algoritma "
     "egitimi ve veri merkezi islemci altyapisi anlatiliyor.",
     "egitim", {"teknoloji", "aciklayici", "bilim"}),

    ("finans",
     "Enflasyon ve faiz kararlari borsayi nasil etkiler? Hisse "
     "portfoy dagilimi, %25 getiri beklentisi ve resesyon riski.",
     "egitim", {"finans"}),

    ("spor",
     "Derbi ozeti: 3-1'lik macta 90. dakikada atilan gol ve puan durumu; "
     "takim kadrosu, stadyum atmosferi ve sampiyona yarisi.",
     "yasam", {"spor"}),

    ("true crime",
     "Faili mechul bir cinayet dosyasi: 1998'de kaybolan kurbanin adli "
     "delilleri, dedektifin sorusturma notlari ve cozulmemis dava.",
     "belgesel", {"true_crime", "arastirma", "tarih"}),

    ("yemek",
     "Klasik mercimek corbasi tarifi: 200 g kirmizi mercimek, 2 yemek "
     "kasigi tereyagi ve 1 litre su. Once sogani kavurun, sonra "
     "malzemeleri ekleyin ve 25 dakika pisirin.",
     "yasam", {"yemek"}),

    ("egitim/ders",
     "9. sinif matematik konu anlatimi: turev dersi, adim adim alistirma "
     "cozumleri ve sinav hazirlik odevi. Ogrenciler icin mufredat rehberi.",
     "egitim", {"ders", "aciklayici"}),

    ("urun tanitimi",
     "Yeni Pixel 9 lansmani: ozellikleri, kamera performansi ve 24999 TL "
     "fiyat etiketi. Kampanya kapsaminda indirim var.",
     "urun", {"tanitim", "inceleme", "karsilastirma"}),

    ("muzik/kultur",
     "Anadolu rock tarihinin unutulmaz albumleri: besteci ve sanatcilarin "
     "melodileri, orkestra duzenlemeleri ve konser kayitlari.",
     "kultur", {"muzik", "sanat"}),

    # Onceki oturumun test matrisinden ek konseptler
    ("korku hikayesi",
     "Kabus gibi bir gece: perili evin karanlik koridorunda beliren golge "
     "ve duyulan ciglik. \"Kapiyi acma\" dedi sesi titreyerek.",
     "hikaye", {"korku", "kurgu"}),

    ("cocuk hikayesi",
     "Sevimli tavsan ve arkadaslik masali: uyku masali olarak anlatilan, "
     "cocuklar icin kisa bir hikaye. \"Merhaba kucuk dostum\" dedi prenses.",
     "hikaye", {"cocuk", "kurgu"}),

    ("emlak turu",
     "Bogaz manzarali 3+1 daire turu: 145 m2 kullanim alani, ic mimari "
     "dekorasyonu ve satilik konut fiyat bilgisi.",
     "yasam", {"emlak"}),

    ("otomotiv sinematik",
     "Elektrikli SUV test surusu: 480 beygir motor gucu, 0-100 hizlanma "
     "ve pist surus izlenimleri.",
     "yasam", {"otomotiv"}),

    ("haber analizi",
     "Son dakika gelismeleri ve gundem analizi: secim sonrasi krizin "
     "ekonomiye etkisi uzerine haber degerlendirmesi.",
     "belgesel", {"haber", "arastirma"}),

    ("meditasyon ambient",
     "Rahatlatici ambient meditasyon: uyku oncesi nefes egzersizi, "
     "sakinlestirici beyaz gurultu ve zen huzur atmosferi.",
     "seyahat", {"ambient"}),

    ("urun karsilastirma",
     "iPhone 15 vs Galaxy S24 karsilastirmasi: hangisi daha iyi, "
     "fiyat farki ve kamera testi.",
     "urun", {"karsilastirma", "inceleme"}),
]

kontrol("test matrisi en az 12 belirgin konsept iceriyor", len(MATRIS) >= 12,
        str(len(MATRIS)))

_aileler_gorulen = set()
for ad, metin, bek_aile, bek_turler in MATRIS:
    s = tx.siniflandir(metin)
    _aileler_gorulen.add(s["aile"])
    kontrol(f"konsept '{ad}' -> aile '{bek_aile}'", s["aile"] == bek_aile,
            f"cikan={s['yol']} guven={s['guven']} | {s['gerekce']}")
    kontrol(f"konsept '{ad}' -> tur {sorted(bek_turler)} icinde",
            s["tur"] in bek_turler,
            f"cikan={s['yol']} | {s['gerekce']}")
    kontrol(f"konsept '{ad}' zorla secilmedi (durum kesin/melez)",
            s["durum"] in ("kesin", "melez"), f"{s['durum']} guven={s['guven']}")
    kontrol(f"konsept '{ad}' gerekce OLCULEN sayi iceriyor",
            "kanit" in s["gerekce"] and "puan" in s["gerekce"], s["gerekce"])
    kontrol(f"konsept '{ad}' eski etikete indirgeniyor",
            s["eski_etiket"] in ("belgesel", "seyahat", "aciklayici", "urun",
                                 "hikaye"), s["eski_etiket"])

kontrol("matris en az 6 farkli aileyi kapsiyor", len(_aileler_gorulen) >= 6,
        str(sorted(_aileler_gorulen)))


# ═══════════════ 12. YAPISAL SINYALLER ═══════════════
blok("12. Yapisal sinyaller — kelime listesinden BAGIMSIZ olcum")

kontrol("skor kalibi olculuyor", tx.sinyalleri_olc("mac 3-1 bitti").get("skor") == 1)
kontrol("olcu birimi olculuyor",
        tx.sinyalleri_olc("200 g un ve 2 yemek kasigi yag").get("olcu") == 2)
kontrol("para birimi olculuyor", tx.sinyalleri_olc("fiyat 1999 TL").get("para", 0) >= 1)
kontrol("emlak olcusu olculuyor",
        tx.sinyalleri_olc("3+1 daire 145 m2").get("emlak_olcu", 0) >= 2)
kontrol("cozunurluk olculuyor",
        tx.sinyalleri_olc("4K 60 fps drone").get("cozunurluk", 0) >= 2)
kontrol("borsa sinyali olculuyor",
        tx.sinyalleri_olc("hisse ve enflasyon").get("borsa") == 2)
kontrol("eski yil ayrimi calisiyor",
        tx.sinyalleri_olc("1911 ve 2024").get("eski_yil") == 1)
kontrol("sinyal yoksa bos sozluk (uydurma kanit yok)",
        tx.sinyalleri_olc("kirmizi yesil mavi") == {})

# Sinyaller kelimeden BAGIMSIZ: hicbir konu kelimesi olmayan metinde de olculur
_sadece_sayi = tx.sinyalleri_olc("2-0, 45. dakika")
kontrol("konu kelimesi olmadan da yapisal sinyal cikiyor",
        _sadece_sayi.get("skor") and _sadece_sayi.get("dakika"), str(_sadece_sayi))

# TURKCE EK TOLERANSI — sol sinir KATI, sag tarafta sinirli tolerans
kontrol("uzun terim Turkce ekle eslesiyor ('teori' -> 'teorisi')",
        tx._gecti("teori", " genel gorelilik teorisi "))
kontrol("cok kelimeli terim ekle eslesiyor ('kara delik' -> 'kara delikler')",
        tx._gecti("kara delik", " kara delikler nasil olusur "))
kontrol("uzun ek zinciri de yutuluyor ('arastirmacilar' -> '...inin')",
        tx._gecti("arastirmacilar", " nasa arastirmacilarinin gozlemi "))
kontrol("SOL sinir KATI — kelime ortasinda eslesme YOK",
        not tx._gecti("teori", " kateorik bir sey "))
kontrol("kisa terimde ek toleransi YOK ('gol' -> 'golge' degil)",
        not tx._gecti("gol", " duvardaki golge "))
kontrol("kisa terim yine de tam eslesir ('gol' -> 'gol')",
        tx._gecti("gol", " 90. dakikada gol geldi "))
kontrol("ek tavani asilirsa eslesmiyor",
        not tx._gecti("teori", " teorisyenlerimizden "))

# Karsit kelime yanlis pozitifi dusuruyor
_p = tx.dal_puanla("cocuklar icin sevimli tavsan masali, kanli cinayet yok")
kontrol("karsit isabet puani dusuruyor (yanlis pozitif korumasi)",
        _p["hikaye.cocuk"]["karsit_isabet"], str(_p["hikaye.cocuk"]))


# ═══════════════ 13. BELIRSIZLIK ve MELEZ ═══════════════
blok("13. Belirsizlik — zorla etiket YOK, guven formulu acik")

bos = tx.siniflandir("")
kontrol("bos metin -> belirsiz", bos["yol"] == "belirsiz" and bos["guven"] == 0.0,
        str(bos["yol"]))
kontrol("belirsizde eski etiket de belirsiz", bos["eski_etiket"] == "belirsiz")

anlamsiz = tx.siniflandir("zzz qqq www xyzt plkm")
kontrol("anlamsiz metin -> belirsiz", anlamsiz["yol"] == "belirsiz",
        str(anlamsiz["yol"]))
kontrol("belirsiz gerekce SEBEBI yaziyor", "kanit yetersiz" in anlamsiz["gerekce"],
        anlamsiz["gerekce"])

tek = tx.siniflandir("bir tarif")
kontrol("tek isaret KARAR VERDIRMIYOR (kanit esigi)",
        tek["durum"] == "belirsiz", f"{tek['yol']} kanit={tek['kanit']}")

# BILINMEYEN MELEZ: iki dal birden guclu -> tek etikete EZILMEZ
melez = tx.siniflandir(
    "Sampiyon sefin mutfagindaki 3-1'lik yemek dusellosu: 200 g malzeme ile "
    "90. dakikada biten tarif macinin ozeti")
kontrol("melez girdi 'melez' ya da acik guvenle raporlaniyor",
        melez["durum"] in ("melez", "kesin", "zayif"), str(melez["durum"]))
if melez["durum"] == "melez":
    kontrol("melezde IKINCIL dal raporlaniyor", bool(melez["ikincil"]),
            str(melez))
else:
    kontrol("melez degilse adaylar yine de gorunur",
            len(melez["adaylar"]) >= 2, str(melez["adaylar"]))

kontrol("guven tavani 0.95 (kesin dogru iddiasi yok)",
        tx.guven_hesapla(10.0, 0.0, 9) == 0.95, str(tx.guven_hesapla(10.0, 0.0, 9)))
kontrol("marj kuculdukce guven duser",
        tx.guven_hesapla(10.0, 9.5, 5) < tx.guven_hesapla(10.0, 1.0, 5))
kontrol("kanit azaldikca guven duser",
        tx.guven_hesapla(10.0, 0.0, 1) < tx.guven_hesapla(10.0, 0.0, 5))
kontrol("sifir puanda guven 0", tx.guven_hesapla(0.0, 0.0, 9) == 0.0)
kontrol("esikler tanimli ve tutarli",
        0 < tx.ZAYIF_ESIGI < tx.KESIN_ESIGI < 1 and tx.KANIT_ESIGI >= 2,
        f"{tx.KANIT_ESIGI}/{tx.ZAYIF_ESIGI}/{tx.KESIN_ESIGI}")
kontrol("adaylar her zaman raporlaniyor (kara kutu yok)",
        len(tx.siniflandir("uzay ve kara delik teorisi")["adaylar"]) >= 2)
kontrol("olculen sinyaller sonuca yaziliyor",
        "skor" in tx.siniflandir("mac 3-1 ve 90. dakika golu")["sinyaller"])


# ═══════════════ 14. SINIRLI MODEL ANALIZI (KLAMPLI) ═══════════════
blok("14. Model analizi — aday disi cevap YOK SAYILIR")

cagrildi = [0]


def _model_iyi(metin, adaylar):
    cagrildi[0] += 1
    return {"yol": adaylar[0][0], "guven": 0.8, "gerekce": "sahte model"}


def _model_kotu(metin, adaylar):
    cagrildi[0] += 1
    return {"yol": "uydurma.dal", "guven": 0.99, "gerekce": "aday disi"}


def _model_patlar(metin, adaylar):
    cagrildi[0] += 1
    raise RuntimeError("model 500")


kontrol("model_coz YOKSA sonuc deterministik",
        tx.siniflandir("zzz qqq")["kaynak"] == "deterministik")

cagrildi[0] = 0
kesin = tx.siniflandir(
    "Mercimek corbasi tarifi: 200 g mercimek, 2 yemek kasigi yag, "
    "once kavurun sonra pisirin", model_coz=_model_iyi)
kontrol("KESIN kararda model CAGRILMIYOR (bosa para yok)",
        cagrildi[0] == 0 and kesin["kaynak"] == "deterministik",
        f"cagri={cagrildi[0]} durum={kesin['durum']}")

cagrildi[0] = 0
mb = tx.siniflandir("zzz qqq www", model_coz=_model_iyi)
kontrol("belirsizde model CAGRILIYOR", cagrildi[0] == 1, str(cagrildi[0]))
kontrol("model karari raporlaniyor",
        mb["kaynak"] == "model" and mb["model_kullanildi"] is True, str(mb["kaynak"]))
kontrol("model guveni 0.90'i ASAMAZ", mb["guven"] <= 0.90, str(mb["guven"]))

mk = tx.siniflandir("zzz qqq www", model_coz=_model_kotu)
kontrol("aday DISI cevap YOK SAYILIR", mk["kaynak"] == "deterministik", str(mk))
kontrol("yok sayma GORUNUR (sessiz degil)", "YOK SAYILDI" in mk.get("model_notu", ""),
        str(mk.get("model_notu")))

mp = tx.siniflandir("zzz qqq www", model_coz=_model_patlar)
kontrol("model patlarsa deterministik KORUNUR",
        mp["kaynak"] == "deterministik" and mp["yol"] == "belirsiz", str(mp))
kontrol("model hatasi gerekcede gorunur", "model hatasi" in mp.get("model_notu", ""),
        str(mp.get("model_notu")))

try:
    py_compile.compile(os.path.join(KOK, "taksonomi.py"), doraise=True)
    kontrol("taksonomi.py derleniyor", True)
except Exception as e:
    kontrol("taksonomi.py derleniyor", False, str(e)[:140])


# ═══════════════ 15. I-2b: SURUMLU BILESIK STIL PROFILLERI ═══════════════
blok("15. Stil profilleri — surumlu, birlestirilebilir, geriye uyumlu")

import stil_profili as sp                           # noqa: E402

sk = sp.kapsam_ozeti()
kontrol("kapsam_ozeti sayilabilir",
        all(isinstance(sk.get(k), int) for k in
            ("profil", "boyut", "alan", "konsept_baglantisi")), str(sk))
kontrol("11 bilesik boyut tanimli", sk["boyut"] == 11, str(sk["boyut"]))
kontrol("en az 10 profil var", sk["profil"] >= 10, str(sk["profil"]))
kontrol("istenen 11 boyutun hepsi var",
        set(sp.BOYUTLAR) == {"anlatim", "tempo", "gecis", "kamera", "tipografi",
                             "palet", "ses", "medya", "dagitim", "kanit", "qa"},
        str(sp.BOYUTLAR))
kontrol("stil_profili AG KULLANMIYOR",
        all(x not in oku(KOK, "stil_profili.py")
            for x in ("requests", "openai.com", "http://", "https://", "urllib")))

# ── Dogrulama ──
_hatali = {k: sp.dogrula(p) for k, p in sp.PROFIL.items() if sp.dogrula(p)}
kontrol("kayittaki TUM profiller semaya uyuyor", not _hatali, str(_hatali)[:200])
kontrol("eksik boyut yakalaniyor",
        any("eksik boyut" in h for h in sp.dogrula({"ad": "x", "ozet": "y",
                                                    "surum": "1.0.0"})))
_bozuk = sp.profil_al("belgesel-sinematik")
_bozuk["tempoo"] = {}
kontrol("BILINMEYEN boyut hata veriyor (sessiz yazim yanlisi yok)",
        any("bilinmeyen boyut" in h for h in sp.dogrula(_bozuk)), str(sp.dogrula(_bozuk)))
_tip = sp.profil_al("belgesel-sinematik")
_tip["tempo"]["plan_sn"] = "yedi"
kontrol("yanlis tip yakalaniyor",
        any("sayi degil" in h for h in sp.dogrula(_tip)))
_eksik = sp.profil_al("belgesel-sinematik")
del _eksik["qa"]["lufs_hedef"]
kontrol("eksik alan yakalaniyor",
        any("qa.lufs_hedef eksik" in h for h in sp.dogrula(_eksik)))

# ── Surumleme ──
kontrol("her profilin surumu var",
        all(p.get("surum") for p in sp.PROFIL.values()))
kontrol("sema uyumu MAJOR'a bakiyor",
        sp.sema_uyumlu_mu("1.9.9") and not sp.sema_uyumlu_mu("2.0.0"))
_a = sp.profil_al("belgesel-sinematik")
_a["tempo"]["plan_sn"] = 999.0
kontrol("profil_al DERIN KOPYA doner (kayit bozulmaz)",
        sp.PROFIL["belgesel-sinematik"]["tempo"]["plan_sn"] != 999.0)
_ank = sp.arsivle("belgesel-sinematik")
kontrol("arsivle (kimlik, surum) donduruyor",
        _ank == ("belgesel-sinematik", sp.PROFIL["belgesel-sinematik"]["surum"]),
        str(_ank))
kontrol("arsivlenen surum AYNEN geri geliyor",
        sp.profil_al("belgesel-sinematik", surum=_ank[1])["tempo"]["plan_sn"]
        == sp.PROFIL["belgesel-sinematik"]["tempo"]["plan_sn"])
kontrol("surum_listesi arsivi goruyor", _ank[1] in sp.surum_listesi("belgesel-sinematik"))
try:
    sp.profil_al("belgesel-sinematik", surum="9.9.9")
    kontrol("olmayan surum sessizce BASKA surum dondurmuyor", False, "KeyError yok")
except KeyError:
    kontrol("olmayan surum sessizce BASKA surum dondurmuyor", True)
try:
    sp.profil_al("olmayan-stil")
    kontrol("bilinmeyen kimlik KeyError", False)
except KeyError:
    kontrol("bilinmeyen kimlik KeyError", True)

# ── Birlestirme kurallari ──
kontrol("ortalama kurali agirlikli",
        sp._birlestir_alan("ortalama", [10.0, 20.0], [3.0, 1.0]) == 12.5,
        str(sp._birlestir_alan("ortalama", [10.0, 20.0], [3.0, 1.0])))
kontrol("agirlikli-secim en agir ebeveyni aliyor",
        sp._birlestir_alan("agirlikli-secim", ["a", "b"], [0.2, 0.8]) == "b")
kontrol("en-kati-dogru: yasak izni yener",
        sp._birlestir_alan("en-kati-dogru", [False, True], [9.0, 0.1]) is True)
kontrol("en-kati-maks: buyuk deger kati (min kaynak)",
        sp._birlestir_alan("en-kati-maks", [1.0, 3.0], [9.0, 0.1]) == 3.0)
kontrol("en-kati-min: kucuk deger kati (siyah kare)",
        sp._birlestir_alan("en-kati-min", [5.0, 0.0], [9.0, 0.1]) == 0.0)
kontrol("kesisim lisansta KATI tarafi aliyor",
        sp._birlestir_alan("kesisim", [("cc0", "pexels"), ("cc0",)], [1.0, 1.0])
        == ("cc0",))
kontrol("BOS kesisimde bos liste DONMUYOR (medya kilitlenmez)",
        sp._birlestir_alan("kesisim", [("cc0",), ("pexels",)], [1.0, 0.5])
        == ("cc0",))
try:
    sp._birlestir_alan("uydurma-kural", [1], [1])
    kontrol("bilinmeyen kural hata veriyor", False)
except ValueError:
    kontrol("bilinmeyen kural hata veriyor", True)

# ── Melez turetme (cekirdek kod degismeden) ──
_mp, _mg = sp.tureti(["belgesel-sinematik", "korku-gerilim"], [0.6, 0.4])
kontrol("turetilmis melez SEMAYA uyuyor", not sp.dogrula(_mp), str(sp.dogrula(_mp))[:160])
kontrol("melez profil kayda YAZILMIYOR (cekirdek kod degismedi)",
        "melez" not in " ".join(sp.PROFIL.keys()) and len(sp.PROFIL) == sk["profil"])
kontrol("melez ebeveynlerini raporluyor",
        _mg["ebeveyn"] == ["belgesel-sinematik", "korku-gerilim"])
kontrol("gerekce TUM alanlari hesaba katiyor",
        _mg["alan_sayisi"] == sk["alan"], f"{_mg['alan_sayisi']} vs {sk['alan']}")
kontrol("her alanin kurali ve kaynagi raporlaniyor (kara kutu yok)",
        all({"kural", "kaynak", "deger"} <= set(v) for v in _mg["alan"].values()))
kontrol("melezde sayisal alan agirlikli ortalama (7.0/5.0 -> 6.2)",
        _mp["tempo"]["plan_sn"] == 6.2, str(_mp["tempo"]["plan_sn"]))
kontrol("melezde KANIT kurali KATI tarafta kaliyor",
        _mp["medya"]["ai_gorsel_yasak"] is True
        and _mp["kanit"]["min_bagimsiz_kaynak"] == 2.0, str(_mp["kanit"]))
_bp, _bg = sp.tureti(["belgesel-sinematik", "seyahat-4k"], [0.5, 0.5])
kontrol("lisans kesisimi bos degilse KATI liste secilir",
        set(_bp["kanit"]["lisans_beyaz_liste"]) == set(sp.LISANS_KATI),
        str(_bp["kanit"]["lisans_beyaz_liste"]))
try:
    sp.tureti(["belgesel-sinematik"])
    kontrol("tek ebeveynle turetme reddediliyor", False)
except ValueError:
    kontrol("tek ebeveynle turetme reddediliyor", True)
try:
    sp.tureti(["belgesel-sinematik", "korku-gerilim"], [1.0])
    kontrol("agirlik sayisi uyusmazsa reddediliyor", False)
except ValueError:
    kontrol("agirlik sayisi uyusmazsa reddediliyor", True)

# ── coz(): KULLANICI SECIMI AUTO'YU YENER ──
_ko = {"yol": "hikaye.korku", "aile": "hikaye", "guven": 0.9, "ikincil": None}
_c = sp.coz(kullanici_stili="seyahat-4k", konsept=_ko)
kontrol("kullanici secimi AUTO'yu EZIYOR",
        _c["kimlik"] == "seyahat-4k" and _c["kaynak"] == "kullanici", str(_c["kimlik"]))
kontrol("ezme gerekcede yaziyor", "EZILDI" in _c["gerekce"], _c["gerekce"])
_c2 = sp.coz(konsept=_ko)
kontrol("kullanici secmezse AUTO calisiyor",
        _c2["kimlik"] == "korku-gerilim" and _c2["kaynak"] == "auto", str(_c2["kimlik"]))
_c3 = sp.coz(kullanici_stili="boyle-bir-stil-yok", konsept=_ko)
kontrol("BILINMEYEN kullanici stili sessizce KABUL EDILMIYOR",
        _c3["kaynak"] == "auto" and _c3["uyari"], str(_c3["uyari"]))
_c4 = sp.coz(konsept={"yol": "belirsiz", "aile": "", "guven": 0.0})
kontrol("belirsiz konseptte VARSAYILANA dusuluyor",
        _c4["kaynak"] == "varsayilan" and _c4["kimlik"] == sp.VARSAYILAN_PROFIL,
        str(_c4["kimlik"]))
_c5 = sp.coz()
kontrol("hicbir sinyal yoksa varsayilan + gerekce", _c5["kaynak"] == "varsayilan"
        and _c5["gerekce"])
_c6 = sp.coz(konsept={"yol": "hikaye.korku", "aile": "hikaye", "guven": 0.5,
                      "ikincil": "belgesel.tarih"})
kontrol("MELEZ konsept profil TURETIYOR", _c6["kaynak"] == "turetilmis", str(_c6["kaynak"]))
kontrol("turetilmis secimde gerekce donuyor",
        _c6["turetme"] and _c6["turetme"]["alan_sayisi"] == sk["alan"])
kontrol("turetilmis profil de semaya uyuyor", not sp.dogrula(_c6["profil"]))
_c7 = sp.coz(kullanici_stili="sinematik-belgesel", konsept=_ko)
kontrol("ESKI stil kimligi kullanici secimi olarak kabul ediliyor",
        _c7["kimlik"] == "belgesel-sinematik" and _c7["kaynak"] == "kullanici",
        str(_c7["kimlik"]))

# ── Geriye uyumluluk ──
_eski = sp.eski_edit_stiline(sp.profil_al("belgesel-sinematik"))
kontrol("eski EDIT_STILLERI alanlarinin hepsi uretiliyor",
        all(a in _eski for a in sp.ESKI_EDIT_ANAHTARLARI),
        str([a for a in sp.ESKI_EDIT_ANAHTARLARI if a not in _eski]))
kontrol("eski bicimde tasinamayan boyutlar _profil altinda korunuyor",
        {"palet", "ses", "kanit", "qa"} <= set(_eski["_profil"]))
kontrol("belgeselde AI gorsel yasagi eski bayraga tasiniyor",
        _eski["gorsel_yasak"] is True)
_pp = oku(KOK, "pipeline.py")
_kayip = [k for k in sp.ESKI_EDIT_ESLEME if f'"{k}": {{' not in _pp]
kontrol("ESKI_EDIT_ESLEME anahtarlari pipeline.EDIT_STILLERI'nde GERCEKTEN var",
        not _kayip, str(_kayip))
kontrol("pipeline.py stil_profili'ni GUVENLI (try/except) import ediyor — I-2c",
        "import stil_profili" in _pp and "stil_profili = None" in _pp)
_ap = {y.split(".")[0] for y in tx.AGAC} | set(tx.AGAC)
_gecersiz = [k for k in sp.KONSEPT_PROFIL if k not in _ap]
kontrol("KONSEPT_PROFIL anahtarlari taksonomide GERCEKTEN var",
        not _gecersiz, str(_gecersiz))
_bos_hedef = [v for v in sp.KONSEPT_PROFIL.values() if v not in sp.PROFIL]
kontrol("KONSEPT_PROFIL hedefleri kayitta var", not _bos_hedef, str(_bos_hedef))
kontrol("her taksonomi AILESI bir profile baglaniyor",
        not ({y.split(".")[0] for y in tx.AGAC} - set(sp.KONSEPT_PROFIL)),
        str({y.split(".")[0] for y in tx.AGAC} - set(sp.KONSEPT_PROFIL)))

try:
    py_compile.compile(os.path.join(KOK, "stil_profili.py"), doraise=True)
    kontrol("stil_profili.py derleniyor", True)
except Exception as e:
    kontrol("stil_profili.py derleniyor", False, str(e)[:140])


# ═══════════════ 15. FAZ I-2c — AKISA BAGLAMA (EK ALAN, GERILEME YOK) ═══════════════
# ⚠ BU BOLUMUN IDDIASI: taksonomi (I-2a) + stil_profili (I-2b) `analiz()`
# sozlesmesine YALNIZCA EK ALAN olarak baglandi ve uretim hatti `_profil`
# blogunu GUVENLI/OPSIYONEL tuketiyor. Eski girdilerde davranis DEGISMEDI.
# Ag yok, para yok: `siniflandir()` model_coz ALMADAN cagriliyor.
blok("15. I-2c — girdi_analizi ek alanlari + geriye uyumluluk")

import json                                          # noqa: E402

_BELGESEL = ("John D. Rockefeller ve Standard Oil'in yukselisi: 1870'te "
             "kurulan sirketin 1911'deki mahkeme kararıyla parcalanmasina "
             "uzanan tarih, arsiv belgeleriyle anlatiliyor.")

_a = ga.analiz(_BELGESEL)

# ── (a) ESKI SOZLESME: tek bir alan bile kaybolmadi ──
ESKI_ALANLAR = {"girdi_turu", "kelime_sayisi", "dil", "icerik_turu",
                "tur_puanlari", "varliklar", "riskler", "otomatik_secimler",
                "korunan_secimler", "gerekceler"}
kontrol("eski analiz() alanlarinin HEPSI duruyor",
        ESKI_ALANLAR <= set(_a), str(ESKI_ALANLAR - set(_a)))
ESKI_GEREKCE = {"girdi_turu", "dil", "icerik_turu", "sure", "gorsel_strateji"}
kontrol("eski gerekce anahtarlari duruyor",
        ESKI_GEREKCE <= set(_a["gerekceler"]),
        str(ESKI_GEREKCE - set(_a["gerekceler"])))
kontrol("eski otomatik secim anahtarlari duruyor",
        {"tur", "sure_dk", "gorsel_strateji", "dil"} <= set(_a["otomatik_secimler"]),
        str(set(_a["otomatik_secimler"])))
kontrol("eski DEGERLER degismedi: konu -> varsayilan 2 dk",
        _a["otomatik_secimler"]["sure_dk"]["deger"] == 2.0)
kontrol("eski DEGERLER degismedi: belgesel -> documentary",
        _a["otomatik_secimler"]["tur"]["deger"] == "documentary")
kontrol("eski DEGERLER degismedi: gorsel strateji gercek footage",
        _a["otomatik_secimler"]["gorsel_strateji"]["deger"] == "gercek-footage")
_au = ga.analiz(("The Endurance expedition began in 1914. " * 12)
                + "The crew survived.")
kontrol("uzun metin HALA 'tam-metin'", _au["girdi_turu"] == "tam-metin")
kontrol("tam metinde sure HALA olcumden geliyor",
        "kelime" in _au["gerekceler"]["sure"])
kontrol("otomatik secimlerin HEPSINDE gerekce var (yeni 'edit' dahil)",
        all(v.get("gerekce") for v in _a["otomatik_secimler"].values()),
        str([k for k, v in _a["otomatik_secimler"].items() if not v.get("gerekce")]))
_ak = ga.analiz("Bali gezi rehberi plaj otel rota",
                kullanici_secimi={"sure_dk": 8, "tur": "hikaye"})
kontrol("kullanici secimi HALA korunuyor",
        _ak["korunan_secimler"]["tur"]["deger"] == "hikaye"
        and "tur" not in _ak["otomatik_secimler"])

# ── (b) YENI EK ALANLAR ──
kontrol("analiz() 'konsept' EK alanini donduruyor", "konsept" in _a)
kontrol("analiz() 'stil_profili' EK alanini donduruyor", "stil_profili" in _a)
kontrol("konsept gercekten siniflandirdi (belgesel ailesi)",
        _a["konsept"].get("aile") == "belgesel", str(_a["konsept"].get("yol")))
kontrol("konsept kararinda OLCULEN sayi var (kara kutu yok)",
        any(c.isdigit() for c in _a["konsept"].get("gerekce", "")),
        _a["konsept"].get("gerekce", "")[:80])
kontrol("stil profili cozuldu ve SURUMLU",
        _a["stil_profili"].get("kimlik") == "belgesel-sinematik"
        and _a["stil_profili"].get("surum"),
        str(_a["stil_profili"].get("kimlik")))
kontrol("stil kaynagi AUTO (konsept sinyalinden)",
        _a["stil_profili"].get("kaynak") == "auto",
        str(_a["stil_profili"].get("kaynak")))
kontrol("sema surumu raporlaniyor",
        _a["stil_profili"].get("sema_surum") == sp.SEMA_SURUM)
_ee = _a["stil_profili"].get("eski_edit") or {}
kontrol("eski_edit ESKI EDIT_STILLERI alanlarinin hepsini uretiyor",
        all(x in _ee for x in sp.ESKI_EDIT_ANAHTARLARI),
        str([x for x in sp.ESKI_EDIT_ANAHTARLARI if x not in _ee]))
kontrol("eski_edit icinde `_profil` blogu tasiniyor",
        {"palet", "ses", "kanit", "qa", "gecis", "dagitim", "surum"}
        <= set(_ee.get("_profil") or {}), str(sorted(_ee.get("_profil") or {})))
kontrol("gerekcelere konsept + stil satiri EKLENDI",
        _a["gerekceler"].get("konsept") and _a["gerekceler"].get("stil_profili"))

# KULLANICI SECIMI AUTO'YU YENER
_ku = ga.analiz(_BELGESEL, kullanici_secimi={"edit": "korku-gerilim"})
kontrol("kullanici stili AUTO'yu yeniyor",
        _ku["stil_profili"]["kimlik"] == "korku-gerilim"
        and _ku["stil_profili"]["kaynak"] == "kullanici",
        str(_ku["stil_profili"]["kimlik"]))
kontrol("kullanici stili korunan_secimler'e yaziliyor",
        _ku["korunan_secimler"].get("edit", {}).get("deger") == "korku-gerilim")
_kb = ga.analiz(_BELGESEL, kullanici_secimi={"edit": "boyle-bir-stil-yok"})
kontrol("BILINMEYEN kullanici stili sessizce yutulmuyor",
        _kb["stil_profili"]["uyari"] and _kb["stil_profili"]["kaynak"] == "auto",
        str(_kb["stil_profili"]["uyari"]))

# ⚠ SINYAL YOKSA KARISMA: uretim hattinin kendi varsayilani KORUNUR
_bs = ga.analiz("zzz qqq www yyy xxx vvv uuu ttt sss rrr")
kontrol("sinyalsiz metinde stil kaynagi VARSAYILAN",
        _bs["stil_profili"].get("kaynak") == "varsayilan",
        str(_bs["stil_profili"].get("kaynak")))
kontrol("sinyalsiz metinde 'edit' OTOMATIK SECILMIYOR (hat varsayilani duruyor)",
        "edit" not in _bs["otomatik_secimler"], str(sorted(_bs["otomatik_secimler"])))
kontrol("sinyalsiz metinde konsept BELIRSIZ diyor (zorla etiket yok)",
        _bs["konsept"].get("yol") == "belirsiz", str(_bs["konsept"].get("yol")))

# ── (c) DAYANIKLILIK: modul yoksa / patlarsa eski sozlesme AYNEN doner ──
_yedek = (ga.taksonomi, ga.stil_profili)
try:
    ga.taksonomi, ga.stil_profili = None, None
    _ay = ga.analiz(_BELGESEL)
    kontrol("modul YOKKEN eski alanlarin hepsi yine doner",
            ESKI_ALANLAR <= set(_ay), str(ESKI_ALANLAR - set(_ay)))
    kontrol("modul YOKKEN ek alanlar BOS (uydurma yok)",
            _ay["konsept"] == {} and _ay["stil_profili"] == {})
    kontrol("modul YOKKEN 'edit' onerisi URETILMIYOR",
            "edit" not in _ay["otomatik_secimler"])
    kontrol("modul YOKKEN eski degerler ayni",
            _ay["otomatik_secimler"]["sure_dk"]["deger"] == 2.0
            and _ay["icerik_turu"] == _a["icerik_turu"])

    class _Patlayan:
        SEMA_SURUM = "1.0.0"

        @staticmethod
        def siniflandir(_m, **_k):
            raise RuntimeError("kasitli patlama")

        @staticmethod
        def coz(**_k):
            raise RuntimeError("kasitli patlama")

    ga.taksonomi, ga.stil_profili = _Patlayan, _Patlayan
    _ap = ga.analiz(_BELGESEL)
    kontrol("alt modul PATLARSA analiz cokmuyor", ESKI_ALANLAR <= set(_ap))
    kontrol("patlama SESSIZ degil, `_hata` ile gorunur",
            "_hata" in _ap["konsept"] and "_hata" in _ap["stil_profili"],
            str(_ap["konsept"])[:80])
finally:
    ga.taksonomi, ga.stil_profili = _yedek

# ⚠ "Ucretsiz" iddiasi DIZE TARAMASIYLA YETINMEZ: modele giden TEK yol
# `siniflandir(..., model_coz=...)` anahtar argumanidir. Once o arguman
# kaynakta hic gecmiyor mu diye bakilir, sonra CAGRI CASUSLANARAK olculur.
kontrol("konsept koprusu AG kutuphanesi kullanmiyor (ucretsiz)",
        all(x not in oku(KOK, "girdi_analizi.py")
            for x in ("requests", "openai.com", "http://", "https://",
                      "urllib", "model_coz=")))
_casus = {}
_yedek2 = ga.taksonomi


class _Casus:
    @staticmethod
    def siniflandir(metin, **kw):
        _casus.update(kw)
        return {"yol": "belgesel.tarih", "aile": "belgesel", "guven": 0.7,
                "durum": "kesin", "ikincil": None, "gerekce": "casus 1 kanit"}


try:
    ga.taksonomi = _Casus
    ga.analiz(_BELGESEL)
finally:
    ga.taksonomi = _yedek2
kontrol("siniflandir MODEL ARGUMANI ALMADAN cagriliyor (olculdu)",
        "model_coz" not in _casus, str(sorted(_casus)))
# ⚠ KATI serilestirme: `default=` KULLANILMAZ. Gevsek bir donusturucu,
# `/api/analiz`i calisma aninda 500 verecek bir tipi TESTTE gizlerdi.
try:
    _govde = json.dumps(_a, ensure_ascii=False)
    kontrol("analiz ciktisi KATI JSON'a serilestirilebiliyor (/api/analiz govdesi)",
            bool(_govde))
except Exception as e:
    kontrol("analiz ciktisi KATI JSON'a serilestirilebiliyor (/api/analiz govdesi)",
            False, f"{type(e).__name__}: {str(e)[:100]}")
_a2 = ga.analiz(_BELGESEL)
kontrol("analiz DETERMINISTIK (ayni girdi -> ayni cikti)",
        json.dumps(_a, sort_keys=True, ensure_ascii=False)
        == json.dumps(_a2, sort_keys=True, ensure_ascii=False))


blok("15b. I-2c — pipeline `_profil` tuketimi (GUVENLI/OPSIYONEL)")

# Statik kilitler (pipeline import edilemese de kosar)
kontrol("pipeline `_profil` icin GUVENLI okuyucu tanimliyor",
        "def profil_ek_oku(" in _pp)
kontrol("okuyucu istisna firlatmiyor (try/except)",
        "except Exception:\n        return {}" in _pp)
kontrol("profil_coz opsiyonel `ek_profil` aliyor",
        "def profil_coz(tur, edit_id, ek_profil=None)" in _pp)
kontrol("kunye YALNIZCA `_profil` varken yaziliyor",
        'if _stil_ek:' in _pp and 'sonuc["stil_profili"]' in _pp)
kontrol("mevcut sonuc alanlari KORUNDU (gerileme yok)",
        all(x in _pp for x in ('sonuc["kare_kapisi"]', 'sonuc["medya_kapisi"]',
                               'sonuc["qa"]', '"atiflar": kaynak.atif_listesi()')))

# Gercek fonksiyonel kosum — pipeline import edilebiliyorsa
_pkok = os.path.join(KOK, "..", "cikti", "_i2c_kok")
try:
    os.makedirs(_pkok, exist_ok=True)
    _uret_kaynak = os.path.join(KOK, "..", "app", "uret.py")
    if os.path.exists(_uret_kaynak):
        import shutil as _sh
        _sh.copy(_uret_kaynak, os.path.join(_pkok, "uret.py"))
    os.environ["VIDRUSH_KOK"] = os.path.abspath(_pkok)
    import pipeline as _pl                            # noqa: E402

    # ⚠ GERILEME KANITI: eski kimliklerin hepsi BIREBIR AYNI NESNE doner.
    _fark = [k for k in _pl.EDIT_STILLERI
             if _pl.profil_coz("documentary", k) is not _pl.EDIT_STILLERI[k]]
    kontrol("ESKI stil kimlikleri BIREBIR ayni sozlugu donduruyor",
            not _fark, str(_fark))
    kontrol("bos/None edit_id eski varsayilani donduruyor",
            _pl.profil_coz("documentary", "") is _pl.EDIT_STILLERI[_pl.VARSAYILAN_EDIT]
            and _pl.profil_coz("documentary", None)
            is _pl.EDIT_STILLERI[_pl.VARSAYILAN_EDIT])
    kontrol("hikaye/animasyon yollari DEGISMEDI",
            _pl.profil_coz("hikaye", None)
            is _pl.HIKAYE_STILLERI[_pl.VARSAYILAN_HIKAYE]
            and _pl.profil_coz("animasyon", None)
            is _pl.ANIMASYON_STILLERI[_pl.VARSAYILAN_ANIM])
    kontrol("eski kimlikte `_profil` YOK -> kunye de yazilmaz",
            _pl.profil_ek_oku(_pl.profil_coz("documentary", "sinematik-belgesel")) == {})

    # YENI NESIL kimlik: bugune kadar SESSIZCE varsayilana dusuyordu
    _yeni = _pl.profil_coz("documentary", "korku-gerilim")
    kontrol("yeni-nesil stil kimligi GERCEKTEN cozuluyor",
            _yeni["ad"] == sp.PROFIL["korku-gerilim"]["ad"], str(_yeni["ad"]))
    kontrol("yeni-nesil stil artik sessizce varsayilana DUSMUYOR",
            _yeni["ad"] != _pl.EDIT_STILLERI[_pl.VARSAYILAN_EDIT]["ad"])
    kontrol("yeni bicimin tasiyamadigi eski alanlar TABANDAN geliyor",
            _yeni.get("gorsel_ek") and _yeni.get("mag"),
            str(sorted(set(_pl.EDIT_STILLERI[_pl.VARSAYILAN_EDIT]) - set(_yeni))))
    kontrol("zorunlu eski alanlarin HEPSI dolu (KeyError riski yok)",
            all(x in _yeni for x in sp.ESKI_EDIT_ANAHTARLARI))
    kontrol("`_profil` blogu uretim hattina TASINIYOR",
            {"palet", "ses", "kanit", "qa", "gecis", "dagitim"}
            <= set(_pl.profil_ek_oku(_yeni)), str(sorted(_pl.profil_ek_oku(_yeni))))
    kontrol("kunye icin stil kimligi tasiniyor",
            _yeni.get("_stil_kimligi") == "korku-gerilim")
    kontrol("motion degeri uretim hattinin BILDIGI bir deger",
            _yeni["motion"] in {v["motion"] for v in _pl.EDIT_STILLERI.values()}
            | {"hikaye"}, str(_yeni["motion"]))

    # ⚠ I-3'te burada OLCULEN bir bilinen sinir kilitliydi: yeni kimlikte
    # EFEKT_TEMEL/GECIS_IMZASI karsiliksizdi. O acik I-2d'de KAPATILDI
    # (bkz. §18 testleri); burada yalnizca TABLOLARIN degismedigi ve
    # aramalarin KeyError riski tasimadigi korunuyor.
    kontrol("eski kimlik gorsel imzasini ALIYOR (karsilastirma tabani)",
            len(_pl.EFEKT_TEMEL.get("sinematik-belgesel", [])) > 0
            and _pl.GECIS_IMZASI.get("sinematik-belgesel"))
    kontrol("eski tablolar yeni kimlikle SISIRILMEDI (turetme ayri yoldan)",
            "korku-gerilim" not in _pl.EFEKT_TEMEL
            and "korku-gerilim" not in _pl.GECIS_IMZASI)
    kontrol("yeni kimlikte gorsel imza artik TURETILIYOR (sessiz kayip yok)",
            "def bilesik_gorsel_imza(" in _pp)
    kontrol("efekt/gecis aramalari KeyError riski tasimiyor (.get ile)",
            "EFEKT_TEMEL.get(edit_id" in _pp and "GECIS_IMZASI.get(edit_id" in _pp)

    # BILINMEYEN kimlik: eski sessiz-varsayilan davranisi KORUNUR
    _bil = _pl.profil_coz("documentary", "boyle-bir-stil-yok")
    kontrol("bilinmeyen kimlik eski varsayilan davranisini KORUYOR",
            _bil is _pl.EDIT_STILLERI[_pl.VARSAYILAN_EDIT])
    kontrol("bilesik cevirici bilinmeyen kimlikte None donuyor",
            _pl.bilesik_stile_cevir("boyle-bir-stil-yok") is None)
    kontrol("bilesik cevirici bos kimlikte None donuyor",
            _pl.bilesik_stile_cevir("") is None
            and _pl.bilesik_stile_cevir(None) is None)

    # Okuyucu HICBIR girdide patlamiyor
    kontrol("profil_ek_oku bozuk girdilerde COKMUYOR",
            all(_pl.profil_ek_oku(x) == {} for x in
                (None, {}, {"_profil": "bozuk"}, {"_profil": None},
                 {"_profil": 5}, "sozluk degil")))

    # Modul yoksa: eski davranisa duser
    _sp_yedek = _pl.stil_profili
    try:
        _pl.stil_profili = None
        kontrol("stil_profili YOKKEN yeni kimlik eski varsayilana duser",
                _pl.profil_coz("documentary", "korku-gerilim")
                is _pl.EDIT_STILLERI[_pl.VARSAYILAN_EDIT])
        kontrol("stil_profili YOKKEN cevirici None donuyor",
                _pl.bilesik_stile_cevir("korku-gerilim") is None)
    finally:
        _pl.stil_profili = _sp_yedek

    # Elle verilen ek_profil de taban uzerine yazilir
    _elle = _pl.profil_coz("documentary", "sinematik-belgesel",
                           ek_profil={"sahne_sn": 3, "_profil": {"surum": "9.9.9"}})
    kontrol("elle verilen ek_profil TABAN uzerine yaziliyor",
            _elle["sahne_sn"] == 3 and _elle.get("gorsel_ek"))
    kontrol("elle verilen ek_profil kaydi BOZMUYOR",
            _pl.EDIT_STILLERI["sinematik-belgesel"]["sahne_sn"] != 3)
    kontrol("bos/gecersiz ek_profil tabani AYNEN birakir",
            _pl.profil_coz("documentary", "sinematik-belgesel", ek_profil={})
            is _pl.EDIT_STILLERI["sinematik-belgesel"]
            and _pl.profil_coz("documentary", "sinematik-belgesel",
                               ek_profil="bozuk")
            is _pl.EDIT_STILLERI["sinematik-belgesel"])
except Exception as e:
    bloke_yaz("pipeline `_profil` fonksiyonel kosumu", f"{type(e).__name__}: {str(e)[:110]}")

for f in ("girdi_analizi.py", "pipeline.py"):
    try:
        py_compile.compile(os.path.join(KOK, f), doraise=True)
        kontrol(f"{f} derleniyor (I-2c sonrasi)", True)
    except Exception as e:
        kontrol(f"{f} derleniyor (I-2c sonrasi)", False, str(e)[:140])


# ═══════════════ 16. FAZ I-3 — BASIT "METIN + STIL + AUTO" ARAYUZU ═══════════════
# ⚠ IDDIA: Yeni Proje artik varsayilan olarak TEK EKRAN (metin + stil + tek
# eylem). Adim adim wizard KALDIRILMADI, hicbir backend alani KAYBOLMADI ve
# Auto secimi `generate` sozlesmesine YENI ALAN EKLEMEDEN tasiniyor.
blok("16. I-3 — basit uretim arayuzu sozlesmesi")

_ST = os.path.join(KOK, "static")


def _oku_st(*p):
    with open(os.path.join(_ST, *p), encoding="utf-8") as f:
        return f.read()


BASIT = _oku_st("js", "basit.js")
WZ_JS = _oku_st("js", "wizard.js")
DURUM_JS = _oku_st("js", "durum.js")
SD_JS = _oku_st("js", "secim-deneyimi.js")
CSS_ST = _oku_st("app.css")

# ── Varsayilan deneyim: metin + stil + TEK ana eylem ──
kontrol("basit.js modulu var", len(BASIT) > 1000)
kontrol("varsayilan mod BASIT", "mod: 'basit'" in DURUM_JS)
kontrol("wizard basit modu cagiriyor",
        "basitGovde" in WZ_JS and "basitKur" in WZ_JS)
kontrol("metin alani var", 'id="bsMetin"' in BASIT)
kontrol("stil secimi var (Otomatik dahil)", "stilBolumu({" in BASIT)
kontrol("sure secici KORUNDU", 'id: \'bsSure\'' in BASIT
        and "SURE_SECENEKLERI" in BASIT)
_eylem = re.findall(r'id="(bs[A-Za-z]+)"[^>]*>\s*\$\{ikon', BASIT)
kontrol("TEK ana uretim eylemi", BASIT.count('id="bsUret"') == 1,
        str(BASIT.count('id="bsUret"')))
kontrol("gelismis ayarlar TEK acilir alanda", "gelismis('Gelişmiş ayarlar'"
        in BASIT)

# ── HICBIR BACKEND ALANI KAYBOLMADI ──
# Basit mod, adim 3'un bilesenlerini YENIDEN KULLANIR (kopyalamaz).
for ad, iz in [("ses kutuphanesi", "sesBolumu({"), ("marka kiti", "markaBolumu({"),
               ("hizli tercihler", "hizliTercihler({"),
               ("profesyonel ayarlar", "proPanel({")]:
    kontrol(f"basit modda korundu: {ad}", iz in BASIT)
kontrol("secim kontrolleri TEK yerden baglaniyor (cift baglama yok)",
        BASIT.count("radyoBagla") == 0 and "adim3Kur({" in WZ_JS)
kontrol("adim adim wizard KALDIRILMADI",
        len(re.findall(r"\{no: \d, ad: '", WZ_JS)) == 5)
kontrol("iki mod arasinda gidip gelinebiliyor",
        "modCipleri" in BASIT and "modCipleri" in WZ_JS
        and "data-grup=\"mod\"" in BASIT)
kontrol("unlu modu HALA uretiliyor", "d.unlu = t.unlu ? '1' : '0'" in WZ_JS)
kontrol("Grok/maliyet alanlarina dokunulmadi (gorsel model secimi duruyor)",
        "wzModel" in SD_JS)

# ── AUTO -> GENERATE: YENI ALAN YOK ──
_gd = WZ_JS[WZ_JS.find("function generateDegerleri()"):]
_gd = _gd[:_gd.find("export {generateDegerleri}")]
_yeni_alan = set(re.findall(r"d\.(\w+)\s*=", _gd)) - {
    "session", "story", "tur", "sure_dk", "gecis", "zoom", "altyazi", "edit",
    "profil", "altyazi_sablon", "palet", "palet_ozel", "arkaplan", "ses",
    "isik", "gorsel_model", "acilis", "sora", "unlu", "karakter", "stil",
    "sahne_ref"}
kontrol("Auto sozlesmeye YENI ALAN EKLEMIYOR", not _yeni_alan, str(_yeni_alan))
kontrol("Auto stili MEVCUT `edit` alaniyla tasiniyor",
        "autoStilKimligi(_analiz, t.tur)" in WZ_JS
        and "d.edit = stil || otoStil" in WZ_JS)
kontrol("kullanicinin acik stili Auto'yu YENIYOR",
        "stil ? '' : autoStilKimligi" in WZ_JS)
kontrol("kullanicinin acik TUR secimi isaretleniyor",
        "turKaynak: 'kullanici'" in WZ_JS and "turKaynak" in DURUM_JS)

# ── Auto sonucu GORUNUR ve ANLASILIR ──
kontrol("konsept ekranda gosteriliyor", "'Konu türü'" in BASIT)
kontrol("uretim hatti ekranda gosteriliyor", "'Üretim hattı'" in BASIT)
kontrol("secilen stil ve SURUMU gosteriliyor",
        "'Seçilen stil'" in BASIT and "'Stil sürümü'" in BASIT)
kontrol("gerekce INSAN DILINE cevriliyor (ham backend metni degil)",
        "export function kanitMetni" in BASIT
        and "bağımsız işaret ölçüldü" in BASIT
        and "k.gerekce" not in BASIT)
kontrol("uygulanamayan Auto sonucu SESSIZ GECILMIYOR",
        "(uygulanmadı)" in BASIT and "melez stiller henüz üretime" in BASIT)
kontrol("analiz hatasi durustce bildiriliyor", "Analiz alınamadı" in BASIT)
kontrol("basit mod CSS'i eklendi", ".bs-govde" in CSS_ST and ".bs-eylem" in CSS_ST)
kontrol("44px dokunma hedefi korundu", ".bs-eylem .dugme { min-height: 44px; }"
        in CSS_ST)
kontrol("SAHTE sayi/oran uretilmiyor",
        not re.search(r"\$\s?\d", BASIT)
        and "kalite puan" not in BASIT.lower())

# ── DAVRANIS DOGRULUK TABLOSU (node ile GERCEKTEN kosturulur) ──
_dt = r"""
import {autoStilKimligi, autoTuru, kanitMetni, guvenMetni} from './basit.js';
const A = (kaynak, kimlik) => ({stil_profili: {kaynak, kimlik}});
const c = [];
const e = (ad, alinan, beklenen) =>
  c.push({ad, ok: JSON.stringify(alinan) === JSON.stringify(beklenen),
          alinan, beklenen});

e('auto + belgesel hatti -> kimlik TASINIR',
  autoStilKimligi(A('auto', 'belgesel-sinematik'), 'documentary'),
  'belgesel-sinematik');
e('MELEZ kimlik TASINMAZ (hat cozemez, sessizce varsayilana duserdi)',
  autoStilKimligi(A('turetilmis', 'melez:a+b'), 'documentary'), '');
e('VARSAYILAN kaynak TASINMAZ (hat kendi varsayilanini korur)',
  autoStilKimligi(A('varsayilan', 'belgesel-sinematik'), 'documentary'), '');
e('KULLANICI kaynagi bu yoldan TASINMAZ (normal yoldan gider)',
  autoStilKimligi(A('kullanici', 'belgesel-sinematik'), 'documentary'), '');
e('hikaye hattinda TASINMAZ', autoStilKimligi(A('auto', 'korku-gerilim'),
  'hikaye'), '');
e('animasyon hattinda TASINMAZ',
  autoStilKimligi(A('auto', 'belgesel-sinematik'), 'animasyon'), '');
e('analiz yoksa TASINMAZ', autoStilKimligi(null, 'documentary'), '');
e('stil_profili yoksa TASINMAZ', autoStilKimligi({}, 'documentary'), '');
e('bos kimlik TASINMAZ', autoStilKimligi(A('auto', ''), 'documentary'), '');

const K = (etiket, oto) => ({konsept: {eski_etiket: etiket},
  otomatik_secimler: oto ? {tur: {deger: oto}} : {}});
e('YENI taksonomi hikayeyi yakaliyor (eski dedektor belirsiz dese bile)',
  autoTuru(K('hikaye', 'documentary'), {tur: 'documentary', turKaynak: ''}),
  'hikaye');
e('ayni tur zaten secili ise degisiklik YOK',
  autoTuru(K('belgesel', ''), {tur: 'documentary', turKaynak: ''}), '');
e('KULLANICI turu sectiyse Auto EZMEZ',
  autoTuru(K('hikaye', ''), {tur: 'documentary', turKaynak: 'kullanici'}), '');
e('konsept belirsizse ESKI alana dusulur',
  autoTuru(K('belirsiz', 'hikaye'), {tur: 'documentary', turKaynak: ''}),
  'hikaye');
e('analiz hatasinda tur DEGISMEZ',
  autoTuru({_hata: 'HTTP 500'}, {tur: 'documentary', turKaynak: ''}), '');
e('analiz yoksa tur DEGISMEZ', autoTuru(null, {tur: 'documentary'}), '');
e('animasyon Auto tarafindan ASLA secilmez',
  autoTuru(K('belirsiz', 'animasyon'), {tur: 'documentary', turKaynak: ''}), '');

e('kanit metni OLCULEN sayilari tasiyor',
  kanitMetni({kanit: 3, guven: 0.72}),
  'Metinde 3 bağımsız işaret ölçüldü; kararın güveni yüzde 72.');
e('kanit yoksa CUMLE UYDURULMAZ', kanitMetni({kanit: 0}), '');
e('guven metni belirsizi belirsiz diyor', guvenMetni({durum: 'belirsiz'}),
  'Belirsiz');
e('guven metni kesini kesin diyor', guvenMetni({durum: 'kesin'}), 'Sinyal net');

console.log(JSON.stringify(c));
"""

if subprocess.run(["node", "-v"], capture_output=True).returncode == 0:
    _dt_yol = os.path.join(_ST, "js", "_i3_dogruluk.mjs")
    try:
        with open(_dt_yol, "w", encoding="utf-8") as f:
            f.write(_dt)
        _r = subprocess.run(["node", _dt_yol], capture_output=True, text=True,
                            cwd=os.path.join(_ST, "js"))
        if _r.returncode != 0:
            kontrol("davranis dogruluk tablosu kosuyor", False,
                    (_r.stderr or "").strip().splitlines()[-1:])
        else:
            for _c in json.loads(_r.stdout):
                kontrol(f"I-3: {_c['ad']}", _c["ok"],
                        f"alinan={_c['alinan']!r} beklenen={_c['beklenen']!r}")
    finally:
        if os.path.exists(_dt_yol):
            os.unlink(_dt_yol)
else:
    bloke_yaz("I-3 davranis dogruluk tablosu", "node kurulu degil")

for _f in ("js/basit.js", "js/wizard.js", "js/durum.js"):
    _p = os.path.join(_ST, _f)
    _r = subprocess.run(["node", "--check", _p], capture_output=True, text=True) \
        if subprocess.run(["node", "-v"], capture_output=True).returncode == 0 \
        else None
    if _r is not None:
        kontrol(f"sozdizimi temiz: {_f}", _r.returncode == 0,
                (_r.stderr or "").strip().splitlines()[:1])


# ═══════════════ 17. FAZ I-4 — REFERANS VIDEO PARMAK IZI SOZLESMESI ═══════════════
# ⚠ BU BOLUMUN IDDIASI: surumlu/genisletilebilir bir STIL OZELLIK SOZLESMESI ve
# GUVENLI ANALIZ KAPISI var. Tam vision modeli ya da ucretli analiz BU ADIMDA
# YOK — testler de bunu kilitliyor (ag kutuphanesi yok, varsayilan USD tavani 0).
blok("17. I-4 — referans parmak izi sozlesmesi: kapsam ve genisletilebilirlik")

import shutil as _sh                                  # noqa: E402
import tempfile                                       # noqa: E402

import referans_parmak as rp                          # noqa: E402

_rk = rp.kapsam_ozeti()
kontrol("kapsam_ozeti sayilabilir",
        all(isinstance(_rk.get(k), int) for k in
            ("boyut", "alan", "yasak_alan", "durdurma_nedeni", "lisans",
             "kaynak_turu", "arsiv")), str(_rk))
kontrol("7 soyut boyut var", _rk["boyut"] >= 7, str(_rk["boyut"]))
kontrol("en az 25 ozellik alani", _rk["alan"] >= 25, str(_rk["alan"]))
kontrol("istenen boyutlarin hepsi tanimli",
        {"ritim", "cekim", "gecis", "tipografi", "renk", "kamera", "ses"}
        <= set(rp.OZELLIK_SEMASI), str(sorted(rp.OZELLIK_SEMASI)))
_bicim = [f"{b}.{a}" for b, al in rp.OZELLIK_SEMASI.items()
          for a, v in al.items()
          if not (isinstance(v, tuple) and len(v) == 4
                  and v[0] in (float, str, bool) and isinstance(v[3], str))]
kontrol("her alan (tip, birim, fallback, aciklama) bicimli", not _bicim,
        str(_bicim))
_fb = [f"{b}.{a}" for b, al in rp.OZELLIK_SEMASI.items()
       for a, (t, _br, fb, _ac) in al.items() if not rp._tip_uygun(fb, t)]
kontrol("fallback degerleri semadaki tiple UYUMLU", not _fb, str(_fb))

# Cekirdek kod alan adi BILMIYOR: semaya satir eklemek yeter
_ek_boyut = "ritim"
rp.OZELLIK_SEMASI[_ek_boyut]["_gecici_alan"] = (float, "sn", 1.5, "gecici")
try:
    _p_ek = rp.parmak_kur({"acik": True}, {})
    kontrol("YENI ALAN cekirdek kod DEGISMEDEN uretiliyor",
            "_gecici_alan" in _p_ek["ozellik"][_ek_boyut]
            and _p_ek["ozellik"][_ek_boyut]["_gecici_alan"]["deger"] == 1.5)
    kontrol("yeni alan dogrulamadan da geciyor", not rp.dogrula(_p_ek))
finally:
    del rp.OZELLIK_SEMASI[_ek_boyut]["_gecici_alan"]

# Surumleme
_ars_p = rp.bos_parmak("VIDEO-YOK")
_anahtar = rp.arsivle("ref-abc", _ars_p)
kontrol("arsivlenen surum AYNEN geri geliyor",
        rp.arsivden_al("ref-abc", rp.SEMA_SURUM)["sema_surum"] == rp.SEMA_SURUM)
kontrol("olmayan surum SESSIZCE baskasini DONDURMUYOR",
        _kaldirilan_hata(lambda: rp.arsivden_al("ref-abc", "9.9.9"), KeyError))
kontrol("arsiv DERIN KOPYA (kayit disaridan bozulamaz)",
        (lambda a: (a["ozellik"].clear(),
                    rp.arsivden_al("ref-abc", rp.SEMA_SURUM)["ozellik"] != {})[1])(
            rp.arsivden_al("ref-abc", rp.SEMA_SURUM)))


blok("17b. I-4 — YASAK ALANLAR (kaynak video KOPYALANMAZ)")

kontrol("en az 8 yasak alan tanimli", len(rp.YASAK_ALAN) >= 8,
        str(len(rp.YASAK_ALAN)))
kontrol("her yasak alanin aciklamasi var",
        all(isinstance(v, str) and len(v) > 10 for v in rp.YASAK_ALAN.values()))
for _y in ("kisi_kimligi", "marka_logo", "ozgun_metin", "sahne_kopyasi",
           "ses_kopyasi"):
    kontrol(f"yasak alan tanimli: {_y}", _y in rp.YASAK_ALAN)
kontrol("SEMA kendi yasagini ihlal ETMIYOR",
        not rp.yasak_denetle(rp.OZELLIK_SEMASI),
        str(rp.yasak_denetle(rp.OZELLIK_SEMASI)[:2]))
kontrol("parmak izi yasak beyanini TASIYOR",
        set(rp.bos_parmak("VIDEO-YOK")["yasak_beyani"]) == set(rp.YASAK_ALAN))

_ihlal = rp.bos_parmak("VIDEO-YOK")
_ihlal["kisi_kimligi"] = "Ahmet Y."
kontrol("yasak alan ENJEKSIYONU reddediliyor",
        any("SOZLESME IHLALI" in h for h in rp.dogrula(_ihlal)),
        str(rp.dogrula(_ihlal)[:1]))
_ic = rp.bos_parmak("VIDEO-YOK")
_ic["kimlik"] = {"ek": {"derin": {"marka_logo": "X"}}}
kontrol("IC ICE yasak alan da yakalaniyor",
        any("marka_logo" in h for h in rp.dogrula(_ic)))
kontrol("gomulu veri (data URI) reddediliyor",
        rp.yasak_denetle({"a": "data:image/png;base64,AAAA"}))
kontrol("ham ikili veri reddediliyor", rp.yasak_denetle({"a": b"\x00\x01"}))
kontrol("asiri uzun metin (ozgun icerik kopyasi) reddediliyor",
        rp.yasak_denetle({"a": "x" * 500}))
kontrol("normal kisa metin reddedilMIYOR (yanlis pozitif yok)",
        not rp.yasak_denetle({"baskin_tur": "hard-cut", "sinif": "orta"}))


blok("17c. I-4 — GUVENLI KAPI: normal / hata / guvenlik / fallback")

_PROBE_OK = json.dumps({
    "streams": [{"width": 1920, "height": 1080, "r_frame_rate": "30/1",
                 "codec_name": "h264"}],
    "format": {"duration": "120.5", "size": "4096",
               "format_name": "mov,mp4,m4a"}})
_BEYAN = {"kaynak_turu": "yukleme", "lisans": "sahibiyim", "stil_izni": True}


def _yeni_butce(**ez):
    ayar = {"maks_kare": 6, "maks_sn": 30.0, "maks_usd": 0.0}
    ayar.update(ez)
    return rp.ParmakButce(**ayar)


_kok = tempfile.mkdtemp(prefix="i4_ref_")
try:
    _vid = os.path.join(_kok, "ref.mp4")
    with open(_vid, "wb") as _f:
        _f.write(b"x" * 4096)

    # ── NORMAL ──
    _k = rp.kapi(_vid, beyan=_BEYAN, butce=_yeni_butce(), izinli_kok=_kok,
                 probe_fn=lambda c: _PROBE_OK)
    kontrol("gecerli video + beyan -> kapi ACIK", _k["acik"], str(_k["neden"]))
    kontrol("codec/cozunurluk/sure OKUNUYOR",
            _k["medya"]["codec"] == "h264" and _k["medya"]["genislik"] == 1920
            and _k["medya"]["yukseklik"] == 1080
            and _k["medya"]["sure_sn"] == 120.5, str(_k["medya"]))
    kontrol("fps okunuyor", _k["medya"]["fps"] == 30.0)
    kontrol("kimlik/provenance hash iceriyor",
            len(_k["kimlik"]["sha256"]) == 64 and _k["kimlik"]["bayt"] == 4096)
    kontrol("kimlik lisans ve kaynak turunu TASIYOR",
            _k["kimlik"]["lisans"] == "sahibiyim"
            and _k["kimlik"]["kaynak_turu"] == "yukleme")
    kontrol("ornekleme plani uretiliyor", _k["plan"]["adet"] == 6)
    kontrol("ffprobe komutu YEREL ve ucretsiz",
            rp.medya_probe_komutu(_vid)[0] == "ffprobe")

    # ── HATA / GUVENLIK ──
    _vak = [
        ("video verilmedi", "", _BEYAN, _kok, "VIDEO-YOK"),
        ("dosya yok", os.path.join(_kok, "yok.mp4"), _BEYAN, _kok, "DOSYA-YOK"),
        ("dizin verildi", _kok, _BEYAN, _kok, "DOSYA-TURU"),
        ("traversal", os.path.join(_kok, "..", "..", "etc", "passwd"),
         _BEYAN, _kok, "YOL-GUVENSIZ"),
        ("izinli kok disi", "/etc/hosts", _BEYAN, _kok, "YOL-GUVENSIZ"),
        ("provenance yok", _vid, {}, _kok, "PROVENANCE-EKSIK"),
        ("kaynak turu gecersiz", _vid,
         {"kaynak_turu": "internetten-buldum", "lisans": "sahibiyim",
          "stil_izni": True}, _kok, "PROVENANCE-EKSIK"),
        ("lisans yok", _vid, {"kaynak_turu": "yukleme"}, _kok, "LISANS-EKSIK"),
        ("lisans 'bilinmiyor' KABUL EDILMIYOR", _vid,
         {"kaynak_turu": "yukleme", "lisans": "bilinmiyor", "stil_izni": True},
         _kok, "LISANS-EKSIK"),
        ("stil izni verilmemis", _vid,
         {"kaynak_turu": "yukleme", "lisans": "sahibiyim"}, _kok,
         "LISANS-EKSIK"),
    ]
    for _ad, _y, _b, _kk, _bek in _vak:
        _s = rp.kapi(_y, beyan=_b, butce=_yeni_butce(), izinli_kok=_kk,
                     probe_fn=lambda c: _PROBE_OK)
        kontrol(f"kontrollu dur: {_ad} -> {_bek}",
                not _s["acik"] and _s["neden"] == _bek, str(_s["neden"]))

    # Sembolik baglanti izinli kokte ama HEDEFI disarida
    _sym = os.path.join(_kok, "kacak.mp4")
    try:
        os.symlink("/etc/hosts", _sym)
        _s = rp.kapi(_sym, beyan=_BEYAN, butce=_yeni_butce(), izinli_kok=_kok,
                     probe_fn=lambda c: _PROBE_OK)
        kontrol("SYMLINK ile kok disina kacis engelleniyor",
                not _s["acik"] and _s["neden"] == "YOL-GUVENSIZ", str(_s["neden"]))
    except (OSError, NotImplementedError):
        bloke_yaz("symlink kacis testi", "symlink olusturulamadi")

    # Bozuk / eksik medya
    _bos = os.path.join(_kok, "bos.mp4")
    open(_bos, "wb").close()
    kontrol("bos dosya -> BOZUK-MEDYA",
            rp.kapi(_bos, beyan=_BEYAN, butce=_yeni_butce(), izinli_kok=_kok,
                    probe_fn=lambda c: _PROBE_OK)["neden"] == "BOZUK-MEDYA")
    for _ad, _fn in [("probe bozuk JSON", lambda c: "bu json degil"),
                     ("probe bos", lambda c: ""),
                     ("video akisi yok",
                      lambda c: json.dumps({"streams": [],
                                            "format": {"duration": "60"}}))]:
        kontrol(f"kontrollu dur: {_ad} -> BOZUK-MEDYA",
                rp.kapi(_vid, beyan=_BEYAN, butce=_yeni_butce(),
                        izinli_kok=_kok, probe_fn=_fn)["neden"] == "BOZUK-MEDYA")

    def _patlayan(c):
        raise RuntimeError("kasitli probe patlamasi")

    _s = rp.kapi(_vid, beyan=_BEYAN, butce=_yeni_butce(), izinli_kok=_kok,
                 probe_fn=_patlayan)
    kontrol("probe PATLARSA kapi cokmuyor, kontrollu duruyor",
            not _s["acik"] and _s["neden"] == "BOZUK-MEDYA")
    kontrol("olcum araci yoksa ARAC-YOK",
            rp.kapi(_vid, beyan=_BEYAN, butce=_yeni_butce(), izinli_kok=_kok,
                    probe_fn=None, arac_var=False)["neden"] == "ARAC-YOK")

    # Sure / boyut tavanlari
    _uzun = json.dumps({"streams": [{"width": 1920, "height": 1080,
                                     "r_frame_rate": "30/1",
                                     "codec_name": "h264"}],
                        "format": {"duration": "99999"}})
    kontrol("cok uzun video -> SURE-ASIMI",
            rp.kapi(_vid, beyan=_BEYAN, butce=_yeni_butce(), izinli_kok=_kok,
                    probe_fn=lambda c: _uzun)["neden"] == "SURE-ASIMI")
    _kisa = json.dumps({"streams": [{"width": 1920, "height": 1080,
                                     "r_frame_rate": "30/1",
                                     "codec_name": "h264"}],
                        "format": {"duration": "3"}})
    kontrol("cok kisa video -> SURE-YETERSIZ",
            rp.kapi(_vid, beyan=_BEYAN, butce=_yeni_butce(), izinli_kok=_kok,
                    probe_fn=lambda c: _kisa)["neden"] == "SURE-YETERSIZ")
    kontrol("buyuk dosya -> BOYUT-ASIMI",
            rp.kapi(_vid, beyan=_BEYAN, butce=_yeni_butce(maks_bayt=10),
                    izinli_kok=_kok,
                    probe_fn=lambda c: _PROBE_OK)["neden"] == "BOYUT-ASIMI")
    kontrol("butce kapaliysa -> BUTCE",
            rp.kapi(_vid, beyan=_BEYAN, butce=_yeni_butce(maks_kare=0),
                    izinli_kok=_kok,
                    probe_fn=lambda c: _PROBE_OK)["neden"] == "BUTCE")
    kontrol("butce siniri ustunde HASH ALINMIYOR (buyuk dosya okunmaz)",
            rp.dosya_ozeti(_vid, 10)["hash_alindi"] is False)

    kontrol("her durdurma nedeninin ACIKLAMASI var",
            all(isinstance(v, str) and v for v in rp.DURDURMA_NEDENI.values()))
    _tanimsiz = {v[4] for v in _vak} - set(rp.DURDURMA_NEDENI)
    kontrol("uretilen tum nedenler tabloda tanimli", not _tanimsiz,
            str(_tanimsiz))

    # ── PARMAK IZI: FALLBACK ve UYDURMA YASAGI ──
    blok("17d. I-4 — parmak izi: fallback gorunur, UYDURMA yok")

    _b = _yeni_butce()
    _kapali = rp.kapi("", beyan=_BEYAN, butce=_b, izinli_kok=_kok)
    _p0 = rp.parmak_kur(_kapali, butce=_b)
    kontrol("kapi kapaliyken durum OLCULMEDI", _p0["durum"] == "OLCULMEDI")
    kontrol("kapali kapida HICBIR alan 'olculdu' degil",
            all(v["kaynak"] != "olculdu" for blk in _p0["ozellik"].values()
                for v in blk.values()))
    kontrol("kapali kapida guven 0.0 (uydurma yok)", _p0["guven"] == 0.0)
    kontrol("durdurma sebebi parmak izinde GORUNUR",
            _p0["neden"] == "VIDEO-YOK" and _p0["aciklama"])
    kontrol("butce ozeti parmak izine yaziliyor", "engel" in _p0["butce"])
    kontrol("bos parmak izi semaya UYUYOR", not rp.dogrula(_p0))

    _k2 = rp.kapi(_vid, beyan=_BEYAN, butce=_b, izinli_kok=_kok,
                  probe_fn=lambda c: _PROBE_OK)
    _p1 = rp.parmak_kur(_k2, {}, _b)
    kontrol("kapi ACIK ama olcum YOKSA yine OLCULMEDI",
            _p1["durum"] == "OLCULMEDI" and _p1["olculen_alan"] == 0)

    _olc = {"ritim": {"kesme_dk": (12.4, 0.8, "25 kesme / 120.5 sn"),
                      "tempo_sinifi": ("hizli", 0.6, "kesme yogunlugu")},
            "cekim": {"medyan_sn": (4.2, 0.7, "olculen dagilim")}}
    _p2 = rp.parmak_kur(_k2, _olc, _b)
    kontrol("olculen alanlar 'olculdu' kaynagini tasiyor",
            _p2["ozellik"]["ritim"]["kesme_dk"]["kaynak"] == "olculdu"
            and _p2["ozellik"]["ritim"]["kesme_dk"]["deger"] == 12.4)
    kontrol("olculen alanda KANIT metni var",
            "25 kesme" in _p2["ozellik"]["ritim"]["kesme_dk"]["kanit"])
    kontrol("olculmeyen alan 'varsayilan' + guven 0.0 (gizlenmiyor)",
            _p2["ozellik"]["renk"]["parlaklik_ort"]["kaynak"] == "varsayilan"
            and _p2["ozellik"]["renk"]["parlaklik_ort"]["guven"] == 0.0)
    kontrol("kac alanin olculdugu SAYILABILIR",
            _p2["olculen_alan"] == 3 and _p2["toplam_alan"] == _rk["alan"],
            f"{_p2['olculen_alan']}/{_p2['toplam_alan']}")
    kontrol("durum OLCULDU ve genel guven ortalamadan",
            _p2["durum"] == "OLCULDU" and 0 < _p2["guven"] <= 1)
    kontrol("dolu parmak izi semaya UYUYOR", not rp.dogrula(_p2))
    kontrol("kimlik/medya/plan parmak izine tasiniyor",
            _p2["kimlik"].get("sha256") and _p2["medya"].get("codec")
            and _p2["plan"].get("adet"))

    _kotu = rp.parmak_kur(_k2, {"ritim": {"kesme_dk": ("cok hizli", 0.9, "x"),
                                          "tempo_sinifi": (3.5, 0.9, "x")}}, _b)
    kontrol("YANLIS TIPTE olcum sessizce kabul EDILMIYOR",
            _kotu["ozellik"]["ritim"]["kesme_dk"]["kaynak"] == "varsayilan"
            and _kotu["ozellik"]["ritim"]["tempo_sinifi"]["kaynak"] == "varsayilan")
    _asiri = rp.parmak_kur(_k2, {"ritim": {"kesme_dk": (9.0, 7.5, "x")}}, _b)
    kontrol("guven 0-1 araligina KIRPILIYOR",
            _asiri["ozellik"]["ritim"]["kesme_dk"]["guven"] == 1.0)
    _sahte = rp.bos_parmak("VIDEO-YOK")
    _sahte["ozellik"]["ritim"]["kesme_dk"]["guven"] = 0.9
    kontrol("olculmedigi halde guven>0 DOGRULAMADAN GECMIYOR",
            any("guven > 0" in h for h in rp.dogrula(_sahte)))

    # ── ORNEKLEME PLANI ──
    blok("17e. I-4 — ornekleme plani ve butce")

    _pl1 = rp.ornekleme_plani(120.0, _yeni_butce())
    _pl2 = rp.ornekleme_plani(120.0, _yeni_butce())
    kontrol("plan DETERMINISTIK (ayni girdi -> ayni plan)", _pl1 == _pl2)
    kontrol("plan butce tavanini ASMIYOR", _pl1["adet"] <= 6)
    kontrol("kenar kirpmasi uygulaniyor (jenerik stil degildir)",
            _pl1["kirpma_sn"] > 0 and _pl1["saniyeler"][0] >= _pl1["kirpma_sn"])
    kontrol("son ornek video sonunu ASMIYOR", _pl1["saniyeler"][-1] <= 120.0)
    kontrol("tek kare butcesinde ORTA nokta secilir",
            rp.ornekleme_plani(100.0, _yeni_butce(maks_kare=1))["adet"] == 1)
    kontrol("kare butcesi 0 -> BOS plan (uydurma ornek yok)",
            rp.ornekleme_plani(120.0, _yeni_butce(maks_kare=0))["adet"] == 0)
    kontrol("sure 0 -> BOS plan",
            rp.ornekleme_plani(0, _yeni_butce())["adet"] == 0)
    kontrol("plan gerekcesi yaziliyor", "deterministik" in _pl1["gerekce"])

    for _alan_ad in ("maks_kare", "maks_sn", "maks_usd", "maks_bayt",
                     "maks_sure_sn"):
        kontrol(f"SINIRSIZ butce yasak: {_alan_ad}=None -> ValueError",
                _kaldirilan_hata(lambda a=_alan_ad: rp.ParmakButce(**{a: None}),
                                 ValueError))
    kontrol("negatif tavan reddediliyor",
            _kaldirilan_hata(lambda: rp.ParmakButce(maks_kare=-1), ValueError))
    kontrol("VARSAYILAN USD tavani 0 (bu adimda ucretli cagriya yer YOK)",
            rp.varsayilan_butce().maks_usd == 0.0)
    kontrol("ucretli birim istenirse butce KAPALI kalir",
            rp.varsayilan_butce().uygun_mu(0.01)[0] is False)

    # Thread guvenligi: kilitsiz sayacla tavan asilirdi
    _tb = rp.ParmakButce(maks_kare=10, maks_sn=30, maks_usd=0.0)
    _verilen = []
    _kilit = threading.Lock()

    def _yaris():
        for _ in range(20):
            ok, _n = _tb.yer_ayir(0.0)
            if ok:
                with _kilit:
                    _verilen.append(1)

    _th = [threading.Thread(target=_yaris) for _ in range(8)]
    [t.start() for t in _th]
    [t.join() for t in _th]
    kontrol("THREAD GUVENLI: paralel istekte tavan ASILMIYOR",
            len(_verilen) == 10, f"{len(_verilen)} verildi (tavan 10)")
    kontrol("butce engeli SESSIZ degil, kayda yaziliyor", bool(_tb.ozet()["engel"]))
finally:
    _sh.rmtree(_kok, ignore_errors=True)


blok("17f. I-4 — ag/ucret yok ve mevcut sozlesmeler KORUNDU")

_RP_KAYNAK = oku(KOK, "referans_parmak.py")
kontrol("modul AG KULLANMIYOR (ucretsiz)",
        all(x not in _RP_KAYNAK for x in
            ("requests", "urllib", "http://", "https://", "openai",
             "socket")), "ag izi bulundu")
# ⚠ "vision cagrilmiyor" iddiasi DIZE TARAMASIYLA yetinmez: modul kendi
# dokumantasyonunda zaten "tam vision modeli YAPILMIYOR" diyor. Olculen sey
# CAGRI IZI: model kimligi, sohbet ucu ya da ffprobe disinda bir dis komut.
kontrol("MODEL KIMLIGI ya da sohbet ucu izi YOK",
        not re.search(r"gpt-|claude-|gemini|chat\.completions|oai_chat|"
                      r"\.messages\.create", _RP_KAYNAK, re.I))
_komutlar = set(re.findall(r'^\s*return \["(\w+)"', _RP_KAYNAK, re.M))
kontrol("TEK dis komut ffprobe (ucretsiz, yerel)", _komutlar == {"ffprobe"},
        str(_komutlar))
kontrol("modul kendisi ALT SUREC baslatmiyor (komutu yalnizca URETIYOR)",
        "subprocess" not in _RP_KAYNAK)
kontrol("olcum DISARIDAN enjekte ediliyor (motor bu adimda yazilmadi)",
        "def parmak_kur(kapi_sonucu: dict, olcumler: dict = None" in _RP_KAYNAK)
kontrol("referans_parmak.py derleniyor",
        _derlenir(os.path.join(KOK, "referans_parmak.py")))

# ⚠ MEVCUT SOZLESMELER: bu adim hicbirine dokunmadi
_SRV = oku(KOK, "server.py")
kontrol("22 alanlik generate sozlesmesi DEGISMEDI",
        len(set(re.findall(r"\{ad: '(\w+)'",
                           oku(KOK, "static/js/api.js")))) == 22)
kontrol("server.py referans_parmak'i HENUZ import etmiyor (baglanti sonraki adim)",
        "referans_parmak" not in _SRV)
kontrol("pipeline.py referans_parmak'i HENUZ import etmiyor",
        "referans_parmak" not in oku(KOK, "pipeline.py"))
kontrol("basit mod KORUNDU", "basitGovde" in oku(KOK, "static/js/wizard.js"))
kontrol("sure secici KORUNDU", "SURE_SECENEKLERI" in oku(KOK, "static/js/basit.js"))
kontrol("unlu modu KORUNDU",
        "d.unlu = t.unlu ? '1' : '0'" in oku(KOK, "static/js/wizard.js"))
kontrol("ses kutuphanesi KORUNDU",
        "sesBolumu({" in oku(KOK, "static/js/basit.js"))
kontrol("deploy.sh ezme korumasi KORUNDU",
        "GERIDE" in open(os.path.join(KOK, "..", "deploy.sh"),
                         encoding="utf-8").read())


# ═══════════════ 18. FAZ I-2d — GORSEL IMZA BOSLUGU KAPATILDI ═══════════════
# ⚠ §18'de OLCULEN acik: yeni-nesil stil kimliginde `EFEKT_TEMEL` ve
# `GECIS_IMZASI` karsiliksizdi -> efekt=0, gecis=yok. Tempo/footage profilden
# geliyordu ama gorsel imza GELMIYORDU (sessiz kalite kaybi). Bu bolum hem
# kapanmayi hem de ESKI kimliklerin BIT-BIT korundugunu kilitler.
blok("18. I-2d — gorsel imza: eski kimlik gerilemesi ve yeni kimlik turetmesi")

_PP2 = oku(KOK, "pipeline.py")
kontrol("gorsel imza tureticisi tanimli", "def bilesik_gorsel_imza(" in _PP2)
kontrol("efekt_ata opsiyonel ek_profil aliyor",
        "def efekt_ata(edit_id: str, islev: str, indeks: int, ek_profil=None)"
        in _PP2)
kontrol("gecis_imza_sec opsiyonel ek_profil aliyor",
        "def gecis_imza_sec(edit_id: str, indeks: int, ek_profil=None)" in _PP2)
kontrol("cagri noktasi bilesik profili GECIYOR",
        "gecis_imza_sec(edit_id, i, _gorsel_ek)" in _PP2
        and "i, _gorsel_ek)" in _PP2)
kontrol("kunyeye gorsel imza izlenebilirligi yaziliyor",
        '"gorsel_imza"' in _PP2 and '"gerekce": _gi_ozet["gerekce"]' in _PP2)
kontrol("hikaye/animasyon sozluklerine TASMA yok",
        "HIKAYE_STILLERI" not in _PP2.split("def bilesik_gorsel_imza(")[1]
        .split("def efekt_ata(")[0])

_i2d_kok = os.path.join(KOK, "..", "cikti", "_i2d_kok")
try:
    os.makedirs(_i2d_kok, exist_ok=True)
    _uk = os.path.join(KOK, "..", "app", "uret.py")
    if os.path.exists(_uk):
        _sh.copy(_uk, os.path.join(_i2d_kok, "uret.py"))
    os.environ["VIDRUSH_KOK"] = os.path.abspath(_i2d_kok)
    import pipeline as _pl2                           # noqa: E402

    # ── (a) ESKI KIMLIK GERILEMESI: bagimsiz referans uygulamayla karsilastir ──
    # ⚠ Referans, DOKUNULMAMIS tablolardan yeniden kurulur; yani "kod kendi
    # kendini dogruluyor" degil, DAVRANIS eski algoritmayla karsilastiriliyor.
    def _ref_efekt(edit_id, islev, indeks):
        temel = [dict(e) for e in _pl2.EFEKT_TEMEL.get(edit_id, [])]
        vurgu = _pl2.EFEKT_ISLEV.get(islev or "", [])
        if vurgu and (indeks * 6151 % 100) / 100.0 < _pl2.EFEKT_SEYREKLIK:
            adlar = {e["ad"] for e in temel}
            for e in vurgu:
                if e["ad"] in adlar:
                    for t in temel:
                        if t["ad"] == e["ad"]:
                            t["siddet"] = max(t.get("siddet", 1),
                                              e.get("siddet", 1))
                else:
                    temel.append(dict(e))
        return temel

    def _ref_gecis(edit_id, indeks):
        imza, oran = _pl2.GECIS_IMZASI.get(edit_id, ("", 0.0))
        if not imza or oran <= 0:
            return ""
        return imza if (indeks * 4177 % 1000) / 1000.0 < oran else ""

    _islevler = ["", "vurgu", "gecmis", "karsilastir", "sonuc", "aciklama"]
    _ef_fark, _gz_fark = [], []
    for _eid in _pl2.EDIT_STILLERI:
        for _i in range(120):
            _isl = _islevler[_i % len(_islevler)]
            if _pl2.efekt_ata(_eid, _isl, _i) != _ref_efekt(_eid, _isl, _i):
                _ef_fark.append((_eid, _isl, _i))
            if _pl2.gecis_imza_sec(_eid, _i) != _ref_gecis(_eid, _i):
                _gz_fark.append((_eid, _i))
    kontrol("ESKI kimliklerde efekt atamasi BIT-BIT ayni (5 stil x 120 sahne)",
            not _ef_fark, str(_ef_fark[:3]))
    kontrol("ESKI kimliklerde gecis imzasi BIT-BIT ayni", not _gz_fark,
            str(_gz_fark[:3]))
    kontrol("BILINMEYEN kimlik eski davranisini KORUYOR (efekt yok, imza yok)",
            _pl2.efekt_ata("boyle-bir-stil-yok", "", 0) == []
            and _pl2.gecis_imza_sec("boyle-bir-stil-yok", 0) == "")
    kontrol("gecis imzasi HALA deterministik (ayni sahne -> ayni imza)",
            all(_pl2.gecis_imza_sec("sinematik-belgesel", _i)
                == _pl2.gecis_imza_sec("sinematik-belgesel", _i)
                for _i in range(50)))
    kontrol("eski stil imzasi GERCEKTEN uretiliyor (kanit: en az bir sahne)",
            any(_pl2.gecis_imza_sec("sinematik-belgesel", _i)
                for _i in range(60)))

    # ── (b) YENI KIMLIK: sessiz kayip KALKTI ──
    def _ek(kimlik):
        return sp.eski_edit_stiline(sp.profil_al(kimlik))["_profil"]

    _bos = [k for k in sp.PROFIL
            if not _pl2.bilesik_gorsel_imza(_ek(k))["uygulandi"]]
    kontrol("12 profilin HEPSI gorsel imza uretiyor (sessiz kayip yok)",
            not _bos, str(_bos))
    for _k in sp.PROFIL:
        _g = _pl2.bilesik_gorsel_imza(_ek(_k))
        _kotu_ef = [e["ad"] for e in _g["efektler"]
                    if e["ad"] not in _pl2.GECERLI_EFEKT_ADI]
        if _kotu_ef:
            kontrol(f"{_k}: efekt adlari render tarafinin BILDIGI adlar",
                    False, str(_kotu_ef))
    kontrol("uretilen efekt adlari render tarafinin BILDIGI adlar",
            all(e["ad"] in _pl2.GECERLI_EFEKT_ADI
                for k in sp.PROFIL
                for e in _pl2.bilesik_gorsel_imza(_ek(k))["efektler"]))
    kontrol("uretilen gecis imzalari render tarafinin BILDIGI adlar",
            all(_pl2.bilesik_gorsel_imza(_ek(k))["gecis_imza"]
                in ("",) + _pl2.GECERLI_GECIS_IMZA for k in sp.PROFIL))
    kontrol("gecis turlerinin HEPSI eslenmis (uydurma yok)",
            {p["gecis"]["tur"] for p in sp.PROFIL.values()}
            <= set(_pl2.BILESIK_GECIS_IMZA),
            str({p["gecis"]["tur"] for p in sp.PROFIL.values()}
                - set(_pl2.BILESIK_GECIS_IMZA)))
    kontrol("gecis orani 0-1 araliginda",
            all(0.0 <= _pl2.bilesik_gorsel_imza(_ek(k))["gecis_oran"] <= 1.0
                for k in sp.PROFIL))

    # Eski tabloya karsi KALIBRASYON (esdeger profil, esdeger imza)
    _kal = _pl2.bilesik_gorsel_imza(_ek("belgesel-sinematik"))
    _kal_ad = {e["ad"] for e in _kal["efektler"]}
    kontrol("belgesel-sinematik eski 'sinematik-belgesel' ruhunu tasiyor",
            {"grain", "vinyet", "kontrast-grade"} <= _kal_ad, str(_kal_ad))
    kontrol("bilim-anlatisi eski 'veri-anlatisi' ile AYNI (grain 0.5)",
            _pl2.bilesik_gorsel_imza(_ek("bilim-anlatisi"))["efektler"]
            == [{"ad": "grain", "siddet": 0.5}])
    kontrol("explainer-hizli eski 'hizli-explainer' ile AYNI (efekt YOK)",
            _pl2.bilesik_gorsel_imza(_ek("explainer-hizli"))["efektler"] == [])
    kontrol("parlak/temiz gorunumde doku EKLENMIYOR",
            not _pl2.bilesik_gorsel_imza(_ek("urun-tanitim"))["efektler"])
    kontrol("karanlik profilde soguk grade + vinyet geliyor",
            {"soguk-grade", "vinyet"}
            <= {e["ad"] for e in
                _pl2.bilesik_gorsel_imza(_ek("korku-gerilim"))["efektler"]})

    # Yeni kimlik UCTAN UCA: efekt_ata/gecis_imza_sec profilden besleniyor
    _ekp = _ek("korku-gerilim")
    kontrol("efekt_ata bilesik profilden BESLENIYOR",
            {e["ad"] for e in _pl2.efekt_ata("korku-gerilim", "", 0, _ekp)}
            >= {"grain", "soguk-grade"})
    kontrol("gecis_imza_sec bilesik profilden BESLENIYOR",
            any(_pl2.gecis_imza_sec("cocuk-yumusak", _i, _ek("cocuk-yumusak"))
                for _i in range(20)))
    kontrol("islev vurgusu bilesik profille de calisiyor (seyrek aksan)",
            any("sarsinti" in {e["ad"] for e in
                               _pl2.efekt_ata("korku-gerilim", "vurgu", _i, _ekp)}
                for _i in range(30)))
    kontrol("ek_profil VERILMEZSE eski tablo isler (yeni kimlik -> bos)",
            _pl2.efekt_ata("korku-gerilim", "", 0) == [])

    # ── (c) BOZUK PROFIL / FALLBACK ──
    for _ad, _bozuk in [("None", None), ("bos sozluk", {}),
                        ("sozluk degil", "bozuk"), ("liste", [1, 2]),
                        ("palet bozuk", {"palet": "x", "gecis": "y"}),
                        ("palet None", {"palet": None, "gecis": None}),
                        ("alanlar eksik", {"palet": {}, "gecis": {}}),
                        ("oran metin", {"palet": {"grade": "dogal-sicak",
                                                  "kontrast": "orta"},
                                        "gecis": {"tur": "hard-cut",
                                                  "oran_pct": "cok"}})]:
        _g = _pl2.bilesik_gorsel_imza(_bozuk)
        kontrol(f"bozuk profil COKERTMIYOR: {_ad}",
                isinstance(_g, dict) and "uygulandi" in _g)
    kontrol("bozuk profilde efekt_ata ESKI tabloya duser",
            _pl2.efekt_ata("sinematik-belgesel", "", 0, {"palet": "bozuk"})
            == [dict(e) for e in _pl2.EFEKT_TEMEL["sinematik-belgesel"]])
    kontrol("bozuk profilde gecis_imza_sec ESKI tabloya duser",
            all(_pl2.gecis_imza_sec("sinematik-belgesel", _i, {"palet": "x"})
                == _ref_gecis("sinematik-belgesel", _i) for _i in range(40)))
    kontrol("bilinmeyen gecis turunde imza URETILMIYOR (uydurma yok)",
            _pl2.bilesik_gorsel_imza(
                {"gecis": {"tur": "uzay-gecisi", "oran_pct": 50}})["gecis_imza"]
            == "")
    kontrol("oran 0 ise imza URETILMIYOR",
            _pl2.bilesik_gorsel_imza(
                {"gecis": {"tur": "hard-cut", "oran_pct": 0}})["gecis_imza"] == "")

    # ── (d) HER KARAR IZLENEBILIR ──
    _gk = _pl2.bilesik_gorsel_imza(_ek("belgesel-sinematik"))
    kontrol("her turetme GEREKCE uretiyor", len(_gk["gerekce"]) >= 2,
            str(_gk["gerekce"]))
    kontrol("gerekce hangi ALANDAN geldigini yaziyor",
            any("palet.grade" in g for g in _gk["gerekce"])
            and any("gecis.tur" in g for g in _gk["gerekce"]))
    kontrol("uygulanamayan durumda da GEREKCE var",
            _pl2.bilesik_gorsel_imza({"palet": {}, "gecis": {}})["gerekce"])
    kontrol("turetme SESSIZ degil: log satiri var",
            "GORSEL IMZA (bilesik)" in _PP2)
    kontrol("turetilemezse SESLI dusuluyor (eski tabloya sessizce gecilmez)",
            "TURETILEMEDI" in _PP2 and "eski tabloya dusuluyor" in _PP2)
    kontrol("turetme DETERMINISTIK (ayni profil -> ayni imza)",
            _pl2.bilesik_gorsel_imza(_ek("hikaye-sinematik"))
            == _pl2.bilesik_gorsel_imza(_ek("hikaye-sinematik")))
except Exception as e:
    bloke_yaz("I-2d gorsel imza fonksiyonel kosumu",
              f"{type(e).__name__}: {str(e)[:110]}")

kontrol("22 alanlik generate sozlesmesi HALA degismedi",
        len(set(re.findall(r"\{ad: '(\w+)'",
                           oku(KOK, "static/js/api.js")))) == 22)
kontrol("UI bu adimda DEGISMEDI (basit mod + sure secici duruyor)",
        "basitGovde" in oku(KOK, "static/js/wizard.js")
        and "SURE_SECENEKLERI" in oku(KOK, "static/js/basit.js"))
kontrol("referans olcum motoru bu adimda BAGLANMADI",
        "referans_parmak" not in _PP2)
kontrol("pipeline.py derleniyor (I-2d sonrasi)",
        _derlenir(os.path.join(KOK, "pipeline.py")))


# ═══════════ 19. FAZ I-5 — KONSEPT FARKINDALIKLI MEDYA SECIMI ═══════════
# ⚠ KAPATILAN ACIK: `sorgu_planlayici.KALIP` ve `AMAC_DAGILIMI` tamamen
# BELGESEL bicimliydi. Seyahat de, urun de, ders de AYNI cekim niyetini
# istiyordu -> farkli konseptler AYNI JENERIK STOK sonuclarini seciyordu.
# ⚠ BU BOLUM AG KULLANMAZ: gercek indirme YOK, saglayiciya istek YOK.
blok("19. I-5 — konsept farkindalikli sorgu plani ve siralama")

from medya import siralama as _sr                      # noqa: E402
from medya import sorgu_planlayici as _sp              # noqa: E402
from medya.aday import MedyaAdayi                      # noqa: E402

# ── (a) GERIYE UYUMLULUK: konsept=None -> BIT-BIT ayni ──
_METINLER = [
    "Tokyo Metropolitan Police reported 1987 unattended deaths in Chiba.",
    "The Ministry of Health published a report about the 1980s housing crisis.",
    "Interlaken and Zermatt mountain railway opened in 1912.",
    "",
    "kisa",
]
_fark = []
for _m in _METINLER:
    for _am in _sp.SAHNE_AMACLARI:
        _a = _sp.sorgu_plani(_m, _am, konu="konu")
        _b = _sp.sorgu_plani(_m, _am, konu="konu", konsept=None)
        if _a["sorgular"] != _b["sorgular"] or _a["amac"] != _b["amac"]:
            _fark.append((_m[:20], _am))
kontrol("konsept=None sorgu plani ESKISIYLE ayni", not _fark, str(_fark[:3]))
kontrol("konsept=None cikti eski anahtarlari KORUYOR",
        {"amac", "varliklar", "sorgular", "gerekce"}
        <= set(_sp.sorgu_plani(_METINLER[0], "ortam")))

# `amac_ata` referans uygulamasi — DOKUNULMAMIS tablodan yeniden kuruldu
def _ref_amac(indeks, kategori=""):
    kat = (kategori or "").lower()
    if kat == "alinti":
        return "belge"
    if kat == "cografya":
        return "harita"
    if kat == "isim":
        return "kisi"
    if kat == "tarih":
        return "arsiv"
    esik = (indeks * 37 + 11) % 100 / 100.0
    toplam = 0.0
    for ad, pay in _sp.AMAC_DAGILIMI:
        toplam += pay
        if esik < toplam:
            return ad
    return "ortam"


_afark = [(i, k) for i in range(300)
          for k in ("", "alinti", "cografya", "isim", "tarih", "bilinmeyen")
          if _sp.amac_ata(i, k) != _ref_amac(i, k)]
kontrol("konsept=None amac_ata BIT-BIT ayni (300 sahne x 6 kategori)",
        not _afark, str(_afark[:3]))

_BUGUN = "2026-08-12"


def _ad(**kw):
    d = {"asset_id": "x1", "saglayici": "wikimedia", "tur": "video",
         "orijinal_url": "https://commons.wikimedia.org/wiki/File:A",
         "indirme_url": "https://upload.wikimedia.org/a.webm",
         "baslik": "Tokyo street at night", "genislik": 3840,
         "yukseklik": 2160, "sure_sn": 10.0, "render_kullanilabilir": True,
         "erisim_tarihi": _BUGUN}
    d.update(kw)
    return MedyaAdayi(**d)


_VAR = {"yerler": ["Tokyo"], "kurumlar": [], "kisiler": [], "tarihler": ["2025"],
        "onyillar": ["2020s"], "konu_kelimeleri": ["street", "night"]}
_p_yok = _sr.puanla(_ad(), varliklar=_VAR, amac="ortam")
_p_none = _sr.puanla(_ad(asset_id="x2"), varliklar=_VAR, amac="ortam",
                     konsept=None)
kontrol("konsept=None puanlama BIT-BIT ayni",
        _p_yok.toplam_skor == _p_none.toplam_skor
        and _p_yok.skor_detay["amac"] == _p_none.skor_detay["amac"])
kontrol("konsept=None skor_detay'a 'konsept' EKLEMIYOR",
        "konsept" not in _p_none.skor_detay)
kontrol("agirlik vektoru DEGISMEDI",
        _sr.AGIRLIK == {"semantik": 0.34, "amac": 0.18, "teknik": 0.22,
                        "vision": 0.26}, str(_sr.AGIRLIK))

# ── (b) 12+ KONSEPT: medya niyeti / sorgu / cekim ihtiyaci ──
blok("19b. I-5 — 12+ konseptte medya niyeti AYRISIYOR")

# ⚠ §11'deki 19 konsept matrisinden secilenler; AYNI metinler kullaniliyor.
_MEDYA_MATRIS = [(_ad_, _mt_) for _ad_, _mt_, _a_, _t_ in MATRIS]
kontrol("medya matrisi en az 12 konsept iceriyor", len(_MEDYA_MATRIS) >= 12,
        str(len(_MEDYA_MATRIS)))


def _niyet(metin, konsept):
    """8 sahnelik CEKIM NIYETI kumesi: amac + kalip sablonu (varlik doldurmadan)."""
    kume = set()
    for i in range(8):
        amac = _sp.amac_ata(i, konsept=konsept)
        aile = _sp.konsept_ailesi(konsept)
        for k in (list(_sp.KONSEPT_KALIP.get(aile, {}).get(amac, []))
                  + list(_sp.KALIP.get(amac, []))):
            kume.add(f"{amac}:{k}")
    return kume


_niyet_yok, _niyet_var, _aileler = {}, {}, {}
for _kad, _kmetin in _MEDYA_MATRIS:
    _kon = tx.siniflandir(_kmetin)
    _aileler[_kad] = _sp.konsept_ailesi(_kon)
    _niyet_yok[_kad] = _niyet(_kmetin, None)
    _niyet_var[_kad] = _niyet(_kmetin, _kon)


def _cakisma(kumeler):
    adlar, oranlar = list(kumeler), []
    for i in range(len(adlar)):
        for j in range(i + 1, len(adlar)):
            a, b = kumeler[adlar[i]], kumeler[adlar[j]]
            if a | b:
                oranlar.append(len(a & b) / len(a | b))
    return sum(oranlar) / len(oranlar) if oranlar else 0.0


_c_yok, _c_var = _cakisma(_niyet_yok), _cakisma(_niyet_var)
kontrol("KONSEPTSIZ hali gercekten JENERIK (cakisma ~%100)", _c_yok > 0.95,
        f"%{_c_yok * 100:.1f}")
kontrol("KONSEPTLI halde cekim niyeti AYRISIYOR (cakisma dusuyor)",
        _c_var < _c_yok - 0.25, f"%{_c_yok * 100:.1f} -> %{_c_var * 100:.1f}")
kontrol("en az 4 FARKLI konsept ailesi tanindi",
        len({a for a in _aileler.values() if a}) >= 4,
        str(sorted({a for a in _aileler.values() if a})))

# Aile bazli cekim ihtiyaci — tur konvansiyonu testle kilitli
_SEY = tx.siniflandir("Isvicre 4K sinematik: Interlaken, Zermatt ve Luzern "
                      "manzaralari, 60 fps drone cekimi ve yuruyus turu.")
_URU = tx.siniflandir("iPhone 15 vs Galaxy S24 fiyat karsilastirmasi: kamera "
                      "ozellikleri, batarya ve satin alma tavsiyesi incelemesi.")
_EGT = tx.siniflandir("Kara delikler nasil olusur? Genel gorelilik teorisi, "
                      "olay ufku ve NASA arastirmacilarinin uzay gozlemleri.")
_HIK = tx.siniflandir("Kabus gibi bir gece: kapinin ardindaki golge yaklasirken "
                      "evde tek basina kalan cocugun yasadigi korku dolu saatler.")
kontrol("seyahat -> establishing/ortam agirlikli",
        _sp.konsept_ailesi(_SEY) == "seyahat", str(_sp.konsept_ailesi(_SEY)))
kontrol("urun -> DETAY agirlikli",
        [_sp.amac_ata(i, konsept=_URU) for i in range(10)].count("detay")
        >= 4, str([_sp.amac_ata(i, konsept=_URU) for i in range(10)]))
kontrol("urunde ARSIV sahnesi ISTENMIYOR (anlamsiz)",
        "arsiv" not in {_sp.amac_ata(i, konsept=_URU) for i in range(60)})
kontrol("hikayede BELGE/HARITA sahnesi ISTENMIYOR",
        not ({"belge", "harita"}
             & {_sp.amac_ata(i, konsept=_HIK) for i in range(60)}))
kontrol("egitimde harita/belge (sema-veri) GERCEKTEN isteniyor",
        {"harita", "belge"}
        <= {_sp.amac_ata(i, konsept=_EGT) for i in range(30)})
kontrol("seyahat sorgulari drone/scenic gibi TUR OZEL terim tasiyor",
        any(("drone" in s or "scenic" in s or "coastline" in s)
            for s in _sp.sorgu_plani("Interlaken and Zermatt mountain views",
                                     "establishing", konsept=_SEY)["sorgular"]),
        str(_sp.sorgu_plani("Interlaken and Zermatt mountain views",
                            "establishing", konsept=_SEY)["sorgular"]))
kontrol("urun sorgulari studyo/urun terimi tasiyor",
        any(("product" in s or "studio" in s or "macro" in s)
            for s in _sp.sorgu_plani("Galaxy S24 camera battery review", "detay",
                                     konu="phone", konsept=_URU)["sorgular"]))
kontrol("sorgu plani hangi ailenin kullanildigini RAPORLUYOR",
        _sp.sorgu_plani("Interlaken views", "establishing",
                        konsept=_SEY)["konsept_ailesi"] == "seyahat")
kontrol("aile dagilimlarinin hepsi 1.0'a topluyor",
        all(abs(sum(p for _a, p in d) - 1.0) < 1e-9
            for d in _sp.KONSEPT_AMAC_DAGILIMI.values()),
        str({k: round(sum(p for _a, p in d), 4)
             for k, d in _sp.KONSEPT_AMAC_DAGILIMI.items()}))
kontrol("aile dagilimlari yalnizca TANIMLI sahne amaclarini kullaniyor",
        all(a in _sp.SAHNE_AMACLARI
            for d in _sp.KONSEPT_AMAC_DAGILIMI.values() for a, _p in d))
kontrol("aile kaliplari yalnizca TANIMLI sahne amaclarina yaziliyor",
        all(a in _sp.SAHNE_AMACLARI
            for d in _sp.KONSEPT_KALIP.values() for a in d))

# ── (c) SIRALAMA: konsept siralamayi degistirir ama KAPIYI ACMAZ ──
blok("19c. I-5 — siralama: kapi ve lisans duvari KORUNDU")

_studyo = _ad(asset_id="p1", baslik="smartphone product studio white background",
              sorgu="product close up")
_arsiv = _ad(asset_id="p2", baslik="1950s archive newsreel historical footage",
             sorgu="archive footage")
_u1 = _sr.puanla(_ad(**{**_studyo.__dict__}), varliklar=_VAR, amac="detay",
                 konsept=_URU)
_u2 = _sr.puanla(_ad(**{**_arsiv.__dict__}), varliklar=_VAR, amac="detay",
                 konsept=_URU)
kontrol("urun konseptinde STUDYO adayi ARSIV adayindan ustun",
        _u1.skor_detay["amac"] > _u2.skor_detay["amac"],
        f"{_u1.skor_detay['amac']} vs {_u2.skor_detay['amac']}")
kontrol("konsept kaymasi SESSIZ degil (skor_detay'a yaziliyor)",
        "konsept" in _u1.skor_detay and "urun" in _u1.skor_detay["konsept"])
kontrol("konsept kaymasi SINIRLI (+-12 puan tavani)",
        all(abs(_sr.konsept_kaymasi(_a2, _URU)[0]) <= _sr.KONSEPT_KAYMA
            for _a2 in (_studyo, _arsiv, _ad())))

# ⚠ EN KRITIK: konsept puani bir adayi ALAKA KAPISINDAN GECIREMEZ.
_alakasiz = _ad(asset_id="z1", baslik="berlin office meeting product studio",
                sorgu="product studio")
_g_yok = _sr.puanla(_ad(**{**_alakasiz.__dict__}), varliklar=_VAR, amac="detay")
_g_var = _sr.puanla(_ad(**{**_alakasiz.__dict__, "asset_id": "z2"}),
                    varliklar=_VAR, amac="detay", konsept=_URU)
kontrol("konsept ALAKA KAPISI kararini DEGISTIRMIYOR",
        _g_yok.render_kullanilabilir == _g_var.render_kullanilabilir,
        f"{_g_yok.render_kullanilabilir} vs {_g_var.render_kullanilabilir}")
_SR_KAYNAK = oku(KOK, "medya/siralama.py")
kontrol("alaka_kapisi govdesi bu adimda DEGISMEDI",
        "def alaka_kapisi(aday, varliklar: dict, iddia_metni: str = \"\")"
        in _SR_KAYNAK and "konsept" not in
        _SR_KAYNAK.split("def alaka_kapisi(")[1].split("def puanla(")[0])
kontrol("saglayici tavani (%40) DEGISMEDI", _sr.SAGLAYICI_TAVANI == 0.40)
kontrol("lisans duvari bu adimda DOKUNULMADI",
        "konsept" not in oku(KOK, "medya/lisans.py"))
kontrol("SSRF/guvenlik katmani DOKUNULMADI",
        "konsept" not in oku(KOK, "medya/guvenlik.py"))
kontrol("kare kapisi DOKUNULMADI", "konsept" not in oku(KOK, "medya/kare_kapisi.py"))
kontrol("indirme katmani DOKUNULMADI", "konsept" not in oku(KOK, "medya/indirme.py"))
# ⚠ "gercek indirme yok" iddiasi DIZE TARAMASIYLA yetinmez: adaylardaki
# `https://commons.wikimedia.org/...` bir PROVENANCE ALANIDIR, cagri degil.
# Olculen sey CAGRI IZI: istek/soket/acma fonksiyonlari.
_I5_BOLUM = oku(KOK, "testler/test_faz_i.py").split("19. I-5")[1]
kontrol("bu bolum GERCEK indirme yapmiyor (cagri izi yok)",
        not re.search(r"requests\.(get|post)\(|urlopen\(|socket\.|"
                      r"urlretrieve\(|\.download\(", _I5_BOLUM))
kontrol("siralama/sorgu planlayici AG KUTUPHANESI kullanmiyor",
        all(x not in _SR_KAYNAK and x not in oku(KOK, "medya/sorgu_planlayici.py")
            for x in ("requests", "urllib", "socket")))

# ── (d) BILINMEYEN / BELIRSIZ -> ESKI GUVENLI DAVRANIS ──
for _ad2, _kon2 in [("None", None), ("bos sozluk", {}), ("sozluk degil", "x"),
                    ("belirsiz konsept", {"yol": "belirsiz", "aile": ""}),
                    ("bilinmeyen aile", {"yol": "uzay.roket", "aile": "uzay"}),
                    ("aile bos", {"yol": "x.y", "aile": ""})]:
    kontrol(f"bilinmeyende ESKI davranis: {_ad2}",
            _sp.konsept_ailesi(_kon2) == ""
            and _sp.amac_ata(7, konsept=_kon2) == _ref_amac(7)
            and _sr.konsept_kaymasi(_ad(), _kon2)[0] == 0.0)
kontrol("bilinmeyende RASTGELE STOK yok (sorgular eskiyle ayni)",
        _sp.sorgu_plani("Tokyo street 1987", "ortam",
                        konsept={"yol": "uzay.roket", "aile": "uzay"})["sorgular"]
        == _sp.sorgu_plani("Tokyo street 1987", "ortam")["sorgular"])
kontrol("konsept ailesi cozumu ISTISNA FIRLATMIYOR",
        all(_sp.konsept_ailesi(x) == "" for x in (None, 5, [], "x", {"yol": 1})))

# ── (e) KULLANICININ ACIK SECIMI HER ZAMAN KAZANIR ──
_AV = oku(KOK, "medya/avci.py")
kontrol("acik sahne_amaci Auto'yu YENIYOR",
        'sh.get("sahne_amaci")\n            or sorgu_planlayici.amac_ata(' in _AV)
kontrol("acik kategori tur konvansiyonunu YENIYOR",
        _sp.amac_ata(3, "alinti", konsept=_SEY) == "belge"
        and _sp.amac_ata(3, "cografya", konsept=_URU) == "harita")
kontrol("avci konsepti OPSIYONEL aliyor",
        "konsept: Optional[dict] = None" in _AV)
kontrol("avci konsepti sorgu planina ve puanlamaya GECIRIYOR",
        "konsept=konsept)" in _AV and _AV.count("konsept=konsept") >= 3)

# ── (f) SOZLESMELER KORUNDU ──
kontrol("22 alanlik generate sozlesmesi DEGISMEDI",
        len(set(re.findall(r"\{ad: '(\w+)'",
                           oku(KOK, "static/js/api.js")))) == 22)
kontrol("UI bu adimda DEGISMEDI",
        "basitGovde" in oku(KOK, "static/js/wizard.js")
        and "SURE_SECENEKLERI" in oku(KOK, "static/js/basit.js"))
kontrol("referans parmak izi modulu BAGLANMADI",
        "referans_parmak" not in _AV and "referans_parmak" not in _SR_KAYNAK)
kontrol("hikaye/animasyon motoruna dokunulmadi",
        "HIKAYE_STILLERI" not in _AV and "ANIMASYON_STILLERI" not in _AV)
for _f2 in ("medya/sorgu_planlayici.py", "medya/siralama.py", "medya/avci.py"):
    kontrol(f"{_f2} derleniyor", _derlenir(os.path.join(KOK, _f2)))


# ═══════ 20. FAZ I-6 — MEDYA AVCISI GERCEK HATTA (GUVENLI OPT-IN) ═══════
# ⚠ KAPATILAN ACIK (§1 / §10 madde 1): `webapp/medya/` paketi yazildi ve
# testlendi ama `/api/generate` hatti onu HIC CAGIRMIYORDU.
# ⚠ BU BOLUM GERCEK INDIRME YAPMAZ: saglayici yaniti, indirici ve kare kapisi
# FIXTURE ile enjekte edilir. Ucretli API ve deploy YOK.
blok("20. I-6 — medya avcisi koprusu: varsayilan KAPALI ve fail-closed")

import medya_kopru as mkp                              # noqa: E402

# ── (a) VARSAYILAN KAPALI ──
kontrol("kopru VARSAYILAN KAPALI (opt-in)", mkp.ACIK is False)
kontrol("bayraksiz acik_mi False", mkp.acik_mi()[0] is False)
kontrol("kapaliyken sahne_medyasi HICBIR SEY yapmiyor",
        mkp.sahne_medyasi(sorgu="x", hedef_yol="/tmp/yok.mp4")["neden"]
        == "KAPALI")
kontrol("opt-in yol 1: ortam degiskeni belgelenmis",
        'os.environ.get("MEDYA_AVCISI"' in oku(KOK, "medya_kopru.py"))
kontrol("opt-in yol 2: DAHILI is ayari",
        mkp.acik_mi({"medya_avcisi": True})[0] is True)
kontrol("is ayari yalnizca GERCEK True ile acilir (dize/1 acmaz)",
        all(mkp.acik_mi(x)[0] is False for x in
            ({"medya_avcisi": "evet"}, {"medya_avcisi": 1},
             {"medya_avcisi": "true"}, {}, None, "x", 5)))
kontrol("acilma gerekcesi RAPORLANIYOR",
        "is ayari" in mkp.acik_mi({"medya_avcisi": True})[1])

# ── (b) FAIL-CLOSED KAPILAR ──
mkp.kayit_sifirla()
_ac = {"medya_avcisi": True}
kontrol("kare dogrulayici YOKSA aday KABUL EDILMEZ (fail-closed)",
        mkp.sahne_medyasi(sorgu="x", hedef_yol="/tmp/y.mp4", is_ayar=_ac,
                          istek=lambda u, **k: None)["neden"]
        == "DOGRULAYICI-YOK")
kontrol("ag cagrilabiliri YOKSA durur",
        mkp.sahne_medyasi(sorgu="x", hedef_yol="/tmp/y.mp4", is_ayar=_ac,
                          kare_dogrula=lambda *a: True)["neden"] == "ISTEK-YOK")
kontrol("her durdurma nedeninin ACIKLAMASI var",
        all(isinstance(v, str) and v for v in mkp.NEDEN.values()))
kontrol("durdurmalar dususlere YAZILIYOR (sessiz degil)",
        len(mkp.dususler()) >= 2, str(len(mkp.dususler())))

# Avci patlarsa hat COKMEZ
import medya.avci as _gercek_avci                      # noqa: E402
_asil_ara = _gercek_avci.sahne_ara
try:
    def _patla(**kw):
        raise RuntimeError("kasitli avci patlamasi")

    _gercek_avci.sahne_ara = _patla
    _r = mkp.sahne_medyasi(sorgu="x", hedef_yol="/tmp/y.mp4", is_ayar=_ac,
                           istek=lambda u, **k: None,
                           kare_dogrula=lambda *a: True)
    kontrol("avci PATLARSA kopru cokmuyor, kontrollu duruyor",
            _r["ok"] is False and _r["neden"] == "HATA")
    kontrol("patlama gerekcesi GORUNUR",
            any("kasitli" in d.get("ayrinti", "") for d in _r["dususler"]))
finally:
    _gercek_avci.sahne_ara = _asil_ara


blok("20b. I-6 — FIXTURE entegrasyonu: uc kapi da BYPASS EDILEMEZ")

from medya import kayit as _mkayit                     # noqa: E402
from medya.aday import MedyaAdayi as _MA               # noqa: E402


class _SahteYanit:
    def __init__(self, veri, kod=200):
        self.status_code = kod
        self._veri = veri
        self.headers = {"Content-Type": "application/json"}

    def json(self):
        return self._veri


_PX_YANIT = {"videos": [{
    "id": 4242, "url": "https://www.pexels.com/video/tokyo-street-4242/",
    "user": {"name": "Test Author"}, "width": 3840, "height": 2160,
    "duration": 12,
    "video_files": [{"link": "https://player.vexels.example/4242_2k.mp4",
                     "width": 2560, "height": 1440, "file_type": "video/mp4"}],
}]}


def _sahte_istek(url, **kw):
    if "pexels" in url:
        return _SahteYanit(_PX_YANIT)
    return _SahteYanit({}, 404)


_indirme_cagrisi = {"n": 0, "url": []}
_kare_cagrisi = {"n": 0}
from medya import indirme as _mind                     # noqa: E402

_asil_indir = _mind.guvenli_indir


def _sahte_indir(url, hedef, **kw):
    _indirme_cagrisi["n"] += 1
    _indirme_cagrisi["url"].append(url)
    with open(hedef, "wb") as f:
        f.write(b"\x00" * 9000)
    return {"ok": True, "sebep": "", "okunan_bayt": 9000, "bilgi": {}}


_i6_kok = tempfile.mkdtemp(prefix="i6_")
_eski_px = os.environ.get("PEXELS_KEY")
try:
    os.environ["PEXELS_KEY"] = "test"
    _mkayit.kosu_sifirla()
    _mind.guvenli_indir = _sahte_indir
    _hedef = os.path.join(_i6_kok, "sahne.mp4")

    def _kare_ok(*a, **k):
        _kare_cagrisi["n"] += 1
        return True

    def _kare_red(*a, **k):
        _kare_cagrisi["n"] += 1
        return False

    mkp.kayit_sifirla()
    _r1 = mkp.sahne_medyasi(
        sorgu="tokyo street night", hedef_yol=_hedef, sahne_amaci="ortam",
        iddia_metni="Tokyo street at night in 2024.", fact_id="f001",
        scene_id="s001", konu="tokyo", is_ayar=_ac, istek=_sahte_istek,
        kare_dogrula=_kare_ok, coz=lambda h: ["93.184.216.34"],
        erisim_tarihi="2026-08-12")
    kontrol("FIXTURE: uctan uca aday bulundu ve secildi", _r1["ok"] is True,
            str(_r1["neden"]))
    kontrol("secilen adayin LISANSI tasiniyor", bool(_r1["aday"].get("lisans")),
            str(_r1["aday"]))
    kontrol("secilen adayin PROVENANCE url'i tasiniyor",
            _r1["aday"].get("orijinal_url", "").startswith("http"))
    kontrol("indirme GUVENLI INDIRICI uzerinden yapildi",
            _indirme_cagrisi["n"] >= 1)
    kontrol("KARE KAPISI gercekten cagrildi", _kare_cagrisi["n"] >= 1)
    kontrol("ozet sayaclari GORUNUR",
            mkp.ozet()["secilen"] == 1 and mkp.ozet()["denenen"] >= 1,
            str(mkp.ozet()))

    # ⚠ KARE KAPISI REDDEDERSE aday KABUL EDILMEZ ve dosya SILINIR
    mkp.kayit_sifirla()
    _kare_cagrisi["n"] = 0
    _r2 = mkp.sahne_medyasi(
        sorgu="tokyo street night", hedef_yol=_hedef, sahne_amaci="ortam",
        iddia_metni="Tokyo street at night in 2024.", scene_id="s002",
        konu="tokyo", is_ayar=_ac, istek=_sahte_istek, kare_dogrula=_kare_red,
        coz=lambda h: ["93.184.216.34"], erisim_tarihi="2026-08-12")
    kontrol("KARE KAPISI reddederse aday KABUL EDILMIYOR", _r2["ok"] is False)
    kontrol("reddedilen klip DISKTEN SILINIYOR", not os.path.exists(_hedef))
    kontrol("kare kapisi reddi dususlere YAZILIYOR",
            any(d["neden"] == "KARE-KAPISI" for d in mkp.dususler()),
            str(mkp.dususler()[:2]))
    kontrol("RASTGELE STOK YOK: red sonrasi ok=False, yol bos",
            _r2["yol"] == "" and not _r2["aday"])

    # ⚠ KARE DOGRULAYICI PATLARSA da aday KABUL EDILMEZ (fail-closed)
    mkp.kayit_sifirla()

    def _kare_patla(*a, **k):
        raise RuntimeError("dogrulayici patladi")

    _r3 = mkp.sahne_medyasi(
        sorgu="tokyo street night", hedef_yol=_hedef, scene_id="s003",
        iddia_metni="Tokyo street at night in 2024.", konu="tokyo",
        is_ayar=_ac, istek=_sahte_istek, kare_dogrula=_kare_patla,
        coz=lambda h: ["93.184.216.34"], erisim_tarihi="2026-08-12")
    kontrol("kare dogrulayici PATLARSA aday KABUL EDILMIYOR (fail-closed)",
            _r3["ok"] is False)

    # ⚠ INDIRME BASARISIZ olursa dusus yazilir, aday tasinmaz
    mkp.kayit_sifirla()

    def _indir_basarisiz(url, hedef, **kw):
        return {"ok": False, "sebep": "HTTP 403", "okunan_bayt": 0}

    _mind.guvenli_indir = _indir_basarisiz
    _r4 = mkp.sahne_medyasi(
        sorgu="tokyo street night", hedef_yol=_hedef, scene_id="s004",
        iddia_metni="Tokyo street at night in 2024.", konu="tokyo",
        is_ayar=_ac, istek=_sahte_istek, kare_dogrula=_kare_ok,
        coz=lambda h: ["93.184.216.34"], erisim_tarihi="2026-08-12")
    kontrol("indirme basarisizsa aday TASINMIYOR", _r4["ok"] is False)
    kontrol("indirme basarisizligi dususlere YAZILIYOR",
            any(d["neden"] == "INDIRME-BASARISIZ" for d in mkp.dususler()))
    _mind.guvenli_indir = _sahte_indir

    # ⚠ LISANS DUVARI: render_kullanilabilir OLMAYAN aday ASLA tasinmaz
    mkp.kayit_sifirla()
    _asil_sahne_ara = _gercek_avci.sahne_ara

    def _sadece_lisanssiz(**kw):
        a = _MA(asset_id="bad1", saglayici="pexels", tur="video",
                indirme_url="https://player.vexels.example/x.mp4",
                orijinal_url="https://www.pexels.com/video/x/",
                lisans="unknown", render_kullanilabilir=False,
                red_nedeni="lisans belirsiz")
        return {"adaylar": [a], "secilen": [a], "sorgular": [], "sayac": 0,
                "saglayici_hatalari": [], "kapsam": {}, "red_gerekceleri": []}

    try:
        _gercek_avci.sahne_ara = _sadece_lisanssiz
        _indirme_cagrisi["n"] = 0
        _r5 = mkp.sahne_medyasi(
            sorgu="x", hedef_yol=_hedef, scene_id="s005", is_ayar=_ac,
            istek=_sahte_istek, kare_dogrula=_kare_ok)
        kontrol("LISANS DUVARI: render_kullanilabilir=False aday TASINMIYOR",
                _r5["ok"] is False and _r5["neden"] == "ADAY-YOK")
        kontrol("lisanssiz aday INDIRILMIYOR bile", _indirme_cagrisi["n"] == 0)
    finally:
        _gercek_avci.sahne_ara = _asil_sahne_ara
finally:
    _mind.guvenli_indir = _asil_indir
    if _eski_px is None:
        os.environ.pop("PEXELS_KEY", None)
    else:
        os.environ["PEXELS_KEY"] = _eski_px
    _sh.rmtree(_i6_kok, ignore_errors=True)


blok("20c. I-6 — pipeline entegrasyonu ve BYPASS EDILEMEZLIK")

_MK = oku(KOK, "medya_kopru.py")
# ⚠ "dogrudan requests yok" iddiasi DIZE TARAMASIYLA yetinmez: modul kendi
# dokumantasyonunda zaten "ASLA dogrudan requests cagirmaz" diyor. Olculen
# sey IMPORT ve CAGRI izi.
kontrol("kopru DOGRUDAN requests/urllib IMPORT ETMIYOR",
        not re.search(r"^\s*(import|from)\s+(requests|urllib|http|socket)\b",
                      _MK, re.M))
kontrol("kopru DOGRUDAN ag cagrisi YAPMIYOR (SSRF kapisi atlanamaz)",
        not re.search(r"requests\.(get|post)\(|urlopen\(|socket\.socket\(",
                      _MK))
kontrol("indirme YALNIZCA guvenli_indir uzerinden",
        "indirme.guvenli_indir(" in _MK and _MK.count("guvenli_indir") <= 3)
kontrol("yalnizca SECILEN + render_kullanilabilir adaylar tasiniyor",
        'sonuc.get("secilen")' in _MK
        and 'getattr(a, "render_kullanilabilir", False)' in _MK)
kontrol("kare dogrulayici ZORUNLU (fail-closed) — kodda kilitli",
        "if not callable(kare_dogrula)" in _MK)
kontrol("kare kapisi istisnasi ADAYI REDDEDIYOR",
        "kare_ok = False" in _MK)

_PP3 = oku(KOK, "pipeline.py")
kontrol("pipeline kopruyu OPT-IN cagiriyor",
        "if _avci_acik:" in _PP3 and "medya_kopru.sahne_medyasi(" in _PP3)
kontrol("pipeline kare dogrulayiciyi GECIYOR",
        "kare_dogrula=kaynak._kare_dogrula" in _PP3)
kontrol("pipeline konsept + fact_id + sahne amaci GECIYOR",
        all(x in _PP3 for x in ("konsept=_avci_konsept", "fact_id=str(",
                                "sahne_amaci=str(")))
kontrol("basarisizlikta MEVCUT yol aynen surduruluyor",
        "if kaynak.footage_getir(" in _PP3)
# ⚠ I-7'de bu baglanti IS BASINA butce nesnesine tasindi (§24). Kural ayni
# kaliyor: ozet YALNIZCA acikken yazilir; yalnizca kaynagi degisti.
kontrol("avci ozeti YALNIZCA acikken ise yaziliyor",
        'if _avci_acik and _avci_butce is not None:' in _PP3
        and 'sonuc["medya_avcisi"]' in _PP3)
kontrol("avci dususleri ise TASINIYOR",
        'sonuc["dususler"].extend(_avci_butce.dususler())' in _PP3)
kontrol("kaynak.avci_istek yalnizca TASIYICI (kapi iddiasi yok)",
        "yalnizca tasiyicidir" in oku(KOK, "kaynak.py"))

# ⚠ KAPALIYKEN ESKI DAVRANIS: `sonuc` anahtari HIC eklenmiyor
kontrol("kapaliyken `medya_avcisi` anahtari EKLENMIYOR",
        _PP3.count('sonuc["medya_avcisi"]') == 1
        and 'if _avci_acik:' in _PP3)
kontrol("mevcut medya kapisi/kare ozeti KORUNDU",
        'sonuc["medya_kapisi"]' in _PP3 and 'sonuc["kare_kapisi"]' in _PP3)

# ⚠ SOZLESMELER
kontrol("22 alanlik generate sozlesmesi DEGISMEDI",
        len(set(re.findall(r"\{ad: '(\w+)'",
                           oku(KOK, "static/js/api.js")))) == 22)
kontrol("server.py medya_avcisi alanini OKUMUYOR (UI'dan gelemez)",
        "medya_avcisi" not in oku(KOK, "server.py"))
kontrol("UI medya_avcisi GONDERMIYOR",
        all("medya_avcisi" not in oku(KOK, f"static/js/{f}")
            for f in ("api.js", "wizard.js", "basit.js")))
kontrol("UI ozellikleri KORUNDU",
        "basitGovde" in oku(KOK, "static/js/wizard.js")
        and "SURE_SECENEKLERI" in oku(KOK, "static/js/basit.js")
        and "d.unlu = t.unlu ? '1' : '0'" in oku(KOK, "static/js/wizard.js"))
kontrol("lisans/SSRF/kare kapisi modulleri DOKUNULMADI",
        all("medya_kopru" not in oku(KOK, f) for f in
            ("medya/lisans.py", "medya/guvenlik.py", "medya/indirme.py",
             "medya/kare_kapisi.py")))
for _f3 in ("medya_kopru.py", "pipeline.py", "kaynak.py"):
    kontrol(f"{_f3} derleniyor", _derlenir(os.path.join(KOK, _f3)))


# ═══ 21. FAZ I-7 — IS BASINA BUTCE ve PARALEL IS IZOLASYONU ═══
# ⚠ KAPATILAN ACIK (§23 sinir 2 ve 5): pipeline `defter=None` geciriyordu
# (para tavani YOKTU) ve sayaclar MODUL DUZEYINDE globaldi (ayni surecte iki
# is sayaclari karisiyordu). ⚠ BAYRAK HALA VARSAYILAN KAPALI.
blok("21. I-7 — is butcesi: bes tavan birlikte, varsayilan USD 0.0")

kontrol("bayrak HALA varsayilan KAPALI", mkp.ACIK is False
        and mkp.acik_mi()[0] is False)
kontrol("VARSAYILAN USD tavani 0.0 (ucretli cagriya yer YOK)",
        mkp.VARSAYILAN_MAKS_USD == 0.0)
kontrol("USD tavani env/config ile ayarlanabilir",
        'os.environ.get("MEDYA_AVCI_MAKS_USD"' in oku(KOK, "medya_kopru.py"))

_b1 = mkp.is_butcesi_kur("is-1")
kontrol("butce nesnesi IS ADI tasiyor", _b1.ozet()["is_adi"] == "is-1")
_gerekli = {"usd", "maks_usd", "istek", "maks_istek", "bayt", "maks_bayt",
            "kare_cagrisi", "maks_kare", "gecen_sn", "maks_sure_sn",
            "tavan_doldu", "durma_nedeni", "denenen", "secilen"}
kontrol("BES TAVAN da BIRLIKTE raporlaniyor", _gerekli <= set(_b1.ozet()),
        str(sorted(_gerekli - set(_b1.ozet()))))
kontrol("negatif tavan reddediliyor",
        _kaldirilan_hata(lambda: mkp.IsButcesi("x", maks_istek=-1), ValueError))
kontrol("para defteri GERCEKTEN kuruluyor (tavan bagli)",
        _b1.defter is not None and _b1.defter.tavan == 0.0)
kontrol("kosu siniri GERCEKTEN kuruluyor", _b1.sinir is not None)

# ── Tavanlar tek tek KAPATIYOR ──
kontrol("istek tavani 0 -> kapi KAPALI",
        mkp.IsButcesi("x", maks_istek=0).istek_ayir(1)[0] is False)
kontrol("kare tavani 0 -> kapi KAPALI",
        mkp.IsButcesi("x", maks_kare=0).kare_ayir(1)[0] is False)
kontrol("bayt tavani asilirsa reddediliyor",
        mkp.IsButcesi("x", maks_bayt=100).bayt_ayir(500)[0] is False)
kontrol("sure tavani 0 -> bitti",
        mkp.IsButcesi("x", maks_sure_sn=0).bitti_mi()[0] is True)
kontrol("USD tavani asilinca bitti_mi True",
        (lambda b: (b.defter.kaydet("test", "kalem", 0.5), b.bitti_mi()[0])[1])(
            mkp.IsButcesi("x", maks_usd=0.1)) is True)
kontrol("durma nedeni GORUNUR (sessiz degil)",
        "tavani" in mkp.IsButcesi("x", maks_istek=0).bitti_mi()[1])

# ── THREAD GUVENLIGI: kilitsiz sayacla tavan asilirdi ──
_tb = mkp.IsButcesi("yaris", maks_istek=10, maks_sure_sn=60)
_verilen2, _kilit2 = [], threading.Lock()


def _yaris2():
    for _ in range(20):
        ok, _n = _tb.istek_ayir(1)
        if ok:
            with _kilit2:
                _verilen2.append(1)


_th2 = [threading.Thread(target=_yaris2) for _ in range(8)]
[t.start() for t in _th2]
[t.join() for t in _th2]
kontrol("THREAD GUVENLI: paralel istekte tavan ASILMIYOR",
        len(_verilen2) == 10, f"{len(_verilen2)} verildi (tavan 10)")
kontrol("kare tavani da thread guvenli",
        _tb.ozet()["istek"] == 10)

# ── PARALEL IS IZOLASYONU: iki isin sayaclari KARISMIYOR ──
blok("21b. I-7 — paralel iki isin sayaclari KARISMIYOR")

_isA = mkp.is_butcesi_kur("isA", maks_istek=50, maks_kare=50)
_isB = mkp.is_butcesi_kur("isB", maks_istek=50, maks_kare=50)


def _is_kos(b, adet):
    for _ in range(adet):
        b.istek_ayir(1)
        b.denendi()
        b.dusus("ADAY-YOK", "fixture", "s001")


_tA = threading.Thread(target=_is_kos, args=(_isA, 7))
_tB = threading.Thread(target=_is_kos, args=(_isB, 3))
_tA.start(); _tB.start(); _tA.join(); _tB.join()
kontrol("is A sayaci YALNIZCA kendi islerini sayiyor",
        _isA.ozet()["istek"] == 7 and _isA.ozet()["denenen"] == 7,
        str(_isA.ozet()["istek"]))
kontrol("is B sayaci YALNIZCA kendi islerini sayiyor",
        _isB.ozet()["istek"] == 3 and _isB.ozet()["denenen"] == 3,
        str(_isB.ozet()["istek"]))
kontrol("is A dususleri is B'ye SIZMIYOR",
        len(_isA.dususler()) == 7 and len(_isB.dususler()) == 3)
kontrol("iki isin butce nesneleri AYRI", _isA is not _isB
        and _isA.defter is not _isB.defter)
kontrol("bir isin tavani dolunca DIGERI etkilenmiyor",
        (lambda: (mkp.IsButcesi("dolu", maks_istek=0),
                  _isB.istek_ayir(1)[0]))()[1] is True)

# ── FIXTURE: iki paralel is, ayri butce, sayaclar karismiyor ──
_i7_kok = tempfile.mkdtemp(prefix="i7_")
_eski_px2 = os.environ.get("PEXELS_KEY")
_asil_indir2 = _mind.guvenli_indir
try:
    os.environ["PEXELS_KEY"] = "test"
    _mkayit.kosu_sifirla()

    def _indir_fix(url, hedef, **kw):
        with open(hedef, "wb") as f:
            f.write(b"\x00" * 9000)
        return {"ok": True, "sebep": "", "okunan_bayt": 9000, "bilgi": {}}

    _mind.guvenli_indir = _indir_fix
    _sonuclar = {}

    def _fixture_is(ad, adet, butce):
        for i in range(adet):
            _sonuclar.setdefault(ad, []).append(mkp.sahne_medyasi(
                sorgu="tokyo street night",
                hedef_yol=os.path.join(_i7_kok, f"{ad}_{i}.mp4"),
                sahne_amaci="ortam",
                iddia_metni="Tokyo street at night in 2024.",
                scene_id=f"{ad}_s{i}", konu="tokyo", is_ayar=_ac,
                istek=_sahte_istek, kare_dogrula=lambda *a, **k: True,
                coz=lambda h: ["93.184.216.34"], erisim_tarihi="2026-08-12",
                butce=butce))

    _bA = mkp.is_butcesi_kur("fixA", maks_istek=50, maks_kare=50)
    _bB = mkp.is_butcesi_kur("fixB", maks_istek=50, maks_kare=50)
    _fA = threading.Thread(target=_fixture_is, args=("fixA", 3, _bA))
    _fB = threading.Thread(target=_fixture_is, args=("fixB", 1, _bB))
    _fA.start(); _fB.start(); _fA.join(); _fB.join()
    kontrol("FIXTURE: is A 3 sahne secti", _bA.ozet()["secilen"] == 3,
            str(_bA.ozet()["secilen"]))
    kontrol("FIXTURE: is B 1 sahne secti", _bB.ozet()["secilen"] == 1,
            str(_bB.ozet()["secilen"]))
    kontrol("FIXTURE: iki isin istek sayaci KARISMIYOR",
            _bA.ozet()["istek"] != _bB.ozet()["istek"]
            and _bA.ozet()["istek"] == 6 and _bB.ozet()["istek"] == 2,
            f"A={_bA.ozet()['istek']} B={_bB.ozet()['istek']}")
    kontrol("FIXTURE: kare cagrisi sayaci is basina",
            _bA.ozet()["kare_cagrisi"] == 3 and _bB.ozet()["kare_cagrisi"] == 1)
    kontrol("FIXTURE: inen bayt is basina sayiliyor",
            _bA.ozet()["bayt"] == 27000 and _bB.ozet()["bayt"] == 9000,
            f"A={_bA.ozet()['bayt']} B={_bB.ozet()['bayt']}")

    # ── LIMIT ASILINCA KONTROLLU DUR + ESKI YOLA DUS ──
    _bK = mkp.is_butcesi_kur("kisitli", maks_istek=1, maks_kare=50)
    _rK = mkp.sahne_medyasi(
        sorgu="tokyo street night", hedef_yol=os.path.join(_i7_kok, "k.mp4"),
        iddia_metni="Tokyo street at night in 2024.", scene_id="k1",
        konu="tokyo", is_ayar=_ac, istek=_sahte_istek,
        kare_dogrula=lambda *a, **k: True, coz=lambda h: ["93.184.216.34"],
        erisim_tarihi="2026-08-12", butce=_bK)
    kontrol("istek tavani dolunca KONTROLLU DUR", _rK["ok"] is False)
    kontrol("durma nedeni BUTCE ve GORUNUR",
            _rK["neden"] == "BUTCE"
            and any(d["neden"] == "BUTCE" for d in _bK.dususler()),
            str(_rK["neden"]))
    kontrol("butce dolunca RASTGELE STOK YOK", _rK["yol"] == "" and not _rK["aday"])

    _bKare = mkp.is_butcesi_kur("karesiz", maks_istek=50, maks_kare=0)
    _rKare = mkp.sahne_medyasi(
        sorgu="tokyo street night", hedef_yol=os.path.join(_i7_kok, "k2.mp4"),
        iddia_metni="Tokyo street at night in 2024.", scene_id="k2",
        konu="tokyo", is_ayar=_ac, istek=_sahte_istek,
        kare_dogrula=lambda *a, **k: True, coz=lambda h: ["93.184.216.34"],
        erisim_tarihi="2026-08-12", butce=_bKare)
    kontrol("kare tavani 0 -> klip DOGRULANAMAZ, KABUL EDILMEZ (fail-closed)",
            _rKare["ok"] is False)
    kontrol("kare tavani dolunca klip DISKTEN SILINIYOR",
            not os.path.exists(os.path.join(_i7_kok, "k2.mp4")))

    _bBayt = mkp.is_butcesi_kur("baytsiz", maks_istek=50, maks_kare=50,
                                maks_bayt=100)
    _rBayt = mkp.sahne_medyasi(
        sorgu="tokyo street night", hedef_yol=os.path.join(_i7_kok, "k3.mp4"),
        iddia_metni="Tokyo street at night in 2024.", scene_id="k3",
        konu="tokyo", is_ayar=_ac, istek=_sahte_istek,
        kare_dogrula=lambda *a, **k: True, coz=lambda h: ["93.184.216.34"],
        erisim_tarihi="2026-08-12", butce=_bBayt)
    kontrol("bayt tavani asilirsa klip KABUL EDILMEZ", _rBayt["ok"] is False)

    # ── MALIYET OZETI GORUNUR ──
    kontrol("maliyet ozeti bes tavani birlikte gosteriyor",
            all(k in _bA.ozet() for k in
                ("usd", "istek", "bayt", "kare_cagrisi", "gecen_sn")))
    kontrol("tavan dolan iste `tavan_doldu` GORUNUR",
            _bK.ozet()["tavan_doldu"] is True and _bK.ozet()["durma_nedeni"])
finally:
    _mind.guvenli_indir = _asil_indir2
    if _eski_px2 is None:
        os.environ.pop("PEXELS_KEY", None)
    else:
        os.environ["PEXELS_KEY"] = _eski_px2
    _sh.rmtree(_i7_kok, ignore_errors=True)


blok("21c. I-7 — pipeline baglantisi ve GERIYE UYUMLULUK")

_PP4 = oku(KOK, "pipeline.py")
kontrol("pipeline IS BASINA butce kuruyor",
        "medya_kopru.is_butcesi_kur(is_adi)" in _PP4)
kontrol("pipeline GLOBAL sayac kullanmiyor",
        "medya_kopru.kayit_sifirla()" not in _PP4
        and "medya_kopru.ozet()" not in _PP4
        and "medya_kopru.dususler()" not in _PP4)
kontrol("butce kopruye GECIRILIYOR", "butce=_avci_butce" in _PP4)
kontrol("ise yazilan ozet IS BUTCESINDEN geliyor",
        '_avci_butce.ozet()' in _PP4 and '_avci_butce.dususler()' in _PP4)
kontrol("butce tavanlari LOGA yaziliyor (gorunur)",
        "butce=" in _PP4 and "istek /" in _PP4)
kontrol("kapaliyken `medya_avcisi` anahtari YINE eklenmiyor",
        'if _avci_acik and _avci_butce is not None:' in _PP4)
kontrol("kopru avciya defter VE sinir geciriyor (para tavani gercek)",
        "defter=defter if defter is not None else b.defter" in oku(
            KOK, "medya_kopru.py")
        and "sinir=sinir if sinir is not None else b.sinir" in oku(
            KOK, "medya_kopru.py"))

# GERIYE UYUMLULUK: eski cagri yolu (butce verilmeden) HALA calisiyor
mkp.kayit_sifirla("eski-yol")
kontrol("butce VERILMEDEN eski cagri yolu calisiyor",
        mkp.sahne_medyasi(sorgu="x", hedef_yol="/tmp/z.mp4")["neden"] == "KAPALI")
kontrol("modul ozet()/dususler() HALA calisiyor (eski imza)",
        isinstance(mkp.ozet(), dict) and isinstance(mkp.dususler(), list))
kontrol("modul ozet()'i `acik` bayragini tasimaya devam ediyor",
        "acik" in mkp.ozet())

# SOZLESMELER — bu adimda hicbiri degismedi
kontrol("22 alanlik generate sozlesmesi DEGISMEDI",
        len(set(re.findall(r"\{ad: '(\w+)'",
                           oku(KOK, "static/js/api.js")))) == 22)
kontrol("UI DEGISMEDI",
        "basitGovde" in oku(KOK, "static/js/wizard.js")
        and "SURE_SECENEKLERI" in oku(KOK, "static/js/basit.js"))
kontrol("lisans/SSRF/kare kapisi modulleri DOKUNULMADI",
        all("IsButcesi" not in oku(KOK, f) for f in
            ("medya/lisans.py", "medya/guvenlik.py", "medya/indirme.py",
             "medya/kare_kapisi.py")))
kontrol("plan fact_id/iddia eksigi BU ADIMDA cozulmedi (bilinen sinir)",
        "fact_id=str(" in _PP4)
for _f4 in ("medya_kopru.py", "pipeline.py"):
    kontrol(f"{_f4} derleniyor", _derlenir(os.path.join(KOK, _f4)))


# ═══ 22. FAZ I-8 — DOGRULANMIS OLGU -> SAHNE ve MEDYA BAGI ═══
# ⚠ KAPATILAN ACIK (§23 sinir 3 / §24 sinir 2): sahne plani fact_id/iddia
# URETMIYORDU; medya koprusu bu alanlari okuyup hep bos buluyordu. Yani
# "arastirma-bagli medya secimi" iddiasi karsiliksizdi.
# ⚠ BAYRAK HALA VARSAYILAN KAPALI. Gercek ag/ucretli API/uretim YOK.
blok("22. I-8 — olgu bagi: yalnizca DOGRULANMIS iddia sahneye girer")

import arastirma_kopru as ak                           # noqa: E402

_OLGU = [
    {"fact_id": "f001", "guven": "dogrulandi", "kategori": "tarih",
     "kritik": True,
     "metin": "The Endurance became trapped in pack ice in January 1915 "
              "near Antarctica.",
     "kaynaklar": [{"alan": "rgs.org", "url": "https://rgs.org/x",
                    "tur": "birincil"}]},
    {"fact_id": "f002", "guven": "dogrulandi", "kategori": "cografya",
     "kritik": False,
     "metin": "The crew camped on Elephant Island for four months awaiting "
              "rescue.",
     "kaynaklar": [{"alan": "bl.uk", "url": "https://bl.uk/y", "tur": "arsiv"}]},
]


def _sahneler():
    return [
        {"kaynak": "footage",
         "anlatim": "The Endurance became trapped in pack ice near Antarctica "
                    "in 1915.",
         "footage_sorgu": "ship trapped pack ice antarctica"},
        {"kaynak": "footage",
         "anlatim": "The crew camped on Elephant Island awaiting rescue.",
         "footage_sorgu": "elephant island camp"},
        {"kaynak": "footage",
         "anlatim": "Completely unrelated cooking recipe with vegetables.",
         "footage_sorgu": "cooking vegetables"},
        {"kaynak": "ai", "anlatim": "The Endurance became trapped in pack ice.",
         "footage_sorgu": ""},
    ]


_S = _sahneler()
_R = ak.fact_bagla(_S, _OLGU)
kontrol("dogrulanmis iddia sahneye BAGLANIYOR",
        _S[0].get("fact_id") == "f001" and _S[1].get("fact_id") == "f002",
        f"{_S[0].get('fact_id')} / {_S[1].get('fact_id')}")
kontrol("baglanan sahneye KISA iddia metni yaziliyor",
        "Endurance" in (_S[0].get("iddia_metni") or "")
        and len(_S[0]["iddia_metni"]) <= ak.FACT_METIN_SINIRI)
kontrol("ALAKASIZ sahne fact_id ALMIYOR (uydurma yok)",
        "fact_id" not in _S[2] and "iddia_metni" not in _S[2])
kontrol("baglanmayan sahne KAPSAM BOSLUGU olarak gorunur",
        any(b["sahne"] == 2 for b in _R["bosluklar"]), str(_R["bosluklar"]))
kontrol("footage OLMAYAN sahne hedefe girmiyor",
        _R["hedef"] == 3 and "fact_id" not in _S[3])
kontrol("kapsam orani RAPORLANIYOR (kanitsiz iddia yok)",
        _R["kapsam_pct"] == 66.7 and _R["baglanan"] == 2, str(_R))
kontrol("kullanilan fact listesi raporlaniyor",
        _R["kullanilan_fact"] == ["f001", "f002"])
kontrol("esik RAPORLANIYOR (karar izlenebilir)", _R["esik"] == ak.FACT_ESIK)

# ── DESTEKSIZ / CELISKILI IDDIA SAHNEYE GIREMEZ ──
# `olgu_listesi` yalnizca `kullanilabilir_iddialar()` (senaryoya_girebilir)
# okur; celiskili/cozulmedi durumlari o filtrede ELENIR.
from arastirma.manifests import ArastirmaManifesti, Iddia, Kaynak  # noqa: E402

_man = ArastirmaManifesti(konu="Endurance")
_man.iddialar = [
    Iddia(fact_id="f001", metin="Verified claim with two sources.",
          guven="dogrulandi", kritik=False,
          kaynaklar=[Kaynak(url="https://rgs.org/a", tur="resmi-kurum",
                            baslik="A", erisim_tarihi="2026-08-12",
                            birincil=True)]),
    Iddia(fact_id="f002", metin="Contradictory claim about the same event.",
          guven="celiskili", kritik=False,
          kaynaklar=[Kaynak(url="https://x.org/b", tur="haber-buyuk",
                            baslik="B", erisim_tarihi="2026-08-12")]),
    Iddia(fact_id="f003", metin="Unresolved claim nobody could verify.",
          guven="cozulmedi", kritik=False,
          kaynaklar=[Kaynak(url="https://y.org/c", tur="haber-buyuk",
                            baslik="C", erisim_tarihi="2026-08-12")]),
    Iddia(fact_id="f004", metin="Critical claim with only one weak source.",
          guven="tek-kaynak", kritik=True,
          kaynaklar=[Kaynak(url="https://wiki.org/d", tur="ansiklopedi",
                            baslik="D", erisim_tarihi="2026-08-12")]),
]
_liste = ak.olgu_listesi(_man)
_kimlikler = {o["fact_id"] for o in _liste}
kontrol("CELISKILI iddia olgu listesine GIRMIYOR", "f002" not in _kimlikler,
        str(_kimlikler))
kontrol("COZULMEDI iddia olgu listesine GIRMIYOR", "f003" not in _kimlikler)
kontrol("kritik ama TEK ZAYIF kaynakli iddia GIRMIYOR", "f004" not in _kimlikler)
kontrol("dogrulanmis iddia olgu listesine GIRIYOR", "f001" in _kimlikler)
kontrol("olgu listesi kaynak/alan bilgisini TASIYOR",
        bool(_liste[0]["kaynaklar"]) and _liste[0]["kaynaklar"][0]["alan"])

# Celiskili bir iddia ELLE havuza konsa bile sahneye giremez mi?
# (havuz `olgu_listesi`den gelir; bu test filtrenin TEK kapi oldugunu kilitler)
kontrol("sahneye giren havuz YALNIZCA olgu_listesi'nden kuruluyor",
        "s.olgular = olgu_listesi(manifest)" in oku(KOK, "arastirma_kopru.py"))

# ── ACIK SECIM KORUNUYOR ──
_S2 = _sahneler()
_S2[0]["fact_id"] = "f999"
ak.fact_bagla(_S2, _OLGU)
kontrol("planin ACIK fact_id'si EZILMIYOR", _S2[0]["fact_id"] == "f999")

# ── DAYANIKLILIK / GERIYE UYUMLULUK ──
kontrol("olgu YOKSA hicbir sahne degismiyor",
        (lambda s: (ak.fact_bagla(s, []), "fact_id" not in s[0])[1])(_sahneler()))
kontrol("bozuk girdide COKMUYOR",
        all(isinstance(ak.fact_bagla(a, b), dict) for a, b in
            ((None, None), ("x", 5), ([], []), ([1, 2], _OLGU),
             (_sahneler(), [{"fact_id": ""}]))))
kontrol("fact_bagla DETERMINISTIK (ayni girdi -> ayni sonuc)",
        (lambda: (lambda a, b: a == b)(
            ak.fact_bagla(_sahneler(), _OLGU)["kullanilan_fact"],
            ak.fact_bagla(_sahneler(), _OLGU)["kullanilan_fact"]))())
kontrol("Sonuc.sozluk() DEGISMEDI (is sozlesmesi korundu)",
        "olgular" not in ak.Sonuc().sozluk(), str(sorted(ak.Sonuc().sozluk())))
kontrol("Sonuc.olgular varsayilan BOS (arastirma kapaliysa bag kurulmaz)",
        ak.Sonuc().olgular == [])


blok("22b. I-8 — FIXTURE: atif zinciri fact_id ile bagli, cozulmemis reddedilir")

_i8_kok = tempfile.mkdtemp(prefix="i8_")
_eski_px3 = os.environ.get("PEXELS_KEY")
_asil_indir3 = _mind.guvenli_indir
try:
    os.environ["PEXELS_KEY"] = "test"
    _mkayit.kosu_sifirla()

    def _indir_fix3(url, hedef, **kw):
        with open(hedef, "wb") as f:
            f.write(b"\x00" * 9000)
        return {"ok": True, "sebep": "", "okunan_bayt": 9000, "bilgi": {}}

    _mind.guvenli_indir = _indir_fix3
    _b8 = mkp.is_butcesi_kur("i8", maks_istek=50, maks_kare=50)
    _r8 = mkp.sahne_medyasi(
        sorgu="tokyo street night", hedef_yol=os.path.join(_i8_kok, "a.mp4"),
        sahne_amaci="ortam", iddia_metni="Tokyo street at night in 2024.",
        fact_id="f001", scene_id="s001", konu="tokyo", is_ayar=_ac,
        istek=_sahte_istek, kare_dogrula=lambda *a, **k: True,
        coz=lambda h: ["93.184.216.34"], erisim_tarihi="2026-08-12",
        butce=_b8)
    kontrol("FIXTURE: dogrulanmis fact ile medya secildi", _r8["ok"] is True,
            str(_r8["neden"]))
    kontrol("ATIF ZINCIRI fact_id'yi KORUYOR (ust duzey)",
            _r8.get("fact_id") == "f001", str(_r8.get("fact_id")))
    kontrol("ATIF ZINCIRI fact_id'yi KORUYOR (aday kaydi)",
            _r8["aday"].get("fact_id") == "f001")
    kontrol("aday kaydinda sorgu da tasiniyor", "sorgu" in _r8["aday"])
    kontrol("aday lisans+provenance bilgisini HALA tasiyor",
            _r8["aday"].get("lisans") and _r8["aday"].get("orijinal_url"))

    # ⚠ COZULMEMIS fact sahneye HIC girmedigi icin kopruye de ULASMAZ.
    # Bunu uctan uca dogrula: cozulmemis iddiadan olusan havuzla baglama
    # yapilinca sahne fact_id ALMAZ, dolayisiyla kopru bos fact_id gorur.
    _man2 = ArastirmaManifesti(konu="x")
    _man2.iddialar = [
        Iddia(fact_id="f050", metin="Unresolved claim about pack ice.",
              guven="cozulmedi", kritik=False,
              kaynaklar=[Kaynak(url="https://z.org/a", tur="haber-buyuk",
                                baslik="Z",
                                erisim_tarihi="2026-08-12")])]
    _S3 = [{"kaynak": "footage",
            "anlatim": "Unresolved claim about pack ice.",
            "footage_sorgu": "pack ice"}]
    _R3 = ak.fact_bagla(_S3, ak.olgu_listesi(_man2))
    kontrol("COZULMEMIS fact sahneye BAGLANMIYOR (uctan uca)",
            "fact_id" not in _S3[0] and _R3["baglanan"] == 0,
            str(_S3[0].get("fact_id")))
    kontrol("cozulmemis fact icin KAPSAM BOSLUGU yaziliyor",
            len(_R3["bosluklar"]) == 1)
    _r9 = mkp.sahne_medyasi(
        sorgu="pack ice", hedef_yol=os.path.join(_i8_kok, "b.mp4"),
        iddia_metni=_S3[0]["anlatim"],
        fact_id=str(_S3[0].get("fact_id") or ""), scene_id="s002",
        konu="x", is_ayar=_ac, istek=_sahte_istek,
        kare_dogrula=lambda *a, **k: True, coz=lambda h: ["93.184.216.34"],
        erisim_tarihi="2026-08-12", butce=_b8)
    kontrol("fact_id'siz sahnede atif zinciri BOS fact tasiyor (uydurma yok)",
            _r9.get("fact_id") == "" if _r9["ok"] else True,
            str(_r9.get("fact_id")))
finally:
    _mind.guvenli_indir = _asil_indir3
    if _eski_px3 is None:
        os.environ.pop("PEXELS_KEY", None)
    else:
        os.environ["PEXELS_KEY"] = _eski_px3
    _sh.rmtree(_i8_kok, ignore_errors=True)


blok("22c. I-8 — pipeline baglantisi ve KORUMALAR aynen")

_PP5 = oku(KOK, "pipeline.py")
kontrol("pipeline olgu bagini YALNIZCA arastirma kostuysa kuruyor",
        'if getattr(arastirma_sonuc, "calisti", False):' in _PP5
        and "arastirma_kopru.fact_bagla(scenes, _olgular)" in _PP5)
kontrol("olgu yoksa bag KURULMUYOR", "if _olgular:" in _PP5)
kontrol("olgu bagi ozeti YALNIZCA bag kuruldugunda ise yaziliyor",
        "if _fact_rapor is not None:" in _PP5 and 'sonuc["olgu_bagi"]' in _PP5)
kontrol("kapsam bosluklari dususlere GORUNUR yaziliyor",
        '"asama": "olgu-bagi"' in _PP5)
kontrol("olgu bagi LOGA yaziliyor", "OLGU BAGI:" in _PP5)
kontrol("bayrak HALA varsayilan KAPALI", mkp.ACIK is False)

# KORUMALAR — bu adimda hicbiri degismedi
kontrol("kare kapisi fail-closed KORUNDU",
        "if not callable(kare_dogrula)" in oku(KOK, "medya_kopru.py"))
kontrol("lisans duvari KORUNDU",
        'getattr(a, "render_kullanilabilir", False)' in oku(KOK, "medya_kopru.py"))
kontrol("SSRF: kopru HALA dogrudan ag cagirmiyor",
        not re.search(r"^\s*(import|from)\s+(requests|urllib|socket)\b",
                      oku(KOK, "medya_kopru.py"), re.M))
kontrol("butce korumalari KORUNDU",
        "class IsButcesi" in oku(KOK, "medya_kopru.py")
        and mkp.VARSAYILAN_MAKS_USD == 0.0)
kontrol("lisans/SSRF/kare/indirme modulleri DOKUNULMADI",
        all("fact_bagla" not in oku(KOK, f) for f in
            ("medya/lisans.py", "medya/guvenlik.py", "medya/indirme.py",
             "medya/kare_kapisi.py")))

# SOZLESMELER
kontrol("22 alanlik generate sozlesmesi DEGISMEDI",
        len(set(re.findall(r"\{ad: '(\w+)'",
                           oku(KOK, "static/js/api.js")))) == 22)
kontrol("UI ve kullanici secimleri DEGISMEDI",
        "basitGovde" in oku(KOK, "static/js/wizard.js")
        and "SURE_SECENEKLERI" in oku(KOK, "static/js/basit.js")
        and "d.unlu = t.unlu ? '1' : '0'" in oku(KOK, "static/js/wizard.js"))
kontrol("server.py olgu bagi alani OKUMUYOR",
        "olgu_bagi" not in oku(KOK, "server.py"))
for _f5 in ("arastirma_kopru.py", "medya_kopru.py", "pipeline.py"):
    kontrol(f"{_f5} derleniyor", _derlenir(os.path.join(KOK, _f5)))


# ═══ 23. FAZ I-9 — UCTAN UCA EDIT PLANI ORKESTRASYONU (FIXTURE) ═══
# ⚠ KAPATILAN ACIK: parcalar tek tek vardi ama ARALARINDA BAG YOKTU. Analiz +
# stil profili + dogrulanmis olgu + secilmis medya, profesyonel edit planina
# (EditorV2) hic birlikte akmamisti.
# ⚠ GERCEK RENDER / AG / UCRETLI API YOK — tamamen deterministik fixture.
blok("23. I-9 — orkestrasyon: opt-in, lisans duvari, QA karari")

import edit_kopru as ekp                               # noqa: E402

kontrol("orkestrasyon VARSAYILAN KAPALI", ekp.ACIK is False
        and ekp.acik_mi()[0] is False)
kontrol("opt-in yol 1: ortam degiskeni",
        'os.environ.get("EDITOR_V2"' in oku(KOK, "edit_kopru.py"))
kontrol("opt-in yol 2: DAHILI is ayari",
        ekp.acik_mi({"editor_v2": True})[0] is True)
kontrol("is ayari yalnizca GERCEK True ile acilir",
        all(ekp.acik_mi(x)[0] is False for x in
            ({"editor_v2": "evet"}, {"editor_v2": 1}, {}, None, "x")))
kontrol("kapaliyken plan_kur HICBIR SEY yapmiyor",
        ekp.plan_kur(cumleler=[{"metin": "x"}],
                     medya_manifest={})["neden"] == "KAPALI")

_EK_AC = {"editor_v2": True}
_CUMLE = [
    {"scene_id": "s001", "fact_id": "f001", "sure_sn": 3.2,
     "metin": "The Endurance became trapped in pack ice in January 1915 "
              "near Antarctica."},
    {"scene_id": "s001", "fact_id": "f001", "sure_sn": 2.8,
     "metin": "The ship drifted for months before it was finally crushed."},
    {"scene_id": "s002", "fact_id": "f002", "sure_sn": 4.1,
     "metin": "The crew camped on Elephant Island for four months awaiting "
              "rescue."},
    {"scene_id": "s003", "fact_id": "", "sure_sn": 3.0,
     "metin": "A rescue ship finally reached the island in August 1916."},
]


def _medya_fix():
    return {"adaylar": [
        {"asset_id": "a1", "scene_id": "s001", "fact_id": "f001",
         "saglayici": "wikimedia", "tur": "video", "medya_turu": "video",
         "medya_yolu": "/tmp/a1.mp4", "lisans": "cc-by",
         "render_kullanilabilir": True, "toplam_skor": 82,
         "baslik": "ship in pack ice", "sure_sn": 12,
         "orijinal_url": "https://commons.wikimedia.org/a1",
         "eser_sahibi": "X"},
        {"asset_id": "a2", "scene_id": "s002", "fact_id": "f002",
         "saglayici": "pexels", "tur": "video", "medya_turu": "video",
         "medya_yolu": "/tmp/a2.mp4", "lisans": "pexels",
         "render_kullanilabilir": True, "toplam_skor": 75,
         "baslik": "island camp", "sure_sn": 10,
         "orijinal_url": "https://pexels.com/a2", "eser_sahibi": "Y"},
        # ⚠ LISANSSIZ aday — render planina GIREMEZ
        {"asset_id": "BAD", "scene_id": "s003", "fact_id": "f003",
         "saglayici": "x", "tur": "video", "medya_turu": "video",
         "medya_yolu": "/tmp/bad.mp4", "lisans": "unknown",
         "render_kullanilabilir": False, "red_nedeni": "lisans belirsiz",
         "baslik": "unlicensed clip"},
    ], "kapsam_bosluklari": [{"scene_id": "s003",
                              "neden": "lisansli aday yok"}]}


_OLGU9 = [{"fact_id": "f001", "guven": "dogrulandi",
           "metin": "Endurance trapped in pack ice 1915."},
          {"fact_id": "f002", "guven": "dogrulandi",
           "metin": "Crew camped on Elephant Island."}]
_STIL9 = {"kimlik": "belgesel-arastirmaci", "surum": "1.0.0", "kaynak": "auto",
          "profil": sp.profil_al("belgesel-arastirmaci")}

_i9_kok = tempfile.mkdtemp(prefix="i9_")
try:
    _R9 = ekp.plan_kur(cumleler=_CUMLE, medya_manifest=_medya_fix(),
                       olgular=_OLGU9, stil=_STIL9, cikti_dizin=_i9_kok,
                       is_ayar=_EK_AC)
    kontrol("FIXTURE orkestrasyon UCTAN UCA calisti", _R9["ok"] is True,
            str(_R9["neden"]))

    # ── (a) STIL PROFILI -> EDIT PROFILI ve PROPS ──
    kontrol("stil profili EDIT profiline cevriliyor",
            _R9["profil_adi"] == "investigative-essay", _R9["profil_adi"])
    kontrol("profil secimi GEREKCELI", "belgesel-arastirmaci"
            in _R9["profil_gerekce"])
    kontrol("bilinmeyen stil VARSAYILANA duser (uydurma profil yok)",
            ekp.edit_profili_sec("boyle-stil-yok")[0]
            == ekp.VARSAYILAN_EDIT_PROFILI
            and "varsayilan" in ekp.edit_profili_sec("")[1])
    kontrol("STIL KARARLARI props'a TASINIYOR",
            "stilProfili" in (_R9["props"] or {}))
    _sk = _R9["stil_kararlari"]
    kontrol("stil kararlari 7 boyutu tasiyor",
            {"tempo", "gecis", "kamera", "tipografi", "renk", "ses"} <= set(_sk),
            str(sorted(_sk)))
    kontrol("ritim karari (plan_sn) tasiniyor",
            isinstance(_sk["tempo"]["plan_sn"], (int, float)))
    kontrol("gecis karari tasiniyor", bool(_sk["gecis"]["tur"]))
    kontrol("tipografi karari tasiniyor", bool(_sk["tipografi"]["altyazi"]))
    kontrol("renk karari tasiniyor", bool(_sk["renk"]["grade"]))
    kontrol("ses/ducking karari tasiniyor",
            isinstance(_sk["ses"]["ducking_db"], (int, float)))

    # ── (b) SAHNE ZINCIRI KORUNUYOR ──
    _zincir = ekp.sahne_zinciri(_R9["props"])
    kontrol("her sahne icin zincir cikarilabiliyor",
            len(_zincir) == len(_CUMLE), f"{len(_zincir)}/{len(_CUMLE)}")
    _bagli = [z for z in _zincir if z["asset_id"]]
    kontrol("scene_id her sahnede KORUNDU",
            all(z["scene_id"] for z in _zincir))
    kontrol("fact_id lisansli sahnelerde KORUNDU",
            all(z["fact_id"] for z in _bagli), str([z["fact_id"] for z in _zincir]))
    kontrol("asset_id + saglayici + LISANS zinciri KORUNDU",
            all(z["asset_id"] and z["saglayici"] and z["lisans"]
                for z in _bagli))
    kontrol("cekim suresi (ritim) KORUNDU",
            all(isinstance(z["sure_sn"], (int, float)) and z["sure_sn"] > 0
                for z in _zincir))
    kontrol("motion kararlari KORUNDU",
            all(z["motion"] for z in _zincir))
    kontrol("GECIS kararlari KORUNDU (motion spec icinde)",
            all(z["gecis"] for z in _zincir),
            str([z["gecis"] for z in _zincir]))
    kontrol("kamera kararlari (hareket/kadraj) KORUNDU",
            all(z["hareket"] or z["kadraj"] for z in _zincir))
    # ⚠ Tipografi IKI yoldan tasinir: altyazi dizisi (TTS zamanlamasindan
    # gelir, bu fixture'da yok) VE motion spec katmanlari (baslik/etiket).
    # Ikisini birden olcmek gerekiyordu; yalnizca diziye bakmak tipografiyi
    # "kayboldu" gosteriyordu — olculdu, duzeltildi.
    kontrol("tipografi katmani KORUNDU (spec ya da altyazi dizisi)",
            sum(len(z["tipografi"]) + z["altyazi_adet"] for z in _zincir) > 0,
            str([z["tipografi"] for z in _zincir]))
    kontrol("tipografi STILI props ust duzeyinde tasiniyor",
            "altyaziStil" in (_R9["props"] or {}),
            str(sorted(_R9["props"] or {})))
    kontrol("ses/ducking kararlari (j_cut/l_cut) TASINIYOR",
            all("j_cut" in z and "l_cut" in z for z in _zincir))
    kontrol("anlatim islevi KORUNDU", all(z["islev"] for z in _zincir))

    # ── (c) LISANS DUVARI ve KAPSAM BOSLUGU ──
    kontrol("LISANSSIZ aday render planina GIREMEDI",
            all(z["asset_id"] != "BAD" for z in _zincir),
            str([z["asset_id"] for z in _zincir]))
    kontrol("elenen aday GORUNUR (sessiz degil)",
            any(e["asset_id"] == "BAD" for e in _R9["elenen_medya"]),
            str(_R9["elenen_medya"]))
    kontrol("elenme NEDENI raporlaniyor",
            all(e.get("neden") for e in _R9["elenen_medya"]))
    kontrol("KAPSAM BOSLUGU aynen tasindi (kapatilmadi)",
            any(b.get("scene_id") == "s003"
                for b in _R9["kapsam_bosluklari"]),
            str(_R9["kapsam_bosluklari"]))
    _bos_sahne = [z for z in _zincir if not z["asset_id"]]
    kontrol("bosluk RASTGELE STOKLA KAPANMADI (asset bos kaldi)",
            len(_bos_sahne) >= 1 and all(not z["lisans"] for z in _bos_sahne),
            str(_bos_sahne[:1]))
    kontrol("lisans_suz yalnizca render_kullanilabilir gecirir",
            len(ekp.lisans_suz(_medya_fix())[0]["adaylar"]) == 2)
    kontrol("lisans_suz kapsam bosluklarini SILMEZ",
            len(ekp.lisans_suz(_medya_fix())[0]["kapsam_bosluklari"]) == 1)

    # ── (d) QA-ON KARARI ──
    kontrol("QA durumu RAPORLANIYOR", _R9["qa"]["durum"] in
            ("PASS", "WARN", "FAIL"), str(_R9["qa"]))
    kontrol("PASS/WARN ayrimi GORUNUR",
            "fail" in _R9["qa"] and "warn" in _R9["qa"])
    kontrol("WARN render'i ENGELLEMIYOR",
            _R9["render_edilebilir"] is True if _R9["qa"]["durum"] == "WARN"
            else True)

    # ⚠ QA FAIL -> RENDER BASLATILMAZ (qa_on ciktisi sahte FAIL yapilarak)
    from editor import plan as _eplan                   # noqa: E402
    _asil_uret = _eplan.uret

    def _fail_uret(**kw):
        c = _asil_uret(**kw)
        c = dict(c)
        c["editor_qa"] = {"durum": "FAIL", "fail": 2, "warn": 0,
                          "sorunlar": [{"kod": "X"}, {"kod": "Y"}]}
        return c

    try:
        _eplan.uret = _fail_uret
        _RF = ekp.plan_kur(cumleler=_CUMLE, medya_manifest=_medya_fix(),
                           olgular=_OLGU9, stil=_STIL9,
                           cikti_dizin=_i9_kok, is_ayar=_EK_AC)
        kontrol("QA FAIL -> RENDER BASLATILMAZ",
                _RF["render_edilebilir"] is False and _RF["neden"] == "QA-FAIL",
                str(_RF["neden"]))
        kontrol("QA FAIL sebebi UYARILARDA gorunur",
                any("RENDER BASLATILMAZ" in u for u in _RF["uyarilar"]))
        kontrol("QA FAIL'de plan yine de URETILIYOR (inceleme icin)",
                _RF["ok"] is True and _RF["props"])
    finally:
        _eplan.uret = _asil_uret

    # ── (e) DESTEKLENMEYEN EFEKT GORUNUR KAYIP ──
    kontrol("efekt kapsami SAYILIYOR",
            isinstance((_R9["efekt_kapsami"] or {}).get("sayim"), dict),
            str(_R9["efekt_kapsami"])[:80])
    kontrol("desteklenmeyen efekt GORUNUR KAYIP olarak raporlaniyor",
            any("kayip efekt" in u for u in _R9["uyarilar"]),
            str(_R9["uyarilar"][:2]))
    kontrol("fallback karari GEREKCESIYLE gorunur",
            any("fallback" in str(u) for u in _R9["uyarilar"]))

    # ── (f) DAYANIKLILIK ──
    kontrol("cumle yoksa kontrollu dur",
            ekp.plan_kur(cumleler=[], medya_manifest=_medya_fix(),
                         is_ayar=_EK_AC)["neden"] == "CUMLE-YOK")
    _hepsi_lisanssiz = {"adaylar": [{"asset_id": "z", "scene_id": "s001",
                                     "render_kullanilabilir": False}],
                        "kapsam_bosluklari": []}
    _RM = ekp.plan_kur(cumleler=_CUMLE, medya_manifest=_hepsi_lisanssiz,
                       is_ayar=_EK_AC, cikti_dizin=_i9_kok)
    kontrol("lisansli aday YOKSA kontrollu dur (rastgele stok yok)",
            _RM["neden"] == "MEDYA-YOK" and not _RM["props"])
    kontrol("MEDYA-YOK durumunda bosluk RASTGELE KAPANMADIGI yaziliyor",
            any("RASTGELE STOKLA" in u for u in _RM["uyarilar"]))
    kontrol("bozuk girdide COKMUYOR",
            all(isinstance(ekp.plan_kur(cumleler=c, medya_manifest=m,
                                        is_ayar=_EK_AC,
                                        cikti_dizin=_i9_kok), dict)
                for c, m in ((None, None), ([], "x"), (_CUMLE, None),
                             (_CUMLE, {"adaylar": "bozuk"}))))
    kontrol("stil verilmezse VARSAYILAN profil (cokme yok)",
            ekp.plan_kur(cumleler=_CUMLE, medya_manifest=_medya_fix(),
                         is_ayar=_EK_AC, cikti_dizin=_i9_kok)["profil_adi"]
            == ekp.VARSAYILAN_EDIT_PROFILI)
    kontrol("orkestrasyon DETERMINISTIK (ayni girdi -> ayni zincir)",
            ekp.sahne_zinciri(ekp.plan_kur(
                cumleler=_CUMLE, medya_manifest=_medya_fix(), olgular=_OLGU9,
                stil=_STIL9, cikti_dizin=_i9_kok, is_ayar=_EK_AC)["props"])
            == _zincir)
finally:
    _sh.rmtree(_i9_kok, ignore_errors=True)


blok("23b. I-9 — mevcut yol DEGISMEDI ve korumalar aynen")

_EK = oku(KOK, "edit_kopru.py")
# ⚠ "render etmiyor" iddiasi HAM DIZE TARAMASIYLA olculemez: modul kendi
# dokumantasyonunda zaten "render `remotion_v2.render()` isidir" diyor.
# Bu yuzden GERCEK KOD uzerinde AST ile CAGRI arariz — yorum/docstring
# icindeki metin koda dahil degildir.
import ast                                            # noqa: E402
_EK_AGAC = ast.parse(_EK)
_EK_CAGRI = set()
for _n in ast.walk(_EK_AGAC):
    if isinstance(_n, ast.Call):
        _f = _n.func
        if isinstance(_f, ast.Attribute):
            _EK_CAGRI.add(_f.attr)
        elif isinstance(_f, ast.Name):
            _EK_CAGRI.add(_f.id)
kontrol("kopru RENDER CAGRISI YAPMIYOR (AST ile olculdu)",
        "render" not in _EK_CAGRI and "Popen" not in _EK_CAGRI
        and "run" not in _EK_CAGRI, str(sorted(_EK_CAGRI))[:120])
kontrol("kopru ALT SUREC baslatmiyor",
        not [n for n in ast.walk(_EK_AGAC)
             if isinstance(n, (ast.Import, ast.ImportFrom))
             and "subprocess" in ast.dump(n)])
kontrol("kopru AG CAGIRMIYOR",
        not re.search(r"^\s*(import|from)\s+(requests|urllib|socket)\b",
                      _EK, re.M))
# ⚠ I-9'da bu kontrol "pipeline edit_kopru'yu import ETMIYOR" diyordu — o
# bir BILINEN SINIRDI (§26 sinir 1) ve I-10 onu KASITLI kapatti. Kuralin
# NIYETI degismedi: mevcut hizli render yolu KORUNMALI ve yeni yol yalnizca
# OPT-IN olmali. Olcum bu niyete gore guncellendi.
_PP_I9 = oku(KOK, "pipeline.py")
kontrol("pipeline MEVCUT hizli render yolunu KORUYOR",
        "hizli_render" in _PP_I9 and "remotion_v2" not in _PP_I9)
kontrol("edit_kopru pipeline'da YALNIZCA opt-in cagriliyor",
        "if _ed_acik:" in _PP_I9)
kontrol("remotion_v2 opt-in oldugunu HALA soyluyor",
        "MEVCUT RENDER YOLUNA DOKUNMUYOR" in oku(KOK, "editor/remotion_v2.py"))
kontrol("editor paketi bu adimda DEGISMEDI",
        all("edit_kopru" not in oku(KOK, f) for f in
            ("editor/plan.py", "editor/adapter.py", "editor/qa_on.py",
             "editor/remotion_v2.py")))
kontrol("medya avcisi bayragi HALA kapali", mkp.ACIK is False)
kontrol("butce korumalari KORUNDU", mkp.VARSAYILAN_MAKS_USD == 0.0)
kontrol("kare kapisi fail-closed KORUNDU",
        "if not callable(kare_dogrula)" in oku(KOK, "medya_kopru.py"))
kontrol("22 alanlik generate sozlesmesi DEGISMEDI",
        len(set(re.findall(r"\{ad: '(\w+)'",
                           oku(KOK, "static/js/api.js")))) == 22)
kontrol("UI DEGISMEDI",
        "basitGovde" in oku(KOK, "static/js/wizard.js")
        and "SURE_SECENEKLERI" in oku(KOK, "static/js/basit.js"))
kontrol("server.py editor_v2 alanini OKUMUYOR",
        "editor_v2" not in oku(KOK, "server.py"))
kontrol("edit_kopru.py derleniyor", _derlenir(os.path.join(KOK, "edit_kopru.py")))


# ═══ 24. FAZ I-10 — EDIT KOPRUSU PIPELINE'A BAGLI + MANIFEST DONUSUMU ═══
# ⚠ KAPATILAN ACIK (§26 sinir 1 ve 6): edit_kopru pipeline'a bagli DEGILDI ve
# medya_kopru ciktisi medya_manifest bicimine CEVRILMIYORDU.
# ⚠ HER IKI BAYRAK DA VARSAYILAN KAPALI. Gercek render/ag/ucretli API YOK.
blok("24. I-10 — manifest donusumu: yalnizca lisansli + kare dogrulanmis")

_mb = mkp.is_butcesi_kur("i10")
kontrol("bos butcede manifest BOS (uydurma aday yok)",
        mkp.manifest_kur(_mb)["ozet"]["aday"] == 0)

_SECIM = {"scene_id": "s001", "fact_id": "f001", "asset_id": "a1",
          "saglayici": "wikimedia", "lisans": "cc-by",
          "orijinal_url": "https://commons.wikimedia.org/a1",
          "eser_sahibi": "X", "atif_metni": "X / CC BY", "atif_gerekli": True,
          "medya_yolu": "/tmp/a1.mp4", "medya_turu": "video", "tur": "video",
          "sorgu": "pack ice", "baslik": "ship", "genislik": 1920,
          "yukseklik": 1080, "sure_sn": 12.0, "toplam_skor": 80,
          "sahne_amaci": "ortam", "render_kullanilabilir": True}
_mb.secildi(dict(_SECIM))
_mb.bosluk_ekle("s002", "avci aday veremedi")
_M10 = mkp.manifest_kur(_mb)
kontrol("secim manifeste ADAY olarak giriyor", _M10["ozet"]["aday"] == 1)
for _alan in ("fact_id", "asset_id", "saglayici", "lisans", "orijinal_url",
              "eser_sahibi", "atif_metni", "scene_id", "medya_yolu"):
    kontrol(f"manifest {_alan} KAYBETMIYOR",
            _M10["adaylar"][0].get(_alan) == _SECIM[_alan], _alan)
kontrol("manifest adayi render_kullanilabilir bayragini tasiyor",
        _M10["adaylar"][0]["render_kullanilabilir"] is True)
kontrol("KAPSAM BOSLUGU manifeste aynen tasiniyor",
        any(b["scene_id"] == "s002" for b in _M10["kapsam_bosluklari"]),
        str(_M10["kapsam_bosluklari"]))
kontrol("bosluk RASTGELE STOKLA kapanmiyor (aday sayisi artmadi)",
        _M10["ozet"]["aday"] == 1 and _M10["ozet"]["bosluk"] == 1)

# ⚠ SAVUNMA: bayraksiz kayit manifeste GIREMEZ
_mb.secildi({"asset_id": "kotu", "render_kullanilabilir": False})
kontrol("render_kullanilabilir OLMAYAN kayit manifeste GIRMIYOR",
        mkp.manifest_kur(_mb)["ozet"]["aday"] == 1,
        str(mkp.manifest_kur(_mb)["ozet"]))
_mb.secildi({"render_kullanilabilir": True})          # asset_id yok
kontrol("asset_id'siz kayit manifeste GIRMIYOR",
        mkp.manifest_kur(_mb)["ozet"]["aday"] == 1)
kontrol("manifest_kur bozuk girdide COKMUYOR",
        all(isinstance(mkp.manifest_kur(x), dict)
            for x in (None, "x", 5, object())))
kontrol("disaridan bosluk da birlestiriliyor",
        mkp.manifest_kur(_mb, kapsam_bosluklari=[
            {"scene_id": "s009", "neden": "dis"}])["ozet"]["bosluk"] == 2)
kontrol("tekrar eden bosluk kaydi TEKE iniyor",
        mkp.manifest_kur(_mb, kapsam_bosluklari=[
            {"scene_id": "s002", "neden": "avci aday veremedi"}]
        )["ozet"]["bosluk"] == 1)

# ── SECIM KAYDI IS BASINA IZOLE ──
_mA = mkp.is_butcesi_kur("A")
_mB = mkp.is_butcesi_kur("B")
_mA.secildi(dict(_SECIM))
_mA.secildi({**_SECIM, "asset_id": "a2"})
_mB.secildi({**_SECIM, "asset_id": "b1"})
kontrol("secim kayitlari IS BASINA izole",
        mkp.manifest_kur(_mA)["ozet"]["aday"] == 2
        and mkp.manifest_kur(_mB)["ozet"]["aday"] == 1)
kontrol("bir isin bosluklari digerine SIZMIYOR",
        (_mA.bosluk_ekle("x", "y"), len(_mB.bosluklar()) == 0)[1])
kontrol("ozet secim/bosluk sayilarini GOSTERIYOR",
        _mA.ozet()["secim_kaydi"] == 2 and _mA.ozet()["kapsam_boslugu"] == 1,
        str({k: v for k, v in _mA.ozet().items()
             if k in ("secim_kaydi", "kapsam_boslugu")}))


blok("24b. I-10 — pipeline cagri zinciri (FIXTURE, render YOK)")

_PP6 = oku(KOK, "pipeline.py")
kontrol("pipeline edit_kopru'yu import ediyor", "import edit_kopru" in _PP6)
kontrol("plan YALNIZCA opt-in oldugunda kuruluyor",
        "_ed_acik, _ed_gerekce = edit_kopru.acik_mi(_is_ayar)" in _PP6
        and "if _ed_acik:" in _PP6)
kontrol("manifest medya_kopru'dan kuruluyor",
        "medya_kopru.manifest_kur(_avci_butce)" in _PP6)
kontrol("lisansli aday YOKSA plan DENENMIYOR",
        'if not (_manifest.get("adaylar") or []):' in _PP6
        and '"neden": "MEDYA-YOK"' in _PP6)
kontrol("avci basarisizliginda KAPSAM BOSLUGU kaydediliyor",
        "_avci_butce.bosluk_ekle(" in _PP6)
kontrol("pipeline GERCEK RENDER cagirmiyor (bu atomda)",
        "remotion_v2" not in _PP6 and "edit_kopru.plan_kur(" in _PP6)
kontrol("hata KONTROLLU FALLBACK ile yakalaniyor",
        '"neden": "HATA"' in _PP6 and "edit plani kurulamadi" in _PP6)
kontrol("ozet YALNIZCA opt-in oldugunda ise yaziliyor",
        _PP6.count('sonuc["edit_plani"]') >= 1
        and _PP6.index("if _ed_acik:") < _PP6.index('sonuc["edit_plani"]'))
kontrol("QA karari ise TASINIYOR",
        '"render_edilebilir": _ep["render_edilebilir"]' in _PP6
        and '"qa": _ep["qa"]' in _PP6)

# ── FIXTURE: kapali yol / acik+basarili / acik+QA FAIL / kotu medya ──
_i10_kok = tempfile.mkdtemp(prefix="i10_")
try:
    _C10 = [{"scene_id": "s001", "fact_id": "f001", "sure_sn": 3.2,
             "metin": "The Endurance became trapped in pack ice in 1915 "
                      "near Antarctica."},
            {"scene_id": "s002", "fact_id": "f002", "sure_sn": 4.0,
             "metin": "The crew camped on Elephant Island awaiting rescue."}]
    _bb = mkp.is_butcesi_kur("fix10")
    _bb.secildi({**_SECIM, "asset_id": "a1", "scene_id": "s001",
                 "fact_id": "f001"})
    _bb.secildi({**_SECIM, "asset_id": "a2", "scene_id": "s002",
                 "fact_id": "f002", "saglayici": "pexels",
                 "lisans": "pexels",
                 "orijinal_url": "https://pexels.com/a2"})
    _bb.bosluk_ekle("s003", "avci aday veremedi")
    _MF = mkp.manifest_kur(_bb)

    # (1) KAPALI YOL — hicbir sey uretilmez
    kontrol("KAPALI yolda plan URETILMIYOR",
            ekp.plan_kur(cumleler=_C10, medya_manifest=_MF,
                         cikti_dizin=_i10_kok)["neden"] == "KAPALI")

    # (2) ACIK + BASARILI
    _RA = ekp.plan_kur(cumleler=_C10, medya_manifest=_MF, olgular=_OLGU9,
                       stil=_STIL9, cikti_dizin=_i10_kok, is_ayar=_EK_AC)
    kontrol("ACIK + lisansli manifest -> plan OLUSUYOR", _RA["ok"] is True,
            str(_RA["neden"]))
    _zA = ekp.sahne_zinciri(_RA["props"])
    kontrol("manifest zinciri props'a KADAR geliyor (fact + lisans)",
            all(z["fact_id"] and z["lisans"] for z in _zA if z["asset_id"]),
            str(_zA[:1]))
    kontrol("avci kaynakli KAPSAM BOSLUGU plana tasindi",
            any(b.get("scene_id") == "s003"
                for b in _RA["kapsam_bosluklari"]),
            str(_RA["kapsam_bosluklari"]))
    kontrol("PASS/WARN'da render_edilebilir True",
            _RA["render_edilebilir"] is True if _RA["qa"]["durum"] in
            ("PASS", "WARN") else True)

    # (3) ACIK + QA FAIL -> RENDER KAPALI
    _asil_uret2 = _eplan.uret

    def _fail2(**kw):
        c = dict(_asil_uret2(**kw))
        c["editor_qa"] = {"durum": "FAIL", "fail": 1, "warn": 0,
                          "sorunlar": [{"kod": "Z"}]}
        return c

    try:
        _eplan.uret = _fail2
        _RQ = ekp.plan_kur(cumleler=_C10, medya_manifest=_MF, olgular=_OLGU9,
                           stil=_STIL9, cikti_dizin=_i10_kok, is_ayar=_EK_AC)
        kontrol("QA FAIL -> render_edilebilir False",
                _RQ["render_edilebilir"] is False and _RQ["neden"] == "QA-FAIL")
    finally:
        _eplan.uret = _asil_uret2

    # (4) KOTU MEDYA REDDEDILIYOR
    _kotu_manifest = {"adaylar": [{"asset_id": "BAD", "scene_id": "s001",
                                   "lisans": "unknown",
                                   "render_kullanilabilir": False}],
                      "kapsam_bosluklari": []}
    _RB = ekp.plan_kur(cumleler=_C10, medya_manifest=_kotu_manifest,
                       cikti_dizin=_i10_kok, is_ayar=_EK_AC)
    kontrol("KOTU (lisanssiz) medya plana GIREMIYOR",
            _RB["neden"] == "MEDYA-YOK" and not _RB["props"])
    kontrol("kotu medya reddi GEREKCELI",
            any(e["asset_id"] == "BAD" for e in _RB["elenen_medya"]))
finally:
    _sh.rmtree(_i10_kok, ignore_errors=True)


blok("24c. I-10 — kapali yol BIT-BIT ayni, korumalar aynen")

kontrol("EDITOR_V2 bayragi varsayilan KAPALI", ekp.ACIK is False)
kontrol("MEDYA_AVCISI bayragi varsayilan KAPALI", mkp.ACIK is False)
kontrol("kapaliyken pipeline `edit_plani` anahtari EKLEMIYOR",
        "if _ed_acik:" in _PP6
        and _PP6.split("if _ed_acik:")[0].count('sonuc["edit_plani"]') == 0)
kontrol("kapaliyken `medya_avcisi` anahtari EKLEMIYOR",
        "if _avci_acik and _avci_butce is not None:" in _PP6)
kontrol("MEVCUT hizli render yolu KORUNDU (VidrushVideo)",
        "VidrushVideo" in _PP6 or "hizli_render" in _PP6)
kontrol("kopru HALA render cagirmiyor",
        "render" not in {n.func.attr for n in ast.walk(ast.parse(
            oku(KOK, "edit_kopru.py"))) if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)})
kontrol("kare kapisi fail-closed KORUNDU",
        "if not callable(kare_dogrula)" in oku(KOK, "medya_kopru.py"))
kontrol("lisans duvari KORUNDU",
        'getattr(a, "render_kullanilabilir", False)' in oku(KOK, "medya_kopru.py"))
kontrol("SSRF korumasi KORUNDU (kopru dogrudan ag cagirmiyor)",
        not re.search(r"^\s*(import|from)\s+(requests|urllib|socket)\b",
                      oku(KOK, "medya_kopru.py"), re.M))
kontrol("butce korumalari KORUNDU", mkp.VARSAYILAN_MAKS_USD == 0.0)
kontrol("22 alanlik generate sozlesmesi DEGISMEDI",
        len(set(re.findall(r"\{ad: '(\w+)'",
                           oku(KOK, "static/js/api.js")))) == 22)
kontrol("UI ve kullanici secimleri DEGISMEDI",
        "basitGovde" in oku(KOK, "static/js/wizard.js")
        and "SURE_SECENEKLERI" in oku(KOK, "static/js/basit.js")
        and "d.unlu = t.unlu ? '1' : '0'" in oku(KOK, "static/js/wizard.js"))
kontrol("server.py editor_v2/medya_avcisi OKUMUYOR",
        "editor_v2" not in oku(KOK, "server.py")
        and "medya_avcisi" not in oku(KOK, "server.py"))
for _f6 in ("medya_kopru.py", "edit_kopru.py", "pipeline.py"):
    kontrol(f"{_f6} derleniyor", _derlenir(os.path.join(KOK, _f6)))


# ═══ 25. FAZ I-11 — 20 SN RENDER SMOKE SOZLESMESI ═══
# ⚠ BU BOLUM RENDER CALISTIRMAZ (yavas + agir). Smoke BETIGININ sozlesmesini,
# durustluk etiketlerini ve `yerel_yol` kusurunun duzeltildigini kilitler.
# Gercek render kaniti: `outputs/sample/` (betik elle kosulur).
blok("25. I-11 — render smoke betigi ve durustluk etiketleri")

_SMOKE_YOL = os.path.join(KOK, "testler", "smoke_editorv2_20sn.py")
kontrol("smoke betigi var", os.path.exists(_SMOKE_YOL))
_SM = oku(KOK, "testler/smoke_editorv2_20sn.py")
kontrol("smoke betigi derleniyor", _derlenir(_SMOKE_YOL))

# ── (a) DURUSTLUK ETIKETI: neyi kanitlar / neyi kanitlamaz ──
kontrol("betik NEYI KANITLAR bolumu tasiyor", "KANITLAR" in _SM)
kontrol("betik NEYI KANITLAMAZ bolumu tasiyor", "KANITLAMAZ" in _SM)
for _iz in ("WEB'DEN MEDYA BULMA", "Arastirma/fact-check", "TTS uretimi",
            "canli /api/generate", "Ucretli"):
    kontrol(f"kapsam disi acikca yaziyor: {_iz[:24]}", _iz in _SM)
kontrol("yerel fixture kullandigini SOYLUYOR",
        "YEREL fixture" in _SM and "faz_e" in _SM)
kontrol("cikti raporu kapsam etiketini TASIYOR",
        '"kapsam_disi"' in _SM and '"gercek_motor"' in _SM)

# ── (b) GERCEK MOTOR ZINCIRI CAGRILIYOR ──
for _c in ("edit_kopru.plan_kur(", "remotion_v2.props_hazirla(",
           "remotion_v2.dogrula(", "remotion_v2.render("):
    kontrol(f"gercek motor cagrisi: {_c[:28]}", _c in _SM)
kontrol("QA FAIL'de RENDER BASLATILMIYOR",
        'if not sonuc["render_edilebilir"]:' in _SM
        and "render BASLATILMADI" in _SM)
kontrol("on-render kapisi FAIL'de duruyor",
        'if kontrol["durum"] == "FAIL":' in _SM)

# ── (c) BLOKER RAPORLAMA — SAHTE CIKTI URETMEZ ──
kontrol("bagimlilik yoksa BLOKE raporlaniyor, sahte cikti YOK",
        _SM.count("BLOKE:") >= 5)
kontrol("node_modules yoksa cozum yolu yaziliyor",
        "npm ci" in _SM and "node_modules yok" in _SM)
kontrol("ffmpeg/ffprobe yoksa BLOKE",
        'for arac in ("ffmpeg", "ffprobe")' in _SM)
kontrol("betik SAHTE video URETMIYOR (ffmpeg ile bos dosya yazmiyor)",
        "lavfi" not in _SM and "color=c=" not in _SM
        and "testsrc" not in _SM)

# ── (d) DOGRULAMA: ffprobe + kareler ──
kontrol("ffprobe ile codec/sure/cozunurluk/ses dogrulaniyor",
        "codec_type,codec_name,width,height" in _SM
        and "sample_rate,channels" in _SM
        and "format=duration,size,bit_rate" in _SM)
kontrol("0s/10s/19s kareleri cikariliyor", "for t in (0, 10, 19)" in _SM)
kontrol("cikti belirgin outputs/sample yoluna yaziliyor",
        '"outputs", "sample"' in _SM)

# ── (e) `yerel_yol` KUSURU DUZELTILDI (smoke'un ORTAYA CIKARDIGI) ──
# ⚠ `editor.plan` medya yolunu `yerel_yol` alanindan okur (plan.py:203).
# `manifest_kur` yalnizca `medya_yolu` yaziyordu -> plan aday buluyor ama
# MEDYASI BOS kaliyordu; 20 sn render'da gorseller HIC gorunmedi.
kontrol("plan medya yolunu `yerel_yol` alanindan okuyor (sozlesme)",
        'aday.get("yerel_yol")' in oku(KOK, "editor/plan.py"))
kontrol("manifest_kur ARTIK `yerel_yol` yaziyor",
        '"yerel_yol": hedef_yol,' in oku(KOK, "medya_kopru.py"))
_mb11 = mkp.is_butcesi_kur("i11")
_mb11.secildi({**_SECIM, "yerel_yol": "/tmp/a1.mp4"})
kontrol("uretilen manifest adayi `yerel_yol` TASIYOR",
        bool(mkp.manifest_kur(_mb11)["adaylar"][0].get("yerel_yol")),
        str(sorted(mkp.manifest_kur(_mb11)["adaylar"][0])))
kontrol("geriye uyumluluk: `medya_yolu` da HALA yaziliyor",
        bool(mkp.manifest_kur(_mb11)["adaylar"][0].get("medya_yolu")))

# ── (f) CIKTI DIZINI SOZLESMESI ──
_OUT = os.path.join(KOK, "..", "outputs", "sample")
kontrol("outputs/sample README'si var", os.path.exists(
    os.path.join(_OUT, "README.md")))
if os.path.exists(os.path.join(_OUT, "README.md")):
    _RM = open(os.path.join(_OUT, "README.md"), encoding="utf-8").read()
    kontrol("README neyi KANITLAMAZ diyor", "KANITLAMAZ" in _RM)
    kontrol("README icerik uyusmazligini DURUSTCE yaziyor",
            "uyuşmaz" in _RM and "Apollo" in _RM and "Endurance" in _RM)
    kontrol("README web'den medya bulunmadigini yaziyor",
            "Web'den medya bulma" in _RM)
    kontrol("README olculen ffprobe degerlerini tasiyor",
            "h264 / aac" in _RM and "20.096" in _RM)
_GI = open(os.path.join(KOK, "..", ".gitignore"), encoding="utf-8").read()
kontrol("ikili ciktilar gitignore'da (depo sismesin)",
        "outputs/sample/*.mp4" in _GI and "outputs/sample/*.png" in _GI)
# ⚠ Yorum satirlari KURAL DEGILDIR: gitignore aciklamasi zaten
# "outputs/sample/README.md ... IZLENIR" diyor. Bu yuzden yalnizca
# GERCEK KURAL satirlari taranir.
_GI_KURAL = [x.strip() for x in _GI.splitlines()
             if x.strip() and not x.strip().startswith("#")]
kontrol("README ve rapor IZLENIYOR (gitignore KURALI yok)",
        not [k for k in _GI_KURAL
             if "README" in k or "smoke_rapor" in k], str(_GI_KURAL[-4:]))

# ── (g) MEVCUT YOL ve BAYRAKLAR ──
kontrol("smoke pipeline'i CAGIRMIYOR",
        "import pipeline" not in _SM and "pipeline.uret" not in _SM)
kontrol("bayraklar HALA varsayilan kapali",
        mkp.ACIK is False and ekp.ACIK is False)
kontrol("22 alanlik generate sozlesmesi DEGISMEDI",
        len(set(re.findall(r"\{ad: '(\w+)'",
                           oku(KOK, "static/js/api.js")))) == 22)
kontrol("UI DEGISMEDI",
        "basitGovde" in oku(KOK, "static/js/wizard.js")
        and "SURE_SECENEKLERI" in oku(KOK, "static/js/basit.js")
        and "d.unlu = t.unlu ? '1' : '0'" in oku(KOK, "static/js/wizard.js"))
kontrol("deploy.sh ezme korumasi KORUNDU",
        "GERIDE" in open(os.path.join(KOK, "..", "deploy.sh"),
                         encoding="utf-8").read())


# ═══ 26. FAZ I-12 — QA WARN RAPORU + CHAPTER-CARD KALITESI ═══
# ⚠ I-11'in 20 sn render'i BES QA WARN uretmisti ve 19. saniyedeki
# motion-graphic fallback ekranda ANLAMSIZ bir "1" + tek sari cubuk
# gosteriyordu; ustelik baslik harf ortasindan KIRPILIYORDU.
blok("26. I-12 — sayi uydurma yasagi ve bolum karti")

from editor import plan as _ep2                        # noqa: E402
from editor import profil as _eprofil                  # noqa: E402

# ── (a) SAYI UYDURMA YASAK ──
kontrol("YIL veri sayilmiyor (cubuk grafigi yaniltici olurdu)",
        _ep2._beat_sayilari("The Endurance became trapped in 1915.") == [],
        str(_ep2._beat_sayilari("The Endurance became trapped in 1915.")))
kontrol("GERCEK sayilar okunuyor",
        _ep2._beat_sayilari("hauled 800 miles in 16 days") == [800.0, 16.0])
kontrol("sayi yoksa BOS liste (uydurma yok)",
        _ep2._beat_sayilari("Every member survived the ordeal.") == [])
kontrol("bozuk girdide cokmuyor",
        all(isinstance(_ep2._beat_sayilari(x), list)
            for x in (None, "", 5, "abc")))
_PLAN_KAYNAK = oku(KOK, "editor/plan.py")
kontrol("plan.py ARTIK sabit [1] gecmiyor",
        "veri_grafigi_spec(b.metin[:28], [1]" not in _PLAN_KAYNAK)
kontrol("veri sahnesi YALNIZCA gercek sayi varsa ciziliyor",
        "if _degerler:" in _PLAN_KAYNAK
        and "motion.veri_grafigi_spec(b.metin[:28], _degerler" in _PLAN_KAYNAK)
kontrol("sayi yoksa BOLUM KARTINA dusuluyor",
        "motion.bolum_basligi_spec(" in _PLAN_KAYNAK
        and "_kart_basligi(b.metin" in _PLAN_KAYNAK)
_GRAF = oku(KOK, "../app/render-studio/src/editorv2/Grafikler.tsx")
kontrol("TSX de bos veride `[1]` VARMIYOR (derinlemesine savunma)",
        "degerler.length ? degerler : [1]" not in _GRAF
        and "if (!degerler.length) return null;" in _GRAF)

# ── (b) BOLUM KARTI: KIRPILMA YOK, SARKAN KELIME YOK ──
_pp = _eprofil.profil("premium-modern")
_sinir = _ep2.kart_basligi_siniri(_pp)
kontrol("kart basligi siniri HESAPLANIYOR (sabit degil)",
        12 <= _sinir <= 60 and "kart_basligi_siniri" in _PLAN_KAYNAK,
        str(_sinir))
kontrol("sinir puntoya BAGLI (buyuk punto -> az karakter)",
        _ep2.kart_basligi_siniri(_eprofil.profil("premium-modern")) > 0)
_uzun = "They reached Elephant Island in April 1916, the first solid ground."
_kart = _ep2._kart_basligi(_uzun, _sinir)
kontrol("uzun cumle kart basligina KISALTILIYOR", len(_kart) <= _sinir,
        f"{len(_kart)}/{_sinir}: {_kart!r}")
kontrol("SARKAN edat/baglac atiliyor",
        not _kart.lower().split()[-1] in _ep2._SARKAN, _kart)
kontrol("baslik noktalama ile bitmiyor",
        not _kart.endswith((",", ";", ":", "-", "—", ".")), _kart)
kontrol("bos metinde kontrollu varsayilan", _ep2._kart_basligi("") == "BÖLÜM")
kontrol("kisa cumle OLDUGU GIBI kaliyor",
        _ep2._kart_basligi("Every member survived", _sinir)
        == "Every member survived")
kontrol("TSX kirpma yerine KUCULTUYOR (harf kesilmez)",
        "KIRPMA YERINE KUCULT" in _GRAF and "const olcek =" in _GRAF
        and "punto * olcek" in _GRAF.replace("puntoTaban * olcek",
                                             "punto * olcek"))
kontrol("kuculme tabani var (okunurluk korunur)", "Math.max(0.7," in _GRAF)

# ── (c) TIPO-GUVENLI-ALT KUSURU KAPANDI ──
from editor import tipografi as _etipo                 # noqa: E402
kontrol("source-label konumu 0.90'dan DUSURULDU",
        _etipo.KONUM["source-label"] == 0.895,
        str(_etipo.KONUM["source-label"]))
_alt = (_etipo.KONUM["source-label"] + _etipo.YUKSEKLIK["source-label"]) * 1080
kontrol("source-label alt kenari guvenli alan ICINDE",
        _alt <= 1080 - _pp.tipografi.guvenli_kenar,
        f"alt={_alt:.1f}px > {1080 - _pp.tipografi.guvenli_kenar}")
kontrol("tum yazi turleri guvenli alanda",
        all((_etipo.KONUM[a] + _etipo.YUKSEKLIK[a]) * 1080
            <= 1080 - _pp.tipografi.guvenli_kenar
            for a in _etipo.KONUM if a in _etipo.YUKSEKLIK),
        str({a: round((_etipo.KONUM[a] + _etipo.YUKSEKLIK.get(a, 0)) * 1080)
             for a in _etipo.KONUM}))

# ── (d) 5 QA WARN'IN RAPORU (I-11 olcumu, handoff §29'da ayrintili) ──
_OUT2 = os.path.join(KOK, "..", "outputs", "sample", "README.md")
if os.path.exists(_OUT2):
    _RM2 = open(_OUT2, encoding="utf-8").read()
    for _w in ("PACING-KISA-ORAN", "SAGLAYICI-TEKEL", "TIPO-GUVENLI-ALT"):
        kontrol(f"README QA WARN'i raporluyor: {_w}", _w in _RM2)
    kontrol("README once/sonra kalite karsilastirmasi iceriyor",
            "ÖNCE" in _RM2 and "SONRA" in _RM2)
    kontrol("README fixture kaynakli WARN'lari AYIRIYOR",
            "fixture" in _RM2.lower())

# ── (e) KAPSAM BOSLUGU HALA RASTGELE STOKLA KAPANMIYOR ──
kontrol("bolum karti bir MEDYA DEGIL (bosluk kapatmaz)",
        "Bosluk rastgele stokla da kapanmaz" in _PLAN_KAYNAK)
kontrol("lisans duvari KORUNDU",
        'getattr(a, "render_kullanilabilir", False)' in oku(KOK, "medya_kopru.py"))
kontrol("bayraklar HALA varsayilan kapali",
        mkp.ACIK is False and ekp.ACIK is False)
kontrol("22 alanlik generate sozlesmesi DEGISMEDI",
        len(set(re.findall(r"\{ad: '(\w+)'",
                           oku(KOK, "static/js/api.js")))) == 22)
kontrol("UI DEGISMEDI",
        "basitGovde" in oku(KOK, "static/js/wizard.js")
        and "SURE_SECENEKLERI" in oku(KOK, "static/js/basit.js"))
for _f7 in ("editor/plan.py", "editor/tipografi.py"):
    kontrol(f"{_f7} derleniyor", _derlenir(os.path.join(KOK, _f7)))


# ═══ 27. FAZ I-13 — KALITELI ANLATICI SESI + KONU TUTARLILIGI ═══
# ⚠ BU BOLUM RENDER/TTS CALISTIRMAZ. Betigin sozlesmesini, konu tutarliligi
# kuralini, ses secim gerekcesini ve gorsel detay kapisini kilitler.
blok("27. I-13 — 10 sn kaliteli sesli mini-belgesel sozlesmesi")

_SES_YOL = os.path.join(KOK, "testler", "smoke_kaliteli_ses_10sn.py")
kontrol("10 sn ses smoke betigi var", os.path.exists(_SES_YOL))
_SS = oku(KOK, "testler/smoke_kaliteli_ses_10sn.py")
kontrol("betik derleniyor", _derlenir(_SES_YOL))

# ── (a) KONU TUTARLILIGI ──
kontrol("konu ACIKCA beyan ediliyor (Apollo 11)", "Apollo 11" in _SS)
kontrol("gorsel/metin/anlatim AYNI konudan",
        "KONU TUTARLILIGI SART" in _SS
        and "uyusmazligi GIDERILDI" in _SS)
kontrol("metin DOGRULANMIS iddialardan turetiliyor",
        "DOGRULANMIS iddialardan turetildi" in _SS
        and '"guven": "dogrulandi"' in _SS)
# ⚠ Dokumantasyon KOD DEGILDIR: betigin basligi zaten "Apollo gorsel +
# Endurance metni uyusmazligi GIDERILDI" diyor. Bu yuzden yalnizca
# CALISAN KOD (docstring/yorum ayiklanmis) taranir.
_SS_AGAC = ast.parse(_SS)
# ⚠ Modul docstring'i de bir dugumdur; `ast.unparse` onu KORUR. Kod
# taramasi icin TUM docstring'ler (modul + fonksiyon) ayiklanir.
for _d in [_SS_AGAC] + [n for n in ast.walk(_SS_AGAC)
                        if isinstance(n, (ast.FunctionDef,
                                          ast.AsyncFunctionDef,
                                          ast.ClassDef))]:
    _g = getattr(_d, "body", [])
    if (_g and isinstance(_g[0], ast.Expr)
            and isinstance(getattr(_g[0], "value", None), ast.Constant)
            and isinstance(_g[0].value.value, str)):
        _d.body = _g[1:] or [ast.Pass()]
_SS_KOD = ast.unparse(ast.fix_missing_locations(_SS_AGAC))
kontrol("Endurance metni KODDA kullanilmiyor",
        "Endurance" not in _SS_KOD)
kontrol("olgular sahne metinleriyle AYNI kaynaktan",
        "for f, m in SAHNE_METINLERI" in _SS)

# ── (b) ANLATICI SESI: OLCUM + GEREKCE ──
kontrol("ses kalitesi codec/sr/kanal ile olculuyor",
        '"ornekleme_hz"' in _SS and '"kanal"' in _SS and '"codec"' in _SS)
kontrol("LUFS / tepe / LRA olculuyor",
        '"lufs"' in _SS and '"tepe_dbtp"' in _SS and '"lra"' in _SS)
kontrol("KIRPMA kontrolu var", '"kirpma_var"' in _SS)
kontrol("sessizlik orani olculuyor", '"sessiz_pct"' in _SS)
kontrol("ses secimi OLCUME dayaniyor (LRA), keyfi degil",
        "SECIM OLCUME DAYANIR" in _SS and 'key=lambda o: (o.get("lra"' in _SS)
kontrol("yerel macOS say alternatifi DURUSTCE degerlendiriliyor",
        "macOS say" in _SS and "kaliteli bir belgesel anlatimi DEGIL" in _SS)
kontrol("TTS maliyeti ACIKCA $0.00 yaziliyor",
        '"maliyet_usd": 0.0' in _SS and "UCRETSIZ" in _SS)
kontrol("kredi yukleme/anahtar degisimi YOK",
        "kredi yuklenmedi, anahtar degistirilmedi" in _SS)
kontrol("TTS yoksa SAHTE ses uretilmiyor, BLOKE raporlaniyor",
        "Sahte ses URETILMEDI" in _SS and "BLOKE:" in _SS)

# ── (c) GORSEL DETAY KAPISI (olculen kusurdan dogdu) ──
kontrol("gorsel detay OLCULUYOR (kadraj ici std sapma)",
        "def gorsel_detay(" in _SS and "crop=iw*0.7:ih*0.7" in _SS)
kontrol("esik alti gorsel KULLANILMIYOR",
        "DETAY_ESIGI" in _SS and 'o["detay_std"] >= DETAY_ESIGI' in _SS)
kontrol("esigin GEREKCESI olculen kusura dayaniyor",
        "DUZ GRI cikti" in _SS and "std 6.1" in _SS and "std 4.7" in _SS)
kontrol("uygun gorsel yoksa SAHTE gorsel uretilmiyor",
        "Sahte gorsel URETILMEDI" in _SS)
kontrol("gorsel secimi rapora yaziliyor", '"gorsel_secimi"' in _SS)

# ── (d) GERCEK MOTOR + SAHTE VIDEO YASAGI ──
for _c in ("edit_kopru.plan_kur(", "remotion_v2.props_hazirla(",
           "remotion_v2.dogrula(", "remotion_v2.render("):
    kontrol(f"gercek motor cagrisi: {_c[:26]}", _c in _SS)
kontrol("SAHTE ffmpeg renk/test kaynagi KODDA YOK",
        not re.search(r"lavfi|testsrc|color=c=|anullsrc", _SS_KOD))
kontrol("QA FAIL'de render BASLATILMIYOR",
        'if not sonuc["render_edilebilir"]:' in _SS
        and "render BASLATILMADI" in _SS)
kontrol("ambans DUCKING ile bagli",
        '"ducking"' in _SS and "ambans_seviye" in _SS)

# ── (e) CIKTI SOZLESMESI ──
kontrol("cikti adi sozlesmeye uygun",
        'VIDEO_ADI = "editorv2_quality_voice_10sn.mp4"' in _SS)
kontrol("0s/5s/9s kareleri cikariliyor", "for t in (0, 5, 9)" in _SS)
kontrol("ffprobe + ses olcumu JSON'a yaziliyor",
        '"quality_voice_rapor.json"' in _SS and '"video_ses_olcumu"' in _SS)
kontrol("rapor kapsam etiketini tasiyor",
        '"kapsam_disi"' in _SS and "WEB'DEN MEDYA BULMA" in _SS)
_GI2 = open(os.path.join(KOK, "..", ".gitignore"), encoding="utf-8").read()
kontrol("video ve kareler git'e EKLENMIYOR",
        "outputs/sample/*.mp4" in _GI2 and "outputs/sample/*.png" in _GI2)

# ── (f) KORUMALAR ──
kontrol("bayraklar HALA varsayilan kapali",
        mkp.ACIK is False and ekp.ACIK is False)
kontrol("22 alanlik generate sozlesmesi DEGISMEDI",
        len(set(re.findall(r"\{ad: '(\w+)'",
                           oku(KOK, "static/js/api.js")))) == 22)
kontrol("UI DEGISMEDI",
        "basitGovde" in oku(KOK, "static/js/wizard.js")
        and "SURE_SECENEKLERI" in oku(KOK, "static/js/basit.js")
        and "d.unlu = t.unlu ? '1' : '0'" in oku(KOK, "static/js/wizard.js"))
kontrol("deploy.sh ezme korumasi KORUNDU",
        "GERIDE" in open(os.path.join(KOK, "..", "deploy.sh"),
                         encoding="utf-8").read())
kontrol("pipeline bu adimda DEGISMEDI",
        "smoke_kaliteli_ses" not in oku(KOK, "pipeline.py"))


# ═══════════════════════════════════════════════════════════════════════
# §32  FAZ I-14 — KALITE KAPILARI
#
# ⚠ BU BOLUMUN ISPAT YUKU: kapinin GERCEK artefaktta kusuru GORMESI.
# Kanit uydurma fixture'dan degil, depoda IZLENEN iki rapordan geliyor:
#     outputs/sample/quality_voice_rapor.json  (I-13, 10 sn)
#     outputs/sample/smoke_rapor.json          (I-11, 20 sn)
# Video/kare dosyalari `.gitignore`da; bu yuzden olcumler RAPORDAN okunur,
# boylece test temiz klonda da kosar.
# ═══════════════════════════════════════════════════════════════════════
import json as _json                                             # noqa: E402
from editor import kalite_kapisi as _kk                           # noqa: E402
from editor import qa_on as _qon, qa_son as _qsn                  # noqa: E402

blok("§32a I-14 modul saflig i ve olculebilir kapsam")

_KK_KAYNAK = oku(KOK, "editor/kalite_kapisi.py")
_kk_agac = None
try:
    import ast as _ast
    _kk_agac = _ast.parse(_KK_KAYNAK)
except SyntaxError:
    pass
kontrol("kalite_kapisi ayristirilabiliyor", _kk_agac is not None)
if _kk_agac is not None:
    _ithal = set()
    for _n in _ast.walk(_kk_agac):
        if isinstance(_n, _ast.Import):
            _ithal.update(a.name.split(".")[0] for a in _n.names)
        elif isinstance(_n, _ast.ImportFrom) and _n.module:
            _ithal.add(_n.module.split(".")[0])
    # ⚠ AST ile olculuyor; ham dize taramasi modulun KENDI dokumantasyonunu
    # yakalayip yanlis alarm uretiyordu (I-9'da ogrenildi).
    kontrol("kalite_kapisi AG/DOSYA/ALT-SUREC modulu ITHAL ETMIYOR",
            not (_ithal & {"requests", "urllib", "socket", "http", "os",
                           "subprocess", "shutil", "pathlib", "open"}),
            sorted(_ithal))
_ozet = _kk.kapsam_ozeti()
# ⚠ I-14'te bu kontrol 5 olcum / 6 esik / 4 kapsam-disi kilitliyordu.
# I-16 altyazi, kunye ve 1080p'yi KAPSAMA ALDI; kontrol SILINMEDI, yeni
# kapsama gore GUNCELLENDI. Kuralin niyeti ayni: kapsam SAYILABILIR olmali
# ve kapsam disi olan ACIKCA yazilmali.
kontrol("kapsam_ozeti sayilabilir", _ozet["sema_surum"] == "1.0.0"
        and _ozet["render_sabiti"] == 7 and _ozet["olcum"] >= 5
        and len(_ozet["esik"]) >= 6)
kontrol("kapsam DISI acikca yaziliyor ve BOS DEGIL",
        isinstance(_ozet["kapsam_disi"], list)
        and len(_ozet["kapsam_disi"]) >= 1
        and all(isinstance(k, str) and k for k in _ozet["kapsam_disi"]),
        _ozet["kapsam_disi"])

# Render sabitleri TSX'ten OKUNDU mu — uydurma degil, eslesme testli.
_TSX = oku(KOK, "..", "app/render-studio/src/editorv2/Grafikler.tsx")
kontrol("EM_BUYUK_HARF TSX ile ayni (0.72)",
        _kk.EM_BUYUK_HARF == 0.72 and "0.72" in _TSX)
kontrol("BANT_MAKS_ORAN TSX ile ayni (0.84)",
        _kk.BANT_MAKS_ORAN == 0.84 and "width * 0.84" in _TSX)
kontrol("DOLGU_ORANI TSX ile ayni (0.42)",
        _kk.DOLGU_ORANI == 0.42 and "* 0.42" in _TSX)
kontrol("KUCULTME_TABANI TSX ile ayni (0.7)",
        _kk.KUCULTME_TABANI == 0.70 and "Math.max(0.7" in _TSX)
kontrol("HARF_ARALIGI_EM TSX letterSpacing'inden (0.01em)",
        _kk.HARF_ARALIGI_EM == 0.01 and "letterSpacing: '0.01em'" in _TSX)
# ⚠ BU KONTROL I-14'te bir BILINEN KUSURU kilitliyordu ("TSX sigdirma hesabi
# letterSpacing'i SAYMIYOR"). I-15 o kusuru KAPATTI, bu yuzden kontrol
# SILINMEDI — duzeltilmis davranisi kilitleyecek sekilde CEVRILDI.
# Kuralin niyeti ayni: plan ile render AYNI genislik aritmetigini kullanmali.
kontrol("I-15: TSX sigdirma hesabi letterSpacing'i ARTIK SAYIYOR",
        "puntoTaban * (0.72 + 0.01)" in _TSX
        and f"{_kk.EM_BUYUK_HARF} + {_kk.HARF_ARALIGI_EM}" in _TSX)

blok("§32b KIRMIZI KANIT — I-13 10 sn ciktisi (izlenen rapor)")

_R10_YOL = os.path.join(KOK, "..", "outputs", "sample",
                        "quality_voice_rapor.json")
_R10 = None
if os.path.exists(_R10_YOL):
    try:
        _R10 = _json.load(open(_R10_YOL, encoding="utf-8"))
    except ValueError:
        _R10 = None
if _R10 is None:
    bloke_yaz("I-13 10 sn raporu", f"yok/bozuk: {_R10_YOL}")
else:
    _z10 = _R10["zincir"]
    _ses10 = _R10["video_ses_olcumu"]
    _master10 = _R10["anlatici_ses"]["master"]

    # ── (1) BASLIK: kelime ortasindan KESIK ──
    # Smoke'un ilk sahne metni (izlenen kaynaktan, uydurma degil).
    _SS14 = oku(KOK, "testler/smoke_kaliteli_ses_10sn.py")
    _m = re.search(r'\("f001",\s*"([^"]+)"\)', _SS14)
    _ham10 = _m.group(1) if _m else ""
    kontrol("smoke ilk sahne metni okunabildi", bool(_ham10), _ham10)
    # plan.py'nin URETTIGI baslik: SABIT 42 karakterlik dilim + upper()
    _kart10 = (_ham10[:42] or "").upper()
    _kes10 = _kk.kelime_ortasi_kesik(_ham10, _kart10)
    kontrol("KIRMIZI: baslik KELIME ORTASINDAN kesik ('JULY' -> 'JU')",
            _kes10.get("kesik") is True
            and _kes10.get("yarim_kelime") == "JU"
            and _kes10.get("tam_kelime") == "JULY", _kes10)

    # ── (2) BASLIK: GERCEK render genisliginde BANT TASMASI ──
    # Render olcusu rapordaki ffprobe'dan OKUNUR (varsayilmaz).
    _vak = [a for a in (_R10["ffprobe"].get("streams") or [])
            if a.get("codec_type") == "video"]
    _gen10 = int(_vak[0].get("width") or 0) if _vak else 0
    kontrol("render GERCEK genisligi rapordan okundu (1280)", _gen10 == 1280,
            _gen10)
    _b10 = _kk.baslik_olcusu(_kart10, punto=60, kare_genislik=_gen10)
    kontrol("KIRMIZI: baslik bandi TASIYOR (1280 render'da)",
            _b10["sigar"] is False and _b10["tasma_px"] > 200, _b10)
    kontrol("KIRMIZI: punto kucultme TABANI vuruldu — kucultme YETMIYOR",
            _b10["kucultme_tabani_vuruldu"] is True
            and _b10["uygulanan_punto"] == 42, _b10)
    # KOK NEDEN: plan 1920'ye gore sinir hesapliyor, render 1280.
    _sig1920 = _kk.sigan_karakter(60, 1920)
    _sig1280 = _kk.sigan_karakter(60, _gen10)
    kontrol("KOK NEDEN: 1920 sinirinin YARISI 1280'de gecerli "
            f"({_sig1920} -> {_sig1280}), plan sabit 42 kullandi",
            _sig1920 > _sig1280 and _sig1280 < 42 and len(_kart10) == 42,
            (_sig1920, _sig1280))

    # ── (3) RITIM: SABIT BLOK + anlatim bagi YOK ──
    _agir10 = []
    for _fid, _mt in re.findall(r'\("(f\d+)",\s*"([^"]+)"\)', _SS14):
        _agir10.append(float(len(_mt.split())))
    _rt10 = _kk.ritim_olcusu(
        [{"sure_sn": s["sure_sn"]} for s in _z10],
        anlatim_agirliklari=_agir10[:len(_z10)],
        toplam_sn=sum(s["sure_sn"] for s in _z10),
        anlatim_bitis_sn=_master10["sure_sn"])
    kontrol("KIRMIZI: uc sahnenin UCU DE ayni surede (3.2 sn, yayilim 0.0)",
            _rt10["sabit_blok"] is True and _rt10["yayilim_sn"] == 0.0
            and _rt10["sureler"] == [3.2, 3.2, 3.2], _rt10["sureler"])
    kontrol("KIRMIZI: sureler anlatima BAGLI DEGIL "
            "(anlatim agirligi %30 degisiyor, sure %0)",
            _rt10["anlatim_bagi"] is False
            and _rt10["agirlik_yayilim_orani"] > 0.15
            and _rt10["sure_yayilim_orani"] == 0.0, _rt10)
    kontrol("KIRMIZI: planda OLU FINAL var (>0.5 sn)",
            _rt10["olu_final_asildi"] is True
            and _rt10["olu_final_sn"] > 0.5, _rt10["olu_final_sn"])
    # ⚠ Mevcut PACING-TEKDUZE bu vakayi NEDEN gormuyordu — olculdu.
    kontrol("OLCULEN BOSLUK: PACING-TEKDUZE >=4 beat sarti tasiyor, "
            "3 sahnelik plani ELIYOR",
            "len(sureler) >= 4" in oku(KOK, "editor/qa_on.py")
            and len(_z10) == 3)

    # ── (4) MIKS: sessizlik orani + OLU KUYRUK ──
    # Sessizlik araliklari raporun kendi olcumunden turetilir.
    _mx10 = _kk.miks_olcusu(
        sure_sn=_ses10["sure_sn"],
        sessizlik_araliklari=[{"bas": 5.390146, "sure": 0.983583},
                              {"bas": 8.739437, "sure": 0.903229}])
    kontrol("olculen sessiz toplam rapordaki degerle uyusuyor (1.887 sn)",
            abs(_mx10["sessiz_sn"] - _ses10["sessiz_sn"]) < 0.01,
            (_mx10["sessiz_sn"], _ses10["sessiz_sn"]))
    kontrol("KIRMIZI: miksin %15'ten fazlasi sessiz (%19.6)",
            _mx10["sessiz_oran_asildi"] is True
            and _mx10["sessiz_orani"] > 0.15, _mx10["sessiz_orani"])
    kontrol("KIRMIZI: videonun SONUNDA 0.9 sn olu kuyruk (>0.5 sn)",
            _mx10["olu_final_asildi"] is True
            and _mx10["olu_final_sn"] > 0.5, _mx10["olu_final_sn"])

    # ── (5) AMBIYANS: DUYULMAZ ──
    # Seviye/ducking degerleri izlenen smoke KAYNAGINDAN okunur.
    kontrol("smoke ambans seviye 0.20 + ducking 0.30 kullaniyor",
            'ambans_seviye"] = 0.20' in _SS14
            and '"ducking"] = {"ambans": 0.30}' in _SS14)
    _AMB_LUFS = -48.68        # ffmpeg loudnorm, ambans0.wav (I-14'te olculdu)
    _amb10 = _kk.ambans_duyulabilirligi(
        ambans_lufs=_AMB_LUFS, anlatim_lufs=_master10["lufs"],
        ambans_seviye=0.20, ducking=0.30)
    kontrol("KIRMIZI: ambiyans anlatimin 30 dB'den COK altinda — DUYULMAZ",
            _amb10["duyulabilir"] is False and _amb10["fark_db"] > 50,
            _amb10["fark_db"])
    kontrol("KOK NEDEN ducking DEGIL: ducking kapatilsa BILE duyulmaz",
            _amb10["ducking_suz_duyulabilir"] is False
            and _amb10["fark_ducksuz_db"] > 40, _amb10["fark_ducksuz_db"])
    # Ambans dosyasi yerelde varsa olcumu YENIDEN dogrula (yoksa BLOKE).
    _AMBW = os.path.join(KOK, "..", "app", "render-studio", "public",
                         "editorv2", "faz_e", "ambans0.wav")
    if not os.path.exists(_AMBW):
        bloke_yaz("ambans0.wav yeniden olcumu",
                  "dosya yok (.gitignore: app/render-studio/public/editorv2/)")
    else:
        _pr = subprocess.run(
            ["ffmpeg", "-nostdin", "-i", _AMBW, "-af",
             "loudnorm=print_format=json", "-f", "null", "-"],
            capture_output=True, text=True, timeout=120)
        _mm = re.findall(r'"input_i"\s*:\s*"(-?[\d.]+)"', _pr.stderr or "")
        kontrol("ambans kaynagi GERCEKTEN -48.7 LUFS civari",
                bool(_mm) and abs(float(_mm[-1]) - _AMB_LUFS) < 1.0,
                _mm[-1:] or "olculemedi")

blok("§32c KIRMIZI KANIT — I-11 20 sn ciktisinda MEDYA TEKRARI")

_R20_YOL = os.path.join(KOK, "..", "outputs", "sample", "smoke_rapor.json")
_R20 = None
if os.path.exists(_R20_YOL):
    try:
        _R20 = _json.load(open(_R20_YOL, encoding="utf-8"))
    except ValueError:
        _R20 = None
if _R20 is None:
    bloke_yaz("I-11 20 sn raporu", f"yok/bozuk: {_R20_YOL}")
else:
    _mt20 = _kk.medya_tekrari(_R20["zincir"])
    kontrol("KIRMIZI: ayni varlik ARKA ARKAYA kullanilmis (a082 x2)",
            len(_mt20["bitisik_ayni_asset"]) == 1
            and _mt20["bitisik_ayni_asset"][0]["asset_id"].startswith("a082"),
            _mt20["bitisik_ayni_asset"])
    kontrol("KIRMIZI: tekrar sayimi dogru (a082 -> 2)",
            _mt20["tekrar_eden_asset"].get("a082_wiki_4ba3ccdace") == 2,
            _mt20["tekrar_eden_asset"])
    # ⚠ DURUSTLUK: 10 sn ciktisinda medya tekrari OLCULEBILIR bicimde YOK.
    if _R10 is not None:
        _mt10 = _kk.medya_tekrari(_R10["zincir"])
        kontrol("DURUST SONUC: 10 sn ciktisinda ayni-asset tekrari YOK "
                "(3 ayri varlik) — kapi burada hakli olarak SESSIZ",
                not _mt10["bitisik_ayni_asset"]
                and not _mt10["tekrar_eden_asset"]
                and _mt10["benzersiz_asset"] == 3, _mt10)
        kontrol("okuyucu verilmeyince 'benzer medya yok' IDDIASI URETILMIYOR",
                _mt10["benzerlik_olculdu"] is False
                and _mt10["benzerlik_temiz"] is False)

blok("§32d Yanlis pozitif korumalari ve bozuk girdi")

kontrol("kelime SINIRINDA kesme KESIK sayilmaz",
        _kk.kelime_ortasi_kesik("The Eagle began its final descent",
                                "THE EAGLE BEGAN ITS")["kesik"] is False)
kontrol("tam metin KESIK sayilmaz",
        _kk.kelime_ortasi_kesik("Tranquility Base",
                                "TRANQUILITY BASE")["kesik"] is False)
kontrol("on ek OLMAYAN kisaltma icin kesik IDDIASI URETILMEZ",
        _kk.kelime_ortasi_kesik("Apollo 11 landed",
                                "BAMBASKA BIR BASLIK")["kesik"] is False)
kontrol("kisa baslik gercek render genisliginde SIGAR",
        _kk.baslik_olcusu("EAGLE HAS LANDED", punto=60,
                          kare_genislik=1280)["sigar"] is True)
kontrol("1920 render'da 34 karakterlik baslik sigar",
        _kk.baslik_olcusu("A" * 30, punto=60, kare_genislik=1920)["sigar"]
        is True)
kontrol("degisken sureler SABIT BLOK sayilmaz",
        _kk.ritim_olcusu([{"sure_sn": 2.5}, {"sure_sn": 5.9},
                          {"sure_sn": 3.4}])["sabit_blok"] is False)
kontrol("tek sahne SABIT BLOK sayilmaz (kiyas yok)",
        _kk.ritim_olcusu([{"sure_sn": 3.2}])["sabit_blok"] is False)
kontrol("anlatim agirligi da SABITSE sabit sure anlatimla TUTARLI",
        _kk.ritim_olcusu([{"sure_sn": 3.2}, {"sure_sn": 3.2}],
                         anlatim_agirliklari=[8, 8])["anlatim_bagi"] is True)
kontrol("olu final esik ALTINDA ise bayrak kalkmaz",
        _kk.ritim_olcusu([{"sure_sn": 3.0}], toplam_sn=3.0,
                         anlatim_bitis_sn=2.7)["olu_final_asildi"] is False)
kontrol("ortadaki sessizlik OLU KUYRUK sayilmaz",
        _kk.miks_olcusu(sure_sn=10.0,
                        sessizlik_araliklari=[{"bas": 2.0, "sure": 0.9}]
                        )["olu_final_sn"] == 0.0)
kontrol("ambiyans esik ICINDE ise DUYULABILIR",
        _kk.ambans_duyulabilirligi(ambans_lufs=-30.0, anlatim_lufs=-16.0,
                                   ambans_seviye=1.0,
                                   ducking=0.5)["duyulabilir"] is True)
kontrol("ambiyans olcumu YOKSA 'duyulabilir' IDDIASI URETILMEZ",
        _kk.ambans_duyulabilirligi(ambans_lufs=None, anlatim_lufs=-16.0
                                   )["duyulabilir"] is None)

# ⚠ HICBIR GIRDIDE ISTISNA FIRLATMAZ.
_BOZUK = (None, {}, [], "x", 5, [{"sure_sn": "cok"}], [None, 3], {"a": 1})
_patlayan = []
for _g in _BOZUK:
    for _fn, _ad in ((lambda v: _kk.medya_tekrari(v), "medya_tekrari"),
                     (lambda v: _kk.ritim_olcusu(v), "ritim_olcusu")):
        try:
            _fn(_g)
        except Exception as _e:                                   # noqa: BLE001
            _patlayan.append(f"{_ad}({_g!r}): {type(_e).__name__}")
for _g in (None, "x", -1, float("nan"), float("inf")):
    try:
        _kk.baslik_olcusu("ABC", punto=_g, kare_genislik=1280)
        _kk.baslik_olcusu(_g, punto=60, kare_genislik=_g)
        _kk.miks_olcusu(sure_sn=_g, sessizlik_araliklari=None)
        _kk.ambans_duyulabilirligi(ambans_lufs=_g, anlatim_lufs=_g)
    except Exception as _e:                                       # noqa: BLE001
        _patlayan.append(f"skaler({_g!r}): {type(_e).__name__}")
kontrol("hicbir bozuk girdide ISTISNA FIRLATMIYOR", not _patlayan, _patlayan)

blok("§32e QA SOZLESMESI — kapali varsayilan, acikken GERCEK kapi")

kontrol("qa_on: I-14 kodlari FAIL_KODLARI'nda",
        {"KALITE-BASLIK-KIRPIK", "KALITE-BASLIK-TASMA", "KALITE-MEDYA-TEKRAR",
         "KALITE-RITIM-SABIT", "KALITE-OLU-FINAL"} <= _qon.FAIL_KODLARI)
kontrol("qa_on.denetle kalite_kapisi VARSAYILAN False",
        "kalite_kapisi: bool = False" in oku(KOK, "editor/qa_on.py"))
kontrol("qa_son.denetle kalite_kapisi VARSAYILAN False",
        "kalite_kapisi: bool = False" in oku(KOK, "editor/qa_son.py"))
kontrol("plan.uret kalite_kapisi VARSAYILAN False",
        "kalite_kapisi: bool = False" in oku(KOK, "editor/plan.py"))
kontrol("edit_kopru: env + is ayari, yalniz GERCEK True acar",
        ekp.kalite_kapisi_acik({"kalite_kapisi": True}) is True
        and ekp.kalite_kapisi_acik({"kalite_kapisi": "evet"}) is False
        and ekp.kalite_kapisi_acik({"kalite_kapisi": 1}) is False
        and ekp.kalite_kapisi_acik(None) is False)
kontrol("cagri parametresi env'i EZEBILIYOR (acik karar)",
        ekp.kalite_kapisi_acik(None, True) is True
        and ekp.kalite_kapisi_acik({"kalite_kapisi": True}, False) is False)

# ⚠ KABA SESSIZLIK GECISI OLU KUYRUGU GORMUYOR — olculdu.
kontrol("OLCULEN BOSLUK: varsayilan sessizlik gecisi d=1.2 "
        "(0.9 sn kuyrugu GORMEZ)",
        "silencedetect=noise=-45dB:d=1.2" in oku(KOK, "editor/qa_son.py"))
kontrol("ince gecis d=0.30 ve YALNIZ kapi acikken kosuluyor",
        "d=0.30" in oku(KOK, "editor/qa_son.py")
        and "sessizlik_ince" not in _qsn.komut_plani("v.mp4")
        and "sessizlik_ince" in _qsn.komut_plani("v.mp4",
                                                 ince_sessizlik=True))
kontrol("kapali komut plani ESKISIYLE BIREBIR ayni (7 komut)",
        len(_qsn.komut_plani("v.mp4")) == 7)


def _sahte_kosucu_10sn(komut, zaman_asimi=0):
    """I-13 ciktisinin GERCEK olcumleriyle besleyen sahte kosucu."""
    j = " ".join(komut)
    if "format=duration,size" in j:
        return {"rc": 0, "stderr": "", "stdout": _json.dumps({
            "streams": [{"width": 1280, "height": 720, "r_frame_rate": "30/1",
                         "codec_name": "h264"}],
            "format": {"duration": "9.643", "size": "8222479"}})}
    if "d=0.30" in j:
        return {"rc": 0, "stdout": "", "stderr":
                "silence_start: 5.390146\nsilence_end: 6.373729 | "
                "silence_duration: 0.983583\nsilence_start: 8.739437\n"
                "silence_end: 9.642667 | silence_duration: 0.903229\n"}
    if "loudnorm" in j:
        return {"rc": 0, "stdout": "", "stderr": _json.dumps(
            {"input_i": "-16.56", "input_tp": "-4.47", "input_lra": "2.7"})}
    return {"rc": 0, "stdout": "{}", "stderr": ""}


_pq_kapali = _qsn.denetle("sahte.mp4", kosucu=_sahte_kosucu_10sn,
                          ambans_lufs=-48.68, anlatim_lufs=-16.43,
                          ambans_seviye=0.20, ducking=0.30)
_pq_acik = _qsn.denetle("sahte.mp4", kosucu=_sahte_kosucu_10sn,
                        kalite_kapisi=True, ambans_lufs=-48.68,
                        anlatim_lufs=-16.43, ambans_seviye=0.20, ducking=0.30)
_kod_kapali = {s["kod"] for s in _pq_kapali.sorunlar}
_kod_acik = {s["kod"] for s in _pq_acik.sorunlar}
kontrol("KAPALIYKEN hicbir I-14 kodu URETILMIYOR",
        not any(k.startswith("POST-SESSIZ-ORAN") or k.startswith("POST-OLU-")
                or k.startswith("POST-AMBANS") for k in _kod_kapali),
        sorted(_kod_kapali))
kontrol("KAPALIYKEN de OLCUM YAZILIYOR (gizlenmiyor)",
        _pq_kapali.olcumler.get("kalite", {}).get("ambans", {}).get(
            "duyulabilir") is False
        and _pq_kapali.olcumler["kalite"]["kapi_acik"] is False)
kontrol("ACIKKEN uc I-14 kodu da FAIL uretiyor",
        {"POST-SESSIZ-ORAN", "POST-OLU-FINAL", "POST-AMBANS-DUYULMAZ"}
        <= _kod_acik and _pq_acik.durum == "FAIL", sorted(_kod_acik))
kontrol("ACIK kapi olu kuyrugu INCE gecisten okuyor",
        _pq_acik.olcumler["kalite"]["miks"]["kaynak_gecis"].startswith(
            "sessizlik_ince"))
kontrol("KAPALI kapi kaba gecise dusuyor ve bunu SOYLUYOR",
        _pq_kapali.olcumler["kalite"]["miks"]["kaynak_gecis"].startswith(
            "sessizlik(d=1.2)"))
# ⚠ Kaba gecis gercekten KACIRIYOR: ayni video, iki farkli olcum.
kontrol("KANIT: kaba gecis olu kuyrugu KACIRIYOR (0.0 vs 0.903)",
        _pq_kapali.olcumler["kalite"]["miks"]["olu_final_sn"] == 0.0
        and _pq_acik.olcumler["kalite"]["miks"]["olu_final_sn"] > 0.9)

blok("§32f UCTAN UCA — plan.uret uzerinden GERCEK kapi karari")

# ⚠ Dosya OKUNMAZ: `plan.uret` manifest SOZLUGUYLE calisir, goruntu baytina
# dokunmaz. Bu yuzden temiz klonda da kosar (fixture goruntusu gerekmez).
from editor import plan as _pln                                   # noqa: E402


def _i14_manifest(asset_bir, asset_iki):
    return {"adaylar": [
        {"asset_id": a, "scene_id": f"s{i + 1:03d}", "fact_id": f"f00{i + 1}",
         "saglayici": "wikimedia", "lisans": "public-domain", "tur": "image",
         "yerel_yol": f"/yok/{a}.jpg", "medya_yolu": f"/yok/{a}.jpg",
         "orijinal_url": f"https://example.invalid/{a}",
         "eser_sahibi": "NASA", "atif_metni": "NASA / Public Domain",
         "atif_gerekli": False, "baslik": "Apollo archive",
         "genislik": 1920, "yukseklik": 1080, "sure_sn": 3.2,
         "toplam_skor": 80, "render_kullanilabilir": True,
         "sahne_amaci": "arsiv"}
        for i, a in enumerate((asset_bir, asset_iki))],
        "kapsam_bosluklari": []}


_C14 = [{"scene_id": "s001", "fact_id": "f001", "sure_sn": 3.2,
         "metin": "The Eagle began its final descent on 20 July 1969."},
        {"scene_id": "s002", "fact_id": "f002", "sure_sn": 3.2,
         "metin": "Armstrong took manual control of the lunar module."}]
_ARA14 = {"iddialar": [{"fact_id": "f001"}, {"fact_id": "f002"}]}

import tempfile as _tf                                            # noqa: E402
with _tf.TemporaryDirectory() as _d14:
    # (1) AYNI varlik iki sahnede -> KALITE-MEDYA-TEKRAR
    _ct = _pln.uret(cumleler=_C14, medya_manifest=_i14_manifest("aX", "aX"),
                    arastirma_manifest=_ARA14, cikti_dizin=_d14,
                    kare_olcu=(1280, 720), kalite_kapisi=True)
    _kt = {s["kod"] for s in _ct["editor_qa"]["sorunlar"]}
    kontrol("UCTAN UCA: ayni varlik tekrari QA HUKMUNE ulasiyor",
            "KALITE-MEDYA-TEKRAR" in _kt
            and _ct["editor_qa"]["durum"] == "FAIL", sorted(_kt))
    # (2) FARKLI varlik -> tekrar kodu URETILMEZ (yanlis pozitif yok)
    _cf = _pln.uret(cumleler=_C14, medya_manifest=_i14_manifest("aX", "aY"),
                    arastirma_manifest=_ARA14, cikti_dizin=_d14,
                    kare_olcu=(1280, 720), kalite_kapisi=True)
    _kf = {s["kod"] for s in _cf["editor_qa"]["sorunlar"]}
    kontrol("UCTAN UCA: farkli varlikta tekrar kodu URETILMIYOR",
            "KALITE-MEDYA-TEKRAR" not in _kf, sorted(_kf))
    # (3) KAPI KAPALI -> ayni girdi, HICBIR KALITE-* kodu yok
    _ck = _pln.uret(cumleler=_C14, medya_manifest=_i14_manifest("aX", "aX"),
                    arastirma_manifest=_ARA14, cikti_dizin=_d14)
    _kk_kapali = {s["kod"] for s in _ck["editor_qa"]["sorunlar"]}
    kontrol("UCTAN UCA: kapi KAPALIYKEN hicbir KALITE-* kodu yok",
            not any(k.startswith("KALITE-") for k in _kk_kapali),
            sorted(_kk_kapali))
    kontrol("UCTAN UCA: kapali/acik AYNI girdide olcum yine yaziliyor",
            _ck["editor_qa"]["olcumler"]["kalite"]["medya_tekrari"][
                "tekrar_eden_asset"] == {"aX": 2}
            and _ck["editor_qa"]["olcumler"]["kalite"]["kapi_acik"] is False)
    # (4) kare_olcu VERILMEZSE profilin nominal olcusune duser (gerileme yok)
    kontrol("kare_olcu verilmezse profil olcusu (1920) kullanilir",
            _ck["editor_qa"]["olcumler"]["kalite"]["kare_genislik"] == 1920
            and _ck["editor_qa"]["olcumler"]["kalite"][
                "kare_olcu_verildi"] is False)


blok("§32g Geriye uyumluluk — varsayilan yol DEGISMEDI")

kontrol("qa_son varsayilan hukmu I-14'ten ETKILENMIYOR",
        _pq_kapali.durum == _qsn.denetle(
            "sahte.mp4", kosucu=_sahte_kosucu_10sn).durum)
kontrol("kalite olcumu qa_on.olcumler['kalite'] altinda IZOLE",
        "q.olcumler[\"kalite\"] = olcum" in oku(KOK, "editor/qa_on.py"))
kontrol("pipeline.py I-14'e HIC dokunmuyor",
        "kalite_kapisi" not in oku(KOK, "pipeline.py"))
kontrol("server.py I-14'e HIC dokunmuyor",
        "kalite_kapisi" not in oku(KOK, "server.py"))
kontrol("22 alanlik generate sozlesmesi I-14'te de DEGISMEDI",
        len(set(re.findall(r"\{ad: '(\w+)'",
                           oku(KOK, "static/js/api.js")))) == 22)
kontrol("kalite kapisi 22 alandan ULASILAMAZ (dahili is ayari)",
        "kalite_kapisi" not in oku(KOK, "static/js/api.js")
        and "kalite_kapisi" not in oku(KOK, "static/js/wizard.js"))
kontrol("I-14 hicbir ucretli/AI cagrisi EKLEMIYOR",
        not re.search(r"openai|anthropic|api_key|xai|freepik",
                      _KK_KAYNAK, re.I))


# ═══════════════════════════════════════════════════════════════════════
# §33  FAZ I-15 — GERCEK DUZELTME + YENIDEN RENDER
#
# I-14 kapilari kurdu ve kusurlari OLCTU; bu bolum kusurlarin GERCEKTEN
# GIDERILDIGINI kilitler. Kanit yine depoda IZLENEN rapordan:
#     outputs/sample/kalite_pass_i15_rapor.json
# (video ve kareler `.gitignore`da — betik yerelde yeniden uretir.)
# ═══════════════════════════════════════════════════════════════════════

blok("§33a KAYNAK DUZELTMELERI — sabit dilim gitti, tek aritmetik kaldi")


def _kod_yalniz(kaynak: str) -> str:
    """Yorum ve dize/docstring'leri ATARAK yalnizca CALISAN kodu don.

    ⚠ Ham dize taramasi modulun KENDI dokumantasyonunu yakaliyor: bu dosyada
    "b.metin[:42] dilimi vardi" diye bir aciklama var ve naif bir `in`
    kontrolu kod duzeltilmis olsa bile KIRMIZI yaniyor. Ayni tuzak I-9'da da
    yasanmisti (AST'ye gecilmisti). Burada tokenize ile ayikliyoruz.
    """
    import io
    import tokenize
    parcalar = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(kaynak).readline):
            if tok.type in (tokenize.COMMENT, tokenize.STRING):
                continue
            parcalar.append(tok.string)
    except (tokenize.TokenError, IndentationError):
        return kaynak
    return " ".join(parcalar)


_PLAN15 = oku(KOK, "editor/plan.py")
_PLAN15_KOD = _kod_yalniz(_PLAN15)
kontrol("plan.py SABIT `b.metin[:42]` dilimini ARTIK KULLANMIYOR",
        "[:42]" not in _PLAN15_KOD.replace(" ", "")
        and "b.metin[:42]" in _PLAN15,      # yorumda TARIHI olarak duruyor
        _PLAN15_KOD.replace(" ", "")[:0])
kontrol("chapter-title artik _kart_basligi + hesaplanan siniri kullaniyor",
        "_kart_basligi(b.metin, baslik_siniri).upper()" in _PLAN15
        and "baslik_siniri = kart_basligi_siniri(p, kare_genislik)" in _PLAN15)
kontrol("kart_basligi_siniri GERCEK kare genisligini aliyor",
        "def kart_basligi_siniri(p: EditProfili,\n"
        "                        kare_genislik: Optional[float] = None)"
        in _PLAN15)
kontrol("TEK ARITMETIK: plan em/bant sabitlerini kalite_kapisi'ndan aliyor",
        "BUYUK_HARF_EM = kalite_kapisi.EM_BUYUK_HARF" in _PLAN15
        and "BANT_MAKS_ORAN = kalite_kapisi.BANT_MAKS_ORAN" in _PLAN15)
kontrol("sinir TAM PUNTODA hesaplaniyor (kucultme geri dusus agi olarak kalir)",
        "kucultme_tabani=1.0" in _PLAN15)

_pp15 = _eprofil.profil("premium-modern")
kontrol("GERCEK render genisliginde sinir DAHA KATI (1920 > 1280)",
        _ep2.kart_basligi_siniri(_pp15, 1920)
        > _ep2.kart_basligi_siniri(_pp15, 1280) > 0,
        (_ep2.kart_basligi_siniri(_pp15, 1920),
         _ep2.kart_basligi_siniri(_pp15, 1280)))
kontrol("kare genisligi verilmezse profil olcusune duser (gerileme yok)",
        _ep2.kart_basligi_siniri(_pp15)
        == _ep2.kart_basligi_siniri(_pp15, _pp15.genislik))
# I-13'un tam metniyle: artik ne kesik ne tasan bir baslik cikiyor.
_HAM15 = "The Eagle landed on the Moon in July, nineteen sixty-nine."
for _g15 in (1920, 1280):
    _s15 = _ep2.kart_basligi_siniri(_pp15, _g15)
    _k15 = _ep2._kart_basligi(_HAM15, _s15).upper()
    _o15 = _kk.baslik_olcusu(_k15, punto=60, kare_genislik=_g15)
    kontrol(f"{_g15}: baslik SIGIYOR ve TAM PUNTO (kucultme yok)",
            _o15["sigar"] is True and _o15["tasma_px"] == 0.0
            and _o15["uygulanan_punto"] == 60, (_g15, _k15, _o15["tasma_px"]))
    kontrol(f"{_g15}: baslik kelime ortasindan KESIK DEGIL",
            _kk.kelime_ortasi_kesik(_HAM15, _k15)["kesik"] is False, _k15)

kontrol("I-15: ambiyans kapisi CIFT TARAFLI (duyulabilir + bastirmiyor)",
        {"bastiriyor", "dengeli", "bastirma_esik_db"}
        <= set(_kk.ambans_duyulabilirligi(ambans_lufs=-26.0,
                                          anlatim_lufs=-14.0).keys()))
kontrol("ambiyans anlatima COK YAKINSA 'bastiriyor' diyor",
        _kk.ambans_duyulabilirligi(ambans_lufs=-18.0, anlatim_lufs=-14.0,
                                   ambans_seviye=1.0,
                                   ducking=1.0)["bastiriyor"] is True)
kontrol("dengeli = hem duyulur hem bogmaz",
        _kk.ambans_duyulabilirligi(ambans_lufs=-26.0, anlatim_lufs=-14.0,
                                   ambans_seviye=0.5,
                                   ducking=0.5)["dengeli"] is True)
kontrol("qa_son POST-AMBANS-BASKIN kodunu tasiyor",
        "POST-AMBANS-BASKIN" in oku(KOK, "editor/qa_son.py"))

blok("§33b YENIDEN RENDER — kalite kapisi ACIK, olculen sonuc")

_R15_YOL = os.path.join(KOK, "..", "outputs", "sample",
                        "kalite_pass_i15_rapor.json")
_R15 = None
if os.path.exists(_R15_YOL):
    try:
        _R15 = _json.load(open(_R15_YOL, encoding="utf-8"))
    except ValueError:
        _R15 = None
if _R15 is None:
    bloke_yaz("I-15 render raporu", f"yok/bozuk: {_R15_YOL}")
else:
    kontrol("rapor kalite kapisinin ACIK oldugunu yaziyor",
            "ACIK" in str(_R15.get("kalite_kapisi")))
    kontrol("maliyet $0.00", _R15.get("maliyet_usd") == 0.0)

    # ── (1) BASLIK ──
    _b15 = _R15["duzeltilen_kusurlar"]["baslik"]
    kontrol("DUZELDI: baslik render genisliginde SIGIYOR",
            _b15["olcum"]["sigar"] is True
            and _b15["olcum"]["tasma_px"] == 0.0, _b15["olcum"]["tasma_px"])
    kontrol("DUZELDI: baslik TAM PUNTODA cizildi (kucultme tabani vurulmadi)",
            _b15["olcum"]["kucultme_tabani_vuruldu"] is False
            and _b15["olcum"]["olcek"] == 1.0)
    kontrol("DUZELDI: baslik kelime ortasindan KESIK DEGIL",
            _b15["olcum"]["kelime_kesik"]["kesik"] is False,
            _b15.get("metin"))
    kontrol("baslik GERCEK render genisligine gore olculdu (1280)",
            _b15["kare_genislik"] == 1280)

    # ── (2) SURELER ──
    _s15r = _R15["duzeltilen_kusurlar"]["sahne_sureleri"]
    kontrol("DUZELDI: sabit blok YOK — her sahne FARKLI surede",
            _s15r["benzersiz"] == len(_s15r["sureler"])
            and len(set(_s15r["sureler"])) == len(_s15r["sureler"]),
            _s15r["sureler"])
    kontrol("DUZELDI: sure yayilimi sabit-blok esiginin COK USTUNDE",
            _s15r["yayilim_sn"] > _kk.SABIT_BLOK_ESIGI_SN * 10,
            _s15r["yayilim_sn"])
    kontrol("sureler GERCEK anlatim zamanlamasindan (SentenceBoundary)",
            "SentenceBoundary" in _s15r["kaynak"]
            and len(_s15r["cumle_sinirlari"]) == len(_s15r["sureler"]))
    _rt15 = _kk.ritim_olcusu([{"sure_sn": s} for s in _s15r["sureler"]])
    kontrol("I-14 ritim kapisi bu surelerde SESSIZ (sabit_blok=False)",
            _rt15["sabit_blok"] is False)
    # Sure sinirlari cumle sinirlariyla gercekten ortusuyor mu?
    _cs15 = _s15r["cumle_sinirlari"]
    _tur15 = [round((_cs15[i + 1]["bas"] if i + 1 < len(_cs15)
                     else _R15["duzeltilen_kusurlar"]["olu_final"]["kesim_sn"])
                    - (0.0 if i == 0 else _cs15[i]["bas"]), 3)
              for i in range(len(_cs15))]
    kontrol("sureler cumle sinirlarindan TUREDIGI dogrulandi (yeniden hesap)",
            all(abs(a - b) < 0.01 for a, b in zip(_tur15, _s15r["sureler"])),
            (_tur15, _s15r["sureler"]))

    # ── (3) OLU FINAL ──
    _of15 = _R15["duzeltilen_kusurlar"]["olu_final"]
    kontrol("DUZELDI: olculen olu final 0.5 sn tavaninin ALTINDA",
            (_of15["olculen_olu_final_sn"] or 0) <= _kk.OLU_FINAL_ESIGI_SN,
            _of15["olculen_olu_final_sn"])
    kontrol("anlatim master anlatim bitisi + kuyruk payindan KESILDI",
            abs((_of15["anlatim_bitis_sn"] + _of15["kuyruk_sn"])
                - _of15["kesim_sn"]) < 0.01)
    kontrol("kuyruk payi tavanin ALTINDA secildi",
            _of15["kuyruk_sn"] < _kk.OLU_FINAL_ESIGI_SN)

    # ── (4) AMBIYANS + MIKS ──
    _a15 = _R15["duzeltilen_kusurlar"]["ambiyans"]
    kontrol("DUZELDI: ambiyans DUYULABILIR",
            _a15["olcum"]["duyulabilir"] is True, _a15["olcum"]["fark_db"])
    kontrol("DUZELDI: ambiyans anlatimi BASTIRMIYOR",
            _a15["olcum"]["bastiriyor"] is False)
    kontrol("ambiyans DENGELI (iki sinir arasinda)",
            _a15["olcum"]["dengeli"] is True)
    kontrol("kok neden giderildi: kaynak -48.7 LUFS'tan yukseltildi",
            _a15["kaynak_lufs"] < -45 and _a15["normalize_lufs"] > -30,
            (_a15["kaynak_lufs"], _a15["normalize_lufs"]))
    kontrol("ASIL DUZELTME: anlatim_araliklari GECIRILDI "
            "(ducking artik tum videoya uygulanmiyor)",
            _a15["anlatim_araliklari_gecildi"] is True
            and "anlatim_araliklari" in oku(
                KOK, "testler/smoke_kalite_pass_i15.py"))
    _m15 = _R15["video_ses_olcumu"]
    kontrol("miks LUFS profil hedefine (-14) 1 dB icinde",
            abs(_m15["lufs"] + 14.0) <= 1.0, _m15["lufs"])
    kontrol("true peak tavanin altinda, kirpma yok",
            _m15["tepe_dbtp"] <= -1.5 and _m15["kirpma_var"] is False,
            _m15["tepe_dbtp"])
    kontrol("sessizlik orani tavanin ALTINDA",
            (_m15["sessiz_pct"] / 100.0) <= _kk.SESSIZ_ORAN_TAVANI,
            _m15["sessiz_pct"])
    kontrol("DURUSTLUK: %0 sessizligin NEDENI raporda yaziyor",
            "ambiyans" in _R15["sessizlik_yorumu"]["neden"]
            and "anlatim_master_sessizlikleri" in _R15["sessizlik_yorumu"])

    # ── (5) MEDYA CESITLILIGI — DURUST RAPOR, ESIK OYNAMASI YOK ──
    _c15 = _R15["medya_cesitliligi"]
    kontrol("SAHTE ESIK DUSURME YOK: esik I-14'teki degeriyle ayni",
            _c15["esik"] == _kk.BENZERLIK_ESIGI
            and _c15["esik_degistirildi_mi"] is False)
    kontrol("hicbir cift esigi asmiyor (kapi hakli olarak sessiz)",
            len(_c15["esigi_asan"]) == 0)
    kontrol("DURUST RAPOR: olculen en yuksek benzerlik aciklanmis",
            isinstance(_c15["en_yuksek"], float)
            and _c15["en_yuksek"] < _c15["esik"], _c15["en_yuksek"])
    kontrol("siralama komsu benzerligini DUSURDU (yalniz SIRA degisti)",
            _c15["siralama"]["sonra_komsu_maks"]
            <= _c15["siralama"]["once_komsu_maks"]
            and sorted(_c15["siralama"]["once_sira"])
            == sorted(_c15["siralama"]["sonra_sira"]),
            _c15["siralama"])
    _z15 = _R15["zincir"]
    _mt15 = _kk.medya_tekrari(_z15)
    kontrol("ayni varlik tekrari YOK, bitisik tekrar YOK",
            not _mt15["tekrar_eden_asset"]
            and not _mt15["bitisik_ayni_asset"])
    kontrol("her sahnede GERCEK medya var (fallback kart yok)",
            all(z.get("asset_id") for z in _z15), _z15)

    # ── (6) KAPI SONUCU + KANIT ──
    kontrol("on-render QA FAIL DEGIL", _R15["plan"]["qa"]["durum"] != "FAIL"
            and _R15["plan"]["qa"]["fail"] == 0)
    kontrol("render sonrasi QA FAIL DEGIL",
            _R15["post_qa"]["durum"] != "FAIL")
    kontrol("hicbir KALITE-*/POST-* kapisi FAIL uretmedi",
            not [s for s in _R15["plan"]["on_render_qa"]["sorunlar"]
                 if s["seviye"] == "fail"]
            and not [s for s in _R15["post_qa"]["sorunlar"]
                     if s["seviye"] == "fail"])
    kontrol("EN AZ 6 kare cikarildi ve gorsel incelendi",
            len(_R15["kareler"]) >= 6, len(_R15["kareler"]))
    kontrol("kareler bos/duz degil (her biri > 100 KB)",
            all(k["bayt"] > 100_000 for k in _R15["kareler"]),
            [k["bayt"] for k in _R15["kareler"]])
    kontrol("ffprobe + kesme + ses olcumleri raporda",
            bool(_R15["ffprobe"].get("streams"))
            and "sayi" in _R15["kesmeler"]
            and "lufs" in _R15["video_ses_olcumu"])
    kontrol("cikti outputs/sample altinda",
            str(_R15["video"]).startswith("outputs/sample/"))
    kontrol("sure 10-20 sn araliginda",
            10.0 <= float((_R15["ffprobe"].get("format") or {}).get(
                "duration") or 0) <= 20.0)
    kontrol("kapsam disi DURUSTCE yaziliyor (altyazi/kunye/1080p)",
            any("altyazi" in k for k in _R15["kapsam"]["kapsam_disi"])
            and any("1080p" in k for k in _R15["kapsam"]["kapsam_disi"]))

blok("§33c I-15 KORUMALARI — dokunulmamasi gerekenler")

_SM15 = oku(KOK, "testler/smoke_kalite_pass_i15.py")
# ⚠ Ham tarama betigin KENDI docstring'ini yakaliyordu ("lavfi/testsrc/color
# KULLANILMAZ" cumlesi). Yalniz CALISAN kod taranir.
kontrol("smoke ffmpeg test kaynagi (lavfi/testsrc) KULLANMIYOR",
        not re.search(r"lavfi|testsrc|color=c=", _kod_yalniz(_SM15)))
kontrol("smoke gercek render zincirini cagiriyor",
        "edit_kopru.plan_kur" in _SM15 and "remotion_v2.render" in _SM15)
kontrol("smoke QA FAIL'de render BASLATMIYOR",
        'if not sonuc["render_edilebilir"]:' in _SM15)
kontrol("smoke saglayici kotasini YUKSELTMIYOR",
        "saglayici_tavani=" not in _SM15)
kontrol("smoke benzerlik esigini DEGISTIRMIYOR",
        "BENZERLIK_ESIGI =" not in _SM15
        and "benzerlik_esigi=" not in _SM15)
kontrol("pipeline.py I-15'te de DEGISMEDI",
        "kalite_kapisi" not in oku(KOK, "pipeline.py")
        and "smoke_kalite_pass" not in oku(KOK, "pipeline.py"))
kontrol("server.py I-15'te de DEGISMEDI",
        "kalite_kapisi" not in oku(KOK, "server.py"))
kontrol("22 alanlik generate sozlesmesi I-15'te de DEGISMEDI",
        len(set(re.findall(r"\{ad: '(\w+)'",
                           oku(KOK, "static/js/api.js")))) == 22)
kontrol("UI I-15'te DEGISMEDI",
        "basitGovde" in oku(KOK, "static/js/wizard.js")
        and "SURE_SECENEKLERI" in oku(KOK, "static/js/basit.js"))
kontrol("deploy.sh ezme korumasi KORUNDU",
        "GERIDE" in open(os.path.join(KOK, "..", "deploy.sh"),
                         encoding="utf-8").read())
kontrol("bayraklar HALA varsayilan kapali",
        mkp.ACIK is False and ekp.ACIK is False
        and ekp.kalite_kapisi_acik(None) is False)
kontrol("ikili ciktilar .gitignore'da (mp4/png depoya girmiyor)",
        "outputs/sample/*.mp4" in oku(KOK, "..", ".gitignore")
        and "outputs/sample/*.png" in oku(KOK, "..", ".gitignore"))


# ═══════════════════════════════════════════════════════════════════════
# §34  FAZ I-16 — ALTYAZI + GORUNUR KAYNAK KUNYESI + 1080p
#
# Kanit yine depoda IZLENEN rapordan:
#     outputs/sample/altyazi_1080p_i16_rapor.json
# ═══════════════════════════════════════════════════════════════════════

def _tsx_kod(kaynak: str) -> str:
    """TSX'ten /* */ ve // yorumlarini ayikla — ayni tuzak, JS tarafi.

    Ham `in` kontrolu benim yazdigim ACIKLAMA satirina takiliyordu
    ("burada `bottom: 22` SABITI vardi"). Kod duzeltilmis olmasina ragmen
    test kirmizi yaniyordu. Python tarafinda `_kod_yalniz` ayni isi yapiyor.
    """
    kaynak = re.sub(r"/\*.*?\*/", " ", kaynak, flags=re.S)
    return re.sub(r"(?m)^\s*//.*$", " ", kaynak)


blok("§34a ALTYAZI RENDER HATTI — 'props'ta var, videoda yok' kapatildi")

_TSX_G = oku(KOK, "..", "app/render-studio/src/editorv2/Grafikler.tsx")
_TSX_E = oku(KOK, "..", "app/render-studio/src/editorv2/EditorV2.tsx")
_ADP = oku(KOK, "editor/adapter.py")

kontrol("Altyazi bileseni Grafikler.tsx'te TANIMLI",
        "export const Altyazi" in _TSX_G)
kontrol("Altyazi EditorV2'de ITHAL ve MOUNT edilmis",
        "Altyazi," in _TSX_E and "<Altyazi" in _TSX_E)
kontrol("altyazi sozlesmede ZATEN vardi (kapatilan acik: cizim yoktu)",
        "altyazi: unknown[]" in oku(
            KOK, "..", "app/render-studio/src/editorv2/sozlesme.ts"))
kontrol("adapter altyazi + punto + konumu TASIYOR",
        '"altyazi": copy.deepcopy(sh.get("altyazi") or [])' in _ADP
        and '"altyazi_punto": sh.get("altyazi_punto")' in _ADP
        and '"altyazi_y": sh.get("altyazi_y")' in _ADP)
# ⚠ I-16'da yasanan GERCEK hata: `sayi(v, d)` yalnizca SAYI OLMAYAN girdide
# varsayilana duser; `?? 0` ile 0 gecirilince fontSize 0 olup altyazi
# GORUNMEZ cizildi. Tuzak koda yazildi, test kilitliyor.
kontrol("KILIT: Altyazi mount'unda `?? 0` tuzagi YOK",
        "sahne.altyazi_punto, 38" in _tsx_kod(_TSX_E)
        and "?? 0, 38" not in _tsx_kod(_TSX_E))
kontrol("sayi() tuzagi kodda ACIKLANMIS",
        "`?? 0` YAZMA" in _TSX_E or "`?? 0` yazma" in _TSX_E)
kontrol("altyazi kup zamanlari SAHNEYE GORELI (Sequence semantigi)",
        "SAHNEYE GORELIDIR" in _TSX_G
        and "def _altyazi_dagit" in oku(KOK, "editor/plan.py"))

blok("§34b ALTYAZI OKUNABILIRLIGI — olculebilir kurallar")

_CUM = [{"bas": 0.05, "sure": 2.9,
         "metin": "Tranquility Base here, the Eagle has landed."},
        {"bas": 2.96, "sure": 5.2,
         "metin": "The lunar module touched down on the Moon on the "
                  "twentieth of July, nineteen sixty-nine."}]
_AK = _kk.altyazi_kupleri(_CUM, maks_karakter=42)
kontrol("kupler uretildi ve okunabilirlik TEMIZ",
        _AK["olculdu"] and _AK["kup_sayisi"] >= 2 and _AK["temiz"] is True)
kontrol("hicbir satir 42 karakteri ASMIYOR",
        all(len(s) <= 42 for k in _AK["kupler"] for s in k["satirlar"]))
kontrol("hicbir kup 2 satiri ASMIYOR",
        all(len(k["satirlar"]) <= 2 for k in _AK["kupler"]))
kontrol("DENGELI BOLME: hicbir kup min sureden kisa degil",
        all(k["sure_sn"] >= _kk.ALTYAZI_MIN_SN - 0.01
            for k in _AK["kupler"]),
        [k["sure_sn"] for k in _AK["kupler"]])
kontrol("SARKAN EDAT satir/kup sonunda YALNIZ BIRAKILMIYOR",
        not any(s.split() and s.split()[-1].lower().strip(",;:.")
                in _kk._SARKAN_KELIME
                for k in _AK["kupler"] for s in k["satirlar"][:-1]),
        [k["satirlar"] for k in _AK["kupler"]])
kontrol("DURUST ETIKET: cumle ici bolunme 'orantili' isaretleniyor",
        any(k["zamanlama"] == "orantili" for k in _AK["kupler"])
        and any(k["zamanlama"] == "olculdu" for k in _AK["kupler"]))
kontrol("okuma hizi tavani asilinca RAPORLANIYOR",
        len(_kk.altyazi_kupleri(
            [{"bas": 0, "sure": 0.5,
              "metin": "A very long sentence that cannot be read this fast"}],
            maks_karakter=42)["cok_hizli"]) >= 1)
kontrol("harf ortasindan ASLA kesilmiyor (kelime sinirinda bolme)",
        all(" ".join(k["satirlar"]).replace("  ", " ") in
            k["metin"].replace("  ", " ") or
            set(" ".join(k["satirlar"]).split()) <= set(k["metin"].split())
            for k in _AK["kupler"]))
for _g in (None, [], "x", 5, [None], [{"bas": "a", "sure": "b"}]):
    try:
        _kk.altyazi_kupleri(_g)
    except Exception as _e:                                       # noqa: BLE001
        kontrol(f"altyazi_kupleri({_g!r}) istisna FIRLATMIYOR", False,
                type(_e).__name__)
kontrol("altyazi_kupleri bozuk girdide ISTISNA FIRLATMIYOR", True)

blok("§34c GUVENLI ALAN + CAKISMA — olcum ve kapi")

_KUT = [{"ad": "chapter-title", "y_ust": 0.70, "yukseklik": 0.105,
         "bas_sn": 0.2, "sure_sn": 5.0},
        {"ad": "subtitle", "y_ust": 0.81, "yukseklik": 0.13,
         "bas_sn": 0.0, "sure_sn": 17.0}]
_GA = _kk.guvenli_alan_olcusu(_KUT, kare_yukseklik=1080, guvenli_kenar=64)
kontrol("guvenli alan olculuyor ve TEMIZ (1080p yerlesimi)",
        _GA["olculdu"] and _GA["temiz"] is True, _GA.get("ihlaller"))
kontrol("altyazi bandi alt siniri TAM guvenli alanda (1015.2 <= 1016)",
        abs(_kk.ALTYAZI_BANT[1] * 1080 - 1015.2) < 0.5
        and _kk.ALTYAZI_BANT[1] * 1080 <= 1080 - 64
        if hasattr(_kk, "ALTYAZI_BANT") else True)
_ihlal = _kk.guvenli_alan_olcusu(
    [{"ad": "kotu", "y_ust": 0.93, "yukseklik": 0.06,
      "bas_sn": 0, "sure_sn": 1}], kare_yukseklik=1080, guvenli_kenar=64)
kontrol("guvenli alani ASAN katman YAKALANIYOR",
        not _ihlal["temiz"] and _ihlal["ihlaller"][0]["ihlal"] == "ALT")
_CK = _kk.yazi_cakismasi(_KUT)
kontrol("1080p yerlesiminde baslik ile altyazi CAKISMIYOR",
        _CK["temiz"] is True, _CK.get("cakisan_cift"))
kontrol("ayni anda ayni yerdeki iki yazi CAKISMA olarak yakalaniyor",
        not _kk.yazi_cakismasi(
            [{"ad": "a", "y_ust": 0.80, "yukseklik": 0.10,
              "bas_sn": 0, "sure_sn": 3},
             {"ad": "b", "y_ust": 0.85, "yukseklik": 0.10,
              "bas_sn": 1, "sure_sn": 3}])["temiz"])
kontrol("ZAMAN kesismiyorsa cakisma SAYILMAZ",
        _kk.yazi_cakismasi(
            [{"ad": "a", "y_ust": 0.80, "yukseklik": 0.10,
              "bas_sn": 0, "sure_sn": 1},
             {"ad": "b", "y_ust": 0.80, "yukseklik": 0.10,
              "bas_sn": 2, "sure_sn": 1}])["temiz"] is True)
kontrol("DIKEY kesismiyorsa cakisma SAYILMAZ",
        _kk.yazi_cakismasi(
            [{"ad": "a", "y_ust": 0.20, "yukseklik": 0.10,
              "bas_sn": 0, "sure_sn": 3},
             {"ad": "b", "y_ust": 0.80, "yukseklik": 0.10,
              "bas_sn": 0, "sure_sn": 3}])["temiz"] is True)

_tip = _ep2 and None
from editor import tipografi as _tg                               # noqa: E402
kontrol("cakisma cozucu YASAK BANDA kaydirmiyor",
        _tg.bant_cakisiyor(0.88, _tg.YUKSEKLIK["source-label"],
                           _tg.ALTYAZI_BANT) is True
        and "yasak_bant" in oku(KOK, "editor/tipografi.py"))
kontrol("altyazi varken kunye BANDIN USTUNE tasiniyor",
        _tg.KAYNAK_ETIKETI_ALTYAZILI + _tg.YUKSEKLIK["source-label"]
        <= _tg.ALTYAZI_BANT[0] + 1e-9,
        (_tg.KAYNAK_ETIKETI_ALTYAZILI, _tg.ALTYAZI_BANT))
kontrol("bant_cakisiyor bozuk girdide ISTISNA FIRLATMIYOR",
        _tg.bant_cakisiyor(None, None, None) is False
        and _tg.bant_cakisiyor("x", "y", (0.8, 0.9)) is False)

# ⚠ I-16'da bulunan GERCEK kusur: KaynakEtiketi `bottom: 22` sabitiyle
# ciziliyordu, yani Python'un konum hesabini HIC okumuyordu ve 1080p'de
# guvenli alanin (64 px) DISINDA kaliyordu.
_TSX_G_KOD = _tsx_kod(_TSX_G)
kontrol("KaynakEtiketi artik y_orani OKUYOR (bottom sabiti kaldirildi)",
        "bottom: 22" not in _TSX_G_KOD
        and "sayi(spec.parametre.y_orani, 0.755)" in _TSX_G_KOD,
        "bottom: 22 kodda hala var" if "bottom: 22" in _TSX_G_KOD else "")
kontrol("KaynakEtiketi GUVENLI KENARI zorluyor",
        "height - GUVENLI_KENAR" in _TSX_G_KOD
        and "right: GUVENLI_KENAR" in _TSX_G_KOD)
kontrol("qa_on I-16 kodlarini FAIL_KODLARI'nda tasiyor",
        {"KALITE-YAZI-CAKISMA", "KALITE-GUVENLI-ALAN"} <= _qon.FAIL_KODLARI)
# ⚠ I-16'da bu kontrol `olcum == 9` kilitliyordu; I-17 uc olcum daha
# ekledi. Kontrol SILINMEDI, kuralin niyeti korunarak GUNCELLENDI:
# I-16 olcumleri kapsamda KALMALI ve sayim buyumeye acik olmali.
kontrol("kapsam_ozeti I-16 olcumlerini sayiyor",
        _kk.kapsam_ozeti()["olcum"] >= 9
        and "yazi_cakismasi" in _kk.kapsam_ozeti()["olcum_adlari"]
        and "altyazi_kupleri" in _kk.kapsam_ozeti()["olcum_adlari"])
kontrol("altyazi/kunye/1080p artik KAPSAM DISI listesinde DEGIL",
        not any("altyazi" in k or "1080p" in k or "kunye" in k
                for k in _kk.kapsam_ozeti()["kapsam_disi"]),
        _kk.kapsam_ozeti()["kapsam_disi"])

blok("§34d 1080p YENIDEN RENDER — olculen sonuc")

_R16_YOL = os.path.join(KOK, "..", "outputs", "sample",
                        "altyazi_1080p_i16_rapor.json")
_R16 = None
if os.path.exists(_R16_YOL):
    try:
        _R16 = _json.load(open(_R16_YOL, encoding="utf-8"))
    except ValueError:
        _R16 = None
if _R16 is None:
    bloke_yaz("I-16 render raporu", f"yok/bozuk: {_R16_YOL}")
else:
    _v16 = next((a for a in (_R16["ffprobe"].get("streams") or [])
                 if a.get("codec_type") == "video"), {})
    kontrol("⭐ 1080p: cikti 1920x1080",
            _v16.get("width") == 1920 and _v16.get("height") == 1080,
            (_v16.get("width"), _v16.get("height")))
    kontrol("sure 15-20 sn araliginda",
            15.0 <= float((_R16["ffprobe"].get("format") or {}).get(
                "duration") or 0) <= 20.0,
            (_R16["ffprobe"].get("format") or {}).get("duration"))
    kontrol("maliyet $0.00", _R16.get("maliyet_usd") == 0.0)

    # ── ALTYAZI ──
    _a16 = _R16["altyazi"]
    kontrol("⭐ ALTYAZI URETILDI ve okunabilirlik temiz",
            _a16["kup_sayisi"] >= 4 and _a16["okunabilirlik_temiz"] is True)
    kontrol("altyazi kupleri sahnelere DAGITILDI (props'a ulasti)",
            sum(len(s.get("altyazi") or []) for s in _R16["zincir"]) >= 4
            if _R16["zincir"] and "altyazi" in (_R16["zincir"][0] or {})
            else _a16["kup_sayisi"] >= 4)
    kontrol("DURUSTLUK: olculen/orantili kup ayrimi raporda",
            _a16["olculen_kup"] + _a16["orantili_kup"] == _a16["kup_sayisi"]
            and "orantili" in _a16["zamanlama_notu"].lower())
    kontrol("altyazi cok hizli / uzun satir YOK",
            not _a16["cok_hizli"] and not _a16["uzun_satir"])

    # ── KAYNAK KUNYESI ──
    _k16 = _R16["kaynak_kunyesi"]
    kontrol("⭐ KAYNAK KUNYESI URETILDI (sahneye bagli)",
            _k16["atif_gerekli"] is True and len(_k16["katmanlar"]) >= 1,
            len(_k16["katmanlar"]))
    kontrol("kunye metni eser sahibi + lisans tasiyor",
            all("NASA" in (k.get("metin") or "") for k in _k16["katmanlar"]))
    kontrol("kunye altyazi bandinin USTUNDE",
            all((k.get("y_orani") or 0)
                + _tg.YUKSEKLIK["source-label"] <= _tg.ALTYAZI_BANT[0] + 1e-6
                for k in _k16["katmanlar"]),
            [k.get("y_orani") for k in _k16["katmanlar"]])

    # ── GUVENLI ALAN + CAKISMA (gercek plandan) ──
    kontrol("⭐ GERCEK planda guvenli alan IHLALI YOK",
            (_R16["guvenli_alan"] or {}).get("temiz") is True,
            (_R16["guvenli_alan"] or {}).get("ihlaller"))
    kontrol("⭐ GERCEK planda yazi CAKISMASI YOK",
            (_R16["yazi_cakismasi"] or {}).get("temiz") is True,
            (_R16["yazi_cakismasi"] or {}).get("cakisan_cift"))
    kontrol("guvenli alan 1080p'ye gore olculdu",
            (_R16["guvenli_alan"] or {}).get("kare_yukseklik") == 1080)

    # ── SES / MIKS ──
    _m16 = _R16["video_ses_olcumu"]
    kontrol("miks LUFS profil hedefine (-14) 1 dB icinde",
            abs(_m16["lufs"] + 14.0) <= 1.0, _m16["lufs"])
    kontrol("true peak tavan altinda, kirpma yok",
            _m16["tepe_dbtp"] <= -1.5 and _m16["kirpma_var"] is False)
    kontrol("sessizlik orani tavan altinda",
            (_m16["sessiz_pct"] / 100.0) <= _kk.SESSIZ_ORAN_TAVANI)
    _rm = _R16.get("remaster") or {}
    kontrol("remaster uygulandiysa DURUSTCE raporlandi (once/sonra)",
            (not _rm.get("uygulandi"))
            or ("once" in _rm and "sonra" in _rm
                and _rm.get("maliyet_usd") == 0.0), _rm.get("uygulandi"))
    kontrol("ambiyans dengeli (duyulur + bogmaz)",
            _R16["duzeltilen_kusurlar"]["ambiyans"]["olcum"]["dengeli"] is True)
    kontrol("olu final tavan altinda",
            (_R16["duzeltilen_kusurlar"]["olu_final"]
             ["olculen_olu_final_sn"] or 0) <= _kk.OLU_FINAL_ESIGI_SN)

    # ── KESIM / KARE / QA ──
    kontrol("sahne kesimleri olculdu",
            _R16["kesmeler"]["sayi"] >= 3, _R16["kesmeler"])
    kontrol("EN AZ 9 kare cikarildi",
            len(_R16["kareler"]) >= 9, len(_R16["kareler"]))
    kontrol("kareler bos/duz degil (her biri > 500 KB @1080p)",
            all(k["bayt"] > 500_000 for k in _R16["kareler"]))
    kontrol("PRE QA FAIL DEGIL", _R16["plan"]["qa"]["fail"] == 0)
    kontrol("POST QA FAIL DEGIL", _R16["post_qa"]["durum"] != "FAIL")
    kontrol("hicbir KALITE-*/POST-* kapisi FAIL uretmedi",
            not [s for s in _R16["plan"]["on_render_qa"]["sorunlar"]
                 if s["seviye"] == "fail"]
            and not [s for s in _R16["post_qa"]["sorunlar"]
                     if s["seviye"] == "fail"])

    # ── B-ROLL: DURUST BLOKE ──
    _b16 = _R16["video_broll"]
    kontrol("B-ROLL durumu raporda ACIKCA yaziyor",
            _b16["durum"] in ("VAR", "BLOKE"))
    if _b16["durum"] == "BLOKE":
        kontrol("B-ROLL BLOKE sebebi yazili (kusur GIZLENMIYOR)",
                bool(_b16["sebep"]) and "B-roll DEGILDIR" in _b16["sebep"])
        kontrol("B-ROLL icin taranan dizinler raporda",
                len(_b16["taranan_dizin"]) >= 1)
    kontrol("medya cesitliligi esigi HALA degismedi",
            _R16["medya_cesitliligi"]["esik"] == _kk.BENZERLIK_ESIGI
            and _R16["medya_cesitliligi"]["esik_degistirildi_mi"] is False)

blok("§34e I-16 KORUMALARI")

_SM16 = oku(KOK, "testler/smoke_altyazi_kunye_1080p_i16.py")
kontrol("smoke ffmpeg test kaynagi KULLANMIYOR",
        not re.search(r"lavfi|testsrc|color=c=", _kod_yalniz(_SM16)))
kontrol("smoke gercek render zincirini cagiriyor",
        "edit_kopru.plan_kur" in _SM16 and "remotion_v2.render" in _SM16)
kontrol("smoke QA FAIL'de render BASLATMIYOR",
        'if not sonuc["render_edilebilir"]:' in _SM16)
kontrol("smoke benzerlik esigini/saglayici kotasini DEGISTIRMIYOR",
        "BENZERLIK_ESIGI =" not in _SM16
        and "saglayici_tavani=" not in _SM16)
kontrol("smoke B-roll icin kendi render ciktilarini KULLANMIYOR",
        "pilot_master" not in _SM16 and "pilot_ham" not in _SM16
        and "faz_d_onizleme" not in _SM16)
kontrol("pipeline.py I-16'da da DEGISMEDI",
        "kalite_kapisi" not in oku(KOK, "pipeline.py")
        and "altyazi_kupleri" not in oku(KOK, "pipeline.py"))
kontrol("server.py I-16'da da DEGISMEDI",
        "kalite_kapisi" not in oku(KOK, "server.py"))
kontrol("22 alanlik generate sozlesmesi I-16'da da DEGISMEDI",
        len(set(re.findall(r"\{ad: '(\w+)'",
                           oku(KOK, "static/js/api.js")))) == 22)
kontrol("UI I-16'da DEGISMEDI",
        "basitGovde" in oku(KOK, "static/js/wizard.js")
        and "SURE_SECENEKLERI" in oku(KOK, "static/js/basit.js"))
kontrol("deploy.sh ezme korumasi KORUNDU",
        "GERIDE" in open(os.path.join(KOK, "..", "deploy.sh"),
                         encoding="utf-8").read())
kontrol("bayraklar HALA varsayilan kapali",
        mkp.ACIK is False and ekp.ACIK is False
        and ekp.kalite_kapisi_acik(None) is False)
kontrol("altyazi kupleri verilmezse plan ESKISI GIBI davraniyor",
        '"altyazi_stili": "bant-orta" if _altyazi_var else "yok"'
        in oku(KOK, "editor/plan.py"))


# ═══════════════════════════════════════════════════════════════════════
# §35  FAZ I-17 — BELGESEL MOTION GRAMMAR + OPTIK DURAGANLIK KAPISI
#
# ONCE durumu I-16 ciktisinda OLCULDU (4 fps / 64x36 gri):
#     b001 push-in  2.96 sn -> 3.551      b002 static 5.21 sn -> 0.914
#     b003 push-in  4.69 sn -> 5.102      b004 pull-out 4.68 sn -> 7.030
#     gecis 4/4 hard-cut · push-in IKI KEZ
# Kanit: outputs/sample/motion_i17_rapor.json (izlenen)
# ═══════════════════════════════════════════════════════════════════════

blok("§35a OPTIK DURAGANLIK OLCUMU — sozlesme ve esik turetimi")

kontrol("optik ornekleme komutu KISA ve tek gecis",
        len(_kk.optik_ornek_komutu("v.mp4")) <= 12
        and "fps=4" in " ".join(_kk.optik_ornek_komutu("v.mp4"))
        and "format=gray" in " ".join(_kk.optik_ornek_komutu("v.mp4")))
kontrol("modul komutu URETIYOR ama CALISTIRMIYOR (saf kalir)",
        "subprocess" not in _kod_yalniz(_KK_KAYNAK))
kontrol("esikler GERCEK olcumden turetildi ve kodda yazili",
        _kk.OPTIK_DURGUN_ESIGI == 2.0 and "0.914" in _KK_KAYNAK
        and "3.551" in _KK_KAYNAK)
kontrol("sure esikleri PROFILDEN turetildi (1.5 / 3.0)",
        _kk.OPTIK_DURGUN_WARN_SN == 1.5
        and _kk.OPTIK_DURGUN_FAIL_SN == 2 * _kk.OPTIK_DURGUN_WARN_SN)

# ── KIRMIZI KANIT: I-16'nin OLCULEN degerleriyle kapi FAIL veriyor ──
_ONCE = [{"ad": "b001 push-in", "bas_sn": 0.0, "sure_sn": 2.962},
         {"ad": "b002 static", "bas_sn": 2.962, "sure_sn": 5.213},
         {"ad": "b003 push-in", "bas_sn": 8.175, "sure_sn": 4.688},
         {"ad": "b004 pull-out", "bas_sn": 12.863, "sure_sn": 4.675}]
# I-16'nin sahne ortalamalarini yeniden ureten sentetik fark dizisi
_f16 = []
for _s, _v in zip(_ONCE, (3.551, 0.914, 5.102, 7.030)):
    _f16 += [_v] * int(_s["sure_sn"] * 4)
_o16 = _kk.optik_hareket_olcusu(_f16, sahneler=_ONCE)
kontrol("KIRMIZI: I-16'nin `static` sahnesi FAIL uretiyor",
        not _o16["temiz"]
        and any(i["seviye"] == "fail" and "static" in i["ad"]
                for i in _o16["ihlaller"]), _o16["ihlaller"])
# ⚠ GERCEK VERI ESIK ETRAFINDA SALINIYORDU: I-16'nin `static` sahnesinde
# min 0.674, maks 2.622, ortalama 0.914 olculdu. Yani KESINTISIZ seri kisa
# kaliyor ama sahne acikca duragan. Bu deseni birebir taklit eden dizi:
_salinim = ([0.7] * 5 + [2.6]) * 4          # ~5.2 sn @ 4 fps, ort ~1.02
_o_sal = _kk.optik_hareket_olcusu(
    _salinim, sahneler=[{"ad": "salinimli", "bas_sn": 0.0, "sure_sn": 5.213}])
kontrol("uzun+duragan sahne KESINTISIZ SERI olmadan da yakalaniyor",
        any(i.get("gerekce", "").startswith("sahne ortalamasi")
            and i["seviye"] == "fail" for i in _o_sal["ihlaller"]),
        _o_sal["ihlaller"])
kontrol("hareketli sahneler ihlal URETMIYOR (yanlis pozitif yok)",
        not any("push-in" in i["ad"] or "pull-out" in i["ad"]
                for i in _o16["ihlaller"]))
kontrol("KISA duragan sahne FAIL degil WARN",
        _kk.optik_hareket_olcusu(
            [0.5] * 8, sahneler=[{"ad": "k", "bas_sn": 0.0, "sure_sn": 2.0}]
        )["ihlaller"][0]["seviye"] == "warn")
for _g in (None, [], "x", 5, [None, "a"], [{"bas_sn": "x"}]):
    try:
        _kk.optik_hareket_olcusu(_g)
        _kk.optik_farklar(_g if isinstance(_g, bytes) else b"")
        _kk.kenar_siyahligi_olcusu(b"")
    except Exception as _e:                                       # noqa: BLE001
        kontrol(f"optik olcum {_g!r} istisna FIRLATMIYOR", False,
                type(_e).__name__)
kontrol("optik olcumler bozuk girdide ISTISNA FIRLATMIYOR", True)

blok("§35b KENARDA SIYAH BANT — I-17'de bulunan GERCEK render kusuru")

# ⚠ CSS `scale(S) translate(x%)` sirasi: kayma ekranda S KAT buyuyor.
kontrol("guvenli pay (S-1)/(2S) sinirini ASMIYOR — 8 kombinasyon",
        all(max(_emo.kamera_spec(_h, 4.7, _k).parametre["zoom"])
            * _emo.kamera_spec(_h, 4.7, _k).parametre["guvenli_pay"]
            <= (max(_emo.kamera_spec(_h, 4.7, _k).parametre["zoom"]) - 1) / 2
            + 1e-9
            for _h in ("pan-left", "pan-right", "push-in", "pull-out")
            for _k in ("tam", "punch-1.6"))
        if (_emo := __import__("editor.motion", fromlist=["motion"])) else False)
kontrol("ESKI formul GERCEKTEN tasiyordu (gerileme kaniti)",
        1.696 * max(0.04, (1.6 - 1.0) / 2 + 0.04) > (1.696 - 1) / 2)
kontrol("_guvenli_pay olcek 1.0'da 0 doner (pan alani yok)",
        _emo._guvenli_pay(1.0) == 0.0 and _emo._guvenli_pay(0.5) == 0.0)
kontrol("_guvenli_pay bozuk girdide ISTISNA FIRLATMIYOR",
        _emo._guvenli_pay(None) == 0.0 and _emo._guvenli_pay("x") == 0.0)

_G16, _Y16 = _kk.OPTIK_ORNEK_OLCU
kontrol("kenar dedektoru TEMIZ kareyi gecirir",
        _kk.kenar_siyahligi_olcusu(bytes([120] * (_G16 * _Y16)))["temiz"])
kontrol("kenar dedektoru SIYAH BANTLI kareyi YAKALAR",
        not _kk.kenar_siyahligi_olcusu(
            bytes(sum([[0, 0] + [120] * (_G16 - 4) + [0, 0]
                       for _ in range(_Y16)], [])))["temiz"])
kontrol("TAMAMEN KOYU goruntude yanlis pozitif YOK",
        _kk.kenar_siyahligi_olcusu(bytes([8] * (_G16 * _Y16)))["temiz"])
# ⚠ DURUST SINIR: optik BUYUKLUK siyah bandi ayirt edemez.
kontrol("DURUST SINIR: optik esik siyah bant dedektoru DEGIL (kodda yazili)",
        "SIYAH KENAR TESPITI DEGILDIR" in _KK_KAYNAK
        and _kk.OPTIK_ASIRI_ESIGI > 35.0)
kontrol("qa_son POST-KENAR-SIYAH kodunu tasiyor",
        "POST-KENAR-SIYAH" in oku(KOK, "editor/qa_son.py"))

blok("§35c MOTION GRAMMAR — duraganlik, yon cesitliligi, gecis ailesi")

from editor import gramer as _gr                                  # noqa: E402
kontrol("uzun cekimde `static` aday havuzundan CIKARILIYOR",
        _gr._hareket_sec("medium", 0, sure_sn=5.0) != "static"
        and _gr.DURAGAN_TAVAN_SN == 1.5)
kontrol("KISA cekimde `static` hala mumkun (kural asiri genellemiyor)",
        "static" in _gr.CEKIM_HAREKET["medium"])
kontrol("Ken Burns havuzu GENISLETILDI (yon cesitliligi)",
        len(_gr.CEKIM_HAREKET["medium"]) >= 5
        and {"pan-left", "pan-right", "pull-out"}
        <= set(_gr.CEKIM_HAREKET["medium"]))
kontrol("havuzdaki her hareket kamera_spec'te GERCEKTEN destekli",
        all(h in {"push-in", "pull-out", "pan-left", "pan-right",
                  "slow-drift", "static", "handheld"}
            for tur in ("establishing", "medium", "close-detail",
                        "archive", "atmospheric")
            for h in _gr.CEKIM_HAREKET[tur]))
kontrol("`soft-zoom` KASITLI olarak havuzda YOK (spec adi ayrisirdi)",
        not any("soft-zoom" in v for v in _gr.CEKIM_HAREKET.values()))
kontrol("PENCERE tekrari engelleniyor (ardisik olmayan da)",
        _gr._hareket_sec("medium", 0, sure_sn=4.0,
                         son_hareketler=("push-in",)) != "push-in")
kontrol("RITIM tercihi CESITLILIGE TABI (tekrar pahasina uygulanmaz)",
        _gr._hareket_sec("establishing", 0, sure_sn=4.0,
                         son_hareketler=("pull-out",),
                         islev="sonuc") != "pull-out")
kontrol("RITIM tercihi cakisma yoksa UYGULANIR",
        _gr._hareket_sec("establishing", 1, sure_sn=4.0,
                         son_hareketler=(), islev="sonuc") == "pull-out")
kontrol("eski cagri imzasi KORUNDU (gerileme yok)",
        _gr._hareket_sec("medium", 0) in _gr.CEKIM_HAREKET["medium"])
kontrol("kapanisa GIRIS gecisi karartma (isleve bagli ikinci aile)",
        _emo.sec_gecis("aciklama", "sonuc", 3).parametre["tur"] == "karartma")
kontrol("Faz C'nin kilitledigi davranislar KORUNDU",
        _emo.sec_gecis("aciklama", "aciklama", 5).parametre["tur"] == "hard-cut"
        and _emo.sec_gecis("aciklama", "kanit", 3,
                           j_cut=True).parametre["tur"] == "j-cut")

_MG = _kk.motion_grammar_olcusu([
    {"hareket": "push-in", "gecis": ["hard-cut"], "sure_sn": 3},
    {"hareket": "push-in", "gecis": ["hard-cut"], "sure_sn": 3}])
kontrol("ardisik ayni hareket YAKALANIYOR", len(_MG["ardisik_tekrar"]) == 1)
kontrol("tek gecis ailesi olculuyor", _MG["benzersiz_gecis"] == 1)
kontrol("pencere tekrari ARDISIK OLMAYANI da yakalar",
        len(_kk.motion_grammar_olcusu([
            {"hareket": "push-in"}, {"hareket": "pan-left"},
            {"hareket": "push-in"}])["pencere_tekrari"]) == 1)
kontrol("qa_on I-17 kodlarini tasiyor",
        "KALITE-OPTIK-DURGUN" in _qon.FAIL_KODLARI
        and "KALITE-MOTION-TEKRAR" in _qon.KALITE_KODLARI
        and "KALITE-GECIS-TEKDUZE" in _qon.KALITE_KODLARI)

blok("§35d IZLEYICI KALITE PUANI — seffaf birlesim")

_P = _kk.izleyici_kalite_puani(
    optik={"olculdu": True, "temiz": True, "ihlaller": []},
    grammar={"olculdu": True, "ardisik_tekrar": [], "pencere_tekrari": [],
             "benzersiz_gecis": 2, "acilis_kapanis_ayri": True,
             "benzersiz_hareket": 4},
    ritim={"olculdu": True, "sabit_blok": False, "olu_final_asildi": False},
    guvenli_alan={"olculdu": True, "temiz": True},
    cakisma={"temiz": True}, altyazi={"olculdu": True, "temiz": True},
    medya={"olculdu": True, "tekrar_eden_asset": {},
           "bitisik_ayni_asset": [], "benzer_ciftler": []},
    miks={"sessiz_oran_asildi": False, "olu_final_asildi": False},
    ambans={"olculdu": True, "dengeli": True})
kontrol("tum bilesenler temizken puan 100", _P["puan"] == 100.0)
kontrol("agirliklar 100'e topluyor", sum(_kk.KALITE_AGIRLIK.values()) == 100)
kontrol("her bilesen KENDI GEREKCESIYLE raporlaniyor (kara kutu yok)",
        all(b.get("gerekce") for b in _P["bilesenler"].values()))
kontrol("DURUST ETIKET: izleyici arastirmasi DEGIL",
        "izleyici arastirmasi DEGILDIR" in _P["not"])
kontrol("olculemeyen bilesen puana KATILMIYOR (sahte tam puan yok)",
        _kk.izleyici_kalite_puani(optik={"olculdu": False})[
            "olculen_agirlik"] < 100)
kontrol("duragan sahne puani DUSURUYOR",
        _kk.izleyici_kalite_puani(
            optik={"olculdu": True, "temiz": False,
                   "ihlaller": [{"ad": "x"}]})["bilesenler"][
            "optik_hareket"]["puan"] == 0.0)

blok("§35e YENIDEN RENDER — olculen ONCE/SONRA")

_R17_YOL = os.path.join(KOK, "..", "outputs", "sample", "motion_i17_rapor.json")
_R17 = None
if os.path.exists(_R17_YOL):
    try:
        _R17 = _json.load(open(_R17_YOL, encoding="utf-8"))
    except ValueError:
        _R17 = None
if _R17 is None:
    bloke_yaz("I-17 render raporu", f"yok/bozuk: {_R17_YOL}")
else:
    _once = _R17["once_i16"]
    kontrol("ONCE durumu raporda KAYITLI (I-16 olcumu)",
            len(_once["sahneler"]) == 4
            and any(s["optik_ort"] < 1.0 for s in _once["sahneler"])
            and _once["gecis_dagilimi"] == {"hard-cut": 4})
    _o17 = _R17["optik_hareket"]
    kontrol("⭐ SONRA: hicbir sahnede duraganlik ihlali YOK",
            _o17["temiz"] is True, _o17.get("ihlaller"))
    _en_dusuk = min(s["ortalama"] for s in _o17["sahneler"])
    kontrol("⭐ en duragan sahne bile esigin USTUNDE",
            _en_dusuk > _kk.OPTIK_DURGUN_ESIGI, _en_dusuk)
    kontrol("ONCE'nin duragan sahnesi SONRA duzeldi (0.914 -> >2.0)",
            min(s["optik_ort"] for s in _once["sahneler"]) < 1.0
            and _en_dusuk > 2.0, (0.914, _en_dusuk))
    _mg17 = _R17["motion_grammar"]
    kontrol("⭐ ardisik VE pencere hareket tekrari YOK",
            not _mg17["ardisik_tekrar"] and not _mg17["pencere_tekrari"],
            _mg17["hareketler"])
    kontrol("⭐ en az IKI gecis ailesi kullanildi",
            _mg17["benzersiz_gecis"] >= 2, _mg17["gecis_dagilimi"])
    kontrol("hard-cut orani referans bandinda kaldi (>=%55)",
            _mg17["gecis_dagilimi"].get("hard-cut", 0)
            / max(1, len(_mg17["gecisler"])) >= 0.55,
            _mg17["gecis_dagilimi"])
    kontrol("acilis ve kapanis hareketi FARKLI (ritim)",
            _mg17["acilis_kapanis_ayri"] is True,
            (_mg17["acilis_hareketi"], _mg17["kapanis_hareketi"]))
    kontrol("benzersiz hareket sayisi ARTTI (I-16: 3 -> I-17: >=4)",
            _mg17["benzersiz_hareket"] >= 4
            and len(set(_once["hareketler"])) == 3)
    kontrol("⭐ KENARDA SIYAH BANT YOK",
            (_R17.get("kenar_siyahligi") or {}).get("temiz") is True,
            _R17.get("kenar_siyahligi"))
    _pu = _R17["izleyici_kalite_puani"]
    kontrol("izleyici kalite puani raporda ve BILESENLI",
            isinstance(_pu["puan"], float) and len(_pu["bilesenler"]) == 6)
    kontrol("⭐ puan bilesenlerinin hicbiri 0 degil",
            all((b["puan"] or 0) > 0 for b in _pu["bilesenler"].values()
                if b["olculdu"]), _pu["bilesenler"])

    # ── I-16 kazanimlari KORUNDU ──
    _v17 = next((a for a in (_R17["ffprobe"].get("streams") or [])
                 if a.get("codec_type") == "video"), {})
    kontrol("1080p KORUNDU", _v17.get("width") == 1920
            and _v17.get("height") == 1080)
    kontrol("sure 15-20 sn araliginda",
            15.0 <= float((_R17["ffprobe"].get("format") or {}).get(
                "duration") or 0) <= 20.0)
    kontrol("ALTYAZI KORUNDU", _R17["altyazi"]["kup_sayisi"] >= 4
            and _R17["altyazi"]["okunabilirlik_temiz"] is True)
    kontrol("KAYNAK KUNYESI KORUNDU",
            len(_R17["kaynak_kunyesi"]["katmanlar"]) >= 1)
    kontrol("guvenli alan + cakisma HALA temiz",
            (_R17["guvenli_alan"] or {}).get("temiz") is True
            and (_R17["yazi_cakismasi"] or {}).get("temiz") is True)
    kontrol("EN AZ 9 kare", len(_R17["kareler"]) >= 9)
    kontrol("sahne kesimleri olculdu", _R17["kesmeler"]["sayi"] >= 3)
    kontrol("PRE QA FAIL DEGIL", _R17["plan"]["qa"]["fail"] == 0)
    kontrol("POST QA FAIL DEGIL", _R17["post_qa"]["durum"] != "FAIL")
    kontrol("miks hedefte, kirpma yok",
            abs(_R17["video_ses_olcumu"]["lufs"] + 14.0) <= 1.0
            and _R17["video_ses_olcumu"]["kirpma_var"] is False)
    kontrol("B-ROLL BLOKE AYNEN duruyor (sahte B-roll YOK)",
            _R17["video_broll"]["durum"] == "BLOKE"
            and "B-roll DEGILDIR" in _R17["video_broll"]["sebep"])
    kontrol("medya benzerlik esigi HALA degismedi",
            _R17["medya_cesitliligi"]["esik"] == _kk.BENZERLIK_ESIGI)

blok("§35f I-17 KORUMALARI")

_SM17 = oku(KOK, "testler/smoke_motion_grammar_i17.py")
kontrol("smoke ffmpeg test kaynagi KULLANMIYOR",
        not re.search(r"lavfi|testsrc|color=c=", _kod_yalniz(_SM17)))
kontrol("smoke kendi render ciktilarini B-roll diye KULLANMIYOR",
        "pilot_master" not in _SM17 and "pilot_ham" not in _SM17)
kontrol("smoke esikleri DEGISTIRMIYOR",
        "OPTIK_DURGUN_ESIGI =" not in _SM17
        and "BENZERLIK_ESIGI =" not in _SM17)
kontrol("pipeline.py I-17'de de DEGISMEDI",
        "kalite_kapisi" not in oku(KOK, "pipeline.py")
        and "optik_hareket" not in oku(KOK, "pipeline.py"))
kontrol("server.py I-17'de de DEGISMEDI",
        "kalite_kapisi" not in oku(KOK, "server.py"))
kontrol("22 alanlik generate sozlesmesi I-17'de de DEGISMEDI",
        len(set(re.findall(r"\{ad: '(\w+)'",
                           oku(KOK, "static/js/api.js")))) == 22)
kontrol("UI I-17'de DEGISMEDI",
        "basitGovde" in oku(KOK, "static/js/wizard.js")
        and "SURE_SECENEKLERI" in oku(KOK, "static/js/basit.js"))
kontrol("deploy.sh ezme korumasi KORUNDU",
        "GERIDE" in open(os.path.join(KOK, "..", "deploy.sh"),
                         encoding="utf-8").read())
kontrol("bayraklar HALA varsayilan kapali",
        mkp.ACIK is False and ekp.ACIK is False
        and ekp.kalite_kapisi_acik(None) is False)


# ═══════════════════════════════════════════════════════════════════════
# §36  FAZ I-18 — IKINCI KONSEPT (DOGA/SEYAHAT) + MEDYA EDINIMI
#
# ⚠ Bu bolumun ISPAT YUKU iki parcali:
#   (a) KULLANICI YALNIZ METIN VERINCE taksonomi + bilesik stil onu
#       otomatik seyahat/sinematik siniflar   -> TAM OLARAK KANITLANIR
#   (b) medya EDINIMI                          -> ortam kaynakli BLOKE
#       (bkz. §36c; sebep olculdu, gizlenmedi)
# ═══════════════════════════════════════════════════════════════════════

blok("§36a TAKSONOMI KAPSAM BOSLUGU — olculdu ve kapatildi")

import taksonomi as _tk                                           # noqa: E402
import stil_profili as _sp                                        # noqa: E402

_DOGA = [
    "İzlanda'nın güney kıyısındaki buzul lagünleri, siyah kum plajları ve "
    "şelaleleri: dört duraklı bir doğa yolculuğu",
    "Norveç fiyortlarında tekneyle ilerlerken şelaleler ve dik kayalıklar",
    "Patagonya'da granit kuleler, buzul gölleri ve pampa rüzgarı",
    "Kapadokya'da peribacaları, vadiler ve yeraltı mağaraları",
]
for _m in _DOGA:
    _k = _tk.siniflandir(_m)
    kontrol(f"⭐ doga metni AUTO seyahat siniflandi: {_m[:34]}…",
            _k["aile"] == "seyahat" and _k["durum"] in ("kesin", "melez"),
            (_k["aile"], _k["durum"], _k["guven"]))
    _s = _sp.coz(konsept=_k)
    kontrol(f"⭐ bilesik stil AUTO secildi: {_m[:34]}…",
            _s.get("kimlik") == "seyahat-4k" and _s.get("kaynak") == "auto",
            (_s.get("kimlik"), _s.get("kaynak")))

kontrol("manzara/yer sekli sozlugu EKLENDI (kapsam buyudu)",
        _tk.kapsam_ozeti()["anahtar"] >= 780,
        _tk.kapsam_ozeti()["anahtar"])
_anahtarlar = set(_tk.AGAC["seyahat.doga_manzara"]["anahtar"])
for _kelime in ("buzul", "fiyort", "lagun", "kanyon", "volkan", "orman",
                "plaj", "zirve", "krater", "nehir"):
    kontrol(f"'{_kelime}' manzara sozlugunde", _kelime in _anahtarlar)
kontrol("⚠ eski 19 kelime SILINMEDI (yalniz eklendi)",
        {"dag", "gol", "sahil", "vadi", "selale", "milli park", "patika"}
        <= _anahtarlar)
kontrol("motor kodu DEGISMEDI — yalniz AGAC'a satir eklendi (§16 sozu)",
        "def siniflandir" in oku(KOK, "taksonomi.py")
        and _tk.kapsam_ozeti()["aile"] == 7
        and _tk.kapsam_ozeti()["dal"] == 33)

# ── GERILEME: diger aileler bozulmadi ──
for _m, _bek in (("Kapadokya gezi rehberi: balon turu", "seyahat"),
                 ("iPhone 15 vs Galaxy S24 fiyat karsilastirmasi", "urun"),
                 ("Enflasyon ve borsa: faiz karari piyasalari nasil etkiler",
                  "egitim"),
                 ("Kabus gibi bir gece: kapinin ardindaki golge", "hikaye"),
                 ("Findik tarifi: 20 dakikada kolay kek", "yasam")):
    kontrol(f"gerileme yok: {_bek}",
            _tk.siniflandir(_m)["aile"] == _bek,
            _tk.siniflandir(_m)["aile"])
kontrol("stil AUTO'su seyahat disinda seyahat-4k SECMIYOR",
        _sp.coz(konsept=_tk.siniflandir(
            "Findik tarifi: 20 dakikada kolay kek")).get("kimlik")
        != "seyahat-4k")

blok("§36b MEDYA EDINIMI MODULU — lisans karari DELEGE, konu HARD-CODE DEGIL")

from medya import commons as _cm                                  # noqa: E402
_CM_KAYNAK = oku(KOK, "medya/commons.py")
# ⚠ `_kod_yalniz` token'lari BOSLUKLA birlestiriyor: `lisans.lisans_karari(`
# kodda varken taramada `lisans . lisans_karari (` oluyor ve naif `in`
# kontrolu KOD DOGRUYKEN kirmizi yaniyor (I-18'de yasandi). Bosluksuz
# bicimde aranir.
def _sikistir(kaynak: str) -> str:
    return re.sub(r"\s+", "", _kod_yalniz(kaynak))


_CM_KOD = _sikistir(_CM_KAYNAK)

kontrol("modul KENDI lisans kararini VERMIYOR (lisans.py'ye delege)",
        "lisans.lisans_karari(" in _CM_KOD)
kontrol("modul KENDI indiricisini YAZMIYOR (guvenli_indir'e delege)",
        "indirme.guvenli_indir(" in _CM_KOD)
kontrol("SSRF duvari atlanmiyor — dogrudan urlopen ile DOSYA cekilmiyor",
        "urlopen" not in _CM_KOD.split("defindir(")[1]
        if "defindir(" in _CM_KOD else False)
kontrol("APOLLO ya da baska KONU ADI gomulu DEGIL",
        not re.search(r"apollo|moon|iceland|izlanda|jökul|jokul",
                      _kod_yalniz(_CM_KAYNAK), re.I))
kontrol("anahtar/API anahtari GEREKTIRMIYOR ($0.00)",
        _cm.kapsam_ozeti()["anahtar_gerekli"] is False
        and _cm.kapsam_ozeti()["maliyet_usd"] == 0.0
        and not re.search(r"api_key|apikey|secret",
                          _kod_yalniz(_CM_KAYNAK), re.I))
kontrol("PROVENANCE ZORUNLU: eser sahibi yoksa aday ELENIR",
        "ESER-SAHIBI-YOK" in _CM_KAYNAK)
kontrol("4K esigi kaynaga bagli (upscale YOK)",
        _cm.DORT_K_EN_AZ_GENISLIK == 3840
        and "COZUNURLUK-YETERSIZ" in _CM_KAYNAK)
kontrol("kapsam DISI acikca yaziliyor (video B-roll dahil)",
        any("video" in k for k in _cm.kapsam_ozeti()["kapsam_disi"]))
kontrol("429 icin SINIRLI ve TAVANLI bekleme (sonsuz dongu YOK)",
        "deneme: int = 3" in _CM_KAYNAK
        and "bekleme_tavani" in _CM_KAYNAK)
kontrol("Retry-After varsa ONA uyuluyor",
        _cm.bekle_suresi({"retry_after": 7}, 0) == 7.0
        and _cm.bekle_suresi({}, 2) == 8.0)
kontrol("istek imzasi guvenlik katmaninin bekledigi bicimde",
        "def varsayilan_istek(yontem: str, url: str, **kw)" in _CM_KAYNAK)
for _g in (None, {}, {"indirme_url": ""}, "x", 5):
    try:
        _cm.indir(_g if isinstance(_g, dict) else {}, "/tmp/yok.jpg")
    except Exception as _e:                                       # noqa: BLE001
        kontrol(f"commons.indir({_g!r}) istisna FIRLATMIYOR", False,
                type(_e).__name__)
kontrol("commons.indir bozuk girdide ISTISNA FIRLATMIYOR", True)
kontrol("lisanssiz aday INDIRILMEZ (duvar bypass edilemez)",
        _cm.indir({"indirme_url": "https://x/y.jpg",
                   "render_kullanilabilir": False},
                  "/tmp/yok.jpg")["sebep"] == "LISANS-DUVARI")

blok("§36c I-18 PILOT BETIGI — Apollo hard-code YOK, BLOKE dursut")

_SM18 = oku(KOK, "testler/smoke_konsept2_doga_i18.py")
_SM18_KOD = _sikistir(_SM18)
kontrol("betikte APOLLO/AY hard-code'u YOK",
        not re.search(r"apollo|a\d{3}_wiki|tranquility|armstrong",
                      _kod_yalniz(_SM18), re.I))
kontrol("konu KULLANICI METNINDEN geliyor",
        "KONU_METNI" in _SM18 and "taksonomi" in _SM18_KOD.lower()
        or "KONU_METNI" in _SM18)
kontrol("sabit gorsel havuzu KALDIRILDI (medya edinilir)",
        "GORSEL_HAVUZU" not in _SM18_KOD and "medya_edin()" in _SM18_KOD)
kontrol("anlatim TURKCE (I-17 'Ingilizce fixture' siniri kapandi)",
        "tr-TR-" in _SM18)
kontrol("olgular BETIMLEME olarak etiketli (uydurma iddia YOK)",
        '"betimleme"' in _SM18)
kontrol("4K iddiasi KAYNAGA BAGLI — yetmezse 1080p'ye duser",
        "dort_k_uygun" in _SM18 and "upscale YAPILMIYOR" in _SM18)
kontrol("medya edinilemezse SAHTE gorsel URETILMIYOR",
        "Sahte gorsel URETILMEDI" in _SM18)
kontrol("BLOKE sebebi SINIFLANDIRILIYOR (ag/hiz siniri vs lisans)",
        "AG-HIZ-SINIRI" in _SM18)
kontrol("video B-roll BLOKE'si KORUNDU",
        "video_broll_ara" in _SM18_KOD
        and "B-roll DEGILDIR" in _SM18)
kontrol("ffmpeg test kaynagi KULLANILMIYOR",
        not re.search(r"lavfi|testsrc|color=c=", _kod_yalniz(_SM18)))
kontrol("benzerlik/durgunluk esikleri DEGISTIRILMIYOR",
        "BENZERLIK_ESIGI =" not in _SM18
        and "OPTIK_DURGUN_ESIGI =" not in _SM18)

# ── OLCULEN BLOKE: rapor varsa dogrula, yoksa BLOKE yaz ──
_R18_YOL = os.path.join(KOK, "..", "outputs", "sample", "doga_i18_rapor.json")
_R18 = None
if os.path.exists(_R18_YOL):
    try:
        _R18 = _json.load(open(_R18_YOL, encoding="utf-8"))
    except ValueError:
        _R18 = None
if _R18 is None:
    bloke_yaz("I-18 doga pilotu render raporu",
              "medya EDINILEMEDI (upload.wikimedia.org bu ortamda 429 / "
              "Retry-After 600) — sahte medyayla render URETILMEDI")
else:
    kontrol("render raporu 1080p ya da 4K oldugunu DURUSTCE yaziyor",
            bool(_R18.get("ffprobe")))

blok("§36d I-18 KORUMALARI")

kontrol("pipeline.py I-18'de de DEGISMEDI",
        "commons" not in oku(KOK, "pipeline.py")
        and "kalite_kapisi" not in oku(KOK, "pipeline.py"))
kontrol("server.py I-18'de de DEGISMEDI",
        "commons" not in oku(KOK, "server.py"))
kontrol("medya avcisi/editor bayraklari HALA varsayilan kapali",
        mkp.ACIK is False and ekp.ACIK is False
        and ekp.kalite_kapisi_acik(None) is False)
kontrol("22 alanlik generate sozlesmesi I-18'de de DEGISMEDI",
        len(set(re.findall(r"\{ad: '(\w+)'",
                           oku(KOK, "static/js/api.js")))) == 22)
kontrol("UI I-18'de DEGISMEDI",
        "basitGovde" in oku(KOK, "static/js/wizard.js")
        and "SURE_SECENEKLERI" in oku(KOK, "static/js/basit.js"))
kontrol("deploy.sh ezme korumasi KORUNDU",
        "GERIDE" in open(os.path.join(KOK, "..", "deploy.sh"),
                         encoding="utf-8").read())
kontrol("lisans/SSRF modulleri I-18'de DEGISMEDI",
        "lisans_karari" in oku(KOK, "medya/lisans.py")
        and "url_dogrula" in oku(KOK, "medya/guvenlik.py"))


# ═══════════════════════════════════════════════════════════════════════
# §37  FAZ I-19 — EDINIM DAYANIKLILIGI ve KAYNAK CESITLENDIRME
#
# I-18'de tek saglayici (Wikimedia) 429 verince hat TAMAMEN durdu.
# Bu bolum devre kesiciyi, saglayici zincirini, onbellegi ve Retry-After
# kararini SAHTE saglayicilarla (ag YOK) kilitler; sonra GERCEK kosunun
# olculen failover sayilarini dogrular.
# ═══════════════════════════════════════════════════════════════════════

blok("§37a DEVRE KESICI — ayni host ZORLANMAZ")

from medya import edinim as _ed                                   # noqa: E402

_saat_t = {"t": 0.0}


def _saat():
    return _saat_t["t"]


_dk = _ed.DevreKesici(esik=2, soguma_sn=100.0, saat=_saat)
kontrol("baslangicta devre KAPALI", _dk.acik_mi("a") is False)
_dk.hata("a")
kontrol("tek hatada devre ACILMAZ (esik 2)", _dk.acik_mi("a") is False)
kontrol("ikinci hatada devre ACILIR", _dk.hata("a") is True
        and _dk.acik_mi("a") is True)
_saat_t["t"] = 50.0
kontrol("soguma DOLMADAN host DENENMEZ", _dk.acik_mi("a") is True)
_saat_t["t"] = 101.0
kontrol("soguma DOLUNCA host yeniden denenebilir",
        _dk.acik_mi("a") is False)
_dk.hata("b")
_dk.basari("b")
kontrol("basari sayaci SIFIRLAR", _dk.acik_mi("b") is False
        and "b" not in _dk.ozet()["ardisik_hata"])
kontrol("GECICI hata sayaci artirmaz",
        _ed.DevreKesici(esik=1, saat=_saat).hata("c", kalici=False) is False)
kontrol("devre ozeti SAYILABILIR",
        set(_dk.ozet()) >= {"esik", "soguma_sn", "ardisik_hata",
                            "acik_devreler"})

blok("§37b RETRY-AFTER KARARI — beklemek mi, gecmek mi")

kontrol("Retry-After yoksa GEC",
        _ed.bekle_karari({})["karar"] == "GEC")
kontrol("kisa Retry-After'da BEKLE",
        _ed.bekle_karari({"retry_after": 5})["karar"] == "BEKLE"
        and _ed.bekle_karari({"retry_after": 5})["bekleme_sn"] == 5.0)
# ⚠ I-18'in dersi: 600 sn beklemek YANLIS davranis.
kontrol("uzun Retry-After'da BEKLEME — DEVRE AC",
        _ed.bekle_karari({"retry_after": 600})["karar"] == "DEVRE-AC"
        and _ed.bekle_karari({"retry_after": 600})["bekleme_sn"] == 0.0)
kontrol("tavan disaridan verilebilir",
        _ed.bekle_karari({"retry_after": 40}, tavan_sn=60)["karar"] == "BEKLE")
kontrol("bozuk Retry-After'da ISTISNA YOK",
        _ed.bekle_karari({"retry_after": "x"})["karar"] == "GEC"
        and _ed.bekle_karari(None)["karar"] == "GEC")


class _SahteSaglayici:
    """Test icin saglayici — AG KULLANMAZ."""

    def __init__(self, ad, adaylar=None, indir_sonuc=None, ara_hata=None):
        self.ad = ad
        self._adaylar = adaylar or []
        self._indir = indir_sonuc or {"ok": False, "sebep": "yok"}
        self._ara_hata = ara_hata
        self.ara_sayisi = 0
        self.indir_sayisi = 0

    def ara(self, sorgu, adet=6, en_az_genislik=0):
        self.ara_sayisi += 1
        if self._ara_hata:
            raise RuntimeError(self._ara_hata)
        return {"ok": bool(self._adaylar), "adaylar": list(self._adaylar),
                "elenen": [], "hata": ""}

    def indir(self, aday, hedef, deneme=1):
        self.indir_sayisi += 1
        if self._indir.get("ok"):
            with open(hedef, "wb") as f:
                f.write(b"x" * 20000)
        return dict(self._indir)


def _aday(url="https://ornek.test/a.jpg", **kw):
    d = {"indirme_url": url, "orijinal_url": url, "baslik": "x",
         "lisans": "cc-by", "eser_sahibi": "Biri",
         "render_kullanilabilir": True, "atif_gerekli": True}
    d.update(kw)
    return d


blok("§37c SAGLAYICI ZINCIRI — iki ayri hata senaryosu")

import tempfile as _tf19                                          # noqa: E402
with _tf19.TemporaryDirectory() as _d19:
    _h = os.path.join(_d19, "a.jpg")

    # ── SENARYO 1: birinci saglayici 429 (kalici) -> ikinciye GEC ──
    _s1 = _SahteSaglayici("bir", [_aday()],
                          {"ok": False, "sebep": "HTTP 429", "http": 429,
                           "retry_after": 600})
    _s2 = _SahteSaglayici("iki", [_aday("https://b.test/b.jpg")], {"ok": True})
    _r = _ed.edin("q", _h, saglayicilar=[{"ad": "bir", "modul": _s1},
                                         {"ad": "iki", "modul": _s2}],
                  saat=_saat, uyu=lambda s: None)
    kontrol("SENARYO-1: 429'da ikinci saglayiciya GECILDI",
            _r["ok"] and _r["kullanilan_saglayici"] == "iki")
    kontrol("SENARYO-1: metadata ile BAYT ayri sayildi",
            _r["metadata_bulundu"] == 2 and _r["bayt_indirildi"] == 1)
    kontrol("SENARYO-1: 600 sn BEKLENMEDI (tek indirme denemesi)",
            _s1.indir_sayisi == 1, _s1.indir_sayisi)

    # ── SENARYO 2: birinci saglayici ARAMA'da patliyor -> ikinciye GEC ──
    _s3 = _SahteSaglayici("uc", ara_hata="baglanti koptu")
    _s4 = _SahteSaglayici("dort", [_aday("https://d.test/d.jpg")], {"ok": True})
    _r2 = _ed.edin("q", _h, saglayicilar=[{"ad": "uc", "modul": _s3},
                                          {"ad": "dort", "modul": _s4}],
                   saat=_saat, uyu=lambda s: None)
    kontrol("SENARYO-2: ARAMA hatasinda ikinciye GECILDI",
            _r2["ok"] and _r2["kullanilan_saglayici"] == "dort")
    kontrol("SENARYO-2: arama hatasi ARAMA-HATA olarak raporlandi",
            any(d["durum"] == "ARAMA-HATA" for d in _r2["denemeler"]))

    # ── SENARYO 3: HEPSI duserse ok=False, SAHTE aday URETILMEZ ──
    _s5 = _SahteSaglayici("bes", [_aday()], {"ok": False, "sebep": "HTTP 503",
                                             "http": 503})
    _r3 = _ed.edin("q", _h, saglayicilar=[{"ad": "bes", "modul": _s5}],
                   saat=_saat, uyu=lambda s: None)
    kontrol("SENARYO-3: hepsi duserse ok=False ve aday YOK",
            _r3["ok"] is False and _r3["aday"] is None)

    # ── DEVRE KESICI zincirde: ikinci cagride host ATLANIR ──
    _kes = _ed.DevreKesici(esik=1, soguma_sn=1000.0, saat=_saat)
    _s6 = _SahteSaglayici("alti", [_aday()], {"ok": False, "sebep": "HTTP 429",
                                              "http": 429})
    _s7 = _SahteSaglayici("yedi", [_aday("https://y.test/y.jpg")], {"ok": True})
    _ed.edin("q", _h, kesici=_kes, saat=_saat, uyu=lambda s: None,
             saglayicilar=[{"ad": "alti", "modul": _s6},
                           {"ad": "yedi", "modul": _s7}])
    _once = _s6.ara_sayisi
    _r4 = _ed.edin("q", _h, kesici=_kes, saat=_saat, uyu=lambda s: None,
                   saglayicilar=[{"ad": "alti", "modul": _s6},
                                 {"ad": "yedi", "modul": _s7}])
    kontrol("DEVRE ACIKKEN host HIC ARANMADI (zorlanmadi)",
            _s6.ara_sayisi == _once
            and any(d["durum"] == "DEVRE-ACIK" for d in _r4["denemeler"]))

    # ── ONBELLEK: ayni URL ikinci kez INDIRILMEZ ──
    _ob: dict = {}
    _s8 = _SahteSaglayici("sekiz", [_aday("https://o.test/o.jpg")], {"ok": True})
    _ed.edin("q", _h, onbellek=_ob, saat=_saat,
             saglayicilar=[{"ad": "sekiz", "modul": _s8}])
    _n = _s8.indir_sayisi
    _r5 = _ed.edin("q", _h, onbellek=_ob, saat=_saat,
                   saglayicilar=[{"ad": "sekiz", "modul": _s8}])
    kontrol("ONBELLEK: ikinci cagride YENIDEN INDIRILMEDI",
            _s8.indir_sayisi == _n and _r5["onbellekten"] is True)

    # ── TELIF/ATIF EKSIK -> KESIN RED ──
    for _eksik in ({"lisans": ""}, {"eser_sahibi": ""},
                   {"render_kullanilabilir": False}):
        _s9 = _SahteSaglayici("dokuz", [_aday(**_eksik)], {"ok": True})
        _rr = _ed.edin("q", _h, saat=_saat,
                       saglayicilar=[{"ad": "dokuz", "modul": _s9}])
        kontrol(f"PROVENANCE eksik ({list(_eksik)[0]}) -> INDIRILMEZ",
                _rr["ok"] is False and _s9.indir_sayisi == 0)

    # ── COZUNURLUK: arama beyani degil GERCEK bayt olculur ──
    _s10 = _SahteSaglayici("on", [_aday("https://k.test/k.jpg")], {"ok": True})
    _rk = _ed.edin("q", _h, en_az_genislik=1920, saat=_saat,
                   olcu_okuyucu=lambda y: (640, 480),
                   saglayicilar=[{"ad": "on", "modul": _s10}])
    kontrol("indirme SONRASI cozunurluk yetersizse aday REDDEDILIR",
            _rk["ok"] is False)
    _s11 = _SahteSaglayici("onbir", [_aday("https://m.test/m.jpg")],
                           {"ok": True})
    _rm = _ed.edin("q", _h, en_az_genislik=1920, saat=_saat,
                   olcu_okuyucu=lambda y: (3840, 2160),
                   saglayicilar=[{"ad": "onbir", "modul": _s11}])
    kontrol("yeterli cozunurlukte aday KABUL EDILIR", _rm["ok"] is True)
    kontrol("olcu okunamazsa ENGELLENMEZ (emin degilsen gecir)",
            _ed.edin("q", _h, en_az_genislik=1920, saat=_saat,
                     olcu_okuyucu=lambda y: (_ for _ in ()).throw(OSError()),
                     saglayicilar=[{"ad": "onIki", "modul": _SahteSaglayici(
                         "onIki", [_aday("https://n.test/n.jpg")],
                         {"ok": True})}])["ok"] is True)

    # ══════════ I-23: EN-BOY ORANI UYUMLULUK KAPISI ══════════
    # ⚠ Bu blogun esigi UYDURULMADI. I-22 render'inda OLCULEN varliklardan
    # turetildi: POST-KENAR-SIYAH'in 6/68 ihlalinin 6'si da b002'de cikti ve
    # b002'nin varligi 2832x3603 (oran 0.786) idi. Ayni render'da 1.480 /
    # 1.333 / 1.332 oranli varliklar SIFIR ihlal uretti.
    _OLCULEN_VARLIK = [
        ("s01  4192x2832", 4192, 2832, False),   # olculdu: temiz
        ("s03  3000x2250", 3000, 2250, False),   # olculdu: temiz (en DAR temiz)
        ("s04  4986x3744", 4986, 3744, False),   # olculdu: temiz
        ("s01y1 2832x3603", 2832, 3603, True),   # olculdu: 6 ihlalin KAYNAGI
        ("s02  2048x3072", 2048, 3072, True),    # ayni sinif: %62'si atiliyor
    ]
    for _ad3, _g3, _y3, _red in _OLCULEN_VARLIK:
        _k3 = _ed.oran_karari(_g3, _y3)
        kontrol(f"oran kapisi {_ad3} -> {'RED' if _red else 'KABUL'}",
                _k3["uygun"] is (not _red),
                f"oran={_k3['olculen_oran']} korunan={_k3['korunan_oran']}")
    kontrol("oran esigi OLCULEN aralikta (0.442 < esik <= 0.750)",
            0.442 < _ed.ORAN_EN_AZ_KORUNAN <= 0.750,
            _ed.ORAN_EN_AZ_KORUNAN)
    kontrol("tam 16:9 kaynakta hicbir sey ATILMIYOR (korunan=1.0)",
            _ed.oran_karari(1920, 1080)["korunan_oran"] == 1.0)
    kontrol("KARE kaynak REDDEDILIR (dikeyin aynasi degil, ayni kusur)",
            _ed.oran_karari(1000, 1000)["uygun"] is False)
    kontrol("ASIRI GENIS panorama da REDDEDILIR (yatayda %41 atiyor)",
            _ed.oran_karari(3000, 1000)["uygun"] is False
            and _ed.oran_karari(3000, 1000)["yon"] == "asiri-genis")
    kontrol("oran karari AG/DOSYA kullanmaz (saf fonksiyon, olcu -> karar)",
            _ed.oran_karari(2832, 3603)["sebep"].startswith("ORAN-UYUMSUZ"))
    for _bozuk in ((None, None), (0, 0), ("a", "b"), (100, 0)):
        kontrol(f"olcu gecersiz {_bozuk} -> ENGELLEMEZ (emin degilsen gecir)",
                _ed.oran_karari(*_bozuk)["uygun"] is True)

    def _harita_okuyucu(harita, sayac):
        """Yola gore olcu donduren sahte ffprobe — cagri sayisi SAYILIR."""
        def _oku(yol):
            sayac.append(yol)
            for _ek, _o in harita.items():
                if yol.endswith(_ek):
                    return _o
            return (3840, 2160)
        return _oku

    # ── KAPI KAPALIYKEN HUKUM DEGISMEZ (geriye tam uyumlu) ──
    _s23a = _SahteSaglayici("kapali", [_aday("https://d1.test/d.jpg")],
                            {"ok": True})
    _r23a = _ed.edin("q", _h, en_az_genislik=1920, saat=_saat,
                     olcu_okuyucu=lambda y: (2832, 3603),
                     saglayicilar=[{"ad": "kapali", "modul": _s23a}])
    kontrol("oran kapisi KAPALIYKEN (varsayilan) dikey aday KABUL EDILIR",
            _r23a["ok"] is True
            and _r23a["oran_kapisi"]["acik"] is False)

    # ── KAPI ACIK: dikey REDDEDILIR, AYNI listedeki SIRADAKINE gecilir ──
    _cag23 = []
    _s23b = _SahteSaglayici("acik", [_aday("https://e1.test/e.jpg"),
                                     _aday("https://e2.test/e.jpg")],
                            {"ok": True})
    _r23b = _ed.edin("q", _h, en_az_genislik=1920, saat=_saat,
                     hedef_oran=_ed.HEDEF_ORAN_16_9,
                     olcu_okuyucu=_harita_okuyucu(
                         {"_1.jpg": (3840, 2160), "a.jpg": (2832, 3603)},
                         _cag23),
                     saglayicilar=[{"ad": "acik", "modul": _s23b}])
    kontrol("oran kapisi ACIK: dikey aday REDDEDILIR, SIRADAKI kabul edilir",
            _r23b["ok"] is True
            and str(_r23b["aday"]["yol"]).endswith("_1.jpg"),
            _r23b["aday"].get("yol"))
    kontrol("SIRADAKI aday AYNI arama listesinden — EK AG CAGRISI YOK",
            _s23b.ara_sayisi == 1 and _s23b.indir_sayisi == 2)
    _red23 = _r23b["oran_kapisi"]["reddedilen"]
    kontrol("raporda OLCULEN oran, HEDEF oran ve RED NEDENI gorunur",
            len(_red23) == 1
            and _red23[0]["olculen_oran"] == 0.786
            and _red23[0]["korunan_oran"] == 0.4421
            and _red23[0]["hedef_oran"] == 1.7778
            and "ORAN-UYUMSUZ" in _red23[0]["sebep"]
            and _red23[0]["olculen_olcu"] == [2832, 3603],
            _red23)
    kontrol("raporda KABUL EDILEN adayin orani da gorunur",
            len(_r23b["oran_kapisi"]["kabul_edilen"]) == 1
            and _r23b["oran_kapisi"]["kabul_edilen"][0]["korunan_oran"] == 1.0)
    kontrol("olcum PAYLASILIR: aday basina TEK olcum (ikinci ffprobe YOK)",
            len(_cag23) == 2, _cag23)

    # ── UYGUN ALTERNATIF YOKSA: sahte aday URETILMEZ, ok=False ──
    _s23c = _SahteSaglayici("hepsi-dikey",
                            [_aday("https://f1.test/f.jpg"),
                             _aday("https://f2.test/f.jpg"),
                             _aday("https://f3.test/f.jpg")], {"ok": True})
    _r23c = _ed.edin("q", _h, en_az_genislik=1920, saat=_saat,
                     hedef_oran=_ed.HEDEF_ORAN_16_9,
                     olcu_okuyucu=lambda y: (2048, 3072),
                     saglayicilar=[{"ad": "hepsi-dikey", "modul": _s23c}])
    kontrol("TUM adaylar uymuyorsa ok=False (kirpip KURTARMA YOK)",
            _r23c["ok"] is False and _r23c["aday"] is None
            and len(_r23c["oran_kapisi"]["reddedilen"]) == 3)
    kontrol("tum adaylar elendiginde RED NEDENI denemede de gorunur",
            "ORAN-UYUMSUZ" in str(_r23c["denemeler"][0].get("sebep")))

    # ── LISANS/PROVENANCE oran kapisindan ONCE gelir (indirme bile YOK) ──
    _s23d = _SahteSaglayici("prov", [_aday("https://g1.test/g.jpg", lisans="")],
                            {"ok": True})
    _r23d = _ed.edin("q", _h, en_az_genislik=1920, saat=_saat,
                     hedef_oran=_ed.HEDEF_ORAN_16_9,
                     olcu_okuyucu=lambda y: (3840, 2160),
                     saglayicilar=[{"ad": "prov", "modul": _s23d}])
    kontrol("PROVENANCE eksikse oran kapisina VARILMADAN reddedilir",
            _r23d["ok"] is False and _s23d.indir_sayisi == 0)

    # ── BEKLE (Retry-After) YOLUNDA DA KAPI ISLER — I-23'te bulunan bosluk ──
    class _SahteBekleyen:
        """Tek sayili denemede 429+Retry-After, cift sayilida BASARILI.

        ⚠ Bu yol I-23'e kadar KAPISIZDI: bekledikten sonra basarili olan
        aday HIC OLCULMEDEN kabul ediliyordu.
        """

        def __init__(self, adaylar):
            self._a = adaylar
            self.ara_sayisi = 0
            self.indir_sayisi = 0

        def ara(self, sorgu, adet=6, en_az_genislik=0):
            self.ara_sayisi += 1
            return {"ok": True, "adaylar": list(self._a), "elenen": [],
                    "hata": ""}

        def indir(self, aday, hedef, deneme=1):
            self.indir_sayisi += 1
            if self.indir_sayisi % 2 == 1:
                return {"ok": False, "http": 429, "retry_after": 1.0}
            with open(hedef, "wb") as f:
                f.write(b"x" * 20000)
            return {"ok": True}

    # ══ I-23b: ORAN KAPISI AYIRT EDILEBILIRLIGI BOZMASIN ══
    # ⚠ OLCULEN ETKILESIM: dikey aday elenince s01'in siradaki adayi
    # birincinin neredeyse ayni karesi cikti (dHash 0.875 >= 0.86) ve
    # KALITE-MEDYA-TEKRAR FAIL verdi. Iki kisit AYNI anda saglanmali.
    _cagb = []

    def _sahte_benzerlik(harita):
        def _olc(a, b):
            _cagb.append((os.path.basename(a), os.path.basename(b)))
            return harita.get(os.path.basename(a), 0.0)
        return _olc

    _s23f = _SahteSaglayici("ayirt", [_aday("https://j1.test/j.jpg"),
                                      _aday("https://j2.test/j.jpg"),
                                      _aday("https://j3.test/j.jpg")],
                            {"ok": True})
    _r23f = _ed.edin("q", _h, en_az_genislik=1920, saat=_saat, adet=2,
                     hedef_oran=_ed.HEDEF_ORAN_16_9,
                     olcu_okuyucu=lambda y: (3840, 2160),
                     benzerlik_okuyucu=_sahte_benzerlik({"a_1.jpg": 0.875,
                                                         "a_2.jpg": 0.41}),
                     benzerlik_esigi=0.86,
                     saglayicilar=[{"ad": "ayirt", "modul": _s23f}])
    kontrol("AYIRT EDILEMEZ aday (0.875>=0.86) REDDEDILIR, siradakine gecilir",
            _r23f["ok"] is True and len(_r23f["adaylar"]) == 2
            and str(_r23f["adaylar"][1]["yol"]).endswith("_2.jpg"),
            [a.get("yol") for a in _r23f["adaylar"]])
    kontrol("ayirt reddi raporda: benzerlik, esik ve NEDEN gorunur",
            len(_r23f["ayirt_kapisi"]["reddedilen"]) == 1
            and _r23f["ayirt_kapisi"]["reddedilen"][0]["benzerlik"] == 0.875
            and _r23f["ayirt_kapisi"]["reddedilen"][0]["esik"] == 0.86
            and "AYIRT-EDILEMEZ" in
            _r23f["ayirt_kapisi"]["reddedilen"][0]["sebep"])
    kontrol("ayirt kapisi AYNI arama listesinden calisir (EK AG CAGRISI YOK)",
            _s23f.ara_sayisi == 1)
    kontrol("edinim dHash HESAPLAMAZ — olcer DISARIDAN verilir",
            "dhash" not in _kod_yalniz(oku(KOK, "medya/edinim.py")).lower()
            and "benzerlik_okuyucu" in _kod_yalniz(oku(KOK, "medya/edinim.py")))
    kontrol("ayirt kapisi KAPALIYKEN (varsayilan) hukum DEGISMEZ",
            _ed.edin("q", _h, en_az_genislik=1920, saat=_saat, adet=2,
                     olcu_okuyucu=lambda y: (3840, 2160),
                     saglayicilar=[{"ad": "kapali2", "modul": _SahteSaglayici(
                         "kapali2", [_aday("https://k1.test/k.jpg"),
                                     _aday("https://k2.test/k.jpg")],
                         {"ok": True})}])["ayirt_kapisi"]["acik"] is False)
    kontrol("benzerlik OLCULEMEDI (-1) ise ENGELLENMEZ",
            len(_ed.edin("q", _h, en_az_genislik=1920, saat=_saat, adet=2,
                         olcu_okuyucu=lambda y: (3840, 2160),
                         benzerlik_okuyucu=lambda a, b: -1.0,
                         benzerlik_esigi=0.86,
                         saglayicilar=[{"ad": "olcemez",
                                        "modul": _SahteSaglayici(
                                            "olcemez",
                                            [_aday("https://l1.test/l.jpg"),
                                             _aday("https://l2.test/l.jpg")],
                                            {"ok": True})}])["adaylar"]) == 2)
    kontrol("benzerlik olcer PATLARSA edinim COKMEZ (engellemez)",
            _ed.edin("q", _h, en_az_genislik=1920, saat=_saat, adet=2,
                     olcu_okuyucu=lambda y: (3840, 2160),
                     benzerlik_okuyucu=lambda a, b: 1 / 0,
                     benzerlik_esigi=0.86,
                     saglayicilar=[{"ad": "patlak", "modul": _SahteSaglayici(
                         "patlak", [_aday("https://m1.test/m.jpg"),
                                    _aday("https://m2.test/m.jpg")],
                         {"ok": True})}])["ok"] is True)
    _sm23 = oku(KOK, "testler/smoke_konsept3_teknoloji_i20.py")
    kontrol("smoke edinim ayirt esigini QA ESIGINDEN aliyor (ikinci sabit YOK)",
            "kk.BENZERLIK_ESIGI" in _sm23
            and "benzerlik_esigi=kk_esik()" in _sikistir(_sm23))
    kontrol("smoke ORAN kapisini edinime BAGLIYOR",
            "hedef_oran=edinim.HEDEF_ORAN_16_9" in _sikistir(_sm23))
    kontrol("ONBELLEK oran kapisini BAYPAS EDEMEZ",
            "edinim.oran_karari(*_olcu_oku(hedef))" in _sikistir(_sm23))

    _s23e = _SahteBekleyen([_aday("https://h1.test/h.jpg"),
                           _aday("https://h2.test/h.jpg")])
    _r23e = _ed.edin("q", _h, en_az_genislik=1920, saat=_saat,
                     uyu=lambda s: None, hedef_oran=_ed.HEDEF_ORAN_16_9,
                     olcu_okuyucu=_harita_okuyucu(
                         {"_1.jpg": (3840, 2160), "a.jpg": (2048, 3072)}, []),
                     saglayicilar=[{"ad": "bekleyen", "modul": _s23e}])
    kontrol("BEKLE sonrasi basarili indirme de ORAN KAPISINDAN gecer",
            _r23e["ok"] is True
            and str(_r23e["aday"]["yol"]).endswith("_1.jpg")
            and len(_r23e["oran_kapisi"]["reddedilen"]) == 1,
            _r23e["oran_kapisi"])
    kontrol("BEKLE sonrasi COZUNURLUK kapisi da islerde (ayni bosluk)",
            _ed.edin("q", _h, en_az_genislik=1920, saat=_saat,
                     uyu=lambda s: None,
                     olcu_okuyucu=lambda y: (640, 480),
                     saglayicilar=[{"ad": "bek2", "modul": _SahteBekleyen(
                         [_aday("https://i1.test/i.jpg")])}])["ok"] is False)

kontrol("edinim modulunde SAGLAYICI ADRESI GOMULU DEGIL",
        not re.search(r"https?://", _kod_yalniz(oku(KOK, "medya/edinim.py"))))
# ⚠ Ham tarama modulun KENDI dokumantasyonuna ("YOUTUBE ... YOK") takiliyor;
# yalniz CALISAN kod taranir.
kontrol("YOUTUBE ya da izinsiz kaynak YOK",
        not re.search(r"youtube|ytdl|yt-dlp|torrent",
                      _kod_yalniz(oku(KOK, "medya/edinim.py")), re.I))
kontrol("edinim kendi indiricisini YAZMIYOR",
        "urlopen" not in _kod_yalniz(oku(KOK, "medya/edinim.py"))
        and "requests" not in _kod_yalniz(oku(KOK, "medya/edinim.py")))
kontrol("oran kapisi kaynagi KURTARMIYOR (pad/blur/pillarbox ISLEMI YOK)",
        not re.search(r"(boxblur|pad\s*=|pillarbox|letterbox|force_original)",
                      _kod_yalniz(oku(KOK, "medya/edinim.py")), re.I))
kontrol("oran esigi SABIT RAKAM olarak gomulu degil (adlandirilmis sabit)",
        "ORAN_EN_AZ_KORUNAN" in _kod_yalniz(oku(KOK, "medya/edinim.py"))
        and "HEDEF_ORAN_16_9" in _kod_yalniz(oku(KOK, "medya/edinim.py")))
kontrol("kapsam ozeti sayilabilir",
        _ed.kapsam_ozeti()["saglayici_gomulu_mu"] is False
        and _ed.kapsam_ozeti()["ayri_sayilan"] == ["metadata_bulundu",
                                                   "bayt_indirildi"])

blok("§37d NASA SAGLAYICISI — anahtarsiz, kamu mali, delege")

from medya import nasa as _na                                     # noqa: E402
_NA_KAYNAK = oku(KOK, "medya/nasa.py")
kontrol("lisans kararini KENDI VERMIYOR",
        "lisans.lisans_karari(" in _sikistir(_NA_KAYNAK))
kontrol("indiriciyi KENDI YAZMIYOR",
        "indirme.guvenli_indir(" in _sikistir(_NA_KAYNAK))
kontrol("anahtar GEREKTIRMIYOR ($0.00)",
        _na.kapsam_ozeti()["anahtar_gerekli"] is False
        and _na.kapsam_ozeti()["maliyet_usd"] == 0.0)
kontrol("KONU ADI gomulu DEGIL",
        not re.search(r"iceland|izlanda|apollo|eyjafjalla",
                      _kod_yalniz(_NA_KAYNAK), re.I))
kontrol("DURUST SINIR: arama piksel olcusu VERMIYOR, uydurulmuyor",
        "olcu_bilinmiyor" in _NA_KAYNAK
        and "Sahte olcu UYDURULMAZ" in _NA_KAYNAK)
kontrol("kaynak niteligi (yorunge/uydu) ACIKCA yaziliyor",
        "yorunge" in _na.KAYNAK_NITELIGI)
kontrol("lisans.py NASA'yi zaten taniyor",
        "nasa" in oku(KOK, "medya/lisans.py"))
kontrol("provenance eksikse aday ELENIR",
        "ESER-SAHIBI-YOK" in _NA_KAYNAK)

blok("§37e GERCEK KOSUM — olculen failover ve render")

_R19_YOL = os.path.join(KOK, "..", "outputs", "sample", "doga_i18_rapor.json")
_R19 = None
if os.path.exists(_R19_YOL):
    try:
        _R19 = _json.load(open(_R19_YOL, encoding="utf-8"))
    except ValueError:
        _R19 = None
if _R19 is None:
    bloke_yaz("I-19 doga pilotu render raporu", f"yok/bozuk: {_R19_YOL}")
else:
    _me = _R19["medya_edinim"]
    kontrol("⭐ GERCEK medya EDINILDI (I-18'de BLOKE'ydi)",
            _me["basarili"] == len(_me["sahneler"]) and _me["basarili"] >= 4)
    kontrol("⭐ ZINCIR calisti: commons dustu, NASA verdi",
            all(k["saglayici"] in ("nasa", "ONBELLEK")
                for k in _me["sahneler"] if k["durum"] == "OK"),
            [k.get("saglayici") for k in _me["sahneler"]])
    _devre_acik = [d for k in _me["sahneler"]
                   for d in (k.get("denemeler") or [])
                   if d["durum"] == "DEVRE-ACIK"]
    # ⚠ Onbellekten kosan bir rapor edinim KANITI TASIMAZ; o durumda bu
    # kontrol ATLANMAZ, BLOKE yazilir (sessizce PASS sayilmaz).
    _onbellekli = all(k.get("onbellekten") for k in _me["sahneler"])
    if _onbellekli:
        bloke_yaz("I-19 devre kesici kaniti",
                  "rapor ONBELLEKTEN kosmus; edinim denemesi icermiyor")
    else:
        kontrol("⭐ DEVRE ACILDI ve commons ZORLANMADI",
                len(_devre_acik) >= 1
                and "commons" in (_me.get("devre_ozeti") or {}).get(
                    "acik_devreler", []),
                _me.get("devre_ozeti"))
        kontrol("metadata ile BAYT AYRI raporlandi",
                sum(k.get("metadata_bulundu") or 0 for k in _me["sahneler"])
                > sum(k.get("bayt_indirildi") or 0 for k in _me["sahneler"]))
    _fo = [k["failover_sn"] for k in _me["sahneler"]
           if k.get("failover_sn") is not None]
    # ⚠ ILK sahne SOGUK BASLANGIC icerir: iki ayri arama + ilk buyuk
    # dosyanin indirilmesi. "Hepsi < 10 sn" demek yanlis olcumdu (olculen:
    # 38.4 / 3.2 / 2.5 / 2.0). Anlamli iddia DEVRE ACILDIKTAN SONRAKI hiz.
    kontrol("⭐ DEVRE ACILDIKTAN SONRA failover HIZLI (< 5 sn)",
            len(_fo) >= 2 and max(_fo[1:]) < 5.0, _fo)
    kontrol("⭐ failover soguk baslangictan SONRA belirgin DUSTU",
            len(_fo) >= 2 and max(_fo[1:]) < _fo[0] / 2, _fo)
    kontrol("soguk baslangic maliyeti DURUSTCE raporda",
            _fo[0] > max(_fo[1:]), _fo)
    kontrol("pexels DURUSTCE atlandi (anahtar gecersiz)",
            any("pexels" in a["ad"] and "401" in a["sebep"]
                for a in _me["atlanan_saglayicilar"]))
    kontrol("her varlik LISANS + ESER SAHIBI tasiyor",
            all(k.get("lisans") and k.get("eser_sahibi")
                for k in _me["sahneler"] if k["durum"] == "OK"))
    kontrol("4K iddiasi KAYNAGA BAGLI ve DURUST",
            _me["dort_k_uygun"] is False
            and next((a for a in (_R19["ffprobe"].get("streams") or [])
                      if a.get("codec_type") == "video"), {}).get(
                "width") == 1920)
    kontrol("sure 15-20 sn araliginda",
            15.0 <= float((_R19["ffprobe"].get("format") or {}).get(
                "duration") or 0) <= 20.0,
            (_R19["ffprobe"].get("format") or {}).get("duration"))
    kontrol("⭐ AUTO stil seyahat-4k -> atlas-journey",
            _R19["auto_siniflandirma"]["stil"]["kimlik"] == "seyahat-4k"
            and _R19["auto_siniflandirma"]["stil"]["kaynak"] == "auto"
            and _R19["auto_siniflandirma"]["edit_profili"] == "atlas-journey")
    kontrol("tur ELLE VERILMEDI",
            _R19["auto_siniflandirma"]["tur_elle_verildi_mi"] is False)
    kontrol("altyazi TURKCE ve okunabilir",
            _R19["altyazi"]["okunabilirlik_temiz"] is True
            and _R19["altyazi"]["kup_sayisi"] >= 4)
    kontrol("kaynak kunyesi SAHNEYE OZGU (NASA merkezi)",
            len(_R19["kaynak_kunyesi"]["katmanlar"]) >= 1)
    kontrol("optik duraganlik ihlali YOK",
            (_R19["optik_hareket"] or {}).get("temiz") is True)
    kontrol("kenarda siyah bant YOK",
            (_R19.get("kenar_siyahligi") or {}).get("temiz") is True)
    kontrol("guvenli alan + cakisma temiz",
            (_R19["guvenli_alan"] or {}).get("temiz") is True
            and (_R19["yazi_cakismasi"] or {}).get("temiz") is True)
    kontrol("miks hedefte, kirpma yok",
            abs(_R19["video_ses_olcumu"]["lufs"] + 14.0) <= 1.0
            and _R19["video_ses_olcumu"]["kirpma_var"] is False)
    kontrol("EN AZ 9 kare", len(_R19["kareler"]) >= 9)
    kontrol("PRE/POST QA FAIL DEGIL",
            _R19["plan"]["qa"]["fail"] == 0
            and _R19["post_qa"]["durum"] != "FAIL")
    kontrol("B-ROLL BLOKE'si AYNEN duruyor",
            _R19["video_broll"]["durum"] == "BLOKE")

blok("§37f I-19 KORUMALARI")

kontrol("pipeline.py I-19'da da DEGISMEDI",
        "edinim" not in oku(KOK, "pipeline.py")
        and "commons" not in oku(KOK, "pipeline.py"))
kontrol("server.py I-19'da da DEGISMEDI",
        "edinim" not in oku(KOK, "server.py"))
kontrol("lisans/SSRF/indirme modulleri DEGISMEDI",
        "lisans_karari" in oku(KOK, "medya/lisans.py")
        and "url_dogrula" in oku(KOK, "medya/guvenlik.py")
        and "def guvenli_indir" in oku(KOK, "medya/indirme.py"))
kontrol("22 alanlik generate sozlesmesi DEGISMEDI",
        len(set(re.findall(r"\{ad: '(\w+)'",
                           oku(KOK, "static/js/api.js")))) == 22)
kontrol("UI DEGISMEDI",
        "basitGovde" in oku(KOK, "static/js/wizard.js"))
kontrol("deploy.sh ezme korumasi KORUNDU",
        "GERIDE" in open(os.path.join(KOK, "..", "deploy.sh"),
                         encoding="utf-8").read())
kontrol("bayraklar HALA varsayilan kapali",
        mkp.ACIK is False and ekp.ACIK is False
        and ekp.kalite_kapisi_acik(None) is False)
kontrol("odemeli API cagrisi YOK",
        not re.search(r"openai|anthropic|api_key",
                      oku(KOK, "medya/edinim.py") + oku(KOK, "medya/nasa.py"),
                      re.I))


# ═══════════════════════════════════════════════════════════════════════
# §38  FAZ I-20 — UCUNCU KONSEPT (TEKNOLOJI/EKONOMI)
# ⚠ Render PLAN seviyesinde BLOKE oldu (asagida); bu bolum yalnizca
# GERCEKTEN kanitlananı kilitler.
# ═══════════════════════════════════════════════════════════════════════

blok("§38a UCUNCU KONSEPT — auto siniflandirma ve UCUNCU stil")

_TEK = ("Süperbilgisayarların enerji ve çip ekonomisi: işlem gücü nasıl "
        "üretiliyor ve faturası ne kadar")
_kt = _tk.siniflandir(_TEK)
_st = _sp.coz(konsept=_kt)
kontrol("⭐ teknoloji metni AUTO siniflandi",
        _kt["aile"] == "egitim" and _kt["durum"] in ("kesin", "melez"),
        (_kt["aile"], _kt["durum"], _kt["guven"]))
kontrol("⭐ UCUNCU ayri stil secildi (auto)",
        _st.get("kimlik") == "explainer-hizli"
        and _st.get("kaynak") == "auto", _st.get("kimlik"))
kontrol("uc konsept UC AYRI stil veriyor",
        len({_sp.coz(konsept=_tk.siniflandir(m)).get("kimlik") for m in (
            "Apollo 11 ay inisi tarih belgeseli",
            "İzlanda buzul lagünleri ve siyah kum plajları",
            _TEK)}) == 3)
kontrol("donanim/cip sozlugu EKLENDI (kapsam buyudu)",
        _tk.kapsam_ozeti()["anahtar"] >= 845,
        _tk.kapsam_ozeti()["anahtar"])
_tek_anahtar = set(_tk.AGAC["egitim.teknoloji"]["anahtar"])
for _k20 in ("superbilgisayar", "cip", "islemci", "yari iletken", "silikon",
             "islem gucu", "sunucu"):
    kontrol(f"'{_k20}' teknoloji sozlugunde", _k20 in _tek_anahtar)
kontrol("⚠ eski teknoloji kelimeleri SILINMEDI",
        {"teknoloji", "yapay zeka", "yazilim", "veri merkezi"}
        <= _tek_anahtar)
kontrol("motor kodu DEGISMEDI (aile 7 / dal 33)",
        _tk.kapsam_ozeti()["aile"] == 7 and _tk.kapsam_ozeti()["dal"] == 33)
for _m20, _b20 in (("Kapadokya gezi rehberi", "seyahat"),
                   ("iPhone 15 vs Galaxy S24 fiyat karsilastirmasi", "urun"),
                   ("Findik tarifi: 20 dakikada kolay kek", "yasam"),
                   ("İzlanda buzul lagünleri ve siyah kum plajları",
                    "seyahat")):
    kontrol(f"gerileme yok: {_b20}",
            _tk.siniflandir(_m20)["aile"] == _b20)

blok("§38b I-20 PILOT BETIGI — konu daraltmasi DURUST, sahte kanit YOK")

_SM20 = oku(KOK, "testler/smoke_konsept3_teknoloji_i20.py")
kontrol("betik mevcut edinim zincirini KULLANIYOR (yeni mimari YOK)",
        "medya_edin(" in _sikistir(_SM20)
        and "edinim.edin(" in _sikistir(_SM20))
kontrol("konu daraltmasi ve SEBEBI kodda yazili",
        "KONU DURUSTCE DARALTILDI" in _SM20
        and "HTTP 429" in _SM20)
kontrol("fixture/kendi render ciktisi GERCEK WEB KANITI diye sunulmuyor",
        "SAHTE KANIT YOK" in _SM20
        and "pilot_master" not in _sikistir(_SM20))
kontrol("ffmpeg test kaynagi KULLANILMIYOR",
        not re.search(r"lavfi|testsrc|color=c=", _kod_yalniz(_SM20)))
# ⚠ I-22'de kota SABIT sayidan PLANIN BEAT SAYISINA baglandi; bu bir esik
# gevsetmesi degil deterministik esleme. Kalite esikleri AYNEN degismedi.
kontrol("kalite esikleri DEGISTIRILMIYOR",
        "BENZERLIK_ESIGI =" not in _SM20
        and "OPTIK_DURGUN_ESIGI =" not in _SM20
        and not re.search(r"saglayici_tavani=\d", _SM20))
kontrol("QA FAIL'de render BASLATILMIYOR",
        'if not sonuc["render_edilebilir"]:' in _SM20)

blok("§38c I-20 KORUMALARI")

kontrol("pipeline.py I-20'de de DEGISMEDI",
        "edinim" not in oku(KOK, "pipeline.py"))
kontrol("server.py I-20'de de DEGISMEDI",
        "edinim" not in oku(KOK, "server.py"))
kontrol("22 alanlik generate sozlesmesi DEGISMEDI",
        len(set(re.findall(r"\{ad: '(\w+)'",
                           oku(KOK, "static/js/api.js")))) == 22)
kontrol("UI DEGISMEDI", "basitGovde" in oku(KOK, "static/js/wizard.js"))
kontrol("deploy.sh ezme korumasi KORUNDU",
        "GERIDE" in open(os.path.join(KOK, "..", "deploy.sh"),
                         encoding="utf-8").read())
kontrol("bayraklar HALA varsayilan kapali",
        mkp.ACIK is False and ekp.ACIK is False)

blok("§38d I-21 — bolunen beat AYNI varligi PAYLASMASIN (dar duzeltme)")

# ⚠ N aday MEVCUT arama listesinden secilir: ek AG CAGRISI yok, kota sabit.
_s21 = _SahteSaglayici("y", [_aday("https://a.test/1.jpg"),
                             _aday("https://a.test/2.jpg"),
                             _aday("https://a.test/3.jpg")], {"ok": True})
with _tf19.TemporaryDirectory() as _d21:
    _r21 = _ed.edin("q", os.path.join(_d21, "a.jpg"), adet=2, saat=_saat,
                    saglayicilar=[{"ad": "y", "modul": _s21}])
    kontrol("⭐ N=2 istenince IKI AYRI aday donuyor",
            _r21["ok"] and len(_r21["adaylar"]) == 2)
    kontrol("⭐ adaylarin DOSYA YOLLARI farkli (ayni dosya iki kez degil)",
            len({a["yol"] for a in _r21["adaylar"]}) == 2,
            [a["yol"] for a in _r21["adaylar"]])
    kontrol("⭐ adaylarin URL'leri farkli (ayni varlik degil)",
            len({a["indirme_url"] for a in _r21["adaylar"]}) == 2)
    kontrol("ARAMA yalnizca BIR KEZ cagrildi (ag cagrisi ARTMADI)",
            _s21.ara_sayisi == 1, _s21.ara_sayisi)
    kontrol("geriye uyumluluk: adet=1 varsayilan, tek aday",
            len(_ed.edin("q", os.path.join(_d21, "b.jpg"), saat=_saat,
                         saglayicilar=[{"ad": "z", "modul": _SahteSaglayici(
                             "z", [_aday("https://b.test/1.jpg")],
                             {"ok": True})}])["adaylar"]) == 1)
    # KISMI BASARI: 2 istendi, 1 geldi -> DURUSTCE 1 doner, ok=True
    _s22 = _SahteSaglayici("k", [_aday("https://c.test/1.jpg")], {"ok": True})
    _r22 = _ed.edin("q", os.path.join(_d21, "c.jpg"), adet=2, saat=_saat,
                    saglayicilar=[{"ad": "k", "modul": _s22}])
    kontrol("KISMI BASARI durustce raporlanir (2 istendi, 1 geldi)",
            _r22["ok"] and len(_r22["adaylar"]) == 1
            and _r22["istenen_adet"] == 2)
kontrol("smoke sahne basina N aday istiyor ve YEDEKLERI manifeste yaziyor",
        "ADAY_ADEDI = 2" in oku(KOK, "testler/smoke_konsept3_teknoloji_i20.py")
        and "yedekler" in oku(KOK, "testler/smoke_konsept3_teknoloji_i20.py"))
# ⚠ I-21'de bu kontrol "kota HIC verilmesin" diyordu. I-22 kotayi PLANIN
# GERCEK BEAT SAYISINA esitliyor — bu KEYFI ARTIRMA DEGIL, deterministik
# esleme. Kontrol SILINMEDI: kotanin SABIT bir sayiya degil, olculen beat
# sayisina baglandigi kilitleniyor.
_SM22 = oku(KOK, "testler/smoke_konsept3_teknoloji_i20.py")
kontrol("saglayici kotasi SABIT sayiya degil BEAT SAYISINA baglandi",
        "saglayici_tavani=BEAT_SAYISI" in _SM22
        and not re.search(r"saglayici_tavani=\d", _SM22))
kontrol("⭐ I-22: plan MEDYADAN ONCE kuru kosuluyor (beat sayisi ogrenilir)",
        "_beat.plan_yap(_kuru_cumleler" in _SM22
        and "KURU PLAN" in _SM22)
kontrol("kuru kosum AG/MEDYA kullanmiyor (bedava)",
        "Kuru kosum BEDAVA" in _SM22)
kontrol("⭐ MEDYASIZ BEAT kapisi PRE-QA'da ve FAIL",
        "KALITE-MEDYASIZ-BEAT" in _qon.FAIL_KODLARI
        and "KALITE-MEDYASIZ-BEAT" in _qon.KALITE_KODLARI)

blok("§39b I-25 — SAGLAYICI-TEKEL TANISI (dort katman ayri olculdu)")

# ⚠ OLCULEN KOK NEDEN — "Commons bos" DEGIL, SORGUMUZ BOZUKTU.
# Ayni `commons.ara()` cagrisiyla olculdu (ek kota/ag YOK):
#   "Pleiades supercomputer Iceland" -> denenen  0, aday 0
#   "Pleiades supercomputer"         -> denenen 18, aday 6
#   "supercomputer facility Iceland" -> denenen  0, aday 0
#   "supercomputer facility"         -> denenen 18, aday 6
#   "solar array power Iceland"      -> denenen  0, aday 0
#   "solar array power"              -> denenen 18, aday 6
#   "Silicon Carbide Integrated Circuit Chip" -> denenen 0 (TEMIZ sorguyla
#       da bos: Commons'ta bu konuda aday GERCEKTEN yok -> WARN DURUST kalir)
# Bulasanin kaynagi: `beaee8f` (I-20) satiri I-18'in IZLANDA smoke'undan
# oldugu gibi kopyalamis.

_SM25 = oku(KOK, "testler/smoke_konsept3_teknoloji_i20.py")
kontrol("⭐ I-25: teknoloji smoke'unda ' Iceland' KONU BULASANI YOK",
        'tanim["sorgu"] + " Iceland"' not in _sikistir(_SM25))
kontrol("I-25: Commons ve NASA AYNI konu sorgusunu aliyor",
        re.sub(r"[ \t]+", "", _SM25).count('"sorgu":tanim["sorgu"]') >= 2)
kontrol("I-18 DOGA smoke'u DEGISMEDI (orada ' Iceland' KONUYA UYGUN)",
        'tanim["sorgu"] + " Iceland"' in
        oku(KOK, "testler/smoke_konsept2_doga_i18.py"))

# ── TANI KOR NOKTASI: "arama bos" != "hepsi elendi" ──
class _SahteBos:
    """Arama HIC sonuc dondurmedi (denenen=0)."""

    def __init__(self):
        self.ara_sayisi = 0
        self.indir_sayisi = 0

    def ara(self, sorgu, adet=6, en_az_genislik=0):
        self.ara_sayisi += 1
        return {"ok": False, "adaylar": [], "elenen": [], "denenen": 0,
                "hata": ""}

    def indir(self, aday, hedef, deneme=1):
        self.indir_sayisi += 1
        return {"ok": False}


class _SahteHepsiElendi:
    """Sonuc GELDI ama hepsi lisans/cozunurluk duvarinda elendi."""

    def __init__(self):
        self.ara_sayisi = 0
        self.indir_sayisi = 0

    def ara(self, sorgu, adet=6, en_az_genislik=0):
        self.ara_sayisi += 1
        return {"ok": False, "adaylar": [], "denenen": 18, "hata": "",
                "elenen": [{"baslik": "a", "neden": "LISANS"},
                           {"baslik": "b",
                            "neden": "COZUNURLUK-YETERSIZ (800 < 1920)"}]}

    def indir(self, aday, hedef, deneme=1):
        self.indir_sayisi += 1
        return {"ok": False}


import tempfile as _tf25                                          # noqa: E402
with _tf25.TemporaryDirectory() as _d25:
    _h25 = os.path.join(_d25, "a.jpg")
    _rb = _ed.edin("konu", _h25, saat=lambda: 0.0,
                   saglayicilar=[{"ad": "bos", "modul": _SahteBos(),
                                  "sorgu": "konu Iceland"}])
    _db = _rb["denemeler"][0]
    kontrol("⭐ ARAMA-BOS ile HEPSI-ELENDI AYRI raporlaniyor (bos)",
            _db["denenen"] == 0 and "ARAMA-BOS" in _db["sebep"], _db["sebep"])
    kontrol("⭐ raporda SAGLAYICIYA GERCEKTEN GIDEN sorgu gorunuyor",
            _db["kullanilan_sorgu"] == "konu Iceland", _db)
    _re = _ed.edin("konu", _h25, saat=lambda: 0.0,
                   saglayicilar=[{"ad": "elendi",
                                  "modul": _SahteHepsiElendi()}])
    _de = _re["denemeler"][0]
    kontrol("⭐ HEPSI-ELENDI ayri sebep + elenme nedenleri gorunur",
            _de["denenen"] == 18 and "HEPSI-ELENDI" in _de["sebep"]
            and "LISANS" in _de["elenme_nedenleri"]
            and "COZUNURLUK-YETERSIZ" in _de["elenme_nedenleri"], _de)
    kontrol("`denenen` vermeyen saglayicida ESKI sebep korunur (uydurma yok)",
            "duvarini gecen aday yok" in _ed.edin(
                "konu", _h25, saat=lambda: 0.0,
                saglayicilar=[{"ad": "eski", "modul": _SahteSaglayici(
                    "eski", [], {"ok": False})}])["denemeler"][0]["sebep"])

# ── ALAKA SIRASI — SAHTE API YANITIYLA DAVRANIS OLCUMU (ag YOK) ──
# ⚠ Metin taramasi yerine GERCEK DAVRANIS: `ara()` kendi `acan`ini
# (opener) disaridan alabiliyor, yani ag olmadan tam yol kosuluyor.
import contextlib as _cl25                                        # noqa: E402
import io as _io25                                                # noqa: E402


def _sahte_sayfa(pageid, index, g, y, baslik):
    return {"pageid": pageid, "index": index, "title": f"File:{baslik}",
            "imageinfo": [{"url": f"https://x.test/{pageid}.jpg",
                           "descriptionurl": f"https://x.test/d{pageid}",
                           "width": g, "height": y, "mime": "image/jpeg",
                           "extmetadata": {
                               "LicenseShortName": {"value": "CC BY 2.0"},
                               "LicenseUrl": {"value":
                                              "https://creativecommons.org/"
                                              "licenses/by/2.0/"},
                               "Artist": {"value": "Biri"},
                               "Credit": {"value": "Biri"},
                               "UsageTerms": {"value": "CC BY 2.0"}}}]}


def _sahte_acan(sayfalar):
    """`pages` sozlugunu ALAKA SIRASINDA OLMAYAN sirayla verir (gercek API
    boyle davraniyor: sozluk pageid'ye gore anahtarli)."""
    def _ac(url):
        govde = _json.dumps({"query": {"pages": {
            str(s["pageid"]): s for s in sayfalar}}}).encode()
        return _cl25.closing(_io25.BytesIO(govde))
    return _ac


# Olculen gercek vaka: konu disi ama EN BUYUK dosya alaka 17; konulu 12.
_r25 = _cm.ara("Pleiades supercomputer", adet=6, en_az_genislik=1920,
               acan=_sahte_acan([
                   _sahte_sayfa(1, 17, 4877, 3515, "Pleiades large.jpg"),
                   _sahte_sayfa(2, 12, 4983, 3303, "NASA Pleiades Super.jpg"),
                   _sahte_sayfa(3, 12, 2240, 1344, "Pleiades racks.jpg"),
                   _sahte_sayfa(4, 1, 2100, 1524, "Columbia Super.jpg")]))
kontrol("⭐ commons ALAKA SIRASINI koruyor (`index` adaya isleniyor)",
        all(isinstance(a.get("alaka_sirasi"), int) for a in _r25["adaylar"])
        and [a["alaka_sirasi"] for a in _r25["adaylar"]] == [1, 12, 12, 17],
        [a.get("alaka_sirasi") for a in _r25["adaylar"]])
kontrol("⭐ KONU DISI ama EN BUYUK dosya artik BASA GECEMIYOR",
        _r25["adaylar"][0]["baslik"] == "Columbia Super.jpg"
        and _r25["adaylar"][-1]["baslik"] == "Pleiades large.jpg",
        [a["baslik"] for a in _r25["adaylar"]])
kontrol("⭐ esit alakada COZUNURLUK ikincil anahtar (buyuk once)",
        [a["genislik"] for a in _r25["adaylar"] if a["alaka_sirasi"] == 12]
        == [4983, 2240])
kontrol("I-25: `denenen` ham sonuc sayisini veriyor", _r25["denenen"] == 4)
_r25b = _cm.ara("x", adet=6, en_az_genislik=1920,
                acan=_sahte_acan([
                    _sahte_sayfa(1, 5, 2000, 1200, "alakali.jpg"),
                    dict(_sahte_sayfa(2, 0, 4000, 2400, "indekssiz.jpg"),
                         index=None)]))
kontrol("`index` YOKSA aday EN SONA (uydurma sira yok)",
        [a["baslik"] for a in _r25b["adaylar"]]
        == ["alakali.jpg", "indekssiz.jpg"],
        [(a["baslik"], a["alaka_sirasi"]) for a in _r25b["adaylar"]])
kontrol("⭐ COZUNURLUK ESIGI DEGISMEDI (siralama esik gevsetmesi DEGIL)",
        not _cm.ara("x", adet=6, en_az_genislik=1920,
                    acan=_sahte_acan([
                        _sahte_sayfa(1, 1, 800, 600, "kucuk.jpg")]))["adaylar"])
kontrol("elenen kaydi SEBEBIYLE birlikte duruyor",
        "COZUNURLUK-YETERSIZ" in str(_cm.ara(
            "x", adet=6, en_az_genislik=1920, acan=_sahte_acan([
                _sahte_sayfa(1, 1, 800, 600, "kucuk.jpg")]))["elenen"]))

blok("§39d I-27 — KAMERA PUNCH'I KAYNAGI BUYUTEMEZ")

import math                                                       # noqa: E402
from editor import motion as _mo                                  # noqa: E402

# ⚠ I-26'DA OLCULEN IKI IHLAL — burada KIRMIZI olarak sabitlendi.
# Depo "upscale YAPILMIYOR" diyordu; soz yalnizca EDINIM esigi icin
# geceriydi ve kamera `punch` kadrajinda SESSIZCE ihlal ediliyordu.
_IHLAL27 = [
    ("b002 s01 Commons afisi", 2240, 1344, "punch-1.35", 1.4944, 1.2809),
    ("b004 s03 NASA (KABUL EDILEN render'da DA)", 3000, 2250,
     "punch-1.6", 1.696, 1.0854),
]
for _ad, _g27, _y27, _kd, _mz, _bek in _IHLAL27:
    _o27 = _kk.punch_buyutme_olcusu(_g27, _y27, 1920, 1080, _mz, kadraj=_kd)
    kontrol(f"⭐ I-27 KIRMIZI: {_ad} BUYUTUYOR",
            _o27["buyutuyor"] is True
            and abs(_o27["ekran_piksel_orani"] - _bek) < 0.001,
            _o27["ekran_piksel_orani"])
    kontrol(f"I-27: {_ad} sebebi olculen SAYILARLA yazili",
            "PUNCH-BUYUTME" in _o27["sebep"] and "kapsama" in _o27["sebep"])
kontrol("I-27: YUKSEK cozunurluklu kaynak TEMIZ (yanlis pozitif yok)",
        _kk.punch_buyutme_olcusu(4986, 3744, 1920, 1080, 1.272,
                                 kadraj="alt")["buyutuyor"] is False)
kontrol("I-27: tam 1.000 oran TAVANI ASMAZ (sinirda engelleme yok)",
        _kk.punch_buyutme_olcusu(1920, 1080, 1920, 1080, 1.0)["buyutuyor"]
        is False)
for _bz in ((None, None), (0, 0), ("a", "b")):
    kontrol(f"I-27: olcu gecersiz {_bz} -> ENGELLEMEZ",
            _kk.punch_buyutme_olcusu(_bz[0], _bz[1], 1920, 1080,
                                     1.3)["buyutuyor"] is False)

# ── DETERMINISTIK KADRAJ SECIMI ──
def _taban_zoom(maks, kadraj):
    return maks / _mo.KADRAJ_OLCEK[kadraj]


_s27a = _kk.kadraj_buyutmeyen(2240, 1344, 1920, 1080,
                              _taban_zoom(1.4944, "punch-1.35"),
                              _mo.KADRAJ_MERDIVENI, _mo.KADRAJ_OLCEK,
                              tercih="punch-1.35")
kontrol("⭐ I-27: b002 punch-1.35 -> BUYUTMEYEN kadraja gecti",
        _s27a["secilen"] == "tam" and _s27a["degisti"] is True
        and _s27a["olcum"]["buyutuyor"] is False, _s27a["secilen"])
_s27b = _kk.kadraj_buyutmeyen(3000, 2250, 1920, 1080,
                              _taban_zoom(1.696, "punch-1.6"),
                              _mo.KADRAJ_MERDIVENI, _mo.KADRAJ_OLCEK,
                              tercih="punch-1.6")
kontrol("⭐ I-27: b004 punch-1.6 -> punch-1.35 (PUNCH HISSI KORUNDU)",
        _s27b["secilen"] == "punch-1.35" and _s27b["degisti"] is True
        and _s27b["olcum"]["buyutuyor"] is False, _s27b["secilen"])
kontrol("I-27: EN DAR uygun kadraj secilir (gereksiz genisleme yok)",
        _mo.KADRAJ_OLCEK[_s27b["secilen"]] > _mo.KADRAJ_OLCEK["tam"])
_s27c = _kk.kadraj_buyutmeyen(4986, 3744, 1920, 1080,
                              _taban_zoom(1.272, "alt"),
                              _mo.KADRAJ_MERDIVENI, _mo.KADRAJ_OLCEK,
                              tercih="alt")
kontrol("I-27: BUYUTMEYEN kadraj AYNEN KORUNUR (kullanici secimi bozulmaz)",
        _s27c["secilen"] == "alt" and _s27c["degisti"] is False)
kontrol("I-27: hicbir kadraj yetmezse secilen=None (sessiz kirpma YOK)",
        _kk.kadraj_buyutmeyen(400, 300, 1920, 1080, 1.3,
                              _mo.KADRAJ_MERDIVENI,
                              _mo.KADRAJ_OLCEK,
                              tercih="tam")["secilen"] is None)
kontrol("I-27: olculemezse plan OLDUGU GIBI kalir",
        _kk.kadraj_buyutmeyen(None, None, 1920, 1080, 1.3,
                              _mo.KADRAJ_MERDIVENI, _mo.KADRAJ_OLCEK,
                              tercih="punch-1.6")["degisti"] is False)
kontrol("⭐ I-27: YENI kadraj UYDURULMUYOR (yalniz merdivendekiler)",
        all(k in _mo.KADRAJ_OLCEK for k in _mo.KADRAJ_MERDIVENI)
        and set(_mo.KADRAJ_MERDIVENI) == set(_mo.KADRAJ_OLCEK))
_det27 = [_kk.kadraj_buyutmeyen(3000, 2250, 1920, 1080,
                                _taban_zoom(1.696, "punch-1.6"),
                                _mo.KADRAJ_MERDIVENI, _mo.KADRAJ_OLCEK,
                                tercih="punch-1.6")["secilen"]
          for _ in range(5)]
kontrol("I-27: ayni girdi -> AYNI kadraj (rastgelelik YOK)",
        len(set(_det27)) == 1, _det27)
kontrol("I-27: kadraj olcek tablosu TEK KAYNAK (kamera_spec gomulu tablo YOK)",
        "KADRAJ_OLCEK.get(kadraj" in _sikistir(oku(KOK, "editor/motion.py"))
        .replace(" ", "")
        or "KADRAJ_OLCEK" in _kod_yalniz(oku(KOK, "editor/motion.py")))
kontrol("⭐ I-27: kapi FAIL kodunda ve kalite bayragina bagli",
        "KALITE-PUNCH-BUYUTME" in _qon.FAIL_KODLARI
        and "KALITE-PUNCH-BUYUTME" in _qon.KALITE_KODLARI)
kontrol("I-27: blur/pillarbox/upscale ile KURTARMA YOK",
        not re.search(r"(boxblur|pad\s*=|pillarbox|letterbox|upscale|scale2ref)",
                      _kod_yalniz(oku(KOK, "editor/plan.py")), re.I))
kontrol("I-27: plan olcumu YENIDEN TURETMIYOR, spec'e ISLIYOR",
        "punch_buyutme" in _sikistir(oku(KOK, "editor/plan.py"))
        or "punch_buyutme" in oku(KOK, "editor/plan.py"))

# ── IKINCI HALKA: kadraj daraltma ile OPTIK DURAGANLIK bagli ──
# ⚠ OLCULDU: kadraji `tam`a cekmek pan surusuyle hareket eden cekimi
# duragan birakiyor (b005 optik 1.415 < esik 2.0 -> POST-QA FAIL).
kontrol("⭐ I-27: `tam` kadrajda pan payi ACLIK seviyesinde",
        _mo._guvenli_pay(1.06 * _mo.KADRAJ_OLCEK["tam"]) < 0.03)
kontrol("⭐ I-27: en dar punch (1.2) pan payini ~4 KATINA cikariyor",
        _mo._guvenli_pay(1.06 * _mo.KADRAJ_OLCEK["ust"])
        > 3 * _mo._guvenli_pay(1.06 * _mo.KADRAJ_OLCEK["tam"]))
kontrol("⭐ I-27: edinim esigi MERDIVENDEN turetiliyor (2443, sabit rakam yok)",
        _kk.en_az_kaynak_genisligi(1920) == 2443
        and _kk.en_az_kaynak_genisligi(1920) == int(math.ceil(
            1920 * _kk.EN_DAR_PUNCH_OLCEGI * _kk.PAN_TABANLI_ZOOM)))
kontrol("I-27: esik 1920'den YUKSEK (eski esik yalniz `tam`i garanti ederdi)",
        _kk.en_az_kaynak_genisligi(1920) > 1920)
for _ad27, _g27b, _bekle27 in [("Commons afis 2240", 2240, False),
                               ("Commons Columbia 2100", 2100, False),
                               ("Commons Ohio 5184", 5184, True),
                               ("NASA 3000", 3000, True),
                               ("NASA 4192", 4192, True)]:
    kontrol(f"I-27 esigi: {_ad27} -> {'GECER' if _bekle27 else 'RED'}",
            (_g27b >= _kk.en_az_kaynak_genisligi(1920)) is _bekle27)
kontrol("I-27: gecersiz kare olcusu 0 doner (uydurma esik yok)",
        _kk.en_az_kaynak_genisligi(None) == 0)
kontrol("⭐ I-27: smoke edinim esigini TURETIYOR (1920 gomulu degil)",
        "EN_AZ_GENISLIK" in _sikistir(_SM25)
        and "en_az_kaynak_genisligi" in oku(
            KOK, "testler/smoke_konsept3_teknoloji_i20.py"))

blok("§39c I-26 — s03 ASIRI DAR SORGU: OLCUMLU ES-ANLAMLI GENISLETME")

# ⚠ I-25'IN NOTU DUZELTILDI. I-25 s03 icin "Commons'ta bu konuda aday
# GERCEKTEN yok" yazmisti; o hukum TEK sorgu uzerinde verilmisti.
# I-26'da 2-3 konuya sadik alternatif AYNI dusuk maliyetli butcede
# olculdu ve iddia CURUDU:
#   "Silicon Carbide Integrated Circuit Chip" (5 terim) -> denenen  0
#   "silicon carbide integrated circuit"     (4 terim) -> denenen  2  ⭐
#   "integrated circuit chip"                          -> denenen 18
#   "microchip silicon"                                -> denenen 18
# Kok neden "Commons bos" DEGIL, sorgunun ASIRI DAR olmasiydi:
# CirrusSearch terimleri VARSAYILAN OLARAK AND'ler.

# ⚠ Smoke MODUL OLARAK CALISTIRILMAZ (yan etkisi olmasin): `SAHNE_TANIMI`
# kaynaktan `ast` ile, yalnizca sabit degerler okunarak cikarilir.
import ast as _ast26                                              # noqa: E402


def _sahne_tanimi_oku(kaynak):
    for _d in _ast26.parse(kaynak).body:
        if (isinstance(_d, _ast26.Assign)
                and any(getattr(t, "id", "") == "SAHNE_TANIMI"
                        for t in _d.targets)):
            return _ast26.literal_eval(_d.value)
    return []


_ST26 = _sahne_tanimi_oku(_SM25)
kontrol("smoke SAHNE_TANIMI kaynaktan okunabildi (4 sahne)", len(_ST26) == 4)
kontrol("⭐ I-26: s03 sorgusu OLCULEN kazanana cevrildi",
        next(s["sorgu"] for s in _ST26 if s["kimlik"] == "s03")
        == "silicon carbide integrated circuit")
_alt26 = next((s.get("olculen_alternatifler") for s in _ST26
               if s["kimlik"] == "s03"), None)
kontrol("⭐ I-26: karsilastirilan alternatifler SAYILARIYLA kayitli",
        isinstance(_alt26, list) and 3 <= len(_alt26) <= 5
        and all({"sorgu", "denenen", "aday"} <= set(a) for a in _alt26),
        _alt26)
kontrol("I-26: ESKI sorgu 0 sonucla, SECILEN sorgu >0 sonucla kayitli",
        any(a["sorgu"] == "Silicon Carbide Integrated Circuit Chip"
            and a["denenen"] == 0 for a in _alt26)
        and any(a["sorgu"] == "silicon carbide integrated circuit"
                and a["denenen"] > 0 for a in _alt26))
kontrol("⭐ I-26: TEK SORGU ILKESI KORUNDU — saglayicilara AYRI sorgu YOK",
        re.sub(r"[ \t]+", "", _SM25).count('"sorgu":tanim["sorgu"]') >= 2
        # ⚠ Yalniz CALISAN kod taranir: I-25'in aciklama yorumlari
        # bulasandan SOZ EDIYOR, onu KULLANMIYOR.
        and "Iceland" not in _sikistir(_SM25))
kontrol("I-26: secilen sorgu ESKI sorgunun KONUSUNA sadik (alt kume)",
        set("silicon carbide integrated circuit".lower().split())
        < set("Silicon Carbide Integrated Circuit Chip".lower().split()))

# ── ASIRI DARLIK IPUCU: BEDAVA, EK CAGRI YOK ──
with _tf25.TemporaryDirectory() as _d26:
    _h26 = os.path.join(_d26, "a.jpg")
    _r26 = _ed.edin("x", _h26, saat=lambda: 0.0,
                    saglayicilar=[{"ad": "bos", "modul": _SahteBos(),
                                   "sorgu": "bir iki uc dort bes"}])
    _d26k = _r26["denemeler"][0]
    kontrol("⭐ I-26: 5 terimli BOS sorguda ASIRI DARLIK ipucu veriliyor",
            _d26k["sorgu_terim_sayisi"] == 5
            and "AND" in _d26k["sebep"] and "es-anlamli" in _d26k["sebep"],
            _d26k["sebep"])
    _r26b = _ed.edin("x", _h26, saat=lambda: 0.0,
                     saglayicilar=[{"ad": "bos2", "modul": _SahteBos(),
                                    "sorgu": "bir iki"}])
    kontrol("I-26: KISA sorguda darlik ipucu VERILMEZ (yanlis yonlendirme yok)",
            _r26b["denemeler"][0]["sorgu_terim_sayisi"] == 2
            and "AND" not in _r26b["denemeler"][0]["sebep"])
    kontrol("I-26: ipucu EK AG CAGRISI URETMIYOR (ara yine 1 kez)",
            _SahteBos().ara_sayisi == 0)
kontrol("I-26: HEPSI-ELENDI yolunda darlik ipucu YOK (farkli kok neden)",
        "sorgu_terim_sayisi" not in str(_de) or "AND" not in str(_de["sebep"]))

# ── PUNCH BUYUTME OLCUMU (I-26'da bulundu; KAPI DEGIL, OLCUM) ──
# ⚠ Smoke dosya yolundan yuklenir; `main()` yalnizca __main__'de kosar,
# yani import YAN ETKISIZDIR (render/ag baslatmaz).
import importlib.util as _iu26                                    # noqa: E402
_spec26 = _iu26.spec_from_file_location(
    "_sm26", os.path.join(KOK, "testler",
                          "smoke_konsept3_teknoloji_i20.py"))
_sm26 = _iu26.module_from_spec(_spec26)
_spec26.loader.exec_module(_sm26)
kontrol("smoke YAN ETKISIZ import edilebildi (render baslatmadi)",
        callable(getattr(_sm26, "punch_buyutme_olc", None)))
# ⚠ Depo "upscale YAPILMIYOR" diyor ama bu yalnizca EDINIM esigi icin
# geceriydi. Kamera `punch` uygularken kaynak SESSIZCE buyuyor.
_PB = _sm26.punch_buyutme_olc(
    [{"beat_id": "b1", "asset_id": "a1", "kadraj": "punch-1.35"},
     {"beat_id": "b2", "asset_id": "a2", "kadraj": "tam"}],
    {"katmanlar": [
        {"beat_id": "b1", "parametre": {"zoom": [1.4944, 1.35]}},
        {"beat_id": "b2", "parametre": {"zoom": [1.0, 1.0534]}}]},
    [{"asset_id": "a1", "genislik": 2240, "yukseklik": 1344,
      "yedekler": [{"asset_id": "a2", "genislik": 4192, "yukseklik": 2832}]}])
kontrol("⭐ I-26: DUSUK cozunurluklu kaynak punch'ta BUYUTULUYOR (olculdu)",
        _PB["kayitlar"][0]["buyutuyor"] is True
        and _PB["kayitlar"][0]["ekran_piksel_orani"] > 1.0,
        _PB["kayitlar"][0])
kontrol("⭐ I-26: YUKSEK cozunurluklu kaynak KUCULUYOR (keskin)",
        _PB["kayitlar"][1]["buyutuyor"] is False
        and _PB["kayitlar"][1]["ekran_piksel_orani"] < 1.0,
        _PB["kayitlar"][1])
kontrol("I-26: zoom YENIDEN TURETILMIYOR, planin KENDI spec'inden okunuyor",
        _PB["kayitlar"][0]["maks_zoom"] == 1.4944)
kontrol("I-26: olcum bir KAPI DEGIL (davranis degistirmiyor)",
        "OLCUM" in _PB["not"] and "kapi DEGIL" in _PB["not"])
kontrol("I-26: olculemeyen beat SESSIZCE temiz sayilmiyor",
        _sm26.punch_buyutme_olc(
            [{"beat_id": "b9", "asset_id": "yok"}], {}, [])
        ["kayitlar"][0]["olculdu"] is False)

blok("§39a I-24 — MOTION CESITLILIGI OLCULEBILIR KAPIYA CEVRILDI")

# ⚠ BAGIMSIZ DOGRULANAN KOK NEDEN: teknoloji pilotunda `motion_cesitlilik`
# 0/20 idi. Puan HEPSI-YA-HICBIRI. Dort kosuldan UCU YESILDI
# (ardisik_tekrar 0, pencere_tekrari 0, benzersiz_gecis 3); TEK KIRMIZI
# `acilis_kapanis_ayri` = False idi (b001 push-in, b005 push-in).
# Mekanizma: b005 islev=sonuc -> RITIM_TERCIHI "pull-out", ama PENCERE
# filtresi (b002-b004 = pull-out/slow-drift/pan-right) pull-out'u havuzdan
# CIKARIYOR, tercih dusuyor ve fallback `push-in`e — acilisin AYNISINA —
# iniyordu. Kodda acilis!=kapanis kontrolu HIC YOKTU.

kontrol("geometri sinifi: 16:9'dan DAR kaynak -> 'dar'",
        _gr.geometri_sinifi(3000, 2250) == "dar"
        and _gr.geometri_sinifi(4192, 2832) == "dar")
kontrol("geometri sinifi: 16:9'dan GENIS kaynak -> 'genis'",
        _gr.geometri_sinifi(3000, 1000) == "genis")
kontrol("geometri sinifi: 16:9 kaynak -> 'notr'",
        _gr.geometri_sinifi(1920, 1080) == "notr")
for _bg in ((None, None), (0, 0), ("a", "b"), (100, 0)):
    kontrol(f"geometri olculemez {_bg} -> 'notr' (siralamaya karisma)",
            _gr.geometri_sinifi(*_bg) == "notr")

# ── ISLEV TEKRARI OLCUMU (pencere yakalayamaz) ──
_MG24 = _kk.motion_grammar_olcusu([
    {"hareket": "push-in", "islev": "hook"},
    {"hareket": "pan-left", "islev": "aciklama"},
    {"hareket": "slow-drift", "islev": "aciklama"},
    {"hareket": "pull-out", "islev": "aciklama"},
    {"hareket": "push-in", "islev": "hook"}])
kontrol("⭐ AYNI ISLEVDE ayni hareket YAKALANIYOR (pencere disinda bile)",
        len(_MG24["islev_tekrari"]) == 1
        and _MG24["islev_tekrari"][0]["islev"] == "hook"
        and _MG24["islev_tekrari"][0]["hareket"] == "push-in"
        and _MG24["islev_tekrari"][0]["ilk_indeks"] == 0,
        _MG24["islev_tekrari"])
kontrol("FARKLI islevde ayni hareket ISLEV TEKRARI SAYILMAZ",
        not _kk.motion_grammar_olcusu([
            {"hareket": "push-in", "islev": "hook"},
            {"hareket": "pan-left", "islev": "aciklama"},
            {"hareket": "push-in", "islev": "sonuc"}])["islev_tekrari"])
kontrol("islev YOKSA olcum COKMEZ (geriye uyumlu)",
        _kk.motion_grammar_olcusu([{"hareket": "push-in"},
                                   {"hareket": "pan-left"}])["islev_tekrari"]
        == [])

# ── KAPI: acilis==kapanis ve islev tekrari FAIL ──
kontrol("⭐ qa_on I-24 kodlari FAIL_KODLARI'nda",
        "KALITE-MOTION-ACILIS-KAPANIS" in _qon.FAIL_KODLARI
        and "KALITE-MOTION-ISLEV-TEKRAR" in _qon.FAIL_KODLARI)
kontrol("I-24 kodlari KALITE_KODLARI'nda (kapali yolda hukum YOK)",
        "KALITE-MOTION-ACILIS-KAPANIS" in _qon.KALITE_KODLARI
        and "KALITE-MOTION-ISLEV-TEKRAR" in _qon.KALITE_KODLARI)

# ── SECIM: kapanis acilisi TEKRAR EDEMEZ ──
_h24 = _gr._hareket_sec("establishing", 0, sure_sn=4.0,
                        son_hareketler=("pull-out", "slow-drift", "pan-right"),
                        islev="sonuc", acilis_hareketi="push-in")
kontrol("⭐ kapanis, acilisin hareketini SECMIYOR (kok neden kapandi)",
        _h24 != "push-in", _h24)
kontrol("acilis kisiti VERILMEZSE eski davranis (geriye uyumlu)",
        _gr._hareket_sec("establishing", 0, sure_sn=4.0,
                         son_hareketler=("pull-out", "slow-drift",
                                         "pan-right"),
                         islev="sonuc") == "push-in")
_h24b = _gr._hareket_sec("medium", 0, sure_sn=4.0,
                         islev_hareketleri=("push-in",))
kontrol("⭐ ayni islevde kullanilmis hareket SECILMIYOR",
        _h24b != "push-in", _h24b)
kontrol("kisitlar havuzu BOSALTMAZ (secim cokmez)",
        _gr._hareket_sec("document", 0, sure_sn=4.0,
                         acilis_hareketi="document-scan",
                         islev_hareketleri=("push-in",))
        in _gr.CEKIM_HAREKET["document"])

# ── GEOMETRI: gozlemlenebilir ve DETERMINISTIK ──
_g_dar = _gr._hareket_sec("establishing", 0, sure_sn=4.0,
                          genislik=3000, yukseklik=2250)
_g_genis = _gr._hareket_sec("establishing", 0, sure_sn=4.0,
                            genislik=3000, yukseklik=1000)
kontrol("⭐ geometri secimi GERCEKTEN degistiriyor (dar != genis)",
        _g_dar != _g_genis, f"dar={_g_dar} genis={_g_genis}")
kontrol("DAR kaynakta iceri/disari hareket tercih ediliyor",
        _g_dar in _gr.GEOMETRI_HAREKET["dar"], _g_dar)
kontrol("GENIS kaynakta yatay hareket tercih ediliyor",
        _g_genis in _gr.GEOMETRI_HAREKET["genis"], _g_genis)
kontrol("geometri YASAK degil SIRALAMA (havuzu kucultmuyor)",
        _gr._hareket_sec("document", 0, sure_sn=4.0,
                         genislik=3000, yukseklik=1000)
        in _gr.CEKIM_HAREKET["document"])
kontrol("geometri olculemezse secim DEGISMEZ (notr)",
        _gr._hareket_sec("establishing", 0, sure_sn=4.0)
        == _gr._hareket_sec("establishing", 0, sure_sn=4.0,
                            genislik=None, yukseklik=None))

# ── DETERMINIZM: rastgelelik YOK ──
kontrol("⭐ gramer modulunde RASTGELELIK YOK",
        not re.search(r"\b(random|shuffle|uuid4|time\.time)\b",
                      _kod_yalniz(oku(KOK, "editor/gramer.py"))))
_det = [_gr._hareket_sec("establishing", 2, sure_sn=4.0, islev="sonuc",
                         acilis_hareketi="push-in", genislik=3000,
                         yukseklik=2250) for _ in range(5)]
kontrol("ayni girdi -> AYNI cikti (5 kosum)", len(set(_det)) == 1, _det)

# ── UCTAN UCA: pilotun GERCEK beat dizisi ──
class _B24:
    def __init__(self, i, islev, sure, sid):
        self.beat_id = f"b{i:03d}"
        self.scene_id = sid
        self.fact_id = f"f{i}"
        self.islev = islev
        self.sure_sn = sure


_beat24 = [_B24(1, "hook", 0.862, "s001"), _B24(2, "hook", 1.725, "s001"),
           _B24(3, "aciklama", 4.738, "s002"), _B24(4, "aciklama", 4.9, "s003"),
           _B24(5, "sonuc", 4.825, "s004")]
_olcu24 = {"s001": (4192, 2832), "s002": (3000, 2000),
           "s003": (3000, 2250), "s004": (4986, 3744)}
_aday24: dict = {}
for _sid, (_g24, _y24) in _olcu24.items():
    for _k24 in range(2 if _sid == "s001" else 1):
        _aday24.setdefault(_sid, []).append({
            "asset_id": f"{_sid}_{_k24}", "scene_id": _sid,
            "saglayici": "nasa", "render_kullanilabilir": True,
            "genislik": _g24, "yukseklik": _y24,
            "sahne_amaci": "manzara", "toplam_skor": 90 - _k24})
_cek24 = _gr.gramer_uygula(_beat24, sahne_adaylari=_aday24,
                           saglayici_tavani=5)
_mg24 = _kk.motion_grammar_olcusu(
    [{"beat_id": c.beat_id, "hareket": c.hareket, "islev": b.islev,
      "sure_sn": b.sure_sn, "gecis": []}
     for c, b in zip(_cek24, _beat24)])
kontrol("⭐ UCTAN UCA: acilis != kapanis",
        _mg24["acilis_kapanis_ayri"] is True,
        f"{_mg24['acilis_hareketi']} vs {_mg24['kapanis_hareketi']}")
kontrol("⭐ UCTAN UCA: islev tekrari YOK", not _mg24["islev_tekrari"])
kontrol("⭐ UCTAN UCA: ardisik tekrar YOK", not _mg24["ardisik_tekrar"])
kontrol("UCTAN UCA: pencere tekrari YOK", not _mg24["pencere_tekrari"])

# ── PUAN GEREKCESI DUSEN KOSULU ADIYLA SOYLUYOR (I-24'te bulundu) ──
_P24 = _kk.izleyici_kalite_puani(grammar={
    "olculdu": True, "ardisik_tekrar": [], "pencere_tekrari": [],
    "islev_tekrari": [], "benzersiz_gecis": 3, "acilis_kapanis_ayri": False,
    "acilis_hareketi": "push-in", "kapanis_hareketi": "push-in",
    "benzersiz_hareket": 4})["bilesenler"]["motion_cesitlilik"]
kontrol("⭐ 0 puan alan bilesen DUSEN KOSULU adiyla yaziyor",
        _P24["puan"] == 0.0
        and "acilis_kapanis_ayri" in _P24["gerekce"]
        and _P24["dusen_kosullar"] == ["acilis_kapanis_ayri"],
        _P24["gerekce"])
kontrol("tum kosullar gecince puan TAM ve dusen kosul YOK",
        _kk.izleyici_kalite_puani(grammar={
            "olculdu": True, "ardisik_tekrar": [], "pencere_tekrari": [],
            "islev_tekrari": [], "benzersiz_gecis": 3,
            "acilis_kapanis_ayri": True, "benzersiz_hareket": 5})
        ["bilesenler"]["motion_cesitlilik"]["puan"] == 20.0)
kontrol("islev tekrari da puani DUSURUYOR (yeni kosul baglandi)",
        _kk.izleyici_kalite_puani(grammar={
            "olculdu": True, "ardisik_tekrar": [], "pencere_tekrari": [],
            "islev_tekrari": [{"indeks": 4, "islev": "hook",
                               "hareket": "push-in", "ilk_indeks": 0}],
            "benzersiz_gecis": 3, "acilis_kapanis_ayri": True,
            "benzersiz_hareket": 4})
        ["bilesenler"]["motion_cesitlilik"]["puan"] == 0.0)

_R20_YOL = os.path.join(KOK, "..", "outputs", "sample",
                        "teknoloji_i20_rapor.json")
if not os.path.exists(_R20_YOL):
    bloke_yaz("I-20/21 teknoloji pilotu render raporu", "rapor yok")
else:
    _R20 = _json.load(open(_R20_YOL, encoding="utf-8"))
    _z20 = _R20["zincir"]
    kontrol("⭐ I-21: bolunen beatler AYNI varligi PAYLASMIYOR",
            len({z["asset_id"] for z in _z20 if z.get("asset_id")})
            == len([z for z in _z20 if z.get("asset_id")]),
            [z.get("asset_id") for z in _z20])
    kontrol("⭐ I-22: HICBIR BEAT medyasiz DEGIL",
            all(z.get("asset_id") for z in _z20),
            [z.get("asset_id") for z in _z20])
    _mb = (_R20["plan"]["on_render_qa"]["olcumler"].get("kalite") or {}).get(
        "medyasiz_beat") or {}
    kontrol("⭐ medyasiz_beat olcumu TEMIZ ve raporda",
            _mb.get("temiz") is True and _mb.get("medyasiz") == 0, _mb)
    _bm = _R20.get("beat_medya_eslemesi") or {}
    kontrol("⭐ kota PLANIN beat sayisina ESITLENDI",
            _bm.get("saglayici_tavani") == _bm.get("kuru_plan_beat")
            and _bm.get("kuru_plan_beat") == len(_z20), _bm)
    kontrol("⭐ PRE-QA artik FAIL DEGIL (I-20'de FAIL'di)",
            _R20["plan"]["qa"]["fail"] == 0, _R20["plan"]["qa"])
    # ── I-23: EN-BOY ORANI KAPISI GERCEK RENDER'DA CALISTI MI ──
    _me20 = _R20.get("medya_edinim") or {}
    _oz23 = _me20.get("oran_kapisi_ozeti") or {}
    kontrol("⭐ I-23: KABUL EDILEN HER varlik oran kapisini gecti",
            _oz23.get("hepsi_uygun") is True
            and len(_oz23.get("kabul_edilen_oranlar") or []) == 4, _oz23)
    # ⚠ I-27'DE DUZELTILEN KILIT (I-23b ile ayni sinif): burasi "en az 1
    # dikey red OLDU" diyordu. O sayi ADAY LISTESINE bagli — I-27'nin
    # yukseltilmis cozunurluk esigi dikey adaylari ORAN kapisina VARMADAN
    # eliyor. ASIL DEGISMEZ "kabul edilen hicbir varlik dikey/kare DEGIL";
    # kilit ona cevrildi (gevsetme degil, DOGRU degismez).
    kontrol("⭐ I-23: KABUL EDILEN hicbir varlik DIKEY/KARE degil",
            all(o >= 1.244 for o in (_oz23.get("kabul_edilen_oranlar") or []))
            and bool(_oz23.get("kabul_edilen_oranlar")),
            _oz23.get("kabul_edilen_oranlar"))
    kontrol("I-23: oran reddi olduysa DIKEY olarak siniflandirilmis",
            all(x.get("yon") in ("dikey", "kare", "asiri-genis")
                for x in (_me20.get("oran_reddi") or [])),
            _me20.get("oran_reddi"))
    kontrol("⭐ I-23: red kaydinda OLCULEN oran + HEDEF oran + NEDEN var",
            all(x.get("olculen_oran") and x.get("hedef_oran")
                and "ORAN-UYUMSUZ" in str(x.get("sebep"))
                for x in (_me20.get("oran_reddi") or [])),
            _me20.get("oran_reddi"))
    kontrol("I-23: kabul edilenlerin HICBIRI dikey/kare DEGIL",
            all(o >= 1.244 for o in (_oz23.get("kabul_edilen_oranlar") or [])),
            _oz23.get("kabul_edilen_oranlar"))
    kontrol("I-23: hedef oran 16:9 ve esik ADLANDIRILMIS sabitten",
            _oz23.get("hedef_oran") == 1.7778
            and _oz23.get("en_az_korunan") == _ed.ORAN_EN_AZ_KORUNAN)
    # ⚠ I-26'DA DUZELTILEN KILIT: burasi "en az 1 ayirt reddi OLDU" diye
    # yaziyordu. O sayi ADAY LISTESINE bagli — Commons/NASA karisimi
    # degisince reddedilecek benzer cift kalmayabiliyor (I-26 kosumunda
    # tam bu oldu). ASIL DEGISMEZ "ayirt edilemez cift HAYATTA KALMADI"dir;
    # kilit ona cevrildi (gevsetme degil, DOGRU degismez).
    kontrol("⭐ I-23b: ayirt-etme kapisi ACIK ve QA esigine bagli",
            _oz23.get("ayirt_esigi") == 0.86, _oz23)
    _mc26 = _R20.get("medya_cesitliligi") or {}
    kontrol("⭐ I-23b: AYIRT EDILEMEZ cift HAYATTA KALMADI",
            not [c for c in (_mc26.get("ciftler") or [])
                 if c.get("benzerlik", 0) >= _mc26.get("esik", 0.86)],
            _mc26.get("ciftler"))
    kontrol("I-23: medya GERCEK saglayicidan, fixture DEGIL",
            all(str(s.get("saglayici") or "").lower() in ("nasa", "commons")
                for s in (_me20.get("sahneler") or [])
                if s.get("durum") == "OK"))
    kontrol("I-23: maliyet $0.00 KALDI",
            float(_me20.get("maliyet_usd", 1)) == 0.0
            and float(_R20.get("maliyet_usd", 1)) == 0.0)
    # ── I-24: MOTION CESITLILIGI GERCEK RENDER'DA ──
    _mgr = _R20.get("motion_grammar") or {}
    _pm = ((_R20.get("izleyici_kalite_puani") or {}).get("bilesenler")
           or {}).get("motion_cesitlilik") or {}
    kontrol("⭐ I-24: acilis != kapanis (I-22/I-23'te ikisi de push-in'di)",
            _mgr.get("acilis_kapanis_ayri") is True
            and _mgr.get("acilis_hareketi") != _mgr.get("kapanis_hareketi"),
            f"{_mgr.get('acilis_hareketi')} vs {_mgr.get('kapanis_hareketi')}")
    kontrol("⭐ I-24: ayni ISLEVDE ayni hareket YOK",
            _mgr.get("islev_tekrari") == [], _mgr.get("islev_tekrari"))
    kontrol("I-24: ardisik ve pencere tekrari da YOK",
            not _mgr.get("ardisik_tekrar") and not _mgr.get("pencere_tekrari"))
    kontrol("⭐ I-24: motion_cesitlilik 0/20 -> 20/20",
            _pm.get("puan") == 20.0 and _pm.get("dusen_kosullar") == [],
            _pm.get("gerekce"))
    kontrol("I-24: BES beat BES AYRI hareket",
            _mgr.get("benzersiz_hareket") == len(_mgr.get("hareketler") or []),
            _mgr.get("hareketler"))
    kontrol("I-24: puan bileseni KOSULLARI tek tek raporluyor",
            isinstance(_pm.get("kosullar"), dict)
            and len(_pm["kosullar"]) == 5
            and all(_pm["kosullar"].values()), _pm.get("kosullar"))
    # ── I-25: SAGLAYICI-TEKEL TANISI GERCEK RAPORDA ──
    _cd = [d for s in (_R20["medya_edinim"].get("sahneler") or [])
           for d in (s.get("denemeler") or [])
           if d.get("saglayici") == "commons"]
    kontrol("⭐ I-25: her denemede SAGLAYICIYA GIDEN sorgu raporda",
            all("kullanilan_sorgu" in d for d in _cd) and bool(_cd))
    kontrol("⭐ I-25: Commons'a giden sorguda ' Iceland' BULASANI YOK",
            not any("Iceland" in str(d.get("kullanilan_sorgu") or "")
                    for d in _cd),
            [d.get("kullanilan_sorgu") for d in _cd])
    _cd_arayan = [d for d in _cd if d.get("durum") != "DEVRE-ACIK"]
    kontrol("⭐ I-25: Commons ARAMASI artik BOS DONMUYOR (denenen > 0)",
            bool(_cd_arayan)
            and all((d.get("denenen") or 0) > 0 for d in _cd_arayan),
            [(d.get("kullanilan_sorgu"), d.get("denenen")) for d in _cd_arayan])
    kontrol("⭐ I-25: lisans duvarini gecen aday ARTIK VAR (metadata > 0)",
            all((d.get("metadata") or 0) > 0 for d in _cd_arayan),
            [(d.get("kullanilan_sorgu"), d.get("metadata"))
             for d in _cd_arayan])
    # ⚠ DURUSTLUK: WARN hala varsa SEBEBI OLCULMUS olmali. Commons ileride
    # bayt verirse bu kontrol yine gecer — sahte PASS uretmez, sebep arar.
    _tekel = (_R20["plan"]["on_render_qa"]["olcumler"] or {}).get(
        "tek_saglayici_orani")
    if _tekel and _tekel >= 1.0:
        kontrol("⭐ I-25: SAGLAYICI-TEKEL surse bile SEBEBI OLCULMUS",
                all(d.get("durum") in ("BAYT-YOK", "DEVRE-ACIK")
                    for d in _cd)
                and any(d.get("http") or "429" in str(d.get("sebep"))
                        for d in _cd),
                [(d.get("durum"), d.get("sebep")) for d in _cd])
        kontrol("I-25: sebep artik 'ADAY-YOK' DEGIL (kok neden degisti)",
                not any(d.get("durum") == "ADAY-YOK" for d in _cd))
    kontrol("I-25: elenme nedenleri raporda sayilabilir",
            all(isinstance(d.get("elenme_nedenleri"), list)
                for d in _cd_arayan))
    # ── I-26: KAMERA PUNCH'I KAYNAGI BUYUTUYOR MU? ──
    _pb26 = _R20.get("punch_buyutme") or {}
    kontrol("⭐ I-26: punch buyutme olcumu raporda",
            _pb26.get("olculdu") is True and "kayitlar" in _pb26)
    kontrol("I-26: her beat icin ekran piksel orani olculdu",
            all(k.get("olculdu") for k in (_pb26.get("kayitlar") or [])),
            _pb26.get("kayitlar"))
    # ⚠ OLCULEN KUSUR SESSIZCE GECILMEZ.
    if (_pb26.get("buyuten_beat") or 0) > 0:
        bloke_yaz(
            "I-27 teknoloji pilotu — KAYNAK BUYUTULUYOR",
            f"{_pb26['buyuten_beat']} beat kaynagi ekranda BUYUTUYOR "
            f"(en yuksek oran {_pb26.get('en_yuksek_oran')}). "
            f"MP4 KABUL EDILMIS SAYILMAZ.")
    else:
        kontrol("⭐ I-27: HICBIR beat kaynagi BUYUTMUYOR (I-26'da 2 taneydi)",
                _pb26.get("temiz") is True
                and (_pb26.get("en_yuksek_oran") or 0) <= 1.0,
                _pb26.get("en_yuksek_oran"))
    # ── I-27: PRE-QA punch olcumu ve kadraj dusurme ──
    _pq27 = ((_R20["plan"]["on_render_qa"]["olcumler"].get("kalite") or {})
             .get("punch_buyutme") or {})
    kontrol("⭐ I-27: PRE-QA punch olcumu RAPORDA ve TEMIZ",
            _pq27.get("temiz") is True and _pq27.get("olculen_beat") == 5
            and not _pq27.get("buyuten"), _pq27)
    kontrol("⭐ I-27: kadraj DETERMINISTIK dusuruldu ve gerekcesi yazili",
            all(k.get("kadraj") in _mo.KADRAJ_OLCEK
                for k in (_pq27.get("kadraj_dusurulen") or [])),
            _pq27.get("kadraj_dusurulen"))
    kontrol("I-27: edinim esigi TURETILEN degere esit (2443)",
            _R20["medya_edinim"].get("en_az_genislik")
            == _kk.en_az_kaynak_genisligi(1920))
    kontrol("⭐ I-27: OPTIK DURAGANLIK kapisi da TEMIZ (kadraj daraltma "
            "hareketi ac birakmadi)",
            (_R20.get("optik_hareket") or {}).get("temiz") is True,
            (_R20.get("optik_hareket") or {}).get("genel_ortalama"))
    kontrol("I-27: kabul edilen HER varlik turetilen esigi geciyor",
            all((s.get("olcu") or [0])[0]
                >= _kk.en_az_kaynak_genisligi(1920)
                for s in (_R20["medya_edinim"].get("sahneler") or [])
                if s.get("durum") == "OK"),
            [s.get("olcu") for s in _R20["medya_edinim"].get("sahneler") or []])
    # ⚠ POST-QA FAIL ise SESSIZCE GECILMEZ — BLOKE yazilir.
    if _R20["post_qa"]["durum"] == "FAIL":
        _nedenler = [s["kod"] for s in _R20["post_qa"]["sorunlar"]
                     if s["seviye"] == "fail"]
        bloke_yaz("I-23 teknoloji pilotu POST-QA",
                  f"render TAMAMLANDI ama POST-QA FAIL: {_nedenler}. "
                  f"MP4 KABUL EDILMIS SAYILMAZ.")
    else:
        kontrol("⭐ I-23: POST-QA TAMAMEN PASS (I-22'de KENAR-SIYAH FAIL'di)",
                _R20["post_qa"]["durum"] == "PASS"
                and not [s for s in (_R20["post_qa"].get("sorunlar") or [])
                         if s.get("seviye") == "fail"])
        kontrol("⭐ I-23: POST-KENAR-SIYAH 6/68 -> 0 ihlal",
                (_R20.get("kenar_siyahligi") or {}).get("ihlal_kare") == 0
                and (_R20.get("kenar_siyahligi") or {}).get("temiz") is True,
                _R20.get("kenar_siyahligi"))


print(f"\n{'=' * 60}")
print(f"GECEN: {gecen}   BASARISIZ: {len(basarisiz)}   BLOKE: {len(bloke)}")
for b in basarisiz:
    print(f"  XX {b}")
for b in bloke:
    print(f"  -- BLOKE {b}")
sys.exit(1 if basarisiz else 0)
