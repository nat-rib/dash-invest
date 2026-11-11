from datetime import date, timedelta

import pytest

from src.analytics.risk import MIN_RETURNS, PricePoint, calculate_risk


def series(values: list[float], start: date = date(2024, 1, 1)) -> list[PricePoint]:
    return [PricePoint(start + timedelta(days=index), value) for index, value in enumerate(values)]


def test_retorno_total_e_drawdown():
    report = calculate_risk(series([100, 110, 90, 120]))

    assert report.observations == 4
    assert report.returns == 3
    assert report.total_return == pytest.approx(0.2)
    assert report.max_drawdown == pytest.approx(-0.1818181818)


def test_amostra_insuficiente_nao_vira_zero():
    report = calculate_risk(series([100, 101, 102]))

    assert report.total_return == pytest.approx(0.02)
    assert report.annualized_volatility is None
    assert report.sharpe is None
    assert report.var_95 is None
    assert "annualized_volatility" in report.unavailable


def test_volatilidade_sharpe_e_cvar_com_amostra_suficiente():
    values = [100 + (index % 7) - 3 for index in range(MIN_RETURNS + 5)]
    report = calculate_risk(series(values), risk_free_rate=0.10)

    assert report.annualized_volatility is not None
    assert report.annualized_volatility > 0
    assert report.sharpe is not None
    assert report.sortino is not None
    assert report.var_95 is not None and report.var_95 >= 0
    assert report.cvar_95 is not None and report.cvar_95 >= report.var_95


def test_beta_e_correlacao_com_benchmark_identico():
    values = [100 + index for index in range(MIN_RETURNS + 5)]
    points = series(values)

    report = calculate_risk(points, benchmark=points)

    assert report.beta == pytest.approx(1.0)
    assert report.correlation == pytest.approx(1.0)


def test_benchmark_curto_indisponibiliza_beta():
    points = series([100 + index for index in range(MIN_RETURNS + 5)])
    short_benchmark = series([50 + index for index in range(5)])

    report = calculate_risk(points, benchmark=short_benchmark)

    assert report.beta is None
    assert "beta" in report.unavailable


def test_precos_invalidos_sao_descartados():
    points = [
        PricePoint(date(2024, 1, 1), 100),
        PricePoint(date(2024, 1, 2), 0),
        PricePoint(date(2024, 1, 3), float("nan")),
        PricePoint(date(2024, 1, 4), 110),
    ]

    report = calculate_risk(points)

    assert report.observations == 2
    assert report.total_return == pytest.approx(0.1)
