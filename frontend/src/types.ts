/** Tipos espelham os schemas Pydantic de api/schemas. Valores financeiros
 * chegam como string para preservar exatidão decimal. */

export type TransactionType =
  | "BUY" | "SELL" | "DEPOSIT" | "WITHDRAWAL" | "DIVIDEND" | "JCP"
  | "INTEREST" | "COUPON" | "AMORTIZATION" | "TAX" | "FEE" | "SPLIT"
  | "BONUS" | "TRANSFER_IN" | "TRANSFER_OUT";

export interface Instrument {
  id: string;
  name: string;
  asset_class: string;
  subclass: string | null;
  currency: string;
  country: string | null;
  exchange: string | null;
  issuer_id: string | null;
  provider_symbols: Record<string, string>;
  metadata: Record<string, unknown>;
}

export interface LedgerTransaction {
  id: string;
  portfolio_id: string;
  transaction_type: TransactionType;
  occurred_at: string;
  sequence: number;
  institution: string;
  instrument_id: string | null;
  instrument_label: string | null;
  quantity: string | null;
  unit_price: string | null;
  amount: string | null;
  currency: string;
  fees: string;
  taxes: string;
  transfer_id: string | null;
  transfer_linked: boolean;
  external_id: string | null;
  notes: string | null;
  metadata: Record<string, unknown>;
}

export interface PageMeta {
  limit: number;
  offset: number;
  total: number;
}

export interface LedgerPage {
  meta: PageMeta;
  items: LedgerTransaction[];
}

export interface SnapshotPosition {
  institution: string;
  asset_class: string;
  ticker: string | null;
  name: string;
  quantity: string | null;
  currency: string;
}

export interface SnapshotPreview {
  portfolio_id: string;
  snapshot_date: string;
  currency: string;
  positions: SnapshotPosition[];
}

export interface SnapshotImportResult {
  portfolio_id: string;
  instruments_saved: number;
  positions_saved: number;
  transactions_created: number;
  message: string;
}

export interface CsvMapping {
  institution: string;
  currency: string;
  delimiter: string;
  columns: Record<string, string>;
  instrument_map: Record<string, string>;
  decimal_locale: string;
  date_format: string;
  timezone_name: string;
}

export interface PreviewTransaction {
  row_number: number;
  external_id: string;
  occurred_at: string;
  transaction_type: string;
  institution: string;
  currency: string;
  instrument_id: string | null;
  quantity: string | null;
  unit_price: string | null;
  amount: string | null;
  fees: string;
  taxes: string;
}

export interface CsvPreview {
  parsed: number;
  transactions: PreviewTransaction[];
}

export interface CsvImportResult {
  parsed: number;
  inserted: number;
  skipped_duplicates: number;
  message: string;
}

export interface TransferEvent {
  id: string;
  transaction_type: string;
  occurred_at: string;
  institution: string;
  amount: string | null;
  quantity: string | null;
  currency: string;
  instrument_id: string | null;
  external_id: string | null;
}

export interface SuggestedPair {
  transfer_out: TransferEvent;
  transfer_in: TransferEvent;
  date_delta_seconds: number;
  amount_delta: string;
}

export interface TransferSuggestions {
  suggested_pairs: SuggestedPair[];
  ambiguous_transaction_ids: string[];
  unmatched_transaction_ids: string[];
  incomplete_transfer_ids: string[];
  invalid_transfer_ids: string[];
  pending_out_events: TransferEvent[];
  pending_in_events: TransferEvent[];
  confirmed_links: TransferLink[];
}

export interface TransferLink {
  transfer_out_id: string;
  transfer_in_id: string;
  portfolio_id: string;
  linked_at: string;
  confirmation_source: string;
}

export interface Portfolio {
  id: string;
  name: string;
  base_currency: string;
  created_at: string;
}

export interface LedgerState {
  portfolios: Portfolio[];
  instruments_count: number;
  snapshots_count: number;
  transactions_count: number;
  unlinked_transfer_events: number;
  migrations: { version: number; name: string; applied_at: string }[];
  database_path: string;
}
