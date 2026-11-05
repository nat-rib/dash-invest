"""Testes de integração do histórico e do mercado (Fase 5)."""
from datetime import date
import json

import pytest
from fastapi.testclient import TestClient

import api.dependencies as dependencies
from api.main import create_app
from src.market_data import Quote

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
            "current_price": "30.00",
            "currency": "BRL",
        },
        {
            "institution": "XP",
            "asset_class": "fii",
            "name": "FII Sem Símbolo",
            "quantity": "10",
            "average_cost": "90.00",
            "current_price": "95.00",
            "currency": "BRL",
        },
    ],
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DASH_INVEST_DB_PATH", str(tmp_path / "api.db"))
    monkeypatch.setenv("PORTFOLIO_PATH", str(tmp_path / "portfolio.json"))
    monkeypatch.setenv("HISTORY_DB_PATH", str(tmp_path / "history.db"))
    (tmp_path / "portfolio.json").write_text(json.dumps(SNAPSHOT), encoding="utf-8")
    dependencies.get_database.cache_clear()
    dependencies.get_repositories.cache_clear()
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def _quote(price: float) -> Quote:
    return Quote(symbol="PETR4.SAO", price=price, as_of=date(2026, 4, 1))


def _ok_client(monkeypatch):
    monkeypatch.setenv("ALPHA_VANTAGE_API_KEY", "test-key")
    from src import market_data as md

    monkeypatch.setattr(md.AlphaVantageClient, "quote_position", lambda self, position: _quote(32.00))
    return md


def test_historico_vazio(client):
    body = client.get("/api/history/portfolio").json()
    assert body["points"] == []
    assert "rentabilidade" in body["notice"]


def test_registrar_snapshot_manual_e_consultar(client):
    recorded = client.post("/api/history/snapshot")
    assert recorded.status_code == 200, recorded.text
    body = client.get("/api/history/portfolio").json()
    assert len(body["points"]) == 1
    assert body["points"][0]["source"] == "manual"
    assert float(body["points"][0]["total_brl"]) == pytest.approx(3000.00 + 950.00)

    keys = client.get("/api/history/positions").json()["keys"]
    assert any("PETR4" in key for key in keys)
    detail = client.get(f"/api/history/positions/{keys[0]}").json()
    assert detail["points"][0]["currency"] == "BRL"
    assert detail["points"][0]["value_brl"] is not None


def test_market_positions_are_updatable_only(client):
    positions = client.get("/api/market/positions").json()
    assert [item["symbol"] for item in positions] == ["PETR4.SAO"]
    assert positions[0]["name"] == "Petrobras PN"


def test_mercado_exige_chave(client, monkeypatch):
    monkeypatch.delenv("ALPHA_VANTAGE_API_KEY", raising=False)
    response = client.post("/api/market/quotes/preview")
    assert response.status_code == 503
    assert "ALPHA_VANTAGE_API_KEY" in response.json()["detail"]


def test_preview_nao_altera_snapshot_e_registra_historico(client, monkeypatch):
    _ok_client(monkeypatch)
    preview = client.post("/api/market/quotes/preview")
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["quotes"][0]["price"] == "32.0"
    changed = [item for item in body["positions"] if item["changed"]]
    assert len(changed) == 1 and changed[0]["current_price"] == "32.0"

    # O arquivo portfolio.json não pode ser alterado pela prévia.
    import os
    stored = json.loads((open(os.environ["PORTFOLIO_PATH"]).read()))
    assert stored["positions"][0]["current_price"] == "30.00"
    # Prévia registra série no histórico (fonte alpha_vantage).
    history = client.get("/api/history/portfolio").json()["points"]
    assert any(point["source"] == "alpha_vantage" for point in history)


def test_confirma_aplica_precos(client, monkeypatch):
    _ok_client(monkeypatch)
    confirmed = client.post("/api/market/quotes/confirm")
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["updated"] == 1

    import os
    stored = json.loads((open(os.environ["PORTFOLIO_PATH"]).read()))
    assert bool(stored["positions"][0]["current_price"] in (32.0, 32.00, "32.0"))


def test_market_history_erro_do_provedor(client, monkeypatch):
    _ok_client(monkeypatch)
    from src import market_data as md

    def failing(self, position):
        raise md.MarketDataError("Histórico indisponível para PETR4.SAO.")

    monkeypatch.setattr(md.AlphaVantageClient, "daily_history_position", failing)
    response = client.get("/api/market/history/0")
    assert response.status_code == 200
    assert response.json()["unavailable_reason"]


def test_market_history_endpoint_503_sem_chave(client, monkeypatch):
    monkeypatch.delenv("ALPHA_VANTAGE_API_KEY", raising=False)
    response = client.get("/api/market/history/0")
    assert response.status_code == 503
