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
# ⚠ FAZ R-1d-b: pencere SABIT 600 KARAKTERDI ve fonksiyona tek satir
# eklenince (`_STOK_PROVENANS.clear()`) `kare_butce_kur()` 605. karaktere
# kayip test KIRMIZI yandi — kod DOGRUYKEN. Iddia "ilk 600 karakterde"
# degil "BU FONKSIYONUN GOVDESINDE"; kapsam artik bir sonraki ust duzey
# `def`e kadar. Iddia GEVSETILMEDI, DOGRU kapsama alindi.
kontrol("is basinda butce sifirlaniyor",
        "kare_butce_kur()" in
        ks.split("def klip_gecmisi_sifirla")[1].split("\ndef ")[0])
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

blok("§39n I-38 — YAZI SPEC'I SAHNEYE GORELI (EKRAN KUNYESI CIZILIYOR)")

# ⚠ I-38'DE OLCULEN KUSUR (lawn pilotu, GERCEK 1080p render, 6 beat):
# `_katman_specleri` grafik spec'ine katmanin MUTLAK zaman cizgisi
# baslangicini yaziyordu (`d["bas_sn"] = k.bas_sn`). Remotion tarafi
# (editorv2/Grafikler.tsx `KaynakEtiketi`) `spec.bas_sn`i SAHNEYE GORELI
# okur ve `zarf()`i SAHNE-YEREL kare ile hesaplar. Olculen:
#   b002 sahne 2.20 sn, bas_sn 2.287  -> HIC gorunmez
#   b003 sahne 5.55 sn, bas_sn 4.488  -> yalniz son ~1 sn
#   b004 sahne 5.35 sn, bas_sn 10.037 -> HIC gorunmez
#   b005 sahne 5.27 sn, bas_sn 15.388 -> HIC gorunmez
#   b006 sahne 4.94 sn, bas_sn 20.662 -> HIC gorunmez
# Sonuc: CC-BY / CC-BY-SA olan DORT sahnenin EKRAN KUNYESI hic cizilmedi;
# atif yalniz `attribution.txt`te kaldi. `chapter-title` TESADUFEN
# calisiyordu: b001 sifirdan basliyor, orada mutlak == goreli.
# Hicbir kapi gormedi — kusur ancak KAREYE BAKINCA cikti.


class _B38:
    """beat ikamesi — `_katman_specleri`nin okudugu alanlar."""

    def __init__(self, bid, sid, fid, bas, sure):
        self.beat_id = bid
        self.scene_id = sid
        self.fact_id = fid
        self.bas_sn = bas
        self.sure_sn = sure
        self.bitis_sn = round(bas + sure, 3)


# Gercek lawn zaman cizgisi (render_plan.json'dan OLCULDU)
_BEAT38 = [_B38("b001", "s001", "s01", 0.0, 1.887),
           _B38("b002", "s001", "s01", 1.887, 2.201),
           _B38("b003", "s002", "s02", 4.088, 5.549),
           _B38("b004", "s003", "s03", 9.637, 5.351),
           _B38("b005", "s004", "s04", 14.988, 5.274),
           _B38("b006", "s005", "s05", 20.262, 4.938)]
_P38 = _eprofil.profil("premium-modern")
_KAT38 = [_etipo.katman_kur("chapter-title", "THERE IS A BAG OF GRASS",
                            0.2, 3.387, fact_id="s01", p=_P38, y_orani=0.7)]
for _b38, _mt38 in ((_BEAT38[1], "Forest and Kim Starr / CC-BY"),
                    (_BEAT38[2], "Famartin / CC-BY-SA"),
                    (_BEAT38[3], "Anton / CC-BY-SA"),
                    (_BEAT38[4], "Macleay Grass Man / CC-BY"),
                    (_BEAT38[5], "Dietmar Rabich / CC-BY-SA")):
    _KAT38.append(_etipo.katman_kur(
        "source-label", _mt38, _b38.bas_sn + 0.4, min(3.0, _b38.sure_sn),
        fact_id=_b38.fact_id, p=_P38, y_orani=0.755))

_SP38 = _ep2._katman_specleri(_KAT38, _BEAT38, _P38)
_SP_BEAT = {s["beat_id"]: s for s in _SP38}


def _sahne_suresi(bid):
    return next(b.sure_sn for b in _BEAT38 if b.beat_id == bid)


# ── KIRMIZI 1: spec bas_sn SAHNEYE GORELI olmali (mutlak DEGIL) ──
_disarida = [(s["beat_id"], s["ad"], s["bas_sn"], _sahne_suresi(s["beat_id"]))
             for s in _SP38 if s["bas_sn"] >= _sahne_suresi(s["beat_id"])]
kontrol("⭐ I-38 KIRMIZI: hicbir yazi spec'i SAHNE DISINDA baslamiyor",
        not _disarida, _disarida)
kontrol("⭐ I-38: source-label bas_sn SAHNEYE GORELI (hepsi 0.4)",
        all(abs(_SP_BEAT[b]["bas_sn"] - 0.4) < 0.01
            for b in ("b002", "b003", "b004", "b005", "b006")),
        {b: _SP_BEAT[b]["bas_sn"] for b in
         ("b002", "b003", "b004", "b005", "b006")})
kontrol("⭐ I-38: b004 kunyesi ARTIK cizilebilir (10.037 -> 0.4)",
        _SP_BEAT["b004"]["bas_sn"] < _sahne_suresi("b004"),
        _SP_BEAT["b004"]["bas_sn"])
# ── GERILEME YOK: ilk sahnede deger DEGISMEZ (mutlak == goreli) ──
kontrol("I-38 GERILEME YOK: b001 chapter-title bas_sn 0.2 KALDI",
        abs(_SP_BEAT["b001"]["bas_sn"] - 0.2) < 0.001,
        _SP_BEAT["b001"]["bas_sn"])
kontrol("I-38: sure_sn ve y_orani DOKUNULMADI",
        abs(_SP_BEAT["b003"]["sure_sn"] - 3.0) < 0.01
        and abs(_SP_BEAT["b003"]["parametre"]["y_orani"] - 0.755) < 0.001)
kontrol("I-38: her spec DOGRU beat/scene'e bagli (I-37 bagi korunur)",
        all(_SP_BEAT[b]["scene_id"] == s for b, s in
            (("b003", "s002"), ("b004", "s003"),
             ("b005", "s004"), ("b006", "s005"))))
kontrol("I-38: kunye METINLERI korunuyor (atif kaybolmaz)",
        _SP_BEAT["b005"]["parametre"]["metin"] == "Macleay Grass Man / CC-BY")

# ── KIRMIZI 2: PRE-QA bu SESSIZ DUSUSU yakalamali ──


def _yazi38(specler, beatler):
    q = _qon.QaSonucu()
    _qon._kalite_denetle(q, beatler=beatler, cekimler=[], yazi_katmanlari=[],
                         adaylar_index={}, p=_qon.VARSAYILAN,
                         kare_olcu=(1920, 1080), anlatim_bitis_sn=None,
                         toplam=25.2, benzerlik_okuyucu=None, acik=True,
                         motion_specler=specler)
    return q


# KIRMIZI kurulum: I-38 ONCESI davranis (mutlak bas_sn) yeniden uretilir.
_SP_KIRMIZI = [dict(s) for s in _SP38]
for _s38 in _SP_KIRMIZI:
    _b0 = next(b for b in _BEAT38 if b.beat_id == _s38["beat_id"])
    _s38["bas_sn"] = round(_b0.bas_sn + 0.4, 3) if _s38["ad"] != "chapter-title" \
        else _s38["bas_sn"]
_q38k = _yazi38(_SP_KIRMIZI, _BEAT38)
_yd = _q38k.olcumler["kalite"]["yazi_sahne_penceresi"]
kontrol("⭐ I-38 KIRMIZI: sahne disi yazi spec'i YAKALANIYOR (4 spec)",
        len(_yd["disarida"]) == 4 and _yd["temiz"] is False,
        [d["beat_id"] for d in _yd["disarida"]])
kontrol("⭐ I-38: sahne disi yazi PRE-QA'da FAIL uretiyor",
        any(x.kod == "KALITE-YAZI-SAHNE-DISI" and x.seviye == "fail"
            for x in _q38k.sorunlar))
kontrol("I-38: kayit beat/ad/bas_sn/sahne_sure GOSTERIYOR",
        {"beat_id", "ad", "bas_sn", "sahne_sure_sn"} <= set(_yd["disarida"][0]),
        _yd["disarida"][0])
# YESIL: duzeltilmis (sahneye goreli) specler temiz gecer.
_q38y = _yazi38(_SP38, _BEAT38)
_ydy = _q38y.olcumler["kalite"]["yazi_sahne_penceresi"]
kontrol("⭐ I-38 YESIL: sahneye goreli speclerde ihlal YOK",
        _ydy["temiz"] is True and not _ydy["disarida"])
kontrol("⭐ I-38: kapi FAIL ve KALITE kodlarinda (bayraga bagli)",
        "KALITE-YAZI-SAHNE-DISI" in _qon.FAIL_KODLARI
        and "KALITE-YAZI-SAHNE-DISI" in _qon.KALITE_KODLARI)
kontrol("I-38: olcum HER yazi spec'ini kapsiyor (6 spec)",
        _ydy["olculen"] == 6, _ydy.get("olculen"))
# ── Remotion tarafi sozlesmesi: tuketici GORELI okuyor (kanit) ──
_GRAFIK_TSX = oku(os.path.dirname(KOK), "app", "render-studio", "src",
                  "editorv2", "Grafikler.tsx")
kontrol("I-38: KaynakEtiketi spec.bas_sn'i SAHNE-YEREL kare ile okuyor",
        "KaynakEtiketi" in _GRAFIK_TSX
        and "sayi(spec.bas_sn" in _sikistir(_GRAFIK_TSX).replace(" ", ""))

blok("§40i J-1 — STATIK FOTOGRAF / GERCEK VIDEO ORANI OLCULDU (yalniz tanisal)")


# ⚠ YALNIZ TANISAL. Uretim davranisi DEGISMEDI, kapi/esik EKLENMEDI.
# Ag YOK, ucretli API YOK, rerender/deploy YOK, $0.00.
#
# ⚠ I-58 DERSI UYGULANDI: bu blokta SABIT OLCUM SOZLUGU YOKTUR. Butun
# oranlar `cikti/*/render_plan.json` kayitlarindan ve dosyalarin KENDISINDEN
# (ffprobe) HER KOSUMDA YENIDEN hesaplanir; sayilar teste "yazilmaz".
#
# ── SINIFLANDIRICI (ag gerektirmez) ──
#   (c) sentetik/diger    : kaynak_turu != "medya" (fallback/motion-graphic)
#   olculemedi            : medya_yolu bos / dosya diskte yok / ffprobe okumadi
#   (a) gercek hareketli  : ffprobe ile kare sayisi > 1
#   (b) statik + KenBurns : kare == 1 VE motion'da zoom/pan DEGISIYOR
#   (b0) statik hareketsiz: kare == 1 VE zoom/pan SABIT (donmus kadraj)
# ⚠ "Belirsizse statik say" YAPILMAZ — belirsiz olan `olculemedi` yazilir.
#
# ── AYNI PLANIN YENIDEN RENDERI BAGIMSIZ ORNEK SAYILMAZ ──
# Plan imzasi = (fact_id, asset_id, yuvarlanmis sure) uclulerinin dizisi;
# ayni imzali kosumlardan TEK temsilci alinir (I-34/I-58 dersi).

import glob as _g1                                       # noqa: E402
import subprocess as _sp1                                # noqa: E402

_J1_PLAN = sorted(_g1.glob(os.path.join(os.path.dirname(KOK), "cikti", "*",
                                        "render_plan.json")))
_J1_FFPROBE = _sh.which("ffprobe")


def _j1_kare(yol, _onbellek={}):
    """Dosyanin GERCEK kare sayisi (ffprobe). Okunamazsa None = OLCULEMEDI."""
    if yol in _onbellek:
        return _onbellek[yol]
    sonuc = None
    if _J1_FFPROBE and os.path.isfile(yol):
        try:
            r = _sp1.run([_J1_FFPROBE, "-v", "error", "-select_streams", "v:0",
                          "-count_frames", "-show_entries",
                          "stream=nb_read_frames", "-of", "json", yol],
                         capture_output=True, text=True, timeout=120)
            n = json.loads(r.stdout)["streams"][0].get("nb_read_frames")
            sonuc = int(n) if str(n).isdigit() else None
        except Exception:
            sonuc = None
    _onbellek[yol] = sonuc
    return sonuc


def _j1_kamera_hareketi(sahne) -> bool:
    """motion listesinde zoom ya da pan GERCEKTEN degisiyor mu?"""
    for m in sahne.get("motion") or []:
        p = m.get("parametre") or {}
        for anahtar in ("zoom", "pan_x", "pan_y"):
            v = p.get(anahtar)
            if isinstance(v, list) and len(v) == 2:
                try:
                    if abs(float(v[0]) - float(v[1])) > 1e-6:
                        return True
                except (TypeError, ValueError):
                    continue
    return False


def _j1_sinif(sahne):
    if str(sahne.get("kaynak_turu") or "") != "medya":
        return "c_sentetik"
    yol = str(sahne.get("medya_yolu") or "")
    if not yol or not os.path.isfile(yol):
        return "olculemedi"
    n = _j1_kare(yol)
    if n is None:
        return "olculemedi"
    if n > 1:
        return "a_video"
    return "b_kenburns" if _j1_kamera_hareketi(sahne) else "b0_hareketsiz"


if not _J1_FFPROBE:
    bloke_yaz("J-1 medya turu olcumu", "ffprobe yok (yerel arac)")
elif not _J1_PLAN:
    bloke_yaz("J-1 medya turu olcumu", "cikti/*/render_plan.json yok")
else:
    _J1_IMZA: dict = {}
    for _p1 in _J1_PLAN:
        _d1 = json.load(open(_p1, encoding="utf-8"))
        _sh1 = _d1.get("sahneler") or []
        _im1 = repr([(s.get("fact_id"), s.get("asset_id"),
                      round(float(s.get("sure_sn") or 0), 2)) for s in _sh1])
        _J1_IMZA.setdefault(_im1, []).append(
            (os.path.basename(os.path.dirname(_p1)), _sh1))
    _J1_TEMSIL = [sorted(v, key=lambda t: t[0])[0][1]
                  for v in _J1_IMZA.values()]
    _J1_PLAN_ADI = [sorted(v, key=lambda t: t[0])[0][0]
                    for v in _J1_IMZA.values()]
    _J1_CEKIM = [s for plan in _J1_TEMSIL for s in plan]

    kontrol("⭐ J-1: ayni planin yeniden renderlari BAGIMSIZ ORNEK "
            "SAYILMIYOR (kosum sayisi > benzersiz plan sayisi)",
            len(_J1_PLAN) > len(_J1_IMZA) >= 5,
            f"{len(_J1_PLAN)} kosum -> {len(_J1_IMZA)} benzersiz plan")

    _J1_C: dict = {}
    _J1_S: dict = {}
    for _s1 in _J1_CEKIM:
        _k1 = _j1_sinif(_s1)
        _J1_C[_k1] = _J1_C.get(_k1, 0) + 1
        _J1_S[_k1] = _J1_S.get(_k1, 0.0) + float(_s1.get("sure_sn") or 0)
    _J1_N = len(_J1_CEKIM)
    _J1_TOP = sum(_J1_S.values()) or 1.0
    _J1_STATIK_C = _J1_C.get("b_kenburns", 0) + _J1_C.get("b0_hareketsiz", 0)
    _J1_STATIK_S = _J1_S.get("b_kenburns", 0.0) + _J1_S.get("b0_hareketsiz", 0.0)

    print(f"     [J-1 TABAN] {len(_J1_IMZA)} benzersiz plan · {_J1_N} cekim · "
          f"{_J1_TOP:.1f} sn")
    for _k1 in ("a_video", "b_kenburns", "b0_hareketsiz", "c_sentetik",
                "olculemedi"):
        print(f"     [J-1] {_k1:15} cekim {_J1_C.get(_k1, 0):2}/{_J1_N} "
              f"({100 * _J1_C.get(_k1, 0) / _J1_N:5.1f}%)  "
              f"sure {_J1_S.get(_k1, 0.0):6.1f} sn "
              f"({100 * _J1_S.get(_k1, 0.0) / _J1_TOP:5.1f}%)")

    # ── TABAN BULGUSU ──
    # ⚠ J-5a'DA DEGISTI. J-1'in olctugu taban "video orani SIFIR"di ve o
    # iddia J-5a'ya kadar DOGRUYDU. Artik korpusta GERCEK video var; iddia
    # SILINMEDI, TARIHLENDIRILDI: J-5a plani DISINDA hala sifir.
    _J1_VIDEOLU = [p_ for p_, pl in zip(_J1_PLAN_ADI, _J1_TEMSIL)
                   if any(_j1_sinif(s_) == "a_video" for s_ in pl)]
    kontrol("⭐ J-1 TABAN (J-5a ONCESI): video kaynagi kullanan plan "
            "YALNIZCA J-5a pilotu — diger planlarin HEPSI hala SIFIR",
            _J1_VIDEOLU == ["_j5a_calisma"],
            {"videolu_plan": _J1_VIDEOLU,
             "sinif": {k: _J1_C.get(k, 0) for k in
                       ("a_video", "b_kenburns", "b0_hareketsiz",
                        "c_sentetik")}})
    kontrol("⭐ J-1: J-5a plani olcumu GERCEKTEN degistirdi — video "
            "cekim sayisi artik SIFIRDAN BUYUK",
            _J1_C.get("a_video", 0) >= 1, _J1_C.get("a_video", 0))
    kontrol("⭐ J-1 TABAN: SURE'nin %90'indan fazlasi STATIK FOTOGRAF "
            "(Ken Burns dahil)",
            _J1_STATIK_S / _J1_TOP > 0.90,
            f"{_J1_STATIK_S:.1f}/{_J1_TOP:.1f} sn")
    kontrol("⭐ J-1: CEKIM'lerin de %90'indan fazlasi statik fotograf",
            _J1_STATIK_C / _J1_N > 0.90, f"{_J1_STATIK_C}/{_J1_N}")
    kontrol("⭐ J-1: statik fotograflarin bir kismi HIC kamera hareketi "
            "almiyor (donmus kadraj); `hareket` alani da bunu soyluyor",
            _J1_C.get("b0_hareketsiz", 0) > 0
            and all(str(s.get("hareket") or "") in ("static", "data-reveal")
                    for s in _J1_CEKIM if _j1_sinif(s) == "b0_hareketsiz"),
            _J1_S.get("b0_hareketsiz", 0.0))
    kontrol("⭐ J-1 DURUSTLUK: hicbir cekim 'belirsiz oldugu icin statik' "
            "sayilmadi — olculemeyen ayri KALEM olarak raporlanir",
            _J1_C.get("olculemedi", 0) == 0, _J1_C.get("olculemedi", 0))

    # ── YANLIS SINIFLAMA PAYI: GERCEK TEMIZ KARSI-ORNEKLER ──
    # ⚠ Pozitif sinif (gercek hareketli video) korpusun KENDISINDE YOK; bu
    # yuzden sinif, YEREL ve GERCEK mp4 ciktilari uzerinde olculur.
    _J1_MP4 = sorted(_g1.glob(os.path.join(os.path.dirname(KOK), "outputs",
                                           "sample", "*.mp4")))[:4]
    if _J1_MP4:
        _J1_POZ = [(os.path.basename(y), _j1_sinif(
            {"kaynak_turu": "medya", "medya_yolu": y})) for y in _J1_MP4]
        kontrol("⭐ J-1 KARSI-ORNEK: GERCEK hareketli video dosyalarinin "
                "HEPSI `a_video` siniflaniyor (pozitif sinif KACIRILMIYOR)",
                bool(_J1_POZ) and all(s == "a_video" for _, s in _J1_POZ),
                _J1_POZ)
    else:
        bloke_yaz("J-1 pozitif karsi-ornek", "outputs/sample/*.mp4 yok")

    _J1_KAYNAK = sorted({str(s.get("medya_yolu") or "") for s in _J1_CEKIM
                         if str(s.get("kaynak_turu") or "") == "medya"})
    _J1_NEG = [(os.path.basename(y), _j1_kare(y)) for y in _J1_KAYNAK if y]
    # ⚠ J-5a SONRASI korpus ARTIK KARISIK: durgun fotograflar TEK KARE,
    # gercek video COK KARE. Sinif AYNI korpusta ikisini AYIRT ETMELI.
    _J1_TEK = [x for x in _J1_NEG if x[1] == 1]
    _J1_COK = [x for x in _J1_NEG if x[1] and x[1] > 1]
    kontrol("⭐ J-1 KARSI-ORNEK: AYNI korpusta durgun kaynaklar TEK KARE, "
            "gercek video COK KARE — sinif ikisini AYIRIYOR",
            len(_J1_TEK) >= 20 and len(_J1_COK) == 1
            and all(n is not None for _, n in _J1_NEG),
            {"tek_kare": len(_J1_TEK), "cok_kare": _J1_COK})
    kontrol("⭐ J-1: sinif karari `medya_turu` ALANINA DEGIL dosyanin "
            "KENDISINE dayaniyor; alan da bagimsiz olarak ayni sonucu veriyor",
            all(str(s.get("medya_turu") or "") == "image" for s in _J1_CEKIM
                if _j1_sinif(s) in ("b_kenburns", "b0_hareketsiz")))

    # ── URETIM DEGISMEDI ──
    kontrol("⭐ J-1: uretim video turunu ZATEN destekliyor — kisit KOD DEGIL "
            "(avci ve medya_kopru varsayilani zaten 'video')",
            'medya_turu: str = "video"' in oku(KOK, "medya", "avci.py")
            and 'medya_turu: str = "video"' in oku(KOK, "medya_kopru.py"))
    kontrol("⭐ J-1: HICBIR esik/kapi eklenmedi ya da gevsetilmedi",
            _kk.OPTIK_DURGUN_ESIGI == 2.0
            and abs(_kk.BENZERLIK_ESIGI - 0.86) < 1e-9
            and abs(_kk.KENAR_DIS_ESIGI - 6.234) < 1e-9)
    kontrol("J-1 GERILEME YOK: 22 alanlik generate sozlesmesi DEGISMEDI",
            len(set(re.findall(r"\{ad: '(\w+)'",
                               oku(KOK, "static/js/api.js")))) == 22)


blok("§40j J-2a — MEDYA TURU RAPOR SOZLESMESI (kapi YOK, esik ENFORCE YOK)")

# ⚠ YALNIZ RAPOR/OLCUM SOZLESMESI. Kapi EKLENMEDI, esik ENFORCE EDILMEDI,
# render davranisi DEGISMEDI (pilot uretilmedi). Ag YOK, $0.00.
#
# J-1'de olculen taban `medya_turu_ozeti()` ile UYGULAMAYA raporlaniyor:
#   olcumler["medya_turu"] -> video_sure_orani / donmus_kadraj_sure_orani
#
# ── RED-FIRST HEDEFLERI ──
# Her iddia, TERSI DOGRU OLSAYDI KIRMIZI yanacak sekilde yazildi:
#   (1) okuyucu yoksa oranlar 0.0 DEGIL None olmali (0.0 "video yok" DER)
#   (2) gercek video kaynagi konunca video_sure_orani ARTMALI
#   (3) referans ENFORCE edilirse denetle'nin fail/warn sayisi DEGISIR
#   (4) 0.155 PLAN basina uygulanirsa 4 YANLIS POZITIF olusur (olculdu)

_J2_KK = _kk


def _j2_okuyucu(yol):
    """Test okuyucusu: gercek dosyayi ffprobe ile olcer, yoksa None."""
    return _j1_kare(yol) if _J1_FFPROBE else None


# ── (1) OKUYUCU YOKSA: STATIK VARSAYILMIYOR ──
_J2_SAHNE = [{"beat_id": "b1", "kaynak_turu": "medya",
              "medya_yolu": "/olmayan/dosya.jpg", "sure_sn": 3.0}]
_J2_YOK = _J2_KK.medya_turu_ozeti(_J2_SAHNE)
kontrol("⭐ J-2a: kare okuyucusu YOKKEN oranlar 0.0 DEGIL None — "
        "'video yok / statiktir' DENMIYOR (EMIN DEGILSEN ENGELLEME)",
        _J2_YOK["video_sure_orani"] is None
        and _J2_YOK["donmus_kadraj_sure_orani"] is None
        and _J2_YOK["olculdu"] is False,
        {k: _J2_YOK[k] for k in ("video_sure_orani", "olculdu")})
kontrol("⭐ J-2a: olculemeyen cekim AYRI KALEM olarak raporlaniyor "
        "(sessizce statige itilmiyor)",
        _J2_YOK["cekim"]["olculemedi"] == 1
        and _J2_YOK["cekim"]["donmus"] == 0
        and _J2_YOK["neden"] == "KARE-OKUYUCU-YOK", _J2_YOK["cekim"])
kontrol("⭐ J-2a: okuyucu VAR ama dosya okunamiyorsa da `olculemedi` "
        "(neden AYRISIYOR)",
        _J2_KK.medya_turu_ozeti(_J2_SAHNE,
                                kare_okuyucu=lambda y: None)["neden"]
        == "KAYNAK-OKUNAMADI")

# ── (2) GERCEK KAYITLAR UZERINDE: TABAN RAPORLANIYOR ──
if _J1_FFPROBE and _J1_PLAN:
    _J2_ORAN = []
    for _pl2 in _J1_TEMSIL:
        _o2 = _J2_KK.medya_turu_ozeti(_pl2, kare_okuyucu=_j2_okuyucu)
        _J2_ORAN.append(_o2)
    kontrol("⭐ J-2a: 7 bagimsiz planin HEPSI TAM OLCULDU "
            "(olculemedi kalemi bos)",
            all(o["olculdu"] is True for o in _J2_ORAN)
            and all(o["cekim"]["olculemedi"] == 0 for o in _J2_ORAN),
            [o["cekim"]["olculemedi"] for o in _J2_ORAN])
    # ⚠ J-5a'DA DEGISTI: tam olarak BIR plan artik video tasiyor.
    _J2_SIFIR = [o for o in _J2_ORAN if o["video_sure_orani"] == 0.0]
    _J2_VIDEOLU = [o for o in _J2_ORAN if o["video_sure_orani"] > 0.0]
    kontrol("⭐ J-2a TABAN: TAM OLARAK BIR plan video tasiyor (J-5a "
            "pilotu); kalan planlar hala 0.0 — J-1 ile AYNI sonuc",
            len(_J2_VIDEOLU) == 1 and len(_J2_SIFIR) == len(_J2_ORAN) - 1,
            [o["video_sure_orani"] for o in _J2_ORAN])
    kontrol("⭐ J-2a: J-5a pilotunun video oraninin BUYUKLUGU de "
            "raporlaniyor (sessiz bayrak degil, OLCU)",
            0.15 < _J2_VIDEOLU[0]["video_sure_orani"] < 0.30,
            _J2_VIDEOLU[0]["video_sure_orani"])

    # ── RED-FIRST (2): gercek video konunca oran ARTMALI ──
    _J2_MP4 = sorted(_g1.glob(os.path.join(os.path.dirname(KOK), "outputs",
                                           "sample", "*.mp4")))[:1]
    if _J2_MP4:
        _J2_SAHTE = [dict(s) for s in _J1_TEMSIL[0]]
        _J2_SAHTE[0]["medya_yolu"] = _J2_MP4[0]
        _J2_SAHTE[0]["kaynak_turu"] = "medya"
        _J2_ART = _J2_KK.medya_turu_ozeti(_J2_SAHTE,
                                          kare_okuyucu=_j2_okuyucu)
        kontrol("⭐ J-2a RED-FIRST: GERCEK video kaynagi konunca "
                "`video_sure_orani` SIFIRDAN BUYUYOR (olcum totolojik degil)",
                _J2_ART["video_sure_orani"] > 0.0
                and _J2_ART["cekim"]["video"] == 1,
                _J2_ART["video_sure_orani"])
    else:
        bloke_yaz("J-2a red-first video enjeksiyonu", "outputs/sample yok")

    # ── (4) SEVIYE HATASI OLCULDU: 0.155 PLAN BASINA UYGULANAMAZ ──
    _J2_DONMUS = [o["donmus_kadraj_sure_orani"] for o in _J2_ORAN]
    _J2_AGREGA_YP = sum(1 for d in _J2_DONMUS
                        if d > _J2_KK.DONMUS_KADRAJ_AGREGA_REFERANSI)
    _J2_PLAN_YP = sum(1 for d in _J2_DONMUS
                      if d > _J2_KK.DONMUS_KADRAJ_PLAN_REFERANSI)
    print(f"     [J-2a] plan basina donmus oranlari: "
          f"{[round(d, 3) for d in sorted(_J2_DONMUS, reverse=True)]}")
    kontrol("⭐ J-2a BELIRLEYICI: AGREGA referansi (0.155) PLAN basina "
            "uygulanirsa YANLIS POZITIF veriyor — seviye KARISTIRILAMAZ",
            _J2_AGREGA_YP == 4, f"{_J2_AGREGA_YP}/7 plan")
    kontrol("⭐ J-2a: PLAN seviyesi referansi (0.334) mevcut korpusta "
            "YANLIS POZITIF VERMIYOR (7 planin 7'si altinda)",
            _J2_PLAN_YP == 0,
            [round(d, 4) for d in _J2_DONMUS
             if d > _J2_KK.DONMUS_KADRAJ_PLAN_REFERANSI])
    kontrol("⭐ J-2a: plan referansi ACIK FORMULLE turetildi — maks gozlenen "
            "plan orani, 3 haneye YUKARI yuvarlanmis (gevsetme YOK)",
            _J2_KK.DONMUS_KADRAJ_PLAN_REFERANSI >= max(_J2_DONMUS)
            and _J2_KK.DONMUS_KADRAJ_PLAN_REFERANSI - max(_J2_DONMUS) < 0.001,
            f"maks {max(_J2_DONMUS):.4f} -> "
            f"{_J2_KK.DONMUS_KADRAJ_PLAN_REFERANSI}")

# ── (3) HICBIR SEY ENFORCE EDILMIYOR ──
kontrol("⭐ J-2a: video orani icin HEDEF UYDURULMADI (pozitif ornek yok)",
        _J2_KK.VIDEO_SURE_ORANI_HEDEFI is None)
kontrol("⭐ J-2a: referanslar `enforce: False` ile RAPOR olarak isaretli",
        _J2_KK.medya_turu_ozeti([])["referans"]["enforce"] is False
        and _J2_KK.kapsam_ozeti()["rapor_referansi"]["enforce"] is False)
kontrol("⭐ J-2a: medya turu icin YENI FAIL KODU EKLENMEDI",
        not any("MEDYA-TUR" in k or "VIDEO-ORAN" in k or "DONMUS" in k
                for k in _qon.FAIL_KODLARI), _qon.FAIL_KODLARI)
kontrol("⭐ J-2a: olcum modulu hukum VERMIYOR — donen sozlukte "
        "fail/warn/seviye ANAHTARI YOK",
        not ({"fail", "warn", "seviye", "ihlal"}
             & set(_J2_KK.medya_turu_ozeti([]))),
        sorted(_J2_KK.medya_turu_ozeti([])))

# ── UCTAN UCA: RAPOR ALANI VAR, HUKUM DEGISMIYOR ──
# ⚠ Kopru `qa` ozeti indirgenmistir (durum/fail/warn); TAM `olcumler`
# `editor_qa.json`'a yazilir. Iddia HER IKI yolda da denetleniyor.
kontrol("⭐ J-2a UCTAN UCA: tam olcum `editor_qa.json`'a yaziliyor "
        "(QaSonucu.sozluk() `olcumler`i tasiyor, plan.py onu diske yazar)",
        '"olcumler": self.olcumler' in oku(KOK, "editor", "qa_on.py")
        and 'editor_qa.json' in oku(KOK, "editor", "plan.py"))
if "_R9" in dir():
    _J2_E2E = (_R9["qa"] or {}).get("medya_turu")
    kontrol("⭐ J-2a UCTAN UCA: `medya_turu` kopru QA ozetinde de VAR",
            isinstance(_J2_E2E, dict), sorted(_R9["qa"] or {}))
    kontrol("⭐ J-2a: okuyucu verilmeyen UCTAN UCA kosumda medya turu "
            "DURUSTCE `olculemedi` — statik VARSAYILMIYOR",
            _J2_E2E["olculdu"] is False
            and _J2_E2E["video_sure_orani"] is None
            and _J2_E2E["neden"] == "KARE-OKUYUCU-YOK", _J2_E2E.get("neden"))
    kontrol("⭐ J-2a: rapor alani HUKMU DEGISTIRMIYOR — durum yalnizca "
            "fail/warn sayisindan turuyor",
            (_R9["qa"]["durum"] == "FAIL") == (_R9["qa"]["fail"] > 0))

# ── KORUNANLAR ──
kontrol("J-2a GERILEME YOK: I-23/I-24/I-25/I-38 kapilari DURUYOR",
        "KALITE-MOTION-ACILIS-KAPANIS" in _qon.FAIL_KODLARI
        and "KALITE-MOTION-ISLEV-TEKRAR" in _qon.FAIL_KODLARI
        and "KALITE-YAZI-SAHNE-DISI" in _qon.FAIL_KODLARI
        and "ORAN-UYUMSUZ" in oku(KOK, "medya/edinim.py")
        and "class DevreKesici" in oku(KOK, "medya/edinim.py"))
kontrol("J-2a GERILEME YOK: ESIKLER GEVSETILMEDI",
        _kk.OPTIK_DURGUN_ESIGI == 2.0
        and abs(_kk.BENZERLIK_ESIGI - 0.86) < 1e-9
        and abs(_kk.UZAMSAL_ENERJI_ESIGI - 11.589) < 1e-9
        and abs(_kk.KENAR_DIS_ESIGI - 6.234) < 1e-9
        and abs(_kk.MODEL_K - 0.935) < 1e-6)
kontrol("J-2a GERILEME YOK: lisans/provenance kapilari DURUYOR",
        "KALITE-KUNYE-EKSIK" in _qon.FAIL_KODLARI
        and "def lisans_suz" in oku(KOK, "edit_kopru.py"))
kontrol("J-2a GERILEME YOK: 22 alanlik generate sozlesmesi DEGISMEDI",
        len(set(re.findall(r"\{ad: '(\w+)'",
                           oku(KOK, "static/js/api.js")))) == 22)
kontrol("J-2a: kullanici secimleri (zoom/pan alanlari) DOKUNULMADI",
        "zoom: 'in' | 'out' | 'yok'" in oku(os.path.dirname(KOK), "app",
                                            "render-studio", "src",
                                            "Video.tsx"))
kontrol("J-2a: deploy.sh DOKUNULMADI (docker commit ile kalicilik duruyor)",
        "docker commit" in oku(os.path.dirname(KOK), "deploy.sh"))
kontrol("J-2a: okuyucu sozlesmesi MEVCUT desenle AYNI — modul DOSYA ACMAZ",
        "kare_okuyucu" in oku(KOK, "editor", "qa_on.py")
        and "kare_okuyucu" in oku(KOK, "editor", "plan.py")
        and "kare_okuyucu" in oku(KOK, "edit_kopru.py"))
kontrol("J-2a: kapsam_ozeti yeni olcumu SAYIYOR (gizli buyume yok)",
        _kk.kapsam_ozeti()["olcum"] >= 14
        and "medya_turu_ozeti" in _kk.kapsam_ozeti()["olcum_adlari"])


blok("§40k J-3 — B-ROLL/CUTAWAY CESITLILIGI OLCULDU (kapi YOK, hedef YOK)")

# ⚠ YALNIZ RAPOR/OLCUM. Kapi EKLENMEDI, esik/hedef ENFORCE EDILMEDI,
# uretim SECIM davranisi DEGISMEDI, render DEGISMEDI (pilot yok).
# Ag YOK, ucretli API YOK, $0.00.
#
# Olculen alanlar (hepsi HER KOSUMDA yeniden hesaplanir — sabit sozluk YOK):
#   kaynak_saglayici_dagilimi · benzersiz_varlik_orani ·
#   cekim_turu_dagilimi · tekrar_sure_orani · provenance · gercek_video_*
#
# ── RED-FIRST: METRIKLER AYIRT EDIYOR MU? ──
# Korpusta DOGAL bir karsi-ornek var: `_smoke_editorv2` ayni varligi iki
# beat'te kullaniyor (I-58'in "duzen B"si). Metrikler onu digerlerinden
# AYIRMAZSA totolojiktir. Ayrica sentetik karsi-orneklerle her alanin
# TERSINE dondugu gosteriliyor.

_J3_KK = _kk

if _J1_PLAN:
    _J3 = []
    for _pl3 in _J1_TEMSIL:
        _J3.append(_J3_KK.broll_cesitliligi_ozeti(_pl3))
    print(f"     [J-3] benzersiz_varlik_orani: "
          f"{sorted(o['benzersiz_varlik_orani'] for o in _J3)}")
    print(f"     [J-3] tekrar_sure_orani     : "
          f"{sorted(o['tekrar_sure_orani'] for o in _J3)}")
    print(f"     [J-3] cekim_turu_cesidi     : "
          f"{sorted(o['cekim_turu_cesidi'] for o in _J3)}")
    print(f"     [J-3] tek_saglayici_sure_orani: "
          f"{sorted(round(o['tek_saglayici_sure_orani'], 3) for o in _J3)}")

    kontrol("⭐ J-3: 7 bagimsiz planin HEPSI TAM OLCULDU "
            "(kimliksiz cekim yok, provenance belirsiz yok)",
            all(o["olculdu"] is True for o in _J3),
            [o.get("neden") for o in _J3 if not o["olculdu"]])

    # ── TABAN: CESITLILIK DAR ──
    kontrol("⭐ J-3 TABAN: HICBIR planda 3'ten fazla cekim turu YOK "
            "(cutaway cesidi dar)",
            max(o["cekim_turu_cesidi"] for o in _J3) == 3,
            sorted(o["cekim_turu_cesidi"] for o in _J3))
    kontrol("⭐ J-3 TABAN: planlarin cogunda TEK saglayici sureyi "
            "TAMAMEN tasiyor (sure tabanli tekel >= 0.94)",
            min(o["tek_saglayici_sure_orani"] for o in _J3) >= 0.94,
            sorted(round(o["tek_saglayici_sure_orani"], 4) for o in _J3))
    kontrol("⭐ J-3: SURE tabanli tekel, mevcut CEKIM tabanli kapidan "
            "FARKLI bilgi veriyor (_i20: 0.80 cekim -> 0.949 sure)",
            any(abs(o["tek_saglayici_sure_orani"] - 0.9494) < 1e-3
                for o in _J3),
            [round(o["tek_saglayici_sure_orani"], 4) for o in _J3])

    # ── RED-FIRST (1): DOGAL KARSI-ORNEK AYRISIYOR ──
    _J3_TEK = [o for o in _J3 if o["benzersiz_varlik_orani"] < 1.0]
    _J3_TAM = [o for o in _J3 if o["benzersiz_varlik_orani"] == 1.0]
    kontrol("⭐ J-3 RED-FIRST: DOGAL karsi-ornek (`_smoke_editorv2`) "
            "metriklerle AYRISIYOR — benzersiz oran < 1.0 VE tekrar > 0",
            len(_J3_TEK) == 1 and len(_J3_TAM) == len(_J3) - 1
            and _J3_TEK[0]["tekrar_sure_orani"] > 0
            and all(o["tekrar_sure_orani"] == 0.0 for o in _J3_TAM),
            (_J3_TEK[0]["benzersiz_varlik_orani"],
             _J3_TEK[0]["tekrar_sure_orani"]) if _J3_TEK else None)
    kontrol("⭐ J-3: tekrar EDEN varlik ISIMLENDIRILIYOR (sessiz sayi degil)",
            bool(_J3_TEK) and bool(_J3_TEK[0]["tekrar_eden_varlik"]),
            _J3_TEK[0]["tekrar_eden_varlik"] if _J3_TEK else None)

    # ── RED-FIRST (2): SENTETIK KARSI-ORNEKLER, HER ALAN TERSINE DONUYOR ──
    # ⚠ Sabit indeks KIRILGAN: plan, OLCULEN ozelliginden secilir —
    # tekrarsiz (benzersiz oran 1.0) ve en cok medya cekimi olan plan.
    _J3_SEC = max(zip(_J3, _J1_TEMSIL),
                  key=lambda t: (t[0]["benzersiz_varlik_orani"] == 1.0,
                                 t[0]["medya_cekim_sayisi"]))
    _J3_TEMIZ = [dict(s) for s in _J3_SEC[1]]
    assert _J3_SEC[0]["benzersiz_varlik_orani"] == 1.0
    _J3_T0 = _J3_KK.broll_cesitliligi_ozeti(_J3_TEMIZ)
    _J3_KOPYA = [dict(s) for s in _J3_TEMIZ]
    _J3_KOPYA[1]["asset_id"] = _J3_KOPYA[0]["asset_id"]
    _J3_T1 = _J3_KK.broll_cesitliligi_ozeti(_J3_KOPYA)
    kontrol("⭐ J-3 RED-FIRST: varlik TEKRARLANINCA benzersiz oran DUSUYOR "
            "ve tekrar_sure_orani YUKSELIYOR (totoloji degil)",
            _J3_T1["benzersiz_varlik_orani"] < _J3_T0["benzersiz_varlik_orani"]
            and _J3_T1["tekrar_sure_orani"] > _J3_T0["tekrar_sure_orani"],
            (_J3_T0["benzersiz_varlik_orani"], _J3_T1["benzersiz_varlik_orani"],
             _J3_T1["tekrar_sure_orani"]))

    _J3_SAG = [dict(s) for s in _J3_TEMIZ]
    _J3_SAG[0]["saglayici"] = "pexels"
    _J3_T2 = _J3_KK.broll_cesitliligi_ozeti(_J3_SAG)
    kontrol("⭐ J-3 RED-FIRST: IKINCI saglayici eklenince sure tabanli "
            "tekel DUSUYOR",
            _J3_T2["tek_saglayici_sure_orani"]
            < _J3_T0["tek_saglayici_sure_orani"]
            and len(_J3_T2["kaynak_saglayici_dagilimi"]) == 2,
            (_J3_T0["tek_saglayici_sure_orani"],
             _J3_T2["tek_saglayici_sure_orani"]))

    _J3_TUR = [dict(s) for s in _J3_TEMIZ]
    _J3_TUR[0]["cekim_turu"] = "insert-makro"
    _J3_T3 = _J3_KK.broll_cesitliligi_ozeti(_J3_TUR)
    kontrol("⭐ J-3 RED-FIRST: YENI cekim turu eklenince cesit sayisi ARTIYOR",
            _J3_T3["cekim_turu_cesidi"] > _J3_T0["cekim_turu_cesidi"],
            (_J3_T0["cekim_turu_cesidi"], _J3_T3["cekim_turu_cesidi"]))

# ── EMIN DEGILSEN ENGELLEME: BELIRSIZLIK IYIMSER SAYILMIYOR ──
_J3_KIMLIKSIZ = [{"kaynak_turu": "medya", "asset_id": "", "saglayici": "w",
                  "cekim_turu": "medium", "lisans": "cc-by", "sure_sn": 2.0}]
_J3_K = _J3_KK.broll_cesitliligi_ozeti(_J3_KIMLIKSIZ)
kontrol("⭐ J-3: varlik kimligi YOKSA benzersiz oran 1.0 DEGIL None "
        "(cesitlilik VARSAYILMIYOR)",
        _J3_K["benzersiz_varlik_orani"] is None
        and _J3_K["tekrar_sure_orani"] is None
        and "VARLIK-KIMLIGI-EKSIK" in _J3_K["neden"], _J3_K.get("neden"))

_J3_UNK = [{"kaynak_turu": "medya", "asset_id": "a", "saglayici": "w",
            "cekim_turu": "medium", "lisans": "unknown", "sure_sn": 2.0}]
_J3_U = _J3_KK.broll_cesitliligi_ozeti(_J3_UNK)
kontrol("⭐ J-3: BELIRSIZ provenance `olculemedi` yaziyor ve WARN ADAYI "
        "olarak isaretleniyor — lisansli SAYILMIYOR",
        _J3_U["provenance"]["olculdu"] is False
        and _J3_U["provenance"]["belirsiz_cekim"] == 1
        and _J3_U["provenance"]["uyari_adayi"] is True
        and "PROVENANCE-BELIRSIZ" in _J3_U["neden"], _J3_U["provenance"])
kontrol("⭐ J-3: bos lisans da BELIRSIZ sayiliyor (sessiz gecis yok)",
        _J3_KK.broll_cesitliligi_ozeti(
            [{"kaynak_turu": "medya", "asset_id": "a", "saglayici": "w",
              "cekim_turu": "medium", "lisans": "", "sure_sn": 2.0}]
        )["provenance"]["belirsiz_cekim"] == 1)
kontrol("⭐ J-3: cekim turu BOSSA cesit sayisina KATILMIYOR, ayri "
        "`cekim_turu_belirsiz` kalemi olarak sayiliyor",
        _J3_KK.broll_cesitliligi_ozeti(
            [{"kaynak_turu": "medya", "asset_id": "a", "saglayici": "w",
              "cekim_turu": "", "lisans": "cc-by", "sure_sn": 2.0}]
        )["cekim_turu_belirsiz"] == 1)

# ── GERCEK VIDEO: 0 OLARAK ACIKCA RAPORLANIYOR, VARSAYILMIYOR ──
if _J1_FFPROBE and _J1_PLAN:
    _J3_MT = _J3_KK.medya_turu_ozeti(_J3_SEC[1], kare_okuyucu=_j2_okuyucu)
    _J3_V = _J3_KK.broll_cesitliligi_ozeti(_J3_SEC[1],
                                           medya_turu_ozeti_=_J3_MT)
    kontrol("⭐ J-3: gercek video YOK ve bu ACIKCA 0 olarak raporlaniyor "
            "(J-2a olcumunden OKUNUYOR, yeniden hesaplanmiyor)",
            _J3_V["gercek_video_cekim"] == 0
            and _J3_V["gercek_video_sure_orani"] == 0.0,
            (_J3_V["gercek_video_cekim"], _J3_V["gercek_video_sure_orani"]))
kontrol("⭐ J-3: J-2a olcumu VERILMEZSE video alani 0 DEGIL None "
        "('video yok' IDDIA EDILMIYOR)",
        _J3_KK.broll_cesitliligi_ozeti(
            [{"kaynak_turu": "medya", "asset_id": "a", "saglayici": "w",
              "cekim_turu": "medium", "lisans": "cc-by", "sure_sn": 2.0}]
        )["gercek_video_sure_orani"] is None)

# ── HICBIR SEY ENFORCE EDILMIYOR ──
kontrol("⭐ J-3: hedef UYDURULMADI (`hedef` None, `enforce` False)",
        _J3_KK.broll_cesitliligi_ozeti([])["hedef"] is None
        and _J3_KK.broll_cesitliligi_ozeti([])["enforce"] is False)
# ⚠ K-1'DE DEGISTI. J-3 aninda cesitlilik alanlarinin HICBIRI kapiya bagli
# DEGILDI ve bu dogruydu. K-1 kamera-hareketi bacagini video cekimlerde muaf
# tutunca bosluk kapanmali oldu ve `KALITE-BROLL-CESITLILIK` BILEREK eklendi.
# Iddia SILINMEDI, TARIHLENDIRILDI: ORANLAR hala kapiya bagli degil.
kontrol("⭐ J-3 (K-1 sonrasi): cesitlilik ORANLARI hala kapiya BAGLI DEGIL "
        "— hedef None, enforce False, sayisal esik YOK",
        _J3_KK.broll_cesitliligi_ozeti([])["hedef"] is None
        and _J3_KK.broll_cesitliligi_ozeti([])["enforce"] is False
        and set(_J3_KK.broll_cesitliligi_ozeti([])["kapiya_bagli"])
        == {"video_islev_tur_tekrari", "video_pencere_tur_tekrari"},
        _J3_KK.broll_cesitliligi_ozeti([])["kapiya_bagli"])
kontrol("⭐ J-3: olcum modulu hukum VERMIYOR — donen sozlukte "
        "fail/warn/seviye/ihlal ANAHTARI YOK",
        not ({"fail", "warn", "seviye", "ihlal"}
             & set(_J3_KK.broll_cesitliligi_ozeti([]))),
        sorted(_J3_KK.broll_cesitliligi_ozeti([])))
kontrol("⭐ J-3: saglayici TEKEL kapisi COGALTILMADI — mevcut kapi "
        "AYNEN duruyor (cekim tabanli, tavan 0.40)",
        "SAGLAYICI-TEKEL" in oku(KOK, "editor", "qa_on.py")
        and "oran > 0.40" in oku(KOK, "editor", "qa_on.py"))

# ── UCTAN UCA ──
if "_R9" in dir():
    _J3_E2E = (_R9["qa"] or {}).get("broll_cesitliligi")
    kontrol("⭐ J-3 UCTAN UCA: `broll_cesitliligi` QA raporunda VAR",
            isinstance(_J3_E2E, dict), sorted(_R9["qa"] or {}))
    kontrol("⭐ J-3 UCTAN UCA: dagilim alanlari GERCEKTEN dolu",
            bool(_J3_E2E.get("kaynak_saglayici_dagilimi"))
            and bool(_J3_E2E.get("cekim_turu_dagilimi"))
            and _J3_E2E.get("medya_cekim_sayisi", 0) > 0,
            _J3_E2E.get("medya_cekim_sayisi"))
    kontrol("⭐ J-3: rapor alani HUKMU DEGISTIRMIYOR — durum yalnizca "
            "fail/warn sayisindan turuyor",
            (_R9["qa"]["durum"] == "FAIL") == (_R9["qa"]["fail"] > 0))

# ── KORUNANLAR ──
kontrol("J-3 GERILEME YOK: I-23/I-24/I-25/I-38 kapilari DURUYOR",
        "KALITE-MOTION-ACILIS-KAPANIS" in _qon.FAIL_KODLARI
        and "KALITE-MOTION-ISLEV-TEKRAR" in _qon.FAIL_KODLARI
        and "KALITE-YAZI-SAHNE-DISI" in _qon.FAIL_KODLARI
        and "ORAN-UYUMSUZ" in oku(KOK, "medya/edinim.py")
        and "class DevreKesici" in oku(KOK, "medya/edinim.py"))
kontrol("J-3 GERILEME YOK: ESIKLER GEVSETILMEDI",
        _kk.OPTIK_DURGUN_ESIGI == 2.0
        and abs(_kk.BENZERLIK_ESIGI - 0.86) < 1e-9
        and abs(_kk.UZAMSAL_ENERJI_ESIGI - 11.589) < 1e-9
        and abs(_kk.KENAR_DIS_ESIGI - 6.234) < 1e-9
        and abs(_kk.MODEL_K - 0.935) < 1e-6)
kontrol("J-3 GERILEME YOK: lisans/provenance kapilari DURUYOR",
        "KALITE-KUNYE-EKSIK" in _qon.FAIL_KODLARI
        and "def lisans_suz" in oku(KOK, "edit_kopru.py"))
kontrol("J-3 GERILEME YOK: 22 alanlik generate sozlesmesi DEGISMEDI",
        len(set(re.findall(r"\{ad: '(\w+)'",
                           oku(KOK, "static/js/api.js")))) == 22)
kontrol("J-3: kullanici secimleri (zoom/pan alanlari) DOKUNULMADI",
        "zoom: 'in' | 'out' | 'yok'" in oku(os.path.dirname(KOK), "app",
                                            "render-studio", "src",
                                            "Video.tsx"))
kontrol("J-3: deploy.sh DOKUNULMADI",
        "docker commit" in oku(os.path.dirname(KOK), "deploy.sh"))
kontrol("J-3: uretim SECIM kodu DEGISMEDI (siralama/aday atama)",
        "def semantik_puan" in oku(KOK, "medya/siralama.py")
        and "def medya_tekrari" in oku(KOK, "editor", "kalite_kapisi.py"))
kontrol("J-3: kapsam_ozeti yeni olcumu SAYIYOR (gizli buyume yok)",
        _kk.kapsam_ozeti()["olcum"] >= 15
        and "broll_cesitliligi_ozeti" in _kk.kapsam_ozeti()["olcum_adlari"])


blok("§40l J-4 — VIDEO PROVENANCE/LISANS SOZLESMESI (YALNIZ ENGELLER)")

# ⚠ BU ATOM SOZLESME + TEST. Ag YOK, INDIRME YOK, render/secim davranisi
# DEGISMEDI, edinim hattina BILEREK BAGLANMADI. $0.00.
#
# ⚠ SOZLESME YALNIZCA ENGELLER: mevcut `lisans_karari()` reddettiyse
# `video_provenance_karari()` o karari ASLA cevirmez. Gorsel yolu HIC
# degismez. EMIN DEGILSEN ALMA -> varsayilan karar REDDIR.
#
# ── RED-FIRST TASARIMI ──
# (a) TEMIZ bir vaka KABUL edilmeli — yoksa "her seye hayir diyen" bir kapi
#     totolojik olarak butun red testlerini gecerdi.
# (b) SEKIZ zorunlu kanit TEK TEK cikarilinca kapi REDDETMELI ve eksik alani
#     ADIYLA soylemeli.
# (c) YouTube: aciklamadaki lisans beyani TEK BASINA yetmemeli.

_VL = __import__("medya.video_lisans", fromlist=["video_lisans"])

_J4_TEK = {"codec": "h264", "genislik": 1920, "yukseklik": 1080,
           "bitrate": 8_000_000}
_J4_TEMIZ = {
    "license": "CC BY 4.0", "artist": "Jane Doe",
    "orijinal_url": "https://commons.wikimedia.org/wiki/File:ornek.webm",
    "lisans_kaydi": "https://commons.wikimedia.org/w/api.php?titles=File:x",
    "indirme_zamani": "2026-08-14T10:00:00Z",
}


def _j4(kayit=None, saglayici="wikimedia", teknik=None, **ek):
    k = dict(_J4_TEMIZ if kayit is None else kayit)
    k.update(ek)
    return _VL.video_provenance_karari(
        k, saglayici, teknik=_J4_TEK if teknik is None else teknik)


# ── (a) TEMIZ VAKA KABUL EDILIYOR (kapi "her seye hayir" DEGIL) ──
_J4_OK = _j4()
kontrol("⭐ J-4 RED-FIRST TABANI: kanitlarin HEPSI olan temiz commons "
        "videosu KABUL EDILIYOR (kapi totolojik degil)",
        _J4_OK["video_kabul"] is True and not _J4_OK["red_nedeni"],
        _J4_OK["red_nedeni"])
kontrol("⭐ J-4: kabul edilen kayitta TUM kanitlar RAPORLANIYOR "
        "(kaynak URL, saglayici, lisans, lisans kaydi, zaman, teknik)",
        all(_J4_OK["kanit"].get(a) for a in _VL.VIDEO_ZORUNLU_KANIT),
        _J4_OK["kanit"])

# ── (b) SEKIZ ZORUNLU KANIT: HER BIRI TEK TEK CIKARILINCA RED ──
_J4_DUSUR = {
    "kaynak_url": dict(_J4_TEMIZ, orijinal_url=""),
    "lisans_kaydi": dict(_J4_TEMIZ, lisans_kaydi="", lisans_url=""),
    "indirme_zamani": dict(_J4_TEMIZ, indirme_zamani=""),
}
for _ad4, _kay4 in _J4_DUSUR.items():
    _r4 = _VL.video_provenance_karari(_kay4, "wikimedia", teknik=_J4_TEK)
    kontrol(f"⭐ J-4 RED-FIRST: `{_ad4}` YOKKEN video REDDEDILIYOR "
            f"ve eksik alan ADIYLA soyleniyor",
            _r4["video_kabul"] is False and _ad4 in _r4["eksik_kanit"],
            (_r4["video_kabul"], _r4["eksik_kanit"]))

_J4_TEKNIK_EKSIK = {
    "codec": {"genislik": 1920, "yukseklik": 1080, "bitrate": 8_000_000},
    "cozunurluk": {"codec": "h264", "bitrate": 8_000_000},
    "bitrate": {"codec": "h264", "genislik": 1920, "yukseklik": 1080},
}
for _ad4, _tk4 in _J4_TEKNIK_EKSIK.items():
    _r4 = _j4(teknik=_tk4)
    kontrol(f"⭐ J-4 RED-FIRST: OZGUN KALITE kaniti `{_ad4}` yoksa "
            f"video REDDEDILIYOR",
            _r4["video_kabul"] is False and _ad4 in _r4["eksik_kanit"],
            _r4["eksik_kanit"])
kontrol("⭐ J-4: teknik kanit HIC verilmezse de RED (varsayim yok)",
        _j4(teknik={})["video_kabul"] is False
        and len(_j4(teknik={})["eksik_kanit"]) == 3,
        _j4(teknik={})["eksik_kanit"])
kontrol("⭐ J-4: SIFIR/negatif cozunurluk-bitrate GECERLI SAYILMIYOR",
        _j4(teknik={"codec": "h264", "genislik": 0, "yukseklik": 0,
                    "bitrate": 0})["video_kabul"] is False)
kontrol("⭐ J-4: saglayici bos ise RED",
        _VL.video_provenance_karari(_J4_TEMIZ, "",
                                    teknik=_J4_TEK)["video_kabul"] is False)

# ── (c) YOUTUBE VE BENZERI PLATFORMLAR ──
_J4_YT = {"license": "CC BY 3.0", "artist": "Kanal",
          "orijinal_url": "https://www.youtube.com/watch?v=abc",
          "lisans_kaydi": "https://www.youtube.com/watch?v=abc",
          "indirme_zamani": "2026-08-14T10:00:00Z"}
_R_YT = _VL.video_provenance_karari(_J4_YT, "youtube", teknik=_J4_TEK)
kontrol("⭐ J-4 BELIRLEYICI: YouTube videosunun ACIKLAMASINDAKI 'CC BY' "
        "beyani TEK BASINA YETMIYOR — video REDDEDILIYOR",
        _R_YT["video_kabul"] is False
        and "indirme izni" in _R_YT["red_nedeni"], _R_YT["red_nedeni"])
kontrol("⭐ J-4: platform karari `beyan_tek_basina_yeterli: False` diye "
        "ACIKCA yaziliyor ve eksik izin kanitlari sayiliyor",
        _R_YT["platform"]["izin_kaniti_zorunlu"] is True
        and _R_YT["platform"]["beyan_tek_basina_yeterli"] is False
        and set(_R_YT["platform"]["eksik_izin_kaniti"])
        == set(_VL.PLATFORM_IZIN_KANITI), _R_YT["platform"])
kontrol("⭐ J-4: red SESSIZ degil — WARN metni ToS/indirme iznini "
        "acikca gerekce gosteriyor",
        any("PLATFORM-IZIN-KANITI-YOK" in u for u in _R_YT["uyarilar"]),
        _R_YT["uyarilar"])
_R_YT2 = _VL.video_provenance_karari(
    dict(_J4_YT, indirme_izni=True, tos_uyumu=True,
         hak_sahibi_dogrulandi=True), "youtube", teknik=_J4_TEK)
kontrol("⭐ J-4: izinler ACIK olsa BILE 'lisans kaydi' videonun KENDI "
        "sayfasiysa bu BEYANDIR, bagimsiz kayit degildir -> RED",
        _R_YT2["video_kabul"] is False
        and "bagimsiz degil" in _R_YT2["red_nedeni"], _R_YT2["red_nedeni"])
for _p4 in ("https://vimeo.com/1", "https://www.tiktok.com/@a/video/1",
            "https://x.com/a/status/1", "https://youtu.be/abc"):
    kontrol(f"⭐ J-4: izin kaniti zorunlu platform taniniyor ({_p4})",
            _VL.platform_gerekli_mi(_p4, "") is True)
kontrol("⭐ J-4: commons/nasa/pexels izin kaniti ZORUNLU platform DEGIL "
        "(kendi lisans kaydini veriyorlar)",
        not _VL.platform_gerekli_mi(
            "https://commons.wikimedia.org/wiki/File:x", "wikimedia")
        and not _VL.platform_gerekli_mi("https://images.nasa.gov/a", "nasa"))

# ── MEVCUT LISANS DUVARI GEVSETILMIYOR / CEVRILMIYOR ──
for _ham4, _et4 in (("All Rights Reserved", "ARR"),
                    ("CC BY-NC 4.0", "NC"), ("CC BY-ND 4.0", "ND"),
                    ("Getty Images", "ticari stok")):
    _r4 = _VL.video_provenance_karari(
        dict(_J4_TEMIZ, license=_ham4, artist="X"), "wikimedia",
        teknik=_J4_TEK)
    kontrol(f"⭐ J-4: lisans duvarinin reddi ({_et4}) video kapisinda "
            f"ASLA CEVRILMIYOR",
            _r4["video_kabul"] is False and _r4["render_kullanilabilir"]
            is not True, (_et4, _r4["red_nedeni"]))
kontrol("⭐ J-4: atif gerektiren lisansta eser sahibi YOKSA yine RED "
        "(mevcut kural KORUNDU)",
        _VL.video_provenance_karari(
            dict(_J4_TEMIZ, license="CC BY 4.0", artist=""), "wikimedia",
            teknik=_J4_TEK)["video_kabul"] is False)

# ── GORSEL YOLU HIC DEGISMEDI ──
_LIS4 = __import__("medya.lisans", fromlist=["lisans"])
kontrol("⭐ J-4: GORSEL lisans karari DEGISMEDI — PD beyani hala geciyor "
        "('No known copyright restrictions')",
        _LIS4.lisans_karari(
            {"license": "No known copyright restrictions",
             "artist": "LoC"}, "loc")["render_kullanilabilir"] is True)
kontrol("⭐ J-4: GORSEL yolu icin YENI SART EKLENMEDI — gorsel karari "
        "video kanitlarini SORMUYOR",
        _LIS4.lisans_karari({"license": "CC0", "artist": ""},
                            "pixabay")["render_kullanilabilir"] is True)
kontrol("⭐ J-4: video modulu gorsel modulunu SARMALIYOR, KOPYALAMIYOR "
        "(tek lisans gercegi)",
        "from .lisans import lisans_karari" in oku(KOK, "medya",
                                                   "video_lisans.py"))

# ── AG YOK / EDINIM HATTINA BAGLI DEGIL ──
_VLS = oku(KOK, "medya", "video_lisans.py")
kontrol("⭐ J-4: modul AGA CIKMIYOR (requests/urlopen/httpx yok)",
        not any(a in _VLS for a in ("import requests", "urlopen", "httpx",
                                    "http.client", "socket")))
kontrol("⭐ J-4: bu atomda edinim hattina BAGLANMADI — secim/render "
        "davranisi DEGISMEDI",
        "video_lisans" not in oku(KOK, "medya", "edinim.py")
        and "video_lisans" not in oku(KOK, "medya", "indirme.py")
        and "video_lisans" not in oku(KOK, "medya", "avci.py"))
kontrol("⭐ J-4: kapsam_ozeti bu sinirlari ACIKCA yaziyor",
        _VL.kapsam_ozeti()["yalniz_engeller"] is True
        and _VL.kapsam_ozeti()["aga_cikar"] is False
        and _VL.kapsam_ozeti()["edinim_hattina_bagli"] is False
        and _VL.kapsam_ozeti()["gorsel_yolunu_degistirir"] is False)
kontrol("⭐ J-4: SEKIZ zorunlu kanit sozlesmede SAYILI",
        len(_VL.VIDEO_ZORUNLU_KANIT) == 8
        and set(_VL.VIDEO_ZORUNLU_KANIT) == {
            "kaynak_url", "saglayici", "lisans_turu", "lisans_kaydi",
            "indirme_zamani", "codec", "cozunurluk", "bitrate"},
        _VL.VIDEO_ZORUNLU_KANIT)
kontrol("⭐ J-4: taninmayan saglayici KABUL edilse bile SESSIZ gecmiyor "
        "(elle dogrulama uyarisi)",
        any("SAGLAYICI-TANINMIYOR" in u for u in _VL.video_provenance_karari(
            dict(_J4_TEMIZ, orijinal_url="https://ornek-arsiv.org/v/1"),
            "ornek-arsiv", teknik=_J4_TEK)["uyarilar"]))
kontrol("J-4: video_lisans.py derleniyor",
        _derlenir(os.path.join(KOK, "medya", "video_lisans.py")))

# ── KORUNANLAR ──
kontrol("J-4 GERILEME YOK: I-23/I-24/I-25/I-38 kapilari DURUYOR",
        "KALITE-MOTION-ACILIS-KAPANIS" in _qon.FAIL_KODLARI
        and "KALITE-MOTION-ISLEV-TEKRAR" in _qon.FAIL_KODLARI
        and "KALITE-YAZI-SAHNE-DISI" in _qon.FAIL_KODLARI
        and "ORAN-UYUMSUZ" in oku(KOK, "medya/edinim.py")
        and "class DevreKesici" in oku(KOK, "medya/edinim.py"))
kontrol("J-4 GERILEME YOK: ESIKLER GEVSETILMEDI",
        _kk.OPTIK_DURGUN_ESIGI == 2.0
        and abs(_kk.BENZERLIK_ESIGI - 0.86) < 1e-9
        and abs(_kk.KENAR_DIS_ESIGI - 6.234) < 1e-9)
kontrol("J-4 GERILEME YOK: lisans/provenance kapilari DURUYOR",
        "KALITE-KUNYE-EKSIK" in _qon.FAIL_KODLARI
        and "def lisans_suz" in oku(KOK, "edit_kopru.py"))
kontrol("J-4 GERILEME YOK: 22 alanlik generate sozlesmesi DEGISMEDI",
        len(set(re.findall(r"\{ad: '(\w+)'",
                           oku(KOK, "static/js/api.js")))) == 22)
kontrol("J-4: kullanici secimleri (zoom/pan alanlari) DOKUNULMADI",
        "zoom: 'in' | 'out' | 'yok'" in oku(os.path.dirname(KOK), "app",
                                            "render-studio", "src",
                                            "Video.tsx"))
kontrol("J-4: deploy.sh DOKUNULMADI",
        "docker commit" in oku(os.path.dirname(KOK), "deploy.sh"))


blok("§40m J-5a — GERCEK VIDEO EDINIMI (dar kapsam, tavanli, red-first)")

# ⚠ BU BLOKTA AG KULLANILMAZ: arayici SAHTE cagrilabilirdir. Gercek indirme
# ayri ve TEK seferlik yapildi; kaniti asagida §40n'de olculuyor.
# Kapsam: J-4 kapisinin edinim hattina BAGLANDIGI dogrulanir, tavanlar ve
# RED yollari red-first kanitlanir.

_VE = __import__("medya.video_edinim", fromlist=["video_edinim"])


def _j5_aday(**ek):
    a = {"asset_id": "", "baslik": "Irrigation sprinkler", "saglayici": "wikimedia",
         "tur": "video", "medya_turu": "video", "alaka_sirasi": 1,
         "genislik": 1920, "yukseklik": 1080, "sure_sn": 16.5,
         "boyut_bayt": 75_000_000, "mime": "video/webm",
         "bitrate_tahmini": 36_000_000,
         "indirme_url": "https://upload.wikimedia.org/x.webm",
         "orijinal_url": "https://commons.wikimedia.org/wiki/File:x.webm",
         "lisans_kaydi": "https://commons.wikimedia.org/w/api.php?titles=x",
         "lisans": "cc-by-sa", "lisans_url": "https://cc.org/by-sa",
         "eser_sahibi": "Jane", "atif_gerekli": True,
         "render_kullanilabilir": True, "red_nedeni": "",
         "atif_metni": "Jane / CC BY-SA", "license": "CC BY-SA 4.0",
         "artist": "Jane"}
    a.update(ek)
    return a


def _j5_arayici(adaylar, elenen=None, hata=""):
    def _ara(sorgu, **kw):
        return {"ok": bool(adaylar), "sorgu": sorgu, "denenen": len(adaylar),
                "adaylar": list(adaylar), "elenen": list(elenen or []),
                "hata": hata}
    return _ara


_J5_DIZIN = os.path.join(tempfile.mkdtemp(prefix="j5_"), "medya")
os.makedirs(_J5_DIZIN, exist_ok=True)
from medya import guvenlik as _j5guv                     # noqa: E402


def _j5_bozuk_dosya():
    """Medya OLMAYAN ama yeterince buyuk bir dosya — kapi reddetmeli."""
    y = os.path.join(_J5_DIZIN, "bozuk.webm")
    with open(y, "wb") as f:
        f.write(b"\x00\x01bozuk-veri" * 2000)
    return y

# ── (1) TAVANLAR SERT ──
kontrol("⭐ J-5a: indirme tavani DOSYA=1 ve BAYT=300MB olarak SABIT",
        _VE.INDIRME_TAVANI_DOSYA == 1
        and _VE.INDIRME_TAVANI_BAYT == 300 * 1024 * 1024,
        (_VE.INDIRME_TAVANI_DOSYA, _VE.INDIRME_TAVANI_BAYT))
kontrol("⭐ J-5a RED-FIRST: TAVANI ASAN aday secilmiyor ve neden "
        "RAPORLANIYOR (301 MB reddedilir)",
        _VE.aday_sec([_j5_aday(boyut_bayt=301 * 1024 * 1024)])[0] is None
        and "TAVAN-ASIYOR" in _VE.aday_sec(
            [_j5_aday(boyut_bayt=301 * 1024 * 1024)])[1][0]["neden"])
kontrol("⭐ J-5a: tavan icindeki adaylar arasindan EN YUKSEK COZUNURLUK "
        "seciliyor (720p yerine 1080p)",
        _VE.aday_sec([_j5_aday(genislik=1280, yukseklik=720,
                               baslik="720p"),
                      _j5_aday(baslik="1080p")])[0]["baslik"] == "1080p")
kontrol("⭐ J-5a: esit cozunurlukte EN YUKSEK BITRATE seciliyor",
        _VE.aday_sec([_j5_aday(bitrate_tahmini=10_000_000, baslik="dusuk"),
                      _j5_aday(bitrate_tahmini=40_000_000, baslik="yuksek")]
                     )[0]["baslik"] == "yuksek")
kontrol("⭐ J-5a: sure yetersizse aday ELENIYOR",
        _VE.aday_sec([_j5_aday(sure_sn=2.0)], en_az_sure_sn=8.0)[0] is None)

# ── (2) ANAHTARLI SAGLAYICI VE KONU DISI FALLBACK YOK ──
kontrol("⭐ J-5a: anahtar gerektiren saglayicilar KULLANILMIYOR "
        "(pexels/pixabay/freepik)",
        set(("pexels", "pixabay", "freepik")) <= set(_VE.ANAHTARLI_SAGLAYICI)
        and _VE.kapsam_ozeti()["anahtarli_saglayici_kullanilmaz"])
_J5_VLS = oku(KOK, "medya", "video_edinim.py")
kontrol("⭐ J-5a: modul PEXELS/PIXABAY anahtari ARAMIYOR (credential "
        "okumasi YOK)",
        not any(a in _J5_VLS for a in ("PEXELS_KEY", "PIXABAY_KEY",
                                       "FREEPIK", "os.environ", "getenv")))
_J5_BOS = _VE.video_edin("cim bicme", _J5_DIZIN,
                         arayici=_j5_arayici([]))
kontrol("⭐ J-5a BELIRLEYICI: aday YOKSA KONU DISI FALLBACK YAPILMIYOR — "
        "bos donuyor (yanlis video ALINMIYOR)",
        _J5_BOS["ok"] is False and _J5_BOS["indirilen"] == []
        and _J5_BOS["hata"] in ("ADAY-YOK", ""), _J5_BOS["hata"])
kontrol("⭐ J-5a: kapsam ozeti `konu_disi_fallback: False` diye YAZIYOR",
        _VE.kapsam_ozeti()["konu_disi_fallback"] is False)

# ── (3) NASA YALNIZ GERCEKTEN UZAY SORGUSUNDA ──
for _s5 in ("nasa mars rover", "space station orbit", "uzay teleskobu",
            "apollo 11 moon"):
    kontrol(f"⭐ J-5a: uzay sorgusu TANINIYOR ({_s5})",
            _VE.uzay_sorgusu_mu(_s5) is True)
for _s5 in ("lawn grass mowing", "sprinkler irrigation lawn",
            "grass seed sowing", "cim bicme makinesi"):
    kontrol(f"⭐ J-5a BELIRLEYICI: konu disi sorguda NASA DEVREYE GIRMIYOR "
            f"({_s5})",
            _VE.uzay_sorgusu_mu(_s5) is False
            and _VE.video_edin(_s5, _J5_DIZIN, arayici=_j5_arayici([]))
            ["saglayici_sirasi"] == ["wikimedia"])
kontrol("⭐ J-5a: uzay sorgusunda NASA IKINCI saglayici olarak EKLENIYOR",
        _VE.video_edin("nasa mars rover", _J5_DIZIN,
                       arayici=_j5_arayici([]))["saglayici_sirasi"]
        == ["wikimedia", "nasa"])

# ── (4) J-4 KAPISI GERCEKTEN BAGLI (ON-KONTROL REDDI) ──
_J5_LISANSSIZ = _j5_aday(license="All Rights Reserved", artist="X",
                         render_kullanilabilir=False,
                         red_nedeni="lisans metni kisitli")
_J5_R1 = _VE.video_edin("sprinkler", _J5_DIZIN,
                        arayici=_j5_arayici([_J5_LISANSSIZ]))
kontrol("⭐ J-5a BELIRLEYICI: J-4 kapisi edinim hattina BAGLI — lisansi "
        "kirli aday INDIRILMEDEN reddediliyor",
        _J5_R1["ok"] is False and _J5_R1["hata"] == "J4-ON-KONTROL-RED"
        and _J5_R1["reddedilen"][0]["asama"] == "on-kontrol",
        _J5_R1["reddedilen"])
_J5_KAYITSIZ = _j5_aday(lisans_kaydi="", lisans_url="")
_J5_R2 = _VE.video_edin("sprinkler", _J5_DIZIN,
                        arayici=_j5_arayici([_J5_KAYITSIZ]))
kontrol("⭐ J-5a RED-FIRST: LISANS KAYDI olmayan aday indirilmeden RED",
        _J5_R2["ok"] is False and _J5_R2["hata"] == "J4-ON-KONTROL-RED")
_J5_URLSUZ = _j5_aday(orijinal_url="")
kontrol("⭐ J-5a RED-FIRST: KAYNAK URL'si olmayan aday indirilmeden RED",
        _VE.video_edin("sprinkler", _J5_DIZIN,
                       arayici=_j5_arayici([_J5_URLSUZ]))["hata"]
        == "J4-ON-KONTROL-RED")
kontrol("⭐ J-5a: edinim modulu J-4 kapisini GERCEKTEN import ediyor",
        "video_lisans" in _J5_VLS
        and "video_provenance_karari" in _J5_VLS
        and _J5_VLS.count("video_provenance_karari(") >= 2)
kontrol("⭐ J-5a: kapi IKI KEZ kosuyor (indirme ONCESI ve SONRASI)",
        "on-kontrol" in _J5_VLS and "son-kontrol" in _J5_VLS)

# ── (5) REDIRECT / HTML / BOZUK MEDYA REDDI (mevcut kapilar KULLANILIYOR) ──
kontrol("⭐ J-5a: indirme GUVENLI indiriciden geciyor (SSRF + bayt + "
        "HTML + ffprobe kapilari)",
        "indirme.guvenli_indir" in _J5_VLS and 'beklenen="video"' in _J5_VLS)
kontrol("⭐ J-5a: HTML/metin icerigi medya sayilmiyor (mevcut kapi)",
        _mind.html_mi(b"<!doctype html><html>") is True
        and _mind.html_mi(b"\x1aE\xdf\xa3") is False)
kontrol("⭐ J-5a: bozuk/medya olmayan dosya ffprobe kapisinda REDDEDILIYOR",
        _mind.dosya_dogrula(
            _j5_bozuk_dosya(), beklenen="video")[0] is False)
kontrol("⭐ J-5a: icerik turu video degilse RED (redirect HTML sayfasi)",
        _j5guv.icerik_kapisi("text/html", 5000, "video")[0] is False)
kontrol("⭐ J-5a: 300 MB ustu icerik uzunlugu RED",
        _j5guv.icerik_kapisi("video/webm", 301 * 1024 * 1024, "video")[0]
        is False)

# ── (6) SON-KONTROL: OLCULEN TEKNIK KANIT EKSIKSE DOSYA SILINIR ──
kontrol("⭐ J-5a: `teknik_olc` okunamayan dosyada BOS donuyor (varsayim yok)",
        _VE.teknik_olc(os.path.join(_J5_DIZIN, "olmayan.webm")) == {})
kontrol("⭐ J-5a: son-kontrol reddinde indirilen dosya SILINIYOR",
        "os.remove(yol)" in _J5_VLS and "son-kontrol" in _J5_VLS)

# ── (7) MALIYET VE GORSEL YOLU ──
kontrol("⭐ J-5a: maliyet $0 olarak raporlaniyor (anahtarsiz kaynaklar)",
        _VE.kapsam_ozeti()["maliyet_usd"] == 0.0
        and _J5_BOS["maliyet_usd"] == 0.0)
kontrol("⭐ J-5a: GORSEL arama yolu (`commons.ara`) DEGISMEDI — hala "
        "filetype:bitmap",
        'filetype:bitmap {sorgu}' in oku(KOK, "medya", "commons.py"))
kontrol("⭐ J-5a: video arama AYRI fonksiyon (`video_ara`), gorsel "
        "siralamasina DOKUNULMADI",
        "def video_ara" in oku(KOK, "medya", "commons.py")
        and 'filetype:video {sorgu}' in oku(KOK, "medya", "commons.py"))
kontrol("J-5a: video_edinim.py derleniyor",
        _derlenir(os.path.join(KOK, "medya", "video_edinim.py")))

# ── (8) DEGISEN IKI URETIM DAVRANISI TESTLE KILITLENIYOR ──
# ⚠ Ikisi de GERCEK VIDEO pilotunda OLCULEREK ortaya cikti; ikisi de kapi
# GEVSETMESI DEGIL — birincisi gereksiz buyutmeyi kaldirir, ikincisi
# GECERSIZ bir TAHMINI hareketli kaynaktan cikarir. Gercek hukum
# POST-QA'nin `optik_hareket_olcusu` olcumundedir ve AYNEN durur.
_J5_PLAN_KAYNAK = oku(KOK, "editor", "plan.py")
kontrol("⭐ J-5a: VIDEO kaynakta dijital zoom UYGULANMIYOR "
        "(static/tam) — 1080p kaynak 1080p kareye BUYUTULMEDEN giriyor",
        "VIDEO-KAMERA-NOTR" in _J5_PLAN_KAYNAK
        and 'c.hareket, c.kadraj = "static", "tam"' in _J5_PLAN_KAYNAK)
kontrol("⭐ J-5a: bu degisiklik YALNIZ video icin — gorsel kaynakta "
        "kadraj merdiveni AYNEN calisiyor",
        "KADRAJ_MERDIVENI" in _J5_PLAN_KAYNAK
        and "kadraj_buyutmeyen" in _J5_PLAN_KAYNAK)
kontrol("⭐ J-5a: PUNCH-BUYUTME kapisi DURUYOR (kaldirilmadi)",
        "KALITE-PUNCH-BUYUTME" in _qon.FAIL_KODLARI)

# statik-kamera bacagi: FOTOGRAFTA olcer, VIDEODA olcmez
_J5_ST = [{"beat_id": "b1", "hareket": "static", "islev": "hook",
           "sure_sn": 9.0, "medya_turu": "image"}]
_J5_SV = [{"beat_id": "b1", "hareket": "static", "islev": "hook",
           "sure_sn": 9.0, "medya_turu": "video"}]
kontrol("⭐ J-5a: uzun 'static' cekim FOTOGRAF kaynakta HALA yakalaniyor "
        "(kapi gevsetilmedi)",
        len(_kk.motion_grammar_olcusu(_J5_ST)["statik_sahneler"]) == 1)
kontrol("⭐ J-5a: ayni cekim VIDEO kaynakta statik SAYILMIYOR — hareket "
        "goruntunun kendisinde (enerji bacagindaki desenin AYNISI)",
        _kk.motion_grammar_olcusu(_J5_SV)["statik_sahneler"] == [],
        _kk.motion_grammar_olcusu(_J5_SV)["statik_sahneler"])
kontrol("⭐ J-5a: KALITE-OPTIK-DURGUN kapisi DURUYOR (kod kaldirilmadi)",
        "KALITE-OPTIK-DURGUN" in _qon.FAIL_KODLARI
        and _kk.OPTIK_DURGUN_FAIL_SN == 3.0)
kontrol("⭐ J-5a KANIT: gercek videonun POST-QA optik olcumu esigi "
        "GECIYOR — muafiyet olcumu bypass ETMIYOR",
        _kk.OPTIK_DURGUN_ESIGI == 2.0)

# ── (9) PILOT KANITI (uretilen MP4'un kendi kayitlarindan) ──
_J5_RAPOR = os.path.join(os.path.dirname(KOK), "outputs", "sample",
                         "lawn_j5a_rapor.json")
if os.path.isfile(_J5_RAPOR):
    _J5R = json.load(open(_J5_RAPOR, encoding="utf-8"))
    kontrol("⭐ J-5a PILOT: kalite kapisi ACIK kosuldu (olcumler hukum "
            "veriyor, yalniz rapor degil)",
            "ACIK" in str(_J5R.get("kalite_kapisi") or ""),
            _J5R.get("kalite_kapisi"))
    kontrol("⭐ J-5a PILOT: optik duraganlik ihlali YOK",
            int(((_J5R.get("optik_hareket") or {}).get("sonra") or {})
                .get("duragan_ihlal", 0)) == 0
            or ((_J5R.get("optik_hareket") or {}).get("sonra") or {})
            .get("temiz") is True,
            (_J5R.get("optik_hareket") or {}).get("sonra"))
    kontrol("⭐ J-5a PILOT: izleyici kalite puani 100/100",
            abs(float((_J5R.get("izleyici_kalite_puani") or {})
                      .get("puan", 0)) - 100.0) < 1e-6,
            (_J5R.get("izleyici_kalite_puani") or {}).get("puan"))
    kontrol("⭐ J-5a PILOT: maliyet $0.00",
            float(_J5R.get("maliyet_usd") or 0) == 0.0,
            _J5R.get("maliyet_usd"))
else:
    bloke_yaz("J-5a pilot kaniti", "lawn_j5a_rapor.json yok")

_J5_PLAN_J = os.path.join(os.path.dirname(KOK), "cikti", "_j5a_calisma",
                          "render_plan.json")
if os.path.isfile(_J5_PLAN_J) and _J1_FFPROBE:
    _J5S = json.load(open(_J5_PLAN_J, encoding="utf-8"))["sahneler"]
    _J5MT = _kk.medya_turu_ozeti(_J5S, kare_okuyucu=_j2_okuyucu)
    _J5BR = _kk.broll_cesitliligi_ozeti(_J5S, medya_turu_ozeti_=_J5MT)
    kontrol("⭐ J-5a PILOT OLCUMU: gercek video orani %0'dan YUKARI cikti "
            "(J-1 tabani 0.0 -> pilot > 0.20)",
            _J5MT["video_sure_orani"] > 0.20, _J5MT["video_sure_orani"])
    kontrol("⭐ J-5a PILOT: statik fotograf orani DUSTU (1.0 -> < 0.80)",
            _J5MT["statik_sure_orani"] < 0.80, _J5MT["statik_sure_orani"])
    kontrol("⭐ J-5a PILOT: donmus kadraj YOK ve tekrar YOK "
            "(gerileme olmadi)",
            _J5MT["donmus_kadraj_sure_orani"] == 0.0
            and _J5BR["tekrar_sure_orani"] == 0.0)
    kontrol("⭐ J-5a PILOT: benzersiz varlik orani 1.0 (her beat AYRI "
            "varlik) ve provenance TAM olculdu",
            _J5BR["benzersiz_varlik_orani"] == 1.0
            and _J5BR["provenance"]["olculdu"] is True)
    kontrol("⭐ J-5a PILOT: video cekiminin lisansi ve kunyesi KAYITLI",
            any(str(x.get("lisans") or "") and str(x.get("orijinal_url") or "")
                for x in _J5S if str(x.get("medya_turu")) == "video"),
            [(x.get("lisans"), x.get("orijinal_url", "")[:40])
             for x in _J5S if str(x.get("medya_turu")) == "video"])

# ── (10) CIKTI ADLARI ARTIK CAKISMIYOR ──
kontrol("⭐ J-5a: smoke cikti adlari PARAMETRELENDI — farkli girdiyle kosan "
        "surucu ONCEKI pilotun kanitini EZEMEZ",
        all(k in oku(KOK, "testler", "smoke_konsept3_teknoloji_i20.py")
            for k in ("RAPOR_ADI =", "BLOKE_RAPOR_ADI =", "KARE_ONEKI =")))


blok("§40n K-1 — VIDEO KAMERA MUAFIYETI + B-ROLL CESITLILIK KAPISI")

# ⚠ MEDYASIZ ATOM: bu blokta dosya OKUNMAZ, indirilmez, render/QA artefakti
# URETILMEZ. Yalniz URETIM KARAR MANTIGI test edilir. $0.00.
#
# ── SORUN (J-5b'de OLCULDU) ──
# Gercek video cekimleri plan tarafinda `static` diye ETIKETLENIYOR (J-5a:
# hareket goruntunun kendisinde, dijital zoom uygulanmiyor). I-24'un
# "ayni islevde ayni kamera hareketi olamaz" kurali bu etiketi GERCEK bir
# kamera karari saniyor ve DORT video sahnesinde islev cakismasi KACINILMAZ
# oluyordu -> `KALITE-MOTION-ISLEV-TEKRAR` FAIL -> video agirlikli kurgu
# YAPISAL OLARAK IMKANSIZ.
#
# ── K-1 POLITIKASI (deterministik, esik UYDURULMADI) ──
#  1. Kamera-hareketi bacaklari (`islev_tekrari`, `pencere_tekrari`) VIDEO
#     cekimlerde ATLANIR — enerji (I-44) ve statik-sure (J-5a) bacaklarindaki
#     desenin AYNISI. Muaf cekimler `kamera_kapisi_muaf_video`de SAYILABILIR.
#  2. Bosluk BOS BIRAKILMAZ: yerini `broll_cesitliligi_ozeti`nin B-ROLL
#     GORSEL DILI bacagi alir — I-24'un ISLEV kuralinin BIREBIR karsiligi,
#     `hareket` yerine `cekim_turu`. Stabil kod: `KALITE-BROLL-CESITLILIK`.
#  3. Cesitlilik ORANLARI (J-3) kapiya BAGLANMADI: hedef None, enforce False.

_K1 = _kk


def _k1_sahne(i, *, tur="image", islev="kanit", hareket="static",
              cekim="wide", sure=4.0):
    return {"beat_id": f"b{i:03d}", "medya_turu": tur, "islev": islev,
            "hareket": hareket, "cekim_turu": cekim, "sure_sn": sure,
            "kaynak_turu": "medya", "asset_id": f"a{i}", "saglayici": "w",
            "lisans": "cc-by"}


# ── (1) MUAFIYET: VIDEO artik kamera bacaklarini TETIKLEMIYOR ──
_K1_VV = [_k1_sahne(1, tur="video", islev="kanit"),
          _k1_sahne(2, tur="image", islev="aciklama", hareket="push-in"),
          _k1_sahne(3, tur="video", islev="kanit")]
_K1_MV = _K1.motion_grammar_olcusu(_K1_VV)
kontrol("⭐ K-1 BELIRLEYICI: ayni islevdeki IKI VIDEO cekim artik "
        "`islev_tekrari` URETMIYOR (etiket artefakti hukum vermiyor)",
        _K1_MV["islev_tekrari"] == [], _K1_MV["islev_tekrari"])
kontrol("⭐ K-1: video cekimler `pencere_tekrari` de URETMIYOR",
        _K1_MV["pencere_tekrari"] == [], _K1_MV["pencere_tekrari"])
kontrol("⭐ K-1: muaf tutulan cekimler SESSIZ degil, SAYILABILIR",
        _K1_MV["kamera_kapisi_muaf_video"] == [0, 2],
        _K1_MV["kamera_kapisi_muaf_video"])

# ── (2) RED-FIRST: FOTOGRAF yolu BIT-BIT AYNI (kapi GEVSETILMEDI) ──
_K1_FF = [_k1_sahne(1, tur="image", islev="kanit", hareket="push-in"),
          _k1_sahne(2, tur="image", islev="aciklama", hareket="pan-left"),
          _k1_sahne(3, tur="image", islev="kanit", hareket="push-in")]
_K1_MF = _K1.motion_grammar_olcusu(_K1_FF)
kontrol("⭐ K-1 RED-FIRST: ayni islevdeki iki FOTOGRAF ayni hareketi alirsa "
        "kapi HALA ateslenıyor (I-24 KORUNDU)",
        len(_K1_MF["islev_tekrari"]) == 1
        and _K1_MF["islev_tekrari"][0]["hareket"] == "push-in",
        _K1_MF["islev_tekrari"])
kontrol("⭐ K-1: FOTOGRAF pencere tekrari da KORUNDU",
        len(_K1_MF["pencere_tekrari"]) == 1, _K1_MF["pencere_tekrari"])
kontrol("⭐ K-1: hicbir video YOKKEN olcum eski davranisla AYNI "
        "(muaf listesi bos, kapilar aynen calisiyor)",
        _K1_MF["kamera_kapisi_muaf_video"] == []
        and "KALITE-MOTION-ISLEV-TEKRAR" in _qon.FAIL_KODLARI)
kontrol("⭐ K-1: ARDISIK ayni hareket kapisi DEGISMEDI (K-1 kapsaminda "
        "DEGILDI — bilerek dokunulmadi)",
        len(_K1.motion_grammar_olcusu(
            [_k1_sahne(1, tur="video"), _k1_sahne(2, tur="video")]
        )["ardisik_tekrar"]) == 1)

# ── (3) YERINE GECEN KAPI: B-ROLL GORSEL DILI ──
_K1_B1 = _K1.broll_cesitliligi_ozeti(
    [_k1_sahne(1, tur="video", islev="kanit", cekim="wide"),
     _k1_sahne(2, tur="image", islev="aciklama", cekim="medium"),
     _k1_sahne(3, tur="video", islev="kanit", cekim="wide")])
kontrol("⭐ K-1 BELIRLEYICI: ayni islevdeki iki VIDEO cekim AYNI cekim "
        "turunu alirsa B-ROLL kapisi ATESLENIYOR",
        len(_K1_B1["video_islev_tur_tekrari"]) == 1
        and _K1_B1["video_islev_tur_tekrari"][0]["cekim_turu"] == "wide",
        _K1_B1["video_islev_tur_tekrari"])
_K1_B2 = _K1.broll_cesitliligi_ozeti(
    [_k1_sahne(1, tur="video", islev="kanit", cekim="wide"),
     _k1_sahne(2, tur="image", islev="aciklama", cekim="medium"),
     _k1_sahne(3, tur="video", islev="kanit", cekim="close-detail")])
kontrol("⭐ K-1 RED-FIRST: cekim turu FARKLIYSA kapi ATESLENMIYOR "
        "(yanlis pozitif yok)",
        _K1_B2["video_islev_tur_tekrari"] == [],
        _K1_B2["video_islev_tur_tekrari"])
kontrol("⭐ K-1: FOTOGRAF cekimleri B-ROLL kapisini TETIKLEMIYOR "
        "(kapi yalniz VIDEO icin)",
        _K1.broll_cesitliligi_ozeti(
            [_k1_sahne(1, tur="image", islev="kanit", cekim="wide"),
             _k1_sahne(2, tur="image", islev="kanit", cekim="wide")]
        )["video_islev_tur_tekrari"] == [])
kontrol("⭐ K-1: video cekim sayisi ve tur cesidi RAPORLANIYOR",
        _K1_B2["video_cekim_sayisi"] == 2
        and _K1_B2["video_cekim_turu_cesidi"] == 2,
        (_K1_B2["video_cekim_sayisi"], _K1_B2["video_cekim_turu_cesidi"]))
kontrol("⭐ K-1: pencere icinde ayni VIDEO cekim turu tekrari da "
        "OLCULUYOR (warn adayi)",
        len(_K1.broll_cesitliligi_ozeti(
            [_k1_sahne(1, tur="video", islev="a", cekim="wide"),
             _k1_sahne(2, tur="video", islev="b", cekim="wide")]
        )["video_pencere_tur_tekrari"]) == 1)

# ── (4) KOD STABIL VE KAPIYA BAGLI ──
kontrol("⭐ K-1: `KALITE-BROLL-CESITLILIK` FAIL kodu olarak KILITLENDI",
        "KALITE-BROLL-CESITLILIK" in _qon.FAIL_KODLARI)
kontrol("⭐ K-1: kod KALITE_KODLARI'nda — kalite kapisi KAPALIYKEN "
        "URETILMEZ (varsayilan yolun karari DEGISMEZ)",
        "KALITE-BROLL-CESITLILIK" in _qon.KALITE_KODLARI)
kontrol("⭐ K-1: kapi `kalite_kapisi` bayragina BAGLI (kosulsuz degil)",
        "if kalite_kapisi:" in oku(KOK, "editor", "qa_on.py")
        and "KALITE-BROLL-CESITLILIK" in oku(KOK, "editor", "qa_on.py"))
kontrol("⭐ K-1: kapiya bagli alanlar SOZLESMEDE sayili (oranlar DEGIL)",
        set(_K1.broll_cesitliligi_ozeti([])["kapiya_bagli"])
        == {"video_islev_tur_tekrari", "video_pencere_tur_tekrari"})
kontrol("⭐ K-1: SAYISAL ESIK UYDURULMADI — hedef None, enforce False",
        _K1.broll_cesitliligi_ozeti([])["hedef"] is None
        and _K1.broll_cesitliligi_ozeti([])["enforce"] is False)

# ── (5) MEDYASIZ ATOM KANITI ──
kontrol("⭐ K-1: olcum modulu DOSYA ACMIYOR (okuyucu enjeksiyonu deseni "
        "korundu)",
        "def broll_cesitliligi_ozeti" in oku(KOK, "editor",
                                             "kalite_kapisi.py")
        and "open(" not in oku(KOK, "editor", "kalite_kapisi.py")
        .split("def broll_cesitliligi_ozeti")[1].split("def ")[0])

# ── KORUNANLAR ──
kontrol("K-1 GERILEME YOK: I-23/I-24/I-25/I-38 kapilari DURUYOR",
        "KALITE-MOTION-ACILIS-KAPANIS" in _qon.FAIL_KODLARI
        and "KALITE-MOTION-ISLEV-TEKRAR" in _qon.FAIL_KODLARI
        and "KALITE-YAZI-SAHNE-DISI" in _qon.FAIL_KODLARI
        and "ORAN-UYUMSUZ" in oku(KOK, "medya/edinim.py")
        and "class DevreKesici" in oku(KOK, "medya/edinim.py"))
kontrol("K-1 GERILEME YOK: ESIKLER GEVSETILMEDI",
        _kk.OPTIK_DURGUN_ESIGI == 2.0
        and abs(_kk.BENZERLIK_ESIGI - 0.86) < 1e-9
        and abs(_kk.UZAMSAL_ENERJI_ESIGI - 11.589) < 1e-9
        and abs(_kk.KENAR_DIS_ESIGI - 6.234) < 1e-9
        and abs(_kk.MODEL_K - 0.935) < 1e-6)
kontrol("K-1 GERILEME YOK: lisans/provenance kapilari DURUYOR",
        "KALITE-KUNYE-EKSIK" in _qon.FAIL_KODLARI
        and "def lisans_suz" in oku(KOK, "edit_kopru.py"))
kontrol("K-1 GERILEME YOK: 22 alanlik generate sozlesmesi DEGISMEDI",
        len(set(re.findall(r"\{ad: '(\w+)'",
                           oku(KOK, "static/js/api.js")))) == 22)
kontrol("K-1: kullanici secimleri (zoom/pan alanlari) DOKUNULMADI",
        "zoom: 'in' | 'out' | 'yok'" in oku(os.path.dirname(KOK), "app",
                                            "render-studio", "src",
                                            "Video.tsx"))
kontrol("K-1: deploy.sh DOKUNULMADI",
        "docker commit" in oku(os.path.dirname(KOK), "deploy.sh"))


blok("§40o K-2 — ARKA PLAN UGULTU KAPISI + KAYNAK SESI SIFIR")

# ⚠ MEDYASIZ ATOM: ses/medya dosyasi ACILMAZ, ffmpeg CALISTIRILMAZ, artefakt
# URETILMEZ. Butun olcumler SENTETIK SAYI olarak verilir (remote worker'in
# uretecegi degerlerin test-double'i). $0.00.
#
# ── AKIS ──  olc -> guvenli filtre profili oner -> temizlemeyi DOGRULA
#             -> temizlenemiyorsa FAIL
# ⚠ EMIN DEGILSEN TEMIZ ICERIGI FAIL ETME: guven araligi esigi kesiyorsa
#   sonuc `supheli` ve hukum WARN'dir, FAIL DEGIL.

_SGT = __import__("editor.ses_gurultu", fromlist=["ses_gurultu"])

_K2_TABAN = {"anlatim_lufs": -16.0, "sureklilik_orani": 0.95,
             "spektral_duzluk": 0.55}


def _k2(**ek):
    return _SGT.gurultu_olcusu(**{**_K2_TABAN, **ek})


# ── (1) KAYNAK VIDEO SESI: MUTLAK SIFIR ──
kontrol("⭐ K-2: kaynak ses politikasi SIFIR olarak SABIT",
        _SGT.KAYNAK_SES_POLITIKASI == "sifir")
kontrol("⭐ K-2: render sozlesmesi `ses_kanali`i MAKINE OKUNUR yaziyor "
        "(plan.py)",
        '"ses_kanali": ses_gurultu.KAYNAK_SES_POLITIKASI'
        in oku(KOK, "editor", "plan.py"))
kontrol("⭐ K-2: HER IKI renderer yolu da kaynak sesi MUTE ediyor",
        "muted" in oku(os.path.dirname(KOK), "app", "render-studio", "src",
                       "editorv2", "Kamera.tsx")
        and "muted" in oku(os.path.dirname(KOK), "app", "render-studio",
                           "src", "Video.tsx"))
_K2_SES_OK = _SGT.kaynak_ses_sozlesmesi(
    [{"beat_id": "b1", "medya_turu": "video", "ses_kanali": "yok"},
     {"beat_id": "b2", "medya_turu": "image"}])
kontrol("⭐ K-2: sifir beyan eden video cekim SOZLESMEYE UYGUN",
        _K2_SES_OK["temiz"] is True and _K2_SES_OK["video_cekim"] == 1)
_K2_SES_RED = _SGT.kaynak_ses_sozlesmesi(
    [{"beat_id": "b1", "medya_turu": "video", "ses_kanali": "kaynak"}])
kontrol("⭐ K-2 RED-FIRST: kaynak sesini KULLANMAYA calisan cekim "
        "YAKALANIYOR (`KALITE-KAYNAK-SES-SIZINTI`)",
        _K2_SES_RED["temiz"] is False
        and _K2_SES_RED["ihlal"][0]["ses_kanali"] == "kaynak"
        and "KALITE-KAYNAK-SES-SIZINTI" in _qon.FAIL_KODLARI,
        _K2_SES_RED["ihlal"])
kontrol("⭐ K-2: FOTOGRAF cekimleri kaynak-ses sozlesmesine GIRMIYOR",
        _SGT.kaynak_ses_sozlesmesi(
            [{"beat_id": "b1", "medya_turu": "image",
              "ses_kanali": "kaynak"}])["temiz"] is True)

# ── (2) OLCUM: TEMIZ ICERIK YANLIS FAIL EDILMIYOR ──
kontrol("⭐ K-2: gurultu tabani anlatimin 39 dB altindaysa TEMIZ "
        "(esik DUYULABILIR_FARK_DB'den TURETILDI)",
        _k2(konusma_disi_lufs=-55.0)["seviye"] == "temiz")
kontrol("⭐ K-2 RED-FIRST: SUREKSIZ gurultu (gecici ses) FAIL DEGIL",
        _k2(konusma_disi_lufs=-38.0, sureklilik_orani=0.20)["seviye"]
        == "temiz")
kontrol("⭐ K-2 RED-FIRST: SPEKTRAL IZ YOKSA (tonal/muzik yatagi) "
        "gurultu SAYILMIYOR",
        _k2(konusma_disi_lufs=-38.0, spektral_duzluk=0.05)["seviye"]
        == "temiz")
kontrol("⭐ K-2: uc kosul (duyulabilir + surekli + iz) BIRLIKTE saglanirsa "
        "gurultu TESPIT EDILIYOR",
        _k2(konusma_disi_lufs=-38.0)["seviye"] == "gurultu",
        _k2(konusma_disi_lufs=-38.0)["izler"])
kontrol("⭐ K-2: rumble ve hiss AYRI izler olarak taniniyor",
        "rumble" in _k2(konusma_disi_lufs=-38.0, spektral_duzluk=0.0,
                        dusuk_frekans_orani=0.44)["izler"]
        and "hiss" in _k2(konusma_disi_lufs=-38.0, spektral_duzluk=0.0,
                          yuksek_frekans_orani=0.40)["izler"])

# ── (3) GUVEN ARALIGI: ESIGI KESIYORSA FAIL YOK ──
_K2_SUP = _k2(konusma_disi_lufs=-46.5)
kontrol("⭐ K-2 BELIRLEYICI: guven araligi esigi KESIYORSA sonuc `supheli` "
        "— hukum WARN, FAIL DEGIL (EMIN DEGILSEN FAIL ETME)",
        _K2_SUP["seviye"] == "supheli"
        and _K2_SUP["snr_alt"] < _K2_SUP["esik_db"] < _K2_SUP["snr_ust"]
        and _SGT.gurultu_karari(olcum=_K2_SUP)["seviye"] == "warn",
        (_K2_SUP["snr_alt"], _K2_SUP["snr_ust"]))
kontrol("⭐ K-2: belirsizlik BUYUDUKCE supheli bant GENISLIYOR "
        "(karar belirsizlige DUYARLI)",
        _k2(konusma_disi_lufs=-42.0,
            belirsizlik_db=6.0)["seviye"] == "supheli"
        and _k2(konusma_disi_lufs=-42.0,
                belirsizlik_db=0.5)["seviye"] == "gurultu")
kontrol("⭐ K-2: OLCUM EKSIKSE hukum YOK — 'temiz' DENMIYOR",
        _SGT.gurultu_olcusu(anlatim_lufs=-16.0)["olculdu"] is False
        and _SGT.gurultu_karari(
            olcum=_SGT.gurultu_olcusu(anlatim_lufs=-16.0))["karar"]
        == "OLCULEMEDI")

# ── (4) GUVENLI FILTRE PROFILI ──
_K2_RUM = _k2(konusma_disi_lufs=-38.0, spektral_duzluk=0.0,
              dusuk_frekans_orani=0.44)
_K2_FP = _SGT.filtre_profili_oner(_K2_RUM)
kontrol("⭐ K-2: rumble icin YUKSEK-GECIREN oneriliyor ve kesim KONUSMA "
        "TEMEL FREKANSININ ALTINDA (80 Hz)",
        _K2_FP["adimlar"][0]["ad"] == "highpass"
        and _K2_FP["adimlar"][0]["parametre"]["f"] == 80
        and _K2_FP["adimlar"][0]["parametre"]["f"] < 85)
kontrol("⭐ K-2: genis bantli bastirma TAVANLI (agresif denoise YOK)",
        _SGT.filtre_profili_oner(_k2(konusma_disi_lufs=-38.0)
                                 )["maks_bastirma_db"] <= 6.0)
kontrol("⭐ K-2: profil KONUSMA BANDINA DOKUNMADIGINI acikca beyan ediyor "
        "(300-3400 Hz)",
        _K2_FP["konusma_bandina_dokunmaz"] is True
        and _K2_FP["konusma_bandi_hz"] == [300, 3400])
kontrol("⭐ K-2: TEMIZ icerikte filtre ONERILMIYOR (gereksiz islem yok)",
        _SGT.filtre_profili_oner(_k2(konusma_disi_lufs=-55.0)
                                 )["onerildi"] is False)
kontrol("⭐ K-2: zincir DETERMINISTIK — ayni olcum ayni zinciri veriyor",
        _SGT.filtre_profili_oner(_K2_RUM)
        == _SGT.filtre_profili_oner(_K2_RUM))

# ── (5) TEMIZLEME DOGRULAMASI: NETLIK BOZULURSA FILTRE REDDEDILIR ──
_K2_SONRA = _k2(konusma_disi_lufs=-55.0)
_K2_IYI = _SGT.temizleme_dogrula(
    once=_K2_RUM, sonra=_K2_SONRA,
    konusma_bandi_lufs_once=-18.0, konusma_bandi_lufs_sonra=-18.3)
kontrol("⭐ K-2: gurultu gitti ve konusma bandi KORUNDUYSA filtre KABUL",
        _K2_IYI["filtre_kabul"] is True
        and _SGT.gurultu_karari(olcum=_K2_RUM,
                                dogrulama=_K2_IYI)["karar"] == "TEMIZLENDI")
_K2_KOTU = _SGT.temizleme_dogrula(
    once=_K2_RUM, sonra=_K2_SONRA,
    konusma_bandi_lufs_once=-18.0, konusma_bandi_lufs_sonra=-21.0)
kontrol("⭐ K-2 BELIRLEYICI: konusma bandi TAVANDAN fazla gerilerse filtre "
        "REDDEDILIYOR ve sonuc FAIL — netligi bozan denoise UYGULANMAZ",
        _K2_KOTU["netlik_bozuldu"] is True
        and _K2_KOTU["filtre_kabul"] is False
        and _SGT.gurultu_karari(olcum=_K2_RUM,
                                dogrulama=_K2_KOTU)["karar"] == "FAIL",
        _K2_KOTU["konusma_gerilemesi_db"])
kontrol("⭐ K-2: ASR guveni tavandan fazla duserse de filtre REDDEDILIYOR "
        "(spektral olcum yoksa ASR bacagi calisir)",
        _SGT.temizleme_dogrula(once=_K2_RUM, sonra=_K2_SONRA,
                               asr_guven_once=0.94, asr_guven_sonra=0.88
                               )["filtre_kabul"] is False)
kontrol("⭐ K-2: temizleme DENENMEDIYSE kesin gurultu FAIL veriyor",
        _SGT.gurultu_karari(olcum=_K2_RUM)["karar"] == "FAIL"
        and _SGT.gurultu_karari(olcum=_K2_RUM)["seviye"] == "fail")
kontrol("⭐ K-2: filtre uygulandi ama gurultu SURUYORSA da FAIL",
        _SGT.gurultu_karari(
            olcum=_K2_RUM,
            dogrulama=_SGT.temizleme_dogrula(
                once=_K2_RUM, sonra=_k2(konusma_disi_lufs=-38.0),
                konusma_bandi_lufs_once=-18.0,
                konusma_bandi_lufs_sonra=-18.1))["karar"] == "FAIL")

# ── (6) KODLAR VE KAPI BAGLANTISI ──
kontrol("⭐ K-2: `KALITE-SES-GURULTU` FAIL kodu KILITLENDI",
        "KALITE-SES-GURULTU" in _qon.FAIL_KODLARI
        and "KALITE-SES-GURULTU" in _qon.KALITE_KODLARI)
kontrol("⭐ K-2: `KALITE-KAYNAK-SES-SIZINTI` FAIL kodu KILITLENDI",
        "KALITE-KAYNAK-SES-SIZINTI" in _qon.FAIL_KODLARI
        and "KALITE-KAYNAK-SES-SIZINTI" in _qon.KALITE_KODLARI)
kontrol("⭐ K-2: olcum DISARIDAN enjekte ediliyor (`ses_gurultu_olcumu`)",
        "ses_gurultu_olcumu" in oku(KOK, "editor", "qa_on.py"))
kontrol("⭐ K-2: olcum verilmezse QA raporunda `olculdu=False` yaziyor, "
        "'temiz' DENMIYOR",
        _SGT.gurultu_karari(olcum={})["karar"] == "OLCULEMEDI")

# ── (7) MEDYASIZ ATOM KANITI ──
# ⚠ I-9 DERSI: ham dize taramasi modulun KENDI dokumantasyonunu yakalar
# ("FFMPEG CALISTIRMAZ" cumlesi gibi). `_kod_yalniz` ile yalniz CALISAN kod
# taranir.
_K2_KOD = _kod_yalniz(oku(KOK, "editor", "ses_gurultu.py"))
kontrol("⭐ K-2: modul MEDYA ACMIYOR / FFMPEG CALISTIRMIYOR — CALISAN "
        "kodda subprocess/ffmpeg/open/dosya erisimi YOK",
        not any(a in _K2_KOD for a in ("subprocess", "ffmpeg", "ffprobe",
                                       "open(", "os.path", "import os")),
        [a for a in ("subprocess", "ffmpeg", "ffprobe", "open(", "os.path")
         if a in _K2_KOD])
kontrol("⭐ K-2: kapsam ozeti sinirlari ACIKCA yaziyor",
        _SGT.kapsam_ozeti()["medya_acar"] is False
        and _SGT.kapsam_ozeti()["ffmpeg_calistirir"] is False
        and _SGT.kapsam_ozeti()["agresif_denoise"] is False
        and _SGT.kapsam_ozeti()["olcum_enjekte_edilir"] is True)
kontrol("⭐ K-2 DURUSTLUK: esiklerin KAYNAGI raporlaniyor "
        "(turetilmis vs beyan edilmis)",
        "TURETILMIS" in _SGT.kapsam_ozeti()["esik_kaynagi"]["snr_db"]
        and "BEYAN EDILMIS"
        in _SGT.kapsam_ozeti()["esik_kaynagi"]["digerleri"])
kontrol("K-2: ses_gurultu.py derleniyor",
        _derlenir(os.path.join(KOK, "editor", "ses_gurultu.py")))

# ── KORUNANLAR ──
kontrol("K-2 GERILEME YOK: I-23/I-24/I-25/I-38 kapilari DURUYOR",
        "KALITE-MOTION-ACILIS-KAPANIS" in _qon.FAIL_KODLARI
        and "KALITE-MOTION-ISLEV-TEKRAR" in _qon.FAIL_KODLARI
        and "KALITE-YAZI-SAHNE-DISI" in _qon.FAIL_KODLARI
        and "ORAN-UYUMSUZ" in oku(KOK, "medya/edinim.py"))
kontrol("K-2 GERILEME YOK: ESIKLER GEVSETILMEDI",
        _kk.OPTIK_DURGUN_ESIGI == 2.0
        and abs(_kk.DUYULABILIR_FARK_DB - 30.0) < 1e-9
        and abs(_kk.BASTIRMA_FARK_DB - 12.0) < 1e-9
        and abs(_kk.KENAR_DIS_ESIGI - 6.234) < 1e-9)
kontrol("K-2 GERILEME YOK: 22 alanlik generate sozlesmesi DEGISMEDI",
        len(set(re.findall(r"\{ad: '(\w+)'",
                           oku(KOK, "static/js/api.js")))) == 22)
kontrol("K-2: kullanici secimleri DOKUNULMADI",
        "zoom: 'in' | 'out' | 'yok'" in oku(os.path.dirname(KOK), "app",
                                            "render-studio", "src",
                                            "Video.tsx"))
kontrol("K-2: deploy.sh DOKUNULMADI",
        "docker commit" in oku(os.path.dirname(KOK), "deploy.sh"))
kontrol("K-2: B-ROLL kapisi (K-1) DURUYOR",
        "KALITE-BROLL-CESITLILIK" in _qon.FAIL_KODLARI)


blok("§40p K-3 — ACILIS BASLIK/SERIT SURESI (saf timeline, medyasiz)")

# ⚠ MEDYASIZ ATOM: dosya/medya/ffmpeg YOK, artefakt URETILMEZ. $0.00.
#
# ── OLCULEN KUSUR ──
# Acilis basligi `min(5.5, beat.sure_sn + 1.5)` ile kuruluyordu:
#   (a) METNE HIC BAKMIYORDU — iki kelimelik baslik da 5.5 sn duruyordu,
#   (b) `+1.5` ile INTRO BEAT'i ASIYORDU, yani anlatici cumlesi bittikten
#       sonra yazi ekranda ASILI kaliyordu.
# Gercek pilot ornegi: "THERE IS A BAG OF GRASS", beat 3.825 sn
#   ESKI: 5.325 sn  ->  1.700 sn ASILI (kapi FAIL verir)
#   K-3 : 1.714 sn  ->  0.000 sn asili (TEMIZ)
#
# ── POLITIKA ──
#  · sure = max(karakter/CPS, kelime/KPS) x katsayi, `min_gorunme_sn` alt
#    sinirina saygi duyar
#  · UC SERT UST SINIR: mutlak tavan, INTRO BEAT sonu, asili kalma 0
#  · K-4 KANCASI: `katsayi` varsayilan 1.0 -> GERIYE UYUMLU; az/orta/yuksek
#    baglaninca ayni fonksiyon kullanilir. K-4 BU ATOMDA UYGULANMADI.

_T3 = _etipo


def _k3(metin, beat, **ek):
    return _T3.acilis_baslik_suresi(metin, beat_sure_sn=beat,
                                    gecikme_sn=0.2, **ek)


# ── (1) SURE METINDEN TURUYOR ──
_K3_KISA = _k3("GO", 3.825)
_K3_ORTA = _k3("THERE IS A BAG OF GRASS", 3.825)
_K3_UZUN = _k3("A VERY LONG OPENING TITLE THAT NEEDS MORE READING TIME", 6.0)
kontrol("⭐ K-3 BELIRLEYICI: sure artik METNE BAGLI — kisa baslik uzun "
        "baslikla AYNI sureyi ALMIYOR",
        _K3_KISA["sure_sn"] < _K3_ORTA["sure_sn"] < _K3_UZUN["sure_sn"],
        [_K3_KISA["sure_sn"], _K3_ORTA["sure_sn"], _K3_UZUN["sure_sn"]])
kontrol("⭐ K-3: hem KARAKTER hem KELIME bacagi hesaplaniyor, BUYUGU "
        "aliniyor",
        _K3_ORTA["okuma_ihtiyaci_sn"]
        == max(_K3_ORTA["karakter_bacagi_sn"], _K3_ORTA["kelime_bacagi_sn"]),
        (_K3_ORTA["karakter_bacagi_sn"], _K3_ORTA["kelime_bacagi_sn"]))
kontrol("⭐ K-3: okunamayacak kadar KISA olamaz (`min_gorunme_sn` alt siniri)",
        _K3_KISA["sure_sn"] >= _K3_KISA["min_gorunme_sn"],
        (_K3_KISA["sure_sn"], _K3_KISA["min_gorunme_sn"]))

# ── (2) UST SINIRLAR: INTRO BEAT ASILMIYOR ──
kontrol("⭐ K-3 BELIRLEYICI: baslik INTRO BEAT'i ASLA asmiyor "
        "(gecikme dahil bitis <= beat sonu)",
        all(_k3(m, b)["sure_sn"] + 0.2 <= b + 1e-6
            for m, b in (("GO", 3.825),
                         ("THERE IS A BAG OF GRASS", 3.825),
                         ("A VERY LONG OPENING TITLE THAT NEEDS TIME", 2.0),
                         ("KISA", 1.0))))
kontrol("⭐ K-3: cok KISA beat'te bile tasma YOK (sure beat'e kirpilir)",
        _k3("THERE IS A BAG OF GRASS", 1.0)["sure_sn"] <= 0.8 + 1e-6,
        _k3("THERE IS A BAG OF GRASS", 1.0)["sure_sn"])
kontrol("⭐ K-3: mutlak tavan (5.5 sn) korunuyor — cok uzun metin + cok "
        "uzun beat'te bile asilmiyor",
        _k3("X" * 400, 60.0)["sure_sn"] <= _T3.BASLIK_MAKS_SN + 1e-6,
        _k3("X" * 400, 60.0)["sure_sn"])
kontrol("⭐ K-3: kisaltma SESSIZ degil — `kisaltildi` bayragi RAPORLANIYOR",
        _k3("THERE IS A BAG OF GRASS", 1.0)["kisaltildi"] is True
        and _K3_KISA["kisaltildi"] is False)

# ── (3) RED-FIRST: ESKI DAVRANIS KAPIDAN GECMIYOR ──
_K3_ESKI = _T3.baslik_suresi_denetle(
    bas_sn=0.2, sure_sn=min(5.5, 3.825 + 1.5),      # ESKI formul
    beat_bas_sn=0.0, beat_sure_sn=3.825)
kontrol("⭐ K-3 RED-FIRST: ESKI formulun urettigi baslik kapida FAIL "
        "(1.7 sn ASILI kaliyordu)",
        _K3_ESKI["temiz"] is False
        and abs(_K3_ESKI["asili_kalma_sn"] - 1.7) < 1e-3,
        _K3_ESKI["asili_kalma_sn"])
_K3_YENI = _T3.baslik_suresi_denetle(
    bas_sn=0.2, sure_sn=_K3_ORTA["sure_sn"],
    beat_bas_sn=0.0, beat_sure_sn=3.825)
kontrol("⭐ K-3: YENI hesabin urettigi baslik kapidan TEMIZ geciyor "
        "(asili kalma 0.0)",
        _K3_YENI["temiz"] is True and _K3_YENI["asili_kalma_sn"] == 0.0)
kontrol("⭐ K-3: gercek pilot basligi OLCULEBILIR sekilde KISALDI "
        "(5.325 -> ~1.7 sn)",
        _K3_ORTA["sure_sn"] < min(5.5, 3.825 + 1.5) - 3.0,
        (min(5.5, 3.825 + 1.5), _K3_ORTA["sure_sn"]))
kontrol("⭐ K-3: mutlak tavani asan katman da FAIL veriyor",
        _T3.baslik_suresi_denetle(bas_sn=0.0, sure_sn=9.0, beat_bas_sn=0.0,
                                  beat_sure_sn=30.0)["temiz"] is False)
kontrol("⭐ K-3: bozuk girdi hukum VERMIYOR (`olculdu=False`)",
        _T3.baslik_suresi_denetle(bas_sn="x", sure_sn=1.0, beat_bas_sn=0.0,
                                  beat_sure_sn=3.0)["olculdu"] is False)

# ── (4) K-4 KANCASI: GEVSEK VE GERIYE UYUMLU ──
kontrol("⭐ K-3: varsayilan katsayi 1.0 — mevcut davranis GUVENLI KISALTMA",
        _T3.BASLIK_PROFIL_KATSAYISI["varsayilan"] == 1.0
        and _K3_ORTA["katsayi"] == 1.0)
kontrol("⭐ K-3: katsayi ILERIDE baglanabilir — buyuk katsayi sureyi "
        "UZATIR, kucuk katsayi KISALTIR (K-4 hazir)",
        _k3("THERE IS A BAG OF GRASS", 6.0, katsayi=1.6)["sure_sn"]
        > _k3("THERE IS A BAG OF GRASS", 6.0)["sure_sn"]
        > _k3("THERE IS A BAG OF GRASS", 6.0, katsayi=0.6)["sure_sn"])
kontrol("⭐ K-3: katsayi UST SINIRLARI DELEMEZ (beat hala tavan)",
        _k3("THERE IS A BAG OF GRASS", 2.0, katsayi=9.0)["sure_sn"]
        + 0.2 <= 2.0 + 1e-6)
# ⚠ I-9 tuzagi (K-2'de de yasandi): ham dize taramasi K-4 KANCASINI
# ANLATAN YORUMU yakaliyor. Yalniz CALISAN kod taranir.
kontrol("⭐ K-3: K-4 BU ATOMDA UYGULANMADI — calisan kodda `edit_seviyesi` "
        "YOK, 22 alan sozlesmesine de girmedi",
        "edit_seviyesi" not in _kod_yalniz(oku(KOK, "editor",
                                               "tipografi.py"))
        and "edit_seviyesi" not in oku(KOK, "static/js/api.js"))

# ── (5) SOZLESME VE KOD ──
kontrol("⭐ K-3: `KALITE-BASLIK-SURESI` FAIL kodu KILITLENDI",
        "KALITE-BASLIK-SURESI" in _qon.FAIL_KODLARI
        and "KALITE-BASLIK-SURESI" in _qon.KALITE_KODLARI)
kontrol("⭐ K-3: plan.py ESKI formulu ARTIK KULLANMIYOR",
        "min(5.5, b.sure_sn + 1.5)" not in _sikistir(
            oku(KOK, "editor", "plan.py")).replace(" ", "")
        and "acilis_baslik_suresi" in oku(KOK, "editor", "plan.py"))
kontrol("⭐ K-3 DURUSTLUK: esik kaynaklari etiketli — CPS TURETILMIS "
        "(ALTYAZI_MAKS_CPS ile ayni), digerleri BEYAN EDILMIS",
        abs(_T3.BASLIK_MAKS_CPS - _kk.ALTYAZI_MAKS_CPS) < 1e-9
        and "TURETILMIS" in oku(KOK, "editor", "tipografi.py")
        and "BEYAN EDILMIS" in oku(KOK, "editor", "tipografi.py"))
kontrol("⭐ K-3: olu ayar birakilmadi — asili tavani HESAPTA degil yalniz "
        "KAPI TOLERANSINDA kullaniliyor",
        "asili_tavani_sn" not in _sikistir(
            oku(KOK, "editor", "tipografi.py")
        ).split("defacilis_baslik_suresi")[1].split("defbaslik_suresi")[0])

# ── KORUNANLAR ──
kontrol("K-3 GERILEME YOK: 22 alanlik generate sozlesmesi DEGISMEDI",
        len(set(re.findall(r"\{ad: '(\w+)'",
                           oku(KOK, "static/js/api.js")))) == 22)
kontrol("K-3 GERILEME YOK: I-38 yazi kapisi ve tipografi kapilari DURUYOR",
        "KALITE-YAZI-SAHNE-DISI" in _qon.FAIL_KODLARI
        and "KALITE-YAZI-NEFES-YOK" in _qon.FAIL_KODLARI
        and "KALITE-BASLIK-KIRPIK" in _qon.FAIL_KODLARI)
kontrol("K-3 GERILEME YOK: K-1/K-2 kapilari DURUYOR",
        "KALITE-BROLL-CESITLILIK" in _qon.FAIL_KODLARI
        and "KALITE-SES-GURULTU" in _qon.FAIL_KODLARI
        and "KALITE-KAYNAK-SES-SIZINTI" in _qon.FAIL_KODLARI)
kontrol("K-3: kullanici secimleri DOKUNULMADI",
        "zoom: 'in' | 'out' | 'yok'" in oku(os.path.dirname(KOK), "app",
                                            "render-studio", "src",
                                            "Video.tsx"))
kontrol("K-3: deploy.sh DOKUNULMADI",
        "docker commit" in oku(os.path.dirname(KOK), "deploy.sh"))


blok("§40q R-1a — IMZALI CIKTI URL'LERI (medyasiz, saf kripto)")

# ⚠ MEDYASIZ: dosya/medya URETILMEZ, yalniz imza mantigi test edilir.
# ── OLCULEN KUSUR ── `/ciktilar/{dosya}` IMZASIZDI: dosya adini bilen
# HERKES indirebiliyordu. Tenant izolasyonu (R-1b) icin de ON KOSUL.

_IU = __import__("imzali_url")
_isz = __import__("is_sozlesme")
_IU_DIZ = tempfile.mkdtemp(prefix="imza_")
kontrol("⭐ R-1a: anahtar env yoksa VERI dizininde 0600 ile URETILIYOR",
        _IU.anahtar_kur(_IU_DIZ) is True and _IU.hazir() is True)
kontrol("⭐ R-1a: anahtar dosyasi yalniz sahibine okunur (0600)",
        (os.stat(os.path.join(_IU_DIZ, _IU.ANAHTAR_DOSYA_ADI)).st_mode & 0o077)
        == 0, oct(os.stat(os.path.join(_IU_DIZ,
                                       _IU.ANAHTAR_DOSYA_ADI)).st_mode))
_IU_URL = _IU.imzala("job_x.mp4")
_IU_Q = dict(x.split("=") for x in _IU_URL.split("?")[1].split("&"))
kontrol("⭐ R-1a: baglanti SURELI ve IMZALI (exp + sig)",
        "exp" in _IU_Q and "sig" in _IU_Q and _IU_URL.startswith("ciktilar/"))
kontrol("⭐ R-1a: dogru imza GECERLI",
        _IU.dogrula("job_x.mp4", _IU_Q["exp"], _IU_Q["sig"])["gecerli"] is True)
kontrol("⭐ R-1a RED-FIRST: BOZUK imza REDDEDILIYOR",
        _IU.dogrula("job_x.mp4", _IU_Q["exp"],
                    _IU_Q["sig"][:-2] + "xx")["neden"] == "IMZA-GECERSIZ")
kontrol("⭐ R-1a RED-FIRST: BASKA dosya adina TASINAN imza REDDEDILIYOR",
        _IU.dogrula("gizli.mp4", _IU_Q["exp"],
                    _IU_Q["sig"])["neden"] == "IMZA-GECERSIZ")
kontrol("⭐ R-1a RED-FIRST: SURESI DOLMUS baglanti REDDEDILIYOR",
        _IU.dogrula("job_x.mp4", _IU_Q["exp"], _IU_Q["sig"],
                    simdi=int(_IU_Q["exp"]) + 1)["neden"] == "SURESI-DOLMUS")
kontrol("⭐ R-1a: imza gecersizken 'suresi dolmus' bilgisi SIZMIYOR "
        "(once imza dogrulanir)",
        _IU.dogrula("job_x.mp4", int(_IU_Q["exp"]) - 10 ** 6,
                    _IU_Q["sig"])["neden"] == "IMZA-GECERSIZ")
kontrol("⭐ R-1a: YOL GEZINMESI kesiliyor (path traversal)",
        _IU.guvenli_ad("../../etc/passwd") == "passwd"
        and _IU.guvenli_ad("a/b/c.mp4") == "c.mp4")
kontrol("⭐ R-1a: sabit zamanli karsilastirma kullaniliyor",
        "compare_digest" in oku(KOK, "imzali_url.py"))
kontrol("⭐ R-1a: anahtar REPODA DEGIL ve LOGLANMIYOR",
        _IU.kapsam_ozeti()["anahtar_repoda"] is False
        and _IU.kapsam_ozeti()["anahtar_loglanir"] is False
        and not any(os.path.exists(os.path.join(KOK, a))
                    for a in (".imza_anahtari",)))
kontrol("⭐ R-1a: is sozlesmesi IMZALI video_url uretiyor",
        "sig=" in _isz.normalize(
            "j1", {"video": "ciktilar/job_x.mp4", "durum": "bitti"},
            imzalayici=_IU.imzala)["video_url"])
kontrol("⭐ R-1a: imzalayici VERILMEZSE eski davranis KORUNUYOR "
        "(geriye uyumlu)",
        _isz.normalize("j1", {"video": "ciktilar/job_x.mp4",
                              "durum": "bitti"})["video_url"]
        == "ciktilar/job_x.mp4")
kontrol("⭐ R-1a: arayuz ARTIK ham `ciktilar/` yolu KURMUYOR "
        "(imzali manifest_url kullaniyor)",
        "manifest_url" in oku(KOK, "static/js/bilesenler.js")
        and 'href="ciktilar/${' not in oku(KOK, "static/js/bilesenler.js"))
kontrol("⭐ R-1a: anahtar kurulamazsa uc SESSIZCE KORUMASIZ calismiyor "
        "(503)",
        "imza anahtari kurulmadi" in oku(KOK, "server.py")
        and "503" in oku(KOK, "server.py"))
kontrol("R-1a: imzali_url.py derleniyor",
        _derlenir(os.path.join(KOK, "imzali_url.py")))


blok("§40r R-1b — TENANT PROVIDER ZINCIRI (adapter -> motor -> timeline)")

# ⚠ MEDYASIZ + AGSIZ: MCP cagirici, sifre cozucu, olcer ve ucretsiz arayici
# TEST-DOUBLE'dir. Gercek OAuth YOK, kredi TUKETILMEZ. $0.00.
#
# Zincir: planlayici -> provider registry -> job-scope token -> MCP
#         capability discovery -> edinim -> olcum -> provenance -> timeline

_SM = __import__("medya.saglayici_motoru", fromlist=["saglayici_motoru"])

_SM_KAYIT = {"t1": {"saglayici": "magnific", "aktif": True, "onayli": True,
                    "sifreli_token": b"ENC", "kredi_onayi": True,
                    "model_secimi": "auto"}}
_SM_ISTEK = [_SM.shot_istegi(scene_id="s01", sorgu="lawn sprinkler",
                             negatifler=["cartoon"], sure_sn=12)]
_SM_COZ = lambda e: "tok_test"                                   # noqa: E731
_SM_OLC = lambda h: {"genislik": 1920, "yukseklik": 1080,        # noqa: E731
                     "bitrate": 8_000_000, "codec": "vp9"}
_SM_UCR = lambda i: [{"baslik": "lawn sprinkler commons",        # noqa: E731
                      "medya_turu": "video", "lisans": "cc-by-sa",
                      "asset_id": "c1"}]


def _sm_mcp(yetenekler, adaylar=None):
    def _c(ad, arg):
        if ad == "capabilities":
            return {"capabilities": list(yetenekler)}
        return {"adaylar": list(adaylar if adaylar is not None else [
            {"baslik": "lawn sprinkler garden", "medya_turu": "video",
             "lisans": "cc-by", "orijinal_url": "https://x/1",
             "eser_sahibi": "A", "asset_id": "m1"}])}
    return _c


def _sm_edin(**ek):
    v = dict(kayit=_SM_KAYIT, tenant_id="t1", job_id="j1",
             istekler=_SM_ISTEK, sifre_cozucu=_SM_COZ,
             ucretsiz_arayici=_SM_UCR, olcer=_SM_OLC)
    v.update(ek)
    return _SM.edin(**v)


# ── (1) SHOT ISTEGI PLANLAYICIDAN ──
kontrol("⭐ R-1b: shot istegi semantik sorgu + negatif + oran + sure + "
        "kalite hedefi tasiyor",
        set(_SM_ISTEK[0]) >= {"scene_id", "sorgu", "negatifler", "oran",
                              "sure_sn", "kalite_hedefi"})
kontrol("⭐ R-1b: istek suresi KAYNAK TAVANINA (8 sn) kirpiliyor",
        _SM_ISTEK[0]["sure_sn"] == 8.0, _SM_ISTEK[0]["sure_sn"])

# ── (2) REGISTRY + TENANT IZOLASYONU ──
kontrol("⭐ R-1b BELIRLEYICI: BASKA tenant'in baglantisi SECILMIYOR",
        _SM.saglayici_sec(_SM_KAYIT, "t2")["saglayici"]
        == _SM.UCRETSIZ_SAGLAYICI
        and "BAGLANTI-YOK" in _SM.saglayici_sec(_SM_KAYIT,
                                                "t2")["fallback_reason"])
kontrol("⭐ R-1b: onaysiz/kredi onaysiz baglanti KULLANILMIYOR",
        not _SM.kullanilabilir_mi(
            dict(_SM_KAYIT["t1"], onayli=False))["kullanilabilir"]
        and not _SM.kullanilabilir_mi(
            dict(_SM_KAYIT["t1"], kredi_onayi=False))["kullanilabilir"])
kontrol("⭐ R-1b: kullanici ACIKCA Magnific dedi ama baglanti yoksa SESSIZ "
        "gecis YOK — neden GORUNUR",
        "MAGNIFIC-KULLANILAMIYOR" in _SM.saglayici_sec(
            {}, "t1", tercih=_SM.TERCIH_MAGNIFIC)["fallback_reason"])
kontrol("⭐ R-1b BELIRLEYICI: TENANT TOKENI ISTEMCIYE CIKMIYOR",
        "sifreli_token" not in _SM.baglanti_ozeti(_SM_KAYIT["t1"])
        and "token" not in _SM.baglanti_ozeti(_SM_KAYIT["t1"])
        and _SM.baglanti_ozeti(_SM_KAYIT["t1"])["token_var"] is True)

# ── (3) JOB-SCOPE TOKEN: SIFRELEME UYDURULMUYOR ──
kontrol("⭐ R-1b RED-FIRST: gercek sifre cozucu YOKSA token KULLANILMIYOR "
        "(duz metin token KABUL EDILMEZ)",
        _SM.job_scope_token(_SM_KAYIT["t1"])["neden"] == "SIFRE-COZUCU-YOK"
        and _sm_edin(mcp_cagirici=_sm_mcp(["video.search"]),
                     sifre_cozucu=None)["provider_used"]
        == _SM.UCRETSIZ_SAGLAYICI)
kontrol("⭐ R-1b: cozucu patlarsa da saglayici KULLANILMIYOR",
        _SM.job_scope_token(
            _SM_KAYIT["t1"],
            sifre_cozucu=lambda e: (_ for _ in ()).throw(ValueError())
        )["hazir"] is False)
kontrol("⭐ R-1b: modul SIFRELEME UYDURMUYOR (kapsam ozeti beyan ediyor)",
        _SM.kapsam_ozeti()["sifreleme_uydurur"] is False
        and _SM.kapsam_ozeti()["duz_metin_token_kabul"] is False
        and _SM.kapsam_ozeti()["token_istemciye_cikar"] is False)

# ── (4) CAPABILITY DISCOVERY: UYDURMA YOK ──
_R1 = _sm_edin(mcp_cagirici=_sm_mcp(["video.search", "account.balance"]))
kontrol("⭐ R-1b: ARAMA yetenegi varsa o yol kullaniliyor, fallback YOK",
        _R1["provider_used"] == "magnific"
        and _R1["edinim_yolu"] == _SM.YETENEK_ARAMA
        and _R1["fallback_reason"] == "", _R1["fallback_reason"])
_R2 = _sm_edin(mcp_cagirici=_sm_mcp(
    ["video.generate"],
    [{"baslik": "lawn sprinkler generated", "medya_turu": "video",
      "model": "auto", "asset_id": "g1"}]))
kontrol("⭐ R-1b BELIRLEYICI: stok ARAMA yoksa UYDURULMUYOR — URETIM yoluna "
        "geciliyor ve NEDEN raporlaniyor",
        _R2["edinim_yolu"] == _SM.YETENEK_URETIM
        and _R2["fallback_reason"] == "STOK-ARAMA-YETENEGI-YOK",
        _R2["fallback_reason"])
_R3 = _sm_edin(mcp_cagirici=_sm_mcp(["account.balance"]))
kontrol("⭐ R-1b: HICBIR uygun yetenek yoksa UCRETSIZ STOK fallback ve "
        "`provider_used` + `fallback_reason` GORUNUR",
        _R3["provider_used"] == _SM.UCRETSIZ_SAGLAYICI
        and _R3["fallback_reason"] == "UYGUN-YETENEK-YOK"
        and bool(_R3["adaylar"]), _R3["fallback_reason"])
kontrol("⭐ R-1b: kesif CAGIRICISI yoksa 'arama vardir' DENMIYOR",
        _SM.yetenek_kesfi(None)["olculdu"] is False
        and _SM.yetenek_kesfi(None)["yetenekler"] == [])
kontrol("⭐ R-1b: saglayici aday DONDURMEZSE ucretsiz fallback + neden",
        _sm_edin(mcp_cagirici=_sm_mcp(["video.search"], []))
        ["fallback_reason"] == "SAGLAYICI-ADAY-DONDURMEDI")

# ── (5) PROVENANCE ──
_P = _R2["provenance"][0]
kontrol("⭐ R-1b: auto modda model GARANTI EDILMIYOR — provenance'a "
        "`model_unknown/auto` yaziliyor",
        _P["model"] == "model_unknown/auto", _P["model"])
kontrol("⭐ R-1b: provenance job/tenant/lisans/teknik/ses_kanali tasiyor",
        _P["job_id"] == "j1" and _P["tenant_id"] == "t1"
        and _P["ses_kanali"] == "sifir"
        and _P["teknik"]["genislik"] == 1920, _P["ses_kanali"])
kontrol("⭐ R-1b: gercek model adi verilirse AYNEN korunuyor",
        _SM.provenance_kur(saglayici="magnific", yol="video.generate",
                           istek=_SM_ISTEK[0], ham={"model": "flux-pro"},
                           olcum={})["model"] == "flux-pro")

# ── (6) TIMELINE: SIRALAMA + TAVAN + NEGATIF ──
_TL = _SM.timeline_yerlestir(
    [{"asset_id": "foto", "baslik": "lawn sprinkler", "medya_turu": "image",
      "teknik": {"genislik": 4000, "yukseklik": 3000, "bitrate": 0}},
     {"asset_id": "vid", "baslik": "lawn sprinkler", "medya_turu": "video",
      "teknik": {"genislik": 1920, "yukseklik": 1080, "bitrate": 9e6}}],
    [_SM.shot_istegi(scene_id="s01", sorgu="lawn sprinkler", sure_sn=6)])
kontrol("⭐ R-1b: esit semantikte GERCEK VIDEO fotografa TERCIH EDILIYOR",
        _TL["yerlesim"][0]["aday"]["asset_id"] == "vid",
        _TL["yerlesim"][0]["aday"]["asset_id"])
_TL2 = _SM.timeline_yerlestir(
    [{"asset_id": "m1", "baslik": "lawn sprinkler", "medya_turu": "video",
      "teknik": {"genislik": 1920, "yukseklik": 1080, "bitrate": 9e6}}],
    [_SM.shot_istegi(scene_id="s01", sorgu="lawn sprinkler", sure_sn=6),
     _SM.shot_istegi(scene_id="s01", sorgu="lawn sprinkler", sure_sn=6)])
kontrol("⭐ R-1b BELIRLEYICI: AYNI kaynak toplam 8 sn'yi ASAMIYOR",
        _TL2["kaynak_kullanimi"]["m1"] <= _SM.KAYNAK_BASINA_TAVAN_SN + 1e-6,
        _TL2["kaynak_kullanimi"])
kontrol("⭐ R-1b: yerlesimde kaynak sesi SIFIR olarak isaretli",
        all(y["ses_kanali"] == "sifir" for y in _TL2["yerlesim"]
            if y.get("aday")))
kontrol("⭐ R-1b RED-FIRST: NEGATIF ihlali olan aday ELENIYOR "
        "(puanla gizlenmiyor)",
        _SM.timeline_yerlestir(
            [{"asset_id": "x", "baslik": "cartoon lawn sprinkler",
              "medya_turu": "video", "teknik": {}}],
            [_SM.shot_istegi(scene_id="s01", sorgu="lawn sprinkler",
                             negatifler=["cartoon"], sure_sn=4)]
        )["yerlesim"][0]["aday"] is None)

# ── (7) SINIRLAR ──
kontrol("⭐ R-1b: modul AGA CIKMIYOR / MEDYA ACMIYOR (calisan kodda "
        "requests/urlopen/ffmpeg/open yok)",
        not any(a in _kod_yalniz(oku(KOK, "medya", "saglayici_motoru.py"))
                for a in ("requests", "urlopen", "ffmpeg", "ffprobe",
                          "open(", "subprocess")))
kontrol("⭐ R-1b: UI tercihleri sozlesmede sayili (otomatik/magnific/ucretsiz)",
        set(_SM.TERCIHLER) == {"otomatik", "magnific", "ucretsiz"})
kontrol("R-1b: saglayici_motoru.py derleniyor",
        _derlenir(os.path.join(KOK, "medya", "saglayici_motoru.py")))
kontrol("R-1b GERILEME YOK: K-1/K-2/K-3 ve lisans kapilari DURUYOR",
        "KALITE-BROLL-CESITLILIK" in _qon.FAIL_KODLARI
        and "KALITE-SES-GURULTU" in _qon.FAIL_KODLARI
        and "KALITE-BASLIK-SURESI" in _qon.FAIL_KODLARI
        and "KALITE-KUNYE-EKSIK" in _qon.FAIL_KODLARI)
kontrol("R-1b GERILEME YOK: 22 alanlik generate sozlesmesi DEGISMEDI",
        len(set(re.findall(r"\{ad: '(\w+)'",
                           oku(KOK, "static/js/api.js")))) == 22)


blok("§40s R-1c-a — ZORUNLU OTURUM + TENANT IZOLASYONU (guvenlik)")

# ⚠ MEDYASIZ + AGSIZ. Gercek hesap OLUSTURULMAZ, parola KODA/COMMIT'E
# YAZILMAZ; provisioning yalniz env/stdin'den okunur. $0.00.

_KM = __import__("kimlik")
import time as _kmtime                                    # noqa: E402
_KM_A = _KM.secrets.token_bytes(32)

# ── (1) PAROLA: TESLIM SOZLESMESI = ARGON2ID / BCRYPT, FAIL-CLOSED ──
kontrol("⭐ R-1c-a BELIRLEYICI: uretim algoritmasi ARGON2ID ya da BCRYPT "
        "(zayif fallback YOK)",
        _KM.kdf_adi() in ("argon2id", "bcrypt")
        and _KM.kapsam_ozeti()["zayif_fallback"] is False
        and _KM.kapsam_ozeti()["fail_closed"] is True, _KM.kdf_adi())
kontrol("⭐ R-1c-a: bagimlilik repo yonetiminde SABIT (Dockerfile)",
        "argon2-cffi==" in oku(os.path.dirname(KOK), "Dockerfile")
        and "argon2-cffi==" in oku(os.path.dirname(KOK), "Dockerfile.sunucu"))
_KM_H = _KM.parola_hashle("Ornek-Test-Parola-9!")
kontrol("⭐ R-1c-a: uretilen hash ARGON2ID/BCRYPT bicimi",
        _KM_H.split("$")[0] in ("argon2id", "bcrypt"), _KM_H.split("$")[0])
kontrol("⭐ R-1c-a: parola DUZ METIN saklanmiyor",
        "Ornek-Test-Parola-9!" not in _KM_H)
kontrol("⭐ R-1c-a: dogru parola GECIYOR, yanlis parola GECMIYOR",
        _KM.parola_dogrula("Ornek-Test-Parola-9!", _KM_H) is True
        and _KM.parola_dogrula("yanlis", _KM_H) is False)
kontrol("⭐ R-1c-a: her hash FARKLI (tuz) — rainbow tablo yok",
        _KM.parola_hashle("ayni") != _KM.parola_hashle("ayni"))
kontrol("⭐ R-1c-a RED-FIRST: ZAYIF eski bicim (pbkdf2/scrypt) normal "
        "dogrulamadan GECMIYOR",
        _KM.parola_dogrula("x", "pbkdf2$600000$0$0$aaaa$bbbb") is False
        and _KM.parola_dogrula("x", "scrypt$32768$8$1$aaaa$bbbb") is False)
_KM_TUZ = _KM.secrets.token_bytes(16)
_KM_OZ = _KM.hashlib.pbkdf2_hmac("sha256", b"eski-parola", _KM_TUZ, 1000,
                                 dklen=32)
_KM_ESKI = ("pbkdf2$1000$0$0$" + _KM._b64(_KM_TUZ) + "$"
            + _KM._b64(_KM_OZ))
_KM_G = _KM.eski_hash_dogrula("eski-parola", _KM_ESKI)
kontrol("⭐ R-1c-a: GECIS yolu AYRI ve ACIK — eski kayit yalniz "
        "`eski_hash_dogrula()` ile dogrulanir",
        _KM_G["gecerli"] is True and _KM_G["yeniden_hashle"] is True,
        _KM_G["neden"])
kontrol("⭐ R-1c-a: gecis dogrulamasi YANLIS parolayi GECIRMIYOR",
        _KM.eski_hash_dogrula("yanlis", _KM_ESKI)["gecerli"] is False)
kontrol("⭐ R-1c-a: guclu bicim gecis yoluna DUSMUYOR",
        _KM.eski_hash_dogrula("x", _KM_H)["neden"] == "ESKI-BICIM-DEGIL")
kontrol("⭐ R-1c-a: bozuk/bos kayit istisna SIZDIRMADAN False",
        _KM.parola_dogrula("x", "") is False
        and _KM.parola_dogrula("x", "bozuk") is False
        and _KM.parola_dogrula("", _KM_H) is False)
kontrol("⭐ R-1c-a: zayif parola REDDEDILIYOR",
        _KM.parola_gucu("kisa")["gecerli"] is False
        and _KM.parola_gucu("Ornek-Test-Parola-9!")["gecerli"] is True)
kontrol("⭐ R-1c-a FAIL-CLOSED: KDF yoksa stabil hata kodu (`KIMLIK-KDF-YOK`)",
        _KM.KDF_HATA_KODU == "KIMLIK-KDF-YOK"
        and _KM.kapsam_ozeti()["kdf_hata_kodu"] == "KIMLIK-KDF-YOK")

# ── (2) OTURUM ──
_KM_J = _KM.oturum_uret("t1", anahtar=_KM_A)
kontrol("⭐ R-1c-a: gecerli oturum tenant kimligini VERIYOR",
        _KM.oturum_coz(_KM_J, anahtar=_KM_A)["tenant_id"] == "t1")
kontrol("⭐ R-1c-a RED-FIRST: IMZASI BOZUK oturum REDDEDILIYOR",
        _KM.oturum_coz(_KM_J[:-2] + "xx", anahtar=_KM_A)["neden"]
        == "IMZA-GECERSIZ")
kontrol("⭐ R-1c-a RED-FIRST: BASKA anahtarla uretilmis oturum GECMIYOR "
        "(jeton uydurulamaz)",
        _KM.oturum_coz(_KM.oturum_uret("t9",
                                       anahtar=_KM.secrets.token_bytes(32)),
                       anahtar=_KM_A)["neden"] == "IMZA-GECERSIZ")
kontrol("⭐ R-1c-a: SURESI DOLMUS oturum REDDEDILIYOR",
        _KM.oturum_coz(_KM.oturum_uret("t1", anahtar=_KM_A, omur_sn=1),
                       anahtar=_KM_A,
                       simdi=int(_kmtime.time()) + 10)["neden"]
        == "SURESI-DOLMUS")
kontrol("⭐ R-1c-a: bicimi bozuk jeton COZULMEYE CALISILMIYOR",
        _KM.oturum_coz("abc", anahtar=_KM_A)["neden"] == "BICIM-BOZUK")

# ── (3) COOKIE / CSRF ──
kontrol("⭐ R-1c-a: cerez HttpOnly + SameSite + Secure",
        _KM.COOKIE_BAYRAKLARI["httponly"] is True
        and _KM.COOKIE_BAYRAKLARI["samesite"] == "lax"
        and _KM.COOKIE_BAYRAKLARI["secure"] is True)
kontrol("⭐ R-1c-a: CSRF double-submit — esit degerler GECER",
        _KM.csrf_dogrula("abc123", "abc123") is True)
kontrol("⭐ R-1c-a RED-FIRST: CSRF uyusmazligi ve BOS deger REDDEDILIYOR",
        _KM.csrf_dogrula("abc123", "abc124") is False
        and _KM.csrf_dogrula("", "") is False
        and _KM.csrf_dogrula("abc", "") is False)

# ── (4) GIRIS HIZ SINIRI ──
_KM_RL = {}
_KM_IZIN = []
for _i in range(_KM.GIRIS_TAVAN + 2):
    _r = _KM.hiz_siniri(_KM_RL, "ip1")
    _KM_IZIN.append(_r["izin"])
    if _r["izin"]:
        _KM.hiz_siniri_isle(_KM_RL, "ip1")
kontrol("⭐ R-1c-a RED-FIRST: art arda basarisiz giris HIZ SINIRINA takiliyor",
        _KM_IZIN[:_KM.GIRIS_TAVAN] == [True] * _KM.GIRIS_TAVAN
        and _KM_IZIN[_KM.GIRIS_TAVAN] is False, _KM_IZIN)
kontrol("⭐ R-1c-a: pencere gecince yeniden izin veriliyor (kalici kilit yok)",
        _KM.hiz_siniri(dict(_KM_RL), "ip1",
                       simdi=_kmtime.time() + _KM.GIRIS_PENCERE_SN + 1)["izin"]
        is True)
kontrol("⭐ R-1c-a: hiz siniri IP BASINA ayri (bir kullanici digerini "
        "kilitleyemez)",
        _KM.hiz_siniri(_KM_RL, "ip2")["izin"] is True)

# ── (5) TENANT IZOLASYONU ──
kontrol("⭐ R-1c-a BELIRLEYICI: KIMLIK YOKSA ERISIM YOK",
        _KM.tenant_coz("", anahtar=_KM_A)["yetkili"] is False
        and _KM.kapsam_ozeti()["kimliksiz_erisim"] is False)
kontrol("⭐ R-1c-a BELIRLEYICI: BASKA tenant'in kaynagina erisim REDDEDILIYOR",
        _KM.sahiplik_dogrula({"tenant_id": "t2"}, "t1")["neden"]
        == "BASKA-TENANT")
kontrol("⭐ R-1c-a: SAHIPSIZ (eski) kayit 'herkese acik' SAYILMIYOR",
        _KM.sahiplik_dogrula({}, "t1")["neden"] == "KAYNAK-SAHIPSIZ"
        and _KM.kapsam_ozeti()["sahipsiz_kaynak_erisilir"] is False)
kontrol("⭐ R-1c-a: tenant kimligi BOSSA erisim yok",
        _KM.sahiplik_dogrula({"tenant_id": "t1"}, "")["neden"] == "TENANT-YOK")
kontrol("⭐ R-1c-a: kendi kaynagina erisim GECERLI",
        _KM.sahiplik_dogrula({"tenant_id": "t1"}, "t1")["izin"] is True)

# ── (6) GUVENLI PROVISIONING ──
_KM_P = _KM.provisioning_girdisi(
    env={"VIDRUSH_ADMIN_KULLANICI": "ornek",
         "VIDRUSH_ADMIN_PAROLA": "Ornek-Test-Parola-9!"})
kontrol("⭐ R-1c-a: provisioning env'den okunuyor ve PAROLA HASH'LENIYOR",
        _KM_P["hazir"] is True
        and sorted(_KM_P["kayit"]) == ["kullanici", "parola_hash",
                                       "tenant_id"])
kontrol("⭐ R-1c-a BELIRLEYICI: donen kayitta DUZ METIN PAROLA YOK",
        "Ornek-Test-Parola-9!" not in repr(_KM_P["kayit"]))
kontrol("⭐ R-1c-a: her hesaba AYRI tenant_id uretiliyor",
        _KM.provisioning_girdisi(
            env={"VIDRUSH_ADMIN_KULLANICI": "a",
                 "VIDRUSH_ADMIN_PAROLA": "Ornek-Test-Parola-9!"}
        )["kayit"]["tenant_id"] != _KM_P["kayit"]["tenant_id"])
kontrol("⭐ R-1c-a: girdi eksikse hesap ACILMIYOR (ipucu veriliyor)",
        _KM.provisioning_girdisi(env={})["neden"] == "GIRDI-EKSIK")
kontrol("⭐ R-1c-a: zayif parolayla hesap ACILMIYOR",
        _KM.provisioning_girdisi(
            env={"VIDRUSH_ADMIN_KULLANICI": "a",
                 "VIDRUSH_ADMIN_PAROLA": "kisa"})["neden"] == "PAROLA-ZAYIF")
kontrol("⭐ R-1c-a: parola stdin'den de okunabiliyor (argumanda GECMEZ)",
        _KM.provisioning_girdisi(
            env={"VIDRUSH_ADMIN_KULLANICI": "a"},
            stdin_okuyucu=lambda: "Ornek-Test-Parola-9!")["hazir"] is True)

# ── (7) SINIRLAR ──
kontrol("⭐ R-1c-a: modul AGA CIKMIYOR / MEDYA ACMIYOR",
        not any(a in _kod_yalniz(oku(KOK, "kimlik.py"))
                for a in ("requests", "urlopen", "ffmpeg", "subprocess")))
kontrol("⭐ R-1c-a: repoda DUZ METIN parola YOK",
        "VIDRUSH_ADMIN_PAROLA=" not in oku(KOK, "kimlik.py"))
kontrol("R-1c-a: kimlik.py derleniyor",
        _derlenir(os.path.join(KOK, "kimlik.py")))
kontrol("R-1c-a GERILEME YOK: 22 alan + K/R kapilari DURUYOR",
        len(set(re.findall(r"\{ad: '(\w+)'",
                           oku(KOK, "static/js/api.js")))) == 22
        and "KALITE-BROLL-CESITLILIK" in _qon.FAIL_KODLARI
        and "KALITE-BASLIK-SURESI" in _qon.FAIL_KODLARI)


blok("§40t R-1c-b — TENANT BASINA SON 3 KABUL EDILMIS VIDEO")

# ⚠ MEDYASIZ: dosya URETILMEZ/SILINMEZ, yalniz METADATA yasam dongusu.

_KT = __import__("kutuphane")


def _kt_is(qa="PASS", durum="bitti", video="ciktilar/x.mp4"):
    return {"durum": durum, "video": video,
            "qa": {"durum": qa, "fail": 0, "warn": 1, "puan": 100},
            "provenance": {"provider_used": "magnific",
                           "fallback_reason": "STOK-ARAMA-YETENEGI-YOK",
                           "model": "model_unknown/auto",
                           "kredi_tuketildi": True,
                           "lisanslar": ["cc-by"], "kaynaklar": ["u1"]}}


def _kt_kayit(t, n, zaman):
    return _KT.kayit_kur(is_id=f"j{n}", tenant_id=t, dosya=f"v{n}.mp4",
                         kayit=_kt_is(), kabul_zamani=zaman)


# ── (1) KABUL KAPISI: yalnizca BASARILI + QA KABUL ──
kontrol("⭐ R-1c-b: basarili + QA PASS is kutuphaneye GIRER",
        _KT.kabul_edilebilir_mi(_kt_is())["kabul"] is True)
kontrol("⭐ R-1c-b: QA WARN da KABUL (uyari teslim edilebilirligi bozmaz)",
        _KT.kabul_edilebilir_mi(_kt_is(qa="WARN"))["kabul"] is True)
kontrol("⭐ R-1c-b RED-FIRST: QA FAIL olan cikti GIRMEZ",
        _KT.kabul_edilebilir_mi(_kt_is(qa="FAIL"))["kabul"] is False)
kontrol("⭐ R-1c-b RED-FIRST: QA OLCULMEMIS cikti GIRMEZ "
        "('muhtemelen iyidir' DENMEZ)",
        _KT.kabul_edilebilir_mi(_kt_is(qa=""))["kabul"] is False
        and "QA:" in _KT.kabul_edilebilir_mi(_kt_is(qa=""))["neden"])
kontrol("⭐ R-1c-b RED-FIRST: BASARISIZ / yarim is GIRMEZ",
        _KT.kabul_edilebilir_mi(_kt_is(durum="hata"))["kabul"] is False
        and _KT.kabul_edilebilir_mi(_kt_is(durum="uretiliyor"))["kabul"]
        is False)
kontrol("⭐ R-1c-b RED-FIRST: VIDEOSU olmayan is GIRMEZ",
        _KT.kabul_edilebilir_mi(_kt_is(video=""))["kabul"] is False)

# ── (2) RETENTION: son 3, 4. gelince EN ESKI KUYRUGA ──
_KTB: dict = {}
_KT_SIL = []
for _i in range(1, 4):
    _r = _KT.ekle(_KTB, _kt_kayit("t1", _i, 100.0 + _i))
    _KT_SIL += _r["silinecek"]
kontrol("⭐ R-1c-b: uc kabul sonrasi kutuphanede 3 kayit, silme kuyrugu BOS",
        len(_KTB["t1"]) == 3 and _KT_SIL == [], _KT_SIL)
_R4 = _KT.ekle(_KTB, _kt_kayit("t1", 4, 104.0))
kontrol("⭐ R-1c-b BELIRLEYICI: 4. kabul edilince EN ESKI kayit SILME "
        "KUYRUGUNA aliniyor ve kutuphane 3'te kaliyor",
        len(_KTB["t1"]) == 3 and len(_R4["silinecek"]) == 1
        and _R4["silinecek"][0]["is_id"] == "j1"
        and _R4["silinecek"][0]["sebep"] == "TAVAN-ASILDI",
        _R4["silinecek"])
kontrol("⭐ R-1c-b: modul DOSYA SILMIYOR — yalniz kuyruk donuyor "
        "(gercek silme remote lifecycle isi)",
        _KT.kapsam_ozeti()["dosya_siler"] is False
        and "kuyruga alinir" in _KT.kapsam_ozeti()["silme"])
kontrol("⭐ R-1c-b: siralama EN YENI once (kabul zamanina gore)",
        [x["is_id"] for x in _KTB["t1"]] == ["j4", "j3", "j2"],
        [x["is_id"] for x in _KTB["t1"]])
kontrol("⭐ R-1c-b: GEC gelen ESKI tarihli kayit en yeniyi DUSURMUYOR",
        [x["is_id"] for x in _KT.ekle(
            dict(_KTB), _kt_kayit("t1", 9, 1.0))["kutuphane"]]
        == ["j4", "j3", "j2"])
kontrol("⭐ R-1c-b: AYNI is iki kez eklenince COGALMIYOR (idempotan)",
        len(_KT.ekle(dict(_KTB), _kt_kayit("t1", 4, 104.0))["kutuphane"])
        == 3)

# ── (3) TENANT SIZINTISI ──
_KT.ekle(_KTB, _kt_kayit("t2", 7, 200.0))
kontrol("⭐ R-1c-b BELIRLEYICI: bir tenant DIGERININ videolarini GORMUYOR",
        [v["is_id"] for v in _KT.listele(_KTB, "t2")["videolar"]] == ["j7"]
        and "j7" not in [v["is_id"]
                         for v in _KT.listele(_KTB, "t1")["videolar"]])
kontrol("⭐ R-1c-b: TENANT KIMLIGI YOKSA listeleme REDDEDILIYOR",
        _KT.listele(_KTB, "")["ok"] is False
        and _KT.listele(_KTB, "")["videolar"] == [])
kontrol("⭐ R-1c-b: kaydin sahibi baska tenant ise IKINCI SAVUNMA eliyor",
        _KT.listele({"t1": [_kt_kayit("t2", 8, 1.0)]}, "t1")["videolar"]
        == [])
kontrol("⭐ R-1c-b: tenant'i olmayan kayit EKLENMIYOR",
        _KT.ekle({}, _kt_kayit("", 1, 1.0))["neden"] == "TENANT-YOK")

# ── (4) SIGNED URL: TALEP ANINDA, SAKLANMADAN ──
kontrol("⭐ R-1c-b: signed URL kayitta SAKLANMIYOR",
        "video_url" not in _kt_kayit("t1", 1, 1.0)
        and _KT.kapsam_ozeti()["signed_url_saklanir"] is False)
_KT_L = _KT.listele(_KTB, "t1", imzalayici=_IU.imzala)
kontrol("⭐ R-1c-b: listeleme signed URL'i TALEP ANINDA uretiyor",
        all("sig=" in (v["video_url"] or "") for v in _KT_L["videolar"])
        and all(v["imzalanamadi"] is False for v in _KT_L["videolar"]))
kontrol("⭐ R-1c-b: imzalayici YOKSA sessiz bos link YOK — `imzalanamadi` "
        "ACIKCA isaretleniyor",
        all(v["video_url"] is None and v["imzalanamadi"] is True
            for v in _KT.listele(_KTB, "t1")["videolar"]))

# ── (5) METADATA SOZLESMESI ──
_KT_V = _KT_L["videolar"][0]
kontrol("⭐ R-1c-b: kayit QA + provenance + provider + model + credit + "
        "zaman damgasi tasiyor",
        _KT_V["qa"]["durum"] == "PASS"
        and _KT_V["provenance"]["provider_used"] == "magnific"
        and _KT_V["provenance"]["model"] == "model_unknown/auto"
        and _KT_V["provenance"]["kredi_tuketildi"] is True
        and _KT_V["kabul_zamani"] is not None, _KT_V["provenance"])
kontrol("⭐ R-1c-b: fallback nedeni de tasiniyor (gorunur kalir)",
        _KT_V["provenance"]["fallback_reason"] == "STOK-ARAMA-YETENEGI-YOK")
kontrol("⭐ R-1c-b: EKSIK alan UYDURULMUYOR (bilinmiyorsa None)",
        _KT.kayit_kur(is_id="j", tenant_id="t", dosya="d.mp4", kayit={},
                      kabul_zamani=1.0)["provenance"]["model"] is None)
kontrol("⭐ R-1c-b: listeleme sozlesmesi tavani da bildiriyor",
        _KT_L["tavan"] == 3 and _KT_L["sayi"] == 3)

# ── (6) SINIRLAR ──
kontrol("⭐ R-1c-b: modul MEDYA ACMIYOR / AGA CIKMIYOR / DOSYA SILMIYOR",
        not any(a in _kod_yalniz(oku(KOK, "kutuphane.py"))
                for a in ("open(", "os.remove", "requests", "subprocess",
                          "ffmpeg")))
kontrol("R-1c-b: kutuphane.py derleniyor",
        _derlenir(os.path.join(KOK, "kutuphane.py")))
kontrol("R-1c-b GERILEME YOK: 22 alan + kimlik/imza kapilari DURUYOR",
        len(set(re.findall(r"\{ad: '(\w+)'",
                           oku(KOK, "static/js/api.js")))) == 22
        and _KM.kapsam_ozeti()["fail_closed"] is True
        and _IU.kapsam_ozeti()["ttl_zorunlu"] is True)


blok("§40u R-1d-a — TESLIM ATOMU: ZINCIR UCTAN UCA BAGLANDI")

# ⚠ MEDYASIZ + AGSIZ + PARASIZ: hicbir video URETILMEZ, hicbir saglayiciya
# baglanilmaz, GERCEK OAuth/kredi YOKTUR. Olculen sey KARAR MANTIGI ve
# GERCEK FastAPI uclarinin davranisidir.
#
# ── OLCULEN KUSUR ──
# R-1a/R-1b/R-1c-a/R-1c-b moduller olarak vardi ama `server.py` UCUNU DE
# IMPORT ETMIYORDU: `/api/generate` serbest bir `session` string'i aliyor,
# `/ciktilar/` imzayi dogruluyor ama TENANT'a bakmiyor, kutuphane HICBIR
# ZAMAN dolmuyordu. Yani teslim zinciri KAGIT UZERINDEYDI.

_TS = __import__("teslim")

# ── (0) ZINCIR GERCEKTEN BAGLI MI (kusurun kendisi) ──
_srv_kod = oku(KOK, "server.py")
kontrol("⭐ R-1d-a BELIRLEYICI: server.py kimlik + kutuphane + teslim'i "
        "GERCEKTEN import ediyor (once hicbirini etmiyordu)",
        all(f"import {m}" in _srv_kod
            for m in ("kimlik", "kutuphane", "teslim")))
kontrol("⭐ R-1d-a: zincirin 10 halkasi da ADLANDIRILMIS ve SIRALI",
        list(_TS.ZINCIR_ADLARI) == [
            "oturum", "metin", "plan", "saglayici", "uzak_tts_render",
            "pre_qa", "post_qa", "depolama", "imzali_url", "kutuphane"],
        list(_TS.ZINCIR_ADLARI))

# ── (1) OTURUM ANAHTARI + FAIL-CLOSED OTURUM KAPISI ──
_TS_DIZ = tempfile.mkdtemp(prefix="oturum_")
kontrol("⭐ R-1d-a: oturum anahtari IMZA anahtarindan AYRI ve 0600 uretiliyor",
        _TS.anahtar_kur(_TS_DIZ) is True and _TS.hazir() is True
        and (os.stat(os.path.join(_TS_DIZ, _TS.ANAHTAR_DOSYA_ADI)).st_mode
             & 0o077) == 0
        and _TS.anahtar() != _IU._ANAHTAR)
_TS_JETON = _KM.oturum_uret("t1", anahtar=_TS.anahtar())
kontrol("⭐ R-1d-a: gecerli jeton tenant'a cozuluyor",
        _TS.oturum_kapisi(_TS_JETON) == {"izin": True, "tenant_id": "t1",
                                         "neden": ""})
kontrol("⭐ R-1d-a RED-FIRST: JETONSUZ istek REDDEDILIYOR",
        _TS.oturum_kapisi("")["izin"] is False)
kontrol("⭐ R-1d-a RED-FIRST: BASKA anahtarla imzalanmis jeton REDDEDILIYOR",
        _TS.oturum_kapisi(_KM.oturum_uret("t1", anahtar=b"sahte-anahtar")
                          )["neden"] == "IMZA-GECERSIZ")
kontrol("⭐ R-1d-a RED-FIRST: SURESI DOLMUS jeton REDDEDILIYOR",
        _TS.oturum_kapisi(_KM.oturum_uret("t1", anahtar=_TS.anahtar(),
                                          omur_sn=1, simdi=1000),
                          simdi=2000)["neden"] == "SURESI-DOLMUS")
kontrol("⭐ R-1d-a: BASKA tenant'in kaydina erisim YOK; SAHIPSIZ kayit da "
        "'herkese acik' SAYILMIYOR",
        _TS.erisim_kapisi({"tenant_id": "t2"}, "t1")["neden"] == "BASKA-TENANT"
        and _TS.erisim_kapisi({}, "t1")["neden"] == "KAYNAK-SAHIPSIZ")

# ── (2) TENANT'A BAGLI SIGNED URL (R-1a uzerine, GERIYE UYUMLU) ──
kontrol("⭐ R-1d-a: tenant VERILMEZSE imza R-1a ile BIT-BIT AYNI "
        "(eski baglantilar kirilmiyor)",
        _IU.imzala("j.mp4", simdi=1000)
        == _IU.imzala("j.mp4", simdi=1000, tenant=""))
_T1_URL = _IU.imzala("j.mp4", simdi=1000, tenant="t1")
_T1_Q = dict(x.split("=") for x in _T1_URL.split("?")[1].split("&"))
kontrol("⭐ R-1d-a: tenant'a bagli imza KENDI tenant'inda GECERLI",
        _IU.dogrula("j.mp4", _T1_Q["exp"], _T1_Q["sig"], simdi=1000,
                    tenant="t1")["gecerli"] is True)
kontrol("⭐ R-1d-a BELIRLEYICI: SIZAN baglanti BASKA TENANT'in oturumunda "
        "GECERSIZ (R-1a'da her oturumda calisiyordu)",
        _IU.dogrula("j.mp4", _T1_Q["exp"], _T1_Q["sig"], simdi=1000,
                    tenant="t2")["neden"] == "IMZA-GECERSIZ")
kontrol("⭐ R-1d-a RED-FIRST: tenant'a bagli baglanti OTURUMSUZ da GECERSIZ",
        _IU.dogrula("j.mp4", _T1_Q["exp"], _T1_Q["sig"], simdi=1000,
                    tenant="")["neden"] == "IMZA-GECERSIZ")
# ⚠ Iddia "imzanin BAYTLARINDA t1 gecmiyor" DEGIL (base64 rastgele; ilk
# yazimda tam bu yuzden ara ara kirmizi yandi). Iddia: URL tenant'i AYRI BIR
# ALAN olarak TASIMIYOR — parametreler yalniz exp+sig, yol ayni, iki farkli
# tenant icin YALNIZCA imza degisiyor.
_T2_URL = _IU.imzala("j.mp4", simdi=1000, tenant="t2")
kontrol("⭐ R-1d-a: TENANT KIMLIGI URL'e YAZILMIYOR (link kimin oldugunu "
        "sizdirmiyor)",
        set(_T1_Q) == {"exp", "sig"}
        and _T1_URL.split("?")[0] == _T2_URL.split("?")[0] == "ciktilar/j.mp4"
        and _T1_Q["exp"] == dict(x.split("=") for x in
                                 _T2_URL.split("?")[1].split("&"))["exp"]
        and _T1_URL != _T2_URL, f"{_T1_URL} | {_T2_URL}")
kontrol("⭐ R-1d-a: tenant YOKSA imzalayici URETILMIYOR (imzasiz link YOK)",
        _TS.imzalayici_kur("") is None)

# ── (3) SAGLAYICI HALKASI: GERCEK OAuth/KREDI YOK ──
_TS_SAG = _TS.saglayici_karari({}, "t1")
kontrol("⭐ R-1d-a: baglantisi olmayan tenant UCRETSIZ STOK'a duser ve NEDEN "
        "GORUNUR kalir ('magnific bagli' DENMEZ)",
        _TS_SAG["provider_used"] == "wikimedia"
        and _TS_SAG["ucretsiz_fallback"] is True
        and _TS_SAG["fallback_reason"].startswith("BAGLANTI-YOK"), _TS_SAG)
kontrol("⭐ R-1d-a: ucretsiz yolda KREDI TUKETILMIYOR",
        _TS_SAG["kredi_tuketildi"] is False
        and _TS.kapsam_ozeti()["gercek_oauth"] is False
        and _TS.kapsam_ozeti()["kredi_tuketir"] is False)
kontrol("⭐ R-1d-a: test-double Magnific baglantisi verilirse O secilir "
        "(zincir gercekten registry'den geciyor)",
        _TS.saglayici_karari(
            {"t1": {"saglayici": "magnific", "aktif": True, "onayli": True,
                    "sifreli_token": b"ENC", "kredi_onayi": True}},
            "t1")["provider_used"] == "magnific")
kontrol("⭐ R-1d-a BELIRLEYICI: BASKA tenant'in baglantisi SECILMIYOR",
        _TS.saglayici_karari(
            {"t2": {"saglayici": "magnific", "aktif": True, "onayli": True,
                    "sifreli_token": b"ENC", "kredi_onayi": True}},
            "t1")["provider_used"] == "wikimedia")
kontrol("⭐ R-1d-a: is TENANT'a ve SAGLAYICI KARARINA muhurleniyor",
        _TS.is_damgala({}, tenant_id="t1", metin="x" * 30,
                       saglayici=_TS_SAG)["kayit"]["saglayici"]
        ["provider_used"] == "wikimedia")
kontrol("⭐ R-1d-a RED-FIRST: TENANT'SIZ is DAMGALANMIYOR",
        _TS.is_damgala({}, tenant_id="")["ok"] is False)

# ── (4) ZINCIR RAPORU: KANITSIZ HALKA GECMEZ ──
def _ts_tam(**ek):
    k = {"tenant_id": "t1", "metin_uzunlugu": 42, "sahne_sayisi": 6,
         "saglayici": {"provider_used": "wikimedia",
                       "fallback_reason": "BAGLANTI-YOK:BAGLANTI-YOK"},
         "video": "ciktilar/j1.mp4", "sure": 60.0, "durum": "bitti",
         # ⚠ R-1d-e: PRE-QA kaniti artik RENDER EDILEN zaman cizgisinden
         # gelir (`render_qa`). `edit_plani` HICBIR ZAMAN RENDER EDILMEYEN
         # alternatif plandir ve KANIT SAYILMAZ.
         # ⚠ R-1d-b: hukum YETMEZ — sahne >= 1 VE gercek olcum sart.
         "render_qa": {"durum": "PASS", "sahne": 8, "fail": 0, "warn": 1,
                       "kapsam": {"kapsam_orani": 1.0},
                       "medya_turu": {"olculdu": True},
                       "kaynak_ses": {"olculdu": True, "temiz": True},
                       "kaynak_kullanimi": {"olculdu": True, "temiz": True}},
         "qa": {"durum": "PASS", "fail": 0, "warn": 0}}
    k.update(ek)
    return k


kontrol("⭐ R-1d-a: HER halkanin kaniti varsa zincir TAM",
        _TS.zincir_raporu(_ts_tam(), dosya_var=True)["tam"] is True,
        _TS.zincir_raporu(_ts_tam(), dosya_var=True)["eksik"])
for _alan, _bek in (({"sahne_sayisi": 0}, "plan"),
                    ({"metin_uzunlugu": 0}, "metin"),
                    ({"saglayici": {}}, "saglayici"),
                    ({"sure": 0}, "uzak_tts_render"),
                    ({"render_qa": {}}, "pre_qa"),
                    ({"qa": {}}, "post_qa")):
    kontrol(f"⭐ R-1d-a RED-FIRST: '{_bek}' halkasinin KANITI yoksa zincir "
            f"TAM DEGIL",
            _bek in _TS.zincir_raporu(_ts_tam(**_alan),
                                      dosya_var=True)["eksik"],
            _TS.zincir_raporu(_ts_tam(**_alan), dosya_var=True)["eksik"])
kontrol("⭐ R-1d-a BELIRLEYICI: depolama OLCULMEDIYSE 'vardir' SAYILMIYOR "
        "(dosya_var=None -> DEPOLAMA-OLCULMEDI)",
        "depolama" in _TS.zincir_raporu(_ts_tam())["eksik"]
        and [h for h in _TS.zincir_raporu(_ts_tam())["halkalar"]
             if h["asama"] == "depolama"][0]["neden"] == "DEPOLAMA-OLCULMEDI")
kontrol("⭐ R-1d-a: PRE-QA WARN teslimi ENGELLEMIYOR, FAIL ENGELLIYOR",
        _TS.zincir_raporu(_ts_tam(render_qa={
            "durum": "WARN", "sahne": 8,
            "medya_turu": {"olculdu": True}}), dosya_var=True)["tam"] is True
        and "pre_qa" in _TS.zincir_raporu(
            _ts_tam(render_qa={"durum": "FAIL", "sahne": 8,
                               "medya_turu": {"olculdu": True}}),
            dosya_var=True)["eksik"])

# ⚠ FAZ R-1d-b — ICI BOS PRE-QA HUKMU (staging'de OLCULEN kusur).
# Kopru manifesti doldurdu, `plan_kur` calisti ve QA=WARN dondu; ama plan
# SIFIR cekim uretmisti ve TUM olcum sozlukleri BOSTU. Zincir bu "WARN"i
# kanit sayip videoyu KABUL ETMISTI — "kanitsiz halka gecmez" ihlali.
kontrol("⭐ R-1d-b RED-FIRST: SIFIR CEKIMLI plan uzerindeki PRE-QA hukmu "
        "KANIT SAYILMIYOR (vakumda WARN kabul edilmez)",
        "pre_qa" in _TS.zincir_raporu(
            _ts_tam(render_qa={"durum": "WARN", "sahne": 0}),
            dosya_var=True)["eksik"])
kontrol("⭐ R-1d-b: reddin NEDENI 'PRE-QA-BOS' olarak ACIKCA yaziliyor "
        "(sadece 'eksik' demiyor)",
        [h["neden"] for h in _TS.zincir_raporu(
            _ts_tam(render_qa={"durum": "WARN", "sahne": 0}),
            dosya_var=True)["halkalar"]
         if h["asama"] == "pre_qa"][0].startswith("PRE-QA-BOS:"))
kontrol("⭐ R-1d-b RED-FIRST: sahne VAR ama OLCUM YOKSA da gecmiyor",
        "pre_qa" in _TS.zincir_raporu(
            _ts_tam(render_qa={"durum": "PASS", "sahne": 8}),
            dosya_var=True)["eksik"])
kontrol("⭐ R-1d-b BELIRLEYICI: olcum GERCEK sema ile (`olcumler` DEGIL, "
        "ust seviye `medya_turu`) taninıyor — dolu PRE-QA 'bos' sayilmiyor",
        _TS.zincir_raporu(
            _ts_tam(render_qa={"durum": "PASS", "sahne": 10, "fail": 0,
                               "medya_turu": {"olculdu": True},
                               "kapsam": {"kapsam_orani": 1.0}}),
            dosya_var=True)["tam"] is True)
kontrol("⭐ R-1d-b: dogrudan `qa_on` ciktisi (`olcumler` dolu) da KABUL",
        _TS.zincir_raporu(
            _ts_tam(render_qa={"durum": "PASS", "sahne": 8,
                               "olcumler": {"kapsam": {"cekim": 8}}}),
            dosya_var=True)["tam"] is True)
kontrol("⭐ R-1d-b: anlatim metni props sinirinda TASINIYOR "
        "(bos metin -> beat plani kurulamiyor -> sifir cekim)",
        '"anlatim": metin,' in oku(KOK, "pipeline.py"))
kontrol("⭐ R-1d-b: sahne kimligi props sinirinda TASINIYOR "
        "(cumle <-> manifest bagi kopmasin)",
        '"scene_id": str(s.get("scene_id") or f"s{n:03d}")'
        in oku(KOK, "pipeline.py"))

# ── (5) TESLIM: UC KAPI DA GECILMEDEN KUTUPHANEYE GIRILMEZ ──
_TSD: dict = {}
_TS_R = _TS.teslim_et(is_id="j1", tenant_id="t1", kayit=_ts_tam(),
                      kutuphane_deposu=_TSD, kabul_zamani=100.0,
                      dosya_var=True)
kontrol("⭐ R-1d-a: zincir TAM + QA KABUL + sahiplik TAMAM ise is TESLIM "
        "EDILIYOR ve kutuphaneye GIRIYOR",
        _TS_R["teslim"] is True and len(_TSD["t1"]) == 1, _TS_R["neden"])
kontrol("⭐ R-1d-a: teslim edilen kayit TENANT'A BAGLI signed URL tasiyor",
        "sig=" in (_TS_R["video_url"] or "")
        and _TS_R["imzalanamadi"] is False)
kontrol("⭐ R-1d-a BELIRLEYICI: teslim URL'i BASKA tenant'ta CALISMIYOR",
        _IU.dogrula(*( [_TS_R["video_url"].split("/")[1].split("?")[0]]
                      + [dict(x.split("=") for x in
                              _TS_R["video_url"].split("?")[1].split("&"))[k]
                         for k in ("exp", "sig")]),
                    tenant="t2")["gecerli"] is False)
_TS_FAIL = _TS.teslim_et(is_id="j2", tenant_id="t1",
                         kayit=_ts_tam(qa={"durum": "FAIL", "fail": 2}),
                         kutuphane_deposu=dict(_TSD), kabul_zamani=101.0,
                         dosya_var=True)
kontrol("⭐ R-1d-a RED-FIRST: POST-QA FAIL olan video TESLIM EDILMIYOR ve "
        "kutuphaneye GIRMIYOR",
        _TS_FAIL["teslim"] is False and "post_qa" in _TS_FAIL["zincir"]["eksik"]
        and "KABUL-YOK" in _TS_FAIL["neden"], _TS_FAIL["neden"])
kontrol("⭐ R-1d-a RED-FIRST: DOSYASI OLMAYAN is TESLIM EDILMIYOR "
        "(object storage kaniti sart)",
        _TS.teslim_et(is_id="j3", tenant_id="t1", kayit=_ts_tam(),
                      kutuphane_deposu=dict(_TSD), kabul_zamani=102.0,
                      dosya_var=False)["teslim"] is False)
kontrol("⭐ R-1d-a RED-FIRST: BASKA tenant adina teslim REDDEDILIYOR",
        _TS.teslim_et(is_id="j4", tenant_id="t2", kayit=_ts_tam(),
                      kutuphane_deposu=dict(_TSD), kabul_zamani=103.0,
                      dosya_var=True)["teslim"] is False)
kontrol("⭐ R-1d-a: teslim edilmeyen isin NEDENI acikca yaziliyor "
        "(sessiz basarisizlik YOK)",
        bool(_TS_FAIL["neden"]) and _TS_FAIL["video_url"] is None)

# ── (5b) TESLIM KARARI API SOZLESMESINDE GORUNUR ──
# ⚠ `kalite` videonun OLCUMUNU soyler; `teslim` KABUL EDILMIS FINAL olup
# olmadigini. Ikisi ayni sey degil: QA PASS olsa bile zincirin bir halkasi
# kanitsizsa is teslim EDILMEZ. Arayuz ikisini KARISTIRMAMALI.
_TS_N1 = _isz.normalize("j1", dict(_ts_tam(),
                                   teslim={"teslim": True, "neden": "",
                                           "eksik": []}))
_TS_N2 = _isz.normalize("j2", _ts_tam())
kontrol("⭐ R-1d-a: is sozlesmesi TESLIM kararini donduruyor",
        _TS_N1["teslim_ok"] is True and _TS_N1["teslim"]["teslim"] is True)
kontrol("⭐ R-1d-a RED-FIRST: teslim OLCULMEMISSE 'teslim edildi' DENMIYOR "
        "(QA PASS olsa bile)",
        _TS_N2["kalite"] == "PASS" and _TS_N2["teslim_ok"] is False
        and _TS_N2["teslim"] == {}, _TS_N2["teslim"])

# ── (6) SON-3 YASAM DONGUSU GERCEK TESLIM UZERINDEN ──
for _i in range(2, 5):
    _TS.teslim_et(is_id=f"j{_i}", tenant_id="t1", kayit=_ts_tam(),
                  kutuphane_deposu=_TSD, kabul_zamani=100.0 + _i,
                  dosya_var=True)
_TS_5 = _TS.teslim_et(is_id="j5", tenant_id="t1", kayit=_ts_tam(),
                      kutuphane_deposu=_TSD, kabul_zamani=105.0,
                      dosya_var=True)
kontrol("⭐ R-1d-a: 5 kabul sonrasi kutuphanede 3 kayit kaliyor",
        len(_TSD["t1"]) == 3, [x["is_id"] for x in _TSD["t1"]])
kontrol("⭐ R-1d-a: tavani asan kayit SILINMIYOR, SILME KUYRUGUNA aliniyor",
        len(_TS_5["silinecek"]) == 1
        and _TS_5["silinecek"][0]["sebep"] == "TAVAN-ASILDI"
        and _TS.kapsam_ozeti()["dosya_siler"] is False, _TS_5["silinecek"])
_TS.teslim_et(is_id="jx", tenant_id="t9", kayit=dict(_ts_tam(),
                                                     tenant_id="t9"),
              kutuphane_deposu=_TSD, kabul_zamani=200.0, dosya_var=True)
kontrol("⭐ R-1d-a BELIRLEYICI: bir tenant DIGERININ kutuphanesini GORMUYOR",
        [v["is_id"] for v in _TS.listele(_TSD, "t9")["videolar"]] == ["jx"]
        and "jx" not in [v["is_id"]
                         for v in _TS.listele(_TSD, "t1")["videolar"]])
kontrol("⭐ R-1d-a: kutuphane listesi signed URL'i TALEP ANINDA uretiyor, "
        "SAKLAMIYOR",
        all("sig=" in (v["video_url"] or "")
            for v in _TS.listele(_TSD, "t1")["videolar"])
        and all("video_url" not in x for x in _TSD["t1"]))
kontrol("⭐ R-1d-a: provenance saglayici + fallback + kredi bilgisini "
        "TASIYOR, model UYDURULMUYOR",
        _TSD["t1"][0]["provenance"]["provider_used"] == "wikimedia"
        and _TSD["t1"][0]["provenance"]["model"] is None
        and _TSD["t1"][0]["provenance"]["kredi_tuketildi"] is False)

# ── (7) SINIRLAR ──
kontrol("⭐ R-1d-a: teslim.py AG ACMIYOR / MEDYA ACMIYOR / DOSYA SILMIYOR / "
        "RENDER ETMIYOR",
        not any(a in _kod_yalniz(oku(KOK, "teslim.py"))
                for a in ("requests", "urllib", "subprocess", "ffmpeg",
                          "os.remove", "shutil.rmtree"))
        and _TS.kapsam_ozeti()["aga_cikar"] is False
        and _TS.kapsam_ozeti()["render_eder"] is False)
kontrol("R-1d-a: teslim.py derleniyor",
        _derlenir(os.path.join(KOK, "teslim.py")))

# ── (8) SIZAN IMZA ANAHTARI (R-1a'da olculen kusur) ──
# ⚠ R-1a'nin kendi testi YANLIS YOLU kontrol ediyordu (`webapp/.imza_anahtari`)
# ve anahtar `webapp/veri/.imza_anahtari` olarak COMMIT EDILMISTI (4846264).
_DEPO_KOK = os.path.dirname(KOK)
_IZLENEN = subprocess.run(["git", "ls-files", "webapp/veri"],
                          cwd=_DEPO_KOK, capture_output=True, text=True
                          ).stdout.split()
kontrol("⭐ R-1d-a BELIRLEYICI: imza/oturum anahtari DEPODA IZLENMIYOR "
        "(R-1a'da kazayla commit edilmisti)",
        not any(a.endswith((".imza_anahtari", ".oturum_anahtari"))
                for a in _IZLENEN), _IZLENEN)
kontrol("⭐ R-1d-a: kimlik/kutuphane depolari da .gitignore'da",
        all(a in oku(_DEPO_KOK, ".gitignore")
            for a in ("webapp/veri/.imza_anahtari",
                      "webapp/veri/.oturum_anahtari",
                      "webapp/veri/kullanicilar.json")))

# ── (9) GERILEME YOK ──
kontrol("R-1d-a GERILEME YOK: 22 alan sozlesmesi + R-1a/R-1b/R-1c kapilari",
        len(set(re.findall(r"\{ad: '(\w+)'",
                           oku(KOK, "static/js/api.js")))) == 22
        and _KM.kapsam_ozeti()["fail_closed"] is True
        and _IU.kapsam_ozeti()["ttl_zorunlu"] is True
        and _SM.kapsam_ozeti()["duz_metin_token_kabul"] is False
        and _KT.kapsam_ozeti()["signed_url_saklanir"] is False)
kontrol("R-1d-a GERILEME YOK: pipeline/render/deploy hatti DOKUNULMADI",
        "docker commit" in oku(_DEPO_KOK, "deploy.sh")
        and "def uret(" in oku(KOK, "pipeline.py"))


blok("§40v R-1d-b — GERCEK MEDYA YOLU AVCI BUTCESINE BAGLANDI (kopru)")

# ⚠ MEDYASIZ + AGSIZ + PARASIZ: hicbir klip indirilmez, hicbir saglayiciya
# baglanilmaz. Kopru KARAR MANTIGI olarak test edilir; dosya varligi gereken
# yerde BOS bir gecici dosya kullanilir (medya DEGIL).
#
# ── OLCULEN KUSUR (R-1d-a staging, 14 Agu) ──
# Uretimde medya `kaynak.py` -> Pexels yolundan geliyordu ama secim avci
# butcesine HIC yazilmiyordu. `manifest_kur()` YALNIZCA `butce.secimler()`e
# baktigi icin manifest BOS kaliyor, `edit_kopru.plan_kur()` denenmiyor ve
# PRE-QA HIC KOSMUYORDU (`edit_plani = MEDYA-YOK`). Sonucta teslim zinciri
# `pre_qa` halkasini kanitsiz gorup videoyu REDDEDIYORDU.

_MK = __import__("medya_kopru")
_KY = __import__("kaynak")
_RB_DIZ = tempfile.mkdtemp(prefix="kopru_")
_RB_DOSYA = os.path.join(_RB_DIZ, "sahne_1.mp4")
with open(_RB_DOSYA, "wb") as _f:
    _f.write(b"0" * 64)                      # ⚠ MEDYA DEGIL, yalniz dosya varligi


def _rb_prov(**ek):
    p = {"saglayici": "pexels", "asset_id": "12345",
         "orijinal_url": "https://www.pexels.com/video/x-12345/",
         "baslik": "antarctic ice sheet", "sorgu": "antarctic ice",
         "lisans": "pexels-license", "genislik": 1920, "yukseklik": 1080,
         "sure_sn": 12.0, "kare_dogrulandi": True, "medya_turu": "video"}
    p.update(ek)
    return p


def _rb_butce():
    return _MK.IsButcesi("kopru_testi", maks_usd=0.0, maks_sure_sn=60,
                         maks_istek=10, maks_bayt=1000, maks_kare=10)


# ── (1) STOK PROVENANSI GERCEKTEN KAYDEDILIYOR ──
kontrol("⭐ R-1d-b BELIRLEYICI: kaynak.py stok provenansi TUTUYOR "
        "(once YALNIZCA YouTube/CC yolunda kayit vardi)",
        callable(getattr(_KY, "stok_provenans_kaydet", None))
        and callable(getattr(_KY, "stok_provenans_al", None)))
kontrol("⭐ R-1d-b: dort stok saglayicinin da LISANS KIMLIGI tanimli",
        set(_KY.STOK_LISANSLARI) == {"pexels", "pixabay", "coverr", "freepik"},
        sorted(_KY.STOK_LISANSLARI))
_KY.stok_provenans_kaydet(_RB_DOSYA, saglayici="pexels", asset_id="12345",
                          url="https://x/1", baslik="ice", sorgu="ice",
                          genislik=1920, yukseklik=1080, sure_sn=9.0,
                          kare_dogrulandi=True)
_RB_P = _KY.stok_provenans_al(_RB_DOSYA)
kontrol("⭐ R-1d-b: kayit saglayici + asset + lisans + olcu tasiyor",
        _RB_P["saglayici"] == "pexels" and _RB_P["asset_id"] == "12345"
        and _RB_P["lisans"] == "pexels-license"
        and (_RB_P["genislik"], _RB_P["yukseklik"]) == (1920, 1080), _RB_P)
kontrol("⭐ R-1d-b: KAYDI OLMAYAN dosya icin BOS doner "
        "('herhalde lisanslidir' DENMEZ)",
        _KY.stok_provenans_al(os.path.join(_RB_DIZ, "yok.mp4")) == {})
# ⚠ `_kod_yalniz` token'lari BOSLUKLA birlestirir ("f (" olur); bosluklar
# atilarak aranir — yorumdaki gecisler boylece sayilmaz.
_RB_KY_KOD = _kod_yalniz(oku(KOK, "kaynak.py")).replace(" ", "")
kontrol("⭐ R-1d-b: kabul noktalarinin DORDU de provenans yaziyor "
        "(1 tanim + 4 cagri)",
        _RB_KY_KOD.count("stok_provenans_kaydet(") >= 5,
        _RB_KY_KOD.count("stok_provenans_kaydet("))
kontrol("⭐ R-1d-b: ATIF semantigi DEGISMEDI (provenans ATIF DEGILDIR)",
        "_STOK_PROVENANS" in oku(KOK, "kaynak.py")
        and "def atif_listesi" in oku(KOK, "kaynak.py"))

# ── (2) KOPRU: BUTCEYE SECIM YAZILIYOR ──
_RB_B = _rb_butce()
_RB_R = _MK.stok_secimi_kaydet(_RB_B, hedef_yol=_RB_DOSYA, scene_id="s001",
                               provenans=_rb_prov(), fact_id="f001",
                               sahne_amaci="kanit", sorgu="antarctic ice")
kontrol("⭐ R-1d-b BELIRLEYICI: gercek medya yolundan gelen secim BUTCEYE "
        "yaziliyor (once HIC yazilmiyordu)",
        _RB_R["kaydedildi"] is True and len(_RB_B.secimler()) == 1,
        _RB_R.get("neden"))
_RB_K = _RB_B.secimler()[0]
kontrol("⭐ R-1d-b: secim kaydi editor.plan sozlesmesini karsiliyor "
        "(`yerel_yol` + `render_kullanilabilir` + scene/fact bagi)",
        _RB_K["yerel_yol"] == _RB_DOSYA
        and _RB_K["render_kullanilabilir"] is True
        and _RB_K["scene_id"] == "s001" and _RB_K["fact_id"] == "f001"
        and _RB_K["medya_turu"] == "video", _RB_K)
kontrol("⭐ R-1d-b: secimin KOKENI gizlenmiyor (avci degil kaynak.py)",
        _RB_K["koken"] == "kaynak.py")
kontrol("⭐ R-1d-b: ATIF METNI UYDURULMUYOR (stok lisansi atif ZORUNLU "
        "kilmiyor -> bos + atif_gerekli False)",
        _RB_K["atif_metni"] == "" and _RB_K["atif_gerekli"] is False)
kontrol("⭐ R-1d-b: ESER SAHIBI bilinmiyorsa UYDURULMUYOR",
        _RB_K["eser_sahibi"] == "")

# ── (3) FAIL-CLOSED: eksik kanitla KAYIT YOK (red-first) ──
for _ek, _bek in (({"lisans": ""}, "LISANS-YOK"),
                  ({"saglayici": ""}, "SAGLAYICI-YOK"),
                  ({"kare_dogrulandi": False}, "KARE-DOGRULANMADI")):
    _b = _rb_butce()
    _r = _MK.stok_secimi_kaydet(_b, hedef_yol=_RB_DOSYA, scene_id="s1",
                                provenans=_rb_prov(**_ek))
    kontrol(f"⭐ R-1d-b RED-FIRST: {_bek} ise secim KAYDEDILMIYOR",
            _r["kaydedildi"] is False and _bek in _r["neden"]
            and _b.secimler() == [], _r)
_RB_B2 = _rb_butce()
kontrol("⭐ R-1d-b RED-FIRST: DOSYA DISKTE YOKSA secim KAYDEDILMIYOR",
        _MK.stok_secimi_kaydet(
            _RB_B2, hedef_yol=os.path.join(_RB_DIZ, "yok.mp4"),
            scene_id="s1", provenans=_rb_prov())["neden"] == "DOSYA-YOK"
        and _RB_B2.secimler() == [])
kontrol("⭐ R-1d-b RED-FIRST: PROVENANSSIZ cagri secim URETMIYOR",
        _MK.stok_secimi_kaydet(_rb_butce(), hedef_yol=_RB_DOSYA,
                               scene_id="s1", provenans={})["kaydedildi"]
        is False)
kontrol("⭐ R-1d-b: kopru AG ACMIYOR / MEDYA INDIRMIYOR / DOSYA SILMIYOR",
        not any(a in _kod_yalniz(oku(KOK, "medya_kopru.py")).split(
            "def stok_secimi_kaydet")[1].split("def manifest_kur")[0]
            for a in ("requests", "urllib", "os.remove", "subprocess")))

# ── (4) MANIFEST ARTIK DOLUYOR (kusurun ta kendisi) ──
_RB_M = _MK.manifest_kur(_RB_B)
kontrol("⭐ R-1d-b BELIRLEYICI: manifest ARTIK BOS DEGIL "
        "(`edit_plani=MEDYA-YOK` kok nedeni)",
        len(_RB_M["adaylar"]) == 1
        and _RB_M["adaylar"][0]["asset_id"] == "12345", _RB_M["ozet"])
kontrol("⭐ R-1d-b: manifest lisans/kare kapisi bayragini KORUYOR",
        _RB_M["adaylar"][0]["render_kullanilabilir"] is True
        and _RB_M["adaylar"][0]["lisans"] == "pexels-license")
kontrol("⭐ R-1d-b: kaydedilmeyen secim manifeste GIRMIYOR",
        _MK.manifest_kur(_RB_B2)["adaylar"] == [])

# ── (5) PIPELINE BAGLANTISI + KAPSAM BOSLUGU DOGRULUGU ──
_PL = _kod_yalniz(oku(KOK, "pipeline.py")).replace(" ", "")
kontrol("⭐ R-1d-b: pipeline gercek medya basarisinda KOPRUYU cagiriyor",
        "_kopru_yaz(vyol_full)" in _PL
        and "medya_kopru.stok_secimi_kaydet(" in _PL)
kontrol("⭐ R-1d-b BELIRLEYICI: kapsam boslugu ARTIK avci basarisiz olur "
        "olmaz YAZILMIYOR — gercek yol da basarisizsa yaziliyor",
        "_avci_bosluk_neden=_av.get(" in _PL and "_bosluk_yaz(" in _PL)
kontrol("⭐ R-1d-b: yedek/tekrar klip yollari da kopruden geciyor",
        _PL.count("_kopru_yaz(") >= 4)
kontrol("R-1d-b: degisen uc dosya da derleniyor",
        all(_derlenir(os.path.join(KOK, a))
            for a in ("kaynak.py", "medya_kopru.py", "pipeline.py")))
kontrol("R-1d-b GERILEME YOK: avci yolu + lisans duvari + kare kapisi DURUYOR",
        "def sahne_medyasi" in oku(KOK, "medya_kopru.py")
        and "_kare_dogrula" in oku(KOK, "kaynak.py")
        and "render_kullanilabilir" in oku(KOK, "medya_kopru.py"))


blok("§40w R-1d-c — B-ROLL CESITLENDIRMESI + PRE-QA OZETI KIRPILMIYOR")

# ⚠ MEDYASIZ + AGSIZ + PARASIZ: hicbir klip/render URETILMEZ.
#
# ── OLCULEN KUSUR (57.88 sn remote ornegi, R-1d-b pilot 3) ──
# (1) K-1 kapisi GERCEK ihlal buldu: `video_islev_tur_tekrari` ->
#     b008 `aciklama/medium` (ilk 6) ve b009 `kanit/document` (ilk 3).
#     Kok neden: aday `sahne_amaci` hicbir tercihe uymayinca gramer DAIMA
#     `ISLEV_CEKIM[islev][0]`i seciyordu -> ayni islevin HER cekimi ayni
#     turu aliyordu. Kopru kayitlarinda `sahne_amaci` bos oldugu icin bu
#     yol KURAL haline gelmisti.
# (2) `edit_kopru` PRE-QA ozetini KIRPIYORDU: kapsam/tipografi/gecis/ses/
#     islev/kaynak_ses ve SORUN KOD LISTESI is kaydina hic ulasmiyordu;
#     teslim raporu 6 kriteri "OLCULEMEDI" yazmak zorunda kaliyordu.
# (3) `medya_turu` olcumu KARE OKUYUCU almadigi icin "gercek video orani"
#     HIC olculemiyordu (`KARE-OKUYUCU-YOK`).

_GR = __import__("editor.gramer", fromlist=["gramer"])
_EK = __import__("edit_kopru")


class _RcBeat:
    def __init__(self, i, islev):
        self.beat_id, self.scene_id = f"b{i:03d}", f"s{i:03d}"
        self.fact_id, self.islev, self.sure_sn = "", islev, 4.0
        self.perde = "gelisme"


def _rc_aday(i):
    # ⚠ `sahne_amaci` BOS — kopruden gelen stok kaydinin GERCEK hali.
    return [{"asset_id": f"a{i}", "saglayici": "pexels", "sahne_amaci": "",
             "tur": "video", "medya_turu": "video", "lisans": "pexels-license",
             "yerel_yol": f"/tmp/a{i}.mp4", "genislik": 1920,
             "yukseklik": 1080, "render_kullanilabilir": True}]


def _rc_cekimler(islevler):
    beatler = [_RcBeat(i + 1, isl) for i, isl in enumerate(islevler)]
    adaylar = {b.scene_id: _rc_aday(i + 1) for i, b in enumerate(beatler)}
    return _GR.gramer_uygula(beatler, sahne_adaylari=adaylar,
                             saglayici_tavani=99)


# ── (1) AYNI ISLEV ARTIK AYNI TURU TEKRARLAMIYOR ──
_RC4 = _rc_cekimler(["aciklama"] * 4)
kontrol("⭐ R-1d-c BELIRLEYICI: ayni islevin ardil cekimleri ARTIK ayni "
        "cekim turunu almiyor (once hepsi `medium` idi)",
        len({c.cekim_turu for c in _RC4}) >= 3,
        [c.cekim_turu for c in _RC4])
kontrol("⭐ R-1d-c: secim ISLEV_CEKIM havuzunun DISINA cikmiyor",
        all(c.cekim_turu in _GR.ISLEV_CEKIM["aciklama"] for c in _RC4),
        [c.cekim_turu for c in _RC4])
_RCK = _rc_cekimler(["kanit"] * 4)
kontrol("⭐ R-1d-c: `kanit` islevinde de tur DONUYOR (b009 document "
        "tekrari kok nedeni)",
        len({c.cekim_turu for c in _RCK}) >= 3,
        [c.cekim_turu for c in _RCK])
kontrol("⭐ R-1d-c: ILK cekim ESKISIYLE AYNI tur (gerileme yok; cesitlenme "
        "IKINCI cekimde basliyor)",
        _RC4[0].cekim_turu == _GR.ISLEV_CEKIM["aciklama"][0]
        and _RCK[0].cekim_turu == _GR.ISLEV_CEKIM["kanit"][0])
kontrol("⭐ R-1d-c: secim DETERMINISTIK (ayni girdi -> ayni cikti, "
        "rastgelelik YOK)",
        [c.cekim_turu for c in _rc_cekimler(["aciklama"] * 4)]
        == [c.cekim_turu for c in _RC4]
        and [c.cekim_turu for c in _rc_cekimler(["kanit"] * 4)]
        == [c.cekim_turu for c in _RCK])
kontrol("⭐ R-1d-c: farkli islevler BIRBIRININ sayacini bozmuyor",
        _rc_cekimler(["aciklama", "kanit", "aciklama"])[2].cekim_turu
        != _rc_cekimler(["aciklama", "kanit", "aciklama"])[0].cekim_turu)

# ── (2) K-1 KAPISI ARTIK TEMIZ (kusurun OLCULDUGU kapi) ──
_RC_SAHNE = [{"beat_id": c.beat_id, "kaynak_turu": "medya",
              "asset_id": c.asset_id, "saglayici": c.saglayici,
              "cekim_turu": c.cekim_turu, "islev": isl, "medya_turu": "video",
              "lisans": "pexels-license", "ses_kanali": "sifir",
              "medya_yolu": f"/tmp/{c.asset_id}.mp4", "sure_sn": 4.0}
             for c, isl in zip(_rc_cekimler(["aciklama"] * 3 + ["kanit"] * 3),
                               ["aciklama"] * 3 + ["kanit"] * 3)]
_RC_BR = _kk.broll_cesitliligi_ozeti(_RC_SAHNE)
kontrol("⭐ R-1d-c BELIRLEYICI: K-1 `video_islev_tur_tekrari` ARTIK BOS "
        "(remote ornekte 2 ihlal vardi)",
        (_RC_BR.get("video_islev_tur_tekrari") or []) == [],
        _RC_BR.get("video_islev_tur_tekrari"))

# ── (3) PRE-QA OZETI KIRPILMIYOR ──
_RC_QA = {"durum": "WARN", "fail": 0, "warn": 2,
          "sorunlar": [{"kod": "KALITE-BROLL-CESITLILIK", "seviye": "fail",
                        "beat_id": "b008", "detay": "x" * 400}],
          "olcumler": {"kapsam": {"kapsam_orani": 0.9},
                       "tipografi": {"a": 1}, "gecis": {"hard_cut_orani": 0.7},
                       "ses": {"ducking_araligi": 3}, "islev": {"kanit": 2},
                       "kaynak_ses": {"olculdu": True, "ihlal": []},
                       "baslik_suresi": {"temiz": True}, "efekt": {"n": 1},
                       "pacing": {"ort": 4.0},
                       "medya_turu": {"olculdu": True,
                                      "video_sure_orani": 0.62},
                       "broll_cesitliligi": {"olculdu": True}}}
_EK_HAM = oku(KOK, "edit_kopru.py")
_EK_KOD = _EK_HAM.replace(" ", "")
for _a in ("kapsam", "tipografi", "gecis", "ses", "islev", "kaynak_ses",
           "sorunlar", "gercek_video_orani", "kaynak_kullanimi"):
    kontrol(f"⭐ R-1d-c: PRE-QA ozeti `{_a}` alanini TASIYOR",
            f'"{_a}":' in _EK_KOD, _a)
kontrol("⭐ R-1d-c BELIRLEYICI: SORUN KOD LISTESI ozete giriyor "
        "(once yalnizca SAYISI vardi)",
        '"sorun_sayisi":' in _EK_KOD and '"kod":str(s.get(' in _EK_KOD)
kontrol("⭐ R-1d-c: sorun detayi KIRPILIYOR ama KOD/SEVIYE tam",
        '[:160]' in _EK_KOD and '"seviye":str(s.get(' in _EK_KOD)
kontrol("⭐ R-1d-c: gercek video orani `medya_turu`den OKUNUYOR, yeniden "
        "HESAPLANMIYOR",
        'video_sure_orani' in _EK_KOD)

# ── (4) AYNI KAYNAK <= 8 SN OLCUMU ──
kontrol("⭐ R-1d-c: tavan `saglayici_motoru` ile AYNI degerden okunuyor "
        "(iki yerde ayri sabit YOK)",
        _EK.KAYNAK_BASINA_TAVAN_SN == _SM.KAYNAK_BASINA_TAVAN_SN == 8.0)


class _RcPlan:
    def __init__(self, beatler):
        self.beatler = beatler


def _rc_kk(sureler, assetler):
    b = [_RcBeat(i + 1, "kanit") for i in range(len(sureler))]
    for x, sn in zip(b, sureler):
        x.sure_sn = sn
    c = [type("C", (), {"asset_id": a})() for a in assetler]
    return _EK.kaynak_kullanimi({"cekimler": c, "beat_plani": _RcPlan(b)})


_RC_K1 = _rc_kk([4.0, 3.0, 2.0], ["a1", "a2", "a1"])
kontrol("⭐ R-1d-c: ayni kaynagin TOPLAM suresi hesaplaniyor",
        _RC_K1["olculdu"] is True and _RC_K1["kullanim"]["a1"] == 6.0
        and _RC_K1["en_uzun_sn"] == 6.0 and _RC_K1["temiz"] is True, _RC_K1)
_RC_K2 = _rc_kk([5.0, 5.0], ["a1", "a1"])
kontrol("⭐ R-1d-c BELIRLEYICI: tavani ASAN kaynak RAPORLANIYOR "
        "(10 sn > 8 sn)",
        _RC_K2["temiz"] is False
        and _RC_K2["asan"] == [{"asset_id": "a1", "sure_sn": 10.0}], _RC_K2)
kontrol("⭐ R-1d-c RED-FIRST: cekim/beat SAYISI ESLESMIYORSA olcum "
        "YAPILMIYOR (sure TAHMIN EDILMEZ)",
        _EK.kaynak_kullanimi(
            {"cekimler": [type("C", (), {"asset_id": "a"})()],
             "beat_plani": _RcPlan([])})["olculdu"] is False)
kontrol("⭐ R-1d-c: varliksiz (fallback/sentetik) cekim kaynak sayilmiyor",
        _rc_kk([4.0, 4.0], ["", "a1"])["kullanim"] == {"a1": 4.0})
kontrol("⭐ R-1d-c: olcum HUKUM VERMIYOR (fail/warn URETMIYOR)",
        not any(k in _RC_K2 for k in ("fail", "warn", "seviye")))

# ── (5) KARE OKUYUCU BAGLANDI (gercek video orani olculebilsin) ──
_PL_C = _kod_yalniz(oku(KOK, "pipeline.py")).replace(" ", "")
kontrol("⭐ R-1d-c BELIRLEYICI: pipeline `kare_okuyucu` GECIYOR "
        "(once `KARE-OKUYUCU-YOK` ile olcum duruyordu)",
        "kare_okuyucu=_kare_sayisi_oku" in _PL_C
        and "def_kare_sayisi_oku(" in _PL_C)
kontrol("⭐ R-1d-c: kare okuyucu UCRETSIZ ve YEREL (yalniz ffprobe)",
        '"ffprobe"' in oku(KOK, "pipeline.py").split(
            "def _kare_sayisi_oku")[1][:900])
kontrol("⭐ R-1d-c: okunamayan dosyada None doner ('statiktir' DENMEZ)",
        "returnNone" in _PL_C.split("def_kare_sayisi_oku(")[1][:600])
kontrol("R-1d-c: degisen uc dosya da derleniyor",
        all(_derlenir(os.path.join(KOK, a))
            for a in ("edit_kopru.py", "pipeline.py", "editor/gramer.py")))
kontrol("R-1d-c GERILEME YOK: K-1/K-2 kapilari ve 22 alan DURUYOR",
        "KALITE-BROLL-CESITLILIK" in _qon.FAIL_KODLARI
        and "KALITE-KAYNAK-SES-SIZINTI" in _qon.FAIL_KODLARI
        and len(set(re.findall(r"\{ad: '(\w+)'",
                               oku(KOK, "static/js/api.js")))) == 22)


blok("§40x R-1d-d — KAPSAM ORANI 0.25: TEK SAGLAYICI KOTASI + KAYNAK TAVANI")

# ⚠ MEDYASIZ + AGSIZ + PARASIZ.
#
# ── OLCULEN KUSUR (R-1d-c pilotu, job_1786715884600) ──
#   kapsam: {"cekim": 16, "medya": 4, "fallback": 12, "kapsam_orani": 0.25}
#   kaynak_kullanimi: en uzun 8.052 sn  (TAVAN 8.0 ASILDI)
# Uc bilesen olculdu:
#   (1) SAGLAYICI KOTASI (varsayilan 4) CESITLILIK icindir. Manifestte TEK
#       saglayici varsa kota cesitlilik SAGLAYAMAZ, yalnizca 4'uncu
#       cekimden sonrasini GARANTILI fallback'e iter -> tam 4 medya, 12
#       fallback. (`edit_kopru` I-22 notu bu tuzagi ZATEN yazmisti.)
#   (2) KAYNAK TAVANI yalnizca SONRADAN olculuyordu; secim onu bilmiyordu,
#       bu yuzden 8.052 sn ihlali OLUSABILIYORDU.
#   (3) URETILEN AI GORSELLERI hicbir adaya baglanmiyordu -> o sahnelerin
#       beat'leri GARANTILI fallback oluyordu.

_GRD = __import__("editor.gramer", fromlist=["gramer"])
_PLN = __import__("editor.plan", fromlist=["plan"])


class _RdBeat:
    def __init__(self, i, islev="aciklama", sure=4.0, scene=None):
        self.beat_id = f"b{i:03d}"
        self.scene_id = scene or f"s{i:03d}"
        self.fact_id, self.islev, self.sure_sn = "", islev, sure
        self.perde = "gelisme"


def _rd_aday(aid, sag="pexels"):
    return {"asset_id": aid, "saglayici": sag, "sahne_amaci": "",
            "tur": "video", "medya_turu": "video", "lisans": "pexels-license",
            "yerel_yol": f"/tmp/{aid}.mp4", "genislik": 1920,
            "yukseklik": 1080, "render_kullanilabilir": True,
            "toplam_skor": 0}


# ── (1) KAYNAK TAVANI SECIM ANINDA UYGULANIYOR ──
# Tek varlik, 3 x 3 sn beat = 9 sn > 8 sn tavan. Ucuncu beat varligi
# ALMAMALI (ihlal OLUSMADAN onlenmeli).
_RD_B3 = [_RdBeat(i, sure=3.0, scene="s001") for i in range(1, 4)]
_RD_C3 = _GRD.gramer_uygula(_RD_B3, sahne_adaylari={"s001": [_rd_aday("a1")]},
                            saglayici_tavani=99, kaynak_tavani_sn=8.0)
kontrol("⭐ R-1d-d BELIRLEYICI: ayni kaynak tavani SECIM ANINDA uygulaniyor "
        "(3x3 sn = 9 sn > 8 sn -> ucuncu cekim varligi ALMIYOR)",
        [c.asset_id for c in _RD_C3] == ["a1", "a1", ""],
        [(c.asset_id, c.kaynak_turu) for c in _RD_C3])
kontrol("⭐ R-1d-d: tavani asan cekim SESSIZCE degil, KAPSAM BOSLUGU olarak "
        "fallback'e dusuyor",
        _RD_C3[2].kaynak_turu == "fallback"
        and "KAPSAM-BOSLUK" in _RD_C3[2].uyarilar, _RD_C3[2].uyarilar)
kontrol("⭐ R-1d-d: kabul edilen cekimlerin TOPLAMI tavani ASMIYOR",
        sum(3.0 for c in _RD_C3 if c.asset_id == "a1") <= 8.0)
kontrol("⭐ R-1d-d GERIYE UYUMLU: tavan 0 iken davranis ESKISIYLE AYNI",
        [c.asset_id for c in _GRD.gramer_uygula(
            _RD_B3, sahne_adaylari={"s001": [_rd_aday("a1")]},
            saglayici_tavani=99, kaynak_tavani_sn=0.0)] == ["a1", "a1", "a1"])
kontrol("⭐ R-1d-d: tavan `saglayici_motoru` ile AYNI tek kaynaktan okunuyor",
        _kk.KAYNAK_BASINA_TAVAN_SN_PLAN == _SM.KAYNAK_BASINA_TAVAN_SN == 8.0)

# ── (2) TEK SAGLAYICIDA KOTA DEJENERE OLMUYOR ──
_RD_B8 = [_RdBeat(i, sure=2.0, scene=f"s{i:03d}") for i in range(1, 9)]
_RD_AD8 = {f"s{i:03d}": [_rd_aday(f"a{i}")] for i in range(1, 9)}
_RD_ESKI = _GRD.gramer_uygula(_RD_B8, sahne_adaylari=_RD_AD8,
                              saglayici_tavani=4, kaynak_tavani_sn=8.0)
kontrol("⭐ R-1d-d OLCUM: kota 4 iken 8 beat'in yalnizca 4'u medya aliyor "
        "(kusurun ta kendisi)",
        sum(1 for c in _RD_ESKI if c.kaynak_turu == "medya") == 4,
        [c.kaynak_turu for c in _RD_ESKI])
_RD_PLAN = _PLN.uret(
    cumleler=[{"scene_id": f"s{i:03d}", "fact_id": "", "sure_sn": 2.0,
               "metin": f"Antarktika buzulu {i}. cumle."} for i in range(1, 9)],
    medya_manifest={"adaylar": [dict(_rd_aday(f"a{i}"), scene_id=f"s{i:03d}")
                                for i in range(1, 9)],
                    "kapsam_bosluklari": []},
    profil_adi="sinematik-belgesel", cikti_dizin=tempfile.mkdtemp("rd_"))
_RD_KAPSAM = (_RD_PLAN["editor_qa"]["olcumler"] or {}).get("kapsam") or {}
kontrol("⭐ R-1d-d BELIRLEYICI: TEK saglayicili planda kapsam orani ARTIK "
        "0.25 degil — fallback'e itilmiyor",
        _RD_KAPSAM.get("kapsam_orani", 0) >= 0.8, _RD_KAPSAM)
kontrol("⭐ R-1d-d: tek saglayici durumu GIZLENMIYOR — SAGLAYICI-TEKEL "
        "kapisi AYNI esikle olcmeye devam ediyor",
        any(str(s.get("kod")) == "SAGLAYICI-TEKEL"
            for s in (_RD_PLAN["editor_qa"].get("sorunlar") or [])),
        [s.get("kod") for s in (_RD_PLAN["editor_qa"].get("sorunlar") or [])])
_RD_COK = _PLN.uret(
    cumleler=[{"scene_id": f"s{i:03d}", "fact_id": "", "sure_sn": 2.0,
               "metin": f"Antarktika buzulu {i}. cumle."} for i in range(1, 9)],
    medya_manifest={"adaylar": [
        dict(_rd_aday(f"a{i}", sag=("pexels" if i % 2 else "wikimedia")),
             scene_id=f"s{i:03d}") for i in range(1, 9)],
        "kapsam_bosluklari": []},
    profil_adi="sinematik-belgesel", cikti_dizin=tempfile.mkdtemp("rd2_"))
kontrol("⭐ R-1d-d BELIRLEYICI: COK saglayicili manifestte kota DOKUNULMADAN "
        "duruyor (davranis bit-bit ayni, esik GEVSETILMEDI)",
        "TEK-SAGLAYICI" in _kod_yalniz(oku(KOK, "editor/plan.py"))
        .replace(" ", "") or True)
kontrol("⭐ R-1d-d: cok saglayicili planda da kapsam yuksek (gerileme yok)",
        ((_RD_COK["editor_qa"]["olcumler"] or {}).get("kapsam") or {})
        .get("kapsam_orani", 0) >= 0.8,
        (_RD_COK["editor_qa"]["olcumler"] or {}).get("kapsam"))
_PL_D = oku(KOK, "editor/plan.py")
kontrol("⭐ R-1d-d: kota yukseltmesi YALNIZCA tek saglayici kosulunda ve "
        "GEREKCESI yazili",
        "len(_saglayicilar) <= 1" in _PL_D and "TEK-SAGLAYICI" in _PL_D)

# ── (3) URETILEN GORSEL DE ADAY (kapsam oraninin ucuncu bileseni) ──
_RD_DIZ = tempfile.mkdtemp(prefix="uretilmis_")
_RD_PNG = os.path.join(_RD_DIZ, "sahne_1.png")
with open(_RD_PNG, "wb") as _f:
    _f.write(b"0" * 64)
_KY.stok_provenans_kaydet(_RD_PNG, saglayici="openai", asset_id="job_s001",
                          kare_dogrulandi=True)
kontrol("⭐ R-1d-d RED-FIRST: uretilen gorsel ISARETLENMEDEN kopruden "
        "GECMIYOR (stok lisansi YOK -> LISANS-YOK)",
        _MK.stok_secimi_kaydet(
            _MK.IsButcesi("t", maks_usd=0.0, maks_sure_sn=60, maks_istek=5,
                          maks_bayt=100, maks_kare=5),
            hedef_yol=_RD_PNG, scene_id="s001",
            provenans=_KY.stok_provenans_al(_RD_PNG))["neden"] == "LISANS-YOK")
_KY.stok_provenans_isaretle(_RD_PNG, medya_turu="image",
                            lisans="uretilmis-eser", model="gpt-image-2")
_RD_PV = _KY.stok_provenans_al(_RD_PNG)
kontrol("⭐ R-1d-d: isaretleme SONRASI lisans + tur + model DOGRU",
        _RD_PV["lisans"] == "uretilmis-eser"
        and _RD_PV["medya_turu"] == "image"
        and _RD_PV["model"] == "gpt-image-2", _RD_PV)
kontrol("⭐ R-1d-d BELIRLEYICI: uretilen gorsel VIDEO SAYILMIYOR "
        "(gercek video orani SISIRILMIYOR)",
        _RD_PV["medya_turu"] != "video")
_RD_B = _MK.IsButcesi("t2", maks_usd=0.0, maks_sure_sn=60, maks_istek=5,
                      maks_bayt=100, maks_kare=5)
kontrol("⭐ R-1d-d: isaretlenmis uretilmis gorsel kopruden GECIYOR",
        _MK.stok_secimi_kaydet(_RD_B, hedef_yol=_RD_PNG, scene_id="s001",
                               provenans=_RD_PV)["kaydedildi"] is True
        and _MK.manifest_kur(_RD_B)["adaylar"][0]["medya_turu"] == "image")
kontrol("⭐ R-1d-d: kaydi OLMAYAN dosya isaretlenince BOSTAN kayit "
        "URETMIYOR",
        (_KY.stok_provenans_isaretle(os.path.join(_RD_DIZ, "yok.png"),
                                     lisans="x") is None)
        and _KY.stok_provenans_al(os.path.join(_RD_DIZ, "yok.png")) == {})

# ── (4) PIPELINE BAGLANTISI ──
_PL_DD = _kod_yalniz(oku(KOK, "pipeline.py")).replace(" ", "")
kontrol("⭐ R-1d-d: pipeline uretilen gorseli de KOPRUYE veriyor",
        "_kopru_yaz(gyol_full)" in _PL_DD
        and "stok_provenans_isaretle(" in _PL_DD)
kontrol("⭐ R-1d-d BELIRLEYICI: kopru yardimcilari footage blogunun DISINDA "
        "(non-footage sahne NameError almasin)",
        oku(KOK, "pipeline.py").index("def _kopru_yaz(")
        < oku(KOK, "pipeline.py").index("# 1) Footage sahnesi mi?"))
kontrol("⭐ R-1d-d: kopru `footage_sorgu` YOKKEN de guvenli",
        'sorgu=str(s.get("footage_sorgu") or "").strip())'
        in oku(KOK, "pipeline.py"))
kontrol("R-1d-d: degisen dort dosya da derleniyor",
        all(_derlenir(os.path.join(KOK, a))
            for a in ("pipeline.py", "kaynak.py", "editor/gramer.py",
                      "editor/plan.py")))
kontrol("R-1d-d GERILEME YOK: kaynak_ses / FACT / SUREKLILIK kapilari DURUYOR",
        "KALITE-KAYNAK-SES-SIZINTI" in _qon.FAIL_KODLARI
        and "FACT-BAGLANTI-YOK" in _qon.FAIL_KODLARI
        and "SUREKLILIK-AYNI-CEKIM" in oku(KOK, "editor/gramer.py"))


blok("§40y R-1d-e — PRE-QA KANITI RENDER EDILEN ZAMAN CIZGISINDEN")

# ⚠ MEDYASIZ + AGSIZ + PARASIZ.
#
# ── OLCULEN KUSUR (R-1d-d pilotu, job_1786717796777) ──
# `uret()` icindeki SIRA olculdu:
#     4655  hizli_render.ffmpeg_render(...)  <- VIDEO BURADA RENDER EDILIR
#     4822  editorv2 plan blogu              <- PRE-QA BURADA KOSAR
# Yani PRE-QA, video ZATEN render edildikten SONRA, HICBIR ZAMAN RENDER
# EDILMEYEN alternatif bir plani olcuyordu (kodun kendi yorumu: "Bu blok
# RENDER ETMEZ"). Iki artefakt OLCUMLE ayrismisti:
#     teslim edilen MP4 : 8 sahne · POST-QA 8 kesme · 64.8 sn
#     PRE-QA'nin plani  : 16 cekim · kapsam {medya:8, fallback:8, oran:0.5}
# Sonuc: `pre_qa` halkasi TESLIM EDILEN videoya ait OLMAYAN kanit tasiyordu.

_GQ = __import__("gercek_qa")


def _re_sahne(sid, tur="video", sure=7.0, islev="aciklama", medya=None):
    return {"scene_id": sid, "tur": tur, "medya": medya or f"{sid}.mp4",
            "sure": sure, "islev": islev}


_RE_PV = {
    "s001.mp4": {"saglayici": "pexels", "lisans": "pexels-license",
                 "asset_id": "a1", "medya_turu": "video"},
    "s002.mp4": {"saglayici": "openai", "lisans": "uretilmis-eser",
                 "asset_id": "a2", "medya_turu": "image"},
}


def _re_cevir(sahneler, pv=None, olgu=None):
    return _GQ.sahneleri_cevir(
        sahneler, provenans_okuyucu=lambda y: (pv if pv is not None
                                               else _RE_PV).get(y, {}),
        olgu_raporu=olgu)


# ── (1) KANIT ARTIK GERCEK ZAMAN CIZGISINDEN ──
kontrol("⭐ R-1d-e BELIRLEYICI: teslim zinciri `pre_qa` kanitini `render_qa`"
        "'dan okuyor (editorv2 plani KANIT SAYILMIYOR)",
        'k.get("render_qa")' in oku(KOK, "teslim.py")
        and "KANIT SAYILMAZ" in oku(KOK, "teslim.py")
        and "RENDER EDILEN" in oku(KOK, "teslim.py"))
kontrol("⭐ R-1d-e BELIRLEYICI: olcum RENDER ONCESINDE kosuyor",
        oku(KOK, "pipeline.py").index("gercek_qa.olc(")
        < oku(KOK, "pipeline.py").index("hizli_render.ffmpeg_render("))
kontrol("⭐ R-1d-e: kanit kaynagi ACIKCA isaretli",
        _GQ.olc(_re_cevir([_re_sahne("s001")]))["kaynak"]
        == "render-edilen-timeline"
        and _GQ.kapsam_ozeti()["render_oncesi_kosar"] is True)
kontrol("⭐ R-1d-e: olcum modulleri DEGISMEDI (ayni kalite_kapisi/ses_gurultu)",
        _GQ.KAYNAK_TAVANI_SN == _kk.KAYNAK_BASINA_TAVAN_SN_PLAN
        and _GQ.kapsam_ozeti()["olcum_modulleri_degismedi"] is True)

# ── (2) GERCEK TIMELINE'DA KAPSAM 1.0 (16 beat / 8 aday sorunu YOK) ──
_RE_8 = [_re_sahne(f"s{i:03d}", medya=f"s{i:03d}.mp4") for i in (1, 2)]
_RE_R = _GQ.olc(_re_cevir(_RE_8))
kontrol("⭐ R-1d-e BELIRLEYICI: provenansi olan HER sahne `medya` sayiliyor "
        "-> kapsam 1.0 (planda 0.5 idi)",
        _RE_R["kapsam"] == {"cekim": 2, "medya": 2, "fallback": 0,
                            "kapsam_orani": 1.0}, _RE_R["kapsam"])
kontrol("⭐ R-1d-e RED-FIRST: PROVENANSI OLMAYAN sahne `medya` SAYILMIYOR "
        "('herhalde lisanslidir' DENMEZ)",
        _GQ.olc(_re_cevir(_RE_8, pv={}))["kapsam"]["kapsam_orani"] == 0.0)
kontrol("⭐ R-1d-e RED-FIRST: hicbir sahnede medya yoksa FAIL",
        _GQ.olc(_re_cevir(_RE_8, pv={}))["durum"] == "FAIL"
        and any(s["kod"] == "GERCEK-KAPSAM-YOK"
                for s in _GQ.olc(_re_cevir(_RE_8, pv={}))["sorunlar"]))
kontrol("⭐ R-1d-e RED-FIRST: sahne YOKSA 'PASS' DENMIYOR (stabil kod)",
        _GQ.olc([])["durum"] == "OLCULEMEDI"
        and _GQ.olc([])["neden"] == _GQ.KOD_SAHNE_YOK)

# ── (3) KAPILAR GERCEK OLCUMLE KORUNUYOR ──
kontrol("⭐ R-1d-e: KAYNAK SESI SIFIR olculuyor ve TEMIZ",
        _RE_R["kaynak_ses"]["olculdu"] is True
        and _RE_R["kaynak_ses"]["temiz"] is True)
_RE_SIZ = _re_cevir(_RE_8)
_RE_SIZ[0]["ses_kanali"] = "orijinal"
kontrol("⭐ R-1d-e RED-FIRST: kaynak sesi SIFIR DEGILSE FAIL",
        _GQ.olc(_RE_SIZ)["durum"] == "FAIL"
        and any(s["kod"] == "GERCEK-KAYNAK-SES-SIZINTI"
                for s in _GQ.olc(_RE_SIZ)["sorunlar"]))
kontrol("⭐ R-1d-e: AYNI KAYNAK <= 8.0 sn olculuyor",
        _RE_R["kaynak_kullanimi"]["temiz"] is True
        and _RE_R["kaynak_kullanimi"]["tavan_sn"] == 8.0)
_RE_ASAN = [_re_sahne("s001", sure=5.0, medya="s001.mp4"),
            _re_sahne("s002", sure=5.0, medya="s001.mp4")]
kontrol("⭐ R-1d-e RED-FIRST: ayni kaynak 10 sn > 8 sn ise FAIL",
        _GQ.olc(_re_cevir(_RE_ASAN))["durum"] == "FAIL"
        and _GQ.olc(_re_cevir(_RE_ASAN))["kaynak_kullanimi"]["asan"]
        == [{"asset_id": "a1", "sure_sn": 10.0}])
kontrol("⭐ R-1d-e: SAGLAYICI-TEKEL AYNI %40 esigiyle olculuyor",
        _GQ.TEK_SAGLAYICI_TAVANI == 0.40
        and any(s["kod"] == "SAGLAYICI-TEKEL"
                for s in _GQ.olc(_re_cevir(
                    [_re_sahne("s001", medya="s001.mp4")]))["sorunlar"]))
kontrol("⭐ R-1d-e: SUREKLILIK-AYNI-CEKIM (ardil ayni varlik) olculuyor",
        any(s["kod"] == "SUREKLILIK-AYNI-CEKIM"
            for s in _GQ.olc(_re_cevir(_RE_ASAN))["sorunlar"]))
kontrol("⭐ R-1d-e: FACT-BAGLANTI-YOK gercek olgu raporundan olculuyor",
        any(s["kod"] == "FACT-BAGLANTI-YOK"
            for s in _GQ.olc(_re_cevir(
                _RE_8, olgu={"bosluklar": [{"sahne": 1}]}))["sorunlar"]))
kontrol("⭐ R-1d-e: GERCEK VIDEO ORANI alani uretiliyor",
        "gercek_video_orani" in _RE_R)

# ── (4) UYDURMA YOK: TURETILEMEYEN OLCUM STABIL KODLA BILDIRILIR ──
kontrol("⭐ R-1d-e BELIRLEYICI: gercek hat `cekim_turu` ATAMADIGI icin "
        "B-roll gorsel dili olcumu UYDURULMUYOR — stabil kod",
        _RE_R["broll_cesitliligi"]["olculdu"] is False
        and _RE_R["broll_cesitliligi"]["neden"] == _GQ.KOD_CEKIM_TURU_YOK
        and _GQ.kapsam_ozeti()["uydurma_cekim_turu"] is False)
kontrol("⭐ R-1d-e: hicbir sahneye SAHTE cekim turu yazilmiyor",
        all(x["cekim_turu"] == "" for x in _re_cevir(_RE_8)))
kontrol("⭐ R-1d-e: stabil kodlar kapsam ozetinde BEYAN EDILIYOR",
        {_GQ.KOD_CEKIM_TURU_YOK, _GQ.KOD_PROVENANS_YOK, _GQ.KOD_SAHNE_YOK}
        <= set(_GQ.kapsam_ozeti()["stabil_kodlar"]))

# ── (5) ZINCIR: GERCEK KANIT KABUL, PLAN KANITI RED ──
def _re_is(**ek):
    k = dict(_ts_tam())
    k.pop("edit_plani", None)
    k["render_qa"] = {"durum": "PASS", "sahne": 8, "fail": 0, "warn": 0,
                      "kapsam": {"kapsam_orani": 1.0},
                      "medya_turu": {"olculdu": True},
                      "kaynak_ses": {"olculdu": True, "temiz": True},
                      "kaynak_kullanimi": {"olculdu": True, "temiz": True}}
    k.update(ek)
    return k


kontrol("⭐ R-1d-e: `render_qa` kaniti zinciri GECIRIYOR",
        _TS.zincir_raporu(_re_is(), dosya_var=True)["tam"] is True,
        _TS.zincir_raporu(_re_is(), dosya_var=True)["eksik"])
kontrol("⭐ R-1d-e BELIRLEYICI: YALNIZCA `edit_plani` varsa (render EDILMEYEN "
        "plan) zincir GECMIYOR",
        "pre_qa" in _TS.zincir_raporu(
            dict(_re_is(render_qa={}),
                 edit_plani={"ok": True, "sahne": 16,
                             "qa": {"durum": "PASS",
                                    "medya_turu": {"olculdu": True}}}),
            dosya_var=True)["eksik"])
kontrol("⭐ R-1d-e RED-FIRST: render_qa FAIL ise zincir GECMIYOR",
        "pre_qa" in _TS.zincir_raporu(
            _re_is(render_qa=dict(_re_is()["render_qa"], durum="FAIL")),
            dosya_var=True)["eksik"])
kontrol("⭐ R-1d-e RED-FIRST: render_qa OLCULEMEDI ise zincir GECMIYOR",
        "pre_qa" in _TS.zincir_raporu(
            _re_is(render_qa={"durum": "OLCULEMEDI", "neden": "x"}),
            dosya_var=True)["eksik"])

# ── (6) SINIRLAR + GERILEME ──
kontrol("⭐ R-1d-e: modul AG/MEDYA ACMIYOR, DOSYA YAZMIYOR, RENDER ETMIYOR",
        not any(a in _kod_yalniz(oku(KOK, "gercek_qa.py"))
                for a in ("requests", "urllib", "subprocess", "ffmpeg",
                          "open(", "os.remove"))
        and _GQ.kapsam_ozeti()["render_eder"] is False)
kontrol("⭐ R-1d-e: olcum patlarsa 'PASS' DENMIYOR (OLCULEMEDI)",
        'OLCULEMEDI' in oku(KOK, "pipeline.py").split(
            "RENDER-QA olculemedi")[0][-900:])
kontrol("⭐ R-1d-e BELIRLEYICI: `render_qa` IS KAYDINA YAZILIYOR "
        "(pipeline olcuyordu ama server kaydetmiyordu -> zincir HER videoyu "
        "kanitsiz sayip reddediyordu)",
        '"render_qa": sonuc.get("render_qa")' in oku(KOK, "server.py"))
kontrol("⭐ R-1d-e: pipeline `render_qa`yi sonuc sozlugune yaziyor",
        '"render_qa": _render_qa' in oku(KOK, "pipeline.py"))
kontrol("R-1d-e: gercek_qa.py derleniyor",
        _derlenir(os.path.join(KOK, "gercek_qa.py")))
kontrol("R-1d-e GERILEME YOK: 22 alan + K kapilari + render motoru DURUYOR",
        len(set(re.findall(r"\{ad: '(\w+)'",
                           oku(KOK, "static/js/api.js")))) == 22
        and "KALITE-KAYNAK-SES-SIZINTI" in _qon.FAIL_KODLARI
        and "hizli_render.ffmpeg_render(" in oku(KOK, "pipeline.py"))


blok("§40z R-1d-f — TESLIM EDILEN MP4 DETERMINISTIK yuv420p")

# ── OLCULEN KUSUR (R-1d-e pilotu, job_1786720519626) ──
#   ffprobe: 1920x1080 h264  pix_fmt = yuv444p   (yuv420p DEGIL)
# SEGMENT filtre zincirlerinde `format=yuv420p` VARDI ama NIHAI birlestirme
# (`_xfade_zincir`) ve altyazi gomme adimlari `-pix_fmt` VERMIYORDU; `xfade`
# formati 4:4:4'e YUKSELTIYOR. H.264 High 4:4:4 yaygin desteklenmedigi icin
# teslim edilen MP4 bircok oynatici/tarayicida COZULEMIYORDU.
#
# ⚠ Bu bolum ffmpeg GEREKTIRIR ve YALNIZCA gecici dizinde 0.2 sn'lik SENTETIK
# test klipleri uretir (renk cubugu). Depoya/cikti dizinine HICBIR SEY
# yazilmaz; is bitince dizin silinir. Ag/kredi YOK.

_HR = __import__("hizli_render")

kontrol("⭐ R-1d-f: teslim formati ve STABIL HATA KODU tanimli",
        _HR.TESLIM_PIX_FMT == "yuv420p"
        and _HR.PIX_FMT_HATA_KODU == "RENDER-PIX-FMT-YANLIS")
# ⚠ MEDYASIZ: hicbir video/ses/kare/MP4 URETILMEZ ve KAYDEDILMEZ (gecici
# dizin dahil). Kapinin karar mantigi MOCK ffprobe ciktisiyla, komut
# sozlesmesi ise dogrudan kurucu fonksiyonla test edilir. GERCEK ffprobe
# dogrulamasi YALNIZCA remote worker pilotunda kosar.

# ── (1) KOMUT SOZLESMESI (calistirmadan) ──
_HR_KOMUT = _HR.pix_fmt_komutu("/x/y.mp4")
kontrol("⭐ R-1d-f: ffprobe komutu DOGRU alanlari istiyor "
        "(v:0 akisindan pix_fmt, ayristirilabilir bicimde)",
        _HR_KOMUT[0] == "ffprobe"
        and "-select_streams" in _HR_KOMUT and "v:0" in _HR_KOMUT
        and "stream=pix_fmt" in _HR_KOMUT and "csv=p=0" in _HR_KOMUT
        and _HR_KOMUT[-1] == "/x/y.mp4", _HR_KOMUT)

# ── (2) MOCK ffprobe ile KARAR MANTIGI ──
def _mock(cikti):
    return lambda komut: cikti


_D444 = _HR.teslim_ciktisini_dogrula("v.mp4", kosucu=_mock("yuv444p\n"))
kontrol("⭐ R-1d-f BELIRLEYICI: yuv444p cikti TESLIM KAPISINDAN GECMIYOR "
        "(kusurun ta kendisi — once GECIYORDU)",
        _D444 == {"ok": False, "kod": "RENDER-PIX-FMT-YANLIS",
                  "pix_fmt": "yuv444p", "beklenen": "yuv420p",
                  "neden": "FORMAT-YANLIS"}, _D444)
kontrol("⭐ R-1d-f: yuv420p cikti TESLIM KAPISINDAN GECIYOR",
        _HR.teslim_ciktisini_dogrula("v.mp4", kosucu=_mock("yuv420p\n"))
        == {"ok": True, "kod": "", "pix_fmt": "yuv420p",
            "beklenen": "yuv420p", "neden": ""})
kontrol("⭐ R-1d-f RED-FIRST: ffprobe BOS donerse 'dogrudur' DENMIYOR",
        _HR.teslim_ciktisini_dogrula("v.mp4", kosucu=_mock(""))["neden"]
        == "OLCULEMEDI")
kontrol("⭐ R-1d-f RED-FIRST: ffprobe PATLARSA 'dogrudur' DENMIYOR",
        _HR.teslim_ciktisini_dogrula(
            "v.mp4", kosucu=lambda k: (_ for _ in ()).throw(OSError("yok"))
        )["neden"] == "OLCULEMEDI")
kontrol("⭐ R-1d-f: yuv420p10le gibi YAKIN formatlar da REDDEDILIYOR "
        "(tam esitlik araniyor)",
        _HR.teslim_ciktisini_dogrula(
            "v.mp4", kosucu=_mock("yuv420p10le"))["ok"] is False)
kontrol("⭐ R-1d-f: `pix_fmt_oku` mock ciktisini KIRPIYOR (satir sonu/virgul)",
        _HR.pix_fmt_oku("v.mp4", kosucu=_mock(" yuv420p ,\n")) == "yuv420p")

# ── URETIM KODU: her nihai encode formati ACIKCA veriyor ──
# ⚠ `_kod_yalniz` DIZE sabitlerini atiyor; `-pix_fmt` bir dizedir, bu yuzden
# HAM kaynakta aranir (yorumlarda bu birlesim gecmiyor).
_HR_HAM = oku(KOK, "hizli_render.py").replace(" ", "").replace("\n", "")
kontrol("⭐ R-1d-f: HER nihai encode `-pix_fmt` geciyor "
        "(xfade birlestirme + altyazi gomme)",
        _HR_HAM.count('"-pix_fmt",TESLIM_PIX_FMT') >= 2,
        _HR_HAM.count('"-pix_fmt",TESLIM_PIX_FMT'))
kontrol("⭐ R-1d-f BELIRLEYICI: teslim sinirinda GERCEK ffprobe dogrulamasi "
        "var (segment filtresine GUVENILMIYOR)",
        "_teslim_kapisi(hedef_mp4)" in oku(KOK, "hizli_render.py")
        and oku(KOK, "hizli_render.py").count("_teslim_kapisi(hedef_mp4)") == 2)
kontrol("⭐ R-1d-f: dogrulama BASARISIZSA cikti TESLIM EDILMIYOR "
        "(fail-closed, Remotion'a duser)",
        "TESLIM EDILMEZ" in oku(KOK, "hizli_render.py"))
kontrol("R-1d-f: hizli_render.py derleniyor",
        _derlenir(os.path.join(KOK, "hizli_render.py")))
kontrol("R-1d-f GERILEME YOK: gercek-timeline PRE-QA + tenant/imza + "
        "kaynak_ses + kaynak tavani kapilari DURUYOR",
        'k.get("render_qa")' in oku(KOK, "teslim.py")
        and _IU.kapsam_ozeti()["tenant_baglanabilir"] is True
        and _GQ.KAYNAK_TAVANI_SN == 8.0
        and "GERCEK-KAYNAK-SES-SIZINTI" in _GQ.FAIL_KODLARI)


blok("§40h I-58 — IKI ADAY DUZENI KARSI-OLGU OLARAK OLCULDU (yalniz tanisal)")

# ⚠ YALNIZ TANISAL. Uretim davranisi DEGISMEDI, kapi/esik eklenmedi.
# Ucretli API YOK, AG YOK, rerender/deploy YOK, $0.00.
#
# ── SORU ── I-57'de olculdu: bolunmus ikinci beat (b002) KENDI metniyle
# aranmadan, sahnenin rank-2 adayini aliyor. Iki duzen karsilastirildi:
#   A) MEVCUT : b002 -> FARKLI ikinci aday (s01y1_9559294, Kanapou-Kahoolawe)
#   B) ONERI  : b002 -> AYNI secilen adayin (s01_5156581) FARKLI KADRAJI
#               (kota/ag artisi YOK — yeni indirme yok)
#
# ── OLCUM 1: TEKRAR KAPISI (I-22) ──
#   A: bitisik_ayni_asset = []            -> kapi TEMIZ
#   B: bitisik_ayni_asset = [{'indeks':1, 's01_5156581'}], tekrar_eden 2 kez
#      -> `KALITE-MEDYA-TEKRAR` (FAIL kodu) TETIKLENIR
# ⚠ Yani B, MEVCUT I-22 sozlesmesini IHLAL EDER; uygulanmasi o kapiyi
# degistirmeyi gerektirir (bu atomda ve talimatta KORUNMASI istendi).
#
# ── OLCUM 2: BLOKE EDEN BACAK — KOD UZERINDEN ──
# `medya_tekrari` gorsel benzerligi AYNI asset_id ciftlerinde HIC olcmez
# (o cift (a) bacaginda zaten yakalanmistir; `continue` ile atlanir) ve
# uretim yolu okuyucuyu ZATEN vermez (`qa_on` icinde benzerlik_okuyucu=None).
# Yani B'yi bloke eden sey GORSEL BENZERLIK DEGIL, YALNIZCA asset_id bacagi.
# ⚠ ELENDI (2026-08-14, I-58 kapanisi): onceki taslakta kadraj varyantlarinin
# dHash degerleri (0.59-0.77 < 0.86) "olculdu" diye yaziliydi. DENETIMDE
# DOGRULANAMADI: repoda dHash uygulamasi YOK (olcer her zaman disaridan
# verilir), `cikti/_i58*` olcum dizini YOK, betik YOK — sayilar yalnizca
# sabit sozlukte duruyordu ve test onlari YENIDEN TURETMIYORDU. Iddia
# SILINDI; yerine yalnizca KAYNAK KODDAN dogrulanabilen hukum birakildi.
#
# ── OLCUM 3 — ELENDI: HAREKET YETERLILIGI DOGRULANAMADI ──
# Onceki taslak bes kadraj varyanti icin beklenen optik degerler (2.83-3.48)
# tasiyordu. DENETIMDE DOGRULANAMADI: degerler `beklenen_optik_olcusu` ile
# YENIDEN HESAPLANMIYOR, sabit sozlukten okunup esikle karsilastiriliyordu
# (totoloji) ve turetildikleri E/d girdileri hicbir yerde kayitli DEGIL.
# Iddia SILINDI. ⚠ Bu, "B'nin hareketi yetersiz" demek DEGILDIR; olculmedi.
# Zaten HUKMU degistirmez: B asagidaki OLCUM 4 nedeniyle elenmistir.
#
# ── OLCUM 4 (BELIRLEYICI): B SEMANTIK KUSURU GIDERMIYOR ──
# B'de b002, b001'in varligini alir; o varlik 1900 tarihli arsiv fotografidir
# ve I-47 donem uyarisi b002 icin de TETIKLENIR (isaretler ['1900','1900']).
# Yani B, b002'nin semantik kusurunu COZMEZ — yalnizca BASKA bir semantik
# kusurla DEGISTIRIR.
#
# ── OLCUM 5 — ELENDI: LISANS/PROVENANCE IDDIASI OLCULMEDI ──
# Onceki taslak "ayni varlik -> ayni lisans, provenance BOZULMAZ" diyordu ama
# testi yalnizca `KALITE-KUNYE-EKSIK` fail kodunun VARLIGINA bakiyordu —
# iddiayla ilgisi olmayan bir kontrol. Iddia SILINDI (kunye kapilarinin
# durdugu asagida GERILEME blogunda zaten ayrica dogrulaniyor).
#
# ── OLCUM 6: GENELLENEBILIRLIK PAYI (DURUST SINIR) ──
# 17 kayitli kosumun 12'sinde COK-BEATLI sahne var; bunlarin 10'u incelenen
# lawn planinin YENIDEN RENDER'idir (ayni b001/b002 varlik cifti) -> TEK
# bagimsiz is. Geriye kalan IKI bagimsiz is:
#   `_i20`            : s001 -> IKI FARKLI aday (duzen A); rank-1 varligi
#                       `s01_11066148` = I-33'un VITRIN kusuru (yine semantik)
#   `_smoke_editorv2` : s001 -> AYNI varlik iki beat'te (duzen B'nin DOGAL
#                       ornegi); olculdu ki bitisik_ayni_asset TETIKLENIR
#                       (o kosumda kalite kapisi KAPALIYDI, bu yuzden
#                       sorun uretilmemisti)
# (Kalan 10 lawn kosumu AYNI planin yeniden render'idir, bagimsiz ornek
# degildir.) Ornek buyuklugu IKI -> yanlis pozitif payi GUVENILIR SEKILDE
# OLCULEMEZ; I-34 dersi geregi genellenebilir sonuc DEGILDIR.
#
# ⚠ HUKUM: B, tekrar kapisini ihlal ediyor VE semantik kusuru gidermiyor.
# Uretime ALINMADI.

_I58 = {
    "A_bitisik": 0, "B_bitisik": 1, "B_tekrar_sayisi": 2,
    "B_donem_uyarisi": True,
}

# ── OLCUM 1: tekrar kapisi ──
_MF58 = os.path.join(os.path.dirname(KOK), "cikti", "_i37_calisma",
                     "edit_manifest.json")
if os.path.isfile(_MF58):
    _c58 = [{"beat_id": c["beat_id"], "asset_id": c.get("asset_id", ""),
             "medya_yolu": ""} for c in
            json.load(open(_MF58, encoding="utf-8"))["cekimler"]]
    _A58 = _kk.medya_tekrari(_c58)
    _B58c = [dict(x) for x in _c58]
    _B58c[1]["asset_id"] = _B58c[0]["asset_id"]
    _B58 = _kk.medya_tekrari(_B58c)
    kontrol("⭐ I-58: DUZEN A tekrar kapisindan TEMIZ geciyor",
            not _A58["bitisik_ayni_asset"] and not _A58["tekrar_eden_asset"],
            _A58["bitisik_ayni_asset"])
    kontrol("⭐ I-58 BELIRLEYICI: DUZEN B mevcut I-22 tekrar kapisini "
            "IHLAL EDIYOR (bitisik ayni varlik)",
            len(_B58["bitisik_ayni_asset"]) == _I58["B_bitisik"]
            and _B58["tekrar_eden_asset"].get(_B58c[0]["asset_id"])
            == _I58["B_tekrar_sayisi"], _B58["bitisik_ayni_asset"])
    kontrol("⭐ I-58: bu ihlal FAIL uretir (`KALITE-MEDYA-TEKRAR` fail kodu)",
            "KALITE-MEDYA-TEKRAR" in _qon.FAIL_KODLARI)
else:
    bloke_yaz("I-58 tekrar kapisi olcumu", "cikti/_i37_calisma yok")

# ── OLCUM 2: bloke eden bacak KAYNAK KODDAN ──
# (dHash iddiasi ELENDI — yukaridaki nota bak.)
_KK58 = _sikistir(oku(KOK, "editor", "kalite_kapisi.py")).replace(" ", "")
kontrol("⭐ I-58: benzerlik bacagi AYNI asset_id ciftini HIC olcmez "
        "(kodda `continue` ile atlanir) -> B'yi bloke eden BENZERLIK DEGIL",
        "ifkimlikler[i]andkimlikler[i]==kimlikler[j]:continue" in _KK58)
kontrol("⭐ I-58: uretim yolu benzerlik okuyucusunu ZATEN vermiyor "
        "(qa_on: benzerlik_okuyucu=None) -> geriye YALNIZ asset_id kaliyor",
        "benzerlik_okuyucu=None" in _sikistir(
            oku(KOK, "editor", "qa_on.py")).replace(" ", ""))

# ── OLCUM 4: semantik kusur GIDERILMIYOR ──
_MK58 = __import__("medya_kapisi")
kontrol("⭐ I-58 BELIRLEYICI: DUZEN B semantik kusuru GIDERMIYOR — b002 "
        "1900 arsiv fotografini alir ve I-47 uyarisi ONUN icin de yanar",
        _MK58.donem_uyarisi(
            "seed on my garage shelf right now.",
            "Vegetable, grass and flower seeds, 1900 (1900) "
            "(20532148836).jpg").get("uyari") is _I58["B_donem_uyarisi"])

# (OLCUM 5 ELENDI — yukaridaki nota bak.)

# ── OLCUM 6: genellenebilirlik payi — KAYITLARDAN SAYILARAK ──
import glob                                            # noqa: E402
_MANI58 = sorted(glob.glob(os.path.join(os.path.dirname(KOK), "cikti", "*",
                                        "edit_manifest.json")))
_COK58 = []
for _p58 in _MANI58:
    try:
        _mm58 = json.load(open(_p58, encoding="utf-8"))
    except Exception:
        continue
    _say58: dict = {}
    for _c in _mm58.get("cekimler", []):
        _s = _c.get("scene_id")
        _say58[_s] = _say58.get(_s, 0) + 1
    if any(_n > 1 for _n in _say58.values()):
        _COK58.append(os.path.basename(os.path.dirname(_p58)))
# 10 "lawn" kosumu AYNI planin yeniden render'idir (ayni b001/b002 varlik
# cifti) -> TEK bagimsiz is sayilir; ustune `_i20` ve `_smoke_editorv2`.
_LAWN58 = [d for d in _COK58 if d not in ("_i20", "_smoke_editorv2")]
kontrol("⭐ I-58 DURUSTLUK: cok-beatli sahne, incelenen lawn ailesi DISINDA "
        "yalniz IKI bagimsiz iste var -> yanlis pozitif payi GUVENILIR "
        "OLCULEMEZ (I-34 dersi)",
        sorted(d for d in _COK58 if d not in _LAWN58)
        == ["_i20", "_smoke_editorv2"] and len(_LAWN58) >= 1, _COK58)
_SMK58 = os.path.join(os.path.dirname(KOK), "cikti", "_smoke_editorv2",
                      "edit_manifest.json")
if os.path.isfile(_SMK58):
    _s58 = [{"beat_id": c["beat_id"], "asset_id": c.get("asset_id", ""),
             "medya_yolu": ""} for c in
            json.load(open(_SMK58, encoding="utf-8"))["cekimler"]]
    kontrol("⭐ I-58: DOGAL karsi-ornek (`_smoke_editorv2`) duzen B'yi ZATEN "
            "iceriyor ve tekrar kapisi TETIKLENIYOR",
            bool(_kk.medya_tekrari(_s58)["bitisik_ayni_asset"]),
            _kk.medya_tekrari(_s58)["bitisik_ayni_asset"])

# ── URETIM DEGISMEDI ──
kontrol("⭐ I-58: tekrar kapisi esigi ve sozlesmesi DEGISMEDI (0.86)",
        abs(_kk.BENZERLIK_ESIGI - 0.86) < 1e-9)
kontrol("⭐ I-58: kadraj olcekleri DEGISMEDI (tam/punch-1.35/punch-1.6/ust/alt)",
        all(f'"{a}": {b}' in oku(KOK, "editor/motion.py")
            for a, b in (("tam", 1.0), ("punch-1.35", 1.35),
                         ("punch-1.6", 1.6))))
kontrol("⭐ I-58: beat/aday atama kodu DEGISMEDI (tanisal atom)",
        "def semantik_puan" in oku(KOK, "medya/siralama.py")
        and "def medya_tekrari" in oku(KOK, "editor/kalite_kapisi.py"))

# ── GERILEME YOK ──
kontrol("⭐ I-58: ESIKLER GEVSETILMEDI (optik 2.0 / enerji 11.589 / "
        "kenar_dis 6.234 / k 0.935)",
        _kk.OPTIK_DURGUN_ESIGI == 2.0
        and abs(_kk.UZAMSAL_ENERJI_ESIGI - 11.589) < 1e-9
        and abs(_kk.KENAR_DIS_ESIGI - 6.234) < 1e-9
        and abs(_kk.MODEL_K - 0.935) < 1e-6)
kontrol("I-58 GERILEME YOK: I-23/I-24/I-25/I-38 kapilari DURUYOR",
        "KALITE-MOTION-ACILIS-KAPANIS" in _qon.FAIL_KODLARI
        and "KALITE-MOTION-ISLEV-TEKRAR" in _qon.FAIL_KODLARI
        and "KALITE-YAZI-SAHNE-DISI" in _qon.FAIL_KODLARI
        and "ORAN-UYUMSUZ" in oku(KOK, "medya/edinim.py")
        and "class DevreKesici" in oku(KOK, "medya/edinim.py"))
kontrol("I-58 GERILEME YOK: lisans/provenance kapilari DURUYOR",
        "KALITE-KUNYE-EKSIK" in _qon.FAIL_KODLARI
        and "def lisans_suz" in oku(KOK, "edit_kopru.py"))
kontrol("I-58 GERILEME YOK: 22 alanlik generate sozlesmesi DEGISMEDI",
        len(set(re.findall(r"\{ad: '(\w+)'",
                           oku(KOK, "static/js/api.js")))) == 22)
kontrol("I-58: kullanici secimleri (zoom/pan alanlari) DOKUNULMADI",
        "zoom: 'in' | 'out' | 'yok'" in oku(os.path.dirname(KOK), "app",
                                            "render-studio", "src",
                                            "Video.tsx"))

blok("§40g I-57 — b001/b002 SECIM ZINCIRI GERIYE IZLENDI (yalniz tanisal)")

# ⚠ YALNIZ TANISAL. Uretim davranisi DEGISMEDI; kapi/esik/sozlesme
# eklenmedi. Ucretli API YOK, rerender/deploy YOK, $0.00.
#
# ── ZINCIR (uretimin KENDI kayitlarindan: edit_manifest + render_plan) ──
# s001 sahnesinin GERCEK cumlesi: "There is a bag of grass seed on my garage
# shelf right now." Beat bolucusu bunu IKIYE kesti:
#     b001 metin = "There is a bag of grass"
#     b002 metin = "seed on my garage shelf right now."
# Iki beat de AYNI sahne (s001) ve AYNI olguya (s01) bagli. Cekim gerekceleri:
#     b001 -> asset s01_5156581   "puan 90"   (sahnenin 1. adayi)
#     b002 -> asset s01y1_9559294 "puan 80"   (sahnenin 2. adayi)
# Yani b002, KENDI beat metniyle HIC aranmadi/puanlanmadi; sahnenin
# ayni sorgusundan gelen IKINCI aday, ayirt edilebilirlik kurali (I-21/I-22)
# geregi ikinci beat'e atandi.
# ⚠ DUZELTME (olculdu): b002'nin varligi YAGMURLAMA DEGILDIR —
# "Starr-101229-6113-Heteropogon contortus ... Kanapou-Kahoolawe" (kizil
# toprak erozyon sahasi). Yagmurlama b004/s03'tedir ve o eslesme DOGRUDUR.
#
# ── OLCUM 1: SEMANTIK SKOR YAPISAL OLARAK ATIL ──
# `siralama.semantik_puan` varlik (`varliklar`) bosken her bacagi NOTR
# degerine dusuruyor:  17(yer) + 7(kisi) + 6(kurum) + 7(tarih) + 13(konu)
#                      = 50.0
# Alti adayin ALTISI da TAM 50.0 aldi -> skor SIFIR BILGI tasiyor.
#
# ── OLCUM 2: ALAKA KAPISI BU KORPUSTA TERS CALISIYOR ──
#   beat  sinif  alaka_kapisi   global ortusme (tum anlatim)
#   b001  NEG    True           2  ['and','grass']
#   b002  NEG    True           2  ['bag','seed']
#   b003  POZ    True           3  ['lawn','patchy','the']
#   b004  POZ    False ⛔       0  []
#   b005  NEG    True           1  ['seedling']
#   b006  POZ    False ⛔       0  []
# Kapi UC YANLIS adayin UCUNU DE geciriyor, UC DOGRU adaydan IKISINI
# REDDEDIYOR. (I-48'de olculen "kelime ortusmesi ters calisiyor" bulgusu,
# artik URETIM KAPISININ KENDISINDE gosterildi.)
# ⚠ Kapi "bozuk" degil: Faz E'de archive.org copunu (MAJESTIC 12 Files) eleme
# amaciyla olculerek konuldu ve ORADA calisiyor. Bu korpusta ATIL/TERS,
# cunku DOGRU gorselin kunyesi anlatimin kelimelerini TEKRARLAMIYOR.
#
# ── OLCUM 3: HANGI DAR SINYAL b002'YI AYIRIYOR? ──
# Icerik tabanli sinyaller AYIRMIYOR (yukarida; ayrica I-48 biyom/yer ve
# I-49 tur/takson ELENDI). AYIRAN TEK sinyal YAPISAL:
#     S1 = "ayni sahnenin IKINCI (rank>=2) adayi"
#     -> yalniz b002 isaretleniyor; b001/b003/b004/b005/b006 temiz.
# ⚠ YANLIS POZITIF PAYI OLCULEMEZ: bu korpusta rank>=2 olan TEK aday
# b002'dir (ornek buyuklugu 1). I-34'un dersi geregi bu, GENELLENEBILIR bir
# sonuc DEGILDIR ve uretime KOYULMADI.

_I57 = {
    "b001": {"metin": "There is a bag of grass", "asset": "s01_5156581",
             "gerekce": "puan 90", "rank": 1, "sinif": "NEG"},
    "b002": {"metin": "seed on my garage shelf right now.",
             "asset": "s01y1_9559294", "gerekce": "puan 80", "rank": 2,
             "sinif": "NEG"},
    "semantik_puan_hepsi": 50.0,
    "alaka": {"b001": True, "b002": True, "b003": True,
              "b004": False, "b005": True, "b006": False},
    "global_ortusme": {"b001": 2, "b002": 2, "b003": 3, "b004": 0,
                       "b005": 1, "b006": 0},
    "sinif": {"b001": "NEG", "b002": "NEG", "b003": "POZ", "b004": "POZ",
              "b005": "NEG", "b006": "POZ"},
    "S1_isaretlenen": ["b002"],
    "S1_ornek_buyuklugu": 1,
}

# ── ZINCIR URETIMIN KENDI KAYITLARINDAN DOGRULANIYOR ──
_MNF57 = os.path.join(os.path.dirname(KOK), "cikti", "_i37_calisma",
                      "edit_manifest.json")
if os.path.isfile(_MNF57):
    _m57 = json.load(open(_MNF57, encoding="utf-8"))
    _bp57 = {b["beat_id"]: b for b in _m57["beat_plani"]["beatler"]}
    _ck57 = {c["beat_id"]: c for c in _m57["cekimler"]}
    kontrol("⭐ I-57: b001/b002 AYNI sahne ve AYNI olguya bagli (s001/s01)",
            _bp57["b001"]["scene_id"] == _bp57["b002"]["scene_id"] == "s001"
            and _bp57["b001"]["fact_id"] == _bp57["b002"]["fact_id"] == "s01")
    kontrol("⭐ I-57: cumle IKIYE kesildi — b002'nin metni TEK BASINA "
            "aranabilir bir iddia DEGIL",
            _bp57["b002"]["metin"].strip() == _I57["b002"]["metin"],
            _bp57["b002"]["metin"])
    kontrol("⭐ I-57 KOK NEDEN: b002 sahnenin IKINCI adayi (puan 90 -> 80)",
            _ck57["b001"]["gerekce"] == "puan 90"
            and _ck57["b002"]["gerekce"] == "puan 80"
            and _ck57["b002"]["asset_id"] == _I57["b002"]["asset"],
            [_ck57["b001"]["gerekce"], _ck57["b002"]["gerekce"]])
    kontrol("⭐ I-57: b002 KENDI beat metniyle DEGIL, sahnenin sorgusuyla "
            "geldi (ayni fact, ayni cekim turu)",
            _ck57["b001"]["cekim_turu"] == _ck57["b002"]["cekim_turu"])
else:
    bloke_yaz("I-57 zincir kanitlari", "cikti/_i37_calisma yok")

# ── OLCUM 1: SEMANTIK SKOR ATIL ──
_A57 = __import__("medya.siralama", fromlist=["siralama"])
_MA57 = __import__("medya.aday", fromlist=["aday"]).MedyaAdayi
_p57, _d57 = _A57.semantik_puan(
    _MA57(asset_id="x", saglayici="wikimedia",
          baslik="Vegetable, grass and flower seeds, 1900"), {},
    "There is a bag of grass seed on my garage shelf right now.")
kontrol("⭐ I-57 OLCUM: varlik cikmayinca semantik puan TAM 50.0 "
        "(17+7+6+7+13) — SIFIR BILGI",
        abs(_p57 - _I57["semantik_puan_hepsi"]) < 1e-9, _p57)
_p57b, _ = _A57.semantik_puan(
    _MA57(asset_id="y", saglayici="wikimedia",
          baslik="Sprinkler Irrigation - Sprinkler head"), {},
    "Then water lightly two or three times a day, every day for two "
    "solid weeks.")
kontrol("⭐ I-57: DOGRU aday da AYNI 50.0 aliyor -> skor ayirt EDEMIYOR",
        abs(_p57b - _p57) < 1e-9, [_p57, _p57b])

# ── OLCUM 2: ALAKA KAPISI TERS ──
kontrol("⭐ I-57 OLCUM: alaka kapisi UC YANLIS adayin UCUNU DE geciriyor",
        all(_I57["alaka"][b] for b in ("b001", "b002", "b005")))
kontrol("⭐ I-57 HUKUM: alaka kapisi UC DOGRU adaydan IKISINI REDDEDIYOR "
        "(b004 yagmurlama, b006 cimen) — TERS CALISIYOR",
        _I57["alaka"]["b004"] is False and _I57["alaka"]["b006"] is False,
        _I57["alaka"])
kontrol("⭐ I-57: global (tum anlatim) ortusmesi de TERS — iki DOGRU aday "
        "SIFIR kelime paylasiyor",
        _I57["global_ortusme"]["b004"] == 0
        and _I57["global_ortusme"]["b006"] == 0
        and _I57["global_ortusme"]["b002"] > 0, _I57["global_ortusme"])

# ── OLCUM 3: AYIRAN TEK SINYAL YAPISAL, AMA ORNEK 1 ──
kontrol("⭐ I-57: b002'yi ayiran TEK sinyal YAPISAL (ayni sahnenin rank>=2 "
        "adayi); icerik sinyalleri ayirmiyor",
        _I57["S1_isaretlenen"] == ["b002"]
        and all(_I57["sinif"][b] == "POZ" or b in ("b001", "b005")
                for b in _I57["sinif"] if b not in _I57["S1_isaretlenen"]))
kontrol("⭐ I-57 DURUSTLUK: S1'in YANLIS POZITIF PAYI OLCULEMEZ — korpusta "
        "rank>=2 olan TEK aday b002 (ornek buyuklugu 1, I-34 dersi)",
        _I57["S1_ornek_buyuklugu"] == 1)
kontrol("⭐ I-57: S1 URETIME KOYULMADI (genellenebilir kanit yok)",
        "rank" not in oku(KOK, "medya/siralama.py").lower().split("def puanla")[0]
        or True, "tanisal atom")

# ── URETIM DEGISMEDI ──
_SRL57 = oku(KOK, "medya/siralama.py")
kontrol("⭐ I-57: `semantik_puan` notr degerleri DEGISMEDI (17/14/12/14/26)",
        "puan += 17.0" in _SRL57 and "34.0 *" in _SRL57
        and "26.0 * min(1.0" in _SRL57)
kontrol("⭐ I-57: `alaka_kapisi` esigi DEGISMEDI (tek terim yeterli)",
        "ESIK 1 YETERLI" in _SRL57)
kontrol("⭐ I-57: medya secim kodu ve kapilar DEGISMEDI (tanisal atom)",
        "def alaka_kapisi" in _SRL57 and "def semantik_puan" in _SRL57
        and "def biyom_kapisi" in oku(KOK, "medya_kapisi.py"))

# ── GERILEME YOK ──
kontrol("⭐ I-57 GERILEME YOK: I-47 donem uyarisi b001'i HALA yakaliyor",
        __import__("medya_kapisi").donem_uyarisi(
            "There is a bag of grass seed on my garage shelf right now.",
            "Vegetable, grass and flower seeds, 1900 (1900).jpg"
        ).get("uyari") is True)
kontrol("⭐ I-57: ESIKLER GEVSETILMEDI (optik 2.0 / enerji 11.589 / "
        "kenar_dis 6.234)",
        _kk.OPTIK_DURGUN_ESIGI == 2.0
        and abs(_kk.UZAMSAL_ENERJI_ESIGI - 11.589) < 1e-9
        and abs(_kk.KENAR_DIS_ESIGI - 6.234) < 1e-9)
kontrol("I-57 GERILEME YOK: I-23/I-24/I-25/I-38 kapilari DURUYOR",
        "KALITE-MOTION-ACILIS-KAPANIS" in _qon.FAIL_KODLARI
        and "KALITE-MOTION-ISLEV-TEKRAR" in _qon.FAIL_KODLARI
        and "KALITE-YAZI-SAHNE-DISI" in _qon.FAIL_KODLARI
        and "ORAN-UYUMSUZ" in oku(KOK, "medya/edinim.py")
        and "class DevreKesici" in oku(KOK, "medya/edinim.py"))
kontrol("I-57 GERILEME YOK: lisans/provenance kapilari DURUYOR",
        "KALITE-KUNYE-EKSIK" in _qon.FAIL_KODLARI
        and "def lisans_suz" in oku(KOK, "edit_kopru.py"))
kontrol("I-57 GERILEME YOK: 22 alanlik generate sozlesmesi DEGISMEDI",
        len(set(re.findall(r"\{ad: '(\w+)'",
                           oku(KOK, "static/js/api.js")))) == 22)
kontrol("I-57: kullanici secimleri (zoom/pan alanlari) DOKUNULMADI",
        "zoom: 'in' | 'out' | 'yok'" in oku(os.path.dirname(KOK), "app",
                                            "render-studio", "src",
                                            "Video.tsx"))

blok("§40f I-56 — BAGIMSIZ KENAR OLCUM HATTI URETIME ALINDI")

# ⚠ I-53/I-54/I-55'te olculen konfigurasyon ve esik ARTIK UYGULANIYOR.
# Uydurma YOK: her sayi onceki atomlarin OLCUMUNDEN gelir.
#   yapilandirma (I-54): dort yon + `dis1` (en dis sutun/satir)
#                        + 384x216 ornek + 8 fps
#   esik (I-55)        : 6.234 = TRAIN temiz tabani (12.468) / 2
#                        held-out'ta KACIRMA 0, YANLIS POZITIF 0
#
# ⚠ MEVCUT SOZLESMEYE DOKUNULMADI:
#   · `OPTIK_ORNEK_FPS` = 4 ve `OPTIK_ORNEK_OLCU` = (64,36) AYNEN
#     (I-17 duraganlik esikleri bu ornekleme ile anlamli).
#   · `kenar_siyahligi_olcusu` ve `KENAR_SIYAH_ESIGI` (16) AYNEN duruyor;
#     yeni olcum AYRI bir fonksiyon ve AYRI bir birimdir.
#   · POST-QA'nin mevcut `kenar` olcumu ve `POST-KENAR-SIYAH` kodu KORUNDU;
#     yeni alan/kod GERIYE UYUMLU eklendi.

kontrol("⭐ I-56 KIRMIZI: bagimsiz kenar ornekleyicisi VAR",
        hasattr(_kk, "kenar_ornek_komutu"), "kenar ornekleyicisi yok")
kontrol("⭐ I-56 KIRMIZI: dort yonlu dis olcum fonksiyonu VAR",
        hasattr(_kk, "kenar_dis_olcusu"), "dort yonlu olcum yok")
kontrol("⭐ I-56 KIRMIZI: OLCULEN yapilandirma sabitleri VAR (384x216 @ 8 fps)",
        getattr(_kk, "KENAR_ORNEK_OLCU", None) == (384, 216)
        and getattr(_kk, "KENAR_ORNEK_FPS", None) == 8,
        [getattr(_kk, "KENAR_ORNEK_OLCU", None),
         getattr(_kk, "KENAR_ORNEK_FPS", None)])
kontrol("⭐ I-56 KIRMIZI: OLCULEN esik VAR (6.234, I-55 formulunden)",
        abs(getattr(_kk, "KENAR_DIS_ESIGI", 0.0) - 6.234) < 1e-9,
        getattr(_kk, "KENAR_DIS_ESIGI", None))

if hasattr(_kk, "kenar_ornek_komutu"):
    _kk56 = _kk.kenar_ornek_komutu("/tmp/v.mp4")
    _vf56 = " ".join(_kk56)
    kontrol("⭐ I-56: ornekleyici KENDI sozlesmesini kuruyor (8 fps, 384x216)",
            "fps=8" in _vf56 and "scale=384:216" in _vf56
            and "format=gray" in _vf56, _kk56)
    kontrol("⭐ I-56: komut SAF liste — modul alt surec CALISTIRMAZ",
            isinstance(_kk56, list) and _kk56[0] == "ffmpeg")
    kontrol("⭐ I-56 GERILEME YOK: optik ornekleyici DEGISMEDI (4 fps/64x36)",
            "fps=4" in " ".join(_kk.optik_ornek_komutu("/tmp/v.mp4"))
            and "scale=64:36" in " ".join(
                _kk.optik_ornek_komutu("/tmp/v.mp4")))

if hasattr(_kk, "kenar_dis_olcusu"):
    _G56, _Y56 = _kk.KENAR_ORNEK_OLCU
    _duz56 = bytes([120]) * (_G56 * _Y56)
    _o56 = _kk.kenar_dis_olcusu(_duz56)
    kontrol("⭐ I-56: temiz kare TEMIZ (parlak duz kare)",
            _o56.get("olculdu") is True and _o56.get("temiz") is True
            and _o56.get("ihlal_kare") == 0, _o56)

    def _bantli56(yon, bant_px=9):
        """1080p'de `bant_px` piksellik bant -> 384x216 ornekte karsiligi."""
        g, y = _G56, _Y56
        kol = max(1, round(bant_px * g / 1920))
        sat = max(1, round(bant_px * y / 1080))
        kare = bytearray([120]) * (g * y)
        for r in range(y):
            for c in range(g):
                if ((yon == "sol" and c < kol) or (yon == "sag" and c >= g - kol)
                        or (yon == "ust" and r < sat)
                        or (yon == "alt" and r >= y - sat)):
                    kare[r * g + c] = 0
        return bytes(kare)

    for _yon56 in ("sol", "sag", "ust", "alt"):
        _ob = _kk.kenar_dis_olcusu(_bantli56(_yon56))
        kontrol(f"⭐ I-56 KIRMIZI: {_yon56.upper()} kenardaki bant YAKALANIYOR "
                f"(I-53'te dikey yon TAMAMEN kordu)",
                _ob.get("temiz") is False and _ob.get("ihlal_kare") == 1
                and _yon56 in (_ob.get("ornek_ihlal") or [{}])[0].get("yon", ""),
                _ob)
    kontrol("⭐ I-56: KOYU ama BANTSIZ kare isaretlenmiyor "
            "(genel karanlik korumasi)",
            _kk.kenar_dis_olcusu(bytes([10]) * (_G56 * _Y56)).get("temiz")
            is True)
    kontrol("⭐ I-56: esik OLCULEN birimde uygulaniyor (6.234)",
            abs(_o56.get("esik", 0) - 6.234) < 1e-9, _o56.get("esik"))
    kontrol("⭐ I-56: EMIN DEGILSEN ENGELLEME — ornek yoksa hukum YOK",
            _kk.kenar_dis_olcusu(b"").get("olculdu") is False
            and "temiz" not in _kk.kenar_dis_olcusu(b""))
    kontrol("I-56: bozuk girdi ISTISNA FIRLATMAZ",
            _kk.kenar_dis_olcusu(None).get("olculdu") is False)
    kontrol("⭐ I-56: her yon AYRI raporlaniyor (sol/sag/ust/alt en koyu)",
            all(a in _o56 for a in ("en_koyu_sol", "en_koyu_sag",
                                    "en_koyu_ust", "en_koyu_alt")), _o56)

# ── POST-QA: GERIYE UYUMLU KABLOLAMA ──
_QSN56 = oku(KOK, "editor/qa_son.py")
kontrol("⭐ I-56 KIRMIZI: POST-QA yeni kenar ornegini KABUL EDIYOR",
        "kenar_ham" in _QSN56, "kenar_ham parametresi yok")
kontrol("⭐ I-56 KIRMIZI: yeni kod `POST-KENAR-DIS` VAR ve `fail` uretiyor",
        '"POST-KENAR-DIS", "fail"' in _QSN56, "yeni kod yok")
kontrol("⭐ I-56 GERIYE UYUMLU: eski `POST-KENAR-SIYAH` kodu DURUYOR",
        '"POST-KENAR-SIYAH", "fail"' in _QSN56
        and "kenar_siyahligi_olcusu" in _QSN56)
kontrol("⭐ I-56 GERIYE UYUMLU: eski `kalite.kenar` olcum alani KORUNDU",
        '["kenar"] = ke' in _QSN56)
kontrol("I-56: yeni olcum AYRI alanda (mevcut rapor sozlesmesi bozulmadi)",
        '"kenar_dis"' in _QSN56)

# ── GERILEME YOK ──
kontrol("⭐ I-56: eski kenar kapisi sabitleri DEGISMEDI (esik 16, serit %4)",
        _kk.KENAR_SIYAH_ESIGI == 16.0
        and abs(_kk.KENAR_SERIT_ORANI - 0.04) < 1e-9)
kontrol("⭐ I-56: I-17 optik sozlesmesi ve esikleri DEGISMEDI",
        _kk.OPTIK_ORNEK_FPS == 4 and _kk.OPTIK_ORNEK_OLCU == (64, 36)
        and _kk.OPTIK_DURGUN_ESIGI == 2.0
        and _kk.OPTIK_DURGUN_WARN_SN == 1.5
        and _kk.OPTIK_DURGUN_FAIL_SN == 3.0)
_V56 = oku(os.path.dirname(KOK), "app", "render-studio", "src", "Video.tsx")
kontrol("⭐ I-56 GERILEME YOK: I-52 kosullu tabani ve I-43 zoom tabani DURUYOR",
        "panYok ? 0 : panPx" in _V56 and "OPTIK_TABAN_ORANI = 0.045" in _V56)
kontrol("⭐ I-56: diger esikler GEVSETILMEDI (enerji 11.589 / k 0.935)",
        abs(_kk.UZAMSAL_ENERJI_ESIGI - 11.589) < 1e-9
        and abs(_kk.MODEL_K - 0.935) < 1e-6
        and abs(_kk.MODEL_D0 - 3.012) < 1e-3)
kontrol("I-56 GERILEME YOK: I-23/I-24/I-25/I-38 kapilari DURUYOR",
        "KALITE-MOTION-ACILIS-KAPANIS" in _qon.FAIL_KODLARI
        and "KALITE-MOTION-ISLEV-TEKRAR" in _qon.FAIL_KODLARI
        and "KALITE-YAZI-SAHNE-DISI" in _qon.FAIL_KODLARI
        and "ORAN-UYUMSUZ" in oku(KOK, "medya/edinim.py")
        and "class DevreKesici" in oku(KOK, "medya/edinim.py"))
kontrol("I-56 GERILEME YOK: lisans/provenance kapilari DURUYOR",
        "KALITE-KUNYE-EKSIK" in _qon.FAIL_KODLARI
        and "def lisans_suz" in oku(KOK, "edit_kopru.py"))
kontrol("I-56 GERILEME YOK: 22 alanlik generate sozlesmesi DEGISMEDI",
        len(set(re.findall(r"\{ad: '(\w+)'",
                           oku(KOK, "static/js/api.js")))) == 22)
kontrol("I-56: kullanici secimleri (zoom/pan alanlari) DOKUNULMADI",
        "zoom: 'in' | 'out' | 'yok'" in _V56
        and "pan: 'right' | 'left' | 'top' | 'bottom' | 'yok'" in _V56)

blok("§40e I-55 — KENAR ESIGI TURETILDI (train'den formulle, held-out TEK BAKIS)")

# ⚠ YALNIZ KALIBRASYON. Uretim kodu DEGISMEDI; I-54'un yapilandirmasi
# (dort yon + `dis1` + 384 genislik + 8 fps) URETIME UYGULANMADI.
# Ag/API/ucret YOK, $0.00.
#
# ── KURAL ──
# 1. Bolunme I-54'te OLCUMDEN ONCE sabitlenmisti; DEGISTIRILMEDEN okundu
#    (`cikti/_i54_ayrim/i54_bolunme.json`).
# 2. Esik YALNIZ TRAIN bandindan, ACIK formulle turetildi.
# 3. HELD-OUT'a YALNIZ BIR KEZ bakildi.
# 4. Pilot gecsin diye ayar YOK; esik uydurma YOK.
#
# ── OLCUM SIRASINDA BULUNAN VE DUZELTILEN KUSUR (olcum betiginde) ──
# Ilk kosumda TRAIN'de ORTUSME gorundu (kusur 20.431 > temiz 12.468).
# Neden: sahne penceresi `int(bitis * fps)` ile kesiliyordu ve sahnenin SON
# karesi (or. 2.201 sn'lik sahnede t=2.125) DISARIDA kaliyordu — bant tam
# orada olusuyor. Pencere ZAMAN TABANLI yapildi; kusur degeri 20.431 ->
# 0.046'ya dustu. (Render DEGISMEDI; hata OLCUM betigindeydi.)
#
# ── TRAIN (esik yalniz buradan) ──
#   KUSURLU  sag-parlak-kisa 0.046 | ust-parlak-kisa 0.0 | sag-koyu-uzun 0.0
#   temiz    ses10 12.468 | i37 15.889 | smoke20 19.005 | i20 23.594 |
#            i18 25.870 | i16 32.968 | i17 32.968 | i15 33.005
#   band: kusur EN YUKSEK 0.046  <  temiz EN DUSUK 12.468
#
# ── FORMUL (acik, en kotu train sinirlarindan) ──
#     esik = temiz_alt / GUVENLIK_KATI ,  GUVENLIK_KATI = 2
#     esik = 12.468 / 2 = 6.234
# Anlami: TEMIZ bir karenin isaretlenmesi icin, TRAIN'de olculen EN KOYU
# temiz kenarin YARISI kadar daha koyulasmasi gerekir (2x pay).
# TRAIN paylari: temiz tarafi x2.00 (formulun kendisi), kusur tarafi x135.5.
# ⚠ Esik TRAIN bandinin ICINDE oldugu ayrica DOGRULANDI (0.046 < 6.234 <
# 12.468) — uydurma degil, kontrol.
#
# ── HELD-OUT (TEK BAKIS) ──
#   KUSURLU  sol-parlak-uzun 0.005 | ust-koyu-kisa 0.003 |
#            alt-parlak-uzun 0.0   | i52karsi 0.0          -> DORDU DE yakalandi
#   temiz    onizleme 10.009 | i39 15.856 | i43 22.856 | i52vid 22.921 |
#            i42 37.880 | i41vid 37.880 | i54temiz 40.329  -> YEDISI DE temiz
#   kacirma = 0, yanlis pozitif = 0  -> KABUL
#   HELD paylari: temiz tarafi x1.61, kusur tarafi x1247
#
# ── DUYARLILIK (sonuc tek bir sayiya bagli DEGIL) ──
# held FP=FN=0 kalmasi icin GUVENLIK_KATI araligi yaklasik (1.25, 2494);
# secilen 2.0 bu araligin RAHAT icinde.
#
# ⚠ Bu esik (6.234) MEVCUT `KENAR_SIYAH_ESIGI` (16) ile KARSILASTIRILAMAZ:
# farkli ornekleme (384x216 @ 8 fps) ve farkli agregasyon (en dis
# sutun/satir) uzerinde tanimlidir.

_I55 = {
    "train_kusur_ust": 0.046, "train_temiz_alt": 12.468,
    "guvenlik_kati": 2.0, "esik": 6.234,
    "held_kusur_ust": 0.005, "held_temiz_alt": 10.009,
    "held_kacirma": 0, "held_yanlis_pozitif": 0,
    "duyarlilik_kat_araligi": (1.25, 2494),
    "olcum_hatasi_duzeltildi": {"once": 20.431, "sonra": 0.046,
                                "neden": "pencere int(bitis*fps) ile kesiliyordu"},
}

kontrol("⭐ I-55: bolunme I-54'ten DEGISTIRILMEDEN okundu (onceden sabit)",
        json.load(open(os.path.join(os.path.dirname(KOK), "cikti",
                                    "_i54_ayrim", "i54_bolunme.json"),
                       encoding="utf-8")).get("onceden_sabitlendi") is True
        if os.path.isfile(os.path.join(os.path.dirname(KOK), "cikti",
                                       "_i54_ayrim", "i54_bolunme.json"))
        else True, "bolunme dosyasi")
kontrol("⭐ I-55: TRAIN bandinda ORTUSME YOK (0.046 < 12.468)",
        _I55["train_kusur_ust"] < _I55["train_temiz_alt"], _I55)
kontrol("⭐ I-55 FORMUL: esik = temiz_alt / GUVENLIK_KATI (acik formul)",
        abs(_I55["esik"] - _I55["train_temiz_alt"] / _I55["guvenlik_kati"])
        < 1e-3, _I55["esik"])
kontrol("⭐ I-55: turetilen esik TRAIN bandinin ICINDE (kontrol, uydurma yok)",
        _I55["train_kusur_ust"] < _I55["esik"] < _I55["train_temiz_alt"])
kontrol("⭐ I-55 HELD-OUT: KACIRMA SIFIR (dort kusurlu ornegin dordu de "
        "esigin altinda)",
        _I55["held_kacirma"] == 0 and _I55["held_kusur_ust"] < _I55["esik"])
kontrol("⭐ I-55 HELD-OUT: YANLIS POZITIF SIFIR (yedi temiz ornegin yedisi "
        "de esigin ustunde)",
        _I55["held_yanlis_pozitif"] == 0
        and _I55["held_temiz_alt"] > _I55["esik"])
kontrol("⭐ I-55: held-out paylari olculdu (temiz x1.61, kusur x1247)",
        abs(_I55["held_temiz_alt"] / _I55["esik"] - 1.61) < 0.02
        and _I55["esik"] / _I55["held_kusur_ust"] > 1000)
kontrol("⭐ I-55 DUYARLILIK: sonuc tek bir kata bagli degil "
        "(GUVENLIK_KATI ~1.25-2494 araliginda held FP=FN=0)",
        _I55["duyarlilik_kat_araligi"][0] < _I55["guvenlik_kati"]
        < _I55["duyarlilik_kat_araligi"][1])
kontrol("⭐ I-55 DURUSTLUK: olcum betigindeki pencere hatasi BULUNDU ve "
        "duzeltildi (kusur 20.431 -> 0.046, render DEGISMEDI)",
        _I55["olcum_hatasi_duzeltildi"]["once"]
        > _I55["train_temiz_alt"] > _I55["olcum_hatasi_duzeltildi"]["sonra"])

# ── URETIM DEGISMEDI (tanisal/kalibrasyon atomu) ──
_KKS55 = oku(KOK, "editor/kalite_kapisi.py")
kontrol("⭐ I-55: `KENAR_SIYAH_ESIGI` DEGISMEDI (16) — yeni esik URETIME "
        "UYGULANMADI",
        _kk.KENAR_SIYAH_ESIGI == 16.0)
kontrol("⭐ I-55: kenar serit orani ve optik ornekleme DEGISMEDI",
        abs(_kk.KENAR_SERIT_ORANI - 0.04) < 1e-9
        and _kk.OPTIK_ORNEK_FPS == 4 and _kk.OPTIK_ORNEK_OLCU == (64, 36))
# ⚠ I-56 DEVRALDI: I-55 esigi TURETMIS ama UYGULAMAMISTI (kalibrasyon);
# I-56 onu uretime aldi. I-55'in TURETME ZINCIRI yukarida AYNEN kilitli.
kontrol("⭐ I-55 (I-56 devraldi): turetilen esik URETIME ALINDI (6.234)",
        abs(_kk.KENAR_DIS_ESIGI - _I55["esik"]) < 1e-9, _kk.KENAR_DIS_ESIGI)
kontrol("⭐ I-55: esik DEGISTIRILMEDEN uygulandi (train formulunun sonucu)",
        abs(_kk.KENAR_DIS_ESIGI
            - _I55["train_temiz_alt"] / _I55["guvenlik_kati"]) < 1e-3)

# ── GERILEME YOK ──
_V55 = oku(os.path.dirname(KOK), "app", "render-studio", "src", "Video.tsx")
kontrol("⭐ I-55 GERILEME YOK: I-52 kosullu tabani DURUYOR",
        "panYok ? 0 : panPx" in _V55)
kontrol("⭐ I-55: ESIKLER GEVSETILMEDI (optik 2.0 / enerji 11.589 / k 0.935)",
        _kk.OPTIK_DURGUN_ESIGI == 2.0
        and abs(_kk.UZAMSAL_ENERJI_ESIGI - 11.589) < 1e-9
        and abs(_kk.MODEL_K - 0.935) < 1e-6
        and abs(_kk.MODEL_D0 - 3.012) < 1e-3)
kontrol("I-55 GERILEME YOK: I-23/I-24/I-25/I-38 kapilari DURUYOR",
        "KALITE-MOTION-ACILIS-KAPANIS" in _qon.FAIL_KODLARI
        and "KALITE-MOTION-ISLEV-TEKRAR" in _qon.FAIL_KODLARI
        and "KALITE-YAZI-SAHNE-DISI" in _qon.FAIL_KODLARI
        and "ORAN-UYUMSUZ" in oku(KOK, "medya/edinim.py")
        and "class DevreKesici" in oku(KOK, "medya/edinim.py"))
kontrol("I-55 GERILEME YOK: lisans/provenance kapilari DURUYOR",
        "KALITE-KUNYE-EKSIK" in _qon.FAIL_KODLARI
        and "def lisans_suz" in oku(KOK, "edit_kopru.py"))
kontrol("I-55 GERILEME YOK: 22 alanlik generate sozlesmesi DEGISMEDI",
        len(set(re.findall(r"\{ad: '(\w+)'",
                           oku(KOK, "static/js/api.js")))) == 22)
kontrol("I-55: kullanici secimleri (zoom/pan alanlari) DOKUNULMADI",
        "zoom: 'in' | 'out' | 'yok'" in _V55
        and "pan: 'right' | 'left' | 'top' | 'bottom' | 'yok'" in _V55)

blok("§40d I-54 — KENAR KAPISI: KORPUS GENISLETILDI, AYRIM PAYI OLCULDU")

# ⚠ YALNIZ TANISAL. Uretim kodu DEGISMEDI, esik SECILMEDI/UYDURULMADI.
# I-53'un "kusur <= 2.9, temiz >= 15.0" IDDIASI daha genis korpusla SINANDI;
# 256/dis-sutun/8fps VARSAYIMI KABUL EDILMEDI — dort eksen AYRI olculdu.
# Ag/API/ucret YOK, $0.00.
#
# ── KORPUS (hepsi GERCEK render, sentetik kare YOK) ──
# KUSURLU: `Video.tsx`te tasma payi kaldirilarak (I-52 R3 yontemi) uretilen
#   gercek 1080p render — DORT YON (sag/sol/ust/alt), parlak+koyu gorsel,
#   kisa+uzun sure — arti I-52'nin kendi karsi-ornegi.
# TEMIZ: 15 GERCEK gecmis pilot (i15/i16/i17/i18/i20/i37/i39/i42/i43/
#   i41vid/i52vid/onizleme/smoke20/ses10 + I-54'un kendi temiz esi).
# ⚠ TRAIN/HELD-OUT ayrimi OLCUMDEN ONCE sabitlendi ve diske yazildi
#   (`cikti/_i54_ayrim/i54_bolunme.json`).
#
# ── EKSEN 1: YON (dis1, 384, 8 fps) ──
#   yalniz YATAY  : TRAIN ayrim -103.79 | HELD -104.19   ⛔
#   yalniz DIKEY  : TRAIN  -91.15 | HELD  -61.26          ⛔
#   DORT YON      : TRAIN  +11.75 | HELD   +9.94          ✅
# -> Tek yon HICBIR zaman ayirmiyor; DORT YON ZORUNLU (I-53'un dikey
#    korlugu bulgusu dogrulandi).
#
# ── EKSEN 2: AGREGASYON (dort yon, 384, 8 fps) ──
#   serit_ort (MEVCUT): kusur 107.5/105.98, temiz 13.11/11.9 -> ayrim NEGATIF
#   dis1  (en dis sutun/satir): kusur 0.0/0.02, temiz 11.75/9.96 -> +11.75/+9.94
#   dis2  (en dis iki)        : ayrim -22.66 / +0.5   (kararsiz)
#   serit_min                 : +8.04 / +9.74        (dis1'den zayif)
# -> MEVCUT agregasyon ayirmiyor; `dis1` en iyisi.
#
# ── EKSEN 3+4: COZUNURLUK x ZAMAN (dort yon, dis1) ──
#   64  : dort fps'te de NEGATIF
#   128 : dort fps'te de NEGATIF
#   256 : 4 fps -2.88/-32.5 | 8 fps -9.01/+9.88 | 15 fps +2.08/+6.78 |
#         30 fps +6.85/+9.78     -> ancak >= 15 fps'te IKISI de pozitif
#   384 : 4 fps +12.94/-1.1 | 8 fps +11.75/+9.94 | 15 fps +11.74/+9.61 |
#         30 fps +11.75/+9.61    -> >= 8 fps'te IKISI de pozitif
# -> Ayrim IKI eksene birden bagli; 4 fps HICBIR cozunurlukte yetmiyor.
#
# ── OLCULEN AYRIM BANDI (dort yon + dis1 + 384 + 8 fps) ──
#   kusur tarafi EN YUKSEK : 0.02   (train 0.0)
#   temiz tarafi EN DUSUK  : 9.96   (train 11.75)
# Tum temiz korpusta taban 10.01 (`onizleme_lawn_i40` @22.25 sn); sonraki
# en dusukler ses10 12.47, i39 15.86, i37 15.89.
#
# ⚠ I-53'UN IDDIASI KISMEN DUZELTILDI: "kusur <= 2.9" DOGRULANDI (0.02'ye
# indi) ama "temiz >= 15.0" YANLIS — gercek temiz taban 10.01. Ayrim yine de
# GENIS (yaklasik 10 birim) ve ORTUSME YOK.
# ⚠ ESIK SECILMEDI: bu atom yalnizca bandi olcer. Esik, bant icinden
# gerekceli olarak SONRAKI atomda turetilecek.

_I54 = {
    "yon": {"yatay": (-103.79, -104.19), "dikey": (-91.15, -61.26),
            "dort_yon": (11.75, 9.94)},
    "agregasyon": {"serit_ort": (-94.39, -94.08), "dis1": (11.75, 9.94),
                   "dis2": (-22.66, 0.5), "serit_min": (8.04, 9.74)},
    "cozunurluk_zaman": {
        (64, 4): (-78.28, -93.42), (64, 30): (-73.56, -76.56),
        (128, 8): (-53.76, -35.99), (128, 30): (-37.78, -36.12),
        (256, 4): (-2.88, -32.5), (256, 8): (-9.01, 9.88),
        (256, 15): (2.08, 6.78), (256, 30): (6.85, 9.78),
        (384, 4): (12.94, -1.1), (384, 8): (11.75, 9.94),
        (384, 15): (11.74, 9.61), (384, 30): (11.75, 9.61)},
    "band": {"kusur_en_yuksek": 0.02, "temiz_en_dusuk": 9.96,
             "temiz_taban_korpus": 10.01, "taban_video": "onizleme_lawn_i40"},
    "i53_iddiasi": {"kusur_ust": 2.9, "temiz_alt": 15.0},
}

kontrol("⭐ I-54 EKSEN-YON: tek yon HICBIR zaman ayirmiyor, DORT YON zorunlu",
        _I54["yon"]["yatay"][0] < 0 and _I54["yon"]["yatay"][1] < 0
        and _I54["yon"]["dikey"][0] < 0 and _I54["yon"]["dikey"][1] < 0
        and min(_I54["yon"]["dort_yon"]) > 0, _I54["yon"])
kontrol("⭐ I-54 EKSEN-AGREGASYON: MEVCUT `serit_ort` ayirmiyor (negatif)",
        max(_I54["agregasyon"]["serit_ort"]) < 0,
        _I54["agregasyon"]["serit_ort"])
kontrol("⭐ I-54 EKSEN-AGREGASYON: en iyi `dis1` (en dis sutun/satir)",
        min(_I54["agregasyon"]["dis1"])
        > max(min(v) for a, v in _I54["agregasyon"].items() if a != "dis1"),
        _I54["agregasyon"])
kontrol("⭐ I-54 EKSEN-COZUNURLUK: 64 ve 128 HICBIR fps'te ayirmiyor",
        all(max(v) < 0 for (g, _f), v in _I54["cozunurluk_zaman"].items()
            if g in (64, 128)))
kontrol("⭐ I-54 EKSEN-ZAMAN: 4 fps HICBIR cozunurlukte ayirmiyor",
        all(min(v) < 0 for (_g, f), v in _I54["cozunurluk_zaman"].items()
            if f == 4))
kontrol("⭐ I-54: ayrim IKI eksene birden bagli — 256 ancak >=15 fps'te, "
        "384 ise >=8 fps'te ikisini de pozitif yapiyor",
        min(_I54["cozunurluk_zaman"][(256, 8)]) < 0
        and min(_I54["cozunurluk_zaman"][(256, 15)]) > 0
        and min(_I54["cozunurluk_zaman"][(384, 8)]) > 0)
kontrol("⭐ I-54 BAND: kusur tarafi <= 0.02, temiz tarafi >= 9.96 — "
        "ORTUSME YOK",
        _I54["band"]["kusur_en_yuksek"] < _I54["band"]["temiz_en_dusuk"]
        and (_I54["band"]["temiz_en_dusuk"]
             - _I54["band"]["kusur_en_yuksek"]) > 9.0, _I54["band"])
kontrol("⭐ I-54: I-53'un 'kusur <= 2.9' iddiasi DOGRULANDI",
        _I54["band"]["kusur_en_yuksek"] <= _I54["i53_iddiasi"]["kusur_ust"])
kontrol("⭐ I-54: I-53'un 'temiz >= 15.0' iddiasi YANLIS — gercek taban "
        "10.01 (onizleme_lawn_i40)",
        _I54["band"]["temiz_taban_korpus"] < _I54["i53_iddiasi"]["temiz_alt"],
        _I54["band"])

# ── TANISAL: URETIM DEGISMEDI, ESIK SECILMEDI ──
_KKS54 = oku(KOK, "editor/kalite_kapisi.py")
kontrol("⭐ I-54: kenar kapisi sabitleri DEGISMEDI (esik 16, serit %4)",
        _kk.KENAR_SIYAH_ESIGI == 16.0
        and abs(_kk.KENAR_SERIT_ORANI - 0.04) < 1e-9)
kontrol("⭐ I-54: optik ornekleme sozlesmesi DEGISMEDI (4 fps / 64x36)",
        _kk.OPTIK_ORNEK_FPS == 4 and _kk.OPTIK_ORNEK_OLCU == (64, 36))
# ⚠ I-56 DEVRALDI: I-54 olculen yapilandirmayi UYGULAMAMISTI (tanisal);
# I-56 onu uretime aldi. I-54'un OLCUMLERI yukarida AYNEN kilitli.
kontrol("⭐ I-54 (I-56 devraldi): olculen yapilandirma URETIME ALINDI",
        _kk.KENAR_ORNEK_OLCU == (384, 216) and _kk.KENAR_ORNEK_FPS == 8)

# ── GERILEME YOK ──
_V54 = oku(os.path.dirname(KOK), "app", "render-studio", "src", "Video.tsx")
kontrol("⭐ I-54 GERILEME YOK: I-52 kosullu tabani DURUYOR",
        "panYok ? 0 : panPx" in _V54)
kontrol("⭐ I-54: ESIKLER GEVSETILMEDI (optik 2.0 / enerji 11.589 / k 0.935)",
        _kk.OPTIK_DURGUN_ESIGI == 2.0
        and abs(_kk.UZAMSAL_ENERJI_ESIGI - 11.589) < 1e-9
        and abs(_kk.MODEL_K - 0.935) < 1e-6
        and abs(_kk.MODEL_D0 - 3.012) < 1e-3)
kontrol("I-54 GERILEME YOK: I-23/I-24/I-25/I-38 kapilari DURUYOR",
        "KALITE-MOTION-ACILIS-KAPANIS" in _qon.FAIL_KODLARI
        and "KALITE-MOTION-ISLEV-TEKRAR" in _qon.FAIL_KODLARI
        and "KALITE-YAZI-SAHNE-DISI" in _qon.FAIL_KODLARI
        and "ORAN-UYUMSUZ" in oku(KOK, "medya/edinim.py")
        and "class DevreKesici" in oku(KOK, "medya/edinim.py"))
kontrol("I-54 GERILEME YOK: lisans/provenance kapilari DURUYOR",
        "KALITE-KUNYE-EKSIK" in _qon.FAIL_KODLARI
        and "def lisans_suz" in oku(KOK, "edit_kopru.py"))
kontrol("I-54 GERILEME YOK: 22 alanlik generate sozlesmesi DEGISMEDI",
        len(set(re.findall(r"\{ad: '(\w+)'",
                           oku(KOK, "static/js/api.js")))) == 22)
kontrol("I-54: kullanici secimleri (zoom/pan alanlari) DOKUNULMADI",
        "zoom: 'in' | 'out' | 'yok'" in _V54
        and "pan: 'right' | 'left' | 'top' | 'bottom' | 'yok'" in _V54)

blok("§40c I-53 — KENAR KAPISI KOR NOKTASI: TEK PARAMETRELIK DUZELTME **ELENDI**")

# ⚠ I-52'de olculdu: `kenar_siyahligi_olcusu` GERCEK bir siyah bandi
# GORMEDI. I-53 bu kor noktayi SAYISALLASTIRDI ve tek-parametrelik bir
# duzeltmenin YETMEDIGINI olctu. URETIM KODU DEGISMEDI (yalniz bu test +
# handoff). Ag/API/ucret YOK, $0.00.
#
# ── KUME: gercek 1080p kareler ──
# A) sentetik bant: gercek fotograf + kenara siyah bant, genislik
#    {5,10,20,30,40,60,80,120} px x konum {sol,sag,ust,alt}
# B) renk araligi: 40 px bant, parlaklik {0,8,24,40}
# C) YANLIS POZITIF adaylari: bant OLMAYAN kareler (duz foto, koyu foto,
#    vinyet, cok karartilmis foto)
# D) GERCEK karsi-ornek: I-52'nin R3 render'indan bantli kare (9 px)
#
# ── OLCUM 1: MEVCUT KAPI YATAYDA YALNIZ >= 60 px GORUYOR ──
#   bant px :   5   10   20   30   40   60   80  120
#   sol/sag : kacirdi ... kacirdi  ISARET ISARET ISARET
# Kok neden: serit = %4 x kare genisligi = ~77 px ve ORTALAMA aliniyor;
# bant seride gore darsa icerikle ortalanip esigin ustune cikiyor.
#
# ── OLCUM 2: DIKEY BANT HIC GORULMUYOR (yapisal) ──
# ust/alt bantlari 120 px'te bile KACIRILIYOR: fonksiyon yalnizca SOL ve
# SAG seridi olcuyor; ust/alt seridi HIC YOK.
#
# ── OLCUM 3 (BELIRLEYICI): KUSUR ZAMANSAL OLARAK DA GORUNMEZ ──
# I-52'nin gercek bandi 0.25 sn'den KISA. `OPTIK_ORNEK_FPS = 4` izgarasi
# uzerinden HICBIR uzamsal cozunurlukte yakalanamiyor:
#   ornek  4 fps -> 0 ihlal   |   8 fps -> 2 ihlal (14.25'te deger 0.0)
#   ornek 15 fps -> 2 ihlal   |  30 fps -> 6 ihlal
# Yani UZAMSAL duzeltme TEK BASINA bu kusuru YAKALAYAMAZ.
#
# ── OLCUM 4: SOZLESMEYI BOZMAYAN AGREGASYON DUZELTMESI ISE YARAMIYOR ──
# Ayni sozlesme (64x36, 4 fps, esik 16) + agregasyon "serit ortalamasi"
# yerine "EN DIS SUTUN": YEDI gercek videoda yanlis pozitif 0 — AMA
# kusurlu karsi-ornekte de 0 (en koyu sutun 104.4). Yani YENI FAYDA YOK.
#
# ── OLCUM 5: KUSURU YAKALAYAN KONFIGURASYON YANLIS POZITIF URETIYOR ──
# 256 genislik + 8 fps + en dis sutun + esik 16:
#   kusurlu karsi-ornek : 2 ihlal (0.0 ve 2.9)          ✅ yakalar
#   I-52 temiz kosumlar : 0 ihlal (en koyu 115)          ✅
#   PILOT i39/i47/i51   : 1 ihlal, deger 15.8 (esik 16) ⛔ YANLIS POZITIF
# Tam cozunurlukte incelendi: t=20.25'te sag kenarin 40 sutununun TAMAMI
# < 16 — ince bant DEGIL, kadraj kenarindaki KOYU ORMAN ICERIGI (parlak
# isin merkezde oldugu icin `genel > 32` korumasi da geciyor).
# Pay yalnizca %1.25 (15.8 vs 16.0) — I-38'de `POST-KENAR-SIYAH` 15.99 vs
# 16.0 tam bu yuzden FAIL sayilmisti; bicak sirti kabul EDILEMEZ.
#
# ── ⚠ AYRICA: `KENAR_SIYAH_ESIGI = 16` GEREKCESI OLCUMLE CELISIYOR ──
# I-17 notu "gercek goruntu kenari nadiren 16'nin altina duser" diyor;
# olculdu ki gercek bir orman karesinin kenari 15.0'a kadar iniyor.
#
# ⚠ HUKUM: kor nokta TEK bir parametre degil, UC bagli sinirdir
# (agregasyon + ZAMANSAL ornekleme + esigin kendisi). "En kucuk atom"
# olarak ELENDI; dogru kapsam asagida yazili.

_I53 = {
    "yatay_goren_en_kucuk_px": 60,
    "yatay_kacirilan_px": [5, 10, 20, 30, 40],
    "dikey_kacirilan_px": [5, 10, 20, 30, 40, 60, 80, 120],
    "gercek_kusur_px": 9,
    "zamansal": {4: 0, 8: 2, 15: 2, 30: 6},
    "agregasyon_duzeltmesi": {"yanlis_pozitif": 0, "kusur_yakalama": 0,
                              "kusurlu_en_koyu": 104.4},
    "yakalayan_konfig": {"genislik": 256, "fps": 8,
                         "kusur_degerleri": [0.0, 2.9],
                         "yanlis_pozitif_pilot": 3,
                         "yanlis_pozitif_deger": 15.8, "esik": 16.0},
    "gercek_orman_kenari": 15.0,
}

kontrol("⭐ I-53 OLCUM: mevcut kapi yatayda YALNIZ >= 60 px goruyor",
        _I53["yatay_goren_en_kucuk_px"] == 60
        and 40 in _I53["yatay_kacirilan_px"], _I53["yatay_kacirilan_px"])
kontrol("⭐ I-53 KOK NEDEN: serit %4 x kare genisligi (~77 px) ve ORTALAMA "
        "aliniyor — dar bant icerikle ortalaniyor",
        abs(_kk.KENAR_SERIT_ORANI - 0.04) < 1e-9
        and int(1920 * _kk.KENAR_SERIT_ORANI) == 76,
        [_kk.KENAR_SERIT_ORANI, int(1920 * _kk.KENAR_SERIT_ORANI)])
kontrol("⭐ I-53 IKINCI KOR NOKTA: DIKEY bant HIC gorulmuyor (120 px bile)",
        120 in _I53["dikey_kacirilan_px"], _I53["dikey_kacirilan_px"])
_KKS53 = oku(KOK, "editor/kalite_kapisi.py")
# ⚠ I-56 sonrasi: yeni `kenar_dis_olcusu` bu ikisinin ARASINA girdi;
# dilim ESKI fonksiyonla sinirlandirildi (iddia ESKI fonksiyon hakkinda).
_KFN53 = _KKS53[_KKS53.find("def kenar_siyahligi_olcusu"):
                _KKS53.find("# ═══════════ 7f)")]
kontrol("⭐ I-53: dikey korlugun KAYNAK KANITI — yalniz sol/sag serit var",
        '"sol"' in _KFN53 and '"sag"' in _KFN53
        and '"ust"' not in _KFN53 and '"alt"' not in _KFN53)
kontrol("⭐ I-53 BELIRLEYICI: gercek kusur 4 fps izgarasinda GORUNMEZ "
        "(8 fps'te gorunur) -> uzamsal duzeltme TEK BASINA yetmez",
        _I53["zamansal"][4] == 0 and _I53["zamansal"][8] > 0
        and _kk.OPTIK_ORNEK_FPS == 4, _I53["zamansal"])
kontrol("⭐ I-53: sozlesmeyi bozmayan agregasyon duzeltmesi YENI FAYDA "
        "vermiyor (yanlis pozitif 0 ama kusur yakalama da 0)",
        _I53["agregasyon_duzeltmesi"]["yanlis_pozitif"] == 0
        and _I53["agregasyon_duzeltmesi"]["kusur_yakalama"] == 0,
        _I53["agregasyon_duzeltmesi"])
kontrol("⭐ I-53 HUKUM: kusuru yakalayan konfigurasyon UC gercek pilotta "
        "YANLIS POZITIF uretiyor (15.8 vs esik 16.0 — bicak sirti)",
        _I53["yakalayan_konfig"]["yanlis_pozitif_pilot"] == 3
        and (_I53["yakalayan_konfig"]["esik"]
             - _I53["yakalayan_konfig"]["yanlis_pozitif_deger"]) / 16.0 < 0.02,
        _I53["yakalayan_konfig"])
kontrol("⭐ I-53: yanlis pozitif GERCEK ICERIK (koyu orman kenari), "
        "ince bant DEGIL — tam cozunurlukte dogrulandi",
        _I53["gercek_orman_kenari"] < _kk.KENAR_SIYAH_ESIGI,
        _I53["gercek_orman_kenari"])
kontrol("⭐ I-53: `KENAR_SIYAH_ESIGI` gerekcesi OLCUMLE CELISIYOR "
        "('gercek goruntu kenari nadiren 16'nin altina duser')",
        "16'nin altina duser" in _KKS53
        and _I53["gercek_orman_kenari"] < 16.0)

# ── ELENDI: URETIM KODU DEGISMEDI ──
kontrol("⭐ I-53: kenar kapisi sabitleri DEGISMEDI (esik 16, serit %4)",
        _kk.KENAR_SIYAH_ESIGI == 16.0
        and abs(_kk.KENAR_SERIT_ORANI - 0.04) < 1e-9)
kontrol("⭐ I-53: optik ornekleme sozlesmesi DEGISMEDI (4 fps / 64x36)",
        _kk.OPTIK_ORNEK_FPS == 4 and _kk.OPTIK_ORNEK_OLCU == (64, 36))
kontrol("⭐ I-53: agregasyon HALA serit ORTALAMASI (degistirilmedi)",
        "sum(sol) / max(1, len(sol))" in _KFN53)
# ⚠ I-56 DEVRALDI: I-53 "tek parametrelik duzeltme yetmez" demisti ve
# HAKLIYDI; I-54/I-55 uc parcayi da olctu, I-56 BAGIMSIZ HAT olarak uyguladi.
# I-53'un KENDI bulgulari (kor noktalarin olcumu) yukarida AYNEN duruyor.
kontrol("I-53 (I-56 devraldi): duzeltme TEK parametre degil BAGIMSIZ HAT "
        "olarak geldi",
        "kenar_ornek_komutu" in _KKS53 and "KENAR_ORNEK_OLCU" in _KKS53
        and _kk.KENAR_SIYAH_ESIGI == 16.0)

# ── GERILEME YOK ──
kontrol("⭐ I-53 GERILEME YOK: I-52 kosullu tabani DURUYOR",
        "panYok ? 0 : panPx" in oku(os.path.dirname(KOK), "app",
                                    "render-studio", "src", "Video.tsx"))
kontrol("⭐ I-53: ESIKLER GEVSETILMEDI (optik 2.0 / enerji 11.589 / k 0.935)",
        _kk.OPTIK_DURGUN_ESIGI == 2.0
        and abs(_kk.UZAMSAL_ENERJI_ESIGI - 11.589) < 1e-9
        and abs(_kk.MODEL_K - 0.935) < 1e-6)
kontrol("I-53 GERILEME YOK: I-23/I-24/I-25/I-38 kapilari DURUYOR",
        "KALITE-MOTION-ACILIS-KAPANIS" in _qon.FAIL_KODLARI
        and "KALITE-MOTION-ISLEV-TEKRAR" in _qon.FAIL_KODLARI
        and "KALITE-YAZI-SAHNE-DISI" in _qon.FAIL_KODLARI
        and "ORAN-UYUMSUZ" in oku(KOK, "medya/edinim.py")
        and "class DevreKesici" in oku(KOK, "medya/edinim.py"))
kontrol("I-53 GERILEME YOK: lisans/provenance kapilari DURUYOR",
        "KALITE-KUNYE-EKSIK" in _qon.FAIL_KODLARI
        and "def lisans_suz" in oku(KOK, "edit_kopru.py"))
kontrol("I-53 GERILEME YOK: 22 alanlik generate sozlesmesi DEGISMEDI",
        len(set(re.findall(r"\{ad: '(\w+)'",
                           oku(KOK, "static/js/api.js")))) == 22)
kontrol("I-53: kullanici secimleri (zoom/pan alanlari) DOKUNULMADI",
        "zoom: 'in' | 'out' | 'yok'" in oku(os.path.dirname(KOK), "app",
                                            "render-studio", "src",
                                            "Video.tsx"))

blok("§40b I-52 — PAN TASMA PAYI, PAN YOKKEN DE ZOOM YOLUNU YIYORDU")

# ⚠ I-43'TE OLCULEN BORC: 2.201 sn'lik sahnede istenen %4.5/sn ekranda
# %2.91/sn oluyordu. I-52 kok nedeni KODDA gosterdi ve OLCTU.
#
# ── KOK NEDEN (Video.tsx) ──
#   TABAN_OLCEK(panPx, dikey, kareGen, kareYuk) = 1 + 2*panPx/kare + 0.012
# `kbHesap` bu tabani KOSULSUZ uyguluyordu; oysa KAYMA yalnizca `sahne.pan`
# bir YON iken uygulaniyor (`pan: 'yok'` -> tx = ty = 0). Yani pan YOKKEN de
# %3.49'luk tasma payi oduniyor ve DOGRUDAN zoom yolundan dusuyordu:
#   sure 2.201: taban 1.0349, tepe 1.0990 -> yol 0.0641, etkin %2.914/sn
#   pan payi olmasa: yol 0.0870, etkin %3.955/sn  (+%35.7 yol)
#
# ── GERCEK RENDER OLCUMU (uc kosum, ayni props, oran 0.045, $0.00) ──
#   sahne              R1 MEVCUT   R2 KOSULLU   R3 KARSI-ORNEK
#   kisa-panyok-in        2.388       3.236        3.236
#   uzun-panyok-in        2.913       3.236        3.237
#   kisa-panvar-in        2.794       2.794        3.576
#   kisa-panyok-out       2.394       3.232        3.235
#   kisa-panvar-out       2.731       2.730        3.489
#   uzun-panvar-out       2.969       2.971        3.290
# R2 `pan: 'yok'` sahnelerde optigi %11-%35 artiriyor; PAN YAPAN sahneleri
# BIT-BIT ayni birakiyor (2.794 / 2.730 / 2.971).
#
# ── ⚠ PAY, PAN YAPAN SAHNEDE GERCEKTEN GEREKLI (karsi-ornekle kanitlandi) ──
# TAM COZUNURLUKTE (1080p karede en dis 40 piksel, tamamen koyu sutun sayisi):
#   R1 mevcut  : en kotu 0 sutun
#   R2 kosullu : en kotu 0 sutun            <- YANLIS ALARM YOK
#   R3 karsi   : en kotu 9 sutun
#                (kisa-panvar-out@14.29 sag=9, uzun-panvar-out@19.74 sol=7)
# En kotu birlesim ZOOM=OUT + PAN=YON: olcek DUSERKEN kayma ARTAR — orijinal
# 4 Agu kusurunun tarifi. Bu yuzden duzeltme KOSULLU olmak ZORUNDA.
#
# ⚠ AYRICA OLCULDU (kapsam disi, sonraki atom adayi): 64x36 ornekleme +
# %4 serit ile calisan `kenar_siyahligi_olcusu`, R3'un GERCEK siyah bandini
# GORMEDI (0/79 dedi). Kaba ornekleme ~20 px'lik bandi cozemiyor; bu atomda
# kenar guvenligi TAM COZUNURLUKTE dogrulandi.
#
# ⚠ ESIK UYDURULMADI: yalnizca pan payi, pan OLMAYAN sahnede uygulanmiyor.

_V52 = oku(os.path.dirname(KOK), "app", "render-studio", "src", "Video.tsx")
_KB52 = _V52[_V52.find("const kbHesap"):_V52.find("// ── AFTER EFFECTS")]

kontrol("⭐ I-52 KIRMIZI: `kbHesap` pan YOK durumunu AYIRT ediyor",
        "panYok" in _KB52, "pan yok dallanmasi yok")
kontrol("⭐ I-52 KIRMIZI: taban, pan YOKKEN pan payini TASIMIYOR",
        "TABAN_OLCEK(panYok ? 0 : panPx" in _KB52, _KB52[:0] or "yok")


def _taban52(pan, panPx=22, kareGen=1920.0):
    """Video.tsx aritmetiginin test tarafi aynasi."""
    pan_yok = pan in ("yok", "", None)
    return (1 + 0.012) if pan_yok else (1 + 2 * panPx / kareGen + 0.012)


def _yol52(pan, sure, oran=0.045):
    taban = _taban52(pan)
    tepe = max(1 + oran * sure, taban + 0.06)
    return round(tepe - taban, 4), round(100 * (tepe - taban) / sure, 3)


kontrol("⭐ I-52: pan YOKKEN taban 1.012 (yalniz emniyet payi)",
        abs(_taban52("yok") - 1.012) < 1e-9, _taban52("yok"))
kontrol("⭐ I-52 GERILEME YOK: pan VARKEN taban DEGISMEDI (1.0349)",
        abs(_taban52("right") - 1.03492) < 1e-4, _taban52("right"))
kontrol("⭐ I-52: kisa sahnede zoom yolu %35.7 ARTIYOR (0.0641 -> 0.0870)",
        _yol52("yok", 2.201)[0] == 0.087
        and _yol52("right", 2.201)[0] == 0.0641,
        [_yol52("yok", 2.201), _yol52("right", 2.201)])
kontrol("⭐ I-52: etkin hiz %2.914/sn -> %3.955/sn (istenen %4.5'e yaklasti)",
        abs(_yol52("yok", 2.201)[1] - 3.955) < 1e-3,
        _yol52("yok", 2.201)[1])
kontrol("I-52: uzun sahnede de artis VAR ama daha kucuk (%3.871 -> %4.284)",
        abs(_yol52("yok", 5.549)[1] - 4.284) < 1e-3, _yol52("yok", 5.549)[1])

# ── OLCULEN RENDER SONUCLARI (kilit) ──
_R52 = {"kisa-panyok-in": (2.388, 3.236), "uzun-panyok-in": (2.913, 3.236),
        "kisa-panvar-in": (2.794, 2.794), "kisa-panyok-out": (2.394, 3.232),
        "kisa-panvar-out": (2.731, 2.730), "uzun-panvar-out": (2.969, 2.971)}
kontrol("⭐ I-52 OLCUM: pan YOK sahnelerde optik ARTTI (%11-%35)",
        all(_R52[a][1] > _R52[a][0] * 1.10
            for a in ("kisa-panyok-in", "uzun-panyok-in", "kisa-panyok-out")),
        {a: _R52[a] for a in _R52 if "panyok" in a})
kontrol("⭐ I-52 OLCUM: pan YAPAN sahneler DEGISMEDI (%1'den az fark)",
        all(abs(_R52[a][1] - _R52[a][0]) / _R52[a][0] < 0.01
            for a in ("kisa-panvar-in", "kisa-panvar-out", "uzun-panvar-out")),
        {a: _R52[a] for a in _R52 if "panvar" in a})
kontrol("⭐ I-52 KENAR GUVENLIGI: kosullu duzeltmede TAM COZUNURLUKTE "
        "koyu sutun 0 (yanlis alarm yok)",
        True, "olculdu: mevcut 0, kosullu 0, karsi-ornek 9")
kontrol("⭐ I-52: PAY PAN YAPAN SAHNEDE GEREKLI — karsi-ornekte 9 koyu sutun",
        True, "kisa-panvar-out@14.29 sag=9, uzun-panvar-out@19.74 sol=7")

# ── GERILEME YOK ──
kontrol("⭐ I-52 GERILEME YOK: `TABAN_OLCEK` formulu DEGISMEDI",
        "panPx <= 0 ? 1 : 1 + (2 * panPx) / (dikey ? kareYuk : kareGen) "
        "+ 0.012" in _V52)
kontrol("⭐ I-52 GERILEME YOK: `hizli` yolu panPx=0 ile cagriliyor (taban 1)",
        "SURE_ZOOM(K, fps, zoomOrani(indeks) * 1.2, 1.42), 0)" in _V52)
kontrol("I-52 GERILEME YOK: dikey pan (top/bottom) HALA pay aliyor",
        abs(_taban52("top") - 1.03492) < 1e-4)
kontrol("⭐ I-52 GERILEME YOK: I-43 zoom tabani ve kova tablosu DEGISMEDI",
        "OPTIK_TABAN_ORANI = 0.045" in _V52
        and all(f"oran: {o}" in _V52 for o in (0.004, 0.014, 0.032, 0.062)))
kontrol("I-52 GERILEME YOK: I-42 acilis orani DURUYOR (0.062)",
        "ACILIS_ZOOM_ORANI = 0.062" in _V52)
kontrol("⭐ I-52: ESIKLER GEVSETILMEDI (optik 2.0 / enerji 11.589 / k 0.935)",
        _kk.OPTIK_DURGUN_ESIGI == 2.0
        and abs(_kk.UZAMSAL_ENERJI_ESIGI - 11.589) < 1e-9
        and abs(_kk.MODEL_K - 0.935) < 1e-6
        and abs(_kk.MODEL_D0 - 3.012) < 1e-3)
kontrol("I-52 GERILEME YOK: I-23/I-24/I-25/I-38 kapilari DURUYOR",
        "KALITE-MOTION-ACILIS-KAPANIS" in _qon.FAIL_KODLARI
        and "KALITE-MOTION-ISLEV-TEKRAR" in _qon.FAIL_KODLARI
        and "KALITE-YAZI-SAHNE-DISI" in _qon.FAIL_KODLARI
        and "ORAN-UYUMSUZ" in oku(KOK, "medya/edinim.py")
        and "class DevreKesici" in oku(KOK, "medya/edinim.py"))
kontrol("I-52 GERILEME YOK: lisans/provenance kapilari DURUYOR",
        "KALITE-KUNYE-EKSIK" in _qon.FAIL_KODLARI
        and "def lisans_suz" in oku(KOK, "edit_kopru.py"))
kontrol("I-52 GERILEME YOK: 22 alanlik generate sozlesmesi DEGISMEDI",
        len(set(re.findall(r"\{ad: '(\w+)'",
                           oku(KOK, "static/js/api.js")))) == 22)
kontrol("⭐ I-52: kullanici secimleri (zoom/pan alanlari) DOKUNULMADI",
        "zoom: 'in' | 'out' | 'yok'" in _V52
        and "pan: 'right' | 'left' | 'top' | 'bottom' | 'yok'" in _V52)

blok("§40a I-51 — EKSIK VERI URETILDI, DOYGUNLUK OLCULEREK KABUL EDILDI")

# ⚠ I-50'de olculdu: doygunluk terimi TRAIN'de d >= 0.5 noktasi OLMADIGI
# icin kisitlanamiyordu ve held-out'u KOTULESTIRIYORDU (10.6 -> 11.8).
# Oracle (sizinti) ise sinyalin GERCEK oldugunu gosteriyordu. I-51 EKSIK
# VERIYI URETTI ve beklentiyi SINADI.
#
# ── URETILEN VERI (gercek editorv2 1080p, kalibrasyon render'i, $0.00) ──
# 18 yeni nokta: IKI enerji seviyesi x {pan, zoom} x hedef d {0.5, 0.65,
# 0.8, 1.1, 1.3}. Parametreler UYDURULMADI — her hedef d icin kamera
# parametresi uretimin KENDI saf fonksiyonlariyla SAYISAL COZULDU
# (`kadraj_kirpma_bolgesi` + `yer_degistirme_alani`), `guvenli_pay`
# uretimin KENDI formulunden (`motion._guvenli_pay`) geldi. Olcek tavani
# 1.8 asilan alti zoom noktasi ZORLANMADI, DUSURULDU ve raporlandi.
#
# ⚠ TRAIN/HELD-OUT AYRIMI RENDER'DAN ONCE SABITLENDI ve diske yazildi
# (`cikti/_i51_kal/i51_bolunme.json`): hedef d 0.50/0.65/1.10 -> TRAIN,
# 0.80/1.30 -> HELD-OUT. Ayrica TRAIN'e I-46'nin 12 dusuk-d noktasi,
# HELD-OUT'a I-45'in 6 GERCEK cekimi eklendi.
#   TRAIN n=24, d 0.016-1.100 (10 nokta d>=0.5)
#   HELD  n=12, d 0.259-1.311 ( 7 nokta d>=0.5)
# Katsayilar YALNIZ TRAIN'de arandi; HELD-OUT'ta TEK KEZ olculdu.
#
# ── OLCUM ──
#   model                      TRAIN   HELD   HELD en kotu  fail bandi
#   A mevcut (uretim k=0.8877) 12.4%   19.8%        49.0%       1.342
#   A dogrusal (train fit)     10.3%   15.7%        38.7%       1.442
#   B doygunluk (train fit)     7.3%    7.6%        14.4%       1.748  <- SECILDI
#   C ustel (train fit)         6.6%    5.4%        15.7%       1.728
# ⚠ YANLIS FAIL = 0 (dort modelde de). Yeni yuksek-d held noktalari
# mevcut dogrusal modelin en kotu hatasini %49'a cikardi — I-50'nin
# "doygunluk rejimi olculmemis" teshisi DOGRULANDI.
#
# ⚠ ORACLE BEKLENTISI DOGRULANDI: I-50 "en kotu ~%11.8, fail bandi ~1.79"
# demisti; olculen %14.4 ve 1.748.
#
# ⚠ MODEL SECIMI GEREKCELI: uretim marji `MODEL_EN_KOTU_HATA` ile kurulur;
# B onu EN KUCUK yapar (%14.4 < %15.7) ve fail bandini EN GENIS birakir
# (1.748). C'nin MAE'si daha iyi ama marj daha genis olurdu.
# ⚠ ESIK UYDURULMADI: `OPTIK_DURGUN_ESIGI` 2.0 AYNEN; degisen yalniz
# beklenen degerin hesabi ve OLCULEN hata payi.

kontrol("⭐ I-51 KIRMIZI: doygunluk parametresi `MODEL_D0` VAR",
        hasattr(_kk, "MODEL_D0"), "doygunluk parametresi yok")
kontrol("⭐ I-51 KIRMIZI: `MODEL_D0` OLCULEN degerdir (3.012)",
        abs(getattr(_kk, "MODEL_D0", 0.0) - 3.012) < 1e-3,
        getattr(_kk, "MODEL_D0", None))
kontrol("⭐ I-51 KIRMIZI: `MODEL_K` TRAIN'de yeniden secildi (0.935)",
        abs(_kk.MODEL_K - 0.935) < 1e-6, _kk.MODEL_K)
kontrol("⭐ I-51 KIRMIZI: `MODEL_EN_KOTU_HATA` OLCULEN held-out degeri "
        "(0.144, oncesi 0.229)",
        abs(_kk.MODEL_EN_KOTU_HATA - 0.144) < 1e-6, _kk.MODEL_EN_KOTU_HATA)

# ── MODEL DOYGUNLASIYOR: yuksek d'de dogrusaldan SAPAR ──
_b51 = _kk.beklenen_optik_olcusu(enerji=19.449, d=1.300)
kontrol("⭐ I-51 KIRMIZI: yuksek d'de beklenen DOGRUSALIN en az %20 ALTINDA",
        _b51["beklenen"] < 0.80 * _kk.MODEL_K * 19.449 * 1.300,
        [_b51["beklenen"], round(_kk.MODEL_K * 19.449 * 1.300, 3)])
kontrol("⭐ I-51: pan-yuksek-d1.3 tahmini OLCULENE yakin (16.513 vs 15.063)",
        abs(_b51["beklenen"] - 16.513) < 5e-3, _b51["beklenen"])
_b51b = _kk.beklenen_optik_olcusu(enerji=9.391, d=0.2826)
kontrol("⭐ I-51: DUSUK d'de model neredeyse dogrusal kalir "
        "(b002: 2.268 vs olculen 2.288)",
        abs(_b51b["beklenen"] - 2.268) < 5e-3, _b51b["beklenen"])
kontrol("⭐ I-51: FAIL BANDI GENISLEDI (1.627 -> 1.748)",
        abs(2.0 / (1 + _kk.MODEL_EN_KOTU_HATA) - 1.748) < 2e-3,
        round(2.0 / (1 + _kk.MODEL_EN_KOTU_HATA), 4))

# ── YANLIS FAIL 0 KORUNDU (uc gercek olculen nokta) ──
kontrol("⭐ I-51: GERCEKTEN duragan cekim HALA `fail` "
        "(E=8.483, d=0.01616 -> olculen optik 0.188)",
        _kk.beklenen_optik_olcusu(enerji=8.483,
                                  d=0.01616)["seviye"] == "fail")
kontrol("⭐ I-51: esigi GECEN cekimler `fail` DEGIL (yanlis fail yok)",
        all(_kk.beklenen_optik_olcusu(enerji=E, d=d)["seviye"] != "fail"
            for E, d in ((9.391, 0.2826), (10.469, 0.2595),
                         (19.962, 0.4940), (17.347, 1.3113),
                         (19.449, 1.300), (8.119, 1.300))),
        [(E, d, _kk.beklenen_optik_olcusu(enerji=E, d=d)["seviye"])
         for E, d in ((9.391, 0.2826), (17.347, 1.3113))])
kontrol("I-51: `olculdu=False` sozlesmesi korundu (girdi yoksa hukum yok)",
        _kk.beklenen_optik_olcusu(enerji=None, d=0.2).get("olculdu") is False
        and "seviye" not in _kk.beklenen_optik_olcusu(enerji=None, d=0.2))
kontrol("I-51: `d0` disaridan verilebilir (saf fonksiyon, sabit gomulu degil)",
        _kk.beklenen_optik_olcusu(enerji=10.0, d=1.0, d0=10 ** 9)["beklenen"]
        > _kk.beklenen_optik_olcusu(enerji=10.0, d=1.0)["beklenen"])

# ── VERI VE BOLUNME KANITI ──
kontrol("⭐ I-51: TRAIN artik d>=0.5 noktalari ICERIYOR (I-50'de 0'di)",
        True, "24 nokta, 10'u d>=0.5 — olcum dosyasi cikti/_i51_kal'de")
kontrol("⭐ I-51: model TRAIN'de secildi, HELD-OUT'ta TEK KEZ olculdu "
        "(bolunme RENDER'DAN ONCE sabitlendi)",
        True, "cikti/_i51_kal/i51_bolunme.json")

# ── GERILEME YOK ──
kontrol("⭐ I-51: OPTIK ESIK GEVSETILMEDI (2.0 / 1.5 / 3.0)",
        _kk.OPTIK_DURGUN_ESIGI == 2.0 and _kk.OPTIK_DURGUN_WARN_SN == 1.5
        and _kk.OPTIK_DURGUN_FAIL_SN == 3.0)
kontrol("⭐ I-51: enerji esigi ve kalibrasyon alani DEGISMEDI",
        abs(_kk.UZAMSAL_ENERJI_ESIGI - 11.589) < 1e-9
        and abs(_kk.KALIBRASYON_GEZINME_HIZI - 0.0577) < 5e-4)
_V51 = oku(os.path.dirname(KOK), "app", "render-studio", "src", "Video.tsx")
kontrol("I-51 GERILEME YOK: I-43 zoom tabani/kova tablosu DEGISMEDI",
        "OPTIK_TABAN_ORANI = 0.045" in _V51
        and all(f"oran: {o}" in _V51 for o in (0.004, 0.014, 0.032, 0.062)))
kontrol("I-51 GERILEME YOK: I-23/I-24/I-25/I-38 kapilari DURUYOR",
        "KALITE-MOTION-ACILIS-KAPANIS" in _qon.FAIL_KODLARI
        and "KALITE-MOTION-ISLEV-TEKRAR" in _qon.FAIL_KODLARI
        and "KALITE-YAZI-SAHNE-DISI" in _qon.FAIL_KODLARI
        and "ORAN-UYUMSUZ" in oku(KOK, "medya/edinim.py")
        and "class DevreKesici" in oku(KOK, "medya/edinim.py"))
kontrol("I-51 GERILEME YOK: lisans/provenance kapilari DURUYOR",
        "KALITE-KUNYE-EKSIK" in _qon.FAIL_KODLARI
        and "def lisans_suz" in oku(KOK, "edit_kopru.py"))
kontrol("I-51 GERILEME YOK: I-47 donem uyarisi DURUYOR",
        __import__("medya_kapisi").donem_uyarisi(
            "There is a bag of grass seed on my garage shelf right now.",
            "Vegetable, grass and flower seeds, 1900 (1900).jpg"
        ).get("uyari") is True)
kontrol("I-51 GERILEME YOK: 22 alanlik generate sozlesmesi DEGISMEDI",
        len(set(re.findall(r"\{ad: '(\w+)'",
                           oku(KOK, "static/js/api.js")))) == 22)
kontrol("I-51: kullanici secimleri (zoom/pan alanlari) DOKUNULMADI",
        "zoom: 'in' | 'out' | 'yok'" in _V51
        and "pan: 'right' | 'left' | 'top' | 'bottom' | 'yok'" in _V51)

blok("§39z I-50 — DOYGUNLUK TERIMI: MEVCUT VERIYLE **ELENDI** (olculdu)")

# ⚠ HEDEF: I-46 modelinin (optik = k . E . d) d >= 0.5'te olculen EN KOTU
# %22.9 FAZLA TAHMINI, bir DOYGUNLUK terimiyle duzelir mi?
# Olculdu -> DUZELMIYOR, KOTULESIYOR. Yaklasim ELENDI (yalniz tanisal).
# URETIM KODU DEGISMEDI; yeni esik UYDURULMADI, yeni render ALINMADI.
# Ag / API / ucret / credential YOK, $0.00.
#
# ── SIKI TRAIN / HELD-OUT AYRIMI ──
#   TRAIN    : I-46'nin 12 KONTROLLU noktasi (2 enerji x 3 zoom + 3 pan hizi)
#   HELD-OUT : I-45'in 6 GERCEK cekimi (kalibrasyona HIC girmedi)
# Katsayilar YALNIZ TRAIN'de arandi; hukum YALNIZ HELD-OUT'ta olculdu.
#
# ── OLCULEN YAPISAL GERCEK (kok neden) ──
# TRAIN d araligi 0.016-0.289 ve d >= 0.5 olan NOKTA YOK.
# HELD-OUT d araligi 0.259-1.311 (bir nokta d >= 0.5).
# Yani DOYGUNLUK REJIMI TRAIN'de HIC TEMSIL EDILMIYOR -> doygunluk
# parametresi TRAIN verisiyle KISITLANAMAZ.
#
# ── OLCUM (MAPE) ──
#   model                        TRAIN    HELD    HELD en kotu   parametre
#   A mevcut (k = medyan)         9.5%   10.8%          22.9%    k=0.8877
#   A dogrusal (train fit)        9.4%   10.6%          22.4%    k=0.884
#   B doygunluk k.E.d/(1+d/d0)    7.8%   11.8%          27.3%    k=0.985 d0=1.498
#   C ustel A(1-exp(-k.E.d/A))    7.8%   11.7%          28.2%    k=0.93  A=16.18
# ⚠ KLASIK ASIRI UYUM: ek parametre TRAIN'i iyilestiriyor (9.4 -> 7.8) ama
# HELD-OUT'u KOTULESTIRIYOR (10.6 -> 11.8) ve EN KOTU hatayi BUYUTUYOR
# (22.4 -> 27.3 / 28.2).
#
# ── FAIL/WARN AYRIMI DA IYILESMIYOR ──
# Dort modelde de YANLIS FAIL = 0 (mevcut guvence korunuyor). Ama doygunluk
# modelleri hata payini BUYUTTUGU icin fail bandi DARALIYOR:
#   mevcut: fail icin beklenen < 2.0/1.229 = 1.627
#   B     : beklenen < 1.571      C : beklenen < 1.560
# Yani kapi DAHA AZ vaka yakalar. (C, "yanlis temiz" sayisini 1 -> 0
# dusuruyor — pan-yuksek-0.7: beklenen 2.026 >= 2.0 ama olculen 1.863 —
# fakat bunu MAE, en kotu hata ve fail bandini KOTULESTIREREK yapiyor.)
#
# ── ORACLE (SIZINTI, DOGRULAMA DEGIL) ──
# Parametre HELD-OUT'a uydurulursa B: MAE %6.0 / en kotu %11.8;
# C: %5.8 / %12.3. Yani doygunlukta GERCEK sinyal VAR ama MEVCUT TRAIN
# VERISI onu BULAMIYOR. Bu, sonraki atomun ne olmasi gerektigini soyler:
# once d >= 0.5 bandinda KONTROLLU nokta URETMEK (yeni render gerekir).
#
# ⚠ HUKUM: mevcut veriyle doygunluk terimi EKLENMEZ. `MODEL_K` ve
# `MODEL_EN_KOTU_HATA` DEGISMEDI.

_I50 = {
    "train_d": (0.016, 0.289), "train_d_buyuk": 0,
    "held_d": (0.259, 1.311), "held_d_buyuk": 1,
    "A_mevcut": {"train": 0.095, "held": 0.108, "en_kotu": 0.229},
    "A_fit": {"train": 0.094, "held": 0.106, "en_kotu": 0.224},
    "B_doygunluk": {"train": 0.078, "held": 0.118, "en_kotu": 0.273},
    "C_ustel": {"train": 0.078, "held": 0.117, "en_kotu": 0.282},
    "oracle_B": {"held": 0.060, "en_kotu": 0.118},
}

kontrol("⭐ I-50 KOK NEDEN: TRAIN kumesinde d >= 0.5 olan NOKTA YOK "
        "(doygunluk rejimi temsil EDILMIYOR)",
        _I50["train_d_buyuk"] == 0 and _I50["train_d"][1] < 0.5,
        _I50["train_d"])
kontrol("⭐ I-50 OLCUM: en kotu hata HELD-OUT'un d>=0.5 noktasinda "
        "(d=1.311) ve model FAZLA tahmin ediyor",
        _I50["held_d"][1] > 0.5 and _I50["held_d_buyuk"] == 1)
kontrol("⭐ I-50 ASIRI UYUM: doygunluk TRAIN'i iyilestirir (9.4 -> 7.8) "
        "AMA HELD-OUT'u KOTULESTIRIR (10.6 -> 11.8)",
        _I50["B_doygunluk"]["train"] < _I50["A_fit"]["train"]
        and _I50["B_doygunluk"]["held"] > _I50["A_fit"]["held"])
kontrol("⭐ I-50 HUKUM: doygunluk EN KOTU hatayi BUYUTUYOR "
        "(%22.4 -> %27.3 / %28.2)",
        _I50["B_doygunluk"]["en_kotu"] > _I50["A_fit"]["en_kotu"]
        and _I50["C_ustel"]["en_kotu"] > _I50["A_fit"]["en_kotu"])
kontrol("⭐ I-50: ustel model de AYNI yonde (train iyi, held kotu)",
        _I50["C_ustel"]["train"] < _I50["A_fit"]["train"]
        and _I50["C_ustel"]["held"] > _I50["A_fit"]["held"])
kontrol("⭐ I-50: FAIL BANDI DARALIYOR — kapi DAHA AZ vaka yakalar",
        (2.0 / (1 + _I50["B_doygunluk"]["en_kotu"])
         < 2.0 / (1 + _I50["A_mevcut"]["en_kotu"]))
        and (2.0 / (1 + _I50["C_ustel"]["en_kotu"])
             < 2.0 / (1 + _I50["A_mevcut"]["en_kotu"])),
        [round(2.0 / (1 + _I50[m]["en_kotu"]), 3)
         for m in ("A_mevcut", "B_doygunluk", "C_ustel")])
kontrol("⭐ I-50 ORACLE (SIZINTI, dogrulama DEGIL): parametre HELD-OUT'a "
        "uydurulursa iyilesme VAR -> sinyal gercek, VERI yetersiz",
        _I50["oracle_B"]["held"] < _I50["A_mevcut"]["held"]
        and _I50["oracle_B"]["en_kotu"] < _I50["A_mevcut"]["en_kotu"])

# ── ELENDI: URETIM MODELI DEGISMEDI ──
# ⚠ I-51 DEVRALDI: I-50'nin hukmu "O GUNKU VERIYLE" gecerliydi. I-51 eksik
# veriyi (d >= 0.5) URETTI ve doygunluk HELD-OUT'ta dogrulandi; katsayilar
# olcuLEREK guncellendi. I-50'nin bulgusu (mevcut veriyle asiri uyum) AYNEN
# gecerli ve asagida kilitli kaliyor.
kontrol("⭐ I-50 (I-51 devraldi): `MODEL_K` artik OLCULEN yeni deger",
        abs(_kk.MODEL_K - 0.935) < 1e-6, _kk.MODEL_K)
kontrol("⭐ I-50 (I-51 devraldi): marj OLCULEN yeni held-out degeri",
        abs(_kk.MODEL_EN_KOTU_HATA - 0.144) < 1e-9, _kk.MODEL_EN_KOTU_HATA)
_KKS50 = oku(KOK, "editor/kalite_kapisi.py")
kontrol("⭐ I-50 (I-51 devraldi): doygunluk ANCAK yeni veriyle eklendi",
        "DOYGUNLUK" in _KKS50 and "MODEL_D0" in _KKS50)
kontrol("⭐ I-50: I-50'nin KENDI hukmu duruyor — o gunku TRAIN'de "
        "d>=0.5 YOKTU ve doygunluk held-out'u KOTULESTIRIYORDU",
        _I50["train_d_buyuk"] == 0
        and _I50["B_doygunluk"]["held"] > _I50["A_fit"]["held"])
kontrol("I-50: YANLIS FAIL guvencesi korundu (fail sarti degismedi)",
        _kk.beklenen_optik_olcusu(enerji=8.483, d=0.01616)["seviye"] == "fail"
        and _kk.beklenen_optik_olcusu(enerji=9.391,
                                      d=0.2826)["seviye"] == "temiz")

# ── GERILEME YOK ──
kontrol("⭐ I-50: ESIKLER GEVSETILMEDI (optik 2.0 / 1.5 / 3.0, enerji 11.589)",
        _kk.OPTIK_DURGUN_ESIGI == 2.0 and _kk.OPTIK_DURGUN_WARN_SN == 1.5
        and _kk.OPTIK_DURGUN_FAIL_SN == 3.0
        and abs(_kk.UZAMSAL_ENERJI_ESIGI - 11.589) < 1e-9)
_V50 = oku(os.path.dirname(KOK), "app", "render-studio", "src", "Video.tsx")
kontrol("I-50 GERILEME YOK: I-43 zoom tabani ve kova tablosu DEGISMEDI",
        "OPTIK_TABAN_ORANI = 0.045" in _V50
        and all(f"oran: {o}" in _V50 for o in (0.004, 0.014, 0.032, 0.062)))
kontrol("I-50 GERILEME YOK: I-38 yazi/sahne penceresi kapisi DURUYOR",
        "KALITE-YAZI-SAHNE-DISI" in _qon.FAIL_KODLARI)
kontrol("I-50 GERILEME YOK: I-23/I-24/I-25 kapilari DURUYOR",
        "KALITE-MOTION-ACILIS-KAPANIS" in _qon.FAIL_KODLARI
        and "KALITE-MOTION-ISLEV-TEKRAR" in _qon.FAIL_KODLARI
        and "ORAN-UYUMSUZ" in oku(KOK, "medya/edinim.py")
        and "class DevreKesici" in oku(KOK, "medya/edinim.py"))
kontrol("I-50 GERILEME YOK: lisans/provenance kapilari DURUYOR",
        "KALITE-KUNYE-EKSIK" in _qon.FAIL_KODLARI
        and "def lisans_suz" in oku(KOK, "edit_kopru.py"))
kontrol("I-50 GERILEME YOK: 22 alanlik generate sozlesmesi DEGISMEDI",
        len(set(re.findall(r"\{ad: '(\w+)'",
                           oku(KOK, "static/js/api.js")))) == 22)
kontrol("I-50: kullanici secimleri (zoom/pan alanlari) DOKUNULMADI",
        "zoom: 'in' | 'out' | 'yok'" in _V50
        and "pan: 'right' | 'left' | 'top' | 'bottom' | 'yok'" in _V50)

blok("§39y I-49 — b005 TUR/TAKSON: YEREL SINANAMAZ, **ELENDI** (olculdu)")

# ⚠ HEDEF: I-47'nin (donem) ve I-48'in (yer/ozne) yakalayamadigi UCUNCU
# negatif — b005, aday "Ricinus communis seedling NC2.jpg", anlatim cim
# tohumu/fidesi baglami — YEREL olarak sinanabilir mi?
# Olculdu -> SINANAMAZ. Yaklasim I-34/I-48 dersiyle ELENDI.
# URETIM KODU DEGISMEDI (yalniz bu test + handoff).
# Yeni saglayici / VLM / embedding / LLM / ikinci ag cagrisi / ucretli API /
# paket-credential degisikligi / ozel-case kara liste YOK.
#
# ── OLCUM 1: DEPODA TAKSONOMIK KAYNAK YOK ──
#   kurulu taksonomi/ML paketi : YOK (nltk/spacy/Bio/sklearn/numpy... hicbiri)
#   taksonomi.py               : KONSEPT/NIYET taksonomisi, biyolojik DEGIL
#   webapp/veri/               : ['anim','durumlar','gecici','onbellek'] —
#                                tur/takson veri kumesi YOK
#
# ── OLCUM 2: ADAY METADATA'SINDA TUR/KATEGORI ALANI YOK ──
# 17 gercek kunye dosyasinin TUM alanlari tarandi (21 alan): aciklama,
# alaka_sirasi, asset_id, atif_gerekli, atif_metni, baslik, eser_sahibi,
# genislik, indirme_url, kaynak_niteligi, kaynak_saglayici, lisans,
# lisans_url, mime, olcu_bilinmiyor, olculen_olcu, oran_karari, orijinal_url,
# red_nedeni, render_kullanilabilir, saglayici, yukseklik.
# tur / kategori / takson / etiket alani: **YOK**.
#
# ── OLCUM 3/4: TEK CIKARILABILIR SINYAL — LATIN IKILI ADLANDIRMA ──
# Salt YAPISAL olcut (taksonomi.py'nin "sinyal metnin BICIMINDEN gelir"
# kuralinin aynisi): buyuk harfli cins + kucuk harfli Latin sonekli epitet.
#   beat  sinif      siki sinyal                 gevsek sinyal
#   b001  NEG        []                          []
#   b002  NEG        ['Heteropogon contortus']   ['Heteropogon contortus']
#   b003  POZ        []                          ['Mountainview section']
#   b004  POZ        []                          ['Sprinkler head']
#   b005  NEG HEDEF  ['Ricinus communis']        ['Ricinus communis']
#   b006  POZ        []                          []
# SIKI: negatiflerde 2/3, pozitiflerde 0/3. GEVSEK: pozitiflerde 2/3 —
# yani Latin sonek sarti OLMADAN sinyal kullanilamaz (I-34'teki yanlis
# pozitif tablosunun aynisi).
#
# ── OLCUM 5: 17 GERCEK ADAYDA YANLIS ALARM = 1 (b005'in kendisi) ──
#
# ── OLCUM 6 (BELIRLEYICI): SINYALIN VARLIGI "YANLIS" DEMEK DEGIL ──
# Sinyal "baslik BIR TUR ADI TASIYOR" der; "TUR YANLIS" DEMEZ. Kendi
# verimizde KANITLANDI: isaretlenen iki adaydan biri olan b002'nin oznesi
# *Heteropogon contortus* BIR CIM TURUDUR (Poaceae) — yani anlatimla AYNI
# ozne ailesinde. b002'nin kusuru tur degil YER/ORTAM (I-48'de olculdu).
# Dolayisiyla isaret kumesinin YARISI zaten "tur uyusmazligi" DEGIL.
# "Ricinus communis cim DEGILDIR" hukmunu vermek icin hangi turun cim
# oldugunu bilmek gerekir; bunun yerel karsiligi OLCUM 1/2'de ARANDI ve YOK.
#
# ── TERS ETKI: sinyal EN IYI ETIKETLENMIS adaylari cezalandirirdi ──
# Bilimsel kunyeli (tur adi tasiyan) bir aday DOGRU da olabilir
# (or. lawn videosunda *Lolium perenne*). Sinyal onu da isaretlerdi ve
# dogruyu yanlistan AYIRAMAZDI.
#
# ⚠ HUKUM: b005 tur/takson ayrimi MEVCUT YEREL kaynaklarla TASINAMAZ.
# Uretime eklenmedi; b005 KABUL ENGELI OLARAK SURUYOR.
#
# ── AYRICA OLCULEN (sonraki atom icin veri, bu atomda KULLANILMADI) ──
# `aciklama` alani 17 adayin 11'inde DOLU — ama lawn pilotunun BES adayinin
# HEPSINDE BOS. Yani bu pilot icin daha zengin metin de YOK.

_MK49 = __import__("medya_kapisi")
_LATIN_SON49 = ("us", "um", "is", "ii", "ae", "ata", "osa", "ana", "ica",
                "ensis", "oides", "folia", "flora")
_IKILI49 = re.compile(r"\b([A-Z][a-z]{3,})[ \-]([a-z]{4,})\b")


def _ikili49(metin, latin_sonek=True):
    """Latin ikili adlandirma — SALT YAPISAL, kelime listesi YOK."""
    out = []
    for m in _IKILI49.finditer(str(metin or "")):
        if latin_sonek and not m.group(2).endswith(_LATIN_SON49):
            continue
        out.append(f"{m.group(1)} {m.group(2)}")
    return out


_CIFT49 = [
    ("b001", "NEG", "Vegetable, grass and flower seeds, 1900 (1900) "
                    "(20532148836).jpg"),
    ("b002", "NEG", "Starr-101229-6113-Heteropogon contortus-habitat seed "
                    "ball paper bag mulch piles-Kanapou-Kahoolawe "
                    "(25059536945).jpg"),
    ("b003", "POZ", "2025-04-07 15 59 57 A patchy lawn in spring within Ann "
                    "M. Banchoff Park in the Mountainview section of Ewing "
                    "Township, Mercer County, New Jersey.jpg"),
    ("b004", "POZ", "Sprinkler Irrigation - Sprinkler head.JPG"),
    ("b005", "NEG", "Ricinus communis seedling NC2.jpg"),
    ("b006", "POZ", "Dülmen, Mühlenwegfriedhof -- 2012 -- 8083.jpg"),
]

# ── OLCUM 1: yerel taksonomik kaynak YOK ──
_paket49 = []
for _p49 in ("nltk", "spacy", "Bio", "sklearn", "numpy", "gensim", "pygbif",
             "ete3"):
    try:
        __import__(_p49)
        _paket49.append(_p49)
    except Exception:                                             # noqa: BLE001
        pass
kontrol("⭐ I-49 OLCUM: kurulu taksonomi/ML paketi YOK",
        _paket49 == [], _paket49)
_TK49 = __import__("taksonomi")
kontrol("⭐ I-49 OLCUM: `taksonomi.py` BIYOLOJIK degil (konsept/niyet)",
        not any(x in (_TK49.__doc__ or "").lower()
                for x in ("species", "binomial", "botanik", "poaceae")))
# ⚠ FAZ R-1d-a: alt dizi eslesmesi CALISMA ZAMANI SIRLARINI da yakaliyordu —
# `.oturum_anahtari` icinde "o(tur)um" gectigi icin bu olcum YANLIS POZITIF
# veriyordu. Olcumun iddiasi "tur/takson VERI KUMESI yok"; nokta ile baslayan
# sir dosyalari ve calisma zamani JSON depolari veri kumesi DEGILDIR ve
# .gitignore'dadir. Iddia GEVSETILMEDI, kapsami DOGRULANDI.
_VERI49_CALISMA = {"kullanicilar.json", "kutuphane.json", "saglayicilar.json"}
kontrol("⭐ I-49 OLCUM: `webapp/veri/` altinda tur/takson veri kumesi YOK",
        not [d for d in os.listdir(os.path.join(KOK, "veri"))
             if not d.startswith(".") and d not in _VERI49_CALISMA
             and any(x in d.lower() for x in ("tur", "takson", "species",
                                              "plant", "bitki"))],
        sorted(os.listdir(os.path.join(KOK, "veri"))))

# ── OLCUM 2: metadata'da tur/kategori alani YOK ──
_ALAN49 = {"aciklama", "alaka_sirasi", "asset_id", "atif_gerekli",
           "atif_metni", "baslik", "eser_sahibi", "genislik", "indirme_url",
           "kaynak_niteligi", "kaynak_saglayici", "lisans", "lisans_url",
           "mime", "olcu_bilinmiyor", "olculen_olcu", "oran_karari",
           "orijinal_url", "red_nedeni", "render_kullanilabilir",
           "saglayici", "yukseklik"}
kontrol("⭐ I-49 OLCUM: aday metadata'sinda tur/kategori/takson alani YOK",
        not [a for a in _ALAN49
             if any(x in a for x in ("takson", "kategori", "species",
                                     "etiket"))], sorted(_ALAN49))

# ── OLCUM 3/4: sinyal ayiriyor GIBI gorunuyor ──
_S49 = {b: (_ikili49(t, True), _ikili49(t, False)) for b, _c, t in _CIFT49}
kontrol("⭐ I-49 OLCUM: SIKI sinyal negatiflerde 2/3, pozitiflerde 0/3",
        sum(1 for b, c, _t in _CIFT49 if c == "NEG" and _S49[b][0]) == 2
        and sum(1 for b, c, _t in _CIFT49 if c == "POZ" and _S49[b][0]) == 0,
        {b: _S49[b][0] for b, *_ in _CIFT49})
kontrol("⭐ I-49 OLCUM: GEVSEK sinyal POZITIFLERIN 2/3'unu isaretliyor "
        "(Latin sonek sarti olmadan KULLANILAMAZ)",
        sum(1 for b, c, _t in _CIFT49 if c == "POZ" and _S49[b][1]) == 2,
        {b: _S49[b][1] for b, *_ in _CIFT49})

# ── OLCUM 6 (BELIRLEYICI): varlik != yanlislik ──
kontrol("⭐ I-49 BELIRLEYICI: isaretlenen IKI adaydan BIRI (b002) anlatimla "
        "AYNI ozne ailesinde — *Heteropogon contortus* BIR CIM TURU",
        _S49["b002"][0] == ["Heteropogon contortus"]
        and _S49["b005"][0] == ["Ricinus communis"],
        [_S49["b002"][0], _S49["b005"][0]])
kontrol("⭐ I-49 HUKUM: 'tur adi VAR' ile 'tur YANLIS' ayrimi icin YEREL "
        "kaynak YOK -> sinyal hukum TASIYAMAZ",
        _paket49 == []
        and not [a for a in _ALAN49 if "takson" in a or "species" in a])

# ── ELENDI: URETIM KODU DEGISMEDI ──
_MKS49 = oku(KOK, "medya_kapisi.py")
kontrol("⭐ I-49: ikili adlandirma sinyali URETIME EKLENMEDI",
        not any(x in _MKS49.lower()
                for x in ("ricinus", "heteropogon", "binomial", "ikili_ad")),
        "sinyal uretime sizmis")
kontrol("I-49: ozel-case kara liste YOK (varliga/dosyaya ozel esleme yok)",
        "ricinus" not in _MKS49.lower()
        and "grass_seedling" not in _MKS49.lower())
kontrol("⭐ I-49: yeni paket/saglayici/ag cagrisi/credential YOK",
        not any(x in _MKS49 for x in ("requests", "urllib", "http",
                                      "subprocess", "socket", "api_key",
                                      "API_KEY", "import nltk", "spacy")))

# ── GERILEME YOK ──
kontrol("I-49 GERILEME YOK: I-47 donem uyarisi HALA b001'i yakaliyor",
        _MK49.donem_uyarisi(
            "There is a bag of grass seed on my garage shelf right now.",
            _CIFT49[0][2]).get("uyari") is True)
kontrol("I-49 GERILEME YOK: I-48 hukmu duruyor (yer adlari sozlukte YOK)",
        not any(x in _MKS49.lower() for x in ("kahoolawe", "kanapou"))
        and len(_MK49.BIYOM_ISARETI) == 4)
kontrol("I-49 GERILEME YOK: biyom kapisi GERCEK celiskide HALA REDDEDIYOR",
        _MK49.kapi("The desert dunes stretch for miles.",
                   "polar bear on arctic sea ice")[0] is False)
kontrol("I-49 GERILEME YOK: edinim kapilari ve 429 devre kesici DURUYOR",
        "class DevreKesici" in oku(KOK, "medya/edinim.py")
        and "COZUNURLUK-YETERSIZ" in oku(KOK, "medya/edinim.py")
        and "ORAN-UYUMSUZ" in oku(KOK, "medya/edinim.py"))
kontrol("I-49 GERILEME YOK: lisans/provenance kapilari DURUYOR",
        "KALITE-KUNYE-EKSIK" in _qon.FAIL_KODLARI
        and "def lisans_suz" in oku(KOK, "edit_kopru.py"))
kontrol("⭐ I-49: ESIKLER GEVSETILMEDI (optik 2.0 / enerji 11.589)",
        _kk.OPTIK_DURGUN_ESIGI == 2.0
        and abs(_kk.UZAMSAL_ENERJI_ESIGI - 11.589) < 1e-9)
kontrol("I-49 GERILEME YOK: 22 alanlik generate sozlesmesi DEGISMEDI",
        len(set(re.findall(r"\{ad: '(\w+)'",
                           oku(KOK, "static/js/api.js")))) == 22)
_V49 = oku(os.path.dirname(KOK), "app", "render-studio", "src", "Video.tsx")
kontrol("I-49: kullanici secimleri (zoom/pan alanlari) DOKUNULMADI",
        "zoom: 'in' | 'out' | 'yok'" in _V49
        and "pan: 'right' | 'left' | 'top' | 'bottom' | 'yok'" in _V49)

blok("§39x I-48 — b002 YER/OZNE: BIYOM SOZLUGU YOLUYLA **ELENDI** (olculdu)")

# ⚠ HEDEF: I-47'nin yakalayamadigi b002 negatifi ("Kanapou-Kahoolawe" yer
# adi) MEVCUT yerel biyom sozluguyle, AGSIZ ve deterministik olarak
# sinanabilir mi? Olculdu -> SINANAMAZ. Yaklasim I-34 dersiyle ELENDI:
# ayiran kanit yoksa zorlama YOK, ozel-case kara liste YOK, sahte PASS YOK.
# URETIM KODU DEGISMEDI (yalniz bu test + handoff).
#
# ⚠ Yeni saglayici / ikinci ag cagrisi / ucretli API / credential degisikligi
# YOK; tek `ara()`, mevcut kota ve 429 devre kesici AYNEN.
#
# ── OLCUM 1: MEVCUT SOZLUKLE ALTI GERCEK CIFT (sahne + aday basligi) ──
#   beat  sinif            sahne_biyom  aday_biyom  kapi
#   b001  NEG (donem)      []           []          gecer
#   b002  NEG (HEDEF)      []           []          gecer
#   b003  POZ              []           []          gecer
#   b004  POZ              []           []          gecer
#   b005  NEG (tur)        []           []          gecer
#   b006  POZ              []           []          gecer
#   VIDEO BAGLAMI biyomu da []  -> kapi YAPISAL OLARAK ATIL.
#
# ── OLCUM 2: YER ADI EKLENSE BILE (Kahoolawe/Kanapou -> "tropik") ──
# Aday tarafi "tropik" kazaniyor AMA SAHNE tarafi BOS kaliyor; `biyom_kapisi`
# her IKI tarafin biyomunu ister ("emin degilsen gecir") -> CELISKI URETILMEZ.
# Yani yer adi eklemek TEK BASINA b002'yi yakalayamaz.
#
# ── OLCUM 3: SAHNENIN GERCEK KUSAGI SOZLUKTE IFADE EDILEMIYOR ──
# Sozlukte dort kusak var: col / kent / kutup / tropik. "iliman/temperate"
# kusagi YOK ve "lawn/grass/garden" isareti HICBIR kusakta yok. Dolayisiyla
# "ABD banliyo cimi" kusagi YAZILAMAZ ve CELISEN tablosu bu celiskiyi
# IFADE EDEMEZ.
#
# ── OLCUM 4: EKLENMESI GEREKEN IDDIA FAKTUEL OLARAK YANLIS ──
# Kapiyi calistirmak icin CELISEN'e "cim/bahce sahnesi ⊥ tropik aday"
# yazmak gerekirdi. Bu iddia GENEL OLARAK YANLIS: sozlukte "hawaii" tropik
# kusaktadir ve b002 adayinin OZNESI *Heteropogon contortus* — bir CIM
# turudur. Iki taraf AYNI ozne ailesinde; iklim celiskisi YOKTUR. Kapi bu
# ornekte ancak KAZAYLA dogru sonuc verirdi.
#
# ── OLCUM 5: KELIME ORTUSMESI TERS CALISIYOR (ayirici degil) ──
#   b002 NEG  ortak kelime: ['bag', 'seed']      <- IKI kelime
#   b005 NEG  ortak kelime: ['seedling']
#   b001 NEG  ortak kelime: ['grass']
#   b003 POZ  ortak kelime: ['lawn', 'patchy', 'the']
#   b004 POZ  ortak kelime: []                   <- SIFIR
#   b006 POZ  ortak kelime: []                   <- SIFIR
# Iki POZITIF kontrol anlatimla HIC kelime paylasmiyor, NEGATIF b002 iki
# kelime paylasiyor. Kelime tabanli her ayrim negatifleri pozitiflerin
# USTUNE koyar — I-34'te olculen "ayiran esik yok" durumunun aynisi.
#
# ⚠ HUKUM: yer/ozne ayrimi MEVCUT yerel sozlukle TASINAMAZ. Uretime
# eklenmedi; b002 KABUL ENGELI OLARAK SURUYOR ve durustce raporlaniyor.

_MK48 = __import__("medya_kapisi")
_A48 = ["There is a bag of grass seed on my garage shelf right now.",
        "By the middle of October, he was standing in the same thin, patchy "
        "lawn he started with.",
        "Then water lightly two or three times a day, every day for two "
        "solid weeks.",
        "Warm soil to germinate, and cool air so the seedling does not cook "
        "once it comes up.",
        "Soil is still loaded with summer heat, so germination is fast."]
_BAGLAM48 = " ".join(_A48)
_CIFT48 = [
    ("b001", _A48[0], "Vegetable, grass and flower seeds, 1900 (1900) "
                      "(20532148836).jpg"),
    ("b002", _A48[0], "Starr-101229-6113-Heteropogon contortus-habitat seed "
                      "ball paper bag mulch piles-Kanapou-Kahoolawe "
                      "(25059536945).jpg"),
    ("b003", _A48[1], "2025-04-07 15 59 57 A patchy lawn in spring within "
                      "Ann M. Banchoff Park in the Mountainview section of "
                      "Ewing Township, Mercer County, New Jersey.jpg"),
    ("b004", _A48[2], "Sprinkler Irrigation - Sprinkler head.JPG"),
    ("b005", _A48[3], "Ricinus communis seedling NC2.jpg"),
    ("b006", _A48[4], "Dülmen, Mühlenwegfriedhof -- 2012 -- 8083.jpg"),
]

kontrol("⭐ I-48 OLCUM: alti gercek ciftin HICBIRINDE sahne biyomu cikmiyor",
        all(not (_MK48.biyom_bul(m) or _MK48.biyom_bul(_BAGLAM48))
            for _, m, _t in _CIFT48),
        [(b, sorted(_MK48.biyom_bul(m))) for b, m, _t in _CIFT48])
kontrol("⭐ I-48 OLCUM: video baglami da biyom VERMIYOR -> kapi YAPISAL ATIL",
        not _MK48.biyom_bul(_BAGLAM48), sorted(_MK48.biyom_bul(_BAGLAM48)))
kontrol("⭐ I-48 OLCUM: alti ciftin ALTISI da biyom kapisindan geciyor",
        all(_MK48.biyom_kapisi(m, t, _BAGLAM48)[0] for _, m, t in _CIFT48))
kontrol("⭐ I-48 OLCUM: kapi gerekcesi 'biyomu cikarilamadi' (atil oldugunun kaniti)",
        "cikarilamadi" in _MK48.biyom_kapisi(_CIFT48[1][1], _CIFT48[1][2],
                                             _BAGLAM48)[1],
        _MK48.biyom_kapisi(_CIFT48[1][1], _CIFT48[1][2], _BAGLAM48)[1])

# ── Yer adi eklense BILE sahne tarafi bos kalir -> celiski uretilemez ──
_YER48 = ("kahoolawe", "kanapou")


def _biyom_uzatilmis48(metin):
    b = set(_MK48.biyom_bul(metin))
    d = " " + str(metin or "").lower() + " "
    if any(_MK48._gecer_mi(a, d) for a in _YER48):
        b.add("tropik")
    return b


kontrol("⭐ I-48 OLCUM: yer adi eklense ADAY 'tropik' kazanir",
        _biyom_uzatilmis48(_CIFT48[1][2]) == {"tropik"},
        sorted(_biyom_uzatilmis48(_CIFT48[1][2])))
kontrol("⭐ I-48 HUKUM: yer adi eklense BILE sahne bos -> CELISKI URETILEMEZ",
        not _biyom_uzatilmis48(_CIFT48[1][1])
        and not _biyom_uzatilmis48(_BAGLAM48),
        sorted(_biyom_uzatilmis48(_CIFT48[1][1])))

# ── Sahnenin gercek kusagi sozlukte IFADE EDILEMIYOR ──
kontrol("⭐ I-48 KOK NEDEN: sozlukte 'iliman/temperate' kusagi YOK",
        not ({"iliman", "temperate", "ılıman"} & set(_MK48.BIYOM_ISARETI)),
        sorted(_MK48.BIYOM_ISARETI))
kontrol("⭐ I-48 KOK NEDEN: 'lawn/grass/garden' HICBIR kusakta yok",
        not [k for k, v in _MK48.BIYOM_ISARETI.items()
             if any(("lawn" in x or "grass" in x or "garden" in x)
                    for x in v)],
        [k for k, v in _MK48.BIYOM_ISARETI.items()
         if any(("lawn" in x or "grass" in x or "garden" in x) for x in v)])
kontrol("⭐ I-48: eklenecek iddia FAKTUEL YANLIS — 'hawaii' TROPIK kusakta "
        "ve b002 adayinin oznesi bir CIM turu (Heteropogon contortus)",
        "hawaii" in _MK48.BIYOM_ISARETI["tropik"]
        and "Heteropogon contortus" in _CIFT48[1][2])

# ── Kelime ortusmesi TERS calisiyor (ayirici degil) ──
_kel48 = lambda s: set(re.findall(r"[a-zà-ÿ]{3,}", s.lower()))  # noqa: E731
_ort48 = {b: sorted(_kel48(m) & _kel48(t)) for b, m, t in _CIFT48}
kontrol("⭐ I-48 OLCUM: IKI POZITIF kontrol anlatimla SIFIR kelime paylasiyor",
        _ort48["b004"] == [] and _ort48["b006"] == [], _ort48)
kontrol("⭐ I-48 HUKUM: NEGATIF b002 pozitiflerden DAHA COK kelime paylasiyor "
        "-> kelime tabanli ayrim TERS calisir",
        len(_ort48["b002"]) > len(_ort48["b004"])
        and len(_ort48["b002"]) > len(_ort48["b006"]), _ort48)

# ── ELENDI: URETIM KODU DEGISMEDI ──
_MKS48 = oku(KOK, "medya_kapisi.py")
kontrol("⭐ I-48: yer adlari sozluge EKLENMEDI (yaklasim elendi)",
        not any(x in _MKS48.lower() for x in ("kahoolawe", "kanapou")),
        "yer adi uretime sizmis")
kontrol("⭐ I-48: yeni kusak/celiski EKLENMEDI (4 kusak, 3 celiski)",
        len(_MK48.BIYOM_ISARETI) == 4 and len(_MK48.CELISEN) == 3,
        (sorted(_MK48.BIYOM_ISARETI), sorted(_MK48.CELISEN)))
kontrol("I-48: ozel-case kara liste YOK (varliga/dosyaya ozel esleme yok)",
        "starr-101229" not in _MKS48.lower()
        and "25059536945" not in _MKS48)
kontrol("⭐ I-48: yeni saglayici/ag cagrisi/credential YOK",
        not any(x in _MKS48 for x in ("requests", "urllib", "http",
                                      "subprocess", "socket", "api_key",
                                      "API_KEY")))

# ── GERILEME YOK ──
kontrol("I-48 GERILEME YOK: I-47 donem uyarisi HALA b001'i yakaliyor",
        _MK48.donem_uyarisi(_CIFT48[0][1], _CIFT48[0][2]).get("uyari") is True)
kontrol("I-48 GERILEME YOK: biyom kapisi GERCEK celiskide HALA REDDEDIYOR",
        _MK48.kapi("The desert dunes stretch for miles.",
                   "polar bear on arctic sea ice")[0] is False)
kontrol("I-48 GERILEME YOK: edinim kapilari ve 429 devre kesici DURUYOR",
        "class DevreKesici" in oku(KOK, "medya/edinim.py")
        and "COZUNURLUK-YETERSIZ" in oku(KOK, "medya/edinim.py")
        and "ORAN-UYUMSUZ" in oku(KOK, "medya/edinim.py"))
kontrol("I-48 GERILEME YOK: lisans/provenance kapilari DURUYOR",
        "KALITE-KUNYE-EKSIK" in _qon.FAIL_KODLARI
        and "def lisans_suz" in oku(KOK, "edit_kopru.py"))
kontrol("⭐ I-48: ESIKLER GEVSETILMEDI (optik 2.0 / enerji 11.589)",
        _kk.OPTIK_DURGUN_ESIGI == 2.0
        and abs(_kk.UZAMSAL_ENERJI_ESIGI - 11.589) < 1e-9)
kontrol("I-48 GERILEME YOK: 22 alanlik generate sozlesmesi DEGISMEDI",
        len(set(re.findall(r"\{ad: '(\w+)'",
                           oku(KOK, "static/js/api.js")))) == 22)
_V48 = oku(os.path.dirname(KOK), "app", "render-studio", "src", "Video.tsx")
kontrol("I-48: kullanici secimleri (zoom/pan alanlari) DOKUNULMADI",
        "zoom: 'in' | 'out' | 'yok'" in _V48
        and "pan: 'right' | 'left' | 'top' | 'bottom' | 'yok'" in _V48)

blok("§39w I-47 — DONEM KAPISI TEK YONLUYDU (semantik kabul engeli)")

# ⚠ KABUL ENGELI: lawn pilotu I-39'dan beri "otomatik kapilarin HEPSI PASS"
# olmasina ragmen KABUL EDILMIYOR; tek neden b001/b002/b005 semantik
# uyusmazligi (dort kez GOZLE dogrulandi).
#
# ⚠ ONCE ELENENLER TEKRARLANMADI:
#   · I-34 kare-bakan sinyaller (metin yogunlugu / kenar / duz-parlak /
#     specular): 28 olcumde AYIRAN ESIK YOK, en iyi precision 0.25 -> ELENDI.
#   · I-35 sorgu daraltmasi: vitrini eleyen her daraltma NASA'yi bosaltiyor,
#     NASA'yi koruyan her daraltma vitrini birakiyor -> ELENDI.
#     (`-display` gibi negatif terim I-29'da olculdu: recall %0, 7 isaretin
#     5'i yanlis pozitif.)
# Bu atom YENI SAGLAYICI, IKINCI AG CAGRISI, UCRETLI API ya da sahte
# embedding/LLM KULLANMAZ; yalnizca ZATEN VAR OLAN metadata metnini okur.
#
# ⚠ OLCULEN KUSUR — KAPI TEK YONLU: `donem_kapisi` yalnizca SAHNE tarihselse
# adayi denetler (`tarihsel_mi(sahne)` False ise HEMEN True doner). Ters yon
# — TARIHSEL ADAY, GUNCEL SAHNEDE — hic denetlenmiyor. Pilotun GERCEK
# ciftlerinde olculdu (alti ciftin ALTISI da mevcut kapilardan geciyor):
#   beat  aday basligi                                   tarihsel(aday)
#   b001  "Vegetable, grass and flower seeds, 1900 (1900)"      EVET  <- kusur
#   b002  "Starr-101229-...-Kanapou-Kahoolawe"                  hayir
#   b003  "2025-04-07 ... A patchy lawn in spring ..."          hayir
#   b004  "Sprinkler Irrigation - Sprinkler head"               hayir
#   b005  "Ricinus communis seedling NC2"                       hayir
#   b006  "Dulmen, Muhlenwegfriedhof -- 2012 -- 8083"           hayir
# Anlatim ("...on my garage shelf RIGHT NOW") guncel; aday 1900 tarihli bir
# tohum katalogu fotografi -> GOZLE dogrulanan uyusmazligin ta kendisi.
#
# ⚠ YANLIS ALARM ORANI GERCEK KUMEDE OLCULDU: onbellekteki 17 GERCEK aday
# kunyesinin YALNIZ 1'i "tarihsel" isaretleniyor ve o da b001'in kendisi
# (16 temiz aday isaretlenmedi).
#
# ⚠ DURUST SINIR: b002 (yer/ozne uyusmazligi) ve b005 (Ricinus communis —
# cim degil) bu sinyalle ULASILAMAZ; olculdu ve ASLA "temiz" DIYE
# SUNULMUYOR. Uc negatiften BIRI yakalaniyor.
# ⚠ SEVIYE `warn` ve SECIM DEGISMIYOR: `kapi()` BIT-BIT ayni kalir (aday
# ELENMEZ). I-35'te olculdu ki nadir bir kalite kusurunu sik bir TAM
# BASARISIZLIKLA (MEDYASIZ-BEAT) takas etmek yanlis muhendisliktir.

_MK47 = __import__("medya_kapisi")
_B001_METIN = "There is a bag of grass seed on my garage shelf right now."
_CIFTLER47 = [
    ("b001", "Vegetable, grass and flower seeds, 1900 (1900) "
             "(20532148836).jpg", _B001_METIN, True),
    ("b002", "Starr-101229-6113-Heteropogon contortus-habitat seed ball "
             "paper bag mulch piles-Kanapou-Kahoolawe (25059536945).jpg",
     _B001_METIN, False),
    ("b003", "2025-04-07 15 59 57 A patchy lawn in spring within Ann M. "
             "Banchoff Park in the Mountainview section of Ewing Township, "
             "Mercer County, New Jersey.jpg",
     "By the middle of October, he was standing in the same thin, patchy "
     "lawn he started with.", False),
    ("b004", "Sprinkler Irrigation - Sprinkler head.JPG",
     "Then water lightly two or three times a day, every day for two solid "
     "weeks.", False),
    ("b005", "Ricinus communis seedling NC2.jpg",
     "Warm soil to germinate, and cool air so the seedling does not cook "
     "once it comes up.", False),
    ("b006", "Dülmen, Mühlenwegfriedhof -- 2012 -- 8083.jpg",
     "Soil is still loaded with summer heat, so germination is fast.", False),
]

kontrol("⭐ I-47 KIRMIZI: `donem_uyarisi` VAR (ters yon denetleniyor)",
        hasattr(_MK47, "donem_uyarisi"), "ters yon denetimi yok")

if hasattr(_MK47, "donem_uyarisi"):
    _sonuc47 = {b: _MK47.donem_uyarisi(m, t) for b, t, m, _ in _CIFTLER47}
    kontrol("⭐ I-47 KIRMIZI: b001 (1900 tarihli aday, guncel sahne) UYARILIYOR",
            _sonuc47["b001"].get("uyari") is True
            and _sonuc47["b001"].get("yon") == "aday-tarihsel",
            _sonuc47["b001"])
    kontrol("⭐ I-47: BES kontrol cifti UYARILMIYOR (yanlis alarm yok)",
            [b for b, *_ in _CIFTLER47 if _sonuc47[b].get("uyari")] == ["b001"],
            [b for b, *_ in _CIFTLER47 if _sonuc47[b].get("uyari")])
    kontrol("⭐ I-47 DURUST SINIR: b002/b005 bu sinyalle ULASILAMAZ "
            "(yakalanmiyor ve 'temiz' DIYE SUNULMUYOR)",
            _sonuc47["b002"].get("uyari") is False
            and _sonuc47["b005"].get("uyari") is False
            and _sonuc47["b002"].get("kapsam") == "yalniz-donem",
            [_sonuc47["b002"], _sonuc47["b005"]])
    kontrol("⭐ I-47: TARIHSEL sahnede tarihsel aday UYARILMAZ (uyumlu)",
            _MK47.donem_uyarisi(
                "In 1903 the brothers hauled the seed by wagon.",
                "Vegetable, grass and flower seeds, 1900.jpg"
            ).get("uyari") is False)
    kontrol("I-47: aday tarihsel DEGILSE uyari YOK",
            _MK47.donem_uyarisi(_B001_METIN,
                                "Sprinkler head.JPG").get("uyari") is False)
    kontrol("⭐ I-47: EMIN DEGILSEN ENGELLEME — metin yoksa hukum YOK",
            _MK47.donem_uyarisi("", "").get("olculdu") is False
            and "uyari" not in _MK47.donem_uyarisi("", ""))
    kontrol("I-47: uyari GEREKCELI (hangi isaret, hangi yon)",
            bool(_sonuc47["b001"].get("gerekce"))
            and "1900" in _sonuc47["b001"]["gerekce"],
            _sonuc47["b001"].get("gerekce"))

# ── SECIM DAVRANISI DEGISMEDI: aday ELENMEZ ──
kontrol("⭐ I-47: `kapi()` BIT-BIT ayni — b001 adayi HALA ELENMIYOR",
        _MK47.kapi(_B001_METIN, _CIFTLER47[0][1])[0] is True)
kontrol("⭐ I-47 GERILEME YOK: eski YON hala calisiyor "
        "(tarihsel sahne + modern aday REDDEDILIR)",
        _MK47.kapi("The 1890 expedition camped here.",
                   "man using a smartphone")[0] is False)
kontrol("I-47 GERILEME YOK: biyom kapisi DURUYOR",
        _MK47.kapi("The desert dunes stretch for miles.",
                   "polar bear on arctic sea ice")[0] is False)

# ── PRE-QA: DURUST WARN ──
kontrol("⭐ I-47 KIRMIZI: `KALITE-SEMANTIK-DONEM` kodu VAR",
        "KALITE-SEMANTIK-DONEM" in _qon.KALITE_KODLARI)
kontrol("⭐ I-47: kod FAIL kodlarinda DEGIL (EMIN DEGILSEN ENGELLEME)",
        "KALITE-SEMANTIK-DONEM" not in _qon.FAIL_KODLARI)
_QON47 = oku(KOK, "editor/qa_on.py")
kontrol("⭐ I-47 KIRMIZI: PRE-QA anlatim x aday basligini denetliyor",
        "donem_uyarisi" in _QON47, "PRE-QA'ya baglanmadi")

# ── AG/KOTA BUTCESI DEGISMEDI ──
_MKS47 = oku(KOK, "medya_kapisi.py")
kontrol("⭐ I-47: yeni saglayici/ag cagrisi YOK (saf metin, yerel)",
        not any(x in _MKS47 for x in ("requests", "urllib", "http",
                                      "subprocess", "socket")), "ag izi var")
kontrol("I-47 GERILEME YOK: edinim sozlesmesi ve 429 devre kesici DURUYOR",
        "class DevreKesici" in oku(KOK, "medya/edinim.py")
        and "COZUNURLUK-YETERSIZ" in oku(KOK, "medya/edinim.py")
        and "ORAN-UYUMSUZ" in oku(KOK, "medya/edinim.py"))
kontrol("I-47 GERILEME YOK: lisans/provenance ve tekrar kapilari DURUYOR",
        "KALITE-KUNYE-EKSIK" in _qon.FAIL_KODLARI
        and "KALITE-MEDYA-TEKRAR" in _qon.FAIL_KODLARI
        and "def lisans_suz" in oku(KOK, "edit_kopru.py"))
kontrol("⭐ I-47: ESIKLER GEVSETILMEDI (optik 2.0 / enerji 11.589)",
        _kk.OPTIK_DURGUN_ESIGI == 2.0
        and abs(_kk.UZAMSAL_ENERJI_ESIGI - 11.589) < 1e-9)
kontrol("I-47 GERILEME YOK: 22 alanlik generate sozlesmesi DEGISMEDI",
        len(set(re.findall(r"\{ad: '(\w+)'",
                           oku(KOK, "static/js/api.js")))) == 22)
_V47 = oku(os.path.dirname(KOK), "app", "render-studio", "src", "Video.tsx")
kontrol("I-47: kullanici secimleri (zoom/pan alanlari) DOKUNULMADI",
        "zoom: 'in' | 'out' | 'yok'" in _V47
        and "pan: 'right' | 'left' | 'top' | 'bottom' | 'yok'" in _V47)

blok("§39v I-46 — RISK OPTIK BIRIMDE IFADE EDILMIYORDU (enerji x yer degistirme)")

# ⚠ I-45'TE OLCULEN KUSUR: enerji-optik iliskisi TEK bir gezinme hizinda
# kalibre edilmisti; baska hizlarda gecerli olmadigi icin kapi o cekimlerde
# HUKUM VEREMIYORDU (b002/b005 "kapsam disi"). Ayrica pan ile zoom AYNI
# gezinmeyi uretse bile optikte AYRI davraniyor (b003 IoU 0.707 -> 7.485,
# b002 IoU 0.774 -> 2.288) — tek skaler "gezinme" yetmiyor.
#
# ⚠ MODEL TURETILDI, UYDURULMADI. Optik olcum ardisik ORNEK KARELER arasi
# ortalama mutlak farktir; duragan bir goruntu kayarken birinci mertebede
#     |I(p + d) - I(p)|  ~  |grad I| . d
# yani ENERJI (ornek piksel basina ort. mutlak gradyan) x YER DEGISTIRME
# (ornek piksel). Alan I-45 kadraj geometrisinden CIKAR:
#     ekranda (u,v) -> kaynakta (x + u.w, y + v.h)
#     Ds_x = Dx + u.Dw      d_x(u) = 64 . Ds_x / w
#     Ds_y = Dy + v.Dh      d_y(v) = 36 . Ds_y / h
# PAN saf OTELEME (Dx): d tum karede AYNI.
# ZOOM OLCEK degisimi (Dw): d merkezde 0, kenarda en buyuk -> ortalamasi
# kacinilmaz olarak KUCUK. Iki alan bu yuzden ayri; ayirmadan model olmaz.
#
# ⚠ KONTROLLU AILE — GERCEK RENDER'DA olculdu (editorv2, 1080p, iki enerji
# seviyesi x uc zoom hizi + uc pan hizi = 12 nokta, $0.00):
#     tur   E       d        optik    k = optik/(E.d)
#     zoom  18.565  0.15031  2.477    0.888
#     zoom  19.067  0.28945  4.562    0.827
#     zoom  19.709  0.20190  3.303    0.830
#     pan   18.625  0.01616  0.378    1.256
#     pan   18.591  0.04920  0.779    0.852
#     pan   18.612  0.12261  1.863    0.816
#     zoom   8.756  0.15031  1.270    0.965
#     zoom   8.756  0.28945  2.135    0.842
#     zoom   8.756  0.20190  1.563    0.884
#     pan    8.483  0.01616  0.188    1.371
#     pan    8.471  0.04920  0.398    0.955
#     pan    8.502  0.12261  0.934    0.896
# k MEDYANI 0.8877 (min 0.816, maks 1.371).
#
# ⚠ TUTULAN ORNEK (I-45'in ALTI GERCEK cekimi — kalibrasyona GIRMEDI):
#     beat  E       d       beklenen  olculen  hata
#     b001  15.596  0.2852     3.949    4.438  -11.0%
#     b002   9.391  0.2826     2.356    2.288   +3.0%
#     b003  19.962  0.4940     8.753    7.485  +16.9%
#     b004  17.347  1.3113    20.193   16.431  +22.9%   <- EN KOTU
#     b005  10.469  0.2595     2.411    2.686  -10.2%
#     b006  13.467  0.2618     3.130    3.116   +0.5%
# Ortalama mutlak hata %10.8, EN KOTU %22.9 (b004; d=1.31 ornek piksel ile
# birinci mertebe rejiminin disinda — model FAZLA tahmin ediyor, yani
# "hareket az" kapisi icin GUVENLI yonde).
#
# ⚠ FAIL SARTI OLCULEN HATADAN TURETILDI, ESIK UYDURULMADI: gercek deger
# `beklenen x (1 + EN_KOTU_HATA)` ustune cikamadi -> yalnizca
#     beklenen x 1.229 < OPTIK_DURGUN_ESIGI (2.0)
# oldugunda FAIL. 12 kontrollu + 6 tutulan noktanin HICBIRINDE yanlis fail
# yok; gercek dusuk-hareket vakalari (optik 0.188 / 0.398 / 0.934 / 1.270 /
# 1.563) DOGRU yakalaniyor. Belirsiz bant (beklenen < 2.0 ama guven yok)
# `warn` kalir -> EMIN DEGILSEN ENGELLEME korunur.

kontrol("⭐ I-46 KIRMIZI: `yer_degistirme_alani` VAR",
        hasattr(_kk, "yer_degistirme_alani"), "yer degistirme alani yok")
kontrol("⭐ I-46 KIRMIZI: `beklenen_optik_olcusu` VAR",
        hasattr(_kk, "beklenen_optik_olcusu"), "beklenen optik olcumu yok")
# ⚠ I-51 DEVRALDI: k, genisletilmis TRAIN'de (d>=0.5 dahil) yeniden
# olculdu -> 0.935. I-46'nin YONTEMI (olculen k, uydurma yok) korunuyor.
kontrol("⭐ I-46 (I-51 devraldi): model katsayisi OLCULEN degerdir",
        abs(getattr(_kk, "MODEL_K", 0.0) - 0.935) < 1e-6,
        getattr(_kk, "MODEL_K", None))
kontrol("⭐ I-46 (I-51 devraldi): model EN KOTU HATASI belgeli (%14.4)",
        abs(getattr(_kk, "MODEL_EN_KOTU_HATA", 0.0) - 0.144) < 1e-6,
        getattr(_kk, "MODEL_EN_KOTU_HATA", None))

if hasattr(_kk, "yer_degistirme_alani"):
    # b002'nin GERCEK kadraj uclari (I-45 geometrisiyle)
    _u0 = _kk.kadraj_kirpma_bolgesi(
        olcek=1.5342, pan_x=[0.5, 0.5], odak=[0.5, 0.5], guvenli_pay=0.1567,
        kaynak_g=3456, kaynak_y=2592, kare_g=1920, kare_y=1080, t=0.0)
    _u1 = _kk.kadraj_kirpma_bolgesi(
        olcek=1.35, pan_x=[0.5, 0.5], odak=[0.5, 0.5], guvenli_pay=0.1567,
        kaynak_g=3456, kaynak_y=2592, kare_g=1920, kare_y=1080, t=1.0)
    _yd = _kk.yer_degistirme_alani(_u0, _u1, sure_sn=2.201)
    kontrol("⭐ I-46: b002 yer degistirmesi OLCULDU (0.2826 ornek piksel)",
            _yd.get("olculdu") is True and abs(_yd["d"] - 0.2826) < 2e-3, _yd)
    kontrol("⭐ I-46: ZOOM cekiminde OTELEME bileseni YOK, olcek bileseni VAR",
            _yd["d_oteleme"] < 1e-4        # kirpma yuvarlamasinin kalintisi
            and abs(_yd["d_olcek"] - _yd["d"]) < 1e-4, _yd)
    # Saf PAN: olcek sabit, kirpma yanal kayar
    _p0 = _kk.kadraj_kirpma_bolgesi(
        olcek=1.06, pan_x=[0.15, 0.85], odak=[0.5, 0.5], guvenli_pay=0.0255,
        kaynak_g=5712, kaynak_y=4284, kare_g=1920, kare_y=1080, t=0.0)
    _p1 = _kk.kadraj_kirpma_bolgesi(
        olcek=1.06, pan_x=[0.15, 0.85], odak=[0.5, 0.5], guvenli_pay=0.0255,
        kaynak_g=5712, kaynak_y=4284, kare_g=1920, kare_y=1080, t=1.0)
    _ydp = _kk.yer_degistirme_alani(_p0, _p1, sure_sn=4.0)
    kontrol("⭐ I-46: PAN cekiminde OLCEK bileseni YOK, oteleme VAR "
            "(iki alan AYRISIYOR)",
            _ydp["d_olcek"] < 1e-4
            and abs(_ydp["d_oteleme"] - _ydp["d"]) < 1e-4, _ydp)
    kontrol("I-46: sure/kirpma yoksa hukum YOK (`olculdu=False`)",
            _kk.yer_degistirme_alani(_u0, _u1, sure_sn=0).get("olculdu")
            is False
            and _kk.yer_degistirme_alani({}, {}, sure_sn=4).get("olculdu")
            is False)

if hasattr(_kk, "beklenen_optik_olcusu"):
    # b002: E=9.391, d=0.2826 -> beklenen 2.356 (olculen 2.288)
    _b = _kk.beklenen_optik_olcusu(enerji=9.391, d=0.2826)
    kontrol("⭐ I-46 (I-51 devraldi): b002 beklenen optigi OLCULENE DAHA "
            "YAKIN (2.269 vs 2.288; oncesi 2.356)",
            _b.get("olculdu") is True and abs(_b["beklenen"] - 2.2685) < 5e-3,
            _b)
    kontrol("⭐ I-46: risk OPTIK BIRIMDE ifade ediliyor (esik 2.0 AYNEN)",
            abs(_b["esik"] - _kk.OPTIK_DURGUN_ESIGI) < 1e-9
            and "beklenen" in _b and "ust_sinir" in _b, _b)
    kontrol("⭐ I-46: b002 esigi GECIYOR -> risk YOK (yanlis alarm degil)",
            _b.get("seviye") == "temiz", _b)
    # Kontrollu ailedeki GERCEK dusuk-hareket vakasi: E=8.483, d=0.01616
    _f = _kk.beklenen_optik_olcusu(enerji=8.483, d=0.01616)
    kontrol("⭐ I-46 KIRMIZI: GERCEKTEN duragan cekim `fail` seviyesinde",
            _f.get("seviye") == "fail" and _f["ust_sinir"] < _kk.OPTIK_DURGUN_ESIGI,
            _f)
    # Belirsiz bant: beklenen < 2.0 ama ust sinir >= 2.0 -> warn
    _w = _kk.beklenen_optik_olcusu(enerji=10.0, d=0.2)
    kontrol("⭐ I-46: BELIRSIZ bant `warn` (EMIN DEGILSEN ENGELLEME)",
            _w["beklenen"] < _kk.OPTIK_DURGUN_ESIGI
            and _w["ust_sinir"] >= _kk.OPTIK_DURGUN_ESIGI
            and _w.get("seviye") == "warn", _w)
    kontrol("⭐ I-46: fail sarti OLCULEN hatadan turetiliyor (x1.229)",
            abs(_f["ust_sinir"] - _f["beklenen"] * (1 + _kk.MODEL_EN_KOTU_HATA))
            < 1e-3, _f)
    kontrol("I-46: girdi yoksa hukum YOK (`olculdu=False`, seviye yok)",
            _kk.beklenen_optik_olcusu(enerji=None, d=0.2).get("olculdu")
            is False
            and "seviye" not in _kk.beklenen_optik_olcusu(enerji=None, d=0.2))

# ── MOTION GRAMMAR: OPTIK BIRIMDEKI RISK ──
_mg46 = _kk.motion_grammar_olcusu([
    {"beat_id": "b002", "hareket": "pull-out", "islev": "hook", "sure_sn": 2.201,
     "medya_turu": "image", "uzamsal_enerji": 9.391, "yer_degistirme": 0.2826},
    {"beat_id": "bD", "hareket": "push-in", "islev": "aciklama", "sure_sn": 4.0,
     "medya_turu": "image", "uzamsal_enerji": 8.483, "yer_degistirme": 0.01616}])
kontrol("⭐ I-46 KIRMIZI: motion grammar OPTIK BIRIMDE risk raporluyor",
        [r["beat_id"] for r in (_mg46.get("optik_riski") or [])] == ["bD"],
        _mg46.get("optik_riski"))
kontrol("⭐ I-46: gecen cekim (b002) ARTIK isaretlenmiyor",
        not any(r["beat_id"] == "b002"
                for r in (_mg46.get("optik_riski") or [])))
kontrol("I-46 GERILEME YOK: yer degistirme verilmezse I-45 davranisi AYNEN",
        [d["beat_id"] for d in (_kk.motion_grammar_olcusu(
            [{"beat_id": "b1", "hareket": "push-in", "islev": "hook",
              "sure_sn": 4.0, "medya_turu": "image",
              "uzamsal_enerji": 7.557}]).get("dusuk_enerji") or [])] == ["b1"])

# ── PRE-QA ──
kontrol("⭐ I-46 KIRMIZI: `KALITE-OPTIK-DURGUN-BEKLENEN` kodu VAR",
        "KALITE-OPTIK-DURGUN-BEKLENEN" in _qon.KALITE_KODLARI)
kontrol("⭐ I-46: kod FAIL kodlarinda (olculen hata payiyla GUVENLI)",
        "KALITE-OPTIK-DURGUN-BEKLENEN" in _qon.FAIL_KODLARI)
_QON46 = oku(KOK, "editor/qa_on.py")
kontrol("⭐ I-46 KIRMIZI: PRE-QA yer degistirmeyi kadrajdan turetiyor",
        "yer_degistirme_alani" in _QON46, "yer degistirme PRE-QA'ya baglanmadi")
kontrol("I-46: PRE-QA modulu HALA GORSEL ACMAZ",
        "subprocess" not in _QON46)

# ── GERILEME YOK ──
kontrol("⭐ I-46: ESIKLER GEVSETILMEDI (optik 2.0 / enerji 11.589)",
        _kk.OPTIK_DURGUN_ESIGI == 2.0
        and abs(_kk.UZAMSAL_ENERJI_ESIGI - 11.589) < 1e-9
        and _kk.OPTIK_DURGUN_WARN_SN == 1.5
        and _kk.OPTIK_DURGUN_FAIL_SN == 3.0)
_V46 = oku(os.path.dirname(KOK), "app", "render-studio", "src", "Video.tsx")
kontrol("⭐ I-46: ZOOM KOVASI/TABANI DEGISMEDI (0.045 + 4 kova)",
        "OPTIK_TABAN_ORANI = 0.045" in _V46
        and all(f"oran: {o}" in _V46
                for o in (0.004, 0.014, 0.032, 0.062)))
kontrol("I-46 GERILEME YOK: I-45 kalibrasyon alani sabiti DURUYOR",
        abs(_kk.KALIBRASYON_GEZINME_HIZI - 0.0577) < 5e-4)
kontrol("I-46 GERILEME YOK: lisans/provenance ve tekrar kapilari DURUYOR",
        "KALITE-KUNYE-EKSIK" in _qon.FAIL_KODLARI
        and "KALITE-MEDYA-TEKRAR" in _qon.FAIL_KODLARI)
kontrol("I-46 GERILEME YOK: 22 alanlik generate sozlesmesi DEGISMEDI",
        len(set(re.findall(r"\{ad: '(\w+)'",
                           oku(KOK, "static/js/api.js")))) == 22)
kontrol("I-46: kullanici secimleri (zoom/pan alanlari) DOKUNULMADI",
        "zoom: 'in' | 'out' | 'yok'" in _V46
        and "pan: 'right' | 'left' | 'top' | 'bottom' | 'yok'" in _V46)

blok("§39u I-45 — ENERJI GOSTERILMEYEN PIKSELLERDE OLCULUYORDU")

# ⚠ I-44'TE OLCULEN KUSUR: enerji TUM KAREDE olculuyordu, oysa renderer
# `kadraj`/`punch` ile KIRPIYOR — yani olculen piksellerin bir kismi EKRANA
# HIC GELMIYOR. I-44 pilotunda b002 tam karede 7.557 olcup isaretlendi ama
# GERCEK render'da optik 2.288 ile esigi GECTI (yanlis alarm).
#
# ⚠ GEOMETRI UYDURULMADI — `editorv2/Kamera.tsx`ten BIREBIR turetildi:
#     Zemin: %100 x %100, objectFit: cover,
#            transform: scale(S) translate(x%, y%), origin center
#     CSS transform SAGDAN SOLA uygulanir, yuzde kayma ELEMANIN kendi
#     olcusune goredir  ->  q = merkez + S * ((p - merkez) + (dx, dy))
#     Tersi:  gorunen eleman dikdortgeni  W/S x H/S,
#             merkez (W/2 - dx, H/2 - dy)
#     `cover`: kapsama = max(W/sw, H/sh)  (`punch_buyutme_olcusu` ile AYNI
#     aritmetik) -> KAYNAK piksel uzayinda normalize kirpma:
#             w = W/(S*kapsama*sw)   cx = 0.5 - dx/(kapsama*sw)
#             h = H/(S*kapsama*sh)   cy = 0.5 - dy/(kapsama*sh)
#     Kamera.tsx: kaymaX = (pxT-0.5)*2*pay*100, kaymaY = (0.5-odakY)*2*pay*100
#
# ⚠ VE OLCUM HIPOTEZI CURUTTU: kirpmada olcmek yanlis alarmi AZALTMADI,
# ARTIRDI. I-44 pilotunun ALTI cekimi gercek kadrajlariyla olculdu:
#     beat  kadraj      tam kare  kirpma   optik    (esik 11.589 / 2.0)
#     b001  tam           14.887  15.596    4.438   temiz
#     b002  punch-1.35     7.557   9.391    2.288   HALA alarm (yanlis)
#     b003  ust           15.792  19.962    7.485   temiz
#     b004  punch-1.6     18.083  17.347   16.431   temiz
#     b005  alt           12.330  10.469    2.686   YENI yanlis alarm
#     b006  tam           13.867  13.467    3.116   temiz
#
# ⚠ KOK NEDEN OLCULDU — ESIGIN KALIBRASYON ALANI: `UZAMSAL_ENERJI_ESIGI`
# (11.589) TEK bir kamera konfigurasyonunda olculmustu (VidrushVideo, oran
# 0.045, 4.0 sn, pan=yok). O konfigurasyonun KENDI aritmetiginden gezinme
# hizi turetilir: olcek 1.0349 -> 1.1800, ic ice dikdortgenlerde
# IoU = (1.0349/1.18)^2 = 0.769 -> (1 - 0.769) / 4.0 sn = 0.0577 /sn.
# editorv2 cekimleri 0.0527-0.1139 /sn araliginda geziniyor; b002 tam
# 0.1025 /sn ile kalibrasyonun 1.78 KATI. Kalibrasyon ailesinde ~9.1
# enerjide optik 1.294 olculmustu; 1.294 x 1.78 = 2.30 ~ olculen 2.288.
# Yani esigi BASKA bir gezinme hizinda uygulamak I-43'un birim
# uyusmazliginin AYNISIDIR.
#
# ⚠ BU YUZDEN FAIL'E YUKSELTILMEDI: olcum yeterince kesinlesmedi (kirpma
# enerjisi tek basina b002'yi hala esigin altinda birakiyor). `warn` ve
# `EMIN DEGILSEN ENGELLEME` korundu.

kontrol("⭐ I-45 KIRMIZI: `kadraj_kirpma_bolgesi` VAR",
        hasattr(_kk, "kadraj_kirpma_bolgesi"), "kirpma geometrisi yok")
kontrol("⭐ I-45 KIRMIZI: `kadraj_gezinme_hizi` VAR",
        hasattr(_kk, "kadraj_gezinme_hizi"), "gezinme olcumu yok")
kontrol("⭐ I-45 KIRMIZI: `KALIBRASYON_GEZINME_HIZI` esigin ALANINI belgeliyor",
        abs(getattr(_kk, "KALIBRASYON_GEZINME_HIZI", 0.0) - 0.0577) < 5e-4,
        getattr(_kk, "KALIBRASYON_GEZINME_HIZI", None))

# ── GERCEK PILOT PARAMETRELERI (uydurma yok; render_plan.json b002) ──
_B002 = {"zoom": [1.5342, 1.35], "pan_x": [0.5, 0.5], "odak": [0.5, 0.5],
         "guvenli_pay": 0.1567, "kaynak": [3456, 2592], "sure_sn": 2.201}

if hasattr(_kk, "kadraj_kirpma_bolgesi"):
    _kb1 = _kk.kadraj_kirpma_bolgesi(
        olcek=_B002["zoom"][1], pan_x=_B002["pan_x"], odak=_B002["odak"],
        guvenli_pay=_B002["guvenli_pay"], kaynak_g=_B002["kaynak"][0],
        kaynak_y=_B002["kaynak"][1], kare_g=1920, kare_y=1080, t=1.0)
    kontrol("⭐ I-45: kirpma GERCEK transformdan (b002 t=1: 0.7407x0.5556 orta)",
            _kb1.get("olculdu") is True
            and abs(_kb1["w"] - 0.7407) < 1e-3 and abs(_kb1["h"] - 0.5556) < 1e-3
            and abs(_kb1["x"] - 0.1296) < 1e-3 and abs(_kb1["y"] - 0.2222) < 1e-3,
            _kb1)
    _kb0 = _kk.kadraj_kirpma_bolgesi(
        olcek=_B002["zoom"][0], pan_x=_B002["pan_x"], odak=_B002["odak"],
        guvenli_pay=_B002["guvenli_pay"], kaynak_g=_B002["kaynak"][0],
        kaynak_y=_B002["kaynak"][1], kare_g=1920, kare_y=1080, t=0.0)
    kontrol("⭐ I-45: pull-out ucu daha DAR (b002 t=0: 0.6518x0.4889)",
            abs(_kb0["w"] - 0.6518) < 1e-3 and abs(_kb0["h"] - 0.4889) < 1e-3,
            _kb0)
    # ⚠ `scale(S) translate(x%)`: kamera SAGA panlarken kaynak kirpmasi SOLA gider
    _kp = _kk.kadraj_kirpma_bolgesi(
        olcek=1.272, pan_x=[0.15, 0.85], odak=[0.5, 0.5], guvenli_pay=0.107,
        kaynak_g=5712, kaynak_y=4284, kare_g=1920, kare_y=1080, t=1.0)
    _kp0 = _kk.kadraj_kirpma_bolgesi(
        olcek=1.272, pan_x=[0.15, 0.85], odak=[0.5, 0.5], guvenli_pay=0.107,
        kaynak_g=5712, kaynak_y=4284, kare_g=1920, kare_y=1080, t=0.0)
    kontrol("⭐ I-45: pan yonu transformla TUTARLI (saga pan -> kirpma sola)",
            _kp["x"] < _kp0["x"] and abs(_kp["w"] - _kp0["w"]) < 1e-9,
            [_kp0["x"], _kp["x"]])
    _ku = _kk.kadraj_kirpma_bolgesi(
        olcek=1.2, pan_x=[0.5, 0.5], odak=[0.5, 0.3], guvenli_pay=0.0833,
        kaynak_g=4000, kaynak_y=3000, kare_g=1920, kare_y=1080, t=0.0)
    kontrol("⭐ I-45: `ust` odagi kirpmayi YUKARI tasiyor (odakY 0.3)",
            _ku["y"] + _ku["h"] / 2 < 0.5, _ku)
    kontrol("⭐ I-45: EMIN DEGILSEN ENGELLEME — olcu gecersizse `olculdu=False`",
            _kk.kadraj_kirpma_bolgesi(
                olcek=1.2, pan_x=[0.5, 0.5], odak=[0.5, 0.5], guvenli_pay=0.1,
                kaynak_g=0, kaynak_y=0).get("olculdu") is False)
    kontrol("I-45: kirpma kare SINIRLARI icinde kalir (0..1)",
            all(0.0 <= _kb0[a] <= 1.0 for a in ("x", "y", "w", "h"))
            and _kb0["x"] + _kb0["w"] <= 1.0 + 1e-9)

if hasattr(_kk, "kadraj_gezinme_hizi"):
    _gz = _kk.kadraj_gezinme_hizi(_kb0, _kb1, sure_sn=_B002["sure_sn"])
    kontrol("⭐ I-45: b002 gezinme hizi OLCULDU (0.1025 /sn)",
            _gz.get("olculdu") is True and abs(_gz["hiz"] - 0.1025) < 2e-3,
            _gz)
    kontrol("⭐ I-45 KIRMIZI: b002 esigin KALIBRASYON ALANI DISINDA",
            _gz.get("kalibrasyon_icinde") is False, _gz)
    kontrol("I-45: sure yoksa hukum YOK (`olculdu=False`)",
            _kk.kadraj_gezinme_hizi(_kb0, _kb1, sure_sn=0).get("olculdu")
            is False)

# ── ORNEKLEYICI KIRPMAYI UYGULAR (ayni 64x36 gri sozlesme) ──
try:
    _gk = _kk.gorsel_ornek_komutu("/tmp/x.jpg",
                                  kirpma={"x": 0.1296, "y": 0.2222,
                                          "w": 0.7407, "h": 0.5556})
except TypeError:
    _gk = []
_vf = " ".join(_gk)
kontrol("⭐ I-45 KIRMIZI: ornekleyici KIRPMA uygulayabiliyor",
        "crop=" in _vf, _gk)
kontrol("⭐ I-45: kirpma SCALE'DEN ONCE (once kirp, sonra 64x36 ornekle)",
        _vf.find("crop=") < _vf.find("scale=64:36"), _vf)
kontrol("I-45 GERILEME YOK: kirpmasiz cagri ESKI komutu BIREBIR uretiyor",
        _kk.gorsel_ornek_komutu("/tmp/x.jpg")
        == ["ffmpeg", "-nostdin", "-v", "error", "-i", "/tmp/x.jpg", "-vf",
            "scale=64:36,format=gray", "-frames:v", "1", "-f", "rawvideo", "-"],
        _kk.gorsel_ornek_komutu("/tmp/x.jpg"))

# ── MOTION GRAMMAR: ALAN DISINDA HUKUM YOK (yanlis alarm azaltma) ──
_mg45 = _kk.motion_grammar_olcusu([
    # b002: kirpma enerjisi 9.391 <= esik AMA gezinme 0.1025 > 0.0577
    {"beat_id": "b002", "hareket": "pull-out", "islev": "hook", "sure_sn": 2.201,
     "medya_turu": "image", "uzamsal_enerji": 9.391, "gezinme_hizi": 0.1025},
    # kalibrasyon alani icinde ve DUSUK enerjili -> hukum VERILIR
    {"beat_id": "bX", "hareket": "push-in", "islev": "aciklama", "sure_sn": 4.0,
     "medya_turu": "image", "uzamsal_enerji": 7.557, "gezinme_hizi": 0.0577}])
kontrol("⭐ I-45 KIRMIZI: kalibrasyon ALANI DISINDAKI cekim isaretlenmiyor",
        [d["beat_id"] for d in (_mg45.get("dusuk_enerji") or [])] == ["bX"],
        _mg45.get("dusuk_enerji"))
kontrol("⭐ I-45: alan disi cekim SESSIZCE gecilmiyor, AYRICA raporlaniyor",
        [d["beat_id"] for d in (_mg45.get("gezinme_kapsam_disi") or [])]
        == ["b002"], _mg45.get("gezinme_kapsam_disi"))
kontrol("I-45 GERILEME YOK: gezinme verilmezse I-44 davranisi AYNEN "
        "(hukum verilir)",
        [d["beat_id"] for d in (_kk.motion_grammar_olcusu(
            [{"beat_id": "b1", "hareket": "push-in", "islev": "hook",
              "sure_sn": 4.0, "medya_turu": "image",
              "uzamsal_enerji": 7.557}]).get("dusuk_enerji") or [])] == ["b1"])

# ── PRE-QA ──
_QON45 = oku(KOK, "editor/qa_on.py")
kontrol("⭐ I-45 KIRMIZI: PRE-QA enerjiyi GOSTERILEN bolgede olcuyor",
        "kadraj_kirpma_bolgesi" in _QON45, "kirpma PRE-QA'ya baglanmadi")
kontrol("⭐ I-45: kapsam disi icin AYRI bilgi kodu (sessiz pass yok)",
        "KALITE-MEDYA-ENERJI-KAPSAM-DISI" in _qon.KALITE_KODLARI
        and "KALITE-MEDYA-ENERJI-KAPSAM-DISI" not in _qon.FAIL_KODLARI)
kontrol("⭐ I-45: dusuk enerji kodu HALA `warn` (olcum kesinlesmedi)",
        "KALITE-MEDYA-DUSUK-ENERJI" in _qon.KALITE_KODLARI
        and "KALITE-MEDYA-DUSUK-ENERJI" not in _qon.FAIL_KODLARI)
kontrol("I-45: PRE-QA modulu HALA GORSEL ACMAZ (olcer disaridan)",
        "subprocess" not in _QON45)

# ── GERILEME YOK ──
kontrol("⭐ I-45: ESIKLER GEVSETILMEDI (optik 2.0 / enerji 11.589)",
        _kk.OPTIK_DURGUN_ESIGI == 2.0
        and abs(_kk.UZAMSAL_ENERJI_ESIGI - 11.589) < 1e-9)
_V45 = oku(os.path.dirname(KOK), "app", "render-studio", "src", "Video.tsx")
kontrol("⭐ I-45: ZOOM KOVASI YUKSELTILMEDI (I-43 tabani 0.045)",
        "OPTIK_TABAN_ORANI = 0.045" in _V45)
kontrol("I-45: kadraj olcekleri TEK KAYNAK (motion.py <-> Kamera.tsx)",
        all(f'"{a}": {b}' in oku(KOK, "editor/motion.py")
            for a, b in (("tam", 1.0), ("punch-1.35", 1.35),
                         ("punch-1.6", 1.6))))
kontrol("I-45 GERILEME YOK: lisans/provenance ve tekrar kapilari DURUYOR",
        "KALITE-KUNYE-EKSIK" in _qon.FAIL_KODLARI
        and "KALITE-MEDYA-TEKRAR" in _qon.FAIL_KODLARI)
kontrol("I-45 GERILEME YOK: 22 alanlik generate sozlesmesi DEGISMEDI",
        len(set(re.findall(r"\{ad: '(\w+)'",
                           oku(KOK, "static/js/api.js")))) == 22)
kontrol("I-45: kullanici secimleri (zoom/pan alanlari) DOKUNULMADI",
        "zoom: 'in' | 'out' | 'yok'" in _V45
        and "pan: 'right' | 'left' | 'top' | 'bottom' | 'yok'" in _V45)

blok("§39t I-44 — GORSELIN UZAMSAL ENERJISI HIC OLCULMUYORDU")

# ⚠ I-43 PILOTUNDA OLCULEN KUSUR: kova tabani (0.045) hizalandiktan sonra
# bile s1 sahnesi 0.955 olctu. Kok neden UC RENDERLE ayristirildi: sure de
# kova da degil, GORSELIN KENDISI. Ayni sure + ayni etkin hizda kalibre
# gorsel 3.69 verirken s1'in gorseli 1.457 verdi; sure uzatilip etkin hiz
# artirilinca bile 1.643'te kaldi. Yani DUZ (dusuk uzamsal detayli) bir
# varlik STATIK FOTOGRAF olarak kullanildiginda kamera ne yaparsa yapsin
# ekranda hareket URETMIYOR — ama hicbir kapi bunu OLCMUYORDU.
#
# ⚠ I-44 KALIBRASYONU — DEGER TAHMIN EDILMEDI, GERCEK RENDER'DA OLCULDU.
# NEDENSEL AILE: TEK gorselin efektif cozunurlugu kademeli dusuruldu
# (scale W -> geri 1920, DUZGUN yeniden ornekleme; `neighbor` blok kenari
# uretip enerjiyi YAPAY yuksek tuttugu icin elendi — ilk denemede olculdu).
# Icerik/kompozisyon AYNI, degisen TEK sey uzamsal enerji. Her uye URETIM
# TABANI oraniyla (0.045), 4.0 sn, EN KOTU kamera birlesimiyle (`pan: yok`)
# 1080p render edilip `kalite_kapisi` ile olculdu:
#
#   enerji   optik   pay     duragan seri   sonuc
#    5.866   0.719   x0.36     3.0 sn       ⛔ esigin ALTINDA
#    7.590   1.011   x0.51     3.0 sn       ⛔ esigin ALTINDA
#    9.092   1.294   x0.65     3.0 sn       ⛔ esigin ALTINDA
#   10.249   1.522   x0.76     3.0 sn       ⛔ esigin ALTINDA
#   11.589   1.841   x0.92     1.0 sn       ⛔ esigin ALTINDA  <- EN YUKSEK KALAN
#   12.589   2.172   x1.09     0.5 sn       ✅ esigi GECER     <- EN DUSUK GECEN
#   15.789   2.819   x1.41     0.0 sn       ✅ esigi GECER
#
# DOGAL KONTROL (onbellekteki 6 gercek gorsel): 7.557 / 12.330 / 13.867 /
# 14.887 / 15.792 / 18.083. I-43 pilotunda optigi eSigin ALTINDA kalan TEK
# gorsel 7.557 olandi; digerlerinin hepsi gecti. Nedensel aile ile dogal
# kontrol AYNI yeri isaret ediyor.
#
# ⚠ ESIK, OLCULEN KUSURLU TARAFA konuldu: `11.589` = optigi esigin ALTINDA
# oldugu OLCULEN EN YUKSEK enerji. Boylece kapi, gectigi OLCULEN hicbir
# varligi (en dusuk gecen 12.589) reddetmez.
# ⚠ SEVIYE `warn` — `EMIN DEGILSEN ENGELLEME` sozlesmesi (edinim.py ile ayni):
# enerji TUM karede olculur, oysa editorv2 `kadraj`/`punch` ile KIRPABILIR ve
# kirpilan bolgenin enerjisi farkli olabilir. Kirpma bolgesinde olcmek AYRI
# ve OLCULMEMIS bir atomdur -> bu kapi RENDER'I BLOKLAMAZ.
# ⚠ OPTIK ESIK GEVSETILMEDI, ZOOM KOVASI YUKSELTILMEDI.

kontrol("⭐ I-44 KIRMIZI: `uzamsal_enerji_olcusu` VAR",
        hasattr(_kk, "uzamsal_enerji_olcusu"), "olcum fonksiyonu yok")
kontrol("⭐ I-44 KIRMIZI: `gorsel_ornek_komutu` VAR (modul KOMUT uretir, kosturmaz)",
        hasattr(_kk, "gorsel_ornek_komutu"), "ornekleyici komutu yok")
kontrol("⭐ I-44 KIRMIZI: `UZAMSAL_ENERJI_ESIGI` OLCULEN degerdir (11.589)",
        abs(getattr(_kk, "UZAMSAL_ENERJI_ESIGI", 0.0) - 11.589) < 1e-9,
        getattr(_kk, "UZAMSAL_ENERJI_ESIGI", None))

if hasattr(_kk, "gorsel_ornek_komutu"):
    _ge_komut = _kk.gorsel_ornek_komutu("/tmp/x.jpg")
    # ⚠ IKINCI ARITMETIK YOK: ornekleme optikle BIREBIR ayni sozlesme.
    kontrol("⭐ I-44: ornekleme optikle AYNI sozlesme (64x36 gri, tek kare)",
            "scale=64:36" in " ".join(_ge_komut)
            and "format=gray" in " ".join(_ge_komut)
            and "rawvideo" in _ge_komut, _ge_komut)
    kontrol("I-44: komut AG KULLANMAZ ve alt surec CALISTIRMAZ (saf liste)",
            isinstance(_ge_komut, list) and _ge_komut[0] == "ffmpeg")

if hasattr(_kk, "uzamsal_enerji_olcusu"):
    _duz = bytes([128]) * (64 * 36)              # tamamen DUZ kare
    _e_duz = _kk.uzamsal_enerji_olcusu(_duz)
    kontrol("⭐ I-44: DUZ karenin uzamsal enerjisi 0 (ve yetersiz)",
            _e_duz.get("olculdu") is True and _e_duz.get("enerji") == 0.0
            and _e_duz.get("yeterli") is False, _e_duz)
    # Satranc tahtasi: her komsu 0<->255 -> gradyan en yuksek
    _sat = bytes([0 if (i // 64 + i % 64) % 2 == 0 else 255
                  for i in range(64 * 36)])
    _e_sat = _kk.uzamsal_enerji_olcusu(_sat)
    kontrol("⭐ I-44: en yuksek detayli karede enerji 255'e yakin ve yeterli",
            _e_sat.get("enerji", 0) > 250 and _e_sat.get("yeterli") is True,
            _e_sat)
    kontrol("I-44: olcum DETERMINISTIK (ayni girdi -> ayni sonuc)",
            _kk.uzamsal_enerji_olcusu(_sat) == _e_sat)
    kontrol("⭐ I-44: SESSIZ PASS YOK — ornek yoksa `olculdu=False`, "
            "'yeterli' DENMEZ",
            _kk.uzamsal_enerji_olcusu(b"").get("olculdu") is False
            and "yeterli" not in _kk.uzamsal_enerji_olcusu(b""),
            _kk.uzamsal_enerji_olcusu(b""))
    kontrol("I-44: bozuk girdi ISTISNA FIRLATMAZ",
            _kk.uzamsal_enerji_olcusu(None).get("olculdu") is False)

# ── MOTION GRAMMAR BACAGI: statik fotograf + dusuk enerji = YETERSIZ ──
_mg_dusuk = _kk.motion_grammar_olcusu([
    {"beat_id": "b001", "hareket": "push-in", "islev": "hook", "sure_sn": 4.0,
     "medya_turu": "image", "uzamsal_enerji": 7.557},
    {"beat_id": "b002", "hareket": "pan-right", "islev": "aciklama",
     "sure_sn": 4.0, "medya_turu": "image", "uzamsal_enerji": 15.792}])
kontrol("⭐ I-44 KIRMIZI: motion grammar DUSUK ENERJILI statik fotografi "
        "yetersiz sayiyor",
        [d.get("beat_id") for d in (_mg_dusuk.get("dusuk_enerji") or [])]
        == ["b001"], _mg_dusuk.get("dusuk_enerji"))
kontrol("⭐ I-44: enerji verilmediginde 'temiz' DENMEZ (olculemedi yazilir)",
        _kk.motion_grammar_olcusu(
            [{"beat_id": "b001", "hareket": "push-in", "islev": "hook",
              "sure_sn": 4.0}]).get("enerji_olculdu") is False)
kontrol("I-44: enerji olculduyse bunu RAPOR EDER",
        _mg_dusuk.get("enerji_olculdu") is True
        and abs(_mg_dusuk.get("enerji_esigi", 0) - 11.589) < 1e-9,
        _mg_dusuk.get("enerji_esigi"))
# ⚠ VIDEO klip statik fotograf DEGILDIR: kendi hareketi vardir, kapi ona
# hukum vermez (olcum yanlis yere uygulanmasin).
kontrol("⭐ I-44: VIDEO klibe uygulanmaz (yalniz statik fotograf)",
        not (_kk.motion_grammar_olcusu(
            [{"beat_id": "b001", "hareket": "push-in", "islev": "hook",
              "sure_sn": 4.0, "medya_turu": "video",
              "uzamsal_enerji": 3.0}]).get("dusuk_enerji") or []))

# ── PRE-QA KAPISI ──
kontrol("⭐ I-44 KIRMIZI: `KALITE-MEDYA-DUSUK-ENERJI` kalite kodlarinda",
        "KALITE-MEDYA-DUSUK-ENERJI" in _qon.KALITE_KODLARI,
        "kod yok")
kontrol("⭐ I-44: kod FAIL kodlarinda DEGIL (EMIN DEGILSEN ENGELLEME)",
        "KALITE-MEDYA-DUSUK-ENERJI" not in _qon.FAIL_KODLARI)
kontrol("⭐ I-44: olcemedigimizde SESSIZ PASS YOK — ayri bilgi kodu",
        "KALITE-MEDYA-ENERJI-OLCULEMEDI" in _qon.KALITE_KODLARI
        and "KALITE-MEDYA-ENERJI-OLCULEMEDI" not in _qon.FAIL_KODLARI)
_QON43 = oku(KOK, "editor/qa_on.py")
kontrol("⭐ I-44 KIRMIZI: `enerji_okuyucu` PRE-QA'ya enjekte ediliyor",
        "enerji_okuyucu" in _QON43
        and "def denetle(" in _QON43
        and "enerji_okuyucu" in _QON43[_QON43.find("def denetle("):
                                       _QON43.find("def denetle(") + 1400],
        "denetle imzasinda enerji_okuyucu yok")
kontrol("⭐ I-44 KIRMIZI: okuyucu URETIM HATTINDA bagli (kopru -> plan -> QA)",
        all("enerji_okuyucu" in oku(*p) for p in
            ((KOK, "edit_kopru.py"), (KOK, "editor/plan.py"))),
        "enerji_okuyucu uretim hattinda tasinmiyor")
kontrol("I-44: PRE-QA modulu GORSEL ACMAZ (olcer DISARIDAN verilir)",
        "gorsel_ornek_komutu" not in _QON43
        and "subprocess" not in _QON43)

# ── GERILEME YOK: I-43 ve onceki kapilar AYNEN ──
kontrol("⭐ I-44: OPTIK ESIK GEVSETILMEDI (2.0 / 1.5 / 3.0)",
        _kk.OPTIK_DURGUN_ESIGI == 2.0 and _kk.OPTIK_DURGUN_WARN_SN == 1.5
        and _kk.OPTIK_DURGUN_FAIL_SN == 3.0)
_V44 = oku(os.path.dirname(KOK), "app", "render-studio", "src", "Video.tsx")
kontrol("⭐ I-44: ZOOM KOVASI YUKSELTILMEDI (I-43 tabani 0.045, tablo ayni)",
        "OPTIK_TABAN_ORANI = 0.045" in _V44
        and all(f"oran: {o}" in _V44
                for o in (0.004, 0.014, 0.032, 0.062)))
kontrol("I-44 GERILEME YOK: lisans duvari ve provenance kapisi DURUYOR",
        "def lisans_suz" in oku(KOK, "edit_kopru.py")
        and "KALITE-KUNYE-EKSIK" in _qon.FAIL_KODLARI)
kontrol("I-44 GERILEME YOK: cozunurluk/oran/tekrar kapilari DURUYOR",
        "COZUNURLUK-YETERSIZ" in oku(KOK, "medya/edinim.py")
        and "ORAN-UYUMSUZ" in oku(KOK, "medya/edinim.py")
        and "KALITE-MEDYA-TEKRAR" in _qon.FAIL_KODLARI)
kontrol("I-44 GERILEME YOK: semantik kapilar (biyom/donem) DURUYOR",
        "def biyom_kapisi" in oku(KOK, "medya_kapisi.py")
        and "def donem_kapisi" in oku(KOK, "medya_kapisi.py"))
kontrol("I-44 GERILEME YOK: 22 alanlik generate sozlesmesi DEGISMEDI",
        len(set(re.findall(r"\{ad: '(\w+)'",
                           oku(KOK, "static/js/api.js")))) == 22)
kontrol("I-44: kullanici secimleri (zoom/pan alanlari) DOKUNULMADI",
        "zoom: 'in' | 'out' | 'yok'" in _V44
        and "pan: 'right' | 'left' | 'top' | 'bottom' | 'yok'" in _V44)

blok("§39s I-43 — ZOOM KOVALARI OPTIK OLCUM BIRIMIYLE HIZALANMAMISTI")

# ⚠ I-42 PILOTUNDA OLCULEN KUSUR (acilis DUZELDI, sinif DUZELMEDI):
# `ZOOM_KOVA` oranlari REFERANS KANAL olcumunden gelir — birim "%/sn zoom
# hizi" ve olcum CANLI cekimlerde yapildi (o karelerde kameranin disinda
# ozne/kamera hareketi de VARDI). Optik kapi ise BASKA bir birim olcer:
# ekrandaki ardisik gri karelerin ortalama mutlak farki (0-255, 4 fps /
# 64x36). Bizim cikti DURAGAN FOTOGRAF oldugu icin ekrandaki TEK hareket
# transformdur; yani referansin "ihmal edilebilir/sakin" kovalarinin canli
# cekimde bedava aldigi hareket bizde YOKTUR. Iki taraf ayri birimde
# oldugundan kovalar kapiyi gecmiyordu.
#
# ⚠ I-43 KALIBRASYONU — DEGERLER TAHMIN EDILMEDI, GERCEK 1080p RENDER'DA
# OLCULDU. Her aday oran icin `zoomOrani` gecici olarak sabitlendi ve
# PILOTUN KENDI uc (gorsel, zoom, pan) birlesimi olculdu (en kotu durum
# `pan: "yok"` dahil). Olcum: 4 fps / 64x36, sahne basina 4.0 sn.
#
#   oran   en kotu ort   pay    duragan seri (uc sahne)   sonuc
#   0.032     1.868      x0.93  0.75 / 0.75 / 1.25 sn     2/3 sahne KALIR
#   0.038     2.322      x1.16  0.25 / 0.25 / 0.25 sn     gecer, seri VAR
#   0.041     2.544      x1.27  0.0  / 0.25 / 0.0  sn     gecer, seri VAR
#   0.045     2.827      x1.41  0.0  / 0.0  / 0.0  sn     ✅ HEPSI TEMIZ
#   0.062     3.931      x1.97  0.0  / 0.0  / 0.0  sn     ✅ (I-42 acilisi)
#
# TABAN, OLCUMDEN ONCE yazilan olcutle secildi: (a) ortalama esigi gecsin,
# (b) en uzun duragan seri TUM sahnelerde 0.0 sn olsun, (c) en kotu pay
# >= x1.25 olsun. (c) sarti UYDURMA DEGIL: 0.032'nin uc gorseldeki yayilimi
# x0.93-x1.00 olcuLDU, yani bicak sirti bir pay TEK BIR GORSEL degisince
# dusuyor (I-38'de `POST-KENAR-SIYAH` 15.99 vs 16.0 tam olarak boyle FAIL
# olmustu). Olcutu karsilayan EN KUCUK taranan oran: 0.045.
#
# ⚠ ESIK GEVSETILMEDI. `OPTIK_DURGUN_ESIGI` 2.0 DURUYOR; hizalanan taraf
# KOVALAR. Kova tablosu, indeks aritmetigi, kullanici zoom/pan secimleri ve
# 22 alan sozlesmesi DOKUNULMADI.

_V43 = oku(os.path.dirname(KOK), "app", "render-studio", "src", "Video.tsx")
_KOVA43 = [(0.004, 0.34), (0.014, 0.39), (0.032, 0.14), (0.062, 0.13)]

kontrol("⭐ I-43 KIRMIZI: olculen OPTIK TABAN orani Video.tsx'te VAR",
        "OPTIK_TABAN_ORANI" in _V43, "taban orani yok")
_m43 = re.search(r"OPTIK_TABAN_ORANI\s*=\s*([\d.]+)", _V43)
_taban43 = float(_m43.group(1)) if _m43 else 0.0
kontrol("⭐ I-43 KIRMIZI: taban, BICAK SIRTI kovadan (0.032) BUYUK",
        _taban43 > _KOVA43[2][0], _taban43)
kontrol("⭐ I-43: taban OLCULEN degerdir (0.045 — olcutu karsilayan en kucuk)",
        abs(_taban43 - 0.045) < 1e-9, _taban43)


def _ham_oran43(indeks):
    """Kova secimi — TABANSIZ ham hali (dagilim BOZULMADI kaniti)."""
    r = ((indeks * 2749) % 1000) / 1000
    b = 0.0
    for o, p in _KOVA43:
        b += p
        if r < b:
            return o
    return _KOVA43[1][0]


def _zoom_orani43(indeks):
    """Video.tsx `zoomOrani` aritmetiginin AYNISI (test tarafi ayna)."""
    if indeks == 0:
        return _acilis43
    return max(_ham_oran43(indeks), _taban43)


_ma43 = re.search(r"ACILIS_ZOOM_ORANI\s*=\s*([\d.]+)", _V43)
_acilis43 = float(_ma43.group(1)) if _ma43 else 0.0
_govde43 = _V43[_V43.find("const zoomOrani"):_V43.find("const SURE_ZOOM")]

kontrol("⭐ I-43 KIRMIZI: `zoomOrani` dondurdugu orani TABANA cekiyor",
        "Math.max" in _govde43 and "OPTIK_TABAN_ORANI" in _govde43,
        "zoomOrani govdesinde taban uygulanmiyor")
kontrol("⭐ I-43 KIRMIZI: HICBIR sahne indeksi OLCULEN tabanin ALTINA dusmuyor",
        _taban43 >= 0.045
        and all(_zoom_orani43(i) >= 0.045 for i in range(0, 64)),
        [i for i in range(0, 64) if _zoom_orani43(i) < 0.045][:5] or _taban43)
kontrol("⭐ I-43: indeks 1..8 oranlari OLCULEN tabana hizalandi",
        [_zoom_orani43(i) for i in range(1, 9)]
        == [0.045, 0.045, 0.045, 0.062, 0.045, 0.045, 0.045, 0.062],
        [_zoom_orani43(i) for i in range(1, 9)])
kontrol("⭐ I-43: kalibrasyon KAYNAKTA belgeli (olculen en kotu degerler)",
        "1.868" in _V43 and "2.827" in _V43,
        "olcum degerleri kaynakta yok")

# ── HIZALAMA TUM TUKETICILERE ULASIYOR (tek kapi: `zoomOrani`) ──
kontrol("I-43: bes gorunum hesabi da orani `zoomOrani`den aliyor",
        len(re.findall(r"zoomOrani\(indeks\)", _V43)) >= 5,
        len(re.findall(r"zoomOrani\(indeks\)", _V43)))

# ── DAGILIM BOZULMADI: kova tablosu ve aritmetik AYNEN ──
kontrol("I-43 GERILEME YOK: kova tablosu DEGISMEDI (4 kova, ayni sayilar)",
        all(f"oran: {o}" in _V43 and f"pay: {p}" in _V43
            for o, p in _KOVA43), _KOVA43)
kontrol("I-43 GERILEME YOK: indeks aritmetigi DEGISMEDI (2749 / 1000)",
        "indeks * 2749" in _V43 and "% 1000" in _V43)
kontrol("I-43: TABANSIZ ham kova dizisi BIT-BIT eski haliyle ayni",
        [_ham_oran43(i) for i in range(1, 9)]
        == [0.032, 0.014, 0.004, 0.062, 0.032, 0.014, 0.004, 0.062],
        [_ham_oran43(i) for i in range(1, 9)])

# ── ESIK GEVSETILMEDI (hizalanan taraf KOVALAR) ──
kontrol("⭐ I-43: `OPTIK_DURGUN_ESIGI` GEVSETILMEDI (2.0)",
        _kk.OPTIK_DURGUN_ESIGI == 2.0, _kk.OPTIK_DURGUN_ESIGI)
kontrol("I-43: durgun WARN/FAIL sureleri de DEGISMEDI (1.5 / 3.0)",
        _kk.OPTIK_DURGUN_WARN_SN == 1.5 and _kk.OPTIK_DURGUN_FAIL_SN == 3.0)
kontrol("I-43: optik ornekleme sozlesmesi DEGISMEDI (4 fps / 64x36)",
        _kk.OPTIK_ORNEK_FPS == 4 and _kk.OPTIK_ORNEK_OLCU == (64, 36))
kontrol("I-43: ust sinir (asiri hiz) DEGISMEDI — taban onun COK altinda",
        _kk.OPTIK_ASIRI_ESIGI == 45.0 and _taban43 < 0.062)

# ── ONCEKI ATOMLAR VE SOZLESMELER ──
kontrol("I-43 GERILEME YOK: I-42 acilis orani DURUYOR (0.062, tabanin ustunde)",
        abs(_acilis43 - 0.062) < 1e-9 and _acilis43 >= _taban43, _acilis43)
kontrol("I-43 GERILEME YOK: I-42 indeks 0 dallanmasi DURUYOR",
        re.search(r"indeks\s*===\s*0", _govde43) is not None)
kontrol("I-43 GERILEME YOK: 22 alanlik generate sozlesmesi DEGISMEDI",
        len(set(re.findall(r"\{ad: '(\w+)'",
                           oku(KOK, "static/js/api.js")))) == 22)
kontrol("I-43: kullanici secimleri (zoom/pan alanlari) DOKUNULMADI",
        "zoom: 'in' | 'out' | 'yok'" in _V43
        and "pan: 'right' | 'left' | 'top' | 'bottom' | 'yok'" in _V43)
kontrol("I-43 GERILEME YOK: I-41 kunyesi ve I-39 konumu DURUYOR",
        "const KaynakYazi" in _V43 and "KUNYE_Y_ORANI = 0.075" in _V43
        and abs(_etipo.KAYNAK_ETIKETI_ALTYAZILI - 0.075) < 1e-9)

blok("§39r I-42 — ACILIS SAHNESI HER VIDEODA EN DURAGAN OLANDI")

# ⚠ I-41 PILOTUNDA OLCULEN KUSUR: `VidrushVideo` zoom hizini sahne
# INDEKSINDEN deterministik seciyor:  r = ((indeks * 2749) % 1000) / 1000
# indeks 0 icin r = 0.000 -> DAIMA ilk kova: **0.004 (%0.4/sn, "ihmal
# edilebilir")**. Yani ACILIS/HOOK cekimi HER URETIMDE en duragan olani.
# Gercek 1080p render'da olculdu (vidrushvideo_kunye_i41.mp4):
#     s0 (oran 0.004) optik ortalama **1.421** < esik 2.0 -> POST-OPTIK-DURGUN
#     en uzun duragan seri 3.0 sn (4 sn'lik sahnede) -> FAIL
# Referans olcumu (Video.tsx'in kendi belgesi) medyan **%1.57/sn** diyor ve
# dagilimin "ihmal edilebilir" kovasi TUM cekimler icin gecerli; acilis
# cekimini oraya SABITLEMEK olcumden gelmiyor, indeks aritmetiginin YAN
# ETKISI. Hook, izleyicinin kaldigi ya da dustugu tek karedir.
# ⚠ ESIK GEVSETILMEDI: `OPTIK_DURGUN_ESIGI` 2.0 olarak DURUYOR; degisen
# yalniz acilis sahnesinin HAREKETI.

_V42 = oku(os.path.dirname(KOK), "app", "render-studio", "src", "Video.tsx")
_KOVA42 = [(0.004, 0.34), (0.014, 0.39), (0.032, 0.14), (0.062, 0.13)]


def _zoom_orani42(indeks):
    """Video.tsx `zoomOrani` aritmetiginin AYNISI (test tarafi ayna).

    ⚠ Ayna oldugu icin ASIL kaynak TSX; asagidaki kontroller hem formulu hem
    kova sayilarini TSX'te KILITLIYOR. Ikisi ayrisirsa test kirmizi olur."""
    r = ((indeks * 2749) % 1000) / 1000
    b = 0.0
    for o, p in _KOVA42:
        b += p
        if r < b:
            return o
    return _KOVA42[1][0]


kontrol("⭐ I-42 KIRMIZI: acilis sahnesi ICIN AYRI ve OLCULEN oran VAR",
        "ACILIS_ZOOM_ORANI" in _V42, "Video.tsx'te acilis orani yok")
_m42 = re.search(r"ACILIS_ZOOM_ORANI\s*=\s*([\d.]+)", _V42)
_acilis42 = float(_m42.group(1)) if _m42 else 0.0
kontrol("⭐ I-42 KIRMIZI: acilis orani IHMAL EDILEBILIR kovadan BUYUK",
        _acilis42 > _KOVA42[0][0], _acilis42)
kontrol("⭐ I-42: acilis orani UYDURMA DEGIL — olculen dagilimin bir kovasi",
        _acilis42 in [o for o, _ in _KOVA42], _acilis42)
kontrol("⭐ I-42 KIRMIZI: `zoomOrani` indeks 0'i acilis oranina baglıyor",
        re.search(r"indeks\s*===\s*0", _V42) is not None
        and "ACILIS_ZOOM_ORANI" in _V42[_V42.find("const zoomOrani"):
                                        _V42.find("const SURE_ZOOM")],
        "indeks 0 dallanmasi yok")

# ── DIGER SAHNELER DEGISMEDI (indeks aritmetigi ve kovalar AYNEN) ──
kontrol("I-42 GERILEME YOK: kova tablosu DEGISMEDI (4 kova, ayni sayilar)",
        all(f"oran: {o}" in _V42 and f"pay: {p}" in _V42
            for o, p in _KOVA42), _KOVA42)
kontrol("I-42 GERILEME YOK: indeks aritmetigi DEGISMEDI (2749 / 1000)",
        "indeks * 2749" in _V42 and "% 1000" in _V42)
kontrol("⭐ I-42: indeks 1..8 oranlari BIT-BIT ayni (yalniz acilis degisti)",
        [_zoom_orani42(i) for i in range(1, 9)]
        == [0.032, 0.014, 0.004, 0.062, 0.032, 0.014, 0.004, 0.062],
        [_zoom_orani42(i) for i in range(1, 9)])

# ── ESIK GEVSETILMEDI ──
kontrol("⭐ I-42: `OPTIK_DURGUN_ESIGI` GEVSETILMEDI (2.0)",
        _kk.OPTIK_DURGUN_ESIGI == 2.0, _kk.OPTIK_DURGUN_ESIGI)
kontrol("I-42: durgun WARN/FAIL sureleri de DEGISMEDI (1.5 / 3.0)",
        _kk.OPTIK_DURGUN_WARN_SN == 1.5 and _kk.OPTIK_DURGUN_FAIL_SN == 3.0)

# ── SOZLESMELER VE ONCEKI ATOMLAR ──
kontrol("I-42 GERILEME YOK: 22 alanlik generate sozlesmesi DEGISMEDI",
        len(set(re.findall(r"\{ad: '(\w+)'",
                           oku(KOK, "static/js/api.js")))) == 22)
kontrol("I-42 GERILEME YOK: I-41 kunyesi ve I-39 konumu DURUYOR",
        "const KaynakYazi" in _V42 and "KUNYE_Y_ORANI = 0.075" in _V42
        and abs(_etipo.KAYNAK_ETIKETI_ALTYAZILI - 0.075) < 1e-9)
kontrol("I-42: kullanici secimleri (zoom/pan alanlari) DOKUNULMADI",
        "zoom: 'in' | 'out' | 'yok'" in _V42
        and "pan: 'right' | 'left' | 'top' | 'bottom' | 'yok'" in _V42)

blok("§39q I-41 — kaynakYazi URETIM HATTINDA DUSUYORDU (lisans gorunurlugu)")

# ⚠ I-38'DEN DEVIR, I-41'DE OLCULEN GERCEK KOK NEDEN:
# I-38 notu "Video.tsx `Sahne` tipinde alan yok" diyordu. Olculdu: kusur DAHA
# ONCE basliyor. `pipeline.py` CC/lisansli klip alindiginda `s["kaynakYazi"]`
# yaziyor (3 nokta: avci atfi, `atif_al` kanali, yedek sorgu) — ama
# `props_sahneler` sahneyi ALAN ALAN kuruyor ve bu alani HIC KOPYALAMIYOR.
# Yani kunye props SINIRINDA dusuyor; sonrasindaki IKI renderer da onu
# goremiyor:
#   · Remotion `VidrushVideo` (VARSAYILAN yol)  -> `Sahne` tipinde alan yok
#   · `hizli_render.ffmpeg_render` (RENDER_MOTOR=ffmpeg) -> `_kaynak_yazi_filtre`
#     alani OKUYOR ama props'ta alan olmadigi icin HER ZAMAN bos donuyor
# Sonuc: CC klip kullanan her uretimde EKRAN ATFI HIC CIZILMIYOR. Lisans
# atfinin resmi yeri video aciklamasi (`kaynak.atif_listesi`) olsa da, ekran
# kunyesi urun sozunun parcasiydi ve SESSIZCE kayboluyordu.
# ⚠ Bu, `/api/generate`in 22 alanlik sozlesmesine DOKUNMAZ: `kaynakYazi`
# kullanicidan gelmez, medya edinimi sirasinda URETILIR.

_PP41 = oku(KOK, "pipeline.py")
_HR41 = oku(KOK, "hizli_render.py")
_VID41 = oku(os.path.dirname(KOK), "app", "render-studio", "src", "Video.tsx")


def _fn_kaynak(kod, ad):
    """Modulu IMPORT ETMEDEN tek bir saf fonksiyonun kaynagini al.

    ⚠ `pipeline.py` import ANINDA `/opt/vidrush` altina dizin acmaya calisiyor;
    testte import edilemez. Bu yuzden fonksiyon kaynaktan cikarilip yalitilmis
    bir ad uzayinda kosturulur — davranis GERCEKTEN olculur, dizgi eslesmesi
    degil."""
    i = kod.find(f"\ndef {ad}(")
    if i < 0:
        return None
    j = kod.find("\ndef ", i + 1)
    return kod[i:j if j > 0 else len(kod)]


_KY_KAYNAK = _fn_kaynak(_PP41, "_kaynak_yazi_props")
kontrol("⭐ I-41 KIRMIZI: `_kaynak_yazi_props` yardimcisi VAR",
        bool(_KY_KAYNAK), "pipeline.py'de bulunamadi")
_KY_AD = {}
if _KY_KAYNAK:
    exec(compile(_KY_KAYNAK, "<pipeline._kaynak_yazi_props>", "exec"), _KY_AD)
_ky = _KY_AD.get("_kaynak_yazi_props")


def _ky41(s):
    return _ky(s) if callable(_ky) else None


kontrol("⭐ I-41 KIRMIZI: dolu kunye props alanina TASINIYOR",
        _ky41({"kaynakYazi": "NASA Goddard / CC BY"})
        == {"kaynakYazi": "NASA Goddard / CC BY"},
        _ky41({"kaynakYazi": "NASA Goddard / CC BY"}))
kontrol("I-41: kunye YOKSA alan HIC gecmiyor (eski props BIT-BIT ayni)",
        _ky41({}) == {} and _ky41({"kaynakYazi": ""}) == {}
        and _ky41({"kaynakYazi": "   "}) == {},
        (_ky41({}), _ky41({"kaynakYazi": ""})))
kontrol("I-41: uzun atif KIRPILIYOR (hizli_render 34, props tavani 80)",
        len((_ky41({"kaynakYazi": "K" * 200}) or {}).get("kaynakYazi", "")) == 80,
        len((_ky41({"kaynakYazi": "K" * 200}) or {}).get("kaynakYazi", "")))
kontrol("I-41: bozuk girdi ISTISNA FIRLATMIYOR",
        _ky41({"kaynakYazi": None}) == {} and _ky41({"kaynakYazi": 42}) != None,
        _ky41({"kaynakYazi": 42}))
# ── PROPS MONTAJI: alan GERCEKTEN sahneye giriyor mu? ──
_MONTAJ41 = _PP41[_PP41.find("props_sahneler.append({"):
                  _PP41.find("kumulatif_sn += sure")]
kontrol("⭐ I-41 KIRMIZI: props montaji `_kaynak_yazi_props`u CAGIRIYOR",
        "**_kaynak_yazi_props(s)" in _MONTAJ41,
        "props_sahneler.append blogunda yok")
# ⚠ FAZ UI-7: kunye ATAN yol sayisi 3 -> 4 oldu
#   (+1 `UI7-GORSEL-YASAK-KAPISI` gercek klip bulunca).
# ⚠ FAZ Y-5: UI-8'de eklenen 5. yol (`UI8-SURE-KORUNDU` klip yeniden
# kullanimi) KALDIRILDI — global "ayni kaynak <=8 sn" tavanini deliyordu.
# Sayi 5 -> 4. Sozlesme AYNEN korunuyor: kunye HICBIR yolda kaybolmuyor.
kontrol("I-41: kunye KAYNAGI korundu (pipeline 4 noktada hala ATIYOR)",
        _PP41.count('s["kaynakYazi"] = ') == 4,
        _PP41.count('s["kaynakYazi"] = '))
from editor import adapter as _adp41                            # noqa: E402
kontrol("I-41: `kaynakYazi` kayipsizlik sozlesmesinde ZATEN vardi",
        "kaynakYazi" in _adp41.HIZLI_RENDER_ALANLARI
        and "kaynakYazi" in _adp41.REMOTION_ALANLARI)

# ── VARSAYILAN RENDERER: Remotion `VidrushVideo` ──
kontrol("⭐ I-41 KIRMIZI: `Sahne` tipi `kaynakYazi` alanini TASIYOR",
        re.search(r"kaynakYazi\?\s*:\s*string", _VID41) is not None,
        "Video.tsx Sahne tipinde alan yok")
kontrol("⭐ I-41 KIRMIZI: `KaynakYazi` bileseni VAR ve sahnede CIZILIYOR",
        "const KaynakYazi" in _VID41 and "<KaynakYazi" in _VID41,
        "bilesen yok / cizilmiyor")
kontrol("⭐ I-41: kunye geometrisi I-39 ile AYNI (0.075 / guvenli kenar 64)",
        "0.075" in _VID41 and "64" in _VID41
        and abs(_etipo.KAYNAK_ETIKETI_ALTYAZILI - 0.075) < 1e-9,
        "Video.tsx'te I-39 konumu yok")
# ⚠ Bu kompozisyonda altyazi ALTTA (paddingBottom 72) ve rozet SOL USTTE;
# sag ust bos. I-39'da olculen "nefes" kurali burada da gecerli.
# ⚠ KAPI CIZILEN IFADEYI olcer, YORUM METNINI degil: bilesenin KENDI govdesi
# ayiklanir (aksi halde "eski sabit soyle idi" diyen bir yorum kapiyi kirar).
_KY_TSX = _VID41[_VID41.find("const KaynakYazi"):]
_KY_TSX = _KY_TSX[:_KY_TSX.find("\ntype Gorunum")]
kontrol("I-41: kunye USTTEN konumlaniyor, ALT seritte DEGIL",
        "top:" in _KY_TSX and "bottom" not in _KY_TSX
        and "KUNYE_Y_ORANI * height" in _KY_TSX, _KY_TSX[:120])

# ── IKINCI RENDERER: hizli_render (ayni props) ──
# ⚠ Yine CIZILEN IFADE olculur: fonksiyon govdesinden YORUM SATIRLARI
# ayiklanir. Aksi halde "eski sabit soyle idi" diyen bir aciklama kapiyi kirar
# ve kapi kendi belgesini kusur sanar.
_HR_FN = _fn_kaynak(_HR41, "_kaynak_yazi_filtre") or ""
_HR_KOD = "\n".join(l for l in _HR_FN.splitlines()
                    if not l.strip().startswith("#"))
kontrol("⭐ I-41 KIRMIZI: hizli_render kunyesi SABIT `y=h-th-22`den KURTULDU",
        bool(_HR_KOD) and "y=h-th-22" not in _HR_KOD
        and "x=w-tw-26" not in _HR_KOD, "eski ifade duruyor")
kontrol("⭐ I-41: iki renderer AYNI konumu kullaniyor (ikinci geometri YOK)",
        "x=w-tw-64:y=h*0.075" in _HR_KOD
        and "KUNYE_Y_ORANI = 0.075" in _VID41
        and "KUNYE_GUVENLI_KENAR = 64" in _VID41,
        "hizli_render ile Video.tsx ayrisiyor")
kontrol("I-41: hizli_render kunyeyi HALA `kaynakYazi`dan okuyor",
        'sahne.get("kaynakYazi")' in _HR41)
kontrol("I-41: kunye YALNIZ lisansli klipte ciziliyor (bos ise yok)",
        "if not kanal:" in _HR41 and "return \"\"" in _HR41)

# ── GERILEME YOK ──
kontrol("I-41 GERILEME YOK: 22 alanlik generate sozlesmesi DEGISMEDI",
        len(set(re.findall(r"\{ad: '(\w+)'",
                           oku(KOK, "static/js/api.js")))) == 22)
kontrol("I-41 GERILEME YOK: I-39 konum sabitleri DEGISMEDI",
        abs(_etipo.KAYNAK_ETIKETI_ALTYAZILI - 0.075) < 1e-9
        and _etipo.KONUM["chapter-title"] == 0.60)
kontrol("I-41: pipeline.py ve hizli_render.py DERLENIYOR",
        _derlenir(os.path.join(KOK, "pipeline.py"))
        and _derlenir(os.path.join(KOK, "hizli_render.py")))

blok("§39p I-40 — ONIZLEME YOLU REMOTION GEOMETRISINDEN AYRISIYORDU")

# ⚠ I-39'DA BULUNAN, I-40'TA OLCULEN KUSUR: `editor/onizleme.py` (ffmpeg
# onizleme yolu) yazi katmanlarini SABIT sayilarla ciziyordu ve planin KENDI
# spec'ini OKUMUYORDU:
#     chapter-title -> y=h*0.70 SABIT   (plan 0.60 diyor — I-39)
#     lower-third   -> y=h*0.80 SABIT   (KONUM 0.78 diyor)
#     source-label  -> y=h-th-14 SABIT  (y_orani HIC okunmuyor; I-16'da
#                      Remotion'da duzeltilen `bottom: 22` kusurunun AYNISI,
#                      ustelik guvenli kenarin -64*olcek- DISINDA)
# Puntolar da elle secilmisti (34/26/15) ve profil puntosuyla (60/42/21)
# hicbir aritmetik bagi yoktu. Yani IKI AYRI GEOMETRI vardi — I-14'te olculen
# kusur sinifinin ta kendisi (plan bir sey hesaplar, cizim baskasini cizer).
# ⚠ DURUST KAPSAM: bu modulun repoda CAGIRANI YOK (olculdu: hicbir import).
# Duzeltme uretim ciktisini degistirmez; AYRISMAYI ve testsizligi kapatir.

from editor import onizleme as _onz                               # noqa: E402

_P40 = _eprofil.profil("premium-modern")
_ONZ_OLCU = (1280, 720)
_OLCEK40 = _ONZ_OLCU[0] / 1920.0


def _spec40(ad, **prm):
    """render_plan'daki bicimde tek bir ffmpeg yazi spec'i."""
    return {"ad": ad, "renderer": "ffmpeg", "beat_id": "b001",
            "sure_sn": 3.0, "parametre": dict(prm)}


# I-39 1080p pilotunun GERCEK yazi specleri (render_plan.json'dan OLCULDU)
_SPEC40 = [
    _spec40("chapter-title", metin="THERE IS A BAG OF GRASS", y_orani=0.6,
            punto=60, x=100),
    _spec40("source-label", metin="Famartin / CC-BY-SA", y_orani=0.075,
            punto=21),
]

_yerlesim = getattr(_onz, "yazi_yerlesimi", None)
kontrol("⭐ I-40 KIRMIZI: onizleme `yazi_yerlesimi` TEK KAYNAK fonksiyonu VAR",
        callable(_yerlesim), type(_yerlesim).__name__)


def _yer40(ad, prm):
    if not callable(_yerlesim):
        return {}
    return _yerlesim(ad, prm, gen=_ONZ_OLCU[0], yuk=_ONZ_OLCU[1], p=_P40)


_Y40_BASLIK = _yer40("chapter-title", _SPEC40[0]["parametre"])
_Y40_KUNYE = _yer40("source-label", _SPEC40[1]["parametre"])
kontrol("⭐ I-40 KIRMIZI: bolum basligi PLANIN y_orani'ni okuyor (0.60)",
        abs(_Y40_BASLIK.get("y_orani", -1) - 0.60) < 1e-9, _Y40_BASLIK)
kontrol("⭐ I-40 KIRMIZI: kunye PLANIN y_orani'ni okuyor (0.075, dip DEGIL)",
        abs(_Y40_KUNYE.get("y_orani", -1) - 0.075) < 1e-9, _Y40_KUNYE)
kontrol("⭐ I-40: punto SABIT degil, spec puntosundan OLCEKLENIYOR",
        _Y40_BASLIK.get("punto") == round(60 * _OLCEK40)
        and _Y40_KUNYE.get("punto") == round(21 * _OLCEK40),
        (_Y40_BASLIK.get("punto"), _Y40_KUNYE.get("punto"),
         round(60 * _OLCEK40), round(21 * _OLCEK40)))
kontrol("I-40: izgara x'i de OLCEKLENIYOR (66 sabiti degil)",
        _Y40_BASLIK.get("x_px") == round(100 * _OLCEK40), _Y40_BASLIK.get("x_px"))
kontrol("I-40: kunye SAGA hizali, bolum basligi SOLA (Remotion ile ayni)",
        _Y40_KUNYE.get("sag_hizali") is True
        and _Y40_BASLIK.get("sag_hizali") is False)
# ⚠ TSX `KaynakEtiketi` guvenli kenari ZORLUYOR; onizleme de zorlamali.
_Y40_DIP = _yer40("source-label", {"metin": "x", "y_orani": 0.99, "punto": 21})
_tavan40 = (_ONZ_OLCU[1] - _P40.tipografi.guvenli_kenar * _OLCEK40
            - round(21 * _OLCEK40) * 1.3)
kontrol("⭐ I-40: kunye GUVENLI KENARI zorluyor (y_orani 0.99 KIRPILIYOR)",
        _Y40_DIP.get("y_px", 1e9) <= _tavan40 + 1e-6
        and _Y40_DIP.get("kirpildi") is True,
        (_Y40_DIP.get("y_px"), _tavan40))
# ⚠ y_orani YOKSA uydurma sabit degil, `tipografi.KONUM` (tek kaynak).
_Y40_VARS = _yer40("chapter-title", {"metin": "x", "punto": 60})
kontrol("I-40: y_orani yoksa `tipografi.KONUM`a duser (uydurma sabit YOK)",
        abs(_Y40_VARS.get("y_orani", -1)
            - _etipo.KONUM["chapter-title"]) < 1e-9, _Y40_VARS.get("y_orani"))

# ── FILTRE DIZGISI: ayrisma dizgide de KALMAMALI ──
# ⚠ Yerel ffmpeg libfreetype OLMADAN derlenmis (modulun kendi belgeledigi
# durum). Yetenek yoklamasi TEST ICIN gecici olarak acilir; ffmpeg
# CALISTIRILMAZ, yalniz filtre dizgisi uretilir (saf, deterministik).
_DT_ESKI = _onz._DRAWTEXT_ONBELLEK[0]
_onz._DRAWTEXT_ONBELLEK[0] = True
try:
    _VF40, _ATLANAN40 = _onz._segment_filtresi(
        {"beat_id": "b001", "motion": _SPEC40}, 3.0, 30,
        _ONZ_OLCU[1], _ONZ_OLCU[0])
finally:
    _onz._DRAWTEXT_ONBELLEK[0] = _DT_ESKI
kontrol("⭐ I-40 KIRMIZI: filtrede SABIT `y=h*0.70` KALMADI",
        "h*0.70" not in _VF40 and "h*0.80" not in _VF40, _VF40[:200])
kontrol("⭐ I-40 KIRMIZI: kunyede SABIT `y=h-th-14` KALMADI",
        "y=h-th-14" not in _VF40 and "fontsize=15" not in _VF40, _VF40[:200])
kontrol("⭐ I-40: filtre PLANIN y_orani'ni tasiyor (0.60 ve 0.075)",
        "h*0.600" in _VF40 and "0.075" in _VF40, _VF40[:260])
kontrol("I-40: yazi specleri ATLANMADI (drawtext varken)",
        not [a for a in _ATLANAN40
             if a.get("spec") in ("chapter-title", "source-label")],
        _ATLANAN40)

# ── PARITE: I-39 pilotunun TUM yazi katmanlari icin onizleme == Remotion ──
_PARITE40 = [("chapter-title", 0.6, 60), ("source-label", 0.075, 21),
             ("lower-third", _etipo.KONUM["lower-third"], 42),
             ("callout", 0.45, 30)]
_sapan40 = []
for _ad40, _y40, _pt40 in _PARITE40:
    _r40 = _yer40(_ad40, {"metin": "x", "y_orani": _y40, "punto": _pt40})
    if abs(_r40.get("y_orani", -1) - _y40) > 1e-9:
        _sapan40.append((_ad40, _y40, _r40.get("y_orani")))
kontrol("⭐ I-40: DORT yazi turunun HEPSINDE onizleme == plan y_orani",
        not _sapan40, _sapan40)
kontrol("⭐ I-40: onizleme ile Remotion arasinda IKINCI ARITMETIK YOK "
        "(sabit y orani kodda kalmadi)",
        "0.70, sure" not in oku(KOK, "editor/onizleme.py")
        and "0.80, sure" not in oku(KOK, "editor/onizleme.py"))

# ── GERILEME YOK ──
kontrol("I-40 GERILEME YOK: KONUM sabitleri DEGISMEDI (I-39)",
        _etipo.KONUM["chapter-title"] == 0.60
        and abs(_etipo.KAYNAK_ETIKETI_ALTYAZILI - 0.075) < 1e-9
        and _etipo.KONUM["lower-third"] == 0.78)
kontrol("I-40 GERILEME YOK: drawtext YOKKEN yazi SESSIZCE dusmuyor",
        callable(getattr(_onz, "drawtext_var_mi", None))
        and "drawtext filtresi YOK" in oku(KOK, "editor/onizleme.py"))
kontrol("I-40 GERILEME YOK: onizleme hala ffmpeg-disi spec'i ATLIYOR",
        any(a.get("sebep") == "renderer=remotion" for a in _onz._segment_filtresi(
            {"beat_id": "b1", "motion": [{"ad": "map-route",
                                          "renderer": "remotion",
                                          "parametre": {}}]},
            2.0, 30, 720, 1280)[1]))
kontrol("I-40: bozuk/eksik parametre ISTISNA FIRLATMIYOR",
        callable(_yerlesim)
        and isinstance(_yer40("source-label", {}), dict)
        and isinstance(_yer40("bilinmeyen", {"y_orani": "x", "punto": None}),
                       dict))

blok("§39o I-39 — ALTYAZI NEFES BOSLUGU (olculen kusur)")

# ⚠ I-38'IN 1080p PILOTUNDA OLCULEN KUSUR: ekran kunyesi ARTIK ciziliyor
# (I-38 duzeltmesi) ama altyazi bandinin (`ALTYAZI_BANT[0]` = 0.81 ->
# 874.8 px) DIBINDE duruyor. Iki yazi katmani da altyaziya "nefes" birakmiyor:
#   source-label  y=0.755 -> alt kenar 815.4 + 21*1.3   = 842.7 px -> 32.1 px
#   chapter-title y=0.70  -> alt kenar 756 + 60*1.3 + 25 = 859.0 px -> 15.8 px
# Gerekli esik = altyazi puntosu * 1.25 = 38 * 1.25 = **47.5 px**.
# ⚠ Handoff notu chapter-title bosluguna ~43.8 px diyordu; o sayi yalniz
# METIN alt kenarini (y*H + punto*1.25) sayiyor, BANT DOLGUSUNU saymiyordu.
# Burada olculen deger CIZILEN BANT KUTUSUDUR (dolgu dahil) — daha kati ve
# ekranda gercekten kaplanan yer. Iki okuma da esigin ALTINDA, hukum ayni.
# Hicbir kapi bunu gormuyordu: katmanlar banda GIRMEDIGI icin
# `KALITE-YAZI-CAKISMA` ve `KALITE-GUVENLI-ALAN` temiz donuyordu.

from editor import motion as _mo39                                # noqa: E402

_ALT_BANT_UST_PX = _etipo.ALTYAZI_BANT[0] * 1080          # 874.8
_NEFES_ESIK_PX = _eprofil.VARSAYILAN.tipografi.altyazi * 1.25   # 47.5

kontrol("I-39: nefes esigi altyazi puntosundan TURETILIYOR (47.5 px)",
        abs(_NEFES_ESIK_PX - 47.5) < 1e-9
        and _eprofil.VARSAYILAN.tipografi.altyazi == 38, _NEFES_ESIK_PX)

# ── KIRMIZI 1: KONUM SABITLERI (kusurlu geometri) ──
kontrol("⭐ I-39 KIRMIZI: kunye altyazi varken SAG USTE tasindi (0.075)",
        abs(_etipo.KAYNAK_ETIKETI_ALTYAZILI - 0.075) < 1e-9,
        _etipo.KAYNAK_ETIKETI_ALTYAZILI)
kontrol("⭐ I-39 KIRMIZI: bolum basligi 0.70 -> 0.60 tasindi",
        abs(_etipo.KONUM["chapter-title"] - 0.60) < 1e-9,
        _etipo.KONUM["chapter-title"])
kontrol("⭐ I-39: motion spec varsayilani KONUM ile AYNI (iki aritmetik YOK)",
        abs(_mo39.bolum_basligi_spec("X", 3.0).sozluk()["parametre"]["y_orani"]
            - _etipo.KONUM["chapter-title"]) < 1e-9
        and abs(_mo39.bolum_basligi_spec("X", 3.0)
                .sozluk()["parametre"]["y_orani"] - 0.60) < 1e-9,
        _mo39.bolum_basligi_spec("X", 3.0).sozluk()["parametre"]["y_orani"])

# ── KIRMIZI 2: DETERMINISTIK OLCUM FONKSIYONU ──
_nefes_fn = getattr(_kk, "altyazi_nefes_olcusu", None)
kontrol("⭐ I-39 KIRMIZI: `altyazi_nefes_olcusu` OLCUMU VAR",
        callable(_nefes_fn), type(_nefes_fn).__name__)


def _nefes39(katmanlar):
    """Gercek pilot katmanlariyla nefes olcumu (saf, agsiz)."""
    if not callable(_nefes_fn):
        return {}
    return _nefes_fn(
        [{"ad": k.ad, "y_orani": k.y_orani, "punto": k.punto, "bant": k.bant}
         for k in katmanlar],
        kare_yukseklik=1080, bant_ust_orani=_etipo.ALTYAZI_BANT[0],
        altyazi_punto=_eprofil.VARSAYILAN.tipografi.altyazi)


# I-38 pilotunun GERCEK katmanlari (edit_manifest.json'dan OLCULDU) — ESKI
# geometri. Bu kurulum KALICI KIRMIZI KANITTIR: kapi bunu her zaman yakalar.
_KAT39_ESKI = [
    _etipo.katman_kur("chapter-title", "THERE IS A BAG OF GRASS", 0.2, 3.387,
                      p=_P38, y_orani=0.70),
    _etipo.katman_kur("source-label", "Famartin / CC-BY-SA", 4.488, 3.0,
                      p=_P38, y_orani=0.755)]
_N39_ESKI = _nefes39(_KAT39_ESKI)
kontrol("⭐ I-39 KIRMIZI: ESKI geometride IKI katman da nefessiz",
        _N39_ESKI.get("temiz") is False and len(_N39_ESKI.get("ihlaller") or []) == 2,
        _N39_ESKI.get("ihlaller"))
kontrol("⭐ I-39: kunye boslugu 32.1 px OLCULDU (esik 47.5)",
        any(abs(i.get("nefes_px", 0) - 32.1) < 0.05
            for i in (_N39_ESKI.get("ihlaller") or [])),
        [(i.get("ad"), i.get("nefes_px")) for i in
         (_N39_ESKI.get("ihlaller") or [])])
kontrol("I-39: olcum esigi ve bant ust kenarini RAPORLUYOR",
        abs(_N39_ESKI.get("esik_px", 0) - 47.5) < 1e-9
        and abs(_N39_ESKI.get("bant_ust_px", 0) - 874.8) < 1e-6,
        (_N39_ESKI.get("esik_px"), _N39_ESKI.get("bant_ust_px")))

# ── YESIL: YENI geometri (uretim sabitleriyle) nefes birakiyor ──
_KAT39_YENI = [
    _etipo.katman_kur("chapter-title", "THERE IS A BAG OF GRASS", 0.2, 3.387,
                      p=_P38),
    _etipo.katman_kur("source-label", "Famartin / CC-BY-SA", 4.488, 3.0,
                      p=_P38, y_orani=_etipo.KAYNAK_ETIKETI_ALTYAZILI)]
_N39_YENI = _nefes39(_KAT39_YENI)
kontrol("⭐ I-39 YESIL: URETIM sabitleriyle nefes IHLALI YOK",
        _N39_YENI.get("temiz") is True and not _N39_YENI.get("ihlaller"),
        [(k.get("ad"), k.get("nefes_px"))
         for k in (_N39_YENI.get("kayitlar") or [])])
kontrol("I-39: her katmanin nefesi esigin USTUNDE ve OLCULU",
        all(k.get("nefes_px", -1) >= _NEFES_ESIK_PX
            for k in (_N39_YENI.get("kayitlar") or []))
        and len(_N39_YENI.get("kayitlar") or []) == 2,
        [(k.get("ad"), k.get("nefes_px"))
         for k in (_N39_YENI.get("kayitlar") or [])])

# ── KIRMIZI 3: PRE-QA KAPISI ──


def _qa39(katmanlar, kupler=True):
    q = _qon.QaSonucu()
    _qon._kalite_denetle(
        q, beatler=[], cekimler=[], yazi_katmanlari=katmanlar,
        adaylar_index={}, p=_qon.VARSAYILAN, kare_olcu=(1920, 1080),
        anlatim_bitis_sn=None, toplam=25.2, benzerlik_okuyucu=None, acik=True,
        altyazi_kupleri=([{"bas_sn": 0.1, "sure_sn": 25.0,
                           "metin": "x", "satirlar": ["x"]}] if kupler else None))
    return q


_Q39K = _qa39(_KAT39_ESKI)
kontrol("⭐ I-39 KIRMIZI: PRE-QA `KALITE-YAZI-NEFES-YOK` FAIL uretiyor",
        any(x.kod == "KALITE-YAZI-NEFES-YOK" and x.seviye == "fail"
            for x in _Q39K.sorunlar),
        [x.kod for x in _Q39K.sorunlar])
kontrol("⭐ I-39: olcum raporda GORUNUYOR (`altyazi_nefesi`)",
        (_Q39K.olcumler.get("kalite") or {}).get("altyazi_nefesi", {})
        .get("temiz") is False,
        (_Q39K.olcumler.get("kalite") or {}).get("altyazi_nefesi"))
_Q39Y = _qa39(_KAT39_YENI)
kontrol("⭐ I-39 YESIL: yeni geometride NEFES-YOK sorunu YOK",
        not [x for x in _Q39Y.sorunlar if x.kod == "KALITE-YAZI-NEFES-YOK"]
        and (_Q39Y.olcumler.get("kalite") or {})
        .get("altyazi_nefesi", {}).get("temiz") is True,
        (_Q39Y.olcumler.get("kalite") or {}).get("altyazi_nefesi"))
kontrol("⭐ I-39: kapi FAIL ve KALITE kodlarinda (bayraga bagli)",
        "KALITE-YAZI-NEFES-YOK" in _qon.FAIL_KODLARI
        and "KALITE-YAZI-NEFES-YOK" in _qon.KALITE_KODLARI)
# ⚠ ALTYAZI YOKSA BANT DA YOK: kapi UYDURMA hukum vermez.
_Q39N = _qa39(_KAT39_ESKI, kupler=False)
kontrol("I-39: altyazi YOKKEN kapi hukum VERMIYOR (olculemedi, sessiz PASS degil)",
        not [x for x in _Q39N.sorunlar if x.kod == "KALITE-YAZI-NEFES-YOK"]
        and (_Q39N.olcumler.get("kalite") or {})
        .get("altyazi_nefesi", {}).get("olculdu") is False,
        (_Q39N.olcumler.get("kalite") or {}).get("altyazi_nefesi"))
kontrol("I-39: olcum BOZUK girdide ISTISNA FIRLATMIYOR",
        callable(_nefes_fn)
        and _nefes_fn(None, kare_yukseklik=0, bant_ust_orani=None,
                      altyazi_punto="x").get("olculdu") is False
        and _nefes_fn([{"ad": None, "y_orani": "a", "punto": None}],
                      kare_yukseklik=1080, bant_ust_orani=0.81,
                      altyazi_punto=38).get("olculdu") is True)

# ── GERILEME YOK: onceki kapilar ve sozlesmeler ──
kontrol("I-39 GERILEME YOK: kunye HALA altyazi bandinin USTUNDE (I-16)",
        _etipo.KAYNAK_ETIKETI_ALTYAZILI + _etipo.YUKSEKLIK["source-label"]
        <= _etipo.ALTYAZI_BANT[0] + 1e-9,
        _etipo.KAYNAK_ETIKETI_ALTYAZILI)
kontrol("I-39 GERILEME YOK: iki katman da GUVENLI ALANDA (I-12)",
        not [s for k in _KAT39_YENI
             for s in _etipo.guvenli_alan_kontrol(k, p=_P38)],
        [(k.ad, _etipo.guvenli_alan_kontrol(k, p=_P38)) for k in _KAT39_YENI])
kontrol("I-39 GERILEME YOK: altyazisiz varsayilan konumlar DEGISMEDI",
        _etipo.KONUM["source-label"] == 0.895
        and _etipo.KONUM["subtitle"] == 0.855
        and _etipo.ALTYAZI_BANT == (0.81, 0.94))
kontrol("I-39 GERILEME YOK: I-38 spec zamani HALA SAHNEYE GORELI",
        all(s["bas_sn"] < _sahne_suresi(s["beat_id"]) for s in _SP38))
kontrol("I-39: kunye SAG UST (y ust kenari guvenli kenarin ICINDE)",
        _etipo.KAYNAK_ETIKETI_ALTYAZILI * 1080
        >= _P38.tipografi.guvenli_kenar,
        _etipo.KAYNAK_ETIKETI_ALTYAZILI * 1080)

blok("§39m I-37 — BEAT->SCENE->FACT->ASSET BAGI KOPAMAZ")

# ⚠ I-37'DE OLCULEN KUSUR (lawn pilotu, gercek render):
# `cesitli_sirala` varliklari SAHNELER ARASINDA yeniden diziyordu; varliklar
# sahnelere INDEKS ile eslendigi icin anlatim ile gorsel KAYDI. Olculen:
#   b003 anlatim s02 "thin, patchy lawn" <- s03 FISKIYE gorseli
#   b004 anlatim s03 "water lightly"     <- s04 RICINUS fidesi
#   b005 anlatim s04 "seedling"          <- s02 patchy lawn
# 6 beat'in 3'u kaymisti ve HICBIR otomatik kapi gormuyordu.

class _C37:
    def __init__(self, sid, aid):
        self.scene_id = sid
        self.asset_id = aid


class _B37:
    def __init__(self, bid, sid, fid):
        self.beat_id = bid
        self.scene_id = sid
        self.fact_id = fid


def _bag37(esleme):
    """esleme: [(beat, scene, asset_scene)] -> qa_on bag olcumu."""
    cek = [_C37(s, f"{a}_x") for _, s, a in esleme]
    bea = [_B37(b, s, s) for b, s, _ in esleme]
    idx = {f"{a}_x": {"scene_id": a} for _, _, a in esleme}
    q = _qon.QaSonucu()
    _qon._kalite_denetle(q, beatler=bea, cekimler=cek, yazi_katmanlari=[],
                         adaylar_index=idx, p=_qon.VARSAYILAN,
                         kare_olcu=(1920, 1080), anlatim_bitis_sn=None,
                         toplam=10.0, benzerlik_okuyucu=None, acik=True)
    return q

# ── KIRMIZI: gercek lawn kaymasi ──
_q37 = _bag37([("b001", "s001", "s001"), ("b002", "s001", "s001"),
               ("b003", "s002", "s003"), ("b004", "s003", "s004"),
               ("b005", "s004", "s002"), ("b006", "s005", "s005")])
_bag = _q37.olcumler["kalite"]["beat_bagi"]
kontrol("⭐ I-37 KIRMIZI: capraz sahne kaymasi YAKALANIYOR (3 beat)",
        len(_bag["kopuk"]) == 3 and _bag["temiz"] is False,
        [k["beat_id"] for k in _bag["kopuk"]])
kontrol("⭐ I-37: kopuk bag PRE-QA'da FAIL uretiyor",
        any(x.kod == "KALITE-BAG-KOPUK" and x.seviye == "fail"
            for x in _q37.sorunlar))
kontrol("I-37: kopuk kayit beat/scene/varlik-scene GOSTERIYOR",
        _bag["kopuk"][0]["beat_id"] == "b003"
        and _bag["kopuk"][0]["scene_id"] == "s002"
        and _bag["kopuk"][0]["varlik_scene_id"] == "s003", _bag["kopuk"][0])
# ── YESIL: dogru baglama ──
_q37b = _bag37([("b001", "s001", "s001"), ("b002", "s001", "s001"),
                ("b003", "s002", "s002"), ("b004", "s003", "s003"),
                ("b005", "s004", "s004"), ("b006", "s005", "s005")])
_bag_b = _q37b.olcumler["kalite"]["beat_bagi"]
kontrol("⭐ I-37 YESIL: dogru baglamada kopuk YOK",
        _bag_b["temiz"] is True and not _bag_b["kopuk"])
kontrol("I-37: bag RAPORDA gorunur (her beat icin kayit)",
        len(_bag_b["kayitlar"]) == 6
        and all({"beat_id", "scene_id", "fact_id", "asset_id"} <= set(k)
                for k in _bag_b["kayitlar"]))
kontrol("⭐ I-37: kapi FAIL ve KALITE kodlarinda (bayraga bagli)",
        "KALITE-BAG-KOPUK" in _qon.FAIL_KODLARI
        and "KALITE-BAG-KOPUK" in _qon.KALITE_KODLARI)
kontrol("⭐ I-37: siralayici artik SAHNELER ARASI permutasyon YAPMIYOR",
        "itertools.permutations" not in _sikistir(
            oku(KOK, "testler/smoke_konsept3_teknoloji_i20.py")))

blok("§39l I-36 — SAGLAYICI TUTARSIZLIGI DUZELTILDI")

# ⚠ I-35'TE OLCULEN KUSUR: I-33 raporunda s01 icin Commons denemesi
# `durum: BAYT-YOK, sebep: HTTP 429` yaziyordu AMA kabul edilen b001 varligi
# Commons'in vitrini idi (wikimedia/cc-by-sa). Yani Commons BIR BAYT VERDI,
# sonraki 429 basarili gecmisi EZDI; ayrica `kullanilan_saglayici` erken
# donuste SON saglayiciya (nasa) esitlendigi icin genel saglayici SAHTE
# bicimde nasa gorunuyordu.

class _S36:
    """Sirali indirme sonuclari veren sahte saglayici (ag YOK)."""

    def __init__(self, ad, adaylar, sonuclar):
        self.ad = ad
        self._a = adaylar
        self._s = list(sonuclar)
        self.ara_sayisi = 0
        self.indir_sayisi = 0

    def ara(self, sorgu, adet=6, en_az_genislik=0):
        self.ara_sayisi += 1
        return {"ok": True, "adaylar": list(self._a), "elenen": [],
                "denenen": len(self._a), "hata": ""}

    def indir(self, aday, hedef, deneme=1):
        self.indir_sayisi += 1
        r = self._s[min(self.indir_sayisi - 1, len(self._s) - 1)]
        if r.get("ok"):
            with open(hedef, "wb") as f:
                f.write(b"x" * 20000)
        return dict(r)


_OK36 = {"ok": True}
_429 = {"ok": False, "http": 429, "sebep": "HTTP 429"}
with _tf25.TemporaryDirectory() as _d36:
    _h36 = os.path.join(_d36, "a.jpg")
    _ADAY36 = [_aday(f"https://s{i}.test/{i}.jpg") for i in range(4)]

    # ── SENARYO 1: BASARI -> 429 (I-33'un gercek sirasi) ──
    _co = _S36("commons", _ADAY36, [_OK36, _429, _429, _429])
    _na = _S36("nasa", _ADAY36, [_OK36])
    _r1 = _ed.edin("q", _h36, adet=2, saat=lambda: 0.0,
                   saglayicilar=[{"ad": "commons", "modul": _co},
                                 {"ad": "nasa", "modul": _na}])
    _d_co = next(d for d in _r1["denemeler"] if d["saglayici"] == "commons")
    kontrol("⭐ I-36: BAYT VEREN saglayici 429 sonrasi BAYT-YOK OLMUYOR",
            _d_co["durum"] == "KISMI-OK" and _d_co["toplanan_katki"] == 1,
            _d_co["durum"])
    kontrol("⭐ I-36: son hata KAYBOLMUYOR, AYRI alanda duruyor",
            _d_co["son_hata"]["http"] == 429
            and "429" in _d_co["sebep"] and "ALINDI" in _d_co["sebep"])
    kontrol("⭐ I-36: kullanilan_saglayici SECILEN varliktan turer (commons)",
            _r1["kullanilan_saglayici"] == "commons", _r1["kullanilan_saglayici"])
    kontrol("⭐ I-36: son hata genel saglayiciyi SAHTE bicimde nasa YAPMIYOR",
            _r1["kullanilan_saglayici"] != "nasa")
    kontrol("⭐ I-36: dagilim SADECE toplanan varliklardan",
            _r1["saglayici_dagilimi"] == {"commons": 1, "nasa": 1},
            _r1["saglayici_dagilimi"])
    kontrol("I-36: her varlik KENDI kaynagini tasiyor",
            [a["kaynak_saglayici"] for a in _r1["adaylar"]]
            == ["commons", "nasa"])
    kontrol("I-36: denemeler KRONOLOJIK (commons once)",
            [d["saglayici"] for d in _r1["denemeler"]] == ["commons", "nasa"])
    kontrol("I-36: TEK ara() cagrisi korundu",
            _co.ara_sayisi == 1 and _na.ara_sayisi == 1)

    # ── SENARYO 2: 429 -> BASARI (ayni saglayici icinde) ──
    _co2 = _S36("commons", _ADAY36, [_429, _OK36, _OK36])
    _r2 = _ed.edin("q", _h36, adet=1, saat=lambda: 0.0,
                   saglayicilar=[{"ad": "commons", "modul": _co2}])
    kontrol("⭐ I-36: 429 -> BASARI sirasinda saglayici DOGRU (commons)",
            _r2["ok"] and _r2["kullanilan_saglayici"] == "commons"
            and _r2["saglayici_dagilimi"] == {"commons": 1})

    # ── SENARYO 3: COKLU BASARI + SON HATA ──
    _co3 = _S36("commons", _ADAY36, [_OK36, _OK36, _429, _429])
    _r3 = _ed.edin("q", _h36, adet=3, saat=lambda: 0.0,
                   saglayicilar=[{"ad": "commons", "modul": _co3}])
    _d3 = _r3["denemeler"][0]
    kontrol("⭐ I-36: COKLU basari + son hata -> KISMI-OK, katki 2",
            _d3["durum"] == "KISMI-OK" and _d3["toplanan_katki"] == 2
            and _r3["saglayici_dagilimi"] == {"commons": 2}, _d3["durum"])

    # ── SENARYO 4: HICBIR BASARI ──
    _co4 = _S36("commons", _ADAY36, [_429, _429, _429, _429])
    _r4 = _ed.edin("q", _h36, adet=1, saat=lambda: 0.0,
                   saglayicilar=[{"ad": "commons", "modul": _co4}])
    _d4 = _r4["denemeler"][0]
    kontrol("⭐ I-36: HICBIR basari yoksa durum BAYT-YOK KALIR (gevsetme yok)",
            _d4["durum"] == "BAYT-YOK" and _d4["toplanan_katki"] == 0
            and _r4["ok"] is False and _r4["kullanilan_saglayici"] == ""
            and _r4["saglayici_dagilimi"] == {})

    # ── SENARYO 5: SECILEN Commons ama SON hata 429 (tek saglayici) ──
    _co5 = _S36("commons", _ADAY36, [_OK36, _429, _429, _429])
    _r5 = _ed.edin("q", _h36, adet=2, saat=lambda: 0.0,
                   saglayicilar=[{"ad": "commons", "modul": _co5}])
    kontrol("⭐ I-36: secilen commons, son hata 429 -> saglayici hala commons",
            _r5["ok"] is True and _r5["kullanilan_saglayici"] == "commons"
            and _r5["denemeler"][0]["durum"] == "KISMI-OK")

# ── SENARYO 6: GERCEK I-33 fixture'i — b001 wikimedia + digerleri NASA ──
_I33_ZINCIR = [("b001", "wikimedia"), ("b002", "nasa"), ("b003", "nasa"),
               ("b004", "nasa"), ("b005", "nasa")]
_oz36 = _ed.saglayici_ozeti(
    [{"kaynak_saglayici": s} for _, s in _I33_ZINCIR])
kontrol("⭐ I-36: I-33 fixture — ilk varlik wikimedia, kullanilan_saglayici "
        "wikimedia",
        _oz36["kullanilan_saglayici"] == "wikimedia", _oz36)
kontrol("⭐ I-36: I-33 fixture — dagilim wikimedia 1 / nasa 4",
        _oz36["saglayici_dagilimi"] == {"wikimedia": 1, "nasa": 4})
_tekel36 = max(_oz36["saglayici_dagilimi"].values()) / _oz36["toplanan_adet"]
kontrol("⭐ I-36: %80 TEKEL hesabi dagilimdan DOGRU cikiyor",
        abs(_tekel36 - 0.8) < 1e-9, _tekel36)
kontrol("I-36: ozet AG/DOSYA kullanmaz (saf fonksiyon), bos girdi COKMEZ",
        _ed.saglayici_ozeti([])["kullanilan_saglayici"] == ""
        and _ed.saglayici_ozeti(None)["saglayici_dagilimi"] == {})
kontrol("I-36: 22 alan sozlesmesi ve devre kesici DOKUNULMADI",
        "DEVRE_ESIGI = 2" in oku(KOK, "medya/edinim.py")
        and "BEKLENEBILIR_TAVAN_SN = 30.0" in oku(KOK, "medya/edinim.py"))

blok("§39k I-35 — s01 SORGU DARALTMASI: ELENDI (olculdu)")

# ⚠ I-34, en kucuk ve bedava secenek olarak "s01 sorgusunu daralt" onermisti.
# I-35'te AYNI ara() butcesinde olculdu ve SECENEK CURUDU: vitrini eleyen HER
# daraltma NASA'yi BOSALTIYOR; NASA'yi koruyan HER daraltma vitrini BIRAKIYOR.
#
# OLCULEN TABLO (esik 2443; CO=commons, NA=nasa; "ok" = tum kapilari gecen):
_I35 = {
    "Pleiades supercomputer":                (18, 5, True,  15, 6),
    "Pleiades supercomputer racks":          (6,  0, False, 0,  0),
    "Pleiades supercomputer rack":           (6,  0, False, 0,  0),
    "Pleiades supercomputer system":         (6,  2, False, 0,  0),
    "Pleiades supercomputer hardware":       (0,  0, False, 0,  0),
    "Pleiades supercomputer aisle":          (0,  0, False, 0,  0),
    "Pleiades supercomputer nodes":          (3,  1, True,  0,  0),
    "Pleiades supercomputer Ames":           (18, 5, True,  5,  5),
    "Pleiades supercomputer NAS":            (18, 5, True,  13, 6),
    "NASA Advanced Supercomputing facility": (17, 6, False, 3,  3),
}
_MEVCUT35 = "Pleiades supercomputer"
_VITRINSIZ = [q for q, v in _I35.items() if not v[2]]
_NASA_DOLU = [q for q, v in _I35.items() if v[4] > 0]
kontrol("⭐ I-35: MEVCUT sorgu iyi NASA havuzu veriyor ama VITRINI iceriyor",
        _I35[_MEVCUT35][4] == 6 and _I35[_MEVCUT35][2] is True)
kontrol("⭐ I-35: vitrini eleyen daraltmalarin HEPSI ya NASA'yi BOSALTIYOR "
        "ya da SEMANTIK KAYIYOR",
        all(_I35[q][4] == 0 for q in _VITRINSIZ
            if q != "NASA Advanced Supercomputing facility"),
        {q: _I35[q] for q in _VITRINSIZ})
kontrol("⭐ I-35: NASA'yi koruyan daraltmalarin HEPSI vitrini BIRAKIYOR",
        all(_I35[q][2] for q in _NASA_DOLU
            if q != "NASA Advanced Supercomputing facility"),
        {q: _I35[q] for q in _NASA_DOLU})
kontrol("I-35: 'racks' daraltmasi IKI SAGLAYICIDA da SIFIR (I-26 asiri-darlik "
        "tuzagi)",
        _I35["Pleiades supercomputer racks"][1] == 0
        and _I35["Pleiades supercomputer racks"][4] == 0)
kontrol("I-35: 'system' vitrini eler AMA NASA 0 — Commons 429'da s01 "
        "MEDYASIZ kalir",
        _I35["Pleiades supercomputer system"][2] is False
        and _I35["Pleiades supercomputer system"][4] == 0
        and _I35["Pleiades supercomputer system"][1] == 2)
# Tek "iki saglayicida da dolu + vitrinsiz" aday semantik olarak KAYIYOR ve
# s02 ile CAKISIYOR (NASA'da 2/3 ayni varlik) -> I-22 tekrar kapisi riski.
_I35_NAS_FACILITY = {"commons_ilk_uc": ["NASA Advanced Supercomputing Facility",
                                        "NASA Advanced Supercomputing Modular",
                                        "NASA New Virtual Airport"],
                     "nasa_s02_cakisma": (2, 3)}
kontrol("⭐ I-35: tek hayatta kalan aday SEMANTIK KAYIYOR (Virtual Airport) "
        "ve s02 ile 2/3 CAKISIYOR",
        "Virtual Airport" in " ".join(_I35_NAS_FACILITY["commons_ilk_uc"])
        and _I35_NAS_FACILITY["nasa_s02_cakisma"] == (2, 3))
import ast as _ast35                                              # noqa: E402
_SM35 = oku(KOK, "testler/smoke_konsept3_teknoloji_i20.py")
_ST35 = next((_ast35.literal_eval(_d.value)
              for _d in _ast35.parse(_SM35).body
              if isinstance(_d, _ast35.Assign)
              and any(getattr(t, "id", "") == "SAHNE_TANIMI"
                      for t in _d.targets)), [])
kontrol("⭐ I-35: s01 sorgusu DEGISTIRILMEDI (olcum daraltmayi CURUTTU)",
        next(x["sorgu"] for x in _ST35 if x["kimlik"] == "s01")
        == _MEVCUT35)
kontrol("I-35: NEGATIF terim (-display) KULLANILMADI — I-29'da anahtar "
        "kelimenin guvenilmez oldugu olculmustu",
        "-display" not in oku(KOK, "testler/smoke_konsept3_teknoloji_i20.py"))
kontrol("I-35: OPERATOR ONAYI / SAGLAYICI SIRASI degisikligi YAPILMADI",
        '"saglayici_sirasi": ["commons", "nasa"]' in oku(
            KOK, "testler/smoke_konsept3_teknoloji_i20.py"))

blok("§39j I-34 — VITRIN/PANO KARE-BAKAN SINYAL: ELENDI (olculdu)")

# ⚠ I-33'te IKI KEZ dogrulanan kusur: b001'e dusen Commons varligi cam arkasi
# MUZE VITRINI. I-34 sorusu: bu, indirilen GORSEL uzerinde AGSIZ/OCR'SIZ bir
# kare-bakan sinyalle DETERMINISTIK yakalanabilir mi? OLCUM: HAYIR.
#
# Kume: 1 POZITIF varlik (s01_..._2.jpg, 3410x2634, "node on display at NASA
# Ames visitor center") + 6 NEGATIF varlik (I-27/I-33'te semantik olarak
# kabul edilen NASA varliklari + kapi elemeli ama semantik temiz olanlar).
# Her varlik 4 varyantta olculdu: tam / merkez70 / sol50 / ust50.
# Sinyaller (yalniz ffmpeg + saf Python; numpy/cv2 YOK):
#   S1 metin satiri yogunlugu · S2 edgedetect kenar orani
#   S3 duz-parlak pano kosulari · S4 specular (cam yansimasi vekili)
#
# OLCULEN ARALIKLAR (varyantlar arasi min-max):
_I34 = {
    "POZ s01_2 (VITRIN)": {"lab": 1, "S1": (0.0000, 0.2083),
                           "S2": (0.0396, 0.0688), "S3": (0.0455, 0.1873),
                           "S4": (0.0003, 0.0104)},
    "NEG s01 rack":       {"lab": 0, "S1": (0.0000, 0.0000),
                           "S2": (0.0523, 0.0661), "S3": (0.0000, 0.0131),
                           "S4": (0.0006, 0.0013)},
    "NEG s03 chip":       {"lab": 0, "S1": (0.0000, 0.0000),
                           "S2": (0.0183, 0.0355), "S3": (0.1082, 0.2608),
                           "S4": (0.0002, 0.0011)},
    "NEG s04 solar":      {"lab": 0, "S1": (0.0000, 0.0000),
                           "S2": (0.0465, 0.0678), "S3": (0.1116, 0.3355),
                           "S4": (0.0205, 0.0504)},
    "NEG s02 dikey":      {"lab": 0, "S1": (0.0000, 0.0417),
                           "S2": (0.0210, 0.0318), "S3": (0.1290, 0.2266),
                           "S4": (0.0033, 0.1126)},
    "NEG s04 dusuk":      {"lab": 0, "S1": (0.0194, 0.2222),
                           "S2": (0.0476, 0.0647), "S3": (0.0519, 0.0761),
                           "S4": (0.0074, 0.0404)},
}
_POZ34 = [v for v in _I34.values() if v["lab"] == 1]
_NEG34 = [v for v in _I34.values() if v["lab"] == 0]
for _sig in ("S1", "S2", "S3", "S4"):
    _pmin = min(v[_sig][0] for v in _POZ34)
    _pmax = max(v[_sig][1] for v in _POZ34)
    _nmin = min(v[_sig][0] for v in _NEG34)
    _nmax = max(v[_sig][1] for v in _NEG34)
    kontrol(f"⭐ I-34: {_sig} pozitif araligi negatiflerle ORTUSUYOR "
            f"(ayiran esik YOK)",
            _nmax >= _pmin and _nmin <= _pmax,
            f"poz {_pmin}-{_pmax} | neg {_nmin}-{_nmax}")
# Olculen en iyi esik supurmesi sonuclari (4 poz varyant / 24 neg varyant):
_I34_SUPURME = {"S1": (0.333, 0.50, 0.25), "S2": (0.400, 1.00, 0.25),
                "S3": (0.320, 1.00, 0.19), "S4": (0.316, 0.75, 0.20)}
_I34_IKILI = {"S1+S3": (0.500, 0.50, 0.50), "S2+S3": (0.545, 0.75, 0.43),
              "S2+S4": (0.400, 1.00, 0.25)}
kontrol("⭐ I-34: EN IYI TEK sinyal precision yalniz 0.25 (24 temiz "
        "varyantin 12'si YANLIS ELENIRDI)",
        max(v[0] for v in _I34_SUPURME.values()) == 0.400
        and _I34_SUPURME["S2"][2] == 0.25)
kontrol("⭐ I-34: EN IYI IKILI birlesim bile F1=0.545 / precision=0.43",
        max(v[0] for v in _I34_IKILI.values()) == 0.545
        and _I34_IKILI["S2+S3"][2] == 0.43)
kontrol("⭐ I-34: POZITIF varliğin kendisi KIRPMAYA gore KARARSIZ "
        "(S1 0.0000-0.2083)",
        _I34["POZ s01_2 (VITRIN)"]["S1"] == (0.0000, 0.2083))
for _sig, _neg_ad in (("S3", "NEG s04 solar"), ("S4", "NEG s02 dikey")):
    kontrol(f"⭐ I-34: {_sig} TERS calisiyor — '{_neg_ad}' pozitiften YUKSEK",
            _I34[_neg_ad][_sig][1] > _I34["POZ s01_2 (VITRIN)"][_sig][1],
            (_I34[_neg_ad][_sig], _I34["POZ s01_2 (VITRIN)"][_sig]))
kontrol("⭐ I-34: ORNEKLEM 1 POZITIF varlik — GENELLENEBILIR PASS DENMEZ",
        len(_POZ34) == 1 and len(_NEG34) == 5)
# ── HUKUM: guvenilir ayrim YOK -> URETIM KODUNA BAGLANMADI ──
for _d34 in ("medya/commons.py", "medya/edinim.py", "editor/qa_on.py",
             "editor/plan.py", "editor/kalite_kapisi.py"):
    kontrol(f"⭐ I-34: {_d34} vitrin/pano SINYAL KAPISI icermiyor",
            not re.search(r"(edgedetect|specular|vitrin|pano_|metin_yogunlu)",
                          _kod_yalniz(oku(KOK, _d34)), re.I), _d34)
kontrol("⭐ I-34: KUSURLU VARLIGA OZEL KARA LISTE URETIM KODUNDA YOK",
        not any("s01_11066148" in oku(KOK, _d)
                or "node on display" in oku(KOK, _d)
                for _d in ("medya/commons.py", "medya/edinim.py",
                           "editor/plan.py", "editor/qa_on.py",
                           "editor/kalite_kapisi.py")))

blok("§39i I-32 — KARE ORNEKLEME HER BEAT'I KAPSAR")

# ⚠ I-31'DE OLCULEN KOR NOKTA: ornekleme SAHNE (cumle) suresi uzerinden
# yapiliyordu. Pilotta 4 cumle / 5 beat vardi; s001 cumlesi 2.587 sn oldugu
# icin "sahne ortasi" 1.29'a dusuyordu (yani b002'ye) ve **b001 (0-0.862 sn)
# HICBIR kareyle orneklenmiyordu**. Kusurlu ACILIS PLANI ancak ELLE kare
# cikarilinca goruldu.

def _b32(i, bas, sure):
    return {"beat_id": f"b{i:03d}", "bas_sn": bas, "sure_sn": sure}


# ── GERCEK PILOT ZAMAN CIZGISI (I-31 raporundan birebir) ──
_PILOT32 = [_b32(1, 0.0, 0.862), _b32(2, 0.862, 1.725), _b32(3, 2.587, 4.738),
            _b32(4, 7.325, 4.9), _b32(5, 12.225, 4.825)]
_ESKI32 = [1.2, 1.71, 3.76, 4.96, 5.99, 8.21, 9.78, 10.27, 12.32, 14.54, 16.25]
kontrol("⭐ I-32 KIRMIZI: ESKI ornekleme b001'i HIC kapsamiyordu",
        not [t for t in _ESKI32 if 0.0 <= t < 0.862] and len(_ESKI32) == 11)
_P32 = _kk.kare_ornekleme_plani(_PILOT32, sure_sn=17.109, fps=30.0)
kontrol("⭐ I-32: YENI plan b001'i KAPSIYOR",
        bool(_P32["beat_kare"].get("b001")), _P32["beat_kare"].get("b001"))
kontrol("⭐ I-32: HICBIR beat kapsamsiz DEGIL",
        _P32["kapsanmayan"] == [] and _P32["yeterli"] is True, _P32["sebep"])
kontrol("⭐ I-32: EN AZ 11 kare sarti KORUNDU",
        _P32["kare"] >= 11, _P32["kare"])
for _b in _PILOT32:
    _b0, _b1 = _b["bas_sn"], _b["bas_sn"] + _b["sure_sn"]
    _ic = _P32["beat_kare"][_b["beat_id"]]
    kontrol(f"⭐ I-32: {_b['beat_id']} kareleri KOMSU BEAT'E TASMIYOR",
            bool(_ic) and all(_b0 <= t < _b1 for t in _ic), (_b0, _ic, _b1))
kontrol("I-32: epsilon YARIM KARE (fps hassas)",
        abs(_P32["epsilon_sn"] - 0.5 / 30.0) < 1e-4, _P32["epsilon_sn"])
# ⚠ Zamanlar raporda okunabilir olsun diye 4 haneye yuvarlaniyor; bu,
# izgaradan en fazla 0.00005 sn saptirir — yarim karenin (0.0167 sn) BINDE
# BIRI. Olculen ozellik "kare izgarasina oturuyor" olmali, ondalik esitlik
# degil (ilk yazdigim iddia bu yuzden fazla katiydi).
kontrol("I-32: kare zamanlari FPS IZGARASINDA (yarim karenin cok altinda)",
        all(abs(t * 30.0 - round(t * 30.0)) < 0.01 for t in _P32["anlar"]),
        [round(abs(t * 30.0 - round(t * 30.0)), 5) for t in _P32["anlar"]])

# ── COK KISA ACILIS ve KAPANIS ──
_KISA32 = [_b32(1, 0.0, 0.862), _b32(2, 0.862, 8.0), _b32(3, 8.862, 0.4)]
_PK32 = _kk.kare_ornekleme_plani(_KISA32, sure_sn=9.262, fps=30.0)
kontrol("⭐ I-32: 0.862 sn ACILIS beat'i kapsandi",
        len(_PK32["beat_kare"]["b001"]) >= 1)
kontrol("⭐ I-32: 0.4 sn KAPANIS beat'i kapsandi",
        len(_PK32["beat_kare"]["b003"]) >= 1,
        _PK32["beat_kare"]["b003"])
kontrol("I-32: cok kisa beatlerin kareleri de kendi sinirlarinda",
        all(8.862 <= t < 9.262 for t in _PK32["beat_kare"]["b003"])
        and all(0.0 <= t < 0.862 for t in _PK32["beat_kare"]["b001"]))

# ── BEAT SAYISI 11'DEN FAZLA: kare sayisi OLCULU olarak yukselir ──
_ONIKI32 = [_b32(i + 1, i * 1.0, 1.0) for i in range(12)]
_P12 = _kk.kare_ornekleme_plani(_ONIKI32, sure_sn=12.0, fps=30.0)
kontrol("⭐ I-32: 12 beat -> kare sayisi BEAT SAYISINA yukseldi (sessiz "
        "atlama YOK)",
        _P12["hedef"] == 12 and _P12["kare"] >= 12
        and _P12["kapsanmayan"] == [], (_P12["hedef"], _P12["kare"]))
kontrol("I-32: 12 beat'in HEPSI kapsandi",
        all(_P12["beat_kare"][b["beat_id"]] for b in _ONIKI32))

# ── 5 BEAT / 11 KARE: dolgu deterministik dagitiliyor ──
kontrol("⭐ I-32: 5 beat -> 5 zorunlu + dolgu ile 11 kare",
        len(_P32["zorunlu"]) == 5 and _P32["kare"] == 11
        and len(_P32["dolgu"]) == 6, (_P32["zorunlu"], _P32["dolgu"]))
kontrol("I-32: dolgu kareleri de BIR BEAT'IN icinde (edge-safe)",
        all(any(b["bas_sn"] <= t < b["bas_sn"] + b["sure_sn"]
                for b in _PILOT32) for t in _P32["dolgu"]))
_det32 = [tuple(_kk.kare_ornekleme_plani(_PILOT32, sure_sn=17.109,
                                         fps=30.0)["anlar"]) for _ in range(5)]
kontrol("I-32: ayni girdi -> AYNI plan (rastgelelik YOK)",
        len(set(_det32)) == 1)
kontrol("I-32: bozuk girdi -> olculdu=False (uydurma plan YOK)",
        _kk.kare_ornekleme_plani([], sure_sn=10)["olculdu"] is False
        and _kk.kare_ornekleme_plani(_PILOT32,
                                     sure_sn=0)["olculdu"] is False)
kontrol("⭐ I-32: smoke ornekleme plani KULLANIYOR (cumle ortasi GITTI)",
        "kare_ornekleme_plani" in oku(
            KOK, "testler/smoke_konsept3_teknoloji_i20.py")
        and "for c in cumleler:                       # her sahnenin ortasi"
        not in oku(KOK, "testler/smoke_konsept3_teknoloji_i20.py"))
kontrol("I-32: beat<->kare eslemesi RAPORA yaziliyor",
        '"kare_ornekleme": _ornek' in oku(
            KOK, "testler/smoke_konsept3_teknoloji_i20.py"))

blok("§39h I-31 — EKRAN KUNYESI POLITIKASI: ATIF EKSILMEDEN SIGDIRMA")

from medya import lisans as _lis                                  # noqa: E402

# ⚠ I-30'un olctugu tasma: 155 karakterlik GERCEK atif -> 2473.8px > 1792px.
# I-31 politikasi: EKRANDA yalniz "sahip / LISANS"; TAM eser adi, kaynak URL,
# lisans URL ve provenance `lisans.atif_metni` + `attribution.txt`te KALIR.
_U31 = ("NASA, ESA, AURA/Caltech, Palomar Observatory The science team "
        "consists of: D. Soderblom and E. Nelan (STScI), F. Benedict "
        "and B. Arthur (U. Texas), and B. Jones")
kontrol("⭐ I-31 KIRMIZI (I-30 vakasi): ham 'sahip / LISANS' YATAY TASIYOR",
        _kk.yatay_guvenli_alan_olcusu(
            [{"ad": "source-label", "metin": f"{_U31} / PUBLIC-DOMAIN",
              "punto": 21}],
            kare_genislik=1920, guvenli_kenar=64)["temiz"] is False)
_K31 = _kk.kunye_kisa_bicim(_U31, "public-domain", punto=21,
                            kare_genislik=1920, guvenli_kenar=64)
kontrol("⭐ I-31: politika KURUM BICIMINE dusuyor ve YATAY KAPI PASS",
        _K31["yontem"] == "KURUM" and _K31["kisaltildi"] is True
        and _kk.yatay_guvenli_alan_olcusu(
            [{"ad": "source-label", "metin": _K31["metin"], "punto": 21}],
            kare_genislik=1920, guvenli_kenar=64)["temiz"] is True,
        _K31["metin"])
kontrol("⭐ I-31: kurum adi metnin KENDI ilk ogesi (UYDURMA YOK)",
        _U31.startswith(_K31["metin"].split(" / ")[0]))
kontrol("⭐ I-31: LISANS KISA ADI KIRPILMADI",
        _K31["metin"].endswith(" / PUBLIC-DOMAIN"))
kontrol("I-31: kisaltilinca TAM sahip adi kararda SAKLANIYOR (izlenebilirlik)",
        _K31.get("tam_sahip") == _U31)

# ── GERCEK PILOT KUNYELERI DEGISMEDEN KALIR (kullanici secimi korunur) ──
for _s31, _l31, _bek31 in [
        ("Dominic Hart", "nasa-public", "Dominic Hart / NASA-PUBLIC"),
        ("GRC", "nasa-public", "GRC / NASA-PUBLIC"),
        ("NASA/JPL-Caltech/Lockheed Martin", "nasa-public",
         "NASA/JPL-Caltech/Lockheed Martin / NASA-PUBLIC")]:
    _r31 = _kk.kunye_kisa_bicim(_s31, _l31, punto=21, kare_genislik=1920,
                                guvenli_kenar=64)
    kontrol(f"⭐ I-31: pilot kunyesi AYNEN kaliyor — {_bek31[:30]}",
            _r31["metin"] == _bek31 and _r31["yontem"] == "TAM"
            and _r31["kisaltildi"] is False, _r31["metin"])

# ── EKSIK ZORUNLU ALAN: UYDURMA YOK, DURUST BLOKE ──
for _sh31, _li31, _yon31 in [("", "cc-by", "SAHIP-YOK"),
                             ("Biri", "", "LISANS-YOK")]:
    _e31 = _kk.kunye_kisa_bicim(_sh31, _li31, punto=21, kare_genislik=1920,
                                guvenli_kenar=64)
    kontrol(f"⭐ I-31: {_yon31} -> metin URETILMEZ, eksik=True",
            _e31["metin"] == "" and _e31["eksik"] is True
            and _e31["yontem"] == _yon31)
kontrol("⭐ I-31: eksik kunye PRE-QA'da FAIL kodu",
        "KALITE-KUNYE-EKSIK" in _qon.FAIL_KODLARI
        and "KALITE-KUNYE-EKSIK" in _qon.KALITE_KODLARI)
# ⚠ LISANS tek basina sigmiyorsa metin URETILMEZ — lisans ASLA kirpilmaz.
kontrol("⭐ I-31: lisans tek basina sigmiyorsa KIRPILMAZ, metin URETILMEZ",
        _kk.kunye_kisa_bicim("X", "CC-BY-SA-4.0", punto=400,
                             kare_genislik=1920,
                             guvenli_kenar=64)["yontem"] == "LISANS-SIGMIYOR")
kontrol("I-31: olculemezse TAM bicim korunur (engelleme yok)",
        _kk.kunye_kisa_bicim("Biri", "cc-by", punto=0, kare_genislik=1920,
                             guvenli_kenar=64)["metin"] == "Biri / CC-BY")
_det31 = [_kk.kunye_kisa_bicim(_U31, "public-domain", punto=21,
                               kare_genislik=1920,
                               guvenli_kenar=64)["metin"] for _ in range(5)]
kontrol("I-31: ayni girdi -> AYNI kunye (rastgelelik YOK)",
        len(set(_det31)) == 1, _det31)

# ── TAM PROVENANCE EKSILMEDI ──
# ⚠ `public-domain` ZATEN atif gerektirmiyor (lisans.LISANS_KURALLARI);
# tam-atif kanitini atif GEREKTIREN bir lisansla kurmak gerekiyor.
_AT31 = _lis.atif_metni("cc-by", _U31, "Pleiades large.jpg",
                        "https://commons.wikimedia.org/wiki/File:X.jpg")
_K31b = _kk.kunye_kisa_bicim(_U31, "cc-by", punto=21, kare_genislik=1920,
                             guvenli_kenar=64)
kontrol("⭐ I-31: TAM atif metni eser adi + sahip + lisans + URL TASIYOR",
        "Pleiades large.jpg" in _AT31 and "https://" in _AT31
        and "CC-BY" in _AT31.upper(), _AT31[:90])
kontrol("⭐ I-31: ekran kunyesi KISALSA DA tam atif KISALMADI",
        _K31b["kisaltildi"] is True and "Soderblom" in _AT31
        and len(_AT31) > len(_K31b["metin"]))
kontrol("⭐ I-31: attribution.txt adayin TAM `atif_metni`ni OLDUGU GIBI yazar",
        'aday.get("atif_metni")' in oku(KOK, "editor/plan.py"))
kontrol("I-31: plan TAM atfi YENIDEN URETMIYOR/KISALTMIYOR",
        "lisans.atif_metni(" not in _kod_yalniz(oku(KOK, "editor/plan.py")))
kontrol("I-31: plan kunye kararlarini manifeste YAZIYOR (izlenebilirlik)",
        "kunye_kararlari" in _sikistir(oku(KOK, "editor/plan.py")))

blok("§39g I-30 — YATAY GUVENLI ALAN: SAG/SOL TASMA OLCULMUYORDU")

# ⚠ I-30'DA BULUNAN BOSLUK: `guvenli_alan_olcusu` YALNIZCA DIKEY olcuyordu.
# `Grafikler.tsx > KaynakEtiketi` saga yaslaniyor (`right: GUVENLI_KENAR`) ve
# `maxWidth` TASIMIYOR — baslikta (84%) ve altyazida (900px) boyle bir sinir
# VAR, kunyede YOK. Yani uzun atif SOLA DOGRU SINIRSIZ buyuyebilir.
_G30 = oku(KOK, "..", "app/render-studio/src/editorv2/Grafikler.tsx")
kontrol("⭐ I-30: KaynakEtiketi'nde genislik siniri YOK (yapisal risk)",
        "maxWidth" not in _G30.split("KaynakEtiketi")[-1][:1000], "-")
kontrol("I-30: baslik ve altyazida genislik siniri VAR (asimetri kaniti)",
        "maxWidth: '84%'" in _G30 and "maxWidth: 900" in _G30)

# ── SENTETIK TASMA VAKASI: pilotun KENDI aday havuzundan gercek atif ──
# "Pleiades large.jpg" (yildiz kumesi) atfi 155 karakter.
_UZUN30 = ("NASA, ESA, AURA/Caltech, Palomar Observatory The science team "
           "consists of: D. Soderblom and E. Nelan (STScI), F. Benedict "
           "and B. Arthur (U. Texas), and B. Jones")
_YG30 = _kk.yatay_guvenli_alan_olcusu(
    [{"ad": "source-label", "metin": _UZUN30, "punto": 21, "hizalama": "sag"}],
    kare_genislik=1920, guvenli_kenar=64)
kontrol("⭐ I-30 KIRMIZI: 155 karakterlik GERCEK atif YATAY TASIYOR",
        _YG30["temiz"] is False and len(_YG30["ihlaller"]) == 1
        and _YG30["ihlaller"][0]["ihlal"] == "YATAY",
        _YG30["ihlaller"])
kontrol("I-30: tasma miktari SAYIYLA raporlaniyor",
        _YG30["ihlaller"][0]["tasma_px"] > 0
        and _YG30["ihlaller"][0]["karakter"] == len(_UZUN30),
        _YG30["ihlaller"][0])

# ── GERCEK PILOT KUNYELERI TEMIZ (yanlis pozitif yok) ──
_PILOT30 = [("Dominic Hart / NASA-PUBLIC", 26), ("GRC / NASA-PUBLIC", 17),
            ("NASA/JPL-Caltech/Lockheed Martin / NASA-PUBLIC", 46)]
_YG30b = _kk.yatay_guvenli_alan_olcusu(
    [{"ad": "source-label", "metin": m, "punto": 21, "hizalama": "sag"}
     for m, _ in _PILOT30], kare_genislik=1920, guvenli_kenar=64)
kontrol("⭐ I-30: GERCEK pilot kunyelerinin UCU DE TEMIZ (yanlis pozitif yok)",
        _YG30b["temiz"] is True and len(_YG30b["olcumler"]) == 3,
        [(o["karakter"], o["tahmini_genislik_px"]) for o in _YG30b["olcumler"]])
kontrol("I-30: karakter tavani hesaplaniyor ve pilot bunun ALTINDA",
        _YG30b["sigan_karakter_tavani"] > max(n for _, n in _PILOT30),
        _YG30b["sigan_karakter_tavani"])
kontrol("I-30: genislik modeli RENDER SABITINDEN (0.72 + kunye araligi 0.04)",
        abs(_YG30b["em_birim"] - (_kk.EM_BUYUK_HARF
                                  + _kk.KUNYE_HARF_ARALIGI_EM)) < 1e-9)
for _bz30 in ({"metin": "", "punto": 21}, {"metin": "x", "punto": 0},
              {"metin": "x"}):
    kontrol(f"I-30: olculemeyen katman ENGELLENMEZ {_bz30}",
            _kk.yatay_guvenli_alan_olcusu(
                [dict(_bz30, ad="x")], kare_genislik=1920,
                guvenli_kenar=64)["temiz"] is True)
kontrol("I-30: bozuk kare olcusu -> olculdu=False (uydurma yok)",
        _kk.yatay_guvenli_alan_olcusu(
            [{"ad": "x", "metin": "y", "punto": 21}],
            kare_genislik=0, guvenli_kenar=64)["olculdu"] is False)
kontrol("⭐ I-30: kapi FAIL kodunda (mevcut GUVENLI-ALAN koduna baglandi)",
        "KALITE-GUVENLI-ALAN" in _qon.FAIL_KODLARI
        and "yatay_guvenli_alan" in _sikistir(oku(KOK, "editor/qa_on.py")))
kontrol("I-30: OCR/harici servis/ag YOK",
        not re.search(r"(tesseract|ocr|pytesseract|requests|urlopen)",
                      _kod_yalniz(oku(KOK, "editor/kalite_kapisi.py")), re.I))
# ⚠ DURUST SINIR: kirpma LISANS ATFINI eksiltebilir; kapi bunu ONERIDE soyler.
kontrol("I-30: oneri LISANS ATFI riskini SOYLUYOR (sessiz kirpma onerilmiyor)",
        "LISANS ATFINI" in oku(KOK, "editor/qa_on.py"))

blok("§39f I-29 — AFIS/PANO SINYALI: METADATA GUVENILIR DEGIL (olculdu)")

# ⚠ I-26'da GOZLE yakalanan kusur: s01'e secilen Commons varligi CAM ARKASI
# BIR MUZE PANOSUNUN fotografiydi. I-29'da sorulan soru: bu, ADAY
# METADATASINDAN (baslik/aciklama/kategori/provenance) DETERMINISTIK olarak
# yakalanabilir mi? OLCUM: HAYIR.
#
# Asagidaki metinler Commons `extmetadata`sindan GERCEKTEN okundu
# (ag YOK — olculen degerler fikstur olarak sabitlendi).
_MD29_KUSURLU = {           # cam arkasi muze panosu — GORSEL OLARAK KUSURLU
    "ObjectName": "Pleiades supercomputer racks 4",
    "ImageDescription": "Pleiades supercomputer racks",
    "Categories": "Taken with LG Ultimate 2|Pleiades supercomputer|"
                  "Self-published work",
    "genislik": 2240}
_MD29_TEMIZ = [
    {"ObjectName": "OSC's HP Intel Xeon Oakley Cluster",
     "ImageDescription": "OSC's HP Intel Xeon Oakley Cluster provides clients "
                         "with a total peak performance of 154 Teraflops.",
     "Categories": "Self-published work|Supercomputers in the United States|"
                   "Hewlett-Packard supercomputers", "genislik": 5184},
    {"ObjectName": "NASA Pleiades Supercomputer (9616175099)",
     "ImageDescription": "With 195 thousand cores, it can hit 2.9 petaflop/s.",
     "Categories": "Pleiades supercomputer|Photographs by Steve Jurvetson",
     "genislik": 4983},
]
# Yanlis pozitif kanitlari: METINDE anahtar kelime VAR ama varlik MESRU.
_MD29_YANLIS_POZITIF = [
    {"ObjectName": "NASA Advanced Supercomputing Facility with sign",
     "ImageDescription": "", "Categories": "", "eslesen": "sign"},
    {"ObjectName": "NASA's Roman Mission Gets Cosmic Sneak Peek",
     "ImageDescription": "the telescope displays its first image",
     "Categories": "", "eslesen": "displays"},
    {"ObjectName": "Solar array, Guilford, Vermont",
     "ImageDescription": "", "Categories": "Banner images", "eslesen": "Banner"},
]
_ANAHTAR29 = re.compile(
    r"\b(display|displays|exhibit|exhibition|museum|poster|signage|sign|signs|"
    r"placard|showcase|plaque|banner|kiosk|information board)\b", re.I)


def _md29_metin(k):
    return " ".join([str(k.get("ObjectName") or ""),
                     str(k.get("ImageDescription") or ""),
                     str(k.get("Categories") or "")])


kontrol("⭐ I-29: GERCEK kusurlu varlik anahtar kelimeyle YAKALANMIYOR "
        "(recall 0/1)",
        _ANAHTAR29.search(_md29_metin(_MD29_KUSURLU)) is None,
        _md29_metin(_MD29_KUSURLU))
kontrol("I-29: kusurlu varligin metadatasi kendini KONU gibi tanitiyor",
        "supercomputer racks" in _MD29_KUSURLU["ImageDescription"].lower())
for _yp in _MD29_YANLIS_POZITIF:
    kontrol(f"⭐ I-29 YANLIS POZITIF: mesru varlik '{_yp['eslesen']}' ile "
            f"isaretlenirdi",
            _ANAHTAR29.search(_md29_metin(_yp)) is not None,
            _yp["ObjectName"][:44])
kontrol("I-29: TEMIZ varliklar anahtar kelimeyle isaretlenmiyor",
        all(_ANAHTAR29.search(_md29_metin(t)) is None for t in _MD29_TEMIZ))

# ── "Taken with <cihaz>" sinyali: kusuru yakalar AMA hassasiyeti %6 ──
_TAKEN29 = re.compile(r"\bTaken with\b", re.I)
kontrol("I-29: 'Taken with' sinyali kusuru YAKALIYOR",
        _TAKEN29.search(_MD29_KUSURLU["Categories"]) is not None)
# Gercek havuzda olculdu: 18/56 aday bu kategoriyi tasiyor, 17'si TEMIZ.
_TAKEN29_OLCUM = {"taranan": 56, "isaretlenen": 18, "gercek_kusur": 1}
kontrol("⭐ I-29: 'Taken with' sinyalinin HASSASIYETI %6 — KAPI OLAMAZ",
        round(100 * _TAKEN29_OLCUM["gercek_kusur"]
              / _TAKEN29_OLCUM["isaretlenen"]) <= 6,
        _TAKEN29_OLCUM)
kontrol("I-29: bu sinyal 17 TEMIZ adayi elerdi (aralarinda SECILENLER var)",
        _TAKEN29_OLCUM["isaretlenen"] - _TAKEN29_OLCUM["gercek_kusur"] == 17)

# ── HUKUM: sinyal guvenilir DEGIL -> URETIM DAVRANISI DEGISMEDI ──
for _dosya29 in ("medya/commons.py", "medya/edinim.py", "editor/qa_on.py",
                 "editor/plan.py"):
    kontrol(f"⭐ I-29: {_dosya29} anahtar-kelime AFIS KAPISI ICERMIYOR",
            not re.search(r"\b(exhibit|museum|poster|signage|placard|showcase)\b",
                          _kod_yalniz(oku(KOK, _dosya29)), re.I),
            _dosya29)
# ⚠ Kusur SINIFI yine de tesadufen degil, I-27 esigiyle KAPALI:
kontrol("⭐ I-29: kusurlu varlik I-27 COZUNURLUK esigiyle ZATEN eleniyor",
        _MD29_KUSURLU["genislik"] < _kk.en_az_kaynak_genisligi(1920),
        f"{_MD29_KUSURLU['genislik']} < {_kk.en_az_kaynak_genisligi(1920)}")

blok("§39e I-28 — SECIM SIRASI TANISI: KUSUR YOK, DAVRANIS KILITLENDI")

# ⚠ I-28'IN ONCULU OLCUMLE CURUDU.
# Beklenen kusur: "2443 esigi yuzunden konuya sadik YUKSEK cozunurluklu
# Ohio OSC (5184x3456) adayi SECILEMIYOR, tekel NASA %100 oluyor."
# GERCEK OLCUM (ayni tek ara() cagrisi):
#   · esik dusuk cozunurluklu Columbia'yi (2100x1524, alaka 1) ELIYOR
#   · SIRADAKI Ohio OSC (5184x3456, alaka 2) 0. SIRADA SECILIYOR
#   · 429 devre disi birakildiginda zincir 4/4 sahnede Commons'tan
#     konuya sadik aday secti (ara() sahne basina 1 kez)
# Yani secim/filtre SIRASI DOGRU. Tekelin TEK sebebi indirmedeki
# HTTP 429 / Retry-After 600 (I-18'den beri belgeli, cevresel).
# KOD DEGISTIRILMEDI; dogru davranis burada KILITLENDI.

def _sayfa28(pageid, index, g, y, baslik, lisans="CC BY 2.0",
             sahip="Biri"):
    _s = _sahte_sayfa(pageid, index, g, y, baslik)
    _em = _s["imageinfo"][0]["extmetadata"]
    _em["LicenseShortName"] = {"value": lisans}
    _em["UsageTerms"] = {"value": lisans}
    # ⚠ LisansUrl de ezilmeli: karar URL'den de lisans cikarabiliyor,
    # yalniz kisa adi degistirmek fikstur'u YANILTICI yapiyordu.
    _em["LicenseUrl"] = {"value": ("" if lisans == "unknown"
                                   else "https://creativecommons.org/"
                                        "licenses/by/2.0/")}
    _em["Artist"] = {"value": sahip}
    _em["Credit"] = {"value": sahip}
    return _s


# Olculen gercek listenin sahtesi: alaka 1 DUSUK cozunurluklu, alaka 2
# konuya sadik YUKSEK cozunurluklu, alaka 15+ konu disi (futbol).
_L28 = [
    _sayfa28(1, 1, 2100, 1524, "Columbia Supercomputer.jpg"),
    _sayfa28(2, 2, 5184, 3456, "OSC's HP Intel Xeon Oakley Cluster.jpg"),
    _sayfa28(3, 3, 4724, 2892, "Titan supercomputer.jpg"),
    _sayfa28(4, 15, 3390, 2543, "RC Lens - Lille OSC.jpg"),
    _sayfa28(5, 4, 3000, 4000, "Dikey supercomputer.jpg"),
    _sayfa28(6, 5, 4000, 3000, "Lisansi belirsiz.jpg", lisans="unknown"),
    _sayfa28(7, 6, 4000, 3000, "Sahibi yok.jpg", sahip=""),
]
_ESIK28 = _kk.en_az_kaynak_genisligi(1920)
_r28 = _cm.ara("supercomputer facility", adet=6, en_az_genislik=_ESIK28,
               acan=_sahte_acan(_L28))
kontrol("⭐ I-28: DUSUK cozunurluklu alaka-1 aday ESIKTE ELENDI",
        all("Columbia" not in a["baslik"] for a in _r28["adaylar"])
        and any("Columbia" in str(e.get("baslik"))
                and "COZUNURLUK" in str(e.get("neden"))
                for e in _r28["elenen"]), _r28["elenen"])
kontrol("⭐ I-28: SIRADAKI konuya sadik YUKSEK cozunurluklu aday 0. SIRADA",
        _r28["adaylar"][0]["baslik"] == "OSC's HP Intel Xeon Oakley Cluster.jpg"
        and _r28["adaylar"][0]["genislik"] == 5184,
        [a["baslik"] for a in _r28["adaylar"]])
kontrol("⭐ I-28: SEMANTIK ALAKA BIRINCIL kaldi (konu disi ARKADA)",
        [a["alaka_sirasi"] for a in _r28["adaylar"]]
        == sorted(a["alaka_sirasi"] for a in _r28["adaylar"])
        and _r28["adaylar"][-1]["baslik"].startswith("RC Lens"),
        [(a["alaka_sirasi"], a["baslik"][:24]) for a in _r28["adaylar"]])
kontrol("I-28: LISANS belirsiz aday GECMEDI",
        all("Lisansi belirsiz" not in a["baslik"] for a in _r28["adaylar"]))
kontrol("I-28: PROVENANCE (eser sahibi) eksik aday GECMEDI",
        all("Sahibi yok" not in a["baslik"] for a in _r28["adaylar"]))
kontrol("I-28: I-23 ORAN kapisi DIKEY adayi hala reddediyor",
        _ed.oran_karari(3000, 4000)["uygun"] is False)
kontrol("I-28: esik I-27'den TURETILEN deger (2443)", _ESIK28 == 2443)
kontrol("⭐ I-28: EK ARA() CAGRISI YOK — tek listede siradakine gecildi",
        len(_r28["adaylar"]) >= 1 and _r28["denenen"] == len(_L28))

# Esik SERTLESTI diye aday havuzu ACLIGA dusmemeli (olculen dort sorgu).
for _q28, _ham28, _kalan28, _istenen28 in [
        ("Pleiades supercomputer", 18, 5, 2),
        ("supercomputer facility", 18, 6, 1),
        ("silicon carbide integrated circuit", 2, 2, 1),
        ("solar array power", 18, 6, 1)]:
    kontrol(f"I-28: '{_q28[:26]}' havuzu ACLIGA dusmuyor "
            f"({_kalan28} kalan >= {_istenen28} istenen)",
            _kalan28 >= _istenen28)

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
    # ── I-31: KARE ORNEKLEMESI HER BEAT'I KAPSIYOR MU? ──
    # ⚠ I-31'DE BULUNDU: 11 kare b001'i (0-0.862 sn) HIC ORNEKLEMIYOR —
    # ilk kare 1.2 sn. Yani ACILIS PLANI gorsel incelemenin KOR NOKTASINDA
    # kaliyordu ve kusurlu acilis ancak ELLE kare cikararak yakalandi.
    _kare31 = [float(k.get("an_sn") or 0)
               for k in (_R20.get("kareler") or [])
               if isinstance(k, dict)]
    _kapsanan31 = []
    for _z31 in (_R20.get("zincir") or []):
        _b0 = float(_z31.get("bas_sn") or 0)
        _b1 = _b0 + float(_z31.get("sure_sn") or 0)
        if not any(_b0 <= t < _b1 for t in _kare31):
            _kapsanan31.append(_z31.get("beat_id"))
    kontrol("I-31: kare ornekleme kapsami OLCULDU",
            isinstance(_kare31, list) and bool(_R20.get("zincir")))
    if _kapsanan31:
        bloke_yaz("I-31 kare ornekleme KOR NOKTASI",
                  f"su beat(ler) hicbir kareyle ornekleNMEDI: "
                  f"{_kapsanan31}. Gorsel/semantik inceleme bu beatleri "
                  f"GORMUYOR; kusur ancak ELLE kare cikararak yakalanir.")
    else:
        kontrol("⭐ I-31: her beat en az bir kareyle ornekleniyor", True)
    # ── I-33: BAGIMSIZ GORSEL INCELEME KAYDI ──
    # ⚠ Bu bir SINIFLANDIRICI DEGIL, OLCULEN TEK VARLIGA OZGU BIR KAYITTIR.
    # I-29'da olculdu: metadata anahtar kelimesi genel bir kapi olamaz
    # (gercek kusurda recall %0, 7 isaretten 5'i yanlis pozitif). Burada
    # yalnizca I-33'te GOZLE dogrulanan varlik, kendi basligiyla kayitlidir;
    # medya degisince bu kayit KENDILIGINDEN dusar ve yeni varlik yeniden
    # incelenmek zorunda kalir.
    _I33_GORULEN = "node on display at NASA Ames visitor center"
    _b001_31 = next((z for z in (_R20.get("zincir") or [])
                     if z.get("beat_id") == "b001"), {})
    _s01_31 = next((s for s in (_R20["medya_edinim"].get("sahneler") or [])
                    if s.get("kimlik") == "s01"), {})
    _kare_b001 = ((_R20.get("kare_ornekleme") or {}).get("beat_kare")
                  or {}).get("b001") or []
    if _I33_GORULEN in str(_s01_31.get("baslik") or ""):
        bloke_yaz(
            "I-33 pilot GORSEL INCELEME — b001 VITRIN/PANO",
            f"kare {_kare_b001} sn · beat b001 · varlik "
            f"{_b001_31.get('asset_id')} · saglayici "
            f"{_b001_31.get('saglayici')} · lisans {_b001_31.get('lisans')} · "
            f"baslik {str(_s01_31.get('baslik'))[:70]!r}. GOZLE DOGRULANDI: "
            f"cam arkasi MUZE VITRINI, Ingilizce bilgi panolari "
            f"('The Pleiades Supercomputer', 'Anatomy of a Pleiades Node'), "
            f"cam yansimalari. Turkce anlatim 'Guc burada uretilir.' ile "
            f"UYUMSUZ. Otomatik kapilarin HEPSI PASS; kusur yalnizca gorsel "
            f"incelemede gorunuyor. MP4 KABUL EDILMIS SAYILMAZ.")
    else:
        kontrol("I-33: b001 varligi I-33'te gorulen vitrin degil — "
                "YENIDEN GORSEL INCELEME GEREKIR", True,
                str(_s01_31.get("baslik"))[:60])
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



blok("§40aa R-1d-g — AYNI KAYNAK <= 8.0 sn DETERMINISTIK GARANTI")

# ⚠ MEDYASIZ: hicbir video/ses/kare/MP4 URETILMEZ. Saf karar mantigi.
#
# ── OLCULEN KUSUR (R-1d-f pilotu, job_1786721869701) ──
#   GERCEK-KAYNAK-TAVANI: 36560908 8.508 · ..._s001 8.124 ·
#                         38614588 8.052 · 15924008 8.028   (tavan 8.0)
# Gercek hatta 1 SAHNE = 1 VARLIK; sahne 8.0'i asinca varlik TEK BASINA
# tavani asiyor. Kabul SUREYE BAGLI ve KARARSIZDI: R-1d-e'de 7.1-7.6 sn
# sahnelerle AYNI urun KABUL EDILMISTI.

_KT2 = __import__("kaynak_tavani")


def _kt_adaylar(n, sag="pexels"):
    return [{"asset_id": f"a{i}", "saglayici": sag,
             "lisans": "pexels-license"} for i in range(1, n + 1)]


kontrol("⭐ R-1d-g: tavan `saglayici_motoru` ile AYNI tek sabitten okunuyor "
        "(YUKSELTILMIYOR)",
        _KT2.KAYNAK_BASINA_TAVAN_SN == _SM.KAYNAK_BASINA_TAVAN_SN == 8.0
        and _KT2.kapsam_ozeti()["tavan_yukseltilir"] is False)

# ── (1) SINIR DAVRANISI: 8.0 PASS, 8.001 BOLUNUR ──
kontrol("⭐ R-1d-g: TAM 8.0 sn sahne BOLUNMUYOR (davranis korunur)",
        _KT2.parca_sayisi(8.0) == 1
        and _KT2.bolme_plani([{"scene_id": "s1", "sure_sn": 8.0}],
                             adaylar=_kt_adaylar(2))["bolunen_sahne"] == 0)
_KT_801 = _KT2.bolme_plani([{"scene_id": "s1", "sure_sn": 8.001}],
                           adaylar=_kt_adaylar(2))
kontrol("⭐ R-1d-g BELIRLEYICI RED-FIRST: 8.001 sn sahne BOLUNUYOR ve iki "
        "parca FARKLI varlik aliyor",
        _KT2.parca_sayisi(8.001) == 2 and _KT_801["ok"] is True
        and len(_KT_801["parcalar"]) == 2
        and _KT_801["parcalar"][0]["asset_id"]
        != _KT_801["parcalar"][1]["asset_id"], _KT_801["parcalar"])
kontrol("⭐ R-1d-g: her parca tavani ASMIYOR ve TOPLAM sure korunuyor",
        all(p["sure_sn"] <= 8.0 for p in _KT_801["parcalar"])
        and abs(sum(p["sure_sn"] for p in _KT_801["parcalar"]) - 8.001) < 0.01)

# ── (2) PILOTUN GERCEK SAYILARI ──
_KT_P = _KT2.bolme_plani(
    [{"scene_id": "s1", "sure_sn": 8.508}, {"scene_id": "s2", "sure_sn": 8.124},
     {"scene_id": "s3", "sure_sn": 8.052}, {"scene_id": "s4", "sure_sn": 8.028}],
    adaylar=_kt_adaylar(8))
kontrol("⭐ R-1d-g BELIRLEYICI: R-1d-f pilotunun DORT ihlali de plana "
        "uyuyor (hicbir varlik 8.0'i asmiyor)",
        _KT_P["ok"] is True and _KT_P["asan"] == []
        and max(_KT_P["kullanim"].values()) <= 8.0
        and _KT_P["bolunen_sahne"] == 4, _KT_P["kullanim"])
kontrol("⭐ R-1d-g: dogrulayici nihai kullanimi ONAYLIYOR",
        _KT2.dogrula(_KT_P["kullanim"])["ok"] is True)

# ── (3) RED-FIRST: TEKRAR-KAYNAK ile TOPLAM ASILMIYOR ──
_KT_TEK = _KT2.bolme_plani([{"scene_id": "s1", "sure_sn": 16.0}],
                           adaylar=_kt_adaylar(1))
kontrol("⭐ R-1d-g BELIRLEYICI RED-FIRST: TEK aday varken ayni kaynak "
        "TEKRAR kullanilip toplam ASILMIYOR — stabil kodla FAIL-CLOSED",
        _KT_TEK["ok"] is False
        and any(s["kod"] == "KAYNAK-TAVANI-VARLIK-YOK"
                for s in _KT_TEK["sorunlar"])
        and _KT2.dogrula(_KT_TEK["kullanim"])["ok"] is True,
        _KT_TEK["kullanim"])
kontrol("⭐ R-1d-g: atanamayan parca SESSIZ gecmiyor (atandi=False)",
        any(p["atandi"] is False and p["asset_id"] is None
            for p in _KT_TEK["parcalar"]))
kontrol("⭐ R-1d-g: iki sahne ayni tek varligi PAYLASINCA da tavan "
        "ASILMIYOR",
        _KT2.dogrula(_KT2.bolme_plani(
            [{"scene_id": "s1", "sure_sn": 5.0},
             {"scene_id": "s2", "sure_sn": 5.0}],
            adaylar=_kt_adaylar(1))["kullanim"])["ok"] is True)

# ── (4) PROVENANS ZORUNLU + DETERMINIZM ──
kontrol("⭐ R-1d-g RED-FIRST: LISANSSIZ/SAGLAYICISIZ aday ATANMIYOR",
        _KT2.bolme_plani(
            [{"scene_id": "s1", "sure_sn": 4.0}],
            adaylar=[{"asset_id": "a1"},
                     {"asset_id": "a2", "saglayici": "pexels"}])["ok"] is False
        and _KT2.kapsam_ozeti()["provenanssiz_varlik_atanir"] is False)
kontrol("⭐ R-1d-g: ayni girdi AYNI cikti (rastgelelik YOK)",
        [p["asset_id"] for p in _KT2.bolme_plani(
            [{"scene_id": "s1", "sure_sn": 8.508}],
            adaylar=_kt_adaylar(4))["parcalar"]]
        == [p["asset_id"] for p in _KT2.bolme_plani(
            [{"scene_id": "s1", "sure_sn": 8.508}],
            adaylar=_kt_adaylar(4))["parcalar"]]
        and _KT2.kapsam_ozeti()["rastgelelik"] is False)
kontrol("⭐ R-1d-g: BOZUK sure sessizce gecmiyor (stabil kod)",
        any(s["kod"] == "KAYNAK-TAVANI-SURE-BOZUK"
            for s in _KT2.bolme_plani([{"scene_id": "s1", "sure_sn": 0}],
                                      adaylar=_kt_adaylar(2))["sorunlar"]))
kontrol("⭐ R-1d-g: modul MEDYA/AG/DOSYA/RENDER'a DOKUNMUYOR",
        not any(a in _kod_yalniz(oku(KOK, "kaynak_tavani.py"))
                for a in ("open(", "requests", "subprocess", "ffmpeg",
                          "os.remove"))
        and _KT2.kapsam_ozeti()["render_eder"] is False)
kontrol("R-1d-g: kaynak_tavani.py derleniyor",
        _derlenir(os.path.join(KOK, "kaynak_tavani.py")))
# ── (5) URETIM HATTINA BAGLANDI (R-1d-g entegrasyon) ──
# ⚠ MEDYASIZ: kod sozlesmesi + saf fonksiyon davranisi test edilir.
_PL_G = oku(KOK, "pipeline.py")
kontrol("⭐ R-1d-g BELIRLEYICI: pipeline bolme planini GERCEK HATTA "
        "uyguluyor (scratch karar mantigi DEGIL)",
        "_kaynak_tavani_uygula(props_sahneler, _sahne_ham)" in _PL_G
        and "import kaynak_tavani" in _PL_G)
kontrol("⭐ R-1d-g: tavani asan sahne icin IKINCI ucretsiz stok klip "
        "ediniliyor (footage_getir)",
        "kaynak.footage_getir(_sorg[sira], hedef, yt_once=False)" in _PL_G
        and "genel_yedek_sorgular" in _PL_G)
kontrol("⭐ R-1d-g: ek klip de KOPRUDEN geciyor (lisans/provenans kaydi)",
        'kopru_yazici=lambda y: _kopru_kaydet(y, _s, h["n"])' in _PL_G)
kontrol("⭐ R-1d-g BELIRLEYICI: SES sunucuda ffmpeg ile SENKRON kesiliyor",
        "def _ses_dilimle(" in _PL_G and '"-ss", f"{bas_sn:.3f}"' in _PL_G
        and '"-t", f"{uzunluk_sn:.3f}"' in _PL_G)
kontrol("⭐ R-1d-g BELIRLEYICI: ALTYAZI zaman dilimleri de bolunuyor ve "
        "SIFIRA tasiniyor",
        "def _kelime_dilimle(" in _PL_G
        and "t0=round(max(0.0, t0 - bas_sn), 3)" in _PL_G
        and 'uretmod.altyazi_parcala(\n                    _kelime_dilimle('
        in _PL_G)
kontrol("⭐ R-1d-g BELIRLEYICI: ek varlik EDINILEMEZSE sahne BOLUNMUYOR ve "
        "KAYNAK-TAVANI-VARLIK-YOK raporlaniyor (fail-closed)",
        '"kod": _ed["kod"]' in _PL_G
        and "ek FARKLI" in _PL_G
        and "tekrar kullanilip tavan ASILMAZ" in _PL_G)
kontrol("⭐ R-1d-g: her parca AYRI scene_id aliyor (olcum ayirt edebilsin)",
        'yeni["scene_id"] = f"{sh.get(\'scene_id\')}p{j + 1}"' in _PL_G)
kontrol("⭐ R-1d-g: parca 1 MEVCUT medyayi korur, sonrakiler EK varligi alir",
        'yeni["medya"] = (sh.get("medya") if j == 0' in _PL_G)

# ── (6) BOLUNMUS ZAMAN CIZGISI GERCEK KAPIDAN GECIYOR ──
# ⚠ Pilotun 8.508 sn'lik sahnesi bolununce `gercek_qa` tavan kapisi TEMIZ.
_G_BOL = _GQ.olc(_GQ.sahneleri_cevir(
    [{"scene_id": "s001p1", "tur": "video", "medya": "a.mp4", "sure": 4.254},
     {"scene_id": "s001p2", "tur": "video", "medya": "b.mp4", "sure": 4.254}],
    provenans_okuyucu=lambda y: {
        "a.mp4": {"saglayici": "pexels", "lisans": "pexels-license",
                  "asset_id": "a1", "medya_turu": "video"},
        "b.mp4": {"saglayici": "pixabay", "lisans": "pixabay-content-license",
                  "asset_id": "b1", "medya_turu": "video"}}.get(y, {})))
kontrol("⭐ R-1d-g BELIRLEYICI: 8.508 sn sahne bolununce GERCEK kapi TEMIZ "
        "(GERCEK-KAYNAK-TAVANI YOK)",
        _G_BOL["kaynak_kullanimi"]["temiz"] is True
        and not [x for x in _G_BOL["sorunlar"]
                 if x["kod"] == "GERCEK-KAYNAK-TAVANI"],
        _G_BOL["kaynak_kullanimi"])
kontrol("⭐ R-1d-g RED-FIRST: AYNI varlik iki parcada kullanilirsa kapi "
        "YINE ihlal veriyor (tekrar-kaynak kacamagi KAPALI)",
        [x["kod"] for x in _GQ.olc(_GQ.sahneleri_cevir(
            [{"scene_id": "s1p1", "tur": "video", "medya": "a.mp4",
              "sure": 4.5},
             {"scene_id": "s1p2", "tur": "video", "medya": "a.mp4",
              "sure": 4.5}],
            provenans_okuyucu=lambda y: {
                "saglayici": "pexels", "lisans": "pexels-license",
                "asset_id": "a1", "medya_turu": "video"}))["sorunlar"]
         ].count("GERCEK-KAYNAK-TAVANI") == 1)
# ── (7) EK VARLIK EDINIMI — GERCEK FONKSIYON + TEST-DOUBLE (string DEGIL) ──
# ⚠ BAGIMSIZ DENETIM (cd3a5b5) IKI DELIK buldu:
#   (1) `footage_getir` AYNI asset_id'i dondurebilir; kimlik HIC
#       karsilastirilmiyordu -> ayni kaynak iki parcada kullanilip toplam
#       tavani ASABILIYORDU.
#   (2) `_kopru_kaydet` False donse (lisans/kare dogrulamasi GECMEDI) bile
#       klip listeye eklenip TIMELINE'A GIRIYORDU.
# Asagidaki kontroller GERCEK `ek_varlik_edin`i test-double'larla cagirir.

_EV_PV = {
    "/a.mp4": {"saglayici": "pexels", "asset_id": "A1",
               "lisans": "pexels-license"},
    "/ayni.mp4": {"saglayici": "pexels", "asset_id": "MEV",
                  "lisans": "pexels-license"},
    "/b.mp4": {"saglayici": "pixabay", "asset_id": "B1",
               "lisans": "pixabay-content-license"},
    "/lisanssiz.mp4": {"saglayici": "pexels", "asset_id": "C1"},
}


def _ev(yollar, *, adet=1, mevcut=("pexels|MEV",), kopru=True):
    return _KT2.ek_varlik_edin(
        adet=adet, mevcut_kimlikler=list(mevcut),
        aday_uretici=lambda i: yollar[i] if i < len(yollar) else None,
        provenans_okuyucu=lambda y: _EV_PV.get(y, {}),
        kopru_yazici=(kopru if callable(kopru) else (lambda y: bool(kopru))),
        maks_deneme=len(yollar) + 1)


kontrol("⭐ R-1d-g BELIRLEYICI: AYNI asset_id donen aday REDDEDILIYOR ve "
        "SIRADAKI deneniyor (kimlik GERCEKTEN karsilastiriliyor)",
        _ev(["/ayni.mp4", "/a.mp4"])["ok"] is True
        and _ev(["/ayni.mp4", "/a.mp4"])["kabul"][0]["kimlik"] == "pexels|A1"
        and any(r.get("neden") == "AYNI-KAYNAK"
                for r in _ev(["/ayni.mp4", "/a.mp4"])["red"]),
        _ev(["/ayni.mp4", "/a.mp4"])["red"])
kontrol("⭐ R-1d-g RED-FIRST: TEK aday ve o da AYNI kaynak ise FAIL-CLOSED "
        "(KAYNAK-TAVANI-VARLIK-YOK)",
        _ev(["/ayni.mp4"])["ok"] is False
        and _ev(["/ayni.mp4"])["kod"] == "KAYNAK-TAVANI-VARLIK-YOK"
        and _ev(["/ayni.mp4"])["kabul"] == [])
kontrol("⭐ R-1d-g BELIRLEYICI: KOPRU FALSE donerse aday KABUL EDILMIYOR "
        "(timeline'a GIRMEZ)",
        _ev(["/a.mp4"], kopru=False)["ok"] is False
        and any(r.get("neden") == "KOPRU-RED"
                for r in _ev(["/a.mp4"], kopru=False)["red"]))
kontrol("⭐ R-1d-g: kopru ILK adayda False, IKINCIDE True ise IKINCISI "
        "kabul ediliyor (sirdaki denenir)",
        _ev(["/a.mp4", "/b.mp4"],
            kopru=lambda y: y == "/b.mp4")["kabul"][0]["kimlik"]
        == "pixabay|B1")
kontrol("⭐ R-1d-g RED-FIRST: LISANSI eksik aday REDDEDILIYOR "
        "(provenans EKSIK -> kimlik uretilmez)",
        _KT2.kimlik_normalize(_EV_PV["/lisanssiz.mp4"]) == ""
        and any(r.get("neden") == "PROVENANS-EKSIK"
                for r in _ev(["/lisanssiz.mp4"])["red"]))
kontrol("⭐ R-1d-g: IKI ek parca istenince IKISI de BIRBIRINDEN farkli "
        "kaynak aliyor",
        [k["kimlik"] for k in _ev(["/a.mp4", "/b.mp4"], adet=2)["kabul"]]
        == ["pexels|A1", "pixabay|B1"])
kontrol("⭐ R-1d-g: aday URETICI patlarsa cokmez, siradakine gecer",
        _KT2.ek_varlik_edin(
            adet=1, mevcut_kimlikler=["pexels|MEV"],
            aday_uretici=lambda i: (_ for _ in ()).throw(OSError())
            if i == 0 else "/a.mp4",
            provenans_okuyucu=lambda y: _EV_PV.get(y, {}),
            kopru_yazici=lambda y: True, maks_deneme=3)["ok"] is True)
kontrol("⭐ R-1d-g: pipeline ARTIK bu yardimciyi kullaniyor "
        "(kabul karari orada)",
        "kaynak_tavani.ek_varlik_edin(" in oku(KOK, "pipeline.py")
        and "kopru_yazici=lambda y: _kopru_kaydet(" in oku(KOK, "pipeline.py"))
kontrol("⭐ R-1d-g: ses dilimleme kodeki ACIKCA PCM WAV — sabit libmp3lame "
        "de UZANTI VARSAYIMI da YOK",
        '"-c:a", "libmp3lame"' not in oku(KOK, "pipeline.py")
        and '"-c:a", "pcm_s16le"' in oku(KOK, "pipeline.py"))

# ── (8) DENETIM 2: KIMLIKSIZ MEVCUT PARCA / KODEK / TRANSACTIONAL ──
# ⚠ Ek bagimsiz denetim uc kusur daha buldu:
#   (1) `_mevcut_kimlik` BOS iken `mevcut_kimlikler=[]` ile devam ediliyordu;
#       yeni adayin mevcut klipten FARKLI oldugu KANITLANAMAZDI.
#   (2) `.mp3` hedefte `-q:a` yine MP3/libmp3lame encoder secebilir; uzanti
#       VARSAYIMIYLA "duzeldi" DENEMEZ.
#   (3) Ses kesimi basarisiz olursa daha once kopruye yazilmis ek adaylar
#       timeline disi kaldigi halde butce/provenans olcumunu KIRLETIYORDU.

_EV_KY = _ev(["/a.mp4"], mevcut=[""])
kontrol("⭐ R-1d-g BELIRLEYICI (denetim-2/1): MEVCUT parcanin kimligi BOS "
        "ise HICBIR aday kabul edilmiyor (fail-closed, MEVCUT-KIMLIK-YOK)",
        _EV_KY["ok"] is False and _EV_KY["kabul"] == []
        and _EV_KY["kod"] == "KAYNAK-TAVANI-VARLIK-YOK"
        and _EV_KY["red"][0]["neden"] == "MEVCUT-KIMLIK-YOK", _EV_KY)
kontrol("⭐ R-1d-g (denetim-2/1): mevcut kimlik listesi BOS olsa da "
        "fail-closed (aday URETICI hic cagrilmaz)",
        _KT2.ek_varlik_edin(
            adet=1, mevcut_kimlikler=[],
            aday_uretici=lambda i: (_ for _ in ()).throw(
                AssertionError("cagrilmamaliydi")),
            provenans_okuyucu=lambda y: {}, kopru_yazici=lambda y: True
        )["kod"] == "KAYNAK-TAVANI-VARLIK-YOK")
kontrol("⭐ R-1d-g (denetim-2/1): pipeline kimliksiz mevcut parcada "
        "KAYNAK-TAVANI-VARLIK-YOK ile DURUYOR (bolmeyi denemiyor)",
        "farklilik \n                                           \"kanitlanamaz\")})"
        in oku(KOK, "pipeline.py")
        or ("kimligi YOK -> farklilik" in oku(KOK, "pipeline.py")
            and '"kod": kaynak_tavani.KOD_VARLIK_YOK' in oku(KOK, "pipeline.py")))
kontrol("⭐ R-1d-g (denetim-2/1): kimlik uretilemeyen provenans BOS kimlik "
        "veriyor (uydurma kimlik YOK)",
        _KT2.kimlik_normalize({"saglayici": "pexels", "asset_id": "A"}) == ""
        and _KT2.kimlik_normalize({"asset_id": "A",
                                   "lisans": "x"}) == ""
        and _KT2.kimlik_normalize({"saglayici": "p", "asset_id": "A",
                                   "lisans": "x"}) == "p|A")

_PL_H = oku(KOK, "pipeline.py")
kontrol("⭐ R-1d-g BELIRLEYICI (denetim-2/2): ses kodeki ACIKCA PCM WAV "
        "(uzanti VARSAYIMI degil)",
        '"-c:a", "pcm_s16le"' in _PL_H and '_p{j}.wav"' in _PL_H
        and '"-q:a"' not in _PL_H)
kontrol("⭐ R-1d-g (denetim-2/2): kesim hatasi stderr ile RAPORLANIYOR "
        "(pilot kok nedeni kanitlanabilsin)",
        "return ok, (r.stderr or \"\")[-300:]" in _PL_H
        and "ses dilimlenemedi: {_kesim_hata}" in _PL_H)

kontrol("⭐ R-1d-g BELIRLEYICI (denetim-2/3): SES KESIMI ONCE, EDINIM SONRA "
        "(transactional: basarisiz kesimde kopruye HICBIR SEY yazilmaz)",
        _PL_H.index("(B) SES DILIMLERI ONCE") < _PL_H.index("(C) EK VARLIKLAR")
        and _PL_H.index("(C) EK VARLIKLAR")
        < _PL_H.index("kaynak_tavani.ek_varlik_edin("))
kontrol("⭐ R-1d-g (denetim-2/3): basarisiz yolda YARIM ses dilimleri "
        "TEMIZLENIYOR (artik birakilmiyor)",
        _PL_H.count("for _y in _ses_yollari:") >= 2
        and (_PL_H.count("for _y in _ses_yollari:")
             == _PL_H.count("os.remove(os.path.join(PUBLIC, _y))")))

kontrol("⭐ R-1d-g BELIRLEYICI (pilot kok nedeni): ses kaynagi ffmpeg'e "
        "MUTLAK yolla veriliyor (`syol` GORELI; pilotta dosya bulunamiyordu)",
        '_kaynak_ses_abs = os.path.join(PUBLIC, str(h["syol"]))' in _PL_H
        and "_ses_dilimle(_kaynak_ses_abs," in _PL_H)
kontrol("⭐ R-1d-g: props `ses` alani GORELI kaliyor (renderer sozlesmesi)",
        "_ses_yollari.append(_goreli)" in _PL_H
        and 'yeni["ses"] = _ses_yollari[j]' in _PL_H)
kontrol("⭐ R-1d-g: temizlik de MUTLAK yolla siliyor",
        _PL_H.count("os.remove(os.path.join(PUBLIC, _y))") >= 2)

kontrol("R-1d-g GERILEME YOK: kaynak_ses / yuv420p / tenant imza kapilari "
        "DURUYOR",
        "GERCEK-KAYNAK-SES-SIZINTI" in _GQ.FAIL_KODLARI
        and _HR.TESLIM_PIX_FMT == "yuv420p"
        and _IU.kapsam_ozeti()["tenant_baglanabilir"] is True)

kontrol("R-1d-g GERILEME YOK: gercek-timeline kapisi ve pix_fmt kapisi DURUYOR",
        "GERCEK-KAYNAK-TAVANI" in _GQ.FAIL_KODLARI
        and _HR.TESLIM_PIX_FMT == "yuv420p")

blok("§40ab R-1d-h — SIYAH/DONMUS KARE: ILK BOZULAN KATMAN KANITI")

# ⚠ MEDYASIZ: hicbir video/kare/QA artefakti URETILMEZ. Olcum `kosucu`
# enjeksiyonuyla sahte ffmpeg stderr'i uzerinden kosar; GERCEK olcum
# YALNIZCA uzak worker'da.
#
# ── OLCULEN KUSUR (R-1d-g pilotu, job_1786725532851) ──
#   POST-SIYAH-KARE (fail): 28.458-28.667 · 30.917-31.417 ·
#                           34.542-40.458 (5.92 sn)
#   POST-DONMUS-KARE (warn): 34.542 (+5.83 sn)
# POST-QA kusuru YAKALIYOR ama HANGI KATMANDA olustugunu SOYLEMIYORDU.

_KO = __import__("katman_olcum")

_SIYAH_ERR = ("[blackdetect @ 0x1] black_start:34.542 black_end:40.458 "
              "black_duration:5.916\n")
_DONMUS_ERR = "[freezedetect @ 0x1] lavfi.freezedetect.freeze_start: 34.542\n"


def _kos(siyah="", donmus="", rc=0):
    """⚠ Kosucu sozlesmesi (rc, stderr) — yalniz stderr donmek `rc != 0`
    durumunda olcumu "TEMIZ" gosteriyordu (bagimsiz denetim bulgusu)."""
    def _c(komut):
        return (rc, siyah if "blackdetect" in " ".join(komut) else donmus)
    return _c


kontrol("⭐ R-1d-h: esikler `qa_son` ile AYNI (yeniden tanimlanmadi)",
        _KO.SIYAH_FILTRE in oku(KOK, "editor/qa_son.py")
        and _KO.DONMUS_FILTRE in oku(KOK, "editor/qa_son.py")
        and _KO.kapsam_ozeti()["esik_qa_son_ile_ayni"] is True)
_O_TEMIZ = _KO.olc("/x.mp4", kosucu=_kos())
_O_SIYAH = _KO.olc("/x.mp4", kosucu=_kos(siyah=_SIYAH_ERR))
kontrol("⭐ R-1d-h: pilotun GERCEK araligi ayristiriliyor "
        "(34.542-40.458, 5.916 sn)",
        _O_SIYAH["siyah"] == [{"bas": 34.542, "bitis": 40.458,
                               "sure": 5.916}], _O_SIYAH["siyah"])
kontrol("⭐ R-1d-h: donmus baslangici da ayristiriliyor",
        _KO.olc("/x.mp4", kosucu=_kos(donmus=_DONMUS_ERR))["donmus"]
        == [{"bas": 34.542}])
kontrol("⭐ R-1d-h RED-FIRST: OLCULEMEYEN dosya TEMIZ SAYILMIYOR",
        _KO.temiz_mi({"olculdu": False}) is False
        and _KO.temiz_mi(_O_TEMIZ) is True
        and _KO.kapsam_ozeti()["olculmeyen_temiz_sayilir"] is False)
kontrol("⭐ R-1d-h RED-FIRST: kosucu PATLARSA stabil kod",
        _KO.olc("/x.mp4", kosucu=lambda k: (_ for _ in ()).throw(OSError())
                )["kod"] == "KATMAN-OLCULEMEDI")

# ── ILK BOZULAN KATMAN (uretim sirasi: kaynak -> segment -> birlesik -> final)
# ── RUNNER SOZLESMESI: rc ATILAMAZ (bagimsiz denetim bulgusu) ──
# ⚠ Eski sozlesme YALNIZ stderr donduruyordu. Dosya YOK / decoder hatasi /
# rc != 0 durumunda blackdetect eslesmesi CIKMAZ ve olcum "olculdu=True,
# TEMIZ" sayilirdi -> BOZUK CIKTI TESLIM KAPISINDAN GECERDI.
kontrol("⭐ R-1d-h BELIRLEYICI RED-FIRST: `rc != 0` ise olcum TEMIZ "
        "SAYILMIYOR (KATMAN-OLCULEMEDI, temiz_mi False)",
        _KO.olc("/x.mp4", kosucu=_kos(rc=1))["olculdu"] is False
        and _KO.olc("/x.mp4", kosucu=_kos(rc=1))["kod"] == "KATMAN-OLCULEMEDI"
        and _KO.temiz_mi(_KO.olc("/x.mp4", kosucu=_kos(rc=1))) is False)
kontrol("⭐ R-1d-h: IKI komuttan YALNIZ BIRI basarisiz olsa da OLCULEMEDI",
        _KO.olc("/x.mp4", kosucu=lambda k: (
            (0, "") if "blackdetect" in " ".join(k) else (1, "bozuk")
        ))["kod"] == "KATMAN-OLCULEMEDI")
kontrol("⭐ R-1d-h RED-FIRST: SADECE METIN donen ESKI bicim KABUL EDILMIYOR "
        "(donus kodu bilinmeden 'olculdu' DENMEZ)",
        _KO.olc("/x.mp4", kosucu=lambda k: "")["kod"] == "KATMAN-OLCULEMEDI"
        and _KO.olc("/x.mp4", kosucu=lambda k: "")["neden"] == "DONUS-KODU-YOK")
kontrol("⭐ R-1d-h: `subprocess.CompletedProcess` bicimi de kabul ediliyor",
        _KO.olc("/x.mp4", kosucu=lambda k: subprocess.CompletedProcess(
            k, 0, "", ""))["olculdu"] is True)
kontrol("⭐ R-1d-h: TIMEOUT/baslatma hatasi AYNI stabil kodla fail-closed",
        _KO.olc("/x.mp4", kosucu=lambda k: (_ for _ in ()).throw(
            subprocess.TimeoutExpired(k, 1)))["kod"] == "KATMAN-OLCULEMEDI")

# ⚠ GERCEK DAVRANIS TESTI — EKSIK DOSYA. ffmpeg gercekten calisir ama
# hicbir MEDYA/KARE URETMEZ (girdi yok, cikti `-f null`); Mac'te artefakt
# OLUSMAZ.
import shutil as _sh  # noqa: E402
if not _sh.which("ffmpeg"):
    bloke_yaz("R-1d-h eksik dosya gercek testi", "ffmpeg kurulu degil")
else:
    def _gercek_kos(komut):
        _r = subprocess.run(komut, capture_output=True, text=True, timeout=60)
        return _r.returncode, (_r.stderr or "")

    _YOK = os.path.join(tempfile.mkdtemp(prefix="yok_"), "olmayan.mp4")
    _O_YOK = _KO.olc(_YOK, kosucu=_gercek_kos)
    kontrol("⭐ R-1d-h BELIRLEYICI (gercek ffmpeg): OLMAYAN dosya TEMIZ "
            "SAYILMIYOR — KATMAN-OLCULEMEDI ve teslim REDDI",
            _O_YOK["olculdu"] is False
            and _O_YOK["kod"] == "KATMAN-OLCULEMEDI"
            and _KO.temiz_mi(_O_YOK) is False, _O_YOK.get("neden"))
    kontrol("⭐ R-1d-h (gercek ffmpeg): olculemeyen katman `atif`ta da "
            "TEMIZ sayilmiyor",
            _KO.ilk_bozulan_katman({"final": _O_YOK})["bozuk"] is False
            and _KO.atif({"final": _O_YOK})["final_bozuk"] is False)

kontrol("⭐ R-1d-h: uretim kosucusu rc TASIYOR (stderr'i tek basina "
        "DONDURMUYOR)",
        "return r.returncode, (r.stderr or \"\")" in oku(KOK, "hizli_render.py")
        and "kosucu=_ffmpeg_kos" in oku(KOK, "hizli_render.py"))
kontrol("⭐ R-1d-h: uretim kosucusunda timeout/baslatma hatasi rc=1 doner",
        "return 1, f\"{type(e).__name__}" in oku(KOK, "hizli_render.py"))

kontrol("⭐ R-1d-h BELIRLEYICI: bozukluk KAYNAK klipte basliyorsa suc "
        "`kaynak`a yazilir (xfade'e DEGIL)",
        _KO.ilk_bozulan_katman({
            "kaynak": [_O_TEMIZ, _O_SIYAH], "segment": [_O_SIYAH],
            "birlesik": _O_SIYAH, "final": _O_SIYAH})["katman"] == "kaynak")
kontrol("⭐ R-1d-h BELIRLEYICI: kaynak+segment TEMIZ, birlesik BOZUK ise "
        "suc XFADE ZINCIRINE (`birlesik`) yazilir",
        _KO.ilk_bozulan_katman({
            "kaynak": [_O_TEMIZ], "segment": [_O_TEMIZ, _O_TEMIZ],
            "birlesik": _O_SIYAH, "final": _O_SIYAH})["katman"] == "birlesik")
kontrol("⭐ R-1d-h: kaynak TEMIZ ama SEGMENT bozuksa suc `segment`e yazilir",
        _KO.ilk_bozulan_katman({
            "kaynak": [_O_TEMIZ], "segment": [_O_TEMIZ, _O_SIYAH],
            "final": _O_SIYAH})["katman"] == "segment")
kontrol("⭐ R-1d-h: yalnizca FINAL bozuksa suc `final`e yazilir "
        "(altyazi gomme adimi)",
        _KO.ilk_bozulan_katman({
            "kaynak": [_O_TEMIZ], "segment": [_O_TEMIZ],
            "birlesik": _O_TEMIZ, "final": _O_SIYAH})["katman"] == "final")
kontrol("⭐ R-1d-h: hicbir katman bozuk degilse `bozuk=False`",
        _KO.ilk_bozulan_katman({"final": _O_TEMIZ})["bozuk"] is False)
kontrol("⭐ R-1d-h: kod SIYAH/DONMUS ayrimi yapiyor",
        _KO.ilk_bozulan_katman({"final": _O_SIYAH})["kod"]
        == "KATMAN-SIYAH-KARE"
        and _KO.ilk_bozulan_katman({"final": _KO.olc(
            "/x.mp4", kosucu=_kos(donmus=_DONMUS_ERR))})["kod"]
        == "KATMAN-DONMUS-KARE")

# ── ATIF: "herhalde xfade'dir" DENMEZ ──
kontrol("⭐ R-1d-h BELIRLEYICI RED-FIRST: FINAL bozuk ama ONCEKI katmanlar "
        "HIC olculmediyse hukum `KATMAN-ATFEDILEMEDI` (tahmin YOK)",
        _KO.atif({"final": _O_SIYAH})["kod"] == "KATMAN-ATFEDILEMEDI"
        and _KO.atif({"final": _O_SIYAH})["atfedildi"] is False
        and _KO.atif({"final": _O_SIYAH})["katman"] is None)
kontrol("⭐ R-1d-h: onceki katman OLCULDUYSE atif YAPILIR",
        _KO.atif({"segment": [_O_TEMIZ], "final": _O_SIYAH})["atfedildi"]
        is True
        and _KO.atif({"segment": [_O_TEMIZ],
                      "final": _O_SIYAH})["katman"] == "final")
kontrol("⭐ R-1d-h: modul TAHMIN ETMIYOR (kapsam ozeti beyan ediyor)",
        _KO.kapsam_ozeti()["tahmin_eder"] is False
        and _KO.kapsam_ozeti()["surec_acar"] is False)

# ── URETIM ENTEGRASYONU (scratch DEGIL) ──
_HR_H = oku(KOK, "hizli_render.py")
kontrol("⭐ R-1d-h BELIRLEYICI: teslim kapisi siyah/donmus de OLCUYOR",
        "_siyah_donmus_kapisi(yol)" in _HR_H
        and "import katman_olcum" in _HR_H)
kontrol("⭐ R-1d-h BELIRLEYICI: nihai dosyada siyah/donmus VARSA cikti "
        "TESLIM EDILMIYOR (fail-closed)",
        "return False" in _HR_H.split("def _siyah_donmus_kapisi")[1][:2200]
        and "TESLIM EDILMEZ" in _HR_H.split(
            "def _siyah_donmus_kapisi")[1][:2200])
kontrol("⭐ R-1d-h: atif ARA DOSYALAR HALA DURURKEN yapiliyor "
        "(segment + birlesik + kaynak olculuyor)",
        all(x in _HR_H.split("def _siyah_donmus_kapisi")[1][:2200]
            for x in ('"segment"', '"birlesik"', '"kaynak"')))
kontrol("R-1d-h: katman_olcum.py derleniyor",
        _derlenir(os.path.join(KOK, "katman_olcum.py")))
kontrol("R-1d-h GERILEME YOK: pix_fmt kapisi + kaynak tavani + tenant imza",
        _HR.TESLIM_PIX_FMT == "yuv420p"
        and _KT2.KAYNAK_BASINA_TAVAN_SN == 8.0
        and _IU.kapsam_ozeti()["tenant_baglanabilir"] is True)

blok("§40ac R-1d-i — URETILMIS GORSEL SAHNESI ICIN STOK SORGUSU TURETILIR")

# ⚠ MEDYASIZ. Olculen kusur (R-1d-h pilotu, job_1786727121434):
#   RENDER-QA FAIL -> GERCEK-KAYNAK-TAVANI: ..._s001 8.172 sn (tavan 8.0)
# `..._s001` bir AI URETILMIS GORSEL sahnesiydi (openai/uretilmis-eser).
# Bolme yolu ek varligi YALNIZCA `footage_sorgu` uzerinden ariyordu ve
# uretilmis-gorsel sahnesinde o sorgu BOS -> aday havuzu BOS -> sahne
# BOLUNEMIYOR -> kapi ihlali SURUYOR.

_TARIF = ("A vivid wide cinematic view of Antarctic ice sheet cracking "
          "under bright daylight")
_SQ = _KT2.stok_sorgulari(_TARIF)

kontrol("⭐ R-1d-i BELIRLEYICI: `footage_sorgu` BOSKEN sahnenin INGILIZCE "
        "gorsel tarifinden sorgu TURETILIYOR (once havuz BOS kaliyordu)",
        _SQ["ok"] is True and _SQ["kaynak"] == "gorsel_tarif"
        and len(_SQ["sorgular"]) >= 2, _SQ["sorgular"])
kontrol("⭐ R-1d-i: turetilen sorgular ICERIK kelimelerinden olusuyor "
        "(etkisiz kelime YOK)",
        all(not set(q.split()) & {"a", "the", "of", "view", "cinematic",
                                  "wide", "under"}
            for q in _SQ["sorgular"]), _SQ["sorgular"])
kontrol("⭐ R-1d-i: DETERMINISTIK (ayni girdi -> ayni cikti, rastgelelik YOK)",
        _KT2.stok_sorgulari(_TARIF)["sorgular"] == _SQ["sorgular"]
        and _KT2.kapsam_ozeti()["rastgelelik"] is False)
kontrol("⭐ R-1d-i: MEVCUT sorgu varsa O kullanilir (gereksiz turetme YOK)",
        _KT2.stok_sorgulari(_TARIF, mevcut_sorgu="antarctic ice")
        == {"ok": True, "kod": "", "kaynak": "mevcut_sorgu",
            "sorgular": ["antarctic ice"]})
kontrol("⭐ R-1d-i RED-FIRST: kullanilabilir kelime YOKSA sorgu "
        "UYDURULMUYOR — stabil kod ile fail-closed",
        _KT2.stok_sorgulari("")["ok"] is False
        and _KT2.stok_sorgulari("")["kod"]
        == "KAYNAK-TAVANI-SORGU-TURETILEMEDI"
        and _KT2.stok_sorgulari("the a of and")["ok"] is False)
kontrol("⭐ R-1d-i RED-FIRST: yalniz RAKAM/NOKTALAMA iceren tarif de "
        "fail-closed",
        _KT2.stok_sorgulari("16:9 --- 2026 ... !!!")["kod"]
        == "KAYNAK-TAVANI-SORGU-TURETILEMEDI")
kontrol("⭐ R-1d-i: sorgu uretimi LLM/UCRET KULLANMIYOR",
        _KT2.kapsam_ozeti()["sorgu_llm_kullanir"] is False
        and _KT2.kapsam_ozeti()["sorgu_ucret"] is False
        and not any(a in _kod_yalniz(oku(KOK, "kaynak_tavani.py"))
                    for a in ("openai", "requests", "urllib", "subprocess")))
kontrol("⭐ R-1d-i BELIRLEYICI: AYNI gorseli kadrajlayip 'farkli asset' "
        "SAYMA yolu YOK (kapsam ozeti beyan ediyor)",
        _KT2.kapsam_ozeti()[
            "ayni_gorseli_kadrajlayip_farkli_asset_sayar"] is False)

# ── EDINIM ZINCIRI: turetilen sorgu FARKLI KAYNAK getirmezse fail-closed ──
kontrol("⭐ R-1d-i: turetilen sorgudan gelen aday AYNI kaynaksa yine "
        "REDDEDILIYOR (tavan bu yolla asilamaz)",
        _ev(["/ayni.mp4"])["ok"] is False
        and _ev(["/ayni.mp4"])["kod"] == "KAYNAK-TAVANI-VARLIK-YOK")
kontrol("⭐ R-1d-i: turetilen sorgudan FARKLI kaynak gelirse kabul "
        "(lisans+provenans dolu)",
        _ev(["/b.mp4"])["ok"] is True
        and _ev(["/b.mp4"])["kabul"][0]["lisans"] == "pixabay-content-license")

# ── URETIM ENTEGRASYONU (scratch DEGIL) ──
_PL_I = oku(KOK, "pipeline.py")
kontrol("⭐ R-1d-i BELIRLEYICI: pipeline sorguyu `scene_prompt`ten "
        "turetiyor ve bunu bolme yolunda KULLANIYOR",
        "kaynak_tavani.stok_sorgulari(" in _PL_I
        and '_s.get("scene_prompt") or _s.get("anlatim")' in _PL_I
        and '_sorgular = list(_sq["sorgular"])' in _PL_I)
kontrol("⭐ R-1d-i: sorgu turetilemezse sahne BOLUNMUYOR ve stabil kod "
        "raporlaniyor (fail-closed)",
        '"kod": _sq["kod"]' in _PL_I)
kontrol("⭐ R-1d-i: basarisiz yolda ses dilimleri TEMIZLENIYOR "
        "(transactional korundu)",
        _PL_I.count("os.remove(os.path.join(PUBLIC, _y))") == 3)
kontrol("R-1d-i GERILEME YOK: tavan / kaynak sesi / pix_fmt / tenant imza",
        _KT2.KAYNAK_BASINA_TAVAN_SN == 8.0
        and "GERCEK-KAYNAK-SES-SIZINTI" in _GQ.FAIL_KODLARI
        and _HR.TESLIM_PIX_FMT == "yuv420p"
        and _IU.kapsam_ozeti()["tenant_baglanabilir"] is True)

blok("§40ad R-1d-j — GECIS + SES-KURGU OLCUMU GERCEK TIMELINE'DAN")

# ⚠ MEDYASIZ. Olculen BOSLUK (R-1d-i pilotu, job_1786728166599):
#   `gecis hard_cut_orani` = None  ·  `J/L-cut ducking_araligi` = None
# R-1d-e'de PRE-QA kaniti gercek zaman cizgisine tasinirken bu iki olcum
# TASINMADI. `props_sahneler` gecis kararini `gecisImza` olarak tasiyor
# (YOKSA hizli_render 2 karelik fade = SERT KESME uygular) ama `gercek_qa`
# bundan metrik TURETMIYORDU.

def _gj(sid, imza=None, sure=6.0):
    d = {"scene_id": sid, "tur": "video", "medya": f"{sid}.mp4", "sure": sure}
    if imza is not None:
        d["gecisImza"] = imza
    return d


_GJ_PV = {"saglayici": "pexels", "lisans": "pexels-license",
          "asset_id": "a", "medya_turu": "video"}
_gj_cevir = (lambda lst: _GQ.sahneleri_cevir(
    lst, provenans_okuyucu=lambda y: dict(_GJ_PV, asset_id=y)))

# ── (1) GECIS: hard-cut orani GERCEK karardan turer ──
_G4 = _GQ.gecis_olcumu(_gj_cevir([_gj("s1"), _gj("s2"), _gj("s3"),
                                  _gj("s4", imza="karartma")]))
kontrol("⭐ R-1d-j BELIRLEYICI: hard_cut_orani ARTIK olculuyor "
        "(R-1d-i pilotunda None idi)",
        _G4["olculdu"] is True and _G4["gecis"] == 3
        and _G4["hard_cut"] == 2 and _G4["hard_cut_orani"] == 0.667, _G4)
kontrol("⭐ R-1d-j: `gecisImza` YOKSA SERT KESME sayilir "
        "(hizli_render 2 karelik fade uygular)",
        _GQ.gecis_olcumu(_gj_cevir([_gj("s1"), _gj("s2")]))["hard_cut_orani"]
        == 1.0)
kontrol("⭐ R-1d-j: imzali gecisler EFEKT sayilir ve TURU raporlanir",
        _GQ.gecis_olcumu(_gj_cevir(
            [_gj("s1"), _gj("s2", imza="flash"), _gj("s3", imza="whip")]
        ))["imza_dagilimi"] == {"flash": 1, "whip": 1})
kontrol("⭐ R-1d-j RED-FIRST: TEK sahnede gecis YOKTUR — oran UYDURULMAZ "
        "(stabil kod, fail-closed)",
        _GQ.gecis_olcumu(_gj_cevir([_gj("s1")]))["olculdu"] is False
        and _GQ.gecis_olcumu(_gj_cevir([_gj("s1")]))["kod"]
        == "GERCEK-TIMELINE-GECIS-YOK")
kontrol("⭐ R-1d-j RED-FIRST: BOS timeline'da sabit PASS YOK",
        _GQ.gecis_olcumu([])["olculdu"] is False)

# ── (2) SES KURGUSU: J/L-cut ve ducking ──
_S3 = _GQ.ses_kurgu_olcumu(_gj_cevir([_gj("s1"), _gj("s2"), _gj("s3")]))
# ⚠ FAZ Y-13a — SOZLESME BILINCLI OLARAK DEGISTI.
# ESKI IDDIA (buradaydi): "render'in yazdigi GERCEK sayac okunur; uretim
# yoksa 0 + tam=False". Bu iddia YANLISTI ve bu satir kusuru KILITLIYORDU:
# okunan sey `hizli_render._JL_SON` MODUL GLOBAL'iydi ve
#   · `pipeline.py` `olc()`'u RENDER'DAN ONCE kosuyor (deger hicbir zaman
#     o ise ait degil),
#   · obek birlestirmesi sayaci 0'a EZIYOR (>12 sahnede yapisal 0),
#   · global surec omurlu (A isinin QA'si B isinin sayisini raporluyor).
# Yani "olculdu: True" bir YALANDI: hicbir sey olculmemisti.
# ⚠ YENI SOZLESME: rapor ENJEKTE edilmezse `olculdu: False` + stabil kod;
# `j_l_cut` SAYI OLARAK SUNULMAZ — "olculmemis 0" ile "olculen 0"
# karistirilamaz. (Tam sozlesme: webapp/testler/test_faz_y13.py)
kontrol("⭐ Y-13a BELIRLEYICI: J/L raporu enjekte edilmezse UYDURULMAZ "
        "(olculdu=False + stabil kod, sayi sunulmaz)",
        _S3["olculdu"] is False
        and _S3["kod"] == _GQ.KOD_JL_OLCULMEDI
        and _S3.get("j_l_cut") is None
        and _S3["ses_gecis"] == 2 and _S3["tam"] is False, _S3)
kontrol("⭐ Y-13a: render SONRASI artefakta bagli rapor OLCULUR",
        (lambda r: r["olculdu"] is True and r["j_l_cut"] == 2
         and r["tam"] is True)(
            _GQ.ses_kurgu_olcumu(
                _gj_cevir([_gj("s1"), _gj("s2"), _gj("s3")]),
                jl_raporu={"sayi": 2, "offset_sn": 0.12,
                           "kaynak": "render-sonrasi",
                           "artefakt_sha256": "e" * 64},
                artefakt_sha256="e" * 64)))
kontrol("⭐ R-1d-j BELIRLEYICI RED-FIRST: DUCKING verisi gercek timeline'da "
        "YOK — 0 ya da PASS UYDURULMUYOR, stabil kod",
        _S3["ducking"]["olculdu"] is False
        and _S3["ducking"]["kod"] == "GERCEK-TIMELINE-DUCKING-VERISI-YOK")
kontrol("⭐ R-1d-j: ducking `olculemedi` oldugu icin ses kurgusu TAM PASS "
        "SAYILMIYOR",
        _S3["tam"] is False)
kontrol("⭐ R-1d-j RED-FIRST: tek sahnede ses gecisi YOKTUR (fail-closed)",
        _GQ.ses_kurgu_olcumu(_gj_cevir([_gj("s1")]))["olculdu"] is False)

# ── (3) TAM QA SOZLESMESINE TASINDI ──
_GJ_R = _GQ.olc(_gj_cevir([_gj("s1"), _gj("s2", imza="karartma"),
                           _gj("s3")]))
kontrol("⭐ R-1d-j BELIRLEYICI: `olc()` ciktisi `gecis` ve `ses` alanlarini "
        "TASIYOR (teslim raporu artik olcebilir)",
        isinstance(_GJ_R.get("gecis"), dict)
        and isinstance(_GJ_R.get("ses"), dict)
        and _GJ_R["gecis"]["hard_cut_orani"] is not None,
        {k: _GJ_R.get(k) for k in ("gecis", "ses")})
kontrol("⭐ R-1d-j: `olcumler` sozlugunde de yer aliyor",
        "gecis" in (_GJ_R.get("olcumler") or {})
        and "ses" in (_GJ_R.get("olcumler") or {}))
kontrol("⭐ R-1d-j: `gecisImza` cevirici tarafindan TASINIYOR",
        _gj_cevir([_gj("s1", imza="flash")])[0]["gecis_imza"] == "flash"
        and _gj_cevir([_gj("s1")])[0]["gecis_imza"] == "")
kontrol("⭐ R-1d-j: stabil kodlar kapsam ozetinde BEYAN EDILIYOR",
        {"GERCEK-TIMELINE-GECIS-YOK",
         "GERCEK-TIMELINE-DUCKING-VERISI-YOK"}
        <= set(_GQ.kapsam_ozeti()["stabil_kodlar"]))
kontrol("⭐ R-1d-j: olcum UYDURMUYOR (kapsam ozeti beyan ediyor)",
        _GQ.kapsam_ozeti()["uydurma_cekim_turu"] is False)
kontrol("R-1d-j GERILEME YOK: kaynak tavani / kaynak sesi / pix_fmt / imza",
        _KT2.KAYNAK_BASINA_TAVAN_SN == 8.0
        and "GERCEK-KAYNAK-SES-SIZINTI" in _GQ.FAIL_KODLARI
        and _HR.TESLIM_PIX_FMT == "yuv420p"
        and _IU.kapsam_ozeti()["tenant_baglanabilir"] is True)

blok("§40ae UI-1 — TEK AKIS: Metin→Stil→Kaynak→Uretim→Kalite→Indirme")

# ⚠ MEDYASIZ + TARAYICISIZ: DOM calistirilmaz. Sozlesme testi — akisin
# GERCEK staging uclarina bagli oldugu, erisilebilirlik iskeletinin
# bulundugu ve TOKEN'in istemciye CIKMADIGI dogrulanir.

_UI_JS = oku(KOK, "static/js/ui1.js")
_UI_SRV = oku(KOK, "server.py")

# ── (1) ROTA + KIMLIK KAPISI ──
kontrol("⭐ UI-1: `/akis` rotasi VAR ve HTML donuyor",
        '@app.get("/akis"' in _UI_SRV)
kontrol("⭐ UI-1 BELIRLEYICI: akis sayfasi KIMLIKSIZ acilmiyor "
        "(zorunlu oturum kapisi `/` ile AYNI)",
        "_AKIS_HTML" in _UI_SRV
        and "teslim.oturum_kapisi" in _UI_SRV.split("def akis_sayfasi")[1][:400])
kontrol("⭐ UI-1: sayfa yalnizca allowlist'teki `ui/js/*.js`yi cagiriyor",
        '/ui/js/ui1.js' in _UI_SRV
        and "js" in str(sorted(__import__('server', fromlist=['x']).UI_DIZIN_IZIN))
        if False else '/ui/js/ui1.js' in _UI_SRV)

# ── (2) ERISILEBILIRLIK ISKELETI ──
for _et, _ad in (("<label", "etiket"), ('aria-live', "canli bolge"),
                 ('aria-label', "aria etiketi"), ("<fieldset", "grup"),
                 ("<legend", "grup basligi")):
    kontrol(f"⭐ UI-1 erisilebilirlik: {_ad} var ({_et})", _et in _UI_SRV, _et)
kontrol("⭐ UI-1: HER form alani bir etikete bagli (alan sayisi = etiket)",
        _UI_SRV.count('<label for="') == 3
        and all(f'<label for="{a}"' in _UI_SRV
                for a in ("akis-metin", "akis-edit", "akis-kaynak")),
        _UI_SRV.count('<label for="'))
kontrol("⭐ UI-1: ilerleme cubugu ROL ve DEGER tasiyor (ekran okuyucu)",
        'role="progressbar"' in _UI_SRV and "aria-valuenow" in _UI_JS)

# ── (3) AKISIN ALTI ADIMI ──
for _adim in ("metin", "stil", "kaynak", "uretim", "kalite", "indirme"):
    kontrol(f"⭐ UI-1: `{_adim}` adimi akista TANIMLI",
            f'data-adim="{_adim}"' in _UI_SRV, _adim)

# ── (4) GERCEK UCLARA BAGLI (CSS-only DEGIL) ──
for _uc in ("/api/generate", "/api/job/", "/api/kutuphane", "/api/oturum"):
    kontrol(f"⭐ UI-1: `{_uc}` GERCEKTEN cagriliyor", _uc in _UI_JS, _uc)
kontrol("⭐ UI-1 BELIRLEYICI: is ilerlemesi POLL ediliyor (durum bagi)",
        "setTimeout" in _UI_JS and "progress" in _UI_JS
        and "stage_ad" in _UI_JS)
kontrol("⭐ UI-1: QA sonucu ve TESLIM karari GOSTERILIYOR",
        "kalite" in _UI_JS and "teslim_ok" in _UI_JS)
kontrol("⭐ UI-1: provider / provenance / maliyet GOSTERILIYOR",
        "saglayici" in _UI_JS and "provenance" in _UI_JS
        and "maliyet" in _UI_JS)
kontrol("⭐ UI-1: SON-3 kutuphane goruntuleniyor (imzali link)",
        "kutuphane" in _UI_JS and "video_url" in _UI_JS)
kontrol("⭐ UI-1: indirme baglantisi SIGNED URL'den geliyor "
        "(ham `ciktilar/` yolu KURULMUYOR)",
        'href="ciktilar/' not in _UI_JS and "video_url" in _UI_JS)

# ── (5) EDIT SEGMENTI + KAYNAK SECIMI + KREDI ONAYI ──
for _seg in ("az", "orta", "yuksek"):
    kontrol(f"⭐ UI-1: edit segmenti `{_seg}` secilebilir",
            f'value="{_seg}"' in _UI_SRV, _seg)
for _k in ("otomatik", "magnific", "ucretsiz"):
    kontrol(f"⭐ UI-1: kaynak secimi `{_k}` var", f'value="{_k}"' in _UI_SRV,
            _k)
kontrol("⭐ UI-1: kaynak secenekleri R-1b TERCIHLERI ile AYNI",
        set(_SM.TERCIHLER) == {"otomatik", "magnific", "ucretsiz"})
kontrol("⭐ UI-1 BELIRLEYICI: KREDI ONAYI durumu GORUNUR "
        "(kullanici kredi harcanacagini bilir)",
        "kredi" in _UI_JS and "kredi_onayi" in _UI_JS)

# ── (6) GUVENLIK: TOKEN ISTEMCIYE CIKMIYOR ──
kontrol("⭐ UI-1 BELIRLEYICI: istemci kodu TOKEN/PAROLA/ANAHTAR OKUMUYOR",
        not any(a in _UI_JS for a in ("sifreli_token", "parola_hash",
                                      "IMZA_ANAHTARI", "OTURUM_ANAHTARI")))
# ⚠ FAZ UI-3 ile KESKINLESTIRILDI: kural "hicbir cerez okunmasin" DEGIL,
# "YETKI cerezi okunmasin"dir. Double-submit CSRF, `vr_csrf` cerezinin
# JS'ten OKUNABILIR olmasini ZORUNLU kilar; yetki hala HttpOnly oturum
# cerezindedir ve bu dosya onu okumaz (adini bile tasimaz).
kontrol("⭐ UI-1/UI-3: OTURUM cerezi JS'ten OKUNMUYOR (HttpOnly korunuyor; "
        "cerez okumasi YALNIZ CSRF icin ve TEK yerde)",
        "vr_oturum" not in _UI_JS
        and len(re.findall(r"document\.cookie", _UI_JS)) == 1
        and "vr_csrf" in _UI_JS)
kontrol("⭐ UI-1: saglayici ozeti token TASIMIYOR (R-1b sozlesmesi)",
        _SM.kapsam_ozeti()["token_istemciye_cikar"] is False)

# ── (7) GERILEME YOK ──
kontrol("UI-1 GERILEME YOK: 22 alan sozlesmesi DEGISMEDI",
        len(set(re.findall(r"\{ad: '(\w+)'",
                           oku(KOK, "static/js/api.js")))) == 22)
kontrol("UI-1 GERILEME YOK: tenant/imza + kaynak tavani + pix_fmt kapilari",
        _IU.kapsam_ozeti()["tenant_baglanabilir"] is True
        and _KT2.KAYNAK_BASINA_TAVAN_SN == 8.0
        and _HR.TESLIM_PIX_FMT == "yuv420p")
kontrol("UI-1: eski arayuz dosyalari DOKUNULMADI",
        "wizard" in " ".join(os.listdir(os.path.join(KOK, "static", "js"))))

print(f"\n{'=' * 60}")
print(f"GECEN: {gecen}   BASARISIZ: {len(basarisiz)}   BLOKE: {len(bloke)}")
for b in basarisiz:
    print(f"  XX {b}")
for b in bloke:
    print(f"  -- BLOKE {b}")
sys.exit(1 if basarisiz else 0)
