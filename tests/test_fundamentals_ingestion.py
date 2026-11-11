from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from src.application.fundamentals import FundamentalsIngestion
from src.domain.issuers import Issuer
from src.domain.observations import Observation
from src.persistence.database import SQLiteDatabase
from src.persistence.issuers import IssuerRepository
from src.persistence.observations import ObservationRepository
from src.providers.base import FundamentalsBatch


@pytest.fixture
def database(tmp_path):
    db = SQLiteDatabase(tmp_path / "observations.db")
    db.initialize()
    return db


@pytest.fixture
def observations(database):
    return ObservationRepository(database)


@pytest.fixture
def issuers(database):
    return IssuerRepository(database)


def make_observation(metric: str, value: str) -> Observation:
    return Observation(
        provider="cvm",
        metric=metric,
        instrument_id="cnpj:00000000000191",
        value=Decimal(value),
        currency="BRL",
        period_start=date(2024, 1, 1),
        period_end=date(2024, 12, 31),
        reference_date=date(2024, 12, 31),
        published_at=datetime(2025, 2, 19, tzinfo=timezone.utc),
        parser_version="cvm-dfp-v1",
    )


def make_issuer(name: str = "EMPRESA TESTE S.A.") -> Issuer:
    return Issuer(
        cnpj="00.000.000/0001-91",
        name=name,
        cvm_code="001023",
        updated_at=datetime(2025, 2, 19, tzinfo=timezone.utc),
    )


class FakeProvider:
    name = "fake"

    def __init__(self, batch: FundamentalsBatch):
        self._batch = batch

    def fetch(self, fiscal_year: int) -> FundamentalsBatch:
        assert fiscal_year == 2024
        return self._batch


def test_ingestao_persiste_emissores_e_observacoes(observations, issuers):
    batch = FundamentalsBatch(
        observations=[make_observation("revenue", "1000"), make_observation("net_income", "100")],
        issuers=[make_issuer()],
    )
    ingestion = FundamentalsIngestion(
        provider=FakeProvider(batch), repository=observations, issuers=issuers
    )

    first = ingestion.run(2024)
    second = ingestion.run(2024)

    assert (first.issuers, first.observations) == (1, 2)
    assert (second.issuers, second.observations) == (0, 0)
    assert len(observations.list(provider="cvm")) == 2
    assert [item.name for item in issuers.list()] == ["EMPRESA TESTE S.A."]


def test_ingestao_processa_em_chunks(observations, issuers):
    generated = (make_observation(f"metric_{index}", str(index)) for index in range(5))
    batch = FundamentalsBatch(observations=generated, issuers=[])
    ingestion = FundamentalsIngestion(
        provider=FakeProvider(batch),
        repository=observations,
        issuers=issuers,
        chunk_size=2,
    )

    result = ingestion.run(2024)

    assert result.observations == 5
    assert len(observations.list()) == 5


def test_record_many_retorna_apenas_linhas_novas(observations):
    first = make_observation("revenue", "1000")
    second = make_observation("net_income", "100")
    corrected = make_observation("net_income", "110")

    assert observations.record_many([first, second]) == 2
    assert observations.record_many([first, second]) == 0
    assert observations.record_many([corrected]) == 1

    current = {item.metric: item.value for item in observations.list()}
    assert current == {"revenue": Decimal("1000"), "net_income": Decimal("110")}
    assert len(observations.list(include_superseded=True)) == 3


def test_upsert_issuer_atualiza_sem_duplicar(issuers):
    assert issuers.upsert(make_issuer("NOME ANTIGO")) is True

    assert issuers.upsert(make_issuer("NOME NOVO")) is False
    assert issuers.count() == 1

    stored = issuers.get("00.000.000/0001-91")
    assert stored is not None
    assert stored.cnpj == "00000000000191"
    assert stored.name == "NOME NOVO"
    assert stored.cvm_code == "001023"


def test_issuers_filtra_por_nome_ou_cnpj(issuers):
    issuers.upsert(make_issuer("PETROBRAS"))
    issuers.upsert(
        Issuer(
            cnpj="11.111.111/0001-11",
            name="VALE",
            updated_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        )
    )

    assert [item.name for item in issuers.list(query="petro")] == ["PETROBRAS"]
    assert [item.name for item in issuers.list(query="11111111")] == ["VALE"]
    assert issuers.count(query="a") == 2
