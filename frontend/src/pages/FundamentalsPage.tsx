import { useEffect, useMemo, useState } from "react";

import { ResponsiveChart } from "../components/insights";
import { Button, Card, EmptyState, ErrorBox, Loading, SelectInput, Table } from "../components/ui";
import type { FundamentalsDataset, Issuer, ObservationSeries } from "../services/observations";
import { fetchIssuers, fetchObservationSeries } from "../services/observations";

const QUICK_METRICS = [
  { metric: "revenue", label: "Receita" },
  { metric: "gross_profit", label: "Lucro bruto" },
  { metric: "operating_income", label: "Resultado operacional" },
  { metric: "net_income", label: "Lucro líquido" },
  { metric: "total_assets", label: "Ativo total" },
  { metric: "equity", label: "Patrimônio líquido" },
];

const METRIC_LABELS: Record<string, string> = Object.fromEntries(
  QUICK_METRICS.map((item) => [item.metric, item.label]),
);

export default function FundamentalsPage() {
  const [issuers, setIssuers] = useState<Issuer[]>([]);
  const [issuerQuery, setIssuerQuery] = useState("");
  const [selected, setSelected] = useState("");
  const [metricDraft, setMetricDraft] = useState("revenue");
  const [metric, setMetric] = useState("revenue");
  const [dataset, setDataset] = useState<FundamentalsDataset>("dfp");
  const [ytd, setYtd] = useState(false);
  const [series, setSeries] = useState<ObservationSeries | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const apiMetric =
    dataset === "itr" && ytd && !metric.endsWith("_ytd") ? `${metric}_ytd` : metric;

  useEffect(() => {
    fetchIssuers()
      .then((data) => {
        setIssuers(data.items);
        setSelected((current) => current || data.items[0]?.cnpj || "");
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)));
  }, []);

  useEffect(() => {
    if (!selected) {
      setSeries(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchObservationSeries(selected, apiMetric, dataset)
      .then((data) => {
        if (!cancelled) setSeries(data);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setSeries(null);
          setError(err instanceof Error ? err.message : String(err));
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selected, apiMetric, dataset]);

  const filteredIssuers = useMemo(() => {
    const query = issuerQuery.trim().toLowerCase();
    if (!query) return issuers;
    const digits = query.replace(/\D/g, "");
    return issuers.filter(
      (issuer) =>
        issuer.name.toLowerCase().includes(query) ||
        (digits !== "" && issuer.cnpj.includes(digits)),
    );
  }, [issuers, issuerQuery]);

  const options = useMemo(() => {
    const items = filteredIssuers.map((issuer) => ({
      value: issuer.cnpj,
      label: `${issuer.name} · ${formatCnpj(issuer.cnpj)}`,
    }));
    if (selected && !items.some((item) => item.value === selected)) {
      const current = issuers.find((issuer) => issuer.cnpj === selected);
      if (current) {
        items.unshift({
          value: current.cnpj,
          label: `${current.name} · ${formatCnpj(current.cnpj)}`,
        });
      }
    }
    return items;
  }, [filteredIssuers, issuers, selected]);

  const points = series?.points ?? [];
  const chartPoints = points
    .map((point) => ({ label: point.reference_date, value: Number(point.value) }))
    .filter((point) => Number.isFinite(point.value));
  const latest = points.length > 0 ? points[points.length - 1] : null;
  const selectedIssuer = issuers.find((issuer) => issuer.cnpj === selected) ?? null;

  const applyMetric = (value: string) => {
    const normalized = value.trim() || "revenue";
    setMetricDraft(normalized);
    setMetric(normalized);
  };

  return (
    <div className="page">
      <header className="page-header">
        <h1>Fundamentos</h1>
        <p className="muted">
          Demonstrações financeiras padronizadas da CVM (DFP anual e ITR trimestral). Valores
          normalizados para BRL; exercícios sem publicação não são exibidos como zero.
        </p>
      </header>
      <ErrorBoxRender error={error} />

      <Card title="Emissor e métrica">
        <div className="field-row">
          <div className="field">
            <span className="field-label">Buscar emissor</span>
            <input
              type="text"
              value={issuerQuery}
              placeholder="nome ou CNPJ"
              onChange={(event) => setIssuerQuery(event.target.value)}
            />
          </div>
          <div className="field">
            <span className="field-label">Emissor</span>
            <SelectInput value={selected} onChange={setSelected} options={options} />
          </div>
          <div className="field">
            <span className="field-label">Periodicidade</span>
            <SelectInput
              value={dataset}
              onChange={(value) => {
                const next = value as FundamentalsDataset;
                setDataset(next);
                if (next === "dfp") setYtd(false);
              }}
              options={[
                { value: "dfp", label: "Anual (DFP)" },
                { value: "itr", label: "Trimestral (ITR)" },
              ]}
            />
          </div>
        </div>
        <div className="field-row">
          <div className="field">
            <span className="field-label">Métrica</span>
            <input
              type="text"
              value={metricDraft}
              list="metric-suggestions"
              onChange={(event) => setMetricDraft(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") applyMetric(metricDraft);
              }}
            />
            <datalist id="metric-suggestions">
              {QUICK_METRICS.map((item) => (
                <option key={item.metric} value={item.metric}>
                  {item.label}
                </option>
              ))}
            </datalist>
          </div>
          <div className="field">
            <span className="field-label">&nbsp;</span>
            {dataset === "itr" && (
              <label className="field-hint">
                <input
                  type="checkbox"
                  checked={ytd}
                  onChange={(event) => setYtd(event.target.checked)}
                />{" "}
                Acumulado no ano (YTD)
              </label>
            )}
          </div>
          <div className="field">
            <span className="field-label">&nbsp;</span>
            <Button variant="primary" onClick={() => applyMetric(metricDraft)}>
              Consultar
            </Button>
          </div>
        </div>
        <div className="field-row">
          {QUICK_METRICS.map((item) => (
            <Button key={item.metric} variant="ghost" onClick={() => applyMetric(item.metric)}>
              {item.label}
            </Button>
          ))}
        </div>
      </Card>

      <Card
        title="Série histórica"
        subtitle={
          selectedIssuer
            ? `${selectedIssuer.name} · ${METRIC_LABELS[metric] ?? metric} · ${
                dataset === "itr" ? (ytd ? "acumulado no ano" : "trimestral") : "anual"
              }`
            : "Selecione um emissor e uma métrica."
        }
      >
        {loading && <Loading />}
        {!loading && !series && !selected && (
          <EmptyState
            title="Nenhum emissor disponível."
            hint="Rode a ingestão da CVM para popular os fundamentos."
          />
        )}
        {!loading && series && points.length === 0 && (
          <EmptyState
            title="Sem observações para este emissor e métrica."
            hint="Tente outra métrica ou exercício; ausência de dado não é zero."
          />
        )}
        {!loading && series && points.length > 0 && (
          <>
            {latest && (
              <p className="muted">
                Último valor: <strong>{formatCurrency(Number(latest.value), latest.currency)}</strong>{" "}
                em {formatDate(latest.reference_date)}.
              </p>
            )}
            <ResponsiveChart
              ariaLabel={`Série de ${metric} de ${selectedIssuer?.name ?? "emissor"}`}
              points={chartPoints}
              formatValue={(value) => formatCurrency(value, latest?.currency ?? "BRL")}
              formatTick={compactCurrency}
            />
            <Table head={["Exercício", "Valor", "Publicado em", "Documento"]}>
              {points
                .slice()
                .reverse()
                .map((point) => (
                  <tr key={`${point.reference_date}-${point.published_at ?? ""}`}>
                    <td>{formatDate(point.reference_date)}</td>
                    <td>{formatCurrency(Number(point.value), point.currency)}</td>
                    <td>{point.published_at ? formatDate(point.published_at.slice(0, 10)) : "—"}</td>
                    <td>
                      {point.source_document ? (
                        <a href={point.source_document} target="_blank" rel="noreferrer">
                          CVM
                        </a>
                      ) : (
                        "—"
                      )}
                    </td>
                  </tr>
                ))}
            </Table>
          </>
        )}
      </Card>
    </div>
  );
}

function ErrorBoxRender({ error }: { error: string | null }) {
  if (!error) return null;
  return <ErrorBox message={error} />;
}

function formatCnpj(value: string): string {
  const digits = value.replace(/\D/g, "");
  if (digits.length !== 14) return value;
  return `${digits.slice(0, 2)}.${digits.slice(2, 5)}.${digits.slice(5, 8)}/${digits.slice(8, 12)}-${digits.slice(12)}`;
}

function formatDate(iso: string): string {
  const [year, month, day] = iso.split("-");
  if (!year || !month || !day) return iso;
  return `${day}/${month}/${year}`;
}

function formatCurrency(value: number, currency: string | null): string {
  try {
    return value.toLocaleString("pt-BR", {
      style: "currency",
      currency: currency || "BRL",
      maximumFractionDigits: 0,
    });
  } catch {
    return value.toLocaleString("pt-BR", { maximumFractionDigits: 0 });
  }
}

function compactCurrency(value: number): string {
  const abs = Math.abs(value);
  if (abs >= 1_000_000_000) {
    return `${(value / 1_000_000_000).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} bi`;
  }
  if (abs >= 1_000_000) {
    return `${(value / 1_000_000).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} mi`;
  }
  if (abs >= 1_000) {
    return `${(value / 1_000).toLocaleString("pt-BR", { maximumFractionDigits: 0 })} mil`;
  }
  return value.toLocaleString("pt-BR", { maximumFractionDigits: 0 });
}
