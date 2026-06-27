FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# collectstatic needs a secret key but not a real DB
RUN DJANGO_SECRET_KEY=build-time-placeholder \
    DJANGO_DEBUG=False \
    python manage.py collectstatic --noinput

EXPOSE 8000

# Railway overrides this via railway.json startCommand (migrate + ensure_superuser + gunicorn)
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]
