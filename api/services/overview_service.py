"""Visão geral: consolida o snapshot e o estado do ledger sem misturar fontes.

O serviço não recalcula patrimônio no frontend nem inventa rentabilidade ou
benchmark. Quando um dado não existe, o contrato devolve indisponibilidade com
motivo explícito.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Literal

from api.config import default_portfolio_id
from api.schemas.analysis import AllocationSlice
from api.schemas.overview import (
    OverviewAlertOut, OverviewBenchmarkOut, OverviewLedgerOut, OverviewOut,
    OverviewPerformanceOut, OverviewQualityOut, OverviewSnapshotOut,
    TopPositionOut,
)
from api.services import analysis_service, performance_service
from api.services.ledger_service import LedgerValidationError

# Indicador transparente de concentração por posição. Não é um score de risco
# universal: serve apenas para destacar fatias relevantes do patrimônio.
HIGH_CONCENTRATION = Decimal("0.20")
MEDIUM_CONCENTRATION = Decimal("0.10")
STALE_SNAPSHOT_DAYS = 30


def _format_date(value: date) -> str:
    return value.strftime("%d/%m/%Y")


def _percent(value: Decimal) -> str:
    return f"{(value * 100).quantize(Decimal('0.1'))}%"


def _concentration_level(share: Decimal) -> Literal["high", "medium", "low"]:
    if share >= HIGH_CONCENTRATION:
        return "high"
    if share >= MEDIUM_CONCENTRATION:
        return "medium"
    return "low"


def _performance(repositories: Any, portfolio_id: str) -> OverviewPerformanceOut:
    try:
        performance_service.require_portfolio(repositories.portfolios, portfolio_id)
    except LedgerValidationError as error:
        return OverviewPerformanceOut(available=False, reason=str(error))

    stored = performance_service.stored_periods(
        repositories.performance_periods, portfolio_id,
    )
    if stored:
        try:
            result = performance_service.calculate_twr(
                performance_service.domain_periods_from(stored),
            )
        except ValueError as error:
            return OverviewPerformanceOut(
                available=False, reason=f"TWR indisponível: {error}",
            )
        return OverviewPerformanceOut(
            available=True,
            metric="TWR",
            rate=str(result.rate),
            periods=result.periods,
            start_date=result.start_date.isoformat(),
            end_date=result.end_date.isoformat(),
        )

    try:
        flows, _, reason = performance_service.external_flows(
            repositories.portfolios,
            repositories.transactions,
            portfolio_id=portfolio_id,
        )
    except LedgerValidationError as error:
        return OverviewPerformanceOut(available=False, reason=str(error))
    if reason:
        return OverviewPerformanceOut(available=False, reason=reason)
    if not flows:
        return OverviewPerformanceOut(
            available=False,
            reason=(
                "Sem fluxos externos no ledger. Registre aportes e retiradas para "
                "habilitar TWR/XIRR; snapshots isolados não produzem rentabilidade."
            ),
        )
    return OverviewPerformanceOut(
        available=False,
        reason=(
            f"Há {len(flows)} fluxo(s) externo(s), mas faltam períodos de avaliação "
            "TWR para calcular a rentabilidade."
        ),
    )


def _quality(
    *, snapshot_available: bool, known: int, unknown: int, total: int,
) -> OverviewQualityOut:
    if not snapshot_available:
        return OverviewQualityOut(
            level="unknown", positions_count=0, known_positions=0,
            unknown_positions=0,
            message="Snapshot indisponível; não há como avaliar a cobertura dos dados.",
        )
    if known == 0:
        return OverviewQualityOut(
            level="unknown", positions_count=total, known_positions=0,
            unknown_positions=unknown,
            message=(
                "Nenhuma posição com valor consolidado em BRL; total e alocação "
                "permanecem indisponíveis."
            ),
        )
    if unknown == 0:
        return OverviewQualityOut(
            level="complete", positions_count=total, known_positions=known,
            unknown_positions=0,
            message=f"Todas as {total} posições têm valor consolidado em BRL.",
        )
    return OverviewQualityOut(
        level="partial", positions_count=total, known_positions=known,
        unknown_positions=unknown,
        message=(
            f"{known} de {total} posições têm valor consolidado em BRL; "
            f"{unknown} ficaram fora do total e da alocação."
        ),
    )


def _ledger(repositories: Any, portfolio_id: str) -> OverviewLedgerOut:
    transactions_count = repositories.transactions.search(portfolio_id, limit=1)[1]
    events = repositories.transactions.list_for_portfolio(portfolio_id)
    transfer_events = [
        event for event in events
        if event.transaction_type.value in {"TRANSFER_IN", "TRANSFER_OUT"}
    ]
    links = repositories.transfer_links.list_for_portfolio(portfolio_id)
    unlinked = max(len(transfer_events) - 2 * len(links), 0)
    return OverviewLedgerOut(
        instruments_count=len(repositories.instruments.list_all()),
        transactions_count=transactions_count,
        snapshots_count=len(repositories.positions.list_snapshots(portfolio_id)),
        unlinked_transfer_events=unlinked,
        database_path=str(repositories.database.path),
    )


def build_overview(
    repositories: Any, *, portfolio_id: str | None = None, today: date | None = None,
) -> OverviewOut:
    pid = portfolio_id or default_portfolio_id()
    today = today or date.today()
    ledger = _ledger(repositories, pid)
    performance = _performance(repositories, pid)
    alerts: list[OverviewAlertOut] = []

    try:
        snapshot = analysis_service.current_snapshot()
        allocation = analysis_service.allocation()
        concentration = analysis_service.concentration()
    except (FileNotFoundError, ValueError) as error:
        message = str(error)
        alerts.append(OverviewAlertOut(
            id="snapshot-unavailable",
            tone="warn",
            title="Snapshot indisponível",
            message=message,
        ))
        if ledger.transactions_count == 0:
            alerts.append(OverviewAlertOut(
                id="ledger-empty",
                tone="info",
                title="Ledger sem transações",
                message=(
                    "Importe o snapshot e registre operações para habilitar "
                    "conciliação, TWR e XIRR."
                ),
            ))
        return OverviewOut(
            portfolio_id=pid,
            snapshot=OverviewSnapshotOut(available=False, error=message),
            total_brl=None,
            known_positions=0,
            unknown_positions=0,
            positions_count=0,
            by_class=[],
            by_institution=[],
            top_positions=[],
            alerts=alerts,
            performance=performance,
            benchmark=OverviewBenchmarkOut(
                available=False,
                reason=(
                    "Benchmark ainda não é calculado: requer série de referência, "
                    "janela e metodologia explícitas."
                ),
            ),
            quality=_quality(
                snapshot_available=False, known=0, unknown=0, total=0,
            ),
            ledger=ledger,
        )

    total = Decimal(allocation["total_brl"])
    known = int(allocation["known_positions"])
    unknown = int(allocation["unknown_positions"])
    positions_count = len(snapshot.positions)
    quality = _quality(
        snapshot_available=True, known=known, unknown=unknown,
        total=positions_count,
    )

    top_positions: list[TopPositionOut] = []
    for item in concentration["top"][:5]:
        share = Decimal(item["share"])
        top_positions.append(TopPositionOut(
            index=int(item["index"]),
            name=item["name"],
            institution=item["institution"],
            asset_class=item["asset_class"],
            consolidated_brl=item["consolidated_brl"],
            share=str(share),
            concentration_level=_concentration_level(share),
            risk_category=snapshot.positions[int(item["index"])].risk_category,
        ))

    if unknown:
        alerts.append(OverviewAlertOut(
            id="unknown-positions",
            tone="warn",
            title="Cobertura parcial em BRL",
            message=(
                f"{unknown} de {positions_count} posições não têm valor consolidado "
                "em BRL e não entram no total nem na alocação."
            ),
        ))
    if known == 0:
        alerts.append(OverviewAlertOut(
            id="no-known-value",
            tone="warn",
            title="Sem patrimônio consolidado",
            message=(
                "Nenhuma posição pôde ser consolidada em BRL. Verifique cotações e "
                "conversões cambiais explícitas."
            ),
        ))

    for position in top_positions:
        if position.concentration_level != "high":
            continue
        alerts.append(OverviewAlertOut(
            id=f"concentration-{position.index}",
            tone="warn",
            title="Concentração elevada",
            message=(
                f"{position.name} ({position.institution}) representa "
                f"{_percent(Decimal(position.share))} do patrimônio consolidado."
            ),
        ))

    age_days = (today - snapshot.snapshot_date).days
    if age_days > STALE_SNAPSHOT_DAYS:
        alerts.append(OverviewAlertOut(
            id="stale-snapshot",
            tone="warn",
            title="Snapshot desatualizado",
            message=(
                f"Data-base {_format_date(snapshot.snapshot_date)} "
                f"({age_days} dias). Atualize as cotações antes de decidir."
            ),
        ))

    if known and len(allocation["by_class"]) == 1:
        only_class = allocation["by_class"][0]["name"]
        alerts.append(OverviewAlertOut(
            id="single-class",
            tone="info",
            title="Carteira em uma única classe",
            message=f"Todo o patrimônio conhecido está em {only_class}.",
        ))

    if ledger.unlinked_transfer_events:
        alerts.append(OverviewAlertOut(
            id="unlinked-transfers",
            tone="warn",
            title="Transferências pendentes",
            message=(
                f"{ledger.unlinked_transfer_events} evento(s) de transferência sem "
                "par confirmado. Revise a conciliação no Ledger."
            ),
        ))

    if ledger.transactions_count == 0:
        alerts.append(OverviewAlertOut(
            id="ledger-empty",
            tone="info",
            title="Ledger sem transações",
            message=(
                "A rentabilidade histórica depende de aportes, retiradas e "
                "avaliações; o snapshot atual não os substitui."
            ),
        ))

    return OverviewOut(
        portfolio_id=pid,
        snapshot=OverviewSnapshotOut(
            available=True,
            snapshot_date=snapshot.snapshot_date.isoformat(),
            currency=snapshot.currency,
        ),
        total_brl=str(total) if known > 0 else None,
        known_positions=known,
        unknown_positions=unknown,
        positions_count=positions_count,
        by_class=[AllocationSlice(**item) for item in allocation["by_class"]],
        by_institution=[
            AllocationSlice(**item) for item in allocation["by_institution"]
        ],
        top_positions=top_positions,
        alerts=alerts,
        performance=performance,
        benchmark=OverviewBenchmarkOut(
            available=False,
            reason=(
                "Benchmark ainda não é calculado: requer série de referência, "
                "janela e metodologia explícitas."
            ),
        ),
        quality=quality,
        ledger=ledger,
    )
