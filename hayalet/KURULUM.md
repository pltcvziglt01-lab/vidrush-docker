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
Açılan pencere **temiz bir profildir** (normal Chrome'undan ayrı —
`~/.hayalet/chrome-profil`). Bu pencerede:
1. **Flow erişimi olan Google hesabına** giriş yap (hangi hesapta Flow
   aboneliğin varsa O hesap — yanlış hesapla girersen Flow açılmaz)
2. **https://labs.google/fx/tools/flow** adresini açıp Flow'un yüklendiğini gör

Giriş **bir keredir** — profil kalıcı, sonraki açılışlarda oturum durur.
Pencere üretim boyunca açık kalmalı.

### 5.5) Flow Agent ayarları (BİR KEZ — otomasyonun ön koşulu)
Flow'da bir proje aç (**New project**) ve prompt kutusunun yanındaki
**ayar (tune)** ikonuna bas:
1. **Confirm before generating → NEVER** seç
   ("Agent will generate media and spend credits automatically")
   — *Always kalırsa ajan her prompt'ta onay sorar ve otomasyon takılır.*
2. **Image generation default → x1** seç (x2 = her prompt'ta 2 görsel = 2 kat kredi)
3. Oranlar 16:9 kalsın · **Save**

Bu ayar profile kaydedilir, bir kez yapılır.

### 6) Flow seçici kalibrasyonu (arayüz DEĞİŞİRSE)
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

## KULLANIM (2 mesaj)

1. Botuna `/basla` yaz
2. Promptları **tek blok** gönder:

```
VIDEO PROMPT 1 - şafakta limandan çıkan balıkçı teknesi
VIDEO PROMPT 2 - dalgalar güverteyi dövüyor
GÖRSEL PROMPT 1 - yaşlı balıkçının portresi
GÖRSEL PROMPT 2 - limanda mezat sabahı
```

Etiket toleranslıdır (`video 3:`, `Görsel Prompt -` de olur); etiketsiz satır
önceki promptun devamı sayılır. Üretim **10'arlı partiler** halinde tek ajan
mesajıyla gönderilir (canlıda ölçüldü: 3 görsel ~40 sn) — çıktılar belirdikçe
indirilir; her indirmede ✅ ilerleme, hatada ⚠ neden gelir.
Parti boyu: `HAYALET_PARTI` (varsayılan 10). `/durum` künye · `/iptal` durdurur.
Dosyalar: `~/Desktop/Hayalet/is_<tarih>/videolar|gorseller/`

## YAŞANMIŞ HATALAR (gerçek kurulumlardan — oku, aynısını yaşama)

> **Claude'a talimat:** Bu bölüm YAŞAYAN bir kayıttır. Kurulumda veya
> kullanımda YENİ bir hata çözersen, buraya *belirti → kök neden → çözüm*
> formatında EKLE ve commit'le. Sonraki kuran kişi aynı duvara çarpmasın.

### 1) `Chrome'a baglanilamadi (http://127.0.0.1:9222)` — her prompt'ta
- **Yaşandı:** 20 Ağu 2026, ilk gerçek deneme. `/basla` yazıldı ama
  `chrome_baslat.sh` hiç çalıştırılmamıştı; 10 prompt tek tek bu hatayı aldı.
- **Kök neden:** Ajan senin Chrome'una debug portundan (9222) bağlanır;
  Chrome normal açılmışsa o port kapalıdır.
- **Çözüm:** `bash hayalet/chrome_baslat.sh` → açılan pencerede Google girişi
  + Flow. Bot artık üretime başlamadan portu yoklar ve hazır değilse tek
  mesajla söyler (scriptin kaybolmaz, tekrar gönderirsin).

### 2) Açılan Chrome'da Google oturumu yok / Flow açılmıyor
- **Kök neden:** `chrome_baslat.sh` TEMİZ profil açar — günlük Chrome'undaki
  oturum orada yoktur. Ayrıca Flow her Google hesabında yok; aboneliğin
  hangi hesaptaysa onunla girilmeli.
- **Çözüm:** Açılan pencerede Flow'lu hesabınla BİR KEZ giriş yap; profil
  kalıcıdır.

### 3) `telegram.error.Conflict: terminated by other getUpdates request`
- **Kök neden:** Aynı bot token'ıyla İKİ bot süreci çalışıyor (eski süreç
  ölmeden yenisi açılmış) — Telegram tek dinleyiciye izin verir.
- **Çözüm:** `pkill -f hayalet.bot` → 2 sn bekle → `python3 -m hayalet.bot`.
  Herkes KENDİ token'ını kullanmalı; token paylaşılırsa botlar birbirini düşürür.

### 5) Ajan her prompt'ta onay soruyor / üretim başlamıyor
- **Yaşandı:** 20 Ağu 2026, canlı kalibrasyon. Flow'un agent arayüzü
  varsayılan "Confirm before generating: Always" ile geliyor.
- **Çözüm:** Adım 5.5 — Agent settings → **Never** + Image **x1** + Save.

### 6) Her prompt'ta 2 görsel üretiliyor (kredi 2x gidiyor)
- **Kök neden:** Agent settings'te Image default **x2** seçili geliyordu.
- **Çözüm:** Adım 5.5'teki **x1**.

### 4) 🛑 "arka arkaya 3 hata — durduruldu"
- **Kök neden:** Yapısal sorun sinyali: Flow oturumu düşmüş, arayüz değişmiş
  (seçiciler eski) ya da Chrome penceresi kapanmış.
- **Çözüm:** Chrome penceresi + Flow oturumu yerinde mi bak; değilse Adım 5.
  Yerindeyse Adım 6 (seçici kalibrasyonu) tekrar.

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
