import React from 'react';
import {Lottie} from '@remotion/lottie';
import {EfektKatmanlari, Glitch, Hologram, KanalFiltreleri, Kromatik, YonluBlur,
  efektHesapla, type Efekt} from './Efektler';
import {AltBand, BolumBasligi, CerceveVurgusu, EditGrafigi, KaliciLogo,
  SahaEtiketleri, beyazZeminMi,
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
  gecisImza?: string;         // 'karartma' | 'flash' | 'whip' — BOSSA sert kesme (olculen %80)
  altBand?: {baslik: string; alt?: string};   // en cok kullanilan yazi turu (olculen %33)
  // ⚠ FAZ I-41: CC/lisansli klip atfi ("Kanal Adi / CC BY"). Bu alan
  // `pipeline.py` tarafinda medya edinimi sirasinda URETILIR (kullanicidan
  // gelmez, 22 alanlik /api/generate sozlesmesinin parcasi DEGILDIR).
  // Alan YOKSA katman cizilmez -> eski davranis birebir korunur.
  kaynakYazi?: string;
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
  logo?: string;              // kalici kose filigrani (kanal adi); bos = filigran yok
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
// ── KEN BURNS EASING (7 Agu 2026 olcumu ile duzeltildi) ──
// 20 referans videodan 134 temiz cekimde zoom RAMPASI olculdu:
//   1. ceyrek %1.22/sn | 2. ceyrek %1.14/sn | 3. ceyrek %1.26/sn
//   son/ilk = 1.03  ->  yani SABIT HIZ, LINEER. Referansta rampa YOK.
// Eski egrimiz bezier(0.33,0,0.2,1) hareketin buyuk kismini ilk ceyrege yigiyordu
// (yaklasik 7:1 on yuklemeli) — referansin tersi. Cok hafif bir yumusatma birakildi
// (baslangic/bitis sertligini kirmak icin), gerisi lineer.
const KB_EASING = Easing.bezier(0.42, 0.32, 0.58, 0.68);

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

/**
 * EKRAN KUNYESI — "Kanal Adi / CC BY" (Faz I-41).
 *
 * NEDEN VAR: Creative Commons klip kullanmak ATIF ZORUNLULUGU getirir.
 * `pipeline.py` atfi sahneye yaziyordu ama props sinirinda DUSUYORDU; bu
 * kompozisyonun `Sahne` tipinde alan bile yoktu, dolayisiyla CC klip kullanan
 * her uretimde ekran atfi HIC cizilmedi.
 *
 * ⚠ BU YAZI TELIF IZNI DEGILDIR ve lisansin RESMI atif yerinin (video
 * aciklamasi, `kaynak.atif_listesi`) yerine GECMEZ.
 *
 * KONUM HESAPLANDI, "yeterince kenarda" VARSAYILMADI (I-12/I-16/I-39 dersi):
 *   · alt serit ALTYAZININ (bu kompozisyonda `paddingBottom: 72`) ve
 *     eski `y=h-th-22` sabiti yayin guvenli alaninin DISINDAYDI
 *   · sol ust `GeriSayimRozeti`nde, ust orta `OverlayBaslik`ta
 *   -> SAG UST bos. Oran I-39'da olculen `tipografi.KAYNAK_ETIKETI_ALTYAZILI`
 *      (0.075) ve guvenli kenar 64 px (1080p tabanli, olcuyle oranlanir).
 * `hizli_render._kaynak_yazi_filtre` AYNI sayilari kullanir — iki renderer
 * arasinda IKINCI ARITMETIK YOK (I-40 dersi).
 */
const KUNYE_Y_ORANI = 0.075;
const KUNYE_GUVENLI_KENAR = 64;

const KaynakYazi: React.FC<{metin?: string}> = ({metin}) => {
  const {height, width} = useVideoConfig();
  const m = (metin || '').trim();
  if (!m) return null;
  const olcek = height / 1080;
  const punto = Math.round(21 * olcek);
  const kenar = Math.round(KUNYE_GUVENLI_KENAR * olcek);
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      <div
        style={{
          position: 'absolute',
          right: kenar,
          top: Math.round(KUNYE_Y_ORANI * height),
          maxWidth: width * 0.5,
          overflow: 'hidden',
          whiteSpace: 'nowrap',
          textOverflow: 'ellipsis',
          fontFamily: fontAilesi('Montserrat'),
          fontWeight: 600,
          fontSize: punto,
          letterSpacing: '0.04em',
          color: '#FFFFFF',
          opacity: 0.62,
          textShadow: '0 1px 3px rgba(0,0,0,0.75), 0 0 1px rgba(0,0,0,0.9)',
        }}
      >
        {m}
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
// ── ZOOM HIZI (7 Agu 2026 olcumu) ──
// 246 cekim olculdu (piksel eslestirme, NCC). Gorsel/AI agirlikli 5 kanalda:
//   medyan %1.57/sn  (bizim eski 0.022 = %2.2/sn, medyanin %40 ustunde)
//   12 sn+ cekimlerde toplam zoom 1.32-1.47 -> eski tavan 1.26 uzun sahneyi kisitliyordu
// ASIL BULGU: hiz TEK BIR DEGER DEGIL, dagilim:
//   %34 ihmal edilebilir (<0.5%/sn) | %39 sakin (0.5-2) | %14 belirgin (2-5) | %12 agresif (>5)
// Bizim motor her sahneye AYNI hizi veriyordu -> "hep ayni kamera" hissi.
// Artik sahne indeksinden deterministik kova secilir.
const ZOOM_KOVA: {oran: number; pay: number}[] = [
  {oran: 0.004, pay: 0.34},   // ihmal edilebilir
  {oran: 0.014, pay: 0.39},   // sakin
  {oran: 0.032, pay: 0.14},   // belirgin
  {oran: 0.062, pay: 0.13},   // agresif
];

// ── ACILIS CEKIMI KOVAYA BIRAKILAMAZ (Faz I-42) ──
// ⚠ OLCULEN KUSUR: asagidaki dagitim `r = ((indeks * 2749) % 1000) / 1000`
// ile calisiyor ve indeks 0 icin r HER ZAMAN 0.000 -> DAIMA ilk kova
// (%0.4/sn, "ihmal edilebilir"). Yani ACILIS/HOOK cekimi her uretimde
// dagilimin EN DURAGAN ucuna sabitleniyordu. Bu bir tercih degil, indeks
// aritmetiginin yan etkisiydi.
// Gercek 1080p render'da olculdu (`vidrushvideo_kunye_i41.mp4`):
//   s0 optik ortalama 1.421 < esik 2.0, en uzun duragan seri 3.0 sn -> FAIL
// ⚠ ESIK GEVSETILMEDI (`kalite_kapisi.OPTIK_DURGUN_ESIGI` = 2.0 duruyor);
// degisen yalniz acilis sahnesinin hareketi.
// ⚠ UYDURMA SAYI YOK: deger dagilimin KENDI kovalarindan secildi ve gercek
// render'da OLCULEREK dogrulandi (bkz. FAZ-H-HANDOFF I-42 kalibrasyonu).
// Diger sahneler icin dagitim BIT-BIT aynidir.
const ACILIS_ZOOM_ORANI = 0.062;

/** Sahne indeksine gore zoom hizi kovasi (deterministik, her uretimde ayni). */
const zoomOrani = (indeks: number): number => {
  if (indeks === 0) return ACILIS_ZOOM_ORANI;
  const r = ((indeks * 2749) % 1000) / 1000;
  let birikim = 0;
  for (const k of ZOOM_KOVA) {
    birikim += k.pay;
    if (r < birikim) return k.oran;
  }
  return ZOOM_KOVA[1].oran;
};

const SURE_ZOOM = (K: number, fps: number, oran = 0.018, tavan = 1.38) =>
  Math.min(tavan, 1 + oran * (K / Math.max(1, fps)));

const sinematikHesapla = (sahne: Sahne, frame: number, K: number, fps: number,
  indeks = 0): Gorunum => {
  const {olcek, tx, ty} = kbHesap(sahne, frame, K, SURE_ZOOM(K, fps, zoomOrani(indeks)), 22);
  return {transform: `scale(${olcek}) translate(${tx}px, ${ty}px)`};
};

const kesmeHesapla = (sahne: Sahne, frame: number, K: number, fps: number,
  indeks = 0): Gorunum => {
  const {olcek, tx, ty} = kbHesap(sahne, frame, K, SURE_ZOOM(K, fps, zoomOrani(indeks)), 20);
  return {transform: `scale(${olcek}) translate(${tx}px, ${ty}px)`};
};

// blur YOK. Push-in reveal transform ile. fade her sahnede degil -> gecis crossfade yapar (flash yok).
const anlatiHesapla = (sahne: Sahne, frame: number, K: number, fps: number,
  indeks = 0): Gorunum => {
  // ⚠ 4 Agu 2026: giris push-in (1.12 -> 1.0) KALDIRILDI.
  // Crossfade sirasinda giden sahne zoom sonunda (~1.12), gelen sahne ayni anda
  // 1.12'den 1.0'a HIZLA kuculuyordu. Iki farkli olcek ust uste karisinca goz
  // bunu TAKILMA olarak goruyor (Polat bildirdi). Artik tek surekli hareket var:
  // sadece Ken Burns, sahne boyunca duzgun akiyor, gecis onu bozmuyor.
  const {olcek: kb, tx: kbTx, ty: kbTy} = kbHesap(sahne, frame, K, SURE_ZOOM(K, fps, zoomOrani(indeks) * 1.2, 1.42), 40);
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
  const {olcek: kb} = kbHesap(sahne, frame, K, SURE_ZOOM(K, fps, zoomOrani(indeks) * 1.2, 1.42), 0);
  return {transform: `translateX(${girisX}px) scale(${kb})`};
};

// Hikaye kanali: ACILIS sahneleri (vurgu=true, ilk ~2.5dk) yogun hareket alir — derin zoom +
// push-in giris + genis paralaks pan (izleyici tutma). Sonraki sahneler sakin sinematik Ken Burns.
// Hepsi transform-only: render maliyetine etkisi yok.
const hikayeHesapla = (sahne: Sahne, frame: number, K: number, fps: number,
  indeks = 0): Gorunum => {
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
  const {olcek, tx, ty} = kbHesap(sahne, frame, K, SURE_ZOOM(K, fps, zoomOrani(indeks)), 26);
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
      ? anlatiHesapla(sahne, frame, K, fps, indeks)
      : motion === 'hizli'
      ? hizliHesapla(sahne, frame, K, indeks, fps)
      : motion === 'kesme'
      ? kesmeHesapla(sahne, frame, K, fps, indeks)
      : motion === 'hikaye'
      ? hikayeHesapla(sahne, frame, K, fps, indeks)
      : sinematikHesapla(sahne, frame, K, fps, indeks);

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
      <AltBand baslik={sahne.altBand?.baslik} alt={sahne.altBand?.alt} kareSayisi={K} />
      <BolumBasligi metin={sahne.bolum} yer={sahne.bolumYeri} kareSayisi={K} />
      <GeriSayimRozeti metin={sahne.overlay || ''} kareSayisi={K} />
      <KaynakYazi metin={sahne.kaynakYazi} />
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
  fps, gecis, altyaziStil, altyaziAyar, sahneler, logo,
}) => {
  fontlariYukle();   // gomulu altyazi fontlarini enjekte et + yuklenene kadar render'i beklet
  const {width, height} = useVideoConfig();
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
    // ── GECIS SECIMI — OLCULEN DAGILIMA GORE (7 Agu 2026) ──
    // 20 referans videodan 786 kesme etiketlendi (kare cifti + piksel dogrulamasi):
    //   sert-kesme %79.9 | karartma %7.6 | beyaz-flash %4.1 | whip-pan %3.3
    //   crossfade %2.2 | wipe %1.1 | zoom-through %1.0 | match-cut %0.3
    // Yani bu niste gecis DEMEK SERT KESME. Susulu gecislerin toplami %2.4 — pratikte yok.
    // ONCEKI HALIM YANLISTI: 6 farkli gecisi anlatim islevine baglamistim (liste->slide,
    // gecmis->clockWipe, vurgu->wipe, digeri->crossfade). Bu, karelerin neredeyse
    // TAMAMINA efekt koyuyordu ve referanslardan UZAKLASTIRIYORDU.
    // Artik: varsayilan SERT KESME (gecis yok), ve sadece stilin OLCULEN imzasi kadar efekt.
    // Kanal imzalari (olculdu):
    //   ZeroReports  karartma %23.1 (genelin 3 kati) — karanlik/gizemli ton
    //   NavyDecoded  flash %10.3 + zoom-through %4.8 + whip %6.2 — enerjik ton
    //   Auralis      %97.5 saf sert kesme — sakin anlati
    if (i < sahneler.length - 1 && gecisler[i] > 0) {
      const sonraki = sahneler[i + 1];
      const imza = String(sonraki?.gecisImza || '');
      const sure = gecisler[i];
      // Imza yoksa GECIS EKLENMEZ -> sert kesme (referanstaki %80'lik pay)
      if (imza) {
        const sunum =
          imza === 'karartma'
            ? (fade({shouldFadeOutExitingScene: true, enterStyle: {}}) as unknown as TransitionPresentation<Record<string, unknown>>)
            : imza === 'whip'
              ? (slide({direction: 'from-right'}) as unknown as TransitionPresentation<Record<string, unknown>>)
              : (fade() as unknown as TransitionPresentation<Record<string, unknown>>);
        cocuklar.push(
          <TransitionSeries.Transition
            key={`t${i}`}
            presentation={sunum}
            timing={linearTiming({durationInFrames: sure})}
          />,
        );
      }
    }
  });

  return (
    <AbsoluteFill style={{backgroundColor: 'black'}}>
      <TransitionSeries>{cocuklar}</TransitionSeries>
      {/* Kalici kose logosu VIDEO seviyesinde: olculdu, 7 kanaldan 2'si videonun
          tamaminda filigran tasiyor ve hic kapanmiyor. Sahne seviyesinde olsa gecislerde
          yanip sonerdi. */}
      <KaliciLogo metin={logo} kose="sag-ust" />
    </AbsoluteFill>
  );
};
