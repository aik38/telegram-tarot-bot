import asyncio

import pytest

from tests.test_bot_modes import import_bot_main


class DummyUser:
    def __init__(self, user_id: int):
        self.id = user_id
        self.language_code = "ja"


class DummyChat:
    def __init__(self, chat_id: int):
        self.id = chat_id


class DummyMessage:
    def __init__(self, text: str, user_id: int, message_id: int):
        self.text = text
        self.from_user = DummyUser(user_id)
        self.chat = DummyChat(user_id)
        self.message_id = message_id
        self.answers: list[str] = []

    async def answer(self, text: str, **kwargs):
        self.answers.append(text)


@pytest.fixture
def bot_main(monkeypatch, tmp_path):
    module = import_bot_main(monkeypatch, tmp_path)
    module.RECENT_HANDLED.clear()
    module.RECENT_HANDLED_ORDER.clear()
    yield module
    module.RECENT_HANDLED.clear()
    module.RECENT_HANDLED_ORDER.clear()


def test_duplicate_tarot_question_is_ignored(bot_main, monkeypatch):
    user_id = 999
    bot_main.set_user_mode(user_id, "tarot")

    calls: list[str] = []

    async def fake_execute_tarot(message, user_query: str, spread, theme=None):
        calls.append(user_query)

    monkeypatch.setattr(bot_main, "execute_tarot_request", fake_execute_tarot)

    message = DummyMessage("占ってください", user_id=user_id, message_id=1)

    asyncio.run(bot_main.handle_message(message))
    asyncio.run(bot_main.handle_message(message))

    assert calls == ["占ってください"]


def test_duplicate_chat_message_is_ignored(bot_main, monkeypatch):
    user_id = 1000
    bot_main.set_user_mode(user_id, "consult")

    calls: list[str] = []

    async def fake_general_chat(message, user_query: str):
        calls.append(user_query)

    monkeypatch.setattr(bot_main, "handle_general_chat", fake_general_chat)

    message = DummyMessage("お話を聞いてほしいです", user_id=user_id, message_id=2)

    asyncio.run(bot_main.handle_message(message))
    asyncio.run(bot_main.handle_message(message))

    assert calls == ["お話を聞いてほしいです"]
