from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

from core.store.catalog import get_product

DB_PATH = os.getenv("SQLITE_DB_PATH", "db/telegram_tarot.db")


@dataclass
class UserRecord:
    user_id: int
    created_at: datetime
    premium_until: datetime | None
    tickets_3: int
    tickets_7: int
    tickets_10: int
    images_enabled: bool


TicketColumn = Literal["tickets_3", "tickets_7", "tickets_10"]


def _ensure_parent_dir(path: str | os.PathLike[str]) -> None:
    directory = Path(path).parent
    if directory and not directory.exists():
        directory.mkdir(parents=True, exist_ok=True)


def _connect() -> sqlite3.Connection:
    _ensure_parent_dir(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                created_at TEXT,
                premium_until TEXT,
                tickets_3 INT,
                tickets_7 INT,
                tickets_10 INT,
                images_enabled INT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INT,
                sku TEXT,
                stars INT,
                telegram_payment_charge_id TEXT,
                provider_payment_charge_id TEXT,
                created_at TEXT
            )
            """
        )


def ensure_user(user_id: int, *, now: datetime | None = None) -> UserRecord:
    now = now or datetime.now(timezone.utc)
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if row:
            return _row_to_user(row)

        conn.execute(
            """
            INSERT INTO users (user_id, created_at, premium_until, tickets_3, tickets_7, tickets_10, images_enabled)
            VALUES (?, ?, NULL, 0, 0, 0, 0)
            """,
            (user_id, now.isoformat()),
        )
        return UserRecord(
            user_id=user_id,
            created_at=now,
            premium_until=None,
            tickets_3=0,
            tickets_7=0,
            tickets_10=0,
            images_enabled=False,
        )


def get_user(user_id: int) -> UserRecord | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    if not row:
        return None
    return _row_to_user(row)


def log_payment(
    *,
    user_id: int,
    sku: str,
    stars: int,
    telegram_payment_charge_id: str | None,
    provider_payment_charge_id: str | None,
    now: datetime | None = None,
) -> None:
    now = now or datetime.now(timezone.utc)
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO payments (
                user_id, sku, stars, telegram_payment_charge_id, provider_payment_charge_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, sku, stars, telegram_payment_charge_id, provider_payment_charge_id, now.isoformat()),
        )


def _row_to_user(row: sqlite3.Row) -> UserRecord:
    premium_until = row["premium_until"]
    premium_dt = datetime.fromisoformat(premium_until) if premium_until else None
    return UserRecord(
        user_id=row["user_id"],
        created_at=datetime.fromisoformat(row["created_at"]),
        premium_until=premium_dt,
        tickets_3=row["tickets_3"],
        tickets_7=row["tickets_7"],
        tickets_10=row["tickets_10"],
        images_enabled=bool(row["images_enabled"]),
    )


def _ticket_column_for_sku(sku: str) -> TicketColumn:
    if sku == "TICKET_3":
        return "tickets_3"
    if sku == "TICKET_7":
        return "tickets_7"
    if sku == "TICKET_10":
        return "tickets_10"
    raise ValueError(f"SKU {sku} is not a ticket product")


def _add_days_to_premium(current: datetime | None, days: int, *, now: datetime) -> datetime:
    base = current if current and current > now else now
    return base + timedelta(days=days)


def grant_purchase(user_id: int, sku: str, *, now: datetime | None = None) -> UserRecord:
    now = now or datetime.now(timezone.utc)
    product = get_product(sku)
    if not product:
        raise ValueError(f"Unknown SKU: {sku}")

    ensure_user(user_id, now=now)
    with _connect() as conn:
        if sku.startswith("PASS_"):
            days = 7 if sku == "PASS_7D" else 30
            row = conn.execute(
                "SELECT premium_until FROM users WHERE user_id = ?", (user_id,)
            ).fetchone()
            current_until = datetime.fromisoformat(row["premium_until"]) if row["premium_until"] else None
            new_until = _add_days_to_premium(current_until, days, now=now)
            conn.execute(
                "UPDATE users SET premium_until = ? WHERE user_id = ?",
                (new_until.isoformat(), user_id),
            )
        elif sku.startswith("TICKET_"):
            column = _ticket_column_for_sku(sku)
            conn.execute(
                f"UPDATE users SET {column} = {column} + 1 WHERE user_id = ?",
                (user_id,),
            )
        elif sku == "ADDON_IMAGES":
            conn.execute(
                "UPDATE users SET images_enabled = 1 WHERE user_id = ?",
                (user_id,),
            )
        else:
            raise ValueError(f"Unsupported SKU: {sku}")

    return get_user(user_id)  # type: ignore[return-value]


def consume_ticket(user_id: int, *, ticket: TicketColumn) -> bool:
    ensure_user(user_id)
    with _connect() as conn:
        row = conn.execute(
            f"SELECT {ticket} FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
        if not row or row[ticket] <= 0:
            return False
        conn.execute(
            f"UPDATE users SET {ticket} = {ticket} - 1 WHERE user_id = ?",
            (user_id,),
        )
    return True


def has_active_pass(user_id: int, *, now: datetime | None = None) -> bool:
    now = now or datetime.now(timezone.utc)
    user = get_user(user_id)
    if not user or not user.premium_until:
        return False
    return user.premium_until > now


init_db()

__all__ = [
    "DB_PATH",
    "UserRecord",
    "TicketColumn",
    "consume_ticket",
    "ensure_user",
    "get_user",
    "grant_purchase",
    "has_active_pass",
    "init_db",
    "log_payment",
]
