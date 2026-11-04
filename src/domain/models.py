"""Modelos universais do domínio; independentes de UI e persistência."""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class AssetClass(StrEnum):
    EQUITY = "equity"
    REIT = "reit"
    FII = "fii"
    ETF = "etf"
    MUTUAL_FUND = "mutual_fund"
    FIXED_INCOME = "fixed_income"
    CRYPTO = "crypto"
    CASH = "cash"
    OTHER = "other"


class TransactionType(StrEnum):
    BUY = "BUY"
    SELL = "SELL"
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    DIVIDEND = "DIVIDEND"
    JCP = "JCP"
    INTEREST = "INTEREST"
    COUPON = "COUPON"
    AMORTIZATION = "AMORTIZATION"
    TAX = "TAX"
    FEE = "FEE"
    SPLIT = "SPLIT"
    BONUS = "BONUS"
    TRANSFER_IN = "TRANSFER_IN"
    TRANSFER_OUT = "TRANSFER_OUT"


class DomainModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class Instrument(DomainModel):
    """Cadastro estável do ativo; ticker não é identidade primária."""

    id: str = Field(default_factory=lambda: str(uuid4()), min_length=1)
    name: str = Field(min_length=1)
    asset_class: AssetClass
    subclass: str | None = None
    currency: str = Field(min_length=3, max_length=3)
    country: str | None = None
    exchange: str | None = None
    issuer_id: str | None = None
    provider_symbols: dict[str, str] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()


class Portfolio(DomainModel):
    id: str = Field(default_factory=lambda: str(uuid4()), min_length=1)
    name: str = Field(min_length=1)
    base_currency: str = Field(default="BRL", min_length=3, max_length=3)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("base_currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()


class PortfolioPosition(DomainModel):
    """Projeção atual de posição, não a origem do histórico econômico."""

    portfolio_id: str = Field(min_length=1)
    instrument_id: str = Field(min_length=1)
    institution: str = Field(min_length=1)
    quantity: Decimal | None = Field(default=None, ge=0)
    average_cost: Decimal | None = Field(default=None, ge=0)
    cost_currency: str = Field(min_length=3, max_length=3)
    as_of: date
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("cost_currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()


class Transaction(DomainModel):
    """Evento do ledger; sentido econômico é definido pelo tipo.

    Valores monetários e quantidades são positivos. Transferências internas
    exigem transfer_id para pareamento entre instituições.
    """

    id: str = Field(default_factory=lambda: str(uuid4()), min_length=1)
    portfolio_id: str = Field(min_length=1)
    transaction_type: TransactionType
    occurred_at: datetime
    institution: str = Field(min_length=1)
    instrument_id: str | None = None
    quantity: Decimal | None = Field(default=None, gt=0)
    unit_price: Decimal | None = Field(default=None, ge=0)
    amount: Decimal | None = Field(default=None, gt=0)
    currency: str = Field(min_length=3, max_length=3)
    fees: Decimal = Field(default=Decimal("0"), ge=0)
    taxes: Decimal = Field(default=Decimal("0"), ge=0)
    transfer_id: str | None = None
    external_id: str | None = None
    notes: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()

    @field_validator("occurred_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("occurred_at deve incluir timezone.")
        return value

    @model_validator(mode="after")
    def validate_transaction_shape(self) -> "Transaction":
        trade_types = {TransactionType.BUY, TransactionType.SELL}
        cash_types = {
            TransactionType.DEPOSIT, TransactionType.WITHDRAWAL,
            TransactionType.DIVIDEND, TransactionType.JCP,
            TransactionType.INTEREST, TransactionType.COUPON,
            TransactionType.AMORTIZATION, TransactionType.TAX,
            TransactionType.FEE,
        }
        if self.transaction_type in trade_types:
            if not self.instrument_id or self.quantity is None or self.unit_price is None:
                raise ValueError("BUY/SELL exigem instrument_id, quantity e unit_price.")
        if self.transaction_type in cash_types and self.amount is None:
            raise ValueError(f"{self.transaction_type.value} exige amount.")
        if self.transaction_type == TransactionType.SPLIT:
            if not self.instrument_id:
                raise ValueError("SPLIT exige instrument_id.")
            try:
                ratio = Decimal(str(self.metadata["ratio"]))
            except (KeyError, TypeError, ValueError):
                raise ValueError("SPLIT exige metadata.ratio numérico.") from None
            if ratio <= 0:
                raise ValueError("SPLIT metadata.ratio deve ser positivo.")
        if self.transaction_type == TransactionType.BONUS:
            if not self.instrument_id or self.quantity is None:
                raise ValueError("BONUS exige instrument_id e quantity.")
        if self.transaction_type == TransactionType.AMORTIZATION and not self.instrument_id:
            raise ValueError("AMORTIZATION exige instrument_id.")
        if self.transaction_type in {TransactionType.TRANSFER_IN, TransactionType.TRANSFER_OUT}:
            if not self.transfer_id:
                raise ValueError("Transferências internas exigem transfer_id.")
            if self.amount is None:
                raise ValueError("Transferências exigem amount (valor em dinheiro ou custo transferido).")
            if self.instrument_id is not None and self.quantity is None:
                raise ValueError("Transferência de ativo exige quantity.")
            if self.instrument_id is None and self.quantity is not None:
                raise ValueError("Transferência em dinheiro não deve informar quantity.")
        return self
