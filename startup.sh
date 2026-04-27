#!/usr/bin/env bash
set -euo pipefail

mkdir -p /home/data

echo "Installing Python dependencies..."
python -m pip install --no-cache-dir --user -r /home/site/wwwroot/requirements.txt

echo "Starting Gunicorn on port ${PORT:-8000}..."
exec python -m gunicorn \
  --chdir /home/site/wwwroot \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers 1 \
  --threads 4 \
  --timeout 600 \
  wsgi:app
