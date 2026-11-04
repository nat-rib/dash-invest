CREATE TABLE transfer_links (
    transfer_out_id TEXT PRIMARY KEY REFERENCES transactions(id) ON DELETE RESTRICT,
    transfer_in_id TEXT NOT NULL UNIQUE REFERENCES transactions(id) ON DELETE RESTRICT,
    portfolio_id TEXT NOT NULL REFERENCES portfolios(id) ON DELETE RESTRICT,
    linked_at TEXT NOT NULL,
    confirmation_source TEXT NOT NULL DEFAULT 'manual'
);

CREATE INDEX idx_transfer_links_portfolio ON transfer_links(portfolio_id, linked_at);
