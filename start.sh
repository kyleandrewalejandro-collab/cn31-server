#!/bin/bash
set -e

export PYTHONUNBUFFERED=1
export PYTHONPATH=/app:$PYTHONPATH

cd /app

exec gunicorn \
  --bind 0.0.0.0:${PORT:-10000} \
  --workers 1 \
  --threads 8 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile - \
  app:app
