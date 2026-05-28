#!/usr/bin/env bash
set -e
alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port 10000 --workers 4 --log-config app/logging.conf
