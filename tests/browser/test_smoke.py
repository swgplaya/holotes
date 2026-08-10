from __future__ import annotations

from datetime import date
import re

import pytest
from playwright.sync_api import (
    Page,
    expect,
)


pytestmark = pytest.mark.browser


def test_holotes_starts_and_opens_settings(
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
            "Holotes",
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

    rules_tab = page.get_by_role(
        "tab",
        name="Правила",
        exact=True,
    )

    pnl_tab = page.get_by_role(
        "tab",
        name="P&L",
        exact=True,
    )

    cash_flow_tab = page.get_by_role(
        "tab",
        name="Cash Flow",
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

    rules_tab.click()

    expect(
        rules_tab
    ).to_have_attribute(
        "aria-selected",
        "true",
    )

    expect(
        page.get_by_role(
            "heading",
            name="Сохранённые правила",
            exact=True,
        )
    ).to_be_visible()

    expect(
        page.get_by_text(
            "Правила пока не созданы.",
            exact=True,
        )
    ).to_be_visible()

    pnl_tab.click()

    expect(
        pnl_tab
    ).to_have_attribute(
        "aria-selected",
        "true",
    )

    expect(
        page.get_by_role(
            "heading",
            name="Период отчёта",
            exact=True,
        )
    ).to_be_visible()

    expect(
        page.get_by_text(
            "Тип периода",
            exact=True,
        )
    ).to_be_visible()

    today = date.today()

    current_period_text = (
        "Период: "
        f"01.{today:%m.%Y}"
        " — "
        f"{today:%d.%m.%Y}"
    )

    expect(
        page.locator(
            '[role="tabpanel"]:visible'
        ).get_by_text(
            current_period_text,
            exact=True,
        )
    ).to_be_visible()

    cash_flow_tab.click()

    expect(
        cash_flow_tab
    ).to_have_attribute(
        "aria-selected",
        "true",
    )

    expect(
        page.locator(
            '[role="tabpanel"]:visible'
        ).get_by_text(
            current_period_text,
            exact=True,
        )
    ).to_be_visible()

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
