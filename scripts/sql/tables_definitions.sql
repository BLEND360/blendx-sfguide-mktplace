-- =============================================================================
-- BlendX Table Definitions
-- SINGLE SOURCE OF TRUTH for all table schemas
-- This file is included by both local_setup.sql and app/src/setup.sql
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Table: crew_execution_results
-- Used by: crew_service.py for storing execution results
-- -----------------------------------------------------------------------------
-- Note: Schema prefix (app_data. or none) is set by the calling script
CREATE TABLE IF NOT EXISTS crew_execution_results (
    id VARCHAR(36) PRIMARY KEY,
    execution_timestamp TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    raw_output VARIANT,
    result_text TEXT,
    status VARCHAR(50),
    error_message TEXT,
    metadata VARIANT,
    workflow_id VARCHAR(255),                    -- Reference to workflows table
    is_test BOOLEAN DEFAULT FALSE               -- Flag for test executions from UI
);

-- -----------------------------------------------------------------------------
-- Table: workflows
-- Used by: workflows_repository.py for storing generated workflows
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS workflows (
    workflow_id VARCHAR(255) NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    type VARCHAR(50) NOT NULL,
    mermaid TEXT,
    title VARCHAR(255),
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    rationale TEXT,
    yaml_text TEXT NOT NULL,
    chat_id VARCHAR(255),
    message_id VARCHAR(255),
    user_id VARCHAR(255),
    model VARCHAR(100),
    stable BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    PRIMARY KEY (workflow_id, version)
);

-- -----------------------------------------------------------------------------
-- Table: chat_messages
-- Used by: workflows_repository.py for conversation context
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS chat_messages (
    id VARCHAR(36) PRIMARY KEY,
    chat_id VARCHAR(255) NOT NULL,
    role VARCHAR(50),
    content TEXT,
    summary TEXT,
    user_id VARCHAR(255),
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);
