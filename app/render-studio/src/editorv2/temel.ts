/**
 * TEMEL YARDIMCILAR — easing, zamanlama, guvenli alan, renk.
 *
 * AE hissi buradan baslar: `Easing.bezier` ile Graph Editor egrileri, spring ile
 * overshoot+settle, ve HER animasyonun tanimli giris/bekleme/cikis davranisi.
 */
import {Easing, interpolate, spring} from 'remotion';

import type {MotionSpec} from './sozlesme';

/** Faz C profil.EASING karsiliklari (olculen degerler). */
export const EASING_BEZIER: Record<string, [number, number, number, number]> = {
  kamera: [0.42, 0.32, 0.58, 0.68], // olculdu: lineere yakin (son/ilk = 1.03)
  giris: [0.16, 1.0, 0.3, 1.0],
  cikis: [0.7, 0.0, 0.84, 0.0],
  overshoot: [0.34, 1.56, 0.64, 1.0],
  lineer: [0.0, 0.0, 1.0, 1.0],
};

/** Spec'ten easing fonksiyonu. Bozuk bezier gelirse lineere DUSER (sessizce degil,
 * validator zaten WARN uretti). */
export const easingAl = (spec?: MotionSpec | null) => {
  const b = spec?.easing_bezier;
  if (Array.isArray(b) && b.length === 4 && b.every((x) => typeof x === 'number')) {
    return Easing.bezier(b[0], b[1], b[2], b[3]);
  }
  const ad = spec?.easing || 'lineer';
  const y = EASING_BEZIER[ad] || EASING_BEZIER.lineer;
  return Easing.bezier(y[0], y[1], y[2], y[3]);
};

/** 0..1 ilerleme (kare -> oran), easing uygulanmis. */
export const ilerleme = (
  frame: number,
  basKare: number,
  sureKare: number,
  spec?: MotionSpec | null,
): number => {
  if (sureKare <= 0) return 1;
  return interpolate(frame, [basKare, basKare + sureKare], [0, 1], {
    easing: easingAl(spec),
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
};

/**
 * GIRIS / BEKLEME / CIKIS zarfi (0..1 opaklik).
 * Referans olcumu: giris animasyonlari 0.5 sn'nin ALTINDA (yazili karelerin
 * yalnizca %1.8'i yariyolda yakalandi). Varsayilan 0.28 sn.
 */
export const zarf = (
  frame: number,
  fps: number,
  basSn: number,
  sureSn: number,
  girisSn = 0.28,
  cikisSn = 0.28,
): number => {
  const b = basSn * fps;
  const s = sureSn * fps;
  const g = Math.max(1, girisSn * fps);
  const c = Math.max(1, cikisSn * fps);
  if (frame < b) return 0;
  if (frame > b + s) return 0;
  const gir = interpolate(frame, [b, b + g], [0, 1], {
    easing: Easing.bezier(...EASING_BEZIER.giris),
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const cik = interpolate(frame, [b + s - c, b + s], [1, 0], {
    easing: Easing.bezier(...EASING_BEZIER.cikis),
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  return Math.max(0, Math.min(gir, cik));
};

/** Overshoot + settle (AE'deki klasik "pop"). */
export const popIn = (frame: number, fps: number, basSn: number): number =>
  spring({
    frame: Math.max(0, frame - basSn * fps),
    fps,
    config: {damping: 14, mass: 0.6, stiffness: 130},
  });

/** Deterministik pseudo-rastgele (Math.random YASAK: her kare ayni olmali). */
export const tohum = (a: number, b = 0): number => {
  const x = Math.sin(a * 127.1 + b * 311.7) * 43758.5453;
  return x - Math.floor(x);
};

/* ── Guvenli alan (yayin standardi ~%5.9) ── */
export const GUVENLI_KENAR = 64;
export const IZGARA_X = 100;

export const guvenliAlanIcinde = (
  x: number,
  y: number,
  w: number,
  h: number,
  genislik: number,
  yukseklik: number,
): boolean =>
  x >= GUVENLI_KENAR &&
  y >= GUVENLI_KENAR &&
  x + w <= genislik - GUVENLI_KENAR &&
  y + h <= yukseklik - GUVENLI_KENAR;

/* ── Tasarim token'lari (Faz C profil.Renk varsayilanlari) ── */
export const RENK = {
  taban: '#0E1013',
  yazi: '#F5F3EF',
  vurgu: '#F5E14B',
  bant: '#000000',
  haritaKara: '#1C2026',
  haritaSu: '#0A0D10',
  veriCubuk: '#F5E14B',
  uyari: '#E2564D',
};

export const FONT = {
  aile: 'Montserrat, "Helvetica Neue", Arial, sans-serif',
  kalin: 700,
  orta: 600,
  normal: 400,
};

/** Spec listesinden ada gore ilkini bul. */
export const specBul = (specler: MotionSpec[], ad: string): MotionSpec | null =>
  specler.find((s) => s.ad === ad) || null;

/** Spec listesinden ada gore hepsini bul. */
export const specleriBul = (specler: MotionSpec[], adlar: string[]): MotionSpec[] =>
  specler.filter((s) => adlar.includes(s.ad));

export const sayi = (v: unknown, varsayilan = 0): number =>
  typeof v === 'number' && Number.isFinite(v) ? v : varsayilan;

export const metin = (v: unknown, varsayilan = ''): string =>
  typeof v === 'string' ? v : varsayilan;

export const dizi = (v: unknown): number[] =>
  Array.isArray(v) ? v.filter((x) => typeof x === 'number') : [];
