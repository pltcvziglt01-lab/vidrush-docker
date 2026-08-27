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
import logging
import signal
import warnings
import re
import time
from pathlib import Path

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (Application, CommandHandler, MessageHandler, filters)

from . import ayar, beyin, flow_surucu, kurgu

# ⚠ SENKRON AKISI (21 Agu 2026 — kullanici karari): /senkron ARTIK IKI GIRDI
# ister ve isi SONUNA kadar goturur:
#     /senkron -> METIN -> SESLENDIRME -> Flow uretimi -> ses hizalama
#              -> CapCut taslagi (her cumle ayri klip) -> BITTI
# Kullanici CapCut'i acip gecis/yazi/efekt ekler; kesme islerini yapmaz.
# Telegram Bot API getFile tavani. Asilirsa indirme HATA verir — o yuzden
# denemeden once boyuta bakariz (bkz. ses_geldi).
TELEGRAM_INDIRME_TAVAN = 20 * 1024 * 1024

_BEKLEYEN = {}       # sohbet_id -> "hikaye" | "senkron_metin" | "senkron_ses"
_TASLAK = {}         # sohbet_id -> {"metin": ...} (adimlar arasi tasima)
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
        "🧠 `/senkron` — KARAKTER + METİN + PROMPTLAR + SESLENDİRME\n"
        "   verirsin; üretir, sesle hizalar ve *CapCut projesi* olarak\n"
        "   zaman çizgisine dizer. Sen sadece geçiş/yazı eklersin.\n\n"
        "`/durum` · `/cumleler` · `/tamam` · `/hazir` · `/sifirla` · `/iptal`",
        parse_mode="Markdown")


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
    _TASLAK.pop(sohbet, None)
    await _karakter_sor(update, sohbet)


def _klavye(secenekler: list) -> ReplyKeyboardMarkup:
    """Tek sutunlu secim klavyesi — yazim hatasi olmasin diye dokunmalik."""
    return ReplyKeyboardMarkup([[x] for x in secenekler],
                               one_time_keyboard=True, resize_keyboard=True)



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
    satir = (f"📋 *{is_['ad']}* ({is_.get('kip', '?')}) — {is_['durum']}\n"
             f"🎬 video: {len(is_['video_promptlari'])} · "
             f"🖼 görsel: {len(is_['gorsel_promptlari'])} · "
             f"⚠ hata: {len(is_['hatalar'])}\n")
    k = is_.get("kurgu")
    if k:
        satir += (f"🎞 CapCut: `{Path(k.get('capcut', '')).name}` · "
                  f"{k.get('toplam_sn', 0):.0f} sn\n")
    await update.message.reply_text(satir + f"📁 `{is_['dizin']}`",
                                    parse_mode="Markdown")


async def ses_geldi(update: Update, ctx):
    """SENKRON 2. ADIM: seslendirme. BIRDEN COK PARCA kabul eder.

    ⚠ NEDEN PARCALI: Telegram Bot API `getFile` 20MB ile sinirlidir ve bu
    sinir botun dosyayi INDIRMESINDEDIR — dosya Telegram sunucusunda durur,
    bot ona hic erisemez, dolayisiyla KENDISI BOLEMEZ. Bolme kacinilmaz
    olarak GONDEREN tarafta olur. Bu yuzden bot birden cok parca alip
    kendisi BIRLESTIRIR: 30 dk'lik anlatimi ikiye bolup gonderirsin.
    """
    if not _izinli(update):
        return
    sohbet = update.effective_chat.id
    if _BEKLEYEN.get(sohbet) != "senkron_ses":
        await update.message.reply_text(
            "Ses aldım ama sıra onda değil. `/senkron` ile başla.",
            parse_mode="Markdown")
        return
    m = update.message
    nesne = m.voice or m.audio or m.document
    if nesne is None:
        return

    boyut = getattr(nesne, "file_size", 0) or 0
    if boyut > TELEGRAM_INDIRME_TAVAN:
        await m.reply_text(
            f"❌ Bu parça *{boyut / 1048576:.1f} MB* — Telegram botları en "
            f"fazla {TELEGRAM_INDIRME_TAVAN // 1048576} MB indirebiliyor ve "
            "dosya sunucuda durduğu için ben bölemiyorum.\n\n"
            "*İki çözümden biri:*\n"
            "1️⃣ Sıkıştır (30 dk → ~14 MB):\n"
            "```\nffmpeg -i ses.mp3 -ac 1 -b:a 64k kucuk.mp3\n```\n"
            "2️⃣ Parçalara böl, sırayla gönder — ben birleştiririm:\n"
            "```\nffmpeg -i ses.mp3 -f segment -segment_time 900 \\\n"
            "  -c copy parca_%02d.mp3\n```\n"
            "_Sesli mesaj olarak gönderirsen zaten ~7 MB olur, hiç uğraşma._",
            parse_mode="Markdown")
        return

    taslak = _TASLAK.setdefault(sohbet, {})
    if "dizin" not in taslak:
        taslak["ad"] = f"is_{time.strftime('%Y%m%d_%H%M%S')}"
        taslak["dizin"] = str(ayar.is_dizini(taslak["ad"]))
        taslak["parcalar"] = []
    d = Path(taslak["dizin"])
    no = len(taslak["parcalar"]) + 1
    await m.reply_text(f"🎧 {no}. parça indiriliyor… "
                       f"({boyut / 1048576:.1f} MB)")
    try:
        dosya = await ctx.bot.get_file(nesne.file_id)
    except Exception as e:                                   # noqa: BLE001
        await m.reply_text(
            f"❌ Parça indirilemedi ({type(e).__name__}). Sıkıştırıp tekrar "
            "dene:\n```\nffmpeg -i ses.mp3 -ac 1 -b:a 64k kucuk.mp3\n```",
            parse_mode="Markdown")
        return
    uzanti = Path(getattr(nesne, "file_name", "") or "ses.ogg").suffix or ".ogg"
    yol = d / f"ses_parca_{no:02d}{uzanti}"
    await dosya.download_to_drive(str(yol))
    taslak["parcalar"].append(str(yol))

    try:
        toplam = sum(kurgu.sure(Path(x)) for x in taslak["parcalar"])
        sure_yazi = f" · toplam {toplam / 60:.1f} dk"
    except Exception:                                        # noqa: BLE001
        sure_yazi = ""
    await m.reply_text(
        f"✅ {no}. parça alındı{sure_yazi}\n\n"
        "Devamı varsa **sırayla** göndermeye devam et.\n"
        "Ses bittiyse ▶️ `/hazir` yaz, üretime başlayayım.",
        parse_mode="Markdown")


async def _karakter_sor(update: Update, sohbet: int):
    _BEKLEYEN[sohbet] = "senkron_karakter"
    await update.message.reply_text(
        "🧠 *Senkron mod* — sonuç CapCut projesi olur.\n"
        "_Görsel promptları sen yazacaksın; stil sormuyorum._\n\n"
        "*1️⃣ Ana karakter var mı?*\n"
        "Varsa `Ad: betimleme` şeklinde ver — promptunda o adı yazdığın "
        "yere tam betimlemesini koyarım:\n"
        "`Elif: 8 yaşında, kızıl örgülü saçlı, yeşil parkalı bir kız`\n\n"
        "_Adsız da verebilirsin; o zaman promptta_ `@karakter` _yazdığın "
        "yere koyarım._\n\n"
        "Karakter yoksa `yok` yaz.",
        reply_markup=_klavye(["🚫 Karakter yok"]), parse_mode="Markdown")


# ⚠ TELEGRAM 4096 KARAKTER SINIRI: 80+ promptluk bir liste ya da 30 dk'lik
# bir anlatim metni TEK mesaja SIGMAZ. Iki cikis yolu da desteklenir:
#   1) parca parca gonder — biriktirilir
#   2) .txt dosyasi olarak gonder — tek seferde alinir
# Prompt adiminda hedef sayi BELLI oldugu icin (cumle sayisi) sayi tutunca
# kendiliginden ilerler; metin adiminda hedef bilinmedigi icin /tamam gerekir.

async def _metin_parcasi(update: Update, sohbet: int, parca: str):
    """Anlatim metninin bir parcasi geldi — biriktir, ozet ver."""
    parca = (parca or "").strip()
    if not parca:
        return
    taslak = _TASLAK.setdefault(sohbet, {})
    yigin = taslak.setdefault("metin_parcalari", [])
    yigin.append(parca)
    tam = "\n".join(yigin)
    taslak["metin"] = tam
    n = len(beyin.cumlelere_bol(tam))
    await update.message.reply_text(
        f"📝 {len(yigin)}. parça alındı — toplam *{n} cümle* "
        f"({len(tam)} karakter)\n\n"
        "Devamı varsa göndermeye devam et.\n"
        "Metin bittiyse ▶️ `/tamam` yaz.", parse_mode="Markdown")


async def komut_tamam(update: Update, _ctx):
    """Metin bitti -> varsayilan tur sorusuna gec."""
    if not _izinli(update):
        return
    sohbet = update.effective_chat.id
    if _BEKLEYEN.get(sohbet) != "senkron_metin":
        await update.message.reply_text(
            "Şu an metin beklemiyorum. `/senkron` ile başla.",
            parse_mode="Markdown")
        return
    cumleler = beyin.cumlelere_bol((_TASLAK.get(sohbet) or {}).get("metin", ""))
    if not cumleler:
        await update.message.reply_text("Henüz metin gelmedi.")
        return
    _BEKLEYEN[sohbet] = "senkron_mod"
    await update.message.reply_text(
        f"✅ Metin tamam: *{len(cumleler)} cümle*\n"
        f"→ {len(cumleler)} prompt yazacaksın (`/cumleler` ile listeyi "
        "görebilirsin).\n\n*3️⃣ Varsayılan tür ne olsun?*",
        reply_markup=_klavye(list(beyin.MODLAR.values())),
        parse_mode="Markdown")


async def _prompt_parcasi(update: Update, sohbet: int, parca: str):
    """Prompt listesinin bir parcasi geldi — biriktir; sayi tutunca ilerle."""
    taslak = _TASLAK.setdefault(sohbet, {})
    cumleler = beyin.cumlelere_bol(taslak.get("metin", ""))
    hedef = len(cumleler)
    yigin = taslak.setdefault("promptlar", [])
    yeni = beyin.promptlari_ayristir(parca)
    if not yeni:
        return
    yigin.extend(yeni)

    if len(yigin) < hedef:
        kalan = hedef - len(yigin)
        await update.message.reply_text(
            f"📥 *{len(yigin)}/{hedef}* prompt alındı — {kalan} tane daha "
            "bekliyorum.\n_Kaldığın yerden devam et._\n\n"
            "Yanlış gittiyse `/sifirla` ile promptları temizle.",
            parse_mode="Markdown")
        return

    if len(yigin) > hedef:
        # ⚠ FAZLA PROMPT = KAYMA: hangisinin fazla oldugunu bilemeyiz, o
        # yuzden kesip devam ETMEYIZ. Kullanici temizleyip yeniden yollar.
        taslak["promptlar"] = []
        await update.message.reply_text(
            f"⚠ *{hedef} cümle* var ama *{len(yigin)} prompt* geldi.\n"
            "Fazlanın hangisi olduğunu bilemem; kesersem sonraki tüm "
            "cümleler yanlış görüntüye bağlanır.\n\n"
            "Promptları temizledim — `/cumleler` ile listeye bakıp "
            f"tam {hedef} satır olarak tekrar gönder.", parse_mode="Markdown")
        return

    _BEKLEYEN[sohbet] = "senkron_ses"
    v = sum(1 for e, _ in yigin if e == "video")
    g = sum(1 for e, _ in yigin if e == "gorsel")
    ezme = f" ({v} video + {g} görsel satır bazında ezildi)" if v or g else ""
    await update.message.reply_text(
        f"✅ {hedef} prompt tamam{ezme}\n\n"
        "*5️⃣ Şimdi SESLENDİRMEYİ gönder* (ses dosyası ya da sesli mesaj).\n"
        "_Metnin tamamının okunmuş hali olmalı._\n\n"
        "Uzunsa parçalara bölüp **sırayla** gönderebilirsin. "
        "Bitince `/hazir` yaz.", parse_mode="Markdown")


async def komut_sifirla(update: Update, _ctx):
    """Biriken promptlari (ya da metni) temizler — bastan yollamak icin."""
    if not _izinli(update):
        return
    sohbet = update.effective_chat.id
    kip = _BEKLEYEN.get(sohbet)
    taslak = _TASLAK.get(sohbet) or {}
    if kip == "senkron_promptlar":
        taslak["promptlar"] = []
        n = len(beyin.cumlelere_bol(taslak.get("metin", "")))
        await update.message.reply_text(
            f"🧹 Promptlar temizlendi. {n} satır olarak tekrar gönder.")
    elif kip == "senkron_metin":
        taslak["metin_parcalari"] = []
        taslak["metin"] = ""
        await update.message.reply_text("🧹 Metin temizlendi. Tekrar gönder.")
    else:
        await update.message.reply_text("Temizlenecek bir şey yok.")


async def belge_geldi(update: Update, ctx):
    """.txt dosyasi: metin ya da prompt listesi olarak alinir.

    ⚠ 80+ prompt icin EN PRATIK YOL budur — mesaj sinirina hic takilmaz.
    """
    if not _izinli(update):
        return
    sohbet = update.effective_chat.id
    kip = _BEKLEYEN.get(sohbet)
    if kip not in ("senkron_metin", "senkron_promptlar"):
        await update.message.reply_text(
            "Dosya aldım ama sırası değil. `/senkron` ile başla.",
            parse_mode="Markdown")
        return
    belge = update.message.document
    if belge is None:
        return
    if (belge.file_size or 0) > 2 * 1024 * 1024:
        await update.message.reply_text("❌ Dosya çok büyük (en fazla 2 MB).")
        return
    try:
        dosya = await ctx.bot.get_file(belge.file_id)
        ham = bytes(await dosya.download_as_bytearray())
    except Exception as e:                                   # noqa: BLE001
        await update.message.reply_text(f"❌ Dosya alınamadı ({type(e).__name__}).")
        return
    for kodlama in ("utf-8", "utf-8-sig", "cp1254", "latin-1"):
        try:
            icerik = ham.decode(kodlama)
            break
        except UnicodeDecodeError:
            continue
    else:
        await update.message.reply_text(
            "❌ Dosya okunamadı — düz metin (.txt), UTF-8 olmalı.")
        return
    await update.message.reply_text(f"📄 `{belge.file_name}` okundu.",
                                    parse_mode="Markdown")
    if kip == "senkron_metin":
        await _metin_parcasi(update, sohbet, icerik)
    else:
        await _prompt_parcasi(update, sohbet, icerik)


async def komut_cumleler(update: Update, _ctx):
    """Metnin nasil cumlelere bolundugunu GOSTERIR — prompt sayisi tutsun."""
    taslak = _TASLAK.get(update.effective_chat.id) or {}
    cumleler = beyin.cumlelere_bol(taslak.get("metin", ""))
    if not cumleler:
        await update.message.reply_text("Önce `/senkron` → metin gönder.",
                                        parse_mode="Markdown")
        return
    satir = [f"{i}. {c}" for i, c in enumerate(cumleler, 1)]
    # Telegram mesaj siniri 4096 — uzun metinlerde parcala.
    yigin, boy = [], 0
    for x in satir:
        if boy + len(x) > 3500:
            await update.message.reply_text("\n".join(yigin))
            yigin, boy = [], 0
        yigin.append(x); boy += len(x) + 1
    if yigin:
        await update.message.reply_text(
            "\n".join(yigin) + f"\n\n→ *{len(cumleler)} prompt* yaz.",
            parse_mode="Markdown")


async def komut_hazir(update: Update, ctx):
    """Ses parcalari tamam -> birlestir -> tam akisi baslat."""
    if not _izinli(update):
        return
    sohbet = update.effective_chat.id
    taslak = _TASLAK.get(sohbet) or {}
    parcalar = taslak.get("parcalar") or []
    if _BEKLEYEN.get(sohbet) != "senkron_ses" or not parcalar:
        await update.message.reply_text(
            "Önce `/senkron` → metin → ses gönder.", parse_mode="Markdown")
        return
    _BEKLEYEN.pop(sohbet, None)
    _TASLAK.pop(sohbet, None)
    d = Path(taslak["dizin"])
    try:
        if len(parcalar) > 1:
            await update.message.reply_text(
                f"🔗 {len(parcalar)} parça birleştiriliyor…")
        ses_yolu = await asyncio.to_thread(
            kurgu.sesleri_birlestir, [Path(x) for x in parcalar],
            d / "seslendirme.m4a")
    except kurgu.KurguHatasi as e:
        _BEKLEYEN[sohbet] = "senkron_ses"
        _TASLAK[sohbet] = taslak
        await update.message.reply_text(f"❌ Ses birleştirilemedi: {e}")
        return
    await _senkron_yurut(update, ctx, taslak["ad"], d,
                         taslak.get("metin", ""), ses_yolu, taslak)


async def metin_geldi(update: Update, ctx):
    if not _izinli(update):
        return
    sohbet = update.effective_chat.id
    kip = _BEKLEYEN.get(sohbet)
    if kip is None:
        await update.message.reply_text(
            "Mod seç: 🎬 `/hikaye` · 🧠 `/senkron`", parse_mode="Markdown")
        return

    if kip == "senkron_karakter":
        cevap = (update.message.text or "").strip()
        atla = cevap.lower() in ("yok", "/gec", "gec", "geç", "🚫 karakter yok")
        _BEKLEYEN[sohbet] = "senkron_metin"
        if atla:
            bilgi = "✅ Karakter yok.\n\n"
        else:
            # ⚠ NE ENJEKTE EDILECEGINI KULLANICI GORMELI (22 Agu 2026):
            # karakter alanina tam bir prompt yapistirilirsa ("referans
            # sayfasi, uc gorunus, sahne yok...") o metin sahne promptuna
            # girip sahneyi ZEHIRLER ve referans sayfasi uretilir. Artik
            # sadelestirip GOSTERIYORUZ; yanlissa kullanici hemen gorur.
            kisa = beyin.karakter_sadelestir(cevap)
            _TASLAK.setdefault(sohbet, {})["karakter_ham"] = cevap
            cevap = kisa                       # enjekte edilecek olan BU
            ad, _b = beyin.karakter_ayristir(kisa)
            bilgi = ("✅ Karakter kaydedildi"
                     + (f" — promptunda *{ad}* yazdığın yere koyacağım.\n"
                        if ad else
                        " — promptunda `@karakter` yazdığın yere koyacağım.\n")
                     + f"\n_Promptlara şu eklenecek:_\n`{kisa[:350]}`\n\n"
                     + ("_Uzun metnini görünüş tarifine indirgedim; sahne "
                        "promptunu bozmasın diye._\n\n"
                        if len(_TASLAK[sohbet]["karakter_ham"]) > len(kisa) + 20
                        else ""))
        # ⚠ KAYIT SADELESTIRMEDEN SONRA: once kaydedilirse HAM metin saklanir
        # ve kullaniciya gosterilenle enjekte edilen FARKLI olur.
        _TASLAK.setdefault(sohbet, {})["karakter"] = "" if atla else cevap
        await update.message.reply_text(
            bilgi + "*2️⃣ Şimdi anlatım METNİNİ gönder* (düz metin, her dilde)."
            "\n\nUzunsa iki yol var:\n"
            "· **parça parça** gönder — biriktiririm\n"
            "· ya da **.txt dosyası** olarak at — tek seferde alırım\n\n"
            "Metin bitince ▶️ `/tamam` yaz.",
            reply_markup=ReplyKeyboardRemove(), parse_mode="Markdown")
        return

    if kip == "senkron_mod":
        t = (update.message.text or "").strip()
        mod = next((k for k, v in beyin.MODLAR.items() if v == t), None)
        if mod is None:
            await update.message.reply_text(
                "Listeden birini seç.",
                reply_markup=_klavye(list(beyin.MODLAR.values())))
            return
        _TASLAK[sohbet]["mod"] = mod
        _BEKLEYEN[sohbet] = "senkron_promptlar"
        n = len(beyin.cumlelere_bol(_TASLAK[sohbet]["metin"]))
        await update.message.reply_text(
            f"*4️⃣ Şimdi {n} PROMPTU gönder* — her satır bir cümle, "
            "sırayla.\n\n"
            "```\n1. Karlı sokak, wide shot, 2D çizgi film\n"
            "2. Elif kapıyı açıyor, medium shot\n"
            "3. video: Kar taneleri düşüyor, yavaş dolly-in\n```\n"
            f"· Varsayılan tür: *{beyin.MODLAR[mod]}*\n"
            "· Bir satırı `video:` ya da `görsel:` ile başlatırsan o satır "
            "için varsayılanı ezersin\n"
            "· Satır başı numarası isteğe bağlı\n\n"
            f"⚠ *{n} satır tek mesaja sığmaz* (Telegram sınırı 4096 karakter). "
            "**Parça parça** gönder — kaçta kaç olduğunu sayarım, tamamlanınca "
            "kendiliğinden devam ederim. Ya da hepsini bir **.txt dosyası** "
            "olarak at.\n"
            "_Karıştırırsan_ `/sifirla` _ile promptları temizle._",
            reply_markup=ReplyKeyboardRemove(), parse_mode="Markdown")
        return

    if kip == "senkron_promptlar":
        return await _prompt_parcasi(update, sohbet, update.message.text)

    if kip == "senkron_metin":
        # ⚠ TELEGRAM MESAJ SINIRI 4096 KARAKTER: uzun anlatim TEK mesaja
        # sigmaz, kullanici bolerek gonderir. Eskiden her parca oncekini
        # EZIYORDU — sessizce metnin yalnizca son parcasi kaliyordu.
        # Artik biriktirilir; kullanici /tamam deyince kapanir.
        return await _metin_parcasi(update, sohbet, update.message.text)

    if kip == "senkron_ses":
        await update.message.reply_text(
            "🎧 Sırada SESLENDİRME var — metin değil. Ses dosyası gönder "
            "ya da `/iptal`.", parse_mode="Markdown")
        return

    # ── HIKAYE: hazir prompt blogu ──
    _BEKLEYEN.pop(sohbet, None)
    videolar, gorseller = _blok_coz(update.message.text)
    if not (videolar or gorseller):
        await update.message.reply_text("Blok boş görünüyor — `/hikaye` ile tekrar.")
        return

    ad = f"is_{time.strftime('%Y%m%d_%H%M%S')}"
    d = ayar.is_dizini(ad)
    is_ = {"ad": ad, "dizin": str(d), "kip": "hikaye",
           "video_promptlari": videolar, "gorsel_promptlari": gorseller,
           "cumleler": {}, "durum": "uretim", "sonuclar": {}, "hatalar": []}
    _SON_IS[sohbet] = is_
    _kaydet(is_)
    _CALISAN.add(sohbet)
    _IPTAL.discard(sohbet)
    await update.message.reply_text(
        f"🚀 Başlıyorum — 🎬 {len(videolar)} video + 🖼 {len(gorseller)} görsel.\n"
        f"📁 `{d}`", parse_mode="Markdown")

    async with _akitici(ctx, sohbet) as bildir:
        def iptal_mi():
            return sohbet in _IPTAL
        try:
            vids = await asyncio.to_thread(
                flow_surucu.parti_uret, videolar, "video", d / "video",
                bildir, iptal_mi, None)
            gors = await asyncio.to_thread(
                flow_surucu.parti_uret, gorseller, "gorsel", d / "gorsel",
                bildir, iptal_mi, None)
            is_["sonuclar"] = {"video": vids, "gorsel": gors}
            is_["hatalar"] = [f"{x['tur']}[{x['sira']}] {x['neden']}"
                              for x in (vids + gors) if not x["ok"]]
            is_["durum"] = "bitti" if not is_["hatalar"] else "bitti-eksikli"
            _kaydet(is_)
            baslik, detay = _ozet(is_, vids, gors, d)
            await ctx.bot.send_message(sohbet, baslik, parse_mode="Markdown")
            if detay:
                await ctx.bot.send_message(sohbet, detay[:3500])
        except Exception as e:                               # noqa: BLE001
            is_["durum"] = "hata"
            is_["hatalar"].append(f"{type(e).__name__}: {e}")
            _kaydet(is_)
            await ctx.bot.send_message(
                sohbet, f"❌ Beklenmeyen hata: {type(e).__name__}: {str(e)[:200]}")
        finally:
            _CALISAN.discard(sohbet)
            _IPTAL.discard(sohbet)


def _ozet(is_: dict, vids: list, gors: list, d: Path) -> tuple:
    """(baslik_markdown, detay_duz_metin) doner.

    ⚠ HATA METNI MARKDOWN OLARAK GONDERILEMEZ: icinde `gorsel[4]`,
    `chrome_baslat.sh`, dosya yollari gecer; Telegram `[...]`'i link,
    `_`'yi italik sanar ve mesaj okunamaz hale gelir (21 Agu 2026'da
    kullanicinin ekraninda goruldu). Detay AYRI ve DUZ gonderilir.
    """
    ok_v = sum(1 for x in vids if x["ok"])
    ok_g = sum(1 for x in gors if x["ok"])
    hatalar = is_.get("hatalar") or []
    baslik = (f"✅ *ÜRETİM BİTTİ*\n🎬 {ok_v}/{len(vids)} video · "
              f"🖼 {ok_g}/{len(gors)} görsel\n📁 `{d}`")
    if not hatalar:
        return baslik + "\n👍 Hata yok.", ""
    baslik += f"\n\n⚠ *{len(hatalar)} başarısız* — ayrıntı aşağıda."
    # Ayni nedenden dusen onlarca satiri tek tek yazmak ekrani doldurur;
    # nedene gore GRUPLA.
    gruplar = {}
    for h in hatalar:
        _, _, neden = h.partition("] ")
        gruplar.setdefault(neden.strip() or h, []).append(h.split("]")[0] + "]")
    satir = []
    for neden, ogeler in list(gruplar.items())[:5]:
        satir.append(f"• {len(ogeler)} adet — {neden[:300]}")
        satir.append(f"   ({', '.join(ogeler[:10])}"
                     f"{'…' if len(ogeler) > 10 else ''})")
    if len(gruplar) > 5:
        satir.append(f"… {len(gruplar) - 5} farklı hata daha (is.json içinde)")
    return baslik, "\n".join(satir)


class _akitici:
    """Arka plan is parcaciklarindan gelen ilerlemeyi Telegram'a akitir.

    ⚠ NEDEN AYRI: uretim `asyncio.to_thread` icinde doner; oradan dogrudan
    `await` edilemez. Kuyruk + tuketici gorev ile mesajlar sirayla cikar.
    """

    def __init__(self, ctx, sohbet):
        self.ctx, self.sohbet = ctx, sohbet
        self.kuyruk: asyncio.Queue = asyncio.Queue()

    async def __aenter__(self):
        async def tuket():
            while True:
                m = await self.kuyruk.get()
                if m is None:
                    break
                try:
                    await self.ctx.bot.send_message(self.sohbet, m[:400])
                except Exception:
                    pass
        self.gorev = asyncio.create_task(tuket())

        def bildir(m):
            try:
                self.kuyruk.put_nowait(m)
            except Exception:
                pass
        return bildir

    async def __aexit__(self, *_):
        await self.kuyruk.put(None)
        await self.gorev
        return False


async def _senkron_yurut(update: Update, ctx, ad: str, d: Path, metin: str,
                         ses_yolu: Path, secim: dict = None):
    """SENKRON TAM AKIS: plan -> Flow uretimi -> ses hizalama -> CapCut.

    ⚠ SONUC BIR CAPCUT PROJESIDIR, duz mp4 degil: kullanici gecis/yazi/efekt
    eklemek istiyor (kullanici karari, 21 Agu 2026). Yine de kontrol icin
    duz `final.mp4` de yazilir.
    """
    sohbet = update.effective_chat.id
    if not metin:
        await ctx.bot.send_message(sohbet, "Metin kayboldu — `/senkron` ile tekrar.")
        return
    _CALISAN.add(sohbet)
    _IPTAL.discard(sohbet)

    async with _akitici(ctx, sohbet) as bildir:
        def iptal_mi():
            return sohbet in _IPTAL
        is_ = {"ad": ad, "dizin": str(d), "kip": "senkron",
               "ses": str(ses_yolu), "video_promptlari": [],
               "gorsel_promptlari": [], "cumleler": {}, "durum": "plan",
               "sonuclar": {}, "hatalar": []}
        _SON_IS[sohbet] = is_
        try:
            secim = secim or {}
            karakter = secim.get("karakter", "")
            mod = secim.get("mod", "karisik")
            is_.update({"karakter": karakter, "mod": mod})
            # ⚠ LLM YOK: promptlari kullanici yazdi. Burada yalnizca karakter
            # betimlemesi yerlestirilir ve tur (video/gorsel) belirlenir.
            plan = beyin.plan_elle(beyin.cumlelere_bol(metin),
                                   secim.get("promptlar") or [],
                                   karakter, mod)
            if not plan:
                await ctx.bot.send_message(sohbet, "Metin boş — `/senkron` tekrar.")
                return
            videolar = [(p["sira"], p["prompt"]) for p in plan if p["tur"] == "video"]
            gorseller = [(p["sira"], p["prompt"]) for p in plan if p["tur"] == "gorsel"]
            is_.update({"video_promptlari": [p for _, p in videolar],
                        "gorsel_promptlari": [p for _, p in gorseller],
                        "cumleler": {str(p["sira"]): p["cumle"] for p in plan},
                        "durum": "uretim"})
            _kaydet(is_)
            await ctx.bot.send_message(
                sohbet, f"📋 {beyin.plan_ozeti(plan)}"
                        f"{' · 🧍 karakter yerleştirildi' if karakter else ''}"
                        f"\n📁 `{d}`\nÜretime başlıyorum — bu uzun sürebilir.",
                parse_mode="Markdown")

            # ⚠ URETIM COKSE BILE IS COPE GITMEZ (22 Agu 2026): 179 promptluk
            # is 168. adimda Flow arayuzu kaybolunca TimeoutError ile oldu ve
            # CapCut adimina HIC gelemedi. Artik hata yakalanir, o ana kadar
            # inen ne varsa onunla kurguya devam edilir.
            vids, gors = [], []
            try:
                vids = await asyncio.to_thread(
                    flow_surucu.uret_tekrarli, [p for _, p in videolar], "video",
                    d / "video", bildir, iptal_mi, None, [s for s, _ in videolar])
                gors = await asyncio.to_thread(
                    flow_surucu.uret_tekrarli, [p for _, p in gorseller], "gorsel",
                    d / "gorsel", bildir, iptal_mi, None,
                    [s for s, _ in gorseller])
            except Exception as e:                           # noqa: BLE001
                is_["hatalar"].append(f"uretim yarida kesildi: "
                                      f"{type(e).__name__}: {str(e)[:200]}")
                _kaydet(is_)
                await ctx.bot.send_message(
                    sohbet, f"⚠ Üretim yarıda kesildi ({type(e).__name__}).\n"
                            "İnen dosyalarla kurguya devam ediyorum — "
                            "eksik cümlelerde önceki görüntü uzayacak.")
            is_["sonuclar"] = {"video": vids, "gorsel": gors}
            is_["hatalar"] = [f"{x['tur']}[{x['sira']}] {x['neden']}"
                              for x in (vids + gors) if not x["ok"]]
            _kaydet(is_)
            baslik, detay = _ozet(is_, vids, gors, d)
            await ctx.bot.send_message(sohbet, baslik, parse_mode="Markdown")
            if detay:
                await ctx.bot.send_message(sohbet, detay[:3500])

            # ── ESLESME: cumle no -> inen dosya (CapCut dizilimi bunu okur) ──
            # ⚠ DISKTEN OKU, sonuc listesinden DEGIL: uretim yarida kesilse
            # ya da tekrar denemede dosya adi degisse bile diskteki gercek
            # durum dogru olandir. Dosya adinin basindaki sayi = cumle no.
            eslesme = {}
            for alt in ("video", "gorsel"):
                for yol in sorted((d / alt).glob("*")):
                    m = re.match(r"0*(\d+)_", yol.name)
                    if m and yol.is_file():
                        eslesme[str(int(m.group(1)))] = str(yol)
            eksik = [p["sira"] for p in plan if str(p["sira"]) not in eslesme]
            if eksik:
                # ⚠ ARTIK DURMUYORUZ (22 Agu 2026 kullanici karari): eksik
                # cumlenin araligi ONCEKI SAHNE UZATILARAK kapatilir. Ses hic
                # kaymaz; izleyici bosluk gormez, sadece bir goruntu daha uzun
                # kalir. Durmak, 183 cumlelik isi 1 eksik yuzunden copa atardi.
                await ctx.bot.send_message(
                    sohbet,
                    f"⚠ {len(eksik)} cümlenin medyası üretilemedi "
                    f"({', '.join(str(x) for x in eksik[:12])}"
                    f"{'…' if len(eksik) > 12 else ''}).\n"
                    "Bu cümlelerde *önceki görüntü daha uzun kalacak* — "
                    "ses kaymayacak.", parse_mode="Markdown")
            Path(d, "eslesme.json").write_text(
                json.dumps(eslesme, ensure_ascii=False, indent=2),
                encoding="utf-8")
            Path(d, "metin.txt").write_text(metin, encoding="utf-8")

            # ── HIZALAMA + CAPCUT ──
            is_["durum"] = "kurgu"
            _kaydet(is_)
            await ctx.bot.send_message(
                sohbet, "🎚 Sesle hizalayıp CapCut'a diziyorum…")
            proje = f"HAYALET_{time.strftime('%m%d_%H%M')}"
            kunye = await asyncio.to_thread(
                kurgu.kurgula, metin, ses_yolu, d, d / "final.mp4",
                False, proje, bildir)
            is_["durum"] = "bitti"
            is_["kurgu"] = kunye
            _kaydet(is_)
            await ctx.bot.send_message(
                sohbet,
                f"🎬 *HAZIR — CapCut'ta aç*\n\n"
                f"Proje: *{proje}*\n"
                f"{len(plan)} klip · {kunye['toplam_sn']:.0f} sn\n"
                f"Hizalama: _{kunye['yontem']}_\n\n"
                f"CapCut'ı kapat-aç, proje listesinde görünür. Her cümle ayrı "
                f"klip; geçiş/yazı/efekt eklemen için hazır.\n"
                f"📁 Kontrol videosu: `{d}/final.mp4`", parse_mode="Markdown")
        except kurgu.KurguHatasi as e:
            is_["durum"] = "kurgu-hatasi"
            is_["hatalar"].append(str(e))
            _kaydet(is_)
            await ctx.bot.send_message(
                sohbet, f"❌ Kurgu yapılamadı:\n`{str(e)[:600]}`\n\n"
                        f"Üretilen dosyalar duruyor: `{d}`",
                parse_mode="Markdown")
        except Exception as e:                               # noqa: BLE001
            is_["durum"] = "hata"
            is_["hatalar"].append(f"{type(e).__name__}: {e}")
            _kaydet(is_)
            await ctx.bot.send_message(
                sohbet, f"❌ Beklenmeyen hata: {type(e).__name__}: {str(e)[:200]}")
        finally:
            _CALISAN.discard(sohbet)
            _IPTAL.discard(sohbet)


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
                   ("hazir", komut_hazir), ("cumleler", komut_cumleler),
                   ("tamam", komut_tamam), ("sifirla", komut_sifirla),
                   ("durum", komut_durum), ("iptal", komut_iptal)):
        app.add_handler(CommandHandler(ad, fn))
    # ⚠ SES ISLEYICISI METINDEN ONCE: sesli mesaj/ses dosyasi /senkron'un
    # 2. adimidir; TEXT filtresi bunlari zaten yakalamaz ama sirayi acik tut.
    app.add_handler(MessageHandler(
        filters.VOICE | filters.AUDIO | filters.Document.AUDIO, ses_geldi))
    # .txt: uzun metin / uzun prompt listesi — mesaj sinirini tamamen atlar.
    app.add_handler(MessageHandler(
        filters.Document.ALL & ~filters.Document.AUDIO, belge_geldi))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, metin_geldi))

    # ⚠ TEMIZ KAPANIS: pencere kapatilinca (SIGTERM/SIGINT) python-telegram-bot
    # kapanis anindaki ag cagrisini yarida kesiyor ve ~200 satirlik traceback
    # basiyor. Kullanici bunu COKME saniyor. Kapaniyor mu diye bayrak tutup
    # o durumda tek satir yaziyoruz; GERCEK hatalar (yanlis token vb.) ise
    # net sekilde gorunmeye devam ediyor.
    # Kapanis aninda yarida kalan coroutine icin PTB uyari basiyor —
    # zararsiz ama kullaniciyi telaslandiriyor.
    warnings.filterwarnings("ignore", message=".*never awaited.*",
                            category=RuntimeWarning)
    kapaniyor = {"evet": False}

    # ⚠ TRACEBACK'I except YAKALAYAMAZ: python-telegram-bot kapanis anindaki
    # ag hatasini KENDI LOGGER'INA basar (logger.exception), exception olarak
    # yukari firlatmaz. Logger'a filtre takmak da YETMEZ — bir logger'in
    # filtresi yalnizca O logger'a dogrudan yazilan kayitlara uygulanir,
    # alt logger'lardan (telegram.ext.*) propagate edilenlere DEGIL.
    # Tek kesin yol: kapanis basladigi anda loglamayi global olarak kapatmak.
    def _kapan(*_):
        kapaniyor["evet"] = True
        logging.disable(logging.CRITICAL)
        raise SystemExit(0)

    for _sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        try:
            signal.signal(_sig, _kapan)
        except (ValueError, OSError):
            pass

    print(f"👻 Hayalet calisiyor. Klasor koku: {ayar.KOK}")
    try:
        app.run_polling(stop_signals=None)
    except (KeyboardInterrupt, SystemExit):
        pass
    except Exception as e:                                   # noqa: BLE001
        if not kapaniyor["evet"]:
            print(f"\n❌ Bot durdu: {type(e).__name__}: {str(e)[:300]}")
            if "token" in str(e).lower() or "Unauthorized" in str(e):
                print("   → Telegram token yanlis olabilir: "
                      f"{ayar.GIZLI_ENV}")
            raise SystemExit(1)
    print("👻 Hayalet kapandi.")


if __name__ == "__main__":
    calistir()
