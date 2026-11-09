"""Contratos de provedores externos.

Implementações traduzem o formato do fornecedor para `Observation`, sem expor
detalhes do provedor ao domínio. Nenhum provedor deve inventar valores para
dados ausentes: ausência simplesmente não gera observação.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Protocol

from src.domain.issuers import Issuer
from src.domain.observations import Observation


@dataclass(frozen=True)
class FundamentalsBatch:
    """Resultado de um exercício: observações normalizadas e emissores vistos."""

    observations: list[Observation]
    issuers: list[Issuer] = field(default_factory=list)


@dataclass(frozen=True)
class DocumentRef:
    """Referência a um documento externo, ainda sem conteúdo interpretado."""

    provider: str
    url: str
    title: str
    published_at: datetime | None = None
    content_hash: str | None = None


class MarketDataProvider(Protocol):
    name: str

    def daily_prices(self, symbol: str, start: date, end: date) -> Iterable[Observation]:
        """Séries de preço diário para um símbolo do provedor."""

    def fx_rate(self, base: str, quote: str, on: date) -> Observation | None:
        """Taxa de câmbio explícita para uma data, se publicada."""


class FundamentalsProvider(Protocol):
    name: str

    def fetch(self, fiscal_year: int) -> FundamentalsBatch:
        """Observações e emissores publicados para um exercício fiscal."""


class MacroDataProvider(Protocol):
    name: str

    def series(self, code: str, start: date, end: date) -> Iterable[Observation]:
        """Série macroeconômica identificada pelo código do provedor."""


class DocumentsProvider(Protocol):
    name: str

    def documents(self, entity_id: str) -> Iterable[DocumentRef]:
        """Documentos oficiais associados a uma entidade."""
