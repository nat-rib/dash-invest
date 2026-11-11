import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../services/api", () => ({ getJson: vi.fn() }));

import { getJson } from "../services/api";
import RiskPage from "./RiskPage";

const report = {
  observations: 40,
  returns: 39,
  start_date: "2024-01-01",
  end_date: "2024-02-09",
  total_return: 0.1,
  annualized_volatility: 0.2,
  max_drawdown: -0.05,
  sharpe: 1.2,
  sortino: 1.8,
  var_95: 0.02,
  cvar_95: 0.03,
  var_95_parametric: 0.025,
  cvar_95_parametric: 0.035,
  beta: null,
  correlation: null,
  monthly_returns: [{ month: "2024-01", return_value: 0.05 }],
  unavailable: [],
  reason: null,
};

function stub(reason: string | null = null) {
  vi.mocked(getJson).mockImplementation((url: string) => {
    if (url.startsWith("/api/data/series")) {
      return Promise.resolve({
        items: [
          { provider: "csv", instrument_id: "PETR4.SAO", metric: "close", observations: 40 },
        ],
      } as never);
    }
    if (url.startsWith("/api/risk/instrument")) {
      return Promise.resolve(
        (reason ? { ...report, reason, total_return: null } : report) as never,
      );
    }
    return Promise.resolve({ ...report, reason: "Sem histórico suficiente." } as never);
  });
}

describe("RiskPage", () => {
  beforeEach(() => {
    vi.mocked(getJson).mockReset();
  });

  it("mostra as métricas do ativo e da carteira", async () => {
    stub();
    render(<RiskPage />);

    expect(await screen.findByText("Volatilidade anualizada")).toBeTruthy();
    expect(screen.getAllByText("20%").length).toBeGreaterThan(0);
    expect(await screen.findByText("Sem histórico suficiente.")).toBeTruthy();
  });

  it("explica quando a série não tem amostra suficiente", async () => {
    stub("São necessários ao menos dois preços válidos.");
    render(<RiskPage />);

    expect(
      await screen.findByText("São necessários ao menos dois preços válidos."),
    ).toBeTruthy();
  });
});
