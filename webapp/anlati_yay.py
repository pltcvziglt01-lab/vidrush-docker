"""BOLUM MINI-YAYI VE KAPANIS OLCUMU. FAZ Y-18.

⚠ OLCULEN KUSUR (`Y18-YAY-PROMPT-SEZGISI`): "her bolum hook -> baglam ->
kanit/karsitlik -> sonuc" kurali sistemde YALNIZCA bir LLM PROMPT CUMLESI
olarak vardi (`pipeline.bolum_kural`); donen JSON uzerinde HICBIR
dogrulama yoktu. Kodda `Bolum` diye bir varlik, kimlik ya da uyelik
iliskisi olmadigi icin kural DOGRULANAMIYORDU — dogrulanamayan kural,
kural degil TEMENNIDIR. Model 3 yerine 7 bolum donse, hepsi ayni islevde
olsa, hat bunu goremezdi.

⚠ OLCULEN KUSUR (`Y18-ISLEV-TAUTOLOJI`): `editor/beat.islev_belirle` ilk
cumleye KOSULSUZ "hook", son cumleye KOSULSUZ "sonuc" veriyordu
(`indeks == 0` / `indeks >= toplam - 1`). Bu yuzden `HOOK-YOK` ve kapanis
kapilari YAPISAL OLARAK ateslenemiyordu — olcum SIFIR BILGI tasiyordu.
Ustelik desenler SALT INGILIZCEYDI; hat Turkce anlatim urettigi icin
`karsitlik` rolu Turkce iste HIC olusmuyordu.

⚠ OLCULEN KUSUR (`Y18-KAPANIS-OLCULMUYOR`): kapanisin ANLATISAL gucu
hicbir yerde olculmuyordu; `qa_son` yalnizca SESSIZ KUYRUK saniyesini
(`POST-OLU-FINAL`) olcuyor.

── SOZLESME ──
  · Olcum YAPILANDIRILMIS alanlardan yapilir: `chapter_id`, `beat_role`,
    `primary_fact_id`. ⚠ SERBEST METIN SEZGISI YOK: rol alani yoksa
    metinden ROL SEZILMEZ, olcum "olculmedi" doner.
  · Her chapter DORT halkayi DOGRU SIRADA tasir:
        hook -> baglam -> (kanit | karsitlik) -> sonuc
  · `kanit`/`karsitlik` KABUL EDILMIS FactPacket allowlist'inden bir
    `primary_fact_id` tasimak ZORUNDA (Y-11 sozlesmesi).
  · `sonuc` YENI fact UYDURAMAZ: tasidigi fact o chapter'da zaten
    kullanilmis olmali.
  · Kapanis: SON chapter'da `sonuc` + `closing`; olculen kapanis gucu
    `KAPANIS_ASGARI`'nin altindaysa FAIL.
  · Render kapsami: render edilen sahne sayisi beat sayisiyla ORTUSMELI.

⚠ Bu modul SAF: ag/dosya/render YOK, rastgelelik YOK. Ayni girdi her
zaman ayni hukmu verir.
"""
from __future__ import annotations

import re

# ── YAY SOZLESMESI ──
# Ucuncu halka IKI rolden BIRIYLE karsilanir (kanit ya da karsitlik).
YAY_SIRASI = ("hook", "baglam", ("kanit", "karsitlik"), "sonuc")
ROLLER = ("hook", "baglam", "kanit", "karsitlik", "sonuc", "closing")
# Chapter icinde EN FAZLA BIR KEZ gecebilecek roller (kanit/karsitlik
# yigilabilir — birden fazla kanit anlatiyi zayiflatmaz).
TEKIL_ROLLER = ("hook", "baglam", "sonuc", "closing")

KAPANIS_ASGARI = 0.60

KOD_OLCULMEDI = "ANLATI-YAY-OLCULMEDI"
KOD_EKSIK_HALKA = "ANLATI-YAY-EKSIK-HALKA"
KOD_SIRA_BOZUK = "ANLATI-YAY-SIRA-BOZUK"
KOD_ROL_TEKRAR = "ANLATI-YAY-ROL-TEKRAR"
KOD_KANIT_FACT_YOK = "ANLATI-KANIT-FACT-YOK"
KOD_SONUC_YENI_FACT = "ANLATI-SONUC-YENI-FACT"
KOD_KAPANIS_ZAYIF = "ANLATI-KAPANIS-ZAYIF"
KOD_RENDER_KAPSAMI = "ANLATI-RENDER-KAPSAMI-EKSIK"

KODLAR = (KOD_OLCULMEDI, KOD_EKSIK_HALKA, KOD_SIRA_BOZUK, KOD_ROL_TEKRAR,
          KOD_KANIT_FACT_YOK, KOD_SONUC_YENI_FACT, KOD_KAPANIS_ZAYIF,
          KOD_RENDER_KAPSAMI)

_KELIME = re.compile(r"[0-9a-zA-ZçğıöşüÇĞİÖŞÜ]{4,}")
_YAYGIN = frozenset({
    "icin", "ile", "olarak", "daha", "gibi", "kadar", "sonra", "once",
    "olan", "oldu", "ancak", "yani", "bunu", "bunun", "sonuc", "this",
    "that", "with", "from", "have", "been", "were", "their", "which"})


def _belirtec(metin) -> set:
    return {k.lower() for k in _KELIME.findall(str(metin or ""))
            if k.lower() not in _YAYGIN}


def _beatler(plan) -> list:
    """Yapilandirilmis beat listesi. ⚠ Rol alani OLMAYAN beat sezilmez."""
    out = []
    for b in (plan or []):
        if not isinstance(b, dict):
            return []
        rol = str(b.get("beat_role") or "").strip().lower()
        cid = str(b.get("chapter_id") or "").strip()
        if not rol or not cid or rol not in ROLLER:
            return []            # ⚠ Sozlesme disi -> OLCULMEZ (sezgi YOK)
        out.append({**b, "beat_role": rol, "chapter_id": cid})
    return out


def _bolumler(beatler) -> list:
    """`chapter_id` sirasini KORUYARAK bolumlere ayir."""
    sira, gruplar = [], {}
    for i, b in enumerate(beatler):
        c = b["chapter_id"]
        if c not in gruplar:
            gruplar[c] = []
            sira.append(c)
        gruplar[c].append((i, b))
    return [(c, gruplar[c]) for c in sira]


def kapanis_gucu(plan) -> float:
    """Kapanisin OLCULEN gucu (0..1). ⚠ DETERMINISTIK, sezgisel degil.

    Uc olculebilir bilesen (her biri 1/3):
      1. GERI CAGIRIM — closing metni videonun HOOK'uyla ortak belirtec
         paylasiyor mu? (anlati kapaniyor mu, yoksa baska yere mi gidiyor)
      2. COZUM — son chapter `sonuc` rolunu tasiyor mu?
      3. YENI BILGI YOK — closing, daha once GECMEYEN bir fact getirmiyor.
    """
    beatler = _beatler(plan)
    if not beatler:
        return 0.0
    closing = [b for b in beatler if b["beat_role"] == "closing"]
    if not closing:
        return 0.0
    son = closing[-1]
    bolum = _bolumler(beatler)
    son_cid = bolum[-1][0] if bolum else ""

    hooklar = [b for b in beatler if b["beat_role"] == "hook"]
    hb = _belirtec(hooklar[0].get("metin")) if hooklar else set()
    cb = _belirtec(son.get("metin"))
    geri = 1.0 if (hb and cb and (hb & cb)) else 0.0

    cozum = 1.0 if any(b["beat_role"] == "sonuc" and b["chapter_id"] == son_cid
                       for b in beatler) else 0.0

    onceki = {str(b.get("primary_fact_id") or "") for b in beatler
              if b is not son} - {""}
    yeni_fact = str(son.get("primary_fact_id") or "")
    temiz = 0.0 if (yeni_fact and yeni_fact not in onceki) else 1.0

    return round((geri + cozum + temiz) / 3.0, 3)


def yeniden_planla(plan) -> list:
    """TEK, DETERMINISTIK onarim denemesi: chapter ICINDE rol SIRASINI duzelt.

    ⚠ YALNIZCA SIRA duzeltilir. Eksik halka UYDURULMAZ, beat EKLENMEZ,
    SILINMEZ, metin DEGISTIRILMEZ — bu yuzden eksik yay bu denemeden sonra
    da FAIL kalir (ve kalmalidir).
    """
    beatler = _beatler(plan)
    if not beatler:
        return list(plan or [])
    oncelik = {"hook": 0, "baglam": 1, "kanit": 2, "karsitlik": 2,
               "sonuc": 3, "closing": 4}
    yeni = list(beatler)
    for _cid, uyeler in _bolumler(beatler):
        indeksler = [i for i, _b in uyeler]
        sirali = sorted((b for _i, b in uyeler),
                        key=lambda b: (oncelik.get(b["beat_role"], 9),
                                       float(b.get("bas_sn") or 0.0)))
        for hedef, b in zip(indeksler, sirali):
            yeni[hedef] = b
    return yeni


def yay_olcumu(plan, *, allowlist=None, render_sahne=None,
               render_scene_idler=None) -> dict:
    """Bolum yayi + kapanis olcumu. ⚠ FAIL-CLOSED, istisna firlatmaz.

    `allowlist` KABUL EDILMIS FactPacket kimlikleri (Y-11). Verilmezse
    kanit bagi DOGRULANAMAZ ve olcum "olculmedi" doner.
    `render_sahne` GERCEK render edilen sahne sayisi; verilmezse timeline
    kapsami DOGRULANAMAZ ve olcum "olculmedi" doner.
    `render_scene_idler` verilirse kapsam SAYIYLA degil BIREBIR KIMLIKLE
    dogrulanir.

    ⚠ OLCULEN KUSUR (`Y18B-KAPSAM-TOTOLOJI`, denetim): cagiran
    `render_sahne=len(beatler)` gecirirse olcum KENDI LISTESINI kapsam
    kaniti sayar ve kontrol anlamsizlasir. Kimlik listesi verildiginde bu
    imkansizdir.
    """
    temel = {"olculdu": False, "bolum": 0, "eksik_halka": None,
             "kapanis_skoru": None, "sira_bozuk": [], "render_kapsam": None}
    beatler = _beatler(plan)
    if not beatler:
        return {**temel, "kod": KOD_OLCULMEDI,
                "neden": "yapilandirilmis beat yok (chapter_id/beat_role)"}
    if allowlist is None:
        return {**temel, "kod": KOD_OLCULMEDI,
                "neden": "kabul edilmis fact allowlist'i verilmedi"}
    if render_sahne is None:
        return {**temel, "kod": KOD_OLCULMEDI,
                "neden": "render sahne sayisi verilmedi (kapsam olculemez)"}

    izin = set(allowlist or ())
    bolumler = _bolumler(beatler)
    eksik, sira_bozuk, tekrar = [], [], []
    kanit_fact_yok, sonuc_yeni_fact = [], []

    for cid, uyeler in bolumler:
        roller = [b["beat_role"] for _i, b in uyeler]
        # ── Halka tamligi ──
        for halka in YAY_SIRASI:
            adlar = halka if isinstance(halka, tuple) else (halka,)
            if not any(r in adlar for r in roller):
                eksik.append(f"{cid}:{'|'.join(adlar)}")
        # ── Tekil rol tekrari ──
        for r in TEKIL_ROLLER:
            if roller.count(r) > 1:
                tekrar.append(f"{cid}:{r}")
        # ── Sira ──
        beklenen = []
        for halka in YAY_SIRASI:
            adlar = halka if isinstance(halka, tuple) else (halka,)
            yerler = [i for i, r in enumerate(roller) if r in adlar]
            if yerler:
                beklenen.append(min(yerler))
        if beklenen != sorted(beklenen):
            sira_bozuk.append(cid)
        # ── Kanit fact bagi + sonuc yeni fact ──
        kullanilan = set()
        for _i, b in uyeler:
            fid = str(b.get("primary_fact_id") or "")
            if b["beat_role"] in ("kanit", "karsitlik"):
                if not fid or fid not in izin:
                    kanit_fact_yok.append(f"{cid}:{fid or 'YOK'}")
                else:
                    kullanilan.add(fid)
            elif fid:
                kullanilan.add(fid)
        for _i, b in uyeler:
            if b["beat_role"] != "sonuc":
                continue
            fid = str(b.get("primary_fact_id") or "")
            if not fid:
                continue
            onceki = {str(x.get("primary_fact_id") or "")
                      for j, x in uyeler
                      if x["beat_role"] in ("kanit", "karsitlik")} - {""}
            if fid not in onceki:
                sonuc_yeni_fact.append(f"{cid}:{fid}")

    # ── Kapanis ──
    son_cid = bolumler[-1][0]
    son_roller = [b["beat_role"] for _i, b in bolumler[-1][1]]
    kapanis_var = "closing" in son_roller and "sonuc" in son_roller
    skor = kapanis_gucu(beatler) if kapanis_var else 0.0

    # ── Render kapsami ──
    try:
        rs = int(render_sahne)
    except (TypeError, ValueError):
        rs = -1
    kapsam_ok = rs == len(beatler)
    kapsam_eksik = []
    if render_scene_idler is not None:
        # ⚠ BIREBIR kimlik eslesmesi: olcumdeki her beat gercekten render
        # edilmis bir sahneye karsilik gelmeli ve tersi de dogru olmali.
        _r = [str(x) for x in (render_scene_idler or [])]
        _b = [str(x.get("scene_id") or "") for x in beatler]
        if "" in _b:
            kapsam_eksik = ["beat scene_id tasimiyor"]
        else:
            _fazla = sorted(set(_b) - set(_r))
            _kayip = sorted(set(_r) - set(_b))
            kapsam_eksik = ([f"olcumde-fazla:{x}" for x in _fazla[:5]]
                            + [f"render-edilip-olculmeyen:{x}"
                               for x in _kayip[:5]])
        kapsam_ok = (not kapsam_eksik) and len(_b) == len(_r)

    kod, neden = "", ""
    if eksik:
        kod, neden = KOD_EKSIK_HALKA, f"eksik halka: {eksik[:6]}"
    elif tekrar:
        kod, neden = KOD_ROL_TEKRAR, f"rol tekrari: {tekrar[:6]}"
    elif sira_bozuk:
        kod, neden = KOD_SIRA_BOZUK, f"sira bozuk: {sira_bozuk[:6]}"
    elif kanit_fact_yok:
        kod, neden = (KOD_KANIT_FACT_YOK,
                      f"kanit kabul edilmis fact tasimiyor: {kanit_fact_yok[:6]}")
    elif sonuc_yeni_fact:
        kod, neden = (KOD_SONUC_YENI_FACT,
                      f"sonuc YENI fact getiriyor: {sonuc_yeni_fact[:6]}")
    elif not kapanis_var or skor < KAPANIS_ASGARI:
        kod = KOD_KAPANIS_ZAYIF
        neden = (f"son bolum ({son_cid}) sonuc+closing tasimiyor"
                 if not kapanis_var
                 else f"kapanis gucu {skor:.2f} < {KAPANIS_ASGARI:.2f}")
    elif not kapsam_ok:
        kod = KOD_RENDER_KAPSAMI
        neden = (f"render {rs} sahne, plan {len(beatler)} beat"
                 + (f" | {kapsam_eksik[:6]}" if kapsam_eksik else ""))

    return {"olculdu": True, "bolum": len(bolumler),
            "beat": len(beatler),
            "eksik_halka": eksik, "sira_bozuk": sira_bozuk,
            "rol_tekrari": tekrar,
            "kanit_fact_yok": kanit_fact_yok,
            "sonuc_yeni_fact": sonuc_yeni_fact,
            "kapanis_skoru": skor,
            "render_kapsam": (round(len(beatler) / rs, 3) if rs > 0 else 0.0),
            "kapsam_eksik": kapsam_eksik,
            "kod": kod, "neden": neden}
