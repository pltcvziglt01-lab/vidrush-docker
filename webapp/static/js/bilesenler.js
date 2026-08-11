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

/**
 * Yukleniyor iskeleti.
 * ⚠ Yukseklik INLINE STIL ile verilmiyor (kural: CSS siniflari). Cagiranlarin
 * kullandigi degerler dort kademeye yuvarlaniyor.
 */
export function yukleniyor(adet = 3, yukseklik = 96) {
  const kademe = yukseklik <= 70 ? 's' : yukseklik <= 100 ? 'm'
    : yukseklik <= 130 ? 'l' : 'xl';
  return `<div class="izgara izgara-3" aria-busy="true" aria-label="Yükleniyor">` +
    Array.from({length: adet}, () =>
      `<div class="iskelet iskelet-${kademe}"></div>`).join('') +
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
    <p class="kucuk orta dar-metin">${kac(aciklama)}</p>
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

/**
 * Is/proje karti.
 *
 * ⚠ FAZ H — IKI KOK NEDEN DUZELTILDI:
 *  1. Ilerleme `is.yuzde`den okunuyordu ama sunucu `ilerleme` donduruyordu ->
 *     cubuk HER ZAMAN %0 idi. Artik sozlesme alani `progress` birincil,
 *     `ilerleme`/`yuzde` yedek.
 *  2. Tamamlanan iste OYNAT/INDIR YOKTU — uretilen video arayuzden hic
 *     acilamiyordu. Artik `video_url` varsa oynatici + indirme baglantisi var.
 *
 * ⚠ UYDURMA YOK: aşama/QA/kaynak yalnizca sunucu gonderdiyse cizilir.
 */
export function isKart(is) {
  const durumHam = String(is.status || is.durum || '').toLowerCase();
  const bittiMi = durumHam === 'done' || durumHam.includes('bitti') ||
    durumHam.includes('tamam');
  const hataMi = durumHam === 'error' || durumHam.includes('hata');
  const yuzde = Math.max(0, Math.min(100, Number(
    is.progress ?? is.ilerleme ?? is.yuzde ?? 0)));
  const isId = is.job_id || is.is_id || is.id || '';
  const video = is.video_url || is.video || '';
  const kapak = is.cover_url || is.kapak || '';
  const hata = is.error || is.hata || '';
  const uyari = is.warning || is.uyari || '';
  const dususler = Array.isArray(is.fallbacks) ? is.fallbacks : [];
  const kaynakSayi = Number(is.research?.kaynak_sayisi ?? 0);
  const olguSayi = Number(is.research?.dogrulanmis_iddia ?? 0);

  const durumEtiket = hataMi ? etiket('Hata', 'hata')
    : bittiMi ? etiket('Tamamlandı', 'iyi')
      : etiket(is.stage_ad || (durumHam === 'queued' ? 'Sırada' : 'Üretimde'),
        'uyari');

  const kuyrukNot = (!bittiMi && !hataMi && is.queue_position)
    ? `<span class="kucuk sessiz">Kuyrukta ${kac(String(is.queue_position))}${
      is.queue_total ? '/' + kac(String(is.queue_total)) : ''}</span>` : '';

  return `<article class="iskart" data-is="${kac(isId)}">
    <div class="iskart-kapak">${kapak
      ? `<img src="${kac(kapak)}" alt="" loading="lazy">`
      : ikon('video', {boyut: 26})}</div>
    <h3 class="iskart-ad" title="${kac(is.ad || isId)}">${kac(is.ad || isId)}</h3>
    <div class="iskart-satir">${durumEtiket}
      ${is.tur ? etiket(is.tur) : ''}${kuyrukNot}</div>
    ${!bittiMi && !hataMi ? `
      <progress class="ilerleme" max="100" value="${yuzde}">${yuzde}%</progress>
      <div class="kucuk sessiz">${kac(is.message || is.mesaj || '')}</div>` : ''}
    ${hataMi && hata
      ? `<p class="kucuk hata-yazi">${kac(String(hata).slice(0, 220))}</p>` : ''}
    ${bittiMi && video ? `
      <video class="iskart-oynatici" controls preload="none"
        ${kapak ? `poster="${kac(kapak)}"` : ''}
        src="${kac(video)}"></video>
      <div class="iskart-eylem">
        <a class="dugme dugme-ana" href="${kac(video)}" download>
          ${ikon('yukle', {boyut: 16})} Videoyu indir</a>
        ${is.research?.manifest
          ? `<a class="dugme dugme-hayalet" href="ciktilar/${
            kac(is.research.manifest)}" download>
            ${ikon('bilgi', {boyut: 16})} Araştırma manifesti</a>` : ''}
      </div>` : ''}
    ${bittiMi && (kaynakSayi || olguSayi) ? `
      <div class="iskart-satir kucuk orta">
        ${etiket(`${kaynakSayi} kaynak`)}${etiket(`${olguSayi} doğrulanmış olgu`)}
      </div>` : ''}
    ${uyari ? uyariKutu(kac(uyari), 'uyari') : ''}
    ${dususler.length ? `
      <details class="gelismis iskart-dusus">
        <summary><span>Kalite notları (${dususler.length})</span></summary>
        <div class="gelismis-ic"><ul class="kucuk orta">${dususler.map((f) =>
          `<li><strong>${kac(f.asama || '')}</strong>: ${kac(f.etki || '')}
           <span class="sessiz">(${kac(f.neden || '')})</span></li>`).join('')}
        </ul></div>
      </details>` : ''}
    <div class="iskart-satir kucuk sessiz tekfont">
      <span>${kac(isId)}</span></div>
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
