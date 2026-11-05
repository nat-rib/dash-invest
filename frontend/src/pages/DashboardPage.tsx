import { useEffect, useState } from "react";
import { Card, ErrorBox, Loading } from "../components/ui";
import { fetchLedgerState } from "../services/ledger";
import type { LedgerState } from "../types";

export default function DashboardPage() {
  const [state, setState] = useState<LedgerState | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchLedgerState().then(setState).catch((err: unknown) => {
      setError(err instanceof Error ? err.message : String(err));
    });
  }, []);

  return (
    <div className="page">
      <header className="page-header">
        <h1>Visão geral</h1>
        <p className="muted">
          Dashboard consolidado — ainda em migração. Use o Streamlit existente
          para as telas ainda não convertidas; o Ledger já opera nesta interface.
        </p>
      </header>
      {error && <ErrorBox message={error} />}
      {!error && !state && <Loading />}
      {state && (
        <div className="metric-grid">
          <Card title="Carteiras">{state.portfolios.length}</Card>
          <Card title="Instrumentos cadastrados">{state.instruments_count}</Card>
          <Card title="Transações no ledger">{state.transactions_count}</Card>
          <Card title="Snapshots persistidos">{state.snapshots_count}</Card>
        </div>
      )}
    </div>
  );
}
