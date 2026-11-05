"""Contratos HTTP da importação de carteira (Fase 3 do roadmap)."""
from __future__ import annotations

from pydantic import BaseModel


class ImportPositionOut(BaseModel):
    institution: str
    asset_class: str
    ticker: str | None
    name: str
    quantity: str | None
    currency: str


class ImportPreviewOut(BaseModel):
    snapshot_date: str
    currency: str
    positions: list[ImportPositionOut]
    duplicates: list[list[str]]
    valid: bool
    validation_errors: list[str]
    message: str


class ImportConfirmOut(BaseModel):
    snapshot_date: str
    positions: int
    message: str
