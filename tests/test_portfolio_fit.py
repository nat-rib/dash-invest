import pytest

from src.analytics.portfolio_fit import FitInput, build_fit


def test_exposicoes_concentracao_e_cobertura():
    inputs = [
        FitInput("A", "XP", "acao", "BRL", 3000),
        FitInput("B", "XP", "fii", "BRL", 1000),
        FitInput(
            "C",
            "BTG",
            "renda_fixa",
            "BRL",
            500,
            liquidity="D+1",
            risk_category="baixo",
        ),
    ]

    fit = build_fit(inputs)

    assert fit.total_brl == pytest.approx(4500)
    assert fit.positions == 3
    assert [slice.name for slice in fit.by_class] == ["acao", "fii", "renda_fixa"]
    assert fit.by_class[0].share == pytest.approx(3000 / 4500)
    assert [slice.name for slice in fit.by_institution] == ["XP", "BTG"]
    assert fit.herfindahl == pytest.approx(
        (3000 / 4500) ** 2 + (1000 / 4500) ** 2 + (500 / 4500) ** 2
    )
    assert fit.liquidity_coverage == pytest.approx(500 / 4500)
    assert fit.credit_coverage == pytest.approx(500 / 4500)
    assert any("Duration" in item for item in fit.unavailable)


def test_sem_posicoes_nao_inventa_metricas():
    fit = build_fit([])

    assert fit.total_brl == 0
    assert fit.positions == 0
    assert fit.herfindahl is None
    assert fit.liquidity_coverage is None
    assert fit.unavailable


def test_etf_marca_look_through_indisponivel():
    fit = build_fit([FitInput("ETF", "XP", "etf", "BRL", 1000)])

    assert fit.herfindahl == pytest.approx(1.0)
    assert any("Look-through" in item for item in fit.unavailable)
