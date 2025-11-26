-- ============================================
-- Consumer Role Setup Script
-- This script contains all operations executed by the consumer role (nac_test)
-- Run with: snow sql -f scripts/sql/consumer.sql --connection mkt_blendx_demo
-- ============================================

USE ROLE nac_test;

-- ============================================
-- Step 1: Setup Secret Infrastructure
-- ============================================

-- Create database and schema for secrets
CREATE DATABASE IF NOT EXISTS secrets_db;
CREATE SCHEMA IF NOT EXISTS secrets_db.app_secrets;

-- Create secret (if it doesn't exist)
-- Note: Replace 'PLACEHOLDER_REPLACE_ME' with your actual Serper API key
-- CREATE SECRET IF NOT EXISTS secrets_db.app_secrets.serper_api_key
--   TYPE = GENERIC_STRING
--   SECRET_STRING = 'PLACEHOLDER_REPLACE_ME';

-- Ensure consumer role has proper access to secret
GRANT USAGE ON DATABASE secrets_db TO ROLE nac_test;
GRANT USAGE ON SCHEMA secrets_db.app_secrets TO ROLE nac_test;
GRANT READ ON SECRET secrets_db.app_secrets.serper_api_key TO ROLE nac_test;

-- ============================================
-- Step 2: Create External Access Integration for Serper API
-- ============================================

-- Create network rule for Serper API
CREATE NETWORK RULE IF NOT EXISTS secrets_db.app_secrets.serper_network_rule
  TYPE = HOST_PORT
  VALUE_LIST = ('google.serper.dev')
  MODE = EGRESS;

-- Create external access integration with the secret
CREATE OR REPLACE EXTERNAL ACCESS INTEGRATION serper_access_integration
  ALLOWED_NETWORK_RULES = (secrets_db.app_secrets.serper_network_rule)
  ALLOWED_AUTHENTICATION_SECRETS = (secrets_db.app_secrets.serper_api_key)
  ENABLED = TRUE;

-- ============================================
-- Step 3: Grant Application Package Permissions
-- ============================================

-- Grant REFERENCE_USAGE on database to package (for secret access)
GRANT REFERENCE_USAGE ON DATABASE secrets_db TO SHARE IN APPLICATION PACKAGE spcs_app_pkg_test;

-- ============================================
-- Step 4: Create and Configure Compute Pool
-- ============================================

CREATE COMPUTE POOL IF NOT EXISTS pool_nac
  MIN_NODES = 1
  MAX_NODES = 3
  INSTANCE_FAMILY = CPU_X64_M
  AUTO_RESUME = TRUE;

-- ============================================
-- Step 5: Create or Upgrade Application Instance
-- ============================================

-- Check if application exists, then create or upgrade
-- CREATE APPLICATION IF NOT EXISTS spcs_app_instance_test
--   FROM APPLICATION PACKAGE spcs_app_pkg_test
--   USING VERSION v1
--   COMMENT = 'CrewAI Native Application with Serper search integration';

-- Or to upgrade existing application:
-- ALTER APPLICATION spcs_app_instance_test UPGRADE USING VERSION v1;

-- ============================================
-- Step 6: Grant APP_ADMIN Role
-- ============================================

-- Grant APP_ADMIN role to consumer role for administrative tasks
GRANT APPLICATION ROLE spcs_app_instance_test.APP_ADMIN TO ROLE nac_test;

-- ============================================
-- Step 7: Grant Application Permissions
-- ============================================

-- Grant compute pool usage
GRANT USAGE ON COMPUTE POOL pool_nac
  TO APPLICATION spcs_app_instance_test;

-- Grant warehouse permissions
GRANT USAGE ON WAREHOUSE WH_BLENDX_DEMO_PROVIDER
  TO APPLICATION spcs_app_instance_test;

GRANT OPERATE ON WAREHOUSE WH_BLENDX_DEMO_PROVIDER
  TO APPLICATION spcs_app_instance_test;

-- Grant database and schema access for secrets
GRANT USAGE ON DATABASE secrets_db TO APPLICATION spcs_app_instance_test;
GRANT USAGE ON SCHEMA secrets_db.app_secrets TO APPLICATION spcs_app_instance_test;

-- Grant secret access
GRANT READ ON SECRET secrets_db.app_secrets.serper_api_key TO APPLICATION spcs_app_instance_test;

-- Grant external access integration
GRANT USAGE ON INTEGRATION serper_access_integration TO APPLICATION spcs_app_instance_test;

-- Show references configured in application
SHOW REFERENCES IN APPLICATION spcs_app_instance_test;


-- Start the application (uncomment when ready)
-- CALL spcs_app_instance_test.app_public.start_app('pool_nac', 'WH_BLENDX_DEMO_PROVIDER');

-- Check service status
-- CALL spcs_app_instance_test.app_public.get_service_status();

-- Get application URL
-- CALL spcs_app_instance_test.app_public.app_url();

-- View service logs (last 200 lines)
-- CALL spcs_app_instance_test.app_public.get_service_logs('eap-backend', 200);

-- Stop the application (if needed)
-- CALL spcs_app_instance_test.app_public.stop_app();