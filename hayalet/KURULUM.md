# 👻 HAYALET — Flow Üretim Ajanı (Kurulum)

> **Bu dosyayı Claude Code'a at ve şunu yaz: "Bu dosyadaki kurulumu yap".**
> Claude işletim sistemini tespit eder, adımları uygular. Senden sadece
> 2 şey ister: kendi Telegram bot token'ın + Chrome'da Flow'a giriş.

---

## Ne yapar

Telegram'dan prompt gönderirsin → **senin bilgisayarındaki Chrome'da**
Google Flow'a girip görselleri/videoları üretir → **indirir ve klasörler**.
Edit/kurgu YOK — montajı kendin yaparsın (CapCut vb.).

Telegram **takip kanalıdır**: her indirmede "✅ 3/12 indi — devam ediyorum",
hata olursa "⚠ neden" bildirir. **Dosyalar Telegram'a gönderilmez** — diskte kalır:

```
~/Desktop/Hayalet/<proje>/
    videolar/    001_video_….mp4
    gorseller/   001_gorsel_….png
    is.json      promptlar + durum + hatalar
```

---

## CLAUDE İÇİN KURULUM TALİMATLARI

### 0) Sistem tespiti
```bash
uname -s   # Darwin=macOS, Linux=Linux; Windows ise WSL2 öner
```

### 1) Araçlar
**macOS:** `brew install python@3.11` (brew yoksa önce onu kur)
**Linux:** `sudo apt update && sudo apt install -y python3 python3-pip curl`

### 2) Python paketleri
```bash
python3 -m pip install --user --upgrade "python-telegram-bot>=21" playwright
```

### 3) Chrome kurulu olmalı
macOS: `/Applications/Google Chrome.app` var mı? Linux: `command -v google-chrome`.
Yoksa kullanıcıya https://google.com/chrome indirt.

### 4) Kullanıcıya KENDİ Telegram botunu kurdur
Kullanıcıya aynen şunu söyle:
1. Telegram'da **@BotFather**'ı aç
2. `/newbot` → bota isim ver → BotFather bir **token** verir (`12345:AAF...`)
3. Token'ı bana yapıştır
4. Kendi botunu Telegram'da açıp **/start** yaz (bot ancak önce sen yazınca cevap verebilir)

Token gelince (ASLA koda/repoya yazma):
```bash
mkdir -p ~/.hayalet && chmod 700 ~/.hayalet
echo "HAYALET_TELEGRAM_TOKEN=BURAYA_TOKEN" > ~/.hayalet/gizli.env
chmod 600 ~/.hayalet/gizli.env
TOKEN=$(grep TOKEN ~/.hayalet/gizli.env | cut -d= -f2)
curl -s "https://api.telegram.org/bot$TOKEN/getMe"   # "ok":true dönmeli
```

### 5) Chrome'u kontrol portuyla başlat + Flow'a giriş
```bash
bash hayalet/chrome_baslat.sh
```
Açılan pencerede kullanıcı **Google hesabına girip**
**https://labs.google/fx/tools/flow** açmalı. Pencere açık kalır.

### 6) Flow seçici kalibrasyonu (İLK KURULUMDA ŞART)
```bash
python3 -c "
import sys; sys.path.insert(0,'.')
from hayalet import flow_surucu
from pathlib import Path
r = flow_surucu.kesfet(Path('hayalet/flow_kesif.json'))
print('URL:', r['url'])
print('textarea:', r['textarea'][:5])
print('dugmeler:', [d['metin'] for d in r['dugme'][:12]])
"
```
Çıktıdaki gerçek alan/buton adlarına göre `hayalet/flow_surucu.py` içindeki
**`SECICILER`** tablosunu güncelle (tek nokta, kod dağılmaz).

### 7) Botu başlat
```bash
python3 -m hayalet.bot
```
`👻 Hayalet calisiyor` görünmeli; terminal açık kalır.
(İstenirse kalıcı: macOS'ta `launchd`, Linux'ta `systemd --user` servisi kur.)

---

## KULLANIM

| Telegram komutu | Ne yapar |
|---|---|
| `/yeni proje_adi` | Yeni klasör açar |
| `/video` | Sonraki mesajlar video promptları (her satır = 1 prompt) |
| `/gorsel` | Sonraki mesajlar görsel promptları |
| `/basla` | Üretim + indirme başlar |
| `/durum` | Künye: kaç prompt, kaç hata, klasör yolu |
| `/iptal` | Sıradaki prompttan sonra durur |

**Takip mesajları:** her indirmede ✅ ilerleme; hatada ⚠ neden; art arda
3 hata olursa 🛑 durur ("oturum düştü / seçici kırıldı" demektir — Adım 6'yı tekrarla).

---

## Sorun giderme

| Belirti | Çözüm |
|---|---|
| `Chrome'a baglanilamadi` | `bash hayalet/chrome_baslat.sh`; pencereyi kapatma |
| `prompt alani bulunamadi` | Flow arayüzü değişti → Adım 6 kalibrasyonu |
| `sonuc gorunmedi` (15 dk) | `HAYALET_FLOW_TAVAN` artır (`~/.hayalet/gizli.env` içine, sn) |
| Bot cevap vermiyor | `getMe` testi (Adım 4); botuna Telegram'dan `/start` yazdın mı? |
| 🛑 art arda 3 hata | Chrome'da Flow oturumu düşmüş olabilir — giriş yap, `/basla` tekrar |

## Bilinen sınırlar (dürüstçe)
- Flow otomasyonu **kırılgandır**: Google arayüzü değişince Adım 6 tekrar gerekir.
  Sistem bunu sessizce geçmez, net hatayla söyler.
- Otomatik erişim Google ToS'ta gri alan — kendi hesabın, kendi riskin.
- Hız Flow'un üretim hızıdır; promptlar sırayla işlenir.
