import type {
  CsvImportResult,
  CsvMapping,
  CsvPreview,
  Instrument,
  LedgerPage,
  LedgerState,
  SnapshotImportResult,
  SnapshotPreview,
  TransferLink,
  TransferSuggestions,
} from "../types";
import { getJson, sendForm, sendJson } from "./api";

const BASE = "/api/ledger";

export function fetchLedgerPage(params: URLSearchParams): Promise<LedgerPage> {
  return getJson(`${BASE}/transactions?${params.toString()}`);
}

export function fetchInstruments(query?: string): Promise<Instrument[]> {
  const url = query ? `${BASE}/instruments?q=${encodeURIComponent(query)}` : `${BASE}/instruments`;
  return getJson(url);
}

export function createInstrument(body: {
  name: string;
  asset_class: string;
  currency: string;
  exchange: string | null;
  ticker: string;
}): Promise<Instrument> {
  return sendJson(`${BASE}/instruments`, "POST", body);
}

export function previewSnapshot(): Promise<SnapshotPreview> {
  return sendJson(`${BASE}/snapshot/preview`, "POST", null);
}

export function importSnapshot(): Promise<SnapshotImportResult> {
  return sendJson(`${BASE}/snapshot/import`, "POST", null);
}

export function fetchLedgerState(): Promise<LedgerState> {
  return getJson(`${BASE}/state`);
}

export function previewCsv(file: File, mapping: CsvMapping): Promise<CsvPreview> {
  return sendForm(`${BASE}/csv/preview`, file, { mapping: JSON.stringify(mapping) });
}

export function importCsv(file: File, mapping: CsvMapping): Promise<CsvImportResult> {
  return sendForm(`${BASE}/csv/import`, file, { mapping: JSON.stringify(mapping) });
}

export function fetchTransferSuggestions(): Promise<TransferSuggestions> {
  return getJson(`${BASE}/transfers/suggestions`);
}

export function confirmTransfer(
  transferOutId: string,
  transferInId: string,
  confirmationSource: "manual" | "manual_review",
): Promise<TransferLink> {
  return sendJson(`${BASE}/transfers/confirm`, "POST", {
    transfer_out_id: transferOutId,
    transfer_in_id: transferInId,
    confirmation_source: confirmationSource,
  });
}

// ---- Rentabilidade (Fase 2) ----

export interface PerformanceFlows {
  portfolio_id: string;
  portfolio_name: string;
  currency: string | null;
  flows: { date: string; amount: string; currency: string }[];
  unavailable_reason: string | null;
}

export interface XirrResult {
  annual_rate: string;
  terminal_value: string;
  terminal_date: string;
  flows_used: number;
}

export interface TwrPeriod {
  start_date: string;
  end_date: string;
  start_value: string;
  end_value_after_flows: string;
  net_external_flow: string;
}

export interface TwrValuations {
  portfolio_id: string;
  currency: string;
  periods: TwrPeriod[];
  saved: number;
}

export interface TwrResult {
  rate: string;
  periods: number;
  start_date: string;
  end_date: string;
}

export function fetchPerformanceFlows(): Promise<PerformanceFlows> {
  return getJson(`${BASE}/performance/flows`);
}

export function calculateXirr(terminalValue: string, terminalDate: string): Promise<XirrResult> {
  return sendJson(`${BASE}/performance/xirr/calculate`, "POST", {
    terminal_value: terminalValue,
    terminal_date: terminalDate,
  });
}

export function fetchTwrValuations(): Promise<TwrValuations> {
  return getJson(`${BASE}/performance/twr`);
}

export function saveTwrValuations(periods: TwrPeriod[]): Promise<TwrValuations> {
  return sendJson(`${BASE}/performance/valuations`, "POST", { periods });
}

export function calculateTwr(periods?: TwrPeriod[]): Promise<TwrResult> {
  return sendJson(`${BASE}/performance/twr/calculate`, "POST", {
    periods: periods ?? null,
  });
}

// ---- Importação de carteira (Fase 3) ----

export interface ImportPreview {
  snapshot_date: string;
  currency: string;
  positions: {
    institution: string;
    asset_class: string;
    ticker: string | null;
    name: string;
    quantity: string | null;
    currency: string;
  }[];
  duplicates: string[][];
  valid: boolean;
  validation_errors: string[];
  message: string;
}

export interface ImportConfirm {
  snapshot_date: string;
  positions: number;
  message: string;
}

export function previewImportSnapshot(file: File): Promise<ImportPreview> {
  return sendForm(`${BASE}/import/snapshot/preview`, file, {});
}

export function confirmImportSnapshot(file: File): Promise<ImportConfirm> {
  return sendForm(`${BASE}/import/snapshot/confirm`, file, { confirm_replacement: "true" });
}
