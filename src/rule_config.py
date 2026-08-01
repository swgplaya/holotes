from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from src.rule_repository import (
    RuleImportPreview,
    get_rule_config_records,
    preview_rule_records,
)


RULE_CONFIG_SCHEMA_VERSION = 1

RULE_CONFIG_FIELDS = {
    "schema_version",
    "exported_at",
    "rules",
}


@dataclass(frozen=True)
class ParsedRuleConfig:
    """Проверенная конфигурация правил из JSON."""

    schema_version: int
    exported_at: str
    records: tuple[dict[str, Any], ...]
    preview: RuleImportPreview


def _current_utc_iso() -> str:
    """Возвращает текущее время UTC в ISO 8601."""

    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _validate_exported_at(value: object) -> str:
    """Проверяет дату формирования конфигурации."""

    if not isinstance(value, str):
        raise ValueError(
            "Поле 'exported_at' должно быть строкой."
        )

    normalized = value.strip()

    if not normalized:
        raise ValueError(
            "Поле 'exported_at' не должно быть пустым."
        )

    try:
        datetime.fromisoformat(
            normalized.replace(
                "Z",
                "+00:00",
            )
        )
    except ValueError as exc:
        raise ValueError(
            "Поле 'exported_at' содержит "
            "некорректную дату ISO 8601."
        ) from exc

    return normalized


def build_rule_config_document() -> dict[str, Any]:
    """Формирует переносимую конфигурацию правил."""

    return {
        "schema_version":
            RULE_CONFIG_SCHEMA_VERSION,
        "exported_at": _current_utc_iso(),
        "rules": get_rule_config_records(),
    }


def export_rule_config_json() -> str:
    """Возвращает конфигурацию правил как JSON."""

    document = build_rule_config_document()

    return json.dumps(
        document,
        ensure_ascii=False,
        indent=2,
    )


def parse_rule_config_json(
    source: str | bytes,
) -> ParsedRuleConfig:
    """
    Читает и предварительно проверяет JSON.

    База данных при этом не изменяется.
    """

    if isinstance(source, bytes):
        try:
            text = source.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValueError(
                "Файл должен быть сохранён "
                "в кодировке UTF-8."
            ) from exc

    elif isinstance(source, str):
        text = source

    else:
        raise TypeError(
            "Ожидалась строка JSON или bytes."
        )

    if not text.strip():
        raise ValueError(
            "Файл конфигурации пуст."
        )

    try:
        document = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "Некорректный JSON: "
            f"строка {exc.lineno}, "
            f"столбец {exc.colno}. "
            f"{exc.msg}"
        ) from exc

    if not isinstance(document, dict):
        raise ValueError(
            "Корневой элемент JSON "
            "должен быть объектом."
        )

    document_fields = set(document)

    missing_fields = (
        RULE_CONFIG_FIELDS
        - document_fields
    )

    if missing_fields:
        raise ValueError(
            "В конфигурации отсутствуют поля: "
            + ", ".join(
                sorted(missing_fields)
            )
            + "."
        )

    unknown_fields = (
        document_fields
        - RULE_CONFIG_FIELDS
    )

    if unknown_fields:
        raise ValueError(
            "В конфигурации найдены "
            "неизвестные поля: "
            + ", ".join(
                sorted(unknown_fields)
            )
            + "."
        )

    schema_version = document[
        "schema_version"
    ]

    if (
        isinstance(schema_version, bool)
        or not isinstance(
            schema_version,
            int,
        )
    ):
        raise ValueError(
            "Поле 'schema_version' "
            "должно быть целым числом."
        )

    if (
        schema_version
        != RULE_CONFIG_SCHEMA_VERSION
    ):
        raise ValueError(
            "Неподдерживаемая версия "
            "конфигурации правил: "
            f"{schema_version}. "
            "Поддерживается версия "
            f"{RULE_CONFIG_SCHEMA_VERSION}."
        )

    exported_at = _validate_exported_at(
        document["exported_at"]
    )

    records = document["rules"]

    if not isinstance(records, list):
        raise ValueError(
            "Поле 'rules' должно "
            "содержать JSON-массив."
        )

    preview = preview_rule_records(
        records
    )

    return ParsedRuleConfig(
        schema_version=schema_version,
        exported_at=exported_at,
        records=tuple(records),
        preview=preview,
    )