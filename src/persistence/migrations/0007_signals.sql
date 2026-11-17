-- Sinais externos (notícias/RSS) e ativos mencionados (Fase 8: monitor).
CREATE TABLE signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL CHECK (length(trim(source)) > 0),
    source_type TEXT NOT NULL DEFAULT 'rss',
    title TEXT NOT NULL CHECK (length(trim(title)) > 0),
    url TEXT NOT NULL,
    summary TEXT NOT NULL DEFAULT '',
    published_at TEXT,
    collected_at TEXT NOT NULL,
    content_hash TEXT NOT NULL DEFAULT '',
    assets_json TEXT NOT NULL DEFAULT '[]',
    raw TEXT,
    UNIQUE (source, url)
);

CREATE INDEX idx_signals_published ON signals (published_at DESC);
CREATE INDEX idx_signals_content ON signals (content_hash);
