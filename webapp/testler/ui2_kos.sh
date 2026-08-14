#!/bin/bash
# FAZ UI-2 — uzak tarayici hattini STAGING uzerinde kosturur.
#
# ⚠ MAC'E HICBIR SEY YAZILMAZ. Betik yalnizca dosyalari UZAGA gonderir ve
#   uzaktan gelen METIN hukmu ekrana basar. Ekran goruntuleri, sonuc.json
#   ve tum QA artefaktlari once konteynerde (/tmp/ui2_kanit), sonra staging
#   HOST diskinde (/root/ui2_kanit) kalir. Yerele indirme YOKTUR.
# ⚠ KREDI HARCANMAZ: hat `/api/generate` istegini tarayici icinde yakalar.
# ⚠ CREDENTIAL YOK: oturum sunucu tarafinda uretilir; jetonu tasiyan ayar
#   dosyasi kanit dizinine YAZILMAZ ve kosum sonunda SILINIR.
#
# Kullanim:  bash webapp/testler/ui2_kos.sh
set -u

IP="${BEDOSAHO_IP:-185.23.17.240}"
KEY="${BEDOSAHO_KEY:-$HOME/.ssh/bedosaho_hetzner}"
KAP="${BEDOSAHO_KAP:-bedosaho}"
SSH="ssh -i $KEY -o StrictHostKeyChecking=no -o ConnectTimeout=20 root@$IP"
KOK="$(cd "$(dirname "$0")" && pwd)"
KOSU="ui2-$(date +%Y%m%d-%H%M%S)"
KANIT_KAP="/tmp/ui2_kanit/$KOSU"       # konteyner ici
KANIT_HOST="/root/ui2_kanit/$KOSU"     # staging host diski (kalici kanit)
HAT="/tmp/ui2_hat"
AYAR="$HAT/ayar.json"

echo "── UI-2 uzak kosu: $KOSU → $IP:$KANIT_HOST"

# ── HAT: betikleri konteynere gonder (stdin ile; Mac'te ara dosya YOK) ──
$SSH "docker exec -i $KAP mkdir -p $HAT $KANIT_KAP" || exit 20
for f in ui2_onkontrol.py ui2_uzak_akis.mjs; do
  $SSH "docker exec -i $KAP sh -c 'cat > $HAT/$f'" < "$KOK/$f" || exit 21
done

# ── ON KONTROL: credentialsiz oturum + kredisiz is ──
echo "── on kontrol"
$SSH "docker exec -e UI2_KANIT=$KANIT_KAP -e UI2_AYAR=$AYAR \
  -e UI2_TABAN=${UI2_TABAN:-http://127.0.0.1:8080} \
  -e UI2_IS_ID=${UI2_IS_ID:-} -i $KAP python3 $HAT/ui2_onkontrol.py"
ON_RC=$?
if [ $ON_RC -ne 0 ]; then
  echo "⛔ ON KONTROL BASARISIZ (rc=$ON_RC) — hat kosmadi."
  $SSH "docker exec -i $KAP rm -f $AYAR" >/dev/null 2>&1
  exit $ON_RC
fi

# ── HAT: gercek tarayici, masaustu + mobil ──
echo "── uzak tarayici (masaustu 1280x800 + mobil 390x844)"
$SSH "docker exec -i $KAP node $HAT/ui2_uzak_akis.mjs $AYAR"
HAT_RC=$?

# ── JETON TEMIZLIGI: ayar dosyasi kanitla birlikte TASINMAZ ──
$SSH "docker exec -i $KAP rm -f $AYAR" >/dev/null 2>&1

# ── KANIT: konteyner → staging HOST diski (Mac'e DEGIL) ──
$SSH "mkdir -p /root/ui2_kanit && docker cp $KAP:$KANIT_KAP $KANIT_HOST \
  >/dev/null 2>&1 && ls -l $KANIT_HOST | tail -n +2 | awk '{print \$5, \$9}'"
echo "── kanit staging host'unda: $KANIT_HOST (Mac'e indirilmedi)"
exit $HAT_RC
