"""Observações externas normalizadas com proveniência (Fase 3: data platform).

Cada observação guarda de onde veio, quando foi publicada/coletada, qual a
unidade/moeda/período e a versão do parser. A ausência de um dado nunca é
representada como zero: um valor ausente simplesmente não gera linha.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class QualityStatus(StrEnum):
    VERIFIED = "verified"
    ESTIMATED = "estimated"
    STALE = "stale"
    UNKNOWN = "unknown"


def decimal_text(value: Decimal) -> str:
    """Serializa Decimal sem notação científica e sem perder casas significativas."""
    return format(value, "f")


class Observation(BaseModel):
    """Um fato externo rastreável até provedor, documento e data."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    provider: str = Field(min_length=1)
    metric: str = Field(min_length=1)
    instrument_id: str | None = None
    value: Decimal
    currency: str | None = None
    unit: str | None = None
    period_start: date | None = None
    period_end: date | None = None
    reference_date: date
    published_at: datetime | None = None
    collected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    parser_version: str = Field(min_length=1)
    quality_status: QualityStatus = QualityStatus.UNKNOWN
    source_document: str | None = None
    raw_payload: str | None = None

    @field_validator("provider", "metric", "parser_version")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("campo obrigatório não pode ser vazio")
        return normalized

    @field_validator("value")
    @classmethod
    def _finite(cls, value: Decimal) -> Decimal:
        if not value.is_finite():
            raise ValueError("value deve ser finito")
        return value

    @field_validator("currency")
    @classmethod
    def _currency(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        if len(normalized) != 3 or not normalized.isalpha():
            raise ValueError("currency deve ser um código ISO 4217 de 3 letras")
        return normalized

    @field_validator("collected_at", "published_at")
    @classmethod
    def _aware_utc(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("instantes devem incluir timezone")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def _period_order(self) -> "Observation":
        if self.period_start and self.period_end and self.period_end < self.period_start:
            raise ValueError("period_end não pode ser anterior a period_start")
        return self

    def fingerprint(self) -> str:
        """Identidade estável; reingestão do mesmo fato é idempotente."""
        payload = {
            "provider": self.provider,
            "instrument_id": self.instrument_id,
            "metric": self.metric,
            "value": decimal_text(self.value),
            "currency": self.currency,
            "unit": self.unit,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "reference_date": self.reference_date.isoformat(),
            "published_at": self.published_at.isoformat() if self.published_at else None,
        }
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
