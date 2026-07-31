from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

import pandas as pd
import streamlit as st
import plotly.express as px

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
from src.reporting import (
    COMPARISON_MODES,
    ReportResult,
    build_cash_flow_report,
    build_category_comparison,
    build_pnl_report,
    filter_transactions_by_period,
    get_comparison_period,
)

from src.rule_repository import (
    DIRECTION_FILTERS,
    MATCH_FIELDS,
    MATCH_TYPES,
    apply_classification_rules,
    create_rule,
    delete_rule,
    get_rules_dataframe,
    set_rule_active,
)

from src.payment_calendar import (
    DIRECTION_LABELS,
    RECURRENCE_LABELS,
    build_cash_forecast,
    create_planned_cash_flow,
    delete_planned_cash_flow,
    expand_planned_cash_flows,
    get_planned_cash_flows_dataframe,
    set_planned_cash_flow_active,
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

def rubles_to_kopecks(value: float) -> int:
    """Безопасно преобразует рубли в копейки."""

    amount = Decimal(str(value))

    kopecks = (
        amount * Decimal("100")
    ).quantize(
        Decimal("1"),
        rounding=ROUND_HALF_UP,
    )

    return int(kopecks)

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

def prepare_report_details(
    transactions: pd.DataFrame,
    category_column: str,
) -> pd.DataFrame:
    """Подготавливает детализацию финансового отчёта."""

    details = transactions.copy()

    details["posted_at"] = pd.to_datetime(
        details["posted_at"],
        errors="coerce",
    )

    details["Дата"] = details[
        "posted_at"
    ].dt.strftime("%d.%m.%Y")

    details["Сумма, ₽"] = (
        details["signed_amount_kopecks"] / 100
    )

    details["Категория"] = (
        details[category_column]
        .fillna("")
        .replace("", "Без категории")
    )

    details["Контрагент"] = (
        details["counterparty_name"]
        .fillna("")
    )

    details["Описание"] = (
        details["description"]
        .fillna("")
    )

    details["Назначение платежа"] = (
        details["payment_purpose"]
        .fillna("")
    )

    return details[
        [
            "Дата",
            "Сумма, ₽",
            "Категория",
            "Контрагент",
            "Описание",
            "Назначение платежа",
        ]
    ]


def show_report_result(
    report: ReportResult,
    category_column: str,
    inflow_label: str,
    outflow_label: str,
    net_label: str,
    current_label: str,
    comparison_report: ReportResult | None = None,
    comparison_label: str | None = None,
) -> None:
    """Отображает финансовый отчёт и сравнение периодов."""

    def money_delta(
        current_value: int,
        comparison_value: int,
    ) -> str:
        difference = (
            current_value - comparison_value
        )

        prefix = "+" if difference > 0 else ""

        return (
            prefix
            + format_rubles(difference)
        )

    metric_columns = st.columns(4)

    inflow_delta = None
    outflow_delta = None
    net_delta = None
    count_delta = None

    if comparison_report is not None:
        inflow_delta = money_delta(
            report.inflow_kopecks,
            comparison_report.inflow_kopecks,
        )

        outflow_delta = money_delta(
            report.outflow_kopecks,
            comparison_report.outflow_kopecks,
        )

        net_delta = money_delta(
            report.net_kopecks,
            comparison_report.net_kopecks,
        )

        operation_difference = (
            report.included_count
            - comparison_report.included_count
        )

        count_delta = (
            f"{operation_difference:+d}"
        )

    metric_columns[0].metric(
        inflow_label,
        format_rubles(report.inflow_kopecks),
        delta=inflow_delta,
    )

    metric_columns[1].metric(
        outflow_label,
        format_rubles(report.outflow_kopecks),
        delta=outflow_delta,
    )

    metric_columns[2].metric(
        net_label,
        format_rubles(report.net_kopecks),
        delta=net_delta,
    )

    metric_columns[3].metric(
        "Учтено операций",
        report.included_count,
        delta=count_delta,
    )

    st.caption(
        f"{current_label}: "
        f"исключено из отчёта — "
        f"{report.excluded_count}; "
        f"не принято решение — "
        f"{report.pending_count}."
    )

    if (
        comparison_report is not None
        and comparison_label is not None
    ):
        st.caption(
            f"{comparison_label}: "
            f"учтено — "
            f"{comparison_report.included_count}; "
            f"исключено — "
            f"{comparison_report.excluded_count}; "
            f"не принято решение — "
            f"{comparison_report.pending_count}."
        )

    if report.pending_count:
        st.warning(
            "Часть операций выбранного периода "
            "ещё не классифицирована для этого отчёта."
        )

    if report.transactions.empty:
        st.info(
            "В выбранном периоде нет операций, "
            "включённых в этот отчёт."
        )

        if comparison_report is None:
            return

    st.subheader("Структура по категориям")

    if comparison_report is None:
        category_table = (
            report.category_totals.copy()
        )

        category_table["Сумма, ₽"] = (
            category_table[
                "amount_kopecks"
            ] / 100
        )

        category_table = category_table.rename(
            columns={
                "category": "Категория",
            }
        )

        if category_table.empty:
            st.info(
                "Нет данных для построения "
                "структуры по категориям."
            )
        else:
            chart = px.bar(
                category_table,
                x="Категория",
                y="Сумма, ₽",
                text_auto=".2s",
            )

            chart.update_layout(
                xaxis_title="",
                yaxis_title="Сумма, ₽",
            )

            st.plotly_chart(
                chart,
                use_container_width=True,
            )

            st.dataframe(
                category_table[
                    [
                        "Категория",
                        "Сумма, ₽",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Сумма, ₽":
                        st.column_config.NumberColumn(
                            "Сумма, ₽",
                            format="%.2f",
                        ),
                },
            )

    else:
        comparison_table = (
            build_category_comparison(
                current_report=report,
                comparison_report=comparison_report,
            )
        )

        comparison_table[
            "Выбранный период, ₽"
        ] = (
            comparison_table[
                "current_amount_kopecks"
            ] / 100
        )

        comparison_table[
            "Период сравнения, ₽"
        ] = (
            comparison_table[
                "comparison_amount_kopecks"
            ] / 100
        )

        comparison_table["Изменение, ₽"] = (
            comparison_table[
                "delta_kopecks"
            ] / 100
        )

        comparison_table = (
            comparison_table.rename(
                columns={
                    "category": "Категория",
                    "change_percent":
                        "Изменение, %",
                }
            )
        )

        if comparison_table.empty:
            st.info(
                "В обоих периодах нет данных "
                "для сравнения категорий."
            )
        else:
            chart_data = comparison_table[
                [
                    "Категория",
                    "Выбранный период, ₽",
                    "Период сравнения, ₽",
                ]
            ].melt(
                id_vars="Категория",
                var_name="Период",
                value_name="Сумма, ₽",
            )

            comparison_chart = px.bar(
                chart_data,
                x="Категория",
                y="Сумма, ₽",
                color="Период",
                barmode="group",
            )

            comparison_chart.update_layout(
                xaxis_title="",
                yaxis_title="Сумма, ₽",
            )

            st.plotly_chart(
                comparison_chart,
                use_container_width=True,
            )

            st.dataframe(
                comparison_table[
                    [
                        "Категория",
                        "Выбранный период, ₽",
                        "Период сравнения, ₽",
                        "Изменение, ₽",
                        "Изменение, %",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Выбранный период, ₽":
                        st.column_config.NumberColumn(
                            "Выбранный период, ₽",
                            format="%.2f",
                        ),
                    "Период сравнения, ₽":
                        st.column_config.NumberColumn(
                            "Период сравнения, ₽",
                            format="%.2f",
                        ),
                    "Изменение, ₽":
                        st.column_config.NumberColumn(
                            "Изменение, ₽",
                            format="%.2f",
                        ),
                    "Изменение, %":
                        st.column_config.NumberColumn(
                            "Изменение, %",
                            format="%.1f%%",
                        ),
                },
            )

    if not report.transactions.empty:
        with st.expander(
            "Операции выбранного периода",
            expanded=False,
        ):
            details = prepare_report_details(
                transactions=report.transactions,
                category_column=category_column,
            )

            st.dataframe(
                details,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Сумма, ₽":
                        st.column_config.NumberColumn(
                            "Сумма, ₽",
                            format="%.2f",
                        ),
                },
            )

    if (
        comparison_report is not None
        and not comparison_report.transactions.empty
    ):
        with st.expander(
            "Операции периода сравнения",
            expanded=False,
        ):
            comparison_details = (
                prepare_report_details(
                    transactions=(
                        comparison_report.transactions
                    ),
                    category_column=category_column,
                )
            )

            st.dataframe(
                comparison_details,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Сумма, ₽":
                        st.column_config.NumberColumn(
                            "Сумма, ₽",
                            format="%.2f",
                        ),
                },
            )


def show_financial_report(
    transactions: pd.DataFrame,
    report_type: str,
    key_prefix: str,
) -> None:
    """Показывает отчёт и сравнение выбранных периодов."""

    if transactions.empty:
        st.info(
            "В базе пока нет операций."
        )
        return

    posted_dates = pd.to_datetime(
        transactions["posted_at"],
        errors="coerce",
    ).dropna()

    if posted_dates.empty:
        st.error(
            "В базе не найдено корректных дат проведения."
        )
        return

    min_date = posted_dates.min().date()
    max_date = posted_dates.max().date()

    selected_period = st.date_input(
        "Период отчёта",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        format="DD.MM.YYYY",
        key=f"{key_prefix}_period",
    )

    comparison_mode = st.selectbox(
        "Сравнить с",
        options=list(COMPARISON_MODES),
        format_func=COMPARISON_MODES.get,
        key=f"{key_prefix}_comparison_mode",
    )

    if (
        not isinstance(selected_period, tuple)
        or len(selected_period) != 2
    ):
        st.info(
            "Выбери дату начала и окончания периода."
        )
        return

    start_date, end_date = selected_period

    try:
        period_transactions = (
            filter_transactions_by_period(
                transactions=transactions,
                start_date=start_date,
                end_date=end_date,
            )
        )

        comparison_dates = (
            get_comparison_period(
                start_date=start_date,
                end_date=end_date,
                mode=comparison_mode,
            )
        )
    except ValueError as exc:
        st.error(str(exc))
        return

    current_label = (
        f"{start_date.strftime('%d.%m.%Y')} — "
        f"{end_date.strftime('%d.%m.%Y')}"
    )

    if report_type == "pnl":
        report_builder = build_pnl_report
        category_column = "pnl_category"
        inflow_label = "Доходы"
        outflow_label = "Расходы"
        net_label = "Результат"

    elif report_type == "cash_flow":
        report_builder = build_cash_flow_report
        category_column = "cf_category"
        inflow_label = "Поступления"
        outflow_label = "Платежи"
        net_label = "Чистый денежный поток"

    else:
        raise ValueError(
            f"Неизвестный тип отчёта: {report_type}"
        )

    report = report_builder(
        period_transactions
    )

    comparison_report = None
    comparison_label = None

    if comparison_dates is not None:
        comparison_start, comparison_end = (
            comparison_dates
        )

        comparison_transactions = (
            filter_transactions_by_period(
                transactions=transactions,
                start_date=comparison_start,
                end_date=comparison_end,
            )
        )

        comparison_report = report_builder(
            comparison_transactions
        )

        comparison_label = (
            f"{comparison_start.strftime('%d.%m.%Y')} — "
            f"{comparison_end.strftime('%d.%m.%Y')}"
        )

    if comparison_label is None:
        st.caption(
            f"Период: {current_label}"
        )
    else:
        st.caption(
            f"Выбранный период: {current_label}. "
            f"Сравнение: {comparison_label}."
        )

    show_report_result(
        report=report,
        category_column=category_column,
        inflow_label=inflow_label,
        outflow_label=outflow_label,
        net_label=net_label,
        current_label=current_label,
        comparison_report=comparison_report,
        comparison_label=comparison_label,
    )

st.title("Open MAS")
st.caption("Система управленческого финансового учёта")

last_import_message = st.session_state.pop(
    "last_import_message",
    None,
)

if last_import_message:
    st.success(last_import_message)

(
    operations_tab,
    classification_tab,
    rules_tab,
    pnl_tab,
    cash_flow_tab,
    payment_calendar_tab,
    import_tab,
) = st.tabs(
    [
        "Операции в базе",
        "Классификация",
        "Правила",
        "P&L",
        "Cash Flow",
        "Платёжный календарь",
        "Импорт выписки",
    ]
)

classification_message = st.session_state.pop(
    "classification_message",
    None,
)

if classification_message:
    st.success(classification_message)

calendar_message = st.session_state.pop(
    "calendar_message",
    None,
)

if calendar_message:
    st.success(calendar_message)

rule_message = st.session_state.pop(
    "rule_message",
    None,
)

if rule_message:
    st.success(rule_message)

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

with rules_tab:
    st.subheader("Правила автоматической классификации")

    st.caption(
        "Правила применяются по убыванию приоритета. "
        "Для каждой операции срабатывает только первое совпадение. "
        "Ручные решения не перезаписываются."
    )

    if st.button(
        "Применить активные правила",
        type="primary",
        use_container_width=True,
    ):
        apply_result = apply_classification_rules()

        st.session_state["rule_message"] = (
            f"Проверено операций: "
            f"{apply_result.checked}. "
            f"Классифицировано: "
            f"{apply_result.matched}. "
            f"Без совпадений: "
            f"{apply_result.unmatched}."
        )

        st.rerun()

    with st.expander(
        "Создать новое правило",
        expanded=True,
    ):
        with st.form("create_rule_form"):
            rule_name = st.text_input(
                "Название правила",
                placeholder="Например: банковские комиссии",
            )

            priority = st.number_input(
                "Приоритет",
                min_value=0,
                max_value=10_000,
                value=100,
                step=10,
                help=(
                    "Чем больше число, тем раньше "
                    "проверяется правило."
                ),
            )

            is_active = st.checkbox(
                "Правило активно",
                value=True,
            )

            direction_filter = st.selectbox(
                "Направление операции",
                options=list(DIRECTION_FILTERS),
                format_func=DIRECTION_FILTERS.get,
            )

            match_field = st.selectbox(
                "Где искать",
                options=list(MATCH_FIELDS),
                format_func=MATCH_FIELDS.get,
            )

            match_type = st.selectbox(
                "Условие",
                options=list(MATCH_TYPES),
                format_func=MATCH_TYPES.get,
            )

            match_value = st.text_input(
                "Искомое значение",
                placeholder="Например: обслуживание счета",
            )

            pnl_column, cf_column = st.columns(2)

            with pnl_column:
                st.markdown("**P&L**")

                pnl_action = st.selectbox(
                    "Решение P&L",
                    options=list(REPORT_ACTIONS),
                    key="rule_pnl_action",
                )

                pnl_category = st.selectbox(
                    "Категория P&L",
                    options=list(PNL_CATEGORIES),
                    key="rule_pnl_category",
                )

            with cf_column:
                st.markdown("**Cash Flow**")

                cf_action = st.selectbox(
                    "Решение Cash Flow",
                    options=list(REPORT_ACTIONS),
                    key="rule_cf_action",
                )

                cf_category = st.selectbox(
                    "Категория Cash Flow",
                    options=list(CF_CATEGORIES),
                    key="rule_cf_category",
                )

            create_rule_submitted = st.form_submit_button(
                "Создать правило",
                type="primary",
                use_container_width=True,
            )

            if create_rule_submitted:
                try:
                    new_rule_id = create_rule(
                        name=rule_name,
                        priority=int(priority),
                        is_active=is_active,
                        direction_filter=direction_filter,
                        match_field=match_field,
                        match_type=match_type,
                        match_value=match_value,
                        pnl_action=pnl_action,
                        pnl_category=pnl_category,
                        cf_action=cf_action,
                        cf_category=cf_category,
                    )
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.session_state["rule_message"] = (
                        f"Правило #{new_rule_id} создано."
                    )
                    st.rerun()

    rules = get_rules_dataframe()

    st.subheader("Сохранённые правила")

    if rules.empty:
        st.info(
            "Правила пока не созданы."
        )
    else:
        visible_rules = rules.rename(
            columns={
                "id": "ID",
                "name": "Название",
                "priority": "Приоритет",
                "is_active": "Активно",
                "direction_filter": "Направление",
                "match_field": "Поле",
                "match_type": "Условие",
                "match_value": "Значение",
                "pnl_action": "Решение P&L",
                "pnl_category": "Категория P&L",
                "cf_action": "Решение CF",
                "cf_category": "Категория CF",
            }
        )

        st.dataframe(
            visible_rules,
            use_container_width=True,
            hide_index=True,
        )

        rule_options = {
            f"{int(row['id'])} — {row['name']}":
                int(row["id"])
            for _, row in rules.iterrows()
        }

        selected_rule_label = st.selectbox(
            "Выберите правило для управления",
            options=list(rule_options),
        )

        selected_rule_id = rule_options[
            selected_rule_label
        ]

        selected_rule = rules.loc[
            rules["id"] == selected_rule_id
        ].iloc[0]

        selected_rule_active = st.checkbox(
            "Правило активно",
            value=bool(
                selected_rule["is_active"]
            ),
            key=f"selected_rule_active_{selected_rule_id}",
        )

        action_column, delete_column = st.columns(2)

        with action_column:
            if st.button(
                    "Сохранить активность",
                    use_container_width=True,
                    key=f"save_rule_activity_{selected_rule_id}",
            ):
                set_rule_active(
                    rule_id=selected_rule_id,
                    is_active=selected_rule_active,
                )

                st.session_state["rule_message"] = (
                    "Состояние правила обновлено."
                )
                st.rerun()

        with delete_column:
            if st.button(
                    "Удалить правило",
                    type="secondary",
                    use_container_width=True,
                    key=f"delete_rule_{selected_rule_id}",
            ):
                delete_rule(selected_rule_id)

                st.session_state["rule_message"] = (
                    "Правило удалено."
                )
                st.rerun()

with pnl_tab:
    st.subheader("P&L")

    st.caption(
        "На текущем этапе отчёт строится "
        "по банковским операциям кассовым методом."
    )

    pnl_transactions = (
        get_transactions_dataframe()
    )

    show_financial_report(
        transactions=pnl_transactions,
        report_type="pnl",
        key_prefix="pnl",
    )

with cash_flow_tab:
    st.subheader("Cash Flow")

    st.caption(
        "Отчёт показывает фактические движения "
        "денежных средств по дате проведения."
    )

    cash_flow_transactions = (
        get_transactions_dataframe()
    )

    show_financial_report(
        transactions=cash_flow_transactions,
        report_type="cash_flow",
        key_prefix="cash_flow",
    )

with payment_calendar_tab:
    st.subheader("Платёжный календарь")

    st.caption(
        "Добавляй будущие платежи и поступления. "
        "Система рассчитает прогноз остатка "
        "и предупредит о кассовом разрыве."
    )

    with st.expander(
        "Добавить плановую операцию",
        expanded=True,
    ):
        with st.form(
            "planned_cash_flow_form",
            clear_on_submit=True,
        ):
            plan_name = st.text_input(
                "Название",
                placeholder=(
                    "Например: аренда офиса "
                    "или поступление от клиента"
                ),
            )

            direction = st.selectbox(
                "Тип операции",
                options=list(DIRECTION_LABELS),
                format_func=DIRECTION_LABELS.get,
            )

            amount_rubles = st.number_input(
                "Сумма, ₽",
                min_value=0.01,
                value=1_000.00,
                step=100.00,
                format="%.2f",
            )

            category = st.selectbox(
                "Категория Cash Flow",
                options=list(CF_CATEGORIES),
            )

            counterparty = st.text_input(
                "Контрагент",
            )

            start_date = st.date_input(
                "Дата первой операции",
                value=date.today(),
                format="DD.MM.YYYY",
            )

            recurrence = st.selectbox(
                "Повторение",
                options=list(RECURRENCE_LABELS),
                format_func=RECURRENCE_LABELS.get,
            )

            use_end_date = st.checkbox(
                "Ограничить повторение датой окончания",
                value=False,
            )

            selected_end_date = st.date_input(
                "Дата окончания повторения",
                value=(
                    date.today()
                    + timedelta(days=365)
                ),
                format="DD.MM.YYYY",
            )

            is_active = st.checkbox(
                "Операция активна",
                value=True,
            )

            comment = st.text_area(
                "Комментарий",
                max_chars=500,
            )

            create_plan_submitted = (
                st.form_submit_button(
                    "Добавить в календарь",
                    type="primary",
                    use_container_width=True,
                )
            )

            if create_plan_submitted:
                plan_end_date = (
                    selected_end_date
                    if use_end_date
                    else None
                )

                try:
                    new_plan_id = create_planned_cash_flow(
                        name=plan_name,
                        direction=direction,
                        amount_kopecks=(
                            rubles_to_kopecks(
                                amount_rubles
                            )
                        ),
                        category=category,
                        counterparty=counterparty,
                        start_date=start_date,
                        recurrence=recurrence,
                        end_date=plan_end_date,
                        is_active=is_active,
                        comment=comment,
                    )
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.session_state[
                        "calendar_message"
                    ] = (
                        f"Плановая операция "
                        f"#{new_plan_id} добавлена."
                    )
                    st.rerun()

    plans = get_planned_cash_flows_dataframe()

    st.subheader("Плановые операции")

    if plans.empty:
        st.info(
            "Платёжный календарь пока пуст."
        )
    else:
        visible_plans = plans.copy()

        visible_plans["Тип"] = (
            visible_plans["direction"]
            .map(DIRECTION_LABELS)
        )

        visible_plans["Сумма, ₽"] = (
            visible_plans["amount_kopecks"] / 100
        )

        visible_plans["Начало"] = pd.to_datetime(
            visible_plans["start_date"]
        ).dt.strftime("%d.%m.%Y")

        visible_plans["Окончание"] = (
            pd.to_datetime(
                visible_plans["end_date"],
                errors="coerce",
            )
            .dt.strftime("%d.%m.%Y")
            .fillna("")
        )

        visible_plans["Повторение"] = (
            visible_plans["recurrence"]
            .map(RECURRENCE_LABELS)
        )

        visible_plans["Активно"] = (
            visible_plans["is_active"]
        )

        visible_plans = visible_plans.rename(
            columns={
                "id": "ID",
                "name": "Название",
                "category": "Категория",
                "counterparty": "Контрагент",
                "comment": "Комментарий",
            }
        )

        st.dataframe(
            visible_plans[
                [
                    "ID",
                    "Название",
                    "Тип",
                    "Сумма, ₽",
                    "Категория",
                    "Контрагент",
                    "Начало",
                    "Повторение",
                    "Окончание",
                    "Активно",
                    "Комментарий",
                ]
            ],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Сумма, ₽":
                    st.column_config.NumberColumn(
                        "Сумма, ₽",
                        format="%.2f",
                    ),
            },
        )

        plan_options = {
            (
                f"{int(row['id'])} — "
                f"{row['name']}"
            ): int(row["id"])
            for _, row in plans.iterrows()
        }

        selected_plan_label = st.selectbox(
            "Выберите операцию для управления",
            options=list(plan_options),
        )

        selected_plan_id = plan_options[
            selected_plan_label
        ]

        selected_plan = plans.loc[
            plans["id"] == selected_plan_id
        ].iloc[0]

        selected_plan_active = st.checkbox(
            "Операция активна",
            value=bool(
                selected_plan["is_active"]
            ),
            key=(
                f"selected_plan_active_"
                f"{selected_plan_id}"
            ),
        )

        active_column, delete_column = st.columns(2)

        with active_column:
            if st.button(
                    "Сохранить активность",
                    use_container_width=True,
                    key=f"save_plan_activity_{selected_plan_id}",
            ):
                set_planned_cash_flow_active(
                    plan_id=selected_plan_id,
                    is_active=selected_plan_active,
                )

                st.session_state[
                    "calendar_message"
                ] = (
                    "Состояние плановой "
                    "операции обновлено."
                )
                st.rerun()

        with delete_column:
            if st.button(
                    "Удалить плановую операцию",
                    use_container_width=True,
                    key=f"delete_plan_{selected_plan_id}",
            ):
                delete_planned_cash_flow(
                    selected_plan_id
                )

                st.session_state[
                    "calendar_message"
                ] = (
                    "Плановая операция удалена."
                )
                st.rerun()

    st.divider()
    st.subheader("Прогноз остатка")

    forecast_start = st.date_input(
        "Начало прогноза",
        value=date.today(),
        format="DD.MM.YYYY",
        key="forecast_start",
    )

    forecast_horizon = st.selectbox(
        "Горизонт прогноза",
        options=[30, 60, 90, 180, 365],
        index=2,
        format_func=lambda days: f"{days} дней",
    )

    opening_balance_rubles = st.number_input(
        "Остаток денежных средств на начало, ₽",
        value=0.00,
        step=1_000.00,
        format="%.2f",
    )

    forecast_end = (
        forecast_start
        + timedelta(days=forecast_horizon - 1)
    )

    occurrences = expand_planned_cash_flows(
        plans=plans,
        period_start=forecast_start,
        period_end=forecast_end,
    )

    forecast = build_cash_forecast(
        occurrences=occurrences,
        period_start=forecast_start,
        period_end=forecast_end,
        opening_balance_kopecks=(
            rubles_to_kopecks(
                opening_balance_rubles
            )
        ),
    )

    total_inflow = int(
        occurrences.loc[
            occurrences[
                "signed_amount_kopecks"
            ] > 0,
            "signed_amount_kopecks",
        ].sum()
    )

    total_outflow = abs(
        int(
            occurrences.loc[
                occurrences[
                    "signed_amount_kopecks"
                ] < 0,
                "signed_amount_kopecks",
            ].sum()
        )
    )

    ending_balance = int(
        forecast[
            "closing_balance_kopecks"
        ].iloc[-1]
    )

    minimum_balance = int(
        forecast[
            "closing_balance_kopecks"
        ].min()
    )

    forecast_metrics = st.columns(4)

    forecast_metrics[0].metric(
        "Плановые поступления",
        format_rubles(total_inflow),
    )

    forecast_metrics[1].metric(
        "Плановые платежи",
        format_rubles(total_outflow),
    )

    forecast_metrics[2].metric(
        "Остаток на конец",
        format_rubles(ending_balance),
    )

    forecast_metrics[3].metric(
        "Минимальный остаток",
        format_rubles(minimum_balance),
    )

    cash_gap_rows = forecast.loc[
        forecast["closing_balance_kopecks"] < 0
    ]

    if cash_gap_rows.empty:
        st.success(
            "На выбранном горизонте "
            "кассовый разрыв не прогнозируется."
        )
    else:
        first_cash_gap = (
            cash_gap_rows.iloc[0]["date"]
        )

        cash_gap_amount = abs(
            int(
                cash_gap_rows[
                    "closing_balance_kopecks"
                ].min()
            )
        )

        st.error(
            "Прогнозируется кассовый разрыв. "
            f"Первая дата: "
            f"{first_cash_gap.strftime('%d.%m.%Y')}. "
            f"Максимальный дефицит: "
            f"{format_rubles(cash_gap_amount)}."
        )

    chart_data = forecast.copy()

    chart_data["Дата"] = pd.to_datetime(
        chart_data["date"]
    )

    chart_data["Остаток, ₽"] = (
        chart_data[
            "closing_balance_kopecks"
        ] / 100
    )

    balance_chart = px.line(
        chart_data,
        x="Дата",
        y="Остаток, ₽",
    )

    balance_chart.add_hline(y=0)

    balance_chart.update_layout(
        xaxis_title="",
        yaxis_title="Остаток, ₽",
    )

    st.plotly_chart(
        balance_chart,
        use_container_width=True,
    )

    with st.expander(
        "События платёжного календаря",
        expanded=False,
    ):
        if occurrences.empty:
            st.info(
                "На выбранном горизонте "
                "нет плановых операций."
            )
        else:
            visible_occurrences = (
                occurrences.copy()
            )

            visible_occurrences["Дата"] = (
                pd.to_datetime(
                    visible_occurrences["date"]
                ).dt.strftime("%d.%m.%Y")
            )

            visible_occurrences["Сумма, ₽"] = (
                visible_occurrences[
                    "signed_amount_kopecks"
                ] / 100
            )

            visible_occurrences = (
                visible_occurrences.rename(
                    columns={
                        "name": "Название",
                        "category": "Категория",
                        "counterparty":
                            "Контрагент",
                        "comment": "Комментарий",
                    }
                )
            )

            st.dataframe(
                visible_occurrences[
                    [
                        "Дата",
                        "Название",
                        "Сумма, ₽",
                        "Категория",
                        "Контрагент",
                        "Комментарий",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Сумма, ₽":
                        st.column_config.NumberColumn(
                            "Сумма, ₽",
                            format="%.2f",
                        ),
                },
            )

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