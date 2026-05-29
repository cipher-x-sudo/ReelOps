#!/usr/bin/env bash
set -euo pipefail

cd /app/backend
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8080}"

