from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"
DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "db" / "common_backend.db"
MIGRATION_FILES: Iterable[str] = (
    "001_init.sql",
    "002_entitlements.sql",
)


def apply_migrations(db_path: str | Path | None = None) -> Path:
    """Apply SQLite migrations idempotently.

    Args:
        db_path: Optional path to the database file. Defaults to db/common_backend.db
            at the repository root.

    Returns:
        Path to the database file the migrations were applied to.
    """

    target_path = Path(db_path) if db_path is not None else DEFAULT_DB_PATH
    target_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(target_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON;")
        connection.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations (filename TEXT PRIMARY KEY)"
        )

        for filename in MIGRATION_FILES:
            already_applied = connection.execute(
                "SELECT 1 FROM schema_migrations WHERE filename = ?", (filename,)
            ).fetchone()
            if already_applied:
                continue

            migration_sql = (MIGRATIONS_DIR / filename).read_text(encoding="utf-8")
            connection.executescript(migration_sql)
            connection.execute(
                "INSERT INTO schema_migrations (filename) VALUES (?)", (filename,)
            )

        connection.commit()

    return target_path
