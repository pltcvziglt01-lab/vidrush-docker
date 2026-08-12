# EditorV2 render örnekleri

Bu dizinde **altı** örnek var:

| Dosya | Ne | Betik |
|---|---|---|
| `editorv2_doga_i18.mp4` | ⭐ **16.4 sn · 1080p · TÜRKÇE doğa/seyahat — Auto stil + gerçek web medyası** | `webapp/testler/smoke_konsept2_doga_i18.py` |
| `editorv2_motion_i17.mp4` | ⭐ **17.6 sn · 1080p · belgesel motion grammar + optik durağanlık kapısı** | `webapp/testler/smoke_motion_grammar_i17.py` |
| `editorv2_altyazi_1080p_i16.mp4` | 17.6 sn · 1080p · altyazılı + künyeli (I-16; b002 5.2 sn optik donuk) | `webapp/testler/smoke_altyazi_kunye_1080p_i16.py` |
| `editorv2_kalite_pass_i15.mp4` | 12.8 sn Apollo belgeseli — kalite kapısı AÇIK ve PASS (720p, altyazısız) | `webapp/testler/smoke_kalite_pass_i15.py` |
| `editorv2_quality_voice_10sn.mp4` | 10 sn Apollo mini-belgeseli (I-13; kapı açıkken **FAIL(4)** verir) | `webapp/testler/smoke_kaliteli_ses_10sn.py` |
| `editorv2_smoke_20sn.mp4` | 20 sn motor smoke (sessiz anlatım, konu uyuşmazlıklı) | `webapp/testler/smoke_editorv2_20sn.py` |

---

# 0) ⭐ I-18/I-19 — ikinci konsept: Türkçe doğa/seyahat, gerçek web medyası

```bash
python3 webapp/testler/smoke_konsept2_doga_i18.py
```

İlk beş örnek hep aynı Apollo fixture'ıydı. Bu, **ikinci konsept** ve
**gerçekten edinilmiş** medyayla üretildi.

| Ölçüm | Değer |
|---|---|
| Konu | kullanıcı **yalnız metin** verdi → `seyahat` / kesin / 0.87 |
| Stil | **`seyahat-4k`** (kaynak `auto`) → edit profili **`atlas-journey`** |
| Medya | **NASA** (kamu malı) — Wikimedia 429 verince devre açıldı |
| Failover | 38.4 sn (soğuk başlangıç) → **2.0–3.2 sn** |
| Anlatım | **Türkçe** (`tr-TR-AhmetNeural`), altyazı Türkçe |
| Künye | sahneye özgü: `GSFC / NASA-PUBLIC`, `Caltech / NASA-PUBLIC` |
| Çıktı | 1920×1080, 16.427 sn, LUFS −14.x, PRE WARN(0) / **POST PASS** |

**Dürüst sınırlar:** çıktı **1080p, 4K değil** — kaynakların hepsi 3840 px
eşiğini geçmiyor (2800–5184 px) ve **upscale yapılmadı**. Medya
**yörünge/uydu** görüntüsüdür; anlatım buna uydurulmuştur (görüntüye
uymayan yer-seviyesi metni kullanılmadı). Tek sağlayıcı hayatta kaldığı
için `SAGLAYICI-TEKEL` WARN'ı duruyor. Hareketli B-roll hâlâ **BLOKE**.
Pexels anahtarı **geçersiz** (HTTP 401) — yeni anahtar alınmadı.

---

# 0b) I-17 — belgesel motion grammar + optik durağanlık kapısı

```bash
python3 webapp/testler/smoke_motion_grammar_i17.py
```

I-16 teknik olarak temizdi ama izleyici için amatördü: dört statik fotoğraf
17.6 sn boyunca duruyordu ve bir sahne neredeyse **hiç değişmiyordu**.

**Ölçülen önce/sonra** (4 fps / 64×36 gri, ardışık ortalama mutlak fark):

| Sahne | I-16 | **I-17** |
|---|---|---|
| b001 | push-in · 3.551 | push-in · **3.517** |
| b002 | **static · 0.914** ← donuk | **pull-out · 5.366** |
| b003 | push-in · 5.102 | **slow-drift · 4.629** |
| b004 | pull-out · 7.030 | **pan-left · 30.426** |
| Geçiş | 4/4 hard-cut | **hard-cut ×3 + karartma ×1** |
| Benzersiz hareket | 3 (push-in ×2) | **4, tekrar yok** |
| İzleyici kalite puanı | — | **100/100** |

**Bulunan ve kapatılan gizli render hatası:** `pan-left` + `punch-1.6`
kadrajında **sağ kenarda siyah bant** oluştu (16.72 sn karesinde görüldü).
Kök neden `motion._guvenli_pay`ın CSS `scale(S) translate(x%)` sırasını
hesaba katmaması — kayma ekranda **S kat** büyüyor. Doğru sınır
`pay ≤ (S−1)/(2S)`. Eski formül 8 kadraj/hareket kombinasyonunun **5'inde**
taşıyordu (en yaygın `pan-left/tam` dahil); pan hareketleri seçilmediği için
görünmemişti.

**Dürüst sınır:** optik büyüklük siyah bandı ayırt **edemiyor** — bantlı kare
38.911, temiz hızlı pan 34.525 ölçtü (%12 fark). Bu yüzden ayrı ve doğru
enstrüman eklendi: `kenar_siyahligi_olcusu`. Hareketli B-roll **BLOKE** aynen
duruyor; benzerlik eşiği (0.86) değişmedi.

---

# 0b) I-16 — altyazılı + kaynak künyeli 1080p Apollo belgeseli

```bash
python3 webapp/testler/smoke_altyazi_kunye_1080p_i16.py
```

I-15 kapıyı PASS ettirmişti ama altyazı yoktu, kaynak künyesi ekranda
görünmüyordu ve çıktı 720p'ydi. Bu örnek üçünü de kapatır.

| Ölçüm | I-15 | **I-16** |
|---|---|---|
| Çözünürlük | 1280×720 | **1920×1080** |
| Süre | 12.8 sn | **17.579 sn** |
| Altyazı | yok | **5 küp, zaman kodlu, ≤2 satır / ≤42 karakter** |
| Kaynak künyesi | üretilmiyordu | **NASA / PUBLIC-DOMAIN, sahneye bağlı** |
| Güvenli alan | — | **ihlal yok** (1080p'de ölçüldü) |
| Yazı çakışması | — | **yok** (başlık + künye + altyazı aynı anda) |
| Miks | −14.87 LUFS | **−14.32 LUFS / TP −2.08** (tek loudnorm remaster) |
| Kare | 9 | **10**, hepsi görsel incelendi |
| PRE / POST QA | WARN / PASS | **WARN(fail=0) / PASS** |

**Kapatılan iki gerçek kusur:** `altyazi` alanı sözleşmede vardı ve adapter
onu props'a taşıyordu ama **hiçbir Remotion bileşeni çizmiyordu** — yeni
`Altyazi` bileşeni eklendi. `KaynakEtiketi` ise `bottom: 22` sabitiyle
çiziliyordu, yani Python'un konum hesabını hiç okumuyordu ve 1080p'de yayın
güvenli alanının (64 px) **dışında** kalıyordu.

**Dürüst sınırlar:** cümle içi bölünme gerektiğinde küp zamanlaması ölçüm
değil, karakter ağırlıklı **orantılı dağıtımdır** (edge-tts 7.2.8 yalnızca
cümle sınırı veriyor, kelime sınırı vermiyor — ölçüldü); her küp
`zamanlama: olculdu|orantili` etiketi taşır. **Hareketli video B-roll
BLOKE:** güvenli fixture havuzunda gerçek video adayı yok; depodaki `.mp4`
dosyalarının hepsi bu projenin kendi render çıktıları (Faz D/E pilotları) ve
B-roll değildir. Medya çeşitliliği eşiği (0.86) **değişmedi**.

---

# 0b) I-15 — kalite kapısı AÇIKKEN PASS üreten Apollo belgeseli

```bash
python3 webapp/testler/smoke_kalite_pass_i15.py
```

I-14 kapıları kurdu ve I-13 çıktısı açık kapıda **FAIL(4)** verdi. Bu örnek
aynı Apollo fixture'ıyla **gerçekten düzeltilmiş** çıktıdır.

| Ölçüm | I-13 (10 sn) | **I-15 (12.8 sn)** |
|---|---|---|
| Ön-render QA | WARN (fail=0) | WARN (fail=0) |
| **Kapı açıkken** | **FAIL(4)** | **PASS** |
| Başlık | `20 JULY` → `20 JU`, 272.5 px taşma | **`THE EAGLE HAS LANDED`, 0 px taşma, tam punto 60** |
| Sahne süreleri | 3.2 · 3.2 · 3.2 (yayılım 0.0) | **1.637 · 4.051 · 3.224 · 3.825** (yayılım 2.414) |
| Süre kaynağı | eşit bölme | **edge-tts `SentenceBoundary`** (gerçek anlatım zamanlaması) |
| Ölü final | 0.903 sn | **0.0 sn** |
| Ambiyans | anlatımın 57.1 dB altında (duyulmaz) | **23.1 dB altında — duyulabilir, bastırmıyor** |
| Miks | −16.56 LUFS | **−14.87 LUFS / TP −4.0 / kırpma yok** |
| Kare | 3 | **9** (hepsi görsel incelendi) |

**Dört gerçek düzeltme:** `plan.py`'nin sabit `[:42]` dilimi kaldırıldı ve
sınır gerçek render genişliğinden (1280) hesaplanıyor · TSX sığdırma hesabı
artık `letterSpacing`'i sayıyor · süreler `SentenceBoundary`'den türetiliyor ·
`anlatim_araliklari` geçirildiği için ducking artık tüm videoya değil yalnızca
konuşma aralıklarına uygulanıyor.

**Dürüst sınırlar:** medya çeşitliliği için hiçbir eşik düşürülmedi; ölçülen en
yüksek ikili benzerlik **0.6094** (eşik 0.86 — I-14'ten değişmedi) ve fixture
havuzunun en çeşitli 4'lüsü zaten seçili. Yalnızca **sıra** değiştirilerek
komşu benzerliği 0.6094 → 0.5312'ye indirildi. Altyazı, kaynak künyesi ve
1080p **hâlâ kapsam dışı**. edge-tts prosodisi çağrıdan çağrıya biraz
değiştiği için süreler bit-bit tekrar üretilebilir değildir.

---

---

# 1) 10 sn — kaliteli anlatıcı sesli Apollo 11 mini-belgeseli

```bash
python3 webapp/testler/smoke_kaliteli_ses_10sn.py
```

**Konu tutarlı:** görsel + metin + anlatım üçü de **Apollo 11 ay inişi**.
Görseller Faz E koşusundan kalan gerçek NASA/Wikimedia arşiv fotoğrafları,
metin Faz E araştırma manifestindeki **doğrulanmış** iddialar (f001/f004/f005),
anlatım aynı metnin seslendirmesi. Önceki örnekteki *Apollo görsel + Endurance
metni* uyuşmazlığı **giderildi**.

## Ölçülen çıktı

| Ölçüm | Değer |
|---|---|
| Video | **h264** 1280×720 @ 30 fps |
| Ses | **aac** 48 000 Hz / 2 kanal |
| Süre | **9.643 sn** |
| Boyut | 8.22 MB |
| Miks | LUFS −16.56 · TP −4.47 dBTP · **kırpma yok** · sessizlik %19.6 |
| Ön-render QA | WARN (fail=0, warn=2) → render'a izin verildi |

Kareler: `vkare_00s.png` (Eagle + astronot) · `vkare_05s.png` (ayak izi) ·
`vkare_09s.png` (bot izi yakın plan) — üçü de gözle doğrulandı.

## Anlatıcı sesi — seçim gerekçesi (ölçüldü)

| Aday | LRA | LUFS | Süre |
|---|---|---|---|
| **en-GB-RyanNeural** ✅ | **1.6** | −21.4 | 9.74 sn |
| en-US-AndrewNeural | 1.5 | −20.3 | 9.14 sn |
| en-US-BrianNeural | 0.5 | −20.2 | 8.95 sn |

Seçim ölçüte dayanıyor: **en yüksek LRA** (dinamik genişlik) = en az düz okuma.
Master'lanmış hâli: `pcm_s16le / 48 kHz / mono · 8.789 sn · LUFS −16.43 ·
TP −1.5 dBTP · LRA 2.0 · sessizlik %11.1 · kırpma yok`.

⚠ **Yereldeki hazır anlatım kullanılmadı.** Faz E `pilot_rapor.json`'a göre o
ses **`macOS say -v Yelda`** ile üretilmiş; ölçümü LRA **0.3–1.9**, yani düz ve
makine benzeri — belgesel anlatımı kalitesinde değil. Onun yerine projenin
**kendi varsayılan TTS motoru** (`app/uret.py` → edge-tts) kullanıldı.

⚠ **Maliyet $0.00.** edge-tts anahtar istemez, kredi harcamaz. Kredi
yüklenmedi, anahtar değiştirilmedi.

⚠ **Dürüst sınır:** LRA 2.0 iyi bir *nöral TTS*'tir, **insan anlatıcı değildir**.
Gerçek belgesel spikeri LRA 4–8 aralığındadır.

## Görsel seçimi — ölçülen kapı

İlk render'da 0. ve 9. saniye kareleri **düz gri** çıktı. Ölçüm nedeni
gösterdi: kullanılan `a281` (detay std **6.1**) ve `a282` (**4.7**) havuzun en
boş kareleriydi. Artık kadraja düşen detay **ölçülüyor** ve eşik altı
(< 20) görsel **kullanılmıyor**:

```
a313  63.6 SEÇİLDİ   a082  63.1 SEÇİLDİ   a314  55.1 SEÇİLDİ
a086  53.8 -         a283  53.0 -
a281   6.1 eşik altı a282   4.7 eşik altı
```

Kare boyutları 647/543/578 KB → **865/925/1121 KB**.

## ⚠ Bu video neyi KANITLAMAZ

- **Web'den medya bulma** — hiçbir sağlayıcıya istek atılmadı
- **Araştırma/fact-check motoru** — olgular Faz E manifestinden hazır geldi
- **Canlı `/api/generate` hattı** — pipeline çağrılmadı
- **Ücretli API** — maliyet $0.00

---

# 2) EditorV2 20 saniyelik render smoke

`webapp/testler/smoke_editorv2_20sn.py` bu dizine gerçek bir MP4 üretir.

```bash
python3 webapp/testler/smoke_editorv2_20sn.py
```

## Kalite: ÖNCE / SONRA (I-11 → I-12)

| | ÖNCE (I-11) | SONRA (I-12) |
|---|---|---|
| Ön-render QA | **5 WARN** | **2 WARN** |
| 19. sn karesi | anlamsız dev **"1"** + tek sarı bar, başlık kırpık | temiz **bölüm kartı**, başlık tam |
| `source-label` alt kenarı | 1020.6 px (güvenli alan **1016** — taşıyor) | 1015.2 px ✅ |
| Kare boyutu (19 s) | 78 KB | 104 KB |

### 5 QA WARN — tek tek

| Kod | Detay | Kaynak | Durum |
|---|---|---|---|
| `TIPO-GUVENLI-ALT` ×3 | `source-label: alt=1020px > 1016` | **motor kusuru** | ✅ kapatıldı (`KONUM` 0.90 → 0.895) |
| `PACING-KISA-ORAN` | 4 sn altı oran %83, referans %32 | **fixture** | açık — test verisinin beat'leri kısa |
| `SAGLAYICI-TEKEL` | tek sağlayıcı %100 (tavan %40): wikimedia | **fixture** | açık — fixture yalnız Wikimedia içeriyor |

Ayrıca 3 adet `uyari` seviyesinde `SUREKLILIK-AYNI-SAGLAYICI` var; aynı
fixture sınırından geliyor.

⚠ Kalan 2 WARN **motor kusuru değil**: QA, test verisinin gerçekçi
olmadığını doğru tespit ediyor. Gerçek bir işte farklı sağlayıcılardan
gelen adaylarla ikisi de düşer.

### Düzeltilen iki gerçek kusur

1. **Sayı uyduruluyordu.** `plan.py` medyasız beat'e sabit `[1]` değeriyle
   veri grafiği veriyordu → ekranda anlamsız dev "1" + tek bar. Artık
   `_beat_sayilari()` metinden **gerçek** sayı çıkarır (yıllar elenir);
   sayı yoksa veri sahnesi **çizilmez**, profesyonel bölüm kartına düşülür.
   `Grafikler.tsx` de boş veride `null` döner (derinlemesine savunma).
2. **Başlık harf ortasından kırpılıyordu.** Bant `overflow:hidden` +
   `nowrap` idi; hesaplanan karakter sınırı font metriği **tahmin** olduğu
   için yetmedi. Artık TSX metni sığdıramazsa **puntoyu küçültür** (en fazla
   %30), yani harf asla kesilmez. Python tarafı ayrıca sarkan edat/bağlaçları
   atar ("…Elephant Island **in**" → "…Elephant Island").

## Ölçülen çıktı (12 Ağu 2026)

| Ölçüm | Değer |
|---|---|
| Codec | h264 / aac |
| Çözünürlük | 1280×720 @ 30 fps |
| Süre | **20.096 sn** |
| Boyut | 10.49 MB |
| Ses | 48 000 Hz / 2 kanal |
| Render süresi | ~25 sn (Apple M-serisi, yerel) |
| Ön-render QA | WARN (fail=0, warn=5) → render'a izin verildi |
| Efekt kapsamı | 38 spec, hepsi `gercek` (0 bilinmeyen) |

Kareler: `kare_00s.png` · `kare_10s.png` · `kare_19s.png`
Makine-okunur rapor: `smoke_rapor.json`

## ⚠ BU VİDEO NEYİ KANITLAR

Gerçek motorun **şu kısımları** çalıştı:

- `edit_kopru.plan_kur()` → `editor.plan.uret()` tam Faz C zinciri
  (beat → gramer → motion → tipografi → ses → **ön-render QA**)
- `editor.adapter.donustur()` ile gerçek Remotion props üretimi
- `editor.remotion_v2.dogrula()` ön-render kapısı
- `editor.remotion_v2.props_hazirla()` + `render()` → **Remotion
  `VidrushEditorV2` kompozisyonu**, Chrome headless + ffmpeg
- Lisans duvarı, kapsam boşluğu ve `fact_id` zincirinin props'a kadar gelmesi

Sahne zinciri (rapordan, birebir):

```
b001 scene=s001 fact=f001 asset=a082_wiki_… lisans=cc-by-sa      2.523 sn
b002 scene=s001 fact=f001 asset=a082_wiki_… lisans=cc-by-sa      2.524 sn
b003 scene=s002 fact=f002 asset=a086_wiki_… lisans=cc-by         5.907 sn
b004 scene=s003 fact=f003 asset=a281_wiki_… lisans=public-domain 2.790 sn
b005 scene=s003 fact=f003 asset=YOK  -> motion-graphic fallback  3.487 sn
b006 scene=s004 fact=f004 asset=YOK  -> motion-graphic fallback  2.769 sn
```

## ⚠ BU VİDEO NEYİ **KANITLAMAZ**

- **Web'den medya bulma.** Hiçbir sağlayıcıya istek atılmadı. Görseller ve
  sesler daha önce indirilmiş **yerel fixture**'lardır
  (`app/render-studio/public/editorv2/faz_e/`, Faz E koşusundan kalma).
- **Araştırma / fact-check motoru.** Olgular sabit fixture.
- **TTS üretimi.** Ses dosyaları hazır `.wav`.
- **Canlı `/api/generate` hattı.** Pipeline çağrılmadı.
- **Ücretli hiçbir API.** Ağ çağrısı yok.

### İçerik uyuşmazlığı (dürüstçe)

Fixture görselleri Faz E koşusundan kalma **Apollo / Ay** arşiv fotoğraflarıdır;
fixture anlatımı ise **Endurance / Antarktika** metnidir. Yani videodaki görsel
ile anlatım **konu olarak örtüşmez**. Bu kasıtlıdır: burada ölçülen şey
*kurgu motorunun gerçekten video üretip üretmediği*, içerik tutarlılığı değil.

Son iki beat'te medya yok → **motion-graphic fallback** çizildi. Bu doğru
davranıştır: kapsam boşluğu **rastgele stokla kapatılmaz**.

## Dosyalar neden git'te izlenmiyor?

MP4 ve PNG'ler `.gitignore`dadır (~13 MB). Git geçmişine giren ikili dosya
geri alınamaz; bu yüzden yalnızca bu `README.md` ve `smoke_rapor.json`
izlenir. Videoyu görmek için betiği yerelde çalıştırmak yeterlidir.
