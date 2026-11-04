"""Importação explícita de snapshots JSON para cadastros e posições.

Snapshots são salvos como posições de referência; nenhum evento de ledger é
fabricado, pois um snapshot não contém histórico de aportes e operações.
"""
from __future__ import annotations

from dataclasses import dataclass
from uuid import NAMESPACE_URL, uuid5

from src.domain.models import (
    AssetClass, Instrument, Portfolio, PortfolioPosition,
)
from src.persistence.database import SQLiteDatabase
from src.persistence.repositories import (
    InstrumentRepository, PortfolioPositionRepository, PortfolioRepository,
)
from src.schemas import PortfolioSnapshot, Position


_LEGACY_ASSET_CLASSES = {
    "acao": AssetClass.EQUITY,
    "fii": AssetClass.FII,
    "renda_fixa": AssetClass.FIXED_INCOME,
    "etf": AssetClass.ETF,
    "exterior": AssetClass.OTHER,
    "cripto": AssetClass.CRYPTO,
    "fundo": AssetClass.MUTUAL_FUND,
    "outros": AssetClass.OTHER,
    "caixa": AssetClass.CASH,
    "credito_privado_coletivo": AssetClass.FIXED_INCOME,
}


@dataclass(frozen=True)
class SnapshotImportResult:
    portfolio_id: str
    instruments_saved: int
    positions_saved: int
    transactions_created: int = 0


def _instrument_for_position(position: Position) -> Instrument:
    legacy_class = str(position.asset_class)
    asset_class = _LEGACY_ASSET_CLASSES.get(legacy_class, AssetClass.OTHER)
    identity = position.market_symbol or position.ticker or position.name
    stable_key = f"{legacy_class}|{position.currency.upper()}|{identity.strip().casefold()}"
    instrument_id = str(uuid5(NAMESPACE_URL, f"dash-invest:legacy:{stable_key}"))
    provider_symbols = {}
    if position.ticker:
        provider_symbols["legacy_ticker"] = position.ticker
    if position.market_symbol:
        provider_symbols["market_symbol"] = position.market_symbol
    return Instrument(
        id=instrument_id,
        name=position.name,
        asset_class=asset_class,
        subclass=legacy_class,
        currency=position.currency,
        provider_symbols=provider_symbols,
        metadata={
            "source": "portfolio_snapshot_json",
            "legacy_asset_class": legacy_class,
            "legacy_ticker": position.ticker,
            "market_symbol": position.market_symbol,
        },
    )


class PortfolioSnapshotImporter:
    """Persiste um snapshot validado sem convertê-lo em operações históricas."""

    def __init__(self, database: SQLiteDatabase):
        self.database = database
        self.portfolios = PortfolioRepository(database)
        self.instruments = InstrumentRepository(database)
        self.positions = PortfolioPositionRepository(database)

    def import_snapshot(
        self, snapshot: PortfolioSnapshot, *,
        portfolio_id: str = "legacy-import",
        portfolio_name: str = "Carteira importada",
    ) -> SnapshotImportResult:
        portfolio = Portfolio(
            id=portfolio_id, name=portfolio_name, base_currency=snapshot.currency,
        )
        mapped = [_instrument_for_position(position) for position in snapshot.positions]
        # Mesmo ativo em instituições diferentes compartilha um Instrument.
        unique_instruments = {instrument.id: instrument for instrument in mapped}
        instrument_by_position = {
            id(position): instrument for position, instrument in zip(snapshot.positions, mapped)
        }
        positions = [
            PortfolioPosition(
                portfolio_id=portfolio_id,
                instrument_id=instrument_by_position[id(position)].id,
                institution=position.institution,
                quantity=position.quantity,
                average_cost=position.average_cost,
                cost_currency=position.currency,
                as_of=snapshot.snapshot_date,
                metadata={
                    "source": "portfolio_snapshot_json",
                    "snapshot_schema_version": snapshot.schema_version,
                    "legacy_position": position.model_dump(mode="json"),
                },
            )
            for position in snapshot.positions
        ]

        position_keys = [(item.instrument_id, item.institution) for item in positions]
        if len(position_keys) != len(set(position_keys)):
            raise ValueError(
                "O snapshot contém o mesmo instrumento mais de uma vez na mesma instituição; "
                "consolide as linhas antes de importar."
            )

        # Um único commit evita carteira parcialmente importada em caso de erro.
        with self.database.transaction() as connection:
            self.portfolios.save(portfolio, connection=connection)
            for instrument in unique_instruments.values():
                self.instruments.save(instrument, connection=connection)
            for position in positions:
                self.positions.save_snapshot(position, connection=connection)

        return SnapshotImportResult(
            portfolio_id=portfolio_id,
            instruments_saved=len(unique_instruments),
            positions_saved=len(positions),
            transactions_created=0,
        )
