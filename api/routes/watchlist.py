"""Rotas da watchlist."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response

from api.dependencies import Repositories as RepositoryBundle
from api.dependencies import get_repositories
from api.schemas.watchlist import WatchlistItemIn, WatchlistItemOut, WatchlistOut
from src.persistence.watchlist import WatchlistItem

router = APIRouter(prefix="/api", tags=["watchlist"])

Repositories = Annotated[RepositoryBundle, Depends(get_repositories)]


def _out(item: WatchlistItem) -> WatchlistItemOut:
    return WatchlistItemOut(
        asset_key=item.asset_key,
        name=item.name,
        asset_class=item.asset_class,
        note=item.note,
        created_at=item.created_at,
    )


@router.get("/watchlist", response_model=WatchlistOut)
def list_watchlist(repositories: Repositories) -> WatchlistOut:
    items = repositories.watchlist.list()
    return WatchlistOut(items=[_out(item) for item in items], total=len(items))


@router.post("/watchlist", response_model=WatchlistItemOut, status_code=201)
def add_watchlist(payload: WatchlistItemIn, repositories: Repositories) -> WatchlistItemOut:
    item = WatchlistItem(
        asset_key=payload.asset_key,
        name=payload.name,
        asset_class=payload.asset_class,
        note=payload.note,
        created_at=datetime.now(timezone.utc),
    )
    repositories.watchlist.add(item)
    return _out(item)


@router.delete("/watchlist/{asset_key:path}", status_code=204)
def remove_watchlist(asset_key: str, repositories: Repositories) -> Response:
    if not repositories.watchlist.remove(asset_key):
        raise HTTPException(status_code=404, detail="Ativo não está na watchlist.")
    return Response(status_code=204)
