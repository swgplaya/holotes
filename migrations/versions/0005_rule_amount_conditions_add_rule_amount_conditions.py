"""Add amount conditions to classification rules.

Revision ID: 0005_rule_amount_conditions
Revises: 0004_telegram_summary_language
Create Date: 2026-08-11 14:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0005_rule_amount_conditions"
down_revision: Union[
    str,
    Sequence[str],
    None,
] = "0004_telegram_summary_language"
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
    """Add optional amount filters to rules."""

    op.add_column(
        "classification_rules",
        sa.Column(
            "amount_operator",
            sa.String(length=16),
            server_default="any",
            nullable=False,
        ),
    )

    op.add_column(
        "classification_rules",
        sa.Column(
            "amount_value_kopecks",
            sa.BigInteger(),
            nullable=True,
        ),
    )

    op.add_column(
        "classification_rules",
        sa.Column(
            "amount_value_to_kopecks",
            sa.BigInteger(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Remove amount filters from rules."""

    op.drop_column(
        "classification_rules",
        "amount_value_to_kopecks",
    )

    op.drop_column(
        "classification_rules",
        "amount_value_kopecks",
    )

    op.drop_column(
        "classification_rules",
        "amount_operator",
    )
