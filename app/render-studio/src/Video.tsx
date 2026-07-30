import React from 'react';
import {
  AbsoluteFill,
  Audio,
  Easing,
  Img,
  OffthreadVideo,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {TransitionSeries, linearTiming} from '@remotion/transitions';
import {fade} from '@remotion/transitions/fade';

export type AltyaziParcasi = {t0: number; t1: number; metin: string};

export type Sahne = {
  tur: 'image' | 'video';
  medya: string;
  ses: string;
  sure: number;
  zoom: 'in' | 'out' | 'yok';
  pan: 'right' | 'left' | 'top' | 'bottom' | 'yok';
  overlay?: string;
  altyazi: AltyaziParcasi[];
  vurgu?: boolean; // hikaye kanalı açılış sahnesi: yoğun hareket (derin zoom + push-in + paralaks)
};

export type Motion = 'sinematik' | 'anlati' | 'hizli' | 'kesme' | 'fade' | 'dinamik' | 'hikaye';
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

export type NormMotion = 'sinematik' | 'anlati' | 'hizli' | 'kesme' | 'hikaye';

export const normMotion = (m?: Motion): NormMotion => {
  if (m === 'kesme') return 'kesme';
  if (m === 'dinamik' || m === 'anlati') return 'anlati';
  if (m === 'hizli') return 'hizli';
  if (m === 'hikaye') return 'hikaye';
  return 'sinematik';
};

// PREMIUM: eased Ken Burns egrisi (lineer degil -> yumusak ivme; bedava, sadece egri)
const KB_EASING = Easing.bezier(0.33, 0, 0.2, 1);

const sahneKare = (sure: number, fps: number) => Math.max(1, Math.round(sure * fps));

// Motion basina crossfade suresi (kare). 0 = hard cut (BBC tarzi, ses tam senkron, flash yok).
// hikaye: 10 kare yumusak crossfade (sinematik hikaye akisi).
const gecisTemel = (motion: NormMotion): number =>
  motion === 'anlati' ? 12 : motion === 'hizli' ? 8 : motion === 'hikaye' ? 10 : 0;

// TEK KAYNAK: Video ve Root ayni kareyi kullansin. Cok kisa sahnede gecisi guvenli kucultur.
export const hesaplaKareler = (
  sahneler: Sahne[],
  fps: number,
  motion: NormMotion,
) => {
  const Ks = sahneler.map((s) => sahneKare(s.sure, fps));
  const temel = gecisTemel(motion);
  const gecisler = Ks.slice(0, -1).map((_, i) => {
    if (temel === 0) return 0;
    const maxT = Math.floor(Math.min(Ks[i], Ks[i + 1]) / 2);
    return Math.max(0, Math.min(temel, maxT));
  });
  const toplam = Ks.reduce((a, b) => a + b, 0) - gecisler.reduce((a, b) => a + b, 0);
  return {Ks, gecisler, toplam: Math.max(1, toplam)};
};

const kbHesap = (sahne: Sahne, frame: number, K: number, buyume: number, panPx: number) => {
  if (sahne.zoom === 'yok') return {olcek: 1, tx: 0, ty: 0};
  const olcek = interpolate(frame, [0, K], sahne.zoom === 'in' ? [1, buyume] : [buyume, 1], {
    extrapolateRight: 'clamp',
    easing: KB_EASING,
  });
  const kayma = interpolate(frame, [0, K], [0, panPx], {
    extrapolateRight: 'clamp',
    easing: KB_EASING,
  });
  const tx = sahne.pan === 'right' ? -kayma : sahne.pan === 'left' ? kayma : 0;
  const ty = sahne.pan === 'bottom' ? -kayma : sahne.pan === 'top' ? kayma : 0;
  return {olcek, tx, ty};
};

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
          overflowWrap: 'anywhere',
          wordBreak: 'break-word',
          fontFamily:
            '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
          fontWeight: 800,
          fontSize: hizli ? 96 : 68,
          lineHeight: 1.05,
          letterSpacing: hizli ? 0 : -1,
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
          backgroundColor: 'rgba(0, 0, 0, 0.72)',
          color: 'white',
          overflowWrap: 'anywhere',
          wordBreak: 'break-word',
          fontFamily:
            '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
          fontSize: yogun ? 52 : 44,
          fontWeight: yogun ? 800 : 700,
          lineHeight: 1.25,
          textAlign: 'center',
          padding: '13px 28px',
          borderRadius: 14,
          textShadow: '0 2px 6px rgba(0,0,0,0.9), 0 0 2px rgba(0,0,0,0.9)',
        }}
      >
        {aktif.metin}
      </div>
    </AbsoluteFill>
  );
};

type Gorunum = {transform: string};

const sinematikHesapla = (sahne: Sahne, frame: number, K: number): Gorunum => {
  const {olcek, tx, ty} = kbHesap(sahne, frame, K, 1.06, 22);
  return {transform: `scale(${olcek}) translate(${tx}px, ${ty}px)`};
};

const kesmeHesapla = (sahne: Sahne, frame: number, K: number): Gorunum => {
  const {olcek, tx, ty} = kbHesap(sahne, frame, K, 1.06, 20);
  return {transform: `scale(${olcek}) translate(${tx}px, ${ty}px)`};
};

// blur YOK. Push-in reveal transform ile. fade her sahnede degil -> gecis crossfade yapar (flash yok).
const anlatiHesapla = (sahne: Sahne, frame: number, K: number): Gorunum => {
  const g = Math.max(8, Math.min(16, Math.floor(K / 4)));
  const girisP = interpolate(frame, [0, g], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });
  const girisOlcek = 1.12 - 0.12 * girisP;
  const {olcek: kb, tx: kbTx, ty: kbTy} = kbHesap(sahne, frame, K, 1.12, 40);
  return {transform: `translate(${kbTx}px, ${kbTy}px) scale(${kb * girisOlcek})`};
};

const hizliHesapla = (sahne: Sahne, frame: number, K: number, indeks: number): Gorunum => {
  const yon = indeks % 2 === 0 ? 1 : -1;
  const g = Math.max(4, Math.min(9, Math.floor(K / 4)));
  const girisP = interpolate(frame, [0, g], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });
  const girisOlcek = 1.18 - 0.18 * girisP;
  const girisX = (1 - girisP) * yon * 60;
  const cikisP = interpolate(frame, [K - g, K], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.in(Easing.cubic),
  });
  const cikisOlcek = 1 + cikisP * 0.12;
  const {olcek: kb} = kbHesap(sahne, frame, K, 1.08, 0);
  return {transform: `translateX(${girisX}px) scale(${kb * girisOlcek * cikisOlcek})`};
};

// Hikaye kanali: ACILIS sahneleri (vurgu=true, ilk ~2.5dk) yogun hareket alir — derin zoom +
// push-in giris + genis paralaks pan (izleyici tutma). Sonraki sahneler sakin sinematik Ken Burns.
// Hepsi transform-only: render maliyetine etkisi yok.
const hikayeHesapla = (sahne: Sahne, frame: number, K: number): Gorunum => {
  if (sahne.vurgu) {
    const g = Math.max(6, Math.min(14, Math.floor(K / 4)));
    const girisP = interpolate(frame, [0, g], [0, 1], {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
      easing: Easing.out(Easing.cubic),
    });
    const girisOlcek = 1.14 - 0.14 * girisP; // hizli push-in giris
    const {olcek, tx, ty} = kbHesap(sahne, frame, K, 1.16, 48); // derin zoom + genis pan
    return {transform: `translate(${tx}px, ${ty}px) scale(${olcek * girisOlcek})`};
  }
  const {olcek, tx, ty} = kbHesap(sahne, frame, K, 1.07, 26); // sakin bolum: standart Ken Burns
  return {transform: `scale(${olcek}) translate(${tx}px, ${ty}px)`};
};

// Bozuk/eksik gorsel ya da footage TUM render'i cokertmesin: onError -> koyu fallback kare.
const GuvenliGorsel: React.FC<{sahne: Sahne; stil: React.CSSProperties}> = ({sahne, stil}) => {
  const [hata, setHata] = React.useState(false);
  if (hata) return <AbsoluteFill style={{backgroundColor: '#0e0e12'}} />;
  return sahne.tur === 'video' ? (
    <OffthreadVideo src={kaynakCoz(sahne.medya)} muted style={stil} onError={() => setHata(true)} />
  ) : (
    <Img src={kaynakCoz(sahne.medya)} style={stil} onError={() => setHata(true)} />
  );
};

const SahneGorunumu: React.FC<{
  sahne: Sahne;
  indeks: number;
  motion: NormMotion;
  altyaziStil: AltyaziStil;
  kareSayisi: number;
}> = ({sahne, indeks, motion, altyaziStil, kareSayisi}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const K = kareSayisi;

  const g =
    motion === 'anlati'
      ? anlatiHesapla(sahne, frame, K)
      : motion === 'hizli'
      ? hizliHesapla(sahne, frame, K, indeks)
      : motion === 'kesme'
      ? kesmeHesapla(sahne, frame, K)
      : motion === 'hikaye'
      ? hikayeHesapla(sahne, frame, K)
      : sinematikHesapla(sahne, frame, K);

  const gorselStil: React.CSSProperties = {
    width: '100%',
    height: '100%',
    objectFit: 'cover',
    transform: g.transform,
  };

  return (
    <AbsoluteFill style={{backgroundColor: 'black'}}>
      <GuvenliGorsel sahne={sahne} stil={gorselStil} />
      {/* Vinyet (anlati/hizli/hikaye): tek radial-gradient, per-frame maliyet yok.
          Hikayede film-karesi hissi verir. */}
      {motion === 'anlati' || motion === 'hizli' || motion === 'hikaye' ? (
        <AbsoluteFill
          style={{
            background:
              'radial-gradient(ellipse at center, rgba(0,0,0,0) 52%, rgba(0,0,0,0.4) 100%)',
          }}
        />
      ) : null}
      <OverlayBaslik metin={sahne.overlay || ''} motion={motion} kareSayisi={K} />
      <Altyazi parcalar={sahne.altyazi} fps={fps} stil={altyaziStil} />
      <Audio src={kaynakCoz(sahne.ses)} />
    </AbsoluteFill>
  );
};

export const VidrushVideo: React.FC<VideoProps> = ({fps, gecis, altyaziStil, sahneler}) => {
  const motion = normMotion(gecis);
  const alt: AltyaziStil = altyaziStil ?? 'orta';   // yalnizca undefined/null -> 'orta' ('yok' korunur)
  const {Ks, gecisler} = hesaplaKareler(sahneler, fps, motion);

  const cocuklar: React.ReactNode[] = [];
  sahneler.forEach((sahne, i) => {
    cocuklar.push(
      <TransitionSeries.Sequence key={`s${i}`} durationInFrames={Ks[i]}>
        <SahneGorunumu
          sahne={sahne}
          indeks={i}
          motion={motion}
          altyaziStil={alt}
          kareSayisi={Ks[i]}
        />
      </TransitionSeries.Sequence>,
    );
    if (i < sahneler.length - 1 && gecisler[i] > 0) {
      cocuklar.push(
        <TransitionSeries.Transition
          key={`t${i}`}
          presentation={fade()}
          timing={linearTiming({durationInFrames: gecisler[i]})}
        />,
      );
    }
  });

  return (
    <AbsoluteFill style={{backgroundColor: 'black'}}>
      <TransitionSeries>{cocuklar}</TransitionSeries>
    </AbsoluteFill>
  );
};
