#!/usr/bin/env python3
"""HAYALET_PAYLAS.md'yi KAYNAKTAN uretir — belge koddan sapmasin.

⚠ NEDEN: HAYALET_PAYLAS.md tek dosyalik kurulum paketidir; icinde her
modulun TAM kaynagi gomulu durur. Elle guncellenirse kod degisir, belgedeki
kopya eskir ve paketi kuran kisi ESKI kodu alir. Bu yuzden:

    · Duzyazi tek yerde: hayalet/KURULUM.md
    · Kod tek yerde:     hayalet/*.py, *.sh
    · HAYALET_PAYLAS.md = ikisinin BIRLESIMI, hep bu scriptle uretilir

Kullanim:
    python3 -m hayalet.paylas_uret          # uretir
    python3 -m hayalet.paylas_uret --kontrol # guncel mi? (CI/commit oncesi)
"""
from __future__ import annotations

import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent
HEDEF = KOK / "HAYALET_PAYLAS.md"

# Pakete girecek dosyalar — SIRA KURULUM SIRASI (bagimlilik once).
DOSYALAR = [
    ("hayalet/__init__.py", "python"),
    ("hayalet/ayar.py", "python"),
    ("hayalet/beyin.py", "python"),
    ("hayalet/flow_surucu.py", "python"),
    ("hayalet/capcut.py", "python"),
    ("hayalet/kurgu.py", "python"),
    ("hayalet/bot.py", "python"),
    ("hayalet/chrome_baslat.sh", "bash"),
]

BASLIK = """# 👻 HAYALET — Metin + Ses → CapCut Projesi (TAM PAKET)

> **NASIL KULLANILIR:** Bu dosyayı Claude Code'a at ve şunu yaz:
> **"Bu dosyadaki sistemi kur"**. Claude önce BÖLÜM 1'deki dosyaları
> aynen oluşturur, sonra BÖLÜM 2'deki kurulum adımlarını işletim
> sistemine göre uygular.
>
> Senden istenenler: kendi Telegram bot token'ın, Chrome'da Flow girişi,
> bir OpenAI anahtarı, kurulu bir CapCut (en az bir kayıtlı projeyle).

**🧠 `/senkron`** — Telegram'a **metin + seslendirme** verirsin; her cümle
için görsel/video üretilir, cümle sınırları **sesin kendisinden** çıkarılır
ve her cümle **ayrı klip** olarak CapCut zaman çizgisine dizilir. Sen
sadece geçiş/yazı/efekt eklersin.

**🎬 `/hikaye`** — promptları sen yazarsın, bot üretip indirir (kurgu yok).

> ⚠ Bu dosya **elle düzenlenmez**, `python3 -m hayalet.paylas_uret` ile
> üretilir. Kaynağı: `hayalet/KURULUM.md` + `hayalet/*.py`.

---

# BÖLÜM 1 — KOD (Claude: bu dosyaları AYNEN oluştur)

Boş klasör aç (ör. `~/hayalet-ajan`), içine `hayalet/` paketi:

"""


def uret() -> str:
    parcalar = [BASLIK]
    for gorece, dil in DOSYALAR:
        yol = KOK.parent / gorece
        if not yol.exists():
            raise SystemExit(f"EKSIK DOSYA: {yol} — pakete girecek kaynak yok")
        icerik = yol.read_text(encoding="utf-8").rstrip("\n")
        parcalar.append(f"## Dosya: `{gorece}`\n```{dil}\n{icerik}\n```\n\n")

    kurulum = (KOK / "KURULUM.md").read_text(encoding="utf-8")
    # KURULUM.md'nin kendi basligini at, "CLAUDE ICIN..."den itibaren al.
    im = kurulum.find("## CLAUDE İÇİN KURULUM TALİMATLARI")
    govde = kurulum[im:] if im > 0 else kurulum
    parcalar.append("---\n\n# BÖLÜM 2 — KURULUM VE KULLANIM\n\n" + govde)
    return "".join(parcalar)


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    yeni = uret()
    if "--kontrol" in argv:
        eski = HEDEF.read_text(encoding="utf-8") if HEDEF.exists() else ""
        if eski != yeni:
            print("✗ HAYALET_PAYLAS.md GUNCEL DEGIL — "
                  "`python3 -m hayalet.paylas_uret` calistir")
            return 1
        print("✓ HAYALET_PAYLAS.md guncel")
        return 0
    HEDEF.write_text(yeni, encoding="utf-8")
    print(f"✓ {HEDEF}  ({len(yeni.splitlines())} satir, "
          f"{len(DOSYALAR)} kaynak dosya gomuldu)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
