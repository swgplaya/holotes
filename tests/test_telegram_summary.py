from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pandas as pd
import pytest

import src.telegram_summary as telegram_summary
from src.telegram_settings import (
    TelegramSettings,
)


def make_settings(
    *,
    include_cash_flow: bool = True,
    include_pnl: bool = True,
    include_pending_count: bool = True,
    include_payment_calendar: bool = True,
) -> TelegramSettings:
    return TelegramSettings(
        is_enabled=True,
        default_summary_period=(
            "current_month"
        ),
        include_cash_flow=(
            include_cash_flow
        ),
        include_pnl=include_pnl,
        include_pending_count=(
            include_pending_count
        ),
        include_payment_calendar=(
            include_payment_calendar
        ),
    )


@pytest.mark.parametrize(
    (
        "period",
        "expected_start",
        "expected_end",
    ),
    [
        (
            "current_month",
            date(2026, 8, 1),
            date(2026, 8, 6),
        ),
        (
            "previous_month",
            date(2026, 7, 1),
            date(2026, 7, 31),
        ),
        (
            "last_30_days",
            date(2026, 7, 8),
            date(2026, 8, 6),
        ),
        (
            "current_quarter",
            date(2026, 7, 1),
            date(2026, 8, 6),
        ),
        (
            "current_year",
            date(2026, 1, 1),
            date(2026, 8, 6),
        ),
    ],
)
def test_resolve_named_periods(
    period: str,
    expected_start: date,
    expected_end: date,
) -> None:
    resolved = (
        telegram_summary
        .resolve_summary_period(
            period,
            as_of=date(
                2026,
                8,
                6,
            ),
        )
    )

    assert (
        resolved.start_date
        == expected_start
    )

    assert (
        resolved.end_date
        == expected_end
    )


def test_resolve_explicit_leap_month() -> None:
    resolved = (
        telegram_summary
        .resolve_summary_period(
            "2024-02",
            as_of=date(
                2026,
                8,
                6,
            ),
        )
    )

    assert resolved.code == "2024-02"

    assert resolved.start_date == date(
        2024,
        2,
        1,
    )

    assert resolved.end_date == date(
        2024,
        2,
        29,
    )


@pytest.mark.parametrize(
    "period",
    [
        "",
        "unknown",
        "2026-00",
        "2026-13",
        "2026-7",
    ],
)
def test_reject_invalid_period(
    period: str,
) -> None:
    with pytest.raises(ValueError):
        (
            telegram_summary
            .resolve_summary_period(
                period,
                as_of=date(
                    2026,
                    8,
                    6,
                ),
            )
        )


def test_build_complete_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository_calls: list[
        dict[str, object]
    ] = []

    def fake_transactions(
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int | None = None,
        offset: int = 0,
        pending_only: bool = False,
    ) -> pd.DataFrame:
        del (
            limit,
            offset,
        )

        repository_calls.append(
            {
                "start_date": start_date,
                "end_date": end_date,
                "pending_only": (
                    pending_only
                ),
            }
        )

        if pending_only:
            return pd.DataFrame(
                {
                    "id": [
                        1,
                        2,
                    ],
                }
            )

        return pd.DataFrame(
            {
                "id": [
                    10,
                    20,
                ],
            }
        )

    monkeypatch.setattr(
        telegram_summary,
        "get_transactions_dataframe",
        fake_transactions,
    )

    monkeypatch.setattr(
        telegram_summary,
        "get_transaction_summary",
        lambda: SimpleNamespace(
            calculated_balance_kopecks=(
                2_345_678
            ),
        ),
    )

    monkeypatch.setattr(
        telegram_summary,
        "build_cash_flow_report",
        lambda transactions: (
            SimpleNamespace(
                inflow_kopecks=1_000_000,
                outflow_kopecks=400_000,
                net_kopecks=600_000,
                included_count=2,
                pending_count=1,
            )
        ),
    )

    monkeypatch.setattr(
        telegram_summary,
        "build_pnl_report",
        lambda transactions: (
            SimpleNamespace(
                inflow_kopecks=900_000,
                outflow_kopecks=300_000,
                net_kopecks=600_000,
                included_count=2,
                pending_count=1,
            )
        ),
    )

    monkeypatch.setattr(
        telegram_summary,
        "build_unclassified_summary",
        lambda transactions: (
            SimpleNamespace(
                operation_count=2,
                inflow_kopecks=300_000,
                outflow_kopecks=120_000,
                net_kopecks=180_000,
            )
        ),
    )

    monkeypatch.setattr(
        telegram_summary,
        "get_planned_cash_flows_dataframe",
        lambda: pd.DataFrame(
            {
                "id": [
                    1,
                ],
            }
        ),
    )

    monkeypatch.setattr(
        telegram_summary,
        "expand_planned_cash_flows",
        lambda **kwargs: pd.DataFrame(
            [
                {
                    "occurrence_date": (
                        date(
                            2026,
                            8,
                            9,
                        )
                    ),
                    "name": "Rent",
                    "signed_amount_kopecks": (
                        -500_000
                    ),
                },
                {
                    "occurrence_date": (
                        date(
                            2026,
                            8,
                            7,
                        )
                    ),
                    "name": "Customer",
                    "signed_amount_kopecks": (
                        800_000
                    ),
                },
                {
                    "occurrence_date": (
                        date(
                            2026,
                            8,
                            8,
                        )
                    ),
                    "name": "Tax",
                    "signed_amount_kopecks": (
                        -100_000
                    ),
                },
            ]
        ),
    )

    result = (
        telegram_summary
        .build_telegram_summary(
            period="2026-07",
            as_of=date(
                2026,
                8,
                6,
            ),
            settings=make_settings(),
            calendar_days=10,
            calendar_limit=2,
        )
    )

    assert result.period.start_date == date(
        2026,
        7,
        1,
    )

    assert result.period.end_date == date(
        2026,
        7,
        31,
    )

    assert (
        result.calculated_balance_kopecks
        == 2_345_678
    )

    assert result.cash_flow is not None

    assert (
        result.cash_flow.net_kopecks
        == 600_000
    )

    assert result.pnl is not None

    assert (
        result.pnl.inflow_kopecks
        == 900_000
    )

    assert (
        result.pending_classification
        == telegram_summary
        .PendingClassificationTotals(
            operation_count=2,
            inflow_kopecks=300_000,
            outflow_kopecks=120_000,
            net_kopecks=180_000,
        )
    )

    assert result.payment_calendar == (
        telegram_summary.PlannedOccurrence(
            occurrence_date=date(
                2026,
                8,
                7,
            ),
            name="Customer",
            signed_amount_kopecks=(
                800_000
            ),
        ),
        telegram_summary.PlannedOccurrence(
            occurrence_date=date(
                2026,
                8,
                8,
            ),
            name="Tax",
            signed_amount_kopecks=(
                -100_000
            ),
        ),
    )

    assert repository_calls == [
        {
            "start_date": date(
                2026,
                7,
                1,
            ),
            "end_date": date(
                2026,
                7,
                31,
            ),
            "pending_only": False,
        },
        {
            "start_date": date(
                2026,
                7,
                1,
            ),
            "end_date": date(
                2026,
                7,
                31,
            ),
            "pending_only": True,
        },
    ]


def test_calendar_only_avoids_period_transaction_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected_query(
        **kwargs: object,
    ) -> pd.DataFrame:
        del kwargs

        raise AssertionError(
            "Period transaction dataframe "
            "must not be queried."
        )

    monkeypatch.setattr(
        telegram_summary,
        "get_transactions_dataframe",
        unexpected_query,
    )

    monkeypatch.setattr(
        telegram_summary,
        "get_transaction_summary",
        lambda: SimpleNamespace(
            calculated_balance_kopecks=0,
        ),
    )

    monkeypatch.setattr(
        telegram_summary,
        "get_planned_cash_flows_dataframe",
        lambda: pd.DataFrame(),
    )

    result = (
        telegram_summary
        .build_telegram_summary(
            as_of=date(
                2026,
                8,
                6,
            ),
            settings=make_settings(
                include_cash_flow=False,
                include_pnl=False,
                include_pending_count=False,
                include_payment_calendar=True,
            ),
        )
    )

    assert result.cash_flow is None
    assert result.pnl is None
    assert (
        result.pending_classification
        is None
    )

    assert (
        result.payment_calendar
        == ()
    )


def test_format_russian_summary() -> None:
    summary = (
        telegram_summary
        .TelegramFinancialSummary(
            period=(
                telegram_summary
                .SummaryPeriod(
                    code="2026-07",
                    start_date=date(
                        2026,
                        7,
                        1,
                    ),
                    end_date=date(
                        2026,
                        7,
                        31,
                    ),
                )
            ),
            calculated_balance_kopecks=(
                2_345_678
            ),
            cash_flow=(
                telegram_summary
                .ReportTotals(
                    inflow_kopecks=(
                        12_345_678
                    ),
                    outflow_kopecks=(
                        8_000_000
                    ),
                    net_kopecks=(
                        4_345_678
                    ),
                    included_count=10,
                    pending_count=2,
                )
            ),
            pnl=(
                telegram_summary
                .ReportTotals(
                    inflow_kopecks=(
                        10_000_000
                    ),
                    outflow_kopecks=(
                        11_000_000
                    ),
                    net_kopecks=(
                        -1_000_000
                    ),
                    included_count=8,
                    pending_count=2,
                )
            ),
            pending_classification=(
                telegram_summary
                .PendingClassificationTotals(
                    operation_count=3,
                    inflow_kopecks=2_000_000,
                    outflow_kopecks=1_250_000,
                    net_kopecks=750_000,
                )
            ),
            payment_calendar=(
                telegram_summary
                .PlannedOccurrence(
                    occurrence_date=date(
                        2026,
                        8,
                        7,
                    ),
                    name="Аренда",
                    signed_amount_kopecks=(
                        -5_000_000
                    ),
                ),
            ),
            calendar_start_date=date(
                2026,
                8,
                6,
            ),
            calendar_end_date=date(
                2026,
                8,
                19,
            ),
        )
    )

    text = (
        telegram_summary
        .format_telegram_summary(
            summary,
            language="ru",
        )
    )

    assert (
        "01.07.2026 — 31.07.2026"
        in text
    )

    assert (
        "23 456,78 ₽"
        in text
    )

    assert (
        "💰 Расчётный остаток "
        "по загруженным операциям\n"
        "23 456,78 ₽"
        in text
    )

    assert (
        "Может отличаться от фактического "
        "остатка банка"
        not in text
    )

    assert (
        "123 456,78 ₽"
        in text
    )

    assert (
        "−10 000,00 ₽"
        in text
    )

    assert (
        "Неклассифицированные операции"
        in text
    )

    assert "Операций: 3" in text

    assert (
        "Поступления: 20 000,00 ₽"
        in text
    )

    assert (
        "Списания: 12 500,00 ₽"
        in text
    )

    assert (
        "Чистое движение: 7 500,00 ₽"
        in text
    )

    assert (
        "07.08 · Аренда: "
        "−50 000,00 ₽"
        in text
    )
