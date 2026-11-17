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
    cnpj: str | None = None
    price_provider: str | None = None
    price_instrument: str | None = None


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


class ScoreBucketOut(BaseModel):
    label: str
    count: int
    average_return: float | None = None
    hit_rate: float | None = None


class BacktestOut(BaseModel):
    snapshots: int
    evaluated: int
    horizon_days: int
    buckets: list[ScoreBucketOut]
    rank_correlation: float | None = None
    top_average: float | None = None
    bottom_average: float | None = None
    spread: float | None = None
    available: bool
    reason: str | None = None


class AlertOut(BaseModel):
    asset_key: str
    name: str
    score: float
    channel: str
    message: str
    sent_at: datetime


class AlertListOut(BaseModel):
    items: list[AlertOut]
    total: int


class AlertConfigOut(BaseModel):
    channels: list[str]
    min_score: float
    cooldown_days: int
    max_alerts: int
    telegram_configured: bool
    email_configured: bool
