use role accountadmin;

-- Create a schema for network rules if it doesn't exist
use schema spcs_app_test.napp;

create or replace network rule cortex_network_rule
  mode = egress
  type = host_port
  value_list = ('*.snowflakecomputing.com');

create or replace external access integration cortex_rest_eai
  allowed_network_rules = (spcs_app_test.napp.cortex_network_rule)
  enabled = true;

-- Grant usage to the consumer role
grant usage on integration cortex_rest_eai to role nac;

-- Grant usage to the application
grant usage on integration cortex_rest_eai to application spcs_app_instance_test;
