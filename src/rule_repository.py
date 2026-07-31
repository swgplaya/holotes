from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import pandas as pd
from sqlalchemy import select

from src.categories import (
    EXCLUDE_ACTION,
    INCLUDE_ACTION,
    UNDEFINED_ACTION,
)
from src.database import SessionLocal
from src.models import BankTransaction, ClassificationRule


MATCH_FIELDS = {
    "all_text": "Все текстовые поля",
    "counterparty_name": "Контрагент",
    "counterparty_inn": "ИНН контрагента",
    "bank_category": "Категория банка",
    "description": "Описание операции",
    "payment_purpose": "Назначение платежа",
    "mcc": "MCC",
    "tax_code": "КБК",
}

MATCH_TYPES = {
    "contains": "Содержит",
    "equals": "Полностью совпадает",
    "starts_with": "Начинается с",
}

DIRECTION_FILTERS = {
    "any": "Любое движение",
    "income": "Только поступления",
    "expense": "Только списания",
}


@dataclass(frozen=True)
class ApplyRulesResult:
    """Результат применения правил."""

    checked: int
    matched: int
    unmatched: int


def _normalize(value: Any) -> str:
    """Нормализует текст для нечувствительного поиска."""

    if value is None or pd.isna(value):
        return ""

    text = str(value)
    text = text.replace("ё", "е")
    text = re.sub(r"\s+", " ", text)

    return text.strip().casefold()


def _optional_text(value: Any) -> str | None:
    """Возвращает очищенный текст или None."""

    if value is None or pd.isna(value):
        return None

    text = str(value).strip()

    return text or None


def _action_to_bool(action: str) -> bool | None:
    """Преобразует действие интерфейса в значение базы."""

    if action == INCLUDE_ACTION:
        return True

    if action == EXCLUDE_ACTION:
        return False

    if action == UNDEFINED_ACTION:
        return None

    raise ValueError(
        f"Неизвестное действие: {action!r}"
    )


def _bool_to_action(value: bool | None) -> str:
    """Преобразует значение базы в подпись интерфейса."""

    if value is True:
        return INCLUDE_ACTION

    if value is False:
        return EXCLUDE_ACTION

    return UNDEFINED_ACTION


def _get_transaction_direction(
    transaction: BankTransaction,
) -> str:
    """Определяет направление банковской операции."""

    direction = _normalize(transaction.direction)

    income_markers = (
        "кредит",
        "пополнение",
        "поступление",
        "приход",
        "credit",
    )

    if any(
        marker in direction
        for marker in income_markers
    ):
        return "income"

    return "expense"


def _get_matchable_text(
    transaction: BankTransaction,
    match_field: str,
) -> str:
    """Возвращает поле операции, по которому работает правило."""

    if match_field == "all_text":
        values = (
            transaction.counterparty_name,
            transaction.counterparty_inn,
            transaction.bank_category,
            transaction.description,
            transaction.payment_purpose,
            transaction.mcc,
            transaction.tax_code,
        )

        return " ".join(
            _normalize(value)
            for value in values
            if value
        )

    if match_field not in MATCH_FIELDS:
        raise ValueError(
            f"Неизвестное поле правила: {match_field}"
        )

    return _normalize(
        getattr(transaction, match_field)
    )


def _rule_matches(
    rule: ClassificationRule,
    transaction: BankTransaction,
) -> bool:
    """Проверяет, подходит ли правило операции."""

    if rule.direction_filter != "any":
        transaction_direction = (
            _get_transaction_direction(transaction)
        )

        if transaction_direction != rule.direction_filter:
            return False

    actual_value = _get_matchable_text(
        transaction=transaction,
        match_field=rule.match_field,
    )

    expected_value = _normalize(rule.match_value)

    if not expected_value:
        return False

    if rule.match_type == "contains":
        return expected_value in actual_value

    if rule.match_type == "equals":
        return actual_value == expected_value

    if rule.match_type == "starts_with":
        return actual_value.startswith(expected_value)

    raise ValueError(
        f"Неизвестное условие правила: {rule.match_type}"
    )


def create_rule(
    *,
    name: str,
    priority: int,
    is_active: bool,
    direction_filter: str,
    match_field: str,
    match_type: str,
    match_value: str,
    pnl_action: str,
    pnl_category: str,
    cf_action: str,
    cf_category: str,
) -> int:
    """Создаёт правило автоматической классификации."""

    clean_name = _optional_text(name)
    clean_match_value = _optional_text(match_value)

    if clean_name is None:
        raise ValueError(
            "Укажи название правила."
        )

    if clean_match_value is None:
        raise ValueError(
            "Укажи значение для поиска."
        )

    if direction_filter not in DIRECTION_FILTERS:
        raise ValueError(
            "Выбрано неизвестное направление операции."
        )

    if match_field not in MATCH_FIELDS:
        raise ValueError(
            "Выбрано неизвестное поле поиска."
        )

    if match_type not in MATCH_TYPES:
        raise ValueError(
            "Выбрано неизвестное условие поиска."
        )

    include_in_pnl = _action_to_bool(pnl_action)
    include_in_cf = _action_to_bool(cf_action)

    clean_pnl_category = _optional_text(pnl_category)
    clean_cf_category = _optional_text(cf_category)

    if (
        include_in_pnl is None
        and include_in_cf is None
    ):
        raise ValueError(
            "Правило должно принимать решение "
            "хотя бы для одного отчёта."
        )

    if (
        include_in_pnl is True
        and clean_pnl_category is None
    ):
        raise ValueError(
            "Для включения в P&L выбери категорию."
        )

    if (
        include_in_cf is True
        and clean_cf_category is None
    ):
        raise ValueError(
            "Для включения в Cash Flow выбери категорию."
        )

    if include_in_pnl is not True:
        clean_pnl_category = None

    if include_in_cf is not True:
        clean_cf_category = None

    rule = ClassificationRule(
        name=clean_name,
        priority=int(priority),
        is_active=bool(is_active),
        direction_filter=direction_filter,
        match_field=match_field,
        match_type=match_type,
        match_value=clean_match_value,
        include_in_pnl=include_in_pnl,
        pnl_category=clean_pnl_category,
        include_in_cf=include_in_cf,
        cf_category=clean_cf_category,
    )

    with SessionLocal() as session:
        session.add(rule)
        session.commit()
        session.refresh(rule)

        return rule.id


def get_rules_dataframe() -> pd.DataFrame:
    """Возвращает правила как DataFrame."""

    columns = [
        "id",
        "name",
        "priority",
        "is_active",
        "direction_filter",
        "match_field",
        "match_type",
        "match_value",
        "pnl_action",
        "pnl_category",
        "cf_action",
        "cf_category",
    ]

    statement = (
        select(ClassificationRule)
        .order_by(
            ClassificationRule.priority.desc(),
            ClassificationRule.id.asc(),
        )
    )

    with SessionLocal() as session:
        rules = session.scalars(statement).all()

        rows = [
            {
                "id": rule.id,
                "name": rule.name,
                "priority": rule.priority,
                "is_active": rule.is_active,
                "direction_filter":
                    DIRECTION_FILTERS[
                        rule.direction_filter
                    ],
                "match_field":
                    MATCH_FIELDS[rule.match_field],
                "match_type":
                    MATCH_TYPES[rule.match_type],
                "match_value": rule.match_value,
                "pnl_action":
                    _bool_to_action(rule.include_in_pnl),
                "pnl_category":
                    rule.pnl_category or "",
                "cf_action":
                    _bool_to_action(rule.include_in_cf),
                "cf_category":
                    rule.cf_category or "",
            }
            for rule in rules
        ]

    return pd.DataFrame(rows, columns=columns)


def set_rule_active(
    rule_id: int,
    is_active: bool,
) -> None:
    """Включает или выключает правило."""

    with SessionLocal() as session:
        rule = session.get(
            ClassificationRule,
            int(rule_id),
        )

        if rule is None:
            raise ValueError(
                f"Правило с ID {rule_id} не найдено."
            )

        rule.is_active = bool(is_active)
        session.commit()


def delete_rule(rule_id: int) -> None:
    """Удаляет правило."""

    with SessionLocal() as session:
        rule = session.get(
            ClassificationRule,
            int(rule_id),
        )

        if rule is None:
            raise ValueError(
                f"Правило с ID {rule_id} не найдено."
            )

        session.delete(rule)
        session.commit()


def apply_classification_rules() -> ApplyRulesResult:
    """
    Применяет активные правила к неклассифицированным операциям.

    При совпадении используется первое правило по приоритету.
    """

    rules_statement = (
        select(ClassificationRule)
        .where(
            ClassificationRule.is_active.is_(True)
        )
        .order_by(
            ClassificationRule.priority.desc(),
            ClassificationRule.id.asc(),
        )
    )

    transactions_statement = (
        select(BankTransaction)
        .where(
            BankTransaction.classification_status
            == "unclassified",
            BankTransaction.classification_source.is_(None),
        )
        .order_by(
            BankTransaction.posted_at.asc(),
            BankTransaction.id.asc(),
        )
    )

    with SessionLocal() as session:
        rules = session.scalars(
            rules_statement
        ).all()

        transactions = session.scalars(
            transactions_statement
        ).all()

        matched = 0

        for transaction in transactions:
            for rule in rules:
                if not _rule_matches(
                    rule,
                    transaction,
                ):
                    continue

                transaction.include_in_pnl = (
                    rule.include_in_pnl
                )
                transaction.pnl_category = (
                    rule.pnl_category
                )

                transaction.include_in_cf = (
                    rule.include_in_cf
                )
                transaction.cf_category = (
                    rule.cf_category
                )

                if (
                    rule.include_in_pnl is not None
                    and rule.include_in_cf is not None
                ):
                    transaction.classification_status = (
                        "classified"
                    )
                else:
                    transaction.classification_status = (
                        "partial"
                    )

                transaction.classification_source = "rule"

                matched += 1
                break

        session.commit()

    checked = len(transactions)

    return ApplyRulesResult(
        checked=checked,
        matched=matched,
        unmatched=checked - matched,
    )