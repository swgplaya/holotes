from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import pandas as pd
from sqlalchemy import delete, select

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

@dataclass(frozen=True)
class RuleImportPreview:
    """Результат предварительной проверки правил."""

    received: int
    valid_unique: int
    duplicates_in_file: int
    duplicates_in_database: int
    errors: tuple[str, ...]
    normalized_rules: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class RuleImportResult:
    """Результат пакетного импорта правил."""

    mode: str
    received: int
    inserted: int
    skipped_duplicates: int
    deleted_existing: int

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

def _prepare_rule_values(
    *,
    name: str,
    priority: int,
    is_active: bool,
    direction_filter: str,
    match_field: str,
    match_type: str,
    match_value: str,
    pnl_action: str,
    pnl_category: str | None,
    cf_action: str,
    cf_category: str | None,
) -> dict[str, Any]:
    """Проверяет и нормализует данные одного правила."""

    clean_name = _optional_text(name)
    clean_match_value = _optional_text(
        match_value
    )

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

    include_in_pnl = _action_to_bool(
        pnl_action
    )

    include_in_cf = _action_to_bool(
        cf_action
    )

    clean_pnl_category = _optional_text(
        pnl_category
    )

    clean_cf_category = _optional_text(
        cf_category
    )

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

    return {
        "name": clean_name,
        "priority": int(priority),
        "is_active": bool(is_active),
        "direction_filter": direction_filter,
        "match_field": match_field,
        "match_type": match_type,
        "match_value": clean_match_value,
        "include_in_pnl": include_in_pnl,
        "pnl_category": clean_pnl_category,
        "include_in_cf": include_in_cf,
        "cf_category": clean_cf_category,
    }

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

    values = _prepare_rule_values(
        name=name,
        priority=priority,
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

    rule = ClassificationRule(**values)

    with SessionLocal() as session:
        session.add(rule)
        session.commit()
        session.refresh(rule)

        return int(rule.id)


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

RULE_CONFIG_FIELDS = {
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
}


def _rule_to_config_record(
    rule: ClassificationRule,
) -> dict[str, Any]:
    """Преобразует модель БД в переносимую конфигурацию."""

    return {
        "name": rule.name,
        "priority": rule.priority,
        "is_active": rule.is_active,
        "direction_filter": rule.direction_filter,
        "match_field": rule.match_field,
        "match_type": rule.match_type,
        "match_value": rule.match_value,
        "pnl_action": _bool_to_action(
            rule.include_in_pnl
        ),
        "pnl_category": rule.pnl_category or "",
        "cf_action": _bool_to_action(
            rule.include_in_cf
        ),
        "cf_category": rule.cf_category or "",
    }


def _model_to_rule_values(
    rule: ClassificationRule,
) -> dict[str, Any]:
    """Преобразует модель БД во внутренние значения."""

    return {
        "name": rule.name,
        "priority": rule.priority,
        "is_active": rule.is_active,
        "direction_filter": rule.direction_filter,
        "match_field": rule.match_field,
        "match_type": rule.match_type,
        "match_value": rule.match_value,
        "include_in_pnl": rule.include_in_pnl,
        "pnl_category": rule.pnl_category,
        "include_in_cf": rule.include_in_cf,
        "cf_category": rule.cf_category,
    }


def _rule_fingerprint(
    values: dict[str, Any],
) -> tuple[Any, ...]:
    """
    Возвращает содержательный идентификатор правила.

    ID и даты БД в сравнении не участвуют.
    """

    return (
        _normalize(values["name"]),
        int(values["priority"]),
        bool(values["is_active"]),
        str(values["direction_filter"]),
        str(values["match_field"]),
        str(values["match_type"]),
        _normalize(values["match_value"]),
        values["include_in_pnl"],
        _normalize(values["pnl_category"]),
        values["include_in_cf"],
        _normalize(values["cf_category"]),
    )


def _validate_rule_record(
    record: object,
    position: int,
) -> dict[str, Any]:
    """Проверяет одно правило из внешней конфигурации."""

    prefix = f"Правило {position}: "

    if not isinstance(record, dict):
        raise ValueError(
            prefix
            + "ожидался JSON-объект."
        )

    record_fields = set(record)

    missing_fields = (
        RULE_CONFIG_FIELDS
        - record_fields
    )

    if missing_fields:
        raise ValueError(
            prefix
            + "отсутствуют поля: "
            + ", ".join(
                sorted(missing_fields)
            )
            + "."
        )

    unknown_fields = (
        record_fields
        - RULE_CONFIG_FIELDS
    )

    if unknown_fields:
        raise ValueError(
            prefix
            + "неизвестные поля: "
            + ", ".join(
                sorted(unknown_fields)
            )
            + "."
        )

    text_fields = (
        "name",
        "direction_filter",
        "match_field",
        "match_type",
        "match_value",
        "pnl_action",
        "cf_action",
    )

    for field_name in text_fields:
        if not isinstance(
            record[field_name],
            str,
        ):
            raise ValueError(
                prefix
                + f"поле {field_name!r} "
                + "должно быть строкой."
            )

    for category_field in (
        "pnl_category",
        "cf_category",
    ):
        category_value = record[
            category_field
        ]

        if (
            category_value is not None
            and not isinstance(
                category_value,
                str,
            )
        ):
            raise ValueError(
                prefix
                + f"поле {category_field!r} "
                + "должно быть строкой или null."
            )

    priority = record["priority"]

    if (
        isinstance(priority, bool)
        or not isinstance(priority, int)
    ):
        raise ValueError(
            prefix
            + "поле 'priority' должно быть целым числом."
        )

    is_active = record["is_active"]

    if not isinstance(is_active, bool):
        raise ValueError(
            prefix
            + "поле 'is_active' должно быть "
            + "логическим значением."
        )

    try:
        return _prepare_rule_values(
            name=record["name"],
            priority=priority,
            is_active=is_active,
            direction_filter=record[
                "direction_filter"
            ],
            match_field=record["match_field"],
            match_type=record["match_type"],
            match_value=record["match_value"],
            pnl_action=record["pnl_action"],
            pnl_category=record["pnl_category"],
            cf_action=record["cf_action"],
            cf_category=record["cf_category"],
        )
    except ValueError as exc:
        raise ValueError(
            prefix + str(exc)
        ) from exc


def get_rule_config_records() -> list[dict[str, Any]]:
    """Возвращает правила в переносимом формате."""

    statement = (
        select(ClassificationRule)
        .order_by(
            ClassificationRule.priority.desc(),
            ClassificationRule.id.asc(),
        )
    )

    with SessionLocal() as session:
        rules = session.scalars(
            statement
        ).all()

        return [
            _rule_to_config_record(rule)
            for rule in rules
        ]


def preview_rule_records(
    records: object,
) -> RuleImportPreview:
    """Проверяет правила без изменения базы."""

    if not isinstance(records, list):
        raise ValueError(
            "Поле rules должно содержать JSON-массив."
        )

    errors: list[str] = []

    normalized_rules: list[
        dict[str, Any]
    ] = []

    file_fingerprints: set[
        tuple[Any, ...]
    ] = set()

    duplicates_in_file = 0

    for position, record in enumerate(
        records,
        start=1,
    ):
        try:
            values = _validate_rule_record(
                record,
                position,
            )
        except ValueError as exc:
            errors.append(str(exc))
            continue

        fingerprint = _rule_fingerprint(
            values
        )

        if fingerprint in file_fingerprints:
            duplicates_in_file += 1
            continue

        file_fingerprints.add(
            fingerprint
        )

        normalized_rules.append(
            values
        )

    with SessionLocal() as session:
        existing_rules = session.scalars(
            select(ClassificationRule)
        ).all()

        existing_fingerprints = {
            _rule_fingerprint(
                _model_to_rule_values(rule)
            )
            for rule in existing_rules
        }

    duplicates_in_database = sum(
        1
        for values in normalized_rules
        if _rule_fingerprint(values)
        in existing_fingerprints
    )

    return RuleImportPreview(
        received=len(records),
        valid_unique=len(normalized_rules),
        duplicates_in_file=duplicates_in_file,
        duplicates_in_database=(
            duplicates_in_database
        ),
        errors=tuple(errors),
        normalized_rules=tuple(
            normalized_rules
        ),
    )


def import_rule_records(
    records: object,
    *,
    mode: str,
) -> RuleImportResult:
    """
    Импортирует правила атомарно.

    merge — добавляет только отсутствующие правила.
    replace — удаляет текущие правила и загружает новые.
    """

    if mode not in {
        "merge",
        "replace",
    }:
        raise ValueError(
            "Неизвестный режим импорта правил."
        )

    preview = preview_rule_records(
        records
    )

    if preview.errors:
        raise ValueError(
            "\n".join(preview.errors)
        )

    with SessionLocal() as session:
        existing_rules = session.scalars(
            select(ClassificationRule)
        ).all()

        deleted_existing = 0

        if mode == "replace":
            deleted_existing = len(
                existing_rules
            )

            session.execute(
                delete(ClassificationRule)
            )

            existing_fingerprints: set[
                tuple[Any, ...]
            ] = set()
        else:
            existing_fingerprints = {
                _rule_fingerprint(
                    _model_to_rule_values(rule)
                )
                for rule in existing_rules
            }

        inserted = 0
        skipped_existing = 0

        for values in preview.normalized_rules:
            fingerprint = _rule_fingerprint(
                values
            )

            if fingerprint in existing_fingerprints:
                skipped_existing += 1
                continue

            session.add(
                ClassificationRule(**values)
            )

            existing_fingerprints.add(
                fingerprint
            )

            inserted += 1

        session.commit()

    return RuleImportResult(
        mode=mode,
        received=preview.received,
        inserted=inserted,
        skipped_duplicates=(
            preview.duplicates_in_file
            + skipped_existing
        ),
        deleted_existing=deleted_existing,
    )

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