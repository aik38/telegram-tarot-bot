from __future__ import annotations

import logging
import os
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

from bot.texts.i18n import normalize_lang
from core.store.catalog import get_product

DB_PATH = os.getenv("SQLITE_DB_PATH", "db/telegram_tarot.db")
USAGE_TIMEZONE = timezone(timedelta(hours=9))
logger = logging.getLogger(__name__)


def _usage_date(now: datetime) -> date:
    return now.astimezone(USAGE_TIMEZONE).date()


@dataclass
class UserRecord:
    user_id: int
    created_at: datetime
    first_seen: datetime
    pass_until: datetime | None
    premium_until: datetime | None
    tickets_3: int
    tickets_7: int
    tickets_10: int
    images_enabled: bool
    terms_accepted_at: datetime | None
    general_chat_count_today: int
    one_oracle_count_today: int
    usage_date: date | None
    last_general_chat_block_notice_at: datetime | None
    lang: str | None


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


@dataclass
class PaymentEvent:
    id: int
    user_id: int
    event_type: str
    sku: str | None
    payload: str | None
    created_at: datetime


@dataclass
class AuditRecord:
    id: int
    action: str
    actor_user_id: int
    target_user_id: int | None
    payload: str | None
    status: str
    created_at: datetime


@dataclass
class FeedbackRecord:
    id: int
    user_id: int
    mode: str
    text: str
    request_id: str | None
    created_at: datetime


@dataclass
class AppEventRecord:
    id: int
    event_type: str
    user_id: int | None
    request_id: str | None
    payload: str | None
    created_at: datetime


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


def _normalize_lang(code: str | None) -> str:
    # Prefer shared normalizer to keep behavior aligned with UI helpers
    return normalize_lang(code)


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                created_at TEXT,
                premium_until TEXT,
                pass_until TEXT,
                first_seen TEXT,
                usage_date TEXT,
                general_chat_count_today INT,
                one_oracle_count_today INT,
                tickets_3 INT,
                tickets_7 INT,
                tickets_10 INT,
                images_enabled INT,
                terms_accepted_at TEXT,
                last_general_chat_block_notice_at TEXT,
                lang TEXT
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
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS payment_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INT,
                event_type TEXT,
                sku TEXT,
                payload TEXT,
                created_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INT,
                mode TEXT,
                text TEXT,
                request_id TEXT,
                created_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS app_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT,
                user_id INT,
                request_id TEXT,
                payload TEXT,
                created_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_app_events_created
            ON app_events(created_at)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_feedback_created
            ON feedback(created_at)
            """
        )

        if not _column_exists(conn, "users", "terms_accepted_at"):
            conn.execute("ALTER TABLE users ADD COLUMN terms_accepted_at TEXT")
        if not _column_exists(conn, "users", "pass_until"):
            conn.execute("ALTER TABLE users ADD COLUMN pass_until TEXT")
        if not _column_exists(conn, "users", "first_seen"):
            conn.execute("ALTER TABLE users ADD COLUMN first_seen TEXT")
        if not _column_exists(conn, "users", "usage_date"):
            conn.execute("ALTER TABLE users ADD COLUMN usage_date TEXT")
        if not _column_exists(conn, "users", "general_chat_count_today"):
            conn.execute(
                "ALTER TABLE users ADD COLUMN general_chat_count_today INT DEFAULT 0"
            )
        if not _column_exists(conn, "users", "one_oracle_count_today"):
            conn.execute(
                "ALTER TABLE users ADD COLUMN one_oracle_count_today INT DEFAULT 0"
            )
        if not _column_exists(conn, "users", "last_general_chat_block_notice_at"):
            conn.execute(
                "ALTER TABLE users ADD COLUMN last_general_chat_block_notice_at TEXT"
            )
        if not _column_exists(conn, "users", "lang"):
            conn.execute("ALTER TABLE users ADD COLUMN lang TEXT")

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
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_payment_events_user_created
            ON payment_events(user_id, created_at)
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT,
                actor_user_id INT,
                target_user_id INT,
                payload TEXT,
                status TEXT,
                created_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_audits_action_created
            ON audits(action, created_at)
            """
        )

        _backfill_user_columns(conn)


def ensure_user(user_id: int, *, now: datetime | None = None) -> UserRecord:
    now = now or datetime.now(timezone.utc)
    usage_today = _usage_date(now)
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if row:
            refreshed = _refresh_daily_counts(conn, row, now)
            return _row_to_user(refreshed)

        conn.execute(
            """
            INSERT INTO users (
                user_id,
                created_at,
                premium_until,
                pass_until,
                first_seen,
                usage_date,
                general_chat_count_today,
                one_oracle_count_today,
                tickets_3,
                tickets_7,
                tickets_10,
                images_enabled,
                terms_accepted_at,
                last_general_chat_block_notice_at
            , lang
            )
            VALUES (?, ?, NULL, NULL, ?, ?, 0, 0, 0, 0, 0, 0, NULL, NULL, NULL)
            """,
            (user_id, now.isoformat(), now.isoformat(), usage_today.isoformat()),
        )
        return UserRecord(
            user_id=user_id,
            created_at=now,
            first_seen=now,
            pass_until=None,
            premium_until=None,
            tickets_3=0,
            tickets_7=0,
            tickets_10=0,
            images_enabled=False,
            terms_accepted_at=None,
            general_chat_count_today=0,
            one_oracle_count_today=0,
            usage_date=usage_today,
            last_general_chat_block_notice_at=None,
            lang=None,
        )


def get_user(user_id: int, *, now: datetime | None = None) -> UserRecord | None:
    now = now or datetime.now(timezone.utc)
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if row:
            row = _refresh_daily_counts(conn, row, now)
    if not row:
        return None
    return _row_to_user(row)


def get_user_lang(user_id: int) -> str | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT lang FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
    if not row:
        return None
    lang_raw = row["lang"]
    return _normalize_lang(lang_raw) if lang_raw else None


def set_user_lang(user_id: int, lang: str, *, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    normalized = _normalize_lang(lang)
    ensure_user(user_id, now=now)
    with _connect() as conn:
        conn.execute(
            "UPDATE users SET lang = ? WHERE user_id = ?",
            (normalized, user_id),
        )
    return normalized


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


def log_payment_event(
    *, user_id: int, event_type: str, sku: str | None = None, payload: str | None = None, now: datetime | None = None
) -> PaymentEvent:
    now = now or datetime.now(timezone.utc)
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO payment_events (user_id, event_type, sku, payload, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, event_type, sku, payload, now.isoformat()),
        )
        row = conn.execute(
            "SELECT * FROM payment_events WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (user_id,),
        ).fetchone()
    if row is None:
        raise ValueError("Failed to insert payment event")
    return _row_to_payment_event(row)


def log_audit(
    *,
    action: str,
    actor_user_id: int,
    target_user_id: int | None,
    payload: str | None,
    status: str,
    now: datetime | None = None,
) -> AuditRecord:
    now = now or datetime.now(timezone.utc)
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO audits (action, actor_user_id, target_user_id, payload, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (action, actor_user_id, target_user_id, payload, status, now.isoformat()),
        )
        row = conn.execute(
            "SELECT * FROM audits WHERE action = ? ORDER BY id DESC LIMIT 1",
            (action,),
        ).fetchone()
    if row is None:
        raise ValueError("Failed to insert audit record")
    return _row_to_audit(row)


def get_latest_audit(action: str | None = None) -> AuditRecord | None:
    query = "SELECT * FROM audits"
    params: tuple[object, ...] = ()
    if action:
        query += " WHERE action = ?"
        params = (action,)
    query += " ORDER BY id DESC LIMIT 1"
    with _connect() as conn:
        row = conn.execute(query, params).fetchone()
    if not row:
        return None
    return _row_to_audit(row)


def get_latest_payment(user_id: int) -> PaymentRecord | None:
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT * FROM payments
            WHERE user_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()
    if not row:
        return None
    return _row_to_payment(row)


def check_db_health() -> tuple[bool, list[str]]:
    messages: list[str] = []
    db_file = Path(DB_PATH)
    if not db_file.exists():
        message = f"DB file missing at {db_file}"
        logger.error(message)
        return False, [message]

    try:
        with _connect() as conn:
            integrity = conn.execute("PRAGMA quick_check").fetchone()
            if not integrity or integrity[0] != "ok":
                message = f"PRAGMA quick_check failed: {integrity[0] if integrity else 'unknown'}"
                logger.error(message)
                return False, [message]

            requirements: dict[str, set[str]] = {
                "users": {
                    "user_id",
                    "created_at",
                    "premium_until",
                    "pass_until",
                    "first_seen",
                    "usage_date",
                    "general_chat_count_today",
                    "one_oracle_count_today",
                    "tickets_3",
                    "tickets_7",
                    "tickets_10",
                    "images_enabled",
                    "terms_accepted_at",
                    "last_general_chat_block_notice_at",
                    "lang",
                },
                "payments": {
                    "user_id",
                    "sku",
                    "stars",
                    "telegram_payment_charge_id",
                    "provider_payment_charge_id",
                    "status",
                    "refund_id",
                    "created_at",
                    "refunded_at",
                },
                "payment_events": {
                    "user_id",
                    "event_type",
                    "sku",
                    "payload",
                    "created_at",
                },
                "audits": {
                    "action",
                    "actor_user_id",
                    "target_user_id",
                    "payload",
                    "status",
                    "created_at",
                },
                "feedback": {
                    "user_id",
                    "mode",
                    "text",
                    "request_id",
                    "created_at",
                },
                "app_events": {
                    "event_type",
                    "user_id",
                    "request_id",
                    "payload",
                    "created_at",
                },
            }

            for table, required_columns in requirements.items():
                rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
                if not rows:
                    message = f"table missing: {table}"
                    logger.error(message)
                    messages.append(message)
                    continue
                present = {row[1] for row in rows}
                missing = required_columns - present
                if missing:
                    message = f"table {table} missing columns: {', '.join(sorted(missing))}"
                    logger.error(message)
                    messages.append(message)
                else:
                    messages.append(f"table {table}: ok ({len(present)} columns)")

    except Exception as exc:  # pragma: no cover - defensive
        message = f"DB health check failed with exception: {exc}"
        logger.exception(message)
        return False, [message]

    return (not any(msg.startswith("table missing") or "missing columns" in msg for msg in messages)), messages


def _row_to_user(row: sqlite3.Row) -> UserRecord:
    premium_until = row["premium_until"]
    pass_until = row["pass_until"]
    premium_dt = datetime.fromisoformat(premium_until) if premium_until else None
    pass_dt = datetime.fromisoformat(pass_until) if pass_until else None
    terms_accepted_raw = row["terms_accepted_at"]
    terms_accepted_dt = (
        datetime.fromisoformat(terms_accepted_raw) if terms_accepted_raw else None
    )
    first_seen_raw = row["first_seen"] or row["created_at"]
    first_seen_dt = datetime.fromisoformat(first_seen_raw)
    usage_date_raw = row["usage_date"]
    usage_date = date.fromisoformat(usage_date_raw) if usage_date_raw else None
    last_notice_raw = row["last_general_chat_block_notice_at"]
    last_notice_dt = datetime.fromisoformat(last_notice_raw) if last_notice_raw else None
    lang_raw = row["lang"]
    return UserRecord(
        user_id=row["user_id"],
        created_at=datetime.fromisoformat(row["created_at"]),
        first_seen=first_seen_dt,
        pass_until=pass_dt,
        premium_until=premium_dt,
        tickets_3=row["tickets_3"],
        tickets_7=row["tickets_7"],
        tickets_10=row["tickets_10"],
        images_enabled=bool(row["images_enabled"]),
        terms_accepted_at=terms_accepted_dt,
        general_chat_count_today=row["general_chat_count_today"],
        one_oracle_count_today=row["one_oracle_count_today"],
        usage_date=usage_date,
        last_general_chat_block_notice_at=last_notice_dt,
        lang=_normalize_lang(lang_raw) if lang_raw else None,
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


def _row_to_payment_event(row: sqlite3.Row) -> PaymentEvent:
    return PaymentEvent(
        id=row["id"],
        user_id=row["user_id"],
        event_type=row["event_type"],
        sku=row["sku"],
        payload=row["payload"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )


def _row_to_audit(row: sqlite3.Row) -> AuditRecord:
    return AuditRecord(
        id=row["id"],
        action=row["action"],
        actor_user_id=row["actor_user_id"],
        target_user_id=row["target_user_id"],
        payload=row["payload"],
        status=row["status"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )


def _row_to_feedback(row: sqlite3.Row) -> FeedbackRecord:
    return FeedbackRecord(
        id=row["id"],
        user_id=row["user_id"],
        mode=row["mode"],
        text=row["text"],
        request_id=row["request_id"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )


def _row_to_app_event(row: sqlite3.Row) -> AppEventRecord:
    return AppEventRecord(
        id=row["id"],
        event_type=row["event_type"],
        user_id=row["user_id"],
        request_id=row["request_id"],
        payload=row["payload"],
        created_at=datetime.fromisoformat(row["created_at"]),
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
                "SELECT pass_until FROM users WHERE user_id = ?", (user_id,)
            ).fetchone()
            current_until = (
                datetime.fromisoformat(row["pass_until"])
                if row["pass_until"]
                else None
            )
            new_until = _add_days_to_premium(current_until, days, now=now)
            conn.execute(
                "UPDATE users SET pass_until = ?, premium_until = ? WHERE user_id = ?",
                (new_until.isoformat(), new_until.isoformat(), user_id),
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


def revoke_purchase(user_id: int, sku: str, *, now: datetime | None = None) -> UserRecord:
    now = now or datetime.now(timezone.utc)
    ensure_user(user_id, now=now)
    with _connect() as conn:
        if sku.startswith("PASS_") or sku.startswith("PREMIUM_"):
            conn.execute(
                "UPDATE users SET pass_until = NULL, premium_until = NULL WHERE user_id = ?",
                (user_id,),
            )
        elif sku.startswith("TICKET_"):
            column = _ticket_column_for_sku(sku)
            conn.execute(
                f"UPDATE users SET {column} = MAX({column} - 1, 0) WHERE user_id = ?",
                (user_id,),
            )
        elif sku == "ADDON_IMAGES":
            conn.execute(
                "UPDATE users SET images_enabled = 0 WHERE user_id = ?",
                (user_id,),
            )
        else:
            raise ValueError(f"Unsupported SKU for revoke: {sku}")
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


def set_last_general_chat_block_notice(
    user_id: int, *, now: datetime | None = None
) -> UserRecord:
    now = now or datetime.now(timezone.utc)
    ensure_user(user_id, now=now)
    with _connect() as conn:
        conn.execute(
            "UPDATE users SET last_general_chat_block_notice_at = ? WHERE user_id = ?",
            (now.isoformat(), user_id),
        )
    return get_user(user_id)  # type: ignore[return-value]


def has_active_pass(user_id: int, *, now: datetime | None = None) -> bool:
    now = now or datetime.now(timezone.utc)
    user = get_user(user_id, now=now)
    if not user:
        return False
    if user.pass_until:
        return user.pass_until > now
    if user.premium_until:
        return user.premium_until > now
    return False


def increment_general_chat_count(user_id: int, *, now: datetime | None = None) -> UserRecord:
    return _increment_daily_count(
        user_id, column="general_chat_count_today", now=now
    )


def increment_one_oracle_count(user_id: int, *, now: datetime | None = None) -> UserRecord:
    return _increment_daily_count(
        user_id, column="one_oracle_count_today", now=now
    )


def _increment_daily_count(
    user_id: int, *, column: str, now: datetime | None = None
) -> UserRecord:
    now = now or datetime.now(timezone.utc)
    ensure_user(user_id, now=now)
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if row is None:
            raise ValueError("User must exist to increment usage counters")
        today = _usage_date(now)
        last_usage_raw = row["usage_date"]
        last_usage = date.fromisoformat(last_usage_raw) if last_usage_raw else None
        new_count = (row[column] + 1) if last_usage == today else 1
        conn.execute(
            f"""
            UPDATE users
            SET usage_date = ?,
                {column} = ?
            WHERE user_id = ?
            """,
            (today.isoformat(), new_count, user_id),
        )
        updated = conn.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
    if updated is None:
        raise ValueError("Failed to reload user after increment")
    return _row_to_user(updated)


def _refresh_daily_counts(
    conn: sqlite3.Connection, row: sqlite3.Row, now: datetime
) -> sqlite3.Row:
    usage_raw = row["usage_date"]
    today = _usage_date(now)
    usage_date_val = date.fromisoformat(usage_raw) if usage_raw else None
    if usage_date_val == today:
        return row

    conn.execute(
        """
        UPDATE users
        SET usage_date = ?, general_chat_count_today = 0, one_oracle_count_today = 0
        WHERE user_id = ?
        """,
        (today.isoformat(), row["user_id"]),
    )
    refreshed = conn.execute(
        "SELECT * FROM users WHERE user_id = ?", (row["user_id"],)
    ).fetchone()
    return refreshed if refreshed else row


def log_feedback(
    *,
    user_id: int,
    mode: str,
    text: str,
    request_id: str | None,
    now: datetime | None = None,
) -> FeedbackRecord:
    now = now or datetime.now(timezone.utc)
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO feedback (user_id, mode, text, request_id, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, mode, text, request_id, now.isoformat()),
        )
        row = conn.execute(
            "SELECT * FROM feedback ORDER BY id DESC LIMIT 1"
        ).fetchone()
    if row is None:
        raise ValueError("Failed to insert feedback")
    return _row_to_feedback(row)


def get_recent_feedback(limit: int = 10) -> list[FeedbackRecord]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM feedback ORDER BY created_at DESC, id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [_row_to_feedback(row) for row in rows]


def log_app_event(
    *,
    event_type: str,
    user_id: int | None,
    request_id: str | None,
    payload: str | None = None,
    now: datetime | None = None,
) -> AppEventRecord:
    now = now or datetime.now(timezone.utc)
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO app_events (event_type, user_id, request_id, payload, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (event_type, user_id, request_id, payload, now.isoformat()),
        )
        row = conn.execute(
            "SELECT * FROM app_events ORDER BY id DESC LIMIT 1"
        ).fetchone()
    if row is None:
        raise ValueError("Failed to insert app event")
    return _row_to_app_event(row)


def get_daily_stats(*, days: int = 7, now: datetime | None = None) -> list[dict[str, object]]:
    now = now or datetime.now(timezone.utc)
    days = max(1, min(14, days))
    end_date = _usage_date(now)
    start_date = end_date - timedelta(days=days - 1)
    day_jst_expr = "date(replace(substr(created_at, 1, 19), 'T', ' '), '+9 hours')"

    with _connect() as conn:
        rows = conn.execute(
            f"""
            WITH RECURSIVE days(day) AS (
                SELECT date(?) AS day
                UNION ALL
                SELECT date(day, '+1 day')
                FROM days
                WHERE day < date(?)
            ),
            event_base AS (
                SELECT
                    {day_jst_expr} AS day_jst,
                    event_type,
                    user_id
                FROM app_events
                WHERE {day_jst_expr} BETWEEN date(?) AND date(?)
                  AND event_type IN ('consult', 'tarot', 'error')
            ),
            usage_events AS (
                SELECT
                    day_jst,
                    SUM(event_type = 'consult') AS consult,
                    SUM(event_type = 'tarot') AS tarot,
                    COUNT(*) AS uses,
                    COUNT(DISTINCT user_id) AS dau
                FROM event_base
                WHERE event_type IN ('consult', 'tarot')
                GROUP BY day_jst
            ),
            error_events AS (
                SELECT day_jst, COUNT(*) AS errors
                FROM event_base
                WHERE event_type = 'error'
                GROUP BY day_jst
            ),
            payment_base AS (
                SELECT
                    {day_jst_expr} AS day_jst,
                    stars
                FROM payments
                WHERE {day_jst_expr} BETWEEN date(?) AND date(?)
                  AND COALESCE(status, 'paid') = 'paid'
                  AND (refunded_at IS NULL OR refunded_at = '')
            ),
            payment_stats AS (
                SELECT
                    day_jst,
                    COUNT(*) AS payments,
                    COALESCE(SUM(stars), 0) AS stars_sales
                FROM payment_base
                GROUP BY day_jst
            )
            SELECT
                days.day AS date,
                COALESCE(usage_events.consult, 0) AS consult,
                COALESCE(usage_events.tarot, 0) AS tarot,
                COALESCE(usage_events.uses, 0) AS uses,
                COALESCE(usage_events.dau, 0) AS dau,
                COALESCE(payment_stats.payments, 0) AS payments,
                COALESCE(payment_stats.stars_sales, 0) AS stars_sales,
                COALESCE(error_events.errors, 0) AS errors
            FROM days
            LEFT JOIN usage_events ON usage_events.day_jst = days.day
            LEFT JOIN error_events ON error_events.day_jst = days.day
            LEFT JOIN payment_stats ON payment_stats.day_jst = days.day
            ORDER BY date(days.day) DESC
            """,
            (
                start_date.isoformat(),
                end_date.isoformat(),
                start_date.isoformat(),
                end_date.isoformat(),
                start_date.isoformat(),
                end_date.isoformat(),
            ),
        ).fetchall()

    return [dict(row) for row in rows]


def _backfill_user_columns(conn: sqlite3.Connection) -> None:
    now = datetime.now(timezone.utc)
    today = _usage_date(now).isoformat()
    conn.execute(
        """
        UPDATE users
        SET first_seen = COALESCE(first_seen, created_at),
            usage_date = COALESCE(usage_date, ?),
            general_chat_count_today = COALESCE(general_chat_count_today, 0),
            one_oracle_count_today = COALESCE(one_oracle_count_today, 0),
            pass_until = COALESCE(pass_until, premium_until),
            last_general_chat_block_notice_at = COALESCE(last_general_chat_block_notice_at, NULL),
            lang = CASE
                WHEN lang IS NULL THEN NULL
                WHEN lower(replace(lang, '_', '-')) LIKE 'pt%' THEN 'pt'
                WHEN lower(replace(lang, '_', '-')) LIKE 'en%' THEN 'en'
                ELSE 'ja'
            END
        """,
        (today,),
    )


init_db()

__all__ = [
    "DB_PATH",
    "AuditRecord",
    "PaymentEvent",
    "PaymentRecord",
    "UserRecord",
    "AppEventRecord",
    "FeedbackRecord",
    "TicketColumn",
    "get_daily_stats",
    "check_db_health",
    "consume_ticket",
    "ensure_user",
    "get_user",
    "get_user_lang",
    "get_recent_feedback",
    "get_latest_audit",
    "get_latest_payment",
    "get_payment_by_charge_id",
    "grant_purchase",
    "has_active_pass",
    "has_accepted_terms",
    "increment_general_chat_count",
    "increment_one_oracle_count",
    "init_db",
    "log_payment",
    "log_app_event",
    "log_feedback",
    "log_payment_event",
    "log_audit",
    "mark_payment_refunded",
    "revoke_purchase",
    "set_user_lang",
    "set_last_general_chat_block_notice",
    "set_terms_accepted",
]
