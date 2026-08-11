/**
 * TEK IKON SISTEMI — inline SVG, bagimlilik yok.
 *
 * ⚠ NEDEN: eski arayuzde 127 emoji/simge, 54 tekili vardi (🎬 ⭐ 🎞 ✨ 🎨 …).
 * Emoji platformdan platforma farkli cizilir, ekran okuyucular tarafindan
 * anlamsiz okunur ("clapper board"), boyut/hizalama tutturulamaz. Tek bir
 * `ikon(ad)` fonksiyonu hepsini degistiriyor; `test_faz_f.py` emoji kalintisi
 * icin lint yapiyor.
 *
 * Kullanim:
 *   ikon("belgesel")                -> SVG dizesi (aria-hidden)
 *   <span data-ikon="ayar"></span>  -> `ikonlariBagla()` doldurur
 */

const IKON_P = 'fill="none" stroke="currentColor" stroke-width="1.8" ' +
          'stroke-linecap="round" stroke-linejoin="round"';

/** Yol tanimlari — viewBox 24x24, tek cizgi stili (tutarlilik icin). */
const IKON_YOLLARI = {
  // ⚠ Ilk surumde logo uc yatay cizgi + daire idi ve mobilde HAMBURGER MENU
  // gibi gorunuyordu (yanlis afordans: tiklanabilir menu sanisi). Bunun yerine
  // diyafram/objektif izi: marka isareti oldugu belli, menu ile karismaz.
  logo: `<circle cx="12" cy="12" r="8.4" ${IKON_P}/><path ${IKON_P} d="M12 3.6v8.4l7.3 4.2"/><path ${IKON_P} d="M12 12 4.7 16.2M12 12l7.3-4.2"/>`,
  ana: `<path ${IKON_P} d="M3 10.5 12 3l9 7.5"/><path ${IKON_P} d="M5.5 9.5V20h13V9.5"/>`,
  arti: `<path ${IKON_P} d="M12 5v14M5 12h14"/>`,
  proje: `<path ${IKON_P} d="M3 7.5A1.5 1.5 0 0 1 4.5 6h5l2 2.5h7.5A1.5 1.5 0 0 1 20.5 10v8a1.5 1.5 0 0 1-1.5 1.5H4.5A1.5 1.5 0 0 1 3 18Z"/>`,
  sablon: `<rect x="3.5" y="4.5" width="7" height="7" rx="1.4" ${IKON_P}/><rect x="13.5" y="4.5" width="7" height="7" rx="1.4" ${IKON_P}/><rect x="3.5" y="14.5" width="7" height="5" rx="1.4" ${IKON_P}/><rect x="13.5" y="14.5" width="7" height="5" rx="1.4" ${IKON_P}/>`,
  ayar: `<circle cx="12" cy="12" r="3" ${IKON_P}/><path ${IKON_P} d="M12 3v2.2M12 18.8V21M4.2 7.5l1.9 1.1M17.9 15.4l1.9 1.1M4.2 16.5l1.9-1.1M17.9 8.6l1.9-1.1"/>`,
  video: `<rect x="3" y="6" width="12.5" height="12" rx="2" ${IKON_P}/><path ${IKON_P} d="m16.5 10.5 4.5-2.8v8.6l-4.5-2.8Z"/>`,
  belgesel: `<rect x="3" y="5" width="18" height="14" rx="2" ${IKON_P}/><path ${IKON_P} d="M3 9h18M7.5 5v4M13 5v4M18.5 5v4"/>`,
  hikaye: `<path ${IKON_P} d="M4 5.5A1.5 1.5 0 0 1 5.5 4H11v16H5.5A1.5 1.5 0 0 1 4 18.5Z"/><path ${IKON_P} d="M20 5.5A1.5 1.5 0 0 0 18.5 4H13v16h5.5A1.5 1.5 0 0 0 20 18.5Z"/>`,
  animasyon: `<path ${IKON_P} d="M12 4.2a7.8 7.8 0 1 0 7.8 7.8c0-1.5-1.3-2.1-2.6-2.1h-1.5a1.8 1.8 0 0 1 0-3.6h.4c1 0 1.6-.9 1-1.7A7.7 7.7 0 0 0 12 4.2Z"/><circle cx="9" cy="10" r="1.1" fill="currentColor"/><circle cx="13" cy="8.4" r="1.1" fill="currentColor"/><circle cx="8.6" cy="14.4" r="1.1" fill="currentColor"/>`,
  kalem: `<path ${IKON_P} d="M15.6 4.9 19 8.3 8.9 18.4l-4.4 1 1-4.4Z"/><path ${IKON_P} d="m14 6.5 3.4 3.4"/>`,
  yukle: `<path ${IKON_P} d="M12 16V4.5M8 8l4-3.5L16 8"/><path ${IKON_P} d="M4.5 15v3.5A1.5 1.5 0 0 0 6 20h12a1.5 1.5 0 0 0 1.5-1.5V15"/>`,
  gorsel: `<rect x="3.5" y="5" width="17" height="14" rx="2" ${IKON_P}/><circle cx="9" cy="10" r="1.6" ${IKON_P}/><path ${IKON_P} d="m4.5 17 4.6-4.2 3.2 2.8 3-2.6 4.2 3.6"/>`,
  ses: `<path ${IKON_P} d="M12 4.5 7.5 8.5H4.5v7h3l4.5 4Z"/><path ${IKON_P} d="M16 9.2a4 4 0 0 1 0 5.6M18.6 6.6a7.6 7.6 0 0 1 0 10.8"/>`,
  yazi: `<path ${IKON_P} d="M5 6.5V5h14v1.5M12 5v14M9 19h6"/>`,
  palet: `<path ${IKON_P} d="M12 4a8 8 0 1 0 0 16c1.2 0 1.8-.8 1.8-1.6 0-1.6 1.2-2.2 2.6-2.2H18a2 2 0 0 0 2-2A8 8 0 0 0 12 4Z"/><circle cx="8.6" cy="10.6" r="1.05" fill="currentColor"/><circle cx="12.4" cy="8.4" r="1.05" fill="currentColor"/><circle cx="8" cy="14.6" r="1.05" fill="currentColor"/>`,
  isik: `<path ${IKON_P} d="M12 3.5v2M5.5 6l1.4 1.4M18.5 6l-1.4 1.4M4 12.5h2M18 12.5h2"/><path ${IKON_P} d="M9 16.5a4.2 4.2 0 1 1 6 0c-.6.6-.9 1.2-.9 2H9.9c0-.8-.3-1.4-.9-2Z"/><path ${IKON_P} d="M10.2 20.5h3.6"/>`,
  arama: `<circle cx="10.8" cy="10.8" r="6.3" ${IKON_P}/><path ${IKON_P} d="m15.4 15.4 4 4"/>`,
  oynat: `<path ${IKON_P} d="M8 5.5 18 12 8 18.5Z"/>`,
  indir: `<path ${IKON_P} d="M12 4v11M8 11.5l4 3.5 4-3.5"/><path ${IKON_P} d="M4.5 19h15"/>`,
  ok: `<path ${IKON_P} d="m9 5.5 6.5 6.5L9 18.5"/>`,
  geri: `<path ${IKON_P} d="m15 5.5-6.5 6.5L15 18.5"/>`,
  onay: `<path ${IKON_P} d="m5 12.5 4.5 4.5L19 7.5"/>`,
  bilgi: `<circle cx="12" cy="12" r="8.2" ${IKON_P}/><path ${IKON_P} d="M12 11v5.5M12 8.1v.1"/>`,
  uyari: `<path ${IKON_P} d="M12 4.5 20.5 19H3.5Z"/><path ${IKON_P} d="M12 10v4M12 16.6v.1"/>`,
  hata: `<circle cx="12" cy="12" r="8.2" ${IKON_P}/><path ${IKON_P} d="m9 9 6 6M15 9l-6 6"/>`,
  bos: `<rect x="3.5" y="5.5" width="17" height="13" rx="2" ${IKON_P} stroke-dasharray="3 3"/><path ${IKON_P} d="M9 12h6"/>`,
  saat: `<circle cx="12" cy="12" r="8.2" ${IKON_P}/><path ${IKON_P} d="M12 7.6V12l3.2 2"/>`,
  kilit: `<rect x="5" y="10.5" width="14" height="9" rx="2" ${IKON_P}/><path ${IKON_P} d="M8.5 10.5V8a3.5 3.5 0 0 1 7 0v2.5"/>`,
  kaynak: `<path ${IKON_P} d="M6 4.5h9L18.5 8v11.5H6Z"/><path ${IKON_P} d="M14.5 4.5V8h4M9 12h6M9 15.5h4"/>`,
  cip: `<rect x="6.5" y="6.5" width="11" height="11" rx="2" ${IKON_P}/><path ${IKON_P} d="M10 3.5v3M14 3.5v3M10 17.5v3M14 17.5v3M3.5 10h3M3.5 14h3M17.5 10h3M17.5 14h3"/>`,
  yenile: `<path ${IKON_P} d="M19 12a7 7 0 1 1-2.4-5.3"/><path ${IKON_P} d="M19.5 4.5V9H15"/>`,
  cop: `<path ${IKON_P} d="M5.5 7.5h13M9.5 7.5V5.2h5v2.3M7 7.5 8 19.5h8l1-12"/>`,
  kanal: `<circle cx="12" cy="12" r="8.2" ${IKON_P}/><path ${IKON_P} d="M4 12h16M12 4c2.4 2.2 3.6 5 3.6 8s-1.2 5.8-3.6 8c-2.4-2.2-3.6-5-3.6-8s1.2-5.8 3.6-8Z"/>`,
};

/**
 * SVG dizesi don. Ikon ADI YOKSA sessizce bos dondurmez — konsola yazar ve
 * bos kare dondurur ki eksik ikon fark edilsin (sessiz kayip yasagi).
 */
export function ikon(ad, {boyut = 20, sinif = ''} = {}) {
  const yol = IKON_YOLLARI[ad];
  if (!yol) {
    console.warn(`[ikon] tanimsiz ikon: ${ad}`);
    return `<svg viewBox="0 0 24 24" width="${boyut}" height="${boyut}" ` +
           `class="${sinif}" aria-hidden="true"><rect x="4" y="4" width="16" ` +
           `height="16" rx="2" ${IKON_P} stroke-dasharray="2 2"/></svg>`;
  }
  return `<svg viewBox="0 0 24 24" width="${boyut}" height="${boyut}" ` +
         `class="${sinif}" aria-hidden="true" focusable="false">${yol}</svg>`;
}

/** `data-ikon` tasiyan tum ogeleri doldur (kok verilirse yalnizca onun icinde). */
export function ikonlariBagla(kok = document) {
  kok.querySelectorAll('[data-ikon]').forEach((el) => {
    if (el.dataset.ikonBagli === '1') return;
    const boyut = Number(el.dataset.ikonBoyut || 20);
    el.innerHTML = ikon(el.dataset.ikon, {boyut});
    el.dataset.ikonBagli = '1';
  });
}

export const IKON_ADLARI = Object.keys(IKON_YOLLARI);
