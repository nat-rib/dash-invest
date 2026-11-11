from datetime import date

import pytest

from src.application.prices import csv_price_observations
from src.providers.alpha_vantage import AlphaVantageProvider


def test_csv_com_cabecalho_em_portugues_e_virgula():
    text = "Data;Fechamento\n02/01/2024;10,50\n01/01/2024;10,00\n"

    observations = list(
        csv_price_observations(text, symbol="PETR4.SAO", currency="BRL")
    )

    assert [item.reference_date for item in observations] == [
        date(2024, 1, 1),
        date(2024, 1, 2),
    ]
    assert observations[0].metric == "close"
    assert observations[0].provider == "csv"
    assert float(observations[1].value) == 10.5
    assert observations[0].currency == "BRL"


def test_csv_rejeita_linha_incompleta():
    text = "date,close\n2024-01-01,10\n2024-01-02,\n"

    with pytest.raises(ValueError):
        list(csv_price_observations(text, symbol="X"))


def test_provider_alpha_vantage_converte_dataframe(monkeypatch):
    import pandas as pd

    frame = pd.DataFrame(
        {
            "Data": [date(2024, 1, 1), date(2024, 1, 2)],
            "Fechamento": [10.0, 11.0],
        }
    )
    monkeypatch.setattr(
        "src.providers.alpha_vantage.AlphaVantageClient.daily_history",
        lambda self, symbol: frame,
    )

    provider = AlphaVantageProvider(api_key="test", currency="BRL")
    observations = list(provider.daily_prices("PETR4.SAO", start=date(2024, 1, 2)))

    assert len(observations) == 1
    assert observations[0].reference_date == date(2024, 1, 2)
    assert float(observations[0].value) == 11.0
    assert observations[0].provider == "alpha_vantage"
    assert "TIME_SERIES_DAILY" in (observations[0].source_document or "")
