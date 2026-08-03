#!/usr/bin/env python3
"""Real-ESRGAN (anime/illustrasyon modeli) ile YEREL upscale — ucretsiz, sinirsiz.

Neden bu model: bizim kareler FOTOGRAF DEGIL, duz renkli cizim. Magnific fotoğraf
icin tasarlanmis, buyuturken DETAY UYDURUYOR (gozenek, kumas dokusu) — cizimde bu
zarar. RealESRGAN_x4plus_anime_6B tam bu is icin egitilmis: cizgiyi keskin tutar,
duz renk alanini temiz buyutur, doku uydurmaz.

Neden 'basicsr' kullanilmiyor: o paket torchvision surum catismasi cikariyor.
RRDBNet mimarisi burada dogrudan tanimli — tek bagimlilik torch.

Kullanim:
  python3 buyut.py <girdi.png> [cikti.png] [--olcek 2|4]
  python3 buyut.py --klasor <dizin> [--olcek 2] [--paralel 6]
"""
import os
import sys
import math

MODEL_URL = ("https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/"
             "RealESRGAN_x4plus_anime_6B.pth")
MODEL_YOL = os.environ.get("ESRGAN_MODEL", "/opt/vidrush/modeller/realesrgan_anime_6b.pth")


def _model_indir():
    if os.path.exists(MODEL_YOL) and os.path.getsize(MODEL_YOL) > 1_000_000:
        return MODEL_YOL
    os.makedirs(os.path.dirname(MODEL_YOL), exist_ok=True)
    import urllib.request
    print(f"  model indiriliyor: {MODEL_URL}", file=sys.stderr)
    urllib.request.urlretrieve(MODEL_URL, MODEL_YOL + ".tmp")
    os.replace(MODEL_YOL + ".tmp", MODEL_YOL)
    return MODEL_YOL


# ── RRDBNet (Real-ESRGAN mimarisi) — basicsr'siz, sade ──
def _ag(torch, nn):
    class ResidualDenseBlock(nn.Module):
        def __init__(s, nf=64, gc=32):
            super().__init__()
            s.conv1 = nn.Conv2d(nf, gc, 3, 1, 1)
            s.conv2 = nn.Conv2d(nf + gc, gc, 3, 1, 1)
            s.conv3 = nn.Conv2d(nf + 2 * gc, gc, 3, 1, 1)
            s.conv4 = nn.Conv2d(nf + 3 * gc, gc, 3, 1, 1)
            s.conv5 = nn.Conv2d(nf + 4 * gc, nf, 3, 1, 1)
            s.lrelu = nn.LeakyReLU(0.2, inplace=True)

        def forward(s, x):
            x1 = s.lrelu(s.conv1(x))
            x2 = s.lrelu(s.conv2(torch.cat((x, x1), 1)))
            x3 = s.lrelu(s.conv3(torch.cat((x, x1, x2), 1)))
            x4 = s.lrelu(s.conv4(torch.cat((x, x1, x2, x3), 1)))
            x5 = s.conv5(torch.cat((x, x1, x2, x3, x4), 1))
            return x5 * 0.2 + x

    class RRDB(nn.Module):
        def __init__(s, nf, gc=32):
            super().__init__()
            s.rdb1, s.rdb2, s.rdb3 = (ResidualDenseBlock(nf, gc) for _ in range(3))

        def forward(s, x):
            return s.rdb3(s.rdb2(s.rdb1(x))) * 0.2 + x

    class RRDBNet(nn.Module):
        def __init__(s, in_ch=3, out_ch=3, nf=64, nb=6, gc=32, scale=4):
            super().__init__()
            s.scale = scale
            s.conv_first = nn.Conv2d(in_ch, nf, 3, 1, 1)
            s.body = nn.Sequential(*[RRDB(nf, gc) for _ in range(nb)])
            s.conv_body = nn.Conv2d(nf, nf, 3, 1, 1)
            s.conv_up1 = nn.Conv2d(nf, nf, 3, 1, 1)
            s.conv_up2 = nn.Conv2d(nf, nf, 3, 1, 1)
            s.conv_hr = nn.Conv2d(nf, nf, 3, 1, 1)
            s.conv_last = nn.Conv2d(nf, out_ch, 3, 1, 1)
            s.lrelu = nn.LeakyReLU(0.2, inplace=True)

        def forward(s, x):
            import torch.nn.functional as F
            feat = s.conv_first(x)
            feat = feat + s.conv_body(s.body(feat))
            feat = s.lrelu(s.conv_up1(F.interpolate(feat, scale_factor=2, mode="nearest")))
            feat = s.lrelu(s.conv_up2(F.interpolate(feat, scale_factor=2, mode="nearest")))
            return s.conv_last(s.lrelu(s.conv_hr(feat)))

    return RRDBNet


_MODEL = None


def _yukle():
    global _MODEL
    if _MODEL is not None:
        return _MODEL
    import torch
    import torch.nn as nn
    torch.set_num_threads(int(os.environ.get("ESRGAN_THREAD", "10")))
    RRDBNet = _ag(torch, nn)
    net = RRDBNet(nb=6)                 # anime_6B: 6 blok
    sd = torch.load(_model_indir(), map_location="cpu")
    sd = sd.get("params_ema") or sd.get("params") or sd
    net.load_state_dict(sd, strict=True)
    net.eval()
    _MODEL = net
    return net


def buyut(girdi: str, cikti: str = "", olcek: int = 2, karo: int = 256) -> str:
    """Gorseli buyutur. olcek=4 modelin dogal cikti oraninda; 2 istenirse sonra kucultulur.
    karo: bellek icin parcali isleme (9 GB RAM'de 1536x1024 tek seferde sisirir)."""
    import torch
    import numpy as np
    from PIL import Image
    cikti = cikti or girdi
    net = _yukle()
    im = Image.open(girdi).convert("RGB")
    W, H = im.size
    a = np.asarray(im, dtype=np.float32) / 255.0
    t = torch.from_numpy(a).permute(2, 0, 1).unsqueeze(0)

    pad = 16
    out = torch.zeros(1, 3, H * 4, W * 4)
    with torch.no_grad():
        for y in range(0, H, karo):
            for x in range(0, W, karo):
                y0, y1 = max(0, y - pad), min(H, y + karo + pad)
                x0, x1 = max(0, x - pad), min(W, x + karo + pad)
                parca = net(t[:, :, y0:y1, x0:x1])
                ust = (y - y0) * 4
                sol = (x - x0) * 4
                yh = min(karo, H - y) * 4
                xw = min(karo, W - x) * 4
                out[:, :, y * 4:y * 4 + yh, x * 4:x * 4 + xw] = \
                    parca[:, :, ust:ust + yh, sol:sol + xw]

    arr = (out.squeeze(0).permute(1, 2, 0).clamp(0, 1).numpy() * 255).astype("uint8")
    res = Image.fromarray(arr)
    if olcek != 4:
        res = res.resize((W * olcek, H * olcek), Image.LANCZOS)
    tmp = cikti + ".up.tmp.png"
    res.save(tmp)
    os.replace(tmp, cikti)
    return cikti


def klasor(dizin: str, olcek: int = 2, paralel: int = 4):
    import glob
    from concurrent.futures import ThreadPoolExecutor
    dosyalar = sorted(glob.glob(os.path.join(dizin, "*.png")) + glob.glob(os.path.join(dizin, "*.jpg")))
    _yukle()
    with ThreadPoolExecutor(max_workers=paralel) as ex:
        list(ex.map(lambda f: buyut(f, f, olcek), dosyalar))
    return len(dosyalar)


if __name__ == "__main__":
    import time
    a = sys.argv[1:]
    olcek = 2
    if "--olcek" in a:
        olcek = int(a[a.index("--olcek") + 1])
    if "--klasor" in a:
        d = a[a.index("--klasor") + 1]
        p = int(a[a.index("--paralel") + 1]) if "--paralel" in a else 4
        t0 = time.time()
        n = klasor(d, olcek, p)
        print(f"{n} gorsel {time.time()-t0:.1f} sn")
    else:
        g = a[0]
        c = a[1] if len(a) > 1 and not a[1].startswith("--") else ""
        t0 = time.time()
        print(buyut(g, c, olcek), f"({time.time()-t0:.1f} sn)")
