import React from 'react';
import {Lottie} from '@remotion/lottie';
import {EfektKatmanlari, Glitch, Hologram, KanalFiltreleri, Kromatik, YonluBlur,
  efektHesapla, type Efekt} from './Efektler';
import {BolumBasligi, CerceveVurgusu, EditGrafigi, SahaEtiketleri, beyazZeminMi,
  type BolumYeri, type Grafik, type SahaEtiketi, type VurguKutu} from './EditPaketi';
import {
  AbsoluteFill,
  Audio,
  Easing,
  Img,
  OffthreadVideo,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {TransitionSeries, linearTiming} from '@remotion/transitions';
import type {TransitionPresentation} from '@remotion/transitions';
import {fade} from '@remotion/transitions/fade';
// AE tarzi gecisler: kutuphane zaten kurulu (@remotion/transitions 4.0.410),
// sadece fade() kullaniliyordu. Anlatim islevine gore sahne basina secilir.
import {slide} from '@remotion/transitions/slide';
import {wipe} from '@remotion/transitions/wipe';
import {clockWipe} from '@remotion/transitions/clock-wipe';
import {fontlariYukle, fontAilesi, ayarCoz, FontAdi, AltyaziAyar} from './fontlar';

export type AltyaziParcasi = {t0: number; t1: number; metin: string};

export type Sahne = {
  tur: 'image' | 'video';
  medya: string;
  ses: string;
  sure: number;
  zoom: 'in' | 'out' | 'yok';
  pan: 'right' | 'left' | 'top' | 'bottom' | 'yok';
  overlay?: string;
  ae?: string;          // After Effects (Lottie) katmani: public altindaki .json yolu
  grafik?: Grafik;      // Edit paketi sablonu (beyaz-tuval / olcu / alinti / metin / harita)
  bolum?: string;       // Bolum basligi — SADECE bolumun ilk sahnesinde dolu
  bolumYeri?: BolumYeri;// 'ust' (sol ust, cumle duzeni) | 'orta' (ortada, BUYUK HARF)
  etiketler?: SahaEtiketi[];  // kucuk saha etiketleri (yer/nesne/sayi adi)
  vurguKutu?: VurguKutu;      // goruntunun bir bolgesini isaretleyen cerceve/daire
  efektler?: Efekt[];         // Efektler.tsx: sarsinti, grain, glitch, hologram, grade...
  altyazi: AltyaziParcasi[];
  vurgu?: boolean; // hikaye kanalı açılış sahnesi: yoğun hareket (derin zoom + push-in + paralaks)
  // Metin derin analizinden gelen anlatım işlevi — geçiş tipini o belirler.
  islev?: 'acilis' | 'liste' | 'vurgu' | 'aciklama' | 'ornek' | 'gecmis'
        | 'karsilastir' | 'soru' | 'sonuc';
};

export type Motion = 'sinematik' | 'anlati' | 'hizli' | 'kesme' | 'fade' | 'dinamik' | 'hikaye';
export type AltyaziStil = 'yok' | 'orta' | 'yogun';

export type VideoProps = {
  fps: number;
  genislik: number;
  yukseklik: number;
  gecis?: Motion;
  altyaziStil?: AltyaziStil;
  altyaziAyar?: Partial<AltyaziAyar> | string;   // sablon adi VEYA tam ayar nesnesi
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

// ⚠ 4 Agu 2026 — KENAR SIYAHLIGI DUZELTMESI (olculdu: 132 karenin 60'inda, %45)
// transform: translate(tx,ty) scale(k) -> once olcek, SONRA kaydirma uygulanir ve
// kaydirma mesafesi olcekten ETKILENMEZ. Olcek 1.0'a indiginde gorsel kareyi TAM
// dolduruyor, tasma payi kalmiyor; ustune panPx kaydirma binince o taraf BOSTA
// kaliyor ve siyah gorunuyor. Sahnelerin cogu zoom=out oldugu icin bu her sahnenin
// SONUNDA oluyordu.
// Cozum: en kucuk olcek, kaydirmayi soguracak kadar buyuk olmali.
//   yatay pan  -> 1 + (2 * panPx) / kareGenisligi
//   DIKEY pan  -> 1 + (2 * panPx) / kareYuksekligi   (yukseklik kucuk oldugu icin DAHA BUYUK)
// ⚠ Ilk duzeltmede her iki eksende de GENISLIK kullanmistim; dikey pan'da yetersiz
// kaliyordu ve alt/ust kenarda siyahlik suruyordu (render testinde yakalandi).
const TABAN_OLCEK = (panPx: number, dikey: boolean, kareGen: number, kareYuk: number) =>
  panPx <= 0 ? 1 : 1 + (2 * panPx) / (dikey ? kareYuk : kareGen) + 0.012;

const kbHesap = (
  sahne: Sahne,
  frame: number,
  K: number,
  buyume: number,
  panPx: number,
  kareGen = 1920,
  kareYuk = 1080,
) => {
  if (sahne.zoom === 'yok') return {olcek: 1, tx: 0, ty: 0};
  const dikeyPan = sahne.pan === 'top' || sahne.pan === 'bottom';
  const taban = TABAN_OLCEK(panPx, dikeyPan, kareGen, kareYuk);
  const tepe = Math.max(buyume, taban + 0.06);   // tepe her zaman tabandan yukarida
  const olcek = interpolate(frame, [0, K], sahne.zoom === 'in' ? [taban, tepe] : [tepe, taban], {
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

// ── AFTER EFFECTS KATMANI (Lottie, 5 Agu 2026) ──
// Lottie = After Effects'in Bodymovin ile disa aktarilmis animasyon formati. Yani bir
// tasarimcinin AE'de yaptigi alt-band/baslik/gecis animasyonu BIREBIR burada oynar;
// biz onu React'te yeniden yazmiyoruz.
// Kullanim: sahne'ye "ae" alani konur -> public altindaki .json yolu. Alan bossa katman
// hic cizilmez, yani mevcut isler etkilenmez.
// NOT: dosya yoksa/bozuksa TUM render cokmesin diye try/catch + hata durumunda null.
const AEKatmani: React.FC<{yol?: string; kareSayisi: number}> = ({yol}) => {
  const [veri, setVeri] = React.useState<Record<string, unknown> | null>(null);
  const [hata, setHata] = React.useState(false);
  React.useEffect(() => {
    if (!yol) return;
    let iptal = false;
    fetch(kaynakCoz(yol))
      .then((r) => r.json())
      .then((j) => !iptal && setVeri(j))
      .catch(() => !iptal && setHata(true));
    return () => {
      iptal = true;
    };
  }, [yol]);
  if (!yol || hata || !veri) return null;
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      <Lottie animationData={veri as never} loop={false} />
    </AbsoluteFill>
  );
};

// ── GERI SAYIM ROZETI (5 Agu 2026 olcumu) ──
// Olcum: referans kanalin karelerinin %35'inde gorselin USTUNDE buyuk bir baslik/sayi var;
// bizim bitmis videomuzda bu oran %5'ti. Sebep: bizim overlay basligimiz sahnenin sadece
// ilk saniyelerinde gorunup soluyordu; referansta ise madde numarasi kosede SAHNE BOYUNCA
// duruyor (REFERANSLAR.md #11-B: "10 videoda da var, liste videolarinin omurgasi").
// Bu yuzden rozet ayri bir katman: overlay yazisi girer-cikar, rozet sabit kalir.
const GeriSayimRozeti: React.FC<{metin: string; kareSayisi: number}> = ({metin, kareSayisi}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const m = /^(\d{1,2})\b/.exec((metin || '').trim());
  if (!m) return null;                       // sadece numarali liste maddelerinde
  const gir = interpolate(frame, [0, Math.round(fps * 0.4)], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });
  const cik = interpolate(frame, [kareSayisi - Math.round(fps * 0.4), kareSayisi], [1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  return (
    <AbsoluteFill style={{justifyContent: 'flex-start', alignItems: 'flex-start'}}>
      <div
        style={{
          opacity: gir * cik,
          transform: `translateY(${(1 - gir) * -24}px)`,
          margin: '48px 0 0 56px',
          fontFamily: fontAilesi('anton'),
          fontSize: 132,
          lineHeight: 1,
          color: '#ffffff',
          WebkitTextStroke: '7px #000000',
          paintOrder: 'stroke fill',
          textShadow: '0 6px 26px rgba(0,0,0,0.45)',
        }}
      >
        {m[1]}
      </div>
    </AbsoluteFill>
  );
};

const OverlayBaslik: React.FC<{metin: string; motion: string; kareSayisi: number}> = ({
  metin,
  motion,
  kareSayisi,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  if (!metin) return null;
  const hizli = motion === 'hizli';

  // ── AE tarzı: kelimeler TEK TEK, spring ile yaylanarak girer ──
  // Tek blok halinde fade yerine kelime bazlı gecikmeli giriş; her kelime
  // aşağıdan yukarı yaylanır, hafif büyür ve blur'dan netliğe geçer.
  const kelimeler = metin.split(/\s+/).filter(Boolean);
  const gecikme = hizli ? 2 : 3;           // kelimeler arası kare farkı

  // Çıkış: blok halinde yumuşak sönüm (girişi bozmasın diye ayrı)
  const cikisBas = hizli ? kareSayisi - 8 : Math.min(kareSayisi - 8, 64);
  const cik = interpolate(frame, [cikisBas, kareSayisi], [1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.in(Easing.cubic),
  });

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
          opacity: cik,
          maxWidth: '84%',
          textAlign: 'center',
          overflowWrap: 'anywhere',
          wordBreak: 'break-word',
          fontFamily: fontAilesi(hizli ? 'anton' : 'montserrat'),
          fontWeight: hizli ? 400 : 800,
          // ⚠ Bu bes satir kelime-animasyonu yazilirken DUSMUSTU: yazi 68px yerine
          // varsayilan ~16px ciziliyordu ve karede okunmuyordu. Render testinde yakalandi.
          fontSize: hizli ? 96 : 68,
          lineHeight: 1.05,
          letterSpacing: hizli ? 0 : -1,
          color: hizli ? '#0a0a0a' : '#ffffff',
          // Kontur: acik zeminlerde (krem mutfak gibi) beyaz yazi golgeyle bile
          // okunmuyordu. paint-order konturu yazinin ARKASINA cizer — altyazi
          // sistemindeki cozumun aynisi, her zeminde okunur.
          textShadow: hizli ? 'none' : '0 3px 18px rgba(0,0,0,0.55)',
          WebkitTextStroke: hizli ? '0' : '5px #000000',
          paintOrder: 'stroke fill',
          background: hizli ? '#ffd400' : 'transparent',
          padding: hizli ? '10px 26px' : 0,
          borderRadius: hizli ? 10 : 0,
          display: 'flex',
          flexWrap: 'wrap',
          justifyContent: 'center',
          gap: '0 0.32em',
        }}
      >
        {kelimeler.map((k, i) => {
          // Her kelimenin kendi yayı — damping yüksek ki titremesin, AE'deki
          // "ease out back" hissi verir.
          const y = spring({
            frame: frame - i * gecikme,
            fps,
            config: {damping: 18, stiffness: 140, mass: 0.7},
            durationInFrames: hizli ? 14 : 20,
          });
          const opak = interpolate(y, [0, 0.55], [0, 1], {extrapolateRight: 'clamp'});
          const ty = (1 - y) * (hizli ? 34 : 26);
          const olcek = 0.9 + y * 0.1;
          const bul = (1 - y) * 5;
          return (
            <span
              key={i}
              style={{
                display: 'inline-block',
                opacity: opak,
                transform: `translateY(${ty}px) scale(${olcek})`,
                filter: bul > 0.15 ? `blur(${bul}px)` : 'none',
                willChange: 'transform, opacity',
              }}
            >
              {k}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

const Altyazi: React.FC<{
  parcalar: AltyaziParcasi[];
  fps: number;
  stil: AltyaziStil;
  ayar?: Partial<AltyaziAyar> | string;
}> = ({parcalar, fps, stil, ayar}) => {
  const frame = useCurrentFrame();
  const saniye = frame / fps;
  const aktif = parcalar.find((p) => saniye >= p.t0 && saniye < p.t1);
  if (!aktif || stil === 'yok') return null;

  const a = ayarCoz(ayar);
  const kutulu = a.arka !== 'yok' && a.arka !== 'transparent';
  const olcek = stil === 'yogun' ? 1.12 : 1;   // 'yogun' biraz buyutur
  const metin = a.buyukHarf ? aktif.metin.toLocaleUpperCase('tr-TR') : aktif.metin;

  const hizalama =
    a.konum === 'ust' ? 'flex-start' : a.konum === 'orta' ? 'center' : 'flex-end';

  return (
    <AbsoluteFill
      style={{
        justifyContent: hizalama,
        alignItems: 'center',
        paddingBottom: a.konum === 'alt' ? 72 : 0,
        paddingTop: a.konum === 'ust' ? 90 : 0,
      }}
    >
      <div
        style={{
          maxWidth: '84%',
          backgroundColor: kutulu ? a.arka : 'transparent',
          color: a.renk,
          overflowWrap: 'anywhere',
          wordBreak: 'break-word',
          fontFamily: fontAilesi(a.font),
          fontSize: Math.round(a.boyut * olcek),
          fontWeight: a.agirlik,
          letterSpacing: a.harfAralik,
          lineHeight: 1.22,
          textAlign: 'center',
          padding: kutulu ? '13px 30px' : 0,
          borderRadius: kutulu ? 14 : 0,
          // GERCEK KONTUR: -webkit-text-stroke + paint-order -> kontur yazinin ARKASINA cizilir,
          // harfler incelmez (text-shadow taklidinden cok daha temiz sonuc).
          WebkitTextStroke: a.konturKalinlik > 0 ? `${a.konturKalinlik}px ${a.konturRenk}` : undefined,
          paintOrder: 'stroke fill',
          textShadow: a.golge ? '0 4px 14px rgba(0,0,0,0.75)' : undefined,
        } as React.CSSProperties}
      >
        {metin}
      </div>
    </AbsoluteFill>
  );
};

type Gorunum = {transform: string};

// ── ZOOM MIKTARI SABIT DEGIL, SURE ILE BUYUR (5 Agu 2026 olcumu) ──
// Referans kanallarda ayni sahnede 8 sn arayla alinan kareler olcek eslestirmesiyle
// karsilastirildi: medyan zoom hizi %2.5/sn, 12 sn'lik bir sahnede toplam ~1.30x.
// Bizde sabit 1.06-1.08 vardi = %1.2/sn — referansin yarisi. Sahne suresi 5 sn'den
// 12 sn'ye cikinca bu sabit zoom "donmus goruntu" haline gelirdi.
// Ust sinir 1.26: kaynak gorsel 1536 px genisliginde, daha derin zoom yumusakliga yol acar.
const SURE_ZOOM = (K: number, fps: number, oran = 0.022, tavan = 1.26) =>
  Math.min(tavan, 1 + oran * (K / Math.max(1, fps)));

const sinematikHesapla = (sahne: Sahne, frame: number, K: number, fps: number): Gorunum => {
  const {olcek, tx, ty} = kbHesap(sahne, frame, K, SURE_ZOOM(K, fps), 22);
  return {transform: `scale(${olcek}) translate(${tx}px, ${ty}px)`};
};

const kesmeHesapla = (sahne: Sahne, frame: number, K: number, fps: number): Gorunum => {
  const {olcek, tx, ty} = kbHesap(sahne, frame, K, SURE_ZOOM(K, fps), 20);
  return {transform: `scale(${olcek}) translate(${tx}px, ${ty}px)`};
};

// blur YOK. Push-in reveal transform ile. fade her sahnede degil -> gecis crossfade yapar (flash yok).
const anlatiHesapla = (sahne: Sahne, frame: number, K: number, fps: number): Gorunum => {
  // ⚠ 4 Agu 2026: giris push-in (1.12 -> 1.0) KALDIRILDI.
  // Crossfade sirasinda giden sahne zoom sonunda (~1.12), gelen sahne ayni anda
  // 1.12'den 1.0'a HIZLA kuculuyordu. Iki farkli olcek ust uste karisinca goz
  // bunu TAKILMA olarak goruyor (Polat bildirdi). Artik tek surekli hareket var:
  // sadece Ken Burns, sahne boyunca duzgun akiyor, gecis onu bozmuyor.
  const {olcek: kb, tx: kbTx, ty: kbTy} = kbHesap(sahne, frame, K, SURE_ZOOM(K, fps, 0.026, 1.30), 40);
  return {transform: `translate(${kbTx}px, ${kbTy}px) scale(${kb})`};
};

const hizliHesapla = (sahne: Sahne, frame: number, K: number, indeks: number, fps: number): Gorunum => {
  const yon = indeks % 2 === 0 ? 1 : -1;
  const g = Math.max(4, Math.min(9, Math.floor(K / 4)));
  const girisP = interpolate(frame, [0, g], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });
  // Hizli modda giris(1.18->1.0) + cikis(1.0->1.12) olcegi geciste ust uste
  // binip zipliyordu. Yanal kayma korundu (o gecisle catismiyor), olcek ziplamasi
  // kaldirildi — tek surekli Ken Burns kaldi.
  const girisX = (1 - girisP) * yon * 60;
  const {olcek: kb} = kbHesap(sahne, frame, K, SURE_ZOOM(K, fps, 0.026, 1.30), 0);
  return {transform: `translateX(${girisX}px) scale(${kb})`};
};

// Hikaye kanali: ACILIS sahneleri (vurgu=true, ilk ~2.5dk) yogun hareket alir — derin zoom +
// push-in giris + genis paralaks pan (izleyici tutma). Sonraki sahneler sakin sinematik Ken Burns.
// Hepsi transform-only: render maliyetine etkisi yok.
const hikayeHesapla = (sahne: Sahne, frame: number, K: number, fps: number): Gorunum => {
  if (sahne.vurgu) {
    const g = Math.max(6, Math.min(14, Math.floor(K / 4)));
    const girisP = interpolate(frame, [0, g], [0, 1], {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
      easing: Easing.out(Easing.cubic),
    });
    // Vurgu sahnesinde push-in KORUNUYOR ama cok daha yumusak (1.2 -> 1.06):
    // gecisle carpismasin diye. Derin zoom + genis pan zaten hareketi tasiyor.
    const girisOlcek = 1.06 - 0.06 * girisP;
    // 1.16/48 yetersizdi ("videolasmis" hissi vermiyordu) -> 1.30/110: kamera geziyor hissi
    const {olcek, tx, ty} = kbHesap(sahne, frame, K, 1.3, 110); // derin zoom + genis pan
    return {transform: `translate(${tx}px, ${ty}px) scale(${olcek * girisOlcek})`};
  }
  const {olcek, tx, ty} = kbHesap(sahne, frame, K, SURE_ZOOM(K, fps), 26); // sakin bolum
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
  altyaziAyar?: Partial<AltyaziAyar> | string;
}> = ({sahne, indeks, motion, altyaziStil, kareSayisi, altyaziAyar}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const K = kareSayisi;

  const g =
    motion === 'anlati'
      ? anlatiHesapla(sahne, frame, K, fps)
      : motion === 'hizli'
      ? hizliHesapla(sahne, frame, K, indeks, fps)
      : motion === 'kesme'
      ? kesmeHesapla(sahne, frame, K, fps)
      : motion === 'hikaye'
      ? hikayeHesapla(sahne, frame, K, fps)
      : sinematikHesapla(sahne, frame, K, fps);

  // Efekt yigini: transform (sarsinti/dolly/3d donme) + filter (grade/bw/glow)
  const ef = efektHesapla(sahne.efektler, frame, fps, K, `s${indeks}`);
  const gorselStil: React.CSSProperties = {
    width: '100%',
    height: '100%',
    objectFit: 'cover',
    transform: `${g.transform}${ef.transform ? ' ' + ef.transform : ''}`,
    ...(ef.filter !== 'none' ? {filter: ef.filter} : {}),
  };
  const efAd = (sahne.efektler || []).map((e) => e.ad);
  // Sarmalayici efektler: goruntuyu KOPYALAYARAK calisirlar (kanal ayirma, blur yonu)
  const sarmala = (ic: React.ReactNode): React.ReactNode => {
    let c = ic;
    if (efAd.includes('glitch')) c = <Glitch tohum={`g${indeks}`}>{c}</Glitch>;
    if (efAd.includes('hologram')) c = <Hologram>{c}</Hologram>;
    if (efAd.includes('kromatik')) c = <Kromatik>{c}</Kromatik>;
    if (efAd.includes('yon-blur') || efAd.includes('hareket-blur')) {
      c = <YonluBlur siddet={1.2} aci={efAd.includes('hareket-blur') ? 90 : 0}>{c}</YonluBlur>;
    }
    return c;
  };

  // Edit paketi: beyaz-tuval/alinti/metin sablonlari BEYAZ zemin ister. O durumda
  // fotografi tam kare cizmek zemini yok eder -> foto sablonun icinde yalitilmis
  // olarak yerlestirilir, vinyet de kapatilir (beyaz zeminde vinyet kir gibi durur).
  const beyaz = beyazZeminMi(sahne.grafik);
  const vinyet =
    !beyaz && (motion === 'anlati' || motion === 'hizli' || motion === 'hikaye');

  return (
    <AbsoluteFill style={{backgroundColor: beyaz ? '#FFFFFF' : 'black'}}>
      {efAd.length ? <KanalFiltreleri /> : null}
      {beyaz ? null : sarmala(<GuvenliGorsel sahne={sahne} stil={gorselStil} />)}
      {/* Vinyet (anlati/hizli/hikaye): tek radial-gradient, per-frame maliyet yok.
          Hikayede film-karesi hissi verir. */}
      {vinyet ? (
        <AbsoluteFill
          style={{
            background:
              'radial-gradient(ellipse at center, rgba(0,0,0,0) 52%, rgba(0,0,0,0.4) 100%)',
          }}
        />
      ) : null}
      <EditGrafigi
        grafik={sahne.grafik}
        medya={sahne.medya ? kaynakCoz(sahne.medya) : undefined}
        kareSayisi={K}
      />
      <AEKatmani yol={sahne.ae} kareSayisi={K} />
      <EfektKatmanlari efektler={sahne.efektler} kareSayisi={K} tohum={`e${indeks}`} />
      <CerceveVurgusu kutu={sahne.vurguKutu} kareSayisi={K} />
      <SahaEtiketleri etiketler={sahne.etiketler} kareSayisi={K} />
      <BolumBasligi metin={sahne.bolum} yer={sahne.bolumYeri} kareSayisi={K} />
      <GeriSayimRozeti metin={sahne.overlay || ''} kareSayisi={K} />
      <OverlayBaslik metin={sahne.overlay || ''} motion={motion} kareSayisi={K} />
      <Altyazi
        parcalar={sahne.altyazi}
        fps={fps}
        stil={altyaziStil}
        ayar={altyaziAyar}
      />
      <Audio src={kaynakCoz(sahne.ses)} />
    </AbsoluteFill>
  );
};

export const VidrushVideo: React.FC<VideoProps> = ({
  fps, gecis, altyaziStil, altyaziAyar, sahneler,
}) => {
  fontlariYukle();   // gomulu altyazi fontlarini enjekte et + yuklenene kadar render'i beklet
  const {width, height} = useVideoConfig();   // clockWipe gecisi boyut ister
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
          altyaziAyar={altyaziAyar}
        />
      </TransitionSeries.Sequence>,
    );
    if (i < sahneler.length - 1 && gecisler[i] > 0) {
      // Geçiş tipi SONRAKİ sahnenin işlevine göre — o sahneye nasıl giriliyor?
      //   liste  -> yeni madde: sayfa çevirir gibi yandan kayma
      //   gecmis -> geçmişe dönüş: saat yönünde silme (zaman hissi)
      //   vurgu  -> vuruş: keskin silme
      //   diğer  -> yumuşak crossfade (varsayılan, siyah flaş yok)
      const sonraki = sahneler[i + 1]?.islev;
      const sure = gecisler[i];
      const sunum =
        sonraki === 'liste'
          ? (slide({direction: 'from-right'}) as unknown as TransitionPresentation<Record<string, unknown>>)
          : sonraki === 'gecmis'
            ? (clockWipe({width, height}) as unknown as TransitionPresentation<Record<string, unknown>>)
            : sonraki === 'vurgu'
              ? (wipe({direction: 'from-left'}) as unknown as TransitionPresentation<Record<string, unknown>>)
              : (fade() as unknown as TransitionPresentation<Record<string, unknown>>);
      cocuklar.push(
        <TransitionSeries.Transition
          key={`t${i}`}
          presentation={sunum}
          timing={linearTiming({durationInFrames: sure})}
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
