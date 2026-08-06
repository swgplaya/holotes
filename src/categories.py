from __future__ import annotations


UNDEFINED_ACTION = "Не определено"
INCLUDE_ACTION = "Включить"
EXCLUDE_ACTION = "Исключить"

REPORT_ACTIONS = (
    UNDEFINED_ACTION,
    INCLUDE_ACTION,
    EXCLUDE_ACTION,
)


PNL_CATEGORIES = (
    "",
    "Выручка",
    "Себестоимость",
    "Разработка продукта и тестовые образцы",
    "Логистика",
    "Маркетинг и реклама",
    "Заработная плата и подрядчики",
    "Аренда и коммунальные расходы",
    "Банковские комиссии",
    "Налоги",
    "Программное обеспечение и подписки",
    "Прочие операционные расходы",
    "Прочие доходы",
    "Прочие расходы",
)


CF_CATEGORIES = (
    "",
    "Операционные поступления",
    "Оплата поставщикам",
    "Операционная деятельность — разработка продукта",
    "Логистика",
    "Маркетинг и реклама",
    "Заработная плата и подрядчики",
    "Аренда и коммунальные расходы",
    "Банковские расходы",
    "Налоги",
    "Прочие операционные платежи",
    "Инвестиционная деятельность",
    "Финансовая деятельность",
    "Вложения собственника",
    "Изъятия собственника",
    "Внутренние переводы",
)

# BUILT-IN CATEGORY TRANSLATION KEYS START
BUILT_IN_CATEGORY_TRANSLATION_KEYS: dict[str, str] = {'Выручка': 'reports.categories.revenue',
 'Себестоимость': 'reports.categories.cost_of_goods_sold',
 'Разработка продукта и тестовые образцы': 'reports.categories.product_development_prototypes',
 'Логистика': 'reports.categories.logistics',
 'Маркетинг и реклама': 'reports.categories.marketing_advertising',
 'Заработная плата и подрядчики': 'reports.categories.payroll_contractors',
 'Аренда и коммунальные расходы': 'reports.categories.rent_utilities',
 'Банковские комиссии': 'reports.categories.bank_fees',
 'Налоги': 'reports.categories.taxes',
 'Программное обеспечение и подписки': 'reports.categories.software_subscriptions',
 'Прочие операционные расходы': 'reports.categories.other_operating_expenses',
 'Прочие доходы': 'reports.categories.other_income',
 'Прочие расходы': 'reports.categories.other_expenses',
 'Операционные поступления': 'reports.categories.operating_inflows',
 'Оплата поставщикам': 'reports.categories.supplier_payments',
 'Операционная деятельность — разработка продукта': 'reports.categories.operating_product_development',
 'Банковские расходы': 'reports.categories.bank_expenses',
 'Прочие операционные платежи': 'reports.categories.other_operating_payments',
 'Инвестиционная деятельность': 'reports.categories.investing_activities',
 'Финансовая деятельность': 'reports.categories.financing_activities',
 'Вложения собственника': 'reports.categories.owner_contributions',
 'Изъятия собственника': 'reports.categories.owner_withdrawals',
 'Внутренние переводы': 'reports.categories.internal_transfers'}
# BUILT-IN CATEGORY TRANSLATION KEYS END
