/* FAZ UI-1 — TEK AKIS istemcisi.
 *
 * Metin -> Stil -> Kaynak -> Uretim -> Kalite -> Indirme
 *
 * ⚠ CSS-ONLY DEGIL: her adim GERCEK staging ucuna baglidir
 *   /api/oturum · /api/generate · /api/job/{id} · /api/kutuphane
 * ⚠ 22 alanlik generate sozlesmesi DEGISMEZ; bu akis onun bir ALT KUMESINI
 *   gonderir, yeni alan EKLEMEZ.
 * ⚠ GUVENLIK: oturum cerezi HttpOnly'dir ve BU DOSYA ONU OKUMAZ
 *   (cerez JS'ten HIC okunmaz). Saglayici TOKEN'i istemciye gelmez;
 *   sunucu yalnizca `saglayici` adi + `fallback` nedenini doner.
 * ⚠ Indirme baglantisi HER ZAMAN sunucudan gelen SIGNED `video_url`dir;
 *   ham `ciktilar/...` yolu BU DOSYADA KURULMAZ (o yol 401/403 doner).
 */
const $ = (s) => document.querySelector(s);
const durumBolgesi = () => $("#akis-durum");

function yaz(mesaj, hataMi = false) {
  const b = durumBolgesi();
  if (!b) return;
  b.textContent = mesaj;
  b.dataset.hata = hataMi ? "1" : "0";
}

function adimAktif(ad) {
  document.querySelectorAll("[data-adim]").forEach((el) => {
    el.setAttribute("aria-current", el.dataset.adim === ad ? "step" : "false");
  });
}

function ilerlemeYaz(yuzde, etiket) {
  const p = $("#akis-ilerleme");
  if (!p) return;
  const v = Math.max(0, Math.min(100, Number(yuzde) || 0));
  p.setAttribute("aria-valuenow", String(v));
  p.setAttribute("aria-valuetext", `${etiket || ""} %${v}`);
  p.style.setProperty("--yuzde", `${v}%`);
  const t = $("#akis-ilerleme-metin");
  if (t) t.textContent = `${etiket || ""} — %${v}`;
}

/* ── OTURUM ── */
async function oturumKontrol() {
  const r = await fetch("/api/oturum");
  const d = await r.json().catch(() => ({}));
  if (!d.girisli) {
    yaz("Giriş gerekli — giriş sayfasına yönlendiriliyorsunuz.", true);
    location.href = "/giris";
    return null;
  }
  const e = $("#akis-tenant");
  if (e) e.textContent = `Hesap: ${d.tenant_id}`;
  return d;
}

/* ── KREDI ONAYI GORUNURLUGU ──
 * ⚠ Kullanici KREDI HARCANACAGINI once bilmelidir. Sunucu saglayici
 * kararini `/api/generate` cevabinda doner; secim aninda ise politikayi
 * ACIKCA yaziyoruz. "Ucretsiz" secildiyse kredi harcanmaz.            */
function krediUyarisiGuncelle() {
  const k = $("#akis-kaynak")?.value || "otomatik";
  const u = $("#akis-kredi");
  if (!u) return;
  if (k === "ucretsiz") {
    u.textContent = "Kredi harcanmaz — yalnızca ücretsiz stok kullanılır.";
    u.dataset.kredi_onayi = "gerekmez";
  } else if (k === "magnific") {
    u.textContent =
      "Magnific bağlantısı ONAYLI ve KREDİLİ ise kullanılır; " +
      "değilse ücretsiz stoğa DÜŞÜLÜR ve nedeni gösterilir.";
    u.dataset.kredi_onayi = "gerekli";
  } else {
    u.textContent =
      "Otomatik: onaylı+kredili bağlantı varsa o, yoksa ücretsiz stok.";
    u.dataset.kredi_onayi = "kosullu";
  }
}

/* ── KAYNAK TERCIHI: SUNUCUYA YAZ, GERCEGI GERI OKU ──
 * ⚠ FAZ UI-3: UI-2 arayuzun "Kredi harcanmaz" dedigini ama secimin
 * sunucuya HIC ulasmadigini olctu (`UI2-KAYNAK-TERCIHI-SUNUCUYA-GITMIYOR`).
 * Artik secim tenant'in saglayici kaydina yazilir ve ekrana SUNUCUNUN
 * verdigi gercek karar yazilir — tahmin DEGIL.
 * ⚠ `/api/generate` sozlesmesi (22 alan) DEGISMEDI.                     */
/* ⚠ Double-submit CSRF: `vr_csrf` cerezi BILEREK JS'ten okunabilir.
 * YETKI o cerezde DEGILDIR — yetki HttpOnly OTURUM cerezindedir ve bu
 * dosya ONU HIC OKUMAZ (adini bile tasimaz). Burada okunan YALNIZCA
 * CSRF jetonudur ve cerez okumasi YALNIZ burada yapilir.               */
function csrfJetonu() {
  return (document.cookie.match(/(?:^|;\s*)vr_csrf=([^;]*)/) || [])[1] || "";
}

async function kaynakTercihiYaz() {
  const k = $("#akis-kaynak")?.value || "otomatik";
  const u = $("#akis-kredi");
  const fd = new FormData();
  fd.append("tercih", k);
  try {
    const r = await fetch("/api/kaynak-tercihi", {
      method: "POST", body: fd,
      headers: {"x-csrf-token": csrfJetonu()},
    });
    if (!r.ok) throw new Error(String(r.status));
    const d = await r.json();
    if (u) {
      u.textContent =
        `Kaynak: ${d.saglayici}` +
        (d.saglayici_fallback ? ` (düşüş: ${d.saglayici_fallback})` : "") +
        ` — ${d.kredi_tuketilir ? "kredi harcanabilir" : "kredi harcanmaz"}`;
      u.dataset.kredi_onayi = d.kredi_tuketilir ? "gerekli" : "gerekmez";
      u.dataset.tercih = d.tercih;
    }
    return d;
  } catch (e) {
    // ⚠ SESSIZ BASARI YOK: yazilamadiysa kullanici bunu GORUR.
    if (u) {
      u.textContent =
        "Kaynak tercihi sunucuya YAZILAMADI — üretim BAŞLATILMADI " +
        "(seçimin sessizce yok sayılmasın diye). Sayfayı yenileyip " +
        "tekrar deneyin.";
      u.dataset.kredi_onayi = "bilinmiyor";
    }
    return null;
  }
}

/* ── URETIM BASLAT ── */
async function uretimBaslat(ev) {
  ev.preventDefault();
  const metin = ($("#akis-metin")?.value || "").trim();
  if (metin.length < 20) {
    yaz("Metin çok kısa (en az 20 karakter).", true);
    $("#akis-metin")?.focus();
    return;
  }
  const fd = new FormData();
  // ⚠ 22 alanlik sozlesmenin ALT KUMESI — yeni alan EKLENMEZ.
  fd.append("session", oturumEtiketi());
  fd.append("story", metin);
  fd.append("tur", "documentary");
  fd.append("edit", $("#akis-edit")?.value || "orta");
  fd.append("sure_dk", "1");
  fd.append("altyazi", "1");
  // ⚠ FAZ UI-3: kaynak secimi BU ISTEGE EKLENMEZ — 22 alanlik sozlesme
  // buyumez. Secim `POST /api/kaynak-tercihi` ile tenant'in saglayici
  // kaydina yazilir ve `/api/generate` onu ORADAN okur.
  // ⚠ FAIL-OPEN YASAK: yazma basarisizsa uretime DEVAM EDILMEZ. Devam
  // etmek isi ESKI (kayitli) tercihle baslatirdi ve kullanicinin secimini
  // SESSIZCE ihlal ederdi — "ucretsiz" secen kullanicinin kredisi
  // yanabilirdi. Durus DETERMINISTIKTIR ve kodu GORUNURDUR.
  const tercihSonuc = await kaynakTercihiYaz();
  if (!tercihSonuc) {
    yaz("UI3-KAYNAK-TERCIHI-YAZILAMADI — kaynak seçimin sunucuya "
        + "yazılamadı, üretim BAŞLATILMADI (seçimin yok sayılmasın diye). "
        + "Bağlantını kontrol edip tekrar dene.", true);
    return;
  }

  adimAktif("uretim");
  yaz("Üretim başlatılıyor…");
  const r = await fetch("/api/generate", {method: "POST", body: fd});
  if (r.status === 401) {
    location.href = "/giris";
    return;
  }
  const d = await r.json().catch(() => ({}));
  if (!r.ok) {
    yaz(`Başlatılamadı: ${d.detail || r.status}`, true);
    return;
  }
  saglayiciYaz(d);
  izle(d.job_id || d.id);
}

function oturumEtiketi() {
  // ⚠ Bu YETKI DEGILDIR; yetki HttpOnly cerezden gelir. Yalnizca eski
  // `session` alan sozlesmesini doldurur.
  let s = localStorage.getItem("akis_oturum_etiketi");
  if (!s) {
    s = `ui1${Math.random().toString(36).slice(2, 10)}`;
    localStorage.setItem("akis_oturum_etiketi", s);
  }
  return s;
}

/* ── SAGLAYICI / PROVENANCE / MALIYET ── */
function saglayiciYaz(d) {
  const e = $("#akis-saglayici");
  if (!e) return;
  const sag = d.saglayici || "-";
  const fb = d.saglayici_fallback || "";
  const kredi = sag === "wikimedia" ? "kredi harcanmadı" : "kredi kullanılabilir";
  e.textContent = `Sağlayıcı: ${sag}${fb ? ` (düşüş: ${fb})` : ""} — ${kredi}`;
  e.dataset.kredi = kredi;
  e.dataset.kredi_onayi = fb ? "dusuldu" : "gecerli";
}

function provenansYaz(is) {
  const e = $("#akis-provenans");
  if (!e) return;
  const p = (is.teslim && is.teslim.provenance) || is.provenance || null;
  const kaynaklar = (is.attribution || []).length;
  const maliyet =
    (is.research && is.research.usd != null) ? `$${is.research.usd}` : "ölçülmedi";
  e.textContent =
    `Provenance: ${p ? (p.provider_used || "-") : "kayıtta yok"} · ` +
    `atıf ${kaynaklar} · maliyet ${maliyet}`;
}

/* ── IS IZLEME ── */
async function izle(isId) {
  if (!isId) {
    yaz("İş kimliği alınamadı.", true);
    return;
  }
  const r = await fetch(`/api/job/${encodeURIComponent(isId)}`);
  if (r.status === 401) {
    location.href = "/giris";
    return;
  }
  if (r.status === 404) {
    yaz("İş bulunamadı (başka bir hesaba ait olabilir).", true);
    return;
  }
  const is = await r.json().catch(() => ({}));
  ilerlemeYaz(is.progress, is.stage_ad || "");
  yaz(is.message || is.stage_ad || "");
  provenansYaz(is);
  if (is.status === "done") {
    adimAktif("kalite");
    kaliteYaz(is);
    indirmeYaz(is);
    kutuphaneYukle();
    return;
  }
  if (is.status === "error") {
    yaz(`Hata: ${is.error || "bilinmiyor"}`, true);
    return;
  }
  setTimeout(() => izle(isId), 5000);
}

/* ── KALITE (QA + TESLIM) ── */
function kaliteYaz(is) {
  const e = $("#akis-kalite");
  if (!e) return;
  const t = is.teslim || {};
  const kabul = is.teslim_ok === true;
  e.textContent =
    `Kalite: ${is.kalite || "ÖLÇÜLMEDİ"} · ` +
    `Teslim: ${kabul ? "KABUL" : "KABUL EDİLMEDİ"}` +
    (kabul ? "" : ` (${t.neden || "neden yok"})`);
  e.dataset.kalite = is.kalite || "";
  e.dataset.teslim_ok = kabul ? "1" : "0";
}

/* ── INDIRME (YALNIZ SIGNED URL) ── */
function indirmeYaz(is) {
  adimAktif("indirme");
  const e = $("#akis-indirme");
  if (!e) return;
  e.innerHTML = "";
  if (!is.video_url) {
    e.textContent = "İndirilebilir bağlantı üretilemedi.";
    return;
  }
  const a = document.createElement("a");
  // ⚠ SIGNED URL sunucudan gelir; burada yol KURULMAZ.
  a.href = is.video_url;
  a.textContent = "Videoyu indir (süreli, hesabına bağlı bağlantı)";
  a.rel = "noopener";
  e.appendChild(a);
}

/* ── SON 3 VIDEO ── */
async function kutuphaneYukle() {
  const e = $("#akis-kutuphane");
  if (!e) return;
  const r = await fetch("/api/kutuphane");
  if (!r.ok) {
    e.textContent = "Kütüphane okunamadı.";
    return;
  }
  const d = await r.json().catch(() => ({}));
  e.innerHTML = "";
  (d.videolar || []).forEach((v) => {
    const li = document.createElement("li");
    const p = v.provenance || {};
    const q = v.qa || {};
    const bilgi = document.createElement("span");
    bilgi.textContent =
      `${v.sure_sn || "?"} sn · QA ${q.durum || "?"} · ` +
      `${p.provider_used || "-"}` +
      `${p.kredi_tuketildi ? " · kredi harcandı" : " · kredi harcanmadı"}`;
    li.appendChild(bilgi);
    if (v.video_url) {
      const a = document.createElement("a");
      a.href = v.video_url;          // ⚠ talep aninda uretilmis SIGNED URL
      a.textContent = " indir";
      a.rel = "noopener";
      li.appendChild(a);
    } else if (v.imzalanamadi) {
      li.appendChild(document.createTextNode(" (bağlantı imzalanamadı)"));
    }
    e.appendChild(li);
  });
  if (!(d.videolar || []).length) e.textContent = "Henüz kabul edilmiş video yok.";
}

/* ── BASLAT ── */
document.addEventListener("DOMContentLoaded", async () => {
  if (!(await oturumKontrol())) return;
  adimAktif("metin");
  krediUyarisiGuncelle();
  $("#akis-kaynak")?.addEventListener("change", () => {
    krediUyarisiGuncelle();      // aninda geri bildirim
    kaynakTercihiYaz();          // sonra SUNUCUNUN gercek karari
  });
  $("#akis-edit")?.addEventListener("change", () => adimAktif("stil"));
  $("#akis-kaynak")?.addEventListener("change", () => adimAktif("kaynak"));
  $("#akis-form")?.addEventListener("submit", uretimBaslat);
  kutuphaneYukle();
});
