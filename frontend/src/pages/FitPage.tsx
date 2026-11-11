import { useEffect, useState } from "react";

import { AllocationBars, MetricCard } from "../components/insights";
import { Card, ErrorBox, Loading, Table } from "../components/ui";
import type { PortfolioFit } from "../services/fit";
import { fetchFit } from "../services/fit";

export default function FitPage() {
  const [fit, setFit] = useState<PortfolioFit | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchFit()
      .then(setFit)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)));
  }, []);

  return (
    <div className="page">
      <header className="page-header">
        <h1>Portfolio Fit</h1>
        <p className="muted">
          Exposição por classe, instituição e moeda, concentração e cobertura de dados. Atributos
          ausentes permanecem explícitos — nada é inferido.
        </p>
      </header>
      <ErrorBoxRender error={error} />
      {!fit && !error && <Loading />}
      {fit && (
        <>
          <Card title="Resumo">
            <div className="metric-grid">
              <MetricCard label="Patrimônio em BRL" value={money(fit.total_brl)} hint={`${fit.positions} posições`} />
              <MetricCard
                label="Concentração (HHI)"
                value={fit.herfindahl === null ? "—" : fit.herfindahl.toFixed(3)}
                hint={hhiLabel(fit.herfindahl)}
                tone={fit.herfindahl !== null && fit.herfindahl > 0.25 ? "warn" : undefined}
              />
              <MetricCard
                label="Cobertura de liquidez"
                value={percent(fit.liquidity_coverage)}
                hint="Fração do valor com liquidez informada"
              />
              <MetricCard
                label="Cobertura de crédito"
                value={percent(fit.credit_coverage)}
                hint="Fração do valor com categoria de risco"
              />
            </div>
          </Card>

          <Card title="Exposição por classe">
            <AllocationBars slices={toSlices(fit.by_class)} />
          </Card>
          <Card title="Exposição por instituição">
            <AllocationBars slices={toSlices(fit.by_institution)} />
          </Card>
          <Card title="Exposição por moeda">
            <AllocationBars slices={toSlices(fit.by_currency)} />
          </Card>

          <Card title="Maiores posições">
            <Table head={["Ativo", "Instituição", "Classe", "Valor", "Fatia", "Liquidez", "Risco"]}>
              {fit.top_positions.map((item) => (
                <tr key={`${item.institution}-${item.name}`}>
                  <td>{item.name}</td>
                  <td>{item.institution}</td>
                  <td>{item.asset_class}</td>
                  <td>{money(item.value_brl)}</td>
                  <td>{percent(item.share)}</td>
                  <td>{item.liquidity ?? "—"}</td>
                  <td>{item.risk_category ?? "—"}</td>
                </tr>
              ))}
            </Table>
          </Card>

          <Card
            title="Correlação entre posições"
            subtitle="Requer ao menos 20 retornos diários alinhados para cada par."
          >
            {fit.correlations.length === 0 ? (
              <p className="muted">Sem pares com série de preços suficiente.</p>
            ) : (
              <Table head={["Posição A", "Posição B", "Correlação", "Observações"]}>
                {fit.correlations.map((pair) => (
                  <tr key={`${pair.left}-${pair.right}`}>
                    <td>{pair.left}</td>
                    <td>{pair.right}</td>
                    <td>{pair.correlation.toFixed(2)}</td>
                    <td>{pair.observations}</td>
                  </tr>
                ))}
              </Table>
            )}
          </Card>

          {fit.unavailable.length > 0 && (
            <div className="warning-box">
              <strong>Limitações explícitas</strong>
              <ul>
                {fit.unavailable.map((item) => (
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

function toSlices(slices: PortfolioFit["by_class"]) {
  return slices.map((slice) => ({
    name: slice.name,
    value: String(slice.value),
    share: String(slice.share),
  }));
}

function hhiLabel(value: number | null): string {
  if (value === null) return "indisponível";
  if (value <= 0.15) return "baixa";
  if (value <= 0.25) return "moderada";
  return "alta";
}

function money(value: number): string {
  return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
}

function percent(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "—";
  return `${(value * 100).toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`;
}

function ErrorBoxRender({ error }: { error: string | null }) {
  if (!error) return null;
  return <ErrorBox message={error} />;
}
