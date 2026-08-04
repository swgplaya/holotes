import pandas as pd
import pytest

from src.unit_economics import (
    build_unit_economics_summary,
)


PRODUCT_COLUMNS = [
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

COST_COLUMNS = [
    "id",
    "product_id",
    "name",
    "calculation_type",
    "amount_kopecks",
    "percentage_bp",
    "is_active",
    "comment",
]


def make_products(
    *rows: dict[str, object],
) -> pd.DataFrame:
    """Создаёт таблицу продуктов для тестов."""

    return pd.DataFrame(
        rows,
        columns=PRODUCT_COLUMNS,
    )


def make_costs(
    *rows: dict[str, object],
) -> pd.DataFrame:
    """Создаёт таблицу затрат для тестов."""

    return pd.DataFrame(
        rows,
        columns=COST_COLUMNS,
    )


def make_product(
    **overrides: object,
) -> dict[str, object]:
    """Создаёт продукт с базовыми значениями."""

    product: dict[str, object] = {
        "id": 1,
        "name": "Тестовый продукт",
        "planned_units": 100,
        "pricing_method": "manual",
        "pricing_value_bp": None,
        "manual_price_kopecks": 20_000,
        "rounding_step_kopecks": 100,
        "is_active": True,
        "comment": None,
    }

    product.update(overrides)

    return product


def make_cost(
    **overrides: object,
) -> dict[str, object]:
    """Создаёт статью затрат с базовыми значениями."""

    cost: dict[str, object] = {
        "id": 1,
        "product_id": 1,
        "name": "Затрата",
        "calculation_type": "fixed_per_unit",
        "amount_kopecks": 0,
        "percentage_bp": None,
        "is_active": True,
        "comment": None,
    }

    cost.update(overrides)

    return cost


def test_empty_products_return_empty_summary() -> None:
    result = build_unit_economics_summary(
        products=make_products(),
        cost_items=make_costs(),
    )

    assert result.empty

    assert "pricing_error" in result.columns
    assert "operating_result_kopecks" in result.columns


def test_inactive_products_and_costs_are_ignored() -> None:
    products = make_products(
        make_product(
            id=1,
            name="Активный",
        ),
        make_product(
            id=2,
            name="Неактивный",
            is_active=False,
        ),
    )

    costs = make_costs(
        make_cost(
            id=1,
            product_id=1,
            amount_kopecks=3_000,
        ),
        make_cost(
            id=2,
            product_id=1,
            amount_kopecks=7_000,
            is_active=False,
        ),
        make_cost(
            id=3,
            product_id=2,
            amount_kopecks=99_000,
        ),
    )

    result = build_unit_economics_summary(
        products,
        costs,
    )

    assert result["product_id"].tolist() == [1]

    row = result.iloc[0]

    assert row["fixed_per_unit_kopecks"] == 3_000
    assert row["base_cost_per_unit_kopecks"] == 3_000
    assert row["profit_per_unit_kopecks"] == 17_000


def test_manual_pricing_calculates_complete_unit_economics(
) -> None:
    products = make_products(
        make_product()
    )

    costs = make_costs(
        make_cost(
            id=1,
            name="Материалы",
            calculation_type="fixed_per_unit",
            amount_kopecks=10_000,
        ),
        make_cost(
            id=2,
            name="Аренда",
            calculation_type="fixed_period",
            amount_kopecks=200_000,
        ),
        make_cost(
            id=3,
            name="Эквайринг",
            calculation_type="percent_of_price",
            amount_kopecks=None,
            percentage_bp=300,
        ),
        make_cost(
            id=4,
            name="Комиссия",
            calculation_type="percent_of_revenue",
            amount_kopecks=None,
            percentage_bp=200,
        ),
    )

    result = build_unit_economics_summary(
        products,
        costs,
    )

    row = result.iloc[0]

    assert row["fixed_per_unit_kopecks"] == 10_000
    assert row["fixed_period_kopecks"] == 200_000

    assert (
        row["allocated_period_per_unit_kopecks"]
        == 2_000
    )

    assert row["base_cost_per_unit_kopecks"] == 12_000

    assert row["percentage_cost_rate"] == pytest.approx(
        5.0
    )

    assert row["selling_price_kopecks"] == 20_000

    assert (
        row["percentage_cost_per_unit_kopecks"]
        == 1_000
    )

    assert row["total_cost_per_unit_kopecks"] == 13_000
    assert row["profit_per_unit_kopecks"] == 7_000

    assert row["margin_percent"] == pytest.approx(
        35.0
    )

    assert row["revenue_kopecks"] == 2_000_000
    assert row["total_cost_kopecks"] == 1_300_000

    assert (
        row["operating_result_kopecks"]
        == 700_000
    )

    assert row["break_even_units"] == 23
    assert row["pricing_error"] is None


def test_markup_pricing_includes_percentage_cost_and_rounds_up(
) -> None:
    products = make_products(
        make_product(
            planned_units=10,
            pricing_method="markup",
            pricing_value_bp=2_500,
            manual_price_kopecks=None,
            rounding_step_kopecks=500,
        )
    )

    costs = make_costs(
        make_cost(
            id=1,
            calculation_type="fixed_per_unit",
            amount_kopecks=10_000,
        ),
        make_cost(
            id=2,
            calculation_type="fixed_period",
            amount_kopecks=10_000,
        ),
        make_cost(
            id=3,
            calculation_type="percent_of_price",
            amount_kopecks=None,
            percentage_bp=1_000,
        ),
    )

    row = build_unit_economics_summary(
        products,
        costs,
    ).iloc[0]

    assert row["base_cost_per_unit_kopecks"] == 11_000
    assert row["selling_price_kopecks"] == 15_500

    assert (
        row["percentage_cost_per_unit_kopecks"]
        == 1_550
    )

    assert row["total_cost_per_unit_kopecks"] == 12_550
    assert row["profit_per_unit_kopecks"] == 2_950

    assert row["margin_percent"] == pytest.approx(
        19.0322580645
    )

    assert row["revenue_kopecks"] == 155_000
    assert row["total_cost_kopecks"] == 125_500

    assert (
        row["operating_result_kopecks"]
        == 29_500
    )

    assert row["break_even_units"] == 3


def test_target_margin_pricing_calculates_price() -> None:
    products = make_products(
        make_product(
            planned_units=20,
            pricing_method="target_margin",
            pricing_value_bp=2_000,
            manual_price_kopecks=None,
            rounding_step_kopecks=100,
        )
    )

    costs = make_costs(
        make_cost(
            id=1,
            calculation_type="fixed_per_unit",
            amount_kopecks=8_000,
        ),
        make_cost(
            id=2,
            calculation_type="fixed_period",
            amount_kopecks=20_000,
        ),
        make_cost(
            id=3,
            calculation_type="percent_of_revenue",
            amount_kopecks=None,
            percentage_bp=1_000,
        ),
    )

    row = build_unit_economics_summary(
        products,
        costs,
    ).iloc[0]

    assert row["base_cost_per_unit_kopecks"] == 9_000
    assert row["selling_price_kopecks"] == 12_900

    assert (
        row["percentage_cost_per_unit_kopecks"]
        == 1_290
    )

    assert row["total_cost_per_unit_kopecks"] == 10_290
    assert row["profit_per_unit_kopecks"] == 2_610

    assert row["margin_percent"] == pytest.approx(
        20.2325581395
    )

    assert (
        row["operating_result_kopecks"]
        == 52_200
    )

    assert row["break_even_units"] == 6


def test_fixed_period_allocation_uses_half_up_rounding(
) -> None:
    products = make_products(
        make_product(
            planned_units=3,
            manual_price_kopecks=10_000,
        )
    )

    costs = make_costs(
        make_cost(
            calculation_type="fixed_period",
            amount_kopecks=10_001,
        )
    )

    row = build_unit_economics_summary(
        products,
        costs,
    ).iloc[0]

    assert (
        row["allocated_period_per_unit_kopecks"]
        == 3_334
    )

    assert row["base_cost_per_unit_kopecks"] == 3_334

    assert row["total_cost_kopecks"] == 10_001


@pytest.mark.parametrize(
    (
        "product_overrides",
        "costs",
        "expected_error",
    ),
    [
        (
            {
                "pricing_method": "not_set",
                "manual_price_kopecks": None,
            },
            [],
            "Способ ценообразования не выбран.",
        ),
        (
            {
                "pricing_method": "manual",
                "manual_price_kopecks": None,
            },
            [],
            "Не указана ручная цена.",
        ),
        (
            {
                "pricing_method": "markup",
                "pricing_value_bp": None,
                "manual_price_kopecks": None,
            },
            [],
            "Не указана наценка.",
        ),
        (
            {
                "pricing_method": "markup",
                "pricing_value_bp": 1_000,
                "manual_price_kopecks": None,
            },
            [
                make_cost(
                    calculation_type=(
                        "percent_of_price"
                    ),
                    amount_kopecks=None,
                    percentage_bp=10_000,
                )
            ],
            (
                "Сумма процентных расходов "
                "должна быть меньше 100%."
            ),
        ),
        (
            {
                "pricing_method": "target_margin",
                "pricing_value_bp": None,
                "manual_price_kopecks": None,
            },
            [],
            "Не указана целевая маржинальность.",
        ),
        (
            {
                "pricing_method": "target_margin",
                "pricing_value_bp": 2_000,
                "manual_price_kopecks": None,
            },
            [
                make_cost(
                    calculation_type=(
                        "percent_of_revenue"
                    ),
                    amount_kopecks=None,
                    percentage_bp=8_000,
                )
            ],
            (
                "Процентные расходы и целевая "
                "маржинальность вместе должны "
                "быть меньше 100%."
            ),
        ),
        (
            {
                "pricing_method": "unexpected",
                "manual_price_kopecks": None,
            },
            [],
            "Неизвестный способ ценообразования.",
        ),
    ],
)
def test_pricing_errors_block_financial_results(
    product_overrides: dict[str, object],
    costs: list[dict[str, object]],
    expected_error: str,
) -> None:
    products = make_products(
        make_product(
            **product_overrides,
        )
    )

    row = build_unit_economics_summary(
        products,
        make_costs(*costs),
    ).iloc[0]

    assert row["pricing_error"] == expected_error

    financial_columns = (
        "selling_price_kopecks",
        "percentage_cost_per_unit_kopecks",
        "total_cost_per_unit_kopecks",
        "profit_per_unit_kopecks",
        "margin_percent",
        "revenue_kopecks",
        "total_cost_kopecks",
        "operating_result_kopecks",
        "break_even_units",
    )

    for column in financial_columns:
        assert pd.isna(row[column])


def test_break_even_is_unavailable_when_contribution_is_not_positive(
) -> None:
    products = make_products(
        make_product(
            planned_units=10,
            manual_price_kopecks=10_000,
        )
    )

    costs = make_costs(
        make_cost(
            id=1,
            calculation_type="fixed_per_unit",
            amount_kopecks=10_000,
        ),
        make_cost(
            id=2,
            calculation_type="fixed_period",
            amount_kopecks=50_000,
        ),
    )

    row = build_unit_economics_summary(
        products,
        costs,
    ).iloc[0]

    assert row["profit_per_unit_kopecks"] == -5_000

    assert pd.isna(
        row["break_even_units"]
    )