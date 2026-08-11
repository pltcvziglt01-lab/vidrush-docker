/**
 * DOKU / ISIK / REVEAL KATMANLARI.
 *
 * Hepsi RESTRAINED: referans olcumunde kareler %84 grafiksiz, efektler seyrek.
 * Amac "efekt gosterisi" degil, goruntuye film dokusu ve yonlendirme vermek.
 *
 * ⚠ GRAIN: her karede yeni SVG filtresi URETMEK YASAK — 11 Agu'da bir videoyu
 * oldurdu (her kare yeni feTurbulence + yeni filtre id -> render 30 dk zaman
 * asimina girdi). Burada onceden uretilmis doku KAYDIRILIYOR.
 */
import React from 'react';
import {AbsoluteFill, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';

import type {MotionSpec} from './sozlesme';
import {RENK, ilerleme, sayi, tohum} from './temel';

/** Film grain — onceden uretilmis doku, kare basina KAYDIRMA. */
export const Grain: React.FC<{spec: MotionSpec}> = ({spec}) => {
  const frame = useCurrentFrame();
  const siddet = sayi(spec.parametre.siddet, 0.35);
  // 2 karede bir kaydir: her karede degistirmek gurultuyu titretiyor
  const adim = Math.floor(frame / 2);
  const kx = Math.floor(tohum(adim, 3) * 512);
  const ky = Math.floor(tohum(adim, 4) * 512);
  return (
    <AbsoluteFill
      style={{
        opacity: 0.04 + 0.09 * siddet,
        mixBlendMode: 'overlay',
        backgroundImage: `url(${staticFile('doku/grain.png')})`,
        backgroundRepeat: 'repeat',
        backgroundSize: '512px 512px',
        backgroundPosition: `${kx}px ${ky}px`,
        pointerEvents: 'none',
      }}
    />
  );
};

export const Vignette: React.FC<{spec: MotionSpec}> = ({spec}) => {
  const siddet = sayi(spec.parametre.siddet, 0.45);
  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(ellipse at center, transparent ${Math.round(
          58 - 10 * siddet,
        )}%, rgba(0,0,0,${(0.55 * siddet).toFixed(3)}) 100%)`,
        pointerEvents: 'none',
      }}
    />
  );
};

/** Renk grade — profil adina gore CSS filtresi. */
export const Grade: React.FC<{spec: MotionSpec}> = ({spec}) => {
  const profil = String(spec.parametre.profil || 'notr-soguk');
  const harita: Record<string, string> = {
    'notr-soguk': 'saturate(0.94) contrast(1.06) brightness(0.99)',
    'soguk-kontrast': 'saturate(0.86) contrast(1.16) brightness(0.96)',
    sicak: 'saturate(1.06) contrast(1.04) sepia(0.06)',
  };
  const tint: Record<string, string> = {
    'notr-soguk': 'rgba(90,120,150,0.06)',
    'soguk-kontrast': 'rgba(70,105,140,0.10)',
    sicak: 'rgba(160,120,70,0.07)',
  };
  return (
    <AbsoluteFill
      style={{
        backdropFilter: harita[profil] || harita['notr-soguk'],
        WebkitBackdropFilter: harita[profil] || harita['notr-soguk'],
        background: tint[profil] || tint['notr-soguk'],
        pointerEvents: 'none',
      }}
    />
  );
};

export const Letterbox: React.FC<{spec: MotionSpec}> = ({spec}) => {
  const {width, height} = useVideoConfig();
  const oran = sayi(spec.parametre.oran, 2.39);
  const hedefY = width / oran;
  const bant = Math.max(0, (height - hedefY) / 2);
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      <div style={{position: 'absolute', top: 0, left: 0, right: 0, height: bant, background: '#000'}} />
      <div style={{position: 'absolute', bottom: 0, left: 0, right: 0, height: bant, background: '#000'}} />
    </AbsoluteFill>
  );
};

/**
 * LIGHT SWEEP — yonlu isik gecisi. AE'deki "shine" karsiligi.
 * Restrained: siddet tavani 0.5, tek gecis.
 */
export const LightSweep: React.FC<{spec: MotionSpec; sureKare: number; fps: number}> = ({
  spec,
  sureKare,
  fps,
}) => {
  const frame = useCurrentFrame();
  const basKare = sayi(spec.bas_sn, 0) * fps;
  const kendiSure = Math.max(1, sayi(spec.sure_sn, 0.8) * fps);
  if (frame < basKare || frame > basKare + kendiSure) return null;
  const t = ilerleme(frame, basKare, kendiSure, spec);
  const aci = sayi(spec.parametre.aci, 24);
  const siddet = Math.min(0.5, sayi(spec.parametre.siddet, 0.35));
  const genislikOrani = sayi(spec.parametre.genislik_orani, 0.22);
  // -20% -> 120% arasi kayma
  const konum = interpolate(t, [0, 1], [-20, 120]);
  return (
    <AbsoluteFill style={{pointerEvents: 'none', overflow: 'hidden'}}>
      <div
        style={{
          position: 'absolute',
          top: '-30%',
          bottom: '-30%',
          left: `${konum}%`,
          width: `${genislikOrani * 100}%`,
          transform: `rotate(${aci}deg)`,
          background: `linear-gradient(90deg, transparent, rgba(255,255,255,${siddet}), transparent)`,
          filter: 'blur(14px)',
          mixBlendMode: 'screen',
        }}
      />
    </AbsoluteFill>
  );
};

/** MASKED REVEAL — goruntu maskeyle acilir (AE mask reveal). */
export const MaskedReveal: React.FC<{
  spec: MotionSpec;
  fps: number;
  children: React.ReactNode;
}> = ({spec, fps, children}) => {
  const frame = useCurrentFrame();
  const basKare = sayi(spec.bas_sn, 0) * fps;
  const sure = Math.max(1, sayi(spec.sure_sn, 0.6) * fps);
  const t = ilerleme(frame, basKare, sure, spec);
  const yon = String(spec.parametre.yon || 'left');
  const yumusak = sayi(spec.parametre.kenar_yumusakligi_px, 24);
  const yuzde = Math.round(t * 100);
  const yonHarita: Record<string, string> = {
    left: `linear-gradient(90deg, black ${yuzde}%, transparent ${Math.min(100, yuzde + 8)}%)`,
    right: `linear-gradient(270deg, black ${yuzde}%, transparent ${Math.min(100, yuzde + 8)}%)`,
    up: `linear-gradient(0deg, black ${yuzde}%, transparent ${Math.min(100, yuzde + 8)}%)`,
    down: `linear-gradient(180deg, black ${yuzde}%, transparent ${Math.min(100, yuzde + 8)}%)`,
  };
  const maske = yonHarita[yon] || yonHarita.left;
  return (
    <AbsoluteFill
      style={{
        maskImage: maske,
        WebkitMaskImage: maske,
        filter: t < 1 ? `blur(${(1 - t) * (yumusak / 12)}px)` : undefined,
      }}
    >
      {children}
    </AbsoluteFill>
  );
};

/** TRACK MATTE WIPE (pseudo) — yazi seklinden acilim yerine dikdortgen matte. */
export const TrackMatteWipe: React.FC<{
  spec: MotionSpec;
  fps: number;
  children: React.ReactNode;
}> = ({spec, fps, children}) => {
  const frame = useCurrentFrame();
  const basKare = sayi(spec.bas_sn, 0) * fps;
  const sure = Math.max(1, sayi(spec.sure_sn, 0.5) * fps);
  const t = ilerleme(frame, basKare, sure, spec);
  const bant = 3;
  return (
    <AbsoluteFill>
      {Array.from({length: bant}).map((_, i) => {
        const gecikme = i * 0.12;
        const ti = Math.max(0, Math.min(1, (t - gecikme) / (1 - gecikme || 1)));
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: 0,
              right: 0,
              top: `${(i * 100) / bant}%`,
              height: `${100 / bant}%`,
              overflow: 'hidden',
              clipPath: `inset(0 ${(1 - ti) * 100}% 0 0)`,
            }}
          >
            <div style={{position: 'absolute', top: `-${i * 100}%`, left: 0, right: 0, height: `${bant * 100}%`}}>
              {children}
            </div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

/** FILM BURN — restrained: siddet tavani 0.25 (yuksek deger ucuz durur). */
export const FilmBurn: React.FC<{spec: MotionSpec; fps: number}> = ({spec, fps}) => {
  const frame = useCurrentFrame();
  const basKare = sayi(spec.bas_sn, 0) * fps;
  const sure = Math.max(1, sayi(spec.sure_sn, 0.5) * fps);
  if (frame < basKare || frame > basKare + sure) return null;
  const t = ilerleme(frame, basKare, sure, spec);
  const siddet = Math.min(0.25, sayi(spec.parametre.siddet, 0.18));
  const sicaklik = sayi(spec.parametre.sicaklik, 0.6);
  // Ortadan disa dogru acilip kapanan sicak leke
  const genlik = Math.sin(t * Math.PI);
  return (
    <AbsoluteFill
      style={{
        pointerEvents: 'none',
        mixBlendMode: 'screen',
        opacity: genlik * siddet,
        background: `radial-gradient(circle at ${45 + t * 10}% ${52 - t * 6}%, ` +
          `rgba(255,${Math.round(170 + 60 * sicaklik)},${Math.round(90 * (1 - sicaklik))},0.95) 0%, ` +
          `rgba(255,120,40,0.35) 26%, transparent 58%)`,
        filter: 'blur(8px)',
      }}
    />
  );
};

/** KROMATIK ABERASYON — gerilim anlari icin, cok hafif. */
export const Kromatik: React.FC<{spec: MotionSpec; children: React.ReactNode}> = ({spec, children}) => {
  const k = Math.min(4, sayi(spec.parametre.k, 2));
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{filter: `drop-shadow(${-k}px 0 0 rgba(255,0,0,0.32))`}}>{children}</AbsoluteFill>
      <AbsoluteFill style={{filter: `drop-shadow(${k}px 0 0 rgba(0,80,255,0.28))`, mixBlendMode: 'screen', opacity: 0.5}}>
        {children}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

export const YonluBlur: React.FC<{spec: MotionSpec; children: React.ReactNode}> = ({spec, children}) => {
  const s = sayi(spec.parametre.sigma, 6);
  return <AbsoluteFill style={{filter: `blur(${s * 0.4}px)`}}>{children}</AbsoluteFill>;
};

/** Kenar korumasi: hicbir katman guvenli alanin disina yazmasin diye zemin. */
export const GuvenliAlanIsareti: React.FC<{goster: boolean}> = ({goster}) => {
  const {width, height} = useVideoConfig();
  if (!goster) return null;
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      <div
        style={{
          position: 'absolute',
          left: 64,
          top: 64,
          width: width - 128,
          height: height - 128,
          border: `1px dashed ${RENK.uyari}`,
          opacity: 0.35,
        }}
      />
    </AbsoluteFill>
  );
};
