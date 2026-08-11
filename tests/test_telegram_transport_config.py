from __future__ import annotations

from pathlib import Path

import pytest

import src.telegram_transport_config as config


@pytest.fixture
def isolated_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    path = tmp_path / ".env"

    for name in config.MANAGED_ENV_NAMES:
        monkeypatch.delenv(
            name,
            raising=False,
        )

    return path


def test_defaults_to_bot_api(
    isolated_env: Path,
) -> None:
    result = config.get_telegram_transport_config(
        env_path=isolated_env
    )

    assert result.transport == "bot_api"
    assert result.api_id == ""
    assert result.api_hash_configured is False
    assert result.mtproxy_configured is False


def test_save_mtproto_preserves_other_env_values(
    isolated_env: Path,
) -> None:
    isolated_env.write_text(
        (
            "DATABASE_URL=sqlite:///data/test.db\n"
            "TELEGRAM_BOT_TOKEN=123:TOKEN\n"
        ),
        encoding="utf-8",
    )

    saved = config.save_telegram_transport_config(
        transport="mtproto",
        api_id="123456",
        api_hash="test-api-hash",
        mtproxy_url=(
            "tg://proxy?"
            "server=proxy.example.com"
            "&port=9443"
            "&secret=dd00112233445" "566778899aabbccddeeff"
        ),
        env_path=isolated_env,
    )

    text = isolated_env.read_text(
        encoding="utf-8"
    )

    assert saved.transport == "mtproto"
    assert saved.api_id == "123456"
    assert saved.api_hash_configured is True
    assert saved.mtproxy_configured is True

    assert (
        "DATABASE_URL=sqlite:///data/test.db"
        in text
    )
    assert (
        "TELEGRAM_BOT_TOKEN=123:TOKEN"
        in text
    )


def test_blank_secrets_keep_existing_values(
    isolated_env: Path,
) -> None:
    isolated_env.write_text(
        (
            "TELEGRAM_TRANSPORT=mtproto\n"
            "TELEGRAM_API_ID=123456\n"
            "TELEGRAM_API_HASH=existing-hash\n"
            "TELEGRAM_MTPROXY_URL="
            "tg://proxy?server=proxy.example.com"
            "&port=9443"
            "&secret=dd001122334455" "66778899aabbccddeeff\n"
        ),
        encoding="utf-8",
    )

    config.save_telegram_transport_config(
        transport="mtproto",
        api_id="123456",
        api_hash="",
        mtproxy_url="",
        env_path=isolated_env,
    )

    text = isolated_env.read_text(
        encoding="utf-8"
    )

    assert (
        "TELEGRAM_API_HASH=existing-hash"
        in text
    )

    assert (
        "secret=dd00112233445" "566778899aabbccddeeff"
        in text
    )


def test_switch_to_bot_api_does_not_delete_mtproto_secrets(
    isolated_env: Path,
) -> None:
    isolated_env.write_text(
        (
            "TELEGRAM_TRANSPORT=mtproto\n"
            "TELEGRAM_API_ID=123456\n"
            "TELEGRAM_API_HASH=existing-hash\n"
            "TELEGRAM_MTPROXY_URL="
            "tg://proxy?server=proxy.example.com"
            "&port=9443"
            "&secret=dd001122334455" "66778899aabbccddeeff\n"
        ),
        encoding="utf-8",
    )

    result = config.save_telegram_transport_config(
        transport="bot_api",
        env_path=isolated_env,
    )

    text = isolated_env.read_text(
        encoding="utf-8"
    )

    assert result.transport == "bot_api"
    assert "TELEGRAM_API_HASH=existing-hash" in text
    assert "TELEGRAM_MTPROXY_URL=" in text


@pytest.mark.parametrize(
    (
        "api_id",
        "api_hash",
        "proxy",
    ),
    [
        (
            "",
            "hash",
            "tg://proxy?server=x&port=443&secret=dd00",
        ),
        (
            "123",
            "",
            "tg://proxy?server=x&port=443&secret=dd00",
        ),
        (
            "123",
            "hash",
            "",
        ),
    ],
)
def test_mtproto_requires_complete_configuration(
    isolated_env: Path,
    api_id: str,
    api_hash: str,
    proxy: str,
) -> None:
    with pytest.raises(
        config.TelegramTransportConfigError
    ):
        config.save_telegram_transport_config(
            transport="mtproto",
            api_id=api_id,
            api_hash=api_hash,
            mtproxy_url=proxy,
            env_path=isolated_env,
        )


def test_save_falls_back_to_in_place_write_when_replace_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_path = tmp_path / ".env"

    env_path.write_text(
        "DATABASE_URL=sqlite:///data/test.db\n",
        encoding="utf-8",
    )

    def fail_replace(
        source: object,
        destination: object,
    ) -> None:
        del source, destination
        raise OSError(
            "bind mount cannot be replaced"
        )

    monkeypatch.setattr(
        config.os,
        "replace",
        fail_replace,
    )

    config.save_telegram_transport_config(
        transport="bot_api",
        env_path=env_path,
    )

    saved_text = env_path.read_text(
        encoding="utf-8"
    )

    assert (
        "DATABASE_URL=sqlite:///data/test.db"
        in saved_text
    )
    assert (
        "TELEGRAM_TRANSPORT=bot_api"
        in saved_text
    )
