"""Add cost_paisa, classification, event_code to notifications

Revision ID: 003
Revises: 002
Create Date: 2024-01-03 00:00:00.000000

"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("notifications", sa.Column("cost_paisa", sa.Integer(), nullable=True))
    op.add_column("notifications", sa.Column("classification", sa.String(20), nullable=True))
    op.add_column("notifications", sa.Column("event_code", sa.String(20), nullable=True))
    op.create_index("ix_notifications_event_code", "notifications", ["event_code"])


def downgrade() -> None:
    op.drop_index("ix_notifications_event_code", "notifications")
    op.drop_column("notifications", "event_code")
    op.drop_column("notifications", "classification")
    op.drop_column("notifications", "cost_paisa")
