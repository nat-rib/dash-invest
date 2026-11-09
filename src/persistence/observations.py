"""Repositório append-only de observações externas com proveniência.

Reapresentações e correções nunca sobrescrevem a linha anterior: elas geram
uma nova observação e marcam a antiga em `superseded_by`.
"""
from __future__ import annotations

import sqlite3
from datetime import date, datetime
from decimal import Decimal

from src.domain.observations import Observation, QualityStatus, decimal_text
from src.persistence.database import SQLiteDatabase


def _optional_iso(value: date | datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _from_row(row: sqlite3.Row) -> Observation:
    return Observation(
        provider=row["provider"],
        metric=row["metric"],
        instrument_id=row["instrument_id"],
        value=Decimal(row["value"]),
        currency=row["currency"],
        unit=row["unit"],
        period_start=date.fromisoformat(row["period_start"]) if row["period_start"] else None,
        period_end=date.fromisoformat(row["period_end"]) if row["period_end"] else None,
        reference_date=date.fromisoformat(row["reference_date"]),
        published_at=datetime.fromisoformat(row["published_at"]) if row["published_at"] else None,
        collected_at=datetime.fromisoformat(row["collected_at"]),
        parser_version=row["parser_version"],
        quality_status=QualityStatus(row["quality_status"]),
        source_document=row["source_document"],
        raw_payload=row["raw_payload"],
    )


class ObservationRepository:
    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    def record(self, observation: Observation) -> int:
        """Insere a observação e retorna o id.

        Identidade idêntica (mesmo fingerprint) não duplica. Quando uma nova
        publicação ocupa o mesmo slot (provedor, instrumento, métrica, período
        e data de referência), a anterior é marcada como superseded_by.
        """
        fingerprint = observation.fingerprint()
        with self.database.transaction() as connection:
            cursor = connection.execute(
                """INSERT OR IGNORE INTO observations (
                    fingerprint, provider, instrument_id, metric, value, currency, unit,
                    period_start, period_end, reference_date, published_at, collected_at,
                    parser_version, quality_status, source_document, raw_payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    fingerprint,
                    observation.provider,
                    observation.instrument_id,
                    observation.metric,
                    decimal_text(observation.value),
                    observation.currency,
                    observation.unit,
                    _optional_iso(observation.period_start),
                    _optional_iso(observation.period_end),
                    observation.reference_date.isoformat(),
                    _optional_iso(observation.published_at),
                    observation.collected_at.isoformat(),
                    observation.parser_version,
                    observation.quality_status.value,
                    observation.source_document,
                    observation.raw_payload,
                ),
            )
            row = connection.execute(
                "SELECT id FROM observations WHERE fingerprint = ?", (fingerprint,)
            ).fetchone()
            observation_id = int(row["id"])
            if cursor.rowcount:
                connection.execute(
                    """UPDATE observations SET superseded_by = ?
                       WHERE id <> ? AND superseded_by IS NULL
                         AND provider = ? AND metric = ?
                         AND instrument_id IS ?
                         AND reference_date = ?
                         AND period_start IS ?
                         AND period_end IS ?
                         AND published_at IS NOT ?""",
                    (
                        observation_id,
                        observation_id,
                        observation.provider,
                        observation.metric,
                        observation.instrument_id,
                        observation.reference_date.isoformat(),
                        _optional_iso(observation.period_start),
                        _optional_iso(observation.period_end),
                        _optional_iso(observation.published_at),
                    ),
                )
            return observation_id

    def get(self, observation_id: int) -> Observation | None:
        with self.database.connection() as connection:
            row = connection.execute(
                "SELECT * FROM observations WHERE id = ?", (observation_id,)
            ).fetchone()
            return _from_row(row) if row is not None else None

    def superseded_by(self, observation_id: int) -> int | None:
        with self.database.connection() as connection:
            row = connection.execute(
                "SELECT superseded_by FROM observations WHERE id = ?", (observation_id,)
            ).fetchone()
        if row is None or row["superseded_by"] is None:
            return None
        return int(row["superseded_by"])

    def list(
        self,
        *,
        provider: str | None = None,
        instrument_id: str | None = None,
        metric: str | None = None,
        include_superseded: bool = False,
    ) -> list[Observation]:
        clauses: list[str] = []
        params: list[object] = []
        if provider is not None:
            clauses.append("provider = ?")
            params.append(provider)
        if instrument_id is not None:
            clauses.append("instrument_id IS ?")
            params.append(instrument_id)
        if metric is not None:
            clauses.append("metric = ?")
            params.append(metric)
        if not include_superseded:
            clauses.append("superseded_by IS NULL")

        query = "SELECT * FROM observations"
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY reference_date, collected_at, id"

        with self.database.connection() as connection:
            return [_from_row(row) for row in connection.execute(query, params)]
