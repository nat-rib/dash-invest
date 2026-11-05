"""Testes de integração dos contratos HTTP de Rentabilidade (Fase 2)."""
from datetime import date
from decimal import Decimal
import json

import pytest
from fastapi.testclient import TestClient

import api.dependencies as dependencies
from api.main import create_app
from src.domain.performance import (
    DatedCashFlow, TwrPeriod, calculate_twr, calculate_xirr,
)

SNAPSHOT_JSON = json.dumps({
    "schema_version": 1,
    "snapshot_date": "2026-01-31",
    "currency": "BRL",
    "positions": [
        {
            "institution": "Corretora A",
            "asset_class": "acao",
            "name": "Ativo",
            "quantity": "1",
            "average_cost": "1.00",
            "current_value": "1.00",
            "currency": "BRL",
        },
    ],
})

CSV_MAPPING = {
    "institution": "X", "currency": "BRL", "delimiter": ";",
    "columns": {
        "external_id": "ID", "occurred_at": "Data", "transaction_type": "Operao",
        "amount": "Valor", "currency": "Moeda",
    },
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DASH_INVEST_DB_PATH", str(tmp_path / "perf.db"))
    monkeypatch.setenv("PORTFOLIO_PATH", str(tmp_path / "portfolio.json"))
    (tmp_path / "portfolio.json").write_text(SNAPSHOT_JSON, encoding="utf-8")
    dependencies.get_database.cache_clear()
    dependencies.get_repositories.cache_clear()
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def _import_snapshot(client):
    assert client.post("/api/ledger/snapshot/import").status_code == 200


def test_flows_empty_before_any_transaction(client):
    _import_snapshot(client)
    body = client.get("/api/performance/flows").json()
    assert body["flows"] == []
    assert body["currency"] == "BRL"
    assert body["unavailable_reason"] is None


def test_flows_error_is_reason_not_http_error(client):
    _import_snapshot(client)
    response = client.post(
        "/api/ledger/csv/import",
        files={"file": ("a.csv", b"ID;Data;Operao;Valor;Moeda\nx;05/02/2026;Aporte;100;USD\n", "text/csv")},
        data={"mapping": json.dumps(CSV_MAPPING)},
    )
    assert response.status_code == 200, response.text
    body = client.get("/api/performance/flows").json()
    assert body["flows"] == []
    assert "FX explícito" in (body["unavailable_reason"] or "")


def test_flows_lists_in_investor_perspective(client):
    _import_snapshot(client)
    rows = (
        "ID;Data;Operao;Valor;Moeda\n"
        "x;05/02/2026;Aporte;1000,00;BRL\n"
        "y;06/02/2026;Retirada;400,00;BRL\n"
    )
    response = client.post(
        "/api/ledger/csv/import",
        files={"file": ("a.csv", rows.encode(), "text/csv")},
        data={"mapping": json.dumps(CSV_MAPPING)},
    )
    assert response.status_code == 200, response.text
    body = client.get("/api/performance/flows").json()
    assert [item["amount"] for item in body["flows"]] == ["-1000.00", "400.00"]


def test_xirr_matches_domain_reference(client):
    _import_snapshot(client)
    client.post(
        "/api/ledger/csv/import",
        files={"file": ("a.csv", b"ID;Data;Operao;Valor;Moeda\nx;05/02/2026;Aporte;1000,00;BRL\n", "text/csv")},
        data={"mapping": json.dumps(CSV_MAPPING)},
    )
    reference = calculate_xirr(
        [DatedCashFlow(date(2026, 2, 5), Decimal("-1000"))],
        terminal_value=Decimal("1100"),
        terminal_date=date(2027, 2, 5),
    )
    response = client.post("/api/performance/xirr/calculate", json={
        "terminal_value": "1100", "terminal_date": "2027-02-05",
    })
    assert response.status_code == 200, response.text
    assert Decimal(response.json()["annual_rate"]) == reference


def test_xirr_unavailable_when_no_flows(client):
    _import_snapshot(client)
    response = client.post("/api/performance/xirr/calculate", json={
        "terminal_value": "1100", "terminal_date": "2027-02-05",
    })
    assert response.status_code == 422
    assert "indisponível" in response.json()["detail"]


def test_twr_valuations_roundtrip_and_calculate(client):
    _import_snapshot(client)
    assert client.get("/api/performance/twr").json()["periods"] == []

    periods = [
        {"start_date": "2026-01-01", "end_date": "2026-06-30",
         "start_value": "1000", "end_value_after_flows": "1200", "net_external_flow": "100"},
        {"start_date": "2026-06-30", "end_date": "2026-12-31",
         "start_value": "1200", "end_value_after_flows": "1300", "net_external_flow": "0"},
    ]
    saved = client.post("/api/performance/valuations", json={"periods": periods})
    assert saved.status_code == 200, saved.text
    assert saved.json()["saved"] == 2

    reference = calculate_twr([
        TwrPeriod(
            date(2026, 1, 1), date(2026, 6, 30), Decimal("1000"), Decimal("1200"), Decimal("100")
        ),
        TwrPeriod(
            date(2026, 6, 30), date(2026, 12, 31), Decimal("1200"), Decimal("1300"), Decimal("0")
        ),
    ])
    result = client.post("/api/performance/twr/calculate", json={})
    assert result.status_code == 200, result.text
    assert Decimal(result.json()["rate"]) == reference.rate
    assert result.json()["periods"] == 2

    explicit = client.post("/api/performance/twr/calculate", json={"periods": periods[:1]})
    assert explicit.status_code == 200
    assert explicit.json()["periods"] == 1


def test_twr_rejects_disconnected_periods(client):
    _import_snapshot(client)
    periods = [
        {"start_date": "2026-01-01", "end_date": "2026-06-30",
         "start_value": "1000", "end_value_after_flows": "1200", "net_external_flow": "0"},
        {"start_date": "2026-07-02", "end_date": "2026-12-31",
         "start_value": "1200", "end_value_after_flows": "1300", "net_external_flow": "0"},
    ]
    response = client.post("/api/performance/twr/calculate", json={"periods": periods})
    assert response.status_code == 422
    assert "incontíguos" in response.json()["detail"] or "contíguos" in response.json()["detail"]


def test_twr_requires_periods(client):
    _import_snapshot(client)
    response = client.post("/api/performance/twr/calculate", json={})
    assert response.status_code == 422
    assert "indisponível" in response.json()["detail"]


def test_without_portfolio_migration_http_400(client):
    response = client.get("/api/performance/flows")
    assert response.status_code == 400
    assert "migre" in response.json()["detail"].lower()
