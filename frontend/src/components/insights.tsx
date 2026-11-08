import { useId, useMemo, useState } from "react";
import type { PointerEvent as ReactPointerEvent, ReactNode } from "react";
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

const CHART_WIDTH = 720;
const CHART_HEIGHT = 260;
const CHART_PADDING = { top: 18, right: 18, bottom: 40, left: 78 };

function parseLabelDate(label: string): Date | null {
  if (!/^\d{4}-\d{2}-\d{2}/.test(label)) return null;
  const parsed = new Date(label);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function shortDate(label: string, withYear: boolean): string {
  const parsed = parseLabelDate(label);
  if (!parsed) return label;
  return parsed.toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    ...(withYear ? { year: "2-digit" as const } : {}),
  });
}

function fullDate(label: string): string {
  const parsed = parseLabelDate(label);
  if (!parsed) return label;
  return parsed.toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}

function compactNumber(value: number): string {
  const abs = Math.abs(value);
  if (abs >= 1_000_000) {
    return `${(value / 1_000_000).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} mi`;
  }
  if (abs >= 1_000) {
    return `${(value / 1_000).toLocaleString("pt-BR", { maximumFractionDigits: 0 })} mil`;
  }
  return value.toLocaleString("pt-BR", { maximumFractionDigits: 0 });
}

function niceTicks(min: number, max: number, count: number): number[] {
  if (!Number.isFinite(min) || !Number.isFinite(max)) return [];
  let low = min;
  let high = max;
  if (low === high) {
    const pad = Math.abs(low) * 0.1 || 1;
    low -= pad;
    high += pad;
  }
  const rough = (high - low) / count;
  const magnitude = 10 ** Math.floor(Math.log10(rough));
  const normalized = rough / magnitude;
  const step = (normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 5 ? 5 : 10) * magnitude;
  const start = Math.floor(low / step) * step;
  const end = Math.ceil(high / step) * step;
  const ticks: number[] = [];
  for (let tick = start; tick <= end + step / 2; tick += step) ticks.push(tick);
  return ticks;
}

export function ResponsiveChart({
  points,
  ariaLabel,
  formatValue,
  formatTick,
}: {
  points: { label: string; value: number }[];
  ariaLabel: string;
  formatValue?: (value: number) => string;
  formatTick?: (value: number) => string;
}) {
  const [active, setActive] = useState<number | null>(null);
  const gradientId = useId().replace(/:/g, "");
  const tickLabel = formatTick ?? compactNumber;
  const valueLabel = (value: number) =>
    formatValue ? formatValue(value) : value.toLocaleString("pt-BR", { maximumFractionDigits: 2 });

  const geometry = useMemo(() => {
    if (points.length === 0) return null;
    const values = points.map((point) => point.value).filter((value) => Number.isFinite(value));
    if (values.length === 0) return null;

    const { top, right, bottom, left } = CHART_PADDING;
    const plotWidth = CHART_WIDTH - left - right;
    const plotHeight = CHART_HEIGHT - top - bottom;

    const min = Math.min(...values);
    const max = Math.max(...values);
    const edge = (max - min || Math.abs(max) || 1) * 0.08;
    const ticks = niceTicks(min - edge, max + edge, 4);
    if (ticks.length < 2) return null;

    const domainMin = ticks[0];
    const domainMax = ticks[ticks.length - 1];
    const span = domainMax - domainMin || 1;

    const times = points.map((point) => parseLabelDate(point.label)?.getTime() ?? null);
    const firstTime = times[0] ?? 0;
    const lastTime = times[times.length - 1] ?? 0;
    const useTime =
      lastTime > firstTime && times.every((time): time is number => time !== null);

    const xAt = (index: number) => {
      if (useTime) {
        return left + (((times[index] as number) - firstTime) / (lastTime - firstTime)) * plotWidth;
      }
      return points.length === 1
        ? left + plotWidth / 2
        : left + (index / (points.length - 1)) * plotWidth;
    };
    const yAt = (value: number) => top + plotHeight - ((value - domainMin) / span) * plotHeight;

    const coords = points.map((point, index) => ({ x: xAt(index), y: yAt(point.value) }));
    const line = coords
      .map((coord, index) => `${index === 0 ? "M" : "L"}${coord.x.toFixed(2)},${coord.y.toFixed(2)}`)
      .join(" ");
    const baseline = top + plotHeight;
    const area =
      coords.length > 0
        ? `${line} L${coords[coords.length - 1].x.toFixed(2)},${baseline.toFixed(2)} L${coords[0].x.toFixed(2)},${baseline.toFixed(2)} Z`
        : "";

    const years = new Set(
      points
        .map((point) => parseLabelDate(point.label)?.getFullYear())
        .filter((year): year is number => typeof year === "number"),
    );
    const withYear = years.size > 1;

    const labelCount = Math.min(4, points.length);
    const xTicks = Array.from({ length: labelCount }, (_, slot) => {
      const index = labelCount === 1 ? 0 : Math.round((slot / (labelCount - 1)) * (points.length - 1));
      return { index, x: xAt(index), label: shortDate(points[index].label, withYear) };
    });

    return { plotWidth, plotHeight, coords, line, area, ticks, yAt, xTicks, withYear };
  }, [points]);

  if (!geometry) {
    return <EmptyState title="Sem dados para o gráfico." />;
  }

  const { plotWidth, plotHeight, coords, line, area, ticks, yAt, xTicks, withYear } = geometry;
  const { top, right, left } = CHART_PADDING;
  const baseline = top + plotHeight;

  const selectAt = (event: ReactPointerEvent<SVGRectElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const ratio = rect.width > 0 ? (event.clientX - rect.left) / rect.width : 0;
    const target = left + Math.min(Math.max(ratio, 0), 1) * plotWidth;
    let nearest = 0;
    let best = Number.POSITIVE_INFINITY;
    coords.forEach((coord, index) => {
      const distance = Math.abs(coord.x - target);
      if (distance < best) {
        best = distance;
        nearest = index;
      }
    });
    setActive(nearest);
  };

  const activePoint = active !== null ? coords[active] : null;
  const lastPoint = coords[coords.length - 1];
  const firstDate = shortDate(points[0].label, withYear);
  const lastDate = shortDate(points[points.length - 1].label, withYear);

  return (
    <div className="responsive-chart">
      <div className="chart-wrap">
        <svg
          viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
          className="line-chart"
          role="img"
          aria-label={ariaLabel}
        >
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--chart-1)" stopOpacity="0.32" />
              <stop offset="100%" stopColor="var(--chart-1)" stopOpacity="0.02" />
            </linearGradient>
          </defs>

          {ticks.map((tick) => {
            const y = yAt(tick);
            return (
              <g key={tick}>
                <line className="chart-grid-line" x1={left} y1={y} x2={CHART_WIDTH - right} y2={y} />
                <text
                  className="chart-axis-label"
                  x={left - 10}
                  y={y}
                  textAnchor="end"
                  dominantBaseline="middle"
                >
                  {tickLabel(tick)}
                </text>
              </g>
            );
          })}

          <path className="chart-area" d={area} fill={`url(#${gradientId})`} />
          <line className="chart-baseline" x1={left} y1={baseline} x2={CHART_WIDTH - right} y2={baseline} />
          <path className="chart-line" d={line} />

          {points.length <= 24 &&
            coords.map((coord, index) => (
              <circle key={index} className="chart-dot" cx={coord.x} cy={coord.y} r={3.4} />
            ))}
          {points.length > 24 && (
            <circle className="chart-dot" cx={lastPoint.x} cy={lastPoint.y} r={4} />
          )}

          {activePoint && (
            <>
              <line
                className="chart-hover-line"
                x1={activePoint.x}
                y1={top}
                x2={activePoint.x}
                y2={baseline}
              />
              <circle
                className="chart-dot chart-dot-active"
                cx={activePoint.x}
                cy={activePoint.y}
                r={5.5}
              />
            </>
          )}

          {xTicks.map((tick) => (
            <text
              key={tick.index}
              className="chart-axis-label chart-axis-x"
              x={tick.x}
              y={CHART_HEIGHT - 12}
              textAnchor="middle"
            >
              {tick.label}
            </text>
          ))}

          <rect
            x={left}
            y={top}
            width={plotWidth}
            height={plotHeight}
            fill="transparent"
            pointerEvents="all"
            onPointerMove={selectAt}
            onPointerLeave={() => setActive(null)}
          />
        </svg>

        {active !== null && activePoint && (
          <div
            className="chart-tooltip"
            style={{ left: `${Math.min(Math.max((activePoint.x / CHART_WIDTH) * 100, 12), 88)}%` }}
          >
            <span>{fullDate(points[active].label)}</span>
            <strong>{valueLabel(points[active].value)}</strong>
          </div>
        )}
      </div>
      <div className="chart-caption">
        <span>
          {points.length} snapshot{points.length === 1 ? "" : "s"}
        </span>
        <span>{points.length > 1 ? `${firstDate} – ${lastDate}` : firstDate}</span>
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
