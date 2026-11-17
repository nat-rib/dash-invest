import { useEffect, useMemo, useState } from "react";

import { Button, Card, EmptyState, ErrorBox, Loading, SelectInput } from "../components/ui";
import type { Candidate } from "../services/monitor";
import { fetchCandidates } from "../services/monitor";

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

const SORT_OPTIONS = [
  { value: "score", label: "Score" },
  { value: "signal_count", label: "Nº de sinais" },
  { value: "confidence", label: "Confiança" },
  { value: "last_seen", label: "Mais recente" },
];

export default function RadarPage() {
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [query, setQuery] = useState("");
  const [assetClass, setAssetClass] = useState("");
  const [minScore, setMinScore] = useState("");
  const [sortBy, setSortBy] = useState("score");
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    setError(null);
    fetchCandidates({ limit: 200 })
      .then((data) => setCandidates(data.items))
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const items = useMemo(() => {
    const minimum = Number(minScore.replace(",", ".")) || 0;
    const term = query.trim().toLowerCase();
    const filtered = candidates.filter(
      (item) =>
        item.score >= minimum &&
        (!assetClass || item.asset_class === assetClass) &&
        (!term || item.name.toLowerCase().includes(term)),
    );
    return [...filtered].sort((left, right) => {
      if (sortBy === "signal_count") return right.signal_count - left.signal_count;
      if (sortBy === "confidence") return right.confidence - left.confidence;
      if (sortBy === "last_seen") {
        return (right.last_seen ?? "").localeCompare(left.last_seen ?? "");
      }
      return right.score - left.score;
    });
  }, [candidates, query, assetClass, minScore, sortBy]);

  const toggle = (key: string) => {
    setExpanded((current) => {
      const next = new Set(current);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  return (
    <div className="page">
      <header className="page-header">
        <h1>Radar de ativos</h1>
        <p className="muted">
          Ativos citados nas fontes monitoradas, ordenados pela aderência à sua carteira. Cada
          score é determinístico e mostra os componentes e o que falta para uma análise completa.
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
            <span className="field-label">Ordenar por</span>
            <SelectInput value={sortBy} onChange={setSortBy} options={SORT_OPTIONS} />
          </div>
          <div className="field">
            <span className="field-label">&nbsp;</span>
            <Button variant="primary" onClick={load}>
              Atualizar
            </Button>
          </div>
        </div>
        <p className="field-hint">
          {items.length} de {candidates.length} ativos exibidos.
        </p>
      </Card>

      {loading && <Loading />}
      {!loading && candidates.length === 0 && (
        <Card>
          <EmptyState
            title="Nenhum ativo no radar."
            hint="Rode a coleta de sinais e verifique se há ativos citados nas notícias."
          />
        </Card>
      )}
      {!loading && candidates.length > 0 && items.length === 0 && (
        <Card>
          <EmptyState title="Nenhum ativo atende aos filtros." hint="Afrouxe o score ou a busca." />
        </Card>
      )}

      {!loading && items.length > 0 && (
        <div className="radar-grid">
          {items.map((item, index) => {
            const isExpanded = expanded.has(item.key);
            return (
              <article className={`radar-card ${isExpanded ? "expanded" : ""}`.trim()} key={item.key}>
                <div className="radar-head">
                  <span className="monitor-rank">{index + 1}</span>
                  <div className="monitor-title">
                    <strong>{item.name}</strong>
                    <span className="muted"> · {CLASS_LABELS[item.asset_class] ?? item.asset_class}</span>
                  </div>
                  <span className="monitor-score">{item.score.toFixed(0)}</span>
                </div>
                <div className="bar-track">
                  <div className="bar-fill" style={{ width: `${Math.min(item.score, 100)}%` }} />
                </div>
                <p className="radar-reason">{item.reasons[0] ?? "Sem motivo registrado."}</p>
                <div className="radar-meta">
                  <span>{item.signal_count} sinal(is)</span>
                  <span>{item.sources.length} fonte(s)</span>
                  <span>confiança {(item.confidence * 100).toFixed(0)}%</span>
                  <span>{item.last_seen ? formatDate(item.last_seen) : "—"}</span>
                </div>
                <Button variant="ghost" onClick={() => toggle(item.key)}>
                  {isExpanded ? "Ocultar detalhes" : "Detalhes"}
                </Button>
                {isExpanded && (
                  <div className="radar-detail">
                    <div>
                      <strong>Motivos</strong>
                      <ul>
                        {item.reasons.map((reason) => (
                          <li key={reason}>{reason}</li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      <strong>Componentes</strong>
                      <ul>
                        {Object.entries(COMPONENT_LABELS).map(([key, label]) => {
                          const value = item.components[key];
                          return (
                            <li key={key}>
                              {label}: {value === null || value === undefined ? "—" : `${(value * 100).toFixed(0)}%`}
                            </li>
                          );
                        })}
                      </ul>
                    </div>
                    <div>
                      <strong>Fontes</strong>
                      <p>{item.sources.join(", ") || "—"}</p>
                    </div>
                    {item.missing.length > 0 && (
                      <p className="field-hint">Sem dados: {item.missing.join(", ")}.</p>
                    )}
                  </div>
                )}
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}

function formatDate(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}

function ErrorBoxRender({ error }: { error: string | null }) {
  if (!error) return null;
  return <ErrorBox message={error} />;
}
