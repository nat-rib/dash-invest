import { useCallback, useEffect, useState } from "react";
import {
  Badge, Button, Card, EmptyState, ErrorBox, Field, Loading, SelectInput, Table,
} from "../components/ui";
import { getJson, sendJson } from "../services/api";

interface MarketPosition {
  index: number;
  name: string;
  symbol: string;
}

interface QuoteRow {
  index: number;
  name: string;
  symbol: string;
  price: string;
  price_date: string | null;
}

interface PreviewPosition {
  index: number;
  institution: string;
  ticker: string | null;
  name: string;
  currency: string;
  quantity: string | null;
  current_price: string | null;
  current_value: string | null;
  converted_value_brl: string | null;
  conversion_rate_to_brl: string | null;
  changed: boolean;
}

interface PreviewOut {
  quotes: QuoteRow[];
  fx_rates: { currency: string; rate: string; as_of_date: string | null }[];
  errors: string[];
  positions: PreviewPosition[];
}

interface HistoryPoint {
  date: string;
  close: string;
}

export default function MercadoPage() {
  return (
    <div className="page">
      <header className="page-header">
        <h1>Cotações e histórico</h1>
        <p className="muted">
          Fonte: Alpha Vantage. Apenas símbolos de negociação são enviados ao provedor; saldos,
          quantidades e instituições permanecem locais.
        </p>
      </header>
      <QuotesFlow />
      <HistoryFlow />
      <ManualRegisterCard />
    </div>
  );
}

function QuotesFlow() {
  const [positions, setPositions] = useState<MarketPosition[] | null>(null);
  const [previewData, setPreviewData] = useState<PreviewOut | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    getJson<MarketPosition[]>("/api/market/positions")
      .then(setPositions)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)));
  }, []);

  async function runPreview() {
    setBusy(true);
    setError(null);
    setMessage(null);
    setConfirmed(false);
    setPreviewData(null);
    try {
      setPreviewData(await sendJson<PreviewOut>("/api/market/quotes/preview", "POST", null));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function applyConfirm() {
    setBusy(true);
    setError(null);
    try {
      const result = await sendJson<{ message: string }>("/api/market/quotes/confirm", "POST", null);
      setMessage(result.message);
      setPreviewData(null);
      setConfirmed(false);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card title="Atualizar preços das posições cotáveis">
      <p className="muted">
        A prévia consulta uma cotação por ativo e registra o resultado no histórico local. Revise e
        confirme para substituir o portfolio.json.
      </p>
      {positions !== null && positions.length === 0 && (
        <EmptyState
          title="Não há posições cotáveis."
          hint="Preencha ticker ou market_symbol nas ações, FIIs e ETFs."
        />
      )}
      <Button variant="primary" onClick={runPreview} disabled={busy}>
        Consultar preços atuais
      </Button>
      {busy && <Loading label="Consultando provedor…" />}
      {error && <ErrorBox message={error} />}
      {previewData && (
        <>
          {previewData.errors.length > 0 && (
            <ErrorBox message={previewData.errors.join(" · ")} />
          )}
          <h3>Cotações obtidas</h3>
          <Table head={["Ativo", "Símbolo", "Preço", "Data do fechamento"]} empty={previewData.quotes.length === 0}>
            {previewData.quotes.map((quote) => (
              <tr key={quote.index}>
                <td>{quote.name}</td>
                <td className="mono">{quote.symbol}</td>
                <td>{parseFloat(quote.price).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                <td>{quote.price_date ?? "—"}</td>
              </tr>
            ))}
          </Table>
          <h3>Prévia das posições</h3>
          <Table
            head={["Ativo", "Instituição", "Preço", "Valor", "Convertido BRL", "Alterado"]}
            empty={false}
          >
            {previewData.positions.map((position) => (
              <tr key={position.index}>
                <td>{position.name}</td>
                <td>{position.institution}</td>
                <td>{position.current_price ?? "—"}</td>
                <td>{position.current_value ?? "—"}</td>
                <td>{position.converted_value_brl ?? "—"}</td>
                <td>{position.changed ? <Badge tone="info">atualizado</Badge> : <span className="muted">inalterado</span>}</td>
              </tr>
            ))}
          </Table>
          <div className="field-row">
            <label className="checkline">
              <input
                type="checkbox"
                checked={confirmed}
                onChange={(event) => setConfirmed(event.target.checked)}
              />
              <span>Confirmo que desejo substituir os preços atuais no portfolio.json.</span>
            </label>
          </div>
          <Button variant="primary" onClick={applyConfirm} disabled={busy || !confirmed}>
            Salvar preços atualizados
          </Button>
        </>
      )}
      {message && <div className="success-box">{message}</div>}
    </Card>
  );
}

function HistoryFlow() {
  const [positions, setPositions] = useState<MarketPosition[] | null>(null);
  const [selectedIndex, setSelectedIndex] = useState("");
  const [points, setPoints] = useState<HistoryPoint[] | null>(null);
  const [reason, setReason] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    getJson<MarketPosition[]>("/api/market/positions")
      .then(setPositions)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)));
  }, []);

  const load = useCallback(() => {
    if (!selectedIndex) {
      setPoints(null);
      setReason(null);
      return;
    }
    setBusy(true);
    setPoints(null);
    setReason(null);
    getJson<{ symbol: string; points: HistoryPoint[]; unavailable_reason: string | null }>(
      `/api/market/history/${selectedIndex}`,
    )
      .then((data) => {
        // O endpoint emite 404/400 via ApiError; aqui só chegamos em caso de sucesso.
        if (data.unavailable_reason) {
          setReason(data.unavailable_reason);
        } else {
          setPoints(data.points);
        }
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)))
      .finally(() => setBusy(false));
  }, [selectedIndex]);
  useEffect(load, [load]);

  const variation = (() => {
    if (!points || points.length < 2) return null;
    const first = parseFloat(points[0].close);
    const last = parseFloat(points[points.length - 1].close);
    if (!Number.isFinite(first) || first <= 0) return null;
    return last / first - 1;
  })();

  return (
    <Card title="Histórico diário do ativo">
      {error && <ErrorBox message={error} />}
      {reason && <ErrorBox message={reason} />}
      <div className="field-row">
        <Field label="Ativo para histórico">
          <SelectInput
            value={selectedIndex}
            onChange={setSelectedIndex}
            options={[
              { value: "", label: "Selecione…" },
              ...(positions ?? []).map((item) => ({ value: String(item.index), label: `${item.name} — ${item.symbol}` })),
            ]}
          />
        </Field>
      </div>
      {busy && <Loading label="Consultando histórico…" />}
      {variation !== null && (
        <p>
          Variação no histórico retornado: <strong>{(variation * 100).toFixed(2)}%</strong>
        </p>
      )}
      {points && points.length > 0 && (
        <Table head={["Data", "Fechamento"]} empty={false}>
          {points.slice(-10).reverse().map((point) => (
            <tr key={point.date}>
              <td>{point.date}</td>
              <td>{parseFloat(point.close).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
            </tr>
          ))}
        </Table>
      )}
    </Card>
  );
}

function ManualRegisterCard() {
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function register() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const result = await sendJson<{ message: string }>("/api/history/snapshot", "POST", null);
      setMessage(result.message);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <label className="field-label">Sem consulta à API</label>
      <p className="muted">Registra os valores atuais conhecidos no histórico local.</p>
      <Button onClick={register} disabled={busy}>Registrar snapshot atual</Button>
      {message && <div className="success-box">{message}</div>}
      {error && <ErrorBox message={error} />}
    </Card>
  );
}
