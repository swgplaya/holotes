import json

import pytest

import src.rule_config as rule_config
from src.categories import INCLUDE_ACTION
from src.rule_repository import RuleImportPreview


VALID_RULE = {
    "name": "Банковские комиссии",
    "priority": 100,
    "is_active": True,
    "direction_filter": "expense",
    "match_field": "description",
    "match_type": "contains",
    "match_value": "комиссия",
    "pnl_action": INCLUDE_ACTION,
    "pnl_category": "Банковские комиссии",
    "cf_action": INCLUDE_ACTION,
    "cf_category": "Банковские расходы",
}


def make_document(
    **overrides: object,
) -> dict[str, object]:
    """Создаёт корректный документ конфигурации."""

    document: dict[str, object] = {
        "schema_version": 1,
        "exported_at": "2026-08-04T18:00:00Z",
        "rules": [
            VALID_RULE.copy(),
        ],
    }

    document.update(overrides)

    return document


def empty_preview(
    records: list[object],
) -> RuleImportPreview:
    """Создаёт успешный результат предпросмотра."""

    return RuleImportPreview(
        received=len(records),
        valid_unique=len(records),
        duplicates_in_file=0,
        duplicates_in_database=0,
        errors=(),
        normalized_rules=tuple(
            record
            for record in records
            if isinstance(record, dict)
        ),
    )


def test_build_document_uses_schema_time_and_records(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    records = [
        VALID_RULE.copy(),
    ]

    monkeypatch.setattr(
        rule_config,
        "_current_utc_iso",
        lambda: "2026-08-04T18:00:00Z",
    )

    monkeypatch.setattr(
        rule_config,
        "get_rule_config_records",
        lambda: records,
    )

    result = (
        rule_config.build_rule_config_document()
    )

    assert result == {
        "schema_version": 1,
        "exported_at":
            "2026-08-04T18:00:00Z",
        "rules": records,
    }


def test_export_json_is_readable_and_preserves_unicode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document = make_document()

    monkeypatch.setattr(
        rule_config,
        "build_rule_config_document",
        lambda: document,
    )

    result = (
        rule_config.export_rule_config_json()
    )

    assert json.loads(result) == document

    assert "Банковские комиссии" in result
    assert "\\u0411" not in result

    assert result.startswith(
        "{\n  "
    )


def test_parse_valid_json_returns_records_and_preview(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[list[object]] = []

    def fake_preview(
        records: list[object],
    ) -> RuleImportPreview:
        captured.append(records)

        return empty_preview(records)

    monkeypatch.setattr(
        rule_config,
        "preview_rule_records",
        fake_preview,
    )

    document = make_document()

    result = rule_config.parse_rule_config_json(
        json.dumps(
            document,
            ensure_ascii=False,
        )
    )

    assert result.schema_version == 1

    assert result.exported_at == (
        "2026-08-04T18:00:00Z"
    )

    assert result.records == (
        VALID_RULE,
    )

    assert result.preview.received == 1

    assert captured == [
        document["rules"],
    ]


def test_parse_accepts_utf8_bom_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        rule_config,
        "preview_rule_records",
        empty_preview,
    )

    source = json.dumps(
        make_document(),
        ensure_ascii=False,
    ).encode(
        "utf-8-sig"
    )

    result = (
        rule_config.parse_rule_config_json(
            source
        )
    )

    assert result.records == (
        VALID_RULE,
    )


@pytest.mark.parametrize(
    (
        "source",
        "error_type",
        "message",
    ),
    [
        (
            "",
            ValueError,
            "Файл конфигурации пуст",
        ),
        (
            "{broken",
            ValueError,
            "Некорректный JSON",
        ),
        (
            "[]",
            ValueError,
            (
                "Корневой элемент JSON "
                "должен быть объектом"
            ),
        ),
        (
            123,
            TypeError,
            (
                "Ожидалась строка JSON "
                "или bytes"
            ),
        ),
        (
            b"\xff\xfe",
            ValueError,
            "кодировке UTF-8",
        ),
    ],
)
def test_parse_rejects_invalid_sources(
    source: object,
    error_type: type[Exception],
    message: str,
) -> None:
    with pytest.raises(
        error_type,
        match=message,
    ):
        rule_config.parse_rule_config_json(
            source  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    (
        "document",
        "message",
    ),
    [
        (
            {
                "schema_version": 1,
                "exported_at":
                    "2026-08-04T18:00:00Z",
            },
            "отсутствуют поля: rules",
        ),
        (
            {
                **make_document(),
                "unexpected": True,
            },
            "неизвестные поля: unexpected",
        ),
        (
            make_document(
                schema_version=True,
            ),
            (
                "schema_version.*"
                "целым числом"
            ),
        ),
        (
            make_document(
                schema_version=2,
            ),
            "Неподдерживаемая версия",
        ),
        (
            make_document(
                exported_at="",
            ),
            (
                "exported_at.*"
                "не должно быть пустым"
            ),
        ),
        (
            make_document(
                exported_at="not-a-date",
            ),
            (
                "некорректную дату "
                "ISO 8601"
            ),
        ),
        (
            make_document(
                rules={},
            ),
            "rules.*JSON-массив",
        ),
    ],
)
def test_parse_rejects_invalid_document_structure(
    document: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(
        ValueError,
        match=message,
    ):
        rule_config.parse_rule_config_json(
            json.dumps(
                document,
                ensure_ascii=False,
            )
        )


def test_parse_preserves_preview_validation_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    preview = RuleImportPreview(
        received=2,
        valid_unique=1,
        duplicates_in_file=1,
        duplicates_in_database=1,
        errors=(
            "Правило 2: ошибка.",
        ),
        normalized_rules=(
            {
                "name": "Нормализовано",
            },
        ),
    )

    monkeypatch.setattr(
        rule_config,
        "preview_rule_records",
        lambda records: preview,
    )

    document = make_document(
        rules=[
            VALID_RULE.copy(),
            VALID_RULE.copy(),
        ]
    )

    result = (
        rule_config.parse_rule_config_json(
            json.dumps(
                document,
                ensure_ascii=False,
            )
        )
    )

    assert result.preview is preview

    assert (
        result.preview.duplicates_in_file
        == 1
    )

    assert (
        result.preview.duplicates_in_database
        == 1
    )

    assert result.preview.errors == (
        "Правило 2: ошибка.",
    )