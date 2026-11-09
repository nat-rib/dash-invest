"""Ingestão de fundamentos: provedor → emissores e observações."""
from __future__ import annotations

from dataclasses import dataclass

from src.persistence.issuers import IssuerRepository
from src.persistence.observations import ObservationRepository
from src.providers.base import FundamentalsProvider


@dataclass(frozen=True)
class FundamentalsIngestionResult:
    issuers: int
    observations: int


@dataclass(frozen=True)
class FundamentalsIngestion:
    provider: FundamentalsProvider
    repository: ObservationRepository
    issuers: IssuerRepository

    def run(self, fiscal_year: int) -> FundamentalsIngestionResult:
        """Persiste emissores e observações; retorna quantas linhas são novas."""
        batch = self.provider.fetch(fiscal_year)
        issuer_count = self.issuers.upsert_many(batch.issuers)
        observation_count = self.repository.record_many(batch.observations)
        return FundamentalsIngestionResult(
            issuers=issuer_count,
            observations=observation_count,
        )
