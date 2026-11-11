import { useEffect, useMemo, useState } from "react";

import { MetricCard } from "../components/insights";
import { Button, Card, EmptyState, ErrorBox, Loading, SelectInput, Table } from "../components/ui";
import type { RiskReport, SeriesKey } from "../services/risk";
import { fetchInstrumentRisk, fetchPortfolioRisk, fetchSeriesKeys } from "../services/risk";

export default function RiskPage() {
  const [keys, setKeys] = useState<SeriesKey[]>([]);
  const [selected, setSelected] = useState("");
  const [rate, setRate] = useState("10");
  const [appliedRate, setAppliedRate] = useState(0.1);
  const [instrument, setInstrument] = useState<RiskReport | null>(null);
  const [portfolio, setPortfolio] = useState<RiskReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSeriesKeys()
      .then((data) => {
        setKeys(data.items);
        setSelected((current) => current || seriesValue(data.items[0]));
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)));
  }, []);

  const selectedKey = useMemo(
    () => keys.find((key) => seriesValue(key) === selected) ?? null,
    [keys, selected],
  );

  useEffect(() => {
    if (!selectedKey?.instrument_id) {
      setInstrument(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchInstrumentRisk(selectedKey.provider, selectedKey.instrument_id, appliedRate)
      .then((data) => {
        if (!cancelled) setInstrument(data);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedKey, appliedRate]);

  useEffect(() => {
    let cancelled = false;
    fetchPortfolioRisk(appliedRate)
      .then((data) => {
        if (!cancelled) setPortfolio(data);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      });
    return () => {
      cancelled = true;
    };
  }, [appliedRate]);

  const applyRate = () => {
    const parsed = Number(rate.replace(",", "."));
    setAppliedRate(Number.isFinite(parsed) ? parsed / 100 : 0);
  };

  return (
    <div className="page">
      <header className="page-header">
        <h1>Risco</h1>
        <p className="muted">
          Métricas calculadas sobre séries de preço armazenadas e sobre o histórico de snapshots da
          carteira. Amostra insuficiente fica explicitamente indisponível.
        </p>
      </header>
      <ErrorBoxRender error={error} />

      <Card title="Parâmetros">
        <div className="field-row">
          <div className="field">
            <span className="field-label">Série de preços</span>
            {keys.length === 0 ? (
              <span className="field-hint">Nenhuma série importada.</span>
            ) : (
              <SelectInput
                value={selected}
                onChange={setSelected}
                options={keys.map((key) => ({
                  value: seriesValue(key),
                  label: `${key.instrument_id ?? "—"} · ${key.provider} (${key.observations})`,
                }))}
              />
            )}
          </div>
          <div className="field">
            <span className="field-label">Taxa livre de risco (% a.a.)</span>
            <input
              type="text"
              value={rate}
              onChange={(event) => setRate(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") applyRate();
              }}
            />
          </div>
          <div className="field">
            <span className="field-label">&nbsp;</span>
            <Button variant="primary" onClick={applyRate}>
              Calcular
            </Button>
          </div>
        </div>
        <p className="field-hint">
          Importe preços com <code>python -m jobs.ingest_prices --symbol PETR4.SAO --csv precos.csv</code>.
        </p>
      </Card>

      <Card
        title="Risco do ativo"
        subtitle={selectedKey?.instrument_id ? `${selectedKey.instrument_id} · ${selectedKey.provider}` : undefined}
      >
        {loading && <Loading />}
        {!loading && !instrument && <EmptyState title="Selecione uma série de preços." />}
        {!loading && instrument && <RiskMetrics report={instrument} />}
      </Card>

      <Card title="Risco da carteira" subtitle="Baseado no histórico de snapshots (HISTORY_DB_PATH).">
        {!portfolio && <Loading />}
        {portfolio && <RiskMetrics report={portfolio} />}
      </Card>
    </div>
  );
}

function RiskMetrics({ report }: { report: RiskReport }) {
  if (report.reason) {
    return <div className="warning-box">{report.reason}</div>;
  }
  return (
    <>
      <div className="metric-grid">
        <MetricCard
          label="Retorno total"
          value={formatPercent(report.total_return)}
          hint={dateRange(report)}
        />
        <MetricCard
          label="Volatilidade anualizada"
          value={formatPercent(report.annualized_volatility)}
          hint={`${report.returns} retornos`}
        />
        <MetricCard
          label="Drawdown máximo"
          value={formatPercent(report.max_drawdown)}
          tone="warn"
        />
        <MetricCard label="Sharpe" value={formatNumber(report.sharpe)} />
        <MetricCard label="Sortino" value={formatNumber(report.sortino)} />
        <MetricCard label="VaR 95% (histórico)" value={formatPercent(report.var_95)} tone="warn" />
        <MetricCard label="CVaR 95% (histórico)" value={formatPercent(report.cvar_95)} tone="warn" />
        <MetricCard
          label="VaR 95% paramétrico"
          value={formatPercent(report.var_95_parametric)}
          tone="warn"
        />
        <MetricCard
          label="CVaR 95% paramétrico"
          value={formatPercent(report.cvar_95_parametric)}
          tone="warn"
        />
      </div>
      {report.monthly_returns.length > 0 && (
        <Table head={["Mês", "Retorno"]}>
          {report.monthly_returns
            .slice()
            .reverse()
            .map((item) => (
              <tr key={item.month}>
                <td>{item.month}</td>
                <td>{formatPercent(item.return_value)}</td>
              </tr>
            ))}
        </Table>
      )}
      {report.unavailable.length > 0 && (
        <p className="field-hint">
          Indisponível por amostra insuficiente: {report.unavailable.join(", ")}.
        </p>
      )}
    </>
  );
}

function seriesValue(key: SeriesKey | undefined): string {
  if (!key) return "";
  return `${key.provider}|${key.instrument_id ?? ""}`;
}

function dateRange(report: RiskReport): string {
  if (!report.start_date || !report.end_date) return "";
  return `${report.start_date} → ${report.end_date}`;
}

function formatPercent(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "—";
  return `${(value * 100).toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`;
}

function formatNumber(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "—";
  return value.toLocaleString("pt-BR", { maximumFractionDigits: 2 });
}

function ErrorBoxRender({ error }: { error: string | null }) {
  if (!error) return null;
  return <ErrorBox message={error} />;
}
