import asyncio

import pytest
from aiogram.types import InlineKeyboardMarkup

from bot.texts.i18n import t
from tests.test_bot_modes import DummyMessage, import_bot_main


def _collect_button_texts(markup: InlineKeyboardMarkup) -> list[str]:
    return [btn.text for row in markup.inline_keyboard for btn in row]


@pytest.mark.parametrize(
    ("button_text", "user_lang"),
    [
        ("🌐 Language", "en"),
        ("言語設定", "ja"),
        ("Idioma", "pt"),
        ("🌐Language", "en"),
        ("🌐　言語設定", "ja"),
        ("🌐\xa0Language", "en"),
        ("🌐\u3000Language", "en"),
        ("🌐\ufe0f Language", "en"),
        ("\u200b🌐 Language", "en"),
        ("\ufeff🌐 Language", "en"),
        ("\u200f🌐 Language", "en"),
        ("\u2060🌐 Language", "en"),
        ("🌐\u200d Language", "en"),
        ("🌐 言語設定", "ja"),
        ("🌐 Idioma", "pt"),
    ],
)
def test_language_reply_button_shows_picker(monkeypatch, tmp_path, button_text, user_lang):
    bot_main = import_bot_main(monkeypatch, tmp_path)

    from core import db as core_db

    core_db.set_user_lang(999, user_lang)
    message = DummyMessage(button_text, user_id=999, chat_id=999, message_id=1)

    asyncio.run(bot_main.handle_message(message))

    assert any(isinstance(markup, InlineKeyboardMarkup) for markup in message.reply_markups)
    prompt = t(user_lang, "LANGUAGE_SELECT_PROMPT")
    assert any(prompt in answer for answer in message.answers)

    markup = next(markup for markup in message.reply_markups if isinstance(markup, InlineKeyboardMarkup))
    buttons = _collect_button_texts(markup)
    expected_options = [
        t(user_lang, "LANGUAGE_OPTION_JA"),
        t(user_lang, "LANGUAGE_OPTION_EN"),
        t(user_lang, "LANGUAGE_OPTION_PT"),
    ]
    for option in expected_options:
        assert option in buttons


@pytest.mark.parametrize(
    "free_text",
    [
        "language",
        "LANGUAGE",
        "I want to change language",
        "言語設定お願いします",
        "Idioma por favor",
    ],
)
def test_language_reply_button_does_not_misfire(monkeypatch, tmp_path, free_text):
    bot_main = import_bot_main(monkeypatch, tmp_path)

    is_button, hint = bot_main.is_language_reply_button(free_text)

    assert is_button is False
    assert hint is None


def test_language_button_bypasses_dedup(monkeypatch, tmp_path):
    bot_main = import_bot_main(monkeypatch, tmp_path)

    from core import db as core_db

    core_db.set_user_lang(555, "en")
    bot_main.RECENT_HANDLED.clear()
    bot_main.RECENT_HANDLED_ORDER.clear()

    first = DummyMessage("🌐 Language", user_id=555, chat_id=555, message_id=5)
    second = DummyMessage("🌐 Language", user_id=555, chat_id=555, message_id=5)

    asyncio.run(bot_main.handle_message(first))
    asyncio.run(bot_main.handle_message(second))

    assert any(isinstance(markup, InlineKeyboardMarkup) for markup in first.reply_markups)
    assert any(isinstance(markup, InlineKeyboardMarkup) for markup in second.reply_markups)
