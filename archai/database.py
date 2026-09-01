"""SQLite connection lifecycle and forward-only schema migrations."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from flask import Flask, current_app, g

MIGRATIONS = (
    (
        1,
        """
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            schema_version INTEGER NOT NULL,
            brief_json TEXT NOT NULL,
            results_json TEXT NOT NULL,
            active_index INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS projects_updated_at_idx
            ON projects(updated_at DESC);
        """,
    ),
)


def get_db() -> sqlite3.Connection:
    """Return the request-scoped SQLite connection."""

    if "db" not in g:
        database_path = Path(current_app.config["DATABASE"])
        database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        g.db = connection
    return g.db


def close_db(_error: BaseException | None = None) -> None:
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


@contextmanager
def transaction() -> Iterator[sqlite3.Connection]:
    connection = get_db()
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise


def migrate_database() -> None:
    """Apply every unapplied migration in ascending version order."""

    connection = get_db()
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    applied = {
        row["version"] for row in connection.execute("SELECT version FROM schema_migrations")
    }
    for version, script in MIGRATIONS:
        if version in applied:
            continue
        with transaction() as active_connection:
            active_connection.executescript(script)
            active_connection.execute(
                "INSERT OR IGNORE INTO schema_migrations (version) VALUES (?)", (version,)
            )


def init_app(app: Flask) -> None:
    app.teardown_appcontext(close_db)
    with app.app_context():
        migrate_database()
