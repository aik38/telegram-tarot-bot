from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from tests.test_bot_modes import import_bot_main


def test_parse_invoice_payload_variants(monkeypatch):
    bot_main = import_bot_main(monkeypatch)

    sku, user_id = bot_main._parse_invoice_payload('{"sku": "TICKET_3", "user_id": "77"}')
    assert sku == "TICKET_3"
    assert user_id == 77

    bad_json = bot_main._parse_invoice_payload("not-json")
    assert bad_json == (None, None)

    missing_fields = bot_main._parse_invoice_payload('{"sku": null, "user_id": "abc"}')
    assert missing_fields == (None, None)

    list_payload = bot_main._parse_invoice_payload('["not", "dict"]')
    assert list_payload == (None, None)


def test_purchase_dedup_respects_ttl(monkeypatch):
    bot_main = import_bot_main(monkeypatch)
    bot_main.PENDING_PURCHASES = {}
    monkeypatch.setattr(bot_main, "PURCHASE_DEDUP_TTL_SECONDS", 0.1)

    clock = iter([10.0, 10.05, 10.2])
    monkeypatch.setattr(bot_main, "monotonic", lambda: next(clock))

    first = bot_main._check_purchase_dedup(1, "PASS_7D")
    dup_hit = bot_main._check_purchase_dedup(1, "PASS_7D")
    after_ttl = bot_main._check_purchase_dedup(1, "PASS_7D")

    assert first is False
    assert dup_hit is True
    assert after_ttl is False


def test_status_reflects_purchase_and_pass(monkeypatch, tmp_path):
    bot_main = import_bot_main(monkeypatch, tmp_path)

    now = datetime(2024, 1, 1, tzinfo=timezone.utc)
    user_id = 24601
    bot_main.ensure_user(user_id, now=now)

    granted = bot_main.grant_purchase(user_id, "PASS_7D", now=now)
    assert bot_main.effective_has_pass(user_id, granted, now=now + timedelta(seconds=1))

    payment_time = now + timedelta(minutes=5)
    bot_main.log_payment(
        user_id=user_id,
        sku="PASS_7D",
        stars=1000,
        telegram_payment_charge_id="charge-123",
        provider_payment_charge_id=None,
        now=payment_time,
    )

    status = bot_main.format_status(granted, now=payment_time)
    expected_until = (now + timedelta(days=7)).astimezone(bot_main.USAGE_TIMEZONE).strftime("%Y-%m-%d %H:%M JST")
    purchase_stamp = payment_time.astimezone(bot_main.USAGE_TIMEZONE).strftime("%Y-%m-%d %H:%M JST")

    assert expected_until in status
    assert "直近の購入" in status and "PASS_7D" in status
    assert purchase_stamp in status
