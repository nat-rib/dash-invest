import { useEffect, useState } from "react";

import { Button, Card, EmptyState, ErrorBox, Loading, SelectInput, Table } from "../components/ui";
import type { DcfResult, ScreenerResponse } from "../services/screener";
import { calculateDcf, fetchScreener } from "../services/screener";

const SORT_OPTIONS = [
  { value: "roe", label: "ROE" },
  { value: "net_margin", label: "Margem líquida" },
  { value: "roa", label: "ROA" },
  { value: "revenue", label: "Receita" },
  { value: "net_income", label: "Lucro líquido" },
  { value: "asset_turnover", label: "Giro do ativo" },
];

export default function ScreenerPage() {
  const [screen, setScreen] = useState<ScreenerResponse | null>(null);
  const [minRoe, setMinRoe] = useState("");
  const [minNetMargin, setMinNetMargin] = useState("");
  const [sortBy, setSortBy] = useState("roe");
  const [order, setOrder] = useState<"asc" | "desc">("desc");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    setError(null);
    fetchScreener({
      minRoe: percentToFraction(minRoe),
      minNetMargin: percentToFraction(minNetMargin),
      sortBy,
      order,
    })
      .then(setScreen)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  return (
    <div className="page">
      <header className="page-header">
        <h1>Screener</h1>
        <p className="muted">
          Indicadores fundamentalistas anuais da CVM, calculados apenas quando numerador e
          denominador existem. Ordenação coloca indisponíveis no fim.
        </p>
      </header>
      <ErrorBoxRender error={error} />

      <Card title="Filtros">
        <div className="field-row">
          <div className="field">
            <span className="field-label">ROE mínimo (%)</span>
            <input type="text" value={minRoe} onChange={(event) => setMinRoe(event.target.value)} />
          </div>
          <div className="field">
            <span className="field-label">Margem líquida mínima (%)</span>
            <input
              type="text"
              value={minNetMargin}
              onChange={(event) => setMinNetMargin(event.target.value)}
            />
          </div>
          <div className="field">
            <span className="field-label">Ordenar por</span>
            <SelectInput value={sortBy} onChange={setSortBy} options={SORT_OPTIONS} />
          </div>
          <div className="field">
            <span className="field-label">Direção</span>
            <SelectInput
              value={order}
              onChange={(value) => setOrder(value as "asc" | "desc")}
              options={[
                { value: "desc", label: "Maior primeiro" },
                { value: "asc", label: "Menor primeiro" },
              ]}
            />
          </div>
          <div className="field">
            <span className="field-label">&nbsp;</span>
            <Button variant="primary" onClick={load}>
              Aplicar
            </Button>
          </div>
        </div>
      </Card>

      <Card title="Resultados" subtitle={screen ? `${screen.items.length} de ${screen.total} emissores` : undefined}>
        {loading && <Loading />}
        {!loading && screen && screen.items.length === 0 && (
          <EmptyState title="Nenhum emissor atende aos filtros." hint="Rode a ingestão DFP e afrouxe os critérios." />
        )}
        {!loading && screen && screen.items.length > 0 && (
          <Table head={["Emissor", "Receita", "Lucro líquido", "Margem", "ROE", "ROA", "Giro", "Exercício"]}>
            {screen.items.map((row) => (
              <tr key={row.cnpj}>
                <td>{row.name ?? row.cnpj}</td>
                <td>{formatMoney(row.revenue)}</td>
                <td>{formatMoney(row.net_income)}</td>
                <td>{formatPercent(row.net_margin)}</td>
                <td>{formatPercent(row.roe)}</td>
                <td>{formatPercent(row.roa)}</td>
                <td>{formatNumber(row.asset_turnover)}</td>
                <td>{row.reference_date ?? "—"}</td>
              </tr>
            ))}
          </Table>
        )}
        {!loading && screen && screen.items.length > 0 && (
          <p className="field-hint">
            ROE, ROA e margem extremos podem refletir patrimônio pequeno ou evento não
            recorrente; confira o documento na CVM antes de concluir.
          </p>
        )}
      </Card>

      <DcfCard />
    </div>
  );
}

function DcfCard() {
  const [base, setBase] = useState("1000000000");
  const [growth, setGrowth] = useState("8");
  const [years, setYears] = useState("5");
  const [terminal, setTerminal] = useState("3");
  const [discount, setDiscount] = useState("12");
  const [result, setResult] = useState<DcfResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const run = () => {
    const payload = {
      base_cash_flow: Number(base.replace(/\./g, "").replace(",", ".")),
      growth_rate: percentToNumber(growth),
      years: Number(years),
      terminal_growth: percentToNumber(terminal),
      discount_rate: percentToNumber(discount),
    };
    if (!Number.isFinite(payload.base_cash_flow) || payload.base_cash_flow <= 0) {
      setError("Informe um fluxo de caixa base positivo.");
      return;
    }
    setLoading(true);
    setError(null);
    calculateDcf(payload)
      .then(setResult)
      .catch((err: unknown) => {
        setResult(null);
        setError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => setLoading(false));
  };

  return (
    <Card title="Valuation — DCF" subtitle="Fluxo de caixa livre descontado com valor terminal de Gordon.">
      <div className="field-row">
        <div className="field">
          <span className="field-label">FCF base (R$)</span>
          <input type="text" value={base} onChange={(event) => setBase(event.target.value)} />
        </div>
        <div className="field">
          <span className="field-label">Crescimento (%)</span>
          <input type="text" value={growth} onChange={(event) => setGrowth(event.target.value)} />
        </div>
        <div className="field">
          <span className="field-label">Anos</span>
          <input type="text" value={years} onChange={(event) => setYears(event.target.value)} />
        </div>
        <div className="field">
          <span className="field-label">Perpetuidade (%)</span>
          <input type="text" value={terminal} onChange={(event) => setTerminal(event.target.value)} />
        </div>
        <div className="field">
          <span className="field-label">Desconto (%)</span>
          <input type="text" value={discount} onChange={(event) => setDiscount(event.target.value)} />
        </div>
        <div className="field">
          <span className="field-label">&nbsp;</span>
          <Button variant="primary" onClick={run}>
            Calcular
          </Button>
        </div>
      </div>
      <ErrorBoxRender error={error} />
      {loading && <Loading />}
      {result && (
        <>
          <div className="metric-grid">
            <p>
              <strong>Valor presente total</strong>
              <br />
              {formatMoney(result.enterprise_value)}
            </p>
            <p>
              <strong>Fluxos explícitos</strong>
              <br />
              {formatMoney(result.present_value_explicit)}
            </p>
            <p>
              <strong>Valor terminal</strong>
              <br />
              {formatMoney(result.present_value_terminal)}
            </p>
          </div>
          <Table head={["Ano", "FCF projetado", "Valor presente"]}>
            {result.projections.map((item) => (
              <tr key={item.year}>
                <td>{item.year}</td>
                <td>{formatMoney(item.cash_flow)}</td>
                <td>{formatMoney(item.present_value)}</td>
              </tr>
            ))}
          </Table>
          <p className="field-hint">
            Premissas informadas pelo usuário; não é recomendação de investimento.
          </p>
        </>
      )}
    </Card>
  );
}

function percentToNumber(value: string): number {
  const parsed = Number(value.replace(",", "."));
  return Number.isFinite(parsed) ? parsed / 100 : 0;
}

function percentToFraction(value: string): string | undefined {
  const parsed = Number(value.replace(",", "."));
  if (!value.trim() || !Number.isFinite(parsed)) return undefined;
  return String(parsed / 100);
}

function formatMoney(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "—";
  const abs = Math.abs(value);
  if (abs >= 1_000_000_000) {
    return `R$ ${(value / 1_000_000_000).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} bi`;
  }
  if (abs >= 1_000_000) {
    return `R$ ${(value / 1_000_000).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} mi`;
  }
  if (abs >= 1_000) {
    return `R$ ${(value / 1_000).toLocaleString("pt-BR", { maximumFractionDigits: 0 })} mil`;
  }
  return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
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
