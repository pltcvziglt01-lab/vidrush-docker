#!/usr/bin/env python3
"""IS SOZLESMESI — tek tip, geriye donuk uyumlu is (job) temsili.

⚠ NEDEN VAR (Faz H envanteri, 12 Agu 2026): backend ile arayuz AYNI SEYE FARKLI
ADLAR veriyordu ve bu sessiz kirikliklar uretmisti:

  · `/api/generate` -> `job_id` doner, `wizard.js` `cevap.job/is_id/id` okurdu
    -> is kimligi HER ZAMAN bos kaliyordu.
  · `/api/isler` -> `ilerleme` doner, `bilesenler.js` `is.yuzde` okurdu
    -> ilerleme cubugu HER ZAMAN %0 gorunuyordu.
  · Uretilen video `video` alaninda geliyordu ama arayuzde OYNAT/INDIR yoktu.

Cozum tek bir sozluk uretmek DEGIL, TEK BIR URETICI kullanmak: her uc ayni
`normalize()`den geciyor. Yeni (ingilizce, makine dostu) adlar ile ESKI
turkce adlar BIRLIKTE donuyor; boylece dagitim sirasi onemli olmuyor
(eski arayuz yeni backend'le, yeni arayuz eski kayitlarla calisir).

ALAN SOZLESMESI
    job_id      str    is kimligi
    status      str    queued | running | done | error
    progress    int    0-100
    stage       str    makine-okunur asama anahtari (ASAMALAR)
    stage_ad    str    asamanin Turkce adi (arayuz gosterir)
    message     str    serbest metin ilerleme mesaji
    video_url   str    goreli yol (ornek "ciktilar/job_x.mp4") ya da ""
    cover_url   str    kapak gorseli goreli yolu ya da ""
    error       str    hata metni ya da ""
    qa          dict   uretim sonrasi olcum (bos dict = olculmedi)
    attribution list   kullanilan kaynaklarin atif listesi
    research    dict   arastirma ozeti (kaynak/iddia sayilari)
    fallbacks   list   [{asama, neden, etki}] — GORUNUR kalite dususleri
    warning     str    kullaniciya gosterilecek uyari
    duration    float  video suresi (sn) ya da None
    scene_count int    sahne sayisi ya da None
    queue_*     int    kuyruk sirasi/toplami (yalnizca beklerken)

⚠ ESKI ALANLAR SILINMEZ: durum, ilerleme, yuzde, mesaj, video, kapak, hata,
atiflar, uyari, sure, sahne_sayisi. Bunlar hala doluyor.
"""
from __future__ import annotations

# Eski turkce durum -> yeni makine-okunur durum
DURUM_ESLEME = {
    "kuyrukta": "queued",
    "uretiliyor": "running",
    "bitti": "done",
    "hata": "error",
}
DURUM_TERS = {v: k for k, v in DURUM_ESLEME.items()}

# ⚠ ASAMA ARALIKLARI UYDURULMADI. `pipeline.py`nin GERCEK `bildir(mesaj, yuzde)`
# cagrilarindan cikarildi:
#   2-3 arastirma · 3-4 referans analizi · 5 plan · 6 kurgu analizi
#   7-71 sahne medyasi + seslendirme · 72 kapak · 78 render
#   96 ses mastering · 98 tamamlaniyor
# Aralik degisirse BURASI da guncellenmeli; test bunu kilitliyor.
ASAMALAR = [
    (0, "sirada", "Sırada"),
    (2, "arastirma", "Araştırma ve doğrulama"),
    (5, "plan", "Senaryo planı"),
    (7, "medya", "Medya ve seslendirme"),
    (72, "kapak", "Kapak"),
    (78, "render", "Render"),
    (96, "ses", "Ses seviyeleme"),
    (98, "tamamlaniyor", "Tamamlanıyor"),
]


def asama_coz(durum: str, yuzde) -> tuple:
    """(stage, stage_ad). Durum bittiyse/hatalıysa yuzdeye BAKILMAZ."""
    d = str(durum or "")
    if d in ("bitti", "done"):
        return "bitti", "Tamamlandı"
    if d in ("hata", "error"):
        return "hata", "Hata"
    if d in ("kuyrukta", "queued"):
        return "sirada", "Sırada"
    try:
        y = int(yuzde or 0)
    except (TypeError, ValueError):
        y = 0
    secili = ASAMALAR[0]
    for esik, anahtar, ad in ASAMALAR:
        if y >= esik:
            secili = (esik, anahtar, ad)
    return secili[1], secili[2]


def _sayi(v, varsayilan=0):
    try:
        return int(v)
    except (TypeError, ValueError):
        return varsayilan


def _imzali(yol, imzalayici):
    """Goreli cikti yolunu imzali baglantiya cevir. Imzalayici yoksa AYNEN doner."""
    y = str(yol or "")
    if not y or not callable(imzalayici):
        return y
    ad = y.split("/")[-1].split("?")[0]
    return imzalayici(ad) or y


def normalize(is_id: str, ham: dict, *, kuyruk_sira=None, kuyruk_toplam=None,
              zaman=None, imzalayici=None) -> dict:
    """Ham is sozlugunu TEK TIP sozlesmeye cevir (eski alanlar korunur).

    `ham` bellekten ya da diskteki durum dosyasindan gelebilir; ikisi de ayni
    semayi kullaniyor. Eksik alan varsa UYDURULMAZ, notr varsayilan konur.
    """
    ham = dict(ham or {})
    durum_ham = str(ham.get("durum") or ham.get("status") or "kuyrukta")
    status = DURUM_ESLEME.get(durum_ham, durum_ham if durum_ham in
                              DURUM_TERS else "queued")
    # Ilerleme: eski adlarin hepsini kabul et (yuzde dahil — arayuz onu okuyordu)
    ilerleme = _sayi(ham.get("ilerleme", ham.get("progress", ham.get("yuzde", 0))))
    ilerleme = max(0, min(100, ilerleme))
    if status == "done":
        ilerleme = 100
    stage, stage_ad = asama_coz(durum_ham, ilerleme)

    arastirma = ham.get("arastirma") or {}
    # ⚠ Dususler iki yerden gelebilir: arastirma koprusunden ve render/QA
    # asamasindan. Ikisi de AYNI listede birlesir — kullanici tek yerde gorur.
    dususler = list(ham.get("dususler") or [])
    for d in (arastirma.get("dususler") or []):
        if d not in dususler:
            dususler.append(d)

    # ⚠ FAZ H — QA FAIL ISI "BASARILI" GOSTERMEZ.
    # Kullanici kurali: "QA FAIL ise is basarili gorunmesin". Videoyu SILMEK
    # ya da durumu "hata" yapmak yanlis olurdu (dosya var ve indirilebilir),
    # bu yuzden ayri bir KALITE ekseni tutuluyor: arayuz "Tamamlandi" yerine
    # "Kalite: BASARISIZ" rozetini kirmizi gosterir.
    qa = ham.get("qa") or {}
    kalite = str(qa.get("durum") or "").upper() or "OLCULMEDI"
    kalite_ok = kalite in ("PASS", "KAPALI")

    yeni = {
        # ── YENI SOZLESME ──
        "job_id": is_id,
        "status": status,
        "progress": ilerleme,
        "stage": stage,
        "stage_ad": stage_ad,
        "message": str(ham.get("mesaj") or ham.get("message") or ""),
        # ⚠ FAZ R-1a: `video_url` artik IMZALI ve SURELI. `imzalayici`
        # verilmezse ESKI davranis (imzasiz goreli yol) korunur — cagiran
        # taraf (server) imzalayiciyi GECER; testler ikisini de kosar.
        "video_url": _imzali(ham.get("video") or ham.get("video_url") or "",
                             imzalayici),
        # ⚠ FAZ R-1d-a: kapak da `/ciktilar/` altinda duruyor ve o uc artik
        # TENANT KORUMALI imza istiyor. Imzalanmazsa arayuzdeki kapak 403
        # alirdi — video_url ile AYNI imzalayicidan geciyor.
        "cover_url": _imzali(ham.get("kapak") or ham.get("cover_url") or "",
                             imzalayici),
        "error": str(ham.get("hata") or ham.get("error") or ""),
        "qa": qa,
        # PASS/WARN/FAIL/OLCULEMEDI/OLCULMEDI/KAPALI
        "kalite": kalite,
        "kalite_ok": kalite_ok,
        "attribution": ham.get("atiflar") or ham.get("attribution") or [],
        "sources": ham.get("kaynaklar") or [],
        # ⚠ FAZ R-1a: arastirma manifesti de IMZALI baglanti ile verilir;
        # arayuz artik ham `ciktilar/...` yolu KURMAZ (o yol 403 doner).
        "research": (dict(arastirma,
                          manifest_url=_imzali(arastirma.get("manifest"),
                                               imzalayici))
                     if isinstance(arastirma, dict)
                     and arastirma.get("manifest") else arastirma),
        "fallbacks": dususler,
        "warning": str(ham.get("uyari") or ham.get("warning") or ""),
        "duration": ham.get("sure"),
        "scene_count": ham.get("sahne_sayisi"),
        "edit": ham.get("edit") or "",

        # ── ESKI ALANLAR (SILINMEZ — eski arayuz bunlari okuyor) ──
        "id": is_id,
        "is_id": is_id,
        "durum": durum_ham,
        "ilerleme": ilerleme,
        "yuzde": ilerleme,          # bilesenler.js bu adi okuyordu
        "mesaj": str(ham.get("mesaj") or ""),
        "video": ham.get("video"),
        "kapak": ham.get("kapak"),
        "hata": ham.get("hata"),
        "atiflar": ham.get("atiflar") or [],
        "uyari": ham.get("uyari"),
        "sure": ham.get("sure"),
        "sahne_sayisi": ham.get("sahne_sayisi"),
    }
    if kuyruk_sira is not None:
        yeni["queue_position"] = kuyruk_sira
        yeni["kuyruk_sira"] = kuyruk_sira
    if kuyruk_toplam is not None:
        yeni["queue_total"] = kuyruk_toplam
        yeni["kuyruk_toplam"] = kuyruk_toplam
    if zaman is not None:
        yeni["t"] = zaman
    return yeni
