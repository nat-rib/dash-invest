"""Leitura de observações externas com proveniência (Fase 3: data platform)."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from api.dependencies import Repositories as RepositoryBundle
from api.dependencies import get_repositories
from api.schemas.observations import (
    ObservationListOut,
    ObservationOut,
    ObservationSeriesOut,
    ObservationSeriesPoint,
)

router = APIRouter(prefix="/api", tags=["data"])

Repositories = Annotated[RepositoryBundle, Depends(get_repositories)]


@router.get("/data/observations", response_model=ObservationListOut)
def list_observations(
    repositories: Repositories,
    provider: str | None = Query(default=None),
    instrument_id: str | None = Query(default=None),
    metric: str | None = Query(default=None),
    include_superseded: bool = Query(default=False),
    limit: int = Query(default=200, ge=1, le=2000),
    offset: int = Query(default=0, ge=0),
) -> ObservationListOut:
    repository = repositories.observations
    items = repository.list(
        provider=provider,
        instrument_id=instrument_id,
        metric=metric,
        include_superseded=include_superseded,
        limit=limit,
        offset=offset,
    )
    total = repository.count(
        provider=provider,
        instrument_id=instrument_id,
        metric=metric,
        include_superseded=include_superseded,
    )
    return ObservationListOut(
        items=[ObservationOut.model_validate(item) for item in items],
        total=total,
    )


@router.get("/data/observations/series", response_model=ObservationSeriesOut)
def observation_series(
    repositories: Repositories,
    provider: str = Query(...),
    metric: str = Query(...),
    instrument_id: str | None = Query(default=None),
) -> ObservationSeriesOut:
    observations = repositories.observations.list(
        provider=provider,
        metric=metric,
        instrument_id=instrument_id,
    )
    return ObservationSeriesOut(
        provider=provider,
        instrument_id=instrument_id,
        metric=metric,
        points=[
            ObservationSeriesPoint(
                reference_date=item.reference_date,
                published_at=item.published_at,
                value=item.value,
                currency=item.currency,
            )
            for item in observations
        ],
    )
