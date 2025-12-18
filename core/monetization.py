from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Set

from dotenv import load_dotenv

from core.db import UserRecord, get_user, has_active_pass

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

    if user_id in ADMIN_USER_IDS:
        return True

    if user_id in PREMIUM_USER_IDS:
        return True

    now = now or datetime.now(timezone.utc)
    return has_active_pass(user_id, now=now)


def get_user_with_default(user_id: int | None):
    if user_id is None:
        return None
    return get_user(user_id)


def _user_pass_expiry(user: UserRecord | None, now: datetime) -> datetime | None:
    if user is None:
        return None
    if user.pass_until and user.pass_until > now:
        return user.pass_until
    if user.premium_until and user.premium_until > now:
        return user.premium_until
    return None


def effective_has_pass(
    user_id: int | None, user: UserRecord | None, now: datetime | None = None
) -> bool:
    now = now or datetime.now(timezone.utc)
    if user_id is None:
        return False

    if user_id in ADMIN_USER_IDS:
        return True

    if _user_pass_expiry(user, now):
        return True

    return has_active_pass(user_id, now=now)


def effective_pass_expires_at(
    user_id: int | None, user: UserRecord | None, now: datetime
) -> datetime | None:
    if user_id is None:
        return None

    if user_id in ADMIN_USER_IDS:
        return now + timedelta(days=30)

    expiry = _user_pass_expiry(user, now)
    if expiry:
        return expiry

    db_user = user if user and user.user_id == user_id else get_user(user_id)
    return _user_pass_expiry(db_user, now)


__all__ = [
    "ADMIN_USER_IDS",
    "PAYWALL_ENABLED",
    "PREMIUM_USER_IDS",
    "effective_has_pass",
    "effective_pass_expires_at",
    "get_user_with_default",
    "is_premium_user",
]
