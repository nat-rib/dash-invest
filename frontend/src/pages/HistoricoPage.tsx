import { useCallback, useEffect, useMemo, useState } from "react";
import { ResponsiveChart } from "../components/insights";
import { Card, EmptyState, ErrorBox, Loading, SelectInput, Table } from "../components/ui";
import { getJson } from "../services/api";

interface HistoryPoint {
  captured_at: string;
  total_brl: number;
  source: string;
}

interface PortfolioHistory {
  points: HistoryPoint[];
  notice: string;
}

interface PositionPoint {
  captured_at: string;
  position_key: string;
  name: string;
  institution: string;
  currency: string;
  current_price: number | null;
  current_value: number | null;
  value_brl: number | null;
}

export default function HistoricoPage() {
  const [history, setHistory] = useState<PortfolioHistory | null>(null);
  const [keys, setKeys] = useState<string[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [series, setSeries] = useState<PositionPoint[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getJson<PortfolioHistory>("/api/history/portfolio")
      .then(setHistory)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)));
    getJson<{ keys: string[] }>("/api/history/positions")
      .then((data) => setKeys(data.keys))
      .catch(() => undefined);
  }, []);

  const loadSeries = useCallback(() => {
    if (!selected) {
      setSeries(null);
      return;
    }
    setSeries(null);
    getJson<{ points: PositionPoint[] }>(`/api/history/positions/${encodeURIComponent(selected)}`)
      .then((data) => setSeries(data.points))
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)));
  }, [selected]);
  useEffect(loadSeries, [loadSeries]);

  const change = useMemo(() => {
    if (!history || history.points.length < 2) return null;
    const first = history.points[0].total_brl;
    const last = history.points[history.points.length - 1].total_brl;
    if (first <= 0) return null;
    return last / first - 1;
  }, [history]);

  return (
    <div className="page">
      <header className="page-header">
        <h1>Histórico patrimonial</h1>
        <p className="muted">
          Snapshots armazenados no banco de histórico persistente do servidor (HISTORY_DB_PATH).
        </p>
      </header>
      <ErrorBoxRender error={error} />
      {!history && !error && <Card><Loading /></Card>}
      {history && history.points.length === 0 && (
        <Card>
          <EmptyState
            title="Ainda não há snapshots."
            hint="Consulte preços em Mercado ou registre o snapshot atual para iniciar o histórico."
          />
        </Card>
      )}
      {history && history.points.length > 0 && (
        <>
          <Card title="Patrimônio consolidado em BRL">
            <ResponsiveChart
              ariaLabel="Patrimônio consolidado em BRL ao longo do histórico"
              points={history.points.map((point) => ({
                label: point.captured_at,
                value: point.total_brl,
              }))}
              formatValue={(value) => value.toLocaleString("pt-BR", {
                style: "currency", currency: "BRL",
              })}
            />
            {change !== null && (
              <p>
                Variação entre primeiro e último snapshot: <strong>{(change * 100).toFixed(2)}%</strong>
              </p>
            )}
            <div className="warning-box">
              Isto é variação de valor, não rentabilidade da carteira: aportes, retiradas, impostos e
              proventos alteram o patrimônio. Para TWR ou XIRR, registre os fluxos de caixa.
            </div>
            <Table head={["Data", "Patrimônio BRL", "Origem"]} empty={false}>
              {history.points.map((point) => (
                <tr key={point.captured_at}>
                  <td>{point.captured_at.slice(0, 16).replace("T", " ")}</td>
                  <td>{point.total_brl.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}</td>
                  <td>{point.source}</td>
                </tr>
              ))}
            </Table>
          </Card>
          {keys.length > 0 && (
            <Card title="Evolução individual de posições">
              <div className="field-row">
                <div className="field">
                  <span className="field-label">Posição</span>
                  <SelectInput
                    value={selected}
                    onChange={setSelected}
                    options={[{ value: "", label: "Selecione…" }, ...keys.map((key) => ({ value: key, label: key.replace(/\|/g, " · ") }))]}
                  />
                </div>
              </div>
              {series && series.length > 0 && (
                <ResponsiveChart
                  ariaLabel={`Evolução do valor em BRL da posição ${selected}`}
                  points={series.map((point) => ({
                    label: point.captured_at,
                    value: point.value_brl ?? point.current_value ?? 0,
                  }))}
                  formatValue={(value) => value.toLocaleString("pt-BR", {
                    style: "currency", currency: "BRL",
                  })}
                />
              )}
              {series !== null && series.length === 0 && (
                <p className="muted">Sem pontos para esta posição.</p>
              )}
            </Card>
          )}
        </>
      )}
    </div>
  );
}

function ErrorBoxRender({ error }: { error: string | null }) {
  if (!error) return null;
  return <ErrorBox message={error} />;
}
