from decimal import Decimal

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

from src.bank_import import (
    BankStatementError,
    read_tbank_csv,
)
from src.database import init_db
from src.transaction_repository import (
    get_transactions_dataframe,
    save_classifications,
    save_transactions,
)



st.set_page_config(
    page_title="Open MAS",
    page_icon="📊",
    layout="wide",
)

init_db()


def format_rubles(kopecks: int) -> str:
    """Форматирует копейки в российский денежный формат."""

    amount = Decimal(int(kopecks)) / Decimal("100")
    formatted = f"{amount:,.2f}"

    formatted = (
        formatted
        .replace(",", " ")
        .replace(".", ",")
    )

    return f"{formatted} ₽"

def bool_to_action(value: object) -> str:
    """Преобразует значение из базы в подпись интерфейса."""

    if value is True:
        return INCLUDE_ACTION

    if value is False:
        return EXCLUDE_ACTION

    return UNDEFINED_ACTION


def prepare_classification_editor(
    transactions: pd.DataFrame,
) -> pd.DataFrame:
    """Подготавливает таблицу ручной классификации."""

    editor = transactions.copy()

    editor["posted_at"] = pd.to_datetime(
        editor["posted_at"]
    )

    editor["Дата"] = editor[
        "posted_at"
    ].dt.strftime("%d.%m.%Y")

    editor["Сумма, ₽"] = (
        editor["signed_amount_kopecks"] / 100
    )

    editor["Контрагент"] = (
        editor["counterparty_name"]
        .fillna("")
    )

    editor["Описание"] = (
        editor["description"]
        .fillna("")
    )

    editor["Назначение платежа"] = (
        editor["payment_purpose"]
        .fillna("")
    )

    editor["Решение P&L"] = (
        editor["include_in_pnl"]
        .apply(bool_to_action)
    )

    editor["Категория P&L"] = (
        editor["pnl_category"]
        .fillna("")
    )

    editor["Решение Cash Flow"] = (
        editor["include_in_cf"]
        .apply(bool_to_action)
    )

    editor["Категория Cash Flow"] = (
        editor["cf_category"]
        .fillna("")
    )

    editor["Комментарий"] = (
        editor["comment"]
        .fillna("")
    )

    return editor[
        [
            "id",
            "Дата",
            "Сумма, ₽",
            "Контрагент",
            "Описание",
            "Назначение платежа",
            "Решение P&L",
            "Категория P&L",
            "Решение Cash Flow",
            "Категория Cash Flow",
            "Комментарий",
        ]
    ]


def prepare_visible_table(
    transactions: pd.DataFrame,
) -> pd.DataFrame:
    """Подготавливает операции для отображения."""

    preview = transactions.copy()

    preview["posted_at"] = pd.to_datetime(
        preview["posted_at"]
    )

    preview["Дата"] = preview[
        "posted_at"
    ].dt.strftime("%d.%m.%Y")

    preview["Сумма, ₽"] = (
        preview["signed_amount_kopecks"] / 100
    )

    preview = preview.rename(
        columns={
            "direction": "Дебет/кредит",
            "bank_category": "Категория банка",
            "status": "Статус",
            "counterparty_name": "Контрагент",
            "counterparty_inn": "ИНН",
            "description": "Описание",
            "payment_purpose": "Назначение платежа",
            "classification_status": "Классификация",
        }
    )

    visible_columns = [
        "Дата",
        "Сумма, ₽",
        "Дебет/кредит",
        "Категория банка",
        "Статус",
        "Контрагент",
        "ИНН",
        "Описание",
        "Назначение платежа",
    ]

    if "Классификация" in preview.columns:
        visible_columns.append("Классификация")

    return preview[visible_columns]


def show_metrics(transactions: pd.DataFrame) -> None:
    """Показывает основные денежные показатели."""

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
        transactions["signed_amount_kopecks"].sum()
    )

    metric_columns = st.columns(4)

    metric_columns[0].metric(
        "Операций",
        f"{len(transactions)}",
    )
    metric_columns[1].metric(
        "Поступления",
        format_rubles(inflow_kopecks),
    )
    metric_columns[2].metric(
        "Списания",
        format_rubles(outflow_kopecks),
    )
    metric_columns[3].metric(
        "Чистое движение",
        format_rubles(net_cash_flow_kopecks),
    )


st.title("Open MAS")
st.caption("Система управленческого финансового учёта")

last_import_message = st.session_state.pop(
    "last_import_message",
    None,
)

if last_import_message:
    st.success(last_import_message)

operations_tab, classification_tab, import_tab = st.tabs(
    [
        "Операции в базе",
        "Классификация",
        "Импорт выписки",
    ]
)

classification_message = st.session_state.pop(
    "classification_message",
    None,
)

if classification_message:
    st.success(classification_message)


with operations_tab:
    stored_transactions = get_transactions_dataframe()

    if stored_transactions.empty:
        st.info(
            "В базе пока нет операций. "
            "Загрузите первую выписку во вкладке импорта."
        )
    else:
        show_metrics(stored_transactions)

        st.subheader("Сохранённые операции")

        st.dataframe(
            prepare_visible_table(stored_transactions),
            use_container_width=True,
            hide_index=True,
        )

        with st.expander("Техническая информация"):
            st.write(
                "Записей в SQLite:",
                len(stored_transactions),
            )
            st.code("data/finance.db")

with classification_tab:
    st.subheader("Классификация операций")

    classification_transactions = (
        get_transactions_dataframe()
    )

    if classification_transactions.empty:
        st.info(
            "В базе пока нет операций для классификации."
        )
    else:
        only_pending = st.checkbox(
            "Показывать только незавершённые",
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
                "Все операции полностью классифицированы."
            )
        else:
            st.caption(
                "Для каждого отчёта выбери отдельное решение. "
                "Операцию можно включить в Cash Flow, "
                "но исключить из P&L, и наоборот."
            )

            editor_source = prepare_classification_editor(
                classification_transactions
            )

            edited_classifications = st.data_editor(
                editor_source,
                use_container_width=True,
                hide_index=True,
                disabled=[
                    "id",
                    "Дата",
                    "Сумма, ₽",
                    "Контрагент",
                    "Описание",
                    "Назначение платежа",
                ],
                column_config={
                    "id": st.column_config.NumberColumn(
                        "ID",
                        format="%d",
                    ),
                    "Сумма, ₽":
                        st.column_config.NumberColumn(
                            "Сумма, ₽",
                            format="%.2f",
                        ),
                    "Решение P&L":
                        st.column_config.SelectboxColumn(
                            "Решение P&L",
                            options=list(REPORT_ACTIONS),
                            required=True,
                        ),
                    "Категория P&L":
                        st.column_config.SelectboxColumn(
                            "Категория P&L",
                            options=list(PNL_CATEGORIES),
                            required=True,
                        ),
                    "Решение Cash Flow":
                        st.column_config.SelectboxColumn(
                            "Решение Cash Flow",
                            options=list(REPORT_ACTIONS),
                            required=True,
                        ),
                    "Категория Cash Flow":
                        st.column_config.SelectboxColumn(
                            "Категория Cash Flow",
                            options=list(CF_CATEGORIES),
                            required=True,
                        ),
                    "Комментарий":
                        st.column_config.TextColumn(
                            "Комментарий",
                            max_chars=500,
                        ),
                },
                key="classification_editor",
            )

            if st.button(
                "Сохранить классификацию",
                type="primary",
                use_container_width=True,
            ):
                classification_payload = (
                    edited_classifications.rename(
                        columns={
                            "id": "id",
                            "Решение P&L":
                                "pnl_action",
                            "Категория P&L":
                                "pnl_category",
                            "Решение Cash Flow":
                                "cf_action",
                            "Категория Cash Flow":
                                "cf_category",
                            "Комментарий":
                                "comment",
                        }
                    )
                )

                try:
                    save_result = save_classifications(
                        classification_payload
                    )
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.session_state[
                        "classification_message"
                    ] = (
                        f"Сохранено операций: "
                        f"{save_result.updated}. "
                        f"Полностью классифицировано: "
                        f"{save_result.classified}. "
                        f"Частично: "
                        f"{save_result.partial}."
                    )

                    st.rerun()


with import_tab:
    st.subheader("Импорт банковской выписки")

    uploaded_file = st.file_uploader(
        "Загрузите CSV-выписку Т-Бизнеса",
        type=["csv"],
        help=(
            "Файл обрабатывается локально "
            "и никуда не отправляется."
        ),
    )

    if uploaded_file is None:
        st.info(
            "Выберите CSV-файл для предварительной проверки."
        )
    else:
        try:
            result = read_tbank_csv(uploaded_file)
        except BankStatementError as exc:
            st.error(str(exc))
            st.stop()
        except Exception as exc:
            st.exception(exc)
            st.stop()

        imported_transactions = result.transactions

        for warning in result.warnings:
            st.warning(warning)

        show_metrics(imported_transactions)

        st.subheader("Предварительный просмотр")

        st.dataframe(
            prepare_visible_table(imported_transactions),
            use_container_width=True,
            hide_index=True,
        )

        if st.button(
            "Сохранить новые операции в базу",
            type="primary",
            use_container_width=True,
        ):
            save_result = save_transactions(
                imported_transactions
            )

            st.session_state["last_import_message"] = (
                f"Получено операций: "
                f"{save_result.received}. "
                f"Добавлено новых: "
                f"{save_result.inserted}. "
                f"Пропущено дублей: "
                f"{save_result.duplicates}."
            )

            st.rerun()