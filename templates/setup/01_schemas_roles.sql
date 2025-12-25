-- =============================================================================
-- SCHEMAS AND ROLES SETUP
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS config;
CREATE APPLICATION ROLE IF NOT EXISTS app_admin;
CREATE APPLICATION ROLE IF NOT EXISTS app_user;
CREATE SCHEMA IF NOT EXISTS app_public;
GRANT USAGE ON SCHEMA config TO APPLICATION ROLE app_admin;

GRANT USAGE ON SCHEMA app_public TO APPLICATION ROLE app_admin;
GRANT USAGE ON SCHEMA app_public TO APPLICATION ROLE app_user;
CREATE OR ALTER VERSIONED SCHEMA v1;
GRANT USAGE ON SCHEMA v1 TO APPLICATION ROLE app_admin;

-- Network rule and External Access Integration are created in start_application() procedure
-- after the application has been granted CREATE EXTERNAL ACCESS INTEGRATION privilege

-- Create schema for application data
CREATE SCHEMA IF NOT EXISTS app_data;
GRANT USAGE ON SCHEMA app_data TO APPLICATION ROLE app_admin;
GRANT USAGE ON SCHEMA app_data TO APPLICATION ROLE app_user;
