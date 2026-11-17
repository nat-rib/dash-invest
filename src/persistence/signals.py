"""Repositório de sinais externos."""
from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from datetime import datetime

from src.domain.signals import AssetMention, Signal
from src.persistence.database import SQLiteDatabase


def _from_row(row: sqlite3.Row) -> Signal:
    assets = tuple(
        AssetMention.model_validate(item) for item in json.loads(row["assets_json"] or "[]")
    )
    return Signal(
        source=row["source"],
        source_type=row["source_type"],
        title=row["title"],
        url=row["url"],
        summary=row["summary"],
        published_at=datetime.fromisoformat(row["published_at"]) if row["published_at"] else None,
        collected_at=datetime.fromisoformat(row["collected_at"]),
        content_hash=row["content_hash"],
        assets=assets,
        raw=row["raw"],
    )


class SignalRepository:
    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    def record(self, signal: Signal) -> bool:
        with self.database.transaction() as connection:
            return self._insert(connection, signal)

    def record_many(self, signals: Iterable[Signal], *, refresh: bool = False) -> int:
        if refresh:
            items = list(signals)
            with self.database.transaction() as connection:
                for signal in items:
                    self._upsert(connection, signal)
            return len(items)

        inserted = 0
        with self.database.transaction() as connection:
            for signal in signals:
                inserted += int(self._insert(connection, signal))
        return inserted

    @staticmethod
    def _params(signal: Signal) -> tuple[object, ...]:
        return (
            signal.source,
            signal.source_type,
            signal.title,
            signal.url,
            signal.summary,
            signal.published_at.isoformat() if signal.published_at else None,
            signal.collected_at.isoformat(),
            signal.content_hash,
            json.dumps(
                [asset.model_dump() for asset in signal.assets],
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            signal.raw,
        )

    def _upsert(self, connection: sqlite3.Connection, signal: Signal) -> None:
        connection.execute(
            """INSERT INTO signals (
                source, source_type, title, url, summary, published_at,
                collected_at, content_hash, assets_json, raw
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source, url) DO UPDATE SET
                source_type = excluded.source_type,
                title = excluded.title,
                summary = excluded.summary,
                published_at = excluded.published_at,
                collected_at = excluded.collected_at,
                content_hash = excluded.content_hash,
                assets_json = excluded.assets_json,
                raw = excluded.raw""",
            self._params(signal),
        )

    def _insert(self, connection: sqlite3.Connection, signal: Signal) -> bool:
        cursor = connection.execute(
            """INSERT OR IGNORE INTO signals (
                source, source_type, title, url, summary, published_at,
                collected_at, content_hash, assets_json, raw
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            self._params(signal),
        )
        return bool(cursor.rowcount)

    def list(
        self,
        *,
        since: datetime | None = None,
        source: str | None = None,
        with_assets: bool = False,
        limit: int = 200,
        offset: int = 0,
    ) -> list[Signal]:
        clauses: list[str] = []
        params: list[object] = []
        if since is not None:
            clauses.append("COALESCE(published_at, collected_at) >= ?")
            params.append(since.isoformat())
        if source is not None:
            clauses.append("source = ?")
            params.append(source)
        if with_assets:
            clauses.append("assets_json != '[]'")

        query = "SELECT * FROM signals"
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += (
            " ORDER BY COALESCE(published_at, collected_at) DESC, id DESC"
            " LIMIT ? OFFSET ?"
        )
        params.extend([limit, offset])

        with self.database.connection() as connection:
            return [_from_row(row) for row in connection.execute(query, params)]

    def count(self, *, since: datetime | None = None, source: str | None = None) -> int:
        clauses: list[str] = []
        params: list[object] = []
        if since is not None:
            clauses.append("COALESCE(published_at, collected_at) >= ?")
            params.append(since.isoformat())
        if source is not None:
            clauses.append("source = ?")
            params.append(source)
        query = "SELECT COUNT(*) AS total FROM signals"
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        with self.database.connection() as connection:
            row = connection.execute(query, params).fetchone()
        return int(row["total"])

    def latest_collected_at(self) -> datetime | None:
        with self.database.connection() as connection:
            row = connection.execute(
                "SELECT MAX(collected_at) AS latest FROM signals"
            ).fetchone()
        return datetime.fromisoformat(row["latest"]) if row and row["latest"] else None
