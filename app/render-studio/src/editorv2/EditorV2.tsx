/**
 * VidrushEditorV2 — Faz C motion spec sozlesmesini GERCEKTEN render eden
 * OPT-IN kompozisyon.
 *
 * ⚠ MEVCUT `VidrushVideo` DEGISMEDI. Bu ayri bir composition id; yalnizca
 * acikca cagrilirsa kosar. Canli hat (pipeline.py -> VidrushVideo) etkilenmez.
 *
 * Sahne akisi:
 *   Zemin (kamera transformu) [veya Parallax]
 *     -> maske/reveal sarmalayicilari
 *     -> doku katmanlari (grain/vignette/grade/letterbox)
 *     -> grafik katmanlari (baslik/alt band/callout/kunye/belge/harita/veri)
 *     -> isik katmanlari (light sweep / film burn)
 *     -> gecis
 *
 * BILINMEYEN SPEC: `dogrula()` FAIL verir ve render'a girmeden ekrana
 * ne oldugu YAZILIR (hatalariGoster). Sessizce dusme YOK.
 */
import React from 'react';
import {AbsoluteFill, Sequence, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';

import {
  AlintiKarti,
  AltBand,
  BelgeVurgusu,
  BolumBasligi,
  Callout,
  HaritaRota,
  KaynakEtiketi,
  KinetikBaslik,
  SahneYazisi,
  VeriGrafigi,
} from './Grafikler';
import {Parallax, Zemin} from './Kamera';
import {
  FilmBurn,
  Grade,
  Grain,
  Kromatik,
  Letterbox,
  LightSweep,
  MaskedReveal,
  TrackMatteWipe,
  Vignette,
  YonluBlur,
} from './Katmanlar';
import {DESTEK_MATRISI, dogrula} from './sozlesme';
import type {EditorSahne, EditorV2Props, MotionSpec} from './sozlesme';
import {FONT, RENK, sayi, specBul, specleriBul} from './temel';

const KAMERA_ADLARI = [
  'push-in',
  'pull-out',
  'pan-right',
  'pan-left',
  'static',
  'slow-drift',
  'handheld',
  'soft-zoom',
];
const GECIS_ADLARI = [
  'hard-cut',
  'crossfade',
  'karartma',
  'flash',
  'match-cut',
  'whip',
  'zoom-through',
  'glitch',
  'j-cut',
  'l-cut',
];

/** Sahne suresi -> kare (gecis ortusmesi hesaba katilmaz; Sequence'ler ardil). */
export const kareHesapla = (sahneler: EditorSahne[], fps: number): number[] =>
  sahneler.map((s) => Math.max(1, Math.round(sayi(s.sure, 1) * fps)));

/* ════════════════════ GECISLER ════════════════════ */

const GecisKatmani: React.FC<{spec: MotionSpec | null; sureKare: number; fps: number}> = ({
  spec,
  sureKare,
  fps,
}) => {
  const frame = useCurrentFrame();
  if (!spec) return null;
  const tur = String(spec.parametre.tur || spec.ad);
  const gs = Math.max(1, sayi(spec.parametre.sure, sayi(spec.sure_sn, 0.2)) * fps);

  // Giriste uygulanan gecisler
  if (tur === 'karartma') {
    // ⚠ SIYAHA INMEZ. Referans olcumu: parlaklik 88 -> 44 (yariya duser).
    // ffmpeg xfade=fadeblack asimetrik oldugu icin kendi dip'imizi kuruyoruz.
    const dip = sayi(spec.parametre.dip, 0.13);
    const op = interpolate(frame, [0, gs * 0.5, gs], [dip * 2.6, dip * 1.2, 0], {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
    });
    return <AbsoluteFill style={{background: '#000', opacity: Math.max(0, op), pointerEvents: 'none'}} />;
  }
  if (tur === 'flash') {
    const op = interpolate(frame, [0, gs * 0.35, gs], [0.55, 0.2, 0], {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
    });
    return <AbsoluteFill style={{background: '#fff', opacity: Math.max(0, op), pointerEvents: 'none'}} />;
  }
  if (tur === 'crossfade') {
    const op = interpolate(frame, [0, gs], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
    return <AbsoluteFill style={{background: '#0B0D10', opacity: Math.max(0, op) * 0.85, pointerEvents: 'none'}} />;
  }
  if (tur === 'glitch') {
    if (frame > gs) return null;
    const k = Math.floor(frame / 2) % 3;
    return (
      <AbsoluteFill style={{pointerEvents: 'none', mixBlendMode: 'screen', opacity: 0.5}}>
        <div
          style={{
            position: 'absolute',
            left: 0,
            right: 0,
            top: `${18 + k * 24}%`,
            height: 8,
            background: 'rgba(120,200,255,0.6)',
            transform: `translateX(${k % 2 ? -14 : 14}px)`,
          }}
        />
      </AbsoluteFill>
    );
  }
  // whip / zoom-through: hareket sarmalayicida uygulanir (asagida)
  return null;
};

/** whip / zoom-through: sahnenin ILK karelerinde transform ile. */
const gecisTransform = (spec: MotionSpec | null, frame: number, fps: number): string => {
  if (!spec) return '';
  const tur = String(spec.parametre.tur || spec.ad);
  const gs = Math.max(1, sayi(spec.parametre.sure, sayi(spec.sure_sn, 0.2)) * fps);
  if (frame > gs) return '';
  const t = Math.max(0, Math.min(1, frame / gs));
  if (tur === 'whip') {
    const kayma = interpolate(t, [0, 1], [26, 0]);
    const bulanik = interpolate(t, [0, 1], [1, 0]);
    return `translateX(${kayma}%) ` + (bulanik > 0.02 ? '' : '');
  }
  if (tur === 'zoom-through') {
    const z = interpolate(t, [0, 1], [1.22, 1]);
    return `scale(${z.toFixed(3)})`;
  }
  return '';
};

/* ════════════════════ TEK SAHNE ════════════════════ */

const SahneKatmani: React.FC<{sahne: EditorSahne; sureKare: number}> = ({sahne, sureKare}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const specler = sahne.motion || [];

  const kamera = specler.find((s) => KAMERA_ADLARI.includes(s.ad)) || null;
  const parallax = specBul(specler, 'parallax-2.5d');
  const maske = specBul(specler, 'masked-reveal');
  const matte = specBul(specler, 'track-matte-wipe');
  const kromatik = specBul(specler, 'chromatic');
  const yonBlur = specBul(specler, 'directional-blur');
  const gecis = specler.find((s) => GECIS_ADLARI.includes(String(s.parametre?.tur || s.ad))) || null;
  const dokular = specleriBul(specler, ['grain', 'vignette', 'grade', 'letterbox']);
  const isiklar = specleriBul(specler, ['light-sweep', 'film-burn']);
  const grafikler = specleriBul(specler, [
    'chapter-title',
    'lower-third',
    'source-label',
    'callout',
    'quote-card',
    'document-highlight',
    'map-route',
    'data-chart',
    'kinetic-title',
    'text-in-video',
  ]);

  // Tam ekran grafik sahneleri (harita/veri) zemini KAPLAR
  const tamEkranGrafik = grafikler.find((g) => g.ad === 'map-route' || g.ad === 'data-chart') || null;

  let zemin: React.ReactNode = tamEkranGrafik ? null : parallax ? (
    <Parallax sahne={sahne} spec={parallax} sureKare={sureKare} />
  ) : (
    <Zemin sahne={sahne} kameraSpec={kamera} sureKare={sureKare} />
  );

  if (zemin && kromatik) zemin = <Kromatik spec={kromatik}>{zemin}</Kromatik>;
  if (zemin && yonBlur) zemin = <YonluBlur spec={yonBlur}>{zemin}</YonluBlur>;
  if (zemin && maske) zemin = <MaskedReveal spec={maske} fps={fps}>{zemin}</MaskedReveal>;
  if (zemin && matte) zemin = <TrackMatteWipe spec={matte} fps={fps}>{zemin}</TrackMatteWipe>;

  const gTransform = gecisTransform(gecis, frame, fps);

  return (
    <AbsoluteFill style={{backgroundColor: RENK.taban, overflow: 'hidden'}}>
      <AbsoluteFill style={gTransform ? {transform: gTransform} : undefined}>
        {zemin}
        {tamEkranGrafik?.ad === 'map-route' ? <HaritaRota spec={tamEkranGrafik} fps={fps} /> : null}
        {tamEkranGrafik?.ad === 'data-chart' ? <VeriGrafigi spec={tamEkranGrafik} fps={fps} /> : null}
      </AbsoluteFill>

      {/* Doku katmanlari — zeminin uzerinde, grafiklerin altinda */}
      {dokular.map((d, i) => (
        <React.Fragment key={`d${i}`}>
          {d.ad === 'grain' ? <Grain spec={d} /> : null}
          {d.ad === 'vignette' ? <Vignette spec={d} /> : null}
          {d.ad === 'grade' ? <Grade spec={d} /> : null}
          {d.ad === 'letterbox' ? <Letterbox spec={d} /> : null}
        </React.Fragment>
      ))}

      {/* Grafik katmanlari */}
      {grafikler.map((g, i) => (
        <React.Fragment key={`g${i}`}>
          {g.ad === 'chapter-title' ? <BolumBasligi spec={g} fps={fps} /> : null}
          {g.ad === 'lower-third' ? <AltBand spec={g} fps={fps} /> : null}
          {g.ad === 'source-label' ? <KaynakEtiketi spec={g} fps={fps} /> : null}
          {g.ad === 'callout' ? <Callout spec={g} fps={fps} /> : null}
          {g.ad === 'quote-card' ? <AlintiKarti spec={g} fps={fps} /> : null}
          {g.ad === 'document-highlight' ? <BelgeVurgusu spec={g} fps={fps} /> : null}
          {g.ad === 'kinetic-title' ? <KinetikBaslik spec={g} fps={fps} /> : null}
          {/* text-in-video kamerayla birlikte hareket eder: kamera spec'ini alir */}
          {g.ad === 'text-in-video' ? (
            <SahneYazisi
              spec={g}
              kameraSpec={kamera}
              kadraj={sahne.kadraj}
              sureKare={sureKare}
              fps={fps}
            />
          ) : null}
        </React.Fragment>
      ))}

      {/* Isik katmanlari en ustte */}
      {isiklar.map((s, i) => (
        <React.Fragment key={`i${i}`}>
          {s.ad === 'light-sweep' ? <LightSweep spec={s} sureKare={sureKare} fps={fps} /> : null}
          {s.ad === 'film-burn' ? <FilmBurn spec={s} fps={fps} /> : null}
        </React.Fragment>
      ))}

      <GecisKatmani spec={gecis} sureKare={sureKare} fps={fps} />
    </AbsoluteFill>
  );
};

/* ════════════════════ HATA EKRANI ════════════════════ */

const HataEkrani: React.FC<{sorunlar: ReturnType<typeof dogrula>['sorunlar']}> = ({sorunlar}) => {
  const failler = sorunlar.filter((s) => s.seviye === 'fail');
  if (failler.length === 0) return null;
  return (
    <AbsoluteFill
      style={{
        background: 'rgba(20,6,6,0.94)',
        padding: 72,
        fontFamily: FONT.aile,
        color: '#FFD9D6',
      }}
    >
      <div style={{fontSize: 44, fontWeight: FONT.kalin, color: RENK.uyari, marginBottom: 24}}>
        MOTION SPEC DOGRULAMA HATASI — {failler.length} sorun
      </div>
      <div style={{fontSize: 20, opacity: 0.8, marginBottom: 20}}>
        Bilinmeyen/desteklenmeyen spec sessizce DUSURULMEZ. Render engellendi.
      </div>
      {failler.slice(0, 10).map((s, i) => (
        <div key={i} style={{fontSize: 22, marginBottom: 12, lineHeight: 1.4}}>
          <b>{s.kod}</b> · {s.scene_id}/{s.beat_id} · <code>{s.spec}</code>
          <div style={{fontSize: 18, opacity: 0.75}}>{s.detay}</div>
        </div>
      ))}
    </AbsoluteFill>
  );
};

/* ════════════════════ ANA KOMPOZISYON ════════════════════ */

export const VidrushEditorV2: React.FC<EditorV2Props> = (props) => {
  const {fps} = useVideoConfig();
  const sahneler = props.sahneler || [];
  const sonuc = dogrula(props);
  const kareler = kareHesapla(sahneler, fps);

  if (sonuc.durum === 'FAIL' && props.hatalariGoster !== false) {
    return (
      <AbsoluteFill style={{backgroundColor: RENK.taban}}>
        <HataEkrani sorunlar={sonuc.sorunlar} />
      </AbsoluteFill>
    );
  }

  let ofset = 0;
  return (
    <AbsoluteFill style={{backgroundColor: RENK.taban}}>
      {sahneler.map((sh, i) => {
        const bas = ofset;
        ofset += kareler[i];
        return (
          <Sequence key={sh.beat_id || i} from={bas} durationInFrames={kareler[i]} layout="none">
            <SahneKatmani sahne={sh} sureKare={kareler[i]} />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};

/** Studio'da bos ekran gorunmesin diye kucuk varsayilan. */
export const editorV2VarsayilanProps: EditorV2Props = {
  fps: 30,
  genislik: 1920,
  yukseklik: 1080,
  gecis: 'sinematik',
  altyaziStil: 'yok',
  sahneler: [
    {
      beat_id: 'b001',
      scene_id: 's001',
      fact_id: 'f001',
      asset_id: '',
      saglayici: '',
      lisans: '',
      tur: 'image',
      medya: '',
      ses: '',
      sure: 3,
      bas_sn: 0,
      islev: 'hook',
      perde: 'acilis',
      cekim_turu: 'atmospheric',
      hareket: 'push-in',
      kadraj: 'tam',
      kaynak_aralik: [0, 3],
      j_cut: false,
      l_cut: false,
      altyazi: [],
      gerekce: 'varsayilan',
      motion: [
        {
          ad: 'push-in',
          renderer: 'remotion',
          parametre: {zoom: [1, 1.12], pan_x: [0.5, 0.5], odak: [0.5, 0.5], guvenli_pay: 0.04},
          easing: 'kamera',
          easing_bezier: [0.42, 0.32, 0.58, 0.68],
          bas_sn: 0,
          sure_sn: 3,
          katman: 0,
          fallback: null,
          remotion_zorunlu: false,
          gerekce: 'varsayilan kamera',
        },
        {
          ad: 'chapter-title',
          renderer: 'remotion',
          parametre: {metin: 'VidrushEditorV2', punto: 60, y_orani: 0.7, bant_opaklik: 0.62},
          easing: 'giris',
          easing_bezier: [0.16, 1, 0.3, 1],
          bas_sn: 0.2,
          sure_sn: 2.4,
          katman: 30,
          fallback: null,
          remotion_zorunlu: false,
          gerekce: 'varsayilan baslik',
        },
        {
          ad: 'grain',
          renderer: 'remotion',
          parametre: {siddet: 0.35},
          easing: 'lineer',
          easing_bezier: [0, 0, 1, 1],
          bas_sn: 0,
          sure_sn: 3,
          katman: 90,
          fallback: null,
          remotion_zorunlu: false,
          gerekce: 'doku',
        },
        {
          ad: 'vignette',
          renderer: 'remotion',
          parametre: {siddet: 0.45},
          easing: 'lineer',
          easing_bezier: [0, 0, 1, 1],
          bas_sn: 0,
          sure_sn: 3,
          katman: 91,
          fallback: null,
          remotion_zorunlu: false,
          gerekce: 'doku',
        },
      ],
    },
  ],
};

export {DESTEK_MATRISI, dogrula};
