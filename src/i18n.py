from __future__ import annotations

from typing import Any


DEFAULT_LANGUAGE = "ru"

SUPPORTED_LANGUAGES: dict[str, str] = {
    "ru": "Русский",
    "en": "English",
    "zh-CN": "简体中文",
}


TRANSLATIONS: dict[str, dict[str, str]] = {
    "ru": {
        "language.selector": "Язык интерфейса",
        "app.eyebrow":
            "Управленческий финансовый учёт",
        "app.description": (
            "Локальная система для управления банковскими "
            "операциями, финансовой отчётностью, правилами "
            "классификации и денежными потоками бизнеса."
        ),
        "app.badge": "Локально · MVP",
        "tabs.operations": "Операции в базе",
        "tabs.classification": "Классификация",
        "tabs.rules": "Правила",
        "tabs.pnl": "P&L",
        "tabs.cash_flow": "Cash Flow",
        "tabs.unit_economics": "Unit Economics",
        "tabs.payment_calendar":
            "Платёжный календарь",
        "tabs.import": "Импорт выписки",
        "operations.empty_state": (
            "В базе пока нет операций. "
            "Загрузите первую выписку во вкладке импорта."
        ),
        "operations.saved_title":
            "Сохранённые операции",
        "operations.technical_info":
            "Техническая информация",
        "operations.sqlite_records":
            "Записей в SQLite:",
        "operations.metrics.count": "Операций",
        "operations.metrics.inflow": "Поступления",
        "operations.metrics.outflow": "Списания",
        "operations.metrics.net": "Чистое движение",
        "operations.columns.date": "Дата",
        "operations.columns.amount": "Сумма, ₽",
        "operations.columns.direction":
            "Дебет/кредит",
        "operations.columns.bank_category":
            "Категория банка",
        "operations.columns.status": "Статус",
        "operations.columns.counterparty":
            "Контрагент",
        "operations.columns.tax_id": "ИНН",
        "operations.columns.description":
            "Описание",
        "operations.columns.payment_purpose":
            "Назначение платежа",
        "operations.columns.classification":
            "Классификация",
        "reports.empty_database":
            "В базе пока нет операций.",
        "reports.invalid_dates":
            "В базе не найдено корректных дат проведения.",
        "reports.unknown_type":
            "Неизвестный тип отчёта: {report_type}",
        "reports.period.title": "Период отчёта",
        "reports.period.start": "Начало периода",
        "reports.period.end": "Конец периода",
        "reports.period.compare": "Сравнить с",
        "reports.period.synced": (
            "Настройки периода синхронизированы "
            "между P&L и Cash Flow."
        ),
        "reports.period.current":
            "Период: {current}",
        "reports.period.with_comparison": (
            "Выбранный период: {current}. "
            "Сравнение: {comparison}."
        ),
        "reports.comparison.none": "Без сравнения",
        "reports.comparison.previous":
            "Предыдущий период",
        "reports.comparison.previous_year":
            "Тот же период год назад",
        "reports.metrics.included":
            "Учтено операций",
        "reports.current_summary": (
            "{label}: исключено из отчёта — "
            "{excluded}; не принято решение — {pending}."
        ),
        "reports.comparison_summary": (
            "{label}: учтено — {included}; "
            "исключено — {excluded}; "
            "не принято решение — {pending}."
        ),
        "reports.pending_warning": (
            "Часть операций выбранного периода "
            "ещё не классифицирована для этого отчёта."
        ),
        "reports.empty_period": (
            "В выбранном периоде нет операций, "
            "включённых в этот отчёт."
        ),
        "reports.category_structure":
            "Структура по категориям",
        "reports.no_category_data": (
            "Нет данных для построения "
            "структуры по категориям."
        ),
        "reports.no_comparison_data": (
            "В обоих периодах нет данных "
            "для сравнения категорий."
        ),
        "reports.current_operations":
            "Операции выбранного периода",
        "reports.comparison_operations":
            "Операции периода сравнения",
        "reports.columns.category": "Категория",
        "reports.columns.amount": "Сумма, ₽",
        "reports.columns.no_category":
            "Без категории",
        "reports.columns.current_amount":
            "Выбранный период, ₽",
        "reports.columns.comparison_amount":
            "Период сравнения, ₽",
        "reports.columns.delta_amount":
            "Изменение, ₽",
        "reports.columns.delta_percent":
            "Изменение, %",
        "reports.columns.period": "Период",
        "reports.percentage_point_delta":
            "{value:+.1f} п.п.",
        "reports.pnl.title": "P&L",
        "reports.pnl.caption": (
            "На текущем этапе отчёт строится "
            "по банковским операциям кассовым методом."
        ),
        "reports.pnl.inflow": "Доходы",
        "reports.pnl.outflow": "Расходы",
        "reports.pnl.net": "Результат",
        "reports.pnl.kpi_title": "KPI P&L",
        "reports.pnl.kpi.profitability":
            "Рентабельность продаж",
        "reports.pnl.kpi.expense_share":
            "Доля расходов в доходах",
        "reports.pnl.kpi.expense_coverage":
            "Покрытие расходов",
        "reports.pnl.kpi.classification_rate":
            "Обработано операций",
        "reports.pnl.kpi.average_income":
            "Среднее поступление",
        "reports.pnl.kpi.average_expense":
            "Среднее списание",
        "reports.pnl.kpi.income_count":
            "Доходных операций",
        "reports.pnl.kpi.expense_count":
            "Расходных операций",
        "reports.pnl.kpi_caption": (
            "KPI рассчитаны по включённым банковским "
            "операциям. Это управленческий P&L "
            "по кассовому методу, а не бухгалтерский "
            "отчёт по методу начисления."
        ),
        "reports.cash_flow.title": "Cash Flow",
        "reports.cash_flow.caption": (
            "Отчёт показывает фактические движения "
            "денежных средств по дате проведения."
        ),
        "reports.cash_flow.inflow": "Поступления",
        "reports.cash_flow.outflow": "Платежи",
        "reports.cash_flow.net":
            "Чистый денежный поток",
    },
    "en": {
        "language.selector": "Interface language",
        "app.eyebrow": "Management accounting",
        "app.description": (
            "A local system for managing bank transactions, "
            "financial reporting, classification rules, "
            "and business cash flows."
        ),
        "app.badge": "Local-first · MVP",
        "tabs.operations": "Transactions",
        "tabs.classification": "Classification",
        "tabs.rules": "Rules",
        "tabs.pnl": "P&L",
        "tabs.cash_flow": "Cash Flow",
        "tabs.unit_economics": "Unit Economics",
        "tabs.payment_calendar": "Payment calendar",
        "tabs.import": "Import statement",
        "operations.empty_state": (
            "There are no transactions in the database yet. "
            "Upload your first bank statement "
            "in the import tab."
        ),
        "operations.saved_title":
            "Saved transactions",
        "operations.technical_info":
            "Technical information",
        "operations.sqlite_records":
            "SQLite records:",
        "operations.metrics.count": "Transactions",
        "operations.metrics.inflow": "Inflows",
        "operations.metrics.outflow": "Outflows",
        "operations.metrics.net": "Net movement",
        "operations.columns.date": "Date",
        "operations.columns.amount": "Amount, ₽",
        "operations.columns.direction":
            "Debit/Credit",
        "operations.columns.bank_category":
            "Bank category",
        "operations.columns.status": "Status",
        "operations.columns.counterparty":
            "Counterparty",
        "operations.columns.tax_id": "Tax ID",
        "operations.columns.description":
            "Description",
        "operations.columns.payment_purpose":
            "Payment purpose",
        "operations.columns.classification":
            "Classification",
        "reports.empty_database":
            "There are no transactions in the database yet.",
        "reports.invalid_dates":
            "No valid transaction dates were found.",
        "reports.unknown_type":
            "Unknown report type: {report_type}",
        "reports.period.title": "Report period",
        "reports.period.start": "Start date",
        "reports.period.end": "End date",
        "reports.period.compare": "Compare with",
        "reports.period.synced": (
            "Period settings are synchronized "
            "between P&L and Cash Flow."
        ),
        "reports.period.current":
            "Period: {current}",
        "reports.period.with_comparison": (
            "Selected period: {current}. "
            "Comparison: {comparison}."
        ),
        "reports.comparison.none": "No comparison",
        "reports.comparison.previous":
            "Previous period",
        "reports.comparison.previous_year":
            "Same period last year",
        "reports.metrics.included":
            "Included transactions",
        "reports.current_summary": (
            "{label}: excluded — {excluded}; "
            "pending decision — {pending}."
        ),
        "reports.comparison_summary": (
            "{label}: included — {included}; "
            "excluded — {excluded}; "
            "pending decision — {pending}."
        ),
        "reports.pending_warning": (
            "Some transactions in the selected period "
            "have not yet been classified for this report."
        ),
        "reports.empty_period": (
            "There are no transactions included "
            "in this report for the selected period."
        ),
        "reports.category_structure":
            "Category structure",
        "reports.no_category_data": (
            "There is no data available "
            "for the category structure."
        ),
        "reports.no_comparison_data": (
            "Neither period contains data "
            "for category comparison."
        ),
        "reports.current_operations":
            "Selected-period transactions",
        "reports.comparison_operations":
            "Comparison-period transactions",
        "reports.columns.category": "Category",
        "reports.columns.amount": "Amount, ₽",
        "reports.columns.no_category":
            "Uncategorized",
        "reports.columns.current_amount":
            "Selected period, ₽",
        "reports.columns.comparison_amount":
            "Comparison period, ₽",
        "reports.columns.delta_amount":
            "Change, ₽",
        "reports.columns.delta_percent":
            "Change, %",
        "reports.columns.period": "Period",
        "reports.percentage_point_delta":
            "{value:+.1f} pp",
        "reports.pnl.title": "P&L",
        "reports.pnl.caption": (
            "At the current stage, the report is built "
            "from bank transactions on a cash basis."
        ),
        "reports.pnl.inflow": "Income",
        "reports.pnl.outflow": "Expenses",
        "reports.pnl.net": "Result",
        "reports.pnl.kpi_title": "P&L KPIs",
        "reports.pnl.kpi.profitability":
            "Profit margin",
        "reports.pnl.kpi.expense_share":
            "Expenses as a share of income",
        "reports.pnl.kpi.expense_coverage":
            "Expense coverage",
        "reports.pnl.kpi.classification_rate":
            "Transactions processed",
        "reports.pnl.kpi.average_income":
            "Average inflow",
        "reports.pnl.kpi.average_expense":
            "Average outflow",
        "reports.pnl.kpi.income_count":
            "Income transactions",
        "reports.pnl.kpi.expense_count":
            "Expense transactions",
        "reports.pnl.kpi_caption": (
            "KPIs are calculated from included bank "
            "transactions. This is a cash-basis management "
            "P&L, not an accrual-basis accounting statement."
        ),
        "reports.cash_flow.title": "Cash Flow",
        "reports.cash_flow.caption": (
            "The report shows actual cash movements "
            "by transaction date."
        ),
        "reports.cash_flow.inflow": "Inflows",
        "reports.cash_flow.outflow": "Payments",
        "reports.cash_flow.net": "Net cash flow",
    },
    "zh-CN": {
        "language.selector": "界面语言",
        "app.eyebrow": "管理会计",
        "app.description": (
            "用于管理银行交易、财务报表、分类规则"
            "和企业现金流的本地系统。"
        ),
        "app.badge": "本地优先 · MVP",
        "tabs.operations": "交易记录",
        "tabs.classification": "分类",
        "tabs.rules": "规则",
        "tabs.pnl": "损益表",
        "tabs.cash_flow": "现金流",
        "tabs.unit_economics": "单位经济模型",
        "tabs.payment_calendar": "付款日历",
        "tabs.import": "导入银行流水",
        "operations.empty_state": (
            "数据库中暂无交易。"
            "请在导入银行流水选项卡中上传第一份银行流水。"
        ),
        "operations.saved_title": "已保存的交易",
        "operations.technical_info": "技术信息",
        "operations.sqlite_records":
            "SQLite 记录数：",
        "operations.metrics.count": "交易笔数",
        "operations.metrics.inflow": "资金流入",
        "operations.metrics.outflow": "资金流出",
        "operations.metrics.net": "净现金变动",
        "operations.columns.date": "日期",
        "operations.columns.amount": "金额，₽",
        "operations.columns.direction":
            "借方/贷方",
        "operations.columns.bank_category":
            "银行类别",
        "operations.columns.status": "状态",
        "operations.columns.counterparty":
            "交易对方",
        "operations.columns.tax_id":
            "纳税人识别号",
        "operations.columns.description": "描述",
        "operations.columns.payment_purpose":
            "付款用途",
        "operations.columns.classification":
            "分类状态",
        "reports.empty_database":
            "数据库中暂无交易。",
        "reports.invalid_dates":
            "数据库中未找到有效的交易日期。",
        "reports.unknown_type":
            "未知报表类型：{report_type}",
        "reports.period.title": "报表期间",
        "reports.period.start": "开始日期",
        "reports.period.end": "结束日期",
        "reports.period.compare": "对比",
        "reports.period.synced": (
            "期间设置已在损益表和现金流量表之间同步。"
        ),
        "reports.period.current":
            "期间：{current}",
        "reports.period.with_comparison": (
            "所选期间：{current}。"
            "对比期间：{comparison}。"
        ),
        "reports.comparison.none": "不对比",
        "reports.comparison.previous": "上一期间",
        "reports.comparison.previous_year":
            "去年同期",
        "reports.metrics.included": "纳入交易",
        "reports.current_summary": (
            "{label}：排除 {excluded} 笔；"
            "待处理 {pending} 笔。"
        ),
        "reports.comparison_summary": (
            "{label}：纳入 {included} 笔；"
            "排除 {excluded} 笔；"
            "待处理 {pending} 笔。"
        ),
        "reports.pending_warning": (
            "所选期间的部分交易尚未完成该报表的分类。"
        ),
        "reports.empty_period": (
            "所选期间内没有纳入该报表的交易。"
        ),
        "reports.category_structure": "按类别构成",
        "reports.no_category_data": (
            "没有可用于生成类别构成的数据。"
        ),
        "reports.no_comparison_data": (
            "两个期间均无可用于类别对比的数据。"
        ),
        "reports.current_operations":
            "所选期间的交易",
        "reports.comparison_operations":
            "对比期间的交易",
        "reports.columns.category": "类别",
        "reports.columns.amount": "金额，₽",
        "reports.columns.no_category": "未分类",
        "reports.columns.current_amount":
            "所选期间，₽",
        "reports.columns.comparison_amount":
            "对比期间，₽",
        "reports.columns.delta_amount":
            "变化额，₽",
        "reports.columns.delta_percent":
            "变化，%",
        "reports.columns.period": "期间",
        "reports.percentage_point_delta":
            "{value:+.1f} 个百分点",
        "reports.pnl.title": "损益表",
        "reports.pnl.caption": (
            "当前阶段，报表按银行交易并采用收付实现制生成。"
        ),
        "reports.pnl.inflow": "收入",
        "reports.pnl.outflow": "费用",
        "reports.pnl.net": "结果",
        "reports.pnl.kpi_title": "损益表 KPI",
        "reports.pnl.kpi.profitability":
            "销售利润率",
        "reports.pnl.kpi.expense_share":
            "费用占收入比",
        "reports.pnl.kpi.expense_coverage":
            "费用覆盖率",
        "reports.pnl.kpi.classification_rate":
            "已处理交易",
        "reports.pnl.kpi.average_income":
            "平均收入",
        "reports.pnl.kpi.average_expense":
            "平均支出",
        "reports.pnl.kpi.income_count":
            "收入交易笔数",
        "reports.pnl.kpi.expense_count":
            "支出交易笔数",
        "reports.pnl.kpi_caption": (
            "KPI 根据已纳入的银行交易计算。"
            "这是采用收付实现制的管理损益表，"
            "并非采用权责发生制的会计报表。"
        ),
        "reports.cash_flow.title": "现金流量表",
        "reports.cash_flow.caption": (
            "该报表按交易日期显示实际现金流动。"
        ),
        "reports.cash_flow.inflow": "现金流入",
        "reports.cash_flow.outflow": "现金流出",
        "reports.cash_flow.net": "净现金流",
    },
}


def normalize_language(
    language: object,
) -> str:
    """Возвращает поддерживаемый код языка."""

    if isinstance(language, str):
        normalized = language.strip()

        if normalized in SUPPORTED_LANGUAGES:
            return normalized

    return DEFAULT_LANGUAGE


def translate(
    key: str,
    language: object = DEFAULT_LANGUAGE,
    **values: Any,
) -> str:
    """
    Возвращает перевод по ключу.

    При отсутствии перевода используется русский язык,
    затем сам ключ.
    """

    normalized_language = normalize_language(
        language
    )

    localized_translations = TRANSLATIONS.get(
        normalized_language,
        {},
    )

    template = localized_translations.get(key)

    if template is None:
        template = TRANSLATIONS[
            DEFAULT_LANGUAGE
        ].get(
            key,
            key,
        )

    if not values:
        return template

    try:
        return template.format(**values)
    except KeyError as exc:
        missing_value = str(exc.args[0])

        raise ValueError(
            "Для перевода "
            f"'{key}' не передано значение "
            f"'{missing_value}'."
        ) from exc


def find_translation_issues() -> tuple[str, ...]:
    """Проверяет полноту словарей локализации."""

    all_keys: set[str] = set()

    for translations in TRANSLATIONS.values():
        all_keys.update(translations)

    issues: list[str] = []

    for language in SUPPORTED_LANGUAGES:
        language_keys = set(
            TRANSLATIONS.get(language, {})
        )

        missing_keys = sorted(
            all_keys - language_keys
        )

        if missing_keys:
            issues.append(
                f"{language}: отсутствуют ключи: "
                + ", ".join(missing_keys)
            )

    return tuple(issues)