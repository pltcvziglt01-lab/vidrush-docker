/* FAZ UI-2 — UZAK GERCEK TARAYICI HATTI (staging konteyneri icinde kosar).
 *
 * `/akis` sayfasini GERCEK Chromium'da, GERCEK staging uclarina karsi
 * ucdan uca kosturur ve MASAUSTU + MOBIL gorsel kanit uretir.
 *
 * ⚠ MAC'E ARTEFAKT YOK: png/json yalnizca konteyner icindeki kanit
 *   dizinine yazilir; kosucu betik onu staging HOST diskine tasir.
 * ⚠ KREDI HARCANMAZ: paranin harcandigi TEK sinir `POST /api/generate`tir.
 *   Bu istek tarayici icinde YAKALANIR ve sunucuya GECIRILMEZ; yerine
 *   ZATEN BITMIS gercek bir isin kimligi doner (test-double). Zincirin
 *   geri kalani — is izleme, QA, imzali indirme, son-3 — GERCEK sunucuya
 *   gider. Sinirin asilmadigi is sayisi ONCE/SONRA karsilastirilarak
 *   OLCULUR, varsayilmaz.
 * ⚠ CREDENTIAL YOK: oturum, on kontrolun sunucu tarafinda urettigi
 *   jetondur. Gecersiz giris denemesi UYDURMA bir kullanici adiyla
 *   yapilir (gercek hesabin hiz siniri kovasi kirletilmez).
 * ⚠ Kimlikler ciktida MASKELI.
 *
 * Bagimlilik YOK: Node 22'nin global `fetch` ve `WebSocket`i + CDP.
 * Kosum: node ui2_uzak_akis.mjs <ayar.json>
 */
import {spawn} from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const AYAR = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const TABAN = process.env.UI2_TABAN || AYAR.taban;
const IS_ID = process.env.UI2_IS_ID || AYAR.is_id;
const KANIT = AYAR.kanit_dizini;
const DURUMLAR = AYAR.durumlar_dizini;
const KOSU = `ui2-${process.pid}`;

/* ── Hukum defteri: PASS / FAIL / OLCULEMEDI AYRI tutulur.
 *    ⚠ "olculemedi" ASLA PASS sayilmaz.                                  */
const hukum = {
  kosu: KOSU, taban: TABAN,
  tenant_maske: AYAR.tenant_maske, is_maske: AYAR.is_maske,
  gecen: 0, basarisiz: [], olculemedi: [],
  is_sayisi_once: 0, is_sayisi_sonra: 0, kanitlar: [],
};

function ok(ad, kosul, kod, detay = "") {
  if (kosul) {
    hukum.gecen++;
    console.log(`  ok   ${ad}`);
  } else {
    hukum.basarisiz.push({ad, kod, detay: String(detay).slice(0, 200)});
    console.log(`  XX   ${ad}  [${kod}] ${String(detay).slice(0, 120)}`);
  }
}

function olculemedi(ad, kod, sebep) {
  hukum.olculemedi.push({ad, kod, sebep: String(sebep).slice(0, 200)});
  console.log(`  --   OLCULEMEDI ${ad}  [${kod}] ${sebep}`);
}

const uyu = (ms) => new Promise((r) => setTimeout(r, ms));

/* ═══════════════ CDP ISTEMCISI (bagimliliksiz) ═══════════════ */
class Cdp {
  constructor(ws) {
    this.ws = ws;
    this.sira = 0;
    this.bekleyen = new Map();
    this.dinleyiciler = [];
    ws.addEventListener("message", (e) => {
      const m = JSON.parse(e.data);
      if (m.id && this.bekleyen.has(m.id)) {
        const {coz, red} = this.bekleyen.get(m.id);
        this.bekleyen.delete(m.id);
        m.error ? red(new Error(JSON.stringify(m.error))) : coz(m.result);
      } else if (m.method) {
        for (const d of this.dinleyiciler) d(m);
      }
    });
  }
  static async ac(url) {
    const ws = new WebSocket(url);
    await new Promise((coz, red) => {
      ws.addEventListener("open", coz, {once: true});
      ws.addEventListener("error", () => red(new Error("ws-acilamadi")),
                          {once: true});
    });
    return new Cdp(ws);
  }
  gonder(yontem, params = {}, sessionId) {
    const id = ++this.sira;
    const p = new Promise((coz, red) => this.bekleyen.set(id, {coz, red}));
    this.ws.send(JSON.stringify(
        sessionId ? {id, method: yontem, params, sessionId}
                  : {id, method: yontem, params}));
    return p;
  }
  dinle(fn) { this.dinleyiciler.push(fn); }
}

/* ═══════════════ TARAYICI ═══════════════ */
async function tarayiciAc() {
  const profil = fs.mkdtempSync("/tmp/ui2-profil-");
  const p = spawn("chromium", [
    "--headless=new", "--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage",
    "--hide-scrollbars", "--remote-debugging-port=0",
    `--user-data-dir=${profil}`, "about:blank",
  ], {stdio: ["ignore", "pipe", "pipe"]});
  const uc = await new Promise((coz, red) => {
    let tampon = "";
    const zaman = setTimeout(() => red(new Error("chromium-acilmadi")), 30000);
    p.stderr.on("data", (d) => {
      tampon += d.toString();
      const m = tampon.match(/ws:\/\/[^\s]+/);
      if (m) { clearTimeout(zaman); coz(m[0]); }
    });
  });
  return {surec: p, cdp: await Cdp.ac(uc)};
}

async function sayfaAc(tarayici) {
  const {targetId} = await tarayici.cdp.gonder("Target.createTarget",
                                               {url: "about:blank"});
  const {sessionId} = await tarayici.cdp.gonder(
      "Target.attachToTarget", {targetId, flatten: true});
  return sessionId;
}

/* ═══════════════ SAYFA YARDIMCILARI ═══════════════ */
function sayfaKur(cdp, oturum) {
  const g = (y, p = {}) => cdp.gonder(y, p, oturum);
  return {
    g,
    async deger(ifade) {
      const r = await g("Runtime.evaluate",
                        {expression: ifade, returnByValue: true,
                         awaitPromise: true});
      if (r.exceptionDetails) throw new Error(r.exceptionDetails.text);
      return r.result.value;
    },
    async git(yol) {
      const yuklendi = new Promise((coz) => {
        const d = (m) => {
          if (m.method === "Page.loadEventFired" && m.sessionId === oturum) coz();
        };
        cdp.dinle(d);
      });
      await g("Page.navigate", {url: `${TABAN}${yol}`});
      await Promise.race([yuklendi, uyu(20000)]);
    },
    async kanit(pasta, no, ad) {
      const r = await g("Page.captureScreenshot",
                        {format: "png", captureBeyondViewport: true});
      const dosya = path.join(KANIT, `${pasta}-${no}-${ad}.png`);
      fs.writeFileSync(dosya, Buffer.from(r.data, "base64"));
      hukum.kanitlar.push(path.basename(dosya));
      return dosya;
    },
  };
}

/** Kosul saglanana kadar bekle; saglanmazsa false doner (asla sonsuz degil). */
async function bekle(s, ifade, sn = 45) {
  const bitis = Date.now() + sn * 1000;
  while (Date.now() < bitis) {
    try { if (await s.deger(ifade)) return true; } catch { /* yukleniyor */ }
    await uyu(500);
  }
  return false;
}

function isSayisi() {
  try { return fs.readdirSync(DURUMLAR).filter((a) => a.endsWith(".json")).length; }
  catch { return -1; }
}

/* ═══════════════ TEK PASTA (masaustu | mobil) ═══════════════ */
async function pastaKos(tarayici, pasta, olcu) {
  console.log(`\n══ ${pasta.toUpperCase()} (${olcu.width}x${olcu.height}) ══`);
  const oturum = await sayfaAc(tarayici);
  const s = sayfaKur(tarayici.cdp, oturum);
  const konsolHatalari = [];
  tarayici.cdp.dinle((m) => {
    if (m.sessionId !== oturum) return;
    if (m.method === "Runtime.exceptionThrown") {
      konsolHatalari.push(m.params.exceptionDetails?.text || "istisna");
    }
    if (m.method === "Log.entryAdded" && m.params.entry?.level === "error") {
      const t = m.params.entry.text || "log-hata";
      const u = m.params.entry.url || "";
      // ⚠ favicon 404'u sayfa hatasi DEGILDIR (sayfa favicon bildirmez).
      if (!/favicon\.ico/.test(u + t)) konsolHatalari.push(`${t} ${u}`.trim());
    }
    if (m.method === "Runtime.consoleAPICalled" && m.params.type === "error") {
      konsolHatalari.push("console.error");
    }
  });
  await s.g("Page.enable");
  await s.g("Runtime.enable");
  await s.g("Log.enable");
  await s.g("Network.enable");
  await s.g("Emulation.setDeviceMetricsOverride", {
    width: olcu.width, height: olcu.height,
    deviceScaleFactor: olcu.dsf, mobile: olcu.mobil,
  });
  if (olcu.mobil) {
    await s.g("Emulation.setTouchEmulationEnabled",
              {enabled: true, maxTouchPoints: 5});
  }

  /* ── 1) KIMLIK KAPISI: cerezsiz `/akis` GIRIS formu vermeli ── */
  await s.g("Network.clearBrowserCookies");
  await s.git("/akis");
  const kimliksiz = await s.deger(`(() => ({
    giris: !!document.querySelector('form#f input[name="parola"]'),
    akis: !!document.querySelector('#akis-form'),
  }))()`);
  await s.kanit(pasta, "01", "kimliksiz");
  ok(`${pasta}: kimliksiz /akis GIRIS formu veriyor`,
     kimliksiz.giris && !kimliksiz.akis, "UI2-KIMLIK-KAPISI-ACIK",
     JSON.stringify(kimliksiz));

  /* ── 2) GECERSIZ giris STABIL 401 ── */
  const giriskodu = new Promise((coz) => {
    tarayici.cdp.dinle((m) => {
      if (m.sessionId === oturum && m.method === "Network.responseReceived"
          && m.params.response.url.endsWith("/api/giris")) {
        coz(m.params.response.status);
      }
    });
  });
  await s.deger(`(() => {
    const f = document.querySelector('form#f');
    f.querySelector('[name="kullanici"]').value = 'ui2-gecersiz-${KOSU}';
    f.querySelector('[name="parola"]').value = 'ui2-gecersiz-parola-yok';
    f.requestSubmit();
    return true;
  })()`);
  const kod = await Promise.race([giriskodu, uyu(15000).then(() => 0)]);
  await s.kanit(pasta, "02", "hatali-giris");
  ok(`${pasta}: gecersiz giris STABIL 401 donuyor`, kod === 401,
     "UI2-GECERSIZ-GIRIS-STABIL-DEGIL", `durum=${kod}`);

  /* ── 3) CREDENTIALSIZ oturum cerezi ── */
  await s.g("Network.setCookie", {
    name: AYAR.cerez_adi, value: AYAR.jeton, domain: "127.0.0.1",
    path: "/", httpOnly: true, secure: false, sameSite: "Lax",
  });
  /* ⚠ CSRF cerezi: gercek giris gibi JS'ten OKUNABILIR kurulur
   * (double-submit sartı). Yetki hala HttpOnly oturum cerezindedir. */
  await s.g("Network.setCookie", {
    name: AYAR.csrf_cerez_adi, value: AYAR.csrf, domain: "127.0.0.1",
    path: "/", httpOnly: false, secure: false, sameSite: "Lax",
  });

  /* ⚠ Konsol olcumu BURADAN baslar: yukaridaki 401 KASITLIDIR (gecersiz
   * giris negatif testi) ve uygulama hatasi olarak sayilmaz. */
  konsolHatalari.length = 0;

  /* ── 4) UCRETLI SINIR: /api/generate YAKALANIR, gecirilmez ── */
  await s.g("Fetch.enable", {
    patterns: [{urlPattern: "*/api/generate*", requestStage: "Request"}],
  });
  let yakalandi = null;
  let generateSayaci = 0;
  let tercihYazimiBozuk = false;
  tarayici.cdp.dinle(async (m) => {
    if (m.method !== "Fetch.requestPaused" || m.sessionId !== oturum) return;
    const istek = m.params.request;
    /* ⚠ FAIL-OPEN SINAMASI: tercih yazimi 500 dondurulur. Uretim
     * DURMALIDIR; `/api/generate` HIC gitmemelidir. */
    if (tercihYazimiBozuk && istek.url.includes("/api/kaynak-tercihi")) {
      await tarayici.cdp.gonder("Fetch.fulfillRequest", {
        requestId: m.params.requestId, responseCode: 500,
        responseHeaders: [{name: "Content-Type", value: "application/json"}],
        body: Buffer.from('{"detail":"sinama"}', "utf8").toString("base64"),
      }, oturum);
      return;
    }
    if (!istek.url.includes("/api/generate")) return;
    generateSayaci += 1;
    yakalandi = {
      url: istek.url,
      alanlar: [...new Set([...(istek.postData || "")
          .matchAll(/name="([^"]+)"/g)].map((x) => x[1]))],
    };
    /* ⚠ TEST-DOUBLE: istek sunucuya ULASMAZ (kredi yanmaz). Yerine
     * ZATEN BITMIS gercek bir isin kimligi donulur; zincirin geri
     * kalani o gercek isle GERCEK sunucudan olculur. */
    const govde = JSON.stringify({
      ok: true, job_id: IS_ID, id: IS_ID, is_id: IS_ID,
      durum: "kuyrukta", status: "queued", ilerleme: 0, progress: 0,
      saglayici: "test-double",
      saglayici_fallback: "UI-2: ucretli sinir gecilmedi ($0.00)",
    });
    await tarayici.cdp.gonder("Fetch.fulfillRequest", {
      requestId: m.params.requestId, responseCode: 200,
      responseHeaders: [{name: "Content-Type", value: "application/json"}],
      body: Buffer.from(govde, "utf8").toString("base64"),
    }, oturum);
  });

  /* ── 5) AKIS sayfasi (girisli) ── */
  await s.git("/akis");
  const hazir = await bekle(s,
      `document.querySelector('#akis-tenant')?.textContent.startsWith('Hesap:')`);
  ok(`${pasta}: girisli /akis akis sayfasini veriyor`, hazir,
     "UI2-KIMLIK-KAPISI-ACIK", "oturum kurulamadi");
  if (!hazir) return konsolHatalari;

  const yapi = await s.deger(`(() => {
    const alanlar = [...document.querySelectorAll('#akis-form textarea, #akis-form select')];
    return {
      adim: document.querySelectorAll('[data-adim]').length,
      etiketli: alanlar.filter(e => e.labels && e.labels.length === 1).length,
      alan: alanlar.length,
      progressbar: document.querySelectorAll('[role="progressbar"]').length,
      canli: document.querySelectorAll('[aria-live]').length,
      tasma: document.documentElement.scrollWidth - window.innerWidth,
      dugme: Math.round(document.querySelector('#akis-form button')
                        ?.getBoundingClientRect().height || 0),
      cerez: document.cookie,
      kaynak_izi: /sifreli_token|parola_hash|IMZA_ANAHTARI|OTURUM_ANAHTARI/
                  .test(document.documentElement.outerHTML),
    };
  })()`);
  await s.kanit(pasta, "03", "akis");
  ok(`${pasta}: 6 adim gostergesi var`, yapi.adim === 6, "UI2-ADIM-EKSIK",
     `adim=${yapi.adim}`);
  ok(`${pasta}: her form alani TAM 1 label[for] ile bagli`,
     yapi.alan === 3 && yapi.etiketli === 3, "UI2-ETIKET-BAGI-YOK",
     `alan=${yapi.alan} etiketli=${yapi.etiketli}`);
  ok(`${pasta}: role=progressbar TEK`, yapi.progressbar === 1,
     "UI2-PROGRESSBAR-YOK", `adet=${yapi.progressbar}`);
  ok(`${pasta}: yatay tasma YOK (scrollWidth <= innerWidth)`,
     yapi.tasma <= 1, "UI2-MOBIL-YATAY-TASMA", `tasma=${yapi.tasma}px`);
  ok(`${pasta}: birincil dugme dokunma hedefi >= 44 px`, yapi.dugme >= 44,
     "UI2-DOKUNMA-HEDEFI-KUCUK", `${yapi.dugme}px`);
  ok(`${pasta}: oturum cerezi JS'ten OKUNAMIYOR (HttpOnly)`,
     !yapi.cerez.includes(AYAR.cerez_adi), "UI2-TOKEN-SIZINTISI",
     "cerez JS'te gorunuyor");
  ok(`${pasta}: canli sayfa kaynaginda token/parola izi YOK`,
     yapi.kaynak_izi === false, "UI2-TOKEN-SIZINTISI", "kaynakta iz var");

  /* ⚠ `/api/kaynak-tercihi` YAKALANMAZ: ucretsizdir ve GERCEK sunucuya
   * gitmelidir — kaydin gercekten yazildigini ancak boyle olceriz. */
  let tercihCevabi = null;
  tarayici.cdp.dinle(async (m) => {
    if (m.method !== "Network.responseReceived" || m.sessionId !== oturum) return;
    if (!m.params.response.url.endsWith("/api/kaynak-tercihi")) return;
    if (m.params.response.status !== 200) return;
    try {
      const r = await tarayici.cdp.gonder("Network.getResponseBody",
                                          {requestId: m.params.requestId},
                                          oturum);
      tercihCevabi = JSON.parse(r.body);
    } catch { /* govde henuz hazir degil */ }
  });

  /* ── 6) AYARLAR: metin + kurgu + kaynak; kredi metni CANLI degismeli ── */
  const kredi = await s.deger(`(() => {
    const d = (el, t) => el.dispatchEvent(new Event(t, {bubbles: true}));
    const m = document.querySelector('#akis-metin');
    m.value = 'UI-2 uzak tarayici dogrulamasi icin yeterince uzun ornek metin.';
    d(m, 'input');
    const once = {
      metin: document.querySelector('#akis-kredi').textContent,
      onay: document.querySelector('#akis-kredi').dataset.kredi_onayi || '',
    };
    const e = document.querySelector('#akis-edit');
    e.value = 'yuksek'; d(e, 'change');
    const k = document.querySelector('#akis-kaynak');
    k.value = 'ucretsiz'; d(k, 'change');
    return {once, sonra: {
      metin: document.querySelector('#akis-kredi').textContent,
      onay: document.querySelector('#akis-kredi').dataset.kredi_onayi || '',
    }, adim: document.querySelector('[data-adim="kaynak"]')
             ?.getAttribute('aria-current')};
  })()`);
  /* ⚠ FAZ UI-3: metin artik SUNUCUNUN gercek cevabindan yazilir; bu bir
   * ag gidis-donusudur, beklenir. */
  const krediYazildi = await bekle(s,
      `document.querySelector('#akis-kredi')?.dataset.tercih === 'ucretsiz'`,
      20);
  const krediSon = await s.deger(`(() => {
    const e = document.querySelector('#akis-kredi');
    return {metin: e.textContent, onay: e.dataset.kredi_onayi || '',
            tercih: e.dataset.tercih || ''};
  })()`);
  await s.kanit(pasta, "04", "ayarlar");
  ok(`${pasta}: kaynak secimi kredi metnini CANLI degistiriyor`,
     kredi.once.metin !== krediSon.metin && krediSon.onay === "gerekmez",
     "UI2-KREDI-METNI-DEGISMIYOR", JSON.stringify(krediSon));
  ok(`${pasta}: kredi metni SUNUCUNUN karari (istemci tahmini degil)`,
     krediYazildi && krediSon.tercih === "ucretsiz",
     "UI2-KREDI-METNI-DEGISMIYOR", JSON.stringify(krediSon));
  ok(`${pasta}: adim gostergesi secime gore ilerliyor`,
     kredi.adim === "step", "UI2-ADIM-EKSIK", `aria-current=${kredi.adim}`);

  /* ── 7) URETIM: istek YAKALANIR, sunucuya GITMEZ ── */
  hukum.is_sayisi_once = isSayisi();
  await s.deger(`(document.querySelector('#akis-form').requestSubmit(), true)`);
  const yakalandiMi = await (async () => {
    const bitis = Date.now() + 20000;
    while (Date.now() < bitis) { if (yakalandi) return true; await uyu(300); }
    return false;
  })();
  await uyu(1500);
  hukum.is_sayisi_sonra = isSayisi();
  ok(`${pasta}: /api/generate tarayicida YAKALANDI`, yakalandiMi,
     "UI2-GENERATE-SUNUCUYA-SIZDI", "istek yakalanamadi");
  ok(`${pasta}: UCRETLI SINIR GECILMEDI — yeni is OLUSMADI ($0.00)`,
     hukum.is_sayisi_sonra === hukum.is_sayisi_once,
     "UI2-GENERATE-SUNUCUYA-SIZDI",
     `once=${hukum.is_sayisi_once} sonra=${hukum.is_sayisi_sonra}`);

  if (yakalandi) {
    /* ⚠ FAZ UI-3: 22 alanlik sozlesme BUYUMEMELI. Kaynak secimi uretim
     * istegine EKLENMEZ; ayri `/api/kaynak-tercihi` ucuna yazilir ve
     * `/api/generate` onu tenant kaydindan okur. */
    const bekleniyor = ["session", "story", "tur", "edit", "sure_dk", "altyazi"];
    ok(`${pasta}: generate govdesi 22 alan sozlesmesinin ALT KUMESI`,
       bekleniyor.every((a) => yakalandi.alanlar.includes(a)),
       "UI2-GENERATE-SUNUCUYA-SIZDI", yakalandi.alanlar.join(","));
    ok(`${pasta}: generate govdesine YENI ALAN EKLENMEDI `
       + `(kaynak_tercihi govdede YOK)`,
       !yakalandi.alanlar.includes("kaynak_tercihi"),
       "UI2-KAYNAK-TERCIHI-SUNUCUYA-GITMIYOR", yakalandi.alanlar.join(","));
    ok(`${pasta}: kaynak secimi GERCEK sunucuya ayri uctan ULASTI `
       + `(/api/kaynak-tercihi)`,
       tercihCevabi && tercihCevabi.tercih === "ucretsiz"
         && tercihCevabi.kredi_tuketilir === false,
       "UI2-KAYNAK-TERCIHI-SUNUCUYA-GITMIYOR", JSON.stringify(tercihCevabi));
  }

  /* ── 8) IZLEME + QA (GERCEK /api/job/{id}) ── */
  const izlendi = await bekle(s,
      `document.querySelector('#akis-kalite')?.dataset.teslim_ok !== undefined`,
      60);
  const sonuc = await s.deger(`(() => {
    const p = document.querySelector('#akis-ilerleme');
    const k = document.querySelector('#akis-kalite');
    const a = document.querySelector('#akis-indirme a');
    return {
      yuzde: p?.getAttribute('aria-valuenow'),
      valuetext: p?.getAttribute('aria-valuetext') || '',
      kalite: k?.dataset.kalite || '', teslim_ok: k?.dataset.teslim_ok,
      indirme: a ? a.getAttribute('href') : '',
      saglayici: document.querySelector('#akis-saglayici')?.textContent || '',
      provenans: document.querySelector('#akis-provenans')?.textContent || '',
    };
  })()`);
  ok(`${pasta}: GERCEK is izlendi, ilerleme yazildi (aria-valuenow)`,
     izlendi && Number(sonuc.yuzde) > 0, "UI2-IS-IZLEME-YOK",
     `yuzde=${sonuc.yuzde}`);
  ok(`${pasta}: QA hukmu ekranda (teslim_ok + kalite)`,
     sonuc.teslim_ok === "0" || sonuc.teslim_ok === "1", "UI2-QA-GORUNMUYOR",
     `teslim_ok=${sonuc.teslim_ok}`);

  /* ── 9) IMZALI INDIRME: 200 / 401 / 403 ── */
  const imzali = String(sonuc.indirme || "");
  ok(`${pasta}: indirme baglantisi IMZALI (ciktilar/... exp+sig)`,
     imzali.startsWith("ciktilar/") && /[?&]sig=/.test(imzali)
       && /[?&]exp=/.test(imzali),
     "UI2-IMZASIZ-INDIRME",
     `sig=${/[?&]sig=/.test(imzali)} exp=${/[?&]exp=/.test(imzali)}`);
  if (imzali && /[?&]sig=/.test(imzali)) {
    const tam = new URL(imzali, TABAN + "/");
    const cerez = {Cookie: `${AYAR.cerez_adi}=${AYAR.jeton}`};
    const durum = async (u, h) => {
      const r = await fetch(u, {headers: h, redirect: "manual"});
      try { await r.body?.cancel(); } catch { /* govde okunmadi */ }
      return r.status;
    };
    const d200 = await durum(tam, cerez);
    const dAnonim = await durum(tam, {});
    const bozuk = new URL(tam);
    const s0 = bozuk.searchParams.get("sig");
    bozuk.searchParams.set("sig", (s0[0] === "A" ? "B" : "A") + s0.slice(1));
    const d403 = await durum(bozuk, cerez);
    ok(`${pasta}: imzali URL oturumla 200`, d200 === 200,
       "UI2-IMZALI-URL-200-DEGIL", `durum=${d200}`);
    ok(`${pasta}: imzali URL OTURUMSUZ erisime KAPALI (401/403)`,
       dAnonim === 401 || dAnonim === 403, "UI2-IMZASIZ-ERISIM-ACIK",
       `durum=${dAnonim}`);
    ok(`${pasta}: imza BOZULUNCA 403`, d403 === 403,
       "UI2-IMZASIZ-ERISIM-ACIK", `durum=${d403}`);
  } else {
    olculemedi(`${pasta}: imzali URL 200/401/403`, "UI2-IMZASIZ-INDIRME",
               "baglanti uretilmedi");
  }

  /* ── 10) SON-3 (GERCEK /api/kutuphane) ── */
  const son3 = await s.deger(`(() => {
    const e = document.querySelector('#akis-kutuphane');
    return {adet: e.querySelectorAll('li').length,
            metin: (e.textContent || '').slice(0, 80),
            kredi: [...e.querySelectorAll('li')]
                   .filter(l => /kredi harc/.test(l.textContent)).length};
  })()`);
  await s.kanit(pasta, "05", "sonuc");
  if (son3.adet > 0) {
    ok(`${pasta}: son-3 listesi GERCEK kutuphaneden doldu`, son3.adet <= 3,
       "UI2-SON3-YOK", `adet=${son3.adet}`);
    ok(`${pasta}: son-3 her satirda kredi durumu yaziyor`,
       son3.kredi === son3.adet, "UI2-SON3-YOK",
       `kredi=${son3.kredi}/${son3.adet}`);
  } else {
    olculemedi(`${pasta}: son-3 icerigi`, "UI2-SON3-YOK",
               `liste bos: "${son3.metin}"`);
  }

  hukum.konsol = {...(hukum.konsol || {}), [pasta]: konsolHatalari.slice(0, 10)};
  ok(`${pasta}: akis uygulamasinda konsol hatasi YOK`,
     konsolHatalari.length === 0, "UI2-KONSOL-HATASI",
     konsolHatalari.slice(0, 2).join(" | "));

  /* ── 11) FAIL-OPEN SINAMASI (en sonda: kasitli 500 konsolu kirletir) ──
   * ⚠ Tercih yazimi basarisizken uretime DEVAM ETMEK, isi ESKI tercihle
   * baslatir ve kullanicinin secimini SESSIZCE ihlal eder. Bu adim
   * uretimin GERCEKTEN durdugunu tarayicida kanitlar.                   */
  // ⚠ Desen YALNIZ bu adimda genisletilir. Surekli acik birakilirsa
  // normal akistaki tercih yazimi duraklatilip HIC surdurulmez ve fetch
  // asili kalir (ilk kosumda tam bunu olctuk: zincir koptu).
  await s.g("Fetch.enable", {
    patterns: [{urlPattern: "*/api/generate*", requestStage: "Request"},
               {urlPattern: "*/api/kaynak-tercihi*", requestStage: "Request"}],
  });
  tercihYazimiBozuk = true;
  const genOnce = generateSayaci;
  await s.deger(`(() => {
    const k = document.querySelector('#akis-kaynak');
    k.value = 'magnific';
    k.dispatchEvent(new Event('change', {bubbles: true}));
    return true;
  })()`);
  await uyu(1500);
  await s.deger(`(document.querySelector('#akis-form').requestSubmit(), true)`);
  await uyu(3000);
  const durdu = await s.deger(
      `(document.querySelector('#akis-durum')?.textContent || '')`);
  ok(`${pasta}: tercih yazilamayinca /api/generate HIC GITMEDI `
     + `(fail-open YOK)`,
     generateSayaci === genOnce, "UI2-TERCIH-YAZILAMADI-FAIL-OPEN",
     `once=${genOnce} sonra=${generateSayaci}`);
  ok(`${pasta}: durus STABIL KODLA gorunur `
     + `(UI3-KAYNAK-TERCIHI-YAZILAMADI)`,
     durdu.includes("UI3-KAYNAK-TERCIHI-YAZILAMADI"),
     "UI2-TERCIH-YAZILAMADI-FAIL-OPEN", durdu.slice(0, 80));
  await s.kanit(pasta, "06", "fail-closed");
  tercihYazimiBozuk = false;
  await s.g("Fetch.enable", {
    patterns: [{urlPattern: "*/api/generate*", requestStage: "Request"}],
  });
  return konsolHatalari;
}

/* ═══════════════ ANA ═══════════════ */
const tarayici = await tarayiciAc();
try {
  await pastaKos(tarayici, "masaustu",
                 {width: 1280, height: 800, dsf: 1, mobil: false});
  await pastaKos(tarayici, "mobil",
                 {width: 390, height: 844, dsf: 3, mobil: true});
} finally {
  try { tarayici.surec.kill("SIGKILL"); } catch { /* kapandi */ }
}

fs.writeFileSync(path.join(KANIT, "sonuc.json"),
                 JSON.stringify(hukum, null, 2));
console.log(`\n${"=".repeat(60)}`);
console.log(`GECEN: ${hukum.gecen}   BASARISIZ: ${hukum.basarisiz.length}   `
            + `OLCULEMEDI: ${hukum.olculemedi.length}`);
console.log(`KANIT: ${hukum.kanitlar.length} png + sonuc.json -> ${KANIT}`);
for (const b of hukum.basarisiz) console.log(`  XX [${b.kod}] ${b.ad}`);
for (const b of hukum.olculemedi) console.log(`  -- [${b.kod}] ${b.ad}`);
process.exit(hukum.basarisiz.length ? 1 : 0);
