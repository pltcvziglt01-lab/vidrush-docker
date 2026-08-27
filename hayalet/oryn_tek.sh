#!/usr/bin/env bash
# 10 saniyelik tekli ORYN klibi icin prompt basar.
# Ses blogu ASLA elle yazilmaz — hep oryn_ses.txt'ten gelir.
#   ./oryn_tek.sh 1        -> 1. replik icin prompt
#   ./oryn_tek.sh          -> replik listesi
set -euo pipefail
D="$(cd "$(dirname "$0")" && pwd)"
L="$D/videolar/oryn_tekli.txt"
for f in oryn_karakter.txt oryn_ses.txt oryn_stil.txt oryn_sureklilik.txt; do
  [ -s "$D/$f" ] || { echo "EKSIK blok: $D/$f" >&2; exit 1; }
done
[ -s "$L" ] || { echo "EKSIK liste: $L" >&2; exit 1; }

sat() { grep -v '^#' "$L" | grep '|' | sed -n "${1}p"; }

if [ $# -eq 0 ]; then
  grep -v '^#' "$L" | grep '|' | nl -w2 -s'. ' | cut -c1-100; exit 0
fi
N="$1"; S="$(sat "$N")"
[ -n "$S" ] || { echo "$N numarali replik yok" >&2; exit 1; }
REPLIK="$(echo "$S" | cut -d'|' -f1 | sed 's/^ *//;s/ *$//')"
SORU="$(echo "$S"  | cut -d'|' -f2 | sed 's/^ *//;s/ *$//')"
K=$(echo "$REPLIK" | wc -w | tr -d ' ')
[ "$K" -le 18 ] || echo "!! $K kelime — 10sn tavani 18. Konusma yarim kalir." >&2

cat <<EOF
The image is the first frame. A single continuous shot, no cuts.

$(cat "$D/oryn_karakter.txt") — stands facing the camera, completely still.

MOTION: it blinks once, slowly, then speaks. It moves almost nothing — only
the small movements of speech, one slow blink midway, and the faintest tilt
of the head on the final sentence. The pale-gold light-lines along its
temples and neck pulse very slightly brighter in time with its words. The
three orbs behind its head turn slowly in place. Golden motes drift steadily
through the light around it. It never gestures, never leans, never smiles.

It says: "$REPLIK"

$(cat "$D/oryn_ses.txt")
$(cat "$D/oryn_sureklilik.txt")
CAMERA: locked off, holding perfectly still on its face and shoulders, with
an almost imperceptible slow drift in over the ten seconds. No handheld
shake, no pans, no cuts.

$(cat "$D/oryn_stil.txt")
EOF
echo
echo "----- EKRAN YAZISI (Flow'a degil, kurguda bindir) -----"
echo "7-10 sn: $SORU"
