"""Add notification_state_log and dead_letter_queue tables

Revision ID: 002
Revises: 001
Create Date: 2024-01-02 00:00:00.000000

"""
from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Notification State Log ────────────────────────────────────────────────
    op.create_table(
        "notification_state_log",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "notification_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("notifications.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("from_status", sa.String(30), nullable=True),
        sa.Column("to_status", sa.String(30), nullable=False),
        sa.Column("actor", sa.String(80), nullable=False),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_nsl_notification_id", "notification_state_log", ["notification_id"])
    op.create_index("ix_nsl_created_at", "notification_state_log", ["created_at"])
    op.create_index(
        "ix_nsl_notification_to_status",
        "notification_state_log",
        ["notification_id", "to_status"],
    )

    # ── Dead Letter Queue table ───────────────────────────────────────────────
    op.create_table(
        "dead_letter_queue",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "notification_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("notifications.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("original_event", postgresql.JSONB, nullable=False),
        sa.Column("failure_reason", sa.Text, nullable=False),
        sa.Column("retry_count", sa.Integer, nullable=False),
        sa.Column("last_error", sa.Text, nullable=True),
        sa.Column("resolved", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("resolved_by", sa.String(50), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_action", sa.String(50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_dlq_notification_id", "dead_letter_queue", ["notification_id"])
    op.create_index("ix_dlq_resolved", "dead_letter_queue", ["resolved"])

    # ── Performance indexes on notifications (from spec Section A8.2) ─────────
    # Composite index for user notification queries
    op.create_index(
        "ix_notifications_user_status_channel",
        "notifications",
        ["user_id", "status", "channel"],
    )
    # Partial index for worker queries (pending retries)
    op.execute("""
        CREATE INDEX ix_notifications_pending_work
        ON notifications (next_retry_at)
        WHERE status IN ('queued', 'retrying', 'pending')
    """)
    # Index for analytics aggregations
    op.create_index(
        "ix_notifications_event_type_created_at",
        "notifications",
        ["event_type", "created_at"],
    )

    # ── Consent records table ─────────────────────────────────────────────────
    op.create_table(
        "consent_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("consent_type", sa.String(50), nullable=False),  # opt_in, opt_out
        sa.Column("classification", sa.String(30), nullable=True),  # transactional, promotional
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("consent_text", sa.Text, nullable=True),
        sa.Column("source", sa.String(100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("consent_records")
    op.execute("DROP INDEX IF EXISTS ix_notifications_pending_work")
    op.drop_index("ix_notifications_event_type_created_at", "notifications")
    op.drop_index("ix_notifications_user_status_channel", "notifications")
    op.drop_index("ix_dlq_resolved", "dead_letter_queue")
    op.drop_index("ix_dlq_notification_id", "dead_letter_queue")
    op.drop_table("dead_letter_queue")
    op.drop_index("ix_nsl_notification_to_status", "notification_state_log")
    op.drop_index("ix_nsl_created_at", "notification_state_log")
    op.drop_index("ix_nsl_notification_id", "notification_state_log")
    op.drop_table("notification_state_log")
