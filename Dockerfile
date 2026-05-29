FROM node:22-bookworm AS web

WORKDIR /app
COPY package.json ./
COPY frontend/package.json frontend/package.json
COPY renderer/package.json renderer/package.json
RUN npm install
COPY frontend frontend
COPY renderer renderer
RUN npm run build

FROM node:22-bookworm AS runtime

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/backend
ENV PATH=/opt/venv/bin:$PATH
ENV PORT=8080
ENV ARTIFACTS_DIR=/app/artifacts
ENV NICHES_DIR=/app/niches
ENV NICHE_CONFIGS_DIR=/app/configs/niches
ENV REMOTION_BROWSER_EXECUTABLE=/usr/bin/chromium

RUN apt-get update \
  && apt-get install -y --no-install-recommends python3 python3-venv python3-pip ffmpeg chromium fonts-liberation \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN python3 -m venv /opt/venv
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY --from=web /app/node_modules node_modules
COPY --from=web /app/package.json package.json
COPY --from=web /app/frontend/dist frontend/dist
COPY --from=web /app/renderer renderer
COPY backend backend
COPY configs configs
COPY niches niches
COPY docker/entrypoint.sh docker/entrypoint.sh
RUN chmod +x docker/entrypoint.sh && mkdir -p /app/artifacts /app/configs/niches

EXPOSE 8080
CMD ["docker/entrypoint.sh"]

