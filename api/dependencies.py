"""Fornecimento de dependências compartilhadas (banco, repositórios).

O banco é inicializado uma vez por processo; cada operação abre conexões
curtas, como já definido em src.persistence.database.
"""
from __future__ import annotations

from functools import lru_cache

from src.importers.transactions_csv import CanonicalTransactionCsvImporter
from src.persistence.database import SQLiteDatabase
from src.persistence.observations import ObservationRepository
from src.persistence.repositories import (
    InstrumentRepository, PortfolioPositionRepository, PortfolioRepository,
    PerformancePeriodRepository, TransactionRepository, TransferLinkRepository,
)
from src.persistence.snapshot_import import PortfolioSnapshotImporter

from api.config import database_path


@lru_cache(maxsize=1)
def get_database() -> SQLiteDatabase:
    database = SQLiteDatabase(database_path())
    database.initialize()
    return database


class Repositories:
    def __init__(self, database: SQLiteDatabase):
        self.database = database
        self.portfolios = PortfolioRepository(database)
        self.instruments = InstrumentRepository(database)
        self.positions = PortfolioPositionRepository(database)
        self.transactions = TransactionRepository(database)
        self.transfer_links = TransferLinkRepository(database)
        self.performance_periods = PerformancePeriodRepository(database)
        self.observations = ObservationRepository(database)
        self.snapshot_importer = PortfolioSnapshotImporter(database)

    def transactions_importer(self) -> CanonicalTransactionCsvImporter:
        return CanonicalTransactionCsvImporter(self.transactions)


@lru_cache(maxsize=1)
def get_repositories() -> Repositories:
    return Repositories(get_database())
