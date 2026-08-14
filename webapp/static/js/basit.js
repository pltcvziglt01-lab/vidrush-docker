/**
 * BASIT URETIM — "Metin + Stil + Auto" (Faz I-3)
 *
 * ⚠ NEDEN VAR: "Yeni Proje" tek yol olarak 5 ADIMLI wizard'di. Bir video
 * baslatmak icin kullanici tur karti seciyor, konu yaziyor, gorsel yon
 * ekraninda stil/ses/marka/palet/altyazi kuruyor, ozet ve onay adimlarindan
 * geciyordu. Cogu is icin gereken UC sey vardi: METIN, STIL, BASLAT.
 *
 * Bu modul o uc seyi tek ekrana indirir. Wizard SILINMEDI — "Adim adim"
 * modu olarak duruyor ve her alan orada da erisilebilir.
 *
 * ⚠ HICBIR BACKEND ALANI KAYBOLMADI. Gelismis acilir alani, adim 3'un
 * `hizliTercihler()` + `proPanel()` bilesenlerinin AYNISINI cagirir; yani
 * palet, arkaplan, isik, gorsel model, altyazi sablonu, acilis, Sora, unlu
 * modu, ses kutuphanesi, marka kiti, karakter/stil gorseli ve referans
 * kareler bu ekranda da yasar. Yeniden yazilmadi, YENIDEN KULLANILDI.
 *
 * ⚠ AUTO SOZLESMESI: Auto secimi `/api/analiz`in `konsept` + `stil_profili`
 * sonucunu GORUNUR kilar ve `generate` sozlesmesine YENI ALAN EKLEMEDEN,
 * mevcut `edit` alaniyla tasir (bkz. `autoStilKimligi`). 22 alanlik sozlesme
 * degismedi.
 */
import {$, alan, gelismis, kac, ozetSatir, secimAlani, uyariKutu}
  from './bilesenler.js';
import {ikon} from './ikon.js';
import {calanSes, hizliTercihler, markaBolumu, medyaBolumu, medyaBolumuKur,
        proPanel, sesBolumu, stilBolumu} from './secim-deneyimi.js';

/** Uzun yer tutucu — sablon dizesi icinde kesme isareti kacis sorunu yaratir. */
export const BASIT_YERTUTUCU =
  'Örnek: Apollo 11 inişindeki kritik son dakikalar — 1202 program alarmı, ' +
  'yarı-elle kontrol, Tranquility Base.';

/** Basit modda varsayilan tur. Digerleri gelismis alandan secilir. */
export const BASIT_VARSAYILAN_TUR = 'documentary';

export const SURE_SECENEKLERI = [
  {id: '1', ad: '1 dakika'}, {id: '2', ad: '2 dakika'},
  {id: '3', ad: '3 dakika'}, {id: '5', ad: '5 dakika'},
  {id: '8', ad: '8 dakika'}, {id: '10', ad: '10 dakika'},
  {id: '15', ad: '15 dakika'}, {id: '20', ad: '20 dakika'},
];

/**
 * Iki kurulum modu arasindaki anahtar — HER IKI ekranin basinda da durur ki
 * kullanici hangi moda gecerse gecsin geri donebilsin.
 */
export function modCipleri(etkin) {
  const c = (deger, ad) => `<button type="button" class="cip" data-grup="mod"
    data-deger="${deger}" aria-pressed="${etkin === deger}">${ad}</button>`;
  return `<div class="cipler mod-cip" role="radiogroup"
    aria-label="Kurulum biçimi">${c('basit', 'Basit')}${
    c('adim', 'Adım adım')}</div>`;
}

/* ════════════════ AUTO SONUCU ════════════════ */

/** Konsept guveni -> insan dili. UYDURMA PUAN YOK; olculen deger yazilir. */
export function guvenMetni(konsept) {
  const d = String(konsept?.durum || '');
  if (d === 'kesin') return 'Sinyal net';
  if (d === 'melez') return 'İki tür arasında';
  if (d === 'zayif') return 'Sinyal zayıf';
  return 'Belirsiz';
}

/**
 * Auto'nun sectigi stil `generate`e TASINABILIR mi?
 *
 * ⚠ YALNIZCA `kaynak === 'auto'` tasinir. Sebebi olculdu:
 *   · `varsayilan`  -> ortada gercek bir sinyal yok; uretim hattinin kendi
 *                      varsayilanini sessizce degistirmeyiz.
 *   · `turetilmis`  -> kimlik `melez:a+b` bicimindedir ve stil profili
 *                      kaydinda BOYLE BIR SATIR YOKTUR; gonderilirse hat onu
 *                      cozemez ve SESSIZCE varsayilana duser. Yani "melez
 *                      uygulandi" demek yalan olurdu. Arayuz bunu acikca
 *                      soyler (bkz. `autoPaneli`).
 *   · `kullanici`   -> zaten kullanicinin acik secimi; normal yoldan gider.
 * Ayrica hikaye/animasyon hatlari kendi stil sozluklerini kullanir; bilesik
 * profil kimligi orada karsiliksizdir, bu yuzden tasinmaz.
 */
/**
 * Auto'nun onerdigi URETIM HATTI (`tur`) — yalnizca kullanici kendisi bir tur
 * secmemisse uygulanir.
 *
 * ⚠ NEDEN GEREKLI (olculdu): basit mod turu sabit `documentary` biraksaydi,
 * "kapinin ardindaki golge" gibi acik bir KORKU HIKAYESI belgesel hattinda
 * uretilirdi. `/api/analiz` bunu zaten `hikaye` diye olcuyor; olculmus bilgiyi
 * gormezden gelmek sessiz bir kalite hatasi olurdu.
 * ⚠ `animasyon` BURADAN GELMEZ — sunucu sozlesmesi yalnizca documentary/hikaye
 * uretir; animasyon referans karesi zorunlu oldugu icin zaten adim adim modun
 * isidir.
 */
export function autoTuru(analiz, t) {
  if (!analiz || analiz._hata) return '';
  if (t && t.turKaynak === 'kullanici') return '';

  // ⚠ KAYNAK SECIMI OLCULDU. `otomatik_secimler.tur` ESKI bes-etiketli
  // dedektorden gelir ve zayif: "kabus gibi bir gece: kapinin ardindaki
  // golge" metninde `belirsiz` deyip `documentary`ye duser — yani acik bir
  // korku hikayesi belgesel hattina giderdi. Ayni metni YENI taksonomi
  // `hikaye.korku` diye dogru siniflandiriyor. Bu yuzden birincil kaynak
  // `konsept.eski_etiket`; eski alan yalnizca YEDEK.
  // Esleme sunucunun `PIPELINE_TURU` tablosuyla ayni: yalnizca `hikaye`
  // ayri hat, digerlerinin hepsi `documentary`.
  const k = analiz.konsept || {};
  let v = '';
  if (k.eski_etiket && k.eski_etiket !== 'belirsiz') {
    v = k.eski_etiket === 'hikaye' ? 'hikaye' : 'documentary';
  } else {
    const oneri = analiz.otomatik_secimler && analiz.otomatik_secimler.tur;
    v = oneri ? String(oneri.deger || '') : '';
  }
  if (v !== 'documentary' && v !== 'hikaye') return '';
  return v === (t && t.tur) ? '' : v;
}

export function autoStilKimligi(analiz, tur) {
  const s = analiz && analiz.stil_profili;
  if (!s || s.kaynak !== 'auto') return '';
  const k = String(s.kimlik || '');
  if (!k || k.startsWith('melez:')) return '';
  if (tur === 'hikaye' || tur === 'animasyon') return '';
  return k;
}

/**
 * Kararin GEREKCESI — insan diliyle, OLCULEN sayilarla.
 *
 * ⚠ Backend'in `gerekce` alani gelistirici metnidir ("belgesel.tarih: puan 8.0
 * (2. belgesel.biyografi 4.5), kanit 4 = 2 anahtar + 2 yapisal sinyal") ve
 * hem ASCII yazimli hem de okunmasi zor. Ekranda ham haliyle gostermek
 * "gorunur" yapar ama ANLASILIR yapmaz. Bu yuzden ayni olcumu yapisal
 * alanlardan yeniden kuruyoruz; uydurma yok, sayilar analizden geliyor.
 */
export function kanitMetni(konsept) {
  const kanit = Number(konsept?.kanit || 0);
  if (!kanit) return '';
  const yuzde = Math.round(Number(konsept?.guven || 0) * 100);
  return `Metinde ${kanit} bağımsız işaret ölçüldü` +
    (yuzde ? `; kararın güveni yüzde ${yuzde}.` : '.');
}

/** Auto panelinin govdesi. Analiz yoksa/patladiysa DURUSTCE soyler. */
export function autoPaneli(analiz, tur, {metinVar = true} = {}) {
  if (!metinVar) {
    return `<p class="kucuk orta">Metni yazdığında konu türünü ve sana uygun
      stili burada göstereceğim. Bu okuma ücretsizdir ve yapay zekâ çağrısı
      yapmaz.</p>`;
  }
  if (!analiz) {
    return `<p class="kucuk orta">Metin okunuyor…</p>`;
  }
  if (analiz._hata) {
    return uyariKutu(`Analiz alınamadı (${kac(String(analiz._hata))}). ` +
      'Üretim yine çalışır; stil varsayılan kalır.', 'uyari');
  }
  const k = analiz.konsept || {};
  const s = analiz.stil_profili || {};
  const tasinan = autoStilKimligi(analiz, tur);
  const stilAdi = s.profil && s.profil.ad ? s.profil.ad : (s.kimlik || '');

  const konseptSatiri = k.yol && k.yol !== 'belirsiz'
    ? ozetSatir('Konu türü', `${k.ad || k.yol} · ${guvenMetni(k)}`)
    : ozetSatir('Konu türü', 'Belirlenemedi — zorla tür seçilmedi');

  const stilSatiri = stilAdi
    ? ozetSatir('Seçilen stil', tasinan
      ? stilAdi
      : `${stilAdi} (uygulanmadı)`)
    : ozetSatir('Seçilen stil', 'Üretim hattının varsayılanı');

  // ⚠ Tasinamayan durumlar SESSIZ GECILMEZ; sebebi yazilir.
  let not = '';
  if (!tasinan && s.kaynak === 'turetilmis') {
    not = uyariKutu('Metin iki türün arasında; sistem melez bir stil türetti ' +
      'ama melez stiller henüz üretime taşınamıyor. Varsayılan stille ' +
      'devam edilir. Kesin bir sonuç istersen aşağıdan stili kendin seç.',
    'uyari');
  } else if (!tasinan && s.kaynak === 'varsayilan') {
    not = `<p class="kucuk sessiz">Metinde belirgin bir tür sinyali yok;
      üretim hattının kendi varsayılanı kullanılır.</p>`;
  } else if (!tasinan && (tur === 'hikaye' || tur === 'animasyon')) {
    not = `<p class="kucuk sessiz">Bu türün kendi stil listesi var; bileşik
      profil yalnızca belgesel hattında uygulanır.</p>`;
  }

  const kanit = kanitMetni(k);
  const HAT_ADI = {documentary: 'Belgesel', hikaye: 'Hikâye',
                   animasyon: 'Animasyon'};
  return `${konseptSatiri}
    ${ozetSatir('Üretim hattı', HAT_ADI[tur] || tur || '—')}
    ${stilSatiri}
    ${s.surum ? ozetSatir('Stil sürümü', String(s.surum)) : ''}
    ${kanit ? `<p class="kucuk sessiz">${kac(kanit)}</p>` : ''}
    ${(s.uyari || []).length
    ? `<p class="kucuk sessiz">${kac(s.uyari.join(' · '))}</p>` : ''}
    ${not}`;
}

/* ════════════════ GOVDE ════════════════ */

/**
 * Basit uretim ekrani.
 * `analiz`: `/api/analiz` sonucu ya da null (henuz gelmedi).
 */
export function basitGovde({t, kaynak, analiz, durum, dosyalar}) {
  const metin = (t.konu || '').trim();
  const otomatikStil = !t.editStili;
  const yeterli = metin.length >= 20;

  return `<div class="sayfa-bas">
    <div class="sayfa-bas-yazi">
      <h1>Yeni Proje</h1>
      <p>Metni yaz, stili seç, başlat.</p>
    </div>
    ${modCipleri('basit')}
  </div>

  <div class="bs-govde">
    ${alan({
    id: 'bsMetin',
    ad: 'Ne anlatalım?',
    ipucu: 'En az 20 karakter. Konu başlığı yazabilir ya da hazır anlatım ' +
           'metnini yapıştırabilirsin; sistem hangisi olduğunu kendi ölçer.',
    ic: `<textarea class="metinalan" id="bsMetin" required minlength="20"
      aria-describedby="bsMetin-ipucu"
      placeholder="${kac(BASIT_YERTUTUCU)}">${kac(t.konu)}</textarea>`,
  })}

    ${stilBolumu({
    liste: kaynak.editStilleri, deger: t.editStili,
    tumunuAc: durum.stilTumu, arama: durum.stilArama,
    hataMetni: 'Stil listesi alınamadı.',
  })}

    ${secimAlani({
    id: 'bsSure', ad: 'Hedef süre', deger: String(t.sureDk),
    ipucu: 'Anlatım uzunluğu buna göre hesaplanır.',
    secenekler: SURE_SECENEKLERI,
  })}

    ${/* ⚠ FAZ UI-5 (`UI5-SAGLAYICI-ANA-AKISTA-YOK`): medya kaynagi ve
         Magnific durumu ANA akista GORUNUR olmali — gelismis ayarlarin
         icinde gizli DEGIL. Canli DOM olcumu: Basit modda hic yoktu. */ ''}
    ${medyaBolumu({tercih: t.kaynakTercihi, sureDk: t.sureDk,
    stil: (kaynak.editStilleri || []).find((x) => x.id === t.editStili) || null})}

    <section class="kart bs-auto" id="bsAuto">
      <h3 class="ozet-kart-bas">${otomatikStil
    ? 'Sistemin okuduğu' : 'Metin analizi'}</h3>
      ${otomatikStil
    ? autoPaneli(analiz, t.tur || BASIT_VARSAYILAN_TUR, {metinVar: yeterli})
    : `<p class="kucuk orta">Stili sen seçtin: <strong>${
      kac(t.editStili)}</strong>. Otomatik öneri devre dışı.</p>
       ${autoPaneli(analiz, t.tur || BASIT_VARSAYILAN_TUR,
    {metinVar: yeterli})}`}
    </section>

    ${gelismis('Gelişmiş ayarlar', `
      <p class="kucuk orta">Buradaki her ayar isteğe bağlı. Dokunmazsan
        sistem konuya göre seçer.</p>
      ${sesBolumu({
    liste: kaynak.sesler, deger: t.ses, tumunuAc: durum.sesTumu,
    arama: durum.sesArama, suzgec: durum.sesSuzgec, calan: calanSes(),
    kaynakSecimi: durum.sesKaynagi,
    katalog: durum.katalog[durum.sesKaynagi] || null,
    katalogYukleniyor: durum.katalogYukleniyor,
  })}
      ${markaBolumu({
    liste: kaynak.profiller, deger: t.profil,
    hataVar: (kaynak.hatalar || []).some((h) => h.ad === 'profiller'),
  })}
      ${hizliTercihler({gecis: t.gecis, zoom: t.zoom, altyazi: t.altyazi})}
      ${proPanel({acik: durum.proAcik, t, kaynak})}
      <p class="kucuk sessiz bs-adim-not">Tür seçimi, referans kareler ve
        adım adım kurulum için yukarıdan <strong>Adım adım</strong> moduna
        geçebilirsin. Seçtiklerin korunur.</p>
    `)}

    <div class="bs-eylem">
      <button type="button" class="dugme dugme-ana dugme-buyuk" id="bsUret"
        ${yeterli ? '' : 'disabled'}>
        ${ikon('onay', {boyut: 18})} Videoyu oluştur</button>
      <span class="kucuk sessiz bs-eylem-not">${yeterli
    ? 'Üretim sunucu kuyruğuna alınır; ilerlemeyi Projeler ekranından izlersin.'
    : 'Başlatmak için en az 20 karakter yaz.'}</span>
    </div>

    <div id="bsUretimDurum" class="kucuk onay-durum" role="status"
      aria-live="polite"></div>
  </div>`;
}

/* ════════════════ OLAYLAR ════════════════ */

/**
 * Basit ekranin olaylari.
 * ⚠ Stil/palet/ses/marka gibi SECIM kontrollerinin baglanmasi `adim3Kur()`
 * icindedir; burada tekrar baglanmaz (cift baglama olurdu).
 */
export function basitKur({kok, taslak, taslakYaz, yenidenCiz, analizTazele,
                          uret}) {
  // ⚠ FAZ UI-5: medya kaynagi secimi SUNUCUYA baglanir (`/api/kaynak-tercihi`).
  // `/api/generate` sozlesmesi (22 alan) BUYUMEZ.
  medyaBolumuKur(kok);

  const metin = $('#bsMetin', kok);
  if (metin) {
    metin.addEventListener('input', () => {
      taslakYaz({konu: metin.value});
      metin.setAttribute('aria-invalid', metin.value.trim().length < 20);
      analizTazele();
      const d = $('#bsUret', kok);
      if (d) d.disabled = metin.value.trim().length < 20;
    });
    // Metin alanindan cikinca analiz sonucunu tazele (ucretsiz, LLM yok)
    metin.addEventListener('change', () => analizTazele({hemen: true}));
  }

  const sure = $('#bsSure', kok);
  if (sure) {
    sure.addEventListener('change', () => taslakYaz({sureDk: sure.value}));
  }

  const uretDugme = $('#bsUret', kok);
  if (uretDugme) uretDugme.addEventListener('click', () => uret(uretDugme));

  if (!taslak().tur) taslakYaz({tur: BASIT_VARSAYILAN_TUR});
  if (yenidenCiz) { /* cizim sahibi wizard.js */ }
}
