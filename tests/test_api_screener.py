from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

import api.dependencies as dependencies
from api.main import create_app
from src.domain.issuers import Issuer
from src.domain.observations import Observation, QualityStatus
from src.persistence.issuers import IssuerRepository
from src.persistence.observations import ObservationRepository

REFERENCE = date(2024, 12, 31)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DASH_INVEST_DB_PATH", str(tmp_path / "api.db"))
    dependencies.get_database.cache_clear()
    dependencies.get_repositories.cache_clear()
    with TestClient(create_app()) as test_client:
        yield test_client


def add_issuer(cnpj: str, name: str, revenue: float, net: float, equity: float, assets: float):
    database = dependencies.get_database()
    IssuerRepository(database).upsert(Issuer(cnpj=cnpj, name=name))
    repository = ObservationRepository(database)
    values = {
        "revenue": revenue,
        "net_income": net,
        "equity": equity,
        "total_assets": assets,
    }
    repository.record_many(
        [
            Observation(
                provider="cvm",
                metric=metric,
                instrument_id=f"cnpj:{cnpj}",
                value=Decimal(str(value)),
                currency="BRL",
                reference_date=REFERENCE,
                parser_version="test",
                quality_status=QualityStatus.VERIFIED,
            )
            for metric, value in values.items()
        ]
    )


def test_screener_ordena_por_roe(client):
    add_issuer("00000000000191", "ALTA", 1000, 200, 500, 2000)
    add_issuer("11111111111111", "BAIXA", 1000, 50, 500, 2000)

    body = client.get("/api/screener", params={"sort_by": "roe"}).json()

    assert body["total"] == 2
    assert [item["name"] for item in body["items"]] == ["ALTA", "BAIXA"]
    assert body["items"][0]["roe"] == pytest.approx(0.4)
    assert body["items"][0]["net_margin"] == pytest.approx(0.2)


def test_screener_filtra_por_roe_minimo(client):
    add_issuer("00000000000191", "ALTA", 1000, 200, 500, 2000)
    add_issuer("11111111111111", "BAIXA", 1000, 50, 500, 2000)

    body = client.get("/api/screener", params={"min_roe": 0.2}).json()

    assert body["total"] == 1
    assert body["items"][0]["name"] == "ALTA"


def test_dcf_endpoint(client):
    body = client.post(
        "/api/valuation/dcf",
        json={
            "base_cash_flow": 100,
            "growth_rate": 0.1,
            "years": 2,
            "terminal_growth": 0.02,
            "discount_rate": 0.1,
        },
    ).json()

    assert body["enterprise_value"] == pytest.approx(1475.0)
    assert len(body["projections"]) == 2


def test_dcf_endpoint_rejeita_premissas_invalidas(client):
    response = client.post(
        "/api/valuation/dcf",
        json={
            "base_cash_flow": 100,
            "growth_rate": 0.1,
            "years": 2,
            "terminal_growth": 0.1,
            "discount_rate": 0.05,
        },
    )

    assert response.status_code == 422
