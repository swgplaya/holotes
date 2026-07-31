from __future__ import annotations

import math
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP
from typing import Any

import pandas as pd
from sqlalchemy import select

from src.database import SessionLocal
from src.models import (
    UnitEconomicsCostItem,
    UnitEconomicsProduct,
)


COST_TYPE_LABELS = {
    "fixed_per_unit": "Фиксированная сумма на единицу",
    "fixed_period": "Фиксированная сумма за период",
    "percent_of_price": "Процент от цены продажи",
    "percent_of_revenue": "Процент от выручки",
}

PRICING_METHOD_LABELS = {
    "not_set": "Не задано",
    "manual": "Цена вручную",
    "markup": "Наценка на базовые затраты",
    "target_margin": "Целевая маржинальность",
}


def _optional_text(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None

    text = str(value).strip()
    return text or None


def _rate_from_basis_points(value: int) -> Decimal:
    return Decimal(int(value)) / Decimal("10000")


def _round_up_to_step(
    value_kopecks: Decimal,
    step_kopecks: int,
) -> int:
    """Округляет цену вверх до выбранного шага."""

    step = max(int(step_kopecks), 1)

    if step == 1:
        return int(
            value_kopecks.quantize(
                Decimal("1"),
                rounding=ROUND_HALF_UP,
            )
        )

    step_decimal = Decimal(step)

    step_count = (
        value_kopecks / step_decimal
    ).to_integral_value(
        rounding=ROUND_CEILING
    )

    return int(step_count * step_decimal)


def create_unit_economics_product(
    *,
    name: str,
    planned_units: int,
    is_active: bool,
    comment: str,
) -> int:
    """Создаёт продукт без обязательного указания цены."""

    clean_name = _optional_text(name)

    if clean_name is None:
        raise ValueError("Укажи название продукта.")

    if planned_units < 1:
        raise ValueError(
            "Плановое количество должно быть не меньше одной единицы."
        )

    product = UnitEconomicsProduct(
        name=clean_name,
        planned_units=int(planned_units),
        pricing_method="not_set",
        pricing_value_bp=None,
        manual_price_kopecks=None,
        rounding_step_kopecks=10_000,
        is_active=bool(is_active),
        comment=_optional_text(comment),
    )

    with SessionLocal() as session:
        session.add(product)
        session.commit()
        session.refresh(product)

        return product.id


def update_unit_economics_pricing(
    *,
    product_id: int,
    pricing_method: str,
    pricing_value_bp: int | None,
    manual_price_kopecks: int | None,
    rounding_step_kopecks: int,
) -> None:
    """Сохраняет настройки ценообразования."""

    if pricing_method not in PRICING_METHOD_LABELS:
        raise ValueError(
            "Выбран неизвестный способ ценообразования."
        )

    if pricing_method == "manual":
        if (
            manual_price_kopecks is None
            or manual_price_kopecks <= 0
        ):
            raise ValueError(
                "Для ручного режима укажи цену больше нуля."
            )

        pricing_value_bp = None

    elif pricing_method in {
        "markup",
        "target_margin",
    }:
        if pricing_value_bp is None:
            raise ValueError(
                "Укажи процент для расчёта цены."
            )

        if pricing_value_bp < 0:
            raise ValueError(
                "Процент не может быть отрицательным."
            )

        if (
            pricing_method == "target_margin"
            and pricing_value_bp >= 10_000
        ):
            raise ValueError(
                "Целевая маржинальность должна быть меньше 100%."
            )

        manual_price_kopecks = None

    else:
        pricing_value_bp = None
        manual_price_kopecks = None

    if rounding_step_kopecks < 1:
        raise ValueError(
            "Шаг округления должен быть больше нуля."
        )

    with SessionLocal() as session:
        product = session.get(
            UnitEconomicsProduct,
            int(product_id),
        )

        if product is None:
            raise ValueError(
                f"Продукт с ID {product_id} не найден."
            )

        product.pricing_method = pricing_method
        product.pricing_value_bp = pricing_value_bp
        product.manual_price_kopecks = (
            manual_price_kopecks
        )
        product.rounding_step_kopecks = int(
            rounding_step_kopecks
        )

        session.commit()


def create_unit_economics_cost_item(
    *,
    product_id: int,
    name: str,
    calculation_type: str,
    amount_kopecks: int | None,
    percentage_bp: int | None,
    is_active: bool,
    comment: str,
) -> int:
    """Добавляет фиксированную или процентную затрату."""

    clean_name = _optional_text(name)

    if clean_name is None:
        raise ValueError(
            "Укажи название статьи затрат."
        )

    if calculation_type not in COST_TYPE_LABELS:
        raise ValueError(
            "Выбран неизвестный тип затрат."
        )

    fixed_types = {
        "fixed_per_unit",
        "fixed_period",
    }

    percentage_types = {
        "percent_of_price",
        "percent_of_revenue",
    }

    if calculation_type in fixed_types:
        if amount_kopecks is None or amount_kopecks < 0:
            raise ValueError(
                "Укажи неотрицательную сумму затрат."
            )

        percentage_bp = None

    elif calculation_type in percentage_types:
        if percentage_bp is None or percentage_bp < 0:
            raise ValueError(
                "Укажи неотрицательный процент."
            )

        if percentage_bp >= 10_000:
            raise ValueError(
                "Процент одной статьи должен быть меньше 100%."
            )

        amount_kopecks = None

    with SessionLocal() as session:
        product = session.get(
            UnitEconomicsProduct,
            int(product_id),
        )

        if product is None:
            raise ValueError(
                f"Продукт с ID {product_id} не найден."
            )

        cost_item = UnitEconomicsCostItem(
            product_id=int(product_id),
            name=clean_name,
            calculation_type=calculation_type,
            amount_kopecks=amount_kopecks,
            percentage_bp=percentage_bp,
            is_active=bool(is_active),
            comment=_optional_text(comment),
        )

        session.add(cost_item)
        session.commit()
        session.refresh(cost_item)

        return cost_item.id


def get_unit_economics_products_dataframe() -> pd.DataFrame:
    columns = [
        "id",
        "name",
        "planned_units",
        "pricing_method",
        "pricing_value_bp",
        "manual_price_kopecks",
        "rounding_step_kopecks",
        "is_active",
        "comment",
    ]

    statement = (
        select(UnitEconomicsProduct)
        .order_by(
            UnitEconomicsProduct.is_active.desc(),
            UnitEconomicsProduct.name.asc(),
            UnitEconomicsProduct.id.asc(),
        )
    )

    with SessionLocal() as session:
        products = session.scalars(statement).all()

        rows = [
            {
                "id": product.id,
                "name": product.name,
                "planned_units": product.planned_units,
                "pricing_method":
                    product.pricing_method,
                "pricing_value_bp":
                    product.pricing_value_bp,
                "manual_price_kopecks":
                    product.manual_price_kopecks,
                "rounding_step_kopecks":
                    product.rounding_step_kopecks,
                "is_active": product.is_active,
                "comment": product.comment,
            }
            for product in products
        ]

    return pd.DataFrame(rows, columns=columns)


def get_unit_economics_cost_items_dataframe() -> pd.DataFrame:
    columns = [
        "id",
        "product_id",
        "name",
        "calculation_type",
        "amount_kopecks",
        "percentage_bp",
        "is_active",
        "comment",
    ]

    statement = (
        select(UnitEconomicsCostItem)
        .order_by(
            UnitEconomicsCostItem.product_id.asc(),
            UnitEconomicsCostItem.is_active.desc(),
            UnitEconomicsCostItem.id.asc(),
        )
    )

    with SessionLocal() as session:
        cost_items = session.scalars(statement).all()

        rows = [
            {
                "id": item.id,
                "product_id": item.product_id,
                "name": item.name,
                "calculation_type":
                    item.calculation_type,
                "amount_kopecks":
                    item.amount_kopecks,
                "percentage_bp":
                    item.percentage_bp,
                "is_active": item.is_active,
                "comment": item.comment,
            }
            for item in cost_items
        ]

    return pd.DataFrame(rows, columns=columns)


def set_unit_economics_product_active(
    product_id: int,
    is_active: bool,
) -> None:
    with SessionLocal() as session:
        product = session.get(
            UnitEconomicsProduct,
            int(product_id),
        )

        if product is None:
            raise ValueError(
                f"Продукт с ID {product_id} не найден."
            )

        product.is_active = bool(is_active)
        session.commit()


def set_unit_economics_cost_item_active(
    cost_item_id: int,
    is_active: bool,
) -> None:
    with SessionLocal() as session:
        item = session.get(
            UnitEconomicsCostItem,
            int(cost_item_id),
        )

        if item is None:
            raise ValueError(
                f"Строка затрат с ID {cost_item_id} не найдена."
            )

        item.is_active = bool(is_active)
        session.commit()


def delete_unit_economics_product(
    product_id: int,
) -> None:
    with SessionLocal() as session:
        product = session.get(
            UnitEconomicsProduct,
            int(product_id),
        )

        if product is None:
            raise ValueError(
                f"Продукт с ID {product_id} не найден."
            )

        session.delete(product)
        session.commit()


def delete_unit_economics_cost_item(
    cost_item_id: int,
) -> None:
    with SessionLocal() as session:
        item = session.get(
            UnitEconomicsCostItem,
            int(cost_item_id),
        )

        if item is None:
            raise ValueError(
                f"Строка затрат с ID {cost_item_id} не найдена."
            )

        session.delete(item)
        session.commit()


def build_unit_economics_summary(
    products: pd.DataFrame,
    cost_items: pd.DataFrame,
) -> pd.DataFrame:
    """Рассчитывает себестоимость, цену и результат."""

    columns = [
        "product_id",
        "product_name",
        "planned_units",
        "pricing_method",
        "fixed_per_unit_kopecks",
        "fixed_period_kopecks",
        "allocated_period_per_unit_kopecks",
        "base_cost_per_unit_kopecks",
        "percentage_cost_rate",
        "selling_price_kopecks",
        "percentage_cost_per_unit_kopecks",
        "total_cost_per_unit_kopecks",
        "profit_per_unit_kopecks",
        "margin_percent",
        "revenue_kopecks",
        "total_cost_kopecks",
        "operating_result_kopecks",
        "break_even_units",
        "pricing_error",
    ]

    if products.empty:
        return pd.DataFrame(columns=columns)

    active_products = products.loc[
        products["is_active"].astype(bool)
    ].copy()

    if cost_items.empty:
        active_cost_items = cost_items.copy()
    else:
        active_cost_items = cost_items.loc[
            cost_items["is_active"].astype(bool)
        ].copy()

    rows: list[dict[str, Any]] = []

    for _, product in active_products.iterrows():
        product_id = int(product["id"])
        planned_units = int(product["planned_units"])

        product_costs = active_cost_items.loc[
            active_cost_items["product_id"]
            == product_id
        ]

        fixed_per_unit = int(
            product_costs.loc[
                product_costs["calculation_type"]
                == "fixed_per_unit",
                "amount_kopecks",
            ].fillna(0).sum()
        )

        fixed_period = int(
            product_costs.loc[
                product_costs["calculation_type"]
                == "fixed_period",
                "amount_kopecks",
            ].fillna(0).sum()
        )

        percentage_bp = int(
            product_costs.loc[
                product_costs[
                    "calculation_type"
                ].isin(
                    {
                        "percent_of_price",
                        "percent_of_revenue",
                    }
                ),
                "percentage_bp",
            ].fillna(0).sum()
        )

        percentage_rate = _rate_from_basis_points(
            percentage_bp
        )

        allocated_period = (
            Decimal(fixed_period)
            / Decimal(planned_units)
        )

        base_cost = (
            Decimal(fixed_per_unit)
            + allocated_period
        )

        pricing_method = str(
            product["pricing_method"]
        )

        pricing_error: str | None = None
        raw_price: Decimal | None = None

        if pricing_method == "not_set":
            pricing_error = (
                "Способ ценообразования не выбран."
            )

        elif pricing_method == "manual":
            manual_price = product[
                "manual_price_kopecks"
            ]

            if manual_price is None or pd.isna(
                manual_price
            ):
                pricing_error = (
                    "Не указана ручная цена."
                )
            else:
                raw_price = Decimal(
                    int(manual_price)
                )

        elif pricing_method == "markup":
            pricing_value = product[
                "pricing_value_bp"
            ]

            if pricing_value is None or pd.isna(
                pricing_value
            ):
                pricing_error = (
                    "Не указана наценка."
                )
            elif percentage_rate >= 1:
                pricing_error = (
                    "Сумма процентных расходов "
                    "должна быть меньше 100%."
                )
            else:
                markup_rate = (
                    _rate_from_basis_points(
                        int(pricing_value)
                    )
                )

                raw_price = (
                    base_cost
                    * (Decimal("1") + markup_rate)
                    / (
                        Decimal("1")
                        - percentage_rate
                    )
                )

        elif pricing_method == "target_margin":
            pricing_value = product[
                "pricing_value_bp"
            ]

            if pricing_value is None or pd.isna(
                pricing_value
            ):
                pricing_error = (
                    "Не указана целевая маржинальность."
                )
            else:
                target_margin = (
                    _rate_from_basis_points(
                        int(pricing_value)
                    )
                )

                denominator = (
                    Decimal("1")
                    - percentage_rate
                    - target_margin
                )

                if denominator <= 0:
                    pricing_error = (
                        "Процентные расходы и целевая "
                        "маржинальность вместе должны "
                        "быть меньше 100%."
                    )
                else:
                    raw_price = (
                        base_cost / denominator
                    )

        else:
            pricing_error = (
                "Неизвестный способ ценообразования."
            )

        if raw_price is None:
            selling_price = None
            percentage_cost_per_unit = None
            total_cost_per_unit = None
            profit_per_unit = None
            margin_percent = None
            revenue = None
            total_cost = None
            operating_result = None
            break_even_units = None

        else:
            if pricing_method == "manual":
                selling_price = int(
                    raw_price.quantize(
                        Decimal("1"),
                        rounding=ROUND_HALF_UP,
                    )
                )
            else:
                selling_price = _round_up_to_step(
                    value_kopecks=raw_price,
                    step_kopecks=int(
                        product[
                            "rounding_step_kopecks"
                        ]
                    ),
                )

            price_decimal = Decimal(selling_price)

            percentage_cost_per_unit = int(
                (
                    price_decimal
                    * percentage_rate
                ).quantize(
                    Decimal("1"),
                    rounding=ROUND_HALF_UP,
                )
            )

            total_cost_per_unit = int(
                (
                    base_cost
                    + Decimal(
                        percentage_cost_per_unit
                    )
                ).quantize(
                    Decimal("1"),
                    rounding=ROUND_HALF_UP,
                )
            )

            profit_per_unit = (
                selling_price
                - total_cost_per_unit
            )

            if selling_price > 0:
                margin_percent = (
                    profit_per_unit
                    / selling_price
                    * 100
                )
            else:
                margin_percent = None

            revenue = (
                selling_price * planned_units
            )

            total_cost = (
                fixed_per_unit * planned_units
                + fixed_period
                + percentage_cost_per_unit
                * planned_units
            )

            operating_result = (
                revenue - total_cost
            )

            unit_contribution_before_period = (
                price_decimal
                * (
                    Decimal("1")
                    - percentage_rate
                )
                - Decimal(fixed_per_unit)
            )

            if unit_contribution_before_period > 0:
                break_even_units = math.ceil(
                    Decimal(fixed_period)
                    / unit_contribution_before_period
                )
            else:
                break_even_units = None

        rows.append(
            {
                "product_id": product_id,
                "product_name": product["name"],
                "planned_units": planned_units,
                "pricing_method": pricing_method,
                "fixed_per_unit_kopecks":
                    fixed_per_unit,
                "fixed_period_kopecks":
                    fixed_period,
                "allocated_period_per_unit_kopecks":
                    int(
                        allocated_period.quantize(
                            Decimal("1"),
                            rounding=ROUND_HALF_UP,
                        )
                    ),
                "base_cost_per_unit_kopecks":
                    int(
                        base_cost.quantize(
                            Decimal("1"),
                            rounding=ROUND_HALF_UP,
                        )
                    ),
                "percentage_cost_rate":
                    float(percentage_rate * 100),
                "selling_price_kopecks":
                    selling_price,
                "percentage_cost_per_unit_kopecks":
                    percentage_cost_per_unit,
                "total_cost_per_unit_kopecks":
                    total_cost_per_unit,
                "profit_per_unit_kopecks":
                    profit_per_unit,
                "margin_percent":
                    margin_percent,
                "revenue_kopecks": revenue,
                "total_cost_kopecks": total_cost,
                "operating_result_kopecks":
                    operating_result,
                "break_even_units":
                    break_even_units,
                "pricing_error":
                    pricing_error,
            }
        )

    return pd.DataFrame(rows, columns=columns)