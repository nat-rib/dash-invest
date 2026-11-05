import { useEffect, useState } from "react";
import {
  AllocationBars, MetricCard, OpportunityCard, PositionCard, QualityBadge,
} from "../components/insights";
import { Card, EmptyState, ErrorBox, Loading } from "../components/ui";
import { fetchOverview } from "../services/overview";
import type { Overview } from "../services/overview";

export default function DashboardPage() {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    fetchOverview()
      .then((data) => {
        if (active) setOverview(data);
      })
      .catch((err: unknown) => {
        if (active) setError(err instanceof Error ? err.message : String(err));
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="page">
      <header className="page-header">
        <div className="page-header-title">
          <h1>Visão geral</h1>
          {overview && (
            <QualityBadge
              level={overview.quality.level}
              message={overview.quality.message}
            />
          )}
        </div>
        <p className="muted">
          Patrimônio conhecido do snapshot JSON (PORTFOLIO_PATH). O ledger SQLite
          é uma fonte separada e não é combinado automaticamente.
        </p>
      </header>

      {error && <ErrorBox message={error} />}
      {!overview && !error && <Card><Loading /></Card>}
      {overview && !overview.snapshot.available && overview.snapshot.error && (
        <ErrorBox message={overview.snapshot.error} />
      )}

      {overview && (
        <>
          <div className="metric-grid">
            <MetricCard
              label="Patrimônio consolidado BRL"
              value={overview.total_brl === null ? "Não disponível" : brl(overview.total_brl)}
              hint={
                overview.snapshot.snapshot_date
                  ? `Snapshot de ${formatDate(overview.snapshot.snapshot_date)}`
                  : "Snapshot indisponível"
              }
              unavailable={overview.total_brl === null}
            />
            <MetricCard
              label="Rentabilidade disponível"
              value={
                overview.performance.available && overview.performance.rate !== null
                  ? `${(parseFloat(overview.performance.rate) * 100).toFixed(2)}%`
                  : "Não disponível"
              }
              hint={
                overview.performance.available
                  ? `${overview.performance.metric} · ${formatDate(overview.performance.start_date)} a ${formatDate(overview.performance.end_date)} · ${overview.performance.periods ?? 0} período(s)`
                  : overview.performance.reason ?? "Cadastre fluxos e avaliações."
              }
              unavailable={!overview.performance.available}
            />
            <MetricCard
              label="Benchmark"
              value={overview.benchmark.available ? overview.benchmark.name ?? "Disponível" : "Indisponível"}
              hint={overview.benchmark.reason ?? "Sem série comparável."}
              unavailable={!overview.benchmark.available}
            />
            <MetricCard
              label="Cobertura do snapshot"
              value={`${overview.known_positions}/${overview.positions_count}`}
              hint={`${overview.unknown_positions} sem valor consolidado em BRL`}
              tone={overview.quality.level === "partial" ? "warn" : undefined}
            />
          </div>

          {overview.alerts.length > 0 && (
            <section className="insight-grid" aria-label="Alertas da carteira">
              {overview.alerts.map((alert) => (
                <OpportunityCard
                  key={alert.id}
                  tone={alert.tone}
                  title={alert.title}
                >
                  {alert.message}
                </OpportunityCard>
              ))}
            </section>
          )}

          <div className="split-two">
            <Card title="Distribuição por classe">
              <AllocationBars slices={overview.by_class} />
            </Card>
            <Card title="Distribuição por instituição">
              <AllocationBars slices={overview.by_institution} />
            </Card>
          </div>

          <Card title="Maiores posições">
            {overview.top_positions.length === 0 ? (
              <EmptyState title="Nenhuma posição com valor consolidado em BRL." />
            ) : (
              <div className="position-list">
                {overview.top_positions.map((position) => (
                  <PositionCard
                    key={position.index}
                    name={position.name}
                    institution={position.institution}
                    assetClass={position.asset_class}
                    value={brl(position.consolidated_brl)}
                    share={position.share}
                    riskCategory={position.risk_category}
                    concentrationLevel={position.concentration_level}
                  />
                ))}
              </div>
            )}
          </Card>

          <Card title="Qualidade e ledger">
            <div className="detail-metrics">
              <div className="metric-box">
                <span className="metric-label">Cobertura</span>
                <span className="metric-value">
                  {overview.known_positions}/{overview.positions_count}
                </span>
              </div>
              <div className="metric-box">
                <span className="metric-label">Sem valor BRL</span>
                <span className="metric-value">{overview.unknown_positions}</span>
              </div>
              <div className="metric-box">
                <span className="metric-label">Transações no ledger</span>
                <span className="metric-value">{overview.ledger.transactions_count}</span>
              </div>
              <div className="metric-box">
                <span className="metric-label">Transferências pendentes</span>
                <span className="metric-value">{overview.ledger.unlinked_transfer_events}</span>
              </div>
            </div>
            <p className="muted">{overview.quality.message}</p>
            <p className="muted">
              Ledger: {overview.ledger.instruments_count} instrumentos ·{" "}
              {overview.ledger.snapshots_count} snapshots persistidos · banco em{" "}
              {overview.ledger.database_path}.
            </p>
          </Card>
        </>
      )}
    </div>
  );
}

function brl(value: string): string {
  const parsed = parseFloat(value);
  if (!Number.isFinite(parsed)) return value;
  return parsed.toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
  });
}

function formatDate(value: string | null): string {
  if (!value) return "—";
  const [year, month, day] = value.slice(0, 10).split("-");
  return `${day}/${month}/${year}`;
}
