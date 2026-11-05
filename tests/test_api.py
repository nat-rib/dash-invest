from fastapi.testclient import TestClient
from api import main

def test_health_endpoint():
    response = TestClient(main.app).get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_overview_uses_snapshot_without_inventing_returns(tmp_path, monkeypatch):
    snapshot = tmp_path / "portfolio.json"
    snapshot.write_text("""{
      "schema_version": 1, "snapshot_date": "2026-11-01", "currency": "BRL",
      "positions": [
        {"institution":"Corretora A","asset_class":"acao","ticker":"AAA3","name":"Ativo A","quantity":10,"average_cost":8,"current_price":10,"currency":"BRL"},
        {"institution":"Banco B","asset_class":"renda_fixa","name":"CDB B","current_value":500,"currency":"BRL"}
      ]
    }""", encoding="utf-8")
    monkeypatch.setattr(main, "PORTFOLIO_PATH", snapshot)
    body = TestClient(main.app).get("/api/overview").json()
    assert body["has_snapshot"] is True
    assert body["metrics"]["total_brl"] == 600
    assert body["metrics"]["assets"] == 2
    assert body["performance"]["twr"] is None
    assert body["performance"]["xirr"] is None

def test_overview_reports_missing_snapshot(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "PORTFOLIO_PATH", tmp_path / "missing.json")
    body = TestClient(main.app).get("/api/overview").json()
    assert body["has_snapshot"] is False
