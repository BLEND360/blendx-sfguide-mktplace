#!/bin/bash

# Deployment script for Snowflake Native App with SPCS
# This script automates the entire deployment process

set -e  # Exit on error

# Configuration
CONNECTION="mkt_blendx_demo"
SNOWFLAKE_REPO="wb19670-c2gpartners.registry.snowflakecomputing.com/spcs_app/napp/img_repo"
BACKEND_IMAGE="eap_backend"
FRONTEND_IMAGE="eap_frontend"
ROUTER_IMAGE="eap_router"

echo "=========================================="
echo "Starting Snowflake Native App Deployment"
echo "=========================================="

# Step 1: Build Docker images
echo ""
echo "[1/8] Building Docker images..."
echo "Building backend..."
cd backend
docker build --platform linux/amd64 -t ${BACKEND_IMAGE} .
cd ..

echo "Building frontend..."
cd frontend
docker build --platform linux/amd64 -t ${FRONTEND_IMAGE} .
cd ..

echo "Building router..."
cd router
docker build --platform linux/amd64 -t ${ROUTER_IMAGE} .
cd ..

# Step 2: Login to Snowflake Docker registry
echo ""
echo "[2/8] Logging in to Snowflake Docker registry..."
snow spcs image-registry token --connection ${CONNECTION} --format=JSON
snow spcs image-registry login --connection ${CONNECTION}  
docker login ${SNOWFLAKE_REPO}

# Step 3: Tag and push images
echo ""
echo "[3/8] Tagging and pushing images..."
echo "Pushing backend..."
docker tag ${BACKEND_IMAGE} ${SNOWFLAKE_REPO}/${BACKEND_IMAGE}
docker push ${SNOWFLAKE_REPO}/${BACKEND_IMAGE}

echo "Pushing frontend..."
docker tag ${FRONTEND_IMAGE} ${SNOWFLAKE_REPO}/${FRONTEND_IMAGE}
docker push ${SNOWFLAKE_REPO}/${FRONTEND_IMAGE}

echo "Pushing router..."
docker tag ${ROUTER_IMAGE} ${SNOWFLAKE_REPO}/${ROUTER_IMAGE}
docker push ${SNOWFLAKE_REPO}/${ROUTER_IMAGE}

# Step 4: Upload application files to Snowflake stage
echo ""
echo "[4/8] Uploading application files to Snowflake stage..."
snow sql -q "PUT file:///Users/mikaelapisani/Projects/blendx-sfguide-mktplace/app/src/* @spcs_app_test.napp.app_stage AUTO_COMPRESS=FALSE OVERWRITE=TRUE;" --connection ${CONNECTION} 

# Step 5: Remove old version from release channel
echo ""
echo "[5/8] Removing old version from release channel..."
snow sql -q "USE ROLE naspcs_role; ALTER APPLICATION PACKAGE spcs_app_pkg_test MODIFY RELEASE CHANNEL default DROP VERSION v1;" \
  --connection ${CONNECTION} || echo "Version v1 not in channel (OK)"

# Step 6: Drop old version
echo ""
echo "[6/8] Dropping old version..."
snow sql -q "USE ROLE naspcs_role; ALTER APPLICATION PACKAGE spcs_app_pkg_test DEREGISTER VERSION v1;" \
  --connection ${CONNECTION} || echo "Version v1 doesn't exist (OK)"

# Step 7: Register new version
echo ""
echo "[7/8] Registering new version v1..."
snow sql -q "USE ROLE naspcs_role; ALTER APPLICATION PACKAGE spcs_app_pkg_test REGISTER VERSION v1 USING @spcs_app_test.napp.app_stage;" \
  --connection ${CONNECTION}

snow sql -q "USE ROLE naspcs_role; ALTER APPLICATION PACKAGE spcs_app_pkg_test MODIFY RELEASE CHANNEL default ADD VERSION v1;" \
  --connection ${CONNECTION}

# Step 8: Upgrade application
echo ""
echo "[8/8] Upgrading application..."
snow sql -q "USE ROLE nac_test; ALTER APPLICATION spcs_app_instance_test UPGRADE USING VERSION v1;" \
  --connection ${CONNECTION}

# Step 9: Restart service
echo ""
echo "[9/9] Restarting service..."
snow sql -q "USE ROLE nac_test; CALL spcs_app_instance_test.app_public.stop_app();" \
  --connection ${CONNECTION} || echo "Service not running (OK)"

snow sql -q "USE ROLE nac_test; CALL spcs_app_instance_test.app_public.start_app('POOL_NAC', 'WH_NAC');" \
  --connection ${CONNECTION}

# Wait for service to start
echo ""
echo "Waiting 30 seconds for service to start..."
sleep 30

# Check service status
echo ""
echo "=========================================="
echo "Checking service status..."
echo "=========================================="
snow sql -q "USE ROLE nac_test; SHOW SERVICES IN APPLICATION spcs_app_instance_test;" \
  --connection ${CONNECTION}

# Get service URL
echo ""
echo "=========================================="
echo "Getting application URL..."
echo "=========================================="
snow sql -q "USE ROLE nac_test; CALL spcs_app_instance_test.app_public.app_url();" \
  --connection ${CONNECTION}

echo ""
echo "=========================================="
echo "Deployment completed successfully!"
echo "=========================================="
echo ""
echo "To view logs, run:"
echo "  snow sql -q \"USE ROLE nac_test; CALL spcs_app_instance_test.app_public.get_service_logs('eap-backend', 200);\" --connection ${CONNECTION}"
echo ""
echo "To check status, run:"
echo "  snow sql -q \"USE ROLE nac_test; CALL spcs_app_instance_test.app_public.get_service_status();\" --connection ${CONNECTION}"
echo ""