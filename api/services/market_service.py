"""Serviço de histórico patrimonial e mercado (Fase 5).

Histórico reutiliza src.history (snapshots locais). Mercado reutiliza
src.market_data: apenas símbolos vão ao provedor; carteira nunca.
Prévias registram no histórico e a gravação do snapshot exige confirmação.
"""
from __future__ import annotations

import os
from pathlib import Path

from src.history import portfolio_history, position_history, record_snapshot
from src.importer import load_snapshot, replace_snapshot
from src.market_data import (
    AlphaVantageClient, MarketDataError, replace_prices, updatable_positions,
)
from api.config import portfolio_path


class MarketUnavailableError(RuntimeError):
    """Não há chave do provedor configurada neste ambiente."""


def history_db_path() -> Path:
    return Path(os.environ.get("HISTORY_DB_PATH", "data/portfolio_history.db"))


def client_from_env() -> AlphaVantageClient:
    api_key = os.environ.get("ALPHA_VANTAGE_API_KEY", "")
    if not api_key:
        raise MarketUnavailableError(
            "Configure ALPHA_VANTAGE_API_KEY (.env do servidor) ou em .streamlit/secrets.toml local."
        )
    return AlphaVantageClient(api_key)


def load_or_none():
    path = portfolio_path()
    if not path.exists():
        raise FileNotFoundError("Importe uma carteira primeiro.")
    return load_snapshot(path)


# ------------------------------------------------------------------- histórico

def portfolio_points() -> list[dict]:
    frame = portfolio_history(history_db_path())
    return [
        {"captured_at": row["Data"].isoformat() if hasattr(row["Data"], "isoformat") else str(row["Data"]),
         "total_brl": float(row["Patrimônio BRL"]), "source": row["Origem"]}
        for _, row in frame.iterrows()
    ]


def position_keys() -> list[str]:
    frame = position_history(history_db_path())
    if frame.empty:
        return []
    return sorted({str(key) for key in frame["Posição"].unique()})


def points_for_key(position_key: str) -> list[dict]:
    frame = position_history(history_db_path())
    if frame.empty:
        return []
    frame = frame[frame["Posição"] == position_key]
    return [
        {
            "captured_at": row["Data"].isoformat() if hasattr(row["Data"], "isoformat") else str(row["Data"]),
            "position_key": str(row["Posição"]),
            "name": str(row["Ativo"]),
            "institution": str(row["Instituição"]),
            "currency": str(row["Moeda"]),
            "current_price": None if row["Preço atual"] is None or row["Preço atual"] != row["Preço atual"] else float(row["Preço atual"]),
            "current_value": None if row["Valor atual"] is None or row["Valor atual"] != row["Valor atual"] else float(row["Valor atual"]),
            "value_brl": None if row["Valor BRL"] is None or row["Valor BRL"] != row["Valor BRL"] else float(row["Valor BRL"]),
        }
        for _, row in frame.iterrows()
    ]


def register_current_snapshot(source: str) -> int:
    """Persiste no histórico os valores conhecidos do snapshot atual."""
    return record_snapshot(load_or_none(), source=source, path=history_db_path())


# --------------------------------------------------------------------- mercado

def market_positions() -> list[dict]:
    snapshot = load_or_none()
    return [
        {"index": index, "name": snapshot.positions[index].name, "symbol": symbol}
        for index, symbol in updatable_positions(snapshot)
    ]


def current_quotes() -> tuple[dict[int, object], dict[str, object], list[str]]:
    snapshot = load_or_none()
    client = client_from_env()
    quotes: dict[int, object] = {}
    errors: list[str] = []
    for index, symbol in updatable_positions(snapshot):
        try:
            quotes[index] = client.quote_position(snapshot.positions[index])
        except MarketDataError as error:
            errors.append(f"{snapshot.positions[index].name} ({symbol}): {error}")
    fx_rates: dict[str, object] = {}
    for currency in {
        snapshot.positions[index].currency for index in quotes
        if snapshot.positions[index].currency != "BRL"
    }:
        try:
            fx_rates[currency] = client.crypto_quote(currency, "BRL")
        except MarketDataError as error:
            errors.append(f"Conversão {currency}/BRL: {error}")
    return quotes, fx_rates, errors


def quote_preview() -> dict:
    """Consulta cotações, monta a prévia do snapshot e registra no histórico."""
    client = client_from_env()
    snapshot = load_or_none()
    quotes, fx_rates, errors = current_quotes()
    if not quotes:
        return {"quotes": {}, "fx_rates": {}, "errors": errors, "positions": [], "snapshot": None,
                "snapshot_before": None, "source": "alpha_vantage"}
    preview = replace_prices(snapshot, quotes, fx_rates)
    record_snapshot(preview, source="alpha_vantage", path=history_db_path())
    return {
        "quotes": quotes, "fx_rates": fx_rates, "errors": errors,
        "positions": [], "preview_snapshot": preview,
        "snapshot_template": snapshot, "source": "alpha_vantage",
    }


def market_history(position_index: int) -> dict:
    snapshot = load_or_none()
    if position_index < 0 or position_index >= len(snapshot.positions):
        raise IndexError("Posição não encontrada.")
    client = client_from_env()
    position = snapshot.positions[position_index]
    history = client.daily_history_position(position)
    return {
        "symbol": position.market_symbol or position.ticker or "",
        "currency": position.currency,
        "provider": "Alpha Vantage",
        "points": [
            {"date": str(row["Data"]), "close": str(float(row["Fechamento"]))}
            for _, row in history.iterrows()
        ],
    }


def confirm_quotes() -> dict:
    """Refaz a consulta e sobrescreve o snapshot atual com confirmação explícita."""
    snapshot = load_or_none()
    quotes, fx_rates, errors = current_quotes()
    if not quotes:
        return {"updated": 0, "unchanged": 0, "errors": errors, "message": "Nenhuma cotação obtida; snapshot não alterado."}
    preview = replace_prices(snapshot, quotes, fx_rates)
    replace_snapshot(portfolio_path(), preview.model_dump_json(indent=2).encode())
    record_snapshot(preview, source="alpha_vantage", path=history_db_path())
    return {
        "updated": len(quotes),
        "unchanged": len(snapshot.positions) - len(quotes),
        "errors": errors,
        "message": "Snapshot atualizado localmente. Registros sem cotação permaneceram inalterados.",
    }
