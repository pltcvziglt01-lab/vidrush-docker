/**
 * GRAFIK ve TIPOGRAFI KATMANLARI.
 *
 * Tasarim kurallari (Faz C profil token'lari):
 *  - EN FAZLA 2 font ailesi / 3 agirlik
 *  - Yazi ZEMINE GUVENMEZ: her bilgi yazisi kontrast bandi tasir
 *    (11 Agu: beyaz yazi aydinlik koridor duvarinda kayboldu)
 *  - Sol hizali sabit izgara (x=100), yayin guvenli alani 64px
 *  - Giris animasyonu 0.28 sn (referans: %98 tam olusmus yakalandi)
 *  - Bolum basligi ORTADA DEGIL alt-uclude (ortali baslik yuzun ustune denk
 *    geliyordu ve hem okunmuyor hem goruntuyu kapatiyordu)
 */
import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';

import {kameraDurumu} from './Kamera';
import type {MotionSpec} from './sozlesme';
import {FONT, IZGARA_X, RENK, dizi, ilerleme, metin, popIn, sayi, zarf} from './temel';

const bantStil = (opaklik: number): React.CSSProperties => ({
  background: `rgba(0,0,0,${opaklik})`,
  backdropFilter: 'blur(2px)',
  WebkitBackdropFilter: 'blur(2px)',
});

/** Bantin soldan saga acilmasi — AE'deki "box reveal". */
const bantGenislik = (t: number): string => `${Math.max(0, Math.min(1, t)) * 100}%`;

export const BolumBasligi: React.FC<{spec: MotionSpec; fps: number}> = ({spec, fps}) => {
  const frame = useCurrentFrame();
  const {height, width} = useVideoConfig();
  const bas = sayi(spec.bas_sn, 0.2);
  const sure = sayi(spec.sure_sn, 5);
  const op = zarf(frame, fps, bas, sure, 0.24, 0.3);
  if (op <= 0) return null;
  const t = ilerleme(frame, bas * fps, 0.28 * fps, spec);
  const puntoTaban = sayi(spec.parametre.punto, 60);
  const yOrani = sayi(spec.parametre.y_orani, 0.7);
  const dolgu = Math.round(puntoTaban * 0.42);
  const yaziT = ilerleme(frame, (bas + 0.12) * fps, 0.28 * fps, spec);

  // ⚠ KIRPMA YERINE KUCULT. Bant `overflow: hidden` + `nowrap` oldugu icin
  // sigmayan baslik HARF ORTASINDAN KESILIYORDU ("...ELEPHANT ISLAN"). Python
  // tarafinda karakter siniri hesaplanmasina ragmen font metrigi TAHMIN oldugu
  // icin kesme yine olabiliyordu (20 sn render'da iki kez goruldu).
  // Cozum tahmine guvenmemek: metin sigmiyorsa punto ORANLA kucultulur, boylece
  // harf ASLA kesilmez. En fazla %30 kuculur; altina inmek okunurlugu bozar.
  const yaziMetni = metin(spec.parametre.metin).toUpperCase();
  const kullanilabilir = width * 0.84 - dolgu * 2.4;
  // BUYUK HARF Montserrat Bold ~0.72em (muhafazakar; azimsamak kirpar).
  // ⚠ I-15: `letterSpacing` (asagida 0.01em) bu hesaba KATILMIYORDU. Yani
  // bant "sigar" dedigi halde cizim harf araligi kadar tasip son harfi
  // `overflow: hidden` ile kesiyordu (I-14'te olculdu: 1920'de 10.9px tasma).
  // Aralik artik sayiliyor; plan tarafi da ayni sabiti kullaniyor
  // (`kalite_kapisi.HARF_ARALIGI_EM`).
  const tahminiGenislik = Math.max(1, yaziMetni.length * puntoTaban * (0.72 + 0.01));
  const olcek = Math.max(0.7, Math.min(1, kullanilabilir / tahminiGenislik));
  const punto = Math.round(puntoTaban * olcek);
  return (
    <AbsoluteFill style={{pointerEvents: 'none', opacity: op}}>
      <div
        style={{
          position: 'absolute',
          left: IZGARA_X - dolgu,
          top: yOrani * height - dolgu,
          padding: `${dolgu}px ${dolgu * 1.2}px`,
          width: bantGenislik(t),
          maxWidth: '84%',
          overflow: 'hidden',
          whiteSpace: 'nowrap',
          ...bantStil(sayi(spec.parametre.bant_opaklik, 0.62)),
        }}
      >
        <span
          style={{
            fontFamily: FONT.aile,
            fontWeight: FONT.kalin,
            fontSize: punto,
            letterSpacing: '0.01em',
            color: RENK.yazi,
            opacity: yaziT,
            display: 'inline-block',
            transform: `translateY(${(1 - yaziT) * 8}px)`,
          }}
        >
          {metin(spec.parametre.metin).toUpperCase()}
        </span>
      </div>
    </AbsoluteFill>
  );
};

export const AltBand: React.FC<{spec: MotionSpec; fps: number}> = ({spec, fps}) => {
  const frame = useCurrentFrame();
  const {height} = useVideoConfig();
  const bas = sayi(spec.bas_sn, 0.3);
  const sure = Math.min(4.7, sayi(spec.sure_sn, 4));
  const op = zarf(frame, fps, bas, sure, 0.28, 0.28);
  if (op <= 0) return null;
  const t = ilerleme(frame, bas * fps, 0.28 * fps, spec);
  const punto = sayi(spec.parametre.punto, 42);
  const altPunto = sayi(spec.parametre.alt_punto, 25);
  const yOrani = sayi(spec.parametre.y_orani, 0.78);
  const dolgu = Math.round(punto * 0.42);
  const alt = metin(spec.parametre.alt);
  const yaziT = ilerleme(frame, (bas + 0.1) * fps, 0.26 * fps, spec);
  return (
    <AbsoluteFill style={{pointerEvents: 'none', opacity: op}}>
      <div style={{position: 'absolute', left: IZGARA_X, top: yOrani * height - dolgu, display: 'flex'}}>
        {/* Sari vurgu cubugu — bantla ayni anda acilir */}
        <div
          style={{
            width: 6,
            background: RENK.vurgu,
            transform: `scaleY(${Math.min(1, t * 1.4)})`,
            transformOrigin: 'top',
          }}
        />
        <div
          style={{
            padding: `${dolgu}px ${dolgu * 1.1}px`,
            width: bantGenislik(t),
            maxWidth: 900,
            overflow: 'hidden',
            whiteSpace: 'nowrap',
            ...bantStil(0.62),
          }}
        >
          <div
            style={{
              fontFamily: FONT.aile,
              fontWeight: FONT.kalin,
              fontSize: punto,
              color: RENK.yazi,
              lineHeight: 1.1,
              opacity: yaziT,
              transform: `translateX(${(1 - yaziT) * -10}px)`,
            }}
          >
            {metin(spec.parametre.baslik)}
          </div>
          {alt ? (
            <div
              style={{
                fontFamily: FONT.aile,
                fontWeight: FONT.orta,
                fontSize: altPunto,
                color: RENK.yazi,
                opacity: 0.86 * yaziT,
                letterSpacing: '0.06em',
                marginTop: 6,
                transform: `translateX(${(1 - yaziT) * -6}px)`,
              }}
            >
              {alt.toUpperCase()}
            </div>
          ) : null}
        </div>
      </div>
    </AbsoluteFill>
  );
};

/** Kunye — bant TASIMAZ (bilgi degil kaynak notu), kontur+golge ile okunur. */
export const KaynakEtiketi: React.FC<{spec: MotionSpec; fps: number}> = ({spec, fps}) => {
  const frame = useCurrentFrame();
  const bas = sayi(spec.bas_sn, 0.4);
  const sure = Math.min(3.0, sayi(spec.sure_sn, 3));
  const op = zarf(frame, fps, bas, sure, 0.3, 0.3);
  if (op <= 0) return null;
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      <div
        style={{
          position: 'absolute',
          right: 26,
          bottom: 22,
          fontFamily: FONT.aile,
          fontWeight: FONT.orta,
          fontSize: sayi(spec.parametre.punto, 21),
          color: RENK.yazi,
          opacity: 0.62 * op,
          textShadow: '0 1px 3px rgba(0,0,0,0.75), 0 0 1px rgba(0,0,0,0.9)',
          letterSpacing: '0.04em',
        }}
      >
        {metin(spec.parametre.metin)}
      </div>
    </AbsoluteFill>
  );
};

/** Callout — nokta + cizgi + kisa etiket. Olculen omur 1.8 sn. */
export const Callout: React.FC<{spec: MotionSpec; fps: number}> = ({spec, fps}) => {
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  const bas = sayi(spec.bas_sn, 0.4);
  const sure = Math.min(1.8, sayi(spec.sure_sn, 1.8));
  const op = zarf(frame, fps, bas, sure, 0.2, 0.24);
  if (op <= 0) return null;
  const pop = popIn(frame, fps, bas);
  const x = sayi(spec.parametre.x, 0.6) * width;
  const y = sayi(spec.parametre.y, 0.42) * height;
  const saga = x < width / 2;
  const cizgi = 92 * Math.min(1, pop);
  return (
    <AbsoluteFill style={{pointerEvents: 'none', opacity: op}}>
      {/* Nokta: koyu halka + beyaz merkez (acik zeminde kaybolmasin) */}
      <div
        style={{
          position: 'absolute',
          left: x - 8,
          top: y - 8,
          width: 16,
          height: 16,
          borderRadius: 8,
          background: RENK.yazi,
          boxShadow: '0 0 0 3px rgba(0,0,0,0.55)',
          transform: `scale(${Math.min(1.2, pop)})`,
        }}
      />
      <div
        style={{
          position: 'absolute',
          left: saga ? x + 8 : x - 8 - cizgi,
          top: y - 1,
          width: cizgi,
          height: 2,
          background: RENK.vurgu,
          opacity: 0.9,
        }}
      />
      <div
        style={{
          position: 'absolute',
          left: saga ? x + 8 + cizgi + 8 : undefined,
          right: saga ? undefined : width - (x - 8 - cizgi) + 8,
          top: y - 20,
          padding: '6px 12px',
          fontFamily: FONT.aile,
          fontWeight: FONT.kalin,
          fontSize: sayi(spec.parametre.punto, 30),
          color: RENK.yazi,
          whiteSpace: 'nowrap',
          opacity: Math.min(1, pop),
          ...bantStil(0.62),
        }}
      >
        {metin(spec.parametre.metin)}
      </div>
    </AbsoluteFill>
  );
};

/** Alinti karti — atifli, HABER EKRAN GORUNTUSU TAKLIDI DEGIL. */
export const AlintiKarti: React.FC<{spec: MotionSpec; fps: number}> = ({spec, fps}) => {
  const frame = useCurrentFrame();
  const bas = sayi(spec.bas_sn, 0.3);
  const sure = sayi(spec.sure_sn, 5);
  const op = zarf(frame, fps, bas, sure, 0.3, 0.3);
  if (op <= 0) return null;
  const t = ilerleme(frame, bas * fps, 0.34 * fps, spec);
  return (
    <AbsoluteFill style={{pointerEvents: 'none', opacity: op}}>
      <div
        style={{
          position: 'absolute',
          left: IZGARA_X,
          top: '34%',
          maxWidth: '62%',
          padding: '28px 32px',
          borderLeft: `4px solid ${RENK.vurgu}`,
          transform: `translateX(${(1 - t) * -14}px)`,
          ...bantStil(0.66),
        }}
      >
        <div
          style={{
            fontFamily: FONT.aile,
            fontWeight: FONT.orta,
            fontSize: 40,
            lineHeight: 1.34,
            color: RENK.yazi,
            fontStyle: 'italic',
          }}
        >
          “{metin(spec.parametre.alinti)}”
        </div>
        <div
          style={{
            marginTop: 16,
            fontFamily: FONT.aile,
            fontWeight: FONT.kalin,
            fontSize: 22,
            letterSpacing: '0.08em',
            color: RENK.vurgu,
            opacity: 0.9,
          }}
        >
          {metin(spec.parametre.kaynak).toUpperCase()}
        </div>
      </div>
    </AbsoluteFill>
  );
};

/** BELGE VURGUSU — disi karartilir, ilgili bolgeye punch-in. */
export const BelgeVurgusu: React.FC<{spec: MotionSpec; fps: number}> = ({spec, fps}) => {
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  const bas = sayi(spec.bas_sn, 0);
  const sure = sayi(spec.sure_sn, 4);
  const op = zarf(frame, fps, bas, sure, 0.35, 0.3);
  if (op <= 0) return null;
  const b = dizi(spec.parametre.bolge);
  const [bx, by, bw, bh] = [b[0] ?? 0.3, b[1] ?? 0.3, b[2] ?? 0.4, b[3] ?? 0.22];
  const t = ilerleme(frame, bas * fps, 0.6 * fps, spec);
  const karartma = sayi(spec.parametre.karartma_disi, 0.45) * t;
  const kalinlik = sayi(spec.parametre.kenar_kalinlik, 3);
  const x = bx * width;
  const y = by * height;
  const w = bw * width;
  const h = bh * height;
  return (
    <AbsoluteFill style={{pointerEvents: 'none', opacity: op}}>
      {/* Disi karart: dort dikdortgen (clip-path'ten daha guvenli) */}
      <div style={{position: 'absolute', left: 0, top: 0, right: 0, height: y, background: `rgba(0,0,0,${karartma})`}} />
      <div style={{position: 'absolute', left: 0, top: y + h, right: 0, bottom: 0, background: `rgba(0,0,0,${karartma})`}} />
      <div style={{position: 'absolute', left: 0, top: y, width: x, height: h, background: `rgba(0,0,0,${karartma})`}} />
      <div style={{position: 'absolute', left: x + w, top: y, right: 0, height: h, background: `rgba(0,0,0,${karartma})`}} />
      {/* Cerceve + kose isaretleri (AE callout hissi) */}
      <div
        style={{
          position: 'absolute',
          left: x,
          top: y,
          width: w,
          height: h,
          border: `${kalinlik}px solid ${RENK.vurgu}`,
          boxShadow: '0 0 0 1px rgba(0,0,0,0.6)',
          transform: `scale(${interpolate(t, [0, 1], [1.04, 1])})`,
        }}
      />
      {[
        [x - 2, y - 2],
        [x + w - 14, y - 2],
        [x - 2, y + h - 14],
        [x + w - 14, y + h - 14],
      ].map(([cx, cy], i) => (
        <div
          key={i}
          style={{
            position: 'absolute',
            left: cx,
            top: cy,
            width: 16,
            height: 16,
            borderTop: i < 2 ? `3px solid ${RENK.yazi}` : undefined,
            borderBottom: i >= 2 ? `3px solid ${RENK.yazi}` : undefined,
            borderLeft: i % 2 === 0 ? `3px solid ${RENK.yazi}` : undefined,
            borderRight: i % 2 === 1 ? `3px solid ${RENK.yazi}` : undefined,
            opacity: t,
          }}
        />
      ))}
    </AbsoluteFill>
  );
};

/**
 * HARITA + ROTA (pseudo). Gercek GeoJSON YOK — stilize izgara + rota cizimi.
 * Destek matrisi bunu `pseudo` beyan ediyor: konum SEMBOLIK.
 */
export const HaritaRota: React.FC<{spec: MotionSpec; fps: number}> = ({spec, fps}) => {
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  const bas = sayi(spec.bas_sn, 0);
  const sure = sayi(spec.sure_sn, 4);
  const op = zarf(frame, fps, bas, sure, 0.4, 0.4);
  if (op <= 0) return null;
  const cizimSn = sayi(spec.parametre.cizim_sn, Math.max(1, sure * 0.55));
  const t = ilerleme(frame, bas * fps, cizimSn * fps, spec);
  const yer = metin(spec.parametre.yer, '—');
  const zoom = interpolate(ilerleme(frame, bas * fps, sure * fps, spec), [0, 1], [1, sayi(spec.parametre.zoom_hedefi, 1.4)]);
  // Deterministik "kara kutlesi" poligonu
  const kara = 'M 120 520 L 300 360 L 520 400 L 700 300 L 860 380 L 1010 300 L 1180 420 L 1280 380 L 1400 460 L 1500 420 L 1620 520 L 1700 620 L 1500 760 L 1200 820 L 900 780 L 640 840 L 380 760 L 200 660 Z';
  const rota = 'M 420 700 C 620 620, 780 660, 940 560 S 1240 520, 1380 600';
  const uzunluk = 1400;
  return (
    <AbsoluteFill style={{opacity: op, pointerEvents: 'none'}}>
      <AbsoluteFill style={{background: RENK.haritaSu}} />
      <svg
        width={width}
        height={height}
        viewBox="0 0 1920 1080"
        style={{position: 'absolute', inset: 0, transform: `scale(${zoom.toFixed(3)})`, transformOrigin: '52% 58%'}}
      >
        {/* Izgara */}
        {Array.from({length: 14}).map((_, i) => (
          <line key={`h${i}`} x1={0} y1={i * 80} x2={1920} y2={i * 80} stroke="#243040" strokeWidth={1} opacity={0.35} />
        ))}
        {Array.from({length: 24}).map((_, i) => (
          <line key={`v${i}`} x1={i * 80} y1={0} x2={i * 80} y2={1080} stroke="#243040" strokeWidth={1} opacity={0.35} />
        ))}
        <path d={kara} fill={RENK.haritaKara} stroke="#2E3A46" strokeWidth={2} />
        {/* Rota: strokeDashoffset ile cizilir (AE trim paths karsiligi) */}
        <path
          d={rota}
          fill="none"
          stroke={RENK.vurgu}
          strokeWidth={5}
          strokeLinecap="round"
          strokeDasharray={uzunluk}
          strokeDashoffset={uzunluk * (1 - t)}
          opacity={0.95}
        />
        {/* Keypoint */}
        <circle cx={1380} cy={600} r={10 + 6 * Math.max(0, Math.sin(frame / 8))} fill={RENK.vurgu} opacity={t} />
        <circle cx={1380} cy={600} r={22} fill="none" stroke={RENK.vurgu} strokeWidth={2} opacity={t * 0.5} />
      </svg>
      <div
        style={{
          position: 'absolute',
          left: IZGARA_X,
          top: '18%',
          padding: '14px 20px',
          fontFamily: FONT.aile,
          fontWeight: FONT.kalin,
          fontSize: 44,
          color: RENK.yazi,
          letterSpacing: '0.02em',
          ...bantStil(0.6),
        }}
      >
        {yer.toUpperCase()}
      </div>
      <div
        style={{
          position: 'absolute',
          left: IZGARA_X,
          top: '18%',
          marginTop: 78,
          fontFamily: FONT.aile,
          fontWeight: FONT.normal,
          fontSize: 18,
          color: RENK.yazi,
          opacity: 0.5,
        }}
      >
        SEMBOLIK HARITA — COGRAFI OLCEK DEGIL
      </div>
    </AbsoluteFill>
  );
};

/** VERI GRAFIGI — cubuk + sayac animasyonu (AE'deki number counter). */
export const VeriGrafigi: React.FC<{spec: MotionSpec; fps: number}> = ({spec, fps}) => {
  const frame = useCurrentFrame();
  const {height} = useVideoConfig();
  const bas = sayi(spec.bas_sn, 0);
  const sure = sayi(spec.sure_sn, 4);
  const op = zarf(frame, fps, bas, sure, 0.35, 0.35);
  if (op <= 0) return null;
  const degerler = dizi(spec.parametre.degerler);
  // ⚠ SAYI UYDURMA YASAK. Onceki surum bos veride `[1]` variyordu; ekranda
  // kocaman anlamsiz bir "1" ve tek sari cubuk cikiyordu (20 sn render
  // smoke'unun 19. saniyesinde goruldu). Veri yoksa BU KATMAN CIZILMEZ —
  // plan tarafi zaten bolum kartina duser (plan.py `_beat_sayilari`).
  if (!degerler.length) return null;
  const veri = degerler;
  const enBuyuk = Math.max(...veri, 1);
  const cizimSn = sayi(spec.parametre.cizim_sn, Math.max(0.8, sure * 0.5));
  const t = ilerleme(frame, bas * fps, cizimSn * fps, spec);
  const sayacDeger = Math.round(veri[0] * t);
  // Cizim bittikten sonra kare DONMASIN: harita gibi tum sure boyunca yavas
  // hareket. (11 Agu: veri sahnesi 20.0'da donmus blok verdi.)
  //
  // ⚠ IKINCI OLCUM (Faz E): %2 sabit sürüklenme UZUN sahnede yetmedi —
  // 6.1 sn'lik tek cubuklu grafik 43.6'da yine donmus blok verdi (%0.33/sn,
  // freezedetect esiginin altinda). Suruklenme artik SUREYE BAGLI: uzun sahne
  // daha cok hareket alir, boylece hiz (%/sn) sabit kalir.
  const surukle = ilerleme(frame, bas * fps, sure * fps, spec);
  const oran = Math.max(0.03, Math.min(0.075, 0.011 * sure));
  const tamOlcek = 1 + oran * surukle;
  const kayY = -oran * 120 * surukle;
  return (
    <AbsoluteFill
      style={{
        opacity: op,
        pointerEvents: 'none',
        transform: `scale(${tamOlcek}) translateY(${kayY}px)`,
        transformOrigin: '30% 50%',
      }}
    >
      <AbsoluteFill style={{background: 'linear-gradient(160deg, #0C0F13 0%, #141A21 100%)'}} />
      <div style={{position: 'absolute', left: IZGARA_X, top: '22%'}}>
        <div
          style={{
            fontFamily: FONT.aile,
            fontWeight: FONT.orta,
            fontSize: 24,
            letterSpacing: '0.14em',
            color: RENK.vurgu,
            opacity: 0.85,
          }}
        >
          {metin(spec.parametre.baslik).toUpperCase()}
        </div>
        <div
          style={{
            fontFamily: FONT.aile,
            fontWeight: FONT.kalin,
            fontSize: 132,
            lineHeight: 1.02,
            color: RENK.yazi,
            marginTop: 8,
            fontVariantNumeric: 'tabular-nums',
          }}
        >
          {sayacDeger.toLocaleString('en-US')}
        </div>
      </div>
      {/* Cubuklar */}
      <div
        style={{
          position: 'absolute',
          left: IZGARA_X,
          bottom: height * 0.16,
          display: 'flex',
          alignItems: 'flex-end',
          gap: 22,
          height: height * 0.3,
        }}
      >
        {veri.slice(0, 6).map((d, i) => {
          const gecikme = i * 0.1;
          const ti = Math.max(0, Math.min(1, (t - gecikme) / Math.max(0.01, 1 - gecikme)));
          return (
            <div
              key={i}
              style={{
                width: 84,
                // Cizim bitince nefes: deterministik (frame tabanli), her
                // cubuk farkli fazda ki mekanik gorunmesin
                height: `${(d / enBuyuk) * 100 * ti *
                  (1 + 0.02 * Math.sin(frame / 17 + i * 1.3))}%`,
                background: i === 0 ? RENK.veriCubuk : 'rgba(245,225,75,0.35)',
                borderTop: `3px solid ${RENK.vurgu}`,
              }}
            />
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

/**
 * KINETIK BASLIK — kelime kelime giren buyuk baslik.
 *
 * `motion.py` bunu REMOTION_ZORUNLU icinde beyan ediyordu ama ne ureticisi ne
 * render bileseni vardi (11 Agu, test_faz_d yakaladi). Beyan edilen bir spec'in
 * karsiligi olmamasi, Faz C'de yakalanan "premium beyan var, piksel yok"
 * hatasinin aynisi — o yuzden matrise `desteklenmiyor` yazmak yerine kodlandi.
 *
 * ffmpeg'de yapilamaz: drawtext kelime basina ayri filtre + ayri zamanlama
 * ister, kelime genisligi onceden bilinmedigi icin hizalama kayar.
 */
export const KinetikBaslik: React.FC<{spec: MotionSpec; fps: number}> = ({spec, fps}) => {
  const frame = useCurrentFrame();
  const {height} = useVideoConfig();
  const bas = sayi(spec.bas_sn, 0.2);
  const sure = sayi(spec.sure_sn, 4);
  const op = zarf(frame, fps, bas, sure, 0.2, 0.3);
  if (op <= 0) return null;

  const punto = sayi(spec.parametre.punto, 72);
  const yOrani = sayi(spec.parametre.y_orani, 0.62);
  // Kelime basina gecikme: 0.09 sn. Referans olcumunde kinetik basliklarin
  // tamami 0.6 sn icinde tam okunur hale geliyordu; 8 kelimeden fazlasi
  // gecikmeyi sikistirir ki baslik yarisi bos kalmasin.
  const kelimeler = metin(spec.parametre.metin, '').split(/\s+/).filter(Boolean);
  const adim = kelimeler.length > 8 ? 0.6 / kelimeler.length : 0.09;
  const dolgu = Math.round(punto * 0.34);

  return (
    <AbsoluteFill style={{pointerEvents: 'none', opacity: op}}>
      <div
        style={{
          position: 'absolute',
          left: IZGARA_X - dolgu,
          top: yOrani * height - dolgu,
          maxWidth: '80%',
          padding: `${dolgu}px ${dolgu * 1.1}px`,
          display: 'flex',
          flexWrap: 'wrap',
          gap: `0 ${Math.round(punto * 0.26)}px`,
          ...bantStil(sayi(spec.parametre.bant_opaklik, 0.55)),
        }}
      >
        {kelimeler.map((k, i) => {
          const kt = ilerleme(frame, (bas + i * adim) * fps, 0.26 * fps, spec);
          return (
            <span
              key={i}
              style={{
                fontFamily: FONT.aile,
                fontWeight: FONT.kalin,
                fontSize: punto,
                lineHeight: 1.06,
                letterSpacing: '0.01em',
                color: i === 0 ? RENK.vurgu : RENK.yazi,
                opacity: kt,
                display: 'inline-block',
                // Asagidan yukari + hafif olcek: AE'deki klasik kinetik giris
                transform: `translateY(${(1 - kt) * punto * 0.22}px) scale(${0.94 + kt * 0.06})`,
              }}
            >
              {k.toUpperCase()}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

/**
 * SAHNE ICI YAZI (text-in-video) — yaziyi kamerayla BIRLIKTE hareket ettirir.
 *
 * Fark: `lower-third` ekrana sabitlenir, bu ise zemine "yapisir" — push-in
 * yapildikca yazi da buyur/kayar, boylece goruntunun icinde duruyormus gibi
 * durur. Kamera transformunu `Kamera.kameraDurumu()` ile PAYLASIR ki zeminle
 * birebir ayni hareket etsin (ayri hesap yapsam kayma olur).
 */
export const SahneYazisi: React.FC<{
  spec: MotionSpec;
  kameraSpec: MotionSpec | null;
  /** Zeminle AYNI kadrajla hesaplanmali; farkli olursa yazi zeminden kayar. */
  kadraj: string;
  sureKare: number;
  fps: number;
}> = ({spec, kameraSpec, kadraj, sureKare, fps}) => {
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  const bas = sayi(spec.bas_sn, 0.2);
  const sure = sayi(spec.sure_sn, 3);
  const op = zarf(frame, fps, bas, sure, 0.24, 0.3);
  if (op <= 0) return null;

  const kd = kameraDurumu(kameraSpec, kadraj, frame, sureKare);
  const punto = sayi(spec.parametre.punto, 44);
  const x = sayi(spec.parametre.x_orani, 0.5) * width;
  const y = sayi(spec.parametre.y_orani, 0.42) * height;
  const t = ilerleme(frame, bas * fps, 0.3 * fps, spec);

  return (
    <AbsoluteFill style={{pointerEvents: 'none', opacity: op}}>
      <div
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width,
          height,
          // Zeminin transformunu AYNEN uygula: yazi goruntuye kilitli kalir
          transform: `scale(${kd.olcek}) translate(${kd.x}px, ${kd.y}px)`,
          transformOrigin: 'center center',
        }}
      >
        <div
          style={{
            position: 'absolute',
            left: x,
            top: y,
            transform: `translate(-50%,-50%) scale(${0.96 + t * 0.04})`,
            padding: '10px 18px',
            opacity: t,
            ...bantStil(sayi(spec.parametre.bant_opaklik, 0.5)),
          }}
        >
          <span
            style={{
              fontFamily: FONT.aile,
              fontWeight: FONT.kalin,
              fontSize: punto,
              letterSpacing: '0.03em',
              color: RENK.yazi,
              whiteSpace: 'nowrap',
            }}
          >
            {metin(spec.parametre.metin).toUpperCase()}
          </span>
        </div>
      </div>
    </AbsoluteFill>
  );
};
