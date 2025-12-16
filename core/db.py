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
    terms_accepted_at: datetime | None


@dataclass
class PaymentRecord:
    id: int
    user_id: int
    sku: str
    stars: int
    telegram_payment_charge_id: str | None
    provider_payment_charge_id: str | None
    status: str
    refund_id: str | None
    created_at: datetime
    refunded_at: datetime | None


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


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row[1] == column for row in rows)


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
                images_enabled INT,
                terms_accepted_at TEXT
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
                status TEXT,
                refund_id TEXT,
                created_at TEXT,
                refunded_at TEXT
            )
            """
        )

        if not _column_exists(conn, "users", "terms_accepted_at"):
            conn.execute("ALTER TABLE users ADD COLUMN terms_accepted_at TEXT")

        if not _column_exists(conn, "payments", "status"):
            conn.execute("ALTER TABLE payments ADD COLUMN status TEXT")
        if not _column_exists(conn, "payments", "refund_id"):
            conn.execute("ALTER TABLE payments ADD COLUMN refund_id TEXT")
        if not _column_exists(conn, "payments", "refunded_at"):
            conn.execute("ALTER TABLE payments ADD COLUMN refunded_at TEXT")
        if not _column_exists(conn, "payments", "telegram_payment_charge_id"):
            conn.execute(
                "ALTER TABLE payments ADD COLUMN telegram_payment_charge_id TEXT"
            )
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_payments_telegram_charge_id
            ON payments(telegram_payment_charge_id)
            WHERE telegram_payment_charge_id IS NOT NULL
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
            INSERT INTO users (user_id, created_at, premium_until, tickets_3, tickets_7, tickets_10, images_enabled, terms_accepted_at)
            VALUES (?, ?, NULL, 0, 0, 0, 0, NULL)
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
            terms_accepted_at=None,
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
) -> tuple[PaymentRecord, bool]:
    now = now or datetime.now(timezone.utc)
    with _connect() as conn:
        if telegram_payment_charge_id:
            existing = conn.execute(
                "SELECT * FROM payments WHERE telegram_payment_charge_id = ?",
                (telegram_payment_charge_id,),
            ).fetchone()
            if existing:
                return _row_to_payment(existing), False

        conn.execute(
            """
            INSERT INTO payments (
                user_id, sku, stars, telegram_payment_charge_id, provider_payment_charge_id, status, refund_id, created_at, refunded_at
            ) VALUES (?, ?, ?, ?, ?, 'paid', NULL, ?, NULL)
            """,
            (
                user_id,
                sku,
                stars,
                telegram_payment_charge_id,
                provider_payment_charge_id,
                now.isoformat(),
            ),
        )
        new_row = conn.execute(
            "SELECT * FROM payments WHERE telegram_payment_charge_id IS ? ORDER BY id DESC LIMIT 1",
            (telegram_payment_charge_id,),
        ).fetchone()
        return _row_to_payment(new_row), True


def get_payment_by_charge_id(telegram_payment_charge_id: str) -> PaymentRecord | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM payments WHERE telegram_payment_charge_id = ?",
            (telegram_payment_charge_id,),
        ).fetchone()
    if not row:
        return None
    return _row_to_payment(row)


def mark_payment_refunded(
    telegram_payment_charge_id: str, *, refund_id: str | None = None, now: datetime | None = None
) -> PaymentRecord | None:
    now = now or datetime.now(timezone.utc)
    with _connect() as conn:
        conn.execute(
            """
            UPDATE payments
            SET status = 'refunded', refund_id = COALESCE(?, refund_id), refunded_at = ?
            WHERE telegram_payment_charge_id = ?
            """,
            (refund_id, now.isoformat(), telegram_payment_charge_id),
        )
        row = conn.execute(
            "SELECT * FROM payments WHERE telegram_payment_charge_id = ?",
            (telegram_payment_charge_id,),
        ).fetchone()
    if not row:
        return None
    return _row_to_payment(row)


def _row_to_user(row: sqlite3.Row) -> UserRecord:
    premium_until = row["premium_until"]
    premium_dt = datetime.fromisoformat(premium_until) if premium_until else None
    terms_accepted_raw = row["terms_accepted_at"]
    terms_accepted_dt = (
        datetime.fromisoformat(terms_accepted_raw) if terms_accepted_raw else None
    )
    return UserRecord(
        user_id=row["user_id"],
        created_at=datetime.fromisoformat(row["created_at"]),
        premium_until=premium_dt,
        tickets_3=row["tickets_3"],
        tickets_7=row["tickets_7"],
        tickets_10=row["tickets_10"],
        images_enabled=bool(row["images_enabled"]),
        terms_accepted_at=terms_accepted_dt,
    )


def _row_to_payment(row: sqlite3.Row) -> PaymentRecord:
    return PaymentRecord(
        id=row["id"],
        user_id=row["user_id"],
        sku=row["sku"],
        stars=row["stars"],
        telegram_payment_charge_id=row["telegram_payment_charge_id"],
        provider_payment_charge_id=row["provider_payment_charge_id"],
        status=row["status"] if row["status"] else "paid",
        refund_id=row["refund_id"],
        created_at=datetime.fromisoformat(row["created_at"]),
        refunded_at=(
            datetime.fromisoformat(row["refunded_at"])
            if row["refunded_at"]
            else None
        ),
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


def has_accepted_terms(user_id: int) -> bool:
    user = get_user(user_id)
    return bool(user and user.terms_accepted_at)


def set_terms_accepted(user_id: int, *, now: datetime | None = None) -> UserRecord:
    now = now or datetime.now(timezone.utc)
    ensure_user(user_id, now=now)
    with _connect() as conn:
        conn.execute(
            "UPDATE users SET terms_accepted_at = ? WHERE user_id = ?",
            (now.isoformat(), user_id),
        )
    return get_user(user_id)  # type: ignore[return-value]


def has_active_pass(user_id: int, *, now: datetime | None = None) -> bool:
    now = now or datetime.now(timezone.utc)
    user = get_user(user_id)
    if not user or not user.premium_until:
        return False
    return user.premium_until > now


init_db()

__all__ = [
    "DB_PATH",
    "PaymentRecord",
    "UserRecord",
    "TicketColumn",
    "consume_ticket",
    "ensure_user",
    "get_user",
    "get_payment_by_charge_id",
    "grant_purchase",
    "has_active_pass",
    "has_accepted_terms",
    "init_db",
    "log_payment",
    "mark_payment_refunded",
    "set_terms_accepted",
]
