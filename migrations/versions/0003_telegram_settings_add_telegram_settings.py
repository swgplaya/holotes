"""Add Telegram bot settings.

Revision ID: 0003_telegram_settings
Revises: 0002_query_indexes
Create Date: 2026-08-05 23:55:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003_telegram_settings"

down_revision: Union[
    str,
    Sequence[str],
    None,
] = "0002_query_indexes"

branch_labels: Union[
    str,
    Sequence[str],
    None,
] = None

depends_on: Union[
    str,
    Sequence[str],
    None,
] = None


def upgrade() -> None:
    """Create Telegram settings and access tables."""

    op.create_table(
        "telegram_bot_settings",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "is_enabled",
            sa.Boolean(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "default_summary_period",
            sa.String(length=32),
            server_default="current_month",
            nullable=False,
        ),
        sa.Column(
            "include_cash_flow",
            sa.Boolean(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.Column(
            "include_pnl",
            sa.Boolean(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.Column(
            "include_pending_count",
            sa.Boolean(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.Column(
            "include_payment_calendar",
            sa.Boolean(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text(
                "(CURRENT_TIMESTAMP)"
            ),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text(
                "(CURRENT_TIMESTAMP)"
            ),
            nullable=False,
        ),
        sa.CheckConstraint(
            "id = 1",
            name=(
                "ck_telegram_bot_settings_"
                "singleton"
            ),
        ),
        sa.PrimaryKeyConstraint(
            "id"
        ),
    )

    op.create_table(
        "telegram_allowed_users",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "telegram_user_id",
            sa.BigInteger(),
            nullable=False,
        ),
        sa.Column(
            "display_name",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text(
                "(CURRENT_TIMESTAMP)"
            ),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text(
                "(CURRENT_TIMESTAMP)"
            ),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint(
            "id"
        ),
        sa.UniqueConstraint(
            "telegram_user_id",
            name=(
                "uq_telegram_allowed_users_"
                "user_id"
            ),
        ),
    )

    op.create_table(
        "telegram_allowed_chats",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "telegram_chat_id",
            sa.BigInteger(),
            nullable=False,
        ),
        sa.Column(
            "display_name",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "chat_type",
            sa.String(length=32),
            server_default="group",
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text(
                "(CURRENT_TIMESTAMP)"
            ),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text(
                "(CURRENT_TIMESTAMP)"
            ),
            nullable=False,
        ),
        sa.CheckConstraint(
            (
                "chat_type IN "
                "('group', 'supergroup')"
            ),
            name=(
                "ck_telegram_allowed_chats_"
                "chat_type"
            ),
        ),
        sa.PrimaryKeyConstraint(
            "id"
        ),
        sa.UniqueConstraint(
            "telegram_chat_id",
            name=(
                "uq_telegram_allowed_chats_"
                "chat_id"
            ),
        ),
    )

    settings_table = sa.table(
        "telegram_bot_settings",
        sa.column(
            "id",
            sa.Integer(),
        ),
        sa.column(
            "is_enabled",
            sa.Boolean(),
        ),
        sa.column(
            "default_summary_period",
            sa.String(),
        ),
        sa.column(
            "include_cash_flow",
            sa.Boolean(),
        ),
        sa.column(
            "include_pnl",
            sa.Boolean(),
        ),
        sa.column(
            "include_pending_count",
            sa.Boolean(),
        ),
        sa.column(
            "include_payment_calendar",
            sa.Boolean(),
        ),
    )

    op.bulk_insert(
        settings_table,
        [
            {
                "id": 1,
                "is_enabled": False,
                "default_summary_period":
                    "current_month",
                "include_cash_flow": True,
                "include_pnl": True,
                "include_pending_count": True,
                "include_payment_calendar": True,
            }
        ],
    )


def downgrade() -> None:
    """Remove Telegram settings and access tables."""

    op.drop_table(
        "telegram_allowed_chats"
    )

    op.drop_table(
        "telegram_allowed_users"
    )

    op.drop_table(
        "telegram_bot_settings"
    )
