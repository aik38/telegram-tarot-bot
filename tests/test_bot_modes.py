import asyncio
import importlib
import sys

from core.tarot import contains_tarot_like, is_tarot_request


def import_bot_main(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:TESTTOKEN")
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    if "core.monetization" in sys.modules:
        del sys.modules["core.monetization"]
    if "bot.main" in sys.modules:
        del sys.modules["bot.main"]
    return importlib.import_module("bot.main")


def test_is_tarot_request_basic():
    assert is_tarot_request("今の恋愛について占って")
    assert is_tarot_request("/tarot 恋愛運")
    assert not is_tarot_request("今日は忙しかったです")
    assert not is_tarot_request("クレジットカードが止まった")


def test_choose_spread(monkeypatch):
    bot_main = import_bot_main(monkeypatch)
    assert bot_main.choose_spread("恋愛について占って") == bot_main.ONE_CARD
    assert bot_main.choose_spread("3枚で恋愛について占って") == bot_main.ONE_CARD


def test_parse_spread_command(monkeypatch):
    bot_main = import_bot_main(monkeypatch)

    spread, question = bot_main.parse_spread_command("/love1 片思いの相手の気持ち")
    assert spread == bot_main.ONE_CARD
    assert question == "片思いの相手の気持ち"

    spread_three, question_three = bot_main.parse_spread_command("/love3 結果を知りたい")
    assert spread_three == bot_main.THREE_CARD_SITUATION
    assert question_three == "結果を知りたい"

    spread_hexa, _ = bot_main.parse_spread_command("/hexa 今後")
    assert spread_hexa == bot_main.HEXAGRAM

    spread_celtic, _ = bot_main.parse_spread_command("/celtic")
    assert spread_celtic == bot_main.CELTIC_CROSS


def test_contains_tarot_like_detection():
    assert contains_tarot_like("引いたカードは恋人でした")
    assert contains_tarot_like("正位置で出たよ")
    assert not contains_tarot_like("今日は友達と映画に行きました")


def test_general_chat_response_triggers_rewrite(monkeypatch):
    bot_main = import_bot_main(monkeypatch)

    called = {"value": False}

    async def fake_rewrite(text: str):
        called["value"] = True
        return "リライト済みです。", False

    result = asyncio.run(
        bot_main.ensure_general_chat_safety(
            "引いたカードは恋人でした。今日は寒いですね。", rewrite_func=fake_rewrite
        )
    )

    assert called["value"] is True
    assert "リライト済み" in result


def test_tarot_response_prefixed(monkeypatch):
    bot_main = import_bot_main(monkeypatch)
    heading = "引いたカードは「恋人（正位置）」です。"
    response = bot_main.ensure_tarot_response_prefixed("解釈が続きます。", heading)
    assert response.startswith(heading)


class DummyFromUser:
    def __init__(self, user_id: int):
        self.id = user_id


class DummyMessage:
    def __init__(self, text: str, user_id: int | None = None):
        self.text = text
        self.from_user = DummyFromUser(user_id) if user_id is not None else None
        self.answers: list[str] = []

    async def answer(self, text: str):
        self.answers.append(text)


def test_paywall_blocks_paid_spread(monkeypatch):
    monkeypatch.setenv("PAYWALL_ENABLED", "true")
    bot_main = import_bot_main(monkeypatch)
    message = DummyMessage("/love3", user_id=42)

    asyncio.run(bot_main.handle_message(message))

    assert message.answers
    assert "/buy" in message.answers[0]
