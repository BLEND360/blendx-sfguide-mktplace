-- Associate the External Access Integration reference with the application
-- Run this AFTER creating the external access integration and BEFORE starting the app

-- First verify the integration exists and re-grant if needed
use role accountadmin;
show integrations like 'cortex_rest_eai';

-- Make sure the application has access
grant usage on integration cortex_rest_eai to application spcs_app_instance_test;

-- Stay as accountadmin to associate the reference
-- The callback needs to be executed with sufficient privileges

-- Call the register callback to associate the reference CORTEX_REST_EAI with the actual integration
-- The callback procedure handles the system$set_reference call
-- The third parameter should match the integration name exactly as created
call spcs_app_instance_test.v1.register_external_access('CORTEX_REST_EAI', 'ADD', 'CORTEX_REST_EAI');
