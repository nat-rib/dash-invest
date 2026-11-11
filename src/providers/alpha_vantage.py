"""Provedor de preços diários do Alpha Vantage como `Observation`."""
from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from urllib.parse import quote

from src.domain.observations import Observation, QualityStatus
from src.market_data import AlphaVantageClient

PARSER_VERSION = "alpha-vantage-daily-v1"


@dataclass(frozen=True)
class AlphaVantageProvider:
    """Implementa `MarketDataProvider` para séries de fechamento diário."""

    api_key: str
    name: str = "alpha_vantage"
    currency: str | None = None

    def daily_prices(
        self,
        symbol: str,
        start: date | None = None,
        end: date | None = None,
        currency: str | None = None,
    ) -> Iterator[Observation]:
        frame = AlphaVantageClient(self.api_key).daily_history(symbol)
        chosen_currency = currency or self.currency
        source = (
            "https://www.alphavantage.co/query"
            f"?function=TIME_SERIES_DAILY&symbol={quote(symbol)}"
        )
        for _, row in frame.iterrows():
            day = row["Data"]
            if start is not None and day < start:
                continue
            if end is not None and day > end:
                continue
            yield Observation(
                provider=self.name,
                metric="close",
                instrument_id=symbol,
                value=Decimal(str(row["Fechamento"])),
                currency=chosen_currency,
                period_end=day,
                reference_date=day,
                parser_version=PARSER_VERSION,
                quality_status=QualityStatus.VERIFIED,
                source_document=source,
            )

    def fx_rate(self, base: str, quote_currency: str, on: date) -> Observation | None:
        return None
