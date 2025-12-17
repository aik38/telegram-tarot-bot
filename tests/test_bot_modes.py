import asyncio
import importlib
import json
import sys

import pytest

from core.tarot import contains_tarot_like, is_tarot_request


def import_bot_main(monkeypatch, tmp_path=None):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:TESTTOKEN")
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    if tmp_path is not None:
        monkeypatch.setenv("SQLITE_DB_PATH", str(tmp_path / "test.db"))
    if "core.monetization" in sys.modules:
        del sys.modules["core.monetization"]
    if "core.db" in sys.modules:
        del sys.modules["core.db"]
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

    spread_read, _ = bot_main.parse_spread_command("/read1 気持ち")
    assert spread_read == bot_main.ONE_CARD

    spread_three, question_three = bot_main.parse_spread_command("/love3 結果を知りたい")
    assert spread_three == bot_main.THREE_CARD_SITUATION
    assert question_three == "結果を知りたい"

    spread_three_read, _ = bot_main.parse_spread_command("/read3")
    assert spread_three_read == bot_main.THREE_CARD_SITUATION

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
    def __init__(self, text: str, user_id: int | None = None, successful_payment=None):
        self.text = text
        self.from_user = DummyFromUser(user_id) if user_id is not None else None
        self.answers: list[str] = []
        self.reply_markups: list[object] = []
        if successful_payment is not None:
            self.successful_payment = successful_payment

    async def answer(self, text: str, **kwargs):
        self.answers.append(text)
        if "reply_markup" in kwargs:
            self.reply_markups.append(kwargs["reply_markup"])


class DummyCallback:
    def __init__(self, data: str, user_id: int | None = None, message: DummyMessage | None = None):
        self.data = data
        self.from_user = DummyFromUser(user_id) if user_id is not None else None
        self.message = message
        self.answers: list[str] = []

    async def answer(self, text: str, **kwargs):
        self.answers.append(text)


def test_start_message_shorter(monkeypatch, tmp_path):
    bot_main = import_bot_main(monkeypatch, tmp_path)
    message = DummyMessage("/start", user_id=1)

    asyncio.run(bot_main.cmd_start(message))

    assert message.answers
    assert "【占いの始め方】" in message.answers[0]
    assert "/read1" in message.answers[0]
    assert "/read3" in message.answers[0]
    assert "恋愛専用" not in message.answers[0]


def test_love1_command_is_alias(monkeypatch, tmp_path):
    bot_main = import_bot_main(monkeypatch, tmp_path)

    calls: list[tuple[str, object]] = []

    async def fake_handle_tarot(message, user_query: str, spread, guidance_note=None):
        calls.append((user_query, spread))

    monkeypatch.setattr(bot_main, "handle_tarot_reading", fake_handle_tarot)

    message_love = DummyMessage("/love1", user_id=10)
    asyncio.run(bot_main.handle_message(message_love))

    message_read = DummyMessage("/read1", user_id=11)
    asyncio.run(bot_main.handle_message(message_read))

    assert len(calls) == 2
    assert calls[0][0] == calls[1][0]
    assert calls[0][1] is bot_main.ONE_CARD
    assert calls[1][1] is bot_main.ONE_CARD


def test_multiple_card_hint_without_command(monkeypatch, tmp_path):
    bot_main = import_bot_main(monkeypatch, tmp_path)

    async def fake_call(messages):
        return "テスト回答", False

    monkeypatch.setattr(bot_main, "call_openai_with_retry", fake_call)
    message = DummyMessage("占って、3枚でお願いします", user_id=5)

    asyncio.run(bot_main.handle_message(message))

    assert any("複数枚はコマンド指定" in ans for ans in message.answers)


def test_paywall_blocks_paid_spread(monkeypatch, tmp_path):
    monkeypatch.setenv("PAYWALL_ENABLED", "true")
    bot_main = import_bot_main(monkeypatch, tmp_path)
    message = DummyMessage("/read3", user_id=42)

    asyncio.run(bot_main.handle_message(message))

    assert message.answers
    assert "/buy" in message.answers[0]


def test_terms_required_before_buy(monkeypatch, tmp_path):
    bot_main = import_bot_main(monkeypatch, tmp_path)
    message = DummyMessage("/buy", user_id=99)

    asyncio.run(bot_main.cmd_buy(message))

    assert any("/terms" in ans or "同意" in ans for ans in message.answers)


def test_terms_support_and_pay_support_use_configured_email(monkeypatch, tmp_path):
    support_email = "support@tarot.test"
    monkeypatch.setenv("SUPPORT_EMAIL", support_email)
    bot_main = import_bot_main(monkeypatch, tmp_path)

    terms_message = DummyMessage("/terms", user_id=500)
    asyncio.run(bot_main.cmd_terms(terms_message))

    support_message = DummyMessage("/support", user_id=500)
    asyncio.run(bot_main.cmd_support(support_message))

    pay_support_message = DummyMessage("/paysupport", user_id=500)
    asyncio.run(bot_main.cmd_pay_support(pay_support_message))

    assert support_email in bot_main.get_terms_text()
    assert any(support_email in ans for ans in terms_message.answers)
    assert any(support_email in ans for ans in support_message.answers)
    assert any(support_email in ans for ans in pay_support_message.answers)


def test_buy_shows_terms_prompt_keyboard(monkeypatch, tmp_path):
    bot_main = import_bot_main(monkeypatch, tmp_path)
    message = DummyMessage("/buy", user_id=123)

    asyncio.run(bot_main.cmd_buy(message))

    assert message.reply_markups
    buttons = [btn.text for row in message.reply_markups[0].inline_keyboard for btn in row]
    assert "利用規約を確認" in buttons
    assert "同意して購入へ進む" in buttons


def test_agree_and_buy_callback_opens_store(monkeypatch, tmp_path):
    bot_main = import_bot_main(monkeypatch, tmp_path)
    user_id = 321
    message = DummyMessage("/buy", user_id=user_id)

    asyncio.run(bot_main.cmd_buy(message))

    callback = DummyCallback(
        bot_main.TERMS_CALLBACK_AGREE_AND_BUY, user_id=user_id, message=message
    )
    asyncio.run(bot_main.handle_terms_agree_and_buy(callback))

    user = bot_main.get_user(user_id)
    assert bot_main.has_accepted_terms(user_id)
    assert user is not None
    assert any("ご希望の商品" in ans for ans in message.answers)


def test_successful_payment_not_double_granted(monkeypatch, tmp_path):
    bot_main = import_bot_main(monkeypatch, tmp_path)
    user_id = 77
    payload = json.dumps({"sku": "TICKET_3", "user_id": user_id})

    class DummyPayment:
        def __init__(self, charge_id: str):
            self.total_amount = 300
            self.invoice_payload = payload
            self.telegram_payment_charge_id = charge_id
            self.provider_payment_charge_id = "provider"

    first_message = DummyMessage("", user_id=user_id, successful_payment=DummyPayment("ch1"))
    asyncio.run(bot_main.process_successful_payment(first_message))

    dup_message = DummyMessage("", user_id=user_id, successful_payment=DummyPayment("ch1"))
    asyncio.run(bot_main.process_successful_payment(dup_message))

    user = bot_main.get_user(user_id)
    assert user.tickets_3 == 1
    assert any("処理済み" in ans for ans in dup_message.answers)


def test_admin_cannot_refund(monkeypatch, tmp_path):
    bot_main = import_bot_main(monkeypatch, tmp_path)
    message = DummyMessage("/refund chx", user_id=1234)

    asyncio.run(bot_main.cmd_refund(message))

    assert any("管理者専用" in ans for ans in message.answers)
