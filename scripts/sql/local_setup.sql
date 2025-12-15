-- =============================================================================
-- BlendX Local Development Setup
-- Script to create all necessary tables and grants for local development
-- =============================================================================

-- =============================================================================
-- STEP 1: GRANTS (Run with ACCOUNTADMIN or owner role)
-- =============================================================================

-- Switch to admin role to grant permissions
USE ROLE ACCOUNTADMIN;  -- Or use the role that owns the database

CREATE ROLE IF NOT EXISTS naspcs_role;

-- Grants on database
GRANT USAGE ON DATABASE spcs_app_test TO ROLE naspcs_role;

-- Grants on schema
GRANT USAGE ON SCHEMA spcs_app_test.napp TO ROLE naspcs_role;
GRANT CREATE TABLE ON SCHEMA spcs_app_test.napp TO ROLE naspcs_role;

-- Grants on existing tables
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA spcs_app_test.napp TO ROLE naspcs_role;

-- Grants on future tables
GRANT SELECT, INSERT, UPDATE, DELETE ON FUTURE TABLES IN SCHEMA spcs_app_test.napp TO ROLE naspcs_role;

-- Grants for Snowflake Cortex (LLM functions)
GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE naspcs_role;

-- Create the warehouse if it doesn't exist
CREATE WAREHOUSE IF NOT EXISTS DEV_WH
    WAREHOUSE_SIZE = 'X-SMALL'
    AUTO_SUSPEND = 60
    AUTO_RESUME = TRUE
    INITIALLY_SUSPENDED = TRUE
    COMMENT = 'Warehouse for local BlendX development';
    
-- Warehouse grant (using separate warehouse for local development)
GRANT USAGE ON WAREHOUSE DEV_WH TO ROLE naspcs_role;

CREATE USER IF NOT EXISTS naspcs_user
  TYPE = SERVICE
  LOGIN_NAME = 'naspcs_user'
  DISPLAY_NAME='naspcs_user'
  DEFAULT_WAREHOUSE='DEV_WH'
  DEFAULT_ROLE='naspcs_role';

-- openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out rsa_key.p8 -nocrypt
-- openssl rsa -in rsa_key.p8 -pubout -out rsa_key.pub
ALTER USER naspcs_user SET RSA_PUBLIC_KEY=''; -- set the key here 

GRANT ROLE naspcs_role TO USER naspcs_user;

-- =============================================================================
-- STEP 2: CREATE TABLES (Run with naspcs_role)
-- =============================================================================

USE ROLE naspcs_role;
USE WAREHOUSE DEV_WH;
USE DATABASE spcs_app_test;
USE SCHEMA napp;

-- -----------------------------------------------------------------------------
-- TABLE DEFINITIONS
-- Source of truth: scripts/sql/tables_definitions.sql
-- Copy the table definitions from that file here, or run it separately
-- -----------------------------------------------------------------------------

-- >>> BEGIN TABLE DEFINITIONS (from scripts/sql/tables_definitions.sql) <<<


-- >>> END TABLE DEFINITIONS <<<



-- =============================================================================
-- STEP 3: VERIFY SETUP
-- =============================================================================

-- Show all tables created
SHOW TABLES IN SCHEMA spcs_app_test.napp;

-- Verify table structure
-- DESCRIBE TABLE crew_execution_results;
-- DESCRIBE TABLE workflows;
-- DESCRIBE TABLE chat_messages;
