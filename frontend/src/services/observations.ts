import { getJson } from "./api";

export interface Issuer {
  cnpj: string;
  name: string;
  cvm_code: string | null;
  source: string;
  updated_at: string;
}

export interface IssuerList {
  items: Issuer[];
  total: number;
}

export interface ObservationSeriesPoint {
  reference_date: string;
  published_at: string | null;
  value: string | number;
  currency: string | null;
  source_document: string | null;
}

export interface ObservationSeries {
  provider: string;
  instrument_id: string | null;
  metric: string;
  points: ObservationSeriesPoint[];
}

export function fetchIssuers(query?: string): Promise<IssuerList> {
  const params = new URLSearchParams({ limit: "2000" });
  if (query) params.set("query", query);
  return getJson(`/api/data/issuers?${params.toString()}`);
}

export function fetchObservationSeries(
  cnpj: string,
  metric: string,
): Promise<ObservationSeries> {
  const digits = cnpj.replace(/\D/g, "");
  const params = new URLSearchParams({
    provider: "cvm",
    metric,
    instrument_id: `cnpj:${digits}`,
  });
  return getJson(`/api/data/observations/series?${params.toString()}`);
}
