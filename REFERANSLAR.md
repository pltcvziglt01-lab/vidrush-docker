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
