-- Lista de ativos acompanhados manualmente (watchlist).
CREATE TABLE watchlist (
    asset_key TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    asset_class TEXT NOT NULL,
    note TEXT,
    created_at TEXT NOT NULL
);
