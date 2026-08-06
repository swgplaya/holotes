from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

import src.telegram_token as telegram_token


class FakeResponse:
    """Minimal urlopen response for getMe tests."""

    def __init__(
        self,
        body: bytes,
    ) -> None:
        self.body = body

    def __enter__(
        self,
    ) -> FakeResponse:
        return self

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        del (
            exc_type,
            exc_value,
            traceback,
        )

    def read(
        self,
    ) -> bytes:
        return self.body


@pytest.fixture
def isolated_env_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    """Uses an isolated dotenv file."""

    env_path = (
        tmp_path
        / ".env"
    )

    monkeypatch.setattr(
        telegram_token,
        "ENV_PATH",
        env_path,
    )

    monkeypatch.delenv(
        telegram_token.TOKEN_ENV_NAME,
        raising=False,
    )

    return env_path


def make_identity() -> (
    telegram_token.TelegramBotIdentity
):
    """Returns a stable test bot identity."""

    return telegram_token.TelegramBotIdentity(
        bot_id=123456789,
        username="holotes_test_bot",
        display_name="Holotes Test",
        can_join_groups=True,
        can_read_all_group_messages=False,
    )


def test_missing_token_is_not_configured(
    isolated_env_path: Path,
) -> None:
    assert isolated_env_path.exists() is False

    assert (
        telegram_token
        .is_telegram_bot_token_configured()
        is False
    )

    with pytest.raises(
        telegram_token.TelegramTokenError,
        match="not configured",
    ):
        telegram_token.load_telegram_bot_token()


def test_validate_token_parses_get_me(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {
        "ok": True,
        "result": {
            "id": 123456789,
            "is_bot": True,
            "first_name": "Holotes",
            "last_name": "Finance",
            "username": "holotes_bot",
            "can_join_groups": True,
            "can_read_all_group_messages": False,
        },
    }

    response_body = json.dumps(
        payload
    ).encode(
        "utf-8"
    )

    def fake_urlopen(
        request: object,
        timeout: float,
    ) -> FakeResponse:
        del request

        assert timeout == 7

        return FakeResponse(
            response_body
        )

    monkeypatch.setattr(
        telegram_token,
        "urlopen",
        fake_urlopen,
    )

    identity = (
        telegram_token
        .validate_telegram_bot_token(
            "123456:TEST_TOKEN",
            timeout=7,
        )
    )

    assert identity.bot_id == 123456789

    assert (
        identity.username
        == "holotes_bot"
    )

    assert (
        identity.display_name
        == "Holotes Finance"
    )

    assert identity.can_join_groups is True

    assert (
        identity.can_read_all_group_messages
        is False
    )


@pytest.mark.parametrize(
    "response_body",
    [
        json.dumps(
            {
                "ok": False,
                "description": (
                    "Unauthorized"
                ),
            }
        ).encode(
            "utf-8"
        ),
        json.dumps(
            {
                "ok": True,
                "result": {
                    "id": 123,
                    "is_bot": False,
                },
            }
        ).encode(
            "utf-8"
        ),
        b"not-json",
    ],
)
def test_validate_rejects_invalid_response(
    monkeypatch: pytest.MonkeyPatch,
    response_body: bytes,
) -> None:
    secret_token = (
        "123456:SUPER_SECRET_TOKEN"
    )

    monkeypatch.setattr(
        telegram_token,
        "urlopen",
        lambda request, timeout: FakeResponse(
            response_body
        ),
    )

    with pytest.raises(
        telegram_token.TelegramTokenError
    ) as error:
        (
            telegram_token
            .validate_telegram_bot_token(
                secret_token
            )
        )

    assert (
        secret_token
        not in str(
            error.value
        )
    )


def test_save_preserves_other_env_values(
    isolated_env_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    isolated_env_path.write_text(
        (
            "# Holotes\n"
            "DATABASE_URL=sqlite:///data/test.db\n"
            "TBANK_API_TOKEN=existing-value\n"
        ),
        encoding="utf-8",
    )

    identity = make_identity()

    monkeypatch.setattr(
        telegram_token,
        "_request_bot_identity",
        lambda token, timeout: identity,
    )

    result = (
        telegram_token
        .save_telegram_bot_token(
            "123456:NEW_TOKEN"
        )
    )

    assert result == identity

    saved_text = (
        isolated_env_path.read_text(
            encoding="utf-8"
        )
    )

    assert (
        "DATABASE_URL="
        "sqlite:///data/test.db"
        in saved_text
    )

    assert (
        "TBANK_API_TOKEN=existing-value"
        in saved_text
    )

    assert (
        "TELEGRAM_BOT_TOKEN="
        "123456:NEW_TOKEN"
        in saved_text
    )

    assert (
        os.environ[
            telegram_token.TOKEN_ENV_NAME
        ]
        == "123456:NEW_TOKEN"
    )


def test_save_replaces_duplicate_assignments(
    isolated_env_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    isolated_env_path.write_text(
        (
            "TELEGRAM_BOT_TOKEN=old-one\n"
            "OTHER_SETTING=value\n"
            "export TELEGRAM_BOT_TOKEN=old-two\n"
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        telegram_token,
        "_request_bot_identity",
        lambda token, timeout: make_identity(),
    )

    telegram_token.save_telegram_bot_token(
        "123456:REPLACEMENT"
    )

    saved_text = (
        isolated_env_path.read_text(
            encoding="utf-8"
        )
    )

    assert saved_text.count(
        "TELEGRAM_BOT_TOKEN="
    ) == 1

    assert "old-one" not in saved_text
    assert "old-two" not in saved_text

    assert (
        "OTHER_SETTING=value"
        in saved_text
    )

    assert (
        "123456:REPLACEMENT"
        in saved_text
    )


def test_failed_validation_does_not_change_env(
    isolated_env_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_text = (
        "OTHER_SETTING=untouched\n"
    )

    isolated_env_path.write_text(
        original_text,
        encoding="utf-8",
    )

    def reject_token(
        token: str,
        *,
        timeout: float,
    ) -> Any:
        del (
            token,
            timeout,
        )

        raise telegram_token.TelegramTokenError(
            "Rejected."
        )

    monkeypatch.setattr(
        telegram_token,
        "_request_bot_identity",
        reject_token,
    )

    with pytest.raises(
        telegram_token.TelegramTokenError,
        match="Rejected",
    ):
        telegram_token.save_telegram_bot_token(
            "123456:INVALID"
        )

    assert (
        isolated_env_path.read_text(
            encoding="utf-8"
        )
        == original_text
    )

    assert (
        telegram_token.TOKEN_ENV_NAME
        not in os.environ
    )


def test_delete_removes_only_telegram_token(
    isolated_env_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    isolated_env_path.write_text(
        (
            "DATABASE_URL=sqlite:///data/test.db\n"
            "TELEGRAM_BOT_TOKEN=123456:TOKEN\n"
            "OTHER_SETTING=value\n"
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv(
        telegram_token.TOKEN_ENV_NAME,
        "123456:TOKEN",
    )

    deleted = (
        telegram_token
        .delete_telegram_bot_token()
    )

    assert deleted is True

    saved_text = (
        isolated_env_path.read_text(
            encoding="utf-8"
        )
    )

    assert (
        "TELEGRAM_BOT_TOKEN"
        not in saved_text
    )

    assert (
        "DATABASE_URL="
        "sqlite:///data/test.db"
        in saved_text
    )

    assert (
        "OTHER_SETTING=value"
        in saved_text
    )

    assert (
        telegram_token.TOKEN_ENV_NAME
        not in os.environ
    )
