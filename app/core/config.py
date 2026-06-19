from functools import lru_cache
from typing import List, Optional
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────────
    APP_NAME: str = "financial-notification-platform"
    APP_ENV: str = "development"
    APP_DEBUG: bool = False
    APP_SECRET_KEY: str
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    APP_WORKERS: int = 4
    API_V1_PREFIX: str = "/api/v1"
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    @property
    def allowed_origins_list(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]

    # ── JWT ──────────────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── PostgreSQL ───────────────────────────────────────────────────────────
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "financial_notifications"
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_POOL_TIMEOUT: int = 30

    # ── Redis ────────────────────────────────────────────────────────────────
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str
    REDIS_DB: int = 0
    REDIS_URL: str
    REDIS_CACHE_TTL: int = 3600
    REDIS_RATE_LIMIT_TTL: int = 86400

    # ── RabbitMQ ─────────────────────────────────────────────────────────────
    RABBITMQ_HOST: str = "rabbitmq"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "fnp_user"
    RABBITMQ_PASSWORD: str = "fnp_rabbit_password"
    RABBITMQ_VHOST: str = "/"
    RABBITMQ_URL: str = "amqp://fnp_user:fnp_rabbit_password@rabbitmq:5672/"

    # ── Kafka ────────────────────────────────────────────────────────────────
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka:9092"
    KAFKA_CONSUMER_GROUP_ID: str = "fnp-consumer-group"
    KAFKA_AUTO_OFFSET_RESET: str = "earliest"
    KAFKA_ENABLE_AUTO_COMMIT: bool = False
    KAFKA_SESSION_TIMEOUT_MS: int = 30000
    KAFKA_HEARTBEAT_INTERVAL_MS: int = 10000
    KAFKA_MAX_POLL_RECORDS: int = 500

    KAFKA_TOPIC_NOTIFICATION_EVENTS: str = "notification.events"
    KAFKA_TOPIC_NOTIFICATION_STATUS: str = "notification.status"
    KAFKA_TOPIC_DLQ: str = "notification.dlq"
    KAFKA_TOPIC_ANALYTICS: str = "notification.analytics"
    KAFKA_TOPIC_RETRY: str = "notification.retry"

    # ── Celery ───────────────────────────────────────────────────────────────
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str
    CELERY_TASK_SERIALIZER: str = "json"
    CELERY_RESULT_SERIALIZER: str = "json"
    CELERY_ACCEPT_CONTENT: str = "json"
    CELERY_TIMEZONE: str = "Asia/Kolkata"
    CELERY_MAX_RETRIES: int = 3
    CELERY_RETRY_BACKOFF: int = 60

    # ── Twilio ───────────────────────────────────────────────────────────────
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_SMS_FROM: str = ""
    TWILIO_WHATSAPP_FROM: str = ""
    TWILIO_MESSAGING_SERVICE_SID: str = ""

    # ── SendGrid ─────────────────────────────────────────────────────────────
    SENDGRID_API_KEY: str = ""
    SENDGRID_FROM_EMAIL: str = "noreply@example.com"
    SENDGRID_FROM_NAME: str = "Financial Notifications"
    SENDGRID_SANDBOX_MODE: bool = False

    # ── Firebase ─────────────────────────────────────────────────────────────
    FIREBASE_CREDENTIALS_PATH: str = "/app/firebase-credentials.json"
    FIREBASE_PROJECT_ID: str = ""

    # ── Notification Settings ────────────────────────────────────────────────
    DEFAULT_LOCALE: str = "en"
    SUPPORTED_LOCALES: str = "en,hi"
    QUIET_HOURS_START: int = 22
    QUIET_HOURS_END: int = 8
    QUIET_HOURS_TIMEZONE: str = "Asia/Kolkata"
    MAX_RETRIES: int = 3
    RETRY_DELAY_SECONDS: int = 60
    FREQUENCY_CAP_HOURLY: int = 10
    FREQUENCY_CAP_DAILY: int = 50
    FREQUENCY_CAP_WEEKLY: int = 200

    # ── TRAI DND ─────────────────────────────────────────────────────────────
    TRAI_DND_CHECK_ENABLED: bool = True
    TRAI_DND_API_URL: str = ""
    TRAI_DND_API_KEY: str = ""

    # ── Rate Limiting ────────────────────────────────────────────────────────
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 60
    RATE_LIMIT_REQUESTS_PER_HOUR: int = 1000

    # ── Logging ──────────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    LOG_FILE: str = "/var/log/fnp/app.log"

    # ── Admin ────────────────────────────────────────────────────────────────
    ADMIN_EMAIL: str = "admin@example.com"
    ADMIN_PASSWORD: str = "change_me"
    FIRST_SUPERUSER_EMAIL: str = "superadmin@example.com"
    FIRST_SUPERUSER_PASSWORD: str = "change_me_superadmin"

    @property
    def supported_locales_list(self) -> List[str]:
        return [l.strip() for l in self.SUPPORTED_LOCALES.split(",")]

    @property
    def kafka_bootstrap_servers_list(self) -> List[str]:
        return [s.strip() for s in self.KAFKA_BOOTSTRAP_SERVERS.split(",")]


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
