import { deleteJson, getJson, sendJson } from "./api";

export interface WatchlistItem {
  asset_key: string;
  name: string;
  asset_class: string;
  note: string | null;
  created_at: string;
}

export function fetchWatchlist(): Promise<{ items: WatchlistItem[]; total: number }> {
  return getJson("/api/watchlist");
}

export function addWatchlist(item: {
  asset_key: string;
  name: string;
  asset_class: string;
  note?: string | null;
}): Promise<WatchlistItem> {
  return sendJson("/api/watchlist", "POST", item);
}

export function removeWatchlist(assetKey: string): Promise<void> {
  return deleteJson(`/api/watchlist/${encodeURIComponent(assetKey)}`);
}
