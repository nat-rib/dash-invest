"""Contratos HTTP de histórico patrimonial e mercado (Fase 5)."""
from __future__ import annotations

from pydantic import BaseModel, Field


class HistoryPoint(BaseModel):
    captured_at: str
    total_brl: float
    source: str


class PositionHistoryPoint(BaseModel):
    captured_at: str
    position_key: str
    name: str
    institution: str
    currency: str
    current_price: float | None
    current_value: float | None
    value_brl: float | None


class PortfolioHistoryOut(BaseModel):
    points: list[HistoryPoint]
    notice: str = (
        "Variação de valor não equivale a rentabilidade: aportes, retiradas, "
        "impostos e proventos alteram o patrimônio."
    )


class PositionKeyListOut(BaseModel):
    keys: list[str]


class PositionHistoryOut(BaseModel):
    position_key: str
    points: list[PositionHistoryPoint]


class MarketPositionOut(BaseModel):
    index: int
    name: str
    symbol: str


class MarketQuoteOut(BaseModel):
    index: int
    name: str
    symbol: str
    price: str
    price_date: str | None


class QuotesPreviewOut(BaseModel):
    quotes: list[MarketQuoteOut]
    fx_rates: list[FxRateOut | None] = Field(default_factory=list)
    errors: list[str]
    positions: list[PreviewPositionOut]
    source: str


class FxRateOut(BaseModel):
    currency: str
    rate: str
    as_of_date: str | None


class PreviewPositionOut(BaseModel):
    index: int
    institution: str
    ticker: str | None
    name: str
    currency: str
    quantity: str | None
    current_price: str | None
    current_value: str | None
    converted_value_brl: str | None
    conversion_rate_to_brl: str | None
    changed: bool


class MarketHistoryPoint(BaseModel):
    date: str
    close: str
    currency: str


class MarketHistoryOut(BaseModel):
    symbol: str
    currency: str
    provider: str
    points: list[MarketHistoryPoint]
    unavailable_reason: str | None = None


class QuoteConfirmOut(BaseModel):
    updated: int
    unchanged: int
    message: str

