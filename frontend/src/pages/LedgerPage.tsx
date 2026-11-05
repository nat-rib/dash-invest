import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Badge, Button, Card, EmptyState, ErrorBox, Field, Loading, SelectInput,
  Table, Tabs, TextInput,
} from "../components/ui";
import {
  confirmTransfer, createInstrument, fetchInstruments, fetchTransferSuggestions,
  importCsv, importSnapshot, previewCsv, previewSnapshot,
} from "../services/ledger";
import { parseCsv } from "../utils/csv";
import type {
  CsvMapping, Instrument, SnapshotPreview, TransferEvent, TransferSuggestions,
} from "../types";

const TABS = [
  { id: "migration", label: "Migrar carteira JSON" },
  { id: "csv", label: "Importar extrato CSV" },
  { id: "transfers", label: "Conciliar transferências" },
];

const CURRENCIES = ["BRL", "USD", "EUR", "GBP", "JPY"];
const ASSET_CLASSES = [
  { value: "equity", label: "Ações" },
  { value: "reit", label: "REIT" },
  { value: "fii", label: "FII" },
  { value: "etf", label: "ETF" },
  { value: "mutual_fund", label: "Fundos" },
  { value: "fixed_income", label: "Renda fixa" },
  { value: "crypto", label: "Cripto" },
  { value: "cash", label: "Caixa" },
  { value: "other", label: "Outros" },
];

const CANONICAL_COLUMNS: { field: string; label: string; required?: boolean }[] = [
  { field: "external_id", label: "ID externo (opcional)" },
  { field: "occurred_at", label: "Data da operação", required: true },
  { field: "transaction_type", label: "Tipo da operação", required: true },
  { field: "instrument_id", label: "Ticker/código do ativo" },
  { field: "quantity", label: "Quantidade" },
  { field: "unit_price", label: "Preço unitário" },
  { field: "amount", label: "Valor bruto/transferência" },
  { field: "fees", label: "Taxas" },
  { field: "taxes", label: "Impostos" },
  { field: "currency", label: "Moeda por linha (opcional)" },
  { field: "sequence", label: "Sequência (opcional)" },
  { field: "transfer_id", label: "ID da transferência (opcional)" },
  { field: "notes", label: "Observações (opcional)" },
];

export default function LedgerPage() {
  const [tab, setTab] = useState("migration");
  return (
    <div className="page">
      <header className="page-header">
        <h1>Ledger e operações</h1>
        <p className="muted">
          Importação controlada, histórico auditável e conciliação explícita de transferências.
        </p>
      </header>
      <Tabs tabs={TABS} active={tab} onChange={setTab} />
      {tab === "migration" && <MigrationTab />}
      {tab === "csv" && <CsvTab />}
      {tab === "transfers" && <TransfersTab />}
    </div>
  );
}

function MigrationTab() {
  const [preview, setPreview] = useState<SnapshotPreview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<string | null>(null);

  const loadPreview = useCallback(() => {
    setBusy(true);
    setError(null);
    setDone(null);
    previewSnapshot()
      .then((result) => {
        setPreview(result);
        setBusy(false);
      })
      .catch((err: unknown) => {
        setPreview(null);
        setError(err instanceof Error ? err.message : String(err));
        setBusy(false);
      });
  }, []);

  useEffect(loadPreview, [loadPreview]);

  async function migrate() {
    setBusy(true);
    setError(null);
    try {
      const result = await importSnapshot();
      setDone(
        `Migração concluída: ${result.instruments_saved} instrumentos e ` +
        `${result.positions_saved} posições. Transações criadas: 0.`,
      );
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card
      subtitle="A migração cria/atualiza cadastro de ativos e posições de referência. Não cria transações fictícias e não apaga nem substitui o portfolio.json."
    >
      {error && <ErrorBox message={error} />}
      {busy && !preview && <Loading />}
      {preview && (
        <>
          <p className="good">
            Snapshot válido: {preview.positions.length} posições,{" "}
            data-base {formatDate(preview.snapshot_date)} · moeda {preview.currency}.
          </p>
          <Table head={["Instituição", "Ativo", "Classe", "Quantidade", "Moeda"]} empty={false}>
            {preview.positions.map((position) => (
              <tr key={`${position.institution}-${position.ticker ?? position.name}`}>
                <td>{position.institution}</td>
                <td>{position.ticker ?? position.name}</td>
                <td>{position.asset_class}</td>
                <td>{position.quantity ?? "—"}</td>
                <td>{position.currency}</td>
              </tr>
            ))}
          </Table>
          <Button variant="primary" onClick={migrate} disabled={busy}>
            {busy ? <Loading /> : "Migrar snapshot para SQLite"}
          </Button>
          <Button onClick={loadPreview} disabled={busy}>Recarregar prévia</Button>
        </>
      )}
      {done && <div className="success-box">{done} O JSON original foi preservado.</div>}
      {!preview && !busy && !error && (
        <EmptyState
          title="Nenhum snapshot para migrar"
          hint="Configure PORTFOLIO_PATH apontando para o portfolio.json legado."
        />
      )}
    </Card>
  );
}

function instrumentLabel(item: Instrument): string {
  const ticker = Object.values(item.provider_symbols)[0];
  return `${item.name} · ${item.asset_class} · ${item.currency}${ticker ? ` · ${ticker}` : ""}`;
}

function CsvTab() {
  const [instruments, setInstruments] = useState<Instrument[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [rows, setRows] = useState<string[][]>([]);
  const [delimiter, setDelimiter] = useState(";");
  const [institution, setInstitution] = useState("");
  const [currency, setCurrency] = useState("BRL");
  const [decimalLocale, setDecimalLocale] = useState("pt_BR");
  const [dateFormat, setDateFormat] = useState("%d/%m/%Y");
  const [timezoneName, setTimezoneName] = useState("America/Sao_Paulo");
  const [columns, setColumns] = useState<Record<string, string>>({});
  const [instrumentMap, setInstrumentMap] = useState<Record<string, string>>({});
  const [previewData, setPreviewData] = useState<Awaited<ReturnType<typeof previewCsv>> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [newInstrument, setNewInstrument] = useState({ ticker: "", name: "", asset_class: "equity", currency: "BRL", exchange: "" });

  const headers = rows[0] ?? [];

  const loadInstruments = useCallback(() => {
    fetchInstruments().then(setInstruments).catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)));
  }, []);
  useEffect(loadInstruments, [loadInstruments]);

  async function onFileChange(selected: File | null, activeDelimiter: string = delimiter) {
    setFile(selected);
    setPreviewData(null);
    setMessage(null);
    setInstrumentMap({});
    if (!selected) {
      setRows([]);
      return;
    }
    try {
      const text = await selected.text();
      const parsed = parseCsv(text, activeDelimiter === "TAB" ? "\t" : activeDelimiter);
      setRows(parsed);
      // Mapeamento inicial: tenta casar nome de coluna canônico com o cabeçalho.
      const guessed: Record<string, string> = {};
      for (const field of CANONICAL_COLUMNS) {
        const match = parsed[0]?.find(
          (header) => header.trim().toLowerCase() === field.field.toLowerCase(),
        );
        if (match) guessed[field.field] = match;
      }
      setColumns(guessed);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  const mapping: CsvMapping = useMemo(() => ({
    institution, currency, delimiter: delimiter === "TAB" ? "\t" : delimiter,
    columns: columnsClearEmpties(columns),
    instrument_map: instrumentMap,
    decimal_locale: decimalLocale,
    date_format: dateFormat,
    timezone_name: timezoneName,
  }), [institution, currency, delimiter, columns, instrumentMap, decimalLocale, dateFormat, timezoneName]);

  const assetColumn = columns["instrument_id"];
  const assetValues = useMemo(() => {
    if (!assetColumn || headers.length === 0) return [];
    const columnIndex = headers.indexOf(assetColumn);
    if (columnIndex < 0) return [];
    const values = new Set<string>();
    for (const row of rows.slice(1)) {
      const value = (row[columnIndex] ?? "").trim();
      if (value) values.add(value);
    }
    return [...values].sort();
  }, [assetColumn, headers, rows]);

  function invalidatePreview() {
    setPreviewData(null);
    setMessage(null);
  }

  // Preenche automaticamente associações quando o ticker já existe no catálogo;
  // só sugere, nunca importa sem a prévia e a confirmação explícita do usuário.
  useEffect(() => {
    if (!assetColumn || instruments.length === 0) return;
    setInstrumentMap((current) => {
      const next = { ...current };
      let changed = false;
      for (const value of assetValues) {
        if (next[value]) continue;
        const match = instruments.find(
          (item) => Object.values(item.provider_symbols).some(
            (symbol) => symbol.toLowerCase() === value.toLowerCase(),
          ),
        );
        if (match) {
          next[value] = match.id;
          changed = true;
        }
      }
      return changed ? next : current;
    });
  }, [assetColumn, assetValues, instruments]);

  async function runPreview() {
    if (!file) return;
    setBusy(true);
    setError(null);
    invalidatePreview();
    try {
      const data = await previewCsv(file, mapping);
      setPreviewData(data);
      setMessage(`${data.parsed} operações prontas para importar. Confira abaixo antes de confirmar.`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function confirmImport() {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const result = await importCsv(file, mapping);
      setMessage(result.message);
      setPreviewData(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function registerInstrument() {
    setBusy(true);
    setError(null);
    try {
      await createInstrument({
        name: newInstrument.name,
        asset_class: newInstrument.asset_class,
        currency: newInstrument.currency,
        exchange: newInstrument.exchange || null,
        ticker: newInstrument.ticker,
      });
      setNewInstrument({ ticker: "", name: "", asset_class: "equity", currency: "BRL", exchange: "" });
      loadInstruments();
      setMessage("Instrumento cadastrado. Associe-o ao extrato no mapeamento.");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  const canPreview = Boolean(file && institution.trim() && columns["occurred_at"] && columns["transaction_type"]);

  return (
    <>
      <Card
        title="Adaptar extrato CSV da instituição"
        subtitle="Cada corretora tem seu próprio layout: selecione as colunas do arquivo. O adaptador normaliza datas, decimais e tipos antes do importador canônico; a importação só acontece após a prévia e a confirmação."
      >
        <div className="field-row">
          <Field label="Arquivo CSV">
            <input
              type="file"
              accept=".csv,text/csv"
              onChange={(event) => void onFileChange(event.target.files?.[0] ?? null)}
            />
          </Field>
          <Field label="Separador">
            <SelectInput
              value={delimiter}
              onChange={(value) => { setDelimiter(value); if (file) void onFileChange(file, value); }}
              options={[
                { value: ";", label: "; (ponto e vírgula)" },
                { value: ",", label: ", (vírgula)" },
                { value: "TAB", label: "TAB" },
              ]}
            />
          </Field>
          <Field label="Instituição / corretora">
            <TextInput value={institution} onChange={(value) => { setInstitution(value); invalidatePreview(); }} />
          </Field>
          <Field label="Moeda padrão">
            <SelectInput value={currency} onChange={setCurrency} options={CURRENCIES.map((item) => ({ value: item, label: item }))} />
          </Field>
        </div>
        <div className="field-row">
          <Field label="Formato numérico">
            <SelectInput
              value={decimalLocale}
              onChange={setDecimalLocale}
              options={[
                { value: "pt_BR", label: "1.000,00 (pt-BR)" },
                { value: "en_US", label: "1,000.00 (en-US)" },
              ]}
            />
          </Field>
          <Field label="Formato da data quando não for ISO-8601">
            <TextInput value={dateFormat} onChange={setDateFormat} />
          </Field>
          <Field label="Timezone para datas sem fuso">
            <TextInput value={timezoneName} onChange={setTimezoneName} />
          </Field>
        </div>
        {file && rows.length > 0 && (
          <>
            <p className="muted">{rows.length - 1} linhas encontradas · cabeçalho: {headers.map((item) => item || "(vazia)").join(" | ")}</p>
            <Table head={headers.map((item, index) => item || `col${index + 1}`)} empty={rows.length <= 1}>
              {rows.slice(1, 11).map((row, rowIndex) => (
                <tr key={rowIndex}>{headers.map((_, colColumn) => <td key={colColumn}>{row[colColumn] ?? ""}</td>)}</tr>
              ))}
            </Table>
          </>
        )}
      </Card>
      {file && (
        <Card title="Mapeamento de colunas">
          <div className="field-grid">
            {CANONICAL_COLUMNS.map((column) => (
              <Field key={column.field} label={column.label} hint={column.required ? "obrigatória" : undefined}>
                <SelectInput
                  value={columns[column.field] ?? ""}
                  onChange={(value) => { setColumns({ ...columns, [column.field]: value }); invalidatePreview(); }}
                  options={[{ value: "", label: "(não mapear)" }, ...headers.map((item) => ({ value: item, label: item }))]}
                />
              </Field>
            ))}
          </div>
          {assetColumn && (
            <Card title={`Associar ativos da coluna ${assetColumn}`}>
              {assetValues.length === 0 && <EmptyState title="Nenhum ativo identificado na coluna." />}
              {assetValues.map((value) => {
                const mapped = instruments.find(
                  (item) => Object.values(item.provider_symbols).some(
                    (symbol) => symbol.toLowerCase() === value.toLowerCase(),
                  ),
                );
                return (
                  <div className="field-row" key={value}>
                    <Field label={`Ticker do extrato: ${value}`}>
                      <SelectInput
                        value={instrumentMap[value] ?? mapped?.id ?? ""}
                        onChange={(selected) => { setInstrumentMap({ ...instrumentMap, [value]: selected }); invalidatePreview(); }}
                        options={[
                          { value: "", label: "(não associado)" },
                          ...instruments.map((item) => ({ value: item.id, label: instrumentLabel(item) })),
                        ]}
                      />
                    </Field>
                    {mapped && <Badge tone="good">associação sugerida</Badge>}
                  </div>
                );
              })}
            </Card>
          )}
          <Card title="Cadastrar instrumento que ainda não existe no catálogo">
            <div className="field-row">
              <Field label="Ticker / código externo">
                <TextInput value={newInstrument.ticker} onChange={(value) => setNewInstrument({ ...newInstrument, ticker: value })} />
              </Field>
              <Field label="Nome do ativo">
                <TextInput value={newInstrument.name} onChange={(value) => setNewInstrument({ ...newInstrument, name: value })} />
              </Field>
              <Field label="Classe do ativo">
                <SelectInput value={newInstrument.asset_class} onChange={(value) => setNewInstrument({ ...newInstrument, asset_class: value })} options={ASSET_CLASSES} />
              </Field>
              <Field label="Moeda do ativo">
                <SelectInput value={newInstrument.currency} onChange={(value) => setNewInstrument({ ...newInstrument, currency: value })} options={CURRENCIES.map((item) => ({ value: item, label: item }))} />
              </Field>
              <Field label="Bolsa / mercado (opcional)">
                <TextInput value={newInstrument.exchange} onChange={(value) => setNewInstrument({ ...newInstrument, exchange: value })} />
              </Field>
            </div>
            <Button onClick={registerInstrument} disabled={busy}>Cadastrar instrumento</Button>
          </Card>
          {error && <ErrorBox message={error} />}
          <div className="actions">
            <Button variant="primary" onClick={runPreview} disabled={busy || !canPreview}>
              Validar e gerar prévia
            </Button>
            <Button
              variant="primary"
              onClick={confirmImport}
              disabled={busy || !previewData || !canPreview}
            >
              Confirmar importação
            </Button>
          </div>
          {!canPreview && <p className="muted">Informe instituição e mapeie Data e Tipo da operação.</p>}
          {message && <div className="success-box">{message}</div>}
          {previewData && (
            <>
              <h3>Prévia das operações (ainda não persistidas)</h3>
              <Table head={["Linha", "Data", "Tipo", "Instituição", "Ativo", "Qtd", "Preço", "Valor", "Moeda"]} empty={false}>
                {previewData.transactions.map((item) => (
                  <tr key={item.row_number}>
                    <td>{item.row_number}</td>
                    <td>{item.occurred_at.slice(0, 10)}</td>
                    <td>{item.transaction_type}</td>
                    <td>{item.institution}</td>
                    <td>{item.instrument_id ?? "—"}</td>
                    <td>{item.quantity ?? "—"}</td>
                    <td>{item.unit_price ?? "—"}</td>
                    <td>{item.amount ?? "—"}</td>
                    <td>{item.currency}</td>
                  </tr>
                ))}
              </Table>
            </>
          )}
        </Card>
      )}
    </>
  );
}

function TransfersTab() {
  const [data, setData] = useState<TransferSuggestions | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [selectedOut, setSelectedOut] = useState("");
  const [selectedIn, setSelectedIn] = useState("");

  const load = useCallback(() => {
    setBusy(true);
    fetchTransferSuggestions()
      .then((result) => {
        setData(result);
        setError(null);
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)))
      .finally(() => setBusy(false));
  }, []);
  useEffect(load, [load]);

  async function confirm(outId: string, inId: string, source: "manual" | "manual_review") {
    setBusy(true);
    setError(null);
    try {
      await confirmTransfer(outId, inId, source);
      setMessage("Pareamento registrado sem alterar os eventos originais.");
      load();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  function eventLabel(event: TransferEvent): string {
    return `${event.institution} · ${formatDate(event.occurred_at)} · ${event.amount ?? "—"} ${event.currency} · ${event.id.slice(0, 8)}`;
  }

  return (
    <Card subtitle="Transferências entre instituições só são conciliadas com confirmação explícita; nunca automaticamente.">
      {error && <ErrorBox message={error} />}
      {message && <div className="success-box">{message}</div>}
      {busy && !data && <Loading />}
      {data && (
        <>
          <p>
            <Badge tone="info">{data.confirmed_links.length} transferências confirmadas manualmente</Badge>
            {data.ambiguous_transaction_ids.length > 0 && (
              <>
                {" "}
                <Badge tone="warn">
                  {data.ambiguous_transaction_ids.length} operações com mais de uma correspondência possível exigem revisão manual
                </Badge>
              </>
            )}
            {data.unmatched_transaction_ids.length > 0 && (
              <span className="muted"> · {data.unmatched_transaction_ids.length} transferências sem correspondência candidata</span>
            )}
          </p>
          {data.suggested_pairs.length > 0 ? (
            <>
              <h3>Sugestões com correspondência única</h3>
              <p className="muted">Confirme somente após conferir os dados do extrato.</p>
              {data.suggested_pairs.map((pair) => (
                <div className="pair-row" key={pair.transfer_out.id}>
                  <div>
                    <strong>Saída — {pair.transfer_out.institution}</strong>
                    <p className="muted">{formatDate(pair.transfer_out.occurred_at)} · {pair.transfer_out.amount} {pair.transfer_out.currency}</p>
                  </div>
                  <div>
                    <strong>Entrada — {pair.transfer_in.institution}</strong>
                    <p className="muted">{formatDate(pair.transfer_in.occurred_at)} · {pair.transfer_in.amount} {pair.transfer_in.currency}</p>
                  </div>
                  <Button onClick={() => confirm(pair.transfer_out.id, pair.transfer_in.id, "manual")} disabled={busy}>
                    Confirmar
                  </Button>
                </div>
              ))}
            </>
          ) : (
            <EmptyState title="Nenhum par único pendente foi encontrado." />
          )}
          <h3>Pareamento manual</h3>
          <p className="muted">
            Resolve casos ambíguos ou com diferenças explicáveis. A confirmação fica registrada separadamente e não modifica as transações.
          </p>
          {data.pending_out_events.length === 0 || data.pending_in_events.length === 0 ? (
            <p className="muted">Não há duas pontas pendentes disponíveis para pareamento manual.</p>
          ) : (
            <div className="field-row">
              <Field label="Transferência de saída">
                <SelectInput
                  value={selectedOut}
                  onChange={setSelectedOut}
                  options={[
                    { value: "", label: "Selecione…" },
                    ...data.pending_out_events.map((event) => ({ value: event.id, label: eventLabel(event) })),
                  ]}
                />
              </Field>
              <Field label="Transferência de entrada">
                <SelectInput
                  value={selectedIn}
                  onChange={setSelectedIn}
                  options={[
                    { value: "", label: "Selecione…" },
                    ...data.pending_in_events.map((event) => ({ value: event.id, label: eventLabel(event) })),
                  ]}
                />
              </Field>
              <Button
                variant="primary"
                disabled={busy || !selectedOut || !selectedIn || selectedOut === selectedIn}
                onClick={() => confirm(selectedOut, selectedIn, "manual_review")}
              >
                Confirmar pareamento manual
              </Button>
            </div>
          )}
          {data.confirmed_links.length > 0 && (
            <>
              <h3>Pareamentos confirmados</h3>
              <Table head={["Saída", "Entrada", "Confirmado em", "Origem"]} empty={false}>
                {data.confirmed_links.map((link) => (
                  <tr key={link.linked_at + link.transfer_out_id}>
                    <td className="mono">{link.transfer_out_id.slice(0, 8)}</td>
                    <td className="mono">{link.transfer_in_id.slice(0, 8)}</td>
                    <td>{link.linked_at.replace("T", " ").slice(0, 19)}</td>
                    <td>{link.confirmation_source}</td>
                  </tr>
                ))}
              </Table>
            </>
          )}
        </>
      )}
    </Card>
  );
}

function columnsClearEmpties(columns: Record<string, string>): Record<string, string> {
  const result: Record<string, string> = {};
  for (const [key, value] of Object.entries(columns)) {
    if (value) result[key] = value;
  }
  return result;
}

function formatDate(value: string): string {
  const [year, month, day] = value.slice(0, 10).split("-");
  return `${day}/${month}/${year}`;
}
