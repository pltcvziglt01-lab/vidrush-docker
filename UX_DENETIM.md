# BEDOSAHO AI — Arayüz denetimi ve yeniden yapılandırma planı
_11 Ağustos 2026 · canlı site http://185.23.17.240/ · kod `webapp/static/index.html` (1698 satır, tek dosya, vanilla JS)_

---

## 1. Mevcut ekran envanteri

Tek sayfa uygulaması, 7 `<section class="view">` bloğu, sol menüde **8 öğe**.

| # | Menü öğesi | DOM id | Ne yapıyor | Durum |
|---|---|---|---|---|
| 1 | Animasyon Stüdyosu | `view-studyo` (tur=animasyon) | Referans kare yükle → analiz → üret | **Açılış ekranı.** Zorunlu dosya yüklemesi ile başlıyor |
| 2 | Hikaye Stüdyosu | `view-studyo` (tur=hikaye) | Aynı ekran, `tur` parametresi farklı | Aynı DOM |
| 3 | Documentary | `view-studyo` (tur=documentary) | Aynı ekran, `tur` parametresi farklı | Aynı DOM |
| 4 | Yeni Video | `view-studio` | Eski elle-ayar paneli — 9 ayar grubu tek sayfada | Kodda "menüden kaldırıldı" notu var ama **menüde duruyor** |
| 5 | Videolarım | `view-videolar` | `localStorage`'daki iş id'lerini listeler | **Bu tarayıcıya bağlı** — başka cihazda boş |
| 6 | Edit Stilleri | `view-styles` | Stil listesi, teknik metinli | Salt okunur |
| 7 | Kaynaklar | `view-sources` | Footage kaynak listesi | **Yanlış bilgi içeriyor** (bkz. §8) |
| 8 | Krediler | `view-credits` | Entegrasyon/maliyet listesi | **Yanlış bilgi içeriyor** |

**Açılış deneyimi sorunu:** Siteye ilk giren kullanıcı "Animasyon Stüdyosu"na düşüyor ve ilk gördüğü şey **zorunlu referans kare yüklemesi**. Elinde dosya yoksa hiçbir şey yapamaz. Kabul kriterin "yeni kullanıcı 60 saniyede proje başlatabilmeli" — şu an başlatamıyor.

**Mobil:** 8 menü öğesi 2 kolonlu ızgarada yığılıyor ve 812px ekranın **~470px'ini (%58)** kaplıyor. İçerik katlamanın çok altında başlıyor.

---

## 2. Tekrarlanan özellikler

**Aynı DOM'u paylaşan 3 menü öğesi:** Animasyon / Hikaye / Documentary — hepsi `view-studyo`, tek fark `data-tur`. Üç ayrı ürün gibi sunuluyor, aslında **tek üretim akışının bir parametresi**.

**Dördüncü, ayrı ama örtüşen akış:** "Yeni Video" (`view-studio`) aynı işi elle ayarlarla yapıyor. Kodda 3 Ağustos'ta menüden kaldırıldığı yazılı ama menüde hâlâ var → kullanıcı aynı işi iki farklı yerden, iki farklı arayüzle yapabiliyor.

**Sonuç:** 8 menü öğesinin 4'ü tek işi tekrarlıyor. Bilgi mimarisi ürünü olduğundan 4 kat karmaşık gösteriyor.

**İkincil tekrar:** stil seçimi hem "Edit Stilleri" sayfasında (salt okunur) hem üretim formunda (seçilebilir) var; kullanıcı hangisinin gerçek olduğunu bilmiyor.

---

## 3. Yeni site haritası

```
Ana Sayfa                    son projeler + tek birincil eylem
Yeni Proje                   5 adımlı wizard  ← Animasyon/Hikâye/Belgesel BURADA tür
Projelerim                   proje kütüphanesi (sunucu tabanlı)
Videolar                     tamamlanmış çıktılar
Marka Kitleri                (eski "Kanal Profili")
Şablonlar                    görsel galeri (eski "Edit Stilleri")
Ayarlar
 ├─ Medya Kaynakları
 ├─ Ses Sağlayıcıları
 ├─ Entegrasyonlar           ← yt-dlp / Magnific / model isimleri YALNIZCA burada
 ├─ Kullanım ve Maliyet      ← eski "Krediler"
 └─ Sistem Durumu            ← /api/saglik burada gösterilir
```

8 öğe → **7 öğe**, ama tekrar sıfır. Mobilde alt navigasyonda 4 öğe: Ana Sayfa · Yeni Proje · Projelerim · Ayarlar.

---

## 4. Beş adımlı kullanıcı akışı

```
ADIM 1  Ne oluşturuyorsun?
        5 kart: Belgesel · Video Essay · Explainer · Hikâye · Animasyon
        Her kart: kısa açıklama + örnek kare + tahmini süre + kullanım alanı
        GÖSTERİLMEZ: model adı, footage oranı, sahne_sn
        ↓
ADIM 2  Konu ve içerik
        Giriş yöntemi (4 sekme): Konu ver · Senaryo yapıştır · URL ekle · Dosya yükle
        Alanlar: konu · hedef izleyici · dil · hedef süre · ton · opsiyonel kaynaklar
        [✓] Web'de araştır ve doğrula          ← VARSAYILAN AÇIK
        ↓
ADIM 3  Görsel yön
        Temel:     edit şablonu · marka kiti · anlatıcı sesi
        Gelişmiş ▸ ışık · özel palet · arka plan · geçiş · zoom · altyazı · sağlayıcı
        ↓
ADIM 4  Üretim planı  (ÜRETİM BAŞLAMADAN ÖNCE)
        süre · kelime · sahne · güvenilir kaynak sayısı · kullanılabilir medya sayısı
        tahmini maliyet · render süresi · stil · ses · çözünürlük · lisans durumu
        ⛔ Yeterli medya yoksa "Projeyi Oluştur" DEVRE DIŞI + genişletme önerisi
        ↓
ADIM 5  Onay
        [ Projeyi Oluştur ]   ← tek birincil buton
        altında: maliyet · süre · çıktılar (video, kapak, kaynakça)
```

Her adımda: sol üstte adım göstergesi, sağ altta "Devam", geri gitmek serbest, girilenler saklanıyor (taslak).

---

## 5. Wireframe — masaüstü

```
┌────────────┬──────────────────────────────────────────────────────────┐
│ BEDOSAHO   │  Ana Sayfa                                    [ + Yeni ] │
│            ├──────────────────────────────────────────────────────────┤
│ ▸ Ana Sayfa│                                                          │
│   Yeni Proj│   ┌────────────────────────────────────────────────┐     │
│   Projelerm│   │  Yeni bir belgesel üret                        │     │
│   Videolar │   │  Konu ver, sistem araştırır ve videoyu kurar.  │     │
│            │   │                      [ Projeye Başla ]         │     │
│   Marka Kit│   └────────────────────────────────────────────────┘     │
│   Şablonlar│                                                          │
│            │   Son projeler                              tümü ›       │
│   Ayarlar  │   ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐                   │
│            │   │kapak │ │kapak │ │kapak │ │kapak │                   │
│            │   │Kodoku│ │Senior│ │Ocean │ │Arctur│                   │
│            │   │●bitti│ │◐%62  │ │●bitti│ │✕hata │                   │
│            │   └──────┘ └──────┘ └──────┘ └──────┘                   │
│            │                                                          │
│            │   Sistem   ● Araştırma  ● Medya  ● Render  ● Ses        │
└────────────┴──────────────────────────────────────────────────────────┘
  240px         maks içerik 1200px, 12 kolon, 8px spacing
```

Wizard adımı (Adım 4 örneği):

```
┌────────────┬──────────────────────────────────────────────────────────┐
│ BEDOSAHO   │  Yeni Proje            ①──②──③──❹──⑤   Üretim planı     │
│            ├──────────────────────────────────────────────────────────┤
│            │   ┌─ Plan ─────────────────┐ ┌─ Kaynak & medya ───────┐ │
│            │   │ Süre        ~9 dk 40 sn│ │ Güvenilir kaynak    14 │ │
│            │   │ Kelime           1.720 │ │ Doğrulanmış iddia   11 │ │
│            │   │ Sahne               96 │ │ Kullanılabilir medya 88│ │
│            │   │ Şablon  Atlas Journey  │ │ Lisans      ✓ tamam    │ │
│            │   │ Ses      Andrew (EN)   │ │ Kapsam       %92       │ │
│            │   │ Çözünürlük     1080p   │ └────────────────────────┘ │
│            │   └────────────────────────┘                             │
│            │   ┌─ Maliyet ──────────────────────────────────────────┐│
│            │   │ Araştırma $0.42 · Ses $0.14 · Medya $0.31          ││
│            │   │ Render $0 · TOPLAM tahmini  $0.87                  ││
│            │   └───────────────────────────────────────────────────┘│
│            │                                    [ Geri ] [ Devam › ] │
└────────────┴──────────────────────────────────────────────────────────┘
```

## Wireframe — mobil (375px)

```
┌───────────────────────────┐   ┌───────────────────────────┐
│ ☰   BEDOSAHO         ⚙    │   │ ‹  Yeni Proje      ①②❸④⑤ │
├───────────────────────────┤   ├───────────────────────────┤
│                           │   │  Görsel yön               │
│  ┌─────────────────────┐  │   │                           │
│  │ Yeni belgesel üret  │  │   │  Edit şablonu             │
│  │ Konu ver, gerisi    │  │   │  ┌─────────────────────┐  │
│  │ bizde.              │  │   │  │ ▶ Atlas Journey   ✓ │  │
│  │  [ Projeye Başla ]  │  │   │  └─────────────────────┘  │
│  └─────────────────────┘  │   │  ┌─────────────────────┐  │
│                           │   │  │ ▶ Cinematic Nature  │  │
│  Son projeler             │   │  └─────────────────────┘  │
│  ┌─────────────────────┐  │   │                           │
│  │ [kapak]  Kodokushi  │  │   │  Marka kiti               │
│  │ Belgesel · 9:40     │  │   │  [ Arcturus Realm    ▾ ]  │
│  │ ● tamamlandı        │  │   │                           │
│  └─────────────────────┘  │   │  Anlatıcı sesi            │
│  ┌─────────────────────┐  │   │  [ Andrew (EN)       ▾ ]  │
│  │ [kapak]  Senior Mon │  │   │                           │
│  │ Belgesel · üretimde │  │   │  ▸ Gelişmiş ayarlar       │
│  │ ◐ %62  medya aranıy │  │   │                           │
│  └─────────────────────┘  │   │                           │
│                           │   ├───────────────────────────┤
├───────────────────────────┤   │   [    Devam    ]  sticky │
│ ⌂     ✎      ▤      ⚙    │   └───────────────────────────┘
│ Ana  Yeni  Projeler Ayar  │
└───────────────────────────┘
```

Mobil kuralları: üst bar + 4 öğeli alt navigasyon, tam genişlik kartlar, sticky "Devam", 44px dokunma hedefi, yatay taşma yok.

---

## 6. Korunacak API uçları

Frontend yeniden yazılırken **bu sözleşmeler aynen korunacak** — backend'e dokunulmayacak.

| Uç | Metot | Wizard'da nerede |
|---|---|---|
| `/api/generate` | POST (multipart) | Adım 5 — **alan adları değişmeyecek** |
| `/api/job/{is_id}` | GET | İlerleme ekranı |
| `/api/isler` | GET | Projelerim / Videolar |
| `/api/edit-stilleri` | GET | Adım 3 + Şablonlar |
| `/api/animasyon-stilleri` | GET | Adım 1/3 (animasyon türü) |
| `/api/sesler`, `/api/ses-kutuphane` | GET | Adım 3 + Ayarlar › Ses |
| `/api/paletler`, `/api/isik-duzeyleri`, `/api/arkaplanlar` | GET | Adım 3 › Gelişmiş |
| `/api/altyazi-sablonlari` | GET | Adım 3 › Gelişmiş |
| `/api/profiller`, `/api/profil`, `/api/profil/{pid}` | GET/POST/DELETE | Marka Kitleri |
| `/api/profil/{pid}/capa-sifirla` | POST | Marka Kiti detay |
| `/api/anim/analiz`, `/api/anim/sorular` | POST | Animasyon türü Adım 2 |
| `/api/saglik`, `/api/freepik-kota` | GET | Ayarlar › Sistem Durumu |
| `/ciktilar/{dosya}`, `/onizleme/{dosya}`, `/fonts/{dosya}`, `/ses-ornek/{dosya}` | GET | Medya servisi |

**Yeni uç gerekecek olanlar** (Faz 2, backend işi — şimdi değil): proje CRUD (`/api/projeler`), Adım 4 ön-kontrol (`/api/onkontrol`), sahne bazlı yeniden üretim.

**Kritik uyum sorunu:** Adım 4'ün göstermesi gereken "güvenilir kaynak sayısı / kullanılabilir medya sayısı / tahmini maliyet" için **backend ucu yok**. Faz 1'de bu alanlar arayüzde yer tutucu olarak kalacak ve gerçek veriye Faz 2'de bağlanacak — uydurma sayı göstermeyeceğim.

---

## 7. Frontend refactor riskleri

| Risk | Etkisi | Önlem |
|---|---|---|
| **Tek 1698 satırlık dosya, framework yok** | Bir hata tüm arayüzü çökertir | Yeni yapıyı ayrı dosyalarda kur (`static/app/`), eski `index.html` bozulmadan dursun; geçiş bitince değiştir |
| **`/api/generate` 20+ form alanı** | Alan adı kayması = üretim başlamaz veya yanlış parametre | Form alanlarını tek bir `alanlar.js` haritasından üret; regresyon testi her alanın gönderildiğini doğrular |
| **`view-studio` (Yeni Video) DOM'u Şahan'ın Sora + ses kütüphanesi ekranlarını taşıyor** | Silinirse o özellikler kaybolur | Silme yok; Adım 3 › Gelişmiş içine taşınacak |
| **Videolarım `localStorage`'a bağlı** | Sunucu tabanlına geçince eski işler listeden düşer | `/api/isler` ile birleştir, localStorage'ı **yedek** olarak koru |
| **Animasyon türü referans kare zorunlu (sunucu 400 döndürüyor)** | Wizard'da atlanırsa üretim başarısız olur | Adım 1'de animasyon seçilirse Adım 2'de yükleme **zorunlu alan** olarak işaretlenir |
| **Emoji → SVG geçişi** | 40+ emoji, kaçırılan biri tutarsız görünür | Tek `ikon(ad)` fonksiyonu; emoji kalıntısı için lint kuralı |
| **Karanlık tema kontrastı** | Mevcut gri metinler WCAG AA altında olabilir | Token'lara geçiş + kontrast ölçümü |
| **Deploy'da frontend ayrı kopyalanıyor mu?** | `deploy.sh` `webapp/` tamamını kopyalıyor → statik dosyalar dahil, sorun yok | Doğrulandı |

---

## 8. Canlı sitedeki yanlış bilgiler — doğrulama sonucu

Kodla karşılaştırdım, altısı da **gerçekten yanlış**:

| Sitede yazan | Gerçek | Kanıt |
|---|---|---|
| "Magnific HD — opsiyonel toggle, kredi bazlı" | **API bozuk**, destek çözmedi | `CODEX_BRIEF.md §2`; `MAG_BASE` düzeltilmesine rağmen anahtar üretilemiyor |
| "Hostinger VPS — Render + web. Yenileme 2026-08-16" | **Hetzner RX-4**, 185.23.17.240, 1 Ağu'da taşındı | `deploy.sh:15-17` |
| "Documentary… footage bulunamazsa AI görsel yedeği" | Belgeselde **AI görsel YASAK** (`gorsel_yasak: True`) | `pipeline.py` seyahat-belgeseli profili |
| "YouTube (yt-dlp) — herhangi bir video" | **Yalnızca Creative Commons**, lisans video bazında tek tek doğrulanıyor | `kaynak.py:_lisans_cc_mi`, `YT_CC_FILTRE` |
| "Telif: YouTube modu telifli içerik indirebilir… güvenli mod tercih et" | Telifli indirme **seçenek olarak sunulmamalı** — kod zaten CC dışına çıkmıyor | Uyarı metni, olmayan bir riski seçenek gibi gösteriyor |
| Footage zinciri "YouTube→Pexels→AI" | Gerçek zincir **Pexels→Pixabay→Coverr→YouTube(CC)** | `kaynak.footage_getir` |
| Krediler ekranı maliyetleri | Güncel değil; bugün ölçülen gerçek rakamlar var (araştırma $0.035/soru, vision $0.0008/klip) | bu oturum ölçümleri |

Ek olarak **"BBC Earth / Nat Geo"** gibi marka adları stil açıklamalarında ürünün kendisiymiş gibi kullanılıyor (`pipeline.py` `ozet` alanları) → şablon adları özgünleştirilecek, marka adları yalnızca ikincil "ilham" satırında kalacak.

---

## 9. Uygulama sırası

**Faz 1 (şimdi, yerelde):** bilgi mimarisi + yeni navigasyon + Ana Sayfa + wizard iskeleti + tasarım token'ları + SVG ikon seti + yanlış bilgilerin düzeltilmesi. Backend'e dokunulmaz, mevcut API sözleşmeleri korunur.

**Faz 2:** proje detay sayfası, sunucu tabanlı kütüphane, aşamalı ilerleme ekranı (yeni backend uçları gerekir).

**Faz 3:** marka kitleri, şablon galerisi, ayarlar ekranları.

**Faz 4:** mobil, erişilebilirlik, mikro animasyonlar.
