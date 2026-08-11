import pytest

from src.telegram_mtproto import (
    TelegramMtProxyConfig,
    TelegramMtProxyConfigError,
    parse_mtproxy_url,
)


TEST_RANDOM_PADDING_SECRET = "dd" + ("0" * 32)
TEST_PLAIN_SECRET = "0" * 32
TEST_ENV_PROXY_SECRET = "".join(
    ("01234567", "89abcdef")
)


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (
            (
                "tg://proxy?"
                "server=proxy.example.com&"
                "port=443&"
                f"secret={TEST_RANDOM_PADDING_SECRET}"
            ),
            TelegramMtProxyConfig(
                host="proxy.example.com",
                port=443,
                secret=TEST_RANDOM_PADDING_SECRET,
            ),
        ),
        (
            (
                "https://t.me/proxy?"
                "server=203.0.113.10&"
                "port=8443&"
                f"secret={TEST_PLAIN_SECRET}"
            ),
            TelegramMtProxyConfig(
                host="203.0.113.10",
                port=8443,
                secret=TEST_PLAIN_SECRET,
            ),
        ),
    ],
)
def test_parse_mtproxy_url(
    url,
    expected,
):
    assert parse_mtproxy_url(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        "",
        "tg://socks?server=example.com&port=443",
        "https://example.com/proxy?server=x&port=443&secret=y",
        "tg://proxy?port=443&secret=abc",
        "tg://proxy?server=example.com&secret=abc",
        "tg://proxy?server=example.com&port=443",
        "tg://proxy?server=example.com&port=abc&secret=abc",
        "tg://proxy?server=example.com&port=0&secret=abc",
        "tg://proxy?server=example.com&port=65536&secret=abc",
    ],
)
def test_parse_mtproxy_url_rejects_invalid_links(
    url,
):
    with pytest.raises(
        TelegramMtProxyConfigError
    ):
        parse_mtproxy_url(url)


def test_parse_mtproxy_url_decodes_query_parameters():
    config = parse_mtproxy_url(
        "tg://proxy?"
        "server=proxy.example.com&"
        "port=443&"
        "secret=eeabcdef%2Fexample.com"
    )

    assert config.host == "proxy.example.com"
    assert config.port == 443
    assert config.secret == "eeabcdef/example.com"


def test_get_telegram_transport_defaults_to_bot_api(
    tmp_path,
    monkeypatch,
):
    from src.telegram_mtproto import (
        get_telegram_transport,
    )

    monkeypatch.delenv(
        "TELEGRAM_TRANSPORT",
        raising=False,
    )

    env_path = tmp_path / ".env"
    env_path.write_text(
        "",
        encoding="utf-8",
    )

    assert (
        get_telegram_transport(
            env_path=env_path
        )
        == "bot_api"
    )


def test_get_telegram_transport_reads_mtproto(
    tmp_path,
    monkeypatch,
):
    from src.telegram_mtproto import (
        get_telegram_transport,
    )

    monkeypatch.delenv(
        "TELEGRAM_TRANSPORT",
        raising=False,
    )

    env_path = tmp_path / ".env"
    env_path.write_text(
        "TELEGRAM_TRANSPORT=mtproto\n",
        encoding="utf-8",
    )

    assert (
        get_telegram_transport(
            env_path=env_path
        )
        == "mtproto"
    )


def test_load_mtproto_settings_with_proxy(
    tmp_path,
    monkeypatch,
):
    from src.telegram_mtproto import (
        load_mtproto_settings,
    )

    for name in (
        "TELEGRAM_API_ID",
        "TELEGRAM_API_HASH",
        "TELEGRAM_MTPROXY_URL",
    ):
        monkeypatch.delenv(
            name,
            raising=False,
        )

    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "TELEGRAM_API_ID=12345",
                "TELEGRAM_API_HASH=abcdef",
                (
                    "TELEGRAM_MTPROXY_URL="
                    "tg://proxy?"
                    "server=proxy.example.com&"
                    "port=443&"
                    f"secret={TEST_ENV_PROXY_SECRET}"
                ),
                "",
            ]
        ),
        encoding="utf-8",
    )

    settings = load_mtproto_settings(
        env_path=env_path,
        session_path=(
            tmp_path / "telegram"
        ),
    )

    assert settings.api_id == 12345
    assert settings.api_hash == "abcdef"
    assert settings.proxy is not None
    assert (
        settings.proxy.host
        == "proxy.example.com"
    )
    assert settings.proxy.port == 443


def test_load_mtproto_settings_rejects_bad_api_id(
    tmp_path,
    monkeypatch,
):
    from src.telegram_mtproto import (
        TelegramMtProxyConfigError,
        load_mtproto_settings,
    )

    for name in (
        "TELEGRAM_API_ID",
        "TELEGRAM_API_HASH",
        "TELEGRAM_MTPROXY_URL",
    ):
        monkeypatch.delenv(
            name,
            raising=False,
        )

    env_path = tmp_path / ".env"
    env_path.write_text(
        (
            "TELEGRAM_API_ID=nope\n"
            "TELEGRAM_API_HASH=abcdef\n"
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        TelegramMtProxyConfigError
    ):
        load_mtproto_settings(
            env_path=env_path
        )


def test_probe_mtproto_bot(
    tmp_path,
    monkeypatch,
):
    import asyncio
    from types import SimpleNamespace

    import src.telegram_mtproto as module

    calls = []

    class FakeClient:
        async def start(
            self,
            *,
            bot_token,
        ):
            calls.append(
                (
                    "start",
                    bot_token,
                )
            )

        async def get_me(
            self,
        ):
            calls.append(
                ("get_me",)
            )

            return SimpleNamespace(
                id=123456,
                username="holotes_bot",
                bot=True,
            )

        async def disconnect(
            self,
        ):
            calls.append(
                ("disconnect",)
            )

    monkeypatch.setattr(
        module,
        "build_mtproto_client",
        lambda settings: FakeClient(),
    )

    settings = module.TelegramMtprotoSettings(
        api_id=12345,
        api_hash="abcdef",
        proxy=None,
        session_path=(
            tmp_path / "telegram"
        ),
    )

    result = asyncio.run(
        module.probe_mtproto_bot(
            "123:token",
            settings,
        )
    )

    assert result.telegram_user_id == 123456
    assert result.username == "holotes_bot"

    assert calls == [
        (
            "start",
            "123:token",
        ),
        ("get_me",),
        ("disconnect",),
    ]


def test_probe_mtproto_bot_disconnects_after_failure(
    tmp_path,
    monkeypatch,
):
    import asyncio

    import src.telegram_mtproto as module

    disconnected = []

    class FakeClient:
        async def start(
            self,
            *,
            bot_token,
        ):
            raise OSError(
                "network unavailable"
            )

        async def get_me(
            self,
        ):
            raise AssertionError(
                "must not be called"
            )

        async def disconnect(
            self,
        ):
            disconnected.append(
                True
            )

    monkeypatch.setattr(
        module,
        "build_mtproto_client",
        lambda settings: FakeClient(),
    )

    settings = module.TelegramMtprotoSettings(
        api_id=12345,
        api_hash="abcdef",
        proxy=None,
        session_path=(
            tmp_path / "telegram"
        ),
    )

    with pytest.raises(
        module.TelegramMtprotoConnectionError
    ):
        asyncio.run(
            module.probe_mtproto_bot(
                "123:token",
                settings,
            )
        )

    assert disconnected == [
        True
    ]


@pytest.mark.parametrize(
    ("peer", "expected"),
    [
        (
            __import__(
                "telethon.tl.types",
                fromlist=["User"],
            ).User(
                id=123,
                is_self=False,
                contact=False,
                mutual_contact=False,
                deleted=False,
                bot=False,
                bot_chat_history=False,
                bot_nochats=False,
                verified=False,
                restricted=False,
                min=False,
                bot_inline_geo=False,
                support=False,
                scam=False,
                apply_min_photo=False,
                fake=False,
                bot_attach_menu=False,
                premium=False,
                attach_menu_enabled=False,
                bot_can_edit=False,
                close_friend=False,
                stories_hidden=False,
                stories_unavailable=False,
                contact_require_premium=False,
                bot_business=False,
                bot_has_main_app=False,
                access_hash=None,
                first_name=None,
                last_name=None,
                username=None,
                phone=None,
                photo=None,
                status=None,
                bot_info_version=None,
                restriction_reason=None,
                bot_inline_placeholder=None,
                lang_code=None,
                emoji_status=None,
                usernames=None,
                stories_max_id=None,
                color=None,
                profile_color=None,
                bot_active_users=None,
                bot_verification_icon=None,
                send_paid_messages_stars=None,
            ),
            123,
        ),
        (
            __import__(
                "telethon.tl.types",
                fromlist=["Chat"],
            ).Chat(
                id=456,
                title="Group",
                photo=__import__(
                    "telethon.tl.types",
                    fromlist=["ChatPhotoEmpty"],
                ).ChatPhotoEmpty(),
                participants_count=2,
                date=None,
                version=1,
                creator=False,
                left=False,
                deactivated=False,
                call_active=False,
                call_not_empty=False,
                noforwards=False,
                migrated_to=None,
                admin_rights=None,
                default_banned_rights=None,
            ),
            -456,
        ),
    ],
)
def test_mtproto_peer_to_bot_api_chat_id(
    peer,
    expected,
):
    from src.telegram_mtproto import (
        mtproto_peer_to_bot_api_chat_id,
    )

    assert (
        mtproto_peer_to_bot_api_chat_id(
            peer
        )
        == expected
    )


def test_mtproto_channel_to_bot_api_chat_id():
    from telethon.tl.types import Channel

    from src.telegram_mtproto import (
        mtproto_peer_to_bot_api_chat_id,
    )

    channel = object.__new__(
        Channel
    )
    channel.id = 789

    assert (
        mtproto_peer_to_bot_api_chat_id(
            channel
        )
        == -1_000_000_000_789
    )


def test_mtproto_chat_type():
    from telethon.tl.types import (
        Channel,
        Chat,
        User,
    )

    from src.telegram_mtproto import (
        mtproto_chat_type,
    )

    user = object.__new__(User)
    chat = object.__new__(Chat)
    channel = object.__new__(Channel)

    channel.megagroup = True

    assert mtproto_chat_type(user) == "private"
    assert mtproto_chat_type(chat) == "group"
    assert (
        mtproto_chat_type(channel)
        == "supergroup"
    )

    channel.megagroup = False

    assert (
        mtproto_chat_type(channel)
        == "channel"
    )


@pytest.mark.parametrize(
    (
        "forum_topic",
        "reply_to_top_id",
        "reply_to_msg_id",
        "expected_thread_id",
    ),
    [
        (
            True,
            None,
            4,
            4,
        ),
        (
            True,
            4,
            95600,
            4,
        ),
        (
            False,
            None,
            95600,
            None,
        ),
    ],
)
def test_extract_mtproto_message_context_preserves_forum_topic(
    forum_topic,
    reply_to_top_id,
    reply_to_msg_id,
    expected_thread_id,
):
    import asyncio
    from types import SimpleNamespace

    from telethon.tl.types import Channel

    from src.telegram_mtproto import (
        extract_mtproto_message_context,
    )

    channel = object.__new__(
        Channel
    )
    channel.id = 789
    channel.megagroup = True

    sender = SimpleNamespace(
        id=123456789,
        lang_code="ru",
    )

    message = SimpleNamespace(
        id=95682,
        reply_to=SimpleNamespace(
            forum_topic=forum_topic,
            reply_to_top_id=reply_to_top_id,
            reply_to_msg_id=reply_to_msg_id,
        ),
    )

    class FakeEvent:
        raw_text = "/summary@holotes_bot"

        def __init__(self):
            self.message = message

        async def get_sender(self):
            return sender

        async def get_chat(self):
            return channel

    context = asyncio.run(
        extract_mtproto_message_context(
            FakeEvent()
        )
    )

    assert context is not None
    assert (
        context.telegram_chat_id
        == -1_000_000_000_789
    )
    assert context.chat_type == "supergroup"
    assert context.message_thread_id == expected_thread_id


def test_send_mtproto_text_splits_messages():
    import asyncio

    import src.telegram_mtproto as module

    calls = []

    class FakeClient:
        async def send_message(
            self,
            entity,
            text,
            **kwargs,
        ):
            calls.append(
                (
                    entity,
                    text,
                    kwargs,
                )
            )

    asyncio.run(
        module.send_mtproto_text(
            client=FakeClient(),
            entity="chat",
            text="abcdefgh",
            chunk_limit=4,
        )
    )

    assert calls == [
        (
            "chat",
            "abcd",
            {},
        ),
        (
            "chat",
            "efgh",
            {},
        ),
    ]


def test_mtproto_config_error_is_base_for_proxy_error():
    import src.telegram_mtproto as module

    assert issubclass(
        module.TelegramMtProxyConfigError,
        module.TelegramMtprotoConfigError,
    )


def test_probe_mtproto_bot_rejects_empty_token():
    import asyncio

    import pytest

    import src.telegram_mtproto as module

    settings = module.TelegramMtprotoSettings(
        api_id=1,
        api_hash="hash",
        proxy=None,
        session_path=module.DEFAULT_SESSION_PATH,
    )

    with pytest.raises(
        module.TelegramMtprotoConfigError
    ):
        asyncio.run(
            module.probe_mtproto_bot(
                "",
                settings,
            )
        )
