import json
from datetime import date
from decimal import Decimal

import pytest

from jobs import ingest_prices_daily
from src.domain.observations import Observation, QualityStatus

PORTFOLIO = {
    "schema_version": 1,
    "snapshot_date": "2026-03-31",
    "currency": "BRL",
    "positions": [
        {
            "institution": "XP",
            "asset_class": "acao",
            "ticker": "PETR4",
            "name": "Petrobras",
            "quantity": "10",
            "current_price": "30.00",
            "currency": "BRL",
        }
    ],
}


class FakeProvider:
    def __init__(self, api_key: str):
        assert api_key

    def daily_prices(self, symbol, start=None, end=None, currency=None):
        return [
            Observation(
                provider="fake",
                metric="close",
                instrument_id=symbol,
                value=Decimal("30"),
                currency=currency,
                reference_date=date(2024, 1, 1),
                period_end=date(2024, 1, 1),
                parser_version="test",
                quality_status=QualityStatus.VERIFIED,
            )
        ]


def test_cli_atualiza_carteira(tmp_path, monkeypatch, capsys):
    portfolio = tmp_path / "portfolio.json"
    portfolio.write_text(json.dumps(PORTFOLIO), encoding="utf-8")
    monkeypatch.setenv("ALPHA_VANTAGE_API_KEY", "test")
    monkeypatch.setattr(ingest_prices_daily, "AlphaVantageProvider", FakeProvider)

    exit_code = ingest_prices_daily.main(
        ["--portfolio", str(portfolio), "--db", str(tmp_path / "dash.db")]
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "1 novas cotações em 1 símbolos" in output
    assert "PETR4.SAO" in output


def test_cli_exige_chave(tmp_path, monkeypatch):
    portfolio = tmp_path / "portfolio.json"
    portfolio.write_text(json.dumps(PORTFOLIO), encoding="utf-8")
    monkeypatch.delenv("ALPHA_VANTAGE_API_KEY", raising=False)

    with pytest.raises(SystemExit):
        ingest_prices_daily.main(["--portfolio", str(portfolio)])
