from datetime import date

import pandas as pd
import pytest

from src.payment_calendar import (
    build_cash_forecast,
    expand_planned_cash_flows,
)


PLAN_COLUMNS = [
    "id",
    "name",
    "direction",
    "amount_kopecks",
    "category",
    "counterparty",
    "start_date",
    "recurrence",
    "end_date",
    "is_active",
    "comment",
]


def make_plans(
    *rows: dict[str, object],
) -> pd.DataFrame:
    """Создаёт таблицу планов с полным набором столбцов."""

    return pd.DataFrame(
        rows,
        columns=PLAN_COLUMNS,
    )


def test_expand_empty_plans_returns_empty_table() -> None:
    result = expand_planned_cash_flows(
        plans=make_plans(),
        period_start=date(2026, 1, 1),
        period_end=date(2026, 1, 31),
    )

    assert result.empty

    assert result.columns.tolist() == [
        "plan_id",
        "date",
        "name",
        "direction",
        "signed_amount_kopecks",
        "category",
        "counterparty",
        "comment",
    ]


def test_expand_once_applies_direction_sign() -> None:
    plans = make_plans(
        {
            "id": 1,
            "name": "Оплата клиента",
            "direction": "inflow",
            "amount_kopecks": 100_000,
            "category": "Продажи",
            "counterparty": "Клиент",
            "start_date": date(2026, 1, 10),
            "recurrence": "once",
            "end_date": date(2026, 12, 31),
            "is_active": True,
            "comment": "Разовый платёж",
        },
        {
            "id": 2,
            "name": "Аренда",
            "direction": "outflow",
            "amount_kopecks": 40_000,
            "category": "Операционные расходы",
            "counterparty": "Арендодатель",
            "start_date": date(2026, 1, 15),
            "recurrence": "once",
            "end_date": None,
            "is_active": True,
            "comment": None,
        },
    )

    result = expand_planned_cash_flows(
        plans=plans,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 1, 31),
    )

    assert result["plan_id"].tolist() == [
        1,
        2,
    ]

    assert result["date"].tolist() == [
        date(2026, 1, 10),
        date(2026, 1, 15),
    ]

    assert result[
        "signed_amount_kopecks"
    ].tolist() == [
        100_000,
        -40_000,
    ]


def test_expand_skips_inactive_and_future_plans() -> None:
    plans = make_plans(
        {
            "id": 1,
            "name": "Неактивный план",
            "direction": "inflow",
            "amount_kopecks": 10_000,
            "category": None,
            "counterparty": None,
            "start_date": date(2026, 1, 10),
            "recurrence": "once",
            "end_date": None,
            "is_active": False,
            "comment": None,
        },
        {
            "id": 2,
            "name": "Будущий план",
            "direction": "inflow",
            "amount_kopecks": 20_000,
            "category": None,
            "counterparty": None,
            "start_date": date(2026, 2, 1),
            "recurrence": "once",
            "end_date": None,
            "is_active": True,
            "comment": None,
        },
    )

    result = expand_planned_cash_flows(
        plans=plans,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 1, 31),
    )

    assert result.empty


def test_monthly_recurrence_preserves_anchor_day() -> None:
    plans = make_plans(
        {
            "id": 1,
            "name": "Ежемесячный платёж",
            "direction": "outflow",
            "amount_kopecks": 30_000,
            "category": None,
            "counterparty": None,
            "start_date": date(2026, 1, 31),
            "recurrence": "monthly",
            "end_date": None,
            "is_active": True,
            "comment": None,
        }
    )

    result = expand_planned_cash_flows(
        plans=plans,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 4, 30),
    )

    assert result["date"].tolist() == [
        date(2026, 1, 31),
        date(2026, 2, 28),
        date(2026, 3, 31),
        date(2026, 4, 30),
    ]

    assert result[
        "signed_amount_kopecks"
    ].tolist() == [
        -30_000,
        -30_000,
        -30_000,
        -30_000,
    ]


def test_yearly_recurrence_handles_february_29() -> None:
    plans = make_plans(
        {
            "id": 1,
            "name": "Ежегодный платёж",
            "direction": "outflow",
            "amount_kopecks": 12_000,
            "category": None,
            "counterparty": None,
            "start_date": date(2024, 2, 29),
            "recurrence": "yearly",
            "end_date": None,
            "is_active": True,
            "comment": None,
        }
    )

    result = expand_planned_cash_flows(
        plans=plans,
        period_start=date(2024, 1, 1),
        period_end=date(2028, 12, 31),
    )

    assert result["date"].tolist() == [
        date(2024, 2, 29),
        date(2025, 2, 28),
        date(2026, 2, 28),
        date(2027, 2, 28),
        date(2028, 2, 29),
    ]


def test_plan_end_date_is_inclusive() -> None:
    plans = make_plans(
        {
            "id": 1,
            "name": "Подписка",
            "direction": "outflow",
            "amount_kopecks": 5_000,
            "category": None,
            "counterparty": None,
            "start_date": date(2026, 1, 15),
            "recurrence": "monthly",
            "end_date": date(2026, 3, 15),
            "is_active": True,
            "comment": None,
        }
    )

    result = expand_planned_cash_flows(
        plans=plans,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 12, 31),
    )

    assert result["date"].tolist() == [
        date(2026, 1, 15),
        date(2026, 2, 15),
        date(2026, 3, 15),
    ]


def test_expand_rejects_inverted_period() -> None:
    with pytest.raises(
        ValueError,
        match="Начало прогноза",
    ):
        expand_planned_cash_flows(
            plans=make_plans(),
            period_start=date(2026, 2, 1),
            period_end=date(2026, 1, 1),
        )


def test_expand_rejects_unknown_recurrence() -> None:
    plans = make_plans(
        {
            "id": 1,
            "name": "Повреждённый план",
            "direction": "inflow",
            "amount_kopecks": 10_000,
            "category": None,
            "counterparty": None,
            "start_date": date(2026, 1, 1),
            "recurrence": "weekly",
            "end_date": None,
            "is_active": True,
            "comment": None,
        }
    )

    with pytest.raises(
        ValueError,
        match="Неизвестная периодичность: weekly",
    ):
        expand_planned_cash_flows(
            plans=plans,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
        )


def test_build_cash_forecast_calculates_balances() -> None:
    occurrences = pd.DataFrame(
        {
            "date": [
                date(2026, 1, 1),
                date(2026, 1, 2),
                date(2026, 1, 2),
                date(2026, 1, 4),
            ],
            "signed_amount_kopecks": [
                100_000,
                -30_000,
                10_000,
                -50_000,
            ],
        }
    )

    result = build_cash_forecast(
        occurrences=occurrences,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 1, 4),
        opening_balance_kopecks=20_000,
    )

    assert result[
        "net_cash_flow_kopecks"
    ].tolist() == [
        100_000,
        -20_000,
        0,
        -50_000,
    ]

    assert result[
        "planned_inflow_kopecks"
    ].tolist() == [
        100_000,
        0,
        0,
        0,
    ]

    assert result[
        "planned_outflow_kopecks"
    ].tolist() == [
        0,
        20_000,
        0,
        50_000,
    ]

    assert result[
        "opening_balance_kopecks"
    ].tolist() == [
        20_000,
        120_000,
        100_000,
        100_000,
    ]

    assert result[
        "closing_balance_kopecks"
    ].tolist() == [
        120_000,
        100_000,
        100_000,
        50_000,
    ]


def test_build_cash_forecast_without_events_keeps_balance(
) -> None:
    result = build_cash_forecast(
        occurrences=pd.DataFrame(),
        period_start=date(2026, 1, 1),
        period_end=date(2026, 1, 3),
        opening_balance_kopecks=75_000,
    )

    assert result["date"].tolist() == [
        date(2026, 1, 1),
        date(2026, 1, 2),
        date(2026, 1, 3),
    ]

    assert result[
        "net_cash_flow_kopecks"
    ].tolist() == [
        0,
        0,
        0,
    ]

    assert result[
        "opening_balance_kopecks"
    ].tolist() == [
        75_000,
        75_000,
        75_000,
    ]

    assert result[
        "closing_balance_kopecks"
    ].tolist() == [
        75_000,
        75_000,
        75_000,
    ]