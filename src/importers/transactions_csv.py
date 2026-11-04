"""Importação de CSV para o formato canônico de transações do Dash-Invest.

O CSV canônico é deliberadamente independente de corretora. Adaptadores específicos
podem converter extratos de instituições para este contrato antes da persistência.
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from io import StringIO
from uuid import NAMESPACE_URL, uuid5

from src.domain.models import Transaction, TransactionType
from src.persistence.repositories import TransactionRepository


REQUIRED_COLUMNS = {"external_id", "occurred_at", "transaction_type", "institution", "currency"}


class TransactionCsvImportError(ValueError):
    """CSV inválido; nenhum evento do arquivo foi persistido."""


@dataclass(frozen=True)
class TransactionCsvImportResult:
    parsed: int
    inserted: int
    skipped_duplicates: int


def _optional_decimal(value: str | None, *, field: str, row_number: int) -> Decimal | None:
    if value is None or not value.strip():
        return None
    try:
        number = Decimal(value.strip().replace(",", "."))
    except InvalidOperation:
        raise TransactionCsvImportError(f"Linha {row_number}: {field} não é um decimal válido.") from None
    if not number.is_finite():
        raise TransactionCsvImportError(f"Linha {row_number}: {field} deve ser finito.")
    return number


def _optional_text(row: dict[str, str | None], key: str) -> str | None:
    value = row.get(key)
    return value.strip() if value and value.strip() else None


class CanonicalTransactionCsvImporter:
    """Valida o arquivo inteiro e grava o lote em uma única transação SQLite."""

    def __init__(self, repository: TransactionRepository):
        self.repository = repository

    def import_text(self, content: str, *, portfolio_id: str) -> TransactionCsvImportResult:
        reader = csv.DictReader(StringIO(content.lstrip("\ufeff")))
        columns = set(reader.fieldnames or [])
        missing = REQUIRED_COLUMNS - columns
        if missing:
            raise TransactionCsvImportError(
                "Colunas obrigatórias ausentes: " + ", ".join(sorted(missing))
            )

        transactions: list[Transaction] = []
        seen_external_ids: set[tuple[str, str]] = set()
        for row_number, row in enumerate(reader, start=2):
            try:
                external_id = (row.get("external_id") or "").strip()
                institution = (row.get("institution") or "").strip()
                if not external_id or not institution:
                    raise TransactionCsvImportError(
                        f"Linha {row_number}: external_id e institution são obrigatórios."
                    )
                identity = (institution, external_id)
                if identity in seen_external_ids:
                    raise TransactionCsvImportError(
                        f"Linha {row_number}: external_id duplicado no próprio arquivo."
                    )
                seen_external_ids.add(identity)

                occurred_raw = (row.get("occurred_at") or "").strip()
                try:
                    occurred_at = datetime.fromisoformat(occurred_raw.replace("Z", "+00:00"))
                except ValueError:
                    raise TransactionCsvImportError(
                        f"Linha {row_number}: occurred_at deve ser ISO-8601 com timezone."
                    ) from None
                if occurred_at.tzinfo is None or occurred_at.utcoffset() is None:
                    raise TransactionCsvImportError(
                        f"Linha {row_number}: occurred_at precisa incluir timezone."
                    )

                raw_type = (row.get("transaction_type") or "").strip().upper()
                try:
                    transaction_type = TransactionType(raw_type)
                except ValueError:
                    raise TransactionCsvImportError(
                        f"Linha {row_number}: transaction_type desconhecido: {raw_type!r}."
                    ) from None

                metadata_raw = _optional_text(row, "metadata_json")
                metadata = json.loads(metadata_raw) if metadata_raw else {}
                if not isinstance(metadata, dict):
                    raise TransactionCsvImportError(
                        f"Linha {row_number}: metadata_json precisa ser um objeto JSON."
                    )

                sequence_raw = _optional_text(row, "sequence")
                sequence = int(sequence_raw) if sequence_raw else 0
                transaction = Transaction(
                    id=str(uuid5(
                        NAMESPACE_URL,
                        f"dash-invest:csv:{portfolio_id}:{institution}:{external_id}",
                    )),
                    portfolio_id=portfolio_id,
                    transaction_type=transaction_type,
                    occurred_at=occurred_at.astimezone(timezone.utc),
                    sequence=sequence,
                    institution=institution,
                    instrument_id=_optional_text(row, "instrument_id"),
                    quantity=_optional_decimal(row.get("quantity"), field="quantity", row_number=row_number),
                    unit_price=_optional_decimal(row.get("unit_price"), field="unit_price", row_number=row_number),
                    amount=_optional_decimal(row.get("amount"), field="amount", row_number=row_number),
                    currency=(row.get("currency") or "").strip().upper(),
                    fees=_optional_decimal(row.get("fees"), field="fees", row_number=row_number) or Decimal("0"),
                    taxes=_optional_decimal(row.get("taxes"), field="taxes", row_number=row_number) or Decimal("0"),
                    transfer_id=_optional_text(row, "transfer_id"),
                    external_id=external_id,
                    notes=_optional_text(row, "notes"),
                    metadata=metadata,
                )
                transactions.append(transaction)
            except TransactionCsvImportError:
                raise
            except (ValueError, TypeError, json.JSONDecodeError) as exc:
                raise TransactionCsvImportError(f"Linha {row_number}: {exc}") from exc

        if not transactions:
            raise TransactionCsvImportError("O CSV não contém transações.")
        inserted, skipped = self.repository.append_many(transactions)
        return TransactionCsvImportResult(
            parsed=len(transactions), inserted=inserted, skipped_duplicates=skipped
        )
