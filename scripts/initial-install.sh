#!/bin/bash

# Initial Installation Script for Snowflake Native App
# This script creates the application instance with references for the first time
# For upgrades, use deploy.sh instead

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
NC='\033[0m' # No Color

# ============================================
# Load Configuration
# ============================================

SNOW_CONNECTION=${SNOW_CONNECTION:-"mkt_blendx_demo"}
APP_CONSUMER_ROLE=${APP_CONSUMER_ROLE:-"nac_test"}
APP_PACKAGE_NAME=${APP_PACKAGE_NAME:-"spcs_app_pkg_test"}
APP_INSTANCE_NAME=${APP_INSTANCE_NAME:-"spcs_app_instance_test"}
APP_VERSION=${APP_VERSION:-"v1"}
COMPUTE_POOL=${COMPUTE_POOL:-"pool_nac"}
WAREHOUSE=${WAREHOUSE:-"wh_nac"}
DRY_RUN=false
DATABASE=spcs_app_test
SCHEMA=napp

# Load .env file if it exists
if [ -f "$SCRIPT_DIR/.env" ]; then
    echo -e "${BLUE}Loading configuration from .env file...${NC}"
    source "$SCRIPT_DIR/.env"
fi

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            echo -e "${YELLOW}Running in DRY RUN mode${NC}"
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Initial installation script for the Native App with references."
            echo ""
            echo "Options:"
            echo "  --dry-run      Show what would be done without making changes"
            echo "  --help, -h     Show this help message"
            echo ""
            echo "Prerequisites:"
            echo "  1. Secret 'serper_api_key' must exist in consumer account"
            echo "  2. External Access Integration 'serper_external_access' must exist"
            echo "  3. Application package must be deployed and have at least one version"
            echo ""
            echo "Configuration can be set via .env file in the scripts/ directory."
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# ============================================
# Helper Functions
# ============================================

run_command() {
    local description=$1
    local command=$2

    if [ "$DRY_RUN" = true ]; then
        echo -e "${BLUE}[DRY RUN]${NC} $description"
        echo -e "${YELLOW}  Command: $command${NC}"
    else
        echo -e "${GREEN}▶${NC} $description"
        eval "$command"
    fi
}

# ============================================
# Main Installation
# ============================================

echo ""
echo "=========================================="
echo "Initial Application Installation"
echo "=========================================="
echo ""
echo "Configuration:"
echo "  Connection: $SNOW_CONNECTION"
echo "  Consumer Role: $APP_CONSUMER_ROLE"
echo "  Package: $APP_PACKAGE_NAME"
echo "  Instance: $APP_INSTANCE_NAME"
echo "  Version: $APP_VERSION"
echo ""

echo "=========================================="
echo "Step 1: Verify Prerequisites"
echo "=========================================="

echo "Checking that secret and external access integration exist..."
run_command "Checking secret" \
    "snow sql -q \"USE ROLE ${APP_CONSUMER_ROLE}; USE DATABASE ${DATABASE}; USE SCHEMA ${SCHEMA}; SHOW SECRETS LIKE 'serper_api_key';\" --connection ${SNOW_CONNECTION}"

run_command "Checking external access integration" \
    "snow sql -q \"USE ROLE ${APP_CONSUMER_ROLE}; SHOW EXTERNAL ACCESS INTEGRATIONS LIKE 'serper_external_access';\" --connection ${SNOW_CONNECTION}"

echo ""

echo "=========================================="
echo "Step 2: Check if application already exists"
echo "=========================================="

if [ "$DRY_RUN" = false ]; then
    # Check if application exists using a robust grep count (counts exact matches)
    APP_EXISTS=$(snow sql -q "USE ROLE ${APP_CONSUMER_ROLE}; SHOW APPLICATIONS LIKE '${APP_INSTANCE_NAME}';" --connection ${SNOW_CONNECTION} 2>&1 | grep -c "^${APP_INSTANCE_NAME}$" || true)

    if [ "${APP_EXISTS}" -gt 0 ]; then
        echo -e "${YELLOW}Application ${APP_INSTANCE_NAME} already exists!${NC}"
        echo ""
        echo "To upgrade existing app, use: ./scripts/deploy.sh"
        echo "To reinstall from scratch:"
        echo "  1. Drop existing: snow sql -q \"USE ROLE ${APP_CONSUMER_ROLE}; DROP APPLICATION ${APP_INSTANCE_NAME};\" --connection ${SNOW_CONNECTION}"
        echo "  2. Run this script again"
        echo ""
        exit 1
    fi
else
    echo -e "${BLUE}[DRY RUN]${NC} Would check if application exists"
fi

echo ""

echo "=========================================="
echo "Step 3: Create Application"
echo "=========================================="

CREATE_SQL="
USE ROLE ${APP_CONSUMER_ROLE};

CREATE APPLICATION ${APP_INSTANCE_NAME}
  FROM APPLICATION PACKAGE ${APP_PACKAGE_NAME}
  USING VERSION ${APP_VERSION}
  COMMENT = 'CrewAI Native Application with Serper search integration';
"

run_command "Creating application" \
    "snow sql -q \"${CREATE_SQL}\" --connection ${SNOW_CONNECTION}"

echo ""
echo "=========================================="
echo "Step 4: Pair References & External Access"
echo "=========================================="

run_command "Pair SECRET reference serper_api_key" \
    "snow sql -q \"USE ROLE ${APP_CONSUMER_ROLE}; ALTER APPLICATION ${APP_INSTANCE_NAME} SET REFERENCES = (SECRET serper_api_key);\" --connection ${SNOW_CONNECTION}"

run_command "Pair EXTERNAL ACCESS INTEGRATION serper_external_access" \
    "snow sql -q \"USE ROLE ${APP_CONSUMER_ROLE}; ALTER APPLICATION ${APP_INSTANCE_NAME} SET EXTERNAL_ACCESS_INTEGRATIONS = (serper_external_access);\" --connection ${SNOW_CONNECTION}"

echo ""

echo "=========================================="
echo "Step 5: Grant Permissions"
echo "=========================================="

run_command "Granting warehouse usage" \
    "snow sql -q \"USE ROLE ${APP_CONSUMER_ROLE}; GRANT USAGE ON WAREHOUSE ${WAREHOUSE} TO APPLICATION ${APP_INSTANCE_NAME};\" --connection ${SNOW_CONNECTION}"

run_command "Granting compute pool usage" \
    "snow sql -q \"USE ROLE ${APP_CONSUMER_ROLE}; GRANT USAGE ON COMPUTE POOL ${COMPUTE_POOL} TO APPLICATION ${APP_INSTANCE_NAME};\" --connection ${SNOW_CONNECTION}"

echo ""

# ============================================
# Completion Message
# ============================================

echo ""
echo "For future deployments, use: ./scripts/deploy.sh"
echo ""
