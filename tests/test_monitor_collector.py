from datetime import datetime, timezone

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
