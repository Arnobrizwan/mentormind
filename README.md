# 🧠 MentorMind

Scalable, ML-powered EdTech platform — a working demonstration of system design:
load balancing, Redis caching, Postgres read replication, background queues,
monitoring, and a full MLOps pipeline (data → model → deployment) — built
entirely on free-tier services.

## Architecture (local, via Docker Compose)

```
client ──► nginx (LB :8080) ──► api-1 / api-2 (Django + DRF + gunicorn)
                                   │            └─ X-Served-By header shows round-robin
                                   ├─► postgres-primary (writes)
                                   ├─► postgres-replica (reads, streaming replication)
                                   ├─► redis (cache · Celery broker · rate limits)
                                   └─► celery worker (emails, OTP, certificates, ML jobs)
            ml-service (FastAPI :9000) — PyTorch/OpenCV inference (Phase 4+)
            prometheus (:9090) + grafana (:3000) — metrics & dashboards
```

## Stack

| Layer | Tech |
|---|---|
| Backend | Django 6 + DRF + Celery + SimpleJWT (Python 3.14) |
| Frontend | Angular (latest) — `student-portal`, `instructor-studio`, `admin-console` |
| ML service | FastAPI (+ PyTorch / OpenCV from Phase 4) |
| Data | PostgreSQL primary + read replica, Redis |
| Infra | Docker Compose → Kubernetes (Phase 6), nginx LB |
| Observability | Prometheus, Grafana, django-prometheus `/metrics` |

## Dynamic-first, no hardcode

- `settings_engine` — every site setting is a DB row, Redis-cached, invalidated on save
- `flags` — feature flags toggle whole modules live from the admin panel
- All connection strings, hosts and instance identity come from environment variables

## Quick start (no Docker)

```bash
cd backend
python3.14 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py migrate && .venv/bin/python manage.py runserver
# http://127.0.0.1:8000/api/docs/  — Swagger UI
# http://127.0.0.1:8000/api/v1/health/

cd frontend && npx ng serve student-portal   # http://localhost:4200
```

## Full architecture demo (Docker)

```bash
cd infra && docker compose up --build
curl -i http://localhost:8080/api/v1/health/   # repeat: X-Served-By alternates api-1/api-2
```

## Repo layout

```
backend/      Django project (apps/: accounts, core, settings_engine, flags, ...)
frontend/     Angular workspace (3 applications)
ml-service/   FastAPI inference microservice
ml-pipeline/  DVC + MLflow training pipeline (Phase 5)
infra/        docker-compose, nginx, prometheus, grafana, k8s (Phase 6)
docs/         architecture notes
```

## Roadmap

1. ✅ Foundation — monorepo, Django + Angular + FastAPI skeletons, full Compose infra
2. ✅ Dynamic content engine + core learning — courses/lessons/quizzes/enrollment API with cache-aside + invalidation, and the student-portal Angular app (catalog, enrollment, lesson viewer, quiz taking, progress dashboard)
3. ✅ Infra showcase — nginx micro-cache, Redis leaderboard (sorted sets), R2/S3 uploads (avatars + course covers), Channels websocket chat, notifications with Celery email mirror
4. ✅ ML features — OpenCV proctoring (face count), grid OMR bubble-sheet grading, Tesseract OCR, co-occurrence course recommendations
5. ✅ MLOps — DVC pipeline (prepare→train→evaluate→drift), MLflow registry hooks, GitHub Actions train/deploy with drift gate, portable numpy-only model artifact served by ml-service
6. ✅ Kubernetes manifests (kustomize: api×2 + HPA, worker, ml-service, ingress), k6 load tests (read-path + student journey), `/system` live status page
