# CLAUDE.md — BEDOSAHO AI

Metinden video üreten web aracı (animasyon + documentary). Bu dosya Claude Code'a projeyi tanıtır.

## Canlı sistem
- URL: http://204.168.136.159/ · Sunucu: Hetzner 2 vCPU, Docker konteyneri adı `bedosaho`
- Kod konteynerde `/opt/vidrush/` altında çalışır. Repo bu kodun kaynağıdır.
- Sağlık: `curl http://204.168.136.159/api/saglik`

## Deploy (ASLA elle scp/docker cp yapma — script kullan)
```bash
git pull && bash deploy.sh && git add -A && git commit -m "..." && git push
```
`deploy.sh`: dosyaları konteynere kopyalar, restart eder, `docker commit` ile kalıcılaştırır.
SSH anahtarı: `~/.ssh/bedosaho_hetzner` (repo'da DEĞİL; sahibinden alınır).

## ⚠️ Ortak sunucu — tek konteyner
- Deploy ÖNCESİ `git pull`, SONRASI `git push`. İki kişi aynı anda deploy etmez.
- Aktif video render'ı varken deploy etme (restart onu öldürür) — `deploy.sh` uyarır.
- `.env` gizli anahtarları içerir, git'te DEĞİL, sadece sunucuda. Asla commit etme, loga yazdırma.

## Mimari
- **TEK AKIŞ (20 Ağu 2026 pivotu)**: arayüzün tek yolu `tur=documentary, edit=akis` — cümle başına 5-7 sn sahne; önce stok video, bulunamazsa Magnific (nano-banana) 16:9 AI görseli; AI video klipler `MAG_KLIP_MAKS` tavanına kadar (`webapp/magnific_motor.py`). Eski animasyon/hikaye stilleri backend'de duruyor ama UI'dan kalktı.
- `webapp/server.py` — FastAPI: `/api/generate` (kuyruk), `/api/job/{id}`, `/api/animasyon-stilleri`, `/api/edit-stilleri`. Tek-işçi kuyruk (1 video/seferde).
- `webapp/pipeline.py` — üretim hattı. Önemli:
  - `uret()` ana akış: plan → sahne görselleri → seslendirme → props → Remotion render
  - `ANIMASYON_STILLERI` (3 stil), `EDIT_STILLERI` (3 documentary stili) ve `HIKAYE_STILLERI` (hikaye kanalı — sinematik gerçekçi film kareleri, ilk `HIKAYE_ACILIS_SN` sn "vurgu" yoğun hareket, altyazı, çapa ile karakter tutarlılığı)
  - Stil promptları `ANIM_STIL/EXP_STIL/HIK_STIL` + `*_SOZLESME` (planlayıcı) + `*_CERCEVE` (kompozisyon) sabitlerinde — **kalite ayarı buradan yapılır**
  - `referansli_gorsel()` — OpenAI/Gemini görsel üretimi (karakter+çapa+stil çoklu referans)
  - `oai_chat()` — dayanıklı LLM çağrısı (retry, bakiye hatası ayrımı)
  - Görsel modeli: `GORSEL_MODEL_ANIM` (gpt-image-1-mini), `GORSEL_MODEL_DOC` (gpt-image-2)
- `webapp/kaynak.py` — stok video (Pexels/Pixabay/Freepik) + Magnific upscale. Anahtar yoksa AI görsele düşer.
- `app/uret.py` — `seslendir()` edge-tts + altyazı. `TTS_RATE` (+15%), `TTS_KUYRUK` env.
- `app/render-studio/src/Video.tsx` — Remotion sahne bileşeni (geçiş, Ken Burns, altyazı, `@remotion/transitions` crossfade). `Root.tsx` süre hesabı.

## Ayarlanabilir env (konteynerde /root/bedosaho/.env)
`AI_SAGLAYICI` (openai/gemini), `IMAGE_QUALITY` (medium), `IMAGE_MODEL*`, `GEMINI_*`,
`ANIM_SAHNE_SN` (5), `TTS_RATE`, `RENDER_CRF` (18), `PEXELS_KEY`, `PIXABAY_KEY`,
`VIDEO_FPS` (24), `HIKAYE_SAHNE_SN` (6), `HIKAYE_ACILIS_SN` (150),
`MAG_KLIP_MAKS` (10, video başı AI klip tavanı), `MAG_VIDEO_MODEL` (minimax-hailuo-02-768p), `MAG_GORSEL_MODEL` (nano-banana-pro-flash).

## Kural
- Değişikliği **gerçek 1 dk'lık videoyla** test et (tahminle "çalışır" deme). Kareleri ffmpeg ile çıkarıp gözle bak.
- Maliyet görsel sayısına bağlı (8 dk animasyon ≈ $1.2). Gereksiz uzun test = boşa kredi.
- Türkçe cevap ver (kullanıcılar Türk).
