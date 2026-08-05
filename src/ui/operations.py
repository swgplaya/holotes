from collections.abc import Callable
from math import ceil

import streamlit as st

from src.transaction_repository import (
    get_transactions_page,
)
from src.ui.transaction_views import (
    prepare_visible_table,
    show_summary_metrics,
)
from src.ui.data_cache import (
    cached_transaction_summary,
)


Translator = Callable[..., str]
MoneyFormatter = Callable[[int], str]


def render_operations_tab(
    *,
    t: Translator,
    format_rubles: MoneyFormatter,
) -> None:
    """Отображает вкладку банковских операций."""

    summary = cached_transaction_summary()

    if summary.count == 0:
        st.info(
            t("operations.empty_state")
        )
        return

    show_summary_metrics(
        count=summary.count,
        inflow_kopecks=(
            summary.inflow_kopecks
        ),
        outflow_kopecks=(
            summary.outflow_kopecks
        ),
        net_cash_flow_kopecks=(
            summary.net_kopecks
        ),
        t=t,
        format_rubles=format_rubles,
    )

    st.subheader(
        t("operations.saved_title")
    )

    page_key = "operations_page"
    page_size_key = (
        "operations_page_size"
    )

    def reset_page() -> None:
        """Возвращает пагинацию на первую страницу."""

        st.session_state[
            page_key
        ] = 1

    control_columns = st.columns(2)

    with control_columns[0]:
        page_size = int(
            st.selectbox(
                t(
                    "operations.pagination."
                    "page_size"
                ),
                options=(
                    25,
                    50,
                    100,
                    250,
                ),
                index=1,
                key=page_size_key,
                on_change=reset_page,
            )
        )

    total_pages = max(
        1,
        ceil(
            summary.count
            / page_size
        ),
    )

    current_page = int(
        st.session_state.get(
            page_key,
            1,
        )
    )

    clamped_page = min(
        max(
            current_page,
            1,
        ),
        total_pages,
    )

    if current_page != clamped_page:
        st.session_state[
            page_key
        ] = clamped_page

    with control_columns[1]:
        page = int(
            st.number_input(
                t(
                    "operations.pagination.page"
                ),
                min_value=1,
                max_value=total_pages,
                step=1,
                key=page_key,
            )
        )

    stored_transactions = (
        get_transactions_page(
            page=page,
            page_size=page_size,
        )
    )

    first_position = (
        page - 1
    ) * page_size + 1

    last_position = (
        first_position
        + len(stored_transactions)
        - 1
    )

    st.caption(
        t(
            "operations.pagination.position",
            page=page,
            pages=total_pages,
            start=first_position,
            end=last_position,
            total=summary.count,
        )
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
            summary.count,
        )

        st.code("data/finance.db")
