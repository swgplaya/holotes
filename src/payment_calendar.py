from __future__ import annotations

from calendar import monthrange
from datetime import date
from typing import Any

import pandas as pd
from sqlalchemy import select

from src.database import SessionLocal
from src.models import PlannedCashFlow


DIRECTION_LABELS = {
    "inflow": "Поступление",
    "outflow": "Платёж",
}

RECURRENCE_LABELS = {
    "once": "Однократно",
    "monthly": "Ежемесячно",
    "yearly": "Ежегодно",
}


def _optional_text(value: Any) -> str | None:
    """Возвращает очищенный текст или None."""

    if value is None or pd.isna(value):
        return None

    text = str(value).strip()

    return text or None


def create_planned_cash_flow(
    *,
    name: str,
    direction: str,
    amount_kopecks: int,
    category: str,
    counterparty: str,
    start_date: date,
    recurrence: str,
    end_date: date | None,
    is_active: bool,
    comment: str,
) -> int:
    """Создаёт плановое поступление или платёж."""

    clean_name = _optional_text(name)

    if clean_name is None:
        raise ValueError(
            "Укажи название плановой операции."
        )

    if direction not in DIRECTION_LABELS:
        raise ValueError(
            "Выбрано неизвестное направление операции."
        )

    if recurrence not in RECURRENCE_LABELS:
        raise ValueError(
            "Выбрана неизвестная периодичность."
        )

    if amount_kopecks <= 0:
        raise ValueError(
            "Сумма должна быть больше нуля."
        )

    if end_date is not None and end_date < start_date:
        raise ValueError(
            "Дата окончания не может быть раньше даты начала."
        )

    if recurrence == "once":
        end_date = None

    planned_cash_flow = PlannedCashFlow(
        name=clean_name,
        direction=direction,
        amount_kopecks=int(amount_kopecks),
        category=_optional_text(category),
        counterparty=_optional_text(counterparty),
        start_date=start_date,
        recurrence=recurrence,
        end_date=end_date,
        is_active=bool(is_active),
        comment=_optional_text(comment),
    )

    with SessionLocal() as session:
        session.add(planned_cash_flow)
        session.commit()
        session.refresh(planned_cash_flow)

        return planned_cash_flow.id


def get_planned_cash_flows_dataframe() -> pd.DataFrame:
    """Возвращает плановые операции как DataFrame."""

    columns = [
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

    statement = (
        select(PlannedCashFlow)
        .order_by(
            PlannedCashFlow.is_active.desc(),
            PlannedCashFlow.start_date.asc(),
            PlannedCashFlow.id.asc(),
        )
    )

    with SessionLocal() as session:
        plans = session.scalars(statement).all()

        rows = [
            {
                "id": plan.id,
                "name": plan.name,
                "direction": plan.direction,
                "amount_kopecks": plan.amount_kopecks,
                "category": plan.category,
                "counterparty": plan.counterparty,
                "start_date": plan.start_date,
                "recurrence": plan.recurrence,
                "end_date": plan.end_date,
                "is_active": plan.is_active,
                "comment": plan.comment,
            }
            for plan in plans
        ]

    return pd.DataFrame(rows, columns=columns)


def set_planned_cash_flow_active(
    plan_id: int,
    is_active: bool,
) -> None:
    """Включает или выключает плановую операцию."""

    with SessionLocal() as session:
        plan = session.get(
            PlannedCashFlow,
            int(plan_id),
        )

        if plan is None:
            raise ValueError(
                f"Плановая операция с ID {plan_id} не найдена."
            )

        plan.is_active = bool(is_active)
        session.commit()


def delete_planned_cash_flow(
    plan_id: int,
) -> None:
    """Удаляет плановую операцию."""

    with SessionLocal() as session:
        plan = session.get(
            PlannedCashFlow,
            int(plan_id),
        )

        if plan is None:
            raise ValueError(
                f"Плановая операция с ID {plan_id} не найдена."
            )

        session.delete(plan)
        session.commit()


def _next_month(
    current_date: date,
    anchor_day: int,
) -> date:
    """Возвращает следующую ежемесячную дату."""

    if current_date.month == 12:
        year = current_date.year + 1
        month = 1
    else:
        year = current_date.year
        month = current_date.month + 1

    last_day = monthrange(year, month)[1]
    day = min(anchor_day, last_day)

    return date(year, month, day)


def _next_year(
    current_date: date,
    anchor_month: int,
    anchor_day: int,
) -> date:
    """Возвращает следующую ежегодную дату."""

    year = current_date.year + 1
    last_day = monthrange(year, anchor_month)[1]
    day = min(anchor_day, last_day)

    return date(year, anchor_month, day)


def expand_planned_cash_flows(
    plans: pd.DataFrame,
    period_start: date,
    period_end: date,
) -> pd.DataFrame:
    """Разворачивает повторяющиеся планы в отдельные события."""

    if period_start > period_end:
        raise ValueError(
            "Начало прогноза не может быть позже окончания."
        )

    columns = [
        "plan_id",
        "date",
        "name",
        "direction",
        "signed_amount_kopecks",
        "category",
        "counterparty",
        "comment",
    ]

    if plans.empty:
        return pd.DataFrame(columns=columns)

    occurrences: list[dict[str, Any]] = []

    for _, plan in plans.iterrows():
        if not bool(plan["is_active"]):
            continue

        plan_start = pd.Timestamp(
            plan["start_date"]
        ).date()

        raw_end_date = plan["end_date"]

        if raw_end_date is None or pd.isna(raw_end_date):
            plan_end = period_end
        else:
            plan_end = min(
                pd.Timestamp(raw_end_date).date(),
                period_end,
            )

        if plan_start > plan_end:
            continue

        recurrence = str(plan["recurrence"])
        current_date = plan_start

        anchor_day = plan_start.day
        anchor_month = plan_start.month

        # Защита от повреждённых данных и бесконечного цикла.
        iterations = 0
        max_iterations = 10_000

        while current_date <= plan_end:
            iterations += 1

            if iterations > max_iterations:
                raise RuntimeError(
                    "Слишком много повторений плановой операции."
                )

            if current_date >= period_start:
                amount_kopecks = int(
                    plan["amount_kopecks"]
                )

                if plan["direction"] == "outflow":
                    signed_amount = -amount_kopecks
                else:
                    signed_amount = amount_kopecks

                occurrences.append(
                    {
                        "plan_id": int(plan["id"]),
                        "date": current_date,
                        "name": str(plan["name"]),
                        "direction": str(
                            plan["direction"]
                        ),
                        "signed_amount_kopecks":
                            signed_amount,
                        "category":
                            _optional_text(
                                plan["category"]
                            ),
                        "counterparty":
                            _optional_text(
                                plan["counterparty"]
                            ),
                        "comment":
                            _optional_text(
                                plan["comment"]
                            ),
                    }
                )

            if recurrence == "once":
                break

            if recurrence == "monthly":
                current_date = _next_month(
                    current_date=current_date,
                    anchor_day=anchor_day,
                )
                continue

            if recurrence == "yearly":
                current_date = _next_year(
                    current_date=current_date,
                    anchor_month=anchor_month,
                    anchor_day=anchor_day,
                )
                continue

            raise ValueError(
                f"Неизвестная периодичность: {recurrence}"
            )

    result = pd.DataFrame(
        occurrences,
        columns=columns,
    )

    if result.empty:
        return result

    return (
        result.sort_values(
            by=["date", "plan_id"],
            kind="stable",
        )
        .reset_index(drop=True)
    )


def build_cash_forecast(
    occurrences: pd.DataFrame,
    period_start: date,
    period_end: date,
    opening_balance_kopecks: int,
) -> pd.DataFrame:
    """Строит ежедневный прогноз остатка денежных средств."""

    dates = pd.date_range(
        start=period_start,
        end=period_end,
        freq="D",
    )

    forecast = pd.DataFrame(
        {
            "date": dates.date,
        }
    )

    if occurrences.empty:
        daily_amounts = pd.DataFrame(
            columns=[
                "date",
                "net_cash_flow_kopecks",
            ]
        )
    else:
        daily_amounts = (
            occurrences.groupby(
                "date",
                as_index=False,
            )["signed_amount_kopecks"]
            .sum()
            .rename(
                columns={
                    "signed_amount_kopecks":
                        "net_cash_flow_kopecks",
                }
            )
        )

    forecast = forecast.merge(
        daily_amounts,
        on="date",
        how="left",
    )

    forecast["net_cash_flow_kopecks"] = (
        pd.to_numeric(
            forecast["net_cash_flow_kopecks"],
            errors="coerce",
        )
        .fillna(0)
        .astype("int64")
    )

    forecast["planned_inflow_kopecks"] = (
        forecast["net_cash_flow_kopecks"]
        .clip(lower=0)
    )

    forecast["planned_outflow_kopecks"] = (
        -forecast["net_cash_flow_kopecks"]
        .clip(upper=0)
    )

    forecast["closing_balance_kopecks"] = (
        int(opening_balance_kopecks)
        + forecast[
            "net_cash_flow_kopecks"
        ].cumsum()
    )

    forecast["opening_balance_kopecks"] = (
        forecast["closing_balance_kopecks"]
        - forecast["net_cash_flow_kopecks"]
    )

    return forecast