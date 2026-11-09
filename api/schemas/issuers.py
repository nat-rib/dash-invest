"""Contratos de emissores (Fase 3)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class IssuerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    cnpj: str
    name: str
    cvm_code: str | None = None
    source: str
    updated_at: datetime


class IssuerListOut(BaseModel):
    items: list[IssuerOut]
    total: int
