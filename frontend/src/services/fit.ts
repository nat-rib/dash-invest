import { getJson } from "./api";

export interface ExposureSlice {
  name: string;
  value: number;
  share: number;
  positions: number;
}

export interface FitPosition {
  name: string;
  institution: string;
  asset_class: string;
  currency: string;
  value_brl: number;
  share: number;
  liquidity: string | null;
  risk_category: string | null;
}

export interface CorrelationPair {
  left: string;
  right: string;
  correlation: number;
  observations: number;
}

export interface PortfolioFit {
  total_brl: number;
  positions: number;
  by_class: ExposureSlice[];
  by_institution: ExposureSlice[];
  by_currency: ExposureSlice[];
  top_positions: FitPosition[];
  herfindahl: number | null;
  liquidity_coverage: number | null;
  credit_coverage: number | null;
  correlations: CorrelationPair[];
  unavailable: string[];
}

export function fetchFit(): Promise<PortfolioFit> {
  return getJson("/api/fit");
}
