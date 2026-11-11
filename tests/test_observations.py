from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.domain.observations import Observation, QualityStatus
from src.persistence.database import SQLiteDatabase
from src.persistence.observations import ObservationRepository


@pytest.fixture
def repository(tmp_path):
    database = SQLiteDatabase(tmp_path / "observations.db")
    database.initialize()
    return ObservationRepository(database)


def make_observation(**overrides) -> Observation:
    fields = {
        "provider": "cvm",
        "metric": "revenue",
        "instrument_id": "PETR4",
        "value": Decimal("1000.50"),
        "currency": "brl",
        "unit": "BRL",
        "period_start": date(2025, 1, 1),
        "period_end": date(2025, 12, 31),
        "reference_date": date(2025, 12, 31),
        "published_at": datetime(2026, 3, 1, 12, tzinfo=timezone.utc),
        "parser_version": "dfp-v1",
        "quality_status": QualityStatus.VERIFIED,
        "source_document": "https://cvm.example/dfp",
        "raw_payload": '{"conta":"3.01"}',
    }
    fields.update(overrides)
    return Observation(**fields)


def test_normaliza_moeda_e_converte_instante_para_utc():
    observation = make_observation(
        currency="brl",
        published_at=datetime(2026, 3, 1, 9, tzinfo=timezone(timedelta(hours=-3))),
    )

    assert observation.currency == "BRL"
    assert observation.published_at is not None
    assert observation.published_at.isoformat() == "2026-03-01T12:00:00+00:00"


def test_rejeita_valor_nao_finito():
    with pytest.raises(ValidationError):
        make_observation(value=Decimal("NaN"))


def test_rejeita_periodo_invertido():
    with pytest.raises(ValidationError):
        make_observation(period_start=date(2025, 12, 31), period_end=date(2025, 1, 1))


def test_rejeita_instante_sem_timezone():
    with pytest.raises(ValidationError):
        make_observation(published_at=datetime(2026, 3, 1, 12))


def test_round_trip_preserva_proveniencia(repository):
    observation = make_observation()
    stored = repository.get(repository.record(observation))

    assert stored == observation
    assert stored is not None
    assert stored.source_document == "https://cvm.example/dfp"
    assert stored.raw_payload == '{"conta":"3.01"}'
    assert stored.quality_status is QualityStatus.VERIFIED


def test_reingestao_identica_e_idempotente(repository):
    observation = make_observation()

    first = repository.record(observation)
    second = repository.record(observation)

    assert first == second
    assert len(repository.list()) == 1


def test_reapresentacao_supersede_sem_apagar(repository):
    original = make_observation(published_at=datetime(2026, 3, 1, 12, tzinfo=timezone.utc))
    original_id = repository.record(original)

    corrected_id = repository.record(
        make_observation(
            value=Decimal("1100.00"),
            published_at=datetime(2026, 4, 15, 12, tzinfo=timezone.utc),
        )
    )

    assert corrected_id != original_id
    # a série atual mostra só a versão vigente
    assert [item.value for item in repository.list()] == [Decimal("1100.00")]
    # o histórico completo permanece auditável
    assert len(repository.list(include_superseded=True)) == 2
    assert repository.superseded_by(original_id) == corrected_id
    assert repository.superseded_by(corrected_id) is None


def test_reingestao_antiga_nao_reverte_supersessao(repository):
    original = make_observation(published_at=datetime(2026, 3, 1, 12, tzinfo=timezone.utc))
    corrected = make_observation(
        value=Decimal("1100.00"),
        published_at=datetime(2026, 4, 15, 12, tzinfo=timezone.utc),
    )
    original_id = repository.record(original)
    corrected_id = repository.record(corrected)

    assert repository.record(original) == original_id

    assert repository.superseded_by(original_id) == corrected_id
    assert repository.superseded_by(corrected_id) is None
    assert [item.value for item in repository.list()] == [Decimal("1100.00")]


def test_correcao_com_mesma_data_de_publicacao_supersede(repository):
    published = datetime(2025, 2, 19, tzinfo=timezone.utc)
    original = make_observation(
        value=Decimal("225"),
        published_at=published,
        collected_at=datetime(2025, 3, 1, tzinfo=timezone.utc),
    )
    corrected = make_observation(
        value=Decimal("2567"),
        published_at=published,
        collected_at=datetime(2025, 3, 2, tzinfo=timezone.utc),
    )

    original_id = repository.record(original)
    corrected_id = repository.record(corrected)

    assert repository.superseded_by(original_id) == corrected_id
    assert repository.superseded_by(corrected_id) is None
    assert [item.value for item in repository.list()] == [Decimal("2567")]


def test_repair_supersession_marca_duplicatas_legadas(repository):
    database = repository.database
    with database.transaction() as connection:
        for index, value in enumerate(("100", "200"), start=1):
            connection.execute(
                """INSERT INTO observations (
                    fingerprint, provider, instrument_id, metric, value, currency,
                    period_start, period_end, reference_date, published_at, collected_at,
                    parser_version, quality_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    f"legacy-{index}",
                    "cvm",
                    "cnpj:00000000000191",
                    "revenue",
                    value,
                    "BRL",
                    None,
                    None,
                    "2024-12-31",
                    "2025-02-19T00:00:00+00:00",
                    f"2025-03-0{index}T00:00:00+00:00",
                    "legacy",
                    "verified",
                ),
            )

    assert repository.repair_supersession() == 1

    active = repository.list()
    assert len(active) == 1
    assert active[0].value == Decimal("200")
    assert repository.repair_supersession() == 0


def test_filtra_por_provedor_instrumento_e_metrica(repository):
    repository.record(make_observation())
    repository.record(make_observation(metric="net_income", value=Decimal("200")))
    repository.record(make_observation(provider="sec", instrument_id="AAPL"))

    metrics = {item.metric for item in repository.list(provider="cvm", instrument_id="PETR4")}

    assert metrics == {"revenue", "net_income"}
