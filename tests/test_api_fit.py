import json
from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

import api.dependencies as dependencies
from api.main import create_app
from src.domain.observations import Observation, QualityStatus
from src.persistence.observations import ObservationRepository

SNAPSHOT = {
    "schema_version": 1,
    "snapshot_date": "2026-03-31",
    "currency": "BRL",
    "positions": [
        {
            "institution": "XP",
            "asset_class": "acao",
            "ticker": "PETR4",
            "name": "Petrobras PN",
            "quantity": "100",
            "average_cost": "20.00",
            "current_price": "30.00",
            "currency": "BRL",
        },
        {
            "institution": "XP",
            "asset_class": "fii",
            "ticker": "HGLG11",
            "name": "CSHG Logística",
            "quantity": "10",
            "average_cost": "90.00",
            "current_price": "100.00",
            "currency": "BRL",
        },
        {
            "institution": "BTG",
            "asset_class": "renda_fixa",
            "name": "CDB",
            "current_value": "500.00",
            "currency": "BRL",
            "liquidity_profile": "D+1",
            "risk_category": "baixo",
        },
    ],
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DASH_INVEST_DB_PATH", str(tmp_path / "api.db"))
    monkeypatch.setenv("PORTFOLIO_PATH", str(tmp_path / "portfolio.json"))
    (tmp_path / "portfolio.json").write_text(json.dumps(SNAPSHOT), encoding="utf-8")
    dependencies.get_database.cache_clear()
    dependencies.get_repositories.cache_clear()
    with TestClient(create_app()) as test_client:
        yield test_client


def insert_close(symbol: str, days: int = 40) -> None:
    repository = ObservationRepository(dependencies.get_database())
    start = date(2024, 1, 1)
    repository.record_many(
        [
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
    )


def test_fit_do_snapshot(client):
    body = client.get("/api/fit").json()

    assert body["total_brl"] == pytest.approx(4500)
    assert body["positions"] == 3
    assert [slice["name"] for slice in body["by_class"]] == ["acao", "fii", "renda_fixa"]
    assert body["by_class"][0]["share"] == pytest.approx(3000 / 4500)
    assert body["herfindahl"] == pytest.approx(
        (3000 / 4500) ** 2 + (1000 / 4500) ** 2 + (500 / 4500) ** 2
    )
    assert body["liquidity_coverage"] == pytest.approx(500 / 4500)
    assert body["correlations"] == []


def test_fit_sem_carteira(client, monkeypatch, tmp_path):
    monkeypatch.setattr(
        "api.services.fit_service.portfolio_path", lambda: tmp_path / "inexistente.json"
    )

    response = client.get("/api/fit")

    assert response.status_code == 400
    assert "Importe uma carteira" in response.json()["detail"]


def test_fit_calcula_correlacao_entre_posicoes_com_serie(client):
    insert_close("PETR4.SAO")
    insert_close("HGLG11.SAO")

    body = client.get("/api/fit").json()

    assert len(body["correlations"]) == 1
    assert body["correlations"][0]["correlation"] == pytest.approx(1.0)
    assert body["correlations"][0]["observations"] == 40
