#!/bin/sh
# n8n servisi giris noktasi. Seed ve kopru ayri compose servisleridir.
set -e
echo "[entrypoint] n8n baslatiliyor (user folder: $N8N_USER_FOLDER)"
exec n8n start
