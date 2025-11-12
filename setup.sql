-- CLI

-- snow connection add --connection-name mkt_blendx_demo \
--     --account c2gpartners.us-east-1 \
--     --user NAHUEL.LARENAS@BLEND360.COM \
--     --role accountadmin \
--     --warehouse wh_nap \
--     --database spcs_app_test \
--     --schema napp \
--     --host c2gpartners.us-east-1.snowflakecomputing.com \
--     --port 443 \
--     --region us-east-1 \
--     --authenticator SNOWFLAKE_JWT \
--     --private-key-file keys/rsa_key.p8 \
--     --no-interactive

-- snow connection test --connection mkt_blendx_demo

-- snow spcs image-registry token --connection mkt_blendx_demo --format=JSON
-- snow spcs image-registry login --connection mkt_blendx_demo

-- # Build and Push backend
--     cd backend
--     docker build --platform linux/amd64 -t eap_backend .
--     cd ..
--     docker tag eap_backend wb19670-c2gpartners.registry.snowflakecomputing.com/spcs_app/napp/img_repo/eap_backend
--     docker push wb19670-c2gpartners.registry.snowflakecomputing.com/spcs_app/napp/img_repo/eap_backend

-- # Build and Push frontend 
--     cd frontend  
--     docker build --platform linux/amd64 -t eap_frontend . 
--     cd ..
--     docker tag eap_frontend wb19670-c2gpartners.registry.snowflakecomputing.com/spcs_app/napp/img_repo/eap_frontend
--     docker push wb19670-c2gpartners.registry.snowflakecomputing.com/spcs_app/napp/img_repo/eap_frontend

-- # Build and Push router
--     cd router 
--     docker build --platform linux/amd64 -t eap_router . 
--     cd ..
--     docker tag eap_router wb19670-c2gpartners.registry.snowflakecomputing.com/spcs_app/napp/img_repo/eap_router
--     docker push wb19670-c2gpartners.registry.snowflakecomputing.com/spcs_app/napp/img_repo/eap_router

// 3
use role accountadmin;
create role if not exists naspcs_role;
grant role naspcs_role to role accountadmin;
grant create integration on account to role naspcs_role;
grant create compute pool on account to role naspcs_role;
grant create warehouse on account to role naspcs_role;
grant create database on account to role naspcs_role;
grant create application package on account to role naspcs_role;
grant create application on account to role naspcs_role with grant option;
grant bind service endpoint on account to role naspcs_role;

use role naspcs_role;
create database if not exists spcs_app_test;
create schema if not exists spcs_app_test.napp;
create stage if not exists spcs_app_test.napp.app_stage;
create image repository if not exists spcs_app_test.napp.img_repo;
-- create warehouse if not exists wh_nap with warehouse_size='xsmall';

// 4

use role accountadmin;
create role if not exists nac_test;
grant role nac_test to role accountadmin;
create warehouse if not exists wh_nac with warehouse_size='xsmall';
grant usage on warehouse wh_nac to role nac_test with grant option;
create database if not exists snowflake_sample_data from share sfc_samples.sample_data;
grant imported privileges on database snowflake_sample_data to role nac_test;
grant create database on account to role nac_test;
grant bind service endpoint on account to role nac_test with grant option;
grant create compute pool on account to role nac_test;
grant create application on account to role nac_test;

use role nac_test;
create database if not exists nac_test_db;
create schema if not exists nac_test_db.data;
use schema nac_test_db.data;

use role naspcs_role;
show image repositories in schema spcs_app.napp;

-- Create External Access Integration for Snowflake API access
use role accountadmin;
CREATE OR REPLACE NETWORK RULE snowflake_api_network_rule
  MODE = EGRESS
  TYPE = HOST_PORT
  VALUE_LIST = ('*.snowflakecomputing.com:443');

CREATE OR REPLACE EXTERNAL ACCESS INTEGRATION snowflake_api_access_integration
  ALLOWED_NETWORK_RULES = (snowflake_api_network_rule)
  ENABLED = true;

GRANT USAGE ON INTEGRATION snowflake_api_access_integration TO ROLE naspcs_role;

use role naspcs_role;
create application package spcs_app_pkg_test;
alter application package spcs_app_pkg_test register version v1 using @spcs_app_test.napp.app_stage;
alter application package spcs_app_pkg_test modify release channel default add version v1;
grant install, develop on application package spcs_app_pkg_test to role nac_test;

use role nac_test;
create application spcs_app_instance_test from application package spcs_app_pkg_test using version v1;

use database nac_test_db;
use role nac_test;
create  compute pool pool_nac for application spcs_app_instance_test
    min_nodes = 1 max_nodes = 1
    instance_family = cpu_x64_s
    auto_resume = true;

grant usage on compute pool pool_nac to application spcs_app_instance_test;
grant usage on warehouse wh_nac to application spcs_app_instance_test;
grant bind service endpoint on account to application spcs_app_instance_test;

call spcs_app_instance_test.app_public.start_app('POOL_NAC', 'WH_NAC');

--After running the above command you can run the following command to determine when the Service Endpoint is ready 
--Copy the endpoint, paste into a browser, and authenticate to the Snowflake account using the same credentials you've been using to log into Snowflake
call spcs_app_instance_test.app_public.app_url();
