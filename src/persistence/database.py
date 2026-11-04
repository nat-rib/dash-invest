"""Conexões SQLite, transações curtas e migrations versionadas."""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import os
import sqlite3
from typing import Iterator


DEFAULT_DB_PATH = Path(os.environ.get("DASH_INVEST_DB_PATH", "data/dash_invest.db"))
MIGRATIONS_PATH = Path(__file__).with_name("migrations")


class SQLiteDatabase:
    """Gerencia conexões isoladas por operação e migrations idempotentes."""

    def __init__(self, path: str | Path = DEFAULT_DB_PATH):
        self.path = Path(path)

    def _connect(self) -> sqlite3.Connection:
        if str(self.path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(
            str(self.path), timeout=10, isolation_level=None
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        connection.execute("PRAGMA synchronous = NORMAL")
        return connection

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            yield connection
        finally:
            connection.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _statements(script: str) -> list[str]:
        """Divide SQL em statements completos sem usar executescript (que faz commit implícito)."""
        statements: list[str] = []
        pending = ""
        for line in script.splitlines(keepends=True):
            pending += line
            if sqlite3.complete_statement(pending):
                statement = pending.strip()
                if statement:
                    statements.append(statement)
                pending = ""
        if pending.strip():
            raise ValueError("Migration contém um statement SQL incompleto.")
        return statements

    def initialize(self) -> None:
        """Aplica migrations pendentes em transações atômicas."""
        with self.connection() as connection:
            if str(self.path) != ":memory:":
                connection.execute("PRAGMA journal_mode = WAL")
        with self.transaction() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    applied_at TEXT NOT NULL
                )"""
            )
            applied = {
                int(row["version"])
                for row in connection.execute("SELECT version FROM schema_migrations")
            }
            for migration in sorted(MIGRATIONS_PATH.glob("[0-9][0-9][0-9][0-9]_*.sql")):
                version = int(migration.name.split("_", 1)[0])
                if version in applied:
                    continue
                for statement in self._statements(migration.read_text(encoding="utf-8")):
                    connection.execute(statement)
                connection.execute(
                    "INSERT INTO schema_migrations (version, name, applied_at) VALUES (?, ?, datetime('now'))",
                    (version, migration.name),
                )

    def applied_migrations(self) -> list[tuple[int, str]]:
        with self.connection() as connection:
            exists = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
            ).fetchone()
            if exists is None:
                return []
            rows = connection.execute(
                "SELECT version, name FROM schema_migrations ORDER BY version"
            ).fetchall()
            return [(int(row["version"]), str(row["name"])) for row in rows]
