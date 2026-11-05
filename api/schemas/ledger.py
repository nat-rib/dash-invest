"""Contratos HTTP do domínio Ledger.

Valores monetários e quantidades trafegam como string para preservar
exatidão decimal; datas como ISO-8601.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ErrorOut(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"detail": "mensagem"}})
    detail: str


class PageMeta(BaseModel):
    limit: int
    offset: int
    total: int


class InstrumentOut(BaseModel):
    id: str
    name: str
    asset_class: str
    subclass: str | None = None
    currency: str
    country: str | None = None
    exchange: str | None = None
    issuer_id: str | None = None
    provider_symbols: dict[str, str]
    metadata: dict


class InstrumentCreate(BaseModel):
    name: str = Field(min_length=1)
    asset_class: str = Field(min_length=1)
    currency: str = Field(min_length=3, max_length=3)
    exchange: str | None = None
    ticker: str = Field(min_length=1)


class TransferEventOut(BaseModel):
    id: str
    transaction_type: str
    occurred_at: str
    institution: str
    amount: str | None = None
    quantity: str | None = None
    currency: str
    instrument_id: str | None = None
    external_id: str | None = None


class SuggestedPairOut(BaseModel):
    transfer_out: TransferEventOut
    transfer_in: TransferEventOut
    date_delta_seconds: int
    amount_delta: str


class TransferSuggestionsOut(BaseModel):
    suggested_pairs: list[SuggestedPairOut]
    ambiguous_transaction_ids: list[str]
    unmatched_transaction_ids: list[str]
    incomplete_transfer_ids: list[str]
    invalid_transfer_ids: list[str]
    pending_out_events: list[TransferEventOut]
    pending_in_events: list[TransferEventOut]
    confirmed_links: list[TransferLinkOut]


class TransferConfirmIn(BaseModel):
    transfer_out_id: str = Field(min_length=1)
    transfer_in_id: str = Field(min_length=1)
    confirmation_source: Literal["manual", "manual_review"] = "manual"


class TransferLinkOut(BaseModel):
    transfer_out_id: str
    transfer_in_id: str
    portfolio_id: str
    linked_at: str
    confirmation_source: str


class SnapshotPositionOut(BaseModel):
    institution: str
    asset_class: str
    ticker: str | None = None
    name: str
    quantity: str | None = None
    currency: str


class SnapshotPreviewOut(BaseModel):
    portfolio_id: str
    snapshot_date: str
    currency: str
    positions: list[SnapshotPositionOut]


class SnapshotImportResultOut(BaseModel):
    portfolio_id: str
    instruments_saved: int
    positions_saved: int
    transactions_created: int
    message: str


class PreviewTransactionOut(BaseModel):
    row_number: int
    external_id: str
    occurred_at: str
    transaction_type: str
    institution: str
    currency: str
    instrument_id: str | None = None
    quantity: str | None = None
    unit_price: str | None = None
    amount: str | None = None
    fees: str
    taxes: str


class CsvPreviewOut(BaseModel):
    parsed: int
    transactions: list[PreviewTransactionOut]


class CsvImportResultOut(BaseModel):
    parsed: int
    inserted: int
    skipped_duplicates: int
    message: str


class LedgerTransactionOut(BaseModel):
    id: str
    portfolio_id: str
    transaction_type: str
    occurred_at: str
    sequence: int
    institution: str
    instrument_id: str | None = None
    instrument_label: str | None = None
    quantity: str | None = None
    unit_price: str | None = None
    amount: str | None = None
    currency: str
    fees: str
    taxes: str
    transfer_id: str | None = None
    transfer_linked: bool = False
    external_id: str | None = None
    notes: str | None = None
    metadata: dict


class LedgerPageOut(BaseModel):
    meta: PageMeta
    items: list[LedgerTransactionOut]


class PortfolioOut(BaseModel):
    id: str
    name: str
    base_currency: str
    created_at: str


class MigrationOut(BaseModel):
    version: int
    name: str
    applied_at: str


class LedgerStateOut(BaseModel):
    portfolios: list[PortfolioOut]
    instruments_count: int
    snapshots_count: int
    transactions_count: int
    unlinked_transfer_events: int
    migrations: list[MigrationOut]
    database_path: str


class LedgerPageQuery(BaseModel):
    portfolio_id: str
