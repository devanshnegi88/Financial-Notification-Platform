"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Enums ─────────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TYPE user_role_enum AS ENUM (
            'superadmin', 'admin', 'manager', 'analyst', 'user'
        )
    """)
    op.execute("""
        CREATE TYPE locale_enum AS ENUM ('en', 'hi')
    """)
    op.execute("""
        CREATE TYPE financial_event_type_enum AS ENUM (
            'transaction.success', 'transaction.failure', 'transaction.pending',
            'transaction.reversed', 'transaction.disputed',
            'payment.due', 'payment.overdue', 'payment.received',
            'payment.failed', 'payment.initiated',
            'account.created', 'account.debit', 'account.credit',
            'account.blocked', 'account.unblocked', 'account.closed',
            'account.low_balance', 'account.statement_ready',
            'loan.approved', 'loan.rejected', 'loan.disbursed',
            'loan.emi_due', 'loan.emi_paid', 'loan.emi_missed', 'loan.foreclosed',
            'investment.matured', 'investment.dividend',
            'investment.purchase', 'investment.redemption',
            'security.login_detected', 'security.password_changed',
            'security.otp_generated', 'security.suspicious_activity',
            'kyc.approved', 'kyc.rejected', 'kyc.pending',
            'offer.available', 'offer.expiring',
            'system.maintenance', 'onboarding.welcome'
        )
    """)
    op.execute("""
        CREATE TYPE notification_channel_enum AS ENUM (
            'sms', 'email', 'whatsapp', 'push', 'in_app'
        )
    """)
    op.execute("""
        CREATE TYPE notification_status_enum AS ENUM (
            'pending', 'queued', 'processing', 'sent', 'delivered',
            'failed', 'retrying', 'dead', 'cancelled', 'skipped'
        )
    """)
    op.execute("""
        CREATE TYPE notification_priority_enum AS ENUM (
            'critical', 'high', 'medium', 'low'
        )
    """)
    op.execute("""
        CREATE TYPE skip_reason_enum AS ENUM (
            'dnd_registered', 'quiet_hours', 'frequency_capped',
            'user_opt_out', 'channel_disabled', 'invalid_contact'
        )
    """)
    op.execute("""
        CREATE TYPE delivery_status_enum AS ENUM (
            'unknown', 'queued', 'sent', 'delivered', 'failed',
            'bounced', 'opened', 'clicked'
        )
    """)
    op.execute("""
        CREATE TYPE tmpl_event_type_enum AS ENUM (
            'transaction.success', 'transaction.failure', 'transaction.pending',
            'transaction.reversed', 'transaction.disputed',
            'payment.due', 'payment.overdue', 'payment.received',
            'payment.failed', 'payment.initiated',
            'account.created', 'account.debit', 'account.credit',
            'account.blocked', 'account.unblocked', 'account.closed',
            'account.low_balance', 'account.statement_ready',
            'loan.approved', 'loan.rejected', 'loan.disbursed',
            'loan.emi_due', 'loan.emi_paid', 'loan.emi_missed', 'loan.foreclosed',
            'investment.matured', 'investment.dividend',
            'investment.purchase', 'investment.redemption',
            'security.login_detected', 'security.password_changed',
            'security.otp_generated', 'security.suspicious_activity',
            'kyc.approved', 'kyc.rejected', 'kyc.pending',
            'offer.available', 'offer.expiring',
            'system.maintenance', 'onboarding.welcome'
        )
    """)
    op.execute("""
        CREATE TYPE tmpl_channel_enum AS ENUM (
            'sms', 'email', 'whatsapp', 'push', 'in_app'
        )
    """)
    op.execute("""
        CREATE TYPE analytics_event_type_enum AS ENUM (
            'transaction.success', 'transaction.failure', 'transaction.pending',
            'transaction.reversed', 'transaction.disputed',
            'payment.due', 'payment.overdue', 'payment.received',
            'payment.failed', 'payment.initiated',
            'account.created', 'account.debit', 'account.credit',
            'account.blocked', 'account.unblocked', 'account.closed',
            'account.low_balance', 'account.statement_ready',
            'loan.approved', 'loan.rejected', 'loan.disbursed',
            'loan.emi_due', 'loan.emi_paid', 'loan.emi_missed', 'loan.foreclosed',
            'investment.matured', 'investment.dividend',
            'investment.purchase', 'investment.redemption',
            'security.login_detected', 'security.password_changed',
            'security.otp_generated', 'security.suspicious_activity',
            'kyc.approved', 'kyc.rejected', 'kyc.pending',
            'offer.available', 'offer.expiring',
            'system.maintenance', 'onboarding.welcome'
        )
    """)
    op.execute("""
        CREATE TYPE analytics_channel_enum AS ENUM (
            'sms', 'email', 'whatsapp', 'push', 'in_app'
        )
    """)
    op.execute("""
        CREATE TYPE dl_channel_enum AS ENUM (
            'sms', 'email', 'whatsapp', 'push', 'in_app'
        )
    """)

    # ── Users ─────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("phone", sa.String(20), nullable=True, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("role", sa.Enum(name="user_role_enum"), nullable=False, server_default="user"),
        sa.Column("locale", sa.Enum(name="locale_enum"), nullable=False, server_default="en"),
        sa.Column("timezone", sa.String(50), nullable=False, server_default="Asia/Kolkata"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("is_verified", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("firebase_token", sa.Text, nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_phone", "users", ["phone"])

    # ── User Preferences ──────────────────────────────────────────────────────
    op.create_table(
        "user_preferences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("sms_enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("email_enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("whatsapp_enabled", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("push_enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("in_app_enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("disabled_event_types", sa.String(2000), nullable=True),
        sa.Column("quiet_hours_enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("quiet_hours_start", sa.Integer, nullable=False, server_default="22"),
        sa.Column("quiet_hours_end", sa.Integer, nullable=False, server_default="8"),
        sa.Column("frequency_cap_hourly", sa.Integer, nullable=False, server_default="0"),
        sa.Column("frequency_cap_daily", sa.Integer, nullable=False, server_default="0"),
        sa.Column("frequency_cap_weekly", sa.Integer, nullable=False, server_default="0"),
        sa.Column("preferred_locale", sa.String(10), nullable=False, server_default="en"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── Notifications ─────────────────────────────────────────────────────────
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.Enum(name="financial_event_type_enum"), nullable=False),
        sa.Column("channel", sa.Enum(name="notification_channel_enum"), nullable=False),
        sa.Column("status", sa.Enum(name="notification_status_enum"), nullable=False, server_default="pending"),
        sa.Column("priority", sa.Enum(name="notification_priority_enum"), nullable=False, server_default="medium"),
        sa.Column("subject", sa.String(500), nullable=True),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("template_id", sa.String(100), nullable=True),
        sa.Column("locale", sa.String(10), nullable=False, server_default="en"),
        sa.Column("recipient", sa.String(500), nullable=False),
        sa.Column("event_data", postgresql.JSONB, nullable=True),
        sa.Column("provider_message_id", sa.String(255), nullable=True),
        sa.Column("provider_response", postgresql.JSONB, nullable=True),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("max_retries", sa.Integer, nullable=False, server_default="3"),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("skip_reason", sa.Enum(name="skip_reason_enum"), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("kafka_topic", sa.String(200), nullable=True),
        sa.Column("kafka_partition", sa.Integer, nullable=True),
        sa.Column("kafka_offset", sa.Integer, nullable=True),
        sa.Column("idempotency_key", sa.String(255), nullable=True, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_event_type", "notifications", ["event_type"])
    op.create_index("ix_notifications_channel", "notifications", ["channel"])
    op.create_index("ix_notifications_status", "notifications", ["status"])
    op.create_index("ix_notifications_idempotency_key", "notifications", ["idempotency_key"])

    # ── Delivery Logs ─────────────────────────────────────────────────────────
    op.create_table(
        "delivery_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("notification_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("notifications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel", sa.Enum(name="dl_channel_enum"), nullable=False),
        sa.Column("status", sa.Enum(name="delivery_status_enum"), nullable=False, server_default="unknown"),
        sa.Column("provider", sa.String(100), nullable=False),
        sa.Column("provider_message_id", sa.String(255), nullable=True),
        sa.Column("provider_response", postgresql.JSONB, nullable=True),
        sa.Column("attempt_number", sa.Integer, nullable=False, server_default="1"),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("latency_ms", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_delivery_logs_notification_id", "delivery_logs", ["notification_id"])

    # ── Device Tokens ─────────────────────────────────────────────────────────
    op.create_table(
        "device_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token", sa.String(500), nullable=False),
        sa.Column("platform", sa.String(20), nullable=False),
        sa.Column("device_id", sa.String(255), nullable=True),
        sa.Column("device_name", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_device_tokens_user_id", "device_tokens", ["user_id"])
    op.create_index("ix_device_tokens_token", "device_tokens", ["token"])

    # ── Notification Templates ────────────────────────────────────────────────
    op.create_table(
        "notification_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("event_type", sa.Enum(name="tmpl_event_type_enum"), nullable=False),
        sa.Column("channel", sa.Enum(name="tmpl_channel_enum"), nullable=False),
        sa.Column("locale", sa.String(10), nullable=False, server_default="en"),
        sa.Column("subject", sa.String(500), nullable=True),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("html_body", sa.Text, nullable=True),
        sa.Column("variables", postgresql.JSONB, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("event_type", "channel", "locale", name="uq_template_event_channel_locale"),
    )
    op.create_index("ix_notification_templates_event_type", "notification_templates", ["event_type"])
    op.create_index("ix_notification_templates_channel", "notification_templates", ["channel"])

    # ── Analytics ─────────────────────────────────────────────────────────────
    op.create_table(
        "notification_analytics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("event_type", sa.Enum(name="analytics_event_type_enum"), nullable=False),
        sa.Column("channel", sa.Enum(name="analytics_channel_enum"), nullable=False),
        sa.Column("total_sent", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("total_delivered", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("total_failed", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("total_skipped", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("total_retried", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("total_dead", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("total_opened", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("total_clicked", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("skip_dnd", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("skip_quiet_hours", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("skip_frequency_cap", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("skip_user_opt_out", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("avg_latency_ms", sa.Float, nullable=True),
        sa.Column("p95_latency_ms", sa.Float, nullable=True),
        sa.Column("delivery_rate", sa.Float, nullable=True),
        sa.Column("open_rate", sa.Float, nullable=True),
        sa.Column("click_rate", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("date", "event_type", "channel", name="uq_analytics_date_event_channel"),
    )
    op.create_index("ix_notification_analytics_date", "notification_analytics", ["date"])
    op.create_index("ix_notification_analytics_event_type", "notification_analytics", ["event_type"])
    op.create_index("ix_notification_analytics_channel", "notification_analytics", ["channel"])


def downgrade() -> None:
    op.drop_table("notification_analytics")
    op.drop_table("notification_templates")
    op.drop_table("device_tokens")
    op.drop_table("delivery_logs")
    op.drop_table("notifications")
    op.drop_table("user_preferences")
    op.drop_table("users")

    for enum_name in [
        "dl_channel_enum", "analytics_channel_enum", "analytics_event_type_enum",
        "tmpl_channel_enum", "tmpl_event_type_enum", "delivery_status_enum",
        "skip_reason_enum", "notification_priority_enum", "notification_status_enum",
        "notification_channel_enum", "financial_event_type_enum", "locale_enum", "user_role_enum",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
