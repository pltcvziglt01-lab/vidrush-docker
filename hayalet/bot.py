#!/usr/bin/env python3
"""HAYALET TELEGRAM BOTU — /basla de, scripti at, gerisi otomatik.

KAPSAM (kullanici karari, 20 Agu 2026):
  · YALNIZCA uretim + indirme + klasorleme. KURGU/EDIT YOK.
  · Telegram = TAKIP KANALI: ilerleme + hata bildirir, DOSYA GONDERMEZ.
  · AKIS BILEREK BASIT (kullanici: "fazla karmasiklastirma"):
        /basla  ->  bot scripti ister  ->  script gelir  ->  uretim baslar

SCRIPT BICIMI (tek mesaj):
    video:
    bir balikci teknesi safakta limandan cikiyor
    dalgalar guverteyi dovuyor
    gorsel:
    yasli balikcinin yakin plan portresi
    limanda mezat sabahi

  · "video:" satirindan sonrakiler VIDEO, "gorsel:" sonrakiler GORSEL promptu.
  · Hic baslik yoksa TUM satirlar GORSEL sayilir (en yaygin kullanim).
"""
from __future__ import annotations

import asyncio
import json
import re
import time
from pathlib import Path

from telegram import Update
from telegram.ext import (Application, CommandHandler, MessageHandler, filters)

from . import ayar, flow_surucu

_BEKLENEN = set()    # /basla demis, script bekleyen sohbetler
_CALISAN = set()     # su an uretimde olan sohbetler (cifte /basla engeli)
_IPTAL = set()
_SON_IS = {}         # sohbet_id -> son is sozlugu (/durum icin)


def _script_coz(metin: str) -> tuple:
    """Script -> (video_promptlari, gorsel_promptlari).

    ⚠ Baslik yoksa hepsi GORSEL: kullanici cogu zaman yalniz gorsel uretir;
    bos video listesi sorun degil, YANLIS SINIFLAMA sorundur.
    """
    videolar, gorseller = [], []
    hedef = gorseller
    for satir in (metin or "").splitlines():
        s = satir.strip()
        if not s:
            continue
        b = s.lower().rstrip(":")
        if b in ("video", "videolar"):
            hedef = videolar
            continue
        if b in ("gorsel", "görsel", "gorseller", "görseller", "image", "images"):
            hedef = gorseller
            continue
        hedef.append(s)
    return videolar, gorseller


def _kaydet(is_: dict) -> None:
    Path(is_["dizin"], "is.json").write_text(
        json.dumps(is_, ensure_ascii=False, indent=2), encoding="utf-8")


def _izinli(update: Update) -> bool:
    if not ayar.IZINLI_KULLANICILAR:
        return True
    return str(update.effective_user.id) in ayar.IZINLI_KULLANICILAR


async def komut_start(update: Update, _ctx):
    await update.message.reply_text(
        "👻 *Hayalet* hazır.\n\n"
        "`/basla` yaz → scripti iste­diğimde tek mesajda gönder:\n\n"
        "```\nvideo:\nprompt 1\nprompt 2\ngorsel:\nprompt 3\nprompt 4\n```\n"
        "Başlık koymazsan hepsini *görsel* sayarım.\n"
        "Dosyalar bilgisayarına iner; buraya sadece durum düşer.\n"
        "`/durum` · `/iptal`", parse_mode="Markdown")


async def komut_basla(update: Update, _ctx):
    if not _izinli(update):
        return
    sohbet = update.effective_chat.id
    if sohbet in _CALISAN:
        await update.message.reply_text(
            "⏳ Zaten bir üretim çalışıyor. `/iptal` ile durdurabilirsin.")
        return
    _BEKLENEN.add(sohbet)
    await update.message.reply_text(
        "📜 Scripti gönder (tek mesaj):\n\n"
        "```\nvideo:\nprompt 1\nprompt 2\ngorsel:\nprompt 3\n```\n"
        "Başlık yoksa hepsi görsel sayılır.", parse_mode="Markdown")


async def komut_iptal(update: Update, _ctx):
    sohbet = update.effective_chat.id
    _BEKLENEN.discard(sohbet)
    if sohbet in _CALISAN:
        _IPTAL.add(sohbet)
        await update.message.reply_text("🛑 İptal istendi — sıradaki prompttan sonra durur.")
    else:
        await update.message.reply_text("🛑 Bekleyen iş yok, script isteği iptal edildi.")


async def komut_durum(update: Update, _ctx):
    is_ = _SON_IS.get(update.effective_chat.id)
    if not is_:
        await update.message.reply_text("Henüz iş yok. `/basla` yaz.")
        return
    await update.message.reply_text(
        f"📋 *{is_['ad']}* — {is_['durum']}\n"
        f"🎬 video: {len(is_['video_promptlari'])} · "
        f"🖼 görsel: {len(is_['gorsel_promptlari'])} · "
        f"⚠ hata: {len(is_['hatalar'])}\n"
        f"📁 `{is_['dizin']}`", parse_mode="Markdown")


async def metin_geldi(update: Update, ctx):
    if not _izinli(update):
        return
    sohbet = update.effective_chat.id
    if sohbet not in _BEKLENEN:
        await update.message.reply_text("Üretim için `/basla` yaz.")
        return
    _BEKLENEN.discard(sohbet)

    videolar, gorseller = _script_coz(update.message.text)
    if not (videolar or gorseller):
        _BEKLENEN.add(sohbet)          # bos mesaj: beklemeye devam
        await update.message.reply_text("Script boş görünüyor — tekrar gönder.")
        return

    ad = f"is_{time.strftime('%Y%m%d_%H%M%S')}"
    d = ayar.is_dizini(ad)
    is_ = {"ad": ad, "dizin": str(d), "video_promptlari": videolar,
           "gorsel_promptlari": gorseller, "durum": "uretim",
           "sonuclar": {}, "hatalar": []}
    _SON_IS[sohbet] = is_
    _kaydet(is_)
    _CALISAN.add(sohbet)
    _IPTAL.discard(sohbet)
    await update.message.reply_text(
        f"🚀 Başlıyorum — 🎬 {len(videolar)} video + 🖼 {len(gorseller)} görsel.\n"
        f"📁 `{d}`\n(Chrome açık ve Flow'a giriş yapılmış olmalı.)",
        parse_mode="Markdown")

    kuyruk: asyncio.Queue = asyncio.Queue()

    def bildir(m):
        try:
            kuyruk.put_nowait(m)
        except Exception:
            pass

    async def akitici():
        while True:
            m = await kuyruk.get()
            if m is None:
                break
            try:
                await ctx.bot.send_message(sohbet, m[:400])
            except Exception:
                pass

    akit = asyncio.create_task(akitici())

    def iptal_mi():
        return sohbet in _IPTAL

    try:
        vids = await asyncio.to_thread(
            flow_surucu.toplu_uret, videolar, "video", d / "videolar",
            bildir, iptal_mi)
        gors = await asyncio.to_thread(
            flow_surucu.toplu_uret, gorseller, "gorsel", d / "gorseller",
            bildir, iptal_mi)
        is_["sonuclar"] = {"video": vids, "gorsel": gors}
        hatalar = [f"{x['tur']}[{x['sira']}] {x['neden']}"
                   for x in (vids + gors) if not x["ok"]]
        is_["hatalar"] = hatalar
        is_["durum"] = "bitti" if not hatalar else "bitti-eksikli"
        _kaydet(is_)
        ok_v = sum(1 for x in vids if x["ok"])
        ok_g = sum(1 for x in gors if x["ok"])
        ozet = (f"✅ *BİTTİ*\n🎬 {ok_v}/{len(vids)} video · "
                f"🖼 {ok_g}/{len(gors)} görsel\n📁 `{d}`")
        if hatalar:
            ilk = "\n".join(f"• {h}" for h in hatalar[:8])
            ozet += (f"\n\n⚠ *{len(hatalar)} başarısız:*\n{ilk}"
                     + ("\n… tamamı is.json içinde" if len(hatalar) > 8 else ""))
        else:
            ozet += "\n👍 Hata yok."
        await ctx.bot.send_message(sohbet, ozet, parse_mode="Markdown")
    except Exception as e:                                   # noqa: BLE001
        is_["durum"] = "hata"
        is_["hatalar"].append(f"{type(e).__name__}: {e}")
        _kaydet(is_)
        await ctx.bot.send_message(
            sohbet, f"❌ Beklenmeyen hata: {type(e).__name__}: {str(e)[:200]}")
    finally:
        _CALISAN.discard(sohbet)
        _IPTAL.discard(sohbet)
        await kuyruk.put(None)
        await akit


def calistir():
    eksik = ayar.eksik_ayarlar()
    if eksik:
        print("EKSIK AYAR:")
        for e in eksik:
            print(f"  · {e}")
        raise SystemExit(1)
    app = Application.builder().token(ayar.TELEGRAM_TOKEN).build()
    for ad, fn in (("start", komut_start), ("basla", komut_basla),
                   ("durum", komut_durum), ("iptal", komut_iptal)):
        app.add_handler(CommandHandler(ad, fn))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, metin_geldi))
    print(f"👻 Hayalet calisiyor. Klasor koku: {ayar.KOK}")
    app.run_polling()


if __name__ == "__main__":
    calistir()
