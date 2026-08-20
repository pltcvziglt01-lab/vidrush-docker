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

from . import ayar, beyin, flow_surucu

_BEKLEYEN = {}       # sohbet_id -> "hikaye" | "senkron" (girdi bekleyen kip)
_CALISAN = set()     # su an uretimde olan sohbetler (cifte /basla engeli)
_IPTAL = set()
_SON_IS = {}         # sohbet_id -> son is sozlugu (/durum icin)


_ETIKET = re.compile(
    r"^(video|g[oö]rsel|image)\s*(prompt\w*)?\s*\d*\s*[-–:.]\s*(.+)$",
    re.IGNORECASE)


def _blok_coz(metin: str) -> tuple:
    """TEK BLOK -> (video_promptlari, gorsel_promptlari).

    BICIM (kullanici karari, 20 Agu 2026):
        VIDEO PROMPT 1 - safakta limandan cikan tekne
        VIDEO PROMPT 2 - dalgalar guverteyi dovuyor
        GÖRSEL PROMPT 1 - yasli balikcinin portresi

    · Etiket buyuk/kucuk harf, numara ve ayirac (- – : .) toleransli.
    · Etiketsiz satir, ONCEKI promptun devami sayilir (cok satirli prompt);
      hic etiket gorulmemisse GORSEL kabul edilir.
    """
    videolar, gorseller = [], []
    son_liste = None
    for satir in (metin or "").splitlines():
        t = satir.strip()
        if not t:
            continue
        m = _ETIKET.match(t)
        if m:
            hedef = videolar if m.group(1).lower() == "video" else gorseller
            hedef.append(m.group(3).strip())
            son_liste = hedef
        elif son_liste:
            son_liste[-1] += " " + t          # onceki promptun devami
        else:
            gorseller.append(t)
            son_liste = gorseller
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
        "👻 *Hayalet* hazır — iki mod:\n\n"
        "🎬 `/hikaye` — hazır promptlarını TEK BLOK gönderirsin\n"
        "   (`VIDEO PROMPT 1 - ...` / `GÖRSEL PROMPT 1 - ...`)\n\n"
        "🧠 `/senkron` — METNİ gönderirsin; her cümle için promptu ben\n"
        "   üretirim, Flow'da oluşturur, çıktıyı CÜMLESİYLE buraya atarım\n\n"
        "`/durum` · `/iptal`", parse_mode="Markdown")


async def komut_hikaye(update: Update, _ctx):
    if not _izinli(update):
        return
    sohbet = update.effective_chat.id
    if sohbet in _CALISAN:
        await update.message.reply_text("⏳ Üretim sürüyor. `/iptal` ile durdur.")
        return
    _BEKLEYEN[sohbet] = "hikaye"
    await update.message.reply_text(
        "📜 Promptları TEK BLOK gönder:\n\n"
        "```\nVIDEO PROMPT 1 - şafakta limandan çıkan tekne\n"
        "GÖRSEL PROMPT 1 - yaşlı balıkçının portresi\n```",
        parse_mode="Markdown")


async def komut_senkron(update: Update, _ctx):
    if not _izinli(update):
        return
    sohbet = update.effective_chat.id
    if sohbet in _CALISAN:
        await update.message.reply_text("⏳ Üretim sürüyor. `/iptal` ile durdur.")
        return
    _BEKLEYEN[sohbet] = "senkron"
    await update.message.reply_text(
        "🧠 *Senkron mod* — anlatım METNİNİ gönder (düz metin).\n"
        "Her cümle için prompt üretip Flow'da oluşturacağım; her çıktıyı "
        "dayandığı cümleyle birlikte buraya atacağım.\n"
        f"İlk ~%20 cümle VİDEO, kalanı GÖRSEL olur.", parse_mode="Markdown")


# Eski akisla uyum: /basla artik kip secim mesaji verir.
async def komut_basla(update: Update, _ctx):
    await update.message.reply_text(
        "İki mod var: 🎬 `/hikaye` (hazır promptlar) · 🧠 `/senkron` (metin ver)",
        parse_mode="Markdown")


async def komut_iptal(update: Update, _ctx):
    sohbet = update.effective_chat.id
    _BEKLEYEN.pop(sohbet, None)
    if sohbet in _CALISAN:
        _IPTAL.add(sohbet)
        await update.message.reply_text("🛑 İptal istendi — sıradaki prompttan sonra durur.")
    else:
        await update.message.reply_text("🛑 Bekleyen iş yok, istek iptal edildi.")


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
    kip = _BEKLEYEN.get(sohbet)
    if kip is None:
        await update.message.reply_text(
            "Mod seç: 🎬 `/hikaye` · 🧠 `/senkron`", parse_mode="Markdown")
        return
    _BEKLEYEN.pop(sohbet, None)

    if kip == "senkron":
        # METIN -> cumle basina plan (beyin) -> uretim
        await update.message.reply_text("🧠 Metni analiz ediyorum…")
        plan = await asyncio.to_thread(
            beyin.plan_kur, update.message.text,
            lambda m: None)
        if not plan:
            await update.message.reply_text("Metin boş görünüyor — `/senkron` ile tekrar.")
            return
        videolar = [p["prompt"] for p in plan if p["tur"] == "video"]
        gorseller = [p["prompt"] for p in plan if p["tur"] == "gorsel"]
        # prompt -> cumle eslesme haritasi (senkron teslim icin)
        cumle_map = {p["prompt"]: p["cumle"] for p in plan}
        await update.message.reply_text(
            f"📋 Plan: {len(plan)} cümle → 🎬 {len(videolar)} video + "
            f"🖼 {len(gorseller)} görsel. Başlıyorum.")
    else:
        videolar, gorseller = _blok_coz(update.message.text)
        cumle_map = {}
        if not (videolar or gorseller):
            await update.message.reply_text("Blok boş görünüyor — `/hikaye` ile tekrar.")
            return

    ad = f"is_{time.strftime('%Y%m%d_%H%M%S')}"
    d = ayar.is_dizini(ad)
    is_ = {"ad": ad, "dizin": str(d), "kip": kip,
           "video_promptlari": videolar, "gorsel_promptlari": gorseller,
           "cumleler": cumle_map, "durum": "uretim",
           "sonuclar": {}, "hatalar": []}
    _SON_IS[sohbet] = is_
    _kaydet(is_)
    _CALISAN.add(sohbet)
    _IPTAL.discard(sohbet)
    if kip != "senkron":
        await update.message.reply_text(
            f"🚀 Başlıyorum — 🎬 {len(videolar)} video + 🖼 {len(gorseller)} görsel.\n"
            f"📁 `{d}`", parse_mode="Markdown")

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

    dongu = asyncio.get_running_loop()

    def indi_cb(kayit):
        """SENKRON teslim: cikti Telegram'a DAYANDIGI CUMLEYLE gider."""
        if kip != "senkron":
            return
        cumle = cumle_map.get(kayit.get("prompt", ""), "")
        yol = kayit.get("dosya", "")

        async def _gonder():
            try:
                with open(yol, "rb") as f:
                    if kayit.get("tur") == "video":
                        await ctx.bot.send_video(sohbet, f, caption=cumle[:1000])
                    else:
                        await ctx.bot.send_photo(sohbet, f, caption=cumle[:1000])
            except Exception as e:                           # noqa: BLE001
                try:
                    await ctx.bot.send_message(
                        sohbet, f"⚠ dosya gönderilemedi ({type(e).__name__}) "
                                f"— diskte: {yol}")
                except Exception:
                    pass
        asyncio.run_coroutine_threadsafe(_gonder(), dongu)

    try:
        # PARTI MODU: promptlar 10'ar verilir, ciktilar belirdikce indirilir.
        vids = await asyncio.to_thread(
            flow_surucu.parti_uret, videolar, "video", d / "video",
            bildir, iptal_mi, indi_cb)
        gors = await asyncio.to_thread(
            flow_surucu.parti_uret, gorseller, "gorsel", d / "gorsel",
            bildir, iptal_mi, indi_cb)
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
                   ("hikaye", komut_hikaye), ("senkron", komut_senkron),
                   ("durum", komut_durum), ("iptal", komut_iptal)):
        app.add_handler(CommandHandler(ad, fn))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, metin_geldi))
    print(f"👻 Hayalet calisiyor. Klasor koku: {ayar.KOK}")
    app.run_polling()


if __name__ == "__main__":
    calistir()
