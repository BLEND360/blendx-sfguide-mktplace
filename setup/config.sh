#!/bin/bash

# ============================================
# Shared Configuration for Setup Scripts
# ============================================
# This file contains all configuration variables and helper functions
# used by provider-setup.sh and create-application.sh
#
# To override values, either:
#   1. Set environment variables before running the script
#   2. Create a .env file in the setup directory
# ============================================

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# ============================================
# Load .env file if it exists
# ============================================
if [ -f "$SCRIPT_DIR/.env" ]; then
    source "$SCRIPT_DIR/.env"
fi

# ============================================
# Snowflake Connection
# ============================================
SNOW_CONNECTION=${SNOW_CONNECTION:-"mkt_blendx_demo"}

# ============================================
# CI/CD User and Role
# ============================================
CICD_USER=${CICD_USER:-"MK_BLENDX_DEPLOY_USER"}
CICD_ROLE=${CICD_ROLE:-"MK_BLENDX_DEPLOY_ROLE"}

# ============================================
# Database Objects
# ============================================
DATABASE_NAME=${DATABASE_NAME:-"BLENDX_APP_DB"}
SCHEMA_NAME=${SCHEMA_NAME:-"BLENDX_SCHEMA"}
STAGE_NAME=${STAGE_NAME:-"APP_STAGE"}
IMAGE_REPO_NAME=${IMAGE_REPO_NAME:-"img_repo"}
WAREHOUSE_NAME=${WAREHOUSE_NAME:-"BLENDX_APP_WH"}

# ============================================
# Application Package and Instance
# ============================================
APP_PACKAGE_NAME=${APP_PACKAGE_NAME:-"MK_BLENDX_APP_PKG"}
APP_INSTANCE_BASE=${APP_INSTANCE_BASE:-"BLENDX_APP_INSTANCE"}
APP_VERSION=${APP_VERSION:-"V1"}

# ============================================
# Consumer Role and Compute Pool
# ============================================
APP_CONSUMER_ROLE=${APP_CONSUMER_ROLE:-"BLENDX_APP_ROLE"}
COMPUTE_POOL_NAME=${COMPUTE_POOL_NAME:-"BLENDX_APP_COMPUTE_POOL"}

# ============================================
# Keys
# ============================================
PUBLIC_KEY_FILE=${PUBLIC_KEY_FILE:-"$PROJECT_ROOT/keys/pipeline/snowflake_key.pub"}
PRIVATE_KEY_FILE=${PRIVATE_KEY_FILE:-"$PROJECT_ROOT/keys/pipeline/snowflake_key.p8"}

# ============================================
# Colors for Output
# ============================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

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
# Get Snowflake Account Info
# ============================================
get_snowflake_info() {
    # Get image repository URL - use SHOW and grep for the URL
    local show_output
    show_output=$(snow sql -q "SHOW IMAGE REPOSITORIES IN SCHEMA ${DATABASE_NAME}.${SCHEMA_NAME};" --connection ${SNOW_CONNECTION} 2>/dev/null) || true

    # Extract URL that contains registry.snowflakecomputing.com
    IMAGE_REPO_URL=$(echo "$show_output" | grep -oE '[a-z0-9_-]+\.registry\.snowflakecomputing\.com/[^[:space:]|]+' | head -1 | tr -d '|' | tr -d ' ') || true

    if [ -z "$IMAGE_REPO_URL" ]; then
        IMAGE_REPO_URL="<run: SHOW IMAGE REPOSITORIES IN SCHEMA ${DATABASE_NAME}.${SCHEMA_NAME}>"
    fi

    # Get Snowflake account info
    local account_output
    account_output=$(snow sql -q "SELECT LOWER(CURRENT_ORGANIZATION_NAME() || '-' || CURRENT_ACCOUNT()) as account_id;" --connection ${SNOW_CONNECTION} 2>/dev/null) || true

    SNOWFLAKE_ACCOUNT_INFO=$(echo "$account_output" | grep -oE '^[a-z0-9_]+-[a-z0-9_]+$' | head -1) || true

    if [ -n "$SNOWFLAKE_ACCOUNT_INFO" ]; then
        SNOWFLAKE_HOST="${SNOWFLAKE_ACCOUNT_INFO}.snowflakecomputing.com"
    else
        SNOWFLAKE_ACCOUNT_INFO="<your-org>-<your-account>"
        SNOWFLAKE_HOST="<your-org>-<your-account>.snowflakecomputing.com"
    fi
}

# ============================================
# Print GitHub Configuration
# ============================================
print_github_config() {
    echo ""
    echo -e "${YELLOW}GitHub Secrets (Repository level):${NC}"
    echo ""
    echo "  SNOWFLAKE_ACCOUNT: ${SNOWFLAKE_ACCOUNT_INFO}"
    echo "  SNOWFLAKE_HOST: ${SNOWFLAKE_HOST}"
    echo "  SNOWFLAKE_PRIVATE_KEY_RAW: <content of ${PRIVATE_KEY_FILE}>"
    echo ""
    echo -e "${YELLOW}GitHub Variables (Repository level - shared):${NC}"
    echo ""
    echo "  SNOWFLAKE_CONNECTION: ${SNOW_CONNECTION}"
    echo "  SNOWFLAKE_DEPLOY_USER: ${CICD_USER}"
    echo "  SNOWFLAKE_DEPLOY_ROLE: ${CICD_ROLE}"
    echo "  SNOWFLAKE_WAREHOUSE: ${WAREHOUSE_NAME}"
    echo "  SNOWFLAKE_DATABASE: ${DATABASE_NAME}"
    echo "  SNOWFLAKE_SCHEMA: ${SCHEMA_NAME}"
    echo "  SNOWFLAKE_REPO: ${IMAGE_REPO_URL}"
    echo "  SNOWFLAKE_APP_PACKAGE: ${APP_PACKAGE_NAME}"
    echo "  SNOWFLAKE_ROLE: ${APP_CONSUMER_ROLE}"
    echo ""
    echo -e "${YELLOW}GitHub Variables (Environment: qa):${NC}"
    echo ""
    echo "  SNOWFLAKE_APP_INSTANCE: ${APP_INSTANCE_BASE}_QA"
    echo "  SNOWFLAKE_COMPUTE_POOL: ${COMPUTE_POOL_NAME}_QA"
    echo ""
    echo -e "${YELLOW}GitHub Variables (Environment: stable):${NC}"
    echo ""
    echo "  SNOWFLAKE_APP_INSTANCE: ${APP_INSTANCE_BASE}_STABLE"
    echo "  SNOWFLAKE_COMPUTE_POOL: ${COMPUTE_POOL_NAME}_STABLE"
    echo ""
    echo "To get the private key content for GitHub secret:"
    echo "  cat ${PRIVATE_KEY_FILE}"
}
