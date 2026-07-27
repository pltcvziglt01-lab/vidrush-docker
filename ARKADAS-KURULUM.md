# BEDOSAHO AI — Geliştirici Kurulumu (Claude Code ile)

Bu proje **metinden animasyon/belgesel video** üreten bir web aracı.
Canlı: **http://204.168.136.159/** · Sunucu: Hetzner (2 vCPU), Docker konteyneri `bedosaho`.

## 0. Ne çalışıyor?
- **webapp/** — FastAPI sunucu (`server.py`), üretim hattı (`pipeline.py`), footage/upscale (`kaynak.py`), arayüz (`static/index.html`)
- **app/uret.py** — edge-tts seslendirme + altyazı
- **app/render-studio/** — Remotion (React) video render motoru; sahne bileşeni `src/Video.tsx`
- Görsel: OpenAI `gpt-image-1-mini` (animasyon) / `gpt-image-2` (documentary). Sağlayıcı `AI_SAGLAYICI` env ile openai/gemini.

## 1. Gerekenler
- **Claude Code** (claude.ai/code veya CLI)
- **git**, **python3**, **ssh** (Mac/Linux'ta hazır)
- **SSH anahtarı**: `~/.ssh/bedosaho_hetzner` — bunu **Polat sana güvenli şekilde gönderecek**
  (WhatsApp/Signal ile; e-posta/GitHub'a KOYMA). Sonra:
  ```bash
  chmod 600 ~/.ssh/bedosaho_hetzner
  ```

## 2. Repoyu klonla
```bash
git clone https://github.com/pltcvziglt01-lab/vidrush-docker.git
cd vidrush-docker
```
Bu dizini Claude Code'da aç. Claude, kök dizindeki `CLAUDE.md`'yi okuyup projeyi tanır.

## 3. Değişiklik yap → canlıya al
Kodda değişikliği yerelde yap (Claude Code ile), sonra **tek komut**:
```bash
git pull            # ÖNCE — Polat'ın son değişikliklerini al
# ... Claude Code ile düzenle ...
bash deploy.sh      # değişikliği canlı sunucuya gönderir + yeniden başlatır + kalıcılaştırır
git add -A && git commit -m "ne yaptın" && git push   # SONRA — paylaş
```

## 4. ⚠️ ORTAK SUNUCU KURALLARI (çok önemli)
Tek sunucu, tek konteyner var. İkiniz aynı anda dokunursa iş bozulur:
1. **Deploy'dan önce `git pull`, sonra `git push`.** Her zaman.
2. **Aynı anda ikiniz `deploy.sh` çalıştırmayın.** Önce "deploy ediyorum" deyin.
3. **Biri video üretirken deploy etmeyin** — `deploy.sh` bunu kontrol edip uyarır (konteyner restart aktif render'ı öldürür).
4. **`.env`'e asla dokunma / commit etme** — API anahtarları orada, sadece sunucuda durur.

## 5. Faydalı komutlar
```bash
S="ssh -i ~/.ssh/bedosaho_hetzner root@204.168.136.159"
$S "docker logs --tail 40 bedosaho"                 # canlı log
$S "docker exec bedosaho sh -c 'ls /opt/vidrush/webapp'"   # konteyner içi
curl -s http://204.168.136.159/api/saglik            # servis sağlık
```

## 6. Test etme
Kredi harcamamak için: küçük değişikliği **1 dakikalık** videoyla test et (~8 TL).
Üretim maliyeti görsel sayısına bağlı — 8 dk animasyon ≈ $1.2. Bakiye: OpenAI hesabı.

## 7. Mimari notlar
- Üretim akışı: metin → `pipeline.uzun_plan` (LLM sahne planı) → sahne başı `referansli_gorsel` (AI görsel) → `uret_seslendir` (edge-tts) → props.json → Remotion render → mp4.
- **Animasyon 3 alt-stil**: `anlati-deneme`, `egitici-explainer`, `hikaye-whatif` (pipeline.py `ANIMASYON_STILLERI`).
- **Documentary 3 stil**: `EDIT_STILLERI`.
- Stil promptları pipeline.py'de `*_STIL` / `*_SOZLESME` sabitlerinde — kalite ayarı buradan.
- Kuyruk tek-işçi (1 video/seferde) — 2 vCPU korumasi.
