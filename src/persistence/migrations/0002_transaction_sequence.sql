ALTER TABLE transactions
    ADD COLUMN sequence INTEGER NOT NULL DEFAULT 0 CHECK (sequence >= 0);

CREATE INDEX idx_transactions_portfolio_sequence
    ON transactions (portfolio_id, occurred_at, sequence, id);
