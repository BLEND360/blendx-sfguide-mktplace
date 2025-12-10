#!/bin/bash

# Provider Setup Script - Step 1: Create Application Package
# This script should be run by the PROVIDER to create the application package
# After this, run deploy.sh to build and push the application

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
echo "Provider Setup - Application Package"
echo "=========================================="
echo ""
echo "Configuration:"
echo "  Connection: $SNOW_CONNECTION"
echo "  Provider Role: $APP_PROVIDER_ROLE"
echo "  Consumer Role: $APP_CONSUMER_ROLE"
echo "  Package: $APP_PACKAGE_NAME"
echo ""

# ============================================
# Step 1: Create Application Package
# ============================================

log_step "Creating Application Package"

run_sql "Creating application package" \
    "USE ROLE ${APP_PROVIDER_ROLE}; CREATE APPLICATION PACKAGE IF NOT EXISTS ${APP_PACKAGE_NAME};"

log_info "Application package created successfully"

# Grant permissions to consumer role
run_sql "Granting INSTALL and DEVELOP privileges" \
    "USE ROLE ${APP_PROVIDER_ROLE}; GRANT INSTALL, DEVELOP ON APPLICATION PACKAGE ${APP_PACKAGE_NAME} TO ROLE ${APP_CONSUMER_ROLE};"

log_info "Permissions granted to consumer role"

# ============================================
# Completion Message
# ============================================

echo ""
echo "=========================================="
echo -e "${GREEN}Provider Setup Complete!${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Run the deployment script to build and deploy the application:"
echo -e "   ${CYAN}./scripts/deploy.sh --setup-mode${NC}"
echo ""
echo "2. After deploy completes, the CONSUMER should:"
echo -e "   a) Setup secrets and permissions: ${CYAN}snow sql -f scripts/sql/consumer.sql --connection ${SNOW_CONNECTION}${NC}"
echo -e "   b) Create application instance: ${CYAN}./scripts/create-application.sh${NC}"
echo ""
