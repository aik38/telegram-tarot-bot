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


def test_grant_purchase_adds_tickets(db):
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    user_id = 123
    db.ensure_user(user_id, now=base)

    db.grant_purchase(user_id, "TICKET_3", now=base)
    db.grant_purchase(user_id, "TICKET_7", now=base)
    db.grant_purchase(user_id, "TICKET_10", now=base)

    user = db.get_user(user_id)
    assert user is not None
    assert user.tickets_3 == 1
    assert user.tickets_7 == 1
    assert user.tickets_10 == 1


def test_grant_purchase_extends_premium_from_current_end(db):
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    user_id = 456
    db.ensure_user(user_id, now=base)

    db.grant_purchase(user_id, "PASS_7D", now=base)
    first_until = db.get_user(user_id).premium_until
    assert first_until == base + timedelta(days=7)

    later = base + timedelta(days=3)
    db.grant_purchase(user_id, "PASS_7D", now=later)
    second_until = db.get_user(user_id).premium_until
    assert second_until == first_until + timedelta(days=7)

    even_later = base + timedelta(days=30)
    db.grant_purchase(user_id, "PASS_30D", now=even_later)
    third_until = db.get_user(user_id).premium_until
    assert third_until == even_later + timedelta(days=30)


def test_consume_ticket_reduces_balance(db):
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    user_id = 789
    db.ensure_user(user_id, now=base)

    db.grant_purchase(user_id, "TICKET_3", now=base)
    assert db.consume_ticket(user_id, ticket="tickets_3")
    assert not db.consume_ticket(user_id, ticket="tickets_3")
