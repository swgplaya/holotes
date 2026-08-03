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