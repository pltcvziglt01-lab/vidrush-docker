/**
 * YENI PROJE — 5 ADIMLI WIZARD
 *   1 Tur  ->  2 Konu/Icerik  ->  3 Gorsel yon  ->  4 Uretim ozeti  ->  5 Onay
 *
 * ⚠ ESKI OZELLIK KAYBI YASAK. Eski `view-studio` ("Yeni Video") ekranindaki
 * TUM kontroller burada yasiyor:
 *   sure_dk, edit/animasyon stili, profil (marka kiti), ses + ses kutuphanesi
 *   (saglayici filtresi + arama + ornek dinleme), palet + ozel hex, arkaplan,
 *   isik, gecis, zoom, altyazi + altyazi_sablon (font/boyut/renk/kontur/konum/
 *   aralik/agirlik/buyuk-harf/golge/arka), acilis (hikaye), sora (hikaye),
 *   gorsel_model, karakter + stil gorseli, sahne_ref (animasyon).
 * Teknik olanlar "Gelismis" altinda; temel akis sade kaliyor.
 *
 * ⚠ ADIM 4 KURALI: backend ucu OLMAYAN degerler (guvenilir kaynak sayisi,
 * kullanilabilir medya, tahmini maliyet) UYDURULMAZ. "Uretim sirasinda
 * hesaplanacak" diye acikca yazilir.
 */
import {GENERATE_ALANLARI, TURLER, UCLAR, getirSessiz, oturumId, uretimBaslat,
        yol} from './api.js';
import {dosyalar, dosyalariTemizle, taslak, taslakSil, taslakYaz,
        yerelIsEkle} from './durum.js';
import {$, $$, alan, anahtar, duyur, etiket, gelismis, grupBagla, kac,
        ozetSatir, secKart, secimAlani, uyariKutu, yukleniyor} from './bilesenler.js';
import {ikon, ikonlariBagla} from './ikon.js';

/** Uzun yer tutucu metinleri — sablon dizesi ICINDE kesme isareti kullanmak
 *  kacis sorunu yaratiyor, bu yuzden ayri sabit. */
const YERTUTUCU = {
  senaryo: 'Hazır anlatım metnini buraya yapıştır…',
  konu: 'Örnek: Apollo 11 inişindeki kritik son dakikalar — 1202 program ' +
        'alarmı, yarı-elle kontrol, Tranquility Base.',
};

const ADIMLAR = [
  {no: 1, ad: 'Tür', tam: 'Ne üretiyorsun?'},
  {no: 2, ad: 'İçerik', tam: 'Konu ve içerik'},
  {no: 3, ad: 'Görsel', tam: 'Görsel yön'},
  {no: 4, ad: 'Özet', tam: 'Üretim özeti'},
  {no: 5, ad: 'Onay', tam: 'Onay ve başlat'},
];

let adim = 1;
let kaynak = {};          // sunucudan gelen listeler
let sesOynatici = null;

/* ════════════════ YARDIMCILAR ════════════════ */

function turBilgi(id) {
  return TURLER.find((t) => t.id === id) || null;
}

/** Adim gecilebilir mi? Eksik zorunlu alan varsa sebebiyle birlikte doner. */
export function adimGecerli(n) {
  const t = taslak();
  if (n === 1) {
    return t.tur ? {ok: true} : {ok: false, sebep: 'Bir tür seç.'};
  }
  if (n === 2) {
    const konu = (t.konu || '').trim();
    if (konu.length < 20) {
      return {ok: false, sebep: 'Konu/metin en az 20 karakter olmalı.'};
    }
    // ⚠ Animasyonda referans kare ZORUNLU: sunucu aksi halde 400 donuyor.
    if (t.tur === 'animasyon' && dosyalar.sahneRef.length === 0) {
      return {ok: false, sebep: 'Animasyon için en az 1 referans kare gerekli.'};
    }
    return {ok: true};
  }
  return {ok: true};
}

function ilerlemeDurumu() {
  return ADIMLAR.map((a) => ({...a, bitti: a.no < adim && adimGecerli(a.no).ok}));
}

/* ════════════════ ADIM 1 — TUR ════════════════ */

function adim1() {
  const t = taslak();
  return `<h2>Ne üretiyorsun?</h2>
  <p class="kucuk orta" style="margin:6px 0 16px">
    Tür, üretim akışının bir ayarı. Sonraki adımlarda değiştirebilirsin.</p>
  <div class="izgara izgara-3" role="radiogroup" aria-label="Video türü">
    ${TURLER.map((x) => secKart({
      id: x.id, ad: x.ad, acik: x.acik, ikonAd: x.ikon,
      etiketler: x.etiketler, secili: t.tur === x.id, grup: 'tur',
    })).join('')}
  </div>
  ${uyariKutu('Belgeselde yapay zekâ ile <strong>görsel üretilmez</strong>; ' +
    'yalnızca gerçek arşiv ve stok görüntüsü kullanılır.', 'bilgi')}`;
}

/* ════════════════ ADIM 2 — KONU / ICERIK ════════════════ */

function adim2() {
  const t = taslak();
  const anim = t.tur === 'animasyon';
  const yontemler = [
    {id: 'konu', ad: 'Konu ver'},
    {id: 'senaryo', ad: 'Metin yapıştır'},
  ];
  return `<h2>Konu ve içerik</h2>
  <p class="kucuk orta" style="margin:6px 0 16px">
    Konuyu bir paragrafla anlat ya da hazır metnini yapıştır.</p>

  <div class="cipler" role="radiogroup" aria-label="Giriş yöntemi" style="margin-bottom:14px">
    ${yontemler.map((y) => `<button type="button" class="cip" data-grup="yontem"
      data-deger="${y.id}" aria-pressed="${t.girisYontemi === y.id}">${
      kac(y.ad)}</button>`).join('')}
  </div>

  ${alan({
    id: 'wzKonu',
    ad: t.girisYontemi === 'senaryo' ? 'Metin' : 'Konu',
    ipucu: 'En az 20 karakter. Ne kadar somut olursa araştırma o kadar isabetli olur.',
    ic: `<textarea class="metinalan" id="wzKonu" required minlength="20"
      aria-describedby="wzKonu-ipucu"
      placeholder="${t.girisYontemi === 'senaryo' ? YERTUTUCU.senaryo : YERTUTUCU.konu}"
      >${kac(t.konu)}</textarea>`,
  })}

  ${secimAlani({
    id: 'wzSure', ad: 'Hedef süre', deger: String(t.sureDk),
    ipucu: 'Anlatım uzunluğu buna göre hesaplanır.',
    secenekler: [
      {id: '1', ad: '1 dakika'}, {id: '2', ad: '2 dakika'},
      {id: '3', ad: '3 dakika'}, {id: '5', ad: '5 dakika'},
      {id: '8', ad: '8 dakika'}, {id: '10', ad: '10 dakika'},
      {id: '15', ad: '15 dakika'}, {id: '20', ad: '20 dakika'},
    ],
  })}

  <div class="alan">
    <span class="alan-ad" id="wzRefBaslik">Referans kareler${
      anim ? ' <span class="etiket etiket-hata">zorunlu</span>'
           : ' <span class="etiket">opsiyonel</span>'}</span>
    <div class="birak" id="wzRefBirak" role="button" tabindex="0"
      aria-describedby="wzRefBaslik">
      ${ikon('yukle', {boyut: 24})}
      <div class="birak-ad">Kare ekle</div>
      <div class="kucuk sessiz">Sürükle-bırak ya da tıkla · PNG/JPG</div>
      <label class="gorunmez" for="wzRefGirdi">Referans kare dosyaları</label>
      <input type="file" id="wzRefGirdi" accept="image/*" multiple class="gorunmez">
    </div>
    <div class="onizler" id="wzRefOnizler"></div>
    <span class="alan-ipucu">${anim
      ? 'Animasyon stilini bu karelerden öğrenir. En az 1 kare gerekli.'
      : 'Bu türde referans zorunlu değil; verirsen renk ve doku yönü için kullanılır.'}</span>
  </div>

  ${t.tur === 'animasyon' ? gelismis('Referans analizi (gelişmiş)', `
    <p class="kucuk orta">Kareleri yükledikten sonra stil analizi
      çalıştırabilirsin. Analiz, üretimde aynı karelerle birlikte kullanılır.</p>
    <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:10px">
      <button type="button" class="dugme" id="wzAnimAnaliz">
        ${ikon('cip', {boyut: 17})} Stil analizi yap</button>
      <button type="button" class="dugme dugme-hayalet" id="wzAnimSorular">
        ${ikon('bilgi', {boyut: 17})} Netleştirme soruları</button>
    </div>
    <div id="wzAnimSonuc" class="kucuk orta" style="margin-top:10px"></div>
  `) : ''}`;
}

/* ════════════════ ADIM 3 — GORSEL YON ════════════════ */

function adim3() {
  const t = taslak();
  const stilListe = t.tur === 'animasyon'
    ? (kaynak.animStilleri || []) : (kaynak.editStilleri || []);
  const stilDeger = t.tur === 'animasyon' ? t.animStili : t.editStili;

  return `<h2>Görsel yön</h2>
  <p class="kucuk orta" style="margin:6px 0 16px">
    Şablon ve ses temel; geri kalan her şey "Gelişmiş" altında.</p>

  <div class="alan">
    <span class="alan-ad">Edit şablonu</span>
    <div id="wzStiller" class="izgara izgara-3" role="radiogroup"
         aria-label="Edit şablonu">${
      stilListe.length
        ? stilListe.map((s) => secKart({
          id: s.id ?? s.ad ?? s, ad: s.ad ?? s.id ?? s,
          acik: s.ozet || s.aciklama || '', ikonAd: 'sablon', grup: 'stil',
          secili: (s.id ?? s.ad ?? s) === stilDeger,
        })).join('')
        : `<p class="kucuk sessiz">Şablon listesi alınamadı — üretim ` +
          `varsayılan şablonla devam eder.</p>`}
    </div>
  </div>

  ${secimAlani({
    id: 'wzSes', ad: 'Anlatıcı sesi', deger: t.ses,
    ipucu: 'Boş bırakırsan sistem türe uygun sesi kendi seçer.',
    secenekler: [{id: '', ad: 'Otomatik (önerilen)'},
      ...(kaynak.sesler || []).map((s) => ({
        id: s.id ?? s.ad ?? s, ad: s.ad ?? s.id ?? s}))],
  })}

  ${secimAlani({
    id: 'wzProfil', ad: 'Marka kiti', deger: t.profil,
    ipucu: 'Kanal profili: videolar arası renk ve karakter tutarlılığı.',
    secenekler: [{id: '', ad: 'Yok'},
      ...(kaynak.profiller || []).map((p) => ({
        id: p.pid ?? p.id ?? p, ad: p.ad ?? p.pid ?? p}))],
  })}

  ${gelismis('Gelişmiş: hareket ve altyazı', `
    ${anahtar({id: 'wzGecis', ad: 'Sahne geçişleri',
      acik: 'Kapatırsan tüm kesmeler sert olur.', acikMi: t.gecis})}
    ${anahtar({id: 'wzZoom', ad: 'Kamera hareketi',
      acik: 'Yavaş yaklaşma/uzaklaşma (Ken Burns).', acikMi: t.zoom})}
    ${anahtar({id: 'wzAltyazi', ad: 'Gömülü altyazı',
      acik: 'Videoya yazılır, sonradan kapatılamaz.', acikMi: t.altyazi})}
    <div id="wzAltyaziAyar" class="${t.altyazi ? '' : 'gorunmez'}"
         style="margin-top:12px">
      ${secimAlani({id: 'wzAltSablon', ad: 'Altyazı şablonu',
        deger: (t.altyaziSablon && t.altyaziSablon.id) || '',
        secenekler: [{id: '', ad: 'Varsayılan'},
          ...(kaynak.altyaziSablonlari || []).map((a) => ({
            id: a.id ?? a.ad ?? a, ad: a.ad ?? a.id ?? a}))]})}
      <div class="izgara izgara-2">
        ${alan({id: 'wzAltBoyut', ad: 'Punto',
          ic: `<input class="girdi" type="number" id="wzAltBoyut" min="18" max="120"
                value="${kac((t.altyaziSablon && t.altyaziSablon.boyut) || 42)}">`})}
        ${alan({id: 'wzAltKonum', ad: 'Konum',
          ic: `<select class="secim" id="wzAltKonum">
            ${['alt', 'orta', 'ust'].map((k) => `<option value="${k}" ${
              (t.altyaziSablon && t.altyaziSablon.konum) === k ? 'selected' : ''
            }>${k}</option>`).join('')}</select>`})}
      </div>
      <fieldset class="alan" style="border:0;padding:0;margin:0 0 16px">
        <legend class="alan-ad" style="padding:0">Yazı ve kontur rengi</legend>
        <div class="renkler">
          <label class="gorunmez" for="wzAltRenk">Yazı rengi</label>
          <input type="color" id="wzAltRenk" aria-label="Yazı rengi"
            value="${kac((t.altyaziSablon && t.altyaziSablon.renk) || '#ffffff')}">
          <label class="gorunmez" for="wzAltKontur">Kontur rengi</label>
          <input type="color" id="wzAltKontur" aria-label="Kontur rengi"
            value="${kac((t.altyaziSablon && t.altyaziSablon.kontur) || '#000000')}">
        </div>
      </fieldset>
      ${anahtar({id: 'wzAltBuyuk', ad: 'BÜYÜK HARF',
        acikMi: Boolean(t.altyaziSablon && t.altyaziSablon.buyuk)})}
      ${anahtar({id: 'wzAltGolge', ad: 'Gölge',
        acikMi: Boolean(t.altyaziSablon && t.altyaziSablon.golge)})}
    </div>
  `)}

  ${gelismis('Gelişmiş: renk ve ışık', `
    <div class="alan">
      <span class="alan-ad">Renk paleti</span>
      <div class="cipler" role="radiogroup" aria-label="Renk paleti">
        <button type="button" class="cip" data-grup="palet" data-deger=""
          aria-pressed="${!t.palet}">Otomatik</button>
        ${(kaynak.paletler || []).map((p) => {
          const id = p.id ?? p.ad ?? p;
          return `<button type="button" class="cip" data-grup="palet"
            data-deger="${kac(id)}" aria-pressed="${t.palet === id}">${
            kac(p.ad ?? id)}</button>`;
        }).join('')}
        <button type="button" class="cip" data-grup="palet" data-deger="ozel"
          aria-pressed="${t.palet === 'ozel'}">Özel renkler</button>
      </div>
      <div id="wzPaletOzel" class="${t.palet === 'ozel' ? '' : 'gorunmez'}"
           style="margin-top:10px">
        <div class="renkler">${t.paletOzel.map((h, i) =>
          `<label class="gorunmez" for="wzHex${i}">Özel renk ${i + 1}</label>
           <input type="color" id="wzHex${i}" value="${kac(h)}"
            aria-label="Özel renk ${i + 1}">`).join('')}</div>
      </div>
    </div>
    ${secimAlani({id: 'wzIsik', ad: 'Işık düzeyi', deger: t.isik,
      secenekler: [{id: '', ad: 'Otomatik'},
        ...(kaynak.isikDuzeyleri || []).map((i) => ({
          id: i.id ?? i.ad ?? i, ad: i.ad ?? i.id ?? i}))]})}
    ${secimAlani({id: 'wzArkaplan', ad: 'Arka plan', deger: t.arkaplan,
      secenekler: [{id: '', ad: 'Otomatik'},
        ...(kaynak.arkaplanlar || []).map((a) => ({
          id: a.id ?? a.ad ?? a, ad: a.ad ?? a.id ?? a}))]})}
  `)}

  ${t.tur === 'hikaye' ? gelismis('Gelişmiş: hikâye seçenekleri', `
    ${secimAlani({id: 'wzAcilis', ad: 'Açılış sahnesi', deger: t.acilis,
      ipucu: 'Videonun ilk saniyelerinin kuruluşu.',
      secenekler: [{id: '', ad: 'Otomatik'}, {id: 'soru', ad: 'Soru ile'},
        {id: 'sahne', ad: 'Sahne ile'}, {id: 'alinti', ad: 'Alıntı ile'}]})}
    ${anahtar({id: 'wzSora', ad: 'Hareketli açılış planı',
      acik: 'Açılış için video modeli kullanılır; süre ve maliyet artar.',
      acikMi: t.sora})}
  `) : ''}

  ${gelismis('Gelişmiş: görsel model ve ek referanslar', `
    ${secimAlani({id: 'wzModel', ad: 'Görsel model', deger: t.gorselModel,
      ipucu: 'Boş = sistem kararı. Yalnızca görsel üretilen türlerde etkili.',
      secenekler: [{id: '', ad: 'Otomatik'}, {id: 'gpt-image', ad: 'gpt-image'},
        {id: 'gemini', ad: 'gemini'}]})}
    <div class="izgara izgara-2">
      <div class="alan">
        <span class="alan-ad">Karakter görseli</span>
        <div class="birak" id="wzKarBirak" role="button" tabindex="0"
             aria-label="Karakter görseli seç">
          ${ikon('yukle', {boyut: 20})}<div class="birak-ad">Seç</div>
          <label class="gorunmez" for="wzKarGirdi">Karakter görseli dosyası</label>
          <input type="file" id="wzKarGirdi" accept="image/*" class="gorunmez">
        </div>
        <span class="alan-ipucu" id="wzKarAd">Seçilmedi</span>
      </div>
      <div class="alan">
        <span class="alan-ad">Stil görseli</span>
        <div class="birak" id="wzStilBirak" role="button" tabindex="0"
             aria-label="Stil görseli seç">
          ${ikon('yukle', {boyut: 20})}<div class="birak-ad">Seç</div>
          <label class="gorunmez" for="wzStilGirdi">Stil görseli dosyası</label>
          <input type="file" id="wzStilGirdi" accept="image/*" class="gorunmez">
        </div>
        <span class="alan-ipucu" id="wzStilAd">Seçilmedi</span>
      </div>
    </div>
  `)}`;
}

/* ════════════════ ADIM 4 — URETIM OZETI ════════════════ */

const HESAPLANACAK = 'Üretim sırasında hesaplanacak';

function adim4() {
  const t = taslak();
  const tb = turBilgi(t.tur);
  const kelime = Math.round(Number(t.sureDk || 2) * 139);  // olculen TTS hizi
  return `<h2>Üretim özeti</h2>
  <p class="kucuk orta" style="margin:6px 0 16px">
    Bunlar senin seçtiklerin. Araştırma ve medya sayıları üretim sırasında
    ölçülür — burada tahmin göstermiyoruz.</p>

  <div class="ozet-izgara">
    <section class="kart">
      <h3 style="margin-bottom:8px">Seçimlerin</h3>
      ${ozetSatir('Tür', tb ? tb.ad : '—')}
      ${ozetSatir('Hedef süre', `${t.sureDk} dk`)}
      ${ozetSatir('Anlatım (yaklaşık)', `${kelime.toLocaleString('tr-TR')} kelime`)}
      ${ozetSatir('Edit şablonu', (t.tur === 'animasyon' ? t.animStili : t.editStili) || 'Varsayılan')}
      ${ozetSatir('Ses', t.ses || 'Otomatik')}
      ${ozetSatir('Marka kiti', t.profil || 'Yok')}
      ${ozetSatir('Altyazı', t.altyazi ? 'Açık (gömülü)' : 'Kapalı')}
      ${ozetSatir('Kamera hareketi', t.zoom ? 'Açık' : 'Kapalı')}
      ${ozetSatir('Geçişler', t.gecis ? 'Açık' : 'Sert kesme')}
      ${ozetSatir('Referans kare', String(dosyalar.sahneRef.length))}
    </section>

    <section class="kart">
      <h3 style="margin-bottom:8px">Üretimde belirlenecek</h3>
      <!-- ⚠ Bu alanlarin backend ucu YOK. Sayi UYDURULMAZ. -->
      ${ozetSatir('Güvenilir kaynak sayısı', HESAPLANACAK, {hesaplanacak: true})}
      ${ozetSatir('Doğrulanmış iddia', HESAPLANACAK, {hesaplanacak: true})}
      ${ozetSatir('Kullanılabilir medya', HESAPLANACAK, {hesaplanacak: true})}
      ${ozetSatir('Sahne sayısı', HESAPLANACAK, {hesaplanacak: true})}
      ${ozetSatir('Tahmini maliyet', HESAPLANACAK, {hesaplanacak: true})}
      ${ozetSatir('Render süresi', HESAPLANACAK, {hesaplanacak: true})}
      ${ozetSatir('Lisans durumu', HESAPLANACAK, {hesaplanacak: true})}
    </section>
  </div>

  <div style="margin-top:16px">
    ${uyariKutu('Bu değerler için henüz bir ön-kontrol ucu yok. Üretim ' +
      'başladığında iş ekranında gerçek ölçülen değerler görünür.', 'bilgi')}
  </div>`;
}

/* ════════════════ ADIM 5 — ONAY ════════════════ */

function adim5() {
  const t = taslak();
  const tb = turBilgi(t.tur);
  return `<h2>Onay</h2>
  <p class="kucuk orta" style="margin:6px 0 16px">
    Üretim başlatılınca sunucu kuyruğuna alınır; ilerlemeyi Projeler
    ekranından izleyebilirsin.</p>

  <section class="kart">
    <div class="iskart-satir" style="margin-bottom:10px">
      ${etiket(tb ? tb.ad : '—', 'vurgu')}${etiket(`${t.sureDk} dk`)}
      ${t.altyazi ? etiket('Altyazili') : ''}
    </div>
    <p class="kucuk orta" style="white-space:pre-wrap;max-height:120px;overflow:auto">${
      kac((t.konu || '').slice(0, 600))}${(t.konu || '').length > 600 ? '…' : ''}</p>
  </section>

  <div style="margin-top:14px">
    ${uyariKutu('Çıktı dosyaları: video, kapak görseli ve kullanılan ' +
      'kaynakların listesi.', 'bilgi')}
  </div>

  <div id="wzUretimDurum" class="kucuk" style="margin-top:14px" role="status"
       aria-live="polite"></div>`;
}

/* ════════════════ KAYNAK YUKLEME ════════════════ */

async function kaynaklariYukle() {
  const istekler = {
    editStilleri: UCLAR.editStilleri,
    animStilleri: UCLAR.animasyonStilleri,
    sesler: UCLAR.sesler,
    profiller: UCLAR.profiller,
    paletler: UCLAR.paletler,
    isikDuzeyleri: UCLAR.isikDuzeyleri,
    arkaplanlar: UCLAR.arkaplanlar,
    altyaziSablonlari: UCLAR.altyaziSablonlari,
  };
  const cikti = {hatalar: []};
  await Promise.all(Object.entries(istekler).map(async ([ad, uc]) => {
    const s = await getirSessiz(uc);
    if (s.ok) {
      // Sunucu bazen {liste:[...]} bazen [...] donuyor — ikisini de kabul et
      const v = s.veri;
      cikti[ad] = Array.isArray(v) ? v
        : Array.isArray(v?.liste) ? v.liste
          : Array.isArray(v?.stiller) ? v.stiller
            : Array.isArray(v?.sesler) ? v.sesler
              : Array.isArray(v?.profiller) ? v.profiller : [];
    } else {
      cikti[ad] = [];
      cikti.hatalar.push({ad, hata: s.hata});
    }
  }));
  return cikti;
}

/* ════════════════ CIZIM + OLAYLAR ════════════════ */

function adimGovdesi() {
  return [adim1, adim2, adim3, adim4, adim5][adim - 1]();
}

function ilerlemeCubugu() {
  const d = ilerlemeDurumu();
  return `<nav class="adimlar" aria-label="Proje adımları">
    ${d.map((a, i) => {
      const durum = a.no === adim ? 'şu anki adım'
        : a.bitti ? 'tamamlandı' : 'henüz tamamlanmadı';
      return `${i ? '<span class="adim-ayirac" aria-hidden="true"></span>' : ''}
      <span class="adim-oge"><button type="button" class="adim-dugme"
        data-adim="${a.no}" data-bitti="${a.bitti ? 1 : 0}"
        aria-label="Adım ${a.no}: ${kac(a.ad)} — ${durum}"
        ${a.no === adim ? 'aria-current="step"' : ''}>
        <span class="adim-no" aria-hidden="true">${a.bitti && a.no !== adim
          ? ikon('onay', {boyut: 12}) : a.no}</span>
        <span class="adim-ad" aria-hidden="true">${kac(a.ad)}</span>
      </button></span>`;
    }).join('')}
  </nav>`;
}

export function wizardHtml() {
  return `<div class="sayfa-bas">
    <div class="sayfa-bas-yazi">
      <h1>Yeni Proje</h1>
      <p>Adım ${adim}/5 — ${kac(ADIMLAR[adim - 1].tam)}</p>
    </div>
    <button type="button" class="dugme dugme-hayalet" id="wzSifirla">
      ${ikon('cop', {boyut: 17})} Taslağı sil</button>
  </div>
  ${ilerlemeCubugu()}
  <div class="wz-govde" id="wzGovde">${adimGovdesi()}</div>
  <div class="wz-alt">
    <button type="button" class="dugme dugme-hayalet" id="wzGeri"
      ${adim === 1 ? 'disabled' : ''}>${ikon('geri', {boyut: 17})} Geri</button>
    <span class="bosluk"></span>
    <span id="wzUyari" class="kucuk" style="color:var(--uyari)"></span>
    ${adim < 5
      ? `<button type="button" class="dugme dugme-ana" id="wzDevam">Devam
          ${ikon('ok', {boyut: 17})}</button>`
      : `<button type="button" class="dugme dugme-ana dugme-buyuk" id="wzUret">
          ${ikon('onay', {boyut: 18})} Projeyi oluştur</button>`}
  </div>`;
}

function onizlemeleriCiz() {
  const kap = $('#wzRefOnizler');
  if (!kap) return;
  kap.innerHTML = dosyalar.sahneRef.map((f, i) =>
    `<img src="${URL.createObjectURL(f)}" alt="Referans kare ${i + 1}">`).join('');
}

function dosyaAlaniBagla(birakId, girdiId, coklu, geri) {
  const birak = $(birakId);
  const girdi = $(girdiId);
  if (!birak || !girdi) return;
  const ac = () => girdi.click();
  birak.addEventListener('click', ac);
  birak.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); ac(); }
  });
  ['dragenter', 'dragover'].forEach((t) => birak.addEventListener(t, (e) => {
    e.preventDefault(); birak.classList.add('uzerinde');
  }));
  ['dragleave', 'drop'].forEach((t) => birak.addEventListener(t, (e) => {
    e.preventDefault(); birak.classList.remove('uzerinde');
  }));
  birak.addEventListener('drop', (e) => {
    const f = Array.from(e.dataTransfer?.files || [])
      .filter((x) => x.type.startsWith('image/'));
    if (f.length) geri(coklu ? f : f[0]);
  });
  girdi.addEventListener('change', () => {
    const f = Array.from(girdi.files || []);
    if (f.length) geri(coklu ? f : f[0]);
  });
}

function olaylariBagla(yenidenCiz) {
  const t = taslak();

  $$('.adim-dugme').forEach((b) => b.addEventListener('click', () => {
    const hedef = Number(b.dataset.adim);
    if (hedef < adim) { adim = hedef; yenidenCiz(); return; }
    // Ileri atlarken aradaki adimlar gecerli olmali
    for (let n = 1; n < hedef; n++) {
      const g = adimGecerli(n);
      if (!g.ok) { adim = n; yenidenCiz(); uyariGoster(g.sebep); return; }
    }
    adim = hedef; yenidenCiz();
  }));

  const geri = $('#wzGeri');
  if (geri) geri.addEventListener('click', () => {
    if (adim > 1) { uyariTemizle(); adim--; yenidenCiz(); }
  });

  const devam = $('#wzDevam');
  if (devam) devam.addEventListener('click', () => {
    const g = adimGecerli(adim);
    if (!g.ok) { uyariGoster(g.sebep); return; }
    uyariTemizle();                 // eski hata sonraki adimda okunmasin
    adim = Math.min(5, adim + 1);
    yenidenCiz();
  });

  const sifirla = $('#wzSifirla');
  if (sifirla) sifirla.addEventListener('click', () => {
    taslakSil(); dosyalariTemizle(); adim = 1; yenidenCiz();
    duyur('Taslak silindi');
  });

  grupBagla(document, 'tur', (v) => {
    taslakYaz({tur: v});
    // Tur degisince stil secimi karismasin
    taslakYaz(v === 'animasyon' ? {editStili: ''} : {animStili: ''});
  });
  grupBagla(document, 'yontem', (v) => taslakYaz({girisYontemi: v}));
  grupBagla(document, 'stil', (v) => taslakYaz(
    taslak().tur === 'animasyon' ? {animStili: v} : {editStili: v}));
  grupBagla(document, 'palet', (v) => {
    taslakYaz({palet: v});
    const oz = $('#wzPaletOzel');
    if (oz) oz.classList.toggle('gorunmez', v !== 'ozel');
  });

  const konu = $('#wzKonu');
  if (konu) konu.addEventListener('input', () => {
    taslakYaz({konu: konu.value});
    konu.setAttribute('aria-invalid', konu.value.trim().length < 20);
  });

  const sure = $('#wzSure');
  if (sure) sure.addEventListener('change', () => taslakYaz({sureDk: sure.value}));

  [['wzSes', 'ses'], ['wzProfil', 'profil'], ['wzIsik', 'isik'],
   ['wzArkaplan', 'arkaplan'], ['wzAcilis', 'acilis'],
   ['wzModel', 'gorselModel']].forEach(([id, anahtarAd]) => {
    const el = document.getElementById(id);
    if (el) el.addEventListener('change', () => taslakYaz({[anahtarAd]: el.value}));
  });

  [['wzGecis', 'gecis'], ['wzZoom', 'zoom'], ['wzSora', 'sora']]
    .forEach(([id, anahtarAd]) => {
      const el = document.getElementById(id);
      if (el) el.addEventListener('change', () =>
        taslakYaz({[anahtarAd]: el.checked}));
    });

  const alt = $('#wzAltyazi');
  if (alt) alt.addEventListener('change', () => {
    taslakYaz({altyazi: alt.checked});
    const kap = $('#wzAltyaziAyar');
    if (kap) kap.classList.toggle('gorunmez', !alt.checked);
  });

  // Altyazi sablonu alanlari -> tek nesne
  const altyaziTopla = () => {
    const g = (id) => document.getElementById(id);
    taslakYaz({altyaziSablon: {
      id: g('wzAltSablon')?.value || '',
      boyut: Number(g('wzAltBoyut')?.value || 42),
      konum: g('wzAltKonum')?.value || 'alt',
      renk: g('wzAltRenk')?.value || '#ffffff',
      kontur: g('wzAltKontur')?.value || '#000000',
      buyuk: Boolean(g('wzAltBuyuk')?.checked),
      golge: Boolean(g('wzAltGolge')?.checked),
    }});
  };
  ['wzAltSablon', 'wzAltBoyut', 'wzAltKonum', 'wzAltRenk', 'wzAltKontur',
   'wzAltBuyuk', 'wzAltGolge'].forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.addEventListener('change', altyaziTopla);
  });

  [0, 1, 2].forEach((i) => {
    const el = document.getElementById(`wzHex${i}`);
    if (el) el.addEventListener('change', () => {
      const h = [...taslak().paletOzel];
      h[i] = el.value;
      taslakYaz({paletOzel: h});
    });
  });

  dosyaAlaniBagla('#wzRefBirak', '#wzRefGirdi', true, (f) => {
    dosyalar.sahneRef = dosyalar.sahneRef.concat(f).slice(0, 8);
    onizlemeleriCiz();
    duyur(`${dosyalar.sahneRef.length} referans kare seçildi`);
  });
  dosyaAlaniBagla('#wzKarBirak', '#wzKarGirdi', false, (f) => {
    dosyalar.karakter = f;
    const e = $('#wzKarAd'); if (e) e.textContent = f.name;
  });
  dosyaAlaniBagla('#wzStilBirak', '#wzStilGirdi', false, (f) => {
    dosyalar.stil = f;
    const e = $('#wzStilAd'); if (e) e.textContent = f.name;
  });
  onizlemeleriCiz();

  const analiz = $('#wzAnimAnaliz');
  if (analiz) analiz.addEventListener('click', () => animAkis(UCLAR.animAnaliz));
  const sorular = $('#wzAnimSorular');
  if (sorular) sorular.addEventListener('click', () => animAkis(UCLAR.animSorular));

  const uret = $('#wzUret');
  if (uret) uret.addEventListener('click', () => uretimiBaslat(uret));
}

function uyariGoster(metin) {
  const el = $('#wzUyari');
  if (el) { el.textContent = metin; duyur(metin); }
}

/** Uyariyi ve ekran okuyucu duyurusunu TEMIZLE (basarili gecişte zorunlu). */
function uyariTemizle() {
  const el = $('#wzUyari');
  if (el) el.textContent = '';
  duyur('');
}

async function animAkis(uc) {
  const kutu = $('#wzAnimSonuc');
  if (!kutu) return;
  if (!dosyalar.sahneRef.length) {
    kutu.textContent = 'Önce en az 1 referans kare ekle.';
    return;
  }
  kutu.textContent = 'Çalışıyor…';
  const fd = new FormData();
  fd.append('session', oturumId());
  dosyalar.sahneRef.forEach((f) => fd.append('kare', f));
  try {
    const r = await fetch(yol(uc), {method: 'POST', body: fd});
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const d = await r.json();
    kutu.textContent = typeof d === 'string' ? d
      : (d.ozet || d.metin || JSON.stringify(d).slice(0, 400));
  } catch (e) {
    kutu.textContent = `Çalıştırılamadı: ${e.message}. ` +
      'Referans kareler üretimde yine kullanılır.';
  }
}

/* ════════════════ URETIM ════════════════ */

function generateDegerleri() {
  const t = taslak();
  const d = {
    session: oturumId(),
    story: (t.konu || '').trim(),
    tur: t.tur || 'documentary',
    sure_dk: String(t.sureDk || '2'),
    gecis: t.gecis ? '1' : '0',
    zoom: t.zoom ? '1' : '0',
    altyazi: t.altyazi ? '1' : '0',
  };
  const stil = t.tur === 'animasyon' ? t.animStili : t.editStili;
  if (stil) d.edit = stil;
  if (t.profil) d.profil = t.profil;
  if (t.altyazi && t.altyaziSablon) {
    d.altyazi_sablon = JSON.stringify(t.altyaziSablon);
  }
  if (t.palet === 'ozel') {
    d.palet = 'ozel';
    d.palet_ozel = t.paletOzel.join(',');
  } else if (t.palet) {
    d.palet = t.palet;
  }
  if (t.arkaplan) d.arkaplan = t.arkaplan;
  if (t.ses) d.ses = t.ses;
  if (t.isik) d.isik = t.isik;
  if (t.gorselModel) d.gorsel_model = t.gorselModel;
  if (t.tur === 'hikaye') {
    if (t.acilis) d.acilis = t.acilis;
    d.sora = t.sora ? '1' : '0';
  }
  if (dosyalar.karakter) d.karakter = dosyalar.karakter;
  if (dosyalar.stil) d.stil = dosyalar.stil;
  if (dosyalar.sahneRef.length) d.sahne_ref = dosyalar.sahneRef;
  return d;
}

// Test/denetim icin disari aciliyor: alan adlarinin sozlesmeye uydugu
// dogrulanabilsin.
export {generateDegerleri};

async function uretimiBaslat(dugme) {
  const durum = $('#wzUretimDurum');
  for (const n of [1, 2]) {
    const g = adimGecerli(n);
    if (!g.ok) {
      if (durum) durum.textContent = g.sebep;
      adim = n;
      return;
    }
  }
  dugme.disabled = true;
  if (durum) durum.textContent = 'Üretim başlatılıyor…';
  try {
    const cevap = await uretimBaslat(generateDegerleri());
    const isId = cevap.job || cevap.is_id || cevap.id || '';
    yerelIsEkle({
      is_id: isId,
      ad: (taslak().konu || '').slice(0, 60) || isId,
      tur: taslak().tur,
      durum: 'kuyrukta',
      olusturma: new Date().toISOString(),
    });
    if (durum) {
      durum.innerHTML = `<span style="color:var(--iyi)">Başlatıldı.</span> ` +
        `İş kimliği <strong class="tekfont">${kac(isId)}</strong>. ` +
        `<a href="#/projeler" style="text-decoration:underline">Projeler</a> ` +
        `ekranından izleyebilirsin.`;
    }
    duyur('Üretim başlatıldı');
    taslakSil();
    dosyalariTemizle();
  } catch (e) {
    dugme.disabled = false;
    if (durum) {
      durum.innerHTML = `<span style="color:var(--hata)">Başlatılamadı:</span> ` +
        kac(String(e.message || e).slice(0, 240));
    }
  }
}

/* ════════════════ GIRIS NOKTASI ════════════════ */

export async function wizardCiz(kap, {adimNo} = {}) {
  if (adimNo) adim = Math.max(1, Math.min(5, Number(adimNo)));
  kap.innerHTML = `<div class="sayfa-bas"><div class="sayfa-bas-yazi">
    <h1>Yeni Proje</h1><p>Seçenekler yükleniyor…</p></div></div>
    ${yukleniyor(3, 84)}`;
  if (!kaynak.yuklendi) {
    kaynak = {...(await kaynaklariYukle()), yuklendi: true};
  }
  const ciz = () => {
    kap.innerHTML = wizardHtml();
    ikonlariBagla(kap);
    olaylariBagla(ciz);
    // Yeni adim cizildi: onceki adimin hata duyurusu artik gecerli degil
    duyur('');
  };
  ciz();
}

export function wizardAdim() { return adim; }
export function wizardKaynakHatalari() { return kaynak.hatalar || []; }
