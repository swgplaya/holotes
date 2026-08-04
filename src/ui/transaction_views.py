from collections.abc import Callable

import pandas as pd
import streamlit as st



Translator = Callable[..., str]
MoneyFormatter = Callable[[int], str]


def prepare_visible_table(
    transactions: pd.DataFrame,
    *,
    t: Translator,
) -> pd.DataFrame:
    """Подготавливает банковские операции для отображения."""

    preview = transactions.copy()

    date_label = t(
        "operations.columns.date"
    )
    amount_label = t(
        "operations.columns.amount"
    )
    direction_label = t(
        "operations.columns.direction"
    )
    bank_category_label = t(
        "operations.columns.bank_category"
    )
    status_label = t(
        "operations.columns.status"
    )
    counterparty_label = t(
        "operations.columns.counterparty"
    )
    tax_id_label = t(
        "operations.columns.tax_id"
    )
    description_label = t(
        "operations.columns.description"
    )
    payment_purpose_label = t(
        "operations.columns.payment_purpose"
    )
    classification_label = t(
        "operations.columns.classification"
    )

    preview["posted_at"] = pd.to_datetime(
        preview["posted_at"]
    )

    preview[date_label] = preview[
        "posted_at"
    ].dt.strftime("%d.%m.%Y")

    preview[amount_label] = (
        preview["signed_amount_kopecks"] / 100
    )

    preview = preview.rename(
        columns={
            "direction": direction_label,
            "bank_category":
                bank_category_label,
            "status": status_label,
            "counterparty_name":
                counterparty_label,
            "counterparty_inn": tax_id_label,
            "description": description_label,
            "payment_purpose":
                payment_purpose_label,
            "classification_status":
                classification_label,
        }
    )

    visible_columns = [
        date_label,
        amount_label,
        direction_label,
        bank_category_label,
        status_label,
        counterparty_label,
        tax_id_label,
        description_label,
        payment_purpose_label,
    ]

    if classification_label in preview.columns:
        visible_columns.append(
            classification_label
        )

    return preview[visible_columns]


def show_metrics(
    transactions: pd.DataFrame,
    *,
    t: Translator,
    format_rubles: MoneyFormatter,
) -> None:
    """Показывает основные показатели банковских операций."""

    inflow_kopecks = int(
        transactions.loc[
            transactions["signed_amount_kopecks"] > 0,
            "signed_amount_kopecks",
        ].sum()
    )

    outflow_kopecks = abs(
        int(
            transactions.loc[
                transactions[
                    "signed_amount_kopecks"
                ] < 0,
                "signed_amount_kopecks",
            ].sum()
        )
    )

    net_cash_flow_kopecks = int(
        transactions[
            "signed_amount_kopecks"
        ].sum()
    )

    metric_columns = st.columns(4)

    metric_columns[0].metric(
        t("operations.metrics.count"),
        f"{len(transactions)}",
    )

    metric_columns[1].metric(
        t("operations.metrics.inflow"),
        format_rubles(inflow_kopecks),
    )

    metric_columns[2].metric(
        t("operations.metrics.outflow"),
        format_rubles(outflow_kopecks),
    )

    metric_columns[3].metric(
        t("operations.metrics.net"),
        format_rubles(
            net_cash_flow_kopecks
        ),
    )