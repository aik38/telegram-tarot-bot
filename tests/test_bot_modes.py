import asyncio
import importlib
import sys

from core.tarot import contains_tarot_like, is_tarot_request


def import_bot_main(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:TESTTOKEN")
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
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
    assert bot_main.choose_spread("3枚で恋愛について占って") == bot_main.THREE_CARD_SITUATION


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
