from __future__ import annotations

import pandas as pd
import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

import src.unit_economics as unit_economics
from src.models import (
    UnitEconomicsCostItem,
    UnitEconomicsProduct,
)


@pytest.fixture
def isolated_repository(
    monkeypatch: pytest.MonkeyPatch,
    sqlite_session_factory: sessionmaker,
) -> sessionmaker:
    """Переключает модуль юнит-экономики на временную базу."""

    monkeypatch.setattr(
        unit_economics,
        "SessionLocal",
        sqlite_session_factory,
    )

    return sqlite_session_factory


def create_product(
    **overrides: object,
) -> int:
    """Создаёт продукт с базовыми значениями."""

    values: dict[str, object] = {
        "name": "Тестовый продукт",
        "planned_units": 100,
        "is_active": True,
        "comment": "Комментарий",
    }

    values.update(overrides)

    return unit_economics.create_unit_economics_product(
        **values,  # type: ignore[arg-type]
    )


def create_cost_item(
    product_id: int,
    **overrides: object,
) -> int:
    """Создаёт статью затрат с базовыми значениями."""

    values: dict[str, object] = {
        "product_id": product_id,
        "name": "Материалы",
        "calculation_type": "fixed_per_unit",
        "amount_kopecks": 10_000,
        "percentage_bp": None,
        "is_active": True,
        "comment": "Основная затрата",
    }

    values.update(overrides)

    return unit_economics.create_unit_economics_cost_item(
        **values,  # type: ignore[arg-type]
    )


def test_create_product_cleans_text_and_sets_defaults(
    isolated_repository: sessionmaker,
) -> None:
    del isolated_repository

    product_id = create_product(
        name="  Онлайн-курс  ",
        planned_units=25,
        is_active=False,
        comment="  Первый поток  ",
    )

    products = (
        unit_economics
        .get_unit_economics_products_dataframe()
        .set_index("id")
    )

    row = products.loc[product_id]

    assert row["name"] == "Онлайн-курс"
    assert row["planned_units"] == 25
    assert row["pricing_method"] == "not_set"

    assert pd.isna(
        row["pricing_value_bp"]
    )

    assert pd.isna(
        row["manual_price_kopecks"]
    )

    assert row["rounding_step_kopecks"] == 10_000
    assert bool(row["is_active"]) is False
    assert row["comment"] == "Первый поток"


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        (
            {
                "name": "   ",
            },
            "Укажи название продукта",
        ),
        (
            {
                "planned_units": 0,
            },
            "не меньше одной единицы",
        ),
    ],
)
def test_create_product_rejects_invalid_values(
    isolated_repository: sessionmaker,
    overrides: dict[str, object],
    message: str,
) -> None:
    del isolated_repository

    with pytest.raises(
        ValueError,
        match=message,
    ):
        create_product(
            **overrides
        )

    assert (
        unit_economics
        .get_unit_economics_products_dataframe()
        .empty
    )


def test_products_are_ordered_active_then_name(
    isolated_repository: sessionmaker,
) -> None:
    del isolated_repository

    create_product(
        name="Яблоко",
        is_active=True,
    )

    create_product(
        name="Абрикос",
        is_active=False,
    )

    create_product(
        name="Банан",
        is_active=True,
    )

    products = (
        unit_economics
        .get_unit_economics_products_dataframe()
    )

    assert products["name"].tolist() == [
        "Банан",
        "Яблоко",
        "Абрикос",
    ]

    assert products["is_active"].tolist() == [
        True,
        True,
        False,
    ]


def test_update_pricing_switches_between_methods(
    isolated_repository: sessionmaker,
) -> None:
    del isolated_repository

    product_id = create_product()

    unit_economics.update_unit_economics_pricing(
        product_id=product_id,
        pricing_method="manual",
        pricing_value_bp=2_500,
        manual_price_kopecks=19_990,
        rounding_step_kopecks=500,
    )

    manual = (
        unit_economics
        .get_unit_economics_products_dataframe()
        .set_index("id")
        .loc[product_id]
    )

    assert manual["pricing_method"] == "manual"

    assert pd.isna(
        manual["pricing_value_bp"]
    )

    assert (
        manual["manual_price_kopecks"]
        == 19_990
    )

    assert (
        manual["rounding_step_kopecks"]
        == 500
    )

    unit_economics.update_unit_economics_pricing(
        product_id=product_id,
        pricing_method="markup",
        pricing_value_bp=3_000,
        manual_price_kopecks=99_999,
        rounding_step_kopecks=1_000,
    )

    markup = (
        unit_economics
        .get_unit_economics_products_dataframe()
        .set_index("id")
        .loc[product_id]
    )

    assert markup["pricing_method"] == "markup"
    assert markup["pricing_value_bp"] == 3_000

    assert pd.isna(
        markup["manual_price_kopecks"]
    )

    assert (
        markup["rounding_step_kopecks"]
        == 1_000
    )

    unit_economics.update_unit_economics_pricing(
        product_id=product_id,
        pricing_method="not_set",
        pricing_value_bp=3_000,
        manual_price_kopecks=99_999,
        rounding_step_kopecks=100,
    )

    not_set = (
        unit_economics
        .get_unit_economics_products_dataframe()
        .set_index("id")
        .loc[product_id]
    )

    assert (
        not_set["pricing_method"]
        == "not_set"
    )

    assert pd.isna(
        not_set["pricing_value_bp"]
    )

    assert pd.isna(
        not_set["manual_price_kopecks"]
    )


@pytest.mark.parametrize(
    ("values", "message"),
    [
        (
            {
                "pricing_method": "unexpected",
                "pricing_value_bp": None,
                "manual_price_kopecks": None,
                "rounding_step_kopecks": 100,
            },
            "неизвестный способ",
        ),
        (
            {
                "pricing_method": "manual",
                "pricing_value_bp": None,
                "manual_price_kopecks": 0,
                "rounding_step_kopecks": 100,
            },
            "цену больше нуля",
        ),
        (
            {
                "pricing_method": "markup",
                "pricing_value_bp": None,
                "manual_price_kopecks": None,
                "rounding_step_kopecks": 100,
            },
            "Укажи процент",
        ),
        (
            {
                "pricing_method": "markup",
                "pricing_value_bp": -1,
                "manual_price_kopecks": None,
                "rounding_step_kopecks": 100,
            },
            "не может быть отрицательным",
        ),
        (
            {
                "pricing_method": "target_margin",
                "pricing_value_bp": 10_000,
                "manual_price_kopecks": None,
                "rounding_step_kopecks": 100,
            },
            "меньше 100%",
        ),
        (
            {
                "pricing_method": "manual",
                "pricing_value_bp": None,
                "manual_price_kopecks": 10_000,
                "rounding_step_kopecks": 0,
            },
            "Шаг округления",
        ),
    ],
)
def test_update_pricing_rejects_invalid_values(
    isolated_repository: sessionmaker,
    values: dict[str, object],
    message: str,
) -> None:
    del isolated_repository

    product_id = create_product()

    with pytest.raises(
        ValueError,
        match=message,
    ):
        unit_economics.update_unit_economics_pricing(
            product_id=product_id,
            **values,  # type: ignore[arg-type]
        )

    row = (
        unit_economics
        .get_unit_economics_products_dataframe()
        .set_index("id")
        .loc[product_id]
    )

    assert row["pricing_method"] == "not_set"


def test_create_fixed_and_percentage_cost_items(
    isolated_repository: sessionmaker,
) -> None:
    del isolated_repository

    product_id = create_product()

    fixed_id = create_cost_item(
        product_id,
        name="  Производство  ",
        calculation_type="fixed_period",
        amount_kopecks=250_000,
        percentage_bp=700,
        comment="  За месяц  ",
    )

    percentage_id = create_cost_item(
        product_id,
        name="Эквайринг",
        calculation_type="percent_of_revenue",
        amount_kopecks=999_999,
        percentage_bp=250,
        is_active=False,
        comment="",
    )

    costs = (
        unit_economics
        .get_unit_economics_cost_items_dataframe()
        .set_index("id")
    )

    fixed = costs.loc[fixed_id]

    assert fixed["name"] == "Производство"

    assert (
        fixed["calculation_type"]
        == "fixed_period"
    )

    assert (
        fixed["amount_kopecks"]
        == 250_000
    )

    assert pd.isna(
        fixed["percentage_bp"]
    )

    assert fixed["comment"] == "За месяц"

    percentage = costs.loc[percentage_id]

    assert percentage["name"] == "Эквайринг"

    assert (
        percentage["calculation_type"]
        == "percent_of_revenue"
    )

    assert pd.isna(
        percentage["amount_kopecks"]
    )

    assert (
        percentage["percentage_bp"]
        == 250
    )

    assert (
        bool(percentage["is_active"])
        is False
    )

    assert pd.isna(
        percentage["comment"]
    )


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        (
            {
                "name": "   ",
            },
            "Укажи название статьи затрат",
        ),
        (
            {
                "calculation_type": "unexpected",
            },
            "неизвестный тип затрат",
        ),
        (
            {
                "calculation_type": "fixed_per_unit",
                "amount_kopecks": -1,
            },
            "неотрицательную сумму",
        ),
        (
            {
                "calculation_type": "percent_of_price",
                "amount_kopecks": None,
                "percentage_bp": None,
            },
            "неотрицательный процент",
        ),
        (
            {
                "calculation_type": "percent_of_price",
                "amount_kopecks": None,
                "percentage_bp": -1,
            },
            "неотрицательный процент",
        ),
        (
            {
                "calculation_type": "percent_of_price",
                "amount_kopecks": None,
                "percentage_bp": 10_000,
            },
            "меньше 100%",
        ),
    ],
)
def test_create_cost_item_rejects_invalid_values(
    isolated_repository: sessionmaker,
    overrides: dict[str, object],
    message: str,
) -> None:
    del isolated_repository

    product_id = create_product()

    with pytest.raises(
        ValueError,
        match=message,
    ):
        create_cost_item(
            product_id,
            **overrides,
        )

    assert (
        unit_economics
        .get_unit_economics_cost_items_dataframe()
        .empty
    )


def test_missing_product_or_cost_item_raises_error(
    isolated_repository: sessionmaker,
) -> None:
    del isolated_repository

    with pytest.raises(
        ValueError,
        match="Продукт с ID 999 не найден",
    ):
        unit_economics.update_unit_economics_pricing(
            product_id=999,
            pricing_method="manual",
            pricing_value_bp=None,
            manual_price_kopecks=10_000,
            rounding_step_kopecks=100,
        )

    with pytest.raises(
        ValueError,
        match="Продукт с ID 999 не найден",
    ):
        create_cost_item(
            999
        )

    with pytest.raises(
        ValueError,
        match="Продукт с ID 999 не найден",
    ):
        unit_economics.set_unit_economics_product_active(
            999,
            False,
        )

    with pytest.raises(
        ValueError,
        match="Строка затрат с ID 999 не найдена",
    ):
        unit_economics.set_unit_economics_cost_item_active(
            999,
            False,
        )

    with pytest.raises(
        ValueError,
        match="Продукт с ID 999 не найден",
    ):
        unit_economics.delete_unit_economics_product(
            999
        )

    with pytest.raises(
        ValueError,
        match="Строка затрат с ID 999 не найдена",
    ):
        unit_economics.delete_unit_economics_cost_item(
            999
        )


def test_active_flags_and_cost_ordering(
    isolated_repository: sessionmaker,
) -> None:
    del isolated_repository

    first_product = create_product(
        name="Первый",
    )

    second_product = create_product(
        name="Второй",
    )

    inactive_cost = create_cost_item(
        first_product,
        name="Неактивная",
        is_active=False,
    )

    active_cost = create_cost_item(
        first_product,
        name="Активная",
        amount_kopecks=20_000,
    )

    second_cost = create_cost_item(
        second_product,
        name="Второй продукт",
        amount_kopecks=30_000,
    )

    unit_economics.set_unit_economics_product_active(
        second_product,
        False,
    )

    unit_economics.set_unit_economics_cost_item_active(
        inactive_cost,
        True,
    )

    unit_economics.set_unit_economics_cost_item_active(
        active_cost,
        False,
    )

    products = (
        unit_economics
        .get_unit_economics_products_dataframe()
        .set_index("id")
    )

    assert (
        bool(
            products.loc[
                first_product,
                "is_active",
            ]
        )
        is True
    )

    assert (
        bool(
            products.loc[
                second_product,
                "is_active",
            ]
        )
        is False
    )

    costs = (
        unit_economics
        .get_unit_economics_cost_items_dataframe()
    )

    assert costs["id"].tolist() == [
        inactive_cost,
        active_cost,
        second_cost,
    ]

    assert costs["is_active"].tolist() == [
        True,
        False,
        True,
    ]


def test_delete_cost_item_removes_only_selected_row(
    isolated_repository: sessionmaker,
) -> None:
    del isolated_repository

    product_id = create_product()

    first_id = create_cost_item(
        product_id,
        name="Первая",
    )

    second_id = create_cost_item(
        product_id,
        name="Вторая",
        amount_kopecks=20_000,
    )

    unit_economics.delete_unit_economics_cost_item(
        first_id
    )

    costs = (
        unit_economics
        .get_unit_economics_cost_items_dataframe()
    )

    assert costs["id"].tolist() == [
        second_id,
    ]

    assert costs["name"].tolist() == [
        "Вторая",
    ]


def test_delete_product_cascades_its_cost_items(
    isolated_repository: sessionmaker,
) -> None:
    first_product = create_product(
        name="Удаляемый продукт",
    )

    second_product = create_product(
        name="Сохраняемый продукт",
    )

    create_cost_item(
        first_product,
        name="Затрата 1",
    )

    create_cost_item(
        first_product,
        name="Затрата 2",
        amount_kopecks=20_000,
    )

    remaining_cost_id = create_cost_item(
        second_product,
        name="Сохраняемая затрата",
        amount_kopecks=30_000,
    )

    unit_economics.delete_unit_economics_product(
        first_product
    )

    products = (
        unit_economics
        .get_unit_economics_products_dataframe()
    )

    costs = (
        unit_economics
        .get_unit_economics_cost_items_dataframe()
    )

    assert products["id"].tolist() == [
        second_product,
    ]

    assert costs["id"].tolist() == [
        remaining_cost_id,
    ]

    assert costs["product_id"].tolist() == [
        second_product,
    ]

    with isolated_repository() as session:
        deleted_product_count = session.scalar(
            select(
                func.count(
                    UnitEconomicsProduct.id
                )
            ).where(
                UnitEconomicsProduct.id
                == first_product
            )
        )

        deleted_cost_count = session.scalar(
            select(
                func.count(
                    UnitEconomicsCostItem.id
                )
            ).where(
                UnitEconomicsCostItem.product_id
                == first_product
            )
        )

    assert deleted_product_count == 0
    assert deleted_cost_count == 0