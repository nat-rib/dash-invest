"""Rotas do Portfolio Fit (Fase 6)."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import Repositories as RepositoryBundle
from api.dependencies import get_repositories
from api.schemas.fit import (
    CorrelationPairOut,
    ExposureSliceOut,
    FitPositionOut,
    PortfolioFitOut,
)
from api.services import fit_service

router = APIRouter(prefix="/api", tags=["fit"])

Repositories = Annotated[RepositoryBundle, Depends(get_repositories)]


@router.get("/fit", response_model=PortfolioFitOut)
def portfolio_fit(repositories: Repositories) -> PortfolioFitOut:
    try:
        fit = fit_service.build(repositories)
    except FileNotFoundError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return PortfolioFitOut(
        total_brl=fit.total_brl,
        positions=fit.positions,
        by_class=[
            ExposureSliceOut(name=item.name, value=item.value, share=item.share, positions=item.positions)
            for item in fit.by_class
        ],
        by_institution=[
            ExposureSliceOut(name=item.name, value=item.value, share=item.share, positions=item.positions)
            for item in fit.by_institution
        ],
        by_currency=[
            ExposureSliceOut(name=item.name, value=item.value, share=item.share, positions=item.positions)
            for item in fit.by_currency
        ],
        top_positions=[
            FitPositionOut(
                name=item.name,
                institution=item.institution,
                asset_class=item.asset_class,
                currency=item.currency,
                value_brl=item.value_brl,
                share=item.share,
                liquidity=item.liquidity,
                risk_category=item.risk_category,
            )
            for item in fit.top_positions
        ],
        herfindahl=fit.herfindahl,
        liquidity_coverage=fit.liquidity_coverage,
        credit_coverage=fit.credit_coverage,
        correlations=[
            CorrelationPairOut(
                left=item.left,
                right=item.right,
                correlation=item.correlation,
                observations=item.observations,
            )
            for item in fit.correlations
        ],
        unavailable=list(fit.unavailable),
    )
