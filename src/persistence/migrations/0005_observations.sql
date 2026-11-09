-- Observações externas normalizadas com proveniência (Fase 3: data platform).
-- Append-only: correções e reapresentações geram novas linhas; a anterior é
-- apenas marcada como superseded_by, nunca apagada ou sobrescrita.
CREATE TABLE observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fingerprint TEXT NOT NULL UNIQUE,
    provider TEXT NOT NULL CHECK (length(trim(provider)) > 0),
    instrument_id TEXT,
    metric TEXT NOT NULL CHECK (length(trim(metric)) > 0),
    value TEXT NOT NULL,
    currency TEXT CHECK (currency IS NULL OR length(currency) = 3),
    unit TEXT,
    period_start TEXT,
    period_end TEXT,
    reference_date TEXT NOT NULL,
    published_at TEXT,
    collected_at TEXT NOT NULL,
    parser_version TEXT NOT NULL CHECK (length(trim(parser_version)) > 0),
    quality_status TEXT NOT NULL
        CHECK (quality_status IN ('verified', 'estimated', 'stale', 'unknown')),
    source_document TEXT,
    raw_payload TEXT,
    superseded_by INTEGER REFERENCES observations(id) ON DELETE SET NULL,
    CHECK (period_start IS NULL OR period_end IS NULL OR period_end >= period_start)
);

CREATE INDEX idx_observations_series
    ON observations (provider, instrument_id, metric, reference_date);

CREATE INDEX idx_observations_collected
    ON observations (collected_at);
