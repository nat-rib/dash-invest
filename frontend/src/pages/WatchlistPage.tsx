import { useEffect, useMemo, useState } from "react";

import { Button, Card, EmptyState, ErrorBox, Loading, Table } from "../components/ui";
import type { Candidate } from "../services/monitor";
import { fetchCandidates } from "../services/monitor";
import type { WatchlistItem } from "../services/watchlist";
import { fetchWatchlist, removeWatchlist } from "../services/watchlist";

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

export default function WatchlistPage() {
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    setError(null);
    Promise.all([fetchWatchlist(), fetchCandidates({ limit: 200 })])
      .then(([watchlist, ranking]) => {
        setItems(watchlist.items);
        setCandidates(ranking.items);
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const byKey = useMemo(
    () => new Map(candidates.map((candidate) => [candidate.key, candidate])),
    [candidates],
  );

  const remove = (assetKey: string) => {
    removeWatchlist(assetKey)
      .then(() =>
        setItems((current) => current.filter((item) => item.asset_key !== assetKey)),
      )
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)));
  };

  return (
    <div className="page">
      <header className="page-header">
        <h1>Watchlist</h1>
        <p className="muted">
          Ativos que você escolheu acompanhar. O score e o último sinal vêm do monitor quando o
          ativo aparece nas fontes recentes; a watchlist continua válida mesmo sem sinal.
        </p>
      </header>
      <ErrorBoxRender error={error} />

      {loading && <Loading />}
      {!loading && items.length === 0 && (
        <Card>
          <EmptyState
            title="Nenhum ativo na watchlist."
            hint="Use o botão Seguir no Radar para adicionar ativos."
          />
        </Card>
      )}
      {!loading && items.length > 0 && (
        <Card title="Ativos acompanhados" subtitle={`${items.length} ativo(s)`}>
          <Table head={["Ativo", "Classe", "Score atual", "Último sinal", "Ações"]}>
            {items.map((item) => {
              const candidate = byKey.get(item.asset_key);
              return (
                <tr key={item.asset_key}>
                  <td>{item.name}</td>
                  <td>{CLASS_LABELS[item.asset_class] ?? item.asset_class}</td>
                  <td>{candidate ? candidate.score.toFixed(0) : "—"}</td>
                  <td>
                    {candidate?.last_seen
                      ? formatDate(candidate.last_seen)
                      : "sem sinal recente"}
                  </td>
                  <td>
                    <div className="radar-actions">
                      {candidate?.cnpj && (
                        <a className="button ghost" href={`/fundamentos?cnpj=${candidate.cnpj}`}>
                          Fundamentos
                        </a>
                      )}
                      {candidate?.price_provider && candidate.price_instrument && (
                        <a
                          className="button ghost"
                          href={`/risco?provider=${encodeURIComponent(candidate.price_provider)}&instrument=${encodeURIComponent(candidate.price_instrument)}`}
                        >
                          Risco
                        </a>
                      )}
                      <Button variant="danger" onClick={() => remove(item.asset_key)}>
                        Remover
                      </Button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </Table>
        </Card>
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
