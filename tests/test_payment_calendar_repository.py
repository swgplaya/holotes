from datetime import date

import pandas as pd
import pytest
from sqlalchemy.orm import sessionmaker

import src.payment_calendar as payment_calendar


@pytest.fixture
def isolated_repository(
    monkeypatch: pytest.MonkeyPatch,
    sqlite_session_factory: sessionmaker,
) -> sessionmaker:
    """Переключает платёжный календарь на временную базу."""

    monkeypatch.setattr(
        payment_calendar,
        "SessionLocal",
        sqlite_session_factory,
    )

    return sqlite_session_factory


def create_plan(
    **overrides: object,
) -> int:
    """Создаёт плановую операцию с базовыми значениями."""

    values: dict[str, object] = {
        "name": "Аренда",
        "direction": "outflow",
        "amount_kopecks": 100_000,
        "category": "Операционные расходы",
        "counterparty": "Арендодатель",
        "start_date": date(2026, 1, 15),
        "recurrence": "monthly",
        "end_date": date(2026, 12, 15),
        "is_active": True,
        "comment": "Основной офис",
    }

    values.update(overrides)

    return payment_calendar.create_planned_cash_flow(
        **values,  # type: ignore[arg-type]
    )


def test_create_plan_cleans_text_and_once_clears_end_date(
    isolated_repository: sessionmaker,
) -> None:
    del isolated_repository

    plan_id = create_plan(
        name="  Разовый платёж  ",
        direction="inflow",
        amount_kopecks=25_000,
        category="  Продажи  ",
        counterparty="  Клиент  ",
        start_date=date(2026, 2, 10),
        recurrence="once",
        end_date=date(2026, 12, 31),
        comment="  Аванс  ",
    )

    plans = (
        payment_calendar
        .get_planned_cash_flows_dataframe()
        .set_index("id")
    )

    row = plans.loc[plan_id]

    assert row["name"] == "Разовый платёж"
    assert row["direction"] == "inflow"
    assert row["amount_kopecks"] == 25_000
    assert row["category"] == "Продажи"
    assert row["counterparty"] == "Клиент"
    assert row["start_date"] == date(2026, 2, 10)
    assert row["recurrence"] == "once"
    assert pd.isna(row["end_date"])
    assert row["comment"] == "Аванс"


def test_get_plans_orders_active_first_then_by_date(
    isolated_repository: sessionmaker,
) -> None:
    del isolated_repository

    create_plan(
        name="Активный поздний",
        start_date=date(2026, 3, 1),
    )

    create_plan(
        name="Неактивный ранний",
        start_date=date(2026, 1, 1),
        is_active=False,
    )

    create_plan(
        name="Активный ранний",
        start_date=date(2026, 2, 1),
    )

    plans = (
        payment_calendar
        .get_planned_cash_flows_dataframe()
    )

    assert plans["name"].tolist() == [
        "Активный ранний",
        "Активный поздний",
        "Неактивный ранний",
    ]

    assert plans["is_active"].tolist() == [
        True,
        True,
        False,
    ]


@pytest.mark.parametrize(
    (
        "overrides",
        "message",
    ),
    [
        (
            {"name": "   "},
            "Укажи название",
        ),
        (
            {"direction": "unexpected"},
            "неизвестное направление",
        ),
        (
            {"recurrence": "weekly"},
            "неизвестная периодичность",
        ),
        (
            {"amount_kopecks": 0},
            "Сумма должна быть больше нуля",
        ),
        (
            {
                "start_date": date(2026, 2, 1),
                "end_date": date(2026, 1, 31),
            },
            "Дата окончания не может быть раньше",
        ),
    ],
)
def test_create_plan_rejects_invalid_values(
    isolated_repository: sessionmaker,
    overrides: dict[str, object],
    message: str,
) -> None:
    del isolated_repository

    with pytest.raises(
        ValueError,
        match=message,
    ):
        create_plan(**overrides)

    assert (
        payment_calendar
        .get_planned_cash_flows_dataframe()
        .empty
    )


def test_set_active_updates_plan(
    isolated_repository: sessionmaker,
) -> None:
    del isolated_repository

    plan_id = create_plan()

    payment_calendar.set_planned_cash_flow_active(
        plan_id,
        False,
    )

    row = (
        payment_calendar
        .get_planned_cash_flows_dataframe()
        .set_index("id")
        .loc[plan_id]
    )

    assert bool(row["is_active"]) is False


@pytest.mark.parametrize(
    "operation",
    [
        "set_active",
        "delete",
    ],
)
def test_missing_plan_raises_error(
    isolated_repository: sessionmaker,
    operation: str,
) -> None:
    del isolated_repository

    with pytest.raises(
        ValueError,
        match="ID 999.*не найдена",
    ):
        if operation == "set_active":
            payment_calendar.set_planned_cash_flow_active(
                999,
                False,
            )
        else:
            payment_calendar.delete_planned_cash_flow(
                999
            )


def test_delete_plan_removes_only_selected_row(
    isolated_repository: sessionmaker,
) -> None:
    del isolated_repository

    first_id = create_plan(
        name="Первый план",
    )

    second_id = create_plan(
        name="Второй план",
        start_date=date(2026, 2, 15),
    )

    payment_calendar.delete_planned_cash_flow(
        first_id
    )

    plans = (
        payment_calendar
        .get_planned_cash_flows_dataframe()
    )

    assert plans["id"].tolist() == [
        second_id,
    ]

    assert plans["name"].tolist() == [
        "Второй план",
    ]