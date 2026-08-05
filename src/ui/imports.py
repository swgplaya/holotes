from collections.abc import Callable
import hashlib
from io import BytesIO

import pandas as pd
import streamlit as st

from src.bank_import import (
    BankStatementError,
    read_tbank_csv,
)
from src.transaction_repository import (
    clear_bank_data,
    delete_import_batch,
    delete_untracked_transactions,
    get_import_batch_transactions_dataframe,
    get_import_batches_dataframe,
    get_untracked_transaction_count,
    save_transactions,
)
from src.ui.transaction_views import (
    prepare_visible_table,
    show_metrics,
)
from src.ui.data_cache import (
    cached_transaction_count,
)

Translator = Callable[..., str]
MoneyFormatter = Callable[[int], str]


def _text_or_empty(value: object) -> str:
    """Преобразует пустое значение базы в пустую строку."""

    if value is None or pd.isna(value):
        return ""

    return str(value).strip()


def render_import_tab(
    *,
    t: Translator,
    format_rubles: MoneyFormatter,
) -> None:
    """Отображает импорт и управление банковскими данными."""

    st.subheader(t("import.title"))

    uploaded_file = st.file_uploader(
        t("import.upload"),
        type=["csv"],
        help=t("import.upload_help"),
    )

    if uploaded_file is None:
        st.info(t("import.select_file"))
    else:
        uploaded_bytes = uploaded_file.getvalue()

        source_sha256 = hashlib.sha256(
            uploaded_bytes
        ).hexdigest()

        try:
            result = read_tbank_csv(
                BytesIO(uploaded_bytes)
            )
        except BankStatementError as exc:
            st.error(str(exc))
            st.stop()
        except Exception as exc:
            st.exception(exc)
            st.stop()

        imported_transactions = result.transactions

        file_info_columns = st.columns(3)

        file_info_columns[0].metric(
            t("import.file.name"),
            uploaded_file.name,
        )

        file_info_columns[1].metric(
            t("import.file.size"),
            t(
                "import.file.size_kb",
                size=len(uploaded_bytes) / 1024,
            ),
        )

        file_info_columns[2].metric(
            "SHA-256",
            source_sha256[:12] + "…",
            help=source_sha256,
        )

        for warning in result.warnings:
            st.warning(warning)

        show_metrics(
            imported_transactions,
            t=t,
            format_rubles=format_rubles,
        )

        st.subheader(t("import.preview"))

        st.dataframe(
            prepare_visible_table(
                imported_transactions,
                t=t,
            ),
            use_container_width=True,
            hide_index=True,
        )

        if st.button(
            t("import.save_button"),
            type="primary",
            use_container_width=True,
        ):
            try:
                save_result = save_transactions(
                    imported_transactions,
                    source_filename=uploaded_file.name,
                    source_size_bytes=len(
                        uploaded_bytes
                    ),
                    source_sha256=source_sha256,
                    warnings=result.warnings,
                )
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.session_state[
                    "last_import_message"
                ] = t(
                    "import.messages.saved",
                    batch_id=(
                        save_result.import_batch_id
                    ),
                    received=save_result.received,
                    inserted=save_result.inserted,
                    duplicates=save_result.duplicates,
                )

                st.rerun()

    st.divider()
    st.subheader(t("import.management.title"))

    import_batches = get_import_batches_dataframe()
    untracked_count = get_untracked_transaction_count()
    total_transaction_count = (
        cached_transaction_count()
    )

    management_metrics = st.columns(3)

    management_metrics[0].metric(
        t("import.management.logged_batches"),
        len(import_batches),
    )

    management_metrics[1].metric(
        t("import.management.untracked"),
        untracked_count,
    )

    management_metrics[2].metric(
        t("import.management.total"),
        total_transaction_count,
    )

    st.caption(t("import.management.caption"))

    if import_batches.empty:
        st.info(t("import.history.empty"))
    else:
        st.markdown(
            "#### " + t("import.history.title")
        )

        import_history = import_batches.copy()

        id_column = t("common.id")
        file_column = t("import.history.file")
        imported_column = t(
            "import.history.imported_at"
        )
        size_column = t("import.history.size_kb")
        received_column = t(
            "import.history.received"
        )
        inserted_column = t(
            "import.history.inserted"
        )
        duplicates_column = t(
            "import.history.duplicates"
        )
        linked_column = t("import.history.linked")

        import_history[imported_column] = (
            pd.to_datetime(
                import_history["imported_at"],
                errors="coerce",
            ).dt.strftime("%d.%m.%Y %H:%M")
        )

        import_history[size_column] = (
            pd.to_numeric(
                import_history["source_size_bytes"],
                errors="coerce",
            ) / 1024
        )

        import_history = import_history.rename(
            columns={
                "id": id_column,
                "source_filename": file_column,
                "received_count": received_column,
                "inserted_count": inserted_column,
                "duplicate_count": duplicates_column,
                "linked_transaction_count":
                    linked_column,
            }
        )

        history_columns = [
            id_column,
            file_column,
            imported_column,
            size_column,
            received_column,
            inserted_column,
            duplicates_column,
            linked_column,
        ]

        st.dataframe(
            import_history[history_columns],
            use_container_width=True,
            hide_index=True,
            column_config={
                id_column:
                    st.column_config.NumberColumn(
                        id_column,
                        format="%d",
                    ),
                size_column:
                    st.column_config.NumberColumn(
                        size_column,
                        format="%.1f",
                    ),
            },
        )

        batch_ids = (
            import_batches["id"]
            .astype(int)
            .tolist()
        )

        batch_labels: dict[int, str] = {}

        for _, batch_row in (
            import_batches.iterrows()
        ):
            batch_id = int(batch_row["id"])

            imported_at = pd.to_datetime(
                batch_row["imported_at"],
                errors="coerce",
            )

            if pd.isna(imported_at):
                imported_at_text = t(
                    "common.unknown_date"
                )
            else:
                imported_at_text = (
                    imported_at.strftime(
                        "%d.%m.%Y %H:%M"
                    )
                )

            batch_labels[batch_id] = (
                f"#{batch_id} — "
                f"{batch_row['source_filename']} — "
                f"{imported_at_text}"
            )

        selected_batch_id = st.selectbox(
            t("import.history.select"),
            options=batch_ids,
            format_func=lambda value: (
                batch_labels[int(value)]
            ),
            key="selected_import_batch_id",
        )

        selected_batch = import_batches.loc[
            import_batches["id"].astype(int)
            == int(selected_batch_id)
        ].iloc[0]

        selected_warnings = _text_or_empty(
            selected_batch["warnings"]
        )

        if selected_warnings:
            st.warning(selected_warnings)

        selected_transactions = (
            get_import_batch_transactions_dataframe(
                int(selected_batch_id)
            )
        )

        st.markdown(
            "#### "
            + t("import.history.operations_title")
        )

        if selected_transactions.empty:
            st.info(
                t("import.history.operations_empty")
            )
        else:
            transaction_view = (
                selected_transactions.copy()
            )

            date_column = t(
                "operations.columns.date"
            )
            amount_column = t(
                "operations.columns.amount"
            )
            counterparty_column = t(
                "operations.columns.counterparty"
            )
            description_column = t(
                "operations.columns.description"
            )
            purpose_column = t(
                "operations.columns.payment_purpose"
            )
            classification_column = t(
                "operations.columns.classification"
            )

            transaction_view[date_column] = (
                pd.to_datetime(
                    transaction_view["posted_at"],
                    errors="coerce",
                ).dt.strftime("%d.%m.%Y")
            )

            transaction_view[amount_column] = (
                pd.to_numeric(
                    transaction_view[
                        "signed_amount_kopecks"
                    ],
                    errors="coerce",
                ) / 100
            )

            transaction_view = (
                transaction_view.rename(
                    columns={
                        "id": id_column,
                        "counterparty_name":
                            counterparty_column,
                        "description":
                            description_column,
                        "payment_purpose":
                            purpose_column,
                        "classification_status":
                            classification_column,
                    }
                )
            )

            transaction_columns = [
                id_column,
                date_column,
                amount_column,
                counterparty_column,
                description_column,
                purpose_column,
                classification_column,
            ]

            st.dataframe(
                transaction_view[
                    transaction_columns
                ],
                use_container_width=True,
                hide_index=True,
                column_config={
                    id_column:
                        st.column_config.NumberColumn(
                            id_column,
                            format="%d",
                        ),
                    amount_column:
                        st.column_config.NumberColumn(
                            amount_column,
                            format="%.2f",
                        ),
                },
            )

        st.markdown(
            "#### "
            + t("import.history.delete_title")
        )

        st.caption(
            t("import.history.delete_caption")
        )

        delete_batch_phrase = t(
            "import.history.delete_phrase",
            batch_id=selected_batch_id,
        )

        delete_batch_confirmation = st.text_input(
            t("import.history.delete_confirmation"),
            placeholder=delete_batch_phrase,
            key=(
                "delete_import_batch_confirmation_"
                f"{selected_batch_id}"
            ),
        )

        if st.button(
            t("import.history.delete_button"),
            disabled=(
                delete_batch_confirmation.strip()
                != delete_batch_phrase
            ),
            key=(
                "delete_import_batch_button_"
                f"{selected_batch_id}"
            ),
            use_container_width=True,
        ):
            try:
                delete_result = delete_import_batch(
                    int(selected_batch_id)
                )
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.session_state[
                    "last_import_message"
                ] = t(
                    "import.messages.batch_deleted",
                    batch_id=(
                        delete_result.import_batch_id
                    ),
                    links=delete_result.links_deleted,
                    transactions=(
                        delete_result.transactions_deleted
                    ),
                )

                st.rerun()

    if untracked_count > 0:
        st.divider()
        st.markdown(
            "#### " + t("import.untracked.title")
        )

        st.warning(
            t(
                "import.untracked.warning",
                count=untracked_count,
            )
        )

        delete_untracked_phrase = t(
            "import.untracked.phrase"
        )

        delete_untracked_confirmation = (
            st.text_input(
                t("import.untracked.confirmation"),
                placeholder=delete_untracked_phrase,
                key="delete_untracked_confirmation",
            )
        )

        if st.button(
            t("import.untracked.delete_button"),
            disabled=(
                delete_untracked_confirmation.strip()
                != delete_untracked_phrase
            ),
            key="delete_untracked_button",
            use_container_width=True,
        ):
            deleted_count = (
                delete_untracked_transactions()
            )

            st.session_state[
                "last_import_message"
            ] = t(
                "import.messages.untracked_deleted",
                count=deleted_count,
            )

            st.rerun()

    st.divider()

    with st.expander(
        t("import.danger.title"),
        expanded=False,
    ):
        st.warning(t("import.danger.warning"))

        clear_phrase = t("import.danger.phrase")

        clear_confirmation = st.text_input(
            t("import.danger.confirmation"),
            placeholder=clear_phrase,
            key="clear_bank_data_confirmation",
        )

        if st.button(
            t("import.danger.clear_button"),
            disabled=(
                clear_confirmation.strip()
                != clear_phrase
            ),
            key="clear_bank_data_button",
            use_container_width=True,
        ):
            clear_result = clear_bank_data()

            st.session_state[
                "last_import_message"
            ] = t(
                "import.messages.cleared",
                batches=(
                    clear_result.import_batches_deleted
                ),
                links=clear_result.links_deleted,
                transactions=(
                    clear_result.transactions_deleted
                ),
            )

            st.rerun()
