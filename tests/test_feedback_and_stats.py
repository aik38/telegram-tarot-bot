from __future__ import annotations

import importlib
from datetime import datetime, timedelta, timezone

import pytest


@pytest.fixture
def db(monkeypatch, tmp_path):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("SQLITE_DB_PATH", str(db_path))
    import core.db as db_module

    db = importlib.reload(db_module)
    yield db


def test_log_and_fetch_feedback(db):
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    db.ensure_user(1, now=base)
    db.log_feedback(
        user_id=1,
        mode="tarot",
        text="first feedback",
        request_id="r1",
        now=base,
    )
    db.log_feedback(
        user_id=1,
        mode="consult",
        text="second feedback",
        request_id="r2",
        now=base + timedelta(minutes=1),
    )

    recent = db.get_recent_feedback(limit=1)
    assert len(recent) == 1
    assert recent[0].text == "second feedback"
    assert recent[0].mode == "consult"
    assert recent[0].request_id == "r2"


def test_daily_stats_counts_events(db):
    base = datetime(2024, 1, 10, 3, tzinfo=timezone.utc)
    day1_time = base - timedelta(hours=15)  # JST: 2024-01-09
    day2_time = base - timedelta(hours=1)  # JST: 2024-01-10

    db.ensure_user(1, now=base)
    db.log_app_event(
        event_type="tarot",
        user_id=1,
        request_id="rid-tarot-1",
        payload=None,
        now=day1_time,
    )
    db.log_app_event(
        event_type="consult",
        user_id=2,
        request_id="rid-consult-1",
        payload=None,
        now=day1_time,
    )
    db.log_app_event(
        event_type="tarot",
        user_id=2,
        request_id="rid-tarot-2",
        payload=None,
        now=day2_time,
    )
    db.log_app_event(
        event_type="error",
        user_id=2,
        request_id="rid-error",
        payload=None,
        now=day2_time,
    )
    db.log_payment(
        user_id=1,
        sku="TICKET_3",
        stars=100,
        telegram_payment_charge_id="charge-1",
        provider_payment_charge_id=None,
        now=day1_time,
    )
    db.log_payment(
        user_id=3,
        sku="TICKET_3",
        stars=50,
        telegram_payment_charge_id="charge-refund",
        provider_payment_charge_id=None,
        now=day1_time,
    )
    db.mark_payment_refunded("charge-refund", now=base)

    stats = db.get_daily_stats(days=2, now=base)
    assert len(stats) == 2
    stats_by_date = {row["date"]: row for row in stats}

    today = base.astimezone(db.USAGE_TIMEZONE).date().isoformat()
    yesterday = (base.astimezone(db.USAGE_TIMEZONE).date() - timedelta(days=1)).isoformat()
    assert stats_by_date[today]["payments"] == 0
    assert stats_by_date[today]["stars_sales"] == 0
    assert stats_by_date[today]["tarot"] == 1
    assert stats_by_date[today]["consult"] == 0
    assert stats_by_date[today]["uses"] == 1
    assert stats_by_date[today]["dau"] == 1
    assert stats_by_date[today]["errors"] == 1

    assert stats_by_date[yesterday]["payments"] == 1
    assert stats_by_date[yesterday]["stars_sales"] == 100
    assert stats_by_date[yesterday]["tarot"] == 1
    assert stats_by_date[yesterday]["consult"] == 1
    assert stats_by_date[yesterday]["uses"] == 2
    assert stats_by_date[yesterday]["dau"] == 2
    assert stats_by_date[yesterday]["errors"] == 0
