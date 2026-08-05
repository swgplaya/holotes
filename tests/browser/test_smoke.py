from __future__ import annotations

import re

import pytest
from playwright.sync_api import (
    Page,
    expect,
)


pytestmark = pytest.mark.browser


def test_open_mas_starts_and_opens_settings(
    page: Page,
    streamlit_base_url: str,
) -> None:
    """Checks startup and Telegram settings."""

    page.goto(
        streamlit_base_url,
        wait_until="domcontentloaded",
    )

    expect(page).to_have_title(
        re.compile(
            "Open MAS",
            re.IGNORECASE,
        )
    )

    main_tabs = page.get_by_role(
        "tab"
    )

    expect(main_tabs).to_have_count(
        9
    )

    operations_tab = page.get_by_role(
        "tab",
        name="Операции в базе",
        exact=True,
    )

    settings_tab = page.get_by_role(
        "tab",
        name="Настройки",
        exact=True,
    )

    expect(
        operations_tab
    ).to_have_attribute(
        "aria-selected",
        "true",
    )

    settings_tab.click()

    expect(
        settings_tab
    ).to_have_attribute(
        "aria-selected",
        "true",
    )

    expect(
        page.get_by_role(
            "heading",
            name="Настройки",
            exact=True,
        )
    ).to_be_visible()

    expect(
        page.get_by_text(
            "Ревизия Alembic",
            exact=True,
        )
    ).to_be_visible()

    telegram_tab = page.get_by_role(
        "tab",
        name="Telegram",
        exact=True,
    )

    telegram_tab.click()

    expect(
        telegram_tab
    ).to_have_attribute(
        "aria-selected",
        "true",
    )

    for heading_name in (
        "Telegram-бот",
        "Токен Telegram-бота",
        "Управление ботом",
        "Разрешённые пользователи",
        "Разрешённые чаты",
    ):
        expect(
            page.get_by_role(
                "heading",
                name=heading_name,
                exact=True,
            )
        ).to_be_visible()

    expect(
        page.get_by_role(
            "button",
            name="Сохранить настройки бота",
            exact=True,
        )
    ).to_be_visible()

    expect(
        page.get_by_role(
            "button",
            name=(
                "Добавить или обновить "
                "пользователя"
            ),
            exact=True,
        )
    ).to_be_visible()

    expect(
        page.get_by_role(
            "button",
            name=(
                "Добавить или обновить чат"
            ),
            exact=True,
        )
    ).to_be_visible()

    expect(
        page.locator(
            '[data-testid="stException"]'
        )
    ).to_have_count(0)
