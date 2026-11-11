import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../services/api", () => ({ getJson: vi.fn() }));

import { getJson } from "../services/api";
import ResearchPage from "./ResearchPage";

const issuers = {
  items: [
    {
      cnpj: "00000000000191",
      name: "Empresa Teste",
      cvm_code: "001023",
      source: "cvm",
      updated_at: "2025-02-19T00:00:00Z",
    },
  ],
  total: 1,
};

const report = {
  cnpj: "00000000000191",
  name: "Empresa Teste",
  generated_at: "2026-11-10T12:00:00Z",
  narrative: "Primeiro parágrafo.\n\nSegundo parágrafo.",
  claims: [
    {
      key: "revenue",
      text: "Receita de R$ 1.200 em 2024",
      metric: "revenue",
      value: 1200,
      unit: "BRL",
      reference_date: "2024-12-31",
      source_url: "http://doc/2024",
    },
  ],
  limitations: ["Não é recomendação de investimento."],
  sources: ["http://doc/2024"],
  gateway: "deterministic",
};

describe("ResearchPage", () => {
  beforeEach(() => {
    vi.mocked(getJson).mockReset();
    vi.mocked(getJson).mockImplementation((url: string) => {
      if (url.startsWith("/api/data/issuers")) return Promise.resolve(issuers as never);
      return Promise.resolve(report as never);
    });
  });

  it("gera relatório com narrativa, evidências e limitações", async () => {
    render(<ResearchPage />);

    const button = await screen.findByRole("button", { name: "Gerar relatório" });
    await waitFor(() => expect((button as HTMLButtonElement).disabled).toBe(false));
    fireEvent.click(button);

    expect(await screen.findByText("Primeiro parágrafo.")).toBeTruthy();
    expect(screen.getByText("Segundo parágrafo.")).toBeTruthy();
    expect(screen.getByText("Receita de R$ 1.200 em 2024")).toBeTruthy();
    expect(screen.getByText(/narrativa determinística/)).toBeTruthy();
    expect(screen.getByText("Não é recomendação de investimento.")).toBeTruthy();
    expect(screen.getByRole("link", { name: "documento" })).toBeTruthy();
  });
});
