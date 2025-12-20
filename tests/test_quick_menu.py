import asyncio

from aiogram.types import ReplyKeyboardMarkup

from bot.keyboards.common import base_menu_kb
from tests.test_bot_modes import import_bot_main


class DummyFromUser:
    def __init__(self, user_id: int):
        self.id = user_id


class DummyMessage:
    def __init__(self, text: str, user_id: int | None = None):
        self.text = text
        self.from_user = DummyFromUser(user_id) if user_id is not None else None
        self.answers: list[str] = []
        self.reply_markups: list[object] = []

    async def answer(self, text: str, **kwargs):
        self.answers.append(text)
        if "reply_markup" in kwargs:
            self.reply_markups.append(kwargs["reply_markup"])


def test_base_menu_layout():
    markup = base_menu_kb()

    assert isinstance(markup, ReplyKeyboardMarkup)
    assert markup.is_persistent is True
    assert len(markup.keyboard) == 2
    assert [button.text for button in markup.keyboard[0]] == ["🎩占い", "💬相談"]
    assert [button.text for button in markup.keyboard[1]] == ["🛒チャージ", "📊ステータス", "🌐 言語設定"]


def test_base_menu_layout_en():
    markup = base_menu_kb(lang="en")

    assert [button.text for button in markup.keyboard[0]] == ["🎩 Tarot", "💬 Chat"]
    assert [button.text for button in markup.keyboard[1]] == ["🛒 Store", "📊 Status", "🌐 Language"]


def test_base_menu_layout_pt():
    markup = base_menu_kb(lang="pt")

    assert [button.text for button in markup.keyboard[0]] == ["🎩 Tarot", "💬 Conversa"]
    assert [button.text for button in markup.keyboard[1]] == ["🛒 Loja", "📊 Status", "🌐 Idioma"]


def test_help_and_terms_attach_quick_menu(monkeypatch, tmp_path):
    bot_main = import_bot_main(monkeypatch, tmp_path)

    help_message = DummyMessage("/help", user_id=1)
    asyncio.run(bot_main.cmd_help(help_message))

    assert any(isinstance(markup, ReplyKeyboardMarkup) for markup in help_message.reply_markups)

    terms_message = DummyMessage("/terms", user_id=2)
    asyncio.run(bot_main.cmd_terms(terms_message))

    assert any(isinstance(markup, ReplyKeyboardMarkup) for markup in terms_message.reply_markups)


def test_safety_notice_resets_state(monkeypatch, tmp_path):
    bot_main = import_bot_main(monkeypatch, tmp_path)
    user_id = 3
    bot_main.set_user_mode(user_id, "tarot")
    bot_main.set_tarot_flow(user_id, "awaiting_question")

    message = DummyMessage("病気について", user_id=user_id)

    handled = asyncio.run(bot_main.respond_with_safety_notice(message, "病気について"))

    assert handled is True
    assert bot_main.USER_MODE.get(user_id) is None
    assert bot_main.TAROT_FLOW.get(user_id) is None
    assert any(isinstance(markup, ReplyKeyboardMarkup) for markup in message.reply_markups)
