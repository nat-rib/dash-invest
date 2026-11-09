from datetime import date, datetime, timezone
from decimal import Decimal

from jobs import ingest_cvm
from src.domain.observations import Observation


def make_observation() -> Observation:
    return Observation(
        provider="cvm",
        metric="revenue",
        instrument_id="cnpj:00000000000191",
        value=Decimal("1000"),
        currency="BRL",
        reference_date=date(2024, 12, 31),
        published_at=datetime(2025, 2, 19, tzinfo=timezone.utc),
        parser_version="cvm-dfp-v1",
    )


class FakeProvider:
    def __init__(self, *, consolidated: bool = True):
        assert consolidated is True

    def statements(self, fiscal_year: int) -> list[Observation]:
        assert fiscal_year == 2024
        return [make_observation()]


def test_cli_ingere_e_reporta(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(ingest_cvm, "CvmDfpProvider", FakeProvider)

    exit_code = ingest_cvm.main(["--year", "2024", "--db", str(tmp_path / "dash.db")])

    assert exit_code == 0
    assert "1 novas observações da CVM DFP 2024" in capsys.readouterr().out
