from datetime import date
from decimal import Decimal

import pytest

from src.ai.gateway import ResearchError
from src.ai.research import build_report
from src.domain.issuers import Issuer
from src.domain.observations import Observation

ISSUER = Issuer(cnpj="00000000000191", name="Empresa Teste")


def observation(metric: str, value: float, reference: date, source: str | None = None) -> Observation:
    return Observation(
        provider="cvm",
        metric=metric,
        instrument_id="cnpj:00000000000191",
        value=Decimal(str(value)),
        currency="BRL",
        reference_date=reference,
        parser_version="test",
        source_document=source,
    )


def full_history() -> list[Observation]:
    return [
        observation("revenue", 1000, date(2023, 12, 31), "http://doc/2023"),
        observation("revenue", 1200, date(2024, 12, 31), "http://doc/2024"),
        observation("net_income", 120, date(2024, 12, 31), "http://doc/2024"),
        observation("equity", 600, date(2024, 12, 31), "http://doc/2024"),
        observation("total_assets", 2000, date(2024, 12, 31), "http://doc/2024"),
    ]


def test_relatorio_deriva_razoes_e_crescimento():
    report = build_report(issuer=ISSUER, observations=full_history())

    claims = {claim.key: claim for claim in report.claims}
    assert claims["net_margin"].value == pytest.approx(0.1)
    assert claims["roe"].value == pytest.approx(0.2)
    assert claims["revenue_growth"].value == pytest.approx(0.2)
    assert claims["revenue"].value == pytest.approx(1200)
    assert "receita" in report.narrative
    assert "http://doc/2024" in report.sources
    assert report.gateway == "deterministic"


def test_sem_ano_anterior_marca_limitacao():
    report = build_report(
        issuer=ISSUER,
        observations=[observation("revenue", 1000, date(2024, 12, 31))],
    )

    assert any("Sem exercício anterior" in item for item in report.limitations)


def test_sem_observacoes_nao_inventa_narrativa():
    report = build_report(issuer=ISSUER, observations=[])

    assert report.claims == ()
    assert "Não há observações" in report.narrative


class FakeGateway:
    name = "fake"

    def summarize(self, *, system: str, prompt: str) -> str:
        assert "Fatos verificados" in prompt
        return "Narrativa gerada pelo LLM."


class FailingGateway:
    name = "failing"

    def summarize(self, *, system: str, prompt: str) -> str:
        raise ResearchError("indisponível")


def test_gateway_substitui_apenas_a_narrativa():
    report = build_report(
        issuer=ISSUER, observations=full_history(), gateway=FakeGateway()
    )

    assert report.narrative == "Narrativa gerada pelo LLM."
    assert report.gateway == "fake"
    assert any(claim.key == "net_margin" for claim in report.claims)


def test_falha_do_gateway_usa_narrativa_deterministica():
    report = build_report(
        issuer=ISSUER, observations=full_history(), gateway=FailingGateway()
    )

    assert "receita" in report.narrative
    assert report.gateway == "deterministic"
    assert any("indisponível" in item for item in report.limitations)
