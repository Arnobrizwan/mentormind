.PHONY: backend-test backend-run worker frontend infra-up infra-down ml-run

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
