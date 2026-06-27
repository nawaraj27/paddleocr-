# Setup / verification notes

This codebase was authored and **syntax-verified** (every `.py` compiles, every
`.js` passes `node --check`) but **not executed**, because the build environment
has no network to install Django/DRF/Celery/google-generativeai and no
Postgres/Redis/Gemini credentials.

Before first run you must:
1. `pip install -r requirements.txt`
2. `python manage.py makemigrations users core uploads processing analytics`
3. `python manage.py migrate`
4. `python manage.py createsuperuser` (becomes an approved Admin)

With no `GEMINI_API_KEY`, the system uses a deterministic **mock extractor**, so
you can exercise upload → extraction → save → analytics end-to-end offline. Set
`GEMINI_API_KEY` to switch to the real Gemini Vision API.
