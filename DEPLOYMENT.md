# Deployment Guide

Production deployment checklist and operational guidance for the Financial Notification Platform.

---

## Pre-Deployment Checklist

### Infrastructure
- [ ] PostgreSQL 16+ provisioned with SSL enabled for client connections
- [ ] PostgreSQL configured with connection pooling (PgBouncer recommended for >50 concurrent connections)
- [ ] Redis 7+ provisioned with `requirepass` set and dangerous commands disabled (`FLUSHALL`, `FLUSHDB`, `KEYS`)
- [ ] Kafka cluster provisioned with minimum 3 brokers for production redundancy
- [ ] RabbitMQ cluster provisioned with mirrored queues across nodes
- [ ] All services configured with resource limits (CPU/memory) to prevent noisy-neighbor exhaustion

### Secrets & Configuration
- [ ] All secrets moved to a secrets manager (AWS Secrets Manager, HashiCorp Vault, or equivalent) — never `.env` files in production
- [ ] `JWT_SECRET_KEY` is a unique, randomly generated value of at least 32 characters, different from any non-production environment
- [ ] `APP_SECRET_KEY` rotated and distinct from staging/development
- [ ] Twilio, SendGrid, Firebase credentials are production (not sandbox/test mode) credentials
- [ ] `.env` file is in `.gitignore` and has never been committed to version control (verify with `git log --all --full-history -- .env`)

### Database
- [ ] All Alembic migrations applied: `alembic upgrade head`
- [ ] Database backups configured (point-in-time recovery enabled)
- [ ] Read replica provisioned for analytics queries to avoid impacting write-path latency
- [ ] Connection pool size tuned based on expected concurrent load (`pool_size`, `max_overflow` in `app/db/base.py`)

### Security
- [ ] Rate limiting verified active on all public endpoints
- [ ] CORS configured to only allow known frontend origins (not `*`)
- [ ] All containers run as non-root user
- [ ] Dependency vulnerability scan run (`pip-audit`) with zero critical/high findings
- [ ] `bandit` security scan run with zero medium+ findings
- [ ] Webhook endpoints (Twilio/SendGrid callbacks) verify provider signatures before processing

### Observability
- [ ] `/metrics` endpoint scraped by Prometheus
- [ ] Structured JSON logs shipped to a log aggregation platform (e.g., ELK, Datadog, CloudWatch)
- [ ] Alerting configured for the rules in spec Section A11.2:
  - `HighDLQDepth`: DLQ depth > 100 for > 5 minutes → page on-call
  - `ProviderCircuitOpen`: any circuit breaker OPEN → notify ops channel
  - `DeliveryLatencySpike`: P99 latency > 30s for CRITICAL events → page on-call
  - `HighFailureRate`: failure rate > 5% in 10-min window → notify ops
  - `DNDViolationDetected`: any DND violation → page on-call + notify compliance

### Compliance
- [ ] TRAI DND scrubbing database refresh job scheduled (daily minimum, ideally real-time)
- [ ] Consent records table populated with historical opt-in data before go-live
- [ ] Audit trail (`notification_state_log`) retention policy confirmed (recommend indefinite retention for regulatory audit purposes, separate from `notifications.personalisation_data` 90-day scrub policy)

---

## Deployment Steps

1. **Build and push image**
   ```bash
   docker build -t your-registry/fnp:latest --target production .
   docker push your-registry/fnp:latest
   ```

2. **Run database migrations**
   ```bash
   alembic upgrade head
   ```

3. **Deploy infrastructure services first** (PostgreSQL, Redis, Kafka, RabbitMQ) and verify health checks pass before deploying the application tier.

4. **Deploy application services**
   - `api` (FastAPI, horizontally scalable behind a load balancer)
   - `celery-worker` (scale based on queue depth)
   - `celery-beat` (single instance only — do not scale beyond 1 replica)
   - `kafka-consumer` (one per partition for optimal parallelism)
   - `rabbitmq-consumer` (scale per priority queue load)

5. **Verify health**
   ```bash
   curl https://your-domain/health
   curl https://your-domain/readiness
   ```

6. **Smoke test event ingestion**
   ```bash
   curl -X POST https://your-domain/api/v1/events \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"event_type": "TXNX-001", "event_id": "smoke-test-001", "source_system": "deployment_check", "timestamp": "2024-01-01T00:00:00Z", "priority": 3, "user_id": "...", "payload": {}}'
   ```

---

## Scaling Guidance (2M → 20M notifications/day)

Per spec Section A12.1 Question 3, the following bottlenecks should be addressed at scale:

| Bottleneck | Mitigation |
|---|---|
| Kafka partition throughput | Increase partition count on `notification.events`; ensure consumer group size matches partition count |
| Database write contention | Move to read replicas for all analytics/reporting queries; keep writes on primary only |
| Redis single-instance limits | Migrate to Redis Cluster for distributed frequency cap counters |
| Celery worker saturation | Horizontally scale `celery-worker` containers; monitor queue depth via Flower |
| RabbitMQ queue depth | Add additional consumer instances per priority queue; CRITICAL queue should never share consumers with lower-priority queues |

---

## Rollback Procedure

1. Re-deploy the previous known-good image tag
2. If a migration was applied, run `alembic downgrade -1` only if the migration is confirmed backward-compatible
3. Verify `/readiness` returns healthy before routing traffic back
4. Check DLQ depth did not spike during the rollback window
