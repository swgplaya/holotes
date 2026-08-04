from collections.abc import Callable

import pandas as pd

from src.categories import (
    EXCLUDE_ACTION,
    INCLUDE_ACTION,
    UNDEFINED_ACTION,
)


Translator = Callable[..., str]


def _text_or_empty(value: object) -> str:
    """Преобразует пустое значение в пустую строку."""

    if value is None or pd.isna(value):
        return ""

    return str(value).strip()


def bool_to_action(value: object) -> str:
    """Преобразует значение базы в решение отчёта."""

    if value is None or pd.isna(value):
        return UNDEFINED_ACTION

    if bool(value):
        return INCLUDE_ACTION

    return EXCLUDE_ACTION


def format_report_action(
    value: object,
    *,
    t: Translator,
) -> str:
    """Возвращает локализованную подпись решения."""

    if value == INCLUDE_ACTION:
        return t(
            "classification.actions.include"
        )

    if value == EXCLUDE_ACTION:
        return t(
            "classification.actions.exclude"
        )

    if value == UNDEFINED_ACTION:
        return t(
            "classification.actions.undefined"
        )

    return str(value)


def option_index(
    options: list[str],
    current_value: object,
) -> int:
    """Находит безопасный индекс текущего значения."""

    current_text = _text_or_empty(
        current_value
    )

    try:
        return options.index(current_text)
    except ValueError:
        return 0


def prepare_classification_editor(
    transactions: pd.DataFrame,
    *,
    t: Translator,
) -> pd.DataFrame:
    """Подготавливает таблицу ручной классификации."""

    editor = transactions.copy()

    date_label = t(
        "classification.columns.date"
    )
    amount_label = t(
        "classification.columns.amount"
    )
    counterparty_label = t(
        "classification.columns.counterparty"
    )
    description_label = t(
        "classification.columns.description"
    )
    payment_purpose_label = t(
        "classification.columns.payment_purpose"
    )
    pnl_action_label = t(
        "classification.columns.pnl_action"
    )
    pnl_category_label = t(
        "classification.columns.pnl_category"
    )
    cf_action_label = t(
        "classification.columns.cf_action"
    )
    cf_category_label = t(
        "classification.columns.cf_category"
    )
    comment_label = t(
        "classification.columns.comment"
    )

    editor["posted_at"] = pd.to_datetime(
        editor["posted_at"]
    )

    editor[date_label] = editor[
        "posted_at"
    ].dt.strftime("%d.%m.%Y")

    editor[amount_label] = (
        editor["signed_amount_kopecks"] / 100
    )

    editor[counterparty_label] = (
        editor["counterparty_name"]
        .fillna("")
    )

    editor[description_label] = (
        editor["description"]
        .fillna("")
    )

    editor[payment_purpose_label] = (
        editor["payment_purpose"]
        .fillna("")
    )

    editor[pnl_action_label] = (
        editor["include_in_pnl"]
        .apply(bool_to_action)
        .apply(
            lambda value: format_report_action(
                value,
                t=t,
            )
        )
    )

    editor[pnl_category_label] = (
        editor["pnl_category"]
        .fillna("")
    )

    editor[cf_action_label] = (
        editor["include_in_cf"]
        .apply(bool_to_action)
        .apply(
            lambda value: format_report_action(
                value,
                t=t,
            )
        )
    )

    editor[cf_category_label] = (
        editor["cf_category"]
        .fillna("")
    )

    editor[comment_label] = (
        editor["comment"]
        .fillna("")
    )

    return editor[
        [
            "id",
            date_label,
            amount_label,
            counterparty_label,
            description_label,
            payment_purpose_label,
            pnl_action_label,
            pnl_category_label,
            cf_action_label,
            cf_category_label,
            comment_label,
        ]
    ]