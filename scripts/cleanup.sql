
--Step 8.1 - Clean Up
--clean up consumer objects
use role nac;
drop application spcs_app_instance;
drop warehouse wh_nac;
drop compute pool pool_nac;
drop database nac_test;

--clean up external access integration
use role accountadmin;
drop integration if exists cortex_rest_eai;
drop network rule if exists cortex_network_rule;

--clean up provider objects
use role naspcs_role;
drop application package spcs_app_pkg;
drop database spcs_app;
drop warehouse wh_nap;

--clean up prep objects
use role accountadmin;
drop role naspcs_role;
drop role nac;
