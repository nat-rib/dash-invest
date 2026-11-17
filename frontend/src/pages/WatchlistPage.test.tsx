import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../services/api", () => ({
  getJson: vi.fn(),
  sendJson: vi.fn(),
  deleteJson: vi.fn(),
}));

import { deleteJson, getJson } from "../services/api";
import WatchlistPage from "./WatchlistPage";

const watchlist = {
  items: [
    {
      asset_key: "ticker:PETR4",
      name: "Petrobras PN",
      asset_class: "acao",
      note: null,
      created_at: "2026-11-16T12:00:00Z",
    },
  ],
  total: 1,
};

const candidates = {
  items: [
    {
      key: "ticker:PETR4",
      name: "Petrobras PN",
      asset_class: "acao",
      score: 85,
      confidence: 0.8,
      components: {},
      reasons: [],
      missing: [],
      sources: ["InfoMoney"],
      signal_count: 2,
      last_seen: "2026-11-16T12:00:00Z",
      cnpj: "33000167000101",
      price_provider: "alpha_vantage",
      price_instrument: "PETR4.SAO",
    },
  ],
  total: 1,
};

describe("WatchlistPage", () => {
  beforeEach(() => {
    vi.mocked(getJson).mockReset();
    vi.mocked(getJson).mockImplementation((url: string) => {
      if (url.startsWith("/api/watchlist")) return Promise.resolve(watchlist as never);
      return Promise.resolve(candidates as never);
    });
    vi.mocked(deleteJson).mockReset();
    vi.mocked(deleteJson).mockResolvedValue(undefined as never);
  });

  it("lista ativos acompanhados com score e links", async () => {
    render(<WatchlistPage />);

    expect(await screen.findByText("Petrobras PN")).toBeTruthy();
    expect(screen.getByText("85")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Fundamentos" }).getAttribute("href")).toBe(
      "/fundamentos?cnpj=33000167000101",
    );
    expect(screen.getByRole("link", { name: "Risco" }).getAttribute("href")).toContain(
      "instrument=PETR4.SAO",
    );
  });

  it("remove ativo da watchlist", async () => {
    render(<WatchlistPage />);
    await screen.findByText("Petrobras PN");

    fireEvent.click(screen.getByRole("button", { name: "Remover" }));

    await waitFor(() =>
      expect(vi.mocked(deleteJson)).toHaveBeenCalledWith("/api/watchlist/ticker%3APETR4"),
    );
    await waitFor(() => expect(screen.queryByText("Petrobras PN")).toBeNull());
  });
});
