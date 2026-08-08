# Referans #12 — @ImpossibleTravel38 (4K seyahat belgeseli), 5 Ağu 2026

**Yöntem:** en çok izlenen 10 video 480p indirildi, ffmpeg sahne-kesme ile **2147 çekim**
sınırı çıkarıldı, video başına ~26 ekran görüntüsü alındı (**260 kare**).

Betik: `~/Desktop/belgesel-referans/belgesel_olc.py`
Kareler: `~/Desktop/belgesel-referans/kare/<video_id>/`

## Çekim süresi (ekranda kalma)

| Ölçü | Değer |
|---|---|
| Medyan | **6.5 sn** |
| Ortalama | 12.5 sn |
| p10 / p25 / p75 / p90 | 1.7 / 3.2 / 13.3 / 28.1 sn |
| 4 sn altı | %32 |
| 4-8 sn | %26 |
| 8-12 sn | %14 |
| 12 sn üstü | %29 |

**Ritim ÇİFT MODLU.** Sabit kesme süresi yok: üçte biri 4 sn'den kısa sert vuruş,
üçte biri 12 sn'den uzun duran plan. Motorun dar kelime bandı (kelime..kelime+3) tüm
sahneleri eşitliyordu — belgeselde metronom hissi veriyordu.

## Video başına dağılım

| Video | Uzunluk | Çekim | Ortalama | Medyan | <4sn | >12sn |
|---|---|---|---|---|---|---|
| 3HZHJ20UfYs (Bermuda, 1.4M) | 31.1 dk | 147 | 12.7 sn | 7.5 sn | %24 | %33 |
| 5Qus-zHdl7M (Kiribati) | 58.4 dk | 469 | 7.5 sn | 4.5 sn | %41 | %18 |
| DIA-QCHzMkM (Marshall) | 68.1 dk | 405 | 10.1 sn | 6.2 sn | %37 | %26 |
| HS-8tBK-vto (Vanuatu) | 36.9 dk | 145 | 15.2 sn | 9.7 sn | %21 | %40 |
| QS4A_uN1R3I (Palau) | 30.7 dk | 56 | 32.9 sn | 3.8 sn | %54 | %25 |
| RAwwd_Yew0c (Azores) | 57.8 dk | 349 | 9.9 sn | 7.1 sn | %29 | %22 |
| Vg6H3Y5QH94 (Maupiti) | 32.0 dk | 83 | 23.1 sn | 8.2 sn | %27 | %39 |
| aSDhtruJBlI (Tristan, 689K) | 56.3 dk | 273 | 12.4 sn | 7.1 sn | %26 | %34 |
| crP5CM9Q6yQ (Falkland) | 36.0 dk | 99 | 21.8 sn | 7.7 sn | %31 | %41 |
| dUNZwicJr7Q (Socotra) | 38.9 dk | 121 | 19.2 sn | 11.0 sn | %21 | %47 |

## Görüntü kimliği

Parlaklık **116**, doygunluk **40**, kontrast **50** — animasyon referansından (162/52/51)
belirgin daha loş ve az doygun.

Kareler elle incelendi (vision analizi OpenAI bakiyesi bittiği için çalışmadı):

- **Tamamı gerçek kamera görüntüsü.** AI illüstrasyon yok. Drone hava çekimi + yer
  seviyesi elde çekim + makro detay + arşiv fotoğrafı.
- Konu döngüsü: kıyı/resif hava çekimi → liman/yerleşim → yerel insanlar (dans, iş) →
  makro detay (kum, kabuk, el, alet) → hava/fırtına → arşiv fotoğraf
- Sağ üstte kalıcı dairesel kanal filigranı
- **Gömülü altyazı yok**, alt-band konum yazısı yok, harita grafiği yok
- Kaynak klipler farklı en-boy oranlarından geliyor; bazı planlarda hafif letterbox

## Motora eklenenler

**Yeni edit stili `seyahat-belgeseli` — "Seyahat Belgeseli (4K)"**

```
sahne_sn 12.5 | footage_pct 92 (motorun en yükseği)
overlay yok | altyazı yok | motion sinematik | mag films_n_photography
tempo "cift-modlu"
```

`sahne_sn` = ölçülen **ortalama** çekim (12.5 sn), medyan (6.5 sn) değil: sahne sayısı
`hedef_sure / sahne_sn` ile bulunduğu için burada ortalama doğru ölçü. Medyanı çift-modlu
bant dağılımı 6-7 sn'ye getiriyor.

`tempo: cift-modlu` plan promptunu değiştirir. Bantlar ölçülen dağılımdan türetilir ve
**ağırlıklı ortalaması 1.0 × sahne_sn** olur (bu şart olmadan video hedeflenen süreden
uzun çıkar — ilk yazımda %23 aşıyordu):

| Bant | Pay | Çarpan | edge-tts'te (178 wpm) |
|---|---|---|---|
| ÇOK KISA | %32 | 0.20 | ~7 kelime |
| KISA | %26 | 0.48 | ~18 kelime |
| ORTA | %14 | 0.80 | ~30 kelime |
| UZUN | %29 | 2.40 | ~89 kelime |

`.32×0.20 + .26×0.48 + .14×0.80 + .29×2.40 = 1.00` ✓

Aynı sınıf üç kez üst üste gelmez, iki ÇOK KISA yan yana konmaz. Diğer 3 edit stili eski
dar bant davranışını korur (canlı testle doğrulandı).

## Bu stilin ortaya çıkardığı iki tıkanıklık

**1. Footage hiç inmiyordu.** `footage_getir` YouTube'u yalnızca `YT_COOKIES` dosyası
varsa deniyordu. Sunucuda cookie yok, `PEXELS_KEY` boş, Pixabay anahtarı yok — yani
%92 footage'lı bir stil tamamen AI görsele düşer, hem stil bozulur hem maliyet ~10 kat
artardı. `player_client=android_vr` cookie gerektirmediği için koşul kaldırıldı.
Canlı test: CC video bulundu → 14 sn 1920×1012 h264, 26 saniyede.

**2. Telif riski.** `youtube_ara` lisans filtresi yapmıyordu; standart YouTube lisanslı
bir video videoya girip kanala ihtar getirebilirdi. Artık `sp=EgIwAQ%3D%3D` ile sadece
Creative Commons aranıyor **ve** `_lisans_cc_mi()` indirmeden önce her adayın lisansını
tek tek doğruluyor. Test: filtreli arama CC=True, filtresiz CC=False.

Not: lisans okuması `player_client=android_vr` ZORUNLU. Düz istemci
"Requested format is not available" veriyor, o zaman lisans okunamıyor ve güvenli taraf
seçildiği için her aday atlanıyordu — footage komple durmuş olurdu.

## Magnific maliyeti

Bu stilde Magnific en küçük kalem, çünkü sahnelerin %92'si video ve Magnific yalnızca
görsel büyütüyor. 30 dk video = 144 sahne → ~12 AI görsel → `hd=true` işaretlenenler +
kapak ≈ **7 büyütme ≈ $0.56** (2K). 4K yapılırsa ~$1.12.

Abonelik karşılaştırması: Pro $39/ay = 2.500 token, etkin ~$0.18-0.20/büyütme →
ayda ~200 büyütme ≈ **28 video**. Ayda 28 videonun altında API pay-per-use daha ucuz.

Tam maliyet dökümü için aşağıdaki tabloya bak.

## Açık kalanlar

- **OpenAI bakiyesi bitti** → şu an hiç video üretilemez. Gemini anahtarı var ama boş
  yanıt dönüyor (fatura açık değil), yani yedek yok.
- **Pexels + Pixabay anahtarı yok** (ikisi de ücretsiz). Footage tek kaynaktan geliyor;
  klip başına 26 sn, 30 dk video için (132 klip) 4 paralel ile ~14 dk sadece footage indirme.
  `GORSEL_PARALEL=8` bunu yarıya indirir (footage ağ-bağımlı, API limitine takılmaz).
- Vision dağılım analizi (kamera açısı/konu oranları) bakiye gelince çalıştırılacak:
  `~/Desktop/belgesel-referans/belgesel_vision.py`

## 30 dakikalık video maliyeti (kodun gerçek değerleriyle)

Fiyatlar: `gpt-image-2` $0.048 · `gpt-image-1-mini` $0.013 · `gpt-4o-mini-tts` $0.015/dk ·
`whisper-1` $0.006/dk · Magnific 2K ~$0.08. KDV %20 (yurtdışı dijital hizmet).

| Kalem | Seyahat Belgeseli (144 sahne) | Animasyon (150 sahne) |
|---|---|---|
| AI görsel | $0.58 (12 ad, gpt-image-2) | $1.95 (150 ad, mini) |
| Kapak | $0.05 | $0.01 |
| Magnific | $0.56 (7 büyütme) — **bugün $0, aşağıya bak** | $0 (profilde kapalı) |
| Footage | $0 (132 klip CC+stok) | — |
| Planlama + analiz | $0.08 | $0.10 |
| Seslendirme (OpenAI) | $0.45 | $0.45 |
| Whisper hizalama | $0.18 | $0.18 |
| **Toplam** | **$1.89** | **$2.69** |
| **+ KDV** | **$2.27** | **$3.23** |
| edge-tts ile (KDV dahil) | $1.52 | $2.48 |

> **Magnific bugün çalışmıyor (5 Ağu 2026 tespiti).** Üç ayrı uç test edildi:
> upscaler `api.magnific.com` → 502 + HTML hata sayfası (adres ölü, Magnific Freepik'e
> katıldı); doğru adres `api.freepik.com` → 502 `"Error consuming credits"`; AI görsel
> üretimi (Mystic/Flux) → 422 `"Account not found"`; stok indirme → 422 `"Tool not found"`.
> **Yalnızca stok ARAMA çalışıyor** (50 sonuç, 4K premium klipler görünüyor).
> Yani bugüne kadar üretilen videolarda hiçbir görsel büyütülmemiş ve Magnific satırı
> gerçekte $0. Kod artık doğru adrese gidiyor; kredi yüklenince çalışacak.

**Neden belgesel daha ucuz:** sahnelerin %92'si footage, yani $0. Animasyonda her sahne
AI görsel. Belgesel pahalı modeli (`gpt-image-2`) kullanmasına rağmen 12 görsel çiziyor,
animasyon ucuz modelle 150 görsel çiziyor.

`sahne_sn = 12.5` (ölçülen ORTALAMA çekim) sahne sayısını belirler; çift-modlu bant
dağılımı medyanı 6-7 sn'ye getirir. Doğrulama: ağırlıklı ortalama 12.4 sn / hedef 12.5 sn,
30 dk hedef → 29.9 dk çıktı, sahnelerin %58'i 8 sn altı (referans: %58).

**Süre (para değil, ama darboğaz):** footage 132 klip × 26 sn ÷ 4 paralel ≈ 14 dk;
hızlı ffmpeg motoru 30 dk videoyu ~12 dk'da render eder (Remotion ~4 saat).
`GORSEL_PARALEL=8` footage aşamasını yarıya indirir.
