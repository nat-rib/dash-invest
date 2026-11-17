import { getJson } from "./api";

export interface AssetMention {
  key: string;
  name: string;
  asset_class: string;
  confidence: number;
  cnpj: string | null;
}

export interface Candidate {
  key: string;
  name: string;
  asset_class: string;
  score: number;
  confidence: number;
  components: Record<string, number | null>;
  reasons: string[];
  missing: string[];
  sources: string[];
  signal_count: number;
  last_seen: string | null;
  cnpj: string | null;
  price_provider: string | null;
  price_instrument: string | null;
}

export interface CandidateList {
  items: Candidate[];
  total: number;
}

export interface MonitorSignal {
  source: string;
  title: string;
  url: string;
  summary: string;
  published_at: string | null;
  collected_at: string;
  assets: AssetMention[];
}

export interface SignalList {
  items: MonitorSignal[];
  total: number;
}

export interface MonitorSource {
  name: string;
  url: string;
  weight: number;
}

export interface ScoreBucket {
  label: string;
  count: number;
  average_return: number | null;
  hit_rate: number | null;
}

export interface BacktestReport {
  snapshots: number;
  evaluated: number;
  horizon_days: number;
  buckets: ScoreBucket[];
  rank_correlation: number | null;
  top_average: number | null;
  bottom_average: number | null;
  spread: number | null;
  available: boolean;
  reason: string | null;
}

export interface AlertRecord {
  asset_key: string;
  name: string;
  score: number;
  channel: string;
  message: string;
  sent_at: string;
}

export interface AlertConfig {
  channels: string[];
  min_score: number;
  cooldown_days: number;
  max_alerts: number;
  telegram_configured: boolean;
  email_configured: boolean;
}

export function fetchCandidates(params?: {
  limit?: number;
  minScore?: number;
  assetClass?: string;
}): Promise<CandidateList> {
  const search = new URLSearchParams({ limit: String(params?.limit ?? 100) });
  if (params?.minScore) search.set("min_score", String(params.minScore));
  if (params?.assetClass) search.set("asset_class", params.assetClass);
  return getJson(`/api/monitor/candidates?${search.toString()}`);
}

export function fetchMonitorSignals(limit = 30): Promise<SignalList> {
  return getJson(`/api/monitor/signals?limit=${limit}&lookback_days=30`);
}

export function fetchMonitorSources(): Promise<{ items: MonitorSource[] }> {
  return getJson("/api/monitor/sources");
}

export function fetchBacktest(horizonDays = 30): Promise<BacktestReport> {
  return getJson(`/api/monitor/backtest?horizon_days=${horizonDays}`);
}

export function fetchMonitorAlerts(limit = 20): Promise<{ items: AlertRecord[]; total: number }> {
  return getJson(`/api/monitor/alerts?limit=${limit}`);
}

export function fetchAlertConfig(): Promise<AlertConfig> {
  return getJson("/api/monitor/alert-config");
}
