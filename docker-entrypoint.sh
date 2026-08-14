#!/bin/sh
set -e

python <<'PY'
import os
import socket
import time

host = os.environ.get("POSTGRES_HOST", "db")
port = int(os.environ.get("POSTGRES_PORT", "5432"))

for _ in range(60):
    try:
        with socket.create_connection((host, port), timeout=2):
            break
    except OSError:
        time.sleep(1)
else:
    raise SystemExit(f"Postgres was not reachable at {host}:{port}")
PY

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec "$@"
