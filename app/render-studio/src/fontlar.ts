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

/** CSS font-family degeri (sistem yigini yedek olarak hep sonda). */
export const fontAilesi = (f?: FontAdi): string =>
  !f || f === 'sistem' ? SISTEM_YIGIN : `"vf-${f}", ${SISTEM_YIGIN}`;

let yuklendi = false;

/**
 * @font-face kurallarini bir kez enjekte eder ve fontlar HAZIR olana kadar render'i bekletir.
 * delayRender olmadan Remotion ilk kareleri font yuklenmeden yakalar -> yazi tipi ATLAR.
 */
export const fontlariYukle = () => {
  if (yuklendi || typeof document === 'undefined') return;
  yuklendi = true;

  const stil = document.createElement('style');
  stil.textContent = (Object.keys(DOSYALAR) as Array<keyof typeof DOSYALAR>)
    .map(
      (ad) => `@font-face{font-family:"vf-${ad}";src:url("${staticFile(
        DOSYALAR[ad],
      )}") format("truetype");font-weight:400 900;font-display:block;}`,
    )
    .join('\n');
  document.head.appendChild(stil);

  // Fontlarin gercekten yuklenmesini bekle (aksi halde ilk kareler yedek fontla cikar)
  const bekle = delayRender('altyazi fontlari yukleniyor');
  const isler = (Object.keys(DOSYALAR) as Array<keyof typeof DOSYALAR>).map((ad) =>
    (document as any).fonts?.load(`700 64px "vf-${ad}"`),
  );
  Promise.all(isler)
    .catch(() => undefined)
    .then(() => continueRender(bekle));
};

/**
 * ALTYAZI SABLONLARI — hazir gorunum setleri.
 * Her sablon: font + boyut + renk + kontur/kutu + konum.
 */
export type SablonAdi = 'klasik' | 'youtube' | 'temiz' | 'kalin' | 'sinema';

export type SablonStil = {
  ad: string;
  font: FontAdi;
  boyut: number;          // 1080p'de piksel
  renk: string;
  arka: string;           // kutu rengi ('transparent' = kutusuz)
  kontur: string;         // text-shadow ile cizilen dis hat
  buyukHarf: boolean;
  agirlik: number;
  harfAralik: number;
  altBosluk: number;      // ekranin altindan uzaklik (px)
};

export const SABLONLAR: Record<SablonAdi, SablonStil> = {
  // Koyu yari-saydam kutu — her zeminde okunur, klasik belgesel
  klasik: {
    ad: 'Klasik Kutu', font: 'montserrat', boyut: 46, renk: '#ffffff',
    arka: 'rgba(0,0,0,0.72)', kontur: '0 2px 6px rgba(0,0,0,0.9)',
    buyukHarf: false, agirlik: 700, harfAralik: 0, altBosluk: 64,
  },
  // MrBeast/faceless tarzi: kalin sari, kutusuz, kalin siyah kontur
  youtube: {
    ad: 'YouTube Sarı', font: 'anton', boyut: 68, renk: '#ffe000',
    arka: 'transparent',
    kontur: '4px 4px 0 #000, -4px 4px 0 #000, 4px -4px 0 #000, -4px -4px 0 #000, 0 6px 14px rgba(0,0,0,0.6)',
    buyukHarf: true, agirlik: 400, harfAralik: 1, altBosluk: 90,
  },
  // Sade beyaz, kutusuz, yumusak golge — modern/temiz
  temiz: {
    ad: 'Temiz Beyaz', font: 'montserrat', boyut: 52, renk: '#ffffff',
    arka: 'transparent',
    kontur: '0 3px 10px rgba(0,0,0,0.85), 0 0 3px rgba(0,0,0,0.9)',
    buyukHarf: false, agirlik: 800, harfAralik: 0, altBosluk: 78,
  },
  // Kalin dolgu kutu, buyuk harf — vurgulu explainer
  kalin: {
    ad: 'Kalın Kutu', font: 'poppins', boyut: 50, renk: '#0a0a0a',
    arka: 'rgba(255,212,0,0.95)', kontur: 'none',
    buyukHarf: true, agirlik: 700, harfAralik: 0.5, altBosluk: 70,
  },
  // Sinematik: ince, genis harf araligi, alt-orta
  sinema: {
    ad: 'Sinematik', font: 'oswald', boyut: 44, renk: '#f2f2f2',
    arka: 'transparent',
    kontur: '0 2px 8px rgba(0,0,0,0.95)',
    buyukHarf: false, agirlik: 600, harfAralik: 1.5, altBosluk: 84,
  },
};

export const sablonCoz = (s?: string): SablonStil =>
  SABLONLAR[(s as SablonAdi) in SABLONLAR ? (s as SablonAdi) : 'klasik'];
