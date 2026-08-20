#!/usr/bin/env python3
"""BEYIN — SENKRON MOD: metin -> cumle basina Flow promptu.

⚠ URETIM BURADA DEGIL: bu modul yalnizca cumleleri SINEMATIK INGILIZCE
prompta cevirir; gorsel/video uretimini yine Flow ajani yapar
(flow_surucu.parti_uret).

KURAL (kullanicinin urun tarifi): ilk ~%20 cumle VIDEO, kalani GORSEL.
Her cikti Telegram'a DAYANDIGI CUMLEYLE birlikte gonderilir — eslesme
bu moduldeki sira uzerinden tasinir.
"""
from __future__ import annotations

import json
import math
import os
import re
import urllib.request

from . import ayar  # gizli.env'i yukler (HAYALET_OPENAI_KEY)

OPENAI_KEY = os.environ.get("HAYALET_OPENAI_KEY",
                            os.environ.get("OPENAI_API_KEY", ""))
MODEL = os.environ.get("HAYALET_LLM_MODEL", "gpt-4.1-mini")
VIDEO_ORANI = float(os.environ.get("HAYALET_SENKRON_VIDEO_ORANI", "0.20"))

_CUMLE = re.compile(r"[^.!?…]+[.!?…]+|[^.!?…]+$")


def cumlelere_bol(metin: str) -> list:
    return [c.strip() for c in _CUMLE.findall(metin or "") if c.strip()]


def _oai(mesajlar, zaman_asimi=120) -> str:
    govde = json.dumps({"model": MODEL, "messages": mesajlar,
                        "response_format": {"type": "json_object"},
                        "temperature": 0.4}).encode()
    istek = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions", data=govde,
        headers={"Authorization": f"Bearer {OPENAI_KEY}",
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(istek, timeout=zaman_asimi) as y:
        return json.load(y)["choices"][0]["message"]["content"]


def plan_kur(metin: str, bildir=None) -> list:
    """Metin -> [{"sira", "cumle", "tur", "prompt"}].

    ⚠ LLM COKERSE IS OLMEZ: dusus promptu cumlenin kendisi + sinematik
    sabit sondur; kullanici bunu Telegram'da GORUR (sessiz dusus yok).
    """
    cumleler = cumlelere_bol(metin)
    if not cumleler:
        return []
    n_video = max(1, math.ceil(len(cumleler) * VIDEO_ORANI))
    plan = []
    if OPENAI_KEY:
        try:
            sistem = (
                "You turn a narration script into Flow generation prompts. "
                "For EVERY numbered sentence, write ONE cinematic, "
                "photorealistic ENGLISH prompt that visually depicts that "
                "exact sentence (setting, subject, light, camera). "
                "No text/watermark in image. Return JSON: "
                '{"items":[{"i":<number>,"prompt":"..."}]} with EXACTLY '
                f"{len(cumleler)} items, same numbering.")
            girdi = "\n".join(f"{i+1}. {c}" for i, c in enumerate(cumleler))
            cevap = json.loads(_oai([{"role": "system", "content": sistem},
                                     {"role": "user", "content": girdi}]))
            eslesme = {int(x["i"]): str(x.get("prompt", "")).strip()
                       for x in cevap.get("items", []) if x.get("i")}
        except Exception as e:                               # noqa: BLE001
            eslesme = {}
            if bildir:
                bildir(f"⚠ LLM plani dusdu ({type(e).__name__}) — "
                       f"cumleler dogrudan prompt olarak kullanilacak")
    else:
        eslesme = {}
        if bildir:
            bildir("⚠ LLM anahtari yok — cumleler dogrudan prompt olacak")
    for i, cumle in enumerate(cumleler, 1):
        prompt = eslesme.get(i) or (
            cumle + " — cinematic, photorealistic, natural light, 35mm")
        plan.append({"sira": i, "cumle": cumle,
                     "tur": "video" if i <= n_video else "gorsel",
                     "prompt": prompt})
    return plan
