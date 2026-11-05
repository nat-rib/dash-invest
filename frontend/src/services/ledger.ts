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
