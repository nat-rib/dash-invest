"""Contratos de leitura de observações externas (Fase 3: data platform)."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ObservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    provider: str
    instrument_id: str | None = None
    metric: str
    value: Decimal
    currency: str | None = None
    unit: str | None = None
    period_start: date | None = None
    period_end: date | None = None
    reference_date: date
    published_at: datetime | None = None
    collected_at: datetime
    parser_version: str
    quality_status: str
    source_document: str | None = None


class ObservationListOut(BaseModel):
    items: list[ObservationOut]
    total: int


class ObservationSeriesPoint(BaseModel):
    reference_date: date
    published_at: datetime | None = None
    value: Decimal
    currency: str | None = None
    source_document: str | None = None


class ObservationSeriesOut(BaseModel):
    provider: str
    instrument_id: str | None = None
    metric: str
    points: list[ObservationSeriesPoint]
