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

⚠ DURUSTLUK KURALI: gercek vision cagrisi YAPILMAZ (para harcamaz). Kapinin
karar mantigi SAF fonksiyon olarak test edilir; entegrasyon sahte okuyucuyla
uctan uca kosturulur. Gercek modelin dogrulugu bu testin iddiasi DEGILDIR.

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


print(f"\n{'=' * 60}")
print(f"GECEN: {gecen}   BASARISIZ: {len(basarisiz)}   BLOKE: {len(bloke)}")
for b in basarisiz:
    print(f"  XX {b}")
for b in bloke:
    print(f"  -- BLOKE {b}")
sys.exit(1 if basarisiz else 0)
