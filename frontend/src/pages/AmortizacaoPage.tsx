import { useCallback, useState } from "react";
import { Button, Card, EmptyState, ErrorBox, Field, Loading, Table, TextInput } from "../components/ui";
import { sendJson } from "../services/api";

interface BalancePoint {
  month: number;
  saldo_final: number;
  scenario: string;
}

interface CompareOut {
  months_saved: number;
  interest_saved: number;
  payment_saved: number;
  invest_value: number;
  amortization_value: number;
  difference: number;
  winner: string;
  break_even_net_return: number;
  horizon_months: number;
  alternative_months: number;
  balance_series: BalancePoint[];
}

interface ScheduleRow {
  month: number;
  saldo_inicial: number;
  saldo_corrigido: number;
  amortizacao: number;
  juros: number;
  encargos: number;
  parcela: number;
  saldo_final: number;
}

interface SimulationOut {
  months: number;
  total_interest: number;
  total_paid: number;
  schedule_rows: ScheduleRow[];
}

const DEFAULTS = {
  balance: "245135.45",
  months: "226",
  annual_interest: "10.7447",
  annual_tr: "0",
  monthly_fees: "0",
  extra: "8464",
  mode: "prazo",
  net_annual_return: "10",
};

export default function AmortizacaoPage() {
  const [form, setForm] = useState(DEFAULTS);
  const [result, setResult] = useState<CompareOut | null>(null);
  const [simulation, setSimulation] = useState<SimulationOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const payload = useCallback(() => ({
    balance: parseFloat(form.balance),
    months: parseInt(form.months, 10),
    annual_interest: parseFloat(form.annual_interest) / 100,
    annual_tr: parseFloat(form.annual_tr) / 100,
    monthly_fees: parseFloat(form.monthly_fees),
    extra: parseFloat(form.extra),
    mode: form.mode,
    net_annual_return: parseFloat(form.net_annual_return) / 100,
  }), [form]);

  async function run() {
    setBusy(true);
    setError(null);
    setSimulation(null);
    setResult(null);
    try {
      const [sim, comp] = await Promise.all([
        sendJson<SimulationOut>("/api/mortgage/simulate", "POST", { ...payload(), rows_limit: 6 }),
        sendJson<CompareOut>("/api/mortgage/compare", "POST", payload()),
      ]);
      setSimulation(sim);
      setResult(comp);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  function update(key: keyof typeof DEFAULTS, value: string) {
    setForm({ ...form, [key]: value });
  }

  return (
    <div className="page">
      <header className="page-header">
        <h1>Amortizar ou investir</h1>
        <p className="muted">
          Projeção para financiamento SAC + TR. Valores estimados; confira sempre a simulação e o
          boleto oficial antes de amortizar.
        </p>
      </header>
      <Card>
        <div className="field-grid">
          <Field label="Saldo devedor atual (R$)">
            <TextInput value={form.balance} onChange={(value) => update("balance", value)} />
          </Field>
          <Field label="Prazo restante (meses)">
            <TextInput value={form.months} onChange={(value) => update("months", value)} />
          </Field>
          <Field label="Juros nominais anuais (%)">
            <TextInput value={form.annual_interest} onChange={(value) => update("annual_interest", value)} />
          </Field>
          <Field label="TR anual estimada (%)" hint="A TR futura é desconhecida; ajuste o cenário.">
            <TextInput value={form.annual_tr} onChange={(value) => update("annual_tr", value)} />
          </Field>
          <Field label="Seguros e taxas mensais (R$)" hint="MIP, DFI e tarifa, se souber.">
            <TextInput value={form.monthly_fees} onChange={(value) => update("monthly_fees", value)} />
          </Field>
          <Field label="Valor para decidir (R$)">
            <TextInput value={form.extra} onChange={(value) => update("extra", value)} />
          </Field>
          <Field label="Se amortizar">
            <select
              value={form.mode}
              onChange={(event) => update("mode", event.target.value)}
            >
              <option value="prazo">Reduzir prazo</option>
              <option value="parcela">Reduzir parcela</option>
            </select>
          </Field>
          <Field label="Retorno líquido anual do investimento (%)" hint="Já líquido de IR e custos.">
            <TextInput value={form.net_annual_return} onChange={(value) => update("net_annual_return", value)} />
          </Field>
        </div>
        <Button variant="primary" onClick={run} disabled={busy}>Simular e comparar</Button>
        {busy && <Loading label="Projetando…" />}
        {error && <ErrorBox message={error} />}
      </Card>
      {result && simulation && (
        <>
          <Card title="Decisão no cenário informado">
            <div className="detail-metrics">
              <div className="metric-box">
                <span className="metric-label">Vencedor</span>
                <span className="metric-value">{result.winner}</span>
              </div>
              <div className="metric-box">
                <span className="metric-label">Diferença ao fim de {result.horizon_months} meses</span>
                <span className="metric-value">{brl(Math.abs(result.difference))}</span>
              </div>
              <div className="metric-box">
                <span className="metric-label">Juros evitados</span>
                <span className="metric-value">{brl(result.interest_saved)}</span>
              </div>
              <div className="metric-box">
                <span className="metric-label">Prazo reduzido</span>
                <span className="metric-value">{result.months_saved} meses</span>
              </div>
              <div className="metric-box">
                <span className="metric-label">Retorno de equilíbrio</span>
                <span className="metric-value">{(result.break_even_net_return * 100).toFixed(2)}% a.a.</span>
              </div>
              <div className="metric-box">
                <span className="metric-label">Investir hoje →</span>
                <span className="metric-value">{brl(result.invest_value)}</span>
              </div>
              <div className="metric-box">
                <span className="metric-label">Amortizar + reaplicar parcelas →</span>
                <span className="metric-value">{brl(result.amortization_value)}</span>
              </div>
            </div>
            <p className="muted">
              Ao fim do prazo original: investir o valor hoje gera {brl(result.invest_value)};
              amortizar e investir as parcelas economizadas gera {brl(result.amortization_value)}.
              Acima da taxa de equilíbrio investir vence; abaixo dela, amortizar vence.
            </p>
            <div className="warning-box">
              A comparação supõe retorno líquido constante e reinvestimento das economias. TR,
              seguros, taxas, impostos e retorno podem variar; não é recomendação individual. A
              decisão Investir não mede segurança, liquidez ou risco; amortizar também reduz dívida
              e risco de fluxo de caixa.
            </div>
            <BalanceChart series={result.balance_series} />
          </Card>
          <Card title="Parcelas projetadas (primeiros meses, sem amortização)">
            <Table head={["Mês", "Saldo inicial", "Amortização", "Juros", "Encargos", "Parcela", "Saldo final"]} empty={false}>
              {simulation.schedule_rows.map((row) => (
                <tr key={row.month}>
                  <td>{row.month}</td>
                  <td>{brl(row.saldo_inicial)}</td>
                  <td>{brl(row.amortizacao)}</td>
                  <td>{brl(row.juros)}</td>
                  <td>{brl(row.encargos)}</td>
                  <td>{brl(row.parcela)}</td>
                  <td>{brl(row.saldo_final)}</td>
                </tr>
              ))}
            </Table>
            <p className="muted">
              Juros totais sem amortização: {brl(simulation.total_interest)} · total pago: {brl(simulation.total_paid)}.
            </p>
          </Card>
        </>
      )}
      {!result && !busy && !error && (
        <EmptyState title="Preencha os parâmetros e clique em Simular e comparar." />
      )}
    </div>
  );
}

function BalanceChart({ series }: { series: BalancePoint[] }) {
  const width = 100;
  const height = 40;
  const byScenario = groupBy(series, (point) => point.scenario);
  const maxMonth = Math.max(...series.map((point) => point.month));
  const maxBalance = Math.max(...series.map((point) => point.saldo_final));
  const palette = ["var(--chart-1)", "var(--chart-2)"];
  return (
    <div className="chart-legend">
      <svg viewBox={`0 0 ${width} ${height}`} className="line-chart" role="img" aria-label="Saldo devedor projetado">
        {[...byScenario.entries()].map(([scenario, points], scenarioIndex) => (
          <polyline
            key={scenario}
            points={points.map((point) => {
              const x = ((point.month - 1) / Math.max(maxMonth - 1, 1)) * width;
              const y = height - (point.saldo_final / (maxBalance || 1)) * height;
              return `${x.toFixed(2)},${y.toFixed(2)}`;
            }).join(" ")}
            fill="none"
            stroke={palette[scenarioIndex % palette.length]}
            strokeWidth="1.1"
          />
        ))}
      </svg>
      <div className="legend-row">
        {[...byScenario.keys()].map((scenario, index) => (
          <span key={scenario}>
            <span
              className="legend-dot"
              style={{ background: palette[index % palette.length] }}
              aria-hidden="true"
            />
            {scenario}
          </span>
        ))}
      </div>
    </div>
  );
}

function groupBy<T, K extends string>(items: T[], key: (item: T) => K): Map<K, T[]> {
  const result = new Map<K, T[]>();
  for (const item of items) {
    const group = key(item);
    if (!result.has(group)) result.set(group, []);
    result.get(group)!.push(item);
  }
  return result;
}

function brl(value: number): string {
  if (!Number.isFinite(value)) return "—";
  return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}
