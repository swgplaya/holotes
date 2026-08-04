import hashlib
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO
from pathlib import Path
from html import escape

import pandas as pd
import streamlit as st
import plotly.express as px

from src.i18n import (
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
    translate,
)

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
from src.ui.operations import (
    render_operations_tab,
)
from src.ui.transaction_views import (
    prepare_visible_table,
    show_metrics,
)
from src.ui.classification import (
    bool_to_action,
    format_report_action,
    option_index,
    prepare_classification_editor,
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

LANGUAGE_STATE_KEY = "ui_language"
MAIN_NAVIGATION_KEY = "main_navigation"

MAIN_TAB_TRANSLATION_KEYS = (
    "tabs.operations",
    "tabs.classification",
    "tabs.rules",
    "tabs.pnl",
    "tabs.cash_flow",
    "tabs.unit_economics",
    "tabs.payment_calendar",
    "tabs.import",
)


def t(
    key: str,
    **values: object,
) -> str:
    """Возвращает перевод для текущего языка."""

    return translate(
        key=key,
        language=st.session_state.get(
            LANGUAGE_STATE_KEY,
            DEFAULT_LANGUAGE,
        ),
        **values,
    )

def sync_main_navigation_language() -> None:
    """Сохраняет активный раздел при смене языка."""

    active_label = st.session_state.get(
        MAIN_NAVIGATION_KEY
    )

    if active_label is None:
        return

    active_translation_key = None

    for translation_key in MAIN_TAB_TRANSLATION_KEYS:
        for language in SUPPORTED_LANGUAGES:
            translated_label = translate(
                key=translation_key,
                language=language,
            )

            if translated_label == active_label:
                active_translation_key = translation_key
                break

        if active_translation_key is not None:
            break

    if active_translation_key is None:
        return

    new_language = st.session_state.get(
        LANGUAGE_STATE_KEY,
        DEFAULT_LANGUAGE,
    )

    st.session_state[MAIN_NAVIGATION_KEY] = translate(
        key=active_translation_key,
        language=new_language,
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

RULE_DIRECTION_TRANSLATION_KEYS = {
    "any": "rules.options.direction.any",
    "income": "rules.options.direction.income",
    "expense": "rules.options.direction.expense",
}


RULE_FIELD_TRANSLATION_KEYS = {
    "all_text":
        "rules.options.field.all_text",
    "counterparty_name":
        "rules.options.field.counterparty_name",
    "counterparty_inn":
        "rules.options.field.counterparty_inn",
    "bank_category":
        "rules.options.field.bank_category",
    "description":
        "rules.options.field.description",
    "payment_purpose":
        "rules.options.field.payment_purpose",
    "mcc":
        "rules.options.field.mcc",
    "tax_code":
        "rules.options.field.tax_code",
}


RULE_MATCH_TRANSLATION_KEYS = {
    "contains":
        "rules.options.match.contains",
    "equals":
        "rules.options.match.equals",
    "starts_with":
        "rules.options.match.starts_with",
}

def format_rule_option(
    value: object,
    *,
    translation_keys: dict[str, str],
    fallback_labels: dict[str, str],
) -> str:
    """Возвращает локализованную подпись параметра правила."""

    value_text = str(value).strip()
    option_key = value_text

    if option_key not in fallback_labels:
        reverse_labels = {
            label: key
            for key, label in fallback_labels.items()
        }

        option_key = reverse_labels.get(
            value_text,
            value_text,
        )

    translation_key = translation_keys.get(
        option_key
    )

    if translation_key is not None:
        return t(translation_key)

    return fallback_labels.get(
        option_key,
        value_text,
    )


def format_rule_direction(
    value: object,
) -> str:
    """Форматирует направление правила."""

    return format_rule_option(
        value,
        translation_keys=(
            RULE_DIRECTION_TRANSLATION_KEYS
        ),
        fallback_labels=DIRECTION_FILTERS,
    )


def format_rule_field(
    value: object,
) -> str:
    """Форматирует поле поиска правила."""

    return format_rule_option(
        value,
        translation_keys=(
            RULE_FIELD_TRANSLATION_KEYS
        ),
        fallback_labels=MATCH_FIELDS,
    )


def format_rule_match_type(
    value: object,
) -> str:
    """Форматирует условие правила."""

    return format_rule_option(
        value,
        translation_keys=(
            RULE_MATCH_TRANSLATION_KEYS
        ),
        fallback_labels=MATCH_TYPES,
    )

def format_rule_active_status(
    value: object,
) -> str:
    """Возвращает локализованный статус активности."""

    if (
        value is not None
        and not pd.isna(value)
        and bool(value)
    ):
        return t(
            "rules.saved.values.active"
        )

    return t(
        "rules.saved.values.inactive"
    )



UNIT_COST_TYPE_TRANSLATION_KEYS = {
    "fixed_per_unit": "unit.cost_type.fixed_per_unit",
    "fixed_period": "unit.cost_type.fixed_period",
    "percent_of_price": "unit.cost_type.percent_of_price",
    "percent_of_revenue": "unit.cost_type.percent_of_revenue",
}

UNIT_PRICING_METHOD_TRANSLATION_KEYS = {
    "not_set": "unit.pricing_method.not_set",
    "manual": "unit.pricing_method.manual",
    "markup": "unit.pricing_method.markup",
    "target_margin": "unit.pricing_method.target_margin",
}

CALENDAR_DIRECTION_TRANSLATION_KEYS = {
    "inflow": "calendar.direction.inflow",
    "outflow": "calendar.direction.outflow",
}

CALENDAR_RECURRENCE_TRANSLATION_KEYS = {
    "once": "calendar.recurrence.once",
    "monthly": "calendar.recurrence.monthly",
    "yearly": "calendar.recurrence.yearly",
}

UNIT_PRICING_ERROR_TRANSLATION_KEYS = {
    "Способ ценообразования не выбран.":
        "unit.pricing_error.not_set",
    "Не указана ручная цена.":
        "unit.pricing_error.manual_missing",
    "Не указана наценка.":
        "unit.pricing_error.markup_missing",
    "Сумма процентных расходов должна быть меньше 100%.":
        "unit.pricing_error.percentage_too_high",
    "Не указана целевая маржинальность.":
        "unit.pricing_error.margin_missing",
    (
        "Процентные расходы и целевая маржинальность "
        "вместе должны быть меньше 100%."
    ): "unit.pricing_error.margin_total_too_high",
    "Неизвестный способ ценообразования.":
        "unit.pricing_error.unknown_method",
}


def format_unit_cost_type(value: object) -> str:
    """Возвращает локализованный тип затрат."""

    return format_rule_option(
        value,
        translation_keys=(
            UNIT_COST_TYPE_TRANSLATION_KEYS
        ),
        fallback_labels=COST_TYPE_LABELS,
    )


def format_unit_pricing_method(value: object) -> str:
    """Возвращает локализованный способ ценообразования."""

    return format_rule_option(
        value,
        translation_keys=(
            UNIT_PRICING_METHOD_TRANSLATION_KEYS
        ),
        fallback_labels=PRICING_METHOD_LABELS,
    )


def format_calendar_direction(value: object) -> str:
    """Возвращает локализованное направление платежа."""

    return format_rule_option(
        value,
        translation_keys=(
            CALENDAR_DIRECTION_TRANSLATION_KEYS
        ),
        fallback_labels=DIRECTION_LABELS,
    )


def format_calendar_recurrence(value: object) -> str:
    """Возвращает локализованную периодичность."""

    return format_rule_option(
        value,
        translation_keys=(
            CALENDAR_RECURRENCE_TRANSLATION_KEYS
        ),
        fallback_labels=RECURRENCE_LABELS,
    )


def format_boolean_status(value: object) -> str:
    """Возвращает локализованный логический статус."""

    if (
        value is not None
        and not pd.isna(value)
        and bool(value)
    ):
        return t("common.yes")

    return t("common.no")


def localize_unit_pricing_error(value: object) -> str:
    """Локализует известную ошибку расчёта цены."""

    message = text_or_empty(value)
    translation_key = (
        UNIT_PRICING_ERROR_TRANSLATION_KEYS.get(
            message
        )
    )

    if translation_key is not None:
        return t(translation_key)

    return message


def text_or_empty(value: object) -> str:
    """Преобразует пустое значение базы в пустую строку."""

    if value is None or pd.isna(value):
        return ""

    return str(value).strip()

def prepare_report_details(
    transactions: pd.DataFrame,
    category_column: str,
) -> pd.DataFrame:
    """Подготавливает детализацию финансового отчёта."""

    details = transactions.copy()

    date_label = t(
        "operations.columns.date"
    )
    amount_label = t(
        "reports.columns.amount"
    )
    category_label = t(
        "reports.columns.category"
    )
    counterparty_label = t(
        "operations.columns.counterparty"
    )
    description_label = t(
        "operations.columns.description"
    )
    payment_purpose_label = t(
        "operations.columns.payment_purpose"
    )

    details["posted_at"] = pd.to_datetime(
        details["posted_at"],
        errors="coerce",
    )

    details[date_label] = details[
        "posted_at"
    ].dt.strftime("%d.%m.%Y")

    details[amount_label] = (
        details["signed_amount_kopecks"] / 100
    )

    details[category_label] = (
        details[category_column]
        .fillna("")
        .replace(
            "",
            t("reports.columns.no_category"),
        )
    )

    details[counterparty_label] = (
        details["counterparty_name"]
        .fillna("")
    )

    details[description_label] = (
        details["description"]
        .fillna("")
    )

    details[payment_purpose_label] = (
        details["payment_purpose"]
        .fillna("")
    )

    return details[
        [
            date_label,
            amount_label,
            category_label,
            counterparty_label,
            description_label,
            payment_purpose_label,
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

    return t(
        "reports.percentage_point_delta",
        value=difference,
    )

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

    st.subheader(
        t("reports.pnl.kpi_title")
    )

    first_row = st.columns(4)

    first_row[0].metric(
        t("reports.pnl.kpi.profitability"),
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
        t("reports.pnl.kpi.expense_share"),
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
        t("reports.pnl.kpi.expense_coverage"),
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
        t("reports.pnl.kpi.classification_rate"),
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
        t("reports.pnl.kpi.average_income"),
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
        t("reports.pnl.kpi.average_expense"),
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
        t("reports.pnl.kpi.income_count"),
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
        t("reports.pnl.kpi.expense_count"),
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
        t("reports.pnl.kpi_caption")
    )

def style_report_chart(
    chart,
    *,
    show_legend: bool = False,
) -> None:
    """Применяет единый стиль к финансовым графикам."""

    layout_options = {
        "height": 420,
        "margin": {
            "l": 16,
            "r": 16,
            "t": 32,
            "b": 16,
        },
        "bargap": 0.22,
        "hovermode": (
            "x unified"
            if show_legend
            else "closest"
        ),
        "showlegend": show_legend,
    }

    if show_legend:
        layout_options["legend"] = {
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "left",
            "x": 0,
            "title_text": "",
        }

    chart.update_layout(
        **layout_options
    )

    chart.update_xaxes(
        title_text="",
        showgrid=False,
        automargin=True,
        tickangle=-15,
    )

    chart.update_yaxes(
        title_text=t(
            "reports.columns.amount"
        ),
        automargin=True,
        gridcolor="rgba(128, 128, 128, 0.18)",
        zerolinecolor="rgba(128, 128, 128, 0.30)",
    )

    chart.update_traces(
        marker_line_width=0,
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
        t("reports.metrics.included"),
        report.included_count,
        delta=count_delta,
    )

    st.caption(
        t(
            "reports.current_summary",
            label=current_label,
            excluded=report.excluded_count,
            pending=report.pending_count,
        )
    )

    if (
        comparison_report is not None
        and comparison_label is not None
    ):
        st.caption(
            t(
                "reports.comparison_summary",
                label=comparison_label,
                included=(
                    comparison_report.included_count
                ),
                excluded=(
                    comparison_report.excluded_count
                ),
                pending=(
                    comparison_report.pending_count
                ),
            )
        )

    if report.pending_count:
        st.warning(
            t("reports.pending_warning")
        )

    if report_type == "pnl":
        show_pnl_kpis(
            report=report,
            comparison_report=comparison_report,
        )

    if report.transactions.empty:
        st.info(
            t("reports.empty_period")
        )

        if comparison_report is None:
            return

    st.subheader(
        t("reports.category_structure")
    )

    category_label = t(
        "reports.columns.category"
    )
    amount_label = t(
        "reports.columns.amount"
    )
    current_amount_label = t(
        "reports.columns.current_amount"
    )
    comparison_amount_label = t(
        "reports.columns.comparison_amount"
    )
    delta_amount_label = t(
        "reports.columns.delta_amount"
    )
    delta_percent_label = t(
        "reports.columns.delta_percent"
    )
    period_label = t(
        "reports.columns.period"
    )

    if comparison_report is None:
        category_table = (
            report.category_totals.copy()
        )

        category_table[amount_label] = (
            category_table[
                "amount_kopecks"
            ] / 100
        )

        category_table = category_table.rename(
            columns={
                "category": category_label,
            }
        )

        if category_table.empty:
            st.info(
                t("reports.no_category_data")
            )
        else:
            chart = px.bar(
                category_table,
                x=category_label,
                y=amount_label,
                text_auto=".2s",
            )

            style_report_chart(chart)

            st.plotly_chart(
                chart,
                use_container_width=True,
            )

            st.dataframe(
                category_table[
                    [
                        category_label,
                        amount_label,
                    ]
                ],
                use_container_width=True,
                hide_index=True,
                column_config={
                    amount_label:
                        st.column_config.NumberColumn(
                            amount_label,
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
            current_amount_label
        ] = (
            comparison_table[
                "current_amount_kopecks"
            ] / 100
        )

        comparison_table[
            comparison_amount_label
        ] = (
            comparison_table[
                "comparison_amount_kopecks"
            ] / 100
        )

        comparison_table[delta_amount_label] = (
            comparison_table[
                "delta_kopecks"
            ] / 100
        )

        comparison_table = (
            comparison_table.rename(
                columns={
                    "category": category_label,
                    "change_percent":
                        delta_percent_label,
                }
            )
        )

        if comparison_table.empty:
            st.info(
                t("reports.no_comparison_data")
            )
        else:
            chart_data = comparison_table[
                [
                    category_label,
                    current_amount_label,
                    comparison_amount_label,
                ]
            ].melt(
                id_vars=category_label,
                var_name=period_label,
                value_name=amount_label,
            )

            comparison_chart = px.bar(
                chart_data,
                x=category_label,
                y=amount_label,
                color=period_label,
                barmode="group",
            )

            style_report_chart(
                comparison_chart,
                show_legend=True,
            )

            st.plotly_chart(
                comparison_chart,
                use_container_width=True,
            )

            st.dataframe(
                comparison_table[
                    [
                        category_label,
                        current_amount_label,
                        comparison_amount_label,
                        delta_amount_label,
                        delta_percent_label,
                    ]
                ],
                use_container_width=True,
                hide_index=True,
                column_config={
                    current_amount_label:
                        st.column_config.NumberColumn(
                            current_amount_label,
                            format="%.2f",
                        ),
                    comparison_amount_label:
                        st.column_config.NumberColumn(
                            comparison_amount_label,
                            format="%.2f",
                        ),
                    delta_amount_label:
                        st.column_config.NumberColumn(
                            delta_amount_label,
                            format="%.2f",
                        ),
                    delta_percent_label:
                        st.column_config.NumberColumn(
                            delta_percent_label,
                            format="%.1f%%",
                        ),
                },
            )

    if not report.transactions.empty:
        with st.expander(
            t("reports.current_operations"),
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
                    amount_label:
                        st.column_config.NumberColumn(
                            amount_label,
                            format="%.2f",
                        ),
                },
            )

    if (
        comparison_report is not None
        and not comparison_report.transactions.empty
    ):
        with st.expander(
            t("reports.comparison_operations"),
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
                    amount_label:
                        st.column_config.NumberColumn(
                            amount_label,
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
            t("reports.empty_database")
        )
        return

    posted_dates = pd.to_datetime(
        transactions["posted_at"],
        errors="coerce",
    ).dropna()

    if posted_dates.empty:
        st.error(
            t("reports.invalid_dates")
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
        st.markdown(
            f"#### {t('reports.period.title')}"
        )

        start_column, end_column, comparison_column = (
            st.columns(
                [1, 1, 1.25],
                gap="medium",
            )
        )

        with start_column:
            start_date = st.date_input(
                t("reports.period.start"),
                min_value=min_date,
                max_value=max_date,
                format="DD.MM.YYYY",
                key=start_widget_key,
                on_change=_sync_report_start_date,
                args=(start_widget_key,),
            )

        with end_column:
            end_date = st.date_input(
                t("reports.period.end"),
                min_value=min_date,
                max_value=max_date,
                format="DD.MM.YYYY",
                key=end_widget_key,
                on_change=_sync_report_end_date,
                args=(end_widget_key,),
            )

        with comparison_column:
            comparison_mode = st.selectbox(
                t("reports.period.compare"),
                options=list(COMPARISON_MODES),
                format_func=lambda mode: t(
                    f"reports.comparison.{mode}"
                ),
                key=comparison_widget_key,
                on_change=(
                    _sync_report_comparison_mode
                ),
                args=(comparison_widget_key,),
            )

        st.caption(
            t("reports.period.synced")
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
        inflow_label = t(
            "reports.pnl.inflow"
        )
        outflow_label = t(
            "reports.pnl.outflow"
        )
        net_label = t(
            "reports.pnl.net"
        )

    elif report_type == "cash_flow":
        report_builder = build_cash_flow_report
        category_column = "cf_category"
        inflow_label = t(
            "reports.cash_flow.inflow"
        )
        outflow_label = t(
            "reports.cash_flow.outflow"
        )
        net_label = t(
            "reports.cash_flow.net"
        )

    else:
        raise ValueError(
            t(
                "reports.unknown_type",
                report_type=report_type,
            )
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
            t(
                "reports.period.current",
                current=current_label,
            )
        )
    else:
        st.caption(
            t(
                "reports.period.with_comparison",
                current=current_label,
                comparison=comparison_label,
            )
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

if LANGUAGE_STATE_KEY not in st.session_state:
    st.session_state[
        LANGUAGE_STATE_KEY
    ] = DEFAULT_LANGUAGE


_, language_column = st.columns(
    [5, 1],
    vertical_alignment="center",
)

with language_column:
    st.selectbox(
        t("language.selector"),
        options=list(SUPPORTED_LANGUAGES),
        format_func=SUPPORTED_LANGUAGES.get,
        key=LANGUAGE_STATE_KEY,
        on_change=sync_main_navigation_language,
        label_visibility="collapsed",
    )


hero_eyebrow = escape(
    t("app.eyebrow")
)

hero_description = escape(
    t("app.description")
)

hero_badge = escape(
    t("app.badge")
)


st.html(
    f"""
    <section class="openmas-hero">
        <div class="openmas-hero__content">
            <div class="openmas-hero__eyebrow">
                {hero_eyebrow}
            </div>

            <h1 class="openmas-hero__title">
                Open MAS
            </h1>

            <p class="openmas-hero__description">
                {hero_description}
            </p>
        </div>

        <div class="openmas-hero__badge">
            {hero_badge}
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
        t(translation_key)
        for translation_key in MAIN_TAB_TRANSLATION_KEYS
    ],
    key=MAIN_NAVIGATION_KEY,
    on_change="rerun",
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

if operations_tab.open:
    with operations_tab:
        render_operations_tab(
            t=t,
            format_rubles=format_rubles,
        )

if classification_tab.open:
    with classification_tab:
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

if rules_tab.open:
    with rules_tab:
        st.subheader(
            t("rules.title")
        )

        st.caption(
            t("rules.caption")
        )

        if st.button(
            t("rules.apply_button"),
            type="primary",
            use_container_width=True,
        ):
            apply_result = (
                apply_classification_rules()
            )

            st.session_state["rule_message"] = t(
                "rules.messages.applied",
                checked=apply_result.checked,
                matched=apply_result.matched,
                unmatched=apply_result.unmatched,
            )

            st.rerun()

        with st.expander(
            t("rules.create_title"),
            expanded=True,
        ):
            with st.form("create_rule_form"):
                rule_name = st.text_input(
                    t("rules.fields.name"),
                    placeholder=t(
                        "rules.placeholders.name"
                    ),
                )

                priority = st.number_input(
                    t("rules.fields.priority"),
                    min_value=0,
                    max_value=10_000,
                    value=100,
                    step=10,
                    help=t(
                        "rules.help.priority"
                    ),
                )

                is_active = st.checkbox(
                    t("rules.fields.active"),
                    value=True,
                )

                direction_filter = st.selectbox(
                    t("rules.fields.direction"),
                    options=list(
                        DIRECTION_FILTERS
                    ),
                    format_func=(
                        format_rule_direction
                    ),
                )

                match_field = st.selectbox(
                    t("rules.fields.match_field"),
                    options=list(
                        MATCH_FIELDS
                    ),
                    format_func=(
                        format_rule_field
                    ),
                )

                match_type = st.selectbox(
                    t("rules.fields.match_type"),
                    options=list(
                        MATCH_TYPES
                    ),
                    format_func=(
                        format_rule_match_type
                    ),
                )

                match_value = st.text_input(
                    t("rules.fields.match_value"),
                    placeholder=t(
                        "rules.placeholders."
                        "match_value"
                    ),
                )

                pnl_column, cf_column = (
                    st.columns(2)
                )

                with pnl_column:
                    st.markdown(
                        "**"
                        + t("reports.pnl.title")
                        + "**"
                    )

                    pnl_action = st.selectbox(
                        t(
                            "classification.columns."
                            "pnl_action"
                        ),
                        options=list(
                            REPORT_ACTIONS
                        ),
                        format_func=lambda value: (
                            format_report_action(
                                value,
                                t=t,
                            )
                        ),
                        key="rule_pnl_action",
                    )

                    pnl_category = st.selectbox(
                        t(
                            "classification.columns."
                            "pnl_category"
                        ),
                        options=list(
                            PNL_CATEGORIES
                        ),
                        key="rule_pnl_category",
                    )

                with cf_column:
                    st.markdown(
                        "**"
                        + t(
                            "reports.cash_flow.title"
                        )
                        + "**"
                    )

                    cf_action = st.selectbox(
                        t(
                            "classification.columns."
                            "cf_action"
                        ),
                        options=list(
                            REPORT_ACTIONS
                        ),
                        format_func=lambda value: (
                            format_report_action(
                                value,
                                t=t,
                            )
                        ),
                        key="rule_cf_action",
                    )

                    cf_category = st.selectbox(
                        t(
                            "classification.columns."
                            "cf_category"
                        ),
                        options=list(
                            CF_CATEGORIES
                        ),
                        key="rule_cf_category",
                    )

                create_rule_submitted = (
                    st.form_submit_button(
                        t("rules.create_button"),
                        type="primary",
                        use_container_width=True,
                    )
                )

                if create_rule_submitted:
                    validation_errors: list[str] = []

                    if not rule_name.strip():
                        validation_errors.append(
                            t(
                                "rules.errors."
                                "name_required"
                            )
                        )

                    if not match_value.strip():
                        validation_errors.append(
                            t(
                                "rules.errors."
                                "match_value_required"
                            )
                        )

                    if (
                        pnl_action
                        == UNDEFINED_ACTION
                        and cf_action
                        == UNDEFINED_ACTION
                    ):
                        validation_errors.append(
                            t(
                                "rules.errors."
                                "decision_required"
                            )
                        )

                    if (
                        pnl_action
                        == INCLUDE_ACTION
                        and not pnl_category
                    ):
                        validation_errors.append(
                            t(
                                "rules.errors."
                                "pnl_category_required"
                            )
                        )

                    if (
                        cf_action
                        == INCLUDE_ACTION
                        and not cf_category
                    ):
                        validation_errors.append(
                            t(
                                "rules.errors."
                                "cf_category_required"
                            )
                        )

                    if validation_errors:
                        for error_message in (
                            validation_errors
                        ):
                            st.error(error_message)

                    else:
                        try:
                            new_rule_id = create_rule(
                                name=rule_name,
                                priority=int(priority),
                                is_active=is_active,
                                direction_filter=(
                                    direction_filter
                                ),
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
                            st.session_state[
                                "rule_message"
                            ] = t(
                                "rules.messages.created",
                                rule_id=new_rule_id,
                            )

                            st.rerun()

        st.divider()

        st.subheader(
            t("rules.transfer.title")
        )

        st.caption(
            t("rules.transfer.caption")
        )

        export_json = export_rule_config_json()

        export_column, export_info_column = (
            st.columns([1, 2])
        )

        with export_column:
            st.download_button(
                t("rules.transfer.download"),
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
                t("rules.transfer.export_info")
            )

        uploaded_rule_config = st.file_uploader(
            t("rules.transfer.upload"),
            type=["json"],
            help=t(
                "rules.transfer.upload_help"
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
                    "#### "
                    + t(
                        "rules.transfer.preview_title"
                    )
                )

                preview_metrics = st.columns(4)

                preview_metrics[0].metric(
                    t(
                        "rules.transfer.metrics."
                        "received"
                    ),
                    rule_preview.received,
                )

                preview_metrics[1].metric(
                    t(
                        "rules.transfer.metrics."
                        "valid"
                    ),
                    rule_preview.valid_unique,
                )

                preview_metrics[2].metric(
                    t(
                        "rules.transfer.metrics."
                        "file_duplicates"
                    ),
                    rule_preview.duplicates_in_file,
                )

                preview_metrics[3].metric(
                    t(
                        "rules.transfer.metrics."
                        "database_duplicates"
                    ),
                    rule_preview.duplicates_in_database,
                )

                st.caption(
                    t(
                        "rules.transfer."
                        "preview_caption",
                        schema_version=(
                            parsed_rule_config.schema_version
                        ),
                        exported_at=(
                            parsed_rule_config.exported_at
                        ),
                    )
                )

                if rule_preview.errors:
                    st.error(
                        t(
                            "rules.transfer.errors."
                            "blocked"
                        )
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
                        t(
                            "rules.transfer.warnings."
                            "file_duplicates"
                        )
                    )

                if (
                        rule_preview.duplicates_in_database
                        > 0
                ):
                    st.info(
                        t(
                            "rules.transfer.info."
                            "database_duplicates"
                        )
                    )

                with st.expander(
                        t(
                            "rules.transfer.json_title"
                        ),
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

                st.markdown(
                    "#### "
                    + t(
                        "rules.transfer.import_title"
                    )
                )

                import_mode_options = {
                    "merge": t(
                        "rules.transfer.import.merge"
                    ),
                    "replace": t(
                        "rules.transfer.import.replace"
                    ),
                }

                import_mode = st.radio(
                    t(
                        "rules.transfer.import_action"
                    ),
                    options=list(
                        import_mode_options
                    ),
                    format_func=(
                        import_mode_options.get
                    ),
                    horizontal=True,
                    key="rule_import_mode",
                )

                if import_mode == "merge":
                    st.caption(
                        t(
                            "rules.transfer.import."
                            "merge_caption"
                        )
                    )

                    replace_confirmation_valid = True

                else:
                    st.warning(
                        t(
                            "rules.transfer.import."
                            "replace_warning"
                        )
                    )

                    replace_phrase = t(
                        "rules.transfer.import."
                        "replace_phrase"
                    )

                    replace_confirmation = (
                        st.text_input(
                            t(
                                "rules.transfer.import."
                                "confirmation"
                            ),
                            placeholder=replace_phrase,
                            key=(
                                "replace_rules_confirmation"
                            ),
                        )
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
                    t(
                        "rules.transfer.import."
                        "merge_button"
                    )
                    if import_mode == "merge"
                    else t(
                        "rules.transfer.import."
                        "replace_button"
                    )
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
                        ] = t(
                            "rules.transfer.messages."
                            "completed",
                            received=(
                                rule_import_result.received
                            ),
                            inserted=(
                                rule_import_result.inserted
                            ),
                            skipped=(
                                rule_import_result
                                .skipped_duplicates
                            ),
                            deleted=(
                                rule_import_result
                                .deleted_existing
                            ),
                        )

                        st.rerun()

            rules = get_rules_dataframe()

            st.subheader(
                t("rules.saved.title")
            )

            if rules.empty:
                st.info(
                    t("rules.saved.empty")
                )

            else:
                visible_rules = rules.copy()

                visible_rules[
                    "direction_filter"
                ] = visible_rules[
                    "direction_filter"
                ].apply(
                    format_rule_direction
                )

                visible_rules[
                    "match_field"
                ] = visible_rules[
                    "match_field"
                ].apply(
                    format_rule_field
                )

                visible_rules[
                    "match_type"
                ] = visible_rules[
                    "match_type"
                ].apply(
                    format_rule_match_type
                )

                visible_rules[
                    "pnl_action"
                ] = visible_rules[
                    "pnl_action"
                ].apply(
                    lambda value: format_report_action(
                        value,
                        t=t,
                    )
                )

                visible_rules[
                    "cf_action"
                ] = visible_rules[
                    "cf_action"
                ].apply(
                    lambda value: format_report_action(
                        value,
                        t=t,
                    )
                )

                visible_rules[
                    "is_active"
                ] = visible_rules[
                    "is_active"
                ].apply(
                    format_rule_active_status
                )

                id_column = t(
                    "rules.saved.columns.id"
                )
                name_column = t(
                    "rules.saved.columns.name"
                )
                priority_column = t(
                    "rules.saved.columns.priority"
                )
                active_column = t(
                    "rules.saved.columns.active"
                )
                direction_column = t(
                    "rules.saved.columns.direction"
                )
                field_column = t(
                    "rules.saved.columns.field"
                )
                condition_column = t(
                    "rules.saved.columns.condition"
                )
                value_column = t(
                    "rules.saved.columns.value"
                )
                pnl_action_column = t(
                    "rules.saved.columns.pnl_action"
                )
                pnl_category_column = t(
                    "rules.saved.columns.pnl_category"
                )
                cf_action_column = t(
                    "rules.saved.columns.cf_action"
                )
                cf_category_column = t(
                    "rules.saved.columns.cf_category"
                )

                visible_rules = visible_rules.rename(
                    columns={
                        "id": id_column,
                        "name": name_column,
                        "priority": priority_column,
                        "is_active": active_column,
                        "direction_filter":
                            direction_column,
                        "match_field": field_column,
                        "match_type": condition_column,
                        "match_value": value_column,
                        "pnl_action": pnl_action_column,
                        "pnl_category":
                            pnl_category_column,
                        "cf_action": cf_action_column,
                        "cf_category":
                            cf_category_column,
                    }
                )

                visible_rule_columns = [
                    id_column,
                    name_column,
                    priority_column,
                    active_column,
                    direction_column,
                    field_column,
                    condition_column,
                    value_column,
                    pnl_action_column,
                    pnl_category_column,
                    cf_action_column,
                    cf_category_column,
                ]

                st.dataframe(
                    visible_rules[
                        visible_rule_columns
                    ],
                    use_container_width=True,
                    hide_index=True,
                )

                rule_options = {
                    (
                        f"{int(row['id'])} — "
                        f"{row['name']}"
                    ): int(row["id"])
                    for _, row in rules.iterrows()
                }

                selected_rule_label = st.selectbox(
                    t("rules.saved.manage"),
                    options=list(rule_options),
                )

                selected_rule_id = rule_options[
                    selected_rule_label
                ]

                selected_rule = rules.loc[
                    rules["id"] == selected_rule_id
                    ].iloc[0]

                selected_rule_active = st.checkbox(
                    t("rules.fields.active"),
                    value=bool(
                        selected_rule["is_active"]
                    ),
                    key=(
                        "selected_rule_active_"
                        f"{selected_rule_id}"
                    ),
                )

                action_column, delete_column = (
                    st.columns(2)
                )

                with action_column:
                    if st.button(
                            t(
                                "rules.saved."
                                "save_activity"
                            ),
                            use_container_width=True,
                            key=(
                                    "save_rule_activity_"
                                    f"{selected_rule_id}"
                            ),
                    ):
                        set_rule_active(
                            rule_id=selected_rule_id,
                            is_active=(
                                selected_rule_active
                            ),
                        )

                        st.session_state[
                            "rule_message"
                        ] = t(
                            "rules.messages."
                            "activity_updated"
                        )

                        st.rerun()

                with delete_column:
                    if st.button(
                            t("rules.saved.delete"),
                            type="secondary",
                            use_container_width=True,
                            key=(
                                    "delete_rule_"
                                    f"{selected_rule_id}"
                            ),
                    ):
                        delete_rule(
                            selected_rule_id
                        )

                        st.session_state[
                            "rule_message"
                        ] = t(
                            "rules.messages.deleted"
                        )

                        st.rerun()

if pnl_tab.open:
    with pnl_tab:
        st.subheader(
            t("reports.pnl.title")
        )

        st.caption(
            t("reports.pnl.caption")
        )

        pnl_transactions = (
            get_transactions_dataframe()
        )

        show_financial_report(
            transactions=pnl_transactions,
            report_type="pnl",
            key_prefix="pnl",
        )

if cash_flow_tab.open:
    with cash_flow_tab:
        st.subheader(
            t("reports.cash_flow.title")
        )

        st.caption(
            t("reports.cash_flow.caption")
        )

        cash_flow_transactions = (
            get_transactions_dataframe()
        )

        show_financial_report(
            transactions=cash_flow_transactions,
            report_type="cash_flow",
            key_prefix="cash_flow",
        )

if unit_economics_tab.open:
    with unit_economics_tab:
        st.subheader(t("unit.title"))

        st.caption(t("unit.caption"))

        with st.expander(
            t("unit.product.add_title"),
            expanded=True,
        ):
            with st.form(
                "create_unit_economics_product_form",
                clear_on_submit=True,
            ):
                product_name = st.text_input(
                    t("unit.product.name"),
                    placeholder=t(
                        "unit.product.name_placeholder"
                    ),
                )

                planned_units = st.number_input(
                    t("unit.product.planned_units"),
                    min_value=1,
                    value=100,
                    step=1,
                )

                product_is_active = st.checkbox(
                    t("unit.product.active"),
                    value=True,
                )

                product_comment = st.text_area(
                    t("unit.product.comment"),
                    max_chars=500,
                )

                product_submitted = st.form_submit_button(
                    t("unit.product.add_button"),
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
                        ] = t(
                            "unit.product.added",
                            product_id=product_id,
                        )

                        st.rerun()

        products = (
            get_unit_economics_products_dataframe()
        )

        cost_items = (
            get_unit_economics_cost_items_dataframe()
        )

        if products.empty:
            st.info(t("unit.product.empty"))
        else:
            product_options = {
                (
                    f"{int(row['id'])} — "
                    f"{row['name']}"
                ): int(row["id"])
                for _, row in products.iterrows()
            }

            selected_product_label = st.selectbox(
                t("unit.product.select"),
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
                t(
                    "unit.costs.title",
                    product_name=selected_product["name"],
                )
            )

            with st.form(
                f"create_cost_item_form_"
                f"{selected_product_id}",
                clear_on_submit=True,
            ):
                cost_name = st.text_input(
                    t("unit.cost.name"),
                    placeholder=t(
                        "unit.cost.name_placeholder"
                    ),
                )

                calculation_type = st.selectbox(
                    t("unit.cost.type"),
                    options=list(COST_TYPE_LABELS),
                    format_func=format_unit_cost_type,
                )

                cost_amount_rubles: float | None
                percentage_value: float | None

                if calculation_type in {
                    "fixed_per_unit",
                    "fixed_period",
                }:
                    cost_amount_rubles = st.number_input(
                        t("common.amount_rub"),
                        min_value=0.00,
                        value=100.00,
                        step=10.00,
                        format="%.2f",
                    )

                    percentage_value = None

                else:
                    percentage_value = st.number_input(
                        t("common.percent"),
                        min_value=0.00,
                        max_value=99.99,
                        value=2.50,
                        step=0.10,
                        format="%.2f",
                    )

                    cost_amount_rubles = None

                cost_is_active = st.checkbox(
                    t("unit.cost.active"),
                    value=True,
                )

                cost_comment = st.text_area(
                    t("unit.cost.comment"),
                    max_chars=500,
                )

                cost_submitted = st.form_submit_button(
                    t("unit.cost.add_button"),
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
                        ] = t(
                            "unit.cost.added",
                            cost_id=cost_item_id,
                        )

                        st.rerun()

            selected_cost_items = cost_items.loc[
                cost_items["product_id"]
                == selected_product_id
            ].copy()

            if selected_cost_items.empty:
                st.info(t("unit.cost.empty"))
            else:
                visible_cost_items = (
                    selected_cost_items.copy()
                )

                id_column = t("common.id")
                item_column = t(
                    "unit.cost.item_column"
                )
                type_column = t("unit.cost.type")
                amount_column = t("common.amount_rub")
                percent_column = t("common.percent")
                active_column = t("common.active")
                comment_column = t("common.comment")

                visible_cost_items[type_column] = (
                    visible_cost_items[
                        "calculation_type"
                    ].apply(format_unit_cost_type)
                )

                visible_cost_items[amount_column] = (
                    pd.to_numeric(
                        visible_cost_items[
                            "amount_kopecks"
                        ],
                        errors="coerce",
                    ) / 100
                )

                visible_cost_items[percent_column] = (
                    pd.to_numeric(
                        visible_cost_items[
                            "percentage_bp"
                        ],
                        errors="coerce",
                    ) / 100
                )

                visible_cost_items[active_column] = (
                    visible_cost_items[
                        "is_active"
                    ].apply(format_boolean_status)
                )

                visible_cost_items = (
                    visible_cost_items.rename(
                        columns={
                            "id": id_column,
                            "name": item_column,
                            "comment": comment_column,
                        }
                    )
                )

                st.dataframe(
                    visible_cost_items[
                        [
                            id_column,
                            item_column,
                            type_column,
                            amount_column,
                            percent_column,
                            active_column,
                            comment_column,
                        ]
                    ],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        amount_column:
                            st.column_config.NumberColumn(
                                amount_column,
                                format="%.2f",
                            ),
                        percent_column:
                            st.column_config.NumberColumn(
                                percent_column,
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
                        t("unit.cost.select_manage"),
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
                        t("unit.cost.active"),
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
                        t("unit.cost.save_activity"),
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
                        ] = t(
                            "unit.cost.activity_updated"
                        )
                        st.rerun()

                with cost_delete_column:
                    if st.button(
                        t("unit.cost.delete"),
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
                        ] = t("unit.cost.deleted")
                        st.rerun()

            st.subheader(t("unit.pricing.title"))

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
                t("unit.pricing.method"),
                options=pricing_options,
                index=default_pricing_index,
                format_func=format_unit_pricing_method,
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
                    t("unit.pricing.manual_price"),
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
                        t("unit.pricing.markup")
                        if pricing_method == "markup"
                        else t(
                            "unit.pricing.target_margin"
                        )
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
                t("unit.pricing.rounding"),
                min_value=1.00,
                value=float(stored_rounding_step) / 100,
                step=10.00,
                format="%.2f",
                key=f"rounding_step_{selected_product_id}",
            )

            if st.button(
                t("unit.pricing.save"),
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
                    ] = t("unit.pricing.saved")

                    st.rerun()

            st.divider()
            st.subheader(t("unit.calculation.title"))

            summary = build_unit_economics_summary(
                products=products,
                cost_items=cost_items,
            )

            selected_summary = summary.loc[
                summary["product_id"] == selected_product_id
            ]

            if selected_summary.empty:
                st.warning(
                    t("unit.calculation.inactive")
                )
            else:
                result = selected_summary.iloc[0]

                base_metrics = st.columns(4)

                base_metrics[0].metric(
                    t("unit.metrics.fixed_per_unit"),
                    format_rubles(
                        int(result["fixed_per_unit_kopecks"])
                    ),
                )

                base_metrics[1].metric(
                    t("unit.metrics.allocated_period"),
                    format_rubles(
                        int(
                            result[
                                "allocated_period_per_unit_kopecks"
                            ]
                        )
                    ),
                )

                base_metrics[2].metric(
                    t("unit.metrics.base_cost"),
                    format_rubles(
                        int(
                            result[
                                "base_cost_per_unit_kopecks"
                            ]
                        )
                    ),
                )

                base_metrics[3].metric(
                    t("unit.metrics.percentage_rate"),
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
                    st.warning(
                        localize_unit_pricing_error(
                            pricing_error
                        )
                    )

                    st.info(
                        t("unit.calculation.setup_hint")
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
                        t("unit.metrics.selling_price"),
                        format_rubles(selling_price),
                    )

                    price_metrics[1].metric(
                        t(
                            "unit.metrics.percentage_per_unit"
                        ),
                        format_rubles(
                            percentage_cost_per_unit
                        ),
                    )

                    price_metrics[2].metric(
                        t("unit.metrics.total_cost"),
                        format_rubles(total_cost_per_unit),
                    )

                    price_metrics[3].metric(
                        t("unit.metrics.profit_per_unit"),
                        format_rubles(profit_per_unit),
                    )

                    margin_percent = result["margin_percent"]

                    if (
                        margin_percent is None
                        or pd.isna(margin_percent)
                    ):
                        margin_text = t(
                            "common.not_calculated"
                        )
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
                        break_even_text = t(
                            "common.not_calculated"
                        )
                    else:
                        break_even_text = t(
                            "common.units_short",
                            count=int(break_even_units),
                        )

                    st.write(
                        f"**{t('unit.details.sales_plan')}:** "
                        + t(
                            "common.units_short",
                            count=int(result["planned_units"]),
                        )
                    )

                    st.write(
                        f"**{t('unit.details.revenue')}:** "
                        f"{format_rubles(int(result['revenue_kopecks']))}"
                    )

                    st.write(
                        f"**{t('unit.details.total_batch_cost')}:** "
                        f"{format_rubles(int(result['total_cost_kopecks']))}"
                    )

                    st.write(
                        f"**{t('unit.details.batch_result')}:** "
                        f"{format_rubles(int(result['operating_result_kopecks']))}"
                    )

                    st.write(
                        f"**{t('unit.details.margin')}:** "
                        f"{margin_text}"
                    )

                    st.write(
                        f"**{t('unit.details.break_even')}:** "
                        f"{break_even_text}"
                    )

                    metric_column = t("unit.chart.metric")
                    amount_column = t("common.amount_rub")

                    chart_data = pd.DataFrame(
                        {
                            metric_column: [
                                t("unit.chart.price"),
                                t("unit.chart.base_cost"),
                                t(
                                    "unit.chart.percentage_cost"
                                ),
                                t("unit.chart.profit"),
                            ],
                            amount_column: [
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
                        x=metric_column,
                        y=amount_column,
                        text_auto=".2s",
                    )

                    unit_chart.update_layout(
                        xaxis_title="",
                        yaxis_title=amount_column,
                    )

                    st.plotly_chart(
                        unit_chart,
                        use_container_width=True,
                    )

            st.divider()
            st.subheader(t("unit.management.title"))

            selected_product_active = st.checkbox(
                t("unit.product.active"),
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
                    t("unit.management.save_activity"),
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
                    ] = t(
                        "unit.management.activity_updated"
                    )
                    st.rerun()

            with product_delete_column:
                if st.button(
                    t("unit.management.delete"),
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
                    ] = t("unit.management.deleted")
                    st.rerun()

            st.divider()
            st.subheader(t("unit.summary.title"))

            if summary.empty:
                st.info(t("unit.summary.empty"))
            else:
                visible_summary = summary.copy()

                product_column = t("unit.summary.product")
                plan_column = t("unit.summary.plan_units")
                pricing_method_column = t(
                    "unit.summary.pricing_method"
                )
                fixed_column = t(
                    "unit.summary.fixed_per_unit"
                )
                period_column = t(
                    "unit.summary.allocated_period"
                )
                base_cost_column = t(
                    "unit.summary.base_cost"
                )
                percentage_rate_column = t(
                    "unit.summary.percentage_rate"
                )
                selling_price_column = t(
                    "unit.summary.selling_price"
                )
                percentage_unit_column = t(
                    "unit.summary.percentage_per_unit"
                )
                total_cost_column = t(
                    "unit.summary.total_cost"
                )
                profit_column = t(
                    "unit.summary.profit_per_unit"
                )
                margin_column = t("unit.summary.margin")
                revenue_column = t("unit.summary.revenue")
                batch_result_column = t(
                    "unit.summary.batch_result"
                )
                break_even_column = t(
                    "unit.summary.break_even"
                )
                status_column = t("unit.summary.status")

                visible_summary[pricing_method_column] = (
                    visible_summary[
                        "pricing_method"
                    ].apply(format_unit_pricing_method)
                )

                money_columns = {
                    "fixed_per_unit_kopecks":
                        fixed_column,
                    "allocated_period_per_unit_kopecks":
                        period_column,
                    "base_cost_per_unit_kopecks":
                        base_cost_column,
                    "selling_price_kopecks":
                        selling_price_column,
                    "percentage_cost_per_unit_kopecks":
                        percentage_unit_column,
                    "total_cost_per_unit_kopecks":
                        total_cost_column,
                    "profit_per_unit_kopecks":
                        profit_column,
                    "revenue_kopecks":
                        revenue_column,
                    "operating_result_kopecks":
                        batch_result_column,
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

                visible_summary[margin_column] = (
                    pd.to_numeric(
                        visible_summary["margin_percent"],
                        errors="coerce",
                    )
                )

                visible_summary[
                    percentage_rate_column
                ] = pd.to_numeric(
                    visible_summary[
                        "percentage_cost_rate"
                    ],
                    errors="coerce",
                )

                visible_summary[
                    break_even_column
                ] = pd.to_numeric(
                    visible_summary["break_even_units"],
                    errors="coerce",
                )

                visible_summary[status_column] = (
                    visible_summary["pricing_error"]
                    .apply(
                        lambda value: (
                            t("unit.summary.status_ok")
                            if not text_or_empty(value)
                            else localize_unit_pricing_error(
                                value
                            )
                        )
                    )
                )

                visible_summary = visible_summary.rename(
                    columns={
                        "product_name": product_column,
                        "planned_units": plan_column,
                    }
                )

                summary_columns = [
                    product_column,
                    plan_column,
                    pricing_method_column,
                    fixed_column,
                    period_column,
                    base_cost_column,
                    percentage_rate_column,
                    selling_price_column,
                    total_cost_column,
                    profit_column,
                    margin_column,
                    revenue_column,
                    batch_result_column,
                    break_even_column,
                    status_column,
                ]

                st.dataframe(
                    visible_summary[summary_columns],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        fixed_column:
                            st.column_config.NumberColumn(
                                fixed_column,
                                format="%.2f",
                            ),
                        period_column:
                            st.column_config.NumberColumn(
                                period_column,
                                format="%.2f",
                            ),
                        base_cost_column:
                            st.column_config.NumberColumn(
                                base_cost_column,
                                format="%.2f",
                            ),
                        percentage_rate_column:
                            st.column_config.NumberColumn(
                                percentage_rate_column,
                                format="%.2f%%",
                            ),
                        selling_price_column:
                            st.column_config.NumberColumn(
                                selling_price_column,
                                format="%.2f",
                            ),
                        total_cost_column:
                            st.column_config.NumberColumn(
                                total_cost_column,
                                format="%.2f",
                            ),
                        profit_column:
                            st.column_config.NumberColumn(
                                profit_column,
                                format="%.2f",
                            ),
                        margin_column:
                            st.column_config.NumberColumn(
                                margin_column,
                                format="%.1f%%",
                            ),
                        revenue_column:
                            st.column_config.NumberColumn(
                                revenue_column,
                                format="%.2f",
                            ),
                        batch_result_column:
                            st.column_config.NumberColumn(
                                batch_result_column,
                                format="%.2f",
                            ),
                        break_even_column:
                            st.column_config.NumberColumn(
                                break_even_column,
                                format="%d",
                            ),
                    },
                )

if payment_calendar_tab.open:
    with payment_calendar_tab:
        st.subheader(t("calendar.title"))

        st.caption(t("calendar.caption"))

        with st.expander(
            t("calendar.add_title"),
            expanded=True,
        ):
            with st.form(
                "planned_cash_flow_form",
                clear_on_submit=True,
            ):
                plan_name = st.text_input(
                    t("calendar.fields.name"),
                    placeholder=t(
                        "calendar.placeholders.name"
                    ),
                )

                direction = st.selectbox(
                    t("calendar.fields.direction"),
                    options=list(DIRECTION_LABELS),
                    format_func=format_calendar_direction,
                )

                amount_rubles = st.number_input(
                    t("calendar.fields.amount"),
                    min_value=0.01,
                    value=1_000.00,
                    step=100.00,
                    format="%.2f",
                )

                category = st.selectbox(
                    t("calendar.fields.category"),
                    options=list(CF_CATEGORIES),
                )

                counterparty = st.text_input(
                    t("calendar.fields.counterparty"),
                )

                start_date = st.date_input(
                    t("calendar.fields.start_date"),
                    value=date.today(),
                    format="DD.MM.YYYY",
                )

                recurrence = st.selectbox(
                    t("calendar.fields.recurrence"),
                    options=list(RECURRENCE_LABELS),
                    format_func=format_calendar_recurrence,
                )

                use_end_date = st.checkbox(
                    t("calendar.fields.use_end_date"),
                    value=False,
                )

                selected_end_date = st.date_input(
                    t("calendar.fields.end_date"),
                    value=(
                        date.today()
                        + timedelta(days=365)
                    ),
                    format="DD.MM.YYYY",
                )

                is_active = st.checkbox(
                    t("calendar.fields.active"),
                    value=True,
                )

                comment = st.text_area(
                    t("calendar.fields.comment"),
                    max_chars=500,
                )

                create_plan_submitted = (
                    st.form_submit_button(
                        t("calendar.add_button"),
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
                        ] = t(
                            "calendar.messages.added",
                            plan_id=new_plan_id,
                        )
                        st.rerun()

        plans = get_planned_cash_flows_dataframe()

        st.subheader(t("calendar.plans.title"))

        if plans.empty:
            st.info(t("calendar.plans.empty"))
        else:
            visible_plans = plans.copy()

            id_column = t("common.id")
            name_column = t("common.name")
            type_column = t("calendar.columns.type")
            amount_column = t("common.amount_rub")
            category_column = t("common.category")
            counterparty_column = t(
                "common.counterparty"
            )
            start_column = t("calendar.columns.start")
            recurrence_column = t(
                "calendar.columns.recurrence"
            )
            end_column = t("calendar.columns.end")
            active_column = t("common.active")
            comment_column = t("common.comment")

            visible_plans[type_column] = (
                visible_plans["direction"]
                .apply(format_calendar_direction)
            )

            visible_plans[amount_column] = (
                visible_plans["amount_kopecks"] / 100
            )

            visible_plans[start_column] = pd.to_datetime(
                visible_plans["start_date"]
            ).dt.strftime("%d.%m.%Y")

            visible_plans[end_column] = (
                pd.to_datetime(
                    visible_plans["end_date"],
                    errors="coerce",
                )
                .dt.strftime("%d.%m.%Y")
                .fillna("")
            )

            visible_plans[recurrence_column] = (
                visible_plans["recurrence"]
                .apply(format_calendar_recurrence)
            )

            visible_plans[active_column] = (
                visible_plans["is_active"]
                .apply(format_boolean_status)
            )

            visible_plans = visible_plans.rename(
                columns={
                    "id": id_column,
                    "name": name_column,
                    "category": category_column,
                    "counterparty": counterparty_column,
                    "comment": comment_column,
                }
            )

            plan_columns = [
                id_column,
                name_column,
                type_column,
                amount_column,
                category_column,
                counterparty_column,
                start_column,
                recurrence_column,
                end_column,
                active_column,
                comment_column,
            ]

            st.dataframe(
                visible_plans[plan_columns],
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

            plan_options = {
                (
                    f"{int(row['id'])} — "
                    f"{row['name']}"
                ): int(row["id"])
                for _, row in plans.iterrows()
            }

            selected_plan_label = st.selectbox(
                t("calendar.select_manage"),
                options=list(plan_options),
            )

            selected_plan_id = plan_options[
                selected_plan_label
            ]

            selected_plan = plans.loc[
                plans["id"] == selected_plan_id
            ].iloc[0]

            selected_plan_active = st.checkbox(
                t("calendar.fields.active"),
                value=bool(
                    selected_plan["is_active"]
                ),
                key=(
                    f"selected_plan_active_"
                    f"{selected_plan_id}"
                ),
            )

            active_action_column, delete_column = (
                st.columns(2)
            )

            with active_action_column:
                if st.button(
                    t("calendar.save_activity"),
                    use_container_width=True,
                    key=(
                        f"save_plan_activity_"
                        f"{selected_plan_id}"
                    ),
                ):
                    set_planned_cash_flow_active(
                        plan_id=selected_plan_id,
                        is_active=selected_plan_active,
                    )

                    st.session_state[
                        "calendar_message"
                    ] = t(
                        "calendar.messages.activity_updated"
                    )
                    st.rerun()

            with delete_column:
                if st.button(
                    t("calendar.delete"),
                    use_container_width=True,
                    key=(
                        f"delete_plan_"
                        f"{selected_plan_id}"
                    ),
                ):
                    delete_planned_cash_flow(
                        selected_plan_id
                    )

                    st.session_state[
                        "calendar_message"
                    ] = t("calendar.messages.deleted")
                    st.rerun()

        st.divider()
        st.subheader(t("calendar.forecast.title"))

        forecast_start = st.date_input(
            t("calendar.forecast.start"),
            value=date.today(),
            format="DD.MM.YYYY",
            key="forecast_start",
        )

        forecast_horizon = st.selectbox(
            t("calendar.forecast.horizon"),
            options=[30, 60, 90, 180, 365],
            index=2,
            format_func=lambda days: t(
                "common.days",
                count=days,
            ),
        )

        opening_balance_rubles = st.number_input(
            t("calendar.forecast.opening_balance"),
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
            t("calendar.forecast.inflows"),
            format_rubles(total_inflow),
        )

        forecast_metrics[1].metric(
            t("calendar.forecast.outflows"),
            format_rubles(total_outflow),
        )

        forecast_metrics[2].metric(
            t("calendar.forecast.ending_balance"),
            format_rubles(ending_balance),
        )

        forecast_metrics[3].metric(
            t("calendar.forecast.minimum_balance"),
            format_rubles(minimum_balance),
        )

        cash_gap_rows = forecast.loc[
            forecast["closing_balance_kopecks"] < 0
        ]

        if cash_gap_rows.empty:
            st.success(
                t("calendar.forecast.no_gap")
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
                t(
                    "calendar.forecast.gap",
                    date=first_cash_gap.strftime(
                        "%d.%m.%Y"
                    ),
                    amount=format_rubles(
                        cash_gap_amount
                    ),
                )
            )

        chart_data = forecast.copy()

        date_column = t("common.date")
        balance_column = t(
            "calendar.forecast.balance"
        )

        chart_data[date_column] = pd.to_datetime(
            chart_data["date"]
        )

        chart_data[balance_column] = (
            chart_data[
                "closing_balance_kopecks"
            ] / 100
        )

        balance_chart = px.line(
            chart_data,
            x=date_column,
            y=balance_column,
        )

        balance_chart.add_hline(y=0)

        balance_chart.update_layout(
            xaxis_title="",
            yaxis_title=balance_column,
        )

        st.plotly_chart(
            balance_chart,
            use_container_width=True,
        )

        with st.expander(
            t("calendar.events.title"),
            expanded=False,
        ):
            if occurrences.empty:
                st.info(
                    t("calendar.events.empty")
                )
            else:
                visible_occurrences = (
                    occurrences.copy()
                )

                name_column = t("common.name")
                amount_column = t("common.amount_rub")
                category_column = t("common.category")
                counterparty_column = t(
                    "common.counterparty"
                )
                comment_column = t("common.comment")

                visible_occurrences[date_column] = (
                    pd.to_datetime(
                        visible_occurrences["date"]
                    ).dt.strftime("%d.%m.%Y")
                )

                visible_occurrences[amount_column] = (
                    visible_occurrences[
                        "signed_amount_kopecks"
                    ] / 100
                )

                visible_occurrences = (
                    visible_occurrences.rename(
                        columns={
                            "name": name_column,
                            "category": category_column,
                            "counterparty":
                                counterparty_column,
                            "comment": comment_column,
                        }
                    )
                )

                occurrence_columns = [
                    date_column,
                    name_column,
                    amount_column,
                    category_column,
                    counterparty_column,
                    comment_column,
                ]

                st.dataframe(
                    visible_occurrences[
                        occurrence_columns
                    ],
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

if import_tab.open:
    with import_tab:
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
        total_transaction_count = len(
            get_transactions_dataframe()
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
