"""Add per-chat Telegram summary language.

Revision ID: 0004_telegram_summary_language
Revises: 0003_telegram_settings
Create Date: 2026-08-06 18:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004_telegram_summary_language"
down_revision: Union[
    str,
    Sequence[str],
    None,
] = "0003_telegram_settings"
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
    """Create Telegram chat preference storage."""

    op.create_table(
        "telegram_chat_preferences",
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
            "language",
            sa.String(length=16),
            server_default="ru",
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
            "language IN ('ru', 'en', 'zh-CN')",
            name=(
                "ck_telegram_chat_preferences_"
                "language"
            ),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "telegram_chat_id",
            name=(
                "uq_telegram_chat_preferences_"
                "chat_id"
            ),
        ),
    )


def downgrade() -> None:
    """Remove Telegram chat preference storage."""

    op.drop_table(
        "telegram_chat_preferences"
    )
