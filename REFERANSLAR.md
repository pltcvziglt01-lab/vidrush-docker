# Referans Kayıt Defteri

Her referans video/kanal, sisteme **somut bir kural** olarak işlendi. Yeni referans geldiğinde
buraya bir satır eklenir. Amaç: öğrenilen dersin kaybolmaması ve neden öyle kodlandığının belli olması.

> **Nasıl kullanılır:** Yeni referans geldiğinde → kare kare analiz → hangi kuralı ürettiği buraya
> yazılır → `pipeline.py`'de ilgili sabite işlenir → **gerçek videoyla** doğrulanır.

---

## 1. "The Psychology of People Who Would Rather Fix Than Replace" (8 dk)
**Ne öğretti:** Elle çizilmiş editorial-karikatür estetiği + **zengin ortamlar**.
- Mürekkep kontur + cel gölge + kâğıt dokusu, soluk vintage palet (oker/adaçayı/tozlu mavi)
- Ortamlar dolu: alet panosu, dolu raflar, kavanozlar, kutular, tek dramatik ışık kaynağı
- Karakter küçük-orta ölçek, **ortam baskın**
- Tempo ~3.5 sn/görsel

**Kod karşılığı:** `ANIM_STIL` (Anlatı stili), `ANIM_CERCEVE`, `ANIM_SOZLESME` 6-slotlu sahne
sözleşmesi + yasak kelime listesi (*empty/plain background, minimalist, negative space*).

## 2. "When Did Ancient Humans First Start Eating Salt" (18.5 dk)
**Ne öğretti:** Eğitici explainer — **beyaz diyagram kartları** + canlı düz renkler.
- Kalın siyah kontur, düz doygun renk, doku YOK
- İki kare tipi dönüşümlü: renkli sahne ↔ **tam ekran beyaz kart** (~%33)
- Kart arketipleri: dev başlık, kırmızı X'li red, terazi karşılaştırma, oklu şema
- Yazı **istenen** bir tasarım öğesi

**Kod karşılığı:** `EXP_STIL`, `EXP_SOZLESME`. **Yazı bütçesi** (maks 2 satır/3 kelime/14 karakter,
sadece A-Z 0-9) — `"300,000"` ve `"Na+"` yasak, `"300 000 YEARS"` / `"SODIUM"` zorunlu.
Bu kural sayesinde üretilen yazılar %100 doğru çıktı.

## 3. "You Wake Up 100,000 Years Ago... Now What?" (12 dk)
**Ne öğretti:** **Sade beyaz stickman + zengin boyalı sinematik dünya** kontrastı.
- "Yağlı boya tablonun üstüne yapıştırılmış kâğıt kesik" mantığı
- **Işık üstünlüğü**: sahne ışığı sadece dünyaya düşer, figür her koşulda düz kalır
- 8 çekim tipi + ses efekti yazıları ("THUMP", "POOF") + infografik/timeline

**Kod karşılığı:** `HIK_STIL`, `HIK_CERCEVE`, `HIK_SOZLESME`.
⚠️ **Hata dersi:** Stil bloğuna *"pure flat white"* yazmak kullanıcının turuncu karakteriyle
çatışıp beyaz↔turuncu salınımı yaptı. **Stil asla renk dayatmaz** — renk daima karakter künyesinden.

## 4. Araç bakım kanalı (4 kare)
**Ne öğretti:** **Karelerin çoğunda karakter YOK.**
- Patlatılmış teknik şema · yazı kartı · makro detay · (sadece 1'inde karakter)
- Ritim: şema → yazı → sahne → makro

**Kod karşılığı:** `KARE_CESITLILIGI` + yeni çekim tipleri **I OBJECT MACRO, J HANDS ONLY,
K MAP ROUTE, G INFOGRAPHIC** (hepsi karaktersiz).
⚠️ **En önemli ders:** Prompt ile *"%40 karaktersiz olsun"* demek **işe yaramadı** (LLM 1/7 üretti).
Çözüm: `sahne_tipi_atamasi()` ile tip **kodla atanır** → 3/7 garanti, arka arkaya gelmez.

## 5. "Mexican Cartel Rank | Stickman Animation" (The Simple Explainer)
**Ne öğretti:** Anlatım kareleri — nesne/el/harita + duygu.
- **Sadece eller** yakın planı (zarf uzatan iki el, bilekten kırpılmış)
- **Etiketli harita + rota** (şehir noktaları, kesikli çizgi, üstünde araç)
- **İç ses**: karakterin başında havada uçuşan kısa kelimeler ("GONE…", "ALONE…")
- Karakter gerçek bir mekânda **iş yaparken** (yatakta para sayarken), etrafında objeler

**Kod karşılığı:** `HANDS ONLY`, `MAP ROUTE`, `INNER VOICE` tipleri + `DESTEK_PLANLAYICI`
(her kare anlatılanı GÖSTEREN somut bir araç içermeli, karakter onunla etkileşmeli).

## 6. "Aussie Money With Bruce" — $12 Million Win (7 kare)
**Ne öğretti:** Renkli **kurşun kalem** medyumu + **imza aksesuar** kimliği + sıkı renk paleti.
- Medyum: renkli kalem tarama dokusu, kâğıt grenli, yumuşak; vektör/dijital DEĞİL
- Karakter: beyaz stickman ama **yeşil-altın çizgili kravat** = kimlik çapası.
  Yüz hatları neredeyse yok; ayırt edici olan **aksesuar**
- Yan karakterler aynı stickman ama **kıyafet/saç** ile ayrılıyor (mavi gömlek, at kuyruğu, topuz)
- Duygu tamamen **kaşlarda**: endişeli eğik kaş, öfkeli çatık kaş, üzgün düşük ağız — her karede net
- Ortamlar çok spesifik ve "yaşanmış": vardiya panolu mola odası, hi-vis montlar, limon ağaçlı mutfak
  penceresi, tüplü TV + çiçekli kanepe, kırmızı ipli mantar pano
- Mesaj taşıyan objeler: tutulan tabela ("WON $12,000,000"), kupa üstünde "FOCUS PLAN FREEDOM"
- **Renkler bütün karelerde aynı dar aile**: krem kâğıt, adaçayı, altın, kiremit, tozlu mavi

**Kod karşılığı:** `PALETLER["aussie-kalem"]` + `palet_prompt()` — renk artık **kelimeyle tarif
edilmiyor, kesin HEX olarak** prompta giriyor (`palet_olc` dersinin genele yayılmışı).
⚠️ Palet **dünyayı** yönetir; karakterin kilitli renkleri her zaman önceliklidir — yoksa
3. referanstaki beyaz↔turuncu salınımı geri gelir.

## 7-10. Toplu kare analizi — 4 kanal, 567 kare (1 Ağu 2026)

20 video yt-dlp ile indirildi, **sahne-değişim tespitiyle** kare çıkarıldı (sabit aralık değil —
her kare farklı bir kompozisyon). Ham kareler + tam bulgular:
`~/Desktop/stickman-referans/` · `BULGULAR.md`

| # | Kanal | Abone | Kare |
|---|---|---|---|
| 7 | The Paint Explainer | 1.96M | 140 |
| 8 | Serious History | 808K | 140 |
| 9 | Aussie Money With Bruce | 2K | 140 |
| 10 | The Simple Explainer | 88 | 140 |

### 🔑 En değerli bulgu: VERİ KARTI
Bruce'un 28 karesinin ~24'ünde tutulan tabela / laptop ekranı / fiyat etiketi var ve üstünde
**anlatılan cümlenin tam sayısı** yazılı (`SERVICE $3,000 A YEAR`, `50% UNUSED SUBS`,
`7.5% vs 13%+`). Karakter hiçbir zaman "sadece anlatmıyor" — sayıyı **gösteriyor**.

**Kod karşılığı:** `VERI_KARTI_PLAN` (planlayıcı: somut sayı içeren her cümlede o sayıyı
taşıyan fiziksel bir yüzey adı ver) + `VERI_KARTI_GORSEL` (görsel: yüzeyi büyük ve okunur çiz,
karakterin **karşı tarafına** koy → iki sütun kompozisyon).
⚠️ "Sayı yoksa uydurma" kuralı açıkça yazıldı — yoksa model her kareye sahte rakam basar.

### İki bağımsız kanalda doğrulanan: MEKÂN SÜREKLİLİĞİ
Paint Explainer bir bölüm boyunca aynı geniş arka planı, Simple Explainer poligraf masasını
8+ karede yeniden kullanıyor. Tesadüf değil, kural.
**Kod karşılığı:** `MEKAN_SUREKLILIGI` — sahneler 2-4'lük aynı-mekân öbeklerine gruplanır,
sadece açı ve aksiyon değişir.

### İki ZIT doğru: arka plan yoğunluğu
- Paint Explainer (1.96M): karelerin çoğu **bomboş beyaz zeminde tek öğe**
- Bruce + Serious History: **tıka basa dolu** mekânlar

İkisi de çalışıyor → "her yer dolsun" **evrensel kural değil, kanal kararı.**
**Kod karşılığı:** `ARKA_PLANLAR` (9 seçenek, sade/orta/zengin). `sade` seçilirse stilin
yoğunluk dayatmasını açıkça **EZER** — palet öncelik kuralının aynı deseni.

### Yeni çekim tipleri (2+ kanalda doğrulandı)
`N SCREEN READOUT` (ekran/veri arayüzü: EKG çizgisi + `HR: 185 bpm`, çubuk grafik) ·
`O OVERHEAD FLATLAY` (masaya tepeden bakan kare: eller, belgeler, kahve)

### Marka güvenliği
Bruce gerçek logolar kullanıyor (Netflix, Disney+, Stan). **Biz kullanmayacağız.**
**Kod karşılığı:** `MARKA_YASAK` — jenerik karşılık üretilir.

### Kaydedilen ama HENÜZ uygulanmayanlar
- **Kalıcı bölüm bandı** (Paint Explainer: `PRECAMBRIAN` → `CAMBRIAN` üst şeridi).
  Serious History'de YOK → evrensel değil, stil başına seçenek olmalı.
- **Konuşma balonu** ve **düşünce balonu içinde mini sahne** (Simple Explainer)
- **Zaman kartı** (`Three weeks later`)
- **Gerçek arşiv fotoğrafı** — Pexels/Pixabay anahtarı gelince yapılabilir

### ⚠️ Dürüst sınır
Serious History **gerçek kare-kare animasyon** yapıyor (hareket bulanıklığı, ara kareler).
Durağan görselle taklit edilemez. Oradan alınan ders animasyon değil, TASARIM
(ayrıntılı kafa + sade gövde, boş nefes karesi, vuruş başına renk sıçraması).

## 11. ThriftyHazel (6.4K abone, 2 aylık) — 10 video, 216 kare

`@thriftyhazel` · 24 video · 379K izlenme · **2 Haz 2026'da açılmış**. Tasarruf/frugal yaşam,
ABD yaşlı kitlesi. Formül: **"N Şey" + yaş işareti ("at 52") + birinci tekil + büyükanne nostaljisi.**

### Diğer 10 referanstan TEMEL farkı: karakter çöp adam DEĞİL
Gerçekçi-karikatür bir insan — 50'li yaşlarda kadın, yuvarlak gözlük, adaçayı hırka.
Sıcak hikâye kitabı illüstrasyonu: ince mürekkep çizgi + kuru boya + suluboya yıkama.

### Bulgular

**A. İKİ REGISTER, DÖNÜŞÜMLÜ**
- **Sunucu karesi**: anlatıcı bomboş soluk zeminde, mekân YOK, kameraya konuşuyor
- **Dünya karesi**: tıka basa döşenmiş oda — duvar kâğıdı, çiçekli perde, saksı, duvar saati
İkisi asla karışmıyor. Bizim tek-modlu çerçevemizden farklı.

**B. GERİ SAYIM ROZETİ**
Köşede kocaman `11` `10` `9` `8` `7`. Liste videolarının omurgası, 10 videoda da var.

**C. BÖLÜM KARTI**
Koyu kahve zeminde süslü çerçeve + zarif serif başlık: `THE RULES IN YOUR HEAD`,
`THE RULES FOR YOUR WALLET`. Paint Explainer'ın üst bandının tam ekran versiyonu.

**D. GEÇMİŞ/BUGÜN RENK KODLAMASI**
Geçmiş sahneler **soluk sepya-kahve**, bugün sahneleri **tam sıcak renk**.
İzleyici hangi döneme baktığını renkten anlıyor. Çok ucuz, çok etkili.

**E. BİRİNCİ TEKİL ELLER (POV)**
Anlatıcının kendi elleri karenin yakın kenarından giriyor — teneke açıyor, fatura yazıyor.
`J HANDS ONLY`den farklı: bu "benim gözümden".

**F. ✅ MARKA YASAĞIMIZI DOĞRULUYOR**
Klarna/Afterpay yerine **uydurma** `FLEXIPAY: MANAGE YOUR PLANS` markası çizilmiş.
Bir gün önce eklediğim `MARKA_YASAK` kuralının bağımsız doğrulaması.

**G. ✅ VERİ KARTINI DOĞRULUYOR**
El yazısı defter: `Oct 1956 $5.00 / Nov 1956 $10.00 / Dec 1956 $20.00` — modern telefonun yanında.
Eski-yeni karşılaştırması TEK karede.

**Kod karşılığı:** yeni 5. stil `ani-defteri` (`ANI_STIL/CERCEVE/SOZLESME`) + `ani-defteri` paleti
(#F5EDDC krem, #8FA68E adaçayı, #A9743F meşe, #E8B65A lamba, #C98B7E gül kurusu, #4A3728 kahve)
+ `COUNTDOWN BADGE` ve `CHAPTER CARD` cihazları (ikisi de **koşullu** — liste değilse rakam yok).

---

---

## Sistemin kendi kendine öğrendiği kurallar (referanslardan bağımsız)

| Ders | Neden |
|---|---|
| **Kirli referansı sahnelere gönderme** | Referanstaki fincan/arka plan her kareye kopyalanıyordu — prompt değil PİKSEL sorunu. Temiz kanon üret, dondur. |
| **Prompt yetmiyorsa kodla zorla** | LLM oran/kota kurallarını uygulamıyor. Tip ataması gibi şeyler deterministik olmalı. |
| **Stil ile künye çatışmamalı** | İki emir çelişince model sahneler arası salınıyor. |
| **Yasaklı şeyi adlandırma** | "pembe olmasın" demek yerine "tam olarak #E8822A" de. |
| **Gerçek videoyla doğrula** | Statik denetim 3 kez gözden kaçırdı; canlı test hepsini yakaladı. |

---

## Yeni referans gönderirken en faydalısı

1. **Kanal linki** → tempo, süre, format ölçebilirim (kare değişim hızı, video uzunluğu)
2. **3-5 farklı ANDAN ekran görüntüsü** → tek kare değil; **ritmi** görmem lazım
   (özellikle: karaktersiz kareler, yazı/grafik kareleri, duygusal anlar)
3. **Video dosyası** → en iyisi; kare kare + tempo + ses analizi yapabilirim
4. Beğendiğin/beğenmediğin noktayı söyle → "şu kare iyi, şu kötü" en hızlı düzeltmeyi sağlar

## 12. ImpossibleTravel (4K seyahat belgeseli) — 10 video, 2147 çekim, 260 kare

`@ImpossibleTravel38` · 20 video · "How People Live in X" kalıbı · 30-70 dk · en iyisi 1.4M.
Tam ölçüm: [OLCUM_BELGESEL.md](OLCUM_BELGESEL.md)

### Diğer 11 referanstan TEMEL farkı: hiç AI görsel yok
Kareler tamamen gerçek kamera görüntüsü — drone hava çekimi + yer seviyesi elde çekim +
makro detay + arşiv fotoğrafı. Bu bir GÖRÜNTÜ DERLEMESİ belgeseli.

### Ürettiği kurallar

**A. RİTİM ÇİFT MODLU** — medyan çekim 6.5 sn ama %32'si 4 sn altı, %29'u 12 sn üstü.
Dar kelime bandı bunu öldürüyordu → `tempo: "cift-modlu"` bayrağı eklendi
(kısa 6-11 / orta 12-20 / uzun 34-50 kelime, aynı sınıf 3 kez üst üste gelmez).

**B. footage_pct 92** — motorun en yükseği. AI görsel sadece görüntü bulunamayan sahneler
(tarihi an, soyut kavram) için.

**C. LOŞ VE AZ DOYGUN** — parlaklık 116, doygunluk 40, kontrast 50. Animasyon
referansı (162/52/51) ile karıştırılmamalı.

**D. YAZI YOK** — gömülü altyazı yok, alt-band konum yazısı yok, harita grafiği yok.
Sadece sağ üstte kalıcı kanal filigranı.

**E. KONU DÖNGÜSÜ** — kıyı/resif hava çekimi → liman/yerleşim → yerel insanlar →
makro detay → hava/fırtına → arşiv.

### Yan kazanç: iki tıkanıklık kapandı
`footage_getir` YouTube'u cookie olmadan hiç denemiyordu (footage komple ölüydü) ve
`youtube_ara` lisans filtresi yapmıyordu (telif ihtarı riski). İkisi de düzeltildi;
artık sadece Creative Commons aranıyor ve indirmeden önce lisans tek tek doğrulanıyor.

## 13. Neu — "The Broken Economics of Oil Tankers" (edit paketi referansı)

`youtube.com/watch?v=uMZ9CkmzYMc` · 9.5 dk · 62K izlenme.
Kullanıcının "after effects kalitesinde tam paket edit" olarak gösterdiği referans.

### Diğer 12 referanstan TEMEL farkı: kesme yok, sürekli animasyon var
ffmpeg sahne-kesme eşik 0.28'de **571 saniyede sadece 2 sert kesme** buldu. Video kesmeyle
değil animasyonla ilerliyor. 143 karede zemin analizi:

| Zemin | Oran |
|---|---|
| Beyaz tuval (grafik/etiket/serif metin) | **%41** |
| Tam kare footage | %43 |
| Karışık / kısmi beyaz | %16 |

Yani stilin yarısı bizde hiç olmayan bir şeydi: **beyaz zeminde veri grafiği.**

### Ürettiği kurallar

**A. GEÇİŞ DEĞİL, KATMAN** — bu bir geçiş meselesi değil. Yeni bir anlatım katmanı gerekti:
`EditPaketi.tsx`, 5 şablon (beyaz-tuval / ölçü / alıntı / metin / harita).

**B. İŞARETLEYİCİ** — sayılar sarı fosforlu kalemle işaretli, başlıklar turuncu.
Yazının arkasına soldan sağa büyüyen bant olarak çizildi (gerçek kalem hissi).

**C. ÖLÇÜ OKU** — nesnenin boyunu gösteren çizgi + iki uçta dik serif + ortada etiket
("375 METERS"). Çizgi soldan sağa çiziliyor, sonra etiket işaretleniyor.

**D. SERIF TİPOGRAFİ** — gövde metni serif, beyaz zeminde ortalı, satır satır açılıyor.

**E. YALITILMIŞ NESNE** — beyaz tuval sahnelerinde konu katalog gibi kesilip beyaza
oturtulmuş. Bu yüzden görsel promptuna "pure white background, product-catalogue
isolation" zorunlu eklendi; yoksa beyaz zemine tam kare fotoğraf konur ve stil olmaz.

### Bilinçli olarak YAPMADIĞIM şey
Referansta gerçek gazete/makale ekran görüntüleri var. Onun taklidini üretmek, olmayan bir
habere gerçek gibi görünen bir belge üretmek olur. Yerine `alinti` şablonu açıkça **alıntı
kartı** gibi durur ve kaynağı yazar; aynı görsel etkiyi verir, uydurma belge üretmez.
Plan promptu da açıkça "kaynak uydurma, senaryoda kaynak adı yoksa bu şablonu kullanma"
diyor ve her etiketteki sayının anlatım metninden gelmesini şart koşuyor.

### Motora eklenenler
- `EditPaketi.tsx` — 5 şablon, koordinatlar 0-1 oranı (çözünürlükten bağımsız)
- Yeni edit stili `veri-anlatisi` — "Veri Anlatısı (Neu)": sahne 9 sn, footage %45,
  grafik %41, `edit_paketi: True`
- Plan promptuna GRAPHIC LAYER kuralı (yalnızca `edit_paketi` stillerinde; diğer 4 stile
  sızmadığı testle doğrulandı)
- Beyaz-tuval sahnelerine zorunlu "pure white background" görsel promptu
- Hızlı ffmpeg motoru grafikli işi reddedip Remotion'a düşürüyor (ffmpeg'de karşılığı yok;
  yarım taklit iki motoru farklı gösterirdi)
- `@remotion/lottie` kuruldu: tasarımcının After Effects'te yaptığı animasyon (Lottie/
  Bodymovin dışa aktarımı) sahneye `ae` alanı ile birebir oynar

### #12 EK — BÖLÜM BAŞLIKLARI (7 Ağu 2026, kullanıcının gönderdiği 2 kare)

**İlk ölçümüm eksikti.** Video başına 26 kare (90 sn aralık) almıştım ve "gömülü yazı yok"
demiştim. Bölüm başlıkları videoda sadece 5-8 kez, bölüm geçişlerinde göründüğü için o
örnekleme onları kaçırmış. Kullanıcı iki ekran görüntüsüyle gösterdi.

Otomatik tespit denedim (parlak piksel + koyu kontur = yazı sezgisi, 2 sn'de bir kare,
2043 kare tarandı) — **işe yaramadı**, parlak su ve gökyüzünü yazı sanıyor, 6 güçlü adayın
altısı boş çıktı. Ölçüm kullanıcının gönderdiği iki kareden yapıldı.

**İKİ VARYANT var, aynı videoda ikisi de kullanılıyor:**

| | `ust` | `orta` |
|---|---|---|
| Konum | sol üst (x %3.2, y %4.4) | ortalı, y ~%55 |
| Yazı düzeni | Cümle düzeni | TAMAMI BÜYÜK HARF |
| Boyut | 46 px @1080p | 68 px @1080p |
| Kalınlık | 800 | 900 |
| Satır | tek satır (genişliğin ~%65'i) | 2-3 satır sarabilir |

Boyut karakter genişliğinden hesaplandı: referansta 50 karakterlik başlık tek satırda
genişliğin %65'ini kaplıyor → ~46 px Montserrat ExtraBold. Önce 52, sonra 58 denedim;
58'de yazı ikinci satıra taştı, referansta tek satır. 46 doğrusu.

**Hareket:** spring (damping 22, stiffness 95) ile aşağıdan süzülme + fade, harf aralığı
hafifçe oturuyor. 4.5 sn ekranda kalıp 0.7 sn'de sönüyor. Blur YOK — 1080p'de ucuz durur.

**Okunurluk:** parlak footage üzerinde beyaz yazı kayboluyordu → `orta` varyantta 3px
siyah kontur + iki katmanlı derin gölge.

### Bölüm bazlı anlatım
Referans düz bir sahne dizisi değil: 5-8 bölüme ayrılmış, her bölümün kendi başlığı ve
kendi anlatım yayı var. Motorda `bolumler: True` bayrağı 4 belgesel stiline eklendi;
plan promptu videoyu ~5 dakikada bir bölüme ayırıyor (40 dk → 8 bölüm, 30 dk → 6),
her bölüm kendi sorusunu açıp tek bir fikri geliştirip sonraki bölüme devrediyor.
Başlık sadece bölümün İLK sahnesine yazılıyor; üçte biri `orta`, gerisi `ust`.
