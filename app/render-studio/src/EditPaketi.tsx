/**
 * EDIT PAKETI — referans #13 (@Neu, "The Broken Economics of Oil Tankers") edit dili.
 *
 * NEDEN AYRI DOSYA: bu bir GECIS meselesi degil, ayri bir anlatim katmani. Referans
 * videoda 10 dakikada sadece 2 sert kesme var (ffmpeg sahne-kesme ile olculdu) — video
 * kesmeyle degil SUREKLI ANIMASYONLA ilerliyor. Kare olcumu:
 *   %41 beyaz tuval (grafik/etiket/metin)  |  %43 tam kare footage  |  %16 karisik
 * Yani stilin yarisi, bizde hic olmayan bir sey: beyaz zeminde veri grafigi.
 *
 * BU DOSYADAKI SABLONLAR
 *   beyaz-tuval : beyaz zemin + yalitilmis konu gorseli + isaretlenmis etiketler
 *   olcu        : iki nokta arasi olcu oku + etiket ("375 METERS")
 *   alinti      : kaynak alinti karti (serif govde + isaretli baslik + KAYNAK ADI)
 *   metin       : beyaz zeminde serif metin blogu, satir satir aciliyor
 *   harita      : harita gorseli + animasyonlu daire/rota isareti
 *
 * ONEMLI — SAHTE EKRAN GORUNTUSU URETMIYORUZ. Referansta gerçek gazete/makale ekran
 * goruntuleri var. Onun taklidini uretmek, olmayan bir habere gercek gibi gorunen bir
 * gorsel uretmek olur. Bunun yerine "alinti" sablonu acikca ALINTI KARTI gibi durur ve
 * kaynagi yazar; ayni gorsel etkiyi verir, uydurma belge uretmez.
 *
 * KOORDINATLAR 0-1 ARASI ORANDIR (kare boyutundan bagimsiz).
 */
import React from 'react';
import {AbsoluteFill, Easing, Img, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {fontAilesi} from './fontlar';

const SERIF = 'Georgia, "Times New Roman", "Liberation Serif", serif';

/** Referanstan olculen isaretleyici sarisi ve baslik turuncusu. */
const VURGU_SARI = '#F5E14B';
const VURGU_TURUNCU = '#E8873A';
const MUREKKEP = '#141414';

export type GrafikEtiket = {
  metin: string;
  x: number;          // 0-1
  y: number;          // 0-1
  vurgu?: boolean;    // arkasina isaretleyici cizgisi
  buyuk?: boolean;
};

export type Grafik =
  | {tur: 'beyaz-tuval'; etiketler?: GrafikEtiket[]}
  | {tur: 'olcu'; metin: string; x1: number; y1: number; x2: number; y2: number}
  | {tur: 'alinti'; baslik?: string; metin: string; kaynak: string}
  | {tur: 'metin'; satirlar: string[]}
  | {tur: 'harita'; noktalar?: GrafikEtiket[]; rota?: boolean};

/** Sablon beyaz zemin mi istiyor (gorselin ustune mi ciziliyor)? */
export const beyazZeminMi = (g?: Grafik): boolean =>
  !!g && (g.tur === 'beyaz-tuval' || g.tur === 'alinti' || g.tur === 'metin');

/* ─────────────────────── ortak yardimcilar ─────────────────────── */

/** 0 -> 1 yumusak giris; gecikme kare cinsinden. */
const gir = (frame: number, fps: number, gecikme = 0, sn = 0.55) =>
  interpolate(frame, [gecikme, gecikme + Math.round(fps * sn)], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });

/** Sahne sonunda blok halinde sonum (gecisle catismasin diye kisa). */
const cikisSonum = (frame: number, K: number, fps: number) =>
  interpolate(frame, [K - Math.round(fps * 0.45), K], [1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

/* ─────────────────────── isaretleyici (highlighter) ─────────────────────── */

/**
 * Referanstaki sari isaretleyici. Yazinin ARKASINA soldan saga buyuyen bir bant cizer —
 * gercek bir fosforlu kalem gibi. CSS background-size animasyonu yerine ayri katman:
 * yazinin genisligini bilmeden de dogru calisir.
 */
const Isaretleyici: React.FC<{ilerleme: number; renk?: string}> = ({ilerleme, renk = VURGU_SARI}) => (
  <span
    style={{
      position: 'absolute',
      left: -6,
      right: -6,
      bottom: '0.08em',
      height: '0.62em',
      backgroundColor: renk,
      transformOrigin: 'left center',
      transform: `scaleX(${ilerleme})`,
      zIndex: 0,
      borderRadius: 2,
    }}
  />
);

const Etiket: React.FC<{e: GrafikEtiket; frame: number; fps: number; gecikme: number}> = ({
  e,
  frame,
  fps,
  gecikme,
}) => {
  const p = gir(frame, fps, gecikme, 0.4);
  const isaret = gir(frame, fps, gecikme + Math.round(fps * 0.28), 0.45);
  return (
    <div
      style={{
        position: 'absolute',
        left: `${e.x * 100}%`,
        top: `${e.y * 100}%`,
        transform: `translate(-50%, -50%) translateY(${(1 - p) * 14}px)`,
        opacity: p,
        fontFamily: SERIF,
        fontWeight: 700,
        fontSize: e.buyuk ? 54 : 38,
        color: MUREKKEP,
        whiteSpace: 'nowrap',
      }}
    >
      <span style={{position: 'relative', display: 'inline-block'}}>
        {e.vurgu !== false ? <Isaretleyici ilerleme={isaret} /> : null}
        <span style={{position: 'relative', zIndex: 1}}>{e.metin}</span>
      </span>
    </div>
  );
};

/* ─────────────────────── olcu oku ─────────────────────── */

/**
 * Iki nokta arasi olcu oku: cizgi soldan saga cizilir, iki ucta dik serif, ortada etiket.
 * Referansta gemi boyunu gosteren "375 METERS" oku bu.
 */
const OlcuOku: React.FC<{g: Extract<Grafik, {tur: 'olcu'}>; frame: number; fps: number}> = ({
  g,
  frame,
  fps,
}) => {
  const {width: W, height: H} = useVideoConfig();
  const p = gir(frame, fps, Math.round(fps * 0.2), 0.7);
  const x1 = g.x1 * W;
  const y1 = g.y1 * H;
  const x2 = g.x2 * W;
  const y2 = g.y2 * H;
  const ux = x1 + (x2 - x1) * p;
  const uy = y1 + (y2 - y1) * p;
  const aci = Math.atan2(y2 - y1, x2 - x1);
  const dik = aci + Math.PI / 2;
  const u = 16;
  const serif = (cx: number, cy: number) => ({
    x1: cx + Math.cos(dik) * u,
    y1: cy + Math.sin(dik) * u,
    x2: cx - Math.cos(dik) * u,
    y2: cy - Math.sin(dik) * u,
  });
  const s1 = serif(x1, y1);
  const s2 = serif(x2, y2);
  return (
    <AbsoluteFill>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <line x1={x1} y1={y1} x2={ux} y2={uy} stroke={MUREKKEP} strokeWidth={3} />
        <line {...s1} stroke={MUREKKEP} strokeWidth={3} />
        {p > 0.985 ? <line {...s2} stroke={MUREKKEP} strokeWidth={3} /> : null}
      </svg>
      <Etiket
        e={{
          metin: g.metin,
          x: (g.x1 + g.x2) / 2,
          y: (g.y1 + g.y2) / 2 - 0.055,
          vurgu: true,
        }}
        frame={frame}
        fps={fps}
        gecikme={Math.round(fps * 0.75)}
      />
    </AbsoluteFill>
  );
};

/* ─────────────────────── alinti karti ─────────────────────── */

const AlintiKarti: React.FC<{g: Extract<Grafik, {tur: 'alinti'}>; frame: number; fps: number}> = ({
  g,
  frame,
  fps,
}) => {
  const p = gir(frame, fps, 0, 0.6);
  const isaret = gir(frame, fps, Math.round(fps * 0.5), 0.5);
  return (
    <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', padding: '7% 12%'}}>
      <div
        style={{
          opacity: p,
          transform: `translateY(${(1 - p) * 18}px)`,
          maxWidth: '86%',
          backgroundColor: '#FFFFFF',
          border: '1px solid #DCDCDC',
          boxShadow: '0 18px 60px rgba(0,0,0,0.10)',
          padding: '64px 78px',
        }}
      >
        {g.baslik ? (
          <div
            style={{
              fontFamily: SERIF,
              fontWeight: 700,
              fontSize: 46,
              lineHeight: 1.24,
              marginBottom: 32,
              color: MUREKKEP,
            }}
          >
            <span style={{position: 'relative', display: 'inline'}}>
              <Isaretleyici ilerleme={isaret} renk={VURGU_TURUNCU} />
              <span style={{position: 'relative', zIndex: 1}}>{g.baslik}</span>
            </span>
          </div>
        ) : null}
        <div
          style={{
            fontFamily: SERIF,
            fontSize: 34,
            lineHeight: 1.58,
            color: '#232323',
            textAlign: 'justify',
          }}
        >
          {g.metin}
        </div>
        <div
          style={{
            marginTop: 30,
            paddingTop: 18,
            borderTop: '1px solid #E4E4E4',
            fontFamily: fontAilesi('montserrat'),
            fontSize: 22,
            letterSpacing: 1.6,
            textTransform: 'uppercase',
            color: '#7A7A7A',
          }}
        >
          Kaynak: {g.kaynak}
        </div>
      </div>
    </AbsoluteFill>
  );
};

/* ─────────────────────── serif metin blogu ─────────────────────── */

const MetinBloku: React.FC<{g: Extract<Grafik, {tur: 'metin'}>; frame: number; fps: number}> = ({
  g,
  frame,
  fps,
}) => (
  <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', padding: '8% 14%'}}>
    <div style={{maxWidth: '80%'}}>
      {g.satirlar.map((satir, i) => {
        const p = gir(frame, fps, i * Math.round(fps * 0.22), 0.5);
        return (
          <div
            key={i}
            style={{
              opacity: p,
              transform: `translateY(${(1 - p) * 12}px)`,
              fontFamily: SERIF,
              fontSize: 40,
              lineHeight: 1.68,
              color: MUREKKEP,
              textAlign: 'center',
              marginBottom: 14,
            }}
          >
            {satir}
          </div>
        );
      })}
    </div>
  </AbsoluteFill>
);

/* ─────────────────────── harita isareti ─────────────────────── */

const HaritaIsareti: React.FC<{
  g: Extract<Grafik, {tur: 'harita'}>;
  frame: number;
  fps: number;
}> = ({g, frame, fps}) => {
  const {width: W, height: H} = useVideoConfig();
  const noktalar = g.noktalar || [];
  return (
    <AbsoluteFill>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        {g.rota && noktalar.length >= 2
          ? noktalar.slice(1).map((n, i) => {
              const a = noktalar[i];
              const p = gir(frame, fps, Math.round(fps * (0.6 + i * 0.5)), 0.8);
              return (
                <line
                  key={i}
                  x1={a.x * W}
                  y1={a.y * H}
                  x2={a.x * W + (n.x - a.x) * W * p}
                  y2={a.y * H + (n.y - a.y) * H * p}
                  stroke="#D03A2C"
                  strokeWidth={7}
                  strokeDasharray="20 14"
                />
              );
            })
          : null}
        {noktalar.map((n, i) => {
          const p = gir(frame, fps, Math.round(fps * (0.25 + i * 0.45)), 0.5);
          return (
            <circle
              key={i}
              cx={n.x * W}
              cy={n.y * H}
              r={44 * p}
              fill="none"
              stroke="#D03A2C"
              strokeWidth={7}
              opacity={p}
            />
          );
        })}
      </svg>
      {noktalar
        .filter((n) => n.metin)
        .map((n, i) => (
          <Etiket
            key={i}
            e={{...n, y: n.y - 0.085, vurgu: true}}   // daireyle cakismasin
            frame={frame}
            fps={fps}
            gecikme={Math.round(fps * (0.45 + i * 0.45))}
          />
        ))}
    </AbsoluteFill>
  );
};

/* ─────────────────────── beyaz tuval ─────────────────────── */

/**
 * Beyaz zeminde yalitilmis konu gorseli. Gorsel BEYAZ ZEMINLE uretilmis olmali
 * (prompt tarafi bunu soyluyor); burada sadece yerlestirilir ve hafifce olceklenir —
 * referansta nesne durur, kamera cok yavas yaklasir.
 */
const BeyazTuval: React.FC<{
  medya?: string;
  g: Extract<Grafik, {tur: 'beyaz-tuval'}>;
  frame: number;
  fps: number;
  K: number;
}> = ({medya, g, frame, fps, K}) => {
  const yay = spring({frame, fps, config: {damping: 24, stiffness: 90, mass: 0.9}});
  const olcek = 0.94 + 0.06 * yay + (frame / Math.max(1, K)) * 0.03;
  return (
    <AbsoluteFill style={{backgroundColor: '#FFFFFF'}}>
      {medya ? (
        <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
          {/* Sabit olculu kap + objectFit:contain. Sadece maxWidth/maxHeight vermek
              YETMIYOR: kaynak gorsel hedeften kucukse (or. 640 px'lik bir onizleme)
              max-* onu BUYUTMEZ ve nesne karenin ortasinda minicik kalir. Olculu kap
              her iki yonde de dogru boyutu garanti eder. */}
          <div
            style={{
              width: '74%',
              height: '70%',
              opacity: gir(frame, fps, 0, 0.5),
              transform: `scale(${olcek})`,
            }}
          >
            <Img
              src={medya}
              style={{width: '100%', height: '100%', objectFit: 'contain'}}
            />
          </div>
        </AbsoluteFill>
      ) : null}
      {(g.etiketler || []).map((e, i) => (
        <Etiket key={i} e={e} frame={frame} fps={fps} gecikme={Math.round(fps * (0.35 + i * 0.4))} />
      ))}
    </AbsoluteFill>
  );
};

/* ─────────────────────── SAHA ETIKETI + CERCEVE VURGUSU ─────────────────────── */

/**
 * OLCUM (7 Agu 2026, 20 referans video / 196 kare vision ile etiketlendi):
 *
 *   kanal          yazi var   baskın tur              grafik var  baskın
 *   NextGen          %57      kucuk etiket %50           %14      cerceve %7
 *   ZeroReports      %57      etiket %39, buyuk %11      %36      cerceve %18
 *   MadeVision       %46      kucuk etiket %43           %7
 *   NavyDecoded      %32                                 %29
 *   ECHOES           %29                                 %4
 *   Auralis          %25      etiket %18                 %7
 *   Atrium           %11                                 %25      cerceve %11, harita %7
 *   BEDOSAHO (biz)   %0       —                          %0       —
 *
 * En cok kullanilan teknik BUYUK BASLIK DEGIL, KUCUK ETIKET: bir yeri/nesneyi/kisiyi/
 * sayiyi karenin uzerine yazmak. En iyi kanallarda karelerin %39-50'sinde var, bizde %0'di.
 * Ikinci teknik: goruntunun bir bolgesini kutu/daire ile isaretlemek (%7-18).
 *
 * Ikisi de DETERMINISTIK grafik — ek AI maliyeti yok.
 */
export type SahaEtiketi = {
  metin: string;
  x: number;              // 0-1
  y: number;              // 0-1
  yon?: 'sol' | 'sag';    // cizgi hangi yone uzasin (varsayilan: x<0.5 ise sag)
  gecikme?: number;       // saniye
};

export type VurguKutu = {
  x: number;              // 0-1, sol
  y: number;              // 0-1, ust
  w: number;              // 0-1
  h: number;              // 0-1
  daire?: boolean;
  gecikme?: number;
};

/** Kucuk saha etiketi: nokta + kisa cizgi + BUYUK HARF kisa yazi. */
export const SahaEtiketleri: React.FC<{
  etiketler?: SahaEtiketi[];
  kareSayisi: number;
}> = ({etiketler, kareSayisi}) => {
  const frame = useCurrentFrame();
  const {fps, width: W, height: H} = useVideoConfig();
  if (!etiketler || !etiketler.length) return null;
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      {etiketler.slice(0, 3).map((e, i) => {
        const gec = Math.round(fps * (e.gecikme ?? 0.35 + i * 0.5));
        const p = interpolate(frame, [gec, gec + Math.round(fps * 0.42)], [0, 1], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
          easing: Easing.out(Easing.cubic),
        });
        const cik = interpolate(frame, [kareSayisi - Math.round(fps * 0.4), kareSayisi],
          [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
        const opak = p * cik;
        const saga = e.yon ? e.yon === 'sag' : e.x < 0.5;
        const cizgi = 78 * p;                    // cizgi soldan saga uzar
        const px = e.x * W;
        const py = e.y * H;
        return (
          <React.Fragment key={i}>
            <svg width={W} height={H} style={{position: 'absolute', inset: 0, opacity: opak}}>
              <circle cx={px} cy={py} r={7} fill="#FFFFFF" stroke="rgba(0,0,0,0.55)"
                      strokeWidth={2} />
              <line x1={px} y1={py} x2={px + (saga ? cizgi : -cizgi)} y2={py}
                    stroke="#FFFFFF" strokeWidth={3} strokeOpacity={0.95} />
            </svg>
            <div
              style={{
                position: 'absolute',
                left: saga ? px + cizgi + 14 : undefined,
                right: saga ? undefined : W - (px - cizgi) + 14,
                top: py,
                transform: `translateY(-50%) translateX(${(1 - p) * (saga ? -10 : 10)}px)`,
                opacity: opak,
                fontFamily: fontAilesi('montserrat'),
                fontWeight: 800,
                fontSize: 30,
                letterSpacing: 1.1,
                textTransform: 'uppercase',
                color: '#FFFFFF',
                whiteSpace: 'nowrap',
                textShadow: '0 2px 10px rgba(0,0,0,0.85), 0 1px 2px rgba(0,0,0,0.95)',
              }}
            >
              {e.metin}
            </div>
          </React.Fragment>
        );
      })}
    </AbsoluteFill>
  );
};

/** Cerceve vurgusu: goruntunun bir bolgesini kutu ya da daire ile isaretler. */
export const CerceveVurgusu: React.FC<{kutu?: VurguKutu; kareSayisi: number}> = ({
  kutu,
  kareSayisi,
}) => {
  const frame = useCurrentFrame();
  const {fps, width: W, height: H} = useVideoConfig();
  if (!kutu) return null;
  const gec = Math.round(fps * (kutu.gecikme ?? 0.5));
  const p = interpolate(frame, [gec, gec + Math.round(fps * 0.5)], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });
  const cik = interpolate(frame, [kareSayisi - Math.round(fps * 0.4), kareSayisi], [1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const opak = p * cik;
  const x = kutu.x * W;
  const y = kutu.y * H;
  const w = kutu.w * W;
  const h = kutu.h * H;
  // Kutu MERKEZDEN acilir: 0.85 -> 1.0 olcek, gozu rahatsiz etmeyen kisa bir hareket
  const olcek = 0.85 + 0.15 * p;
  const kose = Math.min(w, h) * 0.28;   // kose parcalari (tam cerceve yerine kose isareti)
  return (
    <AbsoluteFill style={{opacity: opak, pointerEvents: 'none'}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <g transform={`translate(${x + w / 2} ${y + h / 2}) scale(${olcek}) translate(${-(x + w / 2)} ${-(y + h / 2)})`}>
          {kutu.daire ? (
            <ellipse cx={x + w / 2} cy={y + h / 2} rx={w / 2} ry={h / 2}
                     fill="none" stroke="#FFFFFF" strokeWidth={4}
                     strokeDasharray={`${Math.PI * (w + h) / 2}`}
                     strokeDashoffset={`${(1 - p) * Math.PI * (w + h) / 2}`} />
          ) : (
            <>
              {/* Kose isaretleri: tam cerceve goruntuyu bogar, referansta koseler var */}
              <path d={`M${x} ${y + kose} L${x} ${y} L${x + kose} ${y}`} fill="none"
                    stroke="#FFFFFF" strokeWidth={4} />
              <path d={`M${x + w - kose} ${y} L${x + w} ${y} L${x + w} ${y + kose}`} fill="none"
                    stroke="#FFFFFF" strokeWidth={4} />
              <path d={`M${x + w} ${y + h - kose} L${x + w} ${y + h} L${x + w - kose} ${y + h}`}
                    fill="none" stroke="#FFFFFF" strokeWidth={4} />
              <path d={`M${x + kose} ${y + h} L${x} ${y + h} L${x} ${y + h - kose}`} fill="none"
                    stroke="#FFFFFF" strokeWidth={4} />
            </>
          )}
        </g>
      </svg>
    </AbsoluteFill>
  );
};

/* ─────────────────────── BOLUM BASLIGI ─────────────────────── */

/**
 * Referans #12'nin bolum basliklari (kullanicinin gonderdigi iki kareden olculdu).
 * IKI VARYANT var ve ayni videoda ikisi de kullaniliyor:
 *
 *   "ust"  — sol ust kose, cumle duzeni (Sentence case), orta boy.
 *            or. "A Tourist Paradise and the Contradictions Behind It"
 *            Olculen: x %3.2, y %7.4, yazi yuksekligi kare yuksekliginin ~%3.6'si
 *
 *   "orta" — kare ortasi, TAMAMI BUYUK HARF, cok kalin, iki satira sarabilir.
 *            or. "PRESERVING MADEIRA'S IDENTITY BETWEEN TRADITION AND THE MODERN WORLD"
 *            Olculen: yatayda ortali, y ~%55, satir yuksekligi ~%4.9
 *
 * NOT: ilk olcumumde "gomulu yazi yok" demistim. O olcumde video basina 26 kare
 * (90 sn araliklarla) almistim; bolum baslikleri sadece bolum GECISLERINDE (videoda
 * 5-8 kez) gorundugu icin ornekleme onlari kacirmis. Duzeltildi.
 *
 * HAREKET: "smooth" istegi -> spring ile asagidan yukari suzulme + fade, harf araligi
 * hafifce oturur. Blur YOK (1080p'de ucuz durur ve render'i yavaslatir).
 */
export type BolumYeri = 'ust' | 'orta';

export const BolumBasligi: React.FC<{
  metin?: string;
  yer?: BolumYeri;
  kareSayisi: number;
}> = ({metin, yer = 'orta', kareSayisi}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  if (!metin) return null;

  const yay = spring({frame, fps, config: {damping: 22, stiffness: 95, mass: 0.85}});
  // Ekranda kalma: 4.5 sn, sonra 0.7 sn'de sonum. Sahne kisaysa sahneye sigdir.
  const tut = Math.min(Math.round(fps * 4.5), Math.max(1, kareSayisi - Math.round(fps * 0.7)));
  const cik = interpolate(frame, [tut, tut + Math.round(fps * 0.7)], [1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.in(Easing.cubic),
  });
  const opak = yay * cik;
  const kayma = (1 - yay) * (yer === 'orta' ? 26 : 18);
  const harfAralik = (1 - yay) * (yer === 'orta' ? 3 : 1.5);

  const ustStil: React.CSSProperties = {
    position: 'absolute',
    left: '3.2%',
    top: '4.4%',
    // OLCUM: referans karede baslik TEK SATIR ve kare genisliginin ~%65'ini kapliyor.
    // 50 karakter icin bu ~46px Montserrat ExtraBold demek. 58'e cikarmak fazlaydi —
    // yazi ikinci satira tasiyordu ("...behind / it"), referansta tek satir.
    maxWidth: '92%',
    fontSize: 46,
    fontWeight: 800,
    lineHeight: 1.2,
    textAlign: 'left',
  };
  const ortaStil: React.CSSProperties = {
    maxWidth: '84%',
    fontSize: 68,
    fontWeight: 900,
    lineHeight: 1.14,
    textAlign: 'center',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  };

  return (
    <AbsoluteFill
      style={
        yer === 'orta'
          ? {justifyContent: 'center', alignItems: 'center', padding: '5% 6% 0'}   // ~%55
          : {}
      }
    >
      <div
        style={{
          ...(yer === 'orta' ? ortaStil : ustStil),
          opacity: opak,
          transform: `translateY(${kayma}px)`,
          letterSpacing: `${(yer === 'orta' ? 0.5 : 0) + harfAralik}px`,
          fontFamily: fontAilesi('montserrat'),
          color: '#FFFFFF',
          // Referansta yazi hem koyu hem acik zeminlerde okunuyor: kontur + golge birlikte.
          WebkitTextStroke: yer === 'orta' ? '3px rgba(0,0,0,0.62)' : '0px',
          paintOrder: 'stroke fill',
          textShadow:
            yer === 'orta'
              ? '0 6px 30px rgba(0,0,0,0.85), 0 2px 6px rgba(0,0,0,0.95)'
              : '0 4px 20px rgba(0,0,0,0.8), 0 1px 3px rgba(0,0,0,0.9)',
        }}
      >
        {metin}
      </div>
    </AbsoluteFill>
  );
};

/* ─────────────────────── dis kapi ─────────────────────── */

export const EditGrafigi: React.FC<{
  grafik?: Grafik;
  medya?: string;
  kareSayisi: number;
}> = ({grafik, medya, kareSayisi}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  if (!grafik) return null;
  const sonum = cikisSonum(frame, kareSayisi, fps);
  let ic: React.ReactNode = null;
  switch (grafik.tur) {
    case 'beyaz-tuval':
      ic = <BeyazTuval medya={medya} g={grafik} frame={frame} fps={fps} K={kareSayisi} />;
      break;
    case 'olcu':
      ic = <OlcuOku g={grafik} frame={frame} fps={fps} />;
      break;
    case 'alinti':
      ic = <AlintiKarti g={grafik} frame={frame} fps={fps} />;
      break;
    case 'metin':
      ic = <MetinBloku g={grafik} frame={frame} fps={fps} />;
      break;
    case 'harita':
      ic = <HaritaIsareti g={grafik} frame={frame} fps={fps} />;
      break;
    default:
      ic = null;
  }
  return <AbsoluteFill style={{opacity: sonum}}>{ic}</AbsoluteFill>;
};
