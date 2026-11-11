"""Rotas do screener fundamentalista e do valuation (Fase 5)."""
from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies import Repositories as RepositoryBundle
from api.dependencies import get_repositories
from api.schemas.screener import (
    DcfOut,
    DcfProjectionOut,
    DcfRequest,
    ScreenerOut,
    ScreenerRowOut,
)
from api.services import screener_service
from src.analytics.valuation import discounted_cash_flow

router = APIRouter(prefix="/api", tags=["screener"])

Repositories = Annotated[RepositoryBundle, Depends(get_repositories)]


@router.get("/screener", response_model=ScreenerOut)
def screener(
    repositories: Repositories,
    min_roe: float | None = Query(default=None),
    min_net_margin: float | None = Query(default=None),
    min_roa: float | None = Query(default=None),
    sort_by: str = Query(default="roe"),
    order: Literal["asc", "desc"] = Query(default="desc"),
    limit: int = Query(default=100, ge=1, le=500),
) -> ScreenerOut:
    try:
        rows = screener_service.screen(
            repositories,
            min_roe=min_roe,
            min_net_margin=min_net_margin,
            min_roa=min_roa,
            sort_by=sort_by,
            descending=order == "desc",
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return ScreenerOut(
        items=[ScreenerRowOut.model_validate(row) for row in rows[:limit]],
        total=len(rows),
    )


@router.post("/valuation/dcf", response_model=DcfOut, tags=["valuation"])
def dcf(payload: DcfRequest) -> DcfOut:
    try:
        result = discounted_cash_flow(**payload.model_dump())
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return DcfOut(
        present_value_explicit=result.present_value_explicit,
        present_value_terminal=result.present_value_terminal,
        enterprise_value=result.enterprise_value,
        projections=[
            DcfProjectionOut(
                year=item.year,
                cash_flow=item.cash_flow,
                present_value=item.present_value,
            )
            for item in result.projections
        ],
    )
