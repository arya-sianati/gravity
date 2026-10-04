#!/usr/bin/env bash
set -euo pipefail

# Gravity Production Deployment Script
PROJECT_ROOT="/home/mule/gravity"
cd "${PROJECT_ROOT}"

echo "=== [1/5] Updating repository code ==="
git pull origin main

echo "=== [2/5] Running Django database migrations ==="
"${PROJECT_ROOT}/backend/venv/bin/python" "${PROJECT_ROOT}/backend/manage.py" migrate --noinput

echo "=== [3/5] Collecting Django static assets ==="
"${PROJECT_ROOT}/backend/venv/bin/python" "${PROJECT_ROOT}/backend/manage.py" collectstatic --noinput

echo "=== [4/5] Building frontend production PWA ==="
cd "${PROJECT_ROOT}/frontend"
npm run build
cd "${PROJECT_ROOT}"

echo "=== [5/5] Restarting services ==="
sudo systemctl restart gravity.service
sudo systemctl reload nginx

echo "=== Gravity deployment completed successfully! ==="
