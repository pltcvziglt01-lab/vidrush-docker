import React from 'react';
import {
  AbsoluteFill,
  Audio,
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

export type VideoProps = {
  fps: number;
  genislik: number;
  yukseklik: number;
  sahneler: Sahne[];
};

export const varsayilanProps: VideoProps = {
  fps: 30,
  genislik: 1920,
  yukseklik: 1080,
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

const SahneGorunumu: React.FC<{sahne: Sahne}> = ({sahne}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const kareSayisi = Math.max(1, Math.round(sahne.sure * fps));

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
  const tx =
    sahne.pan === 'right' ? -kayma : sahne.pan === 'left' ? kayma : 0;
  const ty =
    sahne.pan === 'bottom' ? -kayma : sahne.pan === 'top' ? kayma : 0;

  return (
    <AbsoluteFill style={{backgroundColor: 'black'}}>
      <AbsoluteFill style={{opacity: opaklik}}>
        {sahne.tur === 'video' ? (
          <OffthreadVideo
            src={kaynakCoz(sahne.medya)}
            muted
            style={{width: '100%', height: '100%', objectFit: 'cover'}}
          />
        ) : (
          <Img
            src={kaynakCoz(sahne.medya)}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
              transform: `scale(${olcek}) translate(${tx}px, ${ty}px)`,
            }}
          />
        )}
        <Altyazi parcalar={sahne.altyazi} fps={fps} />
      </AbsoluteFill>
      <Audio src={kaynakCoz(sahne.ses)} />
    </AbsoluteFill>
  );
};

export const VidrushVideo: React.FC<VideoProps> = ({fps, sahneler}) => {
  return (
    <AbsoluteFill style={{backgroundColor: 'black'}}>
      <Series>
        {sahneler.map((sahne, i) => (
          <Series.Sequence
            key={i}
            durationInFrames={Math.max(1, Math.round(sahne.sure * fps))}
          >
            <SahneGorunumu sahne={sahne} />
          </Series.Sequence>
        ))}
      </Series>
    </AbsoluteFill>
  );
};
