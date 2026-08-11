/**
 * API SOZLESMESI — TEK DOGRULUK KAYNAGI.
 *
 * ⚠ BACKEND'E DOKUNULMUYOR. Bu dosya `webapp/server.py`'nin var olan uclarini
 * ve `/api/generate`'in 22 form alanini aynen yansitir. `test_faz_f.py` iki
 * tarafi karsilastirir; server.py'de olmayan bir uc ya da burada eksik bir
 * generate alani FAIL uretir.
 *
 * ⚠ KOK YOLU: yollar basinda `/` OLMADAN yazilir ve `document.baseURI`
 * uzerinden cozulur. Eski surumde de boyleydi (`fetch("api/...")` +
 * `<base href="/">`). Boylece alt dizinde barindirma bozulmaz.
 */

export const UCLAR = {
  saglik: 'api/saglik',
  saglikDerin: 'api/saglik/derin',   // Faz H: gercek bagimlilik olcumu
  isler: 'api/isler',
  is: 'api/job/',                    // + is_id
  uret: 'api/generate',
  editStilleri: 'api/edit-stilleri',
  animasyonStilleri: 'api/animasyon-stilleri',
  sesler: 'api/sesler',
  sesKutuphane: 'api/ses-kutuphane',
  paletler: 'api/paletler',
  isikDuzeyleri: 'api/isik-duzeyleri',
  arkaplanlar: 'api/arkaplanlar',
  altyaziSablonlari: 'api/altyazi-sablonlari',
  profiller: 'api/profiller',
  profil: 'api/profil',              // POST; DELETE icin + /{pid}
  capaSifirla: 'api/profil/',        // + {pid}/capa-sifirla
  animAnaliz: 'api/anim/analiz',
  animSorular: 'api/anim/sorular',
  freepikKota: 'api/freepik-kota',
  ciktilar: 'ciktilar/',
  onizleme: 'onizleme/',
  sesOrnek: 'ses-ornek/',
  fontlar: 'fonts/',
};

/**
 * `/api/generate` MULTIPART ALAN HARITASI — server.py `uret_baslat` imzasiyla
 * birebir. Alan adi DEGISTIRILEMEZ; degisirse uretim ya baslamaz ya yanlis
 * parametreyle baslar.
 *
 *   ad      : multipart alan adi (server.py'deki Form/File adi)
 *   tur     : metin | dosya | dosya-listesi
 *   zorunlu : her istekte gonderilir
 *   kosul   : yalnizca bu video turlerinde anlamli (bilgi amacli)
 */
export const GENERATE_ALANLARI = [
  {ad: 'session', tur: 'metin', zorunlu: true},
  {ad: 'story', tur: 'metin', zorunlu: true},
  {ad: 'tur', tur: 'metin', zorunlu: true},
  {ad: 'edit', tur: 'metin', zorunlu: false},
  {ad: 'sure_dk', tur: 'metin', zorunlu: true},
  {ad: 'gecis', tur: 'metin', zorunlu: true},
  {ad: 'zoom', tur: 'metin', zorunlu: true},
  {ad: 'profil', tur: 'metin', zorunlu: false},
  {ad: 'altyazi', tur: 'metin', zorunlu: true},
  {ad: 'altyazi_sablon', tur: 'metin', zorunlu: false},
  {ad: 'palet', tur: 'metin', zorunlu: false},
  {ad: 'palet_ozel', tur: 'metin', zorunlu: false},
  {ad: 'acilis', tur: 'metin', zorunlu: false, kosul: 'hikaye'},
  {ad: 'sora', tur: 'metin', zorunlu: false, kosul: 'hikaye'},
  {ad: 'arkaplan', tur: 'metin', zorunlu: false},
  {ad: 'ses', tur: 'metin', zorunlu: false},
  {ad: 'isik', tur: 'metin', zorunlu: false},
  {ad: 'gorsel_model', tur: 'metin', zorunlu: false},
  {ad: 'karakter', tur: 'dosya', zorunlu: false},
  {ad: 'stil', tur: 'dosya', zorunlu: false},
  {ad: 'sahne_ref', tur: 'dosya-listesi', zorunlu: false, kosul: 'animasyon'},
];

/** Video turleri — tek uretim akisinin PARAMETRESI, ayri menu DEGIL. */
export const TURLER = [
  {
    id: 'documentary', ad: 'Belgesel', ikon: 'belgesel',
    acik: 'Konu ver; sistem araştırır, gerçek arşiv/stok görüntüsüyle kurar.',
    etiketler: ['Araştırmalı', 'Gerçek görüntü'],
    referans: 'opsiyonel',
  },
  {
    id: 'hikaye', ad: 'Hikâye', ikon: 'hikaye',
    acik: 'Anlatıya dayalı kurgu. Açılış sahnesi ve hareketli plan seçenekli.',
    etiketler: ['Anlatı', 'Kurgu'],
    referans: 'opsiyonel',
  },
  {
    id: 'animasyon', ad: 'Animasyon', ikon: 'animasyon',
    acik: 'Referans karelerden stil öğrenir, tutarlı sahneler üretir.',
    etiketler: ['Referans zorunlu', 'Stil öğrenme'],
    referans: 'zorunlu',
  },
];

/** Yolu `document.baseURI`'ye gore coz — kok yolu uyumunu korur. */
export function yol(parca) {
  return new URL(parca, document.baseURI).toString();
}

/** Oturum kimligi — eski surumdeki `SID` ile ayni saklama anahtari. */
export function oturumId() {
  let s = localStorage.getItem('bedosaho_sid');
  if (!s) {
    s = 'w' + Math.random().toString(36).slice(2, 10) +
        Date.now().toString(36).slice(-4);
    localStorage.setItem('bedosaho_sid', s);
  }
  return s;
}

/**
 * GET + JSON. Hata DURUSTCE yukari firlatilir — cagiran taraf gercek hata
 * durumu gosterir; sessizce bos liste dondurmek "veri yok" yalanidir.
 */
export async function getir(parca, {zamanAsimi = 12000} = {}) {
  const kontrol = new AbortController();
  const zt = setTimeout(() => kontrol.abort(), zamanAsimi);
  try {
    const r = await fetch(yol(parca), {signal: kontrol.signal});
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return await r.json();
  } finally {
    clearTimeout(zt);
  }
}

/** Sessizce basarisiz olan surum — YALNIZCA opsiyonel listelerde kullanilir. */
export async function getirSessiz(parca) {
  try {
    return {ok: true, veri: await getir(parca)};
  } catch (e) {
    return {ok: false, hata: String(e.message || e)};
  }
}

/**
 * FormData'yi ALAN HARITASINA gore kur.
 * `degerler` = {alanAdi: deger}. Haritada OLMAYAN bir anahtar gonderilirse
 * hata firlatilir — yazim hatasiyla sessizce dusen alan olmasin.
 */
export function generateFormData(degerler) {
  const bilinen = new Set(GENERATE_ALANLARI.map((a) => a.ad));
  const bilinmeyen = Object.keys(degerler).filter((k) => !bilinen.has(k));
  if (bilinmeyen.length) {
    throw new Error(`generate: bilinmeyen alan(lar): ${bilinmeyen.join(', ')}`);
  }
  const fd = new FormData();
  for (const alan of GENERATE_ALANLARI) {
    const d = degerler[alan.ad];
    if (d === undefined || d === null || d === '') continue;
    if (alan.tur === 'dosya-listesi') {
      (Array.isArray(d) ? d : [d]).forEach((f) => f && fd.append(alan.ad, f));
    } else {
      fd.append(alan.ad, d);
    }
  }
  return fd;
}

export async function uretimBaslat(degerler) {
  const r = await fetch(yol(UCLAR.uret), {
    method: 'POST', body: generateFormData(degerler),
  });
  if (!r.ok) throw new Error((await r.text()) || `HTTP ${r.status}`);
  return r.json();
}

/**
 * Tek isin CANLI durumu. Projeler ekrani bunu periyodik cagirir.
 * ⚠ FAZ H: bu fonksiyon tanimliydi ama HIC CAGRILMIYORDU — Projeler ekrani
 * bir kez cizilip hic yenilenmiyordu. Artik `gorunumler.js` kullaniyor.
 */
export function isDurumu(isId) {
  return getir(UCLAR.is + encodeURIComponent(isId));
}

/**
 * Sunucu cevabindan is kimligini coz.
 * ⚠ FAZ H KOK NEDEN: `/api/generate` `job_id` donduruyordu, wizard ise
 * `cevap.job || cevap.is_id || cevap.id` okuyordu -> kimlik HER ZAMAN bostu.
 * Artik `job_id` BIRINCIL; eski adlar yedek olarak duruyor ki eski bir
 * sunucu surumune karsi da calissin.
 */
export function isKimligiCoz(cevap) {
  const c = cevap || {};
  return String(c.job_id || c.is_id || c.id || c.job || '');
}

export function islerListesi() {
  return getir(`${UCLAR.isler}?session=${encodeURIComponent(oturumId())}`);
}
