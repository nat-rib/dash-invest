from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

import api.dependencies as dependencies
from api.main import create_app
from src.domain.observations import Observation
from src.persistence.observations import ObservationRepository


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DASH_INVEST_DB_PATH", str(tmp_path / "api.db"))
    dependencies.get_database.cache_clear()
    dependencies.get_repositories.cache_clear()
    with TestClient(create_app()) as test_client:
        yield test_client


def make_observation(
    *,
    metric: str = "revenue",
    value: str = "1000",
    reference_date: date = date(2024, 12, 31),
    published_at: datetime = datetime(2025, 2, 19, tzinfo=timezone.utc),
) -> Observation:
    return Observation(
        provider="cvm",
        metric=metric,
        instrument_id="cnpj:00000000000191",
        value=Decimal(value),
        currency="BRL",
        reference_date=reference_date,
        published_at=published_at,
        parser_version="cvm-dfp-v1",
    )


def repository() -> ObservationRepository:
    return ObservationRepository(dependencies.get_database())


def test_lista_e_filtra_observacoes(client):
    repository().record_many(
        [make_observation(metric="revenue"), make_observation(metric="net_income", value="100")]
    )

    body = client.get(
        "/api/data/observations",
        params={"provider": "cvm", "metric": "revenue", "instrument_id": "cnpj:00000000000191"},
    ).json()

    assert body["total"] == 1
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["metric"] == "revenue"
    assert float(item["value"]) == 1000
    assert item["currency"] == "BRL"
    assert item["instrument_id"] == "cnpj:00000000000191"
    assert item["published_at"].startswith("2025-02-19")


def test_pagina_resultados(client):
    repository().record_many(
        [
            make_observation(metric="revenue"),
            make_observation(metric="net_income", value="100"),
            make_observation(metric="equity", value="500"),
        ]
    )

    body = client.get("/api/data/observations", params={"limit": 2, "offset": 1}).json()

    assert body["total"] == 3
    assert len(body["items"]) == 2


def test_serie_ordenada_ignora_superseded(client):
    repo = repository()
    repo.record(
        make_observation(
            value="900",
            reference_date=date(2023, 12, 31),
            published_at=datetime(2024, 2, 1, tzinfo=timezone.utc),
        )
    )
    repo.record(make_observation(value="1000"))
    repo.record(
        make_observation(
            value="1100",
            published_at=datetime(2025, 3, 20, tzinfo=timezone.utc),
        )
    )

    body = client.get(
        "/api/data/observations/series",
        params={
            "provider": "cvm",
            "metric": "revenue",
            "instrument_id": "cnpj:00000000000191",
        },
    ).json()

    assert [point["reference_date"] for point in body["points"]] == ["2023-12-31", "2024-12-31"]
    assert [float(point["value"]) for point in body["points"]] == [900, 1100]


def test_include_superseded_traz_historico_completo(client):
    repo = repository()
    repo.record(make_observation(value="1000"))
    repo.record(
        make_observation(value="1100", published_at=datetime(2025, 3, 20, tzinfo=timezone.utc))
    )

    body = client.get("/api/data/observations", params={"include_superseded": True}).json()

    assert body["total"] == 2


def test_serie_exige_provider_e_metric(client):
    response = client.get("/api/data/observations/series")
    assert response.status_code == 422
