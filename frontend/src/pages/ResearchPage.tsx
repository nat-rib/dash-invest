import { useEffect, useMemo, useState } from "react";

import { Button, Card, EmptyState, ErrorBox, Loading, SelectInput, Table } from "../components/ui";
import type { Issuer } from "../services/observations";
import { fetchIssuers } from "../services/observations";
import type { ResearchReport } from "../services/research";
import { fetchResearch } from "../services/research";

const METRIC_LABELS: Record<string, string> = {
  revenue: "Receita",
  net_income: "Lucro líquido",
  equity: "Patrimônio líquido",
  total_assets: "Ativo total",
  net_margin: "Margem líquida",
  roe: "ROE",
  revenue_growth: "Crescimento da receita",
};

export default function ResearchPage() {
  const [issuers, setIssuers] = useState<Issuer[]>([]);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState("");
  const [report, setReport] = useState<ResearchReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchIssuers()
      .then((data) => {
        setIssuers(data.items);
        setSelected((current) => current || data.items[0]?.cnpj || "");
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)));
  }, []);

  const options = useMemo(() => {
    const term = query.trim().toLowerCase();
    const digits = term.replace(/\D/g, "");
    return issuers
      .filter(
        (issuer) =>
          !term ||
          issuer.name.toLowerCase().includes(term) ||
          (digits !== "" && issuer.cnpj.includes(digits)),
      )
      .map((issuer) => ({
        value: issuer.cnpj,
        label: `${issuer.name} · ${formatCnpj(issuer.cnpj)}`,
      }));
  }, [issuers, query]);

  const generate = () => {
    if (!selected) return;
    setLoading(true);
    setError(null);
    fetchResearch(selected)
      .then(setReport)
      .catch((err: unknown) => {
        setReport(null);
        setError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => setLoading(false));
  };

  return (
    <div className="page">
      <header className="page-header">
        <h1>Pesquisa IA</h1>
        <p className="muted">
          A narrativa usa apenas fatos calculados pelo backend e cita a fonte de cada afirmação.
          Sem gateway configurado, o relatório é determinístico e não chama nenhum serviço externo.
        </p>
      </header>
      <ErrorBoxRender error={error} />

      <Card title="Emissor">
        <div className="field-row">
          <div className="field">
            <span className="field-label">Buscar</span>
            <input
              type="text"
              value={query}
              placeholder="nome ou CNPJ"
              onChange={(event) => setQuery(event.target.value)}
            />
          </div>
          <div className="field">
            <span className="field-label">Emissor</span>
            <SelectInput value={selected} onChange={setSelected} options={options} />
          </div>
          <div className="field">
            <span className="field-label">&nbsp;</span>
            <Button variant="primary" onClick={generate} disabled={!selected || loading}>
              Gerar relatório
            </Button>
          </div>
        </div>
      </Card>

      {loading && <Loading />}
      {!loading && !report && (
        <Card>
          <EmptyState
            title="Nenhum relatório gerado."
            hint="Escolha um emissor e clique em Gerar relatório."
          />
        </Card>
      )}

      {!loading && report && (
        <>
          <Card
            title={`Relatório — ${report.name}`}
            subtitle={`Gerado em ${new Date(report.generated_at).toLocaleString("pt-BR")} · ${gatewayLabel(report.gateway)}`}
          >
            {report.narrative.split(/\n{2,}/).map((paragraph) => (
              <p key={paragraph.slice(0, 40)}>{paragraph}</p>
            ))}
          </Card>

          <Card title="Afirmações e evidências">
            <Table head={["Métrica", "Afirmação", "Exercício", "Fonte"]}>
              {report.claims.map((claim) => (
                <tr key={claim.key}>
                  <td>{METRIC_LABELS[claim.metric] ?? claim.metric}</td>
                  <td>{claim.text}</td>
                  <td>{claim.reference_date ?? "—"}</td>
                  <td>
                    {claim.source_url ? (
                      <a href={claim.source_url} target="_blank" rel="noreferrer">
                        documento
                      </a>
                    ) : (
                      "—"
                    )}
                  </td>
                </tr>
              ))}
            </Table>
          </Card>

          {report.limitations.length > 0 && (
            <div className="warning-box">
              <strong>Limitações</strong>
              <ul>
                {report.limitations.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function gatewayLabel(value: string): string {
  return value === "deterministic" ? "narrativa determinística (sem LLM)" : value;
}

function formatCnpj(value: string): string {
  const digits = value.replace(/\D/g, "");
  if (digits.length !== 14) return value;
  return `${digits.slice(0, 2)}.${digits.slice(2, 5)}.${digits.slice(5, 8)}/${digits.slice(8, 12)}-${digits.slice(12)}`;
}

function ErrorBoxRender({ error }: { error: string | null }) {
  if (!error) return null;
  return <ErrorBox message={error} />;
}
