#!/bin/bash
set -e

# Configuration
ROLE="${SNOWFLAKE_ROLE:-BLENDX_APP_ROLE}"
APP_INSTANCE="${SNOWFLAKE_APP_INSTANCE:-BLENDX_APP_INSTANCE}"
CONNECTION="${SNOWFLAKE_CONNECTION:-mkt_blendx_demo}"
MAX_ATTEMPTS="${MAX_ATTEMPTS:-20}"
INITIAL_WAIT="${INITIAL_WAIT:-10}"

echo "============================================"
echo "Waiting for service to be ready"
echo "============================================"
echo "App Instance: $APP_INSTANCE"
echo "Max attempts: $MAX_ATTEMPTS"
echo ""

attempt=1
wait_time=$INITIAL_WAIT

while [ $attempt -le $MAX_ATTEMPTS ]; do
    echo "Attempt $attempt/$MAX_ATTEMPTS (waiting ${wait_time}s)..."

    # Get service status as JSON
    STATUS_OUTPUT=$(snow sql -q "USE ROLE $ROLE; CALL $APP_INSTANCE.app_public.get_service_status();" \
        --connection $CONNECTION 2>&1) || true

    # Check for READY status
    if echo "$STATUS_OUTPUT" | grep -qi "READY"; then
        echo ""
        echo "Service is READY"
        echo "$STATUS_OUTPUT"
        exit 0
    fi

    # Check for RUNNING status (also acceptable)
    if echo "$STATUS_OUTPUT" | grep -qi "RUNNING"; then
        echo ""
        echo "Service is RUNNING"
        echo "$STATUS_OUTPUT"
        exit 0
    fi

    # Check for failure states
    if echo "$STATUS_OUTPUT" | grep -qiE "FAILED|ERROR"; then
        echo ""
        echo "ERROR: Service failed to start"
        echo "$STATUS_OUTPUT"
        exit 1
    fi

    # Show current status
    CURRENT_STATUS=$(echo "$STATUS_OUTPUT" | grep -oE "(PENDING|STARTING|SUSPENDING|SUSPENDED|READY|RUNNING)" | head -1 || echo "UNKNOWN")
    echo "  Current status: $CURRENT_STATUS"

    sleep $wait_time

    # Exponential backoff: 10, 15, 22, 33, 50... capped at 60
    wait_time=$((wait_time * 3 / 2))
    if [ $wait_time -gt 60 ]; then
        wait_time=60
    fi

    attempt=$((attempt + 1))
done

echo ""
echo "ERROR: Timeout waiting for service to be ready after $MAX_ATTEMPTS attempts"
exit 1
