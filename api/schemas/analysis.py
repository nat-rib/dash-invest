"""Contratos HTTP da análise da carteira (Fase 4 do roadmap)."""
from __future__ import annotations

from pydantic import BaseModel


class AllocationSlice(BaseModel):
    name: str
    value: str
    share: str
    positions: int


class AllocationOut(BaseModel):
    total_brl: str
    known_positions: int
    unknown_positions: int  # posições sem valor consolidado BRL; nunca viram zero
    by_class: list[AllocationSlice]
    by_institution: list[AllocationSlice]


class ConcentrationItem(BaseModel):
    index: int
    name: str
    institution: str
    asset_class: str
    consolidated_brl: str | None
    share: str | None


class ComparablePosition(BaseModel):
    index: int
    name: str
    institution: str
    cost_total: str
    current_value: str
    currency: str


class ConcentrationOut(BaseModel):
    total_brl: str
    items: list[ConcentrationItem]
    top: list[ConcentrationItem]
    comparable: list[ComparablePosition]


class PositionListOut(BaseModel):
    snapshot_date: str
    positions: list[PositionSummaryOut]


class PositionSummaryOut(BaseModel):
    index: int
    name: str
    institution: str
    asset_class: str
    currency: str
    consolidated_brl: str | None


class PositionDetailOut(BaseModel):
    index: int
    name: str
    institution: str
    asset_class: str
    ticker: str | None
    currency: str
    quantity: str | None
    average_cost: str | None
    operation_cost: str | None
    current_price: str | None
    current_value: str | None
    cost_total: str | None
    gain_loss: str | None
    unrealized_return: str | None
    converted_value_brl: str | None
    conversion_rate_to_brl: str | None
    conversion_date: str | None
    consolidated_brl: str | None
    indexer: str | None
    maturity_date: str | None
    application_date: str | None
    issuer: str | None
    annual_rate: str | None
    invested_amount: str | None
    dividends_received: str | None
    risk_category: str | None
    liquidity_profile: str | None
    notes: str | None
