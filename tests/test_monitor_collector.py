from datetime import datetime, timezone

from src.domain.signals import AssetMention, Signal
from src.monitor.collector import collect
from src.monitor.config import MonitorConfig, Source
from src.persistence.database import SQLiteDatabase
from src.persistence.signals import SignalRepository

NOW = datetime(2026, 11, 16, 12, tzinfo=timezone.utc)

RSS_A = b"""<?xml version="1.0"?><rss version="2.0"><channel>
<item><title>PETR4 sobe</title><link>https://a/1</link><description>Petrobras</description></item>
</channel></rss>"""

RSS_B = b"""<?xml version="1.0"?><rss version="2.0"><channel>
<item><title>Tesouro Selic atrai</title><link>https://b/1</link><description>Renda fixa</description></item>
</channel></rss>"""

RSS_HINT = b"""<?xml version="1.0"?><rss version="2.0"><channel>
<item><title>Nubank e Inter lideram na renda fixa</title><link>https://hint/1</link><description>Bancos digitais</description></item>
</channel></rss>"""


def fetcher(url: str) -> bytes:
    if "fail" in url:
        raise RuntimeError("fonte fora do ar")
    if "a.example" in url:
        return RSS_A
    return RSS_B


def config(*urls: str) -> MonitorConfig:
    return MonitorConfig(
        sources=tuple(Source(name=url, url=url, weight=1.0) for url in urls)
    )


def test_coleta_e_idempotencia(tmp_path):
    database = SQLiteDatabase(tmp_path / "signals.db")
    database.initialize()
    repository = SignalRepository(database)

    first = collect(config("https://a.example", "https://b.example"), repository, fetcher=fetcher, now=NOW, sleep=0)
    second = collect(config("https://a.example", "https://b.example"), repository, fetcher=fetcher, now=NOW, sleep=0)

    assert first.sources_ok == 2
    assert first.inserted == 2
    assert second.inserted == 0
    stored = repository.list()
    assert len(stored) == 2
    assets = {asset.key for item in stored for asset in item.assets}
    assert "ticker:PETR4" in assets
    assert "fixed_income:tesouro-selic" in assets


def test_fonte_com_erro_nao_derruba_lote(tmp_path):
    database = SQLiteDatabase(tmp_path / "signals.db")
    database.initialize()
    repository = SignalRepository(database)

    summary = collect(
        config("https://a.example", "https://fail.example"),
        repository,
        fetcher=fetcher,
        now=NOW,
        sleep=0,
    )

    assert summary.sources_ok == 1
    assert summary.sources_failed == 1
    assert summary.inserted == 1
    assert summary.errors


def test_hint_de_cdb_na_fonte_extrai_banco(tmp_path):
    database = SQLiteDatabase(tmp_path / "signals.db")
    database.initialize()
    repository = SignalRepository(database)

    source = Source(name="CDB", url="https://hint.example", weight=1.0, hint="cdb")
    collect(
        MonitorConfig(sources=(source,)),
        repository,
        fetcher=lambda url: RSS_HINT,
        now=NOW,
        sleep=0,
    )

    assets = {asset.key for item in repository.list() for asset in item.assets}
    assert "fixed_income:cdb:nubank" in assets
    assert "fixed_income:cdb:inter" in assets


def test_refresh_atualiza_assets_de_sinal_existente(tmp_path):
    database = SQLiteDatabase(tmp_path / "signals.db")
    database.initialize()
    repository = SignalRepository(database)
    original = Signal(
        source="Fonte",
        title="Notícia",
        url="https://example/1",
        collected_at=NOW,
        assets=(AssetMention(key="old", name="Old", asset_class="outros", confidence=0.5),),
    )
    repository.record_many([original])

    updated = original.model_copy(
        update={
            "assets": (
                AssetMention(
                    key="fixed_income:cdb:nubank",
                    name="CDB Nubank",
                    asset_class="renda_fixa",
                    confidence=0.8,
                ),
            )
        }
    )
    assert repository.record_many([updated], refresh=True) == 1

    stored = repository.list()[0]
    assert stored.assets[0].key == "fixed_income:cdb:nubank"
