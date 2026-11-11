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

CNPJ = "00000000000191"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DASH_INVEST_DB_PATH", str(tmp_path / "api.db"))
    monkeypatch.delenv("AI_BASE_URL", raising=False)
    monkeypatch.delenv("AI_API_KEY", raising=False)
    dependencies.get_database.cache_clear()
    dependencies.get_repositories.cache_clear()
    with TestClient(create_app()) as test_client:
        yield test_client


def seed() -> None:
    database = dependencies.get_database()
    IssuerRepository(database).upsert(Issuer(cnpj=CNPJ, name="Empresa Teste"))
    values = {
        "revenue": (1000, date(2023, 12, 31)),
        "net_income": (100, date(2023, 12, 31)),
        "equity": (500, date(2023, 12, 31)),
        "total_assets": (2000, date(2023, 12, 31)),
    }
    observations = [
        Observation(
            provider="cvm",
            metric=metric,
            instrument_id=f"cnpj:{CNPJ}",
            value=Decimal(str(value)),
            currency="BRL",
            reference_date=reference,
            parser_version="test",
            quality_status=QualityStatus.VERIFIED,
            source_document="http://doc/2023",
        )
        for metric, (value, reference) in values.items()
    ]
    observations.append(
        Observation(
            provider="cvm",
            metric="revenue",
            instrument_id=f"cnpj:{CNPJ}",
            value=Decimal("1200"),
            currency="BRL",
            reference_date=date(2024, 12, 31),
            parser_version="test",
            quality_status=QualityStatus.VERIFIED,
            source_document="http://doc/2024",
        )
    )
    ObservationRepository(database).record_many(observations)


def test_relatorio_de_pesquisa(client):
    seed()

    body = client.get(f"/api/research/{CNPJ}").json()

    assert body["name"] == "Empresa Teste"
    assert body["gateway"] == "deterministic"
    assert body["narrative"]
    keys = {claim["key"] for claim in body["claims"]}
    assert {"revenue", "net_income", "net_margin", "roe", "revenue_growth"} <= keys
    assert "http://doc/2024" in body["sources"]
    assert body["limitations"]


def test_emissor_inexistente_retorna_404(client):
    response = client.get("/api/research/99999999999999")
    assert response.status_code == 404
