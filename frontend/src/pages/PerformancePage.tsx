import { useCallback, useEffect, useState } from "react";
import {
  Button, Card, EmptyState, ErrorBox, Field, Loading, Table, TextInput,
} from "../components/ui";
import {
  calculateTwr, calculateXirr, fetchPerformanceFlows, fetchTwrValuations,
  saveTwrValuations,
} from "../services/ledger";
import type { PerformanceFlows, TwrPeriod } from "../services/ledger";

export default function PerformancePage() {
  return (
    <div className="page">
      <header className="page-header">
        <h1>Rentabilidade da carteira</h1>
        <p className="muted">
          TWR remove o efeito dos fluxos externos; XIRR mede a taxa anualizada sob a ótica do investidor.
        </p>
      </header>
      <FlowsCard />
      <XirrCard />
      <TwrCard />
      <Card>
        <p className="muted">
          Limitação importante: TWR só é confiável quando as avaliações delimitam corretamente os
          fluxos externos. O app não estima cotações nem inventa valores intermediários. Fluxos em
          moedas diferentes exigem conversão cambial explícita.
        </p>
      </Card>
    </div>
  );
}

function FlowsCard() {
  const [flows, setFlows] = useState<PerformanceFlows | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchPerformanceFlows()
      .then(setFlows)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)));
  }, []);

  return (
    <Card title="Fluxos externos identificados no ledger">
      {error && <ErrorBox message={error} />}
      {!flows && !error && <Loading />}
      {flows && flows.unavailable_reason && (
        <ErrorBox message={flows.unavailable_reason} />
      )}
      {flows && flows.flows.length === 0 && !flows.unavailable_reason && (
        <EmptyState
          title="Ainda não há aportes ou retiradas registrados."
          hint="Transferências internas e proventos não são tratados como fluxos externos."
        />
      )}
      {flows && flows.flows.length > 0 && (
        <Table head={["Data", "Fluxo do investidor", "Moeda"]} empty={false}>
          {flows.flows.map((flow) => (
            <tr key={`${flow.date}-${flow.amount}`}>
              <td>{formatDate(flow.date)}</td>
              <td>{flow.amount}</td>
              <td>{flow.currency}</td>
            </tr>
          ))}
        </Table>
      )}
      {flows && (
        <p className="muted">
          Carteira {flows.portfolio_name} · aporte negativo, retirada positiva.
        </p>
      )}
    </Card>
  );
}

function XirrCard() {
  const [portfolioCurrency, setPortfolioCurrency] = useState<string>("BRL");
  const [terminalValue, setTerminalValue] = useState("");
  const [terminalDate, setTerminalDate] = useState(new Date().toISOString().slice(0, 10));
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    fetchPerformanceFlows().then((data: PerformanceFlows) => {
      if (data.currency) setPortfolioCurrency(data.currency);
    }).catch(() => undefined);
  }, []);

  async function run() {
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const outcome = await calculateXirr(terminalValue, terminalDate);
      const percent = (parseFloat(outcome.annual_rate) * 100).toFixed(2);
      setResult(`XIRR anualizada: ${percent}% · fluxos usados: ${outcome.flows_used}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card
      title="XIRR — retorno ponderado pelo dinheiro"
      subtitle="Aportes são fluxos negativos, retiradas positivas e o patrimônio informado entra como valor terminal. Usa datas reais e base anual de 365 dias."
    >
      <div className="field-row">
        <Field label={`Patrimônio final (${portfolioCurrency})`}>
          <TextInput value={terminalValue} onChange={setTerminalValue} placeholder="0.00" />
        </Field>
        <Field label="Data da avaliação final">
          <TextInput value={terminalDate} onChange={setTerminalDate} placeholder="AAAA-MM-DD" />
        </Field>
        <Button variant="primary" onClick={run} disabled={busy || !terminalValue}>
          Calcular XIRR
        </Button>
      </div>
      {error && <ErrorBox message={error} />}
      {result && <div className="success-box">{result}</div>}
    </Card>
  );
}

function TwrCard() {
  const emptyRow: TwrPeriod = {
    start_date: "", end_date: "", start_value: "",
    end_value_after_flows: "", net_external_flow: "0",
  };
  const [periods, setPeriods] = useState<TwrPeriod[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    setBusy(true);
    fetchTwrValuations()
      .then((data) => {
        setPeriods(data.periods.length > 0 ? data.periods : [emptyRow]);
        setError(null);
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)))
      .finally(() => setBusy(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useEffect(load, [load]);

  function updateRow(index: number, field: keyof TwrPeriod, value: string) {
    setPeriods(periods.map((row, rowIndex) => (
      rowIndex === index ? { ...row, [field]: value } : row
    )));
  }

  async function persist() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await saveTwrValuations(completeRows());
      setMessage("Períodos TWR salvos.");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  function completeRows(): TwrPeriod[] {
    return periods.filter((row) => row.start_date && row.end_date && row.start_value);
  }

  async function runCalculate() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const rows = completeRows();
      if (rows.length === 0) {
        setError("Preencha ao menos um período completo antes de calcular.");
        return;
      }
      const outcome = await calculateTwr(rows);
      const percent = (parseFloat(outcome.rate) * 100).toFixed(2);
      setMessage(
        `TWR acumulado: ${percent}% · ${outcome.periods} períodos · ${formatDate(outcome.start_date)} a ${formatDate(outcome.end_date)}`,
      );
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  const fields: { key: keyof TwrPeriod; label: string; placeholder: string }[] = [
    { key: "start_date", label: "Início", placeholder: "AAAA-MM-DD" },
    { key: "end_date", label: "Fim", placeholder: "AAAA-MM-DD" },
    { key: "start_value", label: "Valor inicial", placeholder: "0.00" },
    { key: "end_value_after_flows", label: "Valor final após fluxos", placeholder: "0.00" },
    { key: "net_external_flow", label: "Fluxo (+ aporte / − retirada)", placeholder: "0.00" },
  ];

  return (
    <Card
      title="TWR — retorno ponderado pelo tempo"
      subtitle="Informe avaliações consecutivas; o valor final de cada período deve ser observado imediatamente após o fluxo externo desse fim."
    >
      {error && <ErrorBox message={error} />}
      {message && <div className="success-box">{message}</div>}
      {busy && <Loading label="Atualizando…" />}
      {periods.length === 0 && !busy && <EmptyState title="Sem períodos cadastrados." />}
      {periods.length > 0 && (
        <>
          <Table head={["Início", "Fim", "Valor inicial", "Valor final pós-fluxo", "Fluxo líquido"]} empty={false}>
            {periods.map((row, index) => (
              <tr key={index}>
                {fields.map((field) => (
                  <td key={field.key}>
                    <input
                      className="cell-input"
                      value={row[field.key]}
                      placeholder={field.placeholder}
                      onChange={(event) => updateRow(index, field.key, event.target.value)}
                    />
                  </td>
                ))}
                <td>
                  <Button onClick={() => setPeriods(periods.filter((_, i) => i !== index))} disabled={busy && periods.length === 1}>
                    Remover
                  </Button>
                </td>
              </tr>
            ))}
          </Table>
          <Button onClick={() => setPeriods([...periods, emptyRow])} disabled={busy}>
            Adicionar período
          </Button>
          <Button onClick={persist} disabled={busy}>Salvar períodos</Button>
          <Button variant="primary" onClick={runCalculate} disabled={busy}>Calcular TWR</Button>
          <p className="muted">
            Salvar persiste na carteira; calcular usa os períodos desta tela.
          </p>
        </>
      )}
    </Card>
  );
}

function formatDate(value: string): string {
  const [year, month, day] = value.slice(0, 10).split("-");
  return `${day}/${month}/${year}`;
}
