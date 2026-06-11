# 🧠 MentorMind

Scalable, ML-powered EdTech platform — a working demonstration of system design
**and** applied AI: load balancing, Redis caching, Postgres read replication,
background queues, monitoring, a full MLOps pipeline (data → model → deployment),
and a **fully self-hosted AI tutor** fine-tuned on real Cambridge past papers —
built entirely on free-tier services. No third-party AI APIs anywhere.

## Architecture (local, via Docker Compose)

```
client ──► nginx (LB :8080) ──► api-1 / api-2 (Django + DRF + gunicorn)
                                   │            └─ X-Served-By header shows round-robin
                                   ├─► postgres-primary (writes)
                                   ├─► postgres-replica (reads, streaming replication)
                                   ├─► redis (cache · Celery broker · rate limits)
                                   └─► celery worker + beat (emails, badges, weekly
                                        dropout-risk scan, weekly study plans)
            ml-service (FastAPI :9000) — local LLM tutor · rubric grader ·
                                         flashcard/MCQ generation · OpenCV vision ·
                                         dropout-risk scoring
            prometheus (:9090) + grafana (:3000) — metrics & dashboards
```

## Stack

| Layer | Tech |
|---|---|
| Backend | Django 6 + DRF + Celery (worker + beat) + SimpleJWT (Python 3.14) |
| Frontend | Angular (latest, signals + standalone) — `student-portal` (:4200), `instructor-studio` (:4201), `admin-console` (:4202), `shared` lib |
| Mobile | Capacitor (iOS + Android) wrapping the student portal — same codebase, native camera/mic |
| ML service | FastAPI + PyTorch (MPS/CUDA/CPU) + transformers/peft + OpenCV (Python 3.13) |
| Tutor model | Qwen2.5-0.5B-Instruct + LoRA adapter fine-tuned on aligned Cambridge past papers, served in-process |
| Data | PostgreSQL primary + read replica, Redis, SQLite (past-paper corpus) |
| Infra | Docker Compose → Kubernetes (kustomize), nginx LB, GitHub Actions CI |
| Observability | Prometheus, Grafana, django-prometheus + prometheus-fastapi-instrumentator `/metrics` |

## AI learning features

All model output that reaches students is either grounded in official mark
schemes or reviewed by an instructor first. Every LLM feature has an offline
heuristic fallback, so nothing 503s when no model is loaded.

| Feature | How it works |
|---|---|
| 🤖 **AI tutor** | Retrieval-first over 68k+ aligned past-paper questions (strong match returns the *official mark scheme*, attributed); weak/no match falls to the fine-tuned local LLM with retrieved grounding. Daily quota, premium unlimited, thumbs feedback. |
| 📷 **Multimodal tutoring** | Photograph a textbook question — OCR'd by the ml-service, answered like typed text. |
| 🎤 **Voice tutoring** | Dictate questions (SpeechRecognition) and have answers read aloud (speechSynthesis); feature-detected. |
| 📝 **Short-answer grading** | Free-text answers graded against instructor mark schemes — LLM emits a structured criteria breakdown (met ✓ / missing ✗ + feedback); criterion-recall heuristic fallback. Attempt caps, mark scheme never exposed to students. |
| 🃏 **Spaced repetition** | SM-2 flashcard queue. AI drafts cards from lesson content; drafts are unpublished until the instructor approves. Reviews feed the points/streak system (farming-proof: only due cards grade). |
| 🎯 **Adaptive practice** | Per-question results + topic tags → weak-topic accuracy stats → "Focus areas" feed recommending exactly what to practise next. |
| 📋 **Agentic study planner** | Weekly Celery sweep builds each student a plan (due cards, weak topics, next lessons, unattempted quizzes), nudges them, and **escalates**: two slipping weeks open a remediation ticket for a human. |
| ✨ **AI quiz drafting** | Instructors generate MCQ drafts from a lesson; questions are edited and confirmed before anything is saved — never auto-published. |
| 🚨 **Exam proctoring** | Webcam frames every 12s during quizzes → face-count verdicts (never images) → instructor timeline; edge-triggered alert after 3 consecutive flagged frames. |
| 📈 **Dropout-risk remediation** | Weekly scan scores every student (logistic model served by ml-service); high risk → encouragement nudge + ticket in the instructor "Student Success" queue (scoped per-instructor, single-flight scans). |
| 🎓 **Exam readiness** | 0–100 blend of progress, quiz average, practice volume, accuracy (weights live-tunable). Rings on the student dashboard, weakest-first column on the instructor roster. |
| 🏅 **Gamification** | Points ledger, streaks, badges (DB-defined rules), weekly leaderboard, daily login rewards. |

## The tutor model pipeline (fully self-hosted)

```
Cambridge PDFs ─► OCR + QP/MS alignment (pastpapers pipeline) ─► aligned corpus (68k+ Q/A)
       ─► scripts/train_tutor.py (LoRA fine-tune, runs on Apple-Silicon MPS)
       ─► models/tutor-lora ─► served in-process (LOCAL_LLM=1) or via any
          OpenAI-compatible server (CUSTOM_LLM_URL: vLLM / llama.cpp / Ollama)
```

**Evaluation gate** (Self-Harness style, arXiv:2606.09498): before/after any
prompt or threshold change, run

```bash
cd ml-service && .venv/bin/python scripts/eval_tutor.py --max 40
```

— deterministic held-in/held-out splits, leave-one-out answering, mark-scheme
token recall. Accept a change only if held-in improves without held-out
degrading. Mine real failure clusters from student feedback with
`python manage.py mine_tutor_failures`.

## Dynamic-first, no hardcode

- `settings_engine` — every site setting is a DB row, Redis-cached, invalidated on save;
  all Angular apps bootstrap branding from `/api/v1/settings/public/`
- `flags` — feature flags toggle whole modules live (chat, recommendations, ai_tutor,
  short_answer_grading, flashcard_generation, quiz_generation, proctoring…; the ML
  service polls `/api/v1/flags/` and fails open)
- Tunable without redeploys: quotas, attempt caps, readiness weights, retrieval
  thresholds, points values, scan schedules — env vars or SiteSettings

## Quick start (no Docker)

```bash
# Backend (Python 3.14)
cd backend
python3.14 -m venv .venv && .venv/bin/pip install -r requirements.txt
DEBUG=1 .venv/bin/python manage.py migrate
DEBUG=1 .venv/bin/python manage.py runserver
# http://127.0.0.1:8000/api/docs/  — Swagger UI

# ML service (Python 3.13) — .env enables the local LLM tutor
cd ml-service
python3.13 -m venv .venv && .venv/bin/pip install -r requirements.txt
# .env: LOCAL_LLM=1, LOCAL_LLM_BASE=Qwen/Qwen2.5-0.5B-Instruct (adapter
# defaults to models/tutor-lora). Needs torch/transformers/peft for LLM mode.
.venv/bin/uvicorn app.main:app --port 9000

# Frontend (Node ≥ 24.15 — Homebrew node works; nvm 24.11 is rejected)
cd frontend && npx ng serve student-portal   # http://localhost:4200
npx ng serve instructor-studio               # http://localhost:4201
```

Point Django at the ML service with `ML_SERVICE_URL=http://localhost:9000`,
`TUTOR_MODEL_URL=http://localhost:9000/v1/tutor/answer` and a shared `ML_API_KEY`.

## Mobile app (Capacitor)

The student portal ships as a native iOS/Android app — same code, every feature,
with native camera (proctoring, photo questions) and microphone (dictation)
permissions wired up.

```bash
cd frontend
MM_API_BASE_URL=https://api.your-host npm run build:mobile   # build + inject API origin + cap sync
npm run run:android    # or run:ios / open:android / open:ios
```

## Full architecture demo (Docker)

```bash
cd infra && docker compose up --build
curl -i http://localhost:8080/api/v1/health/   # repeat: X-Served-By alternates api-1/api-2
```

## Tests & CI

```bash
cd backend && DEBUG=1 .venv/bin/python manage.py test    # 109 tests
cd ml-service && .venv/bin/pytest                        # 71 tests (hermetic — no model load)
cd frontend && npx ng build student-portal && npx ng build instructor-studio && npx ng build shared
```

GitHub Actions CI runs ruff (backend + ml-service), both Python suites, and the
Angular builds on every push. `ml-train.yml` retrains on demand; `load-test.yml`
runs the k6 scenarios.

## Repo layout

```
backend/      Django project (apps/: accounts, core, tutor, revision, planner,
              engagement, chat, notifications, settings_engine, flags)
frontend/     Angular workspace (3 apps + shared lib) + Capacitor ios/ & android/
ml-service/   FastAPI inference microservice (LLM tutor, grading, generation,
              vision, dropout) + training & evaluation scripts
ml-pipeline/  DVC + MLflow training pipeline (dropout model)
infra/        docker-compose, nginx, prometheus, grafana, k8s (kustomize)
docs/         architecture notes
```

## Roadmap

1. ✅ Foundation — monorepo, Django + Angular + FastAPI skeletons, full Compose infra
2. ✅ Dynamic content engine + core learning — courses/lessons/quizzes/enrollment with cache-aside + invalidation; student portal (catalog, lessons, quizzes, dashboard)
3. ✅ Infra showcase — nginx micro-cache, Redis leaderboard, R2/S3 uploads, Channels websocket chat, notifications with Celery email mirror
4. ✅ ML features — OpenCV proctoring, OMR bubble-sheet grading, Tesseract OCR, co-occurrence recommendations
5. ✅ MLOps — DVC pipeline (prepare→train→evaluate→drift), MLflow registry hooks, GitHub Actions train/deploy with drift gate
6. ✅ Kubernetes manifests (api×2 + HPA, worker, ml-service, ingress), k6 load tests, `/system` live status page
7. ✅ Self-hosted AI tutor — past-paper OCR/alignment pipeline, LoRA fine-tune, retrieval-grounded serving, multimodal + voice input
8. ✅ AI assessment & intervention — rubric grading, AI quiz/flashcard drafting with human review, proctoring timelines, dropout remediation loop
9. ✅ Adaptive learning — weak-topic practice, SM-2 spaced repetition, agentic weekly study plans, exam-readiness scoring
10. ✅ Mobile — Capacitor iOS/Android app with native camera/mic
