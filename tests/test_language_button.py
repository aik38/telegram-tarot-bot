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
    ],
)
def test_language_reply_button_shows_picker(monkeypatch, tmp_path, button_text, user_lang):
    bot_main = import_bot_main(monkeypatch, tmp_path)

    from core import db as core_db

    core_db.set_user_lang(999, user_lang)
    message = DummyMessage(button_text, user_id=999)

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
