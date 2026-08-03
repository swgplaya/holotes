import hashlib
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO
from pathlib import Path

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

from src.classification_summary import (
    build_unclassified_summary,
)

from src.bank_import import (
    BankStatementError,
    read_tbank_csv,
)
from src.database import init_db
from src.rule_config import (
    export_rule_config_json,
    parse_rule_config_json,
)
from src.transaction_repository import (
    clear_bank_data,
    delete_import_batch,
    delete_untracked_transactions,
    get_import_batch_transactions_dataframe,
    get_import_batches_dataframe,
    get_transactions_dataframe,
    get_untracked_transaction_count,
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
    import_rule_records,
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

from src.unit_economics import (
    COST_TYPE_LABELS,
    PRICING_METHOD_LABELS,
    build_unit_economics_summary,
    create_unit_economics_cost_item,
    create_unit_economics_product,
    delete_unit_economics_cost_item,
    delete_unit_economics_product,
    get_unit_economics_cost_items_dataframe,
    get_unit_economics_products_dataframe,
    set_unit_economics_cost_item_active,
    set_unit_economics_product_active,
    update_unit_economics_pricing,
)


st.set_page_config(
    page_title="Open MAS",
    page_icon="📊",
    layout="wide",
)

APP_ROOT = Path(__file__).resolve().parent

st.html(
    APP_ROOT / "assets" / "styles.css"
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

def percent_to_basis_points(
    value: float,
) -> int:
    """Преобразует проценты в базисные пункты."""

    basis_points = (
        Decimal(str(value))
        * Decimal("100")
    ).quantize(
        Decimal("1"),
        rounding=ROUND_HALF_UP,
    )

    return int(basis_points)

def bool_to_action(value: object) -> str:
    """Преобразует значение из базы в подпись интерфейса."""

    if value is None or pd.isna(value):
        return UNDEFINED_ACTION

    if bool(value):
        return INCLUDE_ACTION

    return EXCLUDE_ACTION

def text_or_empty(value: object) -> str:
    """Преобразует пустое значение базы в пустую строку."""

    if value is None or pd.isna(value):
        return ""

    return str(value).strip()


def option_index(
    options: list[str],
    current_value: object,
) -> int:
    """Находит безопасный индекс текущего значения."""

    current_text = text_or_empty(
        current_value
    )

    try:
        return options.index(current_text)
    except ValueError:
        return 0

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

def _safe_percent(
    numerator: int | float,
    denominator: int | float,
) -> float | None:
    """Безопасно рассчитывает процентное отношение."""

    if denominator <= 0:
        return None

    return (
        float(numerator)
        / float(denominator)
        * 100
    )


def _format_optional_percent(
    value: float | None,
) -> str:
    """Форматирует процент или выводит прочерк."""

    if value is None or pd.isna(value):
        return "—"

    return f"{float(value):.1f}%"


def _format_optional_rubles(
    value: float | int | None,
) -> str:
    """Форматирует сумму или выводит прочерк."""

    if value is None or pd.isna(value):
        return "—"

    return format_rubles(
        int(round(float(value)))
    )


def _percentage_point_delta(
    current_value: float | None,
    comparison_value: float | None,
) -> str | None:
    """Возвращает изменение процентного показателя."""

    if (
        current_value is None
        or comparison_value is None
        or pd.isna(current_value)
        or pd.isna(comparison_value)
    ):
        return None

    difference = (
        float(current_value)
        - float(comparison_value)
    )

    return f"{difference:+.1f} п.п."


def _rubles_delta(
    current_value: float | None,
    comparison_value: float | None,
) -> str | None:
    """Возвращает изменение денежного показателя."""

    if (
        current_value is None
        or comparison_value is None
        or pd.isna(current_value)
        or pd.isna(comparison_value)
    ):
        return None

    difference = int(
        round(
            float(current_value)
            - float(comparison_value)
        )
    )

    formatted_difference = format_rubles(
        difference
    )

    if difference > 0:
        return f"+{formatted_difference}"

    return formatted_difference


def _count_delta(
    current_value: int,
    comparison_value: int,
) -> str:
    """Возвращает изменение количества операций."""

    difference = (
        int(current_value)
        - int(comparison_value)
    )

    return f"{difference:+d}"


def _get_report_operation_counts(
    report: ReportResult,
) -> tuple[int, int]:
    """Считает доходные и расходные операции отчёта."""

    transactions = report.transactions

    if transactions.empty:
        return 0, 0

    if (
        "signed_amount_kopecks"
        in transactions.columns
    ):
        amounts = pd.to_numeric(
            transactions[
                "signed_amount_kopecks"
            ],
            errors="coerce",
        ).fillna(0)

        income_count = int(
            (amounts > 0).sum()
        )

        expense_count = int(
            (amounts < 0).sum()
        )

        return income_count, expense_count

    if "direction" in transactions.columns:
        directions = (
            transactions["direction"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.lower()
        )

        income_values = {
            "income",
            "inflow",
            "credit",
            "поступление",
            "приход",
        }

        expense_values = {
            "expense",
            "outflow",
            "debit",
            "списание",
            "расход",
        }

        income_count = int(
            directions.isin(
                income_values
            ).sum()
        )

        expense_count = int(
            directions.isin(
                expense_values
            ).sum()
        )

        return income_count, expense_count

    return 0, 0


def _build_pnl_kpis(
    report: ReportResult,
) -> dict[str, float | int | None]:
    """Рассчитывает доступные KPI кассового P&L."""

    income_count, expense_count = (
        _get_report_operation_counts(report)
    )

    decided_count = (
        report.included_count
        + report.excluded_count
    )

    total_count = (
        decided_count
        + report.pending_count
    )

    profitability = _safe_percent(
        numerator=report.net_kopecks,
        denominator=report.inflow_kopecks,
    )

    expense_share = _safe_percent(
        numerator=report.outflow_kopecks,
        denominator=report.inflow_kopecks,
    )

    expense_coverage = _safe_percent(
        numerator=report.inflow_kopecks,
        denominator=report.outflow_kopecks,
    )

    classification_rate = _safe_percent(
        numerator=decided_count,
        denominator=total_count,
    )

    average_income = (
        report.inflow_kopecks / income_count
        if income_count > 0
        else None
    )

    average_expense = (
        report.outflow_kopecks / expense_count
        if expense_count > 0
        else None
    )

    return {
        "profitability": profitability,
        "expense_share": expense_share,
        "expense_coverage": expense_coverage,
        "classification_rate":
            classification_rate,
        "average_income": average_income,
        "average_expense": average_expense,
        "income_count": income_count,
        "expense_count": expense_count,
    }


def show_pnl_kpis(
    report: ReportResult,
    comparison_report: ReportResult | None,
) -> None:
    """Показывает KPI текущего кассового P&L."""

    current = _build_pnl_kpis(
        report
    )

    comparison = (
        _build_pnl_kpis(
            comparison_report
        )
        if comparison_report is not None
        else None
    )

    st.subheader("KPI P&L")

    first_row = st.columns(4)

    first_row[0].metric(
        "Рентабельность продаж",
        _format_optional_percent(
            current["profitability"]
        ),
        delta=(
            _percentage_point_delta(
                current["profitability"],
                comparison["profitability"],
            )
            if comparison is not None
            else None
        ),
    )

    first_row[1].metric(
        "Доля расходов в доходах",
        _format_optional_percent(
            current["expense_share"]
        ),
        delta=(
            _percentage_point_delta(
                current["expense_share"],
                comparison["expense_share"],
            )
            if comparison is not None
            else None
        ),
        delta_color="inverse",
    )

    first_row[2].metric(
        "Покрытие расходов",
        _format_optional_percent(
            current["expense_coverage"]
        ),
        delta=(
            _percentage_point_delta(
                current["expense_coverage"],
                comparison[
                    "expense_coverage"
                ],
            )
            if comparison is not None
            else None
        ),
    )

    first_row[3].metric(
        "Обработано операций",
        _format_optional_percent(
            current["classification_rate"]
        ),
        delta=(
            _percentage_point_delta(
                current[
                    "classification_rate"
                ],
                comparison[
                    "classification_rate"
                ],
            )
            if comparison is not None
            else None
        ),
    )

    second_row = st.columns(4)

    second_row[0].metric(
        "Среднее поступление",
        _format_optional_rubles(
            current["average_income"]
        ),
        delta=(
            _rubles_delta(
                current["average_income"],
                comparison["average_income"],
            )
            if comparison is not None
            else None
        ),
    )

    second_row[1].metric(
        "Среднее списание",
        _format_optional_rubles(
            current["average_expense"]
        ),
        delta=(
            _rubles_delta(
                current["average_expense"],
                comparison["average_expense"],
            )
            if comparison is not None
            else None
        ),
        delta_color="off",
    )

    second_row[2].metric(
        "Доходных операций",
        int(current["income_count"]),
        delta=(
            _count_delta(
                int(current["income_count"]),
                int(comparison["income_count"]),
            )
            if comparison is not None
            else None
        ),
    )

    second_row[3].metric(
        "Расходных операций",
        int(current["expense_count"]),
        delta=(
            _count_delta(
                int(current["expense_count"]),
                int(comparison["expense_count"]),
            )
            if comparison is not None
            else None
        ),
        delta_color="off",
    )

    st.caption(
        "KPI рассчитаны по включённым банковским "
        "операциям. Это управленческий P&L "
        "по кассовому методу, а не бухгалтерский "
        "отчёт по методу начисления."
    )

def show_report_result(
    report: ReportResult,
    report_type: str,
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

    if report_type == "pnl":
        show_pnl_kpis(
            report=report,
            comparison_report=comparison_report,
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

REPORT_START_DATE_STATE_KEY = (
    "shared_report_start_date"
)

REPORT_END_DATE_STATE_KEY = (
    "shared_report_end_date"
)

REPORT_COMPARISON_STATE_KEY = (
    "shared_report_comparison_mode"
)


REPORT_START_DATE_WIDGET_KEYS = {
    "pnl": "pnl_report_start_date",
    "cash_flow": "cash_flow_report_start_date",
}

REPORT_END_DATE_WIDGET_KEYS = {
    "pnl": "pnl_report_end_date",
    "cash_flow": "cash_flow_report_end_date",
}

REPORT_COMPARISON_WIDGET_KEYS = {
    "pnl": "pnl_report_comparison_mode",
    "cash_flow": "cash_flow_report_comparison_mode",
}


def _clamp_report_date(
    value,
    min_date,
    max_date,
    default_date,
):
    """Ограничивает дату диапазоном имеющихся операций."""

    # None и pandas.NaT не являются корректными датами.
    if value is None or pd.isna(value):
        return default_date

    try:
        timestamp = pd.Timestamp(value)
    except (TypeError, ValueError, OverflowError):
        return default_date

    # pd.Timestamp(pd.NaT) не выбрасывает ошибку,
    # поэтому NaT требуется проверять отдельно.
    if pd.isna(timestamp):
        return default_date

    result = timestamp.date()

    if result < min_date:
        return min_date

    if result > max_date:
        return max_date

    return result

def _set_report_widget_values(
    widget_keys: dict[str, str],
    value,
) -> None:
    """Устанавливает одно значение всем связанным виджетам."""

    for widget_key in widget_keys.values():
        st.session_state[widget_key] = value


def _sync_report_start_date(
    source_widget_key: str,
) -> None:
    """Синхронизирует начало периода между отчётами."""

    selected_start = st.session_state.get(
        source_widget_key
    )

    if (
            selected_start is None
            or pd.isna(selected_start)
    ):
        return

    st.session_state[
        REPORT_START_DATE_STATE_KEY
    ] = selected_start

    _set_report_widget_values(
        REPORT_START_DATE_WIDGET_KEYS,
        selected_start,
    )

    current_end = st.session_state.get(
        REPORT_END_DATE_STATE_KEY
    )

    if (
            current_end is not None
            and not pd.isna(current_end)
            and selected_start > current_end
    ):
        st.session_state[
            REPORT_END_DATE_STATE_KEY
        ] = selected_start

        _set_report_widget_values(
            REPORT_END_DATE_WIDGET_KEYS,
            selected_start,
        )


def _sync_report_end_date(
    source_widget_key: str,
) -> None:
    """Синхронизирует конец периода между отчётами."""

    selected_end = st.session_state.get(
        source_widget_key
    )

    if (
        selected_end is None
        or pd.isna(selected_end)
    ):
        return

    st.session_state[
        REPORT_END_DATE_STATE_KEY
    ] = selected_end

    _set_report_widget_values(
        REPORT_END_DATE_WIDGET_KEYS,
        selected_end,
    )

    current_start = st.session_state.get(
        REPORT_START_DATE_STATE_KEY
    )

    if (
        current_start is not None
        and not pd.isna(current_start)
        and selected_end < current_start
    ):
        st.session_state[
            REPORT_START_DATE_STATE_KEY
        ] = selected_end

        _set_report_widget_values(
            REPORT_START_DATE_WIDGET_KEYS,
            selected_end,
        )

def _sync_report_comparison_mode(
    source_widget_key: str,
) -> None:
    """Синхронизирует режим сравнения отчётов."""

    selected_mode = st.session_state.get(
        source_widget_key
    )

    if selected_mode not in COMPARISON_MODES:
        return

    st.session_state[
        REPORT_COMPARISON_STATE_KEY
    ] = selected_mode

    _set_report_widget_values(
        REPORT_COMPARISON_WIDGET_KEYS,
        selected_mode,
    )


def _prepare_report_filter_state(
    *,
    report_key: str,
    min_date,
    max_date,
) -> None:
    """Подготавливает общий период перед созданием виджетов."""

    if report_key not in {
        "pnl",
        "cash_flow",
    }:
        raise ValueError(
            f"Неизвестный ключ отчёта: {report_key}"
        )

    shared_start = _clamp_report_date(
        value=st.session_state.get(
            REPORT_START_DATE_STATE_KEY
        ),
        min_date=min_date,
        max_date=max_date,
        default_date=min_date,
    )

    shared_end = _clamp_report_date(
        value=st.session_state.get(
            REPORT_END_DATE_STATE_KEY
        ),
        min_date=min_date,
        max_date=max_date,
        default_date=max_date,
    )

    if shared_start > shared_end:
        shared_end = shared_start

    comparison_mode = st.session_state.get(
        REPORT_COMPARISON_STATE_KEY,
        "none",
    )

    if comparison_mode not in COMPARISON_MODES:
        comparison_mode = "none"

    st.session_state[
        REPORT_START_DATE_STATE_KEY
    ] = shared_start

    st.session_state[
        REPORT_END_DATE_STATE_KEY
    ] = shared_end

    st.session_state[
        REPORT_COMPARISON_STATE_KEY
    ] = comparison_mode

    start_widget_key = (
        REPORT_START_DATE_WIDGET_KEYS[
            report_key
        ]
    )

    end_widget_key = (
        REPORT_END_DATE_WIDGET_KEYS[
            report_key
        ]
    )

    comparison_widget_key = (
        REPORT_COMPARISON_WIDGET_KEYS[
            report_key
        ]
    )

    if (
        st.session_state.get(start_widget_key)
        != shared_start
    ):
        st.session_state[
            start_widget_key
        ] = shared_start

    if (
        st.session_state.get(end_widget_key)
        != shared_end
    ):
        st.session_state[
            end_widget_key
        ] = shared_end

    if (
        st.session_state.get(
            comparison_widget_key
        )
        != comparison_mode
    ):
        st.session_state[
            comparison_widget_key
        ] = comparison_mode

def show_financial_report(
    transactions: pd.DataFrame,
    report_type: str,
    key_prefix: str,
) -> None:
    """Показывает отчёт с общими финансовыми фильтрами."""

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

    try:
        _prepare_report_filter_state(
            report_key=key_prefix,
            min_date=min_date,
            max_date=max_date,
        )
    except ValueError as exc:
        st.error(str(exc))
        return

    start_widget_key = (
        REPORT_START_DATE_WIDGET_KEYS[
            key_prefix
        ]
    )

    end_widget_key = (
        REPORT_END_DATE_WIDGET_KEYS[
            key_prefix
        ]
    )

    comparison_widget_key = (
        REPORT_COMPARISON_WIDGET_KEYS[
            key_prefix
        ]
    )

    with st.container(
            border=True,
            key=f"{key_prefix}_period_panel",
    ):
        st.markdown("#### Период отчёта")

        start_column, end_column, comparison_column = (
            st.columns(
                [1, 1, 1.25],
                gap="medium",
            )
        )

        with start_column:
            start_date = st.date_input(
                "Начало периода",
                min_value=min_date,
                max_value=max_date,
                format="DD.MM.YYYY",
                key=start_widget_key,
                on_change=_sync_report_start_date,
                args=(start_widget_key,),
            )

        with end_column:
            end_date = st.date_input(
                "Конец периода",
                min_value=min_date,
                max_value=max_date,
                format="DD.MM.YYYY",
                key=end_widget_key,
                on_change=_sync_report_end_date,
                args=(end_widget_key,),
            )

        with comparison_column:
            comparison_mode = st.selectbox(
                "Сравнить с",
                options=list(COMPARISON_MODES),
                format_func=COMPARISON_MODES.get,
                key=comparison_widget_key,
                on_change=(
                    _sync_report_comparison_mode
                ),
                args=(comparison_widget_key,),
            )

        st.caption(
            "Настройки периода синхронизированы "
            "между P&L и Cash Flow."
        )

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
        report_type=report_type,
        category_column=category_column,
        inflow_label=inflow_label,
        outflow_label=outflow_label,
        net_label=net_label,
        current_label=current_label,
        comparison_report=comparison_report,
        comparison_label=comparison_label,
    )

st.html(
    """
    <section class="openmas-hero">
        <div class="openmas-hero__content">
            <div class="openmas-hero__eyebrow">
                Управленческий финансовый учёт
            </div>

            <h1 class="openmas-hero__title">
                Open MAS
            </h1>

            <p class="openmas-hero__description">
                Локальная система для управления банковскими
                операциями, финансовой отчётностью, правилами
                классификации и денежными потоками бизнеса.
            </p>
        </div>

        <div class="openmas-hero__badge">
            Local-first · MVP
        </div>
    </section>
    """
)

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
    unit_economics_tab,
    payment_calendar_tab,
    import_tab,
) = st.tabs(
    [
        "Операции в базе",
        "Классификация",
        "Правила",
        "P&L",
        "Cash Flow",
        "Unit Economics",
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

unit_economics_message = st.session_state.pop(
    "unit_economics_message",
    None,
)

if unit_economics_message:
    st.success(unit_economics_message)

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

    classification_summary = (
        build_unclassified_summary(
            classification_transactions
        )
    )

    st.markdown(
        "#### Неклассифицированные операции"
    )

    summary_columns = st.columns(4)

    summary_columns[0].metric(
        "Поступления",
        format_rubles(
            classification_summary.inflow_kopecks
        ),
    )

    summary_columns[1].metric(
        "Списания",
        format_rubles(
            classification_summary.outflow_kopecks
        ),
    )

    summary_columns[2].metric(
        "Чистая сумма",
        format_rubles(
            classification_summary.net_kopecks
        ),
    )

    summary_columns[3].metric(
        "Операций",
        classification_summary.operation_count,
    )

    st.caption(
        "Учитываются операции, для которых не завершена "
        "классификация хотя бы в одном контуре: "
        "P&L или Cash Flow."
    )

    if classification_summary.operation_count == 0:
        st.success(
            "Все операции классифицированы."
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

            selection_source = (
                prepare_classification_editor(
                    classification_transactions
                )
                .reset_index(drop=True)
            )

            st.markdown(
                "#### Выберите операцию"
            )

            st.caption(
                "Нажмите на строку или на маркер слева. "
                "Редактирование выбранной операции "
                "откроется ниже."
            )

            selection_columns = [
                "id",
                "Дата",
                "Сумма, ₽",
                "Контрагент",
                "Описание",
                "Решение P&L",
                "Категория P&L",
                "Решение Cash Flow",
                "Категория Cash Flow",
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
                            "ID",
                            format="%d",
                        ),
                    "Сумма, ₽":
                        st.column_config.NumberColumn(
                            "Сумма, ₽",
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
                    "Выбранная операция не найдена. "
                    "Обновите страницу."
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
                    "#### Классификация выбранной операции"
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
                    "Дата",
                    posted_at_text,
                )

                operation_header_columns[1].metric(
                    "Сумма",
                    format_rubles(
                        int(
                            selected_transaction[
                                "signed_amount_kopecks"
                            ]
                        )
                    ),
                )

                operation_header_columns[2].metric(
                    "Операция",
                    (
                        f"{selected_position + 1} "
                        f"из {len(displayed_ids)}"
                    ),
                )

                counterparty_text = text_or_empty(
                    selected_transaction[
                        "counterparty_name"
                    ]
                )

                description_text = text_or_empty(
                    selected_transaction[
                        "description"
                    ]
                )

                purpose_text = text_or_empty(
                    selected_transaction[
                        "payment_purpose"
                    ]
                )

                st.write(
                    "**Контрагент:** "
                    + (
                            counterparty_text
                            or "не указан"
                    )
                )

                st.write(
                    "**Описание:** "
                    + (
                            description_text
                            or "не указано"
                    )
                )

                with st.expander(
                        "Назначение платежа",
                        expanded=True,
                ):
                    st.write(
                        purpose_text
                        or "Не указано"
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
                    text_or_empty(
                        selected_transaction[
                            "pnl_category"
                        ]
                    )
                )

                current_cf_category = (
                    text_or_empty(
                        selected_transaction[
                            "cf_category"
                        ]
                    )
                )

                current_comment = text_or_empty(
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
                        st.markdown("### P&L")

                        selected_pnl_action = (
                            st.selectbox(
                                "Решение P&L",
                                options=(
                                    pnl_action_options
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
                                "Категория P&L",
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
                                help=(
                                    "Категория обязательна, "
                                    "если операция включается "
                                    "в P&L."
                                ),
                            )
                        )

                    with cf_column:
                        st.markdown("### Cash Flow")

                        selected_cf_action = (
                            st.selectbox(
                                "Решение Cash Flow",
                                options=(
                                    cf_action_options
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
                                "Категория Cash Flow",
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
                                help=(
                                    "Категория обязательна, "
                                    "если операция включается "
                                    "в Cash Flow."
                                ),
                            )
                        )

                    selected_comment = st.text_area(
                        "Комментарий",
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
                                "Сохранить",
                                use_container_width=True,
                            )
                        )

                    with button_columns[1]:
                        save_and_next = (
                            st.form_submit_button(
                                "Сохранить и перейти дальше",
                                type="primary",
                                use_container_width=True,
                            )
                        )

                    with button_columns[2]:
                        exclude_from_both = (
                            st.form_submit_button(
                                "Исключить из обоих",
                                use_container_width=True,
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
                            "Выберите категорию P&L."
                        )

                    if (
                            final_cf_action
                            == INCLUDE_ACTION
                            and not final_cf_category
                    ):
                        validation_errors.append(
                            "Выберите категорию "
                            "Cash Flow."
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

                            action_text = (
                                "Операция исключена "
                                "из обоих отчётов."
                                if exclude_from_both
                                else (
                                    "Классификация "
                                    "сохранена."
                                )
                            )

                            st.session_state[
                                "classification_message"
                            ] = (
                                f"{action_text} "
                                f"Обновлено: "
                                f"{save_result.updated}. "
                                f"Полностью "
                                f"классифицировано: "
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
    st.divider()
    st.subheader("Перенос конфигурации правил")

    st.caption(
        "Правила можно сохранить в JSON и перенести "
        "в другую установку Open MAS. "
        "Локальные ID и даты базы не экспортируются."
    )

    export_json = export_rule_config_json()

    export_column, export_info_column = (
        st.columns([1, 2])
    )

    with export_column:
        st.download_button(
            "Скачать правила в JSON",
            data=export_json,
            file_name=(
                "open_mas_rules_"
                f"{date.today().isoformat()}.json"
            ),
            mime="application/json",
            use_container_width=True,
            key="download_rule_config",
        )

    with export_info_column:
        st.info(
            "Экспорт содержит текущие правила, "
            "их приоритеты, условия, категории "
            "и состояние активности."
        )

    uploaded_rule_config = st.file_uploader(
        "Загрузить конфигурацию правил",
        type=["json"],
        help=(
            "Сначала файл будет проверен. "
            "База не изменится до подтверждения импорта."
        ),
        key="rule_config_uploader",
    )

    if uploaded_rule_config is not None:
        try:
            parsed_rule_config = (
                parse_rule_config_json(
                    uploaded_rule_config.getvalue()
                )
            )
        except (TypeError, ValueError) as exc:
            st.error(str(exc))
        else:
            rule_preview = (
                parsed_rule_config.preview
            )

            st.markdown(
                "#### Результат проверки файла"
            )

            preview_metrics = st.columns(4)

            preview_metrics[0].metric(
                "Получено",
                rule_preview.received,
            )

            preview_metrics[1].metric(
                "Уникальных корректных",
                rule_preview.valid_unique,
            )

            preview_metrics[2].metric(
                "Дублей внутри файла",
                rule_preview.duplicates_in_file,
            )

            preview_metrics[3].metric(
                "Уже есть в базе",
                rule_preview.duplicates_in_database,
            )

            st.caption(
                "Версия формата: "
                f"{parsed_rule_config.schema_version}. "
                "Файл экспортирован: "
                f"{parsed_rule_config.exported_at}."
            )

            if rule_preview.errors:
                st.error(
                    "Конфигурация содержит ошибки. "
                    "Импорт заблокирован."
                )

                for error_message in (
                    rule_preview.errors
                ):
                    st.error(error_message)

            if (
                rule_preview.duplicates_in_file
                > 0
            ):
                st.warning(
                    "Повторяющиеся правила внутри файла "
                    "будут импортированы только один раз."
                )

            if (
                rule_preview.duplicates_in_database
                > 0
            ):
                st.info(
                    "В режиме добавления правила, "
                    "которые уже полностью совпадают "
                    "с существующими, будут пропущены."
                )

            with st.expander(
                "Просмотреть содержимое JSON",
                expanded=False,
            ):
                st.json(
                    {
                        "schema_version":
                            parsed_rule_config.schema_version,
                        "exported_at":
                            parsed_rule_config.exported_at,
                        "rules": list(
                            parsed_rule_config.records
                        ),
                    }
                )

            st.markdown("#### Режим импорта")

            import_mode_label = st.radio(
                "Выберите действие",
                options=[
                    "Добавить отсутствующие правила",
                    "Заменить все текущие правила",
                ],
                horizontal=True,
                key="rule_import_mode",
            )

            if (
                import_mode_label
                == "Добавить отсутствующие правила"
            ):
                import_mode = "merge"

                st.caption(
                    "Текущие правила сохранятся. "
                    "Полностью совпадающие правила "
                    "будут пропущены."
                )

                replace_confirmation_valid = True

            else:
                import_mode = "replace"

                st.warning(
                    "Все текущие правила будут удалены "
                    "и заменены правилами из файла. "
                    "Операция выполняется одной транзакцией."
                )

                replace_phrase = (
                    "ЗАМЕНИТЬ ВСЕ ПРАВИЛА"
                )

                replace_confirmation = st.text_input(
                    "Для замены введите:",
                    placeholder=replace_phrase,
                    key="replace_rules_confirmation",
                )

                replace_confirmation_valid = (
                    replace_confirmation.strip()
                    == replace_phrase
                )

            import_disabled = (
                bool(rule_preview.errors)
                or rule_preview.valid_unique == 0
                or not replace_confirmation_valid
            )

            import_button_label = (
                "Добавить правила"
                if import_mode == "merge"
                else "Заменить все правила"
            )

            if st.button(
                import_button_label,
                type="primary",
                use_container_width=True,
                disabled=import_disabled,
                key="import_rule_config_button",
            ):
                try:
                    rule_import_result = (
                        import_rule_records(
                            list(
                                parsed_rule_config.records
                            ),
                            mode=import_mode,
                        )
                    )
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.session_state[
                        "rule_message"
                    ] = (
                        "Импорт правил завершён. "
                        f"Получено: "
                        f"{rule_import_result.received}. "
                        f"Добавлено: "
                        f"{rule_import_result.inserted}. "
                        f"Пропущено дублей: "
                        f"{rule_import_result.skipped_duplicates}. "
                        f"Удалено прежних правил: "
                        f"{rule_import_result.deleted_existing}."
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

with unit_economics_tab:
    st.subheader("Unit Economics")

    st.caption(
        "Затраты «на единицу» умножаются на плановое "
        "количество. Затраты «за период» вычитаются "
        "из общей маржи продукта."
    )

    with st.expander(
            "Добавить продукт",
            expanded=True,
    ):
        with st.form(
                "create_unit_economics_product_form",
                clear_on_submit=True,
        ):
            product_name = st.text_input(
                "Название продукта",
                placeholder="Например: футболка Core",
            )

            planned_units = st.number_input(
                "Плановое количество",
                min_value=1,
                value=100,
                step=1,
            )

            product_is_active = st.checkbox(
                "Продукт активен",
                value=True,
            )

            product_comment = st.text_area(
                "Комментарий к продукту",
                max_chars=500,
            )

            product_submitted = st.form_submit_button(
                "Добавить продукт",
                type="primary",
                use_container_width=True,
            )

            if product_submitted:
                try:
                    product_id = (
                        create_unit_economics_product(
                            name=product_name,
                            planned_units=int(
                                planned_units
                            ),
                            is_active=product_is_active,
                            comment=product_comment,
                        )
                    )
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.session_state[
                        "unit_economics_message"
                    ] = (
                        f"Продукт #{product_id} добавлен."
                    )

                    st.rerun()

    products = (
        get_unit_economics_products_dataframe()
    )

    cost_items = (
        get_unit_economics_cost_items_dataframe()
    )

    if products.empty:
        st.info(
            "Добавь первый продукт для расчёта "
            "Unit Economics."
        )
    else:
        product_options = {
            (
                f"{int(row['id'])} — "
                f"{row['name']}"
            ): int(row["id"])
            for _, row in products.iterrows()
        }

        selected_product_label = st.selectbox(
            "Выберите продукт",
            options=list(product_options),
            key="unit_economics_selected_product",
        )

        selected_product_id = product_options[
            selected_product_label
        ]

        selected_product = products.loc[
            products["id"] == selected_product_id
        ].iloc[0]

        st.subheader(
            f"Затраты: {selected_product['name']}"
        )

        with st.form(
                f"create_cost_item_form_"
                f"{selected_product_id}",
                clear_on_submit=True,
        ):
            cost_name = st.text_input(
                "Название статьи затрат",
                placeholder=(
                    "Например: ткань, упаковка, "
                    "эквайринг или налог"
                ),
            )

            calculation_type = st.selectbox(
                "Тип затрат",
                options=list(COST_TYPE_LABELS),
                format_func=COST_TYPE_LABELS.get,
            )

            cost_amount_rubles: float | None
            percentage_value: float | None

            if calculation_type in {
                "fixed_per_unit",
                "fixed_period",
            }:
                cost_amount_rubles = st.number_input(
                    "Сумма, ₽",
                    min_value=0.00,
                    value=100.00,
                    step=10.00,
                    format="%.2f",
                )

                percentage_value = None

            else:
                percentage_value = st.number_input(
                    "Процент, %",
                    min_value=0.00,
                    max_value=99.99,
                    value=2.50,
                    step=0.10,
                    format="%.2f",
                )

                cost_amount_rubles = None

            cost_is_active = st.checkbox(
                "Строка затрат активна",
                value=True,
            )

            cost_comment = st.text_area(
                "Комментарий к затратам",
                max_chars=500,
            )

            cost_submitted = st.form_submit_button(
                "Добавить строку затрат",
                type="primary",
                use_container_width=True,
            )

            if cost_submitted:
                try:
                    cost_item_id = (
                        create_unit_economics_cost_item(
                            product_id=selected_product_id,
                            name=cost_name,
                            calculation_type=calculation_type,
                            amount_kopecks=(
                                rubles_to_kopecks(
                                    cost_amount_rubles
                                )
                                if cost_amount_rubles
                                   is not None
                                else None
                            ),
                            percentage_bp=(
                                percent_to_basis_points(
                                    percentage_value
                                )
                                if percentage_value
                                   is not None
                                else None
                            ),
                            is_active=cost_is_active,
                            comment=cost_comment,
                        )
                    )
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.session_state[
                        "unit_economics_message"
                    ] = (
                        f"Строка затрат "
                        f"#{cost_item_id} добавлена."
                    )

                    st.rerun()

        selected_cost_items = cost_items.loc[
            cost_items["product_id"]
            == selected_product_id
        ].copy()

        if selected_cost_items.empty:
            st.info(
                "У этого продукта пока нет "
                "строк затрат."
            )
        else:
            visible_cost_items = selected_cost_items.copy()

            visible_cost_items["Тип"] = (
                visible_cost_items[
                    "calculation_type"
                ].map(COST_TYPE_LABELS)
            )

            visible_cost_items["Сумма, ₽"] = (
                    pd.to_numeric(
                        visible_cost_items["amount_kopecks"],
                        errors="coerce",
                    ) / 100
            )

            visible_cost_items["Процент, %"] = (
                    pd.to_numeric(
                        visible_cost_items["percentage_bp"],
                        errors="coerce",
                    ) / 100
            )

            visible_cost_items = visible_cost_items.rename(
                columns={
                    "id": "ID",
                    "name": "Статья затрат",
                    "is_active": "Активна",
                    "comment": "Комментарий",
                }
            )

            st.dataframe(
                visible_cost_items[
                    [
                        "ID",
                        "Статья затрат",
                        "Тип",
                        "Сумма, ₽",
                        "Процент, %",
                        "Активна",
                        "Комментарий",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Сумма, ₽": st.column_config.NumberColumn(
                        "Сумма, ₽",
                        format="%.2f",
                    ),
                    "Процент, %": st.column_config.NumberColumn(
                        "Процент, %",
                        format="%.2f%%",
                    ),
                },
            )

            cost_item_options = {
                (
                    f"{int(row['id'])} — "
                    f"{row['name']}"
                ): int(row["id"])
                for _, row
                in selected_cost_items.iterrows()
            }

            selected_cost_item_label = (
                st.selectbox(
                    "Выберите строку затрат "
                    "для управления",
                    options=list(cost_item_options),
                    key=(
                        "selected_unit_cost_item_"
                        f"{selected_product_id}"
                    ),
                )
            )

            selected_cost_item_id = (
                cost_item_options[
                    selected_cost_item_label
                ]
            )

            selected_cost_item = (
                selected_cost_items.loc[
                    selected_cost_items["id"]
                    == selected_cost_item_id
                ].iloc[0]
            )

            selected_cost_item_active = (
                st.checkbox(
                    "Строка затрат активна",
                    value=bool(
                        selected_cost_item[
                            "is_active"
                        ]
                    ),
                    key=(
                        "unit_cost_active_"
                        f"{selected_cost_item_id}"
                    ),
                )
            )

            cost_active_column, cost_delete_column = (
                st.columns(2)
            )

            with cost_active_column:
                if st.button(
                    "Сохранить активность статьи",
                    use_container_width=True,
                    key=(
                        "save_unit_cost_activity_"
                        f"{selected_cost_item_id}"
                    ),
                ):
                    set_unit_economics_cost_item_active(
                        cost_item_id=(
                            selected_cost_item_id
                        ),
                        is_active=(
                            selected_cost_item_active
                        ),
                    )

                    st.session_state[
                        "unit_economics_message"
                    ] = (
                        "Состояние статьи затрат "
                        "обновлено."
                    )
                    st.rerun()

            with cost_delete_column:
                if st.button(
                    "Удалить статью затрат",
                    use_container_width=True,
                    key=(
                        "delete_unit_cost_"
                        f"{selected_cost_item_id}"
                    ),
                ):
                    delete_unit_economics_cost_item(
                        selected_cost_item_id
                    )

                    st.session_state[
                        "unit_economics_message"
                    ] = (
                        "Статья затрат удалена."
                    )
                    st.rerun()

        st.subheader("Ценообразование")

        pricing_options = [
            "manual",
            "markup",
            "target_margin",
        ]

        stored_method = str(
            selected_product["pricing_method"]
        )

        default_pricing_index = (
            pricing_options.index(stored_method)
            if stored_method in pricing_options
            else 2
        )

        pricing_method = st.selectbox(
            "Способ формирования цены",
            options=pricing_options,
            index=default_pricing_index,
            format_func=PRICING_METHOD_LABELS.get,
            key=f"pricing_method_{selected_product_id}",
        )

        manual_price_rubles = None
        pricing_percent = None

        if pricing_method == "manual":
            stored_manual_price = (
                selected_product[
                    "manual_price_kopecks"
                ]
            )

            manual_price_rubles = st.number_input(
                "Цена продажи, ₽",
                min_value=0.01,
                value=(
                    float(stored_manual_price) / 100
                    if not pd.isna(stored_manual_price)
                    else 1_000.00
                ),
                step=100.00,
                format="%.2f",
                key=f"manual_price_{selected_product_id}",
            )

        else:
            stored_pricing_value = (
                selected_product["pricing_value_bp"]
            )

            pricing_percent = st.number_input(
                (
                    "Наценка, %"
                    if pricing_method == "markup"
                    else "Целевая маржинальность, %"
                ),
                min_value=0.00,
                max_value=99.99,
                value=(
                    float(stored_pricing_value) / 100
                    if not pd.isna(stored_pricing_value)
                    else 35.00
                ),
                step=1.00,
                format="%.2f",
                key=f"pricing_percent_{selected_product_id}",
            )

        stored_rounding_step = int(
            selected_product["rounding_step_kopecks"]
        )

        rounding_step_rubles = st.number_input(
            "Округлять цену вверх до, ₽",
            min_value=1.00,
            value=float(stored_rounding_step) / 100,
            step=10.00,
            format="%.2f",
            key=f"rounding_step_{selected_product_id}",
        )

        if st.button(
                "Сохранить настройки цены",
                type="primary",
                use_container_width=True,
                key=f"save_pricing_{selected_product_id}",
        ):
            try:
                update_unit_economics_pricing(
                    product_id=selected_product_id,
                    pricing_method=pricing_method,
                    pricing_value_bp=(
                        percent_to_basis_points(
                            pricing_percent
                        )
                        if pricing_percent is not None
                        else None
                    ),
                    manual_price_kopecks=(
                        rubles_to_kopecks(
                            manual_price_rubles
                        )
                        if manual_price_rubles is not None
                        else None
                    ),
                    rounding_step_kopecks=(
                        rubles_to_kopecks(
                            rounding_step_rubles
                        )
                    ),
                )
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.session_state[
                    "unit_economics_message"
                ] = "Настройки ценообразования сохранены."

                st.rerun()

        st.divider()
        st.subheader("Расчёт")

        summary = build_unit_economics_summary(
            products=products,
            cost_items=cost_items,
        )

        selected_summary = summary.loc[
            summary["product_id"] == selected_product_id
            ]

        if selected_summary.empty:
            st.warning(
                "Продукт выключен и не участвует в расчёте."
            )
        else:
            result = selected_summary.iloc[0]

            # Эти показатели доступны даже до формирования цены.
            base_metrics = st.columns(4)

            base_metrics[0].metric(
                "Затраты на единицу",
                format_rubles(
                    int(result["fixed_per_unit_kopecks"])
                ),
            )

            base_metrics[1].metric(
                "Затраты периода на единицу",
                format_rubles(
                    int(
                        result[
                            "allocated_period_per_unit_kopecks"
                        ]
                    )
                ),
            )

            base_metrics[2].metric(
                "Базовая себестоимость",
                format_rubles(
                    int(
                        result[
                            "base_cost_per_unit_kopecks"
                        ]
                    )
                ),
            )

            base_metrics[3].metric(
                "Процентные расходы",
                (
                    f"{float(result['percentage_cost_rate']):.2f}%"
                ),
            )

            pricing_error = result["pricing_error"]

            if (
                    pricing_error is not None
                    and not pd.isna(pricing_error)
                    and str(pricing_error).strip()
            ):
                st.warning(str(pricing_error))

                st.info(
                    "Добавь статьи затрат и настрой способ "
                    "формирования цены в блоке «Ценообразование»."
                )

            else:
                selling_price = int(
                    result["selling_price_kopecks"]
                )

                percentage_cost_per_unit = int(
                    result[
                        "percentage_cost_per_unit_kopecks"
                    ]
                )

                total_cost_per_unit = int(
                    result["total_cost_per_unit_kopecks"]
                )

                profit_per_unit = int(
                    result["profit_per_unit_kopecks"]
                )

                price_metrics = st.columns(4)

                price_metrics[0].metric(
                    "Цена продажи",
                    format_rubles(selling_price),
                )

                price_metrics[1].metric(
                    "Процентные расходы на единицу",
                    format_rubles(
                        percentage_cost_per_unit
                    ),
                )

                price_metrics[2].metric(
                    "Полная себестоимость",
                    format_rubles(total_cost_per_unit),
                )

                price_metrics[3].metric(
                    "Прибыль на единицу",
                    format_rubles(profit_per_unit),
                )

                margin_percent = result["margin_percent"]

                if (
                        margin_percent is None
                        or pd.isna(margin_percent)
                ):
                    margin_text = "не рассчитывается"
                else:
                    margin_text = (
                        f"{float(margin_percent):.1f}%"
                    )

                break_even_units = result[
                    "break_even_units"
                ]

                if (
                        break_even_units is None
                        or pd.isna(break_even_units)
                ):
                    break_even_text = (
                        "не рассчитывается"
                    )
                else:
                    break_even_text = (
                        f"{int(break_even_units)} шт."
                    )

                st.write(
                    f"**План продаж:** "
                    f"{int(result['planned_units'])} шт."
                )

                st.write(
                    f"**Выручка:** "
                    f"{format_rubles(int(result['revenue_kopecks']))}"
                )

                st.write(
                    f"**Полные затраты на тираж:** "
                    f"{format_rubles(int(result['total_cost_kopecks']))}"
                )

                st.write(
                    f"**Результат на тираж:** "
                    f"{format_rubles(int(result['operating_result_kopecks']))}"
                )

                st.write(
                    f"**Фактическая маржинальность:** "
                    f"{margin_text}"
                )

                st.write(
                    f"**Точка безубыточности:** "
                    f"{break_even_text}"
                )

                chart_data = pd.DataFrame(
                    {
                        "Показатель": [
                            "Цена продажи",
                            "Базовая себестоимость",
                            "Процентные расходы",
                            "Прибыль",
                        ],
                        "Сумма, ₽": [
                            selling_price / 100,
                            int(
                                result[
                                    "base_cost_per_unit_kopecks"
                                ]
                            ) / 100,
                            percentage_cost_per_unit / 100,
                            profit_per_unit / 100,
                        ],
                    }
                )

                unit_chart = px.bar(
                    chart_data,
                    x="Показатель",
                    y="Сумма, ₽",
                    text_auto=".2s",
                )

                unit_chart.update_layout(
                    xaxis_title="",
                    yaxis_title="Сумма, ₽",
                )

                st.plotly_chart(
                    unit_chart,
                    use_container_width=True,
                )

        st.divider()
        st.subheader("Управление продуктом")

        selected_product_active = st.checkbox(
            "Продукт активен",
            value=bool(
                selected_product["is_active"]
            ),
            key=(
                "unit_product_active_"
                f"{selected_product_id}"
            ),
        )

        product_active_column, product_delete_column = (
            st.columns(2)
        )

        with product_active_column:
            if st.button(
                "Сохранить активность продукта",
                use_container_width=True,
                key=(
                    "save_unit_product_activity_"
                    f"{selected_product_id}"
                ),
            ):
                set_unit_economics_product_active(
                    product_id=selected_product_id,
                    is_active=selected_product_active,
                )

                st.session_state[
                    "unit_economics_message"
                ] = (
                    "Состояние продукта обновлено."
                )
                st.rerun()

        with product_delete_column:
            if st.button(
                "Удалить продукт",
                use_container_width=True,
                key=(
                    "delete_unit_product_"
                    f"{selected_product_id}"
                ),
            ):
                delete_unit_economics_product(
                    selected_product_id
                )

                st.session_state[
                    "unit_economics_message"
                ] = (
                    "Продукт и его строки "
                    "затрат удалены."
                )
                st.rerun()

        st.divider()
        st.subheader("Сводка по продуктам")

        if summary.empty:
            st.info(
                "Нет активных продуктов для сводного расчёта."
            )
        else:
            visible_summary = summary.copy()

            visible_summary["Способ цены"] = (
                visible_summary["pricing_method"]
                .map(PRICING_METHOD_LABELS)
                .fillna(
                    visible_summary["pricing_method"]
                )
            )

            money_columns = {
                "fixed_per_unit_kopecks":
                    "Фиксированные затраты на единицу, ₽",
                "allocated_period_per_unit_kopecks":
                    "Затраты периода на единицу, ₽",
                "base_cost_per_unit_kopecks":
                    "Базовая себестоимость, ₽",
                "selling_price_kopecks":
                    "Цена продажи, ₽",
                "percentage_cost_per_unit_kopecks":
                    "Процентные расходы на единицу, ₽",
                "total_cost_per_unit_kopecks":
                    "Полная себестоимость, ₽",
                "profit_per_unit_kopecks":
                    "Прибыль на единицу, ₽",
                "revenue_kopecks":
                    "Выручка, ₽",
                "operating_result_kopecks":
                    "Результат на тираж, ₽",
            }

            for source_column, visible_column in (
                    money_columns.items()
            ):
                visible_summary[visible_column] = (
                        pd.to_numeric(
                            visible_summary[source_column],
                            errors="coerce",
                        ) / 100
                )

            visible_summary["Маржинальность, %"] = (
                pd.to_numeric(
                    visible_summary["margin_percent"],
                    errors="coerce",
                )
            )

            visible_summary[
                "Процентные расходы, %"
            ] = pd.to_numeric(
                visible_summary["percentage_cost_rate"],
                errors="coerce",
            )

            visible_summary[
                "Точка безубыточности, шт."
            ] = pd.to_numeric(
                visible_summary["break_even_units"],
                errors="coerce",
            )

            visible_summary["Статус расчёта"] = (
                visible_summary["pricing_error"]
                .fillna("Расчёт выполнен")
                .replace("", "Расчёт выполнен")
            )

            visible_summary = visible_summary.rename(
                columns={
                    "product_name": "Продукт",
                    "planned_units": "План, шт.",
                }
            )

            st.dataframe(
                visible_summary[
                    [
                        "Продукт",
                        "План, шт.",
                        "Способ цены",
                        "Фиксированные затраты на единицу, ₽",
                        "Затраты периода на единицу, ₽",
                        "Базовая себестоимость, ₽",
                        "Процентные расходы, %",
                        "Цена продажи, ₽",
                        "Полная себестоимость, ₽",
                        "Прибыль на единицу, ₽",
                        "Маржинальность, %",
                        "Выручка, ₽",
                        "Результат на тираж, ₽",
                        "Точка безубыточности, шт.",
                        "Статус расчёта",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Фиксированные затраты на единицу, ₽":
                        st.column_config.NumberColumn(
                            "Фиксированные затраты на единицу, ₽",
                            format="%.2f",
                        ),
                    "Затраты периода на единицу, ₽":
                        st.column_config.NumberColumn(
                            "Затраты периода на единицу, ₽",
                            format="%.2f",
                        ),
                    "Базовая себестоимость, ₽":
                        st.column_config.NumberColumn(
                            "Базовая себестоимость, ₽",
                            format="%.2f",
                        ),
                    "Процентные расходы, %":
                        st.column_config.NumberColumn(
                            "Процентные расходы, %",
                            format="%.2f%%",
                        ),
                    "Цена продажи, ₽":
                        st.column_config.NumberColumn(
                            "Цена продажи, ₽",
                            format="%.2f",
                        ),
                    "Полная себестоимость, ₽":
                        st.column_config.NumberColumn(
                            "Полная себестоимость, ₽",
                            format="%.2f",
                        ),
                    "Прибыль на единицу, ₽":
                        st.column_config.NumberColumn(
                            "Прибыль на единицу, ₽",
                            format="%.2f",
                        ),
                    "Маржинальность, %":
                        st.column_config.NumberColumn(
                            "Маржинальность, %",
                            format="%.1f%%",
                        ),
                    "Выручка, ₽":
                        st.column_config.NumberColumn(
                            "Выручка, ₽",
                            format="%.2f",
                        ),
                    "Результат на тираж, ₽":
                        st.column_config.NumberColumn(
                            "Результат на тираж, ₽",
                            format="%.2f",
                        ),
                    "Точка безубыточности, шт.":
                        st.column_config.NumberColumn(
                            "Точка безубыточности, шт.",
                            format="%d",
                        ),
                },
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
            "Имя файла",
            uploaded_file.name,
        )

        file_info_columns[1].metric(
            "Размер",
            (
                f"{len(uploaded_bytes) / 1024:.1f} КБ"
            ),
        )

        file_info_columns[2].metric(
            "SHA-256",
            source_sha256[:12] + "…",
            help=source_sha256,
        )

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
                ] = (
                    f"Импорт #{save_result.import_batch_id}. "
                    f"Получено операций: "
                    f"{save_result.received}. "
                    f"Добавлено новых: "
                    f"{save_result.inserted}. "
                    f"Пропущено дублей: "
                    f"{save_result.duplicates}."
                )

                st.rerun()
    st.divider()
    st.subheader("Управление банковскими данными")

    import_batches = get_import_batches_dataframe()
    untracked_count = get_untracked_transaction_count()
    total_transaction_count = len(
        get_transactions_dataframe()
    )

    management_metrics = st.columns(3)

    management_metrics[0].metric(
        "Загрузок в журнале",
        len(import_batches),
    )

    management_metrics[1].metric(
        "Операций без журнала",
        untracked_count,
    )

    management_metrics[2].metric(
        "Всего банковских операций",
        total_transaction_count,
    )

    st.caption(
        "Операции без журнала были загружены до появления "
        "учёта банковских импортов."
    )

    if import_batches.empty:
        st.info(
            "В журнале пока нет сохранённых импортов."
        )
    else:
        st.markdown("#### Журнал импортов")

        import_history = import_batches.copy()

        import_history["Импортирован"] = (
            pd.to_datetime(
                import_history["imported_at"],
                errors="coerce",
            ).dt.strftime("%d.%m.%Y %H:%M")
        )

        import_history["Размер, КБ"] = (
            pd.to_numeric(
                import_history["source_size_bytes"],
                errors="coerce",
            ) / 1024
        )

        import_history = import_history.rename(
            columns={
                "id": "ID",
                "source_filename": "Файл",
                "received_count": "Получено",
                "inserted_count": "Добавлено",
                "duplicate_count": "Дубли",
                "linked_transaction_count":
                    "Связано операций",
            }
        )

        st.dataframe(
            import_history[
                [
                    "ID",
                    "Файл",
                    "Импортирован",
                    "Размер, КБ",
                    "Получено",
                    "Добавлено",
                    "Дубли",
                    "Связано операций",
                ]
            ],
            use_container_width=True,
            hide_index=True,
            column_config={
                "ID": st.column_config.NumberColumn(
                    "ID",
                    format="%d",
                ),
                "Размер, КБ":
                    st.column_config.NumberColumn(
                        "Размер, КБ",
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
                imported_at_text = (
                    "дата неизвестна"
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
            "Выберите импорт",
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

        selected_warnings = text_or_empty(
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
            "#### Операции выбранного импорта"
        )

        if selected_transactions.empty:
            st.info(
                "С выбранным импортом не связано операций."
            )
        else:
            transaction_view = (
                selected_transactions.copy()
            )

            transaction_view["Дата"] = (
                pd.to_datetime(
                    transaction_view["posted_at"],
                    errors="coerce",
                ).dt.strftime("%d.%m.%Y")
            )

            transaction_view["Сумма, ₽"] = (
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
                        "id": "ID",
                        "counterparty_name":
                            "Контрагент",
                        "description": "Описание",
                        "payment_purpose":
                            "Назначение платежа",
                        "classification_status":
                            "Классификация",
                    }
                )
            )

            st.dataframe(
                transaction_view[
                    [
                        "ID",
                        "Дата",
                        "Сумма, ₽",
                        "Контрагент",
                        "Описание",
                        "Назначение платежа",
                        "Классификация",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "ID":
                        st.column_config.NumberColumn(
                            "ID",
                            format="%d",
                        ),
                    "Сумма, ₽":
                        st.column_config.NumberColumn(
                            "Сумма, ₽",
                            format="%.2f",
                        ),
                },
            )

        st.markdown(
            "#### Удаление выбранного импорта"
        )

        st.caption(
            "Операции, связанные также с другой выпиской, "
            "останутся в базе."
        )

        delete_batch_phrase = (
            f"УДАЛИТЬ ИМПОРТ {selected_batch_id}"
        )

        delete_batch_confirmation = st.text_input(
            "Для удаления введите:",
            placeholder=delete_batch_phrase,
            key=(
                "delete_import_batch_confirmation_"
                f"{selected_batch_id}"
            ),
        )

        if st.button(
            "Удалить выбранный импорт",
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
                ] = (
                    f"Импорт "
                    f"#{delete_result.import_batch_id} "
                    f"удалён. Удалено связей: "
                    f"{delete_result.links_deleted}. "
                    f"Удалено банковских операций: "
                    f"{delete_result.transactions_deleted}."
                )

                st.rerun()

    if untracked_count > 0:
        st.divider()
        st.markdown(
            "#### Операции без журнала импорта"
        )

        st.warning(
            f"Найдено операций, загруженных до появления "
            f"журнала импортов: {untracked_count}. "
            "Их можно удалить отдельно."
        )

        delete_untracked_phrase = (
            "УДАЛИТЬ ОПЕРАЦИИ БЕЗ ЖУРНАЛА"
        )

        delete_untracked_confirmation = (
            st.text_input(
                "Для удаления старых операций введите:",
                placeholder=delete_untracked_phrase,
                key="delete_untracked_confirmation",
            )
        )

        if st.button(
            "Удалить операции без журнала",
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
            ] = (
                "Удалены операции без журнала импорта: "
                f"{deleted_count}."
            )

            st.rerun()

    st.divider()

    with st.expander(
        "Опасная зона: полная очистка банковских данных",
        expanded=False,
    ):
        st.warning(
            "Будут удалены все банковские операции, "
            "журналы импортов и связи между ними. "
            "Правила, платёжный календарь и "
            "Unit Economics останутся."
        )

        clear_phrase = (
            "УДАЛИТЬ ВСЕ БАНКОВСКИЕ ДАННЫЕ"
        )

        clear_confirmation = st.text_input(
            "Для полной очистки введите:",
            placeholder=clear_phrase,
            key="clear_bank_data_confirmation",
        )

        if st.button(
            "Полностью очистить банковские данные",
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
            ] = (
                "Банковские данные очищены. "
                f"Удалено импортов: "
                f"{clear_result.import_batches_deleted}; "
                f"связей: "
                f"{clear_result.links_deleted}; "
                f"операций: "
                f"{clear_result.transactions_deleted}."
            )

            st.rerun()