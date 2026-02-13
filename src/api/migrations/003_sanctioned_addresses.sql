-- M9.4: Sanctioned addresses table for OFAC SDN + EU sanctions screening
-- Stores known sanctioned cryptocurrency addresses synced from public lists.

CREATE TABLE IF NOT EXISTS sanctioned_addresses (
    id              SERIAL PRIMARY KEY,
    address         TEXT NOT NULL,
    blockchain      TEXT NOT NULL,
    source          TEXT NOT NULL,           -- 'ofac_sdn', 'eu_consolidated', 'manual'
    list_name       TEXT,                    -- e.g. 'SDN List', 'EU Consolidated'
    entity_name     TEXT,                    -- Name of sanctioned entity/individual
    entity_id       TEXT,                    -- Source-specific ID (e.g. OFAC UID)
    program         TEXT,                    -- Sanctions program (e.g. 'CYBER2', 'UKRAINE-EO13662')
    added_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    removed_at      TIMESTAMPTZ,            -- NULL = still active; set when address disappears from list
    metadata        JSONB DEFAULT '{}',
    UNIQUE (address, blockchain, source)
);

CREATE INDEX IF NOT EXISTS idx_sanctioned_addr ON sanctioned_addresses (address);
CREATE INDEX IF NOT EXISTS idx_sanctioned_bc ON sanctioned_addresses (blockchain);
CREATE INDEX IF NOT EXISTS idx_sanctioned_source ON sanctioned_addresses (source);
CREATE INDEX IF NOT EXISTS idx_sanctioned_active ON sanctioned_addresses (removed_at) WHERE removed_at IS NULL;

-- Screening log: records every screen request for audit trail
CREATE TABLE IF NOT EXISTS sanctions_screening_log (
    id              SERIAL PRIMARY KEY,
    screened_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    address         TEXT NOT NULL,
    blockchain      TEXT,
    matched         BOOLEAN NOT NULL DEFAULT FALSE,
    match_source    TEXT,                    -- which list matched
    match_entity    TEXT,                    -- entity name if matched
    requested_by    TEXT,                    -- username or 'system'
    metadata        JSONB DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_screening_log_addr ON sanctions_screening_log (address);
CREATE INDEX IF NOT EXISTS idx_screening_log_time ON sanctions_screening_log (screened_at);

-- Sync metadata: tracks last successful sync per source
CREATE TABLE IF NOT EXISTS sanctions_sync_status (
    source          TEXT PRIMARY KEY,
    last_sync_at    TIMESTAMPTZ,
    records_synced  INTEGER DEFAULT 0,
    status          TEXT DEFAULT 'pending',  -- 'pending', 'running', 'success', 'error'
    error_message   TEXT,
    metadata        JSONB DEFAULT '{}'
);

INSERT INTO sanctions_sync_status (source) VALUES ('ofac_sdn'), ('eu_consolidated')
ON CONFLICT (source) DO NOTHING;
