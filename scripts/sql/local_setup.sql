-- =============================================================================
-- BlendX Local Development Setup
-- Script to create all necessary tables and grants for local development
-- =============================================================================

-- =============================================================================
-- STEP 1: GRANTS (Run with ACCOUNTADMIN or owner role)
-- =============================================================================

-- Switch to admin role to grant permissions
USE ROLE ACCOUNTADMIN;  -- Or use the role that owns the database

-- Grants on database
GRANT USAGE ON DATABASE spcs_app_test TO ROLE naspcs_role;

-- Grants on schema
GRANT USAGE ON SCHEMA spcs_app_test.napp TO ROLE naspcs_role;
GRANT CREATE TABLE ON SCHEMA spcs_app_test.napp TO ROLE naspcs_role;

-- Grants on existing tables
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA spcs_app_test.napp TO ROLE naspcs_role;

-- Grants on future tables
GRANT SELECT, INSERT, UPDATE, DELETE ON FUTURE TABLES IN SCHEMA spcs_app_test.napp TO ROLE naspcs_role;

-- Warehouse grant
GRANT USAGE ON WAREHOUSE wh_nap TO ROLE naspcs_role;


-- =============================================================================
-- STEP 2: CREATE TABLES (Run with naspcs_role)
-- =============================================================================

USE ROLE naspcs_role;
USE WAREHOUSE wh_nap;
USE DATABASE spcs_app_test;
USE SCHEMA napp;

-- -----------------------------------------------------------------------------
-- Table: crew_execution_results
-- Used by: crew_service.py for storing crew execution results
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS crew_execution_results (
    id VARCHAR(36) PRIMARY KEY,
    execution_timestamp TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    crew_name VARCHAR(255),
    raw_output VARIANT,
    result_text TEXT,
    status VARCHAR(50),
    error_message TEXT,
    metadata VARIANT
);

-- -----------------------------------------------------------------------------
-- Table: crew_executions
-- Used by: SQLAlchemy ORM model CrewExecution
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS crew_executions (
    id VARCHAR(36) PRIMARY KEY,
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    name VARCHAR(255),
    input TEXT,
    output TEXT,
    context VARIANT,
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    finished_at TIMESTAMP_NTZ,
    execution_group_id VARCHAR(36),
    flow_execution_id VARCHAR(36)
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

-- -----------------------------------------------------------------------------
-- Table: execution_groups
-- Used by: crew_executions foreign key reference
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS execution_groups (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255),
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    input TEXT,
    output TEXT,
    context VARIANT,
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    finished_at TIMESTAMP_NTZ
);

-- -----------------------------------------------------------------------------
-- Table: flow_executions
-- Used by: crew_executions foreign key reference
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS flow_executions (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255),
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    input TEXT,
    output TEXT,
    context VARIANT,
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    finished_at TIMESTAMP_NTZ,
    execution_group_id VARCHAR(36)
);

-- -----------------------------------------------------------------------------
-- Table: agent_executions
-- Used by: crew_executions relationship
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS agent_executions (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255),
    role VARCHAR(255),
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    input TEXT,
    output TEXT,
    context VARIANT,
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    finished_at TIMESTAMP_NTZ,
    crew_execution_id VARCHAR(36)
);


-- =============================================================================
-- STEP 3: VERIFY SETUP
-- =============================================================================

-- Show all tables created
SHOW TABLES IN SCHEMA spcs_app_test.napp;

-- Verify table structure
-- DESCRIBE TABLE crew_execution_results;
-- DESCRIBE TABLE workflows;
-- DESCRIBE TABLE chat_messages;
