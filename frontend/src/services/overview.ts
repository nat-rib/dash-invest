import { getJson } from "./api";

export interface OverviewAllocationSlice {
  name: string;
  value: string;
  share: string | null;
  positions: number;
}

export interface OverviewTopPosition {
  index: number;
  name: string;
  institution: string;
  asset_class: string;
  consolidated_brl: string;
  share: string;
  concentration_level: "high" | "medium" | "low";
  risk_category: string | null;
}

export interface OverviewAlert {
  id: string;
  tone: "good" | "info" | "warn";
  title: string;
  message: string;
}

export interface OverviewPerformance {
  available: boolean;
  metric: string | null;
  rate: string | null;
  periods: number | null;
  start_date: string | null;
  end_date: string | null;
  reason: string | null;
}

export interface OverviewBenchmark {
  available: boolean;
  name: string | null;
  reason: string | null;
}

export interface OverviewQuality {
  level: "complete" | "partial" | "unknown";
  positions_count: number;
  known_positions: number;
  unknown_positions: number;
  message: string;
}

export interface OverviewLedger {
  instruments_count: number;
  transactions_count: number;
  snapshots_count: number;
  unlinked_transfer_events: number;
  database_path: string;
}

export interface Overview {
  portfolio_id: string;
  snapshot: {
    available: boolean;
    error: string | null;
    snapshot_date: string | null;
    currency: string | null;
  };
  total_brl: string | null;
  known_positions: number;
  unknown_positions: number;
  positions_count: number;
  by_class: OverviewAllocationSlice[];
  by_institution: OverviewAllocationSlice[];
  top_positions: OverviewTopPosition[];
  alerts: OverviewAlert[];
  performance: OverviewPerformance;
  benchmark: OverviewBenchmark;
  quality: OverviewQuality;
  ledger: OverviewLedger;
}

export function fetchOverview(): Promise<Overview> {
  return getJson("/api/overview");
}
