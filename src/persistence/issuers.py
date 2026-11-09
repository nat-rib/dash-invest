"""Repositório de emissores (companhias) com atualização idempotente."""
from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from datetime import datetime

from src.domain.issuers import Issuer
from src.persistence.database import SQLiteDatabase


def _from_row(row: sqlite3.Row) -> Issuer:
    return Issuer(
        cnpj=row["cnpj"],
        name=row["name"],
        cvm_code=row["cvm_code"],
        source=row["source"],
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )


class IssuerRepository:
    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    def upsert(self, issuer: Issuer) -> bool:
        """Cria ou atualiza o emissor; retorna True quando é novo."""
        with self.database.transaction() as connection:
            return self._upsert(connection, issuer)

    def upsert_many(self, issuers: Iterable[Issuer]) -> int:
        """Atualiza um lote em uma transação; retorna quantos emissores são novos."""
        inserted = 0
        with self.database.transaction() as connection:
            for issuer in issuers:
                inserted += int(self._upsert(connection, issuer))
        return inserted

    def _upsert(self, connection: sqlite3.Connection, issuer: Issuer) -> bool:
        cursor = connection.execute(
            """INSERT OR IGNORE INTO issuers (cnpj, name, cvm_code, source, updated_at)
               VALUES (?, ?, ?, ?, ?)""",
            (
                issuer.cnpj,
                issuer.name,
                issuer.cvm_code,
                issuer.source,
                issuer.updated_at.isoformat(),
            ),
        )
        connection.execute(
            """UPDATE issuers SET name = ?, cvm_code = ?, source = ?, updated_at = ?
               WHERE cnpj = ?""",
            (
                issuer.name,
                issuer.cvm_code,
                issuer.source,
                issuer.updated_at.isoformat(),
                issuer.cnpj,
            ),
        )
        return bool(cursor.rowcount)

    def get(self, cnpj: str) -> Issuer | None:
        digits = "".join(char for char in cnpj if char.isdigit())
        with self.database.connection() as connection:
            row = connection.execute(
                "SELECT * FROM issuers WHERE cnpj = ?", (digits,)
            ).fetchone()
        return _from_row(row) if row is not None else None

    def list(
        self,
        *,
        query: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Issuer]:
        clauses: list[str] = []
        params: list[object] = []
        if query:
            clauses.append("(name LIKE ? COLLATE NOCASE OR cnpj LIKE ?)")
            pattern = f"%{query.strip()}%"
            params.extend([pattern, pattern])

        sql = "SELECT * FROM issuers"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY name COLLATE NOCASE, cnpj"
        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        elif offset:
            sql += " LIMIT -1 OFFSET ?"
            params.append(offset)

        with self.database.connection() as connection:
            return [_from_row(row) for row in connection.execute(sql, params)]

    def count(self, *, query: str | None = None) -> int:
        clauses: list[str] = []
        params: list[object] = []
        if query:
            clauses.append("(name LIKE ? COLLATE NOCASE OR cnpj LIKE ?)")
            pattern = f"%{query.strip()}%"
            params.extend([pattern, pattern])

        sql = "SELECT COUNT(*) AS total FROM issuers"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        with self.database.connection() as connection:
            row = connection.execute(sql, params).fetchone()
        return int(row["total"])
