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

export type AltyaziParcasi = {
  t0: number;
  t1: number;
  metin: string;
};

export type Sahne = {
  tur: 'image' | 'video';
  medya: string;
  ses: string;
  sure: number;
  zoom: 'in' | 'out';
  pan: 'right' | 'left' | 'top' | 'bottom';
  altyazi: AltyaziParcasi[];
};

// 'fade'    -> yumusak sinematik fade (varsayilan)
// 'dinamik' -> After Effects tarzi belgesel: yonlu slide-in + zoom-punch + guclu Ken Burns + vinyet
export type Gecis = 'fade' | 'dinamik';

export type VideoProps = {
  fps: number;
  genislik: number;
  yukseklik: number;
  gecis?: Gecis;
  sahneler: Sahne[];
};

export const varsayilanProps: VideoProps = {
  fps: 30,
  genislik: 1920,
  yukseklik: 1080,
  gecis: 'fade',
  sahneler: [
    {
      tur: 'image',
      medya: 'ornek/ornek.png',
      ses: 'ornek/ornek.mp3',
      sure: 5,
      zoom: 'in',
      pan: 'right',
      altyazi: [{t0: 0, t1: 4, metin: 'Ornek altyazi'}],
    },
  ],
};

const kaynakCoz = (yol: string): string => {
  if (yol.startsWith('http://') || yol.startsWith('https://')) {
    return yol;
  }
  return staticFile(yol);
};

const Altyazi: React.FC<{parcalar: AltyaziParcasi[]; fps: number}> = ({
  parcalar,
  fps,
}) => {
  const frame = useCurrentFrame();
  const saniye = frame / fps;
  const aktif = parcalar.find((p) => saniye >= p.t0 && saniye < p.t1);
  if (!aktif) {
    return null;
  }
  return (
    <AbsoluteFill
      style={{
        justifyContent: 'flex-end',
        alignItems: 'center',
        paddingBottom: 70,
      }}
    >
      <div
        style={{
          maxWidth: '78%',
          backgroundColor: 'rgba(0, 0, 0, 0.62)',
          color: 'white',
          fontFamily:
            '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
          fontSize: 46,
          fontWeight: 700,
          lineHeight: 1.25,
          textAlign: 'center',
          padding: '14px 30px',
          borderRadius: 16,
        }}
      >
        {aktif.metin}
      </div>
    </AbsoluteFill>
  );
};

// Yumusak sinematik gecis (mevcut davranis)
const fadeHesapla = (sahne: Sahne, frame: number, kareSayisi: number) => {
  const gecis = Math.min(12, Math.floor(kareSayisi / 4));
  const opaklik = interpolate(
    frame,
    [0, gecis, kareSayisi - gecis, kareSayisi - 1],
    [0, 1, 1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}
  );
  const olcek = interpolate(
    frame,
    [0, kareSayisi],
    sahne.zoom === 'in' ? [1, 1.12] : [1.12, 1],
    {extrapolateRight: 'clamp'}
  );
  const kayma = interpolate(frame, [0, kareSayisi], [0, 26], {
    extrapolateRight: 'clamp',
  });
  const tx = sahne.pan === 'right' ? -kayma : sahne.pan === 'left' ? kayma : 0;
  const ty = sahne.pan === 'bottom' ? -kayma : sahne.pan === 'top' ? kayma : 0;
  return {opaklik, transform: `scale(${olcek}) translate(${tx}px, ${ty}px)`};
};

// After Effects tarzi belgesel gecisi: yonlu slide-in reveal + zoom-punch cikis + guclu Ken Burns
const dinamikHesapla = (
  sahne: Sahne,
  frame: number,
  kareSayisi: number,
  indeks: number
) => {
  const yon = indeks % 2 === 0 ? 1 : -1; // sahneler sirayla saga/sola kayar
  const gf = Math.max(6, Math.min(16, Math.floor(kareSayisi / 4.5)));

  // Giris: kenardan kayarak gelir + hafif buyukten normale oturur
  const girisP = interpolate(frame, [0, gf], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });
  const girisX = (1 - girisP) * yon * 150;
  const girisOlcek = 1.12 - 0.12 * girisP;

  // Cikis: ters yona hafif itilir + zoom-punch
  const cikisP = interpolate(
    frame,
    [kareSayisi - gf, kareSayisi],
    [0, 1],
    {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
      easing: Easing.in(Easing.cubic),
    }
  );
  const cikisX = cikisP * -yon * 100;
  const cikisOlcek = 1 + cikisP * 0.08;

  const opaklik = interpolate(
    frame,
    [0, gf, kareSayisi - gf, kareSayisi - 1],
    [0, 1, 1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}
  );

  // Ken Burns (fade'den daha guclu) + pan
  const kb = interpolate(
    frame,
    [0, kareSayisi],
    sahne.zoom === 'in' ? [1, 1.18] : [1.18, 1],
    {extrapolateRight: 'clamp'}
  );
  const kayma = interpolate(frame, [0, kareSayisi], [0, 48], {
    extrapolateRight: 'clamp',
  });
  const kbTx = sahne.pan === 'right' ? -kayma : sahne.pan === 'left' ? kayma : 0;
  const kbTy = sahne.pan === 'bottom' ? -kayma : sahne.pan === 'top' ? kayma : 0;

  const olcek = kb * girisOlcek * cikisOlcek;
  const tx = kbTx + girisX + cikisX;
  return {
    opaklik,
    transform: `translate(${tx}px, ${kbTy}px) scale(${olcek})`,
  };
};

const SahneGorunumu: React.FC<{
  sahne: Sahne;
  indeks: number;
  gecis: Gecis;
}> = ({sahne, indeks, gecis}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const kareSayisi = Math.max(1, Math.round(sahne.sure * fps));

  const dinamik = gecis === 'dinamik';
  const {opaklik, transform} = dinamik
    ? dinamikHesapla(sahne, frame, kareSayisi, indeks)
    : fadeHesapla(sahne, frame, kareSayisi);

  return (
    <AbsoluteFill style={{backgroundColor: 'black'}}>
      <AbsoluteFill style={{opacity: opaklik}}>
        {sahne.tur === 'video' ? (
          <OffthreadVideo
            src={kaynakCoz(sahne.medya)}
            muted
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
              transform: dinamik ? transform : undefined,
            }}
          />
        ) : (
          <Img
            src={kaynakCoz(sahne.medya)}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
              transform,
            }}
          />
        )}
        {dinamik ? (
          <AbsoluteFill
            style={{
              background:
                'radial-gradient(ellipse at center, rgba(0,0,0,0) 55%, rgba(0,0,0,0.38) 100%)',
            }}
          />
        ) : null}
        <Altyazi parcalar={sahne.altyazi} fps={fps} />
      </AbsoluteFill>
      <Audio src={kaynakCoz(sahne.ses)} />
    </AbsoluteFill>
  );
};

export const VidrushVideo: React.FC<VideoProps> = ({fps, gecis, sahneler}) => {
  const mod: Gecis = gecis === 'dinamik' ? 'dinamik' : 'fade';
  return (
    <AbsoluteFill style={{backgroundColor: 'black'}}>
      <Series>
        {sahneler.map((sahne, i) => (
          <Series.Sequence
            key={i}
            durationInFrames={Math.max(1, Math.round(sahne.sure * fps))}
          >
            <SahneGorunumu sahne={sahne} indeks={i} gecis={mod} />
          </Series.Sequence>
        ))}
      </Series>
    </AbsoluteFill>
  );
};
