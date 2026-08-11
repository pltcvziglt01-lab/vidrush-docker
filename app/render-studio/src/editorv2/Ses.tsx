/**
 * SES ZAMAN CIZELGESI — anlatim + ambans + muzik + ducking.
 *
 * ⚠ FAZ D ACIGI (kullanici tespiti): V2 `scene.ses` alanini TASIYORDU ama
 * hicbir yerde `<Audio>` yoktu. Props'ta ses vardi, videoda yoktu — "beyan
 * var, cikti yok" hatasinin ses tarafindaki karsiligi. Mevcut `Video.tsx` (V1)
 * `<Audio src={kaynakCoz(sahne.ses)} />` kullaniyordu; V2'de hic uygulanmamisti.
 *
 * KATMANLAR
 *   anlatim  : tek master dosya (0'dan baslar) VE/VEYA sahne basina ayri dosya
 *   ambans   : ortam sesi, dongu, anlatim varken KISILIR (ducking)
 *   muzik    : yatak muzigi, ambanstan daha derin kisilir
 *
 * DUCKING NEDEN KODDA:
 * Anlatimin uzerine acik muzik en sik amatör hata. Renderer garanti ederse bir
 * sahnede unutulamaz; plan katmanina birakilirsa unutulur.
 */
import React from 'react';
import {Audio, Sequence, useVideoConfig} from 'remotion';

import {medyaYolu} from './Kamera';
import type {EditorSahne, SesAyari} from './sozlesme';
import {dizi, sayi} from './temel';

/** Anlatim varken yatak seslerinin dusurulecegi carpanlar. */
export const DUCK = {
  /** Ambans ~-9 dB: ortam hissi kalir, sozu bogmaz */
  ambans: 0.35,
  /** Muzik ~-14 dB: yalnizca duygu tasir */
  muzik: 0.2,
  /** Ducking rampasi (sn). 0.25'ten kisasi "pompalama" duyulur. */
  gecisSn: 0.35,
};

/** Sahne sesi olan sahnelerin zaman araliklari — ducking icin anlatim sayilir. */
export const sahneAraliklari = (
  sahneler: EditorSahne[],
  kareler: number[],
  fps: number,
): number[][] => {
  const out: number[][] = [];
  let ofset = 0;
  sahneler.forEach((sh, i) => {
    const bas = ofset;
    ofset += kareler[i] || 0;
    if (sh.ses) out.push([bas / fps, (bas + (kareler[i] || 0)) / fps]);
  });
  return out;
};

/**
 * Bir karede ducking carpani.
 *
 * `araliklar` = [[t0,t1],...] saniye. Aralik icinde `dip`, disinda 1; kenarlarda
 * `DUCK.gecisSn` boyunca dogrusal rampa (ani dusus tik sesi gibi duyulur).
 */
export const duckCarpani = (
  frame: number,
  fps: number,
  araliklar: number[][],
  dip: number,
): number => {
  if (!araliklar.length) return 1;
  const t = frame / fps;
  const g = Math.max(0.05, DUCK.gecisSn);
  let enDusuk = 1;
  for (const a of araliklar) {
    const t0 = sayi(a[0], 0);
    const t1 = sayi(a[1], 0);
    if (t1 <= t0) continue;
    let c = 1;
    if (t >= t0 && t <= t1) {
      c = dip;
      if (t - t0 < g) c = 1 + (dip - 1) * ((t - t0) / g);
      else if (t1 - t < g) c = 1 + (dip - 1) * ((t1 - t) / g);
    } else if (t > t0 - g && t < t0) {
      c = 1 + (dip - 1) * ((t - (t0 - g)) / g);
    } else if (t > t1 && t < t1 + g) {
      c = 1 + (dip - 1) * ((t1 + g - t) / g);
    }
    if (c < enDusuk) enDusuk = c;
  }
  return enDusuk;
};

/**
 * SAHNE SESLERI — J/L cut ofsetleriyle, KOK zaman cizelgesinde mutlak konumda.
 *
 * J-cut : ses goruntuden ONCE girer  -> baslangic geriye kayar
 * L-cut : ses goruntuden SONRA biter -> uzunluk uzar
 *
 * ⚠ Sahne Sequence'inin ICINE koyulsa J/L cut CALISMAZ: Remotion bir
 * Sequence'in disina tasan sesi kirpar. Bu yuzden sesler kokte, kendi
 * Sequence'lerinde duruyor.
 */
export const SahneSesleri: React.FC<{
  sahneler: EditorSahne[];
  kareler: number[];
}> = ({sahneler, kareler}) => {
  const {fps} = useVideoConfig();
  let ofset = 0;
  const parcalar: React.ReactNode[] = [];

  sahneler.forEach((sh, i) => {
    const bas = ofset;
    ofset += kareler[i] || 0;
    if (!sh.ses) return;

    // Referans olcumunde J/L cut'lar 0.3-0.6 sn arasindaydi; varsayilan 0.4.
    const jSn = sh.j_cut ? sayi(sh.j_cut_sn, 0.4) : 0;
    const lSn = sh.l_cut ? sayi(sh.l_cut_sn, 0.4) : 0;
    const baslangic = Math.max(0, bas - Math.round(jSn * fps));
    const uzunluk = Math.max(1, (kareler[i] || 0) + Math.round((jSn + lSn) * fps));

    parcalar.push(
      <Sequence
        key={`ses-${sh.beat_id || i}`}
        from={baslangic}
        durationInFrames={uzunluk}
        layout="none"
      >
        <Audio
          src={medyaYolu(sh.ses)}
          // Sahne sesi ANLATIM sayilir: duck uygulanmaz, tam seviyede kalir
          volume={sayi(sh.ses_seviye, 1)}
          startFrom={Math.round(sayi(sh.ses_bas_sn, 0) * fps)}
        />
      </Sequence>,
    );
  });

  return <>{parcalar}</>;
};

/** Master anlatim + sahne sesleri + ambans + muzik (ducking'li). */
export const SesZamanCizelgesi: React.FC<{
  ayar?: SesAyari;
  sahneler: EditorSahne[];
  kareler: number[];
  toplamKare: number;
}> = ({ayar, sahneler, kareler, toplamKare}) => {
  const {fps} = useVideoConfig();
  const sahneSesiVar = sahneler.some((s) => s.ses);
  if (!ayar?.anlatim && !ayar?.muzik && !(ayar?.ambans || []).length && !sahneSesiVar) {
    return null;
  }

  const verilen: number[][] = (ayar?.anlatim_araliklari || []).map((a) => dizi(a));
  // Aralik verilmemisse: master anlatim varsa TUM video, yoksa sahne sesleri
  const etkinAraliklar =
    verilen.length > 0
      ? verilen
      : ayar?.anlatim
        ? [[0, toplamKare / fps]]
        : sahneAraliklari(sahneler, kareler, fps);

  const ambansDip = sayi(ayar?.ducking?.ambans, DUCK.ambans);
  const muzikDip = sayi(ayar?.ducking?.muzik, DUCK.muzik);

  return (
    <>
      {ayar?.anlatim ? (
        <Audio
          src={medyaYolu(ayar.anlatim)}
          volume={sayi(ayar.anlatim_seviye, 1)}
          startFrom={Math.round(sayi(ayar.anlatim_bas_sn, 0) * fps)}
        />
      ) : null}

      <SahneSesleri sahneler={sahneler} kareler={kareler} />

      {(ayar?.ambans || []).map((a, i) => (
        <Audio
          key={`amb${i}`}
          src={medyaYolu(a)}
          loop
          volume={(f) =>
            sayi(ayar?.ambans_seviye, 0.5) * duckCarpani(f, fps, etkinAraliklar, ambansDip)
          }
        />
      ))}

      {ayar?.muzik ? (
        <Audio
          src={medyaYolu(ayar.muzik)}
          loop
          volume={(f) =>
            sayi(ayar?.muzik_seviye, 0.4) * duckCarpani(f, fps, etkinAraliklar, muzikDip)
          }
        />
      ) : null}
    </>
  );
};
