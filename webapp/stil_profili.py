#!/usr/bin/env python3
"""SURUMLU BILESIK STIL PROFILLERI — tek etiket degil, 11 boyutlu sozlesme.

⚠ NEDEN VAR (Faz I-2b): stil bugun TEK BIR ETIKET ("sinematik-belgesel") ve
o etiketin arkasindaki sozluk `pipeline.EDIT_STILLERI` icinde DUZ duruyor:

  - **Surum yok.** Bir stilin `sahne_sn`'i degistiginde dun uretilmis is
    yeniden uretilemez; hangi ayarla ciktigi kayitli degil.
  - **Boyutlar karisik.** `sahne_sn` (tempo), `altyazi` (tipografi),
    `mag` (upscale), `gorsel_ek` (palet promptu) ayni duzlemde.
  - **Turetilemez.** "Korku + belgesel" gibi melez bir istek icin sozluge
    ELLE yeni satir yazmak gerekiyor; cekirdek kod her yeni stilde buyuyor.
  - **Kanit/lisans ve QA esikleri stilin PARCASI degil.** Belgeselde AI
    gorsel yasagi `gorsel_yasak` diye tek bayrak; lisans beyaz listesi,
    minimum bagimsiz kaynak ve QA esikleri stil profiline BAGLI degil.

⚠ TASARIM KURALLARI
1. **SURUMLU.** Her profil `surum` tasir, sema `SEMA_SURUM` tasir. Eski surum
   `ARSIV`e dondurulur; `profil_al(kimlik, surum=...)` ile aynen geri gelir.
   Boylece "dun bu isi hangi ayarla urettik" sorusu CEVAPLANABILIR.
2. **CEKIRDEK KOD DEGISMEDEN GENISLER.** Yeni profil = `PROFIL`e satir.
   Yeni BOYUT ALANI = `BOYUT_KURALI`ya satir. Birlestirme kodu ayni kalir.
3. **MELEZ TURETILEBILIR ve GEREKCESI DONER.** `tureti()` iki (veya daha
   fazla) profili birlestirir ve HANGI ALANIN NEREDEN geldigini raporlar.
4. **KULLANICI SECIMI AUTO'YU YENER.** `coz()` sirasi: kullanici > auto
   (konsept) > turetilmis melez > varsayilan. Kaynak her zaman RAPORLANIR.
   Kullanici BILINMEYEN bir stil verdiyse sessizce yutulmaz — dusulur ve
   `gerekce` bunu soyler.
5. **KATI OLAN KAZANIR.** Kanit/lisans ve QA esikleri birlestirilirken
   gevsek taraf degil KATI taraf secilir (bkz. `BOYUT_KURALI`).
6. **KAYIT DEGISMEZ.** `profil_al()` her zaman DERIN KOPYA doner; cagiran
   kaydi kazara bozamaz.
7. **AG YOK, PARA YOK.** Bu modul tamamen deterministik ve ucretsizdir.
8. **GERIYE UYUMLULUK.** `eski_edit_stiline()` profili `pipeline.EDIT_STILLERI`
   bicimine cevirir. `pipeline.py` BU ADIMDA DEGISTIRILMEDI; baglama I-2c.
"""
from __future__ import annotations

import copy

# Sema surumu. MAJOR degisirse eski profiller UYUMSUZ sayilir (sessiz kabul yok).
SEMA_SURUM = "1.0.0"


# ═══════════════════════════ BOYUT SEMASI ═══════════════════════════
# 11 boyut. Her alan: (birlestirme_kurali, tip)
#
# Birlestirme kurallari — melez turetirken bu tablo karar verir:
#   ortalama          : agirlikli ortalama (sayisal)
#   agirlikli-secim   : en yuksek agirlikli ebeveynin degeri (kategorik)
#   birlesim          : demetlerin birlesimi
#   kesisim           : demetlerin KESISIMI (beyaz liste -> kati taraf)
#   en-kati-dogru     : herhangi biri True ise True (yasak > izin)
#   en-kati-maks      : en buyuk deger kati (or. min_bagimsiz_kaynak)
#   en-kati-min       : en kucuk deger kati (or. siyah_kare_maks)
#
# ⚠ YENI ALAN EKLEMEK: buraya bir satir + her profile deger. Kod DEGISMEZ.
BOYUT_KURALI = {
    # ── 1. ANLATIM YAPISI ──
    "anlatim": {
        "yapi": ("agirlikli-secim", str),          # bolumlu|tek-akis|liste|diyalog
        "acilis": ("agirlikli-secim", str),        # kanca|soguk|baslik
        "kisi": ("agirlikli-secim", str),          # 1.|2.|3.
        "bolum_basligi": ("en-kati-dogru", bool),
    },
    # ── 2. TEMPO / PLAN SURESI ──
    "tempo": {
        "plan_sn": ("ortalama", float),
        "maks_plan_sn": ("en-kati-min", float),    # kati olan KISA tavandir
        "kelime_plan": ("ortalama", float),
        "dagilim": ("agirlikli-secim", str),       # tek-modlu|cift-modlu
    },
    # ── 3. GECIS ──
    "gecis": {
        "tur": ("agirlikli-secim", str),           # hard-cut|crossfade|whip|karisik
        "sure_sn": ("ortalama", float),
        "oran_pct": ("ortalama", float),           # planlarin yuzde kaci gecisli
    },
    # ── 4. KAMERA / HAREKET ──
    "kamera": {
        "hareket": ("agirlikli-secim", str),       # sabit|ken-burns|push-in|handheld|drone
        "yogunluk": ("ortalama", float),           # 0-100
        "zoom_tavan": ("en-kati-min", float),      # kati olan DUSUK zoomdur
    },
    # ── 5. TIPOGRAFI ──
    "tipografi": {
        "altyazi": ("agirlikli-secim", str),       # yok|orta|yogun
        "baslik": ("agirlikli-secim", str),        # yok|sade|kinetik
        "guvenli_alan_pct": ("en-kati-maks", float),
    },
    # ── 6. PALET / COLOR GRADE ──
    "palet": {
        "grade": ("agirlikli-secim", str),
        "doygunluk": ("agirlikli-secim", str),     # dusuk|orta|yuksek
        "kontrast": ("agirlikli-secim", str),
        "hex": ("birlesim", tuple),
    },
    # ── 7. MUZIK / SFX ──
    "ses": {
        "muzik": ("agirlikli-secim", str),
        "muzik_db": ("ortalama", float),
        "sfx": ("agirlikli-secim", str),           # yok|az|yogun
        "ducking_db": ("ortalama", float),
    },
    # ── 8. MEDYA STRATEJISI ──
    "medya": {
        "strateji": ("agirlikli-secim", str),      # gercek-footage|karma|ai-gorsel
        "footage_pct": ("ortalama", float),
        "grafik_pct": ("ortalama", float),
        "ai_gorsel_yasak": ("en-kati-dogru", bool),
    },
    # ── 9. ORAN / KANAL / SURE ──
    "dagitim": {
        "oran": ("agirlikli-secim", str),          # 16:9|9:16|1:1
        "kanal": ("agirlikli-secim", str),         # youtube|shorts|reels|tiktok
        "hedef_sn": ("ortalama", float),
        "maks_sn": ("en-kati-min", float),
    },
    # ── 10. KANIT / LISANS KURALLARI ──
    "kanit": {
        "lisans_beyaz_liste": ("kesisim", tuple),
        "atif_zorunlu": ("en-kati-dogru", bool),
        "min_bagimsiz_kaynak": ("en-kati-maks", float),
        "arsiv_zorunlu": ("en-kati-dogru", bool),
        "yer_kapisi": ("en-kati-dogru", bool),     # Faz I-1 kare kapisi zorunlu mu
    },
    # ── 11. QA ESIKLERI ──
    "qa": {
        "lufs_hedef": ("ortalama", float),
        "tepe_dbtp_maks": ("en-kati-min", float),
        "sure_sapma_pct_maks": ("en-kati-min", float),
        "siyah_kare_maks": ("en-kati-min", float),
        "donmus_kare_maks": ("en-kati-min", float),
        "min_kesme": ("en-kati-maks", float),
    },
}

BOYUTLAR = tuple(BOYUT_KURALI)


# ═══════════════════════════ ORTAK SABITLER ═══════════════════════════
# Belgesel/haber sinifi icin dar lisans beyaz listesi (Faz A `manifests` ile ayni ruh)
LISANS_KATI = ("cc0", "public-domain", "cc-by", "cc-by-sa")
# Stok saglayici lisanslari da kabul eden gevsek liste
LISANS_GENIS = ("cc0", "public-domain", "cc-by", "cc-by-sa", "pexels",
                "pixabay", "coverr", "freepik")

# QA tabani — Faz H6 `qa_kopru`/`editor.qa_son` ile ayni birimler (LUFS, dBTP).
QA_TABAN = {"lufs_hedef": -14.0, "tepe_dbtp_maks": -1.5,
            "sure_sapma_pct_maks": 20.0, "siyah_kare_maks": 0.0,
            "donmus_kare_maks": 0.0, "min_kesme": 4.0}


def _qa(**ez):
    d = dict(QA_TABAN)
    d.update(ez)
    return d


# ═══════════════════════════ PROFIL KAYDI ═══════════════════════════
# ⚠ YENI PROFIL EKLEMEK: buraya bir satir. Cekirdek kod DEGISMEZ.
# ⚠ BIR PROFILI DEGISTIRMEK: once `arsivle(kimlik)` ile mevcut surumu dondur,
#   sonra `surum`u yukselt. Aksi halde eski isler yeniden uretilemez.
PROFIL = {
    "belgesel-sinematik": {
        "ad": "Sinematik Belgesel",
        "ozet": "Yavas anlatim, hard-cut, gercek footage, orkestral muzik",
        "surum": "1.0.0",
        "anlatim": {"yapi": "bolumlu", "acilis": "kanca", "kisi": "3.",
                    "bolum_basligi": True},
        "tempo": {"plan_sn": 7.0, "maks_plan_sn": 9.0, "kelime_plan": 17.0,
                  "dagilim": "tek-modlu"},
        "gecis": {"tur": "hard-cut", "sure_sn": 0.0, "oran_pct": 10.0},
        "kamera": {"hareket": "ken-burns", "yogunluk": 35.0, "zoom_tavan": 1.25},
        "tipografi": {"altyazi": "orta", "baslik": "sade",
                      "guvenli_alan_pct": 8.0},
        "palet": {"grade": "dogal-sicak", "doygunluk": "orta",
                  "kontrast": "yuksek", "hex": ("#1B2A32", "#C9A227", "#E8E2D4")},
        "ses": {"muzik": "orkestral", "muzik_db": -22.0, "sfx": "az",
                "ducking_db": -9.0},
        "medya": {"strateji": "gercek-footage", "footage_pct": 85.0,
                  "grafik_pct": 5.0, "ai_gorsel_yasak": True},
        "dagitim": {"oran": "16:9", "kanal": "youtube", "hedef_sn": 600.0,
                    "maks_sn": 1800.0},
        "kanit": {"lisans_beyaz_liste": LISANS_KATI, "atif_zorunlu": True,
                  "min_bagimsiz_kaynak": 2.0, "arsiv_zorunlu": True,
                  "yer_kapisi": True},
        "qa": _qa(),
    },
    "belgesel-arastirmaci": {
        "ad": "Arastirmaci / true crime",
        "ozet": "Karanlik grade, gerilimli tempo, EN KATI kanit kurallari",
        "surum": "1.0.0",
        "anlatim": {"yapi": "bolumlu", "acilis": "kanca", "kisi": "3.",
                    "bolum_basligi": True},
        "tempo": {"plan_sn": 5.0, "maks_plan_sn": 8.0, "kelime_plan": 14.0,
                  "dagilim": "cift-modlu"},
        "gecis": {"tur": "hard-cut", "sure_sn": 0.0, "oran_pct": 8.0},
        "kamera": {"hareket": "push-in", "yogunluk": 45.0, "zoom_tavan": 1.2},
        "tipografi": {"altyazi": "orta", "baslik": "sade",
                      "guvenli_alan_pct": 8.0},
        "palet": {"grade": "soguk-karanlik", "doygunluk": "dusuk",
                  "kontrast": "yuksek", "hex": ("#0E1116", "#8A1C1C", "#B8B8B8")},
        "ses": {"muzik": "gerilim-drone", "muzik_db": -24.0, "sfx": "az",
                "ducking_db": -10.0},
        "medya": {"strateji": "gercek-footage", "footage_pct": 80.0,
                  "grafik_pct": 10.0, "ai_gorsel_yasak": True},
        "dagitim": {"oran": "16:9", "kanal": "youtube", "hedef_sn": 720.0,
                    "maks_sn": 1800.0},
        # ⚠ EN KATI: gercek kisi/olay anlatiliyor; tek kaynakla iddia kurulmaz.
        "kanit": {"lisans_beyaz_liste": LISANS_KATI, "atif_zorunlu": True,
                  "min_bagimsiz_kaynak": 3.0, "arsiv_zorunlu": True,
                  "yer_kapisi": True},
        "qa": _qa(sure_sapma_pct_maks=15.0),
    },
    "seyahat-4k": {
        "ad": "Seyahat 4K",
        "ozet": "Gercek drone + yer goruntusu derlemesi, AI gorsel YASAK",
        "surum": "1.0.0",
        "anlatim": {"yapi": "bolumlu", "acilis": "baslik", "kisi": "3.",
                    "bolum_basligi": True},
        "tempo": {"plan_sn": 5.5, "maks_plan_sn": 8.0, "kelime_plan": 15.0,
                  "dagilim": "cift-modlu"},
        "gecis": {"tur": "hard-cut", "sure_sn": 0.0, "oran_pct": 12.0},
        "kamera": {"hareket": "drone", "yogunluk": 60.0, "zoom_tavan": 1.18},
        "tipografi": {"altyazi": "yok", "baslik": "sade",
                      "guvenli_alan_pct": 8.0},
        "palet": {"grade": "dogal-canli", "doygunluk": "yuksek",
                  "kontrast": "orta", "hex": ("#0A6C8F", "#2FBFA0", "#F2E8D5")},
        "ses": {"muzik": "atmosferik", "muzik_db": -20.0, "sfx": "az",
                "ducking_db": -8.0},
        "medya": {"strateji": "gercek-footage", "footage_pct": 100.0,
                  "grafik_pct": 0.0, "ai_gorsel_yasak": True},
        "dagitim": {"oran": "16:9", "kanal": "youtube", "hedef_sn": 600.0,
                    "maks_sn": 1800.0},
        "kanit": {"lisans_beyaz_liste": LISANS_GENIS, "atif_zorunlu": True,
                  "min_bagimsiz_kaynak": 1.0, "arsiv_zorunlu": False,
                  "yer_kapisi": True},
        "qa": _qa(min_kesme=8.0),
    },
    "ambient-sakin": {
        "ad": "Ambient / meditasyon",
        "ozet": "Cok uzun planlar, gecissiz, minimum tipografi, sakin ses",
        "surum": "1.0.0",
        "anlatim": {"yapi": "tek-akis", "acilis": "soguk", "kisi": "2.",
                    "bolum_basligi": False},
        "tempo": {"plan_sn": 12.0, "maks_plan_sn": 20.0, "kelime_plan": 8.0,
                  "dagilim": "tek-modlu"},
        "gecis": {"tur": "crossfade", "sure_sn": 1.5, "oran_pct": 90.0},
        "kamera": {"hareket": "sabit", "yogunluk": 10.0, "zoom_tavan": 1.08},
        "tipografi": {"altyazi": "yok", "baslik": "yok",
                      "guvenli_alan_pct": 6.0},
        "palet": {"grade": "yumusak-sicak", "doygunluk": "dusuk",
                  "kontrast": "dusuk", "hex": ("#2B3A42", "#7E9B8F", "#EDE6DA")},
        # ⚠ Meditasyon iceriginde muzik ANLATIMIN kendisidir; -18 dB daha yuksek.
        "ses": {"muzik": "ambient-pad", "muzik_db": -18.0, "sfx": "yok",
                "ducking_db": -4.0},
        "medya": {"strateji": "gercek-footage", "footage_pct": 95.0,
                  "grafik_pct": 0.0, "ai_gorsel_yasak": False},
        "dagitim": {"oran": "16:9", "kanal": "youtube", "hedef_sn": 1800.0,
                    "maks_sn": 3600.0},
        "kanit": {"lisans_beyaz_liste": LISANS_GENIS, "atif_zorunlu": True,
                  "min_bagimsiz_kaynak": 0.0, "arsiv_zorunlu": False,
                  "yer_kapisi": False},
        "qa": _qa(min_kesme=1.0, sure_sapma_pct_maks=30.0),
    },
    "explainer-hizli": {
        "ad": "Hizli Explainer",
        "ozet": "1.5-3 sn kesme, surekli kinetik metin, flat grafik",
        "surum": "1.0.0",
        "anlatim": {"yapi": "liste", "acilis": "kanca", "kisi": "2.",
                    "bolum_basligi": False},
        "tempo": {"plan_sn": 2.4, "maks_plan_sn": 4.0, "kelime_plan": 6.0,
                  "dagilim": "tek-modlu"},
        "gecis": {"tur": "whip", "sure_sn": 0.2, "oran_pct": 45.0},
        "kamera": {"hareket": "push-in", "yogunluk": 70.0, "zoom_tavan": 1.35},
        "tipografi": {"altyazi": "yogun", "baslik": "kinetik",
                      "guvenli_alan_pct": 10.0},
        "palet": {"grade": "flat-canli", "doygunluk": "yuksek",
                  "kontrast": "yuksek", "hex": ("#1446A0", "#F5A623", "#FFFFFF")},
        "ses": {"muzik": "ritmik", "muzik_db": -20.0, "sfx": "yogun",
                "ducking_db": -12.0},
        "medya": {"strateji": "karma", "footage_pct": 45.0,
                  "grafik_pct": 40.0, "ai_gorsel_yasak": False},
        "dagitim": {"oran": "16:9", "kanal": "youtube", "hedef_sn": 300.0,
                    "maks_sn": 900.0},
        "kanit": {"lisans_beyaz_liste": LISANS_GENIS, "atif_zorunlu": True,
                  "min_bagimsiz_kaynak": 1.0, "arsiv_zorunlu": False,
                  "yer_kapisi": False},
        "qa": _qa(min_kesme=20.0),
    },
    "bilim-anlatisi": {
        "ad": "Bilim / veri anlatisi",
        "ozet": "Grafik katmani agirlikli, olculu tempo, kaynak zorunlu",
        "surum": "1.0.0",
        "anlatim": {"yapi": "bolumlu", "acilis": "kanca", "kisi": "3.",
                    "bolum_basligi": True},
        "tempo": {"plan_sn": 7.0, "maks_plan_sn": 9.0, "kelime_plan": 22.0,
                  "dagilim": "tek-modlu"},
        "gecis": {"tur": "hard-cut", "sure_sn": 0.0, "oran_pct": 10.0},
        "kamera": {"hareket": "sabit", "yogunluk": 25.0, "zoom_tavan": 1.15},
        "tipografi": {"altyazi": "orta", "baslik": "sade",
                      "guvenli_alan_pct": 10.0},
        "palet": {"grade": "notr-editoryel", "doygunluk": "orta",
                  "kontrast": "orta", "hex": ("#FFFFFF", "#123B5C", "#D94F30")},
        "ses": {"muzik": "minimal", "muzik_db": -24.0, "sfx": "az",
                "ducking_db": -10.0},
        "medya": {"strateji": "karma", "footage_pct": 45.0,
                  "grafik_pct": 41.0, "ai_gorsel_yasak": False},
        "dagitim": {"oran": "16:9", "kanal": "youtube", "hedef_sn": 600.0,
                    "maks_sn": 1800.0},
        # ⚠ Bilim/veri iddiasi sayiyla konusur; iki bagimsiz kaynak SART.
        "kanit": {"lisans_beyaz_liste": LISANS_GENIS, "atif_zorunlu": True,
                  "min_bagimsiz_kaynak": 2.0, "arsiv_zorunlu": False,
                  "yer_kapisi": False},
        "qa": _qa(),
    },
    "hikaye-sinematik": {
        "ad": "Sinematik hikaye",
        "ozet": "Foto-gercekci film kareleri, yogun acilis, karakter tutarliligi",
        "surum": "1.0.0",
        "anlatim": {"yapi": "tek-akis", "acilis": "kanca", "kisi": "3.",
                    "bolum_basligi": False},
        "tempo": {"plan_sn": 6.0, "maks_plan_sn": 9.0, "kelime_plan": 16.0,
                  "dagilim": "cift-modlu"},
        "gecis": {"tur": "crossfade", "sure_sn": 0.6, "oran_pct": 35.0},
        "kamera": {"hareket": "ken-burns", "yogunluk": 50.0, "zoom_tavan": 1.38},
        "tipografi": {"altyazi": "orta", "baslik": "sade",
                      "guvenli_alan_pct": 8.0},
        "palet": {"grade": "sinematik-teal-orange", "doygunluk": "orta",
                  "kontrast": "yuksek", "hex": ("#123A47", "#E0763B", "#F0E7D8")},
        "ses": {"muzik": "sinematik", "muzik_db": -21.0, "sfx": "yogun",
                "ducking_db": -10.0},
        "medya": {"strateji": "ai-gorsel", "footage_pct": 15.0,
                  "grafik_pct": 0.0, "ai_gorsel_yasak": False},
        "dagitim": {"oran": "16:9", "kanal": "youtube", "hedef_sn": 600.0,
                    "maks_sn": 1800.0},
        # ⚠ Kurgu: gercek olay iddiasi yok, bu yuzden kaynak zorunlulugu yok.
        "kanit": {"lisans_beyaz_liste": LISANS_GENIS, "atif_zorunlu": False,
                  "min_bagimsiz_kaynak": 0.0, "arsiv_zorunlu": False,
                  "yer_kapisi": False},
        "qa": _qa(),
    },
    "korku-gerilim": {
        "ad": "Korku / gerilim",
        "ozet": "Karanlik palet, uzun bekleyis + ani kesme, yogun SFX",
        "surum": "1.0.0",
        "anlatim": {"yapi": "tek-akis", "acilis": "kanca", "kisi": "1.",
                    "bolum_basligi": False},
        "tempo": {"plan_sn": 5.0, "maks_plan_sn": 12.0, "kelime_plan": 12.0,
                  "dagilim": "cift-modlu"},
        "gecis": {"tur": "hard-cut", "sure_sn": 0.0, "oran_pct": 5.0},
        "kamera": {"hareket": "handheld", "yogunluk": 55.0, "zoom_tavan": 1.3},
        "tipografi": {"altyazi": "orta", "baslik": "sade",
                      "guvenli_alan_pct": 8.0},
        "palet": {"grade": "soguk-karanlik", "doygunluk": "dusuk",
                  "kontrast": "yuksek", "hex": ("#07090C", "#3A0F12", "#9AA5A8")},
        "ses": {"muzik": "gerilim-drone", "muzik_db": -23.0, "sfx": "yogun",
                "ducking_db": -12.0},
        "medya": {"strateji": "ai-gorsel", "footage_pct": 10.0,
                  "grafik_pct": 0.0, "ai_gorsel_yasak": False},
        "dagitim": {"oran": "16:9", "kanal": "youtube", "hedef_sn": 600.0,
                    "maks_sn": 1800.0},
        "kanit": {"lisans_beyaz_liste": LISANS_GENIS, "atif_zorunlu": False,
                  "min_bagimsiz_kaynak": 0.0, "arsiv_zorunlu": False,
                  "yer_kapisi": False},
        "qa": _qa(),
    },
    "cocuk-yumusak": {
        "ad": "Cocuk hikayesi",
        "ozet": "Yumusak palet, yavas tempo, sakin ses, yuksek guvenli alan",
        "surum": "1.0.0",
        "anlatim": {"yapi": "tek-akis", "acilis": "soguk", "kisi": "3.",
                    "bolum_basligi": False},
        "tempo": {"plan_sn": 8.0, "maks_plan_sn": 10.0, "kelime_plan": 12.0,
                  "dagilim": "tek-modlu"},
        "gecis": {"tur": "crossfade", "sure_sn": 0.8, "oran_pct": 70.0},
        "kamera": {"hareket": "ken-burns", "yogunluk": 25.0, "zoom_tavan": 1.15},
        "tipografi": {"altyazi": "orta", "baslik": "sade",
                      "guvenli_alan_pct": 12.0},
        "palet": {"grade": "pastel-sicak", "doygunluk": "orta",
                  "kontrast": "dusuk", "hex": ("#FDF3E3", "#F2A9A0", "#8FBFA8")},
        # ⚠ Cocuk icerigi: ani yuksek ses yok, ducking sig.
        "ses": {"muzik": "yumusak", "muzik_db": -20.0, "sfx": "az",
                "ducking_db": -6.0},
        "medya": {"strateji": "ai-gorsel", "footage_pct": 5.0,
                  "grafik_pct": 0.0, "ai_gorsel_yasak": False},
        "dagitim": {"oran": "16:9", "kanal": "youtube", "hedef_sn": 300.0,
                    "maks_sn": 900.0},
        "kanit": {"lisans_beyaz_liste": LISANS_GENIS, "atif_zorunlu": False,
                  "min_bagimsiz_kaynak": 0.0, "arsiv_zorunlu": False,
                  "yer_kapisi": False},
        "qa": _qa(),
    },
    "urun-tanitim": {
        "ad": "Urun tanitimi / inceleme",
        "ozet": "Temiz grade, orta tempo, urun odakli plan, yogun tipografi",
        "surum": "1.0.0",
        "anlatim": {"yapi": "liste", "acilis": "kanca", "kisi": "2.",
                    "bolum_basligi": False},
        "tempo": {"plan_sn": 3.5, "maks_plan_sn": 6.0, "kelime_plan": 9.0,
                  "dagilim": "tek-modlu"},
        "gecis": {"tur": "karisik", "sure_sn": 0.3, "oran_pct": 35.0},
        "kamera": {"hareket": "push-in", "yogunluk": 55.0, "zoom_tavan": 1.28},
        "tipografi": {"altyazi": "yogun", "baslik": "kinetik",
                      "guvenli_alan_pct": 10.0},
        "palet": {"grade": "temiz-notr", "doygunluk": "yuksek",
                  "kontrast": "orta", "hex": ("#FFFFFF", "#111418", "#3D7BFF")},
        "ses": {"muzik": "ritmik", "muzik_db": -21.0, "sfx": "yogun",
                "ducking_db": -11.0},
        "medya": {"strateji": "karma", "footage_pct": 60.0,
                  "grafik_pct": 20.0, "ai_gorsel_yasak": False},
        "dagitim": {"oran": "16:9", "kanal": "youtube", "hedef_sn": 300.0,
                    "maks_sn": 900.0},
        # ⚠ Urun iddiasi (fiyat/performans) kaynak ister; reklam ayrimi atif ile.
        "kanit": {"lisans_beyaz_liste": LISANS_GENIS, "atif_zorunlu": True,
                  "min_bagimsiz_kaynak": 1.0, "arsiv_zorunlu": False,
                  "yer_kapisi": False},
        "qa": _qa(min_kesme=12.0),
    },
    "yasam-dinamik": {
        "ad": "Yasam / dinamik",
        "ozet": "Yemek, spor, moda, emlak — hizli ritim, gercek cekim agirlikli",
        "surum": "1.0.0",
        "anlatim": {"yapi": "liste", "acilis": "kanca", "kisi": "2.",
                    "bolum_basligi": False},
        "tempo": {"plan_sn": 3.0, "maks_plan_sn": 6.0, "kelime_plan": 9.0,
                  "dagilim": "cift-modlu"},
        "gecis": {"tur": "karisik", "sure_sn": 0.25, "oran_pct": 40.0},
        "kamera": {"hareket": "handheld", "yogunluk": 65.0, "zoom_tavan": 1.3},
        "tipografi": {"altyazi": "yogun", "baslik": "kinetik",
                      "guvenli_alan_pct": 10.0},
        "palet": {"grade": "sicak-canli", "doygunluk": "yuksek",
                  "kontrast": "orta", "hex": ("#F7F3EE", "#D9542B", "#2E6E4F")},
        "ses": {"muzik": "ritmik", "muzik_db": -20.0, "sfx": "yogun",
                "ducking_db": -11.0},
        "medya": {"strateji": "gercek-footage", "footage_pct": 80.0,
                  "grafik_pct": 10.0, "ai_gorsel_yasak": False},
        "dagitim": {"oran": "16:9", "kanal": "youtube", "hedef_sn": 300.0,
                    "maks_sn": 900.0},
        "kanit": {"lisans_beyaz_liste": LISANS_GENIS, "atif_zorunlu": True,
                  "min_bagimsiz_kaynak": 0.0, "arsiv_zorunlu": False,
                  "yer_kapisi": True},
        "qa": _qa(min_kesme=15.0),
    },
    "kultur-muzik": {
        "ad": "Kultur / muzik",
        "ozet": "Muzik one cikar, olculu tempo, dusuk ducking",
        "surum": "1.0.0",
        "anlatim": {"yapi": "bolumlu", "acilis": "baslik", "kisi": "3.",
                    "bolum_basligi": True},
        "tempo": {"plan_sn": 6.0, "maks_plan_sn": 10.0, "kelime_plan": 14.0,
                  "dagilim": "tek-modlu"},
        "gecis": {"tur": "crossfade", "sure_sn": 0.7, "oran_pct": 45.0},
        "kamera": {"hareket": "ken-burns", "yogunluk": 30.0, "zoom_tavan": 1.2},
        "tipografi": {"altyazi": "orta", "baslik": "sade",
                      "guvenli_alan_pct": 8.0},
        "palet": {"grade": "sicak-vintage", "doygunluk": "orta",
                  "kontrast": "orta", "hex": ("#221A16", "#C08552", "#EFE3D0")},
        # ⚠ Muzik icerikte one cikar; ducking sig tutulur ki muzik ezilmesin.
        "ses": {"muzik": "one-cikan", "muzik_db": -16.0, "sfx": "az",
                "ducking_db": -5.0},
        "medya": {"strateji": "gercek-footage", "footage_pct": 75.0,
                  "grafik_pct": 5.0, "ai_gorsel_yasak": False},
        "dagitim": {"oran": "16:9", "kanal": "youtube", "hedef_sn": 600.0,
                    "maks_sn": 1800.0},
        # ⚠ Muzik TELIF acisindan en riskli alan; beyaz liste KATI.
        "kanit": {"lisans_beyaz_liste": LISANS_KATI, "atif_zorunlu": True,
                  "min_bagimsiz_kaynak": 1.0, "arsiv_zorunlu": False,
                  "yer_kapisi": False},
        "qa": _qa(),
    },
}

VARSAYILAN_PROFIL = "belgesel-sinematik"

# ⚠ KONSEPT -> PROFIL KOPRUSU (Faz I-2a taksonomisi ile).
# Bu modul `taksonomi`yi IMPORT ETMEZ (dongu olmasin); anahtarlarin gercekten
# var oldugu TESTTE dogrulanir. Once tam yol, yoksa aile denenir.
KONSEPT_PROFIL = {
    "belgesel": "belgesel-sinematik",
    "belgesel.true_crime": "belgesel-arastirmaci",
    "belgesel.haber": "belgesel-arastirmaci",
    "seyahat": "seyahat-4k",
    "seyahat.ambient": "ambient-sakin",
    "egitim": "explainer-hizli",
    "egitim.bilim": "bilim-anlatisi",
    "egitim.finans": "bilim-anlatisi",
    "egitim.ders": "bilim-anlatisi",
    "hikaye": "hikaye-sinematik",
    "hikaye.korku": "korku-gerilim",
    "hikaye.cocuk": "cocuk-yumusak",
    "urun": "urun-tanitim",
    "yasam": "yasam-dinamik",
    "kultur": "kultur-muzik",
}

# Eski `pipeline.EDIT_STILLERI` kimlikleri -> yeni profil (geriye uyumluluk).
ESKI_EDIT_ESLEME = {
    "sinematik-belgesel": "belgesel-sinematik",
    "anlati-video-essay": "belgesel-sinematik",
    "seyahat-belgeseli": "seyahat-4k",
    "veri-anlatisi": "bilim-anlatisi",
    "hizli-explainer": "explainer-hizli",
}

# `eski_edit_stiline()` ciktisinin uretmesi gereken alanlar.
ESKI_EDIT_ANAHTARLARI = ("ad", "ozet", "sahne_sn", "maks_sahne_sn", "kelime",
                         "footage_pct", "overlay", "altyazi", "motion",
                         "gorsel_yasak", "grafik_pct", "bolumler")

# Surumu dondurulmus eski profiller: {(kimlik, surum): profil}
ARSIV = {}


# ═══════════════════════════ SEMA / DOGRULAMA ═══════════════════════════

def sema_uyumlu_mu(surum: str) -> bool:
    """MAJOR ayni mi? Farkliysa profil UYUMSUZ — sessiz kabul YOK."""
    try:
        return str(surum).split(".")[0] == SEMA_SURUM.split(".")[0]
    except Exception:
        return False


def dogrula(profil: dict) -> list:
    """Profili semaya gore dogrula. Donus: hata listesi (bos = gecerli).

    ⚠ FAZLA ALAN DA HATADIR: sessiz yazim yanlisi ("tempoo") kaydin yarisini
    devre disi birakirdi.
    """
    hata = []
    if not isinstance(profil, dict):
        return ["profil sozluk degil"]
    for zorunlu in ("ad", "ozet", "surum"):
        if not profil.get(zorunlu):
            hata.append(f"eksik ust alan: {zorunlu}")
    fazla_boyut = set(profil) - set(BOYUTLAR) - {"ad", "ozet", "surum", "turetilmis"}
    if fazla_boyut:
        hata.append(f"bilinmeyen boyut: {sorted(fazla_boyut)}")
    for boyut, alanlar in BOYUT_KURALI.items():
        deger = profil.get(boyut)
        if not isinstance(deger, dict):
            hata.append(f"eksik boyut: {boyut}")
            continue
        fazla = set(deger) - set(alanlar)
        if fazla:
            hata.append(f"{boyut}: bilinmeyen alan {sorted(fazla)}")
        for alan, (_kural, tip) in alanlar.items():
            if alan not in deger:
                hata.append(f"{boyut}.{alan} eksik")
                continue
            v = deger[alan]
            if tip is float and not isinstance(v, (int, float)):
                hata.append(f"{boyut}.{alan} sayi degil: {v!r}")
            elif tip is bool and not isinstance(v, bool):
                hata.append(f"{boyut}.{alan} bool degil: {v!r}")
            elif tip is str and not isinstance(v, str):
                hata.append(f"{boyut}.{alan} metin degil: {v!r}")
            elif tip is tuple and not isinstance(v, tuple):
                hata.append(f"{boyut}.{alan} demet degil: {v!r}")
    return hata


def kapsam_ozeti() -> dict:
    """Kaydin GERCEK kapsami — 'her stili biliyoruz' iddiasi kurmamak icin."""
    return {
        "sema_surum": SEMA_SURUM,
        "profil": len(PROFIL),
        "boyut": len(BOYUTLAR),
        "alan": sum(len(a) for a in BOYUT_KURALI.values()),
        "konsept_baglantisi": len(KONSEPT_PROFIL),
        "eski_esleme": len(ESKI_EDIT_ESLEME),
        "arsiv": len(ARSIV),
    }


# ═══════════════════════════ ERISIM ═══════════════════════════

def profil_al(kimlik: str, surum: str = None) -> dict:
    """Profili DERIN KOPYA olarak dondur. Bilinmeyen kimlik -> KeyError.

    `surum` verilirse once ARSIV'e bakilir; kayitli surum yoksa ve guncel
    surum de tutmuyorsa KeyError (sessizce baska surum DONDURULMEZ).
    """
    if surum is None:
        if kimlik not in PROFIL:
            raise KeyError(f"bilinmeyen stil profili: {kimlik}")
        return copy.deepcopy(PROFIL[kimlik])
    if (kimlik, surum) in ARSIV:
        return copy.deepcopy(ARSIV[(kimlik, surum)])
    guncel = PROFIL.get(kimlik)
    if guncel and guncel.get("surum") == surum:
        return copy.deepcopy(guncel)
    raise KeyError(f"stil profili surumu bulunamadi: {kimlik}@{surum}")


def arsivle(kimlik: str) -> tuple:
    """Guncel surumu ARSIV'e dondur. Profili DEGISTIRMEDEN ONCE cagrilir.

    ⚠ Cagrilmadan `surum` yukseltilirse eski isler yeniden uretilemez.
    Donus: (kimlik, surum).
    """
    p = PROFIL[kimlik]
    anahtar = (kimlik, p["surum"])
    ARSIV[anahtar] = copy.deepcopy(p)
    return anahtar


def surum_listesi(kimlik: str) -> list:
    """Bu profilin erisilebilir TUM surumleri (guncel + arsiv), sirali."""
    s = set()
    if kimlik in PROFIL:
        s.add(PROFIL[kimlik]["surum"])
    s |= {sv for (k, sv) in ARSIV if k == kimlik}
    return sorted(s)


# ═══════════════════════════ BIRLESTIRME ═══════════════════════════

def _birlestir_alan(kural: str, degerler: list, agirliklar: list):
    """Tek alani kurala gore birlestir. Kurallar `BOYUT_KURALI`dan gelir.

    ⚠ Bu fonksiyon ALAN ADI BILMEZ — bu yuzden yeni alan eklemek kodu
    degistirmez (tasarim kurali 2).
    """
    if kural == "ortalama":
        toplam_a = sum(agirliklar) or 1.0
        return round(sum(float(d) * a for d, a in zip(degerler, agirliklar))
                     / toplam_a, 3)
    if kural == "agirlikli-secim":
        # En yuksek agirlik kazanir; beraberlikte ILK ebeveyn (deterministik)
        en = max(range(len(degerler)), key=lambda i: (agirliklar[i], -i))
        return degerler[en]
    if kural == "birlesim":
        cikti = []
        for d in degerler:
            for x in d:
                if x not in cikti:
                    cikti.append(x)
        return tuple(cikti)
    if kural == "kesisim":
        ortak = set(degerler[0])
        for d in degerler[1:]:
            ortak &= set(d)
        if ortak:
            return tuple(x for x in degerler[0] if x in ortak)
        # ⚠ BOS KESISIM: hicbir lisans ortak degil. Bos liste "hicbir medya
        # kullanilamaz" demek olurdu. En agirlikli ebeveynin listesi alinir
        # ve bu durum `tureti()` gerekcesinde UYARI olarak raporlanir.
        en = max(range(len(degerler)), key=lambda i: (agirliklar[i], -i))
        return tuple(degerler[en])
    if kural == "en-kati-dogru":
        return any(bool(d) for d in degerler)
    if kural == "en-kati-maks":
        return max(float(d) for d in degerler)
    if kural == "en-kati-min":
        return min(float(d) for d in degerler)
    raise ValueError(f"bilinmeyen birlestirme kurali: {kural}")


def tureti(kimlikler, agirliklar=None, ad: str = None,
           kimlik: str = None) -> tuple:
    """Iki+ profilden MELEZ profil turet. Donus: (profil, gerekce).

    ⚠ CEKIRDEK KOD DEGISMEDEN: yeni bir melez stil icin `PROFIL`e satir
    yazmak GEREKMEZ. Bilinmeyen/melez istek burada turetilir.

    `gerekce` her alanin NEREDEN geldigini ve hangi kuralin uygulandigini
    soyler — kara kutu yok.
    """
    kimlikler = list(kimlikler)
    if len(kimlikler) < 2:
        raise ValueError("tureti: en az 2 profil gerekir")
    ebeveyn = [profil_al(k) for k in kimlikler]
    if agirliklar is None:
        agirliklar = [1.0] * len(kimlikler)
    if len(agirliklar) != len(kimlikler):
        raise ValueError("tureti: agirlik sayisi profil sayisiyla ayni olmali")
    agirliklar = [float(a) for a in agirliklar]
    if min(agirliklar) < 0 or sum(agirliklar) <= 0:
        raise ValueError("tureti: agirliklar negatif olamaz ve toplami > 0 olmali")

    en_agir = max(range(len(kimlikler)), key=lambda i: (agirliklar[i], -i))
    yeni = {
        "ad": ad or (" + ".join(p["ad"] for p in ebeveyn) + " (melez)"),
        "ozet": f"{len(kimlikler)} profilden turetilmis melez",
        "surum": SEMA_SURUM,
        "turetilmis": {"ebeveyn": kimlikler, "agirlik": agirliklar,
                       "kimlik": kimlik or "melez:" + "+".join(kimlikler)},
    }
    ayrinti, uyari = {}, []
    for boyut, alanlar in BOYUT_KURALI.items():
        yeni[boyut] = {}
        for alan, (kural, _tip) in alanlar.items():
            degerler = [p[boyut][alan] for p in ebeveyn]
            sonuc = _birlestir_alan(kural, degerler, agirliklar)
            yeni[boyut][alan] = sonuc
            if kural in ("agirlikli-secim",):
                kaynak = kimlikler[en_agir]
            elif kural == "en-kati-maks":
                kaynak = kimlikler[degerler.index(max(degerler, key=float))]
            elif kural == "en-kati-min":
                kaynak = kimlikler[degerler.index(min(degerler, key=float))]
            else:
                kaynak = "birlestirildi"
            ayrinti[f"{boyut}.{alan}"] = {"kural": kural, "kaynak": kaynak,
                                          "deger": sonuc}
            if kural == "kesisim" and not (set(degerler[0]).intersection(
                    *[set(d) for d in degerler[1:]])):
                uyari.append(f"{boyut}.{alan}: lisans kesisimi BOS, en agirlikli "
                             f"ebeveynin listesi kullanildi ({kimlikler[en_agir]})")

    gerekce = {
        "ebeveyn": kimlikler,
        "agirlik": agirliklar,
        "alan_sayisi": len(ayrinti),
        "alan": ayrinti,
        "uyari": uyari,
        "ozet": (f"{len(kimlikler)} profil birlestirildi; sayisal alanlar "
                 f"agirlikli ortalama, kategorik alanlar en agirlikli ebeveyn "
                 f"({kimlikler[en_agir]}), kanit/QA esikleri KATI taraf"),
    }
    return yeni, gerekce


# ═══════════════════════════ COZUM (Auto vs kullanici) ═══════════════════════════

def coz(*, kullanici_stili: str = None, konsept: dict = None,
        melez_esik: float = 0.60, varsayilan: str = VARSAYILAN_PROFIL) -> dict:
    """Hangi profil kullanilacak? KULLANICI SECIMI AUTO'YU YENER.

    `konsept`: `taksonomi.siniflandir()` ciktisi (opsiyonel). Bu modul
    `taksonomi`yi import ETMEZ; yalnizca sozluk alanlarini okur.

    Sira:
      1. Kullanicinin ACIK secimi (bilinen bir profil ise) -> kaynak="kullanici"
      2. Konsept "melez" ve iki dal farkli profile bakiyorsa -> TURETILIR
      3. Konsept tek profile bakiyorsa -> kaynak="auto"
      4. Hicbiri -> varsayilan, kaynak="varsayilan"

    ⚠ Kullanici BILINMEYEN bir stil verdiyse SESSIZCE yutulmaz: auto/varsayilana
    dusulur ve `gerekce` bunu acikca yazar.
    """
    sonuc = {"kimlik": None, "surum": None, "profil": None, "kaynak": None,
             "gerekce": "", "turetme": None, "uyari": []}

    if kullanici_stili:
        k = str(kullanici_stili).strip()
        hedef = k if k in PROFIL else ESKI_EDIT_ESLEME.get(k)
        if hedef:
            p = profil_al(hedef)
            sonuc.update({"kimlik": hedef, "surum": p["surum"], "profil": p,
                          "kaynak": "kullanici",
                          "gerekce": (f"kullanicinin acik secimi '{k}'"
                                      + ("" if k == hedef
                                         else f" -> '{hedef}' (eski kimlik esleme)")
                                      + "; Auto sonucu EZILDI")})
            return sonuc
        sonuc["uyari"].append(
            f"kullanicinin verdigi stil '{k}' kayitta YOK — sessizce "
            f"kabul edilmedi, otomatik secime dusuldu")

    if isinstance(konsept, dict) and konsept.get("yol") and konsept["yol"] != "belirsiz":
        yol = konsept["yol"]
        aile = konsept.get("aile") or yol.split(".")[0]
        birincil = KONSEPT_PROFIL.get(yol) or KONSEPT_PROFIL.get(aile)
        ikincil_yol = konsept.get("ikincil")
        ikincil = None
        if ikincil_yol:
            ikincil = (KONSEPT_PROFIL.get(ikincil_yol)
                       or KONSEPT_PROFIL.get(str(ikincil_yol).split(".")[0]))

        if birincil and ikincil and ikincil != birincil:
            # MELEZ: iki dal farkli profile bakiyor -> cekirdek kod degismeden turet
            g = float(konsept.get("guven") or 0.5)
            a1 = max(0.05, min(0.95, g))
            p, gerekce = tureti([birincil, ikincil], [a1, 1.0 - a1],
                                kimlik=f"melez:{birincil}+{ikincil}")
            sonuc.update({
                "kimlik": p["turetilmis"]["kimlik"], "surum": p["surum"],
                "profil": p, "kaynak": "turetilmis", "turetme": gerekce,
                "gerekce": (f"konsept MELEZ ({yol} + {ikincil_yol}); "
                            f"{birincil} x{a1:.2f} + {ikincil} x{1 - a1:.2f} "
                            f"turetildi")})
            sonuc["uyari"].extend(gerekce["uyari"])
            return sonuc

        if birincil:
            p = profil_al(birincil)
            sonuc.update({"kimlik": birincil, "surum": p["surum"], "profil": p,
                          "kaynak": "auto",
                          "gerekce": (f"konsept '{yol}' (guven "
                                      f"{konsept.get('guven')}) -> {birincil}")})
            return sonuc
        sonuc["uyari"].append(
            f"konsept '{yol}' icin profil baglantisi YOK — varsayilana dusuldu")

    p = profil_al(varsayilan)
    sonuc.update({"kimlik": varsayilan, "surum": p["surum"], "profil": p,
                  "kaynak": "varsayilan",
                  "gerekce": ("kullanici secimi ve guvenilir konsept yok; "
                              f"varsayilan '{varsayilan}'")})
    return sonuc


# ═══════════════════════════ GERIYE UYUMLULUK ═══════════════════════════

# Yeni sozlesme -> eski `pipeline.EDIT_STILLERI` alanlari.
_MOTION_ESLEME = {"sabit": "sinematik", "ken-burns": "sinematik",
                  "push-in": "anlati", "handheld": "hizli", "drone": "sinematik"}


def eski_edit_stiline(profil: dict) -> dict:
    """Bilesik profili eski `EDIT_STILLERI` bicimine cevir.

    ⚠ `pipeline.py` BU ADIMDA DEGISTIRILMEDI. Bu fonksiyon I-2c'de baglanacak
    koprudur; simdilik yalnizca sozlesmeyi ve testini sabitler.
    ⚠ Kayipsiz DEGIL: eski bicimde palet/ses/kanit/QA karsiligi YOKTUR.
    Bu yuzden yeni alanlar `_profil` altinda BIRLIKTE tasinir.
    """
    t, m, tip = profil["tempo"], profil["medya"], profil["tipografi"]
    return {
        "ad": profil["ad"],
        "ozet": profil["ozet"],
        "sahne_sn": t["plan_sn"],
        "maks_sahne_sn": t["maks_plan_sn"],
        "kelime": t["kelime_plan"],
        "footage_pct": m["footage_pct"],
        "overlay": ("yogun" if tip["baslik"] == "kinetik" else "yok"),
        "altyazi": tip["altyazi"],
        "motion": _MOTION_ESLEME.get(profil["kamera"]["hareket"], "sinematik"),
        "gorsel_yasak": m["ai_gorsel_yasak"],
        "grafik_pct": m["grafik_pct"],
        "bolumler": profil["anlatim"]["bolum_basligi"],
        # Eski bicimin tasiyamadigi boyutlar KAYBOLMASIN diye birlikte gider
        "_profil": {"surum": profil["surum"], "palet": profil["palet"],
                    "ses": profil["ses"], "kanit": profil["kanit"],
                    "qa": profil["qa"], "gecis": profil["gecis"],
                    "dagitim": profil["dagitim"]},
    }
