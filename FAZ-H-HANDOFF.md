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
| 12 Ağu | H2–H3 araştırma köprüsü + iş sözleşmesi + derin sağlık + UI | bu commit | ✅ **DEPLOY CHECKPOINT** |

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

## 11. Test çalıştırma (yerel)

```bash
python3 -m venv .venv-test
.venv-test/bin/pip install fastapi python-multipart httpx pillow requests edge-tts
for t in a b c d e f g; do python3 webapp/testler/test_faz_$t.py; done
.venv-test/bin/python webapp/testler/test_faz_h.py
```

Faz H fastapi olmadan da koşar; gerçek uç bloğu **BLOKE** yazar ve başarı saymaz.
