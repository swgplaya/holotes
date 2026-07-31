from decimal import Decimal

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
    ReportResult,
    build_cash_flow_report,
    build_pnl_report,
    filter_transactions_by_period,
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
) -> None:
    """Отображает метрики, график и детализацию отчёта."""

    metric_columns = st.columns(4)

    metric_columns[0].metric(
        inflow_label,
        format_rubles(report.inflow_kopecks),
    )

    metric_columns[1].metric(
        outflow_label,
        format_rubles(report.outflow_kopecks),
    )

    metric_columns[2].metric(
        net_label,
        format_rubles(report.net_kopecks),
    )

    metric_columns[3].metric(
        "Учтено операций",
        report.included_count,
    )

    st.caption(
        f"Исключено из отчёта: "
        f"{report.excluded_count}. "
        f"Не принято решение: "
        f"{report.pending_count}."
    )

    if report.pending_count:
        st.warning(
            "Часть операций ещё не классифицирована "
            "для этого отчёта и не входит в расчёт."
        )

    if report.transactions.empty:
        st.info(
            "В выбранном периоде нет операций, "
            "включённых в этот отчёт."
        )
        return

    category_table = report.category_totals.copy()

    category_table["Сумма, ₽"] = (
        category_table["amount_kopecks"] / 100
    )

    category_table = category_table.rename(
        columns={
            "category": "Категория",
        }
    )

    st.subheader("Структура по категориям")

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

    with st.expander(
        "Показать операции отчёта",
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


def show_financial_report(
    transactions: pd.DataFrame,
    report_type: str,
    key_prefix: str,
) -> None:
    """Показывает P&L или Cash Flow за выбранный период."""

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
    except ValueError as exc:
        st.error(str(exc))
        return

    st.caption(
        f"Период: "
        f"{start_date.strftime('%d.%m.%Y')} — "
        f"{end_date.strftime('%d.%m.%Y')}"
    )

    if report_type == "pnl":
        report = build_pnl_report(
            period_transactions
        )

        show_report_result(
            report=report,
            category_column="pnl_category",
            inflow_label="Доходы",
            outflow_label="Расходы",
            net_label="Результат",
        )

        return

    if report_type == "cash_flow":
        report = build_cash_flow_report(
            period_transactions
        )

        show_report_result(
            report=report,
            category_column="cf_category",
            inflow_label="Поступления",
            outflow_label="Платежи",
            net_label="Чистый денежный поток",
        )

        return

    raise ValueError(
        f"Неизвестный тип отчёта: {report_type}"
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
    import_tab,
) = st.tabs(
    [
        "Операции в базе",
        "Классификация",
        "Правила",
        "P&L",
        "Cash Flow",
        "Импорт выписки",
    ]
)

classification_message = st.session_state.pop(
    "classification_message",
    None,
)

if classification_message:
    st.success(classification_message)

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