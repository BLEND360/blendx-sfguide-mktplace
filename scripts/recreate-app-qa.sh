#!/bin/bash

# Script to recreate the test application using the QA release channel
# This separates the test app from the DEFAULT channel used for marketplace listing
# Usage: ./recreate-app-qa.sh [--dry-run]

set -e

# ============================================
# Script Setup
# ============================================

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ============================================
# Load Configuration
# ============================================

SNOW_CONNECTION=${SNOW_CONNECTION:-"mkt_blendx_demo"}
APP_PACKAGE_ROLE=${APP_PACKAGE_ROLE:-"naspcs_role"}
APP_CONSUMER_ROLE=${APP_CONSUMER_ROLE:-"nac_test"}
APP_PACKAGE_NAME=${APP_PACKAGE_NAME:-"spcs_app_pkg_test"}
APP_INSTANCE_NAME=${APP_INSTANCE_NAME:-"spcs_app_instance_test"}
APP_VERSION=${APP_VERSION:-"v1"}
RELEASE_CHANNEL=${RELEASE_CHANNEL:-"QA"}
DRY_RUN=false

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
            echo -e "${YELLOW}Running in DRY RUN mode - no changes will be made${NC}"
            shift
            ;;
        --channel)
            RELEASE_CHANNEL="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Recreate test application using a specific release channel"
            echo ""
            echo "Options:"
            echo "  --dry-run         Show what would be done without making changes"
            echo "  --channel NAME    Release channel to use (default: QA)"
            echo "  --help, -h        Show this help message"
            echo ""
            echo "Release Channels:"
            echo "  DEFAULT  - Production channel for marketplace listing"
            echo "  ALPHA    - May contain versions where security review was not approved"
            echo "  QA       - Internal testing only, versions never reviewed by Snowflake"
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

run_sql() {
    local description=$1
    local sql=$2
    local role=$3

    if [ "$DRY_RUN" = true ]; then
        echo -e "${BLUE}[DRY RUN]${NC} $description"
        echo -e "${YELLOW}  SQL: $sql${NC}"
    else
        echo -e "${GREEN}▶${NC} $description"
        snow sql -q "USE ROLE ${role}; $sql" --connection ${SNOW_CONNECTION}
    fi
}

# ============================================
# Display Configuration
# ============================================

echo ""
echo "=========================================="
echo "Recreate Application with Release Channel"
echo "=========================================="
echo ""
echo "Configuration:"
echo "  Connection: $SNOW_CONNECTION"
echo "  Package: $APP_PACKAGE_NAME"
echo "  Instance: $APP_INSTANCE_NAME"
echo "  Version: $APP_VERSION"
echo "  Release Channel: $RELEASE_CHANNEL"
echo ""

# ============================================
# Step 1: Get Latest Patch Number
# ============================================

echo "=========================================="
echo "[1/6] Getting latest patch number..."
echo "=========================================="

LATEST_PATCH=0
if [ "$DRY_RUN" = false ]; then
    TEMP_VERSIONS=$(mktemp)
    snow sql -q "USE ROLE ${APP_PACKAGE_ROLE}; SHOW VERSIONS IN APPLICATION PACKAGE ${APP_PACKAGE_NAME};" --connection ${SNOW_CONNECTION} > "$TEMP_VERSIONS" 2>&1 || true

    LATEST_PATCH=$(cat "$TEMP_VERSIONS" | grep -i "| ${APP_VERSION} " | awk -F'|' '{print $3}' | tr -d ' ' | sort -n | tail -1)
    rm -f "$TEMP_VERSIONS"

    if [ -z "$LATEST_PATCH" ] || ! [[ "$LATEST_PATCH" =~ ^[0-9]+$ ]]; then
        LATEST_PATCH=0
    fi

    echo -e "${GREEN}✓ Latest patch for ${APP_VERSION}: ${LATEST_PATCH}${NC}"
fi

echo ""

# ============================================
# Step 2: Setup Release Channel
# ============================================

echo "=========================================="
echo "[2/6] Setting up ${RELEASE_CHANNEL} release channel..."
echo "=========================================="

run_sql "Adding version to ${RELEASE_CHANNEL} channel" \
    "ALTER APPLICATION PACKAGE ${APP_PACKAGE_NAME} MODIFY RELEASE CHANNEL ${RELEASE_CHANNEL} ADD VERSION ${APP_VERSION};" \
    "${APP_PACKAGE_ROLE}" || echo "Version may already be in channel (OK)"

run_sql "Setting release directive for ${RELEASE_CHANNEL}" \
    "ALTER APPLICATION PACKAGE ${APP_PACKAGE_NAME} MODIFY RELEASE CHANNEL ${RELEASE_CHANNEL} SET DEFAULT RELEASE DIRECTIVE VERSION=${APP_VERSION} PATCH=${LATEST_PATCH};" \
    "${APP_PACKAGE_ROLE}"

echo ""

# ============================================
# Step 3: Stop Existing Service
# ============================================

echo "=========================================="
echo "[3/6] Stopping existing service..."
echo "=========================================="

if [ "$DRY_RUN" = false ]; then
    snow sql -q "USE ROLE ${APP_CONSUMER_ROLE}; CALL ${APP_INSTANCE_NAME}.app_public.stop_app();" --connection ${SNOW_CONNECTION} 2>&1 || echo "Service may not be running (OK)"
else
    echo -e "${BLUE}[DRY RUN]${NC} Would stop service"
fi

echo ""

# ============================================
# Step 4: Drop Existing Application
# ============================================

echo "=========================================="
echo "[4/6] Dropping existing application..."
echo "=========================================="

run_sql "Dropping application with CASCADE" \
    "DROP APPLICATION IF EXISTS ${APP_INSTANCE_NAME} CASCADE;" \
    "${APP_CONSUMER_ROLE}"

echo ""

# ============================================
# Step 5: Create Application with Release Channel
# ============================================

echo "=========================================="
echo "[5/6] Creating application using ${RELEASE_CHANNEL} channel..."
echo "=========================================="

run_sql "Creating application" \
    "CREATE APPLICATION ${APP_INSTANCE_NAME} FROM APPLICATION PACKAGE ${APP_PACKAGE_NAME} USING RELEASE CHANNEL ${RELEASE_CHANNEL};" \
    "${APP_CONSUMER_ROLE}"

echo ""

# ============================================
# Step 6: Verify Application
# ============================================

echo "=========================================="
echo "[6/6] Verifying application..."
echo "=========================================="

if [ "$DRY_RUN" = false ]; then
    echo "Application details:"
    snow sql -q "USE ROLE ${APP_CONSUMER_ROLE}; DESCRIBE APPLICATION ${APP_INSTANCE_NAME};" --connection ${SNOW_CONNECTION} 2>&1 | grep -E "version|patch|release_channel"
fi

echo ""

# ============================================
# Completion Message
# ============================================

echo "=========================================="
if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}DRY RUN completed!${NC}"
else
    echo -e "${GREEN}Application recreated successfully!${NC}"
fi
echo "=========================================="
echo ""
echo -e "${YELLOW}IMPORTANT: You need to reconfigure the application:${NC}"
echo ""
echo "1. Grant privileges in the Snowflake UI (Apps > ${APP_INSTANCE_NAME})"
echo "2. Configure secret references if needed"
echo "3. Start the service:"
echo ""
echo "   snow sql -q \"USE ROLE ${APP_CONSUMER_ROLE}; CALL ${APP_INSTANCE_NAME}.app_public.start_app('pool_nac');\" --connection ${SNOW_CONNECTION}"
echo ""
echo "4. Get the application URL:"
echo ""
echo "   snow sql -q \"USE ROLE ${APP_CONSUMER_ROLE}; CALL ${APP_INSTANCE_NAME}.app_public.app_url();\" --connection ${SNOW_CONNECTION}"
echo ""
