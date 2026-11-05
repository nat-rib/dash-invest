"""Serviço da análise da carteira (Fase 4).

Reutiliza src.portfolio (valores/custos) e src.importer (leitura validada
do snapshot). Ausência de informação nunca é convertida em zero.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from src.importer import load_snapshot
from src.portfolio import (
    position_value, position_cost,
)
from api.config import portfolio_path


def _snapshot():
    path = portfolio_path()
    if not path.exists():
        raise FileNotFoundError(f"Snapshot não encontrado: {path}.")
    return load_snapshot(path)


def _consolidated_brl(position) -> tuple[Decimal | None, bool]:
    """Valor consolidado em BRL; None quando não comparável e sem conversão."""
    value = position_value(position)
    if value is None:
        return None, False
    if position.currency == "BRL":
        return value, True
    if position.converted_value_brl is not None:
        return position.converted_value_brl, True
    return None, False


def position_metrics(position) -> dict[str, Any]:
    value = position_value(position)
    cost = position_cost(position)
    comparable = value is not None and cost is not None
    gain = value - cost if comparable else None
    consolidated, known_brl = _consolidated_brl(position)
    return {
        "value": value,
        "cost": cost,
        "gain": gain,
        "return": (gain / cost) if comparable and cost > 0 else None,
        "consolidated_brl": consolidated,
        "known_brl": known_brl,
    }


def load_positions() -> list[tuple[int, object, dict[str, Any]]]:
    snapshot = _snapshot()
    return [
        (index, position, position_metrics(position))
        for index, position in enumerate(snapshot.positions)
    ]


def allocation() -> dict[str, Any]:
    snapshot = _snapshot()
    by_class: dict[str, Decimal] = {}
    by_institution: dict[str, Decimal] = {}
    counts: dict[str, int] = {}
    counts_institution: dict[str, int] = {}
    total = Decimal("0")
    known_positions = 0
    unknown_positions = 0
    for position in snapshot.positions:
        metrics = position_metrics(position)
        consolidated = metrics["consolidated_brl"]
        if consolidated is None:
            unknown_positions += 1
            continue
        known_positions += 1
        total += consolidated
        by_class[str(position.asset_class)] = by_class.get(str(position.asset_class), Decimal("0")) + consolidated
        counts[str(position.asset_class)] = counts.get(str(position.asset_class), 0) + 1
        by_institution[position.institution] = by_institution.get(position.institution, Decimal("0")) + consolidated
        counts_institution[position.institution] = counts_institution.get(position.institution, 0) + 1
    return {
        "total_brl": total,
        "known_positions": known_positions,
        "unknown_positions": unknown_positions,
        "by_class": _slices(by_class, counts, total),
        "by_institution": _slices(by_institution, counts_institution, total),
    }


def _slices(values: dict[str, Decimal], counts: dict[str, int], total: Decimal) -> list[dict[str, Any]]:
    return [
        {
            "name": name,
            "value": str(value),
            "share": str(value / total) if total > 0 else None,
            "positions": counts.get(name, 0),
        }
        for name, value in sorted(values.items(), key=lambda item: item[1], reverse=True)
    ]


def concentration() -> dict[str, Any]:
    snapshot = _snapshot()
    total = sum(
        (metrics["consolidated_brl"] for _, _, metrics in load_positions() if metrics["consolidated_brl"] is not None),
        Decimal("0"),
    )
    items: list[dict[str, Any]] = []
    comparable: list[dict[str, Any]] = []
    for index, position, metrics in load_positions():
        consolidated = metrics["consolidated_brl"]
        items.append({
            "index": index,
            "name": position.name,
            "institution": position.institution,
            "asset_class": str(position.asset_class),
            "consolidated_brl": str(consolidated) if consolidated is not None else None,
            "share": str(consolidated / total) if consolidated is not None and total > 0 else None,
        })
        if metrics["value"] is not None and metrics["cost"] is not None:
            comparable.append({
                "index": index,
                "name": position.name,
                "institution": position.institution,
                "cost_total": str(metrics["cost"]),
                "current_value": str(metrics["value"]),
                "currency": position.currency,
            })
    ordered = sorted(
        (item for item in items if item["consolidated_brl"] is not None),
        key=lambda item: Decimal(item["consolidated_brl"]), reverse=True,
    )
    return {"total_brl": str(total), "items": items, "top": ordered[:10], "comparable": comparable}


def position_detail(position_id: int) -> dict[str, Any]:
    snapshot = _snapshot()
    if position_id < 0 or position_id >= len(snapshot.positions):
        raise IndexError("Posição não encontrada neste snapshot.")
    position = snapshot.positions[position_id]
    metrics = position_metrics(position)
    return {
        "index": position_id,
        "name": position.name,
        "institution": position.institution,
        "asset_class": str(position.asset_class),
        "ticker": position.ticker,
        "currency": position.currency,
        "quantity": position.quantity,
        "average_cost": position.average_cost,
        "operation_cost": position.operation_cost,
        "current_price": position.current_price,
        "current_value": metrics["value"],
        "cost_total": metrics["cost"],
        "gain_loss": metrics["gain"],
        "unrealized_return": metrics["return"],
        "converted_value_brl": position.converted_value_brl,
        "conversion_rate_to_brl": position.conversion_rate_to_brl,
        "conversion_date": position.conversion_date,
        "consolidated_brl": metrics["consolidated_brl"],
        "indexer": position.indexer,
        "maturity_date": position.maturity_date,
        "application_date": position.application_date,
        "issuer": position.issuer,
        "annual_rate": position.annual_rate,
        "invested_amount": position.invested_amount,
        "dividends_received": position.dividends_received,
        "risk_category": position.risk_category,
        "liquidity_profile": position.liquidity_profile,
        "notes": position.notes,
        "snapshot_date": snapshot.snapshot_date,
    }


def position_list() -> dict[str, Any]:
    snapshot = _snapshot()
    positions = []
    for index, position, metrics in load_positions():
        positions.append({
            "index": index,
            "name": position.name,
            "institution": position.institution,
            "asset_class": str(position.asset_class),
            "currency": position.currency,
            "consolidated_brl": str(metrics["consolidated_brl"]) if metrics["consolidated_brl"] is not None else None,
        })
    return {"snapshot_date": snapshot.snapshot_date, "positions": positions}
