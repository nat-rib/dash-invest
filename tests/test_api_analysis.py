"""Testes de integração da análise da carteira (Fase 4)."""
import json

import pytest
from fastapi.testclient import TestClient

import api.dependencies as dependencies
from api.main import create_app

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
            "average_cost": "28.00",
            "current_price": "32.00",
            "currency": "BRL",
        },
        {
            "institution": "XP",
            "asset_class": "fii",
            "name": "FII Logístico",
            "quantity": "50",
            "average_cost": "90.00",
            "current_price": "100.00",
            "currency": "BRL",
        },
        {
            "institution": "Nomad",
            "asset_class": "etf",
            "name": "ETF Global",
            "quantity": "10",
            "average_cost": "100.00",
            "current_price": "120.00",
            "currency": "USD",
        },
        {
            "institution": "BancoB",
            "asset_class": "renda_fixa",
            "name": "Ativo USD Sem Conversão",
            "quantity": "1000",
            "average_cost": "4.00",
            "current_price": "5.00",
            "currency": "USD",
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
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def test_allocation_groups_and_shares(client):
    body = client.get("/api/analysis/allocation").json()
    assert body["known_positions"] == 2
    assert body["unknown_positions"] == 2  # USD sem conversão e CDB sem valor: nunca viram zero
    # XP = 3200 (PETR4) + 5000 (FII)
    assert body["total_brl"] == "8200.00"

    by_institution = {item["name"]: item for item in body["by_institution"]}
    assert set(by_institution) == {"XP"}
    assert float(by_institution["XP"]["value"]) == pytest.approx(8200.00)
    classes = {item["name"]: item["share"] for item in body["by_class"]}
    assert classes["acao"] < classes["fii"]


def test_concentration_top_and_comparable(client):
    body = client.get("/api/analysis/concentration").json()
    top_names = [item["name"] for item in body["top"]]
    assert top_names[0] == "FII Logístico"  # 5000 é o maior
    shares = {item["name"]: item["share"] for item in body["items"]}
    assert shares["Ativo USD Sem Conversão"] is None
    comparable = {item["name"]: item for item in body["comparable"]}
    petr = comparable["Petrobras PN"]
    assert petr["cost_total"] == "2800.00" and petr["current_value"] == "3200.00"


def test_positions_list_and_detail(client):
    listing = client.get("/api/portfolio/positions").json()
    assert listing["snapshot_date"] == "2026-03-31"
    assert len(listing["positions"]) == 4
    detail = client.get("/api/portfolio/positions/0").json()
    assert detail["name"] == "Petrobras PN"
    assert detail["quantity"] == "100"
    assert detail["gain_loss"] == "400.00"
    assert detail["unrealized_return"] is not None
    Campos_ausentes_explícitos = detail["indexer"] is None and detail["maturity_date"] is None
    assert Campos_ausentes_explícitos

    foreign = client.get("/api/portfolio/positions/2").json()
    assert foreign["currency"] == "USD"
    assert foreign["consolidated_brl"] is None  # sem conversão informada, não converte

    missing = client.get("/api/portfolio/positions/99")
    assert missing.status_code == 404


def test_allocation_without_snapshot_returns_400(client, tmp_path):
    (tmp_path / "portfolio.json").unlink()
    response = client.get("/api/analysis/allocation")
    assert response.status_code == 400
    assert "não encontrado" in response.json()["detail"].lower()
