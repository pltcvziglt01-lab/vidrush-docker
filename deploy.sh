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

IP="${BEDOSAHO_IP:-204.168.136.159}"
KEY="${BEDOSAHO_KEY:-$HOME/.ssh/bedosaho_hetzner}"
SSH="ssh -i $KEY -o StrictHostKeyChecking=no -o ConnectTimeout=15 root@$IP"
KOK="$(cd "$(dirname "$0")" && pwd)"

[ -f "$KEY" ] || { echo "HATA: SSH anahtari yok: $KEY (Polat'tan iste)"; exit 1; }

echo "== 1/5 Devam eden is var mi (varsa bekle, isi bozma) =="
# ONEMLI: sadece render'a bakmak YETMEZ — is once ~10-40 dk GORSEL URETIM asamasinda gecirir
# ve o sirada hicbir remotion/chrome sureci yoktur. Gercek kontrol: durum dosyalari.
AKTIF=$($SSH "docker exec bedosaho sh -c 'grep -l \"\\\"durum\\\": \\\"uretiliyor\\\"\" /opt/vidrush/webapp/veri/durumlar/*.json 2>/dev/null | wc -l'" 2>/dev/null || echo 0)
RENDER=$($SSH "docker exec bedosaho sh -c 'ps -eo args|grep -iE \"remotion render|chrome-headless\"|grep -v grep|wc -l'" 2>/dev/null || echo 0)
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
PYTHONUTF8=1 "$PYBIN" -c "import ast,glob,sys
yollar = glob.glob('$KOKPY/webapp/*.py')+['$KOKPY/app/uret.py']
[ast.parse(open(f, encoding='utf-8').read()) for f in yollar]
print('  ✓ syntax OK (%d dosya)' % len(yollar))" || { echo 'SYNTAX HATASI — deploy iptal'; exit 3; }

echo "== 3/5 Dosyalari konteynere kopyala =="
# webapp (pipeline/server/kaynak/static)
$SSH "mkdir -p /tmp/dep/webapp/static /tmp/dep/rs/src /tmp/dep/rs/fonts"
scp -i "$KEY" -o StrictHostKeyChecking=no "$KOK"/webapp/*.py root@$IP:/tmp/dep/webapp/ >/dev/null
scp -i "$KEY" -o StrictHostKeyChecking=no "$KOK"/webapp/static/index.html root@$IP:/tmp/dep/webapp/static/ >/dev/null
scp -i "$KEY" -o StrictHostKeyChecking=no "$KOK"/app/uret.py root@$IP:/tmp/dep/ >/dev/null
# Remotion kaynaklari: .tsx + .ts (fontlar.ts gibi yardimcilar da)
scp -i "$KEY" -o StrictHostKeyChecking=no "$KOK"/app/render-studio/src/*.tsx "$KOK"/app/render-studio/src/*.ts root@$IP:/tmp/dep/rs/src/ >/dev/null
# Gomulu altyazi fontlari (varsa)
if ls "$KOK"/app/render-studio/public/fonts/*.ttf >/dev/null 2>&1; then
  scp -i "$KEY" -o StrictHostKeyChecking=no "$KOK"/app/render-studio/public/fonts/*.ttf root@$IP:/tmp/dep/rs/fonts/ >/dev/null
fi
$SSH "docker cp /tmp/dep/webapp/. bedosaho:/opt/vidrush/webapp/ && \
      docker cp /tmp/dep/uret.py bedosaho:/opt/vidrush/uret.py && \
      docker cp /tmp/dep/rs/src/. bedosaho:/opt/vidrush/render-studio/src/ && \
      docker exec bedosaho mkdir -p /opt/vidrush/render-studio/public/fonts && \
      (ls /tmp/dep/rs/fonts/*.ttf >/dev/null 2>&1 && docker cp /tmp/dep/rs/fonts/. bedosaho:/opt/vidrush/render-studio/public/fonts/ || true) && \
      rm -rf /tmp/dep"
echo "  ✓ kopyalandi"

echo "== 4/5 Yeniden baslat + saglik =="
$SSH "docker restart bedosaho >/dev/null"
# Saglik: tek deneme yerine ~30 sn'ye kadar bekle (acilis 9 sn'yi asinca deploy yarim kalmasin,
# kalicilas tirma adimi atlaniyordu)
# NOT: konteyner 8080 -> host 80 esli (docker port bedosaho). localhost:8080 DEGIL :80!
$SSH 'for i in 1 2 3 4 5 6 7; do sleep 4; R=$(curl -s -m 15 http://localhost:80/api/saglik); [ -n "$R" ] && { echo "$R"; exit 0; }; done; echo "HATA: saglik yaniti alinamadi"; exit 7' ; echo ""

echo "== 5/5 Durumu imaja bas (kalici) =="
$SSH "docker commit bedosaho bedosaho:latest >/dev/null && docker tag bedosaho:latest bedosaho && echo '  ✓ kalici'"

echo ""
echo "✅ DEPLOY TAMAM.  Site: http://$IP/"
echo "   NOT: package.json'a yeni npm paketi eklediysen bu script onu KURMAZ —"
echo "   o durumda: $SSH 'docker exec bedosaho sh -c \"cd /opt/vidrush/render-studio && npm i\"'"
