from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class UnclassifiedSummary:
    """Сводные показатели по неклассифицированным операциям."""

    inflow_kopecks: int
    outflow_kopecks: int
    net_kopecks: int
    operation_count: int


def _empty_series(
    dataframe: pd.DataFrame,
) -> pd.Series:
    """Создаёт пустую серию с индексом исходного DataFrame."""

    return pd.Series(
        data=None,
        index=dataframe.index,
        dtype="object",
    )


def _get_column(
    dataframe: pd.DataFrame,
    column_name: str,
) -> pd.Series:
    """Возвращает колонку или пустую серию."""

    if column_name in dataframe.columns:
        return dataframe[column_name]

    return _empty_series(dataframe)


def _is_blank(
    series: pd.Series,
) -> pd.Series:
    """Определяет пустые и незаполненные текстовые значения."""

    normalized = (
        series.astype("string")
        .str.strip()
    )

    return (
        series.isna()
        | normalized.eq("")
        | normalized.str.lower().eq("<na>")
    )


def _build_pending_mask(
    transactions: pd.DataFrame,
) -> pd.Series:
    """
    Определяет операции, требующие классификации.

    Операция считается незавершённой, когда:
    - решение о включении в P&L не принято;
    - P&L включён, но категория не указана;
    - решение о включении в Cash Flow не принято;
    - Cash Flow включён, но категория не указана.
    """

    include_in_pnl = _get_column(
        transactions,
        "include_in_pnl",
    )

    pnl_category = _get_column(
        transactions,
        "pnl_category",
    )

    include_in_cf = _get_column(
        transactions,
        "include_in_cf",
    )

    cf_category = _get_column(
        transactions,
        "cf_category",
    )

    pnl_pending = (
        include_in_pnl.isna()
        | (
            include_in_pnl.eq(True)
            & _is_blank(pnl_category)
        )
    )

    cf_pending = (
        include_in_cf.isna()
        | (
            include_in_cf.eq(True)
            & _is_blank(cf_category)
        )
    )

    return pnl_pending | cf_pending


def _get_signed_amounts(
    transactions: pd.DataFrame,
) -> pd.Series:
    """Возвращает суммы операций с учётом направления."""

    if "signed_amount_kopecks" in transactions.columns:
        return pd.to_numeric(
            transactions["signed_amount_kopecks"],
            errors="coerce",
        ).fillna(0)

    if "amount_kopecks" not in transactions.columns:
        return pd.Series(
            0,
            index=transactions.index,
            dtype="int64",
        )

    amounts = pd.to_numeric(
        transactions["amount_kopecks"],
        errors="coerce",
    ).fillna(0).abs()

    if "direction" not in transactions.columns:
        return amounts

    directions = (
        transactions["direction"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
    )

    expense_values = {
        "expense",
        "outflow",
        "debit",
        "списание",
        "расход",
    }

    signs = pd.Series(
        1,
        index=transactions.index,
        dtype="int64",
    )

    signs.loc[
        directions.isin(expense_values)
    ] = -1

    return amounts * signs


def build_unclassified_summary(
    transactions: pd.DataFrame,
) -> UnclassifiedSummary:
    """Рассчитывает суммы по незавершённой классификации."""

    if transactions.empty:
        return UnclassifiedSummary(
            inflow_kopecks=0,
            outflow_kopecks=0,
            net_kopecks=0,
            operation_count=0,
        )

    pending_mask = _build_pending_mask(
        transactions
    )

    pending_transactions = transactions.loc[
        pending_mask
    ].copy()

    if pending_transactions.empty:
        return UnclassifiedSummary(
            inflow_kopecks=0,
            outflow_kopecks=0,
            net_kopecks=0,
            operation_count=0,
        )

    signed_amounts = _get_signed_amounts(
        pending_transactions
    )

    inflow_kopecks = int(
        signed_amounts.loc[
            signed_amounts > 0
        ].sum()
    )

    # Списания показываем положительным объёмом.
    outflow_kopecks = int(
        -signed_amounts.loc[
            signed_amounts < 0
        ].sum()
    )

    net_kopecks = (
        inflow_kopecks
        - outflow_kopecks
    )

    return UnclassifiedSummary(
        inflow_kopecks=inflow_kopecks,
        outflow_kopecks=outflow_kopecks,
        net_kopecks=net_kopecks,
        operation_count=len(
            pending_transactions
        ),
    )