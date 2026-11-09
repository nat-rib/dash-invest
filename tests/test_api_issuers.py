from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

import api.dependencies as dependencies
from api.main import create_app
from src.domain.issuers import Issuer
from src.persistence.issuers import IssuerRepository


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DASH_INVEST_DB_PATH", str(tmp_path / "api.db"))
    dependencies.get_database.cache_clear()
    dependencies.get_repositories.cache_clear()
    with TestClient(create_app()) as test_client:
        yield test_client


def make_issuer(cnpj: str, name: str) -> Issuer:
    return Issuer(
        cnpj=cnpj,
        name=name,
        cvm_code="001023",
        updated_at=datetime(2025, 2, 19, tzinfo=timezone.utc),
    )


def repository() -> IssuerRepository:
    return IssuerRepository(dependencies.get_database())


def test_lista_e_busca_emissores(client):
    repository().upsert_many(
        [
            make_issuer("00.000.000/0001-91", "PETROBRAS"),
            make_issuer("11.111.111/0001-11", "VALE"),
        ]
    )

    body = client.get("/api/data/issuers", params={"query": "petro"}).json()

    assert body["total"] == 1
    assert body["items"][0]["name"] == "PETROBRAS"
    assert body["items"][0]["cnpj"] == "00000000000191"


def test_detalha_emissor_por_cnpj(client):
    repository().upsert(make_issuer("00.000.000/0001-91", "PETROBRAS"))

    body = client.get("/api/data/issuers/00.000.000/0001-91").json()

    assert body["name"] == "PETROBRAS"
    assert body["cvm_code"] == "001023"


def test_emissor_inexistente_retorna_404(client):
    response = client.get("/api/data/issuers/99.999.999/0001-99")
    assert response.status_code == 404
