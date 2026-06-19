# Financial Notification Platform

Enterprise-grade, event-driven financial notification system with multi-channel delivery, compliance enforcement, and real-time analytics.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI (API Layer)                       │
│  /auth  /users  /notifications  /preferences  /templates        │
│  /analytics  /device-tokens  /admin  /webhooks                  │
└────────────────────┬────────────────────────────────────────────┘
                     │ Kafka Events
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Kafka (Message Broker)                       │
│  notification.events → notification.status → notification.dlq   │
│  notification.retry  → notification.analytics                   │
└────────────────────┬────────────────────────────────────────────┘
                     │ Consumed by
                     ▼
┌──────────────────────────────────────────────────────────────────┐
│               Kafka Consumer + Celery Workers                    │
│  NotificationFactory → ComplianceService → FrequencyCapService  │
│  → NotificationDispatcher → Channel Routers                     │
└────┬──────────┬──────────┬──────────┬──────────┬───────────────-┘
     │          │          │          │          │
     ▼          ▼          ▼          ▼          ▼
   SMS       Email     WhatsApp    Push       In-App
 (Twilio) (SendGrid)  (Twilio)  (Firebase)    (DB)
```

## Features

- **25+ Financial Event Types** — transactions, payments, loans, investments, security, KYC, offers
- **5 Notification Channels** — SMS (Twilio), Email (SendGrid), WhatsApp (Twilio), Push (Firebase), In-App
- **TRAI DND Compliance** — automatic DND registry check with 24h cache
- **Quiet Hours** — configurable per user, bypassed for critical events
- **Frequency Capping** — hourly / daily / weekly limits per user per channel
- **Retry Engine** — exponential backoff with configurable max retries and Dead Letter Queue
- **Delivery Tracking** — real-time delivery receipts via provider webhooks
- **Analytics Dashboard** — delivery rates, skip analysis, channel performance, daily trends
- **Localization** — English and Hindi templates
- **Personalization** — engagement-based channel selection and context enrichment
- **JWT Authentication** — access + refresh tokens
- **RBAC** — superadmin / admin / manager / analyst / user roles
- **Idempotency** — SHA-256 keyed deduplication
- **Structured Logging** — JSON structured logs via structlog
- **Rate Limiting** — per-IP per-minute and per-hour limits via Redis

---

## Quick Start

### Prerequisites
- Docker 24+
- Docker Compose 2.x

### 1. Clone and configure

```bash
git clone <repo-url>
cd financial-notification-platform
cp .env.example .env
# Edit .env with your credentials (Twilio, SendGrid, Firebase, etc.)
```

### 2. Start all services

```bash
docker compose up -d
```

Services started:
| Service | URL |
|---|---|
| API | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| Flower (Celery monitor) | http://localhost:5555 |
| Kafka UI | http://localhost:8080 |
| Nginx | http://localhost:80 |

### 3. Run database migrations

```bash
docker compose exec api alembic upgrade head
```

### 4. Verify health

```bash
curl http://localhost:8000/health
curl http://localhost:8000/readiness
```

---

## API Overview

### Authentication
```
POST   /api/v1/auth/register          Register a new user
POST   /api/v1/auth/login             Login and get tokens
POST   /api/v1/auth/refresh           Refresh access token
POST   /api/v1/auth/change-password   Change password
GET    /api/v1/auth/me                Get current user
```

### Notifications
```
POST   /api/v1/notifications/events          Trigger a financial event
POST   /api/v1/notifications/events/bulk     Bulk event trigger
GET    /api/v1/notifications/                List user notifications
GET    /api/v1/notifications/unread-count    Get unread in-app count
GET    /api/v1/notifications/{id}            Get notification detail
POST   /api/v1/notifications/mark-read       Mark in-app as read
POST   /api/v1/notifications/{id}/retry      Retry failed notification
DELETE /api/v1/notifications/{id}            Cancel pending notification
```

### Preferences
```
GET    /api/v1/preferences/{user_id}   Get user notification preferences
PUT    /api/v1/preferences/{user_id}   Update preferences
POST   /api/v1/preferences/{user_id}/reset   Reset to defaults
```

### Templates
```
GET    /api/v1/templates/              List templates
POST   /api/v1/templates/              Create template
GET    /api/v1/templates/{id}          Get template
PUT    /api/v1/templates/{id}          Update template
DELETE /api/v1/templates/{id}          Delete template
POST   /api/v1/templates/render        Render template preview
```

### Analytics
```
GET    /api/v1/analytics/dashboard          Overview dashboard
GET    /api/v1/analytics/summary            Daily summary records
GET    /api/v1/analytics/channel-performance   By channel
GET    /api/v1/analytics/event-performance     By event type
GET    /api/v1/analytics/skip-analysis         Skip reason breakdown
POST   /api/v1/analytics/aggregate             Trigger aggregation
```

### Webhooks
```
POST   /api/v1/webhooks/twilio/sms          Twilio SMS delivery receipts
POST   /api/v1/webhooks/sendgrid/email      SendGrid email events
GET    /api/v1/webhooks/delivery-timeline/{id}  Delivery timeline
```

---

## Triggering a Notification Event

```bash
curl -X POST http://localhost:8000/api/v1/notifications/events \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "event_type": "transaction.success",
    "priority": "high",
    "event_data": {
      "amount": "10000",
      "recipient": "Rahul Sharma",
      "reference_id": "TXN202401010001"
    }
  }'
```

---

## Financial Event Types

| Category | Events |
|---|---|
| Transaction | `transaction.success`, `transaction.failure`, `transaction.pending`, `transaction.reversed`, `transaction.disputed` |
| Payment | `payment.due`, `payment.overdue`, `payment.received`, `payment.failed`, `payment.initiated` |
| Account | `account.created`, `account.debit`, `account.credit`, `account.blocked`, `account.unblocked`, `account.closed`, `account.low_balance`, `account.statement_ready` |
| Loan | `loan.approved`, `loan.rejected`, `loan.disbursed`, `loan.emi_due`, `loan.emi_paid`, `loan.emi_missed`, `loan.foreclosed` |
| Investment | `investment.matured`, `investment.dividend`, `investment.purchase`, `investment.redemption` |
| Security | `security.login_detected`, `security.password_changed`, `security.otp_generated`, `security.suspicious_activity` |
| KYC | `kyc.approved`, `kyc.rejected`, `kyc.pending` |
| Offer | `offer.available`, `offer.expiring` |
| System | `system.maintenance`, `onboarding.welcome` |

---

## Compliance Rules

| Rule | Behaviour |
|---|---|
| **TRAI DND** | Blocks SMS/WhatsApp for DND-registered numbers. Exempt: `otp_generated`, `suspicious_activity`, `account_blocked` |
| **Quiet Hours** | Blocks all channels during 22:00–08:00 IST. Exempt: all `CRITICAL_EVENTS` |
| **Frequency Cap** | Hourly (10), Daily (50), Weekly (200) per user per channel. Configurable per user. |
| **User Opt-Out** | Per-event-type and per-channel opt-outs respected |

---

## Running Tests

```bash
# Unit tests only (no external deps)
pytest tests/unit/ -v

# All tests (requires test database)
pytest --cov=app

# With HTML coverage report
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

---

## Environment Variables

See `.env.example` for all required configuration. Key variables:

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL async connection string |
| `REDIS_URL` | Redis connection string |
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka broker address |
| `TWILIO_ACCOUNT_SID` | Twilio account for SMS/WhatsApp |
| `SENDGRID_API_KEY` | SendGrid API key for email |
| `FIREBASE_CREDENTIALS_PATH` | Path to Firebase service account JSON |
| `JWT_SECRET_KEY` | Secret for JWT signing (min 32 chars) |
| `TRAI_DND_CHECK_ENABLED` | Enable/disable TRAI DND verification |

---

## Project Structure

```
financial-notification-platform/
├── app/
│   ├── api/v1/endpoints/   # Route handlers
│   ├── celery/             # Celery tasks and beat schedule
│   ├── channels/           # Channel implementations (SMS, Email, etc.)
│   ├── core/               # Config, constants, exceptions, security, logging
│   ├── db/                 # SQLAlchemy engine and session
│   ├── kafka/              # Kafka producer, consumer, handlers
│   ├── localization/       # EN/HI translations
│   ├── middleware/         # Auth, rate-limit, logging middleware
│   ├── models/             # SQLAlchemy ORM models
│   ├── redis/              # Redis client and frequency cap
│   ├── repositories/       # Data access layer
│   ├── schemas/            # Pydantic request/response schemas
│   ├── services/           # Business logic services
│   └── main.py             # FastAPI app entrypoint
├── alembic/                # Database migrations
├── tests/
│   ├── unit/               # Unit tests (mocked dependencies)
│   └── integration/        # Integration tests (real database)
├── docker/nginx/           # Nginx configuration
├── scripts/                # DB init scripts
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

---

## License

MIT
#   F i n a n c i a l - N o t i f i c a t i o n - P l a t f o r m 
 
 
