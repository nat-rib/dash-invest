import json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

import api.dependencies as dependencies
from api.main import create_app
from src.domain.signals import AssetMention, Signal
from src.persistence.signals import SignalRepository

SNAPSHOT = {
    "schema_version": 1,
    "snapshot_date": "2026-03-31",
    "currency": "BRL",
    "positions": [
        {"institution": "XP", "asset_class": "acao", "ticker": "PETR4", "name": "Petrobras", "quantity": "10", "current_price": "30.00", "currency": "BRL"},
        {"institution": "BTG", "asset_class": "renda_fixa", "name": "CDB", "current_value": "100.00", "currency": "BRL"},
        {"institution": "XP", "asset_class": "fii", "ticker": "HGLG11", "name": "CSHG Log", "quantity": "2", "current_price": "100.00", "currency": "BRL"},
        {"institution": "XP", "asset_class": "etf", "ticker": "BOVA11", "name": "BOVA", "quantity": "1", "current_price": "100.00", "currency": "BRL"},
        {"institution": "XP", "asset_class": "cripto", "ticker": "BTC", "name": "Bitcoin", "quantity": "0.001", "current_price": "100000", "currency": "BRL"},
        {"institution": "Avenue", "asset_class": "exterior", "ticker": "AAPL", "name": "Apple", "quantity": "1", "current_price": "200.00", "currency": "BRL"},
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


def seed_signals() -> None:
    repository = SignalRepository(dependencies.get_database())
    now = datetime.now(timezone.utc)
    repository.record_many(
        [
            Signal(
                source="InfoMoney",
                title="Tesouro Selic atrai investidores",
                url="https://example/tesouro",
                summary="Renda fixa",
                published_at=now,
                collected_at=now,
                assets=(
                    AssetMention(
                        key="fixed_income:tesouro-selic",
                        name="Tesouro Selic",
                        asset_class="renda_fixa",
                        confidence=0.75,
                    ),
                ),
            ),
            Signal(
                source="Exame",
                title="Petrobras anuncia dividendos",
                url="https://example/petrobras",
                summary="PETR4",
                published_at=now,
                collected_at=now,
                assets=(
                    AssetMention(
                        key="ticker:PETR4",
                        name="Petrobras",
                        asset_class="acao",
                        confidence=0.95,
                        cnpj="33000167000101",
                    ),
                ),
            ),
        ]
    )


def test_ranking_prioriza_renda_fixa_abaixo_do_alvo(client):
    seed_signals()

    body = client.get("/api/monitor/candidates").json()

    assert body["total"] >= 2
    first = body["items"][0]
    assert first["key"] == "fixed_income:tesouro-selic"
    assert first["asset_class"] == "renda_fixa"
    assert any("abaixo do alvo" in reason for reason in first["reasons"])
    assert "fundamentos" in first["missing"]

    petro = next(item for item in body["items"] if item["key"] == "ticker:PETR4")
    assert petro["components"]["concentration"] == 0.0


def test_lista_sinais_e_fontes(client):
    seed_signals()
    repository = SignalRepository(dependencies.get_database())
    now = datetime.now(timezone.utc)
    repository.record(
        Signal(
            source="InfoMoney",
            title="Resultado da loteria",
            url="https://example/loteria",
            published_at=now,
            collected_at=now,
        )
    )

    signals = client.get("/api/monitor/signals").json()
    all_signals = client.get("/api/monitor/signals?with_assets=false").json()
    sources = client.get("/api/monitor/sources").json()

    assert signals["total"] == 2
    assert all_signals["total"] == 3
    assert signals["items"][0]["assets"]
    assert sources["items"]


def test_sem_carteira_retorna_400(client, monkeypatch, tmp_path):
    monkeypatch.setattr(
        "api.services.monitor_service.portfolio_path", lambda: tmp_path / "nao.json"
    )

    response = client.get("/api/monitor/candidates")

    assert response.status_code == 400
    assert "Importe uma carteira" in response.json()["detail"]
