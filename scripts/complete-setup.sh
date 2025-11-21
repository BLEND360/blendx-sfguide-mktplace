#!/bin/bash

# Complete Setup Script for Snowflake Native App
# This script performs a full deployment from scratch including:
# - Application Package creation
# - Permission grants
# - Secret setup
# - Application deployment
# - Service startup

set -e  # Exit on error

# ============================================
# Script Setup
# ============================================

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ============================================
# Load Configuration
# ============================================

SNOW_CONNECTION=${SNOW_CONNECTION:-"mkt_blendx_demo"}
APP_PROVIDER_ROLE=${APP_PROVIDER_ROLE:-"naspcs_role"}
APP_CONSUMER_ROLE=${APP_CONSUMER_ROLE:-"nac_test"}
APP_PACKAGE_NAME=${APP_PACKAGE_NAME:-"spcs_app_pkg_test"}
APP_INSTANCE_NAME=${APP_INSTANCE_NAME:-"spcs_app_instance_test"}
APP_VERSION=${APP_VERSION:-"v1"}
COMPUTE_POOL=${COMPUTE_POOL:-"pool_nac"}
WAREHOUSE=${WAREHOUSE:-"WH_BLENDX_DEMO_PROVIDER"}
SECRET_DATABASE=${SECRET_DATABASE:-"secrets_db"}
SECRET_SCHEMA=${SECRET_SCHEMA:-"app_secrets"}
SECRET_NAME=${SECRET_NAME:-"serper_api_key"}
DATABASE=spcs_app_test
SCHEMA=napp

# Load .env file if it exists
if [ -f "$SCRIPT_DIR/.env" ]; then
    echo -e "${BLUE}Loading configuration from .env file...${NC}"
    source "$SCRIPT_DIR/.env"
fi

# ============================================
# Helper Functions
# ============================================

log_step() {
    echo ""
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}========================================${NC}"
}

log_info() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

run_sql() {
    local description=$1
    local sql=$2
    echo -e "${BLUE}▶${NC} $description"
    snow sql -q "$sql" --connection ${SNOW_CONNECTION}
}

# ============================================
# Display Configuration
# ============================================

echo ""
echo "=========================================="
echo "Complete Snowflake Native App Setup"
echo "=========================================="
echo ""
echo "Configuration:"
echo "  Connection: $SNOW_CONNECTION"
echo "  Provider Role: $APP_PROVIDER_ROLE"
echo "  Consumer Role: $APP_CONSUMER_ROLE"
echo "  Package: $APP_PACKAGE_NAME"
echo "  Instance: $APP_INSTANCE_NAME"
echo "  Version: $APP_VERSION"
echo "  Compute Pool: $COMPUTE_POOL"
echo "  Warehouse: $WAREHOUSE"
echo "  Secret: $SECRET_DATABASE.$SECRET_SCHEMA.$SECRET_NAME"
echo ""

# ============================================
# Step 1: Create Application Package
# ============================================

log_step "Step 1: Create Application Package"

run_sql "Creating application package" \
    "USE ROLE ${APP_PROVIDER_ROLE}; CREATE APPLICATION PACKAGE IF NOT EXISTS ${APP_PACKAGE_NAME};"

log_info "Application package created successfully"

# ============================================
# Step 2: Grant Permissions to Consumer Role
# ============================================

log_step "Step 2: Grant Permissions to Consumer Role"

run_sql "Granting INSTALL and DEVELOP privileges" \
    "USE ROLE ${APP_PROVIDER_ROLE}; GRANT INSTALL, DEVELOP ON APPLICATION PACKAGE ${APP_PACKAGE_NAME} TO ROLE ${APP_CONSUMER_ROLE};"

log_info "Permissions granted successfully"

# ============================================
# Step 3: Setup Secret Infrastructure
# ============================================

log_step "Step 3: Setup Secret Infrastructure"

run_sql "Creating secret database and schema" \
    "USE ROLE ${APP_CONSUMER_ROLE};
     CREATE DATABASE IF NOT EXISTS ${SECRET_DATABASE};
     CREATE SCHEMA IF NOT EXISTS ${SECRET_DATABASE}.${SECRET_SCHEMA};"

log_info "Secret infrastructure created"

# Check if secret exists
echo -e "${BLUE}▶${NC} Checking if secret exists..."
SECRET_EXISTS=$(snow sql -q "USE ROLE ${APP_CONSUMER_ROLE}; USE SCHEMA ${SECRET_DATABASE}.${SECRET_SCHEMA}; SHOW SECRETS LIKE '${SECRET_NAME}';" --connection ${SNOW_CONNECTION} 2>&1 | grep -c "${SECRET_NAME}" || echo "0")

if [ "$SECRET_EXISTS" -eq "0" ]; then
    log_warning "Secret does not exist. Creating with placeholder value..."
    run_sql "Creating secret with placeholder" \
        "USE ROLE ${APP_CONSUMER_ROLE};
         USE SCHEMA ${SECRET_DATABASE}.${SECRET_SCHEMA};
         CREATE SECRET ${SECRET_NAME} TYPE = GENERIC_STRING SECRET_STRING = 'PLACEHOLDER_REPLACE_ME';"

    echo ""
    log_warning "IMPORTANT: Update the secret with your actual Serper API key:"
    echo -e "${YELLOW}  snow sql -q \"USE ROLE ${APP_CONSUMER_ROLE}; USE SCHEMA ${SECRET_DATABASE}.${SECRET_SCHEMA}; ALTER SECRET ${SECRET_NAME} SET SECRET_STRING = 'YOUR_ACTUAL_API_KEY';\" --connection ${SNOW_CONNECTION}${NC}"
    echo ""
else
    log_info "Secret already exists"
fi


# ============================================
# Step 4: Build and Deploy Application
# ============================================

log_step "Step 4: Build and Deploy Application"

echo -e "${BLUE}▶${NC} Running deploy script in setup mode..."
cd "$PROJECT_ROOT"
./scripts/deploy.sh --setup-mode

log_info "Application package version deployed successfully"

# ============================================
# Step 5: Create Application Instance
# ============================================

log_step "Step 5: Create Application Instance"

# Check if application exists
echo -e "${BLUE}▶${NC} Checking if application instance exists..."
APP_EXISTS=$(snow sql -q "USE ROLE ${APP_CONSUMER_ROLE}; SHOW APPLICATIONS LIKE '${APP_INSTANCE_NAME}';" --connection ${SNOW_CONNECTION} 2>&1 | grep -v "SHOW APPLICATIONS" | grep -c "${APP_INSTANCE_NAME}" || echo "0")

if [ "$APP_EXISTS" -gt "0" ]; then
    log_warning "Application instance already exists. Upgrading..."
    run_sql "Upgrading application" \
        "USE ROLE ${APP_CONSUMER_ROLE}; ALTER APPLICATION ${APP_INSTANCE_NAME} UPGRADE USING VERSION ${APP_VERSION};"
else
    log_info "Creating new application instance..."
    run_sql "Creating application instance" \
        "USE ROLE ${APP_CONSUMER_ROLE};
         CREATE APPLICATION ${APP_INSTANCE_NAME}
         FROM APPLICATION PACKAGE ${APP_PACKAGE_NAME}
         USING VERSION ${APP_VERSION}
         COMMENT = 'CrewAI Native Application with Serper search integration';"
fi

log_info "Application instance ready"

# ============================================
# Step 6: Configure Secret References
# ============================================

log_step "Step 6: Configure Secret References"

# First, grant REFERENCE_USAGE to the APPLICATION PACKAGE
run_sql "Granting REFERENCE_USAGE on database to package" \
    "USE ROLE ${APP_CONSUMER_ROLE};
     GRANT REFERENCE_USAGE ON DATABASE ${SECRET_DATABASE} TO SHARE IN APPLICATION PACKAGE ${APP_PACKAGE_NAME};"

# Second, grant USAGE on database and schema to the APPLICATION INSTANCE
run_sql "Granting USAGE on database and schema to application" \
    "USE ROLE ${APP_CONSUMER_ROLE};
     GRANT USAGE ON DATABASE ${SECRET_DATABASE} TO APPLICATION ${APP_INSTANCE_NAME};
     GRANT USAGE ON SCHEMA ${SECRET_DATABASE}.${SECRET_SCHEMA} TO APPLICATION ${APP_INSTANCE_NAME};"

# Third, grant READ on the secret to the APPLICATION INSTANCE
run_sql "Granting READ on secret to application" \
    "USE ROLE ${APP_CONSUMER_ROLE};
     GRANT READ ON SECRET ${SECRET_DATABASE}.${SECRET_SCHEMA}.${SECRET_NAME} TO APPLICATION ${APP_INSTANCE_NAME};"

# ============================================
# Step 7: Grant Warehouse Access
# ============================================

log_step "Step 7: Grant Warehouse Access"

run_sql "Granting warehouse usage to application" \
    "USE ROLE ${APP_CONSUMER_ROLE};
     GRANT USAGE ON WAREHOUSE ${WAREHOUSE} TO APPLICATION ${APP_INSTANCE_NAME};"

log_info "Warehouse access granted"

echo ""
log_info "Secret configuration complete"
log_info "The application will access the secret directly using SYSTEM\$REFERENCE at runtime"
log_info "No additional binding step required - permissions are already granted"   

# ============================================
# Step 8: Start SPCS Service
# ============================================

log_step "Step 8: Start SPCS Service"

echo -e "${BLUE}▶${NC} Starting SPCS service (this may take a few minutes)..."
run_sql "Starting service" \
    "USE ROLE ${APP_CONSUMER_ROLE};
     CALL ${APP_INSTANCE_NAME}.app_public.start_app('${COMPUTE_POOL}', '${WAREHOUSE}');"

log_info "Service started successfully"

# ============================================
# Step 9: Check Service Status
# ============================================

log_step "Step 9: Check Service Status"

echo -e "${BLUE}▶${NC} Checking service status..."
snow sql -q "USE ROLE ${APP_CONSUMER_ROLE}; CALL ${APP_INSTANCE_NAME}.app_public.get_service_status();" --connection ${SNOW_CONNECTION}

# ============================================
# Completion Message
# ============================================

echo ""
echo "=========================================="
echo -e "${GREEN}Setup Complete!${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Wait for service to be READY (2-5 minutes):"
echo -e "   ${CYAN}snow sql -q \"USE ROLE ${APP_CONSUMER_ROLE}; CALL ${APP_INSTANCE_NAME}.app_public.get_service_status();\" --connection ${SNOW_CONNECTION}${NC}"
echo ""
echo "2. Get application URL:"
echo -e "   ${CYAN}snow sql -q \"USE ROLE ${APP_CONSUMER_ROLE}; CALL ${APP_INSTANCE_NAME}.app_public.app_url();\" --connection ${SNOW_CONNECTION}${NC}"
echo ""
echo "3. Monitor service logs:"
echo -e "   ${CYAN}snow sql -q \"USE ROLE ${APP_CONSUMER_ROLE}; CALL ${APP_INSTANCE_NAME}.app_public.get_service_logs('eap-backend', 200);\" --connection ${SNOW_CONNECTION}${NC}"
echo ""
echo "For future deployments (code changes only):"
echo -e "   ${CYAN}./scripts/deploy.sh${NC}"
echo ""

# See logs 
echo "Check status of the service until is READY"
echo snow sql -q "USE ROLE nac_test; CALL spcs_app_instance_test.app_public.get_service_status();" --connection mkt_blendx_demo"

echo "Once the service is ready, see the logs"
echo "snow sql -q "USE ROLE nac_test; CALL spcs_app_instance_test.app_public.app_url();" --connection mkt_blendx_demo"
