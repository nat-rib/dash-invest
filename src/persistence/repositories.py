"""Repositórios SQLite para cadastros, snapshots de posição e ledger append-only."""
from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from src.domain.models import Instrument, Portfolio, PortfolioPosition, Transaction
from src.persistence.database import SQLiteDatabase


def _utc_iso(value: datetime) -> str:
    """Normaliza instantes para UTC, permitindo ordenação textual correta."""
    return value.astimezone(timezone.utc).isoformat()


def _json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _instrument_from_row(row: sqlite3.Row) -> Instrument:
    return Instrument(
        id=row["id"], name=row["name"], asset_class=row["asset_class"],
        subclass=row["subclass"], currency=row["currency"], country=row["country"],
        exchange=row["exchange"], issuer_id=row["issuer_id"],
        provider_symbols=json.loads(row["provider_symbols_json"]),
        metadata=json.loads(row["metadata_json"]),
    )


def _portfolio_from_row(row: sqlite3.Row) -> Portfolio:
    return Portfolio(
        id=row["id"], name=row["name"], base_currency=row["base_currency"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )


def _position_from_row(row: sqlite3.Row) -> PortfolioPosition:
    return PortfolioPosition(
        portfolio_id=row["portfolio_id"], instrument_id=row["instrument_id"],
        institution=row["institution"], quantity=Decimal(row["quantity"]) if row["quantity"] is not None else None,
        average_cost=Decimal(row["average_cost"]) if row["average_cost"] is not None else None,
        cost_currency=row["cost_currency"], as_of=date.fromisoformat(row["as_of"]),
        metadata=json.loads(row["metadata_json"]),
    )


def _transaction_from_row(row: sqlite3.Row) -> Transaction:
    decimal_fields = ("quantity", "unit_price", "amount", "fees", "taxes")
    values = {field: Decimal(row[field]) if row[field] is not None else None for field in decimal_fields}
    return Transaction(
        id=row["id"], portfolio_id=row["portfolio_id"],
        transaction_type=row["transaction_type"],
        occurred_at=datetime.fromisoformat(row["occurred_at"]),
        institution=row["institution"], instrument_id=row["instrument_id"],
        currency=row["currency"], transfer_id=row["transfer_id"],
        external_id=row["external_id"], notes=row["notes"],
        metadata=json.loads(row["metadata_json"]), **values,
    )


class PortfolioRepository:
    def __init__(self, database: SQLiteDatabase):
        self.database = database

    def save(self, portfolio: Portfolio, connection: sqlite3.Connection | None = None) -> Portfolio:
        if connection is not None:
            self._save(connection, portfolio)
        else:
            with self.database.transaction() as tx:
                self._save(tx, portfolio)
        return portfolio

    @staticmethod
    def _save(connection: sqlite3.Connection, portfolio: Portfolio) -> None:
        connection.execute(
                """INSERT INTO portfolios (id, name, base_currency, created_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET name=excluded.name,
                       base_currency=excluded.base_currency""",
                (portfolio.id, portfolio.name, portfolio.base_currency, portfolio.created_at.isoformat()),
            )

    def get(self, portfolio_id: str) -> Portfolio | None:
        with self.database.connection() as connection:
            row = connection.execute("SELECT * FROM portfolios WHERE id = ?", (portfolio_id,)).fetchone()
        return _portfolio_from_row(row) if row else None

    def list_all(self) -> list[Portfolio]:
        with self.database.connection() as connection:
            rows = connection.execute("SELECT * FROM portfolios ORDER BY name, id").fetchall()
        return [_portfolio_from_row(row) for row in rows]


class InstrumentRepository:
    def __init__(self, database: SQLiteDatabase):
        self.database = database

    def save(self, instrument: Instrument, connection: sqlite3.Connection | None = None) -> Instrument:
        if connection is not None:
            self._save(connection, instrument)
        else:
            with self.database.transaction() as tx:
                self._save(tx, instrument)
        return instrument

    @staticmethod
    def _save(connection: sqlite3.Connection, instrument: Instrument) -> None:
        now = datetime.now(timezone.utc).isoformat()
        connection.execute(
                """INSERT INTO instruments (
                       id, name, asset_class, subclass, currency, country, exchange,
                       issuer_id, provider_symbols_json, metadata_json, created_at, updated_at
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET
                       name=excluded.name, asset_class=excluded.asset_class,
                       subclass=excluded.subclass, currency=excluded.currency,
                       country=excluded.country, exchange=excluded.exchange,
                       issuer_id=excluded.issuer_id,
                       provider_symbols_json=excluded.provider_symbols_json,
                       metadata_json=excluded.metadata_json, updated_at=excluded.updated_at""",
                (instrument.id, instrument.name, instrument.asset_class.value, instrument.subclass,
                 instrument.currency, instrument.country, instrument.exchange, instrument.issuer_id,
                 _json_dump(instrument.provider_symbols), _json_dump(instrument.metadata), now, now),
            )

    def get(self, instrument_id: str) -> Instrument | None:
        with self.database.connection() as connection:
            row = connection.execute("SELECT * FROM instruments WHERE id = ?", (instrument_id,)).fetchone()
        return _instrument_from_row(row) if row else None

    def list_all(self) -> list[Instrument]:
        with self.database.connection() as connection:
            rows = connection.execute("SELECT * FROM instruments ORDER BY name, id").fetchall()
        return [_instrument_from_row(row) for row in rows]


class PortfolioPositionRepository:
    """Persiste posições importadas/materializadas; não as trata como transações."""

    def __init__(self, database: SQLiteDatabase):
        self.database = database

    def save_snapshot(self, position: PortfolioPosition, connection: sqlite3.Connection | None = None) -> PortfolioPosition:
        if connection is not None:
            self._save_snapshot(connection, position)
        else:
            with self.database.transaction() as tx:
                self._save_snapshot(tx, position)
        return position

    @staticmethod
    def _save_snapshot(connection: sqlite3.Connection, position: PortfolioPosition) -> None:
        connection.execute(
                """INSERT INTO portfolio_positions (
                       portfolio_id, instrument_id, institution, quantity,
                       average_cost, cost_currency, as_of, metadata_json
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(portfolio_id, instrument_id, institution, as_of)
                   DO UPDATE SET quantity=excluded.quantity,
                       average_cost=excluded.average_cost, cost_currency=excluded.cost_currency,
                       metadata_json=excluded.metadata_json""",
                (position.portfolio_id, position.instrument_id, position.institution,
                 str(position.quantity) if position.quantity is not None else None,
                 str(position.average_cost) if position.average_cost is not None else None,
                 position.cost_currency, position.as_of.isoformat(), _json_dump(position.metadata)),
            )

    def list_snapshots(self, portfolio_id: str, as_of: date | None = None) -> list[PortfolioPosition]:
        query = "SELECT * FROM portfolio_positions WHERE portfolio_id = ?"
        parameters: list[Any] = [portfolio_id]
        if as_of is not None:
            query += " AND as_of = ?"
            parameters.append(as_of.isoformat())
        query += " ORDER BY as_of DESC, institution, instrument_id"
        with self.database.connection() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [_position_from_row(row) for row in rows]


class TransactionRepository:
    """Ledger append-only: não oferece update/delete para preservar auditoria."""

    def __init__(self, database: SQLiteDatabase):
        self.database = database

    def append(self, transaction: Transaction) -> Transaction:
        with self.database.transaction() as connection:
            connection.execute(
                """INSERT INTO transactions (
                       id, portfolio_id, transaction_type, occurred_at, institution,
                       instrument_id, quantity, unit_price, amount, currency, fees, taxes,
                       transfer_id, external_id, notes, metadata_json
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (transaction.id, transaction.portfolio_id, transaction.transaction_type.value,
                 _utc_iso(transaction.occurred_at), transaction.institution, transaction.instrument_id,
                 str(transaction.quantity) if transaction.quantity is not None else None,
                 str(transaction.unit_price) if transaction.unit_price is not None else None,
                 str(transaction.amount) if transaction.amount is not None else None,
                 transaction.currency, str(transaction.fees), str(transaction.taxes),
                 transaction.transfer_id, transaction.external_id, transaction.notes,
                 _json_dump(transaction.metadata)),
            )
        return transaction

    def get(self, transaction_id: str) -> Transaction | None:
        with self.database.connection() as connection:
            row = connection.execute("SELECT * FROM transactions WHERE id = ?", (transaction_id,)).fetchone()
        return _transaction_from_row(row) if row else None

    def list_for_portfolio(
        self, portfolio_id: str, *, instrument_id: str | None = None,
        start: datetime | None = None, end: datetime | None = None,
    ) -> list[Transaction]:
        query = "SELECT * FROM transactions WHERE portfolio_id = ?"
        parameters: list[Any] = [portfolio_id]
        if instrument_id is not None:
            query += " AND instrument_id = ?"
            parameters.append(instrument_id)
        if start is not None:
            query += " AND occurred_at >= ?"
            parameters.append(_utc_iso(start))
        if end is not None:
            query += " AND occurred_at <= ?"
            parameters.append(_utc_iso(end))
        query += " ORDER BY occurred_at, id"
        with self.database.connection() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [_transaction_from_row(row) for row in rows]
