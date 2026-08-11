/**
 * FAZ C MOTION SPEC SOZLESMESI — TypeScript karsiligi.
 *
 * Bu dosya `webapp/editor/adapter.py`'nin urettigi `remotion_props` yapisinin
 * BIREBIR karsiligidir. Python tarafinda alan adi degisirse burasi da degismek
 * zorunda; `test_faz_d.py` iki tarafi karsilastirip sapmayi yakaliyor.
 *
 * ⚠ DESTEK MATRISI TEK DOGRULUK KAYNAGI (kullanicinin acik istegi):
 * Hangi spec'in gercekten render edildigi YALNIZCA `DESTEK_MATRISI`'nde yazar.
 * Bir bilesen eklenip matrise yazilmazsa validator FAIL verir; matrise yazilip
 * bileseni olmayan spec de FAIL verir. Boylece "beyan var ama render yok"
 * durumu (Faz C'de yakalanan mimari acik) tekrarlanamaz.
 */

export type Renderer = 'ffmpeg' | 'remotion';

/** Faz C `MotionSpec.sozluk()` cikisinin aynisi. */
export interface MotionSpec {
  ad: string;
  renderer: Renderer;
  parametre: Record<string, unknown>;
  easing: string;
  easing_bezier: number[]; // [x1,y1,x2,y2]
  bas_sn: number;
  sure_sn: number;
  katman: number;
  fallback: Record<string, unknown> | null;
  remotion_zorunlu: boolean;
  gerekce: string;
  beat_id?: string;
  scene_id?: string;
  fact_id?: string;
}

export interface PremiumGerekce {
  spec: string;
  gerekce: string;
  fallback_var: boolean;
}

/** Faz C `adapter.donustur().remotion_props.sahneler[i]` */
export interface EditorSahne {
  beat_id: string;
  scene_id: string;
  fact_id: string;
  asset_id: string;
  saglayici: string;
  lisans: string;
  tur: 'image' | 'video';
  medya: string;
  ses: string;
  sure: number;
  bas_sn: number;
  islev: string;
  perde: string;
  cekim_turu: string;
  hareket: string;
  kadraj: string;
  kaynak_aralik: number[];
  j_cut: boolean;
  l_cut: boolean;
  altyazi: unknown[];
  motion: MotionSpec[];
  gerekce: string;
  premium_gerekce?: PremiumGerekce[];
  /** 2.5D icin hazir katman gorselleri (yoksa pseudo-depth fallback) */
  parallax_katmanlari?: string[];

  /* ── SES (Faz E) ── */
  /** Ses dosyasinda baslangic noktasi (sn) */
  ses_bas_sn?: number;
  /** 0..1 seviye; sahne sesi anlatim sayilir, duck uygulanmaz */
  ses_seviye?: number;
  /** j_cut true ise sesin goruntuden KAC SN once girecegi (varsayilan 0.4) */
  j_cut_sn?: number;
  /** l_cut true ise sesin goruntuden KAC SN sonra bitecegi (varsayilan 0.4) */
  l_cut_sn?: number;
}

/**
 * SES AYARI — master anlatim, ambans ve muzik katmanlari.
 *
 * `anlatim_araliklari` verilirse ducking YALNIZCA o araliklarda uygulanir;
 * verilmezse master anlatim tum videoyu kaplar kabul edilir. Bu ayrim onemli:
 * sessiz bir kapanista muzigin kisik kalmasi yanlis olur.
 */
export interface SesAyari {
  /** Tek master anlatim dosyasi (public/ altinda goreli yol) */
  anlatim?: string;
  anlatim_bas_sn?: number;
  anlatim_seviye?: number;
  /** [[t0,t1],...] saniye — konusmanin oldugu araliklar */
  anlatim_araliklari?: number[][];
  /** Ortam sesleri (dongu) */
  ambans?: string[];
  ambans_seviye?: number;
  /** Yatak muzigi (dongu) */
  muzik?: string;
  muzik_seviye?: number;
  /** Ducking dipleri; verilmezse Ses.tsx DUCK varsayilanlari */
  ducking?: {ambans?: number; muzik?: number};
  /** Anlatimin yapay/deneme oldugunu ACIKCA isaretler (QA raporlar) */
  yapay_ses?: boolean;
  /** Post master hedefi — QA olcumu bu degerlerle karsilastirir */
  hedef_lufs?: number;
  hedef_tp_dbtp?: number;
}

export interface EditorV2Props {
  /**
   * Remotion 4 `Composition` bileseni props tipinin `Record<string, unknown>`
   * ile atanabilir olmasini istiyor. Indeks imzasi bunu saglar; mevcut
   * `VidrushVideo` tipine DOKUNMADAN cozum.
   */
  [key: string]: unknown;
  fps: number;
  genislik: number;
  yukseklik: number;
  gecis: string;
  altyaziStil: string;
  sahneler: EditorSahne[];
  /** Tasarim token'lari (Faz C profil.token_sozlugu) — opsiyonel */
  token?: {
    renk?: Record<string, string>;
    tipografi?: Record<string, unknown>;
    motion?: Record<string, unknown>;
  };
  /** Ses zaman cizelgesi (Faz E). Yoksa video SESSIZ render edilir ve
   *  Python kapisi V2-ANLATIM-YOK uyarisi verir — sessizce gecmez. */
  ses?: SesAyari;
  /** true ise dogrulama hatasi ekrana BASILIR (render durmaz) */
  hatalariGoster?: boolean;
}

/* ════════════════════ DESTEK MATRISI ════════════════════ */

export type DestekDurumu =
  | 'gercek' //         tam uygulanmis
  | 'pseudo' //         yaklastirilmis; kaybi `kayip` alaninda yazili
  | 'ffmpeg-yolu' //    Remotion'da uygulanmaz, hizli yolun isi
  | 'desteklenmiyor'; //  bilincli kapsam disi

export interface DestekKaydi {
  durum: DestekDurumu;
  /** pseudo ise NE KAYBEDILDIGI; gercek ise bos */
  kayip?: string;
  not?: string;
}

/**
 * Bir spec adinin Remotion V2'de nasil ele alindigi.
 * Yeni bilesen eklerken BURAYA da eklenmeli — validator bunu zorunlu kiliyor.
 */
export const DESTEK_MATRISI: Record<string, DestekKaydi> = {
  // ── Kamera ──
  'push-in': {durum: 'gercek'},
  'pull-out': {durum: 'gercek'},
  'pan-right': {durum: 'gercek'},
  'pan-left': {durum: 'gercek'},
  'slow-drift': {durum: 'gercek'},
  static: {durum: 'gercek'},
  handheld: {durum: 'gercek'},
  'soft-zoom': {durum: 'gercek'},

  // ── Katman / derinlik ──
  'parallax-2.5d': {
    durum: 'pseudo',
    kayip:
      'Gercek katman ayrimi icin ayrilmis on/orta/arka gorseller gerekiyor. ' +
      'Onlar yoksa tek gorsel uc olcek katmanina bolunup farkli hizlarda ' +
      'kaydiriliyor (pseudo-depth): derinlik illuzyonu var, gercek oklüzyon yok.',
  },

  // ── Reveal / isik ──
  'masked-reveal': {durum: 'gercek'},
  'track-matte-wipe': {
    durum: 'pseudo',
    kayip:
      'Gercek track matte yazi seklini alfa maskesi yapar; burada dikdortgen ' +
      'maske + yazi kirpma kullaniliyor.',
  },
  'light-sweep': {durum: 'gercek'},
  'film-burn': {durum: 'gercek'},

  // ── Yazi / grafik ──
  'chapter-title': {durum: 'gercek'},
  'lower-third': {durum: 'gercek'},
  'source-label': {durum: 'gercek'},
  callout: {durum: 'gercek'},
  'quote-card': {durum: 'gercek'},
  'document-highlight': {durum: 'gercek'},
  'map-route': {
    durum: 'pseudo',
    kayip:
      'Gercek cografi harita verisi (GeoJSON) yok; stilize soyut harita ' +
      'izgarasi + rota cizimi kullaniliyor. Konum SEMBOLIK, cografi dogru degil.',
    not: 'Cografi dogruluk gerekiyorsa GeoJSON katmani eklenmeli.',
  },
  'data-chart': {durum: 'gercek'},
  'kinetic-title': {durum: 'gercek'},
  'text-in-video': {
    durum: 'gercek',
    not:
      'Yazi kamera transformunu paylasir; goruntuye kilitli durur. ' +
      'Gercek 3D duzlem takibi degil (kamera 2D), duz yuzeyler icin dogru.',
  },

  // ── Doku / grade ──
  grain: {durum: 'gercek'},
  vignette: {durum: 'gercek'},
  grade: {durum: 'gercek'},
  letterbox: {durum: 'gercek'},

  // ── Gecisler ──
  'hard-cut': {durum: 'gercek'},
  crossfade: {durum: 'gercek'},
  karartma: {durum: 'gercek'},
  flash: {durum: 'gercek'},
  'match-cut': {durum: 'gercek', not: 'hard-cut ile ayni; niyet farki'},
  whip: {durum: 'gercek'},
  'zoom-through': {durum: 'gercek'},
  glitch: {durum: 'gercek'},

  // ── Ses montajinda uygulanan (goruntu motorunun isi degil) ──
  'j-cut': {durum: 'ffmpeg-yolu', not: 'ses montajinda uygulanir'},
  'l-cut': {durum: 'ffmpeg-yolu', not: 'ses montajinda uygulanir'},

  // ── ffmpeg tarafinda kalan renk efektleri ──
  chromatic: {durum: 'gercek'},
  'directional-blur': {durum: 'gercek'},
  shake: {durum: 'gercek'},
};

export const DESTEKLENEN_SPECLER = Object.keys(DESTEK_MATRISI);

/* ════════════════════ VALIDATOR ════════════════════ */

export interface DogrulamaSorunu {
  kod: string;
  seviye: 'fail' | 'warn' | 'bilgi';
  scene_id: string;
  beat_id: string;
  spec: string;
  detay: string;
}

export interface DogrulamaSonucu {
  durum: 'PASS' | 'WARN' | 'FAIL';
  sorunlar: DogrulamaSorunu[];
  ozet: {
    sahne: number;
    spec: number;
    gercek: number;
    pseudo: number;
    ffmpegYolu: number;
    bilinmeyen: number;
  };
}

/**
 * Pre-render dogrulama. BILINMEYEN SPEC = FAIL.
 *
 * Neden FAIL (uyari degil): Faz C'de olculdu — sessizce dusen spec, kullanicinin
 * "premium motion" diye odedigi seyin hic uretilmemesi demek. Render'i
 * baslatmadan durdurmak, yanlis videoyu teslim etmekten iyidir.
 */
export const dogrula = (props: EditorV2Props): DogrulamaSonucu => {
  const sorunlar: DogrulamaSorunu[] = [];
  let gercek = 0;
  let pseudo = 0;
  let ffmpegYolu = 0;
  let bilinmeyen = 0;
  let specSayisi = 0;

  const sahneler = props.sahneler || [];
  if (sahneler.length === 0) {
    sorunlar.push({
      kod: 'V2-SAHNE-YOK',
      seviye: 'fail',
      scene_id: '',
      beat_id: '',
      spec: '',
      detay: 'props.sahneler bos',
    });
  }

  sahneler.forEach((sh, i) => {
    const sid = sh.scene_id || `#${i}`;
    const bid = sh.beat_id || `#${i}`;
    if (!sh.beat_id || !sh.scene_id) {
      sorunlar.push({
        kod: 'V2-IZLENEBILIRLIK',
        seviye: 'fail',
        scene_id: sid,
        beat_id: bid,
        spec: '',
        detay: 'beat_id/scene_id zorunlu (izlenebilirlik)',
      });
    }
    if (!(sh.sure > 0)) {
      sorunlar.push({
        kod: 'V2-SURE',
        seviye: 'fail',
        scene_id: sid,
        beat_id: bid,
        spec: '',
        detay: `sure=${sh.sure} (>0 olmali)`,
      });
    }
    if (!sh.medya && sh.tur !== 'image') {
      sorunlar.push({
        kod: 'V2-MEDYA-YOK',
        seviye: 'warn',
        scene_id: sid,
        beat_id: bid,
        spec: '',
        detay: 'medya yolu bos — sentetik zemin cizilecek',
      });
    }

    (sh.motion || []).forEach((sp) => {
      specSayisi += 1;
      const kayit = DESTEK_MATRISI[sp.ad];
      if (!kayit) {
        bilinmeyen += 1;
        sorunlar.push({
          kod: 'V2-BILINMEYEN-SPEC',
          seviye: 'fail',
          scene_id: sid,
          beat_id: bid,
          spec: sp.ad,
          detay:
            `'${sp.ad}' destek matrisinde YOK — sessizce dusmemesi icin ` +
            'render engellendi. Bilesen ekleyin ya da spec adini duzeltin.',
        });
        return;
      }
      if (kayit.durum === 'gercek') gercek += 1;
      else if (kayit.durum === 'pseudo') {
        pseudo += 1;
        sorunlar.push({
          kod: 'V2-PSEUDO',
          seviye: 'bilgi',
          scene_id: sid,
          beat_id: bid,
          spec: sp.ad,
          detay: kayit.kayip || 'yaklastirildi',
        });
      } else if (kayit.durum === 'ffmpeg-yolu') {
        ffmpegYolu += 1;
      } else {
        sorunlar.push({
          kod: 'V2-DESTEKLENMIYOR',
          seviye: 'fail',
          scene_id: sid,
          beat_id: bid,
          spec: sp.ad,
          detay: kayit.not || 'bilincli kapsam disi',
        });
      }
      if (!Array.isArray(sp.easing_bezier) || sp.easing_bezier.length !== 4) {
        sorunlar.push({
          kod: 'V2-EASING',
          seviye: 'warn',
          scene_id: sid,
          beat_id: bid,
          spec: sp.ad,
          detay: 'easing_bezier 4 elemanli olmali; lineere dusulecek',
        });
      }
    });
  });

  const durum: DogrulamaSonucu['durum'] = sorunlar.some((s) => s.seviye === 'fail')
    ? 'FAIL'
    : sorunlar.some((s) => s.seviye === 'warn')
      ? 'WARN'
      : 'PASS';

  return {
    durum,
    sorunlar,
    ozet: {
      sahne: sahneler.length,
      spec: specSayisi,
      gercek,
      pseudo,
      ffmpegYolu,
      bilinmeyen,
    },
  };
};
