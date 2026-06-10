.PHONY: backend-test backend-run worker frontend infra-up infra-down ml-run ml-test pipeline k8s-apply load-test

backend-test:
	cd backend && .venv/bin/python manage.py test

backend-run:
	cd backend && .venv/bin/python manage.py runserver

worker:
	cd backend && .venv/bin/celery -A config worker --loglevel=info

frontend:
	cd frontend && npx ng serve student-portal

ml-run:
	cd ml-service && uvicorn app.main:app --port 9000 --reload

infra-up:
	cd infra && docker compose up --build -d

infra-down:
	cd infra && docker compose down

ml-test:
	cd ml-service && .venv/bin/python -m pytest tests/ -q

pipeline:
	cd ml-pipeline && PATH="$$PWD/.venv/bin:$$PATH" .venv/bin/dvc repro

k8s-apply:
	kubectl apply -k infra/k8s/

load-test:
	k6 run load-tests/catalog-read.js
