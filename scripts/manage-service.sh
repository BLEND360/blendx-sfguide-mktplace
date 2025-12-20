#!/bin/bash

# Configuration - can be overridden via environment variables
ROLE="${SNOWFLAKE_ROLE:-BLENDX_APP_ROLE}"
APP_INSTANCE="${SNOWFLAKE_APP_INSTANCE:-BLENDX_APP_INSTANCE}"
COMPUTE_POOL="${SNOWFLAKE_COMPUTE_POOL:-BLENDX_CP}"
CONNECTION="${SNOWFLAKE_CONNECTION:-mkt_blendx_demo}"

echo "============================================"
echo "Managing SPCS Service"
echo "============================================"
echo "Role: $ROLE"
echo "App Instance: $APP_INSTANCE"
echo "Compute Pool: $COMPUTE_POOL"
echo ""

# Check if service exists and its status
echo "Checking if service exists..."
SERVICE_OUTPUT=$(snow sql -q "USE ROLE $ROLE; SHOW SERVICES IN APPLICATION $APP_INSTANCE;" --connection $CONNECTION 2>&1)
SERVICE_EXISTS=$(echo "$SERVICE_OUTPUT" | grep -i "blendx_st_spcs" | wc -l | tr -d ' ' || echo "0")

if [ "$SERVICE_EXISTS" -gt "0" ]; then
    # Check if service is suspended
    SERVICE_STATUS=$(echo "$SERVICE_OUTPUT" | grep -i "blendx_st_spcs" | grep -i "SUSPENDED" | wc -l | tr -d ' ' || echo "0")

    if [ "$SERVICE_STATUS" -gt "0" ]; then
        echo "Service is suspended. Resuming with resume_app()..."
        snow sql -q "USE ROLE $ROLE; CALL $APP_INSTANCE.app_public.resume_app();" --connection $CONNECTION
    else
        echo "Service exists and is running. Using ALTER SERVICE with FORCE_PULL_IMAGE to pull new images..."
        snow sql -q "USE ROLE $ROLE; ALTER SERVICE $APP_INSTANCE.app_public.blendx_st_spcs FROM SPECIFICATION_FILE='/fullstack.yaml' FORCE_PULL_IMAGE = TRUE;" --connection $CONNECTION
    fi
else
    echo "Service does not exist. Starting fresh with start_app()..."
    snow sql -q "USE ROLE $ROLE; CALL $APP_INSTANCE.app_public.start_app('$COMPUTE_POOL');" --connection $CONNECTION
fi

echo ""
echo "Waiting 30 seconds for service to start..."
sleep 30

echo ""
echo "Checking service status..."
snow sql -q "USE ROLE $ROLE; CALL $APP_INSTANCE.app_public.get_service_status();" --connection $CONNECTION

echo ""
echo "Getting application URL..."
snow sql -q "USE ROLE $ROLE; CALL $APP_INSTANCE.app_public.app_url();" --connection $CONNECTION
