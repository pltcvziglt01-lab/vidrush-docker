/**
 * KUCUK UI YARDIMCILARI — HTML uretici saf fonksiyonlar.
 * Framework yok; her uretici dize dondurur, olaylar sonradan baglanir.
 */
import {ikon} from './ikon.js';

/** HTML kacisi — kullanici/sunucu metni DOM'a girmeden once temizlenir. */
export function kac(s) {
  return String(s ?? '').replace(/[&<>"']/g, (c) => (
    {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
}

export const $ = (s, k = document) => k.querySelector(s);
export const $$ = (s, k = document) => Array.from(k.querySelectorAll(s));

/** Yukleniyor iskeleti. */
export function yukleniyor(adet = 3, yukseklik = 96) {
  return `<div class="izgara izgara-3" aria-busy="true" aria-label="Yükleniyor">` +
    Array.from({length: adet}, () =>
      `<div class="iskelet" style="height:${yukseklik}px"></div>`).join('') +
    `</div>`;
}

/**
 * Bos / hata durumu. `tur`: bos | hata | bilgi
 * ⚠ Metin DURUST olmali: veri yoksa "veri yok" degil NEDEN yok yazilir.
 */
export function durumBlok({tur = 'bos', baslik, aciklama, eylem = ''}) {
  const im = tur === 'hata' ? 'hata' : tur === 'bilgi' ? 'bilgi' : 'bos';
  return `<div class="durum-blok ${tur === 'hata' ? 'hata' : ''}">
    ${ikon(im, {boyut: 26})}
    <h3>${kac(baslik)}</h3>
    <p class="kucuk orta" style="max-width:46ch">${kac(aciklama)}</p>
    ${eylem}
  </div>`;
}

export function uyariKutu(metin, tur = 'uyari') {
  const im = tur === 'bilgi' ? 'bilgi' : tur === 'hata' ? 'hata' : 'uyari';
  return `<div class="uyari-kutu ${tur === 'uyari' ? '' : tur}">
    ${ikon(im, {boyut: 18})}<div>${metin}</div></div>`;
}

export function etiket(metin, tur = '') {
  return `<span class="etiket ${tur ? 'etiket-' + tur : ''}">${kac(metin)}</span>`;
}

/** Secim karti (tur/sablon/palet). */
export function secKart({id, ad, acik, ikonAd, etiketler = [], secili = false,
                         grup = 'sec'}) {
  return `<button type="button" class="seckart" role="radio" data-grup="${kac(grup)}"
    data-deger="${kac(id)}" aria-pressed="${secili ? 'true' : 'false'}">
    <span class="seckart-bas">${ikonAd ? ikon(ikonAd, {boyut: 19}) : ''}
      <span class="seckart-ad">${kac(ad)}</span></span>
    ${acik ? `<span class="seckart-acik">${kac(acik)}</span>` : ''}
    ${etiketler.length ? `<span class="seckart-dip">${
      etiketler.map((e) => etiket(e)).join('')}</span>` : ''}
  </button>`;
}

/** Anahtar (switch) — gercek checkbox, klavye ve ekran okuyucu uyumlu. */
export function anahtar({id, ad, acik = '', acikMi = false}) {
  return `<label class="anahtar" for="${kac(id)}">
    <input type="checkbox" id="${kac(id)}" ${acikMi ? 'checked' : ''}>
    <span class="anahtar-gorsel" aria-hidden="true"></span>
    <span class="anahtar-yazi">${kac(ad)}${acik ? `<small>${kac(acik)}</small>` : ''}</span>
  </label>`;
}

export function alan({id, ad, ipucu = '', ic}) {
  return `<div class="alan">
    <label class="alan-ad" for="${kac(id)}">${kac(ad)}</label>
    ${ic}
    ${ipucu ? `<span class="alan-ipucu" id="${kac(id)}-ipucu">${kac(ipucu)}</span>` : ''}
  </div>`;
}

export function secimAlani({id, ad, ipucu = '', secenekler, deger = ''}) {
  const o = secenekler.map((s) => {
    const v = typeof s === 'string' ? s : s.id;
    const t = typeof s === 'string' ? s : s.ad;
    return `<option value="${kac(v)}" ${v === deger ? 'selected' : ''}>${kac(t)}</option>`;
  }).join('');
  return alan({id, ad, ipucu,
    ic: `<select class="secim" id="${kac(id)}" ${ipucu ? `aria-describedby="${kac(id)}-ipucu"` : ''}>${o}</select>`});
}

/** Gelismis (details) bolumu — teknik terimler YALNIZCA burada. */
export function gelismis(baslik, ic, acik = false) {
  return `<details class="gelismis" ${acik ? 'open' : ''}>
    <summary>${ikon('ok', {boyut: 16, sinif: 'ok'})}
      <span>${kac(baslik)}</span></summary>
    <div class="gelismis-ic">${ic}</div>
  </details>`;
}

/** Is/proje karti. `is` = {is_id, ad, tur, durum, yuzde, kapak} */
export function isKart(is) {
  const d = String(is.durum || '').toLowerCase();
  const bittiMi = d.includes('bitti') || d.includes('tamam') || d === 'done';
  const hataMi = d.includes('hata') || d.includes('error');
  const yuzde = Number(is.yuzde || 0);
  const durumEtiket = hataMi ? etiket('Hata', 'hata')
    : bittiMi ? etiket('Tamamlandı', 'iyi')
      : etiket(is.durum ? String(is.durum) : 'Üretimde', 'uyari');
  return `<article class="iskart">
    <div class="iskart-kapak">${is.kapak
      ? `<img src="${kac(is.kapak)}" alt="" loading="lazy">`
      : ikon('video', {boyut: 26})}</div>
    <h3 class="iskart-ad" title="${kac(is.ad || is.is_id)}">${kac(is.ad || is.is_id)}</h3>
    <div class="iskart-satir">${durumEtiket}
      ${is.tur ? etiket(is.tur) : ''}</div>
    ${!bittiMi && !hataMi
      ? `<div class="ilerleme" role="progressbar" aria-valuenow="${yuzde}"
            aria-valuemin="0" aria-valuemax="100"><i style="width:${
        Math.max(2, Math.min(100, yuzde))}%"></i></div>`
      : ''}
    <div class="iskart-satir kucuk sessiz tekfont">
      <span>${kac(is.is_id)}</span></div>
  </article>`;
}

/** Ozet satiri. `hesaplanacak: true` -> UYDURMA SAYI YOK. */
export function ozetSatir(ad, deger, {hesaplanacak = false} = {}) {
  return `<div class="ozet-satir"><span class="ad">${kac(ad)}</span>
    <span class="deg ${hesaplanacak ? 'hesaplanacak' : 'tekfont'}">${
    kac(deger)}</span></div>`;
}

/** Ekran okuyucuya duyur. */
export function duyur(metin) {
  const el = document.getElementById('duyuru');
  if (el) el.textContent = metin;
}

/** Radyo grubunda tikla-sec davranisini bagla. */
export function grupBagla(kok, grup, geriCagri) {
  $$(`.seckart[data-grup="${grup}"], .cip[data-grup="${grup}"]`, kok)
    .forEach((b) => {
      b.addEventListener('click', () => {
        $$(`[data-grup="${grup}"]`, kok).forEach((x) =>
          x.setAttribute('aria-pressed', 'false'));
        b.setAttribute('aria-pressed', 'true');
        geriCagri(b.dataset.deger, b);
      });
    });
}
