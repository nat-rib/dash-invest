"""Ingestão de fundamentos: provedor → emissores e observações."""
from __future__ import annotations

from dataclasses import dataclass

from src.domain.observations import Observation
from src.persistence.issuers import IssuerRepository
from src.persistence.observations import ObservationRepository
from src.providers.base import FundamentalsProvider

DEFAULT_CHUNK_SIZE = 1000


@dataclass(frozen=True)
class FundamentalsIngestionResult:
    issuers: int
    observations: int


@dataclass(frozen=True)
class FundamentalsIngestion:
    provider: FundamentalsProvider
    repository: ObservationRepository
    issuers: IssuerRepository
    chunk_size: int = DEFAULT_CHUNK_SIZE

    def run(self, fiscal_year: int) -> FundamentalsIngestionResult:
        """Persiste emissores e observações em chunks; retorna quantas linhas são novas.

        O provedor entrega as observações de forma incremental, então o exercício
        inteiro nunca é materializado em memória — importante para o ITR, que tem
        centenas de milhares de linhas.
        """
        batch = self.provider.fetch(fiscal_year)
        issuer_count = self.issuers.upsert_many(batch.issuers)

        observation_count = 0
        chunk: list[Observation] = []
        for observation in batch.observations:
            chunk.append(observation)
            if len(chunk) >= self.chunk_size:
                observation_count += self.repository.record_many(chunk)
                chunk = []
        if chunk:
            observation_count += self.repository.record_many(chunk)

        return FundamentalsIngestionResult(
            issuers=issuer_count,
            observations=observation_count,
        )
