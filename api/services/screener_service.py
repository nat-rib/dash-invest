"""Serviço do screener: últimas observações anuais por emissor."""
from __future__ import annotations

from datetime import date
from typing import Any

from src.analytics.screener import ScreenerRow, build_rows, filter_and_sort, SCREENER_METRICS


def screen(
    repositories: Any,
    *,
    min_roe: float | None = None,
    min_net_margin: float | None = None,
    min_roa: float | None = None,
    sort_by: str = "roe",
    descending: bool = True,
) -> list[ScreenerRow]:
    observations = repositories.observations.latest_by_series(
        provider="cvm", metrics=SCREENER_METRICS
    )
    series: dict[str, dict[str, tuple[float, date]]] = {}
    for observation in observations:
        if not observation.instrument_id:
            continue
        series.setdefault(observation.instrument_id, {})[observation.metric] = (
            float(observation.value),
            observation.reference_date,
        )

    names = {issuer.cnpj: issuer.name for issuer in repositories.issuers.list()}
    return filter_and_sort(
        build_rows(series, names),
        min_roe=min_roe,
        min_net_margin=min_net_margin,
        min_roa=min_roa,
        sort_by=sort_by,
        descending=descending,
    )
