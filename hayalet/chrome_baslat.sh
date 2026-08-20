#!/bin/bash
# Chrome'u UZAKTAN KONTROL portuyla baslatir (Hayalet buna baglanir).
# ⚠ Mevcut Chrome profilin ve Google oturumun AYNEN kullanilir.
PORT="${HAYALET_CHROME_PORT:-9222}"
case "$(uname -s)" in
  Darwin) CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";;
  Linux)  CHROME="$(command -v google-chrome || command -v chromium || command -v chromium-browser)";;
  *)      CHROME="$(command -v chrome)";;
esac
[ -x "$CHROME" ] || { echo "HATA: Chrome bulunamadi"; exit 1; }
if curl -s --max-time 2 "http://127.0.0.1:$PORT/json/version" >/dev/null 2>&1; then
  echo "✓ Chrome zaten $PORT portunda dinliyor"; exit 0
fi
echo "Chrome baslatiliyor (port $PORT)…"
"$CHROME" --remote-debugging-port="$PORT" \
  --user-data-dir="$HOME/.hayalet/chrome-profil" >/dev/null 2>&1 &
sleep 3
curl -s --max-time 3 "http://127.0.0.1:$PORT/json/version" >/dev/null 2>&1 \
  && echo "✓ hazir — acilan pencerede Google hesabina giris yap" \
  || echo "⚠ port yanit vermedi, birkaç saniye sonra tekrar dene"
