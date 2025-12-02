# 1. Upload files 
snow object stage copy ./app/src/setup.sql @spcs_app_test.napp.app_stage --connection mkt_blendx_demo --overwrite

# 2. Delete and recreate package
snow sql -q "USE ROLE naspcs_role; ALTER APPLICATION PACKAGE spcs_app_pkg_test MODIFY RELEASE CHANNEL default DROP VERSION v1;" --connection mkt_blendx_demo

snow sql -q "USE ROLE naspcs_role; ALTER APPLICATION PACKAGE spcs_app_pkg_test DROP VERSION v1;" --connection mkt_blendx_demo

snow sql -q "USE ROLE naspcs_role; ALTER APPLICATION PACKAGE spcs_app_pkg_test REGISTER VERSION v1 USING @spcs_app_test.napp.app_stage;" --connection mkt_blendx_demo

snow sql -q "USE ROLE naspcs_role; ALTER APPLICATION PACKAGE spcs_app_pkg_test MODIFY RELEASE CHANNEL default ADD VERSION v1;" --connection mkt_blendx_demo

snow sql -q "USE ROLE nac_test; ALTER APPLICATION spcs_app_instance_test UPGRADE USING VERSION v1;" --connection mkt_blendx_demo

# 3. Check service status
snow sql -q "USE ROLE nac_test; CALL spcs_app_instance_test.app_public.get_service_status();" --connection mkt_blendx_demo

# 4. Check backend logs
snow sql -q "USE ROLE nac_test; CALL spcs_app_instance_test.app_public.get_service_logs('eap-backend', 200);" --connection mkt_blendx_demo

# 5. Check frontend logs
snow sql -q "USE ROLE nac_test; CALL spcs_app_instance_test.app_public.get_service_logs('eap-frontend', 100);" --connection mkt_blendx_demo

# 6. Check router logs
snow sql -q "USE ROLE nac_test; CALL spcs_app_instance_test.app_public.get_service_logs('eap-router', 100);" --connection mkt_blendx_demo

# 7. Get URL 
snow sql -q "USE ROLE nac_test; CALL spcs_app_instance_test.app_public.app_url(); " --connection mkt_blendx_demo
