"""Contratos da pesquisa assistida por IA (Fase 7)."""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class ClaimOut(BaseModel):
    key: str
    text: str
    metric: str
    value: float
    unit: str
    reference_date: date | None = None
    source_url: str | None = None


class ResearchReportOut(BaseModel):
    cnpj: str
    name: str
    generated_at: datetime
    narrative: str
    claims: list[ClaimOut]
    limitations: list[str]
    sources: list[str]
    gateway: str
