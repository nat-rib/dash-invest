"""Contratos HTTP do domínio Rentabilidade (Fase 2 do roadmap)."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PerformanceFlowOut(BaseModel):
    date: str
    amount: str  # Ótica do investidor: aporte negativo, retirada positiva.
    currency: str


class PerformanceFlowsOut(BaseModel):
    portfolio_id: str
    portfolio_name: str
    currency: str | None
    flows: list[PerformanceFlowOut]
    unavailable_reason: str | None = None


class XirrCalculateIn(BaseModel):
    portfolio_id: str | None = None
    terminal_value: str = Field(pattern=r"^\d+(\.\d+)?$", description="Valor terminal positivo em moeda-base")
    terminal_date: str = Field(min_length=10, max_length=10)


class PerformanceResultOut(BaseModel):
    rate: str
    periods: int
    start_date: str
    end_date: str


class XirrCalculateOut(BaseModel):
    annual_rate: str
    terminal_value: str
    terminal_date: str
    flows_used: int
    unavailable_reason: str | None = None


class TwrPeriodIn(BaseModel):
    start_date: str
    end_date: str
    start_value: str
    end_value_after_flows: str
    net_external_flow: str

    @model_validator(mode="after")
    def dates_ordered(self) -> "TwrPeriodIn":
        if self.end_date <= self.start_date:
            raise ValueError("O fim do período deve ser posterior ao início.")
        return self


class TwrCalculateIn(BaseModel):
    portfolio_id: str | None = None
    periods: list[TwrPeriodIn] | None = None


class TwrPeriodOut(BaseModel):
    start_date: str
    end_date: str
    start_value: str
    end_value_after_flows: str
    net_external_flow: str


class TwrCalculateOut(BaseModel):
    rate: str
    periods: int
    start_date: str
    end_date: str
    unavailable_reason: str | None = None


class TwrValuationsSaveIn(BaseModel):
    portfolio_id: str | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    periods: list[TwrPeriodIn] = Field(min_length=1)


class TwrValuationsOut(BaseModel):
    portfolio_id: str
    currency: str
    periods: list[TwrPeriodOut]
    saved: int
