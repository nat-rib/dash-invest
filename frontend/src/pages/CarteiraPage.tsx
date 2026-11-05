import { useEffect, useState } from "react";
import { Card, EmptyState, ErrorBox, Loading, Table } from "../components/ui";
import { getJson } from "../services/api";

interface PositionSummary {
  index: number;
  name: string;
  institution: string;
  asset_class: string;
  currency: string;
  consolidated_brl: string | null;
}

interface PositionDetail {
  index: number;
  name: string;
  institution: string;
  currency: string;
  quantity: string | null;
  average_cost: string | null;
  current_value: string | null;
  gain_loss: string | null;
  unrealized_return: string | null;
  consolidated_brl: string | null;
  current_price: string | null;
}

export default function CarteiraPage() {
  const [positions, setPositions] = useState<PositionSummary[] | null>(null);
  const [snapshotDate, setSnapshotDate] = useState<string>("");
  const [selected, setSelected] = useState<number | null>(null);
  const [detail, setDetail] = useState<PositionDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getJson<{ snapshot_date: string; positions: PositionSummary[] }>("/api/portfolio/positions")
      .then((data) => {
        setPositions(data.positions);
        setSnapshotDate(data.snapshot_date);
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)));
  }, []);

  useEffect(() => {
    if (selected === null) {
      setDetail(null);
      return;
    }
    setDetail(null);
    getJson<PositionDetail>(`/api/portfolio/positions/${selected}`)
      .then(setDetail)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)));
  }, [selected]);

  return (
    <div className="page">
      <header className="page-header">
        <h1>Posições</h1>
        <p className="muted">Snapshot de data-base {snapshotDate || "—"}. Clique em uma posição para ver o resumo.</p>
      </header>
      {error && <ErrorBox message={error} />}
      {!positions && !error && <Card><Loading /></Card>}
      {positions && positions.length === 0 && (
        <Card><EmptyState title="Nenhuma posição." hint="Importe uma carteira primeiro." /></Card>
      )}
      {positions && positions.length > 0 && (
        <Card>
          <Table head={["Ativo", "Instituição", "Classe", "Moeda", "Valor consolidado BRL"]} empty={false}>
            {positions.map((position) => (
              <tr
                key={position.index}
                className={selected === position.index ? "selected-row" : ""}
                onClick={() => setSelected(position.index === selected ? null : position.index)}
              >
                <td>{position.name}</td>
                <td>{position.institution}</td>
                <td>{position.asset_class}</td>
                <td>{position.currency}</td>
                <td>{position.consolidated_brl ? brl(position.consolidated_brl) : "—"}</td>
              </tr>
            ))}
          </Table>
          {detail && (
            <div className="detail-metrics">
              <MetricBox label="Quantidade" value={detail.quantity ?? "—"} />
              <MetricBox label="Preço médio" value={detail.average_cost ? brl(detail.average_cost) : "—"} />
              <MetricBox label="Preço atual" value={detail.current_price ? brl(detail.current_price) : "—"} />
              <MetricBox label="Valor atual" value={detail.current_value ? brl(detail.current_value) : "—"} />
              <MetricBox label="Ganho/perda" value={detail.gain_loss ? brl(detail.gain_loss) : "—"} />
              <MetricBox
                label="Rentabilidade"
                value={detail.unrealized_return ? `${(parseFloat(detail.unrealized_return) * 100).toFixed(2)}%` : "—"}
              />
            </div>
          )}
        </Card>
      )}
    </div>
  );
}

function MetricBox({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric-box">
      <span className="metric-label">{label}</span>
      <span className="metric-value">{value}</span>
    </div>
  );
}

function brl(value: string): string {
  const parsed = parseFloat(value);
  if (!Number.isFinite(parsed)) return value;
  return parsed.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}
