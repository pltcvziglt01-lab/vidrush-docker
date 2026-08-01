import {staticFile, continueRender, delayRender} from 'remotion';

/**
 * ALTYAZI FONTLARI — TTF dosyalari public/fonts/ icine GOMULU (offline).
 * Google Fonts CDN'e baglanmiyoruz: headless render sirasinda ag beklemesi/hatasi olmasin.
 */
export type FontAdi = 'montserrat' | 'anton' | 'bebas' | 'poppins' | 'oswald' | 'sistem';

const DOSYALAR: Record<Exclude<FontAdi, 'sistem'>, string> = {
  montserrat: 'fonts/Montserrat-Bold.ttf',
  anton: 'fonts/Anton-Regular.ttf',
  bebas: 'fonts/BebasNeue-Regular.ttf',
  poppins: 'fonts/Poppins-Bold.ttf',
  oswald: 'fonts/Oswald-Bold.ttf',
};

const SISTEM_YIGIN =
  '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif';

export const fontAilesi = (f?: FontAdi): string =>
  !f || f === 'sistem' ? SISTEM_YIGIN : `"vf-${f}", ${SISTEM_YIGIN}`;

let yuklendi = false;

/** @font-face enjekte + fontlar HAZIR olana kadar render'i beklet (yoksa ilk kareler yedek fontla cikar). */
export const fontlariYukle = () => {
  if (yuklendi || typeof document === 'undefined') return;
  yuklendi = true;

  const stil = document.createElement('style');
  stil.textContent = (Object.keys(DOSYALAR) as Array<keyof typeof DOSYALAR>)
    .map(
      (ad) => `@font-face{font-family:"vf-${ad}";src:url("${staticFile(
        DOSYALAR[ad],
      )}") format("truetype");font-weight:100 900;font-display:block;}`,
    )
    .join('\n');
  document.head.appendChild(stil);

  const bekle = delayRender('altyazi fontlari yukleniyor');
  const isler = (Object.keys(DOSYALAR) as Array<keyof typeof DOSYALAR>).map((ad) =>
    (document as any).fonts?.load(`700 64px "vf-${ad}"`),
  );
  Promise.all(isler)
    .catch(() => undefined)
    .then(() => continueRender(bekle));
};

/**
 * ALTYAZI AYARI — CapCut tarzi tam kontrol.
 * Kullanici bir sablon secer, sonra istedigi alani tek tek degistirebilir.
 */
export type AltyaziAyar = {
  font: FontAdi;
  boyut: number;          // 1080p'de piksel
  agirlik: number;        // 300-900
  renk: string;           // yazi rengi
  konturRenk: string;     // dis hat rengi
  konturKalinlik: number; // px (0 = kontur yok)
  arka: string;           // 'yok' veya rgba(...) kutu rengi
  konum: 'alt' | 'orta' | 'ust';
  buyukHarf: boolean;
  golge: boolean;         // yumusak dis golge
  harfAralik: number;
};

export const VARSAYILAN_AYAR: AltyaziAyar = {
  font: 'montserrat', boyut: 52, agirlik: 800, renk: '#ffffff',
  konturRenk: '#000000', konturKalinlik: 5, arka: 'yok',
  konum: 'alt', buyukHarf: false, golge: true, harfAralik: 0,
};

/** HAZIR SABLONLAR — YouTube'da yaygin kullanilan altyazi gorunumleri. */
export const SABLONLAR: Record<string, {ad: string; ozet: string; ayar: AltyaziAyar}> = {
  'beyaz-kontur': {
    ad: 'Beyaz Kontur', ozet: 'Faceless kanallarin en yaygini — beyaz + kalin siyah kenar',
    ayar: {...VARSAYILAN_AYAR},
  },
  'youtube-sari': {
    ad: 'YouTube Sarı', ozet: 'MrBeast tarzı — kalın sarı, ağır siyah kontur, BÜYÜK HARF',
    ayar: {font: 'anton', boyut: 68, agirlik: 400, renk: '#ffe000', konturRenk: '#000000',
           konturKalinlik: 7, arka: 'yok', konum: 'alt', buyukHarf: true, golge: true,
           harfAralik: 1},
  },
  hormozi: {
    ad: 'Hormozi', ozet: 'Kısa-video tarzı — çok kalın, büyük harf, orta konum',
    ayar: {font: 'poppins', boyut: 64, agirlik: 900, renk: '#ffffff', konturRenk: '#000000',
           konturKalinlik: 8, arka: 'yok', konum: 'orta', buyukHarf: true, golge: true,
           harfAralik: 0},
  },
  'klasik-kutu': {
    ad: 'Klasik Kutu', ozet: 'Belgesel — koyu yarı saydam kutu, her zeminde okunur',
    ayar: {font: 'montserrat', boyut: 46, agirlik: 700, renk: '#ffffff', konturRenk: '#000000',
           konturKalinlik: 0, arka: 'rgba(0,0,0,0.72)', konum: 'alt', buyukHarf: false,
           golge: true, harfAralik: 0},
  },
  'sari-kutu': {
    ad: 'Sarı Kutu', ozet: 'Vurgulu explainer — sarı dolgu, koyu yazı',
    ayar: {font: 'poppins', boyut: 50, agirlik: 700, renk: '#0a0a0a', konturRenk: '#000000',
           konturKalinlik: 0, arka: 'rgba(255,212,0,0.95)', konum: 'alt', buyukHarf: true,
           golge: false, harfAralik: 0.5},
  },
  sinematik: {
    ad: 'Sinematik', ozet: 'İnce, geniş harf aralığı — belgesel/film hissi',
    ayar: {font: 'oswald', boyut: 44, agirlik: 500, renk: '#f2f2f2', konturRenk: '#000000',
           konturKalinlik: 2, arka: 'yok', konum: 'alt', buyukHarf: false, golge: true,
           harfAralik: 1.5},
  },
  podcast: {
    ad: 'Podcast', ozet: 'Bebas Neue — uzun, dar, iri harfler',
    ayar: {font: 'bebas', boyut: 72, agirlik: 400, renk: '#ffffff', konturRenk: '#000000',
           konturKalinlik: 5, arka: 'yok', konum: 'alt', buyukHarf: true, golge: true,
           harfAralik: 2},
  },
  temiz: {
    ad: 'Temiz Beyaz', ozet: 'Konturuz, sadece yumuşak gölge — minimal/modern',
    ayar: {font: 'montserrat', boyut: 50, agirlik: 700, renk: '#ffffff', konturRenk: '#000000',
           konturKalinlik: 0, arka: 'yok', konum: 'alt', buyukHarf: false, golge: true,
           harfAralik: 0},
  },
};

/** Gelen props'u guvenli bir AltyaziAyar'a cevir (eksik alanlar varsayilandan gelir). */
export const ayarCoz = (girdi?: Partial<AltyaziAyar> | string): AltyaziAyar => {
  if (typeof girdi === 'string') {
    const s = SABLONLAR[girdi];
    return s ? {...s.ayar} : {...VARSAYILAN_AYAR};
  }
  return {...VARSAYILAN_AYAR, ...(girdi || {})};
};
