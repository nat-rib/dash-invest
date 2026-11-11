"""Contratos do Portfolio Fit (Fase 6)."""
from __future__ import annotations

from pydantic import BaseModel


class ExposureSliceOut(BaseModel):
    name: str
    value: float
    share: float
    positions: int


class FitPositionOut(BaseModel):
    name: str
    institution: str
    asset_class: str
    currency: str
    value_brl: float
    share: float
    liquidity: str | None = None
    risk_category: str | None = None


class CorrelationPairOut(BaseModel):
    left: str
    right: str
    correlation: float
    observations: int


class PortfolioFitOut(BaseModel):
    total_brl: float
    positions: int
    by_class: list[ExposureSliceOut]
    by_institution: list[ExposureSliceOut]
    by_currency: list[ExposureSliceOut]
    top_positions: list[FitPositionOut]
    herfindahl: float | None = None
    liquidity_coverage: float | None = None
    credit_coverage: float | None = None
    correlations: list[CorrelationPairOut]
    unavailable: list[str]
