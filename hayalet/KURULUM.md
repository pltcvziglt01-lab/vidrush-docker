# 👻 HAYALET — Metin + Ses → CapCut Projesi (Kurulum)

> **Bu dosyayı Claude Code'a at ve şunu yaz: "Bu dosyadaki kurulumu yap".**
> Claude işletim sistemini tespit eder, adımları uygular. Senden sadece
> 3 şey ister: kendi Telegram bot token'ın, Chrome'da Flow'a giriş,
> bir OpenAI anahtarı.

## ⚠ ÖNCE ŞUNU OKU — bu dosya KOD İÇERMEZ

Bu dosya yalnızca **kurulum adımlarıdır**. Kodun da elinde olması gerekir.
İki yoldan biri:

**A) Tek dosya (en kolay — repo gerekmez).** Sana `HAYALET_PAYLAS.md`
gönderilmişse yalnızca ONU Claude Code'a at ve *"bu dosyadaki sistemi kur"*
de. İçinde hem tüm kaynak kod hem bu kurulum adımları gömülüdür; bu dosyaya
ayrıca ihtiyacın yok.

**B) Repo klonu.** Repoya erişimin varsa:
```bash
git clone <repo-adresi> && cd <repo>
```
Sonra bu dosyayı Claude Code'a at. Kod zaten `hayalet/` altındadır.

> Kısaca: **arkadaşına tek dosya gönderiyorsan `HAYALET_PAYLAS.md` gönder.**
> Bu `KURULUM.md` repoyla birlikte çalışanlar içindir.

---

## Ne yapar

**Telegram'a metin + seslendirme verirsin, CapCut'ta düzenlemeye hazır bir
proje çıkar.** Arada olan her şey otomatik:

```
/senkron
   ↓  METİN            (her dilde, düz metin)
   ↓  SESLENDİRME      (ses dosyası ya da sesli mesaj)
   ↓  her cümle için sinematik prompt          (LLM)
   ↓  Google Flow'da üretim + indirme          (senin Chrome'un)
   ↓  cümle sınırlarını SESTEN çıkarma         (ASR kelime zamanları)
   ↓  CapCut zaman çizgisine dizme             (her cümle = ayrı klip)
   ✅ CapCut'ı aç, geçiş/yazı/efekt ekle
```

Cümlelerin **ilk %30'u koşulsuz VİDEO** olur (kanal açılışı hareket ister;
Flow klipleri ~6 sn). Kalan %70'te LLM cümle cümle seçer: hareket şartsa
video, değilse görsel.

Telegram **takip kanalıdır**: "✅ 3/12 indi — devam ediyorum", hata olursa
"⚠ neden" bildirir. Dosyalar diskte kalır:

```
~/Desktop/Hayalet/is_<tarih>/
    video/           001_video_….mp4     (baştaki sayı = CÜMLE NUMARASI)
    gorsel/          004_gorsel_….png
    seslendirme.m4a  gönderdiğin ses
    metin.txt        gönderdiğin metin
    eslesme.json     {"1": "video/001_….mp4", …}  cümle → dosya
    final.mp4        kontrol videosu (düz mp4)
    final_kurgu.json hangi cümle kaç saniye, hangi dosya
    is.json          promptlar + durum + hatalar
```

Ayrıca 🎬 `/hikaye` modu durur: promptları sen yazarsın, bot yalnızca
üretip indirir (kurgu yok).

---

## CLAUDE İÇİN KURULUM TALİMATLARI

### 0) Sistem tespiti
```bash
uname -s   # Darwin=macOS, Linux=Linux; Windows ise WSL2 öner
```

### 1) Araçlar
**macOS:** `brew install python@3.11 ffmpeg` (brew yoksa önce onu kur)
**Linux:** `sudo apt update && sudo apt install -y python3 python3-pip curl ffmpeg`

`ffmpeg` **zorunlu** — kurgu/hizalama onunla yapılır. Doğrula:
```bash
ffmpeg -version | head -1 && ffprobe -version | head -1
```

⚠ Altyazıyı görüntüye yakmak istiyorsan ffmpeg **libass** ile derlenmiş
olmalı. Kontrol:
```bash
ffmpeg -hide_banner -filters | grep -c " subtitles "
```
`0` dönerse yakma yok — SRT gömülü iz olarak eklenir (oynatıcıdan açılır).
Zaten yazıları CapCut'ta eklemek daha iyi; bu bir engel değil.

### 2) Python paketleri
```bash
python3 -m pip install --user --upgrade "python-telegram-bot>=21" playwright
```

### 3) Chrome kurulu olmalı
macOS: `/Applications/Google Chrome.app` var mı? Linux: `command -v google-chrome`.
Yoksa kullanıcıya https://google.com/chrome indirt.

### 3.5) CapCut kurulu olmalı + EN AZ BİR PROJESİ olmalı
CapCut'ın taslak formatı **belgelenmiş değildir** ve sürümden sürüme
değişir. Bu yüzden şema tahmin EDİLMEZ — kullanıcının **kendi CapCut'ındaki
gerçek bir projeden** kopyalanır (`hayalet/capcut.py` → `bagisci_bul`).
Böylece kurulu sürümle birebir uyumlu taslak üretilir.

Kullanıcıya söyle: CapCut'ı aç, **bir video + bir ses** zaman çizgisine
koyup kaydet, kapat. Bir kez yeterli. Doğrula:
```bash
python3 -c "
import sys; sys.path.insert(0,'.')
from hayalet.capcut import bagisci_bul
b = bagisci_bul(); print('✓ şablon:', b['yol'].parent.name,
                         '| CapCut', b['taslak'].get('new_version'))"
```
Hata verirse kullanıcı henüz uygun bir proje kaydetmemiştir.

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

### 4.5) OpenAI anahtarı (senkron mod için ŞART)
İki yerde kullanılır: (a) her cümle için sinematik prompt yazımı,
(b) **cümle sınırlarının sesten çıkarılması** (ASR kelime zaman damgaları).
```bash
echo "HAYALET_OPENAI_KEY=sk-..." >> ~/.hayalet/gizli.env
```
Anahtar yoksa: promptlar cümlenin kendisi olur **ve** hizalama karakter
oranına düşer (kayma birikir). `/hikaye` modu anahtarsız çalışır.

### 5) Chrome'u kontrol portuyla başlat + Flow'a giriş
```bash
bash hayalet/chrome_baslat.sh
```
> ⚠ Bu adım **Flow'a giriş yapman içindir**. Üretim sırasında Playwright
> Chrome'u kendisi başlatır ve gerekirse bu pencereyi kapatıp yeniden açar
> — giriş kalıcı profilde durduğu için oturumun kaybolmaz.

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
4. **Proje adresini kopyala** (`.../flow/project/<uuid>`) ve kaydet:
   ```bash
   echo "HAYALET_FLOW_URL=<kopyaladığın adres>" >> ~/.hayalet/gizli.env
   ```
   Prompt kutusu yalnızca proje içinde vardır; bu olmadan üretim başlamaz.

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

## KULLANIM — iki mod

### 🎬 `/hikaye` — hazır promptlarını verirsin
Promptları TEK BLOK gönderirsin:
```
VIDEO PROMPT 1 - şafakta limandan çıkan balıkçı teknesi
GÖRSEL PROMPT 1 - yaşlı balıkçının portresi
```
Çıktılar diske iner; Telegram'a yalnızca ilerleme/hata düşer.

### 🧠 `/senkron` — metin + ses verirsin, CapCut projesi çıkar

**1.** Telegram'da `/senkron` yaz
**2.** **ANA KARAKTER** ver, ya da `yok` de
**3.** Anlatım **METNİNİ** gönder → parça parça ya da `.txt` dosyası
   olarak; bitince `/tamam` yaz
**4.** **VARSAYILAN TÜR** seç: karışık / tamamı görsel / tamamı video
**5.** **PROMPTLARI** gönder — her satır bir cümle, sırayla; parça parça
   ya da `.txt` dosyası olarak
**6.** **SESLENDİRMEYİ** gönder — uzunsa parçalara bölüp sırayla
**7.** `/hazir` yaz → Flow → indirme → hizalama → CapCut

> Stil sorusu **yoktur**: promptları sen yazdığın için stil zaten onların
> içindedir. Sistemin ayrıca stil dayatması promptu bozardı.

#### Ana karakter
`Ad: betimleme` biçiminde verirsin:
```
Elif: 8 yaşında, kızıl örgülü saçlı, yeşil parkalı bir kız
```
Promptunda **`Elif`** yazdığın yere tam betimlemeyi koyar. Adsız da
verebilirsin; o zaman promptta **`@karakter`** yazdığın yere koyar.
Promptta karaktere atıf yoksa prompt **aynen kalır** — manzara kareleri
bozulmaz.

> ⚠ **Neden yerine koyuyor?** Flow her promptu bağımsız üretir, önceki
> kareyi hatırlamaz. Sadece "Elif" yazmak yetmez; Elif'in kim olduğunu
> bilmez. Betimlemenin her seferinde yeniden yazılması tutarlılığın tek
> yoludur.
>
> ⚠ Betimleme **metindir**, fotoğraf değil. Flow'a gerçek referans fotoğrafı
> yüklemek tarayıcı otomasyonunda ayrı bir iş; henüz yok.

#### Promptlar
Her satır bir cümleye karşılık gelir. Satır başı numarası isteğe bağlı.
```
1. Karlı bir sokak, wide shot, kalın konturlu 2D çizgi film
2. video: Elif kapıyı açıyor, medium shot, yavaş dolly-in
3. Boş sokak, kuş bakışı, pastel renkler
```
Bir satırı `video:` ya da `görsel:` ile başlatırsan o satır için varsayılan
türü ezersin.

⚠ **Prompt sayısı cümle sayısına EŞİT olmalı.** Bir satır kayarsa sonraki
tüm cümleler yanlış görüntüye bağlanır ve bu sessizce olur.

#### 80+ prompt nasıl gönderilir
Telegram mesaj sınırı **4096 karakter** — 80 promptluk bir liste tek mesaja
sığmaz, Telegram onu bölerek gönderir. İki çözüm var:

**1. Parça parça gönder.** Bot biriktirir ve kaçta kaç olduğunu söyler
(`📥 45/81 prompt alındı — 36 tane daha bekliyorum`). Sayı tamamlanınca
kendiliğinden ses adımına geçer. Aynısı metin için de geçerli — orada
hedef sayı bilinmediği için bitince `/tamam` yazarsın.

**2. `.txt` dosyası olarak at.** *(en pratik yol)* Sınır tamamen atlanır,
81 prompt tek seferde alınır. UTF-8 düz metin, en fazla 2 MB. Aynı yol
anlatım metni için de çalışır.

| Komut | Ne yapar |
|---|---|
| `/cumleler` | Metnin tam olarak nasıl bölündüğünü listeler |
| `/tamam` | Metin bitti, sonraki adıma geç |
| `/sifirla` | Biriken promptları (ya da metni) temizle |

⚠ **Fazla prompt gelirse bot keser mi?** Hayır. Hangisinin fazla olduğunu
bilemeyeceği için hepsini temizler ve baştan ister — kesmek sonraki tüm
cümleleri kaydırırdı.

#### Varsayılan tür
| Seçenek | Ne olur |
|---|---|
| 🎞 İlk %30 video, kalanı görsel | Belgesel/anlatı için *(varsayılan)* |
| 🖼 Tamamı görsel | Hiç video yok — **animasyon/çizgi kanallar için** |
| 🎬 Tamamı video | Her cümle video *(en pahalı, en yavaş)* |

**Cümle sınırları nasıl bulunur** (sırayla denenir, hangisi kullanıldığı
her zaman yazılır — sessiz düşüş yok):

| # | Yöntem | Ne zaman | Doğruluk |
|---|---|---|---|
| 1 | Cümle başına ayrı ses dosyası | `--ses` bir klasörse | **Kesin** |
| 2 | ASR kelime zaman damgaları | OpenAI anahtarı varsa | **Çok iyi** |
| 3 | `silencedetect` duraklamaları | duraklama sayısı = cümle sayısı-1 | İyi |
| 4 | Karakter oranı | hiçbiri olmazsa | **Yaklaşık** (uyarır) |

> Ölçüm (21 Ağu 2026): macOS `say` ile üretilmiş 5 cümlelik TR anlatımda
> ASR sınırları, sesteki gerçek duraklamalarla **0.05–0.17 sn** içinde
> örtüştü. Aynı seste varsayılan eşikle `silencedetect` **hiç** duraklama
> bulamadı — bu yüzden ASR birincil yöntemdir.

⚠ **Telegram bot indirmesi 20MB ile sınırlıdır** (senin gönderme sınırın
2GB ama bot o kadarını *alamaz*). Bot dosyayı indirmeye kalkışmadan önce
boyuta bakar ve ne yapacağını söyler.

| 30 dk ses | Boyut | |
|---|---|---|
| Sesli mesaj (Telegram opus) | ~7 MB | ✅ |
| mp3 64kbps mono | ~14 MB | ✅ |
| m4a 96kbps | ~22 MB | ❌ |
| mp3 128kbps stereo | ~29 MB | ❌ |

**Çözüm 1 — sıkıştır** (30 dk → ~14 MB):
```bash
ffmpeg -i ses.mp3 -ac 1 -b:a 64k kucuk.mp3
```

**Çözüm 2 — parçalara böl, sırayla gönder** (bot birleştirir):
```bash
ffmpeg -i ses.mp3 -f segment -segment_time 900 -c copy parca_%02d.mp3
```
Parçaları **sırayla** gönder, bitince `/hazir` yaz. Parçalar farklı
formatlarda olabilir (sesli mesaj + mp3 + m4a karışık) — bot hepsini tek
formata getirip birleştirir ve süre kaybı olmadığını doğrular.

> ⚠ **Bot dosyayı kendisi bölemez.** 20MB sınırı botun *indirmesindedir*;
> dosya Telegram sunucusunda durur, bot ona hiç erişemez. Bölme kaçınılmaz
> olarak gönderen tarafta olur.

64kbps mono'da tek parça tavanı **~41 dakika**. Ses kalitesi hizalamayı
etkilemez — ASR zaten 16kHz mono'ya indirerek çözümler.

⚠ **UZUN ANLATIM = ÇOK ÜRETİM.** Bu maliyeti önceden bil: 30 dakikalık bir
anlatım kabaca **400-450 cümledir**. Kural gereği ilk %30'u video demek
~130 video klibi + ~300 görsel demektir. Flow'da video klipleri dakikalarca
sürer; bu iş **saatler** alır ve ciddi kredi harcar. Önce 2-3 dakikalık bir
metinle uçtan uca dene, sonucu gör, sonra uzun metne geç.

⚠ **Tek bir cümlenin medyası üretilemezse CapCut dizilimi YAPILMAZ.**
Eksik klip sırayı kaydırıp sessizce yanlış senkron üretir; bot durur ve
hangi cümlelerin eksik olduğunu söyler. Dosyalar diskte durur.

### 🎚 Telegram'sız kullanım (elle kurgu)

Dosyalar zaten diskteyse doğrudan:
```bash
python3 -m hayalet.kurgu --metin metin.txt --ses seslendirme.m4a \
    --medya ~/Desktop/Hayalet/is_xxx --cikti final.mp4 --capcut "PROJE_ADI"
```
Hangi medya hangi cümleye: dosya adının başındaki sayı (`001_`, `002_`)
ya da medya klasöründeki `eslesme.json`. `--capcut` vermezsen sadece düz
`final.mp4` üretir.

⚠ **CapCut kapalıyken çalıştır**, sonra aç — açık CapCut taslak klasörünü
kendi hafızasından üzerine yazabilir.

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

### 7) CapCut projeyi listeliyor ama AÇMIYOR (tıklayınca hiçbir şey olmuyor)
- **Yaşandı:** 21 Ağu 2026, CapCut 9.3.0 taslak üretimi geliştirilirken.
  Proje listede göründü, çift tıklamada sessizce hiçbir şey olmadı; log yok.
- **Kök neden:** Gerçek projelerde `draft_info.json` içindeki `id`,
  `Timelines/<UUID>` klasör adı ve `Timelines/project.json` içindeki
  `main_timeline_id` **aynı UUID** olmak zorunda. Üçü farklı olunca CapCut
  taslağı listeler ama yükleyemez ve sessizce vazgeçer.
- **Çözüm:** `capcut.py` üçünü tek `zc_id`'den üretir. Doğrula:
  ```bash
  python3 -c "
  import json,os,sys; d=sys.argv[1]
  i=json.load(open(f'{d}/draft_info.json'))['id']
  t=[x for x in os.listdir(f'{d}/Timelines') if not x.endswith('.json')][0]
  m=json.load(open(f'{d}/Timelines/project.json'))['main_timeline_id']
  print('ÜÇÜ AYNI' if i==t==m else f'FARKLI: {i} {t} {m}')" <taslak_klasörü>
  ```

### 8) CapCut açılıyor ama klipler kırmızı: "Dosya erişilemiyor"
- **Yaşandı:** 21 Ağu 2026. Klipler `/tmp` altındayken de,
  `~/Desktop` altındayken de kırmızı çıktı; `~/Downloads` altındaki
  medyayı olan gerçek projeler sorunsuzdu.
- **Kök neden:** macOS TCC — CapCut'ın Masaüstü/Belgeler klasörlerine
  erişim izni olmayabilir. `/tmp` zaten sandbox dışı.
- **Çözüm:** `capcut.py` klipleri taslağın kendi içine
  (`<taslak>/Resources/hayalet/`) **kopyalar**; orası CapCut'ın kendi veri
  klasörüdür, izin gerekmez. Taslak büyür ama kırık medya olmaz.

### 9) `Timelines/project.json` şeması uydurulursa proje bozulur
- **Kök neden:** Bu dosyanın gerçek şeması
  `{config, create_time, id, main_timeline_id, timelines:[…], version}`.
  Tahmini bir şema (ör. `{current_timeline_id, timeline_ids}`) yazılırsa
  proje açılmaz. Ayrıca `timeline_layout.json` de zaman çizgisi UUID'sine
  işaret eder — bağışçıdan olduğu gibi kopyalanmamalı.
- **Çözüm:** İkisi de `capcut.py` içinde üretilir, kopyalanmaz.

### 23) Flow'un İKİ farklı ayar arayüzü — otomasyonu bozan iki ayar
- **Yaşandı:** 23 Ağu 2026, başka bir hesabın projesine geçilince.
- **Kök neden:** Flow projeleri iki farklı arayüzle gelebiliyor:
  - **A)** Prompt kutusunun yanında görünür çip (`Video · 720p · 10s
    crop_16_9 x1`) — tıklayınca sekmeler açılır.
  - **B)** Çip YOK; ayarlar `tune|Ayarlar` düğmesinin arkasındaki
    "Ajan ayarları" panelinde.
  B'de iki ayar otomasyonu bozuyordu:
  - "Üretme işleminden önce onaylayın: **Her zaman**" → ajan her promptta
    onay sorar, üretim hiç başlamaz.
  - "Varsayılan görüntü üretimi: **x2**" → her promptta 2 görsel,
    **iki katı kredi**.
- **Çözüm:** `flow_surucu.flow_ayarla()` her iki arayüzü de tanıyor;
  üretimden önce onayı kapatıyor, adedi x1 yapıyor, oranı 16:9'a sabitliyor.
- **Tuzak 1:** Ayar paneli prompt görünümünün YERİNE açılıyor; Escape her
  zaman geri getirmiyordu, her partide sayfa yenilenip ~40 sn boşa gidiyordu.
- **Tuzak 2:** Panelden dönmek için `arrow_back` tıklamak **projeden
  tamamen çıkarıyor** (sol üstteki "Geri Dön"); üretim 0/3'e düştü.
  Doğru yol: proje adresine doğrudan `goto`.

### 24) Chrome profilini/hesabını değiştirme
Hayalet izole bir profil kullanır; gerçek profilinden **kopyalanır**
(mock-keychain bayrakları kalktığı için artık çalışıyor, bkz. madde 15):
```bash
K=~/Library/Application\ Support/Google/Chrome
H=~/.hayalet/chrome-profil
pkill -f "user-data-dir=$H"; rm -rf "$H"; mkdir -p "$H/Default"; touch "$H/First Run"
rsync -a --exclude='Cache' --exclude='Code Cache' --exclude='GPUCache' \
      --exclude='Service Worker/CacheStorage' --exclude='blob_storage' \
      --exclude='Extensions' "$K/Profile N/" "$H/Default/"
cp "$K/Local State" "$H/Local State"
```
Profil numarasını bulmak için `Local State` → `profile.info_cache` içindeki
`user_name` alanına bak. Sonra `HAYALET_FLOW_URL`'i o hesabın proje
adresiyle güncelle.

### 22) Görüntü 1-2 saniyede bir değişiyor — izlemesi yorucu
- **Yaşandı:** 22 Ağu 2026, 179 cümlelik gerçek iş. Cümle başına bir görsel
  konunca ortanca klip **2.14 sn**, %70'i 3 sn altında, 24 tanesi 1 sn'den
  kısa çıktı. Stroboskop etkisi.
- **Çözüm:** `kurgu.sahneleri_grupla()` — kısa cümleler önceki sahneye
  katılır, sahne `HAYALET_EN_KISA_SAHNE` (varsayılan **5 sn**) eşiğine
  ulaşana kadar büyür. Ses **hiç kaymaz**: süreler toplanır, toplam sabit.
  Grubun görüntüsü ilk cümlenin görselidir; diğerleri diskte kalır.
- **Ölçüm:** 179 klip / ortanca 2.14 sn → **68 klip / ortanca 6.2 sn**,
  en kısa 5.0, en uzun 10.0, 1 sn altında klip **0**.
- **Neden karakter sayısı değil süre:** karakter sayısı sürenin dolaylı
  tahminidir (konuşma hızı değişir); ASR'den gelen gerçek süreler zaten
  elimizde ve ekranda kalma süresini doğrudan verir.
- **Eşik denemeleri (aynı iş):** 3 sn→92 klip · 4→78 · 5→68 · 6→56 ·
  7→50 · 8→44 klip.

### 21) Üretim ortasında `Locator.click: Timeout 30000ms` — tüm iş ölüyor
- **Yaşandı:** 22 Ağu 2026. 179 promptluk iş 147. adımda çöktü; prompt
  kutusu (`div[contenteditable='true']`) sayfadan kayboldu. Bot
  "Beklenmeyen hata" deyip durdu ve **CapCut adımına hiç gelemedi** —
  o ana kadar inen 146 görsel boşa gidiyordu.
- **Kök neden (iki katmanlı):**
  1. Flow arayüzü uzun oturumlarda prompt kutusunu kaybedebiliyor.
  2. Üretim bir istisna atınca `_senkron_yurut` komple düşüyordu.
- **Çözüm 1 — kurtarma:** Her prompttan önce kutu var mı kontrol edilir;
  yoksa **sayfa yenilenir**, tür/oran yeniden ayarlanır ve devam edilir.
  Tıklamalarda 30 sn yerine 15 sn zaman aşımı.
- **Çözüm 2 — iş çöpe gitmesin:** Üretim çökse bile yakalanır ve **o ana
  kadar inenlerle kurguya devam edilir**; eksik cümlelerde önceki görüntü
  uzar (bkz. madde 18).
- **Çözüm 3 — eşleşme diskten:** Cümle→dosya eşleşmesi artık sonuç
  listesinden değil, **diskteki gerçek dosyalardan** kurulur (dosya adının
  başındaki sayı = cümle no). Yarıda kesilen iş de doğru eşleşir.
- **Yarım kalan işi sürdürme:** eksik cümleler `is.json` içindeki
  promptlardan yeniden üretilip aynı klasöre indirilebilir; sonra
  `kurgu.kurgula(...)` CapCut projesini kurar. Baştan başlamak gerekmez.

### 19) Karakter yerine ÜÇ GÖRÜNÜŞLÜ REFERANS SAYFASI üretiliyor
- **Yaşandı:** 22 Ağu 2026. Karakter alanına 1575 karakterlik **tam bir
  referans-sayfası promptu** yapıştırıldı ("A character reference sheet: the
  same man drawn three times side by side… **No scene, no text**… STYLE…
  COLOUR… 16:9, high resolution"). Kod bu metni `@karakter` geçen her yere
  **olduğu gibi** enjekte etti; sahne promptu zehirlendi ve Flow sahne
  yerine referans sayfası üretti.
- **Kök neden:** Enjeksiyon metninde uzunluk sınırı ve akıl kontrolü yoktu.
  Karaktere yalnızca **görünüş** tarifi girmeli; stil/oran/"sahne yok" gibi
  meta talimatlar sahneyi ele geçirir.
- **Çözüm:** `beyin.karakter_sadelestir()` — meta işaretleri (`reference
  sheet`, `no scene`, `16:9`, bölüm başlıkları…) ya da 260 karakter sınırı
  aşılırsa metin LLM ile **tek satırlık görünüş cümlesine** indirgenir
  (LLM yoksa CHARACTER/CLOTHING bölümleri toplanır). Kelime ortadan
  bölünmez. Bot enjekte edilecek hali **kullanıcıya gösterir**.
- **Doğrulandı (canlı):** 1575 → 249 karakter; aynı prompt artık kapı
  önünde duran adamı üretiyor (gri saç, sakal, turuncu yakalı mavi ceket
  korunmuş), referans sayfası değil.

### 20) Çalışan botun tarayıcısı aniden kapanıyor
- **Yaşandı:** 22 Ağu 2026. Bot iş yaparken ikinci bir Hayalet süreci
  başlatıldı; `_profil_chromeu_kapat` botun Chrome'unu kapattı ve iş yarıda
  öldü.
- **Kök neden:** İki süreç aynı Chrome profilini paylaşamaz.
- **Çözüm:** `chrome_baglan` başka bir `hayalet.bot` süreci varsa bağlanmayı
  **reddediyor** ve net söylüyor. Bilerek geçmek için `HAYALET_KILIT_YOKSAY=1`.

### 18) Bazı promptlar üretilemiyor — iş çöpe gitmesin
- **Belirti:** Flow tek tek promptlarda "might violate our policies" ya da
  geçici hata verebiliyor; o cümle medyasız kalır.
- **Çözüm 1 — tekrar dene:** `uret_tekrarli()` başarısızları toplayıp
  yeniden gönderiyor (`HAYALET_TEKRAR`, varsayılan 2 ek tur). Aynı prompt
  ikinci denemede çoğu zaman geçiyor.
- **Çözüm 2 — boşluğu önceki sahneyle kapat:** Kalıcı olarak üretilemeyen
  cümlelerde **artık durmuyoruz**. O cümlenin süresi bir önceki sahneye
  eklenir; önceki görüntü ekranda daha uzun kalır (ör. 2 sn yerine 7.6 sn).
  Ses **hiç kaymaz**, izleyici boşluk görmez.
- **Doğrulandı (canlı):** 5 cümle, 2'sinin medyası yok →
  `5 cümle → 3 klip`, 1. klip 2.04 sn yerine **7.64 sn**;
  ses 11.26 sn / video 11.23 sn → **fark 0.02 sn**.
- Künyede `medyasiz_cumleler` ve `uzatilan_cumle` alanları tutulur.

### 17) Üretim neredeyse hiç ilerlemiyor (2 saatte 2 görsel)
- **Yaşandı:** 22 Ağu 2026, 183 promptluk gerçek iş. 2 saatte yalnızca 2
  görsel indi; inen dosyalar 001 ve 021 — aradaki cümleler hiç üretilmedi.
- **Kök neden:** `parti_uret` tek mesajda 10 numaralı prompt gönderiyordu.
  Flow ajanı bu mesaja **parti başına yalnızca 1 görsel** üretiyor. Kalan 9
  hiç gelmiyor, bot tavan dolana kadar (45 dk) boşuna bekleyip sonraki
  partiye geçiyor. Yani toplu gönderim hızlandırmıyor, **kilitliyor**.
- **Çözüm:** `HAYALET_PARTI` varsayılanı **1** yapıldı — her prompt ayrı
  gönderilir. Ayrıca tek üretim tavanı gerçekçi tutuldu
  (`HAYALET_GORSEL_TAVAN`=240 sn, `HAYALET_VIDEO_TAVAN`=900 sn).
- **Ölçüm (canlı):** 3/3 başarılı, **görsel başına 30 saniye**.
  183 görsel ≈ **1.5 saat** (eski haliyle ~190 saat sürerdi).
- **Toplu gönderim tekrar denendi (22 Ağu, çıktı türü doğruyken):**
  5 prompt tek mesajda → **2 dakikada 0 görsel**; aynı sürede tekli modda
  ~4 görsel indi. Ajan toplu promptu kabul ediyor ama işlemesi çok yavaş.
  Karar: tekli mod kalıyor.

### 16) "Görsel" seçtim ama VİDEO üretiyor
- **Yaşandı:** 21 Ağu 2026. Tüm cümleler görsel seçilmesine rağmen video çıktı.
- **Kök neden:** Çıktı türü de Flow ayarıdır — panelde `Image` / `Video`
  sekmeleri var ve **seçili olan kazanır**. Prompttaki
  "Generate one image:" ifadesi bunu **ezmez**. Ayar "Video"da kalmıştı.
- **Çözüm:** `flow_surucu.tur_ayarla()` her partiden önce türü ayarlıyor
  (görsel partisi → Image, video partisi → Video).
- **Doğrulandı:** canlı üretim → `.png`, 1376x768 (video değil).

### 14) Görseller/videolar 16:9 değil, dikey (9:16) çıkıyor
- **Yaşandı:** 21 Ağu 2026. Tüm çıktılar dikey geldi.
- **Kök neden:** Oran **prompta yazılmaz** — Flow projesinin kendi ayarıdır
  ve varsayılanı 9:16 olabiliyor. Prompta "16:9" eklemek işe yaramaz.
- **Çözüm:** `flow_surucu.oran_ayarla()` her partiden önce oranı kontrol
  edip gerekirse düzeltiyor. Zaten doğruysa dokunmuyor.
  Değiştirmek için: `~/.hayalet/gizli.env` içine `HAYALET_ORAN=9:16`.
- **Tuzak:** Ayar çipine körlemesine tıklamak, panel **zaten açıksa onu
  kapatır**. Kod önce sekmenin görünür olup olmadığına bakıyor.
- **Doğrulandı:** canlı üretim → inen dosya 1280x720 (oran 1.778).

### 15) Chrome'a bağlanılıyor ama Flow oturumsuz — çerezler okunmuyor
- **Yaşandı:** 21 Ağu 2026. Kullanıcı defalarca giriş yaptı, her seferinde
  otomasyon oturumu göremedi ve çerezleri ezdi.
- **Kök neden:** Playwright macOS'ta Chrome'a `--use-mock-keychain` ve
  `--password-store=basic` bayraklarını **varsayılan olarak** ekler. Bunlar
  Chrome'un Keychain'deki çerez şifreleme anahtarına erişmesini engeller;
  çerezler diskte durur ama **çözülemez**. Elle başlatılan Chrome'da sorun
  çıkmamasının sebebi budur.
- **Çözüm:** `ignore_default_args=["--use-mock-keychain",
  "--password-store=basic"]`.
- **Yan sonuç:** Bu bayraklar kalkınca, gerçek Chrome profilini kopyalayarak
  oturum taşımak da **çalışır hale geldi** (önce çalışmıyordu — sebebi aynı
  bayraklardı). `rsync` ile profil kopyalanıp 18 oturum çerezi taşındı ve
  Flow açıldı. Günlük Chrome'a hiç dokunulmadı.

### 13) Flow "tanıtım sayfası" açılıyor — oturum yok
- **Belirti:** Proje adresi doğru ama sayfada "Try in Google Flow",
  "Pricing" yazıyor; prompt kutusu yok.
- **Kök neden:** Hayalet'in izole Chrome profilinde Google oturumu açılmamış.
- **Çözüm:** `bash hayalet/chrome_baslat.sh` ile açılan pencerede **Flow
  aboneliği olan hesapla giriş yap**. Bir kez yeterli; oturum profilde kalır.
- ⚠ **Profil kopyalayarak oturum TAŞINMAZ** (21 Ağu 2026'da denendi ve
  ölçüldü). macOS'ta çerez anahtarı Keychain'de ve uygulamaya bağlı;
  `Local State` dahil kopyalansa bile Flow oturumsuz açılıyor.
- **Gerçek profilini kullanmak istersen** (ör. "Curtis"), `~/.hayalet/gizli.env`:
  ```
  HAYALET_CHROME_ANA_DIZIN=/Users/<sen>/Library/Application Support/Google/Chrome
  HAYALET_CHROME_PROFIL_ADI=Profile 48
  ```
  ⚠ Bu yolda **günlük Chrome'un tamamen kapalı olmalı** — Chrome aynı veri
  dizinini iki süreçle açamaz. Bot bunu kontrol edip net söyler. Günlük
  Chrome'unu açık tutmak istiyorsan izole profilde giriş yap (yukarısı).

### 12) "Flow acildi ama PROMPT KUTUSU bulunamadi"
- **Kök neden:** Prompt kutusu Flow'un giriş sayfasında değil, bir
  **projenin içinde** bulunur. Artık Chrome'u Playwright başlattığı için
  taze sekme giriş sayfasına düşer.
- **Çözüm:** Proje adresini sabitle — bir kez:
  ```bash
  # Flow'da projeyi aç, adres çubuğundaki .../flow/project/<uuid> adresini kopyala
  echo "HAYALET_FLOW_URL=https://labs.google/fx/tools/flow/project/<uuid>" >> ~/.hayalet/gizli.env
  ```
  Sonra botu yeniden başlat. Bot bunu doğrulayıp bulamazsa 15 dakika
  beklemek yerine hemen bu talimatı yazar.

### 10) `Browser.setDownloadBehavior: Browser context management is not supported`
- **Yaşandı:** 21 Ağu 2026. Her prompt bu hatayla düştü, hiçbir görsel
  üretilmedi. Chrome 151.0.7922.170 + Playwright 1.60.0.
- **Kök neden:** Playwright'ın `connect_over_cdp` çağrısı bağlanırken
  `Browser.setDownloadBehavior` gönderir; Chrome 151 bunu artık reddediyor.
  Playwright 1.60 **en yeni sürüm** — güncellemek çözmüyor.
- **Çözüm:** Artık çalışan Chrome'a bağlanmak yerine **Playwright Chrome'u
  kendisi başlatıyor** (`launch_persistent_context(channel="chrome")`).
  Chrome 151'de çalıştığı ölçüldü. Aynı kalıcı profil kullanıldığı için
  Flow oturumu korunur. CDP yolu önce yine denenir (eski Chrome'larda
  çalışır), olmazsa bu yola düşer.
- **Yan etki:** O profille açık bir Chrome varsa **kapatılıp yeniden
  açılır** (yalnızca Hayalet profilini kullanan pencere; günlük Chrome'una
  dokunulmaz). Giriş profilde durduğu için oturum kaybolmaz.

### 11) Hata mesajları Telegram'da link/italik olup okunamıyor
- **Yaşandı:** 21 Ağu 2026, yukarıdaki hatanın raporunda.
- **Kök neden:** Özet `parse_mode="Markdown"` ile gönderiliyordu; hata
  metnindeki `gorsel[4]` link, `chrome_baslat.sh` içindeki `_` italik
  sanıldı ve mesaj karmakarışık göründü.
- **Çözüm:** Başlık Markdown, **ayrıntı ayrı ve düz metin** olarak
  gönderiliyor. Ayrıca aynı nedenden düşen satırlar gruplanıyor
  (20 satırlık tekrar yerine tek satır + numaralar).

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
