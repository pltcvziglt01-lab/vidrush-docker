/**
 * GORUNUMLER — Ana Sayfa · Projeler/Videolar · Sablonlar · Ayarlar
 *
 * ⚠ YANLIS METIN DUZELTMELERI (UX_DENETIM.md §8 — kodla dogrulandi):
 *   1. Magnific "calisiyor" gibi gosterilmiyor; API'nin bozuk oldugu yaziyor.
 *   2. Belgeselde "footage bulunamazsa AI gorsel yedegi" YOK — belgeselde
 *      yapay gorsel YASAK (`gorsel_yasak: True`).
 *   3. YouTube kaynagi "herhangi bir video" DEGIL: yalnizca Creative Commons,
 *      lisans video bazinda dogrulaniyor (`kaynak.py:_lisans_cc_mi`).
 *   4. Telifli indirme secenek gibi SUNULMUYOR (kod zaten CC disina cikmiyor).
 *   5. Footage zinciri gercek sirayla: Pexels -> Pixabay -> Coverr -> YouTube(CC).
 *   6. Sunucu/yenileme tarihi gibi altyapi bilgisi kullanici yuzune KONULMUYOR.
 */
import {UCLAR, getirSessiz, isDurumu, islerListesi, oturumId,
        yol} from './api.js';
import {taslak, taslakVarMi, yerelIsler} from './durum.js';
import {$, $$, durumBlok, etiket, isKart, kac, uyariKutu,
        yukleniyor} from './bilesenler.js';
import {ikon, ikonlariBagla} from './ikon.js';

/* ════════════════ ANA SAYFA ════════════════ */

export async function anaSayfa(kap) {
  const t = taslak();
  const devamVar = taslakVarMi();
  kap.innerHTML = `
  <section class="kahraman">
    <h1>Konu ver, videoyu kuralım</h1>
    <p>Araştırma, gerçek görüntü seçimi, kurgu, ses ve altyazı tek akışta.
      İlk taslağı bir dakikada başlatabilirsin.</p>
    <div class="kahraman-eylem">
      <a class="dugme dugme-ana dugme-buyuk" href="#/yeni">
        ${ikon('arti', {boyut: 18})} Yeni proje başlat</a>
      ${devamVar ? `<a class="dugme dugme-hayalet" href="#/yeni">
        ${ikon('kalem', {boyut: 17})} Taslağa devam et${
        t.tur ? ` · ${kac(t.tur)}` : ''}</a>` : ''}
    </div>
    <ul class="kahraman-adim">
      <li><span class="kahraman-no">1</span><span>Türü ve konuyu ver</span></li>
      <li><span class="kahraman-no">2</span><span>Görsel yönü seç</span></li>
      <li><span class="kahraman-no">3</span><span>Özeti onayla, üretim başlasın</span></li>
    </ul>
  </section>

  <div class="bolum-bas">
    <h2>Son işler</h2>
    <a class="kucuk orta baglanti" href="#/projeler">
      Tümü</a>
  </div>
  <div id="anaIsler">${yukleniyor(3, 150)}</div>

  <div class="bolum-bas"><h2>Sistem durumu</h2></div>
  <div id="anaSaglik">${yukleniyor(1, 64)}</div>`;
  ikonlariBagla(kap);
  islerBolumu($('#anaIsler'), 3, {poll: true});
  saglikBolumu($('#anaSaglik'));
}

/* ════════════════ ISLER (paylasilan) ════════════════ */

/**
 * `/api/isler` BIRINCIL kaynak, localStorage YEDEK.
 * ⚠ Eski surumde liste YALNIZCA localStorage'dan geliyordu; baska cihazda bos
 * gorunuyor ve kullanici islerini kaybettigini saniyordu. Hangi kaynagin
 * kullanildigi artik ekranda YAZILI.
 */
/**
 * ⚠ FAZ H — CANLI TAKIP.
 * Onceden Projeler ekrani BIR KEZ ciziliyor ve hic yenilenmiyordu; `isDurumu()`
 * tanimliydi ama hicbir yerden cagrilmiyordu. Kullanici uretimin ilerledigini
 * ancak sayfayi elle yenileyerek gorebiliyordu.
 * Artik: aktif is varsa POLL_MS'de bir `/api/job/{id}` cagrilir.
 * Sekme arka plandaysa poll DURUR (bosa istek atmaz), one gelince devam eder.
 */
const POLL_MS = 4000;
let _pollZaman = null;

export function pollDurdur() {
  if (_pollZaman) { clearTimeout(_pollZaman); _pollZaman = null; }
}

/** Bir isin bittigi/hata aldigi. Aktif isler icin poll surer. */
function bitmisMi(is) {
  const d = String(is.status || is.durum || '').toLowerCase();
  return d === 'done' || d === 'error' || d.includes('bitti') || d.includes('hata');
}

async function islerBolumu(kap, sinir = 0, {poll = false} = {}) {
  if (!kap) return;
  const yerel = yerelIsler();
  let sunucu = null;
  let hata = '';
  try {
    const v = await islerListesi();
    sunucu = Array.isArray(v) ? v
      : Array.isArray(v?.isler) ? v.isler
        : Array.isArray(v?.liste) ? v.liste : [];
  } catch (e) {
    hata = String(e.message || e);
  }

  const harita = new Map();
  (sunucu || []).forEach((x) => {
    // ⚠ FAZ H: `job_id` sozlesmenin BIRINCIL adi; eskiler yedek.
    const id = x.job_id || x.is_id || x.id || x.job;
    if (id) harita.set(id, {...x, is_id: id, job_id: id, _kaynak: 'sunucu'});
  });
  yerel.forEach((x) => {
    if (x.is_id && !harita.has(x.is_id)) {
      harita.set(x.is_id, {...x, _kaynak: 'yerel'});
    }
  });
  let liste = Array.from(harita.values());
  if (sinir) liste = liste.slice(0, sinir);

  if (!liste.length) {
    kap.innerHTML = hata
      ? durumBlok({
        tur: 'hata',
        baslik: 'İş listesi alınamadı',
        aciklama: `Sunucuya ulaşılamıyor (${hata}). Bu tarayıcıda kayıtlı ` +
          'iş de bulunmadı. Sunucu çalışıyorsa sayfayı yenilemeyi dene.',
        eylem: `<button type="button" class="dugme" data-yenile="isler">
          ${ikon('yenile', {boyut: 17})} Yeniden dene</button>`,
      })
      : durumBlok({
        baslik: 'Henüz iş yok',
        aciklama: 'İlk projeni oluşturduğunda burada görünecek.',
        eylem: `<a class="dugme dugme-ana" href="#/yeni">
          ${ikon('arti', {boyut: 17})} Yeni proje</a>`,
      });
    ikonlariBagla(kap);
    const y = $('[data-yenile="isler"]', kap);
    if (y) y.addEventListener('click', () => {
      kap.innerHTML = yukleniyor(2, 120);
      islerBolumu(kap, sinir);
    });
    return;
  }

  const yalnizYerel = !sunucu && liste.length;
  kap.innerHTML = `
    ${yalnizYerel ? uyariKutu(
      'Sunucu listesine ulaşılamadı; aşağıdakiler <strong>bu tarayıcıda' +
      '</strong> kayıtlı işler. Başka cihazda görünmezler.', 'uyari') : ''}
    <div class="izgara izgara-3 ${yalnizYerel ? 'ust-bosluk' : ''}">
      ${liste.map(isKart).join('')}
    </div>`;
  ikonlariBagla(kap);

  if (poll && liste.some((x) => !bitmisMi(x))) {
    isleriTazele(kap, liste, sinir);
  }
}

/**
 * Aktif isleri TEK TEK `/api/job/{id}` ile tazele ve karti YERINDE guncelle.
 * Tum listeyi yeniden cizmiyoruz: kullanici bir videoyu oynatiyorsa
 * `innerHTML` degisimi oynaticiyi sifirlardi.
 */
function isleriTazele(kap, liste, sinir) {
  pollDurdur();
  _pollZaman = setTimeout(async () => {
    // Kap DOM'dan cikmissa (baska ekrana gecildi) poll'u birak.
    if (!kap.isConnected) { pollDurdur(); return; }
    // Sekme arka plandaysa istek atma, bir tur sonra tekrar bak.
    if (document.hidden) { isleriTazele(kap, liste, sinir); return; }

    const aktif = liste.filter((x) => !bitmisMi(x));
    let degisti = false;
    await Promise.all(aktif.map(async (x) => {
      const id = x.job_id || x.is_id;
      if (!id) return;
      try {
        const yeni = await isDurumu(id);
        const birlesik = {...x, ...yeni, ad: x.ad, tur: x.tur || yeni.tur};
        const i = liste.indexOf(x);
        if (i >= 0) liste[i] = birlesik;
        const kart = kap.querySelector(`[data-is="${CSS.escape(id)}"]`);
        if (kart) {
          kart.outerHTML = isKart(birlesik);
          degisti = true;
        }
      } catch {
        // ⚠ Ag kesintisi TAKIBI DURDURMAZ. Kart eski haliyle kalir ve bir
        // sonraki turda yeniden denenir; sahte "hata" durumu YAZILMAZ.
      }
    }));
    if (degisti) ikonlariBagla(kap);
    if (liste.some((x) => !bitmisMi(x))) isleriTazele(kap, liste, sinir);
    else pollDurdur();
  }, POLL_MS);
}

/* ════════════════ PROJELER / VIDEOLAR ════════════════ */

export async function projeler(kap) {
  kap.innerHTML = `<div class="sayfa-bas">
    <div class="sayfa-bas-yazi">
      <h1>Projeler ve videolar</h1>
      <p>Sunucudaki işler ve bu tarayıcıda kayıtlı olanlar birlikte listelenir.</p>
    </div>
    <a class="dugme dugme-ana" href="#/yeni">${ikon('arti', {boyut: 17})}
      Yeni proje</a>
  </div>
  <div id="prjIsler">${yukleniyor(6, 150)}</div>`;
  ikonlariBagla(kap);
  islerBolumu($('#prjIsler'), 0, {poll: true});
}

/* ════════════════ SABLONLAR ════════════════ */

export async function sablonlar(kap) {
  kap.innerHTML = `<div class="sayfa-bas"><div class="sayfa-bas-yazi">
    <h1>Şablonlar</h1>
    <p>Edit şablonları kurgu temposunu, yazı düzenini ve renk yönünü belirler.
      Seçim, Yeni Proje'nin 3. adımında yapılır.</p></div></div>
  <div id="sbListe">${yukleniyor(6, 120)}</div>`;
  ikonlariBagla(kap);

  const kutu = $('#sbListe');
  const [edit, anim] = await Promise.all([
    getirSessiz(UCLAR.editStilleri), getirSessiz(UCLAR.animasyonStilleri)]);

  const coz = (s) => {
    if (!s.ok) return null;
    const v = s.veri;
    return Array.isArray(v) ? v
      : Array.isArray(v?.liste) ? v.liste
        : Array.isArray(v?.stiller) ? v.stiller : [];
  };
  const e = coz(edit);
  const a = coz(anim);

  if (!e && !a) {
    kutu.innerHTML = durumBlok({
      tur: 'hata', baslik: 'Şablonlar alınamadı',
      aciklama: `Sunucuya ulaşılamıyor (${kac(edit.hata || '')}). ` +
        'Üretim yine varsayılan şablonla çalışır.',
    });
    ikonlariBagla(kutu);
    return;
  }

  const grup = (baslik, liste, ikonAd) => !liste || !liste.length ? '' : `
    <div class="bolum-bas"><h2>${kac(baslik)}</h2>
      <span class="kucuk sessiz">${liste.length} şablon</span></div>
    <div class="izgara izgara-3">${liste.map((s) => `
      <article class="kart kart-sik">
        <div class="seckart-bas">${ikon(ikonAd, {boyut: 19})}
          <span class="seckart-ad">${kac(s.ad ?? s.id ?? s)}</span></div>
        <p class="kucuk orta ust-bosluk-kucuk">${
          kac(s.ozet || s.aciklama || 'Açıklama yok.')}</p>
      </article>`).join('')}</div>`;

  kutu.innerHTML = grup('Belgesel ve hikâye', e, 'sablon') +
    grup('Animasyon', a, 'animasyon');
  ikonlariBagla(kutu);
}

/* ════════════════ SISTEM DURUMU ════════════════ */

async function saglikBolumu(kap) {
  if (!kap) return;
  const s = await getirSessiz(UCLAR.saglik);
  const pul = $('#saglikPul');
  const nokta = pul ? $('.pul-nokta', pul) : null;
  const yazi = pul ? $('.pul-yazi', pul) : null;

  if (!s.ok) {
    if (nokta) nokta.dataset.durum = 'hata';
    if (yazi) yazi.textContent = 'Sunucuya ulaşılamıyor';
    kap.innerHTML = durumBlok({
      tur: 'hata', baslik: 'Sunucu durumu okunamadı',
      aciklama: `${kac(s.hata)} — arayüz çalışıyor ama üretim başlatılamaz.`,
    });
    ikonlariBagla(kap);
    return;
  }

  const v = s.veri || {};
  // ⚠ FAZ H — YANLIS POZITIF KAPATILDI.
  // Eski satir: `String(v.durum ?? v.status ?? 'ok')` — yani sunucu `durum`
  // alani DONDURMEZSE 'ok' VARSAYIYORDU. `/api/saglik` o alani hic
  // dondurmuyordu; sonuc olarak ffmpeg/renderer/disk cokse bile ust barda
  // "Sistem hazir" yaziyordu.
  // Yeni kural: durum alani YOKSA "bilinmiyor" denir, hazir DENMEZ.
  const ham = String(v.durum ?? v.status ?? '').toLowerCase();
  const DURUMLAR = {
    hazir: {pul: 'iyi', yazi: 'Sistem hazır'},
    kisitli: {pul: 'uyari', yazi: 'Kısıtlı çalışıyor'},
    kullanilamiyor: {pul: 'hata', yazi: 'Üretim kullanılamıyor'},
  };
  const d = DURUMLAR[ham] ||
    {pul: 'uyari', yazi: 'Durum bilinmiyor'};
  if (nokta) nokta.dataset.durum = d.pul;
  if (yazi) yazi.textContent = d.yazi;

  const derin = await getirSessiz(UCLAR.saglikDerin);
  const dv = derin.ok ? (derin.veri || {}) : {};
  const bilesenler = dv.bilesenler || {};
  const satir = (ad, ok, not) => `<div class="durum-satir">
    <span class="pul-nokta" data-durum="${ok ? 'iyi' : 'hata'}"></span>
    <span class="ad">${kac(ad)}</span>
    <span class="kucuk orta">${kac(not || (ok ? 'çalışıyor' : 'yok'))}</span>
  </div>`;

  kap.innerHTML = `
    ${ham === 'kullanilamiyor'
      ? uyariKutu(`<strong>Video üretilemez.</strong> ${kac(v.ozet || '')}`,
        'hata')
      : ham === 'kisitli'
        ? uyariKutu(kac(v.ozet || 'Bazı bileşenler eksik.'), 'uyari')
        : ham === 'hazir'
          ? uyariKutu(kac(v.ozet || 'Tüm bileşenler çalışıyor.'), 'bilgi')
          : uyariKutu('Sunucu durum alanı döndürmedi; sistemin hazır olduğu ' +
            '<strong>varsayılmıyor</strong>.', 'uyari')}
    ${Object.keys(bilesenler).length ? `<div class="durum-liste ust-bosluk">
      ${Object.entries(bilesenler).map(([k, b]) => satir(
        k.replace(/_/g, ' '), b && b.ok,
        (b && (b.detay || b.surum)) || '')).join('')}
    </div>` : (derin.ok ? '' : uyariKutu(
      `Ayrıntılı ölçüm alınamadı (${kac(derin.hata || '')}).`, 'uyari'))}
    ${Array.isArray(dv.eksik_opsiyonel) && dv.eksik_opsiyonel.length
      ? `<p class="kucuk orta ust-bosluk-kucuk">Kısıtlayan eksikler: ${
        kac(dv.eksik_opsiyonel.join(', '))}</p>` : ''}`;
  ikonlariBagla(kap);
}

/* ════════════════ AYARLAR ════════════════ */

/**
 * Medya kaynak zinciri — GERCEK kodla uyumlu.
 * `kaynak.footage_getir` sirasi: Pexels -> Pixabay -> Coverr -> YouTube(CC).
 * Faz B avcisi ayrica: Wikimedia, Openverse, Library of Congress, Archive.org.
 */
const KAYNAK_ZINCIRI = [
  {ad: 'Pexels', not: 'Stok video/görsel. 4K tercih edilir.', durum: 'iyi'},
  {ad: 'Pixabay', not: 'Stok video/görsel yedeği.', durum: 'iyi'},
  {ad: 'Coverr', not: 'Stok video yedeği.', durum: 'iyi'},
  {ad: 'YouTube (yt-dlp)', durum: 'uyari',
   not: 'YALNIZCA Creative Commons lisanslı videolar. Lisans video bazında ' +
        'tek tek doğrulanır; CC olmayan içerik indirilmez.'},
  {ad: 'Wikimedia Commons', not: 'Arşiv görseli; lisans öğeye göre doğrulanır.',
   durum: 'iyi'},
  {ad: 'Openverse', not: 'Açık lisanslı görsel toplayıcı.', durum: 'iyi'},
  {ad: 'Library of Congress', durum: 'uyari',
   not: 'Haklar alanı yalnızca öğe ayrıntısında gelir; ek istek gerekir.'},
  {ad: 'Internet Archive', not: 'Lisans URL\'si zorunlu tutulur.', durum: 'iyi'},
];

const ENTEGRASYONLAR = [
  {ad: 'Magnific (yükseltme)', durum: 'hata',
   not: 'API şu an ÇALIŞMIYOR — anahtar üretilemiyor. Arayüzde seçenek olarak ' +
        'sunulmuyor.'},
  {ad: 'Remotion render', durum: 'iyi',
   not: 'Yerel render. Mevcut kompozisyon: VidrushVideo.'},
  {ad: 'Yerel TTS (macOS say)', durum: 'iyi',
   not: 'Ücretsiz, yapay ses. İnsan seslendirmesi değildir.'},
];

export async function ayarlar(kap) {
  kap.innerHTML = `<div class="sayfa-bas"><div class="sayfa-bas-yazi">
    <h1>Ayarlar</h1>
    <p>Teknik ayrıntılar ve entegrasyon durumları burada. Üretim seçimleri
      Yeni Proje içinde yapılır.</p></div></div>

  <div class="bolum-bas"><h2>Medya kaynakları</h2></div>
  <div class="veri-liste">${KAYNAK_ZINCIRI.map((k) => `
    <div class="veri-satir">
      <div class="bas"><span class="pul-nokta" data-durum="${k.durum}"></span>
        <strong>${kac(k.ad)}</strong>
        ${k.durum === 'uyari' ? etiket('koşullu', 'uyari') : ''}</div>
      <p class="kucuk orta">${kac(k.not)}</p>
    </div>`).join('')}</div>
  <div class="ust-bosluk">${uyariKutu(
    'Arama sırası: <strong>Pexels → Pixabay → Coverr → YouTube (yalnızca CC)' +
    '</strong>. Belgeselde yapay zekâ görseli <strong>üretilmez</strong>; ' +
    'uygun gerçek görüntü bulunamazsa sahne kapsam boşluğu olarak işaretlenir.',
    'bilgi')}</div>

  <div class="bolum-bas"><h2>Entegrasyonlar</h2></div>
  <div class="veri-liste">${ENTEGRASYONLAR.map((k) => `
    <div class="veri-satir">
      <div class="bas"><span class="pul-nokta" data-durum="${k.durum}"></span>
        <strong>${kac(k.ad)}</strong>
        ${k.durum === 'hata' ? etiket('çalışmıyor', 'hata') : ''}</div>
      <p class="kucuk orta">${kac(k.not)}</p>
    </div>`).join('')}</div>

  <div class="bolum-bas"><h2>Marka kitleri</h2></div>
  <div id="ayProfiller">${yukleniyor(2, 74)}</div>

  <div class="bolum-bas"><h2>Sistem durumu</h2></div>
  <div id="aySaglik">${yukleniyor(1, 64)}</div>

  <div class="bolum-bas"><h2>Kullanım ve maliyet</h2></div>
  ${uyariKutu('Maliyet, üretim sırasında gerçek kullanıma göre ölçülür. ' +
    'Burada sabit bir fiyat listesi göstermiyoruz; eski sürümdeki rakamlar ' +
    'güncel değildi.', 'bilgi')}

  <div class="bolum-bas"><h2>Bu tarayıcı</h2></div>
  <div class="veri-liste">
    <div class="veri-satir"><div class="bas"><strong>Oturum kimliği</strong></div>
      <p class="kucuk orta tekfont">${kac(oturumId())}</p></div>
    <div class="veri-satir"><div class="bas"><strong>Yerel kayıtlar</strong></div>
      <p class="kucuk orta">${yerelIsler().length} iş kaydı ·
        ${taslakVarMi() ? 'kayıtlı taslak var' : 'taslak yok'}</p></div>
  </div>`;
  ikonlariBagla(kap);
  saglikBolumu($('#aySaglik'));
  profilBolumu($('#ayProfiller'));
}

async function profilBolumu(kap) {
  if (!kap) return;
  const s = await getirSessiz(UCLAR.profiller);
  if (!s.ok) {
    kap.innerHTML = durumBlok({
      tur: 'hata', baslik: 'Marka kitleri alınamadı',
      aciklama: `Sunucuya ulaşılamıyor (${kac(s.hata)}).`,
    });
    ikonlariBagla(kap);
    return;
  }
  const v = s.veri;
  const liste = Array.isArray(v) ? v
    : Array.isArray(v?.profiller) ? v.profiller
      : Array.isArray(v?.liste) ? v.liste : [];
  if (!liste.length) {
    kap.innerHTML = durumBlok({
      baslik: 'Marka kiti yok',
      aciklama: 'Marka kiti, videolar arasında renk ve karakter tutarlılığını ' +
        'sağlar. Üretim sırasında oluşturulabilir.',
    });
    ikonlariBagla(kap);
    return;
  }
  kap.innerHTML = `<div class="veri-liste">${liste.map((p) => `
    <div class="veri-satir"><div class="bas">${ikon('kanal', {boyut: 18})}
      <strong>${kac(p.ad ?? p.pid ?? p)}</strong>
      <span class="kucuk sessiz tekfont">${kac(p.pid ?? '')}</span></div>
      ${p.ozet ? `<p class="kucuk orta">${kac(p.ozet)}</p>` : ''}
    </div>`).join('')}</div>`;
  ikonlariBagla(kap);
}

export {saglikBolumu};
