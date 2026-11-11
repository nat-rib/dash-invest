from datetime import date
from decimal import Decimal

import pytest

from src.application.portfolio_prices import ingest_portfolio_prices, portfolio_symbols
from src.domain.observations import Observation, QualityStatus
from src.market_data import MarketDataError
from src.persistence.database import SQLiteDatabase
from src.persistence.observations import ObservationRepository
from src.schemas import PortfolioSnapshot

SNAPSHOT = PortfolioSnapshot.model_validate(
    {
        "schema_version": 1,
        "snapshot_date": "2026-03-31",
        "currency": "BRL",
        "positions": [
            {
                "institution": "XP",
                "asset_class": "acao",
                "ticker": "PETR4",
                "name": "Petrobras",
                "quantity": "10",
                "current_price": "30.00",
                "currency": "BRL",
            },
            {
                "institution": "BTG",
                "asset_class": "acao",
                "ticker": "PETR4",
                "name": "Petrobras",
                "quantity": "5",
                "current_price": "30.00",
                "currency": "BRL",
            },
            {
                "institution": "XP",
                "asset_class": "fii",
                "ticker": "HGLG11",
                "name": "CSHG Log",
                "quantity": "5",
                "current_price": "100.00",
                "currency": "BRL",
            },
            {
                "institution": "XP",
                "asset_class": "etf",
                "ticker": "IVVB11",
                "name": "S&P 500",
                "quantity": "5",
                "current_price": "300.00",
                "currency": "BRL",
            },
            {
                "institution": "XP",
                "asset_class": "cripto",
                "ticker": "BTC",
                "name": "Bitcoin",
                "quantity": "0.1",
                "current_price": "300000",
                "currency": "BRL",
            },
            {
                "institution": "Avenue",
                "asset_class": "exterior",
                "ticker": "AAPL",
                "market_symbol": "AAPL",
                "name": "Apple",
                "quantity": "2",
                "current_price": "200",
                "currency": "USD",
            },
        ],
    }
)


def test_deriva_simbolos_unicos_e_ignora_cripto():
    symbols = portfolio_symbols(SNAPSHOT)

    assert [(item.symbol, item.currency) for item in symbols] == [
        ("PETR4.SAO", "BRL"),
        ("HGLG11.SAO", "BRL"),
        ("IVVB11.SAO", "BRL"),
        ("AAPL", "USD"),
    ]


class FakeProvider:
    def __init__(self, failures: tuple[str, ...] = ()):
        self.failures = failures
        self.calls: list[tuple[str, str | None]] = []

    def daily_prices(self, symbol, start=None, end=None, currency=None):
        self.calls.append((symbol, currency))
        if symbol in self.failures:
            raise MarketDataError("falha simulada")
        return [
            Observation(
                provider="fake",
                metric="close",
                instrument_id=symbol,
                value=Decimal("10"),
                currency=currency,
                reference_date=date(2024, 1, 1),
                period_end=date(2024, 1, 1),
                parser_version="test",
                quality_status=QualityStatus.VERIFIED,
            )
        ]


@pytest.fixture
def repository(tmp_path):
    database = SQLiteDatabase(tmp_path / "prices.db")
    database.initialize()
    return ObservationRepository(database)


def test_ingere_respeitando_limite_e_idempotencia(repository):
    provider = FakeProvider()

    first = ingest_portfolio_prices(SNAPSHOT, provider, repository, max_symbols=2)
    second = ingest_portfolio_prices(SNAPSHOT, provider, repository, max_symbols=2)

    assert first.inserted == 2
    assert first.fetched == ("PETR4.SAO", "HGLG11.SAO")
    assert first.skipped == ("IVVB11.SAO", "AAPL")
    assert second.inserted == 0
    assert len(repository.list(provider="fake")) == 2


def test_falha_de_um_simbolo_nao_interrompe_os_demais(repository):
    provider = FakeProvider(failures=("PETR4.SAO",))

    summary = ingest_portfolio_prices(SNAPSHOT, provider, repository, max_symbols=2)

    assert summary.inserted == 1
    assert len(summary.errors) == 1
    assert "PETR4.SAO" in summary.errors[0]
    assert repository.list(provider="fake")
