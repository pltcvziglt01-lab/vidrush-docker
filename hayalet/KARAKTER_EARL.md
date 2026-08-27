# EARL HOLLIS — ANA KARAKTER KITABI
Kanal: Amerikan "eski usul" · Facebook 9:16 · 30 sn
Ilgili: KONSEPT_AMERIKAN_KOYLU.md · TEST_SES_TUTARLILIGI.md

================================================================
# BOLUM 0 — DOGRULANMIS BULGU: SES BLOGU KILITLENIR
================================================================

**25 Agu 2026, canli test (TEST_SES_TUTARLILIGI.md):**
Ses blogu kelimesi kelimesine ayni verildiginde **Flow ayni sesi uretiyor.**
Farkli sahne, farkli replik — ses tutuyor.

**Sonuclari:**
- ✅ Flow'un kendi sesi **kullanilir**. Dis TTS'e gerek yok.
- ✅ Earl **kameraya konusabilir.** Agiz senkronu Flow'un kendi isi.
- ✅ Uretim tek katmana iner: Flow → kurgu. Ayri seslendirme adimi yok.
- ⚠ **Ses blogu artik karakterin bir parcasi.** Gorunusu kadar kimlik tasiyor.
  Tek kelimesi degisirse ses degisir. **Asla elle yazma, hep kopyala.**

## Kilit kurali
Ses blogu tek bir yerde durur: `hayalet/earl_ses.txt`. Her prompt onu
**dosyadan** alir. Elle yazilan her prompt, sessiz bir ses kaymasi riskidir.

```bash
# Ses blogunu bir kez yaz, bir daha dokunma
cat hayalet/earl_ses.txt
# Prompt kurarken hep bunu bastir:
{ cat sahne.txt; echo; cat hayalet/earl_karakter.txt; echo; cat hayalet/earl_ses.txt; } | pbcopy
```

## Kalan tek ses riski: ORTAM SESI
Ses **tinisi** tutuyor ama Flow her klibe kendi ortam sesini (ruzgar, kus,
oda tonu) koyabiliyor ve bu klipten klibe zipliyor. Kesme noktalarinda
duyulur. Iki onlem:
1. Prompta ortami da sabitle (asagida ORTAM satiri var, o da kilitli blok)
2. Kurguda **tek surekli ortam yatagi** (dusuk seviye) alta serilir, ziplama maskelenir

================================================================
# BOLUM 1 — KARAKTER: EARL HOLLIS
================================================================

**Adi:** EARL (sayfa adinda gecer; videoda kendini tanitmaz — 30 sn'de yer yok)
**Yas:** 85 · **Yer:** Amerikan kirsali, Kentucky
**⚠** Halil (82, TR), Bobo, Oog, Klank ile asla ayni sayfada/videoda olmaz

## 6 KILITLI OZELLIK
AI karakteri 15 detayla degil, **az sayida yuksek kontrastli isaretle** tutar.
Her promptta bu 6'si aynen tekrarlanir, gerisi serbest:

1. **Soluk hardal sarisi hasir sapka** — genis kenarli, kenari hafif yipranmis
2. **Kisa, duzgun kesilmis bembeyaz tam sakal** + kalin beyaz kaslar
3. **Koyu mavi kot tulum** + **kirmizi-beyaz ekose pazen gomlek**, kollar dirsege kivrik
4. **Ince altin metal cerceveli yuvarlak gozluk**
5. **Sol bilekte eski deri kayisli gumus saat** — eller kadraja girdiginde
   karakteri tasiyan isaret budur
6. **SES** — asagidaki blok. Gorunus kadar kimlik. Degistirilemez.

## Renk ve isik anayasasi (her promptta ayni)
- Sicak altin saat isigi, yandan yumusak pencere isigi, havada toz zerreleri
- Palet: ahsap kahvesi, emaye beyazi, kot mavisi, hardal sarisi, soluk kirmizi
- Yuzey: yipranmis ahsap, cam kavanoz, teneke kutu, emaye kase
- **Modern hicbir sey gorunmez:** plastik ambalaj, telefon, LED, markali kutu YOK

## 4 SABIT MEKAN
| Kod | Mekan | Ne icin |
|---|---|---|
| **M1** | Ahsap mutfak masasi, arkada pencere | Yemek, test, tarif |
| **M2** | Arka veranda, sallanan sandalye, korkuluk | Acilis / kapanis |
| **M3** | Ambar-atolye, duvarda el aletleri | Tamir, alet, temizlik |
| **M4** | Sebze bahcesi, tahta yatak, toprak | Bahce, bitki, tohum |

================================================================
# BOLUM 2 — DORT KILITLI BLOK (kopyala, asla yeniden yazma)
================================================================

## BLOK 1 — KARAKTER  → `hayalet/earl_karakter.txt`
```
"EARL", an 85-year-old American farmer — wide-brimmed pale mustard-yellow
straw hat with a slightly frayed brim, short neatly trimmed pure white full
beard and moustache, thick white eyebrows, pale blue eyes behind round thin
gold-rimmed glasses, red-and-white plaid flannel shirt with the sleeves
rolled to the elbow, dark blue denim bib overalls with brass buckles, an old
silver watch on a worn brown leather strap on his left wrist, large tanned
heavily veined hands
```

## BLOK 2 — SES  → `hayalet/earl_ses.txt`  ⚠ DOKUNMA
```
VOICE: he speaks in a low, warm, gravelly voice — an unhurried 85-year-old
American man from rural Kentucky with a soft Appalachian drawl. Slow steady
pace, gentle and reassuring, slightly breathy, never loud, never excited.
Pitch is deep and a little rough around the edges, like a man who has
talked over a workbench his whole life.
```

## BLOK 3 — GORUNTU + ORTAM  → `hayalet/earl_stil.txt`
```
AMBIENCE: quiet indoor room tone with faint birdsong far outside, no wind
gusts, no music.
Warm golden side light, dust motes in the air, shallow depth of field,
photorealistic, 50mm lens. Vertical 9:16. No on-screen text, no captions,
no subtitles, no watermark, no music.
```

## BLOK 4 — SUREKLILIK SOZLESMESI  → `hayalet/earl_sureklilik.txt`  ⚠ HER PROMPTA
**25 Agu 2026:** sakal boyu aciya gore degisiyor / kayboluyor, saat bazen sag
bileğe geciyor, nesneler isinlaniyordu. Cozum: karakterin **her aciya gecerli
fiziksel sabitleri** + **nesne fizigi** ayri blok olarak her prompta girer.
Icerik icin dosyaya bak — elle yazma, `earl_video.sh` otomatik ekliyor.

## PROMPT KALIBI
```
[SAHNE — M1/M2/M3/M4 tarifi + masadaki nesneler]

[BLOK 1] — [EYLEM CUMLESI].

He says: "[REPLIK]"

[BLOK 4 — sureklilik sozlesmesi]

[BLOK 2 — ses]

The camera [KAMERA HAREKETI]. [BLOK 3 — stil]
```

================================================================
# BOLUM 3 — KARAKTER CAPALARI (ilk is — bunlari uret)
================================================================

## 3A. KARAKTER SAYFASI (arsiv — Flow'a ingredient olarak VERME)
```
Character reference sheet on a plain flat warm-grey background (#D8D3C8),
no scene, no props, no text labels, no watermark.

CHARACTER "EARL": an 85-year-old American farmer. Weathered, kind, deeply
lined face with a strong jaw. Short, neatly trimmed pure white full beard
and moustache. Thick white eyebrows. Pale blue eyes behind round thin
gold-rimmed glasses. He wears a wide-brimmed pale mustard-yellow straw hat
with a slightly frayed brim, a red-and-white plaid flannel shirt with the
sleeves rolled to the elbow, and dark blue denim bib overalls with brass
buckles. On his left wrist, an old silver watch on a worn brown leather
strap. His hands are large, tanned and heavily veined, with short clean nails.

LAYOUT: a clean grid of the SAME man, identical in every cell.
Row 1 — full body front view, full body 3/4 view, full body side view.
Row 2 — head close-ups: calm neutral, warm closed-mouth smile, one eyebrow
raised in doubt, mid-sentence with the mouth slightly open.
Row 3 — both hands shown separately: open palms up, and holding a glass
mason jar; plus the left wrist with the silver watch in close-up.

Photorealistic, natural warm side light, shallow depth of field, 50mm lens
look, evenly lit background, high resolution.
```

## 3B. INGREDIENT POZ (Flow'a verilecek TEK gorsel)
⚠ Grid verme — Flow grid'i sahneye kopyaliyor.
```
Full body front view of "EARL", an 85-year-old American farmer, standing
relaxed and centered on a plain flat warm-grey background (#D8D3C8).
Weathered kind lined face, short neatly trimmed pure white full beard and
moustache, thick white eyebrows, pale blue eyes behind round thin gold-rimmed
glasses. Wide-brimmed pale mustard-yellow straw hat with a slightly frayed
brim. Red-and-white plaid flannel shirt, sleeves rolled to the elbow. Dark
blue denim bib overalls with brass buckles. Old silver watch on a worn brown
leather strap on his left wrist. Large tanned veined hands relaxed at his
sides. Calm warm closed-mouth expression, looking straight at the camera.
Photorealistic, soft warm side light, 50mm lens, shallow depth of field.
Vertical 9:16 frame, nothing else in the image, no text, no watermark.
```

## 3C. EL CAPASI (orta planlar icin — videonun cogu eller)
```
Close-up of the hands of "EARL", an 85-year-old American farmer, resting on
a worn wooden kitchen table. Large tanned heavily veined hands with short
clean nails and thick knuckles. Red-and-white plaid flannel shirt sleeves
rolled to the elbow, dark blue denim bib overall straps visible at the top
edge of the frame. An old silver watch on a worn brown leather strap on the
left wrist. Warm golden window light from the left, dust motes in the air,
shallow depth of field. Photorealistic, 50mm lens. Vertical 9:16 frame,
no text, no watermark.
```

## 3D. MEKAN CAPALARI

**M1 — Mutfak masasi**
```
A worn wooden kitchen table in an old American farmhouse, shot from a low
front angle. Behind it a window with warm golden afternoon light streaming
in, dust motes in the air. On the table: a glass mason jar, a white enamel
bowl, a folded cotton cloth. Aged wood grain, chipped enamel, no plastic,
no packaging, no modern objects, no text. Photorealistic, 50mm lens,
shallow depth of field. Vertical 9:16 frame.
```
**M2 — Arka veranda**
```
The back porch of an old American farmhouse at golden hour. A weathered
wooden rocking chair beside a plain wooden railing, worn floorboards, an
open field blurred in the background. Warm low sunlight from the side, long
soft shadows. No plastic, no modern objects, no text. Photorealistic,
50mm lens, shallow depth of field. Vertical 9:16 frame.
```
**M3 — Ambar / atolye**
```
The inside of an old American barn workshop. A heavy wooden workbench, hand
tools hanging on the plank wall behind it, a tin can of nails, coils of
twine. Warm shafts of light coming through gaps in the boards, dust in the
air, deep shadows. No power tools, no plastic, no branding, no text.
Photorealistic, 50mm lens, shallow depth of field. Vertical 9:16 frame.
```
**M4 — Sebze bahcesi**
```
A small American backyard vegetable garden in the early morning. Raised
wooden beds with dark soil, tomato plants tied to wooden stakes, a metal
watering can on the ground. Soft warm low sunlight from the side, gentle
haze. No plastic, no modern objects, no text. Photorealistic, 50mm lens,
shallow depth of field. Vertical 9:16 frame.
```

================================================================
# BOLUM 4 — 60 SANIYELIK ISKELET (6 klip × 10 sn)
================================================================

## 4.0 ⚠ DEGISMEZ KURAL: ILK 3 SANIYEDE URUN VE HOOK

**Klip 1'de urun ELDE, KADRAJDA, BUYUK olacak ve ilk cumle hook olacak.**
Facebook'ta 45+ kitle ilk 2-3 saniyede kaliyor ya da gidiyor. Once merak
kurup sonra gostermek burada calismaz — **once goster, sonra anlat.**

**Klip 1'de ASLA:**
- Selamlama yok. "Hi, I'm Earl" / "Bugun size" yok — tanitim icin yer yok
- Merak tuzagi yok ("birazdan gorecegisiniz") — vaat pesin verilir
- Bos kadraj yok, urun ilk karede elinde
- Malzeme/hazirlik yok — yapim klip 3'te baslar

### Hook formulleri (kanitli basliklardan tureildi)
| # | Kalip | Ornek ilk cumle |
|---|---|---|
| **A** | **Fiyat carpmasi** | "Four dollars. Two hundred loads. The store wants forty." |
| **B** | **Sahtelik** | "Half of what they sell you as honey never saw a bee." |
| **C** | **Unutulmus** | "Nobody makes this anymore. It takes ten minutes." |
| **D** | **Test / meydan okuma** | "If yours does not do this, it is not real olive oil." |
| **E** | **Miras** | "My mother made this every fall. I have not bought one since." |

A ve B en guclusu — rakam ve sahtecilik bu kitlede en yuksek durdurucu.
D testi gosterilebiliyorsa kullan; gorsel kanit yorumu patlatiyor.

## 4.1 Klip dagilimi

| Klip | Sn | Kadraj | Islev | Yuz? |
|---|---|---|---|---|
| **1 HOOK** | 0-10 | Orta plan, **urun elde ve buyuk** | Rakam/sahtelik + vaat | ✅ |
| **2 DUSMAN** | 10-20 | Orta-yakin, magaza urunu vs onunki | Neden kotu — kanit | ✅ |
| **3 MALZEME** | 20-30 | Ust aci, masada malzemeler | "Sadece su uc sey" | ❌ |
| **4 YAPIM** | 30-40 | Yakin plan, eller calisiyor | 1-2. adim + sure | ❌ |
| **5 SONUC** | 40-50 | Yakin plan, urun olusuyor | Son adim + **rakam** | ❌ |
| **6 KAPANIS** | 50-60 | Orta plan, M2 veranda | Miras cumlesi + **SORU** | ✅ |

**Yuz 1, 2 ve 6'da; eller 3, 4, 5'te.** Boylece yuz tutarliligi riski yariya
iner, is on planda kalir, ve orta klipler baska metinle tekrar kullanilabilir.

## 4.2 Replik butcesi — KLIP SURESINE BAGLI

**Earl yavas konusur: ~2.2 kelime/saniye.** Tavan = klip suresi × 2.2.

| Flow klip suresi | Replik tavani | 6 klip = toplam |
|---|---|---|
| 6 sn | **13 kelime** | 36 sn · ~78 kelime |
| 8 sn | **17 kelime** | 48 sn · ~105 kelime |
| **10 sn** | **22 kelime** | **60 sn · ~130 kelime** ← hedef |

⚠ **25 Agu 2026:** klip 4 yarim kaldi — replik 22 kelimeydi ama klip **6 sn**
uretilmisti. Metin dogru, sure yanlisti. **Uretimden once Flow'daki klip
suresini dogrula**; 60 sn'lik video icin **10 sn** secili olmali.

`earl_video.sh` sureyi parametre alir ve tavani ona gore hesaplar:
```bash
./earl_video.sh videolar/deterjan.txt 10   # tavan 22
./earl_video.sh videolar/deterjan.txt 8    # tavan 17
```

**Ikincil etki:** cok eylemli kliplerde (4+ beat) model harekete zaman
ayirir, konusmaya daha az yer kalir. Arac bu kliplerde tavani 3 kelime
kisiyor. Ayrica **eylemi sadelestir** — kurulum ve toparlama beat'lerini at:
"kaseyi getir, rendeyi getir, sabunu al, rendele, birak" yerine sadece
**"rendele"**; nesneler kadraja kendiliginden girer.

- Klip 6'da **tek soru** ile bitir — 45+ kitlede yorum = dagitim.

## 4.2b IKI ZORUNLU BLOK — 25 Agu 2026 olcumu

### (a) KIMLIK GORUNURLUGU — el planlarinda bile sakal kadrajda kalir
**Yasandi:** klip 5'in son karesinde kadraj gogusten asagi kaldi, **beyaz
sakal gorunmedi** — o karede karakter "sakalsiz biri" gibi okundu ve zincirin
kimligi kirildi.

**Kural:** el planlarinda bile kadrajin ust kenarinda **sakalin ucu ve tulum
askisi** gorunecek. Yuzun tamami gerekmiyor, **kimlik isareti** gerekiyor.
Her el planina su cumleyi ekle:

```
FRAMING: his short white beard and the bib of his denim overalls stay
visible at the top edge of the frame throughout the shot.
```

### (b) NESNE SUREKLILIGI — nesneler kaybolmasin
**Yasandi:** kadraja giren/cikan nesneler (kase, rende, torba, kavanoz)
plan icinde kayboluyor, yer degistiriyor ya da cogaliyor.

**Kok neden:** model sadece "ne yaptigini" biliyor, **nesnelerin nerede
oldugunu** bilmiyor. Eylemi tek cumlede yazarsan aradaki durumlari uyduruyor.

**Kural:** eylem cumlesi yetmez. Her plana **iki blok** yaz:

```
OBJECTS ON THE TABLE AT THE START, all already present and visible:
- <nesne> <tam yeri>
- ...

OBJECT CHOREOGRAPHY, in this exact order:
1. <hangi el> <hangi nesneyi> <nereden nereye> — <sonra nerede kalir>
2. ...

CONTINUITY: every object listed stays physically present in the frame for
the whole shot, in the same shape, size and colour. Nothing vanishes,
teleports, duplicates or changes.
```

**Uc alt kural:**
- Bir nesne kadraja **giriyorsa** hangi kenardan girdigini yaz
- Bir nesne **isini bitirdiyse** nerede kaldigini yaz ("returns to the table,
  now empty, and stays there") — yoksa model onu siliyor
- Nesne **markasiz** olmali; her blokta "no label, no text, no logo" tekrar et

⚠ Bu iki blok plani uzatir ama **konusma suresini yemez** — model icin tarif,
eylem degil. Yine de replik tavanini 2-3 kelime asagi cek.

## 4.2c KADRAJ START FRAME'DE KARARLASIR — 25 Agu 2026 olcumu

**Yasandi:** el planlarinda sakali kadraja sokmak icin plana
"camera pulls back and tilts up" yazildi. **Iki denemede de olmadi** — Flow
start frame'in kadrajini koruyor, plan ici kamera hareketi onu ezmiyor.

**Kural:** kadraj **plan icinde duzeltilmez, start frame'de kurulur.**
Bir plani farkli kadrajla istiyorsan onceki klibin son karesini kullanma;
**Image modunda yeni bir start frame uret** ve zinciri oradan devam ettir.

**Ne zaman zincir, ne zaman yeni capa:**
| Durum | Yontem |
|---|---|
| Ayni kadraj, eylem devam ediyor | onceki klibin **son karesi** |
| Kadraj degisecek (genis→yakin, el→yuz) | **yeni Image capasi** uret |
| Zincir kaydi, karakter/nesne bozuldu | **yeni Image capasi** uret |

Yeni capa uretirken nesnelerin **o andaki durumunu** tarif et (kase bos,
sabun kisalmis, kavanoz dolu) — yoksa hikaye geriye sarar.

## 4.3 Ust yazilar
Flow'a **yazdirilmaz** (bozuk yaziyor). Kurguda bindirilir:
1. Hook cumlesinin rakami — "$4 · 200 LOADS"
2. — (yazisiz, nefes)
3. "3 THINGS"
4. "1" / "2"
5. Sonuc rakami
6. Soru

## 4.4 Ornek — "Homemade laundry detergent"
Tanim dosyasi: `videolar/deterjan.txt` · Uret: `./earl_video.sh videolar/deterjan.txt`

| Klip | Hook tipi / islev | Replik |
|---|---|---|
| 1 | **A — fiyat** | "Four dollars. Two hundred loads of laundry. The store wants forty for the same thing, and theirs is mostly water." |
| 2 | dusman | "Read the back of that jug sometime. Water is the first word on it. You are paying to ship water." |
| 3 | malzeme | "Three things. A bar of plain soap. Washing soda. Borax. That is the whole list, and you can say every word of it." |
| 4 | yapim | "Grate the soap fine, like cheese. Takes about four minutes. Do it while the coffee is on and you will not notice." |
| 5 | sonuc | "One cup of each, in the jar, shake it good. One spoonful washes a full load. That jar will outlast the winter." |
| 6 | miras + soru | "My mother made this every fall, in this same kind of jar. I never bought a box of soap in my life. Did your mother make it too?" |

⚠ Klip 2'de magaza urunu **markasiz** tarif edilir ("plain unlabeled white
plastic jug"). Marka ismi ne promptta ne repliktе gecer —
`KONSEPT_AMERIKAN_KOYLU.md` Bolum 7'deki karalama riski.

================================================================
# BOLUM 5 — URETIM SIRASI
================================================================

1. Uc bloku dosyaya yaz: `earl_karakter.txt`, `earl_ses.txt`, `earl_stil.txt`
2. **3A** karakter sayfasini uret → arsivle, Flow'a verme
3. **3B** ingredient pozu uret → **yuzu begenene kadar tekrarla**
4. **3C** el capasini uret
5. **3D** dort mekan capasini uret
6. Flow ayari: **9:16 · Video · x1 · "Confirm before generating: NEVER"**
   (`flow_surucu.py` ayarliyor; `KURULUM.md` Adim 5.5)
7. 4 klibi uret — **her promptta ses blogunu dosyadan kopyala**
8. Klipleri birlestir, kurguda ust yazilari ve dusuk seviyeli ortam yatagini bindir
9. Altyazi: metni zaten biliyorsun (replikler) → `kurgu.py --metin --ses --altyazi`
   ile klipten cikan sesle hizala

**Adim 3'te acele etme.** Karakter capasi bir kez dogru kurulur; sonraki
100 video onun uzerine biner.
