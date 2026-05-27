#!/usr/bin/env bash
set -e
echo "Running database migrations..."
alembic upgrade head
echo "Starting uvicorn..."
uvicorn app.main:app --host 0.0.0.0 --port 10000
