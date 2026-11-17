"""Sinais externos (notícias/RSS) e ativos mencionados.

O sinal guarda apenas metadados, trecho e link — nunca o texto integral de
terceiros. A extração de ativos é determinística e auditável.
"""
from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AssetMention(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    key: str = Field(min_length=1)
    name: str = Field(min_length=1)
    asset_class: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    cnpj: str | None = None


class Signal(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source: str = Field(min_length=1)
    source_type: str = "rss"
    title: str = Field(min_length=1)
    url: str = Field(min_length=1)
    summary: str = ""
    published_at: datetime | None = None
    collected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    content_hash: str = ""
    assets: tuple[AssetMention, ...] = ()
    raw: str | None = None

    @field_validator("source", "title", "url")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("campo obrigatório não pode ser vazio")
        return normalized

    @field_validator("published_at", "collected_at")
    @classmethod
    def _aware_utc(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("instantes devem incluir timezone")
        return value.astimezone(timezone.utc)

    @field_validator("summary")
    @classmethod
    def _trim(cls, value: str) -> str:
        return value.strip()[:4000]
