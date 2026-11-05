"""Rota da visão geral consolidada (Fase 1 da experiência mobile)."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from api.dependencies import get_repositories
from api.schemas.overview import OverviewOut
from api.services import overview_service

router = APIRouter(prefix="/api", tags=["overview"])
Repositories = Annotated[object, Depends(get_repositories)]


@router.get("/overview", response_model=OverviewOut)
def overview(
    repositories: Repositories,
    portfolio_id: str = Query(default=""),  # noqa: A002 - nome do domínio
) -> OverviewOut:
    return overview_service.build_overview(
        repositories, portfolio_id=portfolio_id or None,
    )
