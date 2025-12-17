import asyncio
import importlib
import sys
from datetime import datetime, timedelta, timezone


class DummyFromUser:
    def __init__(self, user_id: int):
        self.id = user_id


class DummyMessage:
    def __init__(self, text: str, user_id: int):
        self.text = text
        self.from_user = DummyFromUser(user_id)
        self.answers: list[str] = []

    async def answer(self, text: str, **kwargs):
        self.answers.append(text)


def import_bot_main(monkeypatch, tmp_path):
    monkeypatch.setenv("SQLITE_DB_PATH", str(tmp_path / "test_limits.db"))
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:TESTTOKEN")
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    monkeypatch.setenv("SUPPORT_EMAIL", "support@example.com")
    for module in ["core.monetization", "core.db", "bot.main"]:
        if module in sys.modules:
            del sys.modules[module]
    return importlib.import_module("bot.main")


def test_general_chat_trial_limits(monkeypatch, tmp_path):
    bot_main = import_bot_main(monkeypatch, tmp_path)
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    monkeypatch.setattr(bot_main, "utcnow", lambda: base)

    async def fake_call(messages):
        return "hi", False

    monkeypatch.setattr(bot_main, "call_openai_with_retry", fake_call)

    first = DummyMessage("こんにちは", user_id=1)
    second = DummyMessage("今日は寒いですね", user_id=1)
    third = DummyMessage("3通目", user_id=1)

    asyncio.run(bot_main.handle_message(first))
    asyncio.run(bot_main.handle_message(second))
    asyncio.run(bot_main.handle_message(third))

    assert len(first.answers) == 1
    assert len(second.answers) == 1
    assert any("無料枠" in ans for ans in third.answers)


def test_general_chat_requires_pass_after_trial(monkeypatch, tmp_path):
    bot_main = import_bot_main(monkeypatch, tmp_path)
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    bot_main.ensure_user(1, now=base)
    future = base + timedelta(days=5)
    monkeypatch.setattr(bot_main, "utcnow", lambda: future)

    async def fake_call(messages):
        return "hi", False

    monkeypatch.setattr(bot_main, "call_openai_with_retry", fake_call)

    message = DummyMessage("6日目の雑談", user_id=1)
    asyncio.run(bot_main.handle_message(message))

    assert any("パス" in ans for ans in message.answers)


def test_one_oracle_limit_triggers_short_response(monkeypatch, tmp_path):
    bot_main = import_bot_main(monkeypatch, tmp_path)
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    monkeypatch.setattr(bot_main, "utcnow", lambda: base)

    calls: list[bool] = []

    async def fake_tarot(
        message, user_query: str, spread=None, guidance_note=None, short_response=False
    ):
        calls.append(short_response)

    monkeypatch.setattr(bot_main, "handle_tarot_reading", fake_tarot)

    first = DummyMessage("占って", user_id=2)
    second = DummyMessage("占って", user_id=2)
    third = DummyMessage("占って", user_id=2)

    asyncio.run(bot_main.handle_message(first))
    asyncio.run(bot_main.handle_message(second))
    asyncio.run(bot_main.handle_message(third))

    assert calls == [True, True]
    assert any("無料枠" in ans for ans in third.answers)


def test_daily_counts_reset(monkeypatch, tmp_path):
    bot_main = import_bot_main(monkeypatch, tmp_path)
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    user_id = 3
    bot_main.ensure_user(user_id, now=base)
    bot_main.increment_general_chat_count(user_id, now=base)
    bot_main.increment_one_oracle_count(user_id, now=base)

    next_day = base + timedelta(days=1)
    user = bot_main.get_user(user_id, now=next_day)

    assert user is not None
    assert user.general_chat_count_today == 0
    assert user.one_oracle_count_today == 0
