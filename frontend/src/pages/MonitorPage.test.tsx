import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../services/api", () => ({ getJson: vi.fn() }));

import { getJson } from "../services/api";
import MonitorPage from "./MonitorPage";

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
      reasons: [
        "Renda fixa está 50.0 p.p. abaixo do alvo de 60%",
        "2 sinal(is) de 1 fonte(s)",
      ],
      missing: ["fundamentos", "valuation", "série de preço"],
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

const signals = {
  items: [
    {
      source: "InfoMoney",
      title: "Tesouro Selic atrai",
      url: "https://example/tesouro",
      summary: "Renda fixa",
      published_at: "2026-11-16T12:00:00Z",
      collected_at: "2026-11-16T12:00:00Z",
      assets: [
        {
          key: "fixed_income:tesouro-selic",
          name: "Tesouro Selic",
          asset_class: "renda_fixa",
          confidence: 0.75,
          cnpj: null,
        },
      ],
    },
  ],
  total: 1,
};

const backtest = {
  snapshots: 10,
  evaluated: 8,
  horizon_days: 30,
  buckets: [
    { label: "0–20", count: 1, average_return: -0.05, hit_rate: 0 },
    { label: "20–40", count: 1, average_return: 0.0, hit_rate: 0.5 },
    { label: "40–60", count: 2, average_return: 0.02, hit_rate: 0.5 },
    { label: "60–80", count: 2, average_return: 0.05, hit_rate: 0.5 },
    { label: "80–100", count: 2, average_return: 0.1, hit_rate: 0.5 },
  ],
  rank_correlation: 0.8,
  top_average: 0.1,
  bottom_average: -0.05,
  spread: 0.15,
  available: true,
  reason: null,
};

const alert = {
  asset_key: "ticker:PETR4",
  name: "Itaú Unibanco",
  score: 85,
  channel: "telegram",
  message: "alerta",
  sent_at: "2026-11-16T12:00:00Z",
};

const alertConfig = {
  channels: ["console", "telegram"],
  min_score: 80,
  cooldown_days: 3,
  max_alerts: 5,
  telegram_configured: true,
  email_configured: false,
};

describe("MonitorPage", () => {
  beforeEach(() => {
    vi.mocked(getJson).mockReset();
    vi.mocked(getJson).mockImplementation((url: string) => {
      if (url.startsWith("/api/monitor/candidates")) return Promise.resolve(candidates as never);
      if (url.startsWith("/api/monitor/signals")) return Promise.resolve(signals as never);
      if (url.startsWith("/api/monitor/backtest")) return Promise.resolve(backtest as never);
      if (url.startsWith("/api/monitor/alerts")) {
        return Promise.resolve({ items: [alert], total: 1 } as never);
      }
      if (url.startsWith("/api/monitor/alert-config")) return Promise.resolve(alertConfig as never);
      return Promise.resolve({ items: [] } as never);
    });
  });

  it("mostra ranking, motivos e sinais", async () => {
    render(<MonitorPage />);

    expect((await screen.findAllByText("Tesouro Selic")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("82").length).toBeGreaterThan(0);
    expect(screen.getByText(/abaixo do alvo/)).toBeTruthy();
    expect(screen.getAllByText(/Lacuna de alocação/).length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: "Tesouro Selic atrai" })).toBeTruthy();
    expect(screen.getByText(/Sem dados: fundamentos/)).toBeTruthy();
  });

  it("mostra avaliação do ranking e alertas", async () => {
    render(<MonitorPage />);

    expect(await screen.findByText("Avaliação do ranking")).toBeTruthy();
    expect(screen.getByText("15%")).toBeTruthy();
    expect(screen.getByText("0.80")).toBeTruthy();
    expect(screen.getByText("Itaú Unibanco")).toBeTruthy();
    expect(screen.getByText(/Canais: console, telegram/)).toBeTruthy();
    expect(screen.getByText(/Telegram configurado/)).toBeTruthy();
  });

  it("filtra pelo score mínimo", async () => {
    render(<MonitorPage />);
    await screen.findAllByText("Tesouro Selic");

    fireEvent.change(screen.getByPlaceholderText("0"), { target: { value: "80" } });

    await waitFor(() => expect(screen.queryByText("Petrobras PN")).toBeNull());
    expect(screen.getAllByText("Tesouro Selic").length).toBeGreaterThan(0);
  });
});
