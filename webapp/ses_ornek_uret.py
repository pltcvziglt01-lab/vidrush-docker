#!/usr/bin/env python3
"""Her ses secenegi icin arayuzde dinlenecek kisa ornek uretir.
edge sesleri bedava; OpenAI sesleri ~$0.002 (kisa metin) — bir kez uretilir."""
import asyncio, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/opt/vidrush")
import pipeline as P
import uret as U

HEDEF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "ses-ornek")
os.makedirs(HEDEF, exist_ok=True)
EN = ("I have learned that the smallest habits save the most money. "
      "Let me tell you what my mother taught me.")
TR = "En küçük alışkanlıkların en çok parayı biriktirdiğini öğrendim. Annemin bana öğrettiklerini anlatayım."

async def main():
    hepsi = "--hepsi" in sys.argv
    ok, hata = [], []
    for sid, v in P.SESLER.items():
        if sid == "otomatik":
            continue
        yol = os.path.join(HEDEF, f"{sid}.mp3")
        if os.path.exists(yol) and not hepsi:
            continue
        metin = TR if v.get("dil") == "tr" else EN
        try:
            if v["motor"] == "openai":
                await U.seslendir_openai(metin, yol, v["ses"], v.get("talimat", ""), v.get("hiz", 0.92))
            else:
                await U.seslendir(metin, v["ses"], yol)
            if os.path.exists(yol) and os.path.getsize(yol) > 1024:
                ok.append(sid); print(f"  OK   {sid:<20} {os.path.getsize(yol):>7} bayt", flush=True)
            else:
                hata.append(sid)
        except Exception as e:
            hata.append(sid); print(f"  HATA {sid}: {str(e)[:160]}", file=sys.stderr)
    print(f"\nURETILEN: {ok}\nHATALI: {hata}")
    return 1 if hata else 0

sys.exit(asyncio.run(main()))
