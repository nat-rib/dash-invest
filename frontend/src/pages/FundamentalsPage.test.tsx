import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../services/api", () => ({ getJson: vi.fn() }));

import { getJson } from "../services/api";
import FundamentalsPage from "./FundamentalsPage";

const issuers = {
  items: [
    {
      cnpj: "00000000000191",
      name: "PETROBRAS",
      cvm_code: "001023",
      source: "cvm",
      updated_at: "2025-02-19T00:00:00Z",
    },
  ],
  total: 1,
};

const points = [
  {
    reference_date: "2023-12-31",
    published_at: "2024-02-01T00:00:00Z",
    value: "900",
    currency: "BRL",
    source_document: "http://doc/2023",
  },
  {
    reference_date: "2024-12-31",
    published_at: "2025-02-19T00:00:00Z",
    value: "1100",
    currency: "BRL",
    source_document: "http://doc/2024",
  },
];

function stubApi(seriesPoints = points) {
  vi.mocked(getJson).mockImplementation((url: string) => {
    if (url.startsWith("/api/data/issuers")) return Promise.resolve(issuers as never);
    if (url.startsWith("/api/data/observations/series")) {
      return Promise.resolve({
        provider: "cvm",
        instrument_id: "cnpj:00000000000191",
        metric: "revenue",
        points: seriesPoints,
      } as never);
    }
    return Promise.resolve({} as never);
  });
}

describe("FundamentalsPage", () => {
  beforeEach(() => {
    vi.mocked(getJson).mockReset();
  });

  it("carrega emissor e série e exibe a proveniência", async () => {
    stubApi();
    render(<FundamentalsPage />);

    expect(await screen.findByText(/Último valor/)).toBeTruthy();
    expect(screen.getAllByText(/1\.100/).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("link", { name: "CVM" }).length).toBe(2);
  });

  it("mostra estado vazio quando não há pontos", async () => {
    stubApi([]);
    render(<FundamentalsPage />);

    expect(await screen.findByText(/Sem observações para este emissor/)).toBeTruthy();
  });

  it("exibe erro da API", async () => {
    vi.mocked(getJson).mockRejectedValue(new Error("falha na CVM"));
    render(<FundamentalsPage />);

    expect(await screen.findByRole("alert")).toBeTruthy();
  });

  it("consulta o provider trimestral ao trocar a periodicidade", async () => {
    stubApi();
    const { container } = render(<FundamentalsPage />);
    await screen.findByText(/Último valor/);

    const selects = container.querySelectorAll("select");
    fireEvent.change(selects[1], { target: { value: "itr" } });

    await waitFor(() => {
      expect(vi.mocked(getJson)).toHaveBeenCalledWith(
        expect.stringContaining("provider=cvm_itr"),
      );
    });
  });

  it("anexa _ytd ao marcar acumulado no ano", async () => {
    stubApi();
    const { container } = render(<FundamentalsPage />);
    await screen.findByText(/Último valor/);

    fireEvent.change(container.querySelectorAll("select")[1], { target: { value: "itr" } });
    fireEvent.click(await screen.findByRole("checkbox"));

    await waitFor(() => {
      expect(vi.mocked(getJson)).toHaveBeenCalledWith(
        expect.stringContaining("metric=revenue_ytd"),
      );
    });
  });
});
