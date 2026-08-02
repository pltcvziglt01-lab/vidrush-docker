#!/usr/bin/env python3
"""Stil onizleme gorselleri uretir — arayuzde her stil kartinin yaninda gorunur.

Neden: stil secimi YAZIYLA yapilamaz. "Elle cizilmis editorial-karikatur" ile
"renkli kursun kalem" arasindaki farki ancak GOREREK secersin.

Tasarim karari: TUM stiller AYNI sahneyi cizer. Boylece kartlar yan yana
konuldugunda fark sadece STILDEN gelir — dogrudan karsilastirilabilir.
(Farkli sahneler cizdirseydik hangi farkin stilden hangisinin konudan geldigi
belli olmazdi.)

Kullanim (konteyner icinde):
    python3 /opt/vidrush/webapp/onizleme_uret.py            # eksikleri uret
    python3 /opt/vidrush/webapp/onizleme_uret.py --hepsi    # hepsini yeniden uret
    python3 /opt/vidrush/webapp/onizleme_uret.py --stil ani-defteri
"""
import os
import sys
import shutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pipeline as P

HEDEF_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "onizleme")
os.makedirs(HEDEF_DIR, exist_ok=True)

# Ortak sahne: her stilin karakterini VE ortamini VE bir veri yuzeyini ayni anda
# sinar; yani kartta stilin uc ozelligi birden gorunur.
ORTAK_SAHNE = (
    "MEDIUM ACTION, PRESENT. A person stands at the left of a warm kitchen in the late afternoon, "
    "turned towards the camera with one hand raised mid-explanation, the other resting on a wooden "
    "table. Behind them: a window with light coming through, open shelves with jars and cups, a "
    "kettle, a potted plant and a wall clock. On the right side of the frame, propped on the table, "
    "a hand-lettered card clearly reads \"SAVE 40\". One warm light source from the window."
)


def uret(stil_id: str, prof: dict) -> bool:
    hedef = os.path.join(HEDEF_DIR, f"{stil_id}.png")
    model = P.GORSEL_MODEL_ANIM
    # Stilin kendi dogal paleti varsa onu da uygula (kartta gercek renk kimligi gorunsun)
    stil_metni = prof["gorsel_ek"]
    if prof.get("varsayilan_karakter"):
        stil_metni += ". " + prof["varsayilan_karakter"]
    pal = P.palet_prompt(prof.get("palet", ""))
    if pal:
        stil_metni += "." + pal
    print(f"  {stil_id}: uretiliyor ({model})...", flush=True)
    # ISIK: uret() bunu cerceve'nin SONUNA ekliyor; onizleme de AYNI kosullari kullanmali,
    # yoksa kartta gordugun parlaklik gercek ciktiyla uyusmaz.
    cerceve = prof.get("cerceve", "") + P.isik_prompt(P.VARSAYILAN_ISIK)
    return P.referansli_gorsel(
        ORTAK_SAHNE, "", hedef,
        stil_prompt=stil_metni,
        cerceve=cerceve,
        yazi_yasak=False,          # kartta "SAVE 40" yazisi GORUNSUN
        model=model, deneme=3,
    )


def main():
    hepsi = "--hepsi" in sys.argv
    tek = None
    if "--stil" in sys.argv:
        tek = sys.argv[sys.argv.index("--stil") + 1]

    stiller = dict(P.ANIMASYON_STILLERI)
    basarili, atlanan, hatali = [], [], []
    for sid, prof in stiller.items():
        if tek and sid != tek:
            continue
        yol = os.path.join(HEDEF_DIR, f"{sid}.png")
        if os.path.exists(yol) and not hepsi and not tek:
            atlanan.append(sid)
            continue
        try:
            if uret(sid, prof) and os.path.exists(yol):
                basarili.append(sid)
            else:
                hatali.append(sid)
        except P.BakiyeHatasi as e:
            print(f"  BAKIYE: {e}", file=sys.stderr)
            hatali.append(sid)
            break
        except Exception as e:
            print(f"  {sid} HATA: {str(e)[:200]}", file=sys.stderr)
            hatali.append(sid)

    # Kucult: kart onizlemesi icin 640px yeter (sayfa hizli acilsin)
    try:
        from PIL import Image
        for sid in basarili:
            y = os.path.join(HEDEF_DIR, f"{sid}.png")
            im = Image.open(y).convert("RGB")
            im.thumbnail((640, 640))
            im.save(os.path.join(HEDEF_DIR, f"{sid}.jpg"), "JPEG", quality=86)
            os.remove(y)
    except Exception as e:
        print(f"  kucultme hata: {e}", file=sys.stderr)

    print(f"\nURETILEN: {basarili}\nATLANAN (zaten var): {atlanan}\nHATALI: {hatali}")
    return 1 if hatali else 0


if __name__ == "__main__":
    sys.exit(main())
