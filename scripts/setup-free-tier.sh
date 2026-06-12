#!/usr/bin/env bash
# Copy free-tier env templates and print next steps. No paid services required.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

cp "$ROOT/backend/.env.free" "$ROOT/backend/.env"
cp "$ROOT/ml-service/.env.free" "$ROOT/ml-service/.env"

cat <<EOF

✓ Free-tier env files installed:
    backend/.env
    ml-service/.env

What you get (all \$0):
  • SQLite database (no Postgres)
  • In-memory cache + WebSocket chat (no Redis)
  • Simulated premium checkout (no Stripe)
  • Corpus retrieval tutor (no OpenAI)
  • pypdf + Tesseract OCR (no Mistral)

Quick start:
  cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
  DEBUG=1 .venv/bin/python manage.py migrate && .venv/bin/python manage.py seed_demo
  DEBUG=1 .venv/bin/python manage.py runserver

  cd frontend && npm ci && npx ng serve student-portal

Optional local ML (still free):
  cd ml-service && pip install -r requirements.txt
  uvicorn app.main:app --port 9000
  # backend/.env already points TUTOR_MODEL_URL at HF Space; for local use:
  #   TUTOR_MODEL_URL=http://127.0.0.1:9000/v1/tutor/answer

Full guide: docs/FREE-DEMO-STACK.md

EOF
