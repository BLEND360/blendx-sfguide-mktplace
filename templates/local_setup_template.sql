-- =============================================================================
-- BlendX Local Development Setup Template
-- =============================================================================
-- This template creates all necessary Snowflake resources for local development.
-- It simulates a CONSUMER environment where the app would be installed.
--
-- USAGE:
--   1. Run the generator script:
--      python scripts/generate/generate_local_setup.py \
--        --database MY_DEV_DB \
--        --schema APP_DATA \
--        --role MY_DEV_ROLE \
--        --user MY_USER \
--        --warehouse MY_DEV_WH
--
--   2. Execute in Snowflake:
--      snow sql -f local_setup.sql --connection <your_connection>
--
--   To update an existing local DB with new migrations only:
--      snow sql -f local_migrations.sql --connection <your_connection>
--
-- =============================================================================

-- =============================================================================
-- STEP 1: CREATE DATABASE AND SCHEMA (Run with ACCOUNTADMIN)
-- =============================================================================

USE ROLE ACCOUNTADMIN;

-- Create separate database for local development (simulates consumer account)
CREATE DATABASE IF NOT EXISTS {{DATABASE}}
    COMMENT = 'Local development database - simulates consumer environment';

-- Create the schema for consumer data
CREATE SCHEMA IF NOT EXISTS {{DATABASE}}.{{SCHEMA}}
    COMMENT = 'Schema for app data - simulates consumer app_data schema';

-- =============================================================================
-- STEP 2: CREATE ROLE AND GRANTS (Run with ACCOUNTADMIN)
-- =============================================================================

-- Create role for local development
CREATE ROLE IF NOT EXISTS {{ROLE}}
    COMMENT = 'Role for local development of BlendX app';

GRANT ROLE {{ROLE}} TO ROLE BLENDX_TEAM;

-- Grants on database
GRANT USAGE ON DATABASE {{DATABASE}} TO ROLE {{ROLE}};

-- Grants on schema
GRANT USAGE ON SCHEMA {{DATABASE}}.{{SCHEMA}} TO ROLE {{ROLE}};
GRANT CREATE TABLE ON SCHEMA {{DATABASE}}.{{SCHEMA}} TO ROLE {{ROLE}};

-- Grants on existing tables
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA {{DATABASE}}.{{SCHEMA}} TO ROLE {{ROLE}};

-- Grants on future tables
GRANT SELECT, INSERT, UPDATE, DELETE ON FUTURE TABLES IN SCHEMA {{DATABASE}}.{{SCHEMA}} TO ROLE {{ROLE}};

-- Grants for Snowflake Cortex (LLM functions)
GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE {{ROLE}};

-- Create the warehouse if it doesn't exist
CREATE WAREHOUSE IF NOT EXISTS {{WAREHOUSE}}
    WAREHOUSE_SIZE = 'X-SMALL'
    AUTO_SUSPEND = 60
    AUTO_RESUME = TRUE
    INITIALLY_SUSPENDED = TRUE
    COMMENT = 'Warehouse for local BlendX development';

-- Warehouse grant
GRANT USAGE ON WAREHOUSE {{WAREHOUSE}} TO ROLE {{ROLE}};


-- =============================================================================
-- STEP 3: CREATE SERVICE USER WITH JWT AUTH
-- =============================================================================
-- The backend uses JWT authentication with a service user.
-- If keys/rsa_key.pub exists, a service user is automatically created.
--
-- To generate RSA keys (if not already present):
--   mkdir -p keys
--   openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out keys/rsa_key.p8 -nocrypt
--   openssl rsa -in keys/rsa_key.p8 -pubout -out keys/rsa_key.pub
-- =============================================================================

{{SERVICE_USER_SQL}}

-- =============================================================================
-- SETUP COMPLETE
-- =============================================================================
-- Next steps:
--   1. Run this script to create the infrastructure
--   2. Generate migrations: cd backend && alembic revision --autogenerate -m "initial"
--   3. Generate SQL: python scripts/generate/generate_migrations_sql.py
--   4. Apply migrations: snow sql -f scripts/generated/local_migrations.sql --connection <your_connection>
--
-- ENVIRONMENT VARIABLES FOR docker-compose / .env file:
-- SNOWFLAKE_ACCOUNT=<your-account>
-- SNOWFLAKE_USER={{USER}}
-- SNOWFLAKE_DATABASE={{DATABASE}}
-- SNOWFLAKE_SCHEMA={{SCHEMA}}
-- SNOWFLAKE_WAREHOUSE={{WAREHOUSE}}
-- SNOWFLAKE_ROLE={{ROLE}}
-- SNOWFLAKE_PRIVATE_KEY_PATH=keys/rsa_key.p8
-- =============================================================================
