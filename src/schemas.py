from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

AssetClass = Literal[
    "acao", "fii", "renda_fixa", "etf", "exterior", "cripto", "fundo", "outros", "caixa",
    "credito_privado_coletivo",
]


class Position(BaseModel):
    """Uma posição de carteira, sem conversão implícita de moedas."""

    model_config = ConfigDict(extra="forbid")

    institution: str = Field(min_length=1)
    asset_class: AssetClass
    ticker: str | None = None
    market_symbol: str | None = None
    name: str = Field(min_length=1)
    quantity: Decimal | None = Field(default=None, ge=0)
    average_cost: Decimal | None = Field(default=None, ge=0)
    operation_cost: Decimal | None = Field(default=None, ge=0)
    current_price: Decimal | None = Field(default=None, ge=0)
    current_value: Decimal | None = Field(default=None, ge=0)
    converted_value_brl: Decimal | None = Field(default=None, ge=0)
    conversion_rate_to_brl: Decimal | None = Field(default=None, gt=0)
    conversion_date: date | None = None
    currency: str = Field(min_length=3, max_length=3)
    indexer: str | None = None
    maturity_date: date | None = None
    application_date: date | None = None
    issuer: str | None = None
    annual_rate: Decimal | None = Field(default=None, ge=0)
    invested_amount: Decimal | None = Field(default=None, ge=0)
    dividends_received: Decimal | None = Field(default=None, ge=0)
    result_with_income_pct: Decimal | None = None
    tax_ir: Decimal | None = Field(default=None, ge=0)
    tax_iof: Decimal | None = Field(default=None, ge=0)
    net_value_reported: Decimal | None = Field(default=None, ge=0)
    valuation_type: str | None = None
    risk_category: str | None = None
    liquidity_profile: str | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def has_value_information(self) -> "Position":
        if self.current_value is None and (self.quantity is None or self.current_price is None):
            raise ValueError("Informe current_value ou quantity e current_price.")
        return self


class PortfolioSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1]
    snapshot_date: date
    currency: str = Field(min_length=3, max_length=3)
    positions: list[Position] = Field(min_length=1)
    institution_totals: dict[str, Decimal] | None = None
    reported_totals: dict[str, Decimal] | None = None
