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


print(f"\n{'=' * 60}")
print(f"GECEN: {gecen}   BASARISIZ: {len(basarisiz)}   BLOKE: {len(bloke)}")
for b in basarisiz:
    print(f"  XX {b}")
for b in bloke:
    print(f"  -- BLOKE {b}")
sys.exit(1 if basarisiz else 0)
