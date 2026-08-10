/**
 * EFEKT KUTUPHANESI — @adobemadesimple kanalindaki AE/Premiere efektlerinin
 * Remotion'da KODLA uretilen karsiliklari (7 Agu 2026).
 *
 * Kanalin 80 videosu tarandi. Efektler uc gruba ayrildi:
 *
 *  ✅ KODLANABILIR (bu dosyada): matematik isi olanlar — transform, filter, SVG, mask.
 *     fade, glitch, 3D spin, zoom/dolly zoom, shake (yumusak/agresif), motion blur,
 *     directional speed blur, siyah-beyaz, renk derecelendirme, flash gecis, glitch gecis,
 *     smooth zoom gecis, letterbox/kirpma, yuvarlak kose, kenarlik, grain, vinyet,
 *     kromatik sapma, glow/bloom, isik sizmasi, hayalet-hologram, ikon parlamasi,
 *     yazi: daktilo / ziplama / titreme / yayilma / kayan / rastgele / yumusak giris,
 *     yazi icinde video (mask), cizgi cizilmesi, daire animasyonu, nesne suzulmesi.
 *
 *  ⚠ SINIRLI: sahne icerigini BILMEYI gerektirenler. Motor sahneyi tanimiyor (prompt'la
 *     uretiyor ya da stoktan cekiyor), o yuzden "nesnenin arkasina yazi", "hareketli
 *     nesneyi cerceveleme", "yuz takibi", "arka plan silme" tam yapilamaz. Bunlar icin
 *     nesne algilama katmani gerekir — ayri is.
 *
 *  ❌ KAPSAM DISI: Premiere/AE arayuz egitimi, ses temizleme, export ayarlari, oynatma
 *     performansi. Bizim motorda karsiligi yok.
 *
 * TASARIM: her efekt SAF fonksiyon — (frame, fps, sure, siddet) -> CSS/SVG. Rastgelelik
 * TOHUMLU (sahne indeksinden), yoksa her render farkli cikar ve tekrar uretilemez.
 */
import React from 'react';
import {AbsoluteFill, Easing, interpolate, random, spring, useCurrentFrame,
  useVideoConfig} from 'remotion';
import {fontAilesi} from './fontlar';

/* ═══════════════════════ ortak yardimcilar ═══════════════════════ */

const kirp = (v: number, a: number, b: number) => Math.max(a, Math.min(b, v));

/** 0->1 giris egrisi. */
const giris = (frame: number, fps: number, gecikme = 0, sn = 0.5) =>
  interpolate(frame, [gecikme, gecikme + Math.round(fps * sn)], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });

/** Tohumlu gurultu: ayni sahne her render'da AYNI sonucu verir. */
const gurultu = (tohum: string, i: number) => random(`${tohum}-${i}`) * 2 - 1;

export type EfektAdi =
  // kamera
  | 'sarsinti' | 'agresif-sarsinti' | 'elde-kamera' | 'dolly-zoom' | 'yumusak-zoom'
  | 'donme-3d' | 'suzulme'
  // goruntu
  | 'grain' | 'vinyet' | 'kromatik' | 'glow' | 'isik-sizmasi' | 'siyah-beyaz'
  | 'soguk-grade' | 'sicak-grade' | 'kontrast-grade' | 'yon-blur' | 'hareket-blur'
  | 'keskinlestir' | 'letterbox' | 'yuvarlak-kose' | 'kenarlik'
  // ozel
  | 'hologram' | 'glitch'
  // preset aileleri (416 presetten)
  | 'whip-pan' | 'slide' | 'pop-in' | 'stretch' | 'shine' | 'tv-bantlari' | 'bulge'
  | 'yukleme-cubugu';

export type Efekt = {ad: EfektAdi; siddet?: number; gecikme?: number};

/* ═══════════════════════ KAMERA EFEKTLERI ═══════════════════════ */

/**
 * Kamera sarsintisi. AE'de wiggle(freq, amp) ile yapilir; burada tohumlu gurultunun
 * kareler arasi yumusatilmis hali. siddet 1 = yumusak (belgesel), 3 = agresif.
 */
export const sarsintiTransform = (
  frame: number, fps: number, siddet = 1, tohum = 's',
): string => {
  const f = frame / Math.max(1, fps);
  const hz = 6 + siddet * 2;
  const a = 2.2 * siddet;                      // piksel
  const i = Math.floor(f * hz);
  const t = f * hz - i;
  const yumusak = t * t * (3 - 2 * t);         // smoothstep
  const x = gurultu(tohum + 'x', i) * (1 - yumusak) + gurultu(tohum + 'x', i + 1) * yumusak;
  const y = gurultu(tohum + 'y', i) * (1 - yumusak) + gurultu(tohum + 'y', i + 1) * yumusak;
  const r = (gurultu(tohum + 'r', i) * (1 - yumusak)
    + gurultu(tohum + 'r', i + 1) * yumusak) * 0.18 * siddet;
  return `translate(${(x * a).toFixed(2)}px, ${(y * a).toFixed(2)}px) rotate(${r.toFixed(3)}deg)`;
};

/** Elde kamera hissi: cok yavas, genis salinim (sarsinti degil, SURUKLENME). */
export const eldeKameraTransform = (frame: number, fps: number, siddet = 1): string => {
  const f = frame / Math.max(1, fps);
  const x = Math.sin(f * 0.6) * 5 * siddet + Math.sin(f * 1.7) * 1.8 * siddet;
  const y = Math.cos(f * 0.47) * 4 * siddet + Math.cos(f * 1.3) * 1.4 * siddet;
  const r = Math.sin(f * 0.33) * 0.12 * siddet;
  return `translate(${x.toFixed(2)}px, ${y.toFixed(2)}px) rotate(${r.toFixed(3)}deg)`;
};

/**
 * Dolly zoom (Vertigo): konu ayni boyutta kalirken arka plan yaklasir/uzaklasir.
 * Tek katmanda gercek dolly zoom yapilamaz (derinlik yok); burada ZITLIK taklidi:
 * olcek buyurken perspektif daralir — gozde ayni tedirginligi yaratir.
 */
export const dollyZoom = (frame: number, fps: number, sure: number, siddet = 1) => {
  const p = kirp(frame / Math.max(1, sure), 0, 1);
  const olcek = 1 + 0.16 * siddet * p;
  const persp = 1400 - 700 * p * siddet;
  return {transform: `perspective(${persp.toFixed(0)}px) scale(${olcek.toFixed(4)})`};
};

/** Yumusak zoom: ease-in-out, sabit hizli zoom'un "mekanik" hissini kirar. */
export const yumusakZoom = (frame: number, sure: number, bas = 1, son = 1.14) => {
  const p = interpolate(frame, [0, sure], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.inOut(Easing.cubic),
  });
  return bas + (son - bas) * p;
};

/** 3D dondurme: Y ekseninde perspektifli cevirme (kart cevirme hissi). */
export const donme3d = (frame: number, fps: number, sure: number, siddet = 1) => {
  const p = interpolate(frame, [0, Math.min(sure, Math.round(fps * 1.1))], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });
  const aci = (1 - p) * 42 * siddet;
  return {transform: `perspective(1200px) rotateY(${aci.toFixed(2)}deg)`, opacity: p};
};

/** Nesne suzulmesi: yukari-asagi cok yavas salinim (AE "float"). */
export const suzulme = (frame: number, fps: number, siddet = 1) => {
  const f = frame / Math.max(1, fps);
  return {transform: `translateY(${(Math.sin(f * 1.1) * 7 * siddet).toFixed(2)}px)`};
};

/* ═══════════════════════ GORUNTU EFEKTLERI ═══════════════════════ */

/** CSS filter zinciri: birden fazla renk/keskinlik efekti tek filter'da birlesir. */
export const filtreZinciri = (efektler: Efekt[]): string => {
  const par: string[] = [];
  for (const e of efektler) {
    const s = e.siddet ?? 1;
    switch (e.ad) {
      case 'siyah-beyaz':
        par.push(`grayscale(${kirp(s, 0, 1)}) contrast(${1 + 0.12 * s})`);
        break;
      case 'soguk-grade':
        par.push(`saturate(${1 - 0.12 * s}) hue-rotate(${-8 * s}deg) brightness(${1 - 0.04 * s})`);
        break;
      case 'sicak-grade':
        par.push(`saturate(${1 + 0.1 * s}) hue-rotate(${6 * s}deg) brightness(${1 + 0.03 * s})`);
        break;
      case 'kontrast-grade':
        par.push(`contrast(${1 + 0.18 * s}) saturate(${1 + 0.06 * s})`);
        break;
      case 'keskinlestir':
        // Gercek unsharp mask CSS'te yok; kontrast+parlaklik ile algisal keskinlik
        par.push(`contrast(${1 + 0.08 * s})`);
        break;
      case 'glow':
        par.push(`brightness(${1 + 0.05 * s}) saturate(${1 + 0.08 * s})`);
        break;
      default:
        break;
    }
  }
  return par.join(' ') || 'none';
};

/** Yonlu hiz blur'u (Premiere "directional blur"): CSS blur yonsuzdur, o yuzden
 *  ust uste iki hafif kaydirilmis kopya ile yon hissi verilir. */
export const YonluBlur: React.FC<{
  siddet?: number; aci?: number; children: React.ReactNode;
}> = ({siddet = 1, aci = 0, children}) => {
  const d = 3 * siddet;
  const rad = (aci * Math.PI) / 180;
  const dx = Math.cos(rad) * d;
  const dy = Math.sin(rad) * d;
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{opacity: 0.5, transform: `translate(${dx}px, ${dy}px)`,
        filter: `blur(${(0.8 * siddet).toFixed(2)}px)`}}>{children}</AbsoluteFill>
      <AbsoluteFill style={{opacity: 0.5, transform: `translate(${-dx}px, ${-dy}px)`,
        filter: `blur(${(0.8 * siddet).toFixed(2)}px)`}}>{children}</AbsoluteFill>
      <AbsoluteFill>{children}</AbsoluteFill>
    </AbsoluteFill>
  );
};

/** Kromatik sapma: kirmizi/mavi kanallari zit yonde kaydirir (lens hatasi taklidi). */
export const Kromatik: React.FC<{siddet?: number; children: React.ReactNode}> = ({
  siddet = 1, children,
}) => (
  <AbsoluteFill>
    {/* Kayma 1.2 -> 2.6 px: acik zeminli karelerde 1.2 px gozle gorulmuyordu.
        Taban katman ONCE cizilir, kanallar UZERINE screen ile biner. */}
    <AbsoluteFill>{children}</AbsoluteFill>
    <AbsoluteFill style={{transform: `translateX(${-2.6 * siddet}px)`,
      filter: 'url(#kanal-r)', opacity: 0.42, mixBlendMode: 'screen'}}>{children}</AbsoluteFill>
    <AbsoluteFill style={{transform: `translateX(${2.6 * siddet}px)`,
      filter: 'url(#kanal-b)', opacity: 0.42, mixBlendMode: 'screen'}}>{children}</AbsoluteFill>
  </AbsoluteFill>
);

/** Kanal ayirma SVG filtreleri — Kromatik bunlari kullanir, bir kez basilir. */
export const KanalFiltreleri: React.FC = () => (
  <svg width={0} height={0} style={{position: 'absolute'}}>
    <defs>
      <filter id="kanal-r">
        <feColorMatrix type="matrix" values="1 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1 0" />
      </filter>
      <filter id="kanal-b">
        <feColorMatrix type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 1 0 0  0 0 0 1 0" />
      </filter>
    </defs>
  </svg>
);

/** Film grain: tohumlu, kare basina degisen ince gurultu dokusu. */
export const Grain: React.FC<{siddet?: number; tohum?: string}> = ({siddet = 1, tohum = 'g'}) => {
  const frame = useCurrentFrame();
  // Her karede desenin yerini kaydirmak "hareketli grain" hissi verir (statik grain
  // "kirli ekran" gibi durur). Desen SVG turbulence ile uretilir, dosya gerekmez.
  const kay = Math.floor(random(`${tohum}-${frame}`) * 100);
  return (
    <AbsoluteFill style={{opacity: 0.05 + 0.07 * siddet, mixBlendMode: 'overlay',
      pointerEvents: 'none'}}>
      <svg width="100%" height="100%">
        <filter id={`grain-${kay}`}>
          <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves={2}
                        seed={kay} stitchTiles="stitch" />
          <feColorMatrix type="saturate" values="0" />
        </filter>
        <rect width="100%" height="100%" filter={`url(#grain-${kay})`} />
      </svg>
    </AbsoluteFill>
  );
};

/** Vinyet: kenarlarda karanlik dusus. */
export const Vinyet: React.FC<{siddet?: number}> = ({siddet = 1}) => (
  <AbsoluteFill style={{
    background: `radial-gradient(ellipse at center, rgba(0,0,0,0) ${58 - 8 * siddet}%, `
      + `rgba(0,0,0,${kirp(0.42 * siddet, 0, 0.85)}) 100%)`,
    pointerEvents: 'none',
  }} />
);

/** Isik sizmasi: kenardan giren sicak parlama, yavas kayar. */
export const IsikSizmasi: React.FC<{siddet?: number; tohum?: string}> = ({
  siddet = 1, tohum = 'l',
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const f = frame / Math.max(1, fps);
  const yer = 12 + Math.sin(f * 0.35 + random(tohum) * 6) * 10;
  return (
    <AbsoluteFill style={{
      background: `radial-gradient(circle at ${yer}% ${28 + Math.cos(f * 0.3) * 8}%, `
        + `rgba(255,196,120,${0.16 * siddet}) 0%, rgba(255,170,90,${0.07 * siddet}) 26%, `
        + 'rgba(0,0,0,0) 55%)',
      mixBlendMode: 'screen', pointerEvents: 'none',
    }} />
  );
};

/** Letterbox: sinematik siyah bantlar (2.39:1 hissi). */
export const Letterbox: React.FC<{oran?: number}> = ({oran = 2.39}) => {
  const {width, height} = useVideoConfig();
  const hedef = width / oran;
  const bant = Math.max(0, (height - hedef) / 2);
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      <div style={{position: 'absolute', top: 0, left: 0, right: 0, height: bant,
        backgroundColor: '#000'}} />
      <div style={{position: 'absolute', bottom: 0, left: 0, right: 0, height: bant,
        backgroundColor: '#000'}} />
    </AbsoluteFill>
  );
};

/** Glitch: RGB ayrisma + yatay blok kaymasi, kisa ve seyrek patlamalar halinde. */
export const Glitch: React.FC<{siddet?: number; tohum?: string; children: React.ReactNode}> = ({
  siddet = 1, tohum = 'gl', children,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  // Patlama: her ~0.8 sn'de bir, 3-4 kare suren bozulma. Surekli glitch yorucu olur.
  const blok = Math.floor(frame / Math.max(1, Math.round(fps * 0.8)));
  const aktif = random(`${tohum}-${blok}`) > 0.55;
  const yerelKare = frame % Math.max(1, Math.round(fps * 0.8));
  const patla = aktif && yerelKare < 4;
  if (!patla) return <AbsoluteFill>{children}</AbsoluteFill>;
  const k = (1 + yerelKare) * siddet;
  const dx = gurultu(`${tohum}-${blok}-x`, yerelKare) * 9 * siddet;
  const dilim = 18 + Math.floor(random(`${tohum}-${blok}-s`) * 26);
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{transform: `translateX(${dx.toFixed(1)}px)`,
        clipPath: `polygon(0 ${dilim}%, 100% ${dilim}%, 100% ${dilim + 12}%, 0 ${dilim + 12}%)`,
        filter: 'url(#kanal-r)', mixBlendMode: 'screen', opacity: 0.9}}>{children}</AbsoluteFill>
      <AbsoluteFill style={{transform: `translateX(${(-dx * 0.7).toFixed(1)}px)`,
        clipPath: `polygon(0 ${dilim + 20}%, 100% ${dilim + 20}%, 100% ${dilim + 30}%, 0 ${dilim + 30}%)`,
        filter: 'url(#kanal-b)', mixBlendMode: 'screen', opacity: 0.9}}>{children}</AbsoluteFill>
      <AbsoluteFill style={{transform: `translateX(${(k * 0.6).toFixed(1)}px)`}}>
        {children}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

/** Hayalet / hologram: yariseffaf, hafif mavi, tarama cizgileri + titreme. */
export const Hologram: React.FC<{siddet?: number; children: React.ReactNode}> = ({
  siddet = 1, children,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const titre = 0.82 + Math.sin(frame * 0.9) * 0.06 + random(`h${Math.floor(frame / 3)}`) * 0.05;
  return (
    <AbsoluteFill>
      {/* Render testinde (7 Agu) hologram fazla soluk cikti: opaklik 0.55-0.80 arasi
          kaliyor ve goruntu kayboluyordu. Taban 0.82'ye cikarildi, doygunluk 0.4 -> 0.62
          (tamamen renksiz kalinca "bozuk video" gibi duruyordu), blur yarilandi. */}
      <AbsoluteFill style={{
        opacity: titre * (0.82 + 0.08 * (1 - siddet / 3)),
        filter: `saturate(0.62) hue-rotate(-150deg) brightness(1.16) blur(${0.2 * siddet}px)`,
      }}>{children}</AbsoluteFill>
      {/* Mavi tonlama ayri katmanda: filtre ile yapinca goruntuyu oldururyor */}
      <AbsoluteFill style={{
        backgroundColor: 'rgba(90,190,255,0.16)', mixBlendMode: 'overlay',
        pointerEvents: 'none',
      }} />
      {/* tarama cizgileri: yukari kayan yatay desen */}
      <AbsoluteFill style={{
        background: 'repeating-linear-gradient(0deg, rgba(120,220,255,0.10) 0px, '
          + 'rgba(120,220,255,0.10) 1px, rgba(0,0,0,0) 3px, rgba(0,0,0,0) 5px)',
        transform: `translateY(${(-(frame % (fps * 2)) / (fps * 2)) * 5}px)`,
        mixBlendMode: 'screen', pointerEvents: 'none',
      }} />
    </AbsoluteFill>
  );
};

/* ═══════════════════════ YAZI ANIMASYONLARI ═══════════════════════ */

export type YaziAnim =
  | 'daktilo' | 'ziplama' | 'titreme' | 'yayilma' | 'kayan' | 'rastgele' | 'yumusak';

const YAZI_TABAN: React.CSSProperties = {
  fontFamily: fontAilesi('montserrat'),
  fontWeight: 800,
  color: '#FFFFFF',
  textShadow: '0 3px 16px rgba(0,0,0,0.8), 0 1px 3px rgba(0,0,0,0.9)',
};

/**
 * Yazi animasyonlari — kanalda ayri ayri anlatilan 7 teknik tek bilesende.
 * daktilo  : harfler tek tek yazilir (typewriter)
 * ziplama  : her kelime yay ile ziplayarak girer (text bounce)
 * titreme  : opaklik rastgele titrer (text flicker)
 * yayilma  : harf araligi genisten normale oturur (text spread)
 * kayan    : alttan yukari kayarak girer (scrolling)
 * rastgele : harfler rastgele siralarda belirir (randomized)
 * yumusak  : blursuz, yay ile yumusak fade+kayma (smooth text)
 */
export const YaziAnimasyonu: React.FC<{
  metin: string;
  anim?: YaziAnim;
  boyut?: number;
  kareSayisi: number;
  gecikme?: number;
  stil?: React.CSSProperties;
}> = ({metin, anim = 'yumusak', boyut = 64, kareSayisi, gecikme = 0, stil}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const g = Math.round(fps * gecikme);
  const cik = interpolate(frame, [kareSayisi - Math.round(fps * 0.5), kareSayisi], [1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const temel: React.CSSProperties = {...YAZI_TABAN, fontSize: boyut, ...stil};

  if (anim === 'daktilo') {
    const harf = Math.floor(interpolate(frame, [g, g + Math.round(fps * 1.4)],
      [0, metin.length], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}));
    const imlec = Math.floor(frame / Math.max(1, Math.round(fps * 0.25))) % 2 === 0;
    return (
      <div style={{...temel, opacity: cik}}>
        {metin.slice(0, harf)}
        <span style={{opacity: harf < metin.length && imlec ? 1 : 0}}>|</span>
      </div>
    );
  }
  if (anim === 'yayilma') {
    const p = giris(frame, fps, g, 0.75);
    return (
      <div style={{...temel, opacity: p * cik,
        letterSpacing: `${((1 - p) * 16).toFixed(2)}px`}}>{metin}</div>
    );
  }
  if (anim === 'kayan') {
    const p = giris(frame, fps, g, 0.6);
    return (
      <div style={{...temel, opacity: cik, overflow: 'hidden'}}>
        <span style={{display: 'inline-block',
          transform: `translateY(${((1 - p) * 100).toFixed(1)}%)`}}>{metin}</span>
      </div>
    );
  }
  if (anim === 'titreme') {
    const p = giris(frame, fps, g, 0.3);
    const t = frame > g ? 0.55 + random(`f${Math.floor(frame / 2)}`) * 0.45 : 0;
    return <div style={{...temel, opacity: p * t * cik}}>{metin}</div>;
  }

  // kelime/harf bazli olanlar
  const parcalar = anim === 'rastgele' ? metin.split('') : metin.split(/(\s+)/);
  return (
    <div style={{...temel, opacity: cik, display: 'flex', flexWrap: 'wrap',
      justifyContent: (stil?.textAlign as never) === 'center' ? 'center' : 'flex-start'}}>
      {parcalar.map((par, i) => {
        if (/^\s+$/.test(par)) return <span key={i}>&nbsp;</span>;
        const sira = anim === 'rastgele'
          ? Math.floor(random(`r${i}`) * parcalar.length)
          : i;
        const gg = g + sira * Math.round(fps * (anim === 'rastgele' ? 0.035 : 0.06));
        const p = giris(frame, fps, gg, anim === 'ziplama' ? 0.42 : 0.4);
        const zipla = anim === 'ziplama'
          ? interpolate(p, [0, 0.6, 0.82, 1], [26, -6, 3, 0])
          : (1 - p) * 12;
        return (
          <span key={i} style={{display: 'inline-block', opacity: p,
            transform: `translateY(${zipla.toFixed(2)}px)`}}>{par}</span>
        );
      })}
    </div>
  );
};

/** Yazi icinde video: metin maskesi (AE "video inside text"). */
export const YaziIcindeVideo: React.FC<{
  metin: string; boyut?: number; children: React.ReactNode;
}> = ({metin, boyut = 190, children}) => (
  <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
    <div style={{
      fontFamily: fontAilesi('anton'), fontSize: boyut, lineHeight: 1, textAlign: 'center',
      backgroundClip: 'text', WebkitBackgroundClip: 'text', color: 'transparent',
      position: 'relative',
    }}>
      <AbsoluteFill style={{
        WebkitMaskImage: 'none', mixBlendMode: 'normal',
      }}>{children}</AbsoluteFill>
      {metin}
    </div>
  </AbsoluteFill>
);

/* ═══════════════════════ GRAFIK ANIMASYONLARI ═══════════════════════ */

/** Cizgi cizilmesi (AE "animate lines" / map line animation). */
export const CizilenCizgi: React.FC<{
  noktalar: {x: number; y: number}[];
  kalinlik?: number;
  renk?: string;
  gecikme?: number;
  kesikli?: boolean;
}> = ({noktalar, kalinlik = 5, renk = '#FFFFFF', gecikme = 0.3, kesikli}) => {
  const frame = useCurrentFrame();
  const {fps, width: W, height: H} = useVideoConfig();
  if (!noktalar || noktalar.length < 2) return null;
  const d = noktalar.map((n, i) => `${i ? 'L' : 'M'}${n.x * W} ${n.y * H}`).join(' ');
  // Yol uzunlugu tahmini: kose kose oklid mesafesi toplami
  let uz = 0;
  for (let i = 1; i < noktalar.length; i++) {
    uz += Math.hypot((noktalar[i].x - noktalar[i - 1].x) * W,
      (noktalar[i].y - noktalar[i - 1].y) * H);
  }
  const p = giris(frame, fps, Math.round(fps * gecikme), 1.1);
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      <svg width={W} height={H}>
        <path d={d} fill="none" stroke={renk} strokeWidth={kalinlik} strokeLinecap="round"
              strokeDasharray={kesikli ? `${kalinlik * 3} ${kalinlik * 2.2}` : uz}
              strokeDashoffset={kesikli ? -p * uz : (1 - p) * uz} />
      </svg>
    </AbsoluteFill>
  );
};

/** Daire animasyonu: cizilerek acilan halka (AE "animate a circle"). */
export const CizilenDaire: React.FC<{
  x: number; y: number; r: number; kalinlik?: number; renk?: string; gecikme?: number;
}> = ({x, y, r, kalinlik = 4, renk = '#FFFFFF', gecikme = 0.3}) => {
  const frame = useCurrentFrame();
  const {fps, width: W, height: H} = useVideoConfig();
  const p = giris(frame, fps, Math.round(fps * gecikme), 0.8);
  const rp = r * Math.min(W, H);
  const cev = 2 * Math.PI * rp;
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      <svg width={W} height={H}>
        <circle cx={x * W} cy={y * H} r={rp} fill="none" stroke={renk}
                strokeWidth={kalinlik} strokeDasharray={cev}
                strokeDashoffset={(1 - p) * cev}
                transform={`rotate(-90 ${x * W} ${y * H})`} />
      </svg>
    </AbsoluteFill>
  );
};

/** Ikon parlamasi: uzerinden gecen egik isik seridi (Premiere "icon shine"). */
export const IkonParlamasi: React.FC<{periyot?: number}> = ({periyot = 3}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const d = Math.max(1, Math.round(fps * periyot));
  const p = (frame % d) / d;
  return (
    <AbsoluteFill style={{
      background: 'linear-gradient(105deg, rgba(255,255,255,0) 38%, '
        + 'rgba(255,255,255,0.34) 50%, rgba(255,255,255,0) 62%)',
      transform: `translateX(${(-120 + p * 240).toFixed(1)}%)`,
      mixBlendMode: 'screen', pointerEvents: 'none',
    }} />
  );
};

/* ═══════════════════════ PRESET AILELERI (416 presetten eksik kalanlar) ═══════════════════════ */

/** Whip pan: hizli yatay/dikey supurme + yon blur'u. 4 yon. */
export const whipPan = (
  frame: number, fps: number, yon: 'sol' | 'sag' | 'ust' | 'alt' = 'sol', siddet = 1,
) => {
  const u = Math.round(fps * 0.28);
  const p = interpolate(frame, [0, u], [1, 0], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.quad),
  });
  const d = 260 * siddet * p;
  const tr = yon === 'sol' ? `translateX(${d}px)`
    : yon === 'sag' ? `translateX(${-d}px)`
    : yon === 'ust' ? `translateY(${d}px)` : `translateY(${-d}px)`;
  const bulanik = (p * 9 * siddet).toFixed(2);
  return {transform: tr, filter: p > 0.02 ? `blur(${bulanik}px)` : 'none'};
};

/** Slide in/out: 8 yon (4 duz + 4 diyagonal), yumusak easing. */
export const slide = (
  frame: number, fps: number,
  yon: 'sol' | 'sag' | 'ust' | 'alt' | 'sol-ust' | 'sag-ust' | 'sol-alt' | 'sag-alt' = 'sol',
  cikis = false, siddet = 1,
) => {
  const u = Math.round(fps * 0.5);
  const p = cikis
    ? interpolate(frame, [0, u], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
      easing: Easing.in(Easing.cubic)})
    : interpolate(frame, [0, u], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
      easing: Easing.out(Easing.cubic)});
  const d = 100 * siddet * p;
  const [sx, sy] = {
    sol: [d, 0], sag: [-d, 0], ust: [0, d], alt: [0, -d],
    'sol-ust': [d, d], 'sag-ust': [-d, d], 'sol-alt': [d, -d], 'sag-alt': [-d, -d],
  }[yon] as [number, number];
  return {transform: `translate(${sx.toFixed(1)}%, ${sy.toFixed(1)}%)`};
};

/** Pop in: yay ile buyuyerek girer. 6 kademe (kucuk/orta/buyuk x normal/zipli). */
export const popIn = (
  frame: number, fps: number, kademe: 1 | 2 | 3 = 2, zipli = false,
) => {
  const bas = [0.86, 0.78, 0.66][kademe - 1];
  const y = spring({frame, fps, config: zipli
    ? {damping: 9, stiffness: 170, mass: 0.7}      // zipli: geri sekme var
    : {damping: 20, stiffness: 130, mass: 0.8}});   // normal: oturur
  return {transform: `scale(${(bas + (1 - bas) * y).toFixed(4)})`, opacity: Math.min(1, y * 1.6)};
};

/** Stretch: yatay ya da dikey gerilme (bounce'lu ya da duz). */
export const stretch = (
  frame: number, fps: number, eksen: 'yatay' | 'dikey' = 'yatay', siddet = 1, zipli = false,
) => {
  const y = spring({frame, fps, config: zipli
    ? {damping: 8, stiffness: 190, mass: 0.6} : {damping: 22, stiffness: 140, mass: 0.8}});
  const g = 1 + 0.3 * siddet * (1 - y);
  return {transform: eksen === 'yatay'
    ? `scaleX(${g.toFixed(4)}) scaleY(${(1 / Math.sqrt(g)).toFixed(4)})`
    : `scaleY(${g.toFixed(4)}) scaleX(${(1 / Math.sqrt(g)).toFixed(4)})`};
};

/** Yuvarlak kose: 8 kademe (kucuk 1-5x, orta 1-3x). */
export const YuvarlakKose: React.FC<{
  kademe?: number; children: React.ReactNode;
}> = ({kademe = 3, children}) => (
  <AbsoluteFill style={{borderRadius: Math.max(0, kademe) * 9, overflow: 'hidden'}}>
    {children}
  </AbsoluteFill>
);

/** Kenarlik: kare cevresine cerceve (Premiere "Borders"). */
export const Kenarlik: React.FC<{kalinlik?: number; renk?: string}> = ({
  kalinlik = 10, renk = '#FFFFFF',
}) => (
  <AbsoluteFill style={{
    border: `${kalinlik}px solid ${renk}`, boxSizing: 'border-box', pointerEvents: 'none',
  }} />
);

/** Shine: 4 yonde egik isik seridi (Premiere "Shine Effect"). */
export const Shine: React.FC<{
  yon?: 'sol-ust' | 'sag-ust' | 'sol-alt' | 'sag-alt'; periyot?: number;
}> = ({yon = 'sol-ust', periyot = 2.6}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const d = Math.max(1, Math.round(fps * periyot));
  const p = (frame % d) / d;
  const aci = {'sol-ust': 105, 'sag-ust': 75, 'sol-alt': -105, 'sag-alt': -75}[yon];
  const yon_isareti = yon.startsWith('sag') ? -1 : 1;
  return (
    <AbsoluteFill style={{
      background: `linear-gradient(${aci}deg, rgba(255,255,255,0) 40%, `
        + 'rgba(255,255,255,0.30) 50%, rgba(255,255,255,0) 60%)',
      transform: `translateX(${(yon_isareti * (-130 + p * 260)).toFixed(1)}%)`,
      mixBlendMode: 'screen', pointerEvents: 'none',
    }} />
  );
};

/** Loading bar: soldan saga (ya da tersi) dolan cubuk. */
export const YuklemeCubugu: React.FC<{
  y?: number; ters?: boolean; renk?: string; sure?: number;
}> = ({y = 0.86, ters, renk = '#F5E14B', sure = 2.2}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const p = interpolate(frame, [Math.round(fps * 0.3), Math.round(fps * (0.3 + sure))], [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.inOut(Easing.cubic)});
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      <div style={{position: 'absolute', left: '10%', right: '10%', top: `${y * 100}%`,
        height: 12, backgroundColor: 'rgba(0,0,0,0.45)', borderRadius: 6, overflow: 'hidden'}}>
        <div style={{height: '100%', width: `${(p * 100).toFixed(1)}%`,
          backgroundColor: renk, borderRadius: 6,
          transformOrigin: ters ? 'right center' : 'left center',
          marginLeft: ters ? 'auto' : 0}} />
      </div>
    </AbsoluteFill>
  );
};

/** TV displacement lines: yatay kayan bozulma bantlari (3 siddet). */
export const TVBantlari: React.FC<{siddet?: number}> = ({siddet = 1}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const y = ((frame / Math.max(1, fps)) * 0.35) % 1;
  return (
    <AbsoluteFill style={{pointerEvents: 'none', opacity: 0.10 + 0.12 * siddet}}>
      <div style={{position: 'absolute', left: 0, right: 0, top: `${y * 100}%`,
        height: `${3 + 5 * siddet}%`,
        background: 'linear-gradient(0deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.5) 50%, '
          + 'rgba(255,255,255,0) 100%)', mixBlendMode: 'overlay'}} />
      <AbsoluteFill style={{
        background: 'repeating-linear-gradient(0deg, rgba(0,0,0,0.16) 0px, '
          + 'rgba(0,0,0,0.16) 1px, rgba(0,0,0,0) 3px)',
      }} />
    </AbsoluteFill>
  );
};

/** Bulge: merkeze dogru sisme/cokme (Premiere "Bulge Screen"). */
export const bulge = (frame: number, fps: number, disa = true, siddet = 1) => {
  const y = spring({frame, fps, config: {damping: 18, stiffness: 110, mass: 0.9}});
  const k = (disa ? 1 : -1) * 0.10 * siddet * (1 - y);
  return {transform: `perspective(900px) scale(${(1 + k).toFixed(4)})`};
};

/* ═══════════════════════ GECIS EFEKTLERI ═══════════════════════ */

/** Flash gecis: kisa beyaz patlama (AE "flash transition"). */
export const FlashGecis: React.FC<{kareSayisi: number; siddet?: number}> = ({
  kareSayisi, siddet = 1,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const u = Math.round(fps * 0.16);
  const o = interpolate(frame, [0, u * 0.4, u], [0, 0.85 * siddet, 0], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  if (frame > u) return null;
  return <AbsoluteFill style={{backgroundColor: '#FFFFFF', opacity: o,
    pointerEvents: 'none'}} />;
};

/** Karartma gecisi: siyaha in-cik (dip to black). */
export const KarartmaGecis: React.FC<{kareSayisi: number}> = ({kareSayisi}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const u = Math.round(fps * 0.32);
  const o = frame < u
    ? interpolate(frame, [0, u], [1, 0], {extrapolateRight: 'clamp'})
    : interpolate(frame, [kareSayisi - u, kareSayisi], [0, 1], {extrapolateLeft: 'clamp'});
  return <AbsoluteFill style={{backgroundColor: '#000', opacity: kirp(o, 0, 1),
    pointerEvents: 'none'}} />;
};

/* ═══════════════════════ DIS KAPI ═══════════════════════ */

/**
 * Sahneye uygulanacak efekt yiginini tek yerden hesaplar.
 * transform ve filter DONER (gorsele uygulanmak uzere), katmanlar ise ayri cizilir.
 */
export const efektHesapla = (
  efektler: Efekt[] | undefined,
  frame: number,
  fps: number,
  kareSayisi: number,
  tohum: string,
): {transform: string; filter: string; katmanlar: EfektAdi[]} => {
  if (!efektler || !efektler.length) return {transform: '', filter: 'none', katmanlar: []};
  const tr: string[] = [];
  const katmanlar: EfektAdi[] = [];
  for (const e of efektler) {
    const s = e.siddet ?? 1;
    switch (e.ad) {
      case 'sarsinti':
        tr.push(sarsintiTransform(frame, fps, s, tohum));
        break;
      case 'agresif-sarsinti':
        tr.push(sarsintiTransform(frame, fps, Math.max(2.5, s * 2.5), tohum));
        break;
      case 'elde-kamera':
        tr.push(eldeKameraTransform(frame, fps, s));
        break;
      case 'dolly-zoom':
        tr.push(dollyZoom(frame, fps, kareSayisi, s).transform);
        break;
      case 'donme-3d':
        tr.push(donme3d(frame, fps, kareSayisi, s).transform);
        break;
      case 'suzulme':
        tr.push(suzulme(frame, fps, s).transform);
        break;
      default:
        katmanlar.push(e.ad);
        break;
    }
  }
  return {transform: tr.join(' '), filter: filtreZinciri(efektler), katmanlar};
};

/** Katman efektlerini (grain/vinyet/glitch/hologram...) tek yerden cizer. */
export const EfektKatmanlari: React.FC<{
  efektler?: Efekt[];
  kareSayisi: number;
  tohum: string;
}> = ({efektler, kareSayisi, tohum}) => {
  if (!efektler || !efektler.length) return null;
  const bul = (ad: EfektAdi) => efektler.find((e) => e.ad === ad);
  const g = bul('grain');
  const v = bul('vinyet');
  const l = bul('isik-sizmasi');
  const lb = bul('letterbox');
  return (
    <>
      {g ? <Grain siddet={g.siddet ?? 1} tohum={tohum} /> : null}
      {l ? <IsikSizmasi siddet={l.siddet ?? 1} tohum={tohum} /> : null}
      {v ? <Vinyet siddet={v.siddet ?? 1} /> : null}
      {lb ? <Letterbox oran={lb.siddet && lb.siddet > 1 ? 2.39 : 2.0} /> : null}
    </>
  );
};
