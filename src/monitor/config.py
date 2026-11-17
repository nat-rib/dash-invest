"""Configuração do monitor: alvos de alocação e fontes RSS."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_TARGETS: dict[str, float] = {
    "renda_fixa": 0.60,
    "acao": 0.15,
    "fii": 0.10,
    "etf": 0.05,
    "cripto": 0.05,
    "exterior": 0.05,
}
DEFAULT_MAX_ASSET_SHARE = 0.10
DEFAULT_LOOKBACK_DAYS = 30


@dataclass(frozen=True)
class Source:
    name: str
    url: str
    weight: float = 1.0
    hint: str | None = None


DEFAULT_SOURCES: tuple[Source, ...] = (
    Source("InfoMoney", "https://www.infomoney.com.br/feed/", 1.0),
    Source(
        "Google News — Money Times",
        "https://news.google.com/rss/search?q=site%3Amoneytimes.com.br+investimentos+when%3A7d&hl=pt-BR&gl=BR&ceid=BR:pt-419",
        0.9,
    ),
    Source("Exame", "https://exame.com/feed/", 0.9),
    Source("Brazil Journal", "https://braziljournal.com/feed/", 1.0),
    Source("Suno Notícias", "https://www.suno.com.br/noticias/feed/", 0.9),
    Source("CVM", "https://www.gov.br/cvm/pt-br/assuntos/noticias/RSS", 1.2),
    Source(
        "Google News — Tesouro Direto",
        "https://news.google.com/rss/search?q=tesouro+direto&hl=pt-BR&gl=BR&ceid=BR:pt-419",
        0.7,
    ),
    Source(
        "Google News — Tesouro taxas",
        "https://news.google.com/rss/search?q=Tesouro+Direto+taxas&hl=pt-BR&gl=BR&ceid=BR:pt-419",
        0.7,
    ),
    Source(
        "Google News — CDB e renda fixa",
        "https://news.google.com/rss/search?q=CDB+renda+fixa&hl=pt-BR&gl=BR&ceid=BR:pt-419",
        0.7,
    ),
    Source(
        "Google News — CDB banco privado",
        "https://news.google.com/rss/search?q=CDB+banco+privado&hl=pt-BR&gl=BR&ceid=BR:pt-419",
        0.75,
        hint="cdb",
    ),
    Source(
        "Google News — CDB bancos digitais",
        "https://news.google.com/rss/search?q=CDB+bancos+digitais&hl=pt-BR&gl=BR&ceid=BR:pt-419",
        0.7,
        hint="cdb",
    ),
    Source(
        "Google News — CDB Nubank/Inter/C6/BTG",
        "https://news.google.com/rss/search?q=CDB+%28Nubank+OR+Inter+OR+C6+OR+BTG%29&hl=pt-BR&gl=BR&ceid=BR:pt-419",
        0.7,
        hint="cdb",
    ),
    Source(
        "Google News — CDB banco Master",
        "https://news.google.com/rss/search?q=CDB+banco+Master&hl=pt-BR&gl=BR&ceid=BR:pt-419",
        0.65,
        hint="cdb",
    ),
    Source(
        "Google News — CDB Nubank (30d)",
        "https://news.google.com/rss/search?q=CDB+Nubank+when%3A30d&hl=pt-BR&gl=BR&ceid=BR:pt-419",
        0.7,
        hint="cdb",
    ),
    Source(
        "Google News — CDB Inter (30d)",
        "https://news.google.com/rss/search?q=CDB+Inter+when%3A30d&hl=pt-BR&gl=BR&ceid=BR:pt-419",
        0.7,
        hint="cdb",
    ),
    Source(
        "Google News — CDB C6 (30d)",
        "https://news.google.com/rss/search?q=CDB+C6+when%3A30d&hl=pt-BR&gl=BR&ceid=BR:pt-419",
        0.7,
        hint="cdb",
    ),
    Source(
        "Google News — CDB BTG (30d)",
        "https://news.google.com/rss/search?q=CDB+BTG+when%3A30d&hl=pt-BR&gl=BR&ceid=BR:pt-419",
        0.7,
        hint="cdb",
    ),
    Source(
        "Google News — CDB taxas (7d)",
        "https://news.google.com/rss/search?q=CDB+taxas+when%3A7d&hl=pt-BR&gl=BR&ceid=BR:pt-419",
        0.75,
        hint="cdb",
    ),
    Source(
        "Google News — LCI e LCA",
        "https://news.google.com/rss/search?q=LCI+LCA+bancos&hl=pt-BR&gl=BR&ceid=BR:pt-419",
        0.7,
    ),
    Source(
        "Google News — fundos imobiliários",
        "https://news.google.com/rss/search?q=fundos+imobiliarios&hl=pt-BR&gl=BR&ceid=BR:pt-419",
        0.7,
    ),
    Source(
        "Google News — ETF",
        "https://news.google.com/rss/search?q=ETF+Brasil&hl=pt-BR&gl=BR&ceid=BR:pt-419",
        0.7,
    ),
    Source(
        "Google News — cripto",
        "https://news.google.com/rss/search?q=criptomoedas&hl=pt-BR&gl=BR&ceid=BR:pt-419",
        0.6,
    ),
    Source(
        "Google News — Valor",
        "https://news.google.com/rss/search?q=site%3Avalor.globo.com+investimentos&hl=pt-BR&gl=BR&ceid=BR:pt-419",
        0.8,
    ),
    Source(
        "Google News — B3",
        "https://news.google.com/rss/search?q=site%3Ab3.com.br%2Fnoticias&hl=pt-BR&gl=BR&ceid=BR:pt-419",
        0.8,
    ),
)


@dataclass(frozen=True)
class MonitorConfig:
    targets: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_TARGETS))
    max_asset_share: float = DEFAULT_MAX_ASSET_SHARE
    lookback_days: int = DEFAULT_LOOKBACK_DAYS
    sources: tuple[Source, ...] = DEFAULT_SOURCES


def load_config(path: str | Path | None = None) -> MonitorConfig:
    """Carrega overrides de um JSON; ausente usa os padrões."""
    candidate = path or os.environ.get("MONITOR_CONFIG_PATH")
    if not candidate:
        return MonitorConfig()
    config_path = Path(candidate)
    if not config_path.exists():
        return MonitorConfig()

    data = json.loads(config_path.read_text(encoding="utf-8"))
    targets = dict(DEFAULT_TARGETS)
    targets.update(
        {key: float(value) for key, value in data.get("targets", {}).items()}
    )
    sources = tuple(
        Source(
            name=item["name"],
            url=item["url"],
            weight=float(item.get("weight", 1.0)),
            hint=item.get("hint"),
        )
        for item in data.get("sources", [])
    ) or DEFAULT_SOURCES
    return MonitorConfig(
        targets=targets,
        max_asset_share=float(data.get("max_asset_share", DEFAULT_MAX_ASSET_SHARE)),
        lookback_days=int(data.get("lookback_days", DEFAULT_LOOKBACK_DAYS)),
        sources=sources,
    )
