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
        "classification.title":
            "Классификация операций",
        "classification.pending_title":
            "Неклассифицированные операции",
        "classification.metrics.inflow":
            "Поступления",
        "classification.metrics.outflow":
            "Списания",
        "classification.metrics.net":
            "Чистая сумма",
        "classification.metrics.count":
            "Операций",
        "classification.pending_caption": (
            "Учитываются операции, для которых не завершена "
            "классификация хотя бы в одном контуре: "
            "P&L или Cash Flow."
        ),
        "classification.all_classified":
            "Все операции классифицированы.",
        "classification.empty_database":
            "В базе пока нет операций для классификации.",
        "classification.only_pending":
            "Показывать только незавершённые",
        "classification.filtered_empty":
            "Все операции полностью классифицированы.",
        "classification.instructions": (
            "Для каждого отчёта выбери отдельное решение. "
            "Операцию можно включить в Cash Flow, "
            "но исключить из P&L, и наоборот."
        ),
        "classification.select_title":
            "Выберите операцию",
        "classification.select_caption": (
            "Нажмите на строку или на маркер слева. "
            "Редактирование выбранной операции "
            "откроется ниже."
        ),
        "classification.columns.id": "ID",
        "classification.columns.date": "Дата",
        "classification.columns.amount": "Сумма, ₽",
        "classification.columns.counterparty":
            "Контрагент",
        "classification.columns.description":
            "Описание",
        "classification.columns.payment_purpose":
            "Назначение платежа",
        "classification.columns.pnl_action":
            "Решение P&L",
        "classification.columns.pnl_category":
            "Категория P&L",
        "classification.columns.cf_action":
            "Решение Cash Flow",
        "classification.columns.cf_category":
            "Категория Cash Flow",
        "classification.columns.comment":
            "Комментарий",
        "classification.actions.include":
            "Включить",
        "classification.actions.exclude":
            "Исключить",
        "classification.actions.undefined":
            "Не определено",
        "classification.selected_title":
            "Классификация выбранной операции",
        "classification.details.date": "Дата",
        "classification.details.amount": "Сумма",
        "classification.details.position": "Операция",
        "classification.details.position_value":
            "{current} из {total}",
        "classification.details.counterparty":
            "Контрагент",
        "classification.details.description":
            "Описание",
        "classification.details.payment_purpose":
            "Назначение платежа",
        "classification.details.not_specified":
            "Не указано",
        "classification.help.pnl_category": (
            "Категория обязательна, "
            "если операция включается в P&L."
        ),
        "classification.help.cf_category": (
            "Категория обязательна, "
            "если операция включается в Cash Flow."
        ),
        "classification.buttons.save":
            "Сохранить",
        "classification.buttons.save_next":
            "Сохранить и перейти дальше",
        "classification.buttons.exclude_both":
            "Исключить из обоих",
        "classification.errors.transaction_not_found": (
            "Выбранная операция не найдена. "
            "Обновите страницу."
        ),
        "classification.errors.pnl_category_required":
            "Выберите категорию P&L.",
        "classification.errors.cf_category_required":
            "Выберите категорию Cash Flow.",
        "classification.messages.excluded_both":
            "Операция исключена из обоих отчётов.",
        "classification.messages.saved":
            "Классификация сохранена.",
        "classification.messages.summary": (
            "{action} Обновлено: {updated}. "
            "Полностью классифицировано: {classified}. "
            "Частично: {partial}."
        ),
        "rules.title":
            "Правила автоматической классификации",
        "rules.caption": (
            "Правила применяются по убыванию приоритета. "
            "Для каждой операции срабатывает только первое "
            "совпадение. Ручные решения не перезаписываются."
        ),
        "rules.apply_button":
            "Применить активные правила",
        "rules.messages.applied": (
            "Проверено операций: {checked}. "
            "Классифицировано: {matched}. "
            "Без совпадений: {unmatched}."
        ),
        "rules.create_title":
            "Создать новое правило",
        "rules.fields.name":
            "Название правила",
        "rules.placeholders.name":
            "Например: банковские комиссии",
        "rules.fields.priority":
            "Приоритет",
        "rules.help.priority": (
            "Чем больше число, тем раньше "
            "проверяется правило."
        ),
        "rules.fields.active":
            "Правило активно",
        "rules.fields.direction":
            "Направление операции",
        "rules.fields.match_field":
            "Где искать",
        "rules.fields.match_type":
            "Условие",
        "rules.fields.match_value":
            "Искомое значение",
        "rules.placeholders.match_value":
            "Например: обслуживание счёта",
        "rules.create_button":
            "Создать правило",
        "rules.messages.created":
            "Правило #{rule_id} создано.",
        "rules.errors.name_required":
            "Укажите название правила.",
        "rules.errors.match_value_required":
            "Укажите значение для поиска.",
        "rules.errors.decision_required": (
            "Правило должно принимать решение "
            "хотя бы для одного отчёта."
        ),
        "rules.errors.pnl_category_required":
            "Для включения в P&L выберите категорию.",
        "rules.errors.cf_category_required":
            "Для включения в Cash Flow выберите категорию.",
        "rules.options.direction.any":
            "Любое движение",
        "rules.options.direction.income":
            "Только поступления",
        "rules.options.direction.expense":
            "Только списания",
        "rules.options.field.all_text":
            "Все текстовые поля",
        "rules.options.field.counterparty_name":
            "Контрагент",
        "rules.options.field.counterparty_inn":
            "ИНН контрагента",
        "rules.options.field.bank_category":
            "Категория банка",
        "rules.options.field.description":
            "Описание операции",
        "rules.options.field.payment_purpose":
            "Назначение платежа",
        "rules.options.field.mcc":
            "MCC",
        "rules.options.field.tax_code":
            "КБК",
        "rules.options.match.contains":
            "Содержит",
        "rules.options.match.equals":
            "Полностью совпадает",
        "rules.options.match.starts_with":
            "Начинается с",
        "rules.transfer.title":
            "Перенос конфигурации правил",
        "rules.transfer.caption": (
            "Правила можно сохранить в JSON и перенести "
            "в другую установку Open MAS. "
            "Локальные ID и даты базы не экспортируются."
        ),
        "rules.transfer.download":
            "Скачать правила в JSON",
        "rules.transfer.export_info": (
            "Экспорт содержит текущие правила, "
            "их приоритеты, условия, категории "
            "и состояние активности."
        ),
        "rules.transfer.upload":
            "Загрузить конфигурацию правил",
        "rules.transfer.upload_help": (
            "Сначала файл будет проверен. "
            "База не изменится до подтверждения импорта."
        ),
        "rules.transfer.preview_title":
            "Результат проверки файла",
        "rules.transfer.metrics.received":
            "Получено",
        "rules.transfer.metrics.valid":
            "Уникальных корректных",
        "rules.transfer.metrics.file_duplicates":
            "Дублей внутри файла",
        "rules.transfer.metrics.database_duplicates":
            "Уже есть в базе",
        "rules.transfer.preview_caption": (
            "Версия формата: {schema_version}. "
            "Файл экспортирован: {exported_at}."
        ),
        "rules.transfer.errors.blocked": (
            "Конфигурация содержит ошибки. "
            "Импорт заблокирован."
        ),
        "rules.transfer.warnings.file_duplicates": (
            "Повторяющиеся правила внутри файла "
            "будут импортированы только один раз."
        ),
        "rules.transfer.info.database_duplicates": (
            "В режиме добавления правила, которые уже "
            "полностью совпадают с существующими, "
            "будут пропущены."
        ),
        "rules.transfer.json_title":
            "Просмотреть содержимое JSON",
        "rules.transfer.import_title":
            "Режим импорта",
        "rules.transfer.import_action":
            "Выберите действие",
        "rules.transfer.import.merge":
            "Добавить отсутствующие правила",
        "rules.transfer.import.replace":
            "Заменить все текущие правила",
        "rules.transfer.import.merge_caption": (
            "Текущие правила сохранятся. "
            "Полностью совпадающие правила "
            "будут пропущены."
        ),
        "rules.transfer.import.replace_warning": (
            "Все текущие правила будут удалены "
            "и заменены правилами из файла. "
            "Операция выполняется одной транзакцией."
        ),
        "rules.transfer.import.replace_phrase":
            "ЗАМЕНИТЬ ВСЕ ПРАВИЛА",
        "rules.transfer.import.confirmation":
            "Для замены введите:",
        "rules.transfer.import.merge_button":
            "Добавить правила",
        "rules.transfer.import.replace_button":
            "Заменить все правила",
        "rules.transfer.messages.completed": (
            "Импорт правил завершён. "
            "Получено: {received}. "
            "Добавлено: {inserted}. "
            "Пропущено дублей: {skipped}. "
            "Удалено прежних правил: {deleted}."
        ),
        "rules.saved.title":
            "Сохранённые правила",
        "rules.saved.empty":
            "Правила пока не созданы.",
        "rules.saved.columns.id": "ID",
        "rules.saved.columns.name": "Название",
        "rules.saved.columns.priority": "Приоритет",
        "rules.saved.columns.active": "Активно",
        "rules.saved.columns.direction": "Направление",
        "rules.saved.columns.field": "Поле",
        "rules.saved.columns.condition": "Условие",
        "rules.saved.columns.value": "Значение",
        "rules.saved.columns.pnl_action":
            "Решение P&L",
        "rules.saved.columns.pnl_category":
            "Категория P&L",
        "rules.saved.columns.cf_action":
            "Решение Cash Flow",
        "rules.saved.columns.cf_category":
            "Категория Cash Flow",
        "rules.saved.values.active": "Да",
        "rules.saved.values.inactive": "Нет",
        "rules.saved.manage":
            "Выберите правило для управления",
        "rules.saved.save_activity":
            "Сохранить активность",
        "rules.saved.delete":
            "Удалить правило",
        "rules.messages.activity_updated":
            "Состояние правила обновлено.",
        "rules.messages.deleted":
            "Правило удалено.",
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
        "classification.title":
            "Transaction classification",
        "classification.pending_title":
            "Unclassified transactions",
        "classification.metrics.inflow":
            "Inflows",
        "classification.metrics.outflow":
            "Outflows",
        "classification.metrics.net":
            "Net amount",
        "classification.metrics.count":
            "Transactions",
        "classification.pending_caption": (
            "Includes transactions whose classification "
            "is incomplete in at least one reporting area: "
            "P&L or Cash Flow."
        ),
        "classification.all_classified":
            "All transactions are classified.",
        "classification.empty_database":
            "There are no transactions to classify yet.",
        "classification.only_pending":
            "Show incomplete only",
        "classification.filtered_empty":
            "All transactions are fully classified.",
        "classification.instructions": (
            "Choose a separate decision for each report. "
            "A transaction may be included in Cash Flow "
            "but excluded from P&L, and vice versa."
        ),
        "classification.select_title":
            "Select a transaction",
        "classification.select_caption": (
            "Click a row or the marker on the left. "
            "The selected transaction editor "
            "will open below."
        ),
        "classification.columns.id": "ID",
        "classification.columns.date": "Date",
        "classification.columns.amount": "Amount, ₽",
        "classification.columns.counterparty":
            "Counterparty",
        "classification.columns.description":
            "Description",
        "classification.columns.payment_purpose":
            "Payment purpose",
        "classification.columns.pnl_action":
            "P&L decision",
        "classification.columns.pnl_category":
            "P&L category",
        "classification.columns.cf_action":
            "Cash Flow decision",
        "classification.columns.cf_category":
            "Cash Flow category",
        "classification.columns.comment":
            "Comment",
        "classification.actions.include":
            "Include",
        "classification.actions.exclude":
            "Exclude",
        "classification.actions.undefined":
            "Not decided",
        "classification.selected_title":
            "Selected transaction classification",
        "classification.details.date": "Date",
        "classification.details.amount": "Amount",
        "classification.details.position":
            "Transaction",
        "classification.details.position_value":
            "{current} of {total}",
        "classification.details.counterparty":
            "Counterparty",
        "classification.details.description":
            "Description",
        "classification.details.payment_purpose":
            "Payment purpose",
        "classification.details.not_specified":
            "Not specified",
        "classification.help.pnl_category": (
            "A category is required when the transaction "
            "is included in P&L."
        ),
        "classification.help.cf_category": (
            "A category is required when the transaction "
            "is included in Cash Flow."
        ),
        "classification.buttons.save":
            "Save",
        "classification.buttons.save_next":
            "Save and continue",
        "classification.buttons.exclude_both":
            "Exclude from both",
        "classification.errors.transaction_not_found": (
            "The selected transaction was not found. "
            "Refresh the page."
        ),
        "classification.errors.pnl_category_required":
            "Select a P&L category.",
        "classification.errors.cf_category_required":
            "Select a Cash Flow category.",
        "classification.messages.excluded_both":
            "The transaction was excluded from both reports.",
        "classification.messages.saved":
            "Classification saved.",
        "classification.messages.summary": (
            "{action} Updated: {updated}. "
            "Fully classified: {classified}. "
            "Partially classified: {partial}."
        ),
        "rules.title":
            "Automatic classification rules",
        "rules.caption": (
            "Rules are applied from highest to lowest priority. "
            "Only the first matching rule is applied to each "
            "transaction. Manual decisions are not overwritten."
        ),
        "rules.apply_button":
            "Apply active rules",
        "rules.messages.applied": (
            "Transactions checked: {checked}. "
            "Classified: {matched}. "
            "No match: {unmatched}."
        ),
        "rules.create_title":
            "Create a new rule",
        "rules.fields.name":
            "Rule name",
        "rules.placeholders.name":
            "For example: bank fees",
        "rules.fields.priority":
            "Priority",
        "rules.help.priority": (
            "A higher number means that the rule "
            "is checked earlier."
        ),
        "rules.fields.active":
            "Rule is active",
        "rules.fields.direction":
            "Transaction direction",
        "rules.fields.match_field":
            "Search field",
        "rules.fields.match_type":
            "Condition",
        "rules.fields.match_value":
            "Search value",
        "rules.placeholders.match_value":
            "For example: account service fee",
        "rules.create_button":
            "Create rule",
        "rules.messages.created":
            "Rule #{rule_id} created.",
        "rules.errors.name_required":
            "Enter a rule name.",
        "rules.errors.match_value_required":
            "Enter a search value.",
        "rules.errors.decision_required": (
            "The rule must make a decision "
            "for at least one report."
        ),
        "rules.errors.pnl_category_required":
            "Select a category when including in P&L.",
        "rules.errors.cf_category_required":
            "Select a category when including in Cash Flow.",
        "rules.options.direction.any":
            "Any direction",
        "rules.options.direction.income":
            "Inflows only",
        "rules.options.direction.expense":
            "Outflows only",
        "rules.options.field.all_text":
            "All text fields",
        "rules.options.field.counterparty_name":
            "Counterparty",
        "rules.options.field.counterparty_inn":
            "Counterparty tax ID",
        "rules.options.field.bank_category":
            "Bank category",
        "rules.options.field.description":
            "Transaction description",
        "rules.options.field.payment_purpose":
            "Payment purpose",
        "rules.options.field.mcc":
            "MCC",
        "rules.options.field.tax_code":
            "Budget classification code",
        "rules.options.match.contains":
            "Contains",
        "rules.options.match.equals":
            "Exact match",
        "rules.options.match.starts_with":
            "Starts with",
        "rules.transfer.title":
            "Rule configuration transfer",
        "rules.transfer.caption": (
            "Rules can be saved as JSON and transferred "
            "to another Open MAS installation. "
            "Local database IDs and dates are not exported."
        ),
        "rules.transfer.download":
            "Download rules as JSON",
        "rules.transfer.export_info": (
            "The export contains the current rules, "
            "their priorities, conditions, categories "
            "and active status."
        ),
        "rules.transfer.upload":
            "Upload rule configuration",
        "rules.transfer.upload_help": (
            "The file will be validated first. "
            "The database will not change until import "
            "is confirmed."
        ),
        "rules.transfer.preview_title":
            "File validation result",
        "rules.transfer.metrics.received":
            "Received",
        "rules.transfer.metrics.valid":
            "Unique and valid",
        "rules.transfer.metrics.file_duplicates":
            "Duplicates in file",
        "rules.transfer.metrics.database_duplicates":
            "Already in database",
        "rules.transfer.preview_caption": (
            "Schema version: {schema_version}. "
            "Exported at: {exported_at}."
        ),
        "rules.transfer.errors.blocked": (
            "The configuration contains errors. "
            "Import is blocked."
        ),
        "rules.transfer.warnings.file_duplicates": (
            "Duplicate rules within the file "
            "will be imported only once."
        ),
        "rules.transfer.info.database_duplicates": (
            "In merge mode, rules that fully match "
            "existing rules will be skipped."
        ),
        "rules.transfer.json_title":
            "View JSON contents",
        "rules.transfer.import_title":
            "Import mode",
        "rules.transfer.import_action":
            "Select an action",
        "rules.transfer.import.merge":
            "Add missing rules",
        "rules.transfer.import.replace":
            "Replace all current rules",
        "rules.transfer.import.merge_caption": (
            "Current rules will be preserved. "
            "Exact duplicates will be skipped."
        ),
        "rules.transfer.import.replace_warning": (
            "All current rules will be deleted and replaced "
            "with the rules from the file. "
            "The operation is performed in one transaction."
        ),
        "rules.transfer.import.replace_phrase":
            "REPLACE ALL RULES",
        "rules.transfer.import.confirmation":
            "To replace the rules, enter:",
        "rules.transfer.import.merge_button":
            "Add rules",
        "rules.transfer.import.replace_button":
            "Replace all rules",
        "rules.transfer.messages.completed": (
            "Rule import completed. "
            "Received: {received}. "
            "Added: {inserted}. "
            "Duplicates skipped: {skipped}. "
            "Previous rules deleted: {deleted}."
        ),
        "rules.saved.title":
            "Saved rules",
        "rules.saved.empty":
            "No rules have been created yet.",
        "rules.saved.columns.id": "ID",
        "rules.saved.columns.name": "Name",
        "rules.saved.columns.priority": "Priority",
        "rules.saved.columns.active": "Active",
        "rules.saved.columns.direction": "Direction",
        "rules.saved.columns.field": "Field",
        "rules.saved.columns.condition": "Condition",
        "rules.saved.columns.value": "Value",
        "rules.saved.columns.pnl_action":
            "P&L decision",
        "rules.saved.columns.pnl_category":
            "P&L category",
        "rules.saved.columns.cf_action":
            "Cash Flow decision",
        "rules.saved.columns.cf_category":
            "Cash Flow category",
        "rules.saved.values.active": "Yes",
        "rules.saved.values.inactive": "No",
        "rules.saved.manage":
            "Select a rule to manage",
        "rules.saved.save_activity":
            "Save active status",
        "rules.saved.delete":
            "Delete rule",
        "rules.messages.activity_updated":
            "Rule status updated.",
        "rules.messages.deleted":
            "Rule deleted.",
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
        "classification.title": "交易分类",
        "classification.pending_title":
            "未完成分类的交易",
        "classification.metrics.inflow":
            "资金流入",
        "classification.metrics.outflow":
            "资金流出",
        "classification.metrics.net":
            "净额",
        "classification.metrics.count":
            "交易笔数",
        "classification.pending_caption": (
            "统计至少在一个报表维度中尚未完成分类的交易："
            "损益表或现金流量表。"
        ),
        "classification.all_classified":
            "所有交易均已分类。",
        "classification.empty_database":
            "数据库中暂无可分类的交易。",
        "classification.only_pending":
            "仅显示未完成分类的交易",
        "classification.filtered_empty":
            "所有交易均已完成分类。",
        "classification.instructions": (
            "请分别为每张报表选择处理方式。"
            "交易可纳入现金流量表而排除在损益表之外，"
            "反之亦然。"
        ),
        "classification.select_title":
            "选择交易",
        "classification.select_caption": (
            "点击一行或左侧标记。"
            "下方将打开所选交易的编辑区域。"
        ),
        "classification.columns.id": "ID",
        "classification.columns.date": "日期",
        "classification.columns.amount": "金额，₽",
        "classification.columns.counterparty":
            "交易对方",
        "classification.columns.description":
            "描述",
        "classification.columns.payment_purpose":
            "付款用途",
        "classification.columns.pnl_action":
            "损益表处理方式",
        "classification.columns.pnl_category":
            "损益表类别",
        "classification.columns.cf_action":
            "现金流处理方式",
        "classification.columns.cf_category":
            "现金流类别",
        "classification.columns.comment":
            "备注",
        "classification.actions.include":
            "纳入",
        "classification.actions.exclude":
            "排除",
        "classification.actions.undefined":
            "未决定",
        "classification.selected_title":
            "所选交易分类",
        "classification.details.date": "日期",
        "classification.details.amount": "金额",
        "classification.details.position": "交易",
        "classification.details.position_value":
            "{current} / {total}",
        "classification.details.counterparty":
            "交易对方",
        "classification.details.description":
            "描述",
        "classification.details.payment_purpose":
            "付款用途",
        "classification.details.not_specified":
            "未填写",
        "classification.help.pnl_category": (
            "交易纳入损益表时必须选择类别。"
        ),
        "classification.help.cf_category": (
            "交易纳入现金流量表时必须选择类别。"
        ),
        "classification.buttons.save": "保存",
        "classification.buttons.save_next":
            "保存并继续",
        "classification.buttons.exclude_both":
            "从两张报表中排除",
        "classification.errors.transaction_not_found": (
            "未找到所选交易，请刷新页面。"
        ),
        "classification.errors.pnl_category_required":
            "请选择损益表类别。",
        "classification.errors.cf_category_required":
            "请选择现金流量表类别。",
        "classification.messages.excluded_both":
            "该交易已从两张报表中排除。",
        "classification.messages.saved":
            "分类已保存。",
        "classification.messages.summary": (
            "{action} 已更新：{updated}。"
            "完全分类：{classified}。"
            "部分分类：{partial}。"
        ),
        "rules.title":
            "自动分类规则",
        "rules.caption": (
            "规则按优先级从高到低应用。"
            "每笔交易只应用第一个匹配规则。"
            "手动分类不会被覆盖。"
        ),
        "rules.apply_button":
            "应用启用的规则",
        "rules.messages.applied": (
            "已检查交易：{checked}。"
            "已分类：{matched}。"
            "未匹配：{unmatched}。"
        ),
        "rules.create_title":
            "创建新规则",
        "rules.fields.name":
            "规则名称",
        "rules.placeholders.name":
            "例如：银行手续费",
        "rules.fields.priority":
            "优先级",
        "rules.help.priority":
            "数值越大，规则越早检查。",
        "rules.fields.active":
            "启用规则",
        "rules.fields.direction":
            "交易方向",
        "rules.fields.match_field":
            "搜索字段",
        "rules.fields.match_type":
            "匹配条件",
        "rules.fields.match_value":
            "搜索值",
        "rules.placeholders.match_value":
            "例如：账户服务费",
        "rules.create_button":
            "创建规则",
        "rules.messages.created":
            "规则 #{rule_id} 已创建。",
        "rules.errors.name_required":
            "请输入规则名称。",
        "rules.errors.match_value_required":
            "请输入搜索值。",
        "rules.errors.decision_required":
            "规则必须至少为一张报表作出处理决定。",
        "rules.errors.pnl_category_required":
            "纳入损益表时请选择类别。",
        "rules.errors.cf_category_required":
            "纳入现金流量表时请选择类别。",
        "rules.options.direction.any":
            "任意方向",
        "rules.options.direction.income":
            "仅资金流入",
        "rules.options.direction.expense":
            "仅资金流出",
        "rules.options.field.all_text":
            "所有文本字段",
        "rules.options.field.counterparty_name":
            "交易对方",
        "rules.options.field.counterparty_inn":
            "交易对方税号",
        "rules.options.field.bank_category":
            "银行类别",
        "rules.options.field.description":
            "交易描述",
        "rules.options.field.payment_purpose":
            "付款用途",
        "rules.options.field.mcc":
            "MCC",
        "rules.options.field.tax_code":
            "预算分类代码",
        "rules.options.match.contains":
            "包含",
        "rules.options.match.equals":
            "完全匹配",
        "rules.options.match.starts_with":
            "开头为",
        "rules.transfer.title":
            "规则配置迁移",
        "rules.transfer.caption": (
            "规则可以保存为 JSON，并迁移到其他 Open MAS "
            "安装中。本地数据库 ID 和日期不会导出。"
        ),
        "rules.transfer.download":
            "下载 JSON 规则",
        "rules.transfer.export_info": (
            "导出文件包含当前规则、优先级、"
            "匹配条件、类别和启用状态。"
        ),
        "rules.transfer.upload":
            "上传规则配置",
        "rules.transfer.upload_help": (
            "文件将首先接受验证。"
            "确认导入前，数据库不会发生变化。"
        ),
        "rules.transfer.preview_title":
            "文件验证结果",
        "rules.transfer.metrics.received":
            "收到",
        "rules.transfer.metrics.valid":
            "有效且唯一",
        "rules.transfer.metrics.file_duplicates":
            "文件内重复",
        "rules.transfer.metrics.database_duplicates":
            "数据库中已存在",
        "rules.transfer.preview_caption": (
            "格式版本：{schema_version}。"
            "导出时间：{exported_at}。"
        ),
        "rules.transfer.errors.blocked":
            "配置中存在错误，导入已被阻止。",
        "rules.transfer.warnings.file_duplicates": (
            "文件中的重复规则只会导入一次。"
        ),
        "rules.transfer.info.database_duplicates": (
            "在添加模式下，与现有规则完全相同的规则"
            "将被跳过。"
        ),
        "rules.transfer.json_title":
            "查看 JSON 内容",
        "rules.transfer.import_title":
            "导入模式",
        "rules.transfer.import_action":
            "选择操作",
        "rules.transfer.import.merge":
            "添加缺少的规则",
        "rules.transfer.import.replace":
            "替换所有当前规则",
        "rules.transfer.import.merge_caption": (
            "当前规则将被保留，完全相同的规则将被跳过。"
        ),
        "rules.transfer.import.replace_warning": (
            "所有当前规则都将被删除，并由文件中的规则替换。"
            "该操作将在一个事务中完成。"
        ),
        "rules.transfer.import.replace_phrase":
            "替换所有规则",
        "rules.transfer.import.confirmation":
            "请输入以下文字以确认替换：",
        "rules.transfer.import.merge_button":
            "添加规则",
        "rules.transfer.import.replace_button":
            "替换所有规则",
        "rules.transfer.messages.completed": (
            "规则导入完成。"
            "收到：{received}。"
            "已添加：{inserted}。"
            "跳过重复项：{skipped}。"
            "已删除原有规则：{deleted}。"
        ),
        "rules.saved.title":
            "已保存的规则",
        "rules.saved.empty":
            "尚未创建任何规则。",
        "rules.saved.columns.id": "ID",
        "rules.saved.columns.name": "名称",
        "rules.saved.columns.priority": "优先级",
        "rules.saved.columns.active": "已启用",
        "rules.saved.columns.direction": "方向",
        "rules.saved.columns.field": "字段",
        "rules.saved.columns.condition": "条件",
        "rules.saved.columns.value": "值",
        "rules.saved.columns.pnl_action":
            "损益表处理方式",
        "rules.saved.columns.pnl_category":
            "损益表类别",
        "rules.saved.columns.cf_action":
            "现金流处理方式",
        "rules.saved.columns.cf_category":
            "现金流类别",
        "rules.saved.values.active": "是",
        "rules.saved.values.inactive": "否",
        "rules.saved.manage":
            "选择要管理的规则",
        "rules.saved.save_activity":
            "保存启用状态",
        "rules.saved.delete":
            "删除规则",
        "rules.messages.activity_updated":
            "规则状态已更新。",
        "rules.messages.deleted":
            "规则已删除。",
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