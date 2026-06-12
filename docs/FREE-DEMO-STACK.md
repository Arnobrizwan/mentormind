# MentorMinds — 100% free demo stack ($0/month)

Everything below has a **real free tier** (no credit card required unless noted). This is what powers [mentormind-demo.vercel.app](https://mentormind-demo.vercel.app) and the public APK.

## What you need (all free)

| Piece | Free service | URL / limit | You already have |
|-------|--------------|-------------|------------------|
| **Student UI** | [Vercel Hobby](https://vercel.com) | 100 GB bandwidth/mo, unlimited static deploys | `mentormind-demo.vercel.app` |
| **Instructor UI** | Vercel Hobby (2nd project) | Same | `mentormind-studio.vercel.app` |
| **Admin UI** | Vercel Hobby (3rd project, optional) | Same | Deploy if needed |
| **Django API** | [Render Free](https://render.com) | 750 hrs/mo, sleeps after 15 min idle | `mentormind-api.onrender.com` |
| **ML / tutor** | [Hugging Face Spaces](https://huggingface.co/spaces) CPU Basic | 2 vCPU, 16 GB RAM, sleeps after 48h idle | `arnob666666-mentormind-ml.hf.space` |
| **Corpus dataset** | [HF Datasets](https://huggingface.co/datasets) private | Free storage for `pastpapers.db` | `ARNOB666666/mentormind-corpus` |
| **Keep-warm pings** | [GitHub Actions](https://github.com/features/actions) | 2,000 min/mo on free repos | `.github/workflows/keepalive.yml` |
| **Fonts** | [Google Fonts](https://fonts.google.com) | Free CDN | Unbounded, Plus Jakarta Sans |
| **Code + APK** | GitHub | Free public repo + Releases | This repo |
| **Android build** | Local SDK + Capacitor | Free | `docs/releases/mentormind-demo.apk` |

**Not needed for demo:** OpenAI, Stripe, Redis, Postgres, Mistral OCR, paid GPUs.

## One secret to sync (demo ML key)

Render and the HF Space must share the **same** `ML_API_KEY`. The repo uses a public demo value (fine for a read-only inference demo):

```
mentormind-public-demo-ml-key
```

Set on:

1. **Render** → `mentormind-api` → Environment → `ML_API_KEY` (or redeploy from `render.yaml`)
2. **HF Space** → Settings → Variables → `ML_API_KEY` = same string

Do **not** use `generateValue` on Render alone — the Space would reject requests.

## Sign-up checklist (15 minutes)

1. **GitHub** — fork/clone this repo (free).
2. **Render** — [Deploy button](https://render.com/deploy?repo=https://github.com/Arnobrizwan/mentormind) → uses `render.yaml` (free web service).
3. **Vercel** — import repo, **Root Directory** `frontend`, build:
   - Student: `npx ng build student-portal --configuration production`
   - Output: `dist/student-portal/browser`
   - Add rewrite: `/*` → `/index.html` (see `frontend/vercel.student-portal.json`)
4. **Hugging Face** — create **Docker Space** from `ml-service/Dockerfile`, set secrets:
   - `ML_API_KEY=mentormind-public-demo-ml-key`
   - `HF_TOKEN` = your read token (download private corpus dataset)
   - `DATASET_REPO=ARNOB666666/mentormind-corpus` (if used by Space startup script)
5. **Render CORS** — include your Vercel URL + `https://localhost` for the APK (already in `render.yaml`).

## Free-tier quirks (expected)

| Symptom | Cause | Mitigation |
|---------|-------|------------|
| First page load ~40–60s | Render cold start | GitHub keep-alive every 10 min + in-app “Waking server” banner |
| Tutor slow first time | HF Space slept 48h | keepalive pings `/healthz` on the Space |
| Demo data resets | Render free SQLite is ephemeral | `seed_demo` on every deploy — by design |
| WebSocket chat | Needs Render **paid** or Redis for multi-worker | Free tier uses 2 gunicorn workers; chat works on single instance |

## Local dev ($0)

```bash
# Backend — no keys required
cd backend && python -m venv .venv && .venv/bin/pip install -r requirements.txt
DEBUG=1 .venv/bin/python manage.py migrate && .venv/bin/python manage.py seed_demo
DEBUG=1 .venv/bin/python manage.py runserver

# Frontend
cd frontend && npm ci && npx ng serve student-portal
```

Optional local ML (still free, self-hosted):

```bash
cd ml-service && pip install -r requirements.txt
ML_ALLOW_UNAUTHENTICATED=1 uvicorn app.main:app --port 9000
# In backend .env: TUTOR_MODEL_URL=http://localhost:9000/v1/tutor/answer
```

## What we deliberately did **not** use (paid)

- OpenAI / Anthropic / Gemini APIs  
- Vercel Postgres / Neon (demo uses SQLite on Render)  
- Render paid instance (no always-on)  
- HF GPU / ZeroGPU (CPU retrieval tutor is enough for DIGITEX)  
- Apple Developer ($99/yr) — Android APK sideload is free; iOS needs paid account to ship  

## DIGITEX booth kit (free)

- Poster PNG/PPTX in `docs/poster/`
- Web demo: student Vercel URL
- Phone: install `docs/releases/mentormind-demo.apk` (login `student@mentormind.dev` / `mentormind123`)
- Laptop: instructor studio URL for proctoring/OMR if needed
