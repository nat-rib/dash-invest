"""Contratos do screener e de valuation (Fase 5)."""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class ScreenerRowOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    cnpj: str
    name: str | None = None
    reference_date: date | None = None
    revenue: float | None = None
    net_income: float | None = None
    equity: float | None = None
    total_assets: float | None = None
    net_margin: float | None = None
    roe: float | None = None
    roa: float | None = None
    asset_turnover: float | None = None


class ScreenerOut(BaseModel):
    items: list[ScreenerRowOut]
    total: int


class DcfRequest(BaseModel):
    base_cash_flow: float = Field(gt=0, le=1e15)
    growth_rate: float = Field(gt=-1, le=1)
    years: int = Field(ge=1, le=50)
    terminal_growth: float = Field(gt=-1, lt=1)
    discount_rate: float = Field(gt=-1, le=1)


class DcfProjectionOut(BaseModel):
    year: int
    cash_flow: float
    present_value: float


class DcfOut(BaseModel):
    present_value_explicit: float
    present_value_terminal: float
    enterprise_value: float
    projections: list[DcfProjectionOut]
