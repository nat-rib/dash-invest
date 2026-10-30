"""Cliente mínimo e seguro para dados públicos do Alpha Vantage."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import time
from typing import Any

import pandas as pd
import requests

from src.schemas import PortfolioSnapshot

BASE_URL = "https://www.alphavantage.co/query"
REQUEST_INTERVAL_SECONDS = 1.1
_last_request_at = 0.0


class MarketDataError(RuntimeError):
    pass


@dataclass(frozen=True)
class Quote:
    symbol: str
    price: float
    as_of: date | None = None


def alpha_symbol(position) -> str | None:
    """Resolve o símbolo; use market_symbol para substituir a convenção padrão."""
    if position.market_symbol:
        return position.market_symbol
    if position.ticker and position.asset_class in {"acao", "fii", "etf"} and position.currency == "BRL":
        return f"{position.ticker}.SAO"
    if position.ticker and position.asset_class == "cripto":
        return position.ticker
    return None


class AlphaVantageClient:
    def __init__(self, api_key: str, timeout: int = 15):
        if not api_key.strip():
            raise ValueError("Informe a chave Alpha Vantage.")
        self.api_key, self.timeout = api_key, timeout

    def _request(self, **params: str) -> dict[str, Any]:
        global _last_request_at
        wait = REQUEST_INTERVAL_SECONDS - (time.monotonic() - _last_request_at)
        if wait > 0:
            time.sleep(wait)
        try:
            response = requests.get(BASE_URL, params={**params, "apikey": self.api_key}, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            _last_request_at = time.monotonic()
        except (requests.RequestException, ValueError) as error:
            raise MarketDataError("Não foi possível consultar o Alpha Vantage.") from error
        for key in ("Error Message", "Information", "Note"):
            if key in data:
                message = str(data[key])
                if "25 requests per day" in message:
                    raise MarketDataError("Limite diário da chave gratuita (25 consultas) atingido. Aguarde a renovação da cota ou use um plano compatível.")
                raise MarketDataError(message)
        return data

    def quote(self, symbol: str) -> Quote:
        data = self._request(function="GLOBAL_QUOTE", symbol=symbol)
        item = data.get("Global Quote", {})
        try:
            return Quote(symbol=symbol, price=float(item["05. price"]), as_of=date.fromisoformat(item["07. latest trading day"]))
        except (KeyError, TypeError, ValueError) as error:
            raise MarketDataError(f"Cotação indisponível para {symbol}.") from error

    def crypto_quote(self, symbol: str, currency: str = "USD") -> Quote:
        data = self._request(function="CURRENCY_EXCHANGE_RATE", from_currency=symbol, to_currency=currency)
        item = data.get("Realtime Currency Exchange Rate", {})
        try:
            refreshed = str(item.get("6. Last Refreshed", ""))[:10]
            return Quote(symbol=f"{symbol}/{currency}", price=float(item["5. Exchange Rate"]), as_of=date.fromisoformat(refreshed))
        except (KeyError, TypeError, ValueError) as error:
            raise MarketDataError(f"Cotação indisponível para {symbol}/{currency}.") from error

    def quote_position(self, position) -> Quote:
        symbol = alpha_symbol(position)
        if not symbol:
            raise MarketDataError("Esta posição não possui símbolo de mercado.")
        if position.asset_class == "cripto":
            return self.crypto_quote(symbol, position.currency)
        return self.quote(symbol)

    def daily_history(self, symbol: str) -> pd.DataFrame:
        data = self._request(function="TIME_SERIES_DAILY", symbol=symbol, outputsize="compact")
        series = data.get("Time Series (Daily)", {})
        rows = [{"Data": date.fromisoformat(day), "Fechamento": float(values["4. close"])} for day, values in series.items()]
        if not rows:
            raise MarketDataError(f"Histórico indisponível para {symbol}.")
        return pd.DataFrame(rows).sort_values("Data")

    def crypto_daily_history(self, symbol: str, currency: str = "USD") -> pd.DataFrame:
        data = self._request(function="DIGITAL_CURRENCY_DAILY", symbol=symbol, market=currency)
        series = data.get("Time Series (Digital Currency Daily)", {})
        close_key = f"4a. close ({currency})"
        rows = [{"Data": date.fromisoformat(day), "Fechamento": float(values[close_key])} for day, values in series.items()]
        if not rows:
            raise MarketDataError(f"Histórico indisponível para {symbol}/{currency}.")
        return pd.DataFrame(rows).sort_values("Data")

    def daily_history_position(self, position) -> pd.DataFrame:
        symbol = alpha_symbol(position)
        if not symbol:
            raise MarketDataError("Esta posição não possui símbolo de mercado.")
        if position.asset_class == "cripto":
            return self.crypto_daily_history(symbol, position.currency)
        return self.daily_history(symbol)


def updatable_positions(snapshot: PortfolioSnapshot) -> list[tuple[int, str]]:
    return [(index, symbol) for index, position in enumerate(snapshot.positions) if (symbol := alpha_symbol(position))]


def replace_prices(snapshot: PortfolioSnapshot, quotes: dict[int, Quote], fx_rates: dict[str, Quote] | None = None) -> PortfolioSnapshot:
    """Gera um novo snapshot; não persiste o arquivo."""
    data = snapshot.model_dump(mode="json")
    fx_rates = fx_rates or {}
    for index, quote in quotes.items():
        data["positions"][index]["current_price"] = quote.price
        position = data["positions"][index]
        if position.get("quantity") is not None:
            position["current_value"] = float(position["quantity"]) * quote.price
        currency = position.get("currency")
        if currency in fx_rates and position.get("current_value") is not None:
            fx_quote = fx_rates[currency]
            position["conversion_rate_to_brl"] = fx_quote.price
            position["converted_value_brl"] = float(position["current_value"]) * fx_quote.price
            position["conversion_date"] = fx_quote.as_of.isoformat() if fx_quote.as_of else None
    return PortfolioSnapshot.model_validate(data)
