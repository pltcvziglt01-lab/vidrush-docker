/**
 * DURUM + TASLAK SAKLAMA.
 *
 * Wizard taslagi `localStorage`'da tutulur; kullanici sekmeyi kapatsa da
 * kaldigi yerden devam eder. Dosyalar (File nesneleri) saklanamaz — bunlar
 * bellekte tutulur ve taslakta yalnizca ADLARI gorunur, bu DURUSTCE belirtilir.
 *
 * ⚠ Eski surumde "Videolarim" YALNIZCA localStorage'daki is id'lerini
 * listeliyordu; baska cihazda liste bosca gorunuyordu. Artik `/api/isler`
 * birincil kaynak, localStorage YEDEK. Hangisinin kullanildigi arayuzde yazili.
 */

const TASLAK_ANAHTAR = 'bedosaho_taslak_v1';
const ISLER_ANAHTAR = 'bedosaho_isler_v1';

/** Wizard'in varsayilan taslagi. Dosya alanlari burada TUTULMAZ. */
export function bosTaslak() {
  return {
    surum: 1,
    // Kurulum bicimi: 'basit' (metin + stil + tek eylem) ya da 'adim'
    // (5 adimli wizard). Varsayilan BASIT; adim adim akis KALDIRILMADI.
    mod: 'basit',
    tur: '',
    // Turu KIM secti? 'kullanici' ise Auto ona DOKUNMAZ. Bos ise basit mod
    // `/api/analiz`in onerisini uygulayabilir (bkz. basit.js `autoTuru`).
    turKaynak: '',
    konu: '',
    girisYontemi: 'konu',
    sureDk: '2',
    editStili: '',
    animStili: '',
    profil: '',
    ses: '',
    palet: '',
    paletOzel: ['#f5e14b', '#6cb6ff', '#4ec98a'],
    arkaplan: '',
    isik: '',
    gecis: true,
    zoom: true,
    altyazi: false,
    altyaziSablon: null,
    acilis: '',
    sora: false,
    unlu: false,
    gorselModel: '',
    guncelleme: '',
  };
}

let _taslak = null;

export function taslak() {
  if (_taslak) return _taslak;
  try {
    const ham = localStorage.getItem(TASLAK_ANAHTAR);
    _taslak = ham ? {...bosTaslak(), ...JSON.parse(ham)} : bosTaslak();
  } catch {
    _taslak = bosTaslak();
  }
  return _taslak;
}

export function taslakYaz(yama) {
  const t = taslak();
  Object.assign(t, yama);
  t.guncelleme = new Date().toISOString();
  try {
    localStorage.setItem(TASLAK_ANAHTAR, JSON.stringify(t));
  } catch (e) {
    console.warn('[taslak] yazilamadi', e);
  }
  return t;
}

export function taslakSil() {
  _taslak = bosTaslak();
  try {
    localStorage.removeItem(TASLAK_ANAHTAR);
  } catch { /* yoksay */ }
}

export function taslakVarMi() {
  const t = taslak();
  return Boolean(t.tur || (t.konu || '').trim());
}

/* ── Bellekteki dosyalar (localStorage'a yazilamaz) ── */
export const dosyalar = {
  sahneRef: [],       // animasyon referans kareleri (List[UploadFile])
  karakter: null,
  stil: null,
};

export function dosyalariTemizle() {
  dosyalar.sahneRef = [];
  dosyalar.karakter = null;
  dosyalar.stil = null;
}

/* ── Yerel is defteri (YEDEK kaynak) ── */
export function yerelIsler() {
  try {
    const l = JSON.parse(localStorage.getItem(ISLER_ANAHTAR) || '[]');
    return Array.isArray(l) ? l : [];
  } catch {
    return [];
  }
}

export function yerelIsEkle(kayit) {
  const l = yerelIsler().filter((x) => x.is_id !== kayit.is_id);
  l.unshift(kayit);
  try {
    localStorage.setItem(ISLER_ANAHTAR, JSON.stringify(l.slice(0, 60)));
  } catch { /* yoksay */ }
}
