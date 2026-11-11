import { getJson, sendJson } from "./api";

export interface ScreenerRow {
  cnpj: string;
  name: string | null;
  reference_date: string | null;
  revenue: number | null;
  net_income: number | null;
  equity: number | null;
  total_assets: number | null;
  net_margin: number | null;
  roe: number | null;
  roa: number | null;
  asset_turnover: number | null;
}

export interface ScreenerResponse {
  items: ScreenerRow[];
  total: number;
}

export interface DcfProjection {
  year: number;
  cash_flow: number;
  present_value: number;
}

export interface DcfResult {
  present_value_explicit: number;
  present_value_terminal: number;
  enterprise_value: number;
  projections: DcfProjection[];
}

export function fetchScreener(params: {
  minRoe?: string;
  minNetMargin?: string;
  minRoa?: string;
  sortBy: string;
  order: "asc" | "desc";
  limit?: number;
}): Promise<ScreenerResponse> {
  const search = new URLSearchParams({
    sort_by: params.sortBy,
    order: params.order,
    limit: String(params.limit ?? 100),
  });
  if (params.minRoe) search.set("min_roe", params.minRoe);
  if (params.minNetMargin) search.set("min_net_margin", params.minNetMargin);
  if (params.minRoa) search.set("min_roa", params.minRoa);
  return getJson(`/api/screener?${search.toString()}`);
}

export function calculateDcf(body: {
  base_cash_flow: number;
  growth_rate: number;
  years: number;
  terminal_growth: number;
  discount_rate: number;
}): Promise<DcfResult> {
  return sendJson("/api/valuation/dcf", "POST", body);
}
