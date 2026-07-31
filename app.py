from decimal import Decimal

import streamlit as st

from src.bank_import import BankStatementError, read_tbank_csv


st.set_page_config(
    page_title="Open MAS",
    page_icon="📊",
    layout="wide",
)


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


st.title("Open MAS")
st.caption("Система управленческого финансового учёта")

st.subheader("Импорт банковской выписки")

uploaded_file = st.file_uploader(
    "Загрузите CSV-выписку Т-Бизнеса",
    type=["csv"],
    help="Файл обрабатывается локально и никуда не отправляется.",
)

if uploaded_file is None:
    st.info("Загрузите обезличенную CSV-выписку для проверки импортёра.")
    st.stop()

try:
    result = read_tbank_csv(uploaded_file)
except BankStatementError as exc:
    st.error(str(exc))
    st.stop()
except Exception as exc:
    st.exception(exc)
    st.stop()

transactions = result.transactions

for warning in result.warnings:
    st.warning(warning)

inflow_kopecks = int(
    transactions.loc[
        transactions["signed_amount_kopecks"] > 0,
        "signed_amount_kopecks",
    ].sum()
)

outflow_kopecks = abs(
    int(
        transactions.loc[
            transactions["signed_amount_kopecks"] < 0,
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

st.subheader("Нормализованные операции")

preview = transactions.copy()

preview["Дата"] = preview["posted_at"].dt.strftime("%d.%m.%Y")
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

st.dataframe(
    preview[visible_columns],
    use_container_width=True,
    hide_index=True,
)

with st.expander("Технические данные"):
    st.write(
        "Уникальных идентификаторов:",
        transactions["source_hash"].nunique(),
    )
    st.dataframe(
        transactions,
        use_container_width=True,
        hide_index=True,
    )