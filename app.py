from decimal import Decimal

import pandas as pd
import streamlit as st

from src.bank_import import (
    BankStatementError,
    read_tbank_csv,
)
from src.database import init_db
from src.transaction_repository import (
    get_transactions_dataframe,
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

operations_tab, import_tab = st.tabs(
    [
        "Операции в базе",
        "Импорт выписки",
    ]
)


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