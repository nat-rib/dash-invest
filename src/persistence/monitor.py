"""Persistência de snapshots do ranking e alertas enviados."""
from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime

from src.persistence.database import SQLiteDatabase


@dataclass(frozen=True)
class CandidateSnapshot:
    snapshot_date: date
    asset_key: str
    name: str
    asset_class: str
    score: float
    confidence: float
    components: dict[str, float | None]
    reasons: tuple[str, ...]
    sources: tuple[str, ...]
    signal_count: int
    reference_price: float | None = None
    reference_price_date: date | None = None
    price_provider: str | None = None
    price_instrument: str | None = None
    created_at: datetime | None = None


@dataclass(frozen=True)
class AlertRecord:
    asset_key: str
    name: str
    score: float
    channel: str
    message: str
    sent_at: datetime


def _snapshot_from_row(row: sqlite3.Row) -> CandidateSnapshot:
    return CandidateSnapshot(
        snapshot_date=date.fromisoformat(row["snapshot_date"]),
        asset_key=row["asset_key"],
        name=row["name"],
        asset_class=row["asset_class"],
        score=float(row["score"]),
        confidence=float(row["confidence"]),
        components=json.loads(row["components_json"] or "{}"),
        reasons=tuple(json.loads(row["reasons_json"] or "[]")),
        sources=tuple(json.loads(row["sources_json"] or "[]")),
        signal_count=int(row["signal_count"]),
        reference_price=float(row["reference_price"]) if row["reference_price"] is not None else None,
        reference_price_date=date.fromisoformat(row["reference_price_date"])
        if row["reference_price_date"]
        else None,
        price_provider=row["price_provider"],
        price_instrument=row["price_instrument"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )


class SnapshotRepository:
    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    def record_many(
        self, snapshots: Iterable[CandidateSnapshot], *, now: datetime
    ) -> int:
        items = list(snapshots)
        with self.database.transaction() as connection:
            for snapshot in items:
                connection.execute(
                    """INSERT INTO candidate_snapshots (
                        snapshot_date, asset_key, name, asset_class, score, confidence,
                        components_json, reasons_json, sources_json, signal_count,
                        reference_price, reference_price_date, price_provider,
                        price_instrument, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(snapshot_date, asset_key) DO UPDATE SET
                        name = excluded.name,
                        asset_class = excluded.asset_class,
                        score = excluded.score,
                        confidence = excluded.confidence,
                        components_json = excluded.components_json,
                        reasons_json = excluded.reasons_json,
                        sources_json = excluded.sources_json,
                        signal_count = excluded.signal_count,
                        reference_price = COALESCE(excluded.reference_price, candidate_snapshots.reference_price),
                        reference_price_date = COALESCE(excluded.reference_price_date, candidate_snapshots.reference_price_date),
                        price_provider = COALESCE(excluded.price_provider, candidate_snapshots.price_provider),
                        price_instrument = COALESCE(excluded.price_instrument, candidate_snapshots.price_instrument),
                        created_at = excluded.created_at""",
                    (
                        snapshot.snapshot_date.isoformat(),
                        snapshot.asset_key,
                        snapshot.name,
                        snapshot.asset_class,
                        snapshot.score,
                        snapshot.confidence,
                        json.dumps(snapshot.components, ensure_ascii=False, sort_keys=True),
                        json.dumps(list(snapshot.reasons), ensure_ascii=False),
                        json.dumps(list(snapshot.sources), ensure_ascii=False),
                        snapshot.signal_count,
                        snapshot.reference_price,
                        snapshot.reference_price_date.isoformat()
                        if snapshot.reference_price_date
                        else None,
                        snapshot.price_provider,
                        snapshot.price_instrument,
                        (snapshot.created_at or now).isoformat(),
                    ),
                )
        return len(items)

    def list(
        self, *, since: date | None = None, limit: int = 5000
    ) -> list[CandidateSnapshot]:
        query = "SELECT * FROM candidate_snapshots"
        params: list[object] = []
        if since is not None:
            query += " WHERE snapshot_date >= ?"
            params.append(since.isoformat())
        query += " ORDER BY snapshot_date DESC, score DESC LIMIT ?"
        params.append(limit)
        with self.database.connection() as connection:
            return [_snapshot_from_row(row) for row in connection.execute(query, params)]

    def count(self) -> int:
        with self.database.connection() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS total FROM candidate_snapshots"
            ).fetchone()
        return int(row["total"])


class AlertRepository:
    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    def record(self, alert: AlertRecord) -> int:
        with self.database.transaction() as connection:
            cursor = connection.execute(
                """INSERT INTO alerts (asset_key, name, score, channel, message, sent_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    alert.asset_key,
                    alert.name,
                    alert.score,
                    alert.channel,
                    alert.message,
                    alert.sent_at.isoformat(),
                ),
            )
            return int(cursor.lastrowid)

    def last_sent(self, asset_key: str) -> datetime | None:
        with self.database.connection() as connection:
            row = connection.execute(
                "SELECT MAX(sent_at) AS latest FROM alerts WHERE asset_key = ?",
                (asset_key,),
            ).fetchone()
        return datetime.fromisoformat(row["latest"]) if row and row["latest"] else None

    def list(self, *, limit: int = 20) -> list[AlertRecord]:
        with self.database.connection() as connection:
            rows = connection.execute(
                "SELECT * FROM alerts ORDER BY sent_at DESC, id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            AlertRecord(
                asset_key=row["asset_key"],
                name=row["name"],
                score=float(row["score"]),
                channel=row["channel"],
                message=row["message"],
                sent_at=datetime.fromisoformat(row["sent_at"]),
            )
            for row in rows
        ]

    def count(self) -> int:
        with self.database.connection() as connection:
            row = connection.execute("SELECT COUNT(*) AS total FROM alerts").fetchone()
        return int(row["total"])
