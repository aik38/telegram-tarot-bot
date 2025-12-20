import asyncio

import pytest

from tests.test_bot_modes import DummyMessage, import_bot_main


@pytest.fixture()
def bot_main(monkeypatch, tmp_path):
    return import_bot_main(monkeypatch, tmp_path)


def test_sensitive_topic_classification(bot_main):
    topics = bot_main.classify_sensitive_topics("頭痛が続いて診断が必要です。")
    assert "medical" in topics
    assert "investment" not in topics


def test_sensitive_topic_short_circuits_llm(monkeypatch, bot_main):
    calls = {"llm": False}

    async def fake_call(messages):
        calls["llm"] = True
        return "LLM should not be called", False

    monkeypatch.setattr(bot_main, "call_openai_with_retry", fake_call)
    message = DummyMessage("裁判や診断について教えてほしい", user_id=77)

    asyncio.run(bot_main.handle_message(message))

    assert message.answers
    assert any("占いとしては" in ans for ans in message.answers)
    assert any("専門家" in ans for ans in message.answers)
    assert calls["llm"] is False
