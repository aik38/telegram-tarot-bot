from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Set

from dotenv import load_dotenv

from core.db import get_user, has_active_pass

load_dotenv()


def _get_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_int_set(value: str | None) -> Set[int]:
    if not value:
        return set()

    ids: set[int] = set()
    for raw in value.split(","):
        candidate = raw.strip()
        if not candidate:
            continue
        try:
            ids.add(int(candidate))
        except ValueError:
            continue
    return ids


PAYWALL_ENABLED: bool = _get_bool("PAYWALL_ENABLED", default=False)
PREMIUM_USER_IDS: set[int] = _parse_int_set(os.getenv("PREMIUM_USER_IDS"))
ADMIN_USER_IDS: set[int] = _parse_int_set(os.getenv("ADMIN_USER_IDS"))


def is_premium_user(user_id: int | None, *, now: datetime | None = None) -> bool:
    if user_id is None:
        return False

    if user_id in PREMIUM_USER_IDS:
        return True

    now = now or datetime.now(timezone.utc)
    return has_active_pass(user_id, now=now)


def get_user_with_default(user_id: int | None):
    if user_id is None:
        return None
    return get_user(user_id)


__all__ = [
    "ADMIN_USER_IDS",
    "PAYWALL_ENABLED",
    "PREMIUM_USER_IDS",
    "get_user_with_default",
    "is_premium_user",
]
