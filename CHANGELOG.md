# Changelog

All notable changes to this project, organized by development day per the ZeTheta 15-day methodology.

---

## Document Error Log

Per spec Section A13, the training document contains 5 deliberate errors. Identified below:

### Error 1 — Retry Backoff Formula Self-Contradiction (Section A9.1)

The spec defines for CRITICAL priority: max retries = 10, base delay = 500ms, max delay = 60 seconds, using the formula:

```
retryDelay = min(baseDelay * 2^attempt + jitter, maxDelay)
```

At attempt 7: `500ms × 2^7 = 64,000ms` already exceeds the stated 60-second max delay, meaning the `min()` clamp activates from attempt 7 onward — fine in isolation, but the spec's own example table only shows attempts 1–5, implying retries 6–10 would all fire at exactly the 60-second ceiling with no further backoff growth. This defeats the purpose of "exponential" backoff for nearly half the configured retry budget and was not caught in the spec's worked example.

**Resolution in our implementation:** We use a fixed retry delay schedule (`RETRY_DELAY_SCHEDULE = [60, 300, 900, 3600, 7200]`) indexed by `min(retry_count, len(schedule)-1)`, which avoids the exponential blow-up entirely while still providing graduated backoff.

### Error 2 — RISK Events List "Call" as a Channel Without Defining It as a Supported Channel

Section A2.3 lists `Call` as a channel for RISK-001 and RISK-002, but Section A3.1's channel matrix and the entire rest of the document (Section E1 tech stack, Appendix A API examples) only define 5 channels: SMS, Email, Push, WhatsApp, In-App. IVR/Call appears in the A3.1 table but no provider, no API contract, and no delivery worker is ever specified for it.

**Resolution:** We modeled `CALL` as a recognized `NotificationChannel` enum value in the taxonomy for fidelity to the spec, but it falls back to escalation logging rather than actual dispatch, since no IVR provider integration was specified anywhere in the 74-page document.

### Error 3 — TXNX-004 (Dividend Credited) Misclassified as MEDIUM Priority

Dividend credit notifications involve a financial credit to the user's bank account and are informational per the spec's own `Regulatory` column, yet other informational/MEDIUM events (e.g., RISK-005 Concentration Alert) carry similar urgency. However, TXNX-005 (Funds Deposited) — which is materially the same kind of event (money arriving) — is classified HIGH with Banking Reg status, while TXNX-004 sits at MEDIUM with only "Informational" regulatory status, despite SEBI requiring dividend disclosure timeliness. The inconsistency suggests TXNX-004 should have been HIGH to align with TXNX-005's treatment of incoming funds.

**Resolution:** We preserved the spec's literal MEDIUM classification in `app/core/event_taxonomy.py` for spec fidelity, documenting this inconsistency here rather than silently "fixing" it.

### Error 4 — PostgreSQL Partitioning Schema Is Invalid as Written

Section A8.1 defines:

```sql
CREATE TABLE notifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ...
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  ...
) PARTITION BY RANGE (created_at);
```

This is **not valid PostgreSQL DDL**. When a table uses `PARTITION BY RANGE`, PostgreSQL requires the partition key column(s) to be included in any `PRIMARY KEY` or `UNIQUE` constraint. A bare `id UUID PRIMARY KEY` with partitioning on a *different* column (`created_at`) raises:

```
ERROR: insufficient columns in PRIMARY KEY constraint definition
DETAIL: PRIMARY KEY constraint on table "notifications" lacks column "created_at" which is part of the partition key.
```

The corrected DDL would need a composite primary key: `PRIMARY KEY (id, created_at)`.

**Resolution:** Our migration (`alembic/versions/001_initial_schema.py`) uses a flat (non-partitioned) table for the reference implementation, since the spec's partitioning DDL would fail to execute as written. We documented the corrected composite-key approach here rather than reproducing the broken DDL.

### Error 5 — Frequency Cap "Per-Category Hourly" Conflicts With CRITICAL Bypass Logic for SIPX Events

Section A6.2 states per-category hourly cap is "Max 3 per category/hour" with override "Margin calls always sent." But SIPX-001 (SIP Due Reminder, priority MEDIUM per our taxonomy reading) fires on a strict T-3-days schedule — if a user has 3+ SIPs maturing within the same hour window (common for HNI users with multiple SIPs configured on the 1st of the month), the 4th SIP reminder would be silently capped even though it's a time-critical transactional reminder, not a discretionary promotional message. The spec never reconciles "transactional but capped" vs. "promotional and capped" — only CRITICAL/regulatory events are exempted, leaving legitimate transactional-but-non-critical reminders vulnerable to silent suppression with no escalation path.

**Resolution:** Our `SpecFrequencyCapService` (`app/redis/frequency_cap_v2.py`) implements the cap exactly as specified, including this edge case. We did not add an undocumented bypass, since the spec doesn't authorize one — but we flag it here as a real production risk: SIP reminder reliability could degrade for power users during month-start clustering.

---

## Day 1 — Project Setup & Architecture Design
- Initialized FastAPI project structure (src→app/ layout adapted for Python idioms)
- Configured Docker Compose with PostgreSQL 16, Redis 7, Kafka (Confluent), RabbitMQ 3.12
- Created `.env.example` with all required environment variables
- Wrote `ARCHITECTURE.md` with C4 diagrams (context, container, component levels)
- Documented technology choices with rationale in Architecture Decision Records
- Defined event taxonomy in `app/core/event_taxonomy.py` covering all 25 spec-coded events (TXNX/RISK/SIPX/MKTX/REGX)
- **AI usage note:** Used Claude to scaffold the initial Docker Compose health-check configuration; reviewed and adjusted timeout/retry values manually based on container startup characteristics observed locally.

## Day 2 — Database Schema & Event Models
- Implemented SQLAlchemy 2.0 async models for all core tables
- Created Alembic migration `001_initial_schema.py` with all enums, tables, and base indexes
- Added `notification_state_log`, `dead_letter_queue`, and `consent_records` tables in migration `002`
- Defined Pydantic schemas with strict validation for all 25+ event types
- Wrote event factory pattern in `app/core/event_taxonomy.py` for test event generation
- **AI usage note:** AI-generated boilerplate for the 25 EventDefinition dataclass entries was reviewed line-by-line against the spec's tables in Section A2 to verify exact channel lists, priorities, and regulatory classifications.

## Day 3 — Event Ingestion Pipeline
- Configured Kafka topics: `notification.events`, `notification.status`, `notification.dlq`, `notification.retry`, `notification.analytics`
- Implemented idempotent Kafka producer (`enable_idempotence=True`, `acks=all`)
- Built consumer with manual offset commit for at-least-once delivery semantics
- Implemented event enrichment in `NotificationFactory`: resolves user context, preferences, channel eligibility
- Built routing engine respecting regulatory mandate override (Section A3.2 Priority 1)

## Day 4 — Template Engine & Personalisation
- Implemented Jinja2-based template engine with `StrictUndefined` (fails loudly on missing variables rather than silently rendering blanks)
- Built template registry backed by PostgreSQL with locale fallback chain (requested locale → English)
- Added localisation for **5 languages**: English, Hindi, Marathi, Tamil, Telugu (`app/localization/translations.py` + `translations_extended.py`)
- Created seed templates for representative event types across SMS/Email/Push/In-App

## Day 5 — User Preference System
- Implemented preference hierarchy resolver: system defaults → user explicit preferences → regulatory override (4-layer model from Section A5.1)
- Built Redis-cached preference lookups with invalidation on update
- Added `UserPreferenceUpdate` schema supporting per-event-type opt-outs

## Day 6 — DND Compliance & Frequency Capping
- Implemented `ComplianceService` with TRAI DND registry lookup + 24h Redis cache
- Built `SpecFrequencyCapService` implementing the exact spec limits: global daily=12, SMS=5/Push=8/Email=3 daily, category hourly=3, 15-min same-type cooldown
- Added quiet hours enforcement with per-user IANA timezone resolution
- Implemented CRITICAL event bypass with audit trail via `NotificationStateLog`

## Day 7 — Multi-Channel Delivery Providers
- Implemented `BaseChannel` interface matching spec's `DeliveryProvider` contract (Section A3.3)
- Built SMS (Twilio), Email (SendGrid), WhatsApp (Twilio), Push (Firebase FCM), In-App channels
- Added provider health check methods on every channel implementation

## Day 8 — Delivery Routing & Failover Engine
- Implemented `CircuitBreaker` dataclass with CLOSED/OPEN/HALF_OPEN states (`app/rabbitmq/circuit_breaker.py`)
- Configured per-provider failure thresholds (5 failures / 60s window → OPEN)
- Built RabbitMQ topology with 4 priority queues (CRITICAL/HIGH/MEDIUM/LOW) bound to a direct exchange, each with dead-letter routing

## Day 9 — Retry Strategy & Dead Letter Queue
- Implemented retry scheduling via Celery `apply_async(countdown=delay)` 
- Configured priority-aware retry delay schedule
- Built `dead_letter_queue` table + `/api/v1/dlq` management endpoints (list, stats, retry, discard, bulk-retry)
- Added DLQ depth alerting threshold (>100 unresolved → alert flag in `/dlq/stats`)

## Day 10 — Analytics Pipeline
- Implemented `AnalyticsService` with daily aggregation upserts into `notification_analytics`
- Built dashboard, channel-performance, event-performance, skip-analysis API endpoints
- Added Prometheus-compatible `/metrics` endpoint exposing DLQ depth, delivery counters, circuit breaker states

## Day 11 — Load Testing & Performance Optimisation
- Documented expected throughput requirements per spec Challenge 5 (292/sec sustained for 4.2M notifications in 4 hours)
- Added composite index `(user_id, status, channel)`, partial index on pending-work statuses, and `(event_type, created_at)` analytics index in migration 002

## Day 12 — Error Handling, Logging & Monitoring
- Implemented structlog-based JSON structured logging with request correlation IDs (`RequestLoggingMiddleware`)
- Added `/health` (liveness) and `/readiness` (checks DB, Redis, RabbitMQ) endpoints
- Implemented graceful exception handlers for all custom exception types

## Day 13 — API Documentation & Comprehensive Testing
- FastAPI auto-generates OpenAPI 3.0 spec at `/openapi.json`, Swagger UI at `/docs`
- Wrote unit tests covering security, compliance service, frequency capping, notification factory, template rendering, translations, channels
- Wrote integration tests covering auth, notifications, preferences, templates, users, analytics endpoints

## Day 14 — Containerisation, CI/CD & Security
- Multi-stage Dockerfile (dependencies → development/production stages)
- Created `.github/workflows/ci.yml`: lint (black/isort/flake8) → unit tests → integration tests (with live Postgres/Redis/RabbitMQ services) → coverage → Docker build → security scan (pip-audit + bandit)
- Implemented sliding-window rate limiting middleware via Redis

## Day 15 — Final Documentation & Repository Transfer
- Completed `README.md`, `ARCHITECTURE.md`, `CHANGELOG.md` (this file), `DEPLOYMENT.md`
- Added mandatory `.zetheta-project.json` per Section E3
- Documented all 5 deliberate spec errors above for bonus scoring (Section A13)

---

## AI-Accelerated Development Disclosure (Section E4)

This project was built with substantial AI assistance (Claude). Per the spec's guidelines:

- **Boilerplate generation:** Docker Compose service definitions, Alembic migration scaffolding, GitHub Actions workflow steps, and repetitive Pydantic schema patterns were AI-generated and then reviewed for correctness against the spec's exact field names and types.
- **Concept explanation, manual implementation:** Circuit breaker state machine, exponential backoff math, and Kafka consumer group rebalancing behavior were discussed with AI for understanding, but the actual state transition logic in `circuit_breaker.py` was written and verified against the CLOSED→OPEN→HALF_OPEN→CLOSED transition rules manually.
- **Code review:** Compliance-sensitive code (DND checking order, frequency cap math, retry budget calculations) was specifically reviewed for edge cases and off-by-one errors.
- Every file in this repository can be explained line-by-line; no unreviewed AI output was committed.
