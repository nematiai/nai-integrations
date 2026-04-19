# NEMI — Production Deploy + Rollback Runbook

First-time prod deploy procedure for `buildmyapp.us`. Execute top-to-bottom. Any trigger in section 3 aborts → run section 4.

## 1. Pre-deploy checklist

All must be green before touching prod.

- [ ] Git tag exists on `production` branch (`vX.Y.Z`) — `git tag -l | tail -5`
- [ ] Full test suite: 262+ passed locally — `pytest -q`
- [ ] Image built + pushed — `docker push ghcr.io/nematiai/nai-integrations:${GIT_SHA}`
- [ ] pg_dump taken in last 1 hour, uploaded to R2 (see section 5)
- [ ] `.env.prod` synced to prod host at repo root
- [ ] Staging env validated — **TBD** (no staging yet)

## 2. Deploy procedure (happy path)

```bash
# On prod host, at repo root
export GIT_SHA=$(git rev-parse --short HEAD)
git fetch --tags && git checkout vX.Y.Z

docker network create nai_public 2>/dev/null || true

docker compose -f docker/production/docker-compose.yml pull
docker compose -f docker/production/docker-compose.yml up -d --no-deps nemi-db nemi-redis
docker compose -f docker/production/docker-compose.yml run --rm nemi-api python manage.py migrate --noinput
docker compose -f docker/production/docker-compose.yml up -d
```

Verify:

```bash
docker compose -f docker/production/docker-compose.yml ps
curl -fsS http://localhost:8000/api/v1/health/ || echo "HEALTH FAIL"
# Smoke-test notify (requires API key + existing channel):
curl -fsS -X POST https://buildmyapp.us/api/v1/notify/send/ \
  -H "X-API-Key: $NEMI_SMOKE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"channel_id": 1, "title": "smoke", "body": "deploy ok"}'
docker compose -f docker/production/docker-compose.yml logs -f --tail=200 nemi-api   # tail 5 min
```

## 3. Rollback triggers (any one = abort, go to section 4)

- `/api/v1/health/` returns non-200 for > 60 seconds
- 500 error rate spikes > 5% in first 10 minutes after cutover
- Any unhandled traceback in `nemi-api` logs
- Integration tests against staging fail — **TBD** (no staging yet)
- Migration reports inconsistent schema after `migrate`

## 4. Rollback procedure

```bash
# On prod host
export PREV_SHA=<previous-known-good-sha>
export PREV_TAG=<previous-tag>

docker compose -f docker/production/docker-compose.yml down

git checkout $PREV_TAG
export GIT_SHA=$PREV_SHA
docker compose -f docker/production/docker-compose.yml pull
docker compose -f docker/production/docker-compose.yml up -d
```

Restore DB only if migrations ran against prod DB:

```bash
export R2_BUCKET=<R2-bucket>
export R2_ENDPOINT=<R2-endpoint>    # TBD — Ali fills in
aws s3 cp s3://$R2_BUCKET/backups/nemi-YYYY-MM-DD.sql.gz . --endpoint-url $R2_ENDPOINT
gunzip -c nemi-*.sql.gz | \
  docker compose -f docker/production/docker-compose.yml exec -T nemi-db \
    psql -U $POSTGRES_USER $POSTGRES_DB
```

Re-verify:

```bash
curl -fsS http://localhost:8000/api/v1/health/
docker compose -f docker/production/docker-compose.yml logs --tail=100 nemi-api
```

## 5. Backup procedure (R2)

Daily cron on prod host (03:00 UTC):

```bash
0 3 * * * cd /opt/nemi && \
  docker compose -f docker/production/docker-compose.yml exec -T nemi-db \
    pg_dump -U $POSTGRES_USER $POSTGRES_DB | gzip | \
  aws s3 cp - s3://<R2-bucket>/backups/nemi-$(date +\%F).sql.gz \
    --endpoint-url <R2-endpoint>
```

- Retention: 30 days (lifecycle rule on R2 bucket)
- Manual verify: `aws s3 ls s3://<R2-bucket>/backups/ --endpoint-url <R2-endpoint> | tail -5` monthly

## 6. Contacts + logs

- **On-call / escalation:** TBD
- **Logs:** `docker compose -f docker/production/docker-compose.yml logs nemi-api --tail=200`
- **Monitoring dashboard:** TBD
