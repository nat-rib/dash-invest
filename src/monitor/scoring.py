"""Ranking determinístico de aderência de ativos à carteira.

Componentes explícitos: lacuna de alocação, concentração, fundamentos,
valuation, momento/risco e força do sinal. Dado ausente fica `None` e reduz a
confiança — nunca é convertido em zero.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from src.domain.signals import Signal

WEIGHTS: dict[str, float] = {
    "allocation": 0.30,
    "concentration": 0.15,
    "fundamentals": 0.20,
    "valuation": 0.10,
    "momentum": 0.15,
    "signal": 0.10,
}

CLASS_BUCKETS = {
    "acao": "acao",
    "fii": "fii",
    "etf": "etf",
    "cripto": "cripto",
    "exterior": "exterior",
    "renda_fixa": "renda_fixa",
    "credito_privado_coletivo": "renda_fixa",
    "fundo": "outros",
    "caixa": "caixa",
    "outros": "outros",
}

CLASS_LABELS = {
    "renda_fixa": "Renda fixa",
    "acao": "Ações",
    "fii": "FIIs",
    "etf": "ETFs",
    "cripto": "Cripto",
    "exterior": "Exterior",
    "outros": "Outros",
}


@dataclass(frozen=True)
class PortfolioContext:
    total_brl: float
    allocation: dict[str, float]
    holdings: dict[str, float]
    targets: dict[str, float]
    max_asset_share: float = 0.10


@dataclass(frozen=True)
class SignalExample:
    source: str
    title: str
    url: str
    published_at: datetime | None


@dataclass(frozen=True)
class SignalAggregate:
    key: str
    name: str
    asset_class: str
    cnpj: str | None
    sources: tuple[str, ...]
    signal_count: int
    last_seen: datetime
    max_weight: float
    examples: tuple[SignalExample, ...] = ()


@dataclass(frozen=True)
class Candidate:
    key: str
    name: str
    asset_class: str
    score: float
    confidence: float
    components: dict[str, float | None] = field(default_factory=dict)
    reasons: tuple[str, ...] = ()
    missing: tuple[str, ...] = ()
    sources: tuple[str, ...] = ()
    signal_count: int = 0
    last_seen: datetime | None = None
    cnpj: str | None = None
    price_provider: str | None = None
    price_instrument: str | None = None
    examples: tuple[SignalExample, ...] = ()


def aggregate_signals(
    signals: list[Signal],
    *,
    source_weights: dict[str, float],
    now: datetime,
    lookback_days: int,
) -> list[SignalAggregate]:
    cutoff = now - timedelta(days=lookback_days)
    grouped: dict[str, dict[str, object]] = {}

    for signal in signals:
        when = signal.published_at or signal.collected_at
        if when < cutoff:
            continue
        weight = source_weights.get(signal.source, 1.0)
        for asset in signal.assets:
            entry = grouped.setdefault(
                asset.key,
                {
                    "name": asset.name,
                    "asset_class": asset.asset_class,
                    "cnpj": asset.cnpj,
                    "confidence": asset.confidence,
                    "sources": set(),
                    "count": 0,
                    "last_seen": when,
                    "max_weight": weight,
                    "examples": [],
                },
            )
            if asset.confidence >= float(entry["confidence"]):
                entry["name"] = asset.name
                entry["asset_class"] = asset.asset_class
                entry["confidence"] = asset.confidence
                if asset.cnpj:
                    entry["cnpj"] = asset.cnpj
            cast_sources = entry["sources"]
            assert isinstance(cast_sources, set)
            cast_sources.add(signal.source)
            entry["count"] = int(entry["count"]) + 1
            entry["last_seen"] = max(entry["last_seen"], when)  # type: ignore[type-var]
            entry["max_weight"] = max(float(entry["max_weight"]), weight)
            examples = entry["examples"]
            assert isinstance(examples, list)
            if len(examples) < 3 and all(example.url != signal.url for example in examples):
                examples.append(
                    SignalExample(
                        source=signal.source,
                        title=signal.title,
                        url=signal.url,
                        published_at=signal.published_at,
                    )
                )

    aggregates = [
        SignalAggregate(
            key=key,
            name=str(entry["name"]),
            asset_class=str(entry["asset_class"]),
            cnpj=entry["cnpj"] if isinstance(entry["cnpj"], str) else None,
            sources=tuple(sorted(entry["sources"])),  # type: ignore[arg-type]
            signal_count=int(entry["count"]),
            last_seen=entry["last_seen"],  # type: ignore[arg-type]
            max_weight=float(entry["max_weight"]),
            examples=tuple(entry["examples"]),  # type: ignore[arg-type]
        )
        for key, entry in grouped.items()
    ]
    aggregates.sort(key=lambda item: (item.signal_count, item.last_seen), reverse=True)
    return aggregates


def _roe_score(value: float) -> float:
    if value >= 0.20:
        return 1.0
    if value >= 0.15:
        return 0.9
    if value >= 0.10:
        return 0.75
    if value >= 0.05:
        return 0.55
    if value >= 0:
        return 0.35
    return 0.1


def _margin_score(value: float) -> float:
    if value >= 0.20:
        return 1.0
    if value >= 0.10:
        return 0.8
    if value >= 0.05:
        return 0.6
    if value >= 0:
        return 0.4
    return 0.2


def _momentum_score(return_value: float, volatility: float) -> float:
    if return_value >= 0.15:
        base = 1.0
    elif return_value >= 0.05:
        base = 0.8
    elif return_value >= 0:
        base = 0.6
    elif return_value >= -0.10:
        base = 0.35
    else:
        base = 0.15
    if volatility > 0.50:
        base *= 0.75
    elif volatility > 0.35:
        base *= 0.9
    return base


def rank_candidates(
    aggregates: list[SignalAggregate],
    context: PortfolioContext,
    *,
    fundamentals: dict[str, dict[str, float | None]],
    momentum: dict[str, dict[str, float]],
    now: datetime,
) -> list[Candidate]:
    candidates: list[Candidate] = []
    for aggregate in aggregates:
        bucket = CLASS_BUCKETS.get(aggregate.asset_class, "outros")
        target = context.targets.get(bucket, 0.0)
        current = context.allocation.get(bucket, 0.0)
        gap = max(0.0, target - current)
        allocation_score = min(1.0, gap / 0.10) if target > 0 else 0.0

        if aggregate.key.startswith("ticker:"):
            ticker = aggregate.key.split(":", 1)[1]
            share = context.holdings.get(ticker, 0.0)
            concentration_score = 1.0 - min(
                1.0, share / context.max_asset_share if context.max_asset_share > 0 else 1.0
            )
        else:
            concentration_score = 1.0

        data = fundamentals.get(aggregate.cnpj) if aggregate.cnpj else None
        fundamentals_score: float | None = None
        fundamental_reason: str | None = None
        if data:
            parts: list[float] = []
            roe = data.get("roe")
            margin = data.get("net_margin")
            if roe is not None:
                parts.append(_roe_score(float(roe)))
            if margin is not None:
                parts.append(_margin_score(float(margin)))
            if parts:
                fundamentals_score = sum(parts) / len(parts)
                year = data.get("year")
                fundamental_reason = (
                    f"ROE {float(roe or 0) * 100:.1f}% · margem {float(margin or 0) * 100:.1f}%"
                    + (f" ({int(year)})" if year else "")
                )

        momentum_score: float | None = None
        momentum_reason: str | None = None
        price = momentum.get(aggregate.key)
        if price and price.get("points", 0) >= 20:
            momentum_score = _momentum_score(
                price.get("return", 0.0), price.get("volatility", 0.0)
            )
            momentum_reason = (
                f"retorno 3M {price.get('return', 0.0) * 100:.1f}% · "
                f"vol {price.get('volatility', 0.0) * 100:.1f}%"
            )

        days = max(0.0, (now - aggregate.last_seen).total_seconds() / 86400)
        recency = math.exp(-days / 7)
        diversity = min(1.0, len(aggregate.sources) / 3)
        signal_score = min(
            1.0,
            (0.6 * recency + 0.4 * diversity) * min(1.2, aggregate.max_weight),
        )

        components: dict[str, float | None] = {
            "allocation": allocation_score,
            "concentration": concentration_score,
            "fundamentals": fundamentals_score,
            "valuation": None,
            "momentum": momentum_score,
            "signal": signal_score,
        }
        available = {name: value for name, value in components.items() if value is not None}
        total_weight = sum(WEIGHTS[name] for name in available)
        raw = (
            sum(WEIGHTS[name] * float(value) for name, value in available.items())
            / total_weight
            if total_weight
            else 0.0
        )
        coverage = total_weight / sum(WEIGHTS.values())
        score = raw * (0.7 + 0.3 * coverage) * 100

        reasons: list[str] = []
        if target > 0 and gap > 0:
            reasons.append(
                f"{CLASS_LABELS.get(bucket, bucket)} está {gap * 100:.1f} p.p. "
                f"abaixo do alvo de {target * 100:.0f}%"
            )
        elif target > 0:
            reasons.append(f"{CLASS_LABELS.get(bucket, bucket)} já está no alvo")
        if fundamental_reason:
            reasons.append(fundamental_reason)
        if momentum_reason:
            reasons.append(momentum_reason)
        reasons.append(
            f"{aggregate.signal_count} sinal(is) de {len(aggregate.sources)} fonte(s)"
        )

        missing = [
            label
            for name, label in (
                ("fundamentals", "fundamentos"),
                ("valuation", "valuation"),
                ("momentum", "série de preço"),
            )
            if components[name] is None
        ]

        candidates.append(
            Candidate(
                key=aggregate.key,
                name=aggregate.name,
                asset_class=aggregate.asset_class,
                score=round(score, 2),
                confidence=round(coverage, 3),
                components=components,
                reasons=tuple(reasons),
                missing=tuple(missing),
                sources=aggregate.sources,
                signal_count=aggregate.signal_count,
                last_seen=aggregate.last_seen,
                cnpj=aggregate.cnpj,
                examples=aggregate.examples,
            )
        )

    candidates.sort(key=lambda item: (item.score, item.last_seen or now), reverse=True)
    return candidates


def fundamentals_from_observations(
    observations: list,
) -> dict[str, dict[str, float | None]]:
    """Monta ROE/margem por CNPJ a partir das últimas observações anuais."""
    by_instrument: dict[str, dict[str, float]] = {}
    years: dict[str, int] = {}
    for item in observations:
        instrument = item.instrument_id or ""
        if not instrument.startswith("cnpj:"):
            continue
        cnpj = instrument.split(":", 1)[1]
        by_instrument.setdefault(cnpj, {})[item.metric] = float(item.value)
        years[cnpj] = max(years.get(cnpj, 0), item.reference_date.year)

    result: dict[str, dict[str, float | None]] = {}
    for cnpj, metrics in by_instrument.items():
        revenue = metrics.get("revenue")
        net = metrics.get("net_income")
        equity = metrics.get("equity")
        margin = net / revenue if revenue and net is not None and revenue > 0 else None
        roe = net / equity if equity and net is not None and equity > 0 else None
        result[cnpj] = {
            "roe": roe,
            "net_margin": margin,
            "year": years.get(cnpj),
        }
    return result
