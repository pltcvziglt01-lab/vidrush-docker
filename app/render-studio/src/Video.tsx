import React from 'react';
import {
  AbsoluteFill,
  Audio,
  Easing,
  Img,
  OffthreadVideo,
  Series,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';

export type AltyaziParcasi = {t0: number; t1: number; metin: string};

export type Sahne = {
  tur: 'image' | 'video';
  medya: string;
  ses: string;
  sure: number;
  zoom: 'in' | 'out';
  pan: 'right' | 'left' | 'top' | 'bottom';
  overlay?: string;
  altyazi: AltyaziParcasi[];
};

// Edit stili motion profili:
// 'sinematik' -> BBC Earth: hard-cut, hafif Ken Burns, overlay yok
// 'anlati'    -> Johnny Harris: blur->net Ken Burns 2.0 push-in, vinyet, kinetik baslik
// 'hizli'     -> Vox: hizli zoom-punch + blur, surekli kinetik merkez metin
export type Motion = 'sinematik' | 'anlati' | 'hizli' | 'fade' | 'dinamik';
export type AltyaziStil = 'yok' | 'orta' | 'yogun';

export type VideoProps = {
  fps: number;
  genislik: number;
  yukseklik: number;
  gecis?: Motion;
  altyaziStil?: AltyaziStil;
  sahneler: Sahne[];
};

export const varsayilanProps: VideoProps = {
  fps: 30,
  genislik: 1920,
  yukseklik: 1080,
  gecis: 'sinematik',
  altyaziStil: 'orta',
  sahneler: [
    {
      tur: 'image',
      medya: 'ornek/ornek.png',
      ses: 'ornek/ornek.mp3',
      sure: 5,
      zoom: 'in',
      pan: 'right',
      overlay: '',
      altyazi: [{t0: 0, t1: 4, metin: 'Ornek altyazi'}],
    },
  ],
};

const kaynakCoz = (yol: string): string =>
  yol.startsWith('http://') || yol.startsWith('https://') ? yol : staticFile(yol);

const normMotion = (m?: Motion): 'sinematik' | 'anlati' | 'hizli' => {
  if (m === 'dinamik' || m === 'anlati') return 'anlati';
  if (m === 'hizli') return 'hizli';
  return 'sinematik';
};

// ─── Kinetik baslik overlay (anlati + hizli) ───
const OverlayBaslik: React.FC<{metin: string; motion: string; kareSayisi: number}> = ({
  metin,
  motion,
  kareSayisi,
}) => {
  const frame = useCurrentFrame();
  if (!metin) return null;
  const gir = interpolate(frame, [0, 8], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });
  const hizli = motion === 'hizli';
  // hizli: sahneler kisa, baslik sahne boyunca kalir; anlati: ~2sn sonra soner
  const cikisBas = hizli ? kareSayisi - 6 : Math.min(kareSayisi - 6, 60);
  const cik = interpolate(frame, [cikisBas, kareSayisi], [1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const opak = Math.min(gir, cik);
  const ty = (1 - gir) * 24;

  return (
    <AbsoluteFill
      style={{
        justifyContent: hizli ? 'center' : 'flex-start',
        alignItems: 'center',
        paddingTop: hizli ? 0 : 120,
      }}
    >
      <div
        style={{
          opacity: opak,
          transform: `translateY(${ty}px)`,
          maxWidth: '84%',
          textAlign: 'center',
          fontFamily:
            '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
          fontWeight: 800,
          fontSize: hizli ? 96 : 68,
          lineHeight: 1.05,
          letterSpacing: hizli ? 0 : -1,
          textTransform: 'uppercase',
          color: hizli ? '#0a0a0a' : '#ffffff',
          background: hizli ? '#ffd400' : 'transparent',
          padding: hizli ? '10px 26px' : 0,
          borderRadius: hizli ? 10 : 0,
          textShadow: hizli ? 'none' : '0 4px 24px rgba(0,0,0,0.75)',
        }}
      >
        {metin}
      </div>
    </AbsoluteFill>
  );
};

const Altyazi: React.FC<{parcalar: AltyaziParcasi[]; fps: number; stil: AltyaziStil}> = ({
  parcalar,
  fps,
  stil,
}) => {
  const frame = useCurrentFrame();
  const saniye = frame / fps;
  const aktif = parcalar.find((p) => saniye >= p.t0 && saniye < p.t1);
  if (!aktif || stil === 'yok') return null;
  const yogun = stil === 'yogun';
  return (
    <AbsoluteFill style={{justifyContent: 'flex-end', alignItems: 'center', paddingBottom: 64}}>
      <div
        style={{
          maxWidth: '80%',
          backgroundColor: 'rgba(0, 0, 0, 0.6)',
          color: 'white',
          fontFamily:
            '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
          fontSize: yogun ? 52 : 44,
          fontWeight: yogun ? 800 : 700,
          lineHeight: 1.25,
          textAlign: 'center',
          padding: '13px 28px',
          borderRadius: 14,
        }}
      >
        {aktif.metin}
      </div>
    </AbsoluteFill>
  );
};

type Gorunum = {opaklik: number; transform: string; filtre: string};

const sinematikHesapla = (sahne: Sahne, frame: number, K: number): Gorunum => {
  // hard-cut hissi: cok kisa (3 kare) giris/cikis fade, lineer hafif Ken Burns
  const g = 3;
  const opaklik = interpolate(frame, [0, g, K - g, K - 1], [0, 1, 1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const olcek = interpolate(frame, [0, K], sahne.zoom === 'in' ? [1, 1.06] : [1.06, 1], {
    extrapolateRight: 'clamp',
  });
  const kayma = interpolate(frame, [0, K], [0, 22], {extrapolateRight: 'clamp'});
  const tx = sahne.pan === 'right' ? -kayma : sahne.pan === 'left' ? kayma : 0;
  const ty = sahne.pan === 'bottom' ? -kayma : sahne.pan === 'top' ? kayma : 0;
  return {opaklik, transform: `scale(${olcek}) translate(${tx}px, ${ty}px)`, filtre: 'none'};
};

const anlatiHesapla = (sahne: Sahne, frame: number, K: number): Gorunum => {
  // Ken Burns 2.0: blur->net + hafif buyukten normale ease-out push-in
  const g = Math.max(8, Math.min(16, Math.floor(K / 4)));
  const girisP = interpolate(frame, [0, g], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });
  const blur = (1 - girisP) * 22;
  const girisOlcek = 1.1 - 0.1 * girisP;
  const kb = interpolate(frame, [0, K], sahne.zoom === 'in' ? [1, 1.12] : [1.12, 1], {
    extrapolateRight: 'clamp',
  });
  const kayma = interpolate(frame, [0, K], [0, 40], {extrapolateRight: 'clamp'});
  const kbTx = sahne.pan === 'right' ? -kayma : sahne.pan === 'left' ? kayma : 0;
  const kbTy = sahne.pan === 'bottom' ? -kayma : sahne.pan === 'top' ? kayma : 0;
  const opaklik = interpolate(frame, [0, g, K - g, K - 1], [0, 1, 1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  return {
    opaklik,
    transform: `translate(${kbTx}px, ${kbTy}px) scale(${kb * girisOlcek})`,
    filtre: `blur(${blur.toFixed(2)}px)`,
  };
};

const hizliHesapla = (sahne: Sahne, frame: number, K: number, indeks: number): Gorunum => {
  // hizli zoom-punch + blur giris; ters yona cikis
  const yon = indeks % 2 === 0 ? 1 : -1;
  const g = Math.max(4, Math.min(9, Math.floor(K / 4)));
  const girisP = interpolate(frame, [0, g], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });
  const blur = (1 - girisP) * 16;
  const girisOlcek = 1.18 - 0.18 * girisP;
  const girisX = (1 - girisP) * yon * 60;
  const cikisP = interpolate(frame, [K - g, K], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.in(Easing.cubic),
  });
  const cikisOlcek = 1 + cikisP * 0.12;
  const kb = interpolate(frame, [0, K], sahne.zoom === 'in' ? [1, 1.08] : [1.08, 1], {
    extrapolateRight: 'clamp',
  });
  const opaklik = interpolate(frame, [0, g, K - Math.min(g, 4), K - 1], [0, 1, 1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  return {
    opaklik,
    transform: `translateX(${girisX}px) scale(${kb * girisOlcek * cikisOlcek})`,
    filtre: `blur(${blur.toFixed(2)}px)`,
  };
};

const SahneGorunumu: React.FC<{
  sahne: Sahne;
  indeks: number;
  motion: 'sinematik' | 'anlati' | 'hizli';
  altyaziStil: AltyaziStil;
}> = ({sahne, indeks, motion, altyaziStil}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const K = Math.max(1, Math.round(sahne.sure * fps));

  const g =
    motion === 'anlati'
      ? anlatiHesapla(sahne, frame, K)
      : motion === 'hizli'
      ? hizliHesapla(sahne, frame, K, indeks)
      : sinematikHesapla(sahne, frame, K);

  const gorselStil: React.CSSProperties = {
    width: '100%',
    height: '100%',
    objectFit: 'cover',
    transform: g.transform,
    filter: g.filtre,
  };

  return (
    <AbsoluteFill style={{backgroundColor: 'black'}}>
      <AbsoluteFill style={{opacity: g.opaklik}}>
        {sahne.tur === 'video' ? (
          <OffthreadVideo src={kaynakCoz(sahne.medya)} muted style={gorselStil} />
        ) : (
          <Img src={kaynakCoz(sahne.medya)} style={gorselStil} />
        )}
        {motion !== 'sinematik' ? (
          <AbsoluteFill
            style={{
              background:
                'radial-gradient(ellipse at center, rgba(0,0,0,0) 52%, rgba(0,0,0,0.4) 100%)',
            }}
          />
        ) : null}
        <OverlayBaslik metin={sahne.overlay || ''} motion={motion} kareSayisi={K} />
        <Altyazi parcalar={sahne.altyazi} fps={fps} stil={altyaziStil} />
      </AbsoluteFill>
      <Audio src={kaynakCoz(sahne.ses)} />
    </AbsoluteFill>
  );
};

export const VidrushVideo: React.FC<VideoProps> = ({fps, gecis, altyaziStil, sahneler}) => {
  const motion = normMotion(gecis);
  const alt: AltyaziStil = altyaziStil || 'orta';
  return (
    <AbsoluteFill style={{backgroundColor: 'black'}}>
      <Series>
        {sahneler.map((sahne, i) => (
          <Series.Sequence key={i} durationInFrames={Math.max(1, Math.round(sahne.sure * fps))}>
            <SahneGorunumu sahne={sahne} indeks={i} motion={motion} altyaziStil={alt} />
          </Series.Sequence>
        ))}
      </Series>
    </AbsoluteFill>
  );
};
