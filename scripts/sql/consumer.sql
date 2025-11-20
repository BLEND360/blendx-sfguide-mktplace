use role accountadmin;
use database spcs_app_test;
use schema napp;

-- ============================================================================
-- Create Secret for Serper API Key
-- ============================================================================
-- Get your API key from: https://serper.dev/dashboard
-- Replace 'YOUR_SERPER_API_KEY_HERE' with your actual key

CREATE OR REPLACE SECRET serper_api_key
  TYPE = GENERIC_STRING
  SECRET_STRING = ''
  COMMENT = 'API key for Serper web search service used by CrewAI application';

SHOW SECRETS;

CREATE NETWORK RULE serper_network_rule
  MODE = EGRESS
  TYPE = HOST_PORT
  VALUE_LIST = ('google.serper.dev:443');

CREATE EXTERNAL ACCESS INTEGRATION serper_external_access
  ALLOWED_NETWORK_RULES = (serper_network_rule)
  ALLOWED_AUTHENTICATION_SECRETS = (serper_api_key)
  ENABLED = TRUE;

SHOW EXTERNAL ACCESS INTEGRATIONS LIKE 'serper_external_access';

GRANT USAGE ON SECRET serper_api_key TO ROLE nac_test;
GRANT USAGE ON INTEGRATION serper_external_access TO ROLE nac_test;

