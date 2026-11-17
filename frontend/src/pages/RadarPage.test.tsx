import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../services/api", () => ({ getJson: vi.fn() }));

import { getJson } from "../services/api";
import RadarPage from "./RadarPage";

const candidates = {
  items: [
    {
      key: "fixed_income:tesouro-selic",
      name: "Tesouro Selic",
      asset_class: "renda_fixa",
      score: 82.4,
      confidence: 0.4,
      components: {
        allocation: 1,
        concentration: 1,
        fundamentals: null,
        valuation: null,
        momentum: null,
        signal: 0.9,
      },
      reasons: ["Renda fixa está 50.0 p.p. abaixo do alvo de 60%", "2 sinais"],
      missing: ["fundamentos", "valuation"],
      sources: ["InfoMoney"],
      signal_count: 2,
      last_seen: "2026-11-16T12:00:00Z",
    },
    {
      key: "ticker:PETR4",
      name: "Petrobras PN",
      asset_class: "acao",
      score: 45.1,
      confidence: 0.8,
      components: {
        allocation: 0,
        concentration: 0,
        fundamentals: 0.9,
        valuation: null,
        momentum: 0.6,
        signal: 0.8,
      },
      reasons: ["Ações já está no alvo"],
      missing: ["valuation"],
      sources: ["Exame"],
      signal_count: 1,
      last_seen: "2026-11-16T11:00:00Z",
    },
  ],
  total: 2,
};

describe("RadarPage", () => {
  beforeEach(() => {
    vi.mocked(getJson).mockReset();
    vi.mocked(getJson).mockResolvedValue(candidates as never);
  });

  it("lista os ativos ordenados e abre detalhes", async () => {
    render(<RadarPage />);

    expect((await screen.findAllByText("Tesouro Selic")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("82").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/abaixo do alvo/).length).toBeGreaterThan(0);
    expect(screen.getByText("2 de 2 ativos exibidos.")).toBeTruthy();

    fireEvent.click(screen.getAllByRole("button", { name: "Detalhes" })[0]);

    expect(screen.getByText("Componentes")).toBeTruthy();
    expect(screen.getAllByText(/Lacuna de alocação/).length).toBeGreaterThan(0);
    expect(screen.getByText(/Sem dados: fundamentos/)).toBeTruthy();
  });

  it("filtra por score mínimo", async () => {
    render(<RadarPage />);
    await screen.findAllByText("Tesouro Selic");

    fireEvent.change(screen.getByPlaceholderText("0"), { target: { value: "80" } });

    await waitFor(() => expect(screen.queryByText("Petrobras PN")).toBeNull());
    expect(screen.getAllByText("Tesouro Selic").length).toBeGreaterThan(0);
  });

  it("mostra erro da API", async () => {
    vi.mocked(getJson).mockRejectedValue(new Error("falha no radar"));
    render(<RadarPage />);

    expect(await screen.findByRole("alert")).toBeTruthy();
  });
});
