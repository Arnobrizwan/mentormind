# Contributing to MentorMind

Thanks for your interest! Issues and PRs are welcome.

## Getting set up

Follow the **Quick start** in the README (backend on Python 3.14, ml-service
on 3.13, frontend on Node ≥ 24.15). Then seed demo data:

```bash
cd backend && DEBUG=1 .venv/bin/python manage.py seed_demo
# Logins: student@mentormind.dev / instructor@mentormind.dev / admin@mentormind.dev
# Password: mentormind123
```

## Before you open a PR

```bash
ruff check backend ml-service                              # lint
cd backend && DEBUG=1 .venv/bin/python manage.py test     # backend suite
cd ml-service && .venv/bin/pytest                          # ml-service suite
cd frontend && npx ng build student-portal && npx ng build instructor-studio
```

All four must pass — CI runs the same checks.

## Ground rules

- **No third-party AI APIs.** The self-hosted constraint is the point of the
  project. LLM features go through `ml-service` (local model or an
  OpenAI-compatible self-hosted server) and must have a heuristic fallback.
- **AI output needs a human gate or grounding.** Generated flashcards/quizzes
  stay unpublished until an instructor approves; tutor answers are grounded
  in mark schemes.
- **Dynamic-first.** New knobs should be SiteSettings or env vars, not
  constants.
- **Tests with features.** New endpoints and models ship with tests in the
  app's `tests.py`.
- If you change tutor prompts or retrieval thresholds, run the eval gate
  (`ml-service/scripts/eval_tutor.py`) before and after, and include both
  numbers in the PR description.

## Commit style

Conventional-ish: `feat(backend): ...`, `fix(ml-service): ...`,
`docs(readme): ...` — match `git log`.
