-- Snapshots do ranking para avaliação futura e histórico de alertas (Fase 8).
CREATE TABLE candidate_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_date TEXT NOT NULL,
    asset_key TEXT NOT NULL,
    name TEXT NOT NULL,
    asset_class TEXT NOT NULL,
    score REAL NOT NULL,
    confidence REAL NOT NULL,
    components_json TEXT NOT NULL DEFAULT '{}',
    reasons_json TEXT NOT NULL DEFAULT '[]',
    sources_json TEXT NOT NULL DEFAULT '[]',
    signal_count INTEGER NOT NULL DEFAULT 0,
    reference_price REAL,
    reference_price_date TEXT,
    price_provider TEXT,
    price_instrument TEXT,
    created_at TEXT NOT NULL,
    UNIQUE (snapshot_date, asset_key)
);

CREATE INDEX idx_snapshots_date ON candidate_snapshots (snapshot_date);

CREATE TABLE alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_key TEXT NOT NULL,
    name TEXT NOT NULL,
    score REAL NOT NULL,
    channel TEXT NOT NULL,
    message TEXT NOT NULL,
    sent_at TEXT NOT NULL
);

CREATE INDEX idx_alerts_asset ON alerts (asset_key, sent_at);
