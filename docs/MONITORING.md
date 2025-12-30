# Check service status
snow sql -q "USE ROLE BLENDX_APP_ROLE; CALL BLENDX_APP_INSTANCE_QA.app_public.get_service_status();" --connection mkt_blendx_demo

# Check backend logs
snow sql -q "USE ROLE BLENDX_APP_ROLE; CALL BLENDX_APP_INSTANCE_QA.app_public.get_service_logs('eap-backend', 200);" --connection mkt_blendx_demo

# Check frontend logs
snow sql -q "USE ROLE BLENDX_APP_ROLE; CALL BLENDX_APP_INSTANCE_QA.app_public.get_service_logs('eap-frontend', 100);" --connection mkt_blendx_demo

# Check router logs
snow sql -q "USE ROLE BLENDX_APP_ROLE; CALL BLENDX_APP_INSTANCE_QA.app_public.get_service_logs('eap-router', 100);" --connection mkt_blendx_demo

# Get URL
snow sql -q "USE ROLE BLENDX_APP_ROLE; CALL BLENDX_APP_INSTANCE_QA.app_public.app_url();" --connection mkt_blendx_demo
