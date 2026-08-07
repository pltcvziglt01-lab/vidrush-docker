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
sahne_sn 6 | kelime 15 | footage_pct 92 (motorun en yükseği)
overlay yok | altyazı yok | motion sinematik | mag films_n_photography
tempo "cift-modlu"
```

`tempo: cift-modlu` plan promptunu değiştirir: kısa 6-11 / orta 12-20 / uzun 34-50
kelime sınıfları, aynı sınıf üç kez üst üste gelmez. Diğer 3 edit stili eski dar bant
davranışını korur.

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

## Magnific maliyeti (30 dk video)

Bu stilde Magnific en küçük kalem, çünkü sahnelerin %92'si video ve Magnific yalnızca
görsel büyütüyor.

| Kalem | Adet | Tutar |
|---|---|---|
| Footage klip | ~258 | $0 |
| AI görsel (footage bulunamayan) | ~22 | ~$1.06 |
| Magnific 2K (`hd=true` + kapak) | ~12 | ~$0.96 |
| Magnific 4K alternatifi | ~12 | ~$1.90 |

Abonelik karşılaştırması: Pro $39/ay = 2.500 token, etkin ~$0.18-0.20/büyütme →
ayda ~200 büyütme ≈ 16 video. Ayda 16 videonun altında API pay-per-use daha ucuz.

## Açık kalanlar

- **OpenAI bakiyesi bitti** → şu an hiç video üretilemez. Gemini anahtarı var ama boş
  yanıt dönüyor (fatura açık değil), yani yedek yok.
- **Pexels + Pixabay anahtarı yok** (ikisi de ücretsiz). Footage tek kaynaktan geliyor;
  klip başına 26 sn, 30 dk video için 4 paralel ile ~30 dk sadece footage indirme.
  `GORSEL_PARALEL=8` bunu yarıya indirir (footage ağ-bağımlı, API limitine takılmaz).
- Vision dağılım analizi (kamera açısı/konu oranları) bakiye gelince çalıştırılacak:
  `~/Desktop/belgesel-referans/belgesel_vision.py`
