# datafast — Gemini Vision document-to-data SaaS

Secure, modular Django + DRF application that extracts structured JSON from
uploaded invoices/bills using the Gemini Vision API, stores it relationally,
and visualizes it with a 3D-animated analytics dashboard styled in the DataFast
design language.

## Highlights

- **Auth + RBAC + approval gate** — custom user, Argon2 hashing, strong-password
  rule, login rate-limiting; users are inactive until an admin approves and
  assigns a role (Admin / Manager / Analyst / Viewer). Roles gate every page & API.
- **Multi-file upload** — drag & drop, client progress, magic-byte validation,
  async processing (Celery + Redis; runs eagerly in dev).
- **Token-optimized Gemini engine** — one cached system instruction, a one-word
  per-image prompt, `response_mime_type=application/json` + compact response
  schema → strict JSON, validated/coerced before storage. Offline mock keeps the
  whole flow runnable with no API key.
- **Relational storage** — `ExtractedDocument` (+ denormalized fields & indexes)
  and `InvoiceItem` for analytics; every row has created/updated/processed
  timestamps and an owner.
- **Data viewer** — JSON view, sortable/filterable table, **Save to database**
  with a **category selector that supports adding a new category inline**, plus
  CSV / Excel / JSON export (filters applied before export).
- **3D analytics** — Three.js animated revenue ribbon, growing product bars and
  a rotating vendor-share pie, fed by cached DB aggregations.
- **Security** — CSRF, session+JWT, scoped rate limits, file sanitization,
  prompt-injection-resistant Gemini input, audit logging, secrets via env only.

## Project layout

```
datafast/
  config/            settings, urls, celery, wsgi/asgi
  apps/
    core/            TimeStampedModel, Category, AuditLog, middleware, landing/dashboard
    users/           custom User, RBAC perms, approval workflow, JWT
    uploads/         upload session/file, validation, async kickoff
    processing/      Gemini service, strict schema, Celery task, models, exporters, save-to-DB
    analytics/       cached aggregation services + API
  templates/         DataFast landing + app shell + pages
  static/css|js/     design system + app/upload/data/analytics3d/landing3d JS
  tests/             schema, gemini mock, validators, full upload→save flow
```

## Quick start (Docker)

```bash
cp .env.example .env          # set GEMINI_API_KEY (optional), secrets
docker compose up --build
docker compose exec web python manage.py createsuperuser
# open http://localhost:8000
```

## Local (no Docker)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # leave POSTGRES_DB / REDIS_URL / GEMINI_API_KEY empty
                              # to use SQLite + eager Celery + mock Gemini
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
# for real async: redis-server &  and  celery -A config worker -l info
```

## Workflow

1. Register → account is inactive.
2. Admin (Users page) approves and assigns a role.
3. Upload invoices (Upload page) → async Gemini extraction.
4. Review each extraction (Data viewer), pick/add a **category**, **Save to
   database** or **download** (CSV/Excel/JSON).
5. Explore the **3D Analytics** dashboard (revenue trend, top products, vendor share).

## Security notes

- Secrets (`GEMINI_API_KEY`, DB password, `DJANGO_SECRET_KEY`) come only from
  the environment / `.env`.
- Gemini receives image bytes + a fixed instruction; user text never enters the
  instruction, mitigating prompt injection. Output is parsed defensively and
  schema-validated before any DB write.
- Audit log records logins, uploads, exports, data saves and admin actions.

## Tests

```bash
pytest          # schema, gemini mock, validators, upload→extract→save flow, RBAC
```

> Note: migrations are generated on first `makemigrations` (not committed here).
