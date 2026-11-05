"""Testes de integração da importação de carteira (Fase 3)."""
import json

import pytest
from fastapi.testclient import TestClient

import api.dependencies as dependencies
from api.main import create_app

VALID_SNAPSHOT = {
    "schema_version": 1,
    "snapshot_date": "2026-02-28",
    "currency": "BRL",
    "positions": [
        {
            "institution": "A",
            "asset_class": "acao",
            "name": "Ativo Um",
            "quantity": "10",
            "current_value": "100.00",
            "currency": "BRL",
        },
    ],
}

filename_json = "portfolio.json"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DASH_INVEST_DB_PATH", str(tmp_path / "api.db"))
    monkeypatch.setenv("PORTFOLIO_PATH", str(tmp_path / "portfolio.json"))
    (tmp_path / "portfolio.json").write_text(json.dumps(VALID_SNAPSHOT), encoding="utf-8")
    dependencies.get_database.cache_clear()
    dependencies.get_repositories.cache_clear()
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def _upload(client, payload, *, confirm=False, filename="portfolio.json"):
    data = {"confirm_replacement": "true"} if confirm else {}
    return client.post(
        f"/api/import/snapshot/{'confirm' if confirm else 'preview'}",
        files={"file": (filename, json.dumps(payload).encode(), "application/json")},
        data=data,
    )


def test_preview_valid_and_invalid(client):
    ok = _upload(client, VALID_SNAPSHOT)
    assert ok.status_code == 200
    body = ok.json()
    assert body["valid"] is True and body["positions"][0]["name"] == "Ativo Um"
    assert body["snapshot_date"] == "2026-02-28"

    invalid = _upload(client, {"schema_version": 1, "snapshot_date": "2026-02-28", "currency": "BRL", "positions": []})
    assert invalid.status_code == 200
    assert invalid.json()["valid"] is False
    assert invalid.json()["validation_errors"]


def test_invalid_file_never_replaces_snapshot(client):
    response = _upload(client, {"schema_version": 1, "snapshot_date": "2026-02-28", "currency": "BRL", "positions": []})
    assert response.status_code == 200
    import os
    from pathlib import Path
    path = Path(os.environ["PORTFOLIO_PATH"])
    content = json.loads(path.read_text())
    assert content["positions"] == VALID_SNAPSHOT["positions"]


def test_confirm_requires_explicit_confirmation(client):
    response = client.post(
        "/api/import/snapshot/confirm",
        files={"file": (filename_json, json.dumps(VALID_SNAPSHOT).encode(), "application/json")},
        data={},
    )
    assert response.status_code == 400
    assert "confirmação" in response.json()["detail"].lower()


def test_confirm_replaces_snapshot_atomically(client):
    new_snapshot = {**VALID_SNAPSHOT, "snapshot_date": "2026-03-31", "positions": [
        {**VALID_SNAPSHOT["positions"][0], "name": "Ativo Dois", "quantity": "5"},
    ]}
    response = _upload(client, new_snapshot, confirm=True)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["positions"] == 1 and body["snapshot_date"] == "2026-03-31"

    import os
    from pathlib import Path
    stored = json.loads(Path(os.environ["PORTFOLIO_PATH"]).read_text())
    assert stored["positions"][0]["name"] == "Ativo Dois"

    # A carteira legado no ledger continua funcionando: nenhuma transação inventada.
    state = client.get("/api/ledger/state").json()
    assert state["transactions_count"] == 0


def test_preview_flags_duplicate_positions(client):
    duplicated = {
        **VALID_SNAPSHOT,
        "positions": VALID_SNAPSHOT["positions"] * 2,
    }
    body = _upload(client, duplicated).json()
    assert body["valid"] is True
    assert body["duplicates"], "duplicadas devem ser sinalizadas na prévia"


def test_invalid_json_payload(client):
    response = client.post(
        "/api/import/snapshot/preview",
        files={"file": ("a.json", b"{invalid", "application/json")},
    )
    assert response.status_code == 200
    assert response.json()["valid"] is False
