#!/usr/bin/env python3
"""HAYALET TELEGRAM BOTU — Flow'da uret, bilgisayara indir, klasorle.

KAPSAM (kullanici karari, 20 Agu 2026):
  · YALNIZCA uretim + indirme + klasorleme. KURGU/EDIT YOK (kullanici kendi yapar).
  · Telegram = TAKIP KANALI. Cikti dosyalari Telegram'a GONDERILMEZ; diskte kalir.
  · Hata varsa BILDIRIR; sorun yoksa "devam ediyorum" der. Sessiz dusus YOK.

AKIS:
  /yeni <ad>   -> klasor acilir
  /video       -> sonraki mesajlar VIDEO promptlari (her satir bir prompt)
  /gorsel      -> sonraki mesajlar GORSEL promptlari
  /basla       -> Flow'da uretir, indirir, klasorler
  /durum       -> kunye        /iptal -> calisan isi durdurur
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

_ISLER = {}          # sohbet_id -> is sozlugu
_TOPLAMA = {}        # sohbet_id -> "video" | "gorsel" | None
_IPTAL = set()       # iptal istenen sohbetler


def _yeni_is(ad: str) -> dict:
    ad = re.sub(r"[^A-Za-z0-9_-]+", "_", ad).strip("_") or f"is_{int(time.time())}"
    d = ayar.is_dizini(ad)
    return {"ad": ad, "dizin": str(d), "video_promptlari": [],
            "gorsel_promptlari": [], "durum": "hazirlik",
            "sonuclar": {}, "hatalar": []}


def _kaydet(is_: dict) -> None:
    Path(is_["dizin"], "is.json").write_text(
        json.dumps(is_, ensure_ascii=False, indent=2), encoding="utf-8")


def _izinli(update: Update) -> bool:
    if not ayar.IZINLI_KULLANICILAR:
        return True
    return str(update.effective_user.id) in ayar.IZINLI_KULLANICILAR


async def komut_start(update: Update, _ctx):
    await update.message.reply_text(
        "👻 *Hayalet* hazır — Flow'da üretir, bilgisayarına indirir.\n\n"
        "1️⃣ `/yeni proje_adi`\n"
        "2️⃣ `/video` → video promptlarını gönder (her satır bir prompt)\n"
        "3️⃣ `/gorsel` → görsel promptlarını gönder\n"
        "4️⃣ `/basla`\n\n"
        "Dosyalar bilgisayarına iner; buraya sadece *durum ve hata* düşer.\n"
        "`/durum` künye · `/iptal` durdur", parse_mode="Markdown")


async def komut_yeni(update: Update, ctx):
    if not _izinli(update):
        return
    ad = " ".join(ctx.args) if ctx.args else f"is_{int(time.time())}"
    is_ = _yeni_is(ad)
    _ISLER[update.effective_chat.id] = is_
    _TOPLAMA[update.effective_chat.id] = None
    _kaydet(is_)
    await update.message.reply_text(
        f"📁 Yeni iş: *{is_['ad']}*\n`{is_['dizin']}`\n\n"
        f"`/video` ya da `/gorsel` ile promptları gönder.",
        parse_mode="Markdown")


async def komut_video(update: Update, _ctx):
    _TOPLAMA[update.effective_chat.id] = "video"
    await update.message.reply_text("🎬 VIDEO modu — promptları gönder (her satır bir prompt).")


async def komut_gorsel(update: Update, _ctx):
    _TOPLAMA[update.effective_chat.id] = "gorsel"
    await update.message.reply_text("🖼 GÖRSEL modu — promptları gönder (her satır bir prompt).")


async def komut_iptal(update: Update, _ctx):
    _IPTAL.add(update.effective_chat.id)
    await update.message.reply_text("🛑 İptal istendi — sıradaki prompttan sonra duracak.")


async def komut_durum(update: Update, _ctx):
    is_ = _ISLER.get(update.effective_chat.id)
    if not is_:
        await update.message.reply_text("Aktif iş yok. `/yeni proje_adi`")
        return
    await update.message.reply_text(
        f"📋 *{is_['ad']}* — {is_['durum']}\n"
        f"🎬 video prompt: {len(is_['video_promptlari'])}\n"
        f"🖼 görsel prompt: {len(is_['gorsel_promptlari'])}\n"
        f"⚠ hata: {len(is_['hatalar'])}\n"
        f"📁 `{is_['dizin']}`", parse_mode="Markdown")


async def metin_geldi(update: Update, _ctx):
    if not _izinli(update):
        return
    sohbet = update.effective_chat.id
    is_ = _ISLER.get(sohbet)
    if not is_:
        await update.message.reply_text("Önce `/yeni proje_adi`.")
        return
    mod = _TOPLAMA.get(sohbet)
    if mod not in ("video", "gorsel"):
        await update.message.reply_text("Önce `/video` ya da `/gorsel` yaz.")
        return
    satirlar = [s.strip() for s in (update.message.text or "").splitlines() if s.strip()]
    anahtar = "video_promptlari" if mod == "video" else "gorsel_promptlari"
    is_[anahtar].extend(satirlar)
    _kaydet(is_)
    await update.message.reply_text(
        f"➕ {len(satirlar)} {mod} promptu eklendi (toplam {len(is_[anahtar])}).")


async def komut_basla(update: Update, ctx):
    if not _izinli(update):
        return
    sohbet = update.effective_chat.id
    is_ = _ISLER.get(sohbet)
    if not is_:
        await update.message.reply_text("Önce `/yeni proje_adi`.")
        return
    if not (is_["video_promptlari"] or is_["gorsel_promptlari"]):
        await update.message.reply_text("❌ Hiç prompt yok.")
        return
    _IPTAL.discard(sohbet)
    is_["durum"] = "uretim"
    _kaydet(is_)
    toplam = len(is_["video_promptlari"]) + len(is_["gorsel_promptlari"])
    await update.message.reply_text(
        f"🚀 Başlıyorum — {toplam} prompt.\n"
        f"Chrome açık ve Flow'a giriş yapılmış olmalı.\n"
        f"📁 `{is_['dizin']}`", parse_mode="Markdown")

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
    d = Path(is_["dizin"])

    def iptal_mi():
        return sohbet in _IPTAL

    try:
        vids = await asyncio.to_thread(
            flow_surucu.toplu_uret, is_["video_promptlari"], "video",
            d / "videolar", bildir, iptal_mi)
        gors = await asyncio.to_thread(
            flow_surucu.toplu_uret, is_["gorsel_promptlari"], "gorsel",
            d / "gorseller", bildir, iptal_mi)
        is_["sonuclar"] = {"video": vids, "gorsel": gors}
        ok_v = [x for x in vids if x["ok"]]
        ok_g = [x for x in gors if x["ok"]]
        hatalar = [f"{x['tur']}[{x['sira']}] {x['neden']}"
                   for x in (vids + gors) if not x["ok"]]
        is_["hatalar"] = hatalar
        is_["durum"] = "bitti" if not hatalar else "bitti-eksikli"
        _kaydet(is_)

        ozet = (f"✅ *BİTTİ*\n\n"
                f"🎬 video: {len(ok_v)}/{len(vids)}\n"
                f"🖼 görsel: {len(ok_g)}/{len(gors)}\n"
                f"📁 `{is_['dizin']}`")
        if hatalar:
            ilk = "\n".join(f"• {h}" for h in hatalar[:8])
            ozet += (f"\n\n⚠ *{len(hatalar)} başarısız:*\n{ilk}"
                     + ("\n… tamamı `is.json` içinde" if len(hatalar) > 8 else ""))
        else:
            ozet += "\n\n👍 Hata yok — hepsi indi."
        await ctx.bot.send_message(sohbet, ozet, parse_mode="Markdown")
    except Exception as e:                                   # noqa: BLE001
        is_["durum"] = "hata"
        is_["hatalar"].append(f"{type(e).__name__}: {e}")
        _kaydet(is_)
        await ctx.bot.send_message(
            sohbet, f"❌ Beklenmeyen hata: {type(e).__name__}: {str(e)[:200]}")
    finally:
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
    for ad, fn in (("start", komut_start), ("yeni", komut_yeni),
                   ("video", komut_video), ("gorsel", komut_gorsel),
                   ("basla", komut_basla), ("durum", komut_durum),
                   ("iptal", komut_iptal)):
        app.add_handler(CommandHandler(ad, fn))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, metin_geldi))
    print(f"👻 Hayalet calisiyor. Klasor koku: {ayar.KOK}")
    app.run_polling()


if __name__ == "__main__":
    calistir()
