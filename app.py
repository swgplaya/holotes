from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from html import escape

import pandas as pd
import streamlit as st

from src.i18n import (
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
    translate,
)

from src.database import init_db
from src.ui.operations import (
    render_operations_tab,
)
from src.ui.classification import (
    render_classification_tab,
)
from src.ui.rules import (
    render_rules_tab,
)
from src.ui.reports import (
    render_cash_flow_tab,
    render_pnl_tab,
)
from src.ui.imports import (
    render_import_tab,
)
from src.ui.payment_calendar import (
    render_payment_calendar_tab,
)
from src.ui.unit_economics import (
    render_unit_economics_tab,
)

from src.ui.settings import (
    render_settings_tab,
)


st.set_page_config(
    page_title="Open MAS",
    page_icon="📊",
    layout="wide",
)

APP_ROOT = Path(__file__).resolve().parent

st.html(
    APP_ROOT / "assets" / "styles.css"
)

init_db()

LANGUAGE_STATE_KEY = "ui_language"
MAIN_NAVIGATION_KEY = "main_navigation"

MAIN_TAB_TRANSLATION_KEYS = (
    "tabs.operations",
    "tabs.classification",
    "tabs.rules",
    "tabs.pnl",
    "tabs.cash_flow",
    "tabs.unit_economics",
    "tabs.payment_calendar",
    "tabs.import",
    "tabs.settings",
)


def t(
    key: str,
    **values: object,
) -> str:
    """Возвращает перевод для текущего языка."""

    return translate(
        key=key,
        language=st.session_state.get(
            LANGUAGE_STATE_KEY,
            DEFAULT_LANGUAGE,
        ),
        **values,
    )

def sync_main_navigation_language() -> None:
    """Сохраняет активный раздел при смене языка."""

    active_label = st.session_state.get(
        MAIN_NAVIGATION_KEY
    )

    if active_label is None:
        return

    active_translation_key = None

    for translation_key in MAIN_TAB_TRANSLATION_KEYS:
        for language in SUPPORTED_LANGUAGES:
            translated_label = translate(
                key=translation_key,
                language=language,
            )

            if translated_label == active_label:
                active_translation_key = translation_key
                break

        if active_translation_key is not None:
            break

    if active_translation_key is None:
        return

    new_language = st.session_state.get(
        LANGUAGE_STATE_KEY,
        DEFAULT_LANGUAGE,
    )

    st.session_state[MAIN_NAVIGATION_KEY] = translate(
        key=active_translation_key,
        language=new_language,
    )

def format_rubles(kopecks: int) -> str:
    """Форматирует копейки в российский денежный формат."""

    amount = Decimal(int(kopecks)) / Decimal("100")
    formatted = f"{amount:,.2f}"

    formatted = (
        formatted
        .replace(",", " ")
        .replace(".", ",")
    )

    return f"{formatted} ₽"

def rubles_to_kopecks(value: float) -> int:
    """Безопасно преобразует рубли в копейки."""

    amount = Decimal(str(value))

    kopecks = (
        amount * Decimal("100")
    ).quantize(
        Decimal("1"),
        rounding=ROUND_HALF_UP,
    )

    return int(kopecks)

def percent_to_basis_points(
    value: float,
) -> int:
    """Преобразует проценты в базисные пункты."""

    basis_points = (
        Decimal(str(value))
        * Decimal("100")
    ).quantize(
        Decimal("1"),
        rounding=ROUND_HALF_UP,
    )

    return int(basis_points)

def format_boolean_status(value: object) -> str:
    """Возвращает локализованный логический статус."""

    if (
        value is not None
        and not pd.isna(value)
        and bool(value)
    ):
        return t("common.yes")

    return t("common.no")


if LANGUAGE_STATE_KEY not in st.session_state:
    st.session_state[
        LANGUAGE_STATE_KEY
    ] = DEFAULT_LANGUAGE


_, language_column = st.columns(
    [5, 1],
    vertical_alignment="center",
)

with language_column:
    st.selectbox(
        t("language.selector"),
        options=list(SUPPORTED_LANGUAGES),
        format_func=SUPPORTED_LANGUAGES.get,
        key=LANGUAGE_STATE_KEY,
        on_change=sync_main_navigation_language,
        label_visibility="collapsed",
    )


hero_eyebrow = escape(
    t("app.eyebrow")
)

hero_description = escape(
    t("app.description")
)

hero_badge = escape(
    t("app.badge")
)


st.html(
    f"""
    <section class="openmas-hero">
        <div class="openmas-hero__content">
            <div class="openmas-hero__eyebrow">
                {hero_eyebrow}
            </div>

            <h1 class="openmas-hero__title">
                Open MAS
            </h1>

            <p class="openmas-hero__description">
                {hero_description}
            </p>
        </div>

        <div class="openmas-hero__badge">
            {hero_badge}
        </div>
    </section>
    """
)


last_import_message = st.session_state.pop(
    "last_import_message",
    None,
)

if last_import_message:
    st.success(last_import_message)

(
    operations_tab,
    classification_tab,
    rules_tab,
    pnl_tab,
    cash_flow_tab,
    unit_economics_tab,
    payment_calendar_tab,
    import_tab,
    settings_tab,
) = st.tabs(
    [
        t(translation_key)
        for translation_key in MAIN_TAB_TRANSLATION_KEYS
    ],
    key=MAIN_NAVIGATION_KEY,
    on_change="rerun",
)

classification_message = st.session_state.pop(
    "classification_message",
    None,
)

if classification_message:
    st.success(classification_message)

unit_economics_message = st.session_state.pop(
    "unit_economics_message",
    None,
)

if unit_economics_message:
    st.success(unit_economics_message)

calendar_message = st.session_state.pop(
    "calendar_message",
    None,
)

if calendar_message:
    st.success(calendar_message)

rule_message = st.session_state.pop(
    "rule_message",
    None,
)

if rule_message:
    st.success(rule_message)

if operations_tab.open:
    with operations_tab:
        render_operations_tab(
            t=t,
            format_rubles=format_rubles,
        )

if classification_tab.open:
    with classification_tab:
        render_classification_tab(
            t=t,
            format_rubles=format_rubles,
        )

if rules_tab.open:
    with rules_tab:
        render_rules_tab(
            t=t,
        )

if pnl_tab.open:
    with pnl_tab:
        render_pnl_tab(
            t=t,
            format_rubles=format_rubles,
        )

if cash_flow_tab.open:
    with cash_flow_tab:
        render_cash_flow_tab(
            t=t,
            format_rubles=format_rubles,
        )

if unit_economics_tab.open:
    with unit_economics_tab:
        render_unit_economics_tab(
            t=t,
            format_rubles=format_rubles,
            rubles_to_kopecks=rubles_to_kopecks,
            percent_to_basis_points=percent_to_basis_points,
            format_boolean_status=format_boolean_status,
        )

if payment_calendar_tab.open:
    with payment_calendar_tab:
        render_payment_calendar_tab(
            t=t,
            format_rubles=format_rubles,
            rubles_to_kopecks=rubles_to_kopecks,
            format_boolean_status=format_boolean_status,
        )

if import_tab.open:
    with import_tab:
        render_import_tab(
            t=t,
            format_rubles=format_rubles,
        )

if settings_tab.open:
    with settings_tab:
        render_settings_tab(
            t=t,
        )
