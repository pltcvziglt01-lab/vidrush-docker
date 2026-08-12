# EditorV2 20 saniyelik render smoke

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
