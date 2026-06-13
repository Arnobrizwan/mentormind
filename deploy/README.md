# Deploying MentorMind to a single VPS (Contabo SG 8 GB)

One server runs the whole backend — Django API, Celery worker, the in-process
AI tutor (`ml-service`), Postgres and Redis — behind **Caddy** with automatic
HTTPS. The three Angular frontends stay on **Vercel** (free static hosting);
only the API lives here.

```
                         ┌─────────────────── VPS (Contabo SG, 8 GB) ───────────────────┐
  Browser ── HTTPS ──►  Caddy :443 ──► backend :8000 ──┬──► postgres   (writes/reads)   │
  (Vercel SPA)                         (Django ASGI)    ├──► redis      (cache/broker)   │
                                        │  worker (Celery + beat)                        │
                                        └──► ml-service :9000  (Qwen2.5-0.5B + corpus)   │
                         └──────────────────────────────────────────────────────────────┘
```

The ml-service is **internal only** — never exposed to the internet, gated by
`ML_API_KEY` on the compose network.

---

## 1. Create the server

On Contabo: **Cloud VPS 10** · Region **Asia (Singapore)** · **Ubuntu 24.04** ·
add your SSH key. You'll get an IP, e.g. `203.0.113.10`.

## 2. Point your domain at it

Add a DNS **A record**: `api.yourdomain.com → 203.0.113.10`.
(Cloudflare DNS works great — if you proxy through Cloudflare, set SSL mode to
**Full (strict)** so Caddy's Let's Encrypt cert is honoured.)

Wait until `dig +short api.yourdomain.com` returns your IP before step 5
(Caddy needs DNS resolving to issue the certificate).

## 3. Install Docker

```bash
ssh root@203.0.113.10
curl -fsSL https://get.docker.com | sh
```

## 4. Clone and configure

```bash
git clone https://github.com/Arnobrizwan/mentormind && cd mentormind/deploy
cp .env.example .env
nano .env          # set API_DOMAIN, secrets, CORS origins, HF token
```

Generate the secrets quickly:

```bash
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(64))"
python3 -c "import secrets; print('DB_PASSWORD=' + secrets.token_urlsafe(24))"
python3 -c "import secrets; print('ML_API_KEY=' + secrets.token_urlsafe(24))"
```

## 5. Launch

```bash
docker compose up -d --build
```

First boot takes a few minutes: it builds the images, then the ml-service
downloads the base model (~1 GB) and your corpus (255 MB). Watch progress:

```bash
docker compose logs -f ml-service
```

## 6. Seed demo data + create an admin (one time)

The Postgres volume is persistent, so seed only once (unlike the ephemeral
Render demo that re-seeds on every restart):

```bash
docker compose exec backend python manage.py seed_demo
docker compose exec backend python manage.py createsuperuser
```

## 7. Verify

```bash
curl https://api.yourdomain.com/api/v1/health/
# {"instance":"contabo-sg","database":"ok","cache":"ok"}
```

Live tutor end-to-end (real mark-scheme retrieval):

```bash
curl -s https://api.yourdomain.com/api/v1/health/ && echo OK
docker compose exec ml-service \
  curl -s -X POST localhost:9000/v1/tutor/answer \
  -H "X-API-Key: $ML_API_KEY" -H 'Content-Type: application/json' \
  -d '{"question":"Explain osmosis"}'
```

## 8. Point the frontend at this API

Your Angular apps call **same-origin `/api/...`**. To make the Vercel-hosted
SPA reach this backend, add a rewrite in each app's `vercel.*.json` so Vercel
proxies the API server-side (this also avoids CORS entirely):

```jsonc
{
  "rewrites": [
    { "source": "/api/(.*)", "destination": "https://api.yourdomain.com/api/$1" },
    { "source": "/(.*)",     "destination": "/index.html" }
  ]
}
```

For the **Android (Capacitor) build**, set the origin before Angular boots —
in `index.html`: `<script>window.MM_API_BASE_URL='https://api.yourdomain.com'</script>`.

---

## Operating it

| Task | Command |
|---|---|
| Update to latest code | `git pull && docker compose up -d --build` |
| Tail logs | `docker compose logs -f backend ml-service` |
| Restart one service | `docker compose restart backend` |
| Apply new migrations | `docker compose run --rm migrate` |
| Backup the database | `docker compose exec postgres pg_dump -U mentormind mentormind > backup.sql` |
| Restore | `cat backup.sql \| docker compose exec -T postgres psql -U mentormind mentormind` |
| Stop everything | `docker compose down` (add `-v` to wipe data volumes) |

### Memory budget (8 GB box)

| Service | Approx RAM |
|---|---|
| ml-service (LLM + corpus) | ~3 GB |
| backend (2 ASGI workers) | ~0.9 GB |
| worker (Celery + beat) | ~0.4 GB |
| postgres | ~0.3 GB |
| redis | ~0.1 GB |
| caddy | ~0.03 GB |
| **Total** | **~4.8 GB** — comfortable headroom |

If the box is tight, lower `WEB_CONCURRENCY` to `1` in `.env`. Keep
`UVICORN_WORKERS=1` for the ml-service — raising it multiplies the model in RAM.

### Notes

- **No paid AI APIs.** The tutor is a local Qwen2.5-0.5B + retrieval over your
  corpus; OCR uses Tesseract (baked into the ml-service image). Everything runs
  on this one box.
- **Persistence:** all state is in named volumes (`pg_data`, `ml_corpus`,
  `hf_cache`, `media_data`). `docker compose down` keeps them; `down -v` deletes.
- **Free-tier comparison:** unlike Render free (which sleeps and cold-starts in
  ~90 s), this box is always warm.
