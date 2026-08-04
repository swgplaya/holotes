from collections.abc import Callable

import pandas as pd
import streamlit as st

from src.categories import (
    CF_CATEGORIES,
    EXCLUDE_ACTION,
    INCLUDE_ACTION,
    PNL_CATEGORIES,
    REPORT_ACTIONS,
    UNDEFINED_ACTION,
)
from src.classification_summary import (
    build_unclassified_summary,
)
from src.transaction_repository import (
    get_transactions_dataframe,
    save_classifications,
)


Translator = Callable[..., str]
MoneyFormatter = Callable[[int], str]


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


def render_classification_tab(
    *,
    t: Translator,
    format_rubles: MoneyFormatter,
) -> None:
    """Отображает вкладку ручной классификации."""

    st.subheader(
        t("classification.title")
    )

    classification_transactions = (
        get_transactions_dataframe()
    )

    classification_summary = (
        build_unclassified_summary(
            classification_transactions
        )
    )

    st.markdown(
        "#### "
        + t("classification.pending_title")
    )

    summary_columns = st.columns(4)

    summary_columns[0].metric(
        t("classification.metrics.inflow"),
        format_rubles(
            classification_summary.inflow_kopecks
        ),
    )

    summary_columns[1].metric(
        t("classification.metrics.outflow"),
        format_rubles(
            classification_summary.outflow_kopecks
        ),
    )

    summary_columns[2].metric(
        t("classification.metrics.net"),
        format_rubles(
            classification_summary.net_kopecks
        ),
    )

    summary_columns[3].metric(
        t("classification.metrics.count"),
        classification_summary.operation_count,
    )

    st.caption(
        t("classification.pending_caption")
    )

    if classification_summary.operation_count == 0:
        st.success(
            t("classification.all_classified")
        )

    if classification_transactions.empty:
        st.info(
            t("classification.empty_database")
        )
    else:
        only_pending = st.checkbox(
            t("classification.only_pending"),
            value=True,
        )

        if only_pending:
            classification_transactions = (
                classification_transactions.loc[
                    classification_transactions[
                        "classification_status"
                    ] != "classified"
                ].copy()
            )

        if classification_transactions.empty:
            st.success(
                t("classification.filtered_empty")
            )
        else:
            st.caption(
                t("classification.instructions")
            )

            selection_source = (
                prepare_classification_editor(
                    classification_transactions,
                    t=t,
                )
                .reset_index(drop=True)
            )

            st.markdown(
                "#### "
                + t("classification.select_title")
            )

            st.caption(
                t("classification.select_caption")
            )

            date_column = t(
                "classification.columns.date"
            )
            amount_column = t(
                "classification.columns.amount"
            )
            counterparty_column = t(
                "classification.columns.counterparty"
            )
            description_column = t(
                "classification.columns.description"
            )
            pnl_action_column = t(
                "classification.columns.pnl_action"
            )
            pnl_category_column = t(
                "classification.columns.pnl_category"
            )
            cf_action_column = t(
                "classification.columns.cf_action"
            )
            cf_category_column = t(
                "classification.columns.cf_category"
            )

            selection_columns = [
                "id",
                date_column,
                amount_column,
                counterparty_column,
                description_column,
                pnl_action_column,
                pnl_category_column,
                cf_action_column,
                cf_category_column,
            ]

            classification_ui_version = int(
                st.session_state.get(
                    "classification_ui_version",
                    0,
                )
            )

            selection_event = st.dataframe(
                selection_source[
                    selection_columns
                ],
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                key=(
                    "classification_selection_table_"
                    f"{classification_ui_version}"
                ),
                column_config={
                    "id":
                        st.column_config.NumberColumn(
                            t(
                                "classification.columns.id"
                            ),
                            format="%d",
                        ),
                    amount_column:
                        st.column_config.NumberColumn(
                            amount_column,
                            format="%.2f",
                        ),
                },
            )

            displayed_ids = (
                selection_source["id"]
                .astype(int)
                .tolist()
            )

            selected_rows = (
                selection_event.selection.rows
            )

            if selected_rows:
                selected_position = int(
                    selected_rows[0]
                )

                if (
                        0
                        <= selected_position
                        < len(selection_source)
                ):
                    selected_from_table = int(
                        selection_source.iloc[
                            selected_position
                        ]["id"]
                    )

                    st.session_state[
                        "classification_selected_id"
                    ] = selected_from_table

            selected_transaction_id = (
                st.session_state.get(
                    "classification_selected_id"
                )
            )

            if (
                    selected_transaction_id
                    not in displayed_ids
            ):
                selected_transaction_id = (
                    displayed_ids[0]
                )

                st.session_state[
                    "classification_selected_id"
                ] = selected_transaction_id

            selected_rows_in_database = (
                classification_transactions.loc[
                    pd.to_numeric(
                        classification_transactions[
                            "id"
                        ],
                        errors="coerce",
                    )
                    == selected_transaction_id
                    ]
            )

            if selected_rows_in_database.empty:
                st.error(
                    t(
                        "classification.errors."
                        "transaction_not_found"
                    )
                )
            else:
                selected_transaction = (
                    selected_rows_in_database.iloc[0]
                )

                selected_position = (
                    displayed_ids.index(
                        selected_transaction_id
                    )
                )

                st.divider()

                st.markdown(
                    "#### "
                    + t(
                        "classification.selected_title"
                    )
                )

                operation_header_columns = (
                    st.columns([1, 1, 2])
                )

                posted_at = pd.to_datetime(
                    selected_transaction[
                        "posted_at"
                    ],
                    errors="coerce",
                )

                if pd.isna(posted_at):
                    posted_at_text = "—"
                else:
                    posted_at_text = (
                        posted_at.strftime(
                            "%d.%m.%Y"
                        )
                    )

                operation_header_columns[0].metric(
                    t(
                        "classification.details.date"
                    ),
                    posted_at_text,
                )

                operation_header_columns[1].metric(
                    t(
                        "classification.details.amount"
                    ),
                    format_rubles(
                        int(
                            selected_transaction[
                                "signed_amount_kopecks"
                            ]
                        )
                    ),
                )

                operation_header_columns[2].metric(
                    t(
                        "classification.details.position"
                    ),
                    t(
                        "classification.details."
                        "position_value",
                        current=selected_position + 1,
                        total=len(displayed_ids),
                    ),
                )

                counterparty_text = _text_or_empty(
                    selected_transaction[
                        "counterparty_name"
                    ]
                )

                description_text = _text_or_empty(
                    selected_transaction[
                        "description"
                    ]
                )

                purpose_text = _text_or_empty(
                    selected_transaction[
                        "payment_purpose"
                    ]
                )

                not_specified_text = t(
                    "classification.details."
                    "not_specified"
                )

                st.write(
                    f"**{t(
                        'classification.details.'
                        'counterparty'
                    )}:** "
                    + (
                            counterparty_text
                            or not_specified_text
                    )
                )

                st.write(
                    f"**{t(
                        'classification.details.'
                        'description'
                    )}:** "
                    + (
                            description_text
                            or not_specified_text
                    )
                )

                with st.expander(
                        t(
                            "classification.details."
                            "payment_purpose"
                        ),
                        expanded=True,
                ):
                    st.write(
                        purpose_text
                        or not_specified_text
                    )
                    counterparty_label = t(
                        "classification.details."
                        "counterparty"
                    )

                    description_label = t(
                        "classification.details."
                        "description"
                    )

                    st.write(
                        f"**{counterparty_label}:** "
                        + (
                                counterparty_text
                                or not_specified_text
                        )
                    )

                    st.write(
                        f"**{description_label}:** "
                        + (
                                description_text
                                or not_specified_text
                        )
                    )

                current_pnl_action = (
                    bool_to_action(
                        selected_transaction[
                            "include_in_pnl"
                        ]
                    )
                )

                current_cf_action = (
                    bool_to_action(
                        selected_transaction[
                            "include_in_cf"
                        ]
                    )
                )

                current_pnl_category = (
                    _text_or_empty(
                        selected_transaction[
                            "pnl_category"
                        ]
                    )
                )

                current_cf_category = (
                    _text_or_empty(
                        selected_transaction[
                            "cf_category"
                        ]
                    )
                )

                current_comment = _text_or_empty(
                    selected_transaction[
                        "comment"
                    ]
                )

                pnl_action_options = list(
                    REPORT_ACTIONS
                )

                cf_action_options = list(
                    REPORT_ACTIONS
                )

                pnl_category_options = list(
                    dict.fromkeys(
                        [
                            "",
                            *list(PNL_CATEGORIES),
                            current_pnl_category,
                        ]
                    )
                )

                cf_category_options = list(
                    dict.fromkeys(
                        [
                            "",
                            *list(CF_CATEGORIES),
                            current_cf_category,
                        ]
                    )
                )

                form_key = (
                    "classification_form_"
                    f"{selected_transaction_id}_"
                    f"{classification_ui_version}"
                )

                with st.form(
                        form_key,
                        clear_on_submit=False,
                ):
                    pnl_column, cf_column = (
                        st.columns(2)
                    )

                    with pnl_column:
                        st.markdown(
                            "### "
                            + t("reports.pnl.title")
                        )

                        selected_pnl_action = (
                            st.selectbox(
                                t(
                                    "classification.columns."
                                    "pnl_action"
                                ),
                                options=(
                                    pnl_action_options
                                ),
                                format_func=lambda value: (
                                    format_report_action(
                                        value,
                                        t=t,
                                    )
                                ),
                                index=option_index(
                                    pnl_action_options,
                                    current_pnl_action,
                                ),
                                key=(
                                    "classification_pnl_action_"
                                    f"{selected_transaction_id}_"
                                    f"{classification_ui_version}"
                                ),
                            )
                        )

                        selected_pnl_category = (
                            st.selectbox(
                                t(
                                    "classification.columns."
                                    "pnl_category"
                                ),
                                options=(
                                    pnl_category_options
                                ),
                                index=option_index(
                                    pnl_category_options,
                                    current_pnl_category,
                                ),
                                key=(
                                    "classification_pnl_category_"
                                    f"{selected_transaction_id}_"
                                    f"{classification_ui_version}"
                                ),
                                help=t(
                                    "classification.help."
                                    "pnl_category"
                                ),
                            )
                        )

                    with cf_column:
                        st.markdown(
                            "### "
                            + t(
                                "reports.cash_flow.title"
                            )
                        )

                        selected_cf_action = (
                            st.selectbox(
                                t(
                                    "classification.columns."
                                    "cf_action"
                                ),
                                options=(
                                    cf_action_options
                                ),
                                format_func=lambda value: (
                                    format_report_action(
                                        value,
                                        t=t,
                                    )
                                ),
                                index=option_index(
                                    cf_action_options,
                                    current_cf_action,
                                ),
                                key=(
                                    "classification_cf_action_"
                                    f"{selected_transaction_id}_"
                                    f"{classification_ui_version}"
                                ),
                            )
                        )

                        selected_cf_category = (
                            st.selectbox(
                                t(
                                    "classification.columns."
                                    "cf_category"
                                ),
                                options=(
                                    cf_category_options
                                ),
                                index=option_index(
                                    cf_category_options,
                                    current_cf_category,
                                ),
                                key=(
                                    "classification_cf_category_"
                                    f"{selected_transaction_id}_"
                                    f"{classification_ui_version}"
                                ),
                                help=t(
                                    "classification.help."
                                    "cf_category"
                                ),
                            )
                        )

                    selected_comment = st.text_area(
                        t(
                            "classification.columns."
                            "comment"
                        ),
                        value=current_comment,
                        max_chars=500,
                        key=(
                            "classification_comment_"
                            f"{selected_transaction_id}_"
                            f"{classification_ui_version}"
                        ),
                    )

                    button_columns = st.columns(
                        [1, 1.3, 1.3]
                    )

                    with button_columns[0]:
                        save_current = (
                            st.form_submit_button(
                                t(
                                    "classification.buttons."
                                    "save"
                                ),
                                use_container_width=True,
                            )
                        )

                    with button_columns[1]:
                        save_and_next = (
                            st.form_submit_button(
                                t(
                                    "classification.buttons."
                                    "save_next"
                                ),
                            )
                        )

                    with button_columns[2]:
                        exclude_from_both = (
                            st.form_submit_button(
                                t(
                                    "classification.buttons."
                                    "exclude_both"
                                ),
                            )
                        )

                if (
                        save_current
                        or save_and_next
                        or exclude_from_both
                ):
                    if exclude_from_both:
                        final_pnl_action = (
                            EXCLUDE_ACTION
                        )

                        final_cf_action = (
                            EXCLUDE_ACTION
                        )

                        final_pnl_category = ""
                        final_cf_category = ""

                    else:
                        final_pnl_action = (
                            selected_pnl_action
                        )

                        final_cf_action = (
                            selected_cf_action
                        )

                        final_pnl_category = (
                            selected_pnl_category
                        )

                        final_cf_category = (
                            selected_cf_category
                        )

                        if (
                                final_pnl_action
                                != INCLUDE_ACTION
                        ):
                            final_pnl_category = ""

                        if (
                                final_cf_action
                                != INCLUDE_ACTION
                        ):
                            final_cf_category = ""

                    validation_errors = []

                    if (
                            final_pnl_action
                            == INCLUDE_ACTION
                            and not final_pnl_category
                    ):
                        validation_errors.append(
                            t(
                                "classification.errors."
                                "pnl_category_required"
                            )
                        )

                    if (
                            final_cf_action
                            == INCLUDE_ACTION
                            and not final_cf_category
                    ):
                        validation_errors.append(
                            t(
                                "classification.errors."
                                "cf_category_required"
                            )
                        )

                    if validation_errors:
                        for error_message in (
                                validation_errors
                        ):
                            st.error(error_message)

                    else:
                        classification_payload = (
                            pd.DataFrame(
                                [
                                    {
                                        "id":
                                            selected_transaction_id,
                                        "pnl_action":
                                            final_pnl_action,
                                        "pnl_category":
                                            final_pnl_category,
                                        "cf_action":
                                            final_cf_action,
                                        "cf_category":
                                            final_cf_category,
                                        "comment":
                                            selected_comment,
                                    }
                                ]
                            )
                        )

                        try:
                            save_result = (
                                save_classifications(
                                    classification_payload
                                )
                            )
                        except ValueError as exc:
                            st.error(str(exc))
                        else:
                            next_transaction_id = None

                            if save_and_next:
                                next_position = (
                                        selected_position + 1
                                )

                                if (
                                        next_position
                                        < len(displayed_ids)
                                ):
                                    next_transaction_id = (
                                        displayed_ids[
                                            next_position
                                        ]
                                    )

                            if (
                                    next_transaction_id
                                    is not None
                            ):
                                st.session_state[
                                    "classification_selected_id"
                                ] = (
                                    next_transaction_id
                                )

                            st.session_state[
                                "classification_ui_version"
                            ] = (
                                    classification_ui_version
                                    + 1
                            )

                            action_key = (
                                "classification.messages."
                                "excluded_both"
                                if exclude_from_both
                                else (
                                    "classification.messages."
                                    "saved"
                                )
                            )

                            st.session_state[
                                "classification_message"
                            ] = t(
                                "classification.messages."
                                "summary",
                                action=t(action_key),
                                updated=(
                                    save_result.updated
                                ),
                                classified=(
                                    save_result.classified
                                ),
                                partial=(
                                    save_result.partial
                                ),
                            )

                            st.rerun()
