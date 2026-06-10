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
