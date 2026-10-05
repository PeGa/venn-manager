# One container, two services: the frontend (vite preview, port 80) and the
# backend (uvicorn, port 8000). The browser calls the backend port directly.

FROM node:24-slim AS node

FROM node AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
# The host port the browser reaches the backend on; baked into the bundle.
ARG VITE_API_PORT=8000
ENV VITE_API_PORT=${VITE_API_PORT}
# The bundle only: no type checking, linting or tests.
RUN npx vite build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATABASE_URL=sqlite:////data/venn_manager.db
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx
WORKDIR /app/backend
COPY backend/requirements.txt ./
# Runtime packages only; requirements.txt pins them and everything they pull in.
RUN pip install --no-cache-dir -c requirements.txt \
    fastapi uvicorn sqlalchemy alembic argon2-cffi tzdata
COPY backend/alembic.ini ./
COPY backend/migrations ./migrations
COPY backend/app ./app
COPY --from=frontend /app/frontend /app/frontend
COPY start.sh /app/start.sh
EXPOSE 80 8000
CMD ["bash", "/app/start.sh"]
