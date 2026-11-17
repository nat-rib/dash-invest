"""Rotas do monitor de ativos (sinais + ranking)."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies import Repositories as RepositoryBundle
from api.dependencies import get_repositories
from api.schemas.monitor import (
    AssetMentionOut,
    CandidateListOut,
    CandidateOut,
    MonitorSourceListOut,
    MonitorSourceOut,
    SignalListOut,
    SignalOut,
)
from api.services import monitor_service
from src.monitor.config import load_config

router = APIRouter(prefix="/api", tags=["monitor"])

Repositories = Annotated[RepositoryBundle, Depends(get_repositories)]


@router.get("/monitor/candidates", response_model=CandidateListOut)
def monitor_candidates(
    repositories: Repositories,
    limit: int = Query(default=50, ge=1, le=200),
    min_score: float = Query(default=0.0, ge=0.0, le=100.0),
    asset_class: str | None = Query(default=None),
) -> CandidateListOut:
    try:
        items = monitor_service.candidates(
            repositories,
            limit=limit,
            min_score=min_score,
            asset_class=asset_class,
        )
    except (FileNotFoundError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return CandidateListOut(
        items=[
            CandidateOut(
                key=item.key,
                name=item.name,
                asset_class=item.asset_class,
                score=item.score,
                confidence=item.confidence,
                components=item.components,
                reasons=list(item.reasons),
                missing=list(item.missing),
                sources=list(item.sources),
                signal_count=item.signal_count,
                last_seen=item.last_seen,
            )
            for item in items
        ],
        total=len(items),
    )


@router.get("/monitor/signals", response_model=SignalListOut)
def monitor_signals(
    repositories: Repositories,
    limit: int = Query(default=100, ge=1, le=500),
    source: str | None = Query(default=None),
    lookback_days: int | None = Query(default=30, ge=1, le=365),
    with_assets: bool = Query(default=True),
) -> SignalListOut:
    items = monitor_service.signals(
        repositories,
        limit=limit,
        source=source,
        lookback_days=lookback_days,
        with_assets=with_assets,
    )
    return SignalListOut(
        items=[
            SignalOut(
                source=item.source,
                title=item.title,
                url=item.url,
                summary=item.summary,
                published_at=item.published_at,
                collected_at=item.collected_at,
                assets=[
                    AssetMentionOut(
                        key=asset.key,
                        name=asset.name,
                        asset_class=asset.asset_class,
                        confidence=asset.confidence,
                        cnpj=asset.cnpj,
                    )
                    for asset in item.assets
                ],
            )
            for item in items
        ],
        total=len(items),
    )


@router.get("/monitor/sources", response_model=MonitorSourceListOut)
def monitor_sources() -> MonitorSourceListOut:
    config = load_config()
    return MonitorSourceListOut(
        items=[
            MonitorSourceOut(name=source.name, url=source.url, weight=source.weight)
            for source in config.sources
        ]
    )
