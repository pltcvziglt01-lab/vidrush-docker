/**
 * SECIM DENEYIMI (Faz G) — Adim 3'un yaratici secim bilesenleri.
 *
 * ⚠ NEDEN AYRI MODUL: `wizard.js` zaten 780 satirdi; secim deneyimi ona
 * eklenirse tek dosya yeniden bakimi zor bir yigina donuyordu. Wizard artik
 * yalnizca adim akisini ve `generate` sozlesmesini yonetiyor; ekranin secim
 * kismi burada.
 *
 * TASARIM MODELI: "her seyi ayni anda goster" DEGIL —
 *   1) Otomatik (onerilen) karti  2) en fazla 3 oneri  3) "tumunu goster"
 *   4) profesyonel ayarlar (tek acik akordeon)  5) canli secim ozeti
 *
 * ⚠ UYDURMA BILGI YASAGI: kart uzerinde yalnizca API'nin GERCEKTEN dondurdugu
 * alanlar gosterilir.
 *   edit-stilleri  -> ad, ozet, sahne_sn, footage_pct
 *   animasyon-stil -> ad, ozet, sahne_sn, onizleme
 *   sesler         -> ad, ozet, motor, ucret, dil, grup, ornek
 *   profiller      -> ad, tur, video_sayisi, kilitli
 *   paletler       -> ad, ozet, renkler (GERCEK hex)
 * Alan yoksa satir hic cizilmez; tahmini deger URETILMEZ.
 *
 * ⚠ ONIZLEMELER DIS MEDYAYA BAGLI DEGIL: her stil icin 16:9 mini gorsel
 * tamamen CSS ile ve stilin GERCEK metadata'sindan turetiliyor
 * (footage_pct -> alan bolusumu, sahne_sn -> tempo cizgileri). Yani onizleme
 * bir suslemenin degil, olculebilir bir bilginin gorselidir.
 */
import {UCLAR, getirSessiz, yol} from './api.js';
import {$, $$, etiket, kac, uyariKutu} from './bilesenler.js';
import {ikon, ikonlariBagla} from './ikon.js';

/* ════════════════════ YARDIMCILAR ════════════════════ */

/** Deterministik ton (0-359) — ayni id her zaman ayni rengi verir. */
function tonHash(metin) {
  let h = 0;
  for (const c of String(metin || '')) h = (h * 31 + c.charCodeAt(0)) % 100000;
  return h % 360;
}

function sayiVar(v) {
  return v !== undefined && v !== null && v !== '' && Number.isFinite(Number(v));
}

/**
 * Stil metadata'sindan DURUST ozellik etiketleri (en fazla 3).
 * Alan yoksa etiket uretilmez.
 */
export function stilEtiketleri(s) {
  const cikti = [];
  if (sayiVar(s.sahne_sn)) {
    const sn = Number(s.sahne_sn);
    cikti.push(sn <= 4 ? 'Hızlı tempo' : sn <= 6.5 ? 'Dengeli tempo' : 'Sakin tempo');
  }
  if (sayiVar(s.footage_pct)) {
    const f = Number(s.footage_pct);
    cikti.push(f >= 70 ? 'Ağırlıkla gerçek görüntü'
      : f <= 30 ? 'Ağırlıkla grafik' : 'Görüntü + grafik');
  }
  return cikti.slice(0, 3);
}

/**
 * CSS mini onizleme (16:9). Dis medya YOK.
 * `footage_pct` -> sol/sag alan bolusumu · `sahne_sn` -> alt tempo cizgileri.
 */
export function stilOnizleme(s) {
  // ⚠ NEDEN SVG: onizlemenin rengi ve alan bolusumu VERIDEN geliyor
  // (footage_pct, sahne_sn, id hash). Bunu CSS'e tasimak `style="--t:210"`
  // gibi INLINE STIL gerektirirdi; kural inline stil yasakliyor. SVG `fill`
  // bir SUNUM NITELIGIDIR, inline CSS degil — hem kurala uyar hem dis medya
  // gerektirmez.
  const ton = tonHash(s.id ?? s.ad ?? '');
  const foot = sayiVar(s.footage_pct)
    ? Math.max(10, Math.min(90, Number(s.footage_pct))) : 60;
  const sn = sayiVar(s.sahne_sn) ? Math.max(2, Math.min(12, Number(s.sahne_sn))) : 6;
  const adet = Math.max(3, Math.min(9, Math.round(14 / sn)));
  const g = 160;
  const y = 90;
  const fw = Math.round(g * foot / 100);
  const cw = (g - 32) / adet;
  const tikler = Array.from({length: adet}, (_, i) =>
    `<rect x="${(16 + i * cw).toFixed(1)}" y="${y - 10}" width="${
      (cw - 3).toFixed(1)}" height="3" rx="1.5" fill="${
      i === 0 ? '#f5e14b' : '#ffffff'}" opacity="${i === 0 ? '.95' : '.34'}"/>`)
    .join('');
  return `<span class="onizk" aria-hidden="true">
    <svg viewBox="0 0 ${g} ${y}" preserveAspectRatio="none" focusable="false">
      <rect width="${g}" height="${y}" fill="hsl(${ton} 24% 17%)"/>
      <rect width="${fw}" height="${y}" fill="hsl(${ton} 30% 31%)"/>
      <rect x="${fw - 1}" width="1.5" height="${y}" fill="#ffffff" opacity=".16"/>
      <rect x="${g - 48}" y="18" width="34" height="26" rx="3"
        fill="#f5e14b" opacity=".30" stroke="#f5e14b" stroke-opacity=".55"/>
      <rect x="14" y="${y - 34}" width="74" height="11" rx="2"
        fill="#000000" opacity=".62"/>
      <rect x="14" y="${y - 34}" width="2.5" height="11" fill="#f5e14b"/>
      ${tikler}
    </svg>
  </span>`;
}

/**
 * Radio semantics — aria-checked, aria-pressed DEGIL.
 *
 * ⚠ IC ICE ETKILESIMLI KONTROL YASAGI (bagimsiz QA bulgusu): eski surumde
 * "Dinle" dugmesi `<span role="button">` olarak RADIO DUGMESININ ICINDE
 * duruyordu. Bu gecersiz HTML ve erisilebilirlik ihlali: AX agacinda radyonun
 * icinde ayri bir dugme goruluyor, ekran okuyucu ikisini ayirt edemiyor.
 * Cozum: kart ile ek eylem KARDES; ikisi `.sk-sar` kapsayicisinda duruyor.
 * `altEylem` HER ZAMAN butonun DISINA yaziliyor.
 */
function radyoKart({deger, ad, acik = '', etiketler = [], secili, grup,
                    onizleme = '', ekBilgi = '', otomatik = false,
                    altEylem = ''}) {
  const kart = `<button type="button" role="radio" class="sk ${otomatik ? 'sk-oto' : ''}"
    data-grup="${kac(grup)}" data-deger="${kac(deger)}"
    aria-checked="${secili ? 'true' : 'false'}" tabindex="${secili ? '0' : '-1'}">
    ${onizleme}
    <span class="sk-govde">
      <span class="sk-bas">
        ${otomatik ? ikon('otomatik', {boyut: 18}) : ''}
        <span class="sk-ad">${kac(ad)}</span>
        <span class="sk-secili">${ikon('onayDaire', {boyut: 16})}
          <span>Seçildi</span></span>
      </span>
      ${acik ? `<span class="sk-acik">${kac(acik)}</span>` : ''}
      ${etiketler.length ? `<span class="sk-etiketler">${
    etiketler.map((e) => etiket(e)).join('')}</span>` : ''}
      ${ekBilgi ? `<span class="sk-ek">${ekBilgi}</span>` : ''}
    </span>
  </button>`;
  // Ek eylem yoksa sarmalayiciya gerek yok (fazladan DOM uretmiyoruz)
  return altEylem ? `<div class="sk-sar">${kart}${altEylem}</div>` : kart;
}

/**
 * Radyo grubunu bagla: tikla-sec + klavye (oklar, Home/End).
 * ⚠ SIZINTI KORUMASI: her cizimde kap.innerHTML degistigi icin eski dugumler
 * ve dinleyicileri birlikte cop toplaniyor; ayni dugume IKINCI dinleyici
 * eklenmiyor (kap yeniden olusuyor, `_bagli` isareti ile de korunuyor).
 */
export function radyoBagla(kap, grup, geriCagri) {
  const dugmeler = $$(`.sk[data-grup="${grup}"], .cip[data-grup="${grup}"]`, kap);
  if (!dugmeler.length) return;
  const sec = (b) => {
    dugmeler.forEach((x) => {
      const bu = x === b;
      x.setAttribute('aria-checked', bu ? 'true' : 'false');
      x.tabIndex = bu ? 0 : -1;
    });
    geriCagri(b.dataset.deger, b);
  };
  dugmeler.forEach((b, i) => {
    if (b.dataset.bagli === '1') return;
    b.dataset.bagli = '1';
    b.addEventListener('click', () => sec(b));
    b.addEventListener('keydown', (e) => {
      const yon = {ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1}[e.key];
      if (yon) {
        e.preventDefault();
        const h = dugmeler[(i + yon + dugmeler.length) % dugmeler.length];
        h.focus();
        sec(h);
      } else if (e.key === 'Home') {
        e.preventDefault(); dugmeler[0].focus(); sec(dugmeler[0]);
      } else if (e.key === 'End') {
        e.preventDefault();
        dugmeler[dugmeler.length - 1].focus(); sec(dugmeler[dugmeler.length - 1]);
      }
    });
  });
}

/* ════════════════════ GORSEL STIL ════════════════════ */

export const ONERI_SINIRI = 3;

/**
 * Onerilen stiller: API sirasi korunur (sunucu zaten anlamli siralamis).
 * Uydurma "populerlik" ya da "AI onerisi" YOK.
 */
export function onerilenStiller(liste) {
  return liste.slice(0, ONERI_SINIRI);
}

export function stilBolumu({liste, deger, tumunuAc, arama, hataMetni}) {
  const varMi = Array.isArray(liste) && liste.length > 0;
  if (!varMi) {
    return `<section class="sb" id="sbStil">
      <div class="sb-bas"><h3>Görsel stil</h3></div>
      <div class="uyari-kutu">${ikon('uyari', {boyut: 18})}<div>${
      kac(hataMetni || 'Stil listesi alınamadı.')} Üretim varsayılan stille
      devam eder; bu seçim zorunlu değil.</div></div>
    </section>`;
  }

  const aramaVar = liste.length > 6;
  const gosterilen = tumunuAc
    ? (arama
      ? liste.filter((s) => (`${s.ad ?? ''} ${s.ozet ?? ''}`)
        .toLocaleLowerCase('tr').includes(arama.toLocaleLowerCase('tr')))
      : liste)
    : onerilenStiller(liste);

  const kartlar = gosterilen.map((s) => {
    const id = String(s.id ?? s.ad ?? '');
    return radyoKart({
      deger: id, ad: s.ad ?? id, grup: 'stil', secili: deger === id,
      // ⚠ `ozet` yoksa CUMLE UYDURMUYORUZ; guvenli genel metin
      acik: s.ozet || 'Bu stil için açıklama sağlanmadı.',
      etiketler: stilEtiketleri(s), onizleme: stilOnizleme(s),
    });
  }).join('');

  return `<section class="sb" id="sbStil">
    <div class="sb-bas">
      <h3>Görsel stil</h3>
      <p class="sb-alt">Kurgu temposunu, kaynak karışımını ve yazı düzenini belirler.</p>
    </div>
    <div class="sk-izgara" role="radiogroup" aria-label="Görsel stil">
      ${radyoKart({
    deger: '', ad: 'Otomatik — konuya göre önerilen', grup: 'stil',
    secili: !deger, otomatik: true,
    acik: 'Konuyu ve türü okuyup uygun stili sistem seçer. Emin değilsen bunu bırak.',
    etiketler: ['Önerilen'],
  })}
      ${kartlar}
    </div>
    ${!tumunuAc && liste.length > ONERI_SINIRI
    ? `<button type="button" class="dugme dugme-hayalet sb-tumu" data-tumu="stil">
        ${ikon('katman', {boyut: 17})} Tüm stilleri göster (${liste.length})</button>`
    : ''}
    ${tumunuAc && aramaVar
    ? `<div class="sb-arama">
        <label class="gorunmez" for="sbStilArama">Stil ara</label>
        ${ikon('arama', {boyut: 17})}
        <input class="girdi" id="sbStilArama" type="search" placeholder="Stil ara…"
          value="${kac(arama || '')}" autocomplete="off">
      </div>` : ''}
    ${tumunuAc && !gosterilen.length
    ? `<p class="kucuk sessiz sb-bos">Aramaya uyan stil yok.</p>` : ''}
  </section>`;
}

/* ════════════════════ SES ════════════════════ */

/**
 * HARICI SES KATALOGU (`/api/ses-kutuphane`).
 *
 * ⚠ SUNUCU SOZLESMESI (server.py `_OZEL_SES_RE`):
 *     ^ozel:(elevenlabs|minimax|fishaudio|kokoro)_[A-Za-z0-9_-]{1,64}$
 * `_ses_secimi()` bu kalibi TUTMAYAN degeri SESSIZCE bos dizeye cevirir; yani
 * yanlis bicimde gonderilen bir ses hicbir hata vermeden DUSER. Bu yuzden
 * kimlik istemcide de AYNI regexle dogrulaniyor ve gecmeyen ses secilebilir
 * KART OLARAK SUNULMUYOR.
 */
export const KUTUPHANE_SAGLAYICILARI = ['elevenlabs', 'minimax', 'fishaudio',
                                        'kokoro'];
const OZEL_SES_KALIBI =
  /^ozel:(elevenlabs|minimax|fishaudio|kokoro)_[A-Za-z0-9_-]{1,64}$/;

/** voice_id -> generate degeri. Gecersizse '' doner (kart uretilmez). */
export function ozelSesKimligi(saglayici, voiceId) {
  const kimlik = `ozel:${saglayici}_${String(voiceId ?? '')}`;
  return OZEL_SES_KALIBI.test(kimlik) ? kimlik : '';
}

/** Katalog ogesini UI ses modeline normalize et. Gecersiz id -> null. */
export function katalogSesiNormalize(oge, saglayici) {
  const kimlik = ozelSesKimligi(saglayici, oge && oge.voice_id);
  if (!kimlik) return null;
  const diller = Array.isArray(oge.diller) ? oge.diller.filter(Boolean) : [];
  return {
    id: kimlik,
    ad: oge.ad || oge.voice_id,
    ozet: oge.ozet || '',
    motor: saglayici,
    dil: oge.dil || diller[0] || '',
    diller,
    cinsiyet: oge.cinsiyet || '',
    yas: oge.yas || '',
    aksan: oge.aksan || '',
    kategori: oge.kategori || '',
    ornek: oge.onizleme || '',
    harici: true,
  };
}

/**
 * Sagalayici katalogunu getir — panel durumunda ONBELLEKLENIR.
 * ⚠ TEMBEL: yalnizca kullanici paneli acip saglayici sectiginde cagrilir;
 * sayfa acilisinda harici istek YAPILMAZ.
 */
export async function katalogGetir(durum, saglayici) {
  durum.katalog = durum.katalog || {};
  if (durum.katalog[saglayici]) return durum.katalog[saglayici];
  const cevap = await getirSessiz(
    `${UCLAR.sesKutuphane}?saglayici=${encodeURIComponent(saglayici)}`);
  if (!cevap.ok) {
    const kayit = {ok: false, hata: cevap.hata, liste: []};
    durum.katalog[saglayici] = kayit;
    return kayit;
  }
  const ham = Array.isArray(cevap.veri) ? cevap.veri
    : Array.isArray(cevap.veri?.liste) ? cevap.veri.liste : [];
  const liste = ham.map((x) => katalogSesiNormalize(x, saglayici))
    .filter(Boolean);
  const kayit = {ok: true, liste, dusen: ham.length - liste.length};
  durum.katalog[saglayici] = kayit;
  return kayit;
}

/** Sesin GERCEK metadata'sindan etiketler (yoksa uretme). */
export function sesEtiketleri(v) {
  const c = [];
  if (v.dil) c.push(String(v.dil).toLocaleUpperCase('tr'));
  if (v.cinsiyet) c.push(String(v.cinsiyet));
  if (v.yas) c.push(String(v.yas).replace(/_/g, ' '));
  if (!v.cinsiyet && !v.yas) {
    if (v.ucret) c.push(String(v.ucret));
    else if (v.grup === 'ucretsiz') c.push('Ücretsiz');
  }
  if (v.aksan) c.push(String(v.aksan));
  if (c.length < 3 && v.motor) c.push(String(v.motor));
  return c.slice(0, 3);
}

/** Dinle/Durdur — GERCEK <button>, radyo kartinin KARDESI. */
function dinleDugmesi(v, caliyor) {
  if (!v.ornek) return '';
  return `<button type="button" class="ses-dinle"
    data-ornek="${kac(v.ornek)}" data-ses-id="${kac(v.id)}"
    aria-label="${kac(v.ad)} sesini ${caliyor ? 'durdur' : 'dinle'}">
    ${ikon(caliyor ? 'durdur' : 'oynatDaire', {boyut: 17})}
    <span>${caliyor ? 'Durdur' : 'Dinle'}</span></button>`;
}

export function sesBolumu({liste, deger, tumunuAc, arama, suzgec, hataMetni,
                           calan, kaynakSecimi = 'yerel', katalog = null,
                           katalogYukleniyor = false}) {
  const yerel = Array.isArray(liste) ? liste : [];
  if (!yerel.length && kaynakSecimi === 'yerel') {
    return `<section class="sb" id="sbSes">
      <div class="sb-bas"><h3>Anlatıcı sesi</h3></div>
      <div class="uyari-kutu">${ikon('uyari', {boyut: 18})}<div>${
      kac(hataMetni || 'Ses listesi alınamadı.')} Üretim türe uygun sesi
      kendisi seçer.</div></div>
    </section>`;
  }

  // ⚠ Harici katalog HATA verirse YEREL listeye dusuyoruz ve bunu ACIKCA
  // yaziyoruz — sessizce bos liste gostermek "ses yok" yalanidir.
  const katalogHatasi = kaynakSecimi !== 'yerel' && katalog && !katalog.ok;
  const kaynakListe = (kaynakSecimi === 'yerel' || katalogHatasi || !katalog)
    ? yerel : katalog.liste;

  let gosterilen = tumunuAc ? kaynakListe : yerel.slice(0, 3);
  if (tumunuAc) {
    if (suzgec) gosterilen = gosterilen.filter((v) => v.motor === suzgec);
    if (arama) {
      const a = arama.toLocaleLowerCase('tr');
      gosterilen = gosterilen.filter((v) =>
        (`${v.ad ?? ''} ${v.ozet ?? ''} ${v.dil ?? ''} ${v.aksan ?? ''}`)
          .toLocaleLowerCase('tr').includes(a));
    }
  }
  const motorlar = Array.from(new Set(
    (kaynakSecimi === 'yerel' ? yerel : kaynakListe)
      .map((v) => v.motor).filter(Boolean)));

  const kart = (v) => {
    const id = String(v.id ?? v.ad ?? '');
    const caliyor = calan === id;
    return radyoKart({
      deger: id, ad: v.ad ?? id, grup: 'ses', secili: deger === id,
      acik: v.ozet || '', etiketler: sesEtiketleri(v),
      // Ornek yoksa DUGME CIZILMEZ; calismayan dugme yanlis yonlendirir.
      ekBilgi: v.ornek ? '' : '<span class="kucuk sessiz">Örnek kayıt yok</span>',
      altEylem: dinleDugmesi(v, caliyor),
    });
  };

  const kaynakCipleri = `
    <div class="cipler sb-kaynak" role="group" aria-label="Ses kaynağı">
      <button type="button" class="cip" data-kaynak="yerel"
        aria-pressed="${kaynakSecimi === 'yerel'}">Kayıtlı sesler</button>
      ${KUTUPHANE_SAGLAYICILARI.map((sg) => `<button type="button" class="cip"
        data-kaynak="${kac(sg)}" aria-pressed="${kaynakSecimi === sg}">${
    kac(sg)}</button>`).join('')}
    </div>`;

  return `<section class="sb" id="sbSes">
    <div class="sb-bas">
      <h3>Anlatıcı sesi</h3>
      <p class="sb-alt">Videoyu okuyan ses. Sonradan da değiştirebilirsin.</p>
    </div>
    <div class="sk-izgara sk-izgara-ses" role="radiogroup" aria-label="Anlatıcı sesi">
      ${radyoKart({
    deger: '', ad: 'Otomatik — türe uygun ses', grup: 'ses',
    secili: !deger, otomatik: true,
    acik: 'Belgesel, hikâye ve animasyon için farklı ses tonları uygundur; ' +
          'sistem türe göre seçer.',
    etiketler: ['Önerilen'],
  })}
      ${gosterilen.map(kart).join('')}
    </div>
    ${!tumunuAc && yerel.length > 3
    ? `<button type="button" class="dugme dugme-hayalet sb-tumu" data-tumu="ses">
        ${ikon('ses', {boyut: 17})} Tüm sesler (${yerel.length})</button>`
    : ''}
    ${tumunuAc ? `
      ${kaynakCipleri}
      ${katalogYukleniyor
    ? '<p class="kucuk sessiz sb-bos">Katalog yükleniyor…</p>' : ''}
      ${katalogHatasi ? uyariKutu(
    'Harici katalog alınamadı, kayıtlı sesler gösteriliyor. ' +
    `(${kac(katalog.hata || 'sunucu yanıt vermedi')})`, 'uyari') : ''}
      ${katalog && katalog.ok && katalog.dusen
    ? uyariKutu(`${katalog.dusen} ses, sunucunun kabul ettiği kimlik biçimine ` +
      'uymadığı için listelenmedi.', 'bilgi') : ''}
      <div class="sb-suzgec">
        <div class="sb-arama">
          <label class="gorunmez" for="sbSesArama">Ses ara</label>
          ${ikon('arama', {boyut: 17})}
          <input class="girdi" id="sbSesArama" type="search" placeholder="Ses ara…"
            value="${kac(arama || '')}" autocomplete="off">
        </div>
        ${motorlar.length > 1 ? `
          <div class="cipler" role="group" aria-label="Ses sağlayıcısına göre süz">
            <button type="button" class="cip" data-suzgec=""
              aria-pressed="${!suzgec}">Tümü</button>
            ${motorlar.map((m) => `<button type="button" class="cip"
              data-suzgec="${kac(m)}" aria-pressed="${suzgec === m}">${
      kac(m)}</button>`).join('')}
          </div>` : ''}
      </div>
      ${!gosterilen.length && !katalogYukleniyor
    ? '<p class="kucuk sessiz sb-bos">Aramaya uyan ses yok.</p>' : ''}
    ` : ''}
    <p class="kucuk sessiz sb-not" id="sbSesNot" role="status" aria-live="polite"></p>
  </section>`;
}

/**
 * Sesin KULLANICIYA GORUNEN adi.
 *
 * ⚠ BAGIMSIZ QA BULGUSU: ozet paneli yalnizca `kaynak.sesler` icinde ad
 * ariyordu; harici katalogtan secilen ses bulunamayinca BACKEND KIMLIGI
 * ("ozel:elevenlabs_21m00Tcm4TlvDq8ikWAM") kullanici yuzune cikiyordu.
 *
 * Sira: yerel liste -> katalog onbellegi -> DURUST NOTR metin.
 * Katalog henuz yuklenmemisse (sayfa yeniden acildi, kullanici paneli hic
 * acmadi) teknik kimlik GOSTERILMEZ; "Harici ses" yazilir ve ilgili saglayici
 * katalogu yuklendiginde gercek ada kendiliginden guncellenir.
 * ⚠ Bu YALNIZCA GORUNEN metni etkiler; `generate`'e giden deger her zaman
 * `ozel:...` kimligidir.
 */
export function sesGorunenAd(id, {yerel = [], katalog = null,
                                  otoMetin = 'Otomatik (önerilen)'} = {}) {
  if (!id) return otoMetin;
  const kimlik = String(id);
  const yerelKayit = (yerel || []).find((v) => String(v.id ?? v.ad) === kimlik);
  if (yerelKayit) return String(yerelKayit.ad ?? kimlik);

  const m = kimlik.match(/^ozel:(elevenlabs|minimax|fishaudio|kokoro)_/);
  if (m) {
    const kayit = katalog && katalog[m[1]];
    const bulunan = (kayit && kayit.ok ? kayit.liste : [])
      .find((v) => String(v.id) === kimlik);
    if (bulunan) return String(bulunan.ad ?? kimlik);
    // Katalog yuklenmemis/hatali: teknik kimligi ASLA gostermiyoruz
    return `Harici ses · ${m[1]}`;
  }
  return kimlik;
}


/** Tek ornek oynatici — ayni anda tek ses. */
let _oynatici = null;
let _calanId = '';

export function sesCal(ornekYolu, id, {bittiginde, hataninda} = {}) {
  sesDurdur();
  try {
    _oynatici = new Audio(yol(ornekYolu));
    _calanId = id;
    _oynatici.addEventListener('ended', () => { _calanId = ''; bittiginde?.(); });
    _oynatici.addEventListener('error', () => {
      _calanId = '';
      hataninda?.('Örnek kayıt çalınamadı.');
    });
    const p = _oynatici.play();
    if (p && typeof p.catch === 'function') {
      p.catch(() => { _calanId = ''; hataninda?.('Örnek kayıt çalınamadı.'); });
    }
  } catch {
    _calanId = '';
    hataninda?.('Bu tarayıcı örnek kaydı çalamadı.');
  }
}

export function sesDurdur() {
  if (_oynatici) {
    try { _oynatici.pause(); } catch { /* yoksay */ }
    _oynatici = null;
  }
  _calanId = '';
}

export function calanSes() { return _calanId; }

/* ════════════════════ MARKA KITI ════════════════════ */

export function markaBolumu({liste, deger, hataVar}) {
  const kayitlar = Array.isArray(liste) ? liste : [];
  return `<section class="sb" id="sbMarka">
    <div class="sb-bas">
      <h3>Marka kiti</h3>
      <p class="sb-alt">Videolar arasında renk ve karakter tutarlılığı sağlar.</p>
    </div>
    <div class="cipler" role="radiogroup" aria-label="Marka kiti">
      <button type="button" role="radio" class="cip cip-oto" data-grup="marka"
        data-deger="" aria-checked="${!deger}" tabindex="${!deger ? '0' : '-1'}">
        ${ikon('otomatik', {boyut: 16})}<span>Yok — marka kiti kullanma</span>
      </button>
      ${kayitlar.map((p) => {
    const id = String(p.id ?? p.pid ?? '');
    const ek = [];
    if (p.tur) ek.push(String(p.tur));
    if (sayiVar(p.video_sayisi)) ek.push(`${p.video_sayisi} video`);
    if (p.kilitli) ek.push('kilitli');
    return `<button type="button" role="radio" class="cip" data-grup="marka"
        data-deger="${kac(id)}" aria-checked="${deger === id}"
        tabindex="${deger === id ? '0' : '-1'}">
        ${ikon('kanal', {boyut: 16})}<span>${kac(p.ad ?? id)}</span>
        ${ek.length ? `<small>${kac(ek.join(' · '))}</small>` : ''}
      </button>`;
  }).join('')}
    </div>
    ${!kayitlar.length ? `<p class="kucuk sessiz sb-bos">${hataVar
    ? 'Marka kiti listesi alınamadı; bu seçim atlanabilir.'
    : 'Kayıtlı marka kiti yok. Üretim sırasında oluşturulabilir.'}</p>` : ''}
  </section>`;
}

/* ════════════════════ HIZLI TERCIHLER ════════════════════ */

/** Uc anlasilir tercih — teknik ad YOK. */
export function hizliTercihler({gecis, zoom, altyazi}) {
  const oge = (id, imAd, ad, acik, acikMi) => `
    <label class="ht" for="${id}">
      <input type="checkbox" id="${id}" ${acikMi ? 'checked' : ''}>
      <span class="ht-govde">
        <span class="ht-bas">${ikon(imAd, {boyut: 17})}
          <span class="ht-ad">${kac(ad)}</span>
          <span class="anahtar-gorsel" aria-hidden="true"></span></span>
        <span class="ht-acik">${kac(acik)}</span>
      </span>
    </label>`;
  return `<section class="sb" id="sbHizli">
    <div class="sb-bas"><h3>Hızlı tercihler</h3></div>
    <div class="ht-izgara">
      ${oge('wzGecis', 'hareket', 'Akıcı geçiş',
    'Sahneler yumuşak geçer. Kapalıysa sert kesme olur.', gecis)}
      ${oge('wzZoom', 'gorsel', 'Hafif kamera hareketi',
    'Görüntü çok yavaş yaklaşır; sabit fotoğraf hissini kırar.', zoom)}
      ${oge('wzAltyazi', 'altyaziIm', 'Altyazı',
    'Videoya yazılır, sonradan kapatılamaz.', altyazi)}
    </div>
  </section>`;
}

/* ════════════════════ PROFESYONEL AYARLAR ════════════════════ */

export const PRO_BOLUMLER = [
  {id: 'renk', ad: 'Renk ve atmosfer', im: 'palet'},
  {id: 'hareket', ad: 'Hareket ve açılış', im: 'hareket'},
  {id: 'altyazi', ad: 'Altyazı görünümü', im: 'altyaziIm'},
  {id: 'uretim', ad: 'Üretim ve referans', im: 'cip'},
];

/** Renk seridi — GERCEK hex'ler SVG `fill` niteligiyle (inline stil YOK). */
function paletSeridi(renkler) {
  const n = renkler.length;
  const w = 100 / n;
  return `<span class="pk-serit" aria-hidden="true">
    <svg viewBox="0 0 100 20" preserveAspectRatio="none" focusable="false">
      ${renkler.map((h, i) => `<rect x="${(i * w).toFixed(2)}" y="0" width="${
    (w + 0.2).toFixed(2)}" height="20" fill="${kac(h)}"/>`).join('')}
    </svg></span>`;
}


/** Palet kartlari — GERCEK hex dizisiyle. */
function paletKartlari(paletler, secili) {
  const liste = Array.isArray(paletler) ? paletler : [];
  const kart = (p) => {
    const id = String(p.id ?? '');
    const renkler = Array.isArray(p.renkler) ? p.renkler.slice(0, 6) : [];
    return `<button type="button" role="radio" class="pk" data-grup="palet"
      data-deger="${kac(id === 'otomatik' ? '' : id)}"
      aria-checked="${(secili || '') === (id === 'otomatik' ? '' : id)}"
      tabindex="${(secili || '') === (id === 'otomatik' ? '' : id) ? '0' : '-1'}">
      ${renkler.length ? paletSeridi(renkler) : '<span class="pk-serit pk-oto-serit" aria-hidden="true"></span>'}
      <span class="pk-ad">${kac(p.ad ?? id)}</span>
      <span class="sk-secili">${ikon('onayDaire', {boyut: 14})}<span>Seçildi</span></span>
    </button>`;
  };
  return `<div class="pk-izgara" role="radiogroup" aria-label="Renk paleti">
    ${liste.map(kart).join('')}
    <button type="button" role="radio" class="pk pk-ozel" data-grup="palet"
      data-deger="ozel" aria-checked="${secili === 'ozel'}"
      tabindex="${secili === 'ozel' ? '0' : '-1'}">
      <span class="pk-serit pk-oto-serit" aria-hidden="true"></span>
      <span class="pk-ad">Kendi renklerim</span>
      <span class="sk-secili">${ikon('onayDaire', {boyut: 14})}<span>Seçildi</span></span>
    </button>
  </div>`;
}

/** `secenekler` API listesinden select uret; bos ise alani GIZLEMEZ, not duser. */
function proSecim({id, ad, ipucu, liste, deger, otomatikAd = 'Otomatik (önerilen)'}) {
  const kayitlar = Array.isArray(liste) ? liste : [];
  return `<div class="alan">
    <label class="alan-ad" for="${id}">${kac(ad)}</label>
    <select class="secim" id="${id}" aria-describedby="${id}-ipucu">
      <option value="" ${!deger ? 'selected' : ''}>${kac(otomatikAd)}</option>
      ${kayitlar.filter((x) => String(x.id ?? '') !== 'otomatik').map((x) => {
    const v = String(x.id ?? x.ad ?? '');
    return `<option value="${kac(v)}" ${deger === v ? 'selected' : ''}>${
      kac(x.ad ?? v)}</option>`;
  }).join('')}
    </select>
    <span class="alan-ipucu" id="${id}-ipucu">${kac(ipucu)}${
    kayitlar.length ? '' : ' Liste alınamadı; otomatik kullanılacak.'}</span>
  </div>`;
}

export function proPanel({acik, t, kaynak}) {
  const bolum = (b, ic) => `
    <section class="pro-bolum" data-pro="${b.id}">
      <h4 class="pro-bas">
        <button type="button" class="pro-dugme" data-pro-ac="${b.id}"
          aria-expanded="${acik === b.id}" aria-controls="pro-${b.id}">
          ${ikon(b.im, {boyut: 17})}<span>${kac(b.ad)}</span>
          ${ikon('ok', {boyut: 15, sinif: 'pro-ok'})}
        </button>
      </h4>
      <div class="pro-ic" id="pro-${b.id}" ${acik === b.id ? '' : 'hidden'}>${ic}</div>
    </section>`;

  const renkIc = `
    <p class="pro-not">Varsayılan önerilir: stilin kendi renk ailesi kullanılır.</p>
    ${paletKartlari(kaynak.paletler, t.palet)}
    <div id="wzPaletOzel" class="${t.palet === 'ozel' ? '' : 'gorunmez'}">
      <span class="alan-ad">Kendi renklerim</span>
      <div class="renkler">${t.paletOzel.map((h, i) => `
        <label class="gorunmez" for="wzHex${i}">Özel renk ${i + 1}</label>
        <input type="color" id="wzHex${i}" value="${kac(h)}"
          aria-label="Özel renk ${i + 1}">`).join('')}</div>
    </div>
    ${proSecim({id: 'wzIsik', ad: 'Işık düzeyi', deger: t.isik,
    liste: kaynak.isikDuzeyleri,
    ipucu: 'Sahnenin genel aydınlığı. Varsayılan önerilir.'})}
    ${proSecim({id: 'wzArkaplan', ad: 'Arka plan', deger: t.arkaplan,
    liste: kaynak.arkaplanlar,
    ipucu: 'Mekân yoğunluğu. Varsayılan önerilir.'})}`;

  const hareketIc = `
    <p class="pro-not">Hızlı tercihlerdeki iki anahtarın ayrıntılı karşılığı burada.</p>
    ${t.tur === 'hikaye' ? `
      ${proSecim({id: 'wzAcilis', ad: 'Hikâye açılışı', deger: t.acilis,
    liste: [{id: 'soru', ad: 'Soru ile'}, {id: 'sahne', ad: 'Sahne ile'},
      {id: 'alinti', ad: 'Alıntı ile'}],
    ipucu: 'Videonun ilk saniyelerinin kuruluşu.'})}
      <label class="anahtar" for="wzSora">
        <input type="checkbox" id="wzSora" ${t.sora ? 'checked' : ''}>
        <span class="anahtar-gorsel" aria-hidden="true"></span>
        <span class="anahtar-yazi">Hareketli açılış planı
          <small>Açılış için video modeli kullanılır; süre ve maliyet artar.</small>
        </span></label>`
    : '<p class="pro-not">Açılış ve hareketli plan seçenekleri yalnızca ' +
      'Hikâye türünde geçerlidir.</p>'}`;

  const altyaziIc = `
    <p class="pro-not">Altyazı kapalıysa bu ayarlar üretimde kullanılmaz.</p>
    ${proSecim({id: 'wzAltSablon', ad: 'Altyazı şablonu',
    deger: (t.altyaziSablon && t.altyaziSablon.id) || '',
    liste: kaynak.altyaziSablonlari, otomatikAd: 'Varsayılan',
    ipucu: 'Hazır yazı düzenleri.'})}
    <div class="izgara izgara-2">
      <div class="alan">
        <label class="alan-ad" for="wzAltBoyut">Punto</label>
        <input class="girdi" type="number" id="wzAltBoyut" min="18" max="120"
          value="${kac((t.altyaziSablon && t.altyaziSablon.boyut) || 42)}">
        <span class="alan-ipucu">Yazı boyutu. Varsayılan önerilir.</span>
      </div>
      <div class="alan">
        <label class="alan-ad" for="wzAltKonum">Konum</label>
        <select class="secim" id="wzAltKonum">
          ${[['alt', 'Altta'], ['orta', 'Ortada'], ['ust', 'Üstte']].map(([v, a]) =>
    `<option value="${v}" ${(t.altyaziSablon && t.altyaziSablon.konum) === v
      ? 'selected' : ''}>${a}</option>`).join('')}
        </select>
        <span class="alan-ipucu">Ekrandaki yeri.</span>
      </div>
    </div>
    <fieldset class="alan pro-fieldset">
      <legend class="alan-ad">Yazı ve kontur rengi</legend>
      <div class="renkler">
        <label class="gorunmez" for="wzAltRenk">Yazı rengi</label>
        <input type="color" id="wzAltRenk" aria-label="Yazı rengi"
          value="${kac((t.altyaziSablon && t.altyaziSablon.renk) || '#ffffff')}">
        <label class="gorunmez" for="wzAltKontur">Kontur rengi</label>
        <input type="color" id="wzAltKontur" aria-label="Kontur rengi"
          value="${kac((t.altyaziSablon && t.altyaziSablon.kontur) || '#000000')}">
      </div>
    </fieldset>
    <label class="anahtar" for="wzAltBuyuk">
      <input type="checkbox" id="wzAltBuyuk"
        ${t.altyaziSablon && t.altyaziSablon.buyuk ? 'checked' : ''}>
      <span class="anahtar-gorsel" aria-hidden="true"></span>
      <span class="anahtar-yazi">BÜYÜK HARF</span></label>
    <label class="anahtar" for="wzAltGolge">
      <input type="checkbox" id="wzAltGolge"
        ${t.altyaziSablon && t.altyaziSablon.golge ? 'checked' : ''}>
      <span class="anahtar-gorsel" aria-hidden="true"></span>
      <span class="anahtar-yazi">Gölge<small>Okunurluğu artırır.</small></span></label>`;

  const uretimIc = `
    <p class="pro-not">Bu alanlar boş bırakıldığında sistem kendi kararını verir.</p>
    ${proSecim({id: 'wzModel', ad: 'Görsel model', deger: t.gorselModel,
    liste: [{id: 'gpt-image', ad: 'gpt-image'}, {id: 'gemini', ad: 'gemini'}],
    ipucu: 'Yalnızca görsel üretilen türlerde etkili.'})}
    <div class="izgara izgara-2">
      <div class="alan">
        <span class="alan-ad">Karakter görseli</span>
        <div class="birak birak-kucuk" id="wzKarBirak" role="button" tabindex="0"
          aria-label="Karakter görseli seç">
          ${ikon('yukle', {boyut: 20})}<span class="birak-ad">Seç</span>
          <label class="gorunmez" for="wzKarGirdi">Karakter görseli dosyası</label>
          <input type="file" id="wzKarGirdi" accept="image/*" class="gorunmez">
        </div>
        <span class="alan-ipucu" id="wzKarAd">Seçilmedi</span>
      </div>
      <div class="alan">
        <span class="alan-ad">Stil görseli</span>
        <div class="birak birak-kucuk" id="wzStilBirak" role="button" tabindex="0"
          aria-label="Stil görseli seç">
          ${ikon('yukle', {boyut: 20})}<span class="birak-ad">Seç</span>
          <label class="gorunmez" for="wzStilGirdi">Stil görseli dosyası</label>
          <input type="file" id="wzStilGirdi" accept="image/*" class="gorunmez">
        </div>
        <span class="alan-ipucu" id="wzStilAd">Seçilmedi</span>
      </div>
    </div>`;

  return `<section class="pro" id="sbPro">
    <div class="sb-bas">
      <h3>Profesyonel ayarlar</h3>
      <p class="sb-alt">Gerekmedikçe dokunma; her bölüm için varsayılan önerilir.</p>
    </div>
    ${bolum(PRO_BOLUMLER[0], renkIc)}
    ${bolum(PRO_BOLUMLER[1], hareketIc)}
    ${bolum(PRO_BOLUMLER[2], altyaziIc)}
    ${bolum(PRO_BOLUMLER[3], uretimIc)}
  </section>`;
}

/* ════════════════════ SECIM OZETI ════════════════════ */

/**
 * Canli ozet. ⚠ SAHTE MALIYET / KALITE PUANI / "AI onerisi %" YOK —
 * yalnizca kullanicinin sectikleri.
 */
export function ozetPaneli({t, kaynak, dosyaSayisi, acik = false,
                            katalog = null}) {
  const ad = (liste, id, otoMetin) => {
    if (!id) return otoMetin;
    const bulunan = (liste || []).find((x) => String(x.id ?? x.ad) === String(id));
    return bulunan ? String(bulunan.ad ?? id) : String(id);
  };
  const stilListe = t.tur === 'animasyon' ? kaynak.animStilleri : kaynak.editStilleri;
  const stilId = t.tur === 'animasyon' ? t.animStili : t.editStili;
  const stilAd = ad(stilListe, stilId, 'Otomatik');
  // ⚠ Harici ses adi katalog onbellegiden cozulur; raw `ozel:` kimligi
  // kullanici yuzune CIKMAZ.
  const sesAd = sesGorunenAd(t.ses, {yerel: kaynak.sesler, katalog,
                                     otoMetin: 'Otomatik'});
  const atmosfer = [
    t.palet === 'ozel' ? 'kendi renklerim'
      : ad(kaynak.paletler, t.palet, 'otomatik renk'),
    ad(kaynak.isikDuzeyleri, t.isik, 'otomatik ışık'),
  ].filter(Boolean).join(' · ');

  const satir = (etiketMetni, deger, hedef) => `
    <div class="oz-satir">
      <span class="oz-ad">${kac(etiketMetni)}</span>
      <span class="oz-deg">${kac(deger)}</span>
      <button type="button" class="oz-degistir" data-odak="${kac(hedef)}">Değiştir</button>
    </div>`;

  // ⚠ MOBIL OLCUMU (Faz G, 390x844): tam ozet karti 255px yuksekligindeydi ve
  // ilk ekranin ucte birini yiyordu — eski arayuzun tam da elestirilen sorunu.
  // Mobilde ozet KISA SERIT olarak duruyor, dokununca aciliyor. Masaustunde
  // tam panel (sticky) degismiyor; CSS ayirimi yapiyor.
  const serit = `${kac(stilAd)} · ${kac(sesAd)} · altyazı ${
    t.altyazi ? 'açık' : 'kapalı'}`;

  return `<aside class="oz" id="sbOzet" aria-label="Seçim özeti"
    data-acik="${acik ? '1' : '0'}">
    <div class="oz-tepe">
      <h3 class="oz-bas">Seçim özeti</h3>
      <button type="button" class="oz-ac" id="wzOzetAc"
        aria-expanded="${acik ? 'true' : 'false'}" aria-controls="ozGovde">
        <span class="oz-serit">${serit}</span>
        ${ikon('ok', {boyut: 15, sinif: 'oz-ok'})}
      </button>
    </div>
    <div class="oz-govde" id="ozGovde">
      ${satir('Görsel stil', stilAd === 'Otomatik' ? 'Otomatik (önerilen)' : stilAd, 'sbStil')}
      ${satir('Ses', sesAd === 'Otomatik' ? 'Otomatik (önerilen)' : sesAd, 'sbSes')}
      ${satir('Marka kiti', ad(kaynak.profiller, t.profil, 'Yok'), 'sbMarka')}
      ${satir('Altyazı', t.altyazi ? 'Açık' : 'Kapalı', 'sbHizli')}
      ${satir('Atmosfer', atmosfer || 'otomatik', 'sbPro')}
      ${satir('Referans görsel', dosyaSayisi ? `${dosyaSayisi} dosya` : 'yok', 'sbPro')}
      <button type="button" class="dugme dugme-hayalet oz-oneri" id="wzOnerileniKullan">
        ${ikon('otomatik', {boyut: 17})} Önerileni kullan</button>
      <p class="kucuk sessiz oz-not">Yalnızca yukarıdaki seçimler otomatiğe döner;
        konu metnin ve yüklediğin dosyalar korunur.</p>
    </div>
  </aside>`;
}

/**
 * "Onerileni kullan" — TEMEL secimleri guvenli otomatige dondurur.
 * ⚠ Konu metni ve YUKLENEN DOSYALAR ASLA silinmez.
 */
export const ONERILEN_VARSAYILAN = {
  editStili: '', animStili: '', ses: '', profil: '',
  palet: '', isik: '', arkaplan: '', gorselModel: '',
  gecis: true, zoom: true, altyazi: false,
  acilis: '', sora: false, altyaziSablon: null,
};

/* ════════════════════ ADIM 3 KURULUMU ════════════════════ */
/**
 * Adim 3'un GOVDESI ve OLAYLARI burada — `wizard.js` yalnizca cagiriyor.
 * ⚠ DONGUSEL BAGIMLILIK YOK: wizard'in fonksiyonlari (taslak, taslakYaz,
 * dosyaAlaniBagla, duyur, yenidenCiz) PARAMETRE olarak geliyor; bu modul
 * wizard'i import etmiyor.
 */
export function bosDurum() {
  return {stilTumu: false, stilArama: '', sesTumu: false, sesArama: '',
          sesSuzgec: '', proAcik: '', ozetAcik: false,
          // Harici ses katalogu: yalnizca panel acilip saglayici secilince
          // doldurulur; ayni saglayici icin ikinci istek atilmaz.
          sesKaynagi: 'yerel', katalog: {}, katalogYukleniyor: false};
}

export function adim3Govde({t, kaynak, durum, dosyalar}) {
  const stilListe = t.tur === 'animasyon'
    ? (kaynak.animStilleri || []) : (kaynak.editStilleri || []);
  const stilDeger = t.tur === 'animasyon' ? t.animStili : t.editStili;
  const hataVar = (kaynak.hatalar || []).some((h) => h.ad === 'profiller');
  const dosyaSayisi = dosyalar.sahneRef.length + (dosyalar.karakter ? 1 : 0)
    + (dosyalar.stil ? 1 : 0);
  return `<h2>Görsel yön</h2>
  <p class="kucuk orta adim-giris">Önerileni seçebilir veya ayrıntıları kendin
    ayarlayabilirsin.</p>
  <div class="a3">
    <div class="a3-form">
      ${stilBolumu({liste: stilListe, deger: stilDeger,
    tumunuAc: durum.stilTumu, arama: durum.stilArama})}
      ${sesBolumu({liste: kaynak.sesler, deger: t.ses, tumunuAc: durum.sesTumu,
    arama: durum.sesArama, suzgec: durum.sesSuzgec, calan: calanSes(),
    kaynakSecimi: durum.sesKaynagi,
    katalog: durum.katalog[durum.sesKaynagi] || null,
    katalogYukleniyor: durum.katalogYukleniyor})}
      ${markaBolumu({liste: kaynak.profiller, deger: t.profil, hataVar})}
      ${hizliTercihler({gecis: t.gecis, zoom: t.zoom, altyazi: t.altyazi})}
      ${proPanel({acik: durum.proAcik, t, kaynak})}
    </div>
    <div class="a3-ozet">
      ${ozetPaneli({t, kaynak, dosyaSayisi, acik: durum.ozetAcik,
    katalog: durum.katalog})}
    </div>
  </div>`;
}

export function adim3Kur(baglam) {
  const {kap, durum, taslak, taslakYaz, kaynak, dosyalar, dosyaAlaniBagla,
         duyur, yenidenCiz} = baglam;
  if (!kap) return;

  const dosyaSayisi = () => dosyalar.sahneRef.length
    + (dosyalar.karakter ? 1 : 0) + (dosyalar.stil ? 1 : 0);

  /** Ozet panelini YERINDE tazele. */
  const ozetiTazele = () => {
    const eski = $('#sbOzet');
    if (!eski) return;
    const gecici = document.createElement('div');
    gecici.innerHTML = ozetPaneli({t: taslak(), kaynak,
      dosyaSayisi: dosyaSayisi(), acik: durum.ozetAcik,
      katalog: durum.katalog});
    const yeni = gecici.firstElementChild;
    eski.replaceWith(yeni);
    ikonlariBagla(yeni);
    ozetBagla(yeni);
  };

  /** Bir bolumu YERINDE tazele (tum adimi yeniden cizmeden). */
  const bolumuTazele = (secici, uretici) => {
    const eski = $(secici);
    if (!eski) return null;
    const gecici = document.createElement('div');
    gecici.innerHTML = uretici();
    const yeni = gecici.firstElementChild;
    if (!yeni) return null;
    eski.replaceWith(yeni);
    ikonlariBagla(yeni);
    return yeni;
  };

  const stilTazele = (odak) => {
    const t = taslak();
    const yeni = bolumuTazele('#sbStil', () => stilBolumu({
      liste: t.tur === 'animasyon'
        ? (kaynak.animStilleri || []) : (kaynak.editStilleri || []),
      deger: t.tur === 'animasyon' ? t.animStili : t.editStili,
      tumunuAc: durum.stilTumu, arama: durum.stilArama,
    }));
    if (!yeni) return;
    radyoBagla(yeni, 'stil', (v) => {
      taslakYaz(taslak().tur === 'animasyon' ? {animStili: v} : {editStili: v});
      ozetiTazele();
    });
    tumuBagla(yeni);
    const ara = $('#sbStilArama', yeni);
    if (ara) {
      ara.addEventListener('input', () => {
        durum.stilArama = ara.value;
        stilTazele('#sbStilArama');
      });
      if (odak) { ara.focus(); ara.setSelectionRange(ara.value.length, ara.value.length); }
    }
  };

  const sesTazele = (odak) => {
    const t = taslak();
    const yeni = bolumuTazele('#sbSes', () => sesBolumu({
      liste: kaynak.sesler, deger: t.ses, tumunuAc: durum.sesTumu,
      arama: durum.sesArama, suzgec: durum.sesSuzgec, calan: calanSes(),
      kaynakSecimi: durum.sesKaynagi,
      katalog: durum.katalog[durum.sesKaynagi] || null,
      katalogYukleniyor: durum.katalogYukleniyor,
    }));
    if (!yeni) return;
    radyoBagla(yeni, 'ses', (v) => { taslakYaz({ses: v}); ozetiTazele(); });
    tumuBagla(yeni);
    dinleBagla(yeni);
    kaynakBagla(yeni);
    $$('[data-suzgec]', yeni).forEach((b) => b.addEventListener('click', () => {
      durum.sesSuzgec = b.dataset.suzgec || '';
      sesTazele(false);
    }));
    const ara = $('#sbSesArama', yeni);
    if (ara) {
      ara.addEventListener('input', () => {
        durum.sesArama = ara.value;
        sesTazele(true);
      });
      if (odak) { ara.focus(); ara.setSelectionRange(ara.value.length, ara.value.length); }
    }
  };

  /**
   * Ses kaynagi ciplerini bagla — harici katalog TEMBEL yuklenir.
   * ⚠ Kullanici paneli acip saglayiciya dokunmadan HICBIR harici istek yok.
   */
  function kaynakBagla(kok) {
    $$('[data-kaynak]', kok).forEach((b) => b.addEventListener('click', async () => {
      const sg = b.dataset.kaynak;
      durum.sesKaynagi = sg;
      durum.sesSuzgec = '';
      if (sg === 'yerel' || durum.katalog[sg]) { sesTazele(false); return; }
      durum.katalogYukleniyor = true;
      sesTazele(false);
      try {
        await katalogGetir(durum, sg);
      } finally {
        durum.katalogYukleniyor = false;
        sesTazele(false);
        // Katalog geldi: ozetteki "Harici ses" artik GERCEK ada donusebilir
        ozetiTazele();
      }
    }));
  }

  function tumuBagla(kok) {
    $$('[data-tumu]', kok).forEach((b) => b.addEventListener('click', () => {
      if (b.dataset.tumu === 'stil') { durum.stilTumu = true; stilTazele(false); }
      else { durum.sesTumu = true; sesTazele(false); }
    }));
  }

  function dinleBagla(kok) {
    $$('.ses-dinle', kok).forEach((d) => {
      // ⚠ Dugme artik radyo kartinin KARDESI; tiklama karta ulasmiyor, yani
      // "Dinle" ses SECIMINI DEGISTIRMIYOR. `stopPropagation` yine duruyor:
      // ileride kart sarmalayiciya tiklama eklenirse kaza olmasin.
      const calistir = (e) => {
        e.stopPropagation();
        e.preventDefault();
        if (calanSes() === d.dataset.sesId) { sesDurdur(); sesTazele(false); return; }
        sesCal(d.dataset.ornek, d.dataset.sesId, {
          bittiginde: () => sesTazele(false),
          hataninda: (m) => {
            sesTazele(false);
            const n = $('#sbSesNot');
            if (n) n.textContent = m;      // DURUST hata; sessiz basarisizlik yok
          },
        });
        sesTazele(false);
      };
      d.addEventListener('click', calistir);
      d.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') calistir(e);
      });
    });
  }

  function ozetBagla(kok) {
    const ac = $('#wzOzetAc', kok);
    if (ac) ac.addEventListener('click', () => {
      durum.ozetAcik = !durum.ozetAcik;
      const oz = kok.matches?.('.oz') ? kok : $('.oz', kok);
      if (oz) oz.dataset.acik = durum.ozetAcik ? '1' : '0';
      ac.setAttribute('aria-expanded', String(durum.ozetAcik));
    });
    $$('[data-odak]', kok).forEach((b) => b.addEventListener('click', () => {
      const hedef = document.getElementById(b.dataset.odak);
      if (!hedef) return;
      if (b.dataset.odak === 'sbPro' && !durum.proAcik) {
        const ilk = $('[data-pro-ac]');
        if (ilk) ilk.click();
      }
      hedef.scrollIntoView({block: 'start', behavior: 'auto'});
      const o = hedef.querySelector('button, [tabindex="0"], select, input');
      if (o) o.focus({preventScroll: true});
    }));
    const oneri = $('#wzOnerileniKullan', kok);
    if (oneri) oneri.addEventListener('click', () => {
      // ⚠ Konu metni ve YUKLENEN DOSYALAR korunur.
      taslakYaz({...ONERILEN_VARSAYILAN});
      Object.assign(durum, bosDurum());
      sesDurdur();
      yenidenCiz();
      duyur('Temel seçimler önerilen değerlere döndü');
    });
  }

  // ── Ilk baglama ──
  radyoBagla(kap, 'stil', (v) => {
    taslakYaz(taslak().tur === 'animasyon' ? {animStili: v} : {editStili: v});
    ozetiTazele();
  });
  radyoBagla(kap, 'ses', (v) => { taslakYaz({ses: v}); ozetiTazele(); });
  radyoBagla(kap, 'marka', (v) => { taslakYaz({profil: v}); ozetiTazele(); });
  radyoBagla(kap, 'palet', (v) => {
    taslakYaz({palet: v});
    const oz = $('#wzPaletOzel');
    if (oz) oz.classList.toggle('gorunmez', v !== 'ozel');
    ozetiTazele();
  });
  tumuBagla(kap);
  dinleBagla(kap);
  kaynakBagla(kap);
  ozetBagla(kap);
  const sArama = $('#sbStilArama', kap);
  if (sArama) sArama.addEventListener('input', () => {
    durum.stilArama = sArama.value; stilTazele(true);
  });
  const sesAra = $('#sbSesArama', kap);
  if (sesAra) sesAra.addEventListener('input', () => {
    durum.sesArama = sesAra.value; sesTazele(true);
  });
  $$('[data-suzgec]', kap).forEach((b) => b.addEventListener('click', () => {
    durum.sesSuzgec = b.dataset.suzgec || '';
    sesTazele(false);
  }));

  // ── Hizli tercihler ──
  [['wzGecis', 'gecis'], ['wzZoom', 'zoom'], ['wzAltyazi', 'altyazi']]
    .forEach(([id, ad]) => {
      const el = document.getElementById(id);
      if (el) el.addEventListener('change', () => {
        taslakYaz({[ad]: el.checked}); ozetiTazele();
      });
    });

  // ── Profesyonel akordeon: AYNI ANDA TEK acik ──
  $$('[data-pro-ac]', kap).forEach((b) => b.addEventListener('click', () => {
    const hedef = b.dataset.proAc;
    durum.proAcik = durum.proAcik === hedef ? '' : hedef;
    PRO_BOLUMLER.forEach((x) => {
      const d = $(`[data-pro-ac="${x.id}"]`, kap);
      const ic = document.getElementById(`pro-${x.id}`);
      const acikMi = durum.proAcik === x.id;
      if (d) d.setAttribute('aria-expanded', String(acikMi));
      if (ic) ic.hidden = !acikMi;
    });
  }));

  // ── Profesyonel alanlar ──
  [['wzIsik', 'isik'], ['wzArkaplan', 'arkaplan'], ['wzAcilis', 'acilis'],
   ['wzModel', 'gorselModel']].forEach(([id, ad]) => {
    const el = document.getElementById(id);
    if (el) el.addEventListener('change', () => {
      taslakYaz({[ad]: el.value}); ozetiTazele();
    });
  });
  const sora = $('#wzSora', kap);
  if (sora) sora.addEventListener('change', () => taslakYaz({sora: sora.checked}));

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

  dosyaAlaniBagla('#wzKarBirak', '#wzKarGirdi', false, (f) => {
    dosyalar.karakter = f;
    const e = $('#wzKarAd'); if (e) e.textContent = f.name;
    ozetiTazele();
  });
  dosyaAlaniBagla('#wzStilBirak', '#wzStilGirdi', false, (f) => {
    dosyalar.stil = f;
    const e = $('#wzStilAd'); if (e) e.textContent = f.name;
    ozetiTazele();
  });
}
