# 1. Upload files 
snow object stage copy ./app/src/setup.sql @spcs_app_test.napp.app_stage --connection mkt_blendx_demo --overwrite

# 2. Check service status
snow sql -q "USE ROLE BLENDX_APP_ROLE; CALL spcs_app_instance_test.app_public.get_service_status();" --connection mkt_blendx_demo

# 3. Check backend logs
snow sql -q "USE ROLE BLENDX_APP_ROLE; CALL spcs_app_instance_test.app_public.get_service_logs('eap-backend', 200);" --connection mkt_blendx_demo

# 4. Check frontend logs
snow sql -q "USE ROLE BLENDX_APP_ROLE; CALL spcs_app_instance_test.app_public.get_service_logs('eap-frontend', 100);" --connection mkt_blendx_demo

# 5. Check router logs
snow sql -q "USE ROLE BLENDX_APP_ROLE; CALL spcs_app_instance_test.app_public.get_service_logs('eap-router', 100);" --connection mkt_blendx_demo

# 6. Get URL 
snow sql -q "USE ROLE BLENDX_APP_ROLE; CALL spcs_app_instance_test.app_public.app_url();" --connection mkt_blendx_demo
