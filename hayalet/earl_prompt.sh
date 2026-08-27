#!/usr/bin/env bash
# Earl promptu kurar — ses blogu ASLA elle yazilmaz, hep dosyadan gelir.
# Kullanim:
#   ./earl_prompt.sh sahne.txt "eylem cumlesi" "replik" "kamera hareketi"
# Ornek:
#   ./earl_prompt.sh M1.txt "lifts a glass mason jar toward the camera" \
#     "Store detergent is mostly water." "slowly pushes in"
set -euo pipefail
D="$(cd "$(dirname "$0")" && pwd)"
[ $# -eq 4 ] || { sed -n '2,8p' "$0"; exit 1; }
SAHNE="$1"; EYLEM="$2"; REPLIK="$3"; KAMERA="$4"
for f in earl_karakter.txt earl_ses.txt earl_stil.txt; do
  [ -s "$D/$f" ] || { echo "EKSIK: $D/$f" >&2; exit 1; }
done
[ -s "$SAHNE" ] || { echo "EKSIK sahne dosyasi: $SAHNE" >&2; exit 1; }

cat "$SAHNE"; echo
cat "$D/earl_karakter.txt" | sed '$ s/$/ — '"$EYLEM"'./'; echo
echo "He says: \"$REPLIK\""; echo
cat "$D/earl_ses.txt"; echo
echo "The camera $KAMERA."
cat "$D/earl_stil.txt"
