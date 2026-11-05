import { useEffect, useState } from "react";
import { Card, ErrorBox, Loading } from "../components/ui";
import { getJson } from "../services/api";

interface Allocation {
  total_brl: string;
  known_positions: number;
  unknown_positions: number;
  by_institution: { name: string; value: string; share: string | null; positions: number }[];
}

interface LedgerState {
  instruments_count: number;
  transactions_count: number;
  snapshots_count: number;
  database_path: string;
}

export default function DashboardPage() {
  const [allocation, setAllocation] = useState<Allocation | null>(null);
  const [state, setState] = useState<LedgerState | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      getJson<Allocation>("/api/analysis/allocation").catch(() => null),
      getJson<LedgerState>("/api/ledger/state").catch(() => null),
    ])
      .then(([alloc, ledgerState]) => {
        if (alloc) setAllocation(alloc);
        if (ledgerState) setState(ledgerState);
        if (!alloc && !ledgerState) {
          setError("Nem o snapshot nem o ledger estão disponíveis neste ambiente.");
        }
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)));
  }, []);

  return (
    <div className="page">
      <header className="page-header">
        <h1>Visão geral</h1>
        <p className="muted">
          Patrimônio consolidado a partir do snapshot JSON (fonte: PORTFOLIO_PATH); o ledger SQLite
          é fonte separada e não é combinado automaticamente.
        </p>
      </header>
      {error && <ErrorBox message={error} />}
      {!allocation && !state && !error && <Card><Loading /></Card>}
      <div className="metric-grid">
        {allocation && (
          <Card title="Patrimônio consolidado BRL">
            {parseFloat(allocation.total_brl).toLocaleString("pt-BR", {
              style: "currency", currency: "BRL",
            })}
          </Card>
        )}
        {allocation && <Card title="Posições conhecidas">{allocation.known_positions}</Card>}
        {allocation && <Card title="Sem valor consolidado">{allocation.unknown_positions}</Card>}
        {state && <Card title="Transações no ledger">{state.transactions_count}</Card>}
      </div>
      {allocation && allocation.by_institution.length > 0 && (
        <Card title="Por instituição (valores conhecidos em BRL)">
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Instituição</th><th>Valor BRL</th><th>Participação</th><th>Posições</th>
                </tr>
              </thead>
              <tbody>
                {allocation.by_institution.map((slice) => (
                  <tr key={slice.name}>
                    <td>{slice.name}</td>
                    <td>{parseFloat(slice.value).toLocaleString("pt-BR", { minimumFractionDigits: 2 })}</td>
                    <td>
                      {slice.share === null ? "—" : `${(parseFloat(slice.share) * 100).toFixed(1)}%`}
                    </td>
                    <td>{slice.positions}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
      {state && (
        <Card>
          <p className="muted">
            Ledger: {state.instruments_count} instrumentos · {state.snapshots_count} snapshots
            persistidos · banco em {state.database_path}.
          </p>
        </Card>
      )}
    </div>
  );
}
