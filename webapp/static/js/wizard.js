/**
 * YENI PROJE — TEK AKIS (20 Agu 2026, urun pivotu).
 *
 * ⚠ ESKI 5 ADIMLI WIZARD KALDIRILDI (kullanici karari: "tek yeni akis,
 * eskiler kalksin"). Tur/stil/palet/isik/arkaplan secimleri ARTIK YOK;
 * uretim hattinin tek yolu var:
 *
 *   metin -> cumle basina 5-7 sn sahne -> her sahne icin ONCE gercek stok
 *   video, bulunamazsa Magnific (nano-banana) 16:9 AI gorseli + sinematik
 *   Remotion gecisleri; AI video klipler sunucu tavanina kadar (MAG_KLIP_MAKS).
 *
 * Backend sozlesmesi DEGISMEDI: ayni /api/generate, tur=documentary,
 * edit=akis sabit gonderilir. `basit.js` / `secim-deneyimi.js` artik bu
 * ekrandan IMPORT EDILMEZ (asamali sokum; dosyalar eski testlerin kaydi
 * olarak duruyor).
 *
 * ⚠ UYDURMA DEGER YOK: maliyet/kaynak sayisi gibi backend'in olcmedigi
 * hicbir sey ekranda tahmin olarak gosterilmez.
 */
import {UCLAR, getirSessiz, isKimligiCoz, uretimBaslat} from './api.js';
import {dosyalariTemizle, taslak, taslakSil, taslakYaz,
        yerelIsEkle} from './durum.js';
import {$, duyur, kac, yukleniyor} from './bilesenler.js';
import {ikonlariBagla} from './ikon.js';

const YERTUTUCU =
  'Konuyu bir paragrafla anlat ya da hazır anlatım metnini yapıştır…\n\n' +
  'Örnek: Apollo 11 inişindeki kritik son dakikalar — 1202 program alarmı, ' +
  'yarı-elle kontrol, Tranquility Base.';

/** Tek akisin SABIT uretim parametreleri — kullanici secimi DEGIL. */
const AKIS = {tur: 'documentary', edit: 'akis'};

let kaynak = {};          // {sesler: [...]} — bir kez yuklenir
let adim = 1;             // eski export sozlesmesi icin (tek ekran = hep 1)

/* ════════════════ ESKI EXPORT SOZLESMESI ════════════════ */

/** Tek ekran: yalnizca metin zorunlu. (Eski cok-adimli imza korunuyor.) */
export function adimGecerli(_n) {
  const konu = (taslak().konu || '').trim();
  return konu.length >= 20
    ? {ok: true}
    : {ok: false, sebep: 'Metin en az 20 karakter olmalı.'};
}

export function wizardAdim() { return adim; }
export function wizardKaynakHatalari() { return kaynak.hatalar || []; }

/** /api/generate degerleri — GENERATE_ALANLARI adlariyla birebir. */
function generateDegerleri() {
  const t = taslak();
  const d = {
    story: (t.konu || '').trim(),
    tur: AKIS.tur,
    edit: AKIS.edit,
    sure_dk: String(t.sure || 2),
    gecis: '1',
    zoom: '1',
    altyazi: t.altyazi === false ? '0' : '1',
  };
  if (t.ses) d.ses = t.ses;
  return d;
}
export {generateDegerleri};

/* ════════════════ EKRAN ════════════════ */

export function wizardHtml() {
  const t = taslak();
  const sesler = kaynak.sesler || [];
  return `<div class="sayfa-bas"><div class="sayfa-bas-yazi">
    <h1>Yeni Video</h1>
    <p>Metni ver — her cümle 5-7 saniyelik bir sahneye dönüşür: gerektiğinde
       gerçek stok video, gerektiğinde AI görsel, sinematik geçişlerle.</p>
  </div></div>

  <section class="kart akis-kart">
    <label class="alan-etiket" for="akMetin">Konu ya da anlatım metni</label>
    <textarea id="akMetin" class="alan akis-metin" rows="10"
      placeholder="${kac(YERTUTUCU)}">${kac(t.konu || '')}</textarea>

    <div class="akis-ayarlar">
      <div class="alan-grup">
        <label class="alan-etiket" for="akSure">Süre (dakika)</label>
        <input id="akSure" class="alan" type="number" min="1" max="30"
               step="1" value="${Number(t.sure) || 2}">
      </div>
      <div class="alan-grup">
        <label class="alan-etiket" for="akSes">Anlatıcı sesi</label>
        <select id="akSes" class="alan">
          <option value="">Otomatik (dile göre)</option>
          ${sesler.map((s) => `<option value="${kac(s.id)}"
            ${t.ses === s.id ? 'selected' : ''}>${kac(s.ad)}${
            s.ucret ? ` — ${kac(s.ucret)}` : ''}</option>`).join('')}
        </select>
      </div>
      <div class="alan-grup">
        <label class="alan-etiket" for="akAltyazi">Altyazı</label>
        <select id="akAltyazi" class="alan">
          <option value="1" ${t.altyazi === false ? '' : 'selected'}>Açık</option>
          <option value="0" ${t.altyazi === false ? 'selected' : ''}>Kapalı</option>
        </select>
      </div>
    </div>

    <div class="bilgi-kutu" role="note">
      <p class="kucuk">Akış her sahne için <strong>önce gerçek stok video</strong>
      arar; bulunamazsa <strong>AI görsel (16:9, 2K)</strong> üretir.
      AI video klipler sunucu tavanına kadar otomatik eklenir.
      Kaynak sayısı ve sahne dökümü üretim sırasında hesaplanır — burada
      tahmin gösterilmez.</p>
    </div>

    <div class="akis-alt">
      <button id="akBaslat" class="dugme dugme-ana dugme-buyuk" type="button">
        Videoyu Üret
      </button>
      <span id="wzUretimDurum" class="kucuk" role="status" aria-live="polite"></span>
    </div>
  </section>`;
}

async function uretimiBaslat(dugme) {
  const durum = $('#wzUretimDurum');
  const g = adimGecerli(1);
  if (!g.ok) {
    if (durum) durum.textContent = g.sebep;
    return;
  }
  dugme.disabled = true;
  if (durum) durum.textContent = 'Üretim başlatılıyor…';
  try {
    const cevap = await uretimBaslat(generateDegerleri());
    const isId = isKimligiCoz(cevap);
    if (!isId) throw new Error('Sunucu iş kimliği döndürmedi; üretim izlenemez.');
    yerelIsEkle({
      is_id: isId,
      ad: (taslak().konu || '').slice(0, 60) || isId,
      tur: AKIS.tur,
      durum: 'kuyrukta',
      olusturma: new Date().toISOString(),
    });
    if (durum) {
      durum.innerHTML = `<span class="iyi-yazi">Başlatıldı.</span> ` +
        `İş kimliği <strong class="tekfont">${kac(isId)}</strong>. ` +
        `<a href="#/projeler" class="baglanti">Projeler</a> ` +
        `ekranından izleyebilirsin.`;
    }
    duyur('Üretim başlatıldı');
    taslakSil();
    dosyalariTemizle();
  } catch (e) {
    dugme.disabled = false;
    if (durum) {
      durum.innerHTML = `<span class="hata-yazi">Başlatılamadı:</span> ` +
        kac(String(e.message || e).slice(0, 240));
    }
  }
}

function olaylariBagla(kap) {
  const metin = $('#akMetin', kap);
  if (metin) metin.addEventListener('input', () => taslakYaz({konu: metin.value}));
  const sure = $('#akSure', kap);
  if (sure) {
    sure.addEventListener('change', () => taslakYaz(
      {sure: Math.max(1, Math.min(30, Number(sure.value) || 2))}));
  }
  const ses = $('#akSes', kap);
  if (ses) ses.addEventListener('change', () => taslakYaz({ses: ses.value}));
  const alt = $('#akAltyazi', kap);
  if (alt) {
    alt.addEventListener('change', () => taslakYaz({altyazi: alt.value !== '0'}));
  }
  const baslat = $('#akBaslat', kap);
  if (baslat) baslat.addEventListener('click', () => uretimiBaslat(baslat));
}

export async function wizardCiz(kap, _secenek = {}) {
  kap.innerHTML = `<div class="sayfa-bas"><div class="sayfa-bas-yazi">
    <h1>Yeni Video</h1><p>Yükleniyor…</p></div></div>${yukleniyor(2, 84)}`;
  if (!kaynak.yuklendi) {
    const sesler = await getirSessiz(UCLAR.sesler);
    kaynak = {sesler: Array.isArray(sesler) ? sesler : [],
              hatalar: Array.isArray(sesler) ? [] : ['sesler yüklenemedi'],
              yuklendi: true};
  }
  kap.innerHTML = wizardHtml();
  ikonlariBagla(kap);
  olaylariBagla(kap);
  duyur('');
}
