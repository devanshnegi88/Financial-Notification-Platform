from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    FNPBaseException,
    NotFoundError,
    RateLimitExceeded,
    ValidationError,
)
from app.core.logging import get_logger, setup_logging
from app.db.base import close_db, init_db
from app.kafka.producer import get_producer, stop_producer
from app.middleware.logging_middleware import RequestLoggingMiddleware
from app.middleware.rate_limit import rate_limit_middleware
from app.redis.client import close_redis, get_redis

setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    logger.info("application_starting", env=settings.APP_ENV)

    # Initialize Redis
    await get_redis()
    logger.info("redis_connected")

    # Initialize Kafka producer
    await get_producer()
    logger.info("kafka_producer_ready")

    # Initialize RabbitMQ topology
    try:
        from app.rabbitmq.client import setup_topology
        await setup_topology()
        logger.info("rabbitmq_topology_ready")
    except Exception as e:
        logger.warning("rabbitmq_topology_setup_failed", error=str(e))

    # Seed initial data
    await _seed_initial_data()

    logger.info("application_ready")
    yield

    # Shutdown
    logger.info("application_shutting_down")
    await stop_producer()
    await close_redis()
    await close_db()
    try:
        from app.rabbitmq.client import close_rabbitmq
        await close_rabbitmq()
    except Exception:
        pass
    logger.info("application_stopped")


async def _seed_initial_data() -> None:
    from app.db.base import AsyncSessionLocal
    from app.repositories.user_repository import UserRepository
    from app.services.auth_service import AuthService
    from app.core.constants import UserRole
    from app.core.exceptions import ConflictError

    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)
        existing = await repo.get_by_email(settings.FIRST_SUPERUSER_EMAIL)
        if not existing:
            service = AuthService(session)
            try:
                await service.register(
                    email=settings.FIRST_SUPERUSER_EMAIL,
                    password=settings.FIRST_SUPERUSER_PASSWORD,
                    full_name="Super Admin",
                    role=UserRole.SUPERADMIN,
                )
                await session.commit()
                logger.info("superadmin_created", email=settings.FIRST_SUPERUSER_EMAIL)
            except ConflictError:
                pass
        await _seed_templates(session)


async def _seed_templates(session) -> None:
    from app.core.constants import FinancialEventType, NotificationChannel
    from app.repositories.template_repository import TemplateRepository

    repo = TemplateRepository(session)

    default_templates = [
        {
            "name": "Transaction Success SMS EN",
            "event_type": FinancialEventType.TRANSACTION_SUCCESS,
            "channel": NotificationChannel.SMS,
            "locale": "en",
            "body": "Dear {{ user_name }}, your transaction of ₹{{ amount }} to {{ recipient }} was successful. Ref: {{ reference_id }}. -YourBank",
        },
        {
            "name": "Transaction Success SMS HI",
            "event_type": FinancialEventType.TRANSACTION_SUCCESS,
            "channel": NotificationChannel.SMS,
            "locale": "hi",
            "body": "प्रिय {{ user_name }}, ₹{{ amount }} का लेनदेन {{ recipient }} को सफलतापूर्वक पूरा हुआ। संदर्भ: {{ reference_id }}। -YourBank",
        },
        {
            "name": "Transaction Failure SMS EN",
            "event_type": FinancialEventType.TRANSACTION_FAILURE,
            "channel": NotificationChannel.SMS,
            "locale": "en",
            "body": "Dear {{ user_name }}, your transaction of ₹{{ amount }} FAILED. Reason: {{ reason }}. Ref: {{ reference_id }}. Contact support if needed.",
        },
        {
            "name": "Payment Due Email EN",
            "event_type": FinancialEventType.PAYMENT_DUE,
            "channel": NotificationChannel.EMAIL,
            "locale": "en",
            "subject": "Payment Due Reminder - ₹{{ amount }}",
            "body": "Dear {{ user_name }},\n\nThis is a reminder that a payment of ₹{{ amount }} is due on {{ due_date }}.\n\nPlease ensure timely payment to avoid penalties.\n\nRegards,\nYourBank Team",
            "html_body": "<p>Dear <strong>{{ user_name }}</strong>,</p><p>A payment of <strong>₹{{ amount }}</strong> is due on <strong>{{ due_date }}</strong>.</p><p>Please ensure timely payment.</p>",
        },
        {
            "name": "Account Low Balance SMS EN",
            "event_type": FinancialEventType.ACCOUNT_LOW_BALANCE,
            "channel": NotificationChannel.SMS,
            "locale": "en",
            "body": "Alert: Your account balance is low (₹{{ balance }}). Minimum required: ₹{{ minimum_balance }}. Add funds to avoid charges. -YourBank",
        },
        {
            "name": "Loan EMI Due SMS EN",
            "event_type": FinancialEventType.LOAN_EMI_DUE,
            "channel": NotificationChannel.SMS,
            "locale": "en",
            "body": "Reminder: EMI of ₹{{ emi_amount }} for loan {{ loan_id }} is due on {{ due_date }}. Auto-debit will be processed. -YourBank",
        },
        {
            "name": "Suspicious Activity SMS EN",
            "event_type": FinancialEventType.SUSPICIOUS_ACTIVITY,
            "channel": NotificationChannel.SMS,
            "locale": "en",
            "body": "SECURITY ALERT: Suspicious activity detected on your account. If not you, call {{ helpline }} immediately. Ref: {{ incident_id }}. -YourBank",
        },
        {
            "name": "OTP SMS EN",
            "event_type": FinancialEventType.OTP_GENERATED,
            "channel": NotificationChannel.SMS,
            "locale": "en",
            "body": "{{ otp }} is your OTP for {{ purpose }}. Valid for {{ validity_minutes }} minutes. DO NOT share with anyone. -YourBank",
        },
        {
            "name": "Loan Approved Push EN",
            "event_type": FinancialEventType.LOAN_APPROVED,
            "channel": NotificationChannel.PUSH,
            "locale": "en",
            "subject": "Loan Approved! 🎉",
            "body": "Congratulations {{ user_name }}! Your loan of ₹{{ amount }} has been approved. Disbursement within {{ disbursement_days }} working days.",
        },
        {
            "name": "Welcome In-App EN",
            "event_type": FinancialEventType.WELCOME,
            "channel": NotificationChannel.IN_APP,
            "locale": "en",
            "subject": "Welcome to YourBank!",
            "body": "Welcome {{ user_name }}! Your account is ready. Start exploring our services.",
        },
    ]

    for tmpl_data in default_templates:
        existing = await repo.get_by_event_channel_locale(
            tmpl_data["event_type"], tmpl_data["channel"], tmpl_data["locale"]
        )
        if not existing:
            await repo.create(tmpl_data)

    await session.commit()


app = FastAPI(
    title="Financial Notification Platform",
    description="Enterprise-grade financial notification system with multi-channel delivery",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# ── Middleware ─────────────────────────────────────────────────────────────────
app.add_middleware(RequestLoggingMiddleware)
app.middleware("http")(rate_limit_middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


# ── Exception Handlers ─────────────────────────────────────────────────────────
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": "Validation error", "detail": exc.errors()},
    )


@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"error": exc.message},
    )


@app.exception_handler(ConflictError)
async def conflict_handler(request: Request, exc: ConflictError):
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"error": exc.message},
    )


@app.exception_handler(AuthenticationError)
async def auth_handler(request: Request, exc: AuthenticationError):
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"error": exc.message},
        headers={"WWW-Authenticate": "Bearer"},
    )


@app.exception_handler(AuthorizationError)
async def authz_handler(request: Request, exc: AuthorizationError):
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={"error": exc.message},
    )


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"error": exc.message},
    )


@app.exception_handler(FNPBaseException)
async def fnp_base_handler(request: Request, exc: FNPBaseException):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": exc.message},
    )


# ── Health & Readiness ─────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy", "service": settings.APP_NAME, "version": "1.0.0"}


@app.get("/readiness", tags=["Health"])
async def readiness():
    checks = {}
    overall = True

    try:
        from app.redis.client import get_redis
        r = await get_redis()
        await r.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"
        overall = False

    try:
        from app.db.base import AsyncSessionLocal
        from sqlalchemy import text
        async with AsyncSessionLocal() as s:
            await s.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as e:
        checks["postgres"] = f"error: {e}"
        overall = False

    try:
        from app.rabbitmq.client import get_rabbitmq_connection
        conn = await get_rabbitmq_connection()
        checks["rabbitmq"] = "ok" if not conn.is_closed else "error: closed"
    except Exception as e:
        checks["rabbitmq"] = f"error: {e}"
        overall = False

    return JSONResponse(
        status_code=status.HTTP_200_OK if overall else status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"status": "ready" if overall else "not_ready", "checks": checks},
    )


@app.get("/metrics", tags=["Monitoring"])
async def prometheus_metrics():
    """
    Prometheus-compatible metrics endpoint.
    Exposes notification counters, DLQ depth, circuit breaker states.
    Per spec Section A11.1.
    """
    from app.redis.client import get_redis
    from app.rabbitmq.circuit_breaker import get_all_circuit_breaker_statuses

    redis = await get_redis()

    lines = [
        "# HELP notification_events_received_total Total notification events received",
        "# TYPE notification_events_received_total counter",
    ]

    try:
        # DLQ depth gauge
        from app.db.base import AsyncSessionLocal
        from sqlalchemy import func, select
        from app.models.dead_letter_queue import DeadLetterQueue
        from app.models.notification import Notification
        from app.core.constants import NotificationStatus

        async with AsyncSessionLocal() as s:
            dlq_depth = await s.scalar(
                select(func.count()).select_from(DeadLetterQueue).where(
                    DeadLetterQueue.resolved == False
                )
            ) or 0

            total_sent = await s.scalar(
                select(func.count()).select_from(Notification).where(
                    Notification.status == NotificationStatus.DELIVERED
                )
            ) or 0

            total_failed = await s.scalar(
                select(func.count()).select_from(Notification).where(
                    Notification.status == NotificationStatus.FAILED
                )
            ) or 0

        lines += [
            f'notification_delivery_total{{status="delivered"}} {total_sent}',
            f'notification_delivery_total{{status="failed"}} {total_failed}',
            "",
            "# HELP notification_dlq_depth Current depth of dead letter queue",
            "# TYPE notification_dlq_depth gauge",
            f"notification_dlq_depth {dlq_depth}",
            "",
        ]

        # Circuit breaker states
        lines += [
            "# HELP delivery_provider_circuit_state Circuit breaker state 0=CLOSED 1=HALF_OPEN 2=OPEN",
            "# TYPE delivery_provider_circuit_state gauge",
        ]
        state_map = {"closed": 0, "half_open": 1, "open": 2}
        for cb in get_all_circuit_breaker_statuses():
            state_val = state_map.get(cb["state"], 0)
            lines.append(f'delivery_provider_circuit_state{{provider="{cb["provider"]}"}} {state_val}')

        # Frequency cap hits from Redis
        lines += [
            "",
            "# HELP notification_frequency_cap_hits_total Total frequency cap hits",
            "# TYPE notification_frequency_cap_hits_total counter",
        ]

    except Exception as e:
        lines.append(f"# Error collecting metrics: {e}")

    from fastapi.responses import PlainTextResponse
    return PlainTextResponse("\n".join(lines), media_type="text/plain; version=0.0.4")
