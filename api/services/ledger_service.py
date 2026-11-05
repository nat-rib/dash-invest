"""Camada de serviços do Ledger: única fronteira entre rotas HTTP e o domínio.

Todos os caminhos reutilizam módulos existentes (src.domain, src.persistence,
src.importers); nenhuma regra financeira é duplicada aqui.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from src.domain.models import AssetClass, Instrument
from src.domain.reconciliation import reconcile_transfers
from src.importers.broker_csv import BrokerCsvMapping, adapt_broker_csv, to_canonical_csv
from src.importers.transactions_csv import CanonicalTransactionCsvImporter
from src.importer import load_snapshot
from src.persistence.repositories import (
    InstrumentRepository, PortfolioPositionRepository, PortfolioRepository,
    TransactionRepository, TransferLinkRepository,
)
from src.persistence.snapshot_import import PortfolioSnapshotImporter

from api.schemas.ledger import (
    CsvImportResultOut, CsvPreviewOut, InstrumentOut, LedgerTransactionOut,
    PreviewTransactionOut, SnapshotImportResultOut, SnapshotPositionOut,
    SnapshotPreviewOut, SuggestedPairOut, TransferEventOut, TransferLinkOut,
    TransferSuggestionsOut,
)

from api.config import default_portfolio_id, portfolio_path


class LedgerValidationError(ValueError):
    """Erro de domínio/validação que vira HTTP 4xx com mensagem acionável."""


def _instrument_label(instrument: Instrument | None) -> str | None:
    if instrument is None:
        return None
    ticker = next(iter(instrument.provider_symbols.values()), None)
    return f"{instrument.name}" + (f" · {ticker}" if ticker else "")


def _transaction_out(
    transaction, *, instrument_label: str | None, transfer_linked: bool,
) -> LedgerTransactionOut:
    return LedgerTransactionOut(
        id=transaction.id,
        portfolio_id=transaction.portfolio_id,
        transaction_type=transaction.transaction_type.value,
        occurred_at=transaction.occurred_at.isoformat(),
        sequence=transaction.sequence,
        institution=transaction.institution,
        instrument_id=transaction.instrument_id,
        instrument_label=instrument_label,
        quantity=str(transaction.quantity) if transaction.quantity is not None else None,
        unit_price=str(transaction.unit_price) if transaction.unit_price is not None else None,
        amount=str(transaction.amount) if transaction.amount is not None else None,
        currency=transaction.currency,
        fees=str(transaction.fees),
        taxes=str(transaction.taxes),
        transfer_id=transaction.transfer_id,
        transfer_linked=transfer_linked,
        external_id=transaction.external_id,
        notes=transaction.notes,
        metadata=transaction.metadata,
    )


def _event_out(transaction) -> TransferEventOut:
    return TransferEventOut(
        id=transaction.id,
        transaction_type=transaction.transaction_type.value,
        occurred_at=transaction.occurred_at.isoformat(),
        institution=transaction.institution,
        amount=str(transaction.amount) if transaction.amount is not None else None,
        quantity=str(transaction.quantity) if transaction.quantity is not None else None,
        currency=transaction.currency,
        instrument_id=transaction.instrument_id,
        external_id=transaction.external_id,
    )


def _require_portfolio(
    repositories: PortfolioRepository, portfolio_id: str,
) -> None:
    if repositories.get(portfolio_id) is None:
        raise LedgerValidationError(
            "A carteira SQLite ainda não existe; migre o snapshot JSON antes desta operação."
        )


# ----------------------------------------------------------------- transações

def list_transactions(
    transactions: TransactionRepository,
    instruments: InstrumentRepository,
    transfer_links: TransferLinkRepository,
    *, portfolio_id: str,
    start: datetime | None = None, end: datetime | None = None,
    institution: str | None = None, transaction_type: str | None = None,
    instrument_id: str | None = None,
    limit: int, offset: int,
) -> tuple[list[LedgerTransactionOut], int]:
    items, total = transactions.search(
        portfolio_id,
        instrument_id=instrument_id, institution=institution,
        transaction_type=transaction_type, start=start, end=end,
        limit=limit, offset=offset,
    )
    catalog = {item.id: item for item in instruments.list_all()}
    links = transfer_links.list_for_portfolio(portfolio_id)
    linked = {
        link.transfer_out_id for link in links
    } | {link.transfer_in_id for link in links}
    return (
        [
            _transaction_out(
                item,
                instrument_label=_instrument_label(catalog.get(item.instrument_id)) if item.instrument_id else None,
                transfer_linked=item.id in linked,
            )
            for item in items
        ],
        total,
    )


def list_instruments(instruments: InstrumentRepository, *, query: str | None = None) -> list[InstrumentOut]:
    result = instruments.list_all()
    if query:
        needle = query.strip().casefold()
        result = [
            item for item in result
            if needle in item.name.casefold()
            or any(needle in value.casefold() for value in item.provider_symbols.values())
        ]
    return [InstrumentOut(**item.model_dump(mode="json")) for item in result]


def create_instrument(instruments: InstrumentRepository, *, data) -> InstrumentOut:
    search_list = instruments.list_all()
    duplicate = any(
        item.currency == data.currency.upper()
        and item.asset_class.value == data.asset_class.lower()
        and (item.exchange or "").casefold() == (data.exchange or "").strip().casefold()
        and data.ticker.strip().casefold() in {
            value.casefold() for value in item.provider_symbols.values()
        }
        for item in search_list
    )
    if duplicate:
        raise LedgerValidationError("Já existe um instrumento com esse ticker em algum provedor.")
    instrument = Instrument(
        name=data.name.strip(),
        asset_class=AssetClass(data.asset_class.lower()),
        currency=data.currency.upper(),
        exchange=(data.exchange or "").strip() or None,
        provider_symbols={"broker_ticker": data.ticker.strip()},
    )
    saved = instruments.save(instrument)
    return InstrumentOut(**saved.model_dump(mode="json"))


# ------------------------------------------------------------------- snapshot

def snapshot_preview(*, portfolio_id: str | None = None, path: Path | None = None) -> SnapshotPreviewOut:
    file_path = path or portfolio_path()
    if not file_path.exists():
        raise LedgerValidationError(f"Arquivo legado não encontrado: {file_path}.")
    snapshot = load_snapshot(file_path)
    return SnapshotPreviewOut(
        portfolio_id=portfolio_id or default_portfolio_id(),
        snapshot_date=snapshot.snapshot_date.isoformat(),
        currency=snapshot.currency,
        positions=[
            SnapshotPositionOut(
                institution=position.institution,
                asset_class=position.asset_class,
                ticker=position.ticker,
                name=position.name,
                quantity=str(position.quantity) if position.quantity is not None else None,
                currency=position.currency,
            )
            for position in snapshot.positions
        ],
    )


def snapshot_import(
    importer: PortfolioSnapshotImporter, *,
    portfolio_id: str | None = None, path: Path | None = None,
) -> SnapshotImportResultOut:
    file_path = path or portfolio_path()
    if not file_path.exists():
        raise LedgerValidationError(f"Arquivo legado não encontrado: {file_path}.")
    snapshot = load_snapshot(file_path)
    result = importer.import_snapshot(
        snapshot, portfolio_id=portfolio_id or default_portfolio_id(),
    )
    return SnapshotImportResultOut(
        portfolio_id=result.portfolio_id,
        instruments_saved=result.instruments_saved,
        positions_saved=result.positions_saved,
        transactions_created=result.transactions_created,
        message=(
            "Migração concluída; o JSON original foi preservado. "
            "Nenhuma transação foi criada e a migração pode ser repetida com segurança."
        ),
    )


# ------------------------------------------------------------------------ CSV

def _mapping_from_payload(payload: dict[str, Any]) -> BrokerCsvMapping:
    return BrokerCsvMapping(
        institution=str(payload.get("institution", "")).strip(),
        currency=str(payload.get("currency", "BRL")).upper(),
        columns=dict(payload.get("columns") or {}),
        instrument_map=dict(payload.get("instrument_map") or {}),
        delimiter={
            "TAB": "\t", "\\t": "\t",
        }.get(str(payload.get("delimiter") or ","), str(payload.get("delimiter") or ",")),
        decimal_locale=payload.get("decimal_locale") or "pt_BR",
        date_format=payload.get("date_format") or "%d/%m/%Y",
        timezone_name=payload.get("timezone_name") or "America/Sao_Paulo",
    )


def csv_preview(
    importer: CanonicalTransactionCsvImporter, *, content: str,
    portfolio_id: str, payload: dict[str, Any],
) -> CsvPreviewOut:
    mapping = _mapping_from_payload(payload)
    canonical = to_canonical_csv(content, mapping=mapping)
    parsed = importer.parse_text(canonical, portfolio_id=portfolio_id)
    return CsvPreviewOut(
        parsed=len(parsed),
        transactions=[
            PreviewTransactionOut(
                row_number=row_number,
                external_id=item.external_id or "",
                occurred_at=item.occurred_at.isoformat(),
                transaction_type=item.transaction_type.value,
                institution=item.institution,
                currency=item.currency,
                instrument_id=item.instrument_id,
                quantity=str(item.quantity) if item.quantity is not None else None,
                unit_price=str(item.unit_price) if item.unit_price is not None else None,
                amount=str(item.amount) if item.amount is not None else None,
                fees=str(item.fees),
                taxes=str(item.taxes),
            )
            for row_number, item in enumerate(parsed, start=2)
        ],
    )


def csv_import(
    importer: CanonicalTransactionCsvImporter, *, content: str,
    portfolio_id: str, payload: dict[str, Any],
) -> CsvImportResultOut:
    mapping = _mapping_from_payload(payload)
    canonical = to_canonical_csv(content, mapping=mapping)
    result = importer.import_text(canonical, portfolio_id=portfolio_id)
    return CsvImportResultOut(
        parsed=result.parsed,
        inserted=result.inserted,
        skipped_duplicates=result.skipped_duplicates,
        message=f"Importação concluída: {result.inserted} novas operações; "
                f"{result.skipped_duplicates} duplicadas ignoradas.",
    )


# ------------------------------------------------------------- transferências

def transfer_suggestions(
    transactions: TransactionRepository,
    transfer_links: TransferLinkRepository, *,
    portfolio_id: str,
    date_window_days: int = 3,
    amount_tolerance: float = 0.01,
    quantity_tolerance: float = 0.0,
) -> TransferSuggestionsOut:
    from decimal import Decimal

    events = transactions.list_for_portfolio(portfolio_id)
    links = transfer_links.list_for_portfolio(portfolio_id)
    linked_ids = {item.transfer_out_id for item in links} | {item.transfer_in_id for item in links}
    pending = [event for event in events if event.id not in linked_ids]
    result = reconcile_transfers(
        pending,
        date_window_days=date_window_days,
        amount_tolerance=Decimal(str(amount_tolerance)),
        quantity_tolerance=Decimal(str(quantity_tolerance)),
    )
    by_id = {event.id: event for event in pending}
    return TransferSuggestionsOut(
        suggested_pairs=[
            SuggestedPairOut(
                transfer_out=_event_out(by_id[pair.transfer_out_id]),
                transfer_in=_event_out(by_id[pair.transfer_in_id]),
                date_delta_seconds=int(pair.date_delta.total_seconds()),
                amount_delta=str(pair.amount_delta),
            )
            for pair in result.suggested_pairs
        ],
        ambiguous_transaction_ids=list(result.ambiguous_transaction_ids),
        unmatched_transaction_ids=list(result.unmatched_transaction_ids),
        incomplete_transfer_ids=list(result.incomplete_transfer_ids),
        invalid_transfer_ids=list(result.invalid_transfer_ids),
        pending_out_events=[
            _event_out(event) for event in pending
            if event.transaction_type.value == "TRANSFER_OUT"
        ],
        pending_in_events=[
            _event_out(event) for event in pending
            if event.transaction_type.value == "TRANSFER_IN"
        ],
        confirmed_links=[
            TransferLinkOut(
                transfer_out_id=link.transfer_out_id,
                transfer_in_id=link.transfer_in_id,
                portfolio_id=link.portfolio_id,
                linked_at=link.linked_at.isoformat(),
                confirmation_source=link.confirmation_source,
            )
            for link in links
        ],
    )


def confirm_transfer(
    transfer_links: TransferLinkRepository, *,
    transfer_out_id: str, transfer_in_id: str, confirmation_source: str,
) -> dict[str, str]:
    link = transfer_links.confirm(
        transfer_out_id, transfer_in_id, confirmation_source=confirmation_source,
    )
    return {
        "transfer_out_id": link.transfer_out_id,
        "transfer_in_id": link.transfer_in_id,
        "portfolio_id": link.portfolio_id,
        "linked_at": link.linked_at.isoformat(),
        "confirmation_source": link.confirmation_source,
    }
