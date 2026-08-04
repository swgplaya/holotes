import pandas as pd
import pytest

from src.classification_summary import (
    UnclassifiedSummary,
    build_unclassified_summary,
)


def test_empty_dataframe_returns_zero_summary() -> None:
    result = build_unclassified_summary(
        pd.DataFrame()
    )

    assert result == UnclassifiedSummary(
        inflow_kopecks=0,
        outflow_kopecks=0,
        net_kopecks=0,
        operation_count=0,
    )


def test_summary_counts_only_pending_transactions() -> None:
    transactions = pd.DataFrame(
        {
            "signed_amount_kopecks": [
                100_000,
                -40_000,
                25_000,
                -15_000,
                5_000,
            ],
            "include_in_pnl": [
                None,
                True,
                False,
                True,
                False,
            ],
            "pnl_category": [
                "Продажи",
                "   ",
                None,
                "Маркетинг",
                "",
            ],
            "include_in_cf": [
                False,
                False,
                True,
                True,
                False,
            ],
            "cf_category": [
                None,
                None,
                "Операционная деятельность",
                None,
                "",
            ],
        }
    )

    result = build_unclassified_summary(
        transactions
    )

    assert result == UnclassifiedSummary(
        inflow_kopecks=100_000,
        outflow_kopecks=55_000,
        net_kopecks=45_000,
        operation_count=3,
    )


def test_excluded_reports_do_not_require_categories() -> None:
    transactions = pd.DataFrame(
        {
            "signed_amount_kopecks": [
                10_000,
                -5_000,
            ],
            "include_in_pnl": [
                False,
                False,
            ],
            "pnl_category": [
                None,
                "",
            ],
            "include_in_cf": [
                False,
                False,
            ],
            "cf_category": [
                "   ",
                None,
            ],
        }
    )

    result = build_unclassified_summary(
        transactions
    )

    assert result.operation_count == 0
    assert result.inflow_kopecks == 0
    assert result.outflow_kopecks == 0
    assert result.net_kopecks == 0


@pytest.mark.parametrize(
    "missing_column",
    [
        "include_in_pnl",
        "include_in_cf",
    ],
)
def test_missing_decision_column_makes_transactions_pending(
    missing_column: str,
) -> None:
    transactions = pd.DataFrame(
        {
            "signed_amount_kopecks": [
                20_000,
                -7_000,
            ],
            "include_in_pnl": [
                False,
                False,
            ],
            "pnl_category": [
                None,
                None,
            ],
            "include_in_cf": [
                False,
                False,
            ],
            "cf_category": [
                None,
                None,
            ],
        }
    ).drop(
        columns=[missing_column]
    )

    result = build_unclassified_summary(
        transactions
    )

    assert result == UnclassifiedSummary(
        inflow_kopecks=20_000,
        outflow_kopecks=7_000,
        net_kopecks=13_000,
        operation_count=2,
    )


def test_amount_and_direction_are_used_when_signed_amount_is_missing(
) -> None:
    transactions = pd.DataFrame(
        {
            "amount_kopecks": [
                10_000,
                20_000,
                30_000,
                40_000,
            ],
            "direction": [
                "income",
                "expense",
                "списание",
                "unknown",
            ],
            "include_in_pnl": [
                None,
                None,
                None,
                None,
            ],
            "pnl_category": [
                None,
                None,
                None,
                None,
            ],
            "include_in_cf": [
                False,
                False,
                False,
                False,
            ],
            "cf_category": [
                None,
                None,
                None,
                None,
            ],
        }
    )

    result = build_unclassified_summary(
        transactions
    )

    assert result == UnclassifiedSummary(
        inflow_kopecks=50_000,
        outflow_kopecks=50_000,
        net_kopecks=0,
        operation_count=4,
    )


def test_invalid_amounts_are_treated_as_zero() -> None:
    transactions = pd.DataFrame(
        {
            "signed_amount_kopecks": [
                "not-a-number",
                None,
                12_500,
            ],
            "include_in_pnl": [
                None,
                None,
                None,
            ],
            "pnl_category": [
                None,
                None,
                None,
            ],
            "include_in_cf": [
                False,
                False,
                False,
            ],
            "cf_category": [
                None,
                None,
                None,
            ],
        }
    )

    result = build_unclassified_summary(
        transactions
    )

    assert result == UnclassifiedSummary(
        inflow_kopecks=12_500,
        outflow_kopecks=0,
        net_kopecks=12_500,
        operation_count=3,
    )


def test_missing_amount_columns_keep_pending_count() -> None:
    transactions = pd.DataFrame(
        {
            "include_in_pnl": [
                None,
                None,
            ],
            "pnl_category": [
                None,
                None,
            ],
            "include_in_cf": [
                False,
                False,
            ],
            "cf_category": [
                None,
                None,
            ],
        }
    )

    result = build_unclassified_summary(
        transactions
    )

    assert result == UnclassifiedSummary(
        inflow_kopecks=0,
        outflow_kopecks=0,
        net_kopecks=0,
        operation_count=2,
    )