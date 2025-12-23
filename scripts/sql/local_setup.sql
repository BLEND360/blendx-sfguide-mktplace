-- =============================================================================
-- BlendX Local Development Setup
-- Script to create all necessary tables and grants for local development
-- This simulates a CONSUMER environment where the app would be installed.
-- =============================================================================

-- =============================================================================
-- CONFIGURATION
-- =============================================================================
-- DATABASE: BLENDX_APP_DEV_DB (separate database for local development)
-- SCHEMA: APP_DATA (where the app stores consumer data)
-- ROLE: BLENDX_APP_DEV_ROLE (role for local development)
-- USER: BLENDX_APP_DEV_USER (optional service user for local dev)
-- WAREHOUSE: BLENDX_APP_DEV_WH (separate warehouse for local development)
-- =============================================================================
-- TODO - validate
-- =============================================================================
-- STEP 1: CREATE DATABASE AND SCHEMA (Run with ACCOUNTADMIN)
-- =============================================================================

USE ROLE ACCOUNTADMIN;

-- Create separate database for local development (simulates consumer account)
CREATE DATABASE IF NOT EXISTS BLENDX_APP_DEV_DB
    COMMENT = 'Local development database - simulates consumer environment';

-- Create the APP_DATA schema for consumer data
CREATE SCHEMA IF NOT EXISTS BLENDX_APP_DEV_DB.APP_DATA
    COMMENT = 'Schema for app data - simulates consumer app_data schema';

-- =============================================================================
-- STEP 2: CREATE ROLE AND GRANTS (Run with ACCOUNTADMIN)
-- =============================================================================

-- Create role for local development
CREATE ROLE IF NOT EXISTS BLENDX_APP_DEV_ROLE
    COMMENT = 'Role for local development of BlendX app';

-- Grants on database
GRANT USAGE ON DATABASE BLENDX_APP_DEV_DB TO ROLE BLENDX_APP_DEV_ROLE;

-- Grants on APP_DATA schema
GRANT USAGE ON SCHEMA BLENDX_APP_DEV_DB.APP_DATA TO ROLE BLENDX_APP_DEV_ROLE;
GRANT CREATE TABLE ON SCHEMA BLENDX_APP_DEV_DB.APP_DATA TO ROLE BLENDX_APP_DEV_ROLE;

-- Grants on existing tables
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA BLENDX_APP_DEV_DB.APP_DATA TO ROLE BLENDX_APP_DEV_ROLE;

-- Grants on future tables
GRANT SELECT, INSERT, UPDATE, DELETE ON FUTURE TABLES IN SCHEMA BLENDX_APP_DEV_DB.APP_DATA TO ROLE BLENDX_APP_DEV_ROLE;

-- Grants for Snowflake Cortex (LLM functions)
GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE BLENDX_APP_DEV_ROLE;

-- Create the warehouse if it doesn't exist
CREATE WAREHOUSE IF NOT EXISTS BLENDX_APP_DEV_WH
    WAREHOUSE_SIZE = 'X-SMALL'
    AUTO_SUSPEND = 60
    AUTO_RESUME = TRUE
    INITIALLY_SUSPENDED = TRUE
    COMMENT = 'Warehouse for local BlendX development';

-- Warehouse grant
GRANT USAGE ON WAREHOUSE BLENDX_APP_DEV_WH TO ROLE BLENDX_APP_DEV_ROLE;

-- =============================================================================
-- STEP 3: CREATE SERVICE USER (Optional - for JWT auth in local dev)
-- =============================================================================

CREATE USER IF NOT EXISTS BLENDX_APP_DEV_USER
    TYPE = SERVICE
    LOGIN_NAME = 'BLENDX_APP_DEV_USER'
    DISPLAY_NAME = 'BLENDX_APP_DEV_USER'
    DEFAULT_WAREHOUSE = 'BLENDX_APP_DEV_WH'
    DEFAULT_ROLE = 'BLENDX_APP_DEV_ROLE'
    COMMENT = 'Service user for local BlendX development';

-- To use JWT authentication, generate keys and set the public key:
-- openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out rsa_key.p8 -nocrypt
-- openssl rsa -in rsa_key.p8 -pubout -out rsa_key.pub
-- Then uncomment and set the key:
-- ALTER USER BLENDX_APP_DEV_USER SET RSA_PUBLIC_KEY='<paste-public-key-without-headers>';

GRANT ROLE BLENDX_APP_DEV_ROLE TO USER BLENDX_APP_DEV_USER;

-- Grant role to your personal user as well (replace YOUR_USERNAME)
-- GRANT ROLE BLENDX_APP_DEV_ROLE TO USER YOUR_USERNAME;

-- =============================================================================
-- STEP 4: CREATE TABLES (Run with BLENDX_APP_DEV_ROLE)
-- =============================================================================

USE ROLE BLENDX_APP_DEV_ROLE;
USE WAREHOUSE BLENDX_APP_DEV_WH;
USE DATABASE BLENDX_APP_DEV_DB;
USE SCHEMA APP_DATA;

-- -----------------------------------------------------------------------------
-- TABLE DEFINITIONS
-- Source of truth: scripts/sql/tables_definitions.sql
-- Copy the table definitions from that file here, or run it separately
-- -----------------------------------------------------------------------------

-- >>> BEGIN TABLE DEFINITIONS (from scripts/sql/tables_definitions.sql) <<<


-- >>> END TABLE DEFINITIONS <<<



-- =============================================================================
-- STEP 5: VERIFY SETUP
-- =============================================================================

-- Show all tables created
SHOW TABLES IN SCHEMA BLENDX_APP_DEV_DB.APP_DATA;

-- Verify table structure
-- DESCRIBE TABLE crew_execution_results;
-- DESCRIBE TABLE workflows;
-- DESCRIBE TABLE chat_messages;

-- =============================================================================
-- ENVIRONMENT VARIABLES FOR docker-compose
-- =============================================================================
-- Copy these to your .env file:
--
-- SNOWFLAKE_ACCOUNT=<your-account>
-- SNOWFLAKE_USER=<your-username-or-BLENDX_APP_DEV_USER>
-- SNOWFLAKE_DATABASE=BLENDX_APP_DEV_DB
-- SNOWFLAKE_SCHEMA=APP_DATA
-- SNOWFLAKE_WAREHOUSE=BLENDX_APP_DEV_WH
-- SNOWFLAKE_ROLE=BLENDX_APP_DEV_ROLE
-- =============================================================================
