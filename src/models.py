from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
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

class ClassificationRule(Base):
    """Правило автоматической классификации операций."""

    __tablename__ = "classification_rules"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=100,
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    direction_filter: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="any",
    )

    match_field: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    match_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="contains",
    )

    match_value: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )

    include_in_pnl: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )

    pnl_category: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    include_in_cf: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )

    cf_category: Mapped[str | None] = mapped_column(
        String(255),
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

class PlannedCashFlow(Base):
    """Запланированное поступление или списание."""

    __tablename__ = "planned_cash_flows"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # inflow — поступление, outflow — платёж
    direction: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        index=True,
    )

    # Всегда положительное количество копеек.
    amount_kopecks: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    category: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    counterparty: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )

    start_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    # once, monthly или yearly
    recurrence: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="once",
    )

    end_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
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

class UnitEconomicsProduct(Base):
    """Продукт для расчёта себестоимости и цены."""

    __tablename__ = "unit_economics_products"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    planned_units: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    # not_set, manual, markup, target_margin
    pricing_method: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="not_set",
    )

    # Наценка или целевая маржинальность
    # в базисных пунктах: 2500 = 25,00%.
    pricing_value_bp: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    manual_price_kopecks: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    # Шаг округления расчётной цены.
    # 10 000 копеек = 100 рублей.
    rounding_step_kopecks: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=10_000,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
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


class UnitEconomicsCostItem(Base):
    """Строка затрат продукта."""

    __tablename__ = "unit_economics_cost_items"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey(
            "unit_economics_products.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # fixed_per_unit
    # fixed_period
    # percent_of_price
    # percent_of_revenue
    calculation_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    # Для фиксированных рублёвых затрат.
    amount_kopecks: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    # Для процентных затрат.
    # 250 = 2,50%.
    percentage_bp: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
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