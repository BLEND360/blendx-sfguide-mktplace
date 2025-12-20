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

echo "Service query output:"
echo "$SERVICE_OUTPUT"
echo ""

# Check if output contains "0 Row" (no services) or error
if echo "$SERVICE_OUTPUT" | grep -q "0 Row"; then
    echo "Service does not exist. Starting fresh with start_app()..."
    snow sql -q "USE ROLE $ROLE; CALL $APP_INSTANCE.app_public.start_app('$COMPUTE_POOL');" --connection $CONNECTION
elif echo "$SERVICE_OUTPUT" | grep -qi "error\|failed"; then
    echo "Error querying services. Attempting start_app()..."
    snow sql -q "USE ROLE $ROLE; CALL $APP_INSTANCE.app_public.start_app('$COMPUTE_POOL');" --connection $CONNECTION
else
    # Service exists - check if suspended
    if echo "$SERVICE_OUTPUT" | grep -qi "SUSPENDED"; then
        echo "Service is suspended. Resuming with resume_app()..."
        snow sql -q "USE ROLE $ROLE; CALL $APP_INSTANCE.app_public.resume_app();" --connection $CONNECTION
    else
        echo "Service exists and is running. Updating service specification..."
        # Update service from specification file to pull new images
        snow sql -q "USE ROLE $ROLE; ALTER SERVICE $APP_INSTANCE.app_public.blendx_st_spcs FROM SPECIFICATION_FILE='/fullstack.yaml';" --connection $CONNECTION
    fi
fi

echo ""
echo "Checking service status..."
snow sql -q "USE ROLE $ROLE; CALL $APP_INSTANCE.app_public.get_service_status();" --connection $CONNECTION

