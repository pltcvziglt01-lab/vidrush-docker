#!/usr/bin/env python3
"""Vidrush Docker self-seed — idempotent.
n8n bos bir hacimle acildiginda: owner kurar, 3 credential olusturur,
data table olusturur, workflow'u (credential ID'leri yeniden eslenerek) import
eder ve aktiflestirir. Ikinci kez calisirsa var olanlari atlar.

Env: N8N_URL, SEED_EMAIL, SEED_PASSWORD, TELEGRAM_TOKEN, OPENAI_KEY,
     PEXELS_KEY (ops.), WORKFLOW_FILE
"""
import json
import os
import re
import time
import urllib.request
import urllib.error
import urllib.parse

N8N = os.environ.get("N8N_URL", "http://n8n:5678").rstrip("/")
EMAIL = os.environ.get("SEED_EMAIL", "")
PASS = os.environ.get("SEED_PASSWORD", "")
TG = os.environ.get("TELEGRAM_TOKEN", "")
OAI = os.environ.get("OPENAI_KEY", "")
PEX = os.environ.get("PEXELS_KEY", "PEXELS_KEY_GIRILECEK")
WF_FILE = os.environ.get("WORKFLOW_FILE", "/opt/vidrush/workflow.json")

COOKIE = {"v": ""}


def istek(yol, veri=None, method=None, raw=False):
    url = N8N + yol
    data = None
    headers = {"Content-Type": "application/json"}
    if COOKIE["v"]:
        headers["Cookie"] = COOKIE["v"]
    if veri is not None:
        data = json.dumps(veri).encode()
    req = urllib.request.Request(url, data=data, headers=headers,
                                 method=method or ("POST" if data else "GET"))
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            sc = r.headers.get("Set-Cookie")
            if sc:
                COOKIE["v"] = sc.split(";")[0]
            body = r.read()
            return r.status, (body if raw else (json.loads(body) if body else {}))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def bekle():
    print("[seed] n8n bekleniyor...", flush=True)
    for _ in range(120):
        try:
            with urllib.request.urlopen(N8N + "/healthz", timeout=3) as r:
                if r.status == 200:
                    print("[seed] n8n hazir", flush=True)
                    return
        except Exception:
            pass
        time.sleep(2)
    raise SystemExit("[seed] n8n acilmadi")


def owner_login():
    sc, r = istek("/rest/owner/setup", {
        "email": EMAIL, "firstName": "Polat", "lastName": "Can", "password": PASS,
    })
    if sc in (200, 201):
        print("[seed] owner kuruldu", flush=True)
        return
    # zaten kurulu -> login
    sc, r = istek("/rest/login", {"emailOrLdapLoginId": EMAIL, "password": PASS})
    if sc == 200:
        print("[seed] login yapildi (zaten kurulu)", flush=True)
    else:
        raise SystemExit(f"[seed] owner/login basarisiz: {sc} {r}")


def cred_var(ad):
    sc, r = istek("/rest/credentials")
    data = r.get("data", r) if isinstance(r, dict) else []
    for c in (data or []):
        if c.get("name") == ad:
            return c["id"]
    return None


def cred_olustur(ad, tip, veri):
    mevcut = cred_var(ad)
    if mevcut:
        print(f"[seed] cred '{ad}' zaten var ({mevcut})", flush=True)
        return mevcut
    sc, r = istek("/rest/credentials", {"name": ad, "type": tip, "data": veri})
    d = r.get("data", r)
    cid = d.get("id")
    print(f"[seed] cred '{ad}' olusturuldu ({cid})", flush=True)
    return cid


def proje_id():
    sc, r = istek("/rest/projects")
    data = r.get("data", r)
    for p in data:
        if p.get("type") == "personal":
            return p["id"]
    return data[0]["id"]


def datatable_id(pid):
    # var mi?
    sc, r = istek(f"/rest/projects/{pid}/data-tables")
    data = (r.get("data", r) or {})
    liste = data.get("data", data) if isinstance(data, dict) else data
    if isinstance(liste, dict):
        liste = liste.get("data", [])
    for t in (liste or []):
        if isinstance(t, dict) and t.get("name") == "video_istekleri":
            return t["id"]
    sc, r = istek(f"/rest/projects/{pid}/data-tables", {
        "name": "video_istekleri",
        "columns": [
            {"name": "chat_id", "type": "string"},
            {"name": "metin", "type": "string"},
            {"name": "stil", "type": "string"},
            {"name": "durum", "type": "string"},
            {"name": "karakter", "type": "string"},
        ],
    })
    d = r.get("data", r)
    tid = d.get("id")
    print(f"[seed] data table olusturuldu ({tid})", flush=True)
    return tid


def wf_var():
    sc, r = istek("/rest/workflows?filter=" + urllib.parse.quote(json.dumps({"name": "Vidrush Tarzi Video Botu"})))
    data = r.get("data", r)
    if isinstance(data, list) and data:
        return data[0]["id"]
    return None


def kopru_bilgisi_yaz(wfid):
    """Kopru'nun okuyacagi webhook yolu + secret token'i paylasimli hacme yazar."""
    sc, r = istek(f"/rest/workflows/{wfid}")
    d = r.get("data", r)
    tetik = next((n for n in d["nodes"]
                  if n["type"] == "n8n-nodes-base.telegramTrigger"), None)
    if not tetik:
        print("[seed] UYARI: telegram trigger bulunamadi", flush=True)
        return
    webhook_id = tetik.get("webhookId", "")
    secret = re.sub(r"[^a-zA-Z0-9_\-]+", "", f"{wfid}_{tetik['id']}")
    bilgi = {
        "webhook_path": f"/webhook/{webhook_id}/webhook",
        "secret": secret,
    }
    hedef = "/opt/vidrush/seedinfo"
    os.makedirs(hedef, exist_ok=True)
    with open(os.path.join(hedef, "bridge.json"), "w") as f:
        json.dump(bilgi, f)
    print(f"[seed] kopru bilgisi yazildi: {bilgi}", flush=True)


def main():
    bekle()
    owner_login()

    tg_id = cred_olustur("Telegram Bot", "telegramApi",
                         {"accessToken": TG, "baseUrl": "https://api.telegram.org"})
    oai_id = cred_olustur("OpenAI Kisisel", "openAiApi",
                          {"apiKey": OAI, "url": "https://api.openai.com/v1"})
    pex_id = cred_olustur("Pexels API", "httpHeaderAuth",
                          {"name": "Authorization", "value": PEX})

    cred_map = {
        "telegramApi": {"id": tg_id, "name": "Telegram Bot"},
        "openAiApi": {"id": oai_id, "name": "OpenAI Kisisel"},
        "httpHeaderAuth": {"id": pex_id, "name": "Pexels API"},
    }

    pid = proje_id()
    tid = datatable_id(pid)

    wfid = wf_var()
    if wfid:
        print(f"[seed] workflow zaten var ({wfid})", flush=True)
    else:
        wf = json.load(open(WF_FILE))
        # data table id'sini yeni tabloya yonlendir
        s = json.dumps(wf)
        s = s.replace("8Qq90K7BJNxaUPuF", tid).replace("AsJTzSVKYsokANxY", tid)
        wf = json.loads(s)
        # credential ID'lerini yeni ID'lerle esle
        for n in wf["nodes"]:
            if n.get("credentials"):
                for t in list(n["credentials"].keys()):
                    if t in cred_map:
                        n["credentials"][t] = cred_map[t]
        govde = {"name": wf["name"], "nodes": wf["nodes"],
                 "connections": wf["connections"],
                 "settings": wf.get("settings", {"executionOrder": "v1"})}
        sc, r = istek("/rest/workflows", govde)
        d = r.get("data", r)
        wfid = d.get("id")
        print(f"[seed] workflow import edildi ({wfid})", flush=True)
        vid = d.get("versionId")
        sc, r = istek(f"/rest/workflows/{wfid}/activate", {"versionId": vid}, method="POST")
        d = r.get("data", r)
        print(f"[seed] workflow aktif: {d.get('active', r)}", flush=True)

    kopru_bilgisi_yaz(wfid)
    print("[seed] TAMAM", flush=True)


if __name__ == "__main__":
    main()
