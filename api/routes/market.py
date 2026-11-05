"""Rotas de histórico patrimonial e mercado (Fase 5 do roadmap).

Histórico escreve em HISTORY_DB_PATH persistente. Nenhuma cotação é aplicada
sem prévia e confirmação; apenas símbolos são enviados ao provedor.
"""
from __future__ import annotations

from urllib.parse import unquote

from fastapi import APIRouter, HTTPException

from api.schemas.market import (
    FxRateOut, MarketHistoryOut, MarketHistoryPoint, MarketPositionOut,
    MarketQuoteOut, PortfolioHistoryOut, PositionHistoryPoint, PositionHistoryOut,
    PositionKeyListOut, QuoteConfirmOut, QuotesPreviewOut, PreviewPositionOut,
)
from api.services import market_service

router = APIRouter(prefix="/api", tags=["market"])


def _bad_request(message: str, status_code: int = 400) -> HTTPException:
    return HTTPException(status_code=status_code, detail=message)


# ------------------------------------------------------------------- histórico

@router.get("/history/portfolio", response_model=PortfolioHistoryOut)
def portfolio_history_route() -> PortfolioHistoryOut:
    try:
        return PortfolioHistoryOut(points=market_service.portfolio_points())
    except Exception as error:  # noqa: BLE001 - o arquivo histórico pode estar inacessível
        raise _bad_request(f"Histórico indisponível: {error}") from error


@router.get("/history/positions", response_model=PositionKeyListOut)
def position_keys() -> PositionKeyListOut:
    return PositionKeyListOut(keys=market_service.position_keys())


@router.get("/history/positions/{position_key:path}", response_model=PositionHistoryOut)
def position_history_route(position_key: str) -> PositionHistoryOut:
    key = unquote(position_key)
    keys = market_service.position_keys()
    if key not in keys:
        raise _bad_request("Posição não encontrada no histórico.", status_code=404)
    return PositionHistoryOut(
        position_key=key,
        points=[PositionHistoryPoint(**item) for item in market_service.points_for_key(key)],
    )


@router.post("/history/snapshot", tags=["history"])
def record_current_snapshot() -> dict:
    """Registra o snapshot atual no histórico sem consultar o provedor."""
    try:
        snapshot_id = market_service.register_current_snapshot("manual")
    except (ValueError, FileNotFoundError) as error:
        raise _bad_request(str(error)) from error
    return {"snapshot_id": snapshot_id, "message": "Snapshot registrado no histórico local."}


# --------------------------------------------------------------------- mercado

@router.get("/market/positions", response_model=list[MarketPositionOut])
def market_positions() -> list[MarketPositionOut]:
    try:
        data = market_service.market_positions()
    except (FileNotFoundError, ValueError) as error:
        raise _bad_request(str(error)) from error
    return [MarketPositionOut(**item) for item in data]


@router.get("/market/quotes", response_model=QuotesPreviewOut)
def market_quotes() -> QuotesPreviewOut:
    """Consulta pura de cotações; não altera snapshot nem histórico."""
    try:
        quotes, fx_rates, errors = market_service.current_quotes()
    except (FileNotFoundError, ValueError) as error:
        raise _bad_request(str(error)) from error
    except market_service.MarketUnavailableError as error:
        raise _bad_request(str(error), status_code=503) from error
    snapshot = market_service.load_or_none()
    return _preview_response(quotes, fx_rates, errors, snapshot)


@router.get("/market/history/{index}", response_model=MarketHistoryOut)
def market_history(index: int) -> MarketHistoryOut:
    try:
        data = market_service.market_history(index)
    except (FileNotFoundError, ValueError) as error:
        raise _bad_request(str(error)) from error
    except IndexError as error:
        raise _bad_request(str(error), status_code=404) from error
    except market_service.MarketUnavailableError as error:
        raise _bad_request(str(error), status_code=503) from error
    except market_service.MarketDataError as error:
        return MarketHistoryOut(symbol="", currency="", provider="Alpha Vantage", points=[], unavailable_reason=str(error))
    return MarketHistoryOut(
        symbol=data["symbol"],
        currency=data["currency"],
        provider=data["provider"],
        points=[MarketHistoryPoint(**item) for item in data["points"]],
    )


@router.post("/market/quotes/preview", response_model=QuotesPreviewOut)
def preview_quotes() -> QuotesPreviewOut:
    try:
        outcome = market_service.quote_preview()
    except (FileNotFoundError, ValueError) as error:
        raise _bad_request(str(error)) from error
    except market_service.MarketUnavailableError as error:
        raise _bad_request(str(error), status_code=503) from error
    return _preview_response(
        outcome["quotes"], outcome["fx_rates"], outcome["errors"], outcome["preview_snapshot"],
    )


@router.post("/market/quotes/confirm", response_model=QuoteConfirmOut)
def confirm_quotes() -> QuoteConfirmOut:
    """Aplica os preços no portfolio.json após nova consulta validada."""
    try:
        outcome = market_service.confirm_quotes()
    except (FileNotFoundError, ValueError, OSError) as error:
        raise _bad_request(f"Não foi possível atualizar os preços: {error}") from error
    except market_service.MarketUnavailableError as error:
        raise _bad_request(str(error), status_code=503) from error
    return QuoteConfirmOut(
        updated=outcome["updated"],
        unchanged=outcome["unchanged"],
        message=outcome["message"],
    )


def _preview_response(quotes, fx_rates, errors, preview_snapshot) -> QuotesPreviewOut:
    market_positions_data = market_service.market_positions()
    label_by_index = {item["index"]: item["name"] for item in market_positions_data}
    symbol_by_index = {item["index"]: item["symbol"] for item in market_positions_data}
    quote_rows = [
        MarketQuoteOut(
            index=index,
            name=label_by_index.get(index, f"posição {index}"),
            symbol=symbol_by_index.get(index, ""),
            price=str(quote.price),
            price_date=quote.as_of.isoformat() if quote.as_of else None,
        )
        for index, quote in quotes.items()
    ]
    fx_rows = [
        FxRateOut(currency=currency, rate=str(quote.price), as_of_date=quote.as_of.isoformat() if quote.as_of else None)
        for currency, quote in fx_rates.items()
    ]
    positions: list[PreviewPositionOut] = []
    if preview_snapshot is not None:
        original = market_service.load_or_none()
        for index, position in enumerate(preview_snapshot.positions):
            before = original.positions[index]
            changed = (
                position.current_price != before.current_price
                or position.current_value != before.current_value
            )
            positions.append(PreviewPositionOut(
                index=index,
                institution=position.institution,
                ticker=position.ticker,
                name=position.name,
                currency=position.currency,
                quantity=str(position.quantity) if position.quantity is not None else None,
                current_price=str(position.current_price) if position.current_price is not None else None,
                current_value=str(position.current_value) if position.current_value is not None else None,
                converted_value_brl=(
                    str(position.converted_value_brl) if position.converted_value_brl is not None else None
                ),
                conversion_rate_to_brl=(
                    str(position.conversion_rate_to_brl) if position.conversion_rate_to_brl is not None else None
                ),
                changed=changed,
            ))
    return QuotesPreviewOut(
        quotes=quote_rows,
        fx_rates=[row for row in fx_rows if row is not None],
        errors=errors,
        positions=positions,
        source="alpha_vantage",
    )
