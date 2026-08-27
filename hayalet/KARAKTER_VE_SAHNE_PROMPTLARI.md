# ANA KARAKTER + SAHNE PROMPT SISTEMI
Kaynak analiz: hayalet/RAKIP_STIL_STICKOOPS.md
Yontem: her plan = START FRAME gorsel + END FRAME gorsel + VIDEO promptu

================================================================
## BOLUM 1 — ANA KARAKTER REFERANSI  (BIR KEZ URET, HER PROJEDE KULLAN)
================================================================

Karakterimizin adi: **BOBO**

Rakipten ayrildigi 5 kucuk nokta (kasitli, telif/klon gorunmemek icin):
1. Kafa daha yuvarlak — tam daireye yakin, altta hafif duz bir cene hatti
2. Gozlerde 2 degil **3 parlama noktasi**, gozler birbirine biraz daha yakin
3. Kontur firca gibi **hafif kalinlasip incelen** cizgi (rakipte tamamen duz)
4. Eller yumruk-eldiven degil, **basparmak centigi olan** kucuk beyaz eldiven
5. Ayaklarin altinda **yumusak gri elips golge** (rakipte golge yok)

----------------------------------------------------------------
### 1A. KARAKTER SAYFASI PROMPTU  (arsiv/referans — bunu uret ve sakla)
----------------------------------------------------------------

```
Character reference sheet on a plain flat light-grey background (#E8E6E1),
no scene, no props, no text labels, no watermark.

CHARACTER "BOBO": a pure white cartoon stickman. His head is a large, almost
perfect circle with a subtly flattened chin line, and it is about 1.6 times
wider than his body. He has no ears, no nose, no hair and no clothes — his body
is a smooth white bulb/pear shape with narrow shoulders. His arms and legs are
thin solid black lines that end in small white oval mitten hands with a visible
thumb notch, and white oval shoe-shaped feet. His eyes are two large round
white circles with big black pupils and THREE small white highlight dots each,
set slightly close together. Two thin black eyebrow arcs sit above them. His
mouth is a black outline shape with a soft red tongue inside. A soft grey
elliptical contact shadow sits under his feet.

LINE STYLE: bold black outlines with a slight brush taper — thicker at the
bottom of each shape, thinner at the top. Flat cel-shaded fills, no gradients,
no texture, no noise.

LAYOUT: a clean grid of poses of the SAME character, all identical in design:
row 1 — full body front view, full body 3/4 view, full body side view, full
body back view; row 2 — head close-ups showing six expressions: calm smile,
wide-eyed shock, screaming with mouth wide open and red tongue visible, sleepy
half-closed eyes, smug grin, sad droopy eyes; row 3 — the two hands and the two
feet drawn separately, plus a running pose with speed lines.

Vector-clean 2D cartoon illustration, high resolution, evenly lit, no shading
on the background.
```

----------------------------------------------------------------
### 1B. INGREDIENT / REFERANS POZ PROMPTU  (Flow'a besleyecegin tek gorsel)
----------------------------------------------------------------
Flow'un "ingredients" alanina karakter sayfasi degil, TEK TEMIZ POZ ver —
grid verirsen Flow bazen grid'i sahneye kopyaliyor.

```
Full body front view of "BOBO", a pure white cartoon stickman, standing
relaxed and centered on a plain flat light-grey background (#E8E6E1).
Large almost-circular head with a subtly flattened chin, about 1.6x wider
than his bulb-shaped white body. No ears, no nose, no hair, no clothes.
Thin solid black line arms and legs ending in small white oval mitten hands
with a thumb notch and white oval shoe feet. Two large round eyes with big
black pupils and three white highlight dots each, set slightly close together.
Thin black eyebrow arcs. Small closed smile. Soft grey elliptical shadow under
his feet. Bold black outlines with a slight brush taper, flat cel-shaded fills,
no gradient, no texture. Vertical 9:16 frame, nothing else in the image,
no text, no watermark.
```

----------------------------------------------------------------
### 1C. HER PROMPTA YAPISTIRACAGIN KISA KARAKTER BLOGU
----------------------------------------------------------------
(Referans gorsel kullansan bile bunu yazmaya devam et — Flow unutuyor.)

```
BOBO = a pure white cartoon stickman with a large almost-circular head (1.6x
wider than his bulb body), no ears, no nose, no hair, no clothes, thin black
line limbs ending in small white oval mitten hands and white oval shoe feet,
two big round eyes with black pupils and three white highlight dots, thin black
eyebrow arcs, black-outlined mouth with a red tongue inside, soft grey shadow
under his feet, bold tapered black outlines, flat cel shading.
```

----------------------------------------------------------------
### 1D. HER PROMPTA YAPISTIRACAGIN STIL BLOGU
----------------------------------------------------------------

```
STYLE: 2D flat cartoon animation, bold tapered black outlines, cel-shaded with
no texture or gradient. Desaturated warm-grey palette — muted beige walls,
grey-brown wood floor — with ONE accent colour: mustard yellow. Soft overhead
spotlight with darkened vignette corners. Vertical 9:16, 24fps, static camera.
NEGATIVE: no text overlay, no subtitles, no watermark, no realistic shading,
no 3D render, no photoreal, no second character, no camera shake, no zoom.
```

================================================================
## BOLUM 2 — SAHNE URETIM SISTEMI (3 PROMPT / PLAN)
================================================================

Her PLAN icin 3 prompt yazilir:

  P1  START FRAME  -> gorsel uretimi (planin ILK karesi)
  P2  END FRAME    -> gorsel uretimi (planin SON karesi)
  P3  VIDEO        -> Flow frames-to-video (ikisi arasindaki HAREKET)

### Demir kurallar
1. **START ve END ayni mekan, ayni kadraj, ayni isik olmali.** Degisen tek sey
   karakterin pozu/ifadesi ve tek bir prop. Kadraji degistirirsen Flow arada
   morph yapip bozuyor.
2. **P3 sadece HAREKETI anlatir.** "Kirmizi yorgan", "sari duvar" gibi
   betimlemeleri P3'e tekrar yazma — start frame zaten soyluyor. P3'e
   betimleme yazarsan Flow sahneyi yeniden kurmaya calisiyor.
3. **P3 mutlaka `static camera` icersin.** Veo kendiliginden kamera oynatiyor.
4. **Devamlilik zinciri:** Plan N'in END FRAME gorselini, Plan N+1'in
   START FRAME'i olarak AYNEN kullan (yeniden uretme). Kesme goze batmaz.
5. Klip ~8-10 sn cikar; CapCut'ta plan basina **1.5-3.5 sn**'ye kirp.
   Toplam hedef: 10 sn.
6. Ekrana yazi BASMA. Metin sadece prop uzerinde olsun (telefon, takvim, saat).

================================================================
## BOLUM 3 — TAM ORNEK: "PAZAR" REEL'I (4 plan, 10 sn)
================================================================
Her P1/P2'nin basina 1C KARAKTER + 1D STIL bloklarini ekle.

----------------------------------------------------------------
PLAN 1 — Sakin acilis  (kurguda 2.0 sn)
----------------------------------------------------------------
P1 START FRAME:
```
Wide shot of a small tidy bedroom seen from the side. BOBO lies asleep in a
single wooden bed under a mustard yellow blanket, head on a white pillow, eyes
closed in a calm content smile. A black digital alarm clock on the nightstand
shows "8:47 AM" in glowing green digits. Beige walls, three small framed
pictures, grey-brown wood floor, warm morning light from the right, soft
vignette. Vertical 9:16.
```
P2 END FRAME:
```
The exact same wide shot of the same bedroom, same framing and lighting.
BOBO is still lying in bed but his eyes are now WIDE OPEN, both pupils shrunk
to tiny dots, eyebrows shot up, mouth open in silent shock. Two yellow impact
flash marks beside his head. The alarm clock still shows "8:47 AM".
Vertical 9:16.
```
P3 VIDEO:
```
Static camera. BOBO sleeps peacefully for a moment, then his eyes snap wide
open and his pupils shrink as he registers the clock. Yellow impact flashes pop
beside his head. Nothing else in the room moves. 2D cartoon animation,
static camera, no zoom, no pan.
```

----------------------------------------------------------------
PLAN 2 — Panik aksiyonu  (kurguda 3.0 sn)
----------------------------------------------------------------
P1 START FRAME = PLAN 1'in END FRAME gorseli (aynen kullan)
P2 END FRAME:
```
The same bedroom, same framing and lighting. The bed is now empty with the
mustard yellow blanket thrown into a crumpled heap. BOBO is standing on the
wood floor mid-stride running toward the door on the right, body leaning
forward, mouth wide open screaming with the red tongue visible, sweat drops
flying off his head, thick horizontal black speed lines and a small grey dust
puff behind his feet. Vertical 9:16.
```
P3 VIDEO:
```
Static camera. BOBO explodes out of the bed, the blanket flies off and lands
crumpled, and he sprints toward the door screaming with sweat drops flying.
Speed lines and a dust puff trail behind him. Exaggerated squash-and-stretch
cartoon motion. 2D cartoon animation, static camera, no zoom, no pan.
```

----------------------------------------------------------------
PLAN 3 — Prop punch-in  (kurguda 2.5 sn)
----------------------------------------------------------------
P1 START FRAME:
```
Close-up shot. BOBO stands frozen by the bedroom door, holding a mustard yellow
smartphone in both mitten hands, screen turned away from us. His face fills the
upper half of the frame, mouth open mid-scream, eyebrows raised, sweat drops in
the air. Blurred beige bedroom wall behind him. Vertical 9:16.
```
P2 END FRAME:
```
Extreme close-up of the same mustard yellow smartphone held by BOBO's two white
mitten hands, now tilted toward us so the screen fills about 60% of the frame.
The screen shows a clean white calendar grid with one day highlighted in a
mustard yellow box reading "SUNDAY" in bold black letters. BOBO's two huge eyes
peek over the top edge of the phone, pupils shrunk to dots. Vertical 9:16.
```
P3 VIDEO:
```
Static camera. BOBO stops dead, turns the phone toward us and freezes as he
reads the screen. His scream dies, his mouth closes, his pupils shrink.
2D cartoon animation, static camera, no zoom, no pan.
```

----------------------------------------------------------------
PLAN 4 — Ters kose kapanis  (kurguda 2.5 sn)
----------------------------------------------------------------
P1 START FRAME = PLAN 3'un END FRAME gorseli (aynen kullan)
P2 END FRAME:
```
Wide shot of the same bedroom, warm morning light, soft vignette. BOBO stands
alone in the middle of the wood floor with his arms hanging limp at his sides,
the yellow phone dangling from one hand, eyes half-closed and droopy, mouth a
flat tired line. The bed behind him is empty with the mustard blanket crumpled.
Vertical 9:16.
```
P3 VIDEO:
```
Static camera. BOBO slowly lowers the phone, his shoulders sag, his eyes droop
half-closed and he stands motionless in the empty room, deflated.
2D cartoon animation, static camera, no zoom, no pan.
```

================================================================
## BOLUM 4 — KURGU & SES (CapCut)
================================================================
- Plan sureleri: 2.0 / 3.0 / 2.5 / 2.5 = 10.0 sn
- Duz cut, gecis efekti YOK
- Konusma YOK, altyazi YOK
- 1 loop komedi muzigi + SFX: alarm, yatak giciridi, kosma adimlari, whoosh,
  telefon bildirimi, kapanista tek "sad trombone" sting
- Punchline'da (Plan 3 sonu) 0.3 sn tam sessizlik, sonra sting
- Hedef loudness: -14 LUFS
