from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from src.application.fundamentals import FundamentalsIngestion
from src.domain.observations import Observation
from src.persistence.database import SQLiteDatabase
from src.persistence.observations import ObservationRepository


@pytest.fixture
def repository(tmp_path):
    database = SQLiteDatabase(tmp_path / "observations.db")
    database.initialize()
    return ObservationRepository(database)


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


class FakeProvider:
    name = "fake"

    def __init__(self, observations: list[Observation]):
        self._observations = observations

    def statements(self, fiscal_year: int) -> list[Observation]:
        assert fiscal_year == 2024
        return self._observations


def test_ingestao_persiste_lote_e_e_idempotente(repository):
    observations = [make_observation("revenue", "1000"), make_observation("net_income", "100")]
    ingestion = FundamentalsIngestion(provider=FakeProvider(observations), repository=repository)

    assert ingestion.run(2024) == 2
    assert ingestion.run(2024) == 0
    assert len(repository.list(provider="cvm")) == 2


def test_record_many_retorna_apenas_linhas_novas(repository):
    first = make_observation("revenue", "1000")
    second = make_observation("net_income", "100")
    corrected = make_observation("net_income", "110")

    assert repository.record_many([first, second]) == 2
    assert repository.record_many([first, second]) == 0
    assert repository.record_many([corrected]) == 1

    current = {item.metric: item.value for item in repository.list()}
    assert current == {"revenue": Decimal("1000"), "net_income": Decimal("110")}
    assert len(repository.list(include_superseded=True)) == 3
