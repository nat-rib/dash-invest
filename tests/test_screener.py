from datetime import date

import pytest

from src.analytics.screener import ScreenerRow, build_rows, filter_and_sort
from src.analytics.valuation import discounted_cash_flow

REFERENCE = date(2024, 12, 31)


def test_calcula_razoes_fundamentalistas():
    series = {
        "cnpj:1": {
            "revenue": (1000.0, REFERENCE),
            "net_income": (100.0, REFERENCE),
            "equity": (500.0, REFERENCE),
            "total_assets": (2000.0, REFERENCE),
        }
    }

    row = build_rows(series, {"1": "Empresa Teste"})[0]

    assert row.name == "Empresa Teste"
    assert row.net_margin == 0.1
    assert row.roe == 0.2
    assert row.roa == 0.05
    assert row.asset_turnover == 0.5


def test_denominador_invalido_nao_vira_zero():
    series = {
        "cnpj:1": {
            "revenue": (0.0, REFERENCE),
            "net_income": (10.0, REFERENCE),
            "equity": (0.0, REFERENCE),
            "total_assets": (0.0, REFERENCE),
        }
    }

    row = build_rows(series, {})[0]

    assert row.net_margin is None
    assert row.roe is None
    assert row.roa is None
    assert row.asset_turnover is None


def test_filtra_e_ordena_com_ausente_por_ultimo():
    rows = [
        ScreenerRow("1", "A", REFERENCE, 100, 10, 100, 200, 0.1, 0.1, 0.05, 0.5),
        ScreenerRow("2", "B", REFERENCE, 100, 20, 100, 200, 0.2, 0.2, 0.1, 0.5),
        ScreenerRow("3", "C", REFERENCE, 100, None, 100, 200, None, None, None, 0.5),
    ]

    ordered = filter_and_sort(rows, sort_by="roe", descending=True)
    assert [row.cnpj for row in ordered] == ["2", "1", "3"]

    filtered = filter_and_sort(rows, min_roe=0.15)
    assert [row.cnpj for row in filtered] == ["2"]


def test_dcf_calcula_valor_presente_explicito_e_terminal():
    result = discounted_cash_flow(
        base_cash_flow=100,
        growth_rate=0.1,
        years=2,
        terminal_growth=0.02,
        discount_rate=0.1,
    )

    assert len(result.projections) == 2
    assert result.projections[0].cash_flow == pytest.approx(110.0)
    assert result.projections[1].cash_flow == pytest.approx(121.0)
    assert result.present_value_explicit == pytest.approx(200.0)
    assert result.present_value_terminal == pytest.approx(1275.0)
    assert result.enterprise_value == pytest.approx(1475.0)


def test_dcf_rejeita_desconto_menor_que_perpetuidade():
    try:
        discounted_cash_flow(
            base_cash_flow=100,
            growth_rate=0.1,
            years=2,
            terminal_growth=0.1,
            discount_rate=0.05,
        )
    except ValueError as error:
        assert "desconto" in str(error)
    else:
        raise AssertionError("esperava ValueError")
