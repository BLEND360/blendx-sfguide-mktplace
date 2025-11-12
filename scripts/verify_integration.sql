-- Verify if the integration was created successfully
use role accountadmin;

-- Check if the database and schema exist
show databases like 'spcs_app_test';
show schemas like 'napp' in database spcs_app_test;

-- Check if the network rule exists
use schema spcs_app_test.napp;
show network rules;

-- Check if the integration exists
show integrations like 'cortex_rest_eai';

-- Show all external access integrations
show external access integrations;
