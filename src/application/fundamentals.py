"""Ingestão de fundamentos: provedor → repositório de observações."""
from __future__ import annotations

from dataclasses import dataclass

from src.persistence.observations import ObservationRepository
from src.providers.base import FundamentalsProvider


@dataclass(frozen=True)
class FundamentalsIngestion:
    provider: FundamentalsProvider
    repository: ObservationRepository

    def run(self, fiscal_year: int) -> int:
        """Persiste o exercício inteiro em uma transação; retorna linhas novas."""
        observations = list(self.provider.statements(fiscal_year))
        return self.repository.record_many(observations)
