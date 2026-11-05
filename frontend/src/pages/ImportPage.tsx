import { useState } from "react";
import { Button, Card, ErrorBox, Loading, Table } from "../components/ui";
import { confirmImportSnapshot, previewImportSnapshot } from "../services/ledger";
import type { ImportPreview } from "../services/ledger";

export default function ImportPage() {
  return (
    <div className="page">
      <header className="page-header">
        <h1>Importar carteira</h1>
        <p className="muted">
          A importação substitui o snapshot inteiro. O arquivo é tratado exclusivamente como dados JSON.
        </p>
      </header>
      <ImportFlow />
    </div>
  );
}

function ImportFlow() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onChange(selected: File | null) {
    setFile(selected);
    setPreview(null);
    setConfirmed(false);
    setError(null);
    setMessage(null);
    if (!selected) return;
    setBusy(true);
    try {
      setPreview(await previewImportSnapshot(selected));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function replaceSnapshot() {
    if (!file || !confirmed) return;
    setBusy(true);
    setError(null);
    try {
      const result = await confirmImportSnapshot(file);
      setMessage(result.message);
      setPreview(null);
      setFile(null);
      setConfirmed(false);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <Card subtitle="Nenhum dado sai do arquivo local. Valide antes e confirme explicitamente a substituição.">
        <div className="field-row">
          <FieldWrapper>
            <input
              type="file"
              accept=".json,application/json"
              disabled={busy}
              onChange={(event) => void onChange(event.target.files?.[0] ?? null)}
            />
          </FieldWrapper>
          {busy && !preview && <Loading />}
        </div>
        {error && <ErrorBox message={error} />}
        {message && <div className="success-box">{message}</div>}
      </Card>
      {preview && (
        <Card title={preview.valid ? "Prévia — confira antes de substituir" : "Arquivo inválido"}>
          {!preview.valid && (
            <>
              <ErrorBox message={preview.message}>
                <ul>
                  {preview.validation_errors.map((item) => <li key={item}>{item}</li>)}
                </ul>
              </ErrorBox>
              <p className="muted">O snapshot atual foi preservado. Corrija o JSON e tente novamente.</p>
            </>
          )}
          {preview.valid && (
            <>
              <div className="success-box">
                {preview.message} · data-base {formatDate(preview.snapshot_date)} · moeda {preview.currency}
              </div>
              {preview.duplicates.length > 0 && (
                <ErrorBox
                  message={
                    "Possíveis posições duplicadas: " +
                    preview.duplicates.map((item) => item.join(" / ")).join("; ")
                  }
                />
              )}
              <Table
                head={["Instituição", "Ativo", "Classe", "Quantidade", "Moeda"]}
                empty={preview.positions.length === 0}
              >
                {preview.positions.map((position, index) => (
                  <tr key={`${position.institution}-${position.name}-${index}`}>
                    <td>{position.institution}</td>
                    <td>{position.ticker ?? position.name}</td>
                    <td>{position.asset_class}</td>
                    <td>{position.quantity ?? "—"}</td>
                    <td>{position.currency}</td>
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
                  <span>Confirmo que desejo substituir a carteira exibida atualmente.</span>
                </label>
              </div>
              <Button variant="primary" onClick={replaceSnapshot} disabled={busy || !confirmed}>
                Substituir carteira
              </Button>
            </>
          )}
        </Card>
      )}
    </>
  );
}

function FieldWrapper({ children }: { children: React.ReactNode }) {
  return (
    <label className="field">
      <span className="field-label">Arquivo portfolio.json</span>
      {children}
    </label>
  );
}

function formatDate(value: string): string {
  const [year, month, day] = value.split("-");
  return `${day}/${month}/${year}`;
}
