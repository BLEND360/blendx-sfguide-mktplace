#!/bin/bash

# Deployment script for Snowflake Native App with SPCS
# This script automates the entire deployment process
# Usage: ./deploy.sh [--dry-run] [--skip-build] [--skip-push]

set -e  # Exit on error

# ============================================
# Script Setup
# ============================================

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Get the project root directory (one level up from scripts/)
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

# Default values (can be overridden by .env file)
SNOW_CONNECTION=${SNOW_CONNECTION:-"mkt_blendx_demo"}
SNOWFLAKE_REGISTRY=${SNOWFLAKE_REGISTRY:-"wb19670-c2gpartners.registry.snowflakecomputing.com/spcs_app/napp/img_repo"}
BACKEND_IMAGE=${BACKEND_IMAGE:-"eap_backend"}
FRONTEND_IMAGE=${FRONTEND_IMAGE:-"eap_frontend"}
ROUTER_IMAGE=${ROUTER_IMAGE:-"eap_router"}
APP_PACKAGE_ROLE=${APP_PACKAGE_ROLE:-"naspcs_role"}
APP_CONSUMER_ROLE=${APP_CONSUMER_ROLE:-"nac_test"}
APP_DATABASE=${APP_DATABASE:-"spcs_app_test"}
APP_SCHEMA=${APP_SCHEMA:-"napp"}
APP_STAGE=${APP_STAGE:-"app_stage"}
APP_PACKAGE_NAME=${APP_PACKAGE_NAME:-"spcs_app_pkg_test"}
APP_INSTANCE_NAME=${APP_INSTANCE_NAME:-"spcs_app_instance_test"}
APP_VERSION=${APP_VERSION:-"v1"}
COMPUTE_POOL=${COMPUTE_POOL:-"pool_nac"}
WAREHOUSE=${WAREHOUSE:-"WH_BLENDX_DEMO_PROVIDER"}
SKIP_BUILD=${SKIP_BUILD:-false}
SKIP_PUSH=${SKIP_PUSH:-false}
SERVICE_START_WAIT=${SERVICE_START_WAIT:-30}
DRY_RUN=false
SETUP_MODE=false

# Load .env file if it exists
if [ -f "$SCRIPT_DIR/.env" ]; then
    echo -e "${BLUE}Loading configuration from .env file...${NC}"
    source "$SCRIPT_DIR/.env"
else
    echo -e "${YELLOW}No .env file found. Using default values.${NC}"
    echo -e "${YELLOW}Copy .env.example to .env and customize for your environment.${NC}"
fi

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            echo -e "${YELLOW}Running in DRY RUN mode - no changes will be made${NC}"
            shift
            ;;
        --skip-build)
            SKIP_BUILD=true
            echo -e "${YELLOW}Skipping Docker build${NC}"
            shift
            ;;
        --skip-push)
            SKIP_PUSH=true
            echo -e "${YELLOW}Skipping Docker push${NC}"
            shift
            ;;
        --setup-mode)
            SETUP_MODE=true
            echo -e "${YELLOW}Running in SETUP MODE - skipping upgrade and service restart${NC}"
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --dry-run      Show what would be done without making changes"
            echo "  --skip-build   Skip Docker image building"
            echo "  --skip-push    Skip Docker image push to registry"
            echo "  --setup-mode   Setup mode: skip upgrade and service restart (for initial setup)"
            echo "  --help, -h     Show this help message"
            echo ""
            echo "Configuration can be set via .env file in the scripts/ directory."
            echo "See .env.example for available options."
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
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

check_command() {
    if ! command -v $1 &> /dev/null; then
        echo -e "${RED}Error: $1 is not installed or not in PATH${NC}"
        exit 1
    fi
}

check_directory() {
    if [ ! -d "$1" ]; then
        echo -e "${RED}Error: Directory $1 does not exist${NC}"
        exit 1
    fi
}

# ============================================
# Pre-flight Checks
# ============================================

echo ""
echo "=========================================="
echo "Snowflake Native App Deployment"
echo "=========================================="
echo ""
echo "Configuration:"
echo "  Project Root: $PROJECT_ROOT"
echo "  Connection: $SNOW_CONNECTION"
echo "  Registry: $SNOWFLAKE_REGISTRY"
echo "  Package: $APP_PACKAGE_NAME"
echo "  Instance: $APP_INSTANCE_NAME"
echo "  Version: $APP_VERSION"
echo ""

if [ "$DRY_RUN" = false ]; then
    echo "Performing pre-flight checks..."

    # Check required commands
    check_command "docker"
    check_command "snow"

    # Check required directories
    check_directory "$PROJECT_ROOT/backend"
    check_directory "$PROJECT_ROOT/frontend"
    check_directory "$PROJECT_ROOT/router"
    check_directory "$PROJECT_ROOT/app/src"

    echo -e "${GREEN}✓ Pre-flight checks passed${NC}"
    echo ""
fi

# ============================================
# Step 1: Build Docker Images
# ============================================

if [ "$SKIP_BUILD" = false ]; then
    echo "=========================================="
    echo "[1/9] Building Docker images..."
    echo "=========================================="

    run_command "Building backend image" \
        "(cd '$PROJECT_ROOT/backend' && docker build --platform linux/amd64 -t ${BACKEND_IMAGE} .)"

    run_command "Building frontend image" \
        "(cd '$PROJECT_ROOT/frontend' && docker build --platform linux/amd64 -t ${FRONTEND_IMAGE} .)"

    run_command "Building router image" \
        "(cd '$PROJECT_ROOT/router' && docker build --platform linux/amd64 -t ${ROUTER_IMAGE} .)"

    echo ""
else
    echo "=========================================="
    echo "[1/9] Skipping Docker build (--skip-build)"
    echo "=========================================="
    echo ""
fi

# ============================================
# Step 2: Login to Snowflake Docker Registry
# ============================================

if [ "$SKIP_PUSH" = false ]; then
    echo "=========================================="
    echo "[2/9] Logging in to Snowflake Docker registry..."
    echo "=========================================="

    run_command "Logging in to Snowflake registry" \
        "snow spcs image-registry login --connection ${SNOW_CONNECTION}"

    echo ""
else
    echo "=========================================="
    echo "[2/9] Skipping registry login (--skip-push)"
    echo "=========================================="
    echo ""
fi

# ============================================
# Step 3: Tag and Push Images
# ============================================

if [ "$SKIP_PUSH" = false ]; then
    echo "=========================================="
    echo "[3/9] Tagging and pushing images..."
    echo "=========================================="

    run_command "Tagging and pushing backend image" \
        "docker tag ${BACKEND_IMAGE} ${SNOWFLAKE_REGISTRY}/${BACKEND_IMAGE} && docker push ${SNOWFLAKE_REGISTRY}/${BACKEND_IMAGE}"

    run_command "Tagging and pushing frontend image" \
        "docker tag ${FRONTEND_IMAGE} ${SNOWFLAKE_REGISTRY}/${FRONTEND_IMAGE} && docker push ${SNOWFLAKE_REGISTRY}/${FRONTEND_IMAGE}"

    run_command "Tagging and pushing router image" \
        "docker tag ${ROUTER_IMAGE} ${SNOWFLAKE_REGISTRY}/${ROUTER_IMAGE} && docker push ${SNOWFLAKE_REGISTRY}/${ROUTER_IMAGE}"

    echo ""
else
    echo "=========================================="
    echo "[3/9] Skipping Docker push (--skip-push)"
    echo "=========================================="
    echo ""
fi

# ============================================
# Step 4: Upload Application Files
# ============================================

echo "=========================================="
echo "[4/9] Uploading application files to Snowflake stage..."
echo "=========================================="

APP_SRC_PATH="$PROJECT_ROOT/app/src"
run_command "Uploading files to stage" \
    "snow sql -q \"PUT file://${APP_SRC_PATH}/* @${APP_DATABASE}.${APP_SCHEMA}.${APP_STAGE} AUTO_COMPRESS=FALSE OVERWRITE=TRUE;\" --connection ${SNOW_CONNECTION}"

echo ""

# ============================================
# Step 5: Remove Old Version from Release Channel
# ============================================

echo "=========================================="
echo "[5/9] Removing old version from release channel..."
echo "=========================================="

run_command "Removing version from release channel" \
    "snow sql -q \"USE ROLE ${APP_PACKAGE_ROLE}; ALTER APPLICATION PACKAGE ${APP_PACKAGE_NAME} MODIFY RELEASE CHANNEL default DROP VERSION ${APP_VERSION};\" --connection ${SNOW_CONNECTION} || echo 'Version not in channel (OK)'"

echo ""

# ============================================
# Step 6: Drop Old Version
# ============================================

echo "=========================================="
echo "[6/9] Dropping old version..."
echo "=========================================="

run_command "Deregistering old version" \
    "snow sql -q \"USE ROLE ${APP_PACKAGE_ROLE}; ALTER APPLICATION PACKAGE ${APP_PACKAGE_NAME} DEREGISTER VERSION ${APP_VERSION};\" --connection ${SNOW_CONNECTION} || echo 'Version does not exist (OK)'"

echo ""

# ============================================
# Step 7: Register New Version
# ============================================

echo "=========================================="
echo "[7/9] Registering new version ${APP_VERSION}..."
echo "=========================================="

run_command "Registering new version" \
    "snow sql -q \"USE ROLE ${APP_PACKAGE_ROLE}; ALTER APPLICATION PACKAGE ${APP_PACKAGE_NAME} REGISTER VERSION ${APP_VERSION} USING @${APP_DATABASE}.${APP_SCHEMA}.${APP_STAGE};\" --connection ${SNOW_CONNECTION}"

run_command "Adding version to release channel" \
    "snow sql -q \"USE ROLE ${APP_PACKAGE_ROLE}; ALTER APPLICATION PACKAGE ${APP_PACKAGE_NAME} MODIFY RELEASE CHANNEL default ADD VERSION ${APP_VERSION};\" --connection ${SNOW_CONNECTION}"

echo ""

# ============================================
# Step 8: Upgrade Application
# ============================================

if [ "$SETUP_MODE" = false ]; then
    echo "=========================================="
    echo "[8/9] Upgrading application..."
    echo "=========================================="

    # Check if application exists before upgrading
    APP_EXISTS=$(snow sql -q "USE ROLE ${APP_CONSUMER_ROLE}; SHOW APPLICATIONS LIKE '${APP_INSTANCE_NAME}';" --connection ${SNOW_CONNECTION} 2>&1 | grep -v "SHOW APPLICATIONS" | grep -c "${APP_INSTANCE_NAME}" || echo "0")

    if [ "$APP_EXISTS" -gt "0" ]; then
        run_command "Upgrading application instance" \
            "snow sql -q \"USE ROLE ${APP_CONSUMER_ROLE}; ALTER APPLICATION ${APP_INSTANCE_NAME} UPGRADE USING VERSION ${APP_VERSION};\" --connection ${SNOW_CONNECTION}"
    else
        echo "Application instance does not exist yet - needs to be created by complete-setup.sh"
        echo "Skipping upgrade step..."
    fi

    echo ""
else
    echo "=========================================="
    echo "[8/9] Skipping upgrade (setup mode)"
    echo "=========================================="
    echo "Application will be created by complete-setup.sh"
    echo ""
fi

# ============================================
# Step 9: Restart Service
# ============================================

if [ "$SETUP_MODE" = false ]; then
    echo "=========================================="
    echo "[9/9] Restarting service..."
    echo "=========================================="

    # Only restart service if application exists
    if [ "$APP_EXISTS" -gt "0" ]; then
        run_command "Stopping service" \
            "snow sql -q \"USE ROLE ${APP_CONSUMER_ROLE}; CALL ${APP_INSTANCE_NAME}.app_public.stop_app();\" --connection ${SNOW_CONNECTION} || echo 'Service not running (OK)'"

        run_command "Starting service" \
            "snow sql -q \"USE ROLE ${APP_CONSUMER_ROLE}; CALL ${APP_INSTANCE_NAME}.app_public.start_app('${COMPUTE_POOL}', '${WAREHOUSE}');\" --connection ${SNOW_CONNECTION}"
    else
        echo "Application instance does not exist yet - service will be started by complete-setup.sh"
        echo "Skipping service restart step..."
    fi

    echo ""

    if [ "$DRY_RUN" = false ]; then
        echo "Waiting ${SERVICE_START_WAIT} seconds for service to start..."
        sleep $SERVICE_START_WAIT
    fi
else
    echo "=========================================="
    echo "[9/9] Skipping service restart (setup mode)"
    echo "=========================================="
    echo "Service will be started by complete-setup.sh"
    echo ""
fi

# ============================================
# Post-Deployment Status
# ============================================

if [ "$SETUP_MODE" = false ]; then
    echo ""
    echo "=========================================="
    echo "Checking service status..."
    echo "=========================================="

    run_command "Showing services" \
        "snow sql -q \"USE ROLE ${APP_CONSUMER_ROLE}; SHOW SERVICES IN APPLICATION ${APP_INSTANCE_NAME};\" --connection ${SNOW_CONNECTION}"

    echo ""
    echo "=========================================="
    echo "Getting application URL..."
    echo "=========================================="

    run_command "Getting app URL" \
        "snow sql -q \"USE ROLE ${APP_CONSUMER_ROLE}; CALL ${APP_INSTANCE_NAME}.app_public.app_url();\" --connection ${SNOW_CONNECTION}"
fi

# ============================================
# Completion Message
# ============================================

echo ""
echo "=========================================="
if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}DRY RUN completed successfully!${NC}"
    echo "No changes were made. Run without --dry-run to deploy."
else
    echo -e "${GREEN}Deployment completed successfully!${NC}"
fi
echo "=========================================="
echo ""
echo "Useful commands:"
echo ""
echo "  View logs:"
echo "    snow sql -q \"USE ROLE ${APP_CONSUMER_ROLE}; CALL ${APP_INSTANCE_NAME}.app_public.get_service_logs('eap-backend', 200);\" --connection ${SNOW_CONNECTION}"
echo ""
echo "  Check status:"
echo "    snow sql -q \"USE ROLE ${APP_CONSUMER_ROLE}; CALL ${APP_INSTANCE_NAME}.app_public.get_service_status();\" --connection ${SNOW_CONNECTION}"
echo ""
echo "  Get app URL:"
echo "    snow sql -q \"USE ROLE ${APP_CONSUMER_ROLE}; CALL ${APP_INSTANCE_NAME}.app_public.app_url();\" --connection ${SNOW_CONNECTION}"
echo ""
