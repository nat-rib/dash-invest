"""Alertas de candidatos: Telegram bot, e-mail e console, com cooldown."""
from __future__ import annotations

import os
import smtplib
from dataclasses import dataclass
from datetime import datetime, timedelta
from email.message import EmailMessage
from typing import Protocol

import httpx

from src.monitor.scoring import CLASS_LABELS, Candidate
from src.persistence.monitor import AlertRecord, AlertRepository


@dataclass(frozen=True)
class AlertSettings:
    min_score: float = 80.0
    cooldown_days: int = 3
    max_alerts: int = 5
    channels: tuple[str, ...] = ("console",)
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    email_from: str | None = None
    email_to: str | None = None


class Notifier(Protocol):
    name: str

    def send(self, message: str) -> None: ...


@dataclass
class ConsoleNotifier:
    name: str = "console"

    def send(self, message: str) -> None:
        print(message)


@dataclass
class TelegramBotNotifier:
    token: str
    chat_id: str
    timeout: float = 10.0
    name: str = "telegram"

    def send(self, message: str) -> None:
        response = httpx.post(
            f"https://api.telegram.org/bot{self.token}/sendMessage",
            json={
                "chat_id": self.chat_id,
                "text": message,
                "disable_web_page_preview": True,
            },
            timeout=self.timeout,
        )
        if response.status_code >= 400:
            raise RuntimeError(f"Telegram respondeu HTTP {response.status_code}")


@dataclass
class EmailNotifier:
    host: str
    port: int
    user: str | None
    password: str | None
    sender: str
    recipient: str
    name: str = "email"

    def send(self, message: str) -> None:
        email = EmailMessage()
        email["Subject"] = "Dash-Invest — alerta de ativo"
        email["From"] = self.sender
        email["To"] = self.recipient
        email.set_content(message)

        if self.port == 465:
            with smtplib.SMTP_SSL(self.host, self.port, timeout=15) as client:
                if self.user:
                    client.login(self.user, self.password or "")
                client.send_message(email)
            return

        with smtplib.SMTP(self.host, self.port, timeout=15) as client:
            client.starttls()
            if self.user:
                client.login(self.user, self.password or "")
            client.send_message(email)


def settings_from_env() -> AlertSettings:
    channels = [
        item.strip().lower()
        for item in os.environ.get("ALERT_CHANNELS", "console").split(",")
        if item.strip()
    ]
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip() or None
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip() or None
    if token and chat_id and "telegram" not in channels:
        channels.append("telegram")

    return AlertSettings(
        min_score=float(os.environ.get("ALERT_MIN_SCORE", "80")),
        cooldown_days=int(os.environ.get("ALERT_COOLDOWN_DAYS", "3")),
        max_alerts=int(os.environ.get("ALERT_MAX_PER_RUN", "5")),
        channels=tuple(channels) or ("console",),
        telegram_bot_token=token,
        telegram_chat_id=chat_id,
        smtp_host=os.environ.get("SMTP_HOST", "").strip() or None,
        smtp_port=int(os.environ.get("SMTP_PORT", "587")),
        smtp_user=os.environ.get("SMTP_USER", "").strip() or None,
        smtp_password=os.environ.get("SMTP_PASSWORD", "").strip() or None,
        email_from=os.environ.get("ALERT_EMAIL_FROM", "").strip() or None,
        email_to=os.environ.get("ALERT_EMAIL_TO", "").strip() or None,
    )


def build_notifiers(settings: AlertSettings) -> tuple[Notifier, ...]:
    notifiers: list[Notifier] = [ConsoleNotifier()]
    if (
        "telegram" in settings.channels
        and settings.telegram_bot_token
        and settings.telegram_chat_id
    ):
        notifiers.append(
            TelegramBotNotifier(
                token=settings.telegram_bot_token,
                chat_id=settings.telegram_chat_id,
            )
        )
    if (
        "email" in settings.channels
        and settings.smtp_host
        and settings.email_from
        and settings.email_to
    ):
        notifiers.append(
            EmailNotifier(
                host=settings.smtp_host,
                port=settings.smtp_port,
                user=settings.smtp_user,
                password=settings.smtp_password,
                sender=settings.email_from,
                recipient=settings.email_to,
            )
        )
    return tuple(notifiers)


def format_alert(candidate: Candidate) -> str:
    label = CLASS_LABELS.get(candidate.asset_class, candidate.asset_class)
    lines = [
        f"🔔 {candidate.name} ({label}) — score {candidate.score:.0f}/100",
        "",
    ]
    lines.extend(f"• {reason}" for reason in candidate.reasons[:4])
    if candidate.sources:
        lines.append(f"Fontes: {', '.join(candidate.sources)}")
    lines.append("")
    lines.append("Triagem determinística do Dash-Invest; não é recomendação.")
    return "\n".join(lines)


@dataclass(frozen=True)
class AlertResult:
    sent: tuple[tuple[str, float, tuple[str, ...]], ...]
    skipped_cooldown: int
    skipped_below_score: int
    errors: tuple[str, ...]


def send_alerts(
    candidates: list[Candidate],
    repository: AlertRepository,
    notifiers: tuple[Notifier, ...],
    *,
    min_score: float,
    cooldown_days: int,
    now: datetime,
    max_alerts: int = 5,
) -> AlertResult:
    external = [notifier for notifier in notifiers if notifier.name != "console"]
    sent: list[tuple[str, float, tuple[str, ...]]] = []
    errors: list[str] = []
    skipped_cooldown = 0
    skipped_below_score = 0

    for candidate in candidates:
        if candidate.score < min_score:
            skipped_below_score += 1
            continue
        last = repository.last_sent(candidate.key)
        if last is not None and (now - last) < timedelta(days=cooldown_days):
            skipped_cooldown += 1
            continue
        if len(sent) >= max_alerts:
            break

        message = format_alert(candidate)
        channels: list[str] = []
        for notifier in notifiers:
            try:
                notifier.send(message)
                if notifier.name != "console" or not external:
                    repository.record(
                        AlertRecord(
                            asset_key=candidate.key,
                            name=candidate.name,
                            score=candidate.score,
                            channel=notifier.name,
                            message=message,
                            sent_at=now,
                        )
                    )
                channels.append(notifier.name)
            except Exception as error:  # noqa: BLE001 - canal com falha não impede os outros
                errors.append(f"{candidate.key}/{notifier.name}: {error}")
        if channels:
            sent.append((candidate.key, candidate.score, tuple(channels)))

    return AlertResult(
        sent=tuple(sent),
        skipped_cooldown=skipped_cooldown,
        skipped_below_score=skipped_below_score,
        errors=tuple(errors),
    )
