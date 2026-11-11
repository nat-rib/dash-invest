import { getJson } from "./api";

export interface SeriesKey {
  provider: string;
  instrument_id: string | null;
  metric: string;
  observations: number;
}

export interface MonthlyReturn {
  month: string;
  return_value: number;
}

export interface RiskReport {
  observations: number;
  returns: number;
  start_date: string | null;
  end_date: string | null;
  total_return: number | null;
  annualized_volatility: number | null;
  max_drawdown: number | null;
  sharpe: number | null;
  sortino: number | null;
  var_95: number | null;
  cvar_95: number | null;
  var_95_parametric: number | null;
  cvar_95_parametric: number | null;
  beta: number | null;
  correlation: number | null;
  monthly_returns: MonthlyReturn[];
  unavailable: string[];
  reason: string | null;
}

export function fetchSeriesKeys(metric = "close"): Promise<{ items: SeriesKey[] }> {
  const params = new URLSearchParams({ metric });
  return getJson(`/api/data/series?${params.toString()}`);
}

export function fetchInstrumentRisk(
  provider: string,
  instrumentId: string,
  riskFreeRate: number,
): Promise<RiskReport> {
  const params = new URLSearchParams({
    provider,
    instrument_id: instrumentId,
    metric: "close",
    risk_free_rate: String(riskFreeRate),
  });
  return getJson(`/api/risk/instrument?${params.toString()}`);
}

export function fetchPortfolioRisk(riskFreeRate: number): Promise<RiskReport> {
  const params = new URLSearchParams({ risk_free_rate: String(riskFreeRate) });
  return getJson(`/api/risk/portfolio?${params.toString()}`);
}
