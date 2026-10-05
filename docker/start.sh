#!/usr/bin/env bash
# Migrate, then run the backend and nginx. If either stops, the container stops.
set -euo pipefail

cd /app/backend
alembic upgrade head

uvicorn --factory app.main:create_app --host 127.0.0.1 --port 8000 &
nginx -g 'daemon off;' &

wait -n
exit 1
