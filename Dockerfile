# One container: the API and the built frontend, served by one uvicorn on port 80.

# Build the frontend. Only the bundle: no type checking, linting or tests.
FROM node:24-slim AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npx vite build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FRONTEND_DIST=/app/frontend \
    DATABASE_URL=sqlite:////data/venn_manager.db
WORKDIR /app/backend
COPY backend/requirements.txt ./
# Runtime packages only; requirements.txt pins them and everything they pull in.
RUN pip install --no-cache-dir -c requirements.txt \
    fastapi uvicorn sqlalchemy alembic argon2-cffi tzdata
COPY backend/alembic.ini ./
COPY backend/migrations ./migrations
COPY backend/app ./app
COPY --from=frontend /build/dist /app/frontend
EXPOSE 80
# Migrations also seed the household and first admin on an empty database.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn --factory app.main:create_app --host 0.0.0.0 --port 80"]
