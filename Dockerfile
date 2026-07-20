# Vidrush Video Botu — hepsi-bir-arada imaj
# Debian tabanli (Remotion'un Chrome'u glibc ister; Alpine'da CALISMAZ).
# Node 22: n8n 2.29.9 node>=22.22 ister.
FROM node:22-bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

# Sistem bagimliliklari: python, ffmpeg, chromium + Chrome/headless icin kutuphaneler, fontlar
RUN apt-get update && apt-get install -y --no-install-recommends \
      python3 python3-pip python3-venv \
      ffmpeg chromium \
      ca-certificates fonts-dejavu-core fonts-noto-core fonts-liberation \
      dumb-init tini \
      libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
      libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
      libgbm1 libpango-1.0-0 libcairo2 libasound2 libatspi2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# edge-tts (ucretsiz Azure sesleri) — sanal ortam PEP668 icin
RUN python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir edge-tts==7.2.8
ENV PATH="/opt/venv/bin:${PATH}"

# n8n (host ile ayni surum). isolated-vm native derleme icin build araclari
# gecici kurulur, ayni katmanda temizlenir (imaj sismesin).
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential python3-dev \
    && npm install -g n8n@2.29.9 \
    && npm cache clean --force \
    && apt-get purge -y build-essential python3-dev \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# Uygulama: render-studio + uret.py + kopru.py
WORKDIR /opt/vidrush
COPY app/render-studio/package.json app/render-studio/package-lock.json ./render-studio/
RUN cd render-studio && npm install --no-audit --no-fund && npm cache clean --force
COPY app/render-studio/ ./render-studio/
COPY app/uret.py app/kopru.py ./

# Web arayuzu Python bagimliliklari (GEC katman: n8n/render-studio onbellegini bozmaz)
RUN /opt/venv/bin/pip install --no-cache-dir \
       fastapi==0.115.6 "uvicorn[standard]==0.34.0" \
       python-multipart==0.0.20 requests==2.32.3 Pillow==11.1.0

# Seed + web arayuzu + calisma dosyalari
COPY seed.py entrypoint.sh ./
COPY workflow.json ./
COPY webapp ./webapp
RUN chmod +x entrypoint.sh \
    && mkdir -p render-studio/public/isler render-studio/out seedinfo \
       webapp/veri/presets webapp/ciktilar /home/node/.n8n \
    && chown -R node:node /opt/vidrush /home/node/.n8n

# Remotion Docker ayarlari
ENV REMOTION_BROWSER_EXECUTABLE=/usr/bin/chromium
ENV REMOTION_GL=swangle
ENV CHROMIUM_FLAGS="--no-sandbox"

USER node
ENV N8N_USER_FOLDER=/home/node
EXPOSE 5678
ENTRYPOINT ["tini", "--"]
CMD ["./entrypoint.sh"]
