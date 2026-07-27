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

echo "== 1/5 Aktif render var mi (varsa bekle, isi bozma) =="
N=$($SSH "docker exec bedosaho sh -c 'ps -eo args|grep -iE \"remotion render|chrome-headless\"|grep -v grep|wc -l'" 2>/dev/null || echo 0)
if [ "$N" -gt 0 ]; then
  echo "⚠️  Su an bir video render ediliyor. Deploy o isi OLDURUR. Once bitmesini bekle."
  echo "   (yine de devam icin: FORCE=1 bash deploy.sh)"
  [ "${FORCE:-0}" = "1" ] || exit 2
fi

echo "== 2/5 Python syntax kontrol =="
python3 -c "import ast,glob,sys
[ast.parse(open(f).read()) for f in glob.glob('$KOK/webapp/*.py')+['$KOK/app/uret.py']]
print('  ✓ syntax OK')" || { echo 'SYNTAX HATASI — deploy iptal'; exit 3; }

echo "== 3/5 Dosyalari konteynere kopyala =="
# webapp (pipeline/server/kaynak/static)
$SSH "mkdir -p /tmp/dep/webapp/static /tmp/dep/rs/src"
scp -i "$KEY" -o StrictHostKeyChecking=no "$KOK"/webapp/*.py root@$IP:/tmp/dep/webapp/ >/dev/null
scp -i "$KEY" -o StrictHostKeyChecking=no "$KOK"/webapp/static/index.html root@$IP:/tmp/dep/webapp/static/ >/dev/null
scp -i "$KEY" -o StrictHostKeyChecking=no "$KOK"/app/uret.py root@$IP:/tmp/dep/ >/dev/null
scp -i "$KEY" -o StrictHostKeyChecking=no "$KOK"/app/render-studio/src/*.tsx root@$IP:/tmp/dep/rs/src/ >/dev/null
$SSH "docker cp /tmp/dep/webapp/. bedosaho:/opt/vidrush/webapp/ && \
      docker cp /tmp/dep/uret.py bedosaho:/opt/vidrush/uret.py && \
      docker cp /tmp/dep/rs/src/. bedosaho:/opt/vidrush/render-studio/src/ && rm -rf /tmp/dep"
echo "  ✓ kopyalandi"

echo "== 4/5 Yeniden baslat + saglik =="
$SSH "docker restart bedosaho >/dev/null"
sleep 9
$SSH "curl -s -m 15 http://localhost:8080/api/saglik" ; echo ""

echo "== 5/5 Durumu imaja bas (kalici) =="
$SSH "docker commit bedosaho bedosaho:latest >/dev/null && docker tag bedosaho:latest bedosaho && echo '  ✓ kalici'"

echo ""
echo "✅ DEPLOY TAMAM.  Site: http://$IP/"
echo "   NOT: package.json'a yeni npm paketi eklediysen bu script onu KURMAZ —"
echo "   o durumda: $SSH 'docker exec bedosaho sh -c \"cd /opt/vidrush/render-studio && npm i\"'"
