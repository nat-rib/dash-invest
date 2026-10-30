"""Cálculos que respeitam moedas e ausência de informação."""
from decimal import Decimal
import pandas as pd

from src.schemas import PortfolioSnapshot


def position_value(position) -> Decimal | None:
    if position.current_value is not None:
        return position.current_value
    if position.quantity is not None and position.current_price is not None:
        return position.quantity * position.current_price
    return None


def position_cost(position) -> Decimal | None:
    if position.quantity is not None and position.average_cost is not None:
        return position.quantity * position.average_cost
    return None


def positions_frame(snapshot: PortfolioSnapshot) -> pd.DataFrame:
    rows = []
    for pos in snapshot.positions:
        value, cost = position_value(pos), position_cost(pos)
        comparable = value is not None and cost is not None
        gain = value - cost if comparable else None
        rows.append({
            "Instituição": pos.institution, "Classe": pos.asset_class, "Ticker": pos.ticker,
            "Nome": pos.name, "Quantidade": float(pos.quantity) if pos.quantity is not None else None,
            "Preço médio": float(pos.average_cost) if pos.average_cost is not None else None,
            "Preço atual": float(pos.current_price) if pos.current_price is not None else None,
            "Valor atual": float(value) if value is not None else None,
            "Custo total": float(cost) if cost is not None else None,
            "Ganho/perda": float(gain) if gain is not None else None,
            "Rentabilidade": float(gain / cost) if comparable and cost > 0 else None,
            "Moeda": pos.currency, "Indexador": pos.indexer,
            "Vencimento": pos.maturity_date, "Referência": snapshot.snapshot_date,
            "Data de aplicação": pos.application_date, "Emissor": pos.issuer,
            "Taxa anual": float(pos.annual_rate) if pos.annual_rate is not None else None,
            "Valor aplicado informado": float(pos.invested_amount) if pos.invested_amount is not None else None,
            "Categoria de risco": pos.risk_category, "Liquidez": pos.liquidity_profile,
            "Observações": pos.notes,
        })
    return pd.DataFrame(rows)


def brl_frame(frame: pd.DataFrame) -> pd.DataFrame:
    return frame[(frame["Moeda"] == "BRL") & frame["Valor atual"].notna()].copy()


def consolidated_total(frame: pd.DataFrame) -> float:
    return float(brl_frame(frame)["Valor atual"].sum())


def duplicate_positions(snapshot: PortfolioSnapshot) -> list[tuple[str, str, str]]:
    seen, duplicates = set(), []
    for p in snapshot.positions:
        key = (p.institution, p.ticker or p.name, p.currency)
        if key in seen:
            duplicates.append(key)
        seen.add(key)
    return duplicates
