import { getJson } from "./api";

export interface ResearchClaim {
  key: string;
  text: string;
  metric: string;
  value: number;
  unit: string;
  reference_date: string | null;
  source_url: string | null;
}

export interface ResearchReport {
  cnpj: string;
  name: string;
  generated_at: string;
  narrative: string;
  claims: ResearchClaim[];
  limitations: string[];
  sources: string[];
  gateway: string;
}

export function fetchResearch(cnpj: string): Promise<ResearchReport> {
  return getJson(`/api/research/${encodeURIComponent(cnpj)}`);
}
