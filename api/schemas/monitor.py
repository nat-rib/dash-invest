"""Contratos do monitor de ativos."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class AssetMentionOut(BaseModel):
    key: str
    name: str
    asset_class: str
    confidence: float
    cnpj: str | None = None


class CandidateOut(BaseModel):
    key: str
    name: str
    asset_class: str
    score: float
    confidence: float
    components: dict[str, float | None]
    reasons: list[str]
    missing: list[str]
    sources: list[str]
    signal_count: int
    last_seen: datetime | None = None


class CandidateListOut(BaseModel):
    items: list[CandidateOut]
    total: int


class SignalOut(BaseModel):
    source: str
    title: str
    url: str
    summary: str
    published_at: datetime | None = None
    collected_at: datetime
    assets: list[AssetMentionOut]


class SignalListOut(BaseModel):
    items: list[SignalOut]
    total: int


class MonitorSourceOut(BaseModel):
    name: str
    url: str
    weight: float


class MonitorSourceListOut(BaseModel):
    items: list[MonitorSourceOut]
