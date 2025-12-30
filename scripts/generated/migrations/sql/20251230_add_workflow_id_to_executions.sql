-- =============================================================================
-- Migration: a1b2c3d4e5f6
-- add_workflow_id_and_result_to_executions
-- =============================================================================
-- This migration is idempotent and can be safely re-run.
-- It uses IF NOT EXISTS / IF EXISTS clauses for all operations.
-- =============================================================================

ALTER TABLE app_data.flow_executions ADD COLUMN IF NOT EXISTS workflow_id VARCHAR;

ALTER TABLE app_data.flow_executions ADD COLUMN IF NOT EXISTS result TEXT;

ALTER TABLE app_data.execution_groups ADD COLUMN IF NOT EXISTS workflow_id VARCHAR;

ALTER TABLE app_data.execution_groups ADD COLUMN IF NOT EXISTS result TEXT;

-- Mark migration as applied (idempotent)
INSERT INTO app_data.alembic_version (version_num)
SELECT 'a1b2c3d4e5f6' WHERE NOT EXISTS (
    SELECT 1 FROM app_data.alembic_version WHERE version_num = 'a1b2c3d4e5f6'
);