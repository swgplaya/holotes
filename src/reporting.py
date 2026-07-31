from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd


@dataclass(frozen=True)
class ReportResult:
    """Результат построения финансового отчёта."""

    transactions: pd.DataFrame
    category_totals: pd.DataFrame
    inflow_kopecks: int
    outflow_kopecks: int
    net_kopecks: int
    included_count: int
    excluded_count: int
    pending_count: int


def filter_transactions_by_period(
    transactions: pd.DataFrame,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    """Фильтрует операции по дате проведения."""

    if start_date > end_date:
        raise ValueError(
            "Дата начала периода не может быть позже даты окончания."
        )

    if transactions.empty:
        return transactions.copy()

    result = transactions.copy()

    result["posted_at"] = pd.to_datetime(
        result["posted_at"],
        errors="coerce",
    )

    posted_dates = result["posted_at"].dt.date

    period_mask = (
        (posted_dates >= start_date)
        & (posted_dates <= end_date)
    )

    return result.loc[period_mask].copy()


def build_report(
    transactions: pd.DataFrame,
    include_column: str,
    category_column: str,
) -> ReportResult:
    """
    Строит агрегированный отчёт.

    include_column:
        include_in_pnl или include_in_cf.

    category_column:
        pnl_category или cf_category.
    """

    required_columns = {
        include_column,
        category_column,
        "signed_amount_kopecks",
    }

    missing_columns = (
        required_columns - set(transactions.columns)
    )

    if missing_columns:
        raise ValueError(
            "Не хватает столбцов для отчёта: "
            + ", ".join(sorted(missing_columns))
        )

    decisions = transactions[include_column]

    included_mask = decisions.eq(True).fillna(False)
    excluded_mask = decisions.eq(False).fillna(False)
    pending_mask = decisions.isna()

    included = transactions.loc[
        included_mask
    ].copy()

    included[category_column] = (
        included[category_column]
        .fillna("")
        .astype(str)
        .str.strip()
        .replace("", "Без категории")
    )

    category_totals = (
        included.groupby(
            category_column,
            as_index=False,
            dropna=False,
        )["signed_amount_kopecks"]
        .sum()
        .rename(
            columns={
                category_column: "category",
                "signed_amount_kopecks":
                    "amount_kopecks",
            }
        )
    )

    if not category_totals.empty:
        category_totals["absolute_amount"] = (
            category_totals["amount_kopecks"].abs()
        )

        category_totals = (
            category_totals.sort_values(
                by="absolute_amount",
                ascending=False,
            )
            .drop(columns="absolute_amount")
            .reset_index(drop=True)
        )

    inflow_kopecks = int(
        included.loc[
            included["signed_amount_kopecks"] > 0,
            "signed_amount_kopecks",
        ].sum()
    )

    outflow_kopecks = abs(
        int(
            included.loc[
                included["signed_amount_kopecks"] < 0,
                "signed_amount_kopecks",
            ].sum()
        )
    )

    net_kopecks = int(
        included["signed_amount_kopecks"].sum()
    )

    return ReportResult(
        transactions=included,
        category_totals=category_totals,
        inflow_kopecks=inflow_kopecks,
        outflow_kopecks=outflow_kopecks,
        net_kopecks=net_kopecks,
        included_count=int(included_mask.sum()),
        excluded_count=int(excluded_mask.sum()),
        pending_count=int(pending_mask.sum()),
    )


def build_pnl_report(
    transactions: pd.DataFrame,
) -> ReportResult:
    """Строит управленческий P&L."""

    return build_report(
        transactions=transactions,
        include_column="include_in_pnl",
        category_column="pnl_category",
    )


def build_cash_flow_report(
    transactions: pd.DataFrame,
) -> ReportResult:
    """Строит отчёт о движении денежных средств."""

    return build_report(
        transactions=transactions,
        include_column="include_in_cf",
        category_column="cf_category",
    )