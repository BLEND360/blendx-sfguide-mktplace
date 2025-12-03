
USE ROLE nac_test;

CREATE DATABASE IF NOT EXISTS secrets_db;
CREATE SCHEMA IF NOT EXISTS secrets_db.app_secrets;

CREATE OR REPLACE SECRET secrets_db.app_secrets.serper_api_key
  TYPE = GENERIC_STRING
  SECRET_STRING = '{key}'
  COMMENT = 'API key for Serper web search service used by CrewAI application';

GRANT REFERENCE_USAGE ON DATABASE secrets_db
  TO SHARE IN APPLICATION PACKAGE spcs_app_pkg_test;

CREATE NETWORK RULE IF NOT EXISTS secrets_db.app_secrets.serper_network_rule
  TYPE = HOST_PORT
  VALUE_LIST = ('google.serper.dev')
  MODE = EGRESS;

CREATE OR REPLACE EXTERNAL ACCESS INTEGRATION serper_access_integration
  ALLOWED_NETWORK_RULES = (secrets_db.app_secrets.serper_network_rule)
  ALLOWED_AUTHENTICATION_SECRETS = (secrets_db.app_secrets.serper_api_key)
  ENABLED = TRUE;
  
GRANT USAGE ON INTEGRATION serper_access_integration TO ROLE nac_test;


use role accountadmin;
create warehouse WH_BLENDX_DEMO_PROVIDER;

GRANT USAGE ON WAREHOUSE WH_BLENDX_DEMO_PROVIDER TO APPLICATION spcs_app_instance_test;
GRANT USAGE ON WAREHOUSE WH_BLENDX_DEMO_PROVIDER TO ROLE nac_test;

GRANT ROLE NAC_TEST TO ROLE BLENDX_TEAM;
 -------

GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE naspcs_role;
GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO APPLICATION spcs_app_instance_test;

GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE TO APPLICATION spcs_app_instance_test;

