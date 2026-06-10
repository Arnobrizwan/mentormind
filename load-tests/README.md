# Load tests (k6)

Install k6 (`brew install k6`), bring the stack up, seed a course, then:

```bash
cd infra && docker compose up -d --build

# Read path — caching showcase. Watch X-Cache-Status flip to HIT and
# Grafana (localhost:3000) stay flat while VUs climb.
k6 run load-tests/catalog-read.js

# Write path — full student journey (register → enroll → quiz → leaderboard).
k6 run -e COURSE_SLUG=systems-design-101 load-tests/student-journey.js
```

Both scripts accept `-e BASE_URL=https://your-deploy` to aim at a cloud
environment. Thresholds fail the run (non-zero exit) when latency or error
budgets are blown, so they slot straight into CI.

What to look at while they run:

| Where | What it shows |
|---|---|
| `X-Served-By` header / `served_by_instances` metric | round-robin across api-1/api-2 |
| `X-Cache-Status` on `/api/v1/courses/` | nginx micro-cache HIT ratio |
| Grafana → Django dashboard | request rate vs DB query rate divergence (cache wins) |
| `/system` page | component latencies under load |
