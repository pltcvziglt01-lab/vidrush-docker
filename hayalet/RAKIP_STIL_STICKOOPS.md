# RAKIP STIL ANALIZI — "StickOops" (stickman komedi reels)

Kaynak: 3 indirilmis reel (snapsave 1712944096427250 / 863444553489207 / 1531325178142810)
Analiz: 23 Agu 2026 — ffprobe + kare/spektrum incelemesi.

## 1. TEKNIK PARMAK IZI (olculdu, tahmin degil)

| Olcum | v1 (ruyada tuvalet) | v2 (alarmdan once uyandim) | v3 (Pazar) |
|---|---|---|---|
| Sure | 10.146 sn | 10.146 sn | 10.111 sn |
| FPS | 24 | 24 | 24 |
| Kare sayisi | 240 | 240 | 240 |
| Cozunurluk | 480x1024 | 604x1276 | 720x1280 |
| Ses | AAC 44.1k stereo | ayni | ayni |
| Kesme sayisi | 3 plan | 5 plan | 4 plan |
| Kesme anlari | 4.00 / 9.33 sn | 1.50 / 2.17 / 2.92 / 8.38 sn | 5.83 / 6.96 / 8.42 sn |

**En kritik bulgu:** ucu de ~10.1 sn ve tam 240 kare @24fps. Bu Veo/Flow'un
standart 8-10 sn cikti uzunlugu. Yani her reel = **1-2 Flow uretimi + kurgu**,
uzun bir animasyon degil. Bizim icin ulasilabilir maliyet demek.

**Diger bulgu:** hicbirinde konusma yok. Spektrumda insan konusmasi formant
deseni yok; 0-2 kHz'de armonik "cizgi film SFX" patlamalari ve 13.2 kHz'de
low-pass duvari var (muzik + SFX katmani). Yani **seslendirme yok, yazi yok** —
hikaye tamamen gorsel. Ekrandaki tek metin prop uzerinde (telefon "06:00",
"10:47 AM", takvim "SUNDAY", calar saat "8:47 AM").

## 2. KARAKTER ANAYASASI (her karede sabit)

- Beyaz, hafif oval kafa; **kafa govdenin ~1.6 kati** genislikte (buyuk kafa)
- Kulak yok, burun yok, sac yok, giysi yok — saf beyaz siluet
- Kontur: **kalin, duz siyah, degisken kalinlikta** (kafa konturu govde konturundan kalin)
- Govde: beyaz ampul/armut formu; kollar-bacaklar **ince siyah cizgi**,
  uclarinda **beyaz oval eldiven/ayakkabi** (siyah cizgi cikip beyaz baloncukla biter)
- Gozler: iki buyuk daire, siyah bebek + 2-3 beyaz parlama noktasi.
  Duyguya gore pupil kuculur (sok) / buyur (mutluluk)
- Kas: sadece ince siyah yay; sok anlarinda kalkik, uzgunde egik
- Agiz: siyah konturlu, iceri **kirmizi/pembe dil** — bagirirken agiz kafanin
  %40'ini kaplar
- Ter damlalari, hiz cizgileri, "!!" isaretleri: klasik manga/cizgi film effect kiti

## 3. ARKA PLAN & RENK ANAYASASI

- 2D cel-shading, kalin siyah kontur, dokusuz duz alanlar
- **Cok dusuk doygunluk.** Olculen kare ortalamalari R≈G≈B (orn. `aea188`,
  `6e6b63`, `9b917b`) — yani sicak-gri, pastel-kirik renk paleti.
  Sebep: beyaz karakterin arka plandan patlamasi.
- Tek vurgu rengi: **hardal/altin sari** (yorgan, telefon kilifi, takvim vurgusu).
  Ikincil: turkuaz (banyo), kahve (kapi/parke).
- Isik: tavandan gelen **yumusak spot/vinyet** — kadrajin kenarlari koyulasir,
  karakterin oldugu yer parlaktir.
- **Renk = anlati araci.** v2'de 5.→6. saniyede kare ortalamasi `49483f`'ten
  `9b917b`'ye zipliyor: gece grisi -> sabah sicagi. Ayni odada renkle zaman
  gectigini anlatiyor.

## 4. HIKAYE FORMULU (3 videoda da ayni iskelet)

10 saniye, 4 beat:

1. **0.0-1.5 sn — SAKIN ACILIS.** Karakter yatakta/normal. Kadraj: geniş plan,
   oda tamamen gorunur. Izleyici mekani bir bakista anliyor.
2. **1.5-3.0 sn — TETIK.** Bir prop devreye giriyor (telefon, calar saat,
   sikisan mesane). **Prop'a sert punch-in** — telefon ekrani kadrajin
   %60'ini kapliyor, uzerinde okunakli buyuk yazi.
3. **3.0-8.0 sn — TEPKI + AKSIYON.** Abartili kosma, ziplama, panik.
   Hiz cizgileri, toz bulutu, ayak/vucut deformasyonu (squash-stretch).
4. **8.0-10.1 sn — TERS KOSE (punchline).** Beklenenin tersi olur ve
   **yuze cok yakin zoom** ile biter (sok yuzu / mutlu yuz).
   v1: banyoya yetisti -> aslinda ruyaydi, yataga isedi.
   v2: alarmdan once uyandi -> tekrar uyudu, 10:47 oldu.
   v3: geç kaldi diye deliriyor -> gun Pazar.

**Formul:** *gunluk hayatta herkesin yasadigi mikro-aci -> abartili panik ->
son 2 saniyede tersine donen bilgi.* Diyalog gerekmiyor, bu yuzden dil
bariyeri yok — global izlenme aliyorlar.

## 5. KAMERA & KURGU GRAMERI

- Cogunlukla **sabit kamera**, cok yavas push-in (Ken Burns degil, gercek 3D his yok)
- Kesmeler duz cut, gecis efekti yok
- **Punch-in kesme** ana araclari: geniş plan -> ayni anin yakin plani.
  Ortalama plan suresi 2-3 sn, son plan 1.5-2 sn
- Son karede yuz kadrajin ~%70'ini kapliyor (thumbnail/loop icin)
- Video dikey 9:16 ama karakter **orta banda** yerlestirilmis — ust ve alt
  %15 (TikTok/Reels UI alani) bos birakilmis

## 6. SES TASARIMI

- Konusma yok
- Hafif dongusel komedi muzigi (dusuk seviye, sureklilik)
- Ustune 4-6 adet nokta SFX: alarm zili, yatak giciridamasi, kosma adimlari,
  "whoosh", su sesi, "record scratch" / dramatik sting punchline'da
- Punchline aninda **muzik kesilir**, tek bir sting kalir — spektrumda
  8.4-8.7 sn arasi bosluk sonra 8.7'de armonik patlama olarak gorunuyor

---

# FLOW ILE UYGULAMA PLANI

## Neden yapilabilir
Her video 10 sn ve 3-5 plan. Flow'da **her plan ayri bir uretim** olmali
(Flow tek promptta kesme yapmaz, yaparsa da kontrolsuz). Yani:
`1 reel = 3-5 Flow klibi + CapCut'ta birlestirme` — mevcut `flow_surucu.py`
+ `kurgu.py` hattimiz tam olarak bunu yapiyor.

## KRITIK: karakter tutarliligi
Flow onceki kareyi hatirlamaz. Iki secenek:
1. **Her promptta tam gorunus tarifi** (asagidaki KARAKTER blogu birebir
   her plana yapistirilir) — `beyin.py`'nin karakter enjeksiyonu bunu yapiyor.
2. **Frames-to-video / ingredients**: ilk plandan bir kare alip sonraki
   planlara referans gorsel olarak vermek. Daha tutarli, daha yavas.
   Uzun serilerde bunu kullan.

## STIL ANAYASASI BLOGU (promptlara sabit eklenecek — EN)

```
STYLE (FIXED, every shot): 2D flat cartoon animation, thick uniform black
outlines, cel-shaded with no texture or gradient noise. Desaturated warm-grey
palette (muted beige walls, grey-brown wood floor); ONE accent colour: mustard
yellow. Soft overhead spotlight with darkened vignette corners. Clean vector
look, 24fps, vertical 9:16.

CHARACTER (FIXED, every shot): a pure white stickman with a large oval head
(head is ~1.6x wider than the body), no ears, no nose, no hair, no clothes.
Thin black line arms and legs ending in small white oval mitten hands and
white oval shoe feet. Two large round eyes with big black pupils and two white
highlight dots. Thin black eyebrow arcs. Mouth drawn as a black outline with a
red tongue inside; it opens to cover 40% of the face when screaming. Exaggerated
squash-and-stretch, cartoon sweat drops and speed lines.

NEGATIVE: no text overlay, no subtitles, no watermark, no realistic shading,
no 3D render, no photoreal, no extra characters, no camera shake.
```

## PLAN PROMPT SABLONLARI (10 sn = 4 plan)

**Plan 1 — sakin acilis (2.5 sn)**
```
video: wide shot of a small bedroom, the stickman lies asleep in bed under a
mustard yellow blanket, eyes closed with a calm smile, static camera, dim
night lighting.
```

**Plan 2 — tetik / prop punch-in (2.0 sn)**
```
video: extreme close-up of a yellow smartphone held by two white mitten hands,
the screen fills most of the frame showing "06:00" in large black digits,
the stickman's shocked face partly visible behind it, static camera.
```

**Plan 3 — abartili tepki (3.5 sn)**
```
video: medium shot, the stickman leaps out of bed and sprints toward the door
in total panic, mouth wide open screaming with red tongue visible, sweat drops
flying, thick horizontal speed lines and a dust cloud behind him, camera static.
```

**Plan 4 — ters kose / kapanis (2.0 sn)**
```
video: extreme close-up of the stickman's face filling the frame, huge round
eyes with shrinking pupils, eyebrows raised, jaw dropped in silent horror,
slow push-in, plain blurred bedroom behind.
```

## SES (Flow disinda, CapCut'ta)
- Konusma EKLEME. Formulun gucu sessiz olmasi.
- 1 loop komedi muzigi (-20 LUFS civari) + nokta SFX
- Punchline'da 0.3 sn tam sessizlik, sonra tek sting
- Hedef entegre loudness: -14 LUFS (Reels/TikTok standardi)

## KACINILACAKLAR (rakipte olmayan seyler)
- Ekrana altyazi/baslik basma — onlar basmiyor, prop uzerine yaziyor
- Doygun/canli renk — palet mat kalmali, yoksa beyaz karakter kayboluyor
- Kamera hareketi (dolly, orbit) — Veo bunu sever, promptta `static camera`
  yazip bastirmak lazim
- 10 sn'yi asma. Formul 10 sn icin kalibre.

## SONRAKI ADIM
`hayalet/bot.py` `/senkron` akisinda:
- Karakter alanina yukaridaki CHARACTER blogunu ver
- Plan promptlarini `video:` onekiyle satir satir gonder (4 satir)
- Seslendirme adiminda ses gonderme yerine sessiz/muzik akisini kullan
