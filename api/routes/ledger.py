"""Rotas do domínio Ledger (Fase 1 do roadmap de migração)."""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile

from src.importers.transactions_csv import TransactionCsvImportError

from api.config import default_portfolio_id, portfolio_path
from api.dependencies import get_repositories
from api.schemas.ledger import (
    CsvImportResultOut, CsvPreviewOut, InstrumentCreate, InstrumentOut,
    LedgerPageOut, LedgerStateOut, MigrationOut, PageMeta,
    PortfolioOut, SnapshotImportResultOut, SnapshotPreviewOut, TransferConfirmIn,
    TransferLinkOut, TransferSuggestionsOut,
)
from api.services import ledger_service
from api.services.ledger_service import LedgerValidationError

router = APIRouter(prefix="/api/ledger", tags=["ledger"])

Repositories = Annotated[object, Depends(get_repositories)]

CSV_IMPORT_ERROR_STATUS = 422


def _bad_request(message: str, status_code: int = 400) -> HTTPException:
    return HTTPException(status_code=status_code, detail=message)


# ---------------------------------------------------------------- transações

@router.get("/transactions", response_model=LedgerPageOut)
def list_transactions(
    repositories: Repositories,
    portfolio_id: str = Query(default=""),  # noqa: A002 - pluralizar nome do domínio
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    start: str | None = Query(default=None, description="Data/instante ISO; naive ou date assume UTC"),
    end: str | None = Query(default=None),
    institution: str | None = None,
    transaction_type: str | None = Query(default=None, alias="type"),
    instrument_id: str | None = None,
) -> LedgerPageOut:
    pid = portfolio_id or default_portfolio_id()
    transactions, total = ledger_service.list_transactions(
        repositories.transactions,
        repositories.instruments,
        repositories.transfer_links,
        portfolio_id=pid,
        start=_instant(start), end=_instant(end),
        institution=institution, transaction_type=transaction_type,
        instrument_id=instrument_id,
        limit=limit, offset=offset,
    )
    return LedgerPageOut(
        meta=PageMeta(limit=limit, offset=offset, total=total),
        items=transactions,
    )


def _instant(value: str | None) -> datetime | None:
    if value is None or not value.strip():
        return None
    raw = value.strip().replace("Z", "+00:00")
    try:
        moment = datetime.fromisoformat(raw)
    except ValueError:
        try:
            parsed_date = date.fromisoformat(raw)
        except ValueError:
            raise _bad_request(f"Data inválida: {value!r}; informe ISO-8601.") from None
        moment = datetime.combine(parsed_date, datetime.min.time())
    if moment.tzinfo is None or moment.utcoffset() is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment


# --------------------------------------------------------------- instrumentos

@router.get("/instruments", response_model=list[InstrumentOut])
def list_instruments(repositories: Repositories, q: str | None = None) -> list[InstrumentOut]:
    return ledger_service.list_instruments(repositories.instruments, query=q)


@router.post("/instruments", response_model=InstrumentOut, status_code=201)
def create_instrument(repositories: Repositories, body: InstrumentCreate) -> InstrumentOut:
    try:
        return ledger_service.create_instrument(repositories.instruments, data=body)
    except LedgerValidationError as error:
        raise _bad_request(str(error), status_code=409) from error


# ------------------------------------------------------------------- snapshot

@router.post("/snapshot/preview", response_model=SnapshotPreviewOut)
def preview_snapshot(
    repositories: Repositories,
    portfolio_id: str = Query(default=""),  # noqa: A002
    path: str | None = Query(default=None, description="Sobrescreve PORTFOLIO_PATH (tests/autoload)"),
) -> SnapshotPreviewOut:
    try:
        return ledger_service.snapshot_preview(
            portfolio_id=portfolio_id or None,
            path=Path(path) if path else None,
        )
    except LedgerValidationError as error:
        raise _bad_request(str(error), status_code=404) from error
    except (ValueError, OSError) as error:
        raise _bad_request(f"Não foi possível validar o snapshot: {error}") from error


@router.post("/snapshot/import", response_model=SnapshotImportResultOut)
def import_snapshot(
    repositories: Repositories,
    portfolio_id: str = Query(default=""),  # noqa: A002
    path: str | None = Query(default=None),
) -> SnapshotImportResultOut:
    try:
        return ledger_service.snapshot_import(
            repositories.snapshot_importer,
            portfolio_id=portfolio_id or None,
            path=Path(path) if path else None,
        )
    except LedgerValidationError as error:
        raise _bad_request(str(error), status_code=404) from error
    except (ValueError, OSError) as error:
        raise _bad_request(f"Não foi possível migrar o snapshot: {error}") from error


# ------------------------------------------------------------------------ CSV

def _csv_request(repositories: Repositories, portfolio_id: str) -> str:
    pid = portfolio_id or default_portfolio_id()
    if repositories.portfolios.get(pid) is None:
        raise _bad_request(
            "A carteira SQLite ainda não existe; migre o snapshot JSON antes de importar extratos.",
        )
    return pid


@router.post("/csv/preview", response_model=CsvPreviewOut)
def preview_csv(
    repositories: Repositories,
    file: Annotated[UploadFile, File()],
    mapping: Annotated[str, Form(description="JSON com institution, currency, delimiter, columns, instrument_map, decimal_locale, date_format, timezone_name")],
    portfolio_id: Annotated[str, Form()] = "",
) -> CsvPreviewOut:
    content = _read_csv(file)
    pid = _csv_request(repositories, portfolio_id)
    try:
        return ledger_service.csv_preview(
            repositories.transactions_importer(), content=content,
            portfolio_id=pid, payload=_parse_mapping(mapping),
        )
    except (LedgerValidationError, TransactionCsvImportError) as error:
        raise _bad_request(str(error), status_code=CSV_IMPORT_ERROR_STATUS) from error


@router.post("/csv/import", response_model=CsvImportResultOut)
def import_csv(
    repositories: Repositories,
    file: Annotated[UploadFile, File()],
    mapping: Annotated[str, Form(description="JSON com institution, currency, delimiter, columns, instrument_map, decimal_locale, date_format, timezone_name")],
    portfolio_id: Annotated[str, Form()] = "",
) -> CsvImportResultOut:
    content = _read_csv(file)
    pid = _csv_request(repositories, portfolio_id)
    try:
        return ledger_service.csv_import(
            repositories.transactions_importer(), content=content,
            portfolio_id=pid, payload=_parse_mapping(mapping),
        )
    except (LedgerValidationError, TransactionCsvImportError) as error:
        raise _bad_request(str(error), status_code=CSV_IMPORT_ERROR_STATUS) from error


def _parse_mapping(raw: str) -> dict:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        raise _bad_request(f"mapping deve ser JSON válido: {error.msg}.") from error
    if not isinstance(payload, dict):
        raise _bad_request("mapping deve ser um objeto JSON.")
    return payload


def _read_csv(file: UploadFile) -> str:
    raw = file.file.read()
    if not raw:
        raise _bad_request("O arquivo CSV está vazio.")
    return raw.decode("utf-8-sig")


# -------------------------------------------------------------- transferências

@router.get("/transfers/suggestions", response_model=TransferSuggestionsOut)
def transfer_suggestions(
    repositories: Repositories,
    portfolio_id: str = Query(default=""),  # noqa: A002
    date_window_days: int = Query(default=3, ge=0),
    amount_tolerance: float = Query(default=0.01, ge=0),
    quantity_tolerance: float = Query(default=0.0, ge=0),
) -> TransferSuggestionsOut:
    pid = portfolio_id or default_portfolio_id()
    return ledger_service.transfer_suggestions(
        repositories.transactions,
        repositories.transfer_links,
        portfolio_id=pid,
        date_window_days=date_window_days,
        amount_tolerance=amount_tolerance,
        quantity_tolerance=quantity_tolerance,
    )


@router.post("/transfers/confirm", response_model=TransferLinkOut)
def confirm_transfer(repositories: Repositories, body: TransferConfirmIn) -> TransferLinkOut:
    try:
        result = ledger_service.confirm_transfer(
            repositories.transfer_links,
            transfer_out_id=body.transfer_out_id,
            transfer_in_id=body.transfer_in_id,
            confirmation_source=body.confirmation_source,
        )
    except ValueError as error:
        raise _bad_request(str(error)) from error
    return TransferLinkOut(**result)


# -------------------------------------------------------------- estado do banco

def _applied_migrations(database) -> list[tuple[int, str, str]]:
    applied: list[tuple[int, str, str]] = []
    with database.connection() as connection:
        exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
        ).fetchone()
        if exists is None:
            return []
        rows = connection.execute(
            "SELECT version, name, applied_at FROM schema_migrations ORDER BY version"
        ).fetchall()
    for row in rows:
        applied.append((int(row["version"]), str(row["name"]), str(row["applied_at"])))
    return applied

@router.get("/state", response_model=LedgerStateOut)
def ledger_state(repositories: Repositories) -> LedgerStateOut:
    database = repositories.database
    transactions_count = repositories.transactions.search(
        default_portfolio_id(), limit=1,
    )[1]
    unlinked = len([
        event for event in repositories.transactions.list_for_portfolio(default_portfolio_id())
        if event.transaction_type.value in {"TRANSFER_IN", "TRANSFER_OUT"}
    ])
    links = repositories.transfer_links.list_for_portfolio(default_portfolio_id())
    return LedgerStateOut(
        portfolios=[
            PortfolioOut(**item.model_dump(mode="json"))
            for item in repositories.portfolios.list_all()
        ],
        instruments_count=len(repositories.instruments.list_all()),
        snapshots_count=len(repositories.positions.list_snapshots(default_portfolio_id())),
        transactions_count=transactions_count,
        unlinked_transfer_events=unlinked - 2 * len(links),
        migrations=[
            MigrationOut(version=version, name=name, applied_at=applied_at)
            for version, name, applied_at in _applied_migrations(database)
        ],
        database_path=str(database.path),
    )
