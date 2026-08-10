from datetime import date

import pandas as pd
import pytest

from src.reporting import (
    build_cash_flow_report,
    build_category_comparison,
    build_pnl_report,
    filter_transactions_by_period,
    get_calendar_month_period,
    get_calendar_year_period,
    get_comparison_period,
    get_last_days_period,
    get_report_month_options,
    get_report_preset_period,
)


def make_transactions() -> pd.DataFrame:
    """Создаёт небольшой набор операций для тестов отчётности."""

    return pd.DataFrame(
        {
            "posted_at": [
                "2026-01-01",
                "2026-01-02",
                "2026-01-03",
                "2026-01-04",
                "2026-01-05",
            ],
            "signed_amount_kopecks": [
                100_000,
                -40_000,
                25_000,
                -15_000,
                5_000,
            ],
            "include_in_pnl": [
                True,
                True,
                True,
                False,
                None,
            ],
            "pnl_category": [
                "Продажи",
                "Маркетинг",
                "  ",
                "Прочее",
                "Прочее",
            ],
            "include_in_cf": [
                True,
                True,
                False,
                True,
                None,
            ],
            "cf_category": [
                "Операционная деятельность",
                "Операционная деятельность",
                "Инвестиционная деятельность",
                "",
                "Финансовая деятельность",
            ],
        }
    )


def test_get_calendar_month_period() -> None:
    assert get_calendar_month_period(
        2026,
        2,
    ) == (
        date(2026, 2, 1),
        date(2026, 2, 28),
    )


def test_get_calendar_month_period_handles_leap_year() -> None:
    assert get_calendar_month_period(
        2024,
        2,
    ) == (
        date(2024, 2, 1),
        date(2024, 2, 29),
    )


def test_get_calendar_year_period() -> None:
    assert get_calendar_year_period(
        2026
    ) == (
        date(2026, 1, 1),
        date(2026, 12, 31),
    )


def test_get_last_days_period_is_inclusive() -> None:
    assert get_last_days_period(
        end_date=date(2026, 8, 10),
        days=30,
    ) == (
        date(2026, 7, 12),
        date(2026, 8, 10),
    )


def test_get_last_days_period_rejects_non_positive_days() -> None:
    with pytest.raises(
        ValueError,
        match="Количество дней",
    ):
        get_last_days_period(
            end_date=date(2026, 8, 10),
            days=0,
        )


def test_report_month_options_include_current_month() -> None:
    result = get_report_month_options(
        min_date=date(2026, 5, 10),
        max_date=date(2026, 7, 31),
        today=date(2026, 8, 11),
    )

    assert result == [
        "2026-08",
        "2026-07",
        "2026-06",
        "2026-05",
    ]


def test_current_month_period_ends_today() -> None:
    result = get_report_preset_period(
        period_mode="month",
        selected_month="2026-08",
        selected_year=2026,
        min_date=date(2026, 1, 1),
        max_date=date(2026, 7, 31),
        today=date(2026, 8, 11),
    )

    assert result == (
        date(2026, 8, 1),
        date(2026, 8, 11),
    )


def test_previous_month_remains_full_calendar_month() -> None:
    result = get_report_preset_period(
        period_mode="month",
        selected_month="2026-07",
        selected_year=2026,
        min_date=date(2026, 1, 1),
        max_date=date(2026, 7, 31),
        today=date(2026, 8, 11),
    )

    assert result == (
        date(2026, 7, 1),
        date(2026, 7, 31),
    )


def test_current_year_period_ends_today() -> None:
    result = get_report_preset_period(
        period_mode="year",
        selected_month="2026-08",
        selected_year=2026,
        min_date=date(2025, 1, 1),
        max_date=date(2026, 7, 31),
        today=date(2026, 8, 11),
    )

    assert result == (
        date(2026, 1, 1),
        date(2026, 8, 11),
    )


def test_last_30_days_uses_today_not_last_transaction() -> None:
    result = get_report_preset_period(
        period_mode="last_30_days",
        selected_month="2026-08",
        selected_year=2026,
        min_date=date(2026, 1, 1),
        max_date=date(2026, 7, 31),
        today=date(2026, 8, 11),
    )

    assert result == (
        date(2026, 7, 13),
        date(2026, 8, 11),
    )


def test_all_time_uses_transaction_bounds() -> None:
    result = get_report_preset_period(
        period_mode="all_time",
        selected_month="2026-08",
        selected_year=2026,
        min_date=date(2025, 10, 15),
        max_date=date(2026, 7, 20),
        today=date(2026, 8, 11),
    )

    assert result == (
        date(2025, 10, 15),
        date(2026, 7, 20),
    )


def test_filter_transactions_by_period_is_inclusive() -> None:
    transactions = make_transactions()

    result = filter_transactions_by_period(
        transactions=transactions,
        start_date=date(2026, 1, 2),
        end_date=date(2026, 1, 4),
    )

    assert len(result) == 3

    assert result[
        "signed_amount_kopecks"
    ].tolist() == [
        -40_000,
        25_000,
        -15_000,
    ]


def test_filter_transactions_rejects_inverted_period() -> None:
    with pytest.raises(
        ValueError,
        match="Дата начала периода",
    ):
        filter_transactions_by_period(
            transactions=make_transactions(),
            start_date=date(2026, 1, 5),
            end_date=date(2026, 1, 1),
        )


def test_build_pnl_report_calculates_totals_and_counts() -> None:
    report = build_pnl_report(
        make_transactions()
    )

    assert report.inflow_kopecks == 125_000
    assert report.outflow_kopecks == 40_000
    assert report.net_kopecks == 85_000

    assert report.included_count == 3
    assert report.excluded_count == 1
    assert report.pending_count == 1

    totals = report.category_totals.set_index(
        "category"
    )["amount_kopecks"].to_dict()

    assert totals == {
        "Продажи": 100_000,
        "Маркетинг": -40_000,
        "Без категории": 25_000,
    }


def test_build_cash_flow_report_uses_cf_decisions() -> None:
    report = build_cash_flow_report(
        make_transactions()
    )

    assert report.inflow_kopecks == 100_000
    assert report.outflow_kopecks == 55_000
    assert report.net_kopecks == 45_000

    assert report.included_count == 3
    assert report.excluded_count == 1
    assert report.pending_count == 1

    totals = report.category_totals.set_index(
        "category"
    )["amount_kopecks"].to_dict()

    assert totals == {
        "Операционная деятельность": 60_000,
        "Без категории": -15_000,
    }


def test_build_report_rejects_missing_columns() -> None:
    transactions = pd.DataFrame(
        {
            "signed_amount_kopecks": [100],
        }
    )

    with pytest.raises(
        ValueError,
        match="Не хватает столбцов",
    ):
        build_pnl_report(transactions)


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        (
            "none",
            None,
        ),
        (
            "previous",
            (
                date(2026, 1, 7),
                date(2026, 1, 9),
            ),
        ),
        (
            "previous_year",
            (
                date(2025, 1, 10),
                date(2025, 1, 12),
            ),
        ),
    ],
)
def test_get_comparison_period(
    mode: str,
    expected: tuple[date, date] | None,
) -> None:
    result = get_comparison_period(
        start_date=date(2026, 1, 10),
        end_date=date(2026, 1, 12),
        mode=mode,
    )

    assert result == expected


def test_get_comparison_period_previous_month() -> None:
    result = get_comparison_period(
        start_date=date(2026, 3, 1),
        end_date=date(2026, 3, 31),
        mode="previous",
        period_mode="month",
    )

    assert result == (
        date(2026, 2, 1),
        date(2026, 2, 28),
    )


def test_get_comparison_period_previous_year_period() -> None:
    result = get_comparison_period(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        mode="previous",
        period_mode="year",
    )

    assert result == (
        date(2025, 1, 1),
        date(2025, 12, 31),
    )


def test_get_comparison_period_rejects_unknown_mode() -> None:
    with pytest.raises(
        ValueError,
        match="Неизвестный режим сравнения",
    ):
        get_comparison_period(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            mode="unexpected",
        )


def test_build_category_comparison_merges_categories() -> None:
    current = pd.DataFrame(
        {
            "signed_amount_kopecks": [
                100_000,
                -50_000,
            ],
            "include_in_pnl": [
                True,
                True,
            ],
            "pnl_category": [
                "A",
                "B",
            ],
        }
    )

    previous = pd.DataFrame(
        {
            "signed_amount_kopecks": [
                80_000,
                -40_000,
            ],
            "include_in_pnl": [
                True,
                True,
            ],
            "pnl_category": [
                "A",
                "C",
            ],
        }
    )

    comparison = build_category_comparison(
        current_report=build_pnl_report(current),
        comparison_report=build_pnl_report(previous),
    ).set_index("category")

    assert comparison.loc[
        "A",
        "delta_kopecks",
    ] == 20_000

    assert comparison.loc[
        "A",
        "change_percent",
    ] == pytest.approx(25.0)

    assert comparison.loc[
        "B",
        "current_amount_kopecks",
    ] == -50_000

    assert comparison.loc[
        "B",
        "comparison_amount_kopecks",
    ] == 0

    assert pd.isna(
        comparison.loc[
            "B",
            "change_percent",
        ]
    )

    assert comparison.loc[
        "C",
        "current_amount_kopecks",
    ] == 0

    assert comparison.loc[
        "C",
        "delta_kopecks",
    ] == 40_000

    assert comparison.loc[
        "C",
        "change_percent",
    ] == pytest.approx(100.0)