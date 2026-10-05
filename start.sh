#!/usr/bin/env bash
# Starts both services in the container. If either stops, the container stops.
set -euo pipefail

cd /app/backend
# Also seeds the household and first admin on an empty database.
alembic upgrade head
uvicorn --factory app.main:create_app --host 0.0.0.0 --port 8000 &

cd /app/frontend
npx vite preview --host 0.0.0.0 --port 80 --strictPort &

wait -n
exit $?
