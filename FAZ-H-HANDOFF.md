# FAZ H — HANDOFF ve ENVANTER

_Başlangıç: 12 Ağustos 2026 · branch `arastirma-motoru` · baz commit `90faaad`_

Bu dosya bağlam dolarsa **yeni bir oturumun sıfırdan devam edebilmesi** için yazıldı.
`CODEX_BRIEF.md` sistemi tanıtır; bu dosya **Faz H'nin ne bulduğunu ve nerede kaldığını** anlatır.

---

## 0. Faz H başlarken doğrulanan durum

| Şey | Değer |
|---|---|
| Branch | `arastirma-motoru` |
| Baz commit | `90faaad` (deploy.sh düzeltmesi — **korundu, geri alınmadı**) |
| Çalışma ağacı | temiz (yalnız `__pycache__` untracked) |
| A–G testleri | **1154 geçti / 0 hata** (A 125 · B 200 · C 148 · D 95 · E 127 · F 242 · G 217) |
| Yerel python | 3.9.6 (sistem) — `fastapi`, `pytest`, `uvicorn`, `python-multipart` **YOK** |
| Yerel node | v24.14.1 · ffmpeg + ffprobe var (`/opt/homebrew/bin`) |

**Testleri çalıştırma:** `pytest` ile TOPLAMA. Bu dosyalar import sırasında `sys.exit()` çağırıyor.
Tek tek betik olarak koş:

```bash
for t in a b c d e f g h; do python3 webapp/testler/test_faz_$t.py; done
```

`timeout` komutu macOS'ta YOK (`exit 127`). Kullanma.

---

## 1. EN AĞIR BULGU — İki paralel dünya

`/api/generate` isteğinin gerçekten çalıştırdığı hat:

```
server.py  →  pipeline.py (4166 satır)  →  kaynak.py  →  hizli_render.py / Remotion
```

Faz A–E'de yazılan modüller:

```
webapp/arastirma/   (researcher, fact_checker, source_conflict, manifests, cache, butce)
webapp/medya/       (avci, lisans, aday, siralama, kapsam, indirme, providers/, vision)
webapp/editor/      (beat, plan, motion, adapter, qa_on, qa_son, ses, tipografi, remotion_v2)
```

**`pipeline.py` bu üç paketin HİÇBİRİNİ import etmiyor.** Doğrulama:

```bash
grep -rn -E "^\s*(import|from) +(arastirma|medya|editor)" webapp --include='*.py' | grep -v testler
# → yalnızca medya/*.py'nin arastirma.*'yi import ettiği 4 satır çıkar.
```

Sonuç: araştırma, fact-check, lisans duvarı, beat planlama, motion motoru ve QA
**yalnızca test betiklerinden** (`webapp/testler/faz_e_pilot.py` gibi) çağrılıyor.
Canlı sitede bunların hiçbiri çalışmıyor.

Bu, ana sayfadaki **"Araştırma, gerçek görüntü seçimi, kurgu, ses ve altyazı tek akışta"**
iddiasını şu an karşılıksız bırakıyor.

---

## 2. Sözleşme matrisi — UI ↔ backend uyuşmazlıkları

| # | Alan | Backend döndürüyor | UI okuyor | Sonuç |
|---|---|---|---|---|
| 1 | iş kimliği | `job_id` (`server.py:677`) | `cevap.job \|\| cevap.is_id \|\| cevap.id` (`wizard.js:543`) | **KIRIK** — iş kimliği hep boş; onay ekranı boş `<strong>` gösterir, localStorage'a `is_id: ""` yazılır |
| 2 | ilerleme | `ilerleme` (`server.py:701`) | `is.yuzde` (`bilesenler.js:108`) | **KIRIK** — ilerleme çubuğu hep %0 |
| 3 | canlı takip | `GET /api/job/{id}` var | `isDurumu()` (`api.js:168`) **tanımlı, hiç çağrılmıyor** | **ÖLÜ KOD** — Projeler ekranı bir kez çizilir, hiç yenilenmez |
| 4 | video çıktısı | `video`, `kapak` + `GET /ciktilar/{dosya}` | `isKart` yalnızca kapak `<img>` çiziyor; oynat/indir bağlantısı yok | **ERİŞİLEMEZ** — üretilen video arayüzden açılamıyor |
| 5 | sağlık | yalnız anahtar booleanları; **`durum`/`status` alanı YOK** | `String(v.durum ?? v.status ?? 'ok')` (`gorunumler.js:221`) | **YANLIŞ POZİTİF** — alan yoksa `'ok'` varsayılır → ffmpeg/renderer/disk çökse bile "Sistem hazır" yazar |
| 6 | atıflar | `atiflar` iş sözlüğünde var (`server.py:782`) | UI hiç göstermiyor | **GÖRÜNMEZ** |
| 7 | uyarı | `uyari` iş sözlüğünde var | UI hiç göstermiyor | **GÖRÜNMEZ** — "bakiye bitti, 12 sahne kurtarıldı" gibi kritik mesajlar kullanıcıya ulaşmıyor |
| 8 | kuyruk sırası | `kuyruk_sira` / `kuyruk_toplam` | UI hiç göstermiyor | **GÖRÜNMEZ** |
| 9 | aşama | **yok** — yalnız serbest metin `mesaj` | — | makine-okunur `stage` alanı hiç yok |
| 10 | QA | **yok** | — | üretim sonrası ölçüm işe hiç yazılmıyor |

---

## 3. UI'da olup backend'i olmayan (dekoratif / yalan)

| Yer | Ne yazıyor | Gerçek |
|---|---|---|
| Wizard Adım 4 | "Güvenilir kaynak sayısı / Doğrulanmış iddia / Kullanılabilir medya / Sahne sayısı / Tahmini maliyet / Render süresi / Lisans durumu → **Üretim sırasında hesaplanacak**" | 7 alandan **yalnız `sahne_sayisi`** üretim sonunda dönüyor. Diğer 6'sı üretim sırasında da hesaplanmıyor. Vaat karşılıksız. |
| Ayarlar → Medya kaynakları | 8 kaynak listeleniyor (Wikimedia, Openverse, Library of Congress, Internet Archive dahil), her birinde yeşil/sarı nokta | **Sabit kodlanmış dizi** (`gorunumler.js:247` `KAYNAK_ZINCIRI`). Ölçüm yok. Son 4 kaynak `medya/providers/` içinde var ama `/api/generate` akışında **yok**. |
| Ayarlar → Entegrasyonlar | 3 satır, durum noktalı | **Sabit kodlanmış** (`gorunumler.js:262`). "Yerel TTS (macOS say)" sunucuda **yok** (Linux konteyner). |
| Ana sayfa | "Araştırma … tek akışta" | Araştırma akışta yok (bkz. §1) |
| Stil kartı önizlemesi | `stilOnizleme(s)` SVG maketi | Sunucunun döndürdüğü gerçek `onizleme: "onizleme/{id}.jpg"` alanı **üzerine yazılıyor** (`secim-deneyimi.js:210`); gerçek önizleme JPEG'i hiç gösterilmiyor. `webapp/static/onizleme/` repoda yok. |
| Ses "Dinle" düğmesi | `/api/sesler` `ornek` alanına bağlı | `webapp/static/ses-ornek/` repoda **yok** → yerel seslerde düğme hiç çizilmiyor (kod doğru davranıyor, varlık eksik) |

---

## 4. Backend'de olup UI'da olmayan (ölü uçlar)

`webapp/static/` içinde 0 kullanım:

| Uç | Durum |
|---|---|
| `GET /api/job/{id}` | `UCLAR.is` + `isDurumu()` tanımlı, **çağrılmıyor** |
| `GET /ciktilar/{dosya}` | `UCLAR.ciktilar` tanımlı, **kullanılmıyor** |
| `GET /api/freepik-kota` | `UCLAR.freepikKota` tanımlı, **kullanılmıyor** |
| `POST /api/profil` | **Marka kiti oluşturma UI'ı YOK** — Ayarlar sadece listeliyor |
| `DELETE /api/profil/{pid}` | UI yok |
| `POST /api/profil/{pid}/capa-sifirla` | UI yok |
| `GET /onizleme/{dosya}` | `UCLAR.onizleme` tanımlı, kullanılmıyor (bkz. §3) |
| `GET /fonts/{dosya}` | `UCLAR.fontlar` tanımlı, kullanılmıyor — altyazı canlı önizlemesi gerçek fontla çizilmiyor |
| `GET /ses-ornek/{dosya}` | dolaylı kullanılıyor ama varlık dizini yok |

---

## 5. 21 generate alanı — durum

`api.js GENERATE_ALANLARI` (21) ile `server.py uret_baslat` imzası (21) **birebir uyuşuyor**;
`test_faz_f.py` bunu kilitliyor. `wizard.js generateDegerleri()` 21'inin hepsini üretebiliyor.

Alanlar: `session, story, tur, edit, sure_dk, gecis, zoom, profil, altyazi, altyazi_sablon,
palet, palet_ozel, acilis, sora, arkaplan, ses, isik, gorsel_model, karakter, stil, sahne_ref`

**Ama:** belgeselde `gorsel_yasak: True` olduğu için `palet`, `arkaplan`, `isik`, `gorsel_model`,
`karakter`, `stil` **belgesel türünde pipeline tarafından tüketilmiyor**. UI bunları türe göre
gizlemiyor → kullanıcı etkisi olmayan seçim yapıyor. (Faz H'de doğrulanacak/gizlenecek.)

---

## 6. Yerel çalıştırma blokerleri (gerçek FastAPI testi için)

1. **`pipeline.py` import anında çöküyor.** `CIKTI_DIR = "/opt/vidrush/webapp/ciktilar"` +
   `os.makedirs(...)` → yerelde `PermissionError: '/opt/vidrush'`.
   Aynı sorun: `PROFIL_DIR`, `STUDYO`, `SFX_DIR`, `kaynak.ANAHTAR_DIZIN`, `hizli_render.STUDYO`,
   `editor/onizleme.py` font yolu, `app/uret.py` AI33 yolu, `server.py:353`.
   → **Çözüm: `VIDRUSH_KOK` env değişkeni, varsayılan `/opt/vidrush` (üretim davranışı değişmez).**
2. `fastapi`/`python-multipart` yerelde yok. Faz H için scratchpad'de venv kuruldu:
   ```bash
   python3 -m venv .venv-test && .venv-test/bin/pip install fastapi python-multipart httpx pillow requests
   ```
3. `import uret as uretmod` — `app/uret.py`. `sys.path` `/opt/vidrush` bekliyor.

---

## 7. Öncelik sırası (kullanıcı 12 Ağu notu)

1. **Gerçek `/api/generate` hattına A–E motorlarını bağla**
2. İş sözleşmesi / UI polling / çıktı linkleri
3. Derin sağlık
4. Otomatik metin + stil analizi
5. A–H testleri ve gerçek pilot

Kurallar: şimdilik **deploy yok**, önce yerel QA. Kalite kapısı geçmeden canlıya çıkılmaz.
Küçük, doğrulanabilir adımlar; her adım kendi commit'i.

---

## 8. İlerleme günlüğü

| Tarih | Adım | Commit | Durum |
|---|---|---|---|
| 14 Ağu | **R-1d-a TESLİM ATOMU — zincir uçtan uca bağlandı** | _(bu commit)_ | ✅ A–I **4003 geçti / 0 hata**; ⚠ **ÖLÇÜLEN KUSUR: R-1a/R-1b/R-1c-a/R-1c-b modülleri VARDI ama `server.py` ÜÇÜNÜ DE İMPORT ETMİYORDU** — `/api/generate` serbest `session` string'i alıyor, `/ciktilar/` imzayı doğrulayıp **tenant'a bakmıyor**, kütüphane **hiç dolmuyordu**; yeni `webapp/teslim.py` (10 halkalı **kanıt temelli** zincir, kanıtsız halka → **teslim YOK**), `imzali_url` imzası **tenant'a bağlanabilir** (tenant boşken **bit-bit** eski davranış), `server.py` zorunlu oturum + tenant süzme + `/api/kutuphane`; ⚠ **AYRI GÜVENLİK BULGUSU: R-1a imza anahtarı (`webapp/veri/.imza_anahtari`) kazayla COMMIT EDİLMİŞTİ** (`4846264`) — modülün kendi sözleşmesi "anahtar_repoda: False" diyordu ama test **YANLIŞ YOLU** kontrol ediyordu; izlemeden çıkarıldı + **döndürüldü** + `.gitignore`; sunucuda anahtar **hiç yoktu** (R-1a deploy edilmemişti) → **üretimde kullanılmadı**; Mac'te medya üretilmedi, $0.00 |
| 12 Ağu | H0 envanter + handoff | `4ec1be1` | ✅ |
| 12 Ağu | H1 kök yolu + deploy.sh alt paket | `eda27fc` | ✅ |
| 12 Ağu | H2–H3 araştırma köprüsü + iş sözleşmesi + derin sağlık + UI | `e4af286` | ✅ |
| 12 Ağu | Deploy engeli belgelendi (main ile ayrışma) | `f19a3f5` | ✅ |
| 12 Ağu | origin/main birleştirmesi (22 alan, ünlü modu, vbee/clone) | `5739d4e` | ✅ |
| 12 Ağu | **CANLIYA ÇIKILDI** + Shackleton pilotu | `ee318ca` | ✅ |
| 12 Ağu | H5 medya doğruluk kapısı (biyom/dönem) | `da44489` | ✅ |
| 12 Ağu | H6 render sonrası QA kapısı | `171737c` | ✅ |
| 12 Ağu | H4 otomatik girdi analizi | `d40936f` | ✅ **CANLI** |
| 12 Ağu | **I-1 kare kapısı** — medya seçim akışına bağlandı | `7dd6322` | ✅ yerel yeşil, **deploy YOK** |
| 12 Ağu | **I-2a hiyerarşik konsept taksonomisi** | `687e004` | ✅ yerel yeşil, **deploy YOK** |
| 12 Ağu | **I-2b sürümlü bileşik stil profilleri** | `fff3f36` | ✅ **origin'e push edildi**, deploy YOK |
| 12 Ağu | **I-2c akışa bağlama** (taksonomi + stil profili → `analiz()`) | `0945a2f` | ✅ **origin'e push edildi**, deploy YOK |
| 12 Ağu | **I-3 basit "Metin + Stil + Auto" arayüzü** | `37b0b04` | ✅ **origin'e push edildi**, deploy YOK |
| 12 Ağu | **I-4 referans video parmak izi sözleşmesi** | `0d45fc8` | ✅ **origin'e push edildi**, deploy YOK |
| 12 Ağu | **I-2d görsel imza boşluğu kapatıldı** | `243bad5` | ✅ **origin'e push edildi**, deploy YOK |
| 12 Ağu | **I-5 konsept farkındalıklı medya seçimi** | `e3559b2` | ✅ **origin'e push edildi**, deploy YOK |
| 12 Ağu | **I-6 medya avcısı canlı hatta (opt-in)** | `1e9c288` | ✅ **origin'e push edildi**, deploy YOK |
| 12 Ağu | **I-7 iş başına bütçe + paralel izolasyon** | `6294369` | ✅ **origin'e push edildi**, deploy YOK |
| 12 Ağu | **I-8 doğrulanmış olgu → sahne/medya bağı** | `e450aa0` | ✅ **origin'e push edildi**, deploy YOK |
| 12 Ağu | **I-9 uçtan uca edit planı orkestrasyonu** | `a0294d0` | ✅ **origin'e push edildi**, deploy YOK |
| 12 Ağu | **I-10 edit köprüsü pipeline'a bağlı + manifest dönüşümü** | `477b168` | ✅ **origin'e push edildi**, deploy YOK |
| 12 Ağu | **I-11 20 sn GERÇEK render smoke** | `f4e3a5e` | ✅ **origin'e push edildi**, deploy YOK |
| 12 Ağu | **I-12 QA WARN raporu + chapter-card kalitesi** | `9be6375` | ✅ **origin'e push edildi**, deploy YOK |
| 12 Ağu | **I-13 10 sn kaliteli sesli Apollo mini-belgeseli** | `ca023f3` | ✅ **origin'e push edildi**, deploy YOK |
| 12 Ağu | **I-14 (1. atom) kalite kapıları ölçüldü + QA'ya bağlandı** | `c584020` | ✅ **origin'e push edildi**, deploy YOK |
| 12 Ağu | **I-15 gerçek düzeltme + yeniden render (kapı AÇIK, PASS)** | `891a814` | ✅ **origin'e push edildi**, deploy YOK |
| 12 Ağu | **I-16 altyazı + kaynak künyesi + 1080p** | `2f16bc6` | ✅ **origin'e push edildi**, deploy YOK |
| 12 Ağu | **I-17 motion grammar + optik durağanlık kapısı** | `2448478` | ✅ **origin'e push edildi**, deploy YOK |
| 12 Ağu | **I-18 ikinci konsept: motor kanıtlandı, medya BLOKE** | `ccb97ce` | ⚠ **origin'e push edildi**, MP4 YOK, deploy YOK |
| 12 Ağu | **I-19 edinim dayanıklılığı — I-18'in BLOKE'si açıldı** | `888063e` | ✅ **origin'e push edildi**, deploy YOK |
| 12 Ağu | **I-20 üçüncü konsept: motor sınandı, render BLOKE** | `beaee8f` | ⚠ **push edildi**, MP4 YOK, deploy YOK |
| 12 Ağu | **I-21 bölünen beat ayrı varlık alır (dar atom)** | `efbf111` | ⚠ **push edildi**, POST-QA FAIL, MP4 teslim YOK |
| 12 Ağu | **I-22 medyasız beat kusuru çözüldü** | `a220fcb` | ⚠ **push edildi**, POST-QA FAIL (dikey kaynak), MP4 teslim YOK |
| 13 Ağu | **I-23 en-boy oranı uyumluluk kapısı (dar atom)** | `49c726e` | ✅ **push edildi**, POST-QA **TAMAMEN PASS**, Faz I BLOKE 0, deploy YOK |
| 13 Ağu | **I-24 motion çeşitliliği ölçülebilir kapıya çevrildi** | `929b9b4` | ✅ **push edildi**, POST-QA PASS, kalite puanı **100/100**, deploy YOK |
| 13 Ağu | **I-25 sağlayıcı-tekel tanısı: kök neden bizdeydi** | `4acf133` | ✅ **push edildi**, 2 gerçek hata düzeltildi, WARN **dürüst** (Commons 429), medya kümesi değişmedi, deploy YOK |
| 13 Ağu | **I-26 s03 aşırı dar sorgu çözüldü; pilot BLOKE** | `2928130` | ⚠ **push edildi**, Commons s03 0→2 aday, tekel %100→%60, MP4 **KABUL EDİLMEDİ** (punch büyütme), deploy YOK |
| 13 Ağu | **I-27 kamera punch büyütmesi ÇÖZÜLDÜ** | `6ccb739` | ✅ **push edildi**, büyüten beat 2→0, POST-QA **TAM PASS**, puan 100/100, Faz I BLOKE 0, deploy YOK |
| 13 Ağu | **I-28 seçim sırası tanısı: KUSUR YOK** | `b61208d` | ✅ **push edildi**, öncül ölçümle çürüdü, üretim kodu DEĞİŞMEDİ, davranış kilitlendi, MP4 korundu, deploy YOK |
| 13 Ağu | **I-29 afiş/pano sinyali: metadata GÜVENİLİR DEĞİL** | `015973e` | ✅ **push edildi**, recall %0 / hassasiyet %6 ölçüldü, üretim DEĞİŞMEDİ, MP4 korundu, deploy YOK |
| 13 Ağu | **I-30 yatay güvenli alan kapısı eklendi** | `527cd28` | ✅ **push edildi**, sağ/sol taşma ölçülür oldu, pilotta ateşlemiyor, MP4 korundu, deploy YOK |
| 13 Ağu | **I-31 ekran künyesi politikası** | `73d91e1` | ⚠ **push edildi**, taşma çözüldü + tam atıf korundu, MP4 **KABUL EDİLMEDİ** (açılış vitrin planı), deploy YOK |
| 13 Ağu | **I-32 kare örnekleme her beat'i kapsıyor** | `7098f4b` | ✅ **push edildi**, b001 kör noktası çözüldü, rerender YOK (talimat), BLOKE kanıt olarak duruyor, deploy YOK |
| 13 Ağu | **I-33 gerçek koşum doğrulaması** | `584dea6` | ⚠ **push edildi**, kare planı KANITLANDI (b001 kapsandı), otomatik kapılar PASS ama MP4 **KABUL EDİLMEDİ** (b001 vitrin/pano), deploy YOK |
| 13 Ağu | **I-34 vitrin sinyali: ELENDİ** | `7c5884f` | ✅ **push edildi**, 4 sinyal x 28 ölçüm: ayıran eşik YOK (en iyi precision 0.25), üretim DEĞİŞMEDİ, rerender/deploy YOK |
| 13 Ağu | **I-35 s01 sorgu daraltması: ELENDİ** | `7709ae1` | ✅ **push edildi**, 10 sorgu ölçüldü: vitrini eleyen her daraltma NASA'yı boşaltıyor, sorgu DEĞİŞMEDİ, rerender/deploy YOK |
| 13 Ağu | **I-36 sağlayıcı tutarsızlığı düzeltildi** | `6bab9f9` | ✅ **push edildi**, başarılı geçmiş 429 ile ezilmiyor, sağlayıcı seçilen varlıktan türüyor, rerender/deploy YOK |
| 13 Ağu | **I-37 beat→scene→asset bağı kopamaz** | `3ccc73c` | ✅ **push edildi**, çapraz sahne kayması ÇÖZÜLDÜ + PRE-QA kapısı; lawn MP4 **KABUL EDİLMEDİ** (s01 tek varlık), deploy YOK |
| 13 Ağu | **I-38 yazı spec'i sahneye göreli** | `bf1b0c8` | ✅ **push edildi**, ekran künyesi artık ÇİZİLİYOR (4 CC sahne) + PRE-QA kapısı; lawn MP4 **KABUL EDİLMEDİ** (POST-KENAR-SIYAH + semantik), deploy YOK |
| 13 Ağu | **I-39 altyazı nefes boşluğu zorunlu** | `391d527` | ✅ **push edildi**, künye SAĞ ÜSTE (32.1→766.5 px) + başlık 0.60 + PRE-QA `KALITE-YAZI-NEFES-YOK`; 1080p pilot POST-QA **PASS**, kenar 1/101→0/101; lawn MP4 **KABUL EDİLMEDİ** (b001/b002/b005 semantik), deploy YOK |
| 13 Ağu | **I-40 önizleme yolu Remotion geometrisine bağlandı** | `3253e62` | ✅ **push edildi**, `y_orani/punto/x` artık SPEC'ten (sabit 0.70/0.80/`h-th-14` gitti) + modülün İLK testi; 1080p pilot **11/11 kare SHA-256 aynı** (gerileme yok), önizleme yazısı **BLOKE** (yerel ffmpeg'de drawtext yok), deploy YOK |
| 13 Ağu | **I-41 `kaynakYazi` üretim hattında kayıpsız taşınıyor** | `6179484` | ✅ **push edildi**, künye props sınırında düşüyordu → **iki renderer da** çizemiyordu; artık sağ üstte **çiziliyor** (kareyle doğrulandı), 22 alan sözleşmesi değişmedi; VidrushVideo pilotu **POST-QA FAIL** (nedenleri I-41 dışı, ayrıştırıldı), editorv2 **11/11 kare aynı**, deploy YOK |
| 13 Ağu | **I-42 açılış çekimi durağanlığı** | `2262833` | ✅ **push edildi**, indeks 0 daima %0.4/sn kovasına düşüyordu → ölçülerek 0.062'ye taşındı (0.032 bıçak sırtı olduğu için **seçilmedi**); pilotta s0 optik **1.421 → 4.016**, durağan seri 3.0 → 0.0 sn; eşik gevşetilmedi, POST-QA **FAIL** (kapsam dışı s1/s2), deploy YOK |
| 14 Ağu | **R-1c-b tenant başına son 3 kabul edilmiş video** | `557b5fe` | ✅ **push edildi**, yeni `webapp/kutuphane.py` — **saf metadata**, modül **medya açmıyor/dosya silmiyor/ağa çıkmıyor**; kabul kapısı: `bitti`+QA **PASS/WARN** girer, **QA FAIL / QA ölçülmemiş / başarısız / videosuz** ⛔ girmez (*"muhtemelen iyidir" denmez*); retention **tenant başına 3**, 4. kabulde **en eski** **silme kuyruğuna** alınır (`TAVAN-ASILDI`) — ⚠ gerçek silme **remote lifecycle işinin** işi; sıralama **en yeni önce**, geç gelen eski kayıt en yeniyi **düşürmez**, aynı iş **idempotan**; tenant izolasyonu **iki savunma hattı** (listeleme + kaydın sahibi kontrolü), kimlik yoksa **red**; signed URL **kayıtta saklanmıyor**, `listele()` sırasında **talep anında** ve **tenant korumalı** üretiliyor, imzalayıcı yoksa **sessiz boş link yok** (`imzalanamadi: True`); metadata **QA+provenance+provider+model+credit+zaman** taşıyor, **eksik alan uydurulmuyor**, fallback nedeni **görünür**; 26 red-first kontrol (tenant sızıntısı, sıralama, retention, signed URL); uçların oturuma bağlanması + dashboard UI **sonraki atom**; deploy YOK, $0.00 |
| 14 Ağu | **R-1c-a zorunlu oturum + tenant izolasyonu temeli** | `16d449c` | ✅ **push edildi**, yeni `webapp/kimlik.py`; ⚠ **parola sözleşmesi FAIL-CLOSED**: yalnız **Argon2id/bcrypt**, güçlü algoritma yoksa hesap açma/giriş **başlamaz** → stabil kod **`KIMLIK-KDF-YOK`**, **zayıf fallback YOK** (ilk taslaktaki scrypt→PBKDF2 zinciri kullanıcı kararıyla **geri alındı**); bağımlılık repo yönetiminde **sabit** (`argon2-cffi==23.1.0`, her iki Dockerfile), Argon2id 64 MiB/3 tur/4 paralellik; ⚠ **geçiş ayrı ve açık yol** — eski `scrypt`/`pbkdf2` yalnız `eski_hash_dogrula()` ile doğrulanır ve `yeniden_hashle` ister, normal doğrulama bu biçimleri **geçirmez**; oturum **HMAC** mühürlü (**önce imza, sonra süre** — bilgi sızmaz), çerez **HttpOnly+SameSite+Secure**, **CSRF double-submit** sabit zamanlı, giriş **5/300sn IP başına** kayan pencere (kalıcı kilit yok); tenant izolasyonu: **kimlik yoksa erişim yok**, başka tenant → `BASKA-TENANT`, ⚠ **sahipsiz kayıt "herkese açık" sayılmıyor** → `KAYNAK-SAHIPSIZ`; provisioning **yalnız env/stdin**, parola **koda/commit'e/argümana yazılmadı**, dönen kayıtta düz metin **yok**, her hesaba ayrı `tenant_id`; ⚠ **gerçek hesap OLUŞTURULMADI**; 33 red-first güvenlik/sızıntı kontrolü; uçların oturuma bağlanması ve son-3-video yaşam döngüsü **R-1c-b**; deploy YOK, $0.00 |
| 14 Ağu | **R-1b tenant provider zinciri (adapter→motor→timeline)** | `4fb1d3a` | ✅ **push edildi**, **gerçek OAuth YOK / kredi TÜKETİLMEDİ** — test-double + ücretsiz stok fallback; yeni `medya/saglayici_motoru.py`: planlayıcı(`shot_istegi`: semantik sorgu+negatifler+oran+süre+kalite hedefi) → **provider registry** (tenant izolasyonlu) → **job-scope token** → **MCP capability discovery** → edinim → ölçüm → **provenance** → **timeline**; dış dünyanın tamamı **enjekte** (modül ağa çıkmaz/medya açmaz, testli); ⚠ **uydurma yok**: stok arama yoksa üretim, o da yoksa dönüşüm, hiçbiri yoksa **ücretsiz stok**, her durumda **`provider_used`+`fallback_reason`** görünür; ⚠ **şifreleme uydurulmadı** — `cryptography` sunucuda **yok**, gerçek çözücü verilmezse token **kullanılmaz** ve **düz metin token kabul edilmez** (R-1c ön koşulu); **tenant tokeni istemciye çıkmıyor** (`baglanti_ozeti` token vermez); başka tenant bağlantısı **asla** seçilmiyor; kullanıcı açıkça Magnific dediyse **sessiz geçiş yok**; provenance auto modda **`model_unknown/auto`** yazıyor; timeline **semantik→gerçek video→piksel→bitrate** ile sıralıyor, **negatif ihlali eleniyor**, **aynı kaynak ≤8 sn**, **kaynak sesi sıfır**; 26 red-first entegrasyon kontrolü; Mac'te medya **üretilmedi**; deploy YOK, $0.00 |
| 14 Ağu | **R-1a sunucu kapasite ölçümü + imzalı çıktı URL** | `4846264` | ✅ **push edildi**, teslim odağı: sunucu **salt-okunur** denetlendi — ⚠ canlı IP CLAUDE.md'deki değil **185.23.17.240**; konteynerde **bellek/CPU limiti YOK**, `RENDER_MOTOR=ffmpeg`, `EDITOR_V2` **kapalı**, `PEXELS_KEY` boş; **kapasite ölçüldü: 60 sn 1080p30 CRF18 render = 18 sn, tepe RSS 968 MB** → 55–65 sn 1080p **blokaj değil** (önceki bellek endişem yanlıştı); yeni `webapp/imzali_url.py`: `/ciktilar/` ucu **imzasızdı** (dosya adını bilen herkes indirebiliyordu) → **HMAC-SHA256 + sabit zamanlı karşılaştırma + zorunlu TTL**, anahtar env→`veri/.imza_anahtari` (**0600**)→üretilir, **repoda değil/loglanmıyor**, kurulamazsa uç **503** (sessizce korumasız çalışmaz), path traversal kesildi; iş sözleşmesi imzalı `video_url`+`manifest_url` üretiyor, **imzalayıcı yoksa eski davranış korunuyor**; ⚠ imzasız istek artık **403** (404 değil — varlık sızdırılmaz), `test_faz_h` bu gerekçeyle güncellendi; 16 red-first kontrol; Mac'te medya **üretilmedi**; deploy YOK, $0.00 |
| 14 Ağu | **K-3 açılış başlık/şerit süresi** | `7d58a4e` | ✅ **push edildi**, **MEDYASIZ atom**: açılış başlığı `min(5.5, beat+1.5)` ile kuruluyordu — **metne hiç bakmıyordu** (iki kelimelik başlık da 5.5 sn) ve `+1.5` ile **intro beat'i aşıyordu** (anlatıcı cümlesi bitince yazı **asılı** kalıyordu); artık süre **metinden** türüyor: `max(karakter/CPS, kelime/KPS) × katsayi`, `min_gorunme_sn` alt sınırı ve **üç sert üst sınır** (mutlak tavan · **intro beat sonu** · asılı kalma **0**); gerçek pilot başlığı **5.325 → 1.714 sn**, asılı kalma **1.700 → 0.000 sn**; CPS eşiği **TÜRETİLMİŞ** (`ALTYAZI_MAKS_CPS` ile aynı okuma hızı), diğerleri **beyan edilmiş**; stabil kod **`KALITE-BASLIK-SURESI`**; kısaltma sessiz değil (`kisaltildi` bayrağı); **K-4 kancası gevşek ve geriye uyumlu** — `katsayi` varsayılanı 1.0, üst sınırları **delemez**, `edit_seviyesi` çalışan koda ve 22 alan sözleşmesine **girmedi**; 25 red-first saf timeline kontrolü; ⚠ I-9 tuzağına ikinci kez düşüldü (yorum taraması) ve `olcum` sözlüğü erken kullanıldı — ikisi de düzeltildi; 22 alan, kullanıcı seçimleri, `deploy.sh`, I-38 ve K-1/K-2 kapıları **korundu**; deploy YOK, $0.00 |
| 14 Ağu | **K-2 arka plan uğultu kapısı + kaynak sesi sıfır** | `200828a` | ✅ **push edildi**, **MEDYASIZ atom** (Mac'te medya/ses/kare/render/QA artefaktı yok, `ffmpeg` çalıştırılmadı): kaynak video sesi **mutlak sıfır** olarak üç katmanda kilitlendi — renderer zaten `muted`, `render_plan` artık **makine okunur** `ses_kanali: "sifir"` yazıyor, `kaynak_ses_sozlesmesi()` denetliyor → ihlal **`KALITE-KAYNAK-SES-SIZINTI`**; TTS dışı sürekli hiss/rumble/wind için yeni `editor/ses_gurultu.py`: öznitelikler (`konusma_disi_lufs`, `sureklilik_orani`, `spektral_duzluk`, `dusuk/yuksek_frekans_orani`, `belirsizlik_db`) **sayı olarak dışarıdan** enjekte edilir (mevcut okuyucu deseni), modül **medya açmaz/ffmpeg çalıştırmaz**; karar **üç koşul birlikte** (duyulabilir + sürekli + spektral iz) — tek başına düşük SNR müzik yatağında da olur; ⚠ SNR eşiği **TÜRETİLMİŞ** (`DUYULABILIR_FARK_DB`=30 dB ters yönde okundu), diğerleri `DUYULABILIR_FARK_DB` ile **aynı dürüstlük etiketiyle** "beyan edilmiş tasarım eşiği" ve `esik_kaynagi` alanında **raporlanıyor**; **güven aralığı**: SNR±belirsizlik eşiği kesiyorsa `supheli` → **WARN, FAIL değil** (emin değilsen temiz içeriği FAIL etme), ölçüm eksikse **hüküm yok**; deterministik akış ölç→**güvenli** filtre öner (rumble `highpass f=80` — konuşma temel frekansının altında; genişbant bastırma **≤6 dB tavanlı**; **konuşma bandı 300–3400 Hz'e dokunulmaz**)→temizlemeyi doğrula (konuşma bandı >1.0 dB geriler **ya da** ASR güveni >0.02 düşerse **filtre reddedilir**, netliği bozan denoise **uygulanmaz**)→temizlenemiyorsa **`KALITE-SES-GURULTU`** FAIL; 38 red-first kontrol; ⚠ testte I-9 tuzağı (ham dize modülün kendi docstring'ini yakaladı) `_kod_yalniz` ile düzeltildi; I-23/I-24/I-25/I-38, eşikler, 22 alan, kullanıcı seçimleri, `deploy.sh`, K-1 B-roll kapısı **korundu**; deploy YOK, $0.00 |
| 14 Ağu | **K-1 video kamera muafiyeti + B-roll çeşitlilik kapısı** | `759fe9b` | ✅ **push edildi**, **MEDYASIZ atom** (Mac'te medya/ses/kare/render cache/QA artefaktı/MP4 **üretilmedi**): video ağırlıklı kurguyu **yapısal olarak imkânsız** kılan etiket artefaktı düzeltildi — J-5a'dan beri gerçek video `static` diye etiketleniyordu ve I-24'ün "aynı işlevde aynı kamera hareketi" kuralı bunu gerçek kamera kararı sanıp **4+ video sahnesinde kaçınılmaz FAIL** üretiyordu; `islev_tekrari` + `pencere_tekrari` bacakları artık video çekimlerde **muaf** (enerji I-44 ve statik-süre J-5a bacaklarındaki **mevcut** desenin aynısı), muaf çekimler `kamera_kapisi_muaf_video`da **sayılabilir**; ⚠ boşluk **boş bırakılmadı**: yerini `broll_cesitliligi_ozeti`nin **B-roll görsel dili** bacağı aldı — I-24 işlev kuralının **birebir** karşılığı (`hareket` yerine `cekim_turu`), stabil kod **`KALITE-BROLL-CESITLILIK`** (işlev tekrarı → FAIL, pencere tekrarı → WARN); **sayısal eşik UYDURULMADI** — J-3 oranları hâlâ yalnız rapor (`hedef: None`, `enforce: False`), kapıya bağlı alanlar `kapiya_bagli`da sayılı; red-first: fotoğraf yolu **bit-bit aynı** (I-24 korundu), video yokken davranış **değişmez**, farklı çekim türünde **yanlış pozitif yok**, kod `KALITE_KODLARI`'nda olduğu için kalite kapısı kapalıyken **üretilmez**; ⚠ `ardisik_tekrar` **bilerek kapsam dışı** → iki video hâlâ yan yana gelemez (K-1b); I-23/I-24/I-25/I-38, eşikler, lisans/provenance, 22 alan, kullanıcı seçimleri, `deploy.sh` **korundu**; deploy YOK, $0.00 |
| 14 Ağu | **J-5a ilk gerçek video edinimi + pilot** | `ee81265` | ⚠ **push edildi**, J-4 kapısı edinim hattına **bağlandı**; Wikimedia Commons'tan **tam 1** gerçek video indi (`Irrigation sprinkler 7`, **1920×1080 vp9 52.2 Mbps** 12.47 sn 81.4 MB, **cc-by-sa**, F ASTILY, lisans **kaydı** API'den — izleme sayfası değil, indirme zamanı kayıtlı, **$0.00**); tavanlar **1 dosya / 300 MB**, NASA **devreye girmedi** (sorgu uzay değil), konu dışı fallback **yok**, PEXELS/PIXABAY anahtarı **aranmadı**; kapı **iki kez** koştu (indirme öncesi + ffprobe ölçümüyle sonrası, red → dosya silinir); **25.30 sn 1080p pilot**: POST-QA **PASS**, kalite **100/100**, `video_sure_orani` **0.0 → 0.2123**, statik **1.0 → 0.7877**, LUFS −14.2 (aynı), LRA 2.5 (aynı), TP −2.6 dBFS, **0** sessizlik bölütü, **11 kare**, benzersiz varlık 1.0 / tekrar 0.0 (gerileme yok); ⚠ gerçek video **iki yapısal kısıt** ortaya çıkardı ve düzeltildi: (1) 1080p kaynak 1080p karede **sıfır punch payı** → video kaynakta dijital zoom **yok** (`VIDEO-KAMERA-NOTR`), (2) `static` süre kapısı hareketli kaynakta **geçersiz tahmin** → statik bacağı video atlıyor (enerji bacağındaki **mevcut** desenin aynısı); ⚠ **kapılar gevşetilmedi**, `KALITE-PUNCH-BUYUTME` ve `KALITE-OPTIK-DURGUN` duruyor, POST-QA optiği b004'te **4.366** ölçtü (eşik 2.0) → muafiyet bypass **değil**; (3) `girdi_kur` medya türünü sabit `"image"` yazıyordu — J-1'deki %0'ın **mekanik nedeni**, düzeltildi; ⚠ **KABUL EDİLMİŞ MP4 DEĞİL** — teknik tam PASS ama **semantik değil** (b001 hâlâ 1900 arşiv fotoğrafı, `KALITE-SEMANTIK-DONEM`); ⚠ ilk koşum `teknoloji_i20_rapor.json` + `i20_kare_*.png` üzerine yazdı, rapor git'ten **geri yüklendi**, smoke çıktı adları **parametrelendi**; 34 red-first **ağsız** test; deploy YOK |
| 14 Ağu | **J-4 video provenance/lisans sözleşmesi (YALNIZ ENGELLER)** | `4440a81` | ✅ **push edildi**, ağsız/indirmesiz koruyucu sözleşme: yeni `medya/video_lisans.py`, video kabulü için **8 zorunlu kanıt** (`kaynak_url`, `saglayici`, `lisans_turu`, **`lisans_kaydi`** — beyan değil, `indirme_zamani`, ffprobe ile ölçülen `codec`/`cozunurluk`/`bitrate`); biri eksikse **RED** ve eksik alan **adıyla** raporlanıyor; ⚠ **YouTube/Vimeo/TikTok/X vb.**: video **açıklamasındaki lisans beyanı TEK BAŞINA YETMİYOR** (`beyan_tek_basina_yeterli: False`), ayrıca `indirme_izni`+`tos_uyumu`+`hak_sahibi_dogrulandi` **üçü birden** şart, eksikse `PLATFORM-IZIN-KANITI-YOK` → RED; izinler açık olsa **bile** lisans kaydı videonun kendi sayfasıysa **beyan sayılıp** RED → ToS/telif ihlali yolu kapalı; **mevcut kapılar gevşetilmedi**: `lisans_karari()` **sarmalanıyor**, ARR/NC/ND/Getty reddi **asla çevrilmiyor**, görsel yolu **hiç değişmedi** (PD beyanı hâlâ geçiyor); red-first **kabul tabanıyla** kuruldu (temiz Commons videosu KABUL) ki kapı totolojik olmasın; ⚠ **bilerek edinim hattına bağlanmadı** ve **ağa çıkmıyor** → seçim/render davranışı değişmedi (HEAD worktree ile `render_plan`/`edit_manifest`/`props` SHA **birebir aynı**), **pilot üretilmedi**; I-23/I-24/I-25/I-38, eşikler, 22 alan, kullanıcı seçimleri, `deploy.sh` **korundu**; deploy YOK, $0.00 |
| 14 Ağu | **J-3 B-roll/cutaway çeşitliliği ölçüldü (kapı YOK)** | `e9034bb` | ✅ **push edildi**, ağsız tanısal: 7 bağımsız planda `kaynak_saglayici_dagilimi` (çekim **ve süre**), `benzersiz_varlik_orani`, `cekim_turu_dagilimi`, `tekrar_sure_orani`, provenance ve `gercek_video_*` ölçüldü; **taban**: benzersiz oran 6 planda 1.000 / `_smoke_editorv2` **0.750**, tekrar süresi 6 planda 0.000 / **0.126**, **çekim türü çeşidi 7/7 planda tam 3** (cutaway **dar**), tek sağlayıcı **süre** oranı 6 planda **1.000** / `_i20` **0.949**, **gerçek video 0.0** (açıkça 0 raporlanıyor, J-2a'dan okunuyor); ⚠ süre tabanlı ölçüm mevcut çekim tabanlı kapıdan **farklı bilgi** veriyor (`_i20` 0.80 → 0.949) → `SAGLAYICI-TEKEL` **çoğaltılmadı**; EMİN DEĞİLSEN ENGELLEME: kimlik yoksa oran **`None`** (1.0 değil), lisans boş/`unknown` ise provenance **ölçülemedi** + `uyari_adayi` (WARN **üretilmedi**, `durum`u değiştirirdi), J-2a yoksa video alanı **`None`**; `hedef: None`, `enforce: False`, **yeni fail kodu YOK**; red-first: doğal karşı-örnek `_smoke_editorv2` ayrışıyor + 5 sentetik müdahalenin **5'i** metriği tersine çeviriyor; **render değişmezliği kanıtlandı** (HEAD worktree, `render_plan`/`edit_manifest`/`props` SHA **birebir aynı**, QA WARN 0/3) → **pilot üretilmedi**; I-23/I-24/I-25/I-38, eşikler, lisans/provenance, 22 alan, kullanıcı seçimleri, `deploy.sh`, üretim seçim kodu **korundu**; deploy YOK, $0.00 |
| 14 Ağu | **J-2a medya türü rapor sözleşmesi (kapı YOK)** | `09edd97` | ✅ **push edildi**, J-1 tabanı uygulamanın kendi raporuna bağlandı: `olcumler["medya_turu"]` → `video_sure_orani` + `donmus_kadraj_sure_orani` (+ statik/ölçülemedi oranları, kalemler); okuyucu deseni **mevcutla birebir** (`kare_okuyucu` dışarıdan, modül **dosya açmaz**), okuyucu yoksa oranlar **`None`** — 0.0 değil, çünkü 0.0 "video yok" **iddiasıdır**; ⚠ **seviye hatası ölçülüp ayrıştırıldı**: 0.155 **korpus agregası**, plan başına uygulanırsa **7 planın 4'ünde yanlış pozitif** → ayrı `DONMUS_KADRAJ_PLAN_REFERANSI = 0.334` (formül: `ceil(maks_gözlenen, 3)`), mevcut korpusta yanlış pozitif **0/7**; ikisi de **`enforce: False`**, hiçbir yerde uygulanmıyor; `VIDEO_SURE_ORANI_HEDEFI = None` — **uydurulmadı** (pozitif örnek yok); **yeni fail kodu YOK**, ölçüm modülü hüküm vermiyor; **render değişmezliği kanıtlandı** (HEAD worktree ile `render_plan`/`edit_manifest`/`props` SHA **birebir aynı**, QA WARN 0/3 aynı) → **pilot üretilmedi**; ⚠ yol boyunca gerçek kusur: `denetle()` imzasındaki bool `kalite_kapisi` parametresi modül adını **gölgeliyor** (→ `_KK` takma adı); I-23/I-24/I-25/I-38, eşikler, lisans/provenance, 22 alan, kullanıcı seçimleri, `deploy.sh` **korundu**; deploy YOK, $0.00 |
| 14 Ağu | **J-1 statik fotoğraf / gerçek video oranı ölçüldü (tanısal)** | `ca9ebc1` | ⚠ **push edildi**, kullanıcı önceliğinin 1. atomu, ağsız: 17 koşum → **7 benzersiz plan** (lawn'ın 10 render'ı **tek** örnek), 32 çekim / 118.5 sn; **gerçek hareketli video %0.0**, statik fotoğraf **süre %94.7** (Ken Burns %79.2 + **donmuş kadraj %15.5**), sentetik %5.3, **ölçülemedi %0**; sınıf kararı `medya_turu` alanına DEĞİL `ffprobe -count_frames` ile **dosyanın kendisine** dayanıyor, belirsiz olan varsayılmıyor; yanlış sınıflama payı **24/24 doğru** (4 gerçek MP4 → 4/4 `a_video`, 20 kaynak → 20/20 tek kare) ⚠ ama pozitif örnekler **render çıktısı**, korpusa hiç video kaynağı girmemiş; red-first: sahte korpusa video enjekte edilince iddia **KIRMIZI** yanıyor (totolojik değil); ⚠ kısıt **kod değil** — `avci`/`medya_kopru` varsayılanı zaten `"video"`; J-2 eşiği **önerildi ama ÜRETİME ALINMADI** (pozitif örnek yok, E türetilemez); üretim kodu/eşik değişmedi, rerender/deploy YOK, $0.00 |
| 14 Ağu | **I-58 iki aday düzeni karşı-olgu olarak ölçüldü (tanısal)** | `855a60c` | ⚠ **push edildi**, ağsız/ücretsiz karşı-olgu: **A** (farklı 2. aday) tekrar kapısından temiz, **B** (aynı adayın farklı kadrajı) **mevcut I-22 kapısını ihlal ediyor** (bitişik aynı varlık → `KALITE-MEDYA-TEKRAR` fail, üretimin kendi manifestinden canlı hesaplandı); B'yi bloke eden şeyin benzerlik **değil** yalnız `asset_id` olduğu **kaynak koddan** gösterildi (`medya_tekrari` aynı-kimlik çiftinde benzerlik bacağını `continue` ile atlıyor; üretimde `benzerlik_okuyucu=None`); ⚠ **belirleyici**: B **semantik kusuru gidermiyor** — b002 1900 arşiv fotoğrafını alıyor, I-47 uyarısı onun için de yanıyor (canlı çağrı); ⚠ çok-beatli sahne 17 koşumun 12'sinde var ama 10'u aynı planın yeniden render'ı → lawn ailesi dışında yalnız **iki** bağımsız iş (`_i20`, `_smoke_editorv2`) → yanlış pozitif payı güvenilir ölçülemez (I-34 dersi); ⚠ **kapanış denetiminde ÜÇ iddia ELENDİ ve silindi** — kadraj varyantı dHash'leri (0.59–0.77), beş varyantın beklenen optiği (2.83–3.48) ve lisans/provenance iddiası: üçü de sabit sözlükten okunup eşikle karşılaştırılıyordu, **yeniden türetilmiyordu** ve dayanağı (dHash uygulaması / E,d girdileri / ilgili kontrol) repoda **yok**; **üretime alınmadı**, üretim kodu değişmedi, rerender/deploy YOK, $0.00 |
| 14 Ağu | **I-57 b001/b002 seçim zinciri geriye izlendi (tanısal)** | `ab9b09e` | ✅ **push edildi**, üretimin kendi kayıtlarından: s001 cümlesi **ikiye kesilmiş**, b002 sahnenin **2. adayı** (puan 90→80) ve **kendi beat metniyle hiç aranmamış**; ⚠ ölçüldü ki `semantik_puan` varlık çıkmayınca **altı adayda da tam 50.0** (sıfır bilgi) ve `alaka_kapisi` bu korpusta **ters** çalışıyor — **3 yanlış adayın 3'ünü geçiriyor, 3 doğrudan 2'sini reddediyor**; b002'yi ayıran tek sinyal **yapısal** (aynı sahnenin rank≥2 adayı) ama **yanlış pozitif payı ölçülemez** (örnek büyüklüğü 1) → **üretime konmadı**; ⚠ b002 varlığı **yağmurlama değil** (Kanapou-Kahoolawe erozyon sahası; yağmurlama b004 ve **doğru**); üretim/render değişmedi, deploy YOK |
| 14 Ağu | **I-56 bağımsız kenar ölçüm hattı üretime alındı** | `ae438bd` | ✅ **push edildi**, I-54 yapılandırması + I-55 eşiği **uygulandı**: `kenar_ornek_komutu` (384×216 @ **8 fps**, optik 64×36@4fps sözleşmesinden **bağımsız**) + `kenar_dis_olcusu` (**dört yön**, en dış sütun/satır, eşik **6.234**); POST-QA'ya **geriye uyumlu** bağlandı (`kenar_dis` alanı + `POST-KENAR-DIS` fail kodu; eski `kenar`/`POST-KENAR-SIYAH` **aynen** duruyor); kabul ölçütü sağlandı: I-52 karşı-örneği **FAIL**, **17 temiz videonun 17'si PASS** → **kaçırma 0, yanlış pozitif 0**; 25.2 sn 1080p pilot **POST-QA PASS**, 11/11 kare SHA-256 aynı, **kabul edilmiş MP4 DEĞİL** (b001/b002 semantik), deploy YOK |
| 14 Ağu | **I-55 kenar eşiği türetildi (train→formül, held-out tek bakış)** | `e9f90c8` | ✅ **push edildi**, I-54'ün **ön-kayıtlı** bölünmesi değiştirilmeden okundu; eşik **yalnız TRAIN**'den açık formülle (`eşik = temiz_alt / 2` = **6.234**) türetildi ve TRAIN bandının içinde olduğu doğrulandı; **held-out'a tek bakış**: 4 kusurlu örneğin **4'ü yakalandı**, 7 temiz örneğin **7'si temiz** → **kaçırma 0, yanlış pozitif 0**; duyarlılık: güvenlik katı ~1.25–2494 aralığında sonuç değişmiyor; ⚠ ölçüm betiğinde pencere hatası bulunup düzeltildi (kusur 20.431→0.046, render değişmedi); **üretim kodu değişmedi** (eşik uygulanmadı, `KENAR_SIYAH_ESIGI` 16 duruyor), geçici varlıklar (345 MB) temizlendi, deploy YOK |
| 14 Ağu | **I-54 kenar kapısı korpusu genişletildi, ayrım payı ölçüldü** | `61ecca8` | ✅ **push edildi**, korpus **gerçek render**la genişletildi (4 yön kusurlu + 15 gerçek temiz pilot), train/held-out **ölçümden önce** sabitlendi; dört eksen **ayrı** raporlandı: tek yön **hiç** ayırmıyor (dört yön zorunlu), mevcut `şerit_ort` agregasyonu **negatif**, 64/128 çözünürlük **hiç**, **4 fps hiçbir çözünürlükte** ayırmıyor; ayrım iki eksene birden bağlı (256 ≥15 fps, **384 ≥8 fps**); ölçülen band **kusur ≤0.02 / temiz ≥9.96** — **örtüşme yok**; ⚠ I-53'ün "kusur ≤2.9" iddiası **doğrulandı**, "temiz ≥15.0" **yanlış** (gerçek taban **10.01**, `onizleme_lawn_i40`); **eşik seçilmedi**, üretim kodu **değişmedi**, geçici varlıklar (345 MB) temizlendi, deploy YOK |
| 14 Ağu | **I-53 kenar kapısı kör noktası: tek parametrelik düzeltme ELENDİ** | `f00ae2f` | ✅ **push edildi**, kör nokta sayısallaştırıldı: yatayda **yalnız ≥60 px** görülüyor, **dikey bant 120 px'te bile hiç** görülmüyor (yapısal — sadece sol/sağ şerit var); ⚠ **belirleyici**: I-52'nin gerçek 9 px bandı **4 fps ızgarasında hiç yok** (8 fps'te 0.0) → uzamsal düzeltme **tek başına yetmiyor**; sözleşmeyi bozmayan agregasyon düzeltmesi yanlış pozitif 0 ama **yeni fayda da 0**; kusuru yakalayan konfigürasyon (256/8 fps) **üç gerçek pilotta yanlış pozitif** üretiyor (15.8 vs eşik 16.0 — bıçak sırtı, gerçek koyu orman kenarı) → **üretim kodu DEĞİŞMEDİ**, geçici varlıklar temizlendi, deploy YOK |
| 14 Ağu | **I-52 pan taşma payı, pan yokken de zoom yolunu yiyordu** | `145986c` | ✅ **push edildi**, I-43 borcunun kök nedeni kodda gösterildi: `kbHesap` pan payını **koşulsuz** ödüyordu ama kayma yalnız `pan` bir yönken uygulanıyor → `pan: 'yok'` sahnelerde %3.49 boşa gidiyordu; **koşullu** düzeltme (taban 1.0349→1.012 yalnız pan yokken) gerçek render'da ölçüldü: pan'sız sahneler **+%9…+%35** optik, pan yapan sahneler **bit-bit aynı**; ⚠ payın pan yapan sahnede **gerekli** olduğu karşı-örnekle kanıtlandı (payı herkesten kaldırınca tam çözünürlükte **9 koyu sütun**), koşullu halde **0**; 25.2 sn 1080p pilot POST-QA **WARN** (tek kalan s1'in kök nedeni bu atom değil — görsel enerjisi), kenar **0/101 + tam çözünürlükte 0**, **kabul edilmiş MP4 DEĞİL**, deploy YOK |
| 14 Ağu | **I-51 eksik veri üretildi, doygunluk ölçülerek kabul edildi** | `ce6be80` | ✅ **push edildi**, gerçek editorv2 1080p'de **18 yeni kontrollü nokta** (2 enerji × {pan, zoom} × hedef d 0.5–1.3; parametreler üretimin kendi saf fonksiyonlarıyla **sayısal çözüldü**, ölçek tavanı yetmeyen 6 zoom noktası **düşürüldü**); **train/held-out ayrımı render'dan ÖNCE** diske sabitlendi; model TRAIN'de seçilip HELD-OUT'ta **tek kez** ölçüldü: doygunluk **HELD MAE 15.7%→7.6%**, **en kötü 38.7%→14.4%**, **fail bandı 1.442→1.748**, **yanlış fail 0** korundu → I-50'nin oracle beklentisi **doğrulandı**; `MODEL_K` 0.935 / `MODEL_D0` 3.012 / marj 0.144; eşikler gevşetilmedi; 25.2 sn pilot POST-QA **PASS**, **11/11 kare SHA-256 aynı**, **kabul edilmiş MP4 DEĞİL** (b001/b002 semantik), deploy YOK |
| 14 Ağu | **I-50 doygunluk terimi mevcut veriyle: ELENDİ** | `f4a0afe` | ✅ **push edildi**, sıkı train/held-out ile ölçüldü: **TRAIN'de d ≥ 0.5 olan nokta YOK** (0.016–0.289) oysa en kötü hata d=1.311'de → doygunluk parametresi train verisiyle **kısıtlanamıyor**; ek parametre TRAIN'i iyileştirip (9.4→7.8%) **HELD-OUT'u kötüleştiriyor** (10.6→11.8%) ve en kötü hatayı **büyütüyor** (22.4→27.3/28.2%) → **fail bandı daralıyor** (1.627→1.571/1.560), yani kapı daha az vaka yakalar; oracle (sızıntı) %6.0/%11.8 ile sinyalin **gerçek ama verinin yetersiz** olduğunu gösteriyor → **üretim modeli DEĞİŞMEDİ** (`MODEL_K` 0.8877, hata payı 0.229), rerender YOK, deploy YOK |
| 13 Ağu | **I-49 b005 tür/takson yerel olarak: ELENDİ** | `f136778` | ✅ **push edildi**, ölçüldü: kurulu taksonomi/ML paketi **yok**, `taksonomi.py` biyolojik değil, `webapp/veri/` altında tür verisi yok, 17 gerçek künyenin **21 alanında** tür/kategori alanı **yok**; tek çıkarılabilir sinyal (Latin ikili adlandırma, salt yapısal) örneklemde ayırıyor gibi görünüyor (negatif 2/3, pozitif 0/3, 17 adayda 1) **ama hüküm taşımıyor**: işaretlenen iki adaydan biri (b002) anlatımla **aynı özne ailesinde** — *Heteropogon contortus* bir **çim türü**; "tür adı var" ile "tür yanlış" ayrımı için yerel kaynak yok ve sinyal en iyi etiketlenmiş adayları cezalandırırdı → **üretim kodu DEĞİŞMEDİ**, b005 kabul engeli **sürüyor**, deploy YOK |
| 13 Ağu | **I-48 b002 yer/özne biyom sözlüğüyle: ELENDİ** | `7b8492d` | ✅ **push edildi**, ölçüldü: altı gerçek çiftin **hiçbirinde** sahne biyomu çıkmıyor (video bağlamı da boş) → kapı **yapısal olarak atıl**; yer adı eklense bile (Kahoolawe→tropik) **sahne tarafı boş** kaldığı için çelişki üretilemiyor; kök neden: sözlükte **"ılıman" kuşağı yok** ve lawn/grass hiçbir kuşakta değil; eklenecek iddia (**çim ⊥ tropik**) **faktüel olarak yanlış** (hawaii tropik listede, b002'nin öznesi *Heteropogon contortus* — bir çim türü); kelime örtüşmesi **ters** çalışıyor (iki POZİTİF kontrol sıfır kelime, negatif b002 iki kelime) → **üretim kodu DEĞİŞMEDİ**, b002 kabul engeli **sürüyor**, deploy YOK |
| 13 Ağu | **I-47 dönem kapısı çift yönlü: ilk otomatik semantik işaret** | `0d21107` | ✅ **push edildi**, `donem_kapisi` yalnız **sahne tarihselse** adayı denetliyordu; ters yön (**tarihsel aday, güncel sahne**) hiç görülmüyordu → `donem_uyarisi` (saf metin, **yeni sağlayıcı/ağ/API yok**); pilotun gerçek 6 çiftinde **yalnız b001** işaretlendi (17 gerçek adayda **1** işaret, yanlış alarm **0**), gözle doğrulandı (1900 arşiv fotoğrafı vs "right now"); **seçim değişmedi** (aday elenmez, 11/11 kare SHA-256 aynı), kod **warn** (`EMIN DEGILSEN ENGELLEME`); ⚠ b002/b005 bu sinyalle **ulaşılamaz** — kabul engeli **sürüyor**, deploy YOK |
| 13 Ağu | **I-46 risk optik birimde ifade ediliyor (enerji × yer değiştirme)** | `9a7438d` | ✅ **push edildi**, I-45 tek gezinme hızında kalibre olduğu için b002/b005'te **hüküm veremiyordu**; model **türetildi** (|ΔI| ≈ |∇I|·d) ve pan (öteleme) ile zoom (ölçek) alanları **ayrıldı**; 12 kontrollü nokta ile **k=0.8877** ölçüldü, **tutulan 6 gerçek çekimde** ort. hata **%10.8** / en kötü **%22.9**; risk artık **optik birimde** (eşik 2.0 aynen) ve fail yalnız `beklenen×1.229 < 2.0` iken → **kapsam dışı 2 → 0**, yanlış alarm **0**, `KALITE-OPTIK-DURGUN-BEKLENEN` **FAIL** seviyesine çıkarıldı (12+6 noktada yanlış fail yok); render **11/11 kare SHA-256 aynı**, POST-QA **PASS**, **kabul edilmiş MP4 DEĞİL** (b001/b002 semantik), deploy YOK |
| 13 Ağu | **I-45 enerji gösterilen kadraj bölgesinde ölçülüyor** | `79422de` | ✅ **push edildi**, I-44 enerjiyi **ekrana hiç gelmeyen** piksellerde de ölçüyordu → gösterilen bölge `Kamera.tsx` transformundan **birebir türetildi**; ⚠ **ölçüm hipotezi çürüttü** (kırpmada ölçmek yanlış alarmı azaltmadı, b005 ile **artırdı**) → gerçek kök neden ölçüldü: eşik **tek bir kamera konfigürasyonunda** (gezinme **0.0577/sn**) kalibre edilmişti; artık **kalibrasyon alanı dışında hüküm verilmiyor** → pilotta yanlış alarm **1 → 0** (PRE-QA warn 4→3), b002/b005 **bilgi** olarak raporlanıyor; fail'e **yükseltilmedi** (ölçüm kesinleşmedi), render **11/11 kare SHA-256 aynı**, POST-QA **PASS** ama **kabul edilmiş MP4 DEĞİL** (b001/b002 semantik), deploy YOK |
| 13 Ağu | **I-44 görselin uzamsal enerjisi ölçülüyor** | `5911e1c` | ✅ **push edildi**, düz görselin statik fotoğraf olarak hareket üretemediği I-43'te ölçülmüştü ama **hiçbir kapı ölçmüyordu** → `uzamsal_enerji_olcusu` + PRE-QA kapısı (**ölçülen eşik 11.589**); 25.2 sn editorv2 pilotunda kapı **doğru varlığı** işaretledi (b002, enerji 7.557), diğer 5 varlık (12.33–18.08) işaretlenmedi; render **11/11 kare SHA-256 aynı** (gerileme yok), POST-QA **PASS** ama **kabul edilmiş MP4 DEĞİL** (b001/b002 semantik, gözle doğrulandı), deploy YOK |
| 13 Ağu | **I-43 zoom kovaları optik ölçüm birimiyle hizalandı** | `ac3ef27` | ✅ **push edildi**, kovalar referans kanal birimindeydi (%/sn zoom), kapı ekran farkını ölçüyordu → **ölçülen taban 0.045**; 25.2 sn pilotta eşiği geçen sahne **2/6 → 5/6** (aynı props ile karşı-olgu render'ı), eşik gevşetilmedi, kova tablosu/aritmetik/22 alan dokunulmadı; POST-QA **WARN** (s1 — kök neden ölçüldü: **görsel enerjisi**, |grad| 4.21 vs 10.9–15.2), **kabul edilmiş MP4 DEĞİL**, deploy YOK |

---

## 9. Bu checkpoint'te KAPANAN maddeler

| Envanterdeki bulgu | Ne yapıldı | Nerede |
|---|---|---|
| §1 A–E motorları pipeline'a bağlı değil | **Araştırma motoru bağlandı.** `documentary` işlerinde konu → web araştırması → bağımsız kaynak doğrulaması → doğrulanmış olgular plan promptuna giriyor | `webapp/arastirma_kopru.py`, `pipeline.py:3613` |
| §2.1 `job_id` okunmuyordu | `isKimligiCoz()` `job_id`'yi birincil okuyor; boş kimlikte sessiz geçmiyor, hata veriyor | `api.js`, `wizard.js` |
| §2.2 ilerleme hep %0 | Tek üretici `is_sozlesme.normalize()` → `progress`+`ilerleme`+`yuzde` birlikte | `is_sozlesme.py` |
| §2.3 poll yok | `isDurumu()` artık çağrılıyor; 4 sn'de bir, arka planda durur, kap DOM'dan çıkınca temizlenir | `gorunumler.js` |
| §2.4 video erişilemez | İş kartında `<video>` oynatıcı + indirme + araştırma manifesti bağlantısı | `bilesenler.js`, `app.css` |
| §2.5 yanlış pozitif "Sistem hazır" | `?? 'ok'` kaldırıldı. `hazir/kisitli/kullanilamiyor`; alan yoksa **"Durum bilinmiyor"** | `gorunumler.js`, `saglik_derin.py` |
| §2.6–2.8 atıf/uyarı/kuyruk görünmez | Sözleşmede `attribution`, `warning`, `queue_position`; kartta çiziliyor | `is_sozlesme.py`, `bilesenler.js` |
| §2.9 makine-okunur aşama yok | `stage` + `stage_ad`; eşikler pipeline'ın **gerçek** `bildir()` yüzdelerinden | `is_sozlesme.py` |
| §3 Adım 4'ün karşılıksız vaadi | `kaynak_sayisi` / `dogrulanmis_iddia` artık gerçekten hesaplanıp işe yazılıyor | `pipeline.py` sonuç sözlüğü |
| §6 yerel test bloke | `VIDRUSH_KOK` → gerçek FastAPI yerel testi çalışıyor | `test_faz_h.py` §8 |

### Yeni dosyalar
- `webapp/arastirma_kopru.py` — Faz A motoru ↔ pipeline köprüsü (para tavanı, görünür düşüş, sır gizleme)
- `webapp/is_sozlesme.py` — tek tip iş sözleşmesi (yeni + eski alanlar birlikte)
- `webapp/saglik_derin.py` — gerçek bağımlılık ölçümü
- `webapp/testler/test_faz_h.py` — 163 test

### Tasarım kuralları (bozma)
1. **Araştırma hattı ASLA çökertmez.** Köprü istisna fırlatmaz; her başarısızlık `dususler`'e yazılır.
2. **Para tavanı zorunlu.** `MaliyetDefteri(tavan_usd=None)` **sınırsız** demektir — asla None geçme.
3. **Sır gizleme.** `dusus_ekle()` her `neden` metnini `gizle()`den geçirir; sağlayıcı 401 gövdeleri anahtar öneki yankılıyor.
4. **Eski alanlar silinmez.** `durum/ilerleme/yuzde/mesaj/video/kapak/hata/atiflar` doldurulmaya devam eder.
5. **Aşama eşikleri** `pipeline.bildir()` yüzdeleriyle senkron; biri değişirse `is_sozlesme.ASAMALAR` da değişmeli (test kilitliyor).

## 10. HENÜZ YAPILMADI (sonraki oturum)

| # | İş | Not |
|---|---|---|
| 1 | **Medya (Faz B) + Editor (Faz C/D) motorlarını bağla** | Araştırma bağlandı; `medya/avci` (6 sağlayıcı + lisans duvarı) ve `editor/*` hâlâ yalnızca test betiklerinde |
| 2 | **QA kapısı (H6)** | `editor/qa_son.denetle` render sonrası işe bağlanacak → `job.qa`. Sözleşmede `qa` alanı hazır, şu an boş dict |
| 3 | **Otomatik analiz (H4)** | Konu/tam metin sınıflandırma, dil, tür, risk → otomatik stil/ses/süre seçimi |
| 4 | **Shackleton pilotu (H8)** | Yerelde node_modules yok → render edilemiyor; canlıda yapılmalı |
| 5 | Ayarlar'daki sabit kodlu `KAYNAK_ZINCIRI` / `ENTEGRASYONLAR` | Hâlâ dekoratif; derin sağlıktan beslenmeli |
| 6 | Marka kiti oluşturma/silme UI'ı | `POST/DELETE /api/profil` hâlâ UI'sız |
| 7 | Belgeselde etkisiz kontroller (palet/arkaplan/ışık/görsel model) | Türe göre gizlenmeli |

## 11. ⛔ DEPLOY ENGELİ — `origin/main` ile derin ayrışma (12 Ağu, ölçüldü)

**Deploy denenmedi ve denenmemeli.** Ölçüm:

```
merge-base:                     2793be1
main'de olup bizde OLMAYAN:     13 commit
bizde olup main'de olmayan:     36 commit
```

`main`'in en son commit'i (`a61c24d`) tam olarak şu:
> *"deploy.sh EZME koruması: yerel kopya origin/main'in gerisindeyse deploy durur — bugün 3 kez yaşanan 'eski kopyayla canlıyı ezme' kazasını kökten engeller"*

Bizim branch'te o koruma **yoktu** (merge ile geldi). Bu branch'ten deploy edilseydi, ekibin 13 commit'i canlıdan silinirdi — korumanın engellemek için yazıldığı kazanın aynısı.

### `main`'de olup bizde olmayan canlı özellikler
- Grok video motoru (`grok-imagine-video`, Sora'nın yarı fiyatı) + bakiye güvencesi
- Ünlü modu (`unlu` — **22. generate alanı**) + CELEBRITY OVERRIDE
- Ses kütüphanesi: sayfalama (2071 ses), disk önbelleği, hız sınırı dayanıklılığı, Vbee/Klon sekmeleri
- Hikâye Stüdyosu video süresi seçici
- `deploy.sh` ezme koruması

### Deneme merge sonucu
`git merge origin/main` → `deploy.sh` **temiz birleşti** (ezme koruması + alt paket kopyalama birlikte). 3 çatışma:

| Dosya | Çatışma | Niteliği |
|---|---|---|
| `webapp/server.py` | 2 | **Mekanik.** main `unlu` alanını + `XAI_KEY`'i ekledi; bizim `/api/saglik` zaten üst küme. İkisi de alınır. |
| `webapp/pipeline.py` | 3 | **Orta.** main Grok/ünlü mantığı ekledi, biz araştırma köprüsü. Kesişmiyorlar. |
| `webapp/static/index.html` | 2 | **AĞIR — asıl karar burada.** |

### Asıl mesele: iki ayrı arayüz kuşağı
- Bizim branch: **76 satır** modüler `index.html` + `ui/app.js` + `js/*.js` (Faz F/G)
- `main`: **1761 satır** eski monolit, inline script/style; `ui/app.js`'i hiç çağırmıyor

**Faz F/G arayüzü hiç canlıya çıkmamış.** Bu arada `main` yeni özellikleri *eski* arayüze eklemiş. Yani merge "hangi satır kalsın" değil, **hangi arayüz kuşağı canlıya gidecek** sorusu.

### Önerilen sıra (sonraki oturum)
1. `git merge origin/main` — `server.py` + `pipeline.py` çatışmalarını **birleştirerek** çöz (ikisini de al, birini atma).
2. `unlu` alanını sözleşmeye ekle: `api.js GENERATE_ALANLARI` 21 → **22**, `test_faz_h.py` §5 sayısı güncellensin.
3. `index.html`: **bizim modüler sürümü koru**, `main`'in 4 UI özelliğini yeni arayüze taşı (süre seçici, ünlü anahtarı, ses kütüphanesi sekmeleri, Grok maliyet metinleri).
4. A–H'yi yeniden koş → yeşil.
5. `bash deploy.sh` (artık ezme koruması var, `GERIDE=0` olacak).

Yedek branch: `fazh-yedek-e4af286`.

---

## 12. ✅ CANLI DEPLOY + SHACKLETON PİLOTU (12 Ağu, ölçüldü)

Merge sonrası `bash deploy.sh` → **başarılı**. Ezme koruması `GERIDE=0` ile geçti, 48 dosya derlendi, 8 uç 200, imaja basıldı.

### Canlı smoke
| Kontrol | Sonuç |
|---|---|
| `/api/saglik/derin` | `durum: hazir`, `uretim_mumkun: true`, 8/8 bileşen ok, render motoru `ffmpeg` |
| Anahtar sızıntısı | **yok** (`sk-`/`AIza` taraması temiz) |
| Modüler arayüz | `index.html` 76 satır canlıda; `ui/app.css`, `ui/app.js`, `ui/js/*.js` hepsi 200 |
| Sağlık göstergesi | "Sistem hazır" artık **ölçülmüş** iddia (ffmpeg/ffprobe/disk/render/işçi/araştırma tek tek yeşil) |

### Pilot: "Shackleton'ın Endurance seferi ve mürettebatın kurtuluşu"
`tur=documentary`, `sure_dk=1`, `altyazi=1` · iş `job_1786491521724_fazh15_102297`

**Aşama geçişleri canlı izlendi** (polling ile): `sirada → arastirma(2%) → plan(5%) → medya(33-39%) → kapak(72%) → render(79-90%) → ses(96%) → bitti(100%)`

| Ölçüm | Değer | Hedef | Durum |
|---|---|---|---|
| Araştırma | 3 kaynak, 5 iddia, **1 doğrulanmış**, 5 sorgu | — | çalıştı |
| Araştırma maliyeti | **$0.3016** (tavan $0.60) | ≤ $0.60 | ✅ |
| Toplam oturum maliyeti | ~$0.30 + görsel yok | ≤ $2.00 | ✅ |
| Süre | 77.95 sn | 60 sn | ⚠ **%130** |
| Çözünürlük / fps | 1920×1080 / 24 | 1080p | ✅ |
| **Loudness** | **−14.0 LUFS**, tepe **−1.5 dBFS** | −14 / ≤−1.5 | ✅ **tam isabet** |
| Siyah kare | 0 | 0 | ✅ |
| Donmuş kare | 0 | 0 | ✅ |
| Kesme (scene>0.12) | 10 | — | ölçüldü |
| **AI görsel üretimi** | **0** | 0 (yasak) | ✅ **kural korundu** |
| Dosya boyutu | 241 MB / 78 sn (25.9 Mbps) | — | ⚠ çok yüksek |

**Arayüz canlı doğrulaması** (Projeler ekranı, tarayıcı): iş kartında `<video>` oynatıcı ✅, "Videoyu indir" ✅, "Araştırma manifesti" ✅, etiketler `Tamamlandı · 3 kaynak · 1 doğrulanmış olgu` ✅.

### ⚠ PİLOTUN ORTAYA ÇIKARDIĞI GERÇEK SORUN — medya yer/dönem isabeti

Sunucu logu:
```
pexels OK [South Georgia island approach boat/large]:
  "aerial view of boat approaching TROPICAL shore"
```
Videoda bu klip **"GÜNEY GEORGIA / SAHİL"** alt bandıyla gösteriliyor. Güney Georgia sub-Antarktik bir ada; ekrana tropik sahil geldi.

Bu tam olarak `webapp/medya/` (Faz B) modülünün K1–K4 yer doğrulama katmanlarının + `vision.py`'nin yakalamak için yazıldığı hata sınıfı — **ama o modül hâlâ pipeline'a bağlı değil.** Araştırma motoru bağlandı, medya motoru bağlanmadı.

**Sonuç:** Faz H'nin bir sonraki en yüksek etkili işi net — `medya/avci` + `medya/vision` + lisans duvarını `/api/generate` hattına bağlamak (§10 madde 1).

---

## 13. FAZ H4/H5/H6 — kritik kalite açığı kapatıldı (12 Ağu, 2. oturum)

### H5 — Medya doğruluk kapısı (`webapp/medya_kapisi.py`)

Pilotun kanıtladığı hatanın **kök nedeni**: `kaynak.py`'nin yer kapısı
`YER_TAKMA_AD` tablosuna bağlı ve o tablo **19 ülke** içeriyor.
`South Georgia`, `Antarctica`, `Elephant Island`, `Patagonia` tabloda **yok** →

```
_sorgu_yer_terimleri("South Georgia island approach boat")  → []
_etkin_yer(...)                                            → []
_yer_dogru_mu(h, [])                                       → True   ← KAPI YOK
```

Yani **tablonun dışındaki her yer için hiçbir kapı çalışmıyordu.** Canlı logda
`yer baglami: yok (sayim: {})` bunu birebir doğruluyor.

**Çözüm:** ülke tablosundan **bağımsız** biyom çelişki kapısı.
`kutup / tropik / col` kuşakları; sahne ile aday çelişiyorsa aday **düşer**.
Ayrıca dönem kapısı: tarihsel sahnede modern teknoloji işareti → red.

Kural: **emin değilsen geçir** — biyom çıkmıyorsa kapı uygulanmaz
(yanlış pozitif de kalite kaybıdır).

Bağlantı: `kaynak.py`'nin **dört** eleme noktası (pexels/pixabay/coverr/youtube).
`pipeline.video_baglami_kur()` genel konu metnini verir. Redler sessiz değil:
`sonuc["medya_kapisi"]` + `dususler`.

**Canlı kanıt** (konteynerde çalıştırıldı):
```
PILOT VAKASI -> REDDEDILDI
  BIYOM CELISKISI: sahne 'kutup' kusagi, aday 'tropik' kusagi
MESRU KLIP   -> GECTI
```

### H6 — Render sonrası QA kapısı (`webapp/qa_kopru.py`)

`editor/qa_son.py` Faz C'de yazılmıştı ama pipeline onu **hiç çağırmıyordu**;
sözleşmedeki `qa` alanı **her zaman boş sözlüktü**.

Şimdi: ffprobe + siyah + donmuş + kesme + loudness + sessizlik →
`PASS / WARN / FAIL / OLCULEMEDI`.

- **QA hattı çökertmez.** Ölçüm patlarsa `OLCULEMEDI` yazılır — sessizce PASS denmez.
- **Kontrollü retry:** yalnızca ses sorunlarında, bir kez, ve yalnızca
  **ücretsiz + deterministik** yol (loudnorm remaster). Görsel yeniden üretmek gibi
  **para harcayan retry yok** — test bunu kilitliyor.
- **QA FAIL işi "başarılı" göstermez:** sözleşmeye `kalite` + `kalite_ok` eklendi.
  Arayüz FAIL'de "Tamamlandı" **demiyor**, kırmızı **"Kalite: BAŞARISIZ"** rozetini
  gösteriyor. QA hiç yoksa `OLCULMEDI` → PASS varsayılmıyor.

**Gerçek pilot videosunda doğrulandı** (78 sn Shackleton çıktısı):
`WARN` — 1920×1080, 24 fps, 77.952 sn, **−14.05 LUFS**, tepe **−1.47 dBTP**,
LRA 3.3, siyah 0, donmuş 0, kesme 10.
Yakalanan 3 sorun elle bulduklarımın **aynısı**: `POST-FPS` (24 vs profil 30),
`POST-SURE-SAPMA` (78 vs 60), `POST-SESSIZLIK` (2.8 sn boşluk).

### H4 — Otomatik girdi analizi (`webapp/girdi_analizi.py`, `POST /api/analiz`)

Kullanıcı yalnızca metin + stil verir; sistem ölçülebilir gerekçeyle seçer.

- **LLM çağrısı YOK** — tamamen deterministik ve ücretsiz (test kilitliyor).
- Girdi türü (konu / tam-metin), dil, içerik türü (belgesel/seyahat/açıklayıcı/
  ürün/hikâye), dönem, kişi/yer adları, risk taraması.
- **Kullanıcının açık seçimi her zaman kazanır**; yalnızca boş alanlar doldurulur
  ve hangisinin otomatik seçildiği `otomatik_secimler` içinde **raporlanır**.
- Sinyal zayıfsa **"belirsiz"** der — zorla tür seçmez.

Wizard Adım 4 artık gerçek analizi gösteriyor. Ölçülemeyenler (kaynak sayısı,
doğrulanmış iddia, kullanılabilir medya, sahne sayısı, maliyet) hâlâ dürüstçe
**"Üretim sırasında ölçülecek"** diyor — uydurma sayı yok.

### Bu oturumda yaptığım ve düzelttiğim iki hata

1. Kapıyı bağlarken `klip_gecmisi_sifirla()` gövdesini kazara ezdim
   (blok `_YER_BAGLAM = []` satırını fonksiyon **içinde** yakaladı) ve import
   fonksiyon içine kaçtı. **H1'de deploy.sh'e eklediğim pyflakes taraması yakaladı** —
   canlıya gitseydi site açılmazdı. Onarıldı; artık testle kilitli.
2. `qa_kopru.ozet()` `qa_son`'un anahtarlarını yanlış okuyordu (`"sure"/"I"/"Peak"` —
   bu adlar `qa_son`'da yok). Süre ve LUFS arayüzde hep boş görünüyordu.
   Gerçek pilot videosunda ölçerek yakalandı; doğru adlar testle kilitli.

### Bilinen sınır (dürüstçe)

Biyom kapısı **iklim kuşağı** çelişkisini yakalar, **ülke** karışıklığını değil.
2. koşuda `"small boat South Georgia sea storm"` sorgusuna
`"maltese pilot motorboat"` geldi — Malta Akdeniz'dir ama tropik/kutup işareti
taşımadığı için kapı tetiklenmez. Bunun için `medya/vision.py`'nin kare-bakan
doğrulaması gerekir (§10 madde 1'in kalan yarısı).

---

## 14. Test çalıştırma (yerel)

```bash
python3 -m venv .venv-test
.venv-test/bin/pip install fastapi python-multipart httpx pillow requests edge-tts pyflakes
for t in a b c d e f g h i; do .venv-test/bin/python webapp/testler/test_faz_$t.py; done
```

⚠ **`edge-tts` ve `pyflakes` şart** (12 Ağu ölçümü): ikisi eksikken Faz H
`202/1 hata + 2 BLOKE` veriyor; ikisi kuruluyken **257/0/1 BLOKE**. Kalan tek
BLOKE `QA_TEST_VIDEO` (opsiyonel ölçüm videosu). Paketleri sistem python'ıyla
koşmak da çalışır ama Faz H'nin **gerçek FastAPI uç testleri bloke kalır**.

⚠ **`node` şart** (Faz I-3): `autoStilKimligi`/`autoTuru` doğruluk tabloları
node ile gerçekten çalıştırılır. node yoksa o 20 kontrol **BLOKE** yazılır,
PASS sayılmaz.

⚠ **Arayüzü yerelde açmak** (ücretsiz, ücretli çağrı yok):
```bash
cd webapp && VIDRUSH_KOK=/tmp/vidrush-kok ../.venv-test/bin/python -m uvicorn server:app --port 8799
```
`/opt/vidrush` yerine geçici kök kullanılır; `app/uret.py` o kökte bulunmalı.

Faz H fastapi olmadan da koşar; gerçek uç bloğu **BLOKE** yazar ve başarı saymaz.
Faz I ağ/para harcamaz — kapı kararı saf fonksiyondur, entegrasyon sahte okuyucuyla koşar.

---

## 15. FAZ I-1 — KARE KAPISI gerçek medya seçim akışına bağlandı (12 Ağu, ölçüldü)

### Kapatılan açık

§13'ün son satırı ("Bilinen sınır") bu maddeyi açık bırakmıştı:

```
sorgu   : "small boat South Georgia sea storm"
gelen   : "maltese pilot motorboat"     (Pexels)
kapı    : TETİKLENMEDİ
```

**Kök neden ölçüldü — kare bakan katman zaten vardı ama devre dışıydı:**

| Katman | Neden yakalayamadı |
|---|---|
| `kaynak._yer_dogru_mu` | `YER_TAKMA_AD` = **19 ülke**. Ne Malta ne South Georgia tabloda. |
| `medya_kapisi.biyom_kapisi` | "maltese pilot motorboat" metni ne tropik ne çöl işareti taşıyor → çelişki çıkmıyor. Testte kilitli: bu vaka **hâlâ** metin kapısından geçiyor. |
| `kaynak._vision_yer_uygun` | **Yalnızca `yer_terim` doluyken** çalışır. Tablo dışı yerde `_etkin_yer()` boş döner → **vision hiç çağrılmaz.** |

Yani kare bakan katman tam da gerektiği vakada kapalıydı.

### Yeni: `webapp/medya/kare_kapisi.py` (tablo BAĞIMSIZ)

- **Bölge/havza tablosu:** 17 bölge · 266 yer terimi · 14 havza · 7 komşuluk grubu
  (`kare_kapisi.kapsam_ozeti()` ile **ölçülebilir** — "her yeri biliyoruz" iddiası yok).
- **Havza kuralı, ülke kuralı değil.** Red yalnızca kabaca kıta/deniz havzası
  farklıysa verilir. Malta → `avrupa_akdeniz`, South Georgia → `guney_kutup` → **RED**.
- **`karar()` SAF fonksiyon** — ağ/dosya/saat görmez. Pilot vakası testte doğrudan kilitli.

### Yanlış pozitif korumaları (hepsi testli)

| Durum | Davranış | Kod |
|---|---|---|
| Gözlem güveni < 0.6 | GEÇER | `DUSUK-GUVEN` |
| Boş/okunamayan gözlem | GEÇER | `GOZLEM-YOK` |
| Kültürel ipucusuz yakın plan | GEÇER | `YAKIN-PLAN` |
| Karede tanınan bölge yok | GEÇER | `BOLGE-CIKMADI` |
| Sahneden beklenti çıkmıyor | GEÇER, **okuma bile yapılmaz** | `BEKLENTI-YOK` |
| Komşu havza (Fransa ↔ Akdeniz, Patagonya ↔ Ge. Amerika) | GEÇER | — |
| Aday hem beklenen hem başka bölge işareti taşıyor | GEÇER | — |
| Okuyucu istisna fırlattı | GEÇER, gerekçe görünür | `OKUMA-HATASI` |
| Bütçe doldu | GEÇER + işe **dürüstçe** yazılır | `BUTCE` |

### Katı süre ve maliyet sınırı

`KareButce(maks_cagri, maks_usd, maks_sn)` — **üçü de zorunlu**, `None` geçmek
`ValueError`. Varsayılan: **60 çağrı / $0.08 / 180 sn** (env: `KARE_MAKS_*`).

- `yer_ayir()` kontrol + harcamayı **tek kilit altında** yapar. Kilitsiz sayaçla
  paralel `_sahne_medya` thread'leri tavanı aşıyordu — test 8 thread × 20 deneme
  ile bunu kilitliyor (tavan 10 → tam 10 verildi).
- **Tek vision çağrısı/klip.** Eski `_vision_yer_uygun` ile birlikte koşsa klip
  başına iki fatura çıkardı; yeni okuma ikisinin sorduğunu birden döndürür.

### kaynak.py entegrasyonu

`_kare_dogrula()` tek giriş noktası. **Dört sağlayıcı da** indirme sonrası bağlı:

| Sağlayıcı | Önce | Şimdi |
|---|---|---|
| pexels | `_vision_yer_uygun` (tablo bağımlı) | `_kare_dogrula` |
| pixabay | `_vision_yer_uygun` (tablo bağımlı) | `_kare_dogrula` |
| coverr | **kare kapısı YOKTU** | `_kare_dogrula` |
| freepik | **kare kapısı YOKTU** | `_kare_dogrula` |

**Gerileme yok:** kapı uygulanamazsa (`BEKLENTI-YOK` / `BUTCE` / `OKUMA-HATASI` /
`OKUYUCU-YOK`) eski `_vision_yer_uygun` katmanı çalışır. Reddedilen klip diskten
silinir, sıradaki aday denenir. `KARE_KAPISI=0` ile tek env'den kapatılır.

⚠ Freepik'te kota sayacı geri alınmaz — indirme sağlayıcı tarafında **gerçekten**
oldu; sahte muhasebe yapılmıyor.

### pipeline.py

`sonuc["kare_kapisi"]` = `{acik, kapsam, butce, red_sayisi, redler}`.
Redler `dususler`'e yazılır. **Bütçe engeli de yazılır** — "kalan klipler kare
doğrulaması OLMADAN geçti, yer isabeti bu klipler için garanti değil".
Kapı hiç çalışmadıysa `butce.cagri == 0` bunu görünür kılar; "her kare doğrulandı"
gibi kanıtsız iddia üretilmez.

### Ölçülen test sonucu (12 Ağu)

| Paket | Geçen | Başarısız |
|---|---|---|
| A | 125 | 0 |
| B | 200 | 0 |
| C | 148 | 0 |
| D | 95 | 0 |
| E | 127 | 0 |
| F | 242 | 0 |
| G | 217 | 0 |
| H | 203 | 0 (2 BLOKE) |
| **I (yeni)** | **81** | **0** |
| **TOPLAM** | **1438** | **0** |

**BLOKE (gizlenmiyor):** Faz H'de 2 blok — `QA_TEST_VIDEO` ayarlanmadı (opsiyonel)
ve gerçek uç testi için `fastapi` yerelde kurulu değil (`.venv-test` bu oturumda
yok). İkisi de **başarı sayılmıyor**. Faz I-1 `server.py`'ye dokunmuyor; import
sağlığı `test_faz_i` §7 (gerçek `import kaynak`) ve `test_faz_h` §9 (51 dosya
derleniyor) ile kapsanıyor.

### Bu adımda düzelttiğim iki şey

1. `KareButce` ilk yazımda kilitsizdi. `_sahne_medya` **paralel** koşuyor;
   "kontrol et sonra harca" yarışı tavanı aşırırdı — yani "katı sınır" iddiası
   karşılıksız kalırdı. Kilit + `yer_ayir()` eklendi, thread testi kilitledi.
2. Statik entegrasyon testi `_kare_dogrula\([^)]*"pexels"` deseniyle yazılmıştı;
   `_etkin_yer(sorgu)` iç parantezi yüzünden desen ilk `)`de duruyor ve **kod
   doğruyken test kırmızı yanıyordu**. Desen düzeltildi (kod değil).

### Henüz YAPILMADI (I-1'in kalan borcu)

- **Gerçek ücretli pilot yok.** Kapının canlı isabet oranı ölçülmedi; iddia
  yalnızca "karar mantığı doğru", "model doğru okuyor" **değil**.
- Bölge tablosu 17 satır — dünya haritası değil. Tablo dışı yerde kapı biyoma düşer.
- `medya/vision.py` (Faz B enjekte edilebilir puanlayıcı) hâlâ sıralama tarafında
  bağlı değil; I-1 yalnızca **kapı** yolunu bağladı.

---

## 16. FAZ I-2a — HİYERARŞİK KONSEPT / NİYET TAKSONOMİSİ (12 Ağu, ölçüldü)

### Kapatılan açık

`girdi_analizi.TUR_SINYALI` **sabit beş etiket** tutuyordu
(belgesel/seyahat/açıklayıcı/ürün/hikâye) ve kararı **tek bir anahtar-kelime
sayımına** dayandırıyordu. Ölçülen sonuçlar:

| Girdi | Eski sonuç |
|---|---|
| `"3-1'lik maçın 90. dakikasındaki golle biten derbi özeti"` | **belirsiz** |
| `"iPhone 15 vs Galaxy S24 fiyat karşılaştırması"` | ürün (alt tür **yok**) |
| `"kabus gibi bir gece: kapının ardındaki gölge"` | **belirsiz** |

### Yeni: `webapp/taksonomi.py` — **ayrı modül, eski sözleşmeye dokunmadı**

- **7 aile · 33 dal · 690 anahtar · 18 yapısal sinyal · 50 sinyal bağı ·
  94 karşıt terim** — hepsi `kapsam_ozeti()` ile **sayılabilir**
  (ölçüm: `python3 -c "import taksonomi; print(taksonomi.kapsam_ozeti())"`).
  Aileler: `belgesel · seyahat · egitim · hikaye · urun · yasam · kultur`
- **Yeni konsept eklemek = `AGAC`a bir satır.** Motor kodu değişmez.

### Sadece kelime listesi DEĞİL — ölçülebilir yapısal sinyaller

Karar iki bacaklı: (a) sözlük isabeti, (b) metnin **biçiminden** sayılan kanıt.
18 sinyal: `yil · eski_yil · para · yuzde · skor · dakika · olcu · adim · soru ·
cozunurluk · emlak_olcu · model_no · karsilastirma · diyalog · emir · borsa ·
suc · kisi_adi`.

Bunlar konu kelimesinden bağımsız çalışır — testte kilitli: `"2-0, 45. dakika"`
metninde hiçbir spor kelimesi yokken `skor` ve `dakika` sinyalleri ölçülüyor.

### Dürüst güven ve fallback

`guven = min(0.95, 0.30 + 0.45·marj + 0.20·min(kanıt,5)/5)` — formül açık,
uydurma metrik yok. Tavan **0.95**: hiçbir deterministik sınıflandırma
"kesin doğru" değildir.

| Durum | Koşul | Davranış |
|---|---|---|
| `belirsiz` | kanıt < 2 **veya** güven < 0.40 | **Zorla etiket YOK.** `yol="belirsiz"`, gerekçe sebebi yazar |
| `melez` | 1. ve 2. aday marjı < 0.25 | Tek etikete ezilmez; **ikincil dal raporlanır** |
| `zayif` | 0.40 ≤ güven < 0.60 | Etiket verilir ama güven düşük olarak işaretlenir |
| `kesin` | güven ≥ 0.60 | — |

Adaylar **her zaman** raporlanır (kara kutu yok).

### Sınırlı model analizi — klamplı, varsayılan KAPALI

`siniflandir(metin, model_coz=None)`. **Bu modülde hiçbir ağ çağrısı yok**
(testte kilitli: `requests`/`openai.com`/`http` dizeleri dosyada geçmiyor).

- Model **yalnızca** `durum ∈ {belirsiz, melez, zayif}` iken çağrılır —
  kesin kararda çağrılmaz (boşa para yok, testli).
- Model **yalnızca motorun ürettiği aday listesinden** seçebilir. Liste dışı
  cevap → **YOK SAYILIR**, deterministik karar korunur, `model_notu` ile görünür.
- Model istisna fırlatırsa deterministik karar korunur.
- Model güveni **0.90'ı aşamaz** (deterministik tavan 0.95'in altında).

### Geriye uyumluluk — BOZULMADI

| Kilit | Durum |
|---|---|
| `girdi_analizi.TUR_SINYALI` hâlâ 5 etiket | ✅ testli |
| `girdi_analizi.tur_tespit()` davranışı | ✅ değişmedi, testli |
| `GORSEL_STRATEJISI` | ✅ dokunulmadı |
| `/api/analiz` sözleşmesi | ✅ dokunulmadı |
| `taksonomi.ESKI_ETIKET` | her aile → eski 5 etiketten biri; beş değerin dışına çıkmıyor (testli) |

`taksonomi.py` **hiçbir yerden import edilmiyor** — bu adımda motor yalnızca
yazıldı ve testlendi. Akışa bağlanması I-2c'ye ait.

### Bu adımda düzelttiğim gerçek tasarım açığı

Katı kelime sınırı Türkçe eklerde sözlüğün yarısını körleştiriyordu:
`"kara delik"` → `"kara delikler"`e, `"teori"` → `"teorisi"`ne,
`"arastirmacilar"` → `"arastirmacilarinin"`e **uymuyordu**. `bilim` konsepti bu
yüzden `belirsiz` çıkıyordu (4 test kırmızı).

Çözüm: **sol sınır katı** (kelime ortasında eşleşme yok), sağda **sınırlı** ek
toleransı — en fazla 6 harf ve yalnızca ≥5 harfli terimlerde. Kısa terimlerde
tolerans yok, çünkü `"gol"` → `"gölge"`, `"kek"` → `"kekik"` gibi yanlış
pozitifler gelirdi. Yedi ayrı test bu sınırı kilitliyor.

⚠ Bu değişiklik **yalnızca `taksonomi.py`** içinde; `medya_kapisi` ve
`kare_kapisi` İngilizce yer adlarıyla çalıştığı için dokunulmadı.

### Ölçülen test sonucu (12 Ağu)

| Paket | Geçen | Başarısız |
|---|---|---|
| A | 125 | 0 |
| B | 200 | 0 |
| C | 148 | 0 |
| D | 95 | 0 |
| E | 127 | 0 |
| F | 242 | 0 |
| G | 217 | 0 |
| H | 203 | 0 (**2 BLOKE**) |
| I (I-1 + I-2a) | **234** | 0 |
| **TOPLAM** | **1591** | **0** |

I paketi I-1'de 81'di → I-2a ile **+153** test (12+ konsept matrisi, yapısal
sinyaller, belirsizlik/melez, klamplı model yolu, Türkçe ek sınırı).

**BLOKE (PASS sayılmadı):** Faz H'de 2 blok — `QA_TEST_VIDEO` ayarlanmadı
(opsiyonel) ve gerçek uç testi için `fastapi` yerelde kurulu değil
(`.venv-test` bu oturumda yok). I-2a `server.py`'ye dokunmuyor.

### Test edilen 19 konsept

Rockefeller tarih belgeseli · biyografi (Curie) · İsviçre 4K gezi · bilim
(kara delik) · teknoloji (yapay zekâ) · finans (enflasyon/borsa) · spor (derbi
özeti) · true crime · yemek tarifi · eğitim/ders · ürün tanıtımı · müzik/kültür ·
korku hikâyesi · çocuk hikâyesi · emlak turu · otomotiv sinematik · haber
analizi · meditasyon ambient · ürün karşılaştırma.

Her konsept için 5 ayrı iddia doğrulanıyor: aile, alt tür, `durum ∈ {kesin,
melez}`, gerekçenin ölçülen sayı içermesi, eski etikete indirgenmesi.

### BİLİNEN LİMİTLER (dürüstçe)

1. **Ağaç dünyayı kapsamıyor.** 33 dal; kapsam dışı girdi `belirsiz` döner —
   bu tasarım gereği, eksiklik gizlenmiyor.
2. **Kapsam dışı iddia yok.** "Tüm stilleri biliyoruz" denmiyor; kapsam
   `kapsam_ozeti()` ile sayılıyor.
3. **Gerçek kullanıcı girdisiyle isabet oranı ölçülmedi.** Kanıt 19 kürasyonlu
   test metni; canlı dağılımda başarım **bilinmiyor**.
4. **Model yolu hiç gerçek modelle koşulmadı** — sahte çağrılabilirle test
   edildi. Ücretli çağrı yapılmadı.
5. **Ek toleransı Türkçeye özel** ve sezgisel (6 harf / ≥5 karakter). İngilizce
   çoğullarda da çalışır ama diğer eklemeli dillerde test edilmedi.
6. **Motor henüz akışa bağlı değil** — `girdi_analizi`/`pipeline` bu adımda
   `taksonomi`yi import etmiyor.

### SONRAKİ ADIM (I-2b/I-2c)

- I-2b: sürümlü **stil profili** kaydı (anlatım yapısı, tempo, geçiş, kamera,
  tipografi, palet, müzik, medya stratejisi, oran/kanal/süre, kanıt-lisans
  kuralları, QA eşikleri) — **bu adımda yazılmadı.**
- I-2c: `girdi_analizi.analiz()` içine `konsept` alanı olarak **ek** bağlama
  (eski alanlar korunarak) + Auto ↔ kullanıcı seçimi önceliği.

---

## 17. FAZ I-2b — SÜRÜMLÜ BİLEŞİK STİL PROFİLLERİ (12 Ağu)

> **Durum (güncellendi): commit `fff3f36`, `origin/arastirma-motoru`'na PUSH EDİLDİ.**
> Akışa bağlanması **I-2c**'de yapıldı (bkz. §18). Deploy **yapılmadı**.

### Kapatılan açık

Stil bugün **tek bir etiket** (`"sinematik-belgesel"`) ve o etiketin arkasındaki
sözlük `pipeline.EDIT_STILLERI` içinde düz duruyor:

| Sorun | Ölçülen durum |
|---|---|
| **Sürüm yok** | Bir stilin `sahne_sn`'i değişince dün üretilmiş iş yeniden üretilemez; hangi ayarla çıktığı kayıtlı değil |
| **Boyutlar karışık** | `sahne_sn` (tempo), `altyazi` (tipografi), `mag` (upscale), `gorsel_ek` (palet promptu) aynı düzlemde |
| **Türetilemez** | Melez istek için sözlüğe **elle** satır gerekiyor; çekirdek kod her yeni stilde büyüyor |
| **Kanıt/QA stilin parçası değil** | AI görsel yasağı tek bayrak (`gorsel_yasak`); lisans beyaz listesi, min bağımsız kaynak ve QA eşikleri stile bağlı değil |

### Yeni: `webapp/stil_profili.py` (841 satır)

**12 profil · 11 boyut · 44 alan · 15 konsept bağlantısı · 5 eski kimlik eşlemesi**
(`kapsam_ozeti()` ile ölçülebilir).

11 boyut: `anlatim · tempo · gecis · kamera · tipografi · palet · ses · medya ·
dagitim · kanit · qa`

Profiller: `belgesel-sinematik · belgesel-arastirmaci · seyahat-4k ·
ambient-sakin · explainer-hizli · bilim-anlatisi · hikaye-sinematik ·
korku-gerilim · cocuk-yumusak · urun-tanitim · yasam-dinamik · kultur-muzik`

### Sürümleme

- `SEMA_SURUM = "1.0.0"`; her profil kendi `surum`unu taşır.
- `arsivle(kimlik)` mevcut sürümü dondurur → `profil_al(kimlik, surum=...)`
  aynen geri getirir. Bir profili değiştirmeden **önce** çağrılmalı.
- Olmayan sürüm istenirse **sessizce başka sürüm dönmez** — `KeyError`.
- `profil_al()` her zaman **derin kopya** döner; kayıt kazara bozulamaz.

### Çekirdek kod değişmeden genişleme

- Yeni profil = `PROFIL`'e satır.
- Yeni boyut alanı = `BOYUT_KURALI`'ya satır.
- `_birlestir_alan()` **alan adı bilmez** — 7 kural: `ortalama ·
  agirlikli-secim · birlesim · kesisim · en-kati-dogru · en-kati-maks ·
  en-kati-min`.

### Melez türetme + gerekçe

`tureti()` 44 alanın her biri için hangi kuralın uygulandığını ve değerin
nereden geldiğini raporlar (kara kutu yok). Melez profil **kayda yazılmaz**.

**Katı olan kazanır:** belgesel + korku melezinde `ai_gorsel_yasak=True`,
`min_bagimsiz_kaynak=2.0`, lisans beyaz listesi katı tarafta kalıyor — testli.

### Kullanıcı seçimi Auto'yu yener

`coz()` sırası: **kullanıcı → auto (konsept) → türetilmiş melez → varsayılan**.
Kaynak her zaman raporlanır. Kullanıcı **bilinmeyen** bir stil verdiyse sessizce
yutulmaz: uyarı üretilip auto'ya düşülür.

### Geriye uyumluluk — BOZULMADI

| Kilit | Durum |
|---|---|
| `pipeline.py` | ✅ **dokunulmadı**; `stil_profili`'ni import etmiyor (testli) |
| `server.py` · modüler arayüz · `deploy.sh` | ✅ dokunulmadı |
| `eski_edit_stiline()` | eski `EDIT_STILLERI` alanlarının hepsini üretiyor (testli) |
| `ESKI_EDIT_ESLEME` | 5 eski kimliğin `pipeline.EDIT_STILLERI`'nde gerçekten var olduğu statik kontrolle doğrulanıyor |
| `KONSEPT_PROFIL` | anahtarların `taksonomi.AGAC`'ta gerçekten var olduğu testli; her aile bir profile bağlı |

### Ölçülen test sonucu

`python3 webapp/testler/test_faz_i.py` → **289 geçen / 0 başarısız / 0 bloke**
(234 → 289; I-2b'den **+55** kontrol).

⚠ **A–H regresyonları I-2b yazılırken KOŞULMAMIŞTI.** Push öncesi bağımsız
denetimde yapılan ölçüm: `test_faz_i.py` **289/0/0**, `kapsam_ozeti()` sayıları
commit iddiasıyla birebir uyuştu (12 profil · 11 boyut · 44 alan · 15 konsept
bağı · 5 eski eşleme) ve üretim kodunda `stil_profili` importu bulunmadığı
doğrulandı. **A–H regresyonları bu noktada değil, I-2c sonrasında koşuldu**
(§18 tablosu).

### BİLİNEN SINIRLAR (dürüstçe)

1. **Profil değerleri ölçülmedi.** 12 profildeki tempo/palet/ses sayıları
   mevcut `EDIT_STILLERI` ölçümlerinden ve tür konvansiyonundan türetilmiş
   **tasarım kararları** — gerçek videoyla A/B doğrulaması yok.
2. **Hiçbir yerden import edilmiyor.** Motor yazıldı ve testlendi; akışa
   bağlanması **I-2c**'ye ait.
3. **`eski_edit_stiline()` kayıpsız değil.** Eski biçimde palet/ses/kanıt/QA
   karşılığı yok; bunlar `_profil` altında birlikte taşınıyor. I-2c'de
   pipeline'ın bunu okuması gerekecek.
4. **Melez ağırlıkları sezgisel.** `coz()` konsept güvenini ağırlık olarak
   kullanıyor; bu seçim ölçülmedi.
5. **Boş lisans kesişiminde** en ağırlıklı ebeveynin listesi alınıyor (medya
   kilitlenmesin diye). Güvenlik açısından en katı davranış değil — uyarı
   olarak raporlanıyor.

### SONRAKİ ADIM (I-2c)

`girdi_analizi.analiz()` içine `konsept` + `stil_profili` alanlarını **ek**
olarak bağlamak (eski alanlar korunarak), `pipeline`'ın `_profil` bloğunu
okuması, ve GUI'da tespit edilen konsept + plan özetinin gösterilmesi.
→ İlk ikisi **§18'de yapıldı**; GUI bacağı **yapılmadı** (kapsam dışı).

---

## 18. FAZ I-2c — TAKSONOMİ + STİL PROFİLİ AKIŞA BAĞLANDI (12 Ağu, ölçüldü)

> **Durum: commit `0945a2f`, `origin/arastirma-motoru`'na PUSH EDİLDİ. Deploy YOK.**
> Dokunulan dosyalar: `webapp/girdi_analizi.py`, `webapp/pipeline.py`,
> `webapp/testler/test_faz_i.py` (+ bu handoff).
> **Dokunulmayan:** `server.py`, GUI (`static/**`), `deploy.sh`, `stil_profili.py`,
> `taksonomi.py`, `is_sozlesme.py`.

### Kapatılan açık

I-2a ve I-2b motorları yazılmıştı ama **hiçbir yerden import edilmiyordu**
(§16 limit 6, §17 limit 2). Yani 7 aile / 33 dal taksonomisi ve 12 sürümlü
bileşik profil, canlı akışta **hiç çalışmıyordu**.

### `girdi_analizi.py` — YALNIZCA EK ALAN

| Eski sözleşme | Durum |
|---|---|
| `TUR_SINYALI` (5 etiket) | ✅ dokunulmadı |
| `tur_tespit()` · `GORSEL_STRATEJISI` · `PIPELINE_TURU` | ✅ dokunulmadı |
| `analiz()` eski 10 anahtarı | ✅ hepsi aynen dönüyor (testli) |
| eski `gerekceler` 5 anahtarı | ✅ duruyor (2 yeni anahtar **eklendi**) |
| eski `otomatik_secimler` 4 anahtarı | ✅ duruyor, değerleri **değişmedi** (testli) |

Yeni: `analiz()` iki **ek** anahtar döndürüyor —
`konsept` (`taksonomi.siniflandir()` çıktısı) ve `stil_profili`
(`stil_profili.coz()` özeti + `eski_edit` köprüsü, `_profil` bloğu dahil).

- **Ağ/para yok.** `siniflandir()` `model_coz` **almadan** çağrılıyor; bu iddia
  dize taramasıyla değil, **çağrı casuslanarak** ölçülüyor (testli).
- **Çökertmez.** `server.py` bu modülü import anında yüklüyor; alt modüller
  `try/except` ile alınıyor. Modül yoksa ek alanlar `{}` olur ve eski sözleşme
  **eksiksiz** döner. Alt modül patlarsa `_hata` ile **görünür** olur, sessiz geçmez.
- **Deterministik.** Aynı girdi → bayt bayt aynı çıktı (testli).
- **Katı JSON.** Gövde `default=` kullanmadan serileşiyor (4.5 KB) — gevşek bir
  dönüştürücü, `/api/analiz`i çalışma anında 500 verecek tipi testte gizlerdi.

**Emin değilsen karışma:** stil önerisi yalnızca `kaynak ∈ {kullanici, auto,
turetilmis}` iken `otomatik_secimler["edit"]`e yazılır. Sinyal yoksa
(`kaynak == "varsayilan"`) **öneri üretilmez** — üretim hattının kendi
varsayılanı sessizce başka bir profille değiştirilmez (testli).

### `pipeline.py` — `_profil`i GÜVENLİ / OPSİYONEL tüketme

| Ekleme | Ne yapıyor |
|---|---|
| `profil_ek_oku(prof)` | `_profil` bloğunu okur. Yok/bozuk → `{}`. **Hiçbir girdide istisna fırlatmaz** (testli: `None`, `{}`, `"bozuk"`, `5`, dize) |
| `bilesik_stile_cevir(id)` | Yeni-nesil kimliği eski stil alanlarına çevirir. Bulunamazsa `None` → eski yol |
| `profil_coz(tur, edit_id, ek_profil=None)` | 3. parametre **opsiyonel**; verilirse TABAN sözlüğün üzerine yazılır |
| `sonuc["stil_profili"]` | Künye: kimlik + profil sürümü + şema sürümü. **Yalnızca `_profil` varsa** yazılır |

**Gerileme kanıtı (ölçüldü, testle kilitli):** `EDIT_STILLERI`'ndeki her eski
kimlik için `profil_coz()` **birebir aynı sözlük nesnesini** (`is`) döndürüyor.
Boş/`None` `edit_id`, `hikaye` ve `animasyon` yolları da aynı. Eski girdiler
yeni kodun tek satırından geçmiyor.

**Kapatılan sessiz hata:** `EDIT_STILLERI` dışındaki her kimlik bugüne kadar
**sessizce** `VARSAYILAN_EDIT`e düşüyordu — kullanıcı başka bir stil seçtiğini
sanıyordu. Artık kimlik `stil_profili` kaydında varsa gerçekten o profille
üretiliyor; kayıtta da yoksa eski sessiz-varsayılan davranış korunuyor.

`eski_edit_stiline()` kayıpsız olmadığı için (§17 limit 3) çevrim her zaman bir
**taban sözlük üzerine** yazılır: yeni biçimin taşıyamadığı `gorsel_ek`, `mag`,
`saha_etiketi`, `etiket_pct` tabandan gelir → `prof["gorsel_ek"]` gibi zorunlu
okumalarda **KeyError riski yok** (testli).

### ⚠ ÖLÇÜLEN BİLİNEN SINIR — görsel imza yeni kimlikle GELMİYOR

`EFEKT_TEMEL` ve `GECIS_IMZASI` tabloları **eski kimliklerle** anahtarlanmış.
Ölçüm:

```
sinematik-belgesel     efekt=3  gecis_imza=('karartma', 0.2)
korku-gerilim          efekt=0  gecis_imza=yok
belgesel-sinematik     efekt=0  gecis_imza=yok
```

Yani yeni-nesil bir kimlikle üretilirse tempo/footage/altyazı **profilden
gelir**, ama grain/vinyet/grade ve geçiş imzası **gelmez**. Profil geçiş
bilgisini `_profil.gecis` içinde (`{'tur': 'hard-cut', 'sure_sn': 0.0,
'oran_pct': 5.0}`) **taşıyor** ama bu tablolara henüz bağlanmadı.

**Sessiz bırakılmadı:** kod bu durumda stderr'e açık uyarı basıyor ve iki
tabloya erişim `.get()` ile (KeyError yok). Üçü de testle kilitli.

> ✅ **BU SINIR §21'DE (I-2d) KAPATILDI.** Görsel imza artık profilin
> `palet`/`gecis` beyanından türetiliyor; 12 profilin hepsi imza üretiyor,
> eski kimlikler bit-bit korunuyor.

### Ölçülen test sonucu (12 Ağu)

| Paket | Geçen | Başarısız |
|---|---|---|
| A | 125 | 0 |
| B | 200 | 0 |
| C | 148 | 0 |
| D | 95 | 0 |
| E | 127 | 0 |
| F | 242 | 0 |
| G | 217 | 0 |
| H | **257** | 0 (**1 BLOKE**) |
| I | **356** | 0 |
| **TOPLAM** | **1767** | **0** |

Faz I 289 → **356** (+67 kontrol). Faz H 203 → **257**: bu oturumda scratchpad'de
venv kurulduğu için **gerçek FastAPI uç testleri koştu** — `POST /api/analiz -> 200`
dahil. Kalan tek BLOKE `QA_TEST_VIDEO` (opsiyonel, ölçüm videosu yok).

`deploy.sh`'nin tanımsız-isim taraması ayrıca elle koşuldu → **temiz**.

### BİLİNEN SINIRLAR (dürüstçe)

1. **Görsel imza boşluğu** (yukarıda ölçüldü) — I-2d.
2. **GUI'da hiçbir şey değişmedi.** Wizard Adım 4 `otomatik_secimler`i zaten
   listeliyor, bu yüzden yeni `edit` satırı gerekçesiyle **kendiliğinden**
   görünür; ama `konsept` / `stil_profili` blokları arayüzde **gösterilmiyor**.
3. **`sonuc["stil_profili"]` künyesi iş sözleşmesine ULAŞMIYOR.** `server.py`
   `sonuc`tan alanları **tek tek** seçiyor; künyeyi işe taşımak `server.py` +
   `is_sozlesme` değişikliği ister — bu adımda kasıtlı olarak yapılmadı.
4. **Bileşik profil `/api/generate`e otomatik akmıyor.** Wizard önerilen `edit`i
   forma **yazmıyor** (yalnızca gösteriyor). Yeni-nesil kimlik ancak elle
   gönderilirse üretime girer.
5. **Profil değerleri hâlâ ölçülmedi** (§17 limit 1 aynen geçerli) — gerçek
   videoyla A/B doğrulaması yok.
6. **Gerçek kullanıcı girdisiyle isabet oranı ölçülmedi** (§16 limit 3 geçerli):
   konsept→profil eşlemesinin canlı dağılımdaki başarımı **bilinmiyor**.

### SONRAKİ ADIM (I-2d — bu adımda YAPILMADI)

`_profil.gecis` → `GECIS_IMZASI` ve profil → `EFEKT_TEMEL` bağı; künyenin
`server.py` + `is_sozlesme` üzerinden işe taşınması.
→ Konsept/stil özetinin arayüzde gösterilmesi **§19'da yapıldı**.

---

## 19. FAZ I-3 — BASİT "METİN + STİL + AUTO" ARAYÜZÜ (12 Ağu, ölçüldü)

> **Durum: commit `37b0b04`, `origin/arastirma-motoru`'na PUSH EDİLDİ. Deploy YOK.**
> Yeni: `webapp/static/js/basit.js`.
> Değişen: `webapp/static/js/wizard.js`, `js/durum.js`, `app.css`,
> `webapp/testler/test_faz_i.py` (+ bu handoff).
> **Dokunulmadı:** `server.py`, `pipeline.py`, `deploy.sh`, `api.js`,
> `secim-deneyimi.js`, `bilesenler.js`, `gorunumler.js`, `index.html`.

### Kapatılan açık

Bir video başlatmanın **tek yolu** 5 adımlı wizard'dı: tür kartı → konu →
görsel yön → özet → onay. Çoğu iş için gereken üç şey vardı: **metin, stil,
başlat.** Ayrıca I-2c'nin bağladığı konsept/stil motoru arayüzde **hiç
görünmüyordu** (§18 bilinen sınır 2 ve 4).

### Yeni varsayılan: tek ekran

`Yeni Proje` artık iki modlu. Varsayılan **Basit**:

```
[Basit] [Adım adım]          ← her iki ekranın başında, geri dönülebilir
Ne anlatalım?                ← metin (en az 20 karakter)
Görsel stil                  ← Otomatik + öneriler (mevcut bileşen)
Hedef süre                   ← KORUNDU
Sistemin okuduğu             ← Auto sonucu (aşağıda)
▸ Gelişmiş ayarlar           ← tek açılır alan
[Videoyu oluştur]            ← TEK ana üretim eylemi
```

**Adım adım wizard KALDIRILMADI** — 5 adım aynen duruyor (testli), `#/yeni/3`
gibi adım bağlantısı otomatik olarak o moda geçiriyor.

### Hiçbir backend alanı kaybolmadı

Gelişmiş açılır alan, adım 3'ün bileşenlerini **yeniden yazmıyor, yeniden
kullanıyor**: `sesBolumu()` (ses kütüphanesi: 6 sağlayıcı, arama, dinleme),
`markaBolumu()`, `hizliTercihler()`, `proPanel()` (4 profesyonel bölüm: renk,
hareket, altyazı, üretim). Bağlama tek yerden — `adim3Kur()` — yapılıyor,
çift bağlama yok (testli).

`unlu` (22. alan), Grok/görsel model seçimi, süre seçici, altyazı şablonu,
palet/hex, ışık, arkaplan, açılış, Sora, karakter/stil görseli ve referans
kareler: hepsi erişilebilir durumda.

### Auto → generate: YENİ ALAN EKLENMEDİ

22 alanlık sözleşme **büyümedi** (testli). Auto'nun çözdüğü bileşik profil
kimliği **mevcut `edit` alanıyla** taşınıyor — I-2c'nin pipeline köprüsü bu
kimlikleri zaten çözebiliyor.

**Tarayıcıda ölçülen kanıt** (fetch kesildi, gerçek üretim başlatılmadı):

```
POST /api/analiz -> 200
gönderilen: {session, story, tur: "documentary",
             edit: "belgesel-sinematik", sure_dk, gecis, zoom, altyazi}
```

**Taşınmayan durumlar sessiz değil** — `autoStilKimligi()` yalnızca üretim
hattının **gerçekten çözebileceği** kimlikleri geçirir:

| Durum | Davranış | Sebep |
|---|---|---|
| `kaynak=auto`, gerçek kimlik | **taşınır** | hat çözebiliyor |
| `kaynak=turetilmis` (`melez:a+b`) | taşınmaz, ekranda **"(uygulanmadı)"** | kayıtta böyle satır yok; gönderilse sessizce varsayılana düşerdi |
| `kaynak=varsayilan` | taşınmaz | gerçek sinyal yok; hattın kendi varsayılanı korunur |
| `hikaye` / `animasyon` hattı | taşınmaz | o hatların kendi stil sözlükleri var |

### Auto sonucu görünür ve ANLAŞILIR

Ekranda: **Konu türü** (+ sinyal gücü) · **Üretim hattı** · **Seçilen stil** ·
**Stil sürümü** · ölçülen kanıt cümlesi.

⚠ Backend'in `gerekce` alanı geliştirici metnidir
(`belgesel.tarih: puan 8.0 (2. belgesel.biyografi 4.5), kanit 4 = 2 anahtar
+ 2 yapisal sinyal`) — ham gösterilmesi "görünür" yapardı ama **anlaşılır**
yapmazdı. Aynı ölçüm yapısal alanlardan yeniden kuruluyor:
*"Metinde 3 bağımsız işaret ölçüldü; kararın güveni yüzde 72."* Uydurma yok.

### Tarayıcıda bulunan ve düzeltilen GERÇEK hata

Basit mod türü sabit `documentary` bırakıyordu. Ölçüm:

```
metin : "kabus gibi bir gece: kapının ardındaki gölge…"
eski `otomatik_secimler.tur` : documentary   ← BES-ETIKETLI dedektör, 'belirsiz'
yeni `konsept`               : hikaye.korku  ← DOĞRU
```

Yani açık bir korku hikâyesi **belgesel hattında** üretilecekti. Bu, §16'nın
zaten belgelediği eski dedektör zaafının canlı sonucu. Düzeltme: `autoTuru()`
birincil kaynak olarak `konsept.eski_etiket` okuyor, eski alan yalnızca
yedek. Eşleme sunucunun `PIPELINE_TURU` tablosuyla aynı.

**Kullanıcının açık tür seçimi Auto'yu yener:** adım 1'de tür seçilince
`turKaynak: 'kullanici'` işaretleniyor ve Auto bir daha türe dokunmuyor.
`animasyon` Auto tarafından **asla** seçilmez (referans kare zorunlu).

### Ölçülen test sonucu (12 Ağu) — İKİ ORTAM AYRI

| Paket | A | B | C | D | E | F | G | H | I | Toplam |
|---|---|---|---|---|---|---|---|---|---|---|
| **Zengin venv** | 125 | 200 | 148 | 95 | 127 | 244 | 218 | **257** | **409** | **1823** |
| **Sistem Python** | 125 | 200 | 148 | 95 | 127 | 244 | 218 | **203** | **409** | **1769** |

0 hata. Zengin venv'de 1 BLOKE (`QA_TEST_VIDEO`, opsiyonel); sistem
Python'da 2 çevresel BLOKE (`fastapi` kurulu değil + `QA_TEST_VIDEO`).
**BLOKE'ler PASS sayılmadı.** Faz I 356 → **409** (+53), F 242 → 244,
G 217 → 218 (yeni dosya dosya-başına döngülere girdiği için).

I-3 testleri **string eşleştirmeyle yetinmiyor**: `autoStilKimligi` ve
`autoTuru` doğruluk tabloları `node` ile **gerçekten çalıştırılıyor**
(20 davranış kontrolü). node yoksa dürüstçe BLOKE yazılır.

`deploy.sh` tanımsız-isim taraması elle koşuldu → temiz.

### Tarayıcı doğrulaması (yerel, ücretsiz)

Uygulama yerelde `VIDRUSH_KOK` ile ayağa kaldırıldı (`127.0.0.1:8799`),
`/ui/js/basit.js` 200, konsolda **hata yok**, `POST /api/analiz` 200.
Üretim eylemi `fetch` kesilerek sınandı — **gerçek üretim başlatılmadı,
ücretli çağrı yapılmadı.**

⚠ `preview_start` `.claude/launch.json` ister; Faz F testi o dosyanın diskte
**bulunmamasını** şart koşuyor. Bu yüzden sunucu doğrudan başlatıldı ve
tarayıcı URL'ye açıldı — `.claude/` oluşturulmadı.

### BİLİNEN SINIRLAR (dürüstçe)

1. **Adım adım modda Auto paneli yok.** Konsept/stil özeti yalnızca basit
   modda gösteriliyor; wizard Adım 4 eski özet kartlarını kullanıyor.
2. **Melez stiller hâlâ üretime taşınamıyor** (§18 ile aynı kök): pipeline
   `melez:a+b` kimliğini çözemiyor. Arayüz bunu açıkça söylüyor.
3. **Hikâye hattında bileşik profil uygulanmıyor** — `HIKAYE_STILLERI` ayrı
   bir sözlük. Auto o hatta stil taşımıyor (sessiz düşüş yerine dürüst not).
4. ~~**Görsel imza boşluğu** (§18 sınır 1): yeni-nesil kimlikle
   `EFEKT_TEMEL`/`GECIS_IMZASI` gelmiyor.~~ → ✅ **§21'de (I-2d) kapatıldı.**
5. **Gerçek kullanıcıyla kullanılabilirlik ölçülmedi.** İddia "akış kısaldı
   ve alan kaybı yok" — bu testlerle kanıtlı; "kullanıcılar daha hızlı
   üretiyor" iddiası **ölçülmedi**.
6. **Ücretli uçtan uca üretim denenmedi.** `edit` alanının doğru gittiği
   ölçüldü; o kimlikle çıkan videonun kalitesi bu adımın iddiası değil.

---

## 20. FAZ I-4 — REFERANS VİDEO PARMAK İZİ SÖZLEŞMESİ (12 Ağu, ölçüldü)

> **Durum: commit `0d45fc8`, `origin/arastirma-motoru`'na PUSH EDİLDİ. Deploy YOK.**
> Yeni: `webapp/referans_parmak.py`.
> Değişen: `webapp/testler/test_faz_i.py` (+ bu handoff).
> **Dokunulmadı:** `server.py`, `pipeline.py`, `deploy.sh`, tüm arayüz.

### Bu adımda NE YAPILMADI (kasıtlı)

**Tam vision modeli yok. Ücretli analiz yok. Kare okuma yok.** Bu adım
yalnızca **sözleşme + güvenli kapı**. Gerçek ölçüm `parmak_kur(..., olcumler)`
ile **dışarıdan enjekte** edilir; verilmezse modül uydurma üretmez.

Ölçülen kilit: modülde model kimliği / sohbet ucu izi **yok**, tek dış komut
`ffprobe` (ücretsiz, yerel), modül **alt süreç bile başlatmıyor** — komutu
yalnızca üretiyor. Varsayılan bütçede `maks_usd = 0.0`, yani ücretli çağrıya
**yer ayrılmıyor**; açmak açık bir karar.

### Sözleşme kapsamı (ölçülebilir)

`kapsam_ozeti()` → **7 boyut · 30 alan · 8 yasak alan · 12 durdurma nedeni ·
6 lisans · 3 kaynak türü**, şema sürümü `1.0.0`.

| Boyut | Örnek alanlar |
|---|---|
| `ritim` | kesme/dk, tempo sınıfı, ritim düzenliliği |
| `cekim` | medyan/ortalama/p90 sn, kısa-uzun pay %, dağılım sınıfı |
| `gecis` | geçişli pay %, baskın tür, ortalama süre |
| `tipografi` | yazı kapsama %, konum eğilimi, kalış süresi, hareket sınıfı |
| `renk` | parlaklık, kontrast/doygunluk sınıfı, sıcaklık, koyu kare payı |
| `kamera` | hareket yoğunluğu, baskın hareket, sabit kare payı |
| `ses` | konuşma yoğunluğu, sessizlik payı, müzik yatağı, ducking dB, ritim hizalanması |

Hepsi **soyut istatistik**. Yeni alan eklemek = `OZELLIK_SEMASI`ya bir satır;
`parmak_kur()` alan adı bilmez (testle kanıtlı: şemaya geçici alan eklendi,
çekirdek kod değişmeden üretildi ve doğrulamadan geçti).

### YASAK ALANLAR — sözleşmenin kalbi

Bunlar "yapmamaya çalışırız" değil, **sözleşme ihlali**. `dogrula()` bu izleri
taşıyan parmak izini **reddeder**:

`kisi_kimligi` · `yuz_bicimi` · `marka_logo` · `ozgun_metin` ·
`sahne_kopyasi` · `kare_verisi` · `ses_kopyasi` · `seslendirme_klonu`

`yasak_denetle()` yalnızca anahtar adına bakmaz: iç içe sözlüklerde arar,
`data:`/`base64,` gömülü veriyi, ham `bytes`'ı ve **400 karakteri aşan metni**
(özgün içerik kopyası olabilir) de reddeder. Kısa sınıf adları
(`"hard-cut"`, `"orta"`) yanlış pozitif üretmiyor — testli.

Şemanın kendisi de denetleniyor: **sözleşme kendi yasağını ihlal etmiyor.**

### Kaynak kimliği / provenance

Kapı açılmadan önce: yol güvenliği (traversal + symlink çözümü) → düz dosya mı
→ boyut tavanı → **provenance beyanı** → bütçe → `ffprobe` ile
codec/çözünürlük/fps/süre → süre tavanı/asgarisi → sha256 + bayt.

⚠ Hash **kimlik** içindir, içerik saklamak için değil: kayıtta yalnızca özet
durur, videonun kendisi değil. Bütçe sınırı üstündeki dosyanın hash'i
**alınmaz** (büyük dosya okunmaz).

**Provenance zorunlu, "bilinmiyor" kabul edilmez:** `kaynak_turu` ∈
{yukleme, kendi-arsivim, lisansli-arsiv}, `lisans` ∈ {sahibiyim, izinli, cc0,
cc-by, cc-by-sa, public-domain} ve `stil_izni: True`. Üçü de olmadan analiz
**başlamaz** — sessiz varsayım yok.

### Örnekleme planı — deterministik

`ornekleme_plani(sure, butce)`: kenarlardan %2 kırpar (açılış logosu ve
kapanış jeneriği stilin kendisi değildir, istatistiği bozar), kalan aralığı
bütçe kadar eşit böler. **Rastgelelik yok** — aksi halde aynı video iki farklı
parmak izi üretir ve "tekrar üretilebilir" iddiası karşılıksız kalırdı.

### Kontrollü durma — 12 neden, uydurma yok

`VIDEO-YOK · DOSYA-YOK · DOSYA-TURU · YOL-GUVENSIZ · BOYUT-ASIMI ·
BOZUK-MEDYA · SURE-ASIMI · SURE-YETERSIZ · PROVENANCE-EKSIK · LISANS-EKSIK ·
BUTCE · ARAC-YOK`

Her biri için test var. Kapı kapalıysa `bos_parmak()` döner:
`durum="OLCULMEDI"`, **hiçbir alan `olculdu` değil**, genel güven `0.0`,
sebep görünür. Probe patlarsa kapı **çökmez**, kontrollü durur.

### Fallback görünür, uydurma yasak

Her alan `kaynak` taşır: `olculdu | varsayilan | olculemedi` + `guven` + `kanit`.

- Ölçülmeyen alan: `varsayilan`, güven **0.0** — gizlenmiyor.
- `olculen_alan / toplam_alan` sayılabilir (ör. `3/30`).
- **Yanlış tipte ölçüm sessizce kabul edilmiyor** → fallback'e düşer.
- Güven 0–1 aralığına kırpılır.
- `dogrula()`: *ölçülmediği halde güven > 0* olan alan **geçmez**.

### Bütçe

`ParmakButce(maks_kare, maks_sn, maks_usd, maks_bayt, maks_sure_sn)` —
**beşi de zorunlu**, `None` geçmek `ValueError`, negatif tavan `ValueError`.
Thread güvenli: 8 thread × 20 deneme ile tavan 10 → **tam 10** verildi
(kilitsiz sayaç tavanı aşardı). Engeller sessiz değil, `ozet()["engel"]`e yazılır.

### Ölçülen test sonucu (12 Ağu) — İKİ ORTAM AYRI

| Paket | A | B | C | D | E | F | G | H | I | Toplam |
|---|---|---|---|---|---|---|---|---|---|---|
| **Zengin venv** | 125 | 200 | 148 | 95 | 127 | 244 | 218 | **257** | **515** | **1929** |
| **Sistem Python** | 125 | 200 | 148 | 95 | 127 | 244 | 218 | **203** | **515** | **1875** |

0 hata. Faz I 409 → **515** (+106 yeni kontrol). Zengin venv'de 1 BLOKE
(`QA_TEST_VIDEO`), sistem Python'da 2 çevresel BLOKE. **BLOKE'ler PASS
sayılmadı.** `deploy.sh` pyflakes taraması → temiz.

**Mevcut konsept testleri korundu:** §11'de 19 konsept · 97 kontrol aynen
duruyor (≥12 şartı sağlanıyor).

### BİLİNEN SINIRLAR (dürüstçe)

1. **Ölçüm motoru YAZILMADI.** Bu adım sözleşme + kapı. `parmak_kur()` şu an
   yalnızca enjekte edilen değerleri kabul ediyor; gerçek kesme/renk/ses
   ölçümü sonraki adımın işi.
2. **Hiçbir yerden import edilmiyor.** `server.py`/`pipeline.py` bağlanmadı
   (testli). Arayüzde referans video yükleme akışı **yok**.
3. **Şema değerleri ölçülmedi.** 30 alanın fallback değerleri tür
   konvansiyonundan türetilmiş tasarım kararları; gerçek videoyla kalibrasyon
   yapılmadı.
4. **Gerçek videoyla uçtan uca koşulmadı.** ffprobe çıktısı testlerde sahte
   veriyle sağlandı; komut planı doğru ama gerçek dosyada ölçüm alınmadı.
5. **Yasak denetimi sezgisel eşiklere dayanıyor** (400 karakter metin sınırı).
   Kötü niyetli bir çağıran, yasağı 399 karakterlik parçalara bölerek
   aşabilir — bu kapı dürüstlük içindir, düşman modeli değildir.
6. **Ses/tipografi boyutları en zayıf halka.** ffprobe bunları vermiyor;
   ölçmek için ek araç (ffmpeg filtreleri, OCR) gerekecek ve OCR'ın
   `ozgun_metin` yasağını ihlal etmemesi ayrıca tasarlanmalı.

### SONRAKİ ADIM (I-5 — bu adımda YAPILMADI)

Ölçüm motoru (ffmpeg `select/scene` + `blackdetect` + `silencedetect` ile
ritim/çekim/ses; renk için kare histogramı), `/api/generate` veya ayrı bir uçla
bağlama, ve arayüzde referans video yükleme + parmak izi özeti.

---

## 21. FAZ I-2d — GÖRSEL İMZA BOŞLUĞU KAPATILDI (12 Ağu, ölçüldü)

> **Durum: commit `243bad5`, `origin/arastirma-motoru`'na PUSH EDİLDİ. Deploy YOK.**
> Değişen: `webapp/pipeline.py`, `webapp/testler/test_faz_i.py` (+ bu handoff).
> **Dokunulmadı:** `server.py`, `stil_profili.py`, `referans_parmak.py`,
> `deploy.sh`, tüm arayüz, 22 alanlık generate sözleşmesi.

### Kapatılan açık

§18 ve §19'un bilinen sınırı ölçülmüştü:

```
sinematik-belgesel  efekt=3  gecis=('karartma', 0.2)
korku-gerilim       efekt=0  gecis=yok
belgesel-sinematik  efekt=0  gecis=yok
```

`EFEKT_TEMEL` ve `GECIS_IMZASI` **eski kimliklerle** anahtarlıydı. Yeni-nesil
bir kimlikle üretilirse tempo/footage/altyazı profilden geliyor ama
grain/vinyet/grade ve geçiş imzası **gelmiyordu** — kullanıcının sebebini
bilmediği sessiz bir kalite kaybı.

### Çözüm: profilin kendi beyanından türetme

`bilesik_gorsel_imza(_profil)` → `{efektler, gecis_imza, gecis_oran, gerekce,
uygulandi}`. Kaynak: profilin `palet` (grade/kontrast/doygunluk) ve `gecis`
(tür/oran) blokları.

**Üretilen adlar yalnızca render tarafının BİLDİĞİ adlar:**
efekt ∈ `grain · vinyet · siyah-beyaz · kontrast-grade · sicak-grade ·
soguk-grade`, geçiş ∈ `karartma · flash · whip`. Bilinmeyen ad sessizce yok
sayılırdı; testler bunu kilitliyor.

Geçiş eşlemesi (4 türün **hepsi** eşlenmiş, uydurma yok):
`hard-cut → karartma` (seyrek aksan, eski modelin aynısı) · `crossfade →
karartma` (render tarafında karartma = crossfade + parlaklık dibi) ·
`whip → whip` · `karisik → flash`. Oran = profilin `oran_pct`'si.

### Eski tabloya karşı kalibrasyon (testle kilitli)

⚠ Bu kurallar **ölçüm değil, türetme kararıdır.** Doğrulama yöntemi: eşdeğer
profilin eski tablonun ruhunu üretmesi.

| Yeni profil | Türetilen | Eski karşılığı |
|---|---|---|
| `belgesel-sinematik` | grain 0.9 · vinyet 0.9 · sicak-grade 0.8 · kontrast-grade 1.1 | `sinematik-belgesel`: grain 0.9 · vinyet 1.0 · kontrast-grade 1.1 |
| `bilim-anlatisi` | grain 0.5 | `veri-anlatisi`: grain 0.5 — **birebir** |
| `explainer-hizli` | efekt yok | `hizli-explainer`: `[]` — **birebir** |
| `korku-gerilim` | grain 0.9 · vinyet 1.0 · soguk-grade 0.9 · kontrast-grade 1.1 | (eski karşılığı yoktu) |

**12 profilin hepsi** görsel imza üretiyor — sessiz kayıp kalmadı.

### Eski kimliklerde BİT-BİT gerileme yok

`efekt_ata(edit_id, islev, indeks, ek_profil=None)` ve
`gecis_imza_sec(edit_id, indeks, ek_profil=None)` — 3./4. parametre
**opsiyonel**. Eski kimliklerde `_profil` bloğu yoktur → `None` → eski kod
yolu aynen işler.

**Kanıt:** test, dokunulmamış tablolardan **bağımsız bir referans uygulama**
kuruyor ve 5 eski stil × 120 sahne × 6 işlev için çıktıyı karşılaştırıyor →
**fark yok**. Yani "kod kendini doğruluyor" değil, davranış eski algoritmayla
karşılaştırılıyor.

### Her karar görünür ve izlenebilir

- `gerekce` listesi hangi alanın hangi efekti doğurduğunu tek tek yazar
  (`palet.grade 'dogal-sicak' -> 'sicak' kurali: sicak-grade 0.8`).
- İş kaydına `sonuc["stil_profili"]["gorsel_imza"]` yazılıyor
  (uygulandı/efektler/geçiş/gerekçe).
- Üretim logunda `GORSEL IMZA (bilesik): efekt=[...] gecis=karartma %10` +
  gerekçe satırları.
- Türetme **başarısız olursa sessizce eski tabloya geçilmez**; log açıkça
  `TURETILEMEDI ... eski tabloya dusuluyor` der.

### Bozuk profil → kontrollü fallback

`bilesik_gorsel_imza()` **istisna fırlatmaz**. `None`, boş sözlük, dize,
liste, `palet: "x"`, eksik alanlar, `oran_pct: "cok"` — hepsi testli; her
durumda eski tabloya düşülür ve gerekçe yazılır. Bilinmeyen geçiş türünde
(`uzay-gecisi`) imza **üretilmez** — uydurma yok.

### Ölçülen test sonucu (12 Ağu) — İKİ ORTAM AYRI

| Paket | A | B | C | D | E | F | G | H | I | Toplam |
|---|---|---|---|---|---|---|---|---|---|---|
| **Zengin venv** | 125 | 200 | 148 | 95 | 127 | 244 | 218 | **257** | **562** | **1976** |
| **Sistem Python** | 125 | 200 | 148 | 95 | 127 | 244 | 218 | **203** | **562** | **1922** |

0 hata. Faz I 515 → **562** (+47). Zengin venv'de 1 BLOKE (`QA_TEST_VIDEO`),
sistem Python'da 2 çevresel BLOKE. pyflakes taraması temiz.

⚠ §16'daki iki kontrol **güncellendi, silinmedi**: I-3 döneminde oradaki
"yeni kimlikte görsel imza YOK" satırı bir *bilinen sınırı* kilitliyordu;
I-2d o sınırı kapattığı için kontrol artık türetmenin varlığını kilitliyor.

### BİLİNEN SINIRLAR (dürüstçe)

1. **Türetme kuralları ölçülmedi.** Eski tablo 786 kesme ölçümünden geliyordu;
   bu kurallar profilin **beyanından** türetiliyor ve gerçek videoyla A/B
   doğrulaması yok. Kalibrasyon iddiası yalnızca "eski tablonun ruhunu
   üretiyor" düzeyinde.
2. **`oran_pct` değerleri profilin kendi beyanı.** `ambient-sakin` %90,
   `explainer-hizli` %45 — bunlar 786 kesme ölçümündeki "sert kesme %79.9"
   gerçeğiyle karşılaştırılmadı. Yüksek oranlar ekranda beklenenden yoğun
   görünebilir.
3. **Gerçek videoyla uçtan uca koşulmadı.** Efekt/geçiş adlarının render
   tarafında tanındığı statik olarak doğrulandı; çıktı videosu izlenmedi.
4. **`kamera.hareket` bu adımda bağlanmadı** — `motion` alanı zaten
   `eski_edit_stiline()` üzerinden akıyordu, ayrıca bir şey yapılmadı.
5. **Hikâye/animasyon hatlarına taşma yok** (kasıtlı): o hatların kendi stil
   sözlükleri var; bileşik profil oralarda hâlâ uygulanmıyor (§19 sınır 3).

### SONRAKİ ADIM

§19 sınır 1–3 ve §20 sınır 1–2 hâlâ açık: adım adım modda Auto paneli,
melez stillerin üretime taşınması, referans ölçüm motoru.

---

## 22. FAZ I-5 — KONSEPT FARKINDALIKLI MEDYA SEÇİMİ (12 Ağu, ölçüldü)

> **Durum: commit `e3559b2`, `origin/arastirma-motoru`'na PUSH EDİLDİ. Deploy YOK.**
> Değişen: `webapp/medya/sorgu_planlayici.py`, `webapp/medya/siralama.py`,
> `webapp/medya/avci.py`, `webapp/testler/test_faz_i.py` (+ bu handoff).
> **Dokunulmadı:** `medya/lisans.py`, `medya/guvenlik.py` (SSRF),
> `medya/kare_kapisi.py`, `medya/indirme.py`, `pipeline.py`, `server.py`,
> tüm arayüz, 22 alanlık generate sözleşmesi, `deploy.sh`.

### Kapatılan açık — ÖLÇÜLDÜ

`sorgu_planlayici.KALIP` ve `AMAC_DAGILIMI` **tamamen belgesel biçimliydi**.
Bir seyahat videosu da, bir ürün tanıtımı da, bir ders anlatımı da aynı
`{yer} city aerial view / close up {konu} / {kurum} document scan`
kalıplarına giriyordu.

**Çekim-niyeti çakışması** (6 farklı konsept, 8 sahne, çift çift Jaccard):

```
KONSEPTSIZ (eski)  = %100.0     ← her konsept AYNI çekimi istiyor
KONSEPTLI  (yeni)  = %43.2
```

Test bunu kilitliyor: eski hâlin >%95, yeninin en az 25 puan altında olması.

### `sorgu_planlayici.py` — ek bilgi, geriye uyumlu

- `KONSEPT_KALIP`: 6 aile (seyahat · urun · egitim · hikaye · kultur · yasam)
  için sahne amacına **eklenen** sorgu kalıpları. Aile kalıpları **önce**
  denenir, genel `KALIP` yedek kalır — hiçbir kalıp silinmedi.
  ⚠ `belgesel` kasıtlı olarak yok: mevcut `KALIP` zaten belgesel için yazıldı.
- `KONSEPT_AMAC_DAGILIMI`: ailenin kendi sahne amacı dağılımı. Seyahatte
  `belge` yok, üründe `arsiv`/`harita` yok, hikâyede `belge`/`harita` yok,
  eğitimde `harita`/`belge` ağırlıklı. Hepsi 1.0'a topluyor (testli).
- `sorgu_plani(..., konsept=None)` ve `amac_ata(indeks, kategori, konsept=None)`.
- Çıktıya `konsept_ailesi` alanı **eklendi**; gerekçe hangi ailenin
  kullanıldığını yazıyor.

**Somut sonuç (testli):** üründe 10 sahnenin ≥4'ü `detay`; üründe hiç `arsiv`
istenmiyor; hikâyede hiç `belge`/`harita` istenmiyor; eğitimde `harita`+`belge`
gerçekten isteniyor; seyahat sorguları `drone`/`scenic`/`coastline` taşıyor;
ürün sorguları `product`/`studio`/`macro` taşıyor.

### `siralama.py` — sınırlı kayma, kapıya dokunmadan

- `KONSEPT_TERIM`: 7 aile için (tercih edilen, cezalandırılan) çekim kelimeleri.
- `konsept_kaymasi(aday, konsept)` → **en fazla ±12 puan**, yalnızca `amac`
  bileşenine uygulanır.
- ⚠ **`AGIRLIK` vektörü DEĞİŞMEDİ** (`0.34/0.18/0.22/0.26`). Yeni bir ağırlık
  eklemek tüm eski skorları değiştirirdi.
- ⚠ **`alaka_kapisi` ve lisans duvarı bu adımda DEĞİŞMEDİ.** Konsept puanı bir
  adayı kapıdan **geçiremez**; yalnızca geçenler arasında sıralamayı değiştirir.
  Test bunu doğrudan ölçüyor: alakasız bir aday konseptli ve konseptsiz
  puanlamada **aynı** `render_kullanilabilir` kararını alıyor.
- Kayma sessiz değil: `skor_detay["konsept"]` gerekçeyi yazıyor.

### `avci.py` — opsiyonel taşıma

`sahne_ara(..., konsept=None)` ve `avla(..., konsept=None)`; konsept sorgu
planına ve puanlamaya geçiriliyor. Diff **tamamen ek**: 6 satır yerinde
genişletildi, silme yok.

### Geriye uyumluluk — BİT-BİT

| Kilit | Kanıt |
|---|---|
| `sorgu_plani(konsept=None)` | 5 metin × 7 amaç → eskiyle aynı |
| `amac_ata(konsept=None)` | **300 sahne × 6 kategori**, dokunulmamış tablodan kurulan bağımsız referans uygulamayla karşılaştırıldı → fark yok |
| `puanla(konsept=None)` | skor ve `amac` bileşeni aynı; `skor_detay`'a `konsept` **eklenmiyor** |
| Sağlayıcı tavanı %40 | değişmedi |
| Faz B paketi | **200/0** — gerileme yok |

### Bilinmeyende güvenli davranış

`None` · boş sözlük · sözlük değil · `belirsiz` konsept · bilinmeyen aile ·
boş aile → hepsinde `konsept_ailesi` `""` döndürüyor, `amac_ata` eski
dağılıma düşüyor, kayma `0.0`. **Rastgele stok yok:** bilinmeyen ailede
sorgular eskiyle **birebir aynı**. `konsept_ailesi` hiçbir girdide istisna
fırlatmıyor (`None`, `5`, `[]`, `"x"`, `{"yol": 1}` testli).

### Kullanıcının açık seçimi her zaman kazanır

- `avla()` içinde açık `sahne_amaci` verilmişse `amac_ata` **çağrılmıyor**.
- İddia kategorisi (`alinti`/`cografya`/`isim`/`tarih`) tür konvansiyonunu
  **yeniyor**: seyahat konseptinde bile `alinti` → `belge`, ürün konseptinde
  `cografya` → `harita` (testli).

### Ölçülen test sonucu (12 Ağu) — İKİ ORTAM AYRI

| Paket | A | B | C | D | E | F | G | H | I | Toplam |
|---|---|---|---|---|---|---|---|---|---|---|
| **Zengin venv** | 125 | 200 | 148 | 95 | 127 | 244 | 218 | **257** | **614** | **2028** |
| **Sistem Python** | 125 | 200 | 148 | 95 | 127 | 244 | 218 | **203** | **614** | **1974** |

0 hata. Faz I 562 → **614** (+52). Konsept matrisi §11'in **19 metninin
tamamı** kullanıldı (≥12 şartı fazlasıyla sağlanıyor). Test **ağ kullanmıyor**:
gerçek indirme yok, sağlayıcıya istek yok — çağrı izi taramasıyla kilitli.
pyflakes temiz.

### BİLİNEN SINIRLAR (dürüstçe)

1. ~~**`medya/avci` hâlâ canlı `/api/generate` hattına bağlı değil**~~ →
   ✅ **§23'te (I-6) OPT-IN olarak bağlandı.** Varsayılan hâlâ kapalı;
   açılmadıkça canlı hat `kaynak.py` üzerinden çalışmaya devam eder.
2. **Aile dağılımları ölçüm değil**, tür konvansiyonundan türetilmiş tasarım
   kararları; gerçek kanal ölçümüyle doğrulanmadı.
3. **%43.2 kalan çakışma** giderilmedi: aileler `establishing`/`ortam`/`detay`
   gibi ortak amaçları paylaşıyor. Sıfıra indirmek tür konvansiyonunu zorlamak
   olurdu.
4. **Kelime tabanlı eşleşme.** `KONSEPT_TERIM` İngilizce stok başlıklarına göre
   yazıldı; sağlayıcı başlığı Türkçe/boş gelirse kayma `0.0` (nötr) kalır.
5. **Gerçek stok sonucuyla A/B yapılmadı.** İddia "istenen çekim niyeti
   ayrışıyor"; "seçilen klipler gerçekten daha iyi" **ölçülmedi**.
6. **`belgesel` ailesi sorgu tarafında ayrışmıyor** (kasıtlı) ama sıralama
   tarafında `KONSEPT_TERIM["belgesel"]` var — iki modüldeki `konsept_ailesi`
   fonksiyonları bu yüzden farklı üyelik tablosuna bakıyor.

---

## 23. FAZ I-6 — MEDYA AVCISI CANLI HATTA (GÜVENLİ OPT-IN) (12 Ağu, ölçüldü)

> **Durum: commit `1e9c288`, `origin/arastirma-motoru`'na PUSH EDİLDİ. Deploy YOK.**
> Yeni: `webapp/medya_kopru.py`.
> Değişen: `webapp/pipeline.py`, `webapp/kaynak.py`,
> `webapp/testler/test_faz_i.py` (+ bu handoff).
> **Dokunulmadı:** `server.py`, tüm arayüz, 22 alanlık generate sözleşmesi,
> `medya/lisans.py`, `medya/guvenlik.py`, `medya/indirme.py`,
> `medya/kare_kapisi.py`, `deploy.sh`.

### Kapatılan açık — handoff'un EN ESKİ bulgusu

§1 (12 Ağu, ilk envanter): *"`pipeline.py` bu üç paketin HİÇBİRİNİ import
etmiyor."* §10 madde 1 bunu en yüksek öncelikli iş olarak bırakmıştı.
Araştırma (H2), kare kapısı (I-1) ve QA (H6) bağlanmıştı; **medya avcısı
bağlanmamıştı.** Bu adım onu bağlıyor — ama **varsayılan olarak kapalı**.

### Opt-in — iki yol, ikisi de açık karar

| Yol | Nasıl |
|---|---|
| Ortam değişkeni | `MEDYA_AVCISI=1` |
| Dahili iş ayarı | kanal profilinde `{"medya_avcisi": True}` |

⚠ `is_ayar` **dahili** bir sözlüktür (kanal profili). `/api/generate`in 22
alanı buraya **ulaşmaz**; `server.py` bu alanı okumuyor, arayüz göndermiyor —
üçü de testli. Yalnızca gerçek `True` açar: `"evet"`, `1`, `"true"` **açmaz**.

Kapalıyken köprünün hiçbir satırı üretim kararına karışmaz ve `sonuc`
sözlüğüne `medya_avcisi` anahtarı **hiç eklenmez** → eski işlerde çıktı
bit-bit aynı.

### Üç kapı da zorunlu — BYPASS EDİLEMEZ (testli)

1. **Lisans + provenance.** Aday listesi değil, avcının **seçtikleri**
   kullanılır; üstüne `render_kullanilabilir` bir kez daha doğrulanır.
   Test: `render_kullanilabilir=False` bir aday **indirilmiyor bile**.
2. **SSRF / indirme.** İndirme yalnızca `medya.indirme.guvenli_indir`
   üzerinden. Köprü `requests`/`urllib`/`socket` **import etmiyor** ve
   doğrudan ağ çağrısı yapmıyor — import ve çağrı izi taramasıyla kilitli.
3. **Kare kapısı.** İndirilen her klip `kare_dogrula` ile sınanır.
   **Fail-closed:** doğrulayıcı verilmezse hiçbir aday kabul edilmez;
   doğrulayıcı **patlarsa** da aday reddedilir. Reddedilen klip **diskten
   silinir**.

### Uydurma/rastgele stok yok

Uygun aday çıkmazsa `ok=False` döner ve çağıran taraf **mevcut güvenli
yolunu** (`kaynak.footage_getir` → genel yedek → tekrar) aynen sürdürür.
Sessiz geçiş yok: her red `dususler`e gerekçesiyle yazılır ve iş kaydına
taşınır. Köprü **hiçbir durumda istisna fırlatmaz** — avcı patlarsa `HATA`,
modül yüklenemezse `MODUL-YOK`, süre dolarsa `SURE-ASIMI`.

9 durdurma nedeninin hepsi açıklamalı: `KAPALI · MODUL-YOK ·
DOGRULAYICI-YOK · ISTEK-YOK · SURE-ASIMI · ADAY-YOK · INDIRME-BASARISIZ ·
KARE-KAPISI · HATA`.

### Aktarılan sinyaller

Konsept (`taksonomi.siniflandir`), sahne amacı, iddia metni, `fact_id`,
`scene_id`, bilinen yerler, konu ve yer terimleri avcıya geçiriliyor — yani
I-5'in konsept farkındalıklı sorgu planı ve sıralaması **canlı hatta
ulaşabiliyor**.

### Fixture entegrasyon testi — GERÇEK İNDİRME YOK

Sağlayıcı yanıtı, indirici, DNS çözücü ve kare kapısı **enjekte edilerek**
uçtan uca koşuldu: aday bulundu → lisans duvarından geçti → güvenli indirici
çağrıldı → kare kapısı çağrıldı → seçildi. Ücretli API yok, ağ yok, deploy yok.

### Ölçülen test sonucu (12 Ağu) — İKİ ORTAM AYRI

| Paket | A | B | C | D | E | F | G | H | I | Toplam |
|---|---|---|---|---|---|---|---|---|---|---|
| **Zengin venv** | 125 | 200 | 148 | 95 | 127 | 244 | 218 | **257** | **665** | **2079** |
| **Sistem Python** | 125 | 200 | 148 | 95 | 127 | 244 | 218 | **203** | **665** | **2025** |

0 hata. Faz I 614 → **665** (+51). Faz B **200/0** — gerileme yok.
pyflakes temiz.

### BİLİNEN SINIRLAR (dürüstçe)

1. **Gerçek üretimle hiç koşulmadı.** Bayrak açıkken canlı bir iş
   çalıştırılmadı; kanıt yalnızca fixture. **Açmadan önce gerçek pilot şart.**
2. ~~**Maliyet ölçülmedi.** Pipeline bütçe defteri geçirmiyor (`defter=None`).~~
   → ✅ **§24'te (I-7) kapatıldı**: iş başına `IsButcesi`, varsayılan USD 0.0.
3. **Sahne planı `iddia_metni`/`fact_id` üretmiyor.** Pipeline'ın plan
   çıktısında bu alanlar çoğunlukla boş; köprü o zaman `footage_sorgu`ya
   düşüyor. Yani araştırma-bağlantılı seçim henüz tam beslenmiyor.
4. **Yalnızca footage sahnelerinde devrede.** AI görsel ve Sora/Grok yolları
   dokunulmadı.
5. ~~**`kayit_sifirla()` iş başına global durum kullanıyor.**~~ →
   ✅ **§24'te (I-7) kapatıldı**: sayaçlar iş başına izole `IsButcesi`
   nesnesinde; iki paralel fixture işiyle kanıtlandı.
6. **Hikâye/animasyon hatları test edilmedi**; köprü tür ayrımı yapmıyor,
   yalnızca footage sahnesi koşuluna bakıyor.

### SONRAKİ ADIM

~~Bütçe defteri + koşu sınırı bağlanması~~ → §24'te yapıldı. Kalan: plan
çıktısına `iddia_metni`/`fact_id` taşınması, sonra **kontrollü gerçek pilot**.

---

## 24. FAZ I-7 — İŞ BAŞINA BÜTÇE ve PARALEL İŞ İZOLASYONU (12 Ağu, ölçüldü)

> **Durum: commit `6294369`, `origin/arastirma-motoru`'na PUSH EDİLDİ. Deploy YOK.**
> **Bayrak HÂLÂ varsayılan KAPALI.**
> Değişen: `webapp/medya_kopru.py`, `webapp/pipeline.py`,
> `webapp/testler/test_faz_i.py` (+ bu handoff).
> **Dokunulmadı:** `server.py`, tüm arayüz, 22 alanlık generate sözleşmesi,
> `medya/lisans.py`, `medya/guvenlik.py`, `medya/indirme.py`,
> `medya/kare_kapisi.py`, `deploy.sh`.

### Kapatılan iki açık (§23 sınır 2 ve 5)

1. **Para tavanı yoktu.** Pipeline avcıya `defter=None` geçiyordu; "para
   tavanı bağlanmadan açılmamalı" uyarısı bunun içindi.
2. **Sayaçlar global sözlükteydi.** Aynı süreçte iki iş koşarsa sayaçlar
   karışıyordu; "iş başına tavan" iddiası karşılıksızdı.

### `IsButcesi` — beş tavan, tek nesne, iş başına

| Tavan | Env | Varsayılan |
|---|---|---|
| USD | `MEDYA_AVCI_MAKS_USD` | **0.0** |
| Süre (sn) | `MEDYA_AVCI_IS_SN` | 240 |
| İstek | `MEDYA_AVCI_MAKS_ISTEK` | 60 |
| Bayt | `MEDYA_AVCI_MAKS_BAYT` | 400 MB |
| Kare çağrısı | `MEDYA_AVCI_MAKS_KARE` | 40 |

⚠ **Varsayılan USD 0.0** — hiçbir ücretli çağrıya yer ayrılmaz; açmak açık bir
karardır. Negatif tavan `ValueError`. Sıfır geçmek kapıyı **kapatır**,
sınırsız yapmaz.

`ozet()` **beşini birlikte** raporlar: harcanan/tavan USD, istek, bayt, kare
çağrısı, geçen süre, `tavan_doldu`, `durma_nedeni`, denenen/seçilen, düşüşler.

**Para tavanı artık gerçekten uygulanıyor:** `IsButcesi` bir `MaliyetDefteri`
(tavanlı) ve bir `KosuSiniri` kuruyor ve bunları avcıya **geçiriyor** —
sağlayıcı katmanında `ButceAsimi` yakalanıp koşu durduruluyor.

### Thread güvenliği ve izolasyon — ölçüldü

- `istek_ayir` / `kare_ayir` / `bayt_ayir` kontrol+harcamayı **tek kilit
  altında** yapıyor. 8 thread × 20 deneme, tavan 10 → **tam 10** verildi.
- **İki paralel fixture işi:** A 3 sahne, B 1 sahne → `istek` 6 vs 2,
  `kare_cagrisi` 3 vs 1, `bayt` 27000 vs 9000, düşüşler 7 vs 3.
  **Sayaçlar karışmıyor**, bütçe nesneleri ayrı, birinin tavanı dolunca
  diğeri etkilenmiyor.

### Limit aşılınca kontrollü dur

Her tavan için ayrı fixture testi: istek tavanı → `BUTCE`; kare tavanı 0 →
klip **doğrulanamaz, dolayısıyla kabul edilmez** (fail-closed) ve **diskten
silinir**; bayt tavanı → klip kabul edilmez. Hepsinde `ok=False`, yol boş,
aday boş — **rastgele stok yok**, çağıran taraf mevcut güvenli yolunu sürdürür.

### Bu adımda bulunan ve düzeltilen GERÇEK kusur

Döngü bütçe yüzünden kırıldığında fonksiyonun **son dönüşü sabit
`KARE-KAPISI`** diyordu — yani bütçe durdurmasını "kare kapısı reddetti" diye
raporluyordu. `son_neden` izleyicisi eklendi; artık gerçek sebep dönüyor
(`BUTCE` / `SURE-ASIMI` / `INDIRME-BASARISIZ` / `KARE-KAPISI` / `ADAY-YOK`).
Test bunu yakaladı ve şimdi kilitliyor.

### Geriye uyumluluk

`butce` verilmeden yapılan eski çağrı yolu hâlâ çalışıyor (modül düzeyinde
varsayılan bütçeye düşer); `ozet()`/`dususler()` eski imzalarıyla duruyor ve
`ozet()` hâlâ `acik` bayrağını taşıyor. Pipeline artık **global sayaç
kullanmıyor** (testli).

### Ölçülen test sonucu (12 Ağu) — İKİ ORTAM AYRI

| Paket | A | B | C | D | E | F | G | H | I | Toplam |
|---|---|---|---|---|---|---|---|---|---|---|
| **Zengin venv** | 125 | 200 | 148 | 95 | 127 | 244 | 218 | **257** | **715** | **2129** |
| **Sistem Python** | 125 | 200 | 148 | 95 | 127 | 244 | 218 | **203** | **715** | **2075** |

0 hata. Faz I 665 → **715** (+50). Faz B 200/0 — gerileme yok. pyflakes temiz.
§20c'deki iki bağlantı kontrolü **silinmedi, güncellendi** (kural aynı kaldı,
yalnızca özetin kaynağı iş bütçesine taşındı).

### BİLİNEN SINIRLAR (dürüstçe)

1. **Gerçek üretimle hâlâ koşulmadı.** Bayrak kapalı; kanıt yalnızca fixture.
   **Açmadan önce kontrollü pilot şart.**
2. ~~**Plan çıktısı `iddia_metni`/`fact_id` üretmiyor** (§23 sınır 3)~~ →
   ✅ **§25'te (I-8) kapatıldı.**
3. **USD sayacı yalnızca `MaliyetDefteri`ye yazılanı görür.** Avcı bir maliyeti
   deftere kaydetmezse bütçe onu bilemez; yani tavan "deftere yazılan" harcama
   içindir, ölçülmeyen harcamayı yakalamaz.
4. **Kare çağrısı tavanı `kare_kapisi.KareButce`den ayrıdır.** İkisi ayrı
   sayar; toplam vision maliyeti iki tavanın **toplamıyla** sınırlıdır, tek
   bir sayıyla değil.
5. **Bayt tavanı indirme sonrası uygulanır.** `guvenli_indir` kendi akış
   tavanını uygular ama iş toplamı ancak dosya indikten sonra bilinir; yani
   tavan bir dosya kadar aşılabilir.
6. Yalnızca footage sahnelerinde devrede; hikâye/animasyon hatları test
   edilmedi (§23 sınır 4 ve 6 aynen geçerli).

---

## 25. FAZ I-8 — DOĞRULANMIŞ OLGU → SAHNE ve MEDYA BAĞI (12 Ağu, ölçüldü)

> **Durum: commit `e450aa0`, `origin/arastirma-motoru`'na PUSH EDİLDİ. Deploy YOK.**
> **Bayrak HÂLÂ varsayılan KAPALI.**
> Değişen: `webapp/arastirma_kopru.py`, `webapp/pipeline.py`,
> `webapp/medya_kopru.py`, `webapp/testler/test_faz_i.py` (+ bu handoff).
> **Dokunulmadı:** `server.py`, tüm arayüz, 22 alanlık generate sözleşmesi,
> `medya/lisans.py`, `medya/guvenlik.py`, `medya/indirme.py`,
> `medya/kare_kapisi.py`, `deploy.sh`.

### Kapatılan açık (§23 sınır 3 / §24 sınır 2)

Sahne planı `fact_id`/`iddia_metni` **üretmiyordu**. Medya köprüsü (I-6) bu
alanları okuyordu ama hep boş buluyor ve `footage_sorgu`ya düşüyordu — yani
*"araştırma-bağlantılı medya seçimi"* iddiası karşılıksızdı.

### Yalnızca doğrulanmış iddia sahneye girer

`olgu_listesi(manifest)` **yalnızca** `manifest.kullanilabilir_iddialar()`
okur — yani `senaryoya_girebilir` olanları. O filtre zaten şunları eliyor:

| Durum | Sahneye girer mi? |
|---|---|
| `dogrulandi` (kaynaklı) | ✅ |
| `celiskili` | ❌ **testli** |
| `cozulmedi` | ❌ **testli** |
| kritik ama tek **zayıf** kaynak (ansiklopedi/blog/forum) | ❌ **testli** |

Havuzun tek kapısı bu fonksiyondur — test bunu da kilitliyor.

### Uydurma fact_id YOK

`fact_bagla(scenes, olgular)` deterministik belirteç örtüşmesiyle eşleştirir
(eşik `FACT_BAGLAMA_ESIGI`, varsayılan 0.16). Eşik altında kalan sahne
**kimlik almaz** ve `bosluklar` içinde görünür kılınır. Ölçülen fixture:

```
sahne0 "Endurance … pack ice"      -> f001
sahne1 "crew camped Elephant Isl." -> f002
sahne2 "cooking recipe vegetables" -> fact_id YOK, kapsam boşluğu
sahne3 (AI sahnesi)                -> hedefe girmez
kapsam %66.7
```

Rapor `esik`, `olgu_sayisi`, `kullanilan_fact`, `kapsam_pct` ve boşlukları
birlikte verir — *"her sahne kaynaklı"* gibi kanıtsız iddia üretilmez.

### Bu adımda bulunan ve düzeltilen GERÇEK kusur

İlk sürümde **olgu havuzu boşsa** fonksiyon sessizce dönüyordu: araştırma
koşmuş ama senaryoya girebilen tek iddia çıkmamışsa hiçbir kapsam boşluğu
yazılmıyordu. Test yakaladı; artık her footage sahnesi için
`"dogrulanmis olgu havuzu bos"` boşluğu kaydediliyor.

### Atıf zinciri fact_id'yi korur

Medya köprüsü dönüşü artık `fact_id`'yi hem üst düzeyde hem `aday` kaydında
taşıyor (`sorgu` alanıyla birlikte). *"Hangi iddia için hangi klip, hangi
lisansla"* sorusu sonradan cevaplanabilir.

### Geriye uyumluluk — bit-bit

- Bağ **yalnızca** `arastirma_sonuc.calisti` **ve** olgu listesi doluysa kurulur.
  Araştırma kapalı/başarısızsa hiçbir sahne değişmez.
- `Sonuc.sozluk()` **değişmedi** — `olgular` alanı iş sözleşmesine yazılmıyor
  (testli). `sonuc["olgu_bagi"]` yalnızca bağ kurulduğunda eklenir.
- Planın/kullanıcının **açık `fact_id`'si ezilmez** (testli).
- Bozuk girdide (`None`, dize, sayı, karışık liste) **çökmez**.
- Faz A **125/0** — araştırma paketinde gerileme yok.

### Ölçülen test sonucu (12 Ağu) — İKİ ORTAM AYRI

| Paket | A | B | C | D | E | F | G | H | I | Toplam |
|---|---|---|---|---|---|---|---|---|---|---|
| **Zengin venv** | 125 | 200 | 148 | 95 | 127 | 244 | 218 | **257** | **760** | **2174** |
| **Sistem Python** | 125 | 200 | 148 | 95 | 127 | 244 | 218 | **203** | **760** | **2120** |

0 hata. Faz I 715 → **760** (+45). pyflakes temiz. Gerçek ağ / ücretli API /
üretim / deploy **yok**; bayrak açılmadı.

### BİLİNEN SINIRLAR (dürüstçe)

1. **Eşleştirme kelime örtüşmesidir, anlam değil.** Eşik 0.16 sezgisel;
   gerçek plan çıktısıyla kalibre edilmedi. Yanlış eşleşme mümkün — ama
   yanlış eşleşme bile **doğrulanmış** bir iddiaya bağlanır, uydurmaya değil.
2. **Anlatım dili ile iddia dili farklıysa örtüşme düşer.** Türkçe anlatım +
   İngilizce iddia metni durumunda çoğu sahne boşlukta kalır (görünür).
3. **Gerçek üretimle koşulmadı** — kanıt yalnızca fixture; bayrak kapalı.
4. **Bir iddia birden çok sahneye bağlanabilir**; tekrar sınırı yok.
5. `iddia_metni` 180 karaktere kırpılıyor — uzun iddialarda bağlam kaybı olur.
6. Yalnızca footage sahneleri hedeflenir (AI/Sora sahneleri kasıtlı dışarıda).

---

## 26. FAZ I-9 — UÇTAN UCA EDİT PLANI ORKESTRASYONU (12 Ağu, ölçüldü)

> **Durum: commit `a0294d0`, `origin/arastirma-motoru`'na PUSH EDİLDİ. Deploy YOK.**
> **Bayrak varsayılan KAPALI.**
> Yeni: `webapp/edit_kopru.py`.
> Değişen: `webapp/testler/test_faz_i.py` (+ bu handoff).
> **Dokunulmadı:** `pipeline.py`, `server.py`, tüm arayüz, 22 alanlık generate
> sözleşmesi, `editor/` paketi (plan/adapter/qa_on/remotion_v2), `deploy.sh`.

### Kapatılan açık

Parçalar tek tek vardı ama **aralarında bağ yoktu**:

| Parça | Üretiyordu | Ama |
|---|---|---|
| `girdi_analizi` | konsept + stil | edit planına **gitmiyordu** |
| `stil_profili` | tempo/geçiş/palet/ses | EditorV2 props'a **gitmiyordu** |
| `arastirma_kopru` | doğrulanmış olgular | plan onları **görmüyordu** |
| `medya_kopru` | lisanslı klipler | render planına **geçmiyordu** |

Yani *"tek akışta araştırma + medya + kurgu"* iddiası uçtan uca
**kanıtlanmamıştı**. Bu adım zinciri fixture ile kurup **ölçüyor**.

### Ölçülen uçtan uca zincir (fixture, gerçek render/ağ YOK)

```
stil 'belgesel-arastirmaci' -> edit profili 'investigative-essay'
lisans duvari: 3 adaydan 1'i (lisans=unknown) ELENDI
kapsam boslugu s003 AYNEN tasindi (rastgele stokla KAPANMADI)
QA-on: WARN (fail=0, warn=2) -> render_edilebilir = True
efekt kapsami: 23 gercek / 0 bilinmeyen
props: 4 sahne + stilProfili + altyaziStil
```

Her sahnede korunduğu **test edilen** alanlar: `scene_id` · `fact_id` ·
`asset_id` · `saglayici` · **`lisans`** · `sure_sn`/`bas_sn` (ritim) ·
`cekim_turu`/`hareket`/`kadraj` (kamera) · `motion` · **geçiş** (motion spec
içinde) · tipografi katmanı · `ses`/`j_cut`/`l_cut` (ducking) · `islev`.

### Sert kurallar — hepsi testli

1. **Lisanssız medya render planına giremez.** `lisans_suz()` yalnızca
   `render_kullanilabilir` olanları geçirir; elenenler `elenen_medya` içinde
   **nedeniyle** görünür.
2. **Kapsam boşluğu rastgele stokla kapanmaz.** Boşluk aynen taşınır; boş
   sahne `asset_id`/`lisans` **boş** kalır. Hiç lisanslı aday yoksa
   `MEDYA-YOK` ile kontrollü durulur.
3. **QA-on FAIL → render başlatılmaz.** `render_edilebilir=False`,
   `neden="QA-FAIL"`, uyarıda açıkça yazılır. PASS/WARN ayrımı `qa` içinde
   görünür; WARN render'ı engellemez. FAIL'de plan yine üretilir (inceleme için).
4. **Desteklenmeyen efekt gizlenmez.** `efekt_kapsami` sayımı + adapter'ın
   `kayip_efektler` listesi uyarılara yazılır (ör. `light-sweep → flash`,
   `data-chart → callout`).

### Stil profili kararları props'a taşınıyor

`props["stilProfili"]` — kimlik/sürüm/kaynak + 6 boyut (tempo, geçiş, kamera,
tipografi, renk, ses/ducking). Remotion bilmediği alanı yok sayar; amaç
**izlenebilirlik**: "hangi stil kararı hangi videoda uygulandı".

Bilinmeyen stil kimliği **varsayılan** profile düşer — uydurma profil üretilmez.

### Mevcut yol değişmedi

`pipeline.py` bu modülü **import etmiyor**; `VidrushVideo` hızlı render yolu
aynen duruyor. Köprü **render etmiyor** ve **ağ çağırmıyor** — ikisi de
**AST ile** ölçüldü (ham dize taraması modülün kendi dokümantasyonunu
yakalıyordu; ölçüm yöntemi düzeltildi).

### Ölçülen test sonucu (12 Ağu) — İKİ ORTAM AYRI

| Paket | A | B | C | D | E | F | G | H | I | Toplam |
|---|---|---|---|---|---|---|---|---|---|---|
| **Zengin venv** | 125 | 200 | 148 | 95 | 127 | 244 | 218 | **257** | **823** | **2237** |
| **Sistem Python** | 125 | 200 | 148 | 95 | 127 | 244 | 218 | **203** | **823** | **2183** |

0 hata. Faz I 760 → **823** (+63). **Faz C 148/0** — editor paketinde
gerileme yok. pyflakes temiz.

### BİLİNEN SINIRLAR (dürüstçe)

1. ~~**Pipeline'a bağlanmadı.**~~ → ✅ **§27'de (I-10) opt-in bağlandı.**
2. **Gerçek render denenmedi.** `render_edilebilir` bir **karardır**;
   `remotion_v2.render()` çağrılmadı, çıktı videosu görülmedi.
3. **Altyazı dizisi fixture'da boş** (TTS zamanlamasından gelir); tipografi
   kanıtı motion spec katmanlarına dayanıyor.
4. **Stil → edit profili eşlemesi 12 satırlık elle tablo**; ölçümle değil tür
   konvansiyonuyla kuruldu.
5. **QA FAIL senaryosu sahte FAIL ile sınandı** — gerçek bir FAIL üreten plan
   girdisiyle değil.

---

## 27. FAZ I-10 — EDİT KÖPRÜSÜ PIPELINE'A BAĞLI + MANİFEST DÖNÜŞÜMÜ (12 Ağu)

> **Durum: commit `477b168`, `origin/arastirma-motoru`'na PUSH EDİLDİ. Deploy YOK.**
> **Her iki bayrak da varsayılan KAPALI.**
> Değişen: `webapp/medya_kopru.py`, `webapp/pipeline.py`,
> `webapp/testler/test_faz_i.py` (+ bu handoff).
> **Dokunulmadı:** `edit_kopru.py`, `server.py`, tüm arayüz, 22 alanlık
> generate sözleşmesi, `editor/` paketi, `medya/lisans.py`,
> `medya/guvenlik.py`, `medya/kare_kapisi.py`, `deploy.sh`.

### Kapatılan iki açık (§26 sınır 1 ve 6)

1. `edit_kopru` **pipeline'a bağlı değildi** — canlı bir işte hiç çalışmıyordu.
2. `medya_kopru` çıktısı **`medya_manifest` biçiminde değildi** — fixture
   manifest kullanılmıştı, gerçek dönüşüm yoktu.

### `manifest_kur()` — yalnızca gerçekten geçmiş adaylar

Seçim kaydı **iş bütçesinde** tutulur (`IsButcesi.secildi(kayit)`), yani iş
başına izole. Kayıt **ancak** lisans duvarından **ve** kare kapısından geçmiş
bir aday için oluşur — manifest tanım gereği lisanslı + kare-doğrulanmış.

**Kaybolmayan alanlar (her biri testli):** `fact_id` · `asset_id` ·
`saglayici` · `lisans` · `orijinal_url` · `eser_sahibi` · `atif_metni` ·
`scene_id` · `medya_yolu`.

**Savunma katmanı:** `render_kullanilabilir` bayrağı olmayan ya da
`asset_id`'siz kayıt manifeste **girmez** (testli). Bozuk girdide çökmez.

**Kapsam boşluğu aynen taşınır**, rastgele stokla kapanmaz; tekrar eden boşluk
kaydı teke iner ama görünürlük kaybolmaz. Avcı bir sahnede aday veremezse
pipeline `bosluk_ekle()` ile bunu **kayda geçirir** — eski yol klip bulsa bile
o sahne avcı zincirinden geçmemiştir.

### Pipeline bağlantısı — opt-in, RENDER YOK

`EDITOR_V2=1` veya dahili `{"editor_v2": True}` iken:
manifest kurulur → lisanslı aday yoksa `MEDYA-YOK` ile **plan denenmez** →
varsa `edit_kopru.plan_kur()` çağrılır → özet `sonuc["edit_plani"]`e yazılır.

⚠ **Bu atomda gerçek render YOK.** `pipeline.py` `remotion_v2`'yi import bile
etmiyor (testli); mevcut `hizli_render` yolu aynen çalışıyor. QA FAIL ise
`render_edilebilir=False` döner ve zaten hiçbir render fonksiyonu çağrılmaz.

Hata durumunda **kontrollü fallback**: `{"ok": False, "neden": "HATA"}` yazılır,
üretim bozulmaz.

### Fixture çağrı zinciri — dört senaryo (testli)

| Senaryo | Sonuç |
|---|---|
| Kapalı yol | plan **üretilmiyor** (`KAPALI`) |
| Açık + lisanslı manifest | plan oluşuyor, `fact_id`+`lisans` props'a kadar geliyor |
| Açık + QA FAIL | `render_edilebilir=False`, `neden="QA-FAIL"` |
| Kötü (lisanssız) medya | `MEDYA-YOK`, props boş, red gerekçeli |

### Ölçülen test sonucu (12 Ağu) — İKİ ORTAM AYRI

| Paket | A | B | C | D | E | F | G | H | I | Toplam |
|---|---|---|---|---|---|---|---|---|---|---|
| **Zengin venv** | 125 | 200 | 148 | 95 | 127 | 244 | 218 | **257** | **879** | **2293** |
| **Sistem Python** | 125 | 200 | 148 | 95 | 127 | 244 | 218 | **203** | **879** | **2239** |

0 hata. Faz I 823 → **879** (+56). pyflakes temiz.

⚠ §23b'deki bir kontrol **güncellendi, silinmedi**: I-9 döneminde "pipeline
`edit_kopru`'yu import etmiyor" bir *bilinen sınırı* kilitliyordu; I-10 onu
kasıtlı kapattı. Kuralın niyeti (mevcut hızlı render yolu korunmalı, yeni yol
opt-in olmalı) aynı kaldı, ölçüm ona göre yeniden yazıldı.

### BİLİNEN SINIRLAR (dürüstçe)

1. **Gerçek render hâlâ denenmedi** (kasıtlı, bu atomun kapsamı değil).
   `render_edilebilir=True` çıksa bile hiçbir şey render edilmiyor.
2. **Canlı bir işle koşulmadı.** Her iki bayrak kapalı; kanıt yalnızca fixture.
3. **Cümleler `props_sahneler`den türetiliyor**; `anlatim` alanı boşsa plan
   zayıf beat üretir. Gerçek anlatım metniyle kalibrasyon yapılmadı.
4. **Stil profili pipeline'dan geçirilmiyor** (`stil=None`) — bu yüzden edit
   profili şu an hep varsayılana düşüyor. Bağlamak ayrı bir adım.
5. **Manifest yalnızca avcı yolundan beslenir.** Eski `kaynak.py` yoluyla inen
   klipler manifeste **girmez**; yani avcı kapalıyken plan hiç kurulamaz.
6. `edit_plani` özeti iş sözleşmesine değil yalnızca `sonuc` sözlüğüne yazılır;
   `server.py` bu alanı okumadığı için arayüzde **görünmez**.

---

## 28. FAZ I-11 — 20 SANİYELİK **GERÇEK** RENDER SMOKE (12 Ağu, ölçüldü)

> **Durum: commit `f4e3a5e`, `origin/arastirma-motoru`'na PUSH EDİLDİ. Deploy YOK.**
> **Bayraklar varsayılan KAPALI.**
> Yeni: `webapp/testler/smoke_editorv2_20sn.py`, `outputs/sample/README.md`.
> Değişen: `webapp/medya_kopru.py`, `webapp/testler/test_faz_i.py`,
> `.gitignore` (+ bu handoff).
> **Dokunulmadı:** `pipeline.py`, `server.py`, arayüz, 22 alan, `editor/`
> paketi, `edit_kopru.py`, `deploy.sh`.

### Keşif: bağımlılıklar GERÇEKTEN var

| Bağımlılık | Durum |
|---|---|
| ffmpeg / ffprobe | ✅ 8.1.1, `/opt/homebrew/bin` |
| node / npx | ✅ v24.14.1 / 11.11.0 |
| `app/render-studio/node_modules` | ✅ **var** (Remotion 4.0.410) |
| `VidrushEditorV2` kompozisyonu | ✅ `src/Root.tsx`'te tanımlı |
| Chrome headless shell | ✅ `~/.cache/puppeteer` — **çevrimdışı render mümkün** |

⚠ Handoff §10 madde 4 *"yerelde node_modules yok → render edilemiyor"*
diyordu. **Bu artık doğru değil** — 30 karelik deneme render'ı ~1 sn'de,
ağ olmadan tamamlandı.

### Ölçülen çıktı — `outputs/sample/editorv2_smoke_20sn.mp4`

| Ölçüm | Değer |
|---|---|
| Codec | **h264 / aac** |
| Çözünürlük | 1280×720 @ 30 fps |
| Süre | **20.096 sn** |
| Boyut | 10.49 MB |
| Ses | 48 000 Hz / **2 kanal** |
| Render süresi | ~25 sn |
| Ön-render QA | **WARN** (fail=0, warn=5) → render'a izin verildi |
| Efekt kapsamı | 38 spec, **hepsi `gercek`** (0 bilinmeyen) |

Kareler çıkarıldı ve **gözle doğrulandı**: `kare_00s.png` ·
`kare_10s.png` (gerçek Wikimedia Apollo arşiv fotoğrafı + grain/vinyet/
nişangâh katmanları) · `kare_19s.png` (motion-graphic fallback + tipografi).

### GERÇEK motorun çalışan kısmı

`edit_kopru.plan_kur()` → `editor.plan.uret()` (beat → gramer → motion →
tipografi → ses → **ön-render QA**) → `adapter.donustur()` →
`remotion_v2.dogrula()` → `props_hazirla()` → `render()` →
**Remotion `VidrushEditorV2`** (Chrome headless + ffmpeg).

Sahne zinciri raporda birebir duruyor: 4 beat gerçek medya + `fact_id` +
lisans (`cc-by-sa`, `cc-by`, `public-domain`) taşıyor; 2 beat'te medya yok →
**motion-graphic fallback** (rastgele stok **değil**).

### ⚠ Bu videonun KANITLAMADIĞI

- **Web'den medya bulma** — hiçbir sağlayıcıya istek atılmadı; görsel/ses
  daha önce indirilmiş yerel fixture (`public/editorv2/faz_e/`).
- Araştırma/fact-check motoru, TTS üretimi, canlı `/api/generate` hattı,
  ücretli API — hiçbiri koşmadı.
- **İçerik tutarlılığı:** fixture görselleri **Apollo/Ay**, fixture anlatımı
  **Endurance/Antarktika**. Görsel ile anlatım konu olarak **örtüşmüyor**.
  Bu kasıtlı: ölçülen şey motorun video üretip üretmediği.

Bu etiketler hem betiğin başlığında hem `outputs/sample/README.md`'de hem de
`smoke_rapor.json` içindeki `kapsam` bloğunda yazılı; testler üçünü de kilitliyor.

### Smoke'un ORTAYA ÇIKARDIĞI GERÇEK KUSUR

İlk render'da **görseller hiç görünmedi** (kareler 62–69 KB, düz koyu zemin).
Kök neden: `editor.plan` medya yolunu **`yerel_yol`** alanından okuyor
(`plan.py:203`), ama I-10'un `manifest_kur()`'u yalnızca `medya_yolu`
yazıyordu. Plan aday buluyor, **medyası boş** kalıyordu — sessiz kayıp.

Düzeltildi: `manifest_kur()` artık **iki adı da** yazıyor (geriye uyumlu).
İkinci render'da kareler 885 KB / 1149 KB'ye çıktı ve görseller göründü.
Test bunu kilitliyor.

⚠ Bu kusur yalnızca **gerçekten render edildiği için** görüldü; fixture
testleri props üretimini doğruluyordu ama *ekranda ne göründüğünü* değil.

### İkili dosyalar neden git'te değil?

MP4 + PNG ≈ **13 MB**. Git geçmişine giren ikili dosya geri alınamaz; bu
yüzden `.gitignore`'a alındı. **İzlenen:** `outputs/sample/README.md` ve
`smoke_rapor.json`. Video betik yerelde koşturularak yeniden üretilir.
Aksini istersen `.gitignore` satırları kaldırılabilir.

### Ölçülen test sonucu (12 Ağu) — İKİ ORTAM AYRI

| Paket | A | B | C | D | E | F | G | H | I | Toplam |
|---|---|---|---|---|---|---|---|---|---|---|
| **Zengin venv** | 125 | 200 | 148 | 95 | 127 | 244 | 218 | **257** | **919** | **2333** |
| **Sistem Python** | 125 | 200 | 148 | 95 | 127 | 244 | 218 | **203** | **919** | **2279** |

0 hata. Faz I 879 → **919** (+40). pyflakes temiz.
⚠ §25 testleri **render çalıştırmaz** (yavaş/ağır); betiğin sözleşmesini,
dürüstlük etiketlerini ve `yerel_yol` düzeltmesini kilitler.

### BİLİNEN SINIRLAR (dürüstçe)

1. **Fixture içeriği anlatımla örtüşmüyor** (Apollo görsel / Endurance metin).
2. **Web medya hattı hâlâ hiç koşulmadı** — bayraklar kapalı, ağ yok.
3. ~~**QA WARN'ın 5 uyarısı incelenmedi.**~~ → ✅ **§29'da (I-12) tek tek
   raporlandı; 3'ü motor kusuruydu ve kapatıldı.**
4. **Altyazı yok** — TTS zamanlaması olmadığı için altyazı dizisi boş; ekranda
   yalnızca başlık/etiket katmanları var.
5. **Sadece 1280×720** render edildi (hız için); 1080p ölçülmedi.
6. **Tek makinede, tek koşu.** Farklı donanımda süre/başarı ölçülmedi.

---

## 29. FAZ I-12 — 5 QA WARN RAPORU + CHAPTER-CARD KALİTESİ (12 Ağu, ölçüldü)

> **Durum: commit `9be6375`, `origin/arastirma-motoru`'na PUSH EDİLDİ. Deploy YOK.**
> **Bayraklar varsayılan KAPALI.**
> Değişen: `webapp/editor/plan.py`, `webapp/editor/tipografi.py`,
> `app/render-studio/src/editorv2/Grafikler.tsx`,
> `webapp/testler/test_faz_i.py`, `outputs/sample/README.md` (+ bu handoff).
> **Dokunulmadı:** `pipeline.py`, `server.py`, arayüz, 22 alan, `deploy.sh`.

### 5 QA WARN — tek tek raporlandı

| Kod | Detay | Kaynak | Durum |
|---|---|---|---|
| `TIPO-GUVENLI-ALT` ×3 | `source-label: alt=1020px > 1016` | **motor kusuru** | ✅ kapatıldı |
| `PACING-KISA-ORAN` | 4 sn altı oran %83, referans %32 | **fixture** | açık |
| `SAGLAYICI-TEKEL` | tek sağlayıcı %100 (tavan %40): wikimedia | **fixture** | açık |

Ayrıca 3 `uyari` seviyesinde `SUREKLILIK-AYNI-SAGLAYICI` — aynı fixture sınırı.

⚠ Kalan 2 WARN **motor kusuru değil**: QA, test verisinin gerçekçi olmadığını
doğru tespit ediyor. Gerçek bir işte farklı sağlayıcı adaylarıyla ikisi de düşer.

### Düzeltilen üç gerçek kusur

**1. Sayı uyduruluyordu.** `plan.py:88` medyasız beat'e **sabit `[1]`** ile veri
grafiği veriyordu → ekranda anlamsız dev **"1"** + tek sarı bar. Artık
`_beat_sayilari()` metinden **gerçek** sayı çıkarır (yıllar elenir: 1915/2024
veri değildir); sayı yoksa veri sahnesi **çizilmez**, profesyonel **bölüm
kartına** düşülür. `Grafikler.tsx` de boş veride `null` döner (derinlemesine
savunma).

**2. Başlık harf ortasından kırpılıyordu.** Bant `overflow:hidden` + `nowrap`
idi. Python tarafında karakter sınırını **hesaplasam bile** font metriği tahmin
olduğu için kırpma sürdü (iki render'da da görüldü). Kalıcı çözüm tahmine
güvenmemek: TSX metni sığdıramazsa **puntoyu oranla küçültür** (en fazla %30) —
harf **asla** kesilmez. Python ayrıca sarkan edat/bağlaçları atar
("…Elephant Island **in**" → "…Elephant Island").

**3. Güvenli alan aritmetiği yanlıştı.** `source-label` 0.90 + 0.045 = 0.945 →
**1020.6px > 1016**. Kod yorumunda **üç ayrı deneme** görünüyor (0.94 → 0.91 →
0.90) ama hiçbirinde hesap yapılmamış, "yeterince aşağı" varsayılmış.
0.895 → 1015.2px ✅.

⚠ **Aynı sınıftan ikinci bir kusur**, I-12'de eklenen *"tüm yazı türleri
güvenli alanda"* testiyle bulundu: `subtitle` 0.86 + 0.085 = 0.945 →
**1020.6px**. Altyazı katmanı henüz üretilmediği için QA'da hiç görünmemişti.
0.855 → 1015.2px ✅. Test artık **tüm türleri** birden kilitliyor.

### Kalite: ÖNCE / SONRA (ölçülen)

| | ÖNCE (I-11) | SONRA (I-12) |
|---|---|---|
| Ön-render QA | **5 WARN** | **2 WARN** |
| 19. sn karesi | anlamsız "1" + bar, başlık kırpık | temiz bölüm kartı, başlık tam |
| `source-label` alt | 1020.6 px (taşıyor) | 1015.2 px |
| 19 s kare boyutu | 78 KB | 104 KB |

Kare **gözle doğrulandı**: "THEY REACHED ELEPHANT ISLAND" tam görünüyor,
kırpma yok, bant alt-üçlü güvenli alanda dengeli.

### Bağımsız ffprobe (yeniden render sonrası)

```
h264 / 1280x720 / 30 fps · aac / 48000 Hz / 2 kanal
duration=20.096000 · size=10647774 bayt
```

### Ölçülen test sonucu (12 Ağu) — İKİ ORTAM AYRI

| Paket | A | B | C | D | E | F | G | H | I | Toplam |
|---|---|---|---|---|---|---|---|---|---|---|
| **Zengin venv** | 125 | 200 | 148 | 95 | 127 | 244 | 218 | **257** | **951** | **2365** |
| **Sistem Python** | 125 | 200 | 148 | 95 | 127 | 244 | 218 | **203** | **951** | **2311** |

0 hata. Faz I 919 → **951** (+32). **Faz C 148/0** — editor paketinde
gerileme yok.

### BİLİNEN SINIRLAR (dürüstçe)

1. **Kalan 2 WARN fixture kaynaklı, giderilmedi** — gerçek çok-sağlayıcılı
   veriyle düşmesi *beklenir* ama **ölçülmedi**.
2. **Punto küçültme oranı tahmine dayanıyor** (0.72 em). Gerçek font
   metriğiyle ölçülmedi; %30 taban güvenlik payıdır, kesin çözüm değil.
3. **Bölüm kartı tek satır.** Uzun başlık kısaltılır; iki satıra bölme yok.
4. **Altyazı hâlâ yok** — `subtitle` düzeltmesi *latent* bir kusurun önlemi,
   ekranda doğrulanmadı.
5. **Motion-graphic fallback tek tip.** Her medyasız beat aynı bölüm kartını
   alır; çeşitlilik (harita/belge/alıntı kartı) seçilmiyor.
6. **İçerik uyuşmazlığı sürüyor** (Apollo görsel / Endurance metin).
6. ~~`medya_kopru` çıktısı `medya_manifest` biçiminde değil.~~ →
   ✅ **§27'de (I-10) `manifest_kur()` ile çözüldü.**

---

## 30. FAZ I-13 — 10 SN KALİTELİ SESLİ APOLLO MİNİ-BELGESELİ (12 Ağu, ölçüldü)

> **Durum: commit `ca023f3`, `origin/arastirma-motoru`'na PUSH EDİLDİ.**
> **Deploy YOK. Bayraklar varsayılan KAPALI. Maliyet $0.00.**
> Yeni: `webapp/testler/smoke_kaliteli_ses_10sn.py`.
> Değişen: `webapp/testler/test_faz_i.py`, `outputs/sample/README.md`
> (+ bu handoff). **Kod tarafında pipeline/UI/editor değişmedi.**

### Konu tutarlılığı — §28'in en ağır sınırı kapatıldı

Önceki smoke'ta **Apollo görsel + Endurance metni** uyuşmazlığı vardı.
Şimdi üçü de aynı konudan: görsel (Faz E NASA/Wikimedia Apollo arşivi),
metin (Faz E manifestindeki **doğrulanmış** f001/f004/f005 iddiaları) ve
anlatım (aynı metnin seslendirmesi).

### Anlatıcı sesi — ölçülen seçim

Yereldeki hazır anlatım **`macOS say -v Yelda`** ile üretilmiş
(Faz E `pilot_rapor.json`), ölçümü **LRA 0.3–1.9** — düz, makine benzeri;
belgesel anlatımı kalitesinde **değil**. Bu yüzden projenin **kendi varsayılan
TTS motoru** (`app/uret.py` → edge-tts) kullanıldı.

| Aday | LRA | LUFS | Süre |
|---|---|---|---|
| **en-GB-RyanNeural** ✅ | **1.6** | −21.4 | 9.74 sn |
| en-US-AndrewNeural | 1.5 | −20.3 | 9.14 sn |
| en-US-BrianNeural | 0.5 | −20.2 | 8.95 sn |

Master: `pcm_s16le / 48 kHz / mono · 8.789 sn · LUFS −16.43 · TP −1.5 dBTP ·
LRA 2.0 · sessizlik %11.1 · kırpma yok`.

⚠ **Maliyet $0.00** — edge-tts anahtar istemez. Kredi yüklenmedi, anahtar
değiştirilmedi. $0.25 tavanı **hiç kullanılmadı**.
⚠ **Dürüst sınır:** LRA 2.0 iyi bir nöral TTS'tir, **insan anlatıcı değildir**
(gerçek spiker LRA 4–8).

### Görsel seçimi — ölçülen kapı (bu adımda bulunan kusur)

İlk render'da 0. ve 9. sn kareleri **düz gri** çıktı. Ölçüm nedeni gösterdi:
`a281` (detay std **6.1**) ve `a282` (**4.7**) havuzun en boş kareleriydi.
Artık kadraja düşen detay ölçülüyor, eşik altı (< 20) görsel **kullanılmıyor**.
Kare boyutları 647/543/578 KB → **865/925/1121 KB**; üç kare de gözle
doğrulandı (Eagle + astronot · ayak izi · bot izi yakın plan).

### Ölçülen çıktı

`outputs/sample/editorv2_quality_voice_10sn.mp4`

| Ölçüm | Değer |
|---|---|
| Video | **h264** 1280×720 @ 30 fps |
| Ses | **aac** 48 000 Hz / 2 kanal |
| Süre | **9.643 sn** · 8.22 MB |
| Miks | LUFS −16.56 · TP −4.47 dBTP · kırpma yok · sessizlik %19.6 |
| Ön-render QA | WARN (fail=0 warn=2) · on-render kapısı **PASS** |

### Ölçülen test sonucu (12 Ağu) — İKİ ORTAM AYRI

| Paket | A | B | C | D | E | F | G | H | I | Toplam |
|---|---|---|---|---|---|---|---|---|---|---|
| **Zengin venv** | 125 | 200 | 148 | 95 | 127 | 244 | 218 | **257** | **989** | **2403** |
| **Sistem Python** | 125 | 200 | 148 | 95 | 127 | 244 | 218 | **203** | **989** | **2349** |

0 hata. Faz I 951 → **989** (+38). §27 testleri render/TTS **çalıştırmaz**.

### BU VİDEO NEYİ KANITLAR / KANITLAMAZ

**Kanıtlar:** `editor.plan.uret` tam Faz C zinciri (beat → gramer → motion →
tipografi → ses → ön-render QA) · `adapter.donustur` · `remotion_v2`
doğrula/props_hazirla/render · **Remotion `VidrushEditorV2`** (Chrome headless
+ ffmpeg) · lisans duvarı + `fact_id` zincirinin props'a kadar gelmesi ·
edge-tts anlatım üretimi + ambiyans ducking.

**KANITLAMAZ:** web'den medya bulma (sağlayıcıya **hiç** istek yok) ·
araştırma/fact-check motoru (olgular hazır manifestten) · canlı
`/api/generate` hattı · ücretli API.

### BİLİNEN SINIRLAR (dürüstçe)

1. **Web araştırma/medya hattı hâlâ hiç koşulmadı** — bayraklar kapalı.
2. **LRA 2.0 insan anlatıcı değil**; nöral TTS sınırında.
3. **Bölüm kartı bu 10 sn'de görünmüyor** — üç sahnenin üçünde de medya var,
   fallback tetiklenmedi.
4. **Altyazı yok** (TTS kelime zamanlaması props'a bağlanmadı).
5. **Anlatım ile sahne sınırları hizalanmadı** — tek master ses; sahne başına
   segment eşlemesi yapılmadı.
6. Kalan 2 QA WARN fixture kaynaklı (tek sağlayıcı, kısa beat).

---

## 31. ⏭ SIRADAKİ ATOM — **I-14: KALİTE KAPILARI** (yeni oturum buradan devralır)

> **Durum (güncellendi): I-14 §32'de ölçtü, I-15 §33'te DÜZELTTİ.**
> Bu bölüm devir belgesi olarak **aynen duruyor**. Yedi kusurdan
> **1–5 kapandı** (başlık, sabit süre, ölü final, ambiyans, miks sessizliği);
> **6 (altyazı/künye) ve 7 (1080p) hâlâ AÇIK** — I-16'ya ait.
> Kusur 3'ün "tekrarlı medya" bacağı ölçülebilir biçimde hiç doğrulanamadı
> (bkz. §32 ve §33 "medya çeşitliliği").

### Bağlam

I-13'ün ürettiği `outputs/sample/editorv2_quality_voice_10sn.mp4` teknik
olarak geçerli (h264 1280×720 · aac 48 kHz stereo · 9.643 sn) **ama** bağımsız
denetimde **yedi somut kalite kusuru** ölçüldü. Bunların hiçbiri şu an QA'da
FAIL/WARN üretmiyor — yani **kapı yok**.

### Ölçülen yedi kusur (I-14'ün kapsamı)

| # | Kusur | Ölçüm |
|---|---|---|
| 1 | **Başlık sağdan kesiliyor** | 10 sn çıktıda hâlâ görülüyor — I-12'nin punto-küçültme düzeltmesi bu yolda yetmiyor |
| 2 | **Sahne süreleri sabit** | üç sahne de **3.2 sn** — ritim yok, anlatımla hizasız |
| 3 | **Son iki medya tekrarlı / semantik zayıf** | aynı görsel ailesi arka arkaya; içerik-metin bağı zayıf |
| 4 | **Ambiyans fiilen duyulmuyor** | kaynak **−48.7 LUFS**; seviye (0.20) + ducking (0.30) sonrası işitilemez |
| 5 | **Mikste %20 ölü alan** | `5.358–6.374` arası **1.016 sn**, `8.715–son` arası **0.928 sn** sessiz |
| 6 | **Altyazı ve kaynak künyesi yok** | ekranda ne altyazı ne `source-label` |
| 7 | **Yalnızca 720p** | smoke 1280×720; 1080p hiç ölçülmedi |

### I-14 için ÇALIŞMA SIRASI (önce test, sonra kapı)

1. **Önce ölçen testleri yaz.** Her kusur için deterministik bir ölçüm
   fonksiyonu + test. Testler **önce kırmızı** yanmalı — kusurun gerçekten
   var olduğunu kanıtlasın.
2. **Sonra QA sözleşmesine çevir.** Her ölçümü `editor/qa_on.py` (ön-render)
   ya da `qa_kopru`/`qa_son` (render sonrası) içinde **doğru seviyeyle**
   bağla:
   - **FAIL** (render başlatılmaz): başlık kesilmesi, ambiyans işitilemez
     seviye, %15'i aşan ölü alan
   - **WARN** (render'a izin, görünür uyarı): sabit sahne süresi, tekrarlı
     medya, altyazı/künye yokluğu, 1080p altı çıktı
   Seviye seçimini **gerekçesiyle** koda yaz; eşikleri sabit sayı olarak değil
   **hesaplanmış** ya da ölçülmüş değer olarak koy (I-12'deki `source-label`
   dersi: üç kez "yeterince aşağı" varsayıldı, hiç hesaplanmadı).
3. **Aynı 10 sn fixture ile yeniden render et**, ffprobe + 0/5/9 sn kareleri
   çıkar, **önce/sonra** dürüst karşılaştırma yaz.
4. Tam A–I yeşilse **stage + handoff**, **commit atmadan dur**.

### I-14 KISITLARI (değişmez)

- Bayraklar **varsayılan kapalı** · **deploy yok** · **ücretli API yok** ·
  dış ağ yok (edge-tts hariç, o da $0.00)
- `pipeline.py` varsayılan yolu, **22 alanlık generate sözleşmesi**, modüler
  UI (basit mod, süre seçici, ünlü modu, ses kütüphanesi, Grok alanları),
  `deploy.sh` korumaları **değişmeyecek**
- Lisans duvarı · SSRF · kare kapısı · iş bütçesi (varsayılan USD 0.0)
  **zayıflatılmayacak**
- Kapsam boşluğu **rastgele stokla kapatılmayacak**; uydurma sayı/fact/medya
  **üretilmeyecek**
- İkili çıktılar (`outputs/sample/*.mp4`, `*.png`) git'e **eklenmeyecek**

### Yeni oturum için başlangıç komutları

```bash
cd /Users/polatcan/vidrush-docker && git log --oneline -1   # ca023f3 olmalı
```

Test koşumu ve ortam notları için **§14**'e bak (`edge-tts`, `pyflakes`,
`fastapi` gerekir; `node` olmadan §25/§27 BLOKE yazar).

---

## 32. FAZ I-14 (1. atom) — KALİTE KAPILARI ÖLÇÜLDÜ ve QA'YA BAĞLANDI (12 Ağu)

> **Durum: yerel yeşil, `origin/arastirma-motoru`'na push edildi. Deploy YOK.**
> **Tüm bayraklar varsayılan KAPALI. Maliyet $0.00 — ağ/ücretli API yok.**
> Yeni: `webapp/editor/kalite_kapisi.py`.
> Değişen: `webapp/editor/qa_on.py`, `webapp/editor/qa_son.py`,
> `webapp/editor/plan.py`, `webapp/edit_kopru.py`,
> `webapp/testler/test_faz_i.py` (+ bu handoff).
> **Dokunulmadı:** `pipeline.py`, `server.py`, tüm arayüz, 22 alanlık generate
> sözleşmesi, `deploy.sh`, lisans duvarı, SSRF, kare kapısı, iş bütçesi.

### Bu atomun kapsamı — ve kasıtlı olarak NE OLMADIĞI

§31 iki iş tanımlamıştı: (1) kusurları **ölçen** kapılar, (2) kusurların
**giderilmesi**. Bu atom **yalnızca (1)**'dir. Kapı açıldığında I-13'ün 10 sn
çıktısı **FAIL veriyor ve render engelleniyor** — bu beklenen ve doğru sonuç,
kusurlar gerçek. Düzeltme I-15'e ait; sahte PASS üretmemek için kapı
gevşetilmedi.

### Ölçülen kusurlar — hepsi GERÇEK artefakttan

Kanıt uydurma fixture'dan değil, depoda **izlenen** iki rapordan geliyor
(`.mp4`/`.png` `.gitignore`'da, bu yüzden ölçümler rapordan okunur —
test temiz klonda da koşar):

| # | Kusur | Ölçülen değer | Kaynak |
|---|---|---|---|
| 1a | Başlık **kelime ortasından kesik** | `"20 JULY"` → `"20 JU"` | `quality_voice_rapor.json` + smoke kaynağı |
| 1b | Başlık bandı **taşıyor** | 1287.7 px çizim / 1015.2 px alan = **272.5 px taşma** | ffprobe genişliği (1280) |
| 2 | **Aynı varlık arka arkaya** | `a082` b001+b002'de | `smoke_rapor.json` (I-11, 20 sn) |
| 3a | **Sabit blok süreler** | 3 sahne de 3.2 sn, yayılım **0.0 sn** | `quality_voice_rapor.json` |
| 3b | Süreler **anlatıma bağlı değil** | anlatım ağırlığı %30 değişiyor, süre %0 | aynı |
| 3c | **Ölü final** | plan 0.811 sn · ölçülen **0.903 sn** (tavan 0.5) | aynı + silencedetect |
| 4a | **Miks sessizlik oranı** | 1.887 sn / 9.643 sn = **%19.6** (tavan %15) | aynı |
| 4b | **Ambiyans duyulmuyor** | anlatımın **57.12 dB** altında | ffmpeg loudnorm |

### Kusur 1'in KÖK NEDENİ — üç katmanlı, ölçüldü

I-12 "punto küçültme" düzeltmesi yapmıştı ama bu yolda yetmiyor. Neden:

1. **`plan.py:57` sabit `b.metin[:42]` dilimi kullanıyor.** Aynı dosyada
   `kart_basligi_siniri()` **zaten var** ve hesaplıyor — ama yalnızca `data`
   çekimi fallback'inde çağrılıyor, `chapter-title` katmanında değil.
   I-12 iki yoldan **birini** düzeltmiş.
2. **Plan 1920'ye göre hesaplıyor, render 1280'e yapılıyor.**
   `remotion_v2.render(olcu=(1280,720))` props'u eziyor, `Root.tsx`
   `calculateMetadata` onu okuyor. Ölçülen sığan karakter: **1920'de 45,
   1280'de 29** — plan 42 verdi.
3. **TSX'in kendi sığdırma hesabı `letterSpacing`'i saymıyor.**
   `Grafikler.tsx:51` `length * punto * 0.72` diyor ama satır 74'te
   `letterSpacing: '0.01em'` var. Üstelik küçültmenin **%70 tabanı** var
   (satır 52); taban vurulduktan sonra `overflow: hidden` **harf ortasından
   keser**. 1280'de taban gerçekten vuruldu (punto 60 → 42).

⚠ **Nominal 1920'de bile taşıyor** (10.9 px) — yani kusur yalnızca çözünürlük
farkından değil, `letterSpacing` boşluğundan da geliyor.

### Kusur 3c/4a'nın ÖLÇÜLEMEZ olmasının nedeni — post-QA kör noktası

`qa_son.komut_plani`'nın `sessizlik` geçişi `silencedetect=...:d=1.2`
kullanıyor. I-13'ün iki boşluğu **0.984 sn** ve **0.903 sn** — ikisi de bu
eşiğin altında, yani post-QA onları **hiç görmedi**. Bu yüzden `d=0.30`'luk
ayrı bir **ince geçiş** eklendi; **yalnız kapı açıkken** koşar (kapalı yolda
fazladan ffmpeg geçişi yok, komut planı **7 komutla birebir aynı**).

Test bunu doğrudan kanıtlıyor: aynı video, kaba geçişte ölü kuyruk **0.0**,
ince geçişte **0.903**.

### `webapp/editor/kalite_kapisi.py` — saf ölçüm modülü

**6 ölçüm · 7 render sabiti · 6 eşik · 1 enjekte okuyucu** (`kapsam_ozeti()`).

- **Ağ/dosya/alt-süreç yok** — `os`, `subprocess`, `requests` **import
  edilmiyor**; AST ile ölçülüyor (ham dize taraması modülün kendi
  dokümantasyonunu yakalıyordu — I-9 dersi).
- **Render sabitleri `Grafikler.tsx`'ten okundu**, uydurulmadı: `0.72 · 0.01em
  · 0.84 · 0.42 · 2.4 · 0.70 · IZGARA_X`. Test TSX ile eşliği kilitliyor.
- **Ölçemediyse "temiz" demiyor.** Benzerlik okuyucusu verilmezse
  `benzerlik_olculdu=False` **ve** `benzerlik_temiz=False` — "benzer medya
  yok" iddiası üretilmiyor.
- **Hiçbir girdide istisna fırlatmıyor** (`None`, `{}`, `"x"`, `5`, `NaN`,
  `inf`, karışık liste — hepsi testli).

### Eşikler — hesaplanmış ya da ölçülmüş, sabit sayı değil

| Eşik | Değer | Nereden |
|---|---|---|
| Sabit blok | 0.05 sn | 30 fps'te ~1.5 kare — izleyici için ayırt edilemez |
| Ölü final | 0.5 sn | kullanıcı kararı (I-14 önceliği) |
| Sessizlik oranı | %15 | §31 devir belgesi |
| Benzerlik | 0.86 | Apollo havuzunda ölçüldü (farklı kareler %60–75 bandında) |
| Anlatım sapması | 0.15 | süre/ağırlık yayılım karşılaştırması |
| Ambiyans farkı | 30 dB | ⚠ **beyan edilmiş tasarım eşiği** — dinleme testi değil |

### QA sözleşmesi — kapalı varsayılan, açıkken gerçek kapı

Yeni kodlar: `KALITE-BASLIK-KIRPIK · KALITE-BASLIK-TASMA ·
KALITE-MEDYA-TEKRAR · KALITE-RITIM-SABIT · KALITE-OLU-FINAL` (ön-render,
hepsi **fail**) ve `POST-SESSIZ-ORAN · POST-OLU-FINAL · POST-AMBANS-DUYULMAZ`
(render sonrası, hepsi **fail**).

**Kritik tasarım kararı:** kapı kapalıyken bu kodların **hiçbiri
üretilmiyor**, ama **ölçüm yine de** `olcumler["kalite"]` altına yazılıyor.
Yani varsayılan yolun PASS/WARN/FAIL kararı **bit-bit aynı** kalıyor ve ölçüm
de gizlenmiyor. Faz A–H'nin 1414 kontrolü bu yüzden dokunulmadan geçiyor.

Açma yolları (üçü de **açık karar**, yalnız gerçek `True`; `"evet"`/`1` açmaz):
`kalite_kapisi=True` parametresi · `KALITE_KAPISI=1` ortam değişkeni ·
dahili `{"kalite_kapisi": True}` iş ayarı.

### Uçtan uca ölçüm — GERÇEK 10 sn planı

```
KAPI KAPALI (varsayilan)   QA=WARN  fail=0 warn=2   render_edilebilir=True
KAPI ACIK                  QA=FAIL  fail=4 warn=2   render_edilebilir=False
                             FAIL KALITE-BASLIK-KIRPIK   'JU' <- 'JULY'
                             FAIL KALITE-BASLIK-TASMA    272.5px tasma
                             FAIL KALITE-RITIM-SABIT     [3.2, 3.2, 3.2]
                             FAIL KALITE-OLU-FINAL       0.811 sn
```

Kapalı sonuç I-13'ün rapor ettiği **WARN (fail=0 warn=2)** ile birebir aynı —
gerileme yok.

### DÜRÜST SONUÇ — kusur 2 bu çıktıda YOK

§31 "son iki medya tekrarlı" diyordu. **10 sn çıktısında ölçülebilir medya
tekrarı yok:** üç ayrı varlık, dHash yapısal benzerlik en fazla **%60.9**,
tonal histogram kesişimi en fazla **%67.9** — ikisi de 0.86 eşiğinin altında.
Kapı burada **haklı olarak sessiz**.

Eşiği kırmızı yansın diye 0.65'e çekmedim: bu **sahte FAIL** olurdu ve
üretimde meşru biçimde farklı görüntüleri elerdi. Bunun yerine kapının
gerçekten çalıştığı **başka bir gerçek artefaktla** kanıtlandı — I-11'in
20 sn çıktısında `a082` **arka arkaya** iki sahnede kullanılmış.

⚠ §31'in "semantik zayıf" gözlemi (5. ve 9. sn kareleri ikisi de gri ay
yüzeyi yakın planı) **gerçek** ama **algısal/anlamsal** bir yargı; ölçtüğüm üç
deterministik araçtan hiçbiri onu yakalamıyor. Bu, ölçüm boşluğu olarak
**açık bırakıldı** — kapatıldığı iddia edilmiyor.

### Bu atomda bulunan ve düzeltilen kendi hatam

`kelime_ortasi_kesik()` ilk sürümde `_KELIME_SON.match(b)` kullanıyordu.
`match()` dizenin **başından** bağlar; `[\w]$` deseni `match` ile ancak tek
karakterlik dizede tutar. Sonuç: ölçüm **sessizce hep `False`** dönüyordu —
yani kapı en ağır kusuru göremiyordu. Gerçek artefaktla koşturulunca yakalandı
(`.search()`), test artık kilitliyor.

### Ölçülen test sonucu (12 Ağu) — İKİ ORTAM AYRI

| Paket | A | B | C | D | E | F | G | H | I | Toplam |
|---|---|---|---|---|---|---|---|---|---|---|
| **Zengin venv** | 125 | 200 | 148 | 95 | 127 | 244 | 218 | **257** | **1060** | **2474** |
| **Sistem Python** | 125 | 200 | 148 | 95 | 127 | 244 | 218 | **203** | **1060** | **2420** |

0 hata. Faz I 989 → **1060** (+71). Zengin venv'de 1 BLOKE (`QA_TEST_VIDEO`),
sistem Python'da 2 çevresel BLOKE (`fastapi` yok). **BLOKE'ler PASS
sayılmadı.** Faz C **148/0** — editor paketinde gerileme yok.
`deploy.sh`'nin tanımsız-isim taraması elle koşuldu → **0 bulgu**.

### BİLİNEN SINIRLAR (dürüstçe)

1. **Hiçbir kusur GİDERİLMEDİ.** Bu atom yalnızca ölçüp kapıya bağladı.
   Kapı açıkken 10 sn fixture'ı render edilemez — düzeltme I-15.
2. **Yeniden render YAPILMADI**, dolayısıyla §31'in istediği "önce/sonra kare
   karşılaştırması" **yok**. Karşılaştırılacak "sonra" hâli henüz üretilmedi.
3. **Ambiyans 30 dB eşiği dinleme testiyle doğrulanmadı** — beyan edilmiş
   tasarım kararı. Girdiler (−48.68 LUFS, 0.20, 0.30, −16.43 LUFS) gerçek
   ölçüm; eşik değil.
4. **Benzerlik eşiği 0.86, 7 görüntülük tek havuzda kalibre edildi.** Gerçek
   stok dağılımında yanlış pozitif/negatif oranı **bilinmiyor**.
5. **Anlatım bağı kelime sayısıyla ölçülüyor**, gerçek TTS kelime
   zamanlamasıyla değil. Vekil ölçüm olduğu kodda yazılı.
6. **`em` oranları hâlâ tahmin.** Gerçek Montserrat font metriği okunmuyor;
   TSX'in kendi tahminiyle **tutarlı** olması sağlandı, doğruluğu ölçülmedi.
7. **Altyazı, kaynak künyesi, 1080p ve gelişmiş motion bu atomda YOK** —
   `kapsam_ozeti()["kapsam_disi"]` bunu açıkça sayıyor.
8. **Canlı `/api/generate` hattı bu kapıyı görmüyor** — `qa_kopru` yalnızca
   `qa_son`'un varsayılan (kapalı) yolunu çağırıyor.

### SONRAKİ ATOM (I-15 — bu atomda YAPILMADI)

1. `plan.py:57` sabit `[:42]` → `kart_basligi_siniri()` + `_kart_basligi()`
   (fonksiyonlar **zaten var**, yalnız bu yola bağlanmamış).
2. Render kare ölçüsünün plana **bildirilmesi** (1920/1280 uyuşmazlığı).
3. TSX sığdırma hesabına `letterSpacing` eklenmesi.
4. Sahne sürelerinin anlatım/olgu uzunluğundan türetilmesi + ölü kuyruğun
   kırpılması.
5. Ambiyans kaynağının duyulabilir seviyeye getirilmesi.
6. Sonra **yeniden render + dürüst önce/sonra kare karşılaştırması**.

---

## 33. FAZ I-15 — GERÇEK DÜZELTME + YENİDEN RENDER (12 Ağu, ölçüldü)

> **Durum: yerel yeşil, `origin/arastirma-motoru`'na push edildi. Deploy YOK.**
> **Bayraklar varsayılan KAPALI. Maliyet $0.00 — ağ/ücretli API yok.**
> Yeni: `webapp/testler/smoke_kalite_pass_i15.py`,
> `outputs/sample/kalite_pass_i15_rapor.json`.
> Değişen: `webapp/editor/plan.py`, `webapp/editor/kalite_kapisi.py`,
> `webapp/editor/qa_son.py`,
> `app/render-studio/src/editorv2/Grafikler.tsx`,
> `webapp/testler/test_faz_i.py`, `outputs/sample/README.md` (+ bu handoff).
> **Dokunulmadı:** `pipeline.py`, `server.py`, tüm arayüz, 22 alanlık generate
> sözleşmesi, `deploy.sh`, lisans duvarı, SSRF, kare kapısı, iş bütçesi.

### I-14 ölçtü, I-15 düzeltti

I-14 kapıları kurmuştu ve I-13'ün 10 sn çıktısı açık kapıda **FAIL(4)**
veriyordu. Bu atom kusurları **gerçekten giderdi** ve aynı Apollo
tarih/belgesel fixture'ıyla **yeniden render** aldı.

### Ölçülen ÖNCE / SONRA

| Ölçüm | I-13 (10 sn) | **I-15 (12.821 sn)** |
|---|---|---|
| **Kapı açıkken** | **FAIL(4)** · render engellendi | **on-render WARN(fail=0) · post-render PASS** |
| Başlık metni | `20 JULY` → `20 JU` | **`THE EAGLE HAS LANDED`** |
| Başlık taşması | **272.5 px** | **0.0 px** |
| Uygulanan punto | 42 (küçültme tabanı vuruldu) | **60 — tam punto, küçültme yok** |
| Sahne süreleri | 3.2 · 3.2 · 3.2 | **1.637 · 4.051 · 3.224 · 3.825** |
| Süre yayılımı | **0.0 sn** | **2.414 sn** |
| Süre kaynağı | eşit bölme `(hedef−0.4)/n` | **edge-tts `SentenceBoundary`** |
| Ölü final | **0.903 sn** | **0.0 sn** |
| Ambiyans farkı | 57.12 dB (duyulmaz) | **23.07 dB — duyulabilir, bastırmıyor** |
| Miks LUFS / TP | −16.56 / −4.47 | **−14.87 / −4.0** (hedef −14) |
| Kesme sayısı | — | **3** (1.633 · 5.7 · 8.933) |
| Kare | 3 | **9**, hepsi görsel incelendi |

### Dört gerçek düzeltme

**1. Başlık — iki katmanlı kök neden kapatıldı.**
`plan.py`'nin sabit `b.metin[:42]` dilimi kaldırıldı; `chapter-title` artık
aynı dosyadaki `_kart_basligi()` + `kart_basligi_siniri()` ikilisini
kullanıyor (I-12 bu ikiliyi yazmış ama yalnızca veri-kartı yoluna bağlamıştı).
Sınır artık **gerçek render genişliğinden** hesaplanıyor ve `kucultme_tabani=1.0`
ile **tam puntoda** sığacak şekilde veriliyor — render tarafının %30 küçültme
güvencesi bir *geri düşüş ağı* olarak kalıyor, normal çalışma şartı olmuyor.
Ayrıca `Grafikler.tsx`'in kendi sığdırma hesabı `letterSpacing`'i saymaya
başladı. **Plan ile render artık tek aritmetiği paylaşıyor:** `plan.py` em/bant
sabitlerini `kalite_kapisi`'ndan alıyor.

**2. Süreler — vekil değil ölçüm.**
edge-tts 7.2.8 `SentenceBoundary` olayları veriyor (WordBoundary değil).
Sahne *i*, cümle *i*'nin başından cümle *i+1*'in başına kadar sürüyor. I-14'te
kullanılan "kelime sayısı" yalnızca bir vekildi; bu motorun kendi sentez zaman
çizelgesi. Test bunu **yeniden hesaplayarak** doğruluyor.

**3. Ölü final — kaynağında kesildi.**
Anlatım master'ı `anlatım_bitişi + 0.35 sn` noktasından kesiliyor.
⚠ **Baş sessizliği kırpılmıyor** — kırpmak `SentenceBoundary` ofsetlerini
kaydırır ve zamanlama ölçümünü yalan yapardı.

**4. Ambiyans — asıl kusur ducking değil, iki ayrı şeydi.**
Kaynak −48.68 LUFS'tan −26 LUFS'a normalize edildi **ve** `anlatim_araliklari`
props'a geçirildi. İkincisi kritikti: `Ses.tsx` bu alan verilmeyince **tüm
videoyu anlatım sayıp** ambiyansı baştan sona kısıyordu. Artık ducking yalnızca
gerçek konuşma aralıklarında uygulanıyor, cümle aralarında ambiyans geri geliyor.
Kapı da **çift taraflı** hale getirildi: `duyulabilir` (≤30 dB) **ve**
`bastiriyor` (<12 dB) — yeni kod `POST-AMBANS-BASKIN`.

### Render sırasında kapının YAKALADIĞI iki gerçek kusur

Bunlar tahmin değil, kapı FAIL verdiği için bulundu ve **eşik gevşetilmeden**
çözüldü:

1. **Beat bölünmesi → aynı görsel arka arkaya.** İlk deneme f001 ile açılıyordu
   (4.438 sn). Beat motoru `hook`/`açılış` için hedefi bilgi yoğunluğuna göre
   ~2.0 sn'ye çekiyor ve bölünme eşiği hedefin 1.5 katı (~3.06 sn). Sahne iki
   beat'e bölündü, ikisi sahnenin tek adayını paylaştı, `KALITE-MEDYA-TEKRAR`
   **FAIL** verdi. Çözüm: açılış cümlesi gerçekten kısaltıldı
   (`"The Eagle has landed."`, 1.637 sn) — hook'un zaten olması gereken şey.
2. **Sağlayıcı kotası → medyasız son sahne.** 5 sahnelik ilk kurguda `gramer`
   bir sağlayıcıdan en fazla 4 çekim alıyor ve fixture havuzunun tamamı
   `wikimedia`. Beşinci sahne fallback karta düştü: görüntüsüz koyu zemin,
   **3.5 sn donmuş kare**, `"ARMSTRONG TOOK"` gibi yarım bir başlık (kareyle
   görüldü). Kotayı yükseltmek yerine sahne sayısı 4'e indirildi — o kota
   gerçek bir çeşitlilik güvencesi.

### MEDYA ÇEŞİTLİLİĞİ — dürüst rapor, eşik oynaması YOK

Benzerlik eşiği **0.86**, I-14'ten **değişmedi** (test kilitliyor).

- Seçilen 4 varlığın ölçülen en yüksek ikili benzerliği **0.6094** — eşiğin
  altında, kapı **haklı olarak sessiz**.
- Uygun 5 görselin **tüm 4'lü alt kümeleri** ölçüldü: hepsinin en yüksek ikili
  benzerliği ≥ 0.6094. Yani **mevcut seçim zaten havuzun en çeşitli 4'lüsü**;
  daha iyisi yok. Bu bir fixture sınırıdır, seçim hatası değil.
- Yapılabilen tek iyileştirme uygulandı: **yalnızca sıra** değiştirilerek en
  benzer çiftin komşu düşmesi engellendi → komşu benzerliği **0.6094 → 0.5312**.
  Küme ve eşikler aynı kaldı.
- ⚠ **Açık kalan ölçüm boşluğu:** iki gri regolit ayak izi karesi algısal olarak
  aynı özne ailesinden; dHash 0.6094 bunu yakalamıyor. §31'in "semantik zayıf"
  gözlemi **hâlâ ölçülemiyor** — I-14'te açık bırakılmıştı, I-15'te de açık.

### Görsel doğrulama — 9 kare, hepsi incelendi

`0.82 · 1.2 · 1.92 · 3.66 · 5.13 · 7.3 · 8.33 · 10.82 · 11.54` sn.
Başlık bandı (0.82/1.2 sn): **"THE EAGLE HAS LANDED" tam görünüyor**, kırpma
yok, bant kare içinde. Sahne akışı: LM → geniş ayak izi → altın folyo →
yakın ayak izi. Boş/düz kare yok (hepsi > 100 KB), donmuş kare yok.

### Ölçülen test sonucu (12 Ağu) — İKİ ORTAM AYRI

| Paket | A | B | C | D | E | F | G | H | I | Toplam |
|---|---|---|---|---|---|---|---|---|---|---|
| **Zengin venv** | 125 | 200 | 148 | 95 | 127 | 244 | 218 | **257** | **1125** | **2539** |
| **Sistem Python** | 125 | 200 | 148 | 95 | 127 | 244 | 218 | **203** | **1125** | **2485** |

0 hata. Faz I 1060 → **1125** (+65). Faz C **148/0** — editor paketinde
gerileme yok. `deploy.sh` tanımsız-isim taraması → **0 bulgu**.

⚠ **İki I-14 kontrolü silinmedi, ÇEVRİLDİ.** O ikisi TSX'in `letterSpacing`'i
saymadığı *bilinen kusuru* kilitliyordu; I-15 kusuru kapattığı için kontrol
artık düzeltilmiş davranışı kilitliyor. Kuralın niyeti aynı: plan ile render
aynı genişlik aritmetiğini kullanmalı.

### Bu atomda düzelttiğim kendi test hatam

İki yeni kontrol ham dize taramasıyla yazılmıştı ve **kod doğruyken kırmızı
yanıyordu**: `"b.metin[:42]"` deseni benim yazdığım *açıklama satırına*,
`lavfi|testsrc` deseni smoke betiğinin *kendi docstring'ine* takılıyordu.
Aynı tuzak I-9'da da yaşanmıştı. `tokenize` ile yorum ve dizeleri ayıklayan
`_kod_yalniz()` yardımcısı eklendi; artık yalnızca **çalışan kod** taranıyor.

### BİLİNEN SINIRLAR (dürüstçe)

1. **Altyazı ve kaynak künyesi hâlâ YOK** — `kapsam_ozeti()["kapsam_disi"]`
   bunu açıkça sayıyor. Sonraki atom.
2. **1080p ölçülmedi** — çıktı 1280×720. §31'in 7. kusuru **açık**.
3. **Medya çeşitliliğinin algısal boyutu ölçülemiyor** (yukarıda).
4. **edge-tts prosodisi çağrıdan çağrıya değişiyor** — süreler bit-bit tekrar
   üretilebilir değil. Rapor son koşunun ölçümüdür; testler süre *değerlerini*
   değil *özelliklerini* (benzersizlik, yayılım, sınırlardan türeme) kilitler.
5. **Ambiyans 30/12 dB eşikleri hâlâ beyan edilmiş tasarım kararı**, dinleme
   testi değil. Girdiler gerçek ölçüm.
6. **İki WARN duruyor:** `PACING-KISA-ORAN` (%75, referans %32) ve
   `SAGLAYICI-TEKEL` (%100 wikimedia). İkisi de **fixture sınırı** — havuzda
   tek sağlayıcı var ve klipler kısa. Gerçek çok sağlayıcılı bir işte düşmesi
   *beklenir* ama **ölçülmedi**.
7. **Canlı `/api/generate` hattı bu kapıyı hâlâ görmüyor** (§32 sınır 8 aynen).
8. **Web'den medya bulma hiç koşulmadı** — sağlayıcıya tek istek atılmadı.

### SONRAKİ ATOM (I-16 — bu atomda YAPILMADI)

Altyazı dizisinin TTS zamanlamasından üretilip props'a bağlanması (artık
`SentenceBoundary` elimizde), `source-label` künyesinin ekrana çıkması ve
1080p render ölçümü.

---

## 34. FAZ I-16 — ALTYAZI + GÖRÜNÜR KAYNAK KÜNYESİ + 1080p (12 Ağu, ölçüldü)

> **Durum: yerel yeşil, `origin/arastirma-motoru`'na push edildi. Deploy YOK.**
> **Bayraklar varsayılan KAPALI. Maliyet $0.00 — ağ/ücretli API yok.**
> Yeni: `webapp/testler/smoke_altyazi_kunye_1080p_i16.py`,
> `outputs/sample/altyazi_1080p_i16_rapor.json`.
> Değişen: `webapp/editor/kalite_kapisi.py`, `webapp/editor/tipografi.py`,
> `webapp/editor/plan.py`, `webapp/editor/qa_on.py`,
> `webapp/editor/adapter.py`, `webapp/edit_kopru.py`,
> `app/render-studio/src/editorv2/Grafikler.tsx`,
> `app/render-studio/src/editorv2/EditorV2.tsx`,
> `webapp/testler/test_faz_i.py`, `outputs/sample/README.md` (+ bu handoff).
> **Dokunulmadı:** `pipeline.py`, `server.py`, tüm arayüz, 22 alanlık generate
> sözleşmesi, `deploy.sh`, lisans duvarı, SSRF, kare kapısı, iş bütçesi.

### Kapatılan üç açık

§33 sınır 1–2 ve §31 kusur 6–7: altyazı yoktu, kaynak künyesi ekranda
görünmüyordu, çıktı yalnızca 720p'ydi. Üçü de kapandı.

| Ölçüm | I-15 | **I-16** |
|---|---|---|
| Çözünürlük | 1280×720 | **1920×1080** |
| Süre | 12.821 sn | **17.579 sn** |
| Altyazı | **yok** | **5 küp**, zaman kodlu, ≤2 satır / ≤42 karakter |
| Kaynak künyesi | **üretilmiyordu** | **NASA / PUBLIC-DOMAIN**, sahneye bağlı |
| Güvenli alan ihlali | ölçülmüyordu | **0** (1080p'de ölçüldü) |
| Yazı çakışması | ölçülmüyordu | **0** (başlık + künye + altyazı aynı anda) |
| Miks LUFS / TP | −14.87 / −4.0 | **−14.32 / −2.08** |
| Sahne kesimi | 3 | **4** (0.033 · 2.967 · 8.167 · 12.867) |
| Kare | 9 | **10**, hepsi görsel incelendi |
| PRE / POST QA | WARN(0) / PASS | **WARN(fail=0) / PASS** |

### Bulunan ve kapatılan İKİ GERÇEK KUSUR

**1. Altyazı: "props'ta var, videoda yok".**
`altyazi` alanı `sozlesme.ts:62`'de tanımlıydı ve `adapter.py:127` onu
props'a kadar **taşıyordu** — ama hiçbir Remotion bileşeni onu **çizmiyordu**.
Bu, `Ses.tsx`'te Faz D'de kapatılan kusurun (ses taşınıyordu, `<Audio>` yoktu)
tipografi tarafındaki eşi. Yeni `Altyazi` bileşeni eklendi ve `SahneKatmani`
içine, geçiş katmanının **altına** mount edildi (geçiş karartması altyazıyı da
etkilesin diye).

**2. Kaynak künyesi güvenli alanın DIŞINDAYDI.**
`KaynakEtiketi` `bottom: 22` **sabitiyle** çiziliyordu — yani Python'un
hesapladığı `y_orani`'yi **hiç okumuyordu**. 1080p'de yayın güvenli kenarı
64 px iken künye 22 px'te duruyordu. Üstelik Python'un çakışma aritmetiği
gerçekle örtüşmüyordu: plan "0.895'te" sanıyor, render 22 px'e çiziyordu.
Artık spec'ten `y_orani` okunuyor ve güvenli kenar **zorlanıyor**.

### Altyazı zamanlaması — dürüst etiket

Cümle sınırları **ölçüm**: edge-tts `SentenceBoundary`. Ama bir cümle iki
küpe sığmıyorsa parça zamanlaması **ölçüm değil, karakter ağırlıklı orantılı
dağıtımdır** — edge-tts 7.2.8 kelime sınırı vermiyor (ölçüldü). Her küp
`zamanlama: "olculdu" | "orantili"` alanı taşır; rapor ikisini ayrı sayar.

Okunabilirlik kuralları ölçülebilir: ≤42 karakter/satır, ≤2 satır,
≥1.2 sn küp süresi, ≤20 karakter/sn okuma hızı.

### Altyazı bandı rezerve edildi

`tipografi.ALTYAZI_BANT = (0.81, 0.94)` — alt sınır **hesaplandı**:
`0.94 × 1080 = 1015.2 px ≤ 1016` (güvenli tavan). Bu bant hiçbir yazı
katmanına açılmaz: `cakisma_coz()` yeni `yasak_bant` parametresiyle oraya
**kaydırmıyor**. Aksi halde çözücü `0.88`'e kaydırıp katmanı altyazının
üstüne bindirir, çözdüğü çakışmanın yerine yenisini koyardı. Altyazı varken
künye `0.755`'e taşınıyor (`0.755 + 0.045 = 0.80` → bandın hemen üstü).

### Render sırasında bulunan ÜÇ hata (hepsi kendi hatam)

1. **`fontSize: 0` — altyazı görünmez çizildi.** `sayi(v, varsayilan)`
   yalnızca **sayı olmayan** girdide varsayılana düşer; ben `?? 0` yazınca
   `sayi(0, 38)` → **0** döndü. İlk 1080p koşusunda altyazı hiç görünmedi,
   kareyle yakalandı. Tuzak koda yazıldı, test kilitliyor.
2. **JSX yorumu attribute listesinin içinde** → esbuild render'ı kırdı.
3. **Sarkan edat altyazıda.** "…on the Moon" / "**on**" — ikinci satır tek
   başına bir edat kaldı (kareyle görüldü). `plan._SARKAN`'ın altyazı
   karşılığı (`_SARKAN_KELIME` + `_sarkani_tasi`) eklendi; ayrıca açgözlü
   doldurma yerine **dengeli bölme** yapılıyor (açgözlü bölme 0.659 sn'lik
   okunamaz bir artık küp bırakıyordu).

### Kontrollü tek remaster

Miks −15.31 LUFS çıktı (hedef −14). §13'te (H6) onaylanmış yol uygulandı:
**yalnız ses sorununda, bir kez, ücretsiz + deterministik** `loudnorm`;
video akışı **kopyalandı**, yeniden render edilmedi. Sonuç −14.32 LUFS /
TP −2.08. Rapor önce/sonra değerlerini birlikte taşıyor.

### ⛔ HAREKETLI VIDEO B-ROLL — DÜRÜSTÇE BLOKE

Güvenli fixture havuzunda **gerçek video adayı yok**. Depoda 4 `.mp4` var ama
hepsi bu projenin **kendi render çıktıları** (`cikti/faz_e/pilot_master.mp4`,
`pilot_ham.mp4`, `cikti/faz_d/*.mp4`). Onları "arşiv B-roll" diye kullanmak
döngüsel ve yanıltıcı olurdu: kendi çıktımızı yeniden render edip "gerçek
çekim" demek. Betik bunu tarayıp `durum: "BLOKE"` yazıyor ve sebebi raporda
duruyor. **Sahte hareket üretilmedi.**

### Görsel doğrulama — 10 kare, hepsi incelendi

`1.2 · 1.76 · 3.87 · 5.57 · 6.16 · 8.45 · 10.52 · 12.67 · 14.96 · 16.72` sn.
1.2/1.76 sn karelerinde **üçü birden** ekranda: bölüm başlığı
("TRANQUILITY BASE HERE", tam, kırpma yok), kaynak künyesi
("NASA / PUBLIC-DOMAIN", sağ üstte güvenli alanda) ve altyazı (alt bantta,
iki satır). Çakışma yok. Sarkan edat düzeltmesi 5.57 sn karesinde doğrulandı.

### Ölçülen test sonucu (12 Ağu) — İKİ ORTAM AYRI

| Paket | A | B | C | D | E | F | G | H | I | Toplam |
|---|---|---|---|---|---|---|---|---|---|---|
| **Zengin venv** | 125 | 200 | 148 | 95 | 127 | 244 | 218 | **257** | **1197** | **2611** |
| **Sistem Python** | 125 | 200 | 148 | 95 | 127 | 244 | 218 | **203** | **1197** | **2557** |

0 hata. Faz I 1125 → **1197** (+72). Faz C **148/0** — editor paketinde
gerileme yok. `deploy.sh` tanımsız-isim taraması → **0 bulgu**.

⚠ **İki I-14 kontrolü silinmedi, GÜNCELLENDİ:** `kapsam_ozeti` kontrolü
5 ölçüm / 4 kapsam-dışı kilitliyordu; I-16 altyazı+künye+1080p'yi kapsama
aldığı için kural aynı niyetle (kapsam sayılabilir olmalı, kapsam dışı
açıkça yazılmalı) yeniden yazıldı.

### BİLİNEN SINIRLAR (dürüstçe)

1. **Hareketli video B-roll YOK** (yukarıda) — havuz sınırı, gizlenmiyor.
2. **Altyazı kelime düzeyinde senkron değil.** Cümle sınırı ölçüm, cümle içi
   dağıtım orantılı. Kelime düzeyi için farklı bir TTS/hizalayıcı gerekir.
3. **Aynı regolit/ayak izi görselleri hâlâ uzun kalıyor.** Ölçülen en yüksek
   ikili benzerlik 0.6094, eşik 0.86 — kapı haklı olarak sessiz. §32/§33'te
   belgelenen **algısal benzerlik ölçüm boşluğu I-16'da da açık**; havuzun en
   çeşitli 4'lüsü zaten seçili ve eşik düşürülmedi.
4. **`SAGLAYICI-TEKEL` WARN duruyor** (%100 wikimedia) — fixture'da tek
   sağlayıcı var. Gerçek çok sağlayıcılı işte düşmesi *beklenir*, ölçülmedi.
5. **Altyazı stili tek tip** (`bant-orta`). Karaoke/kelime vurgulu stiller yok.
6. **`altyaziStil` props alanı hâlâ okunmuyor** — bileşen tek stil çiziyor;
   alan taşınıyor ama davranışı değiştirmiyor.
7. **Ambiyans 30/12 dB eşikleri beyan edilmiş tasarım kararı**, dinleme testi
   değil (§33 sınır 5 aynen geçerli).
8. **Canlı `/api/generate` hattı bu kapıyı hâlâ görmüyor** (§32 sınır 8).
9. **edge-tts prosodisi tekrar üretilebilir değil**; testler süre değerlerini
   değil özelliklerini kilitler.

### SONRAKİ ATOM (I-17 — bu atomda YAPILMADI)

Gerçek hareketli B-roll'un güvenli bir havuzdan (Wikimedia video, Openverse)
**gerçekten indirilmesi** — bu, web medya hattının (`medya_kopru`, bayrak
hâlâ kapalı) ilk gerçek koşusu olur. Yanında: algısal benzerlik ölçümü için
ikinci bir sinyal ve `altyaziStil` alanının gerçekten uygulanması.

---

## 35. FAZ I-17 — BELGESEL MOTION GRAMMAR + OPTİK DURAĞANLIK KAPISI (12 Ağu)

> **Durum: yerel yeşil, `origin/arastirma-motoru`'na push edildi. Deploy YOK.**
> **Bayraklar varsayılan KAPALI. Maliyet $0.00.**
> Yeni: `webapp/testler/smoke_motion_grammar_i17.py`,
> `outputs/sample/motion_i17_rapor.json`.
> Değişen: `webapp/editor/kalite_kapisi.py`, `webapp/editor/gramer.py`,
> `webapp/editor/motion.py`, `webapp/editor/qa_on.py`,
> `webapp/editor/qa_son.py`, `webapp/testler/test_faz_i.py`,
> `outputs/sample/README.md` (+ bu handoff).
> **Dokunulmadı:** `pipeline.py`, `server.py`, tüm arayüz, 22 alanlık generate
> sözleşmesi, `deploy.sh`, TSX render katmanı, lisans duvarı, SSRF.

### ÖNCE durumu — I-16 çıktısında ölçüldü

Ölçüm: 4 fps / 64×36 gri, ardışık ortalama mutlak fark
(`kalite_kapisi.optik_ornek_komutu` — tek ffmpeg geçişi).

| Sahne | Süre | `hareket` | Optik ort. |
|---|---|---|---|
| b001 | 2.96 s | push-in | 3.551 |
| **b002** | **5.21 s** | **static** | **0.914** ← durağanlık kusuru |
| b003 | 4.69 s | push-in | 5.102 |
| b004 | 4.68 s | pull-out | 7.030 |

Geçiş: **4/4 hard-cut**. Hareket: **push-in iki kez** (b001, b003) — komşu
olmadıkları için mevcut `ARDIL-AYNI-HAREKET` kuralı görmüyordu.

### SONRA — aynı fixture, aynı süre, ölçülen sonuç

| Ölçüm | I-16 | **I-17** |
|---|---|---|
| b001 | push-in 3.551 | push-in **3.517** |
| b002 | **static 0.914** | **pull-out 5.366** |
| b003 | push-in 5.102 | **slow-drift 4.629** |
| b004 | pull-out 7.030 | **pan-left 30.426** |
| Durağanlık ihlali | **1 (FAIL)** | **0** |
| Geçiş ailesi | 1 (hard-cut ×4) | **2** (hard-cut ×3 + karartma ×1) |
| Benzersiz hareket | 3 | **4**, ardışık ve pencere tekrarı **0** |
| Açılış / kapanış | push-in / pull-out | push-in / pan-left (**ayrı**) |
| İzleyici kalite puanı | — | **100/100** |
| PRE / POST QA | WARN(0) / PASS | **WARN(fail=0) / PASS** |

### Dört motor değişikliği

1. **Uzun çekimde `static` yasak.** `gramer.DURAGAN_TAVAN_SN = 1.5`
   (profilin `shot_min_sn`i). Bir fotoğrafı bir çekim boyu hareketsiz
   tutmak belgesel dilinde karar değil, ihmal.
2. **Ken Burns yön havuzu genişletildi.** `CEKIM_HAREKET["medium"]` üç
   elemanlıydı; `static` elenip önceki hareket de yasaklanınca **geriye tek
   aday** kalıyor ve `push-in` tekrar ediyordu. Havuzlar `kamera_spec`in
   **gerçekten desteklediği** yönlerle 5–6 elemana çıkarıldı.
   ⚠ `soft-zoom` kasıtlı olarak yok: `kamera_spec` onu spec'e `push-in`
   adıyla yazıyor, plan adı ile render adı ayrışır ve ölçüm yalan söylerdi.
3. **Pencere tekrarı.** `HAREKET_PENCERESI = 3` — ardışık olmayan tekrar da
   engelleniyor.
4. **İşleve bağlı ikinci geçiş ailesi.** `sec_gecis`e "kapanış beat'ine
   giriş → `karartma`" kuralı eklendi. Faz C'nin kilitlediği
   `aciklama→aciklama` (hard-cut) ve `j_cut` davranışları **korundu**.
   hard-cut oranı %75 — ölçülen %79.9 referans bandının içinde kaldı.

⚠ **Açılış/kapanış ritmi çeşitliliğe TABİ.** İlk sürümde `sonuc → pull-out`
tercihi pencere kontrolünden **önce** dönüyordu ve `pull-out` hem b002'de
hem b004'te çıkıyordu (ölçüldü). Ritim bir tercihtir, tekrar üretme pahasına
uygulanmaz; açılış ile kapanışın **farklı** olması zaten korunuyor.

### ⚠ BULUNAN GİZLİ RENDER HATASI — kenarda siyah bant

Pan hareketleri kullanılmaya başlanınca **16.72 sn karesinde sağ kenarda
siyah bant** göründü. Kök neden ölçüldü:

`Kamera.tsx` şu transformu uyguluyor: `transform: scale(S) translate(x%)`.
CSS'te transform **sağdan sola** uygulanır ve yüzde kayma **elemanın kendi
genişliğine** göredir — yani ekrandaki gerçek yer değiştirme **S × x**.
Siyah kenar olmaması için `S·pay ≤ (S−1)/2`, yani `pay ≤ (S−1)/(2S)`.

Eski formül `max(0.04, (olcek−1)/2 + 0.04)` hem S'yi (pan zoom'u dahil toplam
ölçeği) görmüyor hem de taşma payına **ekliyordu**. Ölçülen vaka:
`pan-left` + `punch-1.6` → S=1.696, pay=0.34, yer değiştirme **0.577** vs
taşma payı **0.348**.

**Bu gizli bir hataydı:** düzeltilmiş formülle 8 kadraj/hareket
kombinasyonunun 8'i güvenli; eski formülle **5'i taşıyordu** — en yaygın
`pan-left/tam` dahil. Pan hareketleri seçilmediği için bugüne kadar
görünmemişti.

### ⚠ DÜRÜST SINIR — optik büyüklük siyah bandı AYIRT EDEMEZ

Aşırı hareket eşiği eklendi ama ölçüm gösterdi ki bu **kenar dedektörü
değil**: siyah bantlı kare **38.911**, düzeltilmiş temiz hızlı pan
**34.525** ölçtü — aralarında yalnızca %12 var. Bu yüzden:

- `OPTIK_ASIRI_ESIGI` yalnızca "kamera fazla hızlı" sinyali olarak, ölçülen
  meşru en hızlı panın üstüne (**45.0**) konuldu.
- Kenar taşması için **ayrı ve doğru enstrüman** yazıldı:
  `kenar_siyahligi_olcusu` (kenar şeridi parlaklığı; tamamen koyu görüntüde
  yanlış pozitif üretmiyor — testli). `POST-KENAR-SIYAH` kodu FAIL.

Ayrıca pan aralığı **%100 → %70**'e çekildi (`slow-drift` zaten %30
kullanıyordu); ölçülen etki 34.5 → **30.4**.

### Eşikler — gerçek ölçümden türetildi

| Eşik | Değer | Türetme |
|---|---|---|
| Durağan | **2.0** | ölçülen 0.914 (durağan) ile 3.551 (en zayıf hareketli) arasında, durağan tarafa yakın |
| Durağan WARN | **1.5 s** | profilin `shot_min_sn`i |
| Durağan FAIL | **3.0 s** | iki katı |
| Aşırı hareket | **45.0** | ölçülen meşru en hızlı panın (30–35) üstü |
| Kenar siyah | **16/255** | gerçek görüntü kenarı nadiren altına düşer; taşma bölgesi tam siyah |

⚠ Eşikler **bu örneklemeyle** (4 fps / 64×36) anlamlıdır; örnekleme
değişirse yeniden kalibre edilmeli. Kodda yazılı.

### İzleyici kalite puanı — şeffaf, iddiasız

6 bileşenin ağırlıklı birleşimi (optik 25 · motion çeşitlilik 20 · ritim 15 ·
tipografi 15 · medya 15 · ses 10). Her bileşen **ham gerekçesiyle** raporlanır;
ölçülemeyen bileşen puana **katılmaz** (sahte tam puan yok).
⚠ **İzleyici araştırması DEĞİLDİR** — zaten ölçülen kusur bileşenlerinin
birleşimidir; "izleyiciler bunu daha çok beğeniyor" iddiası taşımaz.

### Ölçülen test sonucu (12 Ağu) — İKİ ORTAM AYRI

| Paket | A | B | C | D | E | F | G | H | I | Toplam |
|---|---|---|---|---|---|---|---|---|---|---|
| **Zengin venv** | 125 | 200 | 148 | 95 | 127 | 244 | 218 | **257** | **1269** | **2683** |
| **Sistem Python** | 125 | 200 | 148 | 95 | 127 | 244 | 218 | **203** | **1269** | **2629** |

0 hata. Faz I 1197 → **1269** (+72). Faz C **148/0** — Faz C'nin geçiş
kilitleri korundu. `deploy.sh` tanımsız-isim taraması → **0 bulgu**.

⚠ Bir I-16 kontrolü silinmedi, **güncellendi**: `kapsam_ozeti` ölçüm sayısını
`== 9` kilitliyordu; I-17 üç ölçüm ekledi, kural `>= 9` olarak yeniden
yazıldı (niyet aynı: I-16 ölçümleri kapsamda kalmalı).

### BİLİNEN SINIRLAR (dürüstçe)

1. **Hareketli video B-roll hâlâ BLOKE** — güvenli havuzda gerçek video yok;
   depodaki `.mp4`'ler bu projenin kendi render çıktıları. Sahte B-roll
   kullanılmadı.
2. **Hareket enerjisi dengesiz.** Ölçülen: 3.5 / 5.4 / 4.6 / **30.4**.
   Kapı geçiyor ama dağılım düz değil; `pan-left` + `punch-1.6` diğerlerinden
   ~6 kat enerjik. Dengeleme yapılmadı, açık bırakıldı.
3. **Parallax UYGULANMADI.** `parallax_spec` yalnızca `archive` çekim türünde
   tetikleniyor; bu fixture'ın çekimleri `close-detail`/`medium`/
   `establishing`. Gerçek katman görselleri de yok — `kapsam_ozeti`
   kapsam dışı listesinde yazılı.
4. **Geçiş çeşitliliği sahne sayısıyla sınırlı.** 4 sahnede üçüncü bir aile
   eklemek hard-cut oranını %50'ye düşürür ve ölçülen %79.9 referansını
   ihlal ederdi. Daha fazla aile için daha çok sahne gerekir; sağlayıcı
   kotası (4) buna izin vermiyor.
5. **Altyazı/sahne metni hâlâ İngilizce fixture** — Türkçe içerikle
   ölçülmedi.
6. **Kaynak künyesi her sahnede aynı genel etiket** (`NASA / PUBLIC-DOMAIN`);
   varlık bazlı ayrı künye yok.
7. **Algısal medya benzerliği hâlâ ölçülemiyor** (§32–§34 aynen geçerli).
8. **Kenar dedektörü gerçek siyah-bantlı çıktıyla değil**, sentetik kareyle
   ve aritmetik ispatla doğrulandı; gerçek vaka bir kez görüldü (kareyle) ve
   kaynağında düzeltildi.
9. **Canlı `/api/generate` hattı bu kapıları hâlâ görmüyor.**

### SONRAKİ ATOM (I-18 — bu atomda YAPILMADI)

Hareket enerjisi dengelemesi (sahneler arası optik varyansı hedef banda
çekmek), `archive` çekim türü için gerçek parallax, ve Türkçe içerikle
uçtan uca bir ölçüm koşusu.

---

## 36. FAZ I-18 — İKİNCİ KONSEPT (DOĞA/SEYAHAT): MOTOR KANITLANDI, MEDYA BLOKE

> **Durum: yerel yeşil, `origin/arastirma-motoru`'na push edildi. Deploy YOK.**
> **Maliyet $0.00. Bayraklar varsayılan KAPALI.**
> Yeni: `webapp/medya/commons.py`,
> `webapp/testler/smoke_konsept2_doga_i18.py`,
> `outputs/sample/doga_i18_bloke_rapor.json`.
> Değişen: `webapp/taksonomi.py`, `webapp/testler/test_faz_i.py` (+ bu handoff).
> **Dokunulmadı:** `pipeline.py`, `server.py`, tüm arayüz, 22 alanlık generate
> sözleşmesi, `deploy.sh`, `medya/lisans.py`, `medya/guvenlik.py`,
> `medya/indirme.py`, `kalite_kapisi.py`, TSX render katmanı.

### ⚠ BU ATOMUN DÜRÜST SONUCU — İKİ PARÇA

| Parça | Sonuç |
|---|---|
| **Otomatik konsept + stil seçimi** | ✅ **TAM KANITLANDI** |
| **Medya baytı edinimi** | ⛔ **BLOKE** (ortam kaynaklı, ölçüldü) |
| Doğa pilotu render/MP4 | ❌ **ÜRETİLMEDİ** — sahte medyayla render yapılmadı |

I-13'ten I-17'ye kadar her pilot aynı Apollo fixture'ıyla koştu. İkinci
konsept için havuzda **tek bir doğa görseli yoktu** (ölçüldü:
`cikti/faz_e/medya/` 12 varlığın 12'si Apollo/Ay; `cikti/faz_d/zemin/`
ise **sentetik gradyan**, fotoğraf değil). Bu yüzden medya **gerçekten
edinilmeye çalışıldı**.

### ✅ KANITLANAN — kullanıcı yalnız metin verdi

```
metin  : "İzlanda'nın güney kıyısındaki buzul lagünleri, siyah kum
          plajları ve şelaleleri: dört duraklı bir doğa yolculuğu"
konsept: aile=seyahat  durum=kesin  guven=0.91
gerekce: seyahat.doga_manzara: puan 4.0, kanit 4 = 4 anahtar
STIL   : kimlik=seyahat-4k  surum=1.0.0  kaynak=auto
edit   : atlas-journey
```

Tür/stil **elle verilmedi**. Seçilen edit profili `atlas-journey` — Apollo
pilotlarının `premium-modern`inden **gerçekten farklı** bir profil.

### ⚠ ÖLÇÜLEN TAKSONOMİ BOŞLUĞU — atomun başında iddia KARŞILIKSIZDI

İlk ölçüm, kullanıcının varsaydığı davranışın **çalışmadığını** gösterdi:

| Metin | ÖNCE | **SONRA** |
|---|---|---|
| İzlanda buzul lagünleri / siyah kum plajları | **belirsiz** (0 işaret) | **seyahat / kesin / 0.91** |
| Norveç fiyortları / şelaleler / kayalıklar | **belirsiz** (1 işaret) | **seyahat / kesin** |
| Patagonya granit kuleler / buzul gölleri | **belirsiz** (0 işaret) | **seyahat / kesin** |
| Kapadokya peribacaları / vadiler / mağaralar | **belirsiz** (1 işaret) | **seyahat / kesin** |
| Stil sonucu | `belgesel-sinematik` (**varsayılan**) | `seyahat-4k` (**auto**) |

**Kök neden:** `seyahat.doga_manzara` dalı yalnızca 19 kelime taşıyordu ve
seyahat ailesi pratikte **hizmet sözlüğüyle** ("gezi", "rehber", "tur")
tetikleniyordu. Eksik olan **manzara / yer şekli** sözlüğüydü.

**Çözüm:** §16'nın tasarım sözü uygulandı — *"yeni konsept eklemek = AGAC'a
bir satır, motor kodu değişmez"*. Yalnızca sözlük büyütüldü:
**690 → 783 anahtar** (+93). Aile 7, dal 33 **aynı kaldı**; eski 19 kelime
**silinmedi**. 19 küratörlü konsept testinin tamamı geçiyor.

⚠ Kısa Türkçe kökler (`vadi`=4, `dağ`=3) §16'nın ek toleransı kuralına
girmiyor; çekimli biçimler (`vadiler`, `dağları`, `gölleri`) **ayrıca**
yazıldı.

### ⛔ MEDYA EDİNİMİ — ne çalıştı, ne durdu

Yeni `webapp/medya/commons.py` yazıldı: **anahtarsız, ücretsiz** Wikimedia
Commons edinimi.

| Katman | Sonuç |
|---|---|
| Commons arama + metadata | ✅ çalıştı (sahne başına 6 aday) |
| Lisans kararı (`medya.lisans`) | ✅ çalıştı — CC-BY / CC-BY-SA doğrulandı |
| Provenance zorunluluğu | ✅ eser sahibi okunamayan aday **elenir** |
| 4K kaynak eşiği (≥3840 px) | ✅ 5000–7800 px adaylar bulundu |
| **Bayt indirme** | ⛔ **HTTP 429, `Retry-After: 600`** — 4/4 sahne |

**Sınıflandırma: `{"AG-HIZ-SINIRI": 4}`** — bu bir **lisans reddi değil**,
`upload.wikimedia.org`un bu ortamın çıkış IP'sine uyguladığı hız sınırı.
11 dakika beklenip yeniden denendi; **aynı** `Retry-After: 600` döndü, yani
geçici bir patlama sınırı değil. Openverse de denendi: arama çalışıyor ama
tam çözünürlük URL'leri **aynı** hosta işaret ediyor.

Kanıt izlenen dosyada: `outputs/sample/doga_i18_bloke_rapor.json`
(`sahte_medya_uretildi_mi: false`).

### NE YAPMADIM (ve neden)

- **Apollo görselleriyle doğa anlatımı render etmedim.** Bu, I-13'te
  kapatılan "Apollo görsel + Endurance metni" uyuşmazlığının aynısı olurdu.
- **`cikti/faz_d/zemin/*.jpg` kullanmadım.** Bunlar sentetik gradyan;
  "doğa fotoğrafı" diye sunmak yanıltıcı, ekranda da I-13'ün ölçtüğü
  "düz gri kare" kusuru olurdu.
- **Kendi render çıktılarımızı B-roll saymadım** (I-16/I-17 BLOKE'si aynen).
- **Upscale yapmadım.** 4K iddiası kaynağa bağlı; betik kaynaklar yetmezse
  dürüstçe 1080p'ye düşüyor (`dort_k_uygun` bayrağı).

### Hazır ama koşmamış olan

Betik **uçtan uca hazır**: Türkçe anlatım üretildi ve ölçüldü
(`tr-TR-AhmetNeural`, 4 cümle sınırı, 17.11 sn, **LRA 3.4** — İngilizce
seslerin 1.4–2.0'ından belirgin daha dinamik), altyazı/künye/motion/optik
kapıları I-17'den aynen devralındı. Medya baytı geldiği anda render, 9+ kare,
PRE/POST QA ve ölçüm zinciri çalışacak. **Bu atomda MP4 YOK.**

### `commons.py` sözleri (testli)

- Lisans kararını **kendi vermez** → `medya.lisans.lisans_karari`
- İndiriciyi **kendi yazmaz** → `medya.indirme.guvenli_indir` (SSRF duvarı)
- **Provenance zorunlu** — eser sahibi yoksa aday elenir
- **Konu adı gömülü değil** — Apollo/Iceland hiçbiri kodda geçmiyor
- **Anahtar/token yok** ($0.00)
- 429'da **sınırlı (3) ve tavanlı** bekleme; `Retry-After` varsa ona uyar

### Ölçülen test sonucu (12 Ağu) — İKİ ORTAM AYRI

| Paket | A | B | C | D | E | F | G | H | I | Toplam |
|---|---|---|---|---|---|---|---|---|---|---|
| **Zengin venv** | 125 | 200 | 148 | 95 | 127 | 244 | 218 | **257** | **1327** | **2741** |
| **Sistem Python** | 125 | 200 | 148 | 95 | 127 | 244 | 218 | **203** | **1327** | **2687** |

0 hata. Faz I 1269 → **1327** (+58). Faz I'de **1 BLOKE**: doğa pilotu render
raporu — **PASS sayılmadı**, sebebi ölçülmüş olarak yazılı.

### Bu atomda düzelttiğim kendi hatalarım

1. `commons.varsayilan_istek` imzasını `(url, zaman_asimi)` yazmıştım;
   güvenlik katmanı `requests` biçiminde `(yontem, url, timeout=,
   allow_redirects=, stream=)` çağırıyor → `TypeError`. Kapı doğru çalıştı,
   sebep görünür oldu.
2. Test yardımcısı `_kod_yalniz` token'ları **boşlukla** birleştiriyor;
   `lisans.lisans_karari(` kodda varken taramada `lisans . lisans_karari (`
   oluyor ve **kod doğruyken test kırmızı** yanıyordu. Boşluksuz karşılaştıran
   `_sikistir()` eklendi.

### BİLİNEN SINIRLAR (dürüstçe)

1. **Doğa pilotu MP4 YOK** — medya baytı edinilemedi (yukarıda).
2. **Renk tutarlılığı, 9 kare, PRE/POST QA, kesim/motion ölçümü bu konsept
   için KOŞULMADI** — medya olmadan koşulamaz. Kod hazır.
3. **4K hiç ölçülmedi.** Kaynak çözünürlüğü yeterliydi (5000–7800 px) ama
   render alınamadı.
4. **Taksonomi genişlemesi Türkçe/İngilizce sözlük tabanlı**; gerçek kullanıcı
   dağılımında isabet oranı hâlâ **ölçülmedi** (§16 sınır 3 aynen geçerli).
5. **Commons modülü tek sağlayıcı.** Openverse denendi ama tam çözünürlük
   aynı hosta gidiyor; ikinci bağımsız sağlayıcı yok.
6. **Hareketli video B-roll BLOKE** (I-16/I-17 aynen).
7. **Algısal medya benzerliği hâlâ ölçülemiyor** (§32–§35 aynen).

### SONRAKİ ATOM (I-19)

Ya (a) hız sınırı olmayan bir ortamdan/aynadan medya baytını edinip doğa
pilotunu **gerçekten** render etmek, ya da (b) depoya küçük, lisansı ve
provenance'ı kayıtlı bir **doğa fixture seti** eklemek. Motorun geri kalanı
hazır ve testli.

---

## 37. FAZ I-19 — EDİNİM DAYANIKLILIĞI: I-18'İN BLOKE'Sİ AÇILDI (12 Ağu)

> **Durum: yerel yeşil, `origin/arastirma-motoru`'na push edildi. Deploy YOK.**
> **Maliyet $0.00. Bayraklar varsayılan KAPALI.**
> Yeni: `webapp/medya/edinim.py`, `webapp/medya/nasa.py`,
> `outputs/sample/doga_i18_rapor.json`.
> Değişen: `webapp/medya/commons.py`,
> `webapp/testler/smoke_konsept2_doga_i18.py`,
> `webapp/testler/test_faz_i.py`, `outputs/sample/README.md` (+ bu handoff).
> **Dokunulmadı:** `pipeline.py`, `server.py`, arayüz, 22 alan, `deploy.sh`,
> `medya/lisans.py`, `medya/guvenlik.py`, `medya/indirme.py`.

### ⭐ I-18'in BLOKE'si AÇILDI — doğa pilotu GERÇEKTEN render edildi

| Ölçüm | I-18 | **I-19** |
|---|---|---|
| Medya | ⛔ **BLOKE** (Wikimedia 429) | ✅ **NASA'dan edinildi** |
| Doğa pilotu MP4 | ❌ yok | ✅ **`editorv2_doga_i18.mp4`** |
| Çözünürlük | — | 1920×1080 (**4K değil, dürüstçe**) |
| Süre | — | **16.427 sn** (15–20 aralığında) |
| Dil | — | **Türkçe** anlatım + Türkçe altyazı |
| PRE / POST QA | — | **WARN(fail=0) / PASS** |

### Üç yeni yetenek

**1. DEVRE KESİCİ (`medya/edinim.py`).** Bir host arka arkaya `esik` (2)
kalıcı hata verirse devre **açılır** ve o host `soguma` (900 sn) boyunca
**hiç denenmez**. Ölçülen davranış:

```
s01  commons BAYT-YOK (HTTP 429)  1.4s  ->  nasa OK   failover 38.4s (soguk baslangic)
s02  commons BAYT-YOK (HTTP 429)  0.9s  ->  nasa OK   failover  3.2s
s03  commons DEVRE-ACIK           0.0s  ->  nasa OK   failover  2.5s
s04  commons DEVRE-ACIK           0.0s  ->  nasa OK   failover  2.0s
devre: ardisik_hata {commons: 2}, acik_devreler ['commons']
```

s03/s04'te commons **hiç aranmadı bile** — aynı host zorlanmadı.

**2. `Retry-After` KARARI: beklemek mi, geçmek mi.**
I-18'in dersi koda yazıldı: sunucu **600 sn** isteyince beklemek yanlıştır.
`bekle_karari()` → kısa süre (≤30 sn) **BEKLE**, uzun süre **DEVRE-AC**.

**3. ARAMA/METADATA ile GERÇEK BAYT AYRIMI.**
Ölçülen: **metadata 16 / bayt 4**. Bir sağlayıcı metadata verip bayt
vermeyebilir — I-18'de tam bu olmuştu. İkisi ayrı sayılıyor.
Aynı ayrım **çözünürlüğe** de uygulandı: NASA arama ucu piksel ölçüsü
**vermiyor**, bu yüzden ölçü **indirme sonrası** doğrulanıyor ve yetersizse
aday **reddediliyor** (ilk koşumda 720×480 geldi → reddedildi → 3624×3624).

### Ölçülen kendi hatam — iki katmanlı yeniden deneme

İlk failover **109.6 sn** sürdü; bunun 103.8'i `commons.indir`ın **kendi**
3 denemesiydi. İki katmanın da yeniden denemesi "hızlı failover" iddiasını
karşılıksız bırakır. Politika tek yere (`edinim`) toplandı →
**109.6 sn → 4.3 sn**.

### Sağlayıcı zinciri — ne kullanıldı, ne atlandı

| Sağlayıcı | Sonuç |
|---|---|
| `commons` (Wikimedia) | metadata ✅, bayt ⛔ **HTTP 429** → devre açıldı |
| `nasa` | ✅ **4/4 sahne**, kamu malı, `GSFC` / `Caltech` künyeli |
| `pexels` | ⛔ **atlandı** — mevcut anahtar **geçersiz (HTTP 401)**, yeni anahtar **ALINMADI** |
| Openverse | ⛔ tam çözünürlük **aynı** rate-limitli hosta gidiyor |

### ⚠ ANLATIM GÖRÜNENE UYDURULDU

I-18'in metni **yer seviyesi** manzarayı anlatıyordu (buzul lagünü, siyah
kum plajı, şelale). NASA kütüphanesi **yörünge/uydu** görüntüsüdür. Metni
değiştirmeden render etmek, I-13'te kapatılan *"görsel ile anlatım
örtüşmüyor"* kusurunu geri getirirdi. Bu yüzden **anlatım görünene
uyduruldu**, görünen anlatıma değil. Yeni konu metni de aynı otomatik
sınıflandırmadan geçti: `seyahat` / kesin / **0.87** → `seyahat-4k` (auto).

### Açılış süresi TAHMİN EDİLMEDİ, ÖLÇÜLDÜ

`atlas-journey` profilinde hook/açılış bölünme eşiği **3.06 sn**,
`shot_min_sn` **2.0** — yani açılış **[2.0, 3.06)** olmalı. 4.025 ve
3.362 sn'lik iki deneme de bölündü ve kapı **doğru şekilde FAIL** verdi
(iki beat tek adayı paylaşıyordu). Eşik gevşetilmedi; cümle kısaltıldı.

### Önbellek kuralı doğruydu, önbellek eksikti

İkinci koşumda önbellekten gelen dosyalar **`ONBELLEK-PROVENANCE-YOK`** ile
**reddedildi**. Kural doğru — telif/atıf bilgisi olmayan medya kesin red.
Kusur önbellekteydi: künye artık dosyanın **yanına** yazılıyor
(`*.kunye.json`).

### Test kapsamı — kullanıcının istediği senaryolar

| Senaryo | Nasıl |
|---|---|
| Sağlayıcı hata 1: **429 → geç** | sahte sağlayıcı, ağ **yok** |
| Sağlayıcı hata 2: **arama patlıyor → geç** | sahte sağlayıcı |
| Hepsi düşerse | `ok=False`, **sahte aday üretilmez** |
| Devre kesici | açılma eşiği, soğuma, başarıda sıfırlama, **host hiç aranmıyor** |
| Önbellek | ikinci çağrıda **yeniden indirilmiyor** |
| `Retry-After` | yok → GEÇ, kısa → BEKLE, **600 → DEVRE-AC** |
| Provenance | lisans/sahip/kullanılabilirlik eksikse **indirilmez** |
| Çözünürlük | indirme **sonrası** ölçülür; yetersizse reddedilir |

Hepsi **ağsız** (sahte sağlayıcı) koşuyor — testler internete bağımlı değil.

### Ölçülen test sonucu (12 Ağu) — İKİ ORTAM AYRI

| Paket | A | B | C | D | E | F | G | H | I | Toplam |
|---|---|---|---|---|---|---|---|---|---|---|
| **Zengin venv** | 125 | 200 | 148 | 95 | 127 | 244 | 218 | **257** | **1397** | **2811** |
| **Sistem Python** | 125 | 200 | 148 | 95 | 127 | 244 | 218 | **203** | **1397** | **2757** |

0 hata, 0 BLOKE (I-18'in BLOKE'si kapandı). Faz I 1327 → **1397** (+70).
`deploy.sh` tanımsız-isim taraması → **0 bulgu**.

### BİLİNEN SINIRLAR (dürüstçe)

1. **4K DEĞİL.** Kaynaklar 2800–5184 px; hepsi 3840 eşiğini geçmediği için
   dürüstçe 1080p. **Upscale yapılmadı.**
2. **Medya yörünge/uydu görüntüsü** — yer seviyesi doğa fotoğrafı değil.
   Anlatım buna uyduruldu ama "İzlanda'da yürüyüş" tarzı bir yapım için
   uygun kaynak hâlâ yok.
3. **`SAGLAYICI-TEKEL` WARN duruyor** (%100 nasa) — zincirde hayatta kalan
   tek sağlayıcı. Gerçek çok sağlayıcılı işte düşmesi *beklenir*, ölçülmedi.
4. **Wikimedia hâlâ 429** — bu ortamın çıkış IP'sine özgü; başka ortamda
   devre hiç açılmayabilir.
5. **Pexels anahtarı geçersiz**; yeni anahtar alınmadı (kullanıcı kararı).
6. **Hareketli video B-roll BLOKE** (I-16'dan beri aynen).
7. **Algısal medya benzerliği hâlâ ölçülemiyor** (§32–§36 aynen).
8. **Canlı `/api/generate` hattı bu edinim zincirini görmüyor** — `pipeline`
   ve `server` değişmedi.

### SONRAKİ ATOM (I-20)

Ya yer seviyesi doğa fotoğrafı veren üçüncü bir güvenli sağlayıcı eklemek
(ör. çalışan bir Pexels/Openverse anahtarıyla), ya da edinim zincirini
`medya_kopru` üzerinden canlı `/api/generate` hattına **opt-in** bağlamak.

---

## 38. FAZ I-20 — ÜÇÜNCÜ KONSEPT: MOTOR SINANDI, RENDER PLAN'DA BLOKE (12 Ağu)

> **Durum: yerel yeşil, push edildi. Deploy YOK. Maliyet $0.00.**
> Yeni: `webapp/testler/smoke_konsept3_teknoloji_i20.py`.
> Değişen: `webapp/taksonomi.py`, `webapp/testler/test_faz_i.py` (+ handoff).
> **Dokunulmadı:** `pipeline.py`, `server.py`, arayüz, 22 alan, `deploy.sh`,
> `medya/*` (edinim zinciri I-19'dan aynen), kalite kapıları.

### Sonuç — iki parça

| Parça | Sonuç |
|---|---|
| Üçüncü konsept **auto sınıflandırma + üçüncü stil** | ✅ **KANITLANDI** |
| **Gerçek web medyası edinimi** (4/4, semantik uyumlu) | ✅ **BAŞARILI** |
| **Render** | ⛔ **PLAN seviyesinde BLOKE** — kapı doğru çalıştı |
| MP4 | ❌ üretilmedi (sahte PASS verilmedi) |

### ✅ Üçüncü konsept, üçüncü stil — hepsi otomatik

```
metin  : "Süperbilgisayarların enerji ve çip ekonomisi: işlem gücü nasıl
          üretiliyor ve faturası ne kadar"
konsept: aile=egitim  durum=kesin  guven=0.77
STIL   : explainer-hizli  (kaynak auto)  ->  edit profili premium-modern
```

Üç konsept → **üç ayrı stil** (testle kilitli):
`belgesel-sinematik` · `seyahat-4k` · `explainer-hizli`.

### ⚠ ÜÇÜNCÜ KEZ AYNI SINIFTA KAPSAM BOŞLUĞU

I-18'de doğa sözlüğü eksikti; burada **donanım/çip sözlüğü** eksikti.
Ölçülen: `egitim.teknoloji` (2.0/2) ile `egitim.aciklayici` (2.0/1) berabere
kaldı, güven 0.40'ın altına düştü → **`belirsiz`**, stil varsayılana düştü.
Teknoloji dalı **yazılım ağırlıklıydı**; süperbilgisayar/işlemci/çip/yarı
iletken/işlem gücü yoktu. §16'nın sözü yine uygulandı — yalnız `AGAC`'a
satır: **783 → 849 anahtar**. Aile 7 / dal 33 aynı, eski kelimeler silinmedi,
gerileme yok.

### ✅ Medya GERÇEKTEN edinildi ve SEMANTİK OLARAK UYUYOR

Wikimedia hâlâ `HTTP 429`. Konu, sağlayıcıların **gerçekten desteklediği**
en yakın dürüst başlıkla kuruldu: NASA'nın **kendi süperbilgisayar tesisi**.

| Sahne | Kaynak | Ölçü | Künye |
|---|---|---|---|
| s01 Pleiades süperbilgisayar | nasa | 4192×2832 | Dominic Hart |
| s02 süperbilgisayar salonu | nasa | 2048×3072 | Wade Sisler |
| s03 silikon karbür çip | nasa | 3000×2250 | GRC |
| s04 güneş paneli / enerji | nasa | 4986×3744 | NASA/JPL-Caltech |

metadata **19** / bayt **4** (ayrı sayıldı). Dört ayrı künye — sahneye özgü.
**NASA görüntüsü konuya uymasaydı kullanılmayacaktı**; burada uyuyor.

### ⛔ RENDER NEDEN BLOKE — kapı doğru çalıştı

Açılış beat'i bölünüyor ve iki beat **tek adayı paylaşıyor** →
`KALITE-MEDYA-TEKRAR` **FAIL** → `render_edilebilir=False`.

Üç ayrı açılış uzunluğu denendi (3.087 / 3.05 / 2.587 sn); üçünde de bölündü.
**Eşik gevşetilmedi, sağlayıcı kotası yükseltilmedi, sahte PASS verilmedi.**
Bu, I-15 ve I-19'da da yaşanan bilinen sınıf: bölünen sahne için **ikinci bir
aday** gerekiyor, ama tek sağlayıcı + kota 4 buna izin vermiyor.

⚠ Özellik dondurma saatine 20 dk kala ayar döngüsü **bilinçli olarak
durduruldu**; kanıtlanan kısım güvene alındı.

### Ölçülen test sonucu

| Paket | A | B | C | D | E | F | G | H | I | Toplam |
|---|---|---|---|---|---|---|---|---|---|---|
| **Zengin venv** | 125 | 200 | 148 | 95 | 127 | 244 | 218 | **257** | **1426** | **2840** |

0 hata. Faz I 1397 → **1426** (+29). Faz I'de **1 BLOKE** (I-20 render
raporu) — **PASS sayılmadı**, sebebi ölçülmüş olarak yazılı.

### SONRAKİ ATOM (I-21)

Bölünen sahneye **ikinci aday** verecek şekilde `medya_edin`i sahne başına
N aday getirir hale getirmek (sağlayıcı kotasını yükseltmeden). Bu, I-15'ten
beri üç kez karşımıza çıkan tek yapısal engel; çözülürse üçüncü konsept
pilotu doğrudan render edilebilir.

---

## 39. FAZ I-21 — BÖLÜNEN BEAT AYNI VARLIĞI PAYLAŞMASIN (dar atom, 12 Ağu)

> **Durum: yerel yeşil, push edildi. Deploy YOK. Maliyet $0.00.**
> Değişen: `webapp/medya/edinim.py`,
> `webapp/testler/smoke_konsept3_teknoloji_i20.py`,
> `webapp/testler/test_faz_i.py` (+ handoff).
> **Yeni sağlayıcı/mimari YOK.** `pipeline.py`, `server.py`, arayüz, 22 alan,
> `deploy.sh`, kalite kapıları, sağlayıcı kotası **dokunulmadı**.

### ✅ Dar hedef TUTTU

I-15'ten beri üç kez çıkan tek yapısal engel: bir sahne iki beat'e
bölündüğünde ikisi **tek adayı paylaşıyor** ve `KALITE-MEDYA-TEKRAR`
FAIL veriyordu.

`edinim.edin(..., adet=N)` artık **mevcut arama listesinden** N ayrı aday
seçiyor. Ölçülen kanıt:

| | I-20 | **I-21** |
|---|---|---|
| b001 / b002 varlığı | `s01_…` / **`s01_…` (AYNI)** | `s01_…` / **`s01y1_…` (FARKLI)** |
| PRE-QA | **FAIL** (fail=1) | **WARN (fail=0)** |
| Render | başlatılmadı | **tamamlandı** (17.109 sn, 1920×1080) |

**Ağ çağrısı sayısı ARTMADI** (testle kilitli: `ara()` yine **1 kez**
çağrılıyor — 6 aday zaten dönüyordu, I-21'e kadar yalnız ilki kullanılıyordu).
**Sağlayıcı kotası YÜKSELTİLMEDİ.** Kısmi başarı (2 istendi 1 geldi)
dürüstçe raporlanıyor.

### ⛔ RENDER KABUL EDİLMİŞ SAYILMAZ — POST-QA FAIL

Render tamamlandı ama **POST-QA FAIL**:
`POST-SIYAH-KARE` · `POST-OPTIK-DURGUN` · `POST-KENAR-SIYAH`.

Kök neden ölçüldü: bölünme 5 beat üretti, sağlayıcı kotası 4 →
**b005 medyasız** kaldı ve statik fallback karta düştü
(optik ortalama **0.178**, 3.75 sn donuk, siyah kare).

Yani I-21 kendi hedefini çözdü, ama **kota ile beat sayısı arasındaki
uyuşmazlık** yeni yüzeye çıktı. Kapılar bunu **doğru** yakaladı; MP4
teslim edilmiyor ve testte **BLOKE** olarak duruyor — sessizce PASS
sayılmadı.

### Ölçülen test sonucu

| Paket | B | C | D | I | Faz I toplam |
|---|---|---|---|---|---|
| Zengin venv | 200 | 148 | 95 | **1436** | 0 hata, **1 BLOKE** |

Faz I 1426 → **1436** (+10). BLOKE: I-21 POST-QA — sebebi ölçülmüş yazılı.

### SONRAKİ ATOM (I-22 — dondurma sonrası)

Tek kalan engel net: **beat sayısı sağlayıcı kotasını aşabiliyor.** Doğru
çözüm kotayı yükseltmek değil, ya (a) bölünmeyi plan aşamasında sahne
sayısına göre sınırlamak, ya da (b) `medya_edin`i **beat sayısına** göre
aday getirmek (plan bir kez koşulup beat sayısı öğrenildikten sonra).

---

## 40. FAZ I-22 — MEDYASIZ BEAT KUSURU ÇÖZÜLDÜ (dar atom, 12 Ağu)

> **Durum: yerel yeşil, push edildi. Deploy YOK. Maliyet $0.00.**
> Değişen: `webapp/editor/qa_on.py`, `webapp/edit_kopru.py`,
> `webapp/testler/smoke_konsept3_teknoloji_i20.py`,
> `webapp/testler/test_faz_i.py` (+ handoff).
> **Yeni sağlayıcı/mimari YOK.** `pipeline.py`, `server.py`, arayüz, 22 alan,
> `deploy.sh`, `medya/lisans.py`, `medya/guvenlik.py`, `medya/indirme.py`,
> kalite eşikleri **dokunulmadı**.

### ✅ Hedeflenen kusur ÇÖZÜLDÜ

I-21'de ölçülen zincir: bölünme **5 beat** üretti, sağlayıcı kotası **4**'tü,
**b005 medyasız** kalıp statik fallback karta düştü →
`POST-SIYAH-KARE` + `POST-OPTIK-DURGUN` + `POST-KENAR-SIYAH`.

| Ölçüm | I-21 | **I-22** |
|---|---|---|
| b005 varlığı | **(YOK)** → fallback kart | **`s04_…`** |
| Medyasız beat | **1/5** | **0/5** |
| b005 optik hareket | **0.178** (3.75 sn donuk) | **4.705** |
| `POST-SIYAH-KARE` | FAIL | ✅ **gitti** |
| `POST-OPTIK-DURGUN` | FAIL | ✅ **gitti** |
| Ardışık aynı medya | yok (I-21) | yok — 5 beat **5 ayrı varlık** |

### İki parçalı, en küçük geriye uyumlu çözüm

**1. Zorunlu PRE-QA kapısı — `KALITE-MEDYASIZ-BEAT` (fail).**
Herhangi bir beat `kaynak_turu != "medya"` ise render **durur**. Bu kusur
I-21'e kadar **render sonrası** yakalanıyordu — yani 40 sn render
harcandıktan sonra. Plan üzerinde **bedava** yakalanıyor artık.
⚠ Kapı `kalite_kapisi` bayrağına bağlı; kapalı yolda hüküm değişmez.

**2. Deterministik beat↔medya eşlemesi.** İki seçenek ölçüldü:
- *(a) bölünmeyi medya kapasitesine göre sınırla* — `beat.py`'ye motor
  değişikliği gerektirir, geriye uyumlu değil;
- *(b) planı bir kez kuru koşup gerçek beat sayısını öğren* — **seçildi.**

`beat.plan_yap` **ağ/medya/dosya kullanmaz**, yani kuru koşum bedava.
Öğrenilen beat sayısı iki yere birden bağlandı: sahne başına istenen aday
adedi **ve** `saglayici_tavani`.

⚠ **Bu keyfi kota artırımı DEĞİL.** Sabit 4 tavanı **çok sağlayıcılı**
durum için bir çeşitlilik güvencesidir; tek sağlayıcılı bir işte 4'ten
fazla beat oluşursa fazlası **garantili** medyasız kalır. Kota artık sabit
bir sayıya değil **ölçülen beat sayısına** bağlı (testle kilitli:
`saglayici_tavani=BEAT_SAYISI`, sabit rakam yasak). Kalite eşiklerinin
hiçbiri değişmedi.

### Bulunan ve düzeltilen kendi hatam

Çözünürlük kapısı ilk adayı reddedip ikinciye geçtiğinde kabul edilen dosya
`…_1.jpg` yolunda oluyor, ama smoke **indeks-0 yolunu** okuyordu. Sonuç:
s04 raporda **1431×820** (reddedilen dosya) görünüyordu ve kamera küçük
görüntüde kadrajdan taşıyordu. Düzeltmeden sonra s04 **4986×3744**.

### ⛔ MP4 KABUL EDİLMİŞ SAYILMIYOR — kalan tek FAIL

`POST-KENAR-SIYAH`: 6/68 karede kenarda siyah bant.
**Kök neden ölçüldü:** s02 kaynağı **2048×3072 — DİKEY**. 16:9 karede
pillarbox (yan siyah bant) veriyor; kamera taşması değil, **en-boy oranı
uyuşmazlığı**. Kapı bunu doğru yakaladı.

Render tamamlandı (17.109 sn, 1920×1080, LUFS −14.36, TP −4.09, sessizlik
%0, 7 kesme) ama **POST-QA FAIL olduğu için MP4 teslim edilmiyor** ve
testte **BLOKE** olarak duruyor.

### Ölçülen test sonucu

| Paket | A | B | C | D | E | F | G | H | I | Toplam |
|---|---|---|---|---|---|---|---|---|---|---|
| Zengin venv | 125 | 200 | 148 | 95 | 127 | 244 | 218 | **257** | **1442** | **2856** |

0 hata. Faz I 1436 → **1442**. **1 BLOKE** (I-22 POST-QA) — PASS sayılmadı.

### SONRAKİ ATOM (I-23)

Tek kalan engel: **dikey/kare kaynak 16:9'a pillarbox veriyor.** Doğru
çözüm eşiği gevşetmek değil; ya (a) edinim tarafında **en-boy oranı kapısı**
(16:9'a yakın olmayan kaynağı reddet — çözünürlük kapısıyla aynı desen), ya
da (b) render tarafında dikey kaynağı **güvenli crop** ile doldurmak.
(a) daha küçük ve mevcut desenle birebir.

---

## 41. FAZ I-23 — EN-BOY ORANI UYUMLULUK KAPISI (dar atom, 13 Ağu)

> **Durum: yerel yeşil, POST-QA TAMAMEN PASS, push edildi. Deploy YOK.
> Maliyet $0.00.**
> Değişen: `webapp/medya/edinim.py`,
> `webapp/testler/smoke_konsept3_teknoloji_i20.py`,
> `webapp/testler/test_faz_i.py`, `outputs/sample/teknoloji_i20_rapor.json`
> (+ handoff).
> **Yeni sağlayıcı/mimari YOK.** `pipeline.py`, `server.py`, arayüz, 22 alan,
> `deploy.sh`, `medya/lisans.py`, `medya/guvenlik.py`, `medya/indirme.py`,
> `medya/nasa.py`, `medya/commons.py`, `editor/qa_on.py`, `editor/qa_son.py`,
> `editor/kalite_kapisi.py`, `editor/motion.py`, kalite eşikleri
> **dokunulmadı** (git ile doğrulandı).

### ⚠ ÖNCE: BÖLÜM 40'IN KÖK NEDENİ YANLIŞTI — ÖLÇÜLDÜ ve DÜZELTİLDİ

Bölüm 40 kalan tek FAIL için şunu yazıyordu:

> "Kök neden ölçüldü: s02 kaynağı **2048×3072 — DİKEY**. 16:9 karede
> **pillarbox** (yan siyah bant) veriyor."

**Bu iddia iki yerden birden yanlış.** I-22 çıktısı üzerinde ölçüldü:

| Ölçüm | Bölüm 40'ın iddiası | **Ölçülen gerçek** |
|---|---|---|
| İhlal eden beat | s02 → b003 | **6/68 ihlalin 6'sı da b002** (1.00–2.25 sn) |
| İhlal eden varlık | s02 `2048×3072` | **s01 yedeği `2832×3603`** (oran 0.786) |
| s02'nin ürettiği ihlal | (kök neden) | **0 (sıfır)** |
| Mekanizma | pillarbox | **pillarbox DEĞİL** |

**Mekanizma neden pillarbox değil:** `Kamera.tsx > Zemin` `objectFit:'cover'`
kullanır, yani kare **tamamen doludur**. İhlal karesinde 0–200. sütunlar
ölçüldü: **ort 8.2 / std 1.24 / min 6 / max 13** — yani gerçek (koyu) fotoğraf
içeriği. Sentetik bir bant **sabit** olurdu (std 0) ve 8.2 değil **0** okunurdu.

**Gerçek mekanizma — AŞIRI COVER-CROP.** 16:9'u 0.786 oranlı kaynaktan `cover`
ile doldurmak kaynağın yüksekliğinin yalnızca **%44'ünü** bırakır; üstüne
`punch-1.35` binince görülen alan kaynağın **~%33'üne** düşer. Geriye kalan dar
dilim temsili olmayan bir **gölge koridoruydu**: sol şerit 8.2 < eşik 16.

Atom yine de doğru atomdu — dikey kaynağı edinimde reddetmek kusuru kaldırıyor
— ama **gerekçe düzeltildi**. Kapı "oran farkına" değil **kırpmanın kaynağın ne
kadarını attığına** bakıyor.

### Eşik uydurma değil — AYNI render'dan türetildi

`korunan_oran = min(r/R, R/r)` (cover sonrası kaynaktan geriye kalan pay):

| Kaynak | oran | korunan | I-22'de ölçülen |
|---|---|---|---|
| 4192×2832 | 1.480 | 0.832 | temiz, 0 ihlal |
| 3000×2250 | 1.333 | **0.750** | temiz, 0 ihlal — **en dar TEMİZ** |
| 4986×3744 | 1.332 | 0.749 | temiz, 0 ihlal |
| **2832×3603** | **0.786** | **0.442** | **6 ihlalin kaynağı** |
| 2048×3072 | 0.667 | 0.375 | aynı sınıf |

Sınır **(0.442, 0.750]** aralığında olmak zorunda. **0.70** seçildi: en dar
temiz ölçümün hemen altında, ihlal üretenin çok üstünde. 4:3 (kamu malı
fotoğrafın baskın formatı) geçer; kare (0.562) ve dikey geçmez.
⚠ **Dürüst sınır:** 5:4 (0.703) eşiği **kıl payı** geçiyor ve ölçülmedi.

### İki parçalı çözüm (ikincisi ölçümle zorunlu oldu)

**1. `ORAN-UYUMSUZ` kapısı.** İndirme sonrası ölç → uymuyorsa reddet → **aynı
mevcut arama listesindeki** sıradaki lisanslı/provenance'lı adaya geç.
Çözünürlük kapısıyla **birebir aynı desen**. Ölçülen oran, hedef oran ve red
nedeni raporda görünür. Kapı `hedef_oran=0` ile **varsayılan kapalı** — geriye
tam uyumlu.

**2. `AYIRT-EDILEMEZ` kapısı — ölçüm bunu ZORUNLU kıldı.** Oran kapısı s01'in
dikey adayını eleyince sıradaki aday birincinin **neredeyse aynı karesi** çıktı
(dHash **0.875 ≥ 0.86**) ve `KALITE-MEDYA-TEKRAR` **FAIL** verdi. İki kısıt
**aynı anda** sağlanmak zorunda; birini greedy seçmek diğerini kırıyor.
⚠ Edinim **dHash HESAPLAMAZ**; ölçer dışarıdan verilir — tıpkı
`kalite_kapisi.medya_tekrari` gibi. Eşik **QA eşiğinin kendisinden** okunur
(`kk.BENZERLIK_ESIGI`), ikinci bir sabit yazılmadı.

### Bulunan ve kapatılan iki boşluk

1. **BEKLE yolu kapısızdı.** `Retry-After` sonrası başarılı olan aday **hiç
   ölçülmeden** kabul ediliyordu — yani çözünürlük kapısı da atlanıyordu.
   Artık iki yol da aynı kapılardan geçer.
2. **Önbellek oran kapısını baypas ediyordu.** Önbellekteki dosya 16:9'a
   uymuyorsa artık **isabet sayılmaz**, normal edinim yoluna düşülür.

### Kendi bulduğum yanlış beyan

Smoke'un son satırı **koşulsuz** olarak "Medya WEB'DEN BULUNMADI — yerel Apollo
fixture'i kullanildi" yazıyordu. I-19'dan beri **doğru değil**; medya gerçek
sağlayıcı zincirinden iniyor. Dosyanın kendi kuralı "SAHTE KANIT YOK" olduğu
için satır **ölçümden türetildi**: `MEDYA: 4/4 sahne GERCEK saglayicidan
(nasa) · fixture KULLANILMADI · maliyet $0.00`.

### Üç kapı da gerçek render'da doğru adayda ateşledi

| Sahne | aday | ölçü | sonuç |
|---|---|---|---|
| s01 | idx0 | 4192×2832 (1.480) | **kabul** |
| s01 | idx1 | 2832×3603 (0.786) | **ORAN-UYUMSUZ** |
| s01 | idx2 | 4256×2832 | **AYIRT-EDILEMEZ** (0.875) |
| s01 | idx3 | 4134×2832 | **kabul** |
| s02 | idx0 | 2048×3072 (0.667) | **ORAN-UYUMSUZ** |
| s02 | idx1 | 3000×2000 (1.500) | **kabul** |
| s04 | idx0 | 1431×820 | **COZUNURLUK-YETERSIZ** |
| s04 | idx1 | 4986×3744 | **kabul** |

**Ağ çağrısı artmadı** (testle kilitli: `ara()` yine **1 kez**). Sağlayıcı
kotası değişmedi. Yeni sağlayıcı yok. Ücretli API yok.

### ✅ PİLOT YENİDEN RENDER — POST-QA TAMAMEN PASS

Gerçek NASA kamu malı medyası + Türkçe ses, 4/4 sahne `nasa`, fixture yok.

| Ölçüm | I-22 | **I-23** |
|---|---|---|
| `POST-KENAR-SIYAH` | **FAIL** 6/68 | ✅ **0/68, temiz** |
| en koyu sol / sağ | 8.26 / 25.18 | **39.44 / 42.54** |
| POST-QA | **FAIL** | ✅ **PASS (0 sorun)** |
| Faz I BLOKE | **1** | ✅ **0** |
| Dikey kaynak sayısı | 2 | **0** |

**ffprobe:** h264 **1920×1080** @30fps + aac 48 kHz/2ch, **17.109 sn**, 45.06 MB.
**Ses:** LUFS **−14.36**, TP **−4.09**, LRA 3.6, sessizlik **%0**, ölü final 0.0 sn.
**Kesmeler:** 7. **Siyah/donmuş aralık:** yok. **Optik:** genel 14.503, durgun ihlal 0.
**Kareler:** **11 adet** (≥9) incelendi — hepsi tam kare, siyah bant yok.
**Semantik uygunluk:** b003 "binlerce işlemci sıra sıra" → SGI ICE X rafları;
b004 "silikon üzerindeki devreler" → silisyum karbür çip; b005 "faturası
enerjiyle" → Juno güneş paneli testi. **Tekrar:** 0 (en yüksek ikili 0.5625).
**Tipografi:** güvenli alan ✅, çakışma ✅, altyazı ✅, Türkçe aksanlar doğru.
**Kaynak künyesi:** sahneye özgü 4 ayrı atıf (Dominic Hart / GRC /
NASA-JPL-Caltech-Lockheed Martin). **Motion:** 4 benzersiz hareket, ardışık
tekrar 0. **İzleyici kalite puanı:** 80.0/100 (I-22 ile aynı — regresyon yok).

### Ölçülen test sonucu

| Paket | A | B | C | D | E | F | G | H | I | Toplam |
|---|---|---|---|---|---|---|---|---|---|---|
| Zengin venv | 125 | 200 | 148 | 95 | 127 | 244 | 218 | 257 | **1489** | **2903** |

0 hata. Faz I 1442 → **1489** (+47). **Faz I BLOKE 1 → 0.**
Kalan tek BLOKE Faz H'deki `QA_TEST_VIDEO` (opsiyonel, I-22'den beri aynı).

### ⚠ BİLİNEN SINIR (I-23 kapsamı dışı, I-22'den devralındı)

Önbellek dolu ikinci koşumda `edin()` çağrılmadığı için **yedek aday
taşınmıyor**; bölünen sahne medyasız kalır ve PRE-QA doğru şekilde **render'ı
durdurur**. Pilotu yeniden üretmek için `cikti/_i20_medya` **silinmeli**.
Bu bir kusur değil kapının doğru davranışı, ama sonraki oturum bilmeli.

### SONRAKİ ATOM (I-24 adayları)

Kapılar temiz; kalan iki **kalite** açığı (ikisi de FAIL değil, WARN/puan):
- `motion_cesitlilik` **0.0/20** — açılış ve kapanış ikisi de `push-in`;
  ritim ailesi çeşitlenmeli (I-17 gramerinde dar atom).
- `SAGLAYICI-TEKEL` WARN — tek sağlayıcı %100 (`nasa`); Commons lisans
  duvarını geçen aday döndürmüyor, sebep **ölçülmeli**.

---

## 42. FAZ I-24 — MOTION ÇEŞİTLİLİĞİ ÖLÇÜLEBİLİR KAPIYA ÇEVRİLDİ (dar atom, 13 Ağu)

> **Durum: yerel yeşil, POST-QA TAMAMEN PASS, kalite puanı 100/100,
> push edildi. Deploy YOK. Maliyet $0.00.**
> Değişen: `webapp/editor/gramer.py`, `webapp/editor/kalite_kapisi.py`,
> `webapp/editor/qa_on.py`, `webapp/testler/test_faz_i.py`,
> `outputs/sample/teknoloji_i20_rapor.json` (+ handoff).
> **Yeni sağlayıcı/ağ çağrısı/ücretli API YOK. Rastgelelik YOK.**
> `pipeline.py`, `server.py`, `deploy.sh`, `medya/*`, `editor/motion.py`,
> `editor/plan.py`, `editor/beat.py` ve **smoke betiği** dokunulmadı
> (git ile doğrulandı) — düzeltme tamamen **motorda**.

### ✅ BAĞIMSIZ DOĞRULANAN KÖK NEDEN

`motion_cesitlilik` puanı **hepsi-ya-hiçbiri**. Dört koşuldan **üçü yeşildi**:

| Koşul | Ölçülen |
|---|---|
| `ardisik_tekrar` yok | ✅ 0 |
| `pencere_tekrari` yok | ✅ 0 |
| `benzersiz_gecis >= 2` | ✅ 3 |
| **`acilis_kapanis_ayri`** | ❌ **False** — b001 `push-in`, b005 `push-in` |

**Tek kırmızı buydu.** Mekanizma da ölçüldü: b005 `islev=sonuc` →
`RITIM_TERCIHI` **"pull-out"** ister; ama **pencere filtresi**
(b002–b004 = `pull-out`/`slow-drift`/`pan-right`) `pull-out`'u havuzdan
**çıkarıyor**, tercih düşüyor ve fallback `adaylar[indeks % len]`
**`push-in`**'e — yani açılışın aynısına — iniyordu.
Kodda **açılış ≠ kapanış kontrolü hiç yoktu**; `gramer.py`'deki
"acilis ile kapanisin FARKLI olmasi zaten korunuyor" yorumu **yanlıştı**.

### ⚠ İKİNCİ BULGU — KUSURU GİZLEYEN RAPORLAMA

Puanın `gerekce` metni yalnızca **geçen** üç koşulu yazıyordu:
`"benzersiz hareket 4, benzersiz gecis 3, pencere tekrari 0"` — hepsi yeşil.
**Düşen koşulun adı hiçbir yerde yoktu.** 0/20 bu yüzden açıklanamaz
görünüyordu. Artık gerekçe düşen koşulu **adıyla** söylüyor ve bileşen
`kosullar` + `dusen_kosullar` alanlarını taşıyor.

### Üç parçalı çözüm

**1. ÖLÇÜM — `islev_tekrari` (yeni).** `islev` bu ölçüme I-17'den beri
**geliyordu ama hiç kullanılmıyordu**. Aynı anlatı işlevindeki
(hook/açıklama/sonuç) iki beat aynı hareketi alırsa izleyici aynı "cümleyi"
iki kez duyar. **Pencere bunu yakalayamaz**: pencere yalnızca son N çekime
bakar, işlev ise videonun her yerine dağılabilir.

**2. KAPI — iki yeni FAIL kodu (PRE-QA, plan üzerinde bedava).**
- `KALITE-MOTION-ACILIS-KAPANIS` — açılış ve kapanış aynı hareket.
- `KALITE-MOTION-ISLEV-TEKRAR` — aynı işlevde aynı hareket.

Bu kusur I-24'e kadar **hiç hüküm üretmiyordu**; yalnızca puanı düşürüyordu.
⚠ İkisi de `kalite_kapisi` bayrağına bağlı (`_ekle` → `if acik`); **kapalı
yolda hüküm değişmez** — I-14'ten beri süren sözleşme korundu.

**3. SEÇİM — deterministik, işlev + medya geometrisi.**
- `acilis_hareketi`: **yalnızca kapanış** çekiminde kısıt.
- `islev_hareketleri`: aynı işlevde kullanılmışlar çıkarılır.
- `genislik/yukseklik`: **geometri sıralaması**.

**Geometri neden anlamlı:** `Zemin` `objectFit:'cover'` kullanır. Kaynak
16:9'dan **genişse** cover fazla genişliği kırpar → yatay pay vardır, yatay
pan kaynağın **gerçekten daha fazlasını** gösterir. Kaynak **darsa** (4:3)
kırpma dikeydir; yatay pan aynı kırpımı kaydırmaktan ibarettir, yeni bilgi
getirmez — orada içeri/dışarı hareket dürüsttür.

⚠ **DÜRÜST SINIR:** geometri bir **yasak değil, deterministik sıralamadır**.
Havuzu asla boşaltmaz; yalnızca eşit geçerli adaylar arasında sırayı belirler.
Sert kısıtlar da havuzu boşaltmaz (boşalırsa eski havuz korunur) — kusur
gizlenmez, kapı zaten PRE-QA'da hüküm verir.
⚠ Düzeltme yolları (`ARDIL-AYNI-VARLIK`, `ARDIL-AYNI-HAREKET`) da aynı
kısıtları taşır; aksi halde tekrarı **geri getirebilirlerdi**.

### ✅ ÖLÇÜLEN ÖNCE → SONRA

| Ölçüm | I-23 | **I-24** |
|---|---|---|
| Hareketler | push-in, pull-out, slow-drift, pan-right, **push-in** | push-in, pull-out, pan-right, pan-left, **slow-drift** |
| Benzersiz hareket | 4 / 5 beat | ✅ **5 / 5 beat** |
| `acilis_kapanis_ayri` | **False** | ✅ **True** |
| `islev_tekrari` | (ölçülmüyordu) | ✅ **0** |
| `motion_cesitlilik` | **0.0 / 20** | ✅ **20.0 / 20** |
| **İzleyici kalite puanı** | 80.0 / 100 | ✅ **100.0 / 100** |

### ✅ PİLOT YENİDEN RENDER — POST-QA TAMAMEN PASS

Gerçek NASA kamu malı medyası + Türkçe ses; 4/4 sahne `nasa`, fixture yok.

**ffprobe:** h264 **1920×1080** @30fps + aac 48 kHz/2ch, **17.109 sn**, 39.88 MB.
**Ses:** LUFS **−14.36**, TP **−4.09**, LRA 3.6, sessizlik **%0** (ince tarama
da boş), ölü final 0.0 sn. **Kesmeler:** 7. **Siyah/donmuş aralık:** yok.
**Kenar siyahlığı:** **0/68**, temiz. **Optik:** genel 15.901, durgun ihlal 0
— beş beat de hareketli (40.9 / 5.4 / 8.2 / 18.6 / 4.0).
**Kareler:** **11 adet** (≥11) incelendi; ayrıca hepsinde **tam çözünürlükte
dört kenar** ayrı ölçüldü — en koyu kenar 24.93 (gerçek görüntü içeriği,
siyah eşiği 16'nın üstünde). Yeni `pan-right`/`pan-left` hareketleri
**taşma üretmedi**. **Tipografi:** güvenli alan ✅, çakışma ✅, altyazı ✅,
Türkçe aksanlar doğru. **Künye:** sahneye özgü 4 ayrı atıf. **Tekrar:** 0.

### Ölçülen test sonucu

| Paket | A | B | C | D | E | F | G | H | I | Toplam |
|---|---|---|---|---|---|---|---|---|---|---|
| Zengin venv | 125 | 200 | 148 | 95 | 127 | 244 | 218 | 257 | **1525** | **2939** |

0 hata. Faz I 1489 → **1525** (+36). **Faz I BLOKE 0.**
Kalan tek BLOKE Faz H'deki `QA_TEST_VIDEO` (opsiyonel, I-22'den beri aynı).

### ⚠ BİLİNEN SINIR (değişmedi)

Pilotu yeniden üretmek için `cikti/_i20_medya` **silinmeli** (dolu önbellekte
yedek aday taşınmıyor; PRE-QA doğru şekilde render'ı durdurur).

### SONRAKİ ATOM (I-25 adayı)

Kalite puanı 100/100; kapılar temiz. Kalan tek WARN:
`SAGLAYICI-TEKEL` — tek sağlayıcı %100 (`nasa`), tavan %40. Commons her
sorguda `ADAY-YOK` dönüyor; **sebebi ölçülmeli** (lisans duvarı mı, sorgu
biçimi mi) — dar atom olarak Commons'ın eleme gerekçesini raporlamak.

---

## 43. FAZ I-25 — SAĞLAYICI-TEKEL TANISI: KÖK NEDEN BİZDEYDİ (dar tanı atomu, 13 Ağu)

> **Durum: yerel yeşil, iki gerçek hata düzeltildi, WARN dürüstçe duruyor,
> push edildi. Deploy YOK. Maliyet $0.00.**
> Değişen: `webapp/medya/commons.py`, `webapp/medya/edinim.py`,
> `webapp/testler/smoke_konsept3_teknoloji_i20.py`,
> `webapp/testler/test_faz_i.py`, `outputs/sample/teknoloji_i20_rapor.json`
> (+ handoff).
> **Sahte sağlayıcı çeşitliliği YOK. Kota/ağ çağrısı artışı YOK. Yeni
> sağlayıcı YOK.** `pipeline.py`, `server.py`, `deploy.sh`, 22 alan
> sözleşmesi, `gramer.py`, `qa_on.py`, `kalite_kapisi.py`, `lisans.py`,
> `guvenlik.py`, `indirme.py`, `nasa.py` **dokunulmadı** (git ile doğrulandı).
> I-23 oran/ayırt kapıları ve I-24 motion kapıları **korundu**.

### ⚠ KÖK NEDEN: "Commons boş" DEĞİLDİ — SORGUMUZ BOZUKTU

Dört atom boyunca `ADAY-YOK / "lisans/provenance duvarını geçen aday yok"`
yazısı, sorunun **lisans duvarında** olduğunu düşündürdü. Ölçüm bunu çürüttü.

İlk sinyal raporun içindeydi: Commons `metadata=0` **ve** `elenen=0`.
Lisans duvarı çalışsaydı `elenen > 0` olurdu. **Hiçbir şey elenmemişti —
arama zaten boş dönüyordu.**

Aynı `commons.ara()` çağrısıyla ölçüldü (ek kota/ağ **yok**):

| sorgu | denenen | aday |
|---|---|---|
| `Pleiades supercomputer **Iceland**` | **0** | 0 |
| `Pleiades supercomputer` | **18** | **6** |
| `supercomputer facility **Iceland**` | **0** | 0 |
| `supercomputer facility` | **18** | **6** |
| `solar array power **Iceland**` | **0** | 0 |
| `solar array power` | **18** | **6** |
| `Silicon Carbide Integrated Circuit Chip` (temiz) | **0** | 0 |

**Kaynak:** `beaee8f` (I-20) satırı I-18'in **doğa/İzlanda** smoke'undan
olduğu gibi kopyalamış. Teknoloji konusunda `" Iceland"` bir **konu
bulaşanı**. 3/4 sahnede tek sebep buydu.
**s03 ise temiz sorguyla da `denenen=0`** — Commons'ta bu konuda aday
**gerçekten yok**; o boşluk **dürüst** bırakıldı, uydurulmadı.

### ⚠ İKİNCİ GERÇEK HATA — ALAKA SİNYALİ ATILIYORDU

Sorguyu düzeltmek **tek başına videoyu bozacaktı.** `commons.ara()` sonuçları
**salt çözünürlüğe** göre sıralıyordu ve arama motorunun zaten verdiği
`index` (alaka sırası) alanını **tamamen atıyordu**. MediaWiki `pages`
sözlüğü pageid'ye göre anahtarlı olduğu için sıra yalnızca `index`te taşınır.

Ölçülen vaka (`"Pleiades supercomputer"`, 18 sonuç):

| dosya | alaka | ölçü | eski sıra | yeni sıra |
|---|---|---|---|---|
| `Pleiades large.jpg` (**yıldız kümesi**, Palomar/STScI künyeli) | **17/18** | 4877×3515 | **1.** | **son** |
| `NASA Pleiades Supercomputer.jpg` (**gerçek konu**) | 12 | 4983×3303 | 2. | öne |

`supercomputer facility` sorgusunda da **RC Lens – Lille OSC futbol maçı**
fotoğrafları ("OSC" eşleşmesi) ilk 6'ya giriyordu; alaka sıralamasıyla
elendiler. Lisansı temiz ama **konu dışı** görsel = **yanlış video**.

Artık **alaka birincil, çözünürlük ikincil**.
⚠ **Çözünürlük EŞİĞİ değişmedi** (`en_az_genislik` filtresi yukarıda ve aynı)
— bu bir eşik gevşetmesi **değildir**; testle kilitli.

### ⚠ ÜÇÜNCÜ DÜZELTME — KUSURU 4 ATOM GİZLEYEN TANI KÖR NOKTASI

`edinim` raporu yalnızca `metadata` ve `elenen` yazıyordu. İkisi de 0 olunca
**"arama hiç sonuç vermedi"** ile **"sonuç geldi, hepsi elendi"** ayırt
edilemiyordu. Ayrıca rapor **sahne sorgusunu** gösteriyordu, sağlayıcıya
**gerçekten giden** sorguyu değil — bulaşan bu yüzden görünmez kaldı.

Eklendi: `kullanilan_sorgu`, `denenen`, `elenme_nedenleri` ve iki ayrı sebep
metni (`ARAMA-BOS` / `HEPSI-ELENDI`).

### ✅ ÖLÇÜLEN ÖNCE → SONRA (arama katmanı)

| Ölçüm | I-24 | **I-25** |
|---|---|---|
| Commons `denenen` (s01/s02) | **0 / 0** | ✅ **18 / 18** |
| Commons `metadata` (s01/s02) | **0 / 0** | ✅ **6 / 6** |
| Commons durumu | `ADAY-YOK` | `BAYT-YOK (HTTP 429)` |
| Konu dışı aday ilk sırada | **evet** (yıldız kümesi) | ✅ **hayır** |
| Raporda giden sorgu | **yok** | ✅ **var** |

### ⛔ SAĞLAYICI-TEKEL WARN **DÜRÜSTÇE DURUYOR** — sebep DEĞİŞTİ

Arama düzeldi ama **bayt gelmedi**: Commons yük sunucusu bu host'a
**HTTP 429 / `Retry-After: 600`** dönüyor. Tek ve nazik bir bağımsız sonda
ile doğrulandı (1 istek): `HTTP 429  Retry-After=600`.

Bu, **I-19'da zaten ölçülmüş ve tasarıma girmiş** koşulun ta kendisi. Motor
doğru davrandı: `bekleme_karari = DEVRE-AC` (600 sn **beklenmedi**), devre
kesici 2. kalıcı hatada açıldı, NASA'ya geçildi.

Yani tekel **sahte çeşitlilikle kapatılmadı**; sebebi artık **ölçülmüş ve
raporda yazılı** (`ADAY-YOK` değil, `HTTP 429`).

### ✅ MEDYA KÜMESİ DEĞİŞMEDİ — kabul edilen MP4 korunuyor

Commons bayt veremediği için 4 sahne de yine NASA'dan geldi. Yeniden render
**zorunluydu** (kümenin değişip değişmediği ancak edinimi koşarak bilinir) ve
sonuç **alan alan aynı** çıktı:

| alan | I-24 (kabul) | I-25 | aynı? |
|---|---|---|---|
| POST-QA | PASS | PASS | ✅ |
| kalite puanı | 100.0 | 100.0 | ✅ |
| ölçü / süre | 1920×1080 / 17.109 sn | aynı | ✅ |
| LUFS / TP | −14.36 / −4.09 | aynı | ✅ |
| sessizlik / siyah / donmuş | 0 / 0 / 0 | aynı | ✅ |
| kesme | 7 | 7 | ✅ |
| kenar ihlali | 0/68 | 0/68 | ✅ |
| hareketler | 5 ayrı | aynı | ✅ |
| varlıklar / sağlayıcı | 4 NASA | aynı | ✅ |

**ffprobe (diskteki dosya):** h264 1920×1080 + aac 48 kHz/2ch, 17.109 sn,
39.88 MB. **11 kare** yerinde. Yeni bir MP4 kabulü **iddia edilmiyor** —
kabul edilen I-24 çıktısı **birebir yeniden üretildi**.

### Ölçülen test sonucu

| Paket | A | B | C | D | E | F | G | H | I | Toplam |
|---|---|---|---|---|---|---|---|---|---|---|
| Zengin venv | 125 | 200 | 148 | 95 | 127 | 244 | 218 | 257 | **1546** | **2960** |

0 hata. Faz I 1525 → **1546** (+21). Faz I BLOKE 0.
Alaka sıralaması testleri **sahte API yanıtı** ile koşuyor (`ara()` kendi
`acan`ını dışarıdan alıyor) — **ağ yok, kota yok**.

### ⚠ ÖLÇÜLEN AMA ÇÖZÜLMEYEN (dürüst not)

s01'in Commons denemesi **54.1 sn** sürdü (s02: 1.3 sn). İkisi de doğru
kararla (`DEVRE-AC`) bitti; gecikme ilk bayt isteğinin sunucu tarafında
yavaş 429'lanmasından geliyor. Tekrar üretmek Commons'ı dövmeyi gerektirir,
bu yüzden **düzeltilmedi, ölçüm olarak yazıldı**. Maliyet $0; yalnızca
duvar saati.

### SONRAKİ ATOM (I-26 adayı)

- Commons 429'u host/IP kaynaklı; **sağlayıcı çeşitliliği için gerçek
  seçenek** ya farklı bir kamu malı sağlayıcı ya da 429 penceresi dışında
  edinim. İkisi de bu atomun kapsamı dışıdır ve **kullanıcı kararıdır**.
- s03 için Commons'ta konu gerçekten yok; sorgu genişletme (ör. eş anlamlı
  terim) **ölçülerek** denenebilir — uydurma eşleşme değil.

---

## 44. FAZ I-26 — s03 AŞIRI DAR SORGU ÇÖZÜLDÜ; PİLOT ⛔ BLOKE (dar atom, 13 Ağu)

> **Durum: atom hedefine ULAŞTI, ama pilot MP4 KABUL EDİLMİŞ SAYILMAZ.
> Yerel yeşil (0 hata), push edildi. Deploy YOK. Maliyet $0.00.**
> Değişen: `webapp/medya/edinim.py`,
> `webapp/testler/smoke_konsept3_teknoloji_i20.py`,
> `webapp/testler/test_faz_i.py`, `outputs/sample/teknoloji_i20_rapor.json`
> (+ handoff).
> **Yeni sağlayıcı YOK. Kota/ağ çağrısı artışı YOK. Sahte sağlayıcı PASS YOK.**
> `pipeline.py`, `server.py`, `deploy.sh`, 22 alan sözleşmesi, `gramer.py`,
> `qa_on.py`, `kalite_kapisi.py`, `motion.py`, `medya/lisans.py`,
> `medya/guvenlik.py`, `medya/indirme.py`, `medya/nasa.py` **dokunulmadı**.
> I-23/I-24/I-25 kapıları **korundu**.

### ⚠ I-25'İN NOTU YANLIŞTI — ÖLÇÜMLE DÜZELTİLDİ

I-25 s03 için şunu yazmıştı: *"Commons'ta bu konuda aday **gerçekten yok**"*.
O hüküm **tek sorgu** üzerinde verilmişti. I-26'da 2–3 konuya sadık alternatif
**aynı düşük maliyetli bütçede** ölçüldü ve iddia **çürüdü**:

| sorgu | terim | denenen | aday |
|---|---|---|---|
| `Silicon Carbide Integrated Circuit Chip` (eski) | 5 | **0** | 0 |
| `silicon carbide integrated circuit` | 4 | **2** | **2** ⭐ |
| `integrated circuit chip` | 3 | 18 | 6 |
| `microchip silicon` | 2 | 18 | 6 |
| `"silicon carbide" OR "integrated circuit" OR microchip` | — | 18 | 6 |

**Kök neden "Commons boş" değil, sorgunun AŞIRI DAR olmasıydı:**
CirrusSearch terimleri **varsayılan olarak AND'ler**; 5 terimin hepsini birden
taşıyan dosya yok.

### Neden A seçildi — sayılarla

- **Semantik sadakat:** A'nın iki adayı da NASA Glenn'in **gerçek silisyum
  karbür entegre devreleri** (*Extremely durable silicon carbide
  semiconductor*, *Heat-resistable ICs*). Anlatım "silikon üzerindeki
  devreler" — birebir aynı konu. B/C/OR ise tüketici anakartları, fare çipi,
  EPROM paketleri getiriyor: lisansı temiz ama **konuya uzak**.
- **Kapılar:** A'nın iki adayı da **6000×3999** (oran 1.500) — çözünürlük
  **ve** I-23 oran kapısından geçti. B'nin 6 adayından 4'ü ORAN-RED.
- **TEK SORGU İLKESİ KORUNDU:** A hem Commons'ı açtı (**0 → 2**) hem NASA'yı
  iyileştirdi (**1 → 2**) ve NASA'nın **birinci adayı değişmedi** (aynı GRC
  çipi). Sağlayıcılara ayrı sorgu gitmiyor — I-25'in ilkesi bozulmadı.

### Bedava tanı: AŞIRI DARLIK ipucu

`ARAMA-BOS` sebebi artık terim sayısını da yazıyor ve ≥4 terimde
*"çok terimli sorgu terimleri AND'leyen uçlarda boş dönebilir, daha genel bir
eş-anlamlı DENENMELİ"* uyarısı veriyor. **Ek çağrı yok.**

### ✅ ATOM HEDEFİNE ULAŞTI

Gerçek koşumda s03 için Commons **meta=2** döndü (I-25'te 0'dı). Ama **indirme
HTTP 429** verdi → devre kesici korundu → **NASA'ya dürüst düşüş**.
**Sahte sağlayıcı PASS üretilmedi.**
Sağlayıcı karışımı da ölçüldü: `wikimedia 2 / nasa 3` → tekel **%100 → %60**
(tavan %40 olduğu için WARN **dürüstçe sürüyor**).

### ⛔ PİLOT MP4 KABUL EDİLMİŞ SAYILMAZ — medya kümesi değişti ve KÖTÜLEŞTİ

Küme değiştiği için tam rerender + POST-QA + 11 kare yapıldı.
**Otomatik POST-QA PASS** (1920×1080, 17.109 sn, LUFS −14.36, TP −4.09,
sessizlik/siyah/donmuş 0, kenar 0/68, 5 ayrı hareket, puan 100/100).
**Ama 11 kare incelemesi kabul edilemez çıktı:**

s01 artık Commons'tan geliyor (`Pleiades supercomputer racks 4.jpg`,
2240×1344) ve bu görsel **cam arkasındaki bir müze afişinin fotoğrafı** —
İngilizce metin blokları, yansımalar, amatör kadraj. Türkçe anlatımlı bir
belgeselde "Güç burada üretilir" cümlesinin altında **İngilizce duvar panosu**
duruyor. `detay_std` 52.3 → 38.2.

### ⚠ ÖLÇÜMÜN AÇIĞA ÇIKARDIĞI GERÇEK KUSUR — "upscale YAPILMIYOR" İHLALİ

Yeni `punch_buyutme` **ölçümü** (kapı değil) eklendi. Zoom değerleri yeniden
türetilmiyor, **planın kendi motion spec'inden** okunuyor:

`ekran_piksel_orani = kapsama × maks_zoom`, `kapsama = max(1920/g, 1080/y)`

| beat | kaynak | kadraj | zoom | ekran oranı | |
|---|---|---|---|---|---|
| b001 | 2240×1344 | tam | 1.053 | 0.903 | küçültme |
| **b002** | **2240×1344** | **punch-1.35** | 1.494 | **1.281** | ⛔ **BÜYÜTME** |
| b003 | 3000×2000 | ust | 1.272 | 0.814 | küçültme |
| **b004** | **3000×2250** | **punch-1.6** | 1.696 | **1.085** | ⛔ **BÜYÜTME** |
| b005 | 4986×3744 | alt | 1.272 | 0.490 | küçültme |

**b004 ZATEN I-24/I-25'in kabul edilen render'ında da büyütüyordu (1.085×).**
Yani bu kusur I-26'nın ürettiği bir gerileme **değil**, atomun **açığa
çıkardığı mevcut bir ihlal**: depo "upscale YAPILMIYOR" diyor, ama bu söz
yalnızca **edinim eşiği** (`en_az_genislik=1920`) için geçerli; kamera
`punch` kadrajında **sessizce ihlal ediliyor**.

Testte **BLOKE** olarak duruyor; PASS sayılmadı.

### Ölçülen test sonucu

| Paket | A | B | C | D | E | F | G | H | I | Toplam |
|---|---|---|---|---|---|---|---|---|---|---|
| Zengin venv | 125 | 200 | 148 | 95 | 127 | 244 | 218 | 257 | **1563** | **2977** |

0 hata. Faz I 1546 → **1563** (+17). **1 BLOKE** (I-26 punch büyütme) —
sebebi ölçülmüş ve yazılı.

### Düzeltilen kendi kilidim

I-23b kilidi *"en az 1 ayırt reddi OLDU"* diye yazılmıştı; o sayı **aday
listesine bağlı** ve Commons/NASA karışımı değişince reddedilecek benzer çift
kalmayabiliyor. Asıl değişmez **"ayırt edilemez çift hayatta kalmadı"**;
kilit ona çevrildi (gevşetme değil, doğru değişmez).

### SONRAKİ ATOM (I-27) — net ve ölçülmüş

**Kadraj, kaynağın çözünürlük payına göre seçilmeli.** Doğru çözüm kaynağı
reddetmek DEĞİL (ölçüldü: `punch-1.6` için gereken ≥3254 px eşiği s02/s03'ü
de eler ve pilot tamamen bloke olur), **kadrajı kaynağa uydurmaktır**:
`kapsama × kadraj_ölçek ≤ 1.0` sağlayan en geniş kadraj deterministik
seçilir (I-24'ün geometri kancası bunun için hazır).
İkinci mesele: **konu dışı "afiş/pano fotoğrafı"** için ölçülebilir bir
eleme sinyali (metin yoğunluğu ölçümü) — uydurma değil, ölçülerek.

---

## 45. FAZ I-27 — KAMERA PUNCH'I KAYNAĞI BÜYÜTEMEZ (dar kalite atomu, 13 Ağu)

> **Durum: ÇÖZÜLDÜ. POST-QA TAMAMEN PASS, kalite puanı 100/100, Faz I BLOKE
> 0, push edildi. Deploy YOK. Maliyet $0.00.**
> Değişen: `webapp/editor/motion.py`, `webapp/editor/kalite_kapisi.py`,
> `webapp/editor/plan.py`, `webapp/editor/qa_on.py`,
> `webapp/testler/smoke_konsept3_teknoloji_i20.py`,
> `webapp/testler/test_faz_i.py`, `outputs/sample/teknoloji_i20_rapor.json`
> (+ handoff).
> **Blur/pillarbox/sentetik doldurma YOK. Rastgelelik YOK. Yeni
> sağlayıcı/ağ/kota/API/maliyet YOK.**
> `pipeline.py`, `server.py`, `deploy.sh`, 22 alan sözleşmesi, `gramer.py`,
> `beat.py`, `medya/*` (commons, edinim, nasa, lisans, guvenlik, indirme)
> **dokunulmadı** (git ile doğrulandı). I-23…I-26 kapıları **korundu**.

### ✅ I-26'NIN İKİ İHLALİ ÖNCE KIRMIZI GÖSTERİLDİ

| beat | kaynak | kadraj | maks zoom | ekran oranı | |
|---|---|---|---|---|---|
| b002 | 2240×1344 | punch-1.35 | 1.4944 | **1.281** | ⛔ |
| b004 | 3000×2250 | punch-1.6 | 1.696 | **1.085** | ⛔ (kabul edilen render'da DA) |

Testte bu iki değer **birebir sabitlendi** (`_IHLAL27`), yani kusur önce
**kırmızı** kanıtlandı, sonra düzeltildi.

### Çözüm 1 — deterministik kadraj merdiveni

`kapsama = max(1920/g, 1080/y)` (objectFit: cover), `ekran = kapsama × zoom`.
Oran > 1.0 ise plan, `motion.KADRAJ_MERDIVENI` içinden **büyütmeyen en dar**
kadraja geçer. Ölçülen sonuç:

- b002 `punch-1.35` → **`tam`** (1.281 → 0.949)
- b004 `punch-1.6` → **`punch-1.35`** (1.085 → 0.916) — **punch hissi korundu**

⚠ Yeni kadraj **uydurulmaz** (yalnız merdivendekiler), hareket/anlatı işlevi
**değişmez**, büyütmeyen kadraj **aynen korunur**, hiçbiri yetmezse kadraj
olduğu gibi bırakılır ve hükmü PRE-QA verir: **`KALITE-PUNCH-BUYUTME` (fail)**.
Kadraj ölçek tablosu `kamera_spec` içinde gömülüydü; **tek kaynağa**
(`motion.KADRAJ_OLCEK`) çıkarıldı ki plan ile render sessizce ayrışmasın.

### ⚠ Çözüm 1 İKİNCİ HALKAYI AÇIĞA ÇIKARDI — ölçülüp kapatıldı

İlk rerender **POST-QA FAIL** verdi: `POST-OPTIK-DURGUN`, b005 optik **1.415**
(eşik 2.0), 3.75 sn durağan. Kök neden ölçüldü: **pan sürüşüyle** hareket eden
çekimlerde zoom sabittir (1.06) ve tüm hareket pan'dan gelir; pan payı ise
`_guvenli_pay(zoom × kadraj_ölçek)`:

| kadraj | ölçek | pan payı |
|---|---|---|
| **tam** | 1.00 | **0.0255** ← hareket açlığı |
| ust/alt | 1.20 | **0.0962** ← ~4 katı |

Yani büyütmemek için kadrajı `tam`a çekmek, hareketi durağanlık eşiğinin
altına düşürebiliyor. **Kadrajı zorlamak çözüm değil**; kaynak en az bir
punch'ı taşımalı. Eşik **türetildi, uydurulmadı**:

```
en_az_genislik = kare_genislik × EN_DAR_PUNCH_OLCEGI(1.2) × PAN_TABANLI_ZOOM(1.06)
               = 1920 × 1.2 × 1.06 = 2443 px
```

Eski `1920` yalnızca `tam` kadrajı garanti ediyordu — yani **açlık kadrajını**.
Yeni eşik tam da sorunlu iki Commons kaynağını eliyor (2240 müze afişi,
2100 Columbia) ve iyi olanların hepsini geçiriyor (Commons Ohio 5184, NASA
3000/4192/4986).

### ✅ ÖLÇÜLEN ÖNCE → SONRA

| Ölçüm | I-26 | **I-27** |
|---|---|---|
| Büyüten beat | **2** | ✅ **0** |
| En yüksek ekran oranı | **1.281** | ✅ **0.916** |
| POST-QA | PASS (ama kabul edilmedi) | ✅ **PASS** |
| Optik durağanlık | temiz | ✅ **temiz** (5/5 beat hareketli) |
| Kalite puanı | 100/100 | ✅ **100/100** |
| s01 görseli | ⛔ cam arkası müze afişi | ✅ **NASA süperbilgisayar rafı** |
| b001 / b002 keskinlik | 5.47 / 5.37 | ✅ **15.74 / 19.60** (≈3×) |
| Faz I BLOKE | **1** | ✅ **0** |

### ✅ PİLOT TAM DOĞRULANDI

**ffprobe:** h264 **1920×1080** @30fps + aac 48 kHz/2ch, **17.109 sn**, 40.50 MB.
**Ses:** LUFS **−14.36**, TP **−4.09**, LRA 3.6, sessizlik **%0** (ince tarama
da boş). **Kesmeler:** 7. **Siyah/donmuş aralık:** yok. **Kenar:** 0/68.
**Optik:** genel 14.734, durgun ihlal 0 (40.9 / 5.4 / 8.2 / 14.1 / 4.0).
**Kareler:** **11 adet** incelendi; ayrıca hepsinde tam çözünürlükte dört
kenar ölçüldü — en koyu kenar **24.93** (siyah eşiği 16'nın üstünde).
**Semantik:** b002 "Güç burada üretilir" → NASA süperbilgisayar rafı;
b004 "silikon üzerindeki devreler" → NASA GRC silisyum karbür IC test kartı.
**Medya:** 4/4 **NASA**, fixture yok, maliyet **$0.00**.
**Punch:** 5/5 beat ölçüldü, **büyüten 0**, en yüksek **0.9158**.

### Ölçülen test sonucu

| Paket | A | B | C | D | E | F | G | H | I | Toplam |
|---|---|---|---|---|---|---|---|---|---|---|
| Zengin venv | 125 | 200 | 148 | 95 | 127 | 244 | 218 | 257 | **1604** | **3018** |

0 hata. Faz I 1563 → **1604** (+41). **Faz I BLOKE 1 → 0.**
Kalan tek BLOKE Faz H'deki `QA_TEST_VIDEO` (opsiyonel, I-22'den beri aynı).

### Düzeltilen kendi kilidim (I-23, I-26'dakiyle aynı sınıf)

I-23 kilidi *"en az 1 dikey red OLDU"* diyordu; o sayı **aday listesine
bağlı** ve I-27'nin yükseltilmiş çözünürlük eşiği dikey adayları **oran
kapısına varmadan** eliyor. Asıl değişmez **"kabul edilen hiçbir varlık
dikey/kare değil"**; kilit ona çevrildi (gevşetme değil, doğru değişmez).

### SONRAKİ ATOM (I-28 adayları)

- **Sağlayıcı tekeli** yine %100 `nasa`: yeni eşik (2443) Commons'ın alaka
  sırasındaki ilk adaylarını eliyor. Commons'ta **yüksek çözünürlüklü ve
  konuya sadık** aday var (Ohio OSC 5184×3456, alaka 2) — eşik **sonra**
  değil **arama sıralamasıyla birlikte** değerlendirilirse tekel gerçekten
  kırılabilir. Ölçülerek denenmeli.
  > ⚠ **I-28 DÜZELTMESİ — bu madde YANILTICIYDI.** "İlk adayları eliyor"
  > doğru ama eksik: **sıradaki** aday (Ohio OSC 5184×3456) eşiği geçiyor ve
  > **0. sırada seçiliyor**. I-28'de ölçüldü: 429 devre dışı bırakıldığında
  > zincir 4/4 sahnede Commons'tan konuya sadık aday seçiyor. Seçim/filtre
  > sırasında **kusur yok**; tekelin tek sebebi indirmedeki HTTP 429.
- **"Afiş/pano fotoğrafı"** için ölçülebilir eleme sinyali (metin yoğunluğu)
  — I-26'da gözle yakalandı, otomatik ölçümü yok.

---

## 46. FAZ I-28 — SEÇİM SIRASI TANISI: **KUSUR YOK**, DAVRANIŞ KİLİTLENDİ (13 Ağu)

> **Durum: öncül ÖLÇÜMLE ÇÜRÜDÜ. Üretim kodu DEĞİŞMEDİ; doğru davranış
> teste kilitlendi. Yerel yeşil (0 hata), push edildi. Deploy YOK.
> Maliyet $0.00.**
> Değişen: **yalnızca** `webapp/testler/test_faz_i.py` (+ handoff).
> `plan.py`, `qa_on.py`, `motion.py`, `kalite_kapisi.py`, `gramer.py`,
> `medya/*`, `pipeline.py`, `server.py`, `deploy.sh`, smoke betiği ve
> 22 alan sözleşmesi **dokunulmadı** (git ile doğrulandı).
> **Pilot yeniden üretilmedi**: medya kümesi ve render davranışı
> değişmediği için I-27'nin kabul edilmiş MP4'ü **korunuyor**.

### ⚠ ARANAN KUSUR YOK — ölçüm öncülü çürüttü

Beklenen kusur: *"2443 eşiği yüzünden konuya sadık yüksek çözünürlüklü
Ohio OSC (5184×3456) adayı seçilemiyor, tekel NASA %100 oluyor."*

Aynı **tek** `ara()` çağrısıyla ölçüldü (ek ağ/kota yok):

| sorgu | ham | elenen | kalan | **0. sıradaki aday** |
|---|---|---|---|---|
| `supercomputer facility` | 18 | 12 | 6 | **OSC's HP Intel Xeon Oakley Cluster 5184×3456** ✅ |
| `Pleiades supercomputer` | 18 | 13 | 5 | NASA Pleiades Supercomputer 4983×3303 ✅ |
| `silicon carbide integrated circuit` | 2 | 0 | 2 | Extremely durable silicon carbide semiconductor ✅ |
| `solar array power` | 18 | 6 | 6 | Solar array-2 ✅ |

Eşik gerçekten düşük çözünürlüklü **alaka-1** adayını (Columbia 2100×1524)
eliyor — ama **sıradaki** aday (Ohio OSC, alaka 2) eşiği geçiyor ve
**0. sırada seçiliyor**. Yani "sıradakine deterministik geçiş" **zaten
çalışıyor**.

### Uçtan uca kanıt — 429 devre dışı bırakılınca zincir Commons'ı seçiyor

Gerçek Commons araması + **sahte indirici** (429 yok) ile koşuldu:

| sahne | istenen | `ara()` | seçilen |
|---|---|---|---|
| s01 | 2 | **1** | NASA Pleiades Supercomputer + Pleiades supercomputer |
| s02 | 1 | **1** | **OSC's HP Intel Xeon Oakley Cluster** |
| s03 | 1 | **1** | Extremely durable silicon carbide semiconductor |
| s04 | 1 | **1** | Solar array-2 |

4/4 sahne Commons'tan **konuya sadık** aday seçti, sahne başına **tek**
arama çağrısı. **Seçim/filtre sırasında kusur yok.**

### Tekelin TEK sebebi — indirmedeki HTTP 429

Son pilot koşumunda Commons `metadata=5` üretti (yani eşikten geçen aday
**seçildi**), düşüş `BAYT-YOK / HTTP 429` ile oldu. Bu, I-18'den beri
belgeli **çevresel** koşul; devre kesici doğru davranıyor (600 sn
beklemiyor, NASA'ya geçiyor). **Sahte sağlayıcı çeşitliliği üretilmedi.**

### Havuz açlığı da yok

Eşik sertleşmesine rağmen kalan aday sayısı istenen adedin **üstünde**:
5≥2, 6≥1, 2≥1, 6≥1. Ham çekim derinliğini (`gsrlimit`) artırmak **ölçülen
bir fayda üretmiyordu**, bu yüzden **değiştirilmedi** — kanıtsız değişiklik
yapılmadı.

### Yapılan tek iş: doğru davranışı KİLİTLEMEK

Sahte API/aday listesiyle (ağ yok) kilitlendi:
- düşük çözünürlüklü alaka-1 aday **eşikte elenir**,
- sıradaki konuya sadık yüksek çözünürlüklü aday **0. sırada seçilir**,
- **semantik alaka birincil** kalır (konu dışı RC Lens futbol fotoğrafları
  arkada),
- lisans belirsiz ve eser sahibi eksik adaylar **geçmez**,
- I-23 oran kapısı dikey adayı **reddetmeye devam eder**,
- eşik I-27'den **türetilen** değere (2443) eşittir,
- **ek `ara()` çağrısı yoktur**.

### Bulunan ve düzeltilen kendi hatam

I-27'nin "SONRAKİ ATOM" notu *"yeni eşik Commons'ın alaka sırasındaki ilk
adaylarını eliyor"* diyordu. Doğru ama **eksik ve yanıltıcı**: sıradaki aday
eşiği geçiyor ve seçiliyor. Bu ifade I-28'in yanlış öncülle başlamasına yol
açtı; handoff'ta **düzeltme notu** olarak işaretlendi.

Ayrıca test fikstürümde `LicenseUrl` ezilmiyordu; yalnız kısa adı
değiştirmek lisans kararını yanıltıyordu (karar URL'den de lisans çıkarıyor).
Fikstür düzeltildi — **üretim kodunda kusur yoktu**.

### Ölçülen test sonucu

| Paket | A | B | C | D | E | F | G | H | I | Toplam |
|---|---|---|---|---|---|---|---|---|---|---|
| Zengin venv | 125 | 200 | 148 | 95 | 127 | 244 | 218 | 257 | **1616** | **3030** |

0 hata. Faz I 1604 → **1616** (+12). Faz I BLOKE **0**.
Kalan tek BLOKE Faz H'deki `QA_TEST_VIDEO` (opsiyonel, I-22'den beri aynı).

### SONRAKİ ATOM (I-29 adayları)

- **Sağlayıcı tekeli teknik olarak çözülemez durumda:** Commons'ın 429'u
  host/IP kaynaklı ve `Retry-After: 600`. Gerçek seçenekler — 429 penceresi
  dışında edinim ya da farklı bir kamu malı sağlayıcı — **kullanıcı
  kararıdır**, mühendislik kusuru değil.
- **"Afiş/pano fotoğrafı"** için ölçülebilir eleme sinyali (metin yoğunluğu)
  — I-26'da gözle yakalandı, otomatik ölçümü hâlâ yok. Tek gerçek açık kalite
  kapısı bu.

---

## 47. FAZ I-29 — AFİŞ/PANO SİNYALİ: METADATA **GÜVENİLİR DEĞİL** (13 Ağu)

> **Durum: ölçüm tamamlandı, sinyal ELENDİ. Üretim davranışı DEĞİŞMEDİ;
> ölçüm ve gerekçe teste kilitlendi. Yerel yeşil (0 hata), push edildi.
> Deploy YOK. Maliyet $0.00.**
> Değişen: **yalnızca** `webapp/testler/test_faz_i.py` (+ handoff).
> `medya/*`, `editor/*`, `pipeline.py`, `server.py`, `deploy.sh`, smoke
> betiği ve 22 alan sözleşmesi **dokunulmadı** (git ile doğrulandı).
> **Pilot yeniden üretilmedi**: medya/render davranışı değişmediği için
> I-27'nin kabul edilmiş MP4'ü **korunuyor**.

### Sorulan soru

I-26'da **gözle** yakalanan kusur: s01'e seçilen Commons varlığı **cam
arkası bir müze panosunun** fotoğrafıydı. I-29: bu, aday **metadatasından**
(başlık / açıklama / kategori / provenance) deterministik yakalanabilir mi?

⚠ Ölçüm **bedava**: `commons.ara` zaten `iiprop=…|extmetadata` istiyor, yani
tüm alanlar **aynı çağrıda** geliyor; yalnızca 5'i çıkarılıyor. Ek ağ/kota
çağrısı yapılmadı.

### Ölçüm 1 — anahtar kelime sinyali: **recall 0/1**

Kusurlu varlığın gerçek metadatası:

| alan | değer |
|---|---|
| ObjectName | `Pleiades supercomputer racks 4` |
| ImageDescription | `Pleiades supercomputer racks` |
| Categories | `Taken with LG Ultimate 2 \| Pleiades supercomputer \| Self-published work` |

**Hiçbir yerde** display / exhibit / museum / poster / signage geçmiyor.
Yükleyici fotoğrafı **konunun kendisi** gibi tanıtmış. Yani sinyal, gerçek
kusuru **hiç yakalamıyor**.

Aynı desen 4 pilot sorgusunun **56 adayında** koşuldu:

| ölçüm | sonuç |
|---|---|
| Taranan aday | 56 |
| İşaretlenen | **7 (%12)** |
| **Gerçek kusur yakalandı mı** | ❌ **HAYIR** |

İşaretlenenler arasında net **yanlış pozitifler** var:
- `NASA Advanced Supercomputing Facility **with sign**` — meşru tesis fotoğrafı
- `NASA's Roman Mission… the telescope **displays** its first image` — fiil
- `Solar array, Guilford, Vermont` — `**Banner** images` kategorisi

⚠ İlk denememde desen `sign\b` idi ve **"design"i** yakalıyordu; bu **benim
regex hatamdı**. Kelime sınırları düzeltilip yeniden ölçüldü — yukarıdaki
sayılar düzeltilmiş desenin sonucudur.

### Ölçüm 2 — `Taken with <cihaz>` sinyali: **hassasiyet %6**

Kusurluda göze çarpan tek fark bu kategoriydi. Ölçüldü:

| ölçüm | sonuç |
|---|---|
| Bu kategoriyi taşıyan aday | **18 / 56** |
| Gerçek kusur yakalandı mı | ✅ evet |
| Elenecek **temiz** aday | **17** |
| **Hassasiyet** | **≈ %6** |

Eleyeceği temiz adaylar arasında `Pleiades supercomputer.jpg` (3072 px —
I-28 kanıtında **s01 için seçilen** adaylardan biri), `OHSupercomputer`
(3488 px) ve `Pleiades supercomputer node on display at NASA Ames`
(3410 px) var. Bu sinyal "pano fotoğrafı"nı değil **"telefonla çekilmiş"i**
ölçüyor — kapı olamaz.

### ⛔ HÜKÜM: sinyal güvenilir değil → üretim davranışı DEĞİŞMEDİ

- Anahtar kelime: **%0 recall** (kusuru kaçırıyor) + meşru varlıkları eliyor.
- Kamera kategorisi: **%6 hassasiyet** (17 temiz adayı eliyor).

İkisi de kapıya dönüştürülemez. Kullanıcı talimatı gereği **üretim kodu
değiştirilmedi**; ölçüm ve gerekçe teste kilitlendi. Ayrıca dört üretim
dosyasına (`commons.py`, `edinim.py`, `qa_on.py`, `plan.py`) **böyle bir
anahtar-kelime kapısı EKLENMEDİĞİNİ** doğrulayan koruma testi kondu — ileride
kanıtsız eklenmesin.

### ✅ Yan bulgu: kusur sınıfı zaten kapalı

Kusurlu varlık **2240 px**; I-27'nin türetilmiş eşiği **2443 px**. Yani bu
somut vaka **I-27 çözünürlük/geometri kapısıyla zaten eleniyor** — semantik
sinyalle değil, ama ölçülebilir ve deterministik biçimde. Testte kilitlendi.

### Ölçülen test sonucu

| Paket | A | B | C | D | E | F | G | H | I | Toplam |
|---|---|---|---|---|---|---|---|---|---|---|
| Zengin venv | 125 | 200 | 148 | 95 | 127 | 244 | 218 | 257 | **1630** | **3044** |

0 hata. Faz I 1616 → **1630** (+14). Faz I BLOKE **0**.
Kalan tek BLOKE Faz H'deki `QA_TEST_VIDEO` (opsiyonel, I-22'den beri aynı).

### SONRAKİ ATOM (I-30 adayları)

- **Afiş/pano tespiti metadata ile ÇÖZÜLEMEZ** (ölçüldü). Gerçek çözüm
  **kare-bakan** bir sinyal olurdu (ör. yüksek metin/kenar yoğunluğu, düz
  dikdörtgen bölge sayımı) — bu, `medya.edinim`in `kapsam_disi` listesinde
  açıkça **kapsam dışı** yazan "kare-bakan içerik doğrulaması"dır. Yeni bir
  yetenek; **kullanıcı kararı**.
- **Sağlayıcı tekeli** teknik olarak çözülmüş durumda değil ama **mühendislik
  kusuru da değil**: Commons 429'u host/IP kaynaklı (I-28'de kanıtlandı).

---

## 48. FAZ I-30 — YATAY GÜVENLİ ALAN: SAĞ/SOL TAŞMA ÖLÇÜLMÜYORDU (13 Ağu)

> **Durum: boşluk kapatıldı. Yerel yeşil (0 hata), push edildi. Deploy YOK.
> Maliyet $0.00.**
> Değişen: `webapp/editor/kalite_kapisi.py`, `webapp/editor/qa_on.py`,
> `webapp/testler/test_faz_i.py` (+ handoff).
> **OCR / harici servis / ağ / API YOK.**
> `plan.py`, `motion.py`, `gramer.py`, `medya/*`, `pipeline.py`, `server.py`,
> `deploy.sh`, smoke betiği, `Grafikler.tsx` ve 22 alan sözleşmesi
> **dokunulmadı** (git ile doğrulandı). I-23…I-29 kapıları **korundu**.
> **Pilot yeniden üretilmedi**: kapı mevcut pilotta **ateşlemiyor**, render
> davranışı değişmedi → I-27'nin kabul edilmiş MP4'ü **korunuyor**.

### Önce elenen aday: altyazı/çakışma zaten sağlam

`yazi_cakismasi` incelendi: çakışma **zaman VE dikey** kesişimi birlikte
arıyor — yani zaman-farkındalıklı ve doğru. Pilot raporundaki
`TIPO-CAKISMA-DUSURULDU … "cozulemedi"` uyarısı ile ölçümün `temiz: true`
demesi çelişkili görünüyordu; ölçüldü: **ölçüm haklı**. `source-label` #2
(815.4–864.0 px) ile `chapter-title` (756–869.4 px) dikeyde kesişiyor ama
**zamanda kesişmiyor**. Uyarı bir **yanlış alarm**; düzen gerçekten temiz.
Bu yüzden oraya dokunulmadı.

### ⛔ Bulunan gerçek boşluk: YATAY hiç ölçülmüyordu

`guvenli_alan_olcusu` yalnızca `y_ust` / `yukseklik` okuyor — **sağ/sol
taşma hiç ölçülmüyordu**. Risk yapısal ve somut:

| bileşen | genişlik sınırı |
|---|---|
| `BolumBasligi` (başlık) | `maxWidth: '84%'` ✅ |
| altyazı bandı | `maxWidth: 900` ✅ |
| **`KaynakEtiketi` (künye)** | **YOK** ⛔ |

`KaynakEtiketi` `position:absolute; right: GUVENLI_KENAR` ile sağa yaslanıyor
ve genişlik sınırı taşımıyor → uzun bir atıf **sola doğru sınırsız** büyür.
Bu teorik değil: pilotun **kendi aday havuzundaki** "Pleiades large.jpg"
(yıldız kümesi) atfı **155 karakter**.

### Genişlik modeli — uydurma değil, render'ın kendi sabiti

`Grafikler.tsx:67` genişlik tahminini `uzunluk × punto × (0.72 + 0.01)` ile
yapıyor. Künyenin harf aralığı 0.01 değil **0.04** (`Grafikler.tsx:205`),
bu yüzden künye için `EM_BUYUK_HARF + 0.04 = 0.76` alındı.

⚠ **DÜRÜST SINIR:** bu model **büyük harf** için türetilmiş; künye **karışık
harf**. Render karesinden doğrudan ölçmeyi denedim ve **güvenilir çıkmadı**
— düşük opaklıktaki (0.62) yazı değişken foto zemininde eşikle ayrılamıyor;
örnekler **0.003 – 0.769** arasında savruldu. Yalnız **kendi kendini
doğrulayan** tek örnek (t=5.99, ölçülen sağ kenar **1854** ≈ beklenen
**1856**) **0.769** verdi ve bu, render'ın belgeli **0.76** sabitiyle **%1
içinde örtüşüyor**. Model bu tek doğrulamaya dayanır; daha iyi bir ölçüm
çıkarsa `KUNYE_HARF_ARALIGI_EM` bloğu güncellenmeli.

### Eklenen: `yatay_guvenli_alan_olcusu` + PRE-QA kapısı

Saf fonksiyon; ağ/dosya kullanmaz. Ölçüm **plan verisinden** (metin uzunluğu
+ punto + kare genişliği), OCR yok. Ölçülemeyen katman **engellenmez**.
İhlal `KALITE-GUVENLI-ALAN` **fail** olarak PRE-QA'da hüküm verir.

⚠ Öneri metni **lisans riskini açıkça söylüyor**: *"kırpma LİSANS ATFINI
eksiltebilir — önce atıf politikasına bak."* Sessiz kırpma **önerilmiyor**;
CC BY atfını kısaltmak bir hukuk kararı, mühendislik kararı değil.

### ✅ Ölçülen sonuç — kırmızı vaka kırmızı, gerçek pilot temiz

| katman | karakter | punto | tahmini | kullanılabilir | |
|---|---|---|---|---|---|
| `chapter-title` "GÜÇ" | 3 | 60 | 136.8 px | 1792 px | temiz |
| `source-label` | 26 | 21 | 415.0 px | 1792 px | temiz |
| `source-label` | 17 | 21 | 271.3 px | 1792 px | temiz |
| `source-label` | 46 | 21 | 734.2 px | 1792 px | temiz |
| **sentetik: gerçek 155 karakterlik atıf** | 155 | 21 | **2473.8 px** | 1792 px | ⛔ **TAŞMA** |

Karakter tavanı (punto 21): **112**. Pilotun en uzunu 46 → **2.4× pay**.
Kapı pilotta **ateşlemiyor** → PRE-QA hükmü ve render davranışı **değişmedi**.

### Ölçülen test sonucu

| Paket | A | B | C | D | E | F | G | H | I | Toplam |
|---|---|---|---|---|---|---|---|---|---|---|
| Zengin venv | 125 | 200 | 148 | 95 | 127 | 244 | 218 | 257 | **1644** | **3058** |

0 hata. Faz I 1630 → **1644** (+14). Faz I BLOKE **0**.
Kalan tek BLOKE Faz H'deki `QA_TEST_VIDEO` (opsiyonel, I-22'den beri aynı).

### SONRAKİ ATOM (I-31 adayları)

- **`KaynakEtiketi`'ne genişlik sınırı vermek** artık kapıyla *görünür* ama
  **çözülmedi**: `maxWidth` + sarma, künyeyi ikinci satıra taşırıp dikey
  planı bozar; `nowrap` + kırpma ise **atfı eksiltir**. Doğru çözüm bir
  **atıf politikası** kararı gerektirir (ör. "eser sahibi + lisans" kısa
  biçimi) — **kullanıcı kararı**.
- **Afiş/pano tespiti** (I-29): metadata ile çözülemez, kare-bakan sinyal
  gerekir; `medya.edinim`'in `kapsam_disi` listesinde açıkça kapsam dışı.

---

## 49. FAZ I-31 — EKRAN KÜNYESİ POLİTİKASI: ATIF EKSİLMEDEN SIĞDIRMA (13 Ağu)

> **Durum: atom ÇÖZÜLDÜ ve yeşil, ama pilot MP4 ⛔ KABUL EDİLMİŞ SAYILMAZ.
> Yerel yeşil (0 hata, 1 BLOKE), push edildi. Deploy YOK. Maliyet $0.00.**
> Değişen: `webapp/editor/kalite_kapisi.py`, `webapp/editor/plan.py`,
> `webapp/editor/qa_on.py`, `webapp/testler/test_faz_c.py`,
> `webapp/testler/test_faz_i.py`, `outputs/sample/teknoloji_i20_rapor.json`
> (+ handoff).
> `medya/*`, `motion.py`, `gramer.py`, `pipeline.py`, `server.py`,
> `deploy.sh`, `Grafikler.tsx`, smoke betiği ve 22 alan sözleşmesi
> **dokunulmadı** (git ile doğrulandı). I-23…I-30 kapıları **korundu**.

### Politika — deterministik ve açıklanabilir

**Ekranda** yalnızca `eser sahibi / LİSANS KISA ADI`.
**Tam eser adı, kaynak URL, lisans ve provenance** `lisans.atif_metni`
çıktısında ve `attribution.txt`te **eksiksiz** kalır — ekran künyesi bir
**özet**tir, atfın yerine geçmez.

Sıralı çözüm (rastgelelik yok):
1. **TAM** biçim sığıyorsa aynen kullanılır (kullanıcı seçimi korunur).
2. **KURUM**: sahip alanı kendi ayraçlarından (`,` `;` `/` `|` ` - ` ` — `)
   bölünür, **birinci** parça alınır. Uydurma değil, metnin kendi ilk öğesi.
3. **KIRPMA**: kurum adı kelime sınırında kırpılır + `…`.

⚠ **LİSANS KISA ADI HİÇBİR ADIMDA KIRPILMAZ.** Lisans tek başına bile
sığmıyorsa metin **üretilmez** ve hükmü PRE-QA verir.
⚠ **SAHİP/LİSANS BOŞSA UYDURULMAZ**: `eksik=True` döner, yeni
`KALITE-KUNYE-EKSIK` (fail) kapısı **dürüstçe BLOKE** eder. Önceki davranış
künyeyi **sessizce atlıyordu** — atıf yükümlülüğü görünmeden düşüyordu.

### ✅ I-30'un 155 karakterlik taşması çözüldü

| girdi | önce | **sonra** | yatay kapı |
|---|---|---|---|
| 155 karakterlik gerçek atıf | **2473.8 px > 1792 px** ⛔ | `NASA / PUBLIC-DOMAIN` (**KURUM**) | ✅ **PASS** |
| `Dominic Hart` | — | aynen (**TAM**) | ✅ |
| `GRC` | — | aynen (**TAM**) | ✅ |
| `NASA/JPL-Caltech/Lockheed Martin` | — | aynen (**TAM**) | ✅ |

Pilotun **hiçbir künyesi değişmedi** (`yontemler: ["TAM"]`, kısaltılan **0**)
— politika yalnızca patolojik girdide devreye giriyor.

### ✅ Tam provenance eksilmedi — ölçüldü

`attribution.txt` her varlık için **tam eser adı + sahip + lisans + URL**
taşımaya devam ediyor; ekran künyesi kısalsa da bu satır kısalmıyor.
Künye kararları (`kunye_kararlari`) manifeste yazılıyor: kısaltıldıysa
**tam sahip adı** da orada duruyor (izlenebilirlik).

### ✅ Render doğrulaması — POST-QA PASS

**ffprobe:** h264 **1920×1080** @30 + aac 48 kHz/2ch, **17.109 sn**, 39.62 MB.
**Ses:** LUFS **−14.36**, TP **−4.09**, sessizlik **%0** (ince tarama da boş).
**Kesmeler:** 6. **Siyah/donmuş:** yok. **Kenar:** 0/68. **Kareler:** 11.
**Tipografi:** güvenli alan ✅, **yatay güvenli alan ✅**, çakışma ✅, altyazı ✅.
**Künye→varlık eşlemesi doğru:** b001 Commons varlığını taşıyor ve künyesi
`Oleg Alexandrov / CC-BY-SA` — yanlış atıf **yok**.
**Kalite puanı:** 100/100.

### ⛔ MP4 KABUL EDİLMİŞ SAYILMAZ — açılış planı kusurlu

Medya kümesi yine kaydı (Commons bu koşumda servis etti) ve **b001'e**
`Pleiades supercomputer node on display at NASA Ames visitor center`
(3410×2634) seçildi. Bu **cam arkası bir müze vitrini**: İngilizce bilgi
panoları, yansımalar. Türkçe *"Güç burada üretilir."* anlatımının altında
**İngilizce açıklama panosu** duruyor. I-26/I-29'da tanımlanan sınıfın
aynısı; 3410 px olduğu için I-27 eşiğine **takılmıyor**, I-29'da ölçüldüğü
gibi metadata da yakalayamıyor.

⚠ Bu **I-31'in ürettiği bir gerileme değil** — künye politikası yalnızca
metni etkiler. Ama bu render'da olduğu için **kabul edilmiyor**.

### ⚠ I-31'DE BULUNAN İKİNCİ KUSUR — kare örnekleme KÖR NOKTASI

Kusurlu açılışı **11 kare göremedi**: ilk örnek **1.2 sn**, oysa **b001
0–0.862 sn**. Yani zorunlu görsel/semantik inceleme **açılış planını hiç
örneklemiyordu**; kusuru ancak **elle** kare çıkararak yakaladım.
Teste **beat kapsama kontrolü** eklendi ve şu an **BLOKE** yazıyor:
`ornekleNMEDI: ['b001']`.

### Ölçülen test sonucu

| Paket | A | B | C | D | E | F | G | H | I | Toplam |
|---|---|---|---|---|---|---|---|---|---|---|
| Zengin venv | 125 | 200 | 148 | 95 | 127 | 244 | 218 | 257 | **1662** | **3076** |

0 hata. Faz I 1644 → **1662** (+18). **1 BLOKE** (kare örnekleme kör noktası).

### Düzeltilen kendi hatalarım

- `_yazi_katmanlari_kur` artık **üç** değer dönüyor; `test_faz_c.py`'deki
  çağrı kırılmıştı (`too many values to unpack`) — güncellendi.
- Test fikstürümde `public-domain` kullanmıştım; o lisans **zaten atıf
  gerektirmiyor** (`LISANS_KURALLARI`), tam-atıf kanıtı `cc-by` ile kuruldu.

### SONRAKİ ATOM (I-32 adayları)

1. **Kare örnekleme her beat'i kapsamalı** — küçük, deterministik, bedava;
   BLOKE'yi kapatır ve görsel incelemenin kör noktasını yok eder.
2. **Vitrin/pano tespiti** hâlâ açık: I-29'da metadata ile çözülemeyeceği
   ölçüldü; kare-bakan sinyal gerekir ve `medya.edinim`'de açıkça kapsam
   dışı — **kullanıcı kararı**.

---

## 50. FAZ I-32 — KARE ÖRNEKLEME HER BEAT'İ KAPSIYOR (13 Ağu)

> **Durum: I-31'in BLOKE'sinin kök nedeni çözüldü. Yerel yeşil
> (0 hata, 1 BLOKE — kanıt), push edildi. Deploy YOK. Maliyet $0.00.**
> Değişen: `webapp/editor/kalite_kapisi.py`,
> `webapp/testler/smoke_konsept3_teknoloji_i20.py`,
> `webapp/testler/test_faz_i.py` (+ handoff).
> **Pilot YENİDEN RENDER EDİLMEDİ** (talimat gereği): atom yalnızca QA
> örnekleme/rapor davranışını değiştiriyor; render/medya seçimi aynı.
> `plan.py`, `qa_on.py`, `motion.py`, `gramer.py`, `medya/*`, `pipeline.py`,
> `server.py`, `deploy.sh`, `Grafikler.tsx`, pilot raporu ve 22 alan
> sözleşmesi **dokunulmadı** (git ile doğrulandı). I-23…I-31 **korundu**.

### ⛔ Kök neden — örnekleme BEAT'e değil CÜMLEYE bakıyordu

Kare seçimi `for c in cumleler` üzerinden "sahne ortası" hesaplıyordu.
Pilotta **4 cümle ama 5 beat** var: `s001` cümlesi 2.587 sn olduğu için
ortası **1.29**'a düşüyor — yani **b002'nin içine**. Sonuç: **b001
(0–0.862 sn) hiçbir kareyle örneklenmiyordu**. Üstelik yakınlık elemesi
(`>= 0.35 sn`) bir beat'in **tek** temsilcisini de düşürebiliyordu.

### ✅ Kanıt — I-31 pilotunun GERÇEK zaman çizgisinde

| beat | aralık | ESKİ kare | **YENİ kare** |
|---|---|---|---|
| **b001** | 0.000–0.862 | ⛔ **YOK** | ✅ **0.4333** |
| b002 | 0.862–2.587 | 1.2, 1.71 | 1.3, 1.7333, 2.4333 |
| b003 | 2.587–7.325 | 3.76, 4.96, 5.99 | 3.7667, 4.9667, 6.1333 |
| b004 | 7.325–12.225 | 8.21, 9.78, 10.27 | 8.5333, 9.7667, 11.0 |
| b005 | 12.225–17.050 | 12.32, 14.54, 16.25 | 14.6333 |

Eski: **11 kare, kapsanmayan `['b001']`**.
Yeni: **11 kare, kapsanmayan `[]`, `yeterli=True`**.
⚠ Yeni kapı I-31'in **mevcut kusurlu raporunu** hâlâ görünür biçimde
**BLOKE ediyor** (`ornekleNMEDI: ['b001']`) — yani kapı gerçekten çalışıyor
ve kusuru gizlemiyor.

### Planlayıcının sözleşmesi

- Her beat'e **zorunlu** bir temsil karesi; zorunlular yakınlık elemesiyle
  **asla düşürülmez** (sessiz atlama yok).
- Zamanlar **FPS ızgarasına** oturur ve beat sınırından **yarım kare**
  (`epsilon = 0.5/fps = 0.01667 sn @30fps`) içeride tutulur → **komşu
  beat'e taşma yok** (testle beat-beat doğrulandı).
- Hedef `max(11, beat_sayısı)`: **beat sayısı 11'i aşarsa kare sayısı
  ölçülü olarak yükselir** (12 beat → 12 kare, kapsanmayan `[]`).
- Dolgu kareleri zaman çizgisine deterministik dağıtılır ve **bir beat'in
  içinde** kalır. Rastgelelik **yok** (5 koşum → aynı plan).
- Beat yarım kareden kısaysa dürüstçe `kapsanmayan`a yazılır — uydurma yok.
- **beat↔kare eşlemesi rapora yazılıyor** (`kare_ornekleme`).

### Ölçülen test sonucu

| Paket | A | B | C | D | E | F | G | H | I | Toplam |
|---|---|---|---|---|---|---|---|---|---|---|
| Zengin venv | 125 | 200 | 148 | 95 | 127 | 244 | 218 | 257 | **1684** | **3098** |

0 hata. Faz I 1662 → **1684** (+22). **1 BLOKE** — I-31 pilotunun eski
kareleri b001'i kapsamıyor; bu **kanıt**, kapı doğru çalışıyor.

Test edilen senaryolar: 0.862 sn açılış · 0.4 sn kapanış · 5 beat/11 kare ·
12 beat → 12 kare · sınır karesi komşu beat'e taşmıyor · determinizm ·
bozuk girdi.

### Düzeltilen kendi hatam

"Kare zamanları FPS ızgarasında" iddiasını ondalık **eşitlik** olarak
yazmıştım; rapor okunabilirliği için 4 haneye yuvarlama ızgaradan en fazla
**0.00005 sn** saptırıyor — yarım karenin **binde biri**. İddia ölçülen
özelliğe (ızgaraya oturma) çevrildi.

### SONRAKİ ATOM (I-33) — ölçülen sonuçtan

**Pilotu yeni örneklemeyle yeniden üret ve b001'i gözle incele.** BLOKE
ancak yeni kareler üretilince kapanır. Beklenen sonuç ikiden biri:
1. Medya kümesi yine kayar ve b001 temiz bir varlık alır → MP4 kabul
   edilebilir;
2. b001 yine **vitrin/pano** sınıfı bir varlık alır → bu kez **11 kare
   içinde görünür** ve kusur ölçülebilir biçimde belgelenir.

İkinci durumda sıra, I-29'da metadata ile çözülemeyeceği ölçülen
**vitrin/pano tespitine** gelir; o **kare-bakan** bir sinyal gerektirir ve
`medya.edinim`'de açıkça kapsam dışıdır — **kullanıcı kararı**.

---

## 51. FAZ I-33 — GERÇEK KOŞUM DOĞRULAMASI: KARE PLANI KANITLANDI, MP4 ⛔ BLOKE (13 Ağu)

> **Durum: I-32'nin kare planı GERÇEK koşumda kanıtlandı. Otomatik kapıların
> HEPSİ PASS, ama bağımsız görsel inceleme kusuru buldu → MP4 KABUL
> EDİLMİŞ SAYILMAZ. Deploy YOK. Maliyet $0.00.**
> Değişen: `webapp/testler/test_faz_i.py`,
> `outputs/sample/teknoloji_i20_rapor.json` (+ handoff).
> **Medya/algoritma kodu DEĞİŞMEDİ** (talimat gereği): `kalite_kapisi.py`,
> `plan.py`, `qa_on.py`, `medya/*` ve smoke betiği git ile doğrulandı.
> Sağlayıcı/ağ bütçesi artmadı, ücretli API **$0**, anahtar/kredi değişikliği
> yok.

### ✅ I-32 kare planı GERÇEK koşumda çalıştı

| beat | aralık | **temsil karesi** | taşma |
|---|---|---|---|
| **b001** | 0.000–0.862 | ✅ **0.4333** | yok |
| b002 | 0.862–2.587 | 1.3, 1.7333, 2.4333 | yok |
| b003 | 2.587–7.325 | 3.7667, 4.9667, 6.1333 | yok |
| b004 | 7.325–12.225 | 8.5333, 9.7667, 11.0 | yok |
| b005 | 12.225–17.050 | 14.6333 | yok |

`kare=11`, `beat=5`, `hedef=11`, **`kapsanmayan=[]`**, `yeterli=True`.
I-31'de kör noktada kalan **b001 artık zorunlu incelemenin içinde** —
kusur elle kare çıkarmaya gerek kalmadan görüldü.

### ✅ Otomatik ölçümlerin hepsi PASS

**ffprobe:** h264 **1920×1080** @30 + aac 48 kHz/2ch, **17.109 sn**, 39.62 MB.
**Ses:** LUFS **−14.36**, TP **−4.09**, LRA 3.6, sessizlik **%0** (ince tarama
da boş). **Kesmeler:** 6. **Siyah/donmuş aralık:** yok. **Kenar:** 0/68;
11 karenin tam çözünürlükte dört kenarı ayrı ölçüldü, en koyu **24.96**
(eşik 16). **Optik:** genel 14.41, durgun ihlal 0.
**Tipografi:** güvenli alan ✅ · yatay güvenli alan ✅ · çakışma ✅ · altyazı ✅.
**Künye:** 5 karar, hepsi `TAM`, politika temiz; künye→varlık eşlemesi doğru.
**Motion:** 5 benzersiz hareket, işlev tekrarı 0, açılış≠kapanış, punch temiz.
**Medya tekrarı:** eşiği aşan çift yok. **POST-QA: PASS**, puan **100/100**.

### ⛔ BAĞIMSIZ GÖRSEL İNCELEME — kusur bulundu

| alan | değer |
|---|---|
| kare zamanı | **0.4333 sn** |
| beat | **b001** |
| varlık | `s01_11066148` |
| sağlayıcı / lisans | `wikimedia` / `cc-by-sa` |
| başlık | `Pleiades supercomputer node on display at NASA Ames visitor center…` |
| ölçü | 3410×2634 |

Kare **cam arkası bir müze vitrini**: *"The Pleiades Supercomputer"* ve
*"Anatomy of a Pleiades Node"* İngilizce bilgi panoları, cam yansımaları.
Türkçe anlatım *"Güç burada üretilir."* ve Türkçe **GÜÇ** başlığı, İngilizce
açıklama panosunun üstünde duruyor — **anlatıyla uyumsuz**.

⚠ **Otomatik kapıların hepsi PASS verdi**; kusur yalnızca görsel incelemede
görünüyor. Bu, I-29'da ölçülen boşluğun aynısı: metadata anahtar kelimesi
genel bir kapı olamaz (gerçek kusurda recall **%0**, 7 işaretten 5'i yanlış
pozitif). Bu yüzden **sınıflandırıcı eklenmedi**; teste yalnızca **bu ölçülen
varlığa özgü, izlenebilir bir kayıt** kondu — medya değişince kayıt
kendiliğinden düşer ve yeni varlık **yeniden incelenmek zorunda kalır**.

**MP4 KABUL EDİLMİŞ SAYILMAZ. Deploy YOK. Kabul edilmiş mutlak MP4 yolu
raporlanmıyor.**

### Ölçülen test sonucu

| Paket | A | B | C | D | E | F | G | H | I | Toplam |
|---|---|---|---|---|---|---|---|---|---|---|
| Zengin venv | 125 | 200 | 148 | 95 | 127 | 244 | 218 | 257 | **1685** | **3099** |

0 hata. Faz I 1684 → **1685**. **1 BLOKE** — I-33 görsel inceleme kaydı.

### ⚠ Ölçülen yan bulgu: sağlayıcı tekeli %100 değil %80

Commons bu koşumda **b001'i** verdi (`meta=5`, bayt geldi), gerisi 429 →
NASA. Yani karışım `wikimedia 1 / nasa 4` = **%80** (tavan %40, WARN sürüyor).
Commons'ın verdiği tek varlık **vitrin fotoğrafı** çıktı.

### SONRAKİ ATOM (I-34) — yalnız ölçülen kusurdan

**Vitrin/pano/dolaylı-medya tespiti artık tek gerçek açık kusur.** İki kez
üst üste (I-31, I-33) **aynı Commons varlığı** b001'e düştü ve her ikisinde
de tüm otomatik kapıları geçti. Ölçülen kısıtlar:

- **Metadata ile çözülemez** (I-29: recall %0, hassasiyet %6).
- **Çözünürlük/oran/punch kapıları görmüyor** (3410×2634, oran 1.294 — hepsi
  temiz).
- Gerçek çözüm **kare-bakan** bir sinyal: cam yansıması / yüksek yoğunluklu
  düz metin bloğu / dikdörtgen pano sayımı. Bu, `medya.edinim`'in
  `kapsam_disi` listesinde **açıkça kapsam dışı** yazan "kare-bakan içerik
  doğrulaması"dır — yeni bir yetenek ve **kullanıcı kararı**.

En küçük ölçülebilir ilk adım önerisi: **indirilen görselde metin yoğunluğu
ölçümü** (ffmpeg kenar/gradyan istatistiği ile, OCR'sız, ağsız) ve bunun
kusurlu varlık ile kabul edilen NASA varlıkları üzerinde **recall/hassasiyet
ölçümü** — I-29'daki disiplinin aynısı. Güvenilir çıkarsa kapı, çıkmazsa
dürüstçe elenir.

---

## 52. FAZ I-34 — VİTRİN/PANO KARE-BAKAN SİNYAL: **ELENDİ** (yalnız tanısal, 13 Ağu)

> **Durum: sinyal ÖLÇÜLDÜ ve ELENDİ. Üretim kodu DEĞİŞMEDİ; ölçüm ve gerekçe
> teste kilitlendi. Yerel yeşil (0 hata, 1 BLOKE — I-33 kaydı sürüyor),
> push edildi. Rerender YOK, deploy YOK. Maliyet $0.00.**
> Değişen: **yalnızca** `webapp/testler/test_faz_i.py` (+ handoff).
> `medya/*`, `editor/*`, smoke betiği, pilot raporu ve 22 alan sözleşmesi
> **dokunulmadı** (git ile doğrulandı). I-23…I-33 **korundu**.
> Yeni sağlayıcı/ağ/ücretli API **yok**; ölçüm yalnız yerel `ffmpeg` +
> saf Python ile yapıldı (`numpy`/`cv2`/`scipy` **yok**, OCR **yok**).

### Kurulan küme

**Pozitif (1 varlık):** `s01_..._2.jpg` — 3410×2634, `wikimedia`, `cc-by-sa`,
*"Pleiades supercomputer node on display at NASA Ames visitor center"*
(I-31 ve I-33'te **iki kez** b001'e düşen cam arkası müze vitrini).
**Negatif (6 varlık):** I-27/I-33'te semantik olarak kabul edilen NASA
varlıkları (rack, facility, chip, solar) + kapı elemeli ama semantik temiz
olanlar (dikey s02, düşük çözünürlüklü s04).
**Varyantlar (4):** `tam` · `merkez70` · `sol50` · `ust50`
→ **28 ölçüm** (4 pozitif + 24 negatif varyant).

### Ölçülen sinyaller (hepsi ffmpeg + saf Python)

`S1` metin satırı yoğunluğu · `S2` `edgedetect` kenar oranı ·
`S3` düz-parlak pano koşuları · `S4` specular (cam yansıması vekili).

| varlık | S1 | S2 | S3 | S4 |
|---|---|---|---|---|
| **POZ vitrin** | **0.0000–0.2083** | 0.0396–0.0688 | 0.0455–0.1873 | 0.0003–0.0104 |
| NEG s01 rack | 0.0000–0.0000 | 0.0523–0.0661 | 0.0000–0.0131 | 0.0006–0.0013 |
| NEG s03 chip | 0.0000–0.0000 | 0.0183–0.0355 | 0.1082–**0.2608** | 0.0002–0.0011 |
| NEG s04 solar | 0.0000–0.0000 | 0.0465–0.0678 | 0.1116–**0.3355** | 0.0205–0.0504 |
| NEG s02 dikey | 0.0000–0.0417 | 0.0210–0.0318 | 0.1290–0.2266 | 0.0033–**0.1126** |
| NEG s04 düşük | 0.0194–**0.2222** | 0.0476–0.0647 | 0.0519–0.0761 | 0.0074–0.0404 |

### ⛔ Hüküm: ayıran eşik YOK

**Dört sinyalin dördünde de pozitif aralık negatiflerle örtüşüyor.**
Eşik süpürmesi (en iyi F1):

| sinyal | eşik | F1 | recall | **precision** | TP/FN/FP/TN |
|---|---|---|---|---|---|
| S2 kenar | 0.0396 | 0.400 | 1.00 | **0.25** | 4/0/**12**/12 |
| S1 metin | 0.0028 | 0.333 | 0.50 | **0.25** | 2/2/6/18 |
| S3 düz | 0.0455 | 0.320 | 1.00 | **0.19** | 4/0/**17**/7 |
| S4 spec | 0.0048 | 0.316 | 0.75 | **0.20** | 3/1/12/12 |

İkili birleşimlerin en iyisi **S2+S3: F1 0.545, recall 0.75, precision 0.43**
— yani pozitif varyantların **birini kaçırıyor** ve **4 temiz varyantı**
yanlış eliyor.

**En iyi tek sinyal (S2) recall 1.00 veriyor ama precision 0.25:** 24 temiz
varyantın **12'si** — yani kabul edilen NASA varlıklarının yarısı —
**yanlışlıkla elenirdi**.

### ⚠ İki ek ölçülen sorun

1. **Pozitifin kendisi kararsız.** S1, kırpma varyantına göre
   **0.0000 → 0.2083** arasında savruluyor; 4 varyantın **2'sinde tam 0**.
   Yani vitrin, kadrajın neresine bakıldığına göre "görünmez" olabiliyor.
2. **İki sinyal TERS çalışıyor.** `S3`: temiz solar paneli **0.3355** ile
   pozitifin maksimumunun (0.1873) çok üstünde. `S4`: temiz dikey s02
   **0.1126** ile pozitifin (0.0104) **on katı**. Yani bu sinyaller vitrini
   değil, **düz/parlak yüzeyleri** ölçüyor.

### ⚠ Örneklem sınırı — genellenebilir PASS DENMEZ

Küme **1 pozitif varlık** içeriyor. Bu boyutta recall pratikte ikili bir
sayıdır ve **genellenebilir bir sonuç vermez**. Sinyal ayrışsaydı bile
"çözüldü" denemezdi. Burada zaten **ayrışmıyor**.

**Kusurlu varlığa özel kara liste genel çözüm olarak sunulmadı** ve üretim
kodunda **yok** (testle kilitli). Üretim dosyalarına vitrin/pano sinyal
kapısı **eklenmedi** (beş dosya için ayrı ayrı doğrulandı).

### Ölçülen test sonucu

| Paket | A | B | C | D | E | F | G | H | I | Toplam |
|---|---|---|---|---|---|---|---|---|---|---|
| Zengin venv | 125 | 200 | 148 | 95 | 127 | 244 | 218 | 257 | **1701** | **3115** |

0 hata. Faz I 1685 → **1701** (+16). **1 BLOKE** — I-33 görsel inceleme
kaydı **sürüyor** (pilot hâlâ kabul edilmedi).

### SONRAKİ ATOM — yalnız ölçülen sonuç belirliyor

Kare-bakan basit sinyaller **elendi**; bu yolla otomatik vitrin tespiti
**mevcut yerel bağımlılıklarla mümkün değil**. Ölçülen duruma göre geriye
**üç seçenek** kalıyor ve üçü de **kullanıcı kararı**:

1. **Kaynağı değiştir:** Commons'ın b001'e verdiği tek varlık vitrin çıktı.
   Pilotun s01 sorgusu (`Pleiades supercomputer`) daraltılabilir
   (ör. `Pleiades supercomputer racks`) — **I-26'daki ölçümlü sorgu
   disiplininin** aynısı, ağ/kota artışı yok.
2. **Sağlayıcı sırasını s01 için ölçüp değiştir** (NASA'nın bu sahnede
   semantik olarak daha güvenilir olduğu iki koşumda gözlendi).
3. **Kabul et ve elle seç:** b001 varlığını operatör onayına bağla.

⚠ Yeni yetenek (gerçek görüntü sınıflandırma / VLM) **kapsam dışı** ve
maliyet doğurur; bu atomun ölçümü onu **gerekçelendirmiyor** çünkü sorun
sinyal seçimi değil, **basit sinyallerin bu ayrımı taşıyamaması**.

---

## 53. FAZ I-35 — s01 SORGU DARALTMASI: **ELENDİ** (ölçüldü, 13 Ağu)

> **Durum: önerilen daraltma ÖLÇÜLDÜ ve UYGULANAMADI. Üretim kodu
> DEĞİŞMEDİ; ölçüm ve gerekçe teste kilitlendi. Yerel yeşil (0 hata,
> 1 BLOKE — I-33 kaydı sürüyor), push edildi. Rerender/deploy YOK.
> Maliyet $0.00.**
> Değişen: **yalnızca** `webapp/testler/test_faz_i.py` (+ handoff).
> Smoke betiği, `medya/*`, `editor/*`, pilot raporu ve 22 alan sözleşmesi
> **dokunulmadı** (git ile doğrulandı). I-23…I-34 **korundu**.
> Operatör onayı ve sağlayıcı sırası **değiştirilmedi** (talimat gereği).
> Ölçüm aynı `ara()` bütçesinde, aynı sağlayıcılarla, ücretli API'siz.

### Ölçülen tablo (eşik 2443; "ok" = tüm kapıları geçen aday)

| sorgu | CO ham | CO ok | **vitrin?** | NA ham | **NA ok** |
|---|---|---|---|---|---|
| `Pleiades supercomputer` **(mevcut)** | 18 | 5 | ⛔ **EVET** | 15 | ✅ **6** |
| `…racks` | 6 | **0** | – | **0** | **0** |
| `…rack` | 6 | **0** | – | **0** | **0** |
| `…system` | 6 | 2 | – | **0** | **0** |
| `…hardware` | 0 | 0 | – | 0 | 0 |
| `…aisle` | 0 | 0 | – | 0 | 0 |
| `…nodes` | 3 | 1 | ⛔ EVET | **0** | **0** |
| `…Ames` | 18 | 5 | ⛔ EVET | 5 | 5 |
| `…NAS` | 18 | 5 | ⛔ EVET | 13 | 6 |
| `NASA Advanced Supercomputing facility` | 17 | 6 | – | 3 | 3 |

### ⛔ Hüküm: karşılıklı dışlayan iki kısıt

**Vitrini eleyen her daraltma NASA'yı boşaltıyor; NASA'yı koruyan her
daraltma vitrini bırakıyor.** Sebep ölçüldü: vitrinin başlığı
*"Pleiades supercomputer node **on display**…"* — yani `Pleiades supercomputer`
terimlerini **tam olarak içeriyor**. CirrusSearch terimleri AND'lediği için
onu dışarıda bırakmanın tek yolu ya **negatif terim** (`-display`) ya da
aramayı o kadar daraltmak ki **hiçbir sağlayıcı sonuç veremiyor**.

- `-display` **kullanılmadı**: I-29'da bu anahtar kelimenin güvenilmez olduğu
  ölçülmüştü (gerçek kusurda recall %0, 7 işaretten 5'i yanlış pozitif) ve
  talimat özel-case kara listeyi yasaklıyor.
- `…racks` / `…rack` / `…hardware` / `…aisle`: **iki sağlayıcıda da sıfır** —
  I-26'da ölçülen **aşırı-darlık tuzağının** aynısı.
- `…system`: vitrini eliyor ama **NASA 0**, Commons yalnız 2. Commons bu
  host'ta **kalıcı olarak 429** veriyor (I-25…I-33'te ölçüldü), dolayısıyla
  s01 çoğu koşumda **medyasız** kalır → `KALITE-MEDYASIZ-BEAT` BLOKE.
  ⚠ Talimat "uygun aday yoksa dürüst BLOKE" diyor; ama bu, **istisna değil
  NORMAL sonuç** olurdu — nadir bir kalite kusurunu sık bir **tam
  başarısızlıkla** takas etmek doğru mühendislik değil.
- `NASA Advanced Supercomputing facility`: tek "iki sağlayıcıda da dolu +
  vitrinsiz" aday, ama **semantik kayıyor** (Commons ilk üçü:
  *NASA New Virtual Airport*, *Future Flight Central*, *Cray 2 Supercomputer*)
  ve **NASA'da s02 ile 2/3 çakışıyor** → I-22 tekrar kapısı riski.

Bu yüzden **s01 sorgusu değiştirilmedi**.

### ⚠ Ölçüm sırasında bulunan AYRI kusur (rapor tutarsızlığı)

I-33 raporunda s01 için Commons denemesi `durum: "BAYT-YOK", sebep: "HTTP 429"`
yazıyor **ama kabul edilen b001 varlığı Commons'ın vitrini**
(`s01_11066148`, `wikimedia`, `cc-by-sa`). Yani Commons'tan **bir bayt
başarıyla indi**, sonra kalanlar 429 aldı ve `deneme["durum"]` son
başarısızlığa göre yazıldı. Rapor ayrıca `saglayici: "nasa"` diyor.

Sonuç: **sağlayıcı durumu ve `kullanilan_saglayici` yanıltıcı.** Bu, hangi
sağlayıcının hangi varlığı verdiğini araştırırken üç atom boyunca kafa
karışıklığı yarattı. Bu atomda **düzeltilmedi** (kapsam dışı), sonraki atom
olarak öneriliyor.

### Ölçülen test sonucu

| Paket | A | B | C | D | E | F | G | H | I | Toplam |
|---|---|---|---|---|---|---|---|---|---|---|
| Zengin venv | 125 | 200 | 148 | 95 | 127 | 244 | 218 | 257 | **1710** | **3124** |

0 hata. Faz I 1701 → **1710** (+9). **1 BLOKE** — I-33 görsel inceleme kaydı
sürüyor; pilot hâlâ kabul edilmedi. **Rerender yapılmadı**: medya seçimi
değişmedi (sorgu değişmedi).

### SONRAKİ ATOM (I-36) — yalnız ölçülen kusurdan

**Edinim raporundaki sağlayıcı durumu tutarsızlığını düzelt.** Ölçülen
somut kusur: bir sağlayıcının adayı **kabul edildiği hâlde** o sağlayıcının
denemesi `BAYT-YOK` yazıyor ve `kullanilan_saglayici` başka bir sağlayıcıyı
gösteriyor. Dar, bedava, ağsız; `edinim.edin` içinde `toplanan` listesindeki
varlıkların sağlayıcısı zaten biliniyor. Bu düzeltilmeden hangi sağlayıcının
neyi verdiğine dair her teşhis şüpheli kalıyor.

⚠ Vitrin kusurunun kendisi için ölçülen üç seçenekten **ikisi elendi**
(I-34 kare-bakan sinyal, I-35 sorgu daraltması). Geriye **operatör onayı**
ve **s01 için sağlayıcı sırası** kalıyor; ikisi de bu atomda açıkça
yasaklanmıştı ve **kullanıcı kararıdır**.

---

## 54. FAZ I-36 — SAĞLAYICI TUTARSIZLIĞI DÜZELTİLDİ (dar kalite atomu, 13 Ağu)

> **Durum: I-35'te ölçülen rapor kusuru ÇÖZÜLDÜ. Yerel yeşil (0 hata,
> 1 BLOKE — I-33 görsel inceleme kaydı sürüyor), push edildi.
> Rerender YOK (medya/render davranışı değişmedi), deploy YOK.
> Maliyet $0.00.**
> Değişen: `webapp/medya/edinim.py`, `webapp/testler/test_faz_i.py`
> (+ handoff).
> `medya/commons.py`, `medya/nasa.py`, `medya/lisans.py`, `editor/plan.py`,
> `editor/qa_on.py`, smoke betiği, pilot raporu ve 22 alan sözleşmesi
> **dokunulmadı** (git ile doğrulandı). 429 devre kesici, tek `ara()`
> çağrısı, kota/ağ bütçesi ve I-23…I-35 **korundu**.

### ⛔ Ölçülen kusur (I-35'ten)

I-33 raporunda s01 için:

| alan | rapor diyordu | **gerçek** |
|---|---|---|
| Commons denemesi | `BAYT-YOK` / `HTTP 429` | **1 varlık İNDİRİLDİ**, sonra 429 |
| `kullanilan_saglayici` | `nasa` | b001'in kaynağı **wikimedia** |

İki ayrı hata birleşiyordu:
1. **Başarılı geçmiş eziliyordu.** Sağlayıcı döngüsünün sonundaki hata bloğu,
   o sağlayıcı bayt vermiş olsa bile `durum`u `BAYT-YOK` yapıyordu.
2. **Genel sağlayıcı son adımdan türüyordu.** Erken dönüşte
   `kullanilan_saglayici` = `ad` (o anki sağlayıcı) yazılıyordu; Commons
   birinciyi, NASA ikinciyi verince hüküm **nasa** oluyordu — oysa kabul
   edilen **ilk** varlık Commons'tandı.

Sonuç: "hangi sağlayıcı neyi verdi" sorusu **üç atom boyunca** yanıltıcı
cevaplandı (I-33'te b001'in kaynağını ancak zincirden çapraz okuyarak
bulabildim).

### Düzeltme

- **Kaynak, toplama anında işaretleniyor.** Her toplanan varlığa
  `kaynak_saglayici` yazılır (önbellek / doğrudan indirme / `BEKLE` sonrası
  — üç toplama noktasının hepsinde).
- **`saglayici_ozeti()` saf fonksiyonu**: `kullanilan_saglayici` ve
  `saglayici_dagilimi` **yalnız toplanan varlıklardan** türer. Ağ/dosya
  kullanmaz. Erken dönüş, kısmi başarı ve önbellek yolları **aynı** özeti
  kullanır — tek kaynak.
- **Deneme kaydı değişmez ve kronolojik.** Sağlayıcı bayt verdiyse
  `durum = KISMI-OK` + `toplanan_katki = N`; son hata **silinmez**, ayrı
  `son_hata` alanında durur. Hiç bayt gelmediyse `durum = BAYT-YOK` **aynen
  kalır** (gevşetme yok).
- **Geriye uyumlu**: `sebep`/`http`/`kalici`/`devre_acildi` alanları duruyor;
  katkı varsa `sebep` artık *"N varlık ALINDI, sonra: …"* diyor. Rapor
  iskeletine `saglayici_dagilimi` **eklendi** (yeni alan, kırıcı değil).

### ✅ Ölçülen senaryolar (hepsi ağsız sahte sağlayıcıyla)

| senaryo | sonuç |
|---|---|
| **başarı → 429** (I-33 sırası) | `KISMI-OK`, katkı 1, `kullanilan_saglayici=commons`, dağılım `{commons:1, nasa:1}` |
| **429 → başarı** | `commons`, dağılım `{commons:1}` |
| **çoklu başarı + son hata** | `KISMI-OK`, katkı **2**, dağılım `{commons:2}` |
| **hiçbir başarı** | `BAYT-YOK`, katkı 0, `ok=False`, sağlayıcı `""`, dağılım `{}` |
| **seçilen Commons + son hata 429** | `ok=True`, sağlayıcı **commons** (nasa değil) |
| **gerçek I-33 fixture** | ilk varlık `wikimedia`, dağılım `{wikimedia:1, nasa:4}`, **tekel %80** dağılımdan doğru çıkıyor |

Ayrıca doğrulandı: denemeler kronolojik (`commons` → `nasa`), her varlık kendi
kaynağını taşıyor, **tek `ara()` çağrısı** korundu, boş girdi çökertmiyor.

### Ölçülen test sonucu

| Paket | A | B | C | D | E | F | G | H | I | Toplam |
|---|---|---|---|---|---|---|---|---|---|---|
| Zengin venv | 125 | 200 | 148 | 95 | 127 | 244 | 218 | 257 | **1727** | **3141** |

0 hata. Faz I 1710 → **1727** (+17). **1 BLOKE** — I-33 görsel inceleme kaydı
sürüyor; pilot hâlâ kabul edilmedi.

⚠ **Rerender yapılmadı**: değişiklik yalnız **rapor doğruluğu**; hangi
varlığın seçildiğini belirleyen mantık (sıralama, kapılar, kota, devre
kesici) **bit-bit aynı**. Yeni `kaynak_saglayici` alanı manifeste sızmıyor
(smoke aday sözlüğünü alan alan kuruyor), dolayısıyla render girdisi de aynı.

### SONRAKİ ATOM — açık tek kusur değişmedi

**b001 vitrin/pano kusuru** hâlâ açık ve pilot kabul edilmedi. Ölçülen üç
seçenekten ikisi elendi (I-34 kare-bakan sinyal, I-35 sorgu daraltması).
Kalan ikisi **kullanıcı kararı**: (a) s01 için sağlayıcı sırası,
(b) operatör onayı. Bu atom teşhis güvenilirliğini onardığı için artık
"hangi sağlayıcı neyi verdi" sorusu **rapordan doğrudan** okunabiliyor —
(a) seçeneği ölçülerek değerlendirilebilir hale geldi.

---

## 55. FAZ I-37 — BEAT→SCENE→FACT→ASSET BAĞI KOPAMAZ (dar kalite atomu, 13 Ağu)

> **Durum: kök neden ÇÖZÜLDÜ, kapı eklendi, A–I yeşil (0 hata).
> Lawn pilotu HÂLÂ kabul edilmedi (ayrı, ölçülen sebep). Deploy YOK.
> Maliyet $0.00.**
> Değişen: `webapp/editor/qa_on.py`,
> `webapp/testler/smoke_konsept3_teknoloji_i20.py`,
> `webapp/testler/test_faz_i.py` (+ handoff).
> `medya/*`, `editor/plan.py`, `motion.py`, `gramer.py`, `kalite_kapisi.py`,
> `pipeline.py`, `server.py`, `deploy.sh` ve 22 alan sözleşmesi
> **dokunulmadı**. I-22…I-36 **korundu**. Rastgelelik/yeni sağlayıcı yok.

### ⛔ Ölçülen kök neden

`cesitli_sirala` varlıkları **sahneler arasında** `itertools.permutations`
ile yeniden diziyor ve *"yalnızca SIRA değişti"* diyordu. Ama varlıklar
sahnelere **indeks** ile eşleşiyor (`manifest_yap`) — dolayısıyla permütasyon
**anlatım ile görseli koparıyordu**. Gerçek render'da ölçüldü (lawn pilotu,
6 beat'in **3**'ü):

| beat | anlatım | ekrandaki görsel |
|---|---|---|
| b003 | *"…thin, **patchy lawn** he started with."* | **fıskiye** (yemyeşil çim) |
| b004 | *"Then **water lightly** two or three times a day…"* | **Ricinus** fidesi |
| b005 | *"Warm soil to germinate… **seedling**"* | **patchy lawn** |

Hiçbir otomatik kapı bunu görmüyordu; kusur ancak kareye bakınca çıktı.

### Düzeltme (en küçük güvenli)

1. **Sıralayıcı sahne bağını korur.** Sahneler arası permütasyon **kaldırıldı**.
   ⚠ Ölçülen kayıp **yok**: komşu benzerliği zaten eşiğin çok altındaydı
   (0.5625 < 0.86). Çeşitlilik hükmünü I-22 `KALITE-MEDYA-TEKRAR`, sahne içi
   seçimi `_varlik_sec` + I-23b ayırt-etme kapısı veriyor — ikisi de **sahne
   bağını zaten korur**.
2. **Yeni PRE-QA kapısı `KALITE-BAG-KOPUK` (fail).** Her beat için
   beat→scene→fact→asset bağı doğrulanır: varlığın `scene_id`'si çekimin
   `scene_id`'sinden farklıysa **render durur**. Bağ `olcum["beat_bagi"]`
   ile **raporda görünür** (her beat için kayıt + kopuk listesi).

### Testler

Kırmızı önce: gerçek lawn kayması fixture'ıyla kapı **3 kopuk beat** yakaladı
ve `KALITE-BAG-KOPUK` **fail** üretti; doğru bağlamada temiz. Ayrıca
sıralayıcıda `itertools.permutations` kalmadığı kilitlendi.

| Paket | A | B | C | D | E | F | G | H | I | Toplam |
|---|---|---|---|---|---|---|---|---|---|---|
| Zengin venv | 125 | 200 | 148 | 95 | 127 | 244 | 218 | 257 | **1734** | **3148** |

0 hata. Faz I 1727 → **1734**. 1 BLOKE (I-33 görsel inceleme kaydı).

### ✅ Rerender: sahne bağı DÜZELDİ, ama pilot yine kabul edilmedi

Mevcut cache ile yeniden üretildi. Zincir artık **doğru**:
`b003→s02`, `b004→s03`, `b005→s04`, `b006→s05` — kayma **gitti**,
`siralama: SAHNE BAGI KORUNDU (yeniden_dizildi=False)`.

⛔ Ama PRE-QA **`KALITE-MEDYA-TEKRAR`** ile durdurdu: `s01` önbellekten
**tek** varlık dönüyor (bölünen b001/b002 aynı görseli paylaşıyor).
Cache'te `s01_..._1.jpg` var ama **künyesi yok** — provenance'ı olmayan
varlık kullanılamaz ve künye **uydurulmaz**. İkinci adayı indirmek Commons'ın
`Retry-After: 600` penceresini beklemeyi gerektiriyor.

**MP4 kabul edilmiş değil, mutlak yol verilmedi, deploy yok.**

### SONRAKİ ATOM (I-38)

1. **Lawn pilotunu tamamla**: taze pencerede s01 için 2 aday indir
   (`cikti/_i37_medya/s01_*` silinip sürücü tek kez koşulur) → PRE-QA geçer.
   Sürücü: `scratchpad/i37_surucu.py` (repo dışı, motoru DEĞİŞTİRMEZ).
2. Sonra da **Ricinus semantik kusuru** kalırsa tam PASS **denmez**:
   `grass seedling` sorgusunun 0. adayı (*Grass seedlings near Dreenhill*,
   4032×3024) tüm kapılardan geçiyor ama indirmesi 429'a takılmıştı;
   `cikti/_i37_medya/s04_*` silinip yeniden alınmalı.

---

## 56. FAZ I-38 — YAZI SPEC'İ SAHNEYE GÖRELİ: EKRAN KÜNYESİ ÇİZİLİYOR (dar kalite atomu, 13 Ağu)

> **Durum: kök neden ÇÖZÜLDÜ, kapı eklendi, A–I yeşil (3162, 0 hata).
> Lawn pilotu HÂLÂ kabul edilmedi (iki ayrı, ölçülen sebep). Deploy YOK.
> Maliyet $0.00.**
> Değişen: `webapp/editor/plan.py` (1 satır + gerekçe),
> `webapp/editor/qa_on.py` (yeni kapı), `webapp/testler/test_faz_i.py`.
> `medya/*`, `adapter.py`, `motion.py`, `tipografi.py`, `remotion_v2.py`,
> TSX'lerin **hiçbiri**, `pipeline.py`, `server.py`, `deploy.sh` ve 22 alan
> sözleşmesi **dokunulmadı**. I-22…I-37 **korundu**.

### ⛔ Ölçülen kök neden

`_katman_specleri` grafik spec'ine katmanın **MUTLAK zaman çizgisi**
başlangıcını yazıyordu (`d["bas_sn"] = k.bas_sn`). Tüketici
(`app/render-studio/src/editorv2/Grafikler.tsx` → `KaynakEtiketi`,
`BolumBasligi`) `spec.bas_sn`i **SAHNEYE GÖRELİ** okur ve zarfı
**sahne-yerel kare** ile hesaplar. Gerçek render'da ölçüldü:

| beat | sahne süresi | spec `bas_sn` | sonuç |
|---|---|---|---|
| b002 | 2.201 | 2.287 | **hiç görünmez** |
| b003 | 5.549 | 4.488 | yalnız son ~1 sn |
| b004 | 5.351 | 10.037 | **hiç görünmez** |
| b005 | 5.274 | 15.388 | **hiç görünmez** |
| b006 | 4.938 | 20.662 | **hiç görünmez** |
| b001 `chapter-title` | 1.887 | 0.2 | çalışıyor |

Yani **CC-BY / CC-BY-SA olan dört sahnenin EKRAN KÜNYESİ hiç çizilmedi**;
atıf yalnız `attribution.txt`te kaldı. `chapter-title` **tesadüfen**
çalışıyordu: b001 sıfırdan başlar, orada mutlak == göreli. I-31 politikası
ölçülüyor, planlanıyor, `kunye_kararlari`'nda `TAM` raporlanıyordu — **ekrana
ulaşmıyordu**. Hiçbir otomatik kapı görmedi; kusur ancak **kareye bakınca**
çıktı (I-33 dersinin aynısı).

### Düzeltme (en küçük güvenli)

1. **Spec zamanı sahneye göreli.** `d["bas_sn"] = max(0.0, k.bas_sn − hedef.bas_sn)`.
   Beş künyenin hepsi `0.4`'e iner (plan zaten `b.bas_sn + 0.4` veriyordu);
   b001 `chapter-title` `0.2`'de **değişmeden** kalır — gerileme yok.
2. **Yeni PRE-QA kapısı `KALITE-YAZI-SAHNE-DISI` (fail).** `bas_sn >= sahne
   süresi` olan yazı katmanı sahne-yerel karede **hiç gelmez** → sessizce
   düşer. Ölçüm `olcum["yazi_sahne_penceresi"]` ile **raporda görünür**
   (ölçülen sayısı + dışarıda kalan listesi).

### Testler

Kırmızı önce: gerçek lawn zaman çizgisiyle kapı **4 sahne-dışı spec** yakaladı
ve `KALITE-YAZI-SAHNE-DISI` **fail** üretti; düzeltilmiş speclerde temiz.

| Paket | A | B | C | D | E | F | G | H | I | Toplam |
|---|---|---|---|---|---|---|---|---|---|---|
| Zengin venv | 125 | 200 | 148 | 95 | 127 | 244 | 218 | 257 | **1748** | **3162** |

0 hata. Faz I 1734 → **1748**. A–H bit-bit değişmedi. 1 BLOKE (I-33 kaydı).

### ✅ Rerender: künye GÖRÜNÜYOR, ama pilot yine kabul edilmedi

1080p yeniden üretildi. Ekran künyesi **kareyle doğrulandı**:
`Famartin / CC-BY-SA` (6.0 sn), `Anton / CC-BY-SA` (11.5 sn),
`Macleay Grass Man / CC-BY` (17.0 sn), `Dietmar Rabich / CC-BY-SA` (22.0 sn)
— sağa hizalı, güvenli alan içinde. Ölçümler: 1920×1080/30fps, 25.3 sn,
LUFS −14.26 / TP −2.57, sessizlik 0, siyah 0, donma 0, 5 benzersiz kesme,
ardışık aynı varlık **yok**, beat→fact→asset kopuk **0**, 11 tam çözünürlük
kare, izleyici kalite puanı 100/100.

⛔ **İki sebeple KABUL EDİLMEDİ:**

1. **POST-QA FAIL — `POST-KENAR-SIYAH`** (1/101 kare, sağ kenar **15.99** vs
   eşik **16.0**). Bıçak sırtı: I-37 render'ı aynı ölçümde **16.06** ile
   geçiyordu (pay 0.06). İhlal karesi ≈20.4 sn — b005 künyesi 18.388'de bitti,
   b006'nınki 20.662'de başlıyor, yani **o karede ekranda künye yok**;
   düzeltme o kareyi içerik olarak değiştirmiyor. Kare `karartma` geçişinin
   içinde. **Eşik GEVŞETİLMEDİ.**
2. **Semantik kusurlar sürüyor** (I-37'den devir, medya değişmedi):
   b001 *"garage shelf"* → 1900 sepya hasat; b002 → Kahoʻolawe kurak
   restorasyon sahası; b005 *"seedling"* → **Ricinus** (kene otu) geniş
   yapraklı fide. b003/b004/b006 semantik olarak **doğru**.

**MP4 kabul edilmiş değil, mutlak yol verilmedi, deploy yok.**

### SONRAKİ ATOM (I-39) — yalnız ölçülen kusurdan

1. **`POST-KENAR-SIYAH` geçiş karelerini ayırt etmiyor.** `karartma`/`flash`
   geçişi kareyi meşru olarak karartır; kapı bunu "kamera kadrajdan taşıyor"
   diye raporluyor. Ölçülebilir atom: geçiş penceresindeki kareleri ya hariç
   tut ya da geçiş için ayrı eşik ölç. Eşiği körlemesine düşürmek **yanlış**.
2. **Medya seçiminde semantik doğrulama yok** (b001/b002/b005). Seçici
   çözünürlük/detay/orana göre puanlıyor; "grass seedling" sorgusuna keskin
   4000×3000 Ricinus'u çim fidesinin üstüne koyuyor. Bu **ayrı ve daha büyük**
   bir atom — sorguyu ya da eşiği zorlamak çözüm değil.
3. **`kaynakYazi` `VidrushVideo` yolunda taşınmıyor** (`Video.tsx` `Sahne`
   tipinde alan yok; `adapter.REMOTION_ALANLARI` ise içeriyor). Bu hat
   (`pipeline.py`) I-38'de **ölçülmedi**; ayrı atom olarak doğrulanmalı.

---

## 57. FAZ I-39 — ALTYAZI NEFES BOŞLUĞU: YAZI ALTYAZIYA YAPIŞAMAZ (dar kalite atomu, 13 Ağu)

> **Durum: ölçülen kusur ÇÖZÜLDÜ, kapı eklendi, A–I yeşil (3183, 0 hata).
> 1080p pilot YENİDEN ÜRETİLDİ ve POST-QA **tam PASS**. Lawn pilotu yine de
> KABUL EDİLMEDİ (ayrı, ölçülen semantik sebep). Deploy YOK. Maliyet $0.00.**
> Değişen: `webapp/editor/tipografi.py` (2 sabit), `webapp/editor/motion.py`
> (2 sabit), `webapp/editor/kalite_kapisi.py` (yeni ölçüm), `webapp/editor/qa_on.py`
> (yeni kapı), `webapp/testler/test_faz_i.py`, `webapp/testler/test_faz_c.py`
> (eski geometriyi kodlayan 1 fixture satırı).
> `medya/*`, `plan.py`, `adapter.py`, `gramer.py`, `remotion_v2.py`, TSX'lerin
> **hiçbiri**, `pipeline.py`, `server.py`, `deploy.sh` ve 22 alan sözleşmesi
> **dokunulmadı** (git ile doğrulandı). I-22…I-38 **korundu**.

### ⛔ Ölçülen kök neden

I-38 ekran künyesini **görünür** yaptı, ama künye altyazı bandının **dibinde**
duruyordu. Üç kapı da (`KALITE-GUVENLI-ALAN`, `KALITE-YAZI-CAKISMA`,
`bant_cakisiyor`) **temiz** dönüyordu, çünkü hiçbir katman bandın **içine
girmiyordu**. Ölçülen boşluklar (1080p, `ALTYAZI_BANT[0]` = 0.81 → 874.8 px):

| katman | y | çizilen alt kenar | **nefes** | eşik |
|---|---|---|---|---|
| `source-label` | 0.755 | 815.4 + 21×1.3 = **842.7 px** | **32.1 px** | 47.5 |
| `chapter-title` | 0.70 | 756 + 60×1.3 + dolgu 25 = **859.0 px** | **15.8 px** | 47.5 |

"Değmiyorsa sorun yok" **yanlış bir kabuldü**: iki metin bloğu birkaç on piksel
arayla yığılınca göz ikisini **tek blok** okuyor; ne künye ne altyazı okunuyor.

⚠ Devir notu `chapter-title` için ~43.8 px diyordu; o sayı yalnız **metin** alt
kenarını sayıyor, **bant dolgusunu** saymıyordu. Burada ölçülen değer
**çizilen bant kutusudur** (dolgu dahil) — daha katı ve ekranda gerçekten
kaplanan yer. İki okuma da eşiğin altında, **hüküm aynı**.

### Düzeltme (en küçük güvenli)

1. **`KAYNAK_ETIKETI_ALTYAZILI` 0.755 → 0.075** (sağ üst köşe). Üst kenar
   81 px, güvenli kenar 64 px'in **içinde**; altyazıdan 766.5 px uzakta.
2. **`KONUM["chapter-title"]` 0.70 → 0.60** ve `motion.bolum_basligi_spec`
   varsayılanı da 0.60 — iki ayrı aritmetik bırakılmadı, test eşliği kilitliyor.
3. **Yeni ölçüm `kalite_kapisi.altyazi_nefes_olcusu`** (saf, ağsız): katmanın
   **çizilen** alt kenarını render'ın kendi geometrisinden türetir
   (`SATIR_KUTU_ORANI = 1.3`, Grafikler.tsx:191; bantlı katmana `DOLGU_ORANI`
   eklenir) ve bant üst kenarına olan boşluğu ölçer.
4. **Yeni PRE-QA kapısı `KALITE-YAZI-NEFES-YOK` (fail).** Eşik **sabit piksel
   değil**, altyazı puntosundan **türetilir**: `38 × 1.25 = 47.5 px`.
   ⚠ Altyazı yoksa bant da yoktur: ölçüm `olculdu=False` döner ve **hüküm
   verilmez** (sessiz PASS değil, "ölçülemedi").
5. `motion.kaynak_etiketi_spec` içindeki yanıltıcı `"konum": "sag-alt"` sabiti
   `"y_orani"` oldu — konumu artık yalnız `y_orani` belirliyor.

### Testler (red-first)

Kırmızı önce **çökmeden** koştu: 21 hedefli kontrolün **15'i XX** verdi
(sabitler, ölçüm fonksiyonu, kapı, rapor alanı). Düzeltmeden sonra 21/21 yeşil.
Kalıcı kırmızı kanıt: I-38 pilotunun **gerçek** katmanlarıyla (0.70 / 0.755)
kurulan fixture kapıyı **her zaman** tetikler ve künye boşluğunu **32.1 px**
olarak ölçer.

⚠ **Faz C'de 1 gerileme çıktı ve düzeltildi** (sessizce geçilmedi):
`test_faz_c.py` çakışma fixture'ı `c2.y_orani = 0.72` **sabitini** başlığın
**eski** 0.70 konumuna göre seçmişti; başlık 0.60'a taşınınca fixture çakışmayı
kurmayı bıraktı ve çözücüyü **boş kümeyle** sınadı. Bindirme artık başlığın
kendi konumundan türetiliyor (`c1.y_orani + 0.02`) — sınamanın niyeti korundu.

| Paket | A | B | C | D | E | F | G | H | I | Toplam |
|---|---|---|---|---|---|---|---|---|---|---|
| Zengin venv | 125 | 200 | 148 | 95 | 127 | 244 | 218 | **257** | **1769** | **3183** |

0 hata. Faz I 1748 → **1769** (+21). 2 BLOKE: I-33 görsel inceleme kaydı +
1 opsiyonel dış fixture (`QA_TEST_VIDEO`).

### ✅ 1080p PİLOT YENİDEN ÜRETİLDİ — POST-QA **tam PASS**

Sürücü: `scratchpad/i39_surucu.py` + `scratchpad/i39_qa.py` (repo dışı, motoru
**değiştirmez**). Medya `cikti/_i37_medya`, anlatım/ambiyans
`cikti/_i37_calisma/ses` **önbelleğinden**; sağlayıcıya **hiç istek atılmadı**,
TTS **yeniden üretilmedi**. **Maliyet $0.00.**

⚠ **SADAKAT KAPISI**: sürücü render'dan önce yeni planı I-38 kaydıyla
karşılaştırır. `beat esit=True`, `varlık esit=True` — yani ölçülen fark
**yalnız I-39'un yazı geometrisidir**, girdi kayması değil.

Ölçümler (`outputs/sample/lawn_i39_rapor.json`):

- ffprobe: h264 **1920×1080 @ 30/1**, aac 48 kHz/2ch, **25.3 sn**, 105 MB
- LUFS **−14.27** / TP **−3.10** / LRA 3.2 · sessizlik **%0.0** · kırpma yok
  (ham render −15.4 idi; H6'da onaylı **tek** deterministik `loudnorm`
  remaster'ı uygulandı, **video akışı kopyalandı**, ücret $0.00)
- kesmeler: **8** · optik hareket genel ort **9.2**, donuk sahne **yok**
- kenar siyahlığı: **0/101 ihlal** (I-38'de 1/101 FAIL'di) — en koyu sağ **16.01**
- **11 kare** çıkarıldı, 6 beat'in **hepsi** örneklendi; 7'si gözle incelendi
- PRE-QA: **0 fail**, 3 warn (`PERDE-EKSIK`, `SAGLAYICI-TEKEL`, `GECIS-ASIRI`)
- **POST-QA: PASS — hiçbir sorun yok**

**Kare kanıtı (I-39'un asıl iddiası):** beş künyenin **hepsi** sağ üstte,
altyazıdan uzakta çiziliyor (`Forest and Kim Starr / CC-BY` 3.0 sn,
`Famartin / CC-BY-SA` 6.87 sn, `Anton / CC-BY-SA` 12.3 sn,
`Macleay Grass Man / CC-BY` 16.83 sn, `Dietmar Rabich / CC-BY-SA` 22.73 sn).
Bölüm başlığı 0.60'ta, altyazıyla arası **123.8 px**.

### ⛔ Pilot yine de KABUL EDİLMEDİ — dürüst kusur listesi

POST-QA tam PASS, ama **görsel/semantik inceleme** kusurları **duruyor**.
Bunlar I-39'un konusu **değildi** ve talimat gereği **kodla genişletilmedi**:

1. **b001 semantik yanlış** — anlatım "garaj rafındaki çim tohumu torbası",
   ekranda **1900 sepya tarla hasadı** (atlar, saban).
2. **b002 semantik yanlış** — ekranda **Kahoʻolawe** kurak restorasyon sahası
   (kırmızı toprak, saman balyaları); "garaj rafı" ile uyumsuz.
3. **b005 semantik yanlış** — anlatım "seedling", ekranda **Ricinus** (kene otu)
   geniş yapraklı fide; çim fidesi **değil**.
4. **Statik fotoğraf + Ken Burns** yapısı sürüyor: gerçek **B-roll/video/cutaway
   yok** (6 çekimin 6'sı da fotoğraf).
5. **Kurgu ritmi, hook ve kapanış zayıf**; sert kesme oranı %50 (referans %80).
6. **Müzik/SFX yok** (yalnız anlatım + ambiyans).
7. **Kenar siyahlığı bıçak sırtı**: en koyu sağ **16.01**, eşik **16.0** —
   ihlal 0 ama pay yalnız **0.01**. Eşik **gevşetilmedi**, düşürülmedi.
8. Tek sağlayıcı **%100 wikimedia** (tekel uyarısı sürüyor).

**MP4 kabul edilmiş değil, mutlak yol verilmedi, deploy yok.**

### SONRAKİ ATOM (I-40) — yalnız ölçülen kusurdan

1. **Medya seçiminde semantik doğrulama yok** (b001/b002/b005). I-38'den devir;
   **ayrı ve daha büyük** bir atom. Sorguyu ya da eşiği zorlamak çözüm değil
   (I-34/I-35'te ikisi de ölçülüp elendi).
2. **`onizleme.py` ffmpeg önizleme yolu I-39'a katılmadı**: `chapter-title`
   orada hâlâ **sabit 0.70** ile, `source-label` ise `y_orani`yi **hiç
   okumadan** `y=h-th-14` ile çiziliyor. Remotion 1080p hattı ile önizleme
   hattı artık **ayrışıyor**. Dar, bedava, ağsız bir atom.
3. **`kaynakYazi` `VidrushVideo` yolunda taşınmıyor** (I-38'den devir,
   `pipeline.py` hattı hâlâ ölçülmedi).

---

## 58. FAZ I-40 — ÖNİZLEME YOLU REMOTION GEOMETRİSİNE BAĞLANDI (dar parite atomu, 13 Ağu)

> **Durum: ölçülen ayrışma ÇÖZÜLDÜ, modüle İLK test kapsamı geldi, A–I yeşil
> (3201, 0 hata). Değişen yolun GERÇEK çıktısı üretildi. 1080p Remotion pilotu
> gerileme kanıtı olarak yeniden üretildi: **11/11 kare SHA-256 birebir aynı**,
> POST-QA **PASS**. Deploy YOK. Maliyet $0.00.**
> Değişen: `webapp/editor/onizleme.py`, `webapp/testler/test_faz_i.py`.
> `tipografi.py`, `motion.py`, `kalite_kapisi.py`, `qa_on.py`, `plan.py`,
> `adapter.py`, `remotion_v2.py`, `medya/*`, TSX'lerin **hiçbiri**,
> `pipeline.py`, `server.py`, `deploy.sh` ve 22 alan sözleşmesi
> **dokunulmadı** (git ile doğrulandı). I-23…I-39 **korundu**.

### ⛔ Ölçülen ayrışma

`editor/onizleme.py` yazı katmanlarını **sabit sayılarla** çiziyordu ve planın
kendi spec'ini (`parametre.y_orani`, `parametre.punto`, `parametre.x`)
**hiç okumuyordu** — oysa spec'ler `renderer=ffmpeg` ile **zaten o değerleri
taşıyor**:

| katman | önizleme (eski) | planın dediği (I-39) |
|---|---|---|
| `chapter-title` | `y=h*0.70`, punto **34** | y_orani **0.60**, punto 60 |
| `lower-third` | `y=h*0.80`, punto **26** | `KONUM` **0.78**, punto 42 |
| `source-label` | `y=h-th-14` (**y_orani hiç okunmuyor**), punto **15** | y_orani **0.075**, punto 21 |

Yani **iki ayrı geometri** vardı: I-14'te ölçülen kusur sınıfının aynısı (plan
bir şey hesaplar, çizim başkasını çizer) ve I-16'da Remotion'da düzeltilen
`bottom: 22` kusurunun **önizlemedeki ikizi** — üstelik `h-th-14` güvenli
kenarın (64×ölçek = 42.7 px) **dışındaydı**.

⚠ **DÜRÜST KAPSAM — ölçüldü:** bu modülün repoda **hiçbir çağıranı yok**
(tek bir `import` bile). Düzeltme üretim çıktısını **değiştirmez**; ayrışmayı
ve **sıfır test kapsamını** kapatır. Bu, atomu küçültmez ama iddiasını
küçültür ve öyle raporlanır.

### Düzeltme (tek kaynak)

- **Yeni saf fonksiyon `onizleme.yazi_yerlesimi(ad, prm, gen, yuk, p)`**:
  punto/x/y/hizalama **önce planın spec'inden**, spec sessizse
  `tipografi.KONUM` ve profil puntosundan gelir. Bu dosyada **uydurma sabit
  tutulmaz**. Puntolar profil nominal genişliğinde (1920) üretildiği için
  önizleme ölçüsüne **oranla** küçültülür (`NOMINAL_GENISLIK`).
- **Künye güvenli kenarı ZORLAR** — Remotion `KaynakEtiketi` ile birebir aynı
  hesap: `min(y*yuk, yuk − güvenli_kenar − punto × SATIR_KUTU_ORANI)`; kırpma
  olduğunda `kirpildi=True` ile **raporlanır**.
- `_bant_yazi` artık sabit argüman değil **yerleşim sözlüğü** alıyor; bant
  dolgusu da `kalite_kapisi.DOLGU_ORANI` (Grafikler.tsx'in kendi sabiti).
- `callout` yatayda **oran** (`x`), diğerleri **izgara px** (`izgara_x`)
  taşıdığı için tür bazında ayrı ele alınır — tahmin/heuristik yok.

### Testler (red-first) — modülün İLK kapsamı

Kırmızı önce **çökmeden** koştu: 18 hedefli kontrolün **14'ü XX** verdi ve
filtre dizgisi kusuru **dizgide** göründü: `fontsize=34:x=66:y=h*0.70`.
Düzeltmeden sonra **18/18 yeşil**. Yerel ffmpeg libfreetype **olmadan**
derlendiği için testler ffmpeg **çalıştırmaz**; yetenek yoklaması test
süresince geçici açılır ve yalnız **saf filtre dizgisi** üretilir.

| Paket | A | B | C | D | E | F | G | H | I | Toplam |
|---|---|---|---|---|---|---|---|---|---|---|
| Zengin venv | 125 | 200 | 148 | 95 | 127 | 244 | 218 | 257 | **1787** | **3201** |

0 hata. Faz I 1769 → **1787** (+18). 2 BLOKE (I-33 kaydı + opsiyonel fixture).

### ✅ Değişen yolun GERÇEK çıktısı: `onizleme_lawn_i40.mp4`

I-39 pilotunun `render_plan.json`i, `editor.onizleme` ile 720p'ye çevrildi.
Medya **önbellekten**, ağ **yok**, **$0.00**. Ölçümler
(`outputs/sample/onizleme_i40_rapor.json`):

- **1280×720 @ 30**, 25.30 sn, 4.99 MB · **6/6 sahne gerçek lisanslı medya**
  (sentetik **kullanılmadı**), hata **yok**
- LUFS **−14.25** / TP **−5.57** / LRA 0.20 · sessizlik aralığı **0**
- **6 kesme** · **11 kare** çıkarıldı; kare gözle doğrulandı (b004 fıskiye)
- **Parite kanıtı**: altı yazı katmanının **hepsi** planın `y_orani`sini
  birebir taşıyor (0.60 / 0.075 ×5), künye **sağa hizalı**, kırpma yok

⛔ **BLOKE — sahte PASS verilmedi:** bu host'un ffmpeg'i **libfreetype olmadan**
derlenmiş; `drawtext` **yok**. Yazı katmanları **çizilemedi** ve modül onları
`atlanan_spec`'te **raporladı** (sessiz kayıp yok: `chapter-title` ×1,
`source-label` ×5). Yani **yazı geometrisi görsel olarak doğrulanamadı**;
deterministik filtre-dizgisi testleriyle kilitlendi. Konteynerdeki ffmpeg'de
filtre **var** — görsel doğrulama orada yapılmalı.

### ✅ 1080p Remotion pilotu — GERİLEME YOK (nesnel kanıt)

`editorv2_lawn_i40.mp4` yeniden üretildi (önbellekten, $0.00). Sadakat kapısı
yine `beat esit=True / varlık esit=True`. Ölçümler I-39 ile **aynı**:
1920×1080@30, 25.259 sn, LUFS −14.27 / TP −3.10, 8 kesme, optik ort 9.2,
kenar siyahlığı **0/101** (en koyu sağ 16.01), 11 kare, **POST-QA PASS**.

**Nesnel gerileme kanıtı:** I-39 ve I-40 render'larının **11 karesinin
11'i de SHA-256 olarak birebir aynı**. Yani I-40 Remotion hattını
**bit düzeyinde** değiştirmedi.

### ⛔ Pilot yine KABUL EDİLMEDİ

I-39'da ölçülen **semantik kusurlar aynen duruyor** (b001 1900 sepya hasat,
b002 Kahoʻolawe kurak saha, b005 Ricinus), statik fotoğraf/Ken Burns yapısı,
B-roll/video yok, hook/kapanış zayıf, müzik/SFX yok. I-40 bunlara
**dokunmadı**. **MP4 kabul edilmiş değil, mutlak yol verilmedi, deploy yok.**

### ⚠ Bu atomda ÖLÇÜLEN, kapsam dışı bırakılan kusurlar

1. **Önizleme yolunda ALTYAZI hiç çizilmiyor** — `render_plan`'daki
   `altyazi` küpleri okunmuyor. I-39 nefes kapısının önizlemede karşılığı
   **yok** (bant da yok). Dar, bedava, ağsız bir atom.
2. **Önizleme sesi 96 kHz aac** çıkıyor (yatak 48 kHz üretilmesine rağmen);
   Remotion hattı 48 kHz. I-40 ses yoluna **dokunmadı**.
3. **Geçiş efektleri önizlemede uygulanmıyor** (modülün kendi belgelediği
   sınır) — sert kesme ile concat ediliyor.

### SONRAKİ ATOM (I-41) — yalnız ölçülen kusurdan

1. **Medya seçiminde semantik doğrulama yok** (b001/b002/b005). I-38'den beri
   açık; **ayrı ve daha büyük** atom. Sorguyu/eşiği zorlamak çözüm değil
   (I-34/I-35'te ikisi de ölçülüp elendi).
2. **Önizlemede altyazı yok** (yukarıda ölçüldü) — dar ve bedava.
3. **`kaynakYazi` `VidrushVideo` yolunda taşınmıyor** (I-38'den devir;
   `pipeline.py` hattı hâlâ ölçülmedi).

---

## 59. FAZ I-41 — `kaynakYazi` ÜRETİM HATTINDA DÜŞÜYORDU (lisans görünürlüğü, 13 Ağu)

> **Durum: I-38'den devir kusurun GERÇEK kök nedeni ölçüldü ve ÇÖZÜLDÜ.
> A–I yeşil (3220, 0 hata). Değişen üretim kompozisyonu (`VidrushVideo`)
> 1080p'de render edildi: künye artık **ÇİZİLİYOR** (kareyle doğrulandı).
> ⛔ O pilotun **POST-QA'sı FAIL** — nedenleri I-41 DIŞI, aşağıda ayrıştırıldı.
> editorv2 hattı gerilemedi: **11/11 kare SHA-256 aynı**, POST-QA PASS.
> Deploy YOK. Maliyet $0.00.**
> Değişen: `webapp/pipeline.py` (1 yardımcı + 1 satır montaj),
> `app/render-studio/src/Video.tsx` (1 alan + 1 bileşen),
> `webapp/hizli_render.py` (1 konum ifadesi), `webapp/testler/test_faz_i.py`.
> `editor/*`, `medya/*`, `server.py`, `deploy.sh`, `Grafikler.tsx`,
> `EditorV2.tsx` ve **22 alan sözleşmesi** **dokunulmadı** (test kilitliyor).

### ⛔ Ölçülen kök neden — I-38'in tahmininden DAHA DERİNDE

I-38 notu *"`Video.tsx` `Sahne` tipinde alan yok"* diyordu. Ölçüldü: kusur
**daha önce** başlıyor. `pipeline.py` CC/lisanslı klip alındığında
`s["kaynakYazi"]` yazıyor (**3 nokta**: avcı atfı, `kaynak.atif_al` kanalı,
genel yedek sorgu) — ama `props_sahneler` sahneyi **alan alan** kuruyor ve bu
alanı **hiç kopyalamıyordu**. Yani künye **props sınırında** düşüyordu ve
sonrasındaki **iki renderer da** onu göremiyordu:

| renderer | durum |
|---|---|
| Remotion `VidrushVideo` (**varsayılan**) | `Sahne` tipinde alan **yok**, katman **yok** |
| `hizli_render` (`RENDER_MOTOR=ffmpeg`) | `_kaynak_yazi_filtre` alanı **okuyor** ama props'ta alan olmadığı için **her zaman boş** dönüyordu |

Sonuç: **CC klip kullanan her üretimde ekran atfı hiç çizilmedi.** Lisansın
resmî atıf yeri video açıklamasıdır (`kaynak.atif_listesi`) ve o **çalışıyor**;
düşen şey ürün sözünün parçası olan **görünür künye**ydi.

⚠ `/api/generate`in **22 alanlık sözleşmesi etkilenmez**: `kaynakYazi`
kullanıcıdan gelmez, medya edinimi sırasında **üretilir**. Test bunu kilitliyor.

### Düzeltme (kayıpsız taşıma + tek geometri)

1. **`pipeline._kaynak_yazi_props(s)`** — `_alt_band_props` ile aynı desen:
   künye varsa `{"kaynakYazi": ...}` (80 karakter tavanı), **yoksa `{}`** →
   künyesiz işlerde props **bit-bit aynı** kalır. Montajda
   `**_kaynak_yazi_props(s)`.
2. **`Video.tsx`**: `Sahne.kaynakYazi?: string` + `KaynakYazi` bileşeni.
   Konum **hesaplandı**, "yeterince kenarda" varsayılmadı: alt şerit altyazının
   (`paddingBottom: 72`), sol üst `GeriSayimRozeti`nin, üst orta
   `OverlayBaslik`ın → **sağ üst boş**. Oran I-39'da ölçülen
   `KAYNAK_ETIKETI_ALTYAZILI` (**0.075**), kenar **64 px** (ölçüyle oranlanır).
3. **`hizli_render`**: `x=w-tw-26:y=h-th-22` → `x=w-tw-64:y=h*0.075`.
   Eski konum 1080p'de alt kenardan 22 px'teydi — yayın güvenli alanının
   (64 px) **dışında**. İki renderer artık **aynı sayıları** kullanıyor;
   **ikinci aritmetik yok** (I-40 dersi).

### Testler (red-first) — gerçek sözleşme akışında

Kırmızı önce çökmeden koştu: 19 hedefli kontrolün **11'i XX**. `pipeline.py`
import anında `/opt/vidrush` altına yazmaya çalıştığı için **import edilmez**;
`_kaynak_yazi_props` **kaynaktan çıkarılıp yalıtılmış koşturulur** — davranış
gerçekten ölçülür, dizgi eşleşmesi değil. Düzeltme sonrası **19/19 yeşil**.

⚠ Yol boyunca **kapının kendi belgesini kusur sanması** yakalandı ve
düzeltildi: ilk sürümde testler dosya metninde `y=h-th-22` arıyordu ve
*"eski sabit şöyleydi"* diyen **açıklama satırı** kapıyı kırıyordu. Kapı artık
**çizilen ifadeyi** ölçüyor (fonksiyon gövdesinden yorumlar ayıklanır, TSX
bileşeninin gövdesi izole edilir).

| Paket | A | B | C | D | E | F | G | H | I | Toplam |
|---|---|---|---|---|---|---|---|---|---|---|
| Zengin venv | 125 | 200 | 148 | 95 | 127 | 244 | 218 | 257 | **1806** | **3220** |

0 hata. Faz I 1787 → **1806** (+19). 2 BLOKE (I-33 kaydı + opsiyonel fixture).

### ✅ Değişen kompozisyonun 1080p pilotu: `vidrushvideo_kunye_i41.mp4`

Props **üretim hattının kendi yardımcısıyla** kuruldu; medya/ses **önbellekten**;
ağ yok, **$0.00**. Ölçümler (`outputs/sample/vidrushvideo_i41_rapor.json`):

- **1920×1080 @ 30**, aac 48 kHz/2ch, 12.05 sn, 54.4 MB · **2 kesme**
- LUFS −15.02 / TP −4.49 · sessizlik 2 aralık (1.92 sn) · **11 kare**
- kenar siyahlığı **0/48 ihlal**
- **KAYIPSIZLIK ÖLÇÜLDÜ**: künyeli 2 sahnede alan props'a taşındı, künyesiz
  sahnede alan **hiç geçmedi**
- **KARE KANITI**: 2.01 sn'de `Famartin / CC BY-SA` **sağ üstte çizili**
  (önceden **hiçbir şey** yoktu); 10.04 sn'de künye **yok** — eski davranış
  künyesiz sahnede birebir korunuyor

⛔ **POST-QA: FAIL — sahte PASS verilmedi.** Dört bulgunun **hiçbiri**
`kaynakYazi` değişikliğinden gelmiyor; nedenler ayrıştırıldı:

| bulgu | gerçek nedeni |
|---|---|
| `POST-SESSIZ-ORAN` %16 (tavan %15) | Pilot anlatımı önbellek master'ından **4'er sn dilimlendi**; cümle araları sessizlik olarak sayıldı. Kaynak sesin özelliği. |
| `POST-OPTIK-DURGUN` ×3 | `VidrushVideo` zoom hızını **sahne indeksinden** deterministik seçiyor (`ZOOM_KOVA`); indeks 0 kovası **%0.4/sn** (ihmal edilebilir). 3 kısa sahnede hareket, **editorv2 için kalibre edilmiş** 2.0 eşiğinin altında kaldı. |
| `POST-LUFS` −15.02 (warn) | Pilot dilimleri **master'lanmadı**; üretim hattı mastering'i render sonrası ayrı adımda yapıyor. |

Eşik **gevşetilmedi**, pilot **eşiği geçsin diye ayarlanmadı**. I-41'in iddiası
(künye taşınıyor ve çiziliyor) **kareyle** ve **props ölçümüyle** kanıtlandı.

⚠ **KOŞULMAYAN**: `/api/generate`in tam hattı (ücretli LLM + TTS) bu oturumda
**çalıştırılmadı**; koşan şey I-41'in değiştirdiği yerdir — pipeline props
sözleşmesi → `VidrushVideo`.

### ✅ editorv2 hattı — GERİLEME YOK

`editorv2_lawn_i41.mp4` yeniden üretildi: sadakat kapısı `beat/varlık esit=True`,
POST-QA **PASS**, kenar 0/101, LUFS −14.27. I-39 render'ıyla **11 karenin
11'i de SHA-256 birebir aynı**. Lawn pilotunun **semantik kusurları duruyor**
(b001/b002/b005) — **kabul edilmiş MP4 değildir**, mutlak yol verilmedi.

### SONRAKİ ATOM (I-42) — yalnız ölçülen kusurdan

1. **`VidrushVideo` açılış sahnesi neredeyse durağan**: `ZOOM_KOVA` indeks 0
   kovası %0.4/sn veriyor ve kısa sahnede "donmuş görüntü" hissi ölçüldü
   (POST-QA optik eşiğinin altında). Dar, bedava, ölçülebilir.
2. **Önizlemede altyazı hiç çizilmiyor** (I-40'ta ölçüldü).
3. **Medya seçiminde semantik doğrulama yok** (b001/b002/b005) — ayrı ve
   daha büyük atom; I-34/I-35'te iki seçenek ölçülüp elendi.

---

## 88. FAZ R-1c-b — TENANT BAŞINA SON 3 KABUL EDİLMİŞ VİDEO (14 Ağu)

> **Durum: kütüphane yaşam döngüsü + listeleme sözleşmesi kuruldu.
> **Saf metadata** — Mac'te medya üretilmedi/saklanmadı, modül dosya
> **silmiyor**. A–I yeşil (**3938**, 0 hata, 2 bilinen BLOKE).
> Deploy YOK. $0.00.**
> Değişen: **yeni** `webapp/kutuphane.py`, `webapp/testler/test_faz_i.py`
> (§40t, 26 kontrol).

### Kabul kapısı — belirsizse girmez

Kütüphaneye **yalnızca** başarılı **ve** QA'dan kabul edilmiş final video
girer:

| Durum | Sonuç |
|---|---|
| `bitti` + QA **PASS** | ✅ girer |
| `bitti` + QA **WARN** | ✅ girer (uyarı teslim edilebilirliği bozmaz) |
| QA **FAIL** | ⛔ girmez |
| QA **ölçülmemiş** | ⛔ girmez — *"muhtemelen iyidir" denmez* |
| `hata` / `uretiliyor` | ⛔ girmez |
| video dosyası yok | ⛔ girmez |

### Retention — güvenli yaşam döngüsü

Tenant başına **en fazla 3**. 4. kabul edilince **en eski** kayıt
**silme kuyruğuna** alınır (`sebep: TAVAN-ASILDI`) ve kütüphaneden düşer.

⚠ **Modül dosya SİLMEZ** — yalnızca kuyruk döndürür; gerçek silme
**remote lifecycle işinin** işidir. Sıralama **en yeni önce**; geç gelen
eski tarihli kayıt en yeniyi **düşürmez**; aynı iş iki kez eklenince
**çoğalmaz** (idempotan).

### Tenant izolasyonu — iki savunma hattı

1. Listeleme yalnız **o tenant'ın** kayıtlarını döndürür
2. ⚠ İkinci hat: kaydın `tenant_id`'si isteyenle **eşleşmiyorsa** eleniyor
   (veri yanlış yazılmış olsa bile sızmaz)

Tenant kimliği yoksa listeleme **reddediliyor**.

### Signed URL — talep anında, saklanmadan

Kayıtta `video_url` **yok** (`signed_url_saklanir: False`). `listele()`
sırasında **talep anında** üretiliyor ve **tenant korumalı**. İmzalayıcı
yoksa **sessiz boş link yok** — `imzalanamadi: True` açıkça işaretleniyor.

### Metadata

`qa(durum/fail/warn/puan)` · `provenance(provider_used, fallback_reason,
model, kredi_tuketildi, lisanslar, kaynaklar)` · `kabul_zamani` ·
`sure_sn`. ⚠ **Eksik alan uydurulmuyor** — bilinmiyorsa `None`.
Fallback nedeni de taşınıyor (görünür kalıyor).

### Kalan

Uçların (`/api/generate`, `/api/job`, `/ciktilar`) oturuma **bağlanması**
ve dashboard UI hâlâ **yapılmadı** — sonraki atom.

---

## 87. FAZ R-1c-a — ZORUNLU OTURUM + TENANT İZOLASYONU TEMELİ (14 Ağu)

> **Durum: kimlik/oturum temeli kuruldu. Parola sözleşmesi **Argon2id**
> (fail-closed). **Gerçek hesap oluşturulmadı, parola hiçbir yere
> yazılmadı.** A–I yeşil (**3912**, 0 hata, 2 bilinen BLOKE). Mac'te medya
> üretilmedi. Deploy YOK. $0.00.**
> Değişen: **yeni** `webapp/kimlik.py`, `Dockerfile`, `Dockerfile.sunucu`,
> `webapp/testler/test_faz_i.py` (§40s, 33 kontrol).

### ⚠ Parola sözleşmesi — FAIL-CLOSED

Ölçüldü: `argon2-cffi`, `bcrypt`, `passlib` **ne yerelde ne sunucuda**
kuruluydu. İlk taslakta `scrypt → PBKDF2` zinciri kurmuştum; **kullanıcı
kararıyla bu reddedildi ve geri alındı.**

Şimdi: **yalnızca Argon2id ya da bcrypt.** Güçlü algoritma yoksa hesap
açma/giriş **başlamaz** → stabil kod **`KIMLIK-KDF-YOK`**. Zayıf geri düşüş
**yok** (`zayif_fallback: False`). Bağımlılık repo yönetiminde **sabit**:
`argon2-cffi==23.1.0` (her iki Dockerfile).

Argon2id parametreleri OWASP 2024 civarı: **64 MiB bellek, 3 tur, 4
paralellik**.

⚠ **Geçiş ayrı ve açık yol**: eski `scrypt`/`pbkdf2` kayıtları **yalnızca**
`eski_hash_dogrula()` ile doğrulanır ve `yeniden_hashle: True` döner — normal
`parola_dogrula()` bu biçimleri **geçirmez**.

### Oturum / CSRF / hız sınırı

- Oturum jetonu **HMAC-SHA256** mühürlü (`tenant.exp.imza`); **önce imza,
  sonra süre** doğrulanır (bilgi sızmasın)
- Çerez: **HttpOnly + SameSite=Lax + Secure**
- CSRF: **double-submit** (çerez + başlık), sabit zamanlı karşılaştırma
- Giriş: **5 deneme / 300 sn** kayan pencere, **IP başına ayrı** (bir
  kullanıcı diğerini kilitleyemez), pencere geçince açılır (kalıcı kilit yok)

### Tenant izolasyonu

- **Kimlik yoksa erişim yok** (`kimliksiz_erisim: False`)
- Başka tenant'ın kaynağı → **`BASKA-TENANT`**
- ⚠ **Sahipsiz (eski) kayıt "herkese açık" sayılmıyor** →
  **`KAYNAK-SAHIPSIZ`**; sessiz sızıntı yerine açık red

### Güvenli provisioning

Hesap girdisi **yalnız** `VIDRUSH_ADMIN_KULLANICI` + `VIDRUSH_ADMIN_PAROLA`
env'inden **ya da stdin**'den okunur. ⚠ Parola **koda/commit'e/argümana
yazılmaz**, dönen kayıtta **düz metin yok** (yalnız `parola_hash`), her
hesaba **ayrı `tenant_id`**. Zayıf parola ya da eksik girdi → hesap
**açılmaz**.

⚠ **Gerçek hesap OLUŞTURULMADI.** Credential girişi son adımda kullanıcı
tarafından yapılacak.

### Kalan (R-1c-b)

Kullanıcı başına **son 3 başarılı video** yaşam döngüsü + dashboard
kütüphanesi; uçların (`/api/generate`, `/api/job`, `/ciktilar`) oturum
zorunluluğuna **bağlanması** — bu atomda **yalnız temel** kuruldu.

---

## 86. FAZ R-1b — TENANT PROVIDER ZİNCİRİ (adapter → motor → timeline, 14 Ağu)

> **Durum: Magnific artık yalnız bir ayar/UI kaydı **değil** — planlayıcıdan
> timeline'a giden medya edinim zincirinin halkası. **Gerçek OAuth YOK,
> kredi TÜKETİLMEDİ**, her şey test-double + ücretsiz stok fallback.
> A–I yeşil (**3873**, 0 hata, 2 bilinen BLOKE). Mac'te medya üretilmedi.
> Deploy YOK. $0.00.**
> Değişen: **yeni** `webapp/medya/saglayici_motoru.py`,
> `webapp/testler/test_faz_i.py` (§40r, 26 kontrol).

### Zincir

```
planlayıcı(shot_istegi) → provider registry → job-scope token
   → MCP capability discovery → edinim → ölçüm(ffprobe) → provenance → timeline
```

Dış dünyanın tamamı **enjekte** ediliyor (`mcp_cagirici`, `sifre_cozucu`,
`olcer`, `ucretsiz_arayici`) — mevcut okuyucu-enjeksiyonu deseni. Modül
**ağa çıkmaz, medya açmaz** (testle doğrulandı).

### ⚠ Uydurma yok — capability discovery

| Sağlayıcı yeteneği | Sonuç | `fallback_reason` |
|---|---|---|
| `video.search` var | magnific / arama | *(boş)* |
| arama yok, `video.generate` var | magnific / üretim | `STOK-ARAMA-YETENEGI-YOK` |
| ikisi de yok, `video.transform` var | magnific / dönüşüm | `STOK-ARAMA-VE-URETIM-YOK` |
| hiçbiri yok | **ücretsiz stok** | `UYGUN-YETENEK-YOK` |
| aday dönmedi | **ücretsiz stok** | `SAGLAYICI-ADAY-DONDURMEDI` |

Keşif çağırıcısı yoksa **"arama vardır" denmiyor** (`olculdu: False`).
Rapor her durumda **`provider_used` + `fallback_reason`** taşıyor.

### ⚠ Şifreleme uydurulmadı

`cryptography` **sunucuda kurulu değil**. Bu yüzden şifre çözücü **enjekte
edilen bir arayüz**: gerçek çözücü verilmezse token **kullanılmaz**
(`SIFRE-COZUCU-YOK`) ve ücretsiz stok'a düşülür. **Düz metin token kabul
edilmiyor.** ⚠ Bu, R-1c'nin somut ön koşulu: sunucuya `cryptography` kurulmalı.

### Tenant izolasyonu

- Başka tenant'ın bağlantısı **asla** seçilmiyor
- Onaysız / kredi onayı olmayan bağlantı **kullanılmıyor**
- Kullanıcı açıkça Magnific dediyse ve bağlantı yoksa **sessiz geçiş yok** —
  `MAGNIFIC-KULLANILAMIYOR:<neden>` görünür
- **Tenant tokeni istemciye çıkmıyor**: `baglanti_ozeti()` yalnız
  durum/kredi/model/`token_var` döner, token'ı **hiçbir biçimde** vermez

### Provenance

`saglayici · edinim_yolu · scene_id · sorgu · kaynak_url · lisans ·
lisans_kaydi · eser_sahibi · model · kredi_tuketildi · job_id · tenant_id ·
teknik · ses_kanali`. ⚠ **Auto mod model adını garanti etmez** →
`model_unknown/auto` yazılır; gerçek model adı verilirse **aynen** korunur.

### Timeline

Sıralama: **semantik örtüşme → gerçek video tercihi → piksel → bitrate**.
Eşit semantikte **video fotoğrafa tercih ediliyor**. **Negatif ihlali olan
aday eleniyor** (puanla gizlenmiyor). **Aynı kaynak toplam ≤8 sn** (J-5b
şartı) ve yerleşimde **kaynak sesi sıfır** işaretli.

---

## 85. FAZ R-1a — SUNUCU KAPASİTE ÖLÇÜMÜ + İMZALI ÇIKTI URL'LERİ (14 Ağu)

> **Durum: teslim odağına geçildi. Sunucu kapasitesi **gerçek ölçüldü**
> (blokaj YOK) ve `/ciktilar/` ucu **imzalı + süreli** hâle getirildi.
> A–I yeşil (**3847**, 0 hata, 2 bilinen BLOKE). Mac'te medya **üretilmedi**.
> Deploy YOK (henüz). $0.00.**

### Sunucu gerçeği (salt-okunur denetim)

⚠ **CLAUDE.md güncel değil**: canlı sunucu `204.168.136.159` **değil** —
`deploy.sh`'in kullandığı **`185.23.17.240`** (RX-4, 1 Ağu'da taşınmış).
Eski IP hâlâ 200 döndüğü için yanıltıcı.

| | |
|---|---|
| Host | 10 vCPU · 9.9 GB RAM · 10 GB swap · 107 GB boş disk · yük 0.00 |
| Konteyner `bedosaho` | **bellek/CPU limiti YOK** (host'un tamamı), 2 gündür ayakta |
| Araçlar | ffmpeg 5.1.9 · node v22 · python 3.11 |
| `RENDER_MOTOR` | **ffmpeg** (Remotion değil → bellek endişesi geçersiz) |
| `EDITOR_V2` | **kapalı** (K-atomlarının hattı üretimde devre dışı) |
| `PEXELS_KEY` | **boş** |

### Kapasite ölçümü — 55–65 sn 1080p **sorun değil**

Sunucuda gerçek render (zoompan + CRF18 + aac):

| Ölçü | Sonuç |
|---|---|
| 60 sn 1080p30 render süresi | **18 saniye** |
| Tepe bellek (RSS) | **968 MB** |
| Çıktı | 6.8 MB · h264/aac · 1920×1080 @30 |

⚠ Önceki "2 GB boşta, render düşebilir" endişem **yanlıştı**: konteynerde
limit yok ve motor ffmpeg. Ölçmeden karar vermemek doğru olmuş.

### İmzalı çıktı URL'leri (yeni `webapp/imzali_url.py`)

⚠ **Ölçülen kusur:** `/ciktilar/{dosya}` **imzasızdı** — dosya adını bilen
herkes indirebiliyordu. Bu, çoklu kullanıcı gelmeden **bugün** bir sızıntı
yolu ve tenant izolasyonunun (R-1b) **ön koşulu**.

- **HMAC-SHA256**, `hmac.compare_digest` ile sabit zamanlı karşılaştırma
- **TTL zorunlu** (`exp`), varsayılan 6 saat
- Anahtar: `IMZA_ANAHTARI` env → `veri/.imza_anahtari` (**0600**) → üretilir.
  **Repoda değil, loglanmıyor.**
- Anahtar kurulamazsa uç **sessizce korumasız çalışmaz** → **503**
- Yol gezinmesi kesiliyor (`basename`)
- İş sözleşmesi imzalı `video_url` + `research.manifest_url` üretiyor;
  **imzalayıcı verilmezse eski davranış korunuyor** (geriye uyumlu)
- Arayüz artık ham `ciktilar/...` yolu **kurmuyor**

⚠ **Bilerek sıkılaştırma:** imzasız istek artık **403** döner, 404 değil —
dosyanın varlığı imzasız isteğe **sızdırılmaz**. `test_faz_h`'deki eski
404 beklentisi bu gerekçeyle güncellendi (gerileme değil).

16 red-first kontrol: bozuk imza, başka dosyaya taşınan imza, süresi dolmuş
bağlantı, imza geçersizken "süresi dolmuş" bilgisinin **sızmaması**, path
traversal, 0600 izni, geriye uyumluluk.

### ⚠ R-1b için BAĞLAYICI mimari (kullanıcı kararı — henüz uygulanmadı)

**Magnific Bağla yalnız UI/ayar kaydı DEĞİL**, doğrudan medya edinim
motorunun **tenant'a özel provider'ı**:

1. Planlayıcı her sahne için **semantik shot sorgusu + negatifler + oran +
   süre + kalite hedefi** üretir.
2. **Provider registry** o tenant'ın **aktif ve onaylı** Magnific MCP
   bağlantısını seçer.
3. Remote worker **job-scope şifreli token** ile MCP **capability
   discovery** yapar, uygun arama/üretme/dönüştürme aracını çağırır.
4. Sonuç **object storage'a ingest** edilir; **remote ffprobe** ile en
   yüksek çözünürlük/bitrate/codec seçilir.
5. **Kaynak audio mutlak sıfır** (K-2) ve **aynı kaynak toplam ≤8 sn**.
6. **provenance/license/model/credit/job** metadata kaydedilir.
7. Medya seçici: **semantik uygunluk + gerçek-video tercihi + tekrar +
   teknik kalite** ile rank eder, timeline'a yerleştirir.

⚠ Magnific **stok arama sunmuyorsa uydurulmaz**: mevcut generate/transform
capability'si kullanılır **ya da** ücretsiz stok fallback'e geçilir;
raporda **`provider_used`** ve **`fallback_reason`** görünür.
⚠ **Tenant tokeni istemciye ÇIKMAZ.** UI'de Otomatik/Magnific/Ücretsiz stok
seçimi ve **kredi onayı** görünür. R-1b'de **red-first adapter → motor →
timeline entegrasyon testi ZORUNLU**.

---

## 84. FAZ K-3 — AÇILIŞ BAŞLIK/ŞERİT SÜRESİ (14 Ağu)

> **Durum: açılış başlığı artık **metinden** hesaplanıyor ve intro beat'i
> **asla** aşmıyor. Gerçek pilot başlığı **5.325 sn → 1.714 sn**.
> **MEDYASIZ ATOM**: Mac'te medya/ses/kare/render/QA artefaktı üretilmedi.
> A–I yeşil (**3828**, 0 hata, 2 bilinen BLOKE). Deploy YOK. $0.00.**
> Değişen: `webapp/editor/tipografi.py`, `webapp/editor/plan.py`,
> `webapp/editor/qa_on.py`, `webapp/testler/test_faz_i.py` (§40p, 25 kontrol).

### Ölçülen kusur

Açılış başlığı `min(5.5, b.sure_sn + 1.5)` ile kuruluyordu:

- **Metne hiç bakmıyordu** — iki kelimelik başlık da 5.5 sn duruyordu.
- **`+1.5` ile intro beat'i aşıyordu** → anlatıcı cümlesi bittikten sonra
  yazı ekranda **asılı** kalıyordu.

Gerçek pilot: `"THERE IS A BAG OF GRASS"`, beat 3.825 sn →
eski **5.325 sn** (1.700 sn asılı) · K-3 **1.714 sn** (0.000 sn asılı).

### Politika

```
sure = max(karakter/CPS, kelime/KPS) × katsayi
       ↑ min_gorunme_sn alt sınırı
       ↓ ÜÇ SERT ÜST SINIR: mutlak tavan · intro beat sonu · asılı kalma 0
```

| Sabit | Değer | Kaynak |
|---|---|---|
| `BASLIK_MAKS_CPS` | 20.0 | **TÜRETİLMİŞ** — `ALTYAZI_MAKS_CPS` ile aynı okuma hızı |
| `BASLIK_KELIME_KPS` | 3.5 | beyan edilmiş (~210 kelime/dk) |
| `BASLIK_MAKS_SN` | 5.5 | beyan edilmiş mutlak tavan |

Stabil kod: **`KALITE-BASLIK-SURESI`** (fail). Kısaltma sessiz değil —
`kisaltildi` bayrağı raporlanıyor.

### K-4 kancası (gevşek, geriye uyumlu)

`katsayi` varsayılanı **1.0** → mevcut davranışı yalnızca **güvenli
kısaltır**. `edit_seviyesi` geldiğinde az/orta/yüksek katsayıları **aynı
fonksiyona** bağlanacak. ⚠ Katsayı **üst sınırları delemez** (beat hâlâ
tavan). K-4 bu atomda **uygulanmadı** — çalışan kodda `edit_seviyesi` yok
ve 22 alan sözleşmesine girmedi.

### Red-first (25/25)

Eski formülün ürettiği başlık kapıda **FAIL** (1.7 sn asılı), yeni hesabınki
**temiz** (0.0). Kısa/orta/uzun başlıklar **farklı** süre alıyor; çok kısa
beat'te süre beat'e kırpılıyor; mutlak tavan korunuyor; bozuk girdi hüküm
vermiyor.

⚠ Test yazarken **I-9 tuzağına ikinci kez** düşüldü: ham dize taraması
K-4 kancasını anlatan **yorumu** yakaladı. `_kod_yalniz` ile düzeltildi.

⚠ Uygulama sırasında `olcum` sözlüğü henüz kurulmadan kullanıldı ve uçtan
uca fixture kırıldı; ölçüm K-1/K-2 ile aynı desende doğrudan `q.olcumler`e
yazılarak düzeltildi.

---

## 83. FAZ K-2 — ARKA PLAN UĞULTU KAPISI + KAYNAK SESİ SIFIR (14 Ağu)

> **Durum: TTS dışı sürekli hiss/rumble/wind için **ölçülebilir öznitelikler,
> güven aralığı ve stabil hata kodu** tanımlandı; kaynak video sesi render
> sözleşmesinde **mutlak sıfır** olarak kilitlendi. **MEDYASIZ ATOM**:
> Mac'te medya/ses/kare/render/QA artefaktı **üretilmedi**, `ffmpeg`
> çalıştırılmadı. A–I yeşil (**3803**, 0 hata, 2 bilinen BLOKE). Deploy YOK.
> $0.00.**
> Değişen: **yeni** `webapp/editor/ses_gurultu.py`, `webapp/editor/plan.py`,
> `webapp/editor/qa_on.py`, `webapp/testler/test_faz_i.py` (§40o, 38 kontrol).

### Kaynak video sesi: mutlak sıfır

`KAYNAK_SES_POLITIKASI = "sifir"` — tartışılabilir bir ayar **değil**.
Harici klibin kendi sesi (rüzgâr/trafik/konuşma/müzik) mikse **giremez**.
Üç katmanda kilitli:

1. Renderer zaten `OffthreadVideo … muted` (`Kamera.tsx`, `Video.tsx`).
2. `render_plan` artık **makine okunur** `ses_kanali: "sifir"` yazıyor.
3. `kaynak_ses_sozlesmesi()` her video çekimini denetler → ihlal
   **`KALITE-KAYNAK-SES-SIZINTI`** (fail).

### Ölçülebilir öznitelikler (hepsi remote worker'dan **sayı** olarak)

`anlatim_lufs`, `konusma_disi_lufs`, `sureklilik_orani`, `spektral_duzluk`,
`dusuk_frekans_orani` (<120 Hz), `yuksek_frekans_orani` (>6 kHz),
`belirsizlik_db`.

⚠ Modül **medya açmaz, ffmpeg çalıştırmaz, dosya yazmaz** — mevcut
`benzerlik_okuyucu` / `enerji_okuyucu` / `kare_okuyucu` enjeksiyon deseninin
aynısı. Bu sayede karar mantığı yerelde **medyasız** test edilebiliyor.

### Karar: üç koşul **birlikte**

Gürültü ancak (a) **duyulabilir** (SNR eşiğin altında), (b) **sürekli** ve
(c) **genişbant/rumble/hiss izi** taşıyorsa vardır. Tek başına düşük SNR bir
müzik yatağında da olur — bu yüzden üçü birden aranır.

| Eşik | Değer | Kaynak |
|---|---|---|
| `GURULTU_SNR_ESIGI_DB` | 30.0 | **TÜRETİLMİŞ** — `DUYULABILIR_FARK_DB` ters yönde okundu: 30 dB'den fazla altta kalan taban **duyulmaz** |
| `SUREKLILIK_ESIGI` | 0.80 | beyan edilmiş tasarım eşiği |
| `SPEKTRAL_DUZLUK_ESIGI` | 0.35 | beyan edilmiş |
| `RUMBLE/HISS bant oranı` | 0.30 / 0.25 | beyan edilmiş |

⚠ "Beyan edilmiş tasarım eşiği" etiketi `DUYULABILIR_FARK_DB`'nin kendi
dürüstlük etiketiyle **aynıdır**: dinleme testi değildir, parametre olarak
dışarı açıldı, `kapsam_ozeti()["esik_kaynagi"]` bunu **raporlar**.

### Güven aralığı — emin değilsen FAIL etme

SNR ± `belirsizlik_db` aralığı eşiği **kesiyorsa** sonuç `supheli` olur ve
hüküm **WARN**'dır, FAIL değil. Aralık tamamen eşiğin altındaysa `gurultu`,
tamamen üstündeyse `temiz`. Ölçüm eksikse `olculdu: False` — **"temiz"
denmez**.

### Deterministik akış

```
gurultu_olcusu()  →  filtre_profili_oner()  →  temizleme_dogrula()  →  gurultu_karari()
```

- **Filtre profili güvenli:** rumble → `highpass f=80` (yetişkin konuşma
  temel frekansı ~85 Hz'in **altında**); hiss/genişbant → `afftdn` ama
  bastırma **≤6 dB tavanlı**. **Konuşma bandı 300–3400 Hz'e dokunulmaz** ve
  profil bunu açıkça beyan eder. Temiz içerikte filtre **önerilmez**.
- **Doğrulama:** temizleme sonrası konuşma bandı `>1.0 dB` gerilerse **ya da**
  ASR güveni `>0.02` düşerse **filtre reddedilir** — netliği bozan denoise
  **uygulanmaz**.
- **FAIL yalnızca** gürültü güven aralığıyla kesin **ve** güvenli temizleme
  ya denenmedi ya da konuşmayı bozmadan gideremedi ise:
  **`KALITE-SES-GURULTU`**.

### Red-first (38/38)

| İddia | Sonuç |
|---|---|
| Kaynak sesini kullanmaya çalışan çekim → **yakalanır** | ✅ |
| Süreksiz gürültü → **FAIL değil** | ✅ |
| Spektral iz yok (tonal/müzik yatağı) → **gürültü sayılmaz** | ✅ |
| Güven aralığı eşiği kesiyor → **WARN, FAIL değil** | ✅ |
| Belirsizlik büyüdükçe şüpheli bant **genişler** | ✅ |
| Ölçüm eksik → **hüküm yok** | ✅ |
| Konuşma bandı tavandan fazla geriler → **filtre reddedilir → FAIL** | ✅ |
| Gürültü gitti + konuşma korundu → **TEMİZLENDİ** | ✅ |
| Çalışan kodda `subprocess/ffmpeg/open/os.path` **yok** | ✅ |

⚠ Test yazarken I-9 tuzağına düşüldü: ham dize taraması modülün **kendi
docstring'ini** (`FFMPEG CALISTIRMAZ`) yakaladı. `_kod_yalniz` ile yalnız
**çalışan kod** taranacak şekilde düzeltildi.

### Medyasız atom kanıtı

`cikti/` ve `outputs/` altında **tek bir yeni dosya oluşmadı**; değişen dört
dosyanın hepsi kaynak koddur.

⚠ **Kapanış ölçütü hatırlatması:** bu atom karar sözleşmesini kilitler; aynı
davranışın `server.py` → pipeline üzerinden **otomatik** çalışması R-1 ile
gelecek. Scratch kanıt atom kapatmaz.

---

## 82. FAZ K-1 — VİDEO KAMERA MUAFİYETİ + B-ROLL ÇEŞİTLİLİK KAPISI (14 Ağu)

> **Durum: video ağırlıklı kurguyu **yapısal olarak imkânsız** kılan kapı
> düzeltildi. Kamera-hareketi bacakları (`islev_tekrari`, `pencere_tekrari`)
> gerçek video çekimlerde **muaf**; boşluk boş bırakılmadı, yerini
> `KALITE-BROLL-CESITLILIK` aldı. **MEDYASIZ ATOM**: Mac'te medya, ses, kare,
> render cache, QA artefaktı veya MP4 **üretilmedi**. A–I yeşil (**3765**,
> 0 hata, 2 bilinen BLOKE). Deploy YOK. $0.00.**
> Değişen: `webapp/editor/kalite_kapisi.py`, `webapp/editor/qa_on.py`,
> `webapp/testler/test_faz_i.py` (§40n, 24 kontrol).

### Ölçülen sorun (J-5b denemesinde)

1 dakikalık video ağırlıklı örnek **iki kez PRE-QA'da bloke oldu**. Kök neden:
J-5a'dan beri gerçek video çekimleri plan tarafında **`static` diye
etiketleniyor** (hareket görüntünün kendisinde; dijital zoom uygulanmıyor).
I-24'ün *"aynı işlevde aynı kamera hareketi olamaz"* kuralı bu **etiketi**
gerçek bir kamera kararı sanıyor ve **4+ video sahnesinde işlev çakışması
kaçınılmaz** oluyordu → `KALITE-MOTION-ISLEV-TEKRAR` FAIL.

⚠ Bu bir **etiket artefaktıydı**, ölçülen bir kusur değil.

### K-1 politikası (deterministik, eşik uydurulmadı)

1. **Muafiyet:** `islev_tekrari` ve `pencere_tekrari` bacakları
   `medya_turu == "video"` çekimleri **atlar** — enerji (I-44) ve statik-süre
   (J-5a) bacaklarındaki desenin **aynısı**. Muaf çekimler
   `kamera_kapisi_muaf_video` alanında **sayılabilir** (sessiz değil).
2. **Yerine geçen kapı:** `broll_cesitliligi_ozeti` içinde **B-roll görsel
   dili** bacağı — I-24'ün işlev kuralının **birebir** karşılığı, `hareket`
   yerine **`cekim_turu`**. Aynı anlatı işlevindeki iki video çekim aynı
   çekim türünü alırsa izleyici aynı görsel cümleyi iki kez görür.
   - `video_islev_tur_tekrari` → **FAIL** `KALITE-BROLL-CESITLILIK`
   - `video_pencere_tur_tekrari` → **WARN** (aynı kod)
3. **Sayısal eşik YOK.** J-3'ün oranları (`video_sure_orani`,
   `benzersiz_varlik_orani`, …) **hâlâ yalnız rapor**: `hedef: None`,
   `enforce: False`. Kapıya bağlı alanlar sözleşmede sayılı
   (`kapiya_bagli`).

### Red-first

| İddia | Kanıt |
|---|---|
| Aynı işlevde iki **video** → artık `islev_tekrari` **yok** | ✅ |
| Aynı işlevde iki **fotoğraf** aynı hareket → **hâlâ FAIL** (I-24 korundu) | ✅ |
| Hiç video yokken ölçüm **eski davranışla aynı** | ✅ |
| Aynı işlevde iki video **aynı çekim türü** → B-roll kapısı **ateşler** | ✅ |
| Çekim türü **farklıysa** → **ateşlemez** (yanlış pozitif yok) | ✅ |
| Fotoğraf çekimleri B-roll kapısını **tetiklemez** | ✅ |
| Kod `KALITE_KODLARI`'nda → kalite kapısı kapalıyken **üretilmez** | ✅ |

### ⚠ Bilerek kapsam dışı

`ardisik_tekrar` (bitişik aynı hareket) **dokunulmadı** — K-1 kapsamında
değildi. Sonuç: **iki video sahnesi hâlâ yan yana gelemez**, yani video
oranı sahne sayısının ~%50'siyle sınırlı. Sıradaki atom adayı (K-1b).

### Medyasız atom kanıtı

Bu atomda dosya okunmadı/indirilmedi; `cikti/` ve `outputs/` altında **tek
bir yeni dosya oluşmadı**. Değişen üç dosya da kaynak koddur.

---

## ⏭ SIRADAKİ ATOM SIRASI (kullanıcı tarafından belirlendi)

⚠ Hepsinde: **Mac'te medya artefaktı üretilmez**, tüm medya QA/render
**yalnız sunucuda**. Scratch çözüm atomu **kapatmaz** — aynı davranış
server/pipeline üzerinden **otomatik** çalışmalı. Deploy yalnız ilgili tam
regresyon yeşil + repo temiz + origin güncel + rollback hazırsa.

| # | Atom | Özet |
|---|---|---|
| **K-2** | **Arka plan uğultu/rüzgâr kapısı** | TTS dışı sürekli hava/hiss/rumble tespiti → deterministik temizleme ya da FAIL. Kaynak video sesi **daima sıfır**. Konuşma netliğini bozan denoise **uygulanmaz**. Ayrı stabil hata kodu + red-first test. |
| **K-3** | **Açılış yazı şeridi süresi** | İlk başlık/şerit metni ekranda asılı kalmasın. Süre **kelime/karakter sayısından** okunabilir min+max ile deterministik; anlatıcı cümlesi bittikten sonraki asılı kalma sınırlı; **intro beat süresini aşamaz**; profile göre farklı ama her profilde **üst sınır**. Stabil kod + red-first görsel-zaman çizelgesi testleri. |
| **K-4** | **`edit_seviyesi` = az \| orta \| yuksek** | ChatGPT düşünme modu benzeri **tek üç-konumlu** çubuk/radio-segment. **22 alan sözleşmesini bozmadan** bağlanır. Seviyeler etiket değil **ölçülebilir profil**: min gerçek-video oranı, ort. plan süresi, cutaway yoğunluğu, geçiş çeşitliliği, J/L-cut sayısı, SFX yoğunluğu, kapanış gücü eşikleri **farklı**; aynı girdiyle çıktılar testte **bariz ayrışmalı**. |
| **K-5** | **Belgesel anlatı kapısı** | hook→bağlam→kanıt/karşıtlık→sonuç→kapanış yapısı + anlatıcı/B-roll **semantik eşleşmesi**. |
| **K-1b** | **Bitişik video kısıtı** | `ardisik_tekrar`ın video çekimlerdeki karşılığı; video oranı tavanını açar. |
| **M-1** | **Magnific MCP sağlayıcı adaptörü** | Resmi uç: `https://mcp.magnific.com`. Sunucu **provider adapter** + kullanıcıya özel **Connect Magnific OAuth/MCP** + **şifreli token** + **tenant izolasyonu** + balance check + varlık arama/edinim + **açık kredi/model onayı** + idempotency/retry/timeout + provenance/license metadata + **object storage ingest** + ffprobe kalite seçimi. Parola/API key **alınmaz**. Auto mode kullanılırsa provenance'a `model_unknown/auto` yazılır; kalite için **açık model seçimi** tercih edilir. Magnific yok/erişilemezse **ücretsiz stok sağlayıcı fallback**. ⚠ MCP yalnız ajan istemcisi olduğundan **resmî çok-kullanıcılı OAuth yetkisi kanıtlanmadan hesap bağlama/deploy YOK**: adaptör **test-double** ile kurulur, gerçek OAuth adımı **güvenli blokaj** olarak raporlanır. Kaynak sesi **daima sıfır**, kaynak başına toplam **≤8 sn** kapıları korunur. |
| **R-1** | **Remote-only iş mimarisi** | web isteği→server job→queue→ephemeral worker→sağlayıcı→object storage→remote TTS/render/PRE-QA/POST-QA→**signed download URL**. Mac yalnız kaynak kodu geliştirme + salt-okunur denetim. Kullanıcı izolasyonu, şifreli OAuth token, kredi onayı, retry/failover/idempotency, lifecycle TTL/cleanup, job status sözleşmesi **zorunlu**. |

---

## 81. FAZ J-5a — İLK GERÇEK VİDEO EDİNİMİ VE PİLOT (14 Ağu)

> **Durum: J-4 kapısı edinim hattına **bağlandı** ve Wikimedia Commons'tan
> **tam 1** gerçek video indirildi (1920×1080 VP9, 52.2 Mbps, 12.47 sn,
> 81.4 MB, CC BY-SA, **$0.00**). 25.30 sn 1080p pilot üretildi:
> **POST-QA PASS, kalite 100/100**, gerçek video oranı **%0.0 → %21.2**.
> A–I yeşil (**3741**, 0 hata, 2 bilinen BLOKE).
> ⚠ **KABUL EDİLMİŞ MP4 DEĞİL** — teknik PASS ama semantik değil (aşağıda).
> Deploy YOK.**

### İndirilen varlık ve J-4 kanıtları

| Kanıt | Değer |
|---|---|
| Başlık | `Irrigation sprinkler 7 2017-06-25.webm` |
| Sağlayıcı | wikimedia (anahtarsız) · **eser sahibi** F ASTILY |
| Lisans | **cc-by-sa** · atıf zorunlu, künye ekranda çiziliyor |
| Kaynak URL | `commons.wikimedia.org/wiki/File:Irrigation_sprinkler_7_2017-06-25.webm` |
| Lisans **kaydı** | Commons API `imageinfo/extmetadata` (izleme sayfası **değil**) |
| İndirme zamanı | `2026-08-14T08:57:23Z` |
| codec / çözünürlük / bitrate | **vp9 / 1920×1080 / 52 242 783 bps** (ffprobe ile ölçüldü) |
| Boyut | 81.4 MB (tavan 300 MB) · **1 dosya** (tavan 1) |
| Maliyet | **$0.00** |

Seçim kuralı kodda: tavan içindeki izinli özgünler arasından **en yüksek
çözünürlük → en yüksek bitrate → en uzun süre**. Süresi yetersiz aday
(`Irrigation sprinkler 9`, 7.6 sn < 8.0) elendi ve **raporlandı**.

### Kapı iki kez koştu

`video_provenance_karari()` indirmeden **önce** (aday kanıtları) ve
indirmeden **sonra** (ffprobe ile ölçülen codec/çözünürlük/bitrate) çalıştı.
Son kontrol reddetseydi **dosya silinecekti**. İndirme mevcut
`guvenli_indir` üzerinden: SSRF + içerik türü + akış sırasında bayt tavanı +
HTML izi + ffprobe decode. Redirect/HTML/bozuk medya/eksik lisans yolları
red-first testlerle kanıtlandı.

**NASA** devreye **girmedi** — sorgu uzay değil (`uzay_sorgusu_mu()` False).
Konu dışı fallback **yok**. PEXELS/PIXABAY anahtarı **aranmadı** (modülde
`os.environ`/`getenv` çağrısı yok, testle doğrulandı).

### ⚠ Gerçek videonun ortaya çıkardığı İKİ yapısal kısıt

Pilot ilk iki denemede **PRE-QA'da bloke oldu**. İkisi de gerçek bulgu:

**1. 1080p kaynak + 1080p kare = sıfır punch payı.** `punch-1.6` kadraj
ekranda **1.696×** büyütüyordu ve `KADRAJ_MERDIVENI`'nin **hiçbir basamağı**
kurtarmıyordu (fotoğraflarda 3–5× pay vardı, videoda **yok**).
→ **Düzeltme:** video kaynakta dijital zoom **uygulanmıyor**
(`static`/`tam`, `VIDEO-KAMERA-NOTR` uyarısıyla). Kapı **gevşetilmedi** —
gereksiz büyütmenin **kendisi** kaldırıldı; `KALITE-PUNCH-BUYUTME` duruyor.

**2. `static` kamera süre kapısı hareketli kaynakta geçersiz.**
`KALITE-OPTIK-DURGUN`, **durgun fotoğraf** üzerindeki statik kameradan optik
durağanlık **tahmin eder**. Gerçek videoda o tahmin yanlıştır.
→ **Düzeltme:** statik-sahne bacağı video kaynağı atlıyor — bu, **aynı
fonksiyonda zaten var olan** enerji-bacağı muafiyetinin (`medya_turu ==
"video" → continue`) birebir aynısı. Gerçek hüküm POST-QA'nın
`optik_hareket_olcusu`'nda ve **aynen yürürlükte**.

⚠ **Ampirik doğrulama:** b004 `static` kamerayla POST-QA'da optik **4.366**
ölçtü (eşik 2.0) — hareket gerçekten görüntünün kendisinde. Muafiyet ölçümü
**bypass etmiyor**.

**3. Üçüncü kusur:** `girdi_kur()` medya türünü **sabit `"image"`** yazıyordu
— J-1'de ölçülen %0'ın **mekanik nedeni buydu**. Artık varlığın kendi
türünden okunuyor.

### Pilot ölçümleri — önceki pilotla karşılaştırma

| Ölçü | i56 (önceki) | **j5a** | Değişim |
|---|---|---|---|
| `video_sure_orani` | 0.0000 | **0.2123** | **+%21.2** |
| `statik_sure_orani` | 1.0000 | **0.7877** | −%21.2 |
| video çekim sayısı | 0 | **1** | +1 |
| `donmus_kadraj_sure_orani` | 0.0 | 0.0 | = |
| `benzersiz_varlik_orani` | 1.0 | 1.0 | = |
| `tekrar_sure_orani` | 0.0 | 0.0 | = |
| Süre / çözünürlük | 25.2 sn 1080p | **25.30 sn 1080p** | = |
| POST-QA | PASS | **PASS** | = |
| Kalite puanı | 100/100 | **100/100** | = |
| Integrated loudness | −14.2 LUFS | **−14.2 LUFS** | = |
| LRA | 2.5 LU | **2.5 LU** | = |
| True peak | −3.1 dBFS | **−2.6 dBFS** | +0.5 dB |
| Sessizlik (−50 dB, 0.3 sn) | — | **0 bölüt** | temiz |
| Kare örneklemesi | 11 | **11** (6 beat) | = |
| Kesme/geçiş algılaması | — | 20 | — |
| Maliyet | $0.00 | **$0.00** | = |

Görsel doğrulama: b004 penceresinden çıkarılan kare **gerçek yağmurlama
görüntüsünü**, doğru altyazıyı ve sağ üstte `F ASTILY / CC-BY-SA` künyesini
gösteriyor.

### ⚠ KABUL EDİLMİŞ MP4 DEĞİL

Teknik taraf **tam PASS**. Semantik taraf **değil**: PRE-QA hâlâ
`KALITE-SEMANTIK-DONEM` WARN veriyor — **b001** açılış çekimi 1900 tarihli
arşiv fotoğrafını (`Vegetable, grass and flower seeds, 1900`) güncel
anlatımla eşleştiriyor. Bu I-47/I-57/I-58'den beri **açık olan** kusurdur ve
J-5a'nın kapsamı **değildi**. Ayrıca `SAGLAYICI-TEKEL` %100 ve `PERDE-EKSIK`
WARN'ları duruyor.

### ⚠ Yol boyunca yapılan hata ve düzeltmesi

İlk pilot koşumu, smoke modülünün **sabit kodlu** çıktı adlarını kullandığı
için `outputs/sample/teknoloji_i20_rapor.json` ve `i20_kare_*.png`
dosyalarının **üzerine yazdı** — I-23/I-25/I-27/I-33 kanıt artefaktları.
Rapor JSON'u git'ten **geri yüklendi** (izleniyor); PNG kareler izlenmiyor
(gitignore) ve **üzerine yazıldı**, i20 smoke'u yeniden koşularak
üretilebilir. Tekrarı önlemek için smoke çıktı adları **parametrelendi**
(`RAPOR_ADI` / `BLOKE_RAPOR_ADI` / `KARE_ONEKI`; varsayılanlar aynen eski) ve
bu testle kilitlendi.

### Testler

§40m'de **34 red-first** birim/entegrasyon kontrolü **ağsız** koşuyor (sahte
arayıcı): tavanlar, konu dışı fallback yokluğu, NASA koşulu, J-4 bağlantısı,
HTML/bozuk medya reddi, dosya silme. Üstüne davranış kilidi ve pilot kanıtı.
J-1/J-2a/J-3'ün **"video oranı sıfır"** taban iddiaları silinmedi,
**tarihlendirildi**: J-5a planı dışındaki planlarda hâlâ sıfır.

---

## 80. FAZ J-4 — VİDEO PROVENANCE/LİSANS SÖZLEŞMESİ (YALNIZ ENGELLER, 14 Ağu)

> **Durum: gerçek video edinimi için **koruyucu** sözleşme kuruldu. Bu modül
> **yalnızca engeller** — mevcut `lisans_karari()` reddettiyse o kararı
> **asla çevirmez**, görsel yolu **hiç değişmez**. Ağ YOK, indirme YOK,
> render/seçim davranışı **değişmedi** (SHA ile kanıtlandı), edinim hattına
> **bilerek bağlanmadı**. A–I yeşil (**3688**, 0 hata, 2 bilinen BLOKE).
> $0.00.**
> Değişen: **yeni** `webapp/medya/video_lisans.py`,
> `webapp/testler/test_faz_i.py` (§40l, 40 kontrol). Başka **hiçbir üretim
> dosyası** değişmedi.

### Sözleşme

`medya/video_lisans.video_provenance_karari(kayit, saglayici, *, teknik,
indirme_zamani)` → `{video_kabul, red_nedeni, eksik_kanit, uyarilar, kanit,
platform, ...lisans_karari alanları}`

**Sekiz zorunlu kanıt** — biri bile eksikse **RED**, eksik alan **adıyla**
raporlanır:

| # | Kanıt | Neden |
|---|---|---|
| 1 | `kaynak_url` | insan tarafından açılabilir kaynak sayfası |
| 2 | `saglayici` | hangi sağlayıcıdan alındı |
| 3 | `lisans_turu` | normalize edilmiş lisans anahtarı (`unknown` kabul edilmez) |
| 4 | `lisans_kaydi` | **sağlayıcının kaydı** — beyan değil |
| 5 | `indirme_zamani` | lisansın o an geçerli olduğunun kaydı |
| 6 | `codec` | ffprobe ile **ölçülen** |
| 7 | `cozunurluk` | özgün genişlik×yükseklik, **ölçülen** |
| 8 | `bitrate` | **ölçülen** (0/negatif geçersiz) |

### ⚠ YouTube ve benzeri platformlar

`youtube.com`, `youtu.be`, `vimeo`, `dailymotion`, `tiktok`, `instagram`,
`facebook`, `x.com`, `twitter`, `reddit`, `pinterest` → **izin kanıtı
zorunlu**. Bu platformlarda:

- **Video açıklamasındaki lisans beyanı TEK BAŞINA YETMEZ.** Rapor bunu
  `beyan_tek_basina_yeterli: False` diye açıkça yazar. Yükleyen kişi eseri
  lisanslama hakkına sahip olmayabilir.
- Kabul için ayrıca **üçü de** gerekir: `indirme_izni`, `tos_uyumu`,
  `hak_sahibi_dogrulandi`. Eksikse **RED** + `PLATFORM-IZIN-KANITI-YOK`.
- ⚠ İzinler açık olsa **bile**, `lisans_kaydi` olarak videonun **kendi
  sayfası** gösterilmişse bu bir **beyandır**, bağımsız kayıt değildir → **RED**.

Böylece ToS ihlali ve telif ihlali yolu kapalı; `EMİN DEĞİLSEN ALMA` gereği
**varsayılan karar REDDİR**.

### Mevcut kapılar gevşetilmedi

`lisans_karari()` **sarmalanıyor, kopyalanmıyor** (tek lisans gerçeği).
Testle doğrulandı: ARR / CC-BY-NC / CC-BY-ND / Getty reddi video kapısında
**asla çevrilmiyor**; atıf gerektiren lisansta eser sahibi yoksa yine RED.
Görsel yolu için **yeni şart eklenmedi** — PD beyanı (`No known copyright
restrictions`) hâlâ geçiyor, görsel kararı video kanıtlarını **sormuyor**.

Tanınmayan sağlayıcı kanıtları tamsa kabul edilir ama **sessiz geçmez**:
`SAGLAYICI-TANINMIYOR` uyarısıyla elle doğrulamaya işaret edilir.

### Red-first

⚠ "Her şeye hayır diyen" bir kapı bütün red testlerini totolojik olarak
geçerdi. Bu yüzden **önce kabul tabanı** kuruldu: kanıtların hepsi olan temiz
bir Commons videosu **KABUL EDİLİYOR**. Ardından **8 zorunlu kanıt tek tek
düşürülüp** her birinde red ve doğru eksik alan adı doğrulandı; 4 platform
tanıma, 4 lisans reddi ve 2 görsel-yolu değişmezlik kontrolü eklendi.

### Sınırlar (bilerek)

⚠ Modül **edinim hattına bağlanmadı** (`edinim.py` / `indirme.py` / `avci.py`
onu import etmiyor — testle doğrulandı), çünkü bağlamak seçim davranışını
değiştirirdi. **Ağa çıkmıyor** (`requests`/`urlopen`/`httpx`/`socket` yok).
Bağlama + gerçek indirme **J-5**'in işi.

### Render değişmezliği (kanıt)

HEAD `974784b` worktree, aynı fixture: `render_plan` `c488eb157312a380`,
`edit_manifest` `34ed2b459b410903`, `props` `db1ff69176149dfa` — **üçü de
birebir aynı**, QA WARN 0/3 aynı → **pilot üretilmedi**.

---

## 79. FAZ J-3 — B-ROLL/CUTAWAY ÇEŞİTLİLİĞİ ÖLÇÜLDÜ (kapı YOK, hedef YOK, 14 Ağu)

> **Durum: çeşitlilik artık ölçülüyor — sağlayıcı, benzersiz varlık, çekim
> türü, zaman içi tekrar ve provenance. **Hiçbir kapı/eşik/hedef eklenmedi**,
> üretim **seçim davranışı değişmedi**, render **değişmedi** (SHA ile
> kanıtlandı) → **pilot üretilmedi**. A–I yeşil (**3648**, 0 hata, 2 bilinen
> BLOKE). Ağ YOK, ücretli API YOK, deploy YOK, $0.00.**
> Değişen: `webapp/editor/kalite_kapisi.py` (+ ölçüm fonksiyonu),
> `webapp/editor/qa_on.py`, `webapp/edit_kopru.py` (rapor alanı),
> `webapp/testler/test_faz_i.py` (§40k, 30 kontrol).

### Ölçülen taban — 7 bağımsız plan

| Metrik | Dağılım | Bulgu |
|---|---|---|
| `benzersiz_varlik_orani` | 6 planda **1.000**, `_smoke_editorv2` **0.750** | tekrar yalnız bir planda |
| `tekrar_sure_orani` | 6 planda **0.000**, `_smoke_editorv2` **0.126** | aynı bulgu, süre cinsinden |
| `cekim_turu_cesidi` | **7 planın 7'sinde de 3** | ⚠ cutaway çeşidi **dar**, hiçbiri 3'ü geçmiyor |
| `tek_saglayici_sure_orani` | 6 planda **1.000**, `_i20` **0.949** | ⚠ süre neredeyse tek sağlayıcıda |
| `gercek_video_sure_orani` | **0.0** (7/7) | J-1/J-2a ile aynı, bağımsız yoldan |
| `provenance` belirsiz | **0** (7/7) | bu korpusta lisans hep dolu |

5 planda **tek sağlayıcı süresi %100** (wikimedia ya da nasa). Çekim türü
sözlüğü fiilen `{close-detail, medium, establishing}` üçlüsüne kilitli;
`_smoke_editorv2` yalnızca farklı bir üçlü kullanıyor
(`atmospheric/medium/data`), daha **zengin** değil.

⚠ **Süre tabanlı ölçüm yeni bilgi veriyor**: `_i20`'de mevcut çekim tabanlı
kapı %80 derken süre tabanlı oran **%94.9**. Aynı şey değiller — bu yüzden
mevcut `SAGLAYICI-TEKEL` kapısı **çoğaltılmadı**, yanına süre tabanlı **rapor**
kondu.

### Sözleşme

`kalite_kapisi.broll_cesitliligi_ozeti(sahneler, *, medya_turu_ozeti_=None)`
→ `olcumler["broll_cesitliligi"]` (ayrıca köprünün `qa` özetinde).

Alanlar: `kaynak_saglayici_dagilimi` (çekim **ve** süre + süre oranı),
`benzersiz_varlik_orani`, `benzersiz_varlik_sayisi`, `kimliksiz_cekim`,
`tekrar_sure_orani`, `tekrar_eden_varlik` (**isimlendirilmiş**),
`cekim_turu_dagilimi`, `cekim_turu_cesidi`, `cekim_turu_belirsiz`,
`provenance`, `gercek_video_cekim` / `gercek_video_sure_orani`.

**EMİN DEĞİLSEN ENGELLEME** üç yerde uygulanıyor:
- varlık kimliği eksikse `benzersiz_varlik_orani` **`None`** (1.0 değil);
- lisans boş/`unknown` ise provenance **`olculdu: False`**, `uyari_adayi: True`
  (lisanslı **sayılmaz**);
- J-2a ölçümü verilmezse `gercek_video_sure_orani` **`None`** — "video yok"
  **iddia edilmez**. Ölçüldüyse **açıkça `0.0`** yazılır.

⚠ Gerçek video oranı J-2a'dan **okunur**, yeniden hesaplanmaz — `ffprobe`
iki kez koşmaz.

⚠ `hedef: None`, `enforce: False`, **yeni fail kodu yok**, dönen sözlükte
`fail/warn/seviye/ihlal` anahtarı bile yok. "Kaç çeşit çekim türü olmalı"
sorusunun cevabı bu korpustan **türetilemez** (tüm planlar aynı dar bantta,
pozitif örnek yok) — I-34/I-58 dersi.

⚠ **Provenance için WARN ÜRETİLMEDİ.** Belirsizlik `uyari_adayi` +
`kod_adayi: BROLL-PROVENANCE-BELIRSIZ` olarak **görünür** kılındı; gerçek WARN
üretmek `durum`u değiştireceği için sonraki atoma bırakıldı.

### Red-first — metrikler totolojik değil

**Doğal karşı-örnek**: `_smoke_editorv2` (I-58'in "düzen B"si) metriklerle
diğer 6 plandan **ayrışıyor** — benzersiz oran < 1.0 **ve** tekrar > 0, diğer
altısında tam tersi.

**Sentetik karşı-örnekler** (her alan tersine dönüyor):

| Müdahale | Beklenen | Ölçülen |
|---|---|---|
| Varlığı tekrarla | benzersiz ↓, tekrar ↑ | ✅ |
| İkinci sağlayıcı ekle | süre tabanlı tekel ↓ | ✅ |
| Yeni çekim türü ekle | çeşit sayısı ↑ | ✅ |
| `asset_id` boşalt | oran `None` olmalı | ✅ (1.0 **değil**) |
| Lisansı `unknown` yap | provenance ölçülemedi | ✅ |

⚠ Test bloğunda **sabit indeks kullanılmadı**: karşı-örnek planı, ölçülen
özelliğinden seçiliyor (tekrarsız + en çok medya çekimi olan plan).

### Render değişmezliği (kanıt)

HEAD `686d1e0`'dan ayrı git worktree, aynı fixture:

| | HEAD | Çalışma ağacı |
|---|---|---|
| `render_plan` SHA | `c488eb157312a380` | **aynı** |
| `edit_manifest` SHA | `34ed2b459b410903` | **aynı** |
| `props` SHA | `db1ff69176149dfa` | **aynı** |
| QA durum/fail/warn | WARN 0/3 | **aynı** |
| `qa.broll_cesitliligi` | YOK | **VAR** |

→ **pilot üretilmedi.**

### Korunanlar

I-23/I-24/I-25/I-38, tüm eşikler, lisans-provenance kapıları, 22 alan
sözleşmesi, modüler okuyucu arayüzü, kullanıcı seçimleri, `deploy.sh`,
üretim seçim kodu (`siralama.py`, `medya_tekrari`) — testle doğrulanarak
**dokunulmadı**.

---

## 78. FAZ J-2a — MEDYA TÜRÜ RAPOR SÖZLEŞMESİ (kapı YOK, eşik ENFORCE YOK, 14 Ağu)

> **Durum: J-1'in ölçtüğü taban artık **uygulamanın kendi raporunda**.
> `olcumler["medya_turu"]` → `video_sure_orani` + `donmus_kadraj_sure_orani`.
> **Hiçbir kapı eklenmedi, hiçbir eşik ENFORCE edilmedi.** Render davranışı
> **değişmedi** (SHA ile kanıtlandı) → **pilot üretilmedi**. A–I yeşil
> (**3618**, 0 hata, 2 bilinen BLOKE). Ağ YOK, ücretli API YOK, deploy YOK,
> $0.00.**
> Değişen: `webapp/editor/kalite_kapisi.py` (+ ölçüm fonksiyonu),
> `webapp/editor/qa_on.py`, `webapp/editor/plan.py`, `webapp/edit_kopru.py`
> (üçü de **yalnız parametre geçişi**), `webapp/testler/test_faz_i.py`
> (§40j, 25 kontrol).

### Sözleşme

`kalite_kapisi.medya_turu_ozeti(sahneler, *, kare_okuyucu=None, motion_specler=None)`

Mevcut okuyucu deseniyle **birebir aynı**: modül **dosya açmaz**, ölçer
dışarıdan verilir (`benzerlik_okuyucu` / `enerji_okuyucu` gibi). Okuyucu
yoksa `olculdu: False`, `neden: "KARE-OKUYUCU-YOK"` ve oranlar **`None`** —
**0.0 değil**, çünkü 0.0 "video yok" **iddiasıdır**. `EMİN DEĞİLSEN
ENGELLEME`. Zincir: `edit_kopru.plan_kur` → `editor.plan` → `qa_on.denetle`.

Rapor alanları: `video_sure_orani`, `donmus_kadraj_sure_orani`,
`statik_sure_orani`, `olculemedi_sure_orani`, sınıf bazında çekim/süre ve
`kalemler`. Tam ölçüm `editor_qa.json`'a, özet köprünün `qa` sözlüğüne yazılır.

### ⚠ SEVİYE HATASI ÖLÇÜLDÜ VE AYRIŞTIRILDI

J-1'in **0.155**'i bir **korpus agregasıdır** (18.4 / 118.5). **Plan başına
uygulanırsa 7 planın 4'ünde YANLIŞ POZİTİF verir** — ölçüldü:

| Plan | donmuş oranı | 0.155 agrega | 0.334 plan |
|---|---|---|---|
| `_ses_10sn` | 0.333 | ⛔ ihlal | ✅ temiz |
| `_i15` | 0.318 | ⛔ ihlal | ✅ temiz |
| `_i16` | 0.297 | ⛔ ihlal | ✅ temiz |
| `_smoke_editorv2` | 0.295 | ⛔ ihlal | ✅ temiz |
| `_i18` / `_i20` / lawn | 0.000 | ✅ | ✅ |
| **Yanlış pozitif** | | **4/7** | **0/7** |

Bu yüzden **iki ayrı referans** tutuluyor ve **hangi seviyede geçerli olduğu
alanın adında yazıyor**:

```
DONMUS_KADRAJ_AGREGA_REFERANSI = 0.155   # KORPUS seviyesi
DONMUS_KADRAJ_PLAN_REFERANSI   = 0.334   # PLAN seviyesi
    formül: ceil(maks_gözlenen_plan_oranı, 3 hane) = ceil(0.3333, 3)
```

Plan referansı bir **kalite hedefi değil, regresyon kilidi**: "bugünkünden
kötüye gitme". Mevcut korpusta yanlış pozitif **tanım gereği 0**. İkisi de
`enforce: False` ile işaretli; **hiçbir yerde uygulanmıyor**.

⚠ `VIDEO_SURE_ORANI_HEDEFI = None` — **uydurulmadı**. Korpusta tek bir
pozitif örnek yok; veriden eşik türetilemez (I-34/I-58 dersi).

### Red-first doğrulaması

| İddia | Tersi olsaydı |
|---|---|
| Okuyucu yoksa oranlar `None` | `0.0` dönseydi sessizce "video yok" denirdi → KIRMIZI |
| Gerçek video konunca `video_sure_orani > 0` | ölçüm totolojik olsaydı 0 kalırdı → KIRMIZI |
| `0.155` plan başına 4 yanlış pozitif | seviye hatası tekrarlanırsa yakalanır |
| `denetle` fail/warn sayısı değişmiyor | referans enforce edilseydi değişirdi |

### Render değişmezliği (kanıt)

HEAD `7d3200f`'ten ayrı bir **git worktree** kurulup aynı fixture iki kodda
koşuldu:

| | HEAD (öncesi) | Çalışma ağacı (sonrası) |
|---|---|---|
| `render_plan` SHA | `c488eb157312a380` | **`c488eb157312a380`** |
| `edit_manifest` SHA | `34ed2b459b410903` | **`34ed2b459b410903`** |
| `props` SHA | `db1ff69176149dfa` | **`db1ff69176149dfa`** |
| QA durum/fail/warn | WARN 0/3 | **WARN 0/3** |
| `qa.medya_turu` | YOK | **VAR** |

Render çıktısı **bit düzeyinde aynı** → talimat gereği **pilot üretilmedi**.

### ⚠ Yol boyunca bulunan gerçek kusur

`qa_on.denetle()` imzasında **`kalite_kapisi` adında bool bir parametre var**
ve modül adını **gölgeliyor**; `kk` takma adı da ayrı bir fonksiyonda
bağlanıyor. İlk bağlama denemesi bu yüzden `AttributeError: 'bool' object has
no attribute ...` verdi. Modül düzeyinde gölgelenmeyen `_KK` takma adı
eklendi. ⚠ Bu tuzak **aynı fonksiyona ileride eklenecek her modül çağrısı
için geçerlidir**.

### Korunanlar

I-23/I-24/I-25/I-38 kapıları, tüm eşikler (optik 2.0 / benzerlik 0.86 /
enerji 11.589 / kenar_dış 6.234 / k 0.935), lisans-provenance kapıları,
22 alan sözleşmesi, kullanıcı seçimleri (`Video.tsx` zoom/pan), `deploy.sh`
— hepsi testle doğrulanarak **dokunulmadı**.

---

## 77. FAZ J-1 — STATİK FOTOĞRAF / GERÇEK VİDEO ORANI ÖLÇÜLDÜ (yalnız tanısal, 14 Ağu)

> **Durum: kullanıcı önceliğinin 1. atomu. "Slayt gösterisi hissi" artık bir
> izlenim değil, **ölçülmüş taban**: kayıtlı 7 benzersiz planın **hiçbirinde**
> gerçek hareketli video yok (**%0.0**), sürenin **%94.7'si statik fotoğraf**.
> Üretim davranışı **DEĞİŞMEDİ**, kapı/eşik **EKLENMEDİ**. A–I yeşil
> (**3593**, 0 hata, 2 bilinen BLOKE). Ağ YOK, ücretli API YOK, rerender/
> deploy YOK, $0.00.**
> Değişen: **yalnızca** `webapp/testler/test_faz_i.py` (§40i, 12 kontrol) ve
> bu handoff.

### Ölçülen taban — 7 benzersiz plan · 32 çekim · 118.5 sn

| Sınıf | Çekim | % | Süre | % |
|---|---|---|---|---|
| **(a) gerçek hareketli video** | **0/32** | **0.0** | **0.0 sn** | **0.0** |
| (b) statik foto + Ken Burns/zoom/pan | 26/32 | 81.2 | 93.9 sn | 79.2 |
| (b0) statik foto, **hiç hareket yok** (donmuş kadraj) | 4/32 | 12.5 | 18.4 sn | **15.5** |
| (c) sentetik / motion-graphic (fallback) | 2/32 | 6.2 | 6.3 sn | 5.3 |
| **ölçülemedi** | 0/32 | 0.0 | 0.0 sn | 0.0 |
| **STATİK FOTOĞRAF TOPLAMI (b+b0)** | **30/32** | **93.8** | **112.3 sn** | **94.7** |

### Yöntem — ağsız, alan bilgisine güvenmeyen

17 kayıtlı koşum plan imzasıyla (`fact_id, asset_id, süre` üçlüleri)
gruplandı → **7 benzersiz plan**; lawn planının **10 yeniden render'ı tek
örnek** sayıldı (I-34/I-58 dersi). Sınıf kararı `medya_turu` **alanına
değil**, dosyanın **kendisine** dayanıyor: her kaynak `ffprobe -count_frames`
ile okundu. Kaynak türü belirsizse (`medya_yolu` boş / dosya yok / ffprobe
okumadı) **varsayılmadı**, ayrı `ölçülemedi` kalemi yazıldı — bu korpusta 0.

⚠ **I-58 dersi uygulandı**: bu blokta **sabit ölçüm sözlüğü yoktur**. Bütün
oranlar her koşumda kayıtlardan **yeniden hesaplanır**; sayı teste yazılmaz.

### Yanlış sınıflama payı (gerçek temiz karşı-örnekler)

| Sınıf | Örnek | Sonuç |
|---|---|---|
| Pozitif (gerçek hareketli video) | 4 gerçek MP4 (`outputs/sample/`, 288–756 kare) | **4/4 `a_video`** — kaçırma 0 |
| Negatif (statik kaynak) | 20 benzersiz kaynak dosyası | **20/20 tek kare** — yanlış pozitif 0 |

**Toplam 24/24 doğru.** ⚠ **Dürüst sınır**: pozitif örnekler korpusun kendi
kaynakları değil, **render çıktılarıdır** — korpusa hiç video kaynağı
girmediği için, indirilmiş bir stok video üzerinde uçtan uca davranış
**ölçülmemiştir**.

**Red-first doğrulaması**: sahte bir korpusa tek gerçek MP4 enjekte edilince
`a_video == 0` iddiası **KIRMIZI** yanıyor; kayıp dosya `ölçülemedi`,
fallback `c_sentetik` veriyor → test **totolojik değil**.

### Kök neden: kısıt kod değil

`medya/avci.py` ve `medya_kopru.py` varsayılanı **zaten `"video"`**; üretim
video türünü destekliyor. Yani %0 sonucu bir **kod kısıtı değil**, arama/arz
ve seçim zincirinin sonucu. Ayrıca `editor/plan.py:462` aday yokken türü
**sessizce `"image"`** yazıyor — ayrı ve dar bir atom adayı.

### J-2 için eşik türetme önerisi (⚠ ÜRETİME ALINMADI)

⚠ Bugün "video oranı ≥ E" kapısı **veriden türetilemez**: korpusta **tek bir
pozitif örnek yok**. E'yi şimdi yazmak I-34/I-58'de elenen hatanın aynısı
olur. Bu yüzden iki aşama önerilir:

**J-2a — regresyon kilidi (bugün türetilebilir).** Ölçülen tabandan, açık
formülle, gevşetmeden:

```
donmus_kadraj_sure_orani  ≤  ölçülen_taban  =  18.4 / 118.5  =  0.155
```

Yeni hedef koymaz, yalnız **kötüleşmeyi** yakalar; yanlış pozitif payı bugün
ölçülebilir (7 planın 7'si geçer). Önce yalnız **rapor alanı** olarak
(`video_sure_orani`, `donmus_kadraj_sure_orani`) eklenir, kapı sonra.

**J-2b — hedef kapı (veri gelince).** `video_sure_orani ≥ E`, ancak **en az
K=5 bağımsız planda** gerçek video kaynağı alındıktan sonra ve I-55 kalıbıyla
(yalnız TRAIN'den açık formül, held-out'a tek bakış). **K < 5 iken eşik
KONULMAZ**, yalnız WARN raporlanır — `EMİN DEĞİLSEN ENGELLEME`.

---

## 76. FAZ I-58 — İKİ ADAY DÜZENİ KARŞI-OLGU OLARAK ÖLÇÜLDÜ (yalnız tanısal, 14 Ağu)

> **Durum: I-57'nin bıraktığı 1. açık atom ("ikinci beat için ayrı sorgu mu,
> aynı adayın farklı kadrajı mı?") ağsız/ücretsiz karşı-olgu ile ölçüldü ve
> öneri (düzen B) **ELENDİ**. Üretim davranışı **DEĞİŞMEDİ**. A–I yeşil
> (**3581**, 0 hata, 2 BLOKE — faz-h `QA_TEST_VIDEO` opsiyonel + faz-i I-33
> görsel inceleme). Rerender YOK, deploy YOK, kabul edilmiş MP4 YOK. $0.00.**
> Değişen: **yalnızca** `webapp/testler/test_faz_i.py` (§40h, 16 kontrol) ve
> bu handoff. `medya/*`, `medya_kapisi.py`, `editor/*`, `Video.tsx`,
> `deploy.sh`, **eşikler**, **22 alan sözleşmesi** ve I-23/I-24/I-25/I-38
> kapıları **dokunulmadı**. I-23…I-57 **korundu**.

### Karşılaştırılan iki düzen

| | b002'ye atanan | Sonuç |
|---|---|---|
| **A (mevcut)** | farklı 2. aday `s01y1_9559294` | tekrar kapısından **TEMİZ** |
| **B (öneri)** | `s01_5156581`'in farklı kadrajı | **I-22 kapısını İHLAL EDİYOR** |

### Ölçülenler (hepsi canlı hesaplanıyor)

1. **Tekrar kapısı** — üretimin kendi `_i37_calisma/edit_manifest.json`'u
   `kalite_kapisi.medya_tekrari()`'ye verildi: A'da `bitisik_ayni_asset=[]`;
   B'de indeks 1'de bitişik aynı varlık + 2 kez tekrar →
   **`KALITE-MEDYA-TEKRAR`** fail kodu tetiklenir.
2. **Bloke eden bacak** — kaynak koddan gösterildi: `medya_tekrari` görsel
   benzerliği **aynı `asset_id` çiftinde hiç ölçmez** (`continue`), üretim
   yolu da okuyucuyu zaten vermiyor (`qa_on: benzerlik_okuyucu=None`).
   Yani B'yi bloke eden **benzerlik değil, yalnız `asset_id`**.
3. **BELİRLEYİCİ — B semantik kusuru gidermiyor**: b002 o düzende b001'in
   varlığını alır; o varlık **1900 tarihli arşiv fotoğrafıdır**
   (`kunye.json` başlığı ile doğrulandı) ve `medya_kapisi.donem_uyarisi()`
   **b002 için de yanar**. B, kusuru çözmüyor; **başka bir kusurla
   değiştiriyor**.
4. **Genellenebilirlik payı (dürüst sınır)** — 17 kayıtlı koşumun 12'sinde
   çok-beatli sahne var, ama **10'u aynı lawn planının yeniden render'ı**
   (tek bağımsız iş). Lawn ailesi dışında yalnız **iki** bağımsız iş:
   `_i20` (düzen A; rank-1 varlığı I-33'ün vitrin kusuru — yine semantik) ve
   `_smoke_editorv2` (**düzen B'nin doğal örneği**; ölçüldü ki bitişik aynı
   varlık **tetikleniyor** — o koşumda kalite kapısı kapalı olduğu için
   sorun üretilmemişti). Örnek büyüklüğü **2** → yanlış pozitif payı
   **güvenilir ölçülemez** (I-34 dersi).

### ⚠ Kapanış denetiminde ELENDİ ve SİLİNDİ (3 iddia)

Taslakta "ölçüldü" diye yazılmış üç iddia, kapanış denetiminde
**yeniden türetilemedi** — üçü de sabit sözlükten okunup eşikle
karşılaştırılıyordu (totoloji) ve dayanağı repoda yok:

| Silinen iddia | Neden elendi |
|---|---|
| Kadraj varyantı dHash'leri **0.59–0.77 < 0.86** | Repoda **dHash uygulaması yok** (ölçer her zaman dışarıdan verilir), `cikti/_i58*` ölçüm dizini yok, betik yok |
| Beş varyantın beklenen optiği **2.83–3.48 > 2.0** | `beklenen_optik_olcusu()` ile **yeniden hesaplanmıyordu**; türetildiği E/d girdileri hiçbir yerde kayıtlı değil |
| "Lisans/provenance bozulmuyor" | Testi iddiayla ilgisiz bir şeye bakıyordu (`KALITE-KUNYE-EKSIK` fail kodunun **varlığı**) |

⚠ Bunların silinmesi **hükmü değiştirmez**: B zaten (1) tekrar kapısını
ihlal ettiği ve (3) semantik kusuru gidermediği için elenmiştir. ⚠ "B'nin
hareketi yetersiz" **denmemektedir** — ölçülmemiştir.

### Hüküm

**Düzen B üretime ALINMADI.** I-57'nin 1. açık atomu **kapandı** (öneri
elendi); 2. ve 3. atomlar (semantik skorun atıl hâli, alaka kapısının
kapsam raporu) **açık kalıyor**.

---

## 75. FAZ I-57 — b001/b002 SEÇİM ZİNCİRİ GERİYE İZLENDİ (yalnız tanısal, 14 Ağu)

> **Durum: iki yanlış adayın NEDEN seçildiği üretimin KENDİ kayıtlarından
> ölçüldü. Kök neden semantik değil **YAPISAL** çıktı; ayrıca iki üretim
> sinyalinin (semantik skor + alaka kapısı) bu korpusta **atıl/ters**
> olduğu ölçüldü. Üretim davranışı **DEĞİŞMEDİ**. A–I yeşil (3565, 0 hata,
> 1 BLOKE — I-33). Rerender YOK, deploy YOK, kabul edilmiş MP4 YOK. $0.00.**
> Değişen: **yalnızca** `webapp/testler/test_faz_i.py` (+175 satır) ve
> handoff. `medya/*`, `medya_kapisi.py`, `editor/*`, `Video.tsx`,
> `deploy.sh`, **eşikler**, **22 alan sözleşmesi** ve I-23/I-24/I-25/I-38
> kapıları **dokunulmadı**. I-23…I-56 **korundu**.

### ⚠ Önce bir düzeltme (ölçüldü)

Devir notunda *"b002 yağmurlama görselleri"* deniyordu; **b002'nin varlığı
yağmurlama değildir**: `Starr-101229-6113-**Heteropogon contortus** …
**Kanapou-Kahoolawe**` (kızıl toprak erozyon sahası). Yağmurlama **b004/s03**
adayıdır ve o eşleşme **doğrudur**.

### Zincir — üretimin kendi kayıtlarından

`edit_manifest.json` + `render_plan.json`:

| beat | beat metni | asset | gerekçe |
|---|---|---|---|
| **b001** | *"There is a bag of grass"* | `s01_5156581` | **puan 90** (1. aday) |
| **b002** | *"seed on my garage shelf right now."* | `s01y1_9559294` | **puan 80** (2. aday) |

- s001 cümlesi **ikiye kesilmiş**; iki beat de **aynı sahne (s001)** ve
  **aynı olguya (s01)** bağlı.
- **b002 kendi beat metniyle hiç aranmadı/puanlanmadı**: sahnenin aynı
  sorgusundan gelen **ikinci aday**, ayırt edilebilirlik kuralı (I-21/I-22)
  gereği ikinci beat'e atandı.
- b002'nin metni (*"seed on my garage shelf right now."*) **tek başına
  aranabilir bir iddia bile değil**.

### Ölçüm 1 — semantik skor YAPISAL OLARAK ATIL

`siralama.semantik_puan`, varlık listesi boşken her bacağı nötr değerine
düşürüyor: **17 (yer) + 7 (kişi) + 6 (kurum) + 7 (tarih) + 13 (konu) = 50.0**.
Altı adayın **altısı da tam 50.0** aldı → skor **sıfır bilgi** taşıyor.
Doğru aday (yağmurlama) ile yanlış aday **aynı puanı** alıyor.

### Ölçüm 2 — alaka kapısı bu korpusta TERS çalışıyor

| beat | sınıf | `alaka_kapisi` | global örtüşme (tüm anlatım) |
|---|---|---|---|
| b001 | NEG | **True** | 2 — `['and','grass']` |
| b002 | NEG | **True** | 2 — `['bag','seed']` |
| b003 | POZ | True | 3 — `['lawn','patchy','the']` |
| **b004** | **POZ** | **False** ⛔ | **0** |
| b005 | NEG | **True** | 1 — `['seedling']` |
| **b006** | **POZ** | **False** ⛔ | **0** |

Kapı **üç yanlış adayın üçünü de geçiriyor**, **üç doğru adaydan ikisini
reddediyor**. Global (tüm anlatım) örtüşmesi de aynı yönde ters.

⚠ Kapı **bozuk değil**: Faz E'de archive.org çöpünü (*MAJESTIC 12 Files*)
elemek için ölçülerek kondu ve **orada çalışıyor**. Bu korpusta atıl/ters,
çünkü **doğru görselin künyesi anlatımın kelimelerini tekrarlamıyor**.
(I-48'de ölçülen "kelime örtüşmesi ters" bulgusu, artık **üretim kapısının
kendisinde** gösterildi.)

### Ölçüm 3 — b002'yi ayıran tek sinyal YAPISAL

İçerik tabanlı sinyaller ayırmıyor (yukarıdaki tablo; ayrıca I-48 biyom/yer
ve I-49 tür/takson **elendi**). Ayıran tek sinyal:

> **S1 = "aynı sahnenin ikinci (rank ≥ 2) adayı"** → yalnız **b002**
> işaretleniyor; b001/b003/b004/b005/b006 temiz.

⚠ **Yanlış pozitif payı ÖLÇÜLEMEZ**: bu korpusta rank ≥ 2 olan **tek** aday
b002'dir (**örnek büyüklüğü 1**). I-34'ün dersi gereği bu **genellenebilir
bir sonuç değildir** ve **üretime konmadı**.

| Paket | A | B | C | D | E | F | G | H | I | Toplam |
|---|---|---|---|---|---|---|---|---|---|---|
| Zengin venv | 125 | 200 | 148 | 95 | 127 | 244 | 218 | 257 | **2151** | **3565** |

0 hata. Faz I 2130 → **2151** (+21). **1 BLOKE** — I-33 kaydı sürüyor.

### ⛔ Kabul durumu değişmedi

Pilot MP4 **kabul edilmiş değildir**; b001/b002 semantik uyumsuzluğu sürüyor.
I-47 yalnız b001'i otomatik işaretliyor.

### SONRAKİ ATOM — ölçüm ne diyor

Bu atom kök nedeni **semantik zekâdan yapısal tasarıma** kaydırdı. Ölçülen
üç ayrı, dar ve **ağsız** aday:

1. **Beat bölme ↔ sorgu bağı**: bir cümle iki beat'e bölündüğünde ikinci
   beat, **kendi metniyle hiç aranmayan** bir adayı alıyor. Ölçülebilir
   atom: ikinci beat için **ayrı sorgu** mu, yoksa **aynı adayın farklı
   kadrajı** mı? (İkincisi ağ/kota **artırmaz**.)
2. **Semantik skorun atıl hâli**: varlık çıkmayınca 50.0 sabit. Ölçülebilir
   atom: varlık çıkmadığında skorun **"ölçülemedi"** diye raporlanması
   (şu an sessizce nötr puan veriyor — `EMIN DEGILSEN ENGELLEME` ihlali).
3. **Alaka kapısının kapsamı**: hangi korpusta çalışıp hangisinde ters
   çalıştığı ölçülebilir; kapının **kendi kapsamını raporlaması** dar bir
   atom olur.

⚠ Diğer açık borçlar: önizlemede altyazı çizilmemesi (I-40), model
d > 1.31 ölçülmemiş (I-51), kenar hattının PRE-QA karşılığı yok (I-56).

---

## 74. FAZ I-56 — BAĞIMSIZ KENAR ÖLÇÜM HATTI ÜRETİME ALINDI (14 Ağu)

> **Durum: I-52'den beri süren zincir KAPANDI. I-54'ün ölçtüğü yapılandırma
> ve I-55'in türettiği eşik **uygulandı**; kabul ölçütü sağlandı:
> I-52 karşı-örneği **FAIL**, **17 temiz videonun 17'si PASS** →
> **kaçırma 0, yanlış pozitif 0**. A–I yeşil (3544, 0 hata, 1 BLOKE — I-33).
> 25.2 sn 1080p pilot **POST-QA PASS**, **11/11 kare SHA-256 aynı**.
> MP4 **kabul edilmedi** (semantik). Deploy YOK. Maliyet $0.00.**
> Değişen: `webapp/editor/kalite_kapisi.py` (2 saf fonksiyon + 3 ölçülen
> sabit), `webapp/editor/qa_son.py` (1 opsiyonel parametre + 1 kod),
> `webapp/testler/test_faz_i.py`. `Video.tsx`, `qa_on.py`, `medya/*`,
> `deploy.sh`, **mevcut eşikler** ve **22 alan sözleşmesi** **dokunulmadı**.
> I-23…I-55 **korundu**.

### ⚠ Mevcut sözleşmeye dokunulmadı

- `OPTIK_ORNEK_FPS` = **4** ve `OPTIK_ORNEK_OLCU` = **(64,36)** aynen
  (I-17 durağanlık eşikleri bu örneklemeyle anlamlı).
- `kenar_siyahligi_olcusu` ve `KENAR_SIYAH_ESIGI` (**16**) aynen duruyor.
- POST-QA'nın mevcut `kalite.kenar` ölçümü ve `POST-KENAR-SIYAH` kodu
  **korundu**; yeni ölçüm **ayrı alanda** (`kalite.kenar_dis`) ve **ayrı
  kodda** (`POST-KENAR-DIS`). Yeni örnek verilmezse davranış **bit-bit**
  eskisi gibidir.

### Uygulanan hat (her sayı önceki atomların ÖLÇÜMÜNDEN)

| parça | değer | kaynak |
|---|---|---|
| örnekleyici | `kenar_ornek_komutu` — **384×216 @ 8 fps** | I-54 |
| yön | **dört yön** (sol/sağ/üst/alt) | I-54 |
| agregasyon | **en dış sütun/satır** | I-54 |
| eşik | **6.234** (= train temiz tabanı 12.468 / 2) | I-55 |
| koyu görüntü koruması | kare geneli > eşik × 2 | `kenar_siyahligi_olcusu` ile aynı sözleşme |

### Kabul ölçütü — ölçüldü

| küme | sonuç |
|---|---|
| **I-52 karşı-örneği** (gerçek bant) | **FAIL** — 2/159 kare, en koyu sol **0.0**, sağ **0.08** ✅ |
| **17 gerçek temiz video** | **17/17 PASS** (i15…i56, önizleme dâhil; en düşük taban 10.01) ✅ |
| **kaçırma / yanlış pozitif** | **0 / 0** ✅ |

Dört yönün her biri için sentetik 9 px bant testi de yeşil — I-53'te
**tamamen kör** olan dikey yön artık yakalanıyor.

| Paket | A | B | C | D | E | F | G | H | I | Toplam |
|---|---|---|---|---|---|---|---|---|---|---|
| Zengin venv | 125 | 200 | 148 | 95 | 127 | 244 | 218 | 257 | **2130** | **3544** |

0 hata. Faz I 2100 → **2130** (+30). Red-first: 6 XX.
⚠ I-53/I-54/I-55'in "henüz uygulanmadı" kilitleyen 5 kontrolü **devralındı**;
her atomun **kendi ölçümü** aynen kilitli kaldı.

### 1080p pilot — `editorv2_lawn_i56.mp4` (25.2 sn)

QA hükmü değiştiği için tam pilot koşuldu. Sadakat: **beat eşit=True,
varlık eşit=True**.

- **1920×1080 @ 30**, aac 48 kHz/2ch, 25.259 sn · **8 kesme** · **11 kare** (6 beat)
- LUFS **−14.27** / TP **−3.10** · sessizlik **%0.0** · kırpma yok
- **eski kenar (I-17)**: 0/101 temiz · **yeni kenar (I-56)**: **0/202 temiz**,
  en koyu sol/sağ/üst/alt = 27.07 / 15.86 / 67.21 / 54.42 (eşik 6.234)
- medya tekrarı **6 benzersiz**, bitişik yok · motion **4 hareket**, tekrar yok
- tipografi dört ölçümde temiz · künye 5 sahnede · optik risk yok
- I-47 dönem uyarısı: **b001** (doğru pozitif, sürüyor)
- PRE-QA **WARN** (fail=0) · **POST-QA: PASS**
- **Render değişmedi**: I-51 ile **11/11 kare SHA-256 birebir aynı**

### ⛔ Kabul durumu

Teknik POST-QA **PASS** ve yeni kenar hattı temiz. Buna rağmen **kabul
edilmiş MP4 değildir**, mutlak yol verilmedi, **deploy yok**: b001/b002
görselleri anlatımla **semantik uyumsuz** (bilinen sınıf; I-47 b001'i
otomatik işaretliyor).

### SONRAKİ ATOM

1. **Semantik kabul engeli** (b002/b005) — dört bağımsız eleme sonrası
   **kullanıcı kararı**: operatör onayı ya da VLM.
2. **Önizlemede altyazı hiç çizilmiyor** (I-40'ta ölçüldü).
3. Model **d > 1.31** hâlâ ölçülmemiş (I-51).
4. ⚠ Yeni kenar hattı şu an **yalnız POST-QA**'da; PRE-QA tarafında karşılığı
   yok (plan üzerinden kenar öngörüsü ayrı bir atom olur).

---

## 73. FAZ I-55 — KENAR EŞİĞİ TÜRETİLDİ (train→formül, held-out TEK BAKIŞ, 14 Ağu)

> **Durum: eşik YALNIZ TRAIN bandından açık formülle türetildi ve
> held-out'a **tek kez** bakıldı: **kaçırma 0, yanlış pozitif 0** → KABUL.
> ⚠ Bu bir **kalibrasyon** atomudur: yapılandırma ve eşik **üretime
> UYGULANMADI**. A–I yeşil (3514, 0 hata, 1 BLOKE — I-33). Rerender YOK.
> Geçici varlıklar (345 MB) temizlendi. Deploy YOK, kabul edilmiş MP4 YOK.
> Maliyet $0.00.**
> Değişen: **yalnızca** `webapp/testler/test_faz_i.py` (+~110 satır) ve
> handoff. `kalite_kapisi.py`, `Video.tsx`, `qa_on.py`, `medya/*`,
> `deploy.sh`, **eşikler**, **22 alan sözleşmesi** **dokunulmadı**.
> I-23…I-54 **korundu**.

### Yöntem — sızıntı yok

1. Bölünme I-54'te **ölçümden önce** sabitlenmişti; buradan
   **değiştirilmeden okundu** (`cikti/_i54_ayrim/i54_bolunme.json`).
2. Eşik **yalnız TRAIN** bandından, **açık formülle** türetildi.
3. Held-out'a **yalnızca bir kez** bakıldı.
4. Pilot geçsin diye ayar **yok**; eşik uydurma **yok**.

Yapılandırma I-54'te ölçülmüştü ve burada **seçilmedi, yalnızca kullanıldı**:
dört yön + `dis1` (en dış sütun/satır) + 384 genişlik + 8 fps.

### ⚠ Ölçüm sırasında bulunan ve düzeltilen kusur (betikte, render'da değil)

İlk koşumda TRAIN'de **örtüşme** göründü (kusur 20.431 > temiz 12.468).
Neden: sahne penceresi `int(bitiş × fps)` ile kesiliyor ve sahnenin **son
karesi** (2.201 sn'lik sahnede t=2.125) dışarıda kalıyordu — **bant tam
orada** oluşuyor. Pencere zaman tabanlı yapıldı; değer **20.431 → 0.046**.
Render **değişmedi**; hata ölçüm betiğindeydi.

### TRAIN — eşik yalnız buradan

| taraf | değerler |
|---|---|
| **kusurlu** | sag-parlak-kisa **0.046** · ust-parlak-kisa 0.0 · sag-koyu-uzun 0.0 |
| **temiz** | **ses10 12.468** · i37 15.889 · smoke20 19.005 · i20 23.594 · i18 25.870 · i16 32.968 · i17 32.968 · i15 33.005 |

Band: kusur **0.046** < temiz **12.468** (örtüşme yok).

### Formül — açık ve en kötü train sınırlarından

```
eşik = temiz_alt / GÜVENLİK_KATI          GÜVENLİK_KATI = 2
eşik = 12.468 / 2 = 6.234
```

**Anlamı**: temiz bir karenin işaretlenmesi için, TRAIN'de ölçülen **en koyu
temiz kenarın yarısı** kadar daha koyulaşması gerekir (**2× pay**).
TRAIN payları: temiz tarafı **×2.00** (formülün kendisi), kusur tarafı
**×135.5**. Eşiğin TRAIN bandının içinde olduğu ayrıca **doğrulandı**
(0.046 < 6.234 < 12.468) — uydurma değil, kontrol.

### HELD-OUT — TEK BAKIŞ

| kusurlu | değer | sonuç |
|---|---|---|
| sol-parlak-uzun | 0.005 | yakalandı |
| ust-koyu-kisa | 0.003 | yakalandı |
| alt-parlak-uzun | 0.0 | yakalandı |
| i52karsi | 0.0 | yakalandı |

| temiz | değer | sonuç |
|---|---|---|
| **onizleme** | **10.009** | temiz |
| i39 | 15.856 | temiz |
| i43 | 22.856 | temiz |
| i52vid | 22.921 | temiz |
| i42 / i41vid | 37.880 | temiz |
| i54temiz | 40.329 | temiz |

**Kaçırma 0 · Yanlış pozitif 0 → KABUL.**
Held payları: temiz tarafı **×1.61**, kusur tarafı **×1247**.

### Duyarlılık — sonuç tek bir sayıya bağlı değil

Held-out'ta FP=FN=0 kalması için `GÜVENLİK_KATI` aralığı yaklaşık
**(1.25, 2494)**; seçilen **2.0** bu aralığın rahat içinde.

⚠ Bu eşik (**6.234**) mevcut `KENAR_SIYAH_ESIGI` (**16**) ile
**karşılaştırılamaz**: farklı örnekleme (384×216 @ 8 fps) ve farklı
agregasyon (en dış sütun/satır) üzerinde tanımlıdır.

| Paket | A | B | C | D | E | F | G | H | I | Toplam |
|---|---|---|---|---|---|---|---|---|---|---|
| Zengin venv | 125 | 200 | 148 | 95 | 127 | 244 | 218 | 257 | **2100** | **3514** |

0 hata. Faz I 2081 → **2100** (+19). **1 BLOKE** — I-33 kaydı sürüyor.

### SONRAKİ ATOM — artık tek parça kaldı

Kenar kapısının **tüm parçaları ölçüldü**: yapılandırma (I-54) ve eşik
(I-55). Geriye **uygulama** kalıyor: bağımsız kenar ölçüm hattı
(`kenar_ornek_komutu` + dört yön + en dış sütun/satır + eşik 6.234), PRE/POST
QA'ya kablolama ve gerçek pilotla doğrulama.
⚠ `OPTIK_ORNEK_FPS` **4'te kalmalı** (I-17 durağanlık eşikleri ona bağlı).
⚠ Uygulama **render davranışını değiştirmez** ama **QA hükmünü** değiştirir;
o atomda ≥20 sn 1080p pilot + tam QA gerekir.

⚠ Diğer açık borçlar: semantik kabul engeli (b002/b005 — **kullanıcı
kararı**), önizlemede altyazı çizilmemesi (I-40), model d > 1.31 ölçülmemiş.

---

## 72. FAZ I-54 — KENAR KAPISI: KORPUS GENİŞLETİLDİ, AYRIM PAYI ÖLÇÜLDÜ (yalnız tanısal, 14 Ağu)

> **Durum: I-53'ün bıraktığı soru ÖLÇÜLDÜ. Ayrım **var** ve **geniş**
> (kusur ≤ 0.02 / temiz ≥ 9.96, örtüşme yok) — ama yalnızca **dört yön +
> en dış sütun + ≥384 genişlik + ≥8 fps** birlikte sağlandığında.
> ⚠ I-53'ün "temiz ≥ 15.0" iddiası **yanlış çıktı** (gerçek taban 10.01).
> **Eşik SEÇİLMEDİ**, üretim kodu **DEĞİŞMEDİ**. A–I yeşil (3495, 0 hata,
> 1 BLOKE — I-33). Rerender YOK. Geçici varlıklar (345 MB) temizlendi.
> Deploy YOK, kabul edilmiş MP4 YOK. Maliyet $0.00.**
> Değişen: **yalnızca** `webapp/testler/test_faz_i.py` (+140 satır) ve
> handoff. `kalite_kapisi.py`, `Video.tsx`, `qa_on.py`, `medya/*`,
> `deploy.sh`, **eşikler**, **22 alan sözleşmesi** **dokunulmadı**.
> I-23…I-53 **korundu**.

### Korpus — hepsi GERÇEK render (sentetik kare yok)

- **Kusurlu**: `Video.tsx`te taşma payı kaldırılarak (I-52 R3 yöntemi)
  üretilen gerçek 1080p render — **dört yön** (sağ/sol/üst/alt), parlak+koyu
  görsel, kısa+uzun süre — artı I-52'nin kendi karşı-örneği.
- **Temiz**: **15 gerçek geçmiş pilot** (i15, i16, i17, i18, i20, i37, i39,
  i42, i43, i41-vid, i52-vid, önizleme, smoke20, ses10 + I-54'ün temiz eşi).
- ⚠ **Train/held-out ayrımı ölçümden ÖNCE** sabitlendi ve diske yazıldı
  (`cikti/_i54_ayrim/i54_bolunme.json`).

### Eksen 1 — YÖN (dış sütun, 384, 8 fps)

| yön | TRAIN ayrım | HELD ayrım |
|---|---|---|
| yalnız yatay | **−103.79** | **−104.19** |
| yalnız dikey | **−91.15** | **−61.26** |
| **dört yön** | **+11.75** | **+9.94** |

Tek yön **hiçbir zaman** ayırmıyor → **dört yön zorunlu** (I-53'ün dikey
körlük bulgusu doğrulandı).

### Eksen 2 — AGREGASYON (dört yön, 384, 8 fps)

| agregasyon | kusur (T/H) | temiz (T/H) | ayrım (T/H) |
|---|---|---|---|
| **`serit_ort` (MEVCUT)** | 107.5 / 105.98 | 13.11 / 11.9 | **−94.39 / −94.08** |
| **`dis1` (en dış sütun/satır)** | **0.0 / 0.02** | **11.75 / 9.96** | **+11.75 / +9.94** |
| `dis2` | 35.65 / 9.49 | 12.99 / 9.99 | −22.66 / +0.5 |
| `serit_min` | 0.0 / 0.02 | 8.04 / 9.76 | +8.04 / +9.74 |

**Mevcut agregasyon ayırmıyor**; `dis1` en iyisi.

### Eksen 3+4 — ÇÖZÜNÜRLÜK × ZAMAN (dört yön, `dis1`)

| genişlik | 4 fps | 8 fps | 15 fps | 30 fps |
|---|---|---|---|---|
| 64 | −78 / −93 | −82 / −76 | −78 / −81 | −74 / −77 |
| 128 | −51 / −76 | −54 / −36 | −47 / −45 | −38 / −36 |
| 256 | −2.9 / −32.5 | −9.0 / +9.9 | **+2.1 / +6.8** | **+6.9 / +9.8** |
| **384** | +12.9 / **−1.1** | **+11.8 / +9.9** | **+11.7 / +9.6** | **+11.8 / +9.6** |

- **64 ve 128 hiçbir fps'te** ayırmıyor.
- **4 fps hiçbir çözünürlükte** ayırmıyor (384'te held **−1.1**).
- Ayrım **iki eksene birden** bağlı: 256 ancak **≥15 fps**, 384 ise **≥8 fps**.

### Ölçülen ayrım bandı (dört yön + `dis1` + 384 + 8 fps)

| taraf | değer |
|---|---|
| kusur tarafı **en yüksek** | **0.02** (train 0.0) |
| temiz tarafı **en düşük** | **9.96** (train 11.75) |
| tüm temiz korpus tabanı | **10.01** — `onizleme_lawn_i40` @ 22.25 sn |

Sonraki en düşükler: `ses10` 12.47, `i39` 15.86, `i37` 15.89.
**Örtüşme yok**; band genişliği ≈ **10 birim**.

### ⚠ I-53'ün iddiası kısmen düzeltildi

- *"kusur ≤ 2.9"* → **doğrulandı** (0.02'ye indi).
- *"temiz ≥ 15.0"* → **YANLIŞ**: gerçek temiz taban **10.01**. Eşik 15
  seçilseydi `onizleme_lawn_i40` ve `ses10` **yanlış pozitif** olurdu.

⚠ **Eşik SEÇİLMEDİ** — bu atom yalnızca bandı ölçer.

| Paket | A | B | C | D | E | F | G | H | I | Toplam |
|---|---|---|---|---|---|---|---|---|---|---|
| Zengin venv | 125 | 200 | 148 | 95 | 127 | 244 | 218 | 257 | **2081** | **3495** |

0 hata. Faz I 2063 → **2081** (+18). **1 BLOKE** — I-33 kaydı sürüyor.

### SONRAKİ ATOM — artık uygulanabilir

Ölçüm, I-53'ün istediği dört parçayı da sabitledi:
**dört yön** + **en dış sütun/satır** + **≥384 genişlik** + **≥8 fps**, ve
eşiğin konacağı **band (0.02, 9.96)**. Sonraki atom bu konfigürasyonu
bağımsız bir kenar ölçüm hattı olarak **uygulayabilir** (⚠ `OPTIK_ORNEK_FPS`
4'te kalmalı — I-17 durağanlık eşikleri ona bağlı) ve eşiği bandın içinden
**gerekçeli** seçebilir; yanlış pozitif 0 korunmalı.

⚠ Diğer açık borçlar: semantik kabul engeli (b002/b005 — **kullanıcı
kararı**), önizlemede altyazı çizilmemesi (I-40), model d > 1.31 ölçülmemiş.

---

## 71. FAZ I-53 — KENAR KAPISI KÖR NOKTASI: TEK PARAMETRELİK DÜZELTME **ELENDİ** (yalnız tanısal, 14 Ağu)

> **Durum: kör nokta SAYISALLAŞTIRILDI; "en küçük atom" olarak bir
> parametre değişikliğinin YETMEDİĞİ ölçüldü ve yaklaşım ELENDİ.
> Üretim kodu DEĞİŞMEDİ; ölçüm ve gerekçe teste kilitlendi.
> A–I yeşil (3477, 0 hata, 1 BLOKE — I-33 kaydı sürüyor). Render davranışı
> değişmediği için **rerender YOK**. Geçici varlıklar (195 MB sentetik kare
> ailesi) **temizlendi**. Deploy YOK. Maliyet $0.00.**
> Değişen: **yalnızca** `webapp/testler/test_faz_i.py` (+148 satır) ve
> handoff. `kalite_kapisi.py`, `Video.tsx`, `qa_on.py`, `medya/*`,
> `deploy.sh`, **eşikler** ve **22 alan sözleşmesi** **dokunulmadı**.
> I-23…I-52 **korundu**.

### Kurulan küme (gerçek 1080p kareler)

**A)** gerçek fotoğraf + kenara siyah bant: genişlik {5,10,20,30,40,60,80,120}
px × konum {sol,sağ,üst,alt} · **B)** 40 px bant, parlaklık {0,8,24,40} ·
**C)** yanlış pozitif adayları (düz foto, koyu foto, vinyet, çok karartılmış) ·
**D)** I-52'nin R3 render'ından **gerçek** bantlı kare (9 px).

### Ölçüm 1 — mevcut kapı yatayda yalnız ≥ 60 px görüyor

| bant | 5 | 10 | 20 | 30 | 40 | **60** | 80 | 120 |
|---|---|---|---|---|---|---|---|---|
| sol/sağ | kaçırdı | kaçırdı | kaçırdı | kaçırdı | kaçırdı | **işaret** | işaret | işaret |

**Kök neden**: şerit = %4 × kare genişliği ≈ **77 px** ve **ortalama**
alınıyor; şeritten dar bir bant içerikle ortalanıp eşiğin üstüne çıkıyor.

### Ölçüm 2 — ikinci kör nokta: DİKEY bant hiç görülmüyor

`ust`/`alt` bantları **120 px'te bile** kaçırılıyor. Kaynak kanıtı: fonksiyon
yalnızca **sol** ve **sağ** şeridi kuruyor; üst/alt şerit **hiç yok**.
(⚠ I-17 notu dikey pan'ın **daha büyük** pay gerektirdiğini söylüyor — yani
bu yön gerçek bir risk taşıyor.)

### ⛔ Ölçüm 3 (BELİRLEYİCİ) — kusur ZAMANSAL olarak da görünmez

I-52'nin gerçek bandı **0.25 sn'den kısa**. `OPTIK_ORNEK_FPS = 4` ızgarası
üzerinden **hiçbir uzamsal çözünürlükte** yakalanamıyor:

| örnekleme | 4 fps | 8 fps | 15 fps | 30 fps |
|---|---|---|---|---|
| ihlal | **0** | 2 (14.25 → **0.0**) | 2 | 6 |

Yani **uzamsal düzeltme tek başına bu kusuru yakalayamaz**.

### Ölçüm 4 — sözleşmeyi bozmayan agregasyon düzeltmesi yeni fayda vermiyor

Aynı sözleşme (64×36, 4 fps, eşik 16) + agregasyon *şerit ortalaması* yerine
**en dış sütun**: yedi gerçek videoda yanlış pozitif **0** — ama **kusurlu
karşı-örnekte de 0** (en koyu sütun 104.4). Kazanç yok.

### Ölçüm 5 — kusuru yakalayan konfigürasyon YANLIŞ POZİTİF üretiyor

256 genişlik + 8 fps + en dış sütun + eşik 16:

| küme | sonuç |
|---|---|
| kusurlu karşı-örnek | **2 ihlal** (0.0 ve 2.9) ✅ |
| I-52 temiz koşumlar | 0 ihlal (en koyu 115) ✅ |
| **PİLOT i39/i47/i51** | **1 ihlal, değer 15.8** (eşik 16.0) ⛔ |

Tam çözünürlükte incelendi: `t=20.25`'te sağ kenarın **40 sütununun tamamı**
< 16 — ince bant **değil**, kadraj kenarındaki **koyu orman içeriği** (parlak
ışın merkezde olduğu için `genel > 32` koruması da geçiyor). Pay yalnızca
**%1.25** (15.8 vs 16.0); I-38'de `POST-KENAR-SIYAH` **15.99 vs 16.0** tam bu
yüzden FAIL sayılmıştı — bıçak sırtı **kabul edilemez**.

### ⚠ Ayrıca: `KENAR_SIYAH_ESIGI = 16`'nın gerekçesi ölçümle çelişiyor

I-17 notu *"gerçek görüntü kenarı nadiren 16'nın altına düşer"* diyor;
ölçüldü ki gerçek bir orman karesinin kenarı **15.0**'a kadar iniyor.

### ⛔ Hüküm

Kör nokta **tek bir parametre değil, üç bağlı sınırdır**: (1) agregasyon
(şerit ortalaması), (2) **zamansal örnekleme** (4 fps), (3) **eşiğin kendisi**
(16, gerekçesi çürüdü). Bunların herhangi biri tek başına düzeltilirse ya
fayda sıfır kalıyor ya da gerçek pilotlarda yanlış pozitif doğuyor.
**"En küçük atom" olarak ELENDİ**; üretime hiçbir şey eklenmedi.

| Paket | A | B | C | D | E | F | G | H | I | Toplam |
|---|---|---|---|---|---|---|---|---|---|---|
| Zengin venv | 125 | 200 | 148 | 95 | 127 | 244 | 218 | 257 | **2063** | **3477** |

0 hata. Faz I 2044 → **2063** (+19). **1 BLOKE** — I-33 kaydı sürüyor.

### SONRAKİ ATOM — doğru kapsam ÖLÇÜLEREK belirlendi

Kenar kapısı için doğru atom **bağımsız bir kenar ölçüm hattıdır**, üç
parçası birlikte kalibre edilmeli:

1. **Bağımsız örnekleyici**: kendi genişliği (ölçüldü: 256 → 7.5 px/sütun,
   9 px bandı payla yakalar) ve kendi **zamansal** hızı (ölçüldü: ≥ 8 fps).
   ⚠ `OPTIK_ORNEK_FPS`'e **dokunulmamalı** — I-17 sözleşmesi durağanlık
   eşiklerini 4 fps'e bağlıyor.
2. **Agregasyon**: en dış sütun (şerit ortalaması değil).
3. **Eşiğin yeniden türetilmesi**: kusur tarafı ≤ **2.9**, temiz içerik
   tarafı ≥ **15.0** ölçüldü — ayrım geniş, ama eşik gerçek bir korpusta
   kalibre edilmeli (bu atomda **uydurulmadı**).
4. **Dikey (üst/alt) şerit** eklenmeli — şu an yapısal olarak kör.

⚠ Diğer açık borçlar: semantik kabul engeli (b002/b005 — **kullanıcı
kararı**), önizlemede altyazı çizilmemesi (I-40), model d > 1.31 ölçülmemiş.

---

## 70. FAZ I-52 — PAN TAŞMA PAYI, PAN YOKKEN DE ZOOM YOLUNU YİYORDU (14 Ağu)

> **Durum: I-43'te ölçülen borcun kök nedeni KODDA gösterildi ve ÇÖZÜLDÜ.
> `pan: 'yok'` sahnelerde optik hareket gerçek pilotta **+%9…+%35**; pan
> yapan sahneler **bit-bit aynı**. Kenar **0/101** ve **tam çözünürlükte
> 0 koyu sütun** — yanlış alarm yok. A–I yeşil (3458, 0 hata).
> POST-QA **WARN** (tek kalan bulgunun kök nedeni bu atom değil).
> MP4 **kabul edilmedi**. Deploy YOK. Maliyet $0.00.**
> Değişen: `app/render-studio/src/Video.tsx` (**tek dallanma**),
> `webapp/testler/test_faz_i.py`. `TABAN_OLCEK` formülü, `kalite_kapisi`,
> `qa_on`, `medya/*`, `deploy.sh`, **eşikler**, **22 alan sözleşmesi** ve
> **kullanıcı zoom/pan seçimleri** **dokunulmadı**. I-23…I-51 **korundu**.

### ⛔ Kök neden — kodda gösterildi

```js
TABAN_OLCEK(panPx, dikey, kareGen, kareYuk) = 1 + 2·panPx/kare + 0.012
```
`kbHesap` bu tabanı **koşulsuz** uyguluyordu; oysa **kayma** yalnızca
`sahne.pan` bir **yön** iken uygulanıyor (`pan: 'yok'` → `tx = ty = 0`).
Yani pan **yokken** de %3.49'luk taşma payı ödeniyor ve **doğrudan zoom
yolundan** düşüyordu:

| süre | taban | tepe | yol | etkin | **pay olmasa** yol / etkin |
|---|---|---|---|---|---|
| 2.201 sn | 1.0349 | 1.0990 | 0.0641 | **%2.914/sn** | **0.0870 / %3.955** |
| 5.549 sn | 1.0349 | 1.2497 | 0.2148 | %3.871/sn | 0.2377 / %4.284 |

I-43'ün ölçtüğü *"istenen %4.5/sn ekranda %2.91/sn"* tam olarak budur.

### Kontrollü ölçüm — üç gerçek render, aynı props

| sahne | R1 mevcut | **R2 koşullu** | R3 karşı-örnek |
|---|---|---|---|
| kisa-panyok-in | 2.388 | **3.236** | 3.236 |
| uzun-panyok-in | 2.913 | **3.236** | 3.237 |
| kisa-panvar-in | 2.794 | **2.794** | 3.576 |
| kisa-panyok-out | 2.394 | **3.232** | 3.235 |
| kisa-panvar-out | 2.731 | **2.730** | 3.489 |
| uzun-panvar-out | 2.969 | **2.971** | 3.290 |

R2 pan'sız sahneleri **%11–%35** iyileştiriyor, pan yapan sahneleri
**değiştirmiyor** (fark <%1).

### ⚠ Pay, pan YAPAN sahnede GERÇEKTEN gerekli — karşı-örnekle kanıtlandı

Payı **herkesten** kaldırınca (R3), **tam çözünürlükte** (1080p karede en dış
40 px, tamamen koyu sütun sayısı) siyah bant ölçüldü:

| koşum | en kötü koyu sütun |
|---|---|
| R1 mevcut | **0** |
| **R2 koşullu** | **0** |
| R3 karşı-örnek | **9** (`kisa-panvar-out@14.29` sağ=9, `uzun-panvar-out@19.74` sol=7) |

En kötü birleşim **zoom=out + pan=yön**: ölçek **düşerken** kayma **artar** —
4 Ağu'daki orijinal kusurun tarifi. Bu yüzden düzeltme **koşullu olmak
zorunda**; ilk test ailem bu birleşimi kapsamıyordu ve eklendi.

### ⚠ Ölçüm sınırı bulundu (kapsam dışı, sonraki atom adayı)

`kenar_siyahligi_olcusu` (64×36 örnekleme, %4 şerit) R3'ün **gerçek** siyah
bandını **görmedi** (0/79 dedi). Kaba ızgara ~20 px'lik bir bandı çözemiyor
(64 px genişlikte 20 px ≈ 0.67 sütun, 2 sütunluk şerit içinde eriyor).
Bu atomda kenar güvenliği **tam çözünürlükte** doğrulandı.

### Düzeltme (en küçük) — tek dallanma

```js
const panYok = sahne.pan === 'yok' || !sahne.pan;
const taban = TABAN_OLCEK(panYok ? 0 : panPx, dikeyPan, kareGen, kareYuk)
  + (panYok ? 0.012 : 0);
```
`TABAN_OLCEK` **formülü değişmedi**; `hizli` yolu (panPx=0) etkilenmedi;
dikey pan (`top`/`bottom`) payını **almaya devam ediyor**.

| Paket | A | B | C | D | E | F | G | H | I | Toplam |
|---|---|---|---|---|---|---|---|---|---|---|
| Zengin venv | 125 | 200 | 148 | 95 | 127 | 244 | 218 | 257 | **2044** | **3458** |

0 hata. Faz I 2023 → **2044** (+21). Red-first: 2 XX.

### 1080p pilot — `vidrushvideo_pan_i52.mp4` (25.2 sn)

Değişen yol `VidrushVideo` olduğu için **o** pilot koşuldu; I-43 pilotuyla
**aynı props** (elma-elmaya).

| sahne | kamera | I-43 | **I-52** | değişim |
|---|---|---|---|---|
| s0 | in/**yok** | 3.534 | **4.479** | **+26.7%** |
| s1 | out/**yok** | 0.955 | **1.288** | **+34.9%** |
| s2 | in/right | 2.914 | 2.914 | **+0.0%** |
| s3 | in/left | 2.810 | 2.810 | **+0.0%** |
| s4 | in/**yok** | 2.806 | **3.058** | **+9.0%** |
| s5 | out/**yok** | 2.195 | **2.450** | **+11.6%** |

- **1920×1080 @ 30**, aac 48 kHz/2ch, 25.259 sn · **6 kesme** · **11 kare** (6 beat)
- LUFS **−14.92** / TP −4.47 · sessizlik 1 aralık %1.4 · kırpma yok
- kenar **0/101** ve **tam çözünürlükte 0 koyu sütun**
- medya tekrarı **6 benzersiz**, bitişik yok · motion **4 hareket**, tekrar yok
- tipografi dört ölçümde **temiz** · künye 4 CC sahnesinde
- **POST-QA: WARN** — tek bulgu `s1` (ort 1.288 < 2.0)

⚠ **s1'in kök nedeni bu atom değil**: görselin uzamsal enerjisi
(I-44/I-45'te ölçüldü, |grad| 7.557 — kırpma enerjisi 9.391). Bu atom onu
da **%34.9 iyileştirdi** ama eşiğin altında kalıyor. Eşik **gevşetilmedi**.

### ⛔ Kabul durumu

**Kabul edilmiş MP4 değildir**, mutlak yol verilmedi, deploy yok: POST-QA
WARN ve ayrıca s0/s1 semantik uyumsuz (bilinen sınıf).

### SONRAKİ ATOM

1. **`kenar_siyahligi_olcusu` çözünürlük sınırı** — bu atomda ölçüldü:
   64×36 ızgara ~20 px'lik gerçek siyah bandı **kaçırıyor**. Dar, ölçülebilir,
   ağsız bir atom (örnekleme ölçüsü ya da şerit tanımı ölçülerek türetilir).
2. **Semantik kabul engeli** (b002/b005) — dört eleme sonrası **kullanıcı kararı**.
3. **Önizlemede altyazı hiç çizilmiyor** (I-40).
4. Model d ≤ 1.31'de doğrulandı; **d > 1.31** hâlâ ölçülmemiş.

---

## 69. FAZ I-51 — EKSİK VERİ ÜRETİLDİ, DOYGUNLUK ÖLÇÜLEREK KABUL EDİLDİ (14 Ağu)

> **Durum: I-50'nin işaret ettiği eksik veri (d ≥ 0.5) GERÇEK RENDERER'DA
> üretildi; doygunluk terimi TRAIN'de seçilip HELD-OUT'ta TEK KEZ ölçüldü
> ve **oracle beklentisi doğrulandı**: HELD MAE 15.7% → **7.6%**, en kötü
> 38.7% → **14.4%**, fail bandı 1.442 → **1.748**, **yanlış fail 0**.
> A–I yeşil (3437, 0 hata). 25.2 sn pilot POST-QA **PASS**, **11/11 kare
> SHA-256 aynı**. MP4 **kabul edilmedi** (semantik). Deploy YOK. $0.00.**
> Değişen: `webapp/editor/kalite_kapisi.py` (2 ölçülen sabit güncellendi +
> 1 doygunluk sabiti + tek satırlık formül), `webapp/testler/test_faz_i.py`.
> `Video.tsx`, `Kamera.tsx`, `qa_on.py`, `medya/*`, `deploy.sh`, **eşikler**
> ve **22 alan sözleşmesi** **dokunulmadı**. I-23…I-50 **korundu**.

### Üretilen veri — ölçüm, tahmin değil

Gerçek **editorv2 1080p** renderer'ında **18 yeni kontrollü nokta**: iki
enerji seviyesi × {**pan**, **zoom**} × hedef `d` ∈ {0.5, 0.65, 0.8, 1.1, 1.3}.

⚠ **Parametre uydurulmadı**: her hedef `d` için kamera parametresi üretimin
**kendi saf fonksiyonlarıyla** (`kadraj_kirpma_bolgesi` +
`yer_degistirme_alani`) **sayısal olarak çözüldü**; `guvenli_pay` üretimin
kendi formülünden (`motion._guvenli_pay`) geldi. Ölçek tavanı **1.8**
(üretimde punch-1.6 ile 1.696 görülmüştü) aşılan **6 zoom noktası
zorlanmadı, düşürüldü ve raporlandı**.

### ⚠ Train/held-out ayrımı RENDER'DAN ÖNCE sabitlendi

`cikti/_i51_kal/i51_bolunme.json` **render'dan önce** yazıldı:
hedef d **0.50/0.65/1.10 → TRAIN**, **0.80/1.30 → HELD-OUT**. Ayrıca
TRAIN'e I-46'nın 12 düşük-d noktası, HELD-OUT'a I-45'in **6 gerçek çekimi**
eklendi — böylece iki küme de hem düşük hem yüksek d içeriyor:

| küme | n | d aralığı | d ≥ 0.5 |
|---|---|---|---|
| TRAIN | 24 | 0.016–1.100 | 10 |
| HELD-OUT | 12 | 0.259–1.311 | 7 |

Katsayılar **yalnız TRAIN**'de arandı; HELD-OUT'ta **tek kez** ölçüldü.

### Ölçüm — tek değerlendirme

| model | TRAIN | HELD | HELD en kötü | fail bandı | yanlış fail |
|---|---|---|---|---|---|
| A doğrusal (eski üretim, k=0.8877) | 12.4% | 19.8% | **49.0%** | 1.342 | **0** |
| A doğrusal (train fit, k=0.8265) | 10.3% | 15.7% | 38.7% | 1.442 | **0** |
| **B doygunluk (SEÇİLEN)** | **7.3%** | **7.6%** | **14.4%** | **1.748** | **0** |
| C üstel | 6.6% | 5.4% | 15.7% | 1.728 | **0** |

⚠ Yeni yüksek-d held-out noktaları, **eski doğrusal modelin** en kötü
hatasını **%49'a** çıkardı — I-50'nin *"doygunluk rejimi ölçülmemiş"*
teşhisi **doğrulandı**.

⚠ **Oracle beklentisi tutturuldu**: I-50 *"en kötü ~%11.8, fail bandı ~1.79"*
demişti; ölçülen **%14.4** ve **1.748**.

### Model seçimi gerekçeli

**B seçildi**: üretim marjı `MODEL_EN_KOTU_HATA` ile kurulur ve B onu **en
küçük** yapar (%14.4 < %15.7), dolayısıyla **fail bandını en geniş** bırakır
(1.748 > 1.728). C'nin MAE'si daha iyi ama marjı daha geniş olurdu.

### Değişen üretim modeli (en küçük)

```
beklenen = k · E · d / (1 + d/d0)        (öncesi: k · E · d)
MODEL_K            0.8877 → 0.935
MODEL_D0           (yeni) 3.012
MODEL_EN_KOTU_HATA 0.229  → 0.144
```

`d ≪ d0` iken bölen ≈ 1 ve model **doğrusal kalır** — düşük-d davranışı
korunuyor (b002: beklenen 2.269, ölçülen 2.288; öncesi 2.356).
⚠ **`OPTIK_DURGUN_ESIGI` 2.0 AYNEN**; hiçbir eşik gevşetilmedi, enerji eşiği
(11.589) ve kalibrasyon gezinme hızı (0.0577) değişmedi.

| Paket | A | B | C | D | E | F | G | H | I | Toplam |
|---|---|---|---|---|---|---|---|---|---|---|
| Zengin venv | 125 | 200 | 148 | 95 | 127 | 244 | 218 | 257 | **2023** | **3437** |

0 hata. Faz I 2001 → **2023** (+22). Red-first: 8 XX.
⚠ I-46/I-50'nin eski katsayıları kilitleyen 9 kontrolü **devralındı** ve
yeni ölçülen değerlere bağlandı; I-50'nin **kendi bulgusu** (o günkü
veriyle aşırı uyum) **aynen kilitli** kalıyor.

### 1080p pilot — `editorv2_lawn_i51.mp4` (25.2 sn)

Üretim modeli değiştiği için tam pilot koşuldu. Sadakat: **beat eşit=True,
varlık eşit=True**.

- **1920×1080 @ 30**, aac 48 kHz/2ch, 25.259 sn · **8 kesme** · **11 kare** (6 beat)
- LUFS **−14.27** / TP **−3.10** · sessizlik **%0.0** · kırpma yok · kenar **0/101**
- medya tekrarı: **6 benzersiz varlık**, bitişik tekrar yok
- motion: **4 farklı hareket**, ardışık/işlev tekrarı yok, açılış≠kapanış
- tipografi: güvenli alan / yatay / nefes / çakışma **temiz** · künye 5 sahnede
- I-51 optik risk: **yok** · I-45 enerji: işaretlenen yok, kapsam dışı yok
- I-47 dönem uyarısı: **b001** (doğru pozitif, sürüyor)
- PRE-QA **WARN** (fail=0), **POST-QA: PASS**
- **Gerileme yok**: I-47 render'ıyla **11/11 kare SHA-256 birebir aynı**

### ⛔ Kabul durumu

**Kabul edilmiş MP4 değildir**, mutlak yol verilmedi, deploy yok: b001/b002
görselleri anlatımla **semantik uyumsuz**. ⚠ `cikti/_i51_kal` altındaki
**kalibrasyon render'ları kabul MP4'ü değildir** — yalnız ölçüm çıktısıdır.

### SONRAKİ ATOM

1. **Semantik kabul engeli** — dört bağımsız eleme (I-34/I-35/I-48/I-49)
   sonrası **kullanıcı kararı**: operatör onayı ya da VLM.
2. **Kısa sahnede zoom yolunun çoğunu pan taşma payı yiyor** (I-43'te
   ölçüldü: 2.201 sn'de istenen %4.5/sn ekranda %2.91/sn).
3. **Önizlemede altyazı hiç çizilmiyor** (I-40).
4. Model artık d ≤ 1.31 bandında doğrulandı; **d > 1.31** hâlâ ölçülmemiş.

---

## 68. FAZ I-50 — DOYGUNLUK TERİMİ, MEVCUT VERİYLE: **ELENDİ** (yalnız tanısal, 14 Ağu)

> **Durum: yaklaşım ÖLÇÜLDÜ ve ELENDİ. Üretim modeli DEĞİŞMEDİ
> (`MODEL_K` 0.8877, `MODEL_EN_KOTU_HATA` 0.229); ölçüm ve gerekçe teste
> kilitlendi. A–I yeşil (3415, 0 hata, 1 BLOKE — I-33 kaydı sürüyor).
> Renderer/üretim koduna dokunulmadı → **rerender YOK**. Yeni render
> alınmadı, yeni eşik uydurulmadı. Deploy YOK. Maliyet $0.00.**
> Değişen: **yalnızca** `webapp/testler/test_faz_i.py` (+129 satır) ve
> handoff (git ile doğrulandı: tek dosya). `kalite_kapisi.py`, `qa_on.py`,
> `Video.tsx`, `Kamera.tsx`, `medya/*`, `deploy.sh`, **22 alan sözleşmesi**
> **dokunulmadı**. I-23…I-49 **korundu**. Ağ / API / ücret / credential
> **yok**.

### Soru

I-46 modelinin (`optik = k · E · d`) d ≥ 0.5'te ölçülen **en kötü %22.9
fazla tahmini**, bir **doygunluk terimiyle** düzelir mi?

### Kurulum — sıkı train/held-out ayrımı

| küme | n | kaynak | d aralığı | d ≥ 0.5 |
|---|---|---|---|---|
| **TRAIN** | 12 | I-46 kontrollü aile (2 enerji × 3 zoom + 3 pan hızı) | 0.016–0.289 | **0** |
| **HELD-OUT** | 6 | I-45'in gerçek çekimleri (kalibrasyona hiç girmedi) | 0.259–1.311 | 1 |

Katsayılar **yalnız TRAIN**'de arandı; hüküm **yalnız HELD-OUT**'ta ölçüldü.

### ⛔ Ölçülen kök neden

**TRAIN kümesinde d ≥ 0.5 olan nokta YOK.** Doygunluk rejimi eğitim
verisinde **hiç temsil edilmiyor**; dolayısıyla doygunluk parametresi
TRAIN verisiyle **kısıtlanamaz**. En kötü hata ise tam o rejimde
(d = 1.311).

### Ölçüm (MAPE)

| model | TRAIN | HELD-OUT | HELD en kötü | parametre |
|---|---|---|---|---|
| **A mevcut** (k = medyan) | 9.5% | **10.8%** | **22.9%** | k=0.8877 |
| A doğrusal (train fit) | 9.4% | 10.6% | 22.4% | k=0.884 |
| B doygunluk `k·E·d/(1+d/d0)` | **7.8%** | **11.8%** ⛔ | **27.3%** ⛔ | k=0.985, d0=1.498 |
| C üstel `A(1−e^{−k·E·d/A})` | **7.8%** | **11.7%** ⛔ | **28.2%** ⛔ | k=0.93, A=16.18 |

⚠ **Klasik aşırı uyum**: ek parametre TRAIN'i iyileştiriyor (9.4 → 7.8) ama
**HELD-OUT'u kötüleştiriyor** (10.6 → 11.8) ve **en kötü hatayı büyütüyor**
(22.4 → 27.3 / 28.2).

### Fail/warn ayrımı da iyileşmiyor — aksine daralıyor

Dört modelde de **YANLIŞ FAIL = 0** (mevcut güvence korunuyor). Ancak
doygunluk modelleri hata payını büyüttüğü için **fail bandı daralıyor**:

| model | hata payı | fail sınırı (beklenen <) |
|---|---|---|
| **mevcut** | 22.9% | **1.627** |
| B | 27.3% | 1.571 |
| C | 28.2% | 1.560 |

Yani kapı **daha az** vaka yakalar. (C, "yanlış temiz" sayısını 1 → 0
düşürüyor — `pan-yuksek-0.7`: beklenen 2.026 ≥ 2.0 ama ölçülen 1.863 —
fakat bunu MAE'yi, en kötü hatayı ve fail bandını **kötüleştirerek** yapıyor.)

### Oracle — SIZINTI, doğrulama DEĞİL

Parametre **held-out'a** uydurulursa B: MAE **%6.0** / en kötü **%11.8**;
C: %5.8 / %12.3. Yani doygunlukta **gerçek sinyal var**, ama **mevcut train
verisi onu bulamıyor**. Bu, sonraki atomun ne olması gerektiğini söyler.

### ⛔ Hüküm

Mevcut veriyle doygunluk terimi **eklenmez**. `MODEL_K` ve
`MODEL_EN_KOTU_HATA` **değişmedi**; model hâlâ tek çarpım (`k · E · d`).
Zorlama yok, yeni eşik yok, sahte PASS yok.

| Paket | A | B | C | D | E | F | G | H | I | Toplam |
|---|---|---|---|---|---|---|---|---|---|---|
| Zengin venv | 125 | 200 | 148 | 95 | 127 | 244 | 218 | 257 | **2001** | **3415** |

0 hata. Faz I 1982 → **2001** (+19). **1 BLOKE** — I-33 kaydı sürüyor.

### SONRAKİ ATOM — ölçüm ne diyor

**Doygunluk için önce VERİ gerekiyor**: `d ≥ 0.5` bandında **kontrollü**
noktalar üretmek (yeni render gerektirir; bu atom tanısal olduğu için
alınmadı). Oracle bunun karşılığını ölçtü: en kötü hata **%22.9 → %11.8**
inebilir, bu da fail bandını **1.627 → ~1.79** genişletir. Ölçülmeden
model **değiştirilmemeli**.

⚠ Açık kalan diğer ölçülmüş kusurlar: **semantik kabul engeli**
(b002/b005 — dört bağımsız eleme sonrası **kullanıcı kararı**: operatör
onayı ya da VLM), kısa sahnede pan taşma payı (I-43), önizlemede altyazı
çizilmemesi (I-40).

---

## 67. FAZ I-49 — b005 TÜR/TAKSON, YEREL OLARAK: **ELENDİ** (yalnız tanısal, 13 Ağu)

> **Durum: yaklaşım ÖLÇÜLDÜ ve ELENDİ. Üretim kodu DEĞİŞMEDİ; ölçüm ve
> gerekçe teste kilitlendi. A–I yeşil (3396, 0 hata, 1 BLOKE — I-33 kaydı
> sürüyor). Render/medya davranışı değişmediği için **rerender YOK**.
> Deploy YOK. Maliyet $0.00.**
> Değişen: **yalnızca** `webapp/testler/test_faz_i.py` (+190 satır) ve
> handoff (git ile doğrulandı: tek dosya). `medya_kapisi.py`, `medya/*`,
> `editor/*`, `deploy.sh`, **22 alan sözleşmesi** **dokunulmadı**.
> Yeni sağlayıcı / **VLM / embedding / LLM** / ikinci ağ çağrısı / ücretli
> API / **paket-credential değişikliği** / özel-case kara liste **yok**.
> I-23…I-48 **korundu**.

### Soru

Üçüncü semantik negatif — **b005**, aday *"Ricinus communis seedling
NC2.jpg"*, anlatım **çim tohumu/fidesi** bağlamı — **yerel** olarak
sınanabilir mi?

### Ölçüm 1 — depoda taksonomik kaynak YOK

| kaynak | sonuç |
|---|---|
| kurulu taksonomi/ML paketi (nltk, spacy, Bio, sklearn, numpy, gensim, pygbif, ete3) | **YOK** |
| `taksonomi.py` | **konsept/niyet** taksonomisi — biyolojik **değil** |
| `webapp/veri/` | `anim`, `durumlar`, `gecici`, `onbellek` — tür verisi **yok** |

### Ölçüm 2 — aday metadata'sında tür/kategori alanı YOK

17 gerçek künyenin **21 alanı** tarandı (`aciklama`, `alaka_sirasi`,
`asset_id`, `atif_gerekli`, `atif_metni`, `baslik`, `eser_sahibi`,
`genislik`, `indirme_url`, `kaynak_niteligi`, `kaynak_saglayici`, `lisans`,
`lisans_url`, `mime`, `olcu_bilinmiyor`, `olculen_olcu`, `oran_karari`,
`orijinal_url`, `red_nedeni`, `render_kullanilabilir`, `saglayici`,
`yukseklik`) → **tür/kategori/takson alanı yok**.

### Ölçüm 3/4 — tek çıkarılabilir sinyal: Latin ikili adlandırma

Salt **yapısal** ölçüt (`taksonomi.py`'nin *"sinyal metnin biçiminden gelir"*
kuralının aynısı): büyük harfli cins + küçük harfli **Latin sonekli** epitet.

| beat | sınıf | sıkı sinyal | gevşek sinyal |
|---|---|---|---|
| b001 | NEG | `[]` | `[]` |
| **b002** | NEG | `['Heteropogon contortus']` | `['Heteropogon contortus']` |
| b003 | POZ | `[]` | `['Mountainview section']` |
| b004 | POZ | `[]` | `['Sprinkler head']` |
| **b005** | **NEG (hedef)** | `['Ricinus communis']` | `['Ricinus communis']` |
| b006 | POZ | `[]` | `[]` |

**Sıkı**: negatiflerde 2/3, pozitiflerde 0/3 — *ayırıyor gibi görünüyor*.
**Gevşek** (Latin sonek şartı olmadan): pozitiflerin **2/3'ünü** işaretliyor
→ kullanılamaz. **Ölçüm 5**: 17 gerçek adayda yanlış alarm **1** (b005'in
kendisi).

### ⛔ Ölçüm 6 (BELİRLEYİCİ) — sinyalin varlığı "yanlış" demek değil

Sinyal *"başlık bir tür adı taşıyor"* der; ***"tür yanlış"* demez.** Bu, kendi
verimizde kanıtlandı: işaretlenen iki adaydan biri olan **b002**'nin öznesi
*Heteropogon contortus* — **bir çim türüdür** (Poaceae), yani anlatımla
**aynı özne ailesinde**; b002'nin kusuru tür değil **yer/ortam** (I-48).
Dolayısıyla işaret kümesinin **yarısı** zaten tür uyuşmazlığı değil.

*"Ricinus communis çim değildir"* hükmünü vermek için **hangi türün çim
olduğunu** bilmek gerekir; bunun yerel karşılığı Ölçüm 1/2'de **arandı ve
yok**.

⚠ **Ters etki**: sinyal, bilimsel künyeli (tür adı taşıyan) **en iyi
etiketlenmiş** adayları da işaretlerdi — örneğin bir çim videosunda
*Lolium perenne* **doğru** adaydır — ve doğruyu yanlıştan **ayıramazdı**.

### ⛔ Hüküm — I-34/I-48 dersi uygulandı

**b005 tür/takson ayrımı mevcut yerel kaynaklarla taşınamaz.** Üretime
**eklenmedi**: ikili adlandırma sinyali yok, özel-case kara liste yok, yeni
paket/ağ/credential yok — üçü de teste kilitlendi. Zorlama yok, sahte PASS
yok, WARN da **eklenmedi** (ayıran güvenilir kanıt bulunamadığı için).

| Paket | A | B | C | D | E | F | G | H | I | Toplam |
|---|---|---|---|---|---|---|---|---|---|---|
| Zengin venv | 125 | 200 | 148 | 95 | 127 | 244 | 218 | 257 | **1982** | **3396** |

0 hata. Faz I 1963 → **1982** (+19). **1 BLOKE** — I-33 kaydı sürüyor.

### ⚠ Ayrıca ölçülen (bu atomda KULLANILMADI)

`aciklama` alanı 17 adayın **11'inde dolu** — ama lawn pilotunun **beş
adayının hepsinde BOŞ**. Yani bu pilot için daha zengin metin de yok.

### ⛔ Kabul durumu — DEĞİŞMEDİ

Pilot MP4 **kabul edilmiş değildir**, deploy yok. Üç semantik negatiften
**yalnız b001** otomatik işaretleniyor (I-47); **b002 ve b005 hâlâ gözle
uyumsuz ve otomatik kapılarla ulaşılamıyor**.

### SONRAKİ ATOM — ölçülen durum ne diyor

Semantik kabul engeli için **yerel yollar tükendi**; dört bağımsız eleme:

| atom | yaklaşım | sonuç |
|---|---|---|
| I-34 | kare-bakan görsel sinyaller | **elendi** (precision 0.25) |
| I-35 | sorgu daraltması | **elendi** (karşılıklı dışlayan kısıtlar) |
| I-48 | biyom/yer adı sözlüğü | **elendi** (kuşak ifade edilemiyor) |
| I-49 | tür/takson (yerel) | **elendi** (kaynak yok, sinyal hüküm taşımıyor) |

Geriye ölçülmemiş **iki** yol kalıyor ve **ikisi de kullanıcı kararıdır**:
**(1) operatör onayı**, **(2) yeni yetenek (VLM/görüntü-metin eşleme)** —
ikincisi ücret ve yeni bağımlılık doğurur; **kapsam/bütçe kararı
kullanıcıya aittir**.

⚠ Semantik dışında ölçülmüş açık kusurlar: model doygunluğu (I-46, %22.9),
kısa sahnede pan taşma payı (I-43), önizlemede altyazı çizilmemesi (I-40).

---

## 66. FAZ I-48 — b002 YER/ÖZNE, BİYOM SÖZLÜĞÜ YOLUYLA: **ELENDİ** (yalnız tanısal, 13 Ağu)

> **Durum: yaklaşım ÖLÇÜLDÜ ve ELENDİ. Üretim kodu DEĞİŞMEDİ; ölçüm ve
> gerekçe teste kilitlendi. A–I yeşil (3377, 0 hata, 1 BLOKE — I-33 kaydı
> sürüyor). Render/medya davranışı değişmediği için **rerender YOK**.
> Deploy YOK. Maliyet $0.00.**
> Değişen: **yalnızca** `webapp/testler/test_faz_i.py` (+ handoff).
> `medya_kapisi.py`, `medya/*`, `editor/*`, `deploy.sh` ve **22 alan
> sözleşmesi** **dokunulmadı** (git ile doğrulandı: tek dosya, +176 satır).
> Yeni sağlayıcı / ikinci ağ çağrısı / ücretli API / credential değişikliği
> **yok**; tek `ara()`, mevcut kota ve **429 devre kesici** aynen.
> I-23…I-47 **korundu**.

### Soru

I-47'nin yakalayamadığı **b002** negatifi — aday başlığındaki
*"Kanapou-Kahoolawe"* yer adı — **mevcut yerel biyom sözlüğüyle**, ağsız ve
deterministik olarak sınanabilir mi?

### Ölçüm 1 — mevcut sözlükle altı gerçek çift

| beat | sınıf | sahne biyomu | aday biyomu | kapı |
|---|---|---|---|---|
| b001 | NEG (dönem) | `[]` | `[]` | geçer |
| **b002** | **NEG (hedef)** | `[]` | `[]` | geçer |
| b003 | POZ | `[]` | `[]` | geçer |
| b004 | POZ | `[]` | `[]` | geçer |
| b005 | NEG (tür) | `[]` | `[]` | geçer |
| b006 | POZ | `[]` | `[]` | geçer |

**Video bağlamının biyomu da `[]`.** `biyom_kapisi` her iki tarafın biyomunu
ister ("emin değilsen geçir") → kapı bu iş sınıfında **yapısal olarak atıl**;
gerekçe birebir *"biyomu çıkarılamadı — kapı uygulanmadı"*.

### Ölçüm 2 — yer adı eklense bile çelişki üretilemiyor

Varsayımsal uzatma (`Kahoolawe`/`Kanapou` → **tropik**; sözlükte zaten
`hawaii`, `svalbard`, `south georgia` gibi yer adları var, yani bu mevcut
desenin uzantısı) ölçüldü:

- aday tarafı **`{tropik}`** kazanıyor ✅
- **sahne tarafı `[]` kalıyor** ⛔ → çelişki **üretilemiyor**

Yani yer adı eklemek **tek başına** b002'yi yakalayamaz.

### Ölçüm 3 — kök neden: sahnenin kuşağı SÖZLÜKTE İFADE EDİLEMİYOR

Sözlükte dört kuşak var: `col` · `kent` · `kutup` · `tropik`.
**"ılıman/temperate" kuşağı YOK** ve `lawn`/`grass`/`garden` işareti
**hiçbir kuşakta** yok. "ABD banliyö çimi" kuşağı **yazılamıyor**, dolayısıyla
`CELISEN` tablosu bu çelişkiyi **ifade edemiyor**.

### Ölçüm 4 — eklenmesi gereken iddia FAKTÜEL OLARAK YANLIŞ

Kapıyı çalıştırmak için `CELISEN`'e **"çim/bahçe sahnesi ⊥ tropik aday"**
yazmak gerekirdi. Bu iddia **genel olarak yanlıştır**: sözlükte `hawaii`
**tropik** kuşaktadır ve b002 adayının öznesi *Heteropogon contortus* —
**bir çim türüdür**. İki taraf aynı özne ailesinde; iklim çelişkisi **yoktur**.
Kapı bu örnekte ancak **kazayla** doğru sonuç verirdi.

### Ölçüm 5 — kelime örtüşmesi TERS çalışıyor

| beat | sınıf | anlatımla ortak kelime |
|---|---|---|
| b002 | **NEG** | `['bag', 'seed']` — **iki** |
| b005 | NEG | `['seedling']` |
| b001 | NEG | `['grass']` |
| b003 | POZ | `['lawn', 'patchy', 'the']` |
| **b004** | **POZ** | `[]` — **sıfır** |
| **b006** | **POZ** | `[]` — **sıfır** |

İki **pozitif** kontrol anlatımla **hiç** kelime paylaşmıyor; **negatif**
b002 iki kelime paylaşıyor. Kelime tabanlı her ayrım negatifleri
pozitiflerin **üstüne** koyar — I-34'te ölçülen *"ayıran eşik yok"*
durumunun aynısı.

### ⛔ Hüküm — I-34 dersi uygulandı

**Yer/özne ayrımı mevcut yerel sözlükle taşınamaz.** Üretime **eklenmedi**:
yer adları sözlüğe girmedi, yeni kuşak/çelişki eklenmedi, **özel-case kara
liste yok** (varlığa/dosyaya özel eşleme olmadığı teste kilitlendi).
Zorlama yok, sahte PASS yok.

| Paket | A | B | C | D | E | F | G | H | I | Toplam |
|---|---|---|---|---|---|---|---|---|---|---|
| Zengin venv | 125 | 200 | 148 | 95 | 127 | 244 | 218 | 257 | **1963** | **3377** |

0 hata. Faz I 1941 → **1963** (+22). **1 BLOKE** — I-33 görsel inceleme
kaydı sürüyor.

### ⛔ Kabul durumu — DEĞİŞMEDİ

Pilot MP4 **kabul edilmiş değildir**, deploy yok. Üç semantik negatiften
**yalnız b001** otomatik işaretleniyor (I-47); **b002 ve b005 hâlâ gözle
uyumsuz ve otomatik kapılarla ulaşılamıyor**.

### SONRAKİ ATOM — ölçülen durum ne diyor

b002 için **yerel metin/sözlük yolları tükendi**: I-34 (kare sinyalleri),
I-35 (sorgu daraltması) ve şimdi I-48 (biyom/yer adı) ölçülüp elendi.
Geriye ölçülmemiş **iki** yol kalıyor ve **ikisi de kullanıcı kararıdır**:

1. **Operatör onayı** — b001/b002 gibi adayları insan onayına bağlamak
   (I-34'te de aynı yere çıkmıştı).
2. **Yeni yetenek (VLM/görüntü-metin eşleme)** — ücret ve yeni bağımlılık
   doğurur; bu atomların ölçümü onu **gerekçelendirmiyor değil**, aksine
   üç bağımsız elemeyle **işaret ediyor**; ama **kapsam/bütçe kararı
   kullanıcıya aittir**.

⚠ **b005 (tür/tür-adı) bu atomda genişletilmedi** (talimat gereği); ölçülmemiş
durumda ve taksonomik bilgi ister.
⚠ Bunlar dışında ölçülen açık kusurlar: model doygunluğu (I-46, %22.9),
kısa sahnede pan taşma payı (I-43), önizlemede altyazı çizilmemesi (I-40).

---

## 65. FAZ I-47 — DÖNEM KAPISI TEK YÖNLÜYDÜ (ilk otomatik semantik işaret, 13 Ağu)

> **Durum: kabul engelinin ÜÇ negatifinden BİRİ (b001) artık OTOMATİK
> işaretleniyor — bu, semantik uyuşmazlığın pipeline'da ilk kez görünür
> olmasıdır. ⚠ b002/b005 bu sinyalle ULAŞILAMAZ (ölçüldü) → **kabul engeli
> SÜRÜYOR**. A–I yeşil (3355, 0 hata). Seçim DEĞİŞMEDİ: **11/11 kare
> SHA-256 aynı**, POST-QA **PASS**. Deploy YOK. Maliyet $0.00.**
> Değişen: `webapp/medya_kapisi.py` (1 saf fonksiyon — `kapi()` zincirine
> GİRMEZ), `webapp/editor/qa_on.py` (1 kod + ölçüm), `test_faz_i.py`.
> `medya/*`, `edinim.py`, `siralama.py`, `Video.tsx`, `Kamera.tsx`,
> **eşikler** ve **22 alan sözleşmesi** **dokunulmadı**. I-23…I-46 **korundu**.

### ⚠ Önce ELENENLER tekrarlanmadı

- **I-34** kare-bakan sinyaller (metin yoğunluğu / kenar / düz-parlak /
  specular): 28 ölçümde **ayıran eşik yok**, en iyi precision 0.25 → elendi.
- **I-35** sorgu daraltması: vitrini eleyen her daraltma NASA'yı boşaltıyor,
  koruyan her daraltma vitrini bırakıyor → elendi. (`-display` gibi negatif
  terim I-29'da ölçüldü: recall %0, 7 işaretin 5'i yanlış pozitif.)
- Bu atom **yeni sağlayıcı, ikinci ağ çağrısı, ücretli API, sahte
  embedding/LLM** kullanmaz; yalnızca **zaten var olan** metadata metnini
  okur. `ara()` sayısı, kota ve 429 devre kesici **aynen**.

### ⛔ Ölçülen kusur — KAPI TEK YÖNLÜ

`donem_kapisi` yalnızca **sahne** tarihselse adayı denetliyor; `tarihsel_mi
(sahne)` False ise **hemen True** dönüyor. Ters yön — **tarihsel aday,
güncel sahnede** — hiç denetlenmiyordu. Pilotun **gerçek** çiftlerinde
ölçüldü (altı çiftin **altısı da** mevcut kapılardan geçiyor):

| beat | aday başlığı | tarihsel(aday) | gözle |
|---|---|---|---|
| **b001** | *"Vegetable, grass and flower seeds, **1900** (1900)"* | **EVET** | ⛔ 1900 atlı pulluk |
| b002 | *"Starr-101229-…-Kanapou-Kahoolawe"* | hayır | ⛔ kızıl toprak erozyon sahası |
| b003 | *"2025-04-07 … A patchy lawn in spring …"* | hayır | ✅ |
| b004 | *"Sprinkler Irrigation - Sprinkler head"* | hayır | ✅ |
| b005 | *"Ricinus communis seedling NC2"* | hayır | ⛔ cim değil (kene otu) |
| b006 | *"Dülmen, Mühlenwegfriedhof -- 2012 -- 8083"* | hayır | ✅ |

Anlatım *"…on my garage shelf **right now**"* güncel; aday 1900 tarihli bir
tohum kataloğu fotoğrafı — **gözle doğrulanan uyuşmazlığın ta kendisi**.

### Yanlış alarm oranı GERÇEK kümede ölçüldü

Önbellekteki **17 gerçek aday künyesinin yalnız 1'i** "tarihsel"
işaretleniyor — ve o da **b001'in kendisi**. 16 temiz aday işaretlenmedi.

### Düzeltme (en küçük)

`medya_kapisi.donem_uyarisi(sahne, aday)` — **saf**, ağsız. Uyarı yalnızca
**aday tarihsel VE sahne tarihsel değil** iken. Dönen kayıt hangi işaretin
(`['1900','1900']`) ve hangi yönün tetiklediğini yazar.

⚠ **SEÇİMİ DEĞİŞTİRMEZ**: `kapi()` zincirine **girmez**, aday **elenmez** —
`kapi()` bit-bit aynı (test kilitler). I-35'te ölçüldü ki nadir bir kalite
kusurunu sık bir **tam başarısızlıkla** (`KALITE-MEDYASIZ-BEAT`) takas etmek
yanlış mühendisliktir. PRE-QA'da `KALITE-SEMANTIK-DONEM` (**warn**,
FAIL_KODLARI'nda **değil**) olarak görünür kılınır.

⚠ **DÜRÜST KAPSAM RAPORLANIYOR**: dönen kayıt `kapsam: "yalniz-donem"`
taşır. b002 (yer/özne uyuşmazlığı) ve b005 (Ricinus communis — çim değil)
**bu sinyalle ulaşılamaz**; ölçüldü ve **asla "temiz" diye sunulmuyor**.
Üç negatiften **biri** yakalanıyor.

| Paket | A | B | C | D | E | F | G | H | I | Toplam |
|---|---|---|---|---|---|---|---|---|---|---|
| Zengin venv | 125 | 200 | 148 | 95 | 127 | 244 | 218 | 257 | **1941** | **3355** |

0 hata. Faz I 1921 → **1941** (+20). Red-first: 3 XX (7 kontrol hasattr
korumasında bekliyordu).

### 1080p pilot — `editorv2_lawn_i47.mp4` (25.2 sn)

Sadakat kapısı **beat eşit=True, varlık eşit=True**.

- **Kapı yalnız b001'i işaretledi**; b002–b006 temiz → PRE-QA warn 3 → **4**
  (yeni olan `KALITE-SEMANTIK-DONEM`, fail=0)
- **Gözle doğrulandı**: b001 karesi sepya/arşiv, atlı pulluk; altyazı
  *"There is a bag of grass seed on my garage shelf right now."* → işaret
  **doğru pozitif**
- **1920×1080 @ 30**, 25.259 sn · 8 kesme · **11 kare** (6 beat)
- LUFS **−14.27** / TP −3.10 · sessizlik %0.0 · kenar **0/101**
- medya tekrarı 6 benzersiz · motion 4 hareket, tekrar yok · tipografi dört
  ölçümde temiz · künye 5 sahnede · optik risk **yok**
- **POST-QA: PASS** · **Seçim/render değişmedi**: I-46 ile **11/11 kare
  SHA-256 birebir aynı**

### ⛔ Kabul durumu — ENGEL SÜRÜYOR

**Kabul edilmiş MP4 değildir**, mutlak yol verilmedi, deploy yok. Üç semantik
negatiften biri artık otomatik işaretleniyor; **b002 ve b005 hâlâ gözle
uyumsuz ve otomatik kapılarla ulaşılamıyor**.

### SONRAKİ ATOM (I-48) — yalnız ölçülen kusurdan

1. **b002 — yer/özne uyuşmazlığı**: aday başlığı bir YER adı taşıyor
   (*Kanapou-Kahoolawe*) ve anlatımın yeriyle ilgisi yok. `medya_kapisi`
   zaten **biyom** sözlüğü taşıyor; yer adı → biyom eşlemesi **ölçülerek**
   sınanabilir (ağsız, sözlük tabanlı). ⚠ I-34'ün dersi: ayıran eşik yoksa
   **elenmeli**, zorlanmamalı.
2. **b005 — tür/tür-adı uyuşmazlığı** (*Ricinus communis* ≠ çim): taksonomik
   bilgi ister; mevcut yerel bağımlılıklarla **ulaşılamaz** görünüyor —
   ölçülmeden yeni yetenek önerilmemeli.
3. **Model büyük yer değiştirmede doygunlaşıyor** (I-46'da ölçüldü: %22.9).
4. **Önizlemede altyazı hiç çizilmiyor** (I-40).

---

## 64. FAZ I-46 — RİSK OPTİK BİRİMDE İFADE EDİLMİYORDU (kalite atomu, 13 Ağu)

> **Durum: enerji×yer değiştirme ilişkisi ÖLÇÜLEREK kalibre edildi, pan ve
> zoom alanları AYRIŞTIRILDI, risk artık OPTİK BİRİMDE ifade ediliyor.
> Kapsam dışı çekim **2 → 0**, yanlış alarm **0**; kod ölçülen hata payıyla
> **FAIL** seviyesine çıkarıldı. A–I yeşil (3335, 0 hata). Render **11/11
> kare SHA-256 aynı**. POST-QA **PASS**, MP4 **kabul edilmedi** (semantik).
> Deploy YOK. Maliyet $0.00.**
> Değişen: `webapp/editor/kalite_kapisi.py` (2 saf fonksiyon + 2 ölçülen
> sabit + motion grammar optik bacağı), `webapp/editor/qa_on.py` (1 kod +
> kablolama), `webapp/testler/test_faz_i.py`. `Video.tsx`, `Kamera.tsx`,
> `motion.py`, `pipeline.py`, `medya/*`, **eşikler** ve **22 alan
> sözleşmesi** **dokunulmadı**. I-23…I-45 **korundu**.

### ⛔ Ölçülen kusur

I-45 eşiği **tek bir gezinme hızında** (0.0577/sn) kalibreydi; dışındaki
çekimlerde **hüküm veremiyordu** (b002/b005 "kapsam dışı"). Ayrıca pan ile
zoom **aynı** gezinmeyi üretse bile optikte ayrı davranıyor (ölçüldü:
b003 örtüşme 0.707 → 7.485; b002 0.774 → 2.288) — tek skaler yetmiyor.

### Model TÜRETİLDİ, uydurulmadı

Optik ölçüm ardışık örnek kareler arası ortalama mutlak farktır; durağan bir
görüntü kayarken birinci mertebede `|I(p+d) − I(p)| ≈ |∇I|·d`, yani
**enerji × yer değiştirme**. Alan I-45 kadraj geometrisinden çıkar:

```
ekranda (u,v) → kaynakta (x + u·w, y + v·h)
Ds_x = Dcx + (u−0.5)·Dw     d_x(u) = 64 · Ds_x / w
Ds_y = Dcy + (v−0.5)·Dh     d_y(v) = 36 · Ds_y / h
```

⚠ Ayrıştırma **merkezden** yapılır, köşeden değil: köşe kayması
`Dx = Dcx − Dw/2` zoom bileşenini de içerir (ilk denemede bu kusur ölçüldü —
saf zoom'da `d_oteleme` 0.53 çıkıyordu, düzeltmeden sonra ~0). **PAN** saf
öteleme (tüm karede aynı), **ZOOM** merkezde 0 / kenarda en büyük.

### Kalibrasyon — GERÇEK RENDER'DA, 12 kontrollü nokta

editorv2 1080p, iki enerji seviyesi × (üç zoom hızı + üç pan hızı), $0.00:

| tür | E | d | optik | k = optik/(E·d) |
|---|---|---|---|---|
| zoom | 18.565 | 0.15031 | 2.477 | 0.888 |
| zoom | 19.067 | 0.28945 | 4.562 | 0.827 |
| zoom | 19.709 | 0.20190 | 3.303 | 0.830 |
| pan | 18.625 | 0.01616 | 0.378 | 1.256 |
| pan | 18.591 | 0.04920 | 0.779 | 0.852 |
| pan | 18.612 | 0.12261 | 1.863 | 0.816 |
| zoom | 8.756 | 0.15031 | 1.270 | 0.965 |
| zoom | 8.756 | 0.28945 | 2.135 | 0.842 |
| zoom | 8.756 | 0.20190 | 1.563 | 0.884 |
| pan | 8.483 | 0.01616 | 0.188 | 1.371 |
| pan | 8.471 | 0.04920 | 0.398 | 0.955 |
| pan | 8.502 | 0.12261 | 0.934 | 0.896 |

**`MODEL_K = 0.8877`** (medyan; uç noktalara dayanıklı).

### Doğrulama — TUTULAN ÖRNEK (kalibrasyona girmedi)

I-45'in altı gerçek çekimi:

| beat | E | d | beklenen | ölçülen | hata |
|---|---|---|---|---|---|
| b001 | 15.596 | 0.2852 | 3.949 | 4.438 | −11.0% |
| b002 | 9.391 | 0.2826 | **2.356** | **2.288** | **+3.0%** |
| b003 | 19.962 | 0.4940 | 8.753 | 7.485 | +16.9% |
| b004 | 17.347 | 1.3113 | 20.193 | 16.431 | **+22.9%** |
| b005 | 10.469 | 0.2595 | 2.411 | 2.686 | −10.2% |
| b006 | 13.467 | 0.2618 | 3.130 | 3.116 | +0.5% |

Ortalama mutlak hata **%10.8**, en kötü **%22.9** (b004; d=1.31 örnek piksel
ile birinci mertebe rejiminin dışında) — ve model **fazla** tahmin ediyor,
yani "hareket az" kapısı için **güvenli yön**. **`MODEL_EN_KOTU_HATA = 0.229`**.

### Düzeltme (en küçük) — risk OPTİK BİRİMDE

- `yer_degistirme_alani(bas, son, sure_sn)` — **saf**; `d`, `d_oteleme`
  (pan), `d_olcek` (zoom) ayrı raporlanır.
- `beklenen_optik_olcusu(enerji, d)` — **saf**; `beklenen = k·E·d`,
  `ust_sinir = beklenen·(1 + en_kotu_hata)`.
- Hüküm **mevcut `OPTIK_DURGUN_ESIGI` (2.0)** ile verilir — **yeni eşik yok**:
  · `fail` : `ust_sinir < 2.0` (ölçülen hata payıyla bile eşiği geçemez)
  · `warn` : `beklenen < 2.0` ama üst sınır geçebiliyor → **EMIN DEGILSEN ENGELLEME**
  · `temiz`: `beklenen ≥ 2.0`
- `motion_grammar_olcusu`: `yer_degistirme` verilirse **optik bacağı** çalışır
  ve enerji-eşiği bacağı atlanır (o bacak tek hızda kalibreydi). Verilmezse
  **I-45 davranışı bit-bit aynı** (test kilitler).
- PRE-QA: `KALITE-OPTIK-DURGUN-BEKLENEN` — **FAIL_KODLARI'na eklendi**.

⚠ **FAIL'E YÜKSELTME GEREKÇESİ ÖLÇÜLDÜ**: 12 kontrollü + 6 tutulan noktanın
**hiçbirinde yanlış fail yok**; gerçek düşük-hareket vakaları (ölçülen optik
0.188 / 0.398 / 0.934 / 1.270 / 1.563) doğru yakalanıyor. Bir gerçek pozitif
kaçıyor (pan 0.7, ölçülen 1.863) — **az engelleme** yönünde, kasıtlı.
⚠ Hiçbir eşik gevşetilmedi (optik 2.0 / enerji 11.589 / zoom tabanı 0.045).

| Paket | A | B | C | D | E | F | G | H | I | Toplam |
|---|---|---|---|---|---|---|---|---|---|---|
| Zengin venv | 125 | 200 | 148 | 95 | 127 | 244 | 218 | 257 | **1921** | **3335** |

0 hata. Faz I 1893 → **1921** (+28). Red-first: 8 XX.

### 1080p pilot — `editorv2_lawn_i46.mp4` (25.2 sn)

Sadakat kapısı **beat eşit=True, varlık eşit=True**.

- **Kapsam dışı 2 → 0**: b002/b005 artık **yargılanıyor** ve `temiz` çıkıyor
  (I-45'te hüküm verilemiyordu)
- **Yanlış alarm 0**, PRE-QA warn **3** (üçü de I-44 öncesinden)
- **1920×1080 @ 30**, 25.259 sn · 8 kesme · **11 kare** (6 beat)
- LUFS **−14.27** / TP −3.10 · sessizlik %0.0 · kenar **0/101**
- medya tekrarı: 6 benzersiz varlık · motion: 4 hareket, tekrar yok ·
  tipografi dört ölçümde temiz · künye 5 sahnede
- **POST-QA: PASS** · **Gerileme yok**: I-45 ile **11/11 kare SHA-256 aynı**

### ⛔ Kabul durumu

Otomatik kapıların hepsi PASS. Yine de **kabul edilmiş MP4 değildir**, mutlak
yol verilmedi, deploy yok: b001/b002 görselleri anlatımla **semantik uyumsuz**.

### SONRAKİ ATOM (I-47) — yalnız ölçülen kusurdan

1. **Medya seçiminde semantik doğrulama yok** (b001/b002/b005) — artık
   **kabul engelinin TEK nedeni**; hareket/enerji tarafı I-42…I-46 ile
   ölçülebilir hale geldi.
2. **Model büyük yer değiştirmede doygunlaşıyor** (ölçüldü: d=1.31'de %22.9
   fazla tahmin). d ≳ 0.5 için doygunluk terimi ölçülüp eklenirse hata payı
   daralır ve fail bandı genişler.
3. **Kısa sahnede zoom yolunun çoğunu pan taşma payı yiyor** (I-43).
4. **Önizlemede altyazı hiç çizilmiyor** (I-40).

---

## 63. FAZ I-45 — ENERJİ EKRANA GELMEYEN PİKSELLERDE DE ÖLÇÜLÜYORDU (kalite atomu, 13 Ağu)

> **Durum: gösterilen kadraj bölgesi ARTIK GERÇEK RENDERER TRANSFORMUNDAN
> türetiliyor ve enerji ORADA ölçülüyor. ⚠ Atomun hipotezi ÖLÇÜMLE ÇÜRÜDÜ
> (aşağıya bakınız) ve gerçek kök neden ölçülerek bulundu → pilotta
> **yanlış alarm 1 → 0**, PRE-QA warn 4 → 3. A–I yeşil (3307, 0 hata).
> Render **11/11 kare SHA-256 aynı** — gerileme yok. POST-QA **PASS**, ama
> MP4 **kabul edilmedi** (b001/b002 semantik). Deploy YOK. Maliyet $0.00.**
> Değişen: `webapp/editor/kalite_kapisi.py` (2 saf fonksiyon + 1 sabit +
> örnekleyiciye kırpma + motion grammar alan kontrolü),
> `webapp/editor/qa_on.py` (1 kod + kablolama), `webapp/testler/test_faz_i.py`.
> `Video.tsx`, `Kamera.tsx`, `motion.py`, `pipeline.py`, `medya/*`,
> `server.py`, `deploy.sh`, **eşikler** ve **22 alan sözleşmesi**
> **dokunulmadı**. I-23…I-44 **korundu**.

### ⛔ Ölçülen kusur

I-44 enerjiyi **tüm karede** ölçüyordu; oysa renderer `kadraj`/`punch` ile
**kırpıyor** — ölçülen piksellerin bir kısmı ekrana **hiç gelmiyor**. I-44
pilotunda b002 tam karede 7.557 ölçülüp işaretlendi ama gerçek render'da
optik **2.288** ile eşiği **geçti** (yanlış alarm).

### Geometri UYDURULMADI — `Kamera.tsx`ten birebir türetildi

```
Zemin: %100×%100, objectFit: cover,
       transform: scale(S) translate(x%, y%), transformOrigin center
CSS transform SAĞDAN SOLA uygulanır, yüzde kayma ELEMANIN KENDİ ölçüsüne göre:
       q = merkez + S · ((p − merkez) + (dx, dy))
Tersi → görünen eleman dikdörtgeni: W/S × H/S, merkez (W/2 − dx, H/2 − dy)
cover → kapsama = max(W/sw, H/sh)   (`punch_buyutme_olcusu` ile AYNI aritmetik)
KAYNAK piksel uzayında:  w = W/(S·kapsama·sw)   cx = 0.5 − dx/(kapsama·sw)
                         h = H/(S·kapsama·sh)   cy = 0.5 − dy/(kapsama·sh)
Kamera.tsx: kaymaX = (pxT−0.5)·2·pay·100,  kaymaY = (0.5−odakY)·2·pay·100
```

Pilotun **gerçek** b002 parametreleriyle (`zoom [1.5342, 1.35]`, `pay 0.1567`,
kaynak 3456×2592) doğrulandı: t=1'de kırpma **0.7407×0.5556** (ortalı),
t=0'da **0.6518×0.4889**. Testler bu sayıları ve pan/odak yönlerini kilitler.

### ⚠ ATOMUN HİPOTEZİ ÖLÇÜMLE ÇÜRÜDÜ

Pilotun altı çekimi gerçek kadrajlarıyla ölçüldü:

| beat | kadraj | tam kare | **kırpma** | optik | tam-kare kapı | kırpma-kapı |
|---|---|---|---|---|---|---|
| b001 | tam | 14.887 | 15.596 | 4.438 | temiz | temiz |
| **b002** | punch-1.35 | **7.557** | **9.391** | **2.288** | ⚠ alarm | ⚠ **hâlâ alarm** |
| b003 | ust | 15.792 | 19.962 | 7.485 | temiz | temiz |
| b004 | punch-1.6 | 18.083 | 17.347 | 16.431 | temiz | temiz |
| **b005** | alt | 12.330 | **10.469** | 2.686 | temiz | ⚠ **YENİ yanlış alarm** |
| b006 | tam | 13.867 | 13.467 | 3.116 | temiz | temiz |

**Kırpmada ölçmek yanlış alarmı azaltmadı — artırdı.** Tahmin değil, ölçüm.

### Gerçek kök neden — EŞİĞİN KALİBRASYON ALANI

`UZAMSAL_ENERJI_ESIGI` (11.589) **tek bir kamera konfigürasyonunda**
ölçülmüştü: `VidrushVideo`, oran 0.045, 4.0 sn, pan=yok. O konfigürasyonun
**kendi aritmetiğinden** gezinme hızı türetilir (Video.tsx `kbHesap`):

```
taban ölçek = 1 + 2·22/1920 + 0.012 = 1.0349
tepe  ölçek = max(1 + 0.045·4, taban + 0.06) = 1.1800
iç içe dikdörtgenlerde IoU = (1.0349/1.1800)² = 0.769
gezinme hızı = (1 − 0.769) / 4.0 sn = 0.0577 /sn
```

editorv2 çekimleri **0.0527–0.1139 /sn** aralığında geziniyor. b002 tam
**0.1025 /sn** ile kalibrasyonun **1.78 katı**; kalibrasyon ailesinde ~9.1
enerjide optik **1.294** ölçülmüştü ve **1.294 × 1.78 = 2.30**, gerçek
render'da ölçülen **2.288** ile örtüşüyor. Yani eşiği başka bir gezinme
hızında uygulamak **I-43'ün birim uyuşmazlığının aynısıdır**.

### Düzeltme (en küçük)

- `kadraj_kirpma_bolgesi(...)` — **saf**; `t` anında ekrana gelen kaynak
  bölgesi. Ölçü geçersizse `olculdu=False` (**engellemez**).
- `kadraj_gezinme_hizi(bas, son, sure_sn)` — **saf**; (1 − IoU)/süre ve
  `kalibrasyon_icinde` bayrağı.
- `KALIBRASYON_GEZINME_HIZI = 0.0577` — uydurma değil, **kalibrasyonun kendi
  konfigürasyonundan** türetildi (yukarıdaki aritmetik).
- `gorsel_ornek_komutu(..., kirpma=...)` — önce **kırpar**, sonra 64×36 gri
  örnekler (renderer da önce kadrajlıyor). ⚠ Kırpmasız çağrı I-44'teki
  komutu **bit-bit** üretir (test kilitler).
- `motion_grammar_olcusu`: enerji eşiği yalnız **kalibrasyon alanı içindeki**
  çekimlere uygulanır; dışındakiler sessizce geçilmez → `gezinme_kapsam_disi`.
- PRE-QA: `KALITE-MEDYA-ENERJI-KAPSAM-DISI` (**bilgi**).
- ⚠ Enerji **iki uçta da** ölçülür ve **en yükseği** alınır — varlığa en
  elverişli uç; `EMIN DEGILSEN ENGELLEME` yönünde muhafazakâr.

⚠ **FAIL'E YÜKSELTİLMEDİ**: ölçüm yeterince kesinleşmedi — kırpma enerjisi
b002'yi hâlâ eşiğin altında bırakıyor (9.391 ≤ 11.589) hâlde çekim geçiyor.
`warn` ve `EMIN DEGILSEN ENGELLEME` korundu. Hiçbir eşik gevşetilmedi
(optik 2.0, enerji 11.589), zoom kovası yükseltilmedi (I-43 tabanı 0.045).

| Paket | A | B | C | D | E | F | G | H | I | Toplam |
|---|---|---|---|---|---|---|---|---|---|---|
| Zengin venv | 125 | 200 | 148 | 95 | 127 | 244 | 218 | 257 | **1893** | **3307** |

0 hata. Faz I 1865 → **1893** (+28). Red-first: 20 kontrolün **9'u XX**.

### 1080p pilot — `editorv2_lawn_i45.mp4` (25.2 sn)

Üretim hattının kendi yolu; sadakat kapısı **beat eşit=True, varlık eşit=True**.

- **Yanlış alarm 1 → 0**: `isaretlenen: []` (I-44'te b002 warn'lanıyordu);
  PRE-QA **warn 4 → 3** (kalan üçü I-44 öncesinden: PERDE-EKSIK,
  SAGLAYICI-TEKEL, GECIS-ASIRI)
- **Kapsam dışı (bilgi, sessiz değil)**: b002 (enerji 9.391, gezinme 0.1025/sn),
  b005 (10.469, 0.0819/sn)
- **1920×1080 @ 30**, aac 48 kHz/2ch, 25.259 sn · 8 kesme · **11 kare** (6 beat)
- LUFS **−14.27** / TP −3.10 · sessizlik **%0.0** · kenar **0/101**
- medya tekrarı: 6 benzersiz varlık, bitişik tekrar yok · motion: 4 farklı
  hareket, ardışık/işlev tekrarı yok, açılış≠kapanış · tipografi dört ölçümde
  temiz · künye 5 sahnede
- **POST-QA: PASS**
- **Gerileme yok**: I-44 render'ıyla **11/11 kare SHA-256 birebir aynı**
  (I-45 render'a dokunmaz; kareler I-44'te gözle de incelenmişti)

### ⛔ Kabul durumu

Otomatik kapıların hepsi PASS. Buna rağmen **kabul edilmiş MP4 değildir**,
mutlak yol verilmedi, deploy yok: b001/b002 görselleri anlatımla **semantik
uyumsuz** (I-39'dan beri açık b001/b002/b005 sınıfı).

### SONRAKİ ATOM (I-46) — yalnız ölçülen kusurdan

1. **Enerji–optik ilişkisi gezinme hızına bağlı ve yalnız TEK hızda ölçüldü**
   (0.0577/sn). Ölçülen kanıt: aynı enerjide 1.78× gezinme → 1.78× optik
   (1.294 → 2.288 beklendi/ölçüldü). Doğru atom: **enerji × gezinme**
   yüzeyini birkaç hızda ölçüp eşiği **optik birimde** ifade etmek — o zaman
   kapsam dışı çekimler de yargılanabilir ve kapı **fail**'e çıkabilir.
   ⚠ Pan ile zoom farklı davranıyor (ölçüldü: b003 IoU 0.707 → optik 7.485,
   b002 IoU 0.774 → 2.288); yüzey **yer değiştirme alanı** ile kurulmalı.
2. **Medya seçiminde semantik doğrulama yok** (b001/b002/b005) — **kabul
   engelinin tek kalan nedeni budur**, dördüncü kez gözle doğrulandı.
3. **Kısa sahnede zoom yolunun çoğunu pan taşma payı yiyor** (I-43'te ölçüldü).
4. **Önizlemede altyazı hiç çizilmiyor** (I-40'ta ölçüldü).

---

## 62. FAZ I-44 — GÖRSELİN UZAMSAL ENERJİSİ HİÇ ÖLÇÜLMÜYORDU (kalite atomu, 13 Ağu)

> **Durum: ölçülen kusur ARTIK ÖLÇÜLÜYOR ve GERÇEK PİLOTTA doğru varlığı
> işaretledi (b002, enerji 7.557 ≤ eşik 11.589; diğer 5 varlık 12.33–18.08
> işaretlenmedi). A–I yeşil (3279, 0 hata). Render **11/11 kare SHA-256
> aynı** — gerileme yok. POST-QA **PASS**, ama MP4 **kabul edilmedi**
> (b001/b002 semantik, gözle doğrulandı). Deploy YOK. Maliyet $0.00.**
> Değişen: `webapp/editor/kalite_kapisi.py` (1 ölçüm + 1 komut üretici +
> motion grammar enerji bacağı), `webapp/editor/qa_on.py` (2 kod + kablolama),
> `webapp/editor/plan.py` ve `webapp/edit_kopru.py` (yalnız parametre taşıma),
> `webapp/testler/test_faz_i.py`.
> `Video.tsx`, `pipeline.py`, `medya/*`, `medya_kapisi.py`, `server.py`,
> `deploy.sh` ve **22 alan sözleşmesi** **dokunulmadı**. I-23…I-43 **korundu**.

### ⛔ Ölçülen kök neden

I-43, kalan tek optik bulgunun kök nedenini üç renderle ayrıştırmıştı: **süre
de kova da değil, görselin kendisi**. Aynı süre + aynı etkin hızda kalibre
görsel **3.690**, düz görsel **1.457**; süre uzatılıp etkin hız artırılınca
bile **1.643**. Yani düz bir varlık statik fotoğraf olarak kullanıldığında
kamera ne yaparsa yapsın ekranda hareket üretmiyor — **ama hiçbir kapı
görselin uzamsal enerjisini ölçmüyordu**; kusur ancak render sonrası
`KALITE-OPTIK-DURGUN` ile görülebiliyordu.

### Kalibrasyon — değer TAHMİN EDİLMEDİ, ÖLÇÜLDÜ

**Nedensel aile**: tek görselin efektif çözünürlüğü kademeli düşürüldü
(scale W → geri 1920, **düzgün** yeniden örnekleme). ⚠ İlk deneme
`flags=neighbor` ile yapıldı ve **başarısız oldu** — blok kenarları enerjiyi
yapay yüksek tuttu (15.79 → 15.03, aralık açılmadı); ölçülüp elendi.
İçerik/kompozisyon aynı, değişen tek şey uzamsal enerji. Her üye **üretim
tabanı oranıyla (0.045)**, 4.0 sn, **en kötü kamera birleşimiyle (`pan: yok`)**
1080p render edilip ölçüldü:

| enerji | optik | pay | en uzun durağan seri | sonuç |
|---|---|---|---|---|
| 5.866 | 0.719 | ×0.36 | 3.0 sn | ⛔ eşiğin altında |
| 7.590 | 1.011 | ×0.51 | 3.0 sn | ⛔ |
| 9.092 | 1.294 | ×0.65 | 3.0 sn | ⛔ |
| 10.249 | 1.522 | ×0.76 | 3.0 sn | ⛔ |
| **11.589** | **1.841** | ×0.92 | 1.0 sn | ⛔ **ölçülen en yüksek kalan** |
| **12.589** | **2.172** | ×1.09 | 0.5 sn | ✅ **ölçülen en düşük geçen** |
| 15.789 | 2.819 | ×1.41 | 0.0 sn | ✅ |

**Doğal kontrol** (6 gerçek önbellek görseli): 7.557 / 12.330 / 13.867 /
14.887 / 15.792 / 18.083 — I-43 pilotunda optiği eşiğin **altında** kalan tek
görsel 7.557 olandı. Nedensel aile ve doğal kontrol **aynı yeri** işaret
ediyor.

⚠ **Eşik ölçülen KUSURLU tarafa konuldu**: `UZAMSAL_ENERJI_ESIGI = 11.589` —
optiği eşiğin altında olduğu **ölçülen en yüksek** enerji. Böylece kapı,
**geçtiği ölçülen** hiçbir varlığı (en düşük geçen 12.589) reddetmez.

### Düzeltme (en küçük)

- `kalite_kapisi.uzamsal_enerji_olcusu(ham)` — **saf**: dosya açmaz, komut
  koşturmaz. Enerji = komşu pikseller arası ortalama mutlak fark (yatay+dikey).
- `kalite_kapisi.gorsel_ornek_komutu(yol)` — örnekleme komutunu **üretir**.
  ⚠ Optikle **birebir aynı** sözleşme (64×36 gri) — ikinci aritmetik yok.
- `motion_grammar_olcusu` enerji bacağı: yalnız **statik fotoğrafa** uygulanır
  (video klibin kendi hareketi vardır); enerji verilmezse `enerji_olculdu=False`
  yazılır, **"temiz" denmez**.
- PRE-QA: `KALITE-MEDYA-DUSUK-ENERJI` (**warn**) + `KALITE-MEDYA-ENERJI-OLCULEMEDI`
  (bilgi). Ölçer `enerji_okuyucu` ile **dışarıdan** verilir
  (`benzerlik_okuyucu` ile aynı sözleşme) — modül görsel açmaz.

⚠ **SEVİYE `warn`, FAIL DEĞİL** — `EMIN DEGILSEN ENGELLEME` sözleşmesi
(`edinim.py` ile aynı): enerji **tüm karede** ölçülür, oysa editorv2
`kadraj`/`punch` ile kaynağı **kırpabilir**. Bu karar pilotta **ölçülerek
doğrulandı** (aşağıya bakınız): FAIL olsaydı gerçekte PASS eden bir render
haksız yere bloke edilecekti.

⚠ **OPTİK EŞİK GEVŞETİLMEDİ** (2.0 / 1.5 / 3.0) ve **ZOOM KOVASI
YÜKSELTİLMEDİ** (I-43 tabanı 0.045, tablo aynı) — test ikisini de kilitler.

| Paket | A | B | C | D | E | F | G | H | I | Toplam |
|---|---|---|---|---|---|---|---|---|---|---|
| Zengin venv | 125 | 200 | 148 | 95 | 127 | 244 | 218 | 257 | **1865** | **3279** |

0 hata. Faz I 1838 → **1865** (+27). Red-first: 20 kontrolün **10'u XX**.

### 1080p pilot — `editorv2_lawn_i44.mp4` (25.2 sn)

Üretim hattının **kendi yolu** koşuldu: `edit_kopru.plan_kur` → PRE-QA →
`remotion_v2` → POST-QA. Medya/ses önbellekten, **$0.00**.
Sadakat kapısı: **beat eşit=True, varlık eşit=True** (I-38/I-41 ile aynı) —
ölçüm I-44 değişikliğine atfedilebilir.

**Kapının kararı — atomun iddiası:**

| varlık | ölçülen enerji | kapı |
|---|---|---|
| **s01_grass_seed_bag_1** (b002) | **7.557** | ⚠ **KALITE-MEDYA-DUSUK-ENERJI** |
| s04_grass_seedling | 12.330 | temiz |
| s05_green_lawn_grass | 13.867 | temiz |
| s01_grass_seed_bag | 14.887 | temiz |
| s02_patchy_lawn | 15.792 | temiz |
| s03_sprinkler | 18.083 | temiz |

Kapı **yalnız** I-43'te 0.955 ölçen varlığı işaretledi; **aşırı engelleme yok**.

- **1920×1080 @ 30**, aac 48 kHz/2ch, 25.259 sn · **8 kesme** · **11 kare** (6 beat kapsandı)
- LUFS **−14.27** (remaster sonrası) / TP **−3.10** · **sessizlik %0.0** · kırpma yok
- kenar siyahlığı **0/101** · medya tekrarı: 6 benzersiz varlık, benzerlik **ölçüldü**, benzer çift yok
- motion grammar: 4 farklı hareket, ardışık/işlev tekrarı yok, açılış≠kapanış
- tipografi: güvenli alan / yatay / nefes / çakışma **temiz**; künye **5 sahnede** çiziliyor
- PRE-QA **WARN** (fail=0): PERDE-EKSIK, SAGLAYICI-TEKEL, GECIS-ASIRI (üçü de I-44 öncesinden) + **yeni** KALITE-MEDYA-DUSUK-ENERJI
- **POST-QA: PASS** (sorun yok)

**Gerileme yok — ölçülerek:** I-41 render'ıyla **11 karenin 11'i de SHA-256
birebir aynı**. I-44 render'a dokunmaz; bu kanıtla doğrulandı.

### ⚠ `warn` kararı pilotta ÖLÇÜLEREK doğrulandı

Aynı düşük enerjili varlık (7.557) **editorv2 yolunda optik 2.288 ölçtü ve
eşiği GEÇTİ** — çünkü editorv2 `kadraj`/`punch` ile kırpıyor ve kırpılan
bölgenin enerjisi tüm karenin enerjisinden farklı. Aynı varlık
`VidrushVideo` yolunda (kırpma yok) **0.955** ölçmüştü. Yani:

- kapının işaretlediği risk **gerçek** (bir renderer'da ölçüldü),
- ama **her yolda gerçekleşmiyor** → `fail` olsaydı **PASS eden bir render
  haksız yere bloke edilecekti**. `EMIN DEGILSEN ENGELLEME` doğru karardı.

### ⛔ Kabul durumu

**Otomatik kapıların hepsi PASS.** Buna rağmen **kabul edilmiş MP4 değildir**,
mutlak yol verilmedi, deploy yok: **gözle doğrulandı** ki b001 (1900 tarihli
atlı pulluk fotoğrafı) ve b002 (kızıl toprak erozyon sahası) anlatımla
(*"There is a bag of grass seed on my garage shelf right now."*) **semantik
olarak uyumsuz** — I-39'dan beri bilinen ve hâlâ açık olan b001/b002/b005
sınıfı.

### SONRAKİ ATOM (I-45) — yalnız ölçülen kusurdan

1. **Enerji TÜM karede ölçülüyor, oysa render KIRPIYOR** (ölçüldü: aynı
   varlık kırpmasız yolda 0.955, `punch` kırpmalı yolda 2.288). Doğru atom:
   enerjiyi **çekimin gerçek kadraj bölgesinde** ölçmek — böylece kapı hem
   yanlış alarm vermez hem de gerçek riski FAIL seviyesine çıkarabilir.
2. **Medya seçiminde semantik doğrulama yok** (b001/b002/b005) — bu pilotta
   üçüncü kez gözle doğrulandı; **kabul engelinin tek kalan nedeni budur**.
3. **Kısa sahnede zoom yolunun çoğunu pan taşma payı yiyor** (I-43'te ölçüldü:
   2.201 sn'de istenen %4.5/sn ekranda %2.91/sn).
4. **Önizlemede altyazı hiç çizilmiyor** (I-40'ta ölçüldü).

---

## 61. FAZ I-43 — ZOOM KOVALARI OPTİK ÖLÇÜM BİRİMİYLE HİZALANMAMIŞTI (kalite atomu, 13 Ağu)

> **Durum: ölçülen birim uyuşmazlığı ÇÖZÜLDÜ ve GERÇEK RENDER'DA doğrulandı
> (aynı 25.2 sn pilotta eşiği geçen sahne **2/6 → 5/6**, karşı-olgu render'ıyla).
> A–I yeşil (3252, 0 hata). ⛔ Pilotun POST-QA'sı **WARN** — kalan tek bulgunun
> kök nedeni ÖLÇÜLDÜ ve bu atomun konusu DEĞİL (görsel enerjisi).
> Eşik GEVŞETİLMEDİ. Deploy YOK. Maliyet $0.00.**
> Değişen: `app/render-studio/src/Video.tsx` (1 sabit + `Math.max`),
> `webapp/testler/test_faz_i.py`. `pipeline.py`, `hizli_render.py`,
> `editor/*`, `medya/*`, `server.py`, `deploy.sh`, **ZOOM_KOVA tablosu**,
> **indeks aritmetiği** ve **22 alan sözleşmesi** **dokunulmadı**.
> I-23…I-42 **korundu**.

### ⛔ Ölçülen kök neden — BİRİM UYUŞMAZLIĞI

`ZOOM_KOVA` oranları **referans kanal ölçümünden** gelir; birim **"%/sn zoom
hızı"** ve ölçüm **canlı çekimlerde** yapıldı — o karelerde zoomun dışında
özne/kamera hareketi de vardı. Optik kapı ise **başka bir şey** ölçer:
ardışık gri karelerin ortalama mutlak farkı (0-255, 4 fps / 64×36). Bizim
çıktı **durağan fotoğraf**; ekrandaki tek hareket transformdur. Yani
referansın "ihmal edilebilir/sakin" kovalarının canlı çekimde **bedava
aldığı** hareket bizde **yoktur** → kovalar kendi kapımızı geçemiyordu.
I-42 pilotunda ölçülmüştü: s1 (0.032) **1.915**, s2 (0.014) **1.214**.

### Kalibrasyon — değer TAHMİN EDİLMEDİ, ÖLÇÜLDÜ

Her aday oran için `zoomOrani` geçici olarak sabitlendi ve **pilotun kendi üç
(görsel, zoom, pan) birleşimi** 1080p render edilip ölçüldü (en kötü durum
`pan: "yok"` dâhil), sahne başına 4.0 sn:

| oran | en kötü ort | pay | durağan seri (üç sahne) | sonuç |
|---|---|---|---|---|
| 0.032 "belirgin" | **1.868** | ×0.93 | 0.75 / 0.75 / 1.25 sn | **2/3 sahne KALIR** |
| 0.038 | 2.322 | ×1.16 | 0.25 / 0.25 / 0.25 sn | geçer, seri VAR |
| 0.041 | 2.544 | ×1.27 | 0.0 / 0.25 / 0.0 sn | geçer, seri VAR |
| **0.045** | **2.827** | **×1.41** | **0.0 / 0.0 / 0.0 sn** | ✅ **hepsi temiz** |
| 0.062 "agresif" | 3.931 | ×1.97 | 0.0 / 0.0 / 0.0 sn | ✅ (I-42 açılışı) |

⚠ **Ölçüt ÖLÇÜMDEN ÖNCE yazıldı**: (a) ortalama eşiği geçsin, (b) en uzun
durağan seri **tüm** sahnelerde 0.0 sn olsun, (c) en kötü pay **≥ ×1.25**.
(c) uydurma değil — 0.032'nin üç görseldeki yayılımı **×0.93–×1.00 ölçüldü**,
yani bıçak sırtı bir pay tek bir görsel değişince düşüyor (I-38'de
`POST-KENAR-SIYAH` 15.99 vs 16.0 tam olarak böyle FAIL olmuştu).
Ölçütü karşılayan **en küçük taranan oran: `OPTIK_TABAN_ORANI = 0.045`**.

### Düzeltme (en küçük)

`zoomOrani`nin döndürdüğü oran `Math.max(k.oran, OPTIK_TABAN_ORANI)` ile
tabana çekilir. **Kova tablosu, `2749 % 1000` aritmetiği, kullanıcının
`zoom`/`pan` seçimleri ve 22 alan sözleşmesi dokunulmadı**; I-42 açılışı
(0.062) tabanın üstünde olduğu için **bit-bit aynı** kaldı.

⚠ **EŞİK GEVŞETİLMEDİ**: `OPTIK_DURGUN_ESIGI` 2.0, WARN 1.5 sn, FAIL 3.0 sn,
örnekleme 4 fps/64×36, `OPTIK_ASIRI_ESIGI` 45.0 aynen duruyor — test kilitler.

⚠ **DÜRÜST SONUÇ**: taban 0.004/0.014/0.032 kovalarını yutar (indekslerin
~%87'si). Orada kaybedilen şey "çeşitlilik" değil, **kusur derecesiydi** —
o kovalar durağan fotoğrafta zaten kapının altındaydı. Tablo dağılımın
**kayıtlı** hali olarak duruyor; tabanın **üstünde** çeşitlilik kazanmak
ayrı ve **ölçülmemiş** bir atomdur.

| Paket | A | B | C | D | E | F | G | H | I | Toplam |
|---|---|---|---|---|---|---|---|---|---|---|
| Zengin venv | 125 | 200 | 148 | 95 | 127 | 244 | 218 | 257 | **1838** | **3252** |

0 hata. Faz I 1818 → **1838** (+20). Red-first: 20 kontrolün **6'sı XX**.

### 1080p pilot — `vidrushvideo_kova_i43.mp4` (25.2 sn)

Sahneler **uydurulmadı**: üretim hattının **gerçek planı** okundu
(`cikti/_i37_calisma/render_plan.json`) — 6 beat, gerçek süreler, gerçek
anlatım metinleri, gerçek `bas_sn` dilimleri; künyeler medyanın **gerçek**
`.kunye.json` dosyalarından üretilip props'a hattın **kendi** yardımcısıyla
(`pipeline._kaynak_yazi_props`) taşındı. Medya/ses önbellekten, **$0.00**.

- **1920×1080 @ 30**, aac 48 kHz/2ch, 25.259 sn, 97.29 MB · **6 kesme** · **11 kare** (6 beat'in hepsi kapsandı)
- LUFS **−14.92** / TP **−4.47** / LRA 3.0 · kırpma **yok** · **sessizlik 1 aralık, 0.347 sn (%1.4)**
- kenar siyahlığı **0/101** · medya tekrarı: **6 benzersiz varlık**, bitişik tekrar yok
- motion grammar: **4 farklı hareket**, ardışık/pencere/işlev tekrarı **yok**, açılış≠kapanış
- tipografi: güvenli alan / yatay / nefes / çakışma **dördü de temiz**; künye **4 CC sahnesinde çiziliyor** (kareyle doğrulandı), PD sahnesinde alan **yok**

**Atomun iddiası — AYNI props ile KARŞI-OLGU render'ı (taban kapalı = I-42 davranışı):**

| sahne | oran ÖNCE | optik ÖNCE | oran SONRA | optik SONRA | durum |
|---|---|---|---|---|---|
| s0 | 0.062 | 3.535 | 0.062 | 3.534 | değişmedi (taban dışı) |
| s1 | 0.032 | 0.904 | 0.045 | **0.955** | ⛔ hâlâ kalıyor |
| s2 | 0.014 | 1.046 | 0.045 | **2.914** | ✅ düzeldi |
| s3 | 0.004 | 1.021 | 0.045 | **2.810** | ✅ düzeldi |
| s4 | 0.062 | 2.806 | 0.062 | 2.806 | değişmedi (taban dışı) |
| s5 | 0.032 | 1.469 | 0.045 | **2.195** | ✅ düzeldi |

**Eşiği geçen sahne: 2/6 → 5/6.** Taban dışı sahneler bit-bit aynı kaldı.

⛔ **POST-QA: WARN — kabul edilmiş MP4 DEĞİLDİR.** Mutlak yol verilmedi.

| bulgu | seviye | detay |
|---|---|---|
| `POST-OPTIK-DURGUN` s1 | WARN | ort **0.955** < 2.0, en uzun durağan seri 1.25 sn |

### s1'in kök nedeni TAHMİN EDİLMEDİ, AYRIŞTIRILDI

Üç tek sahnelik render (hepsi oran 0.045, `zoom=out`, `pan=yok`):

| vaka | görsel | süre | etkin hız | optik | sonuç |
|---|---|---|---|---|---|
| A | s1'in görseli | 2.201 sn | %2.91/sn | **1.457** | ⛔ kalır |
| B | s1'in görseli | 5.550 sn | %3.87/sn | **1.643** | ⛔ kalır |
| C | kalibre görsel | 2.201 sn | %2.91/sn | **3.690** | ✅ geçer |

**C vs A**: aynı süre, aynı etkin hız, farklı görsel → **fark 2.5 kat**.
**B**: süre uzatılıp etkin hız artırılınca bile geçmiyor.
Yani kök neden **süre de kova da değil, GÖRSELİN KENDİSİ**. Ölçüldü —
ortalama yatay gradyan (uzamsal detay, 64×36 gri):

| görsel | \|grad\| | pilottaki optik |
|---|---|---|
| **s01_grass_seed_bag_1** (s1) | **4.21** | **0.955** ⛔ |
| s05_green_lawn_grass | 10.92 | 2.195 |
| s04_grass_seedling | 11.17 | 2.806 |
| s01_grass_seed_bag | 12.61 | 3.534 |
| s02_patchy_lawn | 12.74 | 2.914 |
| s03_sprinkler | 15.20 | 2.810 |

s1'in görseli (kızıl toprak + boş gökyüzü, geniş düz alanlar) diğer beşin
**üçte biri** detaya sahip. **Hiçbir makul zoom oranı düz bir görseli
kurtarmıyor** — bu, kovanın değil **medya seçiminin** sorunudur.

⚠ Ayrıca **gözle doğrulandı**: s0 (1900 tarihli atlı pulluk fotoğrafı) ve s1
(kızıl toprak erozyon sahası) anlatımla (*"There is a bag of grass seed on my
garage shelf right now."*) **semantik olarak uyumsuz** — bilinen b001/b002
kusur sınıfı, otomatik kapıların hepsi PASS. Bu da MP4'ün kabul edilmemesinin
ikinci nedeni.

### SONRAKİ ATOM (I-44) — yalnız ölçülen kusurdan

1. **Optik hareket görselin uzamsal enerjisine bağlı ve bu HİÇ ölçülmüyor**
   (ölçüldü: \|grad\| 4.21 → optik 0.955; 10.9–15.2 → 2.2–3.5). Doğru atom:
   medya seçiminde/kapısında **görsel enerjisini ölçmek** — ya düşük enerjili
   varlığı elemek ya da ona verilen hareketi ölçülen enerjiye göre
   türetmek. ⚠ Körlemesine eşik düşürmek YANLIŞ, kovayı yükseltmek de
   ölçüldüğü gibi ÇÖZMÜYOR (vaka B).
2. **Kısa sahnede zoom yolunun çoğunu pan taşma payı yiyor** (ölçüldü:
   `kbHesap` tabanı 1.0349; 2.201 sn'de istenen %4.5/sn ekranda **%2.91/sn**
   oluyor). Tek başına eşiği düşürmedi ama etkiyi zayıflatıyor.
3. **Önizlemede altyazı hiç çizilmiyor** (I-40'ta ölçüldü).
4. **Medya seçiminde semantik doğrulama yok** (b001/b002/b005) — s0/s1'de
   bu pilotta yeniden gözle doğrulandı.

---

## 60. FAZ I-42 — AÇILIŞ ÇEKİMİ HER VİDEODA EN DURAĞAN OLANDI (kalite atomu, 13 Ağu)

> **Durum: ölçülen kusur ÇÖZÜLDÜ ve GERÇEK RENDER'DA doğrulandı
> (açılış optik ortalaması **1.421 → 4.016**, durağan seri **3.0 sn → 0.0**).
> A–I yeşil (3232, 0 hata). ⛔ Pilotun POST-QA'sı **FAIL** — kalan iki bulgu
> **kapsam dışı bırakılan** sahneler (s1/s2). Eşik GEVŞETİLMEDİ.
> Deploy YOK. Maliyet $0.00.**
> Değişen: `app/render-studio/src/Video.tsx` (1 sabit + 1 dallanma),
> `webapp/testler/test_faz_i.py`. `pipeline.py`, `hizli_render.py`,
> `editor/*`, `medya/*`, `server.py`, `deploy.sh` ve **22 alan sözleşmesi**
> **dokunulmadı**. I-23…I-41 **korundu**.

### ⛔ Ölçülen kök neden

`VidrushVideo` zoom hızını sahne indeksinden deterministik seçiyor:
`r = ((indeks * 2749) % 1000) / 1000`. **indeks 0 için r daima 0.000** →
**daima ilk kova: %0.4/sn ("ihmal edilebilir")**. Yani **açılış/hook çekimi
her üretimde dağılımın en durağan ucuna sabitleniyordu** — bu bir tercih
değil, indeks aritmetiğinin yan etkisiydi. I-41 pilotunda ölçüldü:
`s0` optik ortalama **1.421** < eşik **2.0**, en uzun durağan seri **3.0 sn**.

### Kalibrasyon — değer TAHMİN EDİLMEDİ, ÖLÇÜLDÜ

Dağılımın **kendi kovaları** aday alındı; her biri için 4 sn'lik tek sahnelik
gerçek 1080p `VidrushVideo` render edilip `kalite_kapisi` ile ölçüldü:

| aday kova | optik ortalama | durağan sn | eşik 2.0 |
|---|---|---|---|
| 0.014 "sakin" | **1.45** | 3.0 | ⛔ kalır |
| 0.032 "belirgin" | **2.005** | 0.75 | ✅ geçer — **pay yalnız 0.005** |
| 0.062 "agresif" | **4.103** | 0.0 | ✅ geçer |

**0.032 seçilmedi**: 0.005'lik pay bıçak sırtıdır ve başka bir görselde
düşer (I-38'de `POST-KENAR-SIYAH` 15.99 vs 16.0 tam olarak bu yüzden FAIL
sayılmıştı). **`ACILIS_ZOOM_ORANI = 0.062`** — uydurma sayı değil, ölçülen
dağılımın kendi kovası; hook çekimi referans videolarda da güçlü hareketin
olduğu yerdir.

### Düzeltme (en küçük)

`zoomOrani`ye tek dallanma: `if (indeks === 0) return ACILIS_ZOOM_ORANI;`.
Kova tablosu, `2749 % 1000` aritmetiği ve **indeks 1…8 oranları bit-bit
aynı** (test kilitliyor: `[0.032, 0.014, 0.004, 0.062, 0.032, 0.014, 0.004,
0.062]`). Kullanıcının `zoom`/`pan` seçimleri ve 22 alan sözleşmesi
**dokunulmadı**.

⚠ **EŞİK GEVŞETİLMEDİ**: `OPTIK_DURGUN_ESIGI` 2.0, WARN 1.5 sn, FAIL 3.0 sn
aynen duruyor — test bunu ayrıca kilitliyor.

| Paket | A | B | C | D | E | F | G | H | I | Toplam |
|---|---|---|---|---|---|---|---|---|---|---|
| Zengin venv | 125 | 200 | 148 | 95 | 127 | 244 | 218 | 257 | **1818** | **3232** |

0 hata. Faz I 1806 → **1818** (+12). Red-first: 12 kontrolün **4'ü XX**.

### 1080p pilot — `vidrushvideo_acilis_i42.mp4`

I-41 pilotuyla **aynı şekil** (elma-elmaya). Medya/ses önbellekten, **$0.00**.

- **1920×1080 @ 30**, aac 48 kHz/2ch, 12.05 sn, 59.6 MB · **3 kesme** · **11 kare**
- LUFS **−14.13** / TP −4.45 · **sessizlik 0 aralık** · kenar siyahlığı **0/48**
- Künye (I-41) **çizilmeye devam ediyor**; künyesiz sahnede alan yok

**Açılış sahnesi — atomun iddiası, ölçülerek:**

| ölçüm | I-41 pilotu | I-42 pilotu |
|---|---|---|
| `s0` optik ortalama | **1.421** (fail) | **4.016** ✅ |
| `s0` en uzun durağan seri | **3.0 sn** | **0.0 sn** ✅ |
| genel optik ortalama | 3.971 | **4.762** |

⚠ **PİLOT DÜZENEĞİ DÜZELTİLDİ, ürün değil**: I-41 pilotundaki
`POST-SESSIZ-ORAN` (%16) ve `POST-LUFS` (−15.02) bulguları çıplak anlatım
dilimlerinden geliyordu. Üretim hattı ambiyans yatağı serer ve mastering
yapar; pilot da artık aynısını yapıyor → **sessizlik 0, LUFS −14.13**.
Hiçbir eşik/kapı değiştirilmedi.

⛔ **POST-QA: FAIL — kabul edilmiş MP4 DEĞİLDİR.** Kalan iki bulgu
**bu atomun kapsamı dışında bırakılan** sahnelerdir (talimat: yalnız açılış):

| bulgu | oran | durum |
|---|---|---|
| `POST-OPTIK-DURGUN` s1 | 0.032 "belirgin" | ort **1.915** < 2.0 |
| `POST-OPTIK-DURGUN` s2 | 0.014 "sakin" | ort **1.214**, durağan seri 3.0 sn |

Yani **kusur sınıfı açılışla sınırlı değil**: kalibrasyonda ölçüldüğü gibi
"sakin" kova bu görsel sınıfında eşiği **hiç** geçmiyor ve "belirgin" kova
bıçak sırtında. Bu, I-42'nin çözdüğü şeyin **daha büyük bir kusurun
en keskin ucu** olduğunu gösteriyor. Eşik gevşetilmedi, pilot geçsin diye
ayarlanmadı, mutlak yol verilmedi, deploy yok.

### SONRAKİ ATOM (I-43) — yalnız ölçülen kusurdan

1. **`ZOOM_KOVA` "sakin" (%1.4/sn) ve "belirgin" (%3.2/sn) kovaları da
   optik eşiği geçmiyor** (ölçüldü: 1.45 ve 2.005). Kovalar referans
   dağılımından geliyor ama optik ölçüm eşiği **editorv2 için** kalibre
   edilmişti. Doğru atom: iki tarafı **aynı ölçüm birimiyle** hizalamak —
   ya kovaları ölçülen eşiğe göre yeniden türet ya da `VidrushVideo` için
   eşiği **ölçerek** ayrı kalibre et. ⚠ Körlemesine eşik düşürmek YANLIŞ.
2. **Önizlemede altyazı hiç çizilmiyor** (I-40'ta ölçüldü).
3. **Medya seçiminde semantik doğrulama yok** (b001/b002/b005).

---

## 62. FAZ R-1d-a — TESLİM ATOMU: ZİNCİR UÇTAN UCA BAĞLANDI (14 Ağu)

> **Durum: ölçülen kusur ÇÖZÜLDÜ. A–I yeşil (4003, 0 hata).
> Ayrı bir güvenlik bulgusu (sızan imza anahtarı) de kapatıldı.
> Mac'te medya ÜRETİLMEDİ. Maliyet $0.00.**
> Değişen: yeni `webapp/teslim.py`; `webapp/server.py`, `webapp/imzali_url.py`,
> `webapp/is_sozlesme.py`, `.gitignore`, `webapp/testler/test_faz_{f,h,i}.py`.
> `pipeline.py`, `hizli_render.py`, `kaynak.py`, `editor/*`, `medya/*`,
> `kimlik.py`, `kutuphane.py`, `saglayici_motoru.py`, `deploy.sh`,
> `Video.tsx` ve **22 alan sözleşmesi** **DOKUNULMADI**.

### ⛔ ÖLÇÜLEN KUSUR — modüller vardı, TESLİM yoktu

R-1a (imzalı URL), R-1b (tenant provider zinciri), R-1c-a (zorunlu oturum)
ve R-1c-b (son-3 kütüphane) **yazılmıştı**, ama `server.py` **hiçbirini
import etmiyordu**. Ölçüldü (`grep`):

| iddia edilen halka | gerçekte | kanıt |
|---|---|---|
| zorunlu login/tenant guard | **YOK** | `/api/generate` → `gecerli_session()`, sadece `^[A-Za-z0-9_-]{1,64}$` regex'i |
| tenant korumalı signed URL | **YARIM** | `/ciktilar/` imzayı doğruluyor ama **tenant'a bakmıyor** → sızan link **her hesapta** çalışıyor |
| son-3 kütüphane | **HİÇ DOLMUYOR** | `kutuphane.py` hiçbir yerden çağrılmıyor |
| tenant provider kararı | **HİÇ ÇALIŞMIYOR** | `saglayici_motoru.py` hiçbir yerden çağrılmıyor |
| `/api/isler` izolasyonu | **TAHMİN EDİLEBİLİR** | yetki = iş id'sindeki `session[:6]` ön eki |

### Düzeltme — mevcut hat YENİDEN YAZILMADAN

Yeni `webapp/teslim.py`: **10 halkalı, kanıt temelli** zincir.

```
oturum → metin → plan → saglayici(R-1b) → uzak_tts_render
       → pre_qa → post_qa → depolama → imzali_url(R-1a) → kutuphane(R-1c-b)
```

⚠ **HER HALKA KANIT İSTER.** Kanıt işin **kendi kaydından** okunur;
yoksa `tamam=False` yazılır ve **teslim EDİLMEZ**. "Muhtemelen olmuştur"
denmez. Özellikle `depolama` halkası `dosya_var=None` iken **DEPOLAMA-ÖLÇÜLMEDİ**
sayılır — ölçülmemiş olan "var" **kabul edilmez**.

Teslim üç ayrı kapıdan geçer, üçü de fail-closed: zincir **tam** olacak,
`kutuphane.kabul_edilebilir_mi` **KABUL** diyecek (QA FAIL / ölçülmemiş
**girmez**), kayıt **bu tenant'a ait** olacak.

**`server.py` (en ince entegrasyon):** `/api/giris` `/api/cikis`
`/api/oturum` `/api/kutuphane` eklendi; `/api/generate` işi tenant'a **ve
sağlayıcı kararına** mühürlüyor; `/api/isler` ve `/api/job` **sahipliğe**
göre süzülüyor (`session` ön eki artık yetki DEĞİL); `/ciktilar/` imzayı
**oturumun tenant'ı ile** doğruluyor. Kuyruk/render/storage hattına
**dokunulmadı** — işçi yalnızca bitmiş işi `_teslim_et()` ile zincirden
geçiriyor.

⚠ **`/api/job` başka tenant'ta 404 döner (403 DEĞİL)**: iş kimlikleri
tahmin edilebilir zaman damgası taşıyor; 403 "bu iş var" bilgisini
sızdırırdı.

### Tenant'a bağlı imza — GERİYE UYUMLU

`imzali_url._imza()` artık opsiyonel `tenant` alıyor. ⚠ **Tenant boşken
mesaj eskisiyle BİT-BİT AYNI** (test kilitliyor) → R-1a bağlantıları
kırılmıyor. Tenant kimliği **URL'e yazılmaz** (link kimin olduğunu
sızdırmaz); sunucu onu **oturumdan** okur.

| senaryo | R-1a | R-1d-a |
|---|---|---|
| link sahibinin oturumunda | ✅ geçer | ✅ geçer |
| **link sızdı, başka hesapta** | **✅ geçerdi** ⛔ | **⛔ `IMZA-GECERSIZ`** |
| link sızdı, oturumsuz | ✅ geçerdi ⛔ | ⛔ 401 |

### ⚠ AYRI GÜVENLİK BULGUSU — imza anahtarı DEPOYA COMMIT EDİLMİŞ

`webapp/veri/.imza_anahtari` (64 bayt HMAC anahtarı) `4846264` (R-1a) ile
**depoya girmiş**. Modülün kendi sözleşmesi `anahtar_repoda: False` diyordu
ve bir test bunu iddia ediyordu — ama test **`webapp/.imza_anahtari`**
yolunu kontrol ediyordu, anahtar ise **`webapp/veri/.imza_anahtari`**'ydi.
Depoya erişen herkes **herhangi bir tenant adına** imza üretebilirdi.

**Ölçülen kapsam:** sunucuda (`185.23.17.240`) anahtar dosyası **YOK** —
R-1a hiç deploy edilmemişti. Yani **üretimde kullanılmadı**.
**Yapılan:** `git rm --cached` + yerel dosya silinip **döndürüldü** +
`.gitignore`'a anahtarlar/kimlik depoları eklendi + test artık **gerçek
yolu** (`git ls-files webapp/veri`) kontrol ediyor.
⚠ **Git geçmişinde değer hâlâ duruyor**; geçmiş yeniden yazılmadı (yıkıcı,
kapsam dışı) — anahtar döndürüldüğü için eski değer ÖLÜ.

### Testler — RED-FIRST kanıtı

| paket | A | B | C | D | E | F | G | H | I | Toplam |
|---|---|---|---|---|---|---|---|---|---|---|
| önce | 125 | 200 | 148 | 95 | 127 | 244 | 218 | 260 | 2521 | **3938** |
| sonra | 125 | 200 | 148 | 95 | 127 | 245 | 218 | 277 | 2568 | **4003** |

Red-first **ölçüldü**: R-1d-a üretim değişiklikleri geri alınıp aynı testler
koşuldu →

* `test_faz_h`: 277 → **203 geçti, blok komple ÖLDÜ**
  (`AttributeError: module 'server' has no attribute 'KULLANICI_DOSYA'`) —
  **74 kontrol koşamadı bile**.
* `test_faz_i`: `TypeError: imzala() got an unexpected keyword argument
  'tenant'` — tenant'a bağlı imza API'si **yoktu**.

⚠ **GEVŞETİLEN test YOK.** Üç test güncellendi ve **gerekçesi yazıldı**:
`test_faz_f` "generate imzası değişmedi" (yalnız `istek: Request` eklendi,
**22 Form alanı ayrıca sayılıyor**), `test_faz_h` uç taraması artık
**gerçek giriş** yapıyor (+ kimliksiz red kontrolleri), `test_faz_i` I-49
`webapp/veri/` ölçümü **yanlış pozitif** veriyordu (`.o**tur**um_anahtari`).

### SONRAKİ ATOM (R-1d-b) — yalnız ölçülen eksikten

1. **Arayüz giriş akışı asgari**: `/giris` tek dosyalık form; `app.js`
   401 alınca yönlendirmiyor, "Videolarım" kütüphane ucunu kullanmıyor.
2. **Silme kuyruğu İŞLENMİYOR**: tavanı aşan kayıt kuyruğa alınıyor ama
   dosyayı gerçekten silen remote lifecycle işi **YOK** → disk büyümeye
   devam eder.
3. **`saglayicilar.json` yazan bir uç yok**: provider registry okunuyor ama
   tenant bağlantısını **kuran** akış (gerçek OAuth) hâlâ yok — bu bilinçli.

---

## 63. HATA DÜZELTMESİ — `qa_on._ekle` TANIMSIZDI (R-1d-a deploy'unda yakalandı, 14 Ağu)

> **Durum: ölçülen kusur ÇÖZÜLDÜ. A–I yeşil. Mac'te medya ÜRETİLMEDİ. $0.00.**
> Değişen: `webapp/editor/qa_on.py` (**tek yardımcı fonksiyon eklendi**,
> çağrı yerleri DEĞİŞMEDİ), `webapp/testler/test_faz_c.py`.

### ⛔ Ölçülen kusur

`deploy.sh`in **pyflakes taraması deploy'u DURDURDU** (koruma çalıştı):

```
webapp/editor/qa_on.py:366,374,402,421,437: undefined name '_ekle'
```

K-1/K-2/K-3 atomları bulgularını `_ekle(...)` ile yazıyordu; ama o yardımcı
**yalnızca `_kalite_denetle()` içinde** (satır 574) tanımlıydı. Çağrılar ise
**`denetle()`** içindeydi (163–556). Yani şu dört kapı **bir ihlal bulunca
raporlamak yerine PRE-QA'yı çökertiyordu**:

`KALITE-BROLL-CESITLILIK` · `KALITE-BASLIK-SURESI` ·
`KALITE-KAYNAK-SES-SIZINTI` · `KALITE-SES-GURULTU`

⚠ **Neden hiçbir test yakalamadı**: kod yolu `if kalite_kapisi:` + **ihlal
listesi boş değil** koşuluna bağlı. Mevcut testler ya kapıyı kapalı
koşuyordu ya da temiz plan veriyordu → satırlar **hiç çalışmadı**. K-1/K-2/K-3
testleri yalnızca kodun `FAIL_KODLARI`'na kayıtlı olduğunu doğruluyordu.

### Düzeltme (en küçük)

`denetle()` içine `_kalite_denetle` ile **aynı imzada** yerel bir yardımcı:

```python
def _ekle(kod, seviye, detay, oneri, scene_id="", beat_id=""):
    q.ekle(Sorun(kod, seviye, scene_id, beat_id, detay, oneri))
```

**Beş çağrı yerinin hiçbiri değişmedi.** Eşik/kod/seviye **gevşetilmedi**.

### Red-first — ölçüldü

Düzeltme geri alınıp aynı testler koşuldu → **3 kontrol kırmızı**:
`NameError: name '_ekle' is not defined`, sızıntı raporu `[]` (boş),
pyflakes `undefined name '_ekle'`.

⚠ **Bu, R-1d-a teslim zinciri için de blokajdı**: `pre_qa` halkası kanıtını
`edit_plani.qa`'dan okuyor; PRE-QA çökerse halka **hiç kanıt üretmiyor** ve
hiçbir video teslim edilemiyordu.

---

## 64. R-1d-a — STAGING DEPLOY + SMOKE + 1080p ÖRNEK (14 Ağu)

> **Durum: deploy TAMAM, smoke TAM PASS. ⛔ Üretilen 1080p örnek
> KABUL EDİLMİŞ VİDEO DEĞİLDİR — teslim zinciri onu REDDETTİ
> (`ZINCIR-EKSIK:pre_qa`). Bu, atomun DOĞRU çalışmasıdır.**

### Hedef sunucu — ⚠ CLAUDE.md YANLIŞ

| şey | değer |
|---|---|
| canlı/staging | **`185.23.17.240`** (RX-4, 10 vCPU, 9.9 GB RAM, 107 GB boş) |
| CLAUDE.md'deki IP | `204.168.136.159` — **eski**, `deploy.sh` 1 Ağu'da taşımış |
| rollback etiketi | `bedosaho:rollback-20260814` **VAR** (13 gün, 2.08 GB) |
| ⚠ ek güvenlik etiketi | `bedosaho:pre-r1da-20260814` (deploy öncesi **9.52 GB** hâli) |
| ⚠ ek geri dönüş | `bedosaho_pre_r1da` konteyneri **duruyor** (durdurulmuş) |

⚠ `rollback-20260814` **2.08 GB**, çalışan imaj **9.52 GB** — o etikete
dönmek `node_modules`/Remotion'ı kaybettirebilir. **Gerçek geri dönüş
noktası `bedosaho:pre-r1da-20260814`**.

### Deploy sırasında çıkan İKİ ön koşul (kod dışı)

1. **`argon2-cffi` konteynerde YOKTU.** R-1c-a `Dockerfile`'a eklemişti ama
   `deploy.sh` yalnızca `.py` kopyalar, `pip install` yapmaz. Kurulmadan
   `kdf_hazir:false` → **hiç giriş yapılamaz** (fail-closed doğru çalıştı ve
   `/api/saglik`ta görünür oldu). Kuruldu + imaja basıldı.
2. **`EDITOR_V2=1` env, konteyner yeniden kurulmadan eklenemiyor.**
   Konteyner `--env-file /root/bedosaho.env` (0600) ile YENİDEN KURULDU;
   mevcut env AYNEN korundu, `EDITOR_V2=1` + `MEDYA_AVCISI=1` eklendi.
   Portlar/bind-mount'lar/restart politikası birebir aynı.

### ⚠ `COOKIE_SECURE` — ölçülen kurulum tavizi

Kurulum **düz HTTP** (IP, HTTPS yok). Ölçüldü: uzak adresten `/api/giris`
**200** dönüyor ama tarayıcı/istemci `Secure` çerezi **saklamıyor**, sonraki
`/api/kutuphane` **401** alıyor → zorunlu oturum açıkken uygulama
**kullanılamıyor**. `COOKIE_SECURE` env eklendi: **varsayılan AÇIK**,
staging'de `0`. Sessiz değil — `/api/saglik` `cookie_secure:false` diyor ve
başlangıçta uyarı basılıyor. **Kalıcı çözüm HTTPS'tir.**

### Smoke — **TAM PASS** (uzak adresten, 16/16)

kimliksiz `/api/isler` `/api/kutuphane` `/ciktilar/*` `/api/generate` → **401** ·
`/api/saglik` → 200 · anasayfa **giriş formu** · yanlış parola / olmayan
kullanıcı → **401** · doğru parola → **200** + tenant ·
çerezle korumalı uçlar → **200** · **başka tenant'a imzalanmış link → 403** ·
imza bozuk → 403 · kendi linki **oturumsuz → 401** · çıkış sonrası → **401**.

### 1080p örnek — ölçüldü

`job_1786710555280_r1dasm_82a7d8` · 8 sahne · üretim ~7 dk · `wikimedia`
sağlayıcı kararı (`BAGLANTI-YOK` — **gerçek OAuth/kredi yok**; Magnific
`Error consuming credits` verdi ve iş boyunca devre dışı kaldı).

**PASS (20):** 1920×1080 · h264 · **63.23 sn** (55–65 ✅) · aac 48 kHz ·
**LUFS −14.0** · **TP −1.5 dBTP** · **LRA 3.3** · sessiz oran **%0.0**
(projenin kendi tavanı %15) · ölü final **0.0 sn** · hiss (>9 kHz) ham
sinyalden **20.6 dB** düşük · **7 kesme** · siyah **0** · donmuş **0** ·
**12 kare** çıkarıldı, hiçbiri boş değil · POST-QA **WARN**, FAIL yok.

**FAIL (5):**

| bulgu | ölçüm |
|---|---|
| `pix_fmt` **yuv444p** | yuv420p değil — birçok oynatıcı/tarayıcı çözemez |
| rumble (<80 Hz) marjı | ham sinyalden **19.3 dB** düşük ⚠ eşik 20 dB **BENİM** koyduğum, projede kalibre EDİLMEMİŞ — sayı raporlanır, hüküm zayıf |
| olgu bağı | **4/8 sahne** doğrulanmış iddiaya bağlanamadı (eşik altı örtüşme) |
| **teslim** | `ZINCIR-EKSIK:pre_qa` → **teslim EDİLMEDİ** |
| kütüphane | 0 kayıt (teslim edilmeyen iş **girmez**) |

**ÖLÇÜLEMEDİ (9):** semantik uyum · tekrar/benzerlik · tipografi · ekran
künyesi · motion çeşitliliği · **gerçek video oranı** · **B-roll/cutaway** ·
**hook/J-L-cut/kapanış** · **aynı kaynak ≤ 8 sn**.

### ⛔ TEK SOMUT BLOKAJ — PRE-QA hiç koşmuyor

`EDITOR_V2=1` **ve** `MEDYA_AVCISI=1` açık, avcı bütçesi kuruldu
(`butce=$0.00 / 60 istek / 240 sn / 40 kare`) — ama `edit_plani.neden =
**MEDYA-YOK**`. Kök neden ölçüldü: **gerçek medya `kaynak.py` → Pexels
yolundan geliyor ve avcı bütçesini BESLEMİYOR**; `medya_kopru.manifest_kur()`
`butce.secimler()`den okuduğu için **sıfır aday** görüyor → PRE-QA denenmiyor
→ `pre_qa` halkasının **kanıtı yok** → zincir teslimi **reddediyor**.

Bu, handoff **§1'deki "iki paralel dünya"** kusurunun teslim sınırındaki
somut ölçümüdür. ⚠ **Eşik gevşetilmedi**: `pre_qa` halkasını zincirden
çıkarmak ya da POST-QA'ya indirgemek bu kusuru GİZLERDİ.

### SONRAKİ ATOM (R-1d-b) — yalnız ölçülen kusurdan

1. **`kaynak.py` seçimlerini avcı bütçesine yazmak** (ya da `manifest_kur`u
   gerçek seçim kaydından beslemek) → PRE-QA gerçekten koşar, 9 ölçüm
   ölçülebilir hale gelir, zincir tamamlanabilir.
2. **`pix_fmt` yuv420p**: render/mux çıktısı yuv444p veriyor.
3. **HTTPS**: `COOKIE_SECURE=1`e dönebilmek için.
4. **Silme kuyruğu işlenmiyor** (R-1c-b'den devrediyor).

---

## 65. FAZ R-1d-b — GERÇEK MEDYA YOLU AVCI BÜTÇESİNE BAĞLANDI (köprü, 14 Ağu)

> **Durum: R-1d-a'nın TEK SOMUT BLOKAJI kapatıldı. A–I yeşil.
> Mac'te medya ÜRETİLMEDİ. $0.00.**
> Değişen: `webapp/kaynak.py` (provenans kaydı + 4 kabul noktası),
> `webapp/medya_kopru.py` (`stok_secimi_kaydet` köprüsü),
> `webapp/pipeline.py` (**iki iç yardımcı + 4 çağrı**),
> `webapp/testler/test_faz_i.py`.
> `server.py`, `teslim.py`, `kimlik.py`, `kutuphane.py`, `imzali_url.py`,
> `editor/*`, `hizli_render.py`, `deploy.sh`, `Video.tsx` ve **22 alan
> sözleşmesi DOKUNULMADI**. Kuyruk/render/storage mimarisi **yeniden
> yazılmadı**.

### ⛔ Ölçülen kusur (R-1d-a staging pilotundan)

Üretimde medya `kaynak.py` → Pexels/Pixabay/Coverr/Freepik yolundan geliyor.
Ama:

1. **Stok sağlayıcıların hiçbiri provenans kaydetmiyordu.** `_ATIFLAR`
   YALNIZCA YouTube/CC yolunda doluyordu — bu yüzden pilotta `atiflar: []`.
   Sağlayıcı / asset / lisans / ölçü bilgisi **hiçbir yerde yoktu**.
2. **Seçim avcı bütçesine hiç yazılmıyordu.** `manifest_kur()` yalnızca
   `butce.secimler()`e bakar → manifest **boş** → `edit_kopru.plan_kur()`
   denenmiyor → **PRE-QA hiç koşmuyor** (`edit_plani = MEDYA-YOK`) →
   teslim zinciri `pre_qa` halkasını kanıtsız görüp videoyu **reddediyor**.
3. **Kapsam boşluğu YANLIŞ yazılıyordu**: avcı aday veremeyince hemen
   `bosluk_ekle` çağrılıyordu, oysa gerçek yol hemen ardından **lisanslı +
   kare doğrulanmış** bir klip getirebiliyordu.

### Düzeltme — en ince köprü

**`kaynak.py`**: `_STOK_PROVENANS` (atıftan **AYRI** — `atif_listesi()`
semantiği değişmedi) + `stok_provenans_kaydet/al`. Dört sağlayıcının da
**kare kapısını geçtikten SONRAKİ** kabul noktasına tek çağrı. Lisans
kimlikleri `STOK_LISANSLARI`'nda; lisans metni **yorumlanmıyor**, yalnızca
hangi lisans altında alındığı **kaydediliyor**.

**`medya_kopru.stok_secimi_kaydet()`**: provenansı `editor.plan`'ın beklediği
seçim kaydına çevirir. ⚠ **FAIL-CLOSED** — şu dördünden biri eksikse **kayıt
YAPILMAZ** ve neden kapsam boşluğu olarak yazılır: sağlayıcı yok · lisans
kimliği yok · **kare doğrulanmamış** · dosya diskte yok. `render_kullanilabilir`
yalnızca üçü de sağlandığında `True`. Seçimin `koken: "kaynak.py"` alanı
kökeni **gizlemez** (avcı zincirinden gelmiş gibi gösterilmez).

⚠ **ATIF UYDURULMUYOR**: bu stok lisansları atfı zorunlu kılmıyor →
`atif_metni: ""`, `atif_gerekli: False`, `eser_sahibi: ""`. CC/YouTube yolu
atfını `kaynak.atif_al()` üzerinden **aynen taşımaya devam ediyor**.

**`pipeline.py`**: `_sahne_medya()` içine iki küçük yardımcı — `_kopru_yaz()`
(footage başarısının **4 çıkışında** çağrılır) ve `_bosluk_yaz()`. Kapsam
boşluğu artık **footage yolundan çıkarken** (AI görsele düşerken) yazılıyor.

### Red-first — ölçüldü

| geri alınan | sonuç |
|---|---|
| köprünün tamamı | `AttributeError: module 'kaynak' has no attribute 'STOK_LISANSLARI'` — **API yoktu** |
| yalnız `pipeline.py` | **3 kontrol kırmızı** (köprü çağrısı yok, boşluk hâlâ erken yazılıyor, yedek yollar köprüsüz) |

⚠ **Gevşetilen eşik YOK.** Bir mevcut test düzeltildi ve **gerekçesi
yazıldı**: "iş başında bütçe sıfırlanıyor" kontrolü `def
klip_gecmisi_sifirla`'dan sonraki **sabit 600 karakteri** tarıyordu; tek satır
eklenince `kare_butce_kur()` **605.** karaktere kaydı ve kod DOĞRUYKEN test
kırmızı yandı. İddia "ilk 600 karakterde" değil "**bu fonksiyonun
gövdesinde**" — kapsam bir sonraki üst düzey `def`e kadar genişletildi.

### ⚠ R-1d-b PİLOTU — köprü çalıştı ama İKİ KUSUR DAHA ÖLÇÜLDÜ

İlk köprü pilotunda (`job_1786712620354_r1dasm_45f951`) log şunu dedi:

```
sahne 2/4/6/8: KOPRU -> butceye secim yazildi (pexels/pexels-license)
EDIT PLANI: QA=WARN render_edilebilir=True sahne=0
TESLIM ...: KABUL
```

Yani köprü **çalıştı** (manifest doldu, `plan_kur` denendi) ve teslim
zinciri **KABUL** verdi. Ama QA ölçümü bakınca:

**Kusur 1 — plan SIFIR çekim üretti (`sahne=0`).** Bütün PRE-QA ölçüm
sözlükleri **BOŞ** (`kapsam:{}`, `tipografi:{}`, `medya_turu:{}`,
`broll:{}`, `islev:{}`, `gecis:{}`, `ses:{}`, `kaynak_ses:{}`).
Kök neden ölçüldü: **sahneler `scene_id` TAŞIMIYORDU.**
`edit_kopru.plan_kur(cumleler=...)` her cümleye `scene_id: ""` veriyor,
medya manifesti ise `s001/s002...` taşıyor → `editor.plan` beat ile adayı
**eşleştiremiyor** → plan sıfır çekimle dönüyor.
**Düzeltme:** `props_sahneler`'e tek anahtar — `scene_id`, `_sahne_medya(n, s)`
ile **aynı `n`**den türer. Video.tsx bu alanı okumaz; 22 alan sözleşmesi
değişmedi.

**Kusur 2 — zincir İÇİ BOŞ bir PRE-QA hükmünü KANIT saydı.** `pre_qa`
halkası yalnızca `edit_plani.qa.durum in (PASS, WARN)` bakıyordu. Sıfır
çekim üzerinde üretilen "WARN" **vakumda** oluşmuştu ve zincir onu kanıt
sayıp videoyu **KABUL etti**. Bu, atomun kendi "kanıtsız halka geçmez"
sözleşmesinin **ihlaliydi**.
**Düzeltme (SIKILAŞTIRMA):** hüküm artık **yetmez** — plan en az **1 çekim**
kapsamalı **VE** PRE-QA gerçekten ölçüm yazmış olmalı. Aksi halde
`PRE-QA-BOS:sahne=..,olcum=..` ile **reddedilir**.

⚠ Bu bir eşik **gevşetmesi değil**, tam tersi: R-1d-a'nın kabul ettiği bir
durum artık **reddediliyor**. Red-first ölçüldü: `teslim.py` sıkılaştırması
geri alınınca 3 kontrol kırmızı; `pipeline.py` `scene_id` geri alınınca 1
kontrol kırmızı.

### R-1d-b PİLOT 2 — `sahne=0`'ın GERÇEK kök nedeni (sunucuda ölçüldü)

`scene_id` düzeltmesi **yetmedi**: ikinci pilotta plan yine `sahne=0` verdi.
Sunucuda `edit_kopru.plan_kur`'u **doğrudan** çağıran bir tanı koşuldu
(salt-okuma, medya yok) ve fark net çıktı:

| girdi | sonuç |
|---|---|
| tanıdaki cümleler (metin **DOLU**) | **10 çekim**, `medya_turu`/`broll` **ölçüldü**, QA=FAIL (`FACT-BAGLANTI-YOK`×4, `SAGLAYICI-TEKEL`) |
| üretimdeki cümleler (metin **BOŞ**) | **0 çekim**, tüm ölçümler boş, QA vakumda WARN |

**Kök neden:** `plan_kur(cumleler=...)` her cümlenin metnini
`x.get("anlatim")`'dan okuyor ama **`props_sahneler` bu alanı hiç
taşımıyordu** → her cümle boş metinle gidiyor → beat planı kurulamıyor →
sıfır çekim. **Düzeltme:** props'a `"anlatim": metin` (aynı döngüdeki
mevcut değişken). Video.tsx bu alanı okumaz.

**İkinci şema hatası (kendi kodumda):** sıkılaştırmayı yazarken ölçümü
`edit_plani.qa["olcumler"]` altında aramıştım. Oysa `edit_kopru.plan_kur`
QA'yı **özetliyor**: dönen sözlükte `olcumler` **anahtarı yok**, ölçümler
özetin **üst seviyesinde** (`medya_turu`, `broll_cesitliligi`). Yani DOLU
bir PRE-QA bile "boş" görünüyordu. Kontrol gerçek şemaya göre düzeltildi
(doğrudan `qa_on` çıktısı gelirse `olcumler` de sayılır).

### R-1d-b PİLOT 3 (son) — BLOKAJ KAPANDI, örnek KABUL EDİLMEDİ

`job_1786714318058_r1dasm_7baa9a` · 8 sahne · 5 sahne köprüden geçti
(`pexels/pexels-license`).

```
EDIT PLANI: QA=FAIL render_edilebilir=False  sahne=14
TESLIM ...: RED — ZINCIR-EKSIK:pre_qa
```

**Blokaj kapandı:** PRE-QA artık **gerçekten koşuyor** — 14 çekim,
`fail=4 warn=5`, ve ölçümler **gerçek** (B-roll çeşitliliği `olculdu: true`,
4 video çekim). Zincir **gerçek kanıta dayanarak** reddediyor.

**Teknik (PASS):** 1920×1080 · h264 · **57.88 sn** · aac 48 kHz ·
**LUFS −14.0** · **TP −1.5 dBTP** · **LRA 3.3** · sessiz oran **%0.0**
(tavan %15) · ölü final **0.0 sn** · hiss 21+ dB altta · **9 kesme** ·
siyah **0** · donmuş **0** · **12 kare**, hiçbiri boş değil ·
POST-QA **WARN**, FAIL yok · signed URL kendi oturumunda **200**,
oturumsuz **401**.

**Kalan FAIL'ler (gerçek bulgular):**

| bulgu | ölçüm |
|---|---|
| **PRE-QA FAIL** | `fail=4 warn=5` üzerinden 14 çekim |
| **B-roll çeşitliliği** | `video_islev_tur_tekrari`: b008 `aciklama/medium` (ilk 6), b009 `kanit/document` (ilk 3) |
| `pix_fmt` **yuv444p** | yuv420p değil — birçok oynatıcı çözemez |
| rumble marjı | 19.4 dB ⚠ 20 dB eşiği **BENİM**, projede kalibre DEĞİL |

**ÖLÇÜLEMEDİ (3):** gerçek video oranı (`KARE-OKUYUCU-YOK`) · kaynak sesi
sıfır · aynı kaynak ≤ 8 sn.
⚠ Kök neden: `edit_kopru.plan_kur` PRE-QA'yı **özetlerken** yalnızca
`durum/fail/warn/sorun_sayisi/medya_turu/broll_cesitliligi` taşıyor;
`kapsam`, `tipografi`, `gecis`, `ses`, `islev`, `kaynak_ses` ve sorun
KOD LİSTESİ **kayda geçmiyor**. Ölçülüyorlar ama iş kaydında yoklar.

### ⚠ KÜTÜPHANEDE HATALI KABUL EDİLMİŞ 1 KAYIT VAR

`job_1786712620354_r1dasm_45f951` (2. pilot) **içi boş PRE-QA kusuru
düzeltilmeden önce** kabul edilmişti (`sahne=0`, tüm ölçümler boş).
Sıkılaştırma sonrası aynı iş **reddedilirdi**. Kayıt hâlâ
`veri/kutuphane.json`'da duruyor ve `/api/kutuphane` onu **kabul edilmiş**
gösteriyor. **Silinmedi** — canlı veri, kararı sahibi versin.
Temizlik: o `is_id`'yi `veri/kutuphane.json`'dan düşürmek yeterli
(dosya silmeye gerek yok).

### SONRAKİ ATOM (R-1d-c) — yalnız ölçülen eksikten

1. **PRE-QA özeti ölçümleri kırpıyor**: sorun KOD listesi + `kapsam` /
   `tipografi` / `gecis` / `ses` / `islev` / `kaynak_ses` iş kaydına
   yazılmalı — aksi halde teslim raporu 6 kriteri **ölçemiyor**.
2. **`medya_turu` için kare okuyucu verilmiyor** (`KARE-OKUYUCU-YOK`) →
   **gerçek video oranı** hiç ölçülemiyor.
3. **B-roll çeşitliliği GERÇEKTEN ihlal ediliyor** (ölçüldü) — çekim türü
   ataması aynı işlevde tekrar ediyor.
4. **`pix_fmt` yuv444p**: mux çıktısı yuv420p olmalı.
5. Kütüphanedeki hatalı kabul kaydı (yukarıda).

---

## 66. FAZ R-1d-c — B-ROLL ÇEŞİTLENDİRMESİ + PRE-QA ÖZETİ KIRPILMIYOR (14 Ağu)

> **Durum: R-1d-b'nin bıraktığı iki teslim-kanıtı eksiği kapatıldı.
> A–I yeşil. Mac'te medya ÜRETİLMEDİ. $0.00.**
> Değişen: `webapp/editor/gramer.py` (**tek seçim satırı + 1 sayaç**),
> `webapp/edit_kopru.py` (QA özeti + `kaynak_kullanimi()`),
> `webapp/pipeline.py` (**1 iç yardımcı + 1 argüman**),
> `webapp/testler/test_faz_i.py`.
> `server.py`, `teslim.py`, `kimlik.py`, `kutuphane.py`, `imzali_url.py`,
> `kaynak.py`, `medya_kopru.py`, `deploy.sh`, `Video.tsx` ve **22 alan
> sözleşmesi DOKUNULMADI**. Kuyruk/render/storage **yeniden yazılmadı**.

### ⛔ Ölçülen kusur 1 — B-roll çeşitliliği (K-1 kapısının GERÇEK bulgusu)

57.88 sn'lik remote örnekte K-1 kapısı ihlal buldu:
`video_islev_tur_tekrari` → **b008 `aciklama/medium`** (ilk 6) ve
**b009 `kanit/document`** (ilk 3).

**Kök neden (`gramer.py:330`):**

```python
eslesen = next((t for t in tercihler
                if t in _amac_cekim(aday_amaci)), tercihler[0])
```

Aday `sahne_amaci` hiçbir tercihe uymayınca **daima `tercihler[0]`**
seçiliyordu → aynı işlevin **her** çekimi aynı türü alıyordu. Köprüden
gelen stok kayıtlarında `sahne_amaci` **boş** olduğu için bu yol **kural**
haline gelmişti. Red-first ölçüldü — düzeltme geri alınınca çıktı birebir:
`['medium','medium','medium','medium']` ve
`['document','document','document','document']`.

**Düzeltme (deterministik):** havuz **aynı** kalıyor (amaç eşleşiyorsa
eşleşenler, yoksa `ISLEV_CEKIM[islev]`); havuz **içinden** o işlevde **en az
kullanılmış** tür seçiliyor, eşitlikte **havuz sırası** belirliyor.
⚠ **Rastgelelik YOK** (test aynı girdi → aynı çıktı kilitliyor).
⚠ **İlk çekim eskisiyle AYNI** türü alıyor — gerileme yok; çeşitlenme
**ikinci** çekimde başlıyor.

### ⛔ Ölçülen kusur 2 — PRE-QA özeti ölçümleri KIRPIYORDU

`edit_kopru.plan_kur` yalnızca `durum/fail/warn/sorun_sayisi/medya_turu/
broll_cesitliligi` taşıyordu. `kapsam`, `tipografi`, `gecis`, `ses`,
`islev`, `kaynak_ses` ve **sorun KOD listesi** iş kaydına **hiç ulaşmıyordu**
→ teslim raporu **6 kriteri** "ÖLÇÜLEMEDİ" yazmak zorunda kalıyordu.

**Düzeltme:** özet artık hepsini taşıyor + **sorun kod listesi**
(kod/seviye/beat_id tam, detay 160 karakterde kırpılı, en çok 40 kayıt) +
`gercek_video_orani` (**`medya_turu`den OKUNUR**, yeniden hesaplanmaz) +
`kaynak_kullanimi`.

**Yeni ölçüm — `kaynak_kullanimi()`:** her varlığın **toplam** ekran süresi,
tavan (`8.0 sn`, ⚠ `saglayici_motoru.KAYNAK_BASINA_TAVAN_SN` ile **aynı
sabitten** okunur) ve **aşanlar**. ⚠ **HÜKÜM VERMEZ** — `fail`/`warn`
üretmez; R-1 teslim kanıtıdır, K mikro-kapısı değil. Çekim/beat sayısı
eşleşmezse **ölçüm yapılmaz** (`olculdu: False`), süre **tahmin edilmez**.

### ⛔ Ölçülen kusur 3 — gerçek video oranı hiç ölçülemiyordu

`medya_turu_ozeti` kare sayısını **dışarıdan** ister; `plan_kur`a okuyucu
verilmediği için ölçüm `KARE-OKUYUCU-YOK` ile duruyordu.
**Düzeltme:** `pipeline` artık **ffprobe tabanlı** bir kare okuyucu geçiyor.
⚠ **Ücretsiz ve yerel** — ağ/kredi yok. Okunamazsa **`None`** döner;
"statiktir" **DENMEZ**.

⚠ Depodaki `"kalite_kapisi" not in pipeline.py` kilidi **ham metin** tarıyor;
yorumda modül adını anmak bile testi kırmızı yakıyordu. Kilidin iddiası
(kod bağımlılığı yok) **doğru ve korundu** — yalnızca kendi yorumumu
token içermeyecek şekilde yazdım.

### R-1d-c PİLOTU — hedeflenen iki kusur KAPANDI, örnek KABUL EDİLMEDİ

`job_1786715884600_r1dasm_682d2c` · 8 sahne · **16 beat** · PRE-QA
`QA=FAIL sahne=16` → zincir **RED** (`ZINCIR-EKSIK:pre_qa`).

**Atomun hedefi — ikisi de ölçülerek kapandı:**

| hedef | önce (57.88 sn örneği) | şimdi |
|---|---|---|
| B-roll işlev/tür tekrarı | **2 ihlal** (b008, b009) | `video_islev_tur_tekrari: []` · `video_pencere_tur_tekrari: []` · `video_cekim_turu_cesidi: 4` ✅ |
| PRE-QA ölçümleri iş kaydında | **9 kriter ÖLÇÜLEMEDİ** | **ÖLÇÜLEMEDİ: 0** ✅ |

Artık iş kaydında **ölçülü** duruyor: `kapsam` · `tipografi {katman:1, sorun:0}` ·
`gecis {hard_cut_orani: 0.688}` · `ses` · `islev {hook:3, kanit:4, aciklama:8, sonuc:1}` ·
`kaynak_ses {politika: sifir, video_cekim: 4, ihlal: [], temiz: true}` ·
**`gercek_video_orani: 0.259`** · `kaynak_kullanimi {2 varlık, en uzun 8.052 sn}` ·
**sorun kodları** (`FACT-BAGLANTI-YOK`, `SAGLAYICI-TEKEL`, `SUREKLILIK-AYNI-CEKIM`,
`SUREKLILIK-AYNI-SAGLAYICI`).

**Teknik PASS:** 1920×1080 · h264 · **57.98 sn** · aac 48 kHz ·
**LUFS −14.0** · **TP −1.4 dBTP** · **LRA 3.7** · sessiz oran **%0.0** ·
ölü final 0.0 sn · hiss 21.0 dB altta · **19 kesme** · siyah **0** ·
donmuş **0** · **12 kare** · POST-QA **WARN**, FAIL yok ·
signed URL: kendi oturumu **200** / oturumsuz **401** / **başka tenant 403**.

**FAIL (9):** PRE-QA FAIL · **medya kapsam oranı 0.25** · J/L-cut
(`ducking_araligi: 0`) · **aynı kaynak 8.052 sn > 8.0** · olgu bağı 4/8 ·
`pix_fmt` yuv444p · rumble 19.5 dB (⚠ eşik benim, kalibre değil) ·
teslim RED · kütüphanede yok.

### ⛔ SONRAKİ TEK GERÇEK BLOKAJ — beat sayısı ile aday sayısı uyuşmuyor

```
kapsam: {"cekim": 16, "medya": 4, "fallback": 12, "kapsam_orani": 0.25}
```

Plan **8 cümleden 16 beat** üretiyor, köprü ise **sahne başına 1 aday**
yazıyor (5 aday). Beatlerin **%75'i medyasız** kalıp `fallback`e düşüyor.
Kalan FAIL'lerin **çoğu bunun türevi**:

* `gercek_video_orani 0.259` — yalnızca 4 video çekim var
* `SAGLAYICI-TEKEL %100` — 4 çekimin hepsi tek sağlayıcıdan
* `SUREKLILIK-AYNI-CEKIM` ×2 — aynı varlık tekrar tekrar kullanılıyor
* **`aynı kaynak 8.052 sn > 8.0`** — 2 varlık 16 beat'e yayıldığı için
* `FACT-BAGLANTI-YOK` ×4

⚠ Bunu "eşik gevşeterek" kapatmak YANLIŞ olur: kapsam oranı gerçekten
%25. Doğru atom **beat başına aday üretmek** — ya köprü sahne başına
birden çok aday yazmalı, ya plan beat sayısını gerçek aday sayısına göre
türetmeli.

---

## 67. FAZ R-1d-d — `kapsam_orani: 0.25` KÖK NEDENİ (14 Ağu)

> **Durum: kök neden ÜÇ bileşene ayrıştırıldı ve üçü de kapatıldı.
> A–I yeşil. Eşik GEVŞETİLMEDİ (biri SIKILAŞTIRMA).
> Mac'te medya ÜRETİLMEDİ. $0.00.**
> Değişen: `webapp/editor/gramer.py`, `webapp/editor/plan.py`,
> `webapp/editor/kalite_kapisi.py` (1 sabit), `webapp/kaynak.py`,
> `webapp/pipeline.py`, `webapp/testler/test_faz_i.py`.
> `server.py`, `teslim.py`, `kimlik.py`, `kutuphane.py`, `imzali_url.py`,
> `medya_kopru.py`, `edit_kopru.py`, `deploy.sh`, `Video.tsx` ve **22 alan
> sözleşmesi DOKUNULMADI**.

### ⛔ Ölçülen kusur — üç bileşen

`job_1786715884600`: `kapsam {cekim:16, medya:4, fallback:12,
kapsam_orani:0.25}` · `kaynak_kullanimi` **en uzun 8.052 sn > 8.0**.

**(1) Sağlayıcı kotası tek sağlayıcıda DEJENERE.** Kota (varsayılan **4**)
*çeşitlilik* içindir: "tek sağlayıcı planı ele geçirmesin". Manifestte
**tek** sağlayıcı varsa kota çeşitlilik **sağlayamaz** — yalnızca 4'üncü
çekimden sonrasını **garantili fallback**'e iter. Ölçüldü: 16 beat'in **tam
4'ü** medya aldı. ⚠ `edit_kopru` I-22 notu bu tuzağı **zaten yazmıştı**
("çağıran taraf tavanı planın gerçek beat sayısıyla eşleştirebilir").

**(2) Kaynak tavanı yalnızca SONRADAN ölçülüyordu.** Seçim tavanı
bilmiyordu → **8.052 sn ihlali oluşabiliyordu**.

**(3) Üretilen AI görselleri hiçbir adaya bağlanmıyordu** → o sahnelerin
beat'leri **garantili fallback**.

### Düzeltmeler

**(1) `plan.uret`:** manifestte **tek** sağlayıcı varsa ve kota beat
sayısından küçükse, kota beat sayısına çıkarılır — **gerekçesi yazılı**
(`TEK-SAGLAYICI`).
⚠ **Bu bir eşik gevşetmesi DEĞİLDİR:** çok sağlayıcılı manifestte koşul
sağlanmaz, davranış **bit-bit aynı** (test kilitliyor); tek sağlayıcı
durumu **gizlenmiyor** — `SAGLAYICI-TEKEL` kapısı **aynı %40 eşiğiyle**
ölçmeye ve uyarmaya devam ediyor (test bunu da kilitliyor).

**(2) `gramer._varlik_sec` — SIKILAŞTIRMA:** aynı kaynak tavanı artık
**seçim anında** uygulanıyor; tavanı aşacak aday havuzdan **elenir**. Kapı
raporla değil **inşa ile** sağlanıyor. Tavan `saglayici_motoru` ile **aynı
tek kaynaktan** okunuyor. Tavan `0` verilirse davranış eskisiyle **aynı**.

**(3) `kaynak.stok_provenans_isaretle()` + `pipeline`:** üretilen görsel de
köprüye yazılıyor. ⚠ **UYDURMA YOK** — `medya_turu: "image"` (video
**DENMEZ**, `gercek_video_orani` şişirilmez), `lisans: "uretilmis-eser"`,
gerçek model adı. İşaretlenmeden köprüden **geçemez** (`LISANS-YOK`).

⚠ **Ek düzeltme:** köprü yardımcıları footage bloğunun **içinde**
tanımlıydı; üretilen görsel yolu o bloğun **dışında** olduğu için
non-footage sahne **`NameError`** alırdı. Yardımcılar fonksiyon başına
alındı ve `footage_sorgu` yokken de güvenli hale getirildi.

### Red-first — dört bileşen ayrı ayrı ölçüldü

| geri alınan | sonuç |
|---|---|
| `editor/plan.py` | **4 kırmızı**; kapsam `{medya:4, fallback:4, oran:0.5}` |
| `pipeline.py` | **6 kırmızı** |
| `editor/gramer.py` | test **çöktü** (`KeyError: 'durum'` — plan üretilemiyor) |
| `kaynak.py` | **`AttributeError: stok_provenans_isaretle`** — API yoktu |

### R-1d-d PİLOTU — iki hedef ölçülerek kapandı, örnek KABUL EDİLMEDİ

`job_1786717796777_r1dasm_9f1dda` · **8/8 sahne köprüden geçti**
(5 `pexels/pexels-license` + 3 `openai/uretilmis-eser`).

| ölçüm | R-1d-c pilotu | R-1d-d pilotu |
|---|---|---|
| `kapsam_orani` | **0.25** (medya 4) | **0.50** (medya **8**) ⬆ |
| aynı kaynak ≤ 8.0 sn | ⛔ **8.052 sn İHLAL** | ✅ **PASS** — en uzun **7.716 sn**, **5 varlık** |
| sağlayıcı çeşitliliği | tek (`pexels` %100) | **iki** (`pexels` %38.7 + `openai`) |
| B-roll işlev/tür tekrarı | `[]` | `[]` (korundu) |
| `kaynak_ses` | `sifir`, ihlal `[]` | `sifir`, ihlal `[]` (korundu) |

**Teknik PASS:** 1920×1080 · h264 · **63.74 sn** · aac 48 kHz ·
**LUFS −14.0** · **TP −1.5 dBTP** · **LRA 3.2** · sessiz oran **%0.0** ·
ölü final 0.0 sn · hiss 20.6 dB altta · **8 kesme** · siyah 0 · donmuş 0 ·
**12 kare** · POST-QA **WARN** (FAIL yok).
**Semantik PASS:** tipografi · künye/atıf · motion · geçiş `hard_cut 0.688` ·
hook `{hook:4, kanit:3, aciklama:8, sonuc:1}` · kapanış · tekrar/benzerlik.
**Signed URL:** kendi oturumu **200** · oturumsuz **401** · **başka tenant 403**.

**FAIL (8):** PRE-QA FAIL · kapsam 0.5 · J/L-cut `ducking_araligi: 0` ·
olgu bağı 5/8 · `pix_fmt` yuv444p · rumble 18.4 dB (⚠ eşik benim, kalibre
değil) · teslim RED · kütüphanede yok.

### ⛔ SONRAKİ TEK GERÇEK BLOKAJ — beat sayısı aday sayısının İKİ KATI

```
kapsam: {"cekim": 16, "medya": 8, "fallback": 8, "kapsam_orani": 0.5}
PRE-QA: SHOT-TAVAN: b011 8.075 sn (tavan 8.0)
```

Plan **8 cümleden 16 beat** üretiyor; köprü **sahne başına 1 aday** yazıyor
→ **8 aday / 16 beat**. Her sahnenin tek varlığı ilk beat'ini alıyor,
**ikinci beat zorunlu fallback** oluyor. Kalan `kapsam 0.5` tam olarak bu.

⚠ İkinci beat'in varlığı **tekrar kullanması** artık `≤8 sn` tavanı
tarafından **doğru şekilde** engelleniyor — yani bu, R-1d-d'nin
sıkılaştırmasının **beklenen** sonucu, gerileme değil.

⚠ Ayrıca **yapısal çelişki ölçüldü**: `b011` tek başına **8.075 sn** —
kaynak tavanının (**8.0 sn**) üstünde. Böyle bir beat **hiçbir** varlık
alamaz (ve `SHOT-TAVAN` kapısı da onu ayrıca fail ediyor).

**Doğru atom (R-1d-e):** ya köprü **sahne başına ≥2 gerçek aday** üretsin
(sağlayıcıdan ikinci klip), ya da **beat süreleri/sayısı** mevcut aday
sayısı ve `≤8 sn` tavanıyla **uyumlu türetilsin**. ⚠ Eşik gevşetmek
YANLIŞ olur: kapsam gerçekten %50 ve `b011` gerçekten tavanın üstünde.

---

## 68. FAZ R-1d-e — PRE-QA KANITI **RENDER EDİLEN** ZAMAN ÇİZGİSİNDEN (14 Ağu)

> **Durum: R-1d-e istenen biçimde DEĞİL, ölçülen gerçek blokaja göre
> kuruldu (kullanıcı onayıyla). A–I yeşil. Mac'te medya ÜRETİLMEDİ. $0.00.**
> Değişen: yeni `webapp/gercek_qa.py`; `webapp/pipeline.py`,
> `webapp/teslim.py`, `webapp/testler/test_faz_i.py`.
> `server.py`, `kimlik.py`, `kutuphane.py`, `imzali_url.py`, `kaynak.py`,
> `medya_kopru.py`, `edit_kopru.py`, `editor/*`, `hizli_render.py`,
> `deploy.sh`, `Video.tsx` ve **22 alan sözleşmesi DOKUNULMADI**.

### ⛔ Ölçülen kusur — PRE-QA render EDİLMEYEN bir planı ölçüyordu

`uret()` içindeki **sıra ölçüldü**:

| satır | ne olur |
|---|---|
| **4655** | `hizli_render.ffmpeg_render(is_adi, props, ...)` — **video BURADA render edilir** |
| 4787 | `sonuc = {...}` |
| **4822** | editorv2 plan bloğu — **PRE-QA BURADA koşar** |

Kodun kendi yorumu: *"⚠ Bu blok RENDER ETMEZ … gerçek render mevcut
`VidrushVideo` yoluyla ZATEN yapıldı."* Doğrulandı: `_ep["props"]` yalnızca
`len(...)` için kullanılıyor; `VidrushEditorV2` kompozisyonu **hiç
çağrılmıyor**; `render_edilebilir: False`.

İki artefakt **ölçümle** ayrıştı (`job_1786717796777`):

| | teslim edilen MP4 | PRE-QA'nın ölçtüğü plan |
|---|---|---|
| çekim | **8 sahne** | **16 çekim** |
| kesme | **8** (POST-QA, gerçek dosyada) | — |
| kapsam | — | `{medya:8, fallback:8, oran:0.5}` |

**Sonuç:** teslim zincirinin `pre_qa` halkası **teslim edilen videoya ait
OLMAYAN** bir kanıt taşıyordu. O plandaki `kapsam_orani`'nı yükseltmek MP4'ü
iyileştirmez; halkayı PASS'a döndürmek **yanlış bir kabul sinyali** üretirdi.
Bu, R-1d-a'da kapatılan "içi boş PRE-QA" kusurunun **daha derin** biçimi.

⚠ **Bu yüzden istenen R-1d-e (8/16 kapsam + `b011=8.075 sn`) YAPILMADI**:
o semptomlar **teslim edilen videoda yok**. Kullanıcı, kanıtı gerçek zaman
çizgisine bağlama seçeneğini onayladı.

### Düzeltme — `webapp/gercek_qa.py`

`props_sahneler` (**render EDİLEN** sahneler) → ölçüm sözleşmesi → **mevcut**
ölçüm modülleri (`editor.kalite_kapisi`, `editor.ses_gurultu`).
⚠ **Ölçüm modülleri değişmedi**; değişen tek şey **girdi** ve **zamanlama**
(artık render'dan **önce** koşuyor).

Ölçülen kapılar (hepsi **gerçek** timeline'dan): `kapsam` · `medya_turu` /
**gerçek video oranı** · **`kaynak_ses = sifir`** · **aynı kaynak ≤ 8.0 sn**
(tavan `saglayici_motoru` ile aynı sabitten) · **`SAGLAYICI-TEKEL`** (aynı
%40 eşiği) · **`SUREKLILIK-AYNI-CEKIM`** · **`FACT-BAGLANTI-YOK`**.

⚠ **UYDURMA YOK — türetilemeyen ölçüm ÜRETİLMEZ.** Gerçek hat sahneye
`cekim_turu` **atamaz** (onun yerine `zoom`/`pan` kararları var). Bu yüzden
çekim türü tabanlı B-roll görsel dili ölçümü bu zaman çizgisinde
**uygulanamaz** ve **stabil kodla** bildirilir:
**`GERCEK-TIMELINE-CEKIM-TURU-YOK`**. Sahte çekim türü **yazılmaz**
(test her sahnenin `cekim_turu == ""` olduğunu kilitliyor).
Diğer stabil kodlar: `GERCEK-TIMELINE-PROVENANS-YOK`,
`GERCEK-TIMELINE-SAHNE-YOK`.

**Deterministik politika:** provenansı **olmayan** sahne `medya` **sayılmaz**
(fallback); hiç medya yoksa `GERCEK-KAPSAM-YOK` **fail**; ölçüm patlarsa
durum **`OLCULEMEDI`** — "PASS" **denmez**.

**`teslim.py`:** `pre_qa` kanıtı artık `render_qa`'dan okunuyor; `edit_plani`
**kanıt sayılmıyor** (kayıtta bilgi olarak kalıyor).

⚠ **Ek düzeltme:** `_kare_sayisi_oku` yalnızca editorv2 bloğunda tanımlıydı;
render-QA'nın onu kullanabilmesi için **render öncesine** alındı.

### Red-first — üç bileşen ayrı ölçüldü

| geri alınan | sonuç |
|---|---|
| `gercek_qa.py` | `ModuleNotFoundError: No module named 'gercek_qa'` |
| `teslim.py` | **4+ kırmızı** (zincir hâlâ `edit_plani` arıyor) |
| `pipeline.py` | **1 kırmızı** (ölçüm render öncesinde koşmuyor) |

### R-1d-e PİLOTU — gerçek timeline ölçüldü + PERSİSTANS KUSURU bulundu

`job_1786719801861_r1dasm_32d4e2` logu:

```
RENDER-QA (gercek timeline): FAIL sahne=8 kapsam=1.0 gercek_video=0.5135
TESLIM ...: RED — ZINCIR-EKSIK:pre_qa
```

**Atomun iddiası doğrulandı** — gerçek zaman çizgisinde plandaki iki semptom
**yok**:

| ölçüm | editorv2 planı | **gerçek timeline** |
|---|---|---|
| çekim | 16 | **8** |
| `kapsam_orani` | 0.5 | **1.0** ✅ |
| gerçek video oranı | 0.259 | **0.5135** ✅ |

⚠ **Ama iş kaydında `render_qa` BOŞ çıktı.** Kök neden: `server.py`
`_bir_is` içindeki `d.update({...})` anahtarları **açıkça listelidir** ve
`render_qa` listeye **girmemişti** → ölçüm üretiliyor ama kayda hiç
ulaşmıyor → zincir `pre_qa` halkasını kanıtsız görüp **her** videoyu
reddediyordu. (Daha önce avcı özetinde yaşanan kusurun **aynı sınıfı**.)
Düzeltildi; red-first testle kilitlendi.

### R-1d-e PİLOT 2 — zincir İLK KEZ KABUL etti, ama TAM PASS DEĞİL

`job_1786720519626_r1dasm_def821` · 8 sahne · **57.05 sn**.

```
RENDER-QA (gercek timeline): WARN  fail=0 warn=5  sahne=8
TESLIM ...: KABUL          teslim=true, kutuphane 2 kayit
```

**Atomun ALTI kapısı da gerçek ölçümle korundu:**

| kapı | gerçek timeline ölçümü |
|---|---|
| `kapsam_orani` | **0.875** (7 medya / 1 fallback) ✅ |
| **gerçek video oranı** | **0.4899** (`video:4, donmus:3, sentetik:1`) ✅ |
| **`kaynak_ses = sifir`** | `olculdu: true`, **ihlal `[]`** ✅ |
| **aynı kaynak ≤ 8.0 sn** | **7 varlık**, en uzun **7.572 sn**, `asan: []` ✅ |
| `SAGLAYICI-TEKEL` | **warn %56** (tavan %40) — gizlenmiyor ✅ |
| `SUREKLILIK-AYNI-CEKIM` | ihlal **yok** ✅ |
| `FACT-BAGLANTI-YOK` | **4 warn** — ölçülüyor ✅ |

**Teknik PASS:** 1920×1080 · h264 · **57.05 sn** · aac 48 kHz ·
**LUFS −14.0** · **TP −1.4 dBTP** · **LRA 3.9** · sessiz oran **%0.0** ·
ölü final 0.0 sn · hiss 21.0 dB altta · 5 kesme · siyah 0 · donmuş 0 ·
12 kare · POST-QA WARN (FAIL yok).
**Signed URL:** kendi oturumu **200** · oturumsuz **401** · **başka tenant 403**.

⛔ **TAM PASS DEĞİL — kabul edilmiş video DENMEZ.** Kalan 5 FAIL + 1 ölçülemedi.

### ⛔ SONRAKİ TEK GERÇEK BLOKAJ — teslim edilen MP4 `yuv444p`

```
ffprobe: 1920x1080 h264  pix_fmt = yuv444p     (yuv420p DEĞİL)
hizli_render.py:695  ... + ",format=yuv420p"
hizli_render.py:753  vf += ",format=yuv420p"
```

`hizli_render` **segment** filtre zincirlerinde `format=yuv420p` **var**, ama
**nihai çıktı `yuv444p`** — yani son birleştirme/encode adımı piksel
formatını **korumuyor**. Sonuç: teslim edilen MP4 birçok oynatıcı/tarayıcıda
**çözülemez** (H.264 High 4:4:4 profili yaygın desteklenmez). Bu, teslim
edilen artefaktta **ölçülen, kullanıcıya dokunan** tek gerçek blokaj.

**Diğer kalanlar (blokaj değil, kayıt için):** rumble marjı 17.7 dB
(⚠ 20 dB eşiği **benim**, projede kalibre **değil** — hüküm zayıf) ·
olgu bağı 4/8 · `geçiş hard_cut_orani` ve `J/L-cut ducking` **gerçek zaman
çizgisinde ölçülmüyor** (R-1d-e'nin ölçüm kapsamı dışında kaldı) ·
`B-roll` **`GERCEK-TIMELINE-CEKIM-TURU-YOK`** (gerçek hat çekim türü
atamıyor — uydurulmadı).

⚠ Kütüphanede artık **2 kayıt** var: bu kabul + **R-1d-b'deki hatalı kabul**
(`job_1786712620354`). Eski kayda **dokunulmadı** (talimat).

---

## 69. FAZ R-1d-f — TESLİM EDİLEN MP4 DETERMİNİSTİK `yuv420p` (14 Ağu)

> **Durum: küçük atom, ölçülen blokaj kapatıldı. A–I yeşil.
> Mac'te medya/QA artefaktı ÜRETİLMEDİ (geçici dizin dahil). $0.00.**
> Değişen: `webapp/hizli_render.py`, `webapp/testler/test_faz_i.py`.
> Başka hiçbir dosyaya dokunulmadı.

### ⛔ Ölçülen kusur

R-1d-e pilotu (`job_1786720519626`): teslim edilen MP4 `ffprobe` ile
**`pix_fmt = yuv444p`**. H.264 High 4:4:4 profili yaygın desteklenmediği için
video birçok oynatıcı/tarayıcıda **çözülemiyordu**.

**Kök neden:** `format=yuv420p` yalnızca **segment** filtre zincirlerindeydi
(satır ~695, ~753). **Nihai** iki encode — `_xfade_zincir` (birleştirme) ve
altyazı gömme — `-pix_fmt` **vermiyordu**; `xfade` filtresi formatı 4:4:4'e
**yükseltiyor** ve son encode onu aynen yazıyordu.

### Düzeltme

1. **Her nihai encode formatı AÇIKÇA veriyor** — `-pix_fmt yuv420p`
   (birleştirme + altyazı gömme). Sabit: `TESLIM_PIX_FMT`.
2. **Teslim sınırında GERÇEK ffprobe doğrulaması** — `_teslim_kapisi()`
   nihai dosyayı ölçer. ⚠ **Segment filtresine GÜVENİLMEZ.**
3. **Stabil hata kodu:** `RENDER-PIX-FMT-YANLIS`.
   **FAIL-CLOSED:** format yanlış **ya da ölçülemiyorsa** hızlı motor
   çıktısı **teslim edilmez** (`False` → hat Remotion'a düşer). Çözülemeyen
   bir MP4 teslim edilmektense render yolu değişir.
4. `pix_fmt_oku(..., kosucu=...)` — okuyucu **enjekte edilebilir** (repo
   deseni), böylece kapı **medyasız** test edilir.

⚠ **Ek üretim düzeltmesi:** bazı ffprobe sürümleri `csv=p=0` ile **ardıl
virgül** bırakıyor; kırpma virgülün **iki yanını** da temizliyor (testte
yakalandı).

### Red-first + MEDYASIZ test

⚠ Kullanıcı talimatı gereği **Mac'te hiçbir medya üretilmedi** — geçici
dizin dahil. Test iki eksende **medyasız**:
* **Komut sözleşmesi**: `pix_fmt_komutu()` doğrudan çağrılır (çalıştırılmaz).
* **Karar mantığı**: **mock ffprobe** çıktısı enjekte edilir —
  `yuv444p` → **RED** (`FORMAT-YANLIS`), `yuv420p` → geçer,
  boş/exception → **`OLCULEMEDI`**, `yuv420p10le` → **RED** (tam eşitlik).

Gerçek `ffprobe` doğrulaması **yalnızca remote worker pilotunda** koşar.

Red-first ölçüldü: düzeltme geri alınınca
**`AttributeError: module 'hizli_render' has no attribute 'TESLIM_PIX_FMT'`**.

### R-1d-f PİLOTU — `yuv420p` DOĞRULANDI, örnek yine KABUL EDİLMEDİ

`job_1786721869701_r1dasm_843bd1` · 8 sahne · **61.63 sn**.

| ölçüm | R-1d-e pilotu | **R-1d-f pilotu** |
|---|---|---|
| **`pix_fmt`** | ⛔ **`yuv444p`** | ✅ **`yuv420p`** |

**Teknik PASS:** 1920×1080 · h264 · **`yuv420p`** · **61.63 sn** · aac 48 kHz ·
12 kare · siyah 0 · donmuş 0 · POST-QA **WARN** (FAIL yok).
**Gerçek-timeline PASS:** `kapsam_orani` **1.0** (8 medya / 0 fallback) ·
gerçek video oranı **0.4979** · `kaynak_ses` ihlal **[]** ·
tipografi/künye/motion/semantik FAIL yok.
**Signed URL:** kendi oturumu **200** · oturumsuz **401** · **başka tenant 403**.

⛔ **TAM PASS DEĞİL — kabul edilmiş video DENMEZ.** RENDER-QA **FAIL** (4 fail).

### ⛔ SONRAKİ TEK GERÇEK BLOKAJ — sahne süresi kaynak tavanını aşıyor

```
GERCEK-KAYNAK-TAVANI: 36560908  8.508 sn   (tavan 8.0)
GERCEK-KAYNAK-TAVANI: ..._s001  8.124 sn
GERCEK-KAYNAK-TAVANI: 38614588  8.052 sn
GERCEK-KAYNAK-TAVANI: 15924008  8.028 sn
```

Gerçek hatta **1 sahne = 1 varlık**. Bir sahne **8.0 sn'yi aşarsa** o varlık
**tek başına** kaynak tavanını aşar; başka çare yoktur. Bu iş: 61.63 sn / 8
sahne ≈ **7.7 sn ortalama**, ama 4 sahne 8.0'ın üstünde.

⚠ **Kabul bu yüzden SÜREYE BAĞLI ve KARARSIZ**: R-1d-e pilotunda sahneler
7.1–7.6 sn olduğu için **kabul edilmişti**; bu işte 8.0'ı aşınca reddedildi.
Aynı ürün, aynı kapı, farklı sonuç — **plan sahne süresini tavana göre
sınırlamıyor**.

**Doğru atom (R-1d-g):** sahne/beat süresi üretilirken `KAYNAK_BASINA_TAVAN_SN`
(8.0) **üst sınır olarak uygulansın** (aşan sahne bölünsün), ya da bir sahne
**≥2 varlıkla** kaplansın. ⚠ Tavanı yükseltmek **YANLIŞ** olur: J-5b
kullanıcı şartı ve `saglayici_motoru` ile aynı tek sabit.

**Diğer kalanlar (blokaj değil):** rumble 18.1 dB (⚠ eşik **benim**, kalibre
değil) · olgu bağı 4/8 · `geçiş hard_cut` ve `J/L-cut ducking` gerçek zaman
çizgisinde **ölçülmüyor** · B-roll `GERCEK-TIMELINE-CEKIM-TURU-YOK`.

---

## 70. FAZ R-1d-g — AYNI KAYNAK ≤ 8.0 sn DETERMİNİSTİK PLAN (14 Ağu)

> **Durum: KARAR MANTIĞI tamamlandı ve kilitlendi; UYGULAMA (ses bölme +
> ikinci varlık çekimi) HENÜZ BAĞLANMADI. A–I yeşil.
> Mac'te medya/QA artefaktı ÜRETİLMEDİ. $0.00.**
> Değişen: yeni `webapp/kaynak_tavani.py`, `webapp/testler/test_faz_i.py`.
> Başka hiçbir üretim dosyasına dokunulmadı.

### ⛔ Ölçülen kusur

R-1d-f pilotu (`job_1786721869701`):

```
GERCEK-KAYNAK-TAVANI: 36560908  8.508 sn   (tavan 8.0)
                      ..._s001  8.124 sn
                      38614588  8.052 sn
                      15924008  8.028 sn
```

Gerçek hatta **1 sahne = 1 varlık**. Sahne 8.0 sn'yi aşarsa varlık **tek
başına** tavanı aşar. ⚠ Kabul bu yüzden **süreye bağlı ve kararsızdı**:
R-1d-e pilotunda sahneler 7.1–7.6 sn olduğu için **aynı ürün kabul
edilmişti**.

### Yapılan — `webapp/kaynak_tavani.py` (saf karar mantığı)

Deterministik politika, **rastgelelik yok**:
1. Tavanı **aşmayan** sahne **bölünmez** (davranış aynen korunur; `8.0` → 1).
2. Aşan sahne `ceil(sure/tavan)` **eşit** parçaya bölünür (`8.001` → 2).
3. Her parçaya **farklı** varlık; toplamı tavanı aşacak varlık **atanmaz**.
4. Aday sırası verilen sırayla taranır → **aynı girdi aynı çıktı**.
5. Yeterli farklı varlık yoksa parça **atanmaz** ve **stabil kod**:
   **`KAYNAK-TAVANI-VARLIK-YOK`**. ⚠ Aynı kaynağı tekrar kullanıp toplamı
   **aşmaz**, tavanı **yükseltmez** — FAIL-CLOSED.
   Bozuk süre: **`KAYNAK-TAVANI-SURE-BOZUK`**.

⚠ Tavan `medya.saglayici_motoru` ile **aynı tek sabitten** okunur.
⚠ Lisansı/sağlayıcısı olmayan aday havuzdan **elenir**.

**Pilotun gerçek sayılarıyla doğrulandı:** dört ihlalin dördü de plana
uyuyor (`bolunen_sahne: 4`, `asan: []`, en yüksek kullanım ≤ 8.0).

### Red-first — MEDYASIZ

`8.0` → bölünmez · **`8.001` → bölünür, iki parça FARKLI varlık** ·
tek aday + 16 sn → **`KAYNAK-TAVANI-VARLIK-YOK`** (tekrar-kaynakla toplam
**aşılmıyor**) · lisanssız aday **atanmıyor** · bozuk süre stabil kod.
Modül kaldırılınca: **`ModuleNotFoundError: No module named 'kaynak_tavani'`**.

### ⛔ AÇIK KALAN — uygulama bağlanmadı

Planlayıcı **kararı** veriyor ama **uygulanmıyor**: gerçek hatta bir sahneyi
bölmek **ses dosyasını da bölmeyi** (ffmpeg trim), **altyazı küplerini**
yeniden dilimlemeyi ve o sahne için **ikinci ücretsiz stok varlık**
çekmeyi gerektiriyor (`_sahne_medya` sahne başına **tek** klip alıyor).
Bu bağlanmadan **teslim edilen video değişmez** ve `GERCEK-KAYNAK-TAVANI`
aynen tekrarlar.

⚠ **Bu yüzden bu turda ücretli pilot KOŞULMADI**: sonucu önceden belli bir
render kredi harcaması olurdu. Kapı zaten fail-closed çalışıyor — video
üretilir ama **kabul edilmez**.

### R-1d-g (devam) — PLAN GERÇEK ÜRETİM HATTINA BAĞLANDI

⚠ Önceki turda yalnız **karar mantığı** yazılmıştı; kullanıcı şartına göre
**bağlanmamış mantık atomu kapatmaz**. Bu turda **aynı atom** üretim hattına
bağlandı (yeni atom sayılmadı).

`webapp/pipeline.py` — props kurulduktan **sonra**, render'dan **önce**:

1. **`_kaynak_tavani_uygula(props_sahneler, _sahne_ham)`** — tavanı aşan her
   sahne `kaynak_tavani.parca_sayisi()` kadar parçaya bölünür.
2. **İkinci ücretsiz stok klip**: her ek parça için `kaynak.footage_getir`
   (önce özgün sorgu, sonra `genel_yedek_sorgular`) → **farklı `asset_id` /
   lisans / provenans**. Ek klip de **köprüden** geçer (`_kopru_kaydet`),
   yani lisans+kare doğrulaması olmadan **kayda girmez**.
3. **Ses sunucuda senkron kesilir** — `_ses_dilimle()` ffmpeg `-ss/-t`
   (ücretsiz, yerel).
4. **Altyazı zaman dilimleri** `_kelime_dilimle()` ile pencereye kırpılır ve
   **sıfıra taşınır**; her parça kendi `altyazi_parcala` çıktısını alır.
5. Her parça **ayrı `scene_id`** alır (`s001p1`, `s001p2` …) → ölçüm
   parçaları ayırt eder. Parça 1 **mevcut** medyayı korur.
6. ⚠ **FAIL-CLOSED**: ek varlık **edinilemezse** sahne **bölünmez**,
   `KAYNAK-TAVANI-VARLIK-YOK` raporlanır. **Aynı kaynak tekrar kullanılıp
   tavan AŞILMAZ; tavan YÜKSELTİLMEZ.** Kapı ihlali **görünür** kalır.

⚠ `_kopru_kaydet` **ortak kaydedici** olarak `uret()` kapsamına eklendi
(`_sahne_medya` içindeki nested sürüm bölme pasından erişilemiyordu).

### Red-first (medyasız) — entegrasyon

`pipeline.py` geri alınınca **16 kontrol kırmızı**. Ayrıca saf kapı ölçümü:
* 8.508 sn sahne **bölününce** `gercek_qa` tavan kapısı **TEMİZ**
  (`GERCEK-KAYNAK-TAVANI` yok).
* **Aynı** varlık iki parçada kullanılırsa kapı **yine ihlal** veriyor —
  tekrar-kaynak kaçamağı **kapalı**.

### R-1d-g (devam 2) — BAĞIMSIZ DENETİMİN BULDUĞU İKİ DELİK + PİLOT KUSURU

⚠ Denetim (`cd3a5b5`) haklıydı; pilot üçüncü bir kusuru gösterdi.

| # | kusur | kanıt |
|---|---|---|
| 1 | ek `footage_getir` **aynı `asset_id`** dönebilir; kimlik **hiç karşılaştırılmıyordu** | kod incelemesi |
| 2 | `_kopru_kaydet` **False** dönse bile klip `ek_yollar`a eklenip **timeline'a giriyordu** | kod incelemesi |
| 3 | ses dilimleme **başarısız** → bölme iptal | pilot logu: `KAYNAK TAVANI: 3 parca atanamadi -> KAYNAK-TAVANI-SURE-BOZUK` |

### Düzeltme — `kaynak_tavani.ek_varlik_edin()` (kabul kararı TEK yerde)

`kimlik_normalize(provenans)` → **`saglayici|asset_id`**; lisans/sağlayıcı/
asset_id'den **biri bile eksikse kimlik ÜRETİLMEZ**.

Bir aday ancak **üçü birden** sağlanınca kabul edilir:
* normalize kimlik **üretilebiliyor**,
* kimlik **mevcut parçadan ve kabul edilen tüm parçalardan FARKLI**,
* **köprü kaydı BAŞARILI**.

Aksi halde aday **reddedilir** (`AYNI-KAYNAK` / `PROVENANS-EKSIK` /
`KOPRU-RED` / `ADAY-YOK`) ve **sıradaki ücretsiz aday** denenir. Seçenek
tükenirse **`KAYNAK-TAVANI-VARLIK-YOK`** → bölme **yapılmaz**, timeline
kabulü **fail-closed**. Aday üretici patlarsa çökmez, sıradakine geçer.

**Ses dilimleme:** sabit `libmp3lame` kaldırıldı — kodek **uzantıdan türer**
(bazı ffmpeg derlemelerinde o kodek yok ve dilimleme **sessizce**
başarısızdı; pilotta ölçüldü).

### Red-first — DAVRANIŞ testi (string kontrol DEĞİL)

Gerçek `ek_varlik_edin` **test-double**'larla çağrılıyor:
* aynı `asset_id` dönen aday → **`AYNI-KAYNAK`**, sıradaki kabul edilir;
* tek aday ve o da aynı kaynak → **`KAYNAK-TAVANI-VARLIK-YOK`**, `kabul: []`;
* **köprü False** → **`KOPRU-RED`**, aday timeline'a **girmez**;
* köprü ilk adayda False, ikincide True → **ikincisi** kabul;
* lisanssız aday → **`PROVENANS-EKSIK`**;
* iki ek parça → **birbirinden farklı** iki kaynak.

Modül geri alınınca: **`AttributeError: ... has no attribute 'ek_varlik_edin'`**.

⚠ ffmpeg dilimleme yolu **yalnızca uzak worker'da** koşar; Mac'te medya/QA
artefaktı **üretilmedi**.

### R-1d-g (devam 3) — İKİNCİ BAĞIMSIZ DENETİMİN ÜÇ BULGUSU

| # | bulgu | düzeltme |
|---|---|---|
| 1 | `_mevcut_kimlik` **boşken** `mevcut_kimlikler=[]` ile devam ediliyordu → yeni adayın mevcut klipten farklı olduğu **kanıtlanamaz** | kimlik zorunluluğu **yardımcının içine** alındı: `mevcut_zorunlu=True`; liste boş **ya da** boş kimlik içeriyorsa **`MEVCUT-KIMLIK-YOK`** → `KAYNAK-TAVANI-VARLIK-YOK`, **aday üretici hiç çağrılmaz** |
| 2 | `.mp3` hedefte `-q:a` yine MP3 encoder seçebilir; **uzantı varsayımı** yeterli değil | **`-c:a pcm_s16le` + `.wav`** — her ffmpeg derlemesinde var. Hata **stderr ile raporlanıyor** (`ses dilimlenemedi: …`), pilot kök nedeni kanıtlanabilir |
| 3 | Ses kesimi başarısız olunca daha önce köprüye yazılmış ek adaylar **bütçe/provenans ölçümünü kirletiyordu** | **işlem sırası değişti → doğal transactional**: **(B) ses kesimi ÖNCE**, **(C) edinim SONRA**. Kesim başarısızsa **hiçbir** ek varlık edinilmez ve köprüye **hiçbir şey** yazılmaz; yarım dilimler **silinir** |

### Red-first — DAVRANIŞ (string değil)

* mevcut kimlik **boş** → `ok=False`, `kabul=[]`, `MEVCUT-KIMLIK-YOK`;
* mevcut liste **boş** → aday üretici **hiç çağrılmıyor** (üretici
  `AssertionError` fırlatacak şekilde kuruldu, çağrılmadığı için geçti);
* `kimlik_normalize`: lisans **veya** sağlayıcı eksikse **boş** kimlik.

Sıra ve temizlik kontrolleri kod üzerinden; geri alınınca
**`ValueError: substring not found`** (blok yok).

### R-1d-g (devam 4) — PİLOT KÖK NEDENİ KANITLANDI: göreli ses yolu

Pilot `job_1786724831925` yine `KAYNAK TAVANI: 3 parca atanamadi ->
KAYNAK-TAVANI-SURE-BOZUK` dedi. Kök neden **sunucuda ölçülerek** kanıtlandı
(Mac'te değil, hiçbir kalıcı medya üretmeden):

```
# sunucuda, konteyner içinde
ffmpeg ... -c:a pcm_s16le -ar 44100 /tmp/dilim_t.wav   ->  rc=0, dosya 132378 B
```

Yani **ffmpeg ve PCM WAV encoder sorunsuz**. Sorun **yol**du:
`syol = f"isler/{is_adi}/ses_{n}.mp3"` — **göreli**. Doğrudan ffmpeg'e
verilince sürecin cwd'sine (`/opt/vidrush/webapp`) göre çözülüyor ve dosya
**bulunamıyordu**.

**Düzeltme:** kaynak ve hedef ffmpeg için **`PUBLIC` ile mutlak**;
props `ses` alanı **göreli** kalıyor (renderer sözleşmesi). Temizlik de
mutlak yolla siliyor.

⚠ Bu, "uzantı varsayımıyla PASS deme" uyarısının haklılığını da gösterdi:
kodek değişimi tek başına yetmezdi — asıl kusur yoldu ve **stderr
raporlaması** olmasa yine görünmezdi.

### R-1d-g PİLOTU (son) — HEDEF ÖLÇÜLDÜ, örnek KABUL EDİLMEDİ

`job_1786725532851_r1dasm_189422` · 8 sahne · 56.3 sn.

```
RENDER-QA (gercek timeline): WARN  fail=0 warn=5  sahne=8  kapsam=0.875
kaynak_kullanimi: 7 varlik · en uzun 7.956 sn · asan: []  · temiz: true
TESLIM: RED — ZINCIR-EKSIK:post_qa + KABUL-YOK:QA:FAIL
```

**Atomun hedefi ölçüldü:** `GERCEK-KAYNAK-TAVANI` **kayboldu**
(`asan: []`, `temiz: true`); `KAYNAK TAVANI: … atanamadi` log satırı da
**yok** — yani `KAYNAK-TAVANI-SURE-BOZUK` kusuru **kapandı**.
Kalan uyarılar yalnız `SAGLAYICI-TEKEL` + `FACT-BAGLANTI-YOK` (warn).

⚠ **Bölme yolu bu koşuda ÜRETİMDE TETİKLENMEDİ**: bu işte hiçbir sahne
8.0 sn'yi aşmadı (`en uzun 7.956`), dolayısıyla `n_parca > 1` dalı
çalışmadı. Bölme+ek-varlık zinciri **medyasız davranış testleriyle**
kilitli ama **canlı bir bölme** henüz gözlenmedi.

⛔ **TAM PASS DEĞİL — kabul edilmiş video DENMEZ.**

### ⛔ SONRAKİ TEK GERÇEK BLOKAJ — POST-QA `POST-SIYAH-KARE`

```
POST-QA: FAIL
  [fail] POST-SIYAH-KARE : 3 siyah aralik —
         28.458-28.667 (0.21 sn) · 30.917-31.417 (0.50 sn) ·
         34.542-40.458 (5.92 sn)
  [warn] POST-DONMUS-KARE: 1 donmus aralik — 34.542 (+5.83 sn)
  [warn] POST-FPS        : 24.0 fps, beklenen 30.0
```

Teslim edilen MP4'ün ortasında **~5.9 sn siyah + donmuş** bir bölüm var
(aynı zaman damgası). Bu, izleyicinin **doğrudan gördüğü** bir kusur ve
teknik kapı da onu **fail** ile yakalıyor.

Not: aynı işte `siyah_aralik: 3`, `donmus_aralik: 2` — R-1d-f pilotunda
ikisi de **0**'dı. Bu turda değişen tek render-ilgili şey **ses dilimleme
yolu düzeltmesi** (bölme tetiklenmedi), dolayısıyla **nedensellik
kanıtlanmadı**; bir sonraki atom önce **kaynağı ölçmeli** (segment üretimi
mi, xfade zinciri mi, medya klibinin kendisi mi).

---

## 71. FAZ R-1d-h — SİYAH/DONMUŞ KARE: İLK BOZULAN KATMAN KANITI (14 Ağu)

> **Durum: ölçüm + fail-closed kapı üretim hattında. A–I yeşil.
> Mac'te medya/kare/QA artefaktı ÜRETİLMEDİ. $0.00.**
> Değişen: yeni `webapp/katman_olcum.py`, `webapp/hizli_render.py`,
> `webapp/testler/test_faz_i.py`.

### ⛔ Ölçülen kusur

R-1d-g pilotu (`job_1786725532851`):
`POST-SIYAH-KARE` **fail** — 28.458–28.667 · 30.917–31.417 ·
**34.542–40.458 (5.92 sn)**; `POST-DONMUS-KARE` **warn** — 34.542 (+5.83 sn).
POST-QA kusuru **yakalıyor** ama **hangi katmanda** oluştuğunu
**söylemiyordu**: kaynak klip mi, segment üretimi mi, xfade zinciri mi?

### Yapılan

**`webapp/katman_olcum.py`** — aynı ölçüm (`blackdetect` / `freezedetect`,
eşikler **`qa_son` ile aynı**, yeniden tanımlanmadı) **her katmana ayrı**
uygulanır ve **üretim sırasında ilk bozulan** katman raporlanır:
`kaynak → segment → birlesik → final`.

⚠ **Tahmin yok:** `final` bozuk ama önceki katmanların **hiçbiri
ölçülemediyse** hüküm **`KATMAN-ATFEDILEMEDI`** — "herhalde xfade'dir"
**denmez**. Ölçülemeyen dosya **temiz sayılmaz**. Koşucu patlarsa
**`KATMAN-OLCULEMEDI`**. Kodlar: `KATMAN-SIYAH-KARE`, `KATMAN-DONMUS-KARE`.

**`hizli_render`** — teslim kapısı artık `pix_fmt`'e **ek olarak**
siyah/donmuş de ölçüyor. ⚠ Ölçüm **tam burada** yapılır çünkü **ara
dosyalar (segmentler, `birlesik`) hâlâ duruyor**; iş bitince silinirler ve
atıf **imkânsız** hale gelir. ⚠ **FAIL-CLOSED**: nihai dosyada siyah/donmuş
varsa çıktı **teslim edilmez** (Remotion'a düşer) — izleyicinin gördüğü bir
kusurla teslim yapılmaz.

### Red-first — MEDYASIZ davranış testleri

Sahte ffmpeg stderr enjekte edilerek **gerçek fonksiyonlar** çağrılıyor:
* pilotun **gerçek** aralığı ayrıştırılıyor (`34.542–40.458`, 5.916 sn);
* **kaynak** bozuksa suç `kaynak`a — **xfade'e değil**;
* kaynak+segment temiz, `birlesik` bozuksa suç **xfade zincirine**;
* yalnız `final` bozuksa suç **altyazı gömme adımına**;
* önceki katman ölçülmediyse **`KATMAN-ATFEDILEMEDI`**, `katman=None`;
* ölçülemeyen **temiz sayılmıyor**.

Modül kaldırılınca: **`ModuleNotFoundError: No module named 'katman_olcum'`**.

### R-1d-h (devam) — BAĞIMSIZ DENETİM: `returncode` ATILIYORDU

⚠ Denetim haklıydı: `_ffmpeg_stderr` **yalnız stderr** döndürüyordu.
Dosya yok / decoder hatası / `rc != 0` durumunda `blackdetect` eşleşmesi
**çıkmaz** → `olc()` bunu **`olculdu=True` ve TEMİZ** sayardı → **bozuk
çıktı teslim kapısından GEÇERDİ**. Yani kapı fail-closed **değildi**.

**Düzeltme — koşucu sözleşmesi `(rc, stderr)`:**
* iki komuttan **herhangi biri** `rc != 0` → **`KATMAN-OLCULEMEDI`**,
  `olculdu=False` → `temiz_mi=False` → **teslim reddi**;
* **sadece metin** dönen eski biçim **kabul edilmiyor**
  (`DONUS-KODU-YOK`) — dönüş kodu bilinmeden "ölçüldü" **denmez**;
* `subprocess.CompletedProcess` de kabul;
* **timeout / başlatma hatası** aynı stabil kodla fail-closed
  (üretim koşucusu `rc=1` döner).

**Gerçek davranış testi (string değil):** olmayan bir dosya yolu ile
**gerçek ffmpeg** çağrılıyor → `KATMAN-OLCULEMEDI`, `temiz_mi=False`.
⚠ Bu test **hiçbir medya/kare üretmez** (girdi yok, çıktı `-f null`);
Mac'te artefakt oluşmaz — doğrulandı.

### R-1d-h PİLOTU — siyah/donmuş TEKRARLAMADI; blokaj kaynak tavanına döndü

`job_1786727121434_r1dasm_efa7fe` · 8 sahne · 55.8 sn.

```
POST-QA : WARN   siyah_aralik=0   donmus_aralik=0
(log'da hiç `KATMAN-` satırı YOK -> kapı tetiklenmedi)
RENDER-QA: FAIL fail=1
  GERCEK-KAYNAK-TAVANI: ..._s001  8.172 sn (tavan 8.0)
TESLIM: RED — ZINCIR-EKSIK:pre_qa
```

⚠ **Dürüst sonuç:** R-1d-g pilotundaki siyah/donmuş bölüm **bu koşuda
tekrarlamadı** (`siyah=0, donmus=0`). Kapı ve katman-atıf mekanizması
yerinde ve fail-closed, ama **atfedilecek bir olay olmadığı için ilk
bozulan katman KANITLANAMADI**. Kusur **aralıklı (intermittent)** görünüyor;
tetiklendiğinde artık hem **teslimi durduracak** hem de **hangi katmanda
başladığını yazacak**.

### ⛔ SONRAKİ TEK GERÇEK BLOKAJ — üretilmiş-görsel sahnesi BÖLÜNEMİYOR

`..._s001` bir **AI üretilmiş görsel** sahnesi (`openai/uretilmis-eser`) ve
**8.172 sn** ile tavanı aşıyor. Bölme yolu ek varlığı **yalnızca
`footage_sorgu` üzerinden ücretsiz stok klip** çekerek buluyor; üretilmiş-
görsel sahnesinde bu sorgu **yok/boş** olduğu için aday havuzu **boş**
kalıyor → `ek_varlik_edin` **`KAYNAK-TAVANI-VARLIK-YOK`** ile fail-closed
→ sahne **bölünmüyor** → kapı ihlali sürüyor.

**Doğru atom (R-1d-i):** üretilmiş-görsel sahnesi için de **farklı kaynaklı
ikinci varlık** üretilebilmeli — ya sahne metninden **ücretsiz stok** sorgusu
türetilsin, ya da bölme **görsel düzeyinde** (aynı sahnenin farklı kadraj/
çerçevesi ayrı `asset_id` ile) çözülsün. ⚠ Tavanı yükseltmek **YANLIŞ**;
⚠ ücretli yeni görsel üretmek de **kapsam dışı**.
