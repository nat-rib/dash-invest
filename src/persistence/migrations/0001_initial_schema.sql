CREATE TABLE portfolios (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    base_currency TEXT NOT NULL CHECK (length(base_currency) = 3),
    created_at TEXT NOT NULL
);

CREATE TABLE instruments (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    asset_class TEXT NOT NULL,
    subclass TEXT,
    currency TEXT NOT NULL CHECK (length(currency) = 3),
    country TEXT,
    exchange TEXT,
    issuer_id TEXT,
    provider_symbols_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE portfolio_positions (
    portfolio_id TEXT NOT NULL REFERENCES portfolios(id) ON DELETE RESTRICT,
    instrument_id TEXT NOT NULL REFERENCES instruments(id) ON DELETE RESTRICT,
    institution TEXT NOT NULL CHECK (length(trim(institution)) > 0),
    quantity TEXT NOT NULL,
    average_cost TEXT,
    cost_currency TEXT NOT NULL CHECK (length(cost_currency) = 3),
    as_of TEXT NOT NULL,
    PRIMARY KEY (portfolio_id, instrument_id, institution, as_of)
);

CREATE TABLE transactions (
    id TEXT PRIMARY KEY,
    portfolio_id TEXT NOT NULL REFERENCES portfolios(id) ON DELETE RESTRICT,
    transaction_type TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    institution TEXT NOT NULL CHECK (length(trim(institution)) > 0),
    instrument_id TEXT REFERENCES instruments(id) ON DELETE RESTRICT,
    quantity TEXT,
    unit_price TEXT,
    amount TEXT,
    currency TEXT NOT NULL CHECK (length(currency) = 3),
    fees TEXT NOT NULL DEFAULT '0',
    taxes TEXT NOT NULL DEFAULT '0',
    transfer_id TEXT,
    external_id TEXT,
    notes TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX idx_transactions_portfolio_date
    ON transactions (portfolio_id, occurred_at, id);

CREATE INDEX idx_transactions_instrument_date
    ON transactions (instrument_id, occurred_at)
    WHERE instrument_id IS NOT NULL;

CREATE UNIQUE INDEX uq_transactions_external_id
    ON transactions (portfolio_id, institution, external_id)
    WHERE external_id IS NOT NULL;

CREATE INDEX idx_positions_latest
    ON portfolio_positions (portfolio_id, instrument_id, as_of DESC);
