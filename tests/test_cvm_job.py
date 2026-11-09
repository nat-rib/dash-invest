from datetime import date, datetime, timezone
from decimal import Decimal

from jobs import ingest_cvm
from src.domain.issuers import Issuer
from src.domain.observations import Observation
from src.providers.base import FundamentalsBatch


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


def make_issuer() -> Issuer:
    return Issuer(
        cnpj="00000000000191",
        name="EMPRESA TESTE S.A.",
        cvm_code="001023",
        updated_at=datetime(2025, 2, 19, tzinfo=timezone.utc),
    )


class FakeProvider:
    def __init__(self, *, consolidated: bool = True):
        assert consolidated is True

    def fetch(self, fiscal_year: int) -> FundamentalsBatch:
        assert fiscal_year == 2024
        return FundamentalsBatch(observations=[make_observation()], issuers=[make_issuer()])


def test_cli_ingere_e_reporta(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(ingest_cvm, "CvmDfpProvider", FakeProvider)

    exit_code = ingest_cvm.main(["--year", "2024", "--db", str(tmp_path / "dash.db")])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "1 novas observações e 1 novos emissores da CVM DFP 2024" in output
