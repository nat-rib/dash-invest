from datetime import datetime, timedelta, timezone

from src.domain.signals import AssetMention, Signal
from src.monitor.scoring import (
    PortfolioContext,
    aggregate_signals,
    rank_candidates,
)

NOW = datetime(2026, 11, 16, 12, tzinfo=timezone.utc)


def signal(source: str, assets: tuple[AssetMention, ...], hours_ago: int = 1) -> Signal:
    return Signal(
        source=source,
        title=f"Notícia {source}",
        url=f"https://example/{source}/{hours_ago}",
        published_at=NOW - timedelta(hours=hours_ago),
        collected_at=NOW,
        assets=assets,
    )


def test_agrega_fontes_e_prioriza_lacuna_de_renda_fixa():
    context = PortfolioContext(
        total_brl=1000,
        allocation={"renda_fixa": 0.10, "acao": 0.30},
        holdings={"PETR4": 0.30},
        targets={"renda_fixa": 0.60, "acao": 0.15, "fii": 0.10, "etf": 0.05, "cripto": 0.05},
        max_asset_share=0.10,
    )
    signals = [
        signal("InfoMoney", (AssetMention(key="fixed_income:tesouro-selic", name="Tesouro Selic", asset_class="renda_fixa", confidence=0.75),)),
        signal("Money Times", (AssetMention(key="fixed_income:tesouro-selic", name="Tesouro Selic", asset_class="renda_fixa", confidence=0.75),), hours_ago=3),
        signal("InfoMoney", (AssetMention(key="ticker:PETR4", name="Petrobras", asset_class="acao", confidence=0.95, cnpj="33000167000101"),)),
    ]

    aggregates = aggregate_signals(
        signals,
        source_weights={"InfoMoney": 1.0, "Money Times": 1.0},
        now=NOW,
        lookback_days=14,
    )
    ranked = rank_candidates(
        aggregates,
        context,
        fundamentals={"33000167000101": {"roe": 0.2, "net_margin": 0.2, "year": 2024}},
        momentum={"ticker:PETR4": {"return": 0.05, "volatility": 0.2, "points": 60}},
        now=NOW,
    )

    assert ranked[0].asset_class == "renda_fixa"
    assert any("abaixo do alvo" in reason for reason in ranked[0].reasons)
    assert "fundamentos" in ranked[0].missing
    assert len(ranked[0].examples) == 2

    petro = next(item for item in ranked if item.key == "ticker:PETR4")
    assert petro.components["concentration"] == 0.0
    assert petro.components["allocation"] == 0.0
    assert petro.confidence > ranked[0].confidence


def test_sinal_antigo_perde_forca():
    context = PortfolioContext(
        total_brl=1000,
        allocation={"renda_fixa": 0.0},
        holdings={},
        targets={"renda_fixa": 0.60},
    )
    recent = signal("InfoMoney", (AssetMention(key="fixed_income:cdb", name="CDB", asset_class="renda_fixa", confidence=0.75),), hours_ago=1)
    old = signal("Exame", (AssetMention(key="fixed_income:lci", name="LCI", asset_class="renda_fixa", confidence=0.75),), hours_ago=24 * 30)

    aggregates = aggregate_signals(
        [recent, old],
        source_weights={"InfoMoney": 1.0, "Exame": 1.0},
        now=NOW,
        lookback_days=14,
    )

    assert [item.key for item in aggregates] == ["fixed_income:cdb"]
