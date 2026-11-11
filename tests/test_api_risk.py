from datetime import date, datetime, timedelta
from decimal import Decimal

import pandas as pd
import pytest
from fastapi.testclient import TestClient

import api.dependencies as dependencies
from api.main import create_app
from src.domain.observations import Observation, QualityStatus
from src.persistence.observations import ObservationRepository


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DASH_INVEST_DB_PATH", str(tmp_path / "api.db"))
    dependencies.get_database.cache_clear()
    dependencies.get_repositories.cache_clear()
    with TestClient(create_app()) as test_client:
        yield test_client


def insert_prices(symbol: str = "PETR4.SAO", days: int = 40) -> None:
    repository = ObservationRepository(dependencies.get_database())
    start = date(2024, 1, 1)
    observations = [
        Observation(
            provider="csv",
            metric="close",
            instrument_id=symbol,
            value=Decimal(str(100 + index)),
            currency="BRL",
            reference_date=start + timedelta(days=index),
            period_end=start + timedelta(days=index),
            parser_version="test",
            quality_status=QualityStatus.VERIFIED,
        )
        for index in range(days)
    ]
    repository.record_many(observations)


def test_risco_do_ativo_com_amostra_suficiente(client):
    insert_prices()

    body = client.get(
        "/api/risk/instrument",
        params={"provider": "csv", "instrument_id": "PETR4.SAO", "risk_free_rate": 0.1},
    ).json()

    assert body["observations"] == 40
    assert body["returns"] == 39
    assert body["total_return"] > 0
    assert body["annualized_volatility"] is not None
    assert body["var_95_parametric"] is not None
    assert body["monthly_returns"]
    assert body["max_drawdown"] == 0.0
    assert body["unavailable"] == []


def test_risco_de_serie_inexistente_explica_indisponibilidade(client):
    body = client.get(
        "/api/risk/instrument",
        params={"provider": "csv", "instrument_id": "NAO.EXISTE"},
    ).json()

    assert body["observations"] == 0
    assert body["total_return"] is None
    assert body["reason"]


def test_lista_series_disponiveis(client):
    insert_prices()

    body = client.get("/api/data/series", params={"provider": "csv"}).json()

    assert body["items"] == [
        {
            "provider": "csv",
            "instrument_id": "PETR4.SAO",
            "metric": "close",
            "observations": 40,
        }
    ]


def test_risco_da_carteira_sem_historico(client, monkeypatch):
    monkeypatch.setattr(
        "api.services.risk_service.portfolio_history",
        lambda: pd.DataFrame({"Data": [], "Patrimônio BRL": []}),
    )

    body = client.get("/api/risk/portfolio").json()

    assert body["observations"] == 0
    assert body["total_return"] is None
    assert body["reason"]


def test_risco_da_carteira_com_historico(client, monkeypatch):
    days = [datetime(2024, 1, 1) + timedelta(days=index) for index in range(40)]
    frame = pd.DataFrame(
        {"Data": days, "Patrimônio BRL": [100000 + index * 500 for index in range(40)]}
    )
    monkeypatch.setattr("api.services.risk_service.portfolio_history", lambda: frame)

    body = client.get("/api/risk/portfolio").json()

    assert body["observations"] == 40
    assert body["total_return"] > 0
    assert body["annualized_volatility"] is not None
