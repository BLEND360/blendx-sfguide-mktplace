#!/bin/bash

# Create Application Instance Script - Step 5: Create Application Instance
# This script creates the application instance from the deployed application package
# Run this AFTER provider-setup.sh and deploy.sh --setup-mode
# Prerequisites: consumer.sql must have been executed to setup secrets and permissions

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
APP_CONSUMER_ROLE=${APP_CONSUMER_ROLE:-"nac_test"}
APP_PACKAGE_NAME=${APP_PACKAGE_NAME:-"spcs_app_pkg_test"}
APP_INSTANCE_NAME=${APP_INSTANCE_NAME:-"spcs_app_instance_test"}
APP_VERSION=${APP_VERSION:-"v1"}
COMPUTE_POOL=${COMPUTE_POOL:-"pool_nac"}
SECRET_DATABASE=${SECRET_DATABASE:-"secrets_db"}
SECRET_SCHEMA=${SECRET_SCHEMA:-"app_secrets"}
SECRET_NAME=${SECRET_NAME:-"serper_api_key"}

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
echo "Create Application Instance"
echo "=========================================="
echo ""
echo "Configuration:"
echo "  Connection: $SNOW_CONNECTION"
echo "  Consumer Role: $APP_CONSUMER_ROLE"
echo "  Package: $APP_PACKAGE_NAME"
echo "  Instance: $APP_INSTANCE_NAME"
echo "  Version: $APP_VERSION"
echo "  Compute Pool: $COMPUTE_POOL"
echo "  Secret: $SECRET_DATABASE.$SECRET_SCHEMA.$SECRET_NAME"
echo ""

# ============================================
# Prerequisites Check
# ============================================

log_step "Checking Prerequisites"

echo -e "${BLUE}▶${NC} Checking if secret exists..."
SECRET_EXISTS=$(snow sql -q "USE ROLE ${APP_CONSUMER_ROLE}; USE SCHEMA ${SECRET_DATABASE}.${SECRET_SCHEMA}; SHOW SECRETS LIKE '${SECRET_NAME}';" --connection ${SNOW_CONNECTION} 2>&1 | grep -c "${SECRET_NAME}" || echo "0")

if [ "$SECRET_EXISTS" -eq "0" ]; then
    log_error "Secret does not exist!"
    echo ""
    echo "Please run the consumer.sql script first to setup secrets and permissions:"
    echo -e "${CYAN}snow sql -f scripts/sql/consumer.sql --connection ${SNOW_CONNECTION}${NC}"
    echo ""
    exit 1
else
    log_info "Secret exists"
fi

# ============================================
# Step 1: Create Application Instance
# ============================================

log_step "Creating Application Instance"

# Check if application exists
echo -e "${BLUE}▶${NC} Checking if application instance exists..."

# Query and check if application exists
APP_EXISTS=$(snow sql -q "USE ROLE ${APP_CONSUMER_ROLE}; SHOW APPLICATIONS LIKE '${APP_INSTANCE_NAME}';" --connection ${SNOW_CONNECTION} 2>&1 | grep -c "^|.*${APP_INSTANCE_NAME}.*|" || echo "0")

# Ensure APP_EXISTS is a valid number
if [ -z "$APP_EXISTS" ] || ! [[ "$APP_EXISTS" =~ ^[0-9]+$ ]]; then
    APP_EXISTS=0
fi

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
         COMMENT = 'BlendX Native Application with CrewAI and Serper search integration';"
fi

log_info "Application instance ready"

