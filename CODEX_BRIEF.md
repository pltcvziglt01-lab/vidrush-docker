# BEDOSAHO AI — Codex devir brief'i
_11 Ağustos 2026. Bu dosya, sistemi hiç görmemiş bir geliştiricinin/ajanın devam edebilmesi için yazıldı._

---

## 0. Sistem tek cümlede

Metin girilir, **faceless YouTube belgesel videosu** çıkar: LLM planı → seslendirme → gerçek stok footage → ffmpeg/Remotion kurgu → 1080p mp4 + kapak. Rakip referansı **Vidrush.ai** (dakika başına $1.93–2.72 satıyor); bizim maliyetimiz ~**$3/30 dk video**.

**Ürünün ayırt edici iddiası:** kurgu kararları tahminle değil, **rakip kanalların ölçümüyle** belirleniyor (bkz. `OLCUM_EDIT_TAKSONOMI.md` — 20 video, 32.693 saniye karesi, 786 etiketli geçiş).

---

## 1. Mimari

```
Kullanıcı (tarayıcı)
   │  POST /api/generate  (multipart form)
   ▼
webapp/server.py         FastAPI + tek işçili kuyruk (ISCI_SAYISI)
   │
   ▼
webapp/pipeline.py       4166 satır — ANA HAT
   ├─ plan (gpt-4.1-mini, JSON)            → sahne listesi
   ├─ satirlari_uzat()                     → süre tutmuyorsa satırları uzat
   ├─ uret_seslendir()                     → edge-tts (bedava) / OpenAI TTS / ai33
   ├─ kaynak.footage_getir()               → gerçek video klip
   ├─ (AI görsel — belgesel stilinde YASAK)
   ├─ efekt_ata() / gecis_imza_sec()       → deterministik efekt ataması
   └─ render:
        RENDER_MOTOR=ffmpeg → webapp/hizli_render.py   (1.57x gerçek zaman)
        aksi halde          → Remotion (app/render-studio)  (7.86x — yavaş)
   ▼
webapp/ciktilar/<job>.mp4  +  _kapak.png
```

**Kritik mimari gerçek:** iki render yolu var ve **varsayılan ffmpeg**. Remotion'daki `Efektler.tsx` (35 bileşen) ffmpeg yolunda çalışmaz. 11 Ağu'da 17 efektin ffmpeg karşılığı yazıldı (`hizli_render._efekt_ffmpeg`), ama **tam eşitlik yok** — `suzulme`, `donme-3d`, kinetik başlık, `EditPaketi.tsx` grafikleri (beyaz-tuval/ölçü/alıntı/harita) hâlâ sadece Remotion'da. Grafik içeren iş otomatik Remotion'a düşer ve yavaşlar.

### Dosyalar
| Dosya | Satır | Ne yapar |
|---|---|---|
| `webapp/pipeline.py` | 4166 | ana hat, plan, TTS, efekt atama, ses mastering |
| `webapp/kaynak.py` | 1304 | footage kaynakları, yer doğrulama, vision kontrolü, atıf |
| `webapp/hizli_render.py` | 951 | ffmpeg render motoru, yazı katmanları, çekim bölme |
| `webapp/server.py` | 763 | HTTP API, kuyruk, sağlık ucu |
| `app/render-studio/src/Efektler.tsx` | 768 | Remotion efekt kütüphanesi (35 bileşen) |
| `app/render-studio/src/EditPaketi.tsx` | 785 | grafik şablonları, alt bant, bölüm başlığı |
| `app/render-studio/src/Video.tsx` | 666 | Remotion ana kompozisyon |
| `deploy.sh` | — | tek komut deploy (syntax + tanımsız isim kontrolü + imaja basma + prune) |

### Sunucu
- Hetzner RX-4, 10 vCPU, IP **185.23.17.240**, Docker container adı `bedosaho`
- Kod `/opt/vidrush/`, çıktılar `/opt/vidrush/webapp/ciktilar/`, anahtarlar `/opt/vidrush/webapp/veri/*.txt`
- Deploy: `bash deploy.sh` (repo kökünden). SSH anahtarı `~/.ssh/bedosaho_hetzner`.
- **UYARI:** `docker cp` ve `docker commit` konteyneri geçici duraklatır. Deploy yarıda kalırsa konteyner `paused` kalır ve site cevap vermez → `docker unpause bedosaho`.

---

## 2. Bağlı entegrasyonlar

| Servis | Ne için | Durum | Anahtar |
|---|---|---|---|
| **OpenAI** | plan (gpt-4.1-mini), TTS (gpt-4o-mini-tts), vision doğrulama, whisper hizalama, AI görsel (gpt-image-2 / -1-mini) | ✅ çalışıyor | `OPENAI_KEY` |
| **Pexels** | birincil footage kaynağı, `size=large` = 4K yerli | ✅ çalışıyor | `veri/pexels_key.txt` |
| **Coverr** | ikincil footage | ✅ premium | `veri/coverr_key.txt` |
| **Pixabay** | üçüncül footage | ⚠️ **anahtar yok** | `PIXABAY_KEY` |
| **YouTube (yt-dlp)** | Creative Commons footage, son sıra | ✅ `player_client=android_vr` ZORUNLU | — |
| **Gemini** | alternatif görsel/metin sağlayıcı | ✅ | `GEMINI_KEY` |
| **Magnific / Freepik** | görsel büyütme | ❌ **API bozuk**, destek çözmedi | `MAGNIFIC_KEY`, `FREEPIK_KEYS` |
| **edge-tts** | bedava seslendirme (varsayılan) | ✅ | — |
| **Sora** | açılış sahneleri için gerçek video | opsiyonel, ~$0.8/klip | `SORA_MODEL` |

---

## 3. Ölçülmüş kurgu hedefleri (referans: 20 rakip video)

Bunlar **prompt değil, KOD kuralı**. Kaynak: `OLCUM_EDIT_TAKSONOMI.md`, `OLCUM_BELGESEL.md`, `OLCUM_HAZEL.md`.

| Ölçüm | Referans | Kodda nerede |
|---|---|---|
| Geçiş: sert kesme | **%79.9** | `hizli_render.GECIS_IMZA_FFMPEG`, varsayılan 2 kare fade |
| Karartma | %7.6, parlaklık 88→44 (siyaha inmez) | `_karartma_dip`, `KARARTMA_DIP=0.13` |
| Beyaz flash | %4.1 | `fadewhite` |
| Zoom yönü in/out | **78/22** | `pipeline.islev_kurgu` |
| Zoom hızı | medyan %1.57/sn, 4 kovalı dağılım | `Video.tsx ZOOM_KOVA` |
| Zoom tavanı | 1.38 | `SURE_ZOOM` |
| Ken Burns easing | **lineere yakın** (son/ilk = 1.03) | `Easing.bezier(0.42,0.32,0.58,0.68)` |
| Durgun kare | %12 | `islev_kurgu` |
| Çekim medyanı | **6.5 sn**, %32'si 4 sn altı | `CEKIM_BOL_ORAN=19` (matematiği kodda yazılı) |
| Maks ekran süresi | **8 sn — kullanıcı kuralı, ihlal edilemez** | `_cekim_planla` ZORUNLU dalı |
| Yazı türü dağılımı | alt-band %33, büyük başlık %28, küçük etiket %20 (ömür 1.8 sn) | `_alt_band_filtre`, `_bolum_filtre`, `_etiket_filtre` |
| Yazı giriş animasyonu | **< 0.3 sn** (referansın %98'i tam oluşmuş yakalandı) | `YAZI_GIRIS_SN=0.28` |
| Yazı oranı | %24-28, bimodal | profil bazlı |
| Ses | −14 LUFS, tepe ≤ −1.5 dBTP | iki geçişli `loudnorm` + `acompressor` |

---

## 4. Bugün (11 Ağu) çözülenler — ve tuzaklar

Bunları tekrar bozmamak için sebepleri kodda yorum olarak duruyor.

1. **Font tuzağı.** `Montserrat-Bold.ttf` ve `Oswald-Bold.ttf` aslında **değişken font**; varsayılan ağırlık Montserrat'ta **100 (Thin)**. ffmpeg varsayılan örneği çizdiği için bugüne kadarki TÜM yazılar Thin çıkmıştı. `fontTools.varLib.instancer` ile `wght=700` statik örneği üretildi; değişken sürümler `*-degisken.ttf.yedek` olarak saklandı. **Yeni font eklerken `head -c 4000 font.ttf | grep -a fvar` ile kontrol et.**

2. **ffmpeg `drawbox` tuzağı.** `w`/`h` **ifadelerinde `t` değişkeni YOKTUR** (sadece `enable`'da var). Zaman bağımlı genişlik yazınca ifade son dala düşüp 23.663 üretti, ffmpeg kareye kırptı: bant her sahnede tam ekran çizildi (ölçüm: x=75→1919 = tam `iw - x`). Animasyon `enable` zaman pencereleriyle kademeli yapılıyor.

3. **ffmpeg `crop` tuzağı.** `crop`'un **boyut** ifadelerinde de `t` yok (sadece `x`/`y`'de var). `dolly-zoom` ve `yumusak-zoom` segmenti tamamen düşürüyordu → `zoompan` (`z` ifadesinde `on` kare sayacı var) ile yeniden yazıldı.

4. **`xfade=fadeblack` asimetrik.** Yalıtılmış ölçüm (düz renkli iki klip, 30 fps, d=0.40): `118,118,59,0,0,0,3,16,30,44,57,66,75,84` — iniş 2 kare, çıkış 8 kare. Bizim hatamız değil, filtrenin kendisi. Referans siyaha hiç inmediği için `eq=eval=frame:brightness` ile simetrik dip yazıldı.

5. **Konuşma hızı yanlıştı.** Tablo 178 wpm, ölçüm 212. Üstelik kelime bütçesi **plan üretildikten SONRA** hesaplanıyordu → plan her zaman eski hızla yazıyordu → video %33 kısa. Bütçe plandan öne alındı; sistem her işten sonra `veri/ses_hizi.json`'a **kendini kalibre ediyor** (yumuşatma 0.6/0.4).

6. **Yer doğruluğu 4 katmanda oturdu** (üç denemem yetmedi):
   - K1: klip başlığında konu kelimesi → "switch/door/meeting" ile geçiyordu, Avrupa sigorta kutusu girdi
   - K2: yer takma-ad tablosu (`YER_TAKMA_AD`, 19 ülke) → sorguda ülke yazmayınca kapı kapanıyordu
   - K3: **video düzeyinde yer bağlamı** — ülke metinden bir kez tespit edilip TÜM sahnelere zorunlu (`yer_baglami_kur`)
   - K4: **vision doğrulaması** — başlıkta "japanese" yazan ama Batılı oyunculu reklam stoğunu ancak kare görerek yakalayabildik (`_vision_yer_uygun`, gpt-4.1-mini, ~$0.0008/klip)

7. **Nötr çekim kademesi daraltıldı.** İlk listede `water/sea/sky/door/window/night` vardı ve "kültürsüz" saymıştım — Tokyo metnine turkuaz sulu tropik ada girdi. Geniş plan HER ZAMAN yer söyler. Artık nötr = **sadece makro/yakın plan** (`NOTR_ZORUNLU_ISARET`).

8. **Grain bir videoyu öldürmüştü** (30 dk zaman aşımı): her karede yeni `feTurbulence` SVG filtresi + yeni filtre ID üretiyordu. Önceden üretilmiş doku PNG'sine çevrildi.

---

## 5. Açık eksikler — Codex'in çalışabileceği liste

Öncelik sırasına göre.

### A. Render motoru eşitliği (en yüksek etki)
`Efektler.tsx`'te olup ffmpeg'de olmayanlar: `suzulme`, `donme-3d`, kinetik başlık, `YaziIcindeVideo`, `CizilenCizgi/Daire`, `IkonParlamasi`, `Hologram`, `Glitch`, `IsikSizmasi`, `Letterbox`, `TVBantlari`, `YuklemeCubugu`. Ayrıca `EditPaketi.tsx`'in 5 grafik şablonu (beyaz-tuval, ölçü, alıntı, metin, harita) ffmpeg'de hiç yok — grafik içeren iş Remotion'a düşüp **5x yavaşlıyor**.
- **Hedef:** grafik şablonlarını ffmpeg'de üretmek (drawbox+drawtext+overlay ile) ya da grafikleri ayrı PNG olarak render edip overlay etmek. İkincisi daha temiz: küçük bir headless render ile PNG üret, ffmpeg overlay'le bindir.

### B. Havuz genişletme
Vidrush'ın dokümanı açıkça yazıyor: web taramasını kapatınca kullanılabilir klip **%90 düşüyor**. Bizim havuz: Pexels + Coverr + (Pixabay anahtarı yok) + YouTube CC.
- Pixabay anahtarı ekle (bedava)
- **Kamu malı arşivler:** Internet Archive, Wikimedia Commons, NASA, ulusal arşivler — belgesel için altın madeni, telif sorunu yok
- Storyblocks API gerçekten sınırsız ama kurumsal satış sözleşmesi istiyor

### C. Kurgu (Editor) aşaması yok
Vidrush'ın hattı 5 uzman: Researcher → Scriptwriter → **Motion Designer** → **Editor** → Sound Designer. Bizde tek LLM çağrısı hem anlatımı hem footage sorgusunu yazıyor; **birleştirilmiş kurguya bakan hiçbir aşama yok**.
- **Hedef:** render'dan sonra çıktının 1 fps karelerini örnekleyip bir "kurgu eleştirmeni" ajanına verip ölçülen hedeflerle (bölüm 3 tablosu) karşılaştırmak, sapma varsa plan/efekt parametrelerini düzeltip yeniden render etmek. Ölçüm betikleri hazır (bu oturumda kullanıldı).

### D. Prompt Checker (Vidrush'ta üretimden önce var, bizde kısmen)
Vidrush 3 uyarı birikince üretimi **blokluyor**. Bizde sorgu merdiveni var ama kullanıcıya uyarı yok. Eksik: "bu konu için stokta görüntü yok, konuyu genişlet" geri bildirimi.

### E. Bilinen küçük açıklar
- Ses **−14.8 LUFS** (hedef −14); kompresör eklendi, 0.8 dB kaldı
- Süre isabeti **%109-121** arası salınıyor; `satirlari_uzat` hedefi aşıyor (%92 pay bırakıldı, doğrulanmadı)
- `atiflar` listesi boş dönüyor — CC klip kullanılmadığı için beklenen, ama YouTube CC yolu devreye girince ekranda künye + açıklama listesi test edilmedi
- 4K çıktı kararı **kullanıcıya bırakıldı**: şu an kaynak 2560 indiriliyor, çıktı 1080p. 4K çıktı istenirse render süresi ~4x, disk 41 GB/30dk
- `donme-3d` ve `suzulme` ffmpeg'de sessizce atlanıyor (2B'de karşılığı yok) — plan bunları atıyorsa efekt kayboluyor

---

## 6. Doğrulama yöntemi (bunu koru)

Kullanıcının kalıcı kuralı: **"gözle değil, ölçümle."** Her değişiklikten sonra:

```bash
# 1) uçtan uca video üret
curl -s -X POST http://185.23.17.240/api/generate \
  -F "session=test-$(date +%s)" -F "story=$(cat metin.txt)" \
  -F "tur=documentary" -F "edit=seyahat-belgeseli" -F "sure_dk=1"

# 2) 1 saniyelik kare örneklemesi (yazının GELİŞİNİ bile yakalar)
ffmpeg -i video.mp4 -vf "fps=1,scale=440:-1,tile=5x6" tablo_%d.jpg

# 3) ölç: kesme sayısı, çekim dağılımı, siyah kare, ses
ffmpeg -i video.mp4 -filter:v "select='gt(scene,0.12)',showinfo" -f null -
ffmpeg -i video.mp4 -vf "blackdetect=d=0.03:pix_th=0.10" -f null -
ffmpeg -i video.mp4 -af loudnorm=print_format=summary -f null -
```

Sonra bölüm 3'teki tabloyla karşılaştır.

**Deploy her zaman `bash deploy.sh` ile.** Script Python syntax + **tanımsız isim** taraması yapıyor; bu tarama bugün iki kez benim sildiğim fonksiyonları yakaladı, atlamayın.

---

## 7. Kullanıcının değişmez kuralları

1. **Belgesel stilinde AI görsel YOK** — `gorsel_yasak: True`, footage bulunamazsa ülkeye çapalı genel klip, gerekirse klip tekrarı
2. **Hiçbir görüntü 8 saniyeden fazla ekranda kalmaz**
3. **Gerçek sayfalara/kanallara test içeriği paylaşılmaz**
4. **Kalite referans videolardan ölçülür**, prompt'a yazılmaz — kural olarak KODA girer
5. **Kısa yaz** — uzun rapor değil, madde madde; detay dosyaya
6. **Telif:** kaynak yazmak izin vermez. YouTube footage yalnızca Creative Commons, lisans indirmeden önce tek tek doğrulanır (`_lisans_cc_mi`)
