"""Atualização diária de cotações das posições da carteira.

Lê os símbolos do snapshot (ticker + convenção `.SAO`/`market_symbol`), consulta
o provedor e grava observações. Cripto é ignorado porque o provedor atual cobre
apenas séries de ações/FIIs/ETFs.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.market_data import MarketDataError, alpha_symbol
from src.persistence.observations import ObservationRepository
from src.schemas import PortfolioSnapshot

DEFAULT_MAX_SYMBOLS = 20


@dataclass(frozen=True)
class PortfolioSymbol:
    symbol: str
    currency: str | None


@dataclass(frozen=True)
class PriceIngestionSummary:
    inserted: int
    fetched: tuple[str, ...]
    skipped: tuple[str, ...]
    errors: tuple[str, ...]


def portfolio_symbols(snapshot: PortfolioSnapshot) -> list[PortfolioSymbol]:
    seen: dict[str, str | None] = {}
    for position in snapshot.positions:
        if position.asset_class == "cripto":
            continue
        symbol = alpha_symbol(position)
        if not symbol:
            continue
        seen.setdefault(symbol, position.currency)
    return [PortfolioSymbol(symbol=symbol, currency=currency) for symbol, currency in seen.items()]


def ingest_portfolio_prices(
    snapshot: PortfolioSnapshot,
    provider: Any,
    repository: ObservationRepository,
    *,
    max_symbols: int = DEFAULT_MAX_SYMBOLS,
) -> PriceIngestionSummary:
    symbols = portfolio_symbols(snapshot)
    selected = symbols[:max_symbols]
    skipped = tuple(item.symbol for item in symbols[max_symbols:])

    inserted = 0
    errors: list[str] = []
    for item in selected:
        try:
            inserted += repository.record_many(
                provider.daily_prices(item.symbol, currency=item.currency)
            )
        except MarketDataError as error:
            errors.append(f"{item.symbol}: {error}")

    return PriceIngestionSummary(
        inserted=inserted,
        fetched=tuple(item.symbol for item in selected),
        skipped=skipped,
        errors=tuple(errors),
    )
