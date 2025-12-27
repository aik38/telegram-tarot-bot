import sqlite3
from pathlib import Path

from api.db.migrate import apply_migrations


def get_tables(db_path: Path) -> set[str]:
    with sqlite3.connect(db_path) as connection:
        cursor = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
        )
        return {row[0] for row in cursor.fetchall()}


def test_apply_migrations_creates_tables(tmp_path: Path) -> None:
    db_file = tmp_path / "common_backend.db"

    apply_migrations(db_file)

    tables = get_tables(db_file)
    expected_tables = {
        "accounts",
        "identities",
        "plans",
        "entitlements",
        "stripe_subscriptions",
        "payments",
        "stripe_events",
        "usage_events",
    }
    assert expected_tables.issubset(tables)


def test_apply_migrations_is_idempotent(tmp_path: Path) -> None:
    db_file = tmp_path / "idempotent_backend.db"

    apply_migrations(db_file)
    apply_migrations(db_file)

    tables = get_tables(db_file)
    assert "accounts" in tables
