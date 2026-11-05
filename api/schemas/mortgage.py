"""Contratos HTTP do simulador de amortização (Fase 6)."""
from __future__ import annotations

from pydantic import BaseModel, Field


class MortgageParametersIn(BaseModel):
    balance: float = Field(gt=0, description="Saldo devedor atual")
    months: int = Field(ge=1, le=600)
    annual_interest: float = Field(ge=0, le=2)
    annual_tr: float = Field(ge=0, le=0.5, default=0.0)
    monthly_fees: float = Field(ge=0, default=0.0)


class SimulationIn(MortgageParametersIn):
    rows_limit: int = Field(default=12, ge=1, le=120)


class ScheduleRow(BaseModel):
    month: int
    saldo_inicial: float
    saldo_corrigido: float
    amortizacao: float
    juros: float
    encargos: float
    parcela: float
    saldo_final: float


class SimulationOut(BaseModel):
    months: int
    total_interest: float
    total_paid: float
    schedule_rows: list[ScheduleRow]
    final_balance_series: list[BalancePoint]


class BalancePoint(BaseModel):
    month: int
    saldo_final: float
    scenario: str


class CompareIn(MortgageParametersIn):
    extra: float = Field(gt=0)
    mode: str = Field(pattern="^(prazo|parcela)$")
    net_annual_return: float = Field(ge=0, le=10)


class CompareOut(BaseModel):
    months_saved: int
    interest_saved: float
    payment_saved: float
    invest_value: float
    amortization_value: float
    difference: float
    winner: str
    break_even_net_return: float
    horizon_months: int
    invest_at_end: float
    amortize_at_end: float
    alternative_months: int
    balance_series: list[BalancePoint]
