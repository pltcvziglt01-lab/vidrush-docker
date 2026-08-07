# ThriftyHazel — kare kare ölçüm ve motor kıyası (5 Ağu 2026)

**Yöntem:** referans kanalın 5 videosu 480p indirildi, ffmpeg sahne-kesme ile 253 sahne
sınırı çıkarıldı, 3 sn'de bir 1111 kare örneklendi, 60 kare vision ile etiketlendi.
**Aynı ölçüm bizim bitmiş videomuza da uygulandı** (15.4 dk, 132 sahne, 308 kare) —
sayılar bire bir karşılaştırılabilir.

Ölçüm betikleri: `~/Desktop/stickman-referans/hazel_olc.py`, `hazel_vision.py`

## Kıyas tablosu

| Ölçüm | Hazel | Bizim video | Fark |
|---|---|---|---|
| Sahne süresi (medyan) | 12.8 sn | 6.8 sn | **2× hızlı** |
| 8 sn'den uzun sahne | %90 | %30 | |
| Parlaklık (0-255) | 162 | 123 | **−39 kademe** |
| Doygunluk | 52 | 83 | **+31** |
| Kontrast | 51 | 42 | −9 |
| Zoom hızı | %2.5/sn | %1.2/sn | **yarı hız** |
| Altyazı görünen kare | %98 | %0 | **hiç yok** |
| Görsel üstü başlık/sayı | %35 | %5 | **7× az** |
| Karaktersiz kare | %42 | %47 | ✓ eşleşiyor |
| Orta plan (bel üstü) | %17 | %0 | **dağılımda delik** |
| Yakın + çok yakın | %7 | %14 | ✓ yeterli |
| Geniş + çok geniş | %77 | %86 | biraz fazla |
| İç mekân | %92 | %100 | ✓ |

## Diğer kanalların temposu (aynı yöntem, 339 sahne)

| Kanal | Medyan sahne | Not |
|---|---|---|
| ThriftyHazel | 12.8 sn | %90'ı 8 sn üstü |
| Aussie Bruce | 11.9 sn | %98'i 8 sn üstü |
| Paint Explainer | 5.0 sn | iki modlu |
| Simple Explainer | 2.8 sn | %53'ü 3 sn altı |

Tek bir `ANIM_SAHNE_SN=5` sabiti bu dört kanalın hiçbirine uymuyordu.

## Yapılan düzeltmeler

| # | Düzeltme | Nerede |
|---|---|---|
| T1 | Sahne temposu stil başına ayrıldı (9/5/9/12/12 sn) | `pipeline.py` profiller |
| T2 | Zoom miktarı sahne süresine bağlandı (`SURE_ZOOM`, %2.2/sn, tavan 1.26) | `Video.tsx` |
| T3 | 4 animasyon stilinde altyazı açıldı | `pipeline.py` profiller |
| T4 | Kalıcı geri sayım rozeti (sahne boyunca sol üstte) | `Video.tsx` + `hizli_render.py` |
| T5 | Çekim ölçeği sözleşmesi ölçülen dağılımla yazıldı (orta plan %20) | `CEKIM_OLCEGI` |
| T6 | Kontrast da renk uydurmaya eklendi (yarı yol, ±%15) | `renk_uydur()` |

## Kendi hatam — kayda geçsin

**Görev #27 yanlış yöndeydi.** "39 sahne 8 saniyeden uzun" diye kusur yazıp sahneleri
kısaltmıştım. Ölçüm bunun tersini söylüyor: referansın %90'ı zaten 8 sn'den uzun.
Kullanıcı hiçbir zaman "sahneler uzun" demedi — o maddeyi ben uydurdum.

**Görev #23 kısmen yanlış teşhisti.** "Yakın plan yok" demiştim; ölçüm bizim yakın plan
oranımızın (%14) referanstan (%7) zaten yüksek olduğunu gösterdi. Gerçek boşluk **orta
plan**: bizde %0, referansta %17. Düzeltme yakınlaştırmak değil, orta planı eklemek.

## Maliyet etkisi

Sahne 5 → 12 sn: 11 dk'lık bir ani-defteri videosu ~130 görsel yerine **~55 görsel**.

Animasyon stilleri `GORSEL_MODEL_ANIM = gpt-image-1-mini` kullanıyor → **$0.013/görsel**
(belgesel tarafındaki `gpt-image-2` $0.048 DEĞİL — ilk yazımda bunu karıştırmıştım).
Yani görsel maliyeti **~$1.69 yerine ~$0.72**.
