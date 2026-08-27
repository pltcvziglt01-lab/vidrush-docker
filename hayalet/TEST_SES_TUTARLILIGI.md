# SES TUTARLILIGI TESTI — FLOW
Amac: ayni ses tarifi verilince Flow ne kadar ayni sesi uretiyor?
Karakter: EARL (bkz. KARAKTER_EARL.md) · 9:16 · konusan plan

================================================================
## TESTIN KURGUSU — 3 URETIM, 2 SORU
================================================================

Sadece iki farkli prompt uretirsen sonuc yorumlanamaz: ses farkliysa
"tarif tutmadi" mi yoksa "Flow zaten her seferinde rastgele mi" bilemezsin.
Bu yuzden **3 uretim** yapiyoruz:

| Uretim | Prompt | Olctugu sey |
|---|---|---|
| **A1** | Prompt A | temel |
| **A2** | Prompt A — **birebir ayni, tekrar calistir** | Flow'un **kendi rastgeleligi** (taban gurultu) |
| **B** | Prompt B — ayni ses blogu, farkli sahne + farkli replik | **Ses tarifi tasiniyor mu** |

**Okuma:**
- A1 ≈ A2 **ve** A1 ≈ B → ses tarifi tutuyor. Dis TTS'e gerek yok, sevin.
- A1 ≠ A2 → Flow ayni promptta bile kayiyor. Tarif sucsuz, **is dis seste**.
- A1 ≈ A2 ama A1 ≠ B → tarif sahne degisince tasinmiyor. **Yine dis ses.**

⚠ Ucunu de **ayni oturumda, arka arkaya** uret. Farkli gun / farkli proje
farkli sonuc verebilir ve testi kirletir.

================================================================
## SABIT BLOKLAR — IKI PROMPTTA DA KELIMESI KELIMESINE AYNI
================================================================

Asagidaki iki blogu **hic degistirmeden** kopyalayacaksin. Testin tum anlami
bunlarin ayni olmasinda.

### KARAKTER BLOGU
```
"EARL", an 85-year-old American farmer — wide-brimmed pale mustard-yellow
straw hat with a slightly frayed brim, short neatly trimmed pure white full
beard and moustache, thick white eyebrows, pale blue eyes behind round thin
gold-rimmed glasses, red-and-white plaid flannel shirt with the sleeves
rolled to the elbow, dark blue denim bib overalls with brass buckles, an old
silver watch on a worn brown leather strap on his left wrist, large tanned
heavily veined hands
```

### SES BLOGU
```
VOICE: he speaks in a low, warm, gravelly voice — an unhurried 85-year-old
American man from rural Kentucky with a soft Appalachian drawl. Slow steady
pace, gentle and reassuring, slightly breathy, never loud, never excited.
Pitch is deep and a little rough around the edges, like a man who has
talked over a workbench his whole life.
```

================================================================
## PROMPT A — MUTFAK / EV YAPIMI DETERJAN
================================================================

```
A worn wooden kitchen table in an old American farmhouse, shot from a low
front angle. Behind him a window with warm golden afternoon light streaming
in, dust motes in the air. On the table: a glass mason jar of white powder,
a bar of plain soap, a white enamel bowl.

"EARL", an 85-year-old American farmer — wide-brimmed pale mustard-yellow
straw hat with a slightly frayed brim, short neatly trimmed pure white full
beard and moustache, thick white eyebrows, pale blue eyes behind round thin
gold-rimmed glasses, red-and-white plaid flannel shirt with the sleeves
rolled to the elbow, dark blue denim bib overalls with brass buckles, an old
silver watch on a worn brown leather strap on his left wrist, large tanned
heavily veined hands — sits at the table, lifts the glass jar toward the
camera and turns it slowly in his hand while he talks.

He says: "Store detergent is mostly water. This jar cost me four dollars,
and it'll wash two hundred loads. My mother made it the same way."

VOICE: he speaks in a low, warm, gravelly voice — an unhurried 85-year-old
American man from rural Kentucky with a soft Appalachian drawl. Slow steady
pace, gentle and reassuring, slightly breathy, never loud, never excited.
Pitch is deep and a little rough around the edges, like a man who has
talked over a workbench his whole life.

The camera slowly pushes in. Warm golden side light, shallow depth of field,
photorealistic, 50mm lens. Vertical 9:16. No on-screen text, no captions,
no subtitles, no watermark, no music.
```

================================================================
## PROMPT B — VERANDA / EV YAPIMI SABUN
================================================================

Degisen: mekan, nesne, replik. **Karakter blogu ve ses blogu aynen ayni.**

```
The back porch of an old American farmhouse at golden hour. A weathered
wooden rocking chair beside a plain wooden railing, worn floorboards, an
open field blurred in the background. On the railing: three bars of pale
handmade soap on a folded cotton cloth.

"EARL", an 85-year-old American farmer — wide-brimmed pale mustard-yellow
straw hat with a slightly frayed brim, short neatly trimmed pure white full
beard and moustache, thick white eyebrows, pale blue eyes behind round thin
gold-rimmed glasses, red-and-white plaid flannel shirt with the sleeves
rolled to the elbow, dark blue denim bib overalls with brass buckles, an old
silver watch on a worn brown leather strap on his left wrist, large tanned
heavily veined hands — stands at the railing, picks up one bar of soap and
holds it up toward the camera while he talks.

He says: "Store soap is half perfume. This one is three things and a little
patience. One afternoon gives you a whole year of it."

VOICE: he speaks in a low, warm, gravelly voice — an unhurried 85-year-old
American man from rural Kentucky with a soft Appalachian drawl. Slow steady
pace, gentle and reassuring, slightly breathy, never loud, never excited.
Pitch is deep and a little rough around the edges, like a man who has
talked over a workbench his whole life.

The camera slowly pushes in. Warm golden side light, shallow depth of field,
photorealistic, 50mm lens. Vertical 9:16. No on-screen text, no captions,
no subtitles, no watermark, no music.
```

### Repliklerin esitligi (kasitli)
| | A | B |
|---|---|---|
| Kelime | 24 | 24 |
| Yapi | itiraz → rakam → miras | itiraz → sadelik → kazanc |
| Duygu | sakin, iddiasiz | sakin, iddiasiz |
| Bagirma / vurgu | yok | yok |

Replikler ayni uzunluk ve ayni tonda — boylece ses farki cikarsa **replik
farkindan degil**, modelden gelir.

================================================================
## KARSILASTIRMA CETVELI
================================================================

Ucunu de indir, yan yana dinle. Her satira A1-A2 ve A1-B icin ✅/❌ koy:

| Olcut | A1 vs A2 | A1 vs B |
|---|---|---|
| **Perde (ton kalinligi)** — ayni adam mi? | | |
| **Yas** — ikisi de 80+ duruyor mu? | | |
| **Aksan** — guney/Appalachian tinisi ikisinde de var mi? | | |
| **Tempo** — kelime/saniye yakin mi? | | |
| **Doku** — catlaklik/puruz ayni mi? | | |
| **Nefes** — solukluk ayni mi? | | |
| **Gozu kapali ayirt edilemiyor mu?** | | |

**Gecme notu:** 7 satirin **en az 6'si ✅** ve ozellikle son satir ✅.
Bu esigin altindaysa dis TTS'e gec — `KARAKTER_EARL.md` Bolum 0.

### Sayisal kontrol (kulaga guvenme, olc)
```bash
# temel perde (F0 medyani) — uc dosya icin de calistir
for f in A1.mp4 A2.mp4 B.mp4; do
  echo "== $f"
  ffmpeg -v error -i "$f" -ac 1 -ar 16000 -y "/tmp/$(basename $f .mp4).wav"
done
```
Sonra uc `.wav`'i bir ses editorunde (Audacity → Analyze → Plot Spectrum) ac.
**Temel frekans farki 15 Hz'i geciyorsa** kulak da farki duyar; "ayni adam"
demek zorlasir.

================================================================
## TESTTEN BAGIMSIZ, ZATEN BILINEN IKI SEY
================================================================

1. **Test tutsa bile agiz senkronu sorunu kalir.** Flow konusan plani kendi
   sesiyle uretirse o klibi metnini degistirip tekrar kullanamazsin — her
   replik icin yeni klip, yani her videoda bastan uretim. Dis seste ayni
   klibi bes farkli metinle kullanirsin.
2. **Test tutmasa bile bu kayip degil.** `KARAKTER_EARL.md`'deki tasarim
   (Earl konusmaz, is yapar, ses ustten) zaten daha ucuz ve Amerika'daki
   kazanan kanallarin hepsi oyle calisiyor.

Yani bu test **"dis ses sart mi"** sorusunu degil, **"konusan plan da
kullanabilir miyim"** sorusunu cevapliyor. Tutarsa acilis/kapanis planlarinda
Earl konusabilir — kanala can katar.

================================================================
## SONUCU BURAYA YAZ
================================================================

Tarih:
Flow surumu / arayuz (eski cip / yeni ajan paneli):

| | A1 | A2 | B |
|---|---|---|---|
| Ses nasil? | | | |
| Tahmini yas | | | |
| Aksan | | | |

Cetvel skoru — A1 vs A2: __/7 · A1 vs B: __/7
Karar:
