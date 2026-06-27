#!/usr/bin/env sh
# Railway release command — runs after deploy, before traffic is switched.
# Retries DB connection up to 30 times (handles cold-start Postgres).
set -e

echo "==> Waiting for database..."
python - <<'EOF'
import os, time, sys
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
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

echo "==> Release complete."
