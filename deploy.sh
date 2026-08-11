#!/bin/bash
# BEDOSAHO AI — tek komut deploy.
# Yerel koddaki degisiklikleri canli Hetzner konteynerine gonderir, yeniden baslatir,
# ve durumu imaja basar (kalici olur). Kullanim:  bash deploy.sh
#
# GEREKENLER:
#   - ~/.ssh/bedosaho_hetzner  (sunucu SSH anahtari — Polat'tan al)
#   - Bu repo klonlanmis olmali
#
# ORTAK SUNUCU KURALI: deploy etmeden ONCE `git pull` yap, deploy'dan SONRA `git push`.
# Ayni anda ikiniz deploy ETMEYIN (tek konteyner — biriniz digerinin isini bozar).
set -e

# CANLI SUNUCU: RX-4 (10 vCPU) — 1 Agu 2026'da tasindi. Eski Hetzner (204.168.136.159)
# artik kullanilmiyor; BEDOSAHO_IP ile gecici olarak baska hedefe deploy edilebilir.
IP="${BEDOSAHO_IP:-185.23.17.240}"
KEY="${BEDOSAHO_KEY:-$HOME/.ssh/bedosaho_hetzner}"
SSH="ssh -i $KEY -o StrictHostKeyChecking=no -o ConnectTimeout=15 root@$IP"
KOK="$(cd "$(dirname "$0")" && pwd)"

[ -f "$KEY" ] || { echo "HATA: SSH anahtari yok: $KEY (Polat'tan iste)"; exit 1; }

echo "== 1/5 Devam eden is var mi (varsa bekle, isi bozma) =="
# ONEMLI: sadece render'a bakmak YETMEZ — is once ~10-40 dk GORSEL URETIM asamasinda gecirir
# ve o sirada hicbir remotion/chrome sureci yoktur. Gercek kontrol: durum dosyalari.
AKTIF=$($SSH "docker exec bedosaho sh -c 'grep -l \"\\\"durum\\\": \\\"uretiliyor\\\"\" /opt/vidrush/webapp/veri/durumlar/*.json 2>/dev/null | wc -l'" 2>/dev/null || echo 0)
# defunct (zombi) surecler CANLI DEGIL — bitmis islerin kalintisi; onlari sayma (yanlis alarm)
RENDER=$($SSH "docker exec bedosaho sh -c 'ps -eo args|grep -iE \"remotion render|chrome-headless\"|grep -v grep|grep -v defunct|wc -l'" 2>/dev/null || echo 0)
if [ "${AKTIF:-0}" -gt 0 ] || [ "${RENDER:-0}" -gt 0 ]; then
  echo "⚠️  DEPLOY DURDURULDU — su an bir video uretiliyor (aktif is: $AKTIF, render sureci: $RENDER)."
  echo "   Deploy konteyneri yeniden baslatir ve o isi OLDURUR (harcanan kredi de bosa gider)."
  echo "   Isin bitmesini bekle, sonra tekrar dene."
  echo "   Gercekten zorlamak istersen: FORCE=1 bash deploy.sh"
  [ "${FORCE:-0}" = "1" ] || exit 2
fi

echo "== 2/5 Python syntax kontrol =="
# Windows Git Bash uyumu: python3 yoksa python/py kullan; /c/.. yolunu C:/.. yap (cygpath),
# dosyalari UTF-8 oku (Turkce karakterli yol/iceriklerde varsayilan codec patliyor).
# NOT: Windows'ta python3.exe cogu zaman Store yonlendirme SAHTESI -> gercekten calisani sec.
PYBIN=""
for c in python3 python py; do
  if "$c" -c "pass" >/dev/null 2>&1; then PYBIN="$c"; break; fi
done
[ -n "$PYBIN" ] || { echo "HATA: calisan python bulunamadi"; exit 3; }
KOKPY="$(cygpath -m "$KOK" 2>/dev/null || echo "$KOK")"
# compile() KULLAN, ast.parse DEGIL. ast.parse "duplicate argument 'ses'" gibi hatalari
# YAKALAMAZ (bunlar ayristirmada degil bytecode uretiminde bulunur) — 1 Agu 2026'da tam
# boyle bir hata syntax kontrolunden gecti ve siteyi dusurdu.
# ⚠ 12 Agu 2026 (Faz H): glob ALT PAKETLERI de kapsamali. `webapp/arastirma`,
# `webapp/medya`, `webapp/editor` paketleri pipeline'a baglandi; bunlardaki bir
# sozdizimi hatasi eskiden taramadan GECIYORDU ve ancak canlida ImportError
# olarak patlardi (server hic acilmaz, TUM uclar 500).
PYTHONUTF8=1 "$PYBIN" -c "import glob,sys
yollar = (sorted(glob.glob('$KOKPY/webapp/*.py'))
          + sorted(glob.glob('$KOKPY/webapp/*/*.py'))
          + sorted(glob.glob('$KOKPY/webapp/*/*/*.py'))
          + ['$KOKPY/app/uret.py'])
yollar = [y for y in yollar if '/testler/' not in y.replace('\\\\', '/')]
hata = 0
for f in yollar:
    try:
        compile(open(f, encoding='utf-8').read(), f, 'exec')
    except SyntaxError as e:
        print('  ✗ %s satir %s: %s' % (f, e.lineno, e.msg)); hata = 1
sys.exit(hata) if hata else print('  ✓ derleme OK (%d dosya)' % len(yollar))" \
  || { echo 'SYNTAX HATASI — deploy iptal'; exit 3; }

# TANIMSIZ ISIM taramasi. compile() sadece SOZDIZIMINI dogrular; govdede tanimsiz bir
# degiskene dokunmak (or. endpoint imzasina eklemeyi unuttugun bir Form alani) derlemeden
# GECER ve ancak istek geldiginde 500 verir. 1 Agu 2026'da tam boyle oldu: /api/generate
# 'NameError: name ses is not defined' ile patladi ve kullanicinin videosu baslamadi.
if "$PYBIN" -m pyflakes --version >/dev/null 2>&1; then
  TANIMSIZ=$(PYTHONUTF8=1 "$PYBIN" -m pyflakes "$KOKPY"/webapp/*.py \
               "$KOKPY"/webapp/arastirma/*.py "$KOKPY"/webapp/medya/*.py \
               "$KOKPY"/webapp/medya/providers/*.py "$KOKPY"/webapp/editor/*.py \
               "$KOKPY/app/uret.py" 2>&1 \
             | grep "undefined name" || true)
  if [ -n "$TANIMSIZ" ]; then
    echo "  ✗ TANIMSIZ ISIM — deploy iptal:"; echo "$TANIMSIZ"; exit 3
  fi
  echo "  ✓ tanimsiz isim yok"
else
  echo "  ⚠ pyflakes kurulu degil — tanimsiz isim taramasi ATLANDI (pip install pyflakes)"
fi

echo "== 3/5 Dosyalari konteynere kopyala =="
# webapp (pipeline/server/kaynak/static)
$SSH "mkdir -p /tmp/dep/webapp/static/js /tmp/dep/rs/src/editorv2 /tmp/dep/rs/fonts"
scp -i "$KEY" -o StrictHostKeyChecking=no "$KOK"/webapp/*.py root@$IP:/tmp/dep/webapp/ >/dev/null
# ⚠ 12 Agu 2026 (Faz H): `webapp/*.py` globu ALT PAKETLERI KAPSAMAZ.
# `arastirma/`, `medya/` (+ `medya/providers/`) ve `editor/` paketleri
# pipeline.py tarafindan import ediliyor; kopyalanmazlarsa konteynerde
# ModuleNotFoundError olur, server.py HIC ACILMAZ ve site tamamen duser.
# `testler/` bilerek DISARIDA: canliya test betigi gitmez.
$SSH "mkdir -p /tmp/dep/webapp/arastirma /tmp/dep/webapp/medya/providers /tmp/dep/webapp/editor"
for _p in arastirma medya editor; do
  scp -i "$KEY" -o StrictHostKeyChecking=no "$KOK"/webapp/$_p/*.py \
      root@$IP:/tmp/dep/webapp/$_p/ >/dev/null
done
scp -i "$KEY" -o StrictHostKeyChecking=no "$KOK"/webapp/medya/providers/*.py \
    root@$IP:/tmp/dep/webapp/medya/providers/ >/dev/null
scp -i "$KEY" -o StrictHostKeyChecking=no "$KOK"/webapp/static/index.html root@$IP:/tmp/dep/webapp/static/ >/dev/null
# ⚠ 12 Agu 2026: arayuz tek dosyadan CIKARILDI. `index.html` artik `ui/app.css`
# ve `ui/app.js`'i cagiriyor; bunlar kopyalanmazsa CANLI SITE STILSIZ VE
# ISLEVSIZ kalir (index.html gider, bagimliliklari gitmez). server.py'deki
# allowlist'li /ui rotasi bu dosyalari sunuyor.
scp -i "$KEY" -o StrictHostKeyChecking=no "$KOK"/webapp/static/app.css "$KOK"/webapp/static/app.js root@$IP:/tmp/dep/webapp/static/ >/dev/null
scp -i "$KEY" -o StrictHostKeyChecking=no "$KOK"/webapp/static/js/*.js root@$IP:/tmp/dep/webapp/static/js/ >/dev/null
scp -i "$KEY" -o StrictHostKeyChecking=no "$KOK"/app/uret.py root@$IP:/tmp/dep/ >/dev/null
# Remotion kaynaklari: .tsx + .ts (fontlar.ts gibi yardimcilar da)
scp -i "$KEY" -o StrictHostKeyChecking=no "$KOK"/app/render-studio/src/*.tsx "$KOK"/app/render-studio/src/*.ts root@$IP:/tmp/dep/rs/src/ >/dev/null
# ⚠ 12 Agu 2026: `src/*.tsx` globu ALT DIZINLERI KAPSAMAZ. `Root.tsx`
# `./editorv2/EditorV2`'yi import ediyor; editorv2 kopyalanmazsa Remotion
# PAKETLEME COKER ve TUM video render'i durur (yalnizca V2 degil, VidrushVideo
# da bundle edilemez).
if ls "$KOK"/app/render-studio/src/editorv2/* >/dev/null 2>&1; then
  scp -i "$KEY" -o StrictHostKeyChecking=no "$KOK"/app/render-studio/src/editorv2/* root@$IP:/tmp/dep/rs/src/editorv2/ >/dev/null
fi
# Gomulu altyazi fontlari (varsa)
# Doku dosyalari (grain vb.) — 11 Agu 2026: grain artik onceden uretilmis PNG kullaniyor,
# deploy kopyalamazsa efekt sessizce kaybolur.
$SSH "mkdir -p /tmp/dep/rs/doku"
if ls "$KOK"/app/render-studio/public/doku/*.png >/dev/null 2>&1; then
  scp -i "$KEY" -o StrictHostKeyChecking=no "$KOK"/app/render-studio/public/doku/*.png root@$IP:/tmp/dep/rs/doku/ >/dev/null
fi
if ls "$KOK"/app/render-studio/public/fonts/*.ttf >/dev/null 2>&1; then
  scp -i "$KEY" -o StrictHostKeyChecking=no "$KOK"/app/render-studio/public/fonts/*.ttf root@$IP:/tmp/dep/rs/fonts/ >/dev/null
fi
$SSH "docker exec bedosaho mkdir -p /opt/vidrush/webapp/arastirma \
        /opt/vidrush/webapp/medya/providers /opt/vidrush/webapp/editor && \
      docker cp /tmp/dep/webapp/. bedosaho:/opt/vidrush/webapp/ && \
      docker cp /tmp/dep/uret.py bedosaho:/opt/vidrush/uret.py && \
      docker exec bedosaho mkdir -p /opt/vidrush/render-studio/src/editorv2 && \
      docker cp /tmp/dep/rs/src/. bedosaho:/opt/vidrush/render-studio/src/ && \
      docker exec bedosaho mkdir -p /opt/vidrush/webapp/static/js && \
      docker exec bedosaho mkdir -p /opt/vidrush/render-studio/public/fonts && \
      (ls /tmp/dep/rs/fonts/*.ttf >/dev/null 2>&1 && docker cp /tmp/dep/rs/fonts/. bedosaho:/opt/vidrush/render-studio/public/fonts/ || true) && \
      docker exec bedosaho mkdir -p /opt/vidrush/render-studio/public/doku && \
      (ls /tmp/dep/rs/doku/*.png >/dev/null 2>&1 && docker cp /tmp/dep/rs/doku/. bedosaho:/opt/vidrush/render-studio/public/doku/ || true) && \
      rm -rf /tmp/dep"
echo "  ✓ kopyalandi"

echo "== 4/5 Yeniden baslat + saglik =="
$SSH "docker restart bedosaho >/dev/null"
# Saglik: tek deneme yerine ~30 sn'ye kadar bekle (acilis 9 sn'yi asinca deploy yarim kalmasin,
# kalicilas tirma adimi atlaniyordu)
# NOT: konteyner 8080 -> host 80 esli (docker port bedosaho). localhost:8080 DEGIL :80!
$SSH 'for i in 1 2 3 4 5 6 7; do sleep 4; R=$(curl -s -m 15 http://localhost:80/api/saglik); [ -n "$R" ] && { echo "$R"; exit 0; }; done; echo "HATA: saglik yaniti alinamadi"; exit 7' ; echo ""

# CANLI UC NOKTA TESTI: konteyner ayakta olmasi yetmez, arayuzun cagirdigi uclar
# gercekten 200 donmeli. (Ucret dogurmayan, sadece-okuma uclari test edilir.)
echo "== 4.5/5 Uc nokta testi =="
UCLAR="api/saglik api/animasyon-stilleri api/edit-stilleri api/paletler api/arkaplanlar api/sesler api/altyazi-sablonlari api/profiller"
BOZUK=""
for u in $UCLAR; do
  K=$($SSH "curl -s -o /dev/null -w '%{http_code}' --max-time 15 localhost/$u" 2>/dev/null)
  [ "$K" = "200" ] || BOZUK="$BOZUK $u($K)"
done
if [ -n "$BOZUK" ]; then
  echo "  ✗ BOZUK UC:$BOZUK"
  echo "  Konteyner ayakta ama arayuz calismaz — imaja BASILMADI, logu incele:"
  $SSH "docker logs --tail 25 bedosaho 2>&1 | tail -25"
  exit 4
fi
echo "  ✓ 8 uc nokta 200"

echo "== 5/5 Durumu imaja bas (kalici) =="
# ⚠ HER commit YENI bir 5+ GB imaj katmani yaratir ve eskisi <none> (dangling) olarak
# diskte kalir. 7 Agu 2026'da bu birikim sunucu diskini DOLDURDU: 75 dangling imaj,
# 125 GB, disk %100 -> video uretimi cikti yazamaz hale gelirdi. Bu yuzden commit'ten
# hemen sonra dangling imajlar temizlenir. Calisan konteynerin imaji ETIKETLI oldugu
# icin prune ona dokunmaz.
$SSH "docker commit bedosaho bedosaho:latest >/dev/null && docker tag bedosaho:latest bedosaho && echo '  ✓ kalici'"
GERI=$($SSH "docker image prune -f 2>/dev/null | tail -1")
echo "  ✓ eski imaj katmanlari temizlendi (${GERI:-0})"
BOS=$($SSH "df -h / | tail -1 | awk '{print \$4\" bos (\"\$5\" dolu)\"}'")
echo "  disk: $BOS"

echo ""
echo "✅ DEPLOY TAMAM.  Site: http://$IP/"
echo "   NOT: package.json'a yeni npm paketi eklediysen bu script onu KURMAZ —"
echo "   o durumda: $SSH 'docker exec bedosaho sh -c \"cd /opt/vidrush/render-studio && npm i\"'"
