"""Contratos da watchlist."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class WatchlistItemIn(BaseModel):
    asset_key: str = Field(min_length=1)
    name: str = Field(min_length=1)
    asset_class: str = Field(min_length=1)
    note: str | None = None


class WatchlistItemOut(BaseModel):
    asset_key: str
    name: str
    asset_class: str
    note: str | None = None
    created_at: datetime


class WatchlistOut(BaseModel):
    items: list[WatchlistItemOut]
    total: int
