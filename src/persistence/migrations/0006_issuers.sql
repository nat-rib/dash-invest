-- Emissores de dados externos (Fase 3). CNPJ é a identidade estável do emissor;
-- o vínculo com Instrument (security) é feito em etapa posterior.
CREATE TABLE issuers (
    cnpj TEXT PRIMARY KEY CHECK (length(cnpj) = 14),
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    cvm_code TEXT,
    source TEXT NOT NULL CHECK (length(trim(source)) > 0),
    updated_at TEXT NOT NULL
);

CREATE INDEX idx_issuers_name ON issuers (name COLLATE NOCASE);
