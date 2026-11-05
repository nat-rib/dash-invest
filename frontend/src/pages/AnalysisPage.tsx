import { useEffect, useMemo, useState } from "react";
import {
  Card, EmptyState, ErrorBox, Loading, SelectInput, Table, Tabs,
} from "../components/ui";
import { getJson } from "../services/api";

const BASE = "/api";

interface AllocationSlice {
  name: string;
  value: string;
  share: string | null;
  positions: number;
}

interface Allocation {
  total_brl: string;
  known_positions: number;
  unknown_positions: number;
  by_class: AllocationSlice[];
  by_institution: AllocationSlice[];
}

interface ConcentrationItem {
  index: number;
  name: string;
  institution: string;
  asset_class: string;
  consolidated_brl: string | null;
  share: string | null;
}

interface Concentration {
  total_brl: string;
  top: ConcentrationItem[];
  comparable: {
    index: number;
    name: string;
    institution: string;
    cost_total: string;
    current_value: string;
    currency: string;
  }[];
}

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
  asset_class: string;
  ticker: string | null;
  currency: string;
  quantity: string | null;
  average_cost: string | null;
  operation_cost: string | null;
  current_price: string | null;
  current_value: string | null;
  cost_total: string | null;
  gain_loss: string | null;
  unrealized_return: string | null;
  converted_value_brl: string | null;
  conversion_rate_to_brl: string | null;
  conversion_date: string | null;
  consolidated_brl: string | null;
  indexer: string | null;
  maturity_date: string | null;
  application_date: string | null;
  issuer: string | null;
  annual_rate: string | null;
  invested_amount: string | null;
  dividends_received: string | null;
  risk_category: string | null;
  liquidity_profile: string | null;
  notes: string | null;
}

const TABS = [
  { id: "allocation", label: "Distribuição e concentração" },
  { id: "details", label: "Detalhes do ativo" },
];

export default function AnalysisPage() {
  const [tab, setTab] = useState("allocation");
  return (
    <div className="page">
      <header className="page-header">
        <h1>Análise da carteira</h1>
        <p className="muted">
          Um único snapshot descreve a carteira atual; não permite reconstruir desempenho histórico, TWR ou XIRR.
        </p>
      </header>
      <Tabs tabs={TABS} active={tab} onChange={setTab} />
      {tab === "allocation" ? <AllocationTab /> : <DetailsTab />}
    </div>
  );
}

function money(value: string | null): string {
  if (value === null) return "—";
  const parsed = parseFloat(value);
  if (!Number.isFinite(parsed)) return value;
  return parsed.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function percent(value: string | null): string {
  if (value === null) return "—";
  const parsed = parseFloat(value);
  if (!Number.isFinite(parsed)) return value;
  return `${(parsed * 100).toFixed(2)}%`;
}

function AllocationTab() {
  const [allocation, setAllocation] = useState<Allocation | null>(null);
  const [concentration, setConcentration] = useState<Concentration | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      getJson<Allocation>(`${BASE}/analysis/allocation`),
      getJson<Concentration>(`${BASE}/analysis/concentration`),
    ])
      .then(([alloc, conc]) => {
        setAllocation(alloc);
        setConcentration(conc);
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : String(err));
      });
  }, []);

  if (error) {
    return <Card><ErrorBox message={error} /></Card>;
  }
  if (!allocation || !concentration) {
    return <Card><Loading /></Card>;
  }

  return (
    <>
      <Card title="Total consolidado conhecido em BRL">
        <div className="metric-line">
          <strong>{money(allocation.total_brl)}</strong>
          <span className="muted">
            {" "}· {allocation.known_positions} posições com valor conhecido ·{" "}
            {allocation.unknown_positions} sem valor consolidado (não convertidas em zero)
          </span>
        </div>
        <div className="split-two">
          <div>
            <h3>Distribuição por classe</h3>
            <BarList slices={allocation.by_class} />
          </div>
          <div>
            <h3>Distribuição por instituição</h3>
            <BarList slices={allocation.by_institution} />
          </div>
        </div>
      </Card>
      <Card title="Maiores posições">
        {concentration.top.length === 0 ? (
          <EmptyState title="Nenhuma posição com valor consolidado conhecido." />
        ) : (
          <Table head={["Ativo", "Instituição", "Classe", "Valor BRL", "Concentração"]} empty={false}>
            {concentration.top.map((item) => (
              <tr key={item.index}>
                <td>{item.name}</td>
                <td>{item.institution}</td>
                <td>{item.asset_class}</td>
                <td>{money(item.consolidated_brl)}</td>
                <td>{percent(item.share)}</td>
              </tr>
            ))}
          </Table>
        )}
        <h3>Custo de aquisição × valor atual</h3>
        {concentration.comparable.length === 0 && (
          <p className="muted">Não há posições com custo e valor atual comparáveis.</p>
        )}
        <Table head={["Ativo", "Instituição", "Custo total", "Valor atual", "Moeda"]} empty={concentration.comparable.length === 0}>
          {concentration.comparable.map((item) => (
            <tr key={item.index}>
              <td>{item.name}</td>
              <td>{item.institution}</td>
              <td>{money(item.cost_total)}</td>
              <td>{money(item.current_value)}</td>
              <td>{item.currency}</td>
            </tr>
          ))}
        </Table>
      </Card>
    </>
  );
}

function BarList({ slices }: { slices: AllocationSlice[] }) {
  if (slices.length === 0) {
    return <EmptyState title="Sem posições com valor conhecido em BRL." />;
  }
  return (
    <div className="bar-list">
      {slices.map((slice) => {
        const share = slice.share === null ? 0 : Math.max(parseFloat(slice.share), 0.01);
        return (
          <div className="bar-row" key={slice.name}>
            <span className="bar-name">{slice.name} · {money(slice.value)} ({percent(slice.share)})</span>
            <div className="bar-track">
              <div className="bar-fill" style={{ width: `${Math.min(share * 100, 100)}%` }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

function DetailsTab() {
  const [positions, setPositions] = useState<PositionSummary[] | null>(null);
  const [selectedIndex, setSelectedIndex] = useState<string>("");
  const [detail, setDetail] = useState<PositionDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getJson<{ snapshot_date: string; positions: PositionSummary[] }>(`${BASE}/portfolio/positions`)
      .then((data) => setPositions(data.positions))
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)));
  }, []);

  const options = useMemo(() => {
    const list = positions ?? [];
    return [
      { value: "", label: "Selecione o ativo…" },
      ...list.map((item) => ({ value: String(item.index), label: `${item.name} — ${item.institution}` })),
    ];
  }, [positions]);

  useEffect(() => {
    if (!selectedIndex) {
      setDetail(null);
      return;
    }
    setDetail(null);
    setError(null);
    getJson<PositionDetail>(`${BASE}/portfolio/positions/${selectedIndex}`)
      .then(setDetail)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)));
  }, [selectedIndex]);

  return (
    <Card title="Detalhes do ativo">
      {error && <ErrorBox message={error} />}
      <div className="field-row">
        <div className="field">
          <span className="field-label">Ativo</span>
          <SelectInput value={selectedIndex} onChange={setSelectedIndex} options={options} />
        </div>
      </div>
      {!positions && !error && <Loading />}
      {positions && positions.length === 0 && (
        <EmptyState title="Nenhuma posição no snapshot." hint="Importe uma carteira primeiro." />
      )}
      {detail && (
        <>
          <div className="detail-metrics">
            <Metric label="Valor atual" value={money(detail.current_value)} />
            <Metric label="Ganho/perda" value={money(detail.gain_loss)} />
            <Metric label="Rentabilidade não realizada" value={percent(detail.unrealized_return)} />
            <Metric label="Convertido BRL" value={detail.converted_value_brl === null ? "" : money(detail.converted_value_brl)} />
          </div>
          <Table head={["Campo", "Valor"]} empty={false}>
            <DetailRow label="Instituição" value={detail.institution} />
            <DetailRow label="Classe" value={detail.asset_class} />
            <DetailRow label="Ticker" value={detail.ticker} />
            <DetailRow label="Moeda" value={detail.currency} />
            <DetailRow label="Quantidade" value={detail.quantity} />
            <DetailRow label="Preço médio" value={money(detail.average_cost)} />
            <DetailRow label="Custo da operação" value={money(detail.operation_cost)} />
            <DetailRow label="Preço atual" value={money(detail.current_price)} />
            <DetailRow label="Custo total" value={money(detail.cost_total)} />
            <DetailRow label="Indexador" value={detail.indexer} />
            <DetailRow label="Vencimento" value={detail.maturity_date} />
            <DetailRow label="Data de aplicação" value={detail.application_date} />
            <DetailRow label="Avaliação (data-base)" value={detail.conversion_date} />
            <DetailRow label="Emissor" value={detail.issuer} />
            <DetailRow label="Taxa anual" value={detail.annual_rate} />
            <DetailRow label="Valor aplicado informado" value={money(detail.invested_amount)} />
            <DetailRow label="Proventos recebidos" value={money(detail.dividends_received)} />
            <DetailRow label="Categoria de risco" value={detail.risk_category} />
            <DetailRow label="Liquidez" value={detail.liquidity_profile} />
            <DetailRow label="Observações" value={detail.notes} />
          </Table>
          <p className="muted">
            Campos ausentes aparecem explicitamente como “não informado”; não são convertidos em zero.
          </p>
        </>
      )}
    </Card>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric-box">
      <span className="metric-label">{label}</span>
      <span className="metric-value">{value.trim() === "" ? "—" : value}</span>
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: string | null }) {
  return (
    <tr>
      <td>{label}</td>
      <td>{value === null || value === undefined ? "não informado" : value}</td>
    </tr>
  );
}
