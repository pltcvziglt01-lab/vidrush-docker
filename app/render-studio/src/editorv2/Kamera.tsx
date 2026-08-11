/**
 * KAMERA ve DERINLIK KATMANLARI.
 *
 * Kamera: push-in / pull-out / pan / slow-drift / handheld — hepsi OLCULEN
 * easing egrisiyle (lineere yakin, bezier 0.42,0.32,0.58,0.68). Ilk surumlerde
 * on-yuklemeli egri kullaniyordum ve hareket "yazilim zoom'u" gibi duruyordu.
 *
 * 2.5D PARALLAX — DURUST SINIR: gercek katman ayrimi icin on/orta/arka
 * gorseller gerekiyor. `parallax_katmanlari` verilmezse tek gorsel uc OLCEK
 * katmanina bolunup farkli hizlarda kaydiriliyor (pseudo-depth). Derinlik
 * illuzyonu olusuyor ama GERCEK OKLUZYON YOK — destek matrisi bunu
 * `pseudo` olarak beyan ediyor ve validator bilgi notu uretiyor.
 */
import React from 'react';
import {AbsoluteFill, Img, OffthreadVideo, interpolate, useCurrentFrame, useVideoConfig, staticFile} from 'remotion';

import type {EditorSahne, MotionSpec} from './sozlesme';
import {dizi, easingAl, ilerleme, sayi, tohum} from './temel';

const KADRAJ_OLCEK: Record<string, number> = {
  tam: 1.0,
  'punch-1.35': 1.35,
  'punch-1.6': 1.6,
  ust: 1.2,
  alt: 1.2,
};
const KADRAJ_ODAK: Record<string, [number, number]> = {
  ust: [0.5, 0.3],
  alt: [0.5, 0.7],
};

interface KameraDurumu {
  olcek: number;
  x: number;
  y: number;
  donme: number;
}

/** Kamera spec'inden o karedeki transform. */
/**
 * Medya yolunu Remotion'un cozebilecegi hale getir.
 *
 * 11 Agu: props'a duz `editorv2/faz_d/aD00.jpg` yazmak 404 verdi. public/
 * altindaki dosyalar `staticFile()` ile cozulmek zorunda; http/file/data
 * yollari oldugu gibi gecer.
 */
export const medyaYolu = (yol: string): string => {
  if (!yol) return '';
  if (/^(https?:|file:|data:|blob:)/.test(yol)) return yol;
  return staticFile(yol.replace(/^\/+/, ''));
};

export const kameraDurumu = (
  spec: MotionSpec | null,
  kadraj: string,
  frame: number,
  sureKare: number,
): KameraDurumu => {
  const prm = spec?.parametre || {};
  const zoom = dizi(prm.zoom);
  const panX = dizi(prm.pan_x);
  const odak = dizi(prm.odak);
  const kadrajOlcek = KADRAJ_OLCEK[kadraj] ?? 1.0;
  const kadrajOdak = KADRAJ_ODAK[kadraj];

  const z0 = zoom.length ? zoom[0] : kadrajOlcek;
  const z1 = zoom.length > 1 ? zoom[1] : z0;
  const t = ilerleme(frame, 0, sureKare, spec);
  const olcek = interpolate(t, [0, 1], [z0, z1]);

  // Pan: guvenli pay kadar kaydirma (kenarda siyah bant OLUSMAMALI)
  const pay = sayi(prm.guvenli_pay, 0.04);
  const px0 = panX.length ? panX[0] : 0.5;
  const px1 = panX.length > 1 ? panX[1] : px0;
  const pxT = interpolate(t, [0, 1], [px0, px1]);
  // 0..1 -> -pay..+pay (yuzde cinsinden kaydirma)
  const kaymaX = (pxT - 0.5) * 2 * pay * 100;

  const odakY = kadrajOdak ? kadrajOdak[1] : odak.length > 1 ? odak[1] : 0.5;
  const kaymaY = (0.5 - odakY) * 2 * pay * 100;

  // Handheld: iki farkli frekansta organik titreme (mekanik gorunmesin)
  const genlik = sayi(prm.handheld_genlik_px, 0);
  const hx = genlik ? (tohum(frame, 1) - 0.5) * genlik * 0.6 + Math.sin(frame / 7) * genlik * 0.4 : 0;
  const hy = genlik ? (tohum(frame, 2) - 0.5) * genlik * 0.6 + Math.cos(frame / 9) * genlik * 0.4 : 0;
  const donme = genlik ? Math.sin(frame / 23) * 0.25 : 0;

  // ── ATIL SURUKLENME (idle drift) ──
  // ⚠ 11 Agu olcumu: `static` kamerali sahnelerde grafik animasyonu bitince
  // kare TAMAMEN duruyordu ve freezedetect 3 donmus blok yakaladi (12.7s,
  // 15.2s, 20.0s). Belgeselde 1 sn'den uzun olu kare izleyiciyi dusuruyor.
  // Cozum: gercek bir hareket YOKSA algilanabilir ama fark edilmez bir
  // suruklenme ekle. Referans olcumunde zoom medyani %1.57/sn idi; buradaki
  // %0.6/sn onun caginin altinda, yani "static" niyeti korunur.
  const hareketVar =
    Math.abs(z1 - z0) > 0.004 || Math.abs(px1 - px0) > 0.004 || genlik > 0;
  let atilOlcek = 1;
  let atilX = 0;
  let atilY = 0;
  if (!hareketVar && sureKare > 0) {
    const sn = sureKare / 30; // yaklasik: fps burada yok, 30 tabanli
    atilOlcek = 1 + 0.006 * sn * t;
    // Cok hafif yatay/dikey kayma: tek eksende olsa "kayan slayt" gibi durur
    atilX = Math.sin(t * Math.PI) * 0.35;
    atilY = -t * 0.25;
  }

  return {
    olcek: olcek * atilOlcek,
    x: kaymaX + hx / 10 + atilX,
    y: kaymaY + hy / 10 + atilY,
    donme,
  };
};

/** Zemin medyasi (gorsel/video) — kamera transformu uygulanmis. */
export const Zemin: React.FC<{
  sahne: EditorSahne;
  kameraSpec: MotionSpec | null;
  sureKare: number;
}> = ({sahne, kameraSpec, sureKare}) => {
  const frame = useCurrentFrame();
  const k = kameraDurumu(kameraSpec, sahne.kadraj, frame, sureKare);
  const stil: React.CSSProperties = {
    transform:
      `scale(${k.olcek.toFixed(4)}) translate(${k.x.toFixed(3)}%, ${k.y.toFixed(3)}%) ` +
      `rotate(${k.donme.toFixed(3)}deg)`,
    transformOrigin: 'center center',
    width: '100%',
    height: '100%',
    objectFit: 'cover',
  };
  if (!sahne.medya) {
    // Medya yok: sentetik zemin (validator WARN uretti, sessiz degil)
    return (
      <AbsoluteFill
        style={{
          background: `linear-gradient(${(sahne.beat_id.length * 37) % 360}deg, #12161B, #1D242C)`,
          transform: stil.transform,
        }}
      />
    );
  }
  if (sahne.tur === 'video') {
    const bas = (sahne.kaynak_aralik && sahne.kaynak_aralik[0]) || 0;
    return (
      <AbsoluteFill>
        <OffthreadVideo src={medyaYolu(sahne.medya)} startFrom={Math.round(bas * 30)} style={stil} muted />
      </AbsoluteFill>
    );
  }
  return (
    <AbsoluteFill>
      <Img src={medyaYolu(sahne.medya)} style={stil} />
    </AbsoluteFill>
  );
};

/**
 * 2.5D PARALLAX. Katman gorselleri varsa GERCEK ayrim, yoksa pseudo-depth.
 * Her katman farkli hizda kayar + arkaya dogru artan bulaniklik.
 */
export const Parallax: React.FC<{
  sahne: EditorSahne;
  spec: MotionSpec;
  sureKare: number;
}> = ({sahne, spec, sureKare}) => {
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  const hizlar = dizi(spec.parametre.katman_hizlari);
  const bulanik = dizi(spec.parametre.derinlik_bulaniklik);
  const kayma = dizi(spec.parametre.kamera_kaymasi_px);
  const kaymaMaks = kayma.length > 1 ? kayma[1] : 42;
  const t = ilerleme(frame, 0, sureKare, spec);
  const hazir = sahne.parallax_katmanlari && sahne.parallax_katmanlari.length >= 2;
  const katmanSayisi = hazir ? sahne.parallax_katmanlari!.length : Math.max(2, hizlar.length || 3);

  return (
    <AbsoluteFill>
      {Array.from({length: katmanSayisi}).map((_, i) => {
        // Arka katman EN YAVAS: ters sirada hiz
        const hiz = hizlar[i] ?? 1 - i / katmanSayisi;
        const dx = -kaymaMaks * hiz * t;
        const bl = bulanik[i] ?? i * 0.6;
        // Pseudo-depth: ayni gorsel, artan olcek + azalan opaklik ile katmanlanir
        const olcek = hazir ? 1.06 : 1.02 + (katmanSayisi - 1 - i) * 0.09;
        const kaynak = hazir ? sahne.parallax_katmanlari![i] : sahne.medya;
        const stil: React.CSSProperties = {
          position: 'absolute',
          inset: 0,
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          transform: `translateX(${dx.toFixed(2)}px) scale(${olcek.toFixed(3)})`,
          filter: bl ? `blur(${bl.toFixed(2)}px)` : undefined,
          // Pseudo modda on katmanlar kismen saydam: derinlik hissi
          opacity: hazir ? 1 : i === katmanSayisi - 1 ? 1 : 0.55 - i * 0.12,
          // On katman alt yarida maskeleniyor -> zeminden ayrilma illuzyonu
          maskImage:
            hazir || i === katmanSayisi - 1
              ? undefined
              : `linear-gradient(to bottom, transparent ${28 + i * 14}%, black ${52 + i * 12}%)`,
          WebkitMaskImage:
            hazir || i === katmanSayisi - 1
              ? undefined
              : `linear-gradient(to bottom, transparent ${28 + i * 14}%, black ${52 + i * 12}%)`,
        };
        if (!kaynak) {
          return <div key={i} style={{...stil, background: '#151A20'}} />;
        }
        return <Img key={i} src={medyaYolu(kaynak)} style={stil} />;
      })}
      {/* Derinlik icin hafif dip: alt kenar koyulasir */}
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse at 50% 45%, transparent 45%, rgba(0,0,0,0.35) 100%)`,
          width,
          height,
        }}
      />
    </AbsoluteFill>
  );
};
