#!/usr/bin/env python3
"""Telegram -> lokal n8n koprusu.
Telegram'dan long-polling ile guncellemeleri ceker (getUpdates),
her birini n8n'in lokal webhook adresine POST eder.
Tunel gerektirmez; sadece giden HTTPS (443) kullanir.
"""
import json
import os
import time
import urllib.request
import urllib.error

TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
assert TOKEN, "TELEGRAM_TOKEN env degiskeni gerekli"
API = f"https://api.telegram.org/bot{TOKEN}"
N8N_WEBHOOK = os.environ.get(
    "N8N_WEBHOOK",
    "http://localhost:5678/webhook/9defa455-c351-40c0-aaa8-5c1a46ae633f/webhook",
)
SECRET = os.environ.get("N8N_SECRET", "OrUAUA3rBeX05bBA_84712b58-4ccd-4278-9f64-b6747a5d9299")

# Docker: seed'in yazdigi dinamik webhook yolu + secret varsa onu kullan
_bilgi = "/opt/vidrush/seedinfo/bridge.json"
if os.path.exists(_bilgi):
    try:
        _b = json.load(open(_bilgi))
        _base = os.environ.get("N8N_BASE", "http://n8n:5678").rstrip("/")
        N8N_WEBHOOK = _base + _b["webhook_path"]
        SECRET = _b["secret"]
        print(f"[kopru] seed bilgisi yuklendi: {N8N_WEBHOOK}", flush=True)
    except Exception as _e:
        print(f"[kopru] seed bilgisi okunamadi ({_e}), env/varsayilan kullanilacak", flush=True)

offset = 0
print("Kopru basladi. Telegram -> n8n aktarimi calisiyor...", flush=True)
while True:
    try:
        url = f"{API}/getUpdates?timeout=25&offset={offset}&allowed_updates=%5B%22message%22,%22callback_query%22%5D"
        with urllib.request.urlopen(url, timeout=40) as r:
            data = json.loads(r.read())
        for upd in data.get("result", []):
            body = json.dumps(upd).encode()
            req = urllib.request.Request(
                N8N_WEBHOOK, data=body,
                headers={
                    "Content-Type": "application/json",
                    "x-telegram-bot-api-secret-token": SECRET,
                }, method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    print(f"iletildi update_id={upd['update_id']} -> {resp.status}", flush=True)
                offset = upd["update_id"] + 1
            except urllib.error.HTTPError as e:
                print(f"n8n hata update_id={upd['update_id']} -> {e.code} {e.read()[:200]}", flush=True)
                offset = upd["update_id"] + 1
            except Exception as e:
                print(f"n8n ulasilamadi, mesaj bekletiliyor: {e}", flush=True)
                time.sleep(5)
                break
    except Exception as e:
        if "409" in str(e):
            try:
                with urllib.request.urlopen(f"{API}/deleteWebhook", timeout=15) as r:
                    print("webhook silindi (409 onarimi):", r.read()[:100], flush=True)
            except Exception as e2:
                print(f"webhook silinemedi: {e2}", flush=True)
            time.sleep(2)
        elif "timed out" in str(e).lower() or "errno 8" in str(e).lower() or "errno 54" in str(e).lower() or "errno 51" in str(e).lower():
            globals()["_to"] = globals().get("_to", 0) + 1
            if globals()["_to"] % 10 == 1:
                print(f"gecici ag sorunu (x{globals()['_to']}): {e} - devam", flush=True)
            time.sleep(1)
        else:
            print(f"dongu hatasi: {e} - 5 sn sonra tekrar", flush=True)
            time.sleep(5)
