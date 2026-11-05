CREATE TABLE performance_periods (
    portfolio_id TEXT NOT NULL REFERENCES portfolios(id) ON DELETE RESTRICT,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    start_value TEXT NOT NULL,
    end_value_after_flows TEXT NOT NULL,
    net_external_flow TEXT NOT NULL DEFAULT '0',
    currency TEXT NOT NULL CHECK (length(currency) = 3),
    PRIMARY KEY (portfolio_id, start_date, end_date),
    CHECK (end_date > start_date)
);
