import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../services/api", () => ({ getJson: vi.fn() }));

import { getJson } from "../services/api";
import HistoricoPage from "./HistoricoPage";

type PositionPoint = {
  captured_at: string;
  position_key: string;
  name: string;
  institution: string;
  currency: string;
  current_price: number | null;
  current_value: number | null;
  value_brl: number | null;
};

function stubApi(portfolioTotal: number, positionValues: (number | null)[]) {
  const mocked = vi.mocked(getJson);
  const positionPoints: PositionPoint[] = positionValues.map((value, index) => ({
    captured_at: `2026-11-0${index + 1}T12:00:00`,
    position_key: "PETR4|XP",
    name: "PETR4",
    institution: "XP",
    currency: "BRL",
    current_price: 10,
    current_value: value,
    value_brl: value,
  }));

  mocked.mockImplementation((url: string) => {
    if (url === "/api/history/portfolio") {
      return Promise.resolve({
        points: [
          { captured_at: "2026-11-01T12:00:00", total_brl: 1000, source: "manual" },
          { captured_at: "2026-11-02T12:00:00", total_brl: portfolioTotal, source: "manual" },
        ],
        notice: "",
      } as never);
    }
    if (url === "/api/history/positions") {
      return Promise.resolve({ keys: ["PETR4|XP"] } as never);
    }
    return Promise.resolve({ points: positionPoints } as never);
  });
}

describe("HistoricoPage", () => {
  beforeEach(() => {
    vi.mocked(getJson).mockReset();
  });

  it("mostra a variação entre o primeiro e o último snapshot", async () => {
    stubApi(1500, [100]);
    render(<HistoricoPage />);
    expect(await screen.findByText("50.00%")).toBeTruthy();
  });

  it("omite pontos sem valor em BRL em vez de tratá-los como zero", async () => {
    stubApi(1200, [100, null]);
    render(<HistoricoPage />);

    fireEvent.change(await screen.findByRole("combobox"), { target: { value: "PETR4|XP" } });

    await waitFor(() => {
      expect(screen.getByText(/1 ponto sem valor em BRL foi omitido/i)).toBeTruthy();
    });
  });
});
