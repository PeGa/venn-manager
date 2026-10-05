# Venn Manager: compiled frontend served by nginx, FastAPI backend behind it,
# both in one container. See README.md § Docker.

# --- Frontend build ---------------------------------------------------------
FROM node:24-bookworm-slim AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- Runtime ----------------------------------------------------------------
FROM python:3.12-slim-bookworm
RUN apt-get update \
    && apt-get install -y --no-install-recommends nginx \
    && rm -rf /var/lib/apt/lists/* \
    && rm -f /etc/nginx/sites-enabled/default

WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./

COPY --from=frontend /build/dist /app/frontend
COPY docker/nginx.conf /etc/nginx/conf.d/venn-manager.conf
COPY docker/start.sh /app/start.sh

ENV DATABASE_URL=sqlite:////data/venn_manager.db \
    APP_ENV=development \
    PYTHONUNBUFFERED=1
VOLUME /data
EXPOSE 80
CMD ["bash", "/app/start.sh"]
