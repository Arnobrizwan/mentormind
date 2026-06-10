# MentorMind Architecture Notes

## Read/write splitting

`config/db_router.py` routes all reads to the `replica` alias and all writes to
`default`. The router only activates when `REPLICA_URL` is set, so bare-metal
dev (sqlite) and single-DB cloud deploys work unchanged. Replication itself is
handled by Postgres streaming replication (bitnami images in Compose; Neon
read replicas in the cloud).

Caveat demonstrated intentionally: replica lag means read-your-own-writes can
be stale — modules that need strong consistency read with
`Model.objects.using("default")`.

## Cache strategy

- Pattern: cache-aside with eager invalidation (post_save/post_delete signals)
- `settings_engine` and `flags` cache whole dictionaries (read-heavy, tiny)
- TTL 300s is a safety net only; invalidation is the real mechanism
- Later phases add: per-course cache keys, leaderboard via Redis sorted sets,
  HTTP caching at nginx

## Instance visibility

Every response carries `X-Served-By: <INSTANCE_NAME>` (Django middleware) and
`X-Upstream` (nginx). Hitting the LB repeatedly shows round-robin in devtools —
load balancing made visible.

## Why Celery tasks fall back to eager mode

Without `REDIS_URL`, `CELERY_TASK_ALWAYS_EAGER=True` so the app works on a
laptop with zero services. In Compose/K8s, Redis is the broker and a dedicated
worker container consumes tasks.

## Runtime configuration (dynamic knobs)

Three layers, by change cadence:

- **Feature flags** (`flags` app, `/api/v1/flags/`): live kill switches — `ai_tutor`, `proctoring`, `omr_grading`, `ocr`, `dropout_risk`. The ML service polls them (`FLAGS_URL`, fail-open).
- **Site settings** (`settings_engine` app, `/api/v1/settings/public/`): live business tuning via admin console, no redeploy. Known keys: `site-name`, `tagline`, `tutor-daily-limit`, `premium-{monthly,yearly}-days`, `points-<action>`, `quiz-pass-threshold`, `avatar-max-mb`, `search-min-query-chars`, `search-result-limit`. All have hardcoded fallbacks, so the apps run with an empty table.
- **Environment variables** (restart to apply): secrets and operational tuning. Backend: `COURSE_CACHE_TTL`, `LEADERBOARD_CACHE_TTL`, `API_PAGE_SIZE`, `JWT_*`. ML service: `DROPOUT_HIGH_THRESHOLD`, `DROPOUT_MEDIUM_THRESHOLD`, `OMR_FILL_THRESHOLD`, `PROCTOR_SCALE_FACTOR`, `PROCTOR_MIN_NEIGHBORS`, `PROCTOR_MIN_FACE_PX`, `TUTOR_STRONG_MATCH`, `TUTOR_WEAK_MATCH`, `TUTOR_MAX_CANDIDATES`, `CUSTOM_LLM_TIMEOUT`, `LOCAL_LLM_TEMPERATURE`, `LOCAL_LLM_TOP_P`, `LOCAL_LLM_MAX_TOKENS`, `MAX_IMAGE_BYTES`.

## Free-tier deployment mapping (cloud mode)

| Component | Local (Compose) | Cloud (free) |
|---|---|---|
| Load balancer | nginx | Render/Koyeb edge + Cloudflare |
| API ×2 | api-1, api-2 | Render + Koyeb free instances |
| Postgres + replica | bitnami streaming repl. | Neon (free) + read replica |
| Redis | redis container | Upstash free |
| Files | local volume | Cloudflare R2 (10 GB free) |
| Metrics | Prometheus + Grafana | Grafana Cloud free |
| Errors | — | Sentry free |
| Uptime | — | UptimeRobot free |
