from datetime import date, datetime, timedelta, timezone

import pytest

from src.monitor.backtest import evaluate
from src.persistence.database import SQLiteDatabase
from src.persistence.monitor import CandidateSnapshot, SnapshotRepository

BASE = date(2026, 1, 1)


def snapshot(score: float, instrument: str) -> CandidateSnapshot:
    return CandidateSnapshot(
        snapshot_date=BASE,
        asset_key=f"ticker:{instrument}",
        name=instrument,
        asset_class="acao",
        score=score,
        confidence=0.8,
        components={},
        reasons=(),
        sources=("teste",),
        signal_count=1,
        reference_price=100.0,
        reference_price_date=BASE,
        price_provider="csv",
        price_instrument=instrument,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def prices_for(series: dict[str, float], days: int = 30) -> dict[tuple[str, str], list[tuple[date, float]]]:
    return {
        ("csv", instrument): [(BASE + timedelta(days=days), value)]
        for instrument, value in series.items()
    }


def test_backtest_calcula_faixas_correlacao_e_spread():
    snapshots = [snapshot(90, "A"), snapshot(50, "B"), snapshot(10, "C")]
    prices = prices_for({"A": 110.0, "B": 100.0, "C": 95.0})

    report = evaluate(snapshots, prices, horizon_days=30, min_samples=3)

    assert report.evaluated == 3
    assert report.available is True
    assert report.buckets[4].average_return == pytest.approx(0.10)
    assert report.buckets[2].average_return == pytest.approx(0.0)
    assert report.buckets[0].average_return == pytest.approx(-0.05)
    assert report.spread == pytest.approx(0.15)
    assert report.rank_correlation == pytest.approx(1.0)


def test_backtest_ignora_snapshot_nao_maduro():
    snapshots = [snapshot(90, "A")]
    prices = {("csv", "A"): [(BASE + timedelta(days=3), 110.0)]}

    report = evaluate(snapshots, prices, horizon_days=30, min_samples=1)

    assert report.evaluated == 0
    assert report.available is False
    assert "Amostra insuficiente" in (report.reason or "")


def test_backtest_sem_amostra_explica_motivo():
    report = evaluate([], {}, horizon_days=30, min_samples=5)

    assert report.available is False
    assert report.reason


def test_snapshot_upsert_preenche_preco_em_reexecucao(tmp_path):
    database = SQLiteDatabase(tmp_path / "monitor.db")
    database.initialize()
    repository = SnapshotRepository(database)
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    original = snapshot(90, "A")

    repository.record_many(
        [
            CandidateSnapshot(
                snapshot_date=original.snapshot_date,
                asset_key=original.asset_key,
                name=original.name,
                asset_class=original.asset_class,
                score=original.score,
                confidence=original.confidence,
                components={},
                reasons=(),
                sources=(),
                signal_count=1,
                created_at=now,
            )
        ],
        now=now,
    )
    repository.record_many([original], now=now)

    stored = repository.list()
    assert len(stored) == 1
    assert stored[0].reference_price == 100.0
    assert stored[0].price_instrument == "A"
