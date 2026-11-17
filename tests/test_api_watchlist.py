import json

import pytest
from fastapi.testclient import TestClient

import api.dependencies as dependencies
from api.main import create_app
from src.persistence.database import SQLiteDatabase


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DASH_INVEST_DB_PATH", str(tmp_path / "api.db"))
    dependencies.get_database.cache_clear()
    dependencies.get_repositories.cache_clear()
    with TestClient(create_app()) as test_client:
        yield test_client


def test_watchlist_crud(client):
    created = client.post(
        "/api/watchlist",
        json={
            "asset_key": "ticker:PETR4",
            "name": "Petrobras",
            "asset_class": "acao",
            "note": "acompanhar dividendos",
        },
    )

    assert created.status_code == 201
    body = client.get("/api/watchlist").json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "Petrobras"
    assert body["items"][0]["note"] == "acompanhar dividendos"

    # Upsert não duplica.
    client.post(
        "/api/watchlist",
        json={"asset_key": "ticker:PETR4", "name": "Petrobras PN", "asset_class": "acao"},
    )
    body = client.get("/api/watchlist").json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "Petrobras PN"

    removed = client.delete("/api/watchlist/ticker:PETR4")
    assert removed.status_code == 204
    assert client.get("/api/watchlist").json()["total"] == 0

    assert client.delete("/api/watchlist/ticker:PETR4").status_code == 404
