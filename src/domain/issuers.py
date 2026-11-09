"""Emissores (companhias) que publicam dados externos.

O CNPJ é a identidade estável do emissor. O vínculo com um `Instrument`
(security) é feito depois: uma companhia pode ter várias ações/classes.
"""
from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Issuer(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    cnpj: str
    name: str = Field(min_length=1)
    cvm_code: str | None = None
    source: str = Field(default="cvm", min_length=1)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("cnpj")
    @classmethod
    def _cnpj(cls, value: str) -> str:
        digits = "".join(char for char in value if char.isdigit())
        if len(digits) != 14:
            raise ValueError("cnpj deve conter 14 dígitos")
        return digits

    @field_validator("name", "source")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("campo obrigatório não pode ser vazio")
        return normalized

    @field_validator("cvm_code")
    @classmethod
    def _cvm_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None

    @field_validator("updated_at")
    @classmethod
    def _aware_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("updated_at deve incluir timezone")
        return value.astimezone(timezone.utc)
