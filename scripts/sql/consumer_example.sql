-- ============================================================================
-- BlendX Consumer Setup Script - COMPLETE EXAMPLE
-- ============================================================================
-- This is a complete example showing all steps with actual values.
-- Copy this file and replace the placeholder values with your actual values.
-- ============================================================================

-- Replace these values:
-- <YOUR_ROLE>            
-- <YOUR_SERPER_API_KEY>  Get from https://serper.dev
-- <APP_PACKAGE_NAME>     e.g., BLENDX_PACKAGE
-- <APP_INSTANCE_NAME>    e.g., BLENDX_APP
-- <COMPUTE_POOL_NAME>    e.g., BLENDX_POOL

USE ROLE nac_test;  -- Or your role with sufficient privileges

-- ============================================================================
-- Step 1: Create Secret with Serper API Key
-- ============================================================================

-- Create database and schema for secrets
CREATE DATABASE IF NOT EXISTS secrets_db;
CREATE SCHEMA IF NOT EXISTS secrets_db.app_secrets;

-- Create secret with Serper API key (get from https://serper.dev)
CREATE OR REPLACE SECRET secrets_db.app_secrets.serper_api_key
  TYPE = GENERIC_STRING
  SECRET_STRING = '{your api key}'  -- Replace!
  COMMENT = 'API key for Serper web search service used by CrewAI application';

-- Grant reference usage so the app can use the secret
GRANT REFERENCE_USAGE ON DATABASE secrets_db
  TO APPLICATION PACKAGE BLENDX_PACKAGE;  -- Replace with your package name!

