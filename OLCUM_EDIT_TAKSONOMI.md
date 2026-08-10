# Edit taksonomisi — 20 referans video (7 Ağu 2026)

**Yöntem:** 20 video sunucuda 360p indirildi, ölçüldü, **silindi** (Mac'e hiç inmedi).
Toplanan: 32.693 saniye karesi (1 fps) + 3.144 geçiş karesi (kesme çevresi dörtlüleri)
+ 1.120 hareket karesi (çekim içi dörtlüler). 3 paralel ajan analiz etti.

Kanallar: Zero Reports (4), Navy Decoded (4), NextGen Manufacturing (4), Atrium (4),
Auralis (2), ECHOES (1), Made Vision (1). Toplam ~9.5 saat, 0.7-9.9M izlenme.

---

## 1. GEÇİŞLER — 786 kesme etiketlendi (0 başarısız)

| Tip | % |
|---|---|
| **sert-kesme** | **79.9** |
| karartma | 7.6 |
| beyaz-flash | 4.1 |
| whip-pan | 3.3 |
| crossfade | 2.2 |
| wipe | 1.1 |
| zoom-through | 1.0 |
| match-cut | 0.3 |

**Bu nişte geçiş = sert kesme.** Süslü geçişlerin (wipe + zoom-through + match-cut)
toplamı %2.4 — pratikte yok.

**Piksel doğrulaması** (vision'dan bağımsız, 786/786): sert-kesmede a≈b ve c≈d
(fark 8), b→c'de kopma (57). Karartmada c karesi parlaklığı 88→44'e düşüyor,
flash'ta 125→152'ye çıkıyor. Yani etiketler uydurma değil, ölçümle tutarlı.

### Kanal imzaları
| Kanal | İmza | Oran | Genel ortalamaya göre |
|---|---|---|---|
| ZeroReports | karartma | %23.1 | **×3.0** |
| NavyDecoded | flash + zoom-through + whip | %10.3 / %4.8 / %6.2 | ×2.5 / ×4.7 / ×1.9 |
| Auralis | saf sert kesme | %97.5 | tek efekt yok |
| ECHOES | whip-pan | %7.5 | ×2.3 |
| Atrium | whip-pan | %5.6 | ×1.7 |
| MadeVision | crossfade | %7.5 | ×3.4 (n=3, zayıf sinyal) |

### KENDİ HATAM
5 Ağu'da anlatım işlevine **6 farklı geçiş** bağlamıştım (liste→slideleft,
gecmis→fadegrays, vurgu→wipeleft, karsilastir→hlslice, soru→smoothleft, sonuc→fadeblack).
Bu, kesmelerin neredeyse tamamına efekt koyuyordu — **referansın tam tersi.**
Düzeltildi: varsayılan sert kesme, stil başına tek imza efekti ölçülen oranda.

---

## 2. EKRANDAKİ YAZI — 935 kare etiketlendi

### Kritik ayrım: filigran ≠ bilgi yazısı
| Kanal | kalıcı logo | gerçek bilgi yazısı |
|---|---|---|
| MadeVision | %44 | %15 |
| NextGen | %48 | **%0** |
| ZeroReports | %14 | %60 |

### KENDİ HATAM
Daha önce 196 karelik ölçümle "küçük etiket %39-50, baskın tür bu" demiştim. **Yanlıştı** —
MadeVision/NextGen'in kalıcı köşe logosunu "küçük etiket" saymışım. Filigran ayrılınca
gerçek dağılım (yazılı karelerin içinde, n=254):

| Tür | % | Ölçülen ömür |
|---|---|---|
| **alt-band (lower third)** | **33** | 4.7 sn (max 10) |
| büyük başlık | 28 | 9.0 sn (medyan 16) |
| küçük etiket | 20 | **1.8 sn** (medyan 1) |
| veri-sayı | 12 | 2.9 sn |
| altyazı | 5 | 3.0 sn |
| bölüm kartı | 2 | 3.0 sn |

Yani en çok kullanılan tür **alt-band**, küçük etiket üçüncü sırada ve **çok kısa ömürlü**.

### Yazı yoğunluğu bimodal — ortalama almak yanlış
Auralis/NextGen %0, ZeroReports %60. Toplam %27 ama ortalamayı hedeflemek hiçbir kanala
benzemez. Kanal profili seçilmeli.

### Giriş animasyonu: 0.3 sn'yi geçmemeli
382 yazılı karenin sadece **%1.8'i** yarıyolda yakalandı → referans animasyonları
**0.5 sn'nin altında.** 1 sn'lik fade koysak aynı ölçümde %15-25 çıkar, yani gözle
"yavaş/amatör" görünür.

### Tempo
Yeni yazı 8-10 sn'de bir. Yazı kapandıktan sonra en az 3 sn temiz.

---

## 3. GRAFİK — %84 kare grafiksiz

| Tür | % |
|---|---|
| **çerçeve-vurgu** | **10** |
| harita | 3 |
| ok-callout | 1 |
| çizelge | 1 |
| bölünmüş ekran | 1 |
| zaman çizelgesi | **0** |

**Grafik yazısız konmuyor:** grafik varken %72 olasılıkla yanında yazı da var.
Zaman çizelgesi ve bölünmüş ekran yapılmamalı.

---

## 4. KAYNAK TÜRÜ

| Tür | % | Not |
|---|---|---|
| modern video | 73 | omurga |
| 3D render | 11 | Atrium tek başına %36 |
| arşiv film (hareketli) | 8 | ZeroReports %23 |
| animasyon | 6 | Atrium %26 |
| **arşiv fotoğraf** | **1** | pratikte kullanılmıyor |

Statik arşiv fotoğrafı yerine **hareketli arşiv film** tercih ediliyor.

---

## 5. KAMERA HAREKETİ — 246 çekim ölçüldü (piksel eşleştirme, NCC)

| Kanal | zoom-in | zoom-out | sabit | pan | \|zoom\| medyan |
|---|---|---|---|---|---|
| ZeroReports | 64% | 5% | 26% | 5% | 1.52%/sn |
| NavyDecoded | 23% | 23% | 19% | 35% | 1.27%/sn |
| NextGen | 50% | 15% | 25% | 10% | 3.04%/sn |
| Atrium | 62% | 19% | 6% | 12% | 3.38%/sn |
| Auralis | 55% | 10% | 10% | 25% | 0.92%/sn |
| **TOPLAM** | **50%** | **14%** | **18%** | **18%** | **1.61%/sn** |

Zoom'lu çekimlerin **%78'i zoom-in.**

### Üç düzeltme

**A. Hız:** bizim `%2.2/sn` medyanın %40 üstündeydi → **%1.8/sn**, tavan 1.26 → **1.38**
(referansta 12 sn+ çekimler 1.32-1.47'ye çıkıyor, eski tavan uzun sahneyi kısıtlıyordu).

**B. Dağılım, ortalama değil.** Referansta hız tek değer değil:
%34 ihmal edilebilir (<0.5%/sn), %39 sakin (0.5-2), %14 belirgin (2-5), %12 agresif (>5).
Bizim motor her sahneye aynı hızı veriyordu → "hep aynı kamera" hissi. Artık sahne
indeksinden deterministik kova seçiliyor.

**C. Easing referansa tersti.** Rampa ölçümü (n=134): 1. çeyrek %1.22/sn, 2. çeyrek %1.14,
3. çeyrek %1.26 → **son/ilk = 1.03, yani sabit hız, lineer.** Bizim `bezier(0.33,0,0.2,1)`
hareketin ~7 katını ilk çeyreğe yığıyordu. Lineere yakın eğriye geçildi.

**D. in/out oranı:** 4 Ağu'da sık işlevleri `i % 2` ile 50/50 alternatiflemiştim — tekrar
hissini çözdü ama oranı bozdu. Referans 78/22 → düzeltildi (doğrulama: %79/21).

**E. Durgun kare:** referansta %18-20 çekimde kamera durgun, bizde her sahnede zoom vardı.
Ama onların durgun çekimi **canlı footage**; bizde durgun = donmuş kare (referansta o
sadece %2). Bu yüzden %20 değil **%12** hedeflendi (doğrulama: %12).

---

## Motora giren değerler

| Ayar | Eski | Yeni | Kaynak |
|---|---|---|---|
| Geçiş varsayılanı | işlev bazlı 6 efekt | **sert kesme** | %79.9 |
| Stil imzası | — | karartma/flash, %8-20 | kanal imzaları |
| Zoom hızı | %2.2/sn sabit | **%1.8/sn + 4 kovalı dağılım** | medyan %1.57 |
| Zoom tavanı | 1.26 | **1.38** | 12 sn+ çekimler 1.32-1.47 |
| Ken Burns easing | bezier ön yüklemeli | **lineere yakın** | son/ilk = 1.03 |
| in/out | 50/50 | **78/22** | %78 in |
| Durgun kare | %0 | **%12** | %18-20 (canlı footage payı düşülerek) |
| Yazı türü | küçük etiket | **alt-band birinci** | %33 vs %20 |
| Küçük etiket ömrü | sahne sonuna kadar | **1.8 sn** | medyan 1 sn |
| Yazı giriş animasyonu | 0.42-0.6 sn | **0.28 sn** | %1.8 yakalanma |
| Yazı oranı | %40-50 | **%24-28** | bimodal, profil bazlı |
| Kalıcı köşe logosu | yok | **var (ayrı katman)** | 2/7 kanal |

## Ham veri (sunucuda)
- `/root/gecis_sonuc.jsonl` — 786 geçiş etiketi
- `/root/piksel.jsonl` — 786 geçişin piksel ölçümü
- `/root/bedosaho-veri/veri/_yazi_ornek_agent3*/` — 935 yazı/grafik etiketi
- `/tmp/hrk_sonuc2.json`, `/tmp/hrk_ozet2.json` (konteyner) — hareket ölçümü
- `/root/tekno/<kanal>/<video>/` — 36.957 kare
