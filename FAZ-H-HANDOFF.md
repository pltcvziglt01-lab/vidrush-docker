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
| 12 Ağu | **I-2a hiyerarşik konsept taksonomisi** | bu commit | ✅ yerel yeşil, **deploy YOK** |

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
.venv-test/bin/pip install fastapi python-multipart httpx pillow requests edge-tts
for t in a b c d e f g i; do python3 webapp/testler/test_faz_$t.py; done
.venv-test/bin/python webapp/testler/test_faz_h.py
```

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
