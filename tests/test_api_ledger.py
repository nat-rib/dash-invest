"""Testes de integração dos contratos HTTP do Ledger (Fase 1)."""
from io import BytesIO
import json

import pytest
from fastapi.testclient import TestClient

import api.dependencies as dependencies
from api.main import create_app


SNAPSHOT_JSON = json.dumps({
    "schema_version": 1,
    "snapshot_date": "2026-01-31",
    "currency": "BRL",
    "positions": [
        {
            "institution": "Corretora A",
            "asset_class": "acao",
            "ticker": "PETR4",
            "name": "Petrobras PN",
            "quantity": "100",
            "average_cost": "30.00",
            "current_value": "3200.00",
            "currency": "BRL",
        },
        {
            "institution": "Banco B",
            "asset_class": "renda_fixa",
            "name": "Tesouro IPCA+ 2035",
            "quantity": "10",
            "average_cost": "4500.00",
            "current_value": "47000.00",
            "currency": "BRL",
        },
    ],
})


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DASH_INVEST_DB_PATH", str(tmp_path / "api.db"))
    monkeypatch.setenv("PORTFOLIO_PATH", str(tmp_path / "portfolio.json"))
    (tmp_path / "portfolio.json").write_text(SNAPSHOT_JSON, encoding="utf-8")
    dependencies.get_database.cache_clear()
    dependencies.get_repositories.cache_clear()
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def _migrate_snapshot(client: TestClient) -> None:
    response = client.post("/api/ledger/snapshot/import")
    assert response.status_code == 200, response.text


def _csv_upload(client: TestClient, *, endpoint: str, rows: str, mapping: dict) -> dict:
    files = {"file": ("extrato.csv", BytesIO(rows.encode("utf-8")), "text/csv")}
    data = {"mapping": json.dumps(mapping)}
    response = client.post(endpoint, files=files, data=data)
    assert response.status_code == 200, response.text
    return response.json()


def test_health_ok(client):
    assert client.get("/api/health").json()["status"] == "ok"


def test_snapshot_preview_lists_positions_without_writing(client):
    preview = client.post("/api/ledger/snapshot/preview")
    assert preview.status_code == 200
    body = preview.json()
    assert body["snapshot_date"] == "2026-01-31"
    assert {item["institution"] for item in body["positions"]} == {"Corretora A", "Banco B"}
    # A prévia não pode criar dados.
    state = client.get("/api/ledger/state").json()
    assert state["portfolios"] == [] and state["snapshots_count"] == 0


def test_snapshot_import_creates_portfolio_once(client):
    result = client.post("/api/ledger/snapshot/import")
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["instruments_saved"] == 2 and body["positions_saved"] == 2
    assert body["transactions_created"] == 0
    # Migração repetida continua idempotente e sem transações fictícias.
    repeat = client.post("/api/ledger/snapshot/import")
    assert repeat.status_code == 200
    state = client.get("/api/ledger/state").json()
    assert state["transactions_count"] == 0
    assert state["snapshots_count"] == 2


def test_instruments_create_duplicate_rejected_and_list_filter(client):
    _migrate_snapshot(client)
    created = client.post("/api/ledger/instruments", json={
        "name": "Fundo Imobiliário", "asset_class": "fii",
        "currency": "BRL", "ticker": "MXRF11",
    })
    assert created.status_code == 201, created.text
    instrument_id = created.json()["id"]

    duplicate = client.post("/api/ledger/instruments", json={
        "name": "Outro nome", "asset_class": "fii",
        "currency": "BRL", "ticker": "mxrf11",
    })
    assert duplicate.status_code == 409
    assert "ticker" in duplicate.json()["detail"]

    listing = client.get("/api/ledger/instruments", params={"q": "MXRF11"})
    assert [item["id"] for item in listing.json()] == [instrument_id]


CSV_ROWS = (
    "ID;Data;Operação;Ativo;Qtd;Preço;Valor;Moeda\n"
    "op-1;05/02/2026;Compra;PETR4;10;32,50;325,00;BRL\n"
    "op-2;05/02/2026;Aporte;;;;1.000,00;BRL\n"
)

CSV_MAPPING = {
    "institution": "Corretora C",
    "currency": "BRL",
    "delimiter": ";",
    "columns": {
        "external_id": "ID", "occurred_at": "Data", "transaction_type": "Operação",
        "instrument_id": "Ativo", "quantity": "Qtd", "unit_price": "Preço",
        "amount": "Valor", "currency": "Moeda",
    },
    "instrument_map": {},
}


def test_csv_import_requires_imported_portfolio(client):
    files = {"file": ("extrato.csv", BytesIO(CSV_ROWS.encode()), "text/csv")}
    response = client.post(
        "/api/ledger/csv/preview", files=files, data={"mapping": json.dumps(CSV_MAPPING)},
    )
    assert response.status_code == 400
    assert "migre o snapshot" in response.json()["detail"].lower()


def test_csv_preview_does_not_persist_and_import_is_idempotent(client):
    _migrate_snapshot(client)
    instrument_request = client.get("/api/ledger/instruments", params={"q": "PETR4"})
    petr4_id = instrument_request.json()[0]["id"]
    mapping = {**CSV_MAPPING, "instrument_map": {"PETR4": petr4_id}}

    preview = _csv_upload(client, endpoint="/api/ledger/csv/preview", rows=CSV_ROWS, mapping=mapping)
    assert preview["parsed"] == 2
    types = [item["transaction_type"] for item in preview["transactions"]]
    assert types == ["BUY", "DEPOSIT"]
    state = client.get("/api/ledger/state").json()
    assert state["transactions_count"] == 0  # prévia não persiste

    first = _csv_upload(client, endpoint="/api/ledger/csv/import", rows=CSV_ROWS, mapping=mapping)
    assert first["inserted"] == 2 and first["skipped_duplicates"] == 0
    second = _csv_upload(client, endpoint="/api/ledger/csv/import", rows=CSV_ROWS, mapping=mapping)
    assert second["inserted"] == 0 and second["skipped_duplicates"] == 2

    listing = client.get(
        "/api/ledger/transactions", params={"limit": 100, "institution": "Corretora C"},
    )
    assert listing.json()["meta"]["total"] == 2
    buy = [item for item in listing.json()["items"] if item["transaction_type"] == "BUY"][0]
    assert buy["instrument_label"] == "Petrobras PN · PETR4" or "Petrobras" in buy["instrument_label"]


def test_transactions_pagination_and_filters(client):
    _migrate_snapshot(client)
    instrument_request = client.get("/api/ledger/instruments", params={"q": "PETR4"})
    petr4_id = instrument_request.json()[0]["id"]
    mapping = {**CSV_MAPPING, "instrument_map": {"PETR4": petr4_id}}
    _csv_upload(client, endpoint="/api/ledger/csv/import", rows=CSV_ROWS, mapping=mapping)

    page = client.get("/api/ledger/transactions", params={"limit": 1, "offset": 0})
    assert page.json()["meta"]["total"] == 2
    assert len(page.json()["items"]) == 1
    filtered = client.get(
        "/api/ledger/transactions", params={"type": "BUY", "instrument_id": petr4_id},
    )
    assert filtered.json()["meta"]["total"] == 1
    deposit = client.get("/api/ledger/transactions", params={"type": "DEPOSIT"})
    assert deposit.json()["items"][0]["amount"] == "1000.00"


TRANSFER_OUT_ROWS = (
    "ID;Data;Operação;Valor;Moeda\n"
    "out-1;05/02/2026;Transferencia Saida;1500,00;BRL\n"
)

TRANSFER_IN_ROWS = (
    "ID;Data;Operação;Valor;Moeda\n"
    "in-1;06/02/2026;Transferencia Entrada;1500,00;BRL\n"
)

TRANSFER_COLUMNS = {
    "external_id": "ID", "occurred_at": "Data", "transaction_type": "Operação",
    "amount": "Valor", "currency": "Moeda",
}


def test_transfer_suggestions_and_manual_confirmation(client):
    _migrate_snapshot(client)
    out_mapping = {"institution": "Corretora C", "currency": "BRL", "delimiter": ";",
                   "columns": TRANSFER_COLUMNS}
    in_mapping = {"institution": "Banco B", "currency": "BRL", "delimiter": ";",
                  "columns": TRANSFER_COLUMNS}
    _csv_upload(client, endpoint="/api/ledger/csv/import", rows=TRANSFER_OUT_ROWS, mapping=out_mapping)
    _csv_upload(client, endpoint="/api/ledger/csv/import", rows=TRANSFER_IN_ROWS, mapping=in_mapping)

    suggestions = client.get("/api/ledger/transfers/suggestions").json()
    assert len(suggestions["suggested_pairs"]) == 1
    suggestion = suggestions["suggested_pairs"][0]
    out_id = suggestion["transfer_out"]["id"]
    in_id = suggestion["transfer_in"]["id"]
    assert suggestion["amount_delta"] == "0.00"

    confirmed = client.post("/api/ledger/transfers/confirm", json={
        "transfer_out_id": out_id, "transfer_in_id": in_id,
        "confirmation_source": "manual",
    })
    assert confirmed.status_code == 200, confirmed.text

    # Depois de confirmar, nenhuma sugestão restante para o mesmo par.
    after = client.get("/api/ledger/transfers/suggestions").json()
    assert after["suggested_pairs"] == []

    double = client.post("/api/ledger/transfers/confirm", json={
        "transfer_out_id": out_id, "transfer_in_id": in_id,
    })
    assert double.status_code == 200  # idempotente para o mesmo par
    conflicting = client.post("/api/ledger/transfers/confirm", json={
        "transfer_out_id": out_id,
        "transfer_in_id": "a79a0873-77d3-5b6e-b9bb-1a10d04a321f",
    })
    assert conflicting.status_code == 400


def test_invalid_csv_returns_error_without_persisting(client):
    _migrate_snapshot(client)
    files = {"file": ("extrato.csv", BytesIO(b"Nova;Data\nx;30/02/2026\n"), "text/csv")}
    mapping = {**CSV_MAPPING, "columns": {"occurred_at": "Data", "transaction_type": "Operação"}}
    response = client.post("/api/ledger/csv/preview", files=files, data={"mapping": json.dumps(mapping)})
    assert response.status_code == 422
    listing = client.get("/api/ledger/transactions")
    assert listing.json()["meta"]["total"] == 0
