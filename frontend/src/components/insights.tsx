import type { ReactNode } from "react";
import { EmptyState } from "./ui";

export type Tone = "good" | "info" | "warn";
export type ConcentrationLevel = "high" | "medium" | "low" | "unknown";
export type QualityLevel = "complete" | "partial" | "unknown";

export function MetricCard({
  label,
  value,
  hint,
  tone,
  unavailable = false,
}: {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  tone?: Tone;
  unavailable?: boolean;
}) {
  return (
    <article className={`metric-card ${tone ? `tone-${tone}` : ""} ${unavailable ? "unavailable" : ""}`.trim()}>
      <span className="metric-card-label">{label}</span>
      <strong className="metric-card-value">{value}</strong>
      {hint && <span className="metric-card-hint">{hint}</span>}
    </article>
  );
}

export function RiskBadge({
  level,
  label,
}: {
  level: ConcentrationLevel;
  label?: string;
}) {
  const labels: Record<ConcentrationLevel, string> = {
    high: "Concentração alta",
    medium: "Concentração média",
    low: "Concentração baixa",
    unknown: "Concentração não informada",
  };
  return <span className={`badge risk-badge risk-${level}`}>{label ?? labels[level]}</span>;
}

export function QualityBadge({
  level,
  message,
}: {
  level: QualityLevel;
  message?: string;
}) {
  const labels: Record<QualityLevel, string> = {
    complete: "Cobertura completa",
    partial: "Cobertura parcial",
    unknown: "Cobertura insuficiente",
  };
  const title = message ?? labels[level];
  return (
    <span className={`quality-badge quality-${level}`} title={title}>
      <span className="quality-dot" aria-hidden="true" />
      {labels[level]}
    </span>
  );
}

export function OpportunityCard({
  tone = "info",
  label,
  title,
  children,
}: {
  tone?: Tone;
  label?: string;
  title: string;
  children: ReactNode;
}) {
  const labels: Record<Tone, string> = {
    good: "Ponto positivo",
    info: "Informação",
    warn: "Ponto de atenção",
  };
  return (
    <article className={`opportunity-card opportunity-${tone}`}>
      <span className="opportunity-label">{label ?? labels[tone]}</span>
      <strong>{title}</strong>
      <p>{children}</p>
    </article>
  );
}

export function PositionCard({
  name,
  institution,
  assetClass,
  value,
  share,
  riskCategory,
  concentrationLevel,
}: {
  name: string;
  institution: string;
  assetClass: string;
  value: string;
  share: string | null;
  riskCategory?: string | null;
  concentrationLevel?: ConcentrationLevel;
}) {
  return (
    <article className="position-card">
      <div className="position-card-main">
        <strong>{name}</strong>
        <span className="muted">
          {institution} · {assetClass}
          {riskCategory ? ` · Risco informado: ${riskCategory}` : ""}
        </span>
      </div>
      <div className="position-card-side">
        <strong>{value}</strong>
        {share !== null && (
          <span className="muted">
            {(parseFloat(share) * 100).toFixed(1)}% da carteira
          </span>
        )}
      </div>
      {concentrationLevel && (
        <div className="position-card-footer">
          <RiskBadge level={concentrationLevel} />
        </div>
      )}
    </article>
  );
}

export function AllocationBars({
  slices,
  emptyTitle = "Sem posições com valor conhecido em BRL.",
}: {
  slices: { name: string; value: string; share: string | null }[];
  emptyTitle?: string;
}) {
  if (slices.length === 0) return <EmptyState title={emptyTitle} />;
  return (
    <div className="bar-list">
      {slices.map((slice) => {
        const share = slice.share === null ? 0 : Math.max(parseFloat(slice.share), 0.01);
        return (
          <div className="bar-row" key={slice.name}>
            <span className="bar-name">
              {slice.name} · {money(slice.value)} ({percent(slice.share)})
            </span>
            <div className="bar-track">
              <div
                className="bar-fill"
                style={{ width: `${Math.min(share * 100, 100)}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function ResponsiveChart({
  points,
  ariaLabel,
  formatValue,
}: {
  points: { label: string; value: number }[];
  ariaLabel: string;
  formatValue?: (value: number) => string;
}) {
  if (points.length === 0) {
    return <EmptyState title="Sem dados para o gráfico." />;
  }
  const values = points.map((point) => point.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const width = 100;
  const height = 40;
  const coordinates = points.map((point, index) => {
    const x = points.length === 1 ? width / 2 : (index / (points.length - 1)) * width;
    const y = points.length === 1 ? height / 2 : height - ((point.value - min) / span) * height;
    return `${x.toFixed(2)},${y.toFixed(2)}`;
  });
  const valueLabel = (value: number) => (
    formatValue ? formatValue(value) : value.toLocaleString("pt-BR", { maximumFractionDigits: 2 })
  );

  return (
    <div className="responsive-chart">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="line-chart"
        role="img"
        aria-label={ariaLabel}
      >
        <polyline
          points={coordinates.join(" ")}
          fill="none"
          stroke="var(--chart-1)"
          strokeWidth="1.2"
          strokeLinejoin="round"
          strokeLinecap="round"
        />
        {coordinates.map((coordinate, index) => {
          const [x, y] = coordinate.split(",").map(parseFloat);
          return (
            <circle key={index} cx={x} cy={y} r={points.length === 1 ? 1.6 : 0.8} fill="var(--chart-1)">
              <title>{`${points[index].label}: ${valueLabel(points[index].value)}`}</title>
            </circle>
          );
        })}
      </svg>
      <div className="chart-caption">
        <span>{points[0].label}</span>
        {points.length > 1 && <span>{points[points.length - 1].label}</span>}
      </div>
    </div>
  );
}

function money(value: string): string {
  const parsed = parseFloat(value);
  if (!Number.isFinite(parsed)) return value;
  return parsed.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function percent(value: string | null): string {
  if (value === null) return "—";
  const parsed = parseFloat(value);
  if (!Number.isFinite(parsed)) return value;
  return `${(parsed * 100).toFixed(1)}%`;
}
