from datetime import datetime, timezone

import importlib


def test_effective_has_pass_for_admin(monkeypatch):
    monkeypatch.setenv("ADMIN_USER_IDS", "42")

    import core.monetization as monetization

    monetization = importlib.reload(monetization)
    now = datetime(2024, 1, 1, tzinfo=timezone.utc)

    assert monetization.effective_has_pass(42, None, now=now)
    assert monetization.effective_pass_expires_at(42, None, now) is not None
    assert not monetization.effective_has_pass(7, None, now=now)
