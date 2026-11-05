"""Contratos HTTP da visão geral (Fase 1 do roadmap de experiência)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from api.schemas.analysis import AllocationSlice


class OverviewSnapshotOut(BaseModel):
    available: bool
    error: str | None = None
    snapshot_date: str | None = None
    currency: str | None = None


class TopPositionOut(BaseModel):
    index: int
    name: str
    institution: str
    asset_class: str
    consolidated_brl: str
    share: str
    concentration_level: Literal["high", "medium", "low"]
    risk_category: str | None = None


class OverviewAlertOut(BaseModel):
    id: str
    tone: Literal["good", "info", "warn"]
    title: str
    message: str


class OverviewPerformanceOut(BaseModel):
    available: bool
    metric: str | None = None
    rate: str | None = None
    periods: int | None = None
    start_date: str | None = None
    end_date: str | None = None
    reason: str | None = None


class OverviewBenchmarkOut(BaseModel):
    available: bool = False
    name: str | None = None
    reason: str | None = None


class OverviewQualityOut(BaseModel):
    level: Literal["complete", "partial", "unknown"]
    positions_count: int
    known_positions: int
    unknown_positions: int
    message: str


class OverviewLedgerOut(BaseModel):
    instruments_count: int
    transactions_count: int
    snapshots_count: int
    unlinked_transfer_events: int
    database_path: str


class OverviewOut(BaseModel):
    portfolio_id: str
    snapshot: OverviewSnapshotOut
    total_brl: str | None
    known_positions: int
    unknown_positions: int
    positions_count: int
    by_class: list[AllocationSlice]
    by_institution: list[AllocationSlice]
    top_positions: list[TopPositionOut]
    alerts: list[OverviewAlertOut]
    performance: OverviewPerformanceOut
    benchmark: OverviewBenchmarkOut
    quality: OverviewQualityOut
    ledger: OverviewLedgerOut
