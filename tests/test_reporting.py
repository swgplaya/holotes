from datetime import date

import pandas as pd
import pytest

from src.reporting import (
    build_cash_flow_report,
    build_category_comparison,
    build_pnl_report,
    filter_transactions_by_period,
    get_comparison_period,
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