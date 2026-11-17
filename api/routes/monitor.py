"""Rotas do monitor de ativos (sinais + ranking)."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies import Repositories as RepositoryBundle
from api.dependencies import get_repositories
from api.schemas.monitor import (
    AlertConfigOut,
    AlertListOut,
    AlertOut,
    AssetMentionOut,
    BacktestOut,
    CandidateListOut,
    CandidateOut,
    MonitorSourceListOut,
    MonitorSourceOut,
    ScoreBucketOut,
    SignalExampleOut,
    SignalListOut,
    SignalOut,
)
from api.services import monitor_service
from src.monitor.alerts import settings_from_env
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
                cnpj=item.cnpj,
                price_provider=item.price_provider,
                price_instrument=item.price_instrument,
                examples=[
                    SignalExampleOut(
                        source=example.source,
                        title=example.title,
                        url=example.url,
                        published_at=example.published_at,
                    )
                    for example in item.examples
                ],
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


@router.get("/monitor/backtest", response_model=BacktestOut)
def monitor_backtest(
    repositories: Repositories,
    horizon_days: int = Query(default=30, ge=7, le=365),
    min_samples: int = Query(default=5, ge=1, le=100),
) -> BacktestOut:
    report = monitor_service.backtest(
        repositories, horizon_days=horizon_days, min_samples=min_samples
    )
    return BacktestOut(
        snapshots=report.snapshots,
        evaluated=report.evaluated,
        horizon_days=report.horizon_days,
        buckets=[
            ScoreBucketOut(
                label=bucket.label,
                count=bucket.count,
                average_return=bucket.average_return,
                hit_rate=bucket.hit_rate,
            )
            for bucket in report.buckets
        ],
        rank_correlation=report.rank_correlation,
        top_average=report.top_average,
        bottom_average=report.bottom_average,
        spread=report.spread,
        available=report.available,
        reason=report.reason,
    )


@router.get("/monitor/alerts", response_model=AlertListOut)
def monitor_alerts(
    repositories: Repositories,
    limit: int = Query(default=20, ge=1, le=200),
) -> AlertListOut:
    items = repositories.alerts.list(limit=limit)
    return AlertListOut(
        items=[
            AlertOut(
                asset_key=item.asset_key,
                name=item.name,
                score=item.score,
                channel=item.channel,
                message=item.message,
                sent_at=item.sent_at,
            )
            for item in items
        ],
        total=len(items),
    )


@router.get("/monitor/alert-config", response_model=AlertConfigOut)
def monitor_alert_config() -> AlertConfigOut:
    settings = settings_from_env()
    return AlertConfigOut(
        channels=list(settings.channels),
        min_score=settings.min_score,
        cooldown_days=settings.cooldown_days,
        max_alerts=settings.max_alerts,
        telegram_configured=bool(
            settings.telegram_bot_token and settings.telegram_chat_id
        ),
        email_configured=bool(
            settings.smtp_host and settings.email_from and settings.email_to
        ),
    )
