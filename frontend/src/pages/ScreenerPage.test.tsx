import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../services/api", () => ({ getJson: vi.fn(), sendJson: vi.fn() }));

import { getJson, sendJson } from "../services/api";
import ScreenerPage from "./ScreenerPage";

const rows = {
  items: [
    {
      cnpj: "00000000000191",
      name: "ALTA",
      reference_date: "2024-12-31",
      revenue: 1_000_000_000,
      net_income: 200_000_000,
      equity: 500_000_000,
      total_assets: 2_000_000_000,
      net_margin: 0.2,
      roe: 0.4,
      roa: 0.1,
      asset_turnover: 0.5,
    },
  ],
  total: 1,
};

const dcf = {
  present_value_explicit: 500_000_000,
  present_value_terminal: 975_000_000,
  enterprise_value: 1_475_000_000,
  projections: [{ year: 1, cash_flow: 110, present_value: 100 }],
};

describe("ScreenerPage", () => {
  beforeEach(() => {
    vi.mocked(getJson).mockReset();
    vi.mocked(sendJson).mockReset();
    vi.mocked(getJson).mockResolvedValue(rows as never);
    vi.mocked(sendJson).mockResolvedValue(dcf as never);
  });

  it("lista os emissores com indicadores", async () => {
    render(<ScreenerPage />);

    expect(await screen.findByText("ALTA")).toBeTruthy();
    expect(screen.getAllByText("40%").length).toBeGreaterThan(0);
    expect(screen.getAllByText("20%").length).toBeGreaterThan(0);
  });

  it("calcula DCF e mostra o valor presente", async () => {
    render(<ScreenerPage />);

    fireEvent.click(screen.getByRole("button", { name: "Calcular" }));

    expect(await screen.findByText("R$ 1,5 bi")).toBeTruthy();
    expect(screen.getByText("Fluxos explícitos")).toBeTruthy();
  });
});
