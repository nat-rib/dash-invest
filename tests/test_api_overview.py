"""Testes de integração da visão geral consolidada."""
from datetime import date
from decimal import Decimal
from io import BytesIO
import json

import pytest
from fastapi.testclient import TestClient

import api.dependencies as dependencies
from api.main import create_app
from src.domain.performance import TwrPeriod, calculate_twr

SNAPSHOT = {
    "schema_version": 1,
    "snapshot_date": "2020-01-31",
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
            "name": "ETF Global sem conversão",
            "quantity": "10",
            "average_cost": "100.00",
            "current_price": "120.00",
            "currency": "USD",
        },
    ],
}

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


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DASH_INVEST_DB_PATH", str(tmp_path / "overview.db"))
    monkeypatch.setenv("PORTFOLIO_PATH", str(tmp_path / "portfolio.json"))
    (tmp_path / "portfolio.json").write_text(json.dumps(SNAPSHOT), encoding="utf-8")
    dependencies.get_database.cache_clear()
    dependencies.get_repositories.cache_clear()
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def _csv_upload(client: TestClient, rows: str, mapping: dict) -> None:
    response = client.post(
        "/api/ledger/csv/import",
        files={"file": ("extrato.csv", BytesIO(rows.encode()), "text/csv")},
        data={"mapping": json.dumps(mapping)},
    )
    assert response.status_code == 200, response.text


def test_overview_consolidates_snapshot_quality_and_alerts(client):
    body = client.get("/api/overview").json()
    assert body["snapshot"]["available"] is True
    assert body["snapshot"]["snapshot_date"] == "2020-01-31"
    assert body["total_brl"] == "8200.00"
    assert body["known_positions"] == 2
    assert body["unknown_positions"] == 1
    assert body["positions_count"] == 3
    assert body["quality"]["level"] == "partial"
    assert "1" in body["quality"]["message"]

    top = body["top_positions"][0]
    assert top["name"] == "FII Logístico"
    assert Decimal(top["share"]) > Decimal("0.60")
    assert top["concentration_level"] == "high"

    alert_ids = {item["id"] for item in body["alerts"]}
    assert "unknown-positions" in alert_ids
    assert "concentration-1" in alert_ids
    assert "stale-snapshot" in alert_ids
    assert "ledger-empty" in alert_ids

    assert body["benchmark"]["available"] is False
    assert "Benchmark" in body["benchmark"]["reason"]
    assert body["performance"]["available"] is False
    assert "migre" in body["performance"]["reason"].lower()


def test_overview_returns_twr_when_periods_are_stored(client):
    assert client.post("/api/ledger/snapshot/import").status_code == 200
    periods = [
        {"start_date": "2026-01-01", "end_date": "2026-06-30",
         "start_value": "1000", "end_value_after_flows": "1200", "net_external_flow": "100"},
        {"start_date": "2026-06-30", "end_date": "2026-12-31",
         "start_value": "1200", "end_value_after_flows": "1300", "net_external_flow": "0"},
    ]
    assert client.post("/api/performance/valuations", json={"periods": periods}).status_code == 200
    reference = calculate_twr([
        TwrPeriod(date(2026, 1, 1), date(2026, 6, 30), Decimal("1000"), Decimal("1200"), Decimal("100")),
        TwrPeriod(date(2026, 6, 30), date(2026, 12, 31), Decimal("1200"), Decimal("1300"), Decimal("0")),
    ])

    body = client.get("/api/overview").json()
    assert body["performance"]["available"] is True
    assert body["performance"]["metric"] == "TWR"
    assert Decimal(body["performance"]["rate"]) == reference.rate
    assert body["performance"]["periods"] == 2


def test_overview_without_snapshot_keeps_ledger_visible(client, tmp_path):
    (tmp_path / "portfolio.json").unlink()
    response = client.get("/api/overview")
    assert response.status_code == 200
    body = response.json()
    assert body["snapshot"]["available"] is False
    assert body["total_brl"] is None
    assert body["quality"]["level"] == "unknown"
    assert any(item["id"] == "snapshot-unavailable" for item in body["alerts"])
    assert body["ledger"]["database_path"]


def test_overview_keeps_total_unavailable_when_nothing_is_consolidated(client, tmp_path):
    (tmp_path / "portfolio.json").write_text(json.dumps({
        "schema_version": 1,
        "snapshot_date": "2026-01-31",
        "currency": "BRL",
        "positions": [{
            "institution": "Nomad",
            "asset_class": "etf",
            "name": "Ativo USD sem conversão",
            "quantity": "10",
            "average_cost": "100.00",
            "current_price": "120.00",
            "currency": "USD",
        }],
    }), encoding="utf-8")

    body = client.get("/api/overview").json()
    assert body["total_brl"] is None
    assert body["known_positions"] == 0
    assert body["unknown_positions"] == 1
    assert body["quality"]["level"] == "unknown"
    assert any(item["id"] == "no-known-value" for item in body["alerts"])


def test_overview_flags_unlinked_transfers(client):
    assert client.post("/api/ledger/snapshot/import").status_code == 200
    _csv_upload(client, TRANSFER_OUT_ROWS, {
        "institution": "Corretora C", "currency": "BRL", "delimiter": ";",
        "columns": TRANSFER_COLUMNS,
    })
    _csv_upload(client, TRANSFER_IN_ROWS, {
        "institution": "Banco B", "currency": "BRL", "delimiter": ";",
        "columns": TRANSFER_COLUMNS,
    })

    body = client.get("/api/overview").json()
    assert body["ledger"]["unlinked_transfer_events"] == 2
    assert any(item["id"] == "unlinked-transfers" for item in body["alerts"])
