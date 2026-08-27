#!/usr/bin/env bash
# Bir video tanimindan 6 klibin promptunu basar.
# Ses blogu ASLA elle yazilmaz — hep oryn_ses.txt'ten gelir.
#
# Kullanim:  ./oryn_video.sh videolar/deterjan.txt
#
# Tanim dosyasi bicimi — 6 satir, alanlar | ile ayrilir, # yorum:
#   MEKAN | EYLEM | REPLIK | KAMERA
# MEKAN: M1 M2 M3 M4  (M1.txt vb. dosyalari okunur)
set -euo pipefail
D="$(cd "$(dirname "$0")" && pwd)"
TANIM="${1:?kullanim: ./oryn_video.sh videolar/<konu>.txt [klip_sn]}"
SN="${2:-10}"          # Flow'da secili klip suresi. 6 / 8 / 10
# Earl yavas konusur: ~1.8 kelime/sn — Oryn Earl.den daha yavas konusur. Tavan = sure x 2.2, asagi yuvarlanir.
TAVAN=$(awk -v s="$SN" 'BEGIN{printf "%d", s*2.2}')
[ -s "$TANIM" ] || { echo "EKSIK tanim: $TANIM" >&2; exit 1; }
for f in oryn_karakter.txt oryn_ses.txt oryn_stil.txt oryn_sureklilik.txt; do
  [ -s "$D/$f" ] || { echo "EKSIK blok: $D/$f" >&2; exit 1; }
done

n=0
while IFS='|' read -r mekan eylem replik kamera; do
  case "${mekan// /}" in ''|'#'*) continue ;; esac
  n=$((n+1))
  mekan="${mekan// /}"
  eylem="$(echo "$eylem" | sed 's/^ *//;s/ *$//')"
  replik="$(echo "$replik" | sed 's/^ *//;s/ *$//')"
  kamera="$(echo "$kamera" | sed 's/^ *//;s/ *$//')"
  [ -s "$D/$mekan.txt" ] || { echo "EKSIK mekan: $D/$mekan.txt" >&2; exit 1; }
  kelime=$(echo "$replik" | wc -w | tr -d ' ')
  # Cok eylemli klipte konusmaya daha az yer kalir — tavani biraz kis.
  beat=$(echo "$eylem" | tr ',' '\n' | wc -l | tr -d ' ')
  then_n=$( { echo "$eylem" | grep -o ' then \| and ' || true; } | wc -l | tr -d ' ')
  beat=$((beat + then_n))
  if [ "$beat" -ge 4 ]; then tavan=$((TAVAN - 3)); tip="eylemli"; else tavan=$TAVAN; tip="konusan"; fi
  if [ "$kelime" -gt "$tavan" ]; then
    echo "!! KLIP $n [$tip] $kelime kelime — ${SN}sn icin tavan $tavan. Konusma yarim kalir." >&2
  fi
  echo "########## KLIP $n  ($mekan · $kelime kelime · $tip · ${SN}sn) ##########"
  cat "$D/$mekan.txt"; echo
  sed '$ s/$/ — '"$eylem"'./' "$D/oryn_karakter.txt"; echo
  echo "He says: \"$replik\""; echo
  cat "$D/oryn_sureklilik.txt"; echo
  cat "$D/oryn_ses.txt"; echo
  echo "The camera $kamera."
  cat "$D/oryn_stil.txt"
  echo
done < "$TANIM"

[ "$n" -eq 3 ] || echo "!! $n klip bulundu, 3 olmali" >&2
