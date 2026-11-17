import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

import api.dependencies as dependencies
from api.main import create_app
from src.domain.observations import Observation, QualityStatus
from src.domain.signals import AssetMention, Signal
from src.persistence.monitor import AlertRecord, CandidateSnapshot, SnapshotRepository
from src.persistence.observations import ObservationRepository
from src.persistence.signals import SignalRepository

SNAPSHOT = {
    "schema_version": 1,
    "snapshot_date": "2026-03-31",
    "currency": "BRL",
    "positions": [
        {"institution": "XP", "asset_class": "acao", "ticker": "PETR4", "name": "Petrobras", "quantity": "10", "current_price": "30.00", "currency": "BRL"},
        {"institution": "BTG", "asset_class": "renda_fixa", "name": "CDB", "current_value": "100.00", "currency": "BRL"},
        {"institution": "XP", "asset_class": "fii", "ticker": "HGLG11", "name": "CSHG Log", "quantity": "2", "current_price": "100.00", "currency": "BRL"},
        {"institution": "XP", "asset_class": "etf", "ticker": "BOVA11", "name": "BOVA", "quantity": "1", "current_price": "100.00", "currency": "BRL"},
        {"institution": "XP", "asset_class": "cripto", "ticker": "BTC", "name": "Bitcoin", "quantity": "0.001", "current_price": "100000", "currency": "BRL"},
        {"institution": "Avenue", "asset_class": "exterior", "ticker": "AAPL", "name": "Apple", "quantity": "1", "current_price": "200.00", "currency": "BRL"},
    ],
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DASH_INVEST_DB_PATH", str(tmp_path / "api.db"))
    monkeypatch.setenv("PORTFOLIO_PATH", str(tmp_path / "portfolio.json"))
    (tmp_path / "portfolio.json").write_text(json.dumps(SNAPSHOT), encoding="utf-8")
    dependencies.get_database.cache_clear()
    dependencies.get_repositories.cache_clear()
    with TestClient(create_app()) as test_client:
        yield test_client


def seed_signals() -> None:
    repository = SignalRepository(dependencies.get_database())
    now = datetime.now(timezone.utc)
    repository.record_many(
        [
            Signal(
                source="InfoMoney",
                title="Tesouro Selic atrai investidores",
                url="https://example/tesouro",
                summary="Renda fixa",
                published_at=now,
                collected_at=now,
                assets=(
                    AssetMention(
                        key="fixed_income:tesouro-selic",
                        name="Tesouro Selic",
                        asset_class="renda_fixa",
                        confidence=0.75,
                    ),
                ),
            ),
            Signal(
                source="Exame",
                title="Petrobras anuncia dividendos",
                url="https://example/petrobras",
                summary="PETR4",
                published_at=now,
                collected_at=now,
                assets=(
                    AssetMention(
                        key="ticker:PETR4",
                        name="Petrobras",
                        asset_class="acao",
                        confidence=0.95,
                        cnpj="33000167000101",
                    ),
                ),
            ),
        ]
    )


def test_ranking_prioriza_renda_fixa_abaixo_do_alvo(client):
    seed_signals()

    body = client.get("/api/monitor/candidates").json()

    assert body["total"] >= 2
    first = body["items"][0]
    assert first["key"] == "fixed_income:tesouro-selic"
    assert first["asset_class"] == "renda_fixa"
    assert any("abaixo do alvo" in reason for reason in first["reasons"])
    assert "fundamentos" in first["missing"]

    petro = next(item for item in body["items"] if item["key"] == "ticker:PETR4")
    assert petro["components"]["concentration"] == 0.0
    assert petro["cnpj"] == "33000167000101"


def test_lista_sinais_e_fontes(client):
    seed_signals()
    repository = SignalRepository(dependencies.get_database())
    now = datetime.now(timezone.utc)
    repository.record(
        Signal(
            source="InfoMoney",
            title="Resultado da loteria",
            url="https://example/loteria",
            published_at=now,
            collected_at=now,
        )
    )

    signals = client.get("/api/monitor/signals").json()
    all_signals = client.get("/api/monitor/signals?with_assets=false").json()
    sources = client.get("/api/monitor/sources").json()

    assert signals["total"] == 2
    assert all_signals["total"] == 3
    assert signals["items"][0]["assets"]
    assert sources["items"]


def test_sem_carteira_retorna_400(client, monkeypatch, tmp_path):
    monkeypatch.setattr(
        "api.services.monitor_service.portfolio_path", lambda: tmp_path / "nao.json"
    )

    response = client.get("/api/monitor/candidates")

    assert response.status_code == 400
    assert "Importe uma carteira" in response.json()["detail"]


def seed_backtest() -> tuple[date, date]:
    database = dependencies.get_database()
    now = datetime.now(timezone.utc)
    snapshot_date = date.today() - timedelta(days=60)
    future = snapshot_date + timedelta(days=30)
    SnapshotRepository(database).record_many(
        [
            CandidateSnapshot(
                snapshot_date=snapshot_date,
                asset_key="ticker:PETR4",
                name="Petrobras",
                asset_class="acao",
                score=90,
                confidence=0.8,
                components={},
                reasons=(),
                sources=(),
                signal_count=1,
                reference_price=100.0,
                reference_price_date=snapshot_date,
                price_provider="csv",
                price_instrument="PETR4.SAO",
                created_at=now,
            ),
            CandidateSnapshot(
                snapshot_date=snapshot_date,
                asset_key="ticker:VALE3",
                name="Vale",
                asset_class="acao",
                score=10,
                confidence=0.8,
                components={},
                reasons=(),
                sources=(),
                signal_count=1,
                reference_price=100.0,
                reference_price_date=snapshot_date,
                price_provider="csv",
                price_instrument="VALE3.SAO",
                created_at=now,
            ),
            CandidateSnapshot(
                snapshot_date=snapshot_date,
                asset_key="ticker:ITUB4",
                name="Itaú",
                asset_class="acao",
                score=50,
                confidence=0.8,
                components={},
                reasons=(),
                sources=(),
                signal_count=1,
                reference_price=100.0,
                reference_price_date=snapshot_date,
                price_provider="csv",
                price_instrument="ITUB4.SAO",
                created_at=now,
            ),
        ],
        now=now,
    )
    ObservationRepository(database).record_many(
        [
            Observation(
                provider="csv",
                metric="close",
                instrument_id="PETR4.SAO",
                value=Decimal("110"),
                currency="BRL",
                reference_date=future,
                period_end=future,
                parser_version="test",
                quality_status=QualityStatus.VERIFIED,
            ),
            Observation(
                provider="csv",
                metric="close",
                instrument_id="VALE3.SAO",
                value=Decimal("95"),
                currency="BRL",
                reference_date=future,
                period_end=future,
                parser_version="test",
                quality_status=QualityStatus.VERIFIED,
            ),
            Observation(
                provider="csv",
                metric="close",
                instrument_id="ITUB4.SAO",
                value=Decimal("100"),
                currency="BRL",
                reference_date=future,
                period_end=future,
                parser_version="test",
                quality_status=QualityStatus.VERIFIED,
            ),
        ]
    )
    return snapshot_date, future


def test_backtest_do_ranking(client):
    seed_backtest()

    body = client.get(
        "/api/monitor/backtest", params={"horizon_days": 30, "min_samples": 2}
    ).json()

    assert body["evaluated"] == 3
    assert body["available"] is True
    assert body["spread"] == pytest.approx(0.15)
    assert body["rank_correlation"] == pytest.approx(1.0)


def test_alertas_e_configuracao(client, monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    monkeypatch.delenv("ALERT_CHANNELS", raising=False)
    monkeypatch.delenv("ALERT_MIN_SCORE", raising=False)

    database = dependencies.get_database()
    dependencies.get_repositories().alerts.record(
        AlertRecord(
            asset_key="ticker:PETR4",
            name="Petrobras",
            score=90,
            channel="console",
            message="alert",
            sent_at=datetime.now(timezone.utc),
        )
    )

    alerts = client.get("/api/monitor/alerts").json()
    config = client.get("/api/monitor/alert-config").json()

    assert alerts["total"] == 1
    assert alerts["items"][0]["channel"] == "console"
    assert config["channels"] == ["console"]
    assert config["min_score"] == 80.0
    assert config["telegram_configured"] is False
