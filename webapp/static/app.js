/**
 * BEDOSAHO AI — arayuz giris noktasi (Faz F).
 * Hash tabanli yonlendirici + gezinme. Framework/bagimlilik YOK.
 *
 * BILGI MIMARISI (5 oge — eski surumde 8 oge vardi ve 4'u ayni isi yapiyordu):
 *   Ana Sayfa · Yeni Proje · Projeler · Sablonlar · Ayarlar
 * Animasyon/Hikaye/Belgesel ayri menu DEGIL; Yeni Proje'nin 1. adiminda tur.
 */
import {ikon, ikonlariBagla} from './js/ikon.js';
import {anaSayfa, ayarlar, projeler, sablonlar} from './js/gorunumler.js';
import {wizardCiz} from './js/wizard.js';
import {duyur} from './js/bilesenler.js';

const EKRANLAR = [
  {id: 'ana', ad: 'Ana Sayfa', ikon: 'ana', ciz: anaSayfa, altnav: true},
  {id: 'yeni', ad: 'Yeni Proje', ikon: 'arti', ciz: wizardCiz, altnav: true},
  {id: 'projeler', ad: 'Projeler', ikon: 'proje', ciz: projeler, altnav: true},
  {id: 'sablonlar', ad: 'Şablonlar', ikon: 'sablon', ciz: sablonlar},
  {id: 'ayarlar', ad: 'Ayarlar', ikon: 'ayar', ciz: ayarlar, altnav: true},
];

function menuCiz() {
  const yan = document.getElementById('yanMenu');
  if (yan) {
    yan.innerHTML = EKRANLAR.map((y) => `<li><a class="yanmenu-oge"
      href="#/${y.id}" data-yol="${y.id}">
      <span class="yanmenu-im">${ikon(y.ikon, {boyut: 18})}</span>
      <span>${y.ad}</span></a></li>`).join('');
  }
  const alt = document.getElementById('altNav');
  if (alt) {
    alt.innerHTML = EKRANLAR.filter((y) => y.altnav).map((y) => `<li>
      <a class="altnav-oge" href="#/${y.id}" data-yol="${y.id}">
        ${ikon(y.ikon, {boyut: 21})}<span>${y.ad.replace(' Proje', '')}</span>
      </a></li>`).join('');
  }
}

function etkinIsaretle(id) {
  document.querySelectorAll('[data-yol]').forEach((a) => {
    if (a.dataset.yol === id) a.setAttribute('aria-current', 'page');
    else a.removeAttribute('aria-current');
  });
}

function coz() {
  const h = (location.hash || '').replace(/^#\/?/, '');
  const [id, ek] = h.split('/');
  const y = EKRANLAR.find((x) => x.id === id) || EKRANLAR[0];
  return {yol: y, ek};
}

let cizimSayaci = 0;

async function yonlendir() {
  const {yol: y, ek} = coz();
  const kap = document.getElementById('gorunumKap');
  if (!kap) return;
  etkinIsaretle(y.id);
  document.title = `${y.ad} · BEDOSAHO AI`;

  const benimSira = ++cizimSayaci;
  try {
    await y.ciz(kap, {adimNo: ek});
  } catch (e) {
    // ⚠ Gorunum cokerse BOS EKRAN BIRAKMA — dürüst hata durumu goster.
    console.error('[yonlendir] gorunum cizilemedi', e);
    if (benimSira === cizimSayaci) {
      kap.innerHTML = `<div class="durum-blok hata">
        ${ikon('hata', {boyut: 26})}
        <h3>Bu ekran yüklenemedi</h3>
        <p class="kucuk orta">${String(e.message || e).slice(0, 200)}</p>
        <button type="button" class="dugme" id="hataYenile">Yeniden dene</button>
      </div>`;
      const b = document.getElementById('hataYenile');
      if (b) b.addEventListener('click', yonlendir);
    }
  }
  if (benimSira !== cizimSayaci) return;
  ikonlariBagla(kap);
  duyur(`${y.ad} ekranı`);
  // Yeni ekranda odagi ana icerige tasi (klavye kullanicisi bastan baslar)
  const ana = document.getElementById('anaicerik');
  if (ana && cizimSayaci > 1) ana.focus({preventScroll: true});
  window.scrollTo({top: 0, behavior: 'auto'});
}

function baslat() {
  menuCiz();
  ikonlariBagla(document);
  if (!location.hash) location.replace('#/ana');
  window.addEventListener('hashchange', yonlendir);
  yonlendir();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', baslat);
} else {
  baslat();
}

// Denetim/test icin
window.BEDOSAHO = {EKRANLAR: EKRANLAR.map((y) => y.id), yonlendir};
