"""Histórico local de snapshots. Não há banco ou sincronização remota."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sqlite3

import pandas as pd

from src.portfolio import consolidated_total, positions_frame
from src.schemas import PortfolioSnapshot


DEFAULT_DB = Path("data/portfolio_history.db")


def _connection(path: Path = DEFAULT_DB) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY,
            captured_at TEXT NOT NULL,
            source TEXT NOT NULL,
            total_brl REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS position_snapshots (
            snapshot_id INTEGER NOT NULL REFERENCES snapshots(id) ON DELETE CASCADE,
            position_key TEXT NOT NULL,
            institution TEXT NOT NULL,
            name TEXT NOT NULL,
            asset_class TEXT NOT NULL,
            currency TEXT NOT NULL,
            current_price REAL,
            current_value REAL,
            value_brl REAL
        );
    """)
    return connection


def record_snapshot(snapshot: PortfolioSnapshot, source: str, path: Path = DEFAULT_DB) -> int:
    """Registra valores conhecidos em um momento no banco SQLite local."""
    frame = positions_frame(snapshot)
    captured_at = datetime.now(timezone.utc).isoformat()
    with _connection(path) as connection:
        cursor = connection.execute(
            "INSERT INTO snapshots (captured_at, source, total_brl) VALUES (?, ?, ?)",
            (captured_at, source, consolidated_total(frame)),
        )
        snapshot_id = int(cursor.lastrowid)
        rows = []
        for _, row in frame.iterrows():
            position_key = f"{row['Instituição']}|{row['Ticker'] or row['Nome']}|{row['Moeda']}"
            rows.append((
                snapshot_id, position_key, row["Instituição"], row["Nome"], row["Classe"], row["Moeda"],
                row["Preço atual"], row["Valor atual"], row["Valor consolidado BRL"],
            ))
        connection.executemany("""
            INSERT INTO position_snapshots
            (snapshot_id, position_key, institution, name, asset_class, currency, current_price, current_value, value_brl)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, rows)
    return snapshot_id


def portfolio_history(path: Path = DEFAULT_DB) -> pd.DataFrame:
    with _connection(path) as connection:
        return pd.read_sql_query(
            "SELECT captured_at AS 'Data', total_brl AS 'Patrimônio BRL', source AS 'Origem' FROM snapshots ORDER BY id",
            connection,
            parse_dates=["Data"],
        )


def position_history(path: Path = DEFAULT_DB) -> pd.DataFrame:
    with _connection(path) as connection:
        return pd.read_sql_query("""
            SELECT s.captured_at AS 'Data', p.position_key AS 'Posição', p.name AS 'Ativo',
                   p.institution AS 'Instituição', p.currency AS 'Moeda', p.current_price AS 'Preço atual',
                   p.current_value AS 'Valor atual', p.value_brl AS 'Valor BRL'
            FROM position_snapshots p JOIN snapshots s ON s.id = p.snapshot_id
            ORDER BY s.id
        """, connection, parse_dates=["Data"])
