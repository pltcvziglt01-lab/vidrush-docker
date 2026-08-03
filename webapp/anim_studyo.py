#!/usr/bin/env python3
"""Animasyon Studyosu — sohbet tarzi tek panel.

Tasarim karari (Polat, 3 Agu 2026): "manuel secim kismini bitirelim". Kullanici
sadece REFERANS KARE + METIN verir; palet, isik, arka plan, stil dili hepsi
karelerden OLCULEREK cikarilir. Motor eksik gordugu seyi SORAR, sonra uretir.

Uc adim:
  1) /api/anim/analiz   — kareleri coz: karakter + stil + palet + isik (olculur)
  2) /api/anim/sorular  — analiz + metne bakip SADECE gerekli sorulari uretir
  3) /api/anim/uret     — hepsini birlestirip kuyruga atar
"""
import os
import json
import shutil

import pipeline as P

ANIM_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "veri", "anim")
os.makedirs(ANIM_DIR, exist_ok=True)


def oturum_dizini(oturum: str) -> str:
    if not P._PROFIL_RE.match(oturum or ""):
        raise ValueError("gecersiz oturum")
    d = os.path.join(ANIM_DIR, oturum)
    os.makedirs(d, exist_ok=True)
    return d


def _tr_ozet(sr: dict) -> dict:
    """Analiz sonucunu kullanicinin OKUYABILECEGI Turkce ozete cevir.
    Motorun ne anladigini gormeden onaylamak korlemesine olur."""
    k = sr.get("kimlik") or {}
    st = sr.get("stil") or {}
    o = sr.get("olcum") or {}
    p = o.get("parlaklik", 0)
    isik_tr = ("çok aydınlık" if p >= 175 else "aydınlık" if p >= 150
               else "orta" if p >= 120 else "karanlık")
    d = o.get("doygunluk", 0)
    doy_tr = "soluk/pastel" if d < 65 else "orta doygun" if d < 100 else "canlı/doygun"
    c = o.get("kontrast", 0)
    kon_tr = "yumuşak" if c < 35 else "belirgin" if c < 55 else "sert/keskin"
    return {
        "karakter": {
            "tur": k.get("tur", ""),
            "govde_rengi": k.get("govde_rengi", ""),
            "kafa": k.get("kafa", ""),
            "gozler": k.get("gozler", ""),
            "sac": k.get("sac", ""),
            "kiyafet": k.get("kiyafet", ""),
            "ayirt_edici": k.get("ayirt_edici", ""),
            "guven": k.get("_guven"),
        },
        "stil": {
            "medyum": st.get("medyum", ""),
            "cizgi": st.get("cizgi", ""),
            "golgeleme": st.get("golgeleme", ""),
            "doku": st.get("doku", ""),
            "isik_tarifi": st.get("isik", ""),
            "detay": st.get("detay", ""),
            "ruh": st.get("ruh", ""),
            "arka_plan_yogunlugu": st.get("arka_plan", ""),
            "guven": st.get("_guven"),
        },
        "olcum": {**o, "isik_tr": isik_tr, "doygunluk_tr": doy_tr, "kontrast_tr": kon_tr},
        "palet": sr.get("palet_hex") or [],
        "kare_sayisi": sr.get("kare_sayisi", 0),
    }


def analiz_yap(oturum: str, yollar: list) -> dict:
    d = oturum_dizini(oturum)
    sr = P.sahne_referansi(yollar)
    if not sr:
        return {"ok": False, "hata": "Referans kareler çözümlenemedi — daha net kareler yükleyin."}
    ozet = _tr_ozet(sr)
    # Uretimde aynen kullanilmak uzere sakla (yeniden analiz = bosa para)
    with open(os.path.join(d, "analiz.json"), "w", encoding="utf-8") as f:
        json.dump({"ozet": ozet, "yollar": yollar}, f, ensure_ascii=False)
    return {"ok": True, **ozet}


def analiz_oku(oturum: str) -> dict:
    try:
        with open(os.path.join(oturum_dizini(oturum), "analiz.json"), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def temizle(oturum: str):
    try:
        shutil.rmtree(oturum_dizini(oturum), ignore_errors=True)
    except Exception:
        pass


# Motorun sorabilecegi sabit alanlar — LLM bunlarin DISINA cikamaz, boylece
# arayuz her cevabi tanidigi bir alana yazabilir.
SORU_ALANLARI = {
    "sure_dk": "Video kaç dakika olsun?",
    "dil": "Anlatım hangi dilde olsun?",
    "anlatici": "Anlatıcı kim olsun (yaş/cinsiyet)?",
    "ton": "Anlatım tonu nasıl olsun?",
    "hedef_kitle": "Kimler izleyecek?",
    "altyazi": "Altyazı olsun mu?",
}


def sorular_uret(oturum: str, metin: str) -> dict:
    """Analiz + metne bakip SADECE gercekten eksik olani sorar. Her sey belliyse hic sormaz."""
    kayit = analiz_oku(oturum)
    ozet = kayit.get("ozet") or {}
    if not (metin or "").strip():
        return {"ok": True, "sorular": [{"alan": "metin", "soru": "Videonun metnini yapıştır.",
                                         "secenekler": []}]}
    istek = (
        "You are a video production assistant. Below is (1) the user's narration script and "
        "(2) what we already extracted from their reference frames. Decide what you still MUST "
        "ask before producing the video. Ask AT MOST 3 questions, and ONLY about things you "
        "cannot infer. If the script already makes something obvious (its language, its length, "
        "its tone, its audience), DO NOT ask about it.\n"
        f"ALLOWED FIELDS (use these exact keys): {', '.join(SORU_ALANLARI)}\n"
        "Return STRICT JSON: {\"sorular\": [{\"alan\": <key>, \"soru\": <question in TURKISH>, "
        "\"secenekler\": [<2-4 short Turkish quick answers>]}]}. "
        "If nothing needs asking, return {\"sorular\": []}.\n\n"
        f"SCRIPT (first 1200 chars):\n{metin[:1200]}\n\n"
        f"ALREADY KNOWN FROM REFERENCE FRAMES:\n{json.dumps(ozet, ensure_ascii=False)[:1200]}"
    )
    try:
        j = P.oai_chat({"model": "gpt-4.1-mini",
                        "messages": [{"role": "user", "content": istek}],
                        "response_format": {"type": "json_object"},
                        "max_tokens": 600, "temperature": 0.2}, timeout=60)
        ic = json.loads(j["choices"][0]["message"]["content"])
        sorular = [s for s in (ic.get("sorular") or []) if s.get("alan") in SORU_ALANLARI][:3]
        return {"ok": True, "sorular": sorular}
    except P.BakiyeHatasi as e:
        return {"ok": False, "hata": str(e)}
    except Exception as e:
        # Soru uretilemezse AKIS DURMASIN: makul varsayilanlarla devam edilir
        print(f"  sorular_uret hata: {str(e)[:140]}")
        return {"ok": True, "sorular": []}
