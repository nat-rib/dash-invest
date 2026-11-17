from datetime import datetime, timedelta, timezone

import pytest

from src.monitor.alerts import send_alerts
from src.monitor.scoring import Candidate
from src.persistence.database import SQLiteDatabase
from src.persistence.monitor import AlertRepository

NOW = datetime(2026, 11, 16, 12, tzinfo=timezone.utc)


class FakeNotifier:
    def __init__(self, name: str = "telegram", fail: bool = False):
        self.name = name
        self.fail = fail
        self.messages: list[str] = []

    def send(self, message: str) -> None:
        if self.fail:
            raise RuntimeError("canal fora do ar")
        self.messages.append(message)


def candidate(score: float, key: str = "ticker:PETR4") -> Candidate:
    return Candidate(
        key=key,
        name="Petrobras",
        asset_class="acao",
        score=score,
        confidence=0.8,
        components={},
        reasons=("Ações abaixo do alvo",),
        missing=(),
        sources=("InfoMoney",),
        signal_count=2,
        last_seen=NOW,
    )


@pytest.fixture
def repository(tmp_path):
    database = SQLiteDatabase(tmp_path / "alerts.db")
    database.initialize()
    return AlertRepository(database)


def test_envia_apenas_acima_do_score_e_respeita_cooldown(repository):
    notifier = FakeNotifier()

    first = send_alerts(
        [candidate(85), candidate(70, key="ticker:VALE3")],
        repository,
        (notifier,),
        min_score=80,
        cooldown_days=3,
        now=NOW,
    )

    assert len(first.sent) == 1
    assert first.skipped_below_score == 1
    assert len(notifier.messages) == 1
    assert repository.last_sent("ticker:PETR4") == NOW

    second = send_alerts(
        [candidate(85)],
        repository,
        (notifier,),
        min_score=80,
        cooldown_days=3,
        now=NOW + timedelta(days=1),
    )
    assert second.skipped_cooldown == 1
    assert len(second.sent) == 0

    third = send_alerts(
        [candidate(85)],
        repository,
        (notifier,),
        min_score=80,
        cooldown_days=3,
        now=NOW + timedelta(days=4),
    )
    assert len(third.sent) == 1
    assert len(notifier.messages) == 2


def test_falha_de_canal_nao_grava_alerta(repository):
    notifier = FakeNotifier(fail=True)

    result = send_alerts(
        [candidate(90)],
        repository,
        (notifier,),
        min_score=80,
        cooldown_days=3,
        now=NOW,
    )

    assert result.sent == ()
    assert result.errors
    assert repository.last_sent("ticker:PETR4") is None


def test_console_nao_bloqueia_proximo_envio_quando_ha_canal_externo(repository):
    console = FakeNotifier(name="console")
    telegram = FakeNotifier(name="telegram")

    result = send_alerts(
        [candidate(90)],
        repository,
        (console, telegram),
        min_score=80,
        cooldown_days=3,
        now=NOW,
    )

    assert result.sent[0][2] == ("console", "telegram")
    assert len(console.messages) == 1
    assert len(telegram.messages) == 1
