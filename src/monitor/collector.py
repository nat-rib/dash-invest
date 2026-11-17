"""Coleta de feeds RSS e persistência de sinais."""
from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256

from src.domain.signals import Signal
from src.monitor.config import MonitorConfig
from src.monitor.extraction import extract_assets
from src.monitor.rss import fetch_feed, parse_feed
from src.persistence.signals import SignalRepository


@dataclass(frozen=True)
class CollectionSummary:
    sources_ok: int
    sources_failed: int
    items: int
    inserted: int
    errors: tuple[str, ...]


def collect(
    config: MonitorConfig,
    repository: SignalRepository,
    *,
    issuers: Mapping[str, str] | None = None,
    fetcher: Callable[[str], bytes] = fetch_feed,
    now: datetime | None = None,
    sleep: float = 0.3,
) -> CollectionSummary:
    collected_at = now or datetime.now(timezone.utc)
    signals: list[Signal] = []
    errors: list[str] = []
    sources_ok = 0
    sources_failed = 0

    for source in config.sources:
        try:
            payload = fetcher(source.url)
            feed_items = parse_feed(payload)
        except Exception as error:  # noqa: BLE001 - uma fonte ruim não derruba o lote
            sources_failed += 1
            errors.append(f"{source.name}: {error}")
            continue

        sources_ok += 1
        for item in feed_items:
            text = f"{item.title}. {item.summary}"
            signals.append(
                Signal(
                    source=source.name,
                    url=item.link,
                    title=item.title,
                    summary=item.summary,
                    published_at=item.published_at,
                    collected_at=collected_at,
                    content_hash=sha256(text.encode("utf-8")).hexdigest(),
                    assets=tuple(extract_assets(text, issuers=issuers)),
                )
            )
        if sleep > 0 and len(config.sources) > 1:
            time.sleep(sleep)

    inserted = repository.record_many(signals)
    return CollectionSummary(
        sources_ok=sources_ok,
        sources_failed=sources_failed,
        items=len(signals),
        inserted=inserted,
        errors=tuple(errors),
    )
