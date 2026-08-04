from collections.abc import Callable

import streamlit as st

from src.transaction_repository import (
    get_transactions_dataframe,
)
from src.ui.transaction_views import (
    prepare_visible_table,
    show_metrics,
)


Translator = Callable[..., str]
MoneyFormatter = Callable[[int], str]


def render_operations_tab(
    *,
    t: Translator,
    format_rubles: MoneyFormatter,
) -> None:
    """Отображает вкладку банковских операций."""

    stored_transactions = (
        get_transactions_dataframe()
    )

    if stored_transactions.empty:
        st.info(
            t("operations.empty_state")
        )
        return

    show_metrics(
        stored_transactions,
        t=t,
        format_rubles=format_rubles,
    )

    st.subheader(
        t("operations.saved_title")
    )

    operations_table = prepare_visible_table(
        stored_transactions,
        t=t,
    )

    amount_column = t(
        "operations.columns.amount"
    )

    st.dataframe(
        operations_table,
        use_container_width=True,
        hide_index=True,
        column_config={
            amount_column:
                st.column_config.NumberColumn(
                    amount_column,
                    format="%.2f",
                ),
        },
    )

    with st.expander(
        t("operations.technical_info")
    ):
        st.write(
            t("operations.sqlite_records"),
            len(stored_transactions),
        )

        st.code("data/finance.db")