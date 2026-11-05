from pathlib import Path

from fastapi.testclient import TestClient

import src.history as history_module
from api.main import app


def test_history_empty_database(tmp_path, monkeypatch):
    database = tmp_path / "empty.db"
    monkeypatch.setattr("api.main.portfolio_history", lambda: history_module.portfolio_history(database))
    monkeypatch.setattr("api.main.position_history", lambda: history_module.position_history(database))
    response = TestClient(app).get("/api/history")
    assert response.status_code == 200
    assert response.json()["wealth"] == []
    assert response.json()["positions"] == []
    assert database.exists()


def test_history_returns_recorded_values(tmp_path, monkeypatch):
    database = tmp_path / "history.db"
    with history_module._connection(database) as connection:
        cursor = connection.execute(
            "INSERT INTO snapshots (captured_at, source, total_brl) VALUES (?, ?, ?)",
            ("2026-11-04T12:00:00+00:00", "manual", 1234.56),
        )
        connection.execute(
            "INSERT INTO position_snapshots (snapshot_id, position_key, institution, name, asset_class, currency, value_brl) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (cursor.lastrowid, "bank|ABC|BRL", "bank", "ABC", "acao", "BRL", 1234.56),
        )
    monkeypatch.setattr("api.main.portfolio_history", lambda: history_module.portfolio_history(database))
    monkeypatch.setattr("api.main.position_history", lambda: history_module.position_history(database))
    response = TestClient(app).get("/api/history")
    assert response.status_code == 200
    payload = response.json()
    assert payload["wealth"][0]["Patrimônio BRL"] == 1234.56
    assert payload["positions"][0]["Posição"] == "bank|ABC|BRL"
