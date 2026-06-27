#!/usr/bin/env sh
set -e

echo "==> PORT is: ${PORT}"

echo "==> Waiting for database..."
python - <<'EOF'
import os, time, sys
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()
from django.db import connection
for i in range(30):
    try:
        connection.ensure_connection()
        print(f"DB ready after {i+1} attempt(s).")
        break
    except Exception as e:
        print(f"Attempt {i+1}/30 failed: {e}")
        time.sleep(2)
else:
    print("Could not connect to DB after 30 attempts.")
    sys.exit(1)
EOF

echo "==> Running migrations..."
python manage.py migrate --noinput

echo "==> Ensuring superuser..."
python manage.py ensure_superuser

echo "==> Starting gunicorn on port ${PORT:-8000}..."
exec gunicorn config.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers 2 \
    --timeout 120 \
    --graceful-timeout 30
