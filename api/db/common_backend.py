from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal

from .migrate import DEFAULT_DB_PATH, apply_migrations


@dataclass
class Plan:
    id: int
    plan_code: str
    credit_quota: int
    period_days: int


@dataclass
class Entitlement:
    id: int
    account_id: int
    plan: Plan
    credits_used: int
    active_from: datetime
    period_end: datetime


class CommonBackendDB:
    """Tiny SQLite access layer for the common backend tables."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path is not None else DEFAULT_DB_PATH
        apply_migrations(self.db_path)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON;")
        return connection

    def resolve_identity(
        self, provider: Literal["telegram", "line"], provider_user_id: str
    ) -> tuple[int, int]:
        """Ensure an identity exists and update last_seen_at."""

        with self._connect() as connection:
            cursor = connection.execute(
                """
                SELECT id, account_id FROM identities
                WHERE provider = ? AND provider_user_id = ?
                """,
                (provider, provider_user_id),
            )
            row = cursor.fetchone()

            if row:
                identity_id = int(row["id"])
                account_id = int(row["account_id"])
                connection.execute(
                    "UPDATE identities SET last_seen_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (identity_id,),
                )
                connection.commit()
                return account_id, identity_id

            account_cursor = connection.execute(
                "INSERT INTO accounts DEFAULT VALUES"
            )
            account_id = int(account_cursor.lastrowid)

            identity_cursor = connection.execute(
                """
                INSERT INTO identities (account_id, provider, provider_user_id)
                VALUES (?, ?, ?)
                """,
                (account_id, provider, provider_user_id),
            )
            identity_id = int(identity_cursor.lastrowid)
            connection.commit()

        return account_id, identity_id

    def check_entitlement(self, account_id: int) -> tuple[Entitlement, int, datetime]:
        with self._connect() as connection:
            entitlement = self._ensure_entitlement(connection, account_id)
            credits_remaining = entitlement.plan.credit_quota - entitlement.credits_used
            return entitlement, credits_remaining, entitlement.period_end

    def consume_entitlement(
        self,
        account_id: int,
        feature: str,
        units: int,
        request_id: str,
    ) -> tuple[bool, int]:
        with self._connect() as connection:
            connection.execute("BEGIN;")
            existing = connection.execute(
                """
                SELECT metadata FROM usage_events WHERE request_id = ?
                """,
                (request_id,),
            ).fetchone()
            if existing:
                metadata = json.loads(existing["metadata"]) if existing["metadata"] else {}
                allowed = bool(metadata.get("allowed", False))
                credits_remaining = int(metadata.get("credits_remaining", 0))
                connection.commit()
                return allowed, credits_remaining

            entitlement = self._ensure_entitlement(connection, account_id)
            credits_remaining = entitlement.plan.credit_quota - entitlement.credits_used

            if credits_remaining < units:
                metadata = {
                    "allowed": False,
                    "credits_remaining": credits_remaining,
                    "reason": "insufficient_credits",
                }
                connection.execute(
                    """
                    INSERT INTO usage_events (account_id, event_type, feature, metadata, request_id)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        account_id,
                        "entitlement.consume",
                        feature,
                        json.dumps(metadata),
                        request_id,
                    ),
                )
                connection.commit()
                return False, credits_remaining

            new_used = entitlement.credits_used + units
            credits_remaining = entitlement.plan.credit_quota - new_used

            connection.execute(
                "UPDATE entitlements SET credits_used = ? WHERE id = ?",
                (new_used, entitlement.id),
            )
            metadata = {
                "allowed": True,
                "credits_remaining": credits_remaining,
                "feature": feature,
                "units": units,
            }
            connection.execute(
                """
                INSERT INTO usage_events (account_id, event_type, feature, metadata, request_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    account_id,
                    "entitlement.consume",
                    feature,
                    json.dumps(metadata),
                    request_id,
                ),
            )
            connection.commit()
            return True, credits_remaining

    def increment_line_message_usage(
        self,
        account_id: int,
        user_id: str,
        request_id: str,
        monthly_limit: int,
    ) -> tuple[bool, int]:
        """Increment the LINE monthly message count with idempotency.

        Returns:
            allowed: Whether the increment is within the monthly limit.
            remaining: Remaining messages for the current month (0 if exceeded).
        """

        year_month = datetime.now(timezone.utc).strftime("%Y-%m")
        monthly_limit = max(0, monthly_limit)

        with self._connect() as connection:
            connection.execute("BEGIN;")
            existing = connection.execute(
                """
                SELECT metadata FROM usage_events WHERE request_id = ?
                """,
                (request_id,),
            ).fetchone()
            if existing:
                metadata = (
                    json.loads(existing["metadata"]) if existing["metadata"] else {}
                )
                allowed = bool(metadata.get("allowed", False))
                remaining = int(metadata.get("remaining", 0))
                connection.commit()
                return allowed, remaining

            count_row = connection.execute(
                """
                SELECT COUNT(*) AS count
                FROM usage_events
                WHERE account_id = ?
                  AND event_type = 'line.message'
                  AND strftime('%Y-%m', occurred_at) = ?
                """,
                (account_id, year_month),
            ).fetchone()
            current_count = int(count_row["count"] if count_row else 0)
            new_count = current_count + 1
            allowed = new_count <= monthly_limit
            remaining = max(0, monthly_limit - new_count)

            metadata = {
                "allowed": allowed,
                "remaining": remaining,
                "feature": "line.monthly_messages",
                "year_month": year_month,
                "user_id": user_id,
                "new_count": new_count,
            }
            connection.execute(
                """
                INSERT INTO usage_events (account_id, event_type, feature, metadata, request_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    account_id,
                    "line.message",
                    "line.monthly_messages",
                    json.dumps(metadata),
                    request_id,
                ),
            )
            connection.commit()

            return allowed, remaining

    def _ensure_entitlement(
        self, connection: sqlite3.Connection, account_id: int
    ) -> Entitlement:
        entitlement_row = connection.execute(
            """
            SELECT id, account_id, plan_id, credits_used, active_from, period_end
            FROM entitlements
            WHERE account_id = ?
            ORDER BY active_from DESC
            LIMIT 1
            """,
            (account_id,),
        ).fetchone()

        if entitlement_row:
            plan = self._get_plan_by_id(connection, int(entitlement_row["plan_id"]))
            entitlement = self._build_entitlement(entitlement_row, plan)
            if entitlement.period_end <= datetime.now(timezone.utc):
                entitlement = self._reset_entitlement_period(
                    connection, entitlement.id, plan
                )
            return entitlement

        plan = self._get_default_plan(connection)
        now = datetime.now(timezone.utc)
        period_end = now + timedelta(days=plan.period_days)
        cursor = connection.execute(
            """
            INSERT INTO entitlements (account_id, plan_id, active_from, period_end, credits_used)
            VALUES (?, ?, ?, ?, 0)
            """,
            (
                account_id,
                plan.id,
                now.isoformat(),
                period_end.isoformat(),
            ),
        )
        ent_id = int(cursor.lastrowid)
        connection.commit()

        return Entitlement(
            id=ent_id,
            account_id=account_id,
            plan=plan,
            credits_used=0,
            active_from=now,
            period_end=period_end,
        )

    def _get_default_plan(self, connection: sqlite3.Connection) -> Plan:
        row = connection.execute(
            """
            SELECT id, plan_code, credit_quota, period_days
            FROM plans
            WHERE plan_code = 'free'
            LIMIT 1
            """
        ).fetchone()

        if not row:
            raise RuntimeError("Default plan not found")

        return Plan(
            id=int(row["id"]),
            plan_code=str(row["plan_code"]),
            credit_quota=int(row["credit_quota"]),
            period_days=int(row["period_days"]),
        )

    def _get_plan_by_id(self, connection: sqlite3.Connection, plan_id: int) -> Plan:
        row = connection.execute(
            """
            SELECT id, plan_code, credit_quota, period_days
            FROM plans
            WHERE id = ?
            LIMIT 1
            """,
            (plan_id,),
        ).fetchone()

        if not row:
            raise RuntimeError(f"Plan not found for id {plan_id}")

        return Plan(
            id=int(row["id"]),
            plan_code=str(row["plan_code"]),
            credit_quota=int(row["credit_quota"]),
            period_days=int(row["period_days"]),
        )

    def _build_entitlement(self, row: sqlite3.Row, plan: Plan) -> Entitlement:
        active_from = self._parse_datetime(row["active_from"])
        period_end = self._parse_datetime(row["period_end"])
        return Entitlement(
            id=int(row["id"]),
            account_id=int(row["account_id"]),
            plan=plan,
            credits_used=int(row["credits_used"]),
            active_from=active_from,
            period_end=period_end,
        )

    def _reset_entitlement_period(
        self, connection: sqlite3.Connection, entitlement_id: int, plan: Plan
    ) -> Entitlement:
        now = datetime.now(timezone.utc)
        period_end = now + timedelta(days=plan.period_days)
        account_id_row = connection.execute(
            "SELECT account_id FROM entitlements WHERE id = ?", (entitlement_id,)
        ).fetchone()
        account_id = int(account_id_row["account_id"]) if account_id_row else 0
        connection.execute(
            """
            UPDATE entitlements
            SET credits_used = 0,
                active_from = ?,
                period_end = ?
            WHERE id = ?
            """,
            (
                now.isoformat(),
                period_end.isoformat(),
                entitlement_id,
            ),
        )
        connection.commit()
        return Entitlement(
            id=entitlement_id,
            account_id=account_id,
            plan=plan,
            credits_used=0,
            active_from=now,
            period_end=period_end,
        )

    @staticmethod
    def _parse_datetime(value: Any) -> datetime:
        if value is None:
            return datetime.now(timezone.utc)
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(str(value)).replace(tzinfo=timezone.utc)
