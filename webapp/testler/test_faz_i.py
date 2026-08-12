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


print(f"\n{'=' * 60}")
print(f"GECEN: {gecen}   BASARISIZ: {len(basarisiz)}   BLOKE: {len(bloke)}")
for b in basarisiz:
    print(f"  XX {b}")
for b in bloke:
    print(f"  -- BLOKE {b}")
sys.exit(1 if basarisiz else 0)
