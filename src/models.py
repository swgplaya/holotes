from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class BankTransaction(Base):
    """Банковская операция после нормализации."""

    __tablename__ = "bank_transactions"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    # Используется для защиты от повторного импорта.
    source_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
    )

    account_number: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    direction: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    bank_operation_type: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    bank_category: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    bank_operation_kind: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    status: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    posted_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        index=True,
    )
    transaction_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    payment_number: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )

    # Деньги храним целым числом копеек.
    amount_kopecks: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    signed_amount_kopecks: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    currency: Mapped[str | None] = mapped_column(
        String(8),
        nullable=True,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    payment_purpose: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    counterparty_inn: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        index=True,
    )
    counterparty_name: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
        index=True,
    )
    mcc: Mapped[str | None] = mapped_column(
        String(16),
        nullable=True,
    )
    tax_code: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    # Наши будущие управленческие поля.
    pnl_category: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    cf_category: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    include_in_pnl: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )
    include_in_cf: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )
    classification_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="unclassified",
        index=True,
    )
    classification_source: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )
    comment: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )