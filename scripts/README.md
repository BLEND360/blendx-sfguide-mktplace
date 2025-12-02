1. cleanup
2. complete setup 
3. grant cortex 
4. restart 

snow sql -q "USE ROLE nac_test; GRANT USAGE ON INTEGRATION SERPER_ACCESS_INTEGRATION  TO APPLICATION spcs_app_instance_test;" --connection mkt_blendx_demo 
