import { useEffect, useMemo, useState } from "react";

import { MetricCard } from "../components/insights";
import { Button, Card, EmptyState, ErrorBox, Loading, SelectInput, Table } from "../components/ui";
import type { AlertConfig, AlertRecord, BacktestReport, Candidate, MonitorSignal } from "../services/monitor";
import {
  fetchAlertConfig,
  fetchBacktest,
  fetchCandidates,
  fetchMonitorAlerts,
  fetchMonitorSignals,
} from "../services/monitor";

const CLASS_LABELS: Record<string, string> = {
  renda_fixa: "Renda fixa",
  acao: "Ações",
  fii: "FIIs",
  etf: "ETFs",
  cripto: "Cripto",
  exterior: "Exterior",
  fundo: "Fundos",
  outros: "Outros",
};

const COMPONENT_LABELS: Record<string, string> = {
  allocation: "Lacuna de alocação",
  concentration: "Concentração",
  fundamentals: "Fundamentos",
  valuation: "Valuation",
  momentum: "Momento",
  signal: "Sinal",
};

const CLASS_OPTIONS = [
  { value: "", label: "Todas as classes" },
  ...Object.entries(CLASS_LABELS).map(([value, label]) => ({ value, label })),
];

export default function MonitorPage() {
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [signals, setSignals] = useState<MonitorSignal[]>([]);
  const [backtest, setBacktest] = useState<BacktestReport | null>(null);
  const [alerts, setAlerts] = useState<AlertRecord[]>([]);
  const [alertConfig, setAlertConfig] = useState<AlertConfig | null>(null);
  const [horizon, setHorizon] = useState("30");
  const [minScore, setMinScore] = useState("");
  const [assetClass, setAssetClass] = useState("");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    setError(null);
    Promise.all([
      fetchCandidates({ limit: 100 }),
      fetchMonitorSignals(30),
      fetchBacktest(Number(horizon)),
      fetchMonitorAlerts(20),
      fetchAlertConfig(),
    ])
      .then(([ranking, feed, evaluation, alertList, config]) => {
        setCandidates(ranking.items);
        setSignals(feed.items);
        setBacktest(evaluation);
        setAlerts(alertList.items);
        setAlertConfig(config);
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  useEffect(() => {
    fetchBacktest(Number(horizon))
      .then(setBacktest)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)));
  }, [horizon]);

  const filtered = useMemo(() => {
    const minimum = Number(minScore.replace(",", ".")) || 0;
    const term = query.trim().toLowerCase();
    return candidates.filter(
      (item) =>
        item.score >= minimum &&
        (!assetClass || item.asset_class === assetClass) &&
        (!term || item.name.toLowerCase().includes(term)),
    );
  }, [candidates, minScore, assetClass, query]);

  const topScore = candidates.length > 0 ? candidates[0].score : null;
  const classes = new Set(candidates.map((item) => item.asset_class)).size;

  return (
    <div className="page">
      <header className="page-header">
        <h1>Monitor de ativos</h1>
        <p className="muted">
          Notícias e sinais abertos cruzados com sua carteira. O ranking é determinístico e
          explicável; dado ausente reduz a confiança e não vira zero. Isto é triagem, não
          recomendação.
        </p>
      </header>
      <ErrorBoxRender error={error} />

      <Card title="Filtros">
        <div className="field-row">
          <div className="field">
            <span className="field-label">Buscar ativo</span>
            <input type="text" value={query} onChange={(event) => setQuery(event.target.value)} />
          </div>
          <div className="field">
            <span className="field-label">Classe</span>
            <SelectInput value={assetClass} onChange={setAssetClass} options={CLASS_OPTIONS} />
          </div>
          <div className="field">
            <span className="field-label">Score mínimo</span>
            <input
              type="text"
              value={minScore}
              placeholder="0"
              onChange={(event) => setMinScore(event.target.value)}
            />
          </div>
          <div className="field">
            <span className="field-label">&nbsp;</span>
            <Button variant="primary" onClick={load}>
              Atualizar
            </Button>
          </div>
        </div>
      </Card>

      <div className="metric-grid">
        <MetricCard label="Candidatos" value={String(candidates.length)} hint={`${classes} classes`} />
        <MetricCard
          label="Maior score"
          value={topScore === null ? "—" : topScore.toFixed(0)}
          hint="0 a 100"
        />
        <MetricCard label="Sinais recentes" value={String(signals.length)} hint="últimos 30 dias" />
      </div>

      <Card title="Ranking de aderência">
        {loading && <Loading />}
        {!loading && filtered.length === 0 && (
          <EmptyState
            title="Nenhum candidato no período."
            hint="Rode a coleta de sinais e ajuste os filtros."
          />
        )}
        {!loading && filtered.length > 0 && (
          <div className="monitor-list">
            {filtered.map((item, index) => (
              <CandidateCard key={item.key} item={item} rank={index + 1} />
            ))}
          </div>
        )}
      </Card>

      <Card title="Avaliação do ranking" subtitle="Retorno futuro dos snapshots diários por faixa de score.">
        <div className="field-row">
          <div className="field">
            <span className="field-label">Horizonte</span>
            <SelectInput
              value={horizon}
              onChange={setHorizon}
              options={[
                { value: "30", label: "30 dias" },
                { value: "90", label: "90 dias" },
              ]}
            />
          </div>
        </div>
        {backtest && !backtest.available && (
          <div className="warning-box">{backtest.reason ?? "Sem dados suficientes."}</div>
        )}
        {backtest && backtest.available && (
          <>
            <div className="metric-grid">
              <MetricCard
                label="Avaliados"
                value={String(backtest.evaluated)}
                hint={`${backtest.snapshots} snapshots`}
              />
              <MetricCard label="Spread topo-base" value={percent(backtest.spread)} />
              <MetricCard
                label="Correlação de postos"
                value={backtest.rank_correlation === null ? "—" : backtest.rank_correlation.toFixed(2)}
              />
              <MetricCard
                label="Acerto do topo"
                value={percent(backtest.buckets[4]?.hit_rate ?? null)}
              />
            </div>
            <Table head={["Faixa de score", "Amostras", "Retorno médio", "Acerto"]}>
              {backtest.buckets.map((bucket) => (
                <tr key={bucket.label}>
                  <td>{bucket.label}</td>
                  <td>{bucket.count}</td>
                  <td>{percent(bucket.average_return)}</td>
                  <td>{percent(bucket.hit_rate)}</td>
                </tr>
              ))}
            </Table>
          </>
        )}
      </Card>

      <Card
        title="Alertas"
        subtitle={
          alertConfig
            ? `Canais: ${alertConfig.channels.join(", ")} · score mínimo ${alertConfig.min_score} · cooldown ${alertConfig.cooldown_days} dias`
            : undefined
        }
      >
        {alerts.length === 0 ? (
          <p className="muted">Nenhum alerta enviado ainda.</p>
        ) : (
          <Table head={["Data", "Ativo", "Score", "Canal"]}>
            {alerts.map((alert, index) => (
              <tr key={`${alert.asset_key}-${index}`}>
                <td>{formatDate(alert.sent_at)}</td>
                <td>{alert.name}</td>
                <td>{alert.score.toFixed(0)}</td>
                <td>{alert.channel}</td>
              </tr>
            ))}
          </Table>
        )}
        {alertConfig && (
          <p className="field-hint">
            {alertConfig.telegram_configured ? "Telegram configurado." : "Telegram não configurado."}{" "}
            {alertConfig.email_configured ? "E-mail configurado." : "E-mail não configurado."}
          </p>
        )}
      </Card>

      <Card title="Últimos sinais" subtitle="Fontes abertas monitoradas; clique para abrir a matéria.">
        {signals.length === 0 ? (
          <p className="muted">
            Nenhum sinal coletado. Execute <code>python -m jobs.collect_signals</code>.
          </p>
        ) : (
          <Table head={["Data", "Fonte", "Título", "Ativos"]}>
            {signals.map((item) => (
              <tr key={item.url}>
                <td>{formatDate(item.published_at ?? item.collected_at)}</td>
                <td>{item.source}</td>
                <td>
                  <a href={item.url} target="_blank" rel="noreferrer">
                    {item.title}
                  </a>
                </td>
                <td>{item.assets.map((asset) => asset.name).join(", ") || "—"}</td>
              </tr>
            ))}
          </Table>
        )}
      </Card>
    </div>
  );
}

function CandidateCard({ item, rank }: { item: Candidate; rank: number }) {
  return (
    <article className="monitor-candidate">
      <div className="monitor-head">
        <span className="monitor-rank">{rank}</span>
        <div className="monitor-title">
          <strong>{item.name}</strong>
          <span className="muted">
            {" "}
            · {CLASS_LABELS[item.asset_class] ?? item.asset_class} · {item.signal_count} sinal(is) ·{" "}
            {item.sources.length} fonte(s)
          </span>
        </div>
        <span className="monitor-score">{item.score.toFixed(0)}</span>
      </div>
      <div className="bar-track">
        <div className="bar-fill" style={{ width: `${Math.min(item.score, 100)}%` }} />
      </div>
      <ul className="monitor-reasons">
        {item.reasons.map((reason) => (
          <li key={reason}>{reason}</li>
        ))}
      </ul>
      <div className="monitor-components">
        {Object.entries(COMPONENT_LABELS).map(([key, label]) => {
          const value = item.components[key];
          return (
            <span key={key} className="monitor-component">
              {label}: <strong>{value === null || value === undefined ? "—" : `${(value * 100).toFixed(0)}%`}</strong>
            </span>
          );
        })}
        <span className="monitor-component">
          Confiança: <strong>{(item.confidence * 100).toFixed(0)}%</strong>
        </span>
      </div>
      {item.missing.length > 0 && (
        <p className="field-hint">Sem dados: {item.missing.join(", ")}.</p>
      )}
    </article>
  );
}

function formatDate(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}

function percent(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "—";
  return `${(value * 100).toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`;
}

function ErrorBoxRender({ error }: { error: string | null }) {
  if (!error) return null;
  return <ErrorBox message={error} />;
}
