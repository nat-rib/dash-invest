"""Watchlist: ativos acompanhados manualmente."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime

from src.persistence.database import SQLiteDatabase


@dataclass(frozen=True)
class WatchlistItem:
    asset_key: str
    name: str
    asset_class: str
    note: str | None
    created_at: datetime


def _from_row(row: sqlite3.Row) -> WatchlistItem:
    return WatchlistItem(
        asset_key=row["asset_key"],
        name=row["name"],
        asset_class=row["asset_class"],
        note=row["note"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )


class WatchlistRepository:
    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    def add(self, item: WatchlistItem) -> None:
        with self.database.transaction() as connection:
            connection.execute(
                """INSERT INTO watchlist (asset_key, name, asset_class, note, created_at)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(asset_key) DO UPDATE SET
                       name = excluded.name,
                       asset_class = excluded.asset_class,
                       note = excluded.note""",
                (
                    item.asset_key,
                    item.name,
                    item.asset_class,
                    item.note,
                    item.created_at.isoformat(),
                ),
            )

    def remove(self, asset_key: str) -> bool:
        with self.database.transaction() as connection:
            cursor = connection.execute(
                "DELETE FROM watchlist WHERE asset_key = ?", (asset_key,)
            )
            return bool(cursor.rowcount)

    def list(self) -> list[WatchlistItem]:
        with self.database.connection() as connection:
            rows = connection.execute(
                "SELECT * FROM watchlist ORDER BY created_at DESC, asset_key"
            ).fetchall()
        return [_from_row(row) for row in rows]

    def contains(self, asset_key: str) -> bool:
        with self.database.connection() as connection:
            row = connection.execute(
                "SELECT 1 FROM watchlist WHERE asset_key = ?", (asset_key,)
            ).fetchone()
        return row is not None

    def count(self) -> int:
        with self.database.connection() as connection:
            row = connection.execute("SELECT COUNT(*) AS total FROM watchlist").fetchone()
        return int(row["total"])
