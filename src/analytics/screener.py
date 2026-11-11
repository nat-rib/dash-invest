"""Screener fundamentalista determinístico sobre observações da CVM.

Cada razão só é calculada quando numerador e denominador existem e o
denominador é positivo; caso contrário permanece indisponível (não zero).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

SCREENER_METRICS = ("revenue", "net_income", "equity", "total_assets")
SORT_FIELDS = (
    "revenue",
    "net_income",
    "net_margin",
    "roe",
    "roa",
    "asset_turnover",
)


@dataclass(frozen=True)
class ScreenerRow:
    cnpj: str
    name: str | None
    reference_date: date | None
    revenue: float | None
    net_income: float | None
    equity: float | None
    total_assets: float | None
    net_margin: float | None
    roe: float | None
    roa: float | None
    asset_turnover: float | None


def _ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator <= 0:
        return None
    return numerator / denominator


def build_rows(
    series: dict[str, dict[str, tuple[float, date]]],
    names: dict[str, str],
) -> list[ScreenerRow]:
    rows: list[ScreenerRow] = []
    for instrument_id, metrics in series.items():
        cnpj = instrument_id.split(":", 1)[-1]
        values = {metric: value for metric, (value, _) in metrics.items()}
        reference = max((day for _, day in metrics.values()), default=None)
        revenue = values.get("revenue")
        net_income = values.get("net_income")
        equity = values.get("equity")
        assets = values.get("total_assets")
        rows.append(
            ScreenerRow(
                cnpj=cnpj,
                name=names.get(cnpj),
                reference_date=reference,
                revenue=revenue,
                net_income=net_income,
                equity=equity,
                total_assets=assets,
                net_margin=_ratio(net_income, revenue),
                roe=_ratio(net_income, equity),
                roa=_ratio(net_income, assets),
                asset_turnover=_ratio(revenue, assets),
            )
        )
    return rows


def filter_and_sort(
    rows: list[ScreenerRow],
    *,
    min_roe: float | None = None,
    min_net_margin: float | None = None,
    min_roa: float | None = None,
    sort_by: str = "roe",
    descending: bool = True,
) -> list[ScreenerRow]:
    if sort_by not in SORT_FIELDS:
        raise ValueError(f"ordenação inválida: {sort_by}")

    def passes(row: ScreenerRow) -> bool:
        for value, minimum in (
            (row.roe, min_roe),
            (row.net_margin, min_net_margin),
            (row.roa, min_roa),
        ):
            if minimum is None:
                continue
            if value is None or value < minimum:
                return False
        return True

    def sort_key(row: ScreenerRow) -> tuple[int, float]:
        value = getattr(row, sort_by)
        if value is None:
            return (1, 0.0)
        return (0, -value if descending else value)

    filtered = [row for row in rows if passes(row)]
    filtered.sort(key=sort_key)
    return filtered
