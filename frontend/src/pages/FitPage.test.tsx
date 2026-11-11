import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../services/api", () => ({ getJson: vi.fn() }));

import { getJson } from "../services/api";
import FitPage from "./FitPage";

const fit = {
  total_brl: 4500,
  positions: 3,
  by_class: [
    { name: "acao", value: 3000, share: 3000 / 4500, positions: 1 },
    { name: "fii", value: 1000, share: 1000 / 4500, positions: 1 },
    { name: "renda_fixa", value: 500, share: 500 / 4500, positions: 1 },
  ],
  by_institution: [{ name: "XP", value: 4000, share: 4000 / 4500, positions: 2 }],
  by_currency: [{ name: "BRL", value: 4500, share: 1, positions: 3 }],
  top_positions: [
    {
      name: "Petrobras PN",
      institution: "XP",
      asset_class: "acao",
      currency: "BRL",
      value_brl: 3000,
      share: 3000 / 4500,
      liquidity: null,
      risk_category: null,
    },
  ],
  herfindahl: 0.506,
  liquidity_coverage: 500 / 4500,
  credit_coverage: 500 / 4500,
  correlations: [
    { left: "Petrobras PN", right: "CSHG Logística", correlation: 1, observations: 40 },
  ],
  unavailable: ["Look-through de ETFs indisponível: composição não foi importada."],
};

describe("FitPage", () => {
  beforeEach(() => {
    vi.mocked(getJson).mockReset();
  });

  it("mostra exposições, concentração e correlações", async () => {
    vi.mocked(getJson).mockResolvedValue(fit as never);
    render(<FitPage />);

    expect(await screen.findByText("Portfolio Fit")).toBeTruthy();
    expect(screen.getByText(/0\.506/)).toBeTruthy();
    expect(screen.getAllByText("Petrobras PN").length).toBeGreaterThan(0);
    expect(screen.getByText("1.00")).toBeTruthy();
    expect(screen.getByText(/Look-through de ETFs/)).toBeTruthy();
  });

  it("mostra erro da API", async () => {
    vi.mocked(getJson).mockRejectedValue(new Error("Importe uma carteira primeiro."));
    render(<FitPage />);

    expect(await screen.findByRole("alert")).toBeTruthy();
  });
});
