#!/bin/bash

# Create Application Instance Script
# Run this AFTER:
#   1. provider-setup.sh (creates CI/CD user, roles, permissions)
#   2. First pipeline run (deploys the application package with a version)
#
# This script:
#   1. Creates the application instance from the deployed package
#   2. Grants required account-level permissions to the application
#   3. Optionally starts the application service

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
# Configuration - Same values as provider-setup.sh
# ============================================

SNOW_CONNECTION=${SNOW_CONNECTION:-"mkt_blendx_demo"}

# CI/CD Role (from provider-setup.sh)
CICD_ROLE=${CICD_ROLE:-"MK_BLENDX_DEPLOY_ROLE"}

# Consumer role (for app installation)
APP_CONSUMER_ROLE=${APP_CONSUMER_ROLE:-"BLENDX_APP_ROLE"}

# Application Package (from provider-setup.sh)
APP_PACKAGE_NAME=${APP_PACKAGE_NAME:-"MK_BLENDX_APP_PKG"}

# Application Instance
APP_INSTANCE_NAME=${APP_INSTANCE_NAME:-"BLENDX_APP_INSTANCE"}
APP_VERSION=${APP_VERSION:-"V1"}

# Compute Pool
COMPUTE_POOL_NAME=${COMPUTE_POOL_NAME:-"BLENDX_CP"}

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

run_sql_silent() {
    local sql=$1
    snow sql -q "$sql" --connection ${SNOW_CONNECTION} 2>/dev/null || true
}

# ============================================
# Display Configuration
# ============================================

echo ""
echo "=========================================="
echo "Create Application Instance"
echo "=========================================="
echo ""
echo "Configuration:"
echo "  Connection: $SNOW_CONNECTION"
echo "  CI/CD Role: $CICD_ROLE"
echo "  Consumer Role: $APP_CONSUMER_ROLE"
echo "  Package: $APP_PACKAGE_NAME"
echo "  Instance: $APP_INSTANCE_NAME"
echo "  Version: $APP_VERSION"
echo "  Compute Pool: $COMPUTE_POOL_NAME"
echo ""

read -p "Continue with application creation? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Setup cancelled."
    exit 0
fi

# ============================================
# Step 1: Check Prerequisites
# ============================================

log_step "Step 1: Checking Prerequisites"

# Check if a version exists in the application package
echo -e "${BLUE}▶${NC} Checking for available versions in application package..."
VERSION_EXISTS=$(run_sql_silent "USE ROLE ${CICD_ROLE}; SHOW VERSIONS IN APPLICATION PACKAGE ${APP_PACKAGE_NAME};" | grep -i "| V" | wc -l | tr -d ' ' || echo "0")

if [ "$VERSION_EXISTS" -eq "0" ]; then
    log_error "No versions found in application package ${APP_PACKAGE_NAME}"
    echo ""
    echo "Please run the pipeline first to deploy a version, then run this script again."
    echo ""
    exit 1
fi

log_info "Version found in application package"

# ============================================
# Step 2: Get Latest Patch Number
# ============================================

log_step "Step 2: Getting Latest Patch Number"

echo -e "${BLUE}▶${NC} Querying latest patch for version ${APP_VERSION}..."
# Get versions output - format is pipe-separated table: | version | patch | label | ...
VERSIONS_OUTPUT=$(snow sql -q "USE ROLE ${CICD_ROLE}; SHOW VERSIONS IN APPLICATION PACKAGE ${APP_PACKAGE_NAME};" --connection ${SNOW_CONNECTION} 2>&1)

# Extract patch number from pipe-separated output
# Lines look like: | V1      | 2     | Version One | ...
LATEST_PATCH=$(echo "$VERSIONS_OUTPUT" | grep -i "| ${APP_VERSION} " | awk -F'|' '{print $3}' | tr -d ' ' | sort -n | tail -1 || echo "0")

# Ensure LATEST_PATCH is a valid number
if [ -z "$LATEST_PATCH" ] || ! [[ "$LATEST_PATCH" =~ ^[0-9]+$ ]]; then
    LATEST_PATCH=0
fi

log_info "Latest patch: ${LATEST_PATCH}"

# ============================================
# Step 3: Create Application Instance
# ============================================

log_step "Step 3: Creating Application Instance"

# Check if application exists using SELECT COUNT
echo -e "${BLUE}▶${NC} Checking if application instance exists..."
APP_EXISTS=$(snow sql -q "SELECT COUNT(*) FROM SNOWFLAKE.INFORMATION_SCHEMA.DATABASES WHERE DATABASE_NAME = '${APP_INSTANCE_NAME}' AND TYPE = 'APPLICATION';" --connection ${SNOW_CONNECTION} 2>/dev/null | grep -E "^\| *[0-9]+ *\|$" | tr -d '| ' || echo "0")

# Ensure APP_EXISTS is a valid number
if [ -z "$APP_EXISTS" ] || ! [[ "$APP_EXISTS" =~ ^[0-9]+$ ]]; then
    APP_EXISTS=0
fi

if [ "$APP_EXISTS" -gt "0" ]; then
    log_warning "Application instance already exists. Upgrading..."
    run_sql "Upgrading application" \
        "USE ROLE ${APP_CONSUMER_ROLE};
         ALTER APPLICATION ${APP_INSTANCE_NAME} UPGRADE USING VERSION ${APP_VERSION} PATCH ${LATEST_PATCH};"
else
    log_info "Creating new application instance with version ${APP_VERSION} patch ${LATEST_PATCH}..."
    run_sql "Creating application instance" \
        "USE ROLE ${APP_CONSUMER_ROLE};
         CREATE APPLICATION ${APP_INSTANCE_NAME}
         FROM APPLICATION PACKAGE ${APP_PACKAGE_NAME}
         USING VERSION ${APP_VERSION} PATCH ${LATEST_PATCH}
         COMMENT = 'BlendX Native Application';"
fi

log_info "Application instance created/upgraded"

# ============================================
# Step 4: Grant Account-Level Permissions to Application
# ============================================

log_step "Step 4: Granting Account-Level Permissions to Application"

run_sql "Granting CREATE COMPUTE POOL to application" \
    "USE ROLE ACCOUNTADMIN;
     GRANT CREATE COMPUTE POOL ON ACCOUNT TO APPLICATION ${APP_INSTANCE_NAME};"

run_sql "Granting BIND SERVICE ENDPOINT to application" \
    "USE ROLE ACCOUNTADMIN;
     GRANT BIND SERVICE ENDPOINT ON ACCOUNT TO APPLICATION ${APP_INSTANCE_NAME};"

run_sql "Granting CREATE WAREHOUSE to application" \
    "USE ROLE ACCOUNTADMIN;
     GRANT CREATE WAREHOUSE ON ACCOUNT TO APPLICATION ${APP_INSTANCE_NAME};"

run_sql "Granting CREATE EXTERNAL ACCESS INTEGRATION to application" \
    "USE ROLE ACCOUNTADMIN;
     GRANT CREATE EXTERNAL ACCESS INTEGRATION ON ACCOUNT TO APPLICATION ${APP_INSTANCE_NAME};"

log_info "Account-level permissions granted to application"

# ============================================
# Completion Message
# ============================================

echo ""
echo "=========================================="
echo -e "${GREEN}Application Instance Setup Complete!${NC}"
echo "=========================================="
echo ""
echo "Application: ${APP_INSTANCE_NAME}"
echo ""
