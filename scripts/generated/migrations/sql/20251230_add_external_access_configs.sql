-- =============================================================================
-- Migration: b2c3d4e5f6g7
-- add_external_access_configs
-- =============================================================================
-- This migration is idempotent and can be safely re-run.
-- It uses IF NOT EXISTS / IF EXISTS clauses for all operations.
-- =============================================================================

CREATE TABLE IF NOT EXISTS app_data.external_access_configs (
    id INTEGER NOT NULL,
    name VARCHAR NOT NULL,
    label VARCHAR NOT NULL,
    description TEXT,
    host_ports VARCHAR NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE (name)
);

-- Mark migration as applied (idempotent)
INSERT INTO app_data.alembic_version (version_num)
SELECT 'b2c3d4e5f6g7' WHERE NOT EXISTS (
    SELECT 1 FROM app_data.alembic_version WHERE version_num = 'b2c3d4e5f6g7'
);