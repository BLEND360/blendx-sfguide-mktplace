                          
#!/bin/bash

echo "Stopping service..."
snow sql -q "USE ROLE nac_test; CALL spcs_app_instance_test.app_public.stop_app();" --connection mkt_blendx_demo

echo "Starting service..."
snow sql -q "USE ROLE nac_test; CALL spcs_app_instance_test.app_public.start_app('pool_nac');" --connection mkt_blendx_demo

sleep 30

echo "Get url.."
snow sql -q "USE ROLE nac_test; CALL spcs_app_instance_test.app_public.app_url();"   --connection mkt_blendx_demo